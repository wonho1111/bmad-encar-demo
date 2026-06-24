-- 0009_profiles_name.sql — profiles에 표시 이름(이메일 @앞부분) 추가
-- 적용 순서: … → 0007 → 0008 → 0009(이 파일).
--
-- 왜 필요한가:
--   관리자 회원 관리(/admin/members)에서 회원을 UUID 앞 8자 대신 "이름"으로 식별하고 싶다.
--   profiles엔 이메일/이름이 없고(이메일은 auth.users 소관), 관리자도 anon-key로 타인 auth.users를 못 읽는다.
--   하지만 관리자는 profiles 전체를 읽을 수 있으므로(profiles_select_admin, 0001), profiles에 표시 이름을
--   복사 저장해 두면 회원 관리에서 바로 쓸 수 있다(0007 listings.seller_name·0008 chat_rooms와 동일 패턴).
--
-- 표시 이름 = 이메일 '@' 앞부분(0007·0008과 동일 규칙). ⚠️ 데모 식별용 — 운영 전 개인정보 노출 재검토.
--
-- 채우는 방식: 가입 트리거(handle_new_user, auth.users AFTER INSERT)가 new.email에서 로컬파트를 함께 기록.
--   (handle_new_user는 auth.users 트리거라 new.email을 바로 읽을 수 있어 별도 조회가 필요 없다.)

alter table public.profiles add column if not exists name text;
comment on column public.profiles.name is '표시 이름 = 이메일 @앞부분(가입 트리거 자동기록). 관리자 회원 식별용 데모 표시 — 운영 전 재검토.';

-- handle_new_user 갱신(0001 원본 + name 기록). 역할 강제·on conflict 동작은 그대로 유지.
--   create or replace는 같은 함수 객체를 유지하므로 0005의 EXECUTE 회수(grant 회수)도 그대로 보존된다.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_role text := coalesce(new.raw_user_meta_data ->> 'role', 'buyer');
begin
  if v_role not in ('buyer', 'seller') then
    v_role := 'buyer';
  end if;

  -- role에 더해 표시 이름(이메일 @앞부분)도 함께 기록. on conflict: 재시도/리플레이 시 PK 충돌 무시.
  insert into public.profiles (id, role, status, name)
  values (new.id, v_role, 'active', split_part(new.email, '@', 1))
  on conflict (id) do nothing;

  return new;
end;
$$;

-- 기존 회원 백필(이미 가입된 회원은 갱신 전 트리거라 name이 비어 있다).
update public.profiles p
set name = split_part(u.email, '@', 1)
from auth.users u
where u.id = p.id and p.name is null;
