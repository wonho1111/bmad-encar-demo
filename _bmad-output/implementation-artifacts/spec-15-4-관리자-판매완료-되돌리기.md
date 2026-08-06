---
title: '관리자 판매완료 되돌리기 (오조작 복구, DW-391)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: '42bacb06bc09bed059285d7a0f704964bcda64ca'
final_revision: '938c81a'
---

<intent-contract>

## Intent

**Problem:** `0015_listings_update_not_sold.sql`이 sold 매물의 UPDATE를 판매자·관리자 모두에게서 막아, 오조작으로 판매완료된 매물을 되돌릴 방법이 DB에 직접 SQL을 치는 것뿐이다(DW-391, Story 9.7에서 실제로 밟은 사례).

**Approach:** `status`만 `sold`→`on_sale`로 되돌리는 좁은 `security definer` RPC 1개(`admin_restore_sold_listing`)를 신설하고, 관리자 매물 화면(목록+상세)에 sold 매물 한정 "판매완료 되돌리기" 버튼을 추가한다. 런북의 SQL 복구 절차는 이 화면 절차로 대체하고 비상용 백업으로만 남긴다. Epic 15는 UI-only이나 이 스토리는 명시적 예외다(마이그레이션 1개 동반).

## Boundaries & Constraints

**Always:**
- 신규 RPC `public.admin_restore_sold_listing(p_listing_id uuid)`를 `supabase/migrations/0030_listings_restore_sold_rpc.sql`로 추가한다. `0020_listings_view_count.sql`의 `increment_listing_view` 하드닝 패턴을 그대로 따른다: `language sql`, `security definer`, `set search_path = ''`, `revoke all on function ... from public` 후 `authenticated`에만 `grant execute`(anon은 제외 — `is_admin()`처럼 로그인 사용자만 호출 대상).
- RPC 본문은 `update public.listings set status='on_sale' where id=p_listing_id and status='sold' and public.is_admin() returning id`. 비관리자 호출·이미 on_sale인 행 호출 둘 다 0행 반환으로 수렴시킨다(anon은 EXECUTE 권한 자체가 없어 별도로 거부됨).
- `ListingAdminActions.tsx`(목록·상세 공용 컴포넌트)에 sold 매물에만 보이는 "판매완료 되돌리기" 버튼을 추가한다. 흐름은 `MemberActions.tsx`와 동일: 실행 → RPC 호출 → 반환 행 0개면 한국어 오류 → 성공 시 `router.refresh()`. 기존 삭제 버튼과 병존한다.
- `page.tsx`·`[id]/page.tsx`는 이미 `status`를 조회하므로 `ListingAdminActions`에 그 값을 prop으로 전달한다.
- `docs/deployment-runbook.md` §10을 이 RPC/버튼 절차로 대체한다. 옛 SQL 복구 절차는 지우지 말고 "비상용 백업"으로 표시해 남긴다.
- `api/tests/integration/`에 `test_view_count_rpc_real_db.py`와 동일 패턴(SET LOCAL ROLE 임퍼소네이션)의 RPC 하드닝 실DB 검증을 신설한다: anon EXECUTE 거부, authenticated 비관리자 0행, 관리자 성공+멱등, sold 아닌 행 no-op.
- `web/e2e/write-flows.spec.ts`의 `describe.serial` 블록에 E5 뒤 E6을 추가해, 관리자가 되돌린 뒤 판매자가 그 매물을 다시 정상 수정·구매완료할 수 있음을 왕복 검증한다(같은 `listingId` 공유, afterAll 정리 그대로 재사용).

**Block If:** (해당 없음 — 설계가 에픽 컨텍스트·계획 문서에 이미 못박혀 있음)

**Never:**
- 관리자 UPDATE 정책(`listings_update_admin`)을 통째로 여는 방식은 쓰지 않는다 — `0015`가 막은 "sold 매물 임의 수정"을 반쯤 되여는 것이기 때문.
- RPC가 컬럼·값을 파라미터로 받지 않는다 — `status`만, 범용 UPDATE로 확장하지 않는다(`increment_listing_view` Never 절과 동일 이유).
- 범위 밖: 정지 게이트(DW-669/DW-717), 삭제된 매물 복구, 구매완료 처리 자체(FR7)를 바꾸는 것.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 관리자가 sold 매물 되돌리기 실행 | admin 로그인, `status='sold'` 매물 | `status`가 `on_sale`로 바뀌고 목록에 재노출 | - |
| 비관리자(authenticated)가 RPC 직접 호출 | 구매자/판매자 계정, sold 매물 id | 0행 반환, status 불변 | 클라이언트: 한국어 오류 |
| anon이 RPC 직접 호출 | 비로그인 | EXECUTE 권한 없음 | `InsufficientPrivilege`(42501) |
| 이미 on_sale인 행에 재호출 | admin, on_sale 매물 id | 0행 반환, 에러 없음(멱등) | - |
| 되돌린 뒤 판매자 재사용 | 복구 후 판매자가 수정/재구매완료 시도 | 정상 동작(회귀 없음) | - |

</intent-contract>

## Code Map

