"""chat_room_reads·chat_unread_count()·last_message_at 트리거 실DB 검증
(Story 12.5, FR57, 코드리뷰 verification-gap+intent-alignment 교차 지적).

왜 이 파일이 따로 있나:
  0024가 chat_room_reads 테이블(+RLS)·chat_rooms.last_message_at 컬럼(+트리거)·
  chat_unread_count() RPC를 SQL로 추가하는 것과, 그 SQL이 실제 시나리오에서 기대대로
  동작하는 것은 다른 사실이다(CLAUDE.md B4 "존재 확인은 작동 확인이 아니다"). 이 레포는
  신규 RPC/트리거/RLS가 생길 때마다 이런 실DB 짝 테스트를 둔다(`test_view_count_rpc_real_db.py`·
  `test_chat_idempotency_real_db.py`·`test_chat_realtime_broadcast_real_db.py`와 같은 이유,
  같은 방식) — 이번 마이그레이션만 그 관례에서 비어 있던 것을 이 파일이 채운다.

무엇을 증명하나 (스펙 I/O 매트릭스 4행 + Always 절):
  ① 안읽음 공식(sender_id <> auth.uid() AND created_at > last_read_at)이 실제로 상대방
     메시지만 세고 본인 발신은 제외한다(I/O 매트릭스 "내 발신만 있는 방").
  ② last_read_at 커트라인이 strict `>`다 — 정확히 그 시각인 메시지는 안읽음이 아니다.
  ③ chat_room_reads_insert_participant RLS가 그 방의 실제 당사자가 아닌 사용자의 INSERT를
     실제로 거부한다(42501) — "존재 확인이 아니라 작동 확인"(B4).
  ④ chat_room_reads_select_own RLS가 타인의 읽음 행을 실제로 숨긴다.
  ⑤ chat_room_reads_update_own의 참여자 재검증(코드리뷰 patch)이 자신의 행을 자신이
     당사자 아닌 방으로 재지정하는 UPDATE를 실제로 거부한다 — 패치 전이었다면 통과했을 경로.
  ⑥ chat_messages_touch_room_last_message 트리거가 last_message_at을 갱신하되, 시각 역전
     (out-of-order 커밋)에도 **단조증가만 허용**한다(코드리뷰 patch — greatest() 가드)는
     사실을 실제로 시각을 거꾸로 넣어 확인한다.
  ⑦ 공식의 "내가 당사자인 방" 축 — 남의 방 메시지가 DB에 있어도 집계에 안 잡힌다(0025).
  ⑧ 관리자에게 전체 대화가 집계되지 않는다 — 0005의 관리자 SELECT 정책이 참여자 정책과 OR로
     합쳐지므로 RLS에만 맡기면 새는 축이었다(실측으로 발견, 0025가 함수 안에 참여자 조인을 복원).
  ⑨ **성공 경로** RLS·GRANT — 정상 당사자의 INSERT와 재진입 upsert(ON CONFLICT DO UPDATE)가
     authenticated 롤에서 실제로 통과한다(거부만 검사하면 "정상 사용자도 막히는" 회귀를 못 잡는다).
  ⑩ 0024의 **백필 UPDATE 문 자체**가 데이터가 있는 방들에 대해 올바른 값을 계산한다 — CI는
     전부 빈 DB에 마이그레이션을 적용하므로 이 문장은 어디서도 0행 이상에 실행된 적이 없었다
     (후속 코드리뷰 verification-gap 지적). 공식은 사본을 만들지 않고 마이그레이션 파일에서
     읽어와 실행한다.

무엇을 못 보나: 클라이언트(web)가 이 RPC·테이블을 실제로 어떻게 호출하는지(markChatRoomRead·
  AppHeader의 배선)는 vitest 몫이고 여기서 보지 않는다. 이 파일은 DB 계층만 본다. 접속은
  `psycopg`로 **DSN 소유자(postgres) 권한**이라 RLS·컬럼 GRANT는 대부분 우회된다 — RLS를
  보는 테스트만 `set local role authenticated` + `request.jwt.claim.sub`로 롤을 흉내낸다
  (`test_chat_idempotency_real_db.py`의 ⑬번과 동일한 알려진 한계, 대장 #133).

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import uuid
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest

# 공유 헬퍼는 conftest.py가 정본이다(대장 #188 — 파일마다 사본을 만들다 role 하드코딩 결함이
# 한 번 났다). 후속 코드리뷰 patch: 이 파일도 사본 대신 conftest에서 가져온다.
from conftest import _DSN, _create_user, _insert_listing, pytestmark  # noqa: F401

_RLS_VIOLATION = "42501"

# RLS 거부와 "GRANT 누락으로 인한 권한 거부"는 **둘 다 42501**이라 sqlstate만 보면 구별되지 않는다.
# 대장 #211이 실측한 대로 이 프로젝트의 로컬 스택은 실제로 authenticated의 테이블 GRANT를 잃은
# 적이 있고, 그 상태에서도 아래 거부 테스트들은 초록이 됐을 것이다 — "정책이 걸렀다"가 아니라
# "환경이 깨졌다"를 통과로 읽는 것. 그래서 메시지까지 대조한다(후속 코드리뷰 patch).
_RLS_MESSAGE_MARK = "row-level security policy"


def _insert_chat_room(cur, listing_id, buyer_id, bogus_seller_id):
    """0016 트리거가 seller_id를 매물의 실제 소유자로 강제 덮어쓴다(형제 파일과 동일 전제)."""
    room_id = uuid.uuid4()
    cur.execute(
        "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) "
        "values (%s, %s, %s, %s)",
        (room_id, listing_id, buyer_id, bogus_seller_id),
    )
    return room_id


def _insert_message(cur, room_id, sender_id, body, created_at=None):
    if created_at is None:
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s)",
            (room_id, sender_id, body),
        )
    else:
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body, created_at) "
            "values (%s, %s, %s, %s)",
            (room_id, sender_id, body, created_at),
        )


def _unread_count_as(cur, user_id):
    """authenticated 롤 + request.jwt.claim.sub로 그 사용자를 흉내내 chat_unread_count()를 호출한다.
    SECURITY INVOKER라 auth.uid()가 이 세션 변수를 그대로 읽는다(0024 Design Notes)."""
    cur.execute(f"set local request.jwt.claim.sub = '{user_id}'")
    cur.execute("set local role authenticated")
    try:
        cur.execute("select public.chat_unread_count()")
        return cur.fetchone()[0]
    finally:
        try:
            # 롤뿐 아니라 신분(jwt sub)도 되돌린다(후속 코드리뷰 patch). `set local`은 트랜잭션
            # 끝까지 살아 있는데 이 픽스처는 파일 하나가 트랜잭션 하나다 — 롤만 되돌리면 이 호출
            # 뒤에 오는 문장들이 "남의 신분이 박힌 채" 실행된다. 지금은 롤이 postgres로 돌아가
            # RLS가 우회되므로 무해하지만, auth.uid()를 보는 트리거가 하나만 생겨도 조용히 틀린
            # 초록이 된다.
            cur.execute("reset role")
            cur.execute("reset request.jwt.claim.sub")
        except psycopg.errors.InFailedSqlTransaction:
            pass


@pytest.fixture
def seeded():
    """구매자 1명 + 판매자 1명 + 매물 1건 + 채팅방 1개. 끝나면 롤백(형제 파일과 동일 패턴)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = _create_user(c, f"ci-seller-{uuid.uuid4()}@example.com", role="seller")
            buyer_id = _create_user(c, f"ci-buyer-{uuid.uuid4()}@example.com")
            listing_id = uuid.uuid4()
            _insert_listing(c, listing_id, seller_id)
            room_id = _insert_chat_room(c, listing_id, buyer_id, buyer_id)
            c.execute("select seller_id from public.chat_rooms where id = %s", (room_id,))
            assert c.fetchone()[0] == seller_id, "0016 트리거가 seller_id를 강제하지 않았다(회귀)"
            yield c, room_id, buyer_id, seller_id, listing_id
        conn.rollback()


