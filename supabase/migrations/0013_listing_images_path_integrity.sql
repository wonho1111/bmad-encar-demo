-- 0013_listing_images_path_integrity.sql — 0012의 storage_path 신뢰 구멍을 막는 전진 마이그
-- self-contained: 앞 번호의 public.listings(0002)·public.listing_images(0012)와
--   프렐류드가 선언한 storage 스키마에만 의존한다. 뒤 번호를 가정하지 않는다.
--
-- 왜 이 마이그가 필요한가 (2026-07-16 코드리뷰 — 원격 실측으로 재현된 권한상승):
--   0012의 listing_images_insert_own은 listing_id 소유권만 검사하고 storage_path는 무검증
--   자유 문자열로 받는다. 그런데 storage.objects 읽기 정책은 바로 그 문자열로 조인한다.
--   → 판매자 A가 자기 on_sale 매물에 storage_path='{피해자uid}/{피해자매물}/x.jpg' 행을 넣으면
--     피해자의 sold 매물 사진이 anon에게 열린다.
--   원격 실측(트랜잭션+rollback): 위조 전 anon 0행 → 위조행 insert 통과 → 위조 후 anon 1행.
--   뿌리는 CLAUDE.md B9 — 경로 규칙이 docs/conventions.md §10 문서에만 있고 DB엔 안 박혔다.
--   0012를 in-place로 고치지 않는 이유: 이미 원격에 적용됐다(B3 "뒤로 가지 말고 고치는 마이그를 하나 더").
--
-- 이 마이그레이션이 하는 일:
--   1) storage_path가 {소유자}/{매물}/{파일명} 임을 DB가 강제 — 소유자는 클라 입력이 아니라
--      listings에서 직접 구한다(B9 "중요한 값은 서버·DB가 직접 구한다")
--   2) storage.objects 쓰기 정책을 for all → insert/update/delete로 좁힘 (AC4가 열거한 3동사)

-- ── 1) storage_path 정합성 트리거 ─────────────────────────────────────
-- security definer 아님: 삽입자는 항상 본인 매물에만 쓸 수 있으므로(0012의 insert 정책)
--   그 매물의 seller_id도 본인 권한으로 보인다.
create or replace function public.enforce_listing_images_storage_path()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  v_seller uuid;
  v_parts  text[];
begin
  -- 소유자를 new.storage_path에서 파싱하지 않는다 — 그건 클라가 보낸 값이다.
  -- listings가 정본이고, DB가 직접 구한다.
  select l.seller_id into v_seller
  from public.listings l
  where l.id = new.listing_id;

  if v_seller is null then
    raise exception '존재하지 않는 매물입니다 (listing_id=%)', new.listing_id;
  end if;

  v_parts := string_to_array(new.storage_path, '/');

  if array_length(v_parts, 1) is distinct from 3
     or v_parts[1] <> v_seller::text
     or v_parts[2] <> new.listing_id::text
     or v_parts[3] = ''
  then
    raise exception
      '사진 경로가 계약과 다릅니다 — 기대 "%/%/{파일명}", 실제 "%" (docs/conventions.md §10)',
      v_seller, new.listing_id, new.storage_path;
  end if;

  return new;
end;
$$;

-- update of ...: listing_id 또는 storage_path가 SET 목록에 오를 때만 재검사한다
-- (sort_order·is_cover만 바꾸는 흔한 UPDATE에는 부담을 주지 않는다).
create trigger listing_images_enforce_storage_path
  before insert or update of listing_id, storage_path on public.listing_images
  for each row execute function public.enforce_listing_images_storage_path();

-- public 스키마 함수는 PostgREST가 RPC로 자동 노출한다 — 트리거 전용 함수의 EXECUTE를 회수한다
-- (트리거로서의 발화에는 영향 없음. 0002_listings.sql:123 · 0012 관례).
revoke execute on function public.enforce_listing_images_storage_path() from public, anon, authenticated;

-- ── 2) storage.objects 쓰기 정책을 3동사로 좁힘 (AC4) ──────────────────
-- 0012는 for all이라 SELECT까지 열렸다 → listing_images 행이 없는 고아 오브젝트도
-- 경로 첫 세그먼트가 본인이면 읽혔다. AC4는 읽기의 근거를 listing_images 조인 하나로
-- 단일화했는데 그게 둘로 갈려 있었다(9.2 서명 URL이 어느 쪽에 기대는지 모호해진다).
-- CREATE POLICY는 명령을 하나만 받으므로(ALL|SELECT|INSERT|UPDATE|DELETE) 3개로 나눈다.
drop policy if exists "listing_images_objects_owner_all" on storage.objects;
drop policy if exists "listing_images_objects_owner_insert" on storage.objects;
drop policy if exists "listing_images_objects_owner_update" on storage.objects;
drop policy if exists "listing_images_objects_owner_delete" on storage.objects;

create policy "listing_images_objects_owner_insert" on storage.objects
  for insert to authenticated
  with check (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  );

create policy "listing_images_objects_owner_update" on storage.objects
  for update to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  )
  with check (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  );

create policy "listing_images_objects_owner_delete" on storage.objects
  for delete to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
  );
