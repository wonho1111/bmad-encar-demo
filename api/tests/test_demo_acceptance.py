"""4.8 데모 합격 판정 — OI5 질의셋으로 SM3·CM1·CM2를 결정론적으로 통과/실패 판정한다.

이 파일은 "검증 자산"이다. 경로 A/B/C·sql_guard·graph는 4.3~4.6에서 이미 구현됐고,
여기서는 그것들이 OI5 데모 질의셋(`api/docs/ai-demo-queries.md`, tests/demo_queries.py) 기준으로
합격임을 **재현 가능한 테스트**로 못박는다.

쿼터 보호: 라이브 Gemini에 의존하지 않는다.
  · SM3/CM1 — 라우터·경로 노드를 모킹해 분기·계약을 LLM/DB 없이 검증.
  · CM2 — sql_guard는 순수 함수라 키 없이 항상 결정론적으로 검증.
라이브 동작 확인은 별도 스모크(test_live_smoke.py, 기본 skip)에서 소량만 한다.
[Source: story 4.8 AC1·AC2·AC3; api/docs/ai-demo-queries.md; tests/test_graph.py 모킹 패턴]
"""

import json
from pathlib import Path

import pytest

import app.graph.graph as gmod
from app.db.sql_guard import MAX_LIMIT, SqlGuardError, validate_select_sql
from app.graph.guard_node import _GUARD_ANSWER, guard_node
from tests.demo_queries import GRAY_ALLOWED, SEMANTIC_B, STRUCTURED_A, UNRELATED_C


# ─────────────────────────────────────────────────────────────────────
# 공통 모킹 헬퍼 — 라우터를 고정 route로, 경로 노드를 추적용 가짜로 치환.
# (test_graph.py의 _patch_nodes와 동일 사상 — 여기선 OI5 판정에 맞춰 재사용.)
# ─────────────────────────────────────────────────────────────────────
def _patch_route(monkeypatch, route, *, sql_cards=None, doc_cards=None, hybrid_cards=None):
    """router를 고정 route로 강제하고, 경로 노드가 줄 매물 카드를 주입한다."""
    sql_cards = sql_cards if sql_cards is not None else [{"id": "s1"}]
    doc_cards = doc_cards if doc_cards is not None else [{"id": "d1"}]
    hybrid_cards = hybrid_cards if hybrid_cards is not None else [{"id": "h1"}]
    monkeypatch.setattr(gmod, "router_node", lambda q: route)
    monkeypatch.setattr(
        gmod, "sql_rag_node",
        lambda q: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": list(sql_cards)},
    )
    monkeypatch.setattr(
        gmod, "doc_rag_node",
        lambda q: {"answer": "추천 매물이에요.", "listings": list(doc_cards)},
    )
    # HYBRID(Story 13.3부터 hybrid_rag_node로 실배선)도 sql_rag_node·doc_rag_node와 동일하게
    # 모킹한다 — 안 그러면 route="HYBRID"를 강제할 때 실제 LLM/DB를 호출하게 된다(회귀).
    monkeypatch.setattr(
        gmod, "hybrid_rag_node",
        lambda q: {"answer": "조합 조건에 맞는 매물이에요.", "listings": list(hybrid_cards)},
    )
    # CLARIFY(Story 13.4부터 clarify_node로 실배선) — 고정 템플릿이라 카드 대신 clarify 페이로드를
    # 준다. 이 파일은 run_search를 context 없이 부르므로 clarify_turns가 0으로 계산돼(상한 이내)
    # 언제나 clarify_node가 불린다 — 강제 폴백 분기는 여기서 검증하지 않는다(test_graph.py 소관).
    monkeypatch.setattr(gmod, "clarify_node", lambda q: {
        "answer": "조건을 조금만 좁혀볼게요.",
        "listings": [],
        "clarify": {"question": "조건을 조금만 좁혀볼게요.", "chips": ["a", "b", "c"]},
    })
    # guard_node는 실제 함수를 그대로 둔다(거절 문구·빈 목록 검증을 위해).


