"""chat_messages AFTER INSERT 트리거의 Realtime Broadcast + realtime.messages RLS 실DB 검증
(Story 12.2, AC-CHAT-3, I/O 매트릭스 3행).

왜 이 파일이 따로 있나:
  0023이 SQL로 만드는 트리거·RLS 정책이 **존재한다**는 것과 실제 INSERT·SELECT 시나리오에서
  **기대대로 동작한다**는 것은 다른 사실이다(CLAUDE.md B4 "존재 확인은 작동 확인이 아니다").
  특히 `realtime.messages`의 RLS는 Supabase Realtime 서버가 웹소켓 구독 시 내부적으로 확인하는
  것과 동일한 조건(authenticated 롤 + JWT `sub` + 세션 GUC `realtime.topic`)이라, 웹소켓 연결 없이
  이 파일이 그 인가 검사를 그대로 재현해 실측한다(스펙 Design Notes).

무엇을 증명하나:
  ① 당사자(buyer)가 chat_messages에 INSERT하면 realtime.messages에 `topic='chat:room:{room_id}'`,
     `extension='broadcast'`인 행이 정확히 1개 생성되고, payload에 실제 메시지 내용(NEW)이 실린다
     (I/O 매트릭스 1행, AC-CHAT-3 2번째 Given — payload까지 보는 이유: 트리거가 하드코딩된 값이
     아니라 실제 NEW 레코드를 넘긴다는 것까지 확인해야 "방송이 그 메시지의 것"이라고 말할 수 있다).
  ② seller가 보낸 메시지도 동일하게 방송된다(당사자는 buyer/seller 대칭).
  ③ 방 당사자가 아닌 authenticated 유저(outsider)가 그 토픽으로 접근하면 0행(I/O 매트릭스 2행,
     AC-CHAT-3 3번째 Given — 제3자 차단).
  ④ 당사자(buyer)가 같은 조건으로 조회하면 그 토픽의 행이 보인다(AC-CHAT-3 4번째 Given).
  ④' seller도 당사자이므로 대칭적으로 보인다.
  ⑤ 트리거가 STATEMENT가 아니라 ROW 레벨로 걸려 있는지 회귀 확인 — 한 INSERT 문으로 메시지
     3건을 멀티 VALUES로 한 번에 넣어도 방송 행이 정확히 3건이고 **셋의 payload가 서로 달라야**
     한다(개수만 보면 같은 NEW를 3번 방송하는 구현도 통과한다).
  ⑥ 트리거·정책이 기대한 **모양**으로 존재한다 — 트리거의 시점(AFTER)·수준(FOR EACH ROW)·이벤트
     (INSERT 한정)와 정책 조건식의 두 축을 정의(`pg_get_triggerdef`/`pg_policies.qual`)로 대조한다.
  ⑧ 0023의 "INSERT 정책이 필요 없는 이유"가 기대는 두 속성 — 트리거 함수가 SECURITY DEFINER이고
     그 **함수 소유자**가 `rolbypassrls`라는 것 — 을 고정한다.
  ⑨ 정책이 **행 축**으로도 거르는지 — 방A 토픽으로 인가받은 세션이 토픽 필터 없이 조회해도
     방B 행은 안 보여야 한다(2026-07-28 후속 리뷰가 실측으로 잡은 교차-방 유출의 회귀 검사).
  ⑩ 메시지가 **자기 방** 토픽으로만 방송되는지(방 2개를 두어야 구별된다 — 오배송 회귀 검사).
  ⑪ "어떤 방의 당사자이지만 이 방은 아닌" 세션 차단(③의 outsider와 달리 `exists`가 방을 찾는 경로).
  ⑫ **실제 클라이언트 경로**(`set local role authenticated`로 INSERT)에서도 방송이 나가는지 —
     이것이 SECURITY DEFINER 전제의 동작 축 확인이다.
  ⑬ 0023이 회수한 EXECUTE 권한(public/anon/authenticated)이 실제로 없는지.
  ⑭ **쓰기 축** — authenticated가 남의 방 토픽으로 가짜 방송을 심을 수 없는지. 이 롤은 INSERT
     테이블 GRANT를 이미 갖고 있어서, 막고 있는 건 "쓰기 정책이 하나도 없다"는 사실뿐이다.
  ※ ①은 방송 행의 `private`까지 본다 — Realtime은 **비공개 채널에만** 이 RLS를 물어보므로,
    그 플래그가 이 스토리의 인가 전체가 서 있는 바닥이다(트리거는 그걸 명시하지 않고
    `realtime.send()`의 기본값에 기댄다).

  ※ I/O 매트릭스 3행(소급 방송 없음)의 정적 검사는 DB가 필요 없어 이 파일에서 분리했다 →
    `api/tests/test_migration_no_backfill.py`(TEST_DATABASE_URL 없이도 돈다).

무엇을 못 보나: 실제 웹소켓 연결(Supabase Realtime 서버)을 통한 채널 구독·수신 자체는 이 파일이
  검증하지 않는다 — 클라이언트 구독 코드는 Story 12.3 범위다(스펙 Never 절). 이 파일은 DB 계층
  (트리거 발동·RLS 조건)만 본다. 접속은 psycopg로 **DSN 소유자(postgres) 권한**이라 RLS·GRANT가
  기본 우회되며, RLS를 보는 테스트와 ⑫만 `set local role authenticated` + `request.jwt.claim.sub`
  + `realtime.topic` GUC로 롤과 세션을 흉내낸다(형제 `test_chat_idempotency_real_db.py`의 ⑬과 동일 패턴).
  또한 CI(api-db 잡)에서는 이 파일이 **실제 Supabase 플랫폼이 아니라 `scripts/migration-check-prelude.sql`이
  재현한 realtime 스텁** 위에서 돈다 — 스텁은 비파티션 테이블이라 실제 플랫폼의 "파티션 부재 →
  `realtime.send()`가 예외를 삼킴 → 방송만 조용히 사라짐" 실패 모드가 여기선 구조적으로 발생할 수
  없다. 그 축은 원격에서 확인해야 한다(`docs/tech-debt.md` #195).

실행: CI의 api-db 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import uuid
from typing import NamedTuple

import psycopg
import pytest

from conftest import _DSN, _create_user, _insert_listing, pytestmark  # noqa: F401

_TOPIC_PREFIX = "chat:room:"


class _Seed(NamedTuple):
    """`seeded` 픽스처가 넘기는 값 묶음. 방이 2개로 늘면서 위치 기반 언패킹이 순서 실수에
    취약해져 이름으로 접근하게 바꿨다."""

    cur: object
    room_id: uuid.UUID
    buyer_id: uuid.UUID
    seller_id: uuid.UUID
    outsider_id: uuid.UUID
    room_b_id: uuid.UUID
    seller_b_id: uuid.UUID


def _insert_chat_room(cur, listing_id, buyer_id, seller_id):
    room_id = uuid.uuid4()
    cur.execute(
        "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) "
        "values (%s, %s, %s, %s)",
        (room_id, listing_id, buyer_id, seller_id),
    )
    return room_id


def _send_message(cur, room_id, sender_id, body="실시간 방송 테스트 메시지"):
    cur.execute(
        "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s) "
        "returning id",
        (room_id, sender_id, body),
    )
    return cur.fetchone()[0]


def _send_messages_single_statement(cur, room_id, sender_id, bodies):
    values_sql = ", ".join(["(%s, %s, %s)"] * len(bodies))
    params = []
    for body in bodies:
        params.extend([room_id, sender_id, body])
    cur.execute(
        f"insert into public.chat_messages (room_id, sender_id, body) values {values_sql}",
        params,
    )


def _broadcast_rows_for_topic(cur, topic):
    """DSN 소유자(postgres, RLS 우회) 권한으로 topic 하나에 대한 방송 행을 그대로 본다 —
    트리거가 실제로 무엇을 썼는지(RLS와 무관하게) 확인하는 용도.

    `private`까지 읽는 이유(2026-07-28 3차 리뷰): Supabase Realtime은 **비공개(private) 채널에만**
    `realtime.messages` RLS를 물어본다. 공개 채널이면 이 스토리가 만든 참가자 정책은 아예 조회되지
    않는다. 그런데 트리거는 `broadcast_changes()`에 `private`를 넘기지 않고 `realtime.send()`의
    기본값(`private boolean default true`)에 기대고 있다 — 즉 이 스토리의 인가가 통째로 서 있는
    성질이 **아무 검사도 받지 않는 플랫폼 함수의 기본값**이었다. 한 컬럼 더 읽어 그걸 고정한다."""
    cur.execute(
        "select topic, extension, payload, private from realtime.messages where topic = %s",
        (topic,),
    )
    return cur.fetchall()


def _select_as_authenticated(cur, viewer_id, topic, filter_by_topic=True):
    """`set local role authenticated` + JWT claim + 세션 GUC `realtime.topic`으로 Realtime
    서버가 채널 구독 시 하는 인가 검사를 재현한다(스펙 Design Notes).

    `filter_by_topic=True`(기본)는 Realtime 서버의 실제 조회 형태(항상 그 토픽으로 필터링)를 흉내낸다.
    `filter_by_topic=False`는 **호출자가 토픽 필터를 공급하지 않는 경우**로, 정책이 스스로 행을
    걸러내는지(행 축)를 본다 — 2026-07-28 후속 리뷰에서 정책이 세션 축만 보고 있어 아무 방 하나의
    당사자가 모든 방의 방송을 읽을 수 있던 결함이 실측됐고, 그때 `where topic = ...`을 이 헬퍼가
    스스로 공급하고 있었기 때문에 ③④④'가 전부 초록이었다. 그 사각지대를 없애려고 인자로 뺐다."""
    with cur.connection.transaction():
        cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(viewer_id),))
        cur.execute("select set_config('realtime.topic', %s, true)", (topic,))
        cur.execute("set local role authenticated")
        try:
            if filter_by_topic:
                cur.execute(
                    "select topic, extension from realtime.messages where topic = %s", (topic,)
                )
            else:
                cur.execute("select topic, extension from realtime.messages")
            rows = cur.fetchall()
        finally:
            # 위에서 권한 오류가 나면 트랜잭션이 이미 중단(aborted)돼 reset role 자체가 실패한다 —
            # 그걸 그대로 두면 진짜 원인(권한 거부)이 2차 예외에 가려진다(형제 파일과 동일 패턴).
            try:
                # `set local`/`set_config(..., true)`는 **세이브포인트가 아니라 트랜잭션** 범위다 —
                # `with connection.transaction()`이 세이브포인트를 놓아줘도 두 GUC는 그대로 남는다.
                # 롤만 되돌리면 다음 조회가 **직전 뷰어의 신원**을 그대로 물려받아, 인가를 검사한 게
                # 아닌데 통과로 보이는 거짓 초록이 만들어진다. 롤과 같은 자리에서 함께 지운다.
                cur.execute("select set_config('request.jwt.claim.sub', '', true)")
                cur.execute("select set_config('realtime.topic', '', true)")
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass
    return rows


