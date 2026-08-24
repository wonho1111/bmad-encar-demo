-- 0032_suspended_write_block.sql — 정지(profiles.status='suspended') 회원의 쓰기를 전 경로에서 막는다
-- (FR22 실질화, DW-669·DW-717·DW-721·DW-674·DW-782, Story 17.1)
-- self-contained: 이 파일이 참조하는 것은 전부 자기보다 앞 번호다 — public.profiles(0001)·
--   public.listings(0002·0015)·public.listing_images(0012·0031)·storage.objects(0013·0014)·
--   public.is_admin()(0001)·admin_restore_sold_listing(0030)·chat_messages(0003). 뒤 번호를 가정하지 않는다.
--
-- 불변식(이 파일 전체가 지키려는 한 문장):
--   "profiles.status='suspended'인 계정은 매물·사진·파일·관리자 RPC 어느 경로로도 쓰기를
--    성공시킬 수 없다. 반대로 그 계정의 읽기는 아무것도 줄어들지 않는다."
--   그래서 이 파일은 listings_select_*·listing_images의 SELECT 정책·profiles의 SELECT
--   정책·chat의 SELECT 정책을 **하나도 건드리지 않는다.**
--
-- 왜 is_admin()을 전역으로 좁히지 않고 is_admin_active()를 새로 만드나:
--   is_admin()에 `and status='active'`를 그대로 넣으면 그 함수를 참조하는 읽기 정책(
--   chat_rooms_select_admin·chat_messages_select_admin·listing_images_select_admin·
--   listings_select_admin·listing_images_objects_owner_select의 관리자 분기)까지 함께 좁아져
--   위 불변식의 "읽기는 줄지 않는다" 절반을 깨뜨린다. 그래서 **쓰기 소비처에만** 쓰는 새 판별
--   함수(is_admin_active)를 만든다 — is_admin()은 이 파일에서 정의도, 참조 대체도 하지 않는다.
--
-- ── 1) is_admin_active() — 정지되지 않은 관리자만 참인 SECURITY DEFINER 헬퍼 ─────────────
-- is_admin()(0001)과 같은 이유로 SECURITY DEFINER가 필요하다: profiles_update_admin·
-- profiles_delete_admin은 profiles **자신을 보호하는 정책**이라, 그 정책 안에서 "호출자가
-- 활성 admin인가"를 알려면 다시 profiles를 서브쿼리해야 하고, RLS 정책 안에서 자기 테이블을
-- 직접 서브쿼리하면 "infinite recursion detected in policy"가 난다(0001 주석과 동일 함정).
-- listings·listing_images·storage.objects 쪽 admin 정책은 profiles가 아닌 테이블이라 원칙적으로
-- 직접 서브쿼리도 가능하지만, 관리자 판정 로직을 한 곳에 모아 두는 편이 일관되므로 전부
-- 이 함수로 통일한다(스펙 Design Notes).
create or replace function public.is_admin_active()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin' and status = 'active'
  );
$$;

comment on function public.is_admin_active() is
  '활성 관리자 판정(Story 17.1, DW-721) — role=''admin'' **그리고** status=''active''. is_admin()(0001)과
   달리 정지된 관리자를 거른다. SECURITY DEFINER인 이유는 is_admin()과 같다: profiles 자신을 지키는
   정책(profiles_update_admin·profiles_delete_admin) 안에서 profiles를 직접 서브쿼리하면 정책
   무한재귀가 난다. **소비처는 쓰기 전용이다** — 관리자 SELECT 정책(listings_select_admin·
   profiles_select_admin·chat_*_select_admin·listing_images_select_admin)은 is_admin() 그대로 둔다.
   정지된 관리자도 열람은 허용돼야 한다는 docs/conventions.md §8 원칙 때문이며, 이 함수를 그쪽으로
   넓히면 그 원칙이 조용히 깨진다. 강제 장치: api/tests/integration/test_suspended_write_block_real_db.py
   (정지 관리자의 쓰기 6정책 + 복원 RPC가 전부 0행, 동시에 읽기 정책은 그대로 열려 있음을 고정).';

