"""AC2 — 읽기전용 롤: SELECT 성공 + 쓰기 차단.

라이브 DB 검증이라 DATABASE_URL이 없으면 skip(거짓 통과 금지).
DB 차원 보장은 Supabase MCP로도 별도 검증함(스토리 Completion Notes 참조).
"""

import psycopg
import pytest

from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.database_url,
    reason="DATABASE_URL 미설정 — 읽기전용 라이브 검증은 사용자 .env 입력 후 수행",
)


def test_select_ok_and_write_blocked():
    from app.db.readonly import readonly_connection

    with readonly_connection() as conn:
        # SELECT는 통과(행이 보인다 — ai_readonly permissive 정책).
        with conn.cursor() as cur:
            cur.execute("select count(*) from public.listings")
            assert cur.fetchone()[0] >= 0

        # INSERT는 권한 부족으로 거부(NFR2).
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(
                    "insert into public.listings "
                    "(seller_id, manufacturer, model, body_type, year, price, mileage, "
                    " color, fuel, transmission, displacement, seats, region) "
                    "values (gen_random_uuid(),'현대','x','SUV',2020,1,1,"
                    "'흰색','가솔린','자동',1000,5,'서울')"
                )
