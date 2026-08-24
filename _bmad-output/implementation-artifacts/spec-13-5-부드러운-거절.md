---
title: '13.5 부드러운 거절 (REJECT, 고정 템플릿)'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: 'f76e723fdc837857dc7e0ebf4138496008de41fb'
final_revision: '031ba1919144e74fe80fe6e2abf150de9f630bce'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** REJECT 경로(`guard_node`)의 현재 답변 문구가 EXPERIENCE.md Voice 표(FR47, 정본)와 글자가 다르고, `SearchResponse`에 `narrowed_by`가 없어 "0건·거절의 다양성은 문구 생성이 아니라 구조화 사유 데이터로"라는 CR4 계약을 이행할 수단이 없다(13.2/13.3/13.4가 `route`·`narrowed_by`를 명시적으로 13.5/13.6 소관으로 미뤄둠).
**Approach:** `guard_node`의 고정 답변을 Voice 표 문구로 정정하고, REJECT 전용의 **고정 상수** `narrowed_by`(예시 조건 술어 배열, LLM/컨텍스트 무관 — 무상태·결정론 FR47과 정합)를 만들어 `SearchState`→`answer_node`→`SearchResponse`까지 `clarify`와 동일한 패턴으로 통과시킨다. 공개 `route` 필드는 추가하지 않는다(`docs/conventions.md` §4가 13.4에서 이미 "응답에 route 필드는 없다"로 확정).

## Boundaries & Constraints

**Always:**
- `guard_node`의 고정 답변 문자열을 `EXPERIENCE.md` Voice 표의 "AI 거절(FR47, 고정)" 행과 **글자 그대로** 일치시킨다("저는 중고차 찾기를 도와드리는 차장님이에요 🚗 그건 답하기 어렵지만, 원하는 차 조건을 말씀해 주시면 딱 맞는 매물을 찾아드릴게요.") — LLM 재작성 없음, 질의 내용과 무관하게 항상 동일(무상태·결정론).
- ⚠️ 새 문구도 `"매물을 찾아드릴게요"` 부분 문자열을 반드시 포함해야 한다 — `api/scripts/score_ab.py`의 `REDIRECT_MARKERS`(`is_redirect()`, G1류 dead-end 게이트)가 이 문자열로 "거절이 갈림길 멘트를 포함하는가"를 판정한다. 새 Voice 문구는 이미 이 부분 문자열을 포함하므로 그대로 쓰면 게이트가 깨지지 않는다(직접 확인 필요, Verification 참조).
- `guard_node(query)`는 **고정 상수** `narrowed_by: list[str]`(예: `["price<=30000000", "body_type=SUV", "fuel=전기"]` — CR4 저장단위 정규화 술어 형식, CLARIFY 3축과 동일 계열)를 항상 반환한다. `query`나 `context`를 읽어 값을 바꾸지 않는다(무상태 — CR5와 동일 철학의 REJECT 버전, LLM 호출 없음).
- `SearchState`·`answer_node`·`run_search`·`SearchResponse`가 `clarify`와 동일한 additive 패턴으로 `narrowed_by`를 통과시킨다: SQL/HYBRID/CLARIFY 경로는 `narrowed_by=None`(기존 회귀 없음).
- `docs/conventions.md` §4에 `narrowed_by` 필드를 문서화한다(교차 경계 정본, CR4).
- DW-593 해결: `api/app/routers/ai.py`의 `return SearchResponse(...)`를 `try` 블록 **안으로** 옮겨, 응답 스키마 검증 실패가 기존 `except Exception`(CORS 안쪽, 500)으로 잡히게 한다. 일부러 깨진 값(예: `narrowed_by=[123]`)으로 실제 500 + CORS 헤더 존재를 실측한 뒤 DW-593을 `done`으로 닫는다.
- `web/src/lib/api/aiSearch.ts`에 `narrowed_by` **타입과 매핑을 같은 패스에서** 추가한다(13.4 1차 리뷰가 잡은 "타입만 있고 매핑 없음" 재발 방지) — 형태 검증(문자열 배열인지) 후 아니면 `null`.

**Block If:**
- 로컬 Supabase+`GEMINI_API_KEY`로 REJECT 대표 질의(예: 큐리셋 C1~C3) 1~2개를 `run_phase_b.py --subset`으로 직접 실행했을 때 `is_redirect()`가 새 답변 문구에서 실제로 `False`가 되면(마커 불일치 실측), HALT(status blocked, blocking condition `REJECT 문구 변경이 G1 dead-end 게이트를 깬다`).

**Never:**
- 공개 `route` 필드는 `SearchResponse`에 추가하지 않는다 — `docs/conventions.md` §4가 13.4에서 이미 "클라이언트는 `clarify !== null`로 판별, 응답에 `route` 필드는 없다"고 확정했다. REJECT는 `narrowed_by !== null`로 판별 가능하므로 추가 식별 필드가 필요 없다.
- SQL/HYBRID 경로의 기존 FR17 0건 fallback(`answer_node._EMPTY_FALLBACK`)은 건드리지 않는다 — "narrowed_by로 0건 다양성을 표현"하는 확장은 그 경로엔 적용하지 않는다(구조조건을 narrowed_by로 추출하는 일반화는 이번 스토리 범위 밖 — DW 신규 등재로 남긴다).
- 실제 "재제안 칩" 탭 UI(web/app 렌더링, `narrowed_by`를 버튼으로 그려 탭→재검색)는 만들지 않는다 — `clarify.chips`도 13.4에서 값만 실어 보내고 렌더는 안 만든 것과 동일 경계(DW-587 선례). 이번 스토리는 값 배선까지다.
- `clarify_node`·CLARIFY 분기·되묻기 상한 로직은 손대지 않는다(13.4 소관, 이번 스토리 범위 밖).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 법적/무관 질의 (REJECT) | "오늘 날씨 어때?" | `answer`=Voice 표 고정 문구, `listings=[]`, `narrowed_by`=고정 상수 3개 | No error |
| SQL/HYBRID/CLARIFY 경로 | 임의 질의 | `narrowed_by=None`(회귀 없음, 값 안 채움) | No error |
| 응답 조립 실패(방어) | `run_search`가 스키마 위반 값을 반환(예: narrowed_by에 비문자열) | HTTPException 500 + CORS 헤더 유지(DW-593) | 500, `{error:{code:"internal_error"}}` |

</intent-contract>

## Code Map

