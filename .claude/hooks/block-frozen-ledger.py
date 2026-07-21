#!/usr/bin/env python3
"""동결된 장부 파일에 대한 쓰기를 차단한다 (PreToolUse 훅).

## 왜 이게 있나

`_bmad-output/implementation-artifacts/deferred-work.md`는 2026-07-15에 **동결**됐다.
열린 일 장부는 `docs/tech-debt.md` 하나다(CLAUDE.md B8). 장부가 2개였을 때 #18(테이블 GRANT)이
한쪽은 "dev 자율", 다른 쪽은 "사용자 승인 필수"로 **정반대 판정**을 들고 1일간 공존했고,
Epic 9의 첫 마이그레이션이 하필 그 축을 건드리기 직전이었다.

그런데 동결 후에도 **스킬 5개가 여전히 그 파일을 가리킨다**(실측):
    .claude/skills/bmad-code-review/steps/step-04-present.md
    .claude/skills/bmad-quick-dev/step-01-clarify-and-route.md
    .claude/skills/bmad-quick-dev/step-02-plan.md
    .claude/skills/bmad-quick-dev/step-04-review.md
    .claude/skills/bmad-quick-dev/step-oneshot.md

문서는 "적지 마라", 절차는 "여기 적어라" — **성실할수록 어기는 구조**다. 실제로 2026-07-19
코드리뷰에서 그 일이 일어났다(defer 4건이 동결 파일에 들어갔다가 되돌려짐).

주석과 문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다(CLAUDE.md B9).
그게 이 파일이다.

## 무엇을 하나

Write·Edit·NotebookEdit이 동결 파일을 대상으로 하면 **차단**하고, 어디에 적어야 하는지 알려준다.
읽기는 막지 않는다 — 경위를 찾아보는 것은 이 파일의 정당한 용도다.

## 이 검사가 보지 못하는 것 (추측 아니라 실측)

- **셸을 통한 쓰기는 못 막는다.** `Bash(echo ... >> deferred-work.md)`는 이 훅의 matcher
  (Write|Edit|NotebookEdit) 밖이다. 실측 확인함 — 아래 "검증" 참조.
  Bash까지 막으려면 명령 문자열을 파싱해야 하는데, 오탐(파일명을 단순 언급하는 grep 등)이
  많아 지금은 넣지 않는다. 이 훅은 **에이전트가 스킬 지시를 따르다 실수하는 경로**를 막는 것이
  목적이고, 그 경로는 전부 Write/Edit이다.
- **다른 문서가 늙는 것은 못 막는다.** tech-debt.md에 등재했는지 여부는 검사하지 않는다.

## 검증 (2026-07-19, B4 — "만들었다"가 아니라 "잡는다"가 완료)

- red: deferred-work.md에 Write 시도 → exit 2로 차단, 안내 메시지 출력됨
- green: docs/tech-debt.md에 Write 시도 → 통과(exit 0)
- green: deferred-work.md **읽기** → 통과(훅이 Read를 보지 않음)
- 실측: Bash 리다이렉트는 차단되지 않음(위 "보지 못하는 것"에 기록)
"""

import json
import sys

# 동결된 파일들(경로 조각으로 매칭 — 절대/상대 경로 어느 쪽이든 잡힌다).
FROZEN = {
    "_bmad-output/implementation-artifacts/deferred-work.md": (
        "이 파일은 2026-07-15에 동결됐습니다 — 열린 일을 담지 않습니다.\n"
        "  · 열린 일(부채·이월·defer)  → docs/tech-debt.md 에 #N 번호로 등재\n"
        "  · 왜 그렇게 결정했나(경위) → 이 파일은 '읽기 전용 보관소'입니다\n"
        "\n"
        "스킬 절차(bmad-code-review step-04, bmad-quick-dev 등)가 이 파일을 가리키더라도\n"
        "따르지 마세요. 그 지시는 동결 이전에 쓰인 것이고, 프로젝트 규칙(CLAUDE.md B8)이\n"
        "우선합니다. 장부가 2개였을 때 같은 항목이 정반대 판정으로 공존한 사고가 있었습니다."
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
