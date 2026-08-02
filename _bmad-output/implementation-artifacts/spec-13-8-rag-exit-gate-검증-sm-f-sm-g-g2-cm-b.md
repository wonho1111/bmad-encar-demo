---
title: '13.8 RAG exit-gate 검증 (SM-F/SM-G/G2/CM-B)'
type: 'feature'
created: '2026-08-02'
status: 'done'
baseline_revision: '5fd4b67232a084cb671e06c3937b59581679fef5'
final_revision: 'fd28b438ad55533f4c8ad7fe6565657e0f71f3c9'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/api/docs/ai-ab-test-queryset.json', '{project-root}/api/docs/g2-baseline-report.json']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 13(13.1~13.7)이 4분기 라우팅·하이브리드 검색·가이드 질의확장·LangSmith를 구현했지만, 이 구현들이 기존 AI 검색 시연을 깨지 않았고 신규 분기가 실제로 동작하며 보안 안전장치가 그대로인지를 **실측으로 증명한 적이 없다** — 코드가 존재한다는 것과 게이트가 실제로 선다는 것은 다르다(B4).

**Approach:** 새 기능을 만들지 않는다. 이미 저장소에 있는 도구(`run_phase_b.py`/`score_ab.py`의 G2 하니스, `test_live_smoke.py`의 라이브 스모크, sql_guard/ai_readonly/FR11 각 강제지점의 저장된 테스트)를 실제로 돌려 SM-F·SM-G·G2·CM-B 네 게이트를 실측 확인하고, 그 과정에서 드러난 두 문서(`ai-demo-queries.md`, `run_phase_b.py` 독스트링)의 낡은 서술을 정정한다.

## Boundaries & Constraints

**Always:**
- 네 게이트 전부 라이브/실DB 실행으로 확인한다 — 존재 확인을 작동 확인으로 착각하지 않는다(B4).
- G2는 `api/docs/g2-baseline.json`(13.1이 심고 DW-609가 2026-08-02 **현재 코드 기준**으로 재캡처한 47문항 Phase B 기준선)을 그대로 비교 대상으로 쓴다. 새 기준선을 만들지 않는다.
- SM-F(구조형·질적형·가드 유지)와 SM-G(하이브리드·되묻기·거절 신규 동작)는 `api/tests/test_live_smoke.py`의 기존 4개 라이브 테스트(`pathA`/`pathB`/`pathC`/`hybrid`)로 함께 커버된다 — `pathB`가 "질적형 유지"이자 "되묻기 신규 동작"을, `pathC`가 "가드 유지"이자 "거절 신규 동작"을 **같은 메커니즘**으로 동시에 증명하므로 신규 시연을 따로 만들지 않는다. "질적형 유지"는 **느슨한 읽기**다 — pathB의 출력 형태는 13.4 이전(매물 카드)과 다르다(현재는 CLARIFY 되묻기). "유지"는 "정상적인, 에러·빈손·무관 응답이 아닌 결과를 낸다"는 뜻이며, 정확한 사유는 Design Notes에 남긴다.
- CM-B는 세 안전장치(sql_guard·ai_readonly·FR11)를 저장된 테스트로 확인한다: sql_guard 자체(`test_sql_guard.py`), ai_readonly 롤 격리(`test_readonly.py`), FR11의 4개 강제지점(sql_guard/hybrid_rag_node/doc_rag_node/listing_cards — 단위 3건 `test_hybrid_rag_node.py`/`test_doc_rag_node.py`/`test_listing_cards.py` + 실DB 통합 1건 `test_fr11_cover_images_real_db.py`; sql_guard 자체 테스트와 중복 세지 않음). 새 검사를 추가하지 않는다(조사로 전부 테스트 존재 확인됨).

**Block If:**
- G2 재캡처가 `is_partial: true`이거나 `errored_n > 0`이면 그 결과로 회귀 판정을 내리지 않는다. DB(로컬 Supabase 55322)·쿼터·네트워크 원인을 밝히고 재시도하고, 그래도 안정적으로 47/47 채점되지 않으면 HALT.
- G2가 `is_partial:false`·`errored_n:0`(완전 채점)인데도 `regression_block:true`(진짜 result_mean 하락)면, 회귀로 즉시 결과에 기록하고 게이트 실패로 보고한다 — HALT는 아니다(원인 규명은 후속 스토리 몫).
- 라이브 스모크·CM-B 테스트가 코드 결함으로 실패(스킵 아닌 진짜 실패)했을 때: 그 결함이 13.9 범위(라우팅 안정화, DW-611/612류)이면 고치지 않고 게이트 실패로 결과에 남긴다 — 우회 금지. 13.1~13.7 범위(이 스토리가 검증하는 구현 자체)의 결함이면, 사소하면 이 스토리에서 직접 고치고(patch), 아니면 게이트 실패로 즉시 HALT — 어느 경우든 우회 금지.

**Never:**
- 새 관측 지표·스코어링 축을 추가하지 않는다. G2 게이트 정의(`contamination==0 and deadend==0 and errored_n==0 and scored_n>0` + `result_mean` 비하락)는 이미 `score_ab.py`에 있고, 이 스토리는 그걸 실행할 뿐이다.
- `score_ab.py`의 `lexicographic_winner()`(모델 A/B 채택 랭킹) 결과를 게이트 판정에 쓰지 않는다 — 13.8은 후보 모델 비교가 아니라 **단일 코드 상태**(post-13.7)의 회귀 확인이다. DW-564·DW-565는 "13.8=모델 채택 판단"을 전제로 defer됐으나, `epics-increment-2026-07-12.md`의 실제 13.8 AC엔 모델 비교가 없다 — 이 스펙에서 그 전제를 정정하고 두 항목·DW-556을 범위 밖으로 종결한다(모델 후보 비교가 실제로 생기면 그때 다시 연다).
- Story 13.9(라우팅 안정화)의 작업을 앞당기지 않는다. DW-611(S6·M1.t2, 최상급 표현 CLARIFY 오분류)·DW-612(M6.t1, 교체요청 CLARIFY 오분류로 RESET 오염 게이트 무력화)는 이미 baseline(54/57)에 반영된 기지 결함이라 G2 회귀 게이트를 막지 않는다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| G2 정상 재실행 | 로컬 Supabase 가동, 47문항 라이브 캡처 → 2-file 채점 | `scored_n=47`·`is_partial=false`(양쪽 파일 모두) · `gate_pass=true` · `regression_block=false` | — |
| G2 부분 실패 | 일부 항목 429/DB 오류 | `errored_n>0` 또는 `is_partial=true` | 회귀 판정 보류(Block-If), 원인 규명 후 재시도 |
| G2 완전 채점·실회귀 | `is_partial=false`·`errored_n=0`인데 `regression_block=true` | 게이트 실패로 즉시 결과에 기록 | HALT 아님(Block-If) — 원인 규명·수정은 후속 스토리(13.9 등) 몫 |
| SM-F/SM-G 라이브 스모크 | `RUN_LIVE_SMOKE=1`로 4개 테스트 실행 | 4개 전부 PASSED | 실패가 13.9 범위 결함이면 결과에 명시하고 게이트 실패 보고 |
| CM-B 안전장치 | sql_guard·ai_readonly·FR11 저장 테스트 전량(단위+통합) | 전부 PASS, 판매완료 매물이 4개 지점 어디서도 노출 안 됨(실DB 확인) | 실패 시 보안 블로커로 즉시 기록(우회 금지) |

</intent-contract>

## Code Map

- `api/docs/ai-demo-queries.md` -- ①②③④ 표(6~10줄, 25~42줄)가 여전히 구 A/B/C 3경로로 서술돼 있어 하단 SM3 매핑 표(이미 CLARIFY로 정확함)와 모순 -- 정정
- `api/scripts/run_phase_b.py` -- 독스트링의 "44개 질의·2026-07-30 실행" 문구가 실제 47문항/08-02 큐리셋과 어긋남(수치 사본 노후화) -- 정정
- `api/docs/g2-baseline.json`, `api/docs/g2-baseline-report.json` -- G2 비교 대상 Phase B 기준선 (읽기전용)
- `api/tests/test_live_smoke.py` -- SM-F/SM-G 실동작 검증 도구 (읽기전용 실행)
- `api/tests/test_sql_guard.py`, `api/tests/test_readonly.py`, `api/tests/test_hybrid_rag_node.py`, `api/tests/test_doc_rag_node.py`, `api/tests/test_listing_cards.py`, `api/tests/integration/test_fr11_cover_images_real_db.py` -- CM-B 4대 강제지점 검사 (읽기전용 실행)
- `api/tests/demo_queries.py`, `api/tests/test_demo_acceptance.py` -- ③ 회색지대 예시 질의(문서 갱신에 맞춰 함께 갱신 필요, drift 금지 관례) -- 리뷰에서 드러난 문서-테스트 불일치 정정
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-556·DW-564·DW-565를 범위 밖으로 종결, DW-576을 부분 종결(질의 재분류분)

