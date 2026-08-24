-- 0022_chat_idempotency_key.sql — chat_messages 멱등키 (FR41, CR1, Story 12.1)
--
-- 왜: Epic 12가 폴링을 실시간 전송으로 바꾸면(Story 12.3), 네트워크가 끊긴 채 클라이언트가
--   재전송하면 같은 메시지가 두 번 저장될 수 있다. 이 스토리는 그 중복을 막을 DB 토대만
--   놓는다 — 클라이언트가 client_message_id를 실제로 채워 보내는 것도, 그것을 이용한
--   `INSERT ... ON CONFLICT DO NOTHING` SQL도 전부 Story 12.3 범위다.
--
-- 이 마이그레이션이 하는 일:
--   chat_messages에 nullable client_message_id uuid 컬럼 + UNIQUE(room_id, client_message_id)
--   제약을 추가한다. 기본값·백필 없음(I13, additive만) — 기존 행은 client_message_id가
--   NULL로 남고, Postgres UNIQUE 제약은 NULL끼리 서로 다른 값으로 취급하므로 기존 행이
--   몇 건이든 이 제약과 충돌하지 않는다(Design Notes 참조).
--
-- self-contained: 0003_chat.sql(chat_messages 원본)에만 의존한다. 0022보다 큰 번호(아직
--   존재하지 않는, 이후에 생길 마이그)에는 의존하지 않는다 — 0020·0021(listings view_count)은
--   이미 이보다 작은 번호로 먼저 적용돼 있으므로 반대 사례가 아니라 그냥 선행 마이그일 뿐이다.
--
-- if not exists(컬럼)·do $$ if not exists(제약): **이 파일은** 재적용해도 "already exists"로
--   중단되지 않는다(멱등). 레포 전체의 관례는 아니다 — 예컨대 0010은 맨 `add constraint`라
--   두 번 적용하면 에러로 멈춘다(실측). 마이그를 두 번 적용하는 검사도 아직 없다(대장 #143).

alter table public.chat_messages
  add column if not exists client_message_id uuid;

comment on column public.chat_messages.client_message_id is
  'FR41 멱등키 — 클라이언트가 메시지마다 생성하는 랜덤 id(crypto.randomUUID() 관례, Story 12.3에서
   실제로 채움). nullable·기본값 없음(I13). UNIQUE(room_id, client_message_id)와 함께 재전송
   중복 저장을 막는 토대. NULL은 미도입 구간 메시지(과거 행) — 서로 충돌하지 않는다.';

-- postgres에는 "add constraint if not exists"가 없다. 선택지는 둘이었다:
--   (1) create unique index if not exists — 한 줄이고 네이티브 멱등. ON CONFLICT 추론에도 충분하다.
--   (2) 이름 있는 테이블 제약 + do $$ if not exists $$ 가드 — 아래가 이것.
-- (2)를 고른 이유: chat_messages의 기존 무결성 규칙(0003 빈본문·0010 길이·0003 buyer<>seller)이
-- 전부 **이름 있는 제약**이라 `pg_constraint` 한 곳에서 같이 보인다. 인덱스로 두면 이 테이블의
-- 규칙만 두 군데로 흩어진다. 대신 가드가 이름(conname)을 키로 쓰므로 **이름을 바꾸면 재적용 시
-- 중복 제약이 생긴다** — 그래서 test_chat_idempotency_real_db.py가 이름·정의를 직접 단언한다.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'chat_messages_room_client_message_unique'
      and conrelid = 'public.chat_messages'::regclass
  ) then
    alter table public.chat_messages
      add constraint chat_messages_room_client_message_unique
      unique (room_id, client_message_id);
  end if;
end $$;
