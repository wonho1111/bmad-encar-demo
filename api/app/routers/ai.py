"""POST /ai/search — AI 검색 엔드포인트.

4.1은 스캐폴딩 stub: 인증을 강제하고 공통 응답 계약 형태만 돌려준다.
실제 라우터 분류·Text-to-SQL·문서 RAG·답변 조립은 4.3~4.5에서 연결된다.
"""

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..schemas.ai import SearchResponse, SearchRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, user=Depends(get_current_user)) -> SearchResponse:
    # get_current_user 의존성이 미인증 요청을 401로 막는다(AC3).
    # 4.1 stub — DB·LLM을 건드리지 않고 계약 형태만 반환(라이브 검증은 후속 스토리에서).
    return SearchResponse(
        answer="AI 검색 백엔드 토대가 준비되었습니다. 실제 검색은 다음 스토리(4.3~4.5)에서 연결됩니다.",
        listings=[],
    )
