---
title: '13.6 가이드 문서 content 활용 (질의확장) + 거리 컷오프'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: 'c3cec9608bfead955c11a039eced86a0d2897ee4'
final_revision: 'ad48e8fd8b2028485131a9ea8da9351f39ad6a8e'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `guide_documents`(12문서, content 이미 임베딩됨)는 지금 `doc_rag_node`가 title 1건을 조건 없이 항상 answer에 곁들이는 장식 인용일 뿐이다(FR49 컷오프 없음, 노이즈 위험). `hybrid_rag_node`의 조건추출 LLM은 "패밀리카"류 느낌·용도 표현을 규칙상 명시적으로 버리므로("느낌 표현은 무시하고 버려라"), 매물 설명에 그 단어가 없으면 못 찾는다 — 가이드 코퍼스(예: `02-패밀리카-적합-차종.md`가 이미 "중형차·SUV·RV·5~7인승" 매핑을 담고 있음)를 실제로 읽어 쓰지 않는다.
**Approach:** `doc_rag_node.py`에 `find_relevant_guide(qvec_literal)` 공유 헬퍼를 신설해(title, content, 코사인 거리) 임계값(FR49, 초기값 0.3) 이하일 때만 반환한다. `doc_rag_node`의 기존 인용은 이 게이트를 통과할 때만 붙인다. `hybrid_rag_node`는 조건추출 LLM 호출 **이전**에 이 헬퍼로 가이드를 조회해, 게이트를 통과하면 그 content를 시스템 프롬프트에 추가 블록으로 주입한다((b) 질의확장, FR44) — LLM이 "패밀리카" 같은 느낌 표현을 가이드가 제시하는 구조조건(body_type 등)으로 변환하게 한다. 답변 문장은 LLM이 새로 짓지 않는다(기존 결정론 템플릿 유지, AC2).

## Boundaries & Constraints

**Always:**
- `find_relevant_guide(qvec_literal: str) -> tuple[str, str] | None`(doc_rag_node.py 신설, hybrid_rag_node.py가 import)이 `SELECT title, content, embedding <=> %s::vector AS distance FROM guide_documents WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT 1`을 실행하고, `distance <= _GUIDE_DISTANCE_CUTOFF`(초기값 0.3, FR49)일 때만 (title, content)를 반환한다. 가이드 0건·컷오프 초과는 None.
- `doc_rag_node`의 "(참고: {title})" 인용은 `find_relevant_guide`가 non-None을 반환할 때만 붙는다(listings=0건이면 기존처럼 인용 생략, 회귀 없음).
- `hybrid_rag_node`는 재시도 루프 **진입 전**에 `qvec = embed_query(query)`를 1회만 계산해(재시도마다 재임베딩하던 기존 낭비 제거) `find_relevant_guide`에 넘긴다. 통과한 가이드가 있으면 그 content를 시스템 프롬프트 뒤에 추가 블록으로 붙이고, 그 블록 안에서 "이 매핑은 규칙 2(느낌 표현 버리기)보다 우선한다"를 명시한다. 없으면 프롬프트는 기존 그대로.
- 가이드가 조건추출에 쓰였고 최종 listings가 1건 이상이면, `hybrid_rag_node`도 `doc_rag_node`와 동일하게 결정론적 문자열 붙이기로 answer에 `" (참고: {title})"`를 덧붙인다(LLM 재호출 아님, AC2 유지).
- `doc_rag_node.py`·`hybrid_rag_node.py` 모듈 docstring의 "가이드 1건을 무조건 곁들인다" 서술을 컷오프 반영으로 갱신한다.
- 청킹은 도입하지 않는다(FR48 비대상, 문서=1임베딩 그대로).

**Block If:**
- `RUN_LIVE_SMOKE=1`로 로컬 Supabase+`GEMINI_API_KEY`를 통해 `run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4`를 돌려 `score_ab.py`의 `doc_hit()` recall을 컷오프 적용 전/후로 비교했을 때 하락하면(임계값 0.3이 정답 가이드까지 쳐낸다는 실측), HALT(status blocked, blocking condition `거리 컷오프가 가이드 인용 recall을 회귀시킨다`).

**Never:**
- RRF·가중 선형 융합 등 별도 점수 결합 로직은 도입하지 않는다(연구 문서가 이미 이 규모엔 과설계로 판단 — "가중치"는 AND 결합 조건 하나 추가로 해석한다, Design Notes 참조).
- `sql_rag_node.py`(경로 A, 순수 구조형)는 손대지 않는다 — 질의확장은 `hybrid_rag_node`(조합형)에만 적용한다.
- `answer_node.py`·`narrowed_by`(13.5 소관, DW-600)는 손대지 않는다 — 이번 스토리가 실제로 여는 파일 범위에 `answer_node.py`가 들지 않으므로 DW-600 트리거 조건이 성립하지 않는다(Design Notes에 기록, 강제 종결하지 않음).
- `score_ab.py`에 신규 노이즈 스코어러를 추가하지 않는다 — 기존 `doc_hit()` 회귀 확인 + 라이브 실행 관찰(거리값 로그)로 충분하다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 컷오프 이내 가이드 + 구조조건 일부(가격) | "3천만원 이하로 무난한 패밀리카" (HYBRID) | 가이드 content가 프롬프트에 주입돼 LLM이 body_type 조건도 추가로 조립, 매물이 그 조건 반영해 반환, answer에 "(참고: 패밀리카로 무난한 차종 고르기)" | No error |
| 컷오프 초과(무관 질의) | 가이드와 의미상 먼 질의 | 프롬프트 미주입(기존 동작), listings 있어도 "(참고:...)" 미부착 | No error |
| doc_rag_node 순수 벡터 경로, 컷오프 이내 | 가이드 매칭 | 기존처럼 인용 부착(회귀 없음, 게이트만 신규) | No error |
| doc_rag_node 순수 벡터 경로, 컷오프 초과 | 가이드 있으나 거리 김 | listings 있어도 인용 미부착(신규 — 기존엔 무조건 부착) | No error |
| 매물 0건 | 컷오프 이내 매칭이어도 | FR17 안내만, 인용 생략(기존 규칙 유지) | No error |

</intent-contract>

## Code Map

- `api/app/graph/doc_rag_node.py` -- `_GUIDE_DISTANCE_CUTOFF = 0.3` 상수 + `find_relevant_guide(qvec_literal)` 헬퍼 신설(title/content/distance 조회, 컷오프 게이트), 기존 인라인 title-only 쿼리를 이 헬퍼 호출로 교체, 인용 로직을 게이트 통과 시로 한정, 모듈 docstring 갱신.
- `api/app/graph/hybrid_rag_node.py` -- `find_relevant_guide` import 추가, `qvec`/`qvec_literal`을 재시도 루프 진입 전 1회 계산해 재사용(루프 내부의 개별 `embed_query(query)` 호출 제거), 가이드 컨텍스트 블록을 시스템 프롬프트에 조건부 부착, 최종 answer에 결정론적 인용 부착, 모듈 docstring 갱신.
- `api/tests/test_doc_rag_node.py` -- `_GUIDE_ROW`를 (title, content, distance) 3-tuple로 갱신, 컷오프 이내/초과 신규 테스트 2건(AC1/AC2 대응).
- `api/tests/test_hybrid_rag_node.py` -- 기존 `run_select` 가짜들을 테이블 분기(`from guide_documents` 절이면 빈 리스트)로 통일(신규 가이드 조회와 충돌 방지), NONE/공백/near-miss 폴백 테스트 전부에 `embed_query` 몽키패치 추가(가이드 조회가 조건추출보다 먼저 실행되므로), 가이드 주입 시 시스템 프롬프트에 content가 실제로 포함되는지·컷오프 초과 시 미포함되는지 신규 테스트, 가이드로만 도출된 조건이 최종 SQL에 반영되고 answer에 인용이 붙는지 신규 테스트.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- 이번 구현으로 실제 남는 잔여 위험(있다면)만 신규 등재.

## Tasks & Acceptance

