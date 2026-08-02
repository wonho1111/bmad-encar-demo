# AI 검색 데모 질의셋 (OI5)

이 문서는 라우터(`router_node`)와 네 경로(SQL/HYBRID/CLARIFY/REJECT, 13.2 4분기 라우팅)의
기대 동작을 명세하는 **단일출처**다.
라우터 프롬프트 예시·단위 테스트 케이스·4.8 검증 매트릭스가 이 표를 참조한다.

- **SQL (구조형, FR13/FR14)**: 가격·차종·연식·색상·지역·주행거리·연료 등 **명시적 조건만** → Text-to-SQL.
- **HYBRID (조합형, FR44)**: 명시적 조건 + 용도·느낌 조건이 **함께** → 구조조건 추출 + 벡터검색(가이드 인용).
- **CLARIFY (질적형, FR15/FR46)**: 명시적 조건 없이 용도·느낌만 있다 → **되묻기(clarify), 매물 아님**.
- **REJECT (매물 무관, FR16)**: 중고차 검색과 무관한 잡담·상식(금융·세금·보험 일반지식 포함) →
  **정중한 거절 + 검색 유도**(listings 빈 목록).

회색지대(LLM 판정이 갈릴 수 있는 경계 케이스)는 **하나의 경로로 정해지지 않는다** — 허용 경로가
행마다 다르므로 아래 표 ③을 정본으로 본다. 명시 조건이 전혀 없을 때만 CLARIFY로 되묻는 것이고
(빈손보다 되묻기가 낫다, 13.4), 가격·인승 같은 조건이 이미 있으면 SQL/HYBRID가 정답이다.
(✎ 13.8 4차 리뷰 정정 — 여기 "회색지대는 CLARIFY로 보내 되묻는다"라고 무조건으로 적혀 있었으나
표 ③의 3행 중 2행은 CLARIFY가 **오답**이라 같은 문서 안에서 값이 갈렸다. 구어휘 시절의
"회색지대 → B" 문장을 기계적으로 번역하면서 생긴 모순이다.)

응답 계약은 모든 경로 공통으로 `{answer, listings, route, narrowed_by?, clarify?}`다(정본은 `docs/conventions.md` §4).
`clarify`는 route=CLARIFY 전용이다. 0건이어도 빈손이 아니라 조건 완화/재질문 안내를 준다(FR17).

> **이 표들의 "기대 분류"가 어디서 왔나** (13.8 3차 리뷰 추가 — 근거 강도가 행마다 다르다):
> 아래 12행 중 **실측 라우트가 있는 것은 4행뿐**이다 — `3천만원 이하 흰색 SUV`(SQL) ·
> `패밀리카로 무난한 거`(CLARIFY) · `오늘 날씨 어때?`(REJECT)는 `tests/test_live_smoke.py`가
> 라이브로 route를 단언하고, `출퇴근용으로 편한 차 추천해줘`는 회귀 큐리셋 CL4(CLARIFY)와
> 같은 문자열이다. **나머지 8행은 규칙에서 연역한 기대값이지 관측값이 아니다** — 결정론
> 테스트는 `_patch_route`로 경로를 강제 주입하므로 이 행들이 실제로 어디로 가는지는
> 검증되지 않는다(열린 항목 DW-576). 표 ③(회색지대)만은 세 행 모두 큐리셋 실측 기반이다.

---

## ① 구조형 → SQL

| 질의 | 기대 분류 | 기대 결과 요지 |
|---|---|---|
| "3천만원 이하 흰색 SUV" | SQL | `price <= 30000000 AND color='흰색' AND body_type='SUV' AND status='on_sale'` 매물 카드. |
| "2020년 이후 제네시스" | SQL | `manufacturer='제네시스' AND year >= 2020` 매물. |
| "10만km 미만 디젤" | SQL | `mileage < 100000 AND fuel='디젤'` 매물. |
| "서울 경차 보여줘" | SQL | `region='서울' AND body_type='경차'` 매물. |

## ② 질적형 → CLARIFY (되묻기, 매물 아님)

| 질의 | 기대 분류 | 기대 결과 요지 |
|---|---|---|
| "패밀리카로 무난한 거" | CLARIFY | 명시 조건 0개 → 되묻기(clarify 질문 + 칩), listings는 빈 배열. |
| "초보운전자에게 좋은 차" | CLARIFY | 되묻기(용도만 있고 명시 조건 없음). |
| "출퇴근용으로 편한 차 추천해줘" | CLARIFY | 되묻기(느낌·용도 표현뿐, 명시 조건 없음). 회귀 질의셋 CL4와 같은 문자열이라 실측 라우트가 있다(CLARIFY). |
| "가성비 좋은 차 없을까?" | CLARIFY | 되묻기("가성비"는 숫자 예산이 아니라 구조조건으로 못 씀). |

## ③ 회색지대 (LLM 판정이 갈릴 수 있는 경계 케이스)

