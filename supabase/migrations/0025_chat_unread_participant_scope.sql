-- 0025_chat_unread_participant_scope.sql — chat_unread_count()에 "내가 당사자인 방" 조건을
-- 명시적으로 되돌린다 (Story 12.5 후속 코드리뷰 patch, FR57).
-- self-contained: public.chat_rooms/chat_messages(0003)·chat_room_reads(0024)에만 의존한다.
--
-- 왜 고치나 (실측):
--   0024의 chat_unread_count()는 SECURITY INVOKER라 "호출자의 RLS가 이미 자기 방만 보여준다"는
--   전제로 chat_rooms 조인을 생략했다. 그 전제가 **관리자에게는 성립하지 않는다** —
--   0005_admin_policies.sql의 chat_messages_select_admin(using (is_admin()))이 참여자 정책과
--   OR로 합쳐지므로, 관리자에게는 전체 메시지가 보인다. 그래서 관리자가 소비자 화면(/ 등, AppHeader
--   variant='consumer')을 열면 배지가 "플랫폼 전체 메시지 수"를 표시한다.
--
--   로컬 스택 실측(2026-07-29):
--     관리자(admin@test.com)가 당사자인 방 = 0개인데  chat_unread_count() = 10  (= 전체 메시지 수)
--     일반 구매자(buyer@test.com)                     chat_unread_count() = 0   (대조군, 정상)
--
--   FR57 AC와 docs/conventions.md §12.6이 규정한 공식은 원래부터 "**내가 당사자인 방**의
--   chat_messages 중 …"이다. 즉 이 파일은 새 규칙을 만드는 게 아니라 빠져 있던 조건을 복원한다.
--
-- 왜 0024를 고치지 않고 새 파일인가:
--   DB는 전진(forward-only)이다 — 잘못됐으면 뒤로 가지 말고 고치는 마이그를 하나 더 앞에 붙인다
--   (CLAUDE.md B3, docs/conventions.md §9.1). create or replace라 재적용도 멱등이고, 0024가
--   이미 적용된 환경·아직 안 된 fresh DB 양쪽에서 같은 최종 상태로 수렴한다.

create or replace function public.chat_unread_count()
returns integer
security invoker
stable
set search_path = ''
as $$
  select count(*)::int
  from public.chat_messages m
  join public.chat_rooms c
    on c.id = m.room_id
   and (c.buyer_id = auth.uid() or c.seller_id = auth.uid())
  left join public.chat_room_reads r
    on r.room_id = m.room_id and r.user_id = auth.uid()
  where m.sender_id <> auth.uid()
    and m.created_at > coalesce(r.last_read_at, '-infinity'::timestamptz);
$$
language sql;

comment on function public.chat_unread_count() is
  'Story 12.5(FR57): 로그인 사용자의 안읽음 메시지 총합(내가 당사자인 방 중 상대가 보낸, 마지막 열람 이후 메시지 수).
   SECURITY INVOKER. 참여자 조건은 chat_rooms 조인으로 함수 안에 명시한다(0025) — RLS에만 맡기면
   관리자 정책(0005 chat_messages_select_admin)이 OR로 합쳐져 전체 메시지가 집계된다(실측).
   authenticated 전용(anon은 배지를 계산하지 않는다).';

-- EXECUTE 권한은 0024가 정한 그대로(authenticated 전용) 유지된다 — create or replace는 기존
-- 권한을 보존하므로 여기서 다시 부여·회수하지 않는다(권한을 넓히지 않는다, §9.3).