-- public 스키마 함수는 PostgREST가 RPC로 자동 노출한다 — is_admin()(0001)과 동일하게 회수한다.
revoke execute on function public.is_admin_active() from public, anon;
grant  execute on function public.is_admin_active() to authenticated;

-- ── 2) listings — 본인 쓰기 3정책에 정지 조건 추가 ────────────────────────────────────────
-- listings_insert_own(0002)·listings_update_own(0015가 최신판)·listings_delete_own(0002)을
-- 같은 이름으로 drop→create(§9.1 허용 전진 패턴).
--
-- ⚠️ listings_update_own은 **using에만** 조건을 추가하고 with check는 손대지 않는다:
--   using = 변경 전(OLD) 행을 고르는 조건 → 정지된 행위자는 애초에 어떤 행도 못 고른다.
--   with check = 변경 후(NEW) 행을 검증하는 조건 → 정지 조건을 여기 또 걸 필요가 없다.
--     using이 이미 행을 하나도 안 보여주므로 with check까지 도달하는 경우 자체가 없다(중복).
--   이렇게 하면 0015가 with check에 의도적으로 남겨 둔 "on_sale→sold 전환은 허용" 비대칭이
--   그대로 보존된다 — with check를 건드리면 그 비대칭을 다시 검토해야 하는데 이 스토리의
--   범위가 아니다.
--   ⚠️ 이 논증은 listings에 permissive UPDATE 정책이 이것 하나뿐인 동안만 성립한다 — 두 번째
--   permissive UPDATE 정책이 생기면 NEW 행 경로가 다시 열린다(permissive 정책은 using·
--   with check 각각 OR로 합쳐지므로, 다른 정책의 with check가 열려 있으면 이 정책의 with check
--   생략은 더 이상 무해하지 않다. 2026-08-11 3차 코드리뷰 patch).
drop policy if exists "listings_insert_own" on public.listings;

create policy "listings_insert_own" on public.listings
  for insert to authenticated
  with check (
    auth.uid() = seller_id
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

drop policy if exists "listings_update_own" on public.listings;

create policy "listings_update_own" on public.listings
  for update to authenticated
  using (
    auth.uid() = seller_id
    and status <> 'sold'
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  )
  with check (auth.uid() = seller_id);

drop policy if exists "listings_delete_own" on public.listings;

create policy "listings_delete_own" on public.listings
  for delete to authenticated
  using (
    auth.uid() = seller_id
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

-- ── 3) listing_images — 본인 쓰기 3정책(0031)에 정지 조건 추가 ────────────────────────────
-- 0031은 이미 세 정책 모두 같은 exists(...) 조건을 using·with check 양쪽(update)에 대칭으로
-- 걸어 뒀다(listings처럼 "일부러 남겨 둔 비대칭"이 없다) — 그래서 여기도 대칭으로 추가한다.
drop policy if exists "listing_images_insert_own" on public.listing_images;
drop policy if exists "listing_images_update_own" on public.listing_images;
drop policy if exists "listing_images_delete_own" on public.listing_images;

create policy "listing_images_insert_own" on public.listing_images
  for insert to authenticated
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

create policy "listing_images_update_own" on public.listing_images
  for update to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  )
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

create policy "listing_images_delete_own" on public.listing_images
  for delete to authenticated using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

