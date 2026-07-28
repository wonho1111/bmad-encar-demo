"""chat_messages 멱등키 실DB 검증 — 0022의 스키마·제약이 실제로 동작하는가 (Story 12.1, AC-CHAT-1).

왜 이 파일이 따로 있나:
  0022가 `client_message_id uuid` 컬럼과 `UNIQUE(room_id, client_message_id)` 제약을 SQL로
  추가하는 것과, 그 제약이 실제 INSERT 시나리오에서 기대대로 동작하는 것은 다른 사실이다
  (CLAUDE.md B4 "존재 확인은 작동 확인이 아니다"). 특히 이 스토리는 기존 chat_messages 제약
  2개(0003 빈 본문 CHECK·0010 2000자 CHECK)와 chat_rooms의 seller_id 강제 트리거(0016)가
  이 변경 후에도 그대로 동작함을 요구한다(스펙 Always 절) — 이 파일이 그것들을 실제 INSERT로
  함께 확인한다(`test_view_count_rpc_real_db.py`와 같은 이유, 같은 방식).

무엇을 증명하나 (스펙 I/O 매트릭스 4행 + AC-CHAT-1):
  ① 같은 (room_id, client_message_id) 쌍으로 `ON CONFLICT (room_id, client_message_id) DO
     NOTHING`을 써서 2회 INSERT하면 그 쌍에 해당하는 행이 정확히 1개다(AC-CHAT-1).
  ② 같은 client_message_id라도 room_id가 다르면 유니크 범위가 방 단위라 두 행 모두 존재한다.
  ③ client_message_id를 지정하지 않은(NULL) 여러 건은 서로 충돌 없이 전부 성공한다(Postgres
     UNIQUE가 NULL을 서로 다른 값으로 취급).
  ④ 0016 트리거로 seller_id가 매물 소유자로 강제된 방에 client_message_id를 실은 메시지를
     넣어도 트리거의 강제 동작·CHECK(buyer_id<>seller_id)가 회귀 없이 그대로 동작한다.
  ⑤ 0010의 2000자 CHECK는 client_message_id 유무와 무관하게 여전히 초과 본문을 거부한다.
  ⑥ 0003의 빈 본문 CHECK도 함께 회귀 없다.
  ⑦ 마이그레이션 이전부터 있던 것처럼 client_message_id 없이 넣은 기존 행은 컬럼이 NULL로
     읽힌다(I13, additive) — 새 컬럼이 기존 행에 영향을 주지 않음을 확인.
  ⑧ 컬럼·제약이 **기대한 모양 그대로** 존재한다(제약 정의 문자열을 직접 대조) — AC 1행. ①②는
     제약이 없으면 42P10으로 실패하므로 간접 증거이긴 하나, 제약의 **이름**까지는 안 잡는다.
     0022의 멱등 가드가 바로 그 이름을 키로 쓰므로 이름이 바뀌면 재적용이 조용히 중복 제약을
     만든다 — 그래서 이름·정의를 직접 단언한다.
  ⑨ `ON CONFLICT` 없이 같은 쌍을 두 번 넣으면 제약이 **실제로 거부한다**(23505). ①은 회피
     문법(DO NOTHING)만 확인하므로, 제약 자체가 무는지는 이 테스트가 본다 — 현재 앱 코드
     (`web/src/lib/messages.ts`)는 아직 평범한 INSERT라 이쪽이 지금 도달 가능한 경로다.
  ⑩ **커밋 경계를 넘는** 재전송(첫 요청이 커밋된 뒤 두 번째 요청)도 행 1개로 수렴한다.
     ①은 한 트랜잭션 안 두 문장이라 Postgres의 speculative insertion 경로만 타는데, 스펙이
     말하는 "네트워크가 끊긴 채 재전송"은 별개 요청·별개 트랜잭션이다 — 그 경로를 따로 탄다.
  ⑪ client_message_id가 NULL이면 `ON CONFLICT DO NOTHING`이 중복을 **못 막는다**(2행 그대로
     남는다). 알려진 한계를 산문이 아니라 검사로 고정한다(B4) — Story 12.3 이전 구간과
     구버전 클라이언트가 이 상태다.
  ⑫ 정확히 2000자 본문은 **허용된다**. ⑤는 초과(2001자)만 보므로 상한을 더 조이는 방향의
     회귀(예: `< 2000`)는 못 잡는다 — 경계 양쪽을 다 고정한다.
  ⑬ `authenticated` 롤로도 새 컬럼을 쓰고 읽을 수 있다. 스펙 Always 절의 "새 컬럼은 기존
     chat_messages 정책이 그대로 덮는다"는 **소유자 권한이 아니라 authenticated 표면**에 대한
     주장이라, 그 표면에서 한 번은 실행해봐야 확인된다. `listings`가 0011에서 테이블 GRANT를
     회수하고 컬럼별로 다시 준 탓에 0021이 새 컬럼 GRANT를 따로 줘야 했던 전례가 있다
     (`docs/conventions.md` §4.1, 대장 #109) — chat_messages는 그런 상태가 아님을 여기서 고정한다.
  ⑭ 0016 트리거가 **매물과 무관한 제3자** seller_id도 실소유자로 덮는다(위조 차단 본래 목적).
     ④와 `seeded` 픽스처는 `bogus_seller_id = buyer_id`만 넣어서, 트리거가 "자기충돌만 고치는"
     형태로 퇴화해도 통과한다 — 그 사각을 이 테스트가 닫는다.

무엇을 못 보나: 클라이언트(web·app)가 client_message_id를 실제로 생성해 실어 보내는지, 앱
  코드가 `ON CONFLICT DO NOTHING` SQL을 실제로 쓰는지는 Story 12.3 범위이고 여기서 보지 않는다.
  이 파일은 DB 계층(컬럼·제약·기존 트리거·CHECK와의 상호작용)만 본다. 접속은 `psycopg`로
  **DSN 소유자(postgres) 권한**이라 ⑬ 한 건을 빼면 RLS·컬럼 GRANT가 전부 우회된다 — ⑬만
  `set local role authenticated` + `request.jwt.claim.sub`로 롤을 흉내낸다. 어느 쪽이든
  PostgREST/supabase-js를 통과하는 실제 프로덕션 경로(요청 헤더·에러 코드·반환 모양)는 여기서
  검증되지 않는다(형제 `test_view_count_rpc_real_db.py`와 동일한 알려진 한계, 대장 #133).

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import os
import uuid

import psycopg
import pytest

_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DSN, reason="TEST_DATABASE_URL 미설정 — 실DB 통합 검증은 CI의 api-db 잡에서 돈다"
)

_CHECK_VIOLATION = "23514"
_UNIQUE_VIOLATION = "23505"
_UNIQUE_CONSTRAINT_NAME = "chat_messages_room_client_message_unique"

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)


def _create_user(cur, email, role="buyer"):
    user_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, jsonb_build_object('role', %s::text))",
        (user_id, email, role),
    )
    # 0001의 가입 트리거가 profiles 행을 만든다 — listings/chat_rooms FK가 이를 요구한다.
    # role까지 대조하는 이유: 이 인자를 받아만 두고 확인하지 않으면 "판매자를 만들었다"가
    # 검사되지 않는 주장으로 남는다. 트리거가 raw_user_meta_data->>'role' 읽기를 멈추면
    # 여기서 잡힌다(B4 — 만드는 것이 아니라 잡는 것이 완료다).
    cur.execute("select role from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    assert row[0] == role, f"가입 트리거가 role 메타데이터를 반영하지 않았다({row[0]} != {role})"
    return user_id


def _insert_listing(cur, listing_id, seller_id):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id),
    )


def _insert_chat_room(cur, listing_id, buyer_id, bogus_seller_id):
    """0016 트리거가 seller_id를 매물의 실제 소유자로 강제 덮어쓴다 — 여기 넣는
    bogus_seller_id는 일부러 실제 소유자가 아닌 값을 줘서 트리거가 그것을 무시하고
    실제 소유자로 바꿔치기하는지까지 함께 확인한다(회귀 없음, 스펙 Always 절)."""
    room_id = uuid.uuid4()
    cur.execute(
        "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) "
        "values (%s, %s, %s, %s)",
        (room_id, listing_id, buyer_id, bogus_seller_id),
    )
    return room_id


@pytest.fixture
def seeded():
    """구매자 1명 + 판매자 1명 + 매물 1건 + 채팅방 1개. 끝나면 **롤백**해 원상복구한다
    (다른 실DB 테스트와 동일 패턴)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = _create_user(c, f"ci-seller-{uuid.uuid4()}@example.com", role="seller")
            buyer_id = _create_user(c, f"ci-buyer-{uuid.uuid4()}@example.com")
            listing_id = uuid.uuid4()
            _insert_listing(c, listing_id, seller_id)
            # bogus_seller_id로 buyer_id 자신을 줘본다 — 트리거가 이걸 무시하고 실제
            # 소유자(seller_id)로 강제해야 CHECK(buyer_id<>seller_id)도 통과한다.
            room_id = _insert_chat_room(c, listing_id, buyer_id, buyer_id)
            # 트리거가 seller_id를 실제로 강제했는지 먼저 확인 — 여기서 어긋나면 아래
            # 메시지 테스트들의 전제 자체가 무너진다.
            c.execute("select seller_id from public.chat_rooms where id = %s", (room_id,))
            assert c.fetchone()[0] == seller_id, "0016 트리거가 seller_id를 매물 소유자로 강제하지 않았다(회귀)"
            yield c, room_id, buyer_id, seller_id, listing_id
        conn.rollback()


