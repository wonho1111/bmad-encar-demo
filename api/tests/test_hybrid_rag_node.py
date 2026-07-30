"""hybrid_rag_node 단위 테스트 — 네트워크(LLM)·DB 무관, 조립·폴백·가드 재시도 배선만 검증
(spec-13-3-하이브리드-검색-sql-벡터.md Tasks).

실제 생성·실행(라이브 LLM+DB)은 dev-story 라이브 스모크(test_live_smoke.py)에서 확인한다.
여기서는 결정론적인 부분만 격리해 테스트한다:
  (1) 조립 SQL이 기대 모양(status='on_sale' AND <조건> ORDER BY embedding <=> %s::vector
      LIMIT 5)인지
  (2) NONE 응답 시 doc_rag_node가 정확히 1회 호출되고 그 반환값이 그대로 나오는지
  (3) 가드 차단 1회 후 재생성 성공 경로
  (4) 2회 연속 차단 시 SqlGuardError가 그대로 전파되는지
  (5) run_select가 (qvec,) params와 함께 호출되는지(임베딩 바인딩 배선 검사, DW-559)
"""

import pytest

import app.graph.hybrid_rag_node as node
import app.graph.listing_cards as listing_cards
from app.db.sql_guard import DEFAULT_LIMIT, SqlGuardError

_LISTING_ID = "55555555-5555-4555-8555-555555555555"


def _fake_row():
    return (
        _LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원",
        "가솔린", None, None, None, None,
    )


class _FixedLLM:
    """미리 정해둔 응답을 순서대로 돌려주는 가짜 LLM(네트워크·과금 없음)."""

    def __init__(self, outputs):
        self._outputs = list(outputs)

    def invoke(self, messages):
        text = self._outputs.pop(0)
        return type("Msg", (), {"content": text})()


# ── (1) 조립 SQL 모양 + (5) run_select 임베딩 바인딩 배선 ─────────────────
def test_hybrid_assembles_expected_sql_and_binds_embedding_params(monkeypatch):
    captured = {}

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.5, -0.25])

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
    calls = {"doc": 0}

    def fake_doc(query):
        calls["doc"] += 1
        return {"answer": "DOC 결과", "listings": ["d1"]}

    # 대소문자 무관·공백 트림 확인 — 소문자·앞뒤 공백이 섞여도 폴백해야 한다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM([" none "]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)

    result = node.hybrid_rag_node("패밀리카로 무난한 거")

    assert calls["doc"] == 1
    assert result == {"answer": "DOC 결과", "listings": ["d1"]}


# ── 빈/공백 응답도 NONE과 동일하게 폴백(review patch 2) ────────────────
def test_hybrid_blank_condition_falls_back_to_doc_rag_node(monkeypatch):
    calls = {"doc": 0}

    def fake_doc(query):
        calls["doc"] += 1
        return {"answer": "DOC 결과", "listings": ["d1"]}

    # LLM이 공백만 있는 응답을 내도(정확히 "NONE"이 아니어도) 폴백해야 한다 — 안 그러면
    # `AND ()`라는 깨진 SQL이 가드는 통과(status='on_sale' AND항만으로 충족)하고 실행
    # 단계에서 psycopg 문법 오류로 죽는다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["   "]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)

    result = node.hybrid_rag_node("패밀리카로 무난한 거")

    assert calls["doc"] == 1
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
    calls = {"doc": 0}

    def fake_doc(query):
        calls["doc"] += 1
        return {"answer": "DOC 결과", "listings": ["d1"]}

    # 정확히 "NONE"만 인식하면 `NONE.`은 조건으로 조립돼 가드에 forbidden_column으로
    # 걸리고(실측), 폴백이 아니라 400이 나간다 — 의도한 경로가 통째로 사라진다.
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM([raw]))
    monkeypatch.setattr(node, "doc_rag_node", fake_doc)

    assert node.hybrid_rag_node("패밀리카로 무난한 거") == {
        "answer": "DOC 결과", "listings": ["d1"],
    }
    assert calls["doc"] == 1


# ── 가드는 통과하지만 실행 불가한 조건 → 재시도, 최종 실패는 400 계약 유지(review-2 patch) ──
def test_hybrid_unexecutable_condition_retries_then_raises_sql_guard_error(monkeypatch):
    import psycopg

    # `WHERE price <= N`은 가드를 **통과**한다(실측) — 조각이 `AND (...)` 안에 들어가
    # 토큰 검사만으로는 문법 오류가 안 보인다. 실행 단계에서야 psycopg가 죽는다.
    llm = _FixedLLM(["WHERE price <= 30000000", "AND price <= 30000000"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])

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

    def down(sql, params=None):
        raise psycopg.OperationalError("connection failed")

    monkeypatch.setattr(node, "run_select", down)

    with pytest.raises(psycopg.OperationalError):
        node.hybrid_rag_node("아무 질의")


# ── (3) 가드 차단 1회 후 재생성 성공 ────────────────────────────────────
def test_hybrid_guard_rejection_retries_once_then_succeeds(monkeypatch):
    # 1차: OR 포함 조건(가드가 forbidden_or로 거부) → 2차: 정상 조건.
    llm = _FixedLLM(["price < 1 OR price > 0", "body_type = 'SUV'"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [_fake_row()])
    monkeypatch.setattr(listing_cards, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("아무 질의")

    assert result["listings"]


# ── (4) 2회 연속 가드 차단 → SqlGuardError 전파 ─────────────────────────
def test_hybrid_guard_rejection_twice_propagates_sql_guard_error(monkeypatch):
    llm = _FixedLLM(["price < 1 OR price > 0", "price < 1 OR price > 0"])
    monkeypatch.setattr(node, "_llm", lambda: llm)
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])

    with pytest.raises(SqlGuardError) as exc:
        node.hybrid_rag_node("아무 질의")
    assert exc.value.code == "forbidden_or"


# ── 0건일 때 FR17 안내 문구를 쓰는지(sql_rag_node와 동일 톤) ─────────────
def test_hybrid_empty_result_uses_fr17_message(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(["body_type = 'SUV'"]))
    monkeypatch.setattr(node, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(node, "run_select", lambda sql, params=None: [])

    result = node.hybrid_rag_node("절대 없을 조건")

    assert result["listings"] == []
    assert "없어요" in result["answer"]
