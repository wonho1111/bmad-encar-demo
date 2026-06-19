-- 0002_listings.sql — FR5~8 기반: 매물 테이블 + 소유권 RLS(FR6) + 판매완료 비노출 RLS(FR11) + status 전환 가드
-- 스키마 단일 출처(supabase/migrations/). 적용 순서 0001 → 0006.
--
-- 이 마이그레이션이 하는 일:
--   1) pgvector 확장 보장 (embedding vector(768)에 필요 — 이미 설치돼 있으면 통과)
--   2) listings 테이블 생성 — FR5 15필드(사진 제외) + seller_id·status·embedding·타임스탬프
--      · 고정 목록 6필드(manufacturer·body_type·color·fuel·transmission·region)는 CHECK로 강제
--      · status는 CHECK로 on_sale/sold 두 값만 허용 (전환 가드의 "그 외 값" 차단 — FR8)
--   3) updated_at 자동 갱신 트리거 (행이 바뀔 때 갱신 시각 자동 기록)
--   4) listings RLS — 같은 마이그레이션에 동거(별도 RLS 묶음 대기 없음, 0001 원칙과 동일)
--      · SELECT: 판매중(on_sale) 공개 ∪ 본인 매물 전부 ∪ 관리자 전체  → 구매자에게 sold 비노출(FR11)
--      · INSERT/UPDATE/DELETE: 본인(auth.uid()=seller_id) 매물만 (소유권 FR6 + 타인 status 전환 차단 FR8)
--   5) 트리거 함수 외부 노출(RPC) 차단
--
-- 단위 규칙: price=원(KRW), mileage=km, displacement=cc  (docs/conventions.md §3)
-- 임베딩 차원: vector(768) — gemini-embedding-001(768) 정합 (docs/conventions.md §1)

-- ── 1) pgvector 확장 보장 ────────────────────────────────────────────
-- embedding vector(768) 타입에 필요. Supabase에 이미 설치돼 있으나 멱등성을 위해 명시.
create extension if not exists vector;

-- ── 2) listings 테이블 ───────────────────────────────────────────────
-- 컬럼명·CHECK 목록값은 architecture.md 확정 정의 그대로(전 구간 단일 출처, drift 금지):
--   UI 드롭다운 · AI Text-to-SQL 화이트리스트 · 시드 데이터 · 질의셋과 동일해야 한다.
create table public.listings (
  -- 시스템 컬럼 (FR5 외)
  id            uuid primary key default gen_random_uuid(),
  seller_id     uuid not null references public.profiles (id) on delete cascade,  -- 판매자 삭제 시 매물도 삭제
  status        text not null default 'on_sale' check (status in ('on_sale', 'sold')),  -- 전환 가드: 두 값만 허용
  embedding     vector(768),                              -- 코퍼스① 임베딩(Epic 4에서 backfill, 지금은 NULL)
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  -- FR5 15필드 (사진 제외 — RAG 목표 집중, Supabase Storage 미사용)
  manufacturer  text not null check (manufacturer in (        -- 제조사(고정 목록)
                  '현대', '기아', '제네시스', '쉐보레', '르노코리아', 'KG모빌리티',
                  'BMW', '벤츠', '아우디', '폭스바겐', '토요타', '혼다', '렉서스', '테슬라', '기타')),
  model         text not null,                                 -- 모델(자유 입력)
  body_type     text not null check (body_type in (            -- 차종(Encar/K-Car 분류)
                  '경차', '소형차', '준중형차', '중형차', '대형차', '스포츠카',
                  'SUV', 'RV', '경승합차', '승합차', '화물차', '기타')),
  year          int  not null check (year between 1990 and 2027),
  price         int  not null check (price >= 0),              -- 원(KRW)
  mileage       int  not null check (mileage >= 0),            -- km
  color         text not null check (color in (
                  '흰색', '검정', '회색', '은색', '파랑', '빨강', '갈색', '녹색', '기타')),
  fuel          text not null check (fuel in (
                  '가솔린', '디젤', '하이브리드', '전기', 'LPG')),
  transmission  text not null check (transmission in ('자동', '수동')),
  displacement  int  not null check (displacement >= 0),       -- cc, 전기차 0 허용
  seats         int  not null check (seats between 2 and 11),
  region        text not null check (region in (
                  '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                  '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주')),
  accident_free boolean not null default true,                 -- 무사고 여부
  options       text[] default '{}',                           -- 코퍼스① 임베딩 대상(Epic 4)
  description   text                                           -- 코퍼스① 임베딩 대상(Epic 4)
);

comment on table public.listings is '차량 매물 — FR5 15필드(사진 제외) + 소유권(seller_id)·상태(on_sale/sold)·임베딩(768). RLS로 소유권·판매완료 비노출 강제.';
comment on column public.listings.seller_id is '판매자 = profiles.id. 본인만 수정/삭제(FR6). 위조 불가(INSERT with check).';
comment on column public.listings.status   is '매물 상태. on_sale=판매중(구매자 공개), sold=판매완료(구매자 비노출 FR11). 두 값만 허용(CHECK).';
comment on column public.listings.embedding is '설명·옵션 텍스트의 768차원 임베딩(코퍼스①). Epic 4에서 backfill, 그 전엔 NULL.';

-- ── 3) updated_at 자동 갱신 + created_at 보존 트리거 ──────────────────
-- 행이 UPDATE될 때마다 updated_at을 현재 시각으로 자동 갱신한다.
-- 또한 created_at은 최초 생성 시각이므로 UPDATE로 위조하지 못하게 항상 기존(OLD) 값으로 되돌린다.
--   (소유자가 UPDATE에 created_at을 끼워 넣어 '최신 등록'처럼 위장하는 것을 차단 — 등록일 정렬·노출 신뢰성 보호.)
-- (moddatetime 확장 대신 plpgsql 함수로 — 0001의 함수 스타일과 일관, 확장 의존 최소화.)
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at := now();
  new.created_at := old.created_at;  -- created_at 불변 보장(UPDATE로 변경 불가)
  return new;
end;
$$;

create trigger listings_set_updated_at
  before update on public.listings
  for each row execute function public.set_updated_at();

-- ── 4) listings RLS (소유권 FR6 + 판매완료 비노출 FR11) ───────────────
-- 0001과 동일 원칙: 정책은 해당 테이블 마이그레이션에 동거 → 0001→0006 순 적용 시 에픽 시점마다 필요한 RLS가 이미 존재.
alter table public.listings enable row level security;

