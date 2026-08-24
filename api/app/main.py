"""FastAPI 앱 진입점 — 라우터 등록 + CORS + 공통 에러 포맷 + /health.

자동 OpenAPI 문서: /docs (Swagger UI), /openapi.json (AC1).
모든 에러 응답은 공통 포맷 {error:{code,message}}로 통일(architecture.md).
"""

import contextlib
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .db.readonly import close_pool
from .routers import ai

# ── 로깅 설정 (DW-659) ──────────────────────────────────────────────
# logging.basicConfig가 어디에도 없어 루트 로거가 파이썬 기본값 WARNING(30)에 머물러
# 그래프 노드들의 logger.info(라우팅 결정·생성 SQL·재작성 질의·결과 건수, app/graph/*.py)가
# 전부 소리 없이 버려졌다. 레벨은 LOG_LEVEL 환경변수로 조절(기본 INFO) — 운영에서 DEBUG를
# 끌 수 있어야 한다. 표준출력 + 저장소 루트 .logs/api.log(회전) 두 곳에 남긴다.
#   uvicorn은 자체 dictConfig로 "uvicorn"/"uvicorn.access" 로거만 건드리고 propagate=False로
#   격리해 두므로(실측 확인) 루트 로거를 여기서 따로 설정해도 uvicorn과 충돌·중복 출력이 없다.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _REPO_ROOT / ".logs"
_LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = _LOG_DIR / "api.log"

_log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_log_formatter)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_log_formatter)

logging.getLogger().setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logging.getLogger().addHandler(_stream_handler)
logging.getLogger().addHandler(_file_handler)

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 수명주기 훅 — 기동 시엔 아무것도 하지 않고, 종료 시 DB 커넥션 풀을 닫는다.

    기동 시 풀을 열지 않는 이유: 비밀값 없이도 /health가 떠야 한다(config.py 설계).
    풀은 최초 run_select 때 지연 생성된다(readonly.py).
    종료 시 닫는 이유: 풀은 모듈 싱글턴이라 아무도 닫지 않으면 SIGTERM(Cloud Run
    스케일다운·매 재배포)마다 서버측 세션이 정리되지 않은 채 남는다(코드리뷰 패치).
    """
    yield
    close_pool()


app = FastAPI(
    title="encar-demo AI Search API",
    version="0.1.0",
    description="중고차 직거래 데모 — AI 자연어 검색 전용 백엔드(FastAPI + LangGraph). "
    "클라이언트는 Supabase에 직접 접근하고, 이 API는 AI 검색에만 쓰인다(읽기전용).",
    lifespan=lifespan,
)

# CORS — 웹에서 브라우저 호출 허용.
#   · cors_origins: 정확히 일치해야 하는 오리진 목록(운영 도메인·localhost).
#   · cors_origin_regex: preview처럼 매번 바뀌는 오리진을 패턴으로 허용(개발 환경에서 사용).
#     설정 시 정확 목록과 OR로 동작한다(둘 중 하나만 맞아도 허용).
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """기동 확인용 헬스 체크."""
    return {"status": "ok"}


app.include_router(ai.router)


# ── 공통 에러 포맷 ─────────────────────────────────────────────────
# HTTPException.detail이 {"error":{...}} 형태면 그대로, 아니면 표준 포맷으로 감싼다.
@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(detail)}},
    )


# 요청 검증 실패(422)도 같은 포맷으로.
@app.exception_handler(RequestValidationError)
async def on_validation_error(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "요청 형식이 올바르지 않습니다."}},
    )


# 그 외 모든 미처리 예외(예: config.require()의 RuntimeError, psycopg 연결 오류)도
# 공통 포맷 500으로 감싼다. 내부 메시지는 로그로만 남기고 사용자에겐 일반 문구만 노출
# (스택트레이스·원인 누출 방지).
@app.exception_handler(Exception)
async def on_unhandled_exception(request, exc: Exception):
    logger.exception("미처리 예외 — 500 반환: %r", exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "서버 내부 오류가 발생했습니다."}},
    )
