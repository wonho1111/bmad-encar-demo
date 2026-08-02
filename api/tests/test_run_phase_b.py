"""run_phase_b.py 러너 단위테스트 — run_search를 모킹해 라이브 호출 없이 결정론적으로 검증.

목적: G2 baseline 캡처 러너가 score_ab.score_model()이 기대하는 shape
  (results[id] = [{route_last/turns, ids_last, answer_last, tokens_in, tokens_out, latency_ms}])을
  정확히 조립하는지, 그리고 그 raw 출력이 score_ab.py의 1파일 CLI 모드로 실제 채점되는지
  검증한다. RUN_LIVE_SMOKE 게이트(쿼터 보호)도 여기서 확인한다.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# scripts/run_phase_b.py, scripts/score_ab.py를 모듈로 직접 로드(scripts는 패키지가 아니므로).
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_phase_b = _load("run_phase_b", "run_phase_b.py")
score_ab = _load("score_ab", "score_ab.py")


class _FakeCard:
    """ListingCard 흉내 — pydantic 속성 접근(`.id`)만 필요."""

    def __init__(self, id_):
        self.id = id_


def _fake_run_search_single(query, context=None):
    return {"answer": f"'{query}' 결과", "listings": [_FakeCard("l1"), _FakeCard("l2")], "route": "A"}


def test_capture_single_item_shape():
    queryset = {"items": [{"id": "A1", "kind": "single", "query": "3천만원 이하 SUV"}]}
    raw = run_phase_b.capture(queryset, None, "test-model", _fake_run_search_single)

    assert raw["model"] == "test-model"
    runs = raw["results"]["A1"]
    assert len(runs) == 1
    run = runs[0]
    assert run["route_last"] == "A"
    assert run["ids_last"] == ["l1", "l2"]
    assert run["answer_last"] == "'3천만원 이하 SUV' 결과"
    assert run["tokens_in"] == 0 and run["tokens_out"] == 0
    assert run["latency_ms"] >= 0
    assert "turns" not in run
    # 아무도 안 읽는 "tokens_measured" 스탬프는 찍지 않는다(review pass 5) — score_model은
    # 플래그가 아니라 토큰 합계로 판단한다. 스탬프가 있으면 "True로 바꾸면 비용 축이 켜진다"는
    # 오해를 부르고, 커밋된 g2-baseline-partial.json(스탬프 없음)과도 shape이 어긋난다.
    assert "tokens_measured" not in run


def test_capture_multiturn_item_shape_tracks_context_and_last_turn():
    seen_contexts = []

    # 3턴이어야 "누적"과 "직전 턴만 유지"가 갈린다(review pass 5). 2턴짜리로는 두 구현이
    # 2번째 호출에 똑같은 context를 넘겨 회귀를 관찰할 수 없었다 — 실제 큐리셋의 멀티턴
    # item은 3턴이고, 마지막 REFINE 턴이 첫 턴 조건을 계승해야 한다.
    _ANSWERS = {
        "3천만원 이하 SUV": ("SUV 5건", "s1"),
        "그중에 서울에 있는 것만": ("서울만 2건", "s2"),
        "제일 싼 거 하나만": ("최저가 1건", "s3"),
    }

    def fake_run_search(query, context=None):
        seen_contexts.append(context)
        answer, card = _ANSWERS[query]
        return {"answer": answer, "listings": [_FakeCard(card)], "route": "A"}

    item = {
        "id": "M1", "kind": "multiturn",
        "turns": [
            {"query": "3천만원 이하 SUV"},
            {"query": "그중에 서울에 있는 것만"},
            {"query": "제일 싼 거 하나만"},
        ],
    }
    queryset = {"items": [item]}
    raw = run_phase_b.capture(queryset, None, "test-model", fake_run_search)

    run = raw["results"]["M1"][0]
    # 마지막 턴 값이 route_last/ids_last/answer_last에 반영된다(flaky 판정이 kind 무관하게 이 키를 읽음).
    assert run["route_last"] == "A"
    assert run["ids_last"] == ["s3"]
    assert run["answer_last"] == "최저가 1건"
    assert len(run["turns"]) == 3
    # clarify는 CLARIFY 경로에서만 채워지는 되묻기 페이로드다(DW-609) — 이 fake는 안 내므로 None.
    assert run["turns"][0] == {"route": "A", "ids": ["s1"], "answer": "SUV 5건", "clarify": None}
    assert run["turns"][1] == {"route": "A", "ids": ["s2"], "answer": "서울만 2건", "clarify": None}
    assert run["turns"][2] == {"route": "A", "ids": ["s3"], "answer": "최저가 1건", "clarify": None}
    # context는 "직전 턴만"이 아니라 매 턴 누적이다(FR18 맥락 누적) — 3번째 호출이 그 구분점이다.
    assert seen_contexts[0] is None
    assert seen_contexts[1] == [
        {"role": "user", "content": "3천만원 이하 SUV"},
        {"role": "assistant", "content": "SUV 5건"},
    ]
    assert seen_contexts[2] == [
        {"role": "user", "content": "3천만원 이하 SUV"},
        {"role": "assistant", "content": "SUV 5건"},
        {"role": "user", "content": "그중에 서울에 있는 것만"},
        {"role": "assistant", "content": "서울만 2건"},
    ]


def test_capture_subset_filters_items():
    queryset = {
        "items": [
            {"id": "A1", "kind": "single", "query": "q1"},
            {"id": "B1", "kind": "single", "query": "q2"},
            {"id": "C1", "kind": "single", "query": "q3"},
        ],
    }
    raw = run_phase_b.capture(queryset, ["A1", "C1"], "test-model", _fake_run_search_single)
    assert set(raw["results"].keys()) == {"A1", "C1"}


def test_main_gate_skips_without_run_live_smoke(monkeypatch, tmp_path, capsys):
    """RUN_LIVE_SMOKE=1이 아니면 app/DB import조차 없이 종료한다(쿼터 보호).

    종료코드는 0이 아니어야 한다(review pass 4) — 그래야 `run_phase_b.py && score_ab.py ...`
    처럼 셸에서 체인했을 때 게이트 차단이 조용히 삼켜져 뒤 명령이 낡은 --out 파일을
    그대로 채점해버리는 사고를 막는다.
    """
    monkeypatch.delenv("RUN_LIVE_SMOKE", raising=False)
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["run_phase_b.py", "--out", str(out)])

    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()

    assert exc_info.value.code != 0
    assert not out.exists()
    assert "RUN_LIVE_SMOKE" in capsys.readouterr().out


def test_main_end_to_end_with_mocked_run_search_feeds_score_ab_single_mode(monkeypatch, tmp_path):
    """RUN_LIVE_SMOKE=1 + 모킹된 run_search로 main()을 실행 → 그 출력이 score_ab.py 1파일
    모드로 실제 채점되는지까지 확인한다(라이브 호출·DB 연결 0, C경로만 사용해 골든 SQL 불필요).
    """
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")

    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({
        "items": [
            {"id": "R1", "kind": "single", "category": "clean",
             "query": "오늘 날씨 어때?", "primary_path": "REJECT", "acceptable_paths": ["REJECT"]},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    out_path = tmp_path / "raw.json"

    def fake_run_search(query, context=None):
        # 큐리셋 골든 라벨과 실제 route가 같은 신 4값 어휘다(DW-609 — 번역 계층 제거).
        return {"answer": "그건 못 도와드려요.", "listings": [], "route": "REJECT"}

    # main()이 `from app.graph.graph import run_search`로 늦게 import하므로, 모듈 속성 자체를
    # 패치해 그 늦은 import가 가짜 함수를 받게 한다(라이브 Gemini/DB 호출 0).
    import app.graph.graph as real_graph_module

    monkeypatch.setattr(real_graph_module, "run_search", fake_run_search)
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--subset", "R1", "--out", str(out_path)],
    )

    run_phase_b.main()

    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["results"]["R1"][0]["route_last"] == "REJECT"

    # 이 raw를 score_ab.py의 1파일 모드로 실제 채점(DB 불필요 — C경로는 골든 SQL을 안 씀).
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(
        sys, "argv",
        ["score_ab.py", "--queryset", str(qs_path), "--raw", str(out_path), "--out", str(report_path)],
    )
    score_ab.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "baseline_summary" in report
    assert report["baseline_summary"]["routing_correct"] == 1


def test_subset_blank_string_errors_instead_of_silently_running_all(monkeypatch, tmp_path):
    """--subset " "처럼 공백만 주면(값은 있지만 파싱 후 빈 리스트) 조용히 전량 실행하는 대신
    명시적으로 에러 낸다(빈 부분집합이 "전량 실행"으로 오인되는 사고 방지).
    """
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--subset", "  ", "--out", str(tmp_path / "out.json")],
    )
    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()
    assert exc_info.value.code == 2


# ── 코드리뷰 패치(4건): 부분 실패 내결함성·flush · --subset 오타 · kind 사전검증 ──
def test_capture_continues_after_item_failure_and_records_error(tmp_path):
    """item 하나가 run_search 호출 중 예외를 던져도 나머지 item은 계속 캡처된다(부분 유실 방지)."""

    def flaky_run_search(query, context=None):
        if query == "q2":
            raise RuntimeError("429 quota exceeded")
        return {"answer": f"ok:{query}", "listings": [], "route": "C"}

    queryset = {
        "items": [
            {"id": "X1", "kind": "single", "query": "q1"},
            {"id": "X2", "kind": "single", "query": "q2"},
            {"id": "X3", "kind": "single", "query": "q3"},
        ],
    }
    out_path = tmp_path / "partial.json"
    raw = run_phase_b.capture(queryset, None, "test-model", flaky_run_search, out_path=out_path)

    assert raw["results"]["X1"][0]["answer_last"] == "ok:q1"
    assert "error" in raw["results"]["X2"][0]
    assert raw["results"]["X3"][0]["answer_last"] == "ok:q3"  # 실패 뒤에도 계속 진행
    # 파일이 최종 상태로 flush돼 있다(누적 결과와 동일).
    assert json.loads(out_path.read_text(encoding="utf-8")) == raw


def test_capture_flushes_after_every_item_not_only_at_the_end(tmp_path):
    """`--out`에 매 item 처리 직후 flush된다 — 마지막에 한 번만 쓰는 게 아니다."""
    out_path = tmp_path / "partial.json"
    snapshots_seen_before_each_call: list[frozenset] = []

    def run_search(query, context=None):
        if out_path.exists():
            on_disk = json.loads(out_path.read_text(encoding="utf-8"))
            snapshots_seen_before_each_call.append(frozenset(on_disk["results"].keys()))
        else:
            snapshots_seen_before_each_call.append(frozenset())
        return {"answer": f"ok:{query}", "listings": [], "route": "C"}

    queryset = {
        "items": [
            {"id": "X1", "kind": "single", "query": "q1"},
            {"id": "X2", "kind": "single", "query": "q2"},
        ],
    }
    run_phase_b.capture(queryset, None, "test-model", run_search, out_path=out_path)

    # X1을 처리할 때는 아직 파일이 없어야(첫 item) 하고, X2를 처리할 때는 X1이 이미 flush돼 있어야 한다.
    assert snapshots_seen_before_each_call[0] == frozenset()
    assert snapshots_seen_before_each_call[1] == frozenset({"X1"})


def test_capture_unknown_kind_raises_before_any_live_call():
    """kind가 'single'/'multiturn' 밖이면 원인불명 KeyError 대신 즉시 ValueError — 라이브 호출 0회."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [{"id": "X1", "kind": "weird", "query": "q"}]}
    with pytest.raises(ValueError, match="unknown kind"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
    assert calls == []  # fail-fast — 쿼터를 태우기 전에 멈춘다


def test_capture_empty_turns_raises_before_any_live_call():
    """멀티턴 item의 turns가 빈 배열이면 "정상 실행됐지만 결과가 빔"과 구분 안 되는 대신 즉시 거부."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [{"id": "M1", "kind": "multiturn", "turns": []}]}
    with pytest.raises(ValueError, match="empty turns"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
    assert calls == []


def test_main_subset_with_unknown_id_errors(monkeypatch, tmp_path):
    """--subset에 큐리셋에 없는 id(오타 등)를 섞으면 조용히 드롭하지 않고 명시 거부한다."""
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(
        json.dumps({"items": [{"id": "C1", "kind": "single", "query": "x"}]}), encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--subset", "C1,ZZZ",
         "--out", str(tmp_path / "out.json")],
    )
    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()
    assert exc_info.value.code == 2


# ── review pass 4 — query 사전검증(item 4) ───────────────────────────────
def test_capture_single_item_missing_query_raises_before_any_live_call():
    """query 없는 single item은 라이브 호출 전에 거부한다 — 이전엔 `run_search(item["query"])`
    평가 시 KeyError로 죽고 그게 429와 구별 안 되는 `{"error": "'query'"}`로 삼켜졌다."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [{"id": "X1", "kind": "single"}]}  # query 누락
    with pytest.raises(ValueError, match="missing query"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
    assert calls == []


def test_capture_multiturn_turn_missing_query_raises_before_any_live_call():
    """멀티턴의 특정 turn에 query 키가 없거나(오타 등) 빈 값이면 라이브 호출 전에 거부한다."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [{"id": "M1", "kind": "multiturn",
                           "turns": [{"query": "1턴"}, {"q_typo": "오타"}]}]}
    with pytest.raises(ValueError, match="missing query"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
    assert calls == []


# ── review pass 4 — 중복 id 사전검증(item 5) ─────────────────────────────
def test_capture_rejects_duplicate_item_ids_before_any_live_call():
    """중복 id는 두 item이 같은 결과 슬롯에 쓰여 한 건이 조용히 사라진다 — 두 번 라이브
    호출하고도 결과는 한 건뿐이면 유료 캡처 하나가 그냥 유실된 것이다."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [
        {"id": "D1", "kind": "single", "query": "q1"},
        {"id": "D1", "kind": "single", "query": "q2"},
    ]}
    with pytest.raises(ValueError, match="duplicate"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
    assert calls == []


# ── review pass 4 — --out 상위 디렉터리·원자적 flush(item 6) ─────────────
def test_capture_rejects_out_path_with_missing_parent_dir_before_any_live_call(tmp_path):
    """--out의 상위 디렉터리가 없으면 라이브 호출 전에 거부한다 — 이전엔 첫 캡처 뒤
    `_flush()`에서야 `FileNotFoundError`로 터져 그 호출의 비용이 낭비됐다."""
    calls = []

    def run_search(query, context=None):
        calls.append(query)
        return {"answer": "x", "listings": [], "route": "A"}

    queryset = {"items": [{"id": "X1", "kind": "single", "query": "q"}]}
    bad_out = tmp_path / "missing_dir" / "out.json"  # missing_dir을 만들지 않는다
    with pytest.raises(ValueError, match="상위 디렉터리"):
        run_phase_b.capture(queryset, None, "test-model", run_search, out_path=bad_out)
    assert calls == []


def test_flush_is_atomic_partial_write_does_not_corrupt_existing_file(tmp_path, monkeypatch):
    """flush 도중 프로세스가 죽는 상황(디스크 풀 등)을 흉내내도, 그 직전까지 확보한 유료
    캡처 결과는 --out에 유효한 JSON으로 남아 있어야 한다(원자적 교체 — review pass 4).

    write_text를 몽키패치해 "두 번째 flush의 임시파일(.tmp) 쓰기"만 실패하게 만든다.
    구현이 진짜 원자적(임시파일 → replace)이 아니라 out_path를 직접 truncate-then-write
    했다면애초에 .tmp 파일 자체가 생기지 않으므로 이 실패 주입이 걸리지 않아 예외가 전혀
    나지 않는다 — 즉 이 테스트는 `.tmp` 경유 구현이 실제로 쓰이는지까지 함께 잠근다.
    """
    out_path = tmp_path / "partial.json"
    real_write_text = Path.write_text

    def flaky_write_text(self, data, encoding=None):
        # 두 번째 item(X2)의 flush 때 쓰기 실패를 흉내낸다. 호출 횟수가 아니라 "쓰려는 내용에
        # X2가 들어 있는가"로 고른다 — 루프 시작 전 flush(review pass 5)가 생기면서 횟수
        # 기준이 어긋났고, 내용 기준은 그런 순서 변화에 흔들리지 않는다.
        if self.suffix == ".tmp" and "X2" in data:
            raise OSError("disk full (simulated)")
        return real_write_text(self, data, encoding=encoding)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    queryset = {"items": [
        {"id": "X1", "kind": "single", "query": "q1"},
        {"id": "X2", "kind": "single", "query": "q2"},
    ]}

    def run_search(query, context=None):
        return {"answer": f"ok:{query}", "listings": [], "route": "C"}

    with pytest.raises(OSError):
        run_phase_b.capture(queryset, None, "test-model", run_search, out_path=out_path)

    # X1까지의 flush(첫 번째, 성공)는 파일에 유효한 JSON으로 남아 있어야 한다 — 반쪽짜리로
    # 깨지거나(비어 있거나) X2 처리 실패로 통째로 사라지면 안 된다.
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(on_disk["results"].keys()) == {"X1"}
    # (review pass 5) 여기 있던 `.tmp` 부재 단언은 지웠다 — 위 주입은 write_text 진입 즉시
    # 실패해 .tmp가 애초에 안 생기므로, 그 단언은 어떤 구현에서도 참이라 아무것도 잡지
    # 못했다. 실제 디스크 풀(일부만 쓰인 뒤 실패)에선 _flush()에 정리 경로가 없어 .tmp가
    # 남는다 — out_path는 교체 전이라 무사하고, 다음 flush가 그 .tmp를 덮어쓴다.


# ── review pass 4 — 실패 시 종료코드(item 7) ─────────────────────────────
def test_main_exits_nonzero_when_any_item_errors(monkeypatch, tmp_path):
    """캡처 중 item이 하나라도 {"error": ...}로 남으면 main()은 0이 아닌 코드로 종료한다 —
    이전엔 에러 항목도 그냥 "결과 개수"에 합산돼 exit 0(성공)으로 끝나 부분 실패가
    성공으로 보고됐다. 파일 자체는 여전히 남아야 한다(item 6과 결합 — 부분 결과 보존)."""
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": [
        {"id": "C1", "kind": "single", "query": "ok query"},
        {"id": "C2", "kind": "single", "query": "boom query"},
    ]}), encoding="utf-8")
    out_path = tmp_path / "out.json"

    def flaky_run_search(query, context=None):
        if query == "boom query":
            raise RuntimeError("429 quota exceeded")
        return {"answer": "ok", "listings": [], "route": "C"}

    import app.graph.graph as real_graph_module
    monkeypatch.setattr(real_graph_module, "run_search", flaky_run_search)
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--out", str(out_path)],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()
    assert exc_info.value.code != 0

    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert "error" in raw["results"]["C2"][0]
    assert raw["results"]["C1"][0]["answer_last"] == "ok"


