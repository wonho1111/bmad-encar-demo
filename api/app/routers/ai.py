"""POST /ai/search — AI 검색 엔드포인트.

4.5: 라우터+그래프를 앞단에 꽂는다. 더는 모든 질의를 경로 A로 직행시키지 않고,
  run_search(그래프)가 질의를 라우터로 A/B/C 분류 → 경로 노드 → answer_node로 흘려
  공통 계약 {answer, listings[]}로 돌려준다.
  (4.3까지는 sql_rag_node를 직접 호출했다. 그 한 줄을 그래프 호출로 교체한 것이 4.5의 핵심.)

인증(get_current_user)·응답 계약({answer, listings[]})·에러 포맷은 4.1 확정값 그대로 유지한다.
경로 A가 그래프 안에서 던지는 SqlGuardError도 여기까지 전파돼 똑같이 400으로 잡힌다(회귀 0).
context 필드는 받되 무시한다(멀티턴은 4.6).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..db.sql_guard import SqlGuardError
from ..graph.graph import run_search
from ..schemas.ai import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, user=Depends(get_current_user)) -> SearchResponse:
    # get_current_user 의존성이 미인증 요청을 401로 막는다(AC3).
    try:
        result = run_search(req.query)  # 라우터→경로→answer 그래프. context는 4.6 전까지 무시
    except SqlGuardError as exc:
        # 가드 차단·재시도 실패 — 사용자에게 의미 있는 한국어 안내(400). 서버 500 누출 금지(AC3).
        logger.info("sql_guard 차단 — 400 반환: [%s] %s", exc.code, exc.message)
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": exc.code, "message": exc.message}},
        )
    # 그 외 오류(키 부재 RuntimeError·LLM/DB 장애)는 main.py 전역 핸들러가 공통 500 포맷으로 처리.
    return SearchResponse(answer=result["answer"], listings=result["listings"])
