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

import pytest

import app.graph.graph as gmod
from app.db.sql_guard import MAX_LIMIT, SqlGuardError, validate_select_sql
from app.graph.guard_node import _GUARD_ANSWER, guard_node
from tests.demo_queries import GRAY_AB, SEMANTIC_B, STRUCTURED_A, UNRELATED_C


# ─────────────────────────────────────────────────────────────────────
# 공통 모킹 헬퍼 — 라우터를 고정 route로, 경로 노드를 추적용 가짜로 치환.
# (test_graph.py의 _patch_nodes와 동일 사상 — 여기선 OI5 판정에 맞춰 재사용.)
# ─────────────────────────────────────────────────────────────────────
def _patch_route(monkeypatch, route, *, sql_cards=None, doc_cards=None):
    """router를 고정 route로 강제하고, 경로 노드가 줄 매물 카드를 주입한다."""
    sql_cards = sql_cards if sql_cards is not None else [{"id": "s1"}]
    doc_cards = doc_cards if doc_cards is not None else [{"id": "d1"}]
    monkeypatch.setattr(gmod, "router_node", lambda q: route)
    monkeypatch.setattr(
        gmod, "sql_rag_node",
        lambda q: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": list(sql_cards)},
    )
    monkeypatch.setattr(
        gmod, "doc_rag_node",
        lambda q: {"answer": "추천 매물이에요.", "listings": list(doc_cards)},
    )
    # guard_node는 실제 함수를 그대로 둔다(거절 문구·빈 목록 검증을 위해).


# ═════════════════════════════════════════════════════════════════════
# SM3 — 경로 A·B 두 경로 모두 적절한 매물 카드를 반환한다 (AC1)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("query", STRUCTURED_A)
def test_sm3_pathA_returns_listings(monkeypatch, query):
    """① 구조형 질의 → 경로 A가 매물 카드(listings 비어있지 않음)를 돌려준다."""
    _patch_route(monkeypatch, "A")
    out = gmod.run_search(query)
    assert out["listings"], f"경로 A가 빈손이면 SM3 불합격: {query!r}"
    assert out["answer"].strip(), "answer가 비어 있으면 안 된다(FR17/계약)"


@pytest.mark.parametrize("query", SEMANTIC_B)
def test_sm3_pathB_returns_listings(monkeypatch, query):
    """② 질적·의미형 질의 → 경로 B가 추천 매물(listings 비어있지 않음)을 돌려준다."""
    _patch_route(monkeypatch, "B")
    out = gmod.run_search(query)
    assert out["listings"], f"경로 B가 빈손이면 SM3 불합격: {query!r}"
    assert out["answer"].strip()


@pytest.mark.parametrize("query", GRAY_AB)
@pytest.mark.parametrize("route", ["A", "B"])
def test_sm3_gray_zone_returns_listings_either_route(monkeypatch, query, route):
    """③ 회색지대 — A로 가든 B로 가든 매물/추천을 주면 합격(거절·빈손만 아니면 됨).

    ai-demo-queries.md ③: "둘 중 어디로 가도 매물 카드/추천을 돌려주면 데모 합격".
    경로를 한쪽으로 단정하지 않고 두 경우 모두 빈손이 아님을 확인한다(과잉 단정 금지).
    """
    _patch_route(monkeypatch, route)
    out = gmod.run_search(query)
    assert out["listings"], f"회색지대 {query!r}가 route={route}에서 빈손이면 불합격"


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
    """④ 무관 질의 → 경로 C: listings 빈 목록 + 검색 유도 거절 문구."""
    _patch_route(monkeypatch, "C")
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
    (예산·용도로 매물 찾기) 길을 열어 둔다. 단순 "못 한다" 종결이 아니어야 한다.
    """
    # 거절 멘트가 검색 재유도 정보(예산·용도/매물)를 담고 있어야 한다(부분문자열로 의도만 고정).
    assert "예산" in _GUARD_ANSWER
    assert "용도" in _GUARD_ANSWER
    assert "매물" in _GUARD_ANSWER


def test_cm1_count_all_unrelated_rejected(monkeypatch):
    """집계 단언 — 무관 질의 전부(N건)가 거절된다. 거절 실패 0건이어야 CM1 합격."""
    _patch_route(monkeypatch, "C")
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