## Tasks & Acceptance

**Execution:**
- `api/docs/ai-demo-queries.md` -- 3~10·25~42줄을 4분기 어휘(REJECT/CLARIFY/SQL/HYBRID)로 정정, "질적형→B(매물)"을 "질적형/애매형→CLARIFY(되묻기, 매물 아님)"으로 바꾸고 회색지대 절도 동일 반영 -- SM3 매핑 표와의 문서 내부 모순 제거
- `api/scripts/run_phase_b.py` -- 독스트링 수치·날짜를 47문항/2026-08-02로 정정 -- "수치 사본은 늙는다"(13-7 리뷰가 이미 지적한 패턴) 재발 방지
- (검증) `docs/g2-baseline.json` 대비 오늘 재캡처 결과를 `score_ab.py` 2-file 모드로 채점 -- G2 게이트 실측
- (검증) `test_live_smoke.py` 4종 + CM-B 관련 저장 테스트 전량을 라이브/실DB로 실행 -- SM-F/SM-G/CM-B 실측
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-556·564·565에 "13.8 범위 밖(모델 비교 아님)" 종결 사유 기록
- `api/docs/ai-demo-queries.md` -- SM3 매핑 표의 ③ 회색지대 판정 기준을 REJECT도 정답으로 인정하도록 정정(리뷰 발견: ③ 표는 REJECT를 정답으로 새로 규정했는데 판정 기준 문구는 여전히 "거절 아님"이라 문서 내부 모순)
- `api/tests/test_demo_acceptance.py` -- `test_sm3_gray_zone_returns_listings_either_route`의 `route` 파라미터에 `REJECT` 추가 + REJECT 분기 단언(빈 목록·고정 거절 문구) -- 문서가 정답으로 규정한 REJECT 경로를 결정론 테스트가 전혀 검증하지 않던 공백 제거

**Acceptance Criteria:**
- Given 현재 코드(13.1~13.7 전량), when `RUN_LIVE_SMOKE=1`으로 `test_live_smoke.py::test_live_smoke_pathA/pathB/pathC/hybrid`를 실행하면, then 4건 전부 PASSED이고 각각 SQL/CLARIFY/REJECT/HYBRID route와 페이로드(`clarify.chips`·`narrowed_by`·가이드 인용 로그)가 테스트 단언대로 확인된다(SM-F 3종 + SM-G 3종 동시 충족). Verification 커맨드는 같은 파일의 나머지 2건(`clarify_cap_forces_results`·`langsmith_tracing`)도 함께 돈다 — `langsmith_tracing`은 LangSmith env가 raw 프로세스 환경변수로 노출되지 않으면 SKIPPED(실패 아님)로 자연 스킵되며, 이는 SM-F/SM-G 판정과 무관하다(13-7이 이미 정의한 게이트 동작).
- Given `docs/g2-baseline.json`(47문항 Phase B 기준선), when 동일 큐리셋을 현재 코드로 라이브 재캡처해 `score_ab.py` 2-file 모드로 채점하면, then 두 파일 모두 `is_partial:false`·`scored_n:47`이고 `gate_pass:true`이며 `regression_block:false`다. **⚠️ 자동 판정의 실제 범위(13.8 3차 리뷰 정정):** `regression_block`은 `result_mean` **한 축만** baseline과 비교하고(`score_ab.py`의 `candidate.result_mean < baseline.result_mean`), 그 `result_mean`조차 결과집합 비교가 가능한 33/47 항목의 평균이다. `routing_correct`·`doc_hit_n`·`clarify_ok_n`은 어느 자동 게이트도 baseline과 비교하지 않는다 — 이 세 축의 비하락은 아래 Verification의 **Manual checks(두 리포트 수치 대조)** 로만 확인되며, 이 실행에서는 실제로 수행해 정확히 일치함을 확인했다. 원래 이 AC는 네 축 전부가 `regression_block`으로 보증되는 것처럼 적혀 있었는데 사실이 아니다(리뷰가 캡처를 변형해 실증: 가이드 인용 전멸 12/13→0/13, CLARIFY 분기 전멸 54→47·9/9→2/9 둘 다 `gate_pass:true`·`regression_block:false`로 통과). 구조적 해소는 DW-626.
- Given sql_guard·ai_readonly·FR11의 4개 강제지점 저장 테스트(단위 3종 + `test_fr11_cover_images_real_db.py`), when 전량 실행하면, then 전부 PASS이고 판매완료 매물이 각 지점에서 노출되지 않음이 확인된다. **⚠️ 검증 층이 지점마다 다르다(13.8 3차 리뷰 정정):** 실제 Postgres에 붙는 것은 `test_fr11_cover_images_real_db.py`(이미지 축) **1지점뿐**이고, `hybrid_rag_node`·`doc_rag_node`·`listing_cards` 3지점은 `run_select`를 모킹해 **생성된 SQL 문자열에 `status='on_sale'`이 들어 있는지**를 보는 결정론 단위테스트다. 원래 이 AC는 네 지점 전부를 "실DB로 확인"으로 일반화했는데, 그건 이 스펙 자신이 인용한 B4("존재 확인 ≠ 작동 확인")를 어기는 과장이다. 특히 `doc_rag_node`는 sql_guard를 안 거치고 `listings`의 ai_readonly RLS가 `using(true)`라 그 WHERE 한 줄이 유일한 방어인데, 리뷰가 `(status='on_sale' OR true)`로 무력화해도 CM-B 커맨드 전량이 스펙에 적힌 수치 그대로 초록임을 실증했다(원복 확인). 구조적 해소는 DW-627.
- Given `ai-demo-queries.md` 갱신 후, when 문서를 읽으면, then ①②③④ 표와 하단 SM3 매핑 표가 4분기 어휘로 서로 모순 없이 일치한다(REJECT 포함)
- Given 갱신된 `test_sm3_gray_zone_allowed_routes_are_not_dead_ends`(3차 리뷰에서 개명 — 절반의 케이스가 "매물 없음"을 단언하는데 옛 이름은 `returns_listings`였다), when `pytest tests/test_demo_acceptance.py -k gray`를 실행하면, then 질의별 허용 경로 6건 + 락스텝 검사 1건이 PASS한다. SQL·HYBRID 케이스는 `_patch_route`가 노드별로 주입하는 카드 id(`s1`/`h1`)까지 단언해 분기 오배선을 잡는다

## Spec Change Log

## Review Triage Log