-- SELECT: 세 정책이 OR로 결합된다 → "판매중이거나 ∪ 본인이거나 ∪ 관리자".
--   · 구매자는 본인도 관리자도 아니므로 on_sale만 통과 → sold가 어느 경로로도 안 보임(FR11 핵심).
--   · 판매자는 본인 매물을 status 무관(sold 포함) 조회(본인 매물 관리 2-3 기반).
--   · 관리자는 전체 조회(FR11 예외, Epic 6 기반) — 0001의 is_admin() 재사용.
create policy "listings_select_on_sale" on public.listings
  for select to authenticated using (status = 'on_sale');

create policy "listings_select_own" on public.listings
  for select to authenticated using (auth.uid() = seller_id);

create policy "listings_select_admin" on public.listings
  for select to authenticated using (public.is_admin());

-- INSERT: 본인 명의로만 등록(seller_id 위조 차단). 역할(seller) 게이트는 앱/프록시 책임(2-2).
create policy "listings_insert_own" on public.listings
  for insert to authenticated with check (auth.uid() = seller_id);

-- UPDATE: 본인 매물만 수정.
--   using(기존 행)·with check(변경 후 행) 둘 다 소유권 검증 →
--   · 타인 매물 status 전환 차단(FR8) · 내 매물을 남에게 넘기는 seller_id 재지정 차단.
--   status 값 자체는 CHECK가 on_sale/sold로 제한 → "그 외 값" 전환 차단.
create policy "listings_update_own" on public.listings
  for update to authenticated
  using (auth.uid() = seller_id)
  with check (auth.uid() = seller_id);

-- DELETE: 본인 매물만 삭제(FR6).
create policy "listings_delete_own" on public.listings
  for delete to authenticated using (auth.uid() = seller_id);

-- ── 5) 트리거 함수 외부 노출 차단 ────────────────────────────────────
-- public 스키마 함수는 PostgREST가 RPC로 자동 노출하므로, 트리거 전용 함수의 EXECUTE를 회수한다.
-- (트리거로서의 실행에는 영향 없음 — 트리거는 테이블 소유자 권한으로 실행된다.)
revoke execute on function public.set_updated_at() from public, anon, authenticated;
