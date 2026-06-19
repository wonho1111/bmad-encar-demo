# Story 2.1: listings 스키마 + 소유권·status 가드(DB측)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want `listings` 테이블과 소유권·상태전환 규칙을 DB(RLS+CHECK)에 못박고 싶다,
so that 웹·앱 어느 클라이언트가 붙어도 권한·상태 무결성이 한 곳에서 보장된다.

## Acceptance Criteria

1. **(스키마 — 15필드 + 시스템 컬럼)** `0002_listings` 마이그레이션이 적용되면, 스키마 확인 시 **FR5 15필드** + `seller_id`·`status check(on_sale/sold)`·`embedding vector(768)`·타임스탬프(`created_at`·`updated_at`)가 존재한다. **사진 컬럼은 없다**(`photos`/Storage 미사용).
2. **(고정 목록 CHECK 강제)** 고정 목록 6필드(`manufacturer`·`body_type`·`color`·`fuel`·`transmission`·`region`)는 `CHECK`로 강제된다. 목록 밖 값을 넣으면 DB가 거부한다. (CHECK 목록값은 architecture.md 확정 표·`docs/conventions.md`·`web/src/lib/constants.ts`와 일치해야 한다.)
3. **(RLS 동거)** 소유권 RLS(FR6) + 판매완료 비노출 RLS(FR11)가 **같은 `0002_listings` 마이그레이션에 동거**해 함께 적용된다(별도 RLS 묶음 마이그레이션 대기 없음).
4. **(소유권 — 본인 매물만 변경)** 소유권 RLS가 적용되면, 판매자가 매물을 수정/삭제할 때 `auth.uid() = seller_id`인 본인 매물만 허용된다(FR6). 타인 매물 id로 수정/삭제 시 RLS로 차단(0행 영향)된다. INSERT 시에도 `seller_id`를 타인으로 위조할 수 없다.
5. **(판매완료 비노출 — 구매자 경로)** FR11 비노출 정책이 적용되면, 구매자(역할 buyer) 컨텍스트에서 `status='sold'` 매물은 SELECT로 노출되지 않는다. 판매자는 본인 매물을(sold 포함) 볼 수 있고, 관리자는 전체를 볼 수 있다(관리자 FR11 예외).
6. **(status 전환 가드)** status 전환 규칙(CHECK/정책)이 있을 때, `on_sale`↔`sold` 외 값으로 바꾸거나 타인 매물의 status를 바꾸려 하면 DB가 거부한다. (CHECK가 enum 값을, UPDATE RLS가 소유권을 막는다.)

> **범위 주의(반드시 준수):** 이 스토리는 **DB측 스키마 + RLS + 상태가드(0002_listings 마이그레이션 1개)** 까지다. **매물 등록 폼/화면(2-2)·본인매물 관리 UI(2-3)·구매완료 버튼(2-4)·샘플 시드(2-5)는 후행 스토리** 소관이다. 이 스토리에서 web/app 화면 코드는 만들지 않는다. `embedding` 컬럼은 **선언만**(NULL 허용) 하고, 임베딩 적재(backfill)와 HNSW 인덱스는 **Epic 4(Story 4.2)** 소관이라 여기서 만들지 않는다. `seed.sql`의 샘플 매물도 2-5 소관(건드리지 않음).

## Tasks / Subtasks

- [x] **Task 1: 스키마 사전 점검 (AC: 1, 3 기반)**
  - [x] 1.1 `list_migrations`(0001만 적용)·`list_extensions`(vector 0.8.0 public 설치 확인) — 멱등성 위해 `create extension if not exists vector;`를 선두에 둠.
  - [x] 1.2 `list_tables`·`pg_proc` 조회로 `profiles`·`is_admin()`(SECURITY DEFINER) 존재 확인. 0001 미수정.
