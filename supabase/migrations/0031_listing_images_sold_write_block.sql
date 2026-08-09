-- 0031_listing_images_sold_write_block.sql — DW-390 해소: listing_images 쓰기 3정책에 sold 차단 추가
-- self-contained: 이 마이그가 참조하는 것은 자기보다 앞 번호의 public.listing_images(0012)·
--   public.listings(0002)뿐이다. 뒤 번호를 가정하지 않는다.
--
-- 왜 필요한가 (DW-390, 원출처 2026-07-21 코드리뷰 원격 DB 실측):
--   0015가 listings 테이블에는 authenticated UPDATE에서 sold 행을 뺐지만, RLS 조건은
--   테이블마다 따로 붙는다 — listing_images의 insert/update/delete 3정책은 여전히
--   "이 사진이 달린 매물의 주인이 나인가"만 보고 매물 상태는 보지 않는다. 그래서 판매완료된
--   매물의 사진을 추가·교체·삭제하는 것을 DB가 막지 않았다(원격 pg_policies 조회로 확인).
--   Story 16.7(앱 사진 업로더)이 이 구멍을 그대로 물려받기 전에, 화면 방어를 또 짜는 대신
--   DB 레벨로 강제한다(CLAUDE.md B9 "화면 방어로 대체하지 않는다").
--
--   drop policy → create policy(같은 이름, 같은 파일 안에서 즉시 재생성)는 docs/conventions.md
--   §9.1이 명시적으로 허용한 전진 패턴이다 — 정책은 데이터가 아니라 접근 규칙이라 소실이 없다.

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
  )
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
  );

create policy "listing_images_delete_own" on public.listing_images
  for delete to authenticated using (
    exists (
      select 1 from public.listings l
      where l.id = listing_images.listing_id
        and l.seller_id = auth.uid()
        and l.status <> 'sold'
    )
  );
