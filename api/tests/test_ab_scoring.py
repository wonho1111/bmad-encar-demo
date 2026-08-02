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
    # 큐리셋 골든 라벨과 actual이 같은 신 4값 어휘를 쓰므로 번역 없이 그대로 비교한다(DW-609).
    assert score_ab.route_ok("SQL", "SQL", ["SQL"])
    assert score_ab.route_ok("CLARIFY", "REJECT", ["REJECT", "CLARIFY"])  # gray 혼합 허용
    assert not score_ab.route_ok("REJECT", "SQL", ["SQL", "HYBRID"])


def test_route_ok_honors_every_acceptable_list_element():
    # 허용집합은 primary와 acceptable 원소 **전부**의 합집합이다 — 첫 원소만 보는 회귀 방지.
    assert score_ab.route_ok("HYBRID", "SQL", ["SQL", "HYBRID"])
    assert score_ab.route_ok("CLARIFY", "REJECT", ["REJECT", "CLARIFY"])


# ── 어휘 통일 후의 엄격성 (DW-609) ────────────────────────────────────
# 구 버전은 legacy `A`를 `{"SQL","HYBRID"}` 집합으로 일괄 번역했다(DW-572/575). 그 확장은
# "옛 A 질의를 HYBRID로 정확히 분류한 것"을 살려주는 대신, **진짜 구조형 질의를 HYBRID로
# 오분류하는 버그까지 정답으로 세어** 가려버렸다(당시 문서화된 트레이드오프). 큐리셋이
# 신어휘로 옮겨진 지금은 그 일괄 확장이 필요 없으므로 라우팅을 다시 엄격하게 본다 —
# 두 경로가 모두 타당한 케이스는 큐리셋의 acceptable_paths로 **문항별로** 명시한다.
def test_route_ok_sql_label_does_not_silently_accept_hybrid():
    assert score_ab.route_ok("SQL", "SQL", ["SQL"])
    assert not score_ab.route_ok("HYBRID", "SQL", ["SQL"])
    # 반대 방향도 마찬가지 — HYBRID 문항을 SQL로 처리하면 가이드가 안 쓰인 것이므로 오답이다.
    assert not score_ab.route_ok("SQL", "HYBRID", ["HYBRID"])
    assert not score_ab.route_ok("HYBRID", "CLARIFY", ["CLARIFY"])
    assert not score_ab.route_ok("HYBRID", "REJECT", ["REJECT"])


def test_doc_hit_and_redirect():
    ans = "'초보' 매물 5건 (참고: 초보 운전자에게 적합한 차종)"
    assert score_ab.doc_hit(ans, ["03-초보운전자-적합-차종"])
    assert not score_ab.doc_hit(ans, ["02-패밀리카-적합-차종"])
    assert score_ab.is_redirect("예산·차종을 알려주시면 매물을 찾아드릴게요.")
    assert not score_ab.is_redirect("그냥 거절합니다.")


def test_redirect_markers_actually_match_the_shipped_answers():
    """G1 dead-end 게이트와 실제 응답 문구의 결합을 못박는다(13.5 2차 코드리뷰).

    왜 필요한가: REDIRECT_MARKERS는 guard_node/_EMPTY_FALLBACK의 문구에서 뽑은 부분문자열인데,
    그 결합이 지금까지 **주석에만** 있었다. 실측으로 마커를 13.5 이전 값으로 되돌려도 api 스위트
    355건이 전부 초록이었다 — 즉 문구든 마커든 한쪽만 바뀌면 게이트가 조용히 죽는다.
    deadend는 gate_pass에 직결되므로(score_ab.py) 이 결합은 실행되는 검사여야 한다(CLAUDE.md B9).

    13.5 3차 코드리뷰: 위 두 단언은 **양성 방향만** 못박아, 마커가 과도하게 넓어지는 실패
    (1차 패치의 "차장님")는 여전히 못 잡았다 — 실측으로 마커에 "차장님"을 되돌려도 api 스위트
    356건이 전부 초록이었다. OR 판정이라 넓은 마커 하나면 게이트가 구조적으로 항상 통과한다.
    그래서 아래에 **출고 문구에서 유도 절만 걷어낸 변형**을 음성 대조군으로 고정한다.

    이 검사가 안 보는 것: 마커가 의미상 "행동 유도인가"라는 일반 판단. 페르소나 문장에서 온
    마커는 아래 대조군이 잡지만, 그 밖의 넓은 낱말(예: 조사·흔한 명사)은 사람이 리뷰에서 본다.
    """
    from app.graph.answer_node import _EMPTY_FALLBACK
    from app.graph.guard_node import _GUARD_ANSWER

    # REJECT 고정 문구는 반드시 "갈림길"로 판정돼야 한다(dead-end 0% 결정).
    assert score_ab.is_redirect(_GUARD_ANSWER)
    # FR17 0건 fallback도 재유도 문구다 — C 질의가 다른 경로로 새서 0건이 나와도 dead-end가 아니다.
    assert score_ab.is_redirect(_EMPTY_FALLBACK)
    # 음성 대조군: 출고 거절 문구에서 **유도 절만** 지운 변형은 dead-end여야 한다.
    # 페르소나 문장은 그대로 두었으므로, 마커가 페르소나 낱말("차장님" 등)에서 오면 여기서 red.
    assert not score_ab.is_redirect(
        "저는 중고차 찾기를 도와드리는 차장님이에요 🚗 그건 답하기 어려워요."
    )


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
            "query": "오늘 날씨 어때?", "primary_path": "REJECT", "acceptable_paths": ["REJECT"],
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
                     "query": "q", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}]}
    raw = {"model": "m", "results": {"A1": [{"error": "429 quota exceeded"}]}}
    summary = score_ab.score_model(qs, raw)  # 수정 전엔 여기서 KeyError
    assert summary["errored_n"] == 1
    assert summary["result_n"] == 0


