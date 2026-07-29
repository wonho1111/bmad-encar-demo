#!/usr/bin/env python3
"""동결된 문서에 대한 쓰기를 차단한다 (PreToolUse 훅).

## 왜 이게 있나

**열린 일 장부는 `_bmad-output/implementation-artifacts/deferred-work.md` 하나다**
(2026-07-29 통합, CLAUDE.md B8). 장부가 2개였을 때 #18(테이블 GRANT)이 한쪽은 "dev 자율",
다른 쪽은 "사용자 승인 필수"로 **정반대 판정**을 들고 1일간 공존했고, Epic 9의 첫
마이그레이션이 하필 그 축을 건드리기 직전이었다.

## ⚠️ 2026-07-29에 차단 방향이 **뒤집혔다**

2026-07-15~29 사이엔 이 훅이 정확히 반대로 동작했다 — `deferred-work.md`를 막고
`docs/tech-debt.md`로 보냈다. 그 방향은 **도구와 싸우는 방향이었고, 졌다**:

- BMAD·bmad-loop 상류가 `deferred-work.md`를 유일한 ledger로 규정한다(bmad-loop README:231).
  로컬 `.claude/skills/bmad-*` 전체와 양쪽 상류 README에서 `tech-debt`는 **0건**이다.
- 그래서 vendor 스킬 14개 파일이 전부 `deferred-work.md`에 쓰라고 지시했고, 이 훅과
  `_bmad/custom/*.toml`의 프롬프트 주입은 그 지시를 **막는 데** 쓰였다.
- 그런데 **bmad-loop 엔진에는 둘 다 안 닿는다.** 엔진은 Claude 세션이 아니라 오케스트레이터
  파이썬 프로세스라 PreToolUse 훅이 **호출조차 되지 않고**, 프롬프트도 읽지 않는다.
  실제로 `DW-1`~`DW-9`가 "⛔ 여기 쓰지 마라"라고 적힌 파일에 그대로 쌓였다.
- 결정타: 통합 직전 `bmad-loop sweep --dry-run` 실측에서 `deferred-work.md`의 경위 산문이
  **"옛 형식으로 적힌 열린 일 61건"으로 오독**됐다. 사람이 sweep을 치는 순간 그 파일이
  통째로 재작성될 상태였다.

방향을 뒤집으니 vendor 스킬 14개의 지시가 **저절로 맞는 지시**가 됐다. 막을 것이 없어져
`_bmad/custom/*.toml`의 장부 관련 주입도 함께 걷어냈다. 남은 것은 반대 방향 — 습관이나 옛
참조(리포에 600여 곳) 때문에 **동결 문서에 새로 쓰는 것**을 막는 일이다.

주석과 문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다(CLAUDE.md B9).
그게 이 파일이다.

## 무엇을 하나

Write·Edit·NotebookEdit·MultiEdit이 동결 문서를 대상으로 하면 **차단**하고, 어디에 적어야
하는지 알려준다. 읽기는 막지 않는다 — 경위를 찾아보는 것은 이 문서들의 정당한 용도다.

## 이 검사가 보지 못하는 것 (추측 아니라 실측)

- **셸을 통한 쓰기는 못 막는다.** `Bash(echo ... >> tech-debt.md)`는 이 훅의 matcher
  (Write|Edit|MultiEdit|NotebookEdit) 밖이다. 명령 문자열을 파싱하면 오탐(파일명을 단순
  언급하는 grep 등)이 많아 넣지 않았다. 이 훅의 목적은 **에이전트가 옛 참조를 따라가다
  실수하는 경로**를 막는 것이고, 그 경로는 전부 Write/Edit이다.
- **다른 문서가 늙는 것은 못 막는다.** `deferred-work.md`에 등재했는지는 검사하지 않는다.
- **bmad-loop 엔진의 직접 쓰기는 여전히 못 막는다.** 다만 통합 후에는 **엔진이 쓰는 파일이
  맞는 파일**이라 이제 문제가 아니다 — 이것이 방향을 뒤집은 이유 그 자체다.

## 검증 (2026-07-29, B4 — "만들었다"가 아니라 "잡는다"가 완료)

아래 red/green을 실제로 돌려 확인한 결과는 커밋 메시지에 있다.
- red:   Write → docs/tech-debt.md → exit 2
- red:   Write → docs/decisions-archive.md → exit 2
- green: Write → deferred-work.md → exit 0  (이제 여기가 정상 경로다)
- green: Read  → docs/tech-debt.md → exit 0  (쓰기 도구가 아니므로 통과)
"""

import json
import sys

_LEDGER = "_bmad-output/implementation-artifacts/deferred-work.md"

_WHERE = (
    "  · 열린 일(부채·이월·defer·회고 액션)\n"
    f"      → {_LEDGER} 에 `### DW-<번호>`로 등재\n"
    "      형식: origin / location / severity / reason / **trigger** / status\n"
    "      트리거를 빼지 마세요 — '이월'만 적힌 항목은 다음 작업에서 조용히 또 밀립니다.\n"
    "  · 지켜야 하는 계약 → docs/conventions.md · _bmad-output/project-context.md\n"
    "  · 왜 그렇게 정했나 → docs/decisions-archive.md (이것도 append 금지, 경위 보관용)"
)

# 동결된 문서들(경로 조각으로 매칭 — 절대/상대 경로 어느 쪽이든 잡힌다).
FROZEN = {
    "docs/tech-debt.md": (
        "이 문서는 2026-07-29에 **전방 동결**됐습니다 — 새 항목을 받지 않습니다.\n"
        "열린 항목 177건은 전부 장부로 이관됐고, 여기 남은 것은 닫힌 부채의 경위와\n"
        "옛 번호(`#N` → `DW-(N+300)`)를 찾아가는 이관 색인뿐입니다.\n\n"
        + _WHERE
        + "\n\n옛 참조를 보고 여기 적으려던 것이라면, 그 참조는 이관 색인이 받아줍니다."
    ),
    "docs/decisions-archive.md": (
        "이 문서는 **경위 보관용**입니다 — '왜 그렇게 정했나'만 담고 열린 일을 갖지 않습니다.\n"
        "규칙처럼 읽히는 문장을 여기 새로 적으면 다음 사람이 정본과 헷갈립니다.\n\n" + _WHERE
    ),
}

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # 훅이 입력을 못 읽으면 **통과시킨다** — 판단 못 하는 상태에서 작업을 막지 않는다.
        return 0

    tool = payload.get("tool_name") or payload.get("toolName") or ""
    if tool not in WRITE_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    target = str(
        tool_input.get("file_path")
        or tool_input.get("filePath")
        or tool_input.get("notebook_path")
        or ""
    )
    if not target:
        return 0

    normalized = target.replace("\\", "/")
    for frozen_path, reason in FROZEN.items():
        if normalized.endswith(frozen_path) or frozen_path in normalized:
            print(
                f"⛔ 차단: {frozen_path} 는 쓰기 금지 파일입니다.\n\n{reason}",
                file=sys.stderr,
            )
            return 2  # exit 2 = 도구 호출 차단 + stderr를 에이전트에게 전달

    return 0


if __name__ == "__main__":
    sys.exit(main())