@pytest.fixture
def seeded_committed():
    """`seeded`와 같은 시드지만 **커밋**하며 진행한다(autocommit).

    왜 따로 필요한가: 롤백 픽스처 안의 두 INSERT는 같은 트랜잭션이라 Postgres의 speculative
    insertion(자기 자신과의 충돌) 경로를 탄다. 스펙이 말하는 재전송은 **첫 요청이 커밋된 뒤
    도착하는 별개 요청**이라 커밋된 인덱스 항목과 충돌하는 다른 경로다 — 그 경로는 커밋 없이
    만들 수 없다(형제 `test_view_count_rpc_real_db.py`의 `seeded_committed`가 같은 이유로 있다).

    끝나면 `auth.users` 2행을 지운다 — profiles→listings→chat_rooms→chat_messages가 전부
    on delete cascade라 이 한 번으로 정리된다(실측 확인). 이메일은 실행마다 uuid로 유일하게
    만든다 — 하드코딩하면 프로세스가 도중에 죽었을 때 커밋된 행이 남아 이후 실행이 전부 red가
    된다(형제 파일이 코드리뷰에서 지적받은 자리).
    """
    conn = psycopg.connect(_DSN, autocommit=True)
    try:
        with conn.cursor() as c:
            seller_id = buyer_id = None
            try:
                seller_id = _create_user(
                    c, f"ci-seller-committed-{uuid.uuid4()}@example.com", role="seller"
                )
                buyer_id = _create_user(c, f"ci-buyer-committed-{uuid.uuid4()}@example.com")
                listing_id = uuid.uuid4()
                _insert_listing(c, listing_id, seller_id)
                room_id = _insert_chat_room(c, listing_id, buyer_id, buyer_id)
                yield c, room_id, buyer_id
            finally:
                for uid in (buyer_id, seller_id):
                    if uid is not None:
                        c.execute("delete from auth.users where id = %s", (uid,))
    finally:
        conn.close()