def test_main_exits_zero_when_no_item_errors(monkeypatch, tmp_path):
    """정상 캡처(에러 0건)는 여전히 성공(0) 종료 — item 7 수정이 정상 경로까지 실패로
    바꾸지 않았는지 확인한다."""
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": [
        {"id": "C1", "kind": "single", "query": "ok query"},
    ]}), encoding="utf-8")
    out_path = tmp_path / "out.json"

    def ok_run_search(query, context=None):
        return {"answer": "ok", "listings": [], "route": "C"}

    import app.graph.graph as real_graph_module
    monkeypatch.setattr(real_graph_module, "run_search", ok_run_search)
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--out", str(out_path)],
    )

    run_phase_b.main()  # 예외 없이 정상 종료해야 한다(exit 0 == 반환)


# ── review pass 4 — --out 필수화(item 8) ─────────────────────────────────
def test_main_requires_out_argument(monkeypatch, tmp_path, capsys):
    """--out을 생략하면 예전엔 커밋된 baseline 산출물(docs/g2-baseline-partial.json)이
    기본값으로 쓰여 item 1부터 조용히 덮어써졌다. 이제는 필수 인자라 즉시 거부한다."""
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path)],  # --out 생략
    )

    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()
    assert exc_info.value.code == 2
    assert "--out" in capsys.readouterr().err


