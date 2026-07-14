"""Supabase JWT 검증 — 로그인한 사용자만 통과.

방식 A(채택): supabase-py `auth.get_user(token)`로 Auth 서버에 토큰을 검증시킨다.
  · 장점: 추가 비밀값 불필요(SUPABASE_URL + ANON_KEY만), 폐기 토큰까지 서버가 판정.
  · 미인증(헤더 없음/형식 오류)은 네트워크 호출 전에 바로 401 → 비밀값 없이도 401 경로 동작.
대안 B(JWKS 로컬 검증)는 성능 이슈 발생 시 후속에서 교체(스토리 Dev Notes 참조).

FR58(8.5) 접근 게이트 계약 — 상세는 `docs/conventions.md` §8:
  · **열람**(매물 목록·상세)은 anon 허용 — DB RLS의 anon SELECT 정책(0011)이 담당하며
    이 모듈을 거치지 않는다.
  · **행동**(AI 검색·문의·등록·찜)은 로그인 필수. `/ai/search`도 여기 속한다 —
    검색 1회 = Gemini 호출 3회 내외 = 실제 과금이라 "보기만 하는" 열람이 아니다.
  ⚠️ `ai_readonly` 롤과 `sql_guard`는 **DB 권한**을 지키지 **API 키 지출**은 막지 않는다.
    "인증을 완화해도 권한 누수가 없다"는 참이지만 "열어도 안전하다"를 뜻하지 않는다 —
    JWT가 호출자를 식별하는 유일한 수단이고, 그게 곧 유일한 과금 울타리다.
"""

import asyncio
import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import require, settings

logger = logging.getLogger(__name__)

# auto_error=False: 헤더가 없거나 형식이 틀려도 예외 대신 None을 받아 우리가 직접 401을 만든다.
_bearer = HTTPBearer(auto_error=False)


def _unauthorized(message: str = "로그인이 필요합니다.") -> HTTPException:
    # detail에 공통 에러 포맷을 담아 둔다(main.py의 핸들러가 {error:{...}}로 직렬화).
    return HTTPException(
        status_code=401, detail={"error": {"code": "unauthorized", "message": message}}
    )


def _auth_unavailable() -> HTTPException:
    # Auth 서버 도달 실패(네트워크·5xx)는 인증 실패가 아니라 일시적 서버 문제 → 503.
    # 정상 사용자가 Supabase 장애 중 "토큰 무효"로 잘못 거절되는 것을 막는다.
    return HTTPException(
        status_code=503,
        detail={
            "error": {
                "code": "auth_unavailable",
                "message": "인증 서버에 일시적으로 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
            }
        },
    )


def _validate_token(token: str):
    """토큰을 Supabase Auth 서버에 검증시켜 사용자 객체를 반환. 무효면 401, 전송 실패면 503."""
    # 토큰이 있을 때만 Supabase 설정이 필요 → 이 시점에 fail-loud로 검증.
    url = require("SUPABASE_URL", settings.supabase_url)
    key = require("SUPABASE_ANON_KEY", settings.supabase_anon_key)

    # supabase-py import는 함수 안에서 — 미인증 401 경로(토큰 없음)는 이 의존성을 건드리지 않아
    # supabase 미설치/미설정 환경에서도 401 테스트가 가능하다.
    from supabase import create_client

    try:
        # create_client·get_user 모두 try 안에 둔다(클라이언트 초기화 실패도 여기서 잡는다).
        client = create_client(url, key)
        resp = client.auth.get_user(token)
    except Exception as exc:
        # 토큰 자체가 무효면 supabase가 인증 오류를 던지지만, 네트워크 끊김·Auth 서버 5xx 등
        # "도달 실패"도 같은 자리에서 예외가 된다. 후자를 401로 위장하면 정상 사용자가
        # 장애 중 잘못 거절되므로, 전송 계열 오류는 503으로 분리하고 원인을 로깅한다.
        if _is_transport_error(exc):
            logger.warning("Supabase Auth 도달 실패 — 503 반환: %r", exc)
            raise _auth_unavailable()
        logger.info("토큰 검증 실패 — 401 반환: %r", exc)
        raise _unauthorized("유효하지 않은 인증 토큰입니다.")

    user = getattr(resp, "user", None)
    if user is None:
        raise _unauthorized("유효하지 않은 인증 토큰입니다.")
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """유효한 Bearer 토큰이면 사용자 객체를 반환, 아니면 401."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    # _validate_token은 Auth 서버로 네트워크 왕복을 하는 동기 함수다. 이 의존성이 async라
    # FastAPI가 스레드풀로 빼주지 않으므로, 직접 호출하면 왕복 내내 이벤트 루프가 멈춘다
    # (Auth 지연 시 /health까지 함께 막힘). to_thread로 넘겨 루프를 놓아준다 —
    # 8.4가 run_search에 적용한 것과 같은 이유(FR50/NFR8 논블로킹).
    return await asyncio.to_thread(_validate_token, credentials.credentials)


def _is_transport_error(exc: Exception) -> bool:
    """예외가 '토큰 무효'가 아니라 'Auth 서버 도달 실패'인지 판별.

    supabase-py는 토큰 검증 실패 시 AuthApiError(상태코드 4xx)를 던지고,
    네트워크·DNS·연결 실패 시 httpx의 전송 예외(또는 5xx)를 던진다.
    여기서는 connection/timeout 계열과 5xx만 전송 오류로 본다(보수적: 모르면 401).
    """
    # 표준 라이브러리 연결/타임아웃 오류
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    # httpx 전송 예외(연결 실패·타임아웃 등) — 클래스명으로 느슨하게 판별(의존성 강결합 회피)
    name = type(exc).__name__
    if name in {"ConnectError", "ConnectTimeout", "ReadTimeout", "TransportError", "NetworkError"}:
        return True
    # supabase/httpx가 노출하는 상태코드가 5xx면 서버측 장애로 간주
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if isinstance(status, int) and status >= 500:
        return True
    return False
