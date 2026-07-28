-- 0024_chat_room_reads.sql — 안읽음 배지 + 방 목록 정렬 토대 (Story 12.5, FR57)
-- self-contained: public.profiles(0001)·public.chat_rooms/chat_messages(0003)에만 의존한다.
--
-- 이 마이그레이션이 하는 일:
--   1) chat_room_reads 테이블 — 사용자별·방별 "마지막으로 읽은 시각". 복합 PK(user_id, room_id).
--      RLS: 본인 행만 select/update, insert는 그 방의 실제 당사자일 때만(0003
--      chat_rooms_insert_participant와 동일 EXISTS 패턴). delete 정책 없음(기본 거부).
--   2) chat_rooms.last_message_at 컬럼 — 방 목록 정렬 기준(방 생성순 대신 최신 메시지순).
--      기존 행은 그 방의 실제 마지막 chat_messages.created_at(메시지 없으면 chat_rooms.created_at)으로
--      백필한다(정렬이 롤아웃 즉시 정확해야 함). 이후 chat_messages AFTER INSERT 트리거(SECURITY
--      DEFINER — chat_rooms는 UPDATE 정책이 없어 authenticated로는 이 갱신이 불가능하다, 0016/0020과
--      동일한 이유)가 새 메시지의 created_at으로 갱신한다.
--   3) chat_unread_count() RPC — 인자 없음, SECURITY INVOKER(정의자 권한 불필요 — 호출자 자신의
--      RLS로 이미 자기 방·자기 메시지만 보이므로 그 위에서 집계해도 정확하다, A2 최소 권한).
--      공식(FR57 AC 그대로): 내가 당사자인 방의 chat_messages 중 sender_id <> auth.uid()이고
--      created_at > coalesce(그 방의 내 chat_room_reads.last_read_at, '-infinity')인 행의 개수.
--      authenticated에만 EXECUTE 부여(anon 회수 — 비로그인은 배지를 계산하지 않는다).

-- ── 1) chat_room_reads 테이블 ─────────────────────────────────────────
create table if not exists public.chat_room_reads (
  user_id      uuid not null references public.profiles (id) on delete cascade,
  room_id      uuid not null references public.chat_rooms (id) on delete cascade,
  last_read_at timestamptz not null default now(),
  primary key (user_id, room_id)
);

-- room_id 단독 조회(방 삭제 cascade) 가속 — PK가 user_id 선두라 room_id만으로는 이 인덱스가 필요
-- (0018 wishlists가 listing_id에 같은 이유로 별도 인덱스를 둔 것과 동일 패턴).
create index if not exists chat_room_reads_room_id_idx on public.chat_room_reads (room_id);

comment on table public.chat_room_reads is
  'Story 12.5(FR57) 사용자별·방별 마지막 열람 시각. 안읽음 집계(chat_unread_count)의 기준값. RLS로 본인 행만 접근.';
comment on column public.chat_room_reads.last_read_at is
  '방 진입 시(web/src/lib/chat.ts의 markChatRoomRead) 지금 시각으로 upsert. 그 값보다 늦고 상대가 보낸 메시지 수가 안읽음이다.';

alter table public.chat_room_reads enable row level security;

-- SELECT/UPDATE: 본인 행만(방은 안 바뀌는 값이라 참여자 재검증 불필요).
create policy "chat_room_reads_select_own" on public.chat_room_reads
  for select to authenticated
  using (auth.uid() = user_id);

-- UPDATE도 INSERT와 동일한 참여자 EXISTS 검사를 with check에 둔다(코드리뷰 patch, low) — 그냥
-- auth.uid() = user_id만 보면, 크래프트된 UPDATE로 room_id를 자신이 당사자 아닌 방으로 재지정해도
-- 통과한다(본인 행에 한정되므로 자해적일 뿐 타인에게 영향은 없지만, INSERT 정책과 방어 수준을 맞춘다).
create policy "chat_room_reads_update_own" on public.chat_room_reads
  for update to authenticated
  using (auth.uid() = user_id)
  with check (
    auth.uid() = user_id
    and exists (
      select 1 from public.chat_rooms r
      where r.id = chat_room_reads.room_id
        and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
    )
  );

-- INSERT: 본인 명의 + 그 방의 실제 당사자(buyer 또는 seller)일 때만 — 0003의
-- chat_rooms_insert_participant와 동일한 EXISTS 검사 패턴(남의 방에 읽음 행을 심지 못하게).
create policy "chat_room_reads_insert_participant" on public.chat_room_reads
  for insert to authenticated
  with check (
    auth.uid() = user_id
    and exists (
      select 1 from public.chat_rooms r
      where r.id = chat_room_reads.room_id
        and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
    )
  );

-- DELETE 정책 없음 → 기본 거부(읽음 상태를 지울 정당한 클라이언트 경로가 없다).