### 2026-08-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 5, low 6)
- defer: 2: (high 0, medium 1, low 1)
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` (edge-case-hunter) `ai-demo-queries.md` ③ 표가 REJECT를 회색지대 정답으로 새로 규정했는데 하단 SM3 매핑 표는 여전히 "거절 아님"을 합격 기준으로 적어 문서 내부 모순 — SM3 매핑 행을 REJECT 포함으로 정정.
  - `[medium]` `[patch]` (edge-case-hunter) `test_sm3_gray_zone_returns_listings_either_route`가 REJECT 분기를 검증하지 않아 문서가 정답으로 규정한 경로에 대응하는 테스트가 없었다 — `route` 파라미터에 `REJECT` 추가 + 빈 목록·고정 거절 문구 단언 추가, 실행 확인(PASSED).
  - `[medium]` `[patch]` (adversarial) SM-F의 "질적형 유지"가 실제로는 13.4 이후 출력 형태(매물→CLARIFY)가 바뀐 것을 가리는 표현이었다 — Always/Design Notes에 "느슨한 읽기"(정상 비-에러 응답)임을 2026-07-31 사용자 확정 근거와 함께 명시.
  - `[medium]` `[patch]` (edge-case-hunter) I/O 매트릭스·Block-If가 "완전 채점인데 실제 회귀"·"13.1~13.7 범위 결함" 두 시나리오를 다루지 않아 향후 재실행 시 처리 절차가 불명확 — 매트릭스 행 1개 추가 + Block-If 2문장 추가.
  - `[low]` `[patch]` (adversarial) Never절의 DW-611·612 인용이 DW-612의 실제 대상(M6.t1, RESET 오염 게이트)을 누락하고 DW-611과 한 괄호로 뭉뚱그림 — 인용을 항목별로 분리 정정.
  - `[low]` `[patch]` (adversarial) CM-B 서술이 "4개 강제지점" 괄호에 sql_guard를 중복 포함하고 ai_readonly(`test_readonly.py`)를 누락해 실제 테스트 로스터와 문장이 어긋남 — 문구를 sql_guard/ai_readonly/FR11-4지점으로 재구성.
  - `[low]` `[patch]` (adversarial/edge-case-hunter) `g2-exit-gate-report.json`의 `verdict`/`final_adopt`가 동일 코드·동일 모델의 지연시간(latency) 노이즈만으로 "승자"를 선언해, 스펙 맥락 없이 파일만 보는 독자를 오도할 수 있음 — `score_ab.py`는 Never절에 따라 변경하지 않고, Design Notes에 캐비엇 추가 + Auto Run Result 잔여 리스크에 기록.
  - `[low]` `[patch]` (adversarial) DW-564의 "완전 동일" 재현성 근거가 요약 수치뿐이라 파일 재사용 가능성을 배제하지 못함 — verification-gap 레이어가 수행한 per-item diff(`latency_ms` 제외 바이트 동일, `latency_ms`만 상이 = 독립 재실행 증거) 결과를 DW-564 resolution에 추가 기록.
  - `[low]` `[patch]` (intent-alignment) 이 diff의 `ai-demo-queries.md` 질의 교체가 기존 열린 DW-576(② 목록 실측 오분류)의 트리거 조건을 실제로 충족했는데 갱신 없이 지나칠 뻔함 — DW-576을 부분 종결(질의 재분류분)로 갱신하고, 남은 핵심 결함(route monkeypatch 강제)으로 범위를 좁힘.
  - `[low]` `[patch]` (adversarial) AC1(4개 라이브 테스트)과 Verification 커맨드1(파일 전체, 스킵 없음 기대)의 스코프가 어긋나 `langsmith_tracing`의 env 미노출 스킵이 무관한 게이트 실패처럼 보일 수 있음 — AC1에 스킵 사유 설명 추가.
- 리뷰 레이어: blind-hunter(adversarial) 8건, edge-case-hunter 5건, verification-gap 0건(검증 갭 없음 — 코드 미변경, G2 재현성 per-item 확인 등 독립 재현), intent-alignment 서술 3건(전부 위 addressed_findings에 반영).
- defer(신규 등재, deferred-work.md): DW-619(medium, `docs/conventions.md` §6에 `hybrid_rag_node` FR11 강제지점 미등록 — 13.1~13.3부터 있던 선재 결함, 13.8 diff가 만든 게 아님) · DW-620(low, epic 컨텍스트의 "가이드 문서 12개"가 실제 활성 10개와 어긋남 — 선재 드리프트).

### 2026-08-02 — Review pass (후속 리뷰 / follow-up)

- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 3, medium 4, low 6)
- defer: 5: (high 0, medium 3, low 2)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` (adversarial, 오케스트레이터 재현) Verification 커맨드가 `test_fr11_cover_images_real_db.py`에 `DATABASE_URL`을 넘겼는데 그 파일의 스킵 가드는 `TEST_DATABASE_URL`을 본다 — 실제로는 `1 skipped`였고 종료코드 0이라 "PASSED"로 기록돼 있었다. **CM-B의 FR11 실DB 축이 한 번도 안 돌아간 채 보안 게이트가 통과로 닫혀 있던 것.** 커맨드를 `TEST_DATABASE_URL`로 정정하고 실제로 실행 → **1 passed**(게이트는 실제로 선다).
  - `[high]` `[patch]` (adversarial, 오케스트레이터 재현) CM-B 유닛 커맨드에 `DATABASE_URL`이 없어 `test_readonly.py` 2건(ai_readonly 롤 격리 — Always절이 명시한 세 안전장치 중 하나)이 스킵됐고, "147 passed, 2 skipped"가 통과로 보고돼 있었다. 커맨드에 `DATABASE_URL`·`-rs` 추가 후 실행 → **149 passed, 0 skipped**.
  - `[high]` `[patch]` (edge-case-hunter/verification-gap, git으로 귀속 확인) `epic-13-context.md` 재컴파일이 13.7이 심어 둔 내용을 삭제했다 — G1~CM-B **게이트 정의 문장**, Story 13.9 요구사항 4건(최상급·교체요청 라우팅 / RESET 오염 실데이터 검사 / `contextualize_query` 재작성 / 결정론 단위테스트 고정), 13.9 기술결정(락스텝 계약 유지), "G2 미통과 시 에픽 종료 불가", "앱 레벨 필터링 금지", 하이브리드 추출실패 폴백, 칩 2종 구분, 13.5/13.6 answer_node 순서 의존. **13.9가 바로 다음 스토리이고 그 스펙이 이 파일에서 만들어진다.** 전부 복원(가법 병합 — 새 컴파일의 고유 내용은 유지). 스펙의 "이 스토리 작업물이 아니라 캐시 최신화"라는 기록도 사실과 달라 정정(git은 커밋 69cb941에 귀속).
  - `[medium]` `[patch]` (verification-gap/edge-case-hunter/adversarial 3중 일치) `test_sm3_gray_zone_returns_listings_either_route`가 질의×경로 **교차곱**(3×4=12)이라, 문서가 오답이라 못박은 조합까지 합격으로 단언했다 — 지식형 질의(CL7)가 매물 목록을 주는 것, 가격·인승이 명시된 H6/H7이 거절로 새는 것. 그 상태면 진짜 라우팅 회귀를 이 게이트가 못 잡는다. `demo_queries.GRAY_ALLOWED`(큐리셋 `acceptable_paths`와 1:1)로 질의별 허용 경로를 만들고 파라미터를 12→6으로 좁힘.
  - `[medium]` `[patch]` (edge-case-hunter) `ai-demo-queries.md` ③ 요약이 "빈손·무응답만 아니면 됨"인데 같은 표가 REJECT(=빈 목록)를 정답으로 규정해 자기모순 — 합격 기준을 "행에 적힌 허용 경로로 가고 그 경로가 내놓기로 한 것을 실제로 내놓기"로 재작성.
  - `[medium]` `[patch]` (verification-gap/adversarial) ② 표에 새로 넣은 "출퇴근하기 편한 차"가 큐리셋·라이브 캡처 어디에도 없는 **미실측** 문자열이었다(교체 전 질의는 DW-576이 실측했던 것) — 실측 근거가 있는 큐리셋 CL4 문자열 "출퇴근용으로 편한 차 추천해줘"(관측 라우트 CLARIFY)로 교체, `demo_queries.py`와 락스텝.
  - `[medium]` `[patch]` (edge-case-hunter) `demo_queries.py`의 GRAY 정의가 REJECT를 빠뜨려 같은 커밋의 문서·테스트와 어긋남 + SM3 매핑 표 ③ 행이 여전히 "경로 중 하나면 합격"으로 뭉뚱그림 — 둘 다 질의별 허용 경로 기준으로 정정.
  - `[low]` `[patch]` (adversarial/edge-case-hunter) `ai-demo-queries.md`의 응답 계약 줄이 `{answer, listings[]}` 2필드로 남아 있어, 바로 위에서 CLARIFY(=`clarify` 페이로드)를 새로 설명한 것과 어긋남 — 4분기 계약으로 정정하고 정본을 `conventions.md` §4로 가리킴(사본을 늘리지 않기 위해).
  - `[low]` `[patch]` (edge-case-hunter) ④ "오늘 날씨 어때?" 기대 문구가 13.5 이후 실제 `_GUARD_ANSWER`("차장님")와 다른 옛 문구("어시스턴트")였고, 테스트는 실제 상수를 바이트 단위로 단언 중 — 문구 정정 + 정본이 `guard_node._GUARD_ANSWER`임을 명시.
  - `[low]` `[patch]` (adversarial/edge-case-hunter) `run_phase_b.py` 독스트링의 전량 실행 예시가 `--out docs/g2-baseline.json`(=커밋된 G2 비교 기준선)을 가리켜, 복붙하면 회귀 판정의 기준점이 사라진다 — 세 줄 위에서 `--out`을 필수로 만든 이유와 정면으로 모순. 날짜형 경로 예시 + 덮어쓰기 금지 경고로 정정.
  - `[low]` `[patch]` (edge-case-hunter) `--subset` help가 "전량(47개)"으로 수치를 다시 하드코딩 — `--queryset`은 교체 가능하므로 이 사본은 또 늙는다(이 스토리가 고치려던 바로 그 패턴). 수치를 뺌.
  - `[low]` `[patch]` (adversarial) `demo_queries.py`가 구어휘 변수명 유지 근거를 "하위 호환"이라 적었으나 이 파일 밖 소비처는 테스트 하나뿐이라 사실이 아님 — "아직 안 고친 것"으로 정직하게 고치고 DW-573을 가리킴.
  - `[low]` `[patch]` (adversarial) 라이브 스모크 Verification 기대가 "스킵 없음"이라 AC1의 "`langsmith_tracing`은 SKIPPED가 정상"과 정면 모순 — 정상 스킵이 게이트 실패로 오독되지 않게 기대 문구를 맞춤.