@pytest.fixture
def seeded():
    """구매자 1명 + 판매자 2명 + 매물 2건 + 채팅방 **2개** + 제3자(어느 방과도 무관한 유저) 1명.

    방을 2개 두는 이유(2026-07-28 후속 리뷰): 방이 1개뿐이면 "메시지가 자기 방 토픽으로 갔는가"와
    "아무 토픽으로나 갔는가"가 구별되지 않는다 — 실제로 토픽 유도식을 `sender_id로 방을 찾는` 형태로
    바꿔도 기존 테스트 9건이 전부 통과했고, 그 상태에서 방B 메시지가 방A 토픽에 실려 방A 판매자가
    읽는 교차-방 유출이 재현됐다. 두 방은 **같은 구매자**를 공유해(판매자만 다름) "당사자이긴 한데
    이 방은 아닌" 세션을 만들 수 있게 한다.

    끝나면 **롤백**해 DB를 원상복구한다(형제 `test_chat_idempotency_real_db.py`와 동일 패턴)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = _create_user(c, f"ci-rt-seller-{uuid.uuid4()}@example.com", role="seller")
            seller_b_id = _create_user(c, f"ci-rt-seller-b-{uuid.uuid4()}@example.com", role="seller")
            buyer_id = _create_user(c, f"ci-rt-buyer-{uuid.uuid4()}@example.com")
            outsider_id = _create_user(c, f"ci-rt-outsider-{uuid.uuid4()}@example.com")
            listing_id = uuid.uuid4()
            listing_b_id = uuid.uuid4()
            _insert_listing(c, listing_id, seller_id)
            _insert_listing(c, listing_b_id, seller_b_id)
            room_id = _insert_chat_room(c, listing_id, buyer_id, seller_id)
            room_b_id = _insert_chat_room(c, listing_b_id, buyer_id, seller_b_id)
            yield _Seed(c, room_id, buyer_id, seller_id, outsider_id, room_b_id, seller_b_id)
        conn.rollback()


def test_buyer_message_broadcasts_to_room_topic(seeded):
    """① AC-CHAT-3 — buyer가 메시지를 보내면 realtime.messages에 정확히 topic='chat:room:{room_id}',
    extension='broadcast'인 행이 하나 생기고, payload에 실제 메시지 본문이 실린다."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id, "안녕하세요, 문의드립니다")

    rows = _broadcast_rows_for_topic(cur, topic)
    assert len(rows) == 1, "트리거가 정확히 1개 행을 방송하지 않았다"
    got_topic, got_extension, payload, private = rows[0]
    assert got_topic == topic
    assert got_extension == "broadcast"
    assert private is True, (
        "방송이 **비공개 채널**로 나가지 않았다 — Realtime은 private 채널에만 realtime.messages "
        "RLS를 물어보므로, 이게 false면 이 스토리가 만든 참가자 정책이 통째로 무의미해진다"
    )
    assert payload["operation"] == "INSERT"
    assert payload["record"]["body"] == "안녕하세요, 문의드립니다"
    assert payload["record"]["room_id"] == str(seeded.room_id)