# ── 13.8 3차 리뷰 — 커밋된 기준선을 --out으로 지목하면 거부한다 ──────────
@pytest.mark.parametrize("baseline_name", ["g2-baseline.json", "g2-baseline-partial.json"])
def test_main_refuses_to_overwrite_committed_baseline(
    monkeypatch, tmp_path, capsys, baseline_name
):
    """`--out docs/g2-baseline.json`은 G2 회귀 판정의 기준점을 파괴한다.

    독스트링이 ⚠️로 금지하고 있었지만 주석은 실행되지 않는다(CLAUDE.md B9). 그리고
    capture()는 루프 진입 **전에** 첫 flush를 하므로, 라이브 호출 0회로 죽는 실행조차
    대상 파일을 이미 비운다 — 즉 "실행하다 실패했으니 괜찮겠지"가 성립하지 않는다.
    복구 수단은 유료 47문항 재캡처뿐이라 되돌리기가 없다.
    """
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    protected = run_phase_b.API_ROOT / "docs" / baseline_name
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--out", str(protected)],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_phase_b.main()
    assert exc_info.value.code == 2
    assert "기준선" in capsys.readouterr().err


def test_main_allows_non_baseline_out_path(monkeypatch, tmp_path):
    """과차단 대조군 — 날짜형 캡처 경로는 그대로 통과해야 한다(가드가 정상 사용을 막지 않음)."""
    monkeypatch.setenv("RUN_LIVE_SMOKE", "1")
    qs_path = tmp_path / "qs.json"
    qs_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    out_path = run_phase_b.API_ROOT / "docs" / "g2-capture-2026-08-02.json"
    monkeypatch.setattr(
        sys, "argv",
        ["run_phase_b.py", "--queryset", str(qs_path), "--out", str(tmp_path / out_path.name)],
    )

    run_phase_b.main()  # 거부되지 않고 정상 종료


