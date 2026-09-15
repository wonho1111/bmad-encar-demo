"""market_price._train_rows_query가 실DB에서 "대상과 가까운 순"으로 학습표를 뽑는지 확인
(DW-859 — 시세 엔진 3단계 Change A 검증).

tests/test_market_price.py의 test_train_rows_query_orders_by_similarity_with_expected_param_order는
SQL 문자열·파라미터 순서만 리터럴로 고정한 DB 없는 단위 테스트다 — 여기서는 그 SQL이 실제
Postgres에서 문법적으로도 돌고, 원하는 순서(동일 세대→연료→연식차→주행거리차)로도 나오는지를
실DB로 확인한다. tests/integration/conftest.py의 TEST_DATABASE_URL 스킵 가드·_create_user·
rollback 관례를 그대로 따른다(conftest.py 상단 docstring 참조).

로컬 시드 DB에는 이미 "그랜저" 매물이 있을 수 있어(v3 보정표 등), 반환 목록의 절대 위치(0번째·
1번째...)로 단언하지 않는다 — 이 테스트가 넣은 6건(대상 포함)의 상대 순서만 확인한다. 그래도
정렬 안전성은 잃지 않는다: 1순위 정렬키 `(model = 대상모델)`이 True/False로 전체를 완전히
양분하므로(동석 재실행되지 않는 한) "동일 세대 두 건이 항상 다른 세대 세 건보다 앞선다"는
다른 매물이 섞여 있어도 깨지지 않는다(자세한 논증은 아래 각 assert 옆 주석 참조).
"""

import uuid

import psycopg
from psycopg.rows import dict_row

from app import market_price
from conftest import _DSN, _create_user, pytestmark  # noqa: F401


def _insert_car(cur, listing_id, seller_id, model, year, mileage):
    """conftest._insert_listing과 같은 고정값(현대·중형차·1998cc·흰색·가솔린·자동·5인승·서울)에서
    model·year·mileage만 바꿔 넣는다 — 이 테스트가 보는 건 그 세 값과 model 문자열뿐이다."""
    cur.execute(
        "insert into public.listings "
        "(id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
        "color, fuel, transmission, displacement, seats, region) values "
        "(%s, %s, 'on_sale', '현대', %s, '중형차', %s, 26700000, %s, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id, model, year, mileage),
    )


def test_train_rows_query_orders_gn7_before_ig_and_by_year_then_mileage_distance():
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as cur:
            seller_id = _create_user(
                cur, f"dw859-train-rows-{uuid.uuid4().hex[:8]}@test.com", role="seller"
            )

            target_id = uuid.uuid4()
            gn7_2023_id = uuid.uuid4()
            gn7_2025_id = uuid.uuid4()
            ig_ids = {2021: uuid.uuid4(), 2022: uuid.uuid4(), 2023: uuid.uuid4()}

            # 대상: 그랜저 GN7 2024, 주행 20,000km.
            _insert_car(cur, target_id, seller_id, "그랜저 GN7", 2024, 20_000)
            # 같은 세대(GN7) — 연식차는 둘 다 1년으로 같아(|2023-2024|=|2025-2024|=1),
            # 주행거리차(|25000-20000|=5000 vs |10000-20000|=10000)로 순위가 갈린다.
            _insert_car(cur, gn7_2023_id, seller_id, "그랜저 GN7", 2023, 25_000)
            _insert_car(cur, gn7_2025_id, seller_id, "그랜저 GN7", 2025, 10_000)
            # 다른 세대(더 뉴 그랜저 IG) — model 완전 일치가 아니므로 세대가 갈린다. 연식차는
            # 서로 달라(1/2/3년) 그 순서로 갈린다.
            for year, mileage in ((2021, 60_000), (2022, 45_000), (2023, 30_000)):
                _insert_car(cur, ig_ids[year], seller_id, "더 뉴 그랜저 IG", year, mileage)

        target = {
            "id": target_id,
            "model": "그랜저 GN7",
            "transmission": "자동",
            "year": 2024,
            "mileage": 20_000,
            "fuel": "가솔린",
        }
        sql, params = market_price._train_rows_query(target, "그랜저")

        with conn.cursor(row_factory=dict_row) as cur2:
            cur2.execute(sql, params)
            rows = cur2.fetchall()

        idx = {row["id"]: i for i, row in enumerate(rows)}

        assert target_id not in idx, "대상 자신(id <> %s)은 학습표에서 빠져야 한다"
        assert gn7_2023_id in idx and gn7_2025_id in idx
        assert all(y in idx for y in ig_ids.values())

        # 1순위 정렬키 (model = %s)가 True/False로 행 전체를 완전히 양분하므로(같은 순위 안의
        # 하위 기준과 무관하게), 로컬 DB에 다른 "그랜저" 매물이 섞여 있어도 "동일 세대(GN7) 두
        # 건은 항상 다른 세대(IG) 세 건보다 앞선다"는 관계 자체는 흔들리지 않는다.
        assert max(idx[gn7_2023_id], idx[gn7_2025_id]) < min(idx[y] for y in ig_ids.values())

        # GN7 두 건은 연식차가 같으므로(3순위 동률) 4순위 주행거리차가 더 작은 2023이 먼저 온다.
        assert idx[gn7_2023_id] < idx[gn7_2025_id]

        # IG 세 건은 연식차가 서로 달라(3순위로 갈림) 2023(차 1) → 2022(차 2) → 2021(차 3) 순.
        assert idx[ig_ids[2023]] < idx[ig_ids[2022]] < idx[ig_ids[2021]]

        conn.rollback()