def test_seller_message_also_broadcasts(seeded):
    """② 당사자는 buyer/seller 둘 다 — seller가 보낸 메시지도 동일하게 방송된다.

    sender_id까지 단언하는 이유: 행 개수만 보면 이 테스트는 ①과 완전히 같은 검사가 된다(누가
    보냈는지가 단언에 안 들어가므로). payload가 실제 발신자를 싣는다는 것까지 봐야 "판매자가 보낸
    것도 방송된다"가 검사된 주장이 된다."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.seller_id, "판매자 응답입니다")

    rows = _broadcast_rows_for_topic(cur, topic)
    assert len(rows) == 1
    assert rows[0][1] == "broadcast"
    assert rows[0][2]["record"]["sender_id"] == str(seeded.seller_id)
    assert rows[0][2]["record"]["body"] == "판매자 응답입니다"


def test_third_party_cannot_see_room_topic(seeded):
    """③ AC-CHAT-3 — 방 당사자가 아닌 authenticated 유저(outsider)가 그 토픽으로 접근하면
    0행(RLS 차단, I/O 매트릭스 2행)."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id)

    rows = _select_as_authenticated(cur, seeded.outsider_id, topic)
    assert rows == [], "제3자가 방 토픽의 방송 행을 볼 수 있었다(RLS 차단 실패)"