| 질의 | 기대 분류 | 기대 결과 요지 |
|---|---|---|
| "2500만원 이하 해치백 있어?" | HYBRID 또는 SQL | "해치백"은 DB에 없는 차형 용어라 가이드 매핑(소형차·준중형차)이 필요하지만, 겉보기엔 구조조건뿐이라 SQL로 봐도 데모상 허용. |
| "6천만원 이하로 7명 이상 다 탈 수 있는 가족차 보여줘" | HYBRID 또는 SQL | "7명 이상"이 이미 명시 조건이라 SQL만으로도 정답이 나오는 케이스 — 가이드 없이도 안 망가지는지 확인. |
| "주행거리 많은 차 사도 괜찮을까?" | CLARIFY 또는 REJECT | 지식형 질문(사고이력·주행거리 판별법)이라 매물 답변은 범위 밖 — 되묻기·거절 둘 다 정답, 지식 설명이나 매물 목록이 나오면 오답. |

> 회색지대는 LLM 판정이 갈릴 수 있다. 합격 기준은 **각 행의 "기대 분류"에 적힌 경로 중 하나로 가고, 그 경로가 내놓기로 한 것을
> 실제로 내놓는 것**이다 — SQL/HYBRID면 매물 카드, CLARIFY면 되묻기 칩, REJECT면 고정 거절 문구(+빈 목록).
> 행에 없는 경로로 가면 불합격이다(예: 가격·인승이 명시된 위 두 질의가 거절로 새거나, 지식형 질의가 매물 목록을 주는 것).
> 세 질의는 회귀 질의셋(`docs/ai-ab-test-queryset.json`)의 H6·H7·CL7과 같은 문자열이고, 위 허용 경로는 그 항목의
> `acceptable_paths`와 일치한다. 코드 미러는 `tests/demo_queries.py`의 `GRAY_ALLOWED`다.

## ④ 매물 무관 → REJECT (가드 거절)

| 질의 | 기대 분류 | 기대 결과 요지 |
|---|---|---|
| "오늘 날씨 어때?" | REJECT | "저는 중고차 찾기를 도와드리는 차장님이에요 🚗 …" + `listings: []`. 문구 정본은 `app/graph/guard_node.py`의 `_GUARD_ANSWER`(여기 적힌 건 사본이다). |
| "파이썬 코드 짜줘" | REJECT | 정중한 거절 + 검색 유도. 상식/코드 Q&A 미제공(FR16). |
| "안녕" | REJECT | 인사도 거절 문구로 검색 유도. |
| "1+1은 뭐야?" | REJECT | 상식 질의 거절. |

---

## ⑤ 멀티턴 맥락 → 질의 재작성 후 경로 분류 (FR18)

직전 대화를 클라이언트가 `context`(턴 배열 `{role, content}`)로 동봉하면, 서버는 **그래프 앞단의 맥락화 노드**(`contextualize_node`)가 후속 질의를 **혼자서도 뜻이 통하는 독립 질의**로 재작성한 뒤, 그 재작성 질의를 평소처럼 라우터(4분기)에 흘린다. 서버는 대화를 저장하지 않는다(무상태 — 새로고침/세션 종료 시 초기화).

**요점은 재작성 결과다.** 재작성이 조건을 접어 넣으면 그 독립 질의는 ①~④ 표와 **같은 규칙**으로 분류된다 — 즉 여기 "기대 경로"는 별도 규칙이 아니라 위 표의 결과다.

| 직전 대화(요지) | 후속 질의 | 기대 재작성(독립 질의) | 기대 경로 |
|---|---|---|---|
| user "패밀리카로 무난한 거" / assistant "○○ 등 추천" | "그 중 더 싼 거" | "패밀리카로 무난한 차 중 더 저렴한 매물" | HYBRID 또는 SQL (최상급·정렬 표현은 구조조건이다) |
| user "3천만원 이하 SUV" / assistant "△△ 매물 N건" | "흰색만 보여줘" | "3천만원 이하 흰색 SUV" | SQL |
| user "초보운전자에게 좋은 차" / assistant "□□ 추천" | "그럼 전기차로" | "초보운전자에게 좋은 전기차 추천" | HYBRID (명시 조건 "전기차" + 용도 "초보운전자") |

> ⚠️ 첫 행·셋째 행의 **원 질의**(재작성 전)는 표 ②가 CLARIFY로 규정한 것이다 — 모순이 아니다.
> 맥락 재작성이 조건을 붙여 주기 때문에 후속 질의는 다른 갈래로 간다. 그게 이 절의 요지다.
> (13.8 3차 리뷰 정정: 이 표만 구어휘 A/B/C로 남아 있어 같은 문자열의 기대 경로가
> 문서 안에서 두 값으로 갈렸다. 최상급·교체요청 라우팅은 Story 13.9가 안정화 대상으로
> 다루는 기지 불안정이다 — DW-611·612.)

