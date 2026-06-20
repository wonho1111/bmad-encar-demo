"""Supabase JWT 검증 — 로그인한 사용자만 AI 검색을 쓰게 한다(AC3).

방식 A(채택): supabase-py `auth.get_user(token)`로 Auth 서버에 토큰을 검증시킨다.
  · 장점: 추가 비밀값 불필요(SUPABASE_URL + ANON_KEY만), 폐기 토큰까지 서버가 판정.
  · 미인증(헤더 없음/형식 오류)은 네트워크 호출 전에 바로 401 → 비밀값 없이도 401 경로 동작.
대안 B(JWKS 로컬 검증)는 성능 이슈 발생 시 후속에서 교체(스토리 Dev Notes 참조).
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import require, settings

# auto_error=False: 헤더가 없거나 형식이 틀려도 예외 대신 None을 받아 우리가 직접 401을 만든다.
_bearer = HTTPBearer(auto_error=False)


def _unauthorized(message: str = "로그인이 필요합니다.") -> HTTPException:
    # detail에 공통 에러 포맷을 담아 둔다(main.py의 핸들러가 {error:{...}}로 직렬화).
    return HTTPException(
        status_code=401, detail={"error": {"code": "unauthorized", "message": message}}
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """유효한 Bearer 토큰이면 사용자 객체를 반환, 아니면 401."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    token = credentials.credentials

    # 토큰이 있을 때만 Supabase 설정이 필요 → 이 시점에 fail-loud로 검증.
    url = require("SUPABASE_URL", settings.supabase_url)
    key = require("SUPABASE_ANON_KEY", settings.supabase_anon_key)

    # supabase-py import는 함수 안에서 — 미인증 401 경로(토큰 없음)는 이 의존성을 건드리지 않아
    # supabase 미설치/미설정 환경에서도 401 테스트가 가능하다.
    from supabase import create_client

    client = create_client(url, key)
    try:
        resp = client.auth.get_user(token)
    except Exception:
        raise _unauthorized("유효하지 않은 인증 토큰입니다.")

    user = getattr(resp, "user", None)
    if user is None:
        raise _unauthorized("유효하지 않은 인증 토큰입니다.")
    return user
