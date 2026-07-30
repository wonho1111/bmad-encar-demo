---
title: '13.1 sql_guard 하이브리드 정비 + G2 baseline'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: 'd654beb50ce90cdd9bdd86ad2b895c5370dd0f35'
final_revision: '497f003e8cc31325588d0725a948826e8331a2b5'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 13(AI 검색 RAG 고도화)의 하이브리드(SQL+벡터) 검색을 만들기 전에, `sql_guard.validate_select_sql()`이 벡터 연산자(`<=>`·`::vector`·`embedding`·`vector`)를 아직 화이트리스트하지 않아 하이브리드 SQL을 통째로 거부한다. 또한 이후 RAG 스토리(13.2~13.8)가 회귀 없이 진행됐는지 잴 기준선이 없다 — `score_ab.py`+44개 질의셋 하니스는 이미 있지만 A/B 모델 비교용(원시 결과 2개 필수)이라 "지금 상태 1개"를 baseline으로 기록하는 용도로 못 쓴다. 부수적으로 `sql_guard`의 LIMIT 파싱이 `LIMIT (10)`처럼 숫자가 바로 안 붙는 형태를 못 잡아 이중 LIMIT의 깨진 SQL을 만든다(DW-315, 이 스토리로 예약됨).
**Approach:** `sql_guard.py`에 벡터 화이트리스트(신원 식별자 `embedding`·`vector`, 코드가 붙이는 `%s`/`%(name)s` 바인드 자리표시자)를 추가하되 OR·서브쿼리·컬럼·status 강제는 그대로 유지한다. `score_ab.py --raw`가 파일 1개(baseline 단독)도 받게 확장하고, 44개 질의셋을 실제로 구동해 그 shape의 raw 결과를 만드는 러너를 추가해 소규모로 직접 실행·검증한다. LIMIT 파싱은 숫자 형태가 아니면 명시 거부하도록 고친다.

## Boundaries & Constraints

**Always:**
- `validate_select_sql()`은 여전히 fail-closed다 — 이번에 새로 허용되는 건 `embedding`·`vector` 식별자와 `%s`/`%(name)s` 자리표시자뿐이고, OR 금지·서브쿼리 금지·금지키워드·테이블 화이트리스트·`status='on_sale'` 강제는 하이브리드 SQL에도 그대로 적용된다.
- 벡터 `ORDER BY embedding <=> %s::vector LIMIT n` 절은 **코드가 붙인다, LLM이 아니다**(I4) — 이 원칙을 기존 `DEFAULT_LIMIT`/`MAX_LIMIT` 주석과 같은 스타일의 코드 주석으로 화이트리스트 추가 지점 옆에 남겨 13.3 구현이 참조하게 한다.
- `\blimit\s+([-+]?\d+)`에 안 걸리는 LIMIT(예 `LIMIT (10)`)는 조용히 뒤에 `LIMIT 5`를 덧붙이지 않고 명시적으로 거부한다(DW-315) — 새 에러 코드 `limit_malformed`.
- `score_ab.py --raw`는 기존 2파일 A/B 비교 모드를 그대로 유지한다 — 1파일 모드는 순수 추가.
- Phase B raw 캡처 러너는 `RUN_LIVE_SMOKE=1`(기존 `test_live_smoke.py`와 동일 쿼터 보호 게이트) 없이는 절대 실행되지 않는다 — CI·무심코 실행한 pytest·다음 dev-auto 루프가 실수로 쿼터를 태우지 않게.

**Block If:**
- `ALLOWED_COLUMNS`나 `_SQL_KEYWORDS`에 `embedding`·`vector`가 이미 존재한다(예상 밖 선재 드리프트) — 그냥 덮어쓰지 않고 조사 후 블록.
- `api/docs/ai-ab-test-queryset.json`이 없거나 파싱 실패하거나 `items` 개수가 44에서 크게 벗어나 있다(하니스 전제 붕괴).

**Never:**
- Story 13.2(4분기 라우팅)·13.3(하이브리드 노드)의 실제 그래프 배선을 만들지 않는다 — 이 스토리는 `sql_guard`와 G2 도구만 준비한다.
- 44개 질의 × N=3(flaky 판정) 전량을 실제 프로덕션 Gemini에 이 무인 실행 안에서 돌리지 않는다 — Gemini 무료 티어 일일 쿼터(약 20 req/day, `test_live_smoke.py` 주석 근거)를 한 번에 넘길 수 있다. 전량 실행은 사용자가 쿼터를 보고 직접 트리거할 수동 후속 작업으로 남긴다(DW 신규 등재, trigger 명시).
- `ALLOWED_COLUMNS`에 `embedding`·`vector` 외 다른 컬럼을 추가하지 않는다(예: `storage_path`) — 범위 밖, conventions.md §4.1 락스텝 대상.
- `run_select()` 시그니처·`ai_readonly` 롤 정의·RLS를 건드리지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 정상 하이브리드 벡터 쿼리 | `... WHERE status='on_sale' AND body_type='SUV' ORDER BY embedding <=> %s::vector LIMIT 10` | 정규화된 SQL 그대로 반환(LIMIT 유지) | 통과, 에러 없음 |
| OR 주입(하이브리드 형태) | 위 쿼리에 `OR price < 1` 추가 | `SqlGuardError('forbidden_or')` | 거부 |
| 서브쿼리 주입(하이브리드 형태) | `... AND id IN (SELECT id FROM listings) ... ORDER BY embedding <=> %s::vector` | `SqlGuardError('subquery_not_allowed')` | 거부 |
| status 필터 누락(하이브리드 형태) | `SELECT id FROM listings WHERE body_type='SUV' ORDER BY embedding <=> %s::vector LIMIT 10` | `SqlGuardError('missing_status_filter')` | 거부 |
| 괄호 LIMIT(DW-315) | `... status='on_sale' LIMIT (10)` | `SqlGuardError('limit_malformed')` | 거부(기존 동작: `LIMIT (10) LIMIT 5` 이중 LIMIT의 깨진 SQL 생성 — 이걸 막는 게 이 케이스) |
| 바인드 자리표시자 오탐 | `embedding <=> %s::vector` | `%s`의 `s`, `::vector`의 `vector`가 unknown identifier로 오탐되지 않음 | 통과 |

</intent-contract>

## Code Map

- `api/app/db/sql_guard.py` -- `ALLOWED_COLUMNS`(37-42, **실제 20개 컬럼**)·`_SQL_KEYWORDS`(52-59)·식별자 스캔(146-154)·OFFSET 파싱(168-176)·LIMIT 파싱(177-196)이 이번 변경 지점. `no_strings` 리터럴 제거 패턴(96)을 그대로 흉내내, **"embedding"/"vector"를 `ALLOWED_COLUMNS`/`_SQL_KEYWORDS`에 넣지 않고**, `ORDER BY embedding <=> <placeholder>::vector` 모양 전체를 통째로 매치해 지우는 새 정규식 스텝을 추가(1차 리뷰 패스 bad_spec 수정 — 아래 Spec Change Log 참조).
  - **자리표시자는 이 정규식 안에서만 소비된다** — 벡터절 밖의 `%s`/`%(name)s`를 위치 무관하게 제거하는 별도 스텝은 두지 않는다(3차 리뷰 패스 bad_spec 수정). `run_select()`(`api/app/db/readonly.py`)는 `sql_rag_node.py`에서 params 없이 호출되므로, 가드를 통과한 미바인드 자리표시자는 psycopg 단계에서 문법 오류가 되어 400이 아니라 500이 된다.
  - **LIMIT·OFFSET 숫자 매처의 입력이 `cleaned`(리터럴 포함)라는 점이 선재 결함이다**(168·180행). 문자열 리터럴 안의 `limit <숫자>`가 실제 LIMIT절보다 먼저 매치돼 `MAX_LIMIT` 상한 검사·`DEFAULT_LIMIT` 주입이 통째로 우회된다 — 이번 스토리가 LIMIT 파싱 정비를 맡았으므로 여기서 함께 고친다(3차 리뷰 패스 bad_spec 수정).
- `api/tests/test_sql_guard.py` -- `test_allowed_columns_is_exactly_pinned`(250행대)가 `ALLOWED_COLUMNS` 정확집합을 고정 — `embedding` 추가 시 여기 갱신 필수. `_code()` 헬퍼·`_GOOD` 상수 재사용.
- `api/scripts/score_ab.py` -- `main()`(420-448)의 `--raw nargs=2 required=True`가 확장 지점. `score_model(queryset, r)`는 이미 raw 1개씩 순수하게 채점하므로(434행 리스트컴프) 재사용만 하면 됨.
- `api/tests/test_ab_scoring.py` -- `score_ab.py` 순수함수 단위테스트 관례(라이브 API 없음). CLI 1파일 모드 테스트를 여기 추가.
- `api/tests/test_live_smoke.py` -- `RUN_LIVE_SMOKE=1` 게이트·`_run_or_skip` 패턴의 원본. 신규 러너가 이 관례를 그대로 따른다.
- `api/app/graph/graph.py` -- `run_search(query, context)`가 러너가 호출할 유일한 공개 진입점.
- `api/docs/ai-ab-test-queryset.json` -- 44개 질의셋(단일 35·멀티턴 9), `_meta`에 채점 규약 문서화됨.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-315(해소 대상) 및 이번에 신규 등재할 "44개 전량 라이브 캡처는 수동" 항목이 들어갈 자리.

## Tasks & Acceptance