- `api/app/graph/guard_node.py` -- 고정 답변을 Voice 표 문구로 교체, `_GUARD_NARROWED_BY` 고정 상수 신설, 반환에 `narrowed_by` 추가.
- `api/app/graph/graph.py` -- `SearchState`에 `narrowed_by: list[str] | None` 키 추가, `_guard_step`이 통과시킴, `_answer_step`이 `answer_node` 호출 시 전달, `run_search` 반환 dict에 `narrowed_by` 포함.
- `api/app/graph/answer_node.py` -- `clarify`와 동일하게 `narrowed_by` 키를 통과(없으면 None).
- `api/app/schemas/ai.py` -- `SearchResponse.narrowed_by: list[str] | None = None` 필드 추가.
- `api/app/routers/ai.py` -- `SearchResponse(...)` 생성을 `try` 블록 안으로 이동(DW-593), `narrowed_by=result.get("narrowed_by")` 추가.
- `api/tests/test_graph.py` -- `test_guard_node_returns_empty_listings_and_guidance` 문구 단언 갱신, `guard_node`/`answer_node`/`run_search`의 `narrowed_by` 통과 테스트 신설.
- `api/tests/test_ai_search.py` -- `narrowed_by` 있음/없음 wire 테스트 신설(clarify 선례와 동일 패턴), 응답 조립 실패 시 500+CORS 유지 테스트 신설(DW-593 증거).
- `api/tests/test_live_smoke.py` -- `test_live_smoke_pathC`에 `narrowed_by` 비공백 리스트 단언 추가.
- `docs/conventions.md` -- §4에 `narrowed_by` 필드 문서화, `route` 미노출 문구를 13.5 결정 확정형으로 정리.
- `web/src/lib/api/aiSearch.ts` -- `SearchResult.narrowed_by: string[] | null` 타입 + `searchAi()` 매핑(형태 검증 포함) 동시 추가.
- `web/src/lib/api/aiSearch.test.ts` -- `narrowed_by` 매핑 테스트(있음/없음/깨진 형태) 신설.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-593 closed. 신규 등재: (a) REJECT 재제안 칩 실제 UI 없음, (b) SQL/HYBRID 0건 응답의 narrowed_by 확장은 범위 밖.

## Tasks & Acceptance