def test_buyer_can_see_own_room_topic(seeded):
    """④ AC-CHAT-3 — 당사자(buyer)가 같은 조건으로 조회하면 그 토픽의 행이 보인다."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id)

    rows = _select_as_authenticated(cur, seeded.buyer_id, topic)
    assert len(rows) == 1
    assert rows[0][0] == topic
    assert rows[0][1] == "broadcast"


def test_seller_can_see_own_room_topic(seeded):
    """④' seller도 당사자이므로 마찬가지로 보인다(참여자=buyer 또는 seller 대칭 확인)."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id)

    rows = _select_as_authenticated(cur, seeded.seller_id, topic)
    assert len(rows) == 1


def test_policy_filters_rows_not_just_session(seeded):
    """⑨ **정책이 행 축으로도 거르는지** — 2026-07-28 후속 리뷰가 실측으로 잡은 결함의 회귀 검사.

    처음 정책은 `exists(...)`(세션 축)만 봤고 행의 어떤 컬럼도 참조하지 않아 세션 상수로 평가됐다.
    그래서 아무 방 하나의 당사자이기만 하면 토픽 필터 없는 `select * from realtime.messages`로
    **모든 방의 방송 행**이 보였다(로컬 Supabase 스택에서 재현). 기존 ③④④'는 헬퍼가 스스로
    `where topic = ...`을 붙였기 때문에 이 결함을 못 봤다.

    여기서는 구매자가 두 방 모두의 당사자인 상태로, 방A 토픽으로 인가받은 세션이 **토픽 필터 없이**
    조회한다. 정책이 행 축(`topic = realtime.topic()`)을 함께 보지 않으면 방B 행까지 보여 실패한다."""
    cur = seeded.cur
    topic_a = f"{_TOPIC_PREFIX}{seeded.room_id}"
    topic_b = f"{_TOPIC_PREFIX}{seeded.room_b_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id, "방A 메시지")
        _send_message(cur, seeded.room_b_id, seeded.buyer_id, "방B 메시지")

    rows = _select_as_authenticated(cur, seeded.buyer_id, topic_a, filter_by_topic=False)
    seen = {row[0] for row in rows}
    assert topic_b not in seen, (
        "방A 토픽으로 인가받은 세션이 방B의 방송 행까지 볼 수 있었다 — 정책이 행의 topic을 "
        "안 보고 세션 상수로만 평가되고 있다(교차-방 유출)"
    )
    assert seen == {topic_a}, f"방A 토픽 행만 보여야 하는데 {seen}이 보였다"


