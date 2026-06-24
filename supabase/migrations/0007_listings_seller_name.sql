-- 0007_listings_seller_name.sql — 매물 목록에 "판매자 표시 이름"(이메일 @앞부분) 비정규화
-- 적용 순서: 0001 → 0002 → 0003 → 0003c → 0004 → 0005 → 0006 → 0007(이 파일).
--
-- 왜 필요한가:
--   매물 목록(/search·홈 미리보기)에서 판매자를 식별할 수 있게 "판매자 이름"을 보여주고 싶다.
--   그런데 이름 컬럼이 없고(profiles엔 role/status만), 구매자는 RLS상 남의 profiles/auth.users를
--   읽지 못한다(본인 행만). 그래서 조회 시점에 조인으로 가져올 수 없다.
--   → 매물 행에 판매자의 표시 이름을 복사 저장(비정규화)한다. listings는 on_sale이 모두에게
--     공개(RLS)라, 컬럼만 추가하면 추가 권한 없이 목록과 함께 노출된다.
--
-- 표시 이름 = 판매자 이메일의 '@' 앞부분(예: seller-seed2@test.com → "seller-seed2").
--   별도 이름 컬럼·가입 폼 변경 없이 데모 식별용으로만 쓴다.
--   ⚠️ 이메일 로컬파트가 목록에 공개되므로 개인정보 측면이 있다 — 운영 전 재검토(데모 한정).
--
-- 채우는 방식: BEFORE INSERT 트리거가 seller_id의 auth.users.email에서 로컬파트를 추출해 강제 기록한다.
--   클라이언트 입력을 신뢰하지 않고 DB가 권위 있는 값을 도출(0003c enforce_chat_room_seller와 동일 철학).
--   seller_id는 INSERT RLS(with check auth.uid()=seller_id)로 위조 불가 → 표시 이름도 위조 불가.

alter table public.listings add column if not exists seller_name text;
comment on column public.listings.seller_name is
  '판매자 표시 이름 = auth.users.email의 @앞부분(비정규화, 트리거로 자동 기록). 목록 식별용 데모 표시 — 운영 전 개인정보 노출 재검토.';

-- seller_id의 이메일 로컬파트를 seller_name에 강제 기록(클라 입력 무시).
-- security definer: auth.users를 읽어야 하는데 호출자(판매자)는 자기 행만 보이므로, 정의자 권한으로 읽는다.
--   search_path를 public로 고정(정의자 함수 하이재킹 방지). auth.users는 스키마 명시로 참조한다.
create or replace function public.set_listing_seller_name()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  select split_part(email, '@', 1) into new.seller_name
  from auth.users
  where id = new.seller_id;
  return new;
end;
$$;

comment on function public.set_listing_seller_name() is
  'listings BEFORE INSERT: seller_name을 seller_id의 이메일 @앞부분으로 강제(비정규화·위조 차단).';

-- 트리거 전용 함수의 RPC 노출·직접 호출 차단(0003c 패턴). 트리거는 테이블 소유자 권한으로 발화하므로 회수 후에도 동작.
revoke all on function public.set_listing_seller_name() from public;
revoke all on function public.set_listing_seller_name() from anon;
revoke all on function public.set_listing_seller_name() from authenticated;

drop trigger if exists listings_set_seller_name on public.listings;
create trigger listings_set_seller_name
  before insert on public.listings
  for each row execute function public.set_listing_seller_name();

-- 기존 매물 백필(이미 등록된 행은 트리거가 안 돌았으므로 1회 채운다).
update public.listings l
set seller_name = split_part(u.email, '@', 1)
from auth.users u
where u.id = l.seller_id and l.seller_name is null;
