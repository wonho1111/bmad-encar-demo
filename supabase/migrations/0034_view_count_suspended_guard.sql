-- 0034_view_count_suspended_guard.sql — increment_listing_view(uuid)에 정지 회원 가드 추가
-- (DW-805, Story 17.2 — 0032/0033(Story 17.1)이 남긴 옆문을 닫는다)
-- self-contained: 이 파일이 참조하는 것은 전부 자기보다 앞 번호다 — public.listings(0002)·
--   public.profiles(0001)·public.increment_listing_view(0020). 뒤 번호를 가정하지 않는다.
--
-- ── 배경: 0032 9절이 남긴 판정을 이 파일이 뒤집는다 ─────────────────────────────────────────
-- 0032(Story 17.1) 9절 주석과 docs/conventions.md §8은 이 함수를 "해당 없음(anon도 호출 —
-- profiles 신원 자체가 없어 정지 게이트를 걸 수 없다)"으로 판정했다. 그 판정의 근거는 사실이지만
-- (anon 호출자는 profiles 행이 없다) 결론이 그 근거를 넘어선다 — "anon에 게이트를 걸기 어렵다"는
-- "authenticated인 정지 회원까지 통과시켜야 한다"를 뜻하지 않는다(DW-805). 오케스트레이터가 로컬
-- 55322에서 이 파일 적용 전 상태를 직접 재현해 확인했다: 같은 정지 회원 세션에서
-- `update listings set price=...` → 0행(17.1이 막는다) vs
-- `select increment_listing_view(id)` → view_count 0→1(뚫린다). 즉 정문은 잠갔는데 옆문 하나가
-- 열려 있었다 — view_count는 public.listings의 컬럼이므로 0032/0033의 불변식
-- ("정지 계정은 매물·사진·파일·관리자 RPC 어느 경로로도 쓰기를 성공시킬 수 없다")이 원래
-- 포함해야 했던 범주다. 이 파일이 그 판정을 "안 막는다" → "막는다"로 뒤집는다.
--
-- ── 왜 not exists(status='suspended')인가 — 비로그인 통과가 설계다, 부수효과가 아니다 ─────────
-- auth.uid()가 NULL이면(비로그인 anon 호출) `id = auth.uid()` 비교가 모든 profiles 행에서
-- unknown이 되어 서브쿼리가 0행을 돌려주고 not exists가 참 → 통과한다. 이건 SQL의 우연이
-- 아니라 **의도**다 — FR58(비로그인 상세 열람)이 조회수 집계까지 요구하므로, anon 호출은
-- 지금과 동일하게 계속 동작해야 한다. 다음 사람이 이 NULL 처리를 "빠뜨린 coalesce"로 오해해
-- `coalesce(auth.uid(), ...)`를 붙여 비로그인을 막지 않도록, 이 의도를 여기 각주로 고정하고
-- 아래 실행되는 검사(test_write_policy_manifest_real_db.py 헤더 + test_suspended_write_block_
-- real_db.py의 비로그인 회귀 단언)로도 고정한다.
--
-- ── 왜 SECURITY DEFINER 함수 본문 안에 가드를 두나 ─────────────────────────────────────────
-- docs/conventions.md §6 "SECURITY DEFINER 함수 축"이 이미 문서화한 성질과 같다 — 정의자
-- 함수 안에서는 RLS가 적용되지 않는다(정의자=소유자 권한으로 평가되고, 소유자에겐 RLS가 애초에
-- 안 걸린다). listings_update_own 등 RLS 정책을 아무리 고쳐도 이 함수는 그 정책을 우회하므로,
-- **함수 본문의 인라인 조건이 유일한 강제 지점**이다(0019 get_seller_public_summary·0030
-- admin_restore_sold_listing과 같은 패턴).
--
-- ── GRANT 유지 여부 — 실측 결과 ──────────────────────────────────────────────────────────
-- `create or replace function`이 기존 GRANT(anon·authenticated의 EXECUTE)를 유지하는지 로컬
-- 55322에서 트랜잭션 안에 이 파일과 동일한 정의로 재정의해 실측했다(2026-08-11, 롤백으로 원복):
--   select r.rolname, has_function_privilege(r.oid, 'public.increment_listing_view(uuid)',
--     'execute') from pg_roles r where r.rolname in ('anon','authenticated','postgres',
--     'service_role');
--   → 재정의 전/후 결과 동일: anon=t, authenticated=t, postgres=t, service_role=f.
-- 유지되므로 revoke/grant를 다시 적지 않는다(0028이 handle_new_user에 이미 쓴 것과 같은 전제,
-- 0032 6절의 admin_restore_sold_listing 주석도 동일 근거).
--
-- ── 동작 확인 (로컬 55322, 실측 — 존재 확인이 아니라 작동 확인, CLAUDE.md B4) ────────────────
-- 정지 회원 세션: view_count 변화 없음(0→0). anon 세션: 1 증가(0→1). 활성 회원 세션: 1 증가.
-- 정지 회원이 "자기 매물"을 호출해도 동일하게 막힘(소유 여부 무관 — 정지는 행위자 기준).
create or replace function public.increment_listing_view(p_listing_id uuid)
returns void
language sql
security definer
set search_path = ''
as $$
  update public.listings set view_count = view_count + 1
   where id = p_listing_id
     and not exists (
       select 1 from public.profiles
        where id = auth.uid() and status = 'suspended'
     );
$$;

comment on function public.increment_listing_view(uuid) is
  '상세 페이지 진입 시 조회수 +1(Story 11.1). SECURITY DEFINER — anon·authenticated 모두 실행
   가능(FR58, 상세는 비로그인도 열람). 호출될 때마다 항상 +1(멱등 아님, 의도된 동작) — 호출 지점을
   상세 페이지 서버 컴포넌트 한 곳으로 한정하는 것이 유일한 안전장치(카드 렌더 경로는 호출하지 않음).
   시그니처·반환형·호출 지점은 0020과 동일하게 보존한다.
   ✎ Story 17.2(DW-805)가 본문에 정지 가드를 추가: not exists(auth.uid()가 가리키는 profiles
   행이 status=''suspended'')일 때만 UPDATE가 통과한다. auth.uid()가 NULL(비로그인 anon 호출)이면
   서브쿼리가 항상 0행이라 not exists가 참 → 통과(설계 의도, FR58 회귀 방지). 이 함수는
   SECURITY DEFINER라 RLS가 대신 걸러주지 않으므로 이 인라인 조건이 유일한 강제 지점이다
   (docs/conventions.md §6 "SECURITY DEFINER 함수 축"과 동일 성질). 강제 장치:
   api/tests/integration/test_suspended_write_block_real_db.py(정지/비로그인/활성 3주체 실호출) +
   api/tests/integration/test_write_policy_manifest_real_db.py(전수조사 매니페스트 대조, DW-803).';