def _message_count(cur, room_id, client_message_id):
    # `= %s`는 client_message_id가 NULL이면 항상 unknown이라 0을 돌려준다(SQL 3값 논리) —
    # NULL 케이스도 안전하게 세도록 IS NOT DISTINCT FROM을 쓴다(=의 NULL-safe 버전).
    cur.execute(
        "select count(*) from public.chat_messages "
        "where room_id = %s and client_message_id is not distinct from %s",
        (room_id, client_message_id),
    )
    return cur.fetchone()[0]


def _insert_message_on_conflict_do_nothing(cur, room_id, sender_id, body, client_message_id):
    """스펙이 명시한 앱 코드 패턴(Story 12.3 몫)을 그대로 재현해 제약이 실제로 그 문장과
    맞물려 동작하는지 확인한다."""
    cur.execute(
        "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
        "values (%s, %s, %s, %s) "
        "on conflict (room_id, client_message_id) do nothing",
        (room_id, sender_id, body, client_message_id),
    )


def test_duplicate_resend_same_room_and_client_id_converges_to_one_row(seeded):
    """① AC-CHAT-1 — 같은 (room_id, client_message_id)로 2회 INSERT(ON CONFLICT DO NOTHING)
    해도 행이 정확히 1개만 존재하고 에러가 나지 않는다.

    두 본문을 **다르게** 넣는다: 같은 본문이면 `DO NOTHING`이 `DO UPDATE`(나중 것이 먼저 것을
    덮어씀)로 바뀌어도 개수가 1이라 통과해버린다. 살아남은 행이 **첫 번째** 본문인지까지 봐야
    "무시했다"와 "덮어썼다"가 구별된다. 방 전체 개수도 함께 세어(키로 거르지 않고) 다른 키나
    NULL 키로 새는 행이 없음 — AC-CHAT-1의 "부작용 0" — 을 확인한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded
    client_message_id = uuid.uuid4()

    with cur.connection.transaction():
        _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "원본 메시지", client_message_id)
        _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "재전송 메시지", client_message_id)

    assert _message_count(cur, room_id, client_message_id) == 1

    cur.execute(
        "select body from public.chat_messages where room_id = %s and client_message_id = %s",
        (room_id, client_message_id),
    )
    assert cur.fetchone()[0] == "원본 메시지", "DO NOTHING이 아니라 덮어쓰기(DO UPDATE)로 동작했다"

    cur.execute("select count(*) from public.chat_messages where room_id = %s", (room_id,))
    assert cur.fetchone()[0] == 1, "재전송이 다른 키/NULL 키로 새어 방에 여분 행이 생겼다"


def test_duplicate_resend_across_committed_transactions_converges_to_one_row(seeded_committed):
    """⑩ AC-CHAT-1을 **커밋 경계 너머**에서 — 첫 INSERT가 커밋된 뒤 별개 요청처럼 두 번째가
    도착해도 행이 1개다. ①이 타는 speculative insertion 경로와 다른, 실제 재전송 경로다."""
    cur, room_id, buyer_id = seeded_committed
    client_message_id = uuid.uuid4()

    _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "원본 메시지", client_message_id)
    # autocommit 커넥션이라 이 시점에 첫 행은 이미 커밋됐다 — 아래는 커밋된 인덱스 항목과의 충돌.
    _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "재전송 메시지", client_message_id)

    assert _message_count(cur, room_id, client_message_id) == 1
    cur.execute(
        "select body from public.chat_messages where room_id = %s and client_message_id = %s",
        (room_id, client_message_id),
    )
    assert cur.fetchone()[0] == "원본 메시지"

    # ①과 같은 "부작용 0" 단언을 여기에도 둔다 — 스펙이 말하는 실제 재전송 경로는 ①이 아니라
    # 이쪽인데, 키로 거른 개수만 보면 다른 키나 NULL 키로 새는 행을 못 잡는다.
    cur.execute("select count(*) from public.chat_messages where room_id = %s", (room_id,))
    assert cur.fetchone()[0] == 1, "커밋 경계 재전송이 다른 키/NULL 키로 새어 방에 여분 행이 생겼다"


def test_plain_duplicate_insert_is_rejected_by_the_constraint(seeded):
    """⑨ 제약 **자체**가 무는지 — `ON CONFLICT` 회피 문법 없이 같은 쌍을 두 번 넣으면
    유니크 위반(23505)으로 거부된다. ①②는 회피 문법을 쓰므로 이걸 증명하지 못한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded
    client_message_id = uuid.uuid4()

    with cur.connection.transaction():
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
            "values (%s, %s, %s, %s)",
            (room_id, buyer_id, "첫 전송", client_message_id),
        )

    with pytest.raises(psycopg.errors.UniqueViolation) as exc:
        with cur.connection.transaction():
            cur.execute(
                "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
                "values (%s, %s, %s, %s)",
                (room_id, buyer_id, "중복 전송", client_message_id),
            )
    assert exc.value.sqlstate == _UNIQUE_VIOLATION


