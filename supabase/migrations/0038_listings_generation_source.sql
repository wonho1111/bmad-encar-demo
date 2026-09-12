-- 0038_listings_generation_source.sql — listings에 세대(generation)·출처(source) 컬럼 추가 (DW-874/853)
--
-- self-contained: listings 테이블·RLS·authenticated INSERT 컬럼 GRANT는 0002/0020에서 이미
--   만들어졌다. 이 파일은 **컬럼 2개 + 기존 행 채우기 UPDATE + authenticated INSERT 권한 확장**만
--   더한다(additive, 더하기만).
--
-- 왜 필요한가(DW-874) — listings.model 한 열에 모델군·세대·부분변경('더 뉴'/'올 뉴')·배기량
--   트림('3.3')·연료 접미('하이브리드')가 섞여 있다. TabPFN 11번째 특징(api/app/market_price.py
--   `_tabpfn_features_with_model`)이 이 model 문자열 전체를 범주 코드로 쓰다 보니, 같은 세대인데
--   표기만 다른 매물이 다른 코드를 받아 같은 세대끼리 묶이지 않는다(예: "아반떼 MD"/"아반떼MD"
--   (DW-853), "그랜저 GN7"/"그랜저 GN7 하이브리드"). generation을 model에서 분리해 이 코드의
--   입력으로 쓰면 표기 잡음이 사라진다.
--
-- ── 1) generation·source 컬럼(둘 다 nullable — DB는 되돌리기가 없다, CLAUDE.md B3) ─────
alter table public.listings add column if not exists generation text null;
alter table public.listings add column if not exists source text null;

comment on column public.listings.generation is
  '세대코드, 형식 "[더 뉴 |올 뉴 ]모델군 세대코드"(예: "그랜저 GN7", "더 뉴 그랜저 IG").
   연료 접미("하이브리드")·배기량 트림("3.3")은 제외한다(DW-874). NULL = 세대 표기 없음/불명
   (예: "그랜저", "K5") — 이 경우 TabPFN 11번째 특징은 model 문자열로 폴백한다.';

comment on column public.listings.source is
  '데이터 출처 표식(예: "encar_eval_20260905" — 엔카 수집·검증 배치). 시드·사용자 등록 매물은
   NULL. 분석·회귀 비교에서 배치 단위로 표본을 구분하려는 목적이고, 접근 제어와는 무관하다.';

-- ── 2) 기존 행 채우기 — model에서 세대코드만 뽑아낸다(generation IS NULL인 행만) ────────
-- 순서(요구사항 고정): ① 하이브리드 접미 제거 → ② 배기량 트림 접미(\d\.\d) 제거 →
--   ③ 한글 바로 뒤에 붙은 영문 세대코드 앞에 공백 삽입("아반떼MD"→"아반떼 MD") → ④ 공백 정리.
-- 결과가 `^(더 뉴 |올 뉴 )?[가-힣0-9]+ [A-Z]{1,3}[0-9]{0,2}$`에 맞을 때만 generation에 넣는다 —
-- "그랜저"·"K5"처럼 세대 표기가 아예 없는 model은 이 정규식에 걸리지 않아 NULL로 남는다
-- (의도된 동작 — 세대를 지어내지 않는다, A1 가정 명시).
update public.listings l
set generation = c.candidate
from (
  select
    id,
    regexp_replace(
      regexp_replace(
        regexp_replace(
          regexp_replace(
            regexp_replace(model, '\s*하이브리드$', ''),
            '\s+\d\.\d$', ''
          ),
          '([가-힣])([A-Z])', '\1 \2', 'g'
        ),
        '\s+', ' ', 'g'
      ),
      '^\s+|\s+$', '', 'g'
    ) as candidate
  from public.listings
  where generation is null
) c
where l.id = c.id
  and c.candidate ~ '^(더 뉴 |올 뉴 )?[가-힣0-9]+ [A-Z]{1,3}[0-9]{0,2}$';

-- ── 3) authenticated INSERT 컬럼 권한 확장 ────────────────────────────────────────────
-- 0020이 authenticated의 INSERT를 컬럼 화이트리스트로 좁혀 뒀다(테이블 전체 GRANT를 회수하고
-- 목록만 재부여 — 그 목록에 없는 컬럼은 기본이 "막힘"). 새 컬럼 2개를 등록 시점에 채우려면
-- 그 목록에 추가해야 한다. GRANT는 누적이므로 이 한 줄이 기존 0020 목록 위에 얹힌다.
-- anon은 listings에 직접 쓰는 정당한 경로가 없으므로(0020 5번 블록) 추가하지 않는다.
grant insert (generation, source) on public.listings to authenticated;

-- ai_readonly는 0006에서 `grant select on all tables in schema public`로 **테이블 전체** SELECT를
-- 이미 받았다(컬럼 단위가 아니다) — 새 컬럼도 자동으로 보인다. 0011(anon)은 화이트리스트를
-- 명시적으로 넓히는 정책 판단이 필요해(연료·트림처럼 이미 노출 중인 정보가 아니다) 이 파일
-- 범위 밖으로 둔다 — anon에는 generation·source 어느 것도 추가하지 않는다.
