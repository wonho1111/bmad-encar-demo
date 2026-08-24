"""경로 B — 문서 기반 RAG 노드(FR15).

흐름: 의미형 질의 → embed_query(768) → pgvector 코사인 유사도(<=>) 검색 → ListingCard.
  · 질의 임베딩은 embed_query(task_type=RETRIEVAL_QUERY, 4.2 재사용). embed_documents 아님(함정 #3).
  · 경로 B는 LLM이 SQL을 만들지 않는다 — 코드가 직접 고정 SQL을 쓰고 벡터/LIMIT만 %s 파라미터로
    바인딩하므로 인젝션 위험이 없어 sql_guard를 거치지 않는다. 그 대신 FR11(on_sale)·LIMIT·테이블
    한정이 전부 코드 책임이다(함정 #1·#4). 그래서 매물 검색 SQL에 status='on_sale'을 직접 넣는다.
  · 실행은 항상 ai_readonly 롤(run_select, 4.1 재사용) — 가드가 없어도 쓰기는 DB가 거부(이중 방어).

매물 설명·옵션 임베딩(listings.embedding)과 가이드 문서 임베딩(guide_documents.embedding)을 둘 다
유사도 검색해, 의미가 가까운 on_sale 매물을 추천하고 가이드 문서를 "왜 어울리는지" 근거로 곁들인다.
단, 가이드 인용은 무조건이 아니다 — 코사인 거리가 `_GUIDE_DISTANCE_CUTOFF`(FR49) 이내일 때만
붙인다(Story 13.6). `find_relevant_guide()`가 이 게이트를 지키는 공유 헬퍼이며, `hybrid_rag_node`도
질의확장(FR44)에 같은 헬퍼를 재사용한다.

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

# 가이드 인용/질의확장에 쓸 최상위 가이드 거리 상한(FR49) — 초기 후보값. Phase B 실측
# (run_phase_b.py + score_ab.py doc_hit recall)으로 확정한다(spec-13-6 Block-If).
_GUIDE_DISTANCE_CUTOFF = 0.3


def _vec_literal(vec: list[float]) -> str:
    """list[float] → pgvector 텍스트 리터럴 "[v1,v2,...]".

    이 문자열을 %s 파라미터로 바인딩하고 SQL에서 ::vector로 캐스팅한다. run_select는 연결마다
    register_vector를 호출하지 않으므로(리스트 직접 바인딩 불가) 이 텍스트 캐스팅 방식이 가장 단순·안전.
    (사용자값/벡터를 f-string으로 SQL에 직접 박지 않는다 — 항상 파라미터 바인딩.)
    """
    return "[" + ",".join(map(str, vec)) + "]"


def find_relevant_guide(qvec_literal: str) -> tuple[str, str] | None:
    """질의 벡터와 가장 가까운 가이드 문서 1건을 (title, content)로 반환한다(FR49 게이트).

    코사인 거리가 `_GUIDE_DISTANCE_CUTOFF` 이내일 때만 반환한다 — 가이드가 0건이거나
    거리가 컷오프를 초과하면 None. hybrid_rag_node의 질의확장(FR44)과 doc_rag_node의
    인용이 이 하나의 헬퍼·하나의 임계값을 공유한다(드리프트 방지).

    제목·본문이 공백뿐인 행도 None으로 거른다(후속 코드리뷰) — 호출부마다 따로 막으면
    한쪽만 막힌다. 실제로 이전 패스는 **인용 자리에만** `guide[0]` 검사를 넣어, 빈 제목
    가이드가 hybrid의 조건추출 프롬프트에는 그대로 주입되고(매핑 없는 "규칙 2보다 우선"
    지시만 남는다) 공백 제목은 "(참고:    )"라는 빈 인용까지 통과시켰다. 게이트를 이
    한 곳으로 모아 두 구멍을 함께 닫는다.
    """
    rows = run_select(
        "SELECT title, content, embedding <=> %s::vector AS distance FROM guide_documents "
        "WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT 1",
        (qvec_literal, qvec_literal),
    )
    if not rows:
        # 0건도 반드시 남긴다 — 안 남기면 스펙의 수동 확인("실제 거리를 로그로 관찰")을 따를 때
        # "코퍼스가 비었다/임베딩이 안 됐다"와 "로그가 없다"를 구분할 수 없다(후속 코드리뷰).
        logger.info("find_relevant_guide 후보 0건 — 인용·질의확장 생략")
        return None
    title, content, distance = rows[0]
    # 스펙 Verification의 수동 확인 지시("실제 코사인 거리를 로그로 관찰해 0.3이 그 케이스를
    # 걸러내는지 확인")를 실행 가능하게 한다 — 컷오프 통과/차단 모두 매 호출마다 남긴다(코드리뷰).
    within_cutoff = distance <= _GUIDE_DISTANCE_CUTOFF
    logger.info(
        "find_relevant_guide 거리=%.4f 제목=%r 컷오프통과=%s",
        distance, title, within_cutoff,
    )
    # 게이트는 반드시 "통과 조건"으로 쓴다(`not (d <= cutoff)`) — `d > cutoff`로 쓰면 NaN이
    # 통과한다. NaN과의 모든 비교는 False이므로 `>` 검사는 빠져나가고, 같은 값을 쓰는 위
    # 로그는 `컷오프통과=False`라고 남기는데 함수는 그 가이드를 그대로 반환했다(3회차 코드리뷰
    # 실측). 즉 유일한 계측 수단이 실제 동작과 반대를 말하는 상태였다. 도달 경로: 질의 임베딩이
    # 영벡터면(embeddings.py의 _l2_normalize가 norm==0을 그대로 통과시킨다) pgvector `<=>`가
    # NaN을 내고, 그때 모든 행이 NaN이라 LIMIT 1은 임의의 가이드를 집는다.
    if not within_cutoff:
        return None
    if not title.strip() or not content.strip():
        # title/content는 NOT NULL이지만 빈 문자열·공백은 스키마가 막지 않는다.
        logger.info("find_relevant_guide 제목/본문이 비어 있어 생략 제목=%r", title)
        return None
    return (title, content)


def doc_rag_node(query: str, qvec: list[float] | None = None) -> dict:
    """의미형 질의를 받아 {"answer": str, "listings": list[ListingCard]}를 반환한다.

    GEMINI_API_KEY/DATABASE_URL 부재 시 embed_query/run_select 내부 require()가 명확한 한국어
    에러로 즉시 실패한다(조용한 빈 결과 금지). 0건은 실패가 아니라 FR17 안내로 처리한다.

    qvec(선택) — 호출자가 이미 embed_query로 계산한 임베딩이 있으면 그대로 재사용한다
    (코드리뷰: hybrid_rag_node의 NONE/공백 폴백이 재임베딩 없이 이 노드를 호출할 수 있게
    한다). 생략하면 기존과 동일하게 이 함수가 직접 embed_query(query)를 계산한다 —
    graph.py의 _clarify_step 등 기존 호출자는 인자를 그대로 두면 회귀 없이 동작한다.
    """
    qvec = _vec_literal(qvec if qvec is not None else embed_query(query))  # 키 부재 시 여기서 fail-loud

    # ── 매물 의미검색 — on_sale·임베딩 보유 행만, 코사인 거리 오름차순(=유사도 내림차순) ──
    # FR11(sold 비노출)은 ai_readonly RLS가 못 거르므로 이 WHERE가 직접 책임진다 — RLS는
    # Story 17.4(0035/0036)로 판매자가 활성인지만 걸러졌고(using(private.is_seller_active(
    # seller_id))), status='on_sale' 필터는 여전히 이 쿼리 밖에서 강제되지 않는다.
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

    # ── 근거 가이드 문서 — 컷오프(FR49) 이내일 때만 answer 근거로 곁들인다 ──
    guide = find_relevant_guide(qvec)

    logger.info(
        "doc_rag_node 질의=%r 매물 %d건, 근거 가이드=%r",
        query, len(listings), guide[0] if guide else None,
    )

    if not listings:
        return {"answer": _ANSWER_EMPTY, "listings": []}  # FR17

    answer = _ANSWER_FOUND.format(query=query, n=len(listings))
    # `guide[0]` 검사는 이제 도달 불가하다 — find_relevant_guide가 공백 제목을 이미 None으로
    # 거르므로 non-None 가이드의 title은 항상 비어 있지 않다(3회차 코드리뷰). 두 겹 방어처럼
    # 보이지만 실제 게이트는 헬퍼 한 곳뿐이니, 헬퍼의 strip 검사를 지우면 여기도 못 막는다.
    if guide and guide[0]:
        answer += f" (참고: {guide[0]})"
    return {"answer": answer, "listings": listings}