- [x] **Task 2: `0002_listings.sql` 마이그레이션 작성 — 테이블 (AC: 1, 2)**
  - [x] 2.1 `supabase/migrations/0002_listings.sql` 신규 작성(0001 스타일 한국어 헤더).
  - [x] 2.2 architecture.md 확정 컬럼 정의 그대로 작성(15필드 + 시스템 컬럼, CHECK 목록 한 글자도 안 바꿈, 단위 주석 유지). `list_tables`로 모든 CHECK 일치 확인.
  - [x] 2.3 `seller_id … references public.profiles(id) on delete cascade` — 정리 단계에서 판매자 삭제 시 매물 cascade 삭제 입증.
  - [x] 2.4 `set_updated_at()` plpgsql 트리거(`before update`) + RPC EXECUTE revoke. 검증에서 `updated_at_bumped:true` 확인.
  - [x] 2.5 테이블·핵심 컬럼 `comment on` 한국어.
- [x] **Task 3: 소유권 + FR11 비노출 RLS (AC: 3, 4, 5) — 같은 마이그레이션에 동거**
  - [x] 3.1 `enable row level security` (list_tables `rls_enabled:true` 확인).
  - [x] 3.2 SELECT 정책 3종(on_sale·own·admin) — `is_admin()` 재사용. 임퍼소네이션: buyer(sold 0/on_sale 1)·seller_A(전부 2, sold 1)·admin(전부 2) 확인.
  - [x] 3.3 INSERT `listings_insert_own`(with check) — 타인 명의 INSERT `insufficient_privilege` 차단 확인.
  - [x] 3.4 UPDATE `listings_update_own`(using+with check) — 타인 매물 UPDATE 0행 확인.
  - [x] 3.5 DELETE `listings_delete_own` — 타인 매물 DELETE 0행 확인.
- [x] **Task 4: status 전환 가드 (AC: 6)**
  - [x] 4.1 enum 가드 = CHECK(`on_sale/sold`) — `status='reserved'` UPDATE `check_violation` 차단 확인.
  - [x] 4.2 소유권 전환 가드 = UPDATE RLS — 타인 status 변경 0행 확인.
  - [x] 4.3 재오픈(sold→on_sale) 양방향 허용으로 해석, 별도 트리거 미생성(과설계 금지). Completion Notes에 명시.
- [x] **Task 5: 마이그레이션 적용 + 검증 (AC: 전체)**
  - [x] 5.1 `apply_migration(name=0002_listings)` `{"success":true}`.
  - [x] 5.2 `list_tables(verbose)` 컬럼·CHECK·FK·RLS 확인 + `list_migrations`에 0002_listings 등장.
  - [x] 5.3 임퍼소네이션 검증 전 시나리오 PASS(위 Task 3·4 참조). `set local role authenticated` + `request.jwt.claims` 패턴(1-4 재사용, sub는 리터럴 uuid).
  - [x] 5.4 임시 판매자 2계정 cascade 삭제 → `test_users_left=0, listings_left=0, admin_preserved=1, profiles_left=3` 교차검증. admin@test.com 보존.
  - [x] 5.5 `constants.ts`의 `LISTING_STATUS`/`UNITS`가 CHECK 값과 일치 재확인(변경 불필요).
- [x] **Task 6: 보고 (AC: 전체)**
  - [x] 6.1 결과 사실대로 Completion Notes 기록(적용·RLS 검증·재오픈 판단·정리·advisor).

## Dev Notes