**Execution:**
- `api/app/db/sql_guard.py` -- **`embedding`을 `ALLOWED_COLUMNS`에, `vector`를 `_SQL_KEYWORDS`에 추가하지 않는다**(1차 구현이 이렇게 했다가 위치 무관 오탐/오남용 취약점으로 리뷰에서 되돌려짐 — 아래 Spec Change Log 참조). 대신 식별자 스캔 전에 `ORDER BY embedding <=> (%s|%\(\w+\)s)::vector` **모양 전체를 통째로 매치해 지우는** 새 정규식 스텝을 추가(문자열 리터럴 제거와 같은 자리·같은 스타일) — `embedding`·`vector`·바인드 자리표시자가 **이 정확한 위치에서만** 통과하고, `SELECT embedding ...`이나 `FROM listings vector`처럼 다른 위치에 나오면 여전히 `forbidden_column`으로 거부된다. LIMIT 정규식이 안 걸리는데 `\blimit\b`는 존재하면 `limit_malformed`로 명시 거부 -- AC-SEC-1·I4·DW-315.
- `api/app/db/sql_guard.py` -- **벡터절 밖의 `%s`/`%(name)s`를 제거하는 "방어적 이중 스트립" 스텝을 두지 않는다**(3차 리뷰 패스 bad_spec 수정 — 2차 스펙이 이걸 "이중으로 막는다"고 지시했지만 실제로는 **가드를 여는** 스텝이었다. 아래 Spec Change Log 참조). 자리표시자는 위 벡터절 정규식이 자기 절 안에서 소비하는 것만 허용되고, 그 밖에 나오는 자리표시자는 **미화이트리스트 식별자로 남아 `forbidden_column`으로 거부돼야 한다** -- 베이스라인 동작(실측: `WHERE model = %s` → `forbidden_column`)을 그대로 유지하는 것이 목표이며, 새로 허용 범위를 넓히지 않는다.
- `api/app/db/sql_guard.py` -- **OFFSET·LIMIT 숫자 매처의 입력을 `cleaned`에서 `no_strings`(리터럴 제거본)로 바꾼다**(3차 리뷰 패스 bad_spec 수정). `limit_malformed` 분기에만 적용됐던 "리터럴 제거본으로 검사한다"는 규칙을 짝이 되는 숫자 매처에도 똑같이 적용하는 것이다 — 지금은 규칙이 한쪽에만 적용돼 짝이 안 맞는다. 반환값(`normalized`)은 계속 `cleaned` 기반이어야 한다(리터럴을 지운 SQL을 실행하면 안 되므로) -- DW-315와 같은 계열의 LIMIT 파싱 결함.
- `api/tests/test_sql_guard.py` -- **`test_allowed_columns_is_exactly_pinned`는 이번엔 갱신하지 않는다**(`embedding`을 더 이상 `ALLOWED_COLUMNS`에 넣지 않으므로 기존 20컬럼 그대로 유지). I/O 매트릭스 6행을 각각 테스트 함수로 -- 회귀 3케이스(정상 통과/OR·서브쿼리 거부/status 누락 거부) + DW-315 케이스 + 자리표시자 오탐 케이스 커버. **추가로** 아래 3개 회귀 테스트를 신설한다:
  1. `embedding`이 벡터 절 밖(예: `SELECT id, embedding FROM listings WHERE status='on_sale' LIMIT 5`)에 나오면 여전히 `forbidden_column`으로 거부(1차 패스가 놓친 위치-무관 취약점을 잠근다).
  2. **벡터절 밖의 자리표시자가 거부되는지** -- `SELECT id FROM listings WHERE status='on_sale' AND model = %s LIMIT 5`와 `... AND price <= %(maxp)s LIMIT 5`가 각각 `forbidden_column`(2차 패스가 새로 연 구멍을 잠근다).
  3. **리터럴 안의 `limit`/`offset` + 숫자가 실제 절을 가리지 않는지** -- `... AND description = 'limit 3' LIMIT 100`은 `limit_exceeded`로 거부되고(MAX_LIMIT=50 우회 차단), `... AND description = 'limit 10'`(실제 LIMIT절 없음)은 통과하면서 `LIMIT 5`가 실제로 덧붙는지 단언. 기존 `test_limit_word_inside_literal_does_not_trigger_malformed`의 `'no limit here'`는 숫자가 없어 이 분기에 못 닿으므로 그것만으로는 부족하다.
- `api/scripts/score_ab.py` -- `--raw`를 `nargs='+'`로 바꾸고 길이 1|2만 허용(그 외 `ap.error`), 1개면 `lexicographic_winner`/`regression` 계산을 건너뛰고 `{"baseline_summary": summary}`만 `--out`에 기록 -- **키 이름은 `baseline_summary`다, `baseline`이 아니다**(1차 구현이 2파일 모드의 `report["baseline"]`이 이미 모델명 문자열이라는 걸 놓치고 같은 키를 재사용해 모드마다 타입이 바뀌는 결함을 만들었다 — 아래 Spec Change Log 참조). 13.8이 나중에 후보 1개를 이 baseline과 비교할 수 있게 하는 최소 확장.
- `api/scripts/run_phase_b.py`(신규) -- `RUN_LIVE_SMOKE=1`일 때만 동작, 큐리셋의 각 item에 대해 `run_search()`를 1회(N=1, flaky 판정용 N=3은 이번 스토리 범위 밖) 호출해 `score_model()`이 기대하는 `results[id] = [{route_last/turns, ids_last, answer_last, tokens_in, tokens_out, latency_ms}]` shape으로 직렬화 -- `tokens_in`/`tokens_out`은 `run_search()`가 현재 노출 안 하므로 best-effort 0(비용 축은 이 스토리의 1차 관심사가 아님, G2의 핵심 신호는 `result_mean`/`gate_pass`/`routing_correct`).
- `api/tests/test_ab_scoring.py` 또는 신규 `api/tests/test_run_phase_b.py` -- `run_search`를 모킹해 러너의 per-item shape 조립과 `score_ab.py`의 1파일 CLI 모드를 라이브 호출 없이 결정론적으로 검증.
- 로컬 Supabase(`postgresql://postgres:postgres@127.0.0.1:55322/postgres`, 이미 기동 중)에 `DATABASE_URL`을 맞추고, 큐리셋 중 경로 A/B/C를 대표하는 소수(3~5개)만 실제로 `run_phase_b.py`를 돌려 러너가 기계적으로 동작함을 직접 확인 -- B4 "재보기 전엔 선언하지 않는다". 결과를 `api/docs/g2-baseline-partial.json`로 저장.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- "44개 전량(N=3 flaky 포함) 라이브 캡처"를 신규 DW로 등재, `trigger: 사용자가 Gemini 쿼터 여유를 확인하고 직접 실행할 때(또는 Story 13.8 착수 직전)`.

**Acceptance Criteria:**
- Given `sql_guard.validate_select_sql()`, when 하이브리드 벡터 쿼리(`<=>`·`::vector`·`embedding`·`%s` 바인드)를 검증하면, then 화이트리스트를 통과하고 `status='on_sale'` AND 누락 시엔 여전히 거부된다(AC-SEC-1).
- Given 위 화이트리스트 확장, when OR 주입 또는 서브쿼리를 하이브리드 형태 SQL에 섞으면, then 기존과 동일하게 거부된다(회귀 없음).
- Given `LIMIT (10)`처럼 숫자가 바로 안 붙는 LIMIT, when 검증하면, then 이중 LIMIT의 깨진 SQL을 만들지 않고 `limit_malformed`로 명시 거부한다(DW-315).
- Given `score_ab.py --raw <file1>`(1개만), when 실행하면, then A/B 비교 없이 그 raw 1개의 채점 요약을 `{"baseline_summary": ...}`로 출력한다(2파일 모드의 `{"baseline": <모델명 문자열>, ...}`과 키가 겹치지 않는다). 기존 `--raw <a> <b>` 2파일 모드는 회귀 없다.
- Given `embedding`이 벡터 절(`ORDER BY embedding <=> ...::vector`) 밖의 다른 위치(예: SELECT 목록)에 나오면, when 검증하면, then 여전히 `forbidden_column`으로 거부된다(위치-무관 화이트리스트로 인한 신규 크래시 표면을 만들지 않는다).
- Given `%s`/`%(name)s` 바인드 자리표시자가 벡터 절 밖(예: `WHERE model = %s`)에 나오면, when 검증하면, then 베이스라인과 동일하게 `forbidden_column`으로 거부된다 — 가드를 통과시켜 params 없는 `run_select()`로 흘려보내 psycopg 문법오류(500)로 바꾸지 않는다.
- Given 문자열 리터럴 안에 `limit`/`offset` + 숫자가 들어 있는 쿼리(예: `description = 'limit 3'`), when 검증하면, then 그 리터럴이 실제 LIMIT/OFFSET 절로 오인되지 않는다 — 실제 `LIMIT 100`은 `limit_exceeded`로 거부되고(MAX_LIMIT 우회 차단), 실제 LIMIT 절이 없으면 `LIMIT 5`(DEFAULT_LIMIT)가 실제로 덧붙는다(무제한 SELECT 차단).
- Given 로컬 Supabase(55322)와 `GEMINI_API_KEY`가 준비된 상태, when `RUN_LIVE_SMOKE=1`로 `run_phase_b.py`를 대표 질의 3~5개에 대해 실행하면, then 실제 raw 결과가 만들어지고 `score_ab.py`의 1파일 모드로 채점된다(직접 실행·관찰로 확인, 선언만으로 끝내지 않음).
- Given 44개 전량 라이브 캡처가 이번 실행에서 수행되지 않는다는 결정, when 이 스토리를 마치면, then `deferred-work.md`에 그 사실과 트리거가 등재돼 있다(B8 — 미룬 판단은 틀린 게 아니라 안 적는 게 틀린 것).

## Spec Change Log

### 2026-07-30 — Review pass 1, bad_spec 수정 (2건)

- **트리거 발견 1 (verification-gap + adversarial + edge-case-hunter 중복 확인):** `embedding`을 `ALLOWED_COLUMNS`에, `vector`를 `_SQL_KEYWORDS`에 블랭킷 추가하는 원래 Tasks 지시가, 위치와 무관하게 두 토큰을 SQL 어디서나 허용하게 만들었다. `embedding`이 `rows_to_cards()`의 무방비 숫자 슬롯(`year`/`price`/`mileage`)에 들어가면 잡히지 않는 `TypeError`로 `/ai/search`가 500을 낸다 — 이전엔 이 SQL이 `forbidden_column`으로 안전하게 막혔었다(이번 화이트리스트 확장이 새로 연 구멍). `vector`도 마찬가지로 테이블 별칭 등 엉뚱한 자리에서 통과된다.
  - **무엇을 고쳤나:** Tasks & Acceptance의 sql_guard 실행 지시를 "블랭킷 추가"에서 "`ORDER BY embedding <=> (%s|%(name)s)::vector` 모양 전체를 정규식으로 통째 매치해 지우는 위치-스코프 스텝"으로 교체(Code Map·Design Notes·AC·Verification 동반 수정). `ALLOWED_COLUMNS`/`_SQL_KEYWORDS`는 이제 건드리지 않는다.
  - **피한 known-bad 상태:** `embedding`/`vector`가 벡터 절 밖에서도 통과해 크래시 표면·오탐 표면을 새로 여는 것.
  - **KEEP(재도출 시 유지):** `%s`/`%(name)s` 바인드 자리표시자를 문자열 리터럴과 같은 자리에서 방어적으로 한 번 더 지우는 스텝(벨트-앤-서스펜더로 유지) · `limit_malformed`(DW-315) 분기의 설계와 에러 코드 분리는 그대로 유지 · I/O 매트릭스(intent-contract 안, 무수정)의 6개 시나리오는 전부 그대로 유효.

