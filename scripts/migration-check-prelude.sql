-- migration-check-prelude.sql — 마이그레이션 게이트가 fresh DB에 미리 까는 "Supabase 플랫폼 계약면" 재현
--
-- 여기 있는 것 = 우리가 Supabase에 의존한다고 인정한 것. 추가하려면 그 의존이 정당한지 먼저 답할 것.
-- (프렐류드를 늘려 게이트의 red를 무마하는 우회를 막기 위한 규칙 — Story 8.6 Task 2)
--
-- ⚠️ "정당한 확장"과 "red 무마 우회"를 가르는 기준 (2026-07-15 코드리뷰 추가):
--   · 정당하다 = 실제 Supabase 플랫폼에 **있는데** 이 스텁이 빠뜨려서 red가 났다.
--     → 실측값을 근거로 추가하라(원격에서 확인한 뒤 그 사실을 주석에 남긴다).
--       예: auth.users는 지금 3컬럼 스텁이라, 마이그가 실재하는 created_at·phone 등을
--           참조하면 원격은 멀쩡한데 게이트만 red다 — 이건 스텁의 결함이지 마이그의 결함이 아니다.
--   · 우회다 = 플랫폼에 **없는 것**을 여기 만들어 red를 없앤다.
--     → 금지. 그 red는 진짜 self-containment 위반이고, 마이그를 고쳐야 한다.
--   이 구분이 없으면 "확장 금지"가 탈출구 없는 규칙이 되어 결국 통째로 무시된다.
--
-- self-contained의 정의(이 프렐류드가 그 기준선이다):
--   선언된 프렐류드 계약면 + 자기보다 앞 번호 마이그레이션, 이 둘만으로 성립하는가.
--
-- 대상: pgvector/pgvector:pg17 빈 컨테이너(postgres 슈퍼유저로 실행). 원격 매니지드 DB엔 절대 적용하지 않는다
-- (원격은 이미 이 계약면을 플랫폼이 제공하므로 불필요 — 오히려 충돌 가능).

-- ── auth 스키마 + auth.users (0001의 FK·가입 트리거가 읽는 컬럼만) ──────────
create schema if not exists auth;

create table if not exists auth.users (
  id                 uuid primary key,
  email              text,
  raw_user_meta_data jsonb
);

-- ── auth.uid() 스텁 — 0001 RLS 정책이 참조 ──────────────────────────────
create or replace function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

-- ── Supabase 표준 롤 (0001·0002·0003c·0007~0009·0011이 참조) ────────────
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin;
  end if;
end $$;

-- 롤 postgres는 컨테이너 기본 슈퍼유저 — 그대로 쓴다(별도 생성 불필요).
-- vector 확장은 이미지에 포함되어 있고, 마이그레이션(0002·0004)이 `create extension if not exists vector`로
-- 자체 수행한다 — 여기서 만들지 않는다.
-- ai_readonly 롤은 0006이 만드는 것이므로 여기 넣지 않는다(마이그의 몫).

-- ── 플랫폼 기본 GRANT (2026-07-14 운영 Supabase 실측 — pg_default_acl 재현, 추정 아님) ──
--   원본: postgres 롤의 기본권한 = {anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm, ai_readonly=r}
--   (arwdDxtm = insert·select·update·delete·truncate·references·trigger·maintain)
--   ai_readonly=r은 0006이 만드는 것이므로 여기 넣지 않는다.
-- service_role은 프렐류드에만 등장하고 마이그는 안 쓴다(project-context 규칙 6 — service_role 키 금지).
-- 실측 재현이라 넣을 뿐, 이걸 근거로 마이그에서 service_role을 쓰지 마라.
alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;

-- ── storage 스키마 최소 스텁 (0012_listing_images가 참조 — 2026-07-16 원격 실측 기반, Story 9.1) ──
--   실측 근거: information_schema.columns(storage.buckets/objects 전체 컬럼) + pg_class.relrowsecurity를
--   원격에서 직접 조회(Story 9.1 Task 1). 이 레포 최초의 storage 마이그라 스텁이 아예 없었다.
--   "정당한 확장" 기준 충족: 실제 Supabase 플랫폼에 있는 걸 스텁이 빠뜨려 red가 나는 경우다(우회 아님).
--   스텁은 0012가 실제로 건드리는 컬럼만 담는다(선례: auth.users 3컬럼 스텁과 동일 원칙) — owner 등
--   나머지 실컬럼은 원격엔 있지만 여기 없다(마이그가 안 쓰므로 필요 없음).
create schema if not exists storage;

create table if not exists storage.buckets (
  id                  text primary key,
  name                text not null,
  public              boolean,
  file_size_limit     bigint,
  allowed_mime_types  text[]
);

create table if not exists storage.objects (
  id         uuid primary key default gen_random_uuid(),
  bucket_id  text,
  name       text
);

-- 원격 실측(2026-07-16): relrowsecurity = true — 플랫폼이 이미 켜둔 상태를 재현.
-- (0012는 이 문을 스스로 켜지 않는다 — 원격에서 소유자가 아닌 롤이 건드리면 실패할 수 있어서다.)
alter table storage.objects enable row level security;
-- storage 스텁은 여기까지(Story 9.1, 0012 전용).
