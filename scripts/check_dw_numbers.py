#!/usr/bin/env python3
"""열린 일 장부(`deferred-work.md`)의 DW 번호 중복을 잡는다.

## 왜 이게 있나

번호는 사람(또는 세션)이 파일을 훑어 "제일 큰 번호 + 1"을 눈으로 골라 붙인다. 그래서 **여러
주체가 같은 날 등재하면 반드시 겹친다.** 2026-08-10 하루에 세 번 겹쳤다:

1. 오전 — Epic 16 묶음 코드리뷰가 `DW-770` 중복을 발견(카드 radius / 히어로 글로우).
   나중 등재분을 `DW-787`로 옮겨 해소.
2. 오후 — Story 16.11 **dev 세션**이 새 항목에 `DW-787`을 다시 붙였다(방금 비운 번호가 아니라
   **이미 쓰고 있는** 번호였다).
3. 그 정정 중 — `DW-788`로 옮기려 했더니 **같은 리뷰 패스의 다른 항목이 788을 이미** 집었다.
   결국 `DW-796`으로 갔다.

중복 ID는 장부의 기본 기능을 깬다. `[[DW-xxx]]` 링크가 어느 항목을 가리키는지 알 수 없고,
`grep DW-xxx`로 찾으면 무관한 두 문제가 함께 나온다. `trigger:`("언제 다시 볼지")를 따라가는
흐름도 끊긴다.

주석·문서로 "번호 겹치지 마세요"라고 적는 것은 계약이 아니다 — 실제로 세 번 어겨졌다.
그래서 **실행되는 검사**로 바꾼다(CLAUDE.md B9).

## 무엇을 보나 / 무엇을 안 보나

- 본다: `### DW-<번호>:` 형식 제목의 **번호 중복**, 그리고 번호가 없는 `### DW-` 제목.
- **안 본다**(추측 아니라 명시): 본문 품질·`trigger:` 유무·`status:` 값·`[[DW-xxx]]` 링크가
  실재하는 항목을 가리키는지. 그건 사람이 볼 몫이고, 이 검사는 **기계가 확실히 판정할 수 있는
  한 가지**만 본다.

## 쓰는 법

    python3 scripts/check_dw_numbers.py            # 중복 있으면 exit 1
    python3 scripts/check_dw_numbers.py --path X   # 다른 파일로
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_PATH = "_bmad-output/implementation-artifacts/deferred-work.md"

# 정본 형식 — `### DW-748: 제목`. 이것만 "정상 항목 제목"으로 센다.
HEADING = re.compile(r"^###\s+DW-(\d+)\s*:")

# ⚠️ **정본 형식만 보면 형식을 살짝 어긋내는 것으로 검사를 통째로 우회할 수 있다.**
# 2026-08-10 후속 코드리뷰(adversarial)가 실측으로 6가지 우회를 찾았다 — 아래 전부
# 옛 버전에서는 중복으로도, 형식오류로도 **잡히지 않고 그냥 무시**됐다:
#     `#### DW-770:`(해시 4개) · ` ### DW-770:`(앞 공백) · `> ### DW-770:`(인용)
#     `### dw-770:`(소문자) · `###DW-770:`(공백 없음) · `### [보류] DW-770:`(접두어)
# 그래서 판정을 두 단계로 나눈다:
#   ① SUSPECT — "제목 줄인데 DW 번호를 달고 있는 것"을 **느슨하게** 전부 잡는다.
#   ② 그중 HEADING(정본)이 아니면 형식오류로 실패시킨다.
# 느슨하게 잡되 **번호(숫자)가 실제로 붙어 있을 때만** 본다 — 그래야 이 장부 머리말의
# 형식 예시(`> ### DW-<번호>: <한 줄 제목>`, 숫자가 아니라 자리표시자)를 오탐하지 않는다.
# (실측: 장부에서 `#`로 시작하며 DW를 언급하는 줄은 그 예시 하나뿐이다.)
# ⚠️ **DW 토큰이 제목 맨 앞 근처에 있을 때만** 본다(접두어 한 덩어리까지 허용).
# 처음엔 `.*?`로 줄 어디서든 찾게 했더니 **오탐이 났다**(실측): 장부 5600행은 `#`로 시작하는
# 산문 주석인데 문장 한참 뒤에 `DW-754`를 인용한다 — 제목이 아닌데 제목으로 잡혔다.
# 그래서 `#` 뒤에 올 수 있는 것을 "짧은 접두어 한 덩어리"로 제한한다(`### [보류] DW-770:` 통과,
# 산문 주석은 제외). 이 경계 역시 추측이 아니라 실제 장부로 재서 정했다.
SUSPECT = re.compile(r"^\s*>*\s*#{1,6}\s*(?:\S{1,12}\s+)?[Dd][Ww]\s*-\s*\d+")

# 0 패딩·전각 숫자는 문제가 아니다(실측): `int("0770") == int("７７０") == 770` 이라
# 같은 번호로 합쳐져 중복이 정상적으로 잡힌다. 그래서 별도 처리를 두지 않는다.


def main() -> int:
    ap = argparse.ArgumentParser(description="deferred-work.md의 DW 번호 중복 검사")
    ap.add_argument("--path", default=DEFAULT_PATH)
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"❌ 장부 파일을 찾을 수 없다: {path}", file=sys.stderr)
        return 2

    seen: dict[int, list[int]] = defaultdict(list)
    malformed: list[tuple[int, str]] = []

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = HEADING.match(line)
        if m:
            seen[int(m.group(1))].append(lineno)
        elif SUSPECT.match(line):
            # 제목 줄인데 정본 형식이 아니다 → 중복 검사에서 새어나가므로 실패시킨다.
            malformed.append((lineno, line.strip()[:80]))

    dupes = {n: ls for n, ls in seen.items() if len(ls) > 1}

    if not dupes and not malformed:
        nums = sorted(seen)
        nxt = (nums[-1] + 1) if nums else 1
        print(f"✅ DW 번호 이상 없음 — 항목 {len(seen)}건, 최대 DW-{nums[-1] if nums else 0}. "
              f"다음에 쓸 번호: DW-{nxt}")
        return 0

    for num in sorted(dupes):
        lines = ", ".join(str(x) for x in dupes[num])
        print(f"❌ DW-{num} 이 {len(dupes[num])}번 등장한다 (줄 {lines})", file=sys.stderr)
    for lineno, text in malformed:
        print(f"❌ DW 제목인데 정본 형식이 아니다 (줄 {lineno}): {text}\n   → 정본은 `### DW-<숫자>: <제목>` 이다. 이 형태를 벗어나면 중복 검사가 그 항목을 통째로 건너뛴다.", file=sys.stderr)

    if dupes:
        nums = sorted(seen)
        print(
            "\n고치는 법: **먼저 쓰던 항목을 그대로 두고 나중에 등재된 쪽의 번호만 옮긴다** — "
            f"지금 비어 있는 다음 번호는 DW-{nums[-1] + 1} 이다. 옮긴 항목 본문에 정정 사유를 "
            "한 줄 남기고, 그 항목을 가리키던 참조(코드 주석·테스트·스펙)도 함께 고친다.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