def test_column_and_constraint_exist_with_expected_shape(seeded):
    """⑧ AC 1행 — 컬럼이 nullable uuid로, 제약이 정확한 **이름과 컬럼 조합**으로 존재한다.
    이름을 단언하는 이유: 0022의 재적용 멱등 가드가 `conname`을 키로 쓰므로, 이름이 달라지면
    가드가 못 알아보고 같은 제약을 하나 더 만든다."""
    cur, _room_id, _buyer_id, _seller_id, _listing_id = seeded

    cur.execute(
        "select data_type, is_nullable, column_default from information_schema.columns "
        "where table_schema = 'public' and table_name = 'chat_messages' "
        "and column_name = 'client_message_id'"
    )
    column = cur.fetchone()
    assert column is not None, "client_message_id 컬럼이 없다"
    assert column[0] == "uuid"
    assert column[1] == "YES", "nullable이어야 한다(I13 additive)"
    assert column[2] is None, "기본값이 없어야 한다(스펙 Always 절)"

    cur.execute(
        "select pg_get_constraintdef(oid) from pg_constraint "
        "where conrelid = 'public.chat_messages'::regclass and conname = %s",
        (_UNIQUE_CONSTRAINT_NAME,),
    )
    constraint = cur.fetchone()
    assert constraint is not None, f"{_UNIQUE_CONSTRAINT_NAME} 제약이 없다"
    assert constraint[0] == "UNIQUE (room_id, client_message_id)"


