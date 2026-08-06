-- 0029_unify_existing_account_roles.sql — 기존 계정의 buyer/seller 구분을 없앤다 (역할 통합 마무리)
--
-- 왜: 0027이 CHECK를 풀고 0028이 신규 가입 기본값을 'user'로 바꿨지만, **이미 있던 계정은
--   그대로 buyer/seller로 남아 있다.** 그래서 계정 모집단이 갈라져 있다 —
--   옛 가입자(buyer/seller) vs 14.2 이후 가입자(user). 화면에는 "구매자"·"판매자"·"회원"이
--   섞여 보이는데, 역할 통합 이후 그 구분은 **아무 기능도 하지 않는다**(권한은 소유권으로 판정).
--   뜻 없는 라벨만 남아 헷갈리게 하므로 정리한다(사용자 결정, 2026-08-06).
--
-- 무엇을: admin이 아닌 계정의
--   ① `profiles.role` → 'user' (0028이 정한 기본값과 같은 값으로 통일)
--   ② `auth.users.raw_user_meta_data`에서 `role` 키 제거
--   admin은 **양쪽 다 건드리지 않는다** — is_admin()(0001)이 profiles.role='admin' 정확일치를
--   보고, 앱의 관리자 차단(main.dart, AR9)이 metadata의 'admin'을 본다. 둘 다 살아 있어야 한다.
--
-- ⚠️ 왜 컬럼을 비우지 않고 'user'를 넣나: `profiles.role`은 0001에서 NOT NULL이다. 비울 수 없다.
--   "역할 없음"을 표현하는 값이 필요하고, 0028의 트리거 기본값과 같은 값을 쓰는 것이 자연스럽다
--   (신규 가입자와 기존 계정이 같은 모양이 된다).
--
-- ⚠️ 왜 auth 스키마를 건드리나: 앱(Flutter)이 읽던 역할의 **출처가 거기**다. profiles만 정리하면
--   앱 쪽 사본이 남아 두 벌이 계속 어긋난다. 다만 지금은 그 사본을 읽는 곳이 관리자 차단 하나뿐이라
--   (게이트는 이 스토리가 requireUser로 옮겼다) 이 제거는 **동작을 바꾸지 않는 정리**다.
--
-- ⚠️ **되돌릴 수 없다**(CLAUDE.md B3, forward-only). 다만 "누가 판매자였나"는 `listings.seller_id`로
--   여전히 알 수 있으므로 실질 정보 손실은 없다(착수 전 확인함).
--
-- 이 마이그는 **일회성 데이터 정리**다. 재적용해도 안전하다(이미 정리된 행은 조건에 안 걸린다).

-- ① profiles.role 통일
update public.profiles
   set role = 'user'
 where role <> 'admin'
   and role <> 'user';

-- ② auth 메타데이터에서 role 키 제거
update auth.users u
   set raw_user_meta_data = u.raw_user_meta_data - 'role'
  from public.profiles p
 where p.id = u.id
   and p.role <> 'admin'
   and u.raw_user_meta_data ? 'role';

-- 사후조건: 정리가 실제로 끝났는지 이 마이그 자신이 확인한다(성공 보고 = 정리됨을 보장).
-- 두 축을 **둘 다** 본다 — 한쪽만 보면 나머지 한 벌이 남은 채로 초록이 된다(그게 이 스토리가
-- 고치려던 바로 그 병이다).
do $$
declare
  v_legacy_profiles int;
  v_legacy_meta     int;
begin
  select count(*) into v_legacy_profiles
    from public.profiles where role in ('buyer', 'seller');
  if v_legacy_profiles > 0 then
    raise exception 'profiles.role에 buyer/seller가 %건 남았다 — ① UPDATE가 안 걸렸다.', v_legacy_profiles;
  end if;

  select count(*) into v_legacy_meta
    from auth.users u join public.profiles p on p.id = u.id
   where p.role <> 'admin' and u.raw_user_meta_data ? 'role';
  if v_legacy_meta > 0 then
    raise exception 'auth 메타데이터에 role이 %건 남았다 — ② UPDATE가 안 걸렸다.', v_legacy_meta;
  end if;
end $$;

comment on column public.profiles.role is
  '계정 종류. admin만 특별 취급(is_admin()) — 그 외는 전부 ''user''이며 구매/판매 구분이 없다(역할 통합, 0027·0028·0029). 매물 접근 권한은 이 값이 아니라 소유권(seller_id)+RLS로 판정한다.';
