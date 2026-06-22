"""score_ab.py 순수 함수 단위테스트 — 라이브 API·DB 없이 채점 로직만 검증.

목적: Phase B 채점 하니스가 "조용히 틀리지" 않게 골든 SQL 빌더·집합 지표·사전식 승부·
  게이트 판정을 고정한다. 점수 리포트(라이브)는 score_ab.main이 별도로 낸다.
"""

import importlib.util
from pathlib import Path

# scripts/score_ab.py를 모듈로 직접 로드(scripts는 패키지가 아니므로).
_SPEC = importlib.util.spec_from_file_location(
    "score_ab", Path(__file__).resolve().parent.parent / "scripts" / "score_ab.py"
)
score_ab = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(score_ab)


# ── 골든 SQL 빌더 ──────────────────────────────────────────────────────
def test_golden_sql_basic_eq_and_cmp():
    sql, params = score_ab.build_golden_sql({"body_type": "SUV", "price_max": 30000000})
    assert sql.startswith("SELECT id FROM listings WHERE status = 'on_sale'")
    assert "body_type = %s" in sql
    assert "price <= %s" in sql
    assert "SUV" in params and 30000000 in params


def test_golden_sql_list_uses_any():
    sql, params = score_ab.build_golden_sql({"body_type": ["경차", "소형차", "준중형차"]})
    assert "body_type = ANY(%s)" in sql
    assert ["경차", "소형차", "준중형차"] in params


def test_golden_sql_options_all_and_order_limit():
    sql, params = score_ab.build_golden_sql(
        {"options_all": ["스마트키", "후방카메라"], "order": "price ASC", "limit": 1}
    )
    assert sql.count("= ANY(options)") == 2
    assert sql.rstrip().endswith("LIMIT %s")
    assert "ORDER BY price ASC" in sql
    assert params[-1] == 1  # limit이 마지막 파라미터


def test_golden_sql_rejects_bad_order():
    import pytest
    with pytest.raises(ValueError):
        score_ab.build_golden_sql({"order": "price; DROP TABLE listings"})


def test_golden_sql_accident_free_bool():
    sql, params = score_ab.build_golden_sql({"accident_free": True})
    assert "accident_free = %s" in sql
    assert True in params


# ── 집합 지표 ──────────────────────────────────────────────────────────
def test_jaccard():
    assert score_ab.jaccard({1, 2, 3}, {1, 2, 3}) == 1.0
    assert score_ab.jaccard(set(), set()) == 1.0
    assert score_ab.jaccard({1, 2}, {2, 3}) == 1 / 3


def test_prf_perfect_and_empty():
    p, r, f = score_ab.precision_recall_f1({1, 2, 3}, {1, 2, 3})
    assert (p, r, f) == (1.0, 1.0, 1.0)
    p, r, f = score_ab.precision_recall_f1(set(), set())
    assert (p, r, f) == (1.0, 1.0, 1.0)
    # 정답은 있는데 빈손 → 0
    p, r, f = score_ab.precision_recall_f1(set(), {1})
    assert f == 0.0


def test_score_path_a_precision_when_golden_large():
    # golden 10건(>LIMIT5), 반환 5건이 전부 정답 → precision 1.0
    golden = list(range(10))
    sc = score_ab.score_path_a([0, 1, 2, 3, 4], golden, {"body_type": "SUV"})
    assert sc["mode"] == "precision"
    assert sc["result"] == 1.0
    # 반환 5건 중 1건이 오답(99) → precision 0.8 (예산초과 차 혼입 잡힘)
    sc2 = score_ab.score_path_a([0, 1, 2, 3, 99], golden, {"body_type": "SUV"})
    assert abs(sc2["result"] - 0.8) < 1e-9


def test_score_path_a_topn_exact_order():
    sc = score_ab.score_path_a(["x"], ["x"], {"order": "price ASC", "limit": 1})
    assert sc["mode"] == "topn" and sc["result"] == 1.0
    sc2 = score_ab.score_path_a(["y"], ["x"], {"order": "price ASC", "limit": 1})
    assert sc2["result"] == 0.0


def test_route_ok_acceptable_paths():
    assert score_ab.route_ok("A", "A", ["A"])
    assert score_ab.route_ok("B", "A", ["A", "B"])  # 혼합 허용
    assert not score_ab.route_ok("C", "A", ["A", "B"])


def test_doc_hit_and_redirect():
    ans = "'초보' 매물 5건 (참고: 초보 운전자에게 적합한 차종)"
    assert score_ab.doc_hit(ans, ["03-초보운전자-적합-차종"])
    assert not score_ab.doc_hit(ans, ["02-패밀리카-적합-차종"])
    assert score_ab.is_redirect("예산·차종을 알려주시면 매물을 찾아드릴게요.")
    assert not score_ab.is_redirect("그냥 거절합니다.")


# ── 사전식 승부 ────────────────────────────────────────────────────────
def _summary(name, result_mean=0.9, routing=40, flaky=0, cost=0.01, lat=1000,
             gate=True):
    return {"name": name, "result_mean": result_mean, "routing_correct": routing,
            "flaky_n": flaky, "cost_usd": cost, "latency_ms_mean": lat, "gate_pass": gate}


def test_lexicographic_gate_first():
    a = _summary("A", gate=False)
    b = _summary("B", gate=True)
    v = score_ab.lexicographic_winner(a, b)
    assert v["winner"] == "B" and v["tier"] == "gate"


def test_lexicographic_result_dominates_cost():
    # A가 결과집합 크게 우위지만 비쌈 → 그래도 A 승(가중합 금지)
    a = _summary("A", result_mean=0.95, cost=0.10)
    b = _summary("B", result_mean=0.70, cost=0.01)
    v = score_ab.lexicographic_winner(a, b)
    assert v["winner"] == "A" and v["tier"] == "result"


def test_lexicographic_small_result_diff_falls_to_routing():
    # 결과집합 차 0.05(<0.15 임계) → 라우팅으로 넘어감
    a = _summary("A", result_mean=0.90, routing=30)
    b = _summary("B", result_mean=0.85, routing=40)
    v = score_ab.lexicographic_winner(a, b)
    assert v["winner"] == "B" and v["tier"] == "routing"


def test_lexicographic_tie_then_cost():
    # 결과·라우팅·flaky 동률 → 비용 싼 쪽
    a = _summary("A", cost=0.10)
    b = _summary("B", cost=0.03)
    v = score_ab.lexicographic_winner(a, b)
    assert v["winner"] == "B" and v["tier"] == "cost"