# ── review pass 5 — 0건 매칭이 낡은 --out을 남기면 안 된다 ────────────────
def test_capture_with_zero_matching_items_overwrites_stale_out(tmp_path):
    """매칭 item이 0개여도 --out은 새로 써져야 한다.

    전엔 flush가 루프 안에만 있어 --out이 한 번도 안 써지고 **이전 실행의 낡은 파일이
    그대로 남았는데** main()은 exit 0으로 "0개 캡처 완료"를 냈다 — 그러면
    `run_phase_b.py --out X && score_ab.py --raw X` 체인이 다른 모델의 옛 캡처를
    새 baseline으로 채점한다.
    """
    out_path = tmp_path / "stale.json"
    out_path.write_text(
        json.dumps({"model": "OLD-MODEL", "results": {"STALE": [{"route_last": "A"}]}}),
        encoding="utf-8",
    )

    def run_search(query, context=None):  # 호출될 일이 없어야 한다
        raise AssertionError("라이브 호출이 일어나면 안 된다")

    raw = run_phase_b.capture({"items": []}, None, "new-model", run_search, out_path=out_path)

    assert raw == {"model": "new-model", "results": {}}
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk["model"] == "new-model"
    assert on_disk["results"] == {}  # 낡은 STALE 항목이 살아남지 않았다


def test_capture_rejects_item_without_id(tmp_path):
    """id 없는 item은 맨 KeyError가 아니라 어느 자리인지 말해주는 ValueError로 거부한다.

    이 파일의 다른 구조 오류(kind 오타·query 누락·중복 id)는 전부 그렇게 처리하는데,
    id만 중복검사·subset 필터가 먼저 색인해 원인불명 KeyError로 죽었다.
    """
    queryset = {"items": [{"kind": "single", "query": "q"}]}

    def run_search(query, context=None):
        raise AssertionError("사전검증에서 막혀 라이브 호출이 없어야 한다")

    with pytest.raises(ValueError, match="missing item id"):
        run_phase_b.capture(queryset, None, "test-model", run_search)
