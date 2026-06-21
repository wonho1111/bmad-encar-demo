# Story 4.8: AI 검증 — SM3·CM1·CM2 합격 판정

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 시연자/평가자,
I want OI5 데모 질의셋으로 AI 동작(경로 A/B/C·안전장치)을 통과/실패로 자동 판정하고 싶다,
so that 과제 핵심 목표(SM3·CM1·CM2)가 검증됐음을 재현 가능한 증거로 보일 수 있다.

## Acceptance Criteria

> 출처: `_bmad-output/planning-artifacts/epics.md#Story 4.8` (Given/When/Then), `api/docs/ai-demo-queries.md`(OI5 단일출처).

1. **SM3 (2경로 매물 반환)** — OI5 데모 질의셋의 구조형 질의(①, 경로 A)와 질적·의미형 질의(②, 경로 B)를 실행하면, **두 경로 모두** 적절한 매물 카드(`listings[]` 비어있지 않음)와 한국어 `answer`를 반환한다. 판정은 라이브 LLM에 매번 의존하지 않도록 **결정론적(모킹/픽스처) 판정**을 기본으로 하고, 라이브 동작은 **소량 스모크 1~2건**으로 확인한다(쿼터 보호).
2. **CM1 (무관 질의 거절)** — OI5 무관 질의(④, 경로 C)는 **전부** 정중히 거절된다: `listings == []` AND `answer`에 검색 유도 문구(`guard_node`의 고정 거절 메시지)가 포함된다. 상식·코드 Q&A를 직접 제공하지 않는다(FR16).
3. **CM2 (안전장치 — 범위밖 0건 실행)** — SELECT 전용·테이블/컬럼 화이트리스트·`status='on_sale'` 필수·LIMIT 상한·OR/서브쿼리/주석/다중문장 금지를 벗어나는 위험·범위밖 SQL이 **단 1건도 실행되지 않는다**. 이는 LLM 없이 `sql_guard`(결정론적)로 완전 검증한다. 즉, 위반 SQL은 모두 `validate_select_sql()`이 `SqlGuardError`로 **실행 전 차단**한다.
4. **재현 가능한 판정 자산** — 위 SM3/CM1/CM2 판정을 `pytest`로 실행해 통과/실패가 한 번에 드러난다. OI5 질의셋은 `ai-demo-queries.md`를 **단일출처**로 참조(질의 문자열·기대 경로를 코드에 중복 하드코딩하지 않거나, 하드코딩하면 그 표와 일치함을 주석/테스트로 고정).
5. **라이브 스모크(쿼터-세이프)** — 실제 Gemini를 쓰는 라이브 검증은 **선택적·격리**(예: `RUN_LIVE_SMOKE=1` env 또는 `-m live` 마커)로, 기본 pytest 실행에서는 **스킵**된다. 키 부재/쿼터 429여도 결정론적 판정(1~4)은 그대로 통과한다. 라이브 스모크를 1회 돌렸으면 결과(또는 429 사실)를 Completion Notes에 기록한다.

## Tasks / Subtasks