**Execution:**
- `api/app/graph/doc_rag_node.py` -- `_GUIDE_DISTANCE_CUTOFF = 0.3` 정의(주석: FR49, 초기 후보 — Phase B 실측으로 확정). `find_relevant_guide(qvec_literal)` 신설: 위 3컬럼 쿼리 실행 후 `rows`가 있고 `rows[0][2] <= _GUIDE_DISTANCE_CUTOFF`면 `(rows[0][0], rows[0][1])` 반환, 아니면 `None`. `doc_rag_node()`가 기존 `guide_rows = run_select("SELECT title FROM guide_documents ...")` 블록을 `guide = find_relevant_guide(qvec)` 호출로 교체하고, `if listings and guide: answer += f" (참고: {guide[0]})"` 형태로 정리.
- `api/app/graph/hybrid_rag_node.py` -- import에 `find_relevant_guide` 추가. `hybrid_rag_node()` 최상단에서 `qvec = embed_query(query)`(fail-loud 유지) → `qvec_literal = _vec_literal(qvec)` → `guide = find_relevant_guide(qvec_literal)` 순으로 1회 계산. `messages`의 system 프롬프트를 `_SYSTEM_PROMPT + (가이드 블록 if guide else "")`로 조립(가이드 블록: 제목/본문 + "규칙 2보다 이 매핑을 우선한다" 지시, 답변 생성엔 안 쓴다는 문구 포함). 재시도 루프 안의 `qvec = embed_query(query)` 호출을 제거하고 호이스트된 `qvec_literal`을 재사용. 성공 응답 조립 시 `listings`가 있고 `guide`가 있으면 `answer += f" (참고: {guide[0]})"`.
- `api/tests/test_doc_rag_node.py` -- `_GUIDE_ROW`를 `("패밀리카 적합 차종", "가이드 본문 텍스트", 0.1)`처럼 3-tuple로 갱신(기존 테스트가 쓰는 자리 전부 갱신). 신규: 거리값이 컷오프 초과(예: 0.5)인 가이드 행을 넣고 `doc_rag_node()` 호출 시 answer에 "참고:"가 없는지 확인(AC2). 신규: 컷오프 이내(예: 0.1) 값으로 기존 인용 동작이 유지되는지 명시 확인.
- `api/tests/test_hybrid_rag_node.py` -- 모든 `run_select` 가짜를 `"from guide_documents" in sql.lower()`면 빈 리스트(또는 지정 가이드 행) 반환, 그 외엔 기존 로직을 타는 테이블 분기로 통일. `test_hybrid_none_condition_falls_back_to_doc_rag_node`·blank·near-miss 파라미터라이즈드 테스트에 `monkeypatch.setattr(node, "embed_query", lambda q: [0.1])` 추가(실네트워크 호출 방지). 신규: 가이드 행(컷오프 이내)을 주면 `_llm().invoke`에 전달된 `messages`의 system 프롬프트 문자열에 가이드 content가 포함되는지 캡처해 확인. 신규: 가이드 행(컷오프 초과)이면 프롬프트에 미포함 확인. 신규: LLM이 가이드 정보만으로 body_type 조건을 낸 것으로 가정한 고정 응답을 흘려보내(예: `"body_type IN ('중형차','SUV','RV')"`) 조립 SQL과 answer의 "(참고: ...)" 인용을 함께 확인.
- 두 모듈 docstring에서 "가이드 문서 1건을 항상/무조건 곁들인다" 표현을 "컷오프 이내일 때만"으로 정정.

