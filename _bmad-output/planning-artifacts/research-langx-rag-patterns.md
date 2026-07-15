# 리서치: RAG(검색증강생성, Retrieval-Augmented Generation) 고도화 패턴 — LangGraph 라우팅·하이브리드 검색·LangSmith

- 조사일: 2026-07-11
- 조사 방법: `agent-reach` 스킬 (Exa 검색, 공식 문서 우선)
- 대상 코드: `api/app/graph/*` (현재 A/B/C 3분기 StateGraph 실측 확인 — 아래 "현재 구현 스냅샷" 참조)
- 범위 한정: LangChain/LangGraph는 버전 변화가 빨라 **2025~2026 공식 문서(docs.langchain.com) 기준**만 채택. 오래된 블로그 스니펫은 배제.

---

## 0. 현재 구현 스냅샷 (리서치 대비용)

`api/app/graph/graph.py`는 이미 `StateGraph` + `add_conditional_edges`로 3분기(A=Text-to-SQL, B=벡터 전용 문서 RAG, C=거절)를 구현해 두었다.

- 라우터(`router_node.py`): Gemini 구조화 출력(`Pydantic Literal["A","B","C"]`) 1회 호출 + 코드가 결과를 재검증(형식이탈 시 결정론적 폴백)하는 "LLM 분류 + 코드 이중 검증" 패턴을 이미 쓰고 있음. 이건 아래 §1의 모범사례와 일치한다.
- 경로 B(`doc_rag_node.py`)는 **벡터 검색만** 한다(SQL 필터 없음, 코드가 `status='on_sale'` WHERE만 하드코딩). 즉 "하이브리드"가 아니라 순수 벡터 검색 + 가이드 문서 1건을 부가 설명으로만 붙이는 수준.
- 가이드 문서(`guide_documents`, 12개)는 **문서 전체를 통째로 1개 임베딩**한다(`backfill_embeddings.py`) — 청킹이 전혀 없음.
- 되묻기(clarification)·human-in-the-loop 노드는 **아직 없음**.

사용자가 원하는 4분기(① 거절 ② 되묻기 ③ SQL ④ SQL+벡터 하이브리드+가이드)로 가려면, 기존 C를 유지하고 B를 "④ 하이브리드"로 승격 + 신규 "② 되묻기" 노드를 추가하는 구조가 자연스럽다. 상세는 §8.

---

## 1. LangGraph 라우팅·다분기 설계 모범사례

**패턴 두 가지, 공식 문서가 명시적으로 구분:**

1. **`add_conditional_edges` + 별도 라우팅 함수** — 그래프 구조가 노드와 분리되어 시각화·디버깅이 쉬움. 우리 현재 구현이 이 방식.
2. **`Command` 객체를 노드가 직접 반환** (`Command[Literal["node1","node2"]]`) — 노드 자신이 라우팅을 결정. 상태 업데이트와 분기 결정을 한 번에 처리해 그래프의 엣지 선언이 줄어든다. LangChain 공식 튜토리얼(`thinking-in-langgraph`)이 실제 프로덕션 패턴 예시(이메일 분류 에이전트)로 이 방식을 채택.

의도 분류 노드 모범사례(공식 문서 인용):
> "Use `llm.with_structured_output()`로 분류 결과를 구조화하고, 분류 결과에 따라 `Command`로 다음 노드를 정한다."

우리 프로젝트는 이미 이 패턴(구조화 출력)을 쓰고 있어 그대로 4분기로 확장 가능. `add_conditional_edges` 딕셔너리를 `{"A": "sql", "B": "doc", "C": "guard"}`에서 `{"REJECT": "guard", "CLARIFY": "clarify", "SQL": "sql", "HYBRID": "hybrid"}` 형태로 늘리면 된다 — LangGraph 자체는 분기 수 제한이 없다.

