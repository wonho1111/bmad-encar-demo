-- 04_trust_backfill.sql — 신뢰속성이 **비어 있는 매물 전부**를 데모값으로 채운다 (2026-08-13 사용자 승인)
--
-- 왜 필요한가: 신뢰속성 3컬럼(accident_status·is_single_owner·is_non_smoker)은 2026-07(Story 10.1)에
--   만들어졌지만 **폼에 입력 경로가 없어서** 한 번도 채워진 적이 없다(2026-08-13에 입력 UI를 만들었다).
--   그 결과 로컬 166건 중 104건이 세 값 모두 NULL이었고, 상세 화면엔 "판매자가 입력하지 않았어요"가,
--   카드엔 뱃지가 하나도 안 떴다. 데모로서 화면의 절반이 비어 보이는 상태다.
--
-- 왜 부분 backfill(=예전 "무사고 차량" 체크박스 값으로 accident_status를 유추)이 아닌가:
--   ① 그 체크박스는 **사고이력 하나**만 안다 — 1인소유·비흡연은 애초에 물어본 적이 없어 유추할 근거가 없다.
--   ② 사고이력조차 절반만 된다 — 체크가 꺼져 있던 행이 '단순교환'인지 '사고'인지 구분할 수 없다.
--   즉 그 방식으로는 필터 3개 중 2개가 여전히 빈다.
--
-- 정직성(0017이 "backfill 안 함"으로 정했던 이유)과의 관계:
--   0017의 취지는 *실제 판매자가 신고하지 않은 것을 신고한 것처럼 꾸미지 말 것*이다. 여기서 채우는
--   대상은 **데모용 가공 데이터**(운영 스냅샷 시드)라 그 문제가 성립하지 않는다. 사용자 판단·승인으로 채운다.
--   ⚠️ 그래서 이 파일은 **폼으로 들어온 값은 절대 덮어쓰지 않는다** — 아래 모든 UPDATE가 `is null`
--      조건을 달고 있어, 판매자가 실제로 신고한 값이 있으면 손대지 않는다.
--
-- 왜 DELETE 후 재삽입이 아닌가(03_trust_demo.sql과 같은 이유, 대장 #27/#89):
--   listings를 지우면 listing_images·chat_rooms·wishlists가 **FK cascade로 함께 사라진다**
--   (실측: 세 제약 모두 confdeltype='c'). 사진·채팅방·찜을 날리지 않으려면 UPDATE만 해야 한다.
--
-- 멱등성·재현성: 값은 매물 id의 md5 해시로 **결정적으로** 고른다(난수 아님).
--   · 몇 번을 다시 돌려도 같은 매물에 같은 값이 들어간다.
--   · 로컬과 운영이 같은 id를 가지면 같은 결과가 나온다(운영 스냅샷 기반이라 대체로 그렇다).
--   `('x'||substr(md5(...),1,4))::bit(16)::int`는 항상 0~65535다(음수가 안 나오므로 abs가 필요 없다 —
--   bit(32)::int를 쓰면 음수가 나와 `% 100`이 음수가 될 수 있다).
--
-- 분포(사용자 승인): 무사고 ~75% / 단순교환 ~15% / 사고 ~10%.
--   단 **기존 accident_free=false인 행은 '무사고'로 만들지 않는다** — 그 값은 이미 있던 신호이고,
--   덮으면 예전 데이터와 모순되는 행을 우리가 직접 만드는 셈이다. 그 행들은 단순교환/사고로만 간다.
--
-- 1인소유·비흡연은 **일부만** true로 채우고 나머지는 NULL로 남긴다. 전부 켜면 모든 카드에 뱃지가
--   붙어 뱃지가 아무것도 구분하지 못한다(= 정보가 아니게 된다). 대략 절반이 목표다.
--
-- 실행: scripts/seed-local.sh 가 03 다음 순서로 psql -f 실행한다.
--   운영에 적용할 때도 **이 파일 그대로** 실행한다(로컬 전용 가정이 없다 — 세션 변수·로컬 경로를 안 쓴다).

\set ON_ERROR_STOP on

-- ── 사전 관측 ────────────────────────────────────────────────────────────────
-- 채우기 전 상태를 남긴다. "몇 건이 비어 있었나"를 나중에 로그로 확인할 수 있어야
-- 이 파일이 실제로 무슨 일을 했는지 사후에 대조할 수 있다(B4 — 실행됐다 ≠ 채워졌다).
do $$
declare v_null_status int; v_null_single int; v_null_smoker int;
begin
  select count(*) filter (where accident_status is null),
         count(*) filter (where is_single_owner is null),
         count(*) filter (where is_non_smoker  is null)
    into v_null_status, v_null_single, v_null_smoker
    from public.listings;
  raise notice '[04_trust_backfill] 적용 전 NULL — 사고이력 %건, 1인소유 %건, 비흡연 %건',
    v_null_status, v_null_single, v_null_smoker;
end $$;

-- ── ① 사고이력 ──────────────────────────────────────────────────────────────
-- accident_free=false였던 행은 '무사고'를 피한다(위 주석). 나머지는 75/15/10으로 나눈다.
update public.listings
   set accident_status = case
         when accident_free = false
           then case when ('x' || substr(md5(id::text || 'accident'), 1, 4))::bit(16)::int % 100 < 60
                     then '단순교환' else '사고' end
         else case
                when ('x' || substr(md5(id::text || 'accident'), 1, 4))::bit(16)::int % 100 < 75 then '무사고'
                when ('x' || substr(md5(id::text || 'accident'), 1, 4))::bit(16)::int % 100 < 90 then '단순교환'
                else '사고'
              end
       end
 where accident_status is null;

-- ── ② accident_free 동기화 ──────────────────────────────────────────────────
-- 이제 accident_free는 **파생값**이다(폼도 accident_status에서 계산해 넣는다, SellForm.tsx).
-- 컬럼을 지우지 않는 이유: AI 검색이 이 컬럼을 쓴다(api/app/graph/sql_rag_node.py 지시문 —
-- "사고 관련 질문은 accident_status가 아니라 accident_free로 판단하라"). 두 칸이 어긋나면
-- 필터 결과(accident_status 기준)와 AI 결과(accident_free 기준)가 서로 다른 매물을 낸다.
update public.listings
   set accident_free = (accident_status = '무사고')
 where accident_status is not null
   and accident_free is distinct from (accident_status = '무사고');

-- ── ③ 1인소유 · 비흡연 ───────────────────────────────────────────────────────
-- 비어 있는 행 중 일부만 true. 임계값 25는 "채운 뒤 전체의 절반 안팎"이 되도록 고른 값이다
-- (적용 시점 실측: 각각 116·117건이 NULL이고 이미 true인 행이 50·49건 → +29 ≒ 전체의 47%).
-- salt를 다르게 줘서 두 속성이 **같은 매물에 함께 붙지 않도록** 한다(같은 해시를 쓰면 1인소유가
-- 켜진 매물은 항상 비흡연도 켜져 두 뱃지가 늘 붙어 다닌다 — 구분이 안 된다).
update public.listings
   set is_single_owner = true
 where is_single_owner is null
   and ('x' || substr(md5(id::text || 'single_owner'), 1, 4))::bit(16)::int % 100 < 25;

update public.listings
   set is_non_smoker = true
 where is_non_smoker is null
   and ('x' || substr(md5(id::text || 'non_smoker'), 1, 4))::bit(16)::int % 100 < 25;

-- ── 사후 검증 ────────────────────────────────────────────────────────────────
-- "에러 없이 실행됨"은 "채워짐"이 아니다(B4). 세 가지를 실제로 확인한다:
--   ⓐ 사고이력에 NULL이 하나도 안 남았는가(이 파일의 존재 이유)
--   ⓑ accident_free가 accident_status와 100% 일치하는가(어긋나면 필터와 AI가 갈린다)
--   ⓒ 세 값이 한쪽으로 쏠려 뱃지가 의미를 잃지 않았는가(무사고가 전부이거나 0이면 실패)
do $$
declare
  v_null_status int; v_mismatch int; v_free int; v_total int;
  v_single int; v_smoker int;
begin
  select count(*) into v_total from public.listings;
  select count(*) into v_null_status from public.listings where accident_status is null;
  select count(*) into v_mismatch from public.listings
   where accident_status is not null and accident_free is distinct from (accident_status = '무사고');
  select count(*) into v_free   from public.listings where accident_status = '무사고';
  select count(*) into v_single from public.listings where is_single_owner = true;
  select count(*) into v_smoker from public.listings where is_non_smoker = true;

  if v_null_status > 0 then
    raise exception '[04_trust_backfill] 사고이력이 아직 %건 비어 있습니다 — UPDATE 대상 술어를 확인하세요.', v_null_status;
  end if;
  if v_mismatch > 0 then
    raise exception '[04_trust_backfill] accident_free가 accident_status와 어긋난 행이 %건입니다 — '
      '필터(뱃지 기준)와 AI 검색(accident_free 기준)이 서로 다른 결과를 냅니다.', v_mismatch;
  end if;
  -- 쏠림 가드: 무사고가 전체이거나 0이면 "사고/단순교환 뱃지"를 데모에서 볼 수 없다.
  if v_free = 0 or v_free = v_total then
    raise exception '[04_trust_backfill] 무사고가 %건/전체 %건으로 쏠렸습니다 — 다른 상태 뱃지를 '
      '화면에서 확인할 수 없습니다.', v_free, v_total;
  end if;

  raise notice '[04_trust_backfill] 적용 후 — 전체 %건 / 무사고 %건 / 1인소유 %건 / 비흡연 %건',
    v_total, v_free, v_single, v_smoker;
end $$;
