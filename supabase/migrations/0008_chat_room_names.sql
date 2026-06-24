-- 0008_chat_room_names.sql — 채팅방에 구매자·판매자 표시 이름(이메일 @앞부분) 비정규화
-- 적용 순서: 0001 → 0002 → 0003 → 0003c → 0004 → 0005 → 0006 → 0007 → 0008(이 파일).
--
-- 왜 필요한가:
--   채팅(구매자/판매자/관리자 화면)에서 상대를 이름으로 식별하고 싶다. 그런데 이름 컬럼이 없고
--   RLS상 남의 프로필/이메일을 못 읽어 조회 시 조인으로 가져올 수 없다(0007 listings.seller_name과 동일 사정).
--   특히 관리자 채팅은 그동안 식별 단서가 없어 buyer_id/seller_id의 UUID 앞 8자만 보여주고 있었다(6-5).
--   → chat_rooms 행에 양쪽 표시 이름을 복사 저장한다. 참여자/관리자 RLS로 방을 읽을 때 함께 노출된다.
--
-- 표시 이름 = 이메일 '@' 앞부분(0007과 동일 규칙). ⚠️ 데모 식별용 — 운영 전 개인정보 노출 재검토.
--
-- 채우는 방식: BEFORE INSERT 트리거가 buyer_id/seller_id의 auth.users.email에서 로컬파트를 기록한다.
--   seller_id는 0003c enforce_chat_room_seller가 먼저 매물 주인으로 강제하므로, 이 트리거는 그 "뒤"에
--   발화해 확정된 seller_id 기준으로 이름을 채워야 한다. BEFORE 트리거는 트리거명 알파벳 순으로 발화하는데
--   'chat_rooms_enforce_seller' < 'chat_rooms_set_names' 이라 enforce가 먼저 → 순서 보장됨.

alter table public.chat_rooms add column if not exists buyer_name text;
alter table public.chat_rooms add column if not exists seller_name text;
comment on column public.chat_rooms.buyer_name is '구매자 표시 이름 = 이메일 @앞부분(비정규화, 트리거 자동기록). 데모 식별용 — 운영 전 재검토.';
comment on column public.chat_rooms.seller_name is '판매자 표시 이름 = 이메일 @앞부분(비정규화, 트리거 자동기록). 데모 식별용 — 운영 전 재검토.';

-- buyer_id/seller_id의 이메일 로컬파트를 각각 기록. security definer로 auth.users를 읽는다(0007 패턴).
create or replace function public.set_chat_room_names()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  select split_part(email, '@', 1) into new.buyer_name  from auth.users where id = new.buyer_id;
  select split_part(email, '@', 1) into new.seller_name from auth.users where id = new.seller_id;
  return new;
end;
$$;

comment on function public.set_chat_room_names() is
  'chat_rooms BEFORE INSERT: buyer_name·seller_name을 각 당사자 이메일 @앞부분으로 기록(비정규화). enforce_chat_room_seller 뒤에 발화(트리거명 알파벳순).';

-- RPC 노출·직접 호출 차단(0003c·0007 패턴). 트리거는 테이블 소유자 권한으로 발화하므로 회수 후에도 동작.
revoke all on function public.set_chat_room_names() from public;
revoke all on function public.set_chat_room_names() from anon;
revoke all on function public.set_chat_room_names() from authenticated;

drop trigger if exists chat_rooms_set_names on public.chat_rooms;
create trigger chat_rooms_set_names
  before insert on public.chat_rooms
  for each row execute function public.set_chat_room_names();

-- 기존 방 백필(이미 만들어진 방은 트리거가 안 돌았으므로 1회 채운다).
update public.chat_rooms r
set buyer_name  = split_part(bu.email, '@', 1),
    seller_name = split_part(su.email, '@', 1)
from auth.users bu, auth.users su
where bu.id = r.buyer_id and su.id = r.seller_id;
