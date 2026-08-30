"""툴콜링 에이전트용 도구 4종 — 전부 결정론 코드다(도구 안에서 LLM 호출 금지, 4단계 부품 B).

search_listings·search_guides·market_price_stats·compare_listings 4종. 각 도구는
readonly_connection 관례(run_select/readonly_connection, db/readonly.py 4.1)로만 DB에 닿고,
파라미터는 항상 바인딩한다(사용자값을 f-string으로 SQL에 직접 박지 않는다 — sql_rag_node·
hybrid_rag_node와 동일 원칙, 함정 #1).

⚠️ search_listings의 SQL은 **코드가 조립**한다(LLM이 SQL 텍스트를 만들지 않는다) — 그래서
  sql_guard.validate_select_sql()을 거치지 않는다. 가드가 막는 대상은 "LLM이 생성한 SQL
  텍스트"이고, 이 도구는 파이썬이 고정된 절 목록에서 화이트리스트된 컬럼·연산자만 골라
  조립하므로 애초에 가드가 막으려는 위험(임의 테이블/컬럼/DDL 텍스트 생성)이 없다.
  ORDER BY 절도 마찬가지로 _SORT_WHITELIST에 없는 값은 거부한다(DW-848 해결 지점 —
  하이브리드 노드의 ORDER BY는 sql_guard의 벡터절 정규식이 고정한 모양만 허용하지만, 이
  도구는 LLM 생성 SQL이 아니므로 그 정규식과 무관하게 코드가 직접 화이트리스트를 검사한다).

search_guides는 multi_query.find_relevant_guides_fused(RRF 병합 + top-5 상대 게이트, FR49)를
  그대로 재사용하고, app.rerank_client.rerank가 있으면(사이드카 응답) 그 순서로 재정렬한다
  (병행 구현 중인 4단계 부품 A — 모듈이 없거나 임포트가 실패해도 None 취급하고 원래 순서를
  유지한다, 절대 실패시키지 않는다).

market_price_stats는 app.market_price.diagnose를 readonly_connection 트랜잭션 안에서 그대로
  호출한다(routers/market_price.py의 기존 관례와 동일 — 별도 진단 로직을 새로 만들지 않는다).

각 도구는 langchain @tool(response_format="content_and_artifact")로 감싸 (LLM에 보일 텍스트
요약, 에이전트 루프가 쓸 구조화 데이터) 쌍을 반환한다 — 에이전트 루프(agent.py)가 artifact로
selected_listing_ids 검증·market_diagnosis 노출에 쓸 매물 카드·진단 dict를 얻는다.
"""

import logging
from typing import Literal

from langchain_core.tools import tool

from app.db.readonly import readonly_connection, run_select
from app.embeddings import embed_query
from app.graph.doc_rag_node import _vec_literal
from app.graph.listing_cards import SELECT_COLUMNS, attach_cover_images, rows_to_cards
from app.graph.multi_query import find_relevant_guides_fused
from app.market_price import diagnose
from app.schemas.ai import ListingCard

logger = logging.getLogger(__name__)

try:  # 4단계 부품 A(리랭커 사이드카)가 아직 없는 환경에서도 이 파일은 정상 동작해야 한다.
    from app.rerank_client import rerank
except ImportError:  # pragma: no cover — 방어적 폴백, 현재 레포엔 파일이 이미 존재한다.
    rerank = None

# search_listings 기본/상한 — 과다조회(20건) 후 에이전트가 가이드 지식으로 5건 내외 되추린다
# (DW-849). sql_rag_node의 DEFAULT_LIMIT(5)와는 다른 상수다 — 이 도구는 "최종 추천 개수"가
# 아니라 "에이전트가 되추릴 재료 개수"를 돌려준다.
_DEFAULT_SEARCH_LIMIT = 20
_MAX_SEARCH_LIMIT = 20

# 화이트리스트 ORDER BY — LLM 생성 SQL이 아니므로 sql_guard의 벡터절 정규식과 무관하게
# 이 도구 코드가 직접 검사한다(DW-848). similarity는 별도 분기(임베딩 벡터순)로 처리한다.
_SORT_WHITELIST: dict[str, str] = {
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "year_desc": "year DESC",
    "mileage_asc": "mileage ASC",
}

# compare_listings에 한 번에 넣을 수 있는 최대 매물 수(설계 확정값) — 초과분은 앞에서부터 자른다.
_COMPARE_MAX = 4

