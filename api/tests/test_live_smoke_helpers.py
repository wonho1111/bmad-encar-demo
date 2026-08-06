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

import ast
import pathlib

from tests.test_live_smoke import _missing_span_kinds

_LIVE_SMOKE_PATH = pathlib.Path(__file__).with_name("test_live_smoke.py")


def test_every_test_in_live_smoke_file_is_guarded_by_live_only():
    """위 모듈 독스트링이 선언한 "RUN_LIVE_SMOKE 없으면 0 passed" 계약을 실행되는 검사로 바꾼다.

    왜 필요한가(13.9 독립 후속 리뷰 실측): 그 계약은 지금까지 **독스트링과 주석에만** 있었다.
    실제로 `test_live_smoke.py`의 `@_live_only` 한 줄을 지우고 `RUN_LIVE_SMOKE` 없이 전체
    스위트를 돌리면 `545 passed, 5 skipped`가 나왔다 — 라이브 호출이 0인 실행이 초록 통과로
    보이는 바로 그 상태(DW-630)인데 **아무 검사도 red가 되지 않았다**. 주석은 계약이 아니다
    (CLAUDE.md B9). 파일을 AST로 읽어 `def test_*` 전부가 `@_live_only`를 달고 있는지 본다.

    이 검사가 못 보는 것(추측 아님, 실측): `RUN_LIVE_SMOKE=1`인데 쿼터(429)·키 부재로
    `_run_or_skip`이 전량 skip을 내는 경우는 여전히 못 잡는다 — 그건 마커가 아니라 실행
    시점의 문제라 conftest 훅이 필요하고, DW-649가 그 잔여분을 들고 있다.
    """
    tree = ast.parse(_LIVE_SMOKE_PATH.read_text(encoding="utf-8"))
    tests = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert tests, "라이브 스모크 파일에 테스트가 하나도 없다 — 파일이 비었거나 경로가 틀렸다."
    unguarded = [
        n.name for n in tests
        if not any(isinstance(d, ast.Name) and d.id == "_live_only" for d in n.decorator_list)
    ]
    assert unguarded == [], (
        f"`@_live_only`가 없는 라이브 테스트: {unguarded} — 이 파일은 SM-F/SM-G 게이트의 증거라 "
        "RUN_LIVE_SMOKE 없이 pass가 나오면 안 된다. 순수 함수 단위테스트라면 이 파일로 옮겨라."
    )


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