- **트리거 발견 2 (adversarial + edge-case-hunter 중복 확인):** `score_ab.py --raw` 1개 모드가 `report["baseline"]`을 요약 dict로 쓰도록 지시했는데, 기존 2개 모드는 같은 키를 이미 모델명 **문자열**로 쓰고 있어 같은 필드명이 모드마다 타입이 바뀌는 API가 됐다 — 13.8이 이 파일을 소비할 때 어느 모드로 만들어졌는지 몰라 타입 오류로 깨질 수 있다.
  - **무엇을 고쳤나:** Tasks & Acceptance·Design Notes·AC의 1개 모드 출력 키를 `"baseline"`에서 `"baseline_summary"`로 교체.
  - **피한 known-bad 상태:** 같은 키가 모드마다 다른 타입을 갖는 API로 인한 후속 소비 코드의 `TypeError`.
  - **KEEP(재도출 시 유지):** 1개 모드일 때 `lexicographic_winner`/`regression` 계산을 건너뛰는 로직 자체, 2개 모드는 완전히 무변경으로 유지한다는 결정, `score_model()`을 그대로 재사용하는 접근.

### 2026-07-30 — Review pass 3, bad_spec 수정 (2건)

- **트리거 발견 1 (adversarial + edge-case-hunter + verification-gap + intent-alignment 4개 레이어 전부 중복 확인):** 2차 스펙의 Design Notes가 지시한 "`%s`/`%(name)s` 위치 무관 방어적 이중 스트립"이 실제로는 가드를 **여는** 스텝이었다. 식별자 스캔이 보는 본문에서 자리표시자를 지우면 그 자리표시자는 미화이트리스트 식별자로 안 잡히고 통과한다. 실측 대조로 확인: 베이스라인 `d654beb`에서 `WHERE model = %s`·`WHERE price <= %(maxp)s`는 `forbidden_column`으로 거부됐으나 2차 구현에서는 둘 다 통과. `sql_rag_node.py`가 `run_select(safe_sql)`를 params 없이 호출하므로 결과는 psycopg 문법 오류 → 광역 except → **400이 500으로 바뀜**. 검증 공백도 확인: 그 줄을 `pass`로 바꿔도 `test_sql_guard.py` 전량이 green이었다.
  - **무엇을 고쳤나:** Code Map·Tasks & Acceptance·Design Notes에서 "방어적 이중 스트립" 지시를 **삭제**하고, 자리표시자는 벡터절 정규식 매치 범위 안에서만 소비하며 그 밖의 자리표시자는 `forbidden_column`으로 남긴다는 지시로 교체. AC 1건·Verification의 red→green 실측 1건 추가.
  - **피한 known-bad 상태:** LLM이 뱉은 미바인드 자리표시자가 가드를 통과해 DB 문법 오류로 500을 내는 것(전엔 한국어 메시지의 400). 13.3이 임베딩 파라미터를 바인드할 때 LLM의 유령 `%s`가 첫 슬롯을 먹는 파라미터 오정렬도 함께 피한다.
  - **KEEP(재도출 시 유지):** 벡터절 위치-스코프 정규식(`order\s+by\s+embedding\s*<=>\s*(?:%s|%\(\w+\)s)\s*::\s*vector`) 자체와 그 옆의 I4 주석 · `ALLOWED_COLUMNS`/`_SQL_KEYWORDS`를 건드리지 않는다는 결정 · 벡터절 밖 `embedding`/`vector`가 거부되는 걸 잠그는 2개 테스트 · `limit_malformed`(DW-315) 분기 설계와 에러 코드 분리 · `score_ab.py` 1파일 모드의 `baseline_summary` 키 · `run_phase_b.py`의 `RUN_LIVE_SMOKE=1` 게이트·item별 try/except·중간 flush·`_validate_item()` fail-fast·`--subset` 미매칭 id 거부 · `graph.py`의 additive `route` 키와 `test_graph.py`의 `out["route"]` 단언 4건.

- **트리거 발견 2 (adversarial + edge-case-hunter + verification-gap + intent-alignment 4개 레이어 전부 중복 확인):** LIMIT·OFFSET **숫자 매처**가 `cleaned`(리터럴 포함)를 읽는다. 2차 패스가 `limit_malformed` 분기에는 "리터럴 제거본으로 검사한다"는 규칙을 세웠는데 짝이 되는 숫자 매처에는 적용하지 않아 두 분기가 상보적이지 않다. 실측: `description = 'limit 3' LIMIT 100` → 리터럴의 `3`이 먼저 매치돼 통과(**`MAX_LIMIT`=50 우회**), `description = 'limit 10'` → **LIMIT 절이 아예 없는 무제한 SELECT 반환**, `'limit 0'`·`'offset 999999'` → 정상 쿼리 오탐 거부. 베이스라인에서도 동일하게 재현되는 선재 결함이지만, intent가 "LIMIT 파싱 정비"를 이 스토리 범위로 명시했고 이 스토리가 DW-315를 "4증상 전부 확인 완료"로 닫았으므로 여기서 함께 고친다(안 고치면 대장이 거짓을 기록한다 — CLAUDE.md B8).
  - **무엇을 고쳤나:** Code Map·Tasks & Acceptance에 "OFFSET·LIMIT 숫자 매처 입력을 `no_strings`로 교체(반환 `normalized`는 계속 `cleaned` 기반)" 지시 추가, Design Notes에 실측 표로 근거 기록, AC 1건·Verification의 red→green 실측 1건 추가, 회귀 테스트 3케이스 신설 지시.
  - **피한 known-bad 상태:** `MAX_LIMIT` 상한 우회와 `DEFAULT_LIMIT` 주입 누락으로 `listings` 전량이 `ai_readonly`로 읽혀 `rows_to_cards()`로 흐르는 것. 그리고 DW-315가 닫힌 상태로 이 계열 결함의 추적자가 사라지는 것.
  - **KEEP(재도출 시 유지):** `limit_malformed` 분기가 `no_strings`를 읽는다는 2차 패스 패치(그건 옳았다) · `'no limit here'` 오탐 회귀 테스트 · `[-+]?` 부호 포함 매칭(음수 LIMIT의 이중 LIMIT 방지) · `MAX_LIMIT`/`MAX_OFFSET`/`DEFAULT_LIMIT` 값과 에러 코드·한국어 메시지 전부 무변경.

- **재도출 참고(중요):** 2차 패스 구현은 **커밋 `da9adfe`에 그대로 남아 있다**. 위 KEEP 항목들을 손으로 다시 쓰지 말고 `git show da9adfe:<경로>`로 꺼내 쓰고, 이번 수정 2건(자리표시자 위치-무관 제거 스텝 삭제 · LIMIT·OFFSET 숫자 매처 입력을 `no_strings`로 교체)과 신규 회귀 테스트만 그 위에 얹는다. `api/docs/g2-baseline-partial.json`은 실제 Gemini 쿼터를 태워 얻은 실측 캡처이므로 같은 방법으로 복원한다 — 다만 러너가 기계적으로 동작함은 다시 확인해야 하며(B4), 3건 소규모 재실행이 쿼터상 가능하면 재실행하고 불가하면 복원본을 쓴 사실을 보고에 명시한다. `baseline_revision`은 스토리 착수 전 상태(`d654beb`)를 그대로 유지한다 — HEAD(`da9adfe`)로 바꾸면 다음 리뷰 패스가 스토리 전체 변경이 아니라 교정 델타만 보게 된다.
- **부수 정정:** Tasks & Acceptance·Code Map이 `ALLOWED_COLUMNS`를 "원래 13컬럼"이라 적었으나 실측 20개다(`id, status, manufacturer, model, year, price, mileage, fuel, transmission, body_type, color, region, displacement, seats, accident_free, accident_status, is_single_owner, is_non_smoker, options, description`) — 숫자를 정정했다.

## Review Triage Log

