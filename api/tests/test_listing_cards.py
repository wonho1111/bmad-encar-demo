"""attach_cover_images(경로 A·B 공용 사진 부착) 단위 테스트 — Story 9.6 AC1·AC2·AC7.

DB를 띄우지 않는다: run_select를 가짜로 교체해 **어떤 SQL·파라미터가 나가는지**와
**돌아온 행이 어떻게 카드에 붙는지**만 결정론적으로 검증한다(project-context 규칙12).

여기서 지키는 것:
  · AC1 — 대표 경로(image_path)·총 장수(image_count)가 카드에 붙는다. 사진 0장은 (None, 0).
  · AC1 — 카드가 0건이면 쿼리를 **아예 쏘지 않는다**(빈 IN () 금지).
  · AC2 — 고정 SQL이 listings와 조인해 status='on_sale'을 **직접** 건다.
          이 쿼리가 sold 사진을 거르는 **유일한 지점**이다(ai_readonly RLS는 using(true) —
          0012:153). 그래서 "WHERE절이 있다"만 보지 않고, sold 매물의 storage_path가
          응답 카드에 **실리지 않는다**까지 단언한다(존재 확인 ≠ 작동 확인, CLAUDE.md B4).
  · AC7 — 정렬은 SQL의 ORDER BY sort_order, id가 한다(파이썬에 세 번째 비교자 금지 — #81).
  · Dev Notes §4 — 사진 조회가 실패해도 AI 답변 전체를 실패시키지 않는다.

⚠️ **이 파일이 못 보는 것**(추측이 아니라 red/green을 돌려 확인한 경계, 2026-07-20):
  run_select가 가짜라 **SQL은 한 번도 Postgres에 닿지 않는다.** 그래서 아래는 여기서 증명되지
  않으며 실브라우저·실DB 검증(AC11)이 담당한다 —
    · 쿼리가 문법적으로 유효한지(`DISTINCT ON`·window·`::uuid[]` 캐스팅 포함)
    · `ai_readonly` 롤이 `listing_images`·`listings`를 실제로 읽을 권한이 있는지
    · `DISTINCT ON` + `ORDER BY`가 진짜로 sort_order 첫 행을 고르는지
    · 실제 sold 매물의 사진이 실DB에서 걸러지는지 (여기 sold 테스트의 필터는 **가짜 DB가 흉내낸 것**
      이다 — 쿼리에 조건이 있는지를 보고 스스로 적용한다. 즉 "조건을 안 쓰면 잡는다"는 보장하지만
      "쓴 조건이 Postgres에서 의도대로 동작한다"는 보장하지 않는다.)
"""

import pytest

import app.graph.listing_cards as module
from app.db.sql_guard import SqlGuardError
from app.graph.listing_cards import SELECT_COLUMNS, attach_cover_images, rows_to_cards
from app.schemas.ai import ListingCard


# 실제 UUID 모양 id — 고정 SQL이 `::uuid[]`로 캐스팅하므로 "l-1" 같은 값은 진짜 Postgres에서
# 무조건 실패한다. 불가능한 입력으로 "정상 동작"을 검증하지 않기 위해 실 UUID를 쓴다
# (코드리뷰 2026-07-20).
_L1 = "11111111-1111-4111-8111-111111111111"
_L2 = "22222222-2222-4222-8222-222222222222"
_SOLD = "33333333-3333-4333-8333-333333333333"


def _card(listing_id: str) -> ListingCard:
    """사진 필드가 아직 비어 있는(rows_to_cards 직후) 카드 한 장."""
    return ListingCard(
        id=listing_id,
        manufacturer="현대",
        model="싼타페",
        year=2020,
        price=26700000,
        mileage=62000,
        region="강원",
    )


def _install_fake_run_select(monkeypatch, rows, captured):
    def fake_run_select(query, params=None):
        captured["query"] = query
        captured["params"] = params
        return rows

    monkeypatch.setattr(module, "run_select", fake_run_select)


# --- Story 10.1: SELECT_COLUMNS ↔ rows_to_cards 위치 매핑 ---------------------------
# 상수(문자열)와 매핑 함수(인덱스)가 따로 바뀌면 카드 필드가 조용히 뒤바뀐다(conventions §4.1
# 경고). 컬럼 개수와 읽는 인덱스 개수가 같은지, 그리고 신규 필드(fuel·신뢰속성 3개 + Story 10.3
# options)까지 실제로 올바른 자리에 매핑되는지를 여기서 못박는다.


