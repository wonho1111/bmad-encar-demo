-- 0021_listings_view_count_anon_grant.sql — anon view_count SELECT 권한 + 정렬용 부분 인덱스 (Story 11.4)
-- 적용 순서: 0001 → … → 0020 → 0021(이 파일). self-contained: 참조하는 listings.view_count는
--   0020에서 이미 존재한다.
--
-- 왜 필요한가(대장 #134·#144, docs/tech-debt.md):
--   Story 11.4가 "인기(view_count desc)" 그리드를 랜딩에 추가한다. 그런데 0011은 anon의 listings
--   SELECT를 테이블 단위에서 회수하고 컬럼 화이트리스트로 되돌린 구조라, 0020이 나중에 추가한
--   view_count는 그 목록에 없어 anon에게 기본적으로 안 보인다(0011 주석이 명시한 의도된 동작).
--   실측(#134, 스크래치 PG18, 0020까지 적용): `set local role anon; select view_count from
--   public.listings` → `ERROR: permission denied for table listings`. Postgres는 ORDER BY 대상
--   컬럼에도 SELECT 권한을 요구하므로 `order by view_count desc`도 같은 42501로 죽는다 — 로그인
--   상태(authenticated)는 테이블 단위 SELECT를 그대로 갖고 있어 안 걸리는 비대칭이라 로그인 상태만
--   검증하면 이 결함을 놓친다(비로그인으로 반드시 확인, intent-contract Always 참조).
--   그리고 #144: view_count 컬럼엔 정렬용 인덱스가 없다(0020은 컬럼만 추가) — 인덱스 없이
--   `order by view_count desc limit 4`를 랜딩 매 요청마다 돌리면 매물 전량 seq scan + sort가 된다.
--
-- ── 1) anon에 view_count SELECT 권한 추가(#134 해소) ─────────────────
-- 0011의 컬럼 화이트리스트에 한 줄을 더하는 것과 동일 효과 — 테이블 전체 재회수(revoke)는
-- 필요 없다(이미 0011이 회수해둔 상태), 이 컬럼 하나만 추가로 grant하면 된다.
grant select (view_count) on public.listings to anon;

-- ── 2) 인기 정렬용 부분 인덱스(#144 해소) ───────────────────────────
-- `where status = 'on_sale'`: 인기 그리드는 항상 buyerListingsQuery(FR11, on_sale만)를 거치므로
-- 정렬·필터 대상 행이 on_sale로 이미 좁혀져 있다 — 인덱스도 그 부분집합만 커버하면 충분하고,
-- sold 행까지 인덱싱하는 것은 크기만 늘리는 낭비다(A2). 내림차순(`desc`)으로 만들어
-- `order by view_count desc` 방향과 일치시킨다(정렬 방향이 다르면 인덱스를 못 타고 역순 스캔한다).
create index if not exists listings_view_count_idx
  on public.listings (view_count desc)
  where status = 'on_sale';
