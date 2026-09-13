-- 0039_listings_usage_history.sql — listings에 이용 이력(usage_history) 컬럼 추가 (DW-880, 2026-09-13)
--
-- self-contained: listings 테이블·RLS·authenticated INSERT/UPDATE 컬럼 GRANT는 0002/0020에서 이미
--   만들어졌다. 이 파일은 **컬럼 1개 + authenticated INSERT·UPDATE 권한 확장**만 더한다(additive).
--
-- 왜 필요한가(DW-880) — 엔카 실매물 7,081건 회귀에서 렌트 이력 차는 같은 세대·연식·주행·사고
--   조건에서 중앙값 −6.9%(세대별 −2~−13%, 14세대 중 11세대 유의) 싸게 팔린다. 시세 엔진의 TabPFN
--   특징에는 이 정보가 없어 렌트 이력 차를 실제보다 +3.3% 높게 본다(955건 실측, 이력 없는 차는 +0.3%).
--   수집 데이터(usageChangeTypes)에는 값이 있는데 제품 스키마에 열이 없어 못 쓰고 있었다.
--
-- 값: '없음' | '렌트' | '영업용' | NULL(미입력). '없음'은 "이력이 없다고 확인됨", NULL은 "모름" —
--   accident_status(0017)와 같은 3상태 관례. 기존 행은 채우지 않는다(backfill 안 함 — 시드·사용자
--   매물은 알 수 없고, 엔카 행은 로더 --backfill-usage-prod가 수집 데이터로 채운다).
alter table public.listings
  add column if not exists usage_history text
    check (usage_history in ('없음', '렌트', '영업용'));

comment on column public.listings.usage_history is
  '이용 이력(없음/렌트/영업용). NULL=미입력. 렌트·영업용 이력은 시세 엔진 TabPFN 12번째 특징(DW-880).
   등록 폼 입력란은 아직 없음 — 엔카 적재 행은 load_encar_listings.py가 수집 데이터로 채운다.';

-- authenticated: 0020이 INSERT·UPDATE를 컬럼 화이트리스트로 좁혀 뒀다(목록에 없으면 막힘). 로더가
-- 판매자 토큰으로 POST(신규)·PATCH(기존 엔카 행 채우기)하므로 둘 다 연다. anon은 열지 않는다
-- (0011 화이트리스트 정책 판단은 이 파일 범위 밖 — 화면 노출은 별도 항목).
grant insert (usage_history), update (usage_history) on public.listings to authenticated;