### ⚠️ 핵심 — RLS를 "역할·소유권 결합 SELECT"로 설계하는 이유 (가장 헷갈리는 부분)
- `listings`는 profiles와 달리 **세 종류 시청자**가 있다: 구매자(판매중만), 판매자(본인 것 전부), 관리자(전부). RLS의 여러 PERMISSIVE 정책은 **OR**로 합쳐지므로, 위 세 SELECT 정책을 따로 두면 자동으로 "판매중 ∪ 본인 ∪ (관리자면 전체)"가 된다.
- **FR11(판매완료 비노출)의 강제 지점이 바로 `listings_select_on_sale`의 `status='on_sale'` 조건**이다. 구매자는 본인 매물도 관리자도 아니므로 `on_sale`만 통과 → sold가 어느 경로(목록·필터·상세)로도 안 보임. 이게 "단일 규칙"(FR11)의 DB측 구현이다. [Source: architecture.md#Authentication-&-Security(판매완료 비노출 FR11), docs/conventions.md §6]
- **흔한 실수 방지:** 단일 `using (status='on_sale' or auth.uid()=seller_id or is_admin())` 한 정책으로 합쳐도 동작하지만, **정책을 분리**하면 의도가 명확하고 후속 스토리(2-3/3-3/Epic6)가 개별 정책을 참조·검증하기 쉽다. 분리 권장. 어느 쪽이든 **결과가 같음을 5.3에서 임퍼소네이션으로 증명**할 것.

### status 전환 가드 — CHECK + RLS 2중, 트리거는 만들지 않음
- "**그 외 값**"(AC6) = enum 위반 → **테이블 CHECK**(`status in ('on_sale','sold')`)가 INSERT·UPDATE 양쪽에서 막는다(추가 장치 불필요).
- "**타인 매물 전환**"(AC6) = 소유권 위반 → **UPDATE RLS**(`using`+`with check` 둘 다 `auth.uid()=seller_id`)가 막는다. `with check`를 빼면 "내 매물을 남에게 넘기는" 변경(seller_id 재지정)을 못 막으니 **반드시 둘 다** 건다.
- **재오픈(sold→on_sale):** AC가 "`on_sale`↔`sold`"라 양방향 허용으로 본다 → status 전이를 강제하는 **별도 트리거는 만들지 않는다**(과설계 금지, CLAUDE.md §4 "초기 DB 단순하게"). 이 해석을 Completion Notes에 명시. 2-4(구매완료)는 단순히 `update … set status='sold'`만 하면 되고 본 RLS·CHECK로 충분히 보호된다.

### 0001에서 그대로 가져올 패턴 (재발명 금지)
- **`is_admin()` 함수 재사용:** 0001에 SECURITY DEFINER로 이미 존재(RLS 자기참조 재귀 회피용). listings 관리자 SELECT 정책에서 `public.is_admin()` 그대로 호출. **새 함수·새 admin 판별 로직 만들지 말 것.** [Source: supabase/migrations/0001_profiles.sql:57-68]
- **정책 `to authenticated` 한정:** 0001처럼 모든 정책을 `to authenticated`로 → 비로그인(anon)은 평가 자체를 안 함. [Source: 0001_profiles.sql:77-81]
- **SECURITY DEFINER/트리거 함수 RPC 노출 차단:** 0001은 `handle_new_user`/`is_admin`의 EXECUTE를 public·anon·authenticated에서 revoke했다. `updated_at` 트리거 함수도 동일하게 `revoke execute … from public, anon, authenticated`(트리거 실행은 영향 없음). [Source: 0001_profiles.sql:89-91]
- **헤더 주석·`comment on` 한국어:** 0001과 같은 형식(파일 상단 "이 마이그레이션이 하는 일" 목록 + 섹션 구분선). [Source: 0001_profiles.sql:1-9]

### 컬럼 정의는 architecture.md 확정본을 그대로 (drift 금지)
- architecture.md line 150~184에 **확정된 `create table listings` 블록**이 있다. 컬럼명·타입·CHECK 목록값·단위 주석을 **그대로 옮긴다.** 이 값들은 UI 드롭다운·Text-to-SQL 화이트리스트·시드·질의셋과 전 구간 일치해야 하는 단일 출처다. [Source: architecture.md(line 145~189)]
- `embedding vector(768)` — `EMBEDDING_DIM`(constants.ts)·`GEMINI_EMBEDDING_DIM`(api)과 같은 768. NULL 허용(시드는 NULL로 들어오고 Epic 4에서 backfill). **HNSW 인덱스는 여기서 만들지 않음**(4.2 소관 — 인덱스 없이도 컬럼 선언은 유효). [Source: architecture.md#Data-Architecture(line 193), epics.md#Story-4.2, docs/conventions.md §1]
- `options text[]`·`description` — 코퍼스① 임베딩 대상(Epic 4). 지금은 컬럼만.

### 역할 게이트 위치 (INSERT 시 seller만 등록?)
- AC4는 "본인 매물만"(소유권)까지만 요구한다. "seller 역할만 등록 가능"은 **DB CHECK가 아니라 앱/화면 책임**으로 둔다(2-2에서 판매자 전용 라우트·가드). 이유: profiles.role을 INSERT 정책에서 서브쿼리하면 0001의 재귀 회피 패턴(is_admin SECURITY DEFINER)처럼 또 헬퍼가 필요해 복잡도↑. **지금은 소유권만 DB에서 강제**(단순 우선, CLAUDE.md §4). 필요 시 후속 스토리에서 `is_seller()` 헬퍼 추가 검토. 이 결정을 Completion Notes에 적는다.

### 마이그레이션 적용·검증 표준 (DB 스토리 = HTTP/SQL 검증)
- 이 스토리는 화면이 없어 Playwright 대상이 아니다 → **Supabase MCP로 실제 적용 + `execute_sql` 임퍼소네이션으로 RLS 자체 검증**(1-4에서 확립한 방식). [Source: bmad-encar-demo/CLAUDE.md#6(백엔드는 HTTP/SQL 검증), 1-4 Debug Log(RLS 임퍼소네이션)]
- **임퍼소네이션 패턴(1-4 재사용):** 트랜잭션 안에서 `set local role authenticated;` + `set local request.jwt.claims = '{"sub":"<uuid>","role":"authenticated"}';` 후 SELECT/UPDATE → 해당 사용자 컨텍스트로 RLS 평가. `auth.uid()`는 jwt claims의 sub를 읽는다. [Source: 1-4 Debug Log(AC2 RLS 임퍼소네이션)]
- **Supabase MCP 미연결/적용 불가 시:** 그 사실을 escalate 사유로 남기고 **마이그레이션 파일 작성까지는 완료**(파일이 단일 출처라 보존 가치 있음). (task 지시 4항)
- **현재 DB 상태:** 0001만 적용, profiles에 행 3개(시드 admin 등) 존재 — listings는 신규라 충돌 없음. pgvector 설치 완료. [확인: list_migrations·list_extensions·list_tables]

### 이전 스토리(1.x) 학습 — 그대로 적용
- **테스트 계정/데이터 라이프사이클:** 검증용으로 만든 listings·임시 계정은 검증 후 cascade 삭제 + `count(*)` 0 교차검증. **시드 admin(admin@test.com)은 보존**. [Source: 1-4 Debug Log(정리)]
- **마이그레이션 멱등 고려:** `create extension if not exists vector;` 선두. (테이블·정책 자체는 0002가 처음 만드는 것이라 `if not exists` 불필요하나, 재적용 안전을 위해 정책명 충돌만 주의.)
- **0001 수정 금지·새 마이그레이션으로만 확장**(CLAUDE.md §4 마이그레이션 추적).

### 코드 컨벤션 (이 스토리 적용분)
- 통신선·DB 컬럼 `snake_case`(`seller_id`·`body_type`·`accident_free`). 단위 km·원·cc 주석 유지. [Source: docs/conventions.md §2·§3, architecture.md#Naming-Patterns]
- 사용자 노출 메시지는 한국어(이 스토리는 DB라 직접 노출 메시지는 없음 — CHECK 위반 시 앱이 한국어로 변환하는 건 2-2). 마이그레이션 주석은 한국어.
- 마이그레이션 파일명 규약: `000N_<엔티티>.sql`(0001_profiles 다음 `0002_listings`). [Source: architecture.md(line 330)]

### Project Structure Notes
- **신규 파일:** `supabase/migrations/0002_listings.sql`.
- **수정 파일:** `_bmad-output/implementation-artifacts/sprint-status.yaml`(상태 전이 2-1 + epic-2). web/app/api 소스 미변경.
- **건드리지 않음:** `supabase/migrations/0001_profiles.sql`, `supabase/seed.sql`(샘플 매물은 2-5), `web/src/lib/constants.ts`(이미 일치 — 재확인만).
- 아키텍처 구조도 정합: `supabase/migrations/0002_listings.sql`(line 330) "FR5 15필드(사진 제외) + status + embedding vector(768)". [Source: architecture.md(line 325~333)]

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1 (AC 3종·범위)]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-2 (기반 흡수: 0002_listings·소유권·status 가드 DB측 선치)]
- [Source: _bmad-output/planning-artifacts/architecture.md (line 145~189: listings 확정 컬럼 정의·CHECK 목록·단위)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication-&-Security (RLS 배치 원칙·FR11 비노출·소유권)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data-Architecture (line 193: HNSW는 별도, 768 고정)]
- [Source: docs/conventions.md §1(임베딩 768)·§2(snake_case)·§3(단위)·§6(FR11 비노출)]
- [Source: supabase/migrations/0001_profiles.sql (is_admin·to authenticated·RPC revoke·헤더 주석 패턴 — 재사용)]
- [Source: web/src/lib/constants.ts (LISTING_STATUS·UNITS — CHECK 값 정합)]
- [Source: _bmad-output/implementation-artifacts/1-4-역할별-접근제어-profiles-rls.md (RLS 임퍼소네이션 검증·테스트 계정 정리)]
- [Source: bmad-encar-demo/CLAUDE.md (§4 DB 단순·마이그레이션 추적 / §6 백엔드 HTTP·SQL 검증)]

### 사용자 직접 처리 항목 (왜 / 어디서)
- **(확인만) Supabase 프로젝트 연결·MCP** — 마이그레이션 실제 적용에 필요 / 이미 연결됨(0001 적용 이력 확인). 연결 끊기면 dev가 escalate.
- **(이미 완료)** pgvector 확장 — `embedding vector(768)`에 필요 / Supabase에 0.8.0 설치 확인됨(추가 작업 없음).
- **(후행 안내)** 샘플 매물·임베딩 backfill·HNSW 인덱스는 본 스토리 범위 밖(2-5·Epic 4).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (create-story)

### Debug Log References

- `apply_migration(0002_listings)` → `{"success":true}`. `list_migrations`에 `0002_listings`(20260619205810) 등장.
- `list_tables(verbose)`: `public.listings` `rls_enabled:true`, 15필드+시스템컬럼, `embedding`=vector(nullable), 사진 컬럼 없음, FK `listings_seller_id_fkey → profiles.id`. 6개 CHECK 목록값이 마이그레이션 정의와 정확히 일치(manufacturer/body_type/color/fuel/transmission/region) + status/year/price/mileage/displacement/seats 범위 CHECK.
- `pg_policies`: 6개 정책 확인 — select(on_sale/own/admin), insert_own(with check), update_own(using+with check), delete_own.
- RLS 임퍼소네이션(`set local role authenticated` + `request.jwt.claims` sub=리터럴 uuid):
  - SELECT 가시성: buyer 컨텍스트 `total=1, on_sale=1, sold=0`(FR11 비노출) · seller_A `total=2, own_sold=1`(본인 sold 보임) · admin `total=2, sold=1`(전체, FR11 예외).
  - 소유권: 판매자 B가 A 매물 UPDATE/DELETE → `rows_updated_by_b=0, rows_deleted_by_b=0`. A가 B 명의로 INSERT → `insufficient_privilege`(with check) 차단.
  - status 가드: `status='reserved'` UPDATE → `check_violation` 차단. body_type='세단'(목록밖) INSERT → `check_violation` 차단.
  - 본인 on_sale→sold 전환 정상 + `updated_at_bumped:true`(트리거 동작).
- 정리: 임시 판매자 2계정 cascade 삭제 → `test_users_left=0, listings_left=0`(매물도 FK cascade 삭제 입증), `admin_preserved=1, profiles_left=3`.
- `get_advisors(security)`: listings 관련 신규 경고 없음(RLS 누락 0). 잔존 3건은 본 스토리 범위 밖 — ① vector 확장 public 설치(Supabase 기본·기존 상태) ② is_admin SECURITY DEFINER 실행가능(0001 의도) ③ leaked password protection(Auth 콘솔 설정). 본 스토리 추가 `set_updated_at`은 EXECUTE revoke로 경고 없음.

### Completion Notes List

- **AC1 충족**: `0002_listings` 적용 후 listings에 FR5 15필드 + `seller_id`·`status check(on_sale/sold)`·`embedding vector(768)`·`created_at`·`updated_at` 존재, 사진 컬럼 없음. (`list_tables` 확인)
- **AC2 충족**: 고정 목록 6필드 CHECK 강제 — body_type='세단' 등 목록 밖 값 INSERT가 `check_violation`으로 거부됨. CHECK 목록값은 architecture.md·conventions.md·constants.ts와 동일.
- **AC3 충족**: 소유권 RLS(FR6) + FR11 비노출 RLS가 **같은 0002_listings에 동거**(별도 RLS 묶음 없음). `rls_enabled:true`.
- **AC4 충족**: `auth.uid()=seller_id` 본인 매물만 변경 — 타인 UPDATE/DELETE 0행, 타인 명의 INSERT `insufficient_privilege` 차단. (cascade 삭제도 정리 단계에서 입증)
- **AC5 충족**: 구매자 컨텍스트에서 `sold` 비노출(sold=0), 판매자는 본인 sold 조회, 관리자는 전체 조회(FR11 예외).
- **AC6 충족**: `on_sale`↔`sold` 외 값은 CHECK가, 타인 매물 전환은 UPDATE RLS가 거부.
- **설계 결정 1 — 재오픈(sold→on_sale):** AC가 "on_sale↔sold"라 **양방향 허용**으로 해석 → status 전이 강제 트리거를 만들지 않음(과설계 금지, CLAUDE.md §4). 2-4 구매완료는 `update set status='sold'`만으로 충분하며 본 RLS/CHECK가 보호.
- **설계 결정 2 — 역할 게이트 위치:** "seller만 등록"은 DB가 아닌 앱/프록시 책임(2-2). DB는 소유권(seller_id 위조 차단)만 강제 — profiles.role을 INSERT 정책에서 서브쿼리하면 또 SECURITY DEFINER 헬퍼가 필요해 복잡도↑. 단순 우선.
- **설계 결정 3 — updated_at 트리거:** moddatetime 확장 대신 plpgsql `set_updated_at()`로 구현(0001 함수 스타일 일관, 확장 의존 최소화), RPC 노출 차단.
- **재발명 금지 준수**: 0001의 `is_admin()`·`to authenticated` 한정·RPC revoke·헤더주석 패턴 그대로 재사용. 새 admin 판별 함수·새 마이그레이션 외 변경 없음.
- **범위 준수**: HNSW 인덱스·임베딩 backfill(Epic 4)·샘플 시드(2-5)·매물 폼/화면(2-2~2-4) 미구현. web/app/api 소스 미변경. seed.sql 미변경.
- **검증 방식**: 화면이 없는 DB 스토리라 Playwright 대상 아님 → Supabase MCP 실제 적용 + execute_sql 임퍼소네이션 자체 검증(1-4 방식). 임시 계정·데이터는 검증 후 cascade 삭제·교차검증.
- **escalate 없음**: Supabase MCP 연결 정상, 마이그레이션 적용 성공. 키/환경변수 누락 없음.

### Code Review (2026-06-20, bmad-code-review + 3레이어 자체검토)

- **리뷰 방식**: bmad-code-review 스킬 + 3개 병렬 서브에이전트(Blind Hunter·Edge Case Hunter·Acceptance Auditor). 전 레이어 정상 완료(실패 레이어 없음). Acceptance Auditor: AC1~6 전부 COMPLIANT, CHECK 목록값이 architecture.md 단일출처와 바이트 단위 일치 확인.
- **[Patch] 적용 1건 — created_at 불변 보장**: `set_updated_at()` 트리거가 UPDATE 시 `new.created_at := old.created_at`로 기존 값을 되돌리도록 강화. 소유자가 UPDATE에 created_at을 끼워 넣어 '최신 등록'처럼 위장(등록일 정렬·노출 신뢰성 훼손)하는 것을 차단. `create or replace`라 멱등 → 파일·라이브 DB(`0002b_listings_created_at_immutable`) 동기화. 검증: created_at 위조 시도 `forgery_succeeded=false / created_at_preserved=true`, 트랜잭션 롤백으로 테스트행 정리, security advisor 신규 경고 0.
- **[Decision] escalate 2건(자동 미적용)**:
  - **price/displacement/mileage `int` 오버플로**: `int` 상한 약 21.4억(원). 고가 차량 가격이 상한에 근접·초과할 수 있어 `bigint`가 안전하나, architecture.md 확정 정의가 `int`라 drift-freeze 원칙과 충돌 → 타입 변경은 사용자 결정 필요.
  - **마이그레이션 비멱등 DDL**: table/trigger/policy에 `if not exists`/`drop if exists` 없음(0001도 동일 패턴). 재적용 시 실패. 현 운영엔 무해하나 마이그레이션 재실행 안전성을 원하면 정책 결정 필요.
- **defer(후행 에픽)**: embedding 클라이언트 쓰기 차단(Epic 4) · 정지(suspended) 사용자/관리자 쓰기·읽기 차단(FR22/Epic 6) · 관리자 매물 모더레이션 정책(FR23/Epic 6 `0005_admin_policies`) · CHECK 목록값의 constants.ts 미러링(2-2 UI).
- **dismiss**: sold→on_sale 재오픈 허용(AC6 명시 의도) · anon 비노출(0001 `to authenticated` 설계) · seller_id 노출(Epic 3 문의 필요) · options/description 자유텍스트(임베딩 코퍼스) · year 2027 상한(architecture.md 명시·연도경과 시 마이그레이션 상향).
- **미해결 High/심각 지적: 없음**(escalate 2건은 spec/정책 결정 사항).

### File List

- `supabase/migrations/0002_listings.sql` — 신규 (listings 테이블 + 6개 RLS 정책 + updated_at 트리거 + status/소유권 가드)
- `_bmad-output/implementation-artifacts/2-1-listings-스키마-소유권-status-가드.md` — 수정 (체크박스·Dev Agent Record·Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 수정 (epic-2 in-progress, 2-1 상태 전이)

## Change Log

- 2026-06-20: Story 2.1 구현 — `0002_listings` 마이그레이션(listings 15필드+시스템컬럼, 사진 제외) + 고정목록 6필드 CHECK + status CHECK(on_sale/sold) + 소유권 RLS(FR6)·판매완료 비노출 RLS(FR11) 동거 + updated_at 트리거. Supabase MCP로 실제 적용·임퍼소네이션 검증(AC1~6 전부 PASS: buyer는 sold 비노출/seller는 본인 sold 조회/admin 전체, 타인 UPDATE·DELETE·INSERT 차단, 목록밖 status·body_type CHECK 차단, updated_at 트리거). 임시계정 cascade 정리·교차검증, security advisor 신규 경고 0. Status → review. (dev-story)
- 2026-06-20: Code review(bmad-code-review + 3레이어) — Acceptance Auditor AC1~6 COMPLIANT. [Patch] created_at 불변 보장(`set_updated_at` 트리거 강화, 위조 차단 검증). [Decision] price `int` 오버플로·마이그레이션 비멱등 2건 escalate. defer/dismiss는 Code Review 섹션 참조. Status → done. (code-review)