-- ── 4) storage.objects — 소유자 쓰기 3정책(0013)에 정지 조건 + sold 조건 추가 (DW-782) ────
-- 경로 계약(docs/conventions.md §10): {seller_uid}/{listing_id}/{파일명}. 첫 세그먼트는 이미
-- 0013이 소유자로 검사한다. 두 번째 세그먼트(listing_id)로 listings를 join해 sold 여부를
-- 추가로 본다 — 0031이 listing_images 행에는 이미 건 sold 차단이 storage.objects 파일 자체에는
-- 없었던 구멍(DW-782)을 여기서 같이 닫는다.
--
-- ⚠️ 두 번째 세그먼트를 `::uuid`로 캐스팅하기 전에 형식을 먼저 검증한다(2026-08-11 코드리뷰).
-- storage.objects 쓰기는 0013의 트리거(listing_images 테이블에만 걸림)를 거치지 않으므로,
-- 형식이 어긋난 경로(세그먼트 없음·UUID 아닌 문자열)가 이 정책까지 그대로 들어올 수 있다.
-- `and`로만 캐스팅 앞에 정규식을 놓으면 플래너가 평가 순서를 바꿀 수 있어 안전하지 않다 —
-- `case`는 조건이 거짓이면 `then` 절(캐스팅)을 아예 평가하지 않는다는 것이 보장되므로 이걸 쓴다.
-- 형식이 어긋나면 `case`가 null을 돌려주고, `l.id = null`은 항상 거짓이라 정책이 조용히
-- 거부한다(42501/0행) — `invalid input syntax for type uuid` 예외 대신.
--
-- ⚠️ 정규식은 대문자를 받지 않는다(`[0-9a-f]`, `A-F` 없음) — 0013의
-- enforce_listing_images_storage_path 트리거가 listing_id를 대소문자 구분 텍스트 비교로
-- 대조하고(`split_part(name,'/',2) <> new.listing_id::text`), Postgres가 uuid::text를 항상
-- 소문자로 렌더링해 두 클라이언트(web·app) 모두 DB가 준 소문자 id로 경로를 만들기 때문이다.
-- 대문자를 허용하면 파일은 업로드되는데 그 경로로는 listing_images 행이 영원히 못 만들어지는
-- 상태가 생긴다(2026-08-11 3차 코드리뷰 patch — 실측 없이 대칭성만 보고 A-F를 넣었던 자리).
--
-- ⚠️ **INSERT/UPDATE와 DELETE는 join 형태가 다르다(2026-08-11 bad_spec 루프백 — 로컬 실 스택
-- 재현으로 확정, 아래가 그 결론).** 세 verb에 같은 "살아 있는 non-sold 매물이 있어야 한다"
-- 조건을 복붙하면, docs/conventions.md §10.1이 규정한 실제 삭제 순서(① listings 행 DELETE →
-- ② storage.objects 사진 DELETE)에서 ①이 끝난 뒤 ②를 시도하는 순간 join 대상 매물이 이미
-- 없어(EXISTS 거짓) 사진 DELETE가 0행이 되고 **고아 파일이 영구히 남는다**
-- (`web/src/lib/storage/upload.ts`의 `deleteListingImageObject`는 RLS 0행 응답을
-- "이미 없음"으로 읽어 성공으로 보고하므로 화면·로그 어디에도 안 뜨는 조용한 실패).
--   · INSERT(with check)·UPDATE(using+with check): **긍정형** `exists(살아 있는 자기
--     non-sold 매물)` — 새로 붙이거나 바꾸는 사진은 그 시점에 매물이 살아 있고 sold가 아니며
--     "내" 매물이어야 한다. `l.seller_id = auth.uid()`가 없으면 남의 on_sale 매물 id를 자기
--     uid prefix 아래 붙여 파일을 심을 수 있다(0031의 listing_images 정책이 보는 것과 같은
--     소유권 축 — 2026-08-11 루프백이 추가로 지적).
--   · DELETE(using): **부정형** `not exists(sold 매물)` — "sold 매물의 사진만 못 지운다"이고,
--     매물 행이 이미 없으면(=고아, §10.1 순서상 정상 경로) 소유자가 여전히 지울 수 있다.
--     seller_id 조건을 넣지 않는다 — 첫 세그먼트(경로 소유권) 검사가 이미 "내 폴더 밑의
--     오브젝트"로 좁혀 놨고, DELETE는 "sold가 아니면 지울 수 있다"는 허용 쪽 판단이라 매물이
--     없거나 형식이 어긋난 레거시 경로도 정리 가능해야 하기 때문이다(그래야 §10.1의
--     "회수 가능한 고아" 전제가 성립한다).
drop policy if exists "listing_images_objects_owner_insert" on storage.objects;
drop policy if exists "listing_images_objects_owner_update" on storage.objects;
drop policy if exists "listing_images_objects_owner_delete" on storage.objects;