def test_authenticated_role_can_write_and_read_client_message_id(seeded):
    """⑬ 스펙 Always 절("새 컬럼은 기존 chat_messages 정책이 그대로 덮는다")을 **authenticated
    표면에서** 실제로 확인한다 — 나머지 테스트는 DSN 소유자 권한이라 RLS·컬럼 GRANT를 우회한다.
    이게 없으면 나중에 chat_messages의 테이블 GRANT를 회수하고 컬럼별로 다시 주는 마이그가
    들어왔을 때(listings가 0011→0021에서 실제로 겪은 일) 새 컬럼만 조용히 빠져도 아무도 못 잡는다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded
    client_message_id = uuid.uuid4()

    with cur.connection.transaction():
        cur.execute(f"set local request.jwt.claim.sub = '{buyer_id}'")
        cur.execute("set local role authenticated")
        try:
            _insert_message_on_conflict_do_nothing(
                cur, room_id, buyer_id, "authenticated 롤이 보낸 메시지", client_message_id
            )
            cur.execute(
                "select client_message_id from public.chat_messages "
                "where room_id = %s and client_message_id = %s",
                (room_id, client_message_id),
            )
            row = cur.fetchone()
        finally:
            # 위에서 권한 오류가 나면 트랜잭션이 이미 중단(aborted)돼 reset role 자체가 실패한다 —
            # 그걸 그대로 두면 진짜 원인(권한 거부)이 2차 예외에 가려진다. 감싸는 세이브포인트
            # 롤백이 SET LOCAL ROLE도 함께 되돌리므로 무시해도 새는 것이 없다(형제 파일과 동일).
            try:
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass

    assert row is not None, "authenticated 롤이 방금 쓴 행을 자기가 다시 못 읽었다(RLS 또는 GRANT)"
    assert row[0] == client_message_id


def test_same_client_id_different_room_both_rows_exist(seeded):
    """② 유니크 범위는 방 단위 — 같은 client_message_id라도 room_id가 다르면 둘 다 존재한다."""
    cur, room_id, buyer_id, seller_id, listing_id = seeded

    # 두 번째 방: 같은 매물에 대해 다른 구매자가 문의(다른 buyer_id라 UNIQUE(listing_id,
    # buyer_id, seller_id) 제약과 충돌하지 않는다).
    other_buyer_id = _create_user(cur, f"ci-buyer2-{uuid.uuid4()}@example.com")
    other_room_id = _insert_chat_room(cur, listing_id, other_buyer_id, other_buyer_id)
    cur.execute("select seller_id from public.chat_rooms where id = %s", (other_room_id,))
    assert cur.fetchone()[0] == seller_id

    client_message_id = uuid.uuid4()
    with cur.connection.transaction():
        _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "방1 메시지", client_message_id)
    with cur.connection.transaction():
        _insert_message_on_conflict_do_nothing(
            cur, other_room_id, other_buyer_id, "방2 메시지", client_message_id
        )

    assert _message_count(cur, room_id, client_message_id) == 1
    assert _message_count(cur, other_room_id, client_message_id) == 1


def test_null_client_message_id_multiple_inserts_all_succeed(seeded):
    """③ client_message_id를 지정하지 않은(NULL) 여러 건은 서로 충돌 없이 전부 성공한다
    (Postgres UNIQUE는 NULL끼리 다른 값으로 취급 — Design Notes)."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    with cur.connection.transaction():
        for i in range(3):
            cur.execute(
                "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s)",
                (room_id, buyer_id, f"NULL 멱등키 메시지 {i}"),
            )

    cur.execute(
        "select count(*) from public.chat_messages where room_id = %s and client_message_id is null",
        (room_id,),
    )
    assert cur.fetchone()[0] == 3