def test_message_broadcasts_only_to_its_own_room_topic(seeded):
    """⑩ 토픽 유도식이 **그 메시지의 방**에서 나오는지 — 방이 1개뿐이던 시절엔 어떤 유도식이든
    같은 답이 나와 구별되지 않았다. 방B에 보낸 메시지가 방A 토픽에 실리면 여기서 잡힌다(실측:
    토픽을 sender_id로 방을 찾아 만들도록 바꾸면 기존 테스트는 전부 통과하면서 이 유출이 생겼다).

    같은 구매자가 두 방의 당사자라, 발신자만 보고 방을 고르는 잘못된 유도식이 실제로 오답을 낸다."""
    cur = seeded.cur
    topic_a = f"{_TOPIC_PREFIX}{seeded.room_id}"
    topic_b = f"{_TOPIC_PREFIX}{seeded.room_b_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_b_id, seeded.buyer_id, "방B에만 가야 하는 메시지")

    assert _broadcast_rows_for_topic(cur, topic_a) == [], (
        "방B에 보낸 메시지가 방A 토픽으로 방송됐다(교차-방 오배송)"
    )
    rows_b = _broadcast_rows_for_topic(cur, topic_b)
    assert len(rows_b) == 1
    assert rows_b[0][2]["record"]["body"] == "방B에만 가야 하는 메시지"


