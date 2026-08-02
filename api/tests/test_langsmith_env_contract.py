"""`.env.example`(루트·api)이 LangSmith 트레이싱에 대해 **주장하는 내용**을 못박는다(FR51, Story 13.7).

왜 이 파일이 따로 있나: 이 스토리의 실질 산출물은 두 견본 파일의 주석이고, 그 주석은
"어떤 값이 계측을 켜는가"를 단언한다. 그런데 그 주장을 검증하는 검사가 하나도 없었고,
실제로 **틀린 주장이 하나 실려 나갔다**(LANGSMITH_* 우선순위 — 2026-08-02 3차 리뷰에서
실행으로 반증). 문서는 계약이 아니므로 실행되는 검사로 바꾼다(CLAUDE.md B9).

`test_live_smoke_langsmith_tracing`과 역할이 다르다:
  · 저기: 계측이 실제로 LangSmith 서버에 트레이스를 남기는가 — 라이브·과금, CI 밖.
  · 여기: SDK가 env를 어떻게 해석하는가 — 네트워크·키·과금 없음, **CI의 api 잡에서 실제로 돈다**.
    이 스토리 산출물 중 CI가 지켜주는 유일한 검사다.

⚠️ 이 검사가 **안 보는 것**: 트레이스가 실제로 전송·기록되는지는 전혀 보지 않는다
  (그건 위 라이브 테스트의 몫). env 해석 규칙만 본다.
"""

import pytest
from langsmith.utils import get_env_var, tracing_is_enabled

_KEYS = (
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING_V2",
    "LANGCHAIN_TRACING",
    "LANGSMITH_TRACING",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_API_KEY",
)


@pytest.fixture
def env(monkeypatch):
    """LangSmith 관련 env를 전부 지운 깨끗한 상태에서 시작한다.

    `get_env_var`는 lru_cache가 걸려 있어(SDK 확인) 캐시를 비우지 않으면 앞 케이스의 값이
    남는다 — 이걸 빠뜨리면 검사가 전부 통과하면서 아무것도 안 보게 된다.
    """

    def _set(**kw):
        for k in _KEYS:
            monkeypatch.delenv(k, raising=False)
        for k, v in kw.items():
            monkeypatch.setenv(k, v)
        get_env_var.cache_clear()

    _set()
    yield _set
    get_env_var.cache_clear()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),  # 견본이 채우라고 지시하는 유일한 값
        ("True", False),  # 대문자 — 조용히 꺼진다
        ("1", False),
        ("yes", False),
        ("true ", False),  # 후행 공백(source가 값에 통째로 싣는다)
        ("true # 메모", False),  # 인라인 주석
        ("", False),
    ],
)
def test_tracing_v2_인식값은_정확히_소문자_true뿐(env, value, expected):
    """견본 주석의 '정확히 소문자 "true"만 켜진다' 주장."""
    env(LANGCHAIN_TRACING_V2=value)
    assert tracing_is_enabled() is expected


def test_접미사가_네임스페이스보다_먼저다(env):
    """견본 주석이 **틀리게 적었던** 지점 — 여기가 이 파일의 존재 이유다.

    실제 규칙: `TRACING_V2` 자리가 `TRACING` 자리보다 먼저 해석되고, `LANGSMITH_`가
    `LANGCHAIN_`를 이기는 것은 **같은 자리 안에서만**이다. 그래서 `LANGCHAIN_TRACING_V2`에
    값이 남아 있으면(그게 오타든 false든) 올바르게 설정한 `LANGSMITH_TRACING=true`를 덮는다.
    """
    # V2 자리에 값이 있으면 TRACING 자리는 아예 안 본다
    env(LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="true")
    assert tracing_is_enabled() is False, "LANGSMITH_TRACING이 이겼다 — 견본 주석 쪽이 맞다"

    # 오타 값도 마찬가지로 덮는다(꺼짐이 전파된다)
    env(LANGCHAIN_TRACING_V2="true ", LANGSMITH_TRACING="true")
    assert tracing_is_enabled() is False

    # V2 자리가 비어 있을 때만 TRACING 자리로 내려간다
    env(LANGSMITH_TRACING="true")
    assert tracing_is_enabled() is True

    # 같은 자리 안에서는 LANGSMITH_가 이긴다
    env(LANGSMITH_TRACING_V2="true", LANGCHAIN_TRACING_V2="false")
    assert tracing_is_enabled() is True


def test_api_key는_langsmith_네임스페이스가_이긴다(env):
    """견본 주석의 '셸에 LANGSMITH_API_KEY가 있으면 여기 채운 LANGCHAIN_API_KEY는 무시된다' 주장."""
    env(LANGCHAIN_API_KEY="k-견본", LANGSMITH_API_KEY="k-셸")
    assert get_env_var("API_KEY") == "k-셸"

    env(LANGCHAIN_API_KEY="k-견본")
    assert get_env_var("API_KEY") == "k-견본"


def test_tracing만_켜고_api_key가_없어도_켜진_것으로_보인다(env):
    """견본 주석의 '두 값은 함께 채워야 한다' 경고의 근거.

    SDK는 API_KEY 유무를 미리 확인하지 않으므로 `tracing_is_enabled()`는 True를 돌려준다 —
    "켜진 것처럼 보이지만 트레이스는 하나도 안 남는" 상태가 실재한다는 뜻이다.
    """
    env(LANGCHAIN_TRACING_V2="true")
    assert tracing_is_enabled() is True
    assert not get_env_var("API_KEY")
