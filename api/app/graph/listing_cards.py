"""ListingCard 매핑 공유 헬퍼 — 경로 A(sql_rag_node)·경로 B(doc_rag_node)가 함께 쓴다.

두 노드 모두 동일한 컬럼(현재 11개, SELECT_COLUMNS 참조)을 동일한 순서로 SELECT 해서
ListingCard로 매핑한다. 그 "컬럼 순서"가 두 곳에서 갈라지면(예: 한쪽만 컬럼을 추가) 매핑이
조용히 어긋나므로, SELECT 컬럼 문자열과 튜플→ListingCard 매핑을 **이 한 곳(단일출처)** 에
둔다(drift 방지, AR5). (핵심 7필드 + fuel·신뢰속성 3필드, Story 10.1 — Epic 9/10/11이 값을
채울 때 SELECT_COLUMNS와 락스텝 확장)
[Source: architecture.md#Format Patterns(ListingCard 7필드); docs/conventions.md §4]
"""

import logging
import re

from app.db.readonly import run_select
from app.db.sql_guard import SqlGuardError
from app.schemas.ai import ListingCard

logger = logging.getLogger(__name__)

# 카드 id가 UUID 모양인지 확인하는 정규식(코드리뷰 2026-07-20).
# 왜 필요한가: 아래 고정 SQL은 id 목록을 `::uuid[]`로 **한 번에** 캐스팅하므로, 하나라도
# UUID가 아니면 Postgres가 행을 보기도 전에 문장 **전체**를 실패시킨다 → except가 삼켜
# 그 응답의 **모든** 카드가 사진을 잃는다(부분 실패가 아니라 전량 실패).
# 도달 경로는 실재한다: sql_guard는 테이블·컬럼만 화이트리스트하고 **SELECT 컬럼 순서를
# SELECT_COLUMNS에 고정하지 않으므로**, LLM이 순서를 바꾼 SQL을 만들면 통과하고
# rows_to_cards가 엉뚱한 값(예: region)을 id 자리에 넣는다.
_UUID_RE = re.compile(r"\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")

# ListingCard 7필드 + fuel·신뢰속성 3필드(Story 10.1) — SELECT 컬럼 순서를 이 순서로 고정해
# 결과 매핑(rows_to_cards)을 단순화한다.
# 이 순서가 rows_to_cards의 튜플 인덱스(0~10)와 1:1로 대응한다. 둘은 항상 같이 바꿔야 한다.
SELECT_COLUMNS = (
    "id, manufacturer, model, year, price, mileage, region, "
    "fuel, accident_status, is_single_owner, is_non_smoker"
)

# rows_to_cards가 기대하는 튜플 폭 — 아래 컬럼 개수 불일치 방어의 기준값이다.
_EXPECTED_COLUMN_COUNT = len(SELECT_COLUMNS.split(","))

# accident_status 도메인 — ListingCard.accident_status는 Literal['무사고','단순교환','사고']|None이라
# 이 3값(또는 None) 밖의 문자열이 들어오면 ListingCard(...) 생성 자체가 pydantic ValidationError로
# 죽는다(코드리뷰 P2). DB CHECK(0017)가 저장을 막아 주지만, 이 함수는 LLM이 만든 임의 SELECT의
# 결과도 받는다(경로 A) — 컬럼 순서가 어긋나면(예: fuel이 accident_status 자리에 오면) 도메인 밖
# 문자열이 그대로 들어올 수 있다. conventions.md §4 "계약-외 값 정규화"대로 여기서 None으로
# 강등한다(app `listing.dart`의 fromMap이 이미 하는 방어와 같은 목적).
_ACCIDENT_STATUS_VALUES = {"무사고", "단순교환", "사고"}


