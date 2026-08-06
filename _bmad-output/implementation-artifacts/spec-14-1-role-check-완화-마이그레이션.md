---
title: '14.1 role CHECK 완화 마이그레이션'
type: 'chore'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
baseline_revision: 'a44b522e4cf7d1020c264b321a96c570818915e2'
final_revision: '4358cc30630e66846e117146cbd251620af28f08'
---

<intent-contract>

## Intent

**Problem:** `profiles.role`은 `check (role in ('buyer', 'seller', 'admin'))`으로 고정돼 있어, 이후 스토리(14.2 가입 트리거 기본값 변경)가 buyer/seller가 아닌 새 기본값을 넣을 자리가 없다. 역할 통합(구매자/판매자 구분 폐지)의 첫 단추로 이 CHECK부터 완화해야 한다.

**Approach:** 새 forward 마이그레이션으로 기존 3값 enum CHECK를 drop하고, admin 여부만 의미 있게 유지하는(더 느슨한) CHECK로 교체한다. 컬럼 rename·기존 데이터 변경은 하지 않는다.

## Boundaries & Constraints

**Always:**
- `profiles.role` 컬럼명은 그대로 둔다(rename 금지 — `is_admin()`·0005·기존 RLS가 의존).
- 기존 계정의 `role` 값(buyer/seller/admin)은 데이터를 UPDATE하지 않고 그대로 보존한다(forward-only, B3).
- `is_admin()`(0001)이 계속 정확히 동작해야 한다 — `role = 'admin'` 비교는 이 마이그 이후에도 유효해야 한다.
- 새 마이그 파일 번호는 **구현 시점에** `supabase/migrations/` 목록에서 `max+1`로 정한다 — 지금 하드코딩하지 않는다(과거 사전 번호 배정이 스테일해진 전례가 있어 폐기됨, 아키텍처 결정).
- DDL 실행 전 실제 CHECK 제약 이름을 `pg_constraint`로 직접 조회해 확인한다 — 기본 명명 규칙(`profiles_role_check`)을 추정만으로 하드코딩하지 않는다.
- `python3 scripts/check_migrations.py`(정적 파일명·번호 밀집 검사 + Docker 동적 self-containment 검사)를 통과해야 한다.
- AC-F14-1: `grep -rn "role" supabase/migrations/*.sql`로 이 CHECK 완화가 기존 RLS의 role 비교를 깨지 않는지 검증하고 결과를 남긴다.

**Block If:**
- AC-F14-1 grep에서 `is_admin()`/`handle_new_user()` 외에 `role = 'buyer'` 또는 `role = 'seller'`를 직접 비교하는 RLS 정책이 실제로 발견되면 → 완화 방향에 대한 판단이 필요하므로 HALT(status: blocked).
- `scripts/check_migrations.py`의 동적(Docker) 검사가 환경 문제로 돌지 않으면 → 정적 검사만으로 통과를 선언하지 않고 HALT.

**Never:**
- `handle_new_user` 트리거의 기본값 로직 변경(Story 14.2 범위) — 이 스토리에서 건드리지 않는다.
- 판매 게이트(`requireRole(SELLER)` → `requireUser()`) 변경(Story 14.3 범위) — 이 스토리에서 건드리지 않는다.
- `account_type` 등 신규 컬럼 추가 — 이번 증분은 값 의미만 좁힌다(컬럼 추가 없음).
- 기존 `role` 값을 일괄 변경하는 `UPDATE` 문 포함.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 기존 값 보존 | 마이그 적용 전 `role='buyer'`인 기존 행 | 마이그 적용 후 재조회해도 `role='buyer'` 그대로 | No error expected |
| 신규 비-buyer/seller 값 허용 | `insert into profiles(id, role) values (<uuid>, 'whatever')` | 더 이상 CHECK violation으로 거부되지 않음(NOT NULL 등 다른 제약은 그대로) | No error expected |
| admin 게이트 무손상 | `role='admin'`인 프로필로 `is_admin()` 호출 | `true` 반환(회귀 없음) | No error expected |
| NULL 여전히 거부 | `insert into profiles(id, role) values (<uuid>, null)` | 컬럼 `not null` 제약으로 여전히 거부 | `null value in column "role" violates not-null constraint` |

</intent-contract>

## Code Map

- `supabase/migrations/0001_profiles.sql` -- 완화 대상인 원본 3값 enum CHECK와 `is_admin()`(role='admin' 비교)이 정의된 곳. 읽기 전용 참고(수정 금지, forward-only).
- `supabase/migrations/000N_role_check_relax.sql` (N = 구현 시점 max+1) -- 이 스토리가 만드는 신규 마이그레이션.
- `scripts/check_migrations.py` -- 마이그레이션 게이트. 로컬 검증 커맨드.
- `supabase/migrations/0002·0005·0012·0014·0025·0026_*.sql` -- 전부 `is_admin()`을 통해서만 role을 참조하는 admin 게이트 정책(AC-F14-1 grep 검증 시 이미 확인됨, 직접 `role='buyer'|'seller'` 비교하는 정책 없음).
- `api/tests/integration/test_role_check_relax_real_db.py` (2026-08-06 후속 리뷰가 신규 추가, 3차 리뷰가 3건 증설) -- 이 완화를 매 push마다 잡는 실행 검사(15건). CI `api-db` 잡이 전체 마이그 적용 후 자동 실행한다. ①~⑤는 적용이 끝난 DB 상태를, ⑥~⑧은 0027을 디스크에서 읽어 재실행해 **적용되는 순간**(기존 행 무변경·드리프트 시 중단)을 본다.