def test_select_columns_count_matches_rows_to_cards_indices():
    """SELECT_COLUMNS의 컬럼 개수 == rows_to_cards가 읽는 인덱스 개수(0~11, 12개)."""
    columns = [c.strip() for c in SELECT_COLUMNS.split(",")]
    assert len(columns) == 12
    assert columns == [
        "id", "manufacturer", "model", "year", "price", "mileage", "region",
        "fuel", "accident_status", "is_single_owner", "is_non_smoker", "options",
    ]


def test_rows_to_cards_maps_12_tuple_including_new_fields():
    """12튜플 입력이 fuel·신뢰속성 3필드·options까지 올바른 위치로 매핑된다(기존 7필드는 뒤바뀌지 않음)."""
    rows = [
        (
            _L1, "현대", "싼타페", 2020, 26700000, 62000, "강원",
            "가솔린", "무사고", True, False, ["선루프", "통풍시트"],
        ),
    ]
    cards = rows_to_cards(rows)

    assert len(cards) == 1
    c = cards[0]
    # 기존 7필드 — 값이 서로 뒤바뀌지 않았는지 자리별로 확인.
    assert c.id == _L1
    assert c.manufacturer == "현대"
    assert c.model == "싼타페"
    assert c.year == 2020
    assert c.price == 26700000
    assert c.mileage == 62000
    assert c.region == "강원"
    # 신규 필드(fuel·신뢰속성 3개 + options).
    assert c.fuel == "가솔린"
    assert c.accident_status == "무사고"
    assert c.is_single_owner is True
    assert c.is_non_smoker is False
    assert c.options == ["선루프", "통풍시트"]


# --- Story 10.3: options(text[]) 계약-외 값 정규화 ----------------------------------


def test_rows_to_cards_degrades_non_list_options_to_none():
    """options 자리에 리스트가 아닌 값이 오면(컬럼 순서가 어긋난 LLM SQL 등) None으로 강등한다."""
    rows = [
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", "가솔린", "무사고", True, False, "덤"),
    ]
    cards = rows_to_cards(rows)

    assert cards[0].options is None


def test_rows_to_cards_degrades_options_with_non_string_elements_to_none():
    """options 리스트 원소에 문자열이 아닌 값이 섞이면 배열 전체를 None으로 강등한다."""
    rows = [
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", "가솔린", "무사고", True, False, ["선루프", 1]),
    ]
    cards = rows_to_cards(rows)

    assert cards[0].options is None


def test_rows_to_cards_null_options_stays_none():
    """options가 NULL(None)이면 그대로 None — 빈 배열과 다른 상태를 유지한다."""
    rows = [
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", "가솔린", "무사고", True, False, None),
    ]
    cards = rows_to_cards(rows)

    assert cards[0].options is None


def test_rows_to_cards_empty_options_stays_empty_list():
    """options가 빈 배열이면 빈 배열 그대로(카드가 옵션 0개임을 그대로 반영, None과 구분)."""
    rows = [
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", "가솔린", "무사고", True, False, []),
    ]
    cards = rows_to_cards(rows)

    assert cards[0].options == []


# --- 코드리뷰 P1: 컬럼 수가 안 맞으면 IndexError가 아니라 SqlGuardError ------------------
# 경로 A(sql_rag_node)는 LLM이 만든 SQL을 그대로 실행한다. sql_guard는 컬럼 화이트리스트만
# 보고 SELECT 프로젝션 개수·순서는 고정하지 않으므로, LLM이 프롬프트 규칙 1을 어기고 옛
# 7컬럼만 뽑으면 이 함수가 r[7]에서 IndexError로 죽는다 — sql_rag_node는 `except SqlGuardError`
# 만 잡으므로 IndexError는 못 잡혀 `/ai/search`가 500이 된다. SqlGuardError를 던지면 기존
# 재생성 루프가 처리한다(500이 아니라 재시도).


