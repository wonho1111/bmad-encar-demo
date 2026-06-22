"""환경설정 로드 — pydantic-settings로 api/.env를 읽는다.

설계: 비밀값(Supabase·DB·Gemini)은 모두 Optional 기본 None.
  → 값이 없어도 앱은 기동된다(/health·/docs·미인증 401 경로는 비밀값 불필요).
  → 실제로 그 값이 필요한 지점(auth.py의 토큰 검증, db/readonly.py의 연결)에서
    require()로 "어떤 변수가 비었는지" 명확한 한국어 에러를 던진다(fail-loud, 1.4 패턴 계승).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Supabase — JWT 검증에 사용
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    # 읽기전용 DB 직결 (Session pooler 문자열)
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


settings = Settings()


def require(name: str, value: str | None) -> str:
    """필수 환경변수 검증 — 비어 있으면 어떤 변수인지 알려주며 즉시 실패."""
    if not value:
        raise RuntimeError(
            f"환경변수 {name} 가(이) 설정되지 않았습니다. api/.env 파일을 확인하세요."
        )
    return value