create policy "listing_images_objects_owner_insert" on storage.objects
  for insert to authenticated
  with check (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
    and exists (
      select 1 from public.listings l
      where l.id = case
          when split_part(storage.objects.name, '/', 2)
            ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          then split_part(storage.objects.name, '/', 2)::uuid
        end
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
  );

create policy "listing_images_objects_owner_update" on storage.objects
  for update to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
    and exists (
      select 1 from public.listings l
      where l.id = case
          when split_part(storage.objects.name, '/', 2)
            ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          then split_part(storage.objects.name, '/', 2)::uuid
        end
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
  )
  with check (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
    and exists (
      select 1 from public.listings l
      where l.id = case
          when split_part(storage.objects.name, '/', 2)
            ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          then split_part(storage.objects.name, '/', 2)::uuid
        end
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
  );

create policy "listing_images_objects_owner_delete" on storage.objects
  for delete to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and split_part(storage.objects.name, '/', 1) = auth.uid()::text
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
    and not exists (
      select 1 from public.listings l
      where l.id = case
          when split_part(storage.objects.name, '/', 2)
            ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          then split_part(storage.objects.name, '/', 2)::uuid
        end
        and l.status = 'sold'
    )
  );

-- ── 5) 관리자 쓰기 소비처 — is_admin() → is_admin_active()로 교체 ──────────────────────────
-- 대상: profiles_update_admin·profiles_delete_admin(0005) · listings_delete_admin(0005) ·
--   chat_rooms_delete_admin·chat_messages_delete_admin(0005) ·
--   listing_images_objects_admin_delete(0014). 전부 **쓰기** 정책이다 — is_admin()을 쓰는
--   admin **읽기** 정책(listings_select_admin(0002)·profiles_select_admin(0001)·
--   chat_rooms_select_admin·chat_messages_select_admin(0005)·listing_images_select_admin(0012)·
--   listing_images_objects_owner_select의 관리자 분기(0014))은 위 불변식대로 하나도 건드리지 않는다.
drop policy if exists "profiles_update_admin" on public.profiles;
create policy "profiles_update_admin" on public.profiles
  for update to authenticated
  using (public.is_admin_active())
  with check (public.is_admin_active());

drop policy if exists "profiles_delete_admin" on public.profiles;
create policy "profiles_delete_admin" on public.profiles
  for delete to authenticated
  using (public.is_admin_active());

drop policy if exists "listings_delete_admin" on public.listings;
create policy "listings_delete_admin" on public.listings
  for delete to authenticated
  using (public.is_admin_active());

drop policy if exists "chat_rooms_delete_admin" on public.chat_rooms;
create policy "chat_rooms_delete_admin" on public.chat_rooms
  for delete to authenticated
  using (public.is_admin_active());

drop policy if exists "chat_messages_delete_admin" on public.chat_messages;
create policy "chat_messages_delete_admin" on public.chat_messages
  for delete to authenticated
  using (public.is_admin_active());

drop policy if exists "listing_images_objects_admin_delete" on storage.objects;
create policy "listing_images_objects_admin_delete" on storage.objects
  for delete to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and public.is_admin_active()
  );

-- ── 6) admin_restore_sold_listing RPC(0030) — is_admin() → is_admin_active() (DW-721) ─────
-- SECURITY DEFINER RPC는 RLS를 통째로 우회한다 — 위 5)에서 RLS 정책만 고쳐도 이 함수는 그대로
-- is_admin()을 쓰므로 정지된 관리자가 이 함수로 sold→on_sale을 계속 되돌릴 수 있었다(DW-721
-- 실측: 2026-08-07 로컬, rows=1·status가 실제로 on_sale로 바뀜). create or replace는 같은
-- 시그니처의 함수 소유권·GRANT를 그대로 유지하므로(0028이 handle_new_user에 이미 쓴 전제와
-- 동일) revoke/grant를 다시 하지 않는다 — 0030이 이미 authenticated에만 execute를 줬다.
create or replace function public.admin_restore_sold_listing(p_listing_id uuid)
returns table (id uuid)
language sql
security definer
set search_path = ''
as $$
  update public.listings
     set status = 'on_sale'
   where id = p_listing_id
     and status = 'sold'
     and public.is_admin_active()
  returning id;
$$;

