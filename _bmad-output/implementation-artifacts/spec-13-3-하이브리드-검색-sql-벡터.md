---
title: '13.3 하이브리드 검색 (SQL+벡터 단일쿼리)'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: '20b69679012caf1e85ca433c08edd92243ec1689'
final_revision: '4d9c2bb3ebb661ca9d75e247e2a62cc00e67ad92'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** HYBRID 라우트(13.2가 신설)는 아직 `sql_rag_node`로 임시 배선돼 있어 구조 조건만 반영하고 의미(느낌) 조건을 버린다. 실제 결합 노드가 없어 벡터절 params 미바인드(DW-559)·LIMIT/OFFSET 앵커링 결함(DW-558)·계획문서 바인드 표기 오류(DW-560)·G2 큐리셋의 legacy `A` 라벨이 올바른 HYBRID 분류를 오답으로 집계하는 문제(DW-572/575)가 모두 이 스토리 착수를 트리거로 대기 중이다.
**Approach:** LLM은 WHERE 구조조건만 생성(코드가 `ORDER BY embedding <=> %s::vector LIMIT <정수>`를 붙임, I4)하는 신규 `hybrid_rag_node`를 만들어 HYBRID를 실제 결합 경로로 재배선한다. 구조조건 미추출 시 `doc_rag_node`로 폴백(재사용, 회귀 없음). sql_guard의 LIMIT/OFFSET 앵커링을 하드닝하고, score_ab.py의 route_ok 번역을 확장해 G2 채점을 바로잡는다.

## Boundaries & Constraints