- `supabase/migrations/0030_listings_restore_sold_rpc.sql` -- 신규 RPC(`admin_restore_sold_listing`) + GRANT/REVOKE 하드닝
- `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx` -- sold 매물 한정 "판매완료 되돌리기" 버튼 + RPC 호출 로직 추가
- `web/src/app/(admin)/admin/listings/page.tsx` -- `ListingAdminActions`에 `status` prop 전달
- `web/src/app/(admin)/admin/listings/[id]/page.tsx` -- 동일하게 `status` prop 전달(이미 `listing.status` 보유)
- `docs/deployment-runbook.md` -- §10을 새 절차로 대체, 옛 SQL은 비상용 백업으로 보존
- `api/tests/integration/test_restore_sold_listing_rpc_real_db.py` -- RPC 권한/멱등 실DB 검증 신설
- `web/e2e/write-flows.spec.ts` -- E5 뒤 E6 추가(관리자 복구 → 판매자 재사용 왕복)
- `web/src/app/(admin)/admin/listings/__tests__/restoreSoldWiringContract.test.ts` -- (2차 리뷰 patch) web 배선 계약 소스 스캔. E2E는 CI에 안 배선돼 있어 이 스토리의 web 쪽을 CI가 보는 유일한 검사다. (3차 리뷰 patch) 5개 축이 fail-open이던 것을 불변식으로 교체 — 전부 mutation으로 red 확인.
- `docs/conventions.md` -- (3차 리뷰 patch) §6 "SECURITY DEFINER 함수 축" 소비처 목록에 `0030` 등재. 규칙7이 요구하는 자리인데 비어 있었다(RLS 밖 쓰기 경로가 계약 정본에 안 잡혀 있었음).

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0030_listings_restore_sold_rpc.sql` -- RPC 신설(`security definer`+`is_admin()`+GRANT 하드닝) -- AC1~4
- `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx` -- 되돌리기 버튼(`status` prop 필요) 추가 -- AC1,5,6
- `web/src/app/(admin)/admin/listings/page.tsx` -- `status` 전달 -- 버튼 표시 조건
- `web/src/app/(admin)/admin/listings/[id]/page.tsx` -- `status` 전달 -- 버튼 표시 조건
- `docs/deployment-runbook.md` -- §10 대체 -- AC7(추적 가능성)
- `api/tests/integration/test_restore_sold_listing_rpc_real_db.py` -- RPC 권한/멱등 실DB 검증 -- AC2,3,4
- `web/e2e/write-flows.spec.ts` -- E6 추가 -- AC1,6 E2E 커버

**Acceptance Criteria:**
- Given 관리자로 로그인, when sold 매물에서 "판매완료 되돌리기"를 실행하면, then `status`가 `on_sale`로 바뀌고 목록에 재노출된다.
- Given 복구 경로, when 구현을 확인하면, then `listings_update_admin` 같은 전면 UPDATE 정책이 아니라 status만 되돌리는 좁은 RPC다.
- Given 비관리자(authenticated 비-admin, anon)가 RPC를 직접 호출하면, when 실DB로 확인하면, then 실패한다(0행 또는 EXECUTE 거부).
- Given 이미 on_sale인 행, when RPC를 호출하면, then 아무 일도 일어나지 않는다(멱등, 에러 아님).
- Given 복구된 매물, when 판매자가 수정·재구매완료를 시도하면, then 정상 동작한다(회귀 없음).
- Given 관리자 화면 버튼, when 클릭 흐름을 보면, then `MemberActions.tsx`와 동일한 "실행→0행이면 한국어 오류→router.refresh()" 모양이다.
- Given 런북, when §10을 보면, then 이 RPC/화면 절차가 정본이고 옛 SQL 절차는 비상용 백업으로만 표시된다.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Review pass (3차, 후속 리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 0, medium 5, low 8)
- defer: 3: (low 3)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` **2차 패스가 추가한 `updated_at` 단언이 무의미했다 — 직접 측정으로 확인.** 낡은 값(`2020-01-01`)을 심는 UPDATE 자체가 `listings_set_timestamps` 트리거를 발화시켜(view_count가 안 바뀐 UPDATE라서) 그 자리에서 `now()`로 덮는다. 즉 `_STALE`은 한 번도 저장되지 않았고, 단언은 **RPC를 호출하기도 전에 이미 참**이었다(실측: 시드 직후 `updated_at > stale` = t). 2차 패스가 한 red/green 실험(트리거 drop)이 이 갭을 못 가른 이유도 같다 — 트리거를 지우면 시드 쪽 덮어쓰기도 함께 사라져 red가 되므로 "트리거 존재"와 "RPC 경로 발화"가 구별되지 않았다. 심는 동안만 트리거를 끄고, **심은 값이 실제로 남았는지를 먼저 단언**하도록 고쳤다. 검증: 트리거를 sold→on_sale 전환에서만 건너뛰게 변조하니 red(낡은 값 2020-01-01이 그대로 남음), 원본 복원 후 11건 green. DW-718을 defer한 근거("적어도 updated_at은 움직인다")가 이제 실제로 고정된다.
  - `[medium]` `[patch]` **`isSold` 게이트 검사가 fail-open이었다 — mutation으로 확인.** `labelIndex > gateIndex`로 두 문자열의 **등장 순서**만 비교해서, 버튼을 `{isSold && (...)}` 밖으로 빼내도 앞쪽에 `{isSold && (`가 남아 있으면 그대로 통과했다(실제로 옮겨 돌렸더니 4건 전부 green). 2차 패스가 "④개 축을 일부러 깨서 red 확인"했다고 적었지만 이 축은 **게이트 삭제**만 잡고 **밖으로 빼기**는 못 잡았다. 게이트 직후 `<Button`이 열리고 그 안에 라벨이 오는 포함 관계로 고쳤다.
  - `[medium]` `[patch]` **`router.refresh()`와 0행 거부 분기를 CI가 보는 검사가 하나도 없었다.** 둘 다 지운 채로 vitest·lint·tsc가 전부 green이다(리뷰어가 실제로 지워서 확인). 유일한 커버였던 E2E E6은 CI에 배선돼 있지 않다. 2차 패스가 web 배선을 CI로 끌어온 바로 그 작업에서 이 두 개를 빠뜨린 것이다 — 결과가 각각 "되돌려도 화면이 그대로", "거부가 성공처럼 보임"이라 사용자에게 보이는 축이다. 단언 범위를 `handleRestore` 본문으로 좁혀(파일 전체를 보면 `handleDelete`의 같은 코드가 대신 통과시킨다) 두 축을 추가했다.
  - `[medium]` `[patch]` **AC1의 "목록에 **재노출**된다"를 관측한 검사가 없었다.** 되돌린 뒤 확인하는 것이 전부 관리자 화면(sold도 보이는 화면)과 DB 컬럼 읽기라, FR11이 실제로 사는 표면(구매자 경로)에서 재노출을 본 적이 없다. E6 안에서 판매자로 여는 상세도 소유자 RLS 경로라 status와 무관하게 보인다. E6에 **익명 컨텍스트로 `/search` 재조회** 단계를 추가했다(E5가 sold일 때 0건을 확인하는 것과 짝). 검증: 같은 표면에서 링크 수가 on_sale=1 → sold=0 → 복원=1로 뒤집히는 것을 직접 측정해 구별력을 확인했다.
  - `[medium]` `[patch]` **런북 §10-a가 또 다른 오진으로 이끌고 있었다.** 2차 패스가 `auth.uid()` 오진을 고치면서 넣은 진단 쿼리가 `p.role`과 함께 `p.status`를 뽑는데, 본문은 `role`만 해설한다 — 운영자가 `status='suspended'`를 보고 그게 원인이라 결론 내리기 쉽다. 그런데 같은 커밋이 만든 DW-721이 **정지된 관리자도 이 RPC를 통과한다**고 실측해 놓았다(`is_admin()`은 `role`만 보고, `0030`은 SECURITY DEFINER라 RLS도 안 거친다). "`status`는 0행의 원인이 아니다"를 그 자리에 명시했다.
  - `[low]` `[patch]` `.select(...)` 검사가 파일의 **첫** `.select(`를 보고, `status`를 **부분문자열**로 찾았다 — 매물 쿼리 앞에 다른 쿼리가 생기면 엉뚱한 select를 검사하고, `accident_status`(ListingCard 계약 필드) 같은 이름만 들어와도 통과한다. `.from('listings')`에 앵커하고 컬럼 토큰으로 비교하도록 고쳤다(mutation: `status`→`accident_status`로 바꾸니 red).
  - `[low]` `[patch]` `stripComments`가 문자열·템플릿 리터럴을 구분하지 못해, 리터럴 안 `//`(예: URL) 하나로 코드가 통째로 지워질 수 있었다(지금 세 파일엔 없어 잠재). 과잉 제거를 조용한 통과가 아니라 실패로 만드는 `expectStripped` 앵커 확인을 모든 호출부에 넣었다.
  - `[low]` `[patch]` `disabled={busy}` 개수를 `.toBe(2)`로 못박은 것이 **방향이 반대**였다 — 세 번째 액션이 busy를 쓰면 red(3≠2), 안 쓰면 green(2)이라 정작 잡아야 할 쪽을 놓쳤다. "핸들러를 가진 버튼 수 == busy 가드를 가진 버튼 수" 불변식으로 교체(mutation: 가드 하나 제거 → red).
  - `[low]` `[patch]` 실DB 구조 검사가 함수 **이름**으로만 매치하고 `fetchone()`으로 한 행만 봐서, `admin_restore_sold_listing(uuid, text)` 같은 **형제 오버로드**가 생기면 좁은 쪽이 먼저 반환될 때 통과했다 — 그게 바로 Never 절이 금지하는 모양이다. "이름당 함수 1개"를 단언해 GRANT 검사(같은 이름 필터)의 전제도 함께 고정했다.
  - `[low]` `[patch]` 2차 패스가 신설한 `test_rpc_is_the_only_door_to_a_sold_row`가 임퍼소네이션을 인라인하면서 `reset role`의 `InFailedSqlTransaction` 가드를 빠뜨렸다 — `_call_rpc`의 docstring이 그 가드가 필요한 이유를 직접 적어 둔 항목이다. 향후 UPDATE가 0행이 아니라 예외로 실패하면 원래 원인이 가려진다.
  - `[low]` `[patch]` E6이 관리자 목록 행을 `MODEL` 문자열로 골랐다. `/sell`(판매자 본인 매물만)과 달리 이 화면은 전 판매자·전 상태를 **필터 없이** 보여주므로(그 파일 주석이 그게 목적이라고 적고 있다), 중단된 이전 실행이 남긴 같은 모델 매물 하나로 strict mode 충돌이 난다 — `listingId` 링크로 좁혔다. 함께 0행 오류 알림 부재(`getByRole('alert')` 0건) 단언도 추가.
  - `[low]` `[patch]` `docs/conventions.md` §6의 "SECURITY DEFINER 함수 축" 소비처 목록에 `0030`이 없었다. 규칙7이 "새 경로를 열면 이 목록에 강제 지점을 추가한다"고 명시하고, §6은 그 목록이 낡아 실패한 전례(2026-07-19 이미지 축)까지 자기 안에 기록하고 있다. 이 스토리는 주석 3곳과 런북은 고쳤는데 **계약 정본만** 안 고쳤다 — 그 문서만 읽는 다음 사람은 "authenticated UPDATE = 0015"를 유일한 관문으로 읽게 된다. 등재하면서 "정의자 함수는 조회뿐 아니라 쓰기 경로도 올린다"를 규칙 문장에 명시했다.
  - `[low]` `[patch]` 런북 §10에 "되돌리면 거래내역에서 사라지고 감사 기록이 남지 않는다"는 경고가 없었다. 관리자 거래내역은 `status='sold'`만 거르므로(코드 확인: `.eq('status', SOLD)`) 되돌리는 순간 그 매물이 화면에서 사라지고, 누가·언제 되돌렸는지는 어디에도 안 남는다(DW-718). 운영자가 "되돌리기 전에 기록해 둘 것"을 알 방법이 없었다.
