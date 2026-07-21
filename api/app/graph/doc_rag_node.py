"""경로 B — 문서 기반 RAG 노드(FR15).

흐름: 의미형 질의 → embed_query(768) → pgvector 코사인 유사도(<=>) 검색 → ListingCard.
  · 질의 임베딩은 embed_query(task_type=RETRIEVAL_QUERY, 4.2 재사용). embed_documents 아님(함정 #3).
  · 경로 B는 LLM이 SQL을 만들지 않는다 — 코드가 직접 고정 SQL을 쓰고 벡터/LIMIT만 %s 파라미터로
    바인딩하므로 인젝션 위험이 없어 sql_guard를 거치지 않는다. 그 대신 FR11(on_sale)·LIMIT·테이블
    한정이 전부 코드 책임이다(함정 #1·#4). 그래서 매물 검색 SQL에 status='on_sale'을 직접 넣는다.
  · 실행은 항상 ai_readonly 롤(run_select, 4.1 재사용) — 가드가 없어도 쓰기는 DB가 거부(이중 방어).

매물 설명·옵션 임베딩(listings.embedding)과 가이드 문서 임베딩(guide_documents.embedding)을 둘 다
유사도 검색해, 의미가 가까운 on_sale 매물을 추천하고 가이드 문서를 "왜 어울리는지" 근거로 곁들인다.

4.4는 이 함수를 "호출 가능한 노드"로만 만든다. /ai/search 라우팅(경로 A/B)·StateGraph 조립은 4.5.
[Source: story 4.4 doc_rag_node 설계; research §5.1·§5.5; 4-2 embeddings.py]
"""

import logging

from app.db.readonly import run_select
from app.db.sql_guard import DEFAULT_LIMIT  # 추천 기본 개수(5) — 경로 A와 동일(brief "약 5개")
from app.embeddings import embed_query
from app.graph.listing_cards import SELECT_COLUMNS, attach_cover_images, rows_to_cards
from app.schemas.ai import ListingCard

logger = logging.getLogger(__name__)

_ANSWER_FOUND = "'{query}'에 어울리는 매물 {n}건을 찾았어요."
# FR17 — 0건일 때 빈 목록만 던지지 않고 조건 완화/재질문을 유도한다.
_ANSWER_EMPTY = "조건에 맞는 매물이 없어요. 원하시는 용도나 예산을 알려주시면 더 잘 찾아드릴게요."


def _vec_literal(vec: list[float]) -> str:
    """list[float] → pgvector 텍스트 리터럴 "[v1,v2,...]".

    이 문자열을 %s 파라미터로 바인딩하고 SQL에서 ::vector로 캐스팅한다. run_select는 연결마다
    register_vector를 호출하지 않으므로(리스트 직접 바인딩 불가) 이 텍스트 캐스팅 방식이 가장 단순·안전.
    (사용자값/벡터를 f-string으로 SQL에 직접 박지 않는다 — 항상 파라미터 바인딩.)
    """
    return "[" + ",".join(map(str, vec)) + "]"


def doc_rag_node(query: str) -> dict:
    """의미형 질의를 받아 {"answer": str, "listings": list[ListingCard]}를 반환한다.

    GEMINI_API_KEY/DATABASE_URL 부재 시 embed_query/run_select 내부 require()가 명확한 한국어
    에러로 즉시 실패한다(조용한 빈 결과 금지). 0건은 실패가 아니라 FR17 안내로 처리한다.
    """
    qvec = _vec_literal(embed_query(query))  # 키 부재 시 여기서 fail-loud

    # ── 매물 의미검색 — on_sale·임베딩 보유 행만, 코사인 거리 오름차순(=유사도 내림차순) ──
    # FR11(sold 비노출)은 ai_readonly RLS가 못 거르므로(using(true)) 이 WHERE가 직접 책임진다.
    # 참고(연구 §5.5): pgvector는 사전 필터링을 안 해서 필터+벡터 조합 시 결과가 LIMIT보다 적게
    #   나올 수 있다. 본 데모는 on_sale 42/44로 필터가 느슨해 실질 위험이 작아 그대로 둔다
    #   (대규모라면 SET hnsw.iterative_scan='relaxed_order' 또는 후보 과다조회로 완화).
    listing_rows = run_select(
        f"SELECT {SELECT_COLUMNS} FROM listings "
        "WHERE status = 'on_sale' AND embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector LIMIT %s",
        (qvec, DEFAULT_LIMIT),
    )
    # 사진 부착은 경로 A·B 공용 헬퍼가 한다(Story 9.6) — 여기에 쿼리를 복사하지 않는다.
    listings: list[ListingCard] = attach_cover_images(rows_to_cards(listing_rows))

    # ── 근거 가이드 문서 — 의미가 가장 가까운 1건의 제목을 answer 근거로 곁들인다 ──
    guide_rows = run_select(
        "SELECT title FROM guide_documents WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector LIMIT 1",
        (qvec,),
    )
    guide_title = guide_rows[0][0] if guide_rows else None

    logger.info(
        "doc_rag_node 질의=%r 매물 %d건, 근거 가이드=%r", query, len(listings), guide_title
    )

    if not listings:
        return {"answer": _ANSWER_EMPTY, "listings": []}  # FR17

    answer = _ANSWER_FOUND.format(query=query, n=len(listings))
    if guide_title:
        answer += f" (참고: {guide_title})"
    return {"answer": answer, "listings": listings}