**Router vs Supervisor 구분** (공식 `multi-agent/router` 문서): 라우터는 "무상태(stateless) 전처리 단계"로 한 번의 LLM 호출/규칙으로 분류 후 위임하는 패턴. Supervisor는 멀티턴 대화 맥락을 유지하며 반복적으로 어디로 갈지 재판단하는 패턴. 우리 질의는 단발성 검색 의도 분류이므로 **라우터 패턴이 적합**(Supervisor는 과설계).

출처: https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph , https://docs.langchain.com/oss/python/langchain/multi-agent/router , https://docs.langchain.com/oss/python/langgraph/use-graph-api

---

## 2. 되묻기(Clarification) — interrupt() / human-in-the-loop

공식 문서(`docs.langchain.com/oss/python/langgraph/interrupts`)가 정의하는 핵심 메커니즘:

- `interrupt(payload)`를 노드 안에서 호출하면 그래프 실행이 그 지점에서 멈추고, `payload`(JSON 직렬화 가능한 아무 값)가 호출자에게 반환된다. 체크포인터(checkpointer)가 상태를 저장하고 무기한 대기한다.
- 재개는 `Command(resume=답변)`으로 그래프를 다시 invoke — 이 값이 `interrupt()` 호출의 반환값이 된다.
- **필수 인프라**: 체크포인터(checkpointer, 상태 영속화 계층) + `thread_id`(스레드 식별자, 어느 대화의 상태를 재개할지 지정). 이게 없으면 `interrupt()`가 동작하지 않는다.
- **함정(공식 문서가 강조)**: 재개 시 노드는 **처음부터 다시 실행**된다(정확히 멈춘 줄부터가 아님). 따라서 `interrupt()` 이전의 코드는 부작용이 없어야(멱등) 하고, `while True` 루프 안에서 `interrupt()`를 여러 번 부르면 재개마다 이전 반복이 전부 재실행되는 지수적 재실행 버그가 생긴다. **올바른 패턴**: 재질문할 내용을 state에 저장하고, 노드당 `interrupt()` 1회만 호출한 뒤, 유효하지 않으면 `add_conditional_edges`로 같은 노드에 다시 루프시킨다(state 갱신 → 재진입, 노드 내부 반복 아님).

**우리 "너무 애매한 질문 → 조건 좁혀 되묻기" 시나리오 적용:**
```python
def clarify_node(state: SearchState) -> Command[Literal["router", END]]:
    suggestion = build_clarify_question(state["query"])  # 예: "예산대나 차종을 알려주시겠어요?"
    answer = interrupt({"question": suggestion, "original_query": state["query"]})
    # 재개 시 answer = 사용자가 준 추가 조건 문자열
    return Command(update={"query": f'{state["query"]} {answer}'}, goto="router")
```
API 서버(FastAPI, stateless HTTP) 특성상 `interrupt()`를 쓰려면 **DB/Redis 기반 체크포인터**(예: `AsyncPostgresSaver`)와 `thread_id`(세션/대화 ID)를 프런트가 유지해야 한다. 순수 REST 단발 요청 구조에서는 인프라 부담이 크다.

**실전 대안(더 단순, 우리 규모에 적합)**: `interrupt()`를 쓰지 않고, 그래프가 "되묻기 응답"을 그냥 **최종 답변으로 반환**하고 프런트가 그걸 채팅 UI에 후속 질문처럼 띄운 뒤, 사용자의 다음 메시지를 **기존 멀티턴 `contextualize_query`(4.6에서 이미 구현된 맥락 흡수 로직)**로 이어붙여 다시 그래프를 호출하는 방식. 이러면 체크포인터 없이도 "되묻기 → 답변 → 조건 좁혀 재검색" 흐름이 만들어진다. `interrupt()`는 그래프 **한 번의 실행 안에서** 사람 입력을 기다려야 하는 경우(승인 워크플로 등)에 강점이 있지만, 우리처럼 "그래프 호출 자체가 매 HTTP 요청 단위"인 구조에서는 **불필요한 복잡도**다.

출처: https://docs.langchain.com/oss/python/langgraph/interrupts , https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/

---

## 3. 하이브리드 검색 (Text-to-SQL + pgvector 조합)