**Always:**
- 벡터절은 LLM이 아니라 **코드**가 정확히 `ORDER BY embedding <=> %s::vector LIMIT <정수 리터럴>` 모양으로 붙인다(13.1 정규식과 동일 모양·위치, 별칭·2차 정렬키 없음 — DW-555는 이 결정으로 닫는다). LLM은 WHERE 구조조건 표현식만 생성하고 `SELECT`/`status`/`ORDER BY`/`LIMIT`을 언급하지 않는다.
- `run_select()` 호출 시 질의 임베딩(`embed_query`+`_vec_literal`, doc_rag_node와 동일 표현)을 `%s` 자리표시자에 실제로 바인딩한다(params 튜플, DW-559). LIMIT은 바인드하지 않고 코드가 정수 리터럴로 붙인다(DW-560, 가드가 `LIMIT %s`를 거부).
- LLM이 구조조건을 하나도 못 뽑으면(순수 용도·느낌만 있는 질의) `doc_rag_node(query)`를 그대로 호출해 폴백한다(기존 벡터검색 재사용, 회귀 없음 — 아키텍처 명시 요구).
- 조립된 SQL은 항상 `sql_guard.validate_select_sql()`을 거친다(LLM 생성 텍스트를 신뢰하지 않는다, 함정 #1). 가드 차단 시 sql_rag_node와 동일한 1회 재생성 재시도 패턴을 따른다.
- `sql_guard`의 LIMIT/OFFSET 파싱을 bare-integer 전체 앵커링으로 교체한다(DW-558) — `LIMIT 5+100`·`OFFSET 5 (999999)`·`OFFSET 500+600`·`LIMIT 10, 5`·이중 `LIMIT` 같은 형태는 전부 `limit_malformed`/신규 `offset_malformed`로 명시 거부한다. 정상 `LIMIT n`·`LIMIT n OFFSET m`은 회귀 없이 통과한다.
- `score_ab.py`의 `route_ok()`는 legacy `primary`/`acceptable` 값 `"A"`를 신어휘 `{"SQL","HYBRID"}` 집합으로 번역해 비교한다(DW-572/575 — 13.2의 taxonomy 분리로 legacy `A` 44개 중 일부가 실제로는 HYBRID가 맞기 때문). `captured_route()`·`_require_legacy_paths()`(actual 번역, 큐리셋 어휘 검증)는 손대지 않는다. `api/docs/ai-ab-test-queryset.json` 데이터는 이번에도 수정하지 않는다(13.2 Never 절 승계).
- `graph.py`의 HYBRID 분기는 `sql`(sql_rag_node)이 아니라 신규 `hybrid`(hybrid_rag_node)로 간다. SQL 분기는 그대로 sql_rag_node.

**Block If:**
- 로컬 Supabase+`GEMINI_API_KEY`로 대표 조합형 질의(예: "3천만원 이하로 무난한 패밀리카") 3~5개를 직접 실행했을 때 단일 쿼리 조립이 매번 가드 차단되거나 psycopg 실행 오류가 나고, 재시도 프롬프트 조정으로도 해소되지 않으면 HALT(status blocked, blocking condition `하이브리드 단일쿼리 조립 실패 — 프롬프트 조정으로 해소 안 됨`).

**Never:**
- `narrowed_by`·`clarify` 등 `SearchResponse`/`/ai/search` 공개 계약 필드는 추가하지 않는다(13.5/13.6 소관).
- 13.4(되묻기 UX)·13.5(거절 템플릿)는 손대지 않는다.
- 큐리셋에 HYBRID golden 예시를 신규로 추가하지 않는다(DW-571 — 큐리셋 수정 금지 승계와 `_require_legacy_paths`의 전량-마이그레이션 강제를 피하기 위해, 결과집합 자동채점 대신 라이브 스모크로 HYBRID 동작을 검증하는 쪽을 택한다. 이 결정으로 DW-571을 닫는다).
- `api/tests/demo_queries.py`·`api/docs/ai-demo-queries.md`(DW-573/576)는 이번 스토리가 손대는 파일이 아니므로 건드리지 않는다.
- `sql_guard`의 `_conjunct_is_bare_status_on_sale` 동치-표현 관대화(DW-574)는 이번엔 하지 않는다 — 라이브 스모크로 실제 등장 형태만 관측해 기록한다(코드 변경 없음).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 조합형(구조+의미) | "3천만원 이하로 무난한 패밀리카" | route=HYBRID, 단일 쿼리(`status='on_sale' AND price<=... ORDER BY embedding<=>%s::vector LIMIT 5`) 실행, params에 임베딩 바인딩 | No error |
| 구조조건 미추출 | "패밀리카로 무난한 거"(HYBRID로 오분류됐다고 가정) | LLM이 `NONE` 출력 → `doc_rag_node(query)`로 폴백, 기존 B와 동일 답변 | No error |
| 가드 차단 후 재생성 성공 | LLM이 1차로 허용 안 된 컬럼 언급 | 1회 재생성 후 통과 | No error |
| 가드 차단 지속 | 2회 모두 차단 | `SqlGuardError` 그대로 상위 전파 | 400 한국어 안내 |
| LIMIT 우회 시도 | `... LIMIT 5+100` | `limit_malformed` 거부(red→green, DW-558) | 400 |
| OFFSET 우회 시도 | `... OFFSET 5 (999999)` | `offset_malformed` 거부(신규, DW-558) | 400 |
| G2 legacy 라벨 번역 | `route_ok(actual="HYBRID", primary="A", acceptable=["A"])` | True(집합 번역 후 매칭, DW-572) | No error |

</intent-contract>

## Code Map

- `api/app/graph/sql_rag_node.py` -- `_SYSTEM_PROMPT`의 스키마·enum·단위정규화·차형·옵션 규칙 블록을 `_DOMAIN_RULES` 모듈 상수로 추출(순수 리팩터, 동작 변화 없음) — hybrid_rag_node가 재사용.
- `api/app/graph/hybrid_rag_node.py` -- 신규. 조합형 노드: LLM 구조조건 추출 → 폴백/조립 → sql_guard 검증 → 임베딩 바인딩 실행.
- `api/app/graph/graph.py` -- HYBRID 분기를 `hybrid_rag_node`로 재배선(`_hybrid_step` 신설, `add_conditional_edges`·`add_edge` 갱신).
- `api/app/graph/doc_rag_node.py` -- 변경 없음(hybrid_rag_node가 함수만 import해 재사용).
- `api/app/db/sql_guard.py` -- LIMIT/OFFSET 검사를 bare-integer 전체 앵커링으로 교체(`offset_malformed` 신설), DW-555 결정 근거를 주석에 남김.
- `api/scripts/score_ab.py` -- `route_ok()`의 primary/acceptable 번역을 legacy `A`→`{"SQL","HYBRID"}` 집합 매핑으로 확장.
- `api/tests/test_hybrid_rag_node.py` -- 신규 단위 테스트.
- `api/tests/test_sql_guard.py` -- DW-558 회귀.
- `api/tests/test_graph.py` -- HYBRID 배선 테스트 교체.
- `api/tests/test_ab_scoring.py` -- route_ok 확장 회귀.
- `api/tests/test_live_smoke.py` -- route 단언 추가 + HYBRID 신규 케이스.
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`, `architecture-increment-2026-07-12.md` -- `$1::vector`→`%s::vector`, LIMIT 바인드 서술 정정(DW-560, 5줄).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-555·558·559·560·571·572·575 closed, DW-574 측정치 갱신(open 유지).

## Tasks & Acceptance

**Execution:**
- `api/app/graph/sql_rag_node.py` -- `_SYSTEM_PROMPT`의 `[스키마]`·`[단위 정규화]`·`[차형 용어 매핑]`·`[옵션 필터]` 4블록을 `_DOMAIN_RULES` 상수로 추출하고 `_SYSTEM_PROMPT`가 그걸 f-string으로 포함하도록 교체(문자열 내용 불변, 기존 sql_rag_node 테스트 회귀 없음).
- `api/app/graph/hybrid_rag_node.py` -- `hybrid_rag_node(query: str) -> dict` 신설:
  - 시스템 프롬프트 = `_DOMAIN_RULES` + "구조조건만 뽑아 WHERE 표현식 한 줄로 출력, 없으면 정확히 `NONE`, status·SELECT·ORDER BY·LIMIT 언급 금지, OR 금지" 규칙.
  - LLM 응답을 `_strip_sql`류로 정리(sql_rag_node의 `_content_to_text`/`_strip_sql` import해 재사용).
  - 조건이 `NONE`(대소문자 무관, 공백 트림)이면 `doc_rag_node(query)`를 그대로 반환(폴백).
  - 아니면 `f"SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND ({conditions}) ORDER BY embedding <=> %s::vector LIMIT {DEFAULT_LIMIT}"` 조립 → `validate_select_sql()` 검증(차단 시 sql_rag_node와 동일하게 오류를 대화에 덧붙여 1회 재생성, 2회째도 차단이면 `SqlGuardError` 그대로 raise).
  - 통과하면 `embed_query(query)` → `_vec_literal`(doc_rag_node와 동일 로직, 3줄 중복 허용) → `run_select(safe_sql, (qvec,))`(DW-559) → `attach_cover_images(rows_to_cards(...))`.
  - 답변 문구는 sql_rag_node와 동일 톤("조건에 맞는 매물 {n}건을 찾았어요."/0건 안내)으로 이 파일 내 상수로 둔다(작은 중복 허용, 프로젝트 관례).
- `api/app/graph/graph.py` -- `hybrid_rag_node` import, `_hybrid_step(state)` 신설(`sql_rag_node` 대신 `hybrid_rag_node` 호출, SqlGuardError 전파는 `_sql_step`과 동일하게 감싸지 않는다), `g.add_node("hybrid", _hybrid_step)`·`g.add_edge("hybrid", "answer")` 추가, `add_conditional_edges`의 `"HYBRID"` 매핑을 `"sql"`→`"hybrid"`로 교체, 모듈·함수 docstring 갱신.
- `api/app/db/sql_guard.py` -- LIMIT 검사를 `\blimit\s+([-+]?\d+)\s*(?=$|\s+offset\b)`류로 전체 앵커링(뒤에 OFFSET 절이나 문장 끝만 허용), 매치 실패인데 `limit` 키워드가 있으면 기존처럼 `limit_malformed`. OFFSET도 대칭으로 앵커링해 매치 실패 시 신규 `offset_malformed` raise. 주석에 "DW-555: 13.3은 별칭·2차 정렬 없이 정확히 이 모양만 쓰므로 기존 정규식 확장 불필요, 확인 완료"를 남긴다.
- `api/scripts/score_ab.py` -- `route_ok()` 내부에 `_LEGACY_ROUTE_ALIASES_SET = {"A": {"SQL", "HYBRID"}, "B": {"CLARIFY"}, "C": {"REJECT"}}`를 추가하고, `primary`/`acceptable` 각 값을 이 집합 매핑(없으면 `{v}`)으로 번역해 합집합과 `actual`을 비교하도록 교체. `_LEGACY_ROUTE_ALIASES`(1:1)는 `captured_route`/`_require_legacy_paths` 전용으로 그대로 둔다.
- `api/tests/test_hybrid_rag_node.py` -- (1) 조립 SQL이 기대 모양인지(문자열 검증), (2) `NONE` 응답 시 `doc_rag_node`가 정확히 1회 호출되고 그 반환값이 그대로 나오는지(monkeypatch), (3) 가드 차단 1회 후 재생성 성공 경로, (4) 2회 연속 차단 시 `SqlGuardError` 전파, (5) `run_select`가 `(qvec,)` params와 함께 호출되는지(배선 검사, listing_cards 테스트 패턴 준용).
- `api/tests/test_sql_guard.py` -- DW-558 6형태(`LIMIT 5+100`·`LIMIT 10, 5`·`LIMIT 5 LIMIT 999`·`OFFSET 5 (999999)`·`OFFSET 500+600`·`LIMIT (10)`) 전부 거부 회귀(일부는 기존 `limit_malformed` 테스트 재사용) + `LIMIT 5`·`LIMIT 5 OFFSET 10` 정상 통과 회귀.
- `api/tests/test_graph.py` -- `test_route_HYBRID_calls_sql_only`를 `test_route_HYBRID_calls_hybrid_only`로 교체(hybrid_rag_node만 호출되고 sql_rag_node는 호출 안 됨을 확인), docstring의 "13.3 전까지" 표현 정정.
- `api/tests/test_ab_scoring.py` -- `route_ok("HYBRID","A",["A"])`·`route_ok("SQL","A",["A"])` 둘 다 True, `route_ok("CLARIFY","A",["A"])`는 여전히 False임을 확인하는 회귀 추가.
- `api/tests/test_live_smoke.py` -- `test_live_smoke_pathA/pathB/pathC`에 `assert out["route"] == "SQL"/"CLARIFY"/"REJECT"` 추가, `test_live_smoke_hybrid` 신설("3천만원 이하로 무난한 패밀리카", `route == "HYBRID"` 단언).
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(119·982·1011행), `architecture-increment-2026-07-12.md`(195·382행) -- `$1::vector`→`%s::vector`, "LIMIT k 바인드 파라미터로 덧붙임"→"LIMIT k는 코드가 정수 리터럴로 붙임"으로 표기 정정(DW-560).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-555·558·559·560·571·572·575를 이번 스토리 근거·resolution과 함께 `status: closed`로. DW-574는 라이브 스모크에서 관측한 실제 WHERE 조건 형태를 근거로 실측 결과만 추가하고 `status: open` 유지(코드 변경 없음이므로 닫지 않는다).

**Acceptance Criteria:**
- Given 구조+의미 조합 질의, when `hybrid_rag_node`가 처리하면, then 단일 SQL(`status='on_sale' AND <구조조건> ORDER BY embedding <=> %s::vector LIMIT 5`)이 조립되고 `run_select`가 임베딩을 params로 받아 실행된다(직접 로컬 실행으로 확인, B4).
- Given LLM이 구조조건을 못 뽑는 질의, when `hybrid_rag_node`가 처리하면, then `doc_rag_node`와 동일한 답변·매물이 반환된다(폴백 회귀 없음).
- Given 가드가 2회 연속 차단하는 조건, when `hybrid_rag_node`가 처리하면, then `SqlGuardError`가 그대로 `/ai/search`까지 전파돼 400이 된다(500 아님, sql_rag_node와 동일 계약).
- Given `LIMIT 5+100`·`OFFSET 5 (999999)` 등 DW-558의 6개 우회 형태, when `validate_select_sql()`로 검증하면, then 전부 거부된다(red→green 실측).
- Given 정상 `LIMIT n`·`LIMIT n OFFSET m`, when 검증하면, then 회귀 없이 통과한다.
- Given G2 큐리셋의 legacy `primary_path="A"`, when 실제 route가 `HYBRID`로 캡처되면, then `route_ok()`가 True를 반환한다(DW-572) — 반대로 `primary_path="B"`인데 actual이 `SQL`이면 여전히 False다(집합 번역이 다른 카테고리까지 느슨해지지 않음을 함께 확인).
- Given 로컬 Supabase+`GEMINI_API_KEY`, when 대표 조합형 질의 3~5개로 라이브 스모크를 실행하면, then 매번 HYBRID로 분류되고 매물(또는 FR17 0건 안내)이 반환되며 G1이 위반되지 않는다(직접 실행·관찰, B4).
- Given 이번 스토리 완료, when `deferred-work.md`를 확인하면, then DW-555·558·559·560·571·572·575가 근거와 함께 closed이고 DW-574가 실측 갱신돼 있다(B8).

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 3, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[high]` `[patch]` `api/app/graph/hybrid_rag_node.py` — LLM이 뽑은 구조조건에 `LIKE '%아반떼%'`류 리터럴 `%`가 섞이면 sql_guard는 통과시키지만(문자열 리터럴 내부라 컬럼 화이트리스트 검사에서 안 보임) `run_select()`가 처음으로 params를 실제 바인딩하는 이번 스토리 변경 때문에 psycopg가 그 `%`를 자리표시자로 오인해 `ProgrammingError`/한글이면 `UnicodeDecodeError`까지 던진다(blind-hunter·edge-case-hunter·verification-gap 3개 레이어가 독립 발견, 오케스트레이터가 psycopg 3.3.4 내부 함수로 직접 재현 확인). `except SqlGuardError`가 못 잡아 400 대신 500이 된다 — DW-559가 막으려던 것과 같은 부류의 회귀가 다른 경로로 재발.
  - `[medium]` `[patch]` `api/app/graph/hybrid_rag_node.py` — 폴백 판정이 정확히 `"NONE"` 문자열만 보고, LLM이 빈/공백 응답을 내면 `AND ()`라는 문법 오류 SQL이 가드는 통과(다른 AND 결합항인 `status='on_sale'`가 이미 조건을 만족시켜 버림)한 뒤 DB 실행 단계에서 죽는다(blind-hunter·edge-case-hunter 독립 발견).
  - `[medium]` `[patch]` `api/app/graph/sql_rag_node.py` — `_DOMAIN_RULES` 추출 리팩터가 "동작 변화 없음"이라 주석에 적었지만 실제로는 블록 순서가 바뀌었고(원래 "[불변 규칙]" 뒤 → 지금 앞), 이미 운영 중인 경로 A의 LLM 프롬프트 구조 변화가 재확인 없이 선언됐다(blind-hunter·verification-gap 독립 발견, B4 위반 소지).
  - `[medium]` `[patch]` `api/tests/test_graph.py` — HYBRID 경로도 `_sql_step`과 동일하게 `SqlGuardError`를 삼키지 않는다고 `_hybrid_step` 독스트링이 명시하지만, 그 불변식을 그래프 레벨에서 확인하는 짝 테스트(`test_sql_guard_error_propagates_out_of_graph`의 HYBRID 버전)가 없다(verification-gap 발견).
  - `[low]` `[patch]` `api/app/db/sql_guard.py` — 이번 diff가 새로 삽입한 LIMIT/OFFSET 중복 금지 단계 때문에 뒤 단계 번호가 밀리며 기존 번호와 새로 충돌한다(blind-hunter 발견). diff 이전부터 있던 "4)" 중복(OR 금지/FR11)은 이번 스토리 원인이 아니므로 A3에 따라 손대지 않고, 이번 diff가 새로 만든 충돌만 재번호한다.
  - defer 1건(장부 신규 등재): `assert last_error is not None`을 제어 흐름으로 쓰는 패턴(`-O` 최적화 실행 시 사라지는 실행되지 않는 방어) — sql_rag_node.py에 이미 있던 사전 존재 패턴을 hybrid_rag_node.py가 스펙 지시대로("sql_rag_node와 동일 패턴") 그대로 재현한 것이라 이번 스토리가 새로 만든 결함은 아니다(blind-hunter 발견).
  - reject 사유: HYBRID LIMIT이 "더 보여줘" 요청과 무관하게 항상 5로 고정된 것(blind-hunter)은 스펙 Design Notes가 명시적으로 선택한 단순화(코드가 정수 리터럴을 붙인다)이지 결함이 아니다 · `route_ok` 집합 번역이 legacy `A` 44건 전체에 적용된다는 지적(blind-hunter)은 스펙 Design Notes가 이미 "알려진 트레이드오프"로 명시·공개한 내용이라 새로운 결함이 아니다 · `_vec_literal`·답변 문구 3~4줄 중복(blind-hunter)은 스펙 Tasks가 명시적으로 허용한 프로젝트 관례(CLAUDE.md A2)다 · deferred-work.md의 "5건 라이브 확인" 문구가 `%` 케이스를 안 다뤘다는 지적(blind-hunter)은 위 high 항목 수정으로 해당 실패 클래스 자체가 사라지고, 문구도 실제 테스트한 5건만 정확히 나열해 과장이 아니다.

## Design Notes

**하이브리드 조립을 가드 통과 후가 아니라 통과 "직전"에 완성한다.** LLM은 조건 표현식만 내고, 코드가 `status='on_sale' AND (<조건>) ORDER BY embedding <=> %s::vector LIMIT 5`까지 전부 문자열로 합친 뒤에야 `validate_select_sql()`을 부른다 — 그래야 가드의 LIMIT 리터럴 검사가 이미 붙어 있는 숫자를 보고 통과시키고(별도 주입 로직을 다시 타지 않음), 벡터절 정규식도 정확히 설계된 위치(문장 끝 직전)에서만 매치한다. 가드를 먼저 부르고 나중에 벡터절을 이어붙이면 정규식이 못 보는 위치에 결합돼 버려 embedding/vector가 미화이트리스트 식별자로 거부된다.

**폴백은 새 SQL을 쓰지 않고 `doc_rag_node`를 그대로 호출한다.** 아키텍처가 요구하는 "구조조건 미추출 시 기존 벡터검색 유지"를 코드 재사용으로 만족시킨다 — 별도 폴백 SQL을 새로 쓰면 doc_rag_node와 두 벌의 유사(코사인) 검색 로직이 생겨 그중 하나가 드리프트할 위험이 생긴다.

**route_ok 집합 번역은 legacy `A`에만 적용한다.** `B`(→CLARIFY)·`C`(→REJECT)는 13.2에서 이미 taxonomy가 안 갈라졌으므로 1개 값 그대로 둔다. 이 확장이 "진짜 SQL을 HYBRID로 오분류"하는 버그를 가려버릴 여지(legacy `A` 44개 중 구조전용 항목도 이제 `HYBRID` actual을 허용)는 알려진 트레이드오프다 — 큐리셋을 안 건드리는 쪽을 우선했다(13.2 Never 승계).

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/ -x -q` -- expected: 전량 통과(신규 테스트 포함).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -x -q` -- expected: 4개 라우트 전부 통과, HYBRID가 실제로 관측됨.

**Manual checks (if no CLI):**
- `validate_select_sql()`에 DW-558의 6개 우회 SQL을 직접 넣어 거부되는지, 정상 SQL 2개가 통과하는지 눈으로 확인(red→green 캡처).

## Auto Run Result

**Status:** done

**Summary:** HYBRID 라우트를 임시 배선(sql_rag_node 재사용)에서 실제 SQL+벡터 단일쿼리 결합 노드(`hybrid_rag_node`)로 교체했다. LLM은 WHERE 구조조건만 생성하고, 코드가 `ORDER BY embedding <=> %s::vector LIMIT 5`를 붙여 조립·검증(sql_guard)·실행(임베딩 params 바인딩)한다. 구조조건 미추출 시 `doc_rag_node`로 폴백. 함께 처리한 이월 과제: sql_guard LIMIT/OFFSET bare-integer 앵커링(DW-558), G2 채점기의 legacy `A` 라벨 확장 번역(DW-572/575), 계획문서 바인드 표기 정정(DW-560).

**Files changed:**
- `api/app/graph/hybrid_rag_node.py`(신규) -- 조합형 노드: 구조조건 추출·조립·가드·실행.
- `api/app/graph/sql_rag_node.py` -- `_SCHEMA_RULES`/`_UNIT_AND_FILTER_RULES`/`_DOMAIN_RULES` 추출(리뷰 패치로 원래 프롬프트 블록 순서를 문자 그대로 보존).
- `api/app/graph/graph.py` -- HYBRID 분기를 `hybrid_rag_node`로 재배선.
- `api/app/db/sql_guard.py` -- LIMIT/OFFSET 전체 앵커링 + 중복절 거부(DW-558), 신규 `offset_malformed`, 주석 번호 재정리(리뷰 패치).
- `api/scripts/score_ab.py` -- `route_ok()`가 legacy `A`를 `{SQL,HYBRID}` 집합으로 번역(DW-572/575).
- `api/tests/test_hybrid_rag_node.py`(신규), `test_sql_guard.py`, `test_graph.py`, `test_ab_scoring.py`, `test_live_smoke.py`, `test_sql_rag_node.py`, `test_demo_acceptance.py` -- 신규·보강 테스트(리뷰 패치로 3건 추가: 빈조건 폴백, `%` 이스케이프, 프롬프트 순서 고정, HYBRID 그래프 레벨 SqlGuardError 전파).
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`, `architecture-increment-2026-07-12.md` -- `$1::vector`→`%s::vector` 표기 정정(DW-560).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-555·558·559·560·571·572·575 closed, DW-574 실측 갱신(open 유지), DW-579 신규 등재(리뷰 defer).

**Review findings breakdown:** patch 5건(high 1·medium 3·low 1) 전부 적용·재검증 완료. defer 1건(DW-579) 장부 등재. reject 4건(스펙이 이미 명시적으로 결정했거나 프로젝트 관례로 허용된 트레이드오프 — Review Triage Log 참조).

**Follow-up review recommendation:** true (patch 심각도 1×high 존재 — 계산식과 무관하게 high 1건만으로 true).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -q` → 330 passed, 83 skipped(재검증 완료, 패치 적용 후 재실행).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -q` → 4 passed(SQL/CLARIFY/REJECT/HYBRID 4개 라우트 전부 실측 관측, 패치 적용 후 재실행).
- DW-558 6개 우회 SQL 직접 재현(수정 전 통과 확인 → 수정 후 거부 확인, red→green).
- `%` 이스케이프 수정을 psycopg 내부 함수(`_query2pg_nocache`)로 직접 재현해 크래시 없이 단일 placeholder만 남고 리터럴이 원래 값으로 복원됨을 확인.
- `sql_rag_node._SYSTEM_PROMPT`가 리팩터 전 원본과 문자 그대로 동일함을 직접 렌더링 비교로 확인(추측 아님).

**Residual risks:**
- `route_ok`의 legacy `A`→`{SQL,HYBRID}` 집합 번역은 큐리셋 44건 전체에 적용돼, "진짜 SQL을 HYBRID로 오분류"하는 미래 회귀를 legacy `A` 항목에 한해 못 잡을 수 있다(스펙 Design Notes가 명시한 트레이드오프).
- `assert last_error is not None` 제어흐름 패턴(sql_rag_node·hybrid_rag_node 공통)이 `-O` 최적화 실행 시 사라지는 방어라는 점은 DW-579로 남겨뒀다(이번 스토리가 새로 만든 결함은 아님).
- `epic-13-context.md`에도 `$1::vector` 옛 표기가 남아있으나 이번 스펙의 Code Map 대상이 아니라 손대지 않았다(DW-560 resolution에 기록).