def test_rows_to_cards_raises_sql_guard_error_on_short_tuple():
    """7튜플(옛 컬럼 수) 입력 → SqlGuardError(IndexError 아님)."""
    short_row = [(_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원")]  # 7개뿐(12개 기대)
    try:
        rows_to_cards(short_row)
        assert False, "짧은 튜플인데 예외가 안 났다"
    except SqlGuardError:
        pass  # 기대한 경로 — sql_rag_node의 재생성 루프가 이 예외를 잡는다.
    except IndexError:
        assert False, "IndexError가 그대로 샜다 — sql_rag_node가 못 잡아 500이 된다(P1 회귀)"


def test_rows_to_cards_raises_sql_guard_error_on_long_tuple():
    """컬럼이 더 많이 온 경우(13개)도 같은 방식으로 거부한다 — 폭 불일치는 방향과 무관하다."""
    long_row = [
        (
            _L1, "현대", "싼타페", 2020, 26700000, 62000, "강원",
            "가솔린", "무사고", True, False, ["선루프"], "덤",
        )
    ]
    with pytest.raises(SqlGuardError):
        rows_to_cards(long_row)


# --- 코드리뷰 P2: accident_status 도메인 밖 값은 카드 전체를 죽이지 않고 None으로 강등 -----
# ListingCard.accident_status는 Literal['무사고','단순교환','사고']|None이라, 컬럼 순서가
# 어긋나 도메인 밖 문자열이 오면 ListingCard(...) 생성 자체가 ValidationError로 죽는다
# (그 결과셋의 다른 카드까지 전부 소실). conventions.md §4 "계약-외 값 정규화"대로 여기서
# 미리 걸러 None으로 강등한다.


def test_rows_to_cards_degrades_out_of_domain_accident_status_to_none():
    """accident_status 자리에 3값 밖 문자열이 와도 예외 없이 None으로 강등되고 카드는 산다."""
    rows = [
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", "가솔린", "외판교환", None, None, None),
    ]
    cards = rows_to_cards(rows)  # ValidationError가 나면 이 줄에서 테스트가 실패한다.

    assert len(cards) == 1
    assert cards[0].accident_status is None
    assert cards[0].fuel == "가솔린"  # 다른 필드는 영향받지 않는다


def test_rows_to_cards_degrades_wrong_typed_fuel_and_bool_fields_to_none():
    """fuel·is_single_owner·is_non_smoker 자리에 타입이 어긋난 값이 와도 예외 없이 None으로
    강등되고 카드는 산다(코드리뷰 2026-07-22).

    왜 이 테스트가 있나: sql_guard는 SELECT 컬럼 **순서**를 고정하지 않으므로, 폭은 12로 맞지만
    순서를 바꾼 LLM SQL이 fuel 자리에 bool을, is_single_owner 자리에 문자열을 넣을 수 있다.
    강등이 없으면 ListingCard(...)가 pydantic ValidationError로 죽고 — 그건 SqlGuardError가
    아니라서 sql_rag_node의 재생성 루프가 못 잡아 `/ai/search`가 500이 된다(accident_status만
    강등하던 P2 방어의 사각지대). accident_status를 잡던 것과 같은 실패 모드다.
    """
    rows = [
        # fuel 자리에 bool, is_single_owner 자리에 문자열(region 값), is_non_smoker 자리에 int.
        (_L1, "현대", "싼타페", 2020, 26700000, 62000, "강원", True, "무사고", "서울", 1, None),
    ]
    cards = rows_to_cards(rows)  # ValidationError가 나면 이 줄에서 테스트가 실패한다(500 회귀).

    assert len(cards) == 1
    c = cards[0]
    assert c.fuel is None, "타입 어긋난 fuel이 None으로 강등되지 않았다"
    assert c.is_single_owner is None, "문자열이 온 is_single_owner가 None으로 강등되지 않았다"
    assert c.is_non_smoker is None, "int가 온 is_non_smoker가 None으로 강등되지 않았다"
    # 기존 7필드는 영향받지 않는다.
    assert c.id == _L1
    assert c.region == "강원"


def test_rows_to_cards_null_trust_fields_stay_none():
    """신규 컬럼이 전부 NULL인 행 — fuel은 실값, 신뢰속성 3필드·options는 None(3상태 유지, I/O 매트릭스)."""
    rows = [(_L1, "기아", "K5", 2021, 20000000, 30000, "서울", "디젤", None, None, None, None)]
    c = rows_to_cards(rows)[0]

    assert c.fuel == "디젤"
    assert c.accident_status is None
    assert c.is_single_owner is None
    assert c.is_non_smoker is None
    assert c.options is None


# --- AC1: 대표 경로·장수 부착 -------------------------------------------------------


def test_attaches_cover_path_and_count(monkeypatch):
    captured = {}
    # DB가 매물당 1행(대표 + 총 장수)을 돌려준다 — DISTINCT ON이 SQL에서 이미 골랐다.
    _install_fake_run_select(
        monkeypatch,
        [(_L1, "u/l-1/a.webp", 3), (_L2, "u/l-2/b.webp", 1)],
        captured,
    )

    cards = attach_cover_images([_card(_L1), _card(_L2)])

    assert cards[0].image_path == "u/l-1/a.webp"
    assert cards[0].image_count == 3
    assert cards[1].image_path == "u/l-2/b.webp"
    assert cards[1].image_count == 1


def test_listing_without_photos_gets_none_and_zero(monkeypatch):
    """사진 0장 매물은 쿼리 결과에 아예 없다 → (None, 0). 카드를 버리지 않는다."""
    captured = {}
    _install_fake_run_select(monkeypatch, [(_L1, "u/l-1/a.webp", 2)], captured)

    cards = attach_cover_images([_card(_L1), _card(_L2)])

    assert cards[1].image_path is None
    assert cards[1].image_count == 0
    assert len(cards) == 2  # 사진이 없다고 카드가 사라지면 안 된다


def test_no_query_when_no_cards(monkeypatch):
    """카드 0건이면 쿼리를 쏘지 않는다(빈 IN () 금지)."""
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    assert attach_cover_images([]) == []
    assert "query" not in captured, "카드가 0건인데 DB 쿼리가 나갔다"


def test_query_binds_card_ids_as_parameters(monkeypatch):
    """id는 문자열 보간이 아니라 **파라미터 바인딩**으로 넘긴다(인젝션 여지 0)."""
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    attach_cover_images([_card(_L1), _card(_L2)])

    assert captured["params"] == ([_L1, _L2],)
    assert _L1 not in captured["query"], "id가 SQL 문자열에 직접 박혔다"


# --- AC2: FR11 — 이미지 쿼리 자체가 on_sale을 강제한다 ------------------------------


def test_query_joins_listings_and_filters_on_sale(monkeypatch):
    """고정 SQL이 listings와 조인해 status='on_sale'을 직접 건다.

    ai_readonly의 listing_images 정책은 using(true)라 sold 사진까지 전부 열려 있다
    (0012:153, 의도된 설계). 즉 이 WHERE절이 FR11을 지키는 유일한 지점이다.
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    attach_cover_images([_card(_L1)])

    q = " ".join(captured["query"].lower().split())
    assert "join listings" in q, "listings와 조인하지 않는다 — sold를 거를 수단이 없다"
    assert "status = 'on_sale'" in q, "FR11 필터가 쿼리에 없다"


def test_sold_listing_photo_never_reaches_card(monkeypatch):
    """**sold 매물의 storage_path는 절대 카드에 실리지 않는다.**

    "WHERE절이 있다"(위 테스트)는 존재 확인이고, 이건 작동 확인이다(B4).
    DB 역할을 하는 가짜가 on_sale 필터를 실제로 적용한다 — 쿼리에서 그 조건이 빠지면
    sold 행이 통과해 이 테스트가 red가 된다.
    """
    captured = {}
    # 가짜 DB: l-sold는 sold 매물이고 사진이 있다. l-1은 on_sale.
    listings_status = {_L1: "on_sale", _SOLD: "sold"}
    images = {_L1: "u/l-1/a.webp", _SOLD: "u/l-sold/secret.webp"}

    def fake_run_select(query, params=None):
        captured["query"] = query
        q = " ".join(query.lower().split())
        ids = params[0]
        rows = []
        for lid in ids:
            if lid not in images:
                continue
            # 쿼리가 on_sale을 걸었을 때만 필터가 적용된다(안 걸었으면 sold도 통과 → red).
            if "status = 'on_sale'" in q and listings_status[lid] != "on_sale":
                continue
            rows.append((lid, images[lid], 1))
        return rows

    monkeypatch.setattr(module, "run_select", fake_run_select)

    cards = attach_cover_images([_card(_L1), _card(_SOLD)])

    by_id = {c.id: c for c in cards}
    assert by_id[_L1].image_path == "u/l-1/a.webp"
    assert by_id[_SOLD].image_path is None, "sold 매물의 사진 경로가 응답에 실렸다 (FR11 위반)"
    assert by_id[_SOLD].image_count == 0
    assert "secret" not in str([c.model_dump() for c in cards])


# --- AC7: 정렬은 SQL이 한다 ---------------------------------------------------------


def test_query_orders_by_sort_order_then_id(monkeypatch):
    """대표 = `sort_order` → `id` 정렬의 첫 행. 2차 키 id가 없으면 대표가 매번 바뀐다(#47-2).

    파이썬에서 다시 정렬하지 않는다 — 세 번째 비교자 사본을 만들지 않기 위해서다(#81).
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    attach_cover_images([_card(_L1)])

    q = " ".join(captured["query"].lower().split())
    assert "order by" in q
    # ✎ 2026-07-20 코드리뷰: 원래 `"sort_order" in q and "id" in q`였는데, "id"가
    #   "listing_id"의 부분문자열이라 2차 키 i.id를 **지워도 통과**했다(실측: 8/8 green).
    #   2차 키 유실이 이 AC의 유일한 회귀인데 그걸 못 잡던 자리다. 통째로 단언한다.
    assert "order by i.listing_id, i.sort_order, i.id" in q
    # is_cover는 파생값이라 읽지 않는다(conventions.md §10.2).
    assert "is_cover" not in q, "is_cover를 읽고 있다 — 대표 판별 규칙이 목록 카드와 갈린다"


# --- Dev Notes §4: 조회 실패는 답변 전체를 죽이지 않는다 ----------------------------


def test_query_failure_returns_cards_without_photos(monkeypatch):
    """사진 조회가 실패해도 카드는 그대로 간다(사진 없는 카드 > 빈 화면)."""

    def boom(query, params=None):
        raise RuntimeError("DB 연결 실패")

    monkeypatch.setattr(module, "run_select", boom)

    cards = attach_cover_images([_card(_L1)])

    assert len(cards) == 1
    assert cards[0].image_path is None
    assert cards[0].image_count == 0


# --- 코드리뷰 2026-07-20 반영분 ------------------------------------------------------


def test_non_uuid_card_id_does_not_kill_other_cards_photos(monkeypatch):
    """UUID가 아닌 id 한 건이 섞여도 **나머지 카드는 사진을 지킨다.**

    왜 이 테스트가 있나: 고정 SQL은 id 목록을 `::uuid[]`로 한 번에 캐스팅하므로, 진짜
    Postgres에서는 값 하나만 깨져도 **문장 전체가** 실패한다 → except가 삼켜 그 응답의
    모든 카드가 사진을 잃는다(전량 실패). 그래서 바인딩 전에 UUID 모양만 거른다.
    도달 경로: sql_guard가 SELECT 컬럼 **순서**를 고정하지 않아 id 자리에 region 등이 올 수 있다.
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [(_L1, "u/l-1/a.webp", 2)], captured)

    cards = attach_cover_images([_card(_L1), _card("강원")])

    # 깨진 id는 조회 대상에서 빠진다 — 배열 전체를 죽이지 않는다.
    assert captured["params"] == ([_L1],)
    by_id = {c.id: c for c in cards}
    assert by_id[_L1].image_path == "u/l-1/a.webp", "정상 카드가 깨진 id 때문에 사진을 잃었다"
    assert by_id["강원"].image_path is None
    assert len(cards) == 2  # 카드 자체는 버리지 않는다


def test_all_ids_invalid_skips_query(monkeypatch):
    """쓸 수 있는 id가 하나도 없으면 쿼리를 쏘지 않는다(빈 배열 왕복 회피)."""
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    cards = attach_cover_images([_card("강원"), _card("서울")])

    assert "query" not in captured, "유효한 id가 0건인데 DB 쿼리가 나갔다"
    assert all(c.image_path is None and c.image_count == 0 for c in cards)


def test_malformed_row_does_not_kill_the_answer(monkeypatch):
    """돌아온 **행 모양이 이상해도** 답변 전체를 실패시키지 않는다.

    조회는 성공했는데 count가 None이면 `int(None)`에서 터진다. 이 해석부가 try 밖에 있으면
    예외가 노드를 관통해 `/ai/search`가 500이 되고, docstring의 "답변을 죽이지 않는다"가
    깨진다(코드리뷰 2026-07-20). 일부러 깨진 행을 돌려주고 카드가 살아 오는지 본다.
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [(_L1, "u/l-1/a.webp", None)], captured)

    cards = attach_cover_images([_card(_L1)])

    assert len(cards) == 1, "행 해석 실패가 답변 전체를 죽였다"
    assert cards[0].image_path is None
    assert cards[0].image_count == 0
