-- 0018_wishlists.sql — Story 10.5(찜): 로그인 사용자가 매물을 모아보는 관계 테이블 + 본인 전용 RLS.
-- 스키마 단일 출처(supabase/migrations/). 적용 순서: 0001 → ... → 0017 → 0018(이 파일).
--
-- 이 마이그레이션이 하는 일:
--   1) wishlists 테이블 — (user_id, listing_id) 복합 PK. epic이 스키마를 그대로 지정했다
--      (정규화·집계(찜 개수)·스냅샷 컬럼 추가 금지 — A2, epic-10-context.md "인기신호=보류,
--      스키마만 남김"). listing_id 단독 조회(향후 인기신호 COUNT 등) 가속용 별도 인덱스도 둔다
--      — PK는 user_id가 선두라 listing_id만으로는 이 인덱스를 못 탄다.
--   2) 본인 전용 RLS 3정책(select/insert/delete) — **로그인 전용**(anon·ai_readonly용 정책 없음,
--      docs/conventions.md §8 "행동" 분류). 명시 GRANT는 추가하지 않는다 — 레포 관례상
--      authenticated는 플랫폼 기본 권한을 그대로 쓰고, 행 가시성은 정책이 결정한다
--      (0003_chat.sql·0011_listings_anon_select.sql 참조 — 정책이 없는 롤은 0행).
--
-- FK cascade 근거: 두 FK 모두 on delete cascade. 복합 PK 컬럼은 NOT NULL이라 set null이 불가능하고,
--   restrict는 판매자의 매물 삭제(FR6)를 막아버려 부적합하다. cascade는 레포 전 자식 테이블
--   (0003 chat_rooms/chat_messages, 0012 listing_images)과 동일한 관례다. 이 cascade의 결과
--   (seed.sql 재실행 시 찜도 함께 사라짐)와 그 판단 근거는 `docs/tech-debt.md` #89에 기록돼 있다.

-- ── 1) wishlists 테이블 ──────────────────────────────────────────────
create table if not exists public.wishlists (
  user_id     uuid not null references public.profiles (id) on delete cascade,  -- 찜한 사람. 탈퇴 시 그 사람의 찜도 정리.
  listing_id  uuid not null references public.listings (id) on delete cascade,  -- 찜당한 매물. 매물 삭제 시 찜 관계도 정리.
  created_at  timestamptz not null default now(),
  -- 한 사용자·매물 조합당 행 1개(중복 찜 불가) — 토글(insert↔delete) 로직이 이 유일성에 기댄다.
  primary key (user_id, listing_id)
);

-- listing_id 단독 조회(예: 향후 "이 매물을 몇 명이 찜했나" COUNT) 가속. PK(user_id, listing_id)는
-- user_id가 선두 컬럼이라 listing_id만으로 찾으면 이 인덱스가 없으면 풀스캔이 된다.
create index if not exists wishlists_listing_id_idx on public.wishlists (listing_id);

comment on table public.wishlists is
  'Story 10.5 찜 — 로그인 사용자가 매물을 모아보는 다대다 관계. 정규화·집계·스냅샷 컬럼 없음(epic 지정 스키마 그대로, A2). RLS로 본인 행만 접근(로그인 전용).';
comment on column public.wishlists.user_id is '찜한 사용자 = profiles.id(auth.uid()). 본인 행만 select/insert/delete(RLS).';
comment on column public.wishlists.listing_id is '찜당한 매물 = listings.id. 매물이 하드삭제되면 cascade로 이 행도 함께 사라진다(대장 #89).';

-- ── 2) RLS (본인 전용, 로그인 전용) ────────────────────────────────────
-- 0003·0012와 동일 원칙: 정책은 해당 테이블 마이그레이션에 동거.
-- anon·ai_readonly 정책은 만들지 않는다 — 찜은 "행동"(conventions §8)이라 그 두 롤은 행이
-- 0건으로 보이는 것이 의도된 동작이다(권한이 있어도 정책이 없으면 0건 — §9.1 관례와 동일).
alter table public.wishlists enable row level security;

-- SELECT: 본인이 찜한 행만 본다. 타인의 찜은 항상 0행이어야 한다(Story 문서에 red/green 실측 기록).
create policy "wishlists_select_own" on public.wishlists
  for select to authenticated
  using (auth.uid() = user_id);

-- INSERT: 본인 명의로만 찜을 만들 수 있다(user_id 위조 차단) — listings.seller_id 위조 차단(0002)과 같은 패턴.
create policy "wishlists_insert_own" on public.wishlists
  for insert to authenticated
  with check (auth.uid() = user_id);

-- DELETE: 본인 찜만 취소(토글의 "비우기" 절반).
create policy "wishlists_delete_own" on public.wishlists
  for delete to authenticated
  using (auth.uid() = user_id);

-- UPDATE 정책 없음 → 기본 거부. 찜은 "있다/없다" 두 상태뿐이라 수정 대상 컬럼이 없다
-- (created_at은 최초 찜 시각으로 불변 — 취소 후 재찜은 delete+insert로 새 행이 된다).
