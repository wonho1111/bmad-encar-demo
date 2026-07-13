"""ListingCard 매핑 공유 헬퍼 — 경로 A(sql_rag_node)·경로 B(doc_rag_node)가 함께 쓴다.

두 노드 모두 동일한 7필드를 동일한 순서로 SELECT 해서 ListingCard로 매핑한다.
그 "컬럼 순서"가 두 곳에서 갈라지면(예: 한쪽만 컬럼을 추가) 매핑이 조용히 어긋나므로,
SELECT 컬럼 문자열과 튜플→ListingCard 매핑을 **이 한 곳(단일출처)** 에 둔다(drift 방지, AR5).
(+ 증분 nullable 6필드, 기본 None — Epic 9/10/11이 값을 채울 때 SELECT_COLUMNS와 락스텝 확장)
[Source: architecture.md#Format Patterns(ListingCard 7필드); docs/conventions.md §4]
"""

from app.schemas.ai import ListingCard

# ListingCard 7필드 — SELECT 컬럼 순서를 이 순서로 고정해 결과 매핑(rows_to_cards)을 단순화한다.
# 이 순서가 rows_to_cards의 튜플 인덱스(0~6)와 1:1로 대응한다. 둘은 항상 같이 바꿔야 한다.
SELECT_COLUMNS = "id, manufacturer, model, year, price, mileage, region"


def rows_to_cards(rows: list[tuple]) -> list[ListingCard]:
    """run_select가 돌려준 튜플(SELECT_COLUMNS 순서)을 ListingCard 목록으로 매핑한다.

    숫자 필드(year/price/mileage)는 DB 드라이버가 무엇을 주든 int로 캐스팅해 계약을 맞춘다.
    """
    cards = []
    for r in rows:
        cards.append(
            ListingCard(
                id=str(r[0]),
                manufacturer=r[1],
                model=r[2],
                year=int(r[3]),
                price=int(r[4]),
                mileage=int(r[5]),
                region=r[6],
            )
        )
    return cards
