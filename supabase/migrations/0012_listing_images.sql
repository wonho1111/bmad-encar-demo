-- 0012_listing_images.sql — Epic 9 첫 마이그: listing_images 스키마 + 비공개 버킷 + Storage RLS
-- self-contained: 이 마이그가 참조하는 것은 (1) 프렐류드가 선언한 storage 스키마/RLS 상태
--   (2) 자기보다 앞 번호의 public.listings(0002)·public.is_admin()(0001)뿐이다. 뒤 번호를 가정하지 않는다.
--
-- 이 마이그레이션이 하는 일:
--   1) listing_images 테이블 — 매물 사진 메타데이터(파일 바이너리는 Storage, 여기는 메타만)
--   2) 매물당 대표사진 1장 강제(부분 유니크) + 조회 인덱스
--   3) 매물당 최대 10장 강제 BEFORE INSERT 트리거
--   4) 비공개 버킷 `listing-images` — 장당 5MB·mime 3종 상한을 DB에 박음
--   5) listing_images RLS 5정책(anon/authenticated on_sale·본인·admin/ai_readonly) — 0002+0011 역할분리 패턴
--   6) storage.objects RLS 2정책(쓰기=본인 경로만, 읽기=on_sale∪본인) — FR11·FR58의 스토리지 레이어 강제
--   7) GRANT — anon 컬럼 스코프(0011 패턴) · ai_readonly 명시(0004 패턴). authenticated는 플랫폼 기본에 위임(#18 범위 밖)
--
-- 경로 규칙·상한·SIGNED_URL_TTL 등 계약값은 docs/conventions.md §10 참조(값 중복 금지).

-- ── 1) listing_images 테이블 ─────────────────────────────────────────
-- 컬럼은 이 목록이 전부다(AC1) — 사진 처리상태(I8)·크롭(I14)은 여기 컬럼이 아니라 클라 로컬 상태.
create table public.listing_images (
  id            uuid primary key default gen_random_uuid(),
  listing_id    uuid not null references public.listings (id) on delete cascade,
  storage_path  text not null unique,       -- 버킷 내 key 전체. storage.objects.name과 글자 그대로 동일해야 함(AC3)
  sort_order    int  not null default 0,
  is_cover      boolean not null default false,
  credit        jsonb                       -- nullable. 9.7 Commons 사진의 저작자·라이선스·원본링크
);

comment on table public.listing_images is
  '매물 사진 메타데이터. 파일 바이너리는 비공개 버킷 listing-images에, 여기는 메타데이터만. storage_path는 storage.objects.name과 동일 문자열이어야 RLS 조인이 성립한다.';
comment on column public.listing_images.storage_path is
  '버킷 내 key 전체({user_id}/{listing_id}/{filename}), 버킷명 미포함(docs/conventions.md §10).';
comment on column public.listing_images.is_cover is
  '대표사진 여부. 매물당 최대 1장(부분 유니크 인덱스로 강제).';
comment on column public.listing_images.credit is
  'Commons 시드 사진 등 외부 출처 사진의 저작자·라이선스·원본링크(nullable, Story 9.7).';

-- ── 2) 대표 1장 강제 + 조회 인덱스 ────────────────────────────────────
-- concurrently 미사용: 신규 빈 테이블이라 락 문제 없음(게이트가 --single-transaction으로 돌기 때문에 필수).
create unique index listing_images_one_cover_per_listing
  on public.listing_images (listing_id) where is_cover;

create index listing_images_listing_sort_idx
  on public.listing_images (listing_id, sort_order);

-- ── 3) 매물당 최대 10장 — BEFORE INSERT 트리거 ────────────────────────
-- security definer 아님: insert는 항상 본인 매물에만 허용되므로(아래 RLS), 카운트도 본인 권한으로 충분히 보인다.
create or replace function public.enforce_listing_images_max_10()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  v_count int;
begin
  select count(*) into v_count
  from public.listing_images
  where listing_id = new.listing_id;

  if v_count >= 10 then
    raise exception '매물당 사진은 최대 10장까지 등록할 수 있습니다 (listing_id=%)', new.listing_id;
  end if;

  return new;
end;
$$;

create trigger listing_images_enforce_max_10
  before insert on public.listing_images
  for each row execute function public.enforce_listing_images_max_10();

-- public 스키마 함수는 PostgREST가 RPC로 자동 노출한다 — 트리거 전용 함수의 EXECUTE를 회수한다.
-- (트리거로서의 실행에는 영향 없음 — 트리거는 여전히 정상 발화한다. 0002_listings.sql:123 관례.)
revoke execute on function public.enforce_listing_images_max_10() from public, anon, authenticated;

