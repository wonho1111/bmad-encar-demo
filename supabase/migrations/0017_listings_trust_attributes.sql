-- 0017_listings_trust_attributes.sql — 신뢰속성 3컬럼 추가 (Story 10.1, tech-debt #67 락스텝)
-- self-contained: listings 테이블·RLS enable·GRANT는 0002에서 이미 만들어졌다. 이 파일은
--   nullable 컬럼 3개만 더한다(additive) — 신규 RLS 정책은 만들지 않는다. RLS는 행 단위
--   정책이라 컬럼을 추가해도 기존 listings 정책(0002)을 그대로 상속한다.
--
-- 무엇을 더하나 (전부 nullable):
--   accident_status text    — '무사고'|'단순교환'|'사고' 중 하나 또는 NULL(미입력).
--     네이티브 enum이 아니라 text+CHECK — 기존 body_type/color/region과 같은 관례(drift 없음).
--   is_single_owner boolean — 1인소유 여부. NULL=미상(모른다는 뜻이지 "아니오"가 아니다).
--   is_non_smoker   boolean — 비흡연 여부. NULL=미상.
--
-- 왜 backfill 하지 않나 (기존 100건은 신규 3컬럼 전부 NULL로 남는다):
--   기존 매물은 이 정보를 입력받은 적이 없다. NULL을 "미입력"이 아니라 임의로(예: false) 채우면
--   판매자가 신고하지 않은 사실을 신고한 것처럼 꾸미게 된다 — 이 에픽의 정직성 원칙
--   (epic-10-context.md "가짜 검증 UI/API 금지")과 정면으로 어긋난다. 그래서 채우지 않는다.
--
-- ⚠️ 아래 CHECK가 못 보는 것 (실측 — AC3, 대장에도 등재):
--   (a) 마이그레이션 이전에 이미 들어간 행 — CHECK는 그 시점 이후의 INSERT/UPDATE에만 적용되고,
--       기존 행은 컬럼 자체가 없었으므로 검사 대상이 된 적이 없다.
--   (b) NULL 값 — Postgres의 CHECK 제약은 3값 논리(true/false/unknown)를 쓰고, 표현식이
--       UNKNOWN(NULL이 섞이면 대개 이렇게 된다)이면 위반으로 치지 않는다. 그래서 신규 3컬럼을
--       전부 비워 INSERT해도 그대로 통과한다.
--   (c) accident_free와의 논리적 모순 — 예를 들어 accident_free=true인데
--       accident_status='사고'인 행도 이 CHECK는 그대로 통과시킨다. accident_status 컬럼
--       하나만 보는 제약이라 다른 컬럼과의 정합은 애초에 검사 범위 밖이다.
--
-- 왜 accident_free(기존 NOT NULL bool)를 그대로 두나:
--   이미 카드·상세·시드·AI 프롬프트 등 다수 소비처가 이 컬럼을 쓰고 있다. accident_status는
--   그걸 대체하는 승격이 아니라 더 세분화된 정보를 담는 별도 컬럼이다 — 드롭·backfill 둘 다
--   하지 않는다(CLAUDE.md B3 "추가만, 기존 것을 지우거나 바꾸지 않는다").
-- if not exists — 재적용 안전성(기존 추가형 마이그 0007/0008/0009와 같은 관례). CHECK는 컬럼과
-- 같은 절에 인라인으로 둬서, 컬럼이 이미 있으면 이 clause 전체(컬럼+CHECK)가 통째로 스킵되고
-- 중복 제약 생성 시도 자체가 없다 — 별도로 "이미 있으면 건너뛴다" 로직이 필요 없다.
alter table public.listings
  add column if not exists accident_status text check (accident_status in ('무사고', '단순교환', '사고'));
alter table public.listings
  add column if not exists is_single_owner boolean;
alter table public.listings
  add column if not exists is_non_smoker boolean;

comment on column public.listings.accident_status is '사고 이력 자기신고(무사고/단순교환/사고). NULL=미입력(제3상태, backfill 안 함). 기존 accident_free(bool)와 별개 컬럼 — 승격하지 않는다.';
comment on column public.listings.is_single_owner is '1인소유 여부 자기신고. NULL=미상(false로 단정 금지, bool 3상태).';
comment on column public.listings.is_non_smoker is '비흡연 여부 자기신고. NULL=미상(false로 단정 금지, bool 3상태).';
