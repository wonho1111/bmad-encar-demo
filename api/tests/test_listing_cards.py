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
        [("l-1", "u/l-1/a.webp", 3), ("l-2", "u/l-2/b.webp", 1)],
        captured,
    )

    cards = attach_cover_images([_card("l-1"), _card("l-2")])

    assert cards[0].image_path == "u/l-1/a.webp"
    assert cards[0].image_count == 3
    assert cards[1].image_path == "u/l-2/b.webp"
    assert cards[1].image_count == 1


def test_listing_without_photos_gets_none_and_zero(monkeypatch):
    """사진 0장 매물은 쿼리 결과에 아예 없다 → (None, 0). 카드를 버리지 않는다."""
    captured = {}
    _install_fake_run_select(monkeypatch, [("l-1", "u/l-1/a.webp", 2)], captured)

    cards = attach_cover_images([_card("l-1"), _card("l-2")])

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

    attach_cover_images([_card("l-1"), _card("l-2")])

    assert captured["params"] == (["l-1", "l-2"],)
    assert "l-1" not in captured["query"], "id가 SQL 문자열에 직접 박혔다"


# --- AC2: FR11 — 이미지 쿼리 자체가 on_sale을 강제한다 ------------------------------


def test_query_joins_listings_and_filters_on_sale(monkeypatch):
    """고정 SQL이 listings와 조인해 status='on_sale'을 직접 건다.

    ai_readonly의 listing_images 정책은 using(true)라 sold 사진까지 전부 열려 있다
    (0012:153, 의도된 설계). 즉 이 WHERE절이 FR11을 지키는 유일한 지점이다.
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    attach_cover_images([_card("l-1")])

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
    listings_status = {"l-1": "on_sale", "l-sold": "sold"}
    images = {"l-1": "u/l-1/a.webp", "l-sold": "u/l-sold/secret.webp"}

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

    cards = attach_cover_images([_card("l-1"), _card("l-sold")])

    by_id = {c.id: c for c in cards}
    assert by_id["l-1"].image_path == "u/l-1/a.webp"
    assert by_id["l-sold"].image_path is None, "sold 매물의 사진 경로가 응답에 실렸다 (FR11 위반)"
    assert by_id["l-sold"].image_count == 0
    assert "secret" not in str([c.model_dump() for c in cards])


# --- AC7: 정렬은 SQL이 한다 ---------------------------------------------------------


def test_query_orders_by_sort_order_then_id(monkeypatch):
    """대표 = `sort_order` → `id` 정렬의 첫 행. 2차 키 id가 없으면 대표가 매번 바뀐다(#47-2).

    파이썬에서 다시 정렬하지 않는다 — 세 번째 비교자 사본을 만들지 않기 위해서다(#81).
    """
    captured = {}
    _install_fake_run_select(monkeypatch, [], captured)

    attach_cover_images([_card("l-1")])

    q = " ".join(captured["query"].lower().split())
    assert "order by" in q
    assert "sort_order" in q and "id" in q
    # is_cover는 파생값이라 읽지 않는다(conventions.md §10.2).
    assert "is_cover" not in q, "is_cover를 읽고 있다 — 대표 판별 규칙이 목록 카드와 갈린다"


# --- Dev Notes §4: 조회 실패는 답변 전체를 죽이지 않는다 ----------------------------


def test_query_failure_returns_cards_without_photos(monkeypatch):
    """사진 조회가 실패해도 카드는 그대로 간다(사진 없는 카드 > 빈 화면)."""

    def boom(query, params=None):
        raise RuntimeError("DB 연결 실패")

    monkeypatch.setattr(module, "run_select", boom)

    cards = attach_cover_images([_card("l-1")])

    assert len(cards) == 1
    assert cards[0].image_path is None
    assert cards[0].image_count == 0
