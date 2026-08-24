-- 0030_listings_restore_sold_rpc.sql — 관리자 판매완료 되돌리기 RPC (DW-391, Story 15.4)
-- self-contained: listings 테이블·is_admin()은 0001·0002에서 이미 존재한다. 이 파일은 RPC 1개만 추가한다.
--
-- 왜 필요한가:
--   0015가 sold 매물의 UPDATE를 판매자·관리자 모두에게서 막았다(RLS `using`에 status<>'sold').
--   그런데 오조작으로(다른 탭에서 구매완료를 두 번 누르는 등) 매물이 잘못 sold가 되면, 지금까지는
--   되돌릴 방법이 DB에 직접 SQL을 치는 것뿐이었다(deployment-runbook.md §10, Story 9.7에서 실제로
--   밟은 사례 — 대장 #91). 관리자 UPDATE 정책(listings_update_admin)을 통째로 열면 0015가 막은
--   "sold 매물 임의 수정"을 반쯤 되여는 것이라 쓰지 않는다 — 대신 status만, sold→on_sale 방향으로만
--   되돌리는 좁은 SECURITY DEFINER RPC 하나를 신설한다.
--
-- 패턴 선례: 0020_listings_view_count.sql의 increment_listing_view 하드닝을 그대로 따른다 —
--   language sql, security definer, set search_path = ''(모든 테이블 참조에 public. 접두 필수),
--   revoke all ... from public 후 필요한 롤에만 grant execute.
--   차이점: increment_listing_view는 anon도 호출 대상(비로그인 상세 조회)이지만, 이 RPC는
--   is_admin()처럼 로그인 사용자(관리자)만 호출 대상이므로 anon에는 애초에 grant하지 않는다
--   (anon은 EXECUTE 권한 자체가 없어 별도 로직 없이 거부됨).

create or replace function public.admin_restore_sold_listing(p_listing_id uuid)
returns table (id uuid)
language sql
security definer
set search_path = ''
as $$
  update public.listings
     set status = 'on_sale'
   where id = p_listing_id
     and status = 'sold'
     and public.is_admin()
  returning id;
$$;

comment on function public.admin_restore_sold_listing(uuid) is
  '관리자 판매완료 되돌리기(DW-391, Story 15.4) — status만 sold→on_sale로 되돌린다. WHERE 절에
   status=''sold''와 is_admin()을 함께 걸어 "비관리자 호출"과 "이미 on_sale인 행 호출"을 같은
   0행 신호로 수렴시킨다(둘 다 클라이언트에서 굳이 구분하지 않는다). 관찰 가능한 계약은 이것뿐이다
   — 0행 = "그 행이 sold가 아니었거나, 호출자가 관리자가 아니다". 그 0행이 어떤 경로로 생겼는지
   (동시 호출 레이스인지, 화면이 낡아 이미 복구된 행을 다시 누른 것인지, 권한을 잃은 것인지)는
   이 함수가 구분하지도, 어느 테스트가 측정하지도 않는다(장부 DW-719). 컬럼·값을 파라미터로 받지 않는다 —
   status 외 다른 컬럼을 바꾸는 범용 UPDATE로 확장하지 않는다(increment_listing_view와 동일 이유).';

-- Postgres는 새 함수의 EXECUTE를 기본으로 PUBLIC에 준다 — 먼저 회수한 뒤 authenticated에만
-- 재부여한다(이 줄이 없으면 아래 grant가 장식이 되고 PUBLIC 경유로 누구나 호출 가능).
-- anon은 제외 — is_admin()이 참일 수 없는 비로그인 사용자에게 EXECUTE를 줄 이유가 없다.
--
-- ⚠️ public뿐 아니라 anon·authenticated **각 롤에서도** 회수한다(2026-08-07 코드리뷰 patch).
--   왜: 0001_profiles.sql §5가 이미 규칙으로 적어둔 사실 — "Supabase 기본 권한이 anon·authenticated에
--   EXECUTE를 명시 부여하므로, public뿐 아니라 각 롤에서도 명시적으로 회수해야 한다". PUBLIC 회수는
--   `grant to public` 경로만 닫지, 롤에 **직접** 걸린 GRANT는 남긴다. 0007·0008·0016·0023·0024·0026이
--   전부 3개 롤을 개별 회수하는데 이 파일만 public 하나였다.
--   실측(로컬 Supabase 스택, 55322): 이 스택의 `pg_default_acl`은 postgres 소유 public 함수에
--   `{postgres=X/postgres}`만 주므로 회수 전에도 anon EXECUTE는 없었다(has_function_privilege=false).
--   즉 지금 로컬·CI에서 동작이 바뀌지는 않는다. 그런데도 고치는 이유는, 그 "안전"이 **원격 프로젝트의
--   기본 ACL이 로컬과 같다는, 아무도 측정하지 않은 전제**에 기대고 있었기 때문이다 — 회수 대상을
--   리포 관례대로 3개 롤로 맞추면 그 전제 자체가 필요 없어진다.
revoke all on function public.admin_restore_sold_listing(uuid) from public;
revoke all on function public.admin_restore_sold_listing(uuid) from anon;
revoke all on function public.admin_restore_sold_listing(uuid) from authenticated;
grant execute on function public.admin_restore_sold_listing(uuid) to authenticated;
