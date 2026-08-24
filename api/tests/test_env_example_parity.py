"""루트 `.env.example`의 api 섹션과 `api/.env.example`의 **키 이름 집합**이 어긋나지 않게 못박는다.

왜 있나(DW-616, 2026-08-03 후속 리뷰에서 실측 후 착수): 두 견본의 락스텝은 이 저장소의
오래된 관례인데 **지키는 장치가 없었다**. Story 13.7의 리뷰 패스 두 번이 "두 파일 주석
복붙" 지적을 "의도된 락스텝 관례"라는 근거로 기각했지만, 정작 그 관례를 실행하는 검사는
하나도 없었다 — 주석·관례는 계약이 아니다(CLAUDE.md B9).

실패 모드가 하필 이 스토리가 없애려던 그 함정이다: LangSmith 키를 한쪽 견본에만 적으면,
다른 쪽만 읽은 사람은 "설정했는데 트레이스가 안 남는" 상태에 그대로 빠진다.

⚠️ 단순 파일 비교가 아니라 **키 이름 집합** 비교인 이유(실측): 두 파일은 문구도 경로도
  다르다(`source api/.env` vs `source .env`) — 그건 의도된 차이라 비교 대상이 아니다.

⚠️ 이 검사가 **안 보는 것**(추측 아니라 실측):
  · 값·주석·순서는 안 본다. 키 이름만 본다. 그래서 한쪽 주석만 틀리게 고치는 것은 못 잡는다
    (LangSmith env 해석 규칙에 한해서는 `test_langsmith_env_contract.py`가 그 몫을 맡는다).
  · 견본에 있는 키가 실제로 앱에서 읽히는지는 안 본다(`config.py` Settings와의 대조 아님).
  · 주석 처리된 키(`# SUPABASE_URL=`)는 세지 않는다 — app 섹션이 통째로 그런 형태다.
"""

import re
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
_ROOT_ENV_EXAMPLE = _API_DIR.parent / ".env.example"
_API_ENV_EXAMPLE = _API_DIR / ".env.example"

# 루트 견본에서 api 섹션을 자르는 머리글(파일에 실제로 있는 문자열).
_API_SECTION_HEADER = "# ===== api/.env"
_ANY_SECTION_HEADER = re.compile(r"^# ===== ")

_KEY_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=")

# 2026-08-03 실측한 **의도된 비대칭**: CORS 두 키는 api 견본에만 있고 루트 견본의 api
# 섹션에는 없다. DW-616이 제안한 "키 집합의 완전 일치" 검사는 이 상태에서 그대로 red가
# 난다 — 그래서 여기 측정값으로 고정해 둔다. 목적은 면제가 아니라 **동결**이다:
# 새 비대칭이 생기면(어느 방향이든) 이 목록 밖이라 red가 난다.
_KNOWN_API_ONLY = frozenset({"CORS_ORIGINS", "CORS_ORIGIN_REGEX"})


def _keys(lines):
    return {m.group(1) for m in (_KEY_LINE.match(ln) for ln in lines) if m}


def _root_api_section_lines():
    lines = _ROOT_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(_API_SECTION_HEADER))
    for end in range(start + 1, len(lines)):
        if _ANY_SECTION_HEADER.match(lines[end]):
            return lines[start:end]
    return lines[start:]


def test_두_견본의_api_키_집합이_락스텝을_유지한다():
    root_keys = _keys(_root_api_section_lines())
    api_keys = _keys(_API_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines())

    assert root_keys, f"{_ROOT_ENV_EXAMPLE}의 api 섹션에서 키를 하나도 못 읽었다(파서가 눈 감음)"
    assert api_keys, f"{_API_ENV_EXAMPLE}에서 키를 하나도 못 읽었다(파서가 눈 감음)"

    # 방향 1: 루트 견본에만 있는 키 — api 견본만 보는 개발자가 놓친다
    only_root = root_keys - api_keys
    assert not only_root, (
        f"루트 .env.example의 api 섹션에만 있는 키 {sorted(only_root)} — "
        f"api/.env.example에도 같은 키를 추가해라(락스텝)"
    )

    # 방향 2: api 견본에만 있는 키 — 루트 견본 하나로 전체를 훑는 사람이 놓친다
    only_api = api_keys - root_keys - _KNOWN_API_ONLY
    assert not only_api, (
        f"api/.env.example에만 있는 키 {sorted(only_api)} — "
        f"루트 .env.example의 api 섹션에도 추가하거나, 의도된 비대칭이면 "
        f"이 파일의 _KNOWN_API_ONLY에 근거와 함께 등록해라"
    )


def test_langsmith_두_키가_양쪽_견본에_모두_있다():
    """DW-616이 지목한 구체적 실패 모드 — FR51 키가 한쪽에만 적히는 것 — 를 이름으로 못박는다."""
    expected = {"LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY"}
    assert expected <= _keys(_root_api_section_lines()), "루트 견본 api 섹션에 LangSmith 키 누락"
    assert expected <= _keys(_API_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()), (
        "api/.env.example에 LangSmith 키 누락"
    )