def test_score_model_continues_scoring_other_items_when_one_errors():
    """error 항목이 하나 섞여도 나머지 정상 item은 그대로 채점된다."""
    qs = {"items": [
        {"id": "C1", "kind": "single", "category": "clean",
         "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        {"id": "C2", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
    ]}
    raw = {
        "model": "m",
        "results": {
            # route_last는 캡처된 실제 route라 13.2 이후 항상 신버전 어휘다(queryset의
            # primary_path="C"는 구버전 그대로 — route_ok가 번역해 비교한다, DW-562).
            "C1": [{"route_last": "REJECT", "ids_last": [], "answer_last": "거절",
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
             "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
            {"id": "C2", "kind": "single", "category": "clean",
             "query": "q2", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        ],
    })
    raw = _write_json(tmp_path / "raw.json", {
        "model": "gemini-3.1-flash-lite",
        "results": {
            # route_last는 캡처된 실제 route라 13.2 이후 항상 신버전 어휘다(DW-562).
            "C1": [{"route_last": "REJECT", "ids_last": [], "answer_last": "거절",
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
         "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        {"id": "B1", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        {"id": "C1", "kind": "single", "category": "clean",
         "query": "q3", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        {"id": "D1", "kind": "single", "category": "clean",
         "query": "q4", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
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
                     "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}]}
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
                     "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}]}
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
         "query": "q1", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        {"id": "B1", "kind": "single", "category": "clean",
         "query": "q2", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
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
            "query": f"q{rid}", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}


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
            {"query": "q1", "primary_path": "SQL", "acceptable_paths": ["SQL"]},
            {"query": "q2", "primary_path": "SQL", "acceptable_paths": ["SQL"],
             "must_not_contain": ["중형차"]},
        ],
    }]}
    # turns[].route(=tr["route"])는 캡처된 실제 route라 13.2 이후 항상 신버전 어휘("SQL")다.
    # queryset의 primary_path="A"(구버전)는 route_ok가 번역해 비교한다(DW-562).
    raw = {"model": "m", "results": {
        "M1": [{
            "route_last": "SQL", "ids_last": ["l9"], "answer_last": "a2",
            "turns": [
                {"route": "SQL", "ids": ["l1"], "answer": "a1"},
                {"route": "SQL", "ids": ["l9"], "answer": "a2"},  # 이전 턴 조건이 살아남음 = 오염
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


def test_score_model_multiturn_counts_each_turn_and_fires_contamination_via_hybrid(monkeypatch):
    """review-3 실측 재현 — HYBRID도 SQL과 동일한 sql_rag_node를 타므로 같은 조건 잔존
    위험이 있는데, 하드 오염 게이트가 route=="SQL"만 보면 이 경로를 조용히 놓친다(수정 전
    실측: contamination=0·gate_pass=True로 통과). route만 "HYBRID"로 바꾼 것 외엔 위
    test_score_model_multiturn_counts_each_turn_and_fires_contamination과 동일하다.

    ⚠️ 픽스처는 실제 큐리셋에 존재할 수 있는 라벨만 쓴다(review-4). 이전엔
    `acceptable_paths=["A","HYBRID"]`라는 구·신 혼합 라벨을 썼는데, 큐리셋 데이터는
    수정 금지(Never 절)라 그런 값이 존재할 수 없다 — 그 가짜 라벨이 "라우팅은 맞게
    세면서 게이트도 올라간다"는 존재하지 않는 조합을 증명하고 있었다.

    ✎ Story 13.3(DW-572/575)이 route_ok의 legacy `A` 번역을 1:1(`A→SQL`)에서 집합
    (`A→{"SQL","HYBRID"}`)으로 넓혔다 — 그 전엔 이 테스트가 "라우팅은 오답으로
    집계되지만 오염 게이트는 올라간다"를 잠갔지만, 그건 DW-572가 지목한 바로 그 버그였다
    (라우터가 정확히 HYBRID로 분류해도 legacy `A` 라벨 때문에 오답으로 깎였다). 이제
    routing_correct가 옳게 2로 집계된다 — 그리고 하드 오염 게이트는 라우팅 정답 여부와
    무관하게 독립적으로 발화해야 하므로(수정 전엔 route=="SQL"만 봐서 0/True로 조용히
    통과했었다) 여전히 깨져야 한다.
    """
    monkeypatch.setattr(score_ab, "fetch_attrs",
                        lambda ids: [{"id": i, "body_type": "중형차", "price": 1} for i in ids])
    qs = {"items": [{
        "id": "M1H", "kind": "multiturn", "category": "clean",
        "turns": [
            {"query": "q1", "primary_path": "SQL", "acceptable_paths": ["SQL", "HYBRID"]},
            {"query": "q2", "primary_path": "SQL", "acceptable_paths": ["SQL", "HYBRID"],
             "must_not_contain": ["중형차"]},
        ],
    }]}
    raw = {"model": "m", "results": {
        "M1H": [{
            "route_last": "HYBRID", "ids_last": ["l9"], "answer_last": "a2",
            "turns": [
                {"route": "HYBRID", "ids": ["l1"], "answer": "a1"},
                {"route": "HYBRID", "ids": ["l9"], "answer": "a2"},  # 이전 턴 조건이 살아남음 = 오염
            ],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0,
        }],
    }}
    summary = score_ab.score_model(qs, raw)
    assert summary["routing_total"] == 2
    # 두 경로가 모두 타당한 턴은 acceptable_paths에 HYBRID를 명시했으므로 라우팅 만점이다
    # (DW-609 이후: 일괄 번역이 아니라 문항별 허용집합으로 표현한다).
    assert summary["routing_correct"] == 2
    # 그럼에도 HYBRID 경로에서 하드 오염 게이트는 올라가고 PASS가 깨져야 한다
    # (수정 전엔 0/True로 조용히 통과 — 게이트는 라우팅 정답 여부와 독립이어야 한다).
    assert summary["contamination"] == 1
    assert summary["gate_pass"] is False
    assert summary["per_item"][0]["turns"][1]["contamination"] == ["l9: body_type=중형차 (금지)"]


def test_score_model_multiturn_route_mismatch_counted():
    """턴 라우팅 오답도 실제로 집계된다(route_ok를 True로 못박아도 안 잡히던 자리)."""
    qs = {"items": [{
        "id": "M2", "kind": "multiturn", "category": "clean",
        "turns": [
            {"query": "q1", "primary_path": "SQL", "acceptable_paths": ["SQL"]},
            {"query": "q2", "primary_path": "CLARIFY", "acceptable_paths": ["CLARIFY"]},
        ],
    }]}
    # route(actual)는 13.2 이후 항상 신버전 어휘 — 2번째 턴은 CLARIFY(구 B)여야 하는데 SQL(구 A)이 왔다.
    raw = {"model": "m", "results": {
        "M2": [{"route_last": "SQL", "ids_last": [], "answer_last": "a2",
                "turns": [{"route": "SQL", "ids": [], "answer": "a1"},
                          {"route": "SQL", "ids": [], "answer": "a2"}],  # CLARIFY여야 하는데 SQL
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


# ── 구어휘로 캡처된 옛 raw 재채점 (DW-562 후속, review-4) ──────────────────────
# 구어휘 A/B/C로 캡처된 raw를 신어휘 코드로 재채점하면, route_ok가 primary/acceptable만
# 번역하고 actual은 그대로 두던 동안 라우팅이 50/55 → 0/55로 무너지고 멀티턴 하드 오염
# 게이트는 조건에 걸리지 않아 오염이 있어도 조용히 통과했다. DW-562가 막으려던
# "전량 오판"이 방향만 바뀌어 되살아난 것이라, 캡처 어휘를 읽는 지점에서 올린다.
# ⚠️ 13.8 3차 리뷰 정정: 이 주석은 "커밋된 docs/g2-baseline.json(44개 전량)이 구어휘"라고
#   적었으나 지금은 거짓이다 — DW-609의 2026-08-02 재캡처로 그 파일은 47항목·전부 신어휘다
#   (실측). 별칭표는 리포에 남은 구어휘 raw가 아니라 **외부에서 들어올 옛 raw** 대비책이다.

def test_captured_route_upgrades_legacy_and_passes_new_through():
    assert score_ab.captured_route("A") == "SQL"
    assert score_ab.captured_route("B") == "CLARIFY"
    assert score_ab.captured_route("C") == "REJECT"
    # 신버전 캡처에는 별칭표가 걸리지 않아 무영향이어야 한다(무해성).
    for r in ("SQL", "HYBRID", "CLARIFY", "REJECT"):
        assert score_ab.captured_route(r) == r


def test_legacy_captured_single_turn_scores_as_correct():
    """구어휘로 캡처된 단일턴 raw가 다시 정답으로 집계돼야 한다(수정 전엔 전량 오답)."""
    qs = {"items": [{"id": "A1", "kind": "single", "category": "clean", "query": "q",
                     "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}]}
    raw = {"model": "m", "results": {"A1": [{
        "route_last": "C", "ids_last": [], "answer_last": "매물 검색을 도와드릴게요",
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}
    summary = score_ab.score_model(qs, raw)
    assert summary["routing_total"] == 1
    assert summary["routing_correct"] == 1
    # 리포트에 남는 route는 "무엇이 캡처됐는가"라 원본 그대로 둔다(기록의 정직성).
    assert summary["per_item"][0]["route"] == "C"


def test_legacy_captured_multiturn_still_fires_contamination_gate(monkeypatch):
    """구어휘 캡처에서도 하드 오염 게이트가 올라가야 한다.

    수정 전 실측: 완전히 동일한 오염 데이터가 route="A"면 contamination=0·gate_pass=True,
    "SQL"이면 1·False. 게이트가 조용히 꺼지는 쪽이라 실패가 아니라 통과로 보였다 —
    review-3이 HYBRID에서 잡아낸 것과 같은 구조의 구멍이 구어휘 쪽에 남아 있었다.
    """
    monkeypatch.setattr(score_ab, "fetch_attrs",
                        lambda ids: [{"id": i, "body_type": "중형차", "price": 1} for i in ids])
    qs = {"items": [{
        "id": "M6", "kind": "multiturn", "category": "clean",
        "turns": [
            {"query": "q1", "primary_path": "SQL", "acceptable_paths": ["SQL"]},
            {"query": "q2", "primary_path": "SQL", "acceptable_paths": ["SQL"],
             "must_not_contain": ["중형차"]},
        ],
    }]}
    raw = {"model": "m", "results": {"M6": [{
        "route_last": "A", "ids_last": ["l9"], "answer_last": "a2",
        "turns": [{"route": "A", "ids": ["l1"], "answer": "a1"},
                  {"route": "A", "ids": ["l9"], "answer": "a2"}],
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}
    summary = score_ab.score_model(qs, raw)
    assert summary["routing_correct"] == 2      # 구어휘도 정상 채점
    assert summary["contamination"] == 1        # 게이트가 실제로 발화
    assert summary["gate_pass"] is False


def test_legacy_vocab_primary_path_fails_loud_instead_of_scoring_zero():
    """큐리셋 골든 라벨이 **구어휘(A/B/C)**면 조용히 0점이 아니라 시끄럽게 죽어야 한다.

    DW-609 재설계로 채점 분기가 신어휘 리터럴('SQL'/'HYBRID'/'CLARIFY'/'REJECT')로만
    갈라진다. 그래서 함정의 방향이 뒤집혔다 — 이제 구어휘 큐리셋을 그대로 먹이면
    라우팅은 계속 맞다고 세면서 결과집합·인용 채점만 조용히 0건이 된다. 예전에
    신어휘 라벨 하나가 그랬던 것과 정확히 같은 실패라, 같은 자리에서 막는다(B9).
    """
    qs = {"items": [{"id": "A9", "kind": "single", "category": "clean", "query": "q",
                     "primary_path": "A", "acceptable_paths": ["A"],
                     "predicate": {"price_max": 1}}]}
    raw = {"model": "m", "results": {"A9": [{
        "route_last": "SQL", "ids_last": ["l1"], "answer_last": "a",
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}
    with pytest.raises(ValueError) as exc:
        score_ab.score_model(qs, raw)
    assert "primary_path" in str(exc.value)


def test_legacy_vocab_primary_path_in_multiturn_turn_also_fails_loud():
    """같은 fail-loud 가드가 **멀티턴 턴**에도 걸려야 한다.

    review-5 실측: 단일턴 가드만 테스트로 잠겨 있고 멀티턴 쪽(score_model의 turns 루프)은
    가드를 통째로 지워도 스위트가 초록이었다. 그 상태를 재현하면 라우팅은 만점인데
    결과집합 채점 0건·deadend 0·gate_pass True — 정확히 이 가드가 막으려던 "조용한 오답"이다.
    """
    qs = {"items": [{"id": "M9", "kind": "multiturn", "category": "clean",
                     "turns": [
                         {"query": "q1", "primary_path": "A", "acceptable_paths": ["A"],
                          "predicate": {"price_max": 1}},
                     ]}]}
    raw = {"model": "m", "results": {"M9": [{
        "route_last": "SQL", "ids_last": ["l1"], "answer_last": "a",
        "turns": [{"route": "SQL", "ids": ["l1"], "answer": "a"}],
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}
    with pytest.raises(ValueError) as exc:
        score_ab.score_model(qs, raw)
    assert "M9.t0" in str(exc.value) and "primary_path" in str(exc.value)


def test_unknown_acceptable_path_label_fails_loud_instead_of_being_ignored():
    """`acceptable_paths`의 미지 라벨도 조용히 무시되지 않고 시끄럽게 죽어야 한다.

    review-5 실측: 가드가 primary만 볼 때 오타 한 글자가 허용집합에서 조용히 사라지고
    리포트에 흔적이 안 남았다. 골든 라벨은 우리가 쓴 데이터이므로 primary와 같은
    기준으로 막는다(B9).
    """
    qs = {"items": [{"id": "A8", "kind": "single", "category": "clean", "query": "q",
                     "primary_path": "SQL", "acceptable_paths": ["SQL", "HYBIRD_TYPO"],
                     "predicate": {"price_max": 1}}]}
    raw = {"model": "m", "results": {"A8": [{
        "route_last": "SQL", "ids_last": ["l1"], "answer_last": "a",
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}
    with pytest.raises(ValueError) as exc:
        score_ab.score_model(qs, raw)
    assert "acceptable_paths" in str(exc.value)


def test_mixed_vocab_repeats_are_not_counted_as_flaky():
    """같은 경로를 구/신 어휘로 나눠 캡처한 반복 실행은 flaky가 아니다.

    flaky 서명만 captured_route() 정규화를 빼먹고 raw route를 그대로 썼다(review-5).
    그러면 어휘 이관 중 부분 재캡처된 raw가 "모델이 흔들린다"는 거짓 양성으로 잡혀,
    모델 안정성 지표가 이관 사고로 오염된다.
    """
    qs = {"items": [{"id": "A7", "kind": "single", "category": "clean", "query": "q",
                     "primary_path": "REJECT", "acceptable_paths": ["REJECT"]}]}
    runs = [
        {"route_last": "C", "ids_last": [], "answer_last": "a",
         "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0},
        {"route_last": "REJECT", "ids_last": [], "answer_last": "a",
         "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0},
    ]
    summary = score_ab.score_model(qs, {"model": "m", "results": {"A7": runs}})
    assert summary["flaky_n"] == 0, "같은 경로의 구/신 어휘를 서로 다른 판정으로 세면 안 된다"
    assert summary["routing_correct"] == 1


# ═══════════════════════════════════════════════════════════════════════
# DW-609 재설계로 새로 생긴 채점 경로 — HYBRID(가이드 활용)와 CLARIFY(되묻기)
# ═══════════════════════════════════════════════════════════════════════
# 이 두 경로는 구 채점기에 아예 없었다. 큐리셋에 HYBRID 문항이 0건이었고 CLARIFY 라벨
# 자체가 없었기 때문이다(그래서 게이트가 초록이어도 그 기능은 보고 있지 않았다 — DW-607).
# 아래 검사들은 "지표가 존재한다"가 아니라 "틀린 동작을 실제로 잡는다"를 못박는다.

def test_score_path_hybrid_uses_precision_not_f1():
    """하이브리드는 조건에 맞는 것 중 상위 N건만 보여주는 게 정상이므로 재현율로 깎지 않는다.

    F1을 쓰면 정답 36건 중 5건만 보여준 **정상 동작**이 0.24점으로 깎여 신호가 죽는다.
    대신 precision(보여준 게 전부 정답 집합 안인가)만 본다.
    """
    golden = {f"l{i}" for i in range(36)}
    # 정답 집합의 부분집합만 보여줌 = 만점(정상 동작).
    assert score_ab.score_path_hybrid(["l1", "l2", "l3", "l4", "l5"], golden)["result"] == 1.0
    # 절반이 집합 밖(가이드가 결과를 못 좁혔다) = 감점.
    assert score_ab.score_path_hybrid(["l1", "l2", "x1", "x2"], golden)["result"] == 0.5
    # 정답이 있는데 0건 반환 = 0점.
    assert score_ab.score_path_hybrid([], golden)["result"] == 0.0
    # 정답도 0건이고 반환도 0건 = 만점(빈 조건에 빈손이 맞다).
    assert score_ab.score_path_hybrid([], set())["result"] == 1.0


def _hybrid_qs(**overrides):
    item = {"id": "H1", "kind": "single", "category": "clean",
            "query": "3천만원 이하로 무난한 패밀리카",
            "primary_path": "HYBRID", "acceptable_paths": ["HYBRID"],
            "doc_refs": ["02-패밀리카-적합-차종"],
            "predicate": {"price_max": 30000000}}
    item.update(overrides)
    return {"items": [item]}


def _hybrid_raw(route="HYBRID", ids=("g1", "g2"), answer="조건에 맞는 매물 2건을 찾았어요. (참고: 패밀리카로 무난한 차종 고르기)"):
    return {"model": "m", "results": {"H1": [{
        "route_last": route, "ids_last": list(ids), "answer_last": answer,
        "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}]}}


def test_score_model_hybrid_scores_result_set_and_counts_guide_citation(monkeypatch):
    """HYBRID 문항은 결과집합(가이드가 좁혔나) + 인용(가이드가 쓰였나)을 **둘 다** 센다."""
    monkeypatch.setattr(score_ab, "run_golden_ids", lambda pred: ["g1", "g2", "g3"])
    summary = score_ab.score_model(_hybrid_qs(), _hybrid_raw())

    assert summary["result_n"] == 1               # 결과집합 평균에 HYBRID가 실제로 들어간다
    assert summary["result_mean"] == 1.0
    assert summary["doc_hit_total"] == 1          # 분모 — "볼 문항이 있다"
    assert summary["doc_hit_n"] == 1              # 분자 — 가이드가 실제로 인용됐다
    assert summary["per_item"][0]["doc_hit"] is True


def test_score_model_hybrid_without_guide_citation_is_a_miss(monkeypatch):
    """인용 접미사가 없으면(가이드 미채택) 같은 결과라도 doc_hit이 0이어야 한다.

    구 채점기에서 이 지표는 구조적으로 항상 0이었다 — 0이 "미채택"인지 "볼 문항이 없음"인지
    구분되지 않았다. 분모(doc_hit_total)를 함께 세는 이유가 이것이다.
    """
    monkeypatch.setattr(score_ab, "run_golden_ids", lambda pred: ["g1", "g2", "g3"])
    summary = score_ab.score_model(
        _hybrid_qs(), _hybrid_raw(answer="조건에 맞는 매물 2건을 찾았어요.")
    )
    assert summary["doc_hit_total"] == 1 and summary["doc_hit_n"] == 0
    assert summary["result_mean"] == 1.0  # 결과집합과 인용은 별개 축이다


def test_score_model_hybrid_that_leaked_to_another_route_loses_both_axes(monkeypatch):
    """HYBRID 문항이 되묻기로 새면 라우팅·결과집합·인용이 전부 떨어져야 한다.

    13.4 이후 실제로 벌어졌던 사고 유형이다(하이브리드로 가야 할 질의가 CLARIFY로 흡수).
    구 채점기는 legacy `A`를 {SQL,HYBRID}로 일괄 번역해 이런 이탈을 정답으로 세기도 했다.
    """
    monkeypatch.setattr(score_ab, "run_golden_ids", lambda pred: ["g1", "g2", "g3"])
    summary = score_ab.score_model(
        _hybrid_qs(),
        _hybrid_raw(route="CLARIFY", ids=(), answer="조건을 조금만 좁혀볼게요 — 칩을 눌러도 돼요."),
    )
    assert summary["routing_correct"] == 0
    assert summary["result_mean"] == 0.0
    assert summary["doc_hit_n"] == 0


def test_score_model_hybrid_gray_item_is_excluded_from_result_mean(monkeypatch):
    """gray 문항은 결과집합 평균에서 빠진다(합격선 신호 보호) — 인용은 그래도 센다."""
    monkeypatch.setattr(score_ab, "run_golden_ids", lambda pred: ["g1"])
    summary = score_ab.score_model(_hybrid_qs(category="gray"), _hybrid_raw())
    assert summary["result_n"] == 0
    assert summary["doc_hit_total"] == 1


# ── CLARIFY(되묻기) 채점 ────────────────────────────────────────────────
def test_clarify_marker_matches_the_shipped_clarify_node(monkeypatch):
    """채점 마커가 실제 출고 문구와 결합돼 있음을 못박는다(주석은 계약이 아니다 — B9).

    REDIRECT_MARKERS와 같은 부류의 실패를 막는다: 노드 문구든 마커든 한쪽만 바뀌면
    "되묻기 발동률"이 조용히 0이 되고, 아무 검사도 red가 되지 않는다.
    """
    from app.graph.clarify_node import _CLARIFY_CHIPS, _CLARIFY_QUESTION, clarify_node

    assert score_ab.clarify_question_ok(_CLARIFY_QUESTION)
    assert score_ab.clarify_chips_ok(clarify_node("아무 질의")["clarify"])
    assert _CLARIFY_CHIPS, "칩이 비면 되묻기는 사용자에게 막다른 길이다"
    # 음성 대조군 — 되묻기가 아닌 답변은 통과하면 안 된다.
    assert not score_ab.clarify_question_ok("조건에 맞는 매물 5건을 찾았어요.")


def _clarify_qs():
    return {"items": [{"id": "CL1", "kind": "single", "category": "clean",
                       "query": "초보운전자 첫차로 뭐가 좋아?",
                       "primary_path": "CLARIFY", "acceptable_paths": ["CLARIFY"],
                       "expect_clarify": True}]}


def _clarify_run(answer="조건을 조금만 좁혀볼게요 — 칩을 눌러도 되고, 직접 입력해도 돼요.",
                 chips=("3천만원 이하", "SUV", "전기차"), with_key=True):
    run = {"route_last": "CLARIFY", "ids_last": [], "answer_last": answer,
           "tokens_in": 0, "tokens_out": 0, "latency_ms": 1.0}
    if with_key:
        run["clarify_last"] = {"question": answer, "chips": list(chips)}
    return {"model": "m", "results": {"CL1": [run]}}


def test_score_model_clarify_counts_question_and_chips_together():
    summary = score_ab.score_model(_clarify_qs(), _clarify_run())
    assert summary["clarify_total"] == 1 and summary["clarify_ok_n"] == 1
    assert summary["clarify_chips_unobserved"] == 0


def test_score_model_clarify_with_zero_chips_is_not_ok():
    """"칩을 눌러도 된다"고 말해 놓고 칩이 0개면 사용자에겐 막다른 길이다 — 문구만 보는
    검사는 이 상태를 통과시킨다(DW-587·592가 가리키는 실제 클라이언트 증상의 서버측 대응물)."""
    summary = score_ab.score_model(_clarify_qs(), _clarify_run(chips=()))
    assert summary["clarify_total"] == 1 and summary["clarify_ok_n"] == 0


def test_score_model_clarify_with_wrong_answer_text_is_not_ok():
    """라우터는 CLARIFY라 했는데 되묻기 문구가 안 나오면 발동 실패로 센다."""
    summary = score_ab.score_model(_clarify_qs(), _clarify_run(answer="조건에 맞는 매물 5건을 찾았어요."))
    assert summary["clarify_ok_n"] == 0


def test_score_model_clarify_old_capture_without_chips_key_is_flagged_not_silently_passed():
    """칩을 캡처하지 않은 옛 raw는 질문 문구만으로 판정하되, 그 사실을 요약에 남긴다 —
    "칩까지 확인했다"와 "확인 못 했다"가 같은 숫자로 읽히면 안 된다."""
    summary = score_ab.score_model(_clarify_qs(), _clarify_run(with_key=False))
    assert summary["clarify_ok_n"] == 1
    assert summary["clarify_chips_unobserved"] == 1
    assert summary["per_item"][0]["clarify_chips_unobserved"] is True


def test_observability_line_distinguishes_zero_percent_from_no_items():
    """0%와 "볼 문항이 없음"을 사람이 보는 화면에서 구분한다 — 구셋이 정확히 후자였다."""
    empty = score_ab._observability_line({"doc_hit_n": 0, "doc_hit_total": 0,
                                          "clarify_ok_n": 0, "clarify_total": 0})
    assert "해당 문항 없음" in empty
    real_zero = score_ab._observability_line({"doc_hit_n": 0, "doc_hit_total": 12,
                                              "clarify_ok_n": 7, "clarify_total": 7})
    assert "0/12" in real_zero and "해당 문항 없음" not in real_zero


# ── 출고 큐리셋 자체를 검사한다(B9: 규칙은 어길 수 없는 자리에) ──────────
_SHIPPED_QUERYSET = json.loads(
    (Path(__file__).resolve().parent.parent / "docs" / "ai-ab-test-queryset.json")
    .read_text(encoding="utf-8")
)


def _all_labelled_units():
    """단일 item과 멀티턴 턴을 한 줄로 펼친다(라벨이 붙는 모든 자리)."""
    for item in _SHIPPED_QUERYSET["items"]:
        if item["kind"] == "single":
            yield item["id"], item
        else:
            for ti, turn in enumerate(item["turns"]):
                yield f"{item['id']}.t{ti}", turn


def test_shipped_queryset_uses_only_the_new_vocabulary():
    """커밋된 큐리셋이 구어휘로 되돌아가면 즉시 red — 번역 계층을 없앤 전제를 지킨다."""
    for where, unit in _all_labelled_units():
        score_ab._require_route_labels(
            unit["primary_path"], unit.get("acceptable_paths"), where
        )


def test_shipped_queryset_actually_covers_all_four_routes():
    """네 갈래를 고르게 보는 것이 이 재설계의 목적이다 — 한 갈래라도 0건이면 red.

    특히 HYBRID·CLARIFY는 구셋에서 각각 0건이었다(그래서 13.6이 만든 기능과 13.4가 만든
    되묻기를 회귀 검사가 원리상 못 봤다). 그 상태로 되돌아가는 것을 검사로 막는다.
    """
    from collections import Counter

    counts = Counter(unit["primary_path"] for _, unit in _all_labelled_units())
    for label in score_ab.ROUTE_LABELS:
        assert counts[label] > 0, f"{label} 라벨 문항이 0건 — 그 갈래는 관측되지 않는다"
    assert counts["HYBRID"] >= 10, "하이브리드 비중 확대가 이 재설계의 핵심이다"


def test_shipped_hybrid_items_are_fully_labelled():
    """HYBRID 문항엔 predicate(결과집합)와 doc_refs(인용)가 **둘 다** 있어야 채점된다.

    하나만 빠져도 그 문항은 조용히 반쪽만 채점된다 — 정확히 구셋이 반복해서 밟은 함정이다.
    """
    known_stems = set(score_ab.DOC_STEM_TO_TITLE)
    hybrids = [(w, u) for w, u in _all_labelled_units() if u["primary_path"] == "HYBRID"]
    assert hybrids
    for where, unit in hybrids:
        assert unit.get("predicate"), f"{where}: HYBRID인데 predicate가 없어 결과집합 채점이 안 된다"
        refs = unit.get("doc_refs")
        assert refs, f"{where}: HYBRID인데 doc_refs가 없어 인용 채점이 안 된다"
        unknown = set(refs) - known_stems
        assert not unknown, f"{where}: 존재하지 않는 가이드 stem {unknown} — 인용은 영원히 miss가 된다"


def test_shipped_sql_items_have_predicates():
    for where, unit in _all_labelled_units():
        if unit["primary_path"] == "SQL":
            assert unit.get("predicate"), f"{where}: SQL인데 predicate가 없어 결과집합 채점이 안 된다"