# ═════════════════════════════════════════════════════════════════════
# SM3 — 경로 A·B 두 경로 모두 적절한 매물 카드를 반환한다 (AC1)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("query", STRUCTURED_A)
def test_sm3_pathA_returns_listings(monkeypatch, query):
    """① 구조형 질의 → 경로 SQL이 매물 카드(listings 비어있지 않음)를 돌려준다."""
    _patch_route(monkeypatch, "SQL")
    out = gmod.run_search(query)
    assert out["listings"], f"경로 SQL이 빈손이면 SM3 불합격: {query!r}"
    assert out["answer"].strip(), "answer가 비어 있으면 안 된다(FR17/계약)"


@pytest.mark.parametrize("query", SEMANTIC_B)
def test_sm3_pathB_returns_listings(monkeypatch, query):
    """② 질적·의미형 질의 → 경로 CLARIFY가 매물 대신 되묻기(clarify 페이로드)를 돌려준다.

    ✎ 13.4: CLARIFY는 더는 doc_rag_node 임시 배선(구 B 그대로 매물 반환)이 아니다 — 되묻기
    상한 이내(이 헬퍼는 단일턴 가정)이면 clarify_node가 고정 질문+칩을 반환하고 listings는
    항상 []다. "빈손이 SM3 불합격"이라는 옛 기준은 clarify가 없는 진짜 빈손(dead-end)에만
    해당한다 — clarify 칩은 "누를 수 있는 다음 행동"이라 dead-end가 아니므로, SM3 판정
    기준을 listings 비어있지 않음에서 clarify 페이로드가 채워짐으로 옮긴다.
    """
    _patch_route(monkeypatch, "CLARIFY")
    out = gmod.run_search(query)
    assert out["listings"] == []
    assert out["clarify"] is not None, f"경로 CLARIFY가 clarify 없이 빈손이면 SM3 불합격: {query!r}"
    assert out["clarify"]["chips"]
    assert out["answer"].strip()


# 큐리셋의 단일턴 `category: gray` 항목 중 표 ③에 **싣지 않기로 한 것**. R7·R8은 지식형
# 질문이라 문서에선 표 ④(REJECT)가 다룬다. 큐리셋에 새 gray 질의가 들어오면 아래 검사가
# red가 되어 "표 ③에 넣을지 여기 적을지"를 강제로 결정하게 만든다 — 그냥 두면 새 질의가
# 결정론 게이트에서 영원히 안 보인다.
_GRAY_NOT_IN_DOC_TABLE = frozenset({"R7", "R8"})


def test_gray_allowed_matches_shipped_queryset():
    """`GRAY_ALLOWED` ↔ 큐리셋 `acceptable_paths`가 어긋나면 red(양방향).

    13.8 후속리뷰가 `GRAY_ALLOWED`를 큐리셋과 1:1로 맞췄지만 강제하는 검사는 없어서,
    "지금은 맞다"는 산문 주장뿐이었다(스펙 잔여 리스크가 "표면이 3행뿐이라 과설계"라 적었으나
    큐리셋 로더는 `test_ab_scoring.py`에 이미 있어 3줄이면 된다 — B9). 바로 다음 스토리
    13.9가 라우팅을 바꾸며 `acceptable_paths`를 좁히면 이 사본만 옛 집합을 계속 정답으로
    단언하고 양쪽 다 초록이다 — 방금 없앤 "허용 밖 경로가 합격" 결함이 그대로 되살아난다.

    ✎ 13.8 4차 리뷰 — 원래 이 검사는 큐리셋을 `if it.get("query") in GRAY_ALLOWED`로 **먼저
      걸러서** 기대집합을 만들었다. 그래서 `GRAY_ALLOWED`에서 행을 지우면 양쪽이 같이 줄어
      초록이었고(3행→1행이어도 전량 초록, 3개 리뷰 레이어가 각각 뮤테이션으로 실증), 큐리셋에
      gray 질의가 추가돼도 초록이었다. 즉 이 검사가 막겠다고 적어 둔 두 방향 중 잡히는 건
      "기존 행의 허용 경로가 좁아지는" 한 방향뿐이었다. 지금은 큐리셋에서 gray 항목을
      **독립적으로** 뽑아 세 방향을 전부 본다(행 수는 `demo_queries.py`가 import 시점에 고정).

    ⚠️ 이 검사가 대조하는 것은 **두 곳**(`GRAY_ALLOWED` ↔ 큐리셋)뿐이다. `ai-demo-queries.md`
      표 ③은 어떤 코드도 읽지 않으므로 사람이 함께 고쳐야 한다(문서는 기계가 안 읽는다).
    """
    queryset = json.loads(
        (Path(__file__).resolve().parent.parent / "docs" / "ai-ab-test-queryset.json")
        .read_text(encoding="utf-8")
    )
    # 멀티턴 item은 `query` 대신 `turns`를 갖는다 — 회색지대 표 ③ 3행은 전부 단일턴이다.
    gray_by_query = {
        it["query"]: it
        for it in queryset["items"]
        if it.get("category") == "gray" and "query" in it
    }

    # ① 표 ③의 모든 행이 큐리셋에 gray 항목으로 실재한다(문자열 드리프트·오타를 잡는다).
    missing = set(GRAY_ALLOWED) - set(gray_by_query)
    assert not missing, f"표 ③ 질의가 큐리셋의 gray 항목에 없다: {sorted(missing)}"

    # ② 허용 경로가 정확히 일치한다(13.9가 acceptable_paths를 좁히면 여기서 red).
    assert {q: set(r) for q, r in GRAY_ALLOWED.items()} == {
        q: set(gray_by_query[q]["acceptable_paths"]) for q in GRAY_ALLOWED
    }, (
        "GRAY_ALLOWED가 큐리셋 acceptable_paths와 어긋났다 — "
        "ai-demo-queries.md 표 ③까지 세 곳을 함께 고쳐야 한다"
    )

    # ③ 반대 방향 — 큐리셋에 새 gray 질의가 생겼는데 표 ③에도 예외 목록에도 없으면 red.
    undocumented = {
        it["id"]
        for q, it in gray_by_query.items()
        if q not in GRAY_ALLOWED and it["id"] not in _GRAY_NOT_IN_DOC_TABLE
    }
    assert not undocumented, (
        f"큐리셋에 표 ③에 없는 gray 질의가 있다: {sorted(undocumented)} — "
        "표 ③(+GRAY_ALLOWED)에 넣거나 _GRAY_NOT_IN_DOC_TABLE에 사유와 함께 적어라"
    )


