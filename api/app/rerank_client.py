"""리랭커 사이드카(reranker_service.py) 클라이언트 — api 쪽에서 부르는 얇은 HTTP 래퍼.

설계: 사이드카는 별도 프로세스·별도 venv로 뜬다(reranker_service.py 상단 설명 참조). 이
  클라이언트는 그게 없거나 느리거나 죽어 있어도 **호출부를 절대 깨뜨리지 않는다** — 데모
  환경에 GPU 사이드카가 없을 수 있고, 있어도 일시 장애가 날 수 있다. 그래서 실패 경로는
  전부 예외를 삼키고 None을 돌려주며, 호출부는 None이면 기존 정렬 순서를 그대로 쓰면 된다
  (리랭킹은 "있으면 개선, 없으면 원래대로"인 선택 기능).
설계: id 대신 인덱스로 돌려주는 이유 — 호출부(hybrid_rag_node 등)가 이미 갖고 있는 원본
  리스트를 그대로 재정렬하면 되므로, id 문자열을 다시 원본 인덱스로 매핑하는 별도 단계가
  필요 없다(A2: 최소한의 인터페이스).
"""

import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 3.0


def rerank(query: str, docs: list[tuple[str, str]]) -> list[int] | None:
    """(id, text) 쌍 목록을 사이드카에 보내 점수 내림차순 **인덱스** 리스트를 돌려준다.

    RERANKER_URL 미설정, 연결 실패, 타임아웃(3초), 비정상 응답이면 None — 예외를 밖으로
    던지지 않는다(호출부는 None이면 원래 순서를 유지하면 된다).
    """
    if not settings.reranker_url:
        return None

    id_to_index = {doc_id: i for i, (doc_id, _) in enumerate(docs)}
    payload = {
        "query": query,
        "docs": [{"id": doc_id, "text": text} for doc_id, text in docs],
    }

    try:
        resp = httpx.post(
            f"{settings.reranker_url.rstrip('/')}/rerank",
            json=payload,
            timeout=_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        scores = resp.json()["scores"]
        return [id_to_index[s["id"]] for s in scores]
    except Exception as exc:
        logger.warning("리랭커 사이드카 호출 실패 — 원래 순서 유지: %r", exc)
        return None
