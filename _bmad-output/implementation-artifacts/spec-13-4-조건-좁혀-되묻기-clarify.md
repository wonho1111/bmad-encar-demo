---
title: '13.4 조건 좁혀 되묻기 (CLARIFY)'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: '42824af69dd2a4d6515951119a3cee7560d0606d'
final_revision: 'b55f495d173bdb6b29393f0881a45091628dbb56'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** CLARIFY 라우트(13.2가 신설)는 아직 `doc_rag_node`(경로 B, 의미검색)로 임시 배선돼 있어 애매한 질의에 되묻지 않고 곧장 매물을 던진다. 응답 계약에 `clarify` 필드가 없어 칩 UI를 만들 수 없고(CR5), 되묻기 상한이 순전히 클라이언트 자율에만 맡겨져 있어 서버가 아무것도 강제하지 못한다(DW-563 — CLAUDE.md B9 위반 소지로 13.4 스펙 작성 시점에 결정하도록 트리거돼 있던 항목).
**Approach:** 신규 `clarify_node`가 고정 템플릿(추가 LLM 호출 없음, CR5)으로 되묻는 질문+칩을 만들어 CLARIFY 분기를 여기로 재배선한다. `SearchResponse`에 `clarify?: {question, chips[]}`를 추가한다. 되묻기 상한(2~3턴)은 클라이언트가 이미 요청마다 보내는 `context`의 길이로 서버가 직접 세어, 상한 초과 시 클라이언트 협조 여부와 무관하게 서버가 `doc_rag_node`로 실제 결과를 강제 제시한다(DW-563 해결 — 새 인프라·새 필드 없이 서버가 이미 받는 값만으로 강제).

## Boundaries & Constraints