# 행 수·허용경로 비어있음 검사는 `demo_queries.py`가 `GRAY_ALLOWED` 바로 옆에서 import 시점에
# 건다(13.8 4차 리뷰 — 사본을 늘리지 않으려 이 자리의 중복 assert를 그리로 옮겼다).


@pytest.mark.parametrize(
    "query,route",
    [(q, r) for q, routes in GRAY_ALLOWED.items() for r in routes],
)
def test_sm3_gray_zone_allowed_routes_are_not_dead_ends(monkeypatch, query, route):
    """③ 회색지대 — 질의별 허용 경로에서만 "빈손·무응답이 아니다"를 확인한다.

    허용 경로는 `demo_queries.GRAY_ALLOWED`가 갖고, 그건 ai-demo-queries.md 표 ③의
    "기대 분류" 칸과 1:1이다. SQL/HYBRID는 매물 카드를, CLARIFY는 되묻기 칩을, REJECT는
    고정 거절 문구+빈 목록을 줘야 합격이다.
    ✎ 13.4: CLARIFY의 "빈손 아님"은 listings가 아니라 clarify 칩으로 판정한다(되묻기 칩=
    누를 수 있는 다음 행동이라 dead-end가 아니다, EXPERIENCE.md 칩=타이핑과 동등 경로).
    ✎ 13.8: 지식형 질의("주행거리 많은 차 사도 괜찮을까?")는 CLARIFY·REJECT 둘 다 정답이라
    REJECT 분기를 넣었다.
    ✎ 13.8 후속리뷰: 그때 넣은 방식이 질의×경로 **교차곱**이라, 문서가 오답이라 못박은 조합
    (지식형 질의가 매물 목록을 주는 것, 가격·인승이 명시된 H6/H7이 거절로 새는 것)까지
    합격으로 단언하고 있었다 — 그 조합이면 게이트가 진짜 회귀를 못 잡는다. 질의별 허용
    경로로 좁혔다.

    ✎ 13.8 3차 리뷰: SQL·HYBRID 두 경로가 `assert out["listings"]` 한 줄을 공유해서,
    `conditional_edges`가 "HYBRID" → sql 노드로 잘못 배선돼도 6/6 초록이었다 —
    epic 컨텍스트가 "신규 라우트가 기존 분기에 조용히 흡수되는 회귀"라 경고한 바로 그
    실패 모드다. `_patch_route`가 노드별로 다른 카드 id를 주입하므로 그 id를 단언한다.

    ⚠️ 이 테스트가 보지 못하는 것: 라우트는 `_patch_route`가 강제 주입하므로 **실제 라우터가
    이 질의를 어디로 보내는지는 검증하지 않는다**(그 구조적 공백은 열린 항목 DW-576).
    여기서 지키는 건 "각 허용 경로의 응답 조립이 빈손/무응답이 아니고, 그 경로의 노드가
    실제로 불렸다"까지다. 실제 라우팅은 라이브 스모크(`test_live_smoke.py`)와 G2 재캡처가 본다.
    """
    _patch_route(monkeypatch, route)
    out = gmod.run_search(query)
    if route == "CLARIFY":
        assert out["clarify"] is not None, f"회색지대 {query!r}가 CLARIFY에서 clarify 없이 빈손이면 불합격"
        assert out["clarify"]["chips"]
    elif route == "REJECT":
        assert out["listings"] == [], f"회색지대 {query!r}가 REJECT에서 매물을 주면 불합격"
        assert out["answer"] == _GUARD_ANSWER, "REJECT는 고정 거절 문구(_GUARD_ANSWER)를 내보내야 한다"
    else:
        assert out["listings"], f"회색지대 {query!r}가 route={route}에서 빈손이면 불합격"
        # 어느 노드가 응답을 만들었는지까지 본다 — _patch_route의 카드 id가 노드별로 다르다.
        expected_id = {"SQL": "s1", "HYBRID": "h1"}[route]
        assert out["listings"][0]["id"] == expected_id, (
            f"route={route}인데 {out['listings'][0]['id']!r} 노드가 응답했다 — 분기 배선 회귀"
        )


