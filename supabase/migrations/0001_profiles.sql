-- 0001_profiles.sql — FR1~4 기반: 역할·상태 프로필 + 신규 가입 트리거 + profiles RLS
-- 스키마 단일 출처(supabase/migrations/). 적용 순서 0001 → 0006.
--
-- 이 마이그레이션이 하는 일:
--   1) profiles 테이블 생성 (id → auth.users, role, status)
--   2) handle_new_user() 트리거 — 회원가입(auth.users insert) 시 profiles 행 자동 생성
--   3) is_admin() 함수 — RLS 자기참조 무한재귀를 피하기 위한 SECURITY DEFINER 헬퍼
--   4) profiles RLS — 본인 행만 읽기 + 관리자는 전체 읽기 (로그인 사용자 한정)
--   5) SECURITY DEFINER 함수의 불필요한 외부 노출(RPC) 차단

-- ── 1) profiles 테이블 ───────────────────────────────────────────────
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  role        text not null check (role in ('buyer', 'seller', 'admin')),
  status      text not null default 'active' check (status in ('active', 'suspended')),
  created_at  timestamptz not null default now()
);

comment on table public.profiles is '사용자 프로필 — 역할(buyer/seller/admin)·상태(active/suspended). id는 auth.users 참조.';

-- ── 2) 신규 가입 트리거 ──────────────────────────────────────────────
-- auth.users에 행이 생기면(=회원가입) profiles 행을 함께 만든다.
-- 역할은 가입 시 전달한 메타데이터(raw_user_meta_data.role)에서 읽되,
-- buyer/seller가 아니면 buyer로 강제한다 → 가입 경로로 admin이 들어오는 것을 차단(AC4).
-- SECURITY DEFINER: 함수 정의자(소유자) 권한으로 실행돼 RLS·권한을 우회하므로,
--                   아직 세션이 없는 가입 시점에도 안전하게 insert할 수 있다.
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

  insert into public.profiles (id, role, status)
  values (new.id, v_role, 'active');

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── 3) 관리자 판별 헬퍼 ──────────────────────────────────────────────
-- "관리자는 전체 profiles 조회" 정책 안에서 profiles를 직접 서브쿼리하면
-- RLS가 자기 자신을 재귀 평가해 'infinite recursion detected in policy' 에러가 난다.
-- SECURITY DEFINER 함수로 분리하면 RLS를 우회해 role을 읽으므로 재귀가 끊긴다.
create or replace function public.is_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

-- ── 4) profiles RLS (로그인 사용자 한정) ─────────────────────────────
-- 본인 행만 읽기 + 관리자는 전체 읽기(두 정책은 OR로 결합된다).
-- 정책을 `to authenticated`로 한정 → 비로그인(anon)은 is_admin()을 평가할 일이 없다.
-- INSERT 정책은 두지 않는다 — 프로필 생성은 위 트리거(SECURITY DEFINER)가 전담한다.
-- UPDATE/DELETE(회원 정지·삭제)는 Epic 6 관리자 기능에서 다룬다.
alter table public.profiles enable row level security;

create policy "profiles_select_self" on public.profiles
  for select to authenticated using (auth.uid() = id);

create policy "profiles_select_admin" on public.profiles
  for select to authenticated using (public.is_admin());

-- ── 5) SECURITY DEFINER 함수 외부 노출 차단 ──────────────────────────
-- public 스키마 함수는 PostgREST가 자동으로 RPC(/rest/v1/rpc/<fn>)로 노출한다.
-- Supabase 기본 권한이 anon·authenticated에 EXECUTE를 명시 부여하므로, public뿐 아니라
-- 각 롤에서도 명시적으로 회수해야 한다.
--   handle_new_user: 트리거 전용 → 모든 롤에서 회수(트리거 실행은 영향 없음).
--   is_admin: RLS 평가에 필요 → authenticated만 유지, anon/public은 회수.
revoke execute on function public.handle_new_user() from public, anon, authenticated;
revoke execute on function public.is_admin()        from public, anon;
grant  execute on function public.is_admin()        to authenticated;
