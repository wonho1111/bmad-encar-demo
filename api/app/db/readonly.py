"""읽기전용 DB 접근 — AI 경로는 SELECT만 가능한 ai_readonly 롤로 DB에 닿는다(NFR2, AC-DB-1).

동작: 지연 초기화된 psycopg 커넥션 풀(트랜잭션 풀러 :6543)에서 커넥션을 대여 →
      매 쿼리를 `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;` 으로 감싸 실행한다.

⚠️ 왜 :6543 + SET LOCAL 인가(AC-DB-1): 커넥션 풀은 물리 커넥션을 여러 요청이 재사용한다.
   세션 레벨 `SET ROLE`(과거 방식)은 그 세션이 살아있는 동안 계속 유지되므로, 커넥션이
   풀로 반납돼 다음 요청에 재사용되면 ai_readonly 롤이 그 요청으로 그대로 **누수**된다.
   `SET LOCAL ROLE`은 트랜잭션 스코프에만 적용돼 COMMIT/ROLLBACK 시 자동 원복되므로,
   커넥션이 풀에 반납될 때는 항상 깨끗한 상태다. 그래서 세션 풀러(:5432)가 아니라
   트랜잭션 풀러(:6543)를 쓰고, 세션 SET ROLE은 절대 쓰지 않는다.

⚠️ FR11(판매완료 sold 비노출)은 RLS가 아니라 **호출부 쿼리가 책임진다.**
   ai_readonly 롤에는 listings를 모두 보는 permissive 정책(using true)이 걸려 있으므로,
   AI 검색 쿼리(4.3+)는 반드시 WHERE status = 'on_sale' 을 직접 넣어 sold를 거른다.

풀은 모듈 import 시점에 열지 않는다(config.py 설계: 비밀값 없이도 /health가 떠야 함).
최초 run_select 호출 때 지연 생성되는 싱글턴이다.
"""

import contextlib
import logging
import threading

from psycopg_pool import ConnectionPool

from ..config import require, settings

logger = logging.getLogger(__name__)

READONLY_ROLE = "ai_readonly"

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()

# 풀 생성 시 "실제로 연결이 되는지" 확인하며 기다릴 시간(초).
# 이 시간을 넘기면 풀을 캐시하지 않고 폐기한다 — 아래 _get_pool 주석 참조.
_POOL_OPEN_TIMEOUT = 10