def test_unread_count_excludes_own_messages_counts_counterpart_only(seeded):
    """① I/O 매트릭스 "내 발신만 있는 방" + FR57 공식의 sender_id<>auth.uid() 축.
    seller가 2건, buyer가 1건 보낸 방에서, buyer의 안읽음은 2(seller 메시지만), seller의
    안읽음은 1(buyer 메시지만)이어야 한다 — 자기 발신은 양쪽 다 제외된다."""
    cur, room_id, buyer_id, seller_id, _listing_id = seeded

    _insert_message(cur, room_id, seller_id, "문의 감사합니다")
    _insert_message(cur, room_id, seller_id, "네고 가능합니다")
    _insert_message(cur, room_id, buyer_id, "안녕하세요 문의드립니다")

    assert _unread_count_as(cur, buyer_id) == 2, "buyer는 seller가 보낸 2건만 안읽음이어야 한다"
    assert _unread_count_as(cur, seller_id) == 1, "seller는 buyer가 보낸 1건만 안읽음이어야 한다"


def test_unread_count_cutoff_is_strictly_after_last_read_at(seeded):
    """② FR57 공식의 `created_at > last_read_at`이 strict `>`다 — 정확히 그 시각인 메시지는
    안읽음이 아니고, 그 이후 메시지만 안읽음이다(CR6류 경계값과 정반대 방향이라 특히 헷갈리기
    쉬운 축 — 갭보정의 `gte`와 혼동하면 회귀가 조용히 들어온다)."""
    cur, room_id, buyer_id, seller_id, _listing_id = seeded

    # buyer가 이 방을 "지금" 읽었다고 기록한다.
    cur.execute(
        "insert into public.chat_room_reads (user_id, room_id, last_read_at) "
        "values (%s, %s, now()) returning last_read_at",
        (buyer_id, room_id),
    )
    (read_at,) = cur.fetchone()

    # 정확히 그 시각의 메시지 — 안읽음이 아니어야 한다(strict >).
    _insert_message(cur, room_id, seller_id, "읽은 시각과 정확히 같은 메시지", created_at=read_at)
    assert _unread_count_as(cur, buyer_id) == 0, "last_read_at과 정확히 같은 시각은 안읽음이 아니어야 한다"

    # 그 이후 메시지 — 안읽음이어야 한다.
    _insert_message(
        cur, room_id, seller_id, "그 이후 메시지", created_at=read_at + timedelta(seconds=1)
    )
    assert _unread_count_as(cur, buyer_id) == 1, "읽은 시각 이후 메시지는 안읽음이어야 한다"


