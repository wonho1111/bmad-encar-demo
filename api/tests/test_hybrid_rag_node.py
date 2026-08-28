"""hybrid_rag_node 단위 테스트 — 네트워크(LLM)·DB 무관, 조립·폴백·가드 재시도 배선만 검증
(spec-13-3-하이브리드-검색-sql-벡터.md Tasks; 가이드 질의확장·컷오프는 spec-13-6).

실제 생성·실행(라이브 LLM+DB)은 dev-story 라이브 스모크(test_live_smoke.py)에서 확인한다.
여기서는 결정론적인 부분만 격리해 테스트한다:
  (1) 조립 SQL이 기대 모양(status='on_sale' AND <조건> ORDER BY embedding <=> %s::vector
      LIMIT 5)인지
  (2) NONE 응답 시 doc_rag_node가 정확히 1회 호출되고 그 반환값이 그대로 나오는지
  (3) 가드 차단 1회 후 재생성 성공 경로
  (4) 2회 연속 차단 시 SqlGuardError가 그대로 전파되는지
  (5) run_select가 (qvec,) params와 함께 호출되는지(임베딩 바인딩 배선 검사, DW-559)
  (6) 가이드 질의확장(FR44/FR49, Story 13.6, top-k 상대 게이트로 전환) — 게이트 통과 가이드가
      시스템 프롬프트에 실제로 주입되는지·상한 초과 가이드는 주입되지 않는지·주입 개수·
      글자수 상한(_GUIDE_INJECT_MAX/_GUIDE_INJECT_CHAR_CAP)이 지켜지는지·가이드로만 도출된
      조건이 최종 SQL·answer 인용(상위 최대 2개 제목)에 반영되는지

⚠️ find_relevant_guide()는 doc_rag_node.py에 정의돼 **그 모듈 자신의 run_select**를 참조한다
  (hybrid_rag_node.run_select를 패치해도 닿지 않는다 — 서로 다른 모듈 전역이다). hybrid_rag_node()가
  재시도 루프 진입 전에 항상 find_relevant_guide()를 호출하므로(13.6), 이 파일의 모든 테스트는
  `doc_rag_node_module.run_select`도 함께(guide 없음이면 빈 리스트로) 패치해야 실제 DB 접속
  시도 없이 결정론적으로 돈다 — 안 하면 DATABASE_URL 미설정 환경에서 fail-loud로 죽는다.
"""

import pytest

import app.graph.doc_rag_node as doc_rag_node_module
import app.graph.hybrid_rag_node as node
import app.graph.listing_cards as listing_cards
from app.db.sql_guard import DEFAULT_LIMIT, SqlGuardError

_LISTING_ID = "55555555-5555-4555-8555-555555555555"

# 절대 상한(0.45) 이내/초과 가이드 행 — (title, content, distance) 3-tuple(find_relevant_guide
# 계약). 단독 행이면 1등=자기 자신이라 마진 게이트는 항상 통과하고 상한만 갈린다.
_GUIDE_ROW_WITHIN_CUTOFF = (
    "패밀리카로 무난한 차종 고르기", "중형차·SUV·RV, 5~7인승이 가족 용도로 무난하다.", 0.1,
)
_GUIDE_ROW_BEYOND_CUTOFF = ("전기차 충전·보조금·주행거리 이해", "전기차 본문 텍스트.", 0.5)


def _fake_row():
    return (
        _LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원",
        "가솔린", None, None, None, None,
    )


def _patch_guide_lookup(monkeypatch, guide_rows=None):
    """find_relevant_guide()가 쓰는 doc_rag_node 모듈의 run_select를 가짜로 교체한다.

    guide_rows를 생략하면 빈 리스트 — 가이드 0건(기존 테스트 대다수의 전제, 회귀 없음).

    반환값은 이 가짜가 실제로 받은 인자를 담는 dict다(3회차 코드리뷰). 두 가지를 함께 고친다:
      (1) 이전 버전은 SQL을 보지 않고 **모든** 질의에 가이드 행을 돌려줬다 — 형제 헬퍼
          `_install_fakes`(test_doc_rag_node.py)는 테이블로 분기하는데 이쪽만 안 했다. 나중에
          실물 doc_rag_node를 타는 폴백 테스트가 생기면 (title, content, distance) 3-tuple이
          매물 행으로 넘어가 rows_to_cards에서 정체불명 크래시가 난다.
      (2) params를 통째로 버려서, hybrid가 `qvec_literal`(문자열) 대신 `qvec`(list[float])을
          넘기도록 바뀌어도 전 스위트가 초록이었다(변이 실측). 실 DB에선 psycopg가 리스트를
          ARRAY[...]로 적응시켜 `::vector` 캐스팅이 실패하고 HYBRID 요청 전체가 500이 된다.
    """
    captured: dict = {}

    def fake_run_select(sql, params=None):
        if "from guide_documents" in sql.lower():
            captured["guide_sql"] = sql
            captured["guide_params"] = params
            return guide_rows or []
        captured.setdefault("other_sql", []).append(sql)
        return []

    monkeypatch.setattr(doc_rag_node_module, "run_select", fake_run_select)
    return captured


