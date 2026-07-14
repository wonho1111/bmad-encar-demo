"""AC-DB-1 — 트랜잭션 롤 격리: 커넥션 풀 재사용 시 ai_readonly 롤이 누수되지 않음을 증명한다.

라이브 DB 검증이라 DATABASE_URL이 없으면 skip(거짓 통과 금지).
DB 차원 보장은 Supabase MCP로도 별도 검증함(스토리 Completion Notes 참조).

`test_role_does_not_leak_across_reused_connection`이 실제로 잡는 것(코드리뷰 정정):
  현재의 풀 구조를 유지한 채 `SET LOCAL ROLE` → 세션 `SET ROLE`로 바뀌는 회귀 → **red**.
  같은 물리 커넥션(max_size=1)을 두 번 대여해, 첫 요청의 롤이 두 번째로 새는지 보기 때문이다.
  이게 현실적인 회귀 클래스다(풀은 그대로 두고 롤 설정 방식만 잘못 건드리는 경우).
⚠️ 잡지 못하는 것: 풀 자체를 버리고 `psycopg.connect()`로 매번 새 커넥션을 여는 옛 구현으로
  되돌아가는 경우. 그 구현은 모듈 싱글턴 `_pool`을 읽지 않으므로 아래 fixture의 monkeypatch가
  무력해지고, 검사 대상 커넥션이 run_select와 무관해져 **초록으로 통과한다.**
  (이 파일은 "풀 위에서 롤이 새지 않는가"를 지키지, "풀을 쓰고 있는가"를 지키지는 않는다.)
"""

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from app.config import settings
from app.db import readonly

pytestmark = pytest.mark.skipif(
    not settings.database_url,
    reason="DATABASE_URL 미설정 — 읽기전용 라이브 검증은 사용자 .env 입력 후 수행",
)


@pytest.fixture
def single_connection_pool(monkeypatch):
    """물리 커넥션 1개로 고정된 풀 — 두 번의 대여가 반드시 같은 커넥션임을 보장한다.

    readonly.py의 모듈 싱글턴(_pool)을 이 풀로 교체해 run_select가 이 풀을 쓰게 만든다.
    """
    pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=1,
        open=True,
        kwargs={"connect_timeout": 10, "prepare_threshold": None},
    )
    monkeypatch.setattr(readonly, "_pool", pool)
    yield pool
    pool.close()


def test_select_ok_and_write_blocked(single_connection_pool):
    # SELECT는 통과하고 행이 실제로 보여야 한다(ai_readonly permissive 정책).
    # ⚠️ '>= 0'이 아니라 '> 0'으로 단언: 읽기전용 롤이 RLS에 안 걸려 조용히 0건만
    #    반환하는 '결정적 함정'을 이 테스트가 직접 잡게 한다.
    rows = readonly.run_select("select count(*) from public.listings")
    assert rows[0][0] > 0

    # INSERT는 권한 부족으로 거부(NFR2) — SET LOCAL 트랜잭션 안에서도 쓰기는 여전히 막힌다.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        readonly.run_select(
            "insert into public.listings "
            "(seller_id, manufacturer, model, body_type, year, price, mileage, "
            " color, fuel, transmission, displacement, seats, region) "
            "values (gen_random_uuid(),'현대','x','SUV',2020,1,1,"
            "'흰색','가솔린','자동',1000,5,'서울')"
        )


def test_role_does_not_leak_across_reused_connection(single_connection_pool):
    """AC-DB-1 핵심 — 요청1(ai_readonly로 조회) 이후, 같은 물리 커넥션을 재사용하는
    요청2가 SET LOCAL 없이도 ai_readonly가 아닌 원래 롤로 시작하는지 확인한다.
    """
    # 요청1 — 정상적인 run_select 경로(SET LOCAL ROLE ai_readonly 안에서 실행 후 COMMIT).
    readonly.run_select("select 1")

    # 요청2 — 같은 풀(크기 1)에서 커넥션을 재대여해, SET LOCAL을 거치지 않고
    #   새 트랜잭션이 어떤 롤로 시작하는지 직접 확인한다.
    with single_connection_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select current_user")
            leaked_role = cur.fetchone()[0]

    assert leaked_role != readonly.READONLY_ROLE, (
        f"롤 누수 발견: 2번째 요청이 원래 롤 대신 이전 트랜잭션의 "
        f"{readonly.READONLY_ROLE!r}을 그대로 물려받았다(세션 SET ROLE 회귀 — AC-DB-1 위반)."
    )