def test_participant_of_other_room_cannot_see_this_room(seeded):
    """⑪ 세션 축 음성 대조 — 방B 판매자는 authenticated이고 "어떤 방의 당사자"이기도 하지만
    방A의 당사자는 아니다. ③의 outsider(아무 방에도 없음)와 달리 이쪽은 `exists(...)`가 방을
    찾긴 하는 경로라, 조건이 "그 방"으로 좁혀져 있는지를 따로 본다."""
    cur = seeded.cur
    topic_a = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_message(cur, seeded.room_id, seeded.buyer_id, "방A 비밀")

    rows = _select_as_authenticated(cur, seeded.seller_b_id, topic_a)
    assert rows == [], "방B 판매자가 방A의 방송 행을 볼 수 있었다"


def test_authenticated_cannot_forge_a_broadcast(seeded):
    """⑭ **쓰기 축** — authenticated 롤은 `realtime.messages`에 INSERT **테이블 GRANT를 이미 갖고
    있다**(Supabase 플랫폼 기본, 프렐류드 스텁도 동일). 그래서 남의 방 토픽으로 가짜 방송을 심는 걸
    막는 것은 GRANT가 아니라 **쓰기 정책이 하나도 없다는 사실**뿐이다(정책 없는 RLS = 기본 거부).

    스펙 Never 절이 "INSERT/UPDATE/DELETE 정책을 추가하지 않는다"고 한 것이 이 성질을 지키기 위한
    것인데, 지금까지 그게 **실제로 거르는지**는 아무도 확인하지 않았다(⑥은 정책 집합만 본다 —
    존재 확인이지 작동 확인이 아니다, CLAUDE.md B4·B9)."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        cur.execute(
            "select set_config('request.jwt.claim.sub', %s, true)", (str(seeded.outsider_id),)
        )
        cur.execute("select set_config('realtime.topic', %s, true)", (topic,))
        cur.execute("set local role authenticated")
        try:
            # 거부는 트랜잭션을 중단시키므로 안쪽 세이브포인트에 가둔다 — 그래야 아래 finally의
            # 정리 문장들이 실행될 수 있다.
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with cur.connection.transaction():
                    cur.execute(
                        "insert into realtime.messages (topic, extension, payload) "
                        "values (%s, 'broadcast', %s::jsonb)",
                        (topic, '{"record": {"body": "위조된 방송"}}'),
                    )
        finally:
            try:
                cur.execute("select set_config('request.jwt.claim.sub', '', true)")
                cur.execute("select set_config('realtime.topic', '', true)")
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass


def test_authenticated_client_insert_still_broadcasts(seeded):
    """⑫ **실제 클라이언트 경로**로 방송이 나가는지 — 다른 모든 테스트는 DSN 소유자(postgres,
    RLS·GRANT 우회) 권한으로 INSERT한다. 그래서 "트리거 함수가 SECURITY DEFINER라서 정책 없이도
    realtime.messages에 쓸 수 있다"는 0023의 핵심 전제가 **한 번도 하중을 받지 않았다** — 실측:
    함수에서 `security definer`를 떼도 기존 테스트 9건이 전부 통과했고, 그 상태에서 authenticated
    세션으로 메시지를 보내면 `WarnSendingBroadcastMessage: new row violates row-level security
    policy`만 남고 방송 행이 0건이 됐다(메시지는 저장되므로 조용한 실패).

    여기서는 PostgREST가 하는 것과 같이 `set local role authenticated` + JWT sub로 INSERT해,
    그 전제를 동작으로 확인한다(존재 확인이 아니라 작동 확인, CLAUDE.md B4)."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        cur.execute(
            "select set_config('request.jwt.claim.sub', %s, true)", (str(seeded.buyer_id),)
        )
        cur.execute("set local role authenticated")
        try:
            _send_message(cur, seeded.room_id, seeded.buyer_id, "클라이언트 경로 메시지")
        finally:
            try:
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass

    rows = _broadcast_rows_for_topic(cur, topic)
    assert len(rows) == 1, (
        "authenticated 롤로 보낸 메시지의 방송 행이 없다 — 트리거 함수의 SECURITY DEFINER 전제가 "
        "깨졌을 수 있다(메시지는 저장되고 방송만 조용히 사라지는 실패 모드)"
    )
    assert rows[0][2]["record"]["body"] == "클라이언트 경로 메시지"


