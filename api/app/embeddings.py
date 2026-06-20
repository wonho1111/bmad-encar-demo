"""Gemini 768 임베딩 헬퍼.

⚠️ 핵심: gemini-embedding-001은 기본 3072차원이고, output_dimensionality=768로 줄이면
   자동 정규화가 되지 않는다(벡터 길이가 1이 아님). 그대로 쓰면 코사인 유사도 검색 품질이
   망가지므로, 임베딩을 받은 즉시 코드에서 L2 정규화(각 성분을 벡터 크기로 나눔)한다.
   (참고: 차세대 Gemini Embedding 2는 자동 정규화하지만, 본 프로젝트 단일출처는 gemini-embedding-001@768.)

저장(문서)은 task_type=RETRIEVAL_DOCUMENT, 검색(질의, 4.4에서 사용)은 RETRIEVAL_QUERY를 쓴다.
저장·검색 벡터 모두 L2 정규화하고, pgvector HNSW 인덱스는 vector_cosine_ops로 만든다.
"""

import math

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import require, settings


def _l2_normalize(vec: list[float]) -> list[float]:
    """L2 정규화: 벡터 길이를 1로 맞춰 코사인 유사도가 일관되게 동작하도록 한다."""
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


def _check_dim(vec: list[float]) -> list[float]:
    """차원·유한성 검증(fail-loud) — 768이 아니거나 비유한 값이 섞이면 즉시 실패한다.

    NaN/Inf 성분이 있으면 _vec_literal이 "[...,nan,...]"처럼 pgvector가 거부하는 리터럴을
    만들어 불투명한 DB 오류(invalid input syntax for type vector)로 번진다. 여기서 미리
    명확한 에러로 막아 잘못된 적재·검색을 차단한다(경로 A·B 공통 보호).
    """
    if len(vec) != settings.gemini_embedding_dim:
        raise RuntimeError(
            f"임베딩 차원 불일치: {len(vec)} != {settings.gemini_embedding_dim}. "
            f"GEMINI_EMBEDDING_MODEL/DIM 설정과 실제 모델 응답을 확인하세요."
        )
    if any(not math.isfinite(x) for x in vec):
        raise RuntimeError(
            "임베딩에 비유한 값(NaN/Inf)이 포함됐습니다. 모델 응답을 확인하세요."
        )
    return vec


def _client(task_type: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,  # gemini-embedding-001
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        task_type=task_type,  # RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY
        output_dimensionality=settings.gemini_embedding_dim,  # 768
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """적재용(문서) 임베딩 — 차원 검증 + L2 정규화한 768 벡터 리스트를 돌려준다."""
    vecs = _client("RETRIEVAL_DOCUMENT").embed_documents(texts)
    return [_l2_normalize(_check_dim(v)) for v in vecs]


def embed_query(text: str) -> list[float]:
    """질의용 임베딩 — 4.4(문서 RAG 검색)에서 사용. 여기서는 정의만 제공."""
    return _l2_normalize(_check_dim(_client("RETRIEVAL_QUERY").embed_query(text)))
