"""경로 B — 문서 기반 RAG 노드(FR15).

흐름: 의미형 질의 → embed_query(768) → pgvector 코사인 유사도(<=>) 검색 → ListingCard.
  · 질의 임베딩은 embed_query(task_type=RETRIEVAL_QUERY, 4.2 재사용). embed_documents 아님(함정 #3).
  · 경로 B는 LLM이 SQL을 만들지 않는다 — 코드가 직접 고정 SQL을 쓰고 벡터/LIMIT만 %s 파라미터로
    바인딩하므로 인젝션 위험이 없어 sql_guard를 거치지 않는다. 그 대신 FR11(on_sale)·LIMIT·테이블
    한정이 전부 코드 책임이다(함정 #1·#4). 그래서 매물 검색 SQL에 status='on_sale'을 직접 넣는다.
  · 실행은 항상 ai_readonly 롤(run_select, 4.1 재사용) — 가드가 없어도 쓰기는 DB가 거부(이중 방어).

매물 설명·옵션 임베딩(listings.embedding)과 가이드 문서 임베딩(guide_documents.embedding)을 둘 다
유사도 검색해, 의미가 가까운 on_sale 매물을 추천하고 가이드 문서를 "왜 어울리는지" 근거로 곁들인다.
단, 가이드 인용은 무조건이 아니다 — top-1 절대 컷오프 대신 top-k 상대 게이트(FR49)를 쓴다:
상위 `_GUIDE_TOP_K`건을 후보로 뽑고, 그중 1등 거리 대비 `_GUIDE_MARGIN` 이내면서 절대 상한
`_GUIDE_DISTANCE_CEILING` 이내인 것만 통과시킨다(Story 13.6, DW 후속). 복합 질의는 1등도
거리가 0.30~0.35까지 밀려 절대 컷오프 0.3에서 전멸하거나, 2등이 1등과 0.005 차이인데도
버려지던 문제(실측)를 상대 마진으로 고친다. `find_relevant_guide()`가 이 게이트를 지키는
공유 헬퍼이며, `hybrid_rag_node`도 질의확장(FR44)에 같은 헬퍼를 재사용한다.

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

# top-k 상대 게이트(FR49, DW 후속 — top-1 절대 컷오프에서 전환) — 세 상수가 함께 동작한다.
# 후보 개수 자체를 늘린다 — 1건만 보면 2등 이하가 통과 여부와 무관하게 애초에 안 보인다.
_GUIDE_TOP_K = 5
# 실질 선별은 이 상대 마진이 한다 — 1등 거리 대비 이 폭 안의 후보만 통과. 복합 질의에서
# 1~2등이 근소한 차이(실측 0.005)인데 한쪽만 버려지던 문제를 막는다.
_GUIDE_MARGIN = 0.05  # 2026-08-29 30질의 스윕 실측으로 확정 — 날카로운 질의는 정답 섹션만, 복합 질의는 3~5개 통과
# 옛 `_GUIDE_DISTANCE_CUTOFF`(=0.3, 절대 컷오프)를 대체 — 이름을 CUTOFF에서 CEILING으로
# 바꾼 이유: 이제 이 값은 "선별"을 하지 않는다. 선별은 위 마진이 하고, 이 상한은 그저
# "명백히 무관한 것"만 거르는 최후 안전판이라 0.3보다 넉넉히 잡는다(실측 복합 질의 1등이
# 0.30~0.35까지 밀림 — 옛 컷오프였다면 전멸했을 값).
_GUIDE_DISTANCE_CEILING = 0.45  # 같은 스윕 top1 최대 0.322 — 안전판으로 충분함을 실측 확인


def _vec_literal(vec: list[float]) -> str:
    """list[float] → pgvector 텍스트 리터럴 "[v1,v2,...]".

    이 문자열을 %s 파라미터로 바인딩하고 SQL에서 ::vector로 캐스팅한다. run_select는 연결마다
    register_vector를 호출하지 않으므로(리스트 직접 바인딩 불가) 이 텍스트 캐스팅 방식이 가장 단순·안전.
    (사용자값/벡터를 f-string으로 SQL에 직접 박지 않는다 — 항상 파라미터 바인딩.)
    """
    return "[" + ",".join(map(str, vec)) + "]"


def find_relevant_guide(qvec_literal: str) -> list[tuple[str, str]]:
    """질의 벡터와 가까운 가이드 문서를 top-k 상대 게이트로 걸러 [(title, content), ...]로
    반환한다(FR49 게이트). 순서는 거리 오름차순(가장 가까운 것부터)을 유지한다.

    상위 `_GUIDE_TOP_K`건을 후보로 뽑고, 각 후보가 (a) 1등 거리 대비 `_GUIDE_MARGIN` 이내
    이고 (b) 절대 상한 `_GUIDE_DISTANCE_CEILING` 이내일 때만 통과시킨다 — 둘 다 만족해야
    한다. 후보가 0건이거나 전부 게이트를 통과하지 못하면 빈 리스트. hybrid_rag_node의
    질의확장(FR44)과 doc_rag_node의 인용이 이 하나의 헬퍼·하나의 게이트를 공유한다
    (드리프트 방지).

    제목·본문이 공백뿐인 행은 건너뛰고 나머지는 반환한다(후속 코드리뷰) — 호출부마다
    따로 막으면 한쪽만 막힌다. 실제로 이전 패스는 **인용 자리에만** `guide[0]` 검사를
    넣어, 빈 제목 가이드가 hybrid의 조건추출 프롬프트에는 그대로 주입되고(매핑 없는
    "규칙 2보다 우선" 지시만 남는다) 공백 제목은 "(참고:    )"라는 빈 인용까지 통과시켰다.
    게이트를 이 한 곳으로 모아 두 구멍을 함께 닫는다.
    """
    rows = run_select(
        "SELECT title, content, embedding <=> %s::vector AS distance FROM guide_documents "
        "WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT %s",
        (qvec_literal, qvec_literal, _GUIDE_TOP_K),
    )
    if not rows:
        # 0건도 반드시 남긴다 — 안 남기면 스펙의 수동 확인("실제 거리를 로그로 관찰")을 따를 때
        # "코퍼스가 비었다/임베딩이 안 됐다"와 "로그가 없다"를 구분할 수 없다(후속 코드리뷰).
        logger.info("find_relevant_guide 후보 0건 — 인용·질의확장 생략")
        return []
    best_distance = rows[0][2]  # 1등(가장 가까운) 거리 — 상대 마진의 기준점.
    guides: list[tuple[str, str]] = []
    for title, content, distance in rows:
        # 게이트는 반드시 "통과 조건"으로 쓴다(`d <= best + margin and d <= ceiling`) —
        # `d > ...`로 뒤집어 쓰면 NaN이 통과한다. NaN과의 모든 비교는 False이므로 `>` 검사는
        # 빠져나가고, 같은 값을 쓰는 로그는 `통과=False`라고 남기는데 함수는 그 가이드를
        # 그대로 반환했다(3회차 코드리뷰 실측, 옛 절대 컷오프 시절). 즉 유일한 계측 수단이
        # 실제 동작과 반대를 말하는 상태였다. 도달 경로: 질의 임베딩이 영벡터면
        # (embeddings.py의 _l2_normalize가 norm==0을 그대로 통과시킨다) pgvector `<=>`가
        # NaN을 내고, 그때 모든 행이 NaN이라 best_distance도 NaN — `d <= NaN + margin`은
        # 항상 False이므로 top-k 게이트에서도 동일하게 전부 탈락한다(빈 리스트).
        within_margin = distance <= best_distance + _GUIDE_MARGIN
        within_ceiling = distance <= _GUIDE_DISTANCE_CEILING
        passed = within_margin and within_ceiling
        logger.info(
            "find_relevant_guide 거리=%.4f 제목=%r 통과=%s",
            distance, title, passed,
        )
        if not passed:
            continue
        if not title.strip() or not content.strip():
            # title/content는 NOT NULL이지만 빈 문자열·공백은 스키마가 막지 않는다.
            logger.info("find_relevant_guide 제목/본문이 비어 있어 생략 제목=%r", title)
            continue
        guides.append((title, content))
    return guides


def citation_titles(guides: list[tuple[str, str]], limit: int = 2) -> list[str]:
    """인용용 문서명 리스트를 만든다 — 청킹(섹션 단위 적재)으로 같은 문서의 서로 다른
    섹션 2개가 top에 오면 "A — x, A — y"처럼 인용이 장황해지는 것을 막는다.

    title에서 " — "(문서제목·섹션제목 구분자, load_corpus 참고) 앞부분만 취해 원본
    문서명 기준으로 중복 제거한 뒤 상위 최대 `limit`개를 반환한다. " — "가 없으면
    (청킹 없는 파일의 문서 전체 title) 그대로 문서명으로 쓴다. 순서는 guides 순서
    (거리 오름차순)를 유지한다.
    """
    seen: list[str] = []
    for title, _content in guides:
        doc_name = title.split(" — ", 1)[0]
        if doc_name not in seen:
            seen.append(doc_name)
        if len(seen) >= limit:
            break
    return seen


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

    # ── 근거 가이드 문서 — top-k 상대 게이트(FR49) 통과분만 answer 근거로 곁들인다 ──
    guides = find_relevant_guide(qvec)

    logger.info(
        "doc_rag_node 질의=%r 매물 %d건, 근거 가이드 %d건=%r",
        query, len(listings), len(guides), [g[0] for g in guides],
    )

    if not listings:
        return {"answer": _ANSWER_EMPTY, "listings": []}  # FR17

    answer = _ANSWER_FOUND.format(query=query, n=len(listings))
    # `title.strip()` 재검사는 이제 도달 불가하다 — find_relevant_guide가 공백 제목을 이미
    # 걸러 리스트에 안 담으므로 guides의 모든 title은 비어 있지 않다(3회차 코드리뷰). 인용은
    # citation_titles가 문서명 기준 중복 제거 후 상위 최대 2개만 뽑는다(청킹 후 같은 문서의
    # 섹션 2개가 top에 와도 인용이 장황해지지 않게).
    if guides:
        titles = citation_titles(guides)
        answer += f" (참고: {', '.join(titles)})"
    return {"answer": answer, "listings": listings}