-- ── 4) 비공개 버킷 + 업로드 상한 (AC2) ────────────────────────────────
-- on conflict(id) do nothing: 재적용 안전(마이그는 레시피다 — docs/conventions.md §9.1).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'listing-images',
  'listing-images',
  false,                                       -- 비공개(ADR-IMG-01)
  5242880,                                      -- 5MB (docs/conventions.md §10)
  array['image/jpeg', 'image/png', 'image/webp']  -- 저장형 XSS 방지 — docs/conventions.md §10
)
on conflict (id) do nothing;

-- ── 5) listing_images RLS — 역할별 정책 분리(0002+0011 패턴, is_admin()을 anon 경로에 안 태움) ──
alter table public.listing_images enable row level security;

-- anon: on_sale 매물의 사진만(FR58 열람 + FR11 유지)
create policy "listing_images_select_on_sale_anon" on public.listing_images
  for select to anon using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.status = 'on_sale'
    )
  );

-- authenticated: on_sale ∪ 본인 ∪ 관리자 (listings 3분리 정책과 동일 구조)
create policy "listing_images_select_on_sale" on public.listing_images
  for select to authenticated using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.status = 'on_sale'
    )
  );

create policy "listing_images_select_own" on public.listing_images
  for select to authenticated using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.seller_id = auth.uid()
    )
  );

create policy "listing_images_select_admin" on public.listing_images
  for select to authenticated using (public.is_admin());

-- 쓰기(insert/update/delete): 본인 매물의 사진만.
create policy "listing_images_insert_own" on public.listing_images
  for insert to authenticated
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.seller_id = auth.uid()
    )
  );

create policy "listing_images_update_own" on public.listing_images
  for update to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.seller_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.seller_id = auth.uid()
    )
  );

create policy "listing_images_delete_own" on public.listing_images
  for delete to authenticated using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id and l.seller_id = auth.uid()
    )
  );

-- ai_readonly: CR2 — sold 포함 전체를 본다(의도됨). FR11은 api가 on_sale id로 스코프를 좁혀 강제한다.
--   sql_guard는 listings 단일 테이블을 유지하고 이 테이블과 JOIN하지 않는다(Story 9.6의 일).
create policy "listing_images_ai_readonly_select" on public.listing_images
  for select to ai_readonly using (true);

-- ── 6) storage.objects RLS — 정책 2종, 동거 (AC4) ─────────────────────
-- alter table storage.objects enable row level security는 하지 않는다 — 원격은 플랫폼이 이미 켜뒀다
-- (2026-07-16 실측 확인: relrowsecurity = true).
drop policy if exists "listing_images_objects_owner_all" on storage.objects;
drop policy if exists "listing_images_objects_read" on storage.objects;

-- 쓰기: 첫 경로 세그먼트가 auth.uid()인 경우에만 insert/update/delete 허용(경로 규칙 = docs/conventions.md §10).
--   split_part(name,'/',1)은 text, auth.uid()는 uuid → auth.uid()::text로 비교(반대 캐스팅은 에러 유발).
create policy "listing_images_objects_owner_all" on storage.objects
  for all to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  )
  with check (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  );

-- 읽기: 그 오브젝트를 가리키는 listing_images 행의 매물이 on_sale이거나 본인 소유일 때만(FR11·FR58).
--   is_admin()을 참조하지 않는다 — authenticated에만 execute가 있어 anon이 걸리면 열람 전체가 깨진다(0001_profiles.sql:91).
create policy "listing_images_objects_read" on storage.objects
  for select to anon, authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and exists (
      select 1
      from public.listing_images li
      join public.listings l on l.id = li.listing_id
      where li.storage_path = storage.objects.name
        and (l.status = 'on_sale' or l.seller_id = auth.uid())
    )
  );

-- ── 7) GRANT (AC6, 기술부채 #18 판정 (a′) — 실측 증거는 Debug Log 참조) ──
-- anon: 0011과 같은 모양 — 테이블 전체 SELECT 회수 후 컬럼 스코프로만 재부여(플랫폼 기본 GRANT 암묵 의존을 끊음).
revoke select on public.listing_images from anon;

grant select (
  id,
  listing_id,
  storage_path,
  sort_order,
  is_cover,
  credit
) on public.listing_images to anon;

-- ai_readonly: 0004_guide_documents.sql:58 선례. 0006의 alter default privileges에 기대지 않는다.
grant select on public.listing_images to ai_readonly;

-- authenticated: 이 마이그는 명시 GRANT를 추가하지 않는다 — 플랫폼 기본(alter default privileges)에 위임한다.
--   나머지 테이블(profiles·chat_*)과 동일한 상태로 남겨 #18의 authenticated 범위는 이번에 건드리지 않는다
--   (docs/tech-debt.md #18 — "새로 만드는 테이블만 명시"는 anon+ai_readonly에 한정).
