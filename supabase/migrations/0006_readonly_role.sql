-- 0006_readonly_role.sql — NFR2: AI 전용 읽기전용 롤(ai_readonly)
--
-- 이 마이그레이션이 하는 일:
--   1) ai_readonly 롤 생성 (NOLOGIN — 연결 롤이 SET ROLE로 전환해 사용)
--   2) public 스키마 USAGE + 현재 모든 테이블 SELECT 부여 (쓰기 권한은 일절 부여 안 함)
--   3) ALTER DEFAULT PRIVILEGES — 앞으로 생길 테이블(예: 4.2 guide_documents)도 자동 SELECT
--   4) listings에 ai_readonly용 permissive SELECT 정책(using true) — RLS 가시성 확보
--   5) ai_readonly를 postgres에 멤버십 부여 — 연결 롤(postgres)이 SET ROLE 할 수 있게
--
-- ⚠️ 핵심 설계(반드시 이해):
--   · listings(0002)의 기존 SELECT 정책은 전부 `to authenticated` → 별도 ai_readonly 롤은
--     정책에 안 걸려 0건만 보인다. GRANT만으론 행이 안 보이므로 (4)의 permissive 정책이 필수.
--   · 그래서 ai_readonly는 sold 포함 모든 행을 본다. FR11(판매완료 비노출)은 RLS가 아니라
--     **AI 검색 쿼리(4.3+)가 WHERE status='on_sale'로 직접 책임**진다(Epic 3 회고 액션 #4 정합).
--   · 쓰기(INSERT/UPDATE/DELETE)는 어디에도 GRANT하지 않는다 → DB가 거부(NFR2 보장).
--
-- 번호 갭 메모: 0003(chat·Epic5)·0004(guide_documents·4.2)·0005(admin·Epic6)는 아직 미생성.
--   0006은 현재 존재하는 테이블(profiles·listings)에만 의존하므로 먼저 적용 가능.
--   guide_documents(4.2)에는 그 마이그레이션에서 동일한 ai_readonly SELECT 정책을 추가한다.

-- ── 1) 읽기전용 롤 생성 (멱등) ───────────────────────────────────────
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'ai_readonly') then
    create role ai_readonly nologin;
  end if;
end $$;

-- ── 2) 스키마 사용 + 현재 모든 테이블 SELECT ─────────────────────────
grant usage on schema public to ai_readonly;
grant select on all tables in schema public to ai_readonly;

-- ── 3) 향후 생성 테이블도 자동 SELECT (예: 4.2 guide_documents) ───────
alter default privileges in schema public grant select on tables to ai_readonly;

-- ── 4) RLS 가시성 — ai_readonly는 모든 행을 본다(FR11은 앱 쿼리가 책임) ──
drop policy if exists "listings_ai_readonly_select" on public.listings;
create policy "listings_ai_readonly_select" on public.listings
  for select to ai_readonly using (true);

-- ── 5) 연결 롤(postgres)이 SET ROLE ai_readonly 가능하게 멤버십 부여 ──
grant ai_readonly to postgres;
