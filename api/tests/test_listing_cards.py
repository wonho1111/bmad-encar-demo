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

import app.graph.listing_cards as module
from app.graph.listing_cards import attach_cover_images
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
