"""POST /ai/search — AI 검색 엔드포인트.

4.3: stub을 벗고 경로 A(Text-to-SQL)에 실연결한다. 모든 질의를 sql_rag_node로 처리한다.
  (라우터 의도 분류 A/B/C는 4.5에서 이 앞단에 삽입된다.)

인증(get_current_user)·응답 계약({answer, listings[]})은 4.1 확정값 그대로 유지한다.
context 필드는 받되 무시한다(멀티턴은 4.6).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..db.sql_guard import SqlGuardError
from ..graph.sql_rag_node import sql_rag_node
from ..schemas.ai import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, user=Depends(get_current_user)) -> SearchResponse:
    # get_current_user 의존성이 미인증 요청을 401로 막는다(AC3).
    try:
        result = sql_rag_node(req.query)  # context는 4.6 전까지 무시
    except SqlGuardError as exc:
        # 가드 차단·재시도 실패 — 사용자에게 의미 있는 한국어 안내(400). 서버 500 누출 금지(AC3).
        logger.info("sql_guard 차단 — 400 반환: [%s] %s", exc.code, exc.message)
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": exc.code, "message": exc.message}},
        )
    # 그 외 오류(키 부재 RuntimeError·LLM/DB 장애)는 main.py 전역 핸들러가 공통 500 포맷으로 처리.
    return SearchResponse(answer=result["answer"], listings=result["listings"])