### 2026-07-30 — Review pass 1
- intent_gap: 0
- bad_spec: 2: (high 0, medium 2, low 0)
- patch: 5: (high 0, medium 2, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 2
- addressed_findings:
  - `medium` `bad_spec` `sql_guard.py`의 `embedding`/`vector` 블랭킷 화이트리스트가 위치 무관하게 통과돼 `rows_to_cards()`의 무방비 숫자 슬롯에서 크래시 표면을 새로 열었다 — Tasks/Design Notes를 위치-스코프 정규식 방식으로 교체, 코드 되돌리고 재도출 예정.
  - `medium` `bad_spec` `score_ab.py` 1파일 모드가 2파일 모드와 같은 `"baseline"` 키를 다른 타입(dict vs 문자열)으로 써서 13.8 소비 코드가 깨질 수 있었다 — 키를 `baseline_summary`로 분리, 코드 되돌리고 재도출 예정.
- 이번 패스는 bad_spec이 있어 patch(5)·defer(1)·reject(2)는 이번 라운드에 적용하지 않음(moot) — 재도출 후 다음 리뷰 패스가 다시 판단한다. 참고로 분류만 기록: patch(medium) run_phase_b.py 항목별 예외처리·중간저장 부재(전체 소실 위험) · patch(medium) DW-315 종료가 원 4증상 중 OFFSET-only는 미해소 · patch(low) `--subset` 빈 문자열/공백만 입력 시 무경고 전량·공백 실행 · patch(low) kind 오타 시 무경고 `_run_single` 폴백 · patch(low) 잘못된 `--raw` 개수 테스트가 종료코드/메시지 미검증 · defer(low) 향후 13.3이 LIMIT까지 `%s` 파라미터화하면 `limit_malformed`와 충돌 가능(13.3 스펙 작성 시 리마인드) · reject 모델명 "unknown" 폴백(비용은 이미 항상 0이라 실질 영향 없음) · reject RUN_LIVE_SMOKE가 실제 쿼터 카운팅은 안 함(형제 test_live_smoke.py와 동일 수준의 기존 관례라 이 스토리 결함 아님).

### 2026-07-30 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 3, low 5)
- defer: 2: (high 0, medium 0, low 2)
- reject: 2
- addressed_findings:
  - `medium` `patch` `sql_guard.py`의 `limit_malformed` 분기가 문자열 리터럴 미제거본(`cleaned`)을 검사해, `description = 'no limit here'`처럼 리터럴 안에 우연히 "limit" 단어가 있으면 실제 LIMIT절이 없는 정상 쿼리도 오탐 거부됨(직접 재현 확인) — `no_strings`(리터럴 제거본)로 검사하도록 수정, 회귀 테스트 추가.
  - `medium` `patch` `run_search()`의 신규 `route` 반환값을 검증하는 테스트가 하나도 없어 회귀를 못 잡음(실측: `route`를 항상 빈 문자열로 망가뜨려도 관련 테스트 74개가 전부 통과) — `test_graph.py`의 A/B/C·unexpected 라우팅 테스트 4개에 `out["route"]` 단언 추가(unexpected 케이스는 실제 raw 값 "Z"가 그대로 남는 실측 동작을 그대로 고정).
  - `medium` `patch` `run_phase_b.py`의 `capture()`가 item 순회 중 예외 발생 시 이미 확보한 앞선 결과까지 전부 유실(1차 패스 triage에 이미 기록돼 있던 항목, 이번에 적용) — item별 try/except(`{"error": ...}` 기록 후 계속 진행) + 매 item 처리 후 `--out` flush로 수정.
  - `low` `patch` `deferred-work.md` DW-315가 "OFFSET-only 미해소"로 재보기 없이 단정한 오류(실측: `OFFSET 10` → `OFFSET 10 LIMIT 5`로 이미 안전) — 실측 확인 후 문구 정정, `location:` 갱신, 4증상 전부 확인 완료로 `status: done` 처리.
  - `low` `patch` `run_phase_b.py`의 `--subset`이 큐리셋에 없는 id를 조용히 드롭 — 미매칭 id가 있으면 `ap.error`로 명시 거부하도록 수정.
  - `low` `patch` `run_phase_b.py`의 `capture()` kind 분기가 `"single"` 아닌 모든 값을 무조건 multiturn 취급해 원인불명 `KeyError` — `_validate_item()` 신설, kind가 single/multiturn 밖이면 라이브 호출 전 fail-fast.
  - `low` `patch` `run_phase_b.py`의 `_run_multiturn()`이 `turns` 빈 배열이어도 조용히 빈 결과를 캡처 — 같은 `_validate_item()`에서 fail-fast.
  - `low` `patch` `score_ab.py` 모듈 docstring이 1파일(baseline 단독) 모드 실행 예시를 안 보여줌 — 한 줄 추가.

### 2026-07-30 — Review pass 3
- intent_gap: 0
- bad_spec: 2: (high 1, medium 1, low 0)
- patch: 9: (high 0, medium 4, low 5)
- defer: 3: (high 0, medium 3, low 0)
- reject: 3
- addressed_findings:
  - `high` `bad_spec` LIMIT·OFFSET 숫자 매처가 `cleaned`(리터럴 포함)를 읽어, `description = 'limit 3' LIMIT 100`이 `MAX_LIMIT`(50)을 우회하고 `description = 'limit 10'`은 LIMIT 절이 아예 없는 무제한 SELECT를 반환한다(4개 레이어 중복 확인 + 베이스라인 대조 실측). 2차 패스가 `limit_malformed` 분기에만 세운 "리터럴 제거본으로 검사" 규칙을 짝이 되는 숫자 매처에도 적용하도록 스펙 수정, 코드 되돌리고 재도출 예정.
  - `medium` `bad_spec` Design Notes가 "방어적 이중 스트립"이라 부른 위치-무관 `%s`/`%(name)s` 제거 스텝이 실제로는 가드를 여는 스텝이어서, 베이스라인에서 `forbidden_column`으로 거부됐던 `WHERE model = %s`가 통과해 params 없는 `run_select()`로 흘러 500이 된다(4개 레이어 중복 확인 + 베이스라인 대조 실측 + 해당 줄을 `pass`로 바꿔도 전량 green인 검증 공백 확인). 그 스텝을 스펙에서 삭제, 코드 되돌리고 재도출 예정.
- 이번 패스는 bad_spec이 있어 patch(9)·defer(3)·reject(3)는 이번 라운드에 적용하지 않음(moot) — 재도출 후 다음 리뷰 패스가 다시 판단한다. 분류만 기록:
  - patch(medium) `run_phase_b.py`가 기록하는 `{"error": ...}` 항목을 `score_ab.score_model()`이 `r["route_last"]` 직접 색인으로 읽어 `KeyError`로 죽는다(실측 확인) — 부분 실패 내구성이 정작 자기 소비자에서 무용해진다.
  - patch(medium) 44개 중 3개만 캡처된 raw를 채점해도 `baseline_summary`에 커버리지가 안 남아 `gate_pass: true`로 기록된다 — 13.8이 3건 대비 44건을 비교하게 된다.
  - patch(medium) N=1 러너에서 `flaky_n`은 구조적으로 항상 0인데 `lexicographic_winner` 3순위 판정에 그대로 쓰인다 — 측정 안 한 축으로 baseline이 자동 승리한다.
  - patch(medium) `tokens_in`/`tokens_out` 하드코딩 0이 `cost_usd` 0.0이 되어 4순위 비용 판정에 들어간다 — 조작된 0이 모델 채택 결정을 낸다.
  - patch(low) `_validate_item()`이 `single` item의 `query` 누락·turn의 키 오타를 검증하지 않아 데이터 버그가 429와 구별 안 되는 `{"error": ...}`로 삼켜진다(쿼터 소모 후 발견).
  - patch(low) `_flush()`가 try 밖에 있고 `--out` 부모 디렉터리 존재를 라이브 호출 전에 검증하지 않아, 경로가 없으면 첫 캡처 후 `FileNotFoundError`로 전량 유실.
  - patch(low) 매칭 item이 0개면 `_flush()`가 한 번도 안 돌아 이전 `--out` 파일이 그대로 남고 성공으로 보고된다 — 낡은 데이터가 새 baseline으로 채점된다.
  - patch(low) I4 주석이 `validate_select_sql()` 안에만 있어, intent가 가리킨 `ALLOWED_COLUMNS` 근처를 본 13.3 구현자는 하이브리드 지원 흔적을 못 찾는다.
  - patch(low) 스펙이 `ALLOWED_COLUMNS`를 "13컬럼"이라 적었으나 실측 20개(이번 Spec Change Log에서 정정).
  - defer(medium) 에픽·아키텍처 문서가 벡터절을 `ORDER BY embedding <=> $1::vector LIMIT k`로 규정하지만 psycopg는 `%s` 스타일이고 가드는 `$1::vector`를 `forbidden_column`, `LIMIT %s`를 `limit_malformed`로 거부한다(실측) — 선재 계획문서/드라이버 불일치, 수정 자리는 13.3 스펙.
  - defer(medium) `router_node._fallback_route()`가 일시적 429/timeout을 삼켜 휴리스틱 라우트를 반환하므로, 러너가 폴백을 실측값으로 기록한다 — 선재 라우터 동작, 44건 전량 캡처(DW-554) 직전에 봐야 한다.
  - defer(medium) 질의셋의 `primary_path` A/B/C와 13.2가 도입할 `REJECT|CLARIFY|SQL|HYBRID` 라우트 어휘가 어긋나 13.2 이후 재실행은 라우팅 0/44가 된다 — 선재 에픽 설계 긴장, 수정 자리는 13.2 스펙.
  - reject `graph.py`의 `final_state.get("route", "")` fail-soft(2차 패스가 A/B/C 라우트 단언을 이미 추가해 배선 파손을 잡는다) · `test_graph.py`가 unexpected 라우트 `"Z"`를 고정한 것(스펙이 이미 의도된 결정·잔여 리스크로 기록) · "44건 전량 baseline이 아직 없다"(intent의 Approach가 소규모 검증으로 명시하고 DW-554로 등재됨).

### 2026-07-30 — Review pass 4
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 3, low 7)
- defer: 7: (high 2, medium 5, low 0)
- reject: 4
- addressed_findings:
  - `medium` `patch` `score_ab.score_model()`이 `r["route_last"]`를 무조건 색인해, `run_phase_b.py`가 기록한 `{"error": ...}` 항목이 하나만 있어도 `KeyError`로 죽고 성공 캡처 전량이 채점 불가가 됐다(실측 재현) — error 런은 건너뛰고 `errored_n`으로 집계하도록 수정, 캡처→채점 이음매를 실패 경로까지 통과하는 테스트 추가.
  - `medium` `patch` 1파일 baseline 요약에 커버리지가 없어 3/44 부분 캡처가 완전한 통과 baseline처럼 보였다(실측: `result_mean=1.0, gate_pass=True`, 41건 누락 흔적 없음) — `coverage`(총계·채점수·누락 id)와 `is_partial`을 요약에 기록.
  - `medium` `patch` 조작된 값이 모델 채택 결정에 들어갔다: N=1 러너에서 `flaky_n`은 구조적으로 항상 0, `tokens_in/out`은 하드코딩 0이라 `cost_usd`가 $0.0000 — 실측으로 미측정 baseline이 실제 측정된 후보를 비용 축에서 이기는 것을 확인했다. 두 축을 **데이터에서 유도**해(런수·토큰 합계) 미측정이면 해당 tier를 건너뛰도록 수정. 1차 패치가 `tokens_measured` 플래그 부재 시 `True`로 기본값을 잡아 **정작 이 스토리가 커밋하는 산출물이 "측정됨"으로 오라벨링**되던 것을 오케스트레이터 재검증에서 잡아 되돌려 유도 방식으로 재수정했다.
  - `low` `patch` `_validate_item()`이 `single`의 `query`·turn의 `query` 누락을 검증하지 않아 데이터 버그가 429와 구별 안 되는 `{"error": ...}`로 삼켜졌다(쿼터 소모 후) — 라이브 호출 전 fail-fast로 수정.
  - `low` `patch` 중복 item id가 앞선 유료 캡처를 조용히 덮어쓰고 "N개 완료" 카운트가 그 손실을 감췄다 — 사전검증에서 중복 id 거부.
  - `low` `patch` `_flush()`가 비원자적(truncate-then-write)이어서 44개 쓰기 창 중 어디서든 중단되면 누적 결과 전부가 깨진 JSON이 됐다 — 임시파일+원자적 교체로 수정, `--out` 부모 디렉터리도 라이브 호출 전 검증(전엔 첫 캡처 후 `FileNotFoundError`로 전량 유실).
  - `low` `patch` 쿼터 게이트가 종료코드 0으로 끝나 `run_phase_b.py && score_ab.py`가 낡은 파일을 채점했고, error 항목도 "캡처 완료"로 집계됐다 — 게이트·실패 발생 시 모두 non-zero 종료.
  - `low` `patch` `--out` 기본값이 커밋된 baseline 산출물 자신이라 전량 실행 시 `--out`을 깜빡하면 실측 캡처를 덮어썼다 — `--out`을 필수 인자로.
  - `low` `patch` 벡터절 정규식의 `re.IGNORECASE`가 자리표시자에도 적용돼 `%S::VECTOR`가 통과했다(psycopg가 바인드할 수 없는 형태) — 식별자는 대소문자 무관, 자리표시자만 대소문자 구분으로 분리.
  - `low` `patch` `epic-13-context.md`가 44개 G2 baseline이 13.1에서 심긴다고 단정해 하위 스토리가 3건 파일을 44건으로 오인할 수 있었다 — 3/44만 확보됐고 나머지는 DW-554라는 단서를 그 줄에 추가.