공식/실무 패턴은 명확히 3갈래로 수렴한다(EnterpriseDB aidb 공식 문서, Tiger Data, Alibaba Cloud AnalyticDB 문서 교차 확인):

1. **벡터 + 관계형 필터 (Vector + relational filter)** — SQL `WHERE`와 벡터 `ORDER BY`를 **같은 쿼리 레벨**(CTE로 분리하지 않음)에 둬야 pgvector의 iterative index scan이 작동해 필터링 후에도 `LIMIT`만큼 결과가 채워진다. 우리 `doc_rag_node.py`가 이미 `WHERE status='on_sale' ... ORDER BY embedding <=> %s`를 이 방식으로 쓰고 있다(정답 패턴).
2. **RRF(Reciprocal Rank Fusion, 상호 순위 융합)** — SQL 키워드/구조 검색과 벡터 검색을 **독립적으로** 실행해 각각 Top-N을 뽑고, `1/(k+rank)` (k=60 관행값) 점수를 합산해 재정렬. 순위만 쓰므로 스케일이 다른 두 점수(SQL 매칭 점수 vs 코사인 거리)를 정규화할 필요가 없어 실무에서 가장 널리 쓰임.
3. **가중 선형 융합(Weighted linear fusion)** — 두 점수를 `[0,1]`로 정규화 후 `w1*sql_score + w2*vec_score`. RRF보다 튜닝 노력이 크지만 "이 질의는 키워드가 더 중요/의미가 더 중요"를 명시적으로 제어 가능(예: 정확한 옵션명 매칭엔 SQL 가중치↑).

**우리 시나리오("SQL로 후보 좁히고 벡터로 재정렬")에 가장 맞는 건 패턴 1의 변형**: 구조 조건(가격·연식·차종 등)을 SQL `WHERE`로 먼저 걸고, 그 후보군 안에서 `ORDER BY embedding <=> query_vec`로 의미 재정렬. 이건 이미 `sql_guard`가 만드는 SQL에 벡터 정렬 절만 얹으면 되는 **가장 적은 변경**으로 "④ 조합형" 경로를 만들 수 있는 방법이다 — 별도 RRF 스코어 결합 로직 없이 **CTE 없는 단일 쿼리**로 구현 가능.

**주의점(문서 공통 지적)**:
- `hnsw.iterative_scan = relaxed_order`를 켜지 않으면, 필터가 선택적(selective)일 때 벡터 인덱스가 `LIMIT`보다 적은 결과를 반환할 수 있음 — 우리 코드 주석(§0)이 이미 이 위험을 인지하고 있음(현재는 42/44건이라 리스크 낮다고 판단, 향후 매물 수가 늘면 재검토 필요).
- 필터가 매우 선택적(전체의 1% 미만)이면 부분 HNSW 인덱스(`CREATE INDEX ... WHERE ...`)를 고려.
- RRF는 "필터로 SQL 결과가 0건이어도 벡터 쪽 결과는 그대로 나온다"는 특성이 있어(FULL OUTER JOIN) 조건이 너무 좁아 SQL이 0건일 때 자연스럽게 벡터 검색으로 성능 저하(graceful degradation)한다 — 우리 FR17(0건 안내) 로직과 상호작용을 설계 시 고려해야 함.

출처: https://www.enterprisedb.com/docs/aidb/latest/knowledge-bases/hybrid-search/query-patterns/ , https://www.tigerdata.com/blog/elasticsearchs-hybrid-search-now-in-postgres-bm25-vector-rrf , https://www.alibabacloud.com/help/en/analyticdb/analyticdb-for-postgresql/user-guide/fusion-search-use-guide , https://rivestack.io/blog/hybrid-search-pgvector-postgres

---

## 4. 다중 코퍼스 RAG — 매물 임베딩 vs 가이드 문서 선택적 참조

학술 최신 연구(2025)와 실무 프레임워크(KIMAs, arxiv 2502.09596)가 공통으로 제시하는 "언제 두 번째 코퍼스를 참조할지" 판단 방법 3가지:

