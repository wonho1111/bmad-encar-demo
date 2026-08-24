-- 0026_chat_unread_by_room.sql — 방별 안읽음 개수를 돌려주는 조회 함수 (사용자 요청 2026-07-29, 대장 DW-548).
-- self-contained: public.chat_rooms/chat_messages(0003)·chat_room_reads(0024)에만 의존한다.
--
-- 왜 지금 만드나:
--   Story 12.5(FR57)는 내비 배지에 **총합**만 표시하고 방 목록은 최신순 정렬만 했다. 스펙이
--   *"방 목록 각 행에 개별 안읽음 점(per-room indicator)을 추가하지 않는다 — FR57 AC가 요구하는 건
--   내비 배지(총합)와 정렬뿐이다(과설계 금지, A2)"* 로 **Never를 명시**했고, 코드리뷰에서 올라온
--   같은 제안도 그 근거로 기각됐다. 당시 판단은 맞았다 — FR57이 요구한 "판매자가 문의를 놓치지
--   않는다"는 총합+정렬로 충족된다.
--   다시 여는 이유는 사용 경험이다(사용자 지적): 총합 배지를 보고 목록에 들어가면 **어느 방이
--   새 메시지인지 알 수 없어** 배지가 절반만 일한다. 스펙의 Never를 뒤집는 것이므로 근거를 여기 남긴다.
--
-- 왜 기존 chat_unread_count()를 고치지 않고 새 함수인가:
--   반환 형태가 다르다(정수 1개 vs 방별 행 집합). 기존 함수는 내비 배지가 그대로 쓰고 있으므로
--   건드리지 않는다 — DB는 전진(forward-only), 더하기만 한다(CLAUDE.md B3).
--
-- 계산식은 chat_unread_count()(0025)와 **글자 그대로 같다** — `group by`와 반환 형태만 다르다.
--   두 배지가 다른 규칙으로 세면 "총합 3인데 방별 합이 2"처럼 화면이 스스로 모순된다.
--   특히 chat_rooms 조인("내가 당사자인 방")은 0025가 실측으로 되살린 조건이다: 관리자에게는
--   0005_admin_policies의 chat_messages_select_admin(using (is_admin()))이 OR로 합쳐져 전체 메시지가
--   보이므로, 이 조인이 없으면 관리자 화면에서 남의 방 메시지까지 세어진다.

create or replace function public.chat_unread_by_room()
returns table (room_id uuid, unread integer)
security invoker
stable
set search_path = ''
as $$
  select m.room_id, count(*)::int as unread
  from public.chat_messages m
  join public.chat_rooms c
    on c.id = m.room_id
   and (c.buyer_id = auth.uid() or c.seller_id = auth.uid())
  left join public.chat_room_reads r
    on r.room_id = m.room_id and r.user_id = auth.uid()
  where m.sender_id <> auth.uid()
    and m.created_at > coalesce(r.last_read_at, '-infinity'::timestamptz)
  group by m.room_id;
$$
language sql;

comment on function public.chat_unread_by_room() is
  'DW-548: 로그인 사용자의 **방별** 안읽음 메시지 수(상대가 보낸, 마지막 열람 이후). 안읽음이 0인 방은
   행 자체가 없다(group by 결과) — 호출부는 "없으면 0"으로 읽는다.
   계산식은 chat_unread_count()와 동일하며 group by만 다르다. SECURITY INVOKER — authenticated 전용.';

-- 새 함수의 EXECUTE는 기본으로 PUBLIC에 간다(그리고 Supabase는 anon/authenticated에도 직접 부여한다) —
-- 전부 회수한 뒤 authenticated에만 재부여한다(0016·0020·0024와 동일 하드닝 패턴).
revoke all on function public.chat_unread_by_room() from public;
revoke all on function public.chat_unread_by_room() from anon;
revoke all on function public.chat_unread_by_room() from authenticated;
grant execute on function public.chat_unread_by_room() to authenticated;
