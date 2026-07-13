"""POST /ai/search — AI 검색 엔드포인트.

4.5: 라우터+그래프를 앞단에 꽂는다. 더는 모든 질의를 경로 A로 직행시키지 않고,
  run_search(그래프)가 질의를 라우터로 A/B/C 분류 → 경로 노드 → answer_node로 흘려
  공통 계약 {answer, listings[]}로 돌려준다.
  (4.3까지는 sql_rag_node를 직접 호출했다. 그 한 줄을 그래프 호출로 교체한 것이 4.5의 핵심.)

인증(get_current_user)·응답 계약({answer, listings[]})·에러 포맷은 4.1 확정값 그대로 유지한다.
경로 A가 그래프 안에서 던지는 SqlGuardError도 여기까지 전파돼 똑같이 400으로 잡힌다(회귀 0).
4.6: context(직전 대화 맥락)를 run_search에 전달해 멀티턴을 지원한다(FR18). 맥락은 요청 본문에서만
  오고 서버·DB에 저장하지 않는다(무상태). 맥락이 없으면 단일턴으로 4.5까지와 동일하게 동작한다.
8.4(AC-DB-1): run_search(LLM 호출+DB 조회 모두 동기 블로킹)를 asyncio.to_thread로 스레드풀에
  넘겨 이벤트 루프를 놓아준다(FR50/NFR8 논블로킹). run_search 자체는 동기 그대로 — DB 커넥션
  풀(readonly.py)도 동기라 스레드에서 안전하게 동작한다.
8.4 코드리뷰 패치: 동시 요청이 DB 풀(max_size=8)보다 많으면 커넥션 대여가 타임아웃될 수
  있다(PoolTimeout). 기존 catch-all(500)로 흘려보내는 대신 503으로 즉시 안내한다.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from psycopg_pool import PoolTimeout

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
        # 동기 파이프라인 전체(LLM+DB)를 스레드풀로 넘겨 이벤트 루프를 막지 않는다(AC-DB-1 FR50).
        result = await asyncio.to_thread(run_search, req.query, req.context)
    except SqlGuardError as exc:
        # 가드 차단·재시도 실패 — 사용자에게 의미 있는 한국어 안내(400). 서버 500 누출 금지(AC3).
        logger.info("sql_guard 차단 — 400 반환: [%s] %s", exc.code, exc.message)
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": exc.code, "message": exc.message}},
        )
    except PoolTimeout:
        # DB 커넥션 풀이 꽉 차 대여를 기다리다 타임아웃(8.4 코드리뷰 패치) — 30초 블로킹 대신
        # 즉시 503으로 "잠시 후 재시도" 안내(AC-DB-1 "부하 상황에서도 안정적으로").
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