**Always:**
- `clarify_node(query)`는 LLM/DB를 호출하지 않는다(CR5 "추가 LLM 없음") — 고정 문자열 질문 1개 + 고정 칩 배열을 반환한다. `guard_node`(REJECT 고정 템플릿)와 동일한 결정론 패턴.
- CLARIFY 분기가 상한 이내면 `{"answer", "listings": [], "clarify": {"question", "chips"}}`를 반환한다. `answer`와 `clarify.question`은 같은 고정 문자열이다(단일 출처, EXPERIENCE.md Voice 표 "AI 되묻기" 문구 그대로).
- 되묻기 상한 = 3턴(`_CLARIFY_TURN_CAP`, "최대 2~3턴" 상단값을 코드가 요구하는 단일 정수로 확정). 서버가 `len(context or []) // 2`로 이미 지난 턴 수를 직접 계산한다(DW-563 — 클라이언트가 스스로 멈추기를 기다리지 않는다). 이 값이 상한 이상이고 route가 CLARIFY면, `clarify_node` 대신 `doc_rag_node(query)`를 호출해 현재까지의 질의(맥락화된 `effective_query`)로 실제 매물을 반환한다. 매물이 1건 이상이면 answer 뒤에 고정 안내 문구("여기까지의 조건으로 찾아드릴게요. 더 좁히시려면 검색 후 필터를 이용해보세요.")를 덧붙이고, 0건이면 `doc_rag_node`의 기존 FR17 안내(조건 완화 유도)를 그대로 두고 안내 문구를 덧붙이지 않는다(0건인데 "필터로 더 좁혀라"라고 말하는 모순 방지). 이때 `clarify` 필드는 항상 `None`(칩 없음 — 더 이상 안 묻는다는 신호).
- `answer_node`는 `clarify` 키가 있으면(None 포함) 그대로 통과시킨다 — 새 답을 짓지 않는다(함정 #3 승계).
- `SearchResponse`/`/ai/search`에 `clarify: ClarifyPayload | None` 필드를 추가한다(CR5). `route`·`narrowed_by`는 이번에 추가하지 않는다(아래 Never).
- 3곳 락스텝(`RouterDecision` Literal·`_fallback_route`·`_route_decision`)은 13.2가 이미 CLARIFY를 포함해 확정했으므로 이번 스토리는 손대지 않는다 — 분류 자체는 불변, 분기 목적지만 바뀐다.

**Block If:**
- 로컬 Supabase+`GEMINI_API_KEY`로 대표 되묻기 질의("패밀리카로 무난한 거" 등) 1~2개를 직접 실행했을 때 `clarify` 페이로드가 비거나 형식이 어긋나고, 원인이 명백한 코드 버그가 아니라 요구사항 해석 문제면 HALT(status blocked, blocking condition `clarify 페이로드 형식 확정 실패`).

**Never:**
- `narrowed_by`·공개 `route` 필드는 `SearchResponse`에 추가하지 않는다(13.5/13.6 소관 — 13.3 Never 절과 동일 경계 승계).
- REJECT(거절) 고정 템플릿·`guard_node` 내용은 손대지 않는다(13.5 소관).
- 되묻기 칩을 눌렀을 때의 클라이언트 렌더링·상태 관리(petrol 채움 등)는 만들지 않는다 — 이번 스토리는 API 계약과 서버측 상한 강제까지만이다. ✎ 후속 코드리뷰 정정(intent-alignment): Flutter 앱 쪽은 Story 16.5가 이미 맡고 있지만, **웹 쪽 렌더링 스토리는 현재 에픽 카탈로그(`epics-increment-2026-07-12.md`)에 존재하지 않는다** — 다음 스프린트 플래닝에서 새로 만들어야 한다(DW-587).
- `context`(FR18 멀티턴)를 서버·DB에 저장하지 않는다 — 턴 수 계산도 요청마다 받은 배열 길이를 그 자리에서만 쓰고 버린다(무상태 불변식 승계).
- 진짜 세션 저장소(interrupt()/체크포인터 등)를 도입하지 않는다(아키텍처 Never 승계, 재사용 우선).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 애매 질의, 상한 이내 | "패밀리카로 무난한 거", context 길이 0~4(0~2턴) | route=CLARIFY, listings=[], clarify={question, chips 3개} | No error |
| 애매 질의, 상한 초과 | 동일 질의, context 길이 6 이상(3턴 이상 완료) | clarify=None, doc_rag_node 결과. 매물 1건 이상이면 고정 안내 문구 덧붙임, 0건이면 doc_rag_node의 FR17 안내 그대로(문구 모순 방지) | No error |
| 상한 경계값 | context 길이 정확히 6(3턴) | 상한 초과로 처리(강제 제시) — `>=` 비교, 3턴째까지만 되묻기 허용 | No error |
| 칩 탭 후 재질의 | 사용자가 칩 값("SUV")을 다음 메시지로 전송 | 기존 `contextualize_query`가 이어붙여 독립 질의로 재작성 → 다음 턴 라우터가 SQL/HYBRID로 재분류 가능(회귀 없음, 라우터 불변) | No error |

</intent-contract>

## Code Map

- `api/app/graph/clarify_node.py` -- 신규. 고정 템플릿 되묻기 질문+칩 반환(LLM/DB 없음).
- `api/app/graph/graph.py` -- CLARIFY 분기를 `clarify_node`로 재배선(`_clarify_step` 신설, 상한 계산·초과 시 `doc_rag_node` 강제 폴백 포함). `SearchState`에 `clarify`·`clarify_turns` 키 추가. `_answer_step`이 `clarify` 통과. `run_search`가 `context` 길이로 `clarify_turns`를 계산해 초기 state에 싣고, 반환 dict에 `clarify` 포함.
- `api/app/graph/answer_node.py` -- `clarify` 키 통과(있으면 그대로, 없으면 None).
- `api/app/graph/doc_rag_node.py` -- 변경 없음(강제 폴백이 함수만 재사용).
- `api/app/schemas/ai.py` -- `ClarifyPayload(question: str, chips: list[str])` 신규, `SearchResponse.clarify` 필드 추가.
- `api/routers/ai.py` -- 응답 조립에 `clarify=result.get("clarify")` 추가.
- `api/tests/test_clarify_node.py` -- 신규 단위 테스트(고정 페이로드 형식).
- `api/tests/test_graph.py` -- CLARIFY 분기 테스트 교체(clarify_node 호출 확인) + 상한 초과 강제 폴백 테스트 신설 + `answer_node` clarify 통과 테스트.
- `api/tests/test_live_smoke.py` -- pathB(CLARIFY) 단언 강화(clarify 페이로드 확인) + 상한 초과 라이브 케이스 신설.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-563 closed(이번 결정 근거), DW-586 신규 등재(open — 아래 Design Notes 참조).

## Tasks & Acceptance

**Execution:**
- `api/app/graph/clarify_node.py` -- `clarify_node(query: str) -> dict` 신설: 고정 문자열 `_CLARIFY_QUESTION`("조건을 조금만 좁혀볼게요 — 칩을 눌러도 되고, 직접 입력해도 돼요.", EXPERIENCE.md Voice 표와 동일)과 고정 `_CLARIFY_CHIPS`(가격·차종·연료 세 축의 대표값: `["3천만원 이하", "SUV", "전기차"]`)를 반환. `{"answer": _CLARIFY_QUESTION, "listings": [], "clarify": {"question": _CLARIFY_QUESTION, "chips": list(_CLARIFY_CHIPS)}}`.
- `api/app/schemas/ai.py` -- `ClarifyPayload(BaseModel)` 추가(`question: str`, `chips: list[str]`). `SearchResponse`에 `clarify: ClarifyPayload | None = None` 필드 추가(기존 `answer`/`listings` 순서 유지, additive라 회귀 없음).
- `api/app/graph/answer_node.py` -- `answer_node(result)`가 `out["clarify"] = result.get("clarify")`를 기존 `{"answer", "listings"}` 계약에 추가로 채워 반환(값이 없으면 None 그대로 전달 — 새 판단 없음).
- `api/app/graph/graph.py` --
  - `clarify_node` import 추가, `doc_rag_node` import는 유지(강제 폴백에서 직접 호출).
  - `SearchState`에 `clarify: dict | None`(경로 노드가 채움)·`clarify_turns: int`(진입 시점에 계산돼 있음) 키 추가.
  - `_CLARIFY_TURN_CAP = 3`, `_CLARIFY_CAP_NOTICE = "여기까지의 조건으로 찾아드릴게요. 더 좁히시려면 검색 후 필터를 이용해보세요."` 모듈 상수 신설.
  - `_clarify_step(state)` 신설: `state.get("clarify_turns", 0) >= _CLARIFY_TURN_CAP`이면 `doc_rag_node(state["query"])`를 호출해, `listings`가 비어 있지 않을 때만 `answer`에 `_CLARIFY_CAP_NOTICE`를 덧붙이고(0건이면 doc_rag_node의 FR17 안내를 그대로 둠), `{"answer": answer, "listings": result["listings"], "clarify": None}` 반환. 상한 미만이면 `clarify_node(state["query"])` 호출해 `{"answer", "listings", "clarify"}` 그대로 반환.
  - `_doc_step`·`g.add_node("doc", ...)`·`g.add_edge("doc", "answer")` 제거(이번 변경으로 고아가 됨 — CLARIFY 전용이었고 강제 폴백은 `_clarify_step` 안에서 `doc_rag_node`를 직접 호출하므로 별도 그래프 노드가 더 필요 없다).
  - `g.add_node("clarify", _clarify_step)` 추가, `add_conditional_edges`의 `"CLARIFY"` 매핑을 `"doc"`→`"clarify"`로 교체, `g.add_edge("clarify", "answer")` 추가.
  - `_answer_step`이 `answer_node(...)` 호출 시 `"clarify": state.get("clarify")`를 함께 전달.
  - `run_search(query, context)` -- `COMPILED_GRAPH.invoke`에 `"clarify_turns": len(context or []) // 2`를 추가로 싣는다. 반환 dict에 `"clarify": final_state.get("clarify")` 추가.
- `api/routers/ai.py` -- `SearchResponse(answer=..., listings=..., clarify=result.get("clarify"))`로 교체.
- `api/tests/test_clarify_node.py` -- (1) 반환 dict가 `{"answer", "listings": [], "clarify": {"question", "chips"}}` 형태인지, (2) `clarify["question"] == answer`(단일 출처 확인), (3) `chips`가 길이 3의 비어있지 않은 문자열 리스트인지.
- `api/tests/test_graph.py` -- `test_route_CLARIFY_calls_doc_only`를 `test_route_CLARIFY_calls_clarify_only`로 교체(`_patch_nodes`에 `clarify` 페이크 추가, `doc`는 더 이상 CLARIFY 경로에서 호출되지 않음을 확인). 신규: `test_clarify_turn_cap_forces_doc_fallback`(`clarify_turns=3`, `doc_rag_node`가 매물 1건 이상 반환하도록 페이크 → `doc_rag_node`만 호출되고 `clarify_node`는 호출 안 됨, 출력 `clarify is None`, answer에 `_CLARIFY_CAP_NOTICE` 포함 확인). 신규: `test_clarify_turn_cap_forced_but_zero_listings_no_notice`(같은 상한 초과 조건, `doc_rag_node`가 0건 FR17 안내를 반환하도록 페이크 → answer에 `_CLARIFY_CAP_NOTICE`가 덧붙지 않고 doc_rag_node 문구 그대로임을 확인, 모순 방지 회귀). 신규: `test_clarify_turn_cap_not_yet_reached_still_clarifies`(`clarify_turns=2`, 여전히 `clarify_node` 호출). `test_answer_node_*`군에 `test_answer_node_passes_through_clarify_field` 추가(`answer_node({"answer":"q","listings":[],"clarify":{"question":"q","chips":["a"]}})` → 출력에 `clarify` 키 그대로 보존, `test_answer_node_clarify_absent_defaults_to_none`도 추가). `test_run_search_contextualizes_before_graph`가 모킹하던 `doc_rag_node`를 `clarify_node`로 교체(현재 CLARIFY 경로가 실제로 부르는 노드가 바뀌었으므로).
- `api/tests/test_live_smoke.py` -- `test_live_smoke_pathB`에 `assert out["listings"] == []`·`assert out["clarify"] is not None`·`assert out["clarify"]["chips"]` 단언 추가(현재는 route만 보고 통과해 13.3의 DW-577류 공백을 되풀이할 뻔했다). 신규 `test_live_smoke_clarify_cap_forces_results`: 6개 이상의 더미 `context` 턴과 함께 같은 질의를 호출해 `out["clarify"] is None`이고 `out["listings"]`가 list임을 확인(상한 강제가 라이브로 실제 동작하는지, B4).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-563을 `status: done`(resolution: 아래 Design Notes 요약)으로 닫는다. DW-586을 신규 등재(open, `/ai/search` 전체에 대한 사용자당 요청 빈도 제한이 아예 없다는, 이번 분석에서 드러난 더 넓은 잔여 gap — 코드 변경 없이 장부에만 기록).

**Acceptance Criteria:**
- Given CLARIFY 경로(신규 노드), when 광범위 질의가 되묻기 상한 이내로 들어오면, then `interrupt()`/체크포인터 없이 되묻기 문장이 `answer`로, 구조화된 `clarify: {question, chips[]}`가 응답에 담긴다(FR46, CR5, 직접 로컬 실행으로 확인, B4).
- Given `clarify.chips` 중 하나를 다음 사용자 메시지로 보낸 멀티턴, when `contextualize_query`가 이어붙이면, then 재작성된 독립 질의가 그래프로 들어간다(회귀 없음 — 기존 4.6 배선 그대로).
- Given 이미 3턴(`context` 길이 6 이상)만큼 되묻은 대화, when 라우터가 다시 CLARIFY로 분류해도, then 서버가 `clarify` 없이 `doc_rag_node` 결과 + 고정 안내 문구로 현재 조건의 실제 매물을 강제 제시한다(클라이언트 협조 여부와 무관 — DW-563 해결, 직접 실행으로 확인, B4).
- Given 로컬 Supabase+`GEMINI_API_KEY`, when 대표 되묻기 질의로 라이브 스모크를 실행하면, then route=CLARIFY·listings=[]·clarify 페이로드가 실제로 관측된다(라이브 실행·관찰, B4).
- Given 이번 스토리 완료, when `deferred-work.md`를 확인하면, then DW-563이 근거와 함께 closed이고 DW-586이 신규 open으로 등재돼 있다(B8).

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 3, low 0)
- defer: 1: (high 0, medium 1, low 0)
- reject: 10: (high 0, medium 3, low 7)
- addressed_findings:
  - `[medium]` `[patch]` `docs/conventions.md` §4의 "AI 검색 응답" 항목이 신규 `clarify` 필드를 문서화하지 않고 있었다(project-context.md 규칙 1 — 교차 경계 값의 정본은 conventions.md) — 필드와 채워지는 조건을 한 줄 추가.
  - `[medium]` `[patch]` 스펙 Never 절이 웹 칩 렌더링을 "Story 16.5/웹 대응 스토리 소관"으로 미뤘는데, 실제 에픽 카탈로그엔 웹 스토리가 존재하지 않았다(16.5는 Flutter 전용) — 게다가 `web/src/lib/api/aiSearch.ts`의 `SearchResult` 타입에 `clarify` 필드 자체가 없어 다음 사람이 필드 존재조차 몰랐다. Never 절 문구를 사실대로 정정하고, DW-587을 신규 등재하고, `aiSearch.ts`에 타입만(파싱·렌더 로직 없이) 추가해 가시성을 확보했다.
  - `[medium]` `[patch]` `SearchResponse.clarify`가 실제 HTTP/TestClient 직렬화 경계에서 전혀 검증되지 않고 있었다(`test_ai_search.py`의 모든 기존 테스트가 `clarify` 키 없는 dict만 모킹) — `routers/ai.py`의 `clarify=result.get("clarify")` 라인을 되돌려 전체 스위트를 재실행해도 초록임을 실측으로 확인해 실재하는 gap임을 검증했다. 이 과정에서 그 라인이 디스크에 실제로는 없던(원인 불명, 세션 중 유실 추정) 상태였음을 발견해 복원하고, `test_ai_search.py`에 wire-level 케이스 2건(clarify 있음/없음)을 신규 추가해 red→green으로 확인.
  - `[medium]` `defer` `api/scripts/score_ab.py`의 `doc_hit` 지표가 이번 라우팅 변경(CLARIFY가 더는 doc_rag_node를 타지 않음)으로 CLARIFY 항목에 대해 조용히 항상 false가 된다 — 지표 자체는 어떤 게이트도 좌우하지 않고(gate_pass/result_mean 미반영), 이 스토리 범위 밖(13.1~13.3의 score_ab.py 드리프트 이월 관례와 동일)이라 deferred-work.md에 신규 등재만 함.
  - `[low]` `reject` epic-13-context.md의 CLARIFY 턴상한 서술이 이번 결정(서버 강제) 이전 문구 그대로다 — 이 파일은 계획문서 변경 시에만 재생성되는 캐시이고, 실제 정본(spec·deferred-work.md)은 이미 정확히 갱신됐다.
  - `[low]` `reject` 턴 카운트가 "연속 CLARIFY 횟수"가 아니라 "대화 전체 길이"라는 지적 — 스펙 Design Notes가 이미 이 근사치를 명시적으로 인지·수용한 트레이드오프다.
  - `[low]` `reject` `len(context)//2`가 user/assistant 교대를 가정한다는 지적 — 이미 문서화된 더 심각한 우회(`context: []` 위장)에 지배되는 하위 케이스라 별도 patch 가치가 낮다.
  - `[low]` `reject` `ClarifyPayload.chips`에 스키마 레벨 길이/내용 검증이 없다는 지적 — chips는 서버가 스스로 만드는 상수값일 뿐 클라이언트 입력이 아니라 B9(클라이언트 값 불신)의 트리거 대상이 아니고, 기존 유닛테스트가 이미 그 불변식을 지킨다.
  - `[low]` `reject` 상한 초과 시 안내 문구가 doc_rag_node 답변 뒤에 이어붙어 어색할 수 있다는 지적 — 실제 문자열을 조립해 확인한 결과 자연스러운 세 문장으로 읽혀 결함이 아니다.
  - `[low]` `reject` 상한 테스트 3건이 `contextualize_query`를 모두 모킹해 누적 조건이 실제로 전달되는지 검증하지 않는다는 지적 — 그 책임은 별도 기존 테스트(`test_run_search_contextualizes_before_graph` 등)가 이미 지고 있고, 상한 테스트는 라우팅 분기 자체만 검증하면 되는 별개 관심사다.
  - `[low]` `reject` DW-563을 "done"으로 닫으며 라이브 스모크 실행 로그를 diff에 남기지 않았다는 지적 — 오케스트레이터가 `RUN_LIVE_SMOKE=1`로 직접 재실행해 5 passed를 독립 확인했고(B4), 로그를 인라인하지 않는 것은 기존 DW 종료 항목들의 관례와 같다.
  - `[medium]` `reject` 되묻기 상한 강제 위치가 아키텍처 불변식 I12(클라 강제)의 문자 그대로와 어긋난다는 지적 — DW-563 해결로 이미 의도적으로 재검토·기록된 결정이다(스펙 Design Notes).
  - `[medium]` `reject` G1(되묻기 과다발동율)을 Phase B 전량 재측정하지 않았다는 지적 — 이번 스토리는 라우팅 분류 코드를 손대지 않았고(Never 절), 13.1~13.3의 확립된 선례(대표 질의 재확인으로 충분)를 따라 대표 3개 재확인으로 회귀 없음을 실측했다.
  - `[medium]` `reject` 상한 초과 강제 폴백에서 `doc_rag_node` 호출이 try/except로 감싸이지 않아 인프라 장애 시 500이 날 수 있다는 지적 — `doc_rag_node`의 fail-loud는 이 프로젝트가 이미 도처에서 채택한 의도적 설계이고, 이번 변경은 그 호출 빈도를 오히려 줄인다(이전엔 모든 CLARIFY가 doc_rag_node를 탔지만 이제는 상한 초과 시에만).