- 리뷰 레이어: adversarial 25건 · edge-case-hunter 14건(삭제 검사 4건 포함) · verification-gap 6건 · intent-alignment 서술 8건. 세 레이어가 독립적으로 같은 결론에 도달한 항목 2건(gray_zone 교차곱, G2 재현성)은 각각 patch·defer로 갈렸다.
- defer(신규 등재, deferred-work.md — 기존 항목은 지시에 따라 일절 수정하지 않음): DW-621(medium, G2는 실행 형태상 재현성 검사이지 회귀 검사가 아님) · DW-622(medium, 스킵된 보안 테스트가 통과와 구별 안 됨 — 이번 patch는 커맨드 한 줄만 고쳤고 구조적 보장은 없음) · DW-623(medium, DW-576의 `status:` 값이 sweep 문법 밖) · DW-624(low, 13.8 diff가 사실관계를 바꾼 기존 항목 6건 미갱신) · DW-625(low, CM-B 로스터가 `conventions.md` §6이 아니라 임의 목록에서 나와 SECURITY DEFINER 축 누락).
- reject 8건(요지): 스펙 status와 sprint-status 불일치(이 리뷰 실행이 만든 일시 상태) · followup 권고가 장부에 없다(이 실행이 곧 그 후속 리뷰) · 리포트 JSON의 `verdict`/`final_adopt` 캐비엇(스펙이 이미 잔여 리스크로 공개) · `DEMO_QUERIES` 죽은 상수(열린 DW-573과 중복 → DW-624로 흡수) · SM-F "질적형 유지" 재정의(Design Notes에 사용자 확정 근거와 함께 이미 명시) · DW-564 재현성 근거 과장(per-item 대조로 이미 확인된 뉘앙스) · 리포트 `detail` 키 충돌(`score_ab.py`는 Never절 범위 밖이고 게이트가 읽지 않음) · epic 컨텍스트 "가이드 문서 12개"(열린 DW-620이 소유 — 고치면 장부와 어긋나므로 의도적으로 두었다).

### 2026-08-02 — Review pass (3차 / 독립 후속 리뷰)