1. **임베딩 클러스터 라우팅 (KIMAs 방식)** — 각 코퍼스(매물 vs 가이드)의 청크 임베딩을 클러스터링해 중심점(centroid)을 만들고, 질의 임베딩과 각 코퍼스 중심점의 유사도를 비교해 top-K 코퍼스만 활성화. LLM 호출 없이 임베딩 유사도만으로 판단 가능해 **빠르고 저렴**하지만, 소규모 코퍼스(우리처럼 가이드 12개)에는 클러스터링 자체가 무의미할 만큼 데이터가 적다.
2. **점수 임계값(threshold) 방식** — 가이드 문서 벡터 검색을 항상 실행하되, 최상위 결과의 코사인 유사도가 임계값(예: 0.75) 이상일 때만 답변에 포함. **우리 코드가 이미 절반쯤 이 방식**(`doc_rag_node.py`가 가이드 1건을 항상 조회해 있으면 붙이는데, 임계값 없이 무조건 붙임 — 유사도가 낮아도 붙는 문제가 있을 수 있음).
3. **라우터가 판단(LLM 분류)** — 질의 분류 단계에서 "이 질의가 가이드 문서 성격(예: 초보자 조언, 구매 시 체크리스트)인지"까지 함께 판단해 route 값에 반영. 우리 4분기 설계의 "④ 조합형"이 바로 이 접근.

**우리 규모(가이드 12개, 매물 ~100건)에 대한 권고**: 클러스터링은 과설계. **임계값 방식**을 최소 변경으로 추천 — `doc_rag_node`가 이미 가이드를 조회하니, 코사인 거리가 일정 값(예: 0.3, `<=>`가 거리라 값이 작을수록 유사) 이하일 때만 answer에 붙이는 **1줄짜리 조건 추가**로 "관련 없는 가이드를 억지로 붙이는" 노이즈를 줄일 수 있다.

출처: https://arxiv.org/pdf/2502.09596 (KIMAs), https://arxiv.org/pdf/2505.23052 (RAGRouter — 참고용, 우리 규모엔 과설계)

---

## 5. 가이드 문서 청킹·임베딩 전략

**업계 컨센서스(NVIDIA 실증 벤치마크 + Atlan 2026 가이드 교차 확인):**

- **범용 기본값**: 청크 512 토큰 내외, 오버랩 10~20%(업계 관행, NVIDIA 실측도 15%가 FinanceBench에서 최적). 극단적으로 작은(128토큰) 청크와 큰(2048토큰) 청크 모두 성능이 떨어짐 — "중간이 최적"인 패턴이 데이터셋 전반에서 일관됨.
- **문서 성격별**:
  - 사실형(factoid) 질의 위주 → 작은~중간 청크(256~512토큰).
  - 복잡한 분석형 질의(우리 "패밀리카로 무난한 거" 같은 맥락형 질문에 가까움) → 큰 청크(1024토큰) 또는 **페이지/섹션 단위** 청킹이 더 정확.
  - 프로덕션 표준(2025~2026)은 **계층형 부모-자식(hierarchical parent-child) 청킹** — 작은 자식 청크(128~256토큰)로 정밀 검색하고, 검색되면 더 큰 부모 청크(512~1024토큰)를 LLM 컨텍스트로 반환. "검색 정밀도 vs 생성 시 맥락 손실"의 트레이드오프를 해결하는 현재 업계 기본 패턴.
- **메타데이터**: 최소한 원문서 제목·섹션 제목·위치(순번)를 청크에 붙여야 "왜 이 청크가 왔는지" 근거 표시(예: "참고: {가이드 제목}")가 가능. 업계에서는 소유자·최신성·분류(민감정보 등)까지 붙이지만, 이건 엔터프라이즈 거버넌스용이라 우리 규모엔 불필요.

