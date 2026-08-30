"""리랭커(크로스인코더) 사이드카 — 독립 FastAPI 앱. api 본 서버가 아니라 별도 프로세스로 뜬다.

왜 별도 프로세스인가(4단계 부품 A): BAAI/bge-reranker-v2-m3는 로드에 11.5초, GPU 추론은
  10건 1.1초로 걸린다(bench_reranker.py 실측, api/scripts/bench/results_reranker_desktop.json).
  요청마다 모델을 새로 로드하면 응답마다 11초가 붙으므로, 모델을 한 번만 올려 둔 상주
  프로세스가 필요하다 — 이게 이 파일이다.

왜 api 본 서버(uvicorn app.main:app)에 얹지 않는가: sentence-transformers(torch 의존)를
  api venv에 설치하면 시세 진단 엔진(tabpfn, market 그룹)과 huggingface-hub 버전이
  충돌한다(실측 — pyproject.toml market 그룹 주석 참조). 그래서 이 서비스는 완전히 별도
  venv(/home/whlee/bench/venv-rr)로 돌리고, api는 HTTP로만 부른다(app/rerank_client.py).
  이 파일 자체는 api/app 패키지를 import하지 않는다(독립 실행 — 별도 venv에 api 의존성이
  없어도 동작해야 한다).

기동: scripts/dev-reranker.sh (venv-rr 파이썬으로 실행). 포트: RERANKER_PORT(기본 8801).
디바이스: RERANKER_DEVICE(기본 "cuda", 로드 실패 시 CPU로 자동 폴백 + 로그).
"""

import contextlib
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("reranker_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

MAX_DOCS = 50
MAX_TEXT_CHARS = 2000  # 모델 입력 보호 — 크로스인코더는 (질의, 문서) 쌍을 통째로 토크나이즈한다.

_state: dict = {"model": None, "device": None}


def _load_model() -> None:
    """앱 시작 시 1회 호출. RERANKER_DEVICE로 로드 시도, 실패하면 CPU로 폴백(로그 남김)."""
    from sentence_transformers import CrossEncoder

    requested_device = os.environ.get("RERANKER_DEVICE", "cuda")
    model_name = "BAAI/bge-reranker-v2-m3"

    try:
        model = CrossEncoder(model_name, device=requested_device)
        device = requested_device
    except Exception as exc:
        logger.warning(
            "리랭커 모델을 device=%r로 로드 실패 — cpu로 폴백: %r", requested_device, exc
        )
        model = CrossEncoder(model_name, device="cpu")
        device = "cpu"

    _state["model"] = model
    _state["device"] = device
    logger.info("리랭커 모델 로드 완료 — model=%s device=%s", model_name, device)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield


app = FastAPI(title="reranker-sidecar", version="0.1.0", lifespan=lifespan)


class RerankDoc(BaseModel):
    id: str
    text: str


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1)
    docs: list[RerankDoc]


class RerankScore(BaseModel):
    id: str
    score: float


class RerankResponse(BaseModel):
    scores: list[RerankScore]


@app.get("/health")
def health() -> dict:
    model = _state["model"]
    return {
        "status": "ok" if model is not None else "loading",
        "model": "BAAI/bge-reranker-v2-m3",
        "device": _state["device"],
    }


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest) -> RerankResponse:
    if len(req.docs) > MAX_DOCS:
        raise HTTPException(
            status_code=422,
            detail=f"docs는 최대 {MAX_DOCS}건까지 허용됩니다(요청 {len(req.docs)}건).",
        )

    model = _state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    pairs = [[req.query, doc.text[:MAX_TEXT_CHARS]] for doc in req.docs]
    raw_scores = model.predict(pairs)

    scored = [
        RerankScore(id=doc.id, score=float(score))
        for doc, score in zip(req.docs, raw_scores)
    ]
    scored.sort(key=lambda s: s.score, reverse=True)
    return RerankResponse(scores=scored)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("RERANKER_PORT", "8801"))
    uvicorn.run(app, host="127.0.0.1", port=port)