- **defer 7건은 `deferred-work.md`에 DW-557~DW-563으로 신규 등재**(기존 항목은 수정하지 않았다 — 오케스트레이터 소유). 전부 오케스트레이터가 직접 재현해 확인했고, 5건은 베이스라인 `d654beb`에서도 동일하게 재현되는 선재 결함이다:
  - DW-557 `high` `status='on_sale'` 강제가 존재 확인뿐이어서 `NOT status='on_sale'`·`IS NOT TRUE`로 판매완료 매물이 실제로 노출된다(로컬 DB에서 sold 행 3건 반환 확인, FR11 우회). 선재. → 13.2 착수 시.
  - DW-558 `high` LIMIT·OFFSET 절 파싱이 bare integer 이외 4형태(`LIMIT 5+100`·`OFFSET (999999)`·`LIMIT 10, 5`·`LIMIT 5 LIMIT 999`)를 못 잡아 MAX_LIMIT/MAX_OFFSET이 우회된다(`LIMIT 5+100`은 로컬 DB에서 95행 전량 반환). DW-315가 닫은 4증상과 다른 형태이며 카탈로그된 적 없다. 선재. → 13.3 착수 시.
  - DW-559 `medium` 하이브리드 벡터절이 가드를 통과한 뒤 params 없이 실행돼 400이 500으로 바뀐다 — intent의 Never("13.2·13.3 그래프 배선 금지")가 이 배선을 13.3으로 미룬다. → 13.3 구현 시.
  - DW-560 `medium` 계획문서 3곳의 `$1::vector`·`LIMIT k` 바인드 형태가 psycopg `%s`와 어긋나 가드가 거부한다(실측). 선재. → 13.3 스펙 작성 직전.
  - DW-561 `medium` `router_node` 폴백이 429를 삼켜 러너가 폴백 라우트를 실측값으로 기록한다. 선재. → DW-554 전량 캡처 직전.
  - DW-562 `medium` 질의셋 `primary_path` A/B/C와 13.2의 4분기 라우트 어휘가 어긋나 재실행이 라우팅 0/44가 된다. 선재. → 13.2 스펙 작성 시.
  - DW-563 `medium` CLARIFY 턴 상한이 클라이언트 강제로만 규정돼 유료 호출 상한이 상한이 아니다(B9 위반). 선재. → 13.4 스펙 작성 직전.
- reject: 세 스캔 본문(`cleaned`/`no_strings`/`no_vector`) 이름 재정비 제안(인접 코드 리팩터 = 범위 밖, A3) · DW-315의 `location:` 줄번호 드리프트(이번 실행은 기존 장부 항목 수정 금지 제약이 걸려 있어 손대지 않는다 — 아래 잔여 리스크에 기록) · intent-contract 자체의 서술 부정확(Block If·Never가 이제 발사 불가능한 술어가 된 점, Problem이 차단자를 "벡터 연산자"로 진단한 점, `graph.py`가 Never의 "sql_guard와 G2 도구만" 밖인 점 — 전부 동작 영향 없고 Spec Change Log에 경위가 이미 기록됨) · "가드 산출물이 실행 가능한지 보는 테스트가 없다"(DW-559로 흡수).

### 2026-07-30 — Review pass 5
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 4, low 6)
- defer: 3: (high 0, medium 3, low 0)
- reject: 6
- addressed_findings:
  - `high` `patch` 벡터절 정규식이 절의 **끝**을 안 잠가, 매치 뒤에 뭐가 붙든 절이 통째로 지워지며 검증 없이 통과했다(실측 3형태): `<=> %s::vector DESC`(거리 연산자라 "가장 안 닮은 순"으로 결과가 조용히 뒤집힘) · `<=> %s::vector, price`(검증된 적 없는 2차 정렬키 동승) · 같은 절 2회 반복(ORDER BY 둘인 실행 불가 SQL → psycopg 문법오류로 400이 500). 절 뒤에 문장 끝·`LIMIT`·`OFFSET`만 올 수 있게 lookahead로 고정, 회귀 4케이스 신설(끝고정 제거 시 red 확인).
  - `medium` `patch` 달러 인용 리터럴(`$$...$$`·`$tag$...$tag$`)을 `no_strings`가 안 지워 LIMIT·OFFSET 숫자 매처를 가로챘다 — 3차 패스가 작은따옴표에 대해 막은 것과 **같은 구멍**이 남아 있었다(실측: `description = $$limit 3$$ LIMIT 100` → `MAX_LIMIT`=50 우회 통과, `description = $$limit 3$$` → LIMIT 절 없는 무제한 SELECT). psycopg 자리표시자는 `%s`라 정상 경로에 `$`가 등장할 이유가 없으므로 파싱 규칙을 늘리는 대신 `$` 자체를 `dollar_quote_not_allowed`로 fail-closed 거부.
  - `medium` `patch` `score_ab.gate_pass`가 `contamination == 0 and deadend == 0`만 봐서, **채점된 run이 하나도 없어도 PASS**였다(실측: 44건 전량 429 실패한 캡처와 아예 빈 캡처가 둘 다 `gate_pass=True`). 그 둘은 측정이 없으면 구조적으로 0인 값이다 — 에픽 G2 게이트가 이 값을 읽으므로 게이트가 통째로 무력화됐다. `errored_n == 0 and scored_n > 0`을 게이트에 포함.
  - `medium` `patch` 멀티턴 채점 분기(러너 `turns[]`의 유일한 소비자, 큐리셋 44건 중 9건·라우팅 단위 20/55·**하드 오염 게이트가 오직 여기서만** 올라감)를 보는 테스트가 하나도 없어, 턴 라우팅 집계와 오염 게이트를 통째로 무력화해도 전량 green이었다 — 턴별 라우팅 집계·오염 발화·라우팅 오답 집계 테스트 3건 신설.
  - `medium` `patch` `run_phase_b.capture()`가 매칭 item 0개일 때 flush를 한 번도 안 해 **이전 실행의 낡은 `--out`이 그대로 남는데** exit 0으로 "0개 캡처 완료"를 냈다(3차 패스에 patch(low)로 잡혔다가 bad_spec 루프백에서 유실된 항목) — 루프 시작 전 1회 flush로 수정. 그 체인(`run_phase_b.py && score_ab.py`)이 다른 모델의 옛 캡처를 새 baseline으로 채점하던 경로다.
  - `low` `patch` 멀티턴 맥락 누적 테스트가 2턴짜리라 "누적"과 "직전 턴만 유지"가 같은 입력을 만들어 회귀를 관찰할 수 없었다(실측: 누적을 교체로 망가뜨려도 green) — 실제 큐리셋과 같은 3턴으로 바꿔 3번째 호출의 context를 단언.
  - `low` `patch` `flaky_measured`의 True 방향을 아무 테스트도 안 봐서 이 플래그가 영영 False로 굳어도 잡히지 않았다(그러면 2파일 A/B가 flaky 축을 통째로 건너뛴다) — N>1 raw 테스트 신설.
  - `low` `patch` 러너가 찍던 per-run `tokens_measured` 스탬프를 아무도 안 읽는다(`score_model`은 토큰 합계로 직접 판단). 남겨두면 "True로 찍으면 비용 축이 켜진다"는 오해를 부르고, 스탬프가 없는 커밋된 `g2-baseline-partial.json`과 shape이 어긋난다 — 스탬프 제거, 부재를 테스트로 못박음.
  - `low` `patch` `capture()`가 `item["id"]`를 사전검증보다 먼저 색인해 id 누락이 맨 `KeyError`로 죽었다(이 파일의 다른 구조 오류는 전부 원인을 말해주는 `ValueError`) — 사전검증에 편입.
  - `low` `patch` `test_flush_is_atomic_...`의 `.tmp` 부재 단언이 공허했다 — 주입한 실패가 `.tmp` 생성 **전에** 터져 어떤 구현에서도 참이었다. 단언을 걷어내고 실제 동작(정리 경로 없음 → 다음 flush가 덮어씀)을 주석으로 기록, 실패 주입 기준도 호출 횟수 대신 내용으로 바꿔 순서 변화에 안 흔들리게.
  - `low` `patch` `epic-13-context.md`가 1차 패스에서 **폐기된** 블랭킷 식별자 화이트리스트를 확정 결정처럼 적고, 벡터절 바인드를 `$1::vector LIMIT k`(psycopg가 아닌 형태, 가드가 거부)로 규정했다 — 하위 스토리 13.2~13.8이 가장 먼저 읽는 문서라 실제 채택된 위치-스코프 방식과 `%s` 형태로 정정(계획문서 원본 정리는 DW-560 유지).