**우리 프로젝트에 대한 현실적 판단**: 현재 가이드 문서는 **12개, 각각 통째로 1개 청크(임베딩)**. NVIDIA 벤치마크의 "page-level chunking이 전반적으로 가장 안정적"이라는 결론과 사실상 부합한다 — 가이드 문서 하나가 A4 1페이지 안팎 분량이라면, 지금 방식(문서=청크 1개)이 이미 "page-level chunking"과 다름없다. **문서당 분량이 500~800토큰을 넘지 않는 한 청킹 도입은 불필요한 복잡도**(A2 단순함 우선 원칙과 일치). 만약 가이드 문서가 늘어나거나(수십 개 이상) 문서 하나가 여러 주제를 다루게 되면, 그때 섹션 단위(마크다운 `##` 헤딩 기준) 청킹으로 전환 — 오버랩 없이 헤딩 경계로만 나눠도 충분(문서 구조가 이미 논리적으로 분리돼 있으므로).

출처: https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/ (NVIDIA 실측 벤치마크, 2025-06), https://atlan.com/know/chunking-strategies-rag/ (2026-05), https://github.com/microsoftdocs/architecture-center (Azure RAG 청크 보강 가이드)

---

## 6. LangSmith — 무엇을 주나, 도입 위험도·가치 (2026-06 기준 가격)

**제공 기능**: 트레이싱(각 LLM 호출·툴 호출·그래프 노드 실행을 시각화), 온라인/오프라인 평가(eval), 프롬프트 관리, 배포(Deployment/Engine/Fleet — 유료 상위 기능), 관측(Observability & Monitoring).

**가격 구조(공식 페이지 + 2026-06 3자 검증 기사 교차 확인, 옛 자료와 다름 주의):**

| 플랜 | 가격 | 좌석 | 포함 베이스 트레이스(base trace)/월 |
|---|---|---|---|
| Developer(무료) | $0 | 1 | 5,000건/월 (카드 미등록 시 5,000건 하드 캡) |
| Plus | $39/좌석/월 | 무제한 | 10,000건/월 |
| Enterprise | 별도 협의 | 별도 | 별도 |

- **트레이스(trace)의 정의가 중요**: "1회 그래프 실행"이 1 trace다. 그 안에 LLM 호출 여러 번·노드 여러 개가 있어도 1건으로 카운트 — 우리 4분기 그래프(라우터 1회 + 경로 노드 1회 + answer 노드)는 호출당 1 trace.
- 초과 시 **베이스(14일 보관)** $2.50/1000건, **확장(400일 보관)** $5.00/1000건. 평가(eval) 실행도 trace로 과금된다는 점을 놓치기 쉬움(예: 야간 평가셋 2000건 돌리면 그것만으로 월 60,000 trace ≈ 무료 티어를 훌쩍 넘음).
- 옛 자료(옛 가격 $0.50/1000건)를 인용하는 글이 많으니 **2026-06 갱신 가격($2.50/$5.00)이 최신**임에 주의.

**우리 프로젝트(소규모 데모, 상용 지향)에 대한 도입 판단:**

- **가치**: 지금 `router_node`가 "LLM이 A/B/C 밖 값을 뱉는" 함정을 코드로만 방어하고 있는데, LangSmith 트레이싱을 붙이면 실제 운영 중 **라우팅 오분류·SQL 가드 차단·0건 응답 빈도**를 사후에 눈으로 확인할 수 있다(현재는 `logger.info`/`logger.warning`뿐이라 로그를 뒤져야 함). 4분기로 늘어나면 분기별 분포·되묻기 발생 빈도를 보는 것도 유용.
- **위험**: (1) 과금 트리거 지점(eval 실행이 trace로 잡힘)을 모르고 쓰면 예상 밖 청구서가 나올 수 있음. (2) SDK 추가 의존성 + `LANGCHAIN_TRACING_V2=true` 환경변수/API 키 관리 부담. (3) 데모 규모(사용자 소수, A/B 질의셋 44개 수준)에서는 5,000건/월 무료 티어로 **충분하고도 남는다** — 실질 위험은 낮음.
- **권고**: **Developer(무료) 플랜으로 최소 도입**해 트레이싱만 켜는 것은 가치 대비 위험이 낮아 추천. `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` 환경변수 2개만 추가하면 코드 변경 없이 자동 계측된다(LangChain/LangGraph 표준 통합). 단, **평가(eval) 자동화나 Deployment(Plus 이상)까지는 이 프로젝트 규모에서 불필요** — 과금·복잡도 대비 이득이 없다. 카드 등록은 하지 않고 5,000건 하드 캡을 그대로 안전장치로 둔다.