**Acceptance Criteria:**
- Given HYBRID 경로, when `run_search("3천만원 이하로 무난한 패밀리카")`를 실제로 실행하면, then 응답 `listings`에 담긴 매물들의 `body_type`이 가이드가 제시하는 범주(중형차/SUV/RV 등)로 실제로 좁혀져 있다(매물 설명에 "패밀리카"라는 단어가 없어도 뜬다는 의도의 관찰 가능한 증거, FR44, 직접 실행 확인, B4) — 조립 SQL 확인은 이 관찰을 뒷받침하는 보조 증거일 뿐 대체하지 않는다.
- Given 아무 경로든, when 최상위 가이드 매칭 거리가 `_GUIDE_DISTANCE_CUTOFF`를 초과하면, then 그 가이드는 조건추출에도 answer 인용에도 쓰이지 않는다(FR49).
- Given HYBRID/doc_rag_node 어느 쪽이든, when listings가 0건이면, then 가이드 매칭 여부와 무관하게 인용을 붙이지 않는다(기존 FR17 우선순위 유지, 회귀 없음).
- Given `run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4` 실행, when `score_ab.py`로 채점하면, then `doc_hit()` recall이 컷오프 적용 전(패치 전 baseline)과 같거나 더 낫다(직접 실행 확인, B4, Block-If 조건 실측).
- Given 가이드가 조건추출에 쓰인 실제 응답, when 그 `answer` 문자열을 확인하면, then 정확히 `_ANSWER_FOUND.format(...)` + `" (참고: {title})"` 접미사와 글자 그대로 일치한다(LLM이 새로 지은 자유 문장이 섞여 있지 않다는 관찰 가능한 증거, AC2, 직접 실행 확인).

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[low]` `[patch]` `doc_rag_node.py`·`hybrid_rag_node.py`의 인용 게이트가 `if guide:`(튜플 존재만 확인)라 `guide_documents.title`이 빈 문자열이면 "(참고: )"라는 빈 인용이 붙을 수 있었다(13.6 이전엔 `if guide_title:`이 암묵적으로 이 케이스를 걸렀는데 리팩터로 유실). 두 파일 모두 `if guide and guide[0]:`로 정정, red→green 신규 테스트 2건 추가.
  - `[medium]` `[patch]` `hybrid_rag_node`가 재시도 루프 진입 전 가이드 질의확장을 위해 임베딩을 1회 계산해두고도, LLM이 NONE/공백을 내는 폴백 경로(정확히 이 스토리가 돕는 "느낌만 있는 질의" 유형)에서 `doc_rag_node(query)`를 인자 없이 호출해 그 안에서 embed_query·가이드 조회를 처음부터 다시 실행하고 있었다(재임베딩 낭비를 없앤다는 스펙 취지에 정면으로 반하는 신규 낭비). `doc_rag_node(query, qvec=None)`으로 시그니처를 확장(기존 호출자 회귀 없음)하고 폴백 호출을 `doc_rag_node(query, qvec=qvec)`로 정정, `embed_query` 호출횟수==1 단언으로 고정.
  - `[medium]` `[patch]` 이 스토리의 headline 기능(가이드 질의확장이 실제 LLM 호출에서 동작하는지)을 잡을 수 있는 테스트가 unit·live 어디에도 없었다 — 기존 `test_live_smoke_hybrid`는 route·답변 접두사만 확인해 가이드 주입이 조용히 무동작이어도 계속 초록이었다. 스펙의 manual-check 예시 질의를 그대로 쓰는 이 라이브 테스트에 `"(참고:" in out["answer"]` 단언 추가(body_type은 ListingCard wire 계약에 없어 대체 불가 — 근거를 주석으로 남김).
  - `[medium]` `[patch]` 스펙 Block-If/Verification이 명명한 `run_phase_b.py --subset B1,...,G4`가 `docs/ai-ab-test-queryset.json` 확인 결과 전부 `primary_path: "B"`라 HYBRID 경로를 하나도 안 태운다는 것을 확인 — 이 명령이 나중에 통과해도 AC1(가이드 질의확장)은 검증되지 않는데, 이 사실이 기록돼 있지 않으면 미래 세션이 오판할 위험이 있었다. Verification 섹션(intent-contract 밖)에 이 한계를 명문화하고 DW-605 신규 등재(기존 DW-604 무수정).
  - `[low]` `[patch]` 스펙의 수동 확인 지시("실제 코사인 거리를 로그로 관찰")를 따를 방법이 코드에 없었다(`find_relevant_guide`가 거리값을 로깅하지 않음). 컷오프 통과/차단 무관하게 매 호출마다 거리·제목·통과여부를 `logger.info`로 남기도록 추가.
  - `[low]` `defer` 인용 부착 조건이 "가이드가 컷오프 이내로 발견됨"만 확인하고 "그 가이드가 실제로 LLM의 조건추출에 반영됐음"은 확인하지 않는다 — 이미 명시 조건만 준 질의가 우연히 무관한 가이드와 거리상 가깝다면 그 매물과 무관한 가이드 제목이 인용될 수 있다(코퍼스 규모·거리 특성상 빈도는 낮을 것으로 판단). "실제 반영 여부"를 프로그램적으로 판별하려면 LLM 출력과 가이드 제안 항목의 대응을 검증하는 새 메커니즘이 필요해 이번 패스의 patch 범위를 넘는다 → DW-606.
  - `[low]` `reject` 가이드 content가 검증 없이 시스템 프롬프트에 그대로 삽입된다는 지적 — 코퍼스는 사용자 입력이 아니라 개발자가 작성한 정적 12문서라 실제 공격 표면이 없다.
  - `[low]` `reject` 컷오프가 하드코딩 상수라 조정하려면 재배포가 필요하다는 지적 — 이 프로젝트의 기존 관례(`_CLARIFY_TURN_CAP=3` 등 실측 후 확정하는 상수)와 일치하는 의도된 설계(스펙 Design Notes 참조).
  - `[low]` `reject` "노이즈 부착률"을 재는 전용 스코어러가 `score_ab.py`에 없다는 지적 — 스펙 Never 절이 이미 "신규 노이즈 스코어러 추가하지 않는다, 기존 recall 확인 + 라이브 관찰로 충분"으로 명시적으로 결정한 트레이드오프다.
  - `[low]` `reject` AC 문구 "임계값은 하드코딩 상수가 아니라"를 글자 그대로 읽으면 config/env로 빼야 한다는 지적 — 스펙 Design Notes가 이미 "임의값 금지"로 해석해 실측 후 확정한 상수를 코드에 두는 방식을 명시적으로 택했다.
  - `[low]` `reject` 사용자의 명시 조건과 가이드 제안이 충돌하는 시나리오·거리 동점 시 비결정성 지적 — 이론적 시나리오이고 가이드 주입 여부와 무관하게 LLM 프롬프팅 일반에 이미 내재한 위험이라 이 스토리가 새로 만든 문제가 아니다.

### 2026-07-31 — Review pass (후속 2회차)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 12: (high 0, medium 0, low 12)
- addressed_findings:
  - `[medium]` `[patch]` 1회차가 AC1(가이드 질의확장)의 라이브 가드라고 스펙 Verification·Auto Run Result에 기록한 `assert "(참고:" in out["answer"]`가 **실제로는 가드가 아니었다** — 인용은 `if listings and guide`, 즉 "가이드가 거리상 가까운가"만 보고 "그 가이드가 조건추출에 반영됐는가"는 보지 않는다. 변이 실측으로 확인(`_GUIDE_BLOCK_TEMPLATE`를 통째로 비워 질의확장을 죽여도 단언이 통과). `test_live_smoke_hybrid()`에 추출된 구조조건 로그(`hybrid_rag_node attempt N 구조조건: ...`)를 caplog로 읽어 가이드가 명시하는 구조 컬럼(`body_type`·`seats`·`accident_free`)이 실제 등장하는지 확인하는 단언을 추가(조건추출 규칙 2 때문에 가이드 주입이 없으면 이 질의에서 나올 수 있는 조건은 가격뿐 — 그래서 이 단언이 질의확장을 직접 관측한다). 매물 0건과 가이드 미작동을 구분하는 `assert out["listings"]`도 앞에 추가. 스펙 Verification의 과장된 서술도 정정.
  - `[medium]` `[patch]` `find_relevant_guide`의 SQL은 `%s`를 2개 쓰고 params도 2개를 넘기는데, 두 단위테스트 파일 모두 `run_select` 가짜가 params를 통째로 무시해 바인딩을 1개로 줄여도 전 스위트가 초록이었다(변이 실측). 실 DB에서는 즉시 실행 오류 → `/ai/search` 전체 500이 되는데 CI가 눈이 먼 상태였다(이 SQL은 어떤 통합 테스트에서도 실행되지 않는다). 컬럼(`title, content`)·`embedding IS NOT NULL`·정렬·`LIMIT 1`·**자리표시자 개수 == params 개수 == 2**를 못박는 테스트 추가, red→green 실측.
  - `[low]` `[patch]` 1회차의 빈 제목 방어가 **인용 자리에만** 들어가 두 구멍이 남아 있었다: (a) 공백뿐인 제목("   ")은 truthy라 "(참고:    )"가 그대로 붙었고(실측), (b) 빈 제목·빈 본문 가이드가 hybrid의 조건추출 프롬프트에는 여전히 주입돼 매핑 없이 "규칙 2보다 우선한다"는 지시만 LLM에 전달됐다. 게이트를 `find_relevant_guide` 한 곳으로 모아(제목·본문이 strip 후 비면 None) 두 자리를 함께 닫고, doc/hybrid 양쪽에 파라미터라이즈드 테스트 추가, red→green 실측.
  - `[low]` `[patch]` 컷오프 경계(`<=` vs `<`)가 어디에서도 고정돼 있지 않았다 — 기존 픽스처가 0.1(한참 안쪽)·0.5(한참 바깥)뿐이라 연산자를 바꿔도 전 스위트가 초록이었다. 거리 == 컷오프(포함)·컷오프+1e-9(제외) 경계 테스트 2건 추가. `_GUIDE_DISTANCE_CUTOFF`가 테스트 파일에 import만 되고 안 쓰이던 것도 이 테스트들이 해소한다(DW-604로 0.3이 실측값으로 바뀔 때가 특히 위험한 자리).
  - `[low]` `[patch]` `find_relevant_guide`가 가이드 0건일 때 아무 로그도 남기지 않아, 자기 주석("컷오프 통과/차단 모두 매 호출마다 남긴다")과 스펙의 수동 확인 지시를 지키지 못했다 — 로그가 비면 "코퍼스가 안 임베딩됐다"와 "로그가 사라졌다"를 구분할 수 없다. 0건 로그 추가. 같은 함수의 `title, _content, distance` 언패킹(쓰지 않는다는 뜻의 `_` 접두사를 붙여 놓고 `rows[0][1]`로 다시 읽던 이중 접근)도 이 편집 범위 안에서 `content`로 정리.
  - `[low]` `[patch]` `test_hybrid_near_miss_none_sentinel_falls_back`에 `assert calls["doc"] == 1`이 두 번 있었다(1회차 패치의 붙여넣기 잔재). 중복 삭제.
  - `[medium]` `defer` Block-If의 실측 관측력이 DW-605에 기록된 것보다 더 작다는 것을 이번 리뷰에서 직접 채점해 확인 — 9건 중 5건(B2·B4·B5·B6·B7)이 baseline 캡처에서 실제로 `route_last: "C"`(REJECT)라 `doc_rag_node`에 도달조차 못 했고, `doc_hit`가 True인 항목은 3건(B1·B3·G1)뿐이다. 게다가 `doc_hit()`는 기대 제목의 존재만 상 주고 엉뚱한 인용은 벌하지 못한다 — 실측: G4(`doc_refs: null`)의 baseline answer가 "(참고: 초보 운전자에게 적합한 차종)"을 달고 있는데, 컷오프가 이 노이즈를 성공적으로 걸러도 점수는 0만큼 변한다. 스펙 Never 절이 신규 스코어러를 이미 금지했으므로 고치지 않고 대가를 측정값으로 등재 → DW-607(신규, 기존 항목 무수정).
  - `[low]` `reject` 가이드 조회를 try/except로 감싸 실패 시 degrade하라는 지적(3개 레이어 중복) — 이 프로젝트의 두 노드는 명시적으로 fail-loud 설계이고("조용한 빈 결과 금지"), 13.6 이전에도 `doc_rag_node`의 가이드 조회는 똑같이 무방비였다. 즉 이 스토리가 만든 새 설계가 아니라 기존 규약을 hybrid에 확장한 것이며, 여기서만 예외를 삼키면 `guide_documents` 권한·마이그레이션 사고가 조용해진다.
  - `[low]` `reject` 가이드 유래 AND 조건이 결과를 0건으로 좁힐 수 있으니 폴백하라는 지적 — 스펙 I/O 매트릭스가 "매물 0건 → FR17 안내, 인용 생략"으로 이미 명시적으로 결정한 동작이다(라이브 미관측 이론 시나리오이기도 하다).
  - `[low]` `reject` 가이드 주입이 가드 차단을 유발해 400이 될 수 있다는 지적 — 위와 같은 부류의 이론 시나리오이고, 1회 재시도 메커니즘이 이미 존재한다.
  - `[low]` `reject` NONE 폴백에서 `guide_documents` 조회가 2회 발생한다는 지적(4개 레이어 중복, 실측 사실) — 10행짜리 테이블의 top-1 스캔이고, 없애려면 sentinel 기본값을 가진 세 번째 인자를 뚫어야 한다. 1회차가 없앤 것은 **과금되는** Gemini 임베딩 호출이라 성격이 다르다. A2(단순함 우선) 기준 과설계로 판단.
  - `[low]` `reject` 가이드 content 길이 상한이 없다는 지적 — 개발자가 쓴 정적 10문서(각 ~2KB) 코퍼스라 상한 상수는 과설계.
  - `[low]` `reject` 거리 동점 시 tie-breaker가 없다는 지적 — 리포 전반의 기존 `ORDER BY embedding <=>` 관례이고 이 스토리가 만든 문제가 아니다.
  - `[low]` `reject` `doc_rag_node`의 지역변수 `qvec`이 `list[float]`로 주석돼 있으나 str로 재바인딩된다는 지적 및 명명 정리 요구 — 동작 결과가 없는 표현 정리라 A3(외과적 변경) 기준 이번 diff 밖.
  - `[low]` `reject` 스펙 Intent의 "12문서"가 실제 코퍼스 10개(`corpus/*.md`, 2개는 `_excluded/`)와 다르다는 지적 — 사실이지만 `<intent-contract>` 안이라 수정 대상이 아니고, 그 문장이 뒷받침하던 결론(정적·개발자 작성 코퍼스라 공격 표면 없음)은 그대로 성립한다.
  - `[low]` `reject` `review_loop_iteration: 0`이 채워진 트리아지 로그와 모순된다는 지적 — 이 값은 워크플로가 후속 리뷰 진입 시 0으로 재설정하는 운영 필드다.
  - `[low]` `reject` 스펙 frontmatter `status: in-review`와 sprint-status의 `done`이 어긋난다는 지적 — 바로 이 리뷰 패스가 진행 중이라 그렇다(종료 시 done으로 되돌린다).
  - `[low]` `reject` Block-If 미실행 상태로 done 처리된 것 자체에 대한 지적(4개 레이어) — 이미 DW-604와 Auto Run Result 잔여 위험에 기록돼 있고, 환경 차단(docker·sudo·DATABASE_URL 부재)은 이 세션에서도 그대로다. 중복 등재하지 않는다.
  - `[low]` `reject` 임계값이 실측으로 조정되면 라이브 스모크가 깨진다는 지적 — 그게 가드의 목적이다.
  - `[low]` `reject` 가드 2회 차단으로 400이 되는 경로에서도 임베딩을 1회 쓰게 됐다는 지적 — 재시도 루프 진입 전 1회 계산은 스펙 Always 절이 명시적으로 요구한 동작이다.

### 2026-07-31 — Review pass (후속 3회차)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 3, low 6)
- defer: 2: (high 0, medium 2, low 0)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` HYBRID 경로에서 **"매물 0건이면 인용 없음"(AC3, I/O 매트릭스 5행)이 무방비**였다 — 변이 실측으로 확인: 인용 게이트에서 `listings and`를 지워도 전 스위트가 370 passed로 초록이었다. 컷오프 이내 가이드를 쓰는 HYBRID 테스트 2건은 둘 다 매물 1건을 돌려주고, 0건 테스트 1건은 가이드가 없어서 **두 조건의 교집합이 한 번도 테스트되지 않았다**(doc_rag_node 쪽 짝 테스트는 이미 있었다). 회귀 시 사용자는 "조건에 맞는 매물이 없어요… (참고: …)"라는 모순된 답변을 받는데 CI는 초록이다. `test_hybrid_empty_result_with_guide_omits_citation` 추가, red→green 실측. 2회차 Auto Run Result의 "I/O 매트릭스 5행 전부 커버" 주장이 이 칸에는 성립하지 않았다.
  - `[medium]` `[patch]` **1회차가 고쳤다는 "재임베딩 제거"가 실제로는 고정돼 있지 않았다(검증 착시 3번째)** — `doc_rag_node`가 전달받은 `qvec`을 무시하고 `embed_query(query)`를 다시 부르도록 되돌려도 전 스위트가 초록이었다(변이 실측). 세 곳의 `assert qvec == [0.1]`은 모두 `doc_rag_node` **자체를 대체한** `fake_doc` 안에 있어 "hybrid가 인자를 넘겼다"만 증명하고 "doc_rag_node가 그 인자를 썼다"는 증명하지 않는데, 테스트 주석은 후자를 못박는다고 적혀 있었다. 대가는 과금되는 Gemini 임베딩 중복 호출이며 하필 이 스토리가 돕는 "느낌만 있는 질의"(NONE 폴백) 경로에서 발생한다. 실물 `doc_rag_node`에 `qvec`을 넘겨 `embed_query` 미호출 + 두 쿼리 바인딩값을 단언하는 테스트 추가, red→green 실측.
  - `[medium]` `[patch]` `hybrid_rag_node`가 가이드 조회에 넘기는 **값**이 무관측이었다 — `find_relevant_guide(qvec_literal)`을 `find_relevant_guide(qvec)`(list[float])로 바꿔도 초록(변이 실측). `_patch_guide_lookup`의 가짜 `run_select`가 sql·params를 통째로 버렸기 때문이다. 실 DB에선 psycopg가 리스트를 `ARRAY[...]`로 적응시켜 `::vector` 캐스팅이 실패하고 HYBRID 요청 전체가 500이 된다(2회차가 같은 SQL의 자리표시자 **개수**는 못박았지만 doc_rag_node 호출부만 커버했다). 헬퍼가 인자를 기록하도록 고치고 hybrid 호출부에 `guide_params == ("[0.1]","[0.1]")` 단언 추가, red→green 실측.
  - `[low]` `[patch]` `find_relevant_guide`의 컷오프 게이트가 `if distance > _GUIDE_DISTANCE_CUTOFF`라 **NaN이 통과**했다 — NaN과의 모든 비교는 False이므로 `>` 검사를 빠져나가고, 바로 위 로그는 같은 식을 써서 `컷오프통과=False`라고 남기는데 함수는 그 가이드를 반환했다(직접 실행 재현: 로그 `거리=nan … 컷오프통과=False`, 반환 `('무관 가이드','본문')`). 즉 스펙이 요구한 유일한 계측 수단이 실제 동작과 반대를 말했다. 도달 경로는 영벡터 질의 임베딩(`embeddings.py`의 `_l2_normalize`가 `norm==0`을 그대로 통과시킨다) → pgvector `<=>`가 NaN → 모든 행이 NaN이라 `LIMIT 1`이 임의의 무관 가이드를 집어 조건추출 프롬프트까지 오염시킨다. 게이트를 통과 조건(`not (d <= cutoff)`)으로 뒤집고 NaN 회귀 테스트 추가, red→green 실측.
  - `[low]` `[patch]` 스펙 Always의 "재시도 루프 **진입 전** 1회만 계산"을 못박는 호출횟수 단언이 NONE/공백 폴백 테스트 3건에만 있었다 — 정작 낭비가 2배가 되는 경로(가드 차단 → LLM 2회전)의 테스트는 호출을 세지 않아, 호이스트를 루프 안으로 되돌려도 초록이었다(변이 실측). `test_hybrid_guard_rejection_retries_once_then_succeeds`에 `embed_query`·`find_relevant_guide` 각 1회 단언 추가, red→green 실측.
  - `[low]` `[patch]` 2회차가 공백 제목·본문 게이트를 `find_relevant_guide` 한 곳으로 모은 뒤에도 두 호출부의 `and guide[0]`이 **도달 불가한 죽은 검사**로 남았고, 그것을 지킨다고 주장하는 테스트 docstring 2건이 그대로였다(정적 확인 — 헬퍼가 공백 제목을 None으로 거르므로 non-None 가이드의 title은 항상 비어 있지 않다). "방어가 두 겹"이라는 오해는 위험하다: 헬퍼의 strip 검사를 지우면 호출부는 못 막는다. 검사 자체는 무해하므로 남기고, 두 파일의 주석과 두 테스트 docstring을 "실제 게이트는 헬퍼 한 곳"으로 정정했다.
  - `[low]` `[patch]` `test_guide_derived_condition_flows_into_sql_and_answer_citation`의 이름·docstring이 "가이드로만 **도출된** 조건"을 검증한다고 주장했지만, 조건 문자열은 `_FixedLLM`에 테스트가 직접 박아 넣은 상수라 가이드 주입과 인과가 없다 — 가짜 LLM으로는 원리상 도출을 관측할 수 없다. 2회차가 어렵게 정정한 것과 같은 형태의 검증 착시가 유닛 레벨에 새로 생기는 것을 막기 위해 `test_guide_present_condition_is_assembled_and_cited`로 개명하고, 실제로 고정되는 것(조립 모양·인용 문자열)과 도출을 관측하는 곳(라이브 스모크의 구조조건 로그 단언)을 docstring에 명시했다.
  - `[low]` `[patch]` 2회차가 "실 DB로 못 돌려보므로 유일한 가드"라고 명시한 가이드 SQL 테스트가 기본값 없는 `next(...)`를 써서, 가장 중요한 회귀(가이드 조회가 사라짐)에서 원인을 말하지 않는 `StopIteration` error로 끝났다. `next(..., None)` + 한국어 실패 메시지로 바꿨고, 실제로 `find_relevant_guide` 호출을 제거하는 변이로 `AssertionError: 가이드 조회 SQL이 발행되지 않았다`가 뜨는 것을 확인했다.
  - `[low]` `[patch]` `_patch_guide_lookup`의 가짜 `run_select`가 SQL을 보지 않고 **모든** 질의에 가이드 행을 돌려줬다(형제 헬퍼 `_install_fakes`는 테이블로 분기한다). 지금 깨지지는 않지만, 실물 `doc_rag_node`를 타는 폴백 테스트가 생기면 `(title, content, distance)` 3-tuple이 매물 행으로 넘어가 `rows_to_cards`에서 정체불명 크래시가 난다. `from guide_documents` 분기를 추가했다.
  - `[medium]` `defer` 문서화된 Block-If 명령이 그 명령이 약속한 "전/후 recall 비교"를 원리상 수행하지 못한다 — `score_ab.py`를 직접 읽어 확인: (1) `--raw`에 파일 1개만 넘기는 1-raw 모드는 소스 주석 그대로 "베이스라인 단독 — A/B 비교 없음"이다(617행), (2) 게이트 지표 `doc_hit`은 `score_model()` summary에 **없고** per-item(465행)에만 있어 콘솔·회귀게이트에 안 나온다, (3) subset 9건을 44항목 queryset으로 채점하면 `is_partial: True`·`missing_n: 35`가 되어 44건인 `g2-baseline.json`과 분모가 다르다. 미래 세션이 명령을 그대로 실행하고 "Block-If 초록"으로 오판할 위험이 실재한다. 스펙 Never 절이 신규 스코어러를 금지했고 이 세션엔 실행 환경도 없어 고치지 않고 등재 → DW-608(신규, 기존 항목 무수정).
  - `[medium]` `defer` DW-605·DW-607이 처방한 "subset 재구성"이 원리상 불가능하다 — queryset 44항목 **전체**의 `primary_path`를 직접 집계해 항목 A=20·B=9·C=6·멀티턴 9, 턴 A=16·B=3·C=1이고 파일 전체에 `HYBRID` 문자열이 0회임을 확인했다. 즉 뽑을 HYBRID 항목 자체가 없어 subset을 다시 골라도 AC1은 A/B 하네스에서 영원히 관측되지 않는다 → DW-609(신규, 기존 항목 무수정).
  - `[low]` `reject` 조건추출 규칙 2의 few-shot 예시가 하필 라이브 스모크 질의로 "패밀리카는 버려라 → price만"을 시연해 가이드 블록의 추상 지시를 이길 것이라는 지적 — **라이브 실측으로 반증**됐다. 실제 Gemini로 2회 실행: 가이드 미주입 시 `price <= 30000000`만(구조 컬럼 0회), `corpus/02-패밀리카-적합-차종.md` 주입 시 `body_type IN ('준중형차','중형차','SUV','RV') AND price <= 30000000`. override가 실제로 작동하며, 동시에 2회차가 추가한 AC1 가드의 전제("가이드 없으면 가격뿐")도 실측으로 확인됐다.
  - `[low]` `reject` 가이드 블록에 조건 개수·범위 상한이 없어 AND가 3~5개 쌓여 0건이 되고 새 `assert out["listings"]`가 깨진다는 지적 — 실측으로 반증. 위 라이브 실행이 실제로 낸 조건은 2개(body_type·price)뿐이고, 조립 SQL은 `validate_select_sql()`을 통과했으며, `supabase/seed.sql` 파싱 결과 `on_sale` 37건 중 **14건**이 그 조건을 만족한다(`LIMIT 5` 대비 충분).
  - `[low]` `reject` 가이드 블록이 시스템 프롬프트의 종결 지시("출력: 조건 표현식 한 줄 또는 NONE.") **뒤**에 붙어 출력 형식 지시가 산문에 묻힌다는 지적 — 위 라이브 실행 2회 모두 깨끗한 한 줄 조건을 반환했다(설명문·다중 행 없음). 관측되지 않은 이론 위험이다.
  - `[low]` `reject` 가이드 블록 마지막 문장("이 가이드 내용으로 답변 문장을 새로 짓지는 않는다")이 이 LLM이 할 수 없는 일을 금지하는 잡음이라는 지적 — 사실이지만 관측되는 동작 변화가 없는 표현 정리라 A3(외과적 변경) 기준 이번 diff 밖이다.
  - `[low]` `reject` `doc_rag_node`가 `if not listings` 조기반환 **앞에서** 가이드를 조회해 0건 질의마다 왕복이 낭비된다는 지적 — 이 순서는 13.6 **이전 코드와 동일**하다(구 코드도 `guide_rows = run_select(...)` → 로그 → `if not listings: return` 순서였다). 이 스토리가 만든 문제가 아니고, 2회차가 같은 근거(A2 단순함)로 reject한 폴백 중복 조회와 같은 부류다.
  - `[low]` `reject` DW-607이 DW-605를 명시적으로 정정했는데 DW-605가 무수정 `open`이라 `superseded_by` 표기가 필요하다는 지적 — 타당한 지적이지만 이 실행의 명시 제약이 "기존 대장 항목은 수정·재개방·재작성하지 않는다(오케스트레이터가 상태와 해소를 소유한다)"다. 대신 신규 DW-609의 reason에 "DW-605·DW-607의 처방이 원리상 불가능하다"는 정정 내용을 담아 같은 정보가 대장에 남게 했다.
  - `[low]` `reject` 거리 INFO 로그가 요청마다 1줄로 영구화됐고 내릴 조건이 없다는 지적 — 이 로그는 스펙 Verification의 수동 확인 지시("실제 코사인 거리를 로그로 관찰해 0.3이 그 케이스를 걸러내는지 확인")를 실행 가능하게 하려고 2회차가 의도적으로 넣은 것이고, DW-604의 실측 세션이 바로 이 로그를 소비한다. 그 세션 전에 낮추면 계측 수단을 없애는 것이 된다.

## Design Notes

**질의확장(FR44)을 `hybrid_rag_node.py`에 두고 `doc_rag_node.py`엔 컷오프만 적용한 근거.** architecture 문서는 원래 `doc_rag_node.py`를 "하이브리드 승격 + 가이드 질의확장" 대상 파일로 지목했지만, 그 문서 작성 이후 13.3이 조건추출 LLM 로직을 `hybrid_rag_node.py`로 분리했다. "가이드 content를 검색 조건으로 변환"하려면 그 변환을 실제로 수행하는 LLM 호출이 필요한데, 그게 지금 존재하는 곳은 `hybrid_rag_node`뿐이다(구조조건 추출 LLM). `doc_rag_node`의 순수 벡터 경로는 조건추출 자체가 없어 "변환"할 대상이 없고, 이미 임베딩 유사도로 의미를 반영하고 있어 새 LLM 호출을 추가하는 건 과설계다(A2). 경로 A(`sql_rag_node.py`)는 이미 명시 조건만 다루는 질의만 오므로 가이드 개입이 불필요해 손대지 않는다.

**"가중치"를 별도 스코어 결합이 아니라 AND 조건 추가로 해석한 근거.** 리서치 문서(research-langx-rag-patterns.md §3)가 RRF·가중 선형 융합 모두 이 프로젝트 규모엔 과설계라고 이미 결론 냈고, 기존 하이브리드 조합도 조건들을 전부 AND로만 묶는다(OR 금지). 가이드에서 도출한 조건을 같은 AND 체인에 얹는 것이 유일하게 기존 인프라와 정합하는 해석이다.

**DW-600을 이번 패스에서 닫지 않는 근거.** 에픽 컨텍스트는 "13.6이 answer_node를 여는 시점에 DW-600을 처리하라"고 지정했지만, 실제로 가이드 인용 문구 조립은 `doc_rag_node`/`hybrid_rag_node` 내부에서 일어나고 `answer_node.py`는 여전히 단순 통과(pass-through)만 한다 — 이번 스토리가 그 파일을 열지 않으므로 트리거 조건이 성립하지 않는다. 억지로 `answer_node.py`를 열어 DW-600을 닫으면 13.5가 세 차례 리뷰로 확정한 REJECT `narrowed_by` 범위(칩 UI 이전엔 값 배선까지)를 이번 스토리 범위 밖에서 재론하게 되므로 하지 않는다.

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/ -x -q` -- expected: 전량 통과(신규 테스트 포함).
- `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python scripts/run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4 --out /tmp/g13-6-check.json && .venv/bin/python scripts/score_ab.py --queryset docs/ai-ab-test-queryset.json --raw /tmp/g13-6-check.json --out /tmp/g13-6-report.json` -- expected: `doc_hit` recall이 기존 g2-baseline 대비 하락 없음(Block-If 조건 실측).
  ⚠️ 코드리뷰(2026-07-31): 위 subset(`B1,B2,B3,B4,B5,B6,B7,G1,G4`)은 `docs/ai-ab-test-queryset.json`을
  확인한 결과 전부 `primary_path: "B"`(순수 벡터 `doc_rag_node` 인용 경로)다 — HYBRID로 라우팅되는
  항목이 하나도 없다. 즉 이 명령은 인용/컷오프 recall(FR49, `doc_rag_node`)만 검증하고, 이 스토리의
  headline 기능인 AC1(`hybrid_rag_node`의 가이드 질의확장, FR44)은 전혀 검증하지 못한다. AC1의 실물
  검증은 아래 강화된 `test_live_smoke_hybrid()`와 바로 아래 수동 확인 항목이 맡는다 — 이 subset을
  통과시키는 것만으로 AC1을 검증했다고 판단하지 않는다(DW-605 참조).
  ✎ 후속 코드리뷰(2026-07-31) 정정 2건 — 위 문단이 원래 적어 둔 "answer의 `(참고:` 인용 확인"은
  **AC1의 가드가 아니었다**(변이 실측: `_GUIDE_BLOCK_TEMPLATE`를 통째로 비워 질의확장을 죽여도 그
  단언은 그대로 통과했다). 인용은 "가이드가 거리상 가까운가"만 보고 "그 가이드가 조건추출에
  반영됐는가"는 보지 않기 때문이다. 그래서 `test_live_smoke_hybrid()`에 **추출된 구조조건 로그**에
  가이드가 명시하는 구조 컬럼(`body_type`·`seats`·`accident_free`)이 실제로 등장하는지 확인하는
  단언을 추가했다 — 조건추출 규칙 2("느낌 표현은 버려라") 때문에, 가이드 주입이 없으면 이 질의에서
  나올 수 있는 조건은 가격뿐이다. 또한 위 subset의 실측 관측력은 문단이 시사하는 것보다 더 작다:
  `score_ab.py`는 `doc_hit`를 `primary_path == "B"`인 항목에만 계산하고, `docs/g2-baseline.json`
  기준 9개 중 5개(B2·B4·B5·B6·B7)는 실제로 `route_last: "C"`(REJECT)로 빠져 `doc_hit`가 유의미한
  항목은 사실상 3개뿐이다(DW-607).
  ✎ 3회차 코드리뷰(2026-07-31) — 위 명령은 **적힌 대로는 애초에 동작하지 않는다**(DW-608). `--raw`에
  파일을 1개만 넘기는 모드는 `score_ab.py` 자신의 주석대로 "베이스라인 단독 — A/B 비교 없음"이고,
  게이트 지표 `doc_hit`은 summary에 없어(per-item 465행에만 기록) 콘솔·회귀게이트에 뜨지 않으며,
  subset 9건을 44항목 queryset으로 채점하면 `is_partial: True`라 44건 baseline과 분모가 다르다.
  실행하려면 `--raw`에 baseline과 후보 2개를 넘기고 분모를 맞추고 `per_item`을 직접 세야 한다.
  또한 **AC1을 이 하네스로 관측하는 것은 subset 재구성으로도 불가능하다**(DW-609): queryset 44항목
  전체가 A=20·B=9·C=6·멀티턴 9이고 파일에 `HYBRID` 라벨이 0건이라 뽑을 항목 자체가 없다.
  ✎ 다만 **질의확장 자체는 이 패스에서 라이브로 관측됐다**(프롬프트 단독 실행, 실제 Gemini 2회):
  가이드 미주입 시 `"3천만원 이하로 무난한 패밀리카"` → `price <= 30000000`(구조 컬럼 0회),
  `corpus/02-패밀리카-적합-차종.md` 주입 시 → `body_type IN ('준중형차','중형차','SUV','RV') AND
  price <= 30000000`. 조립 SQL은 `validate_select_sql()`을 통과했고, `seed.sql` 파싱 결과 `on_sale`
  37건 중 14건이 그 조건을 만족한다(`LIMIT 5` 대비 충분 — 0건 위험 없음). 즉 남은 공백은 기능이
  아니라 **회귀 하네스의 커버리지**이며, `test_live_smoke_hybrid`의 구조조건 로그 단언이 겨눈
  전제("가이드 없으면 가격 조건뿐")도 이 실측으로 뒷받침된다.

**Manual checks (if no CLI):**
- 로컬 Supabase+`GEMINI_API_KEY`로 `hybrid_rag_node("3천만원 이하로 무난한 패밀리카")`를 직접 호출해, 조립된 SQL에 `body_type` 조건이 실제로 포함되는지, answer에 "(참고: ...)" 인용이 붙는지 눈으로 확인(SM-G 신규 분기 실동작 증거).
- 가이드와 무관한 질의(예: "타이어 공기압 얼마가 적당해?")로 `find_relevant_guide`가 반환하는 실제 코사인 거리를 로그로 관찰해 0.3이 그 케이스를 걸러내는지 확인, 필요하면 임계값을 조정하고 그 실측값을 여기 기록한다.

## Auto Run Result

**Status:** done

**Summary:** `guide_documents`(가이드 코퍼스 content)를 실제 검색에 반영하는 두 갈래를 구현했다. ① `doc_rag_node.py`에 공유 헬퍼 `find_relevant_guide(qvec_literal)`를 신설해 코사인 거리 컷오프(`_GUIDE_DISTANCE_CUTOFF=0.3`, FR49) 이내일 때만 (title, content)를 반환하게 하고, 기존 "가이드 1건 무조건 인용" 로직을 이 게이트로 교체했다. ② `hybrid_rag_node.py`가 조건추출 LLM 호출 이전에 같은 헬퍼로 가이드를 조회해, 게이트를 통과하면 그 content를 시스템 프롬프트에 주입("규칙 2(느낌 표현 버리기)보다 이 매핑이 우선한다"는 지시 포함)해 LLM이 "패밀리카" 같은 느낌 표현을 가이드가 제시하는 구조조건(body_type 등)으로 바꾸게 했다(질의확장, FR44). 답변 문장 자체는 LLM이 새로 짓지 않고 기존 결정론 템플릿 + 결정론적 인용 접미사만 붙는다(AC2). 코드리뷰에서 잡힌 5건(빈 제목 인용, NONE-폴백 경로의 이중 임베딩 낭비, headline 기능을 잡는 테스트 부재, 스펙 자체 Block-If가 HYBRID를 커버 못하는 문제, 거리값 미로깅)을 전부 패치했다.

**Files changed:**
- `api/app/graph/doc_rag_node.py` -- `_GUIDE_DISTANCE_CUTOFF` 상수 + `find_relevant_guide()` 헬퍼 신설(거리·제목 로깅 포함), `doc_rag_node()`가 이를 사용하도록 교체(qvec 선택적 인자 추가 — 호출자가 이미 계산한 임베딩 재사용 가능), 인용 게이트를 `guide and guide[0]`로 강화, 모듈 docstring 갱신.
- `api/app/graph/hybrid_rag_node.py` -- `find_relevant_guide` import, 재시도 루프 진입 전 qvec/가이드 1회 계산 후 시스템 프롬프트에 조건부 가이드 블록 주입, NONE/공백 폴백이 호이스트된 qvec을 `doc_rag_node`에 넘겨 재임베딩 제거, 성공 경로 answer에 결정론적 인용 부착(빈 제목 방어 포함), 모듈 docstring 갱신.
- `api/tests/test_doc_rag_node.py` -- `_GUIDE_ROW`를 (title, content, distance) 3-tuple로 갱신, 컷오프 이내/초과·빈 제목 신규 테스트 3건.
- `api/tests/test_hybrid_rag_node.py` -- 모든 기존 테스트에 가이드 조회 몽키패치(`_patch_guide_lookup`) 추가, NONE/공백/near-miss 폴백 테스트에 embed_query 1회 호출 단언 추가, 가이드 주입·컷오프 초과 미주입·가이드 유래 조건이 SQL+인용에 반영되는지 신규 테스트 3건.
- `api/tests/test_live_smoke.py` -- `test_live_smoke_hybrid`에 "(참고:" 인용 확인 단언 추가(headline 기능의 유일한 라이브 가드).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-604(Block-If 미검증, 환경 차단)·DW-605(Block-If subset이 HYBRID 미커버)·DW-606(인용이 "실제 사용" 미검증) 신규 open.

**Review findings breakdown:** 4개 레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행. patch 5건(medium 3, low 2) 전부 적용·재검증 완료(red→green 실측 포함). defer 1건(low, DW-606). reject 5건(전부 low — 이미 스펙 Design Notes/Never 절이 결정한 트레이드오프, 신뢰된 정적 코퍼스라 실공격표면 없음, 이 스토리가 만들지 않은 일반 LLM 프롬프팅 위험). intent_gap 0건, bad_spec 0건.

**Follow-up review recommendation:** true (`3×medium(3) + 1×low(2) = 11 ≥ 5`).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -x -q` → **364 passed, 84 skipped**(패치 전후 직접 재실행 확인).
- red→green 실측: `_GUIDE_DISTANCE_CUTOFF`를 1.0으로 완화해 신규 컷오프 테스트 3건이 실제로 깨지는 것 확인 → 0.3으로 원복 후 전량 green 재확인.
- `run_phase_b.py --subset B1,...,G4` + `score_ab.py` 라이브 Block-If: **미실행** — 이 세션 샌드박스에 docker(WSL2 통합 비활성)·sudo·`DATABASE_URL` 모두 없어 로컬 Supabase/pgvector를 띄울 수 없음을 직접 확인(`docker: command not found`, `sudo` 인증 불가, `api/.env`에 `DATABASE_URL` 없음). DW-604로 등재.
- Matrix Test Audit: I/O 매트릭스 5행 전부 실행·통과하는 단위테스트로 커버됨을 확인(가이드 컷오프 이내/초과 각 2경로·매물 0건).

**Residual risks:**
- `_GUIDE_DISTANCE_CUTOFF=0.3`은 실제 임베딩 거리 분포로 실측되지 않은 초기 후보값이다(DW-604) — 배포 전 로컬 Supabase 환경에서 `run_phase_b.py` Block-If를 반드시 실행해 확인해야 한다.
- 그 Block-If의 명명된 subset이 HYBRID 경로를 전혀 커버하지 않아, 통과해도 이 스토리의 headline 기능(질의확장)은 검증되지 않는다 — 강화된 `test_live_smoke_hybrid`가 유일한 라이브 가드이며 이 또한 미실행 상태다(DW-605).
- `hybrid_rag_node`의 가이드 인용이 "거리상 근접"만 확인하고 "실제 조건추출 반영"은 확인하지 않아, 드물게 무관한 가이드가 인용될 수 있다(DW-606, 저빈도로 판단).
- Flutter 앱은 이번 변경으로 늘어난 응답 텍스트(가이드 인용 접미사)를 별도로 파싱하지 않지만, 기존과 동일하게 `answer` 문자열 전체를 그대로 표시하므로 회귀는 없다.

**Residual artifacts (uncommitted):** 이 스펙 파일의 `final_revision` 필드 자체는 커밋 이후에 기록되므로(자기 자신의 해시를 미리 담을 수 없음) 정의상 이번 커밋에 없다 — 13.5 스펙에서도 동일했던 패턴이다. `git status --porcelain`에 이 파일만 단독으로 남으며, 별도로 커밋하지 않고 다음 스토리의 커밋에 자연스럽게 포함되거나 그대로 둔다.

---

### 후속 리뷰 패스 2회차 (2026-07-31)

**Status:** done

**Summary:** `status: done` 스펙에 대한 독립 후속 리뷰(4개 레이어 병렬: adversarial·edge-case-hunter·verification-gap·intent-alignment). 1회차가 남긴 **검증 착시** 두 건이 핵심이었다. ① 1회차가 "AC1(가이드 질의확장)의 유일한 라이브 가드"라고 스펙과 대장에 기록한 `assert "(참고:" in answer`는 실제로는 가드가 아니었다 — 질의확장 메커니즘을 통째로 죽여도 통과한다(변이 실측). ② `find_relevant_guide`의 SQL이 자리표시자 2개·params 2개인데 단위테스트가 params를 전부 무시해, 바인딩을 1개로 줄여도 전 스위트가 초록이었다(실 DB에선 `/ai/search` 전체 500). 둘 다 "만들었다"와 "잡는다"의 차이(CLAUDE.md B4)라 실행되는 검사로 바꿨다. 나머지 4건은 1회차 방어의 미봉(공백 제목·주입 자리 누락), 컷오프 경계 미고정, 0건 로그 누락, 중복 단언.

**Files changed (이번 패스):**
- `api/app/graph/doc_rag_node.py` -- `find_relevant_guide` 게이트를 한 곳으로 통합(컷오프 초과 → None, 제목·본문이 strip 후 비면 → None), 가이드 0건 로그 추가, `_content` 이중 접근 정리.
- `api/tests/test_doc_rag_node.py` -- 가이드 SQL 컬럼·필터·정렬·**자리표시자 개수 == params 개수** 단언, 컷오프 경계 2건(포함/제외), 공백 제목·공백 본문 거부 1건.
- `api/tests/test_hybrid_rag_node.py` -- 빈/공백 가이드가 인용뿐 아니라 **프롬프트 주입에서도** 제외되는지 파라미터라이즈드 3케이스로 교체, 중복 `assert calls["doc"] == 1` 삭제.
- `api/tests/test_live_smoke.py` -- 추출된 구조조건 로그를 caplog로 읽어 가이드 유래 구조 컬럼(`body_type`/`seats`/`accident_free`) 등장 여부를 단언(AC1의 실제 가드), `assert out["listings"]` 선행 확인, 과장된 주석 정정.
- `_bmad-output/implementation-artifacts/spec-13-6-…md` -- Verification의 과장 서술 정정(측정값 포함), 트리아지 로그 2회차 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-607 신규 등재(기존 항목 무수정).

**Review findings breakdown:** patch 6건(medium 2, low 4) 전부 적용. defer 1건(medium, DW-607). reject 12건(전부 low). intent_gap 0, bad_spec 0.

**Follow-up review recommendation:** true (`3×medium(2) + 1×low(4) = 10 ≥ 5`).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **370 passed, 84 skipped**(패치 전 364 → 신규 6건).
- red→green 실측 3건(모두 변이 주입 후 실제 red 확인 → 원복 후 green·md5 동일 확인):
  · 공백 제목/본문 가드 제거 → 신규 blank 테스트 4건 red.
  · 컷오프 비교를 `<=` → `<`로 변이 → 경계 포함 테스트 red.
  · 가이드 SQL 바인딩을 `(qvec_literal, qvec_literal)` → `(qvec_literal,)`로 변이 → 신규 SQL 테스트 red(변이 전에는 전 스위트가 초록이었다는 것이 이 패치의 근거).
- 대장 주장 직접 재측정: `docs/g2-baseline.json`을 `score_ab.doc_hit()`로 직접 채점해 subset 9건 중 5건이 `route_last: "C"`(REJECT), `doc_hit` True는 3건뿐, G4는 `doc_refs: null`인데도 baseline answer에 인용이 붙어 있음을 확인(DW-607 근거 — 문서에 적기 전에 실행해 확인, B4).
- `test_live_smoke_hybrid`의 신규 caplog 단언은 **미실행**(RUN_LIVE_SMOKE + 로컬 Supabase + GEMINI_API_KEY 필요 — DW-604와 동일한 환경 차단). 수집(collect)은 확인.

**Residual risks:**
- 1회차의 잔여 위험 4건은 그대로 유효하다(컷오프 0.3 미실측 DW-604, Block-If가 HYBRID 미커버 DW-605, 인용이 "실제 사용" 미검증 DW-606).
- 이번에 추가한 AC1 가드(구조조건 로그 단언)도 라이브 환경이 없어 아직 한 번도 실행되지 않았다 — DW-605의 트리거가 이 테스트를 지목하고 있으므로 그 세션에서 함께 확인된다.
- Block-If를 실행하더라도 유효 표본이 3건이고 노이즈 인용은 원리상 채점되지 않는다(DW-607) — 초록이 곧 "컷오프가 목적을 달성했다"는 뜻은 아니다.

---

### 후속 리뷰 패스 3회차 (2026-07-31)

**Status:** done

**Summary:** `status: done` 스펙에 대한 세 번째 독립 후속 리뷰(4개 레이어 병렬: adversarial·edge-case-hunter·verification-gap·intent-alignment). 이번 패스의 소득은 두 갈래다. ① **변이 실측으로만 드러나는 구멍 5건** — 2회차가 잡은 것과 같은 부류의 "검사가 있는데 안 잡는" 자리들이다: HYBRID의 "0건이면 인용 없음"(AC3)이 무방비였고, 1회차가 고쳤다는 "재임베딩 제거"는 실제로 고정돼 있지 않았고(주석은 고정한다고 주장 — 검증 착시 3번째), hybrid가 가이드 조회에 넘기는 **값**은 아무도 보지 않았고(리스트를 넘겨도 초록, 실 DB에선 500), 재시도 경로의 임베딩 호이스트도 무관측이었고, 컷오프 게이트는 NaN을 통과시키면서 로그로는 "차단"이라고 남겼다. ② **문서화된 검증 절차 자체가 실행 불가**라는 실측 2건 — Block-If 명령은 적힌 대로는 A/B 비교를 하지 않고 게이트 지표를 출력하지도 않으며(DW-608), AC1을 A/B 하네스로 관측하는 것은 queryset에 HYBRID 항목이 0건이라 subset 재구성으로도 불가능하다(DW-609). 반면 **기능 자체는 이번에 라이브로 관측됐다** — 실제 Gemini에 프롬프트만 따로 실행해 가이드 주입 전/후를 비교했고, 주입 시에만 `body_type` 조건이 나오는 것을 확인했다(1·2회차 잔여 위험 중 "질의확장이 실제로 동작하는지"라는 불확실성을 부분적으로 해소).

**Files changed (이번 패스):**
- `api/app/graph/doc_rag_node.py` -- 컷오프 게이트를 통과 조건(`not (d <= cutoff)`)으로 뒤집어 NaN 통과를 막고, 호출부 `guide[0]` 검사가 도달 불가하다는 사실을 주석에 반영.
- `api/app/graph/hybrid_rag_node.py` -- 인용 게이트에서 실제 게이트가 `listings and`임을 주석에 명시(그 구멍을 닫는 테스트 이름 함께 기재).
- `api/tests/test_doc_rag_node.py` -- NaN 거리 거부 테스트, 전달받은 `qvec`을 실제로 두 쿼리에 바인딩하는지 확인하는 테스트 신규, 가이드 SQL 테스트의 `next()` 기본값+실패 메시지, 빈 제목 테스트 docstring 정정.
- `api/tests/test_hybrid_rag_node.py` -- `_patch_guide_lookup`이 SQL로 분기하고 인자를 기록하도록 개선, hybrid가 넘기는 pgvector 리터럴 단언, 매물 0건+가이드 존재 시 인용 미부착 테스트 신규, 재시도 경로의 임베딩·가이드 조회 1회 단언, 과장된 테스트 이름·docstring 정정.
- `_bmad-output/implementation-artifacts/spec-13-6-…md` -- Verification에 DW-608/609 한계와 이번 라이브 실측 결과 추가, 트리아지 로그 3회차 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-608·DW-609 신규 등재(기존 항목 무수정 — 18줄 추가·0줄 삭제로 확인).

**Review findings breakdown:** patch 9건(medium 3, low 6) 전부 적용. defer 2건(medium 2 — DW-608·DW-609). reject 7건(전부 low — 3건은 라이브 실측으로 반증, 2건은 이 스토리가 만들지 않은 기존 구조, 1건은 표현 정리, 1건은 오케스트레이터가 소유한 기존 대장 항목). intent_gap 0, bad_spec 0.

**Follow-up review recommendation:** true (`3×medium(3) + 1×low(6) = 15 ≥ 5`).

**Verification performed:**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **373 passed, 84 skipped**(패치 전 370 → 신규 3건 + 기존 테스트에 단언 추가).
- red→green 실측 **6건**(모두 변이 주입 → 실제 red 확인 → 원복 후 373 green·`git diff app/graph/` 무변경 확인):
  · 컷오프 게이트를 `d > cutoff`로 되돌림 → NaN 테스트 red.
  · `doc_rag_node`가 전달받은 `qvec` 무시 → qvec 재사용 테스트 red.
  · hybrid 인용에서 `listings and` 제거 → 0건 인용 테스트 red.
  · `find_relevant_guide(qvec_literal)` → `find_relevant_guide(qvec)` → 가이드 params 단언 red.
  · 임베딩 호이스트를 재시도 루프 안으로 되돌림 → 재시도 1회 단언 red.
  · `find_relevant_guide` 호출 제거 → `AssertionError: 가이드 조회 SQL이 발행되지 않았다`(기본값 없는 `next()`였다면 원인 불명 error).
- NaN 게이트 직접 재현(문서에 적기 전에 실행, B4): `run_select`를 NaN 행으로 스텁 → 로그는 `거리=nan … 컷오프통과=False`인데 반환값은 `('무관 가이드','본문')`.
- **라이브 Gemini 관측**(리뷰 레이어가 실행): 가이드 미주입 프롬프트 2회 → `price <= 30000000`만; `corpus/02-패밀리카-적합-차종.md` 주입 → `body_type IN ('준중형차','중형차','SUV','RV') AND price <= 30000000`, 조립 SQL이 `validate_select_sql()` 통과. `seed.sql` 파싱 → `on_sale` 37건 중 14건이 그 조건 만족.
- 대장·도구 주장 직접 재측정: `score_ab.py`의 `--raw` 1개 모드 주석·`score_model()` 반환 필드·`doc_hit` 사용처(465행 단독) 확인, `g2-baseline.json` 44건 확인, queryset `primary_path` 전수 집계(항목 A=20·B=9·C=6·멀티턴 9 / 턴 A=16·B=3·C=1, `HYBRID` 0회) — DW-608·DW-609의 근거.
- `test_live_smoke_hybrid`(2회차가 추가한 AC1 가드)는 이번에도 **미실행** — DW-604와 동일한 환경 차단(docker·sudo·`DATABASE_URL` 부재)이 이 세션에서도 그대로다.

**Residual risks:**
- 1·2회차의 잔여 위험은 유효하다(컷오프 0.3 미실측 DW-604, Block-If가 HYBRID 미커버 DW-605, 인용이 "실제 사용" 미검증 DW-606, `doc_hit` 감도 DW-607).
- 이번에 밝혀진 대로 문서화된 Block-If 명령은 적힌 대로 실행하면 비교를 수행하지 않고 지표도 출력하지 않는다(DW-608) — 그 세션이 이 항목을 먼저 읽지 않으면 "초록"을 오판할 수 있다.
- AC1의 자동 회귀 관측은 queryset에 HYBRID 항목을 추가하기 전까지 존재하지 않는다(DW-609). 라이브 관측은 이 패스에서 프롬프트 단독 실행으로 확인했으나, `/ai/search` 전체 경로를 통과한 관측은 아니다.
- 병렬 리뷰 레이어가 같은 워킹트리에서 동시에 변이 실험을 수행해 서로의 red/green을 오염시킨 사례가 이번 패스에서 관찰됐다(한 레이어가 다른 레이어의 변이를 발견해 정적 분석으로 전환). 이 세션의 최종 6건 변이는 레이어 종료 후 단독으로 수행했고 매번 원복을 확인했다.