- 참고(defer로 장부에 신규 등재, 이 패스에서 코드 변경 없음): [[DW-723]](`MemberActions.tsx`에 삭제·정지 공유 busy 가드가 없다 — 1차 패스가 매물 쪽에서 고친 그 결함이 **본보기였던 파일**에 그대로다. 15.4가 만든 게 아니라 드러낸 것이라 범위 밖이지만, 팀이 이미 진단했다는 사실이 어디에도 없으면 다음 사람이 처음부터 다시 조사한다) · [[DW-724]](`is_admin()`이 `set search_path = public` — 신설 RPC들은 `''`로 하드닝하면서 정작 인가를 위임하는 함수는 옛 기준. 실측으로 뚫리는 경로를 재현하진 못해 "취약점"이 아니라 **기준 불일치**로 등재) · [[DW-725]](관리자 매물 행의 sold 상태(버튼 2개 가로 배치)가 반응형 자동 검사에 없다 — D5 근거가 재현 불가능한 1회성 캡처뿐이고 컨테이너에 `flex-wrap`이 없어 폭 부족 시 오버플로).
- reject(12건, 근거와 함께 기각): `service_role`에 EXECUTE가 남는다는 우려(**직접 측정으로 false** — `has_function_privilege('service_role', …)` = f. 원격 기본 ACL 추정은 2차 패스가 이미 같은 근거로 기각했고, 리포의 다른 6개 마이그도 service_role을 회수하지 않는다) · `router.refresh()`를 await하지 않아 성공 직후 재클릭 시 "다른 관리자가 먼저 처리" 오안내(실재하나 스펙이 `MemberActions.tsx`와 동일한 모양을 **명시 지시**했고, 고치려면 성공 경로에서만 상태를 유지하는 비대칭 구조가 필요해 "실패 시 버튼 영구 잠김"이라는 새 위험을 만든다. 데이터는 이미 올바른 상태이고 사용자 행동 지침(새로고침)도 바뀌지 않는다) · DW-391의 `status: resolved` 형식이 장부 표준과 다름 / 그 본문이 여전히 "복구 경로가 없다"고 적음(둘 다 실재하나 **이 실행의 지시가 기존 장부 항목 수정을 금지** — 오케스트레이터 소유) · `docs/tech-debt.md` #91 이관 색인이 아직 "열림"(동결 문서, 2차 패스 기각 근거 유효) · E2E가 수동 복원한 로컬 DB에서 돌았다는 지적(이미 DW-722로 등재됨 — 중복) · `followup_review_recommended` 점수 공식이 절대 안 꺼진다(워크플로 설계 축이지 이 스토리 산출물이 아니다. 다만 관찰은 아래 잔여 위험에 남긴다) · `test_named_argument_contract`가 다른 테스트의 부분집합이고 `named=False` 분기가 죽어 있음(프로덕션은 명명 인자만 쓰므로 위치 인자 검증은 요구되지 않은 확장 — A2 단순함 우선) · 0행 오류 문구의 390px D5 미확인(비관리자는 `requireRole`에 막혀 이 분기 도달 자체가 불가하고 web에 렌더 테스트 인프라가 없다) · PostgREST/HTTP 계층의 anon 42501 미검증(실DB 테스트 전반의 기존 구조적 한계이고 테스트 헤더가 이미 그렇게 적고 있다 — 이 스토리가 만든 갭이 아니다) · `_call_rpc`의 SQL 문자열 보간(`SET ROLE`은 바인드 파라미터를 못 받는 Postgres 제약이고 테스트 전용 신뢰 리터럴 — 2차 패스와 동일 기각) · `final_revision`이 dangling 커밋을 가리키고 `review_loop_iteration`이 0(전자는 이번 finalize가 어차피 갱신하고, 후자는 워크플로가 후속 리뷰 진입 시 0으로 리셋하도록 **명시 규정**한 값이라 결함이 아니다).

