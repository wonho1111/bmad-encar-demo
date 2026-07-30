# Epic 13 Context: AI 검색 RAG 고도화

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

AI 검색을 상용 수준으로 끌어올린다: 질문 의도를 4갈래(거절/되묻기/구조형/하이브리드)로 정확히 라우팅하고, 정형 조건(가격·차종 등)과 의미 조건(임베딩 유사도)을 한 쿼리로 조합하는 하이브리드 검색을 지원하며, 가이드 문서(차량 상식)를 검색 조건 확장에 실제로 활용하고, 애매한 질문엔 되묻기로 좁히고, 무관/법적 질문엔 정중히 거절한다. 이 모든 확장이 기존 보안장치(sql_guard·ai_readonly)와 판매완료 비노출을 뚫지 않고, 기존 AI 검색 시연이 회귀하지 않음을 회귀 하니스로 증명하면서 진행된다. 커넥션 풀 롤 격리는 Epic 8에서 이미 완료된 전제조건이다.

## Stories

- Story 13.1: sql_guard 하이브리드 정비 + G2 회귀 baseline
- Story 13.2: 4분기 라우팅 (REJECT/CLARIFY/SQL/HYBRID)
- Story 13.3: 하이브리드 검색 (SQL+벡터 단일쿼리)
- Story 13.4: 조건 좁혀 되묻기 (CLARIFY, 무상태)
- Story 13.5: 부드러운 거절 (REJECT, 고정 템플릿)
- Story 13.6: 가이드 문서 content 활용 (질의확장) + 거리 컷오프
- Story 13.7: LangSmith 트레이싱 (env만, 코드 변경 0)
- Story 13.8: RAG exit-gate 검증 (SM-F/SM-G/G2/CM-B)

## Requirements & Constraints

- 라우터는 질문을 4갈래로 분류한다: 무관/법적 질문 → 거절, 광범위/애매 질문 → 되묻기, 구조형 → 기존 Text-to-SQL, 조합형(정형+의미) → 하이브리드.
- 하이브리드는 단일 쿼리(구조조건 WHERE + 유사도 ORDER BY)로 조합한다(RRF 없음). 구조조건을 못 뽑으면 기존 벡터검색으로 폴백해 회귀 없이 처리한다.
- 신규 SQL도 예외 없이 sql_guard를 통과하고 `status='on_sale'`을 강제한다(보안 블로커). 판매완료 비노출 강제지점이 기존 3곳(RLS·sql_guard·문서 RAG 필터)에서 하이브리드 벡터 검색 경로가 추가되어 4곳이 된다 — 앱 레벨 필터링은 금지, 쿼리/DB 레벨에서만 막는다.
- 가이드 문서(12개)는 답변 문장을 생성하는 데가 아니라 검색 조건/가중치 확장(질의확장)에만 쓴다 — 답변 텍스트는 기존 결정론 방식을 유지한다. 청킹은 도입하지 않는다(문서 ≥20개 또는 문서당 ≥800토큰이 될 때까지 조건부 보류).
- 유사도 근거 채택에는 코사인 거리 컷오프를 둔다 — 임계값은 하드코딩이 아니라 회귀 질의셋 실측으로 확정한다(초기 후보 0.3, 배포 전 노이즈 부착률로 판정).
- 되묻기(CLARIFY)는 무상태다 — `interrupt()`/체크포인터 없이 되묻기 문장을 answer로 반환하고, 다음 사용자 메시지는 클라이언트가 이어붙여 기존 멀티턴 처리로 넘긴다. 최대 2~3턴까지만 허용(클라이언트가 횟수 추적), 초과 시 현재 조건으로 결과를 강제 제시한다.
- 거절(REJECT)은 고정 템플릿만 쓴다(LLM 자유 재작성 금지). 0건·거절 응답의 다양성은 문구 생성이 아니라 서버가 내려주는 구조화 사유 데이터(`narrowed_by`)를 결정론 템플릿이 조립해서 만든다.
- AI 응답 계약: `{ answer, listings, route: 'REJECT'|'CLARIFY'|'SQL'|'HYBRID', narrowed_by?, clarify?: { question, chips[] } }`. `clarify`는 route='CLARIFY' 전용이며 칩 렌더에 추가 LLM 호출은 없다.
- LangSmith는 무료 티어(월 5000 trace 하드캡)만 쓴다 — env 2개로 활성화, 코드 변경 없음. 평가 자동화·Deployment는 범위 밖. 목적은 라우팅 오분류·가드 차단·0건 응답·되묻기 빈도의 사후 관측이다.
- `/ai/search`는 로그인(JWT) 게이트를 유지한다 — 매물 열람은 비로그인 허용이어도 AI 검색은 실제 유료 API(임베딩·LLM) 호출을 발생시키는 "행동"이라 신원이 곧 과금 방어선이다. 하이브리드는 질의당 SQL 생성(LLM)과 임베딩을 함께 태워 비용이 커지므로(질의당 최대 4회 호출) 이 게이트를 완화하지 않는다.
- 검증 게이트는 모두 실측으로 통과해야 한다: G1(되묻기 과다발동 방지 — 명시조건 질의가 CLARIFY로 새면 실패), G2(회귀 — Phase B baseline 이하로 떨어지면 실패), SM-F(기존 AI 검색 시연 3종 유지), SM-G(신규 3분기 각 1개 이상 실동작), CM-B(sql_guard·ai_readonly·판매완료 비노출 유지).

