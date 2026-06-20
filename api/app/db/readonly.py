"""읽기전용 DB 접근 — AI 경로는 SELECT만 가능한 ai_readonly 롤로 DB에 닿는다(NFR2, AC2).

동작: DATABASE_URL(Session pooler)로 연결 → 즉시 `SET ROLE ai_readonly` →
      이후 모든 쿼리는 읽기전용 권한으로 실행된다. INSERT/UPDATE/DELETE는 Postgres가 거부한다.

⚠️ FR11(판매완료 sold 비노출)은 RLS가 아니라 **호출부 쿼리가 책임진다.**
   ai_readonly 롤에는 listings를 모두 보는 permissive 정책(using true)이 걸려 있으므로,
   AI 검색 쿼리(4.3+)는 반드시 WHERE status = 'on_sale' 을 직접 넣어 sold를 거른다.

연결 방식: Session pooler(:5432)를 쓴다. SET ROLE이 세션에 유지되어야 하므로
   Transaction pooler(:6543)는 사용하지 않는다(스토리 Dev Notes 참조).
"""

import contextlib

import psycopg

from ..config import require, settings

READONLY_ROLE = "ai_readonly"


@contextlib.contextmanager
def readonly_connection():
    """ai_readonly 롤로 전환된 psycopg 연결을 제공하는 컨텍스트 매니저."""
    dsn = require("DATABASE_URL", settings.database_url)
    # autocommit=True: SET ROLE이 트랜잭션이 아닌 세션 수준으로 유지되게 한다.
    conn = psycopg.connect(dsn, autocommit=True)
    try:
        with conn.cursor() as cur:
            # 식별자는 고정 상수(ai_readonly)라 인젝션 위험 없음.
            cur.execute(f"SET ROLE {READONLY_ROLE}")
        yield conn
    finally:
        conn.close()


def run_select(query: str, params: tuple | None = None) -> list[tuple]:
    """읽기전용 롤로 SELECT 실행 후 결과 행들을 반환."""
    with readonly_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