### 2026-08-07 — Review pass (2차, 후속 리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 4, low 5)
- defer: 2: (low 2)
- reject: 11
- addressed_findings:
  - `[medium]` `[patch]` `0030`이 새 함수의 EXECUTE를 `from public` 하나만 회수했다. `0001_profiles.sql` §5가 이미 규칙으로 적어둔 것("Supabase 기본 권한이 anon·authenticated에 EXECUTE를 명시 부여하므로 각 롤에서도 명시적으로 회수해야 한다")과 어긋나고, 0007·0008·0016·0023·0024·0026이 전부 3개 롤을 개별 회수하는데 이 파일만 예외였다 — `from anon`·`from authenticated` 회수를 추가했다. 실측으로는 로컬 스택·CI 컨테이너 둘 다 회수 전에도 anon EXECUTE가 없었으므로(`has_function_privilege`=false) 동작이 바뀌지는 않는다. 고친 이유는 그 "안전"이 **원격 프로젝트의 기본 ACL이 로컬과 같다는, 아무도 측정하지 않은 전제**에 걸려 있었기 때문이다(리뷰어가 주장한 "원격에는 anon EXECUTE가 남는다"는 미측정 추정이라 근거로 채택하지 않았고, 관례 일치만을 근거로 고쳤다).
  - `[medium]` `[patch]` 이 스토리의 web 배선(RPC 이름·`p_listing_id` 키·`isSold` 게이트·두 화면의 `status` prop·`busy` 공유 가드)을 **CI가 보는 검사가 하나도 없었다** — 유일한 커버가 `write-flows.spec.ts` E6인데 `.github/workflows/tests.yml`은 E2E를 배선하지 않는다(그 파일이 직접 그렇게 적고 있다). 신설 실DB 테스트 파일의 헤더조차 "web 호출 여부는 정적 스캔 몫"이라고 넘겼는데 그 정적 스캔이 없었다. 같은 리포가 0020 RPC에 대해 이미 갖고 있는 선례(`viewCountCallSite.test.ts`·`unreadWiringContract.test.ts`)를 따라 `restoreSoldWiringContract.test.ts`(vitest, `web` 잡에서 실행)를 신설했다. **4개 축을 각각 일부러 깨서 red를 확인하고 되돌려 green을 확인했다**(CLAUDE.md B4).
  - `[medium]` `[patch]` 런북 §10-a가 "되돌릴 수 없습니다가 뜨면 **대개 로그인 계정이 관리자가 아닌 경우**"라고 안내했는데 사실이 아니다 — `/admin/**`은 `(admin)/layout.tsx`의 `requireRole(USER_ROLE.ADMIN)`이 이미 막아 비관리자는 버튼이 있는 화면에 들어오지도 못한다(홈으로 리다이렉트). 게다가 그 진단 쿼리가 `auth.uid()`를 쓰는데, §10-a는 정의상 DB에 직접 붙는 경로라 JWT가 없어 `auth.uid()`가 **항상 NULL**이고 관리자가 맞아도 늘 0행이 나온다(실측 확인). 원인 순서를 "이미 sold가 아님(가장 흔함) → 낡은 세션에서의 역할 회수(드묾)"로 바로잡고, 진단 쿼리를 이메일 조인으로 교체했다.
  - `[low]` `[patch]` `test_no_broad_admin_update_policy_exists`가 정책 **이름**만 본다(1차 패스가 의도적으로 좁힌 결과). 이름 검사만으로는 `listings_update_moderation` 같은 이름의 전면 UPDATE 정책이 생겨도 통과한다 — "복구 통로는 RPC 하나"(AC2)라는 주장 자체가 실측된 적이 없었다. **다른 문을 실제로 밀어보는** 행동 검증 `test_rpc_is_the_only_door_to_a_sold_row`를 추가했다(sold 행에 대한 테이블 직접 UPDATE가 판매자·관리자 양쪽에서 0행). 검증: 실제로 `listings_update_moderation` 정책을 심었더니 새 테스트는 red, 기존 이름 검사는 green — 갭이 실재했음이 그 자리에서 증명됐다.
  - `[low]` `[patch]` `test_admin_restores_sold_listing`의 컬럼 불변 대조군이 `updated_at`을 **제외**하면서 그 컬럼이 어떻게 되는지는 아무도 안 봤다(제외 ≠ 검증). DW-718(감사 로그 부재)을 defer한 근거가 "적어도 updated_at은 움직인다"이므로 그 전제를 실측으로 고정했다. 단순 전후 비교는 트리거의 `now()`가 **트랜잭션 시작 시각**이라 같은 트랜잭션 안에서 구조적으로 항상 실패한다(실측으로 확인) — 대신 명백히 과거인 값을 심고 덮이는지를 본다. 트리거를 실제로 drop해 red, 되살려 green 확인.
  - `[low]` `[patch]` `0030`의 함수 주석이 "0행은 레이스 조건에서만 발생"이라고 단언했는데, 같은 커밋이 만든 DW-719가 "그 주장은 실측되지 않았다"고 적고 있었다(자기모순). 화면이 낡은 탭처럼 레이스가 아닌 경로도 있다 — 관찰 가능한 계약("0행 = sold가 아니었거나 관리자가 아니다")만 남기고 원인 단정을 뺐다(CLAUDE.md B4 "재보기 전엔 선언하지 않는다").
  - `[low]` `[patch]` `write-flows.spec.ts`의 병렬 간섭 분석 문단이 여전히 "E1~E5가 사는 동안"만 on_sale 창으로 말했다 — E6이 되돌리면서 창이 하나에서 둘로 늘었다. 아래 판정들의 결론은 그대로지만 전제 문장이 파일의 실제 수명주기와 어긋난 채였다(그 문단은 병렬 flake가 났을 때 믿고 보라고 존재하는 문서다).
  - `[low]` `[patch]` `admin/listings/page.tsx`·`[id]/page.tsx`의 주석이 액션을 여전히 "삭제만"으로 서술했고, 특히 "판매완료 처리는 판매자 동선이지 관리자 동선이 아니다"라는 범위 컷 근거가 더 이상 전부 참이 아니었다(만드는 것은 판매자, 되돌리는 것은 관리자). 두 곳 모두 갱신.
  - `[medium]` `[patch]` (E2E 보강, 위 2번과 같은 뿌리) 런북이 "목록·**상세** 양쪽에 버튼이 보인다"고 약속하는데 상세 화면의 `status` prop 배선을 렌더한 테스트가 하나도 없었다(다른 관리자 상세 E2E는 전부 on_sale 매물을 열어서 버튼이 애초에 안 뜬다). E6에 sold 상태 상세를 열어 버튼 존재를 확인하는 단계를 추가했다.