comment on function public.admin_restore_sold_listing(uuid) is
  '관리자 판매완료 되돌리기(DW-391, Story 15.4 — DW-721로 Story 17.1이 is_admin()을
   is_admin_active()로 교체) — status만 sold→on_sale로 되돌린다. WHERE 절에 status=''sold''와
   is_admin_active()를 함께 걸어 "비관리자(또는 정지된 관리자) 호출"과 "이미 on_sale인 행
   호출"을 같은 0행 신호로 수렴시킨다(둘 다 클라이언트에서 굳이 구분하지 않는다). 그 0행이 어떤
   경로로 생겼는지(동시 호출 레이스인지, 화면이 낡아 이미 복구된 행을 다시 누른 것인지, 권한을
   잃었거나 정지된 것인지)는 이 함수가 구분하지도, 어느 테스트가 측정하지도 않는다(장부 DW-719 —
   0030의 이 문장은 아직 열린 항목의 유일한 코드 내 포인터라 재작성에서도 보존한다). 관찰 가능한
   계약은 이것뿐이다 — 0행 = "그 행이 sold가 아니었거나, 호출자가 활성 관리자가 아니다".
   컬럼·값을 파라미터로 받지 않는다 — status 외 다른 컬럼을 바꾸는 범용 UPDATE로 확장하지 않는다.';

-- ── 7) chat_messages_insert_participant(0003) — 정지 발신자 차단 ──────────────────────────
-- 결정: 막는다(사용자 지정 기본값 — Block-If 미충족). 근거: 0023의 방송 트리거(AFTER INSERT)와
-- 0024~0026의 안읽음 계산(INSERT 이후 SELECT)은 전부 "INSERT가 이미 성공한 뒤"에만 발화·조회
-- 한다 — 정지 발신자의 INSERT 자체를 막아도(=그 행이 존재하지 않으므로 트리거가 아예 안 돈다)
-- 다른 정상 참가자의 메시지 흐름에는 영향이 없다. 이 파일의 짝 테스트
-- (api/tests/integration/test_suspended_write_block_real_db.py)가 정상 참가자의 발신·방송·
-- 안읽음 카운트가 그대로 동작하는지 실DB로 재확인한다. docs/conventions.md §8에도 이 결정을
-- 한 줄로 등재한다.
drop policy if exists "chat_messages_insert_participant" on public.chat_messages;

create policy "chat_messages_insert_participant" on public.chat_messages
  for insert to authenticated
  with check (
    auth.uid() = sender_id
    and exists (
      select 1 from public.chat_rooms r
      where r.id = chat_messages.room_id
        and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
    )
    and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')
  );

-- ── 8) is_admin() 자체는 수정하지 않는다 ───────────────────────────────────────────────────
-- (Always 절 — 전역으로 좁히면 관리자 읽기 정책까지 함께 좁아진다. 이 파일 어디에도
--  `create or replace function public.is_admin()`이 없다는 사실 자체가 그 준수의 증거다.)