**Execution:**
- `api/app/graph/guard_node.py` -- `_GUARD_ANSWER`를 Voice 표 문구로 교체. `_GUARD_NARROWED_BY = ("price<=30000000", "body_type=SUV", "fuel=전기")` 신설. `guard_node()`가 `{"answer": _GUARD_ANSWER, "listings": [], "narrowed_by": list(_GUARD_NARROWED_BY)}` 반환.
- `api/app/graph/graph.py` -- `SearchState`에 `narrowed_by: list[str] | None` 추가. `_guard_step`이 `result.get("narrowed_by")`를 반환에 포함. `_answer_step`이 `answer_node(...)` 호출 시 `"narrowed_by": state.get("narrowed_by")` 전달. `run_search`가 반환 dict에 `"narrowed_by": final_state.get("narrowed_by")` 추가.
- `api/app/graph/answer_node.py` -- 반환 dict에 `"narrowed_by": result.get("narrowed_by")` 추가(클라이언트 함정 #3 승계 — 새 판단 없이 그대로 통과).
- `api/app/schemas/ai.py` -- `SearchResponse`에 `narrowed_by: list[str] | None = None` 추가(기존 필드 순서 유지, additive).
- `api/app/routers/ai.py` -- `return SearchResponse(...)`를 `try:` 블록의 마지막 줄로 이동(현재 `result = await asyncio.to_thread(...)` 바로 다음), `narrowed_by=result.get("narrowed_by")` 포함.
- `api/tests/test_graph.py` -- `test_guard_node_returns_empty_listings_and_guidance`의 문자열 단언을 새 문구 기준으로 갱신("차장님"·"조건" 등 핵심어). 신규: `test_guard_node_returns_fixed_narrowed_by`(고정 상수 3개, 다른 query로 호출해도 동일). 신규: `test_answer_node_passes_through_narrowed_by_field`/`test_answer_node_narrowed_by_absent_defaults_to_none`(clarify 테스트 짝과 동일 구조). `test_route_REJECT_calls_guard_and_returns_empty_listings`에 `out["narrowed_by"]` 비공백 리스트 단언 추가.
- `api/tests/test_ai_search.py` -- `test_search_returns_narrowed_by_when_present`/`test_search_narrowed_by_absent_serializes_to_null`(clarify 짝과 동일 구조). 신규 `test_search_response_validation_error_returns_500_with_cors`: `run_search`가 `narrowed_by: [123]`(스키마 위반)을 반환하도록 모킹, `Origin: http://localhost:3000` 헤더로 요청, `status_code==500`·`headers["access-control-allow-origin"]=="http://localhost:3000"`·`json()["error"]["code"]=="internal_error"` 확인(DW-593 실측 증거).
- `api/tests/test_live_smoke.py` -- `test_live_smoke_pathC`에 `assert out["narrowed_by"]`(비공백) 단언 추가.
- `docs/conventions.md` §4 -- `narrowed_by?: string[]` 필드 설명 추가(REJECT 전용, 고정 상수, 다른 라우트는 `null`). "응답에 `route` 필드는 없다" 문구에서 "13.5/13.6 소관" 표현을 "13.5가 확정: 노출하지 않음"으로 정리.
- `web/src/lib/api/aiSearch.ts` -- `SearchResult`에 `narrowed_by: string[] | null` 추가. `isValidNarrowedBy(value): value is string[]`(배열이고 모든 원소가 문자열) 신설. `searchAi()` 반환에 `narrowed_by: isValidNarrowedBy(result.narrowed_by) ? result.narrowed_by : null` 추가(clarify와 같은 패스에 타입+매핑 동시 반영).
- `web/src/lib/api/aiSearch.test.ts` -- `narrowed_by` 있음(정상 배열)/없음(undefined→null)/깨진 형태(숫자 배열→null) 3케이스.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-593을 `status: done`(resolution: try 블록 이동 + 실측 테스트)으로 닫는다. 신규 등재 2건: (a) REJECT `narrowed_by`는 값만 배선되고 실제 재제안 칩 UI(web/app)는 없음(DW-587과 같은 자리에서 처리 가능하도록 trigger 명시), (b) SQL/HYBRID 0건 응답에 narrowed_by를 확장하는 일반화(실제 추출 SQL 조건 기반)는 이번 스토리 범위 밖(FR17 후속 개선 후보로 trigger 명시).

**Acceptance Criteria:**
- Given REJECT 경로, when 법적/무관 질의가 오면, then `answer`가 Voice 표 고정 문구와 정확히 일치하고 `listings=[]`·`narrowed_by`가 고정 상수 3개로 채워진다(FR47, 직접 실행 확인, B4).
- Given REJECT 경로, when 서로 다른 질의로 두 번 호출해도, then `narrowed_by` 값이 완전히 동일하다(무상태·결정론 확인).
- Given SQL/HYBRID/CLARIFY 경로, when 정상 동작하면, then `narrowed_by`가 `None`으로 응답에 실려(회귀 없음) 기존 계약을 깨지 않는다.
- Given `run_phase_b.py --subset`으로 REJECT 대표 질의(C1~C3)를 재실행하면, then `is_redirect()`가 여전히 `True`이고 `deadend`가 0이다(G1류 dead-end 게이트 회귀 없음, 직접 실행 확인, B4).
- Given 응답 조립 시 스키마 위반 값이 들어오면, when `/ai/search`가 처리하면, then 500 응답에 CORS 헤더가 유지된다(DW-593 해결 증거, 직접 실행 확인, B4).
- Given 이번 스토리 완료, when `deferred-work.md`를 확인하면, then DW-593이 근거와 함께 closed이고 신규 2건(칩 UI 부재·0건 narrowed_by 확장 범위 밖)이 open으로 등재돼 있다(B8).

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 0
- reject: 8: (high 0, medium 1, low 7)
- addressed_findings:
  - `[medium]` `[patch]` `api/scripts/score_ab.py`의 `REDIRECT_MARKERS`(G1류 dead-end 게이트가 REJECT 응답이 "갈림길" 문구를 포함하는지 판정하는 부분문자열 목록)가 3개 중 2개("예산"·"용도를 알려주시면")를 이번 문구 교체로 더 이상 만들 수 없게 됐다 — OR 판정이라 지금은 나머지 1개로 통과하지만, 그 마지막 하나마저 바뀌면 게이트가 조용히 완전히 죽는다. `("매물을 찾아드릴게요", "조건을 말씀해 주시면", "차장님")`로 갱신하고 `run_phase_b.py --subset C1,C2,C3` + `score_ab.py`로 재확인(dead-end 0, gate PASS).
  - `[low]` `[patch]` `deferred-work.md`의 DW-593 `resolution:`이 "실측 확인했다"고 썼지만 실제로 새 테스트는 `narrowed_by` 위반 시나리오 하나만 돌린다 — `clarify`/`listings` 위반 경로는 이번에도 별도로 실행하지 않았다. 메커니즘이 필드 무관하게 구조적으로(단일 try·단일 return) 동작한다는 점과, `narrowed_by`가 대표 사례로 실측됐다는 점을 정확히 구분해 적도록 resolution 문구를 정정.
  - `[low]` `[patch]` `api/app/graph/graph.py`의 `_guard_step`이 `result["answer"]`/`result["listings"]`는 직접 인덱싱하면서 `narrowed_by`만 `.get()`으로 방어적으로 읽어, guard_node가 실수로 그 키를 빠뜨려도 조용히 `None`으로 흡수되게 돼 있었다(같은 파일의 `_clarify_step`은 보장된 키를 전부 직접 인덱싱하는 것과도 불일치). `result["narrowed_by"]`로 통일.
  - `[low]` `[patch]` `web/src/lib/api/aiSearch.ts`의 `isValidNarrowedBy`가 빈 배열(`[]`)을 유효한 문자열 배열로 통과시켜, 서버 계약(REJECT일 때 항상 정확히 3개)과 어긋나는 값도 "정상"으로 흘려보내고 있었다 — `conventions.md` §4의 `narrowed_by !== null` REJECT 판별 관례를 따르는 소비처가 빈 배열을 REJECT로 오판할 수 있었다. `value.length > 0` 조건 추가 + 빈 배열 케이스 테스트 신설.
  - `[low]` `[patch]` `test_route_SQL_calls_sql_only`/`test_route_HYBRID_calls_hybrid_only`가 `narrowed_by`를 전혀 확인하지 않아, "SQL/HYBRID는 narrowed_by=None"이라는 `run_search` docstring의 보장이 REJECT 쪽만 실제 그래프 실행으로 검증되고 SQL/HYBRID 쪽은 `answer_node`의 범용 단위테스트 하나에만 간접적으로 기대고 있었다. 두 테스트에 `assert out["narrowed_by"] is None` 추가.
  - `[low]` `reject` `guard_node`의 "EXPERIENCE.md Voice 표와 글자 그대로 일치"라는 주석 주장을 markdown 파일을 직접 읽어 대조하는 golden 테스트로 강제해야 한다는 지적 — verification-gap 렌즈가 이미 실측으로 문자 그대로 일치함을 확인했고, 이 프로젝트에 markdown 소스를 파싱해 강제하는 golden 테스트 선례가 없어(clarify_node도 단순 부분문자열 단언만 씀) 이번에 새로 만들면 과설계다.
  - `[low]` `reject` `narrowed_by`의 고정 예시(가격·SUV·전기)가 답변 문구의 예시와 안 맞는다는 지적 — 스펙 Design Notes가 이미 "고정 상수 vs 실제 조건 복원" 두 해석을 검토해 고정 상수를 명시적으로 택한 트레이드오프다(아래 참조).
  - `[low]` `reject` `test_answer_node_preserves_existing_answer_and_listings`가 dict 전체 동등성이라 필드가 늘 때마다 깨진다는 지적 — 기존 코드베이스 전반의 관례(13.4도 동일 패턴)이고 이번 변경이 새로 만든 문제가 아니다.
  - `[low]` `reject` DW-593 CORS 테스트가 `localhost:3000` 한 오리진만 확인한다는 지적 — try/except 배치 자체가 오리진 값과 무관하게 동작하는 구조적 수정이라, 오리진별 파라미터화는 이 수정이 실제로 고치는 것과 무관하다.
  - `[low]` `reject` `clarify`·`narrowed_by`가 동시에 non-null이 되는 오염 입력에 대한 통합테스트가 없다는 지적 — 그래프 구조상 한 요청은 라우트 하나만 타므로 그런 상태는 실제로 도달 불가능하다(불가능한 상태용 방어는 넣지 않는다, CLAUDE.md A2).
  - `[low]` `reject` 새 거절 문구의 이모지(🚗)가 어떤 테스트로도 인코딩 확인이 안 된다는 지적 — 이 문자열을 sanitize/정규화하는 유틸이 현재 아무 데도 없어 realistic한 실패 경로가 없다.
  - `[medium]` `reject` intent-alignment 감사가 제기한 "원 조건 재제안 칩"·"0건" 문구의 여러 해석(고정 예시 vs 실제 이전 대화 조건 복원, REJECT 한정 vs SQL/HYBRID 0건까지 확장, 데이터 배선 vs 실제 칩 렌더링)이 이 스토리의 좁은 선택으로 완전히 해소되지 않는다는 지적 — 실재하는 다중 해석이지만, 스펙 Design Notes가 이미 그 해석들을 명시적으로 나열·검토한 뒤 FR47의 "무상태·결정론" 요구와 CLARIFY(13.4)가 동일 범주 요구를 고정 상수+렌더 유예로 푼 선례를 근거로 좁은 해석을 선택했다(스펙의 범위 선언 자체가 아니라 그 근거가 판단 권한이다). 13.4가 리뷰 3회 동안 거의 동일한 성격의 지적("칩 UI가 없다", "상한 계산이 이상적 해석과 다르다")을 매번 "이미 기록된 트레이드오프"로 reject해 온 이 에픽의 일관된 선례를 따른다. 잔여 지점은 이미 DW-597(칩 UI 부재)·DW-598(0건 확장 범위 밖)로 등재돼 있다.
  - `[low]` `reject` intent-alignment 감사가 지적한 "이번 diff가 `epic-13-context.md`의 모호한 '0건 결과도 동일 방식' 문구를 수정해 논쟁을 감췄다"는 지적 — 실측 확인 결과 그 문서 재생성은 이번 스토리 구현(step-03) 이전, step-01 라우팅 단계에서 별개 사유(DW-560 표기 정정 후속)로 이미 수행됐고, 정본인 `epics-increment-2026-07-12.md`(미수정)는 여전히 "0건·거절" 문구를 그대로 갖고 있어 긴장 관계가 사라진 게 아니라 그대로 남아 있으며 DW-598로 추적 중이다.

### 2026-07-31 — Review pass (2차, followup)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 3: (high 0, medium 0, low 3)
- reject: 9: (high 0, medium 1, low 8)
- addressed_findings:
  - `[medium]` `[patch]` 1차 패치가 `REDIRECT_MARKERS`에 넣은 `"차장님"`은 페르소나 호칭일 뿐 행동 유도 의미가 없어, OR 판정인 dead-end 게이트가 **구조적으로 항상 통과**하게 만들었다(거절 문장을 통째로 지워도 redirect=True). 동시에 1차 패치가 뺀 `"용도를 알려주시면"` 때문에 `answer_node._EMPTY_FALLBACK`(FR17 0건 재유도 문구)이 dead-end로 오분류되고 있었다 — 실측으로 `is_redirect(_EMPTY_FALLBACK)=False` 확인. 마커를 행동 유도 문구 3개(`"매물을 찾아드릴게요"`, `"조건을 말씀해 주시면"`, `"용도를 알려주시면"`)로 교체하고, 라이브 게이트를 C1~C3이 아니라 **C 전량(C1~C6)+M9**로 확대 재실행(라우팅 8/8, dead-end 0, gate PASS).
  - `[medium]` `[patch]` `docs/conventions.md` §4가 `narrowed_by !== null`을 REJECT 판별자로 공표하는데, **같은 커밋의 DW-598**이 그 배타성을 깨는 확장(SQL/HYBRID 0건까지 채움)을 예고한다 — 확장이 채택되는 날 이 규칙을 따른 모든 클라이언트가 0건 검색 결과를 거절로 렌더한다. §4에 유효 조건과 동반 수정 의무를 명시(DW-598 엔트리는 orchestrator 소관이라 미수정).
  - `[low]` `[patch]` `is_redirect(_GUARD_ANSWER)`를 실제로 호출하는 검사가 하나도 없어 문구·마커 결합이 **주석에만** 존재했다(실측: 마커를 13.5 이전 값으로 되돌려도 api 355건 전량 초록). `tests/test_ab_scoring.py`에 결합 검사 신설 — 1차 패치 상태(`"차장님"` 포함)로 되돌리면 red가 되는 것까지 확인(CLAUDE.md B9).
  - `[low]` `[patch]` 스펙의 최강 제약("EXPERIENCE.md Voice 표와 **글자 그대로** 일치")을 어느 검사도 지키지 않아, 문구를 리워드해도 전 스위트가 초록이었다(실측). 1차 리뷰가 reject한 "markdown 파싱 golden 테스트"는 과설계라는 판단을 유지하되, **요구 액션이 다른** 리터럴 동등 단언 1줄을 `test_demo_acceptance.py`에 추가(파싱 없음, 새 선례 없음) — red 확인 완료.
  - `[low]` `[patch]` I/O 매트릭스 2행이 CLARIFY를 명시하는데 1차 패치는 SQL·HYBRID에만 `narrowed_by is None` 단언을 넣어 CLARIFY만 간접 증거로 남아 있었다. `_clarify_step`은 **분기가 둘**(상한 이내 / 상한 초과 doc 폴백)이라 두 테스트 모두에 단언 추가 — 각 분기에 leak을 심어 개별로 red 확인.
  - `[low]` `[patch]` `test_guard_node_returns_fixed_narrowed_by`가 길이·타입만 봐서, 값을 `_CLARIFY_CHIPS`류 한국어 표시문자열("3천만원 이하")로 바꿔도 통과했다 — `conventions.md` §4가 클라이언트에 공표한 CR4 저장단위 술어 형식이 조용히 깨진다. 정확한 상수 동등 단언으로 교체, red 확인.
  - `[low]` `defer` FR17 0건 문구(`_EMPTY_FALLBACK`)가 EXPERIENCE.md Voice 표 62행과 다르다(실측 대조). 13.5가 만든 결함은 아니나(Epic 4부터 존재, Never 절이 손대지 말라고 명시) "노출 문구=Voice 표 정본" 규칙의 예외가 장부에 없었다 → **DW-599**.
  - `[low]` `defer` 정본 AC·CR4·`epic-13-context.md`가 요구하는 "`narrowed_by`를 결정론 템플릿이 **조립**해 answer 문장을 만든다"가 미구현인데, DW-597(칩 UI)·DW-598(0건 확장) 어디에도 안 잡혀 있다(리포지토리 전체에서 `narrowed_by`↔`answer` 연결 단언 0개) → **DW-600**. 스펙의 좁은 해석 자체는 FR47 무상태·결정론과 정합해 유지.
  - `[low]` `defer` DW-593 resolution이 "구조적으로 모든 필드 동일 경로"라 적었으나, FastAPI `response_model=` 재검증·직렬화는 엔드포인트 `try` **밖**에서 돌고 그 500은 CORSMiddleware 바깥에서 만들어진다 — 잔여 노출면. 기존 엔트리 수정 금지 지시에 따라 신규 등재 → **DW-601**.
  - `[medium]` `reject` intent-alignment 감사의 "다중 해석 미해소" 재지적 — 1차 패스와 동일 판단(FR47 무상태·결정론 요구가 좁은 해석의 근거)을 유지하되, 이번엔 지적이 실재하는 **장부 공백**을 짚었으므로 그 부분만 DW-600으로 등재했다.
  - `[low]` `reject` `api/app/routers/ai.py`가 `narrowed_by`를 `.get()`으로 읽는다는 지적 — 실측 확인 결과 바로 윗줄 `clarify`도 `.get()`이다. 형제와 동일 관례이고, 바꾸면 의도적으로 만든 부재-키 테스트가 깨진다.
  - `[low]` `reject` `answer_node`가 `narrowed_by`를 정규화하지 않는다는 지적 — 값의 출처가 고정 상수뿐이라 도달 불가한 상태용 방어다(CLAUDE.md A2). 스펙도 "새 판단 없이 그대로 통과"(함정 #3 승계)를 명시했다.
  - `[low]` `reject` `SearchResponse.narrowed_by`에 서버측 `min_length=1`을 걸라는 지적 — 위와 같은 이유로 도달 불가.
  - `[low]` `reject` `api/docs/g2-baseline.json`이 13.5 이전 거절 문구를 갖고 있어 마커를 조이면 G2가 깨진다는 지적 — 실측 반증. 프리즈된 baseline의 C1~C6 답변을 옛/현/조인 마커 세 세트로 전부 채점해 **모두 redirect=True** 확인.
  - `[low]` `reject` live smoke의 `assert out["narrowed_by"]`가 truthiness만 본다는 지적 — 그 테스트의 목적은 실제 Gemini+DB 경로에서 필드가 **살아 나오는지**이고 값 고정은 단위테스트 몫이다.
  - `[low]` `reject` `_GUARD_NARROWED_BY`와 `_CLARIFY_CHIPS`가 같은 3축을 두 형식으로 중복한다는 지적 — 스펙 Design Notes가 명시적으로 택한 설계(wire 술어 vs 표시 문자열)다.
  - `[low]` `reject` 응답 조립 실패 로그가 파이프라인 오류와 구분되지 않는다는 지적 — cosmetic.
  - `[low]` `reject` 필드명 `narrowed_by`가 실제로는 좁힌 적 없는 조건이라 거짓 인과를 주장한다는 지적 — 1차 패스가 이미 같은 취지로 reject한 "고정 예시 해석" 항목과 동일 사안이며, 잔여 지점은 DW-600이 잡는다.

### 2026-07-31 — Review pass (3차, followup)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 15: (high 0, medium 3, low 12)
- addressed_findings:
  - `[medium]` `[patch]` 2차가 신설한 결합 검사 `test_redirect_markers_actually_match_the_shipped_answers`가 **양성 방향만** 못박아, 정작 2차가 잡아낸 실패 유형(마커가 과도하게 넓어져 OR 게이트가 구조적으로 항상 통과)은 여전히 못 잡았다 — 3개 레이어가 독립적으로 지적했고, 실측으로 `REDIRECT_MARKERS`에 `"차장님"`을 되돌려도 api 356건 전량 초록임을 재확인했다. **출고 거절 문구에서 유도 절만 걷어낸 변형**을 음성 대조군으로 추가(`is_redirect(...) is False` 단언). red→green 실측 완료 — `"차장님"` 마커 복원 시 red, 원복 후 green, `score_ab.py`는 HEAD와 바이트 동일.
  - `[low]` `[patch]` `narrowed_by`의 **빈 배열(`[]`) 의미가 계약 정본에 없어** 서버(길이 제약 없음, `[]` 허용)와 web(`isValidNarrowedBy`가 `[]`→`null`)이 같은 값을 반대로 판정하고 있었다. 서버에 `min_length=1`을 거는 반대 방향은 채택하지 않았다 — DW-598이 0건 응답까지 확장할 때 "조건을 못 뽑았다"의 자연스러운 표현이 `[]`인데 그러면 500이 된다. 대신 `docs/conventions.md` §4에 "`[]`는 `null`과 동일 취급, 판별은 **비어 있지 않은 문자열 배열인가**로 한다"를 명문화(정본 한 곳에 규약을 두고 web 구현이 그것을 따르는 형태).
  - `[low]` `[patch]` `api/app/graph/graph.py` 모듈 docstring이 공통 계약을 아직 `{answer, listings[], clarify}`로 광고하고 있었다 — 이번 스토리가 함수 docstring 3개는 갱신하면서 모듈 헤더만 놓쳤다. `narrowed_by` 포함으로 정정.
  - `[low]` `defer` 라우터 LLM 장애 시 `_fallback_route`가 정상 차량 질의도 `REJECT`로 보내는데, 이제 그 응답에 사용자가 말한 적 없는 고정 `narrowed_by` 3개가 "좁힌 조건"으로 함께 실린다. 스펙 Always 절("`query`/`context`를 읽어 값을 바꾸지 않는다")이 코드 수정을 막으므로 이번 패스에서 못 고침 → **DW-602**(trigger: DW-597 칩 UI 구현 시점 = 값이 화면에 보이기 직전).
  - `[medium]` `reject` `response_model=` 재검증이 여전히 `try` 밖이라 DW-593이 닫은 은폐 경로가 남아 있다는 지적 — 사실이고 adversarial 레이어가 프로브로 실제 재현까지 했으나, 2차 패스가 이미 **DW-601**로 등재해 둔 항목이다(edge-case 레이어도 "중복 계상하지 말라"고 명시). 신규 등재는 중복이고 기존 엔트리는 orchestrator 소관이라 무수정.
  - `[medium]` `reject` 정본 AC의 "결정론 템플릿이 조립"·"원 조건 재제안 칩"이 미이행인데 story가 done이라는 지적 — 1·2차와 동일 판단(FR47 무상태·결정론이 좁은 해석의 근거). 2차가 이미 잔여 격차를 DW-597·DW-598·DW-600으로 전부 등재해 장부 공백도 없다. 3연속 동일 지적이며 새 근거가 추가되지 않았다.
  - `[medium]` `reject` `epic-13-context.md` 재생성이 살아 있는 제약(sql_guard 회귀 3케이스·422 파일 경로·G2 baseline 44개 서술)을 산문으로 희석했다는 지적 — 실측 확인 결과 사라진 포인터 3건(DW-554·559·560)은 **전부 `status: done`**이라 삭제가 오히려 정확하고, 나머지(500자 상한·sql_guard 강제·G2 게이트)는 새 본문에도 남아 있으며 정본 `epics-increment-2026-07-12.md`는 무수정이다. 게다가 이 파일은 step-01이 조건부로 재생성하는 **캐시**라 손편집이 내구성이 없다.
  - `[low]` `reject` 마커 3개 중 1·2번이 서로를 가려 하나를 지워도 초록이라는 지적 — 두 마커가 같은 출고 문구를 중복 커버하는 것은 게이트를 **약화시키지 않는다**(OR 판정에서 남은 하나가 그대로 잡는다). 위험한 방향은 넓어지는 쪽이고 그건 이번에 음성 대조군으로 막았다.
  - `[low]` `reject` DW-600의 `location:`이 55줄짜리 파일의 L71·L93을 가리킨다는 지적 — 사실이나 기존 장부 엔트리는 orchestrator 소관(수정 금지 지시)이라 이 패스가 손댈 수 없다. 잔여 위험으로 보고만 한다.
  - `[low]` `reject` `review_loop_iteration: 0`이 본문의 리뷰 2회 기록과 모순이라는 지적 — `done` 스펙에 후속 리뷰를 걸 때 워크플로가 **규정대로** 0으로 리셋한 값이다(설계된 동작).
  - `[low]` `reject` 라우팅 안전보정 분기(`_route_decision`)에서 `route`와 `narrowed_by`가 어긋날 수 있다는 지적 — `router_node`가 반환 전 4값으로 정규화하므로 도달 불가(A2).
  - `[low]` `reject` 술어 문자열(`price<=30000000`)의 문법·파서·테스트가 없다는 지적 — 생산자가 3원소 고정 상수 하나뿐인 지금 문법을 정의하는 것은 과설계(A2). 칩 UI를 만드는 자리(DW-597)가 그 문법을 정할 자리다.
  - `[low]` `reject` REJECT 판별 규약에 실행되는 검사가 없다는 지적 — 유일한 "못 어기는" 수단은 `route` 필드 노출인데 스펙 Never 절이 금지한다. 실행 가능한 부분(빈 배열 규약)만 위 patch로 처리했다.
  - `[low]` `reject` DW-593 종료에 수정 전 상태(음성 대조군) 측정이 없다는 지적 — adversarial 레이어가 이번에 직접 프로브로 측정해 "try 밖이면 CORS 헤더 없음"이 참임을 확인했다. 결론이 확증됐으므로 추가 작업 없음(DW-593 엔트리는 수정 금지).
  - `[low]` `reject` 라이브 G1 게이트가 상수 대 상수 비교라 증명력이 낮은데 유료 호출을 쓴다는 지적 — 스펙 Block-If가 명시적으로 요구한 실행이고, 실제로 측정되는 값(라우팅 정확도)은 오프라인으로 대체 불가다.
  - `[low]` `reject` Voice 표 리터럴 단언이 정본 markdown이 아니라 테스트 파일 안 사본과 비교한다는 지적 — 1차가 "markdown 파싱 golden 테스트는 과설계"로 판단했고 2차가 그 한계를 인지한 채 리터럴 단언을 택했다. 동일 판단 유지.
  - `[low]` `reject` 실제 라우팅을 거친 REJECT가 고정 3값을 내는지 상시 검사하는 E2E가 없다는 지적 — 라이브 스모크(secrets 필요, CI 제외)는 프로젝트가 의도적으로 택한 경계다(project-context §12).
  - `[low]` `reject` Flutter `ai_search_api.dart` 헤더 주석이 계약을 `{answer, listings[]}`로 적고 있다는 지적 — `clarify`(13.4)부터 이미 낡아 있던 선재 상태이고 DW-592가 같은 경계를 잡고 있다.
  - `[low]` `reject` `aiSearch.test.ts` 신규 `describe`가 위 블록의 mock 셋업 15줄을 복붙했다는 지적 — 인접 코드 리팩터 금지(A3), 기존 스타일과 일치.
  - `[low]` `reject` 장부에 Never 절 재진술(DW-597·598)만 늘고 정작 "2차 followup 미실행"은 안 적혔다는 지적 — 이번 패스가 그 followup 자체다(무효).

## Design Notes

**narrowed_by 값의 출처를 "실제 조건 추출"이 아니라 "고정 상수"로 결정한 근거.** 상위 문서(epics/architecture)는 `narrowed_by`를 "0건·거절 시 사유 술어"로 설명하고, UX 문서는 REJECT 응답에 "원 조건 재제안 칩"을 요구한다. 이를 "이전 턴에 사용자가 실제로 검색했던 조건을 대화 맥락에서 복원한다"로 읽을 수도 있으나, 그러려면 자연어 대화 이력에서 구조 조건을 LLM 없이 파싱하는 별도 추출기가 필요해(A2 단순함 위반, 이번 스토리 범위를 크게 넘음), FR47이 REJECT 전체에 못박은 "무상태·결정론·LLM 자유 재작성 없음"과도 정면으로 배치된다(추출기 자체가 대화 상태에 의존하는 로직이 된다). CLARIFY의 `_CLARIFY_CHIPS`가 이미 "고정 예시 3축(가격·차종·연료)"으로 동일한 요구("칩 제시")를 결정론적으로 풀었으므로, REJECT도 같은 패턴(고정 상수, CR4의 술어 형식만 다름)을 쓰는 것이 유일하게 이번 범위 안에서 완결되는 해석이다. 실제 "칩을 탭하면 그 조건으로 재검색"하는 UI는 이번 스토리가 만들지 않는다(위 Never 절 + 신규 DW) — clarify.chips가 13.4에서 값만 배선되고 렌더는 미룬 것과 동일한 경계다.

**"0건·거절" 문구를 REJECT에만 적용하고 SQL/HYBRID 0건에는 확장하지 않은 근거.** Story 13.5의 Given/When/Then은 "Given REJECT 경로"로 시작한다 — REJECT는 태생적으로 `listings=[]`(0건)이므로 "0건·거절"은 REJECT 자신의 속성을 가리키는 것으로 읽었다. SQL/HYBRID의 기존 FR17 0건 fallback(`_EMPTY_FALLBACK`, Epic 4부터 존재)에 "실제 추출된 SQL 조건을 narrowed_by로 노출"하는 확장은 Story 13.6(가이드 활용) AC에도 언급이 없어, 별도 스토리로 남기는 것이 안전하다(신규 DW로 추적, 조용히 사라지지 않게).

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/ -x -q` -- expected: 전량 통과(신규 테스트 포함).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -x -q` -- expected: pathC가 새 Voice 문구 + narrowed_by를 실제로 반환.
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python scripts/run_phase_b.py --subset C1,C2,C3 --out /tmp/reject-check.json && .venv/bin/python scripts/score_ab.py --raw /tmp/reject-check.json --out /tmp/reject-check-report.json` -- expected: 콘솔/리포트에서 redirect 관련 항목이 여전히 True, `deadend` 0(G1류 회귀 없음, Block-If 조건 실측).
- `cd web && npm run lint && npm run test` -- expected: 무경고, 신규 narrowed_by 테스트 포함 전량 통과.

**Manual checks (if no CLI):**
- 로컬 Supabase+`GEMINI_API_KEY`로 "오늘 날씨 어때?"를 `run_search()`로 직접 호출해 `answer`가 Voice 표 문구와 글자 그대로 같은지, `narrowed_by`가 고정 3개 값인지 눈으로 확인.

## Auto Run Result

**Status:** done

**Summary:** REJECT(경로 C, `guard_node`)의 고정 답변 문구를 EXPERIENCE.md Voice 표("AI 거절(FR47, 고정)")와 글자 그대로 일치시키고, REJECT 전용 고정 상수 `narrowed_by: list[str]`(`["price<=30000000", "body_type=SUV", "fuel=전기"]`)를 `SearchState`→`answer_node`→`SearchResponse`까지 `clarify`와 동일한 additive 패턴으로 배선했다. SQL/HYBRID/CLARIFY 경로는 `narrowed_by=None`(회귀 없음). 공개 `route` 필드는 추가하지 않았다(13.4가 이미 "노출하지 않음"으로 확정한 결정을 그대로 유지·문구만 확정형으로 정리). 함께 DW-593(`/ai/search` 응답 조립이 CORS 미들웨어 바깥 500 경로로 샐 수 있던 구조적 결함)을 해결했다 — `return SearchResponse(...)`를 `try` 블록 안으로 옮겨 스키마 검증 실패도 CORS 안쪽 500으로 잡히게 했다.

**Files changed:**
- `api/app/graph/guard_node.py` -- `_GUARD_ANSWER`를 Voice 표 문구로 교체, `_GUARD_NARROWED_BY` 고정 상수 신설, `guard_node()`가 `narrowed_by` 반환.
- `api/app/graph/graph.py` -- `SearchState.narrowed_by` 키 추가, `_guard_step`/`_answer_step`/`run_search`가 additive로 통과(리뷰 패치: `_guard_step`을 `.get()`에서 직접 인덱싱으로 정정).
- `api/app/graph/answer_node.py` -- `narrowed_by` 키 통과(clarify와 동일 패턴).
- `api/app/schemas/ai.py` -- `SearchResponse.narrowed_by: list[str] | None = None` 추가.
- `api/app/routers/ai.py` -- `SearchResponse(...)` 생성을 `try` 블록 안으로 이동(DW-593), `narrowed_by` 포함.
- `api/scripts/score_ab.py` -- (리뷰 패치) `REDIRECT_MARKERS`를 새 거절 문구에 맞춰 갱신(2/3 마커가 죽어 있었음).
- `api/tests/test_graph.py` -- guard 문구 단언 갱신, `narrowed_by` 통과·고정값·SQL/HYBRID `None` 테스트 신설(리뷰 패치 포함).
- `api/tests/test_ai_search.py` -- `narrowed_by` wire 테스트 신설, DW-593 실측 증거 테스트(500+CORS) 신설.
- `api/tests/test_demo_acceptance.py` -- dead-end 검사 핵심어 갱신(새 문구 기준).
- `api/tests/test_live_smoke.py` -- pathC에 `narrowed_by` 단언 추가.
- `docs/conventions.md` -- §4에 `narrowed_by` 필드 문서화, `route` 미노출 확정 문구 정리.
- `web/src/lib/api/aiSearch.ts` -- `narrowed_by` 타입+매핑+빈배열 방어(리뷰 패치) 동시 반영.
- `web/src/lib/api/aiSearch.test.ts` -- `narrowed_by` 매핑 테스트(있음/없음/깨진 형태/빈 배열).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-593 closed(리뷰 패치로 resolution 문구 정정), DW-597·DW-598 신규 open.
- `_bmad-output/implementation-artifacts/epic-13-context.md` -- (step-01 라우팅 단계에서 재컴파일, DW-560 표기 정정 후속 — 이 스토리 구현 자체와는 별개)

**Review findings breakdown:** 4개 리뷰 레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행. patch 5건(medium 1, low 4) 전부 적용·재검증 완료(G1류 dead-end 게이트 실측 재확인 포함). defer 0건. reject 8건(medium 1, low 7 — 이미 스펙 Design Notes가 검토·결정한 트레이드오프, 프로젝트 관례상 과설계, 실측으로 반증된 항목 포함). intent_gap 0건, bad_spec 0건.

**Follow-up review recommendation:** true (`3×medium(1) + 1×low(4) = 7 ≥ 5`).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **355 passed, 84 skipped**(패치 전후 동일 — 패치가 기존 스위트를 안 건드림, 신규 empty-array 테스트는 web 쪽).
- `cd web && npm run lint && npm run test` → 무경고, **305 passed / 32 files**(패치로 빈 배열 테스트 1건 추가돼 304→305).
- `RUN_LIVE_SMOKE=1 pytest tests/test_live_smoke.py` → **5 passed**(실제 Gemini+로컬 Supabase, pathC가 새 Voice 문구+narrowed_by 실제 반환).
- `run_phase_b.py --subset C1,C2,C3` + `score_ab.py` → 라우팅 3/3, **dead-end: 0, gate: PASS**(리뷰 패치로 갱신된 `REDIRECT_MARKERS` 기준으로 재확인 — 오케스트레이터가 독립적으로 재실행해 확인).
- red→green류 실측: 패치 전 `.venv/bin/python`으로 REDIRECT_MARKERS 변경 전 상태를 재확인해, 옛 마커 2개가 실제로 새 문구에 없음을 grep으로 직접 확인 후 패치.
- Matrix Test Audit: I/O 매트릭스 3행 전부 실행·통과하는 테스트로 커버됨을 확인(REJECT 고정값·다른 라우트 None·응답조립실패 500+CORS).

**Residual risks:**
- `narrowed_by`는 REJECT에서 값만 배선되고 실제 탭 가능한 "재제안 칩" UI(web/app)는 없다(DW-597, `clarify.chips`와 동일 경계).
- SQL/HYBRID 0건 응답에는 `narrowed_by`가 확장되지 않는다 — FR17 기존 일반 안내를 그대로 유지(DW-598).
- Flutter 앱은 `narrowed_by`(및 여전히 `clarify`)를 파싱하지 않는다 — 기존 DW-592/DW-587과 같은 경계, 이번 스토리가 만든 결함은 아님.
- `narrowed_by`의 값이 실제 대화 맥락에서 복원된 "원 조건"이 아니라 고정 예시라는 해석 차이가 있을 수 있음(스펙 Design Notes가 명시적으로 검토·결정한 트레이드오프, Review Triage Log 참조).

---

### 2차 리뷰 패스 (2026-07-31, followup)

**Status:** done

**이 패스가 바꾼 것:** 코드 동작은 그대로다 — 1차 패스가 남긴 **검증 장치의 구멍**을 메웠다. 핵심은 1차 리뷰 패치 자체가 dead-end 게이트를 약화시켰다는 발견이다: `REDIRECT_MARKERS`에 들어간 `"차장님"`이 행동 유도가 아닌 페르소나 호칭이라 OR 판정 게이트가 구조적으로 항상 통과하게 됐고, 함께 빠진 `"용도를 알려주시면"` 때문에 FR17 0건 재유도 문구가 반대로 dead-end로 오분류되고 있었다.

**Files changed (2차):**
- `api/scripts/score_ab.py` -- `REDIRECT_MARKERS`를 행동 유도 문구 3개로 교체(`"차장님"` 제거, `"용도를 알려주시면"` 복구).
- `api/tests/test_ab_scoring.py` -- `is_redirect(_GUARD_ANSWER)`·`is_redirect(_EMPTY_FALLBACK)` 결합 검사 신설(주석에만 있던 계약을 실행되는 검사로).
- `api/tests/test_demo_acceptance.py` -- `_GUARD_ANSWER`와 EXPERIENCE.md Voice 표 문구의 리터럴 동등 단언 추가.
- `api/tests/test_graph.py` -- CLARIFY 두 분기(상한 이내/초과)에 `narrowed_by is None` 단언 추가, `narrowed_by` 고정값 단언을 정확한 상수 비교로 강화.
- `docs/conventions.md` -- §4 REJECT 판별자(`narrowed_by !== null`)에 유효 조건·동반 수정 의무 명시(DW-598이 깨뜨릴 규칙).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-599·DW-600·DW-601 신규 open(기존 엔트리 무수정).

**Review findings breakdown (2차):** 4개 레이어 병렬. patch 6(medium 2, low 4) 전부 적용·red→green 실측. defer 3(전부 low, DW-599~601). reject 9(medium 1, low 8 — 도달 불가 방어, 형제 관례와 일치, 실측 반증, 1차 판단 유지 항목). intent_gap 0, bad_spec 0.

**Follow-up review recommendation:** true (`3×medium(2) + 1×low(4) = 10 ≥ 5`).

**Verification performed (2차, 전부 직접 실행):**
- `api` 단위 스위트 → **356 passed, 84 skipped**(신규 결합 검사 1건 추가로 355→356).
- red→green 실측 4건 — ① 마커를 1차 상태(`"차장님"`)로 되돌림 → `test_redirect_markers_actually_match_the_shipped_answers` red ② 거절 문구 리워드 → `test_cm1_decline_is_not_dead_end` red ③ `_clarify_step` 정상 분기에 leak 주입 → `test_route_CLARIFY_calls_clarify_only` red ④ 상한 초과 분기에 leak 주입 → `test_clarify_turn_cap_forces_doc_fallback` red. 매번 원복 후 green 재확인, app 코드 diff 0.
  - ⚠️ 이 과정에서 1차 검증의 한 주장이 재현되지 않았다: `_clarify_step`의 **첫 번째** `return`은 상한 초과 분기라, 거기에 leak을 넣으면 정상 분기 테스트가 안 타서 초록으로 남는다. 분기별로 따로 심어야 실제로 잡힌다 — 그래서 두 테스트 모두에 단언을 넣었다.
- 프리즈 baseline 오프라인 재채점 — `docs/g2-baseline.json`·`g2-baseline-partial.json`의 C1~C6 답변을 옛/현/신 마커 세 세트로 채점해 전부 `redirect=True` 확인(마커 조정이 G2 baseline을 깨지 않음을 실측).
- 라이브 G1 게이트 확대 재실행 — `run_phase_b.py --subset C1,C2,C3,C4,C5,C6,M9`(실제 Gemini + 로컬 Supabase, 7 item 실패 0) → `score_ab.py` → **라우팅 8/8, 오염 0, dead-end 0, 게이트 PASS**. 1차가 C1~C3만 봤던 커버리지 공백을 닫았다(스펙 Block-If 조건 재확인).
- `RUN_LIVE_SMOKE=1 pytest tests/test_live_smoke.py` → **5 passed**.
- `cd web && npm run lint && npm run test` → 무경고, **305 passed / 32 files**(웹 코드 무변경, 회귀 확인용).

**Residual risks (2차 추가):**
- `narrowed_by`가 answer 문장으로 조립되지 않아 정본 AC의 "결정론 템플릿이 조립" 요구가 미이행 상태다(DW-600 — 13.6이 같은 함수를 열 때 처리).
- `conventions.md` §4의 REJECT 판별자는 DW-598이 채택되는 순간 깨진다 — 문서에 경고를 박았을 뿐 실행되는 검사는 없다(확장하는 쪽이 지켜야 하는 계약).
- `_EMPTY_FALLBACK`이 Voice 표와 다른 상태로 남아 있다(DW-599).

---

### 3차 리뷰 패스 (2026-07-31, followup)

**Status:** done

**이 패스가 바꾼 것:** 런타임 코드는 한 줄도 안 바뀌었다 — 2차가 세운 검증 장치가 **한 방향으로만** 작동한다는 것이 이번 발견이다. 2차는 "마커가 죽어서 게이트가 통과 못 하는" 실패를 막는 검사를 만들었지만, 정작 2차가 손으로 잡아낸 실패(마커가 **넓어져서** 게이트가 항상 통과하는 것)는 그 검사가 못 본다 — 실측으로 `"차장님"`을 되돌려도 356건 전량 초록이었다. 출고 문구에서 유도 절만 걷어낸 변형을 음성 대조군으로 박아 그 방향을 닫았다. 나머지 둘은 계약 정본의 공백 메우기다(빈 배열 의미, 모듈 docstring).

**Files changed (3차):**
- `api/tests/test_ab_scoring.py` -- 결합 검사에 음성 대조군 1건 추가(유도 절 없는 거절 변형 → dead-end 판정).
- `docs/conventions.md` -- §4 `narrowed_by`에 빈 배열(`[]`) 규약 명문화(= `null` 취급, 판별은 "비어 있지 않은 문자열 배열"로).
- `api/app/graph/graph.py` -- 모듈 docstring의 공통 계약에 `narrowed_by` 반영(주석만).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-602 신규 open(기존 엔트리 무수정).

**Review findings breakdown (3차):** 4개 레이어 병렬(adversarial·edge-case-hunter·verification-gap·intent-alignment). patch 3(medium 1, low 2) 전부 적용. defer 1(low, DW-602). reject 15(medium 3, low 12 — 이미 DW로 등재된 항목, 3연속 동일 지적, 실측으로 반증된 항목, 도달 불가 방어, A2/A3 위반 제안). intent_gap 0, bad_spec 0.

**Follow-up review recommendation:** true (`3×medium(1) + 1×low(2) = 5 ≥ 5`).

**Verification performed (3차, 전부 직접 실행):**
- red→green 실측 1건 — `REDIRECT_MARKERS`에 `"차장님"` 복원 → 신규 음성 대조군 red(`assert not True`) 확인 → 원복 후 green, `git diff HEAD -- api/scripts/score_ab.py` 무변경으로 바이트 동일 증명.
- `api` 단위 스위트 → **356 passed, 84 skipped**(단언만 추가돼 건수 불변).
- `cd web && npm run lint && npm run test` → 무경고, **305 passed / 32 files**(web 코드 무변경, 회귀 확인용).
- `RUN_LIVE_SMOKE=1 pytest tests/test_live_smoke.py`(실제 Gemini + 로컬 Supabase) → **5 passed**.
- 실측으로 반증한 리뷰 주장 2건 — ① `epic-13-context.md` 재생성이 지운 DW 포인터 3건(554·559·560)이 전부 `status: done`임을 장부에서 확인 ② `router_node._fallback_route`가 매물 신호 없는 질의에 `REJECT`를 준다는 것을 코드로 확인(DW-602의 근거).
- `run_phase_b.py` + `score_ab.py` 라이브 G1 게이트는 **재실행하지 않았다** — 이 패스의 diff에 런타임 코드가 없고 `score_ab.py`가 HEAD와 바이트 동일해 결과가 달라질 수 없다(2차가 C1~C6+M9 전량으로 실행한 결과가 그대로 유효). 유료 호출을 반복하지 않기 위한 의도적 생략이며, 마커 의미 판정은 이번에 추가한 오프라인 음성 대조군이 대신 상시로 지킨다.

**Residual risks (3차 추가):**
- DW-600의 `location:`이 존재하지 않는 줄 번호(`epic-13-context.md` L71·L93, 실제 파일은 55줄 — 해당 서술은 L28·L41)를 가리킨다. 기존 장부 엔트리 수정 금지 지시에 따라 손대지 않았다 — **orchestrator가 정정해야 한다.**
- 라우터 폴백 REJECT가 거짓 `narrowed_by`를 실어 보낸다(DW-602). 지금은 렌더 소비처가 없어 사용자에게 안 보이지만, DW-597(칩 UI)이 그 방어의 마지막 자리다.
- 음성 대조군은 **페르소나 문장에서 온 넓은 마커**를 잡는다. 그 밖의 넓은 낱말(흔한 조사·명사)까지 일반적으로 막지는 못한다 — 검사 docstring에 그 한계를 적어 두었다.
- `response_model` 재검증 잔여 노출면(DW-601)은 이번 패스에서도 미해결이며, adversarial 레이어가 프로브로 **실제 재현**했다(도달 조건은 여전히 미충족).