- **defer 3건은 `deferred-work.md`에 DW-564~DW-566으로 신규 등재**(기존 항목은 수정하지 않았다 — 오케스트레이터 소유): DW-564 `lexicographic_winner()`가 커버리지 다른 요약의 절대 개수를 비교해 3/44 baseline이 44/44 후보에게 커버리지 차이만으로 진다(→ 13.8) · DW-565 유일한 러너가 구조적으로 N=1·토큰 0이라 사전식 3·4순위가 영구 미측정이다(→ 13.8) · DW-566 러너 테스트가 `RUN_LIVE_SMOKE=1`을 켠 채 몽키패치 1곳에만 의존해 쿼터 보호가 관례에 얹혀 있다(→ DW-554 실행 직전).
- reject: `offset_malformed` 부재(DW-558이 이미 카탈로그한 같은 계열) · DW-557·DW-558 재보고(등재 완료) · `_flush()`가 item별 try 밖이라 flush 실패 시 캡처가 중단됨(이전 flush는 원자적 교체로 무사하고 트레이스백으로 시끄럽게 실패하므로 데이터 손실 없음) · `score_ab.py` docstring의 2파일 예시가 없는 파일을 가리킴(예시일 뿐 동작 영향 없음) · intent-contract 자체의 서술 부정확(Block If가 발사 불가능한 술어가 된 점 등 — pass 4가 이미 같은 이유로 reject, 경위는 Spec Change Log에 있음) · DW-315 종료 문구와 DW-558의 긴장(기존 장부 항목 수정 금지 제약 — 아래 잔여 리스크에 기록).

## Design Notes

**`embedding`/`vector`는 위치-스코프 매치로만 통과시킨다(1차 리뷰 패스 수정).** 1차 구현은 `embedding`을 `ALLOWED_COLUMNS`에, `vector`를 `_SQL_KEYWORDS`에 그냥 추가했다 — 이러면 두 토큰이 SQL 어디에 나와도(예: `SELECT id, embedding FROM listings ...`, `FROM listings vector`) 통과한다. `embedding`이 SELECT 목록의 숫자 슬롯(`year`/`price`/`mileage`, `int()` 직접 캐스팅) 자리에 끼면 `rows_to_cards()`가 잡지 못하는 `TypeError`로 `/ai/search`가 500을 낸다(`listing_cards.py`의 기존 주석이 이미 경고하는 위치-혼동 취약점의 새 사례) — 이전엔 이 SQL 자체가 `forbidden_column`으로 아예 막혔었다. 고친 방법: 문자열 리터럴을 지우는 기존 패턴(96행)과 같은 자리에, `ORDER BY embedding <=> (%s|%\(\w+\)s)::vector` **정확히 이 모양 전체**를 통째로 매치해 지우는 정규식 스텝을 추가한다. 이 매치에 걸린 범위 안의 `embedding`/`vector`/자리표시자만 소비되고 사라지므로, 그 밖의 위치에 나오는 `embedding`·`vector`는 여전히 미화이트리스트 식별자로 거부된다. `ALLOWED_COLUMNS`/`_SQL_KEYWORDS`는 건드리지 않는다(13컬럼·기존 키워드 그대로).

**`%s`/`%(name)s` 자리표시자는 벡터절 안에서만 소비한다 — 위치 무관 제거 스텝을 두지 않는다(3차 리뷰 패스 수정).** 2차 스펙은 "벡터절 정규식이 자기 절 안의 자리표시자는 이미 소비하니, 그 밖에 남는 건 방어적 케이스뿐 — 리터럴 제거와 같은 자리에 `%\(\w+\)s|%s` 제거 스텝을 하나 더 두어 **이중으로 막는다**(벨트-앤-서스펜더)"고 지시했다. 이 추론이 틀렸다. 그 스텝은 무언가를 **막는 게 아니라 여는** 스텝이다 — 식별자 스캔이 보는 본문에서 자리표시자를 지우면, 그 자리표시자는 "미화이트리스트 식별자"로 안 잡히고 **통과한다**. 실측 대조: 베이스라인(`d654beb`)에서 `SELECT id FROM listings WHERE status='on_sale' AND model = %s LIMIT 5`는 `forbidden_column`으로 거부됐고, 그 스텝을 넣은 구현에서는 통과했다. 그리고 `sql_rag_node.py`는 `run_select(safe_sql)`를 **params 없이** 호출하므로, 통과한 미바인드 `%s`는 psycopg 단계에서 문법 오류가 되고 `ai.py`의 광역 except에 걸려 **400(한국어 거부 메시지)이 500(서버 내부 오류)으로 바뀐다**. LLM이 리터럴 대신 `%s`를 뱉는 것은 흔한 습관이므로 실제로 도달하는 경로다. 그래서 이번엔 자리표시자를 **벡터절 정규식 매치 범위 안에서만** 소비하고, 그 밖의 자리표시자는 그대로 `forbidden_column`에 걸리게 둔다("새로 허용되는 것"의 범위를 넓히지 않는다 — intent-contract의 fail-closed Always 조항).

**LIMIT·OFFSET 숫자 매처도 리터럴 제거본으로 검사한다(3차 리뷰 패스 수정).** 2차 패스가 `limit_malformed` 분기에 대해 "리터럴 미제거본(`cleaned`)으로 검사하면 리터럴 속 `limit` 단어가 분기를 잘못 태운다"는 규칙을 세웠는데, **짝이 되는 숫자 매처(`\blimit\s+([-+]?\d+)`·`\boffset\s+([-+]?\d+)`)는 여전히 `cleaned`를 읽는다.** 규칙이 한쪽에만 적용돼 두 분기가 상보적이지 않다. 실측 결과(베이스라인부터 이미 존재하는 선재 결함):

| 입력 | 현재 결과 | 문제 |
|---|---|---|
| `... AND description = 'limit 3' LIMIT 100` | 통과, `LIMIT 100` 그대로 | 리터럴의 `3`이 먼저 매치돼 `n=3`으로 판정 → **`MAX_LIMIT`(50) 상한 우회** |
| `... AND description = 'limit 10'`(실제 LIMIT 절 없음) | 통과, **LIMIT 절이 아예 없는 SQL** | `normalized = cleaned` 경로를 타서 `DEFAULT_LIMIT` 주입이 건너뛰어짐 → **무제한 SELECT** |
| `... AND description = 'limit 0'` | `limit_invalid` 거부 | 정상 쿼리 오탐 거부 |
| `... AND description = 'offset 999999'` | `offset_exceeded` 거부 | 정상 쿼리 오탐 거부 |

`description`은 `ALLOWED_COLUMNS`에 있는 자유텍스트 컬럼이고 LLM이 사용자 질의를 그대로 리터럴에 흘려넣는 것이 이 파일 docstring이 상정한 위협 모델이므로, 도달 가능한 경로다. 이 스토리가 "LIMIT 파싱 정비"와 DW-315 종료를 맡았으므로 같은 3줄 안에서 함께 고친다 — 매처 입력만 `no_strings`로 바꾸고, **반환되는 `normalized`는 계속 `cleaned` 기반**이어야 한다(리터럴이 지워진 SQL을 실행하면 안 된다).

`limit_malformed` vs 기존 `limit_invalid`: `limit_invalid`는 "숫자는 잡았는데 값이 0 이하"(의미 오류), `limit_malformed`는 "숫자 형태 자체를 못 잡음"(형식 오류) — 원인이 다르므로 코드를 분리해 로그·재시도 프롬프트에서 구분 가능하게 한다.

`score_ab.py` 1파일 모드의 출력 키는 `baseline_summary`다(1차 리뷰 패스 수정). 2파일 모드는 이미 `report["baseline"]`을 **모델명 문자열**로 쓰고 있어(기존 코드, 변경 없음), 1파일 모드가 같은 키에 요약 dict를 넣으면 같은 필드명이 모드마다 타입이 바뀌는 API가 된다 — 13.8이 이 파일을 나중에 소비할 때 어느 모드로 만들어졌는지 몰라 깨질 수 있으므로, 애초에 겹치지 않는 별도 키를 쓴다.

## Auto Run Result

**요약:** `sql_guard.validate_select_sql()`에 하이브리드 벡터절(`ORDER BY embedding <=> %s::vector`) 위치-스코프 화이트리스트를 추가하고, `LIMIT (10)`처럼 숫자가 안 붙는 LIMIT을 `limit_malformed`로 명시 거부하도록 고쳤다. `score_ab.py --raw`가 1파일(baseline 단독) 모드를 지원하도록 확장했고, 큐리셋을 실제 `run_search()`로 돌려 그 shape의 raw 결과를 만드는 러너(`run_phase_b.py`)를 신설해 대표 3개 질의(A1·B1·C1)로 실측 검증했다.

리뷰를 4패스 돌렸고 bad_spec 루프백이 2회 있었다. pass 1은 블랭킷 화이트리스트의 위치-무관 크래시 표면과 1파일 모드의 타입-바뀌는 키 충돌을 잡았고, pass 3은 더 무거운 두 건을 잡았다 — (1) 스펙이 "이중으로 막는다"고 지시한 자리표시자 위치-무관 제거 스텝이 실제로는 **가드를 여는** 스텝이어서 베이스라인에서 거부됐던 `WHERE model = %s`가 통과해 400이 500이 되던 것, (2) LIMIT·OFFSET 숫자 매처가 문자열 리터럴 포함본을 읽어 `description = 'limit 3' LIMIT 100`이 `MAX_LIMIT`을 우회하고 `description = 'limit 10'`이 무제한 SELECT를 반환하던 것. 둘 다 근본 원인이 스펙 문구에 있어 스펙을 고치고 코드를 되돌려 재도출했다. pass 4는 재도출된 코드에서 patch 10건(캡처 실패 항목이 채점기를 죽이던 것, 부분 캡처가 완전한 통과 baseline처럼 보이던 것, 조작된 flaky 0·비용 $0이 모델 채택 결정을 내리던 것 등)을 적용하고, 선재 결함 7건을 장부에 등재했다.