def test_null_client_message_id_is_not_deduplicated_by_on_conflict(seeded):
    """⑪ 알려진 한계를 검사로 고정 — 키가 NULL이면 `ON CONFLICT DO NOTHING`을 써도 중복이
    막히지 않고 2행이 남는다(NULL은 서로 다른 값이라 arbiter가 절대 충돌하지 않는다).
    Story 12.3이 클라이언트에 키를 채우기 전까지, 그리고 키를 안 보내는 구버전 클라이언트가
    남아 있는 동안은 FR41의 중복 방지가 **작동하지 않는다** — 이 사실이 산문에만 있으면
    다음 스토리가 반대로 가정한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    with cur.connection.transaction():
        _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "키 없는 전송", None)
        _insert_message_on_conflict_do_nothing(cur, room_id, buyer_id, "키 없는 재전송", None)

    assert _message_count(cur, room_id, None) == 2


def test_existing_row_without_client_message_id_reads_null(seeded):
    """⑦ 마이그레이션 이전 행처럼 client_message_id 없이 넣은 행은 NULL로 읽힌다(I13,
    additive — 새 컬럼이 기존 행에 영향을 주지 않는다는 것을 직접 확인)."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    with cur.connection.transaction():
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s) "
            "returning id",
            (room_id, buyer_id, "마이그레이션 이전 스타일 메시지"),
        )
        (msg_id,) = cur.fetchone()

    cur.execute(
        "select client_message_id from public.chat_messages where id = %s", (msg_id,)
    )
    assert cur.fetchone()[0] is None


def test_body_over_2000_chars_still_rejected(seeded):
    """⑤ 회귀 방지 — 0010의 2000자 CHECK는 client_message_id 유무와 무관하게 여전히
    초과 본문을 거부한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded
    too_long_body = "가" * 2001

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with cur.connection.transaction():
            cur.execute(
                "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
                "values (%s, %s, %s, %s)",
                (room_id, buyer_id, too_long_body, uuid.uuid4()),
            )
    assert exc.value.sqlstate == _CHECK_VIOLATION


def test_body_exactly_2000_chars_still_accepted(seeded):
    """⑫ 경계의 반대쪽 — 0010의 CHECK는 `<= 2000`이므로 정확히 2000자는 통과해야 한다.
    ⑤(2001자 거부)만 있으면 상한을 더 조이는 회귀(예: `< 2000`)는 green으로 지나간다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded
    client_message_id = uuid.uuid4()

    with cur.connection.transaction():
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
            "values (%s, %s, %s, %s)",
            (room_id, buyer_id, "가" * 2000, client_message_id),
        )

    assert _message_count(cur, room_id, client_message_id) == 1