출처: https://www.langchain.com/pricing , https://docs.langchain.com/langsmith/pricing-faq , https://docs.langchain.com/langsmith/usage-and-billing , https://inference.net/content/langsmith-pricing/ (2026-06 검증 기사)

---

## 7. LangChain vs LangGraph 역할 분리 (2026 기준, v1.0 이후)

공식 문서(`docs.langchain.com/oss/python/concepts/products`, 2025-10 LangChain/LangGraph 1.0 발표 기준)가 명확히 3계층으로 정리:

| 계층 | 역할 | 언제 쓰나 |
|---|---|---|
| **LangGraph** | 저수준 오케스트레이션 런타임 — durable execution(내결함 실행), 스트리밍, human-in-the-loop, 영속성(persistence) | 세밀한 제어가 필요한 장기 실행·상태형 워크플로/에이전트. **LangChain 없이 단독 사용 가능.** |
| **LangChain** | 에이전트 프레임워크 — 모델/툴/에이전트 루프에 대한 표준 추상화. **LangChain 1.0은 LangGraph 위에 얹혀 있음**(내부적으로 LangGraph 런타임 사용). | 빠르게 표준적인 에이전트를 만들 때. 팀 표준화. LangGraph를 몰라도 쓸 수 있음. |
| **LangSmith** | 트레이싱·평가·프롬프트·배포 플랫폼. 프레임워크와 독립. | 관측·평가가 필요할 때(§6). |

핵심 인용: "LangGraph is very low-level, and focused entirely on agent orchestration... we recommend you use LangChain's agents that provide prebuilt architectures for common LLM and tool-calling loops (더 높은 추상화가 필요하면)."

**우리 스택에 대한 판단**: 우리는 이미 **LangGraph만 직접 쓰고 LangChain은 모델 통합(`langchain_google_genai.ChatGoogleGenerativeAI`)에만 얇게 쓰는 상태** — 이건 공식 문서가 말하는 "LangGraph를 LangChain 없이(정확히는 통합 컴포넌트만 빌려서) 쓰는" 전형적인 저수준 사용 패턴과 일치한다. 우리 그래프는 4개 이하 노드의 단순 조건부 분기라 LangChain의 "표준 에이전트 루프" 추상화(툴 호출 반복, ReAct 등)가 필요 없다 — **지금 방식이 과설계도 부족도 아닌 적정 수준**. `Command` 기반 라우팅(§1)으로 리팩터할 여지는 있지만 필수는 아니다.

출처: https://docs.langchain.com/oss/python/concepts/products , https://docs.langchain.com/oss/python/langgraph/overview , https://www.langchain.com/blog/langchain-langgraph-1dot0 , https://docs.langchain.com/oss/python/langgraph/choosing-apis

---

## 8. 우리 적용 권고 (종합)

### 8.1 4분기 라우팅 설계 스케치

`router_node`의 `RouterDecision.route` Literal을 `"A"/"B"/"C"` → `"REJECT"/"CLARIFY"/"SQL"/"HYBRID"` 4값으로 확장(또는 기존 값 유지하되 매핑만 바꿔도 됨). `_route_decision`/`add_conditional_edges` 딕셔너리에 키 하나만 늘어난다 — **그래프 구조 변경은 작다.**