def test_sm3_pathA_real_guard_passes_generated_sql(monkeypatch):
    """경로 A 내부 LLM만 모킹 — 현실적 SELECT 생성 → sql_guard 실제 통과 → 매핑까지 도달.

    4.3 deferred("IN-매핑 가드 통과 미커버") 보강: 가드가 정상 SQL을 막지 않음을 증명한다.
    LLM(`_llm`)과 DB(`run_select`)만 가짜로 치환하고, validate_select_sql은 실제로 돈다.
    """
    import app.graph.sql_rag_node as sql_mod

    # 세단 IN-매핑 + status='on_sale' + 12컬럼(Story 10.1 — fuel·신뢰속성 3필드, Story 10.3 —
    # options 포함)을 갖춘 현실적 SQL(가드를 실제로 통과해야 함).
    generated = (
        "SELECT id, manufacturer, model, year, price, mileage, region, "
        "fuel, accident_status, is_single_owner, is_non_smoker, options "
        "FROM listings WHERE status = 'on_sale' "
        "AND body_type IN ('준중형차','중형차','대형차') AND price <= 30000000"
    )

    class _Msg:
        content = generated

    class _FakeLLM:
        def invoke(self, messages):
            return _Msg()

    captured = {}

    def _fake_run_select(sql):
        captured["sql"] = sql  # 가드를 통과한 안전 SQL을 캡처
        # DB 결과 1행(SELECT_COLUMNS 순서) — 매핑이 ListingCard로 떨어지는지 확인.
        return [("uuid-1", "현대", "쏘나타", 2021, 25000000, 41000, "서울", "가솔린", None, None, None, None)]

    monkeypatch.setattr(sql_mod, "_llm", lambda: _FakeLLM())
    monkeypatch.setattr(sql_mod, "run_select", _fake_run_select)

    out = sql_mod.sql_rag_node("3천만원 이하 세단")
    # 가드가 IN-매핑 SQL을 막지 않고 통과시켰다 → DB 호출까지 도달.
    assert "sql" in captured, "가드가 정상 SQL을 차단하면 안 된다(SM3 경로 A 회귀)"
    assert "body_type in" in captured["sql"].lower()
    assert "limit" in captured["sql"].lower()  # LIMIT 미지정 → 기본 LIMIT 주입됨
    assert len(out["listings"]) == 1
    assert out["listings"][0].manufacturer == "현대"