- 참고(defer로 장부에 신규 등재, 이 패스에서 코드 변경 없음): [[DW-721]](`is_admin()`이 `profiles.status`를 안 봐서 **정지된 관리자**도 이 RPC를 쓸 수 있다 — 직접 실측으로 재현했다. 스펙 Never 절이 정지 게이트를 명시적으로 범위 밖에 뒀으므로 이 스토리의 결함은 아니지만, `0030`은 SECURITY DEFINER라 RLS를 우회하므로 **Epic 17의 `17-1-정지-회원-쓰기-차단-rls`가 RLS 범위로만 구현되면 이 경로가 안 닫힌다** — 그 스토리 인수조건으로 심으라고 trigger에 적었다) · [[DW-722]](`supabase db reset`로 만든 로컬 스택엔 플랫폼 기본 테이블 GRANT가 없어 로그인 사용자용 앱이 통째로 안 뜬다 — 이번 검증 중 실측으로 드러난 기존 환경 갭. CI 프렐류드만 그걸 재현한다).
- reject(11건, 근거와 함께 기각): "원격 Supabase에는 anon EXECUTE가 남아 있다"는 결론부(미측정 추정 — 측정 가능한 두 환경 모두 false였다. 관례 불일치만 patch로 채택) · `router.refresh()`를 await하지 않고 `finally`에서 상태를 푼다(스펙이 "`MemberActions.tsx`와 동일한 모양"을 명시 지시했고 그 파일이 정확히 같은 형태 — 리포 관례) · `returns table(id uuid)`의 `listings.id` 이름 충돌(스펙이 RPC 본문을 글자 그대로 못박았고, 실DB 테스트 12건이 실제 통과해 컬럼이 이긴다는 것이 실측됨) · 테스트 헬퍼의 SQL 문자열 보간(테스트 전용·신뢰 리터럴이고, 복붙 확산 축은 이미 DW-720이 갖고 있다) · `_create_user`의 `{"role":"seller"}` 메타데이터 라벨(0028·0029로 역할이 통합돼 무해하고, "판매자" 라벨은 `seller_id` 소유권으로 실재한다) · E6의 행 선택자를 `listingId`로 좁히지 않음(E3·E5가 `/sell`에서 정확히 같은 패턴을 쓰는 파일 전반의 기존 성질이지 이 변경이 만든 위험이 아님) · E6의 admin→seller 세션 전환에 별도 컨텍스트 없음(1차 패스가 근거와 함께 기각했고 이번에도 6/6 그린) · DW-391을 `status: resolved`로 닫은 형식이 장부 표준(`status: done <날짜>` + `resolution:`)과 다름(실재하는 지적이나, 이 실행의 지시가 **기존 장부 항목을 수정하지 말라**고 명시 — 오케스트레이터 소유) · 0행 UI 오류 문구가 렌더 테스트로 검증되지 않음(비관리자는 `requireRole` 게이트에 막혀 이 분기에 도달 자체가 불가하고, web에 컴포넌트 렌더 테스트 인프라가 없다 — 대신 분기의 **존재**는 위 소스 스캔이 고정) · 관리자 거래내역의 `updated_at`(거래일)이 되돌리기로 흔들림(1차 패스가 근거와 함께 기각했고 재검토해도 그 분석이 옳다 — 그 화면은 `status='sold'`만 필터한다) · `docs/tech-debt.md`가 아직 "어떤 롤로도 되돌릴 수 없다"고 적고 있음(그 파일은 훅으로 쓰기가 막힌 경위 전용 동결 문서이고, 새 런북 §10이 그것을 배경으로 인용한다).

