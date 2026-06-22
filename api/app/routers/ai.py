"""POST /ai/search — AI 검색 엔드포인트.

4.5: 라우터+그래프를 앞단에 꽂는다. 더는 모든 질의를 경로 A로 직행시키지 않고,
  run_search(그래프)가 질의를 라우터로 A/B/C 분류 → 경로 노드 → answer_node로 흘려
  공통 계약 {answer, listings[]}로 돌려준다.
  (4.3까지는 sql_rag_node를 직접 호출했다. 그 한 줄을 그래프 호출로 교체한 것이 4.5의 핵심.)

인증(get_current_user)·응답 계약({answer, listings[]})·에러 포맷은 4.1 확정값 그대로 유지한다.
경로 A가 그래프 안에서 던지는 SqlGuardError도 여기까지 전파돼 똑같이 400으로 잡힌다(회귀 0).
4.6: context(직전 대화 맥락)를 run_search에 전달해 멀티턴을 지원한다(FR18). 맥락은 요청 본문에서만
  오고 서버·DB에 저장하지 않는다(무상태). 맥락이 없으면 단일턴으로 4.5까지와 동일하게 동작한다.
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
        # 맥락화→라우터→경로→answer 그래프. context가 있으면 후속 질의를 독립 질의로 재작성해 반영(FR18).
        result = run_search(req.query, req.context)
    except SqlGuardError as exc:
        # 가드 차단·재시도 실패 — 사용자에게 의미 있는 한국어 안내(400). 서버 500 누출 금지(AC3).
        logger.info("sql_guard 차단 — 400 반환: [%s] %s", exc.code, exc.message)
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": exc.code, "message": exc.message}},
        )
    except Exception as exc:
        # 그 외 오류(키 부재 RuntimeError·LLM/DB 장애 등)를 여기서 HTTPException(500)으로 바꿔 던진다.
        #   왜: 라우트 밖(main.py 전역 Exception 핸들러)에서 잡으면 그 500 응답이 CORSMiddleware
        #   바깥에서 만들어져 Access-Control-Allow-Origin 헤더가 빠진다 → 브라우저가 실제 500을
        #   "CORS 차단/연결 실패"로 오인(원인 은폐). HTTPException은 CORS 안쪽에서 처리되므로
        #   헤더가 정상적으로 붙어, 프런트가 진짜 서버 오류 메시지를 받게 된다.
        logger.exception("run_search 처리 중 오류 — 500 반환: %r", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "internal_error", "message": "서버 내부 오류가 발생했습니다."}},
        )
    return SearchResponse(answer=result["answer"], listings=result["listings"])
