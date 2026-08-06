-- 0027_role_check_relax.sql — profiles.role의 3값 enum CHECK 완화 (Story 14.1, 역할 통합 착수)
--
-- 왜: profiles.role은 0001에서 `check (role in ('buyer', 'seller', 'admin'))`으로 고정돼 있어,
--   이후 스토리(14.2 가입 트리거 기본값 변경)가 buyer/seller가 아닌 새 기본값을 넣을 자리가 없다.
--   역할 통합(구매자/판매자 구분 폐지)의 첫 단추로 이 CHECK부터 완화한다.
--
-- 무엇을: 기존 3값 enum CHECK를 drop하고, 빈 문자열만 막는(사실상 무제한) CHECK로 같은 이름
--   (profiles_role_check)에 교체한다. 컬럼명(role)은 그대로 둔다 — is_admin()(0001)이 role
--   컬럼명에 의존한다(0005는 role을 직접 참조하지 않고 is_admin()만 호출한다 — grep 확인).
--   기존 행의 role 값(buyer/seller/admin)은 이 마이그가 UPDATE하지 않는다(forward-only, CLAUDE.md B3).
--   신규 기본값 결정(14.2)·판매 게이트 완화(14.3)는 이 마이그의 범위가 아니다.
--
-- 완화 폭을 "특정 새 값 집합"으로 좁히지 않는 이유: 14.2의 신규 가입 기본값이 아직 미정이다.
--   지금 특정 신규 집합(예: 'user','admin')으로 좁히면 기존 buyer/seller 행이 그 즉시 위반 상태가
--   된다 — Postgres CHECK는 UPDATE 시 변경 컬럼과 무관하게 행 전체를 재평가하므로, 그 행의 아무
--   컬럼이나 이후 UPDATE되는 순간 조용히 실패한다. 그래서 admin이 아닌 값은 자유롭게 허용한다.
--
-- ⚠️ 이 마이그 이후 role의 **어휘는 DB가 강제하지 않는다**. 남은 `role <> ''`는 어휘 검사가
--   아니라 "빈 문자열이라는 무의미한 값만 막는" 최소 방어선이다 — `' '`·`'ADMIN'`·`'admin '`
--   같은 값도 전부 통과하고, 그런 값은 is_admin()에서 admin으로 인정되지 않는다(정확일치 비교).
--   NOT NULL은 컬럼 정의(0001)에 이미 있고 CHECK는 NULL에 unknown이라 애초에 관여하지 않으므로,
--   이 조건이 NOT NULL을 보조하는 것도 아니다. 어휘를 다시 좁힐지는 14.2가 기본값을 정할 때
--   같은 이름으로 교체하며 판단한다.
--
-- 제약 이름 확인: `select conname from pg_constraint where conrelid = 'public.profiles'::regclass
--   and contype = 'c';`로 실제 이름이 `profiles_role_check`(0001의 기본 명명 관례와 일치)임을
--   로컬 pgvector 컨테이너에서 직접 확인한 뒤 아래 DDL을 작성했다(추정이 아니라 조회, CLAUDE.md B4).
--   다만 그 확인은 **이 레포의 0001로 만든 컨테이너**에서 한 것이라, 배포 대상 DB의 이름이
--   다른 경우(드리프트)를 원리적으로 볼 수 없다 — `drop ... if exists`는 그때 조용히 no-op이 되고
--   뒤이은 add는 성공해, 옛 3값 CHECK가 제 이름으로 살아남은 채 마이그는 성공을 보고한다
--   (Postgres는 같은 테이블의 CHECK 여러 개를 AND로 결합한다). 그래서 아래에 사후조건을 둔다.

alter table public.profiles
  drop constraint if exists profiles_role_check;

alter table public.profiles
  add constraint profiles_role_check check (role <> '');

-- 사후조건: 완화가 실제로 일어났는지 이 마이그 자신이 확인한다(성공 보고 = 완화됨을 보장).
-- 이름이 무엇이든 buyer/seller를 강제하는 CHECK가 남아 있으면 여기서 크게 실패시킨다.
-- buyer와 seller를 **둘 다** 본다: 부분 편집으로 한쪽만 남은 드리프트(예: `role in ('seller','admin')`)는
-- buyer만 보는 술어를 통과해버린다(3차 리뷰 지적). 짝이 되는 테스트
-- (test_role_check_relax_real_db.py의 test_no_check_constraint_still_enforces_buyer_or_seller)와
-- 같은 술어를 쓴다 — 두 층이 서로 다른 것을 보면 한쪽만 빨개지는 구멍이 생긴다.
do $$
begin
  if exists (
    select 1 from pg_constraint
    where conrelid = 'public.profiles'::regclass
      and contype = 'c'
      and (pg_get_constraintdef(oid) ilike '%buyer%' or pg_get_constraintdef(oid) ilike '%seller%')
  ) then
    raise exception 'profiles.role의 3값 CHECK가 아직 남아 있다 — drop이 no-op였다(제약 이름 드리프트). 실제 이름을 pg_constraint로 확인하고 이 마이그를 고칠 것.';
  end if;
end $$;

-- 테이블 COMMENT도 3값 계약을 서술하고 있었다(0001) — 그건 DB 카탈로그 안에 사는 서술이라
-- 레포의 문서를 고쳐도 Supabase Studio·`\d+ profiles`·스키마 introspection에는 닿지 않는다.
-- forward-only라 0001을 고치지 않고 여기서 덮어쓴다.
comment on table public.profiles is '사용자 프로필 — 역할(role: admin만 is_admin()이 특별 취급, 그 외 값은 DB가 강제하지 않음 — 0027)·상태(active/suspended). id는 auth.users 참조.';