-- ── 9) 쓰기 경로 전수조사 (Always 2항 — "정책 N개 고쳤다"로 끝내지 않는다) ──────────────────
-- 실측 쿼리(2026-08-11, 로컬 55322, 이 파일 적용 후):
--   select schemaname, tablename, policyname, cmd from pg_policies
--     where cmd <> 'SELECT' and 'authenticated' = any(roles);        -- 21행
--   select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
--     where p.prosecdef and n.nspname='public';                       -- 11행
-- 아래는 그 21+11개 전량에 대한 "막는다/안 막는다 + 이유" 판정이다(grep 목록이 아니라 이 쿼리
-- 결과 그대로). 같은 표가 스펙 Design Notes에도 있고 docs/conventions.md §8에도 세 번째 요약이
-- 있다 — 세 곳에 값을 흩어 둔 것이 아니라, §8이 정본(project-context.md 규칙 1 "값은 한쪽에만
-- 산다")이고 여기 있는 사본은 §9.1의 self-contained 원칙("레포 파일만으로 빈 DB가 서야 한다")
-- 때문이다: 이 마이그레이션 파일 하나만 읽어도 무엇을 막고 안 막는지 판정이 보이게 하려는
-- 것이지, "이 실행의 guardrail이 스펙 파일 편집을 금지해서"가 아니다(그 서술은 사실이 아니었다
-- — 이 스토리도 bad_spec 루프백에서 스펙을 여러 차례 고쳤다, 2026-08-11 3차 코드리뷰 patch).
-- 세부 근거·귀결은 `_bmad-output/implementation-artifacts/deferred-work.md`(DW-799·DW-801·
-- DW-802)에도 남긴다.
--
-- authenticated 대상 non-SELECT 정책 21개:
--   막는다(이 파일 1~7절이 새로 걸거나 이미 걸려 있던 것): listings_insert_own·
--     listings_update_own·listings_delete_own(2) · listing_images_insert_own·
--     listing_images_update_own·listing_images_delete_own(3) ·
--     listing_images_objects_owner_insert·_update·_delete(4, storage.objects) ·
--     listings_delete_admin·profiles_update_admin·profiles_delete_admin·
--     chat_rooms_delete_admin·chat_messages_delete_admin·
--     listing_images_objects_admin_delete(5) · chat_messages_insert_participant(7).
--     = 16개. (listings 3 + listing_images 3 + storage owner 3 + 관리자 6 + 채팅 발신 1)
--   안 막는다(불변식 문장 — 매물·사진·파일·관리자 RPC·채팅 발신 — 밖이라고 판단, 근거는
--     deferred-work.md 참조):
--     · chat_rooms_insert_participant — 채팅방 "생성"은 판단 대상이 "발신"뿐이었다([[DW-799]]).
--     · wishlists_insert_own·wishlists_delete_own — 찜은 본인만 보는 개인화 데이터라 정지가
--       막으려는 "타인에게 영향을 주는 쓰기"와 성격이 다르다([[DW-801]]).
--     · chat_room_reads_insert_participant·chat_room_reads_update_own — 본인 안읽음 커서,
--       상대방에게 노출되지 않는다([[DW-802]]).
--     = 5개. (16 + 5 = 21, 실측과 일치.)
--   ⚠️ 이전 판은 이 두 수를 15/6으로 적었다 — increment_listing_view(함수)를 정책 그룹에도
--      잘못 계상해 합계만 우연히 21로 맞았다. 합계가 맞는다는 자기검사가 항목 누락을 못 잡는
--      상태였다(2026-08-11 2차 코드리뷰 지적 → pg_policies 재실측으로 정정).
--
-- public 스키마 SECURITY DEFINER 함수 11개:
--   막는다: admin_restore_sold_listing(6, is_admin_active()로 교체) · is_admin_active(1, 이
--     스토리가 신설).
--   전역 유지(Always 3항 — 건드리지 않음): is_admin().
--   해당 없음(트리거 부산물 — 이미 정지 조건이 걸린 INSERT가 성공해야만 호출되므로, 그
--     INSERT를 막으면 이 함수는 애초에 안 불린다. 함수 자체에 조건을 걸 필요가 없다):
--     chat_messages_broadcast·chat_rooms_touch_last_message(0003·0023, chat_messages INSERT
--     트리거) · enforce_chat_room_seller·set_chat_room_names(0003, chat_rooms INSERT 트리거 —
--     단 chat_rooms INSERT 자체는 안 막는다는 판단이 위 DW-799라 이 함수들도 정지 회원이
--     생성한 방에서는 여전히 돈다. 그 방에 값을 채워 넣을 뿐 정지 여부와 무관한 로직) ·
--     set_listing_seller_name(0007, listings INSERT 트리거 — listings INSERT 자체가 이미
--     막히므로 정지 회원 경로에서는 안 불린다).
--   해당 없음(anon도 호출 — profiles 신원 자체가 없어 정지 게이트를 걸 수 없다):
--     increment_listing_view(조회수 집계, 불변식의 "매물 쓰기" 범주 밖이라는 판단도 함께).
--   해당 없음(가입 트리거 — 아직 존재하지 않는 사용자를 다루므로 "정지된 사용자의 쓰기"라는
--     전제 자체가 성립하지 않는다): handle_new_user(0033이 이번 스토리에서 별도로 손봤다,
--     DW-682 — 정지 게이트와는 다른 축).
--   해당 없음(읽기 전용, §6이 이미 문서화): get_seller_public_summary.
--   = 11개, 실측과 일치.
