-- 0014_listing_images_public_bucket.sql — Story 9.0: 비공개 버킷 + 서명 URL → 공개 버킷 + 고정 URL
--
-- 무엇을 바꾸나:
--   1) 버킷 listing-images를 public = true로 전환 (동시에 5MB·MIME 3종 상한을 UPDATE로 재확정 — #44 해소)
--   2) storage.objects 읽기 정책을 listing_images 조인 → 경로 기반(소유자·관리자)으로 교체
--   3) 관리자 DELETE 정책 추가 (관리자 매물 삭제가 사진을 정리할 수 있어야 함)
--
-- 왜 뒤집나 (사용자 결정 2026-07-19):
--   FR11을 "사진 바이너리까지 접근 불가"로 해석해 비공개+서명URL을 골랐는데, 그 복잡도를 다 치르고도
--   서명 URL은 발급 시점에만 RLS를 보고 TTL(1시간) 동안 재검사하지 않아 sold 전환 후에도 뚫려 있었다
--   (docs/tech-debt.md #50-2 — "수용"으로 기록돼 있었다). 비용은 전부 내고 효과는 못 얻은 상태였다.
--   그 대가로 #45·#46·#50-2·#55·#62가 열렸다. 사진 URL은 FR11 강제 대상에서 내리고 명시 수용한다.
--   매물이 목록·상세·AI에서 안 보이는 것은 listings RLS·sql_guard가 계속 강제한다(변경 없음).
--
-- 무엇을 바꾸지 않나 (중요):
--   - 업로드(쓰기) 권한: 본인 경로에만. 0012·0013의 insert/update/delete 정책 그대로. "공개"는 읽기만이다.
--   - 경로 무결성 트리거(0013), 10장 트리거, listing_images 테이블 RLS, ai_readonly 정책.
--   - MIME 3종 화이트리스트: 공개 버킷에선 오히려 더 중요하다 — 인증 없이 열리므로
--     .html/.svg가 올라가면 우리 도메인에서 실행되는 저장형 XSS가 된다.
--
-- 전진 전용(forward-only). 되돌리는 마이그레이션을 만들지 않는다(docs/conventions.md §9).
-- 계약값(버킷명·경로·상한)의 정본은 docs/conventions.md §10 — 여기 값을 다시 적지 않는다.

-- ── 1) 버킷 공개 전환 + 상한 재확정 ───────────────────────────────────
-- 0012는 insert ... on conflict (id) do nothing이라, 버킷이 이미 존재하면 public·5MB·MIME이
-- 조용히 무효였다(#44).
--
-- ✎ 2026-07-19 코드리뷰 정정: 처음엔 위를 bare UPDATE로 고쳤는데, 그건 구멍을 옮긴 것뿐이었다 —
--   UPDATE는 대상 행이 **없으면** 0행에 적중하고도 성공한다. 즉 "이미 있으면 무효"가
--   "없으면 무효"로 바뀌었을 뿐인데 #44는 해소로 선언됐다. fresh DB·복구 시나리오(0012가 만들지
--   못했거나 대시보드에서 버킷이 지워진 경우)에서 마이그는 초록인데 상한이 전부 미설정으로 남는다.
--   insert ... on conflict do update는 두 구멍을 다 막는다: 없으면 만들고, 있으면 값을 덮어쓴다.
--   §9.3 (a) 자율 처리 — 멱등 가드 추가만이고, 원격 실측 결과 델타 0이다
--   (2026-07-19 조회: public=true · file_size_limit=5242880 · {image/jpeg,image/png,image/webp}).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'listing-images',
  'listing-images',
  true,
  5242880,                                                           -- 5MB (docs/conventions.md §10)
  array['image/jpeg', 'image/png', 'image/webp']                     -- 저장형 XSS 방지
)
on conflict (id) do update
set
  public             = excluded.public,
  file_size_limit    = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- ── 2) 읽기 정책 교체: listing_images 조인 → 경로 기반 ────────────────
-- 기존(0012 listing_images_objects_read)은 "그 파일을 가리키는 listing_images 행이 살아 있고
-- 그 매물이 on_sale이거나 본인 소유일 때만" 읽기를 허용했다. 이 조인이 두 가지를 만들었다:
--   (a) 행이 먼저 사라진 파일은 소유자에게도 안 보여 정상 권한으로 영영 못 지웠다(#46 — 실제 2건 발생).
--       Storage API의 DELETE·LIST는 대상을 먼저 SELECT로 찾기 때문이다(#51 규명 결과).
--   (b) 관리자는 storage.objects 쪽에 분기가 없어 sold 매물 사진 바이너리를 못 봤다(#45).
-- 공개 전환으로 익명 읽기는 /object/public/ 경로가 담당하고 RLS를 타지 않는다. 그래서 이 정책은
-- 이제 "인증 사용자가 자기 파일을 목록·삭제하기 위한" 용도만 남고, 경로만 보면 충분하다.
drop policy if exists "listing_images_objects_read" on storage.objects;
drop policy if exists "listing_images_objects_owner_select" on storage.objects;

create policy "listing_images_objects_owner_select" on storage.objects
  for select to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and (
      split_part(storage.objects.name, '/', 1) = auth.uid()::text  -- 경로 첫 세그먼트 = 소유자(0012 경로 규칙)
      or public.is_admin()                                          -- 관리자는 sold 포함 전체(#45)
    )
  );
-- is_admin()을 여기 써도 안전하다: 이 정책은 to authenticated이고, is_admin()의 EXECUTE도
-- authenticated에만 있다(0001_profiles.sql:90-91). anon은 이 정책 자체에 걸리지 않는다.
-- (0012가 is_admin()을 피했던 이유는 그 정책이 anon까지 대상으로 삼았기 때문이다 — 이제 아니다.)

-- ── 3) 관리자 DELETE 정책 ─────────────────────────────────────────────
-- 관리자 매물 삭제가 사진 오브젝트를 정리하려면 관리자에게 DELETE가 있어야 한다.
-- 0013의 owner_delete는 경로 첫 세그먼트=본인만 허용하므로 남의 매물엔 걸리지 않는다.
-- 다중 permissive 정책은 OR로 합쳐지므로 owner_delete는 그대로 두고 한 장을 더 얹는다.
drop policy if exists "listing_images_objects_admin_delete" on storage.objects;

create policy "listing_images_objects_admin_delete" on storage.objects
  for delete to authenticated
  using (
    storage.objects.bucket_id = 'listing-images'
    and public.is_admin()
  );