# ═════════════════════════════════════════════════════════════════════
# CM1 — 무관 질의는 전부 정중히 거절된다 (AC2)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("query", UNRELATED_C)
def test_cm1_unrelated_rejected_via_graph(monkeypatch, query):
    """④ 무관 질의 → 경로 REJECT(구 C): listings 빈 목록 + 검색 유도 거절 문구."""
    _patch_route(monkeypatch, "REJECT")
    out = gmod.run_search(query)
    assert out["listings"] == [], f"무관 질의에 매물을 주면 CM1 불합격: {query!r}"
    # 거절 문구는 고정 상수(_GUARD_ANSWER)와 "정확히 일치"해야 한다 — 부분문자열 검사보다 강한 단언.
    # 부분문자열("중고차"·"어시스턴트")만 보면 문구가 바뀌어도 조용히 통과해 거절 계약을 못 박는다(코드리뷰 4.8).
    assert out["answer"] == _GUARD_ANSWER, (
        "그래프 경로 C는 고정 거절 문구(_GUARD_ANSWER)를 그대로 내보내야 한다(FR16)"
    )


@pytest.mark.parametrize("query", UNRELATED_C)
def test_cm1_guard_node_is_deterministic(query):
    """guard_node 직접 — 어떤 무관 질의든 동일한 고정 거절 + 빈 목록(결정론적)."""
    out = guard_node(query)
    assert out["listings"] == []
    assert out["answer"] == _GUARD_ANSWER  # 질의 내용과 무관하게 고정 문구


def test_cm1_decline_is_not_dead_end():
    """거절 문구는 "막다른 길"이 아니라 "갈림길"이어야 한다 — 사용자를 매물 검색으로 재유도.

    party-mode 2026-06-23 결정(dead-end 0%): 거절하더라도 사용자가 다음에 무엇을 하면 되는지
    (조건을 알려주면 매물을 찾아준다) 길을 열어 둔다. 단순 "못 한다" 종결이 아니어야 한다.

    13.5: 문구가 EXPERIENCE.md Voice 표("AI 거절(FR47, 고정)")로 정정되며 예산·용도 대신
    "조건"으로 재유도 정보를 묶었다(car-condition 축 통합) — 의도(dead-end 0%)는 그대로이므로
    이 검사도 새 핵심어로 갱신한다. score_ab.py의 REDIRECT_MARKERS(is_redirect, G1 게이트)가
    보는 "매물을 찾아드릴게요" 부분문자열도 함께 고정한다.
    """
    # 거절 멘트가 검색 재유도 정보(조건/매물)를 담고 있어야 한다(부분문자열로 의도만 고정).
    assert "조건" in _GUARD_ANSWER
    assert "매물" in _GUARD_ANSWER
    assert "매물을 찾아드릴게요" in _GUARD_ANSWER
    # 13.5 2차 코드리뷰: 스펙의 최강 제약("EXPERIENCE.md Voice 표와 글자 그대로 일치")을 어느 검사도
    # 지키지 않아, 문구를 리워드해도 전 스위트가 초록이었다(실측). markdown을 파싱하는 golden 검사는
    # 과설계라 채택하지 않고(1차 리뷰 판단 유지), 정본 문자열 자체를 리터럴로 못박는다 — 문구 변경이
    # "조용한 드리프트"가 아니라 "두 곳을 같이 고치는 의도적 편집"이 되게 한다.
    # 정본: _bmad-output/planning-artifacts/ux-designs/.../EXPERIENCE.md Voice 표 "AI 거절(FR47, 고정)" 행.
    assert _GUARD_ANSWER == (
        "저는 중고차 찾기를 도와드리는 차장님이에요 🚗 "
        "그건 답하기 어렵지만, 원하는 차 조건을 말씀해 주시면 딱 맞는 매물을 찾아드릴게요."
    )


def test_cm1_count_all_unrelated_rejected(monkeypatch):
    """집계 단언 — 무관 질의 전부(N건)가 거절된다. 거절 실패 0건이어야 CM1 합격."""
    _patch_route(monkeypatch, "REJECT")
    not_rejected = []
    for q in UNRELATED_C:
        out = gmod.run_search(q)
        # 빈 목록 + 고정 거절 문구(정확 일치)를 모두 만족해야 "거절됨"으로 센다(코드리뷰 4.8).
        rejected = (out["listings"] == []) and (out["answer"] == _GUARD_ANSWER)
        if not rejected:
            not_rejected.append(q)
    assert not_rejected == [], f"거절되지 않은 무관 질의(CM1 위반): {not_rejected}"