-- ── 2) chat_rooms.last_message_at 컬럼 + 백필 + 유지 트리거 ─────────────
alter table public.chat_rooms add column if not exists last_message_at timestamptz not null default now();

comment on column public.chat_rooms.last_message_at is
  'Story 12.5(FR57) 방 목록 정렬 기준(최신 문의 순). 유일한 쓰기 통로는 chat_messages_touch_room_last_message
   트리거(SECURITY DEFINER) — authenticated 직접 UPDATE는 chat_rooms에 UPDATE 정책이 없어 애초에 불가능하다.';

-- 백필: 재적용해도 항상 같은 결과로 수렴하는 멱등 UPDATE(현재 상태에서 다시 계산할 뿐이라 재실행 안전).
update public.chat_rooms r
set last_message_at = coalesce(
  (select max(m.created_at) from public.chat_messages m where m.room_id = r.id),
  r.created_at
);

-- search_path를 빈 문자열로 고정 — 정의자 권한 함수의 search_path 하이재킹 방지(0016·0023과 동일 원칙).
-- security definer 이유: chat_rooms는 UPDATE 정책이 미설정(방 메타는 불변, 0003 주석)이라 authenticated
-- 권한으로는 이 갱신이 통과하지 못한다 — 트리거가 테이블 소유자 권한(RLS 우회)으로 대신 쓴다(0020 동일 이유).
create or replace function public.chat_rooms_touch_last_message()
returns trigger
security definer
set search_path = ''
language plpgsql
as $$
begin
  -- greatest()로 단조증가만 허용(코드리뷰 patch, low) — 무조건 덮어쓰면, 시각 순서와 다르게
  -- 커밋되는 메시지(동시 전송 등)가 last_message_at을 더 이른 시각으로 되돌릴 수 있다(시드
  -- 스크립트가 대량 INSERT에서 실측한 것과 같은 현상). 방 목록 정렬 기준은 "지금까지 본 것 중
  -- 가장 늦은 시각"이어야 하므로, 되돌아가지 않게 고정한다.
  update public.chat_rooms
  set last_message_at = greatest(last_message_at, new.created_at)
  where id = new.room_id;
  return null;
end;
$$;

comment on function public.chat_rooms_touch_last_message() is
  'chat_messages AFTER INSERT: 그 방의 chat_rooms.last_message_at을 새 메시지 시각으로 갱신(Story 12.5, FR57 정렬 토대).';

-- 트리거 함수는 클라이언트가 직접 호출할 필요가 없다 — RPC 노출 차단(0016·0023과 동일 원칙).
revoke all on function public.chat_rooms_touch_last_message() from public;
revoke all on function public.chat_rooms_touch_last_message() from anon;
revoke all on function public.chat_rooms_touch_last_message() from authenticated;

drop trigger if exists chat_messages_touch_room_last_message on public.chat_messages;
create trigger chat_messages_touch_room_last_message
after insert on public.chat_messages
for each row execute function public.chat_rooms_touch_last_message();

-- ── 3) chat_unread_count() RPC (SECURITY INVOKER) ───────────────────────
-- invoker이므로 아래 select는 호출자 자신의 RLS 그대로 평가된다: chat_messages는 참여자 방만
-- 보이고(0003 chat_messages_select_participant), chat_room_reads는 본인 행만 보인다(위 정책).
-- 그래서 별도로 chat_rooms를 조인해 참여자를 재검증할 필요가 없다 — 두 RLS가 이미 그 경계를 긋는다.
create or replace function public.chat_unread_count()
returns integer
security invoker
stable
set search_path = ''
as $$
  select count(*)::int
  from public.chat_messages m
  left join public.chat_room_reads r
    on r.room_id = m.room_id and r.user_id = auth.uid()
  where m.sender_id <> auth.uid()
    and m.created_at > coalesce(r.last_read_at, '-infinity'::timestamptz);
$$
language sql;

comment on function public.chat_unread_count() is
  'Story 12.5(FR57): 로그인 사용자의 안읽음 메시지 총합(내가 당사자인 방 중 상대가 보낸, 마지막 열람 이후 메시지 수).
   SECURITY INVOKER — 정의자 권한 불필요(A2 최소 권한). authenticated 전용(anon은 배지를 계산하지 않는다).';

-- 새 함수의 EXECUTE는 기본으로 PUBLIC에 간다(그리고 Supabase는 anon/authenticated에도 직접 부여한다) —
-- 전부 회수한 뒤 authenticated에만 재부여한다(0016·0020과 동일 하드닝 패턴).
revoke all on function public.chat_unread_count() from public;
revoke all on function public.chat_unread_count() from anon;
revoke all on function public.chat_unread_count() from authenticated;
grant execute on function public.chat_unread_count() to authenticated;
