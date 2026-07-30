"""score_ab.py 순수 함수 단위테스트 — 라이브 API·DB 없이 채점 로직만 검증.

목적: Phase B 채점 하니스가 "조용히 틀리지" 않게 골든 SQL 빌더·집합 지표·사전식 승부·
  게이트 판정을 고정한다. 점수 리포트(라이브)는 score_ab.main이 별도로 낸다.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

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


# ── 측정 안 된 축은 건너뛴다(review pass 4 — flaky_measured/tokens_measured) ──────
# run_phase_b.py(G2 baseline 러너)는 N=1이라 flaky_n이 항상 0이고 tokens는 하드코딩 0이다.
# 그 raw를 채점한 summary는 flaky_measured=False·tokens_measured=False를 달고 나오므로,
# 사전식 승부가 그 축을 "완벽함"으로 잘못 읽고 진짜 측정된 상대에게 자동으로 이기면 안 된다.
def test_lexicographic_flaky_axis_skipped_when_unmeasured_falls_through_to_cost():
    # A(baseline, N=1)는 flaky=0이지만 측정 안 됨 — 그대로면 flaky 축에서 A가 자동 승리한다.
    a = _summary("A", flaky=0, cost=0.05)
    a["flaky_measured"] = False
    b = _summary("B", flaky=5, cost=0.01)  # 실제 N=3으로 측정된 상대, flaky는 A보다 나쁨
    v = score_ab.lexicographic_winner(a, b)
    assert v["tier"] != "flaky"
    assert v["tier"] == "cost" and v["winner"] == "B"


def test_lexicographic_cost_axis_skipped_when_tokens_unmeasured_falls_through_to_latency():
    # A는 tokens_measured=False(하드코딩 0이라 cost_usd=0.001로 사실상 가짜로 저렴) — 그대로면
    # 비용 축에서 A가 자동 승리한다.
    a = _summary("A", cost=0.001, lat=2000)
    a["tokens_measured"] = False
    b = _summary("B", cost=1.0, lat=500)
    v = score_ab.lexicographic_winner(a, b)
    assert v["tier"] != "cost"
    assert v["tier"] == "latency" and v["winner"] == "B"


def test_lexicographic_two_file_mode_unchanged_when_both_sides_measured():
    """flaky_measured/tokens_measured 키가 아예 없는(기존 2파일 raw) 경우 회귀 없이 그대로
    flaky/cost 축을 쓴다 — 기본값 True가 옛 동작을 보존한다."""
    a = _summary("A", flaky=0, cost=0.10)
    b = _summary("B", flaky=2, cost=0.03)
    v = score_ab.lexicographic_winner(a, b)
    assert v["tier"] == "flaky" and v["winner"] == "A"


# ── CLI `--raw` 1개/2개 모드 (13.1 — G2 baseline) ──────────────────────
# 경로 C(거절) 질의 1건만 써서 score_model이 DB(경로 A 골든) 없이도 순수하게 도는 케이스로
# main()을 실제로 실행해 검증한다(라이브 호출·DB 연결 0).
_C_QUERYSET = {
    "items": [
        {
            "id": "C1", "kind": "single", "category": "clean",
            "query": "오늘 날씨 어때?", "primary_path": "C", "acceptable_paths": ["C"],
        },
    ],
}


def _raw(model: str) -> dict:
    return {
        "model": model,
        "results": {
            "C1": [
                {"route_last": "C", "ids_last": [], "answer_last": "그건 못 도와드려요.",
                 "tokens_in": 0, "tokens_out": 0, "latency_ms": 5.0},
            ],
        },
    }


def _write_json(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_cli_raw_single_file_mode_writes_baseline_summary_key(tmp_path, monkeypatch):
    """`--raw` 1개면 A/B 비교 없이 `{"baseline_summary": ...}`만 --out에 쓴다."""
    qs = _write_json(tmp_path / "qs.json", _C_QUERYSET)
    raw = _write_json(tmp_path / "raw.json", _raw("gemini-3.1-flash-lite"))
    out = tmp_path / "out.json"

    monkeypatch.setattr(sys, "argv", ["score_ab.py", "--queryset", qs, "--raw", raw, "--out", str(out)])
    score_ab.main()

    report = json.loads(out.read_text(encoding="utf-8"))
    assert "baseline_summary" in report
    assert report["baseline_summary"]["name"] == "gemini-3.1-flash-lite"
    # 2파일 모드 전용 키가 섞여 들어오지 않는다(타입이 바뀌는 API 금지 — Spec Change Log).
    assert "baseline" not in report
    assert "candidate" not in report
    assert "verdict" not in report


def test_cli_raw_two_file_mode_unchanged(tmp_path, monkeypatch):
    """기존 `--raw <a> <b>` 2파일 모드는 회귀 없이 그대로 동작한다(`baseline`=모델명 문자열)."""
    qs = _write_json(tmp_path / "qs.json", _C_QUERYSET)
    raw_a = _write_json(tmp_path / "raw_a.json", _raw("gemini-3.1-flash-lite"))
    raw_b = _write_json(tmp_path / "raw_b.json", _raw("gemini-2.5-flash-lite"))
    out = tmp_path / "out.json"

    monkeypatch.setattr(
        sys, "argv",
        ["score_ab.py", "--queryset", qs, "--raw", raw_a, raw_b, "--out", str(out)],
    )
    score_ab.main()

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["baseline"] == "gemini-3.1-flash-lite"  # 모델명 문자열(기존 동작 그대로)
    assert report["candidate"] == "gemini-2.5-flash-lite"
    assert "baseline_summary" not in report  # 1개 모드 전용 키가 섞여 들어오지 않는다


@pytest.mark.parametrize("raw_args", [[], ["a.json", "b.json", "c.json"]])
def test_cli_raw_invalid_count_exits_with_usage_error(tmp_path, monkeypatch, capsys, raw_args):
    """`--raw`가 1·2개가 아니면 ap.error로 종료코드 2 + 에러 메시지를 낸다."""
    qs = _write_json(tmp_path / "qs.json", _C_QUERYSET)
    argv = ["score_ab.py", "--queryset", qs, "--out", str(tmp_path / "out.json")]
    if raw_args:
        argv += ["--raw", *raw_args]
    else:
        argv += ["--raw"]  # argparse 자체가 인자 0개는 이미 별도로 거부(nargs='+')
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc_info:
        score_ab.main()
    assert exc_info.value.code == 2
    assert "--raw" in capsys.readouterr().err


# ── score_model 부분 실패 내구성(review pass 4) ─────────────────────────
# 44개 전량 실행 중 일부가 429로 `{"error": ...}`만 남기는 것(DW-554)이 정확히 이 시나리오다.
def test_score_model_skips_error_runs_without_crashing():
    """`r["route_last"]`를 무조건 인덱싱하던 옛 코드는 error run 1개만 섞여도 KeyError로
    죽어 이미 성공한 다른 item까지 채점이 통째로 불가능했다(코디네이터 실측 그대로 재현)."""
    qs = {"items": [{"id": "A1", "kind": "single", "category": "clean",
                     "query": "q", "primary_path": "C", "acceptable_paths": ["C"]}]}
    raw = {"model": "m", "results": {"A1": [{"error": "429 quota exceeded"}]}}
    summary = score_ab.score_model(qs, raw)  # 수정 전엔 여기서 KeyError
    assert summary["errored_n"] == 1
    assert summary["result_n"] == 0


def test_score_model_continues_scoring_other_items_when_one_errors():
    """error 항목이 하나 섞여도 나머지 정상 item은 그대로 채점된다."""
    qs = {"items": [
        {"id": "C1", "kind": "single", "category": "clean",
         "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]},
        {"id": "C2", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "C", "acceptable_paths": ["C"]},
    ]}
    raw = {
        "model": "m",
        "results": {
            "C1": [{"route_last": "C", "ids_last": [], "answer_last": "거절",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
            "C2": [{"error": "429 quota exceeded"}],
        },
    }
    summary = score_ab.score_model(qs, raw)
    assert summary["errored_n"] == 1
    assert summary["routing_correct"] == 1  # C1만 라우팅 채점 대상
    assert summary["routing_total"] == 1


def test_cli_raw_single_file_mode_survives_error_entries(tmp_path, monkeypatch):
    """44개 중 일부가 {"error": ...}인 raw를 1파일 모드로 CLI 전체 경로까지 태워도
    리포트가 실제로 만들어진다(DW-554 시나리오 — score_ab 1파일 모드 end-to-end)."""
    qs = _write_json(tmp_path / "qs.json", {
        "items": [
            {"id": "C1", "kind": "single", "category": "clean",
             "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]},
            {"id": "C2", "kind": "single", "category": "clean",
             "query": "q2", "primary_path": "C", "acceptable_paths": ["C"]},
        ],
    })
    raw = _write_json(tmp_path / "raw.json", {
        "model": "gemini-3.1-flash-lite",
        "results": {
            "C1": [{"route_last": "C", "ids_last": [], "answer_last": "거절",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
            "C2": [{"error": "429 quota exceeded"}],
        },
    })
    out = tmp_path / "out.json"

    monkeypatch.setattr(sys, "argv", ["score_ab.py", "--queryset", qs, "--raw", raw, "--out", str(out)])
    score_ab.main()  # 수정 전엔 KeyError로 죽어 --out 파일 자체가 안 만들어졌다

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["baseline_summary"]["errored_n"] == 1
    assert report["baseline_summary"]["routing_correct"] == 1


# ── score_model 커버리지(review pass 4) ─────────────────────────────────
def test_score_model_summary_reports_coverage_for_partial_capture():
    """44개 중 일부만 캡처된 raw는 그 사실(누락 id·개수)이 summary에 남아야 한다 —
    안 그러면 g2-baseline-partial.json(3/44)이 완전한 baseline처럼 보인다."""
    qs = {"items": [
        {"id": "A1", "kind": "single", "category": "clean",
         "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]},
        {"id": "B1", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "C", "acceptable_paths": ["C"]},
        {"id": "C1", "kind": "single", "category": "clean",
         "query": "q3", "primary_path": "C", "acceptable_paths": ["C"]},
        {"id": "D1", "kind": "single", "category": "clean",
         "query": "q4", "primary_path": "C", "acceptable_paths": ["C"]},
    ]}
    raw = {
        "model": "m",
        "results": {
            "A1": [{"route_last": "C", "ids_last": [], "answer_last": "x",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
            "B1": [{"route_last": "C", "ids_last": [], "answer_last": "x",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
        },
    }
    summary = score_ab.score_model(qs, raw)
    assert summary["coverage"]["queryset_total"] == 4
    assert summary["coverage"]["scored_n"] == 2
    assert summary["coverage"]["missing_ids"] == ["C1", "D1"]
    assert summary["is_partial"] is True


def test_score_model_full_capture_is_not_marked_partial():
    qs = {"items": [{"id": "A1", "kind": "single", "category": "clean",
                     "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]}]}
    raw = {"model": "m", "results": {
        "A1": [{"route_last": "C", "ids_last": [], "answer_last": "x",
                "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["is_partial"] is False
    assert summary["coverage"]["missing_ids"] == []


# ── flaky_measured/tokens_measured 집계(review pass 4, 재수정) ──────────
# tokens_measured는 run의 "tokens_measured" 키가 아니라 채점된 run 전체의 토큰 합계에서
# 직접 도출한다(합계가 0이면 미측정) — 그 키 유무와 무관하게 항상 옳아야 한다. 아래 두
# 테스트가 각각 "키가 있어도 무시하고 데이터로 판단" · "키가 아예 없는 구버전 raw도 옳게
# 판단"을 커버한다.
def test_score_model_marks_flaky_and_tokens_unmeasured_for_run_phase_b_style_raw():
    """N=1·토큰 0인 raw에 "tokens_measured" 키가 **있어도** 그 값을 믿지 않고 토큰 합계(0)로
    판단한다 — summary에 flaky_measured=False·tokens_measured=False가 찍힌다.
    (러너는 review pass 5부터 이 스탬프를 아예 찍지 않는다. 외부·구버전 raw가 찍어 보내도
     판단이 데이터에서 나온다는 것이 이 테스트가 잠그는 것이다.)"""
    qs = {"items": [{"id": "A1", "kind": "single", "category": "clean",
                     "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]}]}
    raw = {"model": "m", "results": {
        "A1": [{"route_last": "C", "ids_last": [], "answer_last": "x",
                "tokens_in": 0, "tokens_out": 0, "tokens_measured": False, "latency_ms": 1.0}],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["flaky_measured"] is False  # N=1이라 반복 실행 자체가 없었다
    assert summary["tokens_measured"] is False  # 토큰 합계 0에서 도출


def test_score_model_derives_tokens_unmeasured_for_committed_baseline_shape_without_flag():
    """실제 커밋된 `api/docs/g2-baseline-partial.json`은 `tokens_measured` 플래그가 생기기
    *전에* 캡처됐다 — 그 키 자체가 없다. 키 부재를 기본 True로 처리하면(구 버전 로직) 바로
    이 파일에서 $0.0000 비용이 실측처럼 cost 티어를 이겨버린다(코디네이터 실측: 커밋된
    파일을 score_model에 먹였더니 tokens_measured=True로 잘못 나왔고, lexicographic_winner가
    '비용 $0.0000 vs $0.0090'로 그 baseline 손을 들어줬다). 플래그 없이도 토큰 합계 0에서
    직접 도출해야 이 실제 파일에서도 옳게 판정된다.
    """
    qs = {"items": [
        {"id": "A1", "kind": "single", "category": "clean",
         "query": "q1", "primary_path": "C", "acceptable_paths": ["C"]},
        {"id": "B1", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "C", "acceptable_paths": ["C"]},
    ]}
    # g2-baseline-partial.json과 동일한 shape — tokens_in/out=0, "tokens_measured" 키 자체가 없다.
    baseline_raw = {
        "model": "gemini-3.1-flash-lite",
        "results": {
            "A1": [{"route_last": "C", "ids_last": [], "answer_last": "x",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
            "B1": [{"route_last": "C", "ids_last": [], "answer_last": "y",
                    "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
        },
    }
    baseline_summary = score_ab.score_model(qs, baseline_raw)
    assert "tokens_measured" not in baseline_raw["results"]["A1"][0]  # 플래그 없음을 재확인
    assert baseline_summary["tokens_measured"] is False  # 플래그가 아니라 합계(0)에서 도출

    # 실측 토큰이 있는 후보와 비교 — 조작된 $0.0000가 cost 티어를 이겨선 안 된다.
    candidate_summary = dict(baseline_summary)
    candidate_summary["name"] = "gemini-2.5-flash-lite"
    candidate_summary["cost_usd"] = 0.0090
    candidate_summary["tokens_measured"] = True
    candidate_summary["latency_ms_mean"] = baseline_summary["latency_ms_mean"] + 1  # 지연도 갈라둔다

    verdict = score_ab.lexicographic_winner(baseline_summary, candidate_summary)
    assert verdict["tier"] != "cost"


# ── review pass 5 — 게이트는 "측정됐다"까지 확인해야 한다 ────────────────
# 오염(contamination)·데드엔드(deadend)는 채점된 run이 하나도 없으면 구조적으로 0이다.
# 그래서 "위반 없음"만 보던 게이트는 아무것도 측정 안 한 캡처를 PASS로 통과시켰다 —
# 에픽 G2 게이트("baseline 이하면 에픽 미종료")가 그 값을 읽으므로 게이트가 무력화된다.
def _clean_single(rid: str) -> dict:
    return {"id": rid, "kind": "single", "category": "clean",
            "query": f"q{rid}", "primary_path": "C", "acceptable_paths": ["C"]}


def test_gate_fails_when_every_run_errored():
    """44건 전량이 429로 실패한 캡처는 PASS가 아니다(실측: 전엔 gate_pass=True였다)."""
    qs = {"items": [_clean_single("A1"), _clean_single("B1")]}
    raw = {"model": "m", "results": {
        "A1": [{"error": "429 quota"}],
        "B1": [{"error": "429 quota"}],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["errored_n"] == 2
    assert summary["coverage"]["scored_n"] == 0
    assert summary["gate_pass"] is False


def test_gate_fails_when_nothing_captured():
    """결과가 아예 비어 있는 raw도 PASS가 아니다."""
    qs = {"items": [_clean_single("A1")]}
    summary = score_ab.score_model(qs, {"model": "m", "results": {}})
    assert summary["coverage"]["scored_n"] == 0
    assert summary["gate_pass"] is False


def test_gate_still_passes_for_clean_full_capture():
    """반대 방향 고정 — 전량이 정상 채점되고 위반이 없으면 여전히 PASS다."""
    qs = {"items": [_clean_single("A1")]}
    raw = {"model": "m", "results": {
        "A1": [{"route_last": "C", "ids_last": [], "answer_last": "다시 검색해 보세요",
                "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["coverage"]["scored_n"] == 1
    assert summary["gate_pass"] is True


# ── review pass 5 — 멀티턴 채점 분기(러너 turns[]의 유일한 소비자) ────────
# 큐리셋 44건 중 9건이 멀티턴이고, 하드 오염 게이트(contamination)는 **오직** 이 분기에서만
# 올라간다. 그런데 이 분기를 보는 테스트가 하나도 없어, 턴 라우팅 집계·오염 게이트를
# 통째로 무력화해도 전량 green이었다.
def test_score_model_multiturn_counts_each_turn_and_fires_contamination(monkeypatch):
    # 오염 판정은 반환 id의 실제 속성을 DB에서 읽는다 — 단위테스트라 그 조회만 대체한다.
    monkeypatch.setattr(score_ab, "fetch_attrs",
                        lambda ids: [{"id": i, "body_type": "중형차", "price": 1} for i in ids])
    qs = {"items": [{
        "id": "M1", "kind": "multiturn", "category": "clean",
        "turns": [
            {"query": "q1", "primary_path": "A", "acceptable_paths": ["A"]},
            {"query": "q2", "primary_path": "A", "acceptable_paths": ["A"],
             "must_not_contain": ["중형차"]},
        ],
    }]}
    raw = {"model": "m", "results": {
        "M1": [{
            "route_last": "A", "ids_last": ["l9"], "answer_last": "a2",
            "turns": [
                {"route": "A", "ids": ["l1"], "answer": "a1"},
                {"route": "A", "ids": ["l9"], "answer": "a2"},  # 이전 턴 조건이 살아남음 = 오염
            ],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0,
        }],
    }}
    summary = score_ab.score_model(qs, raw)
    # 턴마다 라우팅을 센다 — item 하나가 아니라 턴 2개다.
    assert summary["routing_total"] == 2
    assert summary["routing_correct"] == 2
    # 2번째 턴이 must_not_contain을 위반했으므로 하드 오염 게이트가 올라가고 PASS가 깨진다.
    assert summary["contamination"] == 1
    assert summary["gate_pass"] is False
    assert summary["per_item"][0]["turns"][1]["contamination"] == ["l9: body_type=중형차 (금지)"]


def test_score_model_multiturn_route_mismatch_counted():
    """턴 라우팅 오답도 실제로 집계된다(route_ok를 True로 못박아도 안 잡히던 자리)."""
    qs = {"items": [{
        "id": "M2", "kind": "multiturn", "category": "clean",
        "turns": [
            {"query": "q1", "primary_path": "A", "acceptable_paths": ["A"]},
            {"query": "q2", "primary_path": "B", "acceptable_paths": ["B"]},
        ],
    }]}
    raw = {"model": "m", "results": {
        "M2": [{"route_last": "A", "ids_last": [], "answer_last": "a2",
                "turns": [{"route": "A", "ids": [], "answer": "a1"},
                          {"route": "A", "ids": [], "answer": "a2"}],  # B여야 하는데 A
                "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["routing_total"] == 2
    assert summary["routing_correct"] == 1


# ── review pass 5 — flaky_measured의 True 방향도 고정한다 ─────────────────
def test_flaky_measured_true_when_repeated_runs_present():
    """N>1로 실제 반복 실행된 raw면 flaky_measured가 True다.

    False 방향만 고정돼 있어서 이 플래그가 영영 False로 굳어도 아무 테스트가 안 잡혔다 —
    그러면 2파일 A/B 모드가 flaky 축(사전식 3순위)을 통째로 건너뛴다.
    """
    qs = {"items": [_clean_single("A1")]}
    raw = {"model": "m", "results": {
        "A1": [
            {"route_last": "C", "ids_last": ["l1"], "answer_last": "x",
             "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0},
            {"route_last": "C", "ids_last": ["l2"], "answer_last": "x",  # 서명이 달라 flaky
             "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0},
        ],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["flaky_measured"] is True
    assert summary["flaky_n"] == 1