def rows_to_cards(rows: list[tuple]) -> list[ListingCard]:
    """run_select가 돌려준 튜플(SELECT_COLUMNS 순서)을 ListingCard 목록으로 매핑한다.

    숫자 필드(year/price/mileage)는 DB 드라이버가 무엇을 주든 int로 캐스팅해 계약을 맞춘다.
    fuel·accident_status·is_single_owner·is_non_smoker(인덱스 7·8·9·10)는 모두 계약-외 값을
    None으로 강등한다(conventions §4 "계약-외 값 정규화") — 이유는 아래 "왜 네 필드를 다 방어하나"
    참조. is_single_owner/is_non_smoker의 NULL은 "미상"이라는 유효한 제3상태라, 강등 대상은
    "타입이 어긋난 값"이지 NULL 자체가 아니다(bool 3상태, conventions §4).

    왜 네 필드를 다 방어하나(코드리뷰 2026-07-22): pydantic ListingCard는 fuel=str|None,
    accident_status=Literal|None, is_single_owner/is_non_smoker=bool|None이라, 그 슬롯에 타입이
    어긋난 값(예: fuel 자리에 bool, is_single_owner 자리에 문자열)이 오면 ListingCard(...) 생성이
    ValidationError로 죽는다. 이건 SqlGuardError가 아니라서 sql_rag_node의 `except SqlGuardError`
    재생성 루프가 못 잡고 그대로 `/ai/search` 500이 된다(P1/P2와 같은 실패 모드). 도달 경로도
    같다 — sql_guard는 SELECT 컬럼 순서를 SELECT_COLUMNS에 고정하지 않으므로, 폭은 11로 맞지만
    순서를 바꾼 LLM SQL이 타입이 어긋난 값을 이 슬롯들에 넣을 수 있다. 그래서 accident_status만
    강등하던 P2 방어를 나머지 세 필드로 넓힌다.

    ⚠️ 튜플 폭이 SELECT_COLUMNS(11개)와 다르면 `r[7]` 등에서 바로 IndexError가 난다 — 경로 A는
    LLM이 만든 SQL을 그대로 실행하므로(sql_guard는 컬럼 화이트리스트만 보고 **SELECT 프로젝션
    개수·순서는 고정하지 않는다**, 파일 상단 주석 참조), 모델이 프롬프트 규칙 1을 어기고 옛
    7컬럼만 뽑으면 이 함수가 IndexError로 죽는다. 그러면 `sql_rag_node`의 `except SqlGuardError`가
    못 잡아 `/ai/search`가 500이 된다(코드리뷰 P1). 그래서 IndexError 대신 SqlGuardError를 던져
    **`sql_rag_node`의 기존 재생성(retry) 루프가 처리**하게 한다 — 새 방어선이 아니라 이미 있는
    방어선에 이 실패 모드를 편입시키는 것이다.
    """
    cards = []
    for r in rows:
        if len(r) != _EXPECTED_COLUMN_COUNT:
            raise SqlGuardError(
                "column_count_mismatch",
                f"조회 결과 컬럼 수가 예상과 다릅니다(받음 {len(r)}개, 기대 {_EXPECTED_COLUMN_COUNT}개). "
                f"SELECT {SELECT_COLUMNS} FROM listings 형태로 컬럼을 빠짐없이 순서대로 조회해 주세요.",
            )
        raw_accident_status = r[8]
        cards.append(
            ListingCard(
                id=str(r[0]),
                manufacturer=r[1],
                model=r[2],
                year=int(r[3]),
                price=int(r[4]),
                mileage=int(r[5]),
                region=r[6],
                # fuel·신뢰속성 3필드 — 타입이 어긋난 값은 None으로 강등한다(docstring "왜 네
                # 필드를 다 방어하나" 참조). isinstance(x, bool)은 int 1/0을 bool로 오인하지 않는다.
                fuel=(r[7] if isinstance(r[7], str) else None),
                accident_status=(
                    raw_accident_status if raw_accident_status in _ACCIDENT_STATUS_VALUES else None
                ),
                is_single_owner=(r[9] if isinstance(r[9], bool) else None),
                is_non_smoker=(r[10] if isinstance(r[10], bool) else None),
            )
        )
    return cards