### 2026-07-31 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 3: (high 0, medium 2, low 1)
- reject: 8: (high 0, medium 2, low 6)
- addressed_findings:
  - `[medium]` `[patch]` `web/src/lib/api/aiSearch.ts`의 `searchAi()`가 `clarify`를 응답에서 **꺼내지 않고 버리고** 있었다 — 1차 리뷰가 "가시성 확보"로 추가한 타입만 있고 매핑이 없어, 타입은 "필드가 있다"고 말하는데 런타임 값은 영원히 `undefined`였다(나중에 칩 UI를 만드는 사람이 `if (result.clarify)`로 분기해도 아무 일도 안 일어나고 오류도 안 남 = 조용한 실패). 매핑 한 줄(`clarify: result.clarify ?? null`)을 추가하고, `aiSearch.test.ts`에 fetch를 모킹한 매핑 테스트 2건(있음/없음)을 신설했다. red→green 실측: 매핑 줄을 지우면 신규 2건이 실제로 빨갛게 실패, 복원하면 9 passed.
  - `[medium]` `[patch]` `docs/conventions.md` §4가 `clarify`의 채움 조건을 `route === 'CLARIFY'`로 문서화했는데, **응답에 `route` 필드가 없다**(13.4 Never 절이 명시적으로 제외 — 13.5/13.6 소관). 교차 경계 정본을 읽고 클라이언트를 짜는 사람이 절대 성립하지 않는 분기를 쓰게 되는 문구였다. "클라이언트는 `clarify !== null`로만 판별한다 / 응답에 `route`는 없다"를 명시하도록 정정.
  - `[low]` `[patch]` `test_live_smoke_clarify_cap_forces_results`가 `clarify is None` + `isinstance(listings, list)`만 단언해 **상한 강제를 전혀 증명하지 못했다** — 두 조건 모두 SQL/HYBRID/REJECT 어느 라우트에서나 참이라, 상한 분기를 통째로 지워도 초록으로 남는다(더미 context가 실제 `contextualize_query`를 거치며 라우트가 바뀔 수 있어 더 그렇다). `route == "CLARIFY"` 단언과, 매물이 나왔을 때 `_CLARIFY_CAP_NOTICE`가 붙었는지 보는 단언을 추가했다. 라이브 재실행으로 실제 통과 확인.
  - `[low]` `[patch]` `test_clarify_node.py`가 **형식만** 보고 문구·칩 내용을 하나도 고정하지 않아, `_CLARIFY_QUESTION`을 엉뚱한 말로 바꿔도 전부 초록이었다 — 이 문구는 CLARIFY 경로의 **유일한** 사용자 노출 출력이다(listings는 항상 []). 형제 노드 `guard_node`가 문구 핵심 단어를 단언하는 선례를 따라 문구 단언을 추가하고, 칩은 길이 하한(`len(c) >= 2`)으로 막았다. ✎ 실측 정정: 리뷰어가 제시한 실패 시나리오("`_CLARIFY_CHIPS`가 문자열이면 pydantic이 거부해 500")는 **반증됐다** — 노드가 `list(...)`로 감싸 반환하므로 `['a','b','c']`가 되어 500이 아니라 "한 글자 칩 3개"가 조용히 나간다. 그 실제 실패 형태를 잡도록 검사를 고쳤고, 이 검사가 **안 보는 것**(칩 문구의 적절성 — 제품 판단이라 의도적으로 안 얼림)을 검사 옆에 적었다.
  - `[medium]` `defer` 아키텍처 불변식 I12가 여전히 "되묻기 cap = 클라 강제"라고 못박고 있어, 웹 칩 스토리·앱 16.5가 클라이언트에 두 번째 상한을 또 만들 위험이 있다 → DW-589 신규 등재.
  - `[medium]` `defer` SM3(데모 인수) 판정이 이제 벡터 경로 장애를 못 잡고(게이트가 `clarify_node`를 모킹), PRD·epics의 "두 경로 시연" 문구는 갱신되지 않은 채 하위 문서만 바뀌었다 → DW-590 신규 등재. 벡터 경로 자체는 라이브 실측으로 살아 있음을 확인했다(강제 폴백이 매물 5건 + 가이드 인용 반환).
  - `[low]` `defer` DW-563의 잔여 우회(`context: []` 위장)를 다시 트리아지할 열린 항목이 없다(DW-586의 trigger는 과금 급증인데 이 우회는 과금 신호를 남기지 않는다) → DW-591 신규 등재.
  - `[medium]` `reject` 되묻기 상한이 "연속 CLARIFY 횟수"가 아니라 "대화 전체 길이"라 SQL 검색을 3회 한 사용자는 칩을 못 본다는 지적(4개 렌즈 중 4개가 제기) — 스펙 Design Notes가 **바로 이 시나리오를 문장으로 적어 수용**했고("그 앞의 3턴이 CLARIFY였든 아니든 결과를 강제 제시한다"), intent-contract가 계산식 자체를 지시했다. 해석 문제가 아니라 기록된 트레이드오프다.
  - `[medium]` `reject` 칩을 렌더하는 클라이언트가 아직 없는데 답변이 "칩을 눌러도 되고"라고 말한다(웹 기능 후퇴) — 1차 리뷰가 이미 같은 사실을 DW-587로 등재했다. 같은 주장·같은 조치라 중복.
  - `[low]` `reject` `len(context)//2`가 user/assistant 교대를 가정해 홀수 길이에서 한 턴 늦게 걸린다 — 1차 리뷰에서 이미 같은 근거로 reject된 하위 케이스.
  - `[low]` `reject` `ClarifyPayload.chips`가 빈 배열을 허용한다 — 1차 리뷰에서 reject(칩은 서버가 만드는 상수라 클라 입력 불신 대상이 아님). 단위 테스트가 불변식을 지킨다.
  - `[low]` `reject` 상한 이내에서 같은 질문·같은 칩이 최대 3번 반복된다 — CR5("추가 LLM 호출 없음")가 고정 템플릿을 요구한 결과이며 스펙이 선택한 비용이다.
  - `[low]` `reject` 상한 초과 + 0건이면 칩도 매물도 없는 dead-end다 — 그 자리에 `doc_rag_node`의 FR17 안내("원하시는 용도나 예산을 알려주시면…")가 남아 다음 행동을 유도한다. 진짜 막다른 길이 아니다.
  - `[low]` `reject` 회색지대 질의가 라우터 흔들림에 따라 매물/칩으로 응답 형태가 갈린다 — 13.2가 확정한 라우팅 분류의 성질이고 이번 변경이 만든 것이 아니다.
  - `[low]` `reject` `epic-13-context.md`가 낡았다 — 1차 리뷰에서 reject(계획문서 변경 시 재생성되는 캐시이고 정본은 이미 정확).
  - `[low]` `reject` `test_sm3_pathB_returns_listings`의 이름이 단언과 정반대다 — 지적 자체는 사실이나, 이름을 지금 바꾸면 **기존 열린 장부 항목 DW-576이 참조하는 함수명이 끊긴다**(오케스트레이터 소유라 이 세션이 수정 불가). 이름 변경을 DW-590의 처리 항목으로 묶어 참조와 함께 옮기도록 했다.