class _FixedLLM:
    """미리 정해둔 응답을 순서대로 돌려주는 가짜 LLM(네트워크·과금 없음)."""

    def __init__(self, outputs):
        self._outputs = list(outputs)

    def invoke(self, messages):
        text = self._outputs.pop(0)
        return type("Msg", (), {"content": text})()


class _CapturingLLM:
    """호출된 messages를 그대로 기록하고 고정 응답을 돌려주는 가짜 LLM(시스템 프롬프트 검증용)."""

    def __init__(self, output):
        self._output = output
        self.calls: list = []

    def invoke(self, messages):
        self.calls.append(messages)
        return type("Msg", (), {"content": self._output})()


# ── (1) 조립 SQL 모양 + (5) run_select 임베딩 바인딩 배선 ─────────────────
def test_hybrid_assembles_expected_sql_and_binds_embedding_params(monkeypatch):
    captured = {}

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.5, -0.25])
    _patch_guide_lookup(monkeypatch)

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(node, "run_select", fake_run_select)
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("3천만원 이하로 무난한 패밀리카")

    sql = captured["sql"]
    assert "status = 'on_sale'" in sql
    assert "AND (body_type = 'SUV')" in sql
    assert "ORDER BY embedding <=> %s::vector" in sql
    assert f"LIMIT {DEFAULT_LIMIT}" in sql
    # run_select가 %s 자리표시자에 실제로 임베딩(벡터 리터럴)을 바인딩해 호출됐는지(DW-559).
    # 기대값을 _vec_literal로 만들지 않고 문자열로 박는다 — 검사 대상 함수로 기대값을 만들면
    # 그 함수가 어떤 모양을 내든 항상 참이라 pgvector 리터럴 형식을 고정하지 못한다
    # (test_doc_rag_node.py가 쓰는 방식과 맞춘다).
    assert captured["params"] == ("[0.5,-0.25]",)
    assert result["listings"]


# ── (2) NONE 폴백 ─────────────────────────────────────────────────────
def test_hybrid_none_condition_falls_back_to_doc_rag_node(monkeypatch):
    calls = {"doc": 0, "embed": 0}

    def fake_doc(query, qvec=None):
        calls["doc"] += 1
        # 재임베딩 없이 위에서 계산한 벡터를 그대로 넘겨받았는지(코드리뷰 — 이중 임베딩 제거).
        assert qvec == [0.1]
        return {"answer": "DOC 결과", "listings": ["d1"]}

    def fake_embed_query(q):
        calls["embed"] += 1
        return [0.1]

    # 대소문자 무관·공백 트림 확인 — 소문자·앞뒤 공백이 섞여도 폴백해야 한다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM([" none "]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    # 가이드 조회가 조건추출(NONE 판정)보다 먼저 실행되므로(13.6) embed_query·가이드 조회도
    # 여기서 결정론적으로 막아야 한다.
    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    _patch_guide_lookup(monkeypatch)

    result = node.hybrid_rag_node("패밀리카로 무난한 거")

    assert calls["doc"] == 1
    # embed_query가 정확히 1회만 불려야 한다 — doc_rag_node가 qvec을 넘겨받아 재계산하지
    # 않는지 못박는다(코드리뷰: 폴백에서 임베딩 API가 중복 호출되던 문제).
    assert calls["embed"] == 1
    assert result == {"answer": "DOC 결과", "listings": ["d1"]}


# ── 빈/공백 응답도 NONE과 동일하게 폴백(review patch 2) ────────────────
def test_hybrid_blank_condition_falls_back_to_doc_rag_node(monkeypatch):
    calls = {"doc": 0, "embed": 0}

    def fake_doc(query, qvec=None):
        calls["doc"] += 1
        assert qvec == [0.1]
        return {"answer": "DOC 결과", "listings": ["d1"]}

    def fake_embed_query(q):
        calls["embed"] += 1
        return [0.1]

    # LLM이 공백만 있는 응답을 내도(정확히 "NONE"이 아니어도) 폴백해야 한다 — 안 그러면
    # `AND ()`라는 깨진 SQL이 가드는 통과(status='on_sale' AND항만으로 충족)하고 실행
    # 단계에서 psycopg 문법 오류로 죽는다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["   "]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    _patch_guide_lookup(monkeypatch)

    result = node.hybrid_rag_node("패밀리카로 무난한 거")

    assert calls["doc"] == 1
    assert calls["embed"] == 1
    assert result == {"answer": "DOC 결과", "listings": ["d1"]}


