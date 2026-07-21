-- 0003c_chat_room_integrity.sql — chat_rooms 무결성 트리거 (코드리뷰 [Decision] 옵션 A, 사용자 승인)
-- 적용 순서: 0001 → 0002(+0002b/c/d) → 0003 → 0003b → 0003c(이 파일) → 0004 → 0006.
--
-- 왜 필요한가(코드리뷰 High 지적):
--   0003의 chat_rooms INSERT RLS는 "만드는 사람이 buyer 또는 seller 둘 중 하나"이기만 하면 통과한다.
--   그래서 구매자가 임의의 seller_id(아무 프로필)·임의의 listing_id를 적어 넣어도 DB가 막지 못해,
--   "모르는 사람에게 원치 않는 방을 강제 생성"하거나 (매물,판매자) 짝이 어긋난 방이 만들어질 수 있었다.
--
-- 이 마이그레이션이 하는 일(옵션 A — 프로젝트 방침 "무결성은 DB로 못박기", Story 2.1 DB측 가드 전례와 일치):
--   chat_rooms BEFORE INSERT 트리거가 seller_id를 **그 매물(listing_id)의 실제 소유자로 강제로 덮어쓴다.**
--   · 클라이언트가 보낸 seller_id 값은 무시 → 위조 벡터 원천 차단.
--   · 동시에 기획 흐름("상대를 고르지 않고 매물 주인에게 자동 연결")을 DB가 보장한다.
--   · 매물이 없으면(잘못된 listing_id) 거부.
--   · 구매자가 자기 매물에 문의하면 seller_id가 본인이 되어 기존 CHECK(buyer_id <> seller_id)로 자동 거부된다.
--
-- security definer 이유: 함수가 listings.seller_id를 조회해야 하는데, 호출자(구매자)는 RLS상
--   sold 매물 등을 못 볼 수 있다. definer(소유자 권한)로 실행해 소유자 조회가 항상 동작하게 한다.
--   search_path를 public으로 고정해 정의자 권한 함수의 search_path 하이재킹을 방지(보안 권고).

create or replace function public.enforce_chat_room_seller()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_owner uuid;
begin
  -- 그 매물의 실제 소유자를 조회(RLS 우회 — definer 권한).
  select seller_id into v_owner
  from public.listings
  where id = new.listing_id;

  -- 존재하지 않는 매물로 방을 만들려는 시도 거부.
  if v_owner is null then
    raise exception '존재하지 않는 매물로 채팅방을 만들 수 없습니다 (listing_id=%)', new.listing_id
      using errcode = '23503';  -- foreign_key_violation 계열
  end if;

  -- seller_id를 매물의 실제 소유자로 강제(클라이언트 입력 무시). 위조 차단 + "매물 주인 자동 연결".
  --   buyer = 소유자인 경우 seller_id가 buyer_id와 같아져 CHECK(buyer_id <> seller_id)가 잡아낸다.
  new.seller_id := v_owner;

  return new;
end;
$$;

comment on function public.enforce_chat_room_seller() is
  'chat_rooms BEFORE INSERT: seller_id를 매물(listing_id)의 실제 소유자로 강제. 위조 차단 + 매물주 자동 연결(코드리뷰 옵션A).';

-- 트리거 함수는 클라이언트가 직접 호출할 필요가 없다. PostgREST가 public 함수를 /rest/v1/rpc로 자동 노출하므로
--   default EXECUTE(PUBLIC) 권한을 회수해 RPC 노출·SECURITY DEFINER 직접 호출 경로를 차단한다(advisor 0028/0029).
--   트리거는 테이블 소유자 권한으로 발화하므로 EXECUTE 회수 후에도 정상 동작한다.
--   Supabase는 anon/authenticated에 EXECUTE를 직접 부여하므로 PUBLIC뿐 아니라 두 롤에서도 명시 회수한다.
revoke all on function public.enforce_chat_room_seller() from public;
revoke all on function public.enforce_chat_room_seller() from anon;
revoke all on function public.enforce_chat_room_seller() from authenticated;

drop trigger if exists chat_rooms_enforce_seller on public.chat_rooms;
create trigger chat_rooms_enforce_seller
  before insert on public.chat_rooms
  for each row execute function public.enforce_chat_room_seller();