# 대표 사진 1장 + 총 장수를 매물당 한 행으로 구하는 **손으로 쓴 고정 SQL**(Story 9.6 AC1).
#
# LLM이 만들지 않으므로 sql_guard를 타지 않는다 — 가드가 겨누는 것은 LLM 생성 SQL이고,
# 그쪽은 여전히 listings 단일 테이블만 허용한다(tests/test_sql_guard.py가 못박는다).
#
# ⚠️ `l.status = 'on_sale'`이 FR11을 지키는 **유일한 지점**이다.
#    ai_readonly의 listing_images 정책은 `using(true)`라 sold 사진 메타까지 전부 열려 있다
#    (0012:153 — 의도된 설계, CR2). "카드 id가 이미 on_sale에서 왔다"는 상위 단계에 대한
#    신뢰일 뿐이고, CLAUDE.md B9는 중요한 값을 데이터 계층이 직접 구하라고 한다.
#    이 조건을 지우면 tests/test_listing_cards.py의 sold 테스트가 red가 된다.
#
# 정렬·대표 판별은 SQL이 한다(conventions.md §10.2):
#   · `DISTINCT ON (listing_id)` + `ORDER BY listing_id, sort_order, id` → 매물별 첫 행 = 대표.
#   · 2차 키 `id`가 없으면 sort_order 동률(#47-2)에서 호출할 때마다 대표가 바뀐다.
#   · `is_cover`는 순서의 파생값이라 **읽지 않는다** — 목록 카드(coverImages.ts)와 같은 규칙.
#   · 파이썬에서 다시 정렬하지 않는다 — 비교자 사본을 세 벌째 만들지 않기 위해서다(#81).
# `count(*) OVER (PARTITION BY ...)`는 DISTINCT ON보다 먼저 계산되므로 매물의 **전체** 장수다.
_COVER_IMAGE_SQL = """
SELECT DISTINCT ON (i.listing_id)
       i.listing_id,
       i.storage_path,
       count(*) OVER (PARTITION BY i.listing_id)
  FROM listing_images i
  JOIN listings l ON l.id = i.listing_id
 WHERE i.listing_id = ANY(%s::uuid[])
   AND l.status = 'on_sale'
 ORDER BY i.listing_id, i.sort_order, i.id
"""


def attach_cover_images(cards: list[ListingCard]) -> list[ListingCard]:
    """카드 목록에 대표 사진 경로(image_path)와 사진 장수(image_count)를 채워 돌려준다.

    경로 A(sql_rag_node)·경로 B(doc_rag_node)가 **둘 다 이 함수를 통과한다** — 사진을 붙이는
    자리를 두 노드에 복사하면 이 파일의 존재 이유(경로 A·B drift 방지)가 무너진다.

    사진이 0장인 매물은 쿼리 결과에 아예 없으므로 `(None, 0)`이 된다 — 정상 상태다
    (conventions.md §10.2 "대표 0장은 정상"). 카드를 버리지 않는다.

    조회가 실패해도 **AI 답변 전체를 실패시키지 않는다** — 사진 없는 카드가 빈 화면보다 낫다
    (web `listings.ts`의 기존 정책 상속). 실패는 서버 로그에만 남는다.
    ⚠️ 그 대가로 `docs/tech-debt.md` #73(전면 장애와 "사진 0장"이 화면에서 구별 안 됨)을
       그대로 상속한다 — 이 스토리에서 새로 해결하지 않는다.
    """
    if not cards:
        # 불필요한 DB 왕복 회피 — 카드가 없으면 쿼리를 아예 쏘지 않는다.
        # ✎ 2026-07-20 코드리뷰: 여기 근거가 "빈 IN () 금지"로 적혀 있었으나 **틀렸다** —
        #   이 쿼리는 `IN`이 아니라 `= ANY(배열)`이고, 빈 배열은 문법 오류가 아니라 0행을
        #   정상 반환한다. 조기 반환 자체는 옳지만 이유가 달랐다(같은 오해가 에픽 원문·
        #   테스트 docstring에도 복사돼 있었다 — 함께 정정).
        return cards

    # UUID 모양인 id만 넘긴다(_UUID_RE 주석 참조) — 하나가 깨져도 나머지 카드는 사진을 지킨다.
    lookup_ids = [c.id for c in cards if _UUID_RE.match(c.id)]
    if len(lookup_ids) != len(cards):
        logger.warning(
            "attach_cover_images: UUID가 아닌 카드 id %d건을 사진 조회에서 제외했다",
            len(cards) - len(lookup_ids),
        )

    covers: dict[str, tuple[str | None, int]] = {}
    if lookup_ids:
        try:
            rows = run_select(_COVER_IMAGE_SQL, (lookup_ids,))
            # ⚠️ 행 해석도 **try 안**에 둔다(코드리뷰 2026-07-20) — 밖에 두면 행이 짧거나
            #    count가 None일 때(int(None)) 예외가 그대로 위로 터져 `/ai/search`가 500이
            #    되고, 위 docstring이 약속한 "답변 전체를 실패시키지 않는다"가 깨진다.
            covers = {str(r[0]): (r[1], int(r[2])) for r in rows}
        except Exception:  # DB 장애·권한·행 형태 이상 — 사진만 포기하고 카드는 그대로 보낸다.
            logger.exception("attach_cover_images 사진 조회 실패 — 사진 없이 카드만 반환한다")
            covers = {}
    for card in cards:
        path, count = covers.get(card.id, (None, 0))
        card.image_path = path
        card.image_count = count
    return cards
