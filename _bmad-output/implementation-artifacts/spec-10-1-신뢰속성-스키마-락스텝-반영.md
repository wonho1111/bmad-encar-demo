---
title: 'Story 10.1 — 신뢰속성 스키마 + 락스텝 반영'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '14f84e0'
final_revision: '04e6502'  # 후속 리뷰 패스 2 등재 커밋(패치 커밋 a1283a3, 스토리 구현 전량 e07b2b2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-10-context.md'
  - '{project-root}/docs/tech-debt.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 신뢰속성(무사고·1인소유·비흡연)은 `docs/conventions.md` §4의 ListingCard 계약과 web/api/app 세 클라이언트 모델에 **필드 자리만 선점돼 있고**(Story 8.3), 정작 `listings` 테이블에 컬럼이 없어 **값이 흐르는 경로가 0**이다. 같은 이유로 `fuel`은 DB·필터엔 있는데 카드 계약에만 빠져 카드 meta가 AC 문구(`주행·연료·지역`)와 다르게 렌더된다(대장 #67).

**Approach:** 컬럼 3개를 nullable로 **더하는(additive)** 마이그레이션 1장을 넣고, 그 값이 DB→api→web/app 카드까지 실제로 흐르도록 §4.1 락스텝 지점을 한 번에 갱신한다. `fuel`을 같은 락스텝에 태워 #67을 닫는다. 렌더(뱃지·면책 라벨)는 이 스토리가 아니라 10.2가 한다 — 여기서는 **값이 도달하는 것**까지다.

## Boundaries & Constraints