def test_multi_row_insert_broadcasts_one_row_per_message(seeded):
    """⑤ 트리거가 FOR EACH ROW로 걸려 있는지 회귀 확인 — 한 INSERT 문으로 메시지 3건을 한 번에
    넣어도(멀티 VALUES) 방송 행이 정확히 3건이어야 하고, **각 행의 payload가 서로 다른 메시지**여야
    한다. 개수만 보면 같은 NEW를 3번 방송하는 구현도 통과하므로 본문 집합까지 단언한다."""
    cur = seeded.cur
    topic = f"{_TOPIC_PREFIX}{seeded.room_id}"

    with cur.connection.transaction():
        _send_messages_single_statement(
            cur, seeded.room_id, seeded.buyer_id, ["메시지1", "메시지2", "메시지3"]
        )

    rows = _broadcast_rows_for_topic(cur, topic)
    assert len(rows) == 3, "메시지 3건을 한 문장으로 INSERT했는데 방송 행이 3건이 아니다"
    assert sorted(row[2]["record"]["body"] for row in rows) == ["메시지1", "메시지2", "메시지3"], (
        "방송 3건이 서로 다른 메시지를 싣지 않았다 — 같은 NEW가 반복 방송됐을 수 있다"
    )


def test_trigger_and_policy_exist_with_expected_shape(seeded):
    """⑥ AC 1행 — 트리거·정책이 기대한 **모양**으로 실제 존재한다.

    이름만 보던 것을 정의까지 보도록 넓혔다: 트리거의 시점(AFTER)·수준(FOR EACH ROW)·이벤트(INSERT
    한정)와 정책 조건식의 두 축(`realtime.topic()` 세션 축, `topic` 행 축)이 그것이다. 이름만 보면
    `after insert or update`로 바꾸거나 `before insert`로 바꿔도 전부 통과했다."""
    cur = seeded.cur

    cur.execute(
        "select tgname, pg_get_triggerdef(oid) from pg_trigger "
        "where tgrelid = 'public.chat_messages'::regclass and not tgisinternal"
    )
    triggers = {row[0]: row[1] for row in cur.fetchall()}
    assert "chat_messages_broadcast_trigger" in triggers, "chat_messages_broadcast_trigger가 없다"
    definition = triggers["chat_messages_broadcast_trigger"]
    assert "AFTER INSERT" in definition, f"트리거가 AFTER INSERT가 아니다: {definition}"
    assert "FOR EACH ROW" in definition, f"트리거가 ROW 수준이 아니다: {definition}"
    assert "UPDATE" not in definition and "DELETE" not in definition, (
        f"트리거에 UPDATE/DELETE가 배선됐다(스펙 Always: AFTER INSERT로만): {definition}"
    )
    # `when (...)` 조건절이 붙으면 **일부 메시지만** 방송된다 — 위 세 단언은 그래도 전부 참이라
    # 조용히 통과한다(픽스처의 본문이 전부 비어있지 않아 동작 테스트도 못 잡는다).
    assert " WHEN " not in definition.upper(), (
        f"트리거에 WHEN 조건절이 붙어 일부 메시지만 방송된다: {definition}"
    )

    cur.execute(
        "select policyname, cmd, roles::text[], qual from pg_policies "
        "where schemaname = 'realtime' and tablename = 'messages'"
    )
    policies = {row[0]: row for row in cur.fetchall()}
    # 스펙 Never 절("realtime.messages에 INSERT/UPDATE/DELETE 정책을 추가하지 않는다")을 고정한다 —
    # 있어야 할 게 있는지만 보면, 나중에 누가 쓰기 정책을 하나 더 얹어도 전부 초록이다.
    assert set(policies) == {"chat_room_participants_select_broadcast"}, (
        f"realtime.messages의 정책 집합이 기대와 다르다(SELECT 1개만이어야 한다): {sorted(policies)}"
    )
    _name, cmd, roles, qual = policies["chat_room_participants_select_broadcast"]
    assert cmd == "SELECT", "정책이 SELECT 전용이 아니다"
    assert "authenticated" in roles
    assert "realtime.topic()" in qual, f"정책이 세션 축(realtime.topic())을 안 본다: {qual}"
    assert "topic = realtime.topic()" in qual, (
        f"정책이 행 축(topic 컬럼)을 안 본다 — 교차-방 유출 회귀: {qual}"
    )
    # `extension = 'broadcast'` 축은 지금까지 아무도 안 봤다 — 이 항을 빼면 참가자가 같은 토픽의
    # presence·postgres_changes 행까지 읽게 되는데, 이 파일의 모든 행이 broadcast라 동작 테스트로는
    # 구별되지 않는다(3차 리뷰 실측: 항을 빼도 13건 전부 통과).
    assert "extension = 'broadcast'" in qual, (
        f"정책이 extension 축을 안 본다 — broadcast 외 이벤트까지 열린다: {qual}"
    )


