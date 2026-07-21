"""FR11 실DB 검증 — sold 매물의 사진은 **진짜 Postgres에서** AI 카드에 실리지 않는다.

왜 이 파일이 따로 있나 (코드리뷰 2026-07-20, docs/tech-debt.md #48):
  `tests/test_listing_cards.py`의 sold 테스트는 **가짜 DB**를 쓴다. 그 가짜는 쿼리 문자열에
  `status = 'on_sale'`이라는 글자가 있는지 보고 스스로 필터를 흉내 낸다. 그래서 조건을
  **지우면** 잡지만 **무력화하면**(`OR true`·`AND false`·`LEFT JOIN`) 전부 초록이다 — 실측으로
  확인했다. 즉 그 층은 "글자가 있나"까지만 보장하고 "Postgres가 실제로 거르나"는 못 본다.

  A안(문서 설계)을 택하면서 FR11 강제가 DB(RLS)가 아니라 **api 고정쿼리의 WHERE절**로
  옮겨왔다. `ai_readonly`의 listing_images 정책은 `using(true)`라 sold 사진까지 열려 있으므로
  (0012:153, 의도된 설계) 그 WHERE절이 **거르는 유일한 지점**이다. 그 유일한 방어를 문자열
  검사로 지킬 수는 없다 — 그래서 진짜 Postgres에 붙는 이 층이 필요하다(CLAUDE.md B4·B9).

무엇을 증명하나: api가 실제로 부르는 `attach_cover_images()`를 그대로 호출한다.
  파라미터 바인딩·`::uuid[]` 캐스팅·`DISTINCT ON`·`ai_readonly` 롤 전환까지 전 경로가 실행된다.
무엇을 못 보나: 운영 DB의 데이터가 마이그레이션과 어긋난 경우(스키마 드리프트) —
  그건 migration-gate.yml 소관이다.

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬에서 돌리려면 같은 변수를 직접 지정한다. 없으면 skip(거짓 통과 금지).
"""

import os
import uuid

import psycopg
import pytest

from app.graph.listing_cards import attach_cover_images
from app.schemas.ai import ListingCard

_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DSN, reason="TEST_DATABASE_URL 미설정 — 실DB 통합 검증은 CI의 api-db 잡에서 돈다"
)

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)


def _insert_listing(cur, listing_id, seller_id, status):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, %s, '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id, status),
    )


@pytest.fixture
def seeded(monkeypatch):
    """on_sale 1건 + sold 1건, 각각 사진 1장. 테스트 후 **롤백**해 DB를 원상복구한다."""
    monkeypatch.setenv("DATABASE_URL", _DSN)
    # readonly 모듈은 import 시점이 아니라 최초 호출 때 풀을 만든다 — 여기서 강제로 재설정.
    from app.db import readonly

    readonly._pool = None
    monkeypatch.setattr(readonly.settings, "database_url", _DSN, raising=False)

    seller_id = uuid.uuid4()
    on_sale_id, sold_id = uuid.uuid4(), uuid.uuid4()

    with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("insert into auth.users (id, email) values (%s, %s)", (seller_id, "s@t.test"))
        cur.execute(
            "insert into public.profiles (id, role) values (%s, 'seller') "
            "on conflict (id) do nothing",
            (seller_id,),
        )
        _insert_listing(cur, on_sale_id, seller_id, "on_sale")
        _insert_listing(cur, sold_id, seller_id, "sold")
        cur.execute(
            "insert into public.listing_images (listing_id, storage_path, sort_order) values "
            "(%s, %s, 0), (%s, %s, 0)",
            (on_sale_id, f"{seller_id}/{on_sale_id}/live.webp",
             sold_id, f"{seller_id}/{sold_id}/secret.webp"),
        )

    yield on_sale_id, sold_id, seller_id

    with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("delete from public.listings where seller_id = %s", (seller_id,))
        cur.execute("delete from public.profiles where id = %s", (seller_id,))
        cur.execute("delete from auth.users where id = %s", (seller_id,))


def _card(listing_id) -> ListingCard:
    return ListingCard(
        id=str(listing_id), manufacturer="현대", model="싼타페",
        year=2020, price=26700000, mileage=62000, region="서울",
    )


def test_sold_listing_photo_never_reaches_card_on_real_postgres(seeded):
    """**진짜 Postgres**에서 sold 매물의 storage_path가 카드에 실리지 않는다.

    이 테스트가 잡는 회귀(가짜 DB 층이 못 잡던 것):
      · `AND l.status = 'on_sale'` → `AND (l.status = 'on_sale' OR true)`
      · `JOIN listings` → `LEFT JOIN listings`
      · 조인 키 오타 등 — 문자열은 멀쩡한데 의미가 뒤집히는 모든 변형
    """
    on_sale_id, sold_id, seller_id = seeded

    cards = attach_cover_images([_card(on_sale_id), _card(sold_id)])
    by_id = {c.id: c for c in cards}

    # 판매중 매물은 사진이 정상적으로 붙는다 — 필터가 과잉 차단하지 않는지도 함께 본다.
    assert by_id[str(on_sale_id)].image_path == f"{seller_id}/{on_sale_id}/live.webp"
    assert by_id[str(on_sale_id)].image_count == 1

    # 판매완료 매물은 사진이 **한 글자도** 새지 않는다(FR11).
    assert by_id[str(sold_id)].image_path is None, "sold 매물의 사진 경로가 응답에 실렸다 (FR11 위반)"
    assert by_id[str(sold_id)].image_count == 0
    assert "secret" not in str([c.model_dump() for c in cards])