- intent_gap: 0
- bad_spec: 0
- patch: 16: (high 2, medium 5, low 9)
- defer: 7: (high 0, medium 5, low 2)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[high]` `[patch]` (adversarial/edge-case/verification-gap 3중 일치) 이 diff가 `run_phase_b.py` 독스트링에 "`--out`을 커밋된 기준선으로 주지 말 것" ⚠️를 새로 넣었는데 **주석은 실행되지 않는다** — 같은 커밋이 DW-622에서 CLAUDE.md B9 위반을 지적하며 동일 안티패턴을 심었다. edge-case 렌즈가 실측으로 증명: `capture()`는 루프 진입 **전에** 첫 `_flush`를 하므로 라이브 호출 0회로 죽는 실행조차 대상 파일을 이미 비운다(baseline 사본 47항목 → 1항목). 복구는 유료 47문항 재캡처뿐. `main()`에 `_PROTECTED_BASELINES` 검사 추가 + 거부/과차단대조 테스트 3건 추가 → **가드 제거 시 red, 복원 시 green 확인**.
  - `[high]` `[patch]` (verification-gap 뮤테이션 실증, adversarial·intent-alignment 독립 일치) AC3가 FR11 4개 강제지점 전부를 "실DB로 확인"이라 일반화했으나, 실제 Postgres에 붙는 건 `test_fr11_cover_images_real_db.py` **1지점뿐**이고 나머지 3지점은 생성 SQL 문자열 포함 검사다. 특히 `doc_rag_node`는 sql_guard를 안 거치고 RLS가 `using(true)`라 그 WHERE가 유일한 방어인데, `(status='on_sale' OR true)`로 무력화해도 CM-B 커맨드 전량이 스펙 기록 수치 그대로 초록임이 실증됐다(원복 확인). AC3를 검증 층별로 정직하게 분해하고, 구조적 해소는 DW-627로 등재.
  - `[medium]` `[patch]` (verification-gap 실증, adversarial 2건 일치) AC2가 `regression_block:false`를 "네 축 비하락"으로 읽었으나 자동 판정은 `result_mean` 한 축뿐이고 그조차 33/47 항목 평균이다. 실증: 가이드 인용 전멸(12/13→0/13)·CLARIFY 분기 전멸(54→47·9/9→2/9) 둘 다 `gate_pass:true`·`regression_block:false` 통과. AC2에 자동 판정의 실제 범위를 명시하고 세 축은 Manual checks 소관임을 밝힘(이번 실행에서 실제 대조해 일치 확인). 구조적 해소는 DW-626.
  - `[medium]` `[patch]` (edge-case) 회색지대 테스트의 SQL·HYBRID 두 파라미터가 `assert out["listings"]` 한 줄을 공유해, `conditional_edges`가 `"HYBRID" → sql`로 오배선돼도 6/6 초록이었다 — epic 컨텍스트가 경고한 "신규 라우트가 기존 분기에 조용히 흡수되는 회귀" 그 자체. `_patch_route`가 노드별로 주입하는 카드 id(`s1`/`h1`)를 단언하도록 보강 → **오배선 주입 시 2건 red, 복원 시 green 확인**.
  - `[medium]` `[patch]` (adversarial/edge-case) `GRAY_ALLOWED`↔큐리셋 `acceptable_paths` 일치가 세 곳의 산문 주장일 뿐 강제 검사가 없었다. 스펙 잔여 리스크는 "표면이 3행뿐이라 과설계(A2)"라 적었으나 큐리셋 로더는 `test_ab_scoring.py`에 이미 있어 3줄이면 된다 — 바로 다음 스토리 13.9가 라우팅을 바꾸며 `acceptable_paths`를 좁히면 이 사본만 옛 집합을 계속 정답으로 단언한다. 락스텝 테스트 추가 → **한 행에서 REJECT 제거 시 red 확인**.
  - `[medium]` `[patch]` (edge-case) `ai-demo-queries.md` ⑤ 멀티턴 절만 구어휘 A/B/C로 남아, 같은 문서가 `패밀리카로 무난한 거`의 기대 경로를 ②에선 CLARIFY, ⑤에선 B(매물)로 **두 값으로 갈랐다**(AC4가 ①②③④+SM3 표만 범위로 잡아 빠짐). 4분기 어휘로 옮기고, 재작성 전/후 질의가 다른 갈래로 가는 게 이 절의 요지임을 명시.
  - `[medium]` `[patch]` (edge-case) `epic-13-context.md` 기술결정이 "되묻기 상한도 **클라이언트가** 강제한다(서버가 무상태이므로)"라 적었는데 코드와 정면으로 어긋난다 — `graph.py`의 `_CLARIFY_TURN_CAP`(=3)이 서버에서 막고, DW-563의 해결 근거가 정확히 "클라이언트만 세는 상한은 상한이 아니다"였다. **13.9 스펙이 이 파일에서 만들어지므로** 서버 상한을 중복으로 오해해 걷어낼 자리였다.
  - `[low]` `[patch]` (edge-case) 같은 파일이 SM-G 범위를 게이트 정의에선 "신규 3분기", Cross-Story에선 "신규 4갈래"로 적어 판정 범위가 문서 안에서 갈렸다 — 3분기(HYBRID·CLARIFY·REJECT)로 통일하고 SQL이 SM-F 소관임을 명시.
  - `[low]` `[patch]` (edge-case, 삭제 검사) 재컴파일에서 청킹 임계값의 **"문서당"** 한정어가 빠져 총량 기준으로 읽히면 이미 초과라는 반대 결론이 나온다 — 복원.
  - `[low]` `[patch]` (edge-case/adversarial, 삭제 검사) "0건·거절 응답의 다양성은 문구 생성이 아니라 `narrowed_by`를 결정론 템플릿이 조립해 만든다" 제약이 Requirements에서 사라지고 문구 예시만 UX 절로 내려갔다 — 요구사항만 읽는 다음 스토리가 0건 안내에 LLM 문구를 넣어도 막을 근거가 없었다. Requirements로 복원(B8 "각주에 둔 제약도 본문으로 올린다").
  - `[low]` `[patch]` (adversarial) 같은 커밋이 `ai-demo-queries.md`엔 "`_GUARD_ANSWER`가 정본, 여기 건 사본" 표시를 붙이면서 `epic-13-context.md`엔 표시 없이 전문을 새로 복사했다 — 이 사본만 조용히 늙을 자리였다. 정본 포인터 추가.
  - `[low]` `[patch]` (edge-case) 이 스토리가 `run_phase_b.py`의 "44개" 사본을 고친 바로 그 이유로, 이웃한 `score_ab.py`·`test_ab_scoring.py` 독스트링의 쌍둥이 사본은 그대로였다 — 게다가 그 문장("커밋된 `g2-baseline.json`(44개 전량)은 구어휘 A/B/C다")은 **지금 거짓**이다(실측: 47항목·전부 신어휘). 두 독스트링을 정정하고 별칭표가 외부 raw 대비책임을 명시.
  - `[low]` `[patch]` (adversarial) `test_sm3_gray_zone_returns_listings_either_route`는 6개 케이스 중 2개가 "매물 없음"을 단언하므로 이름이 절반 반대였다 — `..._allowed_routes_are_not_dead_ends`로 개명(실패 로그 이름만 보고 오진할 자리).
  - `[low]` `[patch]` (adversarial) `conventions.md` §6의 세 번째 축(SECURITY DEFINER `get_seller_public_summary` — 정의자 함수 안에선 RLS가 안 걸려 가장 새기 쉽다)을 후속 리뷰가 실행해 green을 봤으면서 Verification 커맨드엔 안 넣어 재현 불가였다 — 커맨드 등재 후 재실행 **5 passed**.
  - `[low]` `[patch]` (adversarial/edge-case) `ai-demo-queries.md` ①②④ 12행 중 실측 라우트가 있는 건 4행뿐인데(나머지는 규칙 연역), ② 한 행에만 "실측 라우트가 있다"가 붙어 표 전체가 실측된 것처럼 읽혔다 — 표 앞에 행별 근거 강도를 밝히는 주석 추가. 남은 8행 실측은 DW-632.
  - `[low]` `[patch]` (edge-case) 파라미터가 dict 컴프리헨션으로 바뀌면서 허용 경로가 비면 pytest가 실패가 아니라 **SKIPPED + exit 0**을 낸다(실측) — 회색지대 게이트가 조용히 사라지는 경로라 수집 시점 assert로 막음(이 스토리 주제 그대로: 스킵은 통과가 아니다).
- 리뷰 레이어: adversarial 21건 · edge-case-hunter 12건(삭제 검사 2건 포함) · verification-gap 5건(전부 재실행·뮤테이션으로 실증) · intent-alignment 서술(축 A~D + 발산 D1~D5). 세 레이어가 독립적으로 같은 결론에 도달한 항목 3건(기준선 덮어쓰기 가드, CM-B 검증 층, G2 단일 축).
- **bad_spec으로 올리지 않은 이유**: AC2·AC3의 과장은 `<intent-contract>` 밖(Tasks & Acceptance)에 있어 형식상 bad_spec 후보다. 그러나 bad_spec 경로는 코드 revert + 재구현을 요구하는데, 이 스토리의 "코드"는 유료 라이브 검증 실행 결과이며 실행 자체는 정확했다 — 틀린 건 그 결과를 서술한 문장뿐이다. 되돌리면 47문항 유료 재캡처를 다시 태우면서 얻는 게 없다. 문장 정정 + 구조적 공백의 장부 등재로 처리했다.
- defer(신규 등재만, 기존 항목은 지시대로 일절 수정하지 않음): DW-626(medium, G2가 `result_mean` 한 축만 비교 — 13.4·13.6 전멸도 통과, 뮤테이션 실증) · DW-627(medium, `doc_rag_node` FR11 축에 실DB 검증 없음 — `OR true` 무력화가 전량 초록, 뮤테이션 실증) · DW-628(medium, `test_readonly.py`를 실행하는 CI 잡이 없음) · DW-629(medium, **DW-622가 적어 둔 fallback 해법을 그대로 구현하면 통합 테스트가 운영 DB에 쓴다** — 채택 금지 경고) · DW-630(medium, 라이브 스모크 전량 스킵도 exit 0 → SM-F/SM-G 거짓 초록 가능) · DW-631(low, 캡처 아티팩트에 시각·커밋 해시 없음) · DW-632(low, ①②④ 12행 중 8행이 미관측 기대값).
- reject 9건(요지, 전부 low): DW-576 `status:` 문법 위반·DW-556/564/565 재개봉 지점 미지정·§6 `hybrid_rag_node` 미등록·에픽 게이트 "회귀" 문구·"가이드 문서 12개"·`GRAY_AB`/`DEMO_QUERIES` 죽은 상수 — **여섯 건 모두 이미 열린 장부 항목(DW-623·624·619·621·620·573)이 소유**하며, 이번 실행의 지시가 기존 항목 수정을 금지하므로 코드만 고치면 장부와 어긋난다 · 리포트 JSON `detail` 키 충돌(baseline per-item은 `g2-baseline.json`·`g2-baseline-report.json`에 그대로 남아 있어 소실 아님) · `verdict`/`final_adopt`(이미 잔여 리스크로 공개, `score_ab.py`는 Never절 범위) · "장부가 순증한 채 done"(관찰이지 결함 아님).

## Design Notes

**G2 기준선의 정체**: 13.1이 심으려던 baseline은 미룸을 반복하다 DW-609가 2026-08-02에 **현재(post-13.6) 코드**로 47문항을 재캡처하며 확정됐다 — 즉 "Phase B baseline"과 "13.8이 확인할 현재 상태"가 같은 자리에서 만난다. 별도의 "구 버전 vs 신 버전" 비교가 아니라, 어제 캡처와 오늘 재캡처의 재현성(reproducibility) 확인이 G2의 실질이다.

**DW-564/565/556 종결 근거**: 세 항목 모두 "Story 13.8 스펙 작성 시" 결정하라는 trigger가 있었다. `score_ab.py`의 `lexicographic_winner()`(4단계 사전식 랭킹, flaky/비용 tier 포함)와 `--model` 라벨링은 **경쟁 모델 후보를 채택 판단**할 때 쓰는 기능인데, `epics-increment-2026-07-12.md`의 13.8 AC 원문(967~1130줄)엔 모델 비교가 전혀 없다 — SM-F/SM-G/G2/CM-B 네 게이트뿐이다. 세 항목은 "13.8=모델 A/B 채택"이라는, 실제 AC와 다른 전제로 defer됐다. 이 스펙은 그 전제를 정정해 세 항목을 범위 밖으로 닫는다: G2는 `regression_block`(단일 불리언, `candidate.result_mean < baseline.result_mean`)만 쓰고 `lexicographic_winner`의 랭킹·tier는 읽지 않는다. 단, `score_ab.py` 2-file 모드는 이 스펙이 손대지 않으므로 리포트 JSON엔 여전히 `verdict`(승자)·`final_adopt` 필드가 남는다 — 같은 코드·같은 큐리셋을 비교하면 실질 차이가 없는 지연시간(latency) 200ms 안팎으로 "승자"가 갈리는데, 이건 노이즈이지 채택 판단이 아니다. 코드(score_ab.py)는 Never절에 따라 건드리지 않고, 이 사실만 Auto Run Result 잔여 리스크로 남긴다.

**SM-F "질적형 유지"의 정확한 의미**: 13.4 이전 pathB는 매물 카드를 반환했고 지금은 CLARIFY 되묻기를 반환한다 — 겉보기 출력이 달라졌다. 그런데도 "유지"로 보는 근거는 2026-07-31 사용자 확정(deferred-work.md DW-604 resolution 인용): "이번 증분 RAG 고도화의 목적은 지식형 질문에 답하는 게 아니다... 애매한 질문은 되묻기가 정답이다." 즉 pathB의 산출물 형태 변경은 13.4가 의도적으로 내린 제품 결정이고, SM-F가 지키려는 것은 "그 질의가 에러·빈손·엉뚱한 응답 없이 정상 처리된다"이지 "13.4 이전과 바이트 단위로 같다"가 아니다.

## Verification

**Commands:**
- `cd api && set -a && source .env && set +a && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_live_smoke.py -v` -- expected: `test_live_smoke_pathA/pathB/pathC/hybrid` + `clarify_cap_forces_results` 5건 PASSED. `langsmith_tracing`은 PASSED **또는** SKIPPED 둘 다 정상이다(LangSmith env가 raw 프로세스 환경변수로 노출되지 않으면 자연 스킵 — 13-7이 정의한 동작이고 SM-F/SM-G 판정과 무관). AC1과 문구를 맞춘 것 — 이전엔 "스킵 없음"이라 적혀 있어 정상 스킵이 게이트 실패처럼 보였다.
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python scripts/run_phase_b.py --out docs/g2-exit-gate-2026-08-02.json` -- expected: 47/47 캡처, 0 errored
- `cd api && .venv/bin/python scripts/score_ab.py --raw docs/g2-baseline.json docs/g2-exit-gate-2026-08-02.json --out docs/g2-exit-gate-report.json` -- expected: 리포트의 `gate_pass:true`(양쪽)·`regression_block:false`·`coverage.is_partial:false`(양쪽)
- `cd api && DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/test_sql_guard.py tests/test_readonly.py tests/test_hybrid_rag_node.py tests/test_doc_rag_node.py tests/test_listing_cards.py -q -rs` -- expected: **149 passed, 0 skipped**. ⚠️ `DATABASE_URL` 없이 돌리면 `test_readonly.py`의 2건(ai_readonly 롤 격리 = CM-B의 세 안전장치 중 하나)이 조용히 스킵돼 "147 passed, 2 skipped"가 되는데, 그건 통과가 아니라 **검증 안 함**이다. `-rs`로 스킵 사유를 항상 눈에 보이게 한다.
- `cd api && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/integration/test_fr11_cover_images_real_db.py -v -rs` -- expected: **1 passed, 0 skipped**(실DB 기준 판매완료 이미지 비노출 확인). ⚠️ 이 파일의 스킵 가드가 보는 변수는 `DATABASE_URL`이 아니라 **`TEST_DATABASE_URL`**이다(CI의 `api-db` 잡이 주는 이름). 잘못된 변수로 돌리면 `1 skipped`가 나오는데 종료코드가 0이라 초록으로 오독된다.
- `cd api && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -m pytest tests/integration/test_seller_summary_real_db.py -v -rs` -- expected: **5 passed**. `conventions.md` §6의 **세 번째 축(SECURITY DEFINER 함수 `get_seller_public_summary`)** — 정의자 함수 안에선 RLS가 안 걸려 함수 본문 인라인 조건이 유일한 강제 지점이라 §6의 세 축 중 가장 새기 쉽다. 후속 리뷰에서 실행해 green을 확인했으면서 커맨드 목록엔 안 넣어 재현 불가였던 것을 3차 리뷰에서 등재(DW-625).
- `cd api && .venv/bin/python -m pytest tests/ -q` -- expected: 기존과 동일 통과(문서·독스트링 정정 외 앱 코드 변경 0 회귀 없음 확인). ⚠️ 이 커맨드의 초록에는 **85건 안팎의 skip**(라이브·실DB 통합 전량)이 묻힌다 — 위 개별 커맨드들이 그 skip을 걷어내는 자리다.

