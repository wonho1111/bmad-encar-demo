-- 0028_handle_new_user_default_role.sql — 가입 트리거 기본 role을 'user'로 (Story 14.2)
--
-- 왜: web 가입 화면(이 스토리)이 역할 선택 UI를 없애 더 이상 role metadata를 보내지 않는다.
--   그런데 0009의 handle_new_user는 metadata에 role이 없으면(또는 buyer/seller가 아니면)
--   'buyer'로 강제했다 — 통합된 계정 모델(FR52 "로그인만 하면 누구나 사고팔 수 있다")에
--   맞는 기본값이 아니다. 이 마이그는 그 기본값을 'user'로 바꾼다.
--   0027(Story 14.1)이 profiles.role의 3값 enum CHECK를 이미 걷어내 'user'가 저장 가능하다.
--
-- 무엇을: create or replace function으로 handle_new_user()를 교체한다(0001의 원본 정의자·
--   revoke execute(0001)·트리거 배선(0001)은 함수 객체가 그대로 유지되므로 다시 손댈 필요가
--   없다 — 0009가 이미 같은 방식으로 한 번 교체했다).
--   - metadata.role이 정확히 'buyer' 또는 'seller'면 그대로 반영한다(하위호환 — Flutter 앱은
--     이번 스토리에서 UI를 안 건드리므로 여전히 role metadata를 보낸다, spec Design Notes).
--   - 그 외(누락 포함, 'admin' 포함, 그 어떤 다른 문자열 포함)는 전부 'user'로 강제한다.
--     admin 승격 경로가 가입으로는 없어야 한다는 0001의 방어를 그대로 이어받는 것뿐이다
--     (0001 원본은 "buyer/seller 아니면 buyer" 였고, 이 마이그는 그 "아니면"의 착지점만
--     buyer → user로 바꾼다 — admin을 막는다는 목적은 동일).
--   - name(0009, 이메일 @앞부분) 기록·on conflict do nothing은 그대로 유지한다.
--
-- 기존 행은 건드리지 않는다(forward-only, CLAUDE.md B3) — 이 마이그는 함수 정의만 바꾸고
-- profiles를 UPDATE하지 않는다. 이미 가입된 buyer/seller/admin 계정의 role은 그대로 남는다.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_meta_role text := new.raw_user_meta_data ->> 'role';
  v_role text;
begin
  if v_meta_role in ('buyer', 'seller') then
    v_role := v_meta_role;
  else
    -- 누락·admin·그 외 임의 문자열은 전부 'user'로 강제(admin 승격 방어의 강화판).
    v_role := 'user';
  end if;

  insert into public.profiles (id, role, status, name)
  values (new.id, v_role, 'active', split_part(new.email, '@', 1))
  on conflict (id) do nothing;

  return new;
end;
$$;
