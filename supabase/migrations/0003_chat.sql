-- 0003_chat.sql — FR19~21 기반: 문의 채팅방·메시지 테이블 + 참여자 한정 RLS
-- 스키마 단일 출처(supabase/migrations/). 적용 순서: 0001 → 0002(+0002b/c/d) → 0003(이 파일) → 0004 → 0006.
--   (번호 갭 의도됨: 0003=chat(Epic5)·0005=admin(Epic6). 0004/0006 헤더가 이 예약을 명시.)
--
-- 이 마이그레이션이 하는 일:
--   1) chat_rooms 테이블 — 한 매물에 대한 구매자↔판매자 1:1 대화방.
--      · listing_id→listings, buyer_id/seller_id→profiles (0002 listings.seller_id가 profiles를 참조한 패턴과 동일)
--      · UNIQUE(listing_id, buyer_id, seller_id) — "한 매물·구매자·판매자 조합당 방 1개"(5-2 기존 방 재사용 토대)
--   2) chat_messages 테이블 — 방 안의 개별 메시지(room_id→chat_rooms, sender_id→profiles, body, created_at)
--   3) 참여자 한정 RLS — 같은 마이그레이션에 동거(0001·0002 원칙). 방의 당사자(buyer_id/seller_id)만 read/write, 제3자 차단.
--
-- ⚠️ ai_readonly 영향(0006): 0006의 `alter default privileges ... grant select to ai_readonly`로
--    이 두 테이블에도 ai_readonly의 테이블 SELECT 권한이 자동 부여된다. 그러나 chat 테이블에는
--    ai_readonly용 가시성 정책(using true)을 **만들지 않으므로**, RLS가 켜진 한 ai_readonly는 행을 0건만 본다.
--    (테이블 권한이 있어도 행 가시성 정책이 없으면 0건.) AI 검색은 chat을 조회하지 않으므로 이게 의도된 안전 동작이다.
--    → chat 테이블에 ai_readonly 정책을 추가하지 말 것.

-- ── 1) chat_rooms 테이블 ─────────────────────────────────────────────
-- if not exists: 재적용·신규 환경 재생성 시 "already exists"로 중단되지 않게(멱등).
create table if not exists public.chat_rooms (
  id          uuid primary key default gen_random_uuid(),
  listing_id  uuid not null references public.listings (id) on delete cascade,  -- 매물 삭제 시 방도 정리
  buyer_id    uuid not null references public.profiles (id) on delete cascade,  -- 구매자 = 문의를 연 쪽
  seller_id   uuid not null references public.profiles (id) on delete cascade,  -- 판매자 = 매물 소유자
  created_at  timestamptz not null default now(),
  -- 한 매물·구매자·판매자 조합당 방 1개 (5-2 "기존 방 재사용"이 이 키에 의존)
  unique (listing_id, buyer_id, seller_id)
);

comment on table public.chat_rooms is
  'FR19 문의 채팅방 — 한 매물에 대한 구매자↔판매자 1:1 대화방. (listing_id,buyer_id,seller_id) 조합당 1개(UNIQUE). RLS로 당사자만 접근.';
comment on column public.chat_rooms.buyer_id  is '구매자 = profiles.id. 문의를 연 쪽. 본인이 buyer 또는 seller일 때만 방을 보고/만든다(RLS).';
comment on column public.chat_rooms.seller_id is '판매자 = profiles.id(매물 소유자). 구매자와 함께 방의 당사자.';

-- ── 2) chat_messages 테이블 ──────────────────────────────────────────
create table if not exists public.chat_messages (
  id          uuid primary key default gen_random_uuid(),
  room_id     uuid not null references public.chat_rooms (id) on delete cascade,  -- 방 삭제 시 메시지도 정리
  sender_id   uuid not null references public.profiles (id) on delete cascade,    -- 보낸 사람 = 방의 당사자 중 하나
  body        text not null,                                                       -- 메시지 본문
  created_at  timestamptz not null default now()
);

comment on table public.chat_messages is
  'FR20·21 채팅 메시지 — 방 안의 개별 메시지(영속). sender_id는 방 당사자만(RLS). 폴링(3~5초)으로 상대가 읽음.';
comment on column public.chat_messages.room_id is '소속 방 = chat_rooms.id. RLS는 이 방의 당사자인지로 read/write를 판정한다.';

-- room_id로 메시지를 시간순 조회하는 폴링(5-3) 패턴 가속용 인덱스.
create index if not exists chat_messages_room_created_idx
  on public.chat_messages (room_id, created_at);

-- ── 3) chat_rooms RLS (참여자 한정) ──────────────────────────────────
-- 0001·0002와 동일 원칙: 정책은 해당 테이블 마이그레이션에 동거 → 적용 순서대로 RLS가 함께 존재.
-- 참여자 = buyer_id 또는 seller_id. auth.uid()가 둘 중 하나면 당사자.
alter table public.chat_rooms enable row level security;

-- SELECT: 당사자(구매자 또는 판매자)만 자기 방을 본다. 제3자는 0건.
create policy "chat_rooms_select_participant" on public.chat_rooms
  for select to authenticated
  using (auth.uid() = buyer_id or auth.uid() = seller_id);

-- INSERT: 자기를 당사자로 포함하는 방만 만들 수 있다(남의 방을 대신 못 만듦).
--   5-2에서 구매자가 buyer_id=본인으로 방을 여는 흐름과 정합. seller가 먼저 여는 경우도 seller_id=본인으로 허용.
create policy "chat_rooms_insert_participant" on public.chat_rooms
  for insert to authenticated
  with check (auth.uid() = buyer_id or auth.uid() = seller_id);

-- UPDATE/DELETE 정책 미설정 → 기본 거부(방 메타는 불변). 관리자 삭제권은 Epic6 0005_admin_policies(교차 정책)에서 추가.

-- ── 4) chat_messages RLS (방 당사자 한정) ────────────────────────────
-- chat_messages 자체엔 buyer/seller가 없으므로, 소속 방(chat_rooms)을 EXISTS로 조인해 당사자인지 판정한다.
--   · 이 서브쿼리는 다른 테이블(chat_rooms)을 참조하므로 0001에서 겪은 "자기참조 무한재귀"가 없다.
alter table public.chat_messages enable row level security;

-- SELECT: 메시지가 속한 방의 당사자만 읽는다.
create policy "chat_messages_select_participant" on public.chat_messages
  for select to authenticated
  using (
    exists (
      select 1 from public.chat_rooms r
      where r.id = chat_messages.room_id
        and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
    )
  );

-- INSERT: 보낸 사람이 본인(sender_id=auth.uid())이고 그 방의 당사자일 때만.
--   → 남의 명의로 메시지 위조 차단 + 당사자 아닌 방에 끼어들기 차단.
create policy "chat_messages_insert_participant" on public.chat_messages
  for insert to authenticated
  with check (
    auth.uid() = sender_id
    and exists (
      select 1 from public.chat_rooms r
      where r.id = chat_messages.room_id
        and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
    )
  );

-- UPDATE/DELETE 정책 미설정 → 메시지는 영속·불변(2-x "영속" 정신). 관리자 삭제는 Epic6 0005_admin_policies가 담당.