## Technical Decisions

- sql_guard 확장은 `embedding`/`vector`를 식별자 화이트리스트로 넣지 않는다(그러면 두 토큰이 SQL 어디에 나와도 통과해 안전하지 않다). 대신 `ORDER BY embedding <=> %s::vector`라는 절 모양 전체를 그 위치(문장 끝 직전, 뒤에 `LIMIT`/`OFFSET`만 허용)에서만 통과시키는 위치-스코프 화이트리스트다. 그 밖의 위치에 나오는 `embedding`·`vector`는 여전히 거부된다.
- 벡터절은 LLM이 아니라 코드가 붙인다 — LLM은 WHERE 구조조건만 생성하고, `ORDER BY embedding <=> %s::vector`와 `LIMIT <정수>`는 코드가 덧붙인다. 자리표시자는 이 프로젝트의 드라이버(psycopg) 기준 `%s` 바인드 파라미터이며 질의 임베딩을 받는다. `LIMIT`은 바인드하지 않고 코드가 정수 리터럴로 붙인다.
- 4분기 라우팅은 `RouterDecision` Literal·`_fallback_route`·`_route_decision` 3곳을 항상 락스텝으로 갱신한다 — 하나만 빠지면 신규 라우트가 기존 분기에 조용히 흡수되는 회귀가 생긴다.
- AI DB 읽기는 쿼리 단위 트랜잭션 내 롤 격리(`BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`, 세션 레벨 `SET ROLE` 금지)를 전제로 한다 — 격리 자체는 Epic 8에서 이미 완료됐고, Epic 13은 그 위에 하이브리드 경로만 얹는다.
- AI 입력 500자 상한은 서버측에서 검증한다(클라이언트 상한만으론 우회 가능하므로).
- `narrowed_by`는 저장단위(원) 정규화 술어 배열이다(예: `["price<=30000000"]`, 만원 표시단위 아님). 한국어 렌더링은 answer_node의 결정론 템플릿이 책임진다.
- 재사용 우선 원칙: 기존 LangGraph StateGraph·corpus 로더·임베딩 파이프라인에 노드만 추가한다. `interrupt()`/체크포인터 등 무거운 신규 인프라는 도입하지 않는다(되묻기는 무상태로 구현).

## UX & Interaction Patterns

- 칩은 스타일이 다른 2종이다 — 상시 제안칩(petrol 반투명, 입력바 위 상시 노출)과 맥락 칩(되묻기·거절 전용, 탭 시 petrol 채움 "선택됨" 상태로 전환). 맥락 칩 탭은 자유 타이핑과 항상 동등한 입력 경로이며, 자유 타이핑은 칩 존재와 무관하게 항상 병존한다.

## Cross-Story Dependencies

- 13.1(sql_guard 정비 + G2 baseline)이 13.2~13.7 전체의 선행 조건이다.
- 13.3(하이브리드)은 13.2가 만드는 HYBRID 분기와 13.1의 sql_guard 정비가 둘 다 있어야 진행 가능하다(없으면 보안 블로커).
- 13.4(되묻기)는 13.2가 만드는 CLARIFY 분기를 전제하며, 응답 계약의 `clarify` 필드·칩 렌더와 맞물린다.
- 13.6(가이드 활용)과 13.5(거절)는 둘 다 answer_node의 응답 조립 로직을 건드리므로 작업 순서에 주의한다.
- 13.8(exit-gate)은 13.1~13.7이 모두 구현된 뒤에만 의미가 있고, G2 미통과 시 에픽을 종료할 수 없다.
- 이 에픽은 Epic 8에서 완료된 커넥션 풀 롤 격리(AC-DB-1)를 전제조건으로 삼는다 — 재작업하지 않는다.