# ── LIKE 조건의 리터럴 '%'가 psycopg params 바인딩과 충돌하지 않는지(review patch 1) ──
def test_hybrid_percent_literal_in_condition_is_escaped_before_execution(monkeypatch):
    captured = {}

    # model LIKE '%아반떼%' — LLM이 자연스럽게 낼 수 있는 부분일치 조건. run_select가
    # params=(qvec,)와 함께 호출되므로(이 스토리부터 처음), psycopg가 SQL 전체에서 '%'를
    # 자리표시자로 스캔한다 — 이스케이프 없이 그대로 두면 실행 단계에서 ProgrammingError/
    # UnicodeDecodeError로 죽는다(가드는 리터럴 안 '%'를 못 잡는다, no_strings가 지우고 검사).
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["model LIKE '%아반떼%'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(node, "run_select", fake_run_select)
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아반떼 비슷한 거")

    # 실행에 넘어간 SQL은 '%'가 전부 '%%'로 이스케이프돼 있어야 psycopg가 안전하게 처리한다
    # (벡터절의 진짜 자리표시자는 단일 %s로 그대로 남아야 한다).
    assert "LIKE '%%아반떼%%'" in captured["sql"]
    assert "ORDER BY embedding <=> %s::vector" in captured["sql"]
    assert captured["params"] == ("[0.1]",)
    # psycopg가 실제로 이 SQL+params를 어떻게 치환하는지까지 직접 재현 — 크래시 없이 단일
    # placeholder만 남고 리터럴 '%'는 원래 값으로 복원돼야 한다(가드 통과 후 500으로 새지 않음).
    from psycopg._queries import _query2pg_nocache

    formatted, formats, *_ = _query2pg_nocache(captured["sql"].encode("utf-8"), "utf-8")
    assert formatted.count(b"$1") == 1  # 진짜 자리표시자는 하나만 남는다
    assert "%아반떼%".encode("utf-8") in formatted  # 이스케이프가 원래 리터럴로 복원됨
    assert result["listings"]


# ── NONE 유사 응답(따옴표·마침표)도 폴백으로 읽는지(review-2 patch) ─────
@pytest.mark.parametrize("raw", ["NONE.", '"NONE"', "`none`", " None . "])
def test_hybrid_near_miss_none_sentinel_falls_back(monkeypatch, raw):
    calls = {"doc": 0, "embed": 0}

    def fake_doc(query, qvec=None):
        calls["doc"] += 1
        assert qvec == [0.1]
        return {"answer": "DOC 결과", "listings": ["d1"]}

    def fake_embed_query(q):
        calls["embed"] += 1
        return [0.1]

    # 정확히 "NONE"만 인식하면 `NONE.`은 조건으로 조립돼 가드에 forbidden_column으로
    # 걸리고(실측), 폴백이 아니라 400이 나간다 — 의도한 경로가 통째로 사라진다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM([raw]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    _patch_guide_lookup(monkeypatch)

    assert node.hybrid_rag_node("패밀리카로 무난한 거") == {
        "answer": "DOC 결과", "listings": ["d1"],
    }
    assert calls["doc"] == 1
    assert calls["embed"] == 1


# ── 가드는 통과하지만 실행 불가한 조건 → 재시도, 최종 실패는 400 계약 유지(review-2 patch) ──
def test_hybrid_unexecutable_condition_retries_then_raises_sql_guard_error(monkeypatch):
    import psycopg

    # `WHERE price <= N`은 가드를 **통과**한다(실측) — 조각이 `AND (...)` 안에 들어가
    # 토큰 검사만으로는 문법 오류가 안 보인다. 실행 단계에서야 psycopg가 죽는다.
    llm = _FixedLLM(["WHERE price <= 30000000", "AND price <= 30000000"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)

    calls = {"n": 0}

    def boom(sql, params=None):
        calls["n"] += 1
        raise psycopg.errors.SyntaxError('syntax error at or near "WHERE"')

    monkeypatch.setattr(node, "run_select", boom)

    with pytest.raises(SqlGuardError) as exc:
        node.hybrid_rag_node("3천만원 이하로 무난한 패밀리카")

    # 2회(최초+재생성) 시도했고, 최종적으로 psycopg 예외가 아니라 SqlGuardError가 나가야
    # /ai/search가 500이 아닌 400 한국어 안내로 응답한다(sql_rag_node와 동일 계약).
    assert calls["n"] == 2
    assert exc.value.code == "condition_not_executable"


def test_hybrid_unexecutable_condition_recovers_on_retry(monkeypatch):
    import psycopg

    llm = _FixedLLM(["price", "body_type = 'SUV'"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    state = {"n": 0}

    def flaky(sql, params=None):
        state["n"] += 1
        if state["n"] == 1:
            raise psycopg.errors.DatatypeMismatch("argument of AND must be type boolean")
        return [_fake_row()]

    monkeypatch.setattr(node, "run_select", flaky)

    assert node.hybrid_rag_node("아무 질의")["listings"]


def test_hybrid_connection_failure_is_not_swallowed_as_400(monkeypatch):
    import psycopg

    # 연결 장애는 "조건이 나쁜 것"이 아니므로 400으로 바꾸면 안 된다 — 그대로 올라가 500이
    # 돼야 운영에서 DB 장애가 사용자 입력 탓으로 오분류되지 않는다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)

    def down(sql, params=None):
        raise psycopg.OperationalError("connection failed")

    monkeypatch.setattr(node, "run_select", down)

    with pytest.raises(psycopg.OperationalError):
        node.hybrid_rag_node("아무 질의")


# ── (3) 가드 차단 1회 후 재생성 성공 ────────────────────────────────────
def test_hybrid_guard_rejection_retries_once_then_succeeds(monkeypatch):
    """LLM을 2회 부르는 경로에서도 임베딩·가이드 조회는 각각 1회뿐이다(스펙 Always).

    3회차 코드리뷰: "재시도 루프 **진입 전** 1회만 계산"을 못박는 호출횟수 단언이 NONE/공백
    폴백 테스트 3건에만 있었다. 정작 낭비가 2배가 되는 경로는 여기(LLM 2회 = 루프 2회전)인데
    이 테스트는 호출을 세지 않는 람다를 써서, 호이스트를 루프 안으로 되돌리면 과금되는 Gemini
    임베딩 호출과 guide_documents 조회가 매 재시도마다 반복되는데도 초록으로 통과했다.
    """
    # 1차: OR 포함 조건(가드가 forbidden_or로 거부) → 2차: 정상 조건.
    llm = _FixedLLM(["price < 1 OR price > 0", "body_type = 'SUV'"])
    calls = {"embed": 0, "guide": 0}

    def counting_embed(q):
        calls["embed"] += 1
        return [0.1]

    def counting_guide(query, qvec_literal):
        calls["guide"] += 1
        return []

    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", counting_embed)
    monkeypatch.setattr(node, "find_relevant_guides_fused", counting_guide)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아무 질의")

    assert result["listings"]
    assert calls["embed"] == 1, "재시도 2회전인데 임베딩이 재계산됐다(호이스트 회귀)"
    assert calls["guide"] == 1, "재시도 2회전인데 가이드 조회가 반복됐다(호이스트 회귀)"


# ── (4) 2회 연속 가드 차단 → SqlGuardError 전파 ─────────────────────────
def test_hybrid_guard_rejection_twice_propagates_sql_guard_error(monkeypatch):
    llm = _FixedLLM(["price < 1 OR price > 0", "price < 1 OR price > 0"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)

    with pytest.raises(SqlGuardError) as exc:
        node.hybrid_rag_node("아무 질의")
    assert exc.value.code == "forbidden_or"


# ── 0건일 때 FR17 안내 문구를 쓰는지(sql_rag_node와 동일 톤) ─────────────
def test_hybrid_empty_result_uses_fr17_message(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("절대 없을 조건")

    assert result["listings"] == []
    assert "없어요" in result["answer"]


def test_hybrid_empty_result_with_guide_omits_citation(monkeypatch):
    """매물 0건이면 컷오프 이내 가이드가 있어도 인용을 붙이지 않는다(AC3, I/O 매트릭스 5행).

    3회차 코드리뷰 실측: hybrid의 인용 게이트에서 `listings and`를 지워도 전 스위트가
    370 passed로 초록이었다. 컷오프 이내 가이드를 쓰는 HYBRID 테스트 2건은 둘 다 매물
    1건을 돌려주고, 0건 테스트는 가이드가 없어서 **두 조건의 교집합이 한 번도 테스트되지
    않았다**. 회귀가 나면 사용자는 "조건에 맞는 매물이 없어요… (참고: …)" — 0건 안내에
    근거 인용이 붙은 모순된 답변을 받는다. doc_rag_node 쪽 짝 테스트는
    test_empty_result_returns_fr17_guidance(test_doc_rag_node.py)로 이미 있었다.
    """
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch, [_GUIDE_ROW_WITHIN_CUTOFF])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("가이드는 가깝지만 매물이 없는 조건")

    assert result["listings"] == []
    assert "참고:" not in result["answer"]


# ── 가이드 질의확장(FR44/FR49, Story 13.6) ─────────────────────────────
def test_guide_within_cutoff_is_injected_into_system_prompt(monkeypatch):
    """컷오프 이내 가이드는 시스템 프롬프트에 title·content가 실제로 포함된다(FR44)."""
    llm = _CapturingLLM("body_type IN ('중형차','SUV','RV')")
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    captured = _patch_guide_lookup(monkeypatch, [_GUIDE_ROW_WITHIN_CUTOFF])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    node.hybrid_rag_node("3천만원 이하로 무난한 패밀리카")

    system_prompt = llm.calls[0][0][1]  # messages[0] == ("system", ...)
    assert _GUIDE_ROW_WITHIN_CUTOFF[0] in system_prompt  # title
    assert _GUIDE_ROW_WITHIN_CUTOFF[1] in system_prompt  # content
    assert "규칙 2" in system_prompt  # 규칙 2보다 우선한다는 지시가 실제로 들어갔는지
    # hybrid가 가이드 조회에 **pgvector 텍스트 리터럴**을 넘기는지 못박는다(3회차 코드리뷰) —
    # qvec_literal 대신 qvec(list[float])을 넘기면 실 DB에서 ::vector 캐스팅이 실패해 500이
    # 되는데, 가짜가 params를 버리던 동안엔 이 변이가 전 스위트 초록으로 통과했다.
    # 세 번째 값은 top-k 상수(doc_rag_node._GUIDE_TOP_K) — LIMIT %s 바인딩.
    assert captured["guide_params"] == ("[0.1]", "[0.1]", doc_rag_node_module._GUIDE_TOP_K)


def test_guide_beyond_cutoff_is_not_injected(monkeypatch):
    """컷오프 초과 가이드는 프롬프트에 미포함 — 무관 가이드로 조건추출을 오염시키지 않는다(FR49)."""
    llm = _CapturingLLM("body_type = 'SUV'")
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch, [_GUIDE_ROW_BEYOND_CUTOFF])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아무 질의")

    system_prompt = llm.calls[0][0][1]
    assert _GUIDE_ROW_BEYOND_CUTOFF[0] not in system_prompt
    assert _GUIDE_ROW_BEYOND_CUTOFF[1] not in system_prompt
    # 컷오프 초과 가이드는 answer 인용에도 쓰이지 않는다.
    assert "참고:" not in result["answer"]


@pytest.mark.parametrize(
    "guide_row", [("", "본문", 0.1), ("   ", "본문", 0.1), ("제목", "  \n ", 0.1)]
)
def test_blank_guide_is_neither_injected_nor_cited(monkeypatch, guide_row):
    """제목·본문이 비었거나 공백뿐인 가이드는 프롬프트 주입도 인용도 하지 않는다(후속 코드리뷰).

    이전 패스는 인용 자리에만 `guide[0]` 검사를 넣어 두 구멍을 남겼다: 공백 제목("   ")은
    참이라 "(참고:    )"가 그대로 붙었고, 빈 제목·빈 본문 가이드도 주입 자리는 `if guide:`뿐이라
    시스템 프롬프트에 "규칙 2보다 우선한다"는 지시만 매핑 없이 들어갔다. 이제 게이트가
    find_relevant_guide 한 곳에 있으므로 두 자리 모두 한 번에 닫힌다.
    """
    llm = _CapturingLLM("body_type = 'SUV'")
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch, [guide_row])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아무 질의")

    assert result["listings"]
    assert "참고:" not in result["answer"]
    # 주입 자리도 함께 확인 — 가이드 블록의 우선순위 지시가 프롬프트에 들어가면 안 된다.
    system_prompt = llm.calls[0][0][1]
    assert "참고 가이드 문서" not in system_prompt


# ── 다건 가이드 — 주입 개수 상한(_GUIDE_INJECT_MAX=3) ────────────────────
def test_multiple_guides_injection_capped_at_max(monkeypatch):
    """게이트를 4건이 통과해도 프롬프트에는 상위 최대 3개까지만 주입된다.

    상충 매핑(서로 다른 페르소나 섹션)이 전부 프롬프트에 들어가 조건 AND 폭발로 0건이
    되는 것을 막기 위한 상한 — doc_rag_node.py 상단 docstring이 밝히는 이유와 동일하다.
    """
    llm = _CapturingLLM("body_type = 'SUV'")
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    guide_rows = [
        ("1등", "본문1", 0.10),
        ("2등", "본문2", 0.11),
        ("3등", "본문3", 0.12),
        ("4등", "본문4", 0.13),
    ]
    _patch_guide_lookup(monkeypatch, guide_rows)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    node.hybrid_rag_node("아무 질의")

    system_prompt = llm.calls[0][0][1]
    assert "1등" in system_prompt and "2등" in system_prompt and "3등" in system_prompt
    assert "4등" not in system_prompt  # 4번째는 주입 상한(_GUIDE_INJECT_MAX=3) 밖.


def test_multiple_guides_injection_capped_at_char_budget(monkeypatch):
    """content 누적 글자수가 `_GUIDE_INJECT_CHAR_CAP`(3000자)을 넘기면 그 문서부터 제외한다.

    프롬프트 비대화 방지 — 상위 2개만으로 이미 3000자를 넘으면 3번째는 개수 상한(3개) 안에
    있어도 주입되지 않는다.
    """
    llm = _CapturingLLM("body_type = 'SUV'")
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    guide_rows = [
        ("1등", "가" * 1600, 0.10),
        ("2등", "나" * 1600, 0.11),  # 누적 3200자 — 3000자 상한 초과, 여기서 끊긴다.
        ("3등", "다" * 100, 0.12),
    ]
    _patch_guide_lookup(monkeypatch, guide_rows)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    node.hybrid_rag_node("아무 질의")

    system_prompt = llm.calls[0][0][1]
    assert "1등" in system_prompt
    assert "2등" not in system_prompt  # 누적이 상한을 넘기는 순간부터 제외.
    assert "3등" not in system_prompt


# ── 다건 가이드 — 인용(answer)은 주입 상한과 무관하게 상위 최대 2개 제목 ──────
def test_multiple_guides_citation_capped_at_two_titles(monkeypatch):
    """게이트 통과분이 3건이어도(주입 상한 3 이내) answer 인용은 상위 최대 2개까지만.

    doc_rag_node의 인용 규칙과 동일해야 한다(스펙 "답변 인용도 doc_rag_node와 동일 규칙").
    """
    llm = _FixedLLM(["body_type = 'SUV'"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    guide_rows = [
        ("1등 가이드", "본문1", 0.10),
        ("2등 가이드", "본문2", 0.11),
        ("3등 가이드", "본문3", 0.12),
    ]
    _patch_guide_lookup(monkeypatch, guide_rows)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아무 질의")

    assert result["answer"].endswith("(참고: 1등 가이드, 2등 가이드)")
    assert "3등 가이드" not in result["answer"]


# ── 최상급×HYBRID 정렬 캐비엇(옵션 b, spec-13-9 Design Notes) ───────────
def test_superlative_query_appends_sort_caveat(monkeypatch):
    """최상급 표현("제일"·"가장")이 섞인 HYBRID 질의는 정렬 미적용 캐비엇이 답변에 붙는다.

    캐비엇 문구는 "조건을 더 구체적으로 말씀해주세요"류 실행 불가능한 조언이면 안 된다
    (P11 — HYBRID는 벡터 정렬만 적용해 조건을 더 붙여도 여전히 HYBRID로 남는다. 가격
    정렬은 순수 구조질의(SQL 경로)에서만 가능하므로 그런 조언은 지킬 수 없는 약속이다).

    ⚠️ **P11의 나머지 절반은 2026-08-05 사용자 결정으로 뒤집혔다.** 원래 P11은 "실제로
    가격순을 볼 수 있는 방법을 **구체 예시와 함께** 알려줘야 한다"까지 요구했고, 그래서
    캐비엇에 `구조적 조건만으로 다시 물어보시면 …(예: "3천만원 이하 SUV 가격 낮은 순")`
    이 붙어 있었다. 실제 답변 본문이 `조건에 맞는 매물 5건을 찾았어요.` 한 줄인데 안내가
    그보다 길어져, 사용자가 "잔소리"로 판단해 한 문장으로 줄이기로 했다(선택지 A 유지/
    B 축약/C 삭제 중 B). 그래서 "구체 예시가 있어야 한다"는 단언은 여기서 뺀다 —
    **고지 자체가 남아 있어야 한다는 요구(위 첫 단언)는 그대로다.** 삭제(C)를 안 택한
    이유가 그것이다: 없애면 "제일 싼"이라고 물은 사용자가 가격순이 아닌 결과를 아무
    설명 없이 받는다.
    """
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("제일 싼 패밀리카")

    assert node._SUPERLATIVE_CAVEAT in result["answer"]
    assert "조건을 더 구체적으로 말씀해" not in result["answer"]  # 실행 불가능한 옛 조언 제거
    # 축약 후에도 "정렬이 반영되지 않았다"는 사실 자체는 문구에 남아 있어야 한다 —
    # 상수를 빈 문자열로 만들거나 무관한 문구로 갈아끼우면 여기서 red가 난다(실측 확인).
    assert "정렬" in node._SUPERLATIVE_CAVEAT and "반영되지 않" in node._SUPERLATIVE_CAVEAT


def test_non_superlative_query_omits_sort_caveat(monkeypatch):
    """최상급 표현이 없으면 캐비엇을 붙이지 않는다(과잉 경고 방지)."""
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("3천만원 이하로 무난한 패밀리카")

    assert node._SUPERLATIVE_CAVEAT not in result["answer"]


def test_superlative_empty_result_omits_caveat(monkeypatch):
    """매물 0건이면 최상급이 있어도 캐비엇을 붙이지 않는다(0건 안내와 모순되는 답변 방지,
    guide 인용의 `test_hybrid_empty_result_with_guide_omits_citation`과 동일 원칙)."""
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("제일 싼 패밀리카")

    assert result["listings"] == []
    assert node._SUPERLATIVE_CAVEAT not in result["answer"]


def test_non_price_superlative_query_omits_sort_caveat(monkeypatch):
    """가격과 무관한 최상급("가장 안전한")은 캐비엇을 붙이지 않는다(코드리뷰 정정).

    router_node 프롬프트는 최상급 부사("제일"·"가장") + 가격 형용사(싸다·비싸다·저렴하다)의
    **결합**만 구조조건으로 본다. `_has_superlative`가 부사만으로 판정하면 "가장 안전한
    SUV"·"가장 인기있는 SUV로 바꿔줘"처럼 가격과 무관한 최상급에도 캐비엇이 잘못 붙는다.
    """
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch)
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("가장 안전한 SUV")

    assert node._SUPERLATIVE_CAVEAT not in result["answer"]


def test_superlative_query_via_none_fallback_appends_sort_caveat(monkeypatch):
    """spec의 예시("제일 싼 패밀리카")는 구조조건을 못 뽑아 doc_rag_node로 폴백하는 경로를
    타는데(느낌 표현뿐이라 LLM이 NONE을 낸다), 캐비엇 부착 로직이 SQL 조립 분기에만 있으면
    바로 이 실제 케이스가 캐비엇 없이 나간다(코드리뷰 정정) — 폴백 경로에도 적용한다.
    """
    def fake_doc(query, qvec=None):
        return {
            "answer": "'제일 싼 패밀리카'에 어울리는 매물 3건을 찾았어요.",
            "listings": ["d1", "d2", "d3"],
        }

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["NONE"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    _patch_guide_lookup(monkeypatch)

    result = node.hybrid_rag_node("제일 싼 패밀리카")

    assert node._SUPERLATIVE_CAVEAT in result["answer"]
    assert result["listings"] == ["d1", "d2", "d3"]


def test_non_superlative_none_fallback_omits_sort_caveat(monkeypatch):
    """폴백 경로도 최상급이 없으면 캐비엇을 붙이지 않는다(회귀 대조군)."""
    def fake_doc(query, qvec=None):
        return {"answer": "'패밀리카로 무난한 거'에 어울리는 매물 1건을 찾았어요.", "listings": ["d1"]}

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["NONE"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    _patch_guide_lookup(monkeypatch)

    result = node.hybrid_rag_node("패밀리카로 무난한 거")

    assert node._SUPERLATIVE_CAVEAT not in result["answer"]


def test_superlative_none_fallback_empty_result_omits_caveat(monkeypatch):
    """폴백 경로도 0건이면 캐비엇을 붙이지 않는다(정상 SQL 분기와 동일 원칙)."""
    def fake_doc(query, qvec=None):
        return {"answer": "조건에 맞는 매물이 없어요.", "listings": []}

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["NONE"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)
    _patch_guide_lookup(monkeypatch)

    result = node.hybrid_rag_node("제일 싼 패밀리카")

    assert result["listings"] == []
    assert node._SUPERLATIVE_CAVEAT not in result["answer"]


# ── P5 — `_has_superlative`가 순서 무관 substring AND가 아니라 근접 결합만 잡는지 ──────
def test_has_superlative_false_for_santafe_substring_false_positive():
    """"싼타페"의 "싼"이 가격 형용사로 오매칭되면 안 된다(실측 버그, P5)."""
    assert node._has_superlative("가장 인기있는 싼타페 보여줘") is False


def test_has_superlative_false_for_unrelated_adverb_and_adjective_in_same_sentence():
    """최상급 부사와 가격 형용사가 서로 다른 절에 각각 있으면(순서 무관 AND) 결합이 아니다."""
    assert node._has_superlative("가장 인기 많고 저렴한 SUV") is False
    assert node._has_superlative("제일 안전한 차인데 가격도 싸게") is False


def test_has_superlative_false_for_non_price_superlative():
    assert node._has_superlative("가장 안전한 SUV") is False


def test_has_superlative_true_for_adjacent_price_combo():
    assert node._has_superlative("제일 싼 패밀리카") is True
    assert node._has_superlative("가장 비싼 차") is True
    assert node._has_superlative("제일 저렴한 SUV") is True


# ── P2(13.9 3차 리뷰) — 근접 정규식만으론 "싼타페" 오탐이 안 잡혔다 ──────────────────
# 위 `test_has_superlative_false_for_santafe_substring_false_positive`는 부사와 차종명 사이에
# 다른 낱말("인기있는")이 낀 변형만 덮어서, 부사 **바로 뒤**에 차종명이 오는 원형(`\S{0,4}?`가
# 0자를 허용하므로 그대로 매칭)은 통과한 채로 남아 있었다(실측: 넷 다 True).
# 가격 형용사 뒤 음절 경계 `(?![가-힣])`가 이 넷을 거른다.
@pytest.mark.parametrize(
    "query",
    [
        "가장 싼타페 보여줘",      # 부사 바로 뒤 차종명 — "싼"이 "싼타페"의 첫 음절일 뿐
        "제일 싼타페 보여줘",
        "제일 싸지 않은 차",       # "싸지 않은" = 부정 — 가격 정렬 요청이 아니다
        "가장 비싸도 되는 차",     # "비싸도" = 양보 — 정렬이 아니라 허용 범위 언급
    ],
)
def test_has_superlative_false_when_price_adjective_continues_into_another_syllable(query):
    assert node._has_superlative(query) is False


# ── DW-653 — 음절 경계가 만든 "알려진 구멍"을 양성/음성과 같은 표에 함께 고정한다 ─────────
# 이 검사가 왜 있나: 위 P2가 넣은 `(?![가-힣])`는 `가장 싼타페`(오탐)를 막는 대신 띄어쓰기를
#   생략한 `가장 싼거`·`제일 싼차`(정상 질의)도 함께 떨어뜨렸다. 정규식만 보면 둘이 구분되지
#   않는다. 그 경계가 **어디에 있는지**를 고정하는 테스트가 없어서, DW-653은 "다음에 정규식을
#   손대는 사람이 이 경계를 모른 채 되돌리거나 더 좁힌다"를 위험으로 적었다 — 그 항목이
#   요구한 "셋을 한 테스트에서 대조"가 이것이다.
# ⚠️ `가장 싼거`·`제일 싼차`의 기대값 False는 **옳아서가 아니라 지금 그렇기 때문이다.**
#   DW-653을 실제로 고치면(어간+조사/어미 목록으로 전환) 이 두 줄이 red가 된다 —
#   그때 기대값을 True로 바꾸고 DW-653을 닫아라. red가 나는 것이 이 검사의 목적이다.
@pytest.mark.parametrize(
    ("query", "expected", "why"),
    [
        ("가장 싼 거", True, "양성 — 띄어쓰기 정상형(큐리셋 M1.t3 계열)"),
        ("제일 싼 차", True, "양성 — 띄어쓰기 정상형(큐리셋 S6)"),
        ("가장 저렴한 SUV", True, "양성 — `저렴`은 어미 때문에 음절 경계에서 제외됨"),
        ("가장 싼타페", False, "음성 — `싼`이 차명 첫 음절일 뿐(P2가 닫으려던 오탐)"),
        ("제일 싼타페", False, "음성 — 위와 같음"),
        ("가장 싼거", False, "⚠ 알려진 구멍(DW-653) — 정규식상 `싼타페`와 구분되지 않는다"),
        ("제일 싼차", False, "⚠ 알려진 구멍(DW-653) — 위와 같음"),
    ],
)
def test_has_superlative_syllable_boundary_covers_positive_negative_and_known_gap(
    query, expected, why
):
    assert node._has_superlative(query) is expected, why


def test_superlative_price_re_identical_in_both_modules():
    """P7 — 두 사본이 같다는 계약을 주석이 아니라 실행되는 검사로 못박는다(CLAUDE.md B9).

    `hybrid_rag_node`·`contextualize_node`는 같은 어휘·모양의 정규식을 각자 지역 상수로
    둔다(공유 유틸로 뽑지 않기로 한 Design Notes 결정). 지금까지 그 "동일하다"는 계약은
    양쪽 주석에만 있었고, 실제로 한쪽만 넓혀도 전체 스위트가 초록이었다(실측). 이 한 줄이
    그 lockstep을 실행 가능한 계약으로 바꾼다.
    """
    from app.graph import contextualize_node

    assert node._SUPERLATIVE_PRICE_RE.pattern == contextualize_node._SUPERLATIVE_PRICE_RE.pattern


def test_guide_present_condition_is_assembled_and_cited(monkeypatch):
    """가이드가 주입된 상태에서 조건이 SQL로 조립되고 answer에 결정론적 인용이 붙는다(AC2).

    ⚠️ 이 테스트는 "가이드가 그 조건을 **도출**했다"는 것을 검증하지 않는다(3회차 코드리뷰 —
    이전 이름·docstring은 그렇게 주장했다). 조건 문자열은 아래 `_FixedLLM`에 테스트가 직접
    박아 넣은 상수이므로 가이드 주입과 그 조건 사이에 인과가 없다. 가짜 LLM으로는 원리상
    도출을 관측할 수 없다 — 그 역할은 test_live_smoke.py::test_live_smoke_hybrid의
    "추출된 구조조건 로그에 body_type/seats/accident_free가 등장하는지" 단언이 맡는다.
    여기서 실제로 고정되는 것은 (a) `AND (<조건>)` 조립 모양과 (b) 인용 접미사 문자열이다.
    """
    captured = {}
    # 가이드 매핑을 반영한 조건을 LLM이 냈다고 **가정한** 고정 응답(도출 자체는 검증 대상 아님).
    llm = _FixedLLM(["body_type IN ('중형차','SUV','RV')"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    _patch_guide_lookup(monkeypatch, [_GUIDE_ROW_WITHIN_CUTOFF])

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        return [_fake_row()]

    monkeypatch.setattr(node, "run_select", fake_run_select)
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("3천만원 이하로 무난한 패밀리카")

    assert "AND (body_type IN ('중형차','SUV','RV'))" in captured["sql"]
    # LLM이 답변 문장을 새로 짓지 않는다 — _ANSWER_FOUND 템플릿 + 결정론적 인용 접미사 그대로.
    assert result["answer"] == (
        "조건에 맞는 매물 1건을 찾았어요. (참고: 패밀리카로 무난한 차종 고르기)"
    )