### 2026-07-31 — Review pass (3차)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 4: (high 0, medium 2, low 2)
- reject: 11: (high 0, medium 3, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `docs/conventions.md` §4의 `clarify` 채움 조건이 **오프바이원**이었다 — "되묻기 상한(3턴)을 **넘지 않았을 때**"라고 썼는데 코드는 `>= 3`이라 정확히 3턴째부터 이미 억제한다. 게다가 무엇을 세는지(되묻기 횟수가 아니라 `context` 총 턴 수)가 적혀 있지 않아, 이 교차 경계 정본만 읽고 클라이언트를 짜는 사람은 "몇 번 더 물어볼 수 있나"를 서버와 다르게 계산하게 된다. "대화가 3턴 미만일 때만" + 세는 단위 정의로 정정.
  - `[medium]` `[patch]` 서버 상한이 발동할 수 있느냐를 좌우하는 값(웹이 보내는 `context` 턴 수)이 **어떤 검사에도 걸려 있지 않았다** — `buildContext`는 export돼 있는데 테스트가 0건이고, e2e는 `/ai/search`를 모킹해 지나간다. `MAX_CONTEXT_TURNS`를 5 이하로 줄이면 웹에서 상한이 영원히 발동하지 않는데 api·web 스위트는 전부 초록으로 남는다(앱은 같은 상수를 `app/test/ai_search_test.dart`가 이미 고정하고 있어 웹만 비어 있던 비대칭). `ChatAssistant.test.ts`를 신설해 절단 상수·빈 턴 제외·2000자 절단을 고정했다. red→green 실측: 상수를 4로 낮추면 실제로 빨갛게 실패.
  - `[low]` `[patch]` `web/src/lib/api/aiSearch.ts`가 `clarify`를 **형태 검사 없이** 그대로 통과시키고 있었다 — 같은 파일이 `listings`는 `isValidListing`으로 원소마다 검사하고 그 이유(깨진 값이 렌더 도중 터지고 try/catch 밖이라 화면 전체가 날아간다)를 주석으로 길게 적어둔 곳이다. `isValidClarify` 추가로 계약 위반 값을 null로 떨구고, 타입에서 `?`를 빼 소비처가 다뤄야 할 상태를 2가지로 줄였다. red→green 실측: 검사를 빼면 신규 4건이 실패.
  - `[low]` `[patch]` `graph.py`의 상한 관련 주석 3곳이 "이미 몇 턴 **되물었는가**"라고 서술해 실제 계산(대화 전체 길이)과 어긋났다 — 다음 사람이 주석을 믿고 클라이언트에 두 번째 상한을 만들 위험(DW-589가 이미 걱정하는 시나리오)을 키운다. 세는 대상이 총 턴 수임을 모듈 docstring·상수 주석·`SearchState` 필드 주석·`run_search` 주석에 사실대로 적었다.
  - `[low]` `[patch]` 상한의 "총 턴 수" 의미가 **문서에만** 있고 검사에는 없었다 — 기존 상한 테스트 3건은 context를 전부 되묻기처럼 생긴 턴으로만 만들어서 이 의미를 고정하지 못한다. `test_clarify_cap_counts_all_turns_not_only_clarify_turns` 신설(앞선 3턴이 전부 일반 SQL 검색이어도 강제 폴백). red→green 실측: 상한을 "되묻기 문구가 든 턴만 세기"로 바꾸면 이 검사를 포함해 3건이 빨갛게 실패.
  - `[low]` `[patch]` `test_demo_acceptance.py`의 헬퍼 주석이 "run_search가 `clarify_turns`를 넣지 않은 채 호출되므로"라고 적었는데 `run_search`는 **항상** 넣는다(context 없으면 0). 존재하지 않는 메커니즘을 설명하는 주석이라 사실대로 정정.
  - `[low]` `[patch]` 응답 계약을 복창하는 주석 3곳(`graph.py` 모듈 docstring, `routers/ai.py` docstring 2줄, `aiSearch.ts` 상단 계약 블록)이 여전히 `{answer, listings[]}`라 13.4가 추가한 `clarify`를 빠뜨렸다 — 정본(`conventions.md` §4)만 갱신되고 사본들이 늙은 상태. 셋 다 갱신하며 정본을 가리키게 했다.
  - `[medium]` `defer` 출시된 Flutter 앱이 `clarify`를 파싱조차 안 해, 13.4 이전엔 매물 카드가 나오던 애매한 질의가 앱에서 "질문 한 줄만 뜨는 화면"으로 퇴행한다. Story 16.5는 `backlog`라 착수 일정이 없다 → DW-592 신규 등재(trigger = api 운영 반영 직전 결정).
  - `[medium]` `defer` `/ai/search`의 `return SearchResponse(...)`가 try/except 밖이라, 응답 스키마 검증 실패는 그 파일 주석이 막으려던 바로 그 경로(CORS 헤더 없는 500 → 브라우저가 연결 실패로 오인)로 나간다. `listings`부터 있던 구조라 이번 결함은 아니지만 `clarify`로 노출면이 넓어졌다 → DW-593 신규 등재(trigger = 다음에 응답 필드를 추가하는 13.5/13.6).
  - `[low]` `defer` 되묻기 칩 세 축 중 하나가 UX 정본 워크스루와 다르다(구현 가격·차종·연료 vs EXPERIENCE.md "인원·예산·연료 / 7인승 칩 탭") — 동작 결함은 아니나 데모 각본과 칩 UI 담당자가 없는 칩을 전제하게 된다 → DW-594 신규 등재.
  - `[low]` `defer` 오프라인 A/B 러너의 최장 멀티턴 항목(3턴)이 상한과 정확히 1턴 차이라, 4턴 항목을 추가하거나 상한을 2로 낮추면 그 항목이 조용히 강제 폴백을 타게 된다(누구도 라우팅을 바꾼 줄 모른다) → DW-595 신규 등재.
  - `[medium]` `reject` 상한이 "연속 CLARIFY 횟수"가 아니라 "대화 전체 길이"라 일반 검색 3회 한 사용자는 칩을 못 본다 — 1·2차에서 이미 같은 근거로 reject된 항목이고, intent-contract가 계산식(`len(context or []) // 2`)을 직접 지시했으며 Design Notes가 이 시나리오를 문장으로 적어 수용했다. 다만 "주석이 이 사실과 어긋난다"·"검사가 이 의미를 고정하지 못한다"는 별개 지적이라 위 patch 2건으로 처리했다.
  - `[medium]` `reject` DW-563 resolution의 "클라이언트 협조 여부와 무관하게"가 DW-591(`context: []` 위장)과 모순된다 — **실측으로 반증**: 그 resolution 본문 같은 문단에 "잔여 한계: 클라이언트가 매번 `context: []`로 위장하면 이 계산도 무력화된다"가 이미 적혀 있다. 숨긴 것이 아니라 함께 기록돼 있다.
  - `[medium]` `reject` SM3 데모 게이트가 벡터 경로 장애를 못 잡고 PRD·epics 문구가 안 맞는다 — 2차에서 DW-590으로 이미 등재된 같은 지적.
  - `[low]` `reject` DW-586·DW-591의 재검토 트리거가 발화 불가능한 신호에 걸려 있다 — **실측으로 반증**: DW-586의 trigger는 "남용 신고 **또는 에픽 13 회고에서 우선순위로 올릴 때**"이고, DW-591은 그 DW-586 구현 시점을 가리킨다. 회고는 실제로 예정된 사건이라 두 항목 모두 도달 가능하다.
  - `[low]` `reject` DW-563의 trigger 중 "계획문서에 결정을 박는다" 절반이 미이행인데 done으로 닫혔다 — 미이행분은 DW-589가 이미 열린 항목으로 추적 중이고, 기존 장부 항목의 상태·해결은 오케스트레이터 소유라 이 세션이 수정하지 않는다.
  - `[low]` `reject` 라이브 스모크의 `route == "CLARIFY"` 단언이 LLM 분류 변동에 취약하다 — 2차 리뷰가 **바로 그 단언이 없으면 테스트가 상한 분기를 지워도 통과한다**는 이유로 추가한 것이다. skip으로 바꾸면 2차가 고친 공허함이 되돌아온다. 이 테스트는 CI에 없고 수동 실행 전용이며, 이번 실행에서도 통과했다.
  - `[low]` `reject` `clarify_node`가 `query`를 무시해 상한 이내에서 같은 질문·같은 칩이 최대 3번 반복된다 — 2차에서 같은 근거(CR5 "추가 LLM 호출 없음"이 고정 템플릿을 요구)로 reject.
  - `[low]` `reject` `test_clarify_node.py`가 칩 **내용**을 고정하지 않는다 — 2차가 "제품 판단으로 바뀔 수 있는 값이라 얼리지 않는다"고 검사 옆에 명시적으로 적어둔 결정이다. 축 자체의 정합성 문제는 DW-594로 별도 등재했다.
  - `[low]` `reject` `answer_node`에서 answer가 공백이고 `clarify`가 있으면 FR17 "조건을 넓히세요"와 좁히는 칩이 함께 나간다 — 현재 도달 불가하다(`clarify_node`의 answer는 모듈 상수라 절대 공백이 아니다). 불가능한 상태용 방어를 넣지 않는다(CLAUDE.md A2).
  - `[low]` `reject` I/O 매트릭스는 wire(`POST /ai/search`) 기준인데 상한 테스트는 `run_search()` 함수 표면에서만 돈다 — 그 사이 구간은 `len()` 한 번이고 pydantic 모델 리스트든 dict 리스트든 결과가 같다. 계약 경계 자체는 1차가 추가한 HTTP 직렬화 테스트 2건이 이미 지킨다.
  - `[low]` `reject` DW-587의 reason이 "웹은 타입만 추가(파싱·렌더 없음)"라고 적었는데 2차에서 매핑이 추가돼 문구가 늙었다 — 기존 장부 항목 수정은 오케스트레이터 소유라 이 세션이 손대지 않는다.

## Design Notes

**DW-563 해결 근거 (턴 상한을 서버가 직접 계산한다).** 원래 서술("클라이언트가 횟수를 추적해 강제")은 두 가지를 뒤섞고 있었다: (a) `/ai/search`의 실제 과금 방어선은 JWT 인증이고, 이는 라우트와 무관하게 이미 모든 요청에 적용된다 — CLARIFY를 반복한다고 해서 다른 라우트를 반복하는 것보다 더 많은 비용이 생기지 않는다(질의 1회=인증된 사용자의 정상 1회 호출, 라우트 종류와 무관). (b) 되묻기 상한의 실제 목적은 비용 방어가 아니라 "질문만 계속하고 결과를 못 보여주는 막다른 루프"를 막는 UX 보장이다. 문제는 (b)마저 순전히 클라이언트 판단(칩 숨김)에만 맡겨져 있어, 서버가 그 시점에 아무 결정도 못 내렸다는 점 — CLAUDE.md B9가 말하는 "중요한 값은 서버가 직접 구한다"를 어겼다. 해결: 서버가 이미 매 요청마다 받는 `context`(FR18, 새 필드 아님)의 길이로 "이미 몇 턴 되물었는가"를 직접 계산해, 상한 초과 시 클라이언트가 칩을 계속 보내든 말든 서버가 스스로 되묻기를 멈추고 실제 결과를 강제한다. 잔여 한계(문서화, 새로 만들지 않음): 클라이언트가 매번 `context: []`로 위장하면 이 계산도 무력화된다 — 하지만 이는 무상태 아키텍처의 근본 한계이지 CLARIFY 특유의 결함이 아니며, 진짜 세션 저장소 도입은 이 스토리 범위를 넘는다(Never 절). 이 잔여 gap과 "애초에 `/ai/search`에 요청 빈도 제한이 전혀 없다"는 더 넓은 사실은 DW-586으로 별도 등재한다(CLARIFY만의 문제가 아니므로 이 스토리가 고치지 않는다).

**턴 카운트는 "지금까지의 대화 길이"이지 "연속 CLARIFY 횟수"가 아니다.** `context` 항목에 라우트 태그가 없어 정확히 "몇 번 연속으로 되물었는가"는 셀 수 없다 — 대신 대화 전체 길이(`len(context)//2`)를 대리 신호로 쓴다. 이미 3턴짜리 대화가 있었던 사용자가 4번째에 다시 애매한 질문을 하면, 그 앞의 3턴이 CLARIFY였든 아니든 결과를 강제 제시한다. 새 세션 인프라 없이 구현 가능한 가장 단순한 근사치이고(A2), 부작용은 "이미 충분히 대화한 사용자에게 한 번 더 물을 기회를 안 준다"는 보수적 방향이라 안전하다.

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/ -x -q` -- expected: 전량 통과(신규 테스트 포함).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -x -q` -- expected: pathB가 clarify 페이로드를 실제로 반환하고, 상한 강제 케이스가 listings를 실제로 반환함을 확인.

**Manual checks (if no CLI):**
- 로컬 Supabase+`GEMINI_API_KEY`로 "패밀리카로 무난한 거"를 `context` 없이/6턴짜리 `context`와 함께 각각 `run_search()`로 직접 호출해 전자는 `clarify` 있음+listings=[], 후자는 `clarify` None+listings 채워짐을 눈으로 확인(red→green 대신 상태 대조로 검증).
- `run_phase_b.py --subset`으로 명시조건 대표 질의(예: 기존 A 라벨 몇 개) 2~3개를 재실행해 CLARIFY로 새지 않음(G1)을 확인 — 라우터 자체는 이번 스토리가 손대지 않으므로 회귀 없음을 재확인하는 용도.

## Auto Run Result

**Status:** done

**Summary:** CLARIFY 라우트를 임시 배선(doc_rag_node)에서 실제 되묻기 노드(`clarify_node`, 고정 질문+칩, LLM/DB 없음)로 교체했다. `SearchResponse`에 `clarify: {question, chips[]} | None` 필드를 추가했다(CR5). 되묻기 상한(3턴)을 서버가 `context` 길이로 직접 계산해, 상한 초과 시 클라이언트 협조 여부와 무관하게 `doc_rag_node`로 실제 매물을 강제 제시하도록 했다 — 13.1 착수 시점부터 대기 중이던 DW-563(클라이언트 강제 상한이 CLAUDE.md B9 위반 소지라는 지적)을 이 스토리 스펙 작성 시점에 실제로 결정·구현해 해결했다.

**Files changed:**
- `api/app/graph/clarify_node.py`(신규) -- 고정 되묻기 질문+칩 3개 반환(LLM/DB 없음, CR5).
- `api/app/graph/graph.py` -- CLARIFY 분기를 `clarify_node`로 재배선, `_clarify_step` 신설(상한 이내=clarify_node, 초과=doc_rag_node 강제 폴백+고정 안내 문구), `SearchState`에 `clarify`/`clarify_turns` 추가, `run_search`가 `len(context)//2`로 상한 계산해 반환값에 `clarify` 포함.
- `api/app/graph/answer_node.py` -- `clarify` 키 통과(값 없으면 None).
- `api/app/schemas/ai.py` -- `ClarifyPayload` 신규, `SearchResponse.clarify` 필드 추가.
- `api/app/routers/ai.py` -- `/ai/search` 응답 조립에 `clarify` 포함.
- `api/tests/test_clarify_node.py`(신규), `test_graph.py`, `test_live_smoke.py`, `test_demo_acceptance.py`, `test_ai_search.py` -- 신규·보강 테스트(고정 페이로드 형식, 상한 이내/초과/0건-모순방지 분기, HTTP 직렬화 경계, 데모 인수 SM3 판정 기준 갱신).
- `api/docs/ai-demo-queries.md` -- SM3 표 서술을 CLARIFY=되묻기로 정정.
- `docs/conventions.md` -- §4에 `clarify` 필드 계약 문서화(교차 경계 정본 갱신, 코드리뷰 패치).
- `web/src/lib/api/aiSearch.ts` -- `SearchResult`에 `clarify` 타입만 추가(파싱·렌더 없음, 코드리뷰 패치).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-563 closed(서버 강제로 해결), DW-586 신규 open(요청 빈도 제한 부재, 더 넓은 잔여 gap), DW-587 신규 open(웹 칩 렌더링 스토리 부재, 코드리뷰 패치로 등재).

**Review findings breakdown:** 1개 패스, patch 3건(전부 medium) 전부 적용·재검증 완료. defer 1건(score_ab.py doc_hit 지표 드리프트, DW 미배정 — 신규 등재만) 등재. reject 10건(스펙이 이미 결정했거나 프로젝트 관례로 허용된 트레이드오프, 실측으로 반증된 항목 포함 — Review Triage Log 참조).

**Follow-up review recommendation:** true (patch 3건 전부 medium, `3×medium(3) + 1×low(0) = 9 ≥ 5`).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **347 passed, 84 skipped**(패치 전 345 → HTTP 경계 테스트 2건 추가).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -q` → **5 passed**(실제 Gemini+로컬 Supabase, 오케스트레이터가 직접 재실행해 독립 확인).
- Matrix Test Audit: I/O 매트릭스 4행 전부 실행·통과하는 테스트로 커버됨을 확인(상한 이내/초과/경계값/칩 탭 후 재질의 배선).
- red→green 실측(패치 3): `routers/ai.py`의 `clarify=result.get("clarify")`를 되돌려 전체 스위트가 여전히 초록임을 확인해 gap이 실재함을 증명 → 그 과정에서 그 라인이 실제로 디스크에서 유실돼 있던 상태를 발견·복원 → 신규 HTTP 경계 테스트 2건으로 다시 확인.
- `run_phase_b.py --subset A1,A2,A3`(구조형 대표 질의) 재실행 → 전부 여전히 `route=SQL`(CLARIFY로 안 샘, G1 회귀 없음).

**Residual risks:**
- 되묻기 상한 계산(`len(context)//2`)은 "연속 CLARIFY 횟수"가 아니라 "대화 전체 길이"의 근사치다 — 스펙이 이미 인지·수용한 트레이드오프(위 Design Notes).
- 클라이언트가 매 요청 `context: []`로 위장하면 상한 계산이 무력화된다 — 무상태 아키텍처의 근본 한계이며 진짜 세션 저장소 도입은 이 스토리 범위 밖(DW-563 resolution·DW-586에 기록).
- `clarify` 필드가 api 응답에는 실려 있지만 웹은 아직 소비하지 않는다(파싱조차 안 함) — 앱(16.5)만 렌더링 스토리가 있고 웹 스토리는 없다(DW-587, 다음 스프린트 플래닝에서 신설 필요).
- `score_ab.py`의 `doc_hit` 지표가 CLARIFY 항목에 대해 조용히 항상 false가 된다(라우팅 변경의 부작용) — 어떤 게이트도 좌우하지 않지만 다음 모델 비교 시 오독 소지(DW 신규 등재, 이번 세션에서 미처리).

---

### 후속 리뷰 패스 (2026-07-31, 2차)

**Summary:** 코드 거동은 바꾸지 않았다. 1차 리뷰가 남긴 **거짓 신호 두 개**(타입만 있고 값이 안 실리는 웹 `clarify` 필드, 응답에 없는 `route`로 판별하라고 적힌 정본 문구)와 **작동하지 않는 검사 두 개**(라이브 상한 테스트가 어느 라우트에서나 통과, 되묻기 문구가 아무 검사에도 안 걸림)를 고쳤다. 새 결함이 아니라 "있는데 안 잡는 것"들이라 전부 patch로 처리했다.

**Files changed (이 패스):**
- `web/src/lib/api/aiSearch.ts` -- `searchAi()`가 응답의 `clarify`를 실제로 실어 돌려주도록 매핑 추가(없으면 `null` 정규화).
- `web/src/lib/api/aiSearch.test.ts` -- `searchAi` 응답 매핑 테스트 2건 신설(fetch 모킹, clarify 있음/없음).
- `docs/conventions.md` -- §4에 "클라이언트는 `clarify !== null`로 판별한다 / 응답에 `route` 필드는 없다" 명시.
- `api/tests/test_live_smoke.py` -- 상한 강제 라이브 테스트에 `route == "CLARIFY"` + 매물 있을 때 안내 문구 단언 추가.
- `api/tests/test_clarify_node.py` -- 되묻기 문구 단언 신설(guard_node 선례), 칩 길이 하한 검사 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-589·DW-590·DW-591 **신규 등재만**(기존 항목 무수정).

**Review findings breakdown:** patch 4건(medium 2, low 2) 적용·재검증. defer 3건(DW-589/590/591) 등재. reject 8건(1차에서 이미 판단됐거나, 스펙이 기록으로 수용한 트레이드오프, 실측으로 반증된 항목 포함).

**Follow-up review recommendation:** true (`3×medium(2) + 1×low(2) = 8 ≥ 5`).

**Verification performed (이 패스):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **348 passed, 84 skipped**(문구 테스트 1건 추가로 347 → 348).
- `cd web && npm run lint` → 무경고. `npm run test` → **293 passed**(매핑 테스트 2건 추가로 291 → 293).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=…:55322 pytest tests/test_live_smoke.py -q` → **5 passed**(강화한 `route == "CLARIFY"` 단언이 실물에서도 통과).
- red→green 실측 2건: (1) 웹 매핑 줄 제거 → 신규 테스트 2건 실패 확인 → 복원 후 9 passed. (2) `_CLARIFY_CHIPS`를 문자열로, `_CLARIFY_QUESTION`을 다른 문구로 변조 → 각각 해당 검사가 실패 확인 → 복원 후 4 passed.
- 라이브 직접 관찰(존재 확인이 아니라 작동 확인): 상한 초과(context 12항목) → `route=CLARIFY`·`clarify=None`·**매물 5건**·안내 문구 포함·답변에 가이드 문서 인용("(참고: 패밀리카로 무난한 차종 고르기)") — 강제 폴백이 실제로 벡터 경로를 타고 결과를 낸다. 상한 이내(context 없음) → `listings=0`·칩 3개(`3천만원 이하`/`SUV`/`전기차`) 관측.

**Residual risks (이 패스 추가분):**
- 웹은 이제 `clarify` 값을 **받아서 들고만 있다** — 렌더링은 여전히 없다(DW-587). 타입이 거짓말하지 않게 된 것뿐이다.
- 아키텍처 I12가 아직 "클라 강제"라, 다음 클라이언트 스토리가 두 번째 상한을 만들 여지가 남아 있다(DW-589).
- SM3 데모 게이트는 벡터 경로 장애를 여전히 못 잡는다(DW-590) — 라이브 스모크에만 그 증거가 있고, 라이브 스모크는 CI에서 돌지 않는다.

---

### 후속 리뷰 패스 (2026-07-31, 3차)

**Summary:** 이번에도 코드 **거동**은 바꾸지 않았다. 고친 것은 두 부류다. (1) **상한이 무엇을 세는지에 대한 거짓말** — 교차 경계 정본(`conventions.md` §4)의 오프바이원과 단위 미명시, 그리고 `graph.py` 주석 3곳이 "되물은 횟수"라고 서술한 것. 실제로 세는 값은 대화 전체 턴 수이고, 이 차이를 모르는 클라이언트는 "몇 번 더 물어볼 수 있나"를 서버와 다르게 계산한다. (2) **있는데 안 잡는 자리** — 서버 상한이 발동할 수 있느냐를 좌우하는 웹의 `buildContext`가 무검사였고(앱은 같은 상수를 이미 고정하고 있었다), `clarify` wire 값이 형태 검사 없이 통과했으며, "총 턴 수를 센다"는 결정이 문서에만 있고 검사에는 없었다. 새 결함이 아니라 전부 "말과 실제가 어긋난 자리"라 patch로 처리했다.

**Files changed (이 패스):**
- `api/app/graph/graph.py` -- 상한이 세는 대상이 "되묻기 횟수"가 아니라 "대화 전체 턴 수"임을 모듈 docstring·상수 주석·`SearchState` 필드·`run_search` 주석에 사실대로 기재(코드 로직 변경 없음).
- `docs/conventions.md` -- §4 `clarify` 채움 조건의 오프바이원 정정("3턴을 넘지 않았을 때" → "대화가 3턴 미만일 때") + 세는 단위(`len(context)//2`, 일반 검색 턴도 포함) 명시.
- `api/tests/test_graph.py` -- `test_clarify_cap_counts_all_turns_not_only_clarify_turns` 신설(앞선 3턴이 전부 SQL 검색이어도 강제 폴백 — 기록된 트레이드오프를 검사로 고정).
- `web/src/components/ai/ChatAssistant.test.ts`(신규) -- `buildContext` 단위테스트 4건(12턴 절단·빈 턴 제외·2000자 절단). 이 상수가 서버 상한의 도달 가능성을 결정한다.
- `web/src/lib/api/aiSearch.ts` -- `isValidClarify` 추가(계약 위반 wire 값을 null로 떨굼, `listings`의 `isValidListing`과 같은 규칙) + 타입에서 `?` 제거(상태를 2가지로).
- `web/src/lib/api/aiSearch.test.ts` -- 계약 위반 clarify 4형태가 null로 떨어지는지 확인하는 케이스 추가.
- `api/app/routers/ai.py` · `web/src/lib/api/aiSearch.ts`(상단 주석) -- 응답 계약 복창 주석이 `clarify`를 빠뜨린 것 정정, 정본(`conventions.md` §4)을 가리키게 함.
- `api/tests/test_demo_acceptance.py` -- 존재하지 않는 메커니즘을 설명하던 헬퍼 주석 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-592·593·594·595 **신규 등재만**(기존 항목 무수정).

**Review findings breakdown:** patch 7건(medium 2, low 5) 적용·재검증. defer 4건(DW-592/593/594/595) 등재. reject 11건 — 그중 2건은 **실측으로 반증**했다(DW-563 resolution이 잔여 우회를 숨겼다는 지적 → 같은 문단에 이미 적혀 있음 / DW-586·591의 트리거가 발화 불가라는 지적 → 둘 다 "에픽 13 회고" 경로로 도달 가능).

**Follow-up review recommendation:** true (`3×medium(2) + 1×low(5) = 11 ≥ 5`).

**Verification performed (이 패스):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **349 passed, 84 skipped**(상한 의미 테스트 1건 추가로 348 → 349).
- `cd web && npm run lint` → 무경고. `npm run test` → **301 passed / 32 files**(clarify 형태 4건 + buildContext 4건 추가로 293 → 301).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=…:55322 pytest tests/test_live_smoke.py -q` → **5 passed**(실제 Gemini + 로컬 Supabase).
- red→green 실측 3건(만든 게 아니라 **잡는지** 확인):
  1. `isValidClarify` 검사 제거 → 신규 clarify 형태 테스트 4건 실패 → 복원 후 301 통과.
  2. `MAX_CONTEXT_TURNS`를 12 → 4로 축소 → `buildContext` 절단 테스트 실패 → 복원 후 통과. (이 실패가 뜻하는 것: 그 상수 아래에서는 서버 상한이 웹에서 영원히 발동하지 않는다.)
  3. 상한 계산을 "되묻기 문구가 든 턴만 세기"라는 대안 해석으로 변조 → 상한 테스트 3건(신규 1건 포함) 실패 → 복원 후 349 통과.
- 이 검사들이 **안 보는 것**(추측이 아니라 확인한 것): (a) 웹이 실제로 그 context를 서버에 보내 상한이 발동하는 왕복 전체는 아직 어느 자동 검사도 보지 않는다 — 웹 e2e가 `/ai/search`를 모킹하기 때문이다(양쪽 절반만 각각 고정돼 있다). (b) 칩 문구·축의 적절성은 의도적으로 고정하지 않는다(제품 판단 — DW-594).

**Residual risks (이 패스 추가분):**
- 앱(Flutter)은 `clarify`를 파싱조차 하지 않아, api를 운영에 반영하면 애매한 질의가 앱에서 "질문 한 줄"로 퇴행한다(DW-592) — **api 운영 반영 전에 판단이 필요한 유일한 항목**이다.
- `/ai/search` 응답 객체 생성이 여전히 try/except 밖이다(DW-593) — 지금은 도달 불가에 가깝지만 13.5가 응답 필드를 늘리는 순간 열린다.
- 되묻기 칩 축이 UX 정본 워크스루와 하나 어긋난다(DW-594) — 데모 각본 확정 시 통일 필요.
