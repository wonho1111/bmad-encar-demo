"""`test_live_smoke._missing_span_kinds` 순수 함수 단위테스트(DW-641).

왜 별도 파일인가(P6, 13.9 3차 리뷰):
  `tests/test_live_smoke.py`는 SM-F/SM-G 게이트의 **증거 파일**이다 — "라이브를 실제로 돌려
  통과했다"만 초록으로 보여야 한다. 이 단위테스트들이 그 파일 안에 있으면 RUN_LIVE_SMOKE가
  꺼진 실행이 `5 passed, 6 skipped`(실측)로 끝나, 라이브 커버리지가 0인데도 초록 통과처럼
  읽힌다 — DW-630("전부 skip이 초록으로 보이면 안 된다")이 정확히 막으려던 상태다.
  반대로 모듈 단위 `pytestmark = skipif`로 되돌리면 이 순수 함수 단위테스트까지 함께 스킵돼
  DW-641("그 함수만 단위테스트한다")이 깨진다. 두 요건을 동시에 만족시키는 방법은 파일 분리뿐:
    · test_live_smoke.py       → 라이브 테스트만. RUN_LIVE_SMOKE 없으면 **0 passed**.
    · test_live_smoke_helpers.py(이 파일) → 순수 함수만. 환경과 무관하게 **항상 돈다**.
  판정 함수는 import로 가져오므로 사본이 생기지 않는다(로직은 계속 한 곳에만 있다).
"""

from tests.test_live_smoke import _missing_span_kinds


class _FakeRun:
    """LangSmith run 객체 흉내(테스트 전용) — `_missing_span_kinds`가 읽는 두 속성만 있다."""

    def __init__(self, run_type, name):
        self.run_type = run_type
        self.name = name


def test_missing_span_kinds_all_present():
    runs = [_FakeRun("llm", "ChatGoogleGenerativeAI"), _FakeRun("chain", "router_node")]
    assert _missing_span_kinds(runs, {"router_node"}) == []


def test_missing_span_kinds_detects_no_runs_at_all():
    assert _missing_span_kinds([], {"router_node"}) == ["root"]


def test_missing_span_kinds_detects_missing_llm_span():
    runs = [_FakeRun("chain", "router_node")]
    assert _missing_span_kinds(runs, {"router_node"}) == ["llm"]


def test_missing_span_kinds_detects_missing_node_span():
    runs = [_FakeRun("llm", "ChatGoogleGenerativeAI")]
    assert _missing_span_kinds(runs, {"router_node"}) == ["node"]


def test_missing_span_kinds_detects_both_missing():
    runs = [_FakeRun("chain", "some_other_chain")]
    assert _missing_span_kinds(runs, {"router_node"}) == ["llm", "node"]