- **단일턴(맥락 없음)**: `context`가 없거나 비면 맥락화 노드는 **LLM을 부르지 않고 원 질의를 그대로** 흘린다(4.5까지와 동일, 비용·지연 0).
- **안전장치**: 재작성 결과가 비거나 LLM 호출이 실패하면 **원 질의로 폴백**(빈손 금지). 직전 대화에 없는 새 조건·매물은 지어내지 않는다(지시어만 치환).
- **무상태 보증**: 맥락은 매 요청의 `context`에서만 온다. 같은 서버라도 `context` 없는 요청은 직전을 기억하지 못한다(FR18).
- **`context` 입력 형태**(웹/Flutter가 보낼 단일출처): `[{"role":"user","content":"…"}, {"role":"assistant","content":"…"}]`. 최대 12턴, 각 content 최대 2000자(초과 시 422).

---

## 차형(body_type) 용어 매핑 (SQL 생성 참고)

자연어 차형 표현을 DB `body_type` 허용값으로 매핑한다(단일출처: `sql_rag_node` 프롬프트).

| 자연어 | DB 매핑 |
|---|---|
| 세단 | `body_type IN ('준중형차','중형차','대형차')` |
| SUV | `body_type = 'SUV'` |
| 경차 | `body_type = '경차'` |
| 데모에 없는 차형(해치백·쿠페 등) | 무리한 매핑 금지 — 가격·기타 조건만 적용 |

> `body_type` 허용값: 경차·소형차·준중형차·중형차·대형차·스포츠카·SUV·RV·경승합차·승합차·화물차·기타.
> 정규화 단위: 주행거리 "만km" → ×10000, 가격 "천만원"=10,000,000 / "만원"=10,000.

---

## 4.8 검증 매트릭스 (SM3·CM1·CM2 합격 판정)

이 질의셋이 SM3·CM1·CM2 합격임을 **재현 가능한 pytest**로 못박는다. 질의 문자열·기대 경로는
`api/tests/demo_queries.py`가 위 표 ①②③④를 그대로 미러링한다(단일출처, drift 금지).

쿼터 보호: 판정은 라이브 LLM에 매번 의존하지 않는다.
- **SM3·CM1** — 라우터·경로 노드를 모킹해 분기·계약을 LLM/DB 없이 결정론적으로 검증.
- **CM2** — `sql_guard`는 순수 함수라 키 없이 항상 결정론적으로 완전 검증.
- 라이브 동작은 별도 스모크에서 소량(3건 이하)만 확인하며 기본 실행에서는 스킵된다.

| 판정 | 대상 질의 | 기대 | 검증 테스트(`api/tests/`) |
|---|---|---|---|
| SM3 | ① 구조형(SQL) | SQL 경로가 매물 카드 반환(빈손 아님) | `test_demo_acceptance.py::test_sm3_pathA_returns_listings` |
| SM3 | ② 질적형(CLARIFY) | CLARIFY 경로가 되묻기(clarify 페이로드) 반환(13.4 — 매물 아님) | `test_demo_acceptance.py::test_sm3_pathB_returns_listings` |
| SM3 | ③ 회색지대 | **질의별 허용 경로**(표 ③ = `GRAY_ALLOWED`)에서만 합격 — SQL/HYBRID는 매물, CLARIFY는 되묻기 칩, REJECT는 거절 문구+빈 목록. 허용 밖 경로는 불합격 | `test_demo_acceptance.py::test_sm3_gray_zone_allowed_routes_are_not_dead_ends`, `::test_gray_allowed_matches_shipped_queryset` |
| SM3 | SQL 가드 통과 | 세단 IN-매핑 SQL이 sql_guard를 실제 통과 | `test_demo_acceptance.py::test_sm3_pathA_real_guard_passes_generated_sql` |
| CM1 | ④ 무관(REJECT) | 전부 빈 목록 + 정중한 거절 문구 | `test_demo_acceptance.py::test_cm1_unrelated_rejected_via_graph`, `test_cm1_count_all_unrelated_rejected` |
| CM2 | 위반 SQL 코퍼스 | 범위밖 SQL 0건 통과(전부 실행 전 차단) | `test_demo_acceptance.py::test_cm2_violating_sql_is_blocked`, `test_cm2_zero_violations_pass_through` |
| CM2 | 정상 SQL 대조군 | 정상 SELECT는 통과(과차단 아님) | `test_demo_acceptance.py::test_cm2_valid_sql_still_passes` |
| 라이브 | SQL·CLARIFY·REJECT·HYBRID 각 1건 | 실물 동작 눈 확인(쿼터-세이프, 기본 skip) | `test_live_smoke.py`(`RUN_LIVE_SMOKE=1`로 활성) |

> 실행: `cd api && pytest`(전체) 또는 `pytest tests/test_demo_acceptance.py`(판정만). 라이브 스모크는
> `RUN_LIVE_SMOKE=1`(+ `GEMINI_API_KEY`·`DATABASE_URL`)일 때만 돈다. 429/키부재는 실패가 아닌 skip이다.