def test_chat_room_reads_insert_rejects_non_participant(seeded):
    """③ chat_room_reads_insert_participant RLS — 그 방의 당사자가 아닌 사용자는 읽음 행을
    만들 수 없다. "정책이 있다"가 아니라 "실제로 거른다"를 실측한다(B4)."""
    cur, room_id, _buyer_id, _seller_id, _listing_id = seeded
    outsider_id = _create_user(cur, f"ci-outsider-{uuid.uuid4()}@example.com")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with cur.connection.transaction():
            cur.execute(f"set local request.jwt.claim.sub = '{outsider_id}'")
            cur.execute("set local role authenticated")
            cur.execute(
                "insert into public.chat_room_reads (user_id, room_id) values (%s, %s)",
                (outsider_id, room_id),
            )
    assert exc_info.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc_info.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(#211류 환경 붕괴)일 수 있다"
    )


def test_chat_room_reads_select_own_hides_other_users_rows(seeded):
    """④ chat_room_reads_select_own RLS — buyer는 자기 읽음 행만 보고, seller의 읽음 행은
    (같은 방이라도) 보이지 않는다."""
    cur, room_id, buyer_id, seller_id, _listing_id = seeded

    cur.execute(
        "insert into public.chat_room_reads (user_id, room_id) values (%s, %s), (%s, %s)",
        (buyer_id, room_id, seller_id, room_id),
    )

    with cur.connection.transaction():
        cur.execute(f"set local request.jwt.claim.sub = '{buyer_id}'")
        cur.execute("set local role authenticated")
        try:
            cur.execute("select user_id from public.chat_room_reads where room_id = %s", (room_id,))
            visible = {row[0] for row in cur.fetchall()}
        finally:
            try:
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass

    assert visible == {buyer_id}, "buyer가 seller의 읽음 행까지 봐서는 안 된다(RLS 누수)"