**파일 변경:**
- `api/app/db/sql_guard.py` — 하이브리드 벡터절 위치-스코프 정규식 제거 스텝 추가(자리표시자는 이 절 안에서만 소비, 대소문자 구분), `limit_malformed` 신설, LIMIT·OFFSET 숫자 매처 입력을 리터럴 제거본으로 교체.
- `api/app/graph/graph.py` — `run_search()` 반환에 `route` 부가 키 추가(러너의 라우팅 채점용, additive).
- `api/scripts/score_ab.py` — `--raw` 1파일 모드 추가(`baseline_summary` 키), error 런 건너뛰기·`errored_n`, `coverage`/`is_partial` 기록, flaky·비용 축을 데이터에서 유도해 미측정 tier 건너뛰기.
- `api/scripts/run_phase_b.py`(신규) — G2 baseline 캡처 러너. 라이브 호출 전 사전검증(kind·`query`·중복 id·`--out` 경로), item별 예외 처리, 원자적 중간 flush, 게이트·실패 시 non-zero 종료, `--out` 필수.
- `api/tests/test_sql_guard.py` — I/O 매트릭스 6행 + 위치-스코프(벡터절 밖 `embedding`·`vector`·자리표시자 거부) + 리터럴 하이재킹(LIMIT·OFFSET) + `%S` 거부 회귀 테스트.
- `api/tests/test_ab_scoring.py` — CLI 1파일/2파일/잘못된 개수 모드, error 런 채점, 커버리지 기록, 미측정 tier 건너뛰기 테스트.
- `api/tests/test_graph.py` — A/B/C·unexpected 라우팅 테스트에 `out["route"]` 단언 추가.
- `api/tests/test_run_phase_b.py`(신규) — shape 조립·서브셋 필터·쿼터 게이트·부분 실패 유실 방지·사전검증·원자적 flush·종료코드 테스트.
- `api/docs/g2-baseline-partial.json`(신규) — 대표 3개 질의(A1·B1·C1)의 실측 raw 캡처 결과.
- `_bmad-output/implementation-artifacts/epic-13-context.md` — G2 baseline 서술에 "3/44만 확보, 나머지는 DW-554" 단서 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-554·DW-555·DW-556(앞선 패스)에 이어 **DW-557~DW-563 신규 7건 등재**. 기존 항목은 이번 실행에서 수정하지 않았다(오케스트레이터 소유).

**리뷰 findings 분류:**
- Pass 1: intent_gap 0 · bad_spec 2 (medium 2) · patch 5 · defer 1 · reject 2 — bad_spec 있어 patch/defer/reject는 그 라운드에 미적용(moot), 스펙 재도출 후 코드 재구현.
- Pass 2: intent_gap 0 · bad_spec 0 · patch 8 (medium 3, low 5, 전부 적용) · defer 2 (low 2, DW-555·DW-556 등재) · reject 2.
- Pass 3: intent_gap 0 · bad_spec 2 (high 1, medium 1) · patch 9 · defer 3 · reject 3 — bad_spec 있어 patch/defer/reject는 그 라운드에 미적용(moot), 스펙 수정 후 코드 재도출.
- Pass 4: intent_gap 0 · bad_spec 0 · patch 10 (medium 3, low 7, 전부 적용) · defer 7 (high 2, medium 5 — DW-557~DW-563 등재) · reject 4.

**Follow-up review recommendation 계산(pass 5 갱신):** 이번 패스(pass 5)에서 patch로 확정·적용된 건만 집계 — high 1건, medium 4건, low 6건. **high가 1건이라도 있으면 무조건 true**(점수식도 `3 × 4 + 1 × 6 = 18 ≥ 5`) → **true**.

---

## Auto Run Result — Review pass 5 (후속 리뷰)

**이번 패스가 한 일:** `done`으로 닫힌 스펙에 후속 리뷰 1패스를 더 돌렸다. bad_spec·intent_gap은 없었고(스펙 문구가 아니라 코드가 그 문구를 덜 지킨 경우들), patch 11건을 적용하고 선재/후속 결정 3건을 장부에 등재했다. 코드 되돌림·재도출은 없었다.

**가장 무거운 발견 — 벡터절 정규식이 "절 모양"이 아니라 "접두사"만 검사했다.** 13.1이 새로 연 유일한 통과 경로가 벡터절인데, 그 정규식이 절의 **끝**을 안 잠갔다. 그래서 매치 뒤에 뭐가 붙어도 절이 통째로 지워졌다 — 실측으로 세 형태가 통과했다: `<=> %s::vector DESC`(`<=>`는 거리 연산자라 DESC는 "가장 안 닮은 순"이다 — 가드는 통과시키고 결과만 조용히 뒤집힌다), `<=> %s::vector, price`(검증된 적 없는 2차 정렬키가 딸려 들어온다), 같은 절 2회 반복(ORDER BY가 둘인 실행 불가 SQL → psycopg 문법오류로 400이 500). 절 뒤에는 문장 끝·`LIMIT`·`OFFSET`만 올 수 있게 lookahead로 못박았다. 여기 안 걸리는 변형은 지워지지 않아 `forbidden_column`으로 남는다 — **넓히는 쪽이 아니라 막는 쪽으로 실패한다.**

**두 번째 — 3차 패스가 막은 리터럴 하이재킹과 같은 구멍이 달러 인용으로 남아 있었다.** `no_strings`는 작은따옴표만 지우므로 `$$limit 3$$`는 "리터럴이 아닌 본문"으로 남아 LIMIT·OFFSET 숫자 매처를 그대로 가로챈다(실측: `description = $$limit 3$$ LIMIT 100` → `MAX_LIMIT`=50 우회, `description = $$limit 3$$` → LIMIT 절 없는 무제한 SELECT). psycopg 자리표시자는 `%s` 스타일이라 정상 경로에 `$`가 나올 이유가 없으므로, 파싱 규칙을 늘리는 대신 `$`를 fail-closed로 거부했다.

**세 번째 — 게이트가 "위반 없음"만 봐서 아무것도 안 잰 캡처를 PASS로 통과시켰다.** `contamination`·`deadend`는 채점된 run이 하나도 없으면 구조적으로 0이다. 실측: 44건 전량이 429로 실패한 캡처와 아예 빈 캡처가 둘 다 `gate_pass=True`였다. 에픽 G2 게이트("baseline 이하면 에픽 미종료")가 그 값을 읽으므로 게이트가 통째로 무력화된다. `errored_n == 0 and scored_n > 0`을 게이트 조건에 넣었고, 커버리지를 **콘솔에도** 찍게 했다(전엔 JSON에만 남아 사람이 보는 화면엔 `게이트: PASS`만 떴다 — 커버리지를 기록한 이유 자체가 그걸 막는 것이었다).

**추가 파일 변경(pass 5):**
- `api/app/db/sql_guard.py` — 벡터절 정규식에 끝 고정 lookahead 추가, 달러 인용(`$`) fail-closed 거부(`dollar_quote_not_allowed`), `ALLOWED_COLUMNS` 옆에 하이브리드가 어디서 처리되는지 가리키는 주석 추가(intent가 요구한 "화이트리스트 추가 지점 옆" 참조점).
- `api/scripts/score_ab.py` — `gate_pass`에 "실제로 측정됐다" 조건 추가, 1파일 모드 콘솔 요약에 커버리지·부분캡처 경고 출력.
- `api/scripts/run_phase_b.py` — 루프 시작 전 1회 flush(0건 매칭 시 낡은 `--out` 잔존 차단), `id` 누락 사전검증, 안 읽히는 `tokens_measured` 스탬프 제거.
- `api/tests/test_sql_guard.py` — 벡터절 끝고정 회귀 4건 + 벡터식이 ORDER BY 밖(SELECT 목록·WHERE)에 오면 거부 + 달러 인용 거부.
- `api/tests/test_ab_scoring.py` — 게이트 3건(전량 실패·빈 캡처·정상 전량), 멀티턴 채점 3건, `flaky_measured` True 방향 1건.
- `api/tests/test_run_phase_b.py` — 맥락 누적을 3턴으로 확장, 0건 매칭 시 낡은 파일 덮어쓰기, `id` 누락 거부, 스탬프 부재 단언, 공허했던 `.tmp` 단언 정리.
- `_bmad-output/implementation-artifacts/epic-13-context.md` — 폐기된 블랭킷 화이트리스트 서술과 `$1::vector` 바인드 형태를 실제 채택된 위치-스코프·`%s` 형태로 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-564~DW-566 신규 3건. 기존 항목은 이번에도 수정하지 않았다(오케스트레이터 소유).

**검증 수행(전부 직접 실행·관찰):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **272 passed, 82 skipped**(pass 4의 258 → 신규 회귀 14건 증가). 라이브 게이트 skip은 정상.
- **B4 red→green 실측 9건.** 고친 부분을 하나씩 되돌려 해당 테스트가 red가 되는 것을 확인하고 원복해 green: 벡터절 끝고정 제거(3건 red) · 달러 인용 거부 제거(1건) · `gate_pass` 옛 조건 복원(2건) · 멀티턴 오염 게이트 무력화(1건) · `flaky_measured = True` 제거(1건) · 루프전 flush 제거(1건) · 맥락 누적→교체(1건) · `id` 사전검증 제거(1건) · `tokens_measured` 스탬프 되살림(1건). 마지막에 전량 원복 후 272 green 재확인.
- **가드 판정 대조표 직접 실행:** 새로 막는 6형태(`DESC`·중복절·후행 정렬키·`$$…$$` 3변형)와 계속 통과해야 하는 4형태(절 뒤 문장끝/`LIMIT`/`OFFSET`, named 자리표시자), 그리고 기존 거부 5형태(`forbidden_or`·`missing_status_filter`·벡터절 밖 `%s`·`limit_malformed`·리터럴 `'limit 3' LIMIT 100`)가 모두 기대대로임을 확인.
- **커밋된 baseline 재채점(로컬 Supabase 55322 실제 연결, 경로 A 골든 SQL 실행):** `score_ab.py --raw docs/g2-baseline-partial.json` → 콘솔에 `커버리지: 3/44 채점(실패 0 · 미캡처 41) ⚠ 부분 캡처`가 실제로 출력됨을 확인(전엔 이 줄이 없어 `게이트: PASS`만 보였다).
- **라이브 Gemini 재캡처는 이번 패스에서 하지 않았다.** 러너의 라이브 호출 경로 자체는 이번에 바뀌지 않았고(변경은 전부 라이브 호출 **전** 사전검증과 파일 쓰기), 스탬프 제거로 러너 출력과 커밋된 `g2-baseline-partial.json`의 shape이 오히려 일치하게 됐다. Gemini 무료 티어 쿼터를 태우지 않는다는 intent의 Never 조항을 지키기 위한 판단이며, 캡처→채점 이음매는 위 로컬 DB 재채점과 `test_main_end_to_end_...`(모킹) 테스트로 확인했다.

