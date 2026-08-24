"""`.env`의 LangSmith 키를 os.environ으로 승격하는 로직(DW-658 처방①)을 검증한다.

역할 구분(기존 `test_langsmith_env_contract.py`와 겹치지 않게):
  · 그 파일: os.environ에 **이미 어떤 문자열이 들어 있다고 가정**하고, langsmith SDK가 그
    문자열을 어떻게 해석하는가(env 이름 우선순위·정확값 매칭 등, SDK 소관)를 못박는다.
  · 여기: 그 문자열이 애초에 **`.env` 파일에서 os.environ으로 어떻게 옮겨지는가**(승격 로직,
    이번에 추가한 우리 코드 소관)를 본다.
  둘 다 있어야 "SDK 해석 규칙은 맞는데 값이 애초에 안 옮겨진다"(DW-658이 실제로 겪은 버그 —
  `api/.env`에 값이 있는데도 `tracing_is_enabled() == False`였다)를 놓치지 않는다.

⚠️ 이 검사가 **안 보는 것**(추측 아니라 실측):
  · `app.config`가 모듈 로드 시점에 `_promote_env_from_dotenv`를 **자동 호출하는지**는 보지
    않는다 — pytest 세션에서는 그 자동 호출을 의도적으로 건너뛴다(테스트가 실제 그래프를
    태워 LangSmith 쿼터를 쓰는 것을 막기 위해, config.py의 주석 참고). 여기서는 함수를
    직접 불러 로직만 검증하고, 실제 서버 기동에서 자동 승격이 일어나는지는 스토리 검증
    섹션(사람이 `bash scripts/dev-api.sh`로 직접 확인)의 몫이다.
  · `get_env_var`의 lru_cache 타이밍(캐시가 이미 굳은 뒤 승격하면 늦는다는 것) 자체는 여기서
    재현하지 않는다 — 이 파일은 매 테스트 전 캐시를 비우고 시작해 그 함정을 피해서 승격
    로직 자체만 본다.
"""

import os

import pytest
from langsmith.utils import get_env_var, tracing_is_enabled

from app.config import _promote_env_from_dotenv

_KEYS = ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY")
# get_env_var가 참조하는 전체 후보 — 승격 대상이 아닌 LANGSMITH_* 까지 깨끗이 비워야
# tracing_is_enabled()가 이전 테스트의 잔여값이 아니라 이 테스트가 만든 상태만 본다.
_ALL_RELATED_KEYS = _KEYS + (
    "LANGSMITH_TRACING_V2",
    "LANGSMITH_TRACING",
    "LANGCHAIN_TRACING",
    "LANGSMITH_API_KEY",
)


@pytest.fixture
def clean_env(monkeypatch):
    for k in _ALL_RELATED_KEYS:
        monkeypatch.delenv(k, raising=False)
    get_env_var.cache_clear()
    yield
    get_env_var.cache_clear()


def _write_env(path, **kv):
    path.write_text("\n".join(f"{k}={v}" for k, v in kv.items()) + "\n", encoding="utf-8")


def test_파일값이_있으면_승격되어_트레이싱이_켜진다(clean_env, tmp_path):
    env_file = tmp_path / ".env"
    _write_env(env_file, LANGCHAIN_TRACING_V2="true", LANGCHAIN_API_KEY="k-test")

    _promote_env_from_dotenv(str(env_file), _KEYS)

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "k-test"
    assert tracing_is_enabled() is True


def test_os_환경변수가_이미_있으면_파일값이_덮지_않는다(clean_env, monkeypatch, tmp_path):
    # dev-api.sh가 DATABASE_URL 등을 export하는 것과 같은 우선순위 원칙 — 셸 값이 이긴다.
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    env_file = tmp_path / ".env"
    _write_env(env_file, LANGCHAIN_TRACING_V2="true")

    _promote_env_from_dotenv(str(env_file), _KEYS)

    assert os.environ["LANGCHAIN_TRACING_V2"] == "false", "OS 값이 파일값에 덮였다"
    assert tracing_is_enabled() is False


def test_값이_없으면_조용히_아무것도_안_한다(clean_env, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    _promote_env_from_dotenv(str(env_file), _KEYS)

    assert "LANGCHAIN_TRACING_V2" not in os.environ
    assert "LANGCHAIN_API_KEY" not in os.environ
    assert tracing_is_enabled() is False


def test_파일이_아예_없어도_에러없이_통과한다(clean_env, tmp_path):
    missing = tmp_path / "no-such.env"

    _promote_env_from_dotenv(str(missing), _KEYS)

    assert "LANGCHAIN_TRACING_V2" not in os.environ