**Manual checks (if no CLI):**
- `docs/g2-exit-gate-report.json`의 `routing_correct`·`result_mean`·`doc_hit_n/total`·`clarify_ok_n/total`을 `docs/g2-baseline-report.json`(54/57·0.8936·12/13·9/9) 수치와 나란히 대조해 하락이 없는지 눈으로 확인.

## Auto Run Result

**Status:** done

**Summary:** Epic 13(13.1~13.7)이 만든 4분기 라우팅·하이브리드 검색·가이드 질의확장·LangSmith 계측을 실측으로 검증했다. 새 기능은 추가하지 않았다 — 이미 있는 도구(G2 회귀 하니스, 라이브 스모크, CM-B 저장 테스트)를 실제로 돌려 SM-F·SM-G·G2·CM-B 네 게이트를 전부 통과 확인하고, 그 과정에서 드러난 문서·독스트링 노후화와 테스트 공백을 고쳤다.

**Files changed:**
- `_bmad-output/implementation-artifacts/spec-13-8-rag-exit-gate-검증-sm-f-sm-g-g2-cm-b.md` -- 이 스토리의 스펙(신규).
- `api/docs/g2-exit-gate-2026-08-02.json`, `api/docs/g2-exit-gate-report.json` -- G2 게이트 라이브 재캡처(47/47)·2-file 채점 리포트(신규 증거 아티팩트).
- `api/docs/ai-demo-queries.md` -- ①②③④ 표·서두 설명을 4분기 어휘(SQL/HYBRID/CLARIFY/REJECT)로 정정, 실제 분류와 어긋나던 예시 질의 교체(②·③), 리뷰에서 드러난 SM3 매핑 행의 REJECT 모순도 정정.
- `api/tests/demo_queries.py` -- 위 문서 변경과 락스텝(자기 선언 drift-금지 계약)으로 예시 질의·라벨 동기화.
- `api/tests/test_demo_acceptance.py` -- 리뷰 패치: `test_sm3_gray_zone_returns_listings_either_route`에 REJECT 분기 추가(문서가 정답으로 규정한 경로를 이전엔 테스트가 검증하지 않았음).
- `api/scripts/run_phase_b.py` -- 독스트링의 낡은 수치·날짜(44개/07-30)를 47개/08-02로 정정, `--subset` 예시 id를 신어휘로 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-556·564·565를 "13.8 범위 밖(모델 비교 아님)"으로 종결(DW-564는 리뷰 검증 결과로 근거 보강), DW-576을 부분 종결(질의 재분류분 반영, 잔여 범위 축소), DW-619·DW-620 신규 등재(리뷰에서 발견한 선재 문서 드리프트).
- `_bmad-output/implementation-artifacts/epic-13-context.md` -- step-01 라우팅 단계에서 재컴파일. **⚠️ 2026-08-02 후속 리뷰 정정:** 최초 기록은 "이 스토리의 작업물이 아니라 워크플로 캐시 최신화"였으나 사실이 아니다 — `git log`가 이 변경을 이 스토리의 커밋(69cb941)에 귀속하며, 재컴파일이 13.7이 심어 둔 게이트 정의·Story 13.9 요구사항·기술결정 등을 삭제했다. 후속 리뷰에서 전부 복원했다(상세는 Review Triage Log 2번째 패스).

_후속 리뷰 패스(2026-08-02)가 추가로 손댄 파일은 위 목록과 같다 — 새 파일은 없고, `epic-13-context.md`(삭제된 요구사항 복원) · `demo_queries.py`/`test_demo_acceptance.py`(회색지대 교차곱 제거) · `ai-demo-queries.md`(자기모순 3건) · `run_phase_b.py`(기준선 덮어쓰기 유도 예시) · 이 스펙(Verification 커맨드 2건 정정)이다. `_bmad-output/implementation-artifacts/sprint-status.yaml`(13-8 → done)도 이 커밋에 포함된다._