```
router (LLM 분류, 구조화 출력 4값)
  ├─ REJECT  → guard_node(기존 C 그대로, FR16)
  ├─ CLARIFY → clarify_node(신규) — "질문이 너무 넓다" 판단 시 되묻기 문장 생성 후
  │              interrupt() 없이 그대로 answer로 반환(§2 "실전 대안"),
  │              프런트가 후속 메시지를 기존 멀티턴 contextualize_query로 이어붙여 재호출
  ├─ SQL     → sql_rag_node(기존 A 그대로, Text-to-SQL)
  └─ HYBRID  → hybrid_rag_node(신규, 기존 doc_rag_node를 승격) — §8.2
       → answer_node → END
```

라우터 프롬프트에 CLARIFY 분류 기준을 추가할 때 판단 신호 예시: "조건이 하나도 없이 매우 포괄적인 질의"("차 추천해줘", "좋은 매물 있어?") 이면서 매물 신호가 있어 C는 아닌 경우 → CLARIFY. 지금 프롬프트가 "차종·용도를 묻는데 조건이 흐릿하면 B(현 HYBRID)로 보낸다"고 돼 있는데, 이 규칙 중 "정말 아무 조건도 없는 극단적 사례"만 CLARIFY로 갈라내면 된다(전부 CLARIFY로 보내면 사용자 경험이 나빠지므로 **애매함의 정도**를 기준으로 좁게 적용 권고).

### 8.2 하이브리드 검색 권장 방식

`doc_rag_node`를 다음처럼 확장(§3 패턴 1, 최소 변경):
- 질의에서 뽑아낼 수 있는 구조 조건(가격대·차종 등)이 있으면 `sql_guard`가 만드는 WHERE 절을 재사용해 후보를 좁히고, 그 위에 `ORDER BY embedding <=> %s::vector`를 **같은 쿼리 레벨**로 붙여 의미 재정렬(RRF 없이 이 정도로 충분 — 우리 규모에서 두 랭킹을 따로 뽑아 합치는 RRF는 과설계).
- 구조 조건을 전혀 못 뽑으면(순수 의미형 질의) 지금처럼 벡터 검색만 수행 — 기존 `doc_rag_node` 로직 그대로 유지(회귀 없음).
- 가이드 문서 참조는 §4 임계값 방식으로: 코사인 거리가 일정 값 이하일 때만 answer에 근거로 붙인다(현재 무조건 붙이는 로직에 1줄 조건 추가).

### 8.3 가이드 문서 참조 조건

- 지금 규모(12개 문서, 문서=1청크)는 청킹 불필요 — 그대로 유지.
- 참조 여부는 코사인 거리 임계값(§4)으로 노이즈 컷.
- 문서가 향후 늘어나거나 길어지면(≥ 20개 또는 문서당 800토큰 초과) 그때 마크다운 `##` 헤딩 기준 섹션 청킹 도입(오버랩 불필요, 헤딩 경계가 이미 논리적 단위).

### 8.4 LangGraph/LangSmith 채택 범위와 위험

- **LangGraph**: 지금 저수준 StateGraph 직접 사용 방식이 적정 — 유지. `interrupt()`/체크포인터 기반 human-in-the-loop는 **도입하지 않음 권고**(REST 단발 요청 구조와 안 맞고, 멀티턴 맥락 이어붙이기로 같은 효과를 더 단순하게 낼 수 있음 — A2 단순함 우선).
- **LangSmith**: 무료 Developer 플랜으로 트레이싱만 최소 도입 권고(환경변수 2개, 코드 변경 없음). 평가 자동화·Deployment는 규모 대비 불필요, 도입 안 함. 카드 미등록으로 5,000건 하드 캡을 안전장치로 유지.
- **위험 요약**: 4분기 확장 자체는 그래프 구조상 위험이 낮다(조건부 엣지 키 추가뿐). 가장 큰 리스크는 CLARIFY 분류 기준이 애매해 사용자가 되묻기를 자주 겪어 이탈하는 것 — 라우터 프롬프트에서 CLARIFY를 "정말 아무 조건 없는 극단 사례"로 좁게 잡고, A/B 질의셋(기존 Phase B 하니스 재사용 가능)으로 CLARIFY 발동 빈도를 실측 검증한 뒤 배포하는 게 안전하다.
