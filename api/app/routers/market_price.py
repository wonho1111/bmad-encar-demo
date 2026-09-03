"""GET /api/market-price/{listing_id} — 시세 진단 엔드포인트(3단계, HANDOFF.md §2).

인증(get_current_user)·읽기전용 DB 관례(db/readonly.py의 readonly_connection)는 ai.py를
  그대로 따른다 — 로그인 필수인 이유도 동일 원칙(FR58): 매물 열람은 anon에 열려 있지만
  이 엔드포인트는 조회당 TabPFN 추론까지 도는 "행동"이라 로그인을 요구한다.
응답은 market_price.diagnose()가 만든 dict를 그대로 돌려준다(설계 확정 — 그 dict 자체가
  응답 스키마). 별도 Pydantic 응답 모델을 새로 만들지 않는다(불필요한 추상화 금지, A2).
DB 작업은 동기 블로킹이라 asyncio.to_thread로 스레드풀에 넘긴다 — ai.py의 run_search와
  동일 패턴(AC-DB-1, FR50 논블로킹).
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from psycopg_pool import PoolTimeout

from ..auth import get_current_user
from ..db.readonly import readonly_connection
from ..market_price import diagnose

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market-price", tags=["market-price"])


def _diagnose_sync(listing_id: str) -> dict | None:
    with readonly_connection() as conn:
        return diagnose(listing_id, conn)


@router.get("/{listing_id}")
async def get_market_price(listing_id: str, user=Depends(get_current_user)) -> dict:
    try:
        result = await asyncio.to_thread(_diagnose_sync, listing_id)
    except PoolTimeout:
        # ai.py와 동일 패턴(8.4 코드리뷰 패치) — DB 커넥션 풀 고갈을 30초 블로킹 대신 즉시 503으로.
        logger.warning("DB 커넥션 풀 고갈 — 503 반환")
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "pool_exhausted",
                    "message": "지금 사용자가 많아 요청을 처리할 수 없습니다. 잠시 후 다시 시도해주세요.",
                }
            },
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "매물을 찾을 수 없습니다."}},
        )

    return result