_3차 리뷰 패스(2026-08-02)가 추가로 손댄 파일: `api/scripts/run_phase_b.py`(기준선 덮어쓰기 가드 — 주석을 실행되는 검사로) · `api/tests/test_run_phase_b.py`(그 가드의 red 확인 테스트 3건 신규) · `api/tests/test_demo_acceptance.py`(SQL/HYBRID 노드 구분 단언 · 큐리셋 락스텝 검사 · 빈 파라미터셋 가드 · 개명) · `api/scripts/score_ab.py`·`api/tests/test_ab_scoring.py`(거짓이 된 "44개·구어휘" 독스트링 사본 정정) · `api/docs/ai-demo-queries.md`(⑤절 구어휘 잔존 · 행별 근거 강도 주석) · `epic-13-context.md`(코드와 어긋난 되묻기 상한 주체 · SM-G 범위 불일치 · 삭제된 제약 2건 복원 · `_GUARD_ANSWER` 사본 표시) · 이 스펙(AC2·AC3 과장 정정, Verification에 SECURITY DEFINER 축 등재) · `deferred-work.md`(DW-626~632 신규 7건). **앱 코드(`api/app/**`)는 이 패스에서도 한 줄도 바뀌지 않았다** — 뮤테이션 2건은 검증용이었고 전부 원복 확인했다._

**Review findings breakdown (4 layers: adversarial·edge-case-hunter·verification-gap·intent-alignment, 3 passes):**
- intent_gap: 0, bad_spec: 0
- patch: 11 (medium 5, low 6) — 전부 적용·재검증 완료(상세는 Review Triage Log)
- defer: 2 (medium 1 — DW-619, low 1 — DW-620) — 둘 다 13.8 이전부터 있던 선재 드리프트
- reject: 0
- verification-gap 레이어는 findings 0건 — 이 diff가 만든 어떤 검증 갭도 찾지 못했고, G2 재현성(per-item diff)까지 직접 실측해 다른 레이어의 우려를 반증했다.

**Follow-up review recommendation:** true.
- 1차 패스: patch medium 5·low 6 → 3×5+1×6=21 ≥ 5 → true.
- 2차 패스(2026-08-02): patch **high 3**(CM-B 실DB 2축 미실행, epic 컨텍스트 요구사항 삭제) → high가 하나라도 있으면 규칙상 즉시 true. 참고 점수 3×4+1×6=18.
- 3차 패스(2026-08-02): patch **high 2**(기준선 덮어쓰기 가드가 주석뿐, CM-B 4지점 중 3지점이 실DB 아님) → true. 참고 점수 3×5+1×9=24.
- **세 패스 연속 true인 것이 이 스토리의 가장 중요한 신호다.** 각 패스가 이전 패스의 "확인했다"를 한 겹씩 벗겨냈다 — 1차는 문서 모순을, 2차는 두 게이트가 실제로는 스킵이었음을, 3차는 통과한 그 검사들이 **무엇을 못 잡는지**(기준선 파괴·필터 무력화·세 축 미비교)를 드러냈다. 공통점은 전부 **diff를 읽어서가 아니라 커맨드를 실제로 돌리거나 코드를 일부러 깨서** 나왔다는 것이다(B4). 4차 패스를 또 도는 것보다, 이번에 등재한 DW-626·627·630(전부 "검사가 있는데 못 잡는다"류)을 13.9에서 실제 검사로 바꾸는 편이 남은 위험을 더 줄인다.

**Verification performed:**
- 최초 패스에서 오케스트레이터가 재실행해 확인한 것: `pytest tests/ -q` → 400 passed, 85 skipped, 0 failed. 라이브 `RUN_LIVE_SMOKE=1 ... pytest tests/test_live_smoke.py -v` → **6/6 PASSED**(pathA/pathB/pathC/hybrid/clarify_cap/langsmith_tracing) — SM-F·SM-G 직접 재현. `docs/g2-exit-gate-report.json`을 직접 읽어 `gate_pass:true`(양쪽)·`is_partial:false`(양쪽)·`scored_n:47/47`·`regression_block:false`·수치(routing 54/57·result_mean 0.8936…·doc_hit 12/13·clarify_ok 9/9)가 baseline과 정확히 일치함을 확인.
- **⚠️ 2026-08-02 후속 리뷰 정정 — 최초 패스의 CM-B 보고 2건은 사실이 아니었다.** "CM-B 유닛 5파일 → 147 passed, 2 skipped"의 그 2건이 곧 `test_readonly.py`(ai_readonly 롤 격리)였고, "`test_fr11_cover_images_real_db.py`(실DB) → PASSED"는 실제로는 `1 skipped`였다(스펙에 적힌 커맨드가 `TEST_DATABASE_URL` 대신 `DATABASE_URL`을 넘겨 스킵 가드에 걸렸고, pytest 종료코드가 0이라 초록으로 읽혔다). 즉 **CM-B 세 안전장치 중 둘이 한 번도 안 돌아간 채 게이트가 통과로 닫혀 있었다** — 이 스펙이 B4를 인용하며 경계한 "존재 확인 ≠ 작동 확인"이 이 스토리 자신의 결과 기록에서 일어났다.
- **후속 리뷰에서 올바른 환경변수로 실제 실행해 확인한 것(게이트는 실제로 선다):** `TEST_DATABASE_URL=... pytest tests/integration/test_fr11_cover_images_real_db.py -rs` → **1 passed, 0 skipped**. `DATABASE_URL=... pytest <CM-B 유닛 5파일> -rs` → **149 passed, 0 skipped**(ai_readonly 2건 포함). 추가로 `conventions.md` §6의 세 번째 축(SECURITY DEFINER 함수 — 정의자 함수 안에선 RLS가 안 걸려 인라인 조건이 유일한 강제 지점)이 로스터에서 빠져 있던 것을 발견해 `TEST_DATABASE_URL=... pytest tests/integration/test_seller_summary_real_db.py` → **5 passed**로 함께 확인(DW-625).
- 후속 리뷰 패치 후 전체 재검증: `pytest tests/ -q` → **394 passed, 85 skipped, 0 failed**(회색지대 파라미터를 교차곱 12개에서 문서와 1:1인 6개로 좁혀 -6). `pytest tests/test_demo_acceptance.py -k gray_zone -v` → 6 passed이며 파라미터 목록이 H6/H7=SQL·HYBRID, CL7=CLARIFY·REJECT로 문서 표 ③과 정확히 일치함을 눈으로 확인. 앱 코드(`api/app/**`)는 이 패스에서 한 줄도 바뀌지 않았으므로 라이브 스모크·G2는 재실행하지 않았다(유료 호출 절약, 최초 패스 결과가 그대로 유효).
- 구현 서브에이전트가 최초 실행한 것(위와 별개 실행, 상세는 최초 구현 보고): 동일 항목 전부 최초 1회씩 그린 확인 + `git diff --stat`로 무관 변경 없음 확인.
- 매트릭스 감사(Matrix Test Audit): I/O 매트릭스 4행 전부(+패치로 추가된 1행 포함 5행) 실행·통과한 테스트로 커버 확인 — "G2 부분 실패" 행은 `test_ab_scoring.py`의 `is_partial`/`errored_n` 결정론 단위테스트(전체 스위트에 포함, 통과)로 커버.
- **3차 리뷰에서 실제로 돌린 것:** CM-B 유닛 5파일 `DATABASE_URL=… -rs` → **149 passed, 0 skipped** · FR11 실DB `TEST_DATABASE_URL=…` → **1 passed** · SECURITY DEFINER 축 `test_seller_summary_real_db.py` → **5 passed** · 전체 `pytest tests/ -q` → **398 passed, 85 skipped, 0 failed**(신규 검사 4건만큼 394에서 증가) · 회색지대 `-k gray` → **7 passed**(허용경로 6 + 락스텝 1). G2는 Manual checks를 실제로 수행 — 두 요약이 `routing_correct 54`·`result_mean 0.8936…`·`result_n 33/47`·`doc_hit 12/13`·`clarify_ok 9/9`·`gate_pass:true`·`coverage 47/47 errored 0`으로 동일하고 `regression_block:false`임을 직접 읽어 확인했다(AC2가 이제 명시하듯 세 축은 이 대조로만 확인된다).
- **새로 만든 검사는 일부러 깨서 red를 확인했다(B4 "만들었다가 아니라 잡는다가 완료"):** ① 기준선 가드 → `_PROTECTED_BASELINES` 검사를 무력화하니 2건 red, 복원하니 green. ② SQL/HYBRID 노드 구분 단언 → `conditional_edges`를 `"HYBRID": "sql"`로 오배선하니 HYBRID 2건 red, 복원하니 green. ③ 큐리셋 락스텝 → `GRAY_ALLOWED`에서 REJECT 한 개를 빼니 red, 복원하니 green. 뮤테이션은 전부 원복했고 `git diff`로 앱 코드 잔여 변경 0건을 확인했다.
- **⚠️ 3차 리뷰 중 커밋된 기준선이 실제로 파괴됐다(그리고 복원했다).** 리뷰 레이어가 "`--out`에 기준선 경로를 주면 파괴된다"를 실증하는 과정에서 `api/docs/g2-baseline.json`(47항목)과 `api/docs/g2-baseline-partial.json`(3항목)이 **둘 다 0항목으로 잘렸다** — 커밋 직전 `git status`에서 발견해 `git restore`로 HEAD 상태(47·3항목)로 되돌렸고, 두 파일은 이 스토리의 변경 대상이 아니므로 커밋에 포함하지 않았다. 즉 이 위험은 가설이 아니라 **이번 세션에서 실제로 일어났고**, 마침 커밋되지 않은 상태였기 때문에 되돌릴 수 있었다(커밋 이후였다면 복구 수단은 유료 47문항 재캡처뿐이었다). 이번에 넣은 `_PROTECTED_BASELINES` 가드가 정확히 이 경로를 막는다.
- **그 검사들이 여전히 못 보는 것(추측 아니라 실측):** 회색지대 테스트는 `_patch_route`로 경로를 강제 주입하므로 **실제 라우터의 분류**는 여전히 안 본다(DW-576). 락스텝 검사는 `GRAY_ALLOWED`↔큐리셋 두 곳만 대조하고 `ai-demo-queries.md` 표 ③은 사람이 맞춰야 한다(문서는 기계가 읽지 않는다). 기준선 가드는 `--out` 경로만 보므로 파일을 손으로 덮어쓰는 것은 못 막는다.