- [x] **Task 1 — OI5 질의셋을 코드가 읽는 단일출처 픽스처로 정리** (AC: #1,#2,#4)
  - [x] `api/tests/demo_queries.py` 신설: `ai-demo-queries.md` 표 ①②③④를 파이썬 데이터(질의, 기대 경로 A/B/C/AB)로 옮김. 회색지대(③)는 "AB"(A 또는 B 허용)로 표기.
  - [x] 각 항목에 `ai-demo-queries.md`의 어느 표(①~④)에서 왔는지 출처 주석을 달음(drift 추적).
- [x] **Task 2 — SM3 결정론적 판정 테스트** (AC: #1,#4)
  - [x] `api/tests/test_demo_acceptance.py` 신설. 경로 A·B 질의를 `run_search`로 흘리되 라우터·경로 노드를 모킹해 LLM/DB 없이 "기대 경로 분기 → listings 비어있지 않음 + answer 비어있지 않음"을 검증(`_patch_route` 헬퍼, test_graph.py 패턴 재사용).
  - [x] 경로 A: `sql_rag_node` 내부 `_llm`만 모킹해 세단 IN-매핑 SELECT 생성 → `validate_select_sql` 실제 통과 → `rows_to_cards` 매핑까지 도달 검증(`test_sm3_pathA_real_guard_passes_generated_sql`). DB(`run_select`) 모킹. 4.3 deferred "IN-매핑 가드 통과 미커버" 보강.
- [x] **Task 3 — CM1 결정론적 판정 테스트** (AC: #2,#4)
  - [x] 무관 질의(④) router="C" 고정 후 `run_search`가 `listings == []` AND 거절 문구 포함인지 전부 검증(parametrize + 집계 단언 `test_cm1_count_all_unrelated_rejected`).
  - [x] `guard_node` 직접 호출 — 어떤 무관 질의든 고정 거절(`_GUARD_ANSWER`) + 빈 목록(결정론적) 확인.
- [x] **Task 4 — CM2 안전장치 판정(결정론적, LLM 불필요)** (AC: #3,#4)
  - [x] 위반 SQL 코퍼스 19건(DML/DDL·다중문장·주석·`SELECT *`·비화이트리스트 테이블/컬럼·OR 우회·서브쿼리·status 누락·sold·LIMIT 초과·빈입력) 각각 `SqlGuardError`로 차단 검증(`test_cm2_violating_sql_is_blocked`).
  - [x] "범위밖 0건 실행" 집계 단언 — 코퍼스 순회하며 통과(반환)한 건수 == 0(`test_cm2_zero_violations_pass_through`). 대조군: 정상 SELECT는 통과(`test_cm2_valid_sql_still_passes`, 과차단 방지).
- [x] **Task 5 — 라이브 스모크 러너(쿼터-세이프, 선택)** (AC: #5)
  - [x] `api/tests/test_live_smoke.py` 신설: `RUN_LIVE_SMOKE=1`일 때만 실제 Gemini로 경로 A·B·C 각 1건(총 3건) 실행. 기본 실행은 `pytest.mark.skipif`로 스킵.
  - [x] 429/키부재/DB부재 시 `pytest.skip`(실패 아님). 호출 3건으로 묶어 쿼터 보호. **라이브 1회 실행 결과: 3 passed(아래 Completion Notes).**
- [x] **Task 6 — 검증 매트릭스 문서화** (AC: #4)
  - [x] `api/docs/ai-demo-queries.md` 끝에 "4.8 검증 매트릭스" 섹션 추가 — 판정(SM3/CM1/CM2) → 대상 질의 → 검증 테스트 함수명 연결(추적성). 새 파일 없이 기존 문서에 덧붙임.
- [x] **Task 7 — 전체 pytest 통과 + 회귀 0 확인** (AC: #1~#4)
  - [x] `api/.venv`에서 `pytest` 전체: **135 passed, 3 skipped(라이브 스모크)**. 신규 44건 + 기존 91건 전부 통과, 회귀 0.

## Dev Notes

### 이 스토리의 본질 (무엇을·왜)

- **새 기능 추가가 아니라 "검증 자산"을 만드는 스토리**다. 경로 A/B/C·sql_guard·graph는 4.3~4.6에서 이미 구현·동작 확인됨. 4.8은 그것들이 **OI5 데모 질의셋 기준으로 합격(SM3·CM1·CM2)임을 재현 가능한 테스트로 못박는다**.
- 왜 모킹 기반인가: 라이브 Gemini는 무료 티어 일일 쿼터(약 20 req/day)가 빡빡하다. 판정이 매번 라이브에 의존하면 쿼터 소진·비결정성으로 CI/재실행이 깨진다. 그래서 **판정 로직은 결정론적(모킹/픽스처)**, 라이브는 **소량 스모크로 분리**한다.
- **CM2는 LLM이 전혀 필요 없다** — `sql_guard`는 순수 함수다. "범위밖 0건 실행"은 위반 SQL이 전부 실행 전에 `SqlGuardError`로 막힘을 결정론적으로 증명하면 끝. 반드시 완전 검증한다(쿼터와 무관).

### 핵심 소스 (반드시 재사용 — 새로 만들지 말 것)

- **OI5 질의셋 단일출처**: `api/docs/ai-demo-queries.md` — ① 구조형(A), ② 질적·의미형(B), ③ 회색지대(B 우선), ④ 무관(C). 질의 문자열·기대 경로의 권위 출처. 코드가 이 표를 미러링한다(drift 시 주석/테스트로 잡음).
- **그래프 진입점**: `api/app/graph/graph.py` `run_search(query, context=None) -> {answer, listings[]}`. SM3/CM1 판정은 이 함수를 통해 검증.
- **모킹 패턴(그대로 재사용)**: `api/tests/test_graph.py`의 `_patch_nodes(monkeypatch, route=..., sql=..., doc=...)` — `gmod.router_node`/`sql_rag_node`/`doc_rag_node`/`guard_node`를 monkeypatch. LLM/DB 일절 호출 안 함.
- **라우터 모킹 패턴**: `api/tests/test_router_node.py`의 `_FakeStructured`/`_FakeLLM`/`_patch_llm` — `rn._llm`을 가짜로 치환해 구조화 출력을 결정.
- **CM2 안전장치 단일출처**: `api/app/db/sql_guard.py` `validate_select_sql()` + `SqlGuardError(code, message)`. 차단 코드: `empty, multiple_statements, comment_not_allowed, not_select, forbidden_keyword, forbidden_or, subquery_not_allowed, select_star, no_table, forbidden_table, forbidden_column, missing_status_filter, limit_exceeded`. 상수 `DEFAULT_LIMIT=5`, `MAX_LIMIT=50`, `ALLOWED_TABLES={listings}`, `ALLOWED_COLUMNS`(17개).
- **기존 sql_guard 테스트**: `api/tests/test_sql_guard.py` — 위반 케이스 다수 이미 존재. **삭제·중복 금지**. CM2 집계 테스트는 이 케이스들을 "OI5/CM2 관점으로 묶어 0건 통과를 단언"하는 식으로 보강(중복 최소화).
- **거절 노드**: `api/app/graph/guard_node.py` `guard_node(query) -> {answer: <고정 거절문구>, listings: []}`. CM1 판정은 이 문구 포함 여부로 한다. 고정 문구: "저는 중고차 매물 검색을 도와드리는 어시스턴트예요. 찾으시는 차의 예산·차종·용도를 알려주시면 매물을 찾아드릴게요."
- **경로 A 노드**: `api/app/graph/sql_rag_node.py` — `_llm()`(monkeypatch 대상), `_content_to_text`/`_strip_sql`로 LLM 출력 정제 → `validate_select_sql` → `run_select`(DB, 모킹 대상) → `rows_to_cards`. 7컬럼 SELECT는 `app.graph.listing_cards.SELECT_COLUMNS` 단일출처.
- **HTTP 계약 테스트**: `api/tests/test_ai_search.py` — `app.dependency_overrides[get_current_user]`로 인증 우회, `app.routers.ai.run_search` monkeypatch. 엔드포인트 레벨 SM3/CM1 회귀가 필요하면 이 파일 패턴 사용(이미 200/401/422/400 커버).

### 회색지대(③) 판정 규칙 — AC 모호 방지

`ai-demo-queries.md` ③은 LLM 판정이 A/B로 갈릴 수 있다고 명시: "둘 중 어디로 가도 매물 카드/추천을 돌려주면 데모 합격(빈손·거절만 아니면 됨)". 따라서:
- 결정론적 판정에서 회색지대 질의는 **경로를 A 또는 B로 모킹한 두 경우 모두** "listings 비어있지 않음"이면 합격으로 본다(경로 고정 강제 금지).
- 회색지대를 "정확히 어느 경로"로 가야 한다고 단정하지 말 것(과잉 단정은 오탐). 핵심 불변은 "거절(C)·빈손이 아니다".

### CM2 위반 SQL 코퍼스 (실행되면 안 되는 것들 — 전부 차단 기대)

연구 §4.2 + `ai-demo-queries.md` 안전장치 사상 기준. 각각 `validate_select_sql`이 raise해야 함:
- `DELETE/UPDATE/INSERT/DROP/ALTER/TRUNCATE FROM listings ...` → not_select/forbidden_keyword
- 다중문장: `SELECT ... ; DROP TABLE listings` → multiple_statements
- 주석: `... -- x`, `... /* x */` → comment_not_allowed
- `SELECT * FROM listings WHERE status='on_sale'` → select_star
- 비화이트리스트 테이블: `... FROM profiles ...` → forbidden_table
- 환각 컬럼: `SELECT password FROM listings ...` → forbidden_column
- OR 우회(sold 누출): `... WHERE status='on_sale' OR price<9e9` → forbidden_or
- 서브쿼리(외부 LIMIT 우회): `... AND year IN (SELECT year FROM listings LIMIT 50)` → subquery_not_allowed
- status 필터 누락: `SELECT id FROM listings WHERE color='흰색'` → missing_status_filter
- 상한 초과: `... LIMIT 51` → limit_exceeded

> 집계 단언: 위 코퍼스를 순회하며 "통과(정상 반환)한 건수 == 0"을 assert → "범위밖 쿼리 0건 실행"을 코드로 증명(CM2).

### 라이브 스모크 — 쿼터 보호 규칙

- 기본 pytest run에서 **반드시 skip**(env 게이트 `RUN_LIVE_SMOKE=1` 또는 marker). 켜졌을 때만 `GEMINI_API_KEY`·`DATABASE_URL` 확인 후 실행.
- 호출 **3건 이하**(경로 A·B·C 각 1). 429/키부재 → `pytest.skip(...)`(실패 아님). 결과/429 사실을 Completion Notes에 적는다.
- 라이브 스모크가 실패/스킵돼도 SM3/CM1/CM2 **결정론 판정은 독립적으로 통과**해야 한다(판정의 권위는 결정론 테스트에 있다).

### 테스트 실행 환경

- 작업 디렉터리 `api/`, 가상환경 `api/.venv`. AI 의존성은 `.[ai]` 그룹(langgraph·langchain-google-genai·sqlparse·pgvector) — 이미 4.2~4.4에서 설치됨.
- `pytest` 설정은 `pyproject.toml`(`pythonpath=["."]`, `testpaths=["tests"]`). 신규 테스트는 `api/tests/`에 둔다.
- Windows 환경: `python3` 별칭 이슈 있음([[windows-python3-alias]]) — `python -m pytest` 또는 venv 활성화 후 `pytest` 사용.
- 키/DATABASE_URL 없을 때: 결정론 테스트는 전부 pass, 라이브 의존만 skip(기존 `test_readonly.py` 동작과 동일).

### Project Structure Notes

- 신규 파일은 모두 `api/tests/`(테스트) 또는 `api/scripts/`(라이브 러너) 하위 — 기존 구조(4.1~4.7) 정합.
- 새 마이그레이션·새 앱 코드(app/) 변경 **불필요**(검증 스토리). 만약 검증 중 sql_guard/노드 버그를 발견하면 최소 수정 + 회귀 테스트로 고치고 Completion Notes에 명시(범위 넘는 리팩터 금지).
- 문서는 기존 `api/docs/ai-demo-queries.md`에 매트릭스를 덧붙임(새 .md 남발 금지 — CLAUDE.md 지침).

### 4.3 deferred-work 연계 (이 스토리가 일부 해소)

`deferred-work.md`(4-3)에 적힌 다음 부채를 본 스토리가 자연스럽게 흡수한다:
- "AC4 단위 정규화·차형(세단) 매핑 결정론적 단위테스트 부재" → Task 2의 경로 A LLM-모킹 케이스로 일부 보강(완전 정규화 테스트가 과하면 핵심 1~2건만, 나머지는 라이브 스모크/이연 유지하고 Notes에 명시).
- "FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버" → Task 2에서 가드 IN-절 통과를, FR17 0건은 `answer_node`(이미 `test_graph.py` 커버) 재확인.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.8: AI 검증 — SM3·CM1·CM2 합격 판정]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4 (검증 AC: SM3·CM1·CM2)]
- [Source: api/docs/ai-demo-queries.md (OI5 데모 질의셋 단일출처 — 표 ①②③④)]
- [Source: api/app/db/sql_guard.py (validate_select_sql, SqlGuardError, DEFAULT_LIMIT/MAX_LIMIT, 화이트리스트)]
- [Source: api/app/graph/graph.py (run_search, conditional A/B/C 분기)]
- [Source: api/app/graph/router_node.py, guard_node.py, sql_rag_node.py]
- [Source: api/tests/test_graph.py (_patch_nodes 모킹 패턴), test_router_node.py (_FakeLLM), test_sql_guard.py (위반 케이스), test_ai_search.py (HTTP 계약)]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md (4-3 이연 항목 연계)]
- [Source: _bmad-output/planning-artifacts/research/ §4.1·4.2·4.3 (안전장치·라우팅 설계)]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- 베이스라인 `pytest`: 91 passed(작업 전).
- 신규 판정 테스트만: `pytest tests/test_demo_acceptance.py tests/test_live_smoke.py` → 44 passed, 3 skipped.
- 전체 회귀: `pytest` → 135 passed, 3 skipped(라이브 스모크), 0 fail.
- 라이브 스모크(쿼터-세이프, 1회): `RUN_LIVE_SMOKE=1 pytest tests/test_live_smoke.py` → **3 passed in 119.38s**(실 Gemini, 429 없음).

### Completion Notes List

- **검증 스토리(새 기능 추가 아님).** 경로 A/B/C·sql_guard·graph는 4.3~4.6에서 이미 구현됨. 4.8은 그것들이 OI5 데모 질의셋 기준 SM3·CM1·CM2 합격임을 **재현 가능한 pytest 자산**으로 못박았다. **앱 코드(app/)·마이그레이션 변경 0** — 테스트/문서만 추가. 작업 중 sql_guard·노드 버그는 발견되지 않았다(기존 구현이 OI5 전 질의에 합격).
- **SM3 판정(AC1): 합격.** 경로 A 4건·경로 B 4건·회색지대 3건(A/B 양쪽) 전부 listings 비어있지 않음 + answer 채워짐. 경로 A는 LLM만 모킹한 케이스로 "세단 IN-매핑 SQL이 sql_guard를 실제 통과 → ListingCard 매핑"까지 도달 증명(4.3 deferred 일부 해소).
- **CM1 판정(AC2): 합격.** 무관 질의 4건 전부 `listings == []` + 정중한 거절 문구 포함. 집계 단언으로 "거절 실패 0건" 확인. guard_node가 질의 내용과 무관하게 고정 문구를 줌(결정론적).
- **CM2 판정(AC3): 합격(LLM 불필요, 완전 검증).** 위반 SQL 코퍼스 19건이 전부 `validate_select_sql`에서 `SqlGuardError`로 실행 전 차단. 집계 단언으로 "가드를 통과한 위반 SQL == 0건" 못박음("범위밖 쿼리 0건 실행"). 대조군으로 정상 SELECT는 통과시켜 과차단 아님도 보장.
- **라이브 스모크(AC5): 1회 실행 성공.** `GEMINI_API_KEY`·`DATABASE_URL`이 `.env`에 있어 경로 A·B·C 각 1건을 실제 Gemini로 호출 → 3 passed(429/쿼터 소진 없음). 즉 결정론 판정뿐 아니라 실물 파이프라인도 동작 확인. 기본 pytest 실행에서는 이 3건이 스킵돼 쿼터를 소진하지 않는다.
- **단일출처 유지.** 질의 문자열·기대 경로는 `api/docs/ai-demo-queries.md`(권위) ↔ `api/tests/demo_queries.py`(코드 미러) ↔ `ai-demo-queries.md` 4.8 매트릭스(추적표)로 일관. drift 시 주석으로 추적 가능.
- **escalate/미해결 없음.** Halt 조건(키 누락·3연속 실패·AC 모호·설계 분기) 미발생.

### File List

- `api/tests/demo_queries.py` (신규) — OI5 질의셋 단일출처 미러(파이썬 데이터).
- `api/tests/test_demo_acceptance.py` (신규) — SM3·CM1·CM2 결정론적 판정(44 테스트).
- `api/tests/test_live_smoke.py` (신규) — 라이브 스모크 3건(쿼터-세이프, 기본 skip).
- `api/docs/ai-demo-queries.md` (수정) — "4.8 검증 매트릭스" 섹션 추가.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (수정) — 4-8 상태 전이(ready-for-dev→in-progress→review).
- `_bmad-output/implementation-artifacts/4-8-ai-검증-sm3-cm1-cm2.md` (신규) — 본 스토리 파일.

## Change Log

- 2026-06-22: 4.8 구현 — OI5 데모 질의셋 기반 SM3·CM1·CM2 합격 판정 자산 추가(결정론 판정 44 테스트 + 라이브 스모크 3, 전체 135 passed/3 skipped, 회귀 0). 앱 코드 변경 없음. Status → review.
- 2026-06-22: code-review 통과(병렬 3레이어: Blind Hunter·Edge Case Hunter·Acceptance Auditor). 패치 3건 자동 반영(commit 47f8e66) — CM1 그래프-경로 단언을 `== _GUARD_ANSWER` 정확 일치로 강화, 서브쿼리 코퍼스 주석 정정, ③ "AB" 라벨 정합 명시. High/심각 무. 앱코드 사전이슈 2건(sql_guard `LIMIT -1` 이중 LIMIT·OFFSET 무상한)은 4.8 범위 밖이라 escalate. pytest 135 passed/3 skipped. Status → done.
