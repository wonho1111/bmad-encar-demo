"""환경설정 로드 — pydantic-settings로 api/.env를 읽는다.

설계: 비밀값(Supabase·DB·Gemini)은 모두 Optional 기본 None.
  → 값이 없어도 앱은 기동된다(/health·/docs·미인증 401 경로는 비밀값 불필요).
  → 실제로 그 값이 필요한 지점(auth.py의 토큰 검증, db/readonly.py의 연결)에서
    require()로 "어떤 변수가 비었는지" 명확한 한국어 에러를 던진다(fail-loud, 1.4 패턴 계승).
"""

import os
import sys

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Supabase — JWT 검증에 사용
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    # 읽기전용 DB 직결 (Transaction pooler :6543 문자열 — AC-DB-1, SET LOCAL ROLE 트랜잭션 격리 전제)
    database_url: str | None = None

    # CORS 허용 오리진(쉼표 구분, 정확 매칭)
    cors_origins: str = "http://localhost:3000"
    # CORS 정규식 허용(선택) — preview처럼 매번 바뀌는 오리진을 패턴으로 허용한다.
    #   예: ^https://bmad-encar-demo-.*\.vercel\.app$  (미설정(None)이면 정확 매칭만 사용)
    cors_origin_regex: str | None = None

    # Gemini — 4.2+에서 사용 (4.1 미사용)
    gemini_api_key: str | None = None
    gemini_embedding_dim: int = 768
    # 별칭(gemini-flash-latest) 대신 명시 버전 고정 — 비용·재현성 안정화(데모/유료 단계).
    gemini_generation_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    # 리랭커 사이드카(4단계 부품 A) 주소 — 예: http://127.0.0.1:8801.
    # 미설정이면 rerank_client.rerank()가 즉시 None을 돌려주고 호출부는 기존 순서를 유지한다
    # (데모 환경엔 GPU 사이드카가 없을 수 있으므로 이 기능은 있으면 쓰고 없으면 조용히 꺼진다).
    reranker_url: str | None = None
    # 리랭커 사이드카 호출 타임아웃(초) — 기본 3.0은 로컬 GPU 사이드카 기준(1.1초/10건 실측,
    # reranker_service.py 상단 주석). Cloud Run CPU 사이드카는 건당 수 초가 걸려 이 기본값이
    # 너무 짧다 — 그럴 땐 배포 환경변수로 RERANKER_TIMEOUT_SECONDS를 올려 잡는다.
    reranker_timeout_seconds: float = 3.0

    # 4단계 부품 B — True면 routers/ai.py가 run_search_agent(툴콜링 에이전트)를,
    # False면 기존 run_search(고정 4분기 그래프)를 부른다. 기본 True(신규 경로가 기본).
    ai_agent_mode: bool = True


settings = Settings()


# ── LangSmith 트레이싱 env 승격 (FR51, DW-658) ──────────────────────────
# langsmith SDK는 위 Settings가 아니라 os.environ을 직접 읽는다(api/.env.example:22-40).
# Settings는 langchain_*를 선언하지 않고 extra="ignore"라 .env에 값이 있어도 조용히
# 버려지므로, 여기서 파일값을 os.environ으로 직접 옮긴다.
#
# 승격 함수 자체(_promote_env_from_dotenv)는 순수하게 "파일값을 os.environ에 옮긴다"만
# 하고, "언제 자동 실행할지"는 아래에서 따로 판단한다 — 이 둘을 분리해야 테스트가 실행
# 여부와 무관하게 이 함수를 직접 불러 검증할 수 있다(api/tests/test_langsmith_env_promotion.py).
def _promote_env_from_dotenv(env_path: str, keys: tuple[str, ...]) -> None:
    """`env_path`의 `keys`만 os.environ으로 승격한다. OS 환경변수가 이미 있으면 덮지 않는다
    (scripts/dev-api.sh가 DATABASE_URL 등을 export로 우선시키는 것과 동일한 원칙). 파일이
    없거나 키가 없거나 비어 있으면 조용히 아무것도 하지 않는다(트레이싱은 선택 기능).
    """
    values = dotenv_values(env_path)
    for key in keys:
        if key in os.environ:
            continue
        value = values.get(key)
        if value:
            os.environ[key] = value


_LANGSMITH_ENV_KEYS = ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY")

# 승격 시점이 중요하다: langsmith.utils.get_env_var는 lru_cache가 걸려 있어(첫 호출 때
# 값이 굳는다) app.main이 langgraph/langchain-google-genai를 import하는 순간 이미 한 번
# 호출된다(실측 확인). config.py는 main.py에서 그 import들보다 먼저 로드되므로, 여기 모듈
# 로드 시점에 즉시 실행해야 늦지 않는다(main.py의 lifespan 기동 훅은 이미 늦다 — 그 시점엔
# import가 끝난 뒤라 캐시가 굳어 있다).
#
# pytest 세션에서는 자동 실행을 건너뛴다: app/graph/graph.py의 run_search는 COMPILED_GRAPH
# .invoke()를 실제로 태우므로, 결정론 테스트가 그래프 노드 함수를 몽키패치해도 LangGraph
# 실행 자체는 트레이싱된다 — 로컬 개발자의 api/.env에 진짜 키가 있는 채로 pytest를 돌리면
# 매번 LangSmith에 트레이스가 올라간다(DW-658 origin이 기록한 "가짜 LLM 단위테스트 흔적"
# 재발 — tests.yml이 라이브 스모크를 CI 밖으로 뺀 것과 같은 이유로 여기서도 막는다). CI는
# 애초에 api/.env가 없어 원래도 안전하다.
if "pytest" not in sys.modules:
    _promote_env_from_dotenv(".env", _LANGSMITH_ENV_KEYS)


def require(name: str, value: str | None) -> str:
    """필수 환경변수 검증 — 비어 있으면 어떤 변수인지 알려주며 즉시 실패."""
    if not value:
        raise RuntimeError(
            f"환경변수 {name} 가(이) 설정되지 않았습니다. api/.env 파일을 확인하세요."
        )
    return value