### 2026-08-07 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 1, low 9)
- defer: 3: (low 3)
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` DW-391(이 스토리가 해소한 장부 항목)이 `deferred-work.md`에서 여전히 `status: open`이었다 — `resolved`로 갱신하고 이 스토리·RPC·런북 절을 근거로 남김(CLAUDE.md B8 "일을 끝내면 대장을 닫는다").
  - `[low]` `[patch]` `ListingAdminActions.tsx`의 삭제·되돌리기 버튼이 서로 독립된 `loading` 상태만 봐서, 한쪽 진행 중 다른 쪽을 눌러도 막히지 않는 레이스가 있었다 — `busy(=deleting||restoring)` 공유 가드를 두 버튼의 `disabled`와 두 핸들러의 조기 리턴 모두에 추가.
  - `[low]` `[patch]` E2E(`write-flows.spec.ts` E6)가 되돌린 뒤 "판매중" 배지만 확인하고 되돌리기 버튼 자체가 사라지는지는 확인하지 않았다 — `toHaveCount(0)` 단언 추가.
  - `[low]` `[patch]` `test_no_broad_admin_update_policy_exists`가 listings UPDATE 정책 집합 전체를 `{"listings_update_own"}`로 하드코딩해, 이 스토리와 무관한 향후 좁은 UPDATE 정책 추가에도 깨지게 돼 있었다 — Never 절이 실제로 금지하는 것("admin" 이름의 정책 부재)만 좁혀 확인하도록 수정.
  - `[low]` `[patch]` `handleRestore`의 0행 오류 메시지가 "권한 없음"을 앞세워, 버튼이 sold 매물에만 렌더돼 실제 도달 경로 대부분이 레이스(동시 처리)인 사실과 어긋났다 — "다른 관리자가 먼저 처리했을 수 있습니다"를 앞세우도록 문구 교체.
  - `[low]` `[patch]` `docs/deployment-runbook.md` §10-a가 "0030 미적용 환경"을 폴백 조건으로 들면서도 그걸 확인하는 방법이 없었고, "로그인 계정이 실제로는 관리자가 아님" 케이스도 안내가 없었다 — `pg_proc` 확인 쿼리 + `profiles.role` 확인 안내 추가.
  - `[low]` `[patch]` `0015_listings_update_not_sold.sql`과 `app/lib/features/listings/listings_repository.dart:167`의 "sold→on_sale 되돌리기는 없다"는 주석이 `0030` 이후 더 이상 전부 참이 아닌데 갱신되지 않았다 — 두 파일 모두에 관리자 전용 예외(0030)를 명시하는 주석 추가.
  - `[low]` `[patch]` `admin_restore_sold_listing`이 실제로 `status` 외 컬럼을 안 바꾼다는 Never 절 주장이 테스트로 실측되지 않았다 — `test_admin_restores_sold_listing`에 호출 전후 나머지 전 컬럼 스냅샷 비교 추가.
  - `[low]` `[patch]` `test_grant_execute_only_to_authenticated`가 authenticated·anon·PUBLIC 세 롤만 개별 확인해, 제3의 롤에 실수로 EXECUTE가 부여돼도 못 잡았다 — 함수 소유자를 실시간 조회해 제외한 뒤 나머지 grantee 집합이 정확히 `{authenticated}`인지 비교하도록 강화.
  - `[low]` `[patch]` E6이 재수정된 가격을 DB(`runPsql`)로만 확인하고 렌더된 상세 페이지는 확인하지 않아, E3가 잡는 것과 같은 부류의 렌더링 결함(되돌리기→재수정 경로 전용)을 못 잡을 수 있었다 — `/listings/{id}` 렌더 텍스트 단언 추가(E3와 동일 패턴).
- 참고(defer로 장부에 신규 등재, 이 패스에서 코드 변경 없음): [[DW-718]](관리자 쓰기 액션 전반의 감사 로그 부재 — 이 스토리 고유 결함이 아니라 기존 삭제·정지 액션과 공유하는 패턴), [[DW-719]](동시 다중 세션 되돌리기 레이스가 순차 테스트로만 검증됨 — 테스트 스위트 전반의 공백), [[DW-720]](`auth.users` 최소 컬럼 직접 insert 패턴이 여러 실DB 테스트 파일에 중복 — 3번째 복붙 전에 공유 헬퍼로 추출).
- reject(9건, 근거와 함께 기각): E2E의 admin 시드 계정 존재 미검증(기존 core-flows.spec.ts가 이미 같은 계정으로 CI에서 검증 중, 이 스토리가 새로 만든 위험 아님) · 되돌리기에 확인 다이얼로그 없음(스펙이 MemberActions 정지/해제 토글과 동일 모양을 명시 지시, 의도된 설계) · `status` 타입 좁히기에 런타임 검증 없음(리포 전역이 공유하는 기존 패턴이고 DB CHECK가 이미 값 자체를 제한) · E6이 admin→seller 3단계를 한 테스트에 묶음(스펙이 "왕복 검증"을 명시 요구, 분리는 스펙 위반) · E6이 별도 브라우저 컨텍스트 없이 admin→seller 세션 전환(로그인 페이지에 인증 시 리다이렉트 로직 없음을 직접 확인, 실제로 6/6 그린) · 관리자 거래내역 화면의 `updated_at`(거래일 근사)이 되돌리기로 흔들린다는 우려(그 화면은 `status='sold'`만 필터하므로 재판매 시 updated_at은 그 재판매 시점을 정확히 반영, 분석상 실패 시나리오 없음) · 주석 상호 참조 부재(cosmetic) · FR23 범위 문장의 모호함(cosmetic) · `handleRestore`의 `rpcError`(네트워크) 분기 미검증(verification-gap 렌즈가 기존 `handleDelete`도 동일하게 미검증인 리포 전역 관례임을 확인, 이 스토리 고유 결함 아님).

## Design Notes

RPC는 `increment_listing_view`(0020)의 SECURITY DEFINER 하드닝 패턴을 그대로 따른다: `language sql`, `set search_path = ''`, `revoke all ... from public` 후 `grant execute ... to authenticated`만(anon 제외). `returning id`로 0/1행을 클라이언트가 구분하게 해, `MemberActions.tsx`의 "0행=거부" 관례를 RPC에도 동일하게 적용한다. WHERE 절에 `status='sold' and public.is_admin()`을 함께 걸어 "비관리자 호출"과 "이미 on_sale인 행 호출"을 같은 0행 신호로 수렴시킨다 — 이 두 경우를 UI에서 굳이 구분하지 않는다(둘 다 버튼이 애초에 sold 매물에서만 렌더되므로 후자는 레이스 조건에서만 발생).

## Verification

**Commands:**
- `supabase db reset` (로컬) -- expected: `0030` 마이그레이션 에러 없이 적용
- `cd api && pytest tests/integration/test_restore_sold_listing_rpc_real_db.py -v` -- expected: 전부 통과(TEST_DATABASE_URL 필요, 없으면 skip)
- `cd web && npx tsc --noEmit` -- expected: 타입 에러 0
- `cd web && npm run lint` -- expected: 에러 0
- `cd web && npx playwright test write-flows.spec.ts --project=desktop-1280x800` -- expected: 전부 통과(E6 포함)

**Manual checks (if no CLI):**
- 다크 모드에서 "판매완료 되돌리기" 버튼이 sold 매물에만 보이는지 육안 확인.

## Auto Run Result

Status: done

### 3차 패스 (2026-08-07, 후속 리뷰 — `followup_review_recommended: true`로 재진입)

**무엇을 했나**: 기능은 그대로 두고, **2차 패스가 만든 검사들이 실제로 무엇을 잡는지**를 직접 깨서 확인했다. 결과가 이 패스의 성격을 정한다 — 2차 패스가 "검증 구멍을 메웠다"며 추가한 검사 중 **세 개가 자기가 주장하는 것을 못 보고 있었다**(무의미한 단언 1건, fail-open 게이트 1건, 아예 빠진 축 2개). 논증이 아니라 측정으로 갈랐다.

**파일 변경(3차)**:
- `api/tests/integration/test_restore_sold_listing_rpc_real_db.py` — `updated_at` 단언을 실제로 발화 여부를 보는 형태로 교체(트리거 우회 시드 + 심긴 값 선단언), 함수 오버로드 검출, 인라인 `reset role`의 트랜잭션 가드 복원.
- `web/src/app/(admin)/admin/listings/__tests__/restoreSoldWiringContract.test.ts` — 5개 축을 fail-open에서 불변식으로 교체(`isSold` 포함 관계 · `router.refresh()` · 0행 분기 · `.from('listings')` 앵커+토큰 비교 · busy 가드 개수→불변식), 주석 제거 과잉을 실패로 만드는 앵커 확인 추가.
- `web/e2e/write-flows.spec.ts` — E6에 **익명 컨텍스트 재노출 검증**(AC1의 실제 표면) 추가, 관리자 행 선택자를 `listingId`로 좁힘, 0행 오류 알림 부재 단언 추가.
- `docs/deployment-runbook.md` — §10에 "되돌리면 거래내역에서 사라지고 감사 기록이 없다" 경고 추가, §10-a의 `status='suspended'` 오진 유도 차단.
- `docs/conventions.md` — §6 SECURITY DEFINER 축에 `0030` 등재(규칙7이 요구하는 자리인데 비어 있었다).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-723·724·725 **신규 등재만**(기존 항목은 지시대로 손대지 않음).

**검증 수행(3차, 전부 직접 실행·관찰)**:
- `npx tsc --noEmit` → 0 에러 · `npm run lint` → 0 에러 · `npx vitest run` → **38 파일 340건 통과**.
- `pytest test_restore_sold_listing_rpc_real_db.py`(로컬 실DB) → **11건 통과**(변경 전후 테스트 개수 동일: 11 → 11, 유실 없음).
- `npx playwright test write-flows.spec.ts --project=desktop-1280x800` → **6/6 통과**(E6의 새 익명 재노출 단계 포함).
- **"만들었다"가 아니라 "잡는다"를 전 축에서 확인**(CLAUDE.md B4):
  - vitest 5축 mutation — 버튼을 `isSold` 밖으로 빼기 / `router.refresh()` 삭제 / 0행 분기 약화 / busy 가드 1개 제거 / `status`→`accident_status`. **5건 모두 red**, 되돌려 4/4 green.
  - 실DB — `listings_set_timestamps`를 "sold→on_sale 전환에서만 건너뛰게" 변조하니 `updated_at` 단언 **red**(낡은 값 2020-01-01이 그대로 잔존), 원본 정의 복원 후 11건 green. 고치기 전 단언은 이 변조를 **통과했다**(그래서 무의미했다는 것이 증명됐다).
  - E6 새 단언의 구별력 — 운영 빌드 서버를 띄우고 익명 `/search`에서 같은 매물 링크 수가 `on_sale=1 → sold=0 → 복원=1`로 뒤집히는 것을 직접 측정.
- **측정으로 기각한 것**: `service_role` EXECUTE 잔존 우려 → `has_function_privilege('service_role', …)` = **false**(실측). 추정이 아니라 측정으로 갈랐다.
- 검증 뒤 환경 원상 확인: 변조한 트리거 함수 복원 확인(변조 흔적 0건), 상태를 뒤집었던 매물 원복, 임시 서버 종료, `git status`에 의도한 7개 파일만.

**후속 리뷰 권고**: 이번 패스 patch 13건(medium 5, low 8) → 3×5 + 1×8 = **23 ≥ 5** → `followup_review_recommended: true` 유지.

**잔여 위험(3차)**:
- **이 패스가 드러낸 패턴이 잔여 위험 자체다.** 2차 패스가 추가한 검사 5개 중 3개가 자기가 주장하는 것을 못 봤고, 그 중 하나(`updated_at`)는 2차 패스가 red/green 실험까지 했는데도 **그 실험이 갭을 가르지 못하는 형태**였다. 앞으로 이 스토리 주변에 검사를 추가할 때는 "일부러 깼더니 red"만으로 부족하고 **"내가 주장하는 결함으로 깼는가"**를 따로 확인해야 한다.
- 신규 defer 3건: **DW-723**(`MemberActions.tsx` busy 가드 부재) · **DW-724**(`is_admin()`의 `search_path` 기준 불일치) · **DW-725**(sold 행 반응형 자동 검사 부재).
- 이전 패스의 **DW-718**(감사 로그 부재) · **DW-719**(동시 다중 세션 레이스 미검증) · **DW-720**(`auth.users` insert 중복) · **DW-721**(정지 관리자가 RPC 통과 — Epic 17-1이 반드시 흡수) · **DW-722**(로컬 `db reset`에 기본 GRANT 없음)는 그대로 열려 있다.
- 이번 패스가 **못 본 것**: PostgREST/HTTP 계층의 anon 거부(실DB 테스트는 Postgres 롤 임퍼소네이션까지만 본다 — 리포 전반의 구조적 한계) · 0행 오류 문구의 실제 렌더(분기 *존재*는 이제 CI가 고정하지만 문구가 그려지는지는 렌더 테스트 인프라가 없어 여전히 미검증) · E2E 전반이 CI 밖(`docs/tech-debt.md` #168).
- **워크플로 관찰(코드 아닌 축)**: `followup_review_recommended` 공식이 `3×medium + 1×low ≥ 5`라, 성실한 패스일수록 low가 5건 이상 나와 플래그가 구조적으로 안 꺼진다. 이번이 같은 diff의 3번째 리뷰다. 이 스토리 산출물이 아니라 루프 설계 축이라 patch로 고치지 않았지만, 다음 리뷰를 자동으로 도는 근거로 쓰기 전에 사람이 한 번 볼 만하다.

---

### 2차 패스 (2026-08-07, 후속 리뷰 — `followup_review_recommended: true`로 재진입)

**무엇을 했나**: 코드는 이미 done 상태였으므로 기능을 다시 만들지 않았다. 4개 렌즈로 baseline 이후 diff 전체를 다시 훑고, 나온 지적을 **직접 실측으로 갈라** 실재하는 9건만 고쳤다. 이번 패스의 성격은 "기능 추가"가 아니라 **검증 구멍 메우기**다 — 이 스토리의 web 쪽 배선이 CI에서 완전히 무검증이었고, 런북의 장애 대응 안내가 실제로는 틀린 진단으로 이끌고 있었다.

**파일 변경(2차)**:
- `supabase/migrations/0030_listings_restore_sold_rpc.sql` — EXECUTE 회수를 `public` 하나에서 `public`·`anon`·`authenticated` 3개 롤로(리포 관례 일치). 함수 주석에서 미실측 인과 단정("레이스 조건에서만 발생") 제거.
- `web/src/app/(admin)/admin/listings/__tests__/restoreSoldWiringContract.test.ts` — **신설**. RPC 이름·`p_listing_id` 키·`isSold` 게이트·`busy` 공유 가드·두 화면의 `status` 조회+전달을 CI(`web` 잡)가 보는 검사로 고정.
- `docs/deployment-runbook.md` — §10-a의 잘못된 원인 순서와, 이 절에서는 항상 NULL인 `auth.uid()` 진단 쿼리를 교체.
- `api/tests/integration/test_restore_sold_listing_rpc_real_db.py` — 행동 검증 `test_rpc_is_the_only_door_to_a_sold_row` 신설(정책 이름이 아니라 "다른 문을 실제로 밀어본다"), `updated_at` 트리거 발화 실측 단언 추가.
- `web/e2e/write-flows.spec.ts` — E6에 sold 상태 **상세 화면** 버튼 확인 추가, 병렬 간섭 분석의 on_sale 창 서술을 실제 수명주기(2구간)로 정정.
- `web/src/app/(admin)/admin/listings/page.tsx`·`[id]/page.tsx` — "삭제만" 시대의 주석 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-721·DW-722 **신규 등재만**(기존 항목은 지시대로 손대지 않음).

**검증 수행(2차, 전부 직접 실행·관찰)**:
- `npx tsc --noEmit` → 0 에러 · `npm run lint` → 0 에러 · `npm test`(vitest) → **38 파일 340건 통과**(신설 계약 테스트 4건 포함).
- `npx supabase db reset` → `0030` 포함 전 마이그레이션 무에러 적용. 적용 후 `has_function_privilege('anon', …)` = **false**, `authenticated` = true로 GRANT 상태 실측.
- **CI 동등 환경 재현**(일회용 `pgvector/pgvector:pg17` 컨테이너 + `scripts/migration-check-prelude.sql` + 전 마이그레이션) → `pytest tests/integration` **116건 전부 통과**. 이 재현이 필요했던 이유는 아래 잔여 위험 DW-722 참조.
- `npx playwright test write-flows.spec.ts` → **6/6 통과**(E6 상세 확인 포함) · `core-flows.spec.ts` → **10/10 통과**(관리자 화면 회귀 없음) · `viewport-audit.spec.ts` → **21/21 통과**(3 뷰포트).
- **"만들었다"가 아니라 "잡는다"를 확인**(CLAUDE.md B4): 새 vitest 계약의 4개 축(RPC 이름·isSold 게이트·busy 가드·status prop)을 각각 일부러 깨서 red → 되돌려 green. 새 실DB 테스트 2건도 DB를 실제로 깨서 확인 — 넓은 UPDATE 정책(`listings_update_moderation`)을 심자 새 행동 테스트는 red인데 **기존 이름 검사는 green**이었다(그 갭이 실재했다는 직접 증거). `listings_set_timestamps` 트리거를 drop하자 `updated_at` 단언이 red.
- **D5(반응형 무결성) 육안 확인**: 390px·1280px × 라이트/다크 4조합에서 sold 행을 실제로 렌더해 캡처. 배지·"판매완료 되돌리기"·"삭제"가 390px에서도 **한 줄을 유지**하고(두 버튼 y좌표 동일, 라벨 1줄), 공간 부족은 요약 텍스트의 `…` truncate로만 흡수됨을 확인. 행 우측 끝 366px ≤ 뷰포트 390px.

**후속 리뷰 권고**: 이번 패스 patch 9건(medium 4, low 5) → 3×4 + 1×5 = **17 ≥ 5** → `followup_review_recommended: true` 유지.

**잔여 위험(2차)**:
- **DW-721** — `is_admin()`이 `profiles.status`를 안 봐서 정지된 관리자도 이 RPC를 쓸 수 있다(직접 실측 재현). 스펙 Never 절이 정지 게이트를 범위 밖에 뒀으므로 이 스토리의 결함은 아니지만, **Epic 17의 `17-1`이 RLS로만 구현되면 SECURITY DEFINER RPC인 이 경로는 안 닫힌다.** 장부 trigger에 "17-1 인수조건으로 심을 것"을 명시했다.
- **DW-722** — 로컬 `supabase db reset` 직후 `authenticated`에 테이블 GRANT가 없어 로그인 사용자용 앱이 통째로 안 뜬다(실측). 이번 검증에서 E2E가 E1부터 죽었고, 기존 `test_view_count_rpc_real_db.py` 2건도 로컬에서만 실패했다 — **CI 동등 컨테이너에서는 116건 전부 통과**하므로 코드 결함이 아니라 환경 축이다. 로컬은 기준선 GRANT를 수동 복원해 검증을 마쳤다(리포 변경 아님).
- 1차 패스의 DW-718(감사 로그 부재)·DW-719(동시 다중 세션 레이스 미검증)·DW-720(`auth.users` insert 중복)은 그대로 열려 있다.
- 이번 패스가 **못 본 것**: 0행 UI 오류 문구가 브라우저에 실제로 렌더되는지(web에 컴포넌트 렌더 테스트 인프라가 없고, 비관리자는 `requireRole` 게이트에 막혀 그 분기에 도달 자체가 불가) · PostgREST HTTP 계층의 anon 거부(실DB 테스트는 Postgres 롤 임퍼소네이션까지만 본다) · 원격 Supabase 프로젝트의 실제 기본 ACL(측정 수단 없음 — 그래서 3개 롤 회수로 전제 자체를 없앴다).

---

### 1차 패스 (2026-08-07)

**요약**: 오조작으로 "판매완료(sold)"가 된 매물을 관리자가 화면에서 되돌릴 방법이 DB에 직접 SQL을 치는 것뿐이던 문제(DW-391)를 해소했다. `status`만 `sold`→`on_sale`로 되돌리는 좁은 `SECURITY DEFINER` RPC(`admin_restore_sold_listing`, 0030)를 신설하고, 관리자 매물 관리 목록·상세 화면에 sold 매물 한정 "판매완료 되돌리기" 버튼을 추가했다. 런북의 수동 SQL 절차는 이 화면 절차로 대체하고 비상용 백업으로 격하했다. Epic 15는 UI-only 원칙이지만 이 스토리는 계획 문서가 명시한 유일한 예외(마이그레이션 1개)다.

**파일 변경**:
- `supabase/migrations/0030_listings_restore_sold_rpc.sql` — 신규 RPC. `is_admin()` 내부 확인 + `status='sold'` 조건 + `security definer`/`search_path=''`/GRANT 하드닝(0020 패턴 그대로).
- `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx` — 되돌리기 버튼 추가, 삭제·되돌리기 간 공유 busy 가드(코드리뷰 patch), 0행 오류 문구를 레이스 우선으로 재작성(코드리뷰 patch).
- `web/src/app/(admin)/admin/listings/page.tsx`, `.../[id]/page.tsx` — `status` prop 전달.
- `docs/deployment-runbook.md` — §10을 화면 절차로 교체, §10-a(비상용 SQL)에 배포 확인 쿼리 추가(코드리뷰 patch).
- `supabase/migrations/0015_listings_update_not_sold.sql`, `app/lib/features/listings/listings_repository.dart` — "되돌리기 없음" 주석이 0030 이후 더 이상 전부 참이 아님을 반영(코드리뷰 patch).
- `api/tests/integration/test_restore_sold_listing_rpc_real_db.py` — RPC 권한 매트릭스·멱등성·구조 검증 실DB 테스트 10건 신설(관리자/비관리자/소유자/anon/멱등/존재하지않는id/명명인자/정책구조/파라미터시그니처/GRANT 완전성). 코드리뷰 patch 3건 반영(정책 집합 단언 완화, 컬럼-불변 단언 추가, GRANT 단언 강화).
- `web/e2e/write-flows.spec.ts` — E5 뒤 E6 추가(관리자 되돌리기→판매자 재수정·재구매완료 왕복). 코드리뷰 patch 2건 반영(버튼 소멸 단언, 렌더 페이지 가격 단언).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-391을 `resolved`로 갱신, DW-718/719/720 신규 등재(감사로그 부재·동시성 테스트 공백·auth.users insert 중복, 전부 이 스토리 고유 결함 아닌 defer).

**리뷰 결과**: adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 렌즈 병렬 실행(diff 전체 대상). intent_gap 0, bad_spec 0 — 재도출 루프 없음. patch 10건(medium 1, low 9) 전부 적용·재검증 완료. defer 3건 신규 장부 등재(DW-718~720, 전부 이 스토리 고유 결함이 아닌 리포 전반의 기존 패턴). reject 9건은 근거와 함께 기각(스펙이 명시 지시한 설계, 이미 검증된 전제, 또는 분석상 실패 시나리오 없음 — 상세는 위 Review Triage Log 참조). 후속 리뷰 권고 점수 3×1(medium)+1×9(low)=12 ≥ 5 → `followup_review_recommended: true`.

**검증 수행**(전부 오케스트레이터가 직접 실행·관찰, 구현 직후 1차 + 패치 적용 후 2차): `npx tsc --noEmit`(0 에러) · `npm run lint`(0 에러) · `pytest test_restore_sold_listing_rpc_real_db.py`(10 passed, 패치 후에도 10 passed) · `npx playwright test write-flows.spec.ts --project=desktop-1280x800`(6 passed, E6 포함, 패치 후에도 6 passed) · `npx playwright test core-flows.spec.ts --project=desktop-1280x800`(10 passed — 관리자 화면 전반 회귀 없음, 패치 후에도 10 passed). I/O & Edge-Case Matrix 5행 전부 실행·통과한 테스트로 커버됨(Matrix Test Audit 통과).

**잔여 위험**: DW-718(관리자 쓰기 액션에 감사 로그 없음, 실사용자 운영 단계 트리거) · DW-719(동시 다중 세션 되돌리기 레이스가 순차 테스트로만 검증됨) · DW-720(`auth.users` 직접 insert 패턴이 여러 실DB 테스트 파일에 중복) — 셋 다 낮은 심각도이고 이 스토리 고유 결함이 아니라 리포 전반의 기존 패턴이라 defer로 장부에만 남긴다.
