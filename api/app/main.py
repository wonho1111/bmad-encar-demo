"""FastAPI 앱 진입점 — 라우터 등록 + CORS + 공통 에러 포맷 + /health.

자동 OpenAPI 문서: /docs (Swagger UI), /openapi.json (AC1).
모든 에러 응답은 공통 포맷 {error:{code,message}}로 통일(architecture.md).
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .routers import ai

app = FastAPI(
    title="encar-demo AI Search API",
    version="0.1.0",
    description="중고차 직거래 데모 — AI 자연어 검색 전용 백엔드(FastAPI + LangGraph). "
    "클라이언트는 Supabase에 직접 접근하고, 이 API는 AI 검색에만 쓰인다(읽기전용).",
)

# CORS — 개발 웹(localhost:3000)에서 브라우저 호출 허용.
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
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