**잔여 리스크(pass 5 추가):**
- **`$1::vector`의 거부 코드가 바뀌었다.** 달러 인용 차단이 식별자 스캔보다 먼저 걸리므로, DW-560이 근거로 적은 "`$1::vector` → `forbidden_column`"이 이제 `dollar_quote_not_allowed`다. 거부된다는 결론은 그대로이고 코드만 다르다 — 기존 장부 항목 수정 금지 제약이 걸려 있어 손대지 않았다(오케스트레이터 몫).
- **DW-315 종료 문구와 DW-558의 긴장이 남아 있다.** DW-315는 "LIMIT 비정수형 처리 미흡"을 4증상 확인 완료로 닫았는데, 같은 계열의 다른 형태(`LIMIT 5+100` 등)는 DW-558로 열려 있다. 같은 제약 때문에 이번에도 문구를 손대지 않았다. pass 4도 같은 항목을 기록했다.
- **사전식 승부의 축 3개가 사실상 남아 있지 않거나 미검증이다**(DW-565): flaky·비용 tier가 이 레포가 만들 수 있는 raw로는 영구 미측정이고, 남는 지연 tier는 로컬 컨테이너 기준이다. 커버리지가 다른 요약끼리의 비교도 여전히 절대 개수로 이뤄진다(DW-564).
- 하이브리드 벡터절은 이제 세 방향(끝고정·달러인용·위치)으로 더 좁아졌다 — 13.3이 실제로 붙일 절이 이 모양에서 벗어나면 `forbidden_column`으로 막힌다(DW-555·DW-560과 같은 계열). 13.3 착수 시 붙일 절의 정확한 문자열을 먼저 이 가드에 통과시켜 보는 것이 안전하다.

**검증 수행(전부 오케스트레이터가 직접 실행·관찰):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **258 passed, 82 skipped**(라이브 게이트 skip은 정상). pass 2 시점 233 → pass 4 신규 회귀 테스트가 늘어 258.
- `cd api && .venv/bin/python -m pytest tests/test_sql_guard.py -q` → 50 passed. `tests/test_ab_scoring.py tests/test_run_phase_b.py -q` → 48 passed(라이브 호출 0).
- **Matrix Test Audit:** intent-contract의 I/O 매트릭스 6행을 각각 실행해 기대 코드와 일치함을 확인(`pass`/`forbidden_or`/`subquery_not_allowed`/`missing_status_filter`/`limit_malformed`/`pass` → 6/6 일치). 각 행을 잡는 이름 있는 테스트(`test_hybrid_vector_query_passes`·`test_hybrid_or_rejected`·`test_hybrid_subquery_rejected`·`test_hybrid_missing_status_filter_rejected`·`test_parenthesized_limit_rejected_as_malformed`·`test_hybrid_bind_placeholder_named_form_passes`)가 실제로 실행돼 PASSED임을 `-v` 출력으로 확인(skip·미등록 아님).
- **pass 3 bad_spec 2건 수정 실측:** 베이스라인 `d654beb`의 `sql_guard.py`를 별도 모듈로 로드해 대조했다. `WHERE model = %s`는 베이스라인에서 `forbidden_column`이었고 pass 2 구현에서 통과했다가 지금 다시 `forbidden_column`으로 복귀(가드를 여는 스텝 제거 확인). `description = 'limit 3' LIMIT 100`은 베이스라인·pass 2에서 통과(MAX_LIMIT=50 우회)했다가 지금 `limit_exceeded`로 거부, `description = 'limit 10'`은 LIMIT 절 없는 무제한 SELECT였다가 지금 `LIMIT 5`가 실제로 덧붙는 것을 확인.
- **pass 4 patch 실측:** `%S::VECTOR` → `forbidden_column` 거부(정상 `%s`는 통과). error 항목이 든 raw를 `score_model()`에 넣어 `KeyError` 없이 `errored_n=1`·`is_partial=True`로 채점됨을 확인. 실제 커밋 산출물 `docs/g2-baseline-partial.json`을 채점해 `is_partial=True`·`coverage 3/44`·`missing 41건`·`flaky_measured=False`·`tokens_measured=False`를 확인하고, 그 baseline을 실제 측정된 후보와 붙여 **비용 축의 조작된 $0.0000이 더 이상 승부를 결정하지 못하고 동률로 빠지는 것**을 확인(1차 패치는 플래그 기본값 `True` 때문에 이 실측에서 여전히 비용 축으로 이겼고, 그래서 유도 방식으로 되돌려 재수정했다).
- B4 red→green: pass 4의 patch 10건 중 7건(1·3·4·5·6·7·9)에 대해 고친 부분을 일부러 되돌려 해당 테스트가 red가 되는 것을 확인한 뒤 원복해 green. `tokens_measured` 재수정도 같은 방식으로 red→green 확인.
- 라이브 실행(RUN_LIVE_SMOKE=1, 로컬 Supabase 55322 + 실제 Gemini): `run_phase_b.py --subset A1,B1,C1`로 대표 3건을 **이번 재도출에서 다시 캡처**하고 `score_ab.py` 1파일 모드로 채점(라우팅 3/3, 결과정확도 1.0) — 직접 실행·관찰로 확인.

**잔여 리스크:**
- **선재 보안 결함 2건이 열린 채 남는다(이번 스토리 범위 밖, 실측 확인·등재 완료).** `status='on_sale'` 강제가 존재 확인뿐이라 `NOT status='on_sale'`로 판매완료 매물이 실제로 노출되고(DW-557, 로컬 DB에서 sold 행 3건 반환), LIMIT·OFFSET 절 파싱이 bare integer 이외 4형태를 못 잡아 MAX_LIMIT/MAX_OFFSET이 우회된다(DW-558, `LIMIT 5+100`이 95행 전량 반환). 둘 다 베이스라인에서도 동일하게 재현되며 각각 13.2·13.3 착수 시점으로 트리거가 지정돼 있다.
- 하이브리드 벡터절 화이트리스트는 아직 실제 호출자가 없다(13.2/13.3 그래프 배선은 이번 스토리 범위 밖). 그 사이 LLM이 그 모양을 뱉으면 가드는 통과시키고 params 없이 실행돼 400이 500으로 바뀐다(DW-559).
- `ORDER BY (embedding <=> ...)`(괄호)·복합 정렬 키 등 정규식이 인식 못하는 변형이 있으면 하이브리드 경로가 `forbidden_column`으로 막힌다(DW-555). 계획문서가 규정한 `$1::vector`·`LIMIT k` 바인드 형태도 지금 가드가 거부한다(DW-560).
- G2 baseline은 3/44 부분 캡처다(DW-554). 이제 채점 결과가 `is_partial`·`coverage`·누락 id를 명시하므로 완전한 baseline으로 오인될 수는 없지만, **실제 기준선은 아직 없다** — 44건 전량 캡처는 사용자가 쿼터를 보고 직접 실행해야 한다. 그 캡처 전에 DW-561(폴백이 실측값으로 기록됨)·DW-562(라우트 어휘 불일치)를 먼저 정리해야 한다.
- `run_phase_b.py --model` 생략은 지금은 안전하지만 13.8 재사용 시 라벨링이 오염될 수 있다(DW-556).
- `run_search()`의 unexpected-route 폴백은 라우터 원시값을 그대로 노출한다(예: "Z") — 실제 동작 그대로 테스트에 고정했다.
- **DW-315의 `location:` 줄번호가 낡았다.** 이번 변경으로 LIMIT 블록이 아래로 밀려 실제 위치는 `api/app/db/sql_guard.py`의 OFFSET 매처 이후 구간인데, 항목에 적힌 범위는 그 전 좌표다. 이번 실행에는 "기존 장부 항목을 수정하지 않는다"는 제약이 걸려 있어 손대지 않았다 — 오케스트레이터가 갱신할 몫이다.

**Residual artifacts (git status에는 보이지만 이 diff에 속하지 않아 손대지 않음):** `.bmad-loop/policy.toml`·`_bmad-output/implementation-artifacts/sprint-status.yaml`(둘 다 이 스토리 착수 전부터 수정돼 있던 오케스트레이터 소유 파일).

## Verification

**Commands:**
- `cd api && python -m pytest tests/test_sql_guard.py -q` -- expected: 전부 green. 벡터 절 정규식 스텝을 잠깐 지우고 하이브리드 케이스가 red로 바뀌는지, `limit_malformed` 분기를 잠깐 지우고 해당 케이스가 red로 바뀌는지, `embedding`을 벡터 절 밖(SELECT 목록)에 넣은 신규 회귀 테스트가 지금 이 시점(정규식 방식)엔 처음부터 green인지(위치-스코프가 실제로 동작함을 증명) 각각 확인 후 원복(B4 "잡는다"가 완료).
- **자리표시자 회귀 red→green 실측(3차 패스 신규):** 벡터절 밖 자리표시자 거부 테스트를 추가한 뒤, 일부러 `%\(\w+\)s|%s` 위치-무관 제거 스텝을 넣어 그 테스트가 **red로 바뀌는지** 확인하고 원복해 green. "그 스텝이 없어야 한다"를 검사가 실제로 잡는다는 증명 — 없으면 다음 구현이 같은 스텝을 또 넣는다(B9: 규칙은 어길 수 없는 자리에 박는다).
- **LIMIT 리터럴 하이재킹 red→green 실측(3차 패스 신규):** 매처 입력을 `no_strings`로 고치기 **전에** 신규 테스트 3케이스(`'limit 3' LIMIT 100` → `limit_exceeded` / `'limit 10'` → `LIMIT 5` 덧붙음 / `'no limit here'` → 통과)를 먼저 돌려 앞 2개가 red임을 확인하고, 고친 뒤 green으로 바뀌는지 확인. 동시에 `OFFSET` 케이스도 같은 방식으로 확인.
- `cd api && python -m pytest tests/ -q` -- expected: 전체 스위트 green(라이브 게이트 skip은 정상). 자리표시자·LIMIT 매처 변경이 기존 SQL 가드 테스트를 회귀시키지 않는지 확인 — 특히 `normalized` 반환값이 계속 리터럴을 보존하는지(리터럴이 지워진 SQL이 반환되면 실행 결과가 달라진다).
- `cd api && python -m pytest tests/test_ab_scoring.py -q` (또는 신규 `test_run_phase_b.py` 포함) -- expected: 전부 green, 라이브 호출 없음.
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres python scripts/run_phase_b.py --subset A1,B1,C1` (또는 동등한 소규모 실행) -- expected: 실제 raw JSON 생성, `score_ab.py` 1파일 모드로 채점 성공.

**Manual checks (if no CLI):**
- `deferred-work.md`에 44개 전량 라이브 캡처 항목이 `trigger:` 필드와 함께 실제로 등재됐는지 눈으로 확인.