**Anything not completed:** 스펙의 AC·I/O 매트릭스 전 행이 라이브 또는 결정론 실행으로 확인됐고 전부 green이다. 다만 **AC2·AC3가 원래 주장하던 범위 그대로는 완료되지 않았고, 3차 리뷰에서 AC 문장을 실제 증명 범위로 좁혔다** — G2의 세 축(routing_correct·doc_hit_n·clarify_ok_n)은 자동 게이트가 아니라 사람의 리포트 대조로 확인되고(DW-626), CM-B 4지점 중 3지점은 실DB가 아니라 생성 SQL 문자열 검사로 확인된다(DW-627). 둘 다 이번 실행에서는 실제로 확인해 green이지만, **다음 재실행에 자동으로 상속되지 않는다.** 이 두 항목을 실행되는 검사로 바꾸는 일은 13.9(어차피 기준선을 재캡처하는 자리)로 넘겼다.

**Residual risks:**
- `api/docs/g2-exit-gate-report.json`의 `verdict`/`final_adopt` 필드는 `score_ab.py`(이 스토리가 손대지 않기로 결정한 도구)가 2-file 모드에서 항상 계산해 남기는 것으로, 동일 모델의 지연시간(latency) 노이즈만으로 "승자"를 표기한다 — 이 스토리의 실제 게이트 판정은 `regression_block`만 썼고 이 필드는 읽지 않았지만, 스펙 맥락 없이 이 JSON만 보는 미래 독자는 실제 모델 채택 결과로 오독할 수 있다. 코드 수정은 Never절로 범위 밖이라 하지 않았다 — score_ab.py를 다음에 손댈 때(모델 비교가 실제로 생기거나) 억제 옵션 도입을 함께 검토한다.
- DW-576(회색지대 route가 여전히 `_patch_route`로 강제 주입돼 SM3가 실제 라우팅을 보장하지 않는 구조적 문제)은 이번에 질의 재분류분만 부분 해소됐고, 핵심 결함은 열려 있다(위 표 참조) — 13.8 범위가 아니라고 판단해 구조 변경은 하지 않았다.
- DW-619(conventions.md §6에 hybrid_rag_node 미등록)·DW-620(가이드 문서 12개 vs 실제 10개)는 13.8 이전부터 있던 문서 드리프트로, 이번 리뷰에서 발견해 장부에 신규 등재했다 — 코드 동작 자체는 정상(라이브로 확인)이라 안전 문제는 아니다.
- 이 세션에서 Gemini/LangSmith 실호출이 다시 발생했다(라이브 스모크 재실행 1회 — 6건, G2 47문항 캡처는 구현 단계에서 1회만 — 무료/유료 티어 한도 내, 과금 자체는 사용자가 이미 인지). **후속 리뷰 패스에서는 유료 호출 0건**(앱 코드 무변경이라 라이브 재실행 불필요).
- **(후속 리뷰) G2가 증명하는 것의 범위** — 비교 대상 baseline이 이미 13.6까지 들어간 코드로 뜬 것이라, G2가 실측한 건 "13.1~13.7이 회귀를 안 만들었다"가 아니라 "같은 코드가 같은 결과를 재현한다"다(두 캡처가 `latency_ms` 빼고 바이트 동일, 그 사이 `api/app` 커밋 0건). 에픽 레벨 게이트 문구는 여전히 "회귀"라 이 간극이 남는다 — DW-621로 등재했고, 13.9가 어차피 기준선을 재캡처하는 자리에서 결정한다.
- **(후속 리뷰) 회색지대 허용 경로 표는 여전히 사본이다** — `demo_queries.GRAY_ALLOWED`는 `ai-demo-queries.md` 표 ③과 큐리셋 `acceptable_paths`를 손으로 옮긴 것이고, 셋이 어긋나도 잡아 주는 검사는 없다. 지금은 세 곳이 일치함을 실측 확인했지만(H6/H7=SQL·HYBRID, CL7=CLARIFY·REJECT), 문서를 고치면 사람이 같이 고쳐야 한다. 자동 대조를 넣지 않은 건 표면이 3행뿐이라 과설계라 판단한 것(A2) — 행이 늘면 재검토할 자리다.
- **(후속 리뷰) 라우팅 자체는 이 결정론 게이트가 보지 못한다** — 회색지대 테스트는 `_patch_route`로 경로를 강제 주입하므로 "실제 라우터가 이 질의를 어디로 보내는가"는 여전히 미검증이다(열린 DW-576). 이번 패치는 "허용 밖 경로까지 합격으로 단언하던 것"을 없앤 것이지 그 구조적 공백을 메운 게 아니다. 실제 라우팅은 라이브 스모크와 G2 재캡처가 본다.
- **(3차 리뷰) 통과한 게이트가 무엇을 못 잡는지가 이제 측정돼 있다 — 그게 남은 위험의 실체다.** 세 가지를 뮤테이션으로 실증했다: (a) G2는 `result_mean` 한 축만 자동 비교하므로 13.6 가이드 인용 전멸·13.4 CLARIFY 분기 전멸이 **둘 다 통과**한다(DW-626), (b) `doc_rag_node`의 FR11 필터를 `OR true`로 무력화해도 CM-B 커맨드 전량이 초록이다(DW-627), (c) 라이브 스모크는 전량 스킵돼도 exit 0이다(DW-630). 이번 실행은 세 축 모두 사람이 직접 확인해 green이지만, **확인의 형태가 사람이면 다음 실행에 상속되지 않는다**(CLAUDE.md B9). 13.9가 기준선을 재캡처하는 자리가 이 셋을 실행되는 검사로 바꿀 지점이다.
- **(3차 리뷰) `test_readonly.py`는 어느 CI 잡에서도 돌지 않는다**(DW-628) — `api` 잡은 운영 DB 접속 위험 때문에 `DATABASE_URL`을 일부러 비우고, `api-db` 잡은 `tests/integration`만 대상으로 한다. 두 결정 각각은 옳은데 교집합에서 ai_readonly 롤 격리 축이 통째로 빠졌다. 이번 149 passed는 손으로 친 로컬 실행이다.
- **(3차 리뷰) 장부에 적힌 해법 하나가 위험하다**(DW-629) — DW-622가 제안한 "환경변수 fallback"을 그대로 구현하면, 쓰기를 수행하는 통합 테스트가 운영 Supabase를 가리키는 `DATABASE_URL`로 떨어진다. 기존 항목 수정이 금지돼 있어 신규 항목으로 경고만 남겼다 — **DW-622를 처리하는 사람은 DW-629를 함께 읽어야 한다.**