**Always:**
- 마이그레이션은 **additive·forward-only**. 기존 `accident_free`(NOT NULL bool) 컬럼과 값은 **드롭·변경 금지**. 신규 3컬럼은 **전부 nullable**이고 기존 100건은 **NULL 유지 — backfill 하지 않는다**.
- `accident_status`는 native enum이 아니라 **`text + check (accident_status in ('무사고','단순교환','사고'))`** — 기존 `body_type`/`color`/`region` 관례와 일치.
- 파일명은 `supabase/migrations/0017_listings_trust_attributes.sql`. **번호는 max+1만**(알파벳 접미사 금지, 대장 #101). self-contained: 테이블·RLS·GRANT를 다시 만들지 않고 컬럼만 더한다. RLS는 **기존 listings 정책을 상속**하며 새 정책을 만들지 않는다.
- `docs/conventions.md`가 계약 정본이다 — **코드보다 문서를 먼저 고친다**(규칙1).
- `api/app/graph/listing_cards.py`의 `SELECT_COLUMNS`와 `rows_to_cards()`의 **위치 인덱스 매핑은 1:1로 유지**한다(순서가 어긋나면 카드 값이 서로 뒤바뀐다).
- 카드 meta는 **한 줄 가로 유지**. 공간 부족은 `truncate`로만 흡수한다 — 세로로 접지 않는다(project-context 규칙13/D5).
- `ALLOWED_COLUMNS`에는 **`listings` 컬럼만** 더한다. `storage_path` 등 다른 테이블 컬럼은 절대 넣지 않는다(conventions §4.1 경고 — FR11이 그 경로에서 무너진다).

**Block If:**
- 마이그레이션 적용 후 기존 행의 `accident_free` 값이 하나라도 달라지면 → HALT.
- `SELECT_COLUMNS` 확장이 `rows_to_cards()` 위치 매핑과 어긋나 기존 카드 필드가 뒤바뀌면 → HALT.

**Never:**
- 신뢰 뱃지·면책 라벨 **렌더는 하지 않는다**(10.2 범위). 카드의 신뢰속성 슬롯은 값이 흘러도 비어 있다.
- 판매자가 신뢰속성을 **입력하는 폼 UI를 만들지 않는다**(아래 Design Notes의 "쓰기 경로 부재" 참조 — 대장에 등재하고 넘긴다).
- `accident_free` → `accident_status` **backfill 금지**. 옵션(`options`) 구조는 건드리지 않는다(10.3 범위).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 정상 3값 | `accident_status='단순교환'` INSERT | 저장 성공 | 에러 없음 |
| 도메인 밖 값 | `accident_status='외판교환'` INSERT | **CHECK 위반으로 거부** | Postgres `23514` |
| 미입력 | `accident_status` 생략 | `NULL` 저장(제3상태) | 에러 없음 |
| 기존 100건 | 마이그 적용 직후 조회 | 신규 3컬럼 전부 `NULL`, `accident_free` 값 그대로 | 에러 없음 |
| bool 3상태 | `is_single_owner=null` | 소비처가 `false`로 단정하지 않음(미상) | 에러 없음 |
| api 카드 매핑 | 신규 컬럼이 NULL인 행 | `ListingCard.accident_status=None`, `fuel`은 실제 값 | 에러 없음 |
| app 파싱 | `accident_status`가 비-String | `null`로 강등(행은 버리지 않음) | 에러 없음 |

</intent-contract>

## Code Map

- `supabase/migrations/0002_listings.sql` -- 기존 컬럼·CHECK 관례의 원천(`accident_free`는 55행 근처). 신규 마이그의 문체·주석 밀도를 여기와 `0015_*.sql`에 맞춘다.
- `docs/conventions.md` §4 / §4.1 -- ListingCard 계약 정본. 신규 필드 표(`accident_status`·`is_single_owner`·`is_non_smoker`)가 이미 있고 "값 채움" 열이 `Epic 10`이다. `fuel`은 **표에 없다 — 추가 대상**.
- `api/app/db/sql_guard.py:33-38` -- `ALLOWED_COLUMNS`. `fuel`은 이미 있고 신뢰속성 3개가 없다.
- `api/app/graph/listing_cards.py:29,32-50` -- `SELECT_COLUMNS`(7컬럼 문자열) + `rows_to_cards()`의 **위치 인덱스 0~6** 매핑. `sql_rag_node.py`·`doc_rag_node.py`가 이 상수를 import 하므로 여기만 고치면 두 경로가 함께 따라온다.
- `api/app/schemas/ai.py:60-84` -- `ListingCard`. 신뢰속성 3필드는 **이미 nullable로 존재**(`Literal["무사고","단순교환","사고"] | None`). `fuel`만 없다.
- `api/app/graph/sql_rag_node.py:32-74` -- `_SYSTEM_PROMPT`의 `[스키마: listings 테이블]` 블록. `accident_free`만 있고 신뢰속성 3개가 없다.
- `api/tests/test_sql_guard.py:233,239-247` -- `storage_path` 거부·`ALLOWED_TABLES` 정확 고정 테스트. `ALLOWED_COLUMNS`를 정확히 고정하는 테스트는 **없다**.
- `web/src/components/listings/ListingCard.tsx:13-29,50-57` -- `ListingCardData`(신뢰속성 3필드 이미 존재, `fuel` 없음) + meta 줄(현재 `주행 · 지역 · 판매자`, 43-44행에 신뢰속성 슬롯 주석).
- `web/src/app/page.tsx:59` · `web/src/app/(user)/search/page.tsx:102` -- 목록 `.select(...)` 문자열 2곳. 둘 다 `fuel`·신뢰속성 미포함.
- `web/src/lib/api/aiSearch.ts:120-123,161-173` -- AI wire 타입 + `isValidListing`(필수 7필드만 검증, 신규 nullable은 검증 안 함 — 그대로 둔다).
- `app/lib/features/listings/listing.dart:20-113` -- `ListingCardData`(신뢰속성 3필드 이미 존재·`fromMap` 108-110행에서 이미 파싱, `fuel` 없음). 74-112행 `fromMap`의 "핵심 7필드는 strict, 이후 필드는 nullable 강등" 패턴을 따른다.
- `app/lib/features/listings/listings_repository.dart:38-40` -- `fetchListings`의 카드용 `.select(...)`. (69-73·126-130행의 상세용 select는 **건드리지 않는다** — 상세는 10.2 이후 범위.)
- `app/lib/features/ai_search/ai_search_api.dart:108-124` -- `/ai/search` 응답도 **같은** `ListingCardData.fromMap`을 쓴다(별도 파서 없음).
- `app/test/listing_model_test.dart:6-60` -- `ListingCardData.fromMap` 테스트 그룹. 신규 필드 단언이 **하나도 없다**.
- `scripts/check_migrations.py` -- 마이그 게이트(정적 3검사 + 도커 동적 검사). 로컬 Supabase 스택이 이미 떠 있다(`supabase_db_bmad-encar-demo`, 포트 55322).
- `docs/tech-debt.md:857-862` -- #67(카드 meta 연료 누락, 📅 예약: Story 10.1). 이 스토리가 닫는다.

## Tasks & Acceptance

**Execution:**
- `docs/conventions.md` -- §4 ListingCard 신규 필드 표에 `fuel | string\|null | Epic 10 (10.1)` 행을 추가하고, 신뢰속성 3필드의 "값 채움"을 `Epic 10 (10.1 컬럼 생성)`으로 구체화 -- 계약 정본을 코드보다 먼저 고친다(규칙1).
- `supabase/migrations/0017_listings_trust_attributes.sql` -- 신규 파일. `alter table public.listings add column ...` 3건(nullable) + `accident_status` CHECK + 각 컬럼 `comment on column` -- 값이 흐를 그릇을 만든다. 헤더 주석에 **왜 backfill 하지 않는지**(NULL=미입력 제3상태)와 **왜 `accident_free`를 남기는지**(additive, 소비처 다수)를 `0015_*.sql` 문체로 적는다.
- `api/app/db/sql_guard.py` -- `ALLOWED_COLUMNS`에 `accident_status`·`is_single_owner`·`is_non_smoker` 추가 -- LLM SQL이 신뢰속성으로 필터할 수 있게. `listings` 밖 컬럼은 넣지 않는다.
- `api/app/graph/listing_cards.py` -- `SELECT_COLUMNS`에 `fuel, accident_status, is_single_owner, is_non_smoker`를 **끝에 순서대로** 덧붙이고 `rows_to_cards()`에 인덱스 7~10 읽기를 추가 -- 상수와 위치 매핑을 1:1로 유지한다.
- `api/app/schemas/ai.py` -- `ListingCard`에 `fuel: str | None = None` 추가 -- #67이 요구한 계약 필드.
- `api/app/graph/sql_rag_node.py` -- `_SYSTEM_PROMPT` 스키마 블록에 `accident_status ∈ (무사고,단순교환,사고)`·`is_single_owner`·`is_non_smoker`(bool, nullable)를 추가하고, **"이 3컬럼은 대부분 NULL(미입력)이므로 '무사고' 조건은 `accident_free = true`를 쓴다"**는 지시문을 함께 넣는다 -- 프롬프트만 늘리면 LLM이 전부 NULL인 컬럼으로 필터해 0건을 내는 회귀가 생긴다.
- `api/tests/test_sql_guard.py` -- `ALLOWED_COLUMNS`를 **정확 집합으로 고정**하는 테스트 추가(`test_allowed_tables_is_exactly_listings` 패턴) -- 지금은 아무 테스트도 이 집합을 보지 않아 조용히 넓어질 수 있다.
- `api/tests/test_listing_cards.py` -- `SELECT_COLUMNS` 컬럼 수와 `rows_to_cards()`가 읽는 인덱스 수가 일치하는지, 11튜플 입력이 신규 필드까지 매핑되는지 검증하는 테스트 추가 -- 위치 매핑 어긋남을 잡는다.
- `api/tests/test_sql_rag_node.py` -- `_SYSTEM_PROMPT`에 신뢰속성 3컬럼과 "무사고는 accident_free" 지시문이 모두 들어 있는지 단언 추가 -- 프롬프트 회귀 방지.
- `web/src/components/listings/ListingCard.tsx` -- `ListingCardData`에 `fuel?: string | null` 추가, meta 줄을 `주행 · 연료 · 지역`(+ 기존 `판매자` 조건부 유지)로 바꾸고 `fuel`이 없을 때는 그 마디를 통째로 생략 -- #67을 닫되 한 줄 가로 유지(D5).
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` -- 두 `.select(...)` 문자열에 `fuel, accident_status, is_single_owner, is_non_smoker` 추가 -- 값이 실제로 카드까지 온다.
- `app/lib/features/listings/listing.dart` -- `ListingCardData`에 `fuel` 필드 + 생성자 파라미터 + `fromMap`의 nullable 강등 파싱(`raw['fuel'] is String ? ... : null`) 추가 -- 핵심 7필드가 아니므로 행을 버리지 않는다.
- `app/lib/features/listings/listings_repository.dart` -- `fetchListings`의 select 문자열에 4컬럼 추가 -- 상세용 select 2곳은 건드리지 않는다.
- `app/test/listing_model_test.dart` -- `ListingCardData.fromMap`에 대해 (a) 신규 4필드 정상 파싱, (b) `accident_status`가 비-String이면 `null`로 강등되고 **행은 살아남는지**, (c) `is_single_owner`가 없을 때 `false`가 아니라 `null`인지를 단언 -- bool 3상태 오독을 잡는다.
- `docs/tech-debt.md` -- #67을 `✅ 해소`로 닫고(무엇을 어떻게 닫았는지 실측 근거 1줄), **신규 항목 등재**: "신뢰속성 3컬럼에 값을 넣는 경로가 없다(쓰기 UI 부재)" — 위치·내용·실측·**트리거** 포함 -- 대장은 하나이고, 미룬 것은 재판단 시점과 함께 적는다(B8).

**Acceptance Criteria:**
- Given 마이그레이션 전 `listings` 100건, when `0017`을 빈 DB와 기존 DB 양쪽에 적용하면, then 신규 3컬럼이 nullable로 생기고 **기존 행은 전부 신규 컬럼 NULL·`accident_free` 값 무변**이다.
- Given 적용된 DB, when `accident_status`에 `'외판교환'`을 INSERT 하면, then **CHECK 위반(SQLSTATE 23514)으로 거부**되고, 값을 `'단순교환'`으로 되돌리면 성공한다. *(검사를 만든 게 아니라 잡는 걸 증명 — 아래 Verification에 red/green 실측을 기록한다.)*
- Given CHECK 제약, when 그 검사가 **안 보는 것**을 실측하면, then 최소 (a) 마이그 이전에 이미 들어간 행, (b) `NULL` 경로, (c) `accident_free`와의 논리적 모순(예: `accident_free=true` + `accident_status='사고'`)이 **전부 통과한다**는 사실을 마이그 파일 주석과 대장에 적는다.
- Given 신규 컬럼이 전부 NULL인 매물, when web 목록·검색과 app 목록을 조회하면, then 카드 meta에 **연료가 표시**되고 신뢰속성 필드는 `null`로 도달하되 **뱃지는 렌더되지 않는다**(10.2 이전이므로 슬롯은 빈 채).
- Given `/ai/search` 응답, when api가 카드를 만들면, then `fuel`이 채워지고 신뢰속성 3필드는 `None`이며, **기존 7필드 값이 서로 뒤바뀌지 않는다**.
- Given 대장, when 작업이 끝나면, then #67이 닫혀 있고 신규 "쓰기 경로 부재" 항목이 **트리거와 함께** 등재돼 있다.

## Spec Change Log

## Review Triage Log

### 2026-07-22 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 2: (high 0, medium 1, low 1)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - none

4개 리뷰 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 돌렸다. **이번 패스는 새 패치·스펙 결함 0건** — 코드가 앞선 두 패스(11+1 패치)로 이미 굳어 있음을 확인했다. 새로 표면화한 **선재(先在)·아키텍처성 결함 2건만 대장에 등재**했다(패치하지 않음).

- **defer 2건 → `docs/tech-debt.md`에 신규 등재**(동결된 `deferred-work.md`에는 쓰지 않는다 — 프로젝트 규칙 우선):
  - `#110` (medium) — `rows_to_cards`의 계약-외 강등이 `fuel`·신뢰속성 4슬롯뿐이라, 숫자 슬롯(`int(r[3..5])`)·필수 str 슬롯(`r[1]`/`r[2]`/`r[6]`)은 순서를 바꾼 폭-11 LLM SQL에 `int()` `ValueError` / pydantic `ValidationError`로 `/ai/search` 500. **이 7슬롯은 10.1 이전 7컬럼 시절부터 있던 선재 결함**이라 이 스토리가 만든 게 아니다 — 근본 해결은 sql_guard의 SELECT 순서 고정(B9, 보안 민감)이며 "컬럼 추가" 범위 밖. 트리거: sql_guard 순서 고정 도입 시 또는 `rows_to_cards` 컬럼 확장 시(10.2).
  - `#111` (low) — 클라이언트 `.select(...)` 3곳(web page/search·app repository)이 §4.1 락스텝 컬럼을 포함하는지 강제하는 자동 검사 부재 → **#67 형태의 조용한 재발 가능**. B9 위반. 화면 검증이 E2E-only(#106)라 즉시 패치 안 함. 트리거: 10.2에서 select 재수정 시 또는 실제 누락 회귀 발생 시.
- **reject 14건**(전부 low, 조치 없음). 대부분 (a) 이미 대장에 있거나(#108 쓰기 경로 부재, #109 anon GRANT 경계 = `search/page.tsx` 자동 검사 부재와 동일), (b) 앞선 패스에서 이미 기각됐거나(0017 `if not exists`가 CHECK 없는 반쯤 만든 컬럼 건너뜀 = 전진 마이그에 없는 시나리오, 프롬프트 substring-only 테스트 = eval 트랙, sprint-status.yaml 산문 증식, Flutter/web 렌더 테스트 부재 = 규칙12 E2E-only), (c) 의도 범위 밖이다(app `fromMap`은 I/O 매트릭스대로 **비-String→null** type-guard만 요구 — 도메인 정규화는 뱃지 렌더하는 10.2 몫이고 DB CHECK+api 상류 정규화로 실제 도달 불가; 상세 select는 Code Map이 "건드리지 않는다"고 명시한 10.2 범위; `accident_free`+`accident_status` 모순 허용은 AC #3이 문서화를 요구한 의도적 gap). defer·intent_gap·bad_spec은 위 2건 외 0건.
- **후속 리뷰 권고: `false`** — 이번 패스 패치 0건(high 0), 점수 3×0+1×0 = 0 < 5. 앞선 패스들의 high 패치는 이미 반영·검증됐고, 남은 것은 트리거가 달린 선재 부채 2건뿐이다.

### 2026-07-22 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 1, medium 0, low 0)
- defer: 0
- reject: 11: (high 0, medium 0, low 11)
- addressed_findings:
  - `[high]` `[patch]` FP1 — `rows_to_cards`가 `accident_status`(P2)만 도메인 강등하고 `fuel`(r[7])·`is_single_owner`(r[9])·`is_non_smoker`(r[10])는 raw로 통과시켜, 폭은 11로 맞지만 순서를 바꾼 LLM SQL이 이 슬롯에 타입 어긋난 값을 넣으면 `ListingCard(...)`가 pydantic `ValidationError`로 죽는다. 이건 `SqlGuardError`가 아니라 `sql_rag_node`의 `except SqlGuardError` 재생성 루프가 못 잡아 `/ai/search` 500 — P1/P2가 닫으려던 바로 그 실패 모드가 세 필드에 남아 있었다(리뷰어 4개 레인 전원 수렴, edge-case가 pydantic 2.13.4로 실증). P2 방어를 세 필드로 확장(`fuel`은 `isinstance(str)`, bool 2개는 `isinstance(bool)` — int 1/0 오인 없음) + 회귀 테스트. 실측: 방어 되돌리면 test **red**(`fuel`/`is_single_owner` ValidationError 2건) → 복원 후 **green**, api 202 passed.
  - reject 11건(전부 low, 조치 없음): (1) 프롬프트가 `단순교환`을 전부-NULL인 `accident_status`로 유도해 0건 — 쓰기 경로 부재라 어느 컬럼으로도 답이 없다(대장 #108이 이미 담음), (2) anon select 분기를 지키는 자동 검사 부재 + (3) anon이 신뢰속성을 못 읽어 Epic10 목표가 좁혀짐 — 둘 다 대장 #109가 트리거(10.2 착수)와 함께 이미 담음, (4) `column_count_mismatch` 메시지가 SELECT_COLUMNS(공개 계약, 비밀 아님)를 노출 — 2회 재시도 실패 후에만 표면화되고 기존 가드 메시지 문체와 일치, (5) web/app meta의 `.filter(Boolean)`이 빈 문자열 region을 생략 — region은 NOT NULL·17개 고정값이라 비현실적 상태, (6) 0017의 `if not exists`가 CHECK 없이 반쯤 만들어진 컬럼을 건너뛸 수 있음 — 전진·게이트 마이그에선 실재하지 않는 시나리오, (7) retry 테스트가 실패 경로만 증명·회복 경로 미증명 — retry 메커니즘은 이 스토리 이전부터 존재, (8) oversized 스토리 스코프 지적·(9) sprint-status.yaml 산문 증식·(10) final_revision 주석 문구·(11) Flutter fuel 위젯 테스트 부재(프로젝트 규칙12: 화면은 E2E-only) — 모두 이 스토리가 만든 결함이 아니거나 규칙과 부합.

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 7, low 3)
- defer: 1: (high 0, medium 1, low 0)
- reject: 3: (high 0, medium 1, low 2)
- addressed_findings:
  - `[high]` `[patch]` P1 — `rows_to_cards`가 인덱스 7~10을 무조건 읽는데 `sql_guard`는 SELECT 프로젝션을 `SELECT_COLUMNS`에 고정하지 않는다(파일 주석이 이미 인정하던 사실). LLM이 옛 7컬럼을 뽑으면 `IndexError`→`/ai/search` 500. 튜플 폭 불일치 시 `SqlGuardError('column_count_mismatch')`를 던져 기존 재생성 루프가 처리하도록 수정 + 단위/노드 테스트 추가. 실측: 7튜플 투입 → `SqlGuardError` 확인.
  - `[medium]` `[patch]` P2 — `accident_status`를 `Literal` 필드에 그대로 통과시켜, 도메인 밖 값 1건이 응답 전체를 ValidationError로 죽일 수 있었다. conventions §4 "계약-외 값 정규화"대로 `None` 강등 + 테스트.
  - `[medium]` `[patch]` P3 — 0017이 `add column`에 `if not exists`가 없어 재적용 시 42701. 기존 관례(0007/0008/0009)에 맞춰 수정, 재적용 무해함 실측.
  - `[medium]` `[patch]` P4 — 대장 #67을 "카드 meta=주행·연료·지역"으로 닫았는데 Flutter 카드는 여전히 `주행 · 지역`이었다(모델·쿼리에만 fuel 추가). `listing_card.dart` 위젯이 실제로 연료를 렌더하도록 수정 — 닫힘 주장과 화면을 일치시킴.
  - `[medium]` `[patch]` P5 — 프롬프트 규칙 7이 "무사고"만 `accident_free`로 유도하고 반대 방향("사고 있는 차")과 bool 2컬럼은 전 건 NULL인 컬럼으로 유도돼 반드시 0건이 되는 회귀. 양방향 지시 + bool 컬럼 필터 금지 지시 추가 + 프롬프트 단언 2건.
  - `[medium]` `[patch]` P6 — anon 경로에서 신뢰속성 3필드가 `null`이 아니라 `undefined`로 도착하는데 `.returns<ListingCardData[]>()`로 단언해 타입이 거짓이 됐다. 명시적 `null` 정규화.
  - `[medium]` `[patch]` P8 — 이번에 배운 락스텝 지점 2종(목록 select 문자열 3곳·anon GRANT §9.3(b) 승인)이 대장 산문에만 있었다. 정본 `conventions.md` §4.1로 승격(B8·B9).
  - `[medium]` `[patch]` P9 — `tests.yml`의 `api-db` 잡 `paths`에 `supabase/migrations/**`가 없어, 0017의 CHECK를 약화하는 변경이 그것을 검증하는 테스트를 트리거하지 않았다. paths 추가 + 낡은 잡 이름·주석 갱신.
  - `[low]` `[patch]` P7 — web 카드가 `fuel`을 타입 가드 없이 렌더(비-string이면 `[object Object]`). `typeof === 'string'` 가드.
  - `[low]` `[patch]` P10 — 통합 테스트가 seller id를 모듈 전역에 커서 키로 담고 실패 INSERT 후 트랜잭션 전체를 롤백해 픽스처가 심은 행까지 날렸다. 픽스처가 `(cur, seller_id)` 반환 + SAVEPOINT로 재설계.
  - `[low]` `[patch]` P11 — `sprint-status.yaml`이 `epic-10: backlog`로 코드와 반대를 말하고 있었다. `in-progress`/`done`으로 갱신.

defer 1건은 `docs/tech-debt.md` #109에 이미 등재돼 있다(anon GRANT 경계를 지키는 자동 검사가 없어 `search/page.tsx`의 로그인 분기 하나에 의존 — 트리거: Story 10.2 착수 시). **동결된 `deferred-work.md`에는 쓰지 않는다**(프로젝트 규칙 우선).

## Design Notes

**계약 자리는 이미 있다 — 이 스토리는 "값이 흐르게" 한다.** Story 8.3이 web `ListingCardData`·api `ListingCard`·app `ListingCardData` 세 곳에 신뢰속성 3필드를 nullable로 미리 넣어 뒀다(실측 확인). 그래서 §4.1 락스텝 4곳 중 **2·3·4번은 `fuel` 때문에만 변경**되고, 신뢰속성은 **DB 컬럼 + SELECT 경로(`SELECT_COLUMNS`·`ALLOWED_COLUMNS`·web/app select 문자열)**가 진짜 작업이다.

**backfill 여부 — 두 문구가 부딪혀 보이지만 답은 하나다.** 에픽 AC는 "기존 `accident_free`에서 승격되며 값이 보존된다"와 "기존 100건 NULL 유지·backfill 없음"을 나란히 적었다. 앞 문장은 **`accident_free` 컬럼과 그 값을 드롭하지 않는다**는 뜻이고(PRD 부록 "추가만·드롭 금지"와 일치), 뒷 문장이 `accident_status` 쪽 동작을 직접 규정한다. 따라서 **backfill 없음**이 확정이다. (구 PRD 부록 60행의 "0012 신뢰속성+backfill"은 증분 아키텍처 정정 섹션과 에픽 AC보다 오래된 서술이라 따르지 않는다.)

**프롬프트 회귀 주의.** 신뢰속성을 LLM 스키마에 넣는 것은 AC가 요구하지만, 그대로 넣으면 "무사고 차량 찾아줘"에 LLM이 `accident_status = '무사고'`(전부 NULL → 0건)를 쓸 수 있다. 지금 동작하는 경로는 `accident_free = true`다. 그래서 프롬프트에 **어느 쪽을 쓸지 지시문을 함께** 넣고 테스트로 고정한다.

**쓰기 경로 부재(이 스토리 밖, 대장 등재 대상).** Epic 10 어느 스토리에도 판매자가 신뢰속성을 **입력하는 폼**이 없다(10.2=표시, 10.3/10.4=옵션, 10.5=찜, 10.6=판매자 정보). 그래서 컬럼은 생기지만 값을 넣을 사람이 없고, 10.2의 뱃지와 10.7의 통합 검증은 **수동 시드 없이는 볼 게 없다**. 이 스토리에서 폼을 만드는 것은 범위 밖이므로 만들지 않고, 대장에 **트리거를 달아** 등재한다(예: "트리거: 10.2 착수 시 — 뱃지를 렌더할 실제 값이 있는지 먼저 확인").

## Verification

**Commands:**
- `python3 scripts/check_migrations.py` -- expected: 정적 3검사 + 도커 동적 검사 전부 통과(종료코드 0). 도커는 사용 가능하다(실측). 이 브랜치는 `develop`/`main`이 아니라 CI가 자동으로 돌지 않으므로 **반드시 로컬에서 돌린다**.
- `psql "postgresql://postgres:postgres@127.0.0.1:55322/postgres" -c "<위 CHECK red/green INSERT>"` -- expected: `'외판교환'`은 `23514`로 실패, `'단순교환'`은 성공. **두 출력을 모두 기록**한다.
- `cd api && python -m pytest -q` -- expected: 전부 통과(신규 sql_guard/listing_cards/프롬프트 테스트 포함).
- `cd web && npm run lint && npx tsc --noEmit && npm test` -- expected: 타입·린트 통과, vitest 통과.
- `export PATH="$PATH:/home/whlee/flutter/bin" && cd app && flutter test` -- expected: 전부 통과(신규 `ListingCardData` 단언 포함).
- `cd web && npm run build` -- expected: 빌드 성공(서버 컴포넌트 select 변경이 타입과 맞는지).

**Manual checks (if no CLI):**
- 로컬 Supabase(55322)에 마이그 적용 후 `select accident_free, accident_status, is_single_owner, is_non_smoker from listings limit 5;` -- 기존 행의 `accident_free`가 그대로이고 신규 3컬럼이 전부 NULL인지 눈으로 확인.
- 한 행에만 `accident_status='무사고'`를 넣고 web 목록(`/search`)을 브라우저로 열어 -- meta에 **연료가 보이고**, 신뢰 뱃지는 **아직 안 보이는지**(10.2 범위) 확인.

## Auto Run Result

Status: done

**구현 요약.** `listings`에 신뢰속성 3컬럼(`accident_status` text+CHECK · `is_single_owner` · `is_non_smoker`)을 **전부 nullable로 추가**(마이그 `0017`, additive·backfill 없음·기존 `accident_free` 보존)하고, 그 값이 DB→api→web/app 카드까지 흐르도록 conventions §4.1 락스텝 지점을 한 번에 갱신했다. 같은 락스텝에 `fuel`을 태워 대장 #67을 닫았다. 렌더(뱃지·면책 라벨)는 10.2 범위이므로 하지 않았다.

**변경 파일.**
- `supabase/migrations/0017_listings_trust_attributes.sql` (신규) — 신뢰속성 3컬럼 additive 추가. CHECK가 못 보는 것 3종을 헤더 주석에 실측 기록.
- `api/tests/integration/test_trust_attributes_real_db.py` (신규) — 실DB에서 CHECK가 실제로 거르는지 증명하는 통합 테스트 12건.
- `docs/conventions.md` — §4에 `fuel` 필드 추가, §4.1에 이번에 배운 락스텝 지점 2종(select 문자열 3곳·anon GRANT 승인 규칙) 승격.
- `api/app/graph/listing_cards.py` — `SELECT_COLUMNS` 7→11, 위치 매핑 확장, 튜플 폭 불일치 시 `SqlGuardError`, 도메인 밖 `accident_status` None 강등.
- `api/app/db/sql_guard.py` — `ALLOWED_COLUMNS`에 신뢰속성 3컬럼 추가.
- `api/app/schemas/ai.py` — `ListingCard.fuel` 추가.
- `api/app/graph/sql_rag_node.py` — 프롬프트 스키마에 3컬럼 + "무사고/사고 판정은 `accident_free`를 쓰고 bool 2컬럼으로는 필터하지 마라" 지시.
- `api/tests/{test_sql_guard,test_listing_cards,test_sql_rag_node,test_demo_acceptance,test_doc_rag_node}.py` — 신규 단언 및 11튜플 픽스처 갱신.
- `web/src/components/listings/ListingCard.tsx` — `fuel` 필드 + meta `주행 · 연료 · 지역(· 판매자)`, typeof 가드.
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` — select 문자열 확장(anon 경로는 3필드 명시 null 정규화).
- `app/lib/features/listings/{listing.dart,listings_repository.dart,listing_card.dart}` — `fuel` 모델·select·위젯 렌더.
- `app/test/listing_model_test.dart` — 신규 4필드 파싱·bool 3상태 단언.
- `.github/workflows/tests.yml` — `api-db` 잡 paths에 `supabase/migrations/**` 추가, 낡은 이름·주석 갱신.
- `docs/tech-debt.md` — #67 해소, #108·#109 신규 등재(트리거 포함).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 10.1 done, epic-10 in-progress.
- `_bmad-output/implementation-artifacts/epic-10-context.md` (신규) — Epic 10 컴파일 컨텍스트.

**리뷰 결과.** patch 11건 적용(high 1·medium 7·low 3) / defer 1건(대장 #109에 등재) / reject 3건 / intent_gap·bad_spec 0건.

**후속 리뷰 권고.** `true` — 패치 중 high 1건(P1, `/ai/search` 500 경로)이 있었다. 점수: high 1 → 무조건 true(3×medium 7 + 1×low 3 = 24도 임계 5 초과).

**검증(직접 실행·관찰).**
- `python3 scripts/check_migrations.py` → 정적 3검사 + 도커 동적 검사 통과(0017 포함, 프로브 3건 확인).
- CHECK red/green **실측**(로컬 Supabase 55322): `accident_status='외판교환'` INSERT → `ERROR: violates check constraint "listings_accident_status_check"`(23514) / `'단순교환'` → `INSERT 0 1`.
- **검사가 잡는지 증명**(변이 심기): 제약을 `drop constraint` → 통합 테스트 **4건 red** → 제약 원복 → **10건 green**. 존재가 아니라 작동을 확인했다.
- **검사가 안 보는 것 실측**: `accident_free=true` + `accident_status='사고'` 모순 조합 INSERT 성공 / 신규 3컬럼 전부 생략한 INSERT 성공(NULL 경로). 마이그 주석·대장·의도적 green 테스트 3곳에 기록.
- 기존 데이터 무변 실측: 103건 중 신규 3컬럼 non-null **0건**, `accident_free` null **0건**.
- CI 동등 환경 재현: 빈 pgvector 컨테이너에 프렐류드+마이그 전량 적용(profiles 0건) → 통합 테스트 **12건 통과, skip 0**. 원래는 `profiles`가 비어 조용히 skip될 자리였고, 그 거짓 통과를 막았다.
- `api pytest` → 201 passed / 17 skipped. `TEST_DATABASE_URL` 지정 시 → 213 passed / 5 skipped.
- `web`: `npm run lint` · `npx tsc --noEmit` · `npm test`(96 passed) · `npm run build` 전부 통과.
- `flutter test` → 80 passed.
- P1 회귀 직접 확인: 7튜플을 `rows_to_cards`에 투입 → `SqlGuardError('column_count_mismatch')`(IndexError 아님).

**잔여 위험.**
1. **신뢰속성에 값을 넣는 경로가 없다**(대장 #108). 컬럼은 생겼지만 판매자 입력 폼이 Epic 10 어느 스토리에도 없어, 10.2가 뱃지를 그려도 뜰 매물이 0건이다. 트리거: 10.2 착수 시.
2. **비로그인 방문자는 신뢰속성 3컬럼을 못 읽는다**(대장 #109). 0011의 anon 컬럼 GRANT 목록에 없어 요청 전체가 42501로 실패한다(실측). §9.3이 승인을 요구하므로 넓히지 않고 `search/page.tsx`가 로그인 여부로 분기한다 — 이 분기를 지키는 자동 검사는 아직 없다. 트리거: 10.2 착수 시.
3. **프롬프트 회귀 검사는 문자열 존재만 본다.** LLM이 실제로 어떤 SQL을 만드는지는 보지 않는다(테스트 주석에 명시). 실제 품질은 eval/live-smoke 트랙 몫.
4. **브랜치**: 이 작업은 `test/bmad-loop`(develop보다 9커밋 앞선 bmad-loop 검증용 브랜치)에서 이뤄졌다. 프로젝트 규약(B3)의 `develop` 개발 흐름과 다르므로, 반영하려면 develop으로 옮기는 판단이 필요하다.

---

**후속 리뷰 패스 (2026-07-22).** 4개 리뷰 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 돌렸고, 전원이 같은 최상위 결함 하나로 수렴했다.

- **패치 1건(high).** `rows_to_cards`가 `accident_status`(P2)만 계약-외 값을 None으로 강등하고 `fuel`·`is_single_owner`·`is_non_smoker`는 raw로 통과시켰다. sql_guard가 SELECT 컬럼 **순서**를 고정하지 않으므로, 폭은 11로 맞지만 순서를 바꾼 LLM SQL이 이 슬롯에 타입 어긋난 값(예: `fuel` 자리에 bool)을 넣으면 pydantic `ValidationError`가 나고 — 그건 `SqlGuardError`가 아니라 `sql_rag_node`의 재생성 루프를 빠져나가 `/ai/search`가 500이 된다. P1/P2가 닫으려던 실패 모드가 세 필드에 남아 있었다. P2 방어를 세 필드로 확장하고 회귀 테스트를 추가했다.
  - 변경 파일: `api/app/graph/listing_cards.py`(강등 3필드 확장 + docstring "왜 네 필드를 다 방어하나"), `api/tests/test_listing_cards.py`(신규 테스트 1건).
  - **잡는지 증명(red/green).** 방어를 되돌리면 신규 테스트가 정확히 `ValidationError`로 **red**(`fuel`·`is_single_owner` 2건) → 방어 복원 후 **green**. 존재가 아니라 작동을 확인했다.
  - 검증: `cd api && python -m pytest -q` → **202 passed / 17 skipped**(이전 201에서 신규 테스트 1건 증가, 회귀 0). web·app·마이그레이션은 이 패스에서 불변이라 재실행하지 않았다(원 실행에서 web 96·flutter 80·마이그 게이트 통과 확인됨).
- **reject 11건**(전부 low, 조치 없음). 대부분 이미 대장에 담겼거나(#108 쓰기 경로 부재, #109 anon GRANT 경계) 이 스토리가 만든 결함이 아니다(비현실적 빈-문자열 region, 전진 마이그에 없는 시나리오, 프로젝트 규칙12에 부합하는 Flutter E2E-only). defer·intent_gap·bad_spec 0건.
- **후속 리뷰 권고: `true`** — 이번 패스 패치에 high 1건(`/ai/search` 500 경로)이 있어 무조건 true.

---

**후속 리뷰 패스 2 (2026-07-22).** `done` 스펙에 대한 신선한 후속 리뷰(무인 dev-auto 재진입). 4개 레인 병렬. **새 패치·스펙 결함 0건** — 앞선 두 패스로 코드가 이미 굳어 있음을 확인.

- **patch 0 / bad_spec 0 / intent_gap 0.** 조치 없음.
- **defer 2건 → `docs/tech-debt.md` 신규 등재**(동결된 `deferred-work.md` 아님, 프로젝트 규칙 우선):
  - `#110` (medium) — `rows_to_cards`가 `fuel`·신뢰속성 4슬롯만 계약-외 강등하고 숫자/필수-str 7슬롯은 순서-뒤바뀐 폭11 LLM SQL에 `/ai/search` 500. **7슬롯은 10.1 이전부터 있던 선재 결함**이라 이 스토리 소산이 아님 — 근본 해결은 sql_guard의 SELECT 순서 고정(B9). 트리거 포함.
  - `#111` (low) — 클라이언트 `.select(...)` 3곳의 §4.1 락스텝을 지키는 자동 검사 부재 → #67 형태 재발 가능(B9). E2E-only(#106)라 즉시 패치 안 함. 트리거 포함.
- **reject 14건**(전부 low). 이미 대장(#108/#109)·앞선 패스에서 처리됐거나 의도 범위 밖(app `fromMap`은 매트릭스대로 type-guard만 요구, 상세 select는 10.2, 모순 허용은 AC #3이 문서화 요구한 의도적 gap).
- **후속 리뷰 권고: `false`** — 이번 패스 패치 0건(high 0), 점수 0 < 5. 남은 것은 트리거 달린 선재 부채 2건뿐이라 재진입할 코드 변경이 없다.
- **검증.** 이 패스는 코드를 바꾸지 않았다(문서 2건만: 대장 +#110/#111, 스펙 triage log). 앞선 실행에서 확인된 게이트(api 202·web 96·flutter 80·마이그 게이트)는 코드 불변이라 재실행하지 않았다. 등재 근거는 실코드 대조로 확인 — `listing_cards.py:89-92`에 숫자/str 슬롯 가드 부재 실측, `grep`으로 web/app select 테스트 0건 실측.