# ═════════════════════════════════════════════════════════════════════
# CM2 — 범위밖·위험 SQL은 단 1건도 실행되지 않는다 (AC3)
#       sql_guard는 순수 함수 → LLM 불필요, 항상 결정론적으로 완전 검증.
# ═════════════════════════════════════════════════════════════════════
# 실행되면 안 되는 위반 SQL 코퍼스 — 각각 validate_select_sql이 raise해야 한다.
# (연구 §4.2 + ai-demo-queries.md 안전장치 사상. 카테고리별 최소 1건씩.)
VIOLATING_SQL = [
    # DML/DDL
    "DELETE FROM listings WHERE id = '1'",
    "UPDATE listings SET price = 0 WHERE status='on_sale'",
    "INSERT INTO listings (id) VALUES ('x')",
    "DROP TABLE listings",
    "ALTER TABLE listings ADD COLUMN x int",
    "TRUNCATE listings",
    # 다중문장(스태킹)
    "SELECT id FROM listings WHERE status='on_sale'; DROP TABLE listings",
    # 주석
    "SELECT id FROM listings WHERE status='on_sale' -- 주석",
    "SELECT id FROM listings WHERE status='on_sale' /* x */",
    # SELECT *
    "SELECT * FROM listings WHERE status='on_sale'",
    # 비화이트리스트 테이블
    "SELECT id FROM profiles WHERE status='on_sale'",
    # 환각 컬럼
    "SELECT password FROM listings WHERE status='on_sale'",
    # OR 우회(sold 누출)
    "SELECT id, manufacturer, model, year, price, mileage, region "
    "FROM listings WHERE status = 'on_sale' OR price < 99999999",
    # 서브쿼리 — 중첩 SELECT는 무조건 차단(subquery_not_allowed). 내부 LIMIT의 외부 상한 우회
    # 여지를 애초에 없앤다(SELECT 2개 이상이면 LIMIT 검사 전에 먼저 거부됨).
    "SELECT id, manufacturer, model, year, price, mileage, region "
    "FROM listings WHERE status='on_sale' AND year IN (SELECT year FROM listings LIMIT 50)",
    # status='on_sale' 필터 누락
    "SELECT id FROM listings WHERE color='흰색'",
    # sold만 — on_sale 필터 아님
    "SELECT id FROM listings WHERE status='sold'",
    # LIMIT 상한 초과
    f"SELECT id FROM listings WHERE status='on_sale' LIMIT {MAX_LIMIT + 1}",
    # 빈 입력
    "   ",
]


@pytest.mark.parametrize("sql", VIOLATING_SQL)
def test_cm2_violating_sql_is_blocked(sql):
    """각 위반 SQL은 실행 전에 SqlGuardError로 차단된다(CM2)."""
    with pytest.raises(SqlGuardError):
        validate_select_sql(sql)


def test_cm2_zero_violations_pass_through():
    """집계 단언 — 위반 SQL 코퍼스 전체에서 '가드를 통과한 건수 == 0'.

    'SELECT 전용·범위 제한을 벗어나는 쿼리가 0건 실행된다'(CM2)를 코드로 못박는다.
    하나라도 통과(반환)하면 그 SQL이 실행될 수 있다는 뜻이므로 즉시 불합격.
    """
    passed_through = []
    for sql in VIOLATING_SQL:
        try:
            validate_select_sql(sql)
            passed_through.append(sql)  # 차단되지 않고 통과 → CM2 위반
        except SqlGuardError:
            pass  # 정상 — 차단됨
    assert passed_through == [], (
        f"가드를 통과한 위반 SQL {len(passed_through)}건(CM2 위반, 0건이어야 함): {passed_through}"
    )


def test_cm2_valid_sql_still_passes():
    """대조군 — 정상 SELECT(7컬럼·status='on_sale')는 가드를 통과한다.

    CM2가 '전부 막기'가 아니라 '범위밖만 막기'임을 보장(정상까지 막으면 SM3가 깨진다).
    """
    good = (
        "SELECT id, manufacturer, model, year, price, mileage, region "
        "FROM listings WHERE status = 'on_sale' AND color = '흰색' AND body_type = 'SUV'"
    )
    safe = validate_select_sql(good)
    assert "limit" in safe.lower()  # LIMIT 주입 포함 정규화 SQL 반환
