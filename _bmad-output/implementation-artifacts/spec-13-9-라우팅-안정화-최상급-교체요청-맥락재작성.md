---
title: '13.9 라우팅 안정화 (최상급·교체요청·맥락 재작성)'
type: 'feature'
created: '2026-08-03'
status: 'done'
baseline_revision: '1cf5d7ac6c3b0943c77f707a0d8cfdabe07ef746'
final_revision: '7641c5489ede623addab1bf01a1eac33ed7982ca'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/planning-artifacts/epics-increment-2026-07-12.md', '{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 2026-08-02 재설계 기준선(47문항/57턴) 실측에서 라우터가 최상급 표현("제일 싼"·"가장 비싼")과 차종 교체요청("쏘렌토 같은 SUV로 바꿔줘")을 구조조건으로 인식하지 못해 CLARIFY로 잘못 분류하고(DW-611·612), `contextualize_query`는 최상급만 담긴 REFINE 턴을 주제전환으로 오판해 앞 조건을 접지 않고 원 질의를 그대로 흘린다. 그 결과 라우팅 정답률이 54/57에 머물고, M6의 RESET 오염 게이트(교체요청이 옛 차종 조건을 실수로 이어받는지 검사)가 CLARIFY 오분류 때문에 SQL/HYBRID 경로에서만 도는 로직에 닿지 못해 사실상 발화하지 않는다. 또한 13.7·13.8 후속 리뷰가 이 스토리로 넘긴 6건(DW-619·620·625·626·627·630·632·641)은 "게이트가 선언만 하고 실제로는 못 잡는" 구조적 공백이다.

**Approach:** 새 기능이 아니라 기존 4분기 라우팅(13.2)·하이브리드(13.3)·맥락화(4.6) 코드에 최소 침습으로 정정을 넣는다 — 라우터 프롬프트에 최상급/교체요청 예시를 추가하고, `contextualize_node`의 결정적 주제전환 가드에 최상급 표현을 리파인 신호로 추가하며, G2 게이트를 `result_mean` 단일축에서 4축 전부 비교로 넓히고, RESET 오염 검사에 teardown을 붙이고, 문서·로스터 드리프트 6건을 정정한다.

## Boundaries & Constraints

**Always:**
- 4분기 계약(13.2, `RouterDecision`·`_fallback_route`·`_route_decision` 3곳 락스텝)과 `SearchState` 계약을 깨지 않는다 — 프롬프트·휴리스틱 텍스트만 넓히고 구조는 바꾸지 않는다.
- `sql_guard.py`는 건드리지 않는다(DW-555가 이미 닫은 2차 정렬키 차단은 보안 결정 — 아래 Design Notes 참조).
- 이 스토리가 새로 넣거나 고치는 모든 검사는 양방향(주입 시 red, 원복 시 green)으로 깨서 확인한다(13.8이 반복 학습한 교훈).
- G2 재기준선은 **판정 → 통과 후에만 갱신** 순서를 지킨다(아래 두-단계 절차).

**Block If:**
- G2 1단계(재캡처 vs `g2-baseline.json`)에서 `regression_block:true`(또는 확장된 4축 중 하나라도 하락)면 기준선을 갱신하지 않고 즉시 결과에 기록한다. "하락했지만 의도된 변경"이라는 판단은 사용자 확인 없이 내리지 않는다 — HALT, status `blocked`, blocking condition `G2 regression unresolved`.
- 재작업으로도 4축 비하락을 못 만들면 에픽 13 종료를 보류한다(HALT, blocking condition `G2 gate still failing after rework`).

**Never:**
- `score_ab.py`의 `lexicographic_winner()`/모델 채택 판단에 손대지 않는다(13.8이 이미 범위 밖으로 닫음).
- 이 스토리가 다루지 않는 인접 케이스(주관적 최상급·차종 미명시 교체·RESET 오탐 방향·`contextualize_query` 성공했지만 잘못 접는 경우·직전 턴이 CLARIFY/REJECT일 때·같은 축 재명시 누적vs대체)는 구현하지 않는다 — deferred-work.md에 후보로만 남긴다.
- 최상급+의미조건이 함께 있는 HYBRID 질의(예: "제일 싼 패밀리카")에 대해 `sql_guard`를 넓히거나 2차 정렬키를 SQL로 만들지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 최상급 단독 | "제일 싼 차 뭐야?" (S6) | route=SQL, `ORDER BY price ASC LIMIT 1` | — |
| 최상급 REFINE | 이전 대화(SUV·3천만원·서울) + "제일 싼 거 하나만 알려줘"(M1.t2) | `contextualize_query`가 조건을 접어 SQL로 라우팅, `count_range:[1,1]` | 재작성 실패 시 원 질의 폴백(기존 방어선 유지) |
| 교체요청(조건만) | "아니 쏘렌토 같은 SUV로 바꿔줘"(M6.t2) | route=SQL, body_type=SUV만, 준중형차 미포함(오염 0) | 오염 발견 시 RESET 게이트 red |
| 교체요청+느낌 | "가족이 타기 좋은 SUV로 바꿔줘" | route=HYBRID(13.2 4분기 계약 우선) | — |
| 최상급+HYBRID | "제일 싼 패밀리카" | route=HYBRID, 벡터 정렬 유지 + 가격 정렬 미적용 캐비엇 문구 추가(옵션 b, 아래 Design Notes) | sql_guard 미변경 |
| G2 1단계 실회귀 | 재캡처 4축 중 하나라도 baseline 대비 하락 | `regression_block:true`, 기준선 갱신 안 함 | Block-If → HALT |

</intent-contract>

## Code Map

- `api/app/graph/router_node.py` -- `_SYSTEM_PROMPT`에 최상급/정렬 표현을 구조조건으로, 교체요청을 조건유무 기준(SQL vs HYBRID)으로 분류하는 규칙·예시 추가. `_fallback_route`는 변경 없음(SQL/HYBRID는 휴리스틱 폴백 대상이 아니라는 기존 설계 유지).
- `api/app/graph/contextualize_node.py` -- `_REFINE_MARKERS`(L144-147)에 최상급 어휘("제일"·"가장") 추가 — `_is_topic_shift`가 M1.t2류를 주제전환으로 오판하는 것을 막는다.
- `api/app/graph/hybrid_rag_node.py` -- 최상급 감지 시 답변에 정렬 미적용 캐비엇 한 줄 추가(옵션 b, sql_guard 미변경).
- `api/scripts/score_ab.py` -- `regression_block`(L777, `result_mean` 단일축)을 4축(`result_mean`·`routing_correct`·`doc_hit_n`·`clarify_ok_n`) 비교로 확장(DW-626). `--raw` 순서 모호성 정정 — baseline/candidate를 모델명이 아니라 실제 파일 경로로도 리포트에 남긴다(DW-637). `--out` 기본 경로(`docs/ab-eval-report.json`)·docstring 예시가 커밋된 리포트 파일을 가리키지 않게 정정, run_phase_b의 `_PROTECTED_BASELINES` 패턴을 이식(DW-635).
- `api/scripts/run_phase_b.py` -- `_PROTECTED_BASELINES`에 이 스토리가 재기준선 절차에서 만드는 증거 파일 경로도 포함하거나, 재기준선 커맨드 자체를 보호 경로 밖(날짜 경로)으로만 쓰도록 Verification에 못박는다(DW-636).
- `api/tests/test_router_node.py` -- 최상급/교체요청 프롬프트 규칙을 고정하는 결정론 테스트 추가(기존 `test_system_prompt_defines_hybrid_and_its_precedence` 패턴 재사용).
- `api/tests/test_contextualize_node.py` -- 최상급 REFINE 마커가 topic-shift를 막는지 고정하는 `test_is_topic_shift_pure_function` 계열 테스트 추가.
- `api/tests/test_hybrid_rag_node.py` -- 최상급 캐비엇 문구 추가/부재 테스트.
- `api/tests/test_ab_scoring.py` -- 4축 회귀 게이트·`--raw` 순서 안전장치의 red/green 양방향 테스트.
- `api/docs/ai-demo-queries.md` -- ①②④ 표와 서두 프로즈 불일치 정정(DW-632), "가이드 문서 12개" → 10개 정정(DW-620), 멀티턴 ⑤절 최상급 행이 실제 라우팅과 일치하도록 갱신. (✎ Code Map 정정, 2026-08-03 리뷰: `test_demo_acceptance.py`·`demo_queries.py`는 실제로는 변경이 필요하지 않았다 — DW-632 조치는 이 문서 하나로 끝났다, 아래 Verification 결과 참조.)
- `docs/conventions.md` §6 -- `hybrid_rag_node`를 매물 축 강제 지점 목록에 등록(DW-619).
- `api/tests/integration/test_doc_rag_node_real_db.py` (신규) -- `doc_rag_node`의 FR11 `status='on_sale'` 필터를 실DB로 확인(`test_fr11_cover_images_real_db.py` 패턴 재사용, DW-627).
- `api/tests/test_live_smoke.py` -- `langsmith_tracing`의 인라인 라이브 단언을 순수 함수로 추출(DW-641). 라이브 스모크 전량 스킵 시 게이트가 실패로 보고되도록 Verification 커맨드에 스킵-카운트 확인을 못박는다(DW-630).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-611·612·619·620·625·626·627·630·632·635·636·637·640·641 종결/갱신.
- `api/docs/g2-baseline.json`, `api/docs/g2-baseline-report.json` -- 두-단계 절차로 재캡처·교체(1단계 통과 후에만).

## Tasks & Acceptance

**Execution:**
- `api/app/graph/router_node.py` -- `_SYSTEM_PROMPT`에 최상급 규칙("제일/가장 + 싸다·비싸다·저렴하다 등 정렬 표현은 구조조건이다")과 예시("제일 싼 차 뭐야?"→SQL) 추가, 교체요청 규칙("~같은 ~로 바꿔줘"는 명시 차종 조건만 있으면 SQL, 느낌 표현이 섞이면 HYBRID) + 대조 예시 두 쌍 추가 -- DW-611·612·617(사분면 귀속) 정정
- `api/app/graph/contextualize_node.py` -- `_REFINE_MARKERS`에 `"제일"`, `"가장"` 추가 -- M1.t2류 REFINE 턴이 주제전환으로 오판돼 조건이 접히지 않는 버그(DW-611 3항) 제거
- `api/app/graph/hybrid_rag_node.py` -- 최상급 어휘 감지 시 `_ANSWER_FOUND` 뒤에 "가격 정렬은 반영되지 않았어요, 정확한 가격순은 조건을 더 구체적으로 말씀해주세요" 류 고정 캐비엇 추가 -- 최상급×HYBRID 정렬 충돌(DW-614 #4)을 옵션(b)로 결정·기록(아래 Design Notes)
- `api/scripts/score_ab.py` -- `regression_block`을 4축 비교로 확장하고 각 축 개별 하락 여부를 리포트에 남김, `gate_pass`는 4축 전부 비하락을 요구 -- DW-626(단일축만 보던 게이트가 13.4·13.6 전멸도 통과시킨 실증된 공백)
- `api/scripts/score_ab.py` -- 리포트에 baseline/candidate의 실제 파일 경로를 추가 기록(모델명만으론 자기비교 시 구분 불가) -- DW-637(순서 뒤집으면 회귀가 뒤집힌다)
- `api/scripts/score_ab.py`, `api/scripts/run_phase_b.py` -- `_PROTECTED_BASELINES` 패턴을 score_ab 쪽에도 적용하고 두 스크립트의 docstring 예시가 커밋된 파일을 `--out`으로 가리키지 않게 정정 -- DW-635·636
- `docs/conventions.md` §6 -- 매물 축 강제 지점 목록에 `hybrid_rag_node`(자체 조립 SQL이 `sql_guard`를 거침) 추가 -- DW-619
- `api/tests/integration/test_doc_rag_node_real_db.py` (신규) -- `test_fr11_cover_images_real_db.py`와 동일 패턴으로 실 Supabase에 sold 매물을 심고 `doc_rag_node` 결과에 없음을 확인, `status='on_sale'` 조건 제거 시 red -- DW-627(문자열 검사만 있고 실DB 검증이 없던 공백)
- `api/tests/test_live_smoke.py` -- `langsmith_tracing`의 라이브 스팬 단언 로직을 순수 함수(예: `_assert_span_present(spans) -> bool`)로 추출하고 그 함수만 단위테스트 -- DW-641
- `api/docs/ai-demo-queries.md`, `api/tests/demo_queries.py` -- ①②④ 표의 구어휘 잔존 정정(하단 SM3 매핑 표와 일치시킴), "가이드 문서 12개" → "10개"로 정정, ⑤절 최상급 행 라벨을 4분기 어휘로 통일 -- DW-632·620
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-611·612를 이 스토리 완료로 종결, DW-619·620·625·626·627·630·632·635·636·637·641을 조치 내용과 함께 종결, DW-640은 4건 재지정분(620·625·627·632) 처리 완료로 종결

**Acceptance Criteria:**
- Given 재설계된 질의셋(47문항/57턴), when 전량 재캡처하면, then 최상급·정렬 표현이 구조조건으로 취급돼 S6·M1.t2가 SQL로 라우팅되고, 라우팅 정답이 54/57 → 57/57이 되며, 결과집합 정확도(0.894)·가이드 인용(12/13)·되묻기 발동(9/9)이 하락하지 않는다
- Given `M6`(교체요청 RESET), when 재캡처하면, then `아니 쏘렌토 같은 SUV로 바꿔줘`가 SQL로 라우팅되고 `준중형차` 조건이 2턴째 결과에 남지 않는다(오염 0) — RESET 게이트가 실제로 발화 가능한 상태임을, 일부러 오염 데이터를 주입해 red가 되는지까지 확인해 증명한다(존재 확인 ≠ 작동 확인)
- Given "가족이 타기 좋은 SUV로 바꿔줘"류(느낌+명시조건 혼합 교체요청), when 라우팅하면, then HYBRID로 간다(13.2 4분기 계약이 상위 — "교체요청=SQL"은 무조건이 아니라 "교체요청이라는 이유로 CLARIFY로 새지 않는다"는 뜻)
- Given `contextualize_query`, when REFINE 턴이 최상급 표현만 담고 있으면, then 주제전환으로 오판하지 않고 LLM 재작성을 거쳐 이전 조건을 접은 독립 질의를 만든다 — 재작성 실패 시 원 질의 폴백은 유지된다
- Given G2 스코어러, when 재기준선 절차를 밟으면, then **1단계(판정)**로 이전 `g2-baseline.json`과 변경 후 코드의 재캡처를 비교해 4축(결과집합·라우팅·가이드인용·되묻기) 전부 비하락을 확인하고, **2단계(갱신)**로 1단계 통과 후에만 `g2-baseline.json`/`g2-baseline-report.json`을 교체한다 — 순서가 바뀌면 게이트가 자기 자신과 비교하는 무의미한 상태가 된다
- Given RESET 오염 검사, when 실행하면, then 검사가 일부러 심은 오염 데이터를 teardown한다 — 같은 로컬 DB에서 뒤이어 도는 G2 재캡처가 잔존 행에 오염되지 않는다
- Given 코드가 판정하는 라우팅 규칙(최상급/교체요청 전처리, `_fallback_route`), when 결정론 단위테스트를 돌리면, then 프롬프트 문자열·`_REFINE_MARKERS` 내용을 직접 단언하는 테스트가 통과한다 — "단위테스트가 프롬프트 흔들림을 먼저 잡는다"는 요구는 하지 않는다(fake LLM은 프롬프트에 반응하지 않으므로 정의상 불가능, 프롬프트 흔들림은 라이브 재캡처가 잡는다)
- Given `score_ab.py`의 4축 게이트, when 가이드 인용을 전부 제거하거나 CLARIFY 분기를 전부 SQL로 바꾸는 뮤테이션을 주입하면, then `gate_pass:false`가 된다(DW-626 실증 재현 후 고정) — 원복 시 green
- Given `--raw` 인자 순서, when baseline/candidate 파일을 뒤바꿔 실행하면, then 리포트의 파일 경로 필드로 어느 쪽이 baseline인지 항상 구분 가능하다(DW-637)
- Given `doc_rag_node`의 FR11 실DB 테스트, when `status='on_sale'` 조건을 제거하는 뮤테이션을 주입하면, then red가 되고, 원복하면 green이 된다
- Given 이 스토리가 새로 넣거나 고친 모든 검사, when 양방향으로 깨보면(주입 시 red, 원복 시 green), then 그 결과가 Auto Run Result에 실측 기록된다

## Spec Change Log

## Review Triage Log

### 2026-08-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 1, medium 5, low 4)
- defer: 1: (medium 1)
- reject: 2: (low 2)
- addressed_findings:
  - `[high]` `[patch]` (edge-case-hunter) `contextualize_node._is_topic_shift`의 `_REFINE_MARKERS` 검사(1단계)가 새로 추가된 "제일"·"가장" 때문에 카테고리 값 교체 검사(2단계)보다 먼저 걸려, "가장 저렴한 SUV로 바꿔줘" 같은 최상급+차종교체 질의가 RESET(리셋) 판정 없이 리파인으로 오분류될 수 있었다(DW-612가 고치려던 바로 그 오염 클래스가 새 형태로 재발할 위험) — 2단계(카테고리 교체 검사)를 1단계보다 먼저 검사하도록 순서 변경, red/green 테스트 추가.
  - `[medium]` `[patch]` (edge-case-hunter) `hybrid_rag_node`의 최상급 캐비엇이 조건추출 성공 분기에만 있어, 스펙 자신의 예시("제일 싼 패밀리카")처럼 조건추출이 NONE으로 실패해 `doc_rag_node`로 폴백하는 바로 그 경로에서는 캐비엇이 빠졌다 — 폴백 경로에도 동일 캐비엇 로직 적용.
  - `[medium]` `[patch]` (adversarial/edge-case-hunter 독립 일치) `_has_superlative`가 "제일"·"가장"만 보고 가격 형용사 동반 여부를 안 봐서, 라우터 프롬프트가 정의한 "최상급+가격형용사 결합"보다 넓게 발동해 "가장 안전한 SUV" 같은 가격 무관 질의에도 엉뚱한 가격정렬 캐비엇이 붙었다 — 가격 형용사 동반 조건 추가.
  - `[medium]` `[patch]` (edge-case-hunter, 코드 확인) `score_ab.py`의 4축 게이트 중 개수 기반 세 축(`routing_correct`·`doc_hit_n`·`clarify_ok_n`)이 baseline·candidate의 채점 항목 수(`scored_n`)가 같은지 확인 없이 원시 개수만 비교해, 부분 재캡처가 정확도 동일/개선이어도 거짓 회귀로 잡힐 수 있었다 — `scored_n` 불일치 시 그 세 축을 신뢰 불가로 표시하도록 가드 추가, 불일치 상황을 재현하는 테스트 추가.
  - `[medium]` `[patch]` (adversarial) 이번 diff가 만든 재기준선 증거 파일(`g2-recapture-2026-08-03.json`·`-report.json`)이 정작 같은 diff가 만든 `PROTECTED_BASELINES`엔 없었다(직전 스토리의 선례 — 스토리 근거가 된 날짜형 증거 파일은 보호 목록에 넣는다 — 를 스스로 어김) — 두 파일 추가.
  - `[medium]` `[patch]` (verification-gap, 실측) 신규 `test_doc_rag_node_real_db.py`가 공유 `conftest.py`의 롤백 기반 픽스처(신규 통합 테스트의 정해진 사용법, 자매 파일들이 이미 채택 중)를 안 쓰고 `test_fr11_cover_images_real_db.py`의 옛 하드코딩 이메일+명시적 DELETE 패턴을 그대로 복제해, CI가 이미 알고 있는 취약점(설정 도중 실패 시 잔존 행이 다음 알파벳순 통합테스트를 깨는 것)의 노출면을 1곳에서 2곳으로 늘렸다 — 공유 conftest 픽스처로 리팩터.
  - `[low]` `[patch]` (adversarial) `score_ab.py`의 자기비교 경고(`self_comparison`)가 콘솔에만 찍히고 커밋되는 JSON 리포트 필드엔 안 남아, 터미널 로그 없이 리포트만 보는 사람은 못 본다 — `report`에 `self_comparison` 불리언 필드 추가.
  - `[low]` `[patch]` (adversarial) `test_live_smoke_langsmith_tracing`의 최종 단언이 "llm"·"node"만 보고 "root"(트레이스 자체 없음)는 앞선 `assert mine`이 우연히 대신 잡고 있다 — 오늘은 논리적으로 동치라 실오류는 아니지만, 나중에 `assert mine`을 "중복"으로 오인해 지우면 무방비가 된다 — 대칭성을 위해 `assert "root" not in missing`을 명시적으로 추가.
  - `[low]` `[patch]` (intent-alignment) 스펙 Code Map이 DW-632 조치 파일로 `test_demo_acceptance.py`·`demo_queries.py`를 적었으나 실제로는(장부 기록대로) 안 고쳐도 됐다 — Code Map 항목을 실제 결과에 맞게 정정.
  - `[low]` `[patch]` (intent-alignment) 스펙 Boundaries&Constraints의 "구조는 바꾸지 않는다"가 근거 없이 결정처럼 적혀 있었다(에픽 계획 문서가 "추출-후-분기 재구조화"도 후보로 열어뒀던 것과 대조됨) — Design Notes에 왜 순수 프롬프트 패치를 택했는지(라이브 재캡처로 57/57 달성, 재구조화의 더 큰 블라스트 반경 대비 A2 단순함 우선) 한 줄 근거 추가.
- 리뷰 레이어: adversarial 8건 · edge-case-hunter 4건(일부 adversarial과 독립 일치) · verification-gap 1건(실제 재실행+뮤테이션으로 확인) · intent-alignment 서술 다수(그중 2건이 스펙 정정으로 이어짐).
- defer(신규 등재, deferred-work.md): 1건 — `epics-increment-2026-07-12.md`의 되묻기 상한 서술이 "클라 강제"로 남아 실제 코드(서버 강제, `_CLARIFY_TURN_CAP`)와 반대다. 이 diff가 같은 파일의 다른 줄(가이드 문서 개수)만 고쳐서 생긴 게 아니라 이전부터 있던 오기이므로 defer.
- reject 2건: 라우팅 정정의 실제 검증이 1회성 라이브 재캡처 서술로만 남아 재실행 가능한 회귀 테스트가 없다는 지적(intent-alignment) — 스펙이 이미 "프롬프트 흔들림은 라이브 재캡처가 잡는다"(DW-614 #6)로 명시적으로 수용한 트레이드오프라 새 결함이 아님. `ai-demo-queries.md`의 "12행 전부 실측"이 상시 게이트가 아니라는 지적 — 문서 자신이 이미 그 한계를 스냅샷이라고 명시해 뒀음.

### 2026-08-03 — Review pass (후속 리뷰, 2차)

- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 4, medium 5, low 4)
- defer: 6: (medium 2, low 4)
- reject: 3: (low 3)
- addressed_findings:
  - `[high]` `[patch]` (adversarial·edge-case-hunter·verification-gap 3중 독립 일치, 오케스트레이터 실행 재현) 이 diff가 `g2-recapture-2026-08-03.json`·`g2-recapture-report.json`을 `PROTECTED_BASELINES`에 넣으면서, 정작 `score_ab.py`의 docstring 예시·`ap.error` 안내 문구·스펙 Verification의 G2 1단계 커맨드가 **바로 그 경로를 쓰라고** 지시하고 있었다 — 안내대로 치면 exit 2, 에러 메시지가 다시 같은 경로를 권해 빠져나갈 수 없는 고리였고, 에픽의 유일한 회귀 게이트가 문서대로는 재실행 불가 상태였다(DW-636의 reason이 이 결과를 미리 경고했던 자리). 예시·에러·스펙 커맨드를 전부 미보호 날짜 템플릿 경로로 바꾸고, "문서화된 예시 경로는 보호목록 밖이어야 한다"를 **반대 방향 테스트**(docstring·에러 문자열에서 경로를 뽑아 `is_protected(...) is False` 단언)로 고정.
  - `[high]` `[patch]` (edge-case-hunter·verification-gap 독립 일치, 오케스트레이터 실행 재현) 새로 넣은 최상위 `gate_pass`가 `not regression` 하나였다 — (1) `scored_n` 불일치로 개수 3축이 `unverifiable_axes`로 빠지면 라우팅 0/2·4건 errored인 부분 캡처도 `gate_pass:true`·exit 0이 됐고(DW-626이 닫은 공백의 재개방 입구), (2) 오염·dead-end·errored를 보는 기존 summary별 `gate_pass`를 전혀 참조하지 않아 M6 오염으로 `게이트: FAIL`이 찍히는데도 최상위는 true였다(gray 항목은 `result_mean`에서 제외돼 어느 축도 안 움직인다). `(not regression) and not unverifiable_axes and all(summary gate_pass)`로 교정하고, 기존에 `gate_pass is True`를 못박던 테스트를 False로 뒤집고 오염 케이스 테스트를 신규 추가.
  - `[high]` `[patch]` (4개 레이어 전원 독립 일치, 오케스트레이터 실행 재현) 1차 리뷰 patch #1(`_is_topic_shift`에서 카테고리 값 교체를 마커보다 먼저 판정)이 최상급과 무관한 기존 리파인 턴까지 뒤집었다 — 직전 "3천만원 이하 흰색 SUV" + `그중 검정도 있어?`, "서울 SUV" + `그중 경기 매물도`, "현대 SUV" + `그중 기아 것도` 가 전부 RESET(맥락 폐기)으로 실측 확인됐고, 사용자는 앞 결과집합을 좁히는 중인데 가격·차종·지역이 통째로 사라졌다(DW-611이 고치려던 손실의 반대 방향). `_REPLACEMENT_MARKERS`("바꿔"·"말고"·"대신"·"아니")를 도입해 **교체 의도가 있을 때만** 값 교체가 마커를 이긴다로 바꿔, DW-612의 교체요청 오염 차단은 유지하면서 나머지 마커 케이스의 diff 이전 동작을 복원. 8개 경계 케이스를 결정론 테스트로 고정.
  - `[high]` `[patch]` (adversarial·edge-case-hunter 독립 일치, 오케스트레이터 grep 재현) `epic-13-context.md` 재컴파일이 제약 3건을 대체 없이 삭제했다 — `/ai/search` 로그인(JWT) 필수(과금 울타리), AI 검색 입력 서버측 500자 검증, 되묻기 상한의 **서버** 강제(`_CLARIFY_TURN_CAP`). 셋 다 보안·비용 축이고 특히 세 번째는 13.8 3차 리뷰가 "코드와 정면으로 어긋난다"며 일부러 본문으로 올려둔 정정이었다(CLAUDE.md B8 "문서를 새로 쓰는 순간이 가장 위험하다"의 실사례). 세 항목 복원, 재컴파일의 나머지는 유지.
  - `[medium]` `[patch]` (edge-case-hunter, 오케스트레이터 실행 재현) `_REFINE_MARKERS`에 추가한 "제일"·"가장"이 3단계(비-매물 주제 점프) 가드를 무력화해, `제일 좋은 자동차보험 알려줘`·`제일 인기있는 여행지`가 리셋되지 않고 앞선 매물 조건을 끌고 갔다(diff 이전엔 정상 리셋). 최상급 판정을 라우터 프롬프트와 동일한 기준(최상급 부사 + 가격 형용사 결합)으로 좁혀 해결 — 잔여 구멍(`가장 싼 할부 이자율`류)은 비-매물 주제 어휘 사전이 필요해 DW-648로 이월.
  - `[medium]` `[patch]` (edge-case-hunter·adversarial 독립 일치, 오케스트레이터 실행 재현) 1차 리뷰 patch #3의 "가격 형용사 동반" 좁히기가 근접성 없는 부분문자열 AND라, `가장 인기있는 싼타페`가 **차명 "싼타페"의 "싼"** 때문에 True였다(이 diff의 신규 통합테스트가 심는 모델명이다). `가장 인기 많고 저렴한 SUV`·`제일 안전한 차인데 가격도 싸게`도 오발동. 부사-형용사 인접 정규식으로 교체하고 반례 3건을 음성 테스트로 고정.
  - `[medium]` `[patch]` (adversarial) 4축 게이트가 개수 3축에는 커버리지 가드를 붙였지만 `result_mean`에는 없었다 — 그 축의 분모는 `scored_n`이 아니라 `result_n`(clean SQL+HYBRID 항목 수)이고, 라우팅이 CLARIFY→SQL로 바뀌면 채점 모드가 바뀌어 분모가 움직인다. 즉 **라우팅을 바꾸는 스토리**(이 스토리 같은)에서 분모가 다른 두 평균을 비교하게 된다. `result_n` 비교를 가드에 추가.
  - `[medium]` `[patch]` (adversarial·verification-gap 독립 일치) DW-637로 넣은 `baseline_raw`의 첫 실사용 값이 다른 세션의 휘발성 스크래치패드 경로(`/tmp/claude-1000/.../scratchpad/...`)라, "산출물만 보고 방향을 되짚는다"는 목적이 그 세션 종료와 함께 무너졌다. 경로를 해석해 저장소 상대경로(불가 시 절대 해석경로)로 기록하도록 고치고, 기록된 경로가 실재하는지를 테스트가 단언하게 보강.
  - `[medium]` `[patch]` (adversarial) 2단계 갱신을 "비교 리포트를 그대로 복사"로 수행한 탓에, **기준선 리포트**(`g2-baseline-report.json`)의 첫 요약이 13.9 **이전** 수치(result_mean 0.894 / 라우팅 54)였다 — DW-635가 "사람이 눈으로 대조하는 유일한 기준점"이라 부른 파일을 열면 폐기된 숫자가 먼저 나오는 상태였고, 커밋된 4개 JSON이 사실상 동일한 2쌍이었다(md5 실측). 새 기준선 raw로 **1파일 모드 재생성**해 요약 하나(라우팅 57 / 0.954)만 남도록 교체.
  - `[low]` `[patch]` (edge-case-hunter) 신규 실DB 테스트의 `finally` 정리가 `seller_id is not None`을 전제로 해, `_create_user`가 INSERT(autocommit) 직후 가입 트리거 단언에서 실패하면 이미 커밋된 `auth.users` 행이 고아로 남았다 — 픽스처 docstring의 "시드 도중 실패해도 고아 행이 남지 않게 보장한다"가 그 경로에서 거짓이었다. 이메일 패턴 재조회로 정리하도록 수정(실패 주입 실측: 옛 로직 잔존 1건 → 새 로직 0건).
  - `[low]` `[patch]` (adversarial) 최상급 캐비엇 문구가 실행 불가능한 방향을 안내했다 — "조건을 더 구체적으로"는 조건을 더할수록 HYBRID에 더 머물러 가격정렬을 영영 못 받는다(정렬은 순수 구조질의=SQL 경로에서만 산다). "3천만원 이하 SUV 가격 낮은 순"처럼 **조건만으로** 물어보라는 안내로 교체.
  - `[low]` `[patch]` (adversarial) DW-630이 택한 조치("커맨드에 `-rs`와 기대 개수를 못박는다")가 정작 스펙의 라이브 스모크 커맨드엔 반영돼 있지 않아(자매 커맨드엔 있음) 전량 스킵이 여전히 초록으로 보였다 — Verification 커맨드에 `-rs`와 기대 수집/스킵 개수 명시. 코드로 강제하는 층(conftest 훅)은 DW-649로 이월.
  - `[low]` `[patch]` (intent-alignment) RESET teardown AC가 "DB에 오염 행을 심고 지운다"로 읽히지만 오염 판정은 캡처 JSON 위에서 돌고 실제 red 증명도 캡처 사본에서 했다(=지울 DB 행 자체가 없었다) — AC가 미이행으로 오독되지 않도록 실제 증명 방식과 그 경위를 Design Notes에 기록.
- 리뷰 레이어: adversarial 15건 · edge-case-hunter 10건 · verification-gap 4건(실행 재현·뮤테이션 포함) · intent-alignment 서술(그중 2건이 defer로 이어짐). 4개 레이어 중 3개 이상이 독립적으로 같은 결함을 지목한 것이 3건(보호목록 자기부정, `gate_pass` 과대보고, `_is_topic_shift` 순서 부작용).
- ⚠️ 이 패스의 발견은 모두 **오케스트레이터가 직접 실행해 재현한 뒤** 분류했다(서브에이전트 보고를 그대로 채택하지 않음): `is_protected()` 호출, `_is_topic_shift`·`_has_superlative` 직접 호출, 4개 JSON md5 대조, `epic-13-context.md` grep 0건, `g2-baseline-report.json` 요약 값 확인.
- defer(신규 등재, deferred-work.md — 기존 항목은 오케스트레이터 소관이라 수정하지 않음): DW-645(최상급 규칙이 가격 축에만 닫힘 — 연식·주행거리·연비 누락) · DW-646(게이트가 채점 문항 **집합**은 비교 안 함) · DW-647(큐리셋의 `count_range`를 스코어러가 한 번도 안 읽음) · DW-648(최상급+가격형용사가 비-매물 주제에 붙는 잔여 구멍) · DW-649(DW-625·630의 미이행 잔여분 인수) · DW-650(DW-644가 실재하지 않는 문자열을 인용).
- reject 3건: 스펙 frontmatter의 `review_loop_iteration: 0`이 리뷰 1패스 기록과 어긋난다는 지적 — 그 필드는 리뷰 패스 횟수가 아니라 **bad_spec 루프백 횟수**이고, 워크플로가 `done` 스펙 재리뷰 시 0으로 리셋하도록 규정하므로 오해다. 이 diff의 게이트 작업 절반이 Approach 열거 밖이라는 지적(intent-alignment) — 방향이 일치하고 Code Map이 근거를 제공하므로 결함 아님. 최상급×HYBRID의 route 자체가 미검증이라는 지적 — 큐리셋에 해당 조합이 없다는 사실을 Design Notes가 이미 스스로 밝혀 수용한 트레이드오프.

### 2026-08-03 — Review pass (후속 리뷰, 3차)

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 4, low 6)
- defer: 3: (medium 1, low 2)
- reject: 6: (low 6)
- addressed_findings:
  - `[high]` `[patch]` (adversarial·edge-case-hunter·verification-gap 3중 독립 일치, 오케스트레이터가 pre-diff 코드와 직접 대조 실행) 2패스 patch #3이 도입한 `_REPLACEMENT_MARKERS`가 **모든 카테고리 축**에서 리파인 단축판정을 무력화했다 — `"말고"`가 `_REFINE_MARKERS`와 `_REPLACEMENT_MARKERS` 양쪽에 들어 있고, 값 교체 판정이 `_CATEGORICAL_VOCAB` 5개 축 전부에 적용됐기 때문이다. 직전 턴 `"3천만원 이하 서울 흰색 현대 SUV 보여줘"` 기준 실측: `그중 경기 말고 인천`·`그중 검정으로 바꿔줘`·`아까 그거 대신 경기 매물로`·`위에 거 말고 부산 매물`·`그럼 기아로 바꿔줘` 5건이 전부 pre-diff `False` → `True`(맥락 폐기)로 뒤집혀 있었다 — 색상 하나 바꾸려던 사용자의 가격 상한·차종·지역이 통째로 사라진다. **같은 함수가 세 패스 연속 회귀한 자리다**(1패스 patch #1 → 2패스 patch #3 → 이번). 값 교체가 마커를 이기는 범위를 **`body_type` 축 하나로** 좁혀, DW-612의 차종 교체 오염 차단(`아니 쏘렌토 같은 SUV로 바꿔줘` → RESET)은 유지하면서 나머지 축의 pre-diff 동작을 복원했다. 5건을 결정론 테스트로 고정(뮤테이션 주입 시 5 failed, 원복 시 31 passed 실측).
  - `[medium]` `[patch]` (adversarial·edge-case-hunter 독립 일치, 오케스트레이터 실행 재현) 2패스 patch #6이 "싼타페 오발동을 닫았다"며 넣은 인접 정규식이 실제로는 **부사 바로 뒤(0자 간격)** 형태를 못 막았다 — `\S{0,4}?`가 0자를 허용해 `가장 싼타페 보여줘`·`제일 싼타페 보여줘`가 여전히 True였고, 부정·양보형 `제일 싸지 않은 차`·`가장 비싸도 되는 차`도 True였다. 테스트 이름(`test_has_superlative_false_for_santafe_substring_false_positive`)이 수정 완료를 주장하는데 정작 띄어쓰기 한 변형만 덮고 있었다. 어간형 형용사 뒤에 음절 경계를 요구하도록 교정(`((싼|싸|비싼|비싸)(?![가-힣])|저렴)` — `저렴`은 `저렴한`의 어미 때문에 경계에서 제외, 그러지 않으면 기존 green 단언 2건이 깨진다는 것을 구현이 실측으로 보고했고 오케스트레이터가 재확인). 두 파일 락스텝 유지, 음성 케이스 4건 추가.
  - `[medium]` `[patch]` (edge-case-hunter·verification-gap 독립 일치, 오케스트레이터 grep 재현) `score_ab.py`에 `sys.exit`가 **한 곳도 없어**, 2패스가 만든 4축 게이트와 최상위 `gate_pass`가 JSON 필드·콘솔 문구로만 존재했다 — `regression_block:true`여도 종료코드 0이라 문서화된 `run_phase_b … && score_ab …` 체인이 실회귀를 그대로 통과한다. 쌍둥이 스크립트 `run_phase_b.py`는 이미 실패 시 exit 1이고 자기 독스트링에 그 원칙을 적어 뒀다. `gate_pass:false`면 리포트 기록·콘솔 요약 이후 exit 1 하도록 추가하고, 기존 게이트-실패 테스트 4건을 `pytest.raises(SystemExit)` + `.code == 1` 단언으로 승격.
  - `[medium]` `[patch]` (adversarial·verification-gap 독립 일치, 오케스트레이터가 리포트 원문·파일 존재로 확인) 커밋된 `docs/g2-recapture-report.json`의 `baseline_raw`가 **다른 세션의 스크래치패드 절대경로**(`/tmp/claude-1000/.../f0358e8c-.../g2-baseline-pre13.9.json`, 미추적)였다 — DW-637이 세운 목적("산출물만 봐도 방향을 되짚는다")이 그 목적으로 만든 첫 산출물에서 깨져 있었고, 그 임시 디렉터리가 정리되면 `0.894 → 0.954` 주장의 before 쪽을 저장소만으로 재현할 수 없었다. 원본이 아직 살아 있는 동안(33275 bytes, md5 `523196c3…`) `api/docs/g2-baseline-pre-13-9.json`으로 저장소에 들여오고 리포트를 재생성했다 — 필드 대조 결과 `baseline_raw` 한 줄만 바뀌고 나머지는 동일(`gate_pass:true`·`unverifiable_axes:[]`·라우팅 54→57·result_mean 0.8936→0.9542 보존, 오케스트레이터 재확인). 새 증거 파일도 `PROTECTED_BASELINES`와 거부 테스트에 등재.
  - `[medium]` `[patch]` (verification-gap·edge-case-hunter 독립 일치, 오케스트레이터 실행 재현) 2패스가 DW-641을 위해 모듈 단위 `pytestmark`를 개별 `@_live_only`로 바꾸면서, **SM-F/SM-G 게이트 증거 파일 자신이** `RUN_LIVE_SMOKE` 없이도 `5 passed, 6 skipped`로 초록 통과 줄을 찍게 됐다 — diff 이전엔 전량 스킵밖에 나올 수 없었다. 이 스토리가 닫았다고 기록한 DW-630("전량 스킵이 초록으로 보인다")을 같은 diff가 더 나쁘게 만든 셈이다. 순수 함수 단위테스트 5건을 `tests/test_live_smoke_helpers.py`로 분리해, 라이브 파일은 라이브 실행 없이 pass를 낼 수 없게 하면서 DW-641의 "그 함수만 단위테스트한다" 요건은 무조건 유지되게 했다(실측: 라이브 파일 `6 skipped`·0 passed, 헬퍼 파일 `5 passed`).
  - `[low]` `[patch]` (edge-case-hunter, 오케스트레이터 코드 확인) 커버리지 불일치가 두 종류(`scored_n`·`result_n`) 모두 발생하면 4축이 전부 `unverifiable_axes`로 빠져 `regression_axes`가 빈 dict가 되고, `any({})`가 False라 커밋되는 리포트에 `regression_block:false`가 박힌다 — **아무것도 비교하지 않았는데 "회귀 없음"으로 읽힌다.** 비교 축이 0개인 경우를 `None`으로 구분해 표기하고 기준선 유지로 처리, 해당 조합을 재현하는 테스트 추가.
  - `[low]` `[patch]` (verification-gap, 뮤테이션 실증) `_SUPERLATIVE_PRICE_RE` 두 사본의 "동일 유지" 계약이 주석에만 있어, 한쪽만 넓혀도 전체 스위트가 초록이었다(리뷰어가 실제로 넓혀 448 passed 확인). DW-645가 예정한 축 확장이 정확히 이 둘을 어긋나게 만들 작업이다 — 두 패턴 문자열 동일성을 단언하는 검사 1건 추가(한쪽만 넓히면 이 검사만 red가 됨을 실측).
  - `[low]` `[patch]` (adversarial) `_resolve_evidence_path`가 OS 기본 구분자로 경로를 기록하고 테스트가 슬래시를 하드코딩해, 이 모듈 독스트링이 스스로 문서화한 Windows 환경에서는 `docs\g2-baseline.json`을 남기고 테스트가 깨진다(리눅스 CI는 초록). `.as_posix()`로 교정.
  - `[low]` `[patch]` (edge-case-hunter, 오케스트레이터 코드 확인) 신규 실DB 테스트가 픽스처의 다른 부분과 달리 `readonly._pool = None`을 **monkeypatch 없이 직접 대입**하고 `close_pool()`도 부르지 않아, 픽스처 종료 후 모듈 전역 풀이 테스트 DB에 묶인 채(커넥션도 열린 채) 세션 끝까지 남았다. `monkeypatch.setattr` + teardown `close_pool()`로 교정(자매 파일 `test_fr11_cover_images_real_db.py`는 이 스토리 소관이 아니라 손대지 않음 — A3).
  - `[low]` `[patch]` (adversarial, 오케스트레이터 코드 확인) `baseline_guard.py` 주석이 보호 검사를 "main()·capture() 양쪽에서" 한다고 적었으나 `score_ab.py`는 `main()`에서만 검사하고 쓰기 지점은 무방비다 — 주석이 없는 보호를 있다고 말하는 상태(B9: 주석은 계약이 아니다). 새 층을 넣는 대신 주석이 사실을 말하도록 정정.
  - `[low]` `[patch]` (adversarial, 오케스트레이터 원문 확인) `docs/conventions.md` §6 "매물 축"에서 이 스토리가 추가한 하이브리드 항목만 파일 경로·강제 장치를 갖고, `문서 RAG 결과 필터`는 여전히 이름 없는 구절이었다 — 정작 이 스토리가 그 축의 **첫 실동작 강제 장치**를 만들었고 DW-625는 "§6이 정확한 정본이 됐다"를 전제로 닫혔는데도. `doc_rag_node.py` 경로·`sql_guard` 미경유·`ai_readonly` RLS가 `using(true)`라 그 한 줄이 유일 강제 지점임·강제 장치 파일까지 명시.
- 리뷰 레이어: adversarial 16건 · edge-case-hunter 7건 · verification-gap 6건(뮤테이션·실행 재현 포함) · intent-alignment 서술(그중 2건이 defer로 이어짐). 4개 레이어 중 3개 이상이 독립적으로 같은 결함을 지목한 것이 2건(`_is_topic_shift` 축 과확대, `score_ab` 종료코드 부재).
- ⚠️ 이 패스의 발견도 전부 **오케스트레이터가 직접 실행해 재현한 뒤** 분류했다: pre-diff `contextualize_node.py`를 `git show`로 꺼내 나란히 호출한 진리표 대조, `_has_superlative` 11개 입력 직접 호출, `grep sys.exit` 0건, 커밋된 리포트 JSON 필드 직접 읽기, `env -u RUN_LIVE_SMOKE pytest` 실행, 스크래치패드 원본 md5 대조, `deferred-work.md` 전문 grep 0건.
- defer(신규 등재, deferred-work.md — 기존 항목은 오케스트레이터 소관이라 무수정): DW-651(스펙 Design Notes가 약속한 최상급×HYBRID 재검토 트리거가 실제로는 장부에 없다) · DW-652(`제일 싼 차 뭐야?`가 여전히 5건 반환 — `predicate.limit:1`을 SQL 생성이 안 지킨다, DW-647의 반쪽) · DW-653(이번 P2가 만든 띄어쓰기 없는 `가장 싼거`류 좁힘, 미고정).
- reject 6건: 최상위 `gate_pass`가 baseline 자신의 게이트까지 AND한다는 지적 — 오염된 기준선으로는 후보를 채택하지 않는 것이 방어 가능한 설계이고 현재 실발동 없음. `test_docstring_out_examples_are_not_protected`가 위조 불가라는 지적 — 실제 정규식 매치는 `docs/ab-eval-report.json`·`docs/g2-recapture-<YYYY-MM-DD>-report.json` 2건이라 전자가 실경로로 검사를 지탱한다(오케스트레이터 실행 확인). `epic-13-context.md` 재컴파일이 아직도 제약을 빠뜨렸다는 지적 — 2패스가 복원한 3건(JWT·500자·`_CLARIFY_TURN_CAP`)이 실재함을 grep으로 확인했고, 나머지는 `compile-epic-context.md`가 명시적으로 배제하는 "코드베이스에서 도출 가능한 세부"라 DW-643이 이미 판정한 사안. DW-630·625가 done인데 DW-649가 잔여 의무를 적고 있어 모순이라는 지적, DW-644의 인용 오류를 DW-650 신설로 우회했다는 지적 — 둘 다 **기존 장부 항목의 status·본문은 오케스트레이터 소관**이라는 이번 호출의 명시 지시에 걸리고, 잔여 의무는 이미 DW-649·DW-650이 들고 있다. `PROTECTED_BASELINES`를 손 목록 대신 `git ls-files`로 바꾸라는 지적 — DW-636이 열린 채 그 항목을 명시적으로 스코프 밖으로 남겨 뒀다.

## Design Notes

**최상급×HYBRID 정렬 충돌 — 옵션(b) 채택 근거:** 후보는 (a) SQL로 보내 정렬을 살리기, (b) HYBRID 유지·최상급 버리되 알리기, (c) sql_guard 2차 정렬키 차단 재검토(보안 결정, 범위 밖)였다. 실제 큐리셋(47문항) 어디에도 "최상급+의미조건" 조합 사례가 없어(S6·S7·M1.t2·M2.t3는 전부 순수 최상급, 의미조건 없음) 이 조합을 실측 검증할 방법이 없다 — 검증 없이 (a)의 "SQL로 보내되 의미조건을 어떻게 살릴지"를 설계하면 B4("재보기 전엔 선언하지 않는다")를 어기는 미검증 코드가 된다. (b)는 오늘 `hybrid_rag_node`가 **이미 하고 있는 동작**(벡터 정렬만 적용, 최상급 무시)에 "그 사실을 답변에 알린다"만 더하는 것이라 침습이 가장 적고, 새 큐리셋 항목 없이도 결정론 단위테스트(캐비엇 문구 유무)로 고정 가능하다. 이 조합이 실제로 관측되면(향후 큐리셋에 항목이 생기면) 그때 (a)/(c)를 재검토한다 — deferred-work.md에 그 트리거로 신규 항목을 남긴다.

**RESET 오염 게이트의 red-proof는 DB가 아니라 캡처 JSON 위에서 이뤄졌다(AC 읽기 정정):** 위 AC(`Given RESET 오염 검사, when 실행하면, then 검사가 일부러 심은 오염 데이터를 teardown한다`)는 문면만 보면 "DB에 오염 행을 심고 지운다"는 뜻으로 읽히기 쉽지만, 오염 판정(`score_ab.contamination_violations`)은 **DB 행을 새로 만드는 것이 아니라, 캡처(raw JSON)에 담긴 반환 id 목록을 대조**하는 로직이다 — `fetch_attrs()`가 그 id들의 기존 카테고리 값을 DB에서 "조회"만 하고 아무것도 쓰지 않는다. 실제 red 증명(2026-08-03, DW-611 resolution 참조)은 M6.t1(교체요청, SUV 전용 턴)의 캡처 결과 id 목록 **사본**에 이미 DB에 존재하는 준중형차 매물 id 1건을 인위로 추가한 뒤 그 사본으로 채점해 `오염(하드): 1`·`게이트: FAIL`을 확인하는 방식으로 했다 — 원본 캡처 파일은 건드리지 않고 임시 사본에서만 실험했으므로 DB에 새로 심거나 되돌릴 행 자체가 없었다(teardown 대상 부재). 즉 이 AC가 실제로 요구·확인한 것은 "DB row teardown"이 아니라 "오염 실험이 원본 증거 파일·DB 상태를 오염시키지 않고 격리된 채로 수행됐는가"이며, 그 조건은 충족됐다 — AC 문구가 DB 시딩을 규정하는 것으로 읽히지 않도록 이 문단으로 명확히 한다.

**공유 유틸 대신 지역 상수:** 최상급 감지가 `contextualize_node`(리파인 신호, 넓게)와 `hybrid_rag_node`(캐비엇 문구, asc/desc 구분)에서 서로 다른 목적으로 쓰이므로, 두 파일에 각각 짧은 상수를 두는 쪽을 택했다(3줄 중복 < 조기 추상화, A2) — 기존 코드도 `_LISTING_SIGNALS`/`_FINANCE_SIGNALS`/`_CATEGORICAL_VOCAB`/`_REFINE_MARKERS`를 파일별 지역 상수로 두는 관례를 따른다.

**G2 두-단계 절차는 새 코드가 아니라 순서다:** `score_ab.py`의 2-file 비교 모드는 이미 파일을 변형하지 않고 비교만 한다 — 1단계(판정)는 기존 그대로 쓴다. 2단계(갱신)는 1단계 통과 확인 후 새 캡처를 `git`으로 커밋 추적되는 기존 경로 위에 얹는 **수동 절차**(plain copy, `run_phase_b.py`의 `capture()`를 다시 부르지 않음 — 그러면 `_PROTECTED_BASELINES`에 막힌다)로, Verification 커맨드 순서로 못박는다.

**2단계 갱신에서 두 파일은 만드는 법이 다르다(2026-08-03 후속 리뷰 정정):** `g2-baseline.json`(raw)은 새 캡처의 plain copy가 맞지만, `g2-baseline-report.json`은 **비교 리포트를 복사하면 안 된다** — 2-file 리포트의 `summaries[0]`은 정의상 *옛* 기준선이라, 복사하면 "기준선 리포트"라는 이름의 파일 첫 요약이 방금 폐기한 수치가 된다(실제로 그렇게 돼 있었다: 0.894/54). 갱신본은 새 기준선 raw로 **1파일 모드**(`--raw` 1개)를 다시 돌려 만든다 — 그래야 요약이 하나뿐이고 그게 실제 현행 기준선이다. 보호목록이 그 경로로의 직접 쓰기를 막으므로 미보호 임시 경로로 출력한 뒤 옮긴다(가드는 의도대로 동작한 것이다).

**왜 재구조화가 아니라 프롬프트 패치인가(2026-08-03 리뷰 정정 — Boundaries&Constraints "구조는 바꾸지 않는다"의 근거):** 에픽 계획 문서는 "먼저 조건을 추출하고 그 결과로 코드가 갈래를 정하는" 재구조화도 후보로 열어뒀지만, 이 스토리는 프롬프트·휴리스틱 텍스트 패치만으로 실제 라이브 재캡처에서 라우팅 정답 57/57을 달성했다(아래 Verification 결과) — 재구조화는 `RouterDecision`·`_fallback_route`·`_route_decision` 3곳 락스텝과 REJECT 분기(DW-614 #2가 지적한 붕괴 위험)까지 건드리는 더 큰 블라스트 반경을 요구하는데, 더 싼 수정으로 목표를 달성했으므로 그쪽을 택하지 않았다(A2 단순함 우선). 프롬프트 패치가 부족한 것으로 드러나면(예: 다음 재캡처에서 다시 흔들리면) 그때 재구조화를 재검토한다.

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/test_router_node.py tests/test_contextualize_node.py tests/test_hybrid_rag_node.py -v` -- expected: 신규 최상급/교체요청/캐비엇 테스트 전부 PASSED
- `cd api && DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_ab_scoring.py -v` -- expected: 4축 게이트·`--raw` 순서 테스트 전부 PASSED(뮤테이션 주입 시 red, 원복 시 green 확인 포함)
- `cd api && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/integration/test_doc_rag_node_real_db.py -v -rs` -- expected: 1 passed, 0 skipped
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -v -rs` -- expected: collected 11 · 0 skipped, 또는 langsmith 트레이싱 미설정 환경이면 1 skipped(langsmith만) · 나머지 10 PASSED — `-rs`로 스킵 사유를 요약에 찍어, 스킵이 예상보다 많으면(=대량 스킵) 그 자체가 게이트 실패로 읽히게 한다(DW-630 — pin하지 않으면 "전부 스킵돼도 초록"이 통과로 보인다)
- G2 1단계: `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=... .venv/bin/python scripts/run_phase_b.py --out docs/g2-recapture-<YYYY-MM-DD>.json` → `DATABASE_URL=... .venv/bin/python scripts/score_ab.py --raw docs/g2-baseline.json docs/g2-recapture-<YYYY-MM-DD>.json --out docs/g2-recapture-<YYYY-MM-DD>-report.json` -- expected: 4축 전부 비하락, `gate_pass:true`. **`<YYYY-MM-DD>`는 실행 당일 날짜로 치환하고 매번 새로 뜬다** — 이 스토리가 실제로 커밋한 증거(`docs/g2-recapture-2026-08-03.json`·`docs/g2-recapture-report.json`)는 이제 `scripts/baseline_guard.py`의 `PROTECTED_BASELINES`에 등재돼 `--out`으로 재사용하면 두 스크립트 모두 즉시 거부한다(위 명령을 그대로 복사해 다시 돌리면 안 되는 이유).
- G2 2단계(1단계 통과 후에만): `cp api/docs/g2-recapture-2026-08-03.json api/docs/g2-baseline.json && cp api/docs/g2-recapture-report.json api/docs/g2-baseline-report.json` -- expected: git diff로 갱신 확인
- `cd api && .venv/bin/python -m pytest tests/ -q` -- expected: 기존 통과 건수 대비 신규 테스트만큼 증가, 0 failed

**Manual checks (if no CLI):**
- `docs/conventions.md` §6에 `hybrid_rag_node`가 등록됐는지, `api/docs/ai-demo-queries.md`의 ①②④·⑤·SM3 표가 서로 모순 없이 4분기 어휘로 통일됐는지 육안 확인

## Auto Run Result

**Status:** done

**Summary:** 라우터가 최상급 표현("제일 싼"·"가장 비싼")과 차종 교체요청("쏘렌토 같은 SUV로 바꿔줘")을 구조조건으로 인식하지 못해 CLARIFY로 오분류하던 문제(DW-611·612)와, `contextualize_node`가 최상급만 담긴 REFINE 턴을 주제전환으로 오판해 이전 조건을 접지 못하던 문제를 최소 침습 프롬프트/휴리스틱 정정으로 고쳤다. G2 회귀 게이트를 `result_mean` 단일축에서 4축 비교로 확장하고, RESET 오염 게이트가 실제로 발화 가능함을 실측(주입 red·복원 green)으로 증명했으며, 13.7·13.8 후속 리뷰가 넘긴 문서·로스터 드리프트 6건(DW-619·620·625·627·630·632)을 정정했다. 리뷰 1패스에서 발견된 10건(라우터 조건 순서 버그 1건 포함)은 전부 패치로 반영·재검증했다.

**Files changed:**
- `api/app/graph/router_node.py` -- 최상급·교체요청을 구조조건으로 분류하는 프롬프트 규칙·예시 추가(DW-611·612·617).
- `api/app/graph/contextualize_node.py` -- `_REFINE_MARKERS`에 "제일"·"가장" 추가 + `_is_topic_shift` 판정 순서 정정(카테고리 값 교체 검사를 마커 단축 판정보다 먼저 — 리뷰 patch #1).
- `api/app/graph/hybrid_rag_node.py` -- 최상급×HYBRID 정렬 캐비엇 추가(옵션 b), NONE-폴백 경로에도 적용 + 가격 형용사 동반 조건으로 좁힘(리뷰 patch #2·#3).
- `api/scripts/score_ab.py` -- G2 게이트 4축 확장(DW-626), `scored_n` 불일치 시 개수축을 검증불가로 표시(리뷰 patch #4), `baseline_raw`/`candidate_raw`·`self_comparison` 필드 추가(DW-637, 리뷰 patch #7).
- `api/scripts/run_phase_b.py`, `api/scripts/baseline_guard.py`(신규) -- 기준선 보호를 공용 모듈로 통합(DW-635·636), 신규 재기준선 증거 파일도 보호 목록에 포함(리뷰 patch #5).
- `docs/conventions.md` -- §6 매물 축 강제 지점에 `hybrid_rag_node` 등록(DW-619).
- `api/tests/integration/test_doc_rag_node_real_db.py`(신규) -- `doc_rag_node`의 FR11 실DB 검증(DW-627), 공유 conftest 픽스처로 리팩터(리뷰 patch #6).
- `api/tests/test_live_smoke.py` -- 라이브 트레이싱 단언을 순수 함수로 분리(DW-641) + "root" 대칭 단언 추가(리뷰 patch #8).
- `api/tests/test_router_node.py`, `test_contextualize_node.py`, `test_hybrid_rag_node.py`, `test_ab_scoring.py`, `test_run_phase_b.py` -- 위 변경 전부를 고정하는 결정론 테스트(양방향 red/green 확인).
- `api/docs/ai-demo-queries.md` -- 표 ①②④·⑤·SM3의 구어휘·불일치 정정(DW-632), "가이드 문서 12개"→10개(DW-620).
- `api/docs/g2-baseline.json`, `g2-baseline-report.json` -- 두-단계 절차로 교체(1단계 판정 통과 확인 후). `g2-recapture-2026-08-03.json`·`-report.json`(신규) -- 갱신 전후 비교 증거, 보호 목록에 등재.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-611·612·619·620·625·626·627·630·632·635·636·637·640·641 종결, DW-642(CORS 비대칭 이월)·DW-643(epic-context 재컴파일, 원인 규명 후 종결)·DW-644(계획 문서의 되묻기 상한 서술 오류, 신규 defer) 등재.
- `_bmad-output/implementation-artifacts/epic-13-context.md` -- step-01 컨텍스트 캐시 재컴파일(계획 산출물 기준, DW-643 참조 — 이 스토리의 코드 변경이 아니라 워크플로 자체의 캐시 무효화 절차).
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` -- "가이드 문서 12개" 정정(DW-620).

*2패스(후속 리뷰)가 추가로 바꾼 것:*
- `api/scripts/score_ab.py` -- docstring·에러 안내의 `--out` 예시를 미보호 날짜 템플릿으로 교체(2패스 patch #1), 최상위 `gate_pass`를 `unverifiable_axes`+summary별 게이트까지 포함하도록 교정(#2), `result_n` 커버리지 가드 추가(#7), `baseline_raw`/`candidate_raw`를 해석된 저장소 상대경로로 기록(#8).
- `api/scripts/run_phase_b.py` -- **변경 없음**(구현 보고는 정정했다고 적었으나 오케스트레이터 확인 결과 고칠 자리가 없었다 — 이 스크립트의 안내 문구는 이미 미보호 템플릿 `docs/g2-exit-gate-YYYY-MM-DD.json`을 가리킨다). 같은 성격의 반대 방향 검사만 `api/tests/test_run_phase_b.py`에 추가했다.
- `api/app/graph/contextualize_node.py` -- `_REPLACEMENT_MARKERS` 도입으로 "교체 의도가 있을 때만 값 교체가 마커를 이긴다"로 순서 재정리(#3), 최상급 판정을 가격 형용사 인접 정규식으로 좁힘(#4). 거짓이 된 주석·docstring 정정.
- `api/app/graph/hybrid_rag_node.py` -- `_has_superlative`를 인접 정규식으로 교체("싼타페" 오발동 제거, #6), 캐비엇 문구를 실제로 통하는 안내로 교체(#11).
- `api/tests/integration/test_doc_rag_node_real_db.py` -- 시드 실패 시에도 고아 행이 정리되도록 이메일 패턴 재조회로 teardown 보강(#10).
- `api/tests/test_ab_scoring.py`·`test_run_phase_b.py`·`test_contextualize_node.py`·`test_hybrid_rag_node.py` -- 위 전부를 고정하는 테스트 추가/교정(+15건). 특히 "문서화된 예시 경로는 보호목록 밖이어야 한다"를 **반대 방향 검사**로 신설.
- `api/docs/g2-baseline-report.json` -- 1파일 모드로 재생성해 단일 요약(라우팅 57 / 0.954)으로 교체(#9).
- `_bmad-output/implementation-artifacts/epic-13-context.md` -- 재컴파일이 지운 제약 3건(로그인 필수·서버측 500자·되묻기 상한 서버 강제) 복원(#5).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-645~650 **신규 6건만** 추가(기존 항목은 오케스트레이터 소관이라 무수정).

**Review findings breakdown (4 layers: adversarial·edge-case-hunter·verification-gap·intent-alignment):**

*1패스(구현 직후):*
- intent_gap: 0, bad_spec: 0
- patch: 10 (high 1, medium 5, low 4) — 전부 적용·재검증 완료(상세는 Review Triage Log)
- defer: 1 (medium) — DW-644 신규 등재
- reject: 2 (low) — 이미 스펙/문서가 스스로 밝혀 둔 트레이드오프라 새 결함 아님

*2패스(후속 리뷰, 같은 날 재실행):*
- intent_gap: 0, bad_spec: 0
- patch: 13 (high 4, medium 5, low 4) — 전부 적용·오케스트레이터 직접 재검증 완료
- defer: 6 (medium 2, low 4) — DW-645~650 신규 등재(기존 항목 무수정)
- reject: 3 (low)
- 이 패스의 high 4건 중 2건(`_is_topic_shift` 순서 부작용, `_has_superlative` 부분문자열 오발동)은 **1패스가 적용한 패치 자신이 만든 회귀**다 — 패치가 새 결함을 만들 수 있다는 것을 이 스토리가 두 번 실증했다.

**Follow-up review recommendation:** true — 3패스에서도 patch 중 high 1건이 있어 규칙상 true. 참고 점수: 3×4+1×6=18(3패스 기준). 2패스 기준은 3×5+1×4=19였다.

*3패스(후속 리뷰, 3차):*
- intent_gap: 0, bad_spec: 0
- patch: 11 (high 1, medium 4, low 6) — 전부 적용·오케스트레이터 직접 재검증 완료
- defer: 3 (medium 1, low 2) — DW-651~653 신규 등재(기존 항목 무수정)
- reject: 6 (low 6)
- 이 패스의 high 1건과 medium 2건(`_has_superlative` 인접 오발동, 라이브 스모크 초록 오인)은 **2패스가 적용한 패치 자신이 만든 결함**이다 — 1패스 2건에 이어, 패치가 새 결함을 만드는 현상이 이 스토리에서 세 번째로 실증됐다.

**Verification performed:**
- 리뷰 패치 전: `pytest tests/ -q` → 502 passed, 6 skipped, 0 failed(오케스트레이터 직접 재실행으로 확인). `docs/g2-baseline-report.json` 직접 읽어 라우팅 54/57→57/57·result_mean 0.894→0.954(개선)·doc_hit 12/13·clarify_ok 9/9 유지·4축 `regression_axes` 전부 false·`gate_pass:true`를 확인.
- 리뷰 1패스(4개 레이어 병렬) 종료 후, patch 10건을 구현 서브에이전트에 동기 재위임(SendMessage로 재개, TaskOutput block=true로 완료까지 대기)해 전부 적용.
- 패치 적용 후: `pytest tests/ -q` → 511 passed, 6 skipped, 0 failed(오케스트레이터 직접 재실행으로 재확인, 서브에이전트 자체 보고 509는 로컬 라이브 스킵 조건 차이로 추정되는 근소한 오차이며 실패 0건은 일치).
- patch #1(`_is_topic_shift` 순서)·#4(`score_ab.py` scored_n 가드) 코드를 오케스트레이터가 직접 열어 재검증: 두 파일 모두 리뷰가 지적한 정확한 수정이 반영돼 있음을 확인.
- 새로 넣거나 고친 검사는 전부 양방향(주입 시 red, 원복 시 green)으로 서브에이전트가 재확인했다(상세는 구현 보고 — `_is_topic_shift` 순서 되돌리기, `scored_n` 불일치 케이스 구성, 4축 게이트를 3축으로 되돌리기, 판매완료 필터 무력화, 기준선 보호 무력화 등).

*2패스(후속 리뷰) 검증:*
- 리뷰 4개 레이어를 병렬 동기 실행한 뒤, 보고를 채택하기 전에 **오케스트레이터가 직접 실행해 재현**했다: `is_protected()`로 보호목록 자기부정 확인(문서화된 경로 3개 전부 True), `_is_topic_shift`·`_has_superlative` 직접 호출로 회귀 케이스 8건 재현, 커밋된 4개 JSON의 md5 대조(동일 2쌍), `epic-13-context.md`의 제약 3건 grep 0건, `g2-baseline-report.json`의 `summaries[0]`이 폐기 수치(0.894/54)임을 확인.
- 패치 13건 적용 후 오케스트레이터가 같은 검사를 재실행: `_is_topic_shift` 8/8·`_has_superlative` 7/7 기대값 일치, docstring 예시 경로 `is_protected` False, 최상위 `gate_pass`가 `unverifiable_axes`·summary별 게이트를 포함하도록 교정됨을 소스로 확인, `g2-baseline-report.json`이 1파일 모드 단일 요약(라우팅 57 / 0.954)으로 교체되고 `g2-recapture-report.json`과 더 이상 동일하지 않음(md5 상이) 확인, `epic-13-context.md` 제약 3건 복원 확인.
- `TEST_DATABASE_URL=... pytest tests/ -q` → **526 passed, 8 skipped, 0 failed**(오케스트레이터 직접 실행). 1패스 종료 시점 511 passed 대비 +15는 이번 패스가 추가한 테스트 수와 일치한다. 신규 실DB 통합테스트는 로컬 Supabase(포트 55322)로 실제 실행됐다(skip 아님).
- 이번 패스가 넣거나 고친 검사도 전부 양방향으로 깨서 확인했다(구현 보고 실측: 보호목록 예시 되돌리기 → red, `gate_pass` 공식 되돌리기 → red 3건, `_is_topic_shift` 순서 되돌리기 → red, `_has_superlative` 부분문자열로 되돌리기 → red 2건, `result_n` 가드 무력화 → red, `_resolve_evidence_path` 항등함수화 → red 2건; 전부 원복 시 green). P10(고아 행 정리)은 conftest 공유 코드를 건드리지 않기 위해 pytest 대신 동일 코드경로를 재현하는 독립 스크립트로 실측했다(옛 로직 잔존 1건 → 새 로직 0건).

**Residual risks:**
- 두 헤드라인 수정(최상급·교체요청 라우팅)의 실제 분류 정확도는 프롬프트 문자열을 고정하는 결정론 테스트와, 1회성 라이브 재캡처(2026-08-03) 서술로만 뒷받침된다 — 모델이 바뀌면 재현 가능한 회귀 테스트 없이 조용히 흔들릴 수 있다. 스펙이 이미 이 한계를 DW-614 #6 근거로 명시적으로 수용한 트레이드오프다(reject 처리, 새 결함 아님) — 다음 라우팅 관련 스토리가 재캡처할 때 다시 확인해야 한다.
- 구현 서브에이전트가 patch #6(실DB 테스트 teardown)에서 스펙 지시(conftest 롤백 패턴)를 문자 그대로 따르지 않고 커밋 기반 정리로 판단을 바꿨다 — `doc_rag_node`가 별도 커넥션(`ai_readonly` 풀)으로 읽어 롤백만으로는 그 커넥션에서 안 보인다는 근거를 코드(`readonly.py`)로 직접 확인한 뒤 내린 판단이며, 실패 시에도 teardown이 도는 것(try/finally)을 실측했다 — 근거가 확인됐으므로 그대로 채택했다.
- patch #5(기준선 보호) red 확인 과정에서 이번 스토리가 만든 재기준선 증거 파일(`g2-recapture-2026-08-03.json`·`-report.json`, 커밋 전이라 git 복구 불가)이 일시적으로 0건 캡처로 덮어써졌다가 `g2-baseline.json`에서 재구성해 바이트 단위로 복구됐다 — 데이터 유실은 없었으나, 보호 검사 자체를 검증하는 과정에서도 보호 대상 파일을 다치기 쉽다는 점이 실측으로 재확인됐다(다음에 유사 가드를 테스트할 때 임시 디렉터리 사용을 권장).
- `deferred-work.md`에 DW-642(CORS 비대칭, 이월)·DW-644(계획 문서 되묻기 상한 서술 오류, 신규)가 열린 채로 남아 있다 — 둘 다 이 스토리 스코프 밖이며 trigger가 명시돼 있다.
- Epic 13 종료 판정(에픽의 유일한 회귀 게이트)이 이 스토리의 G2 1단계 통과로 충족됐다 — 사용자에게 에픽 13 종료를 알리고 다음 에픽(14 또는 15) 착수 여부를 확인해야 한다.

*2패스(후속 리뷰) 이후 남은 위험:*
- **커밋된 G2 수치(라우팅 57/57·result_mean 0.954)는 2패스 패치 이전 코드로 캡처된 것이다.** 2패스가 `_is_topic_shift` 판정 순서와 `_has_superlative` 범위를 바꿨으므로, 엄밀히는 재캡처해야 그 수치가 현행 코드의 것이 된다. 다만 실측으로 다음을 확인했다: (a) 패치 전 코드(HEAD)와 패치 후 코드로 큐리셋의 **멀티턴 후속 턴 10개 전부를 `_is_topic_shift`에 통과시킨 결과 판정이 바뀐 것이 0건**이다(M3.t2·M6.t2·M8.t2는 여전히 RESET, 나머지 7턴은 여전히 맥락 유지) — 이번에 동작이 바뀐 입력 클래스(지시어+값교체 동시 등장, 비-매물 최상급, 차명 "싼타페"에 붙는 최상급)가 큐리셋에 **하나도 없기** 때문이다. (b) `_has_superlative`가 True인 문항은 S6·S7·M1.t3·M2.t3 넷뿐이고 전부 가격 형용사를 동반한 SQL 라우팅 항목이라, 캐비엇이 붙는 HYBRID 경로의 채점 답변에는 애초에 닿지 않는다. 즉 수치는 바뀌지 않는다고 판단했으나 **라이브 재캡처로 확증하지는 않았다**(실비용·쿼터 소모 회피). 다음 라우팅 관련 스토리가 재캡처할 때 확인해야 한다.
- 2패스 patch #4가 최상급 판정을 "가격 형용사 동반"으로 좁히면서 `가장 싼 할부 이자율이 뭐야?`류(가격 형용사를 가진 비-매물 주제)는 여전히 앞선 매물 조건을 끌고 간다 — 알려진 잔여 구멍으로 DW-648에 등재했다. 제대로 닫으려면 비-매물 주제 어휘 사전이 필요해 이 스토리의 최소 침습 범위를 벗어난다.
- 라우터의 최상급 규칙이 **가격 축에만** 닫혀 있다(연식·주행거리·연비 최상급은 여전히 CLARIFY) — DW-645. 스펙 Never 절이 유예한 것은 "주관적 최상급"이지 객관적 정렬축이 아니므로, 이건 의도적 유예가 아니라 못 본 자리다.
- 1패스가 적용한 패치 10건 중 2건이 2패스에서 회귀로 잡혔다(순서 부작용·부분문자열 오발동). 패치는 그 자체가 검증 대상이라는 뜻이며, 이번 패스의 13건도 같은 위험을 갖는다 — `followup_review_recommended: true`를 유지하는 실질적 근거다.

*3패스(후속 리뷰, 같은 날 3차)가 추가로 바꾼 것:*
- `api/app/graph/contextualize_node.py` -- 값 교체가 리파인 마커를 이기는 범위를 `body_type` 축 하나로 좁힘(3패스 P1). 색상·지역·연료·제조사 교체는 pre-diff대로 맥락을 유지한다.
- `api/app/graph/hybrid_rag_node.py`, `contextualize_node.py` -- `_SUPERLATIVE_PRICE_RE`에 어간형 형용사 음절 경계 추가(P2), 두 사본 락스텝 유지.
- `api/scripts/score_ab.py` -- `gate_pass:false`일 때 exit 1(P3), 비교 축 0개인 경우를 `regression_block:null`로 구분(P4), `_resolve_evidence_path`를 posix 경로로 통일(P8).
- `api/scripts/baseline_guard.py` -- 새 증거 파일 `g2-baseline-pre-13-9.json` 등재(P5), 보호 층 위치를 사실대로 적도록 주석 정정(P10).
- `api/docs/g2-baseline-pre-13-9.json`(신규) · `g2-recapture-report.json` -- 13.9 이전 기준선 raw를 저장소에 들여오고 리포트를 재생성해 `baseline_raw`를 저장소 상대경로로 교체(P5). 판정값은 전부 보존.
- `api/tests/test_live_smoke_helpers.py`(신규) · `test_live_smoke.py` -- 순수 함수 단위테스트 5건을 분리해, 라이브 파일이 라이브 실행 없이 pass를 낼 수 없게 함(P6).
- `api/tests/integration/test_doc_rag_node_real_db.py` -- `readonly._pool`을 monkeypatch로 바꾸고 teardown에 `close_pool()` 추가(P9).
- `docs/conventions.md` -- §6 `문서 RAG 결과 필터`에 파일 경로·유일 강제 지점 근거·강제 장치 명시(P11).
- `api/tests/test_contextualize_node.py`·`test_hybrid_rag_node.py`·`test_ab_scoring.py`·`test_run_phase_b.py` -- 위 전부를 고정하는 테스트(+18건, 두 패턴 동일성 단언 P7 포함).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-651~653 **신규 3건만** 추가(기존 항목 무수정).

*3패스(후속 리뷰, 3차) 검증:*
- 4개 레이어를 병렬 동기 실행한 뒤, 보고 채택 **전에** 오케스트레이터가 직접 재현했다: `git show 1cf5d7ac:api/app/graph/contextualize_node.py`로 pre-diff 판정 함수를 꺼내 현행과 나란히 호출해 진리표를 대조(6건 중 5건이 `False→True`로 뒤집혀 있음을 확인), `_has_superlative` 11개 입력 직접 호출, `grep sys.exit scripts/score_ab.py` 0건, 커밋된 `g2-recapture-report.json`의 `baseline_raw` 필드 직접 읽기, `env -u RUN_LIVE_SMOKE pytest tests/test_live_smoke.py` → `5 passed, 6 skipped` 실행, 스크래치패드 원본 md5 대조, `deferred-work.md` 전문 grep으로 "최상급×HYBRID 트리거 항목 0건" 확인.
- 패치 11건 적용 후 같은 검사를 오케스트레이터가 재실행: P1 진리표 6/6 `False` + DW-612 케이스는 여전히 `True`, P2 11개 입력 전부 기대값 일치(기존 green이던 `가장 저렴한 SUV로 바꿔줘`·`제일 저렴한 SUV` 포함), 두 정규식 패턴 문자열 동일, `sys.exit(1)` 존재, `baseline_raw = docs/g2-baseline-pre-13-9.json`·md5 `523196c3…` 원본과 동일·판정값(`gate_pass:true`/라우팅 54→57/result_mean 0.8936→0.9542) 보존, 라이브 파일 `6 skipped`·헬퍼 파일 `5 passed`.
- 스펙 Verification 커맨드 재실행(오케스트레이터 직접): 라우터·맥락화·하이브리드 **86 passed**, `test_ab_scoring.py` **75 passed**, 실DB 통합테스트 **1 passed, 0 skipped**(로컬 Supabase 실행), 전체 `pytest tests/ -q` → **544 passed, 6 skipped, 0 failed**(2패스 종료 시점 526 대비 +18은 이번 패스가 추가한 테스트 수와 일치).
- 이번 패스가 넣거나 고친 검사도 전부 양방향으로 깨서 확인했다(구현 실측: P1 축 범위 되돌리기 → 5 failed, P2 옛 패턴 복귀 → 8 failed, P3 `sys.exit` 제거 → 5 failed, P4 `any()` 복귀 → 1 failed, P5 보호목록 항목 제거 → 1 failed, P7 한쪽 정규식만 확장 → 1 failed, P8 Windows 경로 모사 → 1 failed; 전부 원복 시 green). P5의 red 확인 과정에서 이번에도 보호 대상 파일이 실제로 손상됐다가(md5 변화) 원본에서 복구됐다 — 2패스가 남긴 "가드를 검증하다 가드 대상을 다친다"는 경고가 그대로 재현됐다.

*3패스(후속 리뷰) 이후 남은 위험:*
- **`_is_topic_shift`가 세 패스 연속으로 회귀했다**(1패스 patch #1 → 2패스 patch #3 → 3패스 P1). 매번 직전 패치가 만든 부작용이었고, 매번 다음 패스에서야 잡혔다. 이번 수정은 축을 `body_type` 하나로 좁혀 표면적이 가장 작지만, 이 함수는 결정론 테스트가 커버하는 입력 조합보다 실제 입력 공간이 훨씬 넓다는 것이 세 번 실증됐다 — `followup_review_recommended: true`의 가장 강한 근거다.
- **커밋된 G2 수치는 여전히 2패스·3패스 패치 이전 코드로 캡처된 것이다.** 3패스는 `_is_topic_shift`(축 좁힘)와 `_SUPERLATIVE_PRICE_RE`(경계 추가)를 또 바꿨다. 2패스가 실측한 논거(큐리셋 멀티턴 후속 10턴 전부 판정 불변, `_has_superlative` True 문항 4건은 전부 SQL 경로)는 이번 변경 방향(둘 다 **좁히는** 방향)에서도 유지되지만, 라이브 재캡처로 확증하지는 않았다(실비용·쿼터 회피). 다음 라우팅 관련 스토리가 재캡처할 때 확인해야 한다.
- `제일 싼 차 뭐야?`는 라우팅은 고쳐졌지만 여전히 **5건**을 반환한다 — 스펙 I/O 매트릭스가 기대출력으로 적은 `LIMIT 1`의 정렬 절반만 달성됐다. 게이트 쪽(스코어러가 `count_range` 미채점)은 DW-647, 생성 쪽(`sql_rag_node`가 `LIMIT 1`을 안 냄)은 이번에 DW-652로 신규 등재했다 — 둘을 함께 처리해야 한다.
- 스펙 Design Notes가 약속했던 "최상급×HYBRID 재검토 트리거" 장부 항목이 실제로는 없었다(DW-651로 신규 등재). 스펙 본문의 약속이 장부에 실제로 심겼는지는 아무도 검사하지 않는다 — B8의 "지정한 곳에도 실제로 심는다"가 다시 깨진 자리다.
- Epic 13 종료 판정에는 변화가 없다 — G2 1단계 판정값(`gate_pass:true`, 4축 비하락)은 리포트 재생성 후에도 보존됐다. 사용자에게 에픽 13 종료를 알리고 다음 에픽 착수 여부를 확인해야 한다.
