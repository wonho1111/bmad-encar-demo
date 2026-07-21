-- 0015_listings_update_not_sold.sql — 판매완료(sold) 매물의 수정을 DB에서 막는다 (tech-debt #54)
-- self-contained: listings 테이블·RLS enable·listings_update_own 정책은 0002에서 이미 만들어졌다.
--   이 파일은 그 정책 **하나만** 교체한다. 테이블·트리거·GRANT는 건드리지 않는다.
--
-- 무엇이 문제였나:
--   0002의 listings_update_own은 `using (auth.uid() = seller_id)` 뿐이라 **status 조건이 없었다.**
--   그래서 수정 폼을 열어둔 채 다른 탭에서 구매완료 처리하면, 이미 sold가 된 매물이 그대로
--   수정된다. 지금까지 이걸 막고 있던 건 화면 층(수정 버튼을 canEdit로 가리는 것) 하나뿐이었다 —
--   화면이 하나 늘 때마다 다시 막아야 하는 구조다. 그래서 데이터 계층에 박는다(CLAUDE.md B9).
--   2026-07-21 실측(red): 시드 판매자 JWT로 sold 매물 price PATCH → HTTP 200 · 1행 변경(뚫림).
--
-- ⚠️ `using`에만 조건을 건다 — `with check`에는 걸지 않는다.
--   · using   = **변경 전(OLD) 행**에 대한 조건 → "이미 sold인 행은 고를 수 없다"
--   · with check = **변경 후(NEW) 행**에 대한 조건 → 여기에 status <> 'sold'를 걸면
--     on_sale → sold 전환 자체가 막힌다. 그건 FR7(구매 완료 처리)을 통째로 죽이는 것이다.
--   즉 "sold로 바꾸는 것"은 계속 허용하고, "sold가 된 뒤에 고치는 것"만 막는 게 정확한 요구다.
--   (전이 규칙은 on_sale → sold 단방향이며 되돌리기가 없다 — web ListingActions.tsx ·
--    app listings_repository.dart::markSold 양쪽이 이미 그 전제로 짜여 있다.)
--
-- 소비처 영향: web/app 모두 UPDATE 결과 행 수를 보고 0행이면 "권한 없음"으로 안내한다
--   (SellForm.tsx · ListingActions.tsx · listings_repository.dart). RLS 거부는 에러가 아니라
--   0행으로 오므로 별도 코드 변경이 필요 없다.

drop policy if exists "listings_update_own" on public.listings;

create policy "listings_update_own" on public.listings
  for update to authenticated
  using (auth.uid() = seller_id and status <> 'sold')
  with check (auth.uid() = seller_id);