def test_blank_body_still_rejected(seeded):
    """⑥ 회귀 방지 — 0003의 빈 본문(공백만) CHECK도 client_message_id와 무관하게 여전히
    거부한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with cur.connection.transaction():
            cur.execute(
                "insert into public.chat_messages (room_id, sender_id, body, client_message_id) "
                "values (%s, %s, %s, %s)",
                (room_id, buyer_id, "   ", uuid.uuid4()),
            )
    assert exc.value.sqlstate == _CHECK_VIOLATION


def test_listing_owner_cannot_open_chat_room_on_own_listing(seeded):
    """④ 회귀 방지 — 0016 트리거가 강제한 seller_id는 `seeded`의 setup 단언(bogus_seller_id →
    실제 소유자로 치환됨)이 이미 매 테스트마다 실측한다(트리거를 지우면 그 단언이 먼저 깨져
    이 파일 전체가 red가 된다 — 트리거는 거기서 고정된다). 이 테스트는 그 짝으로, seller_id가
    buyer_id와 같아지는 입력에서 0003의 CHECK(buyer_id<>seller_id)가 이 스토리 이후에도 여전히
    거부하는지를 본다 — 다만 아래 INSERT는 buyer_id=seller_id=매물 소유자를 그대로 넣으므로
    트리거가 아예 안 돌아도 이 CHECK 하나만으로 거부된다(트리거 자체의 단독 회귀 증거는 아니고,
    트리거+CHECK 조합이 여전히 매물주 본인 문의를 막는다는 시스템 레벨 확인이다)."""
    cur, _room_id, _buyer_id, seller_id, listing_id = seeded

    # 매물 소유자(seller_id) 본인이 자기 매물에 문의 — 트리거가 seller_id를 소유자로(그대로)
    # 강제하고, buyer_id == seller_id이므로 CHECK(buyer_id<>seller_id)가 거부해야 한다.
    with pytest.raises(psycopg.errors.CheckViolation):
        with cur.connection.transaction():
            cur.execute(
                "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) "
                "values (%s, %s, %s, %s)",
                (uuid.uuid4(), listing_id, seller_id, seller_id),
            )


def test_trigger_overwrites_third_party_seller_id_and_new_column_still_works(seeded):
    """⑭ 0016 트리거의 **본래 목적**(제3자 seller_id 위조 차단)을 실제 입력으로 확인한다.

    왜 따로 필요한가: 이 파일의 다른 곳은 전부 `bogus_seller_id = buyer_id`만 넣는다. 그 입력은
    트리거가 "자기 자신이 seller일 때만 고치는" 형태로 퇴화해도 통과한다 — 0016 헤더가 밝힌
    진짜 차단 대상("임의의 seller_id를 적어 모르는 사람에게 방을 강제 생성")은 한 번도 안 탄다.
    여기서는 매물과 아무 관계없는 **제3의 사용자**를 seller_id로 실어 보내고, 트리거가 그것을
    무시하고 실제 소유자로 덮는지 본다. 이어서 그 방에 client_message_id를 실은 메시지가
    정상 삽입되는지까지 확인해 이 스토리의 새 컬럼이 트리거와 공존함을 함께 고정한다.
    """
    cur, _room_id, _buyer_id, seller_id, listing_id = seeded

    outsider_id = _create_user(cur, f"ci-outsider-{uuid.uuid4()}@example.com")
    other_buyer_id = _create_user(cur, f"ci-buyer3-{uuid.uuid4()}@example.com")

    # 매물과 무관한 제3자를 seller_id로 위조해 방 생성 시도.
    room_id = _insert_chat_room(cur, listing_id, other_buyer_id, outsider_id)

    cur.execute("select seller_id from public.chat_rooms where id = %s", (room_id,))
    stored_seller = cur.fetchone()[0]
    assert stored_seller == seller_id, "트리거가 제3자 seller_id를 매물 실소유자로 덮지 않았다(위조 차단 회귀)"
    assert stored_seller != outsider_id

    client_message_id = uuid.uuid4()
    with cur.connection.transaction():
        _insert_message_on_conflict_do_nothing(
            cur, room_id, other_buyer_id, "위조 시도 후 정상화된 방의 메시지", client_message_id
        )
    assert _message_count(cur, room_id, client_message_id) == 1