def test_chat_room_reads_update_cannot_retarget_to_non_participant_room(seeded):
    """⑤ 코드리뷰 patch 회귀 검사 — chat_room_reads_update_own이 참여자 재검증 없이
    `auth.uid() = user_id`만 봤다면, 이 UPDATE(자기 행의 room_id를 자신이 당사자 아닌 방으로
    재지정)가 **통과**했을 것이다. 패치 후에는 거부돼야 한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    # buyer가 당사자가 아닌 두 번째 방(다른 매물·다른 판매자·다른 구매자)을 만든다.
    other_seller_id = _create_user(cur, f"ci-seller2-{uuid.uuid4()}@example.com", role="seller")
    other_buyer_id = _create_user(cur, f"ci-buyer2-{uuid.uuid4()}@example.com")
    other_listing_id = uuid.uuid4()
    _insert_listing(cur, other_listing_id, other_seller_id)
    other_room_id = _insert_chat_room(cur, other_listing_id, other_buyer_id, other_buyer_id)

    cur.execute(
        "insert into public.chat_room_reads (user_id, room_id) values (%s, %s)",
        (buyer_id, room_id),
    )

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with cur.connection.transaction():
            cur.execute(f"set local request.jwt.claim.sub = '{buyer_id}'")
            cur.execute("set local role authenticated")
            cur.execute(
                "update public.chat_room_reads set room_id = %s where user_id = %s and room_id = %s",
                (other_room_id, buyer_id, room_id),
            )
    assert exc_info.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc_info.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(#211류 환경 붕괴)일 수 있다"
    )


def test_unread_count_excludes_rooms_i_am_not_a_participant_of(seeded):
    """⑦ FR57 공식의 "**내가 당사자인 방**" 축(0025 회귀 검사).

    0024는 이 조건을 SQL에 쓰지 않고 "SECURITY INVOKER라 호출자 RLS가 이미 자기 방만 보여준다"에
    맡겼다. 이 테스트는 그 전제를 실제로 확인한다 — 남의 방 메시지가 DB에 존재하는 상태에서
    카운트가 흔들리지 않아야 한다. (양성 대조: 자기 방 메시지는 같은 시나리오에서 실제로 세진다 —
    아니면 "아무것도 안 세어서" 통과하는 검사가 된다.)"""
    cur, room_id, buyer_id, seller_id, _listing_id = seeded

    # buyer가 당사자가 아닌 제3의 방과 그 안의 메시지.
    other_seller_id = _create_user(cur, f"ci-oseller-{uuid.uuid4()}@example.com", role="seller")
    other_buyer_id = _create_user(cur, f"ci-obuyer-{uuid.uuid4()}@example.com")
    other_listing_id = uuid.uuid4()
    _insert_listing(cur, other_listing_id, other_seller_id)
    other_room_id = _insert_chat_room(cur, other_listing_id, other_buyer_id, other_buyer_id)
    _insert_message(cur, other_room_id, other_seller_id, "남의 방 메시지 1")
    _insert_message(cur, other_room_id, other_buyer_id, "남의 방 메시지 2")

    assert _unread_count_as(cur, buyer_id) == 0, "당사자가 아닌 방의 메시지가 안읽음에 잡혔다"

    # 양성 대조 — 자기 방 메시지는 세어진다(위 0이 "카운트가 죽어서"가 아님을 증명).
    _insert_message(cur, room_id, seller_id, "내 방 메시지")
    assert _unread_count_as(cur, buyer_id) == 1, "자기 방 메시지는 안읽음으로 세어져야 한다"


def test_unread_count_does_not_leak_all_messages_to_admin(seeded):
    """⑧ 0025 회귀 검사(실측으로 발견된 결함).

    0005_admin_policies.sql의 `chat_messages_select_admin (using is_admin())`은 참여자 정책과
    **OR로 합쳐진다** — 즉 관리자에게는 모든 메시지가 보인다. 그래서 참여자 조건을 RLS에만
    맡기면(0024), 관리자가 소비자 화면을 열 때 배지가 "플랫폼 전체 메시지 수"가 된다
    (로컬 실측: 참여 방 0개인 관리자에게 chat_unread_count() = 10 = 전체 메시지 수).
    0025가 chat_rooms 조인을 함수 안에 되돌린 뒤에는 0이어야 한다."""
    cur, room_id, _buyer_id, seller_id, _listing_id = seeded

    # 가입 트리거는 admin 역할을 메타데이터로 받지 않는다(0028 이후 'user'로 떨어진다 —
    # 0028 이전엔 같은 자리에서 'buyer'였다, Story 14.2). 관리자는
    # 운영자가 승격시키는 역할이므로 profiles를 직접 올린다(is_admin()이 보는 것이 이 컬럼이다).
    admin_id = _create_user(cur, f"ci-admin-{uuid.uuid4()}@example.com")
    cur.execute("update public.profiles set role = 'admin' where id = %s", (admin_id,))

    _insert_message(cur, room_id, seller_id, "관리자와 무관한 대화 1")
    _insert_message(cur, room_id, seller_id, "관리자와 무관한 대화 2")

    # 전제 확인 ① 관리자는 이 방의 당사자가 아니다.
    cur.execute(
        "select count(*) from public.chat_rooms where id = %s and (buyer_id = %s or seller_id = %s)",
        (room_id, admin_id, admin_id),
    )
    assert cur.fetchone()[0] == 0, "테스트 전제 붕괴 — 관리자가 이 방의 당사자다"

    # 전제 확인 ② 이 사용자가 실제로 is_admin()이다 — 아니면 이 검사는 "관리자 축"을 안 본 채
    # 통과하는 검사가 된다(일반 사용자로는 애초에 새지 않으므로).
    with cur.connection.transaction():
        cur.execute(f"set local request.jwt.claim.sub = '{admin_id}'")
        cur.execute("set local role authenticated")
        try:
            cur.execute("select public.is_admin()")
            assert cur.fetchone()[0] is True, "테스트 전제 붕괴 — is_admin()이 false다"
        finally:
            try:
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass

    assert _unread_count_as(cur, admin_id) == 0, (
        "관리자 배지에 남의 대화가 집계됐다 — chat_unread_count()의 참여자 조건 회귀(0025)"
    )


def test_participant_can_actually_write_and_update_own_read_row(seeded):
    """⑨ 성공 경로 RLS·GRANT 검사(후속 코드리뷰 patch).

    기존 검사들은 **거부**만 authenticated 롤로 확인하고, 통과해야 하는 쓰기는 전부 DSN
    소유자(postgres) 권한으로 실행했다 — RLS도 GRANT도 우회하는 경로다. 그래서 정책이 너무
    좁아지거나 authenticated의 테이블 GRANT가 빠져 **정상 사용자의 읽음 기록이 막히는** 회귀는
    어떤 검사도 잡지 못했다(대장 #211이 실측한 로컬 붕괴가 정확히 이 축이었다). 그 상태의
    증상은 조용하다 — markChatRoomRead는 실패를 콘솔 로그로만 삼키므로 화면은 멀쩡하고
    배지만 영원히 안 줄어든다.

    여기서는 실제 앱이 보내는 문장 그대로(upsert = INSERT ... ON CONFLICT DO UPDATE) 검증한다."""
    cur, room_id, buyer_id, _seller_id, _listing_id = seeded

    with cur.connection.transaction():
        cur.execute(f"set local request.jwt.claim.sub = '{buyer_id}'")
        cur.execute("set local role authenticated")
        try:
            # ① 최초 진입 — INSERT 경로가 실제로 통과해야 한다.
            cur.execute(
                "insert into public.chat_room_reads (user_id, room_id) values (%s, %s) "
                "returning last_read_at",
                (buyer_id, room_id),
            )
            (first_read_at,) = cur.fetchone()

            # ② 재진입 — markChatRoomRead의 upsert가 보내는 ON CONFLICT DO UPDATE 경로.
            cur.execute(
                "insert into public.chat_room_reads (user_id, room_id, last_read_at) "
                "values (%s, %s, %s) "
                "on conflict (user_id, room_id) do update set last_read_at = excluded.last_read_at "
                "returning last_read_at",
                (buyer_id, room_id, first_read_at + timedelta(seconds=5)),
            )
            (second_read_at,) = cur.fetchone()
        finally:
            try:
                cur.execute("reset role")
            except psycopg.errors.InFailedSqlTransaction:
                pass

    assert second_read_at > first_read_at, "재진입 upsert가 last_read_at을 갱신하지 못했다"


def test_last_message_at_trigger_is_monotonic_despite_out_of_order_commit(seeded):
    """⑥ 코드리뷰 patch 회귀 검사 — 트리거가 무조건 덮어썼다면(patch 전), 시각이 더 이른
    메시지가 나중에 INSERT될 때 last_message_at이 그 이전 시각으로 **후퇴**했을 것이다.
    patch 후에는 greatest()로 단조증가만 허용해 되돌아가지 않아야 한다(시드 스크립트가
    실제로 겪은 현상과 동일한 시나리오를 여기서 고정한다)."""
    cur, room_id, buyer_id, seller_id, _listing_id = seeded

    cur.execute("select now()")
    (now_ish,) = cur.fetchone()

    # ⚠️ later를 now()와 **같게** 두면 이 테스트가 통째로 공허해진다(후속 코드리뷰 patch, 실측).
    #    chat_rooms.last_message_at의 기본값이 `now()`이고 픽스처 전체가 한 트랜잭션이라
    #    now()는 트랜잭션 시작 시각으로 고정된다 — 즉 방을 만든 순간 이미 last_message_at == now()다.
    #    그 상태에서 later = now_ish로 두면 **트리거를 통째로 비활성화해도** 아래 두 단언이 전부
    #    통과한다(실제로 `alter table ... disable trigger`로 재현해 확인). 기본값보다 확실히 뒤인
    #    시각을 써야 "트리거가 값을 실제로 옮겼다"가 증명된다.
    later = now_ish + timedelta(hours=1)
    earlier = now_ish - timedelta(hours=1)

    # 전제 확인 — 방의 초기값(기본값 now())은 later와 달라야 한다. 같으면 아래 단언이 트리거
    # 유무와 무관하게 통과하는 공허한 검사가 된다.
    cur.execute("select last_message_at from public.chat_rooms where id = %s", (room_id,))
    assert cur.fetchone()[0] != later, "테스트 전제 붕괴 — 방 초기값이 이미 later다(검사가 공허해진다)"

    # 늦은 시각 메시지를 먼저 INSERT.
    _insert_message(cur, room_id, buyer_id, "나중 시각 메시지", created_at=later)
    cur.execute("select last_message_at from public.chat_rooms where id = %s", (room_id,))
    assert cur.fetchone()[0] == later, (
        "트리거가 last_message_at을 새 메시지 시각으로 옮기지 못했다 — 트리거 자체의 회귀"
    )

    # 그 다음, 시각상 더 이른 메시지를 INSERT(out-of-order 커밋 시뮬레이션).
    _insert_message(cur, room_id, seller_id, "이전 시각 메시지(늦게 도착)", created_at=earlier)
    cur.execute("select last_message_at from public.chat_rooms where id = %s", (room_id,))
    (result,) = cur.fetchone()

    assert result == later, (
        f"last_message_at이 더 이른 시각({earlier})으로 후퇴했다 — greatest() 가드 회귀 "
        f"(실제 값: {result})"
    )


# ── ⑩ 0024 백필문 자체를 데이터가 있는 DB에서 실행해 본다 ─────────────────────
#
# 왜 필요한가(후속 코드리뷰 verification-gap 지적, 실측):
#   CI의 api-db 잡도, migration-gate의 동적 프로브도 **빈 Postgres**에 마이그레이션을 적용한다.
#   즉 0024:81-85의 백필 UPDATE는 어느 검사에서도 항상 0행에 대해 실행돼, 그 공식이 맞는지는
#   한 번도 관측되지 않는다. `max(`를 `min(`으로 바꿔도, `coalesce(..., r.created_at)` 폴백을
#   지워도 전 CI 잡이 초록이다. 그런데 이 문장은 **운영 DB에 이미 쌓인 방 전체의 정렬 기준을
#   한 번에 정하는** 일회성 코드다 — 틀리면 롤아웃 순간 모든 방이 잘못 정렬되거나(min), 메시지
#   없는 방에서 NOT NULL 위반으로 마이그레이션이 배포 도중 죽는다(폴백 삭제).
#
# 어떻게 보는가: 공식을 여기 다시 적지 않는다(그러면 사본이 늘어 같이 틀린다 — 대장 #146의 교훈).
#   **마이그레이션 파일에서 그 문장을 그대로 읽어와 실행**하고, 기대값은 파이썬이 독립적으로
#   계산해 대조한다. 파일의 공식이 바뀌면 이 검사가 실제로 그 바뀐 공식을 돌려보고 red가 된다.

_MIGRATION_0024 = (
    Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "0024_chat_room_reads.sql"
)


def _extract_backfill_statement() -> str:
    """0024에서 last_message_at 백필 UPDATE 한 문장을 원문 그대로 떼어 온다."""
    sql = _MIGRATION_0024.read_text(encoding="utf-8")
    start = sql.index("update public.chat_rooms r")
    end = sql.index(";", start)
    return sql[start : end + 1]


def test_0024_backfill_recomputes_last_message_at_for_existing_rows(seeded):
    """⑩ 백필 공식이 (a) 그 방의 **마지막** 메시지 시각을 고르고 (b) 메시지 없는 방은
    chat_rooms.created_at으로 떨어지는지를, 실제 데이터가 있는 상태에서 확인한다."""
    cur, room_id, buyer_id, seller_id, listing_id = seeded

    # (a) 메시지가 있는 방 — 시각을 일부러 뒤섞어 넣는다(가장 늦은 것이 정답).
    cur.execute("select now()")
    (base,) = cur.fetchone()
    newest = base + timedelta(hours=3)
    _insert_message(cur, room_id, buyer_id, "중간", created_at=base + timedelta(hours=1))
    _insert_message(cur, room_id, seller_id, "가장 늦음", created_at=newest)
    _insert_message(cur, room_id, buyer_id, "가장 이름", created_at=base - timedelta(hours=5))

    # (b) 메시지가 하나도 없는 방. chat_rooms에 (listing_id, buyer_id, seller_id) 유니크 제약이
    #     있어 같은 매물로는 두 번째 방을 못 만든다 — 같은 판매자의 매물을 하나 더 만든다.
    other_listing_id = uuid.uuid4()
    _insert_listing(cur, other_listing_id, seller_id)
    empty_room_id = _insert_chat_room(cur, other_listing_id, buyer_id, buyer_id)
    cur.execute("select created_at from public.chat_rooms where id = %s", (empty_room_id,))
    (empty_room_created_at,) = cur.fetchone()

    # 두 방 모두 값을 확실히 틀리게 만들어 둔다 — 이렇게 해야 "백필이 실제로 다시 계산했다"가
    # 증명된다(트리거가 이미 맞춰둔 값을 보고 통과하는 공허한 검사가 되지 않게).
    bogus = base - timedelta(days=365)
    cur.execute(
        "update public.chat_rooms set last_message_at = %s where id in (%s, %s)",
        (bogus, room_id, empty_room_id),
    )

    cur.execute(_extract_backfill_statement())

    cur.execute("select last_message_at from public.chat_rooms where id = %s", (room_id,))
    assert cur.fetchone()[0] == newest, (
        "백필이 그 방의 마지막 메시지 시각을 고르지 못했다 — max() 회귀(min이면 가장 이른 값이 들어온다)"
    )

    cur.execute("select last_message_at from public.chat_rooms where id = %s", (empty_room_id,))
    assert cur.fetchone()[0] == empty_room_created_at, (
        "메시지 없는 방의 백필이 chat_rooms.created_at으로 떨어지지 않았다 — coalesce 폴백 회귀"
    )
