-- 0011_listings_anon_select.sql — FR58 접근제어 토대: listings anon(비로그인) SELECT 허용
-- self-contained: listings 테이블·RLS enable은 0002에서 이미 완료됨(재생성하지 않음).
--   이 파일은 anon 롤에 대한 (1) 정책 1개 + (2) 컬럼 스코프 GRANT 만 추가한다.
--
-- 이 마이그레이션이 하는 일:
--   listings에 anon 롤 SELECT를 연다. 기존 authenticated 정책 4개(select_on_sale/own/admin
--   + insert/update/delete)는 건드리지 않는다 — anon은 조회(on_sale만)만 가능, 쓰기는 여전히 불가
--   (anon용 INSERT/UPDATE/DELETE 정책이 없으므로 RLS가 쓰기를 차단한다).
--   FR11(판매완료 비노출)을 anon 경로에서도 동일하게 강제: status='on_sale'만 노출.
--
-- ⚠️ 왜 정책만으로 부족한가 — RLS는 "행"만 통제하고 "컬럼"은 통제하지 못한다.
--   정책만 두면 anon 키로 PostgREST에 `?select=embedding` 하면 RAG 코퍼스 임베딩(vector 768)이
--   통째로 나간다. RLS엔 컬럼 차원이 없으므로, 컬럼 차단은 GRANT로만 가능하다.
--   또한 "anon이 이 테이블을 읽어도 된다"는 테이블 GRANT 자체가 이 레포 어느 마이그레이션에도
--   없었고 Supabase 플랫폼 기본 권한에 암묵 의존하고 있었다(0006_readonly_role.sql이 ai_readonly
--   롤·GRANT를 명시적으로 다루는 것과 대조). 아래 revoke+grant가 그 의존을 끊어 self-contained하게 만든다.

-- ── 1) 정책 — 행 차원: on_sale만 ─────────────────────────────────────
-- drop policy if exists로 재적용 안전성 확보(forward-only 마이그레이션 재실행 대비).
drop policy if exists "listings_select_on_sale_anon" on public.listings;

create policy "listings_select_on_sale_anon" on public.listings
  for select to anon using (status = 'on_sale');

-- ── 2) GRANT — 컬럼 차원: 화면이 쓰는 컬럼만 ──────────────────────────
-- 먼저 테이블 전체 SELECT를 회수한다(플랫폼 기본 GRANT 무력화). 그 뒤 컬럼별로만 다시 준다.
-- 이 두 줄이 함께여야 의미가 있다 — revoke 없이 grant만 하면 기본 권한이 남아 전 컬럼이 열린다.
revoke select on public.listings from anon;

-- 아래 목록 = anon 경로가 실제로 참조하는 컬럼의 합집합.
--   · SELECT 목록: /search 카드 8필드 + /listings/[id] 상세 전 필드
--   · WHERE 필터: model·body_type·color·fuel·transmission·region·price·year·status
--     (Postgres는 WHERE에 쓰인 컬럼에도 SELECT 권한을 요구한다 — 빠뜨리면 필터가 깨진다)
--   · ORDER BY: created_at, id
-- 제외: embedding(RAG 코퍼스 — 차단 대상), updated_at(anon 경로 미사용).
-- ⚠️ 앞으로 listings에 컬럼을 추가해도 anon엔 기본적으로 안 보인다(의도된 동작).
--    anon 화면에 새 컬럼을 노출하려면 후속 마이그레이션으로 이 목록에 grant를 추가해야 한다.
grant select (
  id,
  seller_id,
  status,
  created_at,
  manufacturer,
  model,
  body_type,
  year,
  price,
  mileage,
  color,
  fuel,
  transmission,
  displacement,
  seats,
  region,
  accident_free,
  seller_name,
  options,
  description
) on public.listings to anon;