# search_guides가 LLM에 넘기는 섹션당 본문 글자수 상한(doc_rag_node류와 동일 사상 — 프롬프트 비대화 방지).
_GUIDE_CONTENT_CHAR_CAP = 1200


def _format_listing_summary(listings: list[ListingCard]) -> str:
    """번호 매긴 간결한 매물 목록(id·모델·연식·주행·가격·연료·옵션 요약) — LLM에 보일 텍스트."""
    if not listings:
        return "조건에 맞는 매물이 없습니다."
    lines = []
    for i, c in enumerate(listings, start=1):
        opts = ", ".join((c.options or [])[:3])
        line = (
            f"{i}. id={c.id} {c.manufacturer} {c.model} {c.year}년식 "
            f"{c.mileage:,}km {c.price:,}원 연료={c.fuel or '미상'}"
        )
        if opts:
            line += f" 옵션={opts}"
        lines.append(line)
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def search_listings(
    query_text: str,
    manufacturer: str | None = None,
    model_keyword: str | None = None,
    body_type: str | None = None,
    fuel: str | None = None,
    price_max: int | None = None,
    price_min: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    mileage_max: int | None = None,
    accident_free_only: bool | None = None,
    options_any: list[str] | None = None,
    sort_by: Literal["price_asc", "price_desc", "year_desc", "mileage_asc", "similarity"] | None = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
) -> tuple[str, list[ListingCard]]:
    """조건에 맞는 매물을 검색한다. status='on_sale'만(FR11), 최대 20건까지 과다조회한다 —
    이 20건은 최종 추천 개수가 아니라 되추릴 재료다. 결과가 한 조건(예: 연료·차종)에 쏠려
    보이면 search_guides로 관련 가이드를 읽고 5건 내외로 다양성 있게 골라 최종 답하라.

    query_text는 매물 성격을 요약한 자연어(정렬 기준이 similarity일 때 벡터 검색에 쓰인다).
    sort_by 생략 시 similarity(벡터 유사도순)가 기본이다. limit은 20을 넘길 수 없다(자동 보정).
    options_any는 사용자가 요구한 옵션 문자열 목록(예: ["스마트키","통풍시트"]) — 하나라도
    포함된 매물만 걸러진다.
    """
    limit = min(max(int(limit or _DEFAULT_SEARCH_LIMIT), 1), _MAX_SEARCH_LIMIT)

    clauses = ["status = 'on_sale'"]
    params: list = []
    if manufacturer:
        clauses.append("manufacturer = %s")
        params.append(manufacturer)
    if model_keyword:
        clauses.append("model ILIKE %s")
        params.append(f"%{model_keyword}%")
    if body_type:
        clauses.append("body_type = %s")
        params.append(body_type)
    if fuel:
        clauses.append("fuel = %s")
        params.append(fuel)
    if price_max is not None:
        clauses.append("price <= %s")
        params.append(price_max)
    if price_min is not None:
        clauses.append("price >= %s")
        params.append(price_min)
    if year_min is not None:
        clauses.append("year >= %s")
        params.append(year_min)
    if year_max is not None:
        clauses.append("year <= %s")
        params.append(year_max)
    if mileage_max is not None:
        clauses.append("mileage <= %s")
        params.append(mileage_max)
    if accident_free_only:
        clauses.append("accident_free = %s")
        params.append(True)
    if options_any:
        clauses.append("options && %s::text[]")
        params.append(list(options_any))
    where_sql = " AND ".join(clauses)

    if sort_by is None or sort_by == "similarity":
        qvec = _vec_literal(embed_query(query_text))
        sql = (
            f"SELECT {SELECT_COLUMNS} FROM listings WHERE {where_sql} "
            "AND embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        rows = run_select(sql, (*params, qvec, limit))
    else:
        if sort_by not in _SORT_WHITELIST:
            # 정상 경로에서는 Literal 타입이 LLM 호출 이전에 걸러주지만(langchain 스키마
            # 검증), 함수를 직접 부르는 호출자(테스트 포함)에도 같은 방어선을 둔다(코드 방어).
            raise ValueError(f"허용되지 않은 정렬 기준입니다: {sort_by!r}")
        sql = (
            f"SELECT {SELECT_COLUMNS} FROM listings WHERE {where_sql} "
            f"ORDER BY {_SORT_WHITELIST[sort_by]} LIMIT %s"
        )
        rows = run_select(sql, (*params, limit))

    listings = attach_cover_images(rows_to_cards(rows))
    return _format_listing_summary(listings), listings


@tool
def search_guides(query_text: str) -> str:
    """중고차 구매 가이드 문서를 의미 검색한다(용도·차급·연비 등 결정에 참고). 검색 결과가
    한 조건에 쏠릴 때(예: 하이브리드만 5건) 이 도구로 관련 섹션을 읽고 다양한 차급·용도를
    조합해 최종 추천을 5건 내외로 되추리는 데 쓴다(예: 하이브리드 소형 4 + 대형 3 + 준중형
    1 → 소형+준중형으로 5건). 근거 없는 시세·통계를 지어내지 말고, 이 도구가 준 문서
    내용만 인용하라.
    """
    qvec_literal = _vec_literal(embed_query(query_text))
    guides = find_relevant_guides_fused(query_text, qvec_literal)
    if not guides:
        return "관련 가이드 문서를 찾지 못했습니다."

    if rerank is not None:
        try:
            order = rerank(query_text, [(title, content) for title, content in guides])
        except Exception as exc:  # 사이드카 실패는 원래 순서로 조용히 폴백(rerank_client와 동일 태도).
            logger.warning("search_guides 리랭크 호출 실패 — 원래 순서 유지: %r", exc)
            order = None
        if order:
            guides = [guides[i] for i in order if 0 <= i < len(guides)]

    blocks = [
        f"[{title}]\n{content[:_GUIDE_CONTENT_CHAR_CAP]}" for title, content in guides
    ]
    return "\n\n".join(blocks)


def _format_market_diagnosis(result: dict) -> str:
    listing = result["listing"]
    stats = result["stats"]
    header = (
        f"{listing['manufacturer']} {listing['model']} {listing['year']}년식 "
        f"{listing['price']:,}원"
    )
    if stats is None:
        return f"{header} — 비교 가능한 매물이 없어 시세 판정을 할 수 없습니다."
    percentile = result["percentile"]
    pct_txt = f"하위 {percentile * 100:.0f}%" if percentile is not None else "백분위 미상"
    lines = [
        f"{header} — 시세 판정: {result['verdict']}({pct_txt})",
        f"비교군 {result['criteria']['sample_count']}건({result['criteria']['desc']}) "
        f"가격범위 {stats['min']:,}~{stats['max']:,}원, 중앙값 {stats['median']:,.0f}원",
    ]
    tabpfn_price = result["tabpfn"]["price"]
    if tabpfn_price is not None:
        lines.append(f"모델 예측 적정가: {tabpfn_price:,}원")
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def market_price_stats(listing_id: str) -> tuple[str, dict | None]:
    """매물 1건의 시세를 진단한다(비교군 통계 + 적정가 예측). 직전 검색 결과의 N번째
    매물 시세를 물으면, 그 결과 목록에서 N번째 매물의 id를 골라 이 도구를 호출하라.
    """
    with readonly_connection() as conn:
        result = diagnose(listing_id, conn)
    if result is None:
        return f"매물 id={listing_id}를 찾을 수 없습니다.", None
    return _format_market_diagnosis(result), result


def _format_compare_table(listings: list[ListingCard]) -> str:
    if not listings:
        return "비교할 매물을 찾지 못했습니다."
    lines = []
    for c in listings:
        opts = ", ".join((c.options or [])[:3])
        line = (
            f"- id={c.id} {c.manufacturer} {c.model} {c.year}년식 {c.mileage:,}km "
            f"{c.price:,}원 연료={c.fuel or '미상'} 사고={c.accident_status or '미상'}"
        )
        if opts:
            line += f" 옵션={opts}"
        lines.append(line)
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def compare_listings(listing_ids: list[str]) -> tuple[str, list[ListingCard]]:
    """매물 여러 건(최대 4건)의 핵심 필드를 나란히 비교한다. 4건을 넘기면 앞의 4건만 쓴다."""
    ids = list(listing_ids)[:_COMPARE_MAX]
    if not ids:
        return "비교할 매물 id가 없습니다.", []
    rows = run_select(
        f"SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND id = ANY(%s::uuid[])",
        (ids,),
    )
    listings = attach_cover_images(rows_to_cards(rows))
    return _format_compare_table(listings), listings


# 에이전트 루프(agent.py)가 bind_tools/이름 조회에 쓰는 목록·딕셔너리.
AGENT_TOOLS = [search_listings, search_guides, market_price_stats, compare_listings]
TOOLS_BY_NAME = {t.name: t for t in AGENT_TOOLS}
