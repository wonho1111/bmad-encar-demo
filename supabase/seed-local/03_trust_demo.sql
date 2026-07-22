-- 03_trust_demo.sql — 로컬 신뢰속성 데모값 (Story 10.2, additive)
--
-- 왜 필요한가: 02_data.sql이 채우는 listings는 운영 스냅샷(data/listings.json)이고, 신뢰속성
--   3컬럼(accident_status·is_single_owner·is_non_smoker)은 스냅샷 시점 전부 NULL이다(10.1 원칙 —
--   backfill 없음). 뱃지 렌더를 로컬에서 눈으로 확인하려면 대표 소수에 값을 심어야 한다.
--
-- 왜 멱등 UPDATE인가(delete 없음, 대장 #89 재현 안 함): 02_data.sql처럼 delete 후 재삽입하면
--   listing_images가 FK cascade로 함께 사라진다(#27/#89). 이 파일은 UPDATE만 해서 그 문제를
--   구조적으로 피한다 — 몇 번을 다시 돌려도 같은 4건에 같은 값이 들어갈 뿐이다.
--
-- 왜 manufacturer/model로 안 고르나: seed.sql(운영 정본)은 UPDATE 대상을 (seller_id, manufacturer,
--   model, year)로 특정하지만, 이 파일이 대상으로 하는 02_data.sql의 listings는 운영 스냅샷이라
--   seed.sql이 만드는 것과 **같은 id를 갖는다는 보장이 없다**(스냅샷 시점이 다르면 id도 다르다).
--   그래서 대신 이미 있는 accident_free(bool, NOT NULL)와 id 정렬만으로 결정적으로 4건을 고른다 —
--   데이터셋이 무엇이든(스냅샷이 바뀌어도) 같은 술어로 같은 개수를 고르므로 재현 가능하다.
--
-- ⚠️ **왜 status='on_sale'도 걸어야 하나 (코드리뷰 2026-07-22 P2 — sold 오염 실측):**
--   `buyerListingsQuery`(/search·/listings/[id] 둘 다의 시작점, FR11 단일 출처)는 `status='on_sale'`
--   만 보여준다. accident_free만 보고 골라 sold 행에 값을 심으면, 이 스토리가 데모하려는 화면에는
--   **영원히 안 보이는 뱃지**가 생긴다 — AC9(네 상태가 눈에 구분돼 보임)가 조용히 깨진다. 로컬
--   스냅샷엔 sold 8건이 섞여 있어 이 조건 없이는 실제로 걸릴 수 있는 경로였다(실측).
--
-- 어느 매물에 무엇을 심었나:
--   status='on_sale' + accident_free=true인 매물 중 id 오름차순 첫 2건
--     → 무사고 + 1인소유 + 비흡연(초록 뱃지·칩 3개)
--   status='on_sale' + accident_free=false인 매물 중 id 오름차순 1번째 → 사고(중립 상태칩)
--   status='on_sale' + accident_free=false인 매물 중 id 오름차순 2번째 → 단순교환(중립 상태칩)
--   나머지는 전부 NULL로 남는다(미표시 상태도 함께 보여야 네 상태가 다 보인다, AC9).
--
-- 실행: scripts/seed-local.sh 가 02_data.sql 다음 순서로 psql -f 실행한다(아래 스크립트 편입).

\set ON_ERROR_STOP on

-- ── 게이팅(코드리뷰 2026-07-22 P3과 같은 사유로 P2에도 적용) ────────────────────────
-- 대상 후보가 부족하면(스냅샷이 작아지는 등) 아래 UPDATE들은 에러 없이 조용히 1건만 심거나
-- 0건을 심는다 — "에러 없음"이 "정상"이 아니다(대장 #27이 이미 겪은 실패 모드와 같은 성격).
-- 그래서 대상이 되는 4건을 실제로 채울 수 있는지 먼저 확인하고, 부족하면 크게 실패시킨다.
do $$
declare
  v_free_count     int;
  v_accident_count int;
begin
  select count(*) into v_free_count
    from public.listings
   where status = 'on_sale' and accident_free = true;

  select count(*) into v_accident_count
    from public.listings
   where status = 'on_sale' and accident_free = false;

  if v_free_count < 2 then
    raise exception '[03_trust_demo] status=on_sale AND accident_free=true 매물이 2건 미만입니다'
      '(실제 %건) — 무사고+1인소유+비흡연 데모값 2건을 채울 수 없습니다. 로컬 스냅샷 '
      '(data/listings.json)이 줄었는지 확인하세요.', v_free_count;
  end if;

  if v_accident_count < 2 then
    raise exception '[03_trust_demo] status=on_sale AND accident_free=false 매물이 2건 미만입니다'
      '(실제 %건) — 사고·단순교환 데모값을 각 1건씩 채울 수 없습니다. 로컬 스냅샷 '
      '(data/listings.json)이 줄었는지 확인하세요.', v_accident_count;
  end if;
end $$;

update public.listings
   set accident_status = '무사고', is_single_owner = true, is_non_smoker = true
 where id in (
   select id from public.listings
    where status = 'on_sale' and accident_free = true
    order by id limit 2
 );

update public.listings
   set accident_status = '사고'
 where id = (
   select id from public.listings
    where status = 'on_sale' and accident_free = false
    order by id limit 1
 );

update public.listings
   set accident_status = '단순교환'
 where id = (
   select id from public.listings
    where status = 'on_sale' and accident_free = false
    order by id offset 1 limit 1
 );