def test_broadcast_function_execute_is_revoked(seeded):
    """⑬ 0023이 명시적으로 회수한 EXECUTE 권한이 실제로 없는지 — 파일 주석은 "PostgREST의
    /rest/v1/rpc 노출과 SECURITY DEFINER 직접 호출을 막는다"고 주장하지만 지금까지 아무도
    확인하지 않았다. `create or replace`가 아니라 `drop function` + `create function`으로 바뀌면
    기본 PUBLIC EXECUTE가 조용히 되살아난다(형제 `test_view_count_rpc_real_db.py`가 0020의
    함수에 대해 이미 같은 검사를 한다)."""
    cur = seeded.cur
    for role in ("public", "anon", "authenticated"):
        cur.execute(
            "select has_function_privilege(%s, 'public.chat_messages_broadcast()', 'EXECUTE')",
            (role,),
        )
        assert cur.fetchone()[0] is False, (
            f"{role}에 chat_messages_broadcast()의 EXECUTE 권한이 남아 있다 — RPC로 직접 호출 가능"
        )


def test_broadcast_function_is_security_definer_owned_by_bypassrls_role(seeded):
    """⑧ 0023 파일 주석의 핵심 전제를 **올바른 대상에 대해** 잠근다.

    이전 버전은 `current_user`(테스트 커넥션의 롤)의 `rolbypassrls`를 쟀는데, 그건 CI에서 항상
    postgres 슈퍼유저라 구조적으로 참이라 절대 실패할 수 없었다 — 실측: 함수에서 `security definer`를
    떼어도 이 테스트는 그대로 통과했다. 전제가 실제로 기대는 것은 ⓐ 함수가 SECURITY DEFINER이고
    ⓑ 그 **함수 소유자**가 rolbypassrls라는 두 가지다. 그 둘을 직접 조회한다.

    (동작 축은 ⑫가 본다 — 이 검사는 그 동작이 어떤 속성 위에 서 있는지를 고정한다.)"""
    cur = seeded.cur
    cur.execute(
        "select p.prosecdef, r.rolname, r.rolbypassrls "
        "from pg_proc p join pg_roles r on r.oid = p.proowner "
        "join pg_namespace n on n.oid = p.pronamespace "
        "where n.nspname = 'public' and p.proname = 'chat_messages_broadcast'"
    )
    row = cur.fetchone()
    assert row is not None, "public.chat_messages_broadcast() 함수를 찾지 못했다"
    prosecdef, owner, owner_bypassrls = row
    assert prosecdef is True, "트리거 함수가 더 이상 SECURITY DEFINER가 아니다"
    assert owner_bypassrls is True, (
        f"트리거 함수 소유자({owner})가 rolbypassrls가 아니다 — 0023이 realtime.messages에 INSERT "
        f"정책을 안 둔 전제가 깨졌다(방송이 조용히 사라진다)"
    )