def _get_pool() -> ConnectionPool:
    """지연 초기화된 커넥션 풀을 반환한다. 최초 호출 시 1회만 생성해 캐시한다.

    asyncio.to_thread로 여러 요청이 동시에 첫 호출을 할 수 있으므로(AC-DB-1 코드리뷰
    패치), 락으로 감싸 풀이 중복 생성되지 않게 한다(더블체크락).

    ⚠️ 생성 직후 wait()로 연결을 검증하고, 실패하면 풀을 버리고 예외를 올린다(코드리뷰 패치).
       왜: ConnectionPool(open=True)는 커넥션을 백그라운드로 열기 때문에 **DSN이 틀렸거나
       DB가 죽어 있어도 생성자는 그냥 성공한다.** 그대로 캐시하면 그 뒤 모든 요청이 대여
       타임아웃(PoolTimeout)을 맞고, 라우터는 그걸 "사용자가 많아 풀이 고갈됐다"로 오진해
       응답한다(사실은 아무도 없음). 진짜 원인은 어디에도 안 뜨고, DB를 고쳐도 죽은 풀이
       영구 캐시돼 프로세스를 재시작해야 살아난다. wait()가 그 두 상황을 여기서 갈라준다 —
       연결 불가는 생성 시점에 진짜 원인과 함께 터지고, `_pool`은 None으로 남아 다음 요청이
       다시 시도한다.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # 락을 기다리는 동안 다른 스레드가 이미 만들었을 수 있음
                dsn = require("DATABASE_URL", settings.database_url)
                pool = ConnectionPool(
                    dsn,
                    min_size=1,
                    max_size=8,
                    # 풀이 꽉 찼을 때 커넥션 대여 대기 시간(기본 30초는 너무 길어
                    # 사용자를 오래 붙잡는다 — 코드리뷰 패치, FR50 "부하 상황에서도 안정적").
                    timeout=5,
                    open=True,
                    # 대여 전 커넥션이 살아있는지 확인한다(코드리뷰 패치).
                    # 왜: min_size=1이라 트래픽이 없으면 커넥션 1개가 무기한 유휴로 남는데
                    # (max_idle은 min_size 초과분만 회수한다), 그 사이 풀러가 유휴 커넥션을
                    # 끊으면 다음 요청의 첫 문장이 OperationalError로 터진다(PoolTimeout이
                    # 아니라 catch-all 500). check가 죽은 커넥션을 조용히 교체해준다.
                    check=ConnectionPool.check_connection,
                    kwargs={
                        "connect_timeout": 10,
                        # 트랜잭션 풀러(:6543)는 커넥션을 트랜잭션 단위로 갈아끼우므로
                        # 서버측 준비문(prepared statement)이 깨질 수 있다 — 비활성화.
                        "prepare_threshold": None,
                    },
                )
                try:
                    pool.wait(timeout=_POOL_OPEN_TIMEOUT)
                except Exception:
                    # 연결 자체가 안 되는 풀은 캐시하지 않는다 — 캐시하면 위 docstring의
                    # "죽은 풀 영구 캐시 + 부하로 오진" 상태가 된다. 진짜 원인을 로그에 남기고
                    # 그대로 올려보낸다(라우터의 catch-all이 500으로 감싼다 — PoolTimeout이
                    # 아니므로 "사용자가 많아요" 오안내가 나가지 않는다).
                    logger.exception("DB 커넥션 풀 초기화 실패 — DATABASE_URL·DB 상태를 확인하세요")
                    pool.close()
                    raise
                _pool = pool
    return _pool


def close_pool() -> None:
    """커넥션 풀을 닫는다(앱 종료 훅에서 호출 — main.py lifespan).

    왜 필요한가: 풀은 모듈 싱글턴이라 아무도 닫아주지 않으면, SIGTERM(Cloud Run 스케일다운·
    매 재배포)마다 최대 8개의 서버측 세션과 풀 워커 스레드가 정리되지 않은 채 프로세스가
    사라진다. 롤링 배포가 반복되면 고아 세션이 쌓여 Supabase 커넥션 상한을 밀어붙인다 —
    풀을 도입해 막으려던 바로 그 실패 모드다(코드리뷰 패치).
    """
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


@contextlib.contextmanager
def readonly_connection():
    """트랜잭션 안에서 ai_readonly 롤로 전환된 풀 커넥션을 제공하는 컨텍스트 매니저.

    커넥션은 풀에서 대여되고, 컨텍스트 종료 시 풀로 반납된다(닫히지 않음).
    `SET LOCAL ROLE`은 with-block 안에서 열린 트랜잭션 스코프에만 적용된다 —
    이 컨텍스트를 벗어나 트랜잭션이 커밋/롤백되면 롤은 자동 원복된다.
    """
    pool = _get_pool()
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                # 식별자는 고정 상수(ai_readonly)라 인젝션 위험 없음.
                cur.execute(f"SET LOCAL ROLE {READONLY_ROLE}")
            yield conn


def run_select(query: str, params: tuple | None = None) -> list[tuple]:
    """읽기전용 롤로 SELECT 실행 후 결과 행들을 반환한다.

    BEGIN(트랜잭션 시작) → SET LOCAL ROLE ai_readonly → SELECT → COMMIT(롤 자동 원복)
    → 커넥션 풀 반납. 공개 시그니처는 변경하지 않는다(sql_rag_node·doc_rag_node 등
    다수 호출부·테스트가 이 시그니처에 의존).
    """
    with readonly_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