**이 완화가 거짓으로 만든 서술·타입을 고친 소비처(리뷰 패치로 함께 변경됨 — 14.2/14.3이 같은 자리를 다시 본다):**

- `web/src/app/(admin)/admin/members/page.tsx` -- 행 타입이 `role: UserRole`이었는데 그 타입을 참으로 만들어주던 것이 방금 지운 CHECK다. `string`으로 넓히고 `ROLE_LABEL` 인덱싱에 폴백 적용.
- `web/src/lib/__tests__/roleLabelFallback.test.ts` (3차 리뷰가 신규 추가) -- 위 폴백 규칙을 주석이 아니라 검사로 고정(web/src 전체 스캔). CI `web` 잡의 `npm test`가 실행.
- `web/src/lib/constants.ts` · `app/lib/features/auth/user_role.dart` -- "profiles.role CHECK와 일치"라는 이제-틀린 주석 정정(Dart 쪽은 실제로 `user_metadata['role']`을 읽는다는 경로 정정 포함).
- `docs/db-schema-guide.md` · `docs/learning/01-db.md` -- role 컬럼의 3값 CHECK 서술 정정.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/000N_role_check_relax.sql` -- 신규 파일 생성 -- 다음 세 단계로 구성: (1) `select conname from pg_constraint where conrelid = 'public.profiles'::regclass and contype = 'c';`로 실제 제약 이름 확인, (2) `alter table public.profiles drop constraint <확인된 이름>;`으로 3값 enum CHECK 제거, (3) admin 외 값을 자유롭게 허용하는 완화된 CHECK로 교체(Design Notes 참고) — 데이터 UPDATE 문 없음
- (검증) `grep -rn "role" supabase/migrations/*.sql` 실행 -- AC-F14-1 수행 -- 결과를 구현 보고에 남긴다(이미 사전 조사로 위 Code Map에 정리됨, 재확인만)

**Acceptance Criteria:**
- Given 신규 마이그가 로컬 pgvector 컨테이너에 전체 순서대로 적용된 상태, when `role`에 `'buyer'`/`'seller'`가 아닌 임의 텍스트로 insert하면, then CHECK violation 없이 성공한다
- Given 동일 환경, when `role='admin'`인 행에 대해 `is_admin()`을 호출하면, then `true`를 반환한다
- Given 마이그 적용 전 `role='buyer'`로 존재하던 행, when 마이그 적용 후 그 행을 조회하면, then `role` 값이 여전히 `'buyer'`다(무변경)
- Given 전체 `supabase/migrations/*.sql`, when `python3 scripts/check_migrations.py`를 실행하면, then exit code 0으로 통과한다

## Design Notes

- **CHECK 이름을 추정하지 않는 이유**: `create table`의 인라인 컬럼 CHECK는 Postgres가 `<table>_<column>_check` 관례로 자동 명명한다(이 경우 `profiles_role_check`로 추정됨). 그러나 이건 관례일 뿐 보장이 아니므로, DDL을 쓰기 전에 `pg_constraint`로 실제 이름을 확인한다(CLAUDE.md B4 — 재보기 전엔 선언하지 않는다).
- **완화 폭을 "특정 새 값 집합"으로 좁히지 않는 이유**: 14.2의 신규 가입 기본값이 아직 미정이다. 지금 `role in ('user', 'admin')`처럼 구체적 신규 집합으로 좁히면 기존 `buyer`/`seller` 행이 그 즉시 위반 상태가 된다 — Postgres CHECK는 UPDATE 시 변경 컬럼과 무관하게 행 전체를 재평가하므로, 그 행의 아무 컬럼이나 이후 UPDATE되는 순간 조용히 실패한다. 그래서 완화는 **비-admin 값을 자유롭게 허용하는 방향**이어야 한다(CHECK 제거 또는 사실상 무제한 조건) — 특정 신규 문자열을 강제하지 않아야 14.2가 무엇을 고르든 14.1을 다시 열 필요가 없다.
- `role` 컬럼 자체의 `not null`은 테이블 정의(0001)에 이미 있으므로 이 마이그가 별도로 강제할 필요는 없다.

## Verification

**Commands:**
- `python3 scripts/check_migrations.py` -- expected: exit 0 (정적 파일명/번호 검사 + Docker 동적 self-containment 검사 모두 통과)
- `grep -rn "role" supabase/migrations/*.sql` -- expected: `is_admin()`·`handle_new_user()` 외에 role 값을 직접 비교하는 곳이 새로 생기지 않았음을 육안 확인(AC-F14-1)

**Manual checks (if no CLI):**
- 로컬 pgvector 컨테이너에 전체 마이그 적용 후 `select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid = 'public.profiles'::regclass and contype = 'c';`로 새 CHECK 정의가 buyer/seller를 더 이상 강제하지 않음을 눈으로 확인

## Verification Evidence

리뷰(verification-gap 렌즈)가 "실행 증거가 없다"고 지적해 추가한, 실제로 돌려 확인한 기록(CLAUDE.md B4).

- `select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid = 'public.profiles'::regclass and contype = 'c';` → `profiles_role_check | CHECK ((role <> ''::text))` (기존 3값 enum 사라짐, 이름은 재사용).
- 신규 임의 값 허용: 트리거로 만들어진 기존 행을 `update ... set role = 'whatever-new-value'` → 성공, 재조회 시 그 값 그대로.
- `role='admin'`인 행에 대해 세션을 `request.jwt.claim.sub`로 그 행 id로 흉내 낸 뒤 `select public.is_admin();` → `t`(회귀 없음).
- 기존 `role='buyer'` 행(마이그 적용 후에도 마이그가 UPDATE하지 않은 행) 재조회 → `role='buyer'` 그대로.
- `insert into profiles(..., role) values (..., null)` → `null value in column "role" violates not-null constraint`로 여전히 거부(컬럼 자체의 NOT NULL, CHECK와 무관하게 유효).
- `grep -rn "role" supabase/migrations/*.sql` → `is_admin()`(0001:66)·`handle_new_user()`(0001·0009)의 `v_role`/`role = 'admin'` 비교 외에 role 값을 직접 비교하는 RLS 정책은 없음(AC-F14-1 충족).
- `python3 scripts/check_migrations.py` → exit 0(정적+Docker 동적 검사 전부 통과, 패치 적용 후 재실행으로 재확인).
- 위 5개 DB 확인은 전부 신규 pgvector 컨테이너에 0001~0027 전체를 순서대로 적용한 뒤 실행했고, 검증 후 컨테이너는 `docker rm -f`로 정리했다(잔여 없음 확인).

### 2026-08-06 후속 리뷰 패스에서 추가로 실측한 것

1차 패스의 증거는 **사람이 한 번 손으로 본 기록**이었고 계속 도는 검사가 없었다. 이번 패스가 그 자리를 메웠고, 아래는 전부 새 일회용 pgvector 컨테이너(프렐류드 + 0001~0027 전량 적용)에서 실제로 돌린 결과다.

- **새 검사가 실제로 "잡는지"(B4: 만든 게 아니라 잡는 게 완료)**: `test_role_check_relax_real_db.py` 12건 green → 0027의 CHECK를 원래 3값 enum으로 되돌려 재실행 → **9건 red**(`test_non_enum_role_is_accepted` 4건 · `test_no_check_constraint_still_enforces_buyer_or_seller` · 사각지대 명시 4건) → 원복 후 다시 **12건 green**. 즉 이 스토리가 무효화되면 CI가 빨개진다.
- **마이그 사후조건 가드가 이름 드리프트를 잡는지**: 제약을 `profiles_role_check_legacy`로 rename(3값 enum 그대로)한 뒤 0027 재적용 → `drop ... if exists`가 예상대로 `does not exist, skipping`으로 no-op이 됐고, 새로 넣은 `do $$ ... raise exception` 사후조건이 **psql exit 3으로 마이그를 중단**시켰다(`3값 CHECK가 아직 남아 있다 — drop이 no-op였다`). 가드 추가 전에는 이 시나리오가 조용히 성공했다.
- **테이블 COMMENT 갱신 확인**: `select obj_description('public.profiles'::regclass, 'pg_class')` → `역할(role: admin만 is_admin()이 특별 취급, 그 외 값은 DB가 강제하지 않음 — 0027)…`로 실제로 바뀜(0001의 3값 서술이 DB 안에 남아 있던 마지막 사본).
- **회귀 없음**: `pytest tests/integration` 전체 **90건 통과**(기존 78 + 신규 12). `npx tsc --noEmit` exit 0 · `npm run lint` 통과 · `npm test`(vitest) **305건 통과** · `flutter analyze` No issues found.
- `python3 scripts/check_migrations.py` → 0027 사후조건·COMMENT 추가 후에도 **exit 0**(정적 + Docker 동적 프로브 3축 전부 통과).
- 검증에 쓴 컨테이너는 `docker rm -f role-relax-test`로 정리했고 `docker ps -a` 잔여 0개 확인.

### 2026-08-06 3차 리뷰 패스에서 추가로 실측한 것

2차 패스가 만든 가드들이 **CI에서 실제로 발화하는지**는 아무도 확인하지 않았다. 이번 패스가 그걸 재현해 확인했고, 아래는 전부 새 일회용 pgvector 컨테이너(프렐류드 + 0001~0027 전량 적용)에서 돌린 결과다.

- **0027 사후조건의 술어 구멍(실측 대조)**: `role in ('seller','admin')`처럼 buyer가 빠진 드리프트를 만들어 두 술어를 같은 DB에서 나란히 평가 → 옛 술어(`ilike '%buyer%'`) `f`(못 잡음) · 새 술어(buyer **또는** seller) `t`(잡음). 수정 후 그 드리프트에 0027을 실제로 적용 → `ERROR: profiles.role의 3값 CHECK가 아직 남아 있다`로 중단 확인.
- **새 검사 3건이 실제로 "잡는지"**: ⑥⑦⑧ 추가 후 15건 green → 0027에 `update public.profiles set role = 'user' where role in ('buyer','seller');`를 넣어 재실행 → **⑥·⑧ 2건 red** → 원복 green. 별도로 0027 끝의 `do $$` 사후조건 블록을 통째로 제거 → **⑦ 1건 red**(`DID NOT RAISE RaiseException`) → 원복 green. 즉 2차 패스가 추가한 가드를 지우면 이제 CI가 빨개진다(그 전에는 아무 일도 없었다).
- **ROLE_LABEL 폴백 스캔이 실제로 "잡는지"**: 신규 vitest 3건 green → `admin/members/page.tsx`의 `?? m.role` 폴백 2곳을 제거 → **1건 red**(누락 지점 2곳을 파일명과 함께 보고) → 원복 green.
- **회귀 없음**: `pytest tests/integration` 전체 **93건 통과**(기존 78 + 14.1이 만든 15) · `npx tsc --noEmit` exit 0 · `npm run lint` 통과 · `npm test`(vitest) **308건 통과**(33파일) · `flutter analyze` No issues found.
- `python3 scripts/check_migrations.py` → 술어 수정 후에도 **exit 0**(정적 + Docker 동적 프로브 3축 전부 통과, 0027 적용 성공 로그 확인).
- 검증에 쓴 컨테이너(`role-relax-p3`)는 종료 후 `docker rm -f`로 정리했다.

## Spec Change Log

## Review Triage Log

### 2026-08-06 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 2: (high 0, medium 1, low 1)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` `docs/db-schema-guide.md`·`web/src/lib/constants.ts`·`app/lib/features/auth/user_role.dart` 세 곳이 "role은 buyer/seller/admin 3값만 CHECK로 허용"이라는 이제-틀린 서술을 유지 — 완화된 사실을 반영해 정정
  - `[low]` `[patch]` `DROP CONSTRAINT`에 `IF EXISTS` 누락 + 새 제약 이름이 `<table>_<column>_check` 관례를 벗어남 — 기존 이름(`profiles_role_check`)을 그대로 재사용하고 `IF EXISTS` 추가로 동시 해결
  - `[low]` `[patch]` 마이그 주석이 "0005도 role 컬럼명에 의존한다"고 부정확하게 서술(실제론 `is_admin()`을 통해서만 의존, 0005는 role을 직접 참조하지 않음) — 정정
  - `[medium]` `[patch]` AC-F14-1 grep 결과·4개 AC 실측 결과가 산출물 어디에도 기록돼 있지 않아 "실행했다"는 주장을 사후 검증할 수 없었음 — `## Verification Evidence` 섹션을 신설해 실측 결과를 기록
- follow_up_score: patch 4건(high 0, medium 2, low 2) → 3×2(medium) + 1×2(low) = 8 ≥ 5 → `followup_review_recommended: true`

### 2026-08-06 — Review pass (후속 리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 4, low 3)
- defer: 2: (high 0, medium 1, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` `0027`의 `drop constraint if exists`가 **이 스펙이 Always 제약으로 세운 "이름을 추정하지 않는다"를 사실상 무력화**했다 — 배포 대상 DB의 제약 이름이 다르면 drop이 조용히 no-op이 되고 뒤이은 add가 두 번째 CHECK로 성공해, 옛 3값 enum이 살아남은 채 마이그는 성공을 보고한다(Postgres는 CHECK를 AND 결합). 1차 패스의 이름 확인은 "이 레포의 0001로 만든 컨테이너"에서 한 것이라 드리프트를 원리적으로 못 본다 → 마이그 끝에 `do $$ ... raise exception` 사후조건을 넣어 그 경우 크게 실패하게 함(드리프트를 재현해 exit 3 확인)
  - `[medium]` `[patch]` `0001`의 `comment on table public.profiles`가 여전히 "역할(buyer/seller/admin)"이라고 서술 — 3값 사본 중 유일하게 **DB 카탈로그 안에 사는 것**이라 레포 문서를 고쳐도 Supabase Studio·`\d+`·스키마 introspection에는 닿지 않는다 → forward-only 원칙대로 0001을 고치지 않고 0027에서 `comment on table`로 덮어씀
  - `[medium]` `[patch]` 이 스토리의 행위 변경(role 어휘 제약 제거)을 **잡는 실행 검사가 0개**였다 — 스펙이 내세운 `check_migrations.py`는 profiles를 보는 프로브가 없어 이 스토리가 완전히 틀려도 exit 0이고(1차 패스가 이미 실측), 1차 증거는 삭제된 컨테이너에서 한 번 손으로 본 산문이었다. 그런데 CI `api-db` 잡이 이미 전체 마이그 적용 후 실DB 테스트를 돌리고 `tests.yml`이 `supabase/migrations/**`를 "제약을 약화·삭제하는 변경"을 잡으려고 paths 트리거에 넣어뒀다 → `api/tests/integration/test_role_check_relax_real_db.py` 신규(12건), 되돌리면 9건 red 확인 후 원복 green
  - `[medium]` `[patch]` `web/src/app/(admin)/admin/members/page.tsx`의 행 타입이 `role: UserRole`인데 그 타입을 참으로 만들어주던 것이 방금 지운 CHECK였고, role 라벨을 그리는 코드 7곳 중 **이 페이지만** 폴백(`?? profile.role`)이 없었다(:76 표시, :99 삭제 확인 문구) — 14.2가 새 기본값을 쓰는 순간 라벨이 빈칸이 되고 `MemberActions`의 `label`이 "undefined <회원>"이 된다 → 타입을 `string`으로 넓히고 형제 6곳과 같은 폴백 적용
  - `[low]` `[patch]` `docs/learning/01-db.md:61`이 여전히 `CHECK(buyer/seller/admin)` — 1차 패스가 "3곳 정정"으로 확정했으나 실제로는 4번째 사본이 남아 있었다(현재 스키마를 서술하는 문서) → 정정. 참고: `_bmad-output/planning-artifacts/architecture.md:157`도 3값을 유지하나 그건 계획 시점 스냅샷이라(0009의 `name` 컬럼도 없음) 소급 정정 대상이 아님 → reject
  - `[low]` `[patch]` 0027 주석의 "NOT NULL의 취지를 이어 빈 문자열만 막는다"가 부정확 — NOT NULL은 컬럼 정의(0001)에 이미 있고 CHECK는 NULL에 unknown이라 애초에 관여하지 않는다. 더 중요하게는 `role <> ''`가 **어휘를 전혀 강제하지 않는다**는 사실이 어디에도 안 적혀 있었다 → 근거를 정정하고 "이 마이그 이후 role의 어휘는 DB가 강제하지 않는다(`' '`·`'ADMIN'`·`'admin '` 통과, is_admin()은 정확일치라 admin으로 인정 안 함)"를 명시
  - `[low]` `[patch]` `app/lib/features/auth/user_role.dart`에 1차 패스가 새로 단 주석이 **틀린 경로를 설명**했다 — 이 enum이 파싱하는 값은 `profiles.role`이 아니라 세션의 `user_metadata['role']`이다(`auth_controller.dart:30`의 `currentRoleProvider`). 14.2가 가입 역할선택을 없애면 metadata에 role이 안 실려 null이 되는 것이지 CHECK 완화 때문이 아니다 → 실제 경로로 정정
- follow_up_score: patch 7건(high 0, medium 4, low 3) → 3×4(medium) + 1×3(low) = 15 ≥ 5 → `followup_review_recommended: true`
- deferred: DW-661(마이그레이션 게이트 CI가 `test/bmad-loop`에서 안 돌아 에픽 첫 마이그 DoD 미충족 — 이 워크플로는 push를 하지 않으므로 여기서 해결 불가) · DW-662(1차 패스가 등재한 defer 2건이 장부의 `### DW-<번호>` 형식을 안 따라 번호로 조회되지 않음 — 이번 실행의 지시가 기존 항목 수정을 금해 신고만)
- rejected(주요): `role <> ''`가 공백·대소문자 변형을 허용(인텐트가 "admin 아닌 값은 자유롭게 허용"을 명시적으로 골랐고 사각지대를 테스트로 못박음) · `add constraint`에 `IF NOT EXISTS` 없음(Postgres 테이블 제약에 그 문법이 없고 마이그는 1회만 적용) · `sprint-status.yaml`(done)과 스펙 frontmatter(in-review) 불일치(이 리뷰 패스가 설정한 일시 상태, 패스 종료 시 done 복귀) · `conventions.md §9.1`에 CHECK drop-recreate 예외를 지금 문서화(이미 1차 패스가 장부에 등재했고 오케스트레이터 소유) · `architecture.md:157`의 3값 서술(계획 시점 스냅샷) · `db-schema-guide.md`가 운영 미적용인데 현재형(이 리포의 스키마 문서는 마이그레이션 기준으로 쓴다) · `profiles_update_admin`이 role을 무제한 UPDATE 가능(관리자 전권은 기존 설계, 완화 전에도 admin 승격 가능) · I/O 매트릭스의 INSERT 경로가 FK로 도달 불가해 UPDATE로 검증(CHECK 평가 관점에서 등가)

### 2026-08-06 — Review pass (3차 리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 4: (high 0, medium 2, low 2)
- reject: 13: (high 0, medium 0, low 13)
- addressed_findings:
  - `[medium]` `[patch]` 2차 패스가 넣은 0027 사후조건이 `pg_get_constraintdef(oid) ilike '%buyer%'` **한 문자열만** 봐서, buyer가 빠진 드리프트(예: `role in ('seller','admin')`)를 그대로 통과시켰다 — 짝이 되는 테스트 ⑤는 buyer **또는** seller를 보므로 두 층이 서로 다른 것을 보고 있었다. 술어를 테스트와 일치시키고, 같은 DB에서 옛/새 술어를 나란히 평가해 `f` vs `t`로 실측 대조
  - `[medium]` `[patch]` 2차 패스가 만든 가드들이 **CI에서는 발화 조건 자체가 생기지 않는 죽은 코드**였다 — CI DB는 언제나 0001부터 새로 만들어지므로 ①~⑤는 "적용이 끝난 상태"만 볼 뿐, 0027이 **적용되는 순간**(기존 행을 건드리는가·드리프트를 만나면 멈추는가)은 관측되지 않았다. 사후조건 블록을 통째로 지워도 아무것도 red가 되지 않았다 → 0027을 **디스크에서 읽어 트랜잭션 안에서 재실행**하는 검사 3건 신설(⑥ 기존 행 무변경 · ⑦ 드리프트 시 중단 · ⑧ 본문에 UPDATE/DELETE 없음), 각각 깨서 red 확인 후 원복 green
  - `[medium]` `[patch]` 2차 패스가 `admin/members/page.tsx` 한 곳의 폴백 누락을 고쳤지만, **다음 화면이 같은 실수를 반복하는 것을 막는 것은 주석 한 줄뿐**이었다(`ROLE_LABEL`은 여전히 전사상 `Record<UserRole, string>`이고 그 타입을 참으로 만들던 CHECK는 이 스토리가 지웠다) → `web/src/lib/__tests__/roleLabelFallback.test.ts` 신설: web/src의 모든 `ROLE_LABEL[...]` 인덱싱이 (a) `USER_ROLE.*` 상수 키이거나 (b) `??` 폴백을 갖는지 CI `web` 잡에서 매번 확인. 폴백을 지워 red 확인 후 원복 green
  - `[low]` `[patch]` 같은 파일 주석의 "형제 화면 **6곳**이 이미 쓰는 패턴"이 실제로는 8곳이었다 — 근거로 적은 숫자가 틀리면 다음 사람과 14.2/14.3이 그걸 믿는다. 숫자 사본을 지우고, 이 규칙을 지키는 것이 주석이 아니라 위 검사임을 명시
  - `[low]` `[patch]` `epic-14-context.md`가 **영어로 생성**돼 있었다(`document_output_language: korean`·CLAUDE.md §0 위반, 형제 산출물은 전부 한국어). 14.2·14.3이 인용할 파일이라 한국어로 옮기고, 그 안의 "관리자 회원관리 화면의 구매자/판매자 **필터** 정리"라는 서술이 실제 화면과 다름을 실측해 정정(그 화면에 역할 필터 UI는 없다 — 라벨만 있다. FR61 원문의 표현이 그대로 흘러들어온 것)
  - `[low]` `[patch]` 스펙 Code Map이 이 스토리가 실제로 바꾼 소비처 파일들(`admin/members/page.tsx`·`constants.ts`·`user_role.dart`·문서 2곳)을 하나도 담고 있지 않았다 — 14.2/14.3이 접점을 찾을 때 보는 자리다 → 추가. 테스트 파일 헤더의 "적용 시점 행 보존은 재현할 수 없다"는 서술도 ⑥ 추가로 스테일해져 함께 정정
- follow_up_score: patch 6건(high 0, medium 3, low 3) → 3×3(medium) + 1×3(low) = 12 ≥ 5 → `followup_review_recommended: true`
- deferred: DW-663(공용 픽스처가 가입 트리거 기본 role을 단언 → 14.2가 트리거를 바꾸면 실DB 테스트가 무더기로 깨진다) · DW-664(`tests.yml`도 이 브랜치에서 안 돌아 신규 검사 15건이 CI에서 실행된 적 없음 — DW-661은 `migration-gate.yml`만 지목) · DW-665(마이그레이션이 CI·원격 경로에서 원자적이지 않아 실패 시 앞부분만 적용된 채 남는다 — 레포 전체 관례 공백) · DW-666(`sprint-status.yaml`의 `epic-14`가 backlog인데 첫 스토리는 done). 지시대로 **신규 항목만 추가**했고 기존 항목은 건드리지 않았다.
- rejected(주요): 사후조건에 "새 제약이 실제로 생겼다"는 **긍정** 단언 추가(`test_empty_string_role_is_still_rejected`가 이미 `add constraint` 누락을 red로 잡음 — 실측 확인) · `ROLE_LABEL`을 `Partial<Record<...>>`나 헬퍼 함수로 바꾸는 타입 층 리팩터(이 스토리 범위 밖의 구조 변경이고, 새 스캔 검사가 같은 규칙을 이미 강제한다) · 스펙 Tasks/AC에 후속 패스 산출물용 AC 추가(AC 집합은 `<intent-contract>`의 I/O 매트릭스를 반영하는 자리이고, 리뷰가 추가한 검증 인프라는 Code Map·Verification Evidence·이 트리아지 로그가 담는다) · 테스트의 `set local ... = '{uuid}'` f-string(형제 파일과 같은 패턴, 값은 생성된 uuid) · 테스트 ⑤의 `profile` 픽스처 의존(신규 검사용으로 행을 안 만드는 `db` 픽스처를 따로 뒀고, 기존 테스트를 옮기는 건 외과적이지 않다) · 공백문자 role이 라벨을 빈칸으로 만든다(그 값을 쓰는 경로가 아직 없고, 완화의 사각지대로 이미 테스트에 명시돼 있다) · 신규 가입(INSERT) 경로가 여전히 buyer/seller로 강제된다(0009 트리거는 Story 14.2 범위 — Never 절이 명시적으로 금지, 대신 테스트 헤더에 사각지대로 기록) · `conventions.md §9.1`에 CHECK drop-recreate 예외 문서화 및 DW-662의 형식 정정(둘 다 이미 장부에 등재돼 있고 오케스트레이터 소유) · `final_revision`이 자기 자신을 기록하는 커밋을 못 담는다(워크플로 구조상 불가피, 이번 패스도 동일) · `followup_review_recommended` 점수식이 검증 인프라 추가를 행위 결함과 같은 무게로 센다(규칙대로 계산하고 관측만 기록)

## Auto Run Result

**요약**: `profiles.role`의 3값 enum CHECK(`buyer`/`seller`/`admin`)를 완화해 admin만 계속 의미 있게 식별되도록 하는 forward-only 마이그레이션(`0027_role_check_relax.sql`)을 추가했다. 컬럼명·기존 데이터는 손대지 않았고, `is_admin()`·기존 RLS가 여전히 정확히 동작함을 로컬 DB에서 실측 확인했다.

**변경 파일:**
- `supabase/migrations/0027_role_check_relax.sql` (신규) — profiles.role CHECK를 `role in ('buyer','seller','admin')`에서 `role <> ''`로 완화(같은 이름 `profiles_role_check` 재사용, `IF EXISTS` 포함).
- `docs/db-schema-guide.md` — role 컬럼 설명을 완화된 CHECK에 맞게 정정(리뷰 patch).
- `web/src/lib/constants.ts` — `USER_ROLE` 주석의 "profiles.role CHECK와 일치" 서술 정정(리뷰 patch).
- `app/lib/features/auth/user_role.dart` — `UserRole` enum 주석 정정 + 14.2 관련 향후 위험 메모 추가(리뷰 patch).
- `_bmad-output/implementation-artifacts/deferred-work.md` — defer 2건 등재(게이트 사각지대, conventions.md 문서화 공백).
- `_bmad-output/implementation-artifacts/epic-14-context.md` (신규) — Epic 14 컴파일 컨텍스트(계획 단계 산출물).

**리뷰 결과**: 4개 레이어(blind-hunter·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행. intent_gap 0 · bad_spec 0 · patch 4(medium 2, low 2, 전부 적용) · defer 2(medium 1, low 1, deferred-work.md 등재) · reject 4(트랜잭션 래핑 우려·공백문자 미차단·락 우려·모니터링창 관찰 — 근거 불충분 또는 이미 인프라가 처리).

**후속 리뷰 권고**: `true` — patch 4건(high 0, medium 2, low 2) → 3×2+1×2=8 ≥ 5.

**검증 수행**: `python3 scripts/check_migrations.py`(패치 적용 후 재실행 포함, 2회 모두 exit 0) · `grep -rn "role" supabase/migrations/*.sql`(AC-F14-1, is_admin()/handle_new_user() 외 role 값 직접 비교 없음 확인) · 로컬 pgvector 컨테이너에 0001~0027 전체 적용 후 4개 AC 전부 실측(제약 정의 조회·신규 값 허용·is_admin() true·기존 buyer 값 보존·NULL 거부) — 상세는 `## Verification Evidence` 참고. 검증에 쓴 컨테이너는 전부 정리됨(잔여 없음).

**잔여 리스크**: `check_migrations.py` 게이트가 이 마이그의 실제 CHECK 내용까지는 검증하지 못함(defer 등재, 게이트 설계 범위 밖) · `conventions.md §9.1`이 이번에 쓴 "CHECK drop 후 재생성" 패턴을 아직 문서화하지 않음(defer 등재) · 이 마이그는 아직 원격(운영) DB에 적용되지 않았다 — 실제 배포는 `docs/conventions.md` §9.4·CLAUDE.md B3에 따라 별도 승인 후 진행해야 한다.

---

## Auto Run Result — 2026-08-06 후속 리뷰 패스

**요약**: 1차 패스가 남긴 가장 큰 구멍은 "이 스토리가 한 일을 잡는 검사가 하나도 없다"였다. 마이그레이션 자체는 옳았으므로 코드를 되돌리지 않고(intent_gap 0 · bad_spec 0), 패치 7건으로 **검사를 실행되는 자리에 박고**(CI 통합 테스트 + 마이그 자체 사후조건) 완화가 깨는 소비처 1곳과 스테일/부정확한 서술 4곳을 정정했다.

**변경 파일(이번 패스):**
- `supabase/migrations/0027_role_check_relax.sql` — ① 이름 드리프트로 `drop`이 no-op이 되면 크게 실패시키는 사후조건(`do $$ ... raise exception`) ② `comment on table public.profiles` 갱신(DB 카탈로그에 남아 있던 마지막 3값 서술) ③ 주석의 부정확한 근거 정정 + "어휘는 이제 DB가 강제하지 않는다" 명시.
- `api/tests/integration/test_role_check_relax_real_db.py` (신규) — 완화를 매 push마다 잡는 실DB 검사 12건. CI `api-db` 잡이 자동 실행(배선 불필요).
- `web/src/app/(admin)/admin/members/page.tsx` — 행 타입 `role: UserRole` → `string`, `ROLE_LABEL` 인덱싱에 폴백 추가(형제 6곳과 동일 패턴).
- `docs/learning/01-db.md` — `role` 행의 3값 CHECK 서술 정정(1차 패스가 놓친 4번째 사본).
- `app/lib/features/auth/user_role.dart` — 1차 패스 주석이 설명한 경로 정정(이 enum이 읽는 건 `profiles.role`이 아니라 `user_metadata['role']`).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-661·DW-662 **신규 추가만**(기존 항목 무수정 — 이번 실행의 지시).

**리뷰 결과**: 4개 레이어(blind-hunter·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행. intent_gap 0 · bad_spec 0 · patch 7(medium 4, low 3, 전부 적용) · defer 2(DW-661·DW-662) · reject 10. 세 레이어가 독립적으로 같은 것을 짚은 항목이 셋이었다(사후조건 부재 · `comment on table` 잔존 · members 페이지 폴백 부재) — 그만큼 신호가 강했다.

**후속 리뷰 권고**: `true` — patch 7건(high 0, medium 4, low 3) → 3×4+1×3=15 ≥ 5. ⚠️ 다만 이번 패스의 patch는 **검증 인프라 추가**가 대부분이고 마이그레이션의 동작은 1차와 동일하다(사후조건·COMMENT는 순수 추가). 점수는 규칙대로 계산했으나, 다음 패스가 또 7건을 낼 여지는 이번에 상당히 줄었다.

**검증 수행**: 새 검사를 **일부러 깨서 red 확인 후 원복 green**(0027 되돌림 → 9건 red → 원복 → 12건 green) · 사후조건 가드를 **드리프트 재현으로 실측**(제약 rename 후 0027 적용 → psql exit 3으로 중단) · `pytest tests/integration` 전체 **90건 통과**(회귀 없음) · `python3 scripts/check_migrations.py` **exit 0** · `npx tsc --noEmit` exit 0 · `npm run lint` 통과 · `npm test` **305건 통과** · `flutter analyze` No issues found. 상세는 `## Verification Evidence`의 후속 패스 절 참고. 검증 컨테이너는 정리 완료(잔여 0).

**잔여 리스크**: (1) **마이그레이션 게이트 CI가 이 브랜치에서 한 번도 안 돌았다** — `test/bmad-loop`은 게이트 트리거(`develop`/`main`·PR) 밖이라 "에픽 첫 마이그 스토리는 게이트 통과가 DoD"(conventions §9.4)가 아직 문서상 미충족이다. 로컬 재현은 동적 Docker 검사까지 exit 0으로 통과했다(DW-661). (2) 이 마이그는 **아직 운영 DB에 적용되지 않았다** — 배포는 §9.4·CLAUDE.md B3에 따라 별도 승인 사항. (3) role의 **어휘를 강제하는 주체가 지금은 없다**(트리거가 buyer/seller만 배정하는 것에 의존) — 14.2가 기본값을 정할 때 다시 좁힐지 판단해야 하며, 그 사각지대는 새 테스트가 의도적으로 초록으로 못박아 두었다. (4) 1차 패스가 등재한 defer 2건은 장부 형식을 안 따라 번호로 조회되지 않는다(DW-662, 지시상 이번에 고치지 않음).

---

## Auto Run Result — 2026-08-06 3차 리뷰 패스

**요약**: 2차 패스는 "완화를 잡는 검사를 실행되는 자리에 박았다"로 끝났다. 이번 패스가 확인한 것은 **그 검사들이 정작 CI에서 발화하지 않는다**는 사실이다 — CI DB는 언제나 0001부터 새로 만들어지므로, 마이그레이션이 *적용되는 순간*에만 성립하는 일(기존 행을 건드리는가, 이름 드리프트를 만나면 멈추는가)이 한 번도 관측되지 않았고, 2차 패스가 넣은 사후조건 가드는 통째로 지워도 아무것도 red가 되지 않는 죽은 코드였다. 마이그레이션의 동작 자체는 여전히 옳으므로 코드를 되돌리지 않고(intent_gap 0 · bad_spec 0), 패치 6건으로 **가드를 살리고**(0027을 디스크에서 읽어 재실행하는 검사 3건 + 술어 구멍 수정) **폴백 규칙을 검사로 못박고**(web 정적 스캔) 산출물의 스테일·언어 위반을 정정했다.

**변경 파일(이번 패스):**
- `supabase/migrations/0027_role_check_relax.sql` — 사후조건 술어가 `%buyer%`만 보던 것을 buyer **또는** seller로 확장(짝이 되는 테스트 ⑤와 같은 술어). seller만 남은 드리프트를 옛 술어는 못 잡고 새 술어는 잡는 것을 같은 DB에서 실측 대조.
- `api/tests/integration/test_role_check_relax_real_db.py` — 검사 3건 증설(12→15): ⑥ 기존 행이 있는 상태에 0027을 재적용해도 role 무변경 · ⑦ 제약 이름 드리프트를 재현하면 0027이 `raise exception`으로 중단 · ⑧ 본문에 profiles를 바꾸는 UPDATE/DELETE 없음. 행을 만들지 않는 `db` 픽스처 추가(가입 트리거에 불필요하게 묶이지 않게). 헤더의 스테일 서술 정정.
- `web/src/lib/__tests__/roleLabelFallback.test.ts` (신규) — web/src의 모든 `ROLE_LABEL[...]` 인덱싱에 폴백이 붙어 있는지 CI `web` 잡에서 강제하는 정적 스캔 3건.
- `web/src/app/(admin)/admin/members/page.tsx` — 주석의 틀린 개수("형제 6곳" → 실제 8곳) 제거, 규칙을 지키는 주체가 위 검사임을 명시.
- `_bmad-output/implementation-artifacts/epic-14-context.md` — 한국어화(생성본이 영어였다) + 관리자 회원관리 "필터" 서술을 실측해 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-663·664·665·666 **신규 추가만**(기존 항목 무수정 — 이번 실행의 지시).

**리뷰 결과**: 4개 레이어(blind-hunter·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행. intent_gap 0 · bad_spec 0 · patch 6(medium 3, low 3, 전부 적용) · defer 4(DW-663~666) · reject 13. 세 레이어가 독립적으로 같은 것을 짚은 항목이 둘이었다(사후조건 술어가 buyer만 본다 · 공용 픽스처가 14.2와 충돌한다).

**후속 리뷰 권고**: `true` — patch 6건(high 0, medium 3, low 3) → 3×3+1×3=12 ≥ 5. ⚠️ 2차 패스가 남긴 관측이 이번에도 재현됐다: 점수식은 **검증 인프라 추가**를 행위 결함과 같은 무게로 세므로, 마이그레이션의 동작이 1차 이후 한 글자도 안 바뀌었는데도 세 패스 연속 `true`가 나온다. 다만 이번 패스가 고친 술어 구멍은 실제 동작 결함이었고(옛 술어는 드리프트를 놓쳤다), 남은 지적은 대부분 이 워크플로 밖에서만 닫을 수 있는 것들(CI 트리거·오케스트레이터 상태)로 수렴했다.

**검증 수행**: 새 검사 3건을 **일부러 깨서 red 확인 후 원복 green**(0027에 UPDATE 삽입 → ⑥·⑧ red / 사후조건 블록 제거 → ⑦ red) · 새 vitest 스캔도 **폴백 제거 → red, 원복 → green** · 술어 수정을 드리프트 재현으로 실측(옛 `f` vs 새 `t`, 실제 적용 시 psql ERROR로 중단) · `pytest tests/integration` 전체 **93건 통과** · `python3 scripts/check_migrations.py` **exit 0** · `npx tsc --noEmit` exit 0 · `npm run lint` 통과 · `npm test` **308건 통과** · `flutter analyze` No issues found. 상세는 `## Verification Evidence`의 3차 패스 절. 검증 컨테이너는 `docker rm -f`로 정리.

**잔여 리스크**: (1) **이 브랜치에서는 CI가 한 번도 돌지 않았다** — 마이그레이션 게이트(DW-661)뿐 아니라 `tests.yml`의 `api-db`·`web` 잡도 마찬가지라(DW-664), 이번에 만든 검사 15+3건이 초록인 근거는 여전히 로컬 실행이다. 이 워크플로는 push를 하지 않으므로 여기서 닫을 수 없다. (2) 0027은 **아직 운영 DB에 적용되지 않았다**(배포는 `docs/conventions.md` §9.4·CLAUDE.md B3에 따라 별도 승인 사항). (3) 마이그레이션 적용이 CI·원격 경로에서 원자적이지 않아, 실패 시 앞부분만 적용된 채 남는다(DW-665 — 파일 하나가 아니라 레포 관례의 공백이라 다음 마이그 스토리에서 정한다). (4) role의 **어휘를 강제하는 주체가 지금도 없다** — 신규 가입은 트리거가 buyer/seller로 계속 강제하므로 완화의 효용은 Story 14.2부터 드러난다. 그 사각지대는 테스트가 의도적으로 초록으로 못박아 두었다. (5) Story 14.2가 트리거를 바꾸는 순간 공용 픽스처의 role 단언이 깨진다(DW-663 — 14.2 인수조건에 심어야 한다).
