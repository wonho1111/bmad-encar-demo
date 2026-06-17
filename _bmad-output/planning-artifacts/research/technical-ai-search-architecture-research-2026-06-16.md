---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments: ['docs/idea.md']
workflowType: 'research'
lastStep: 7
research_type: 'technical'
research_topic: 'AI 자연어 검색 아키텍처 (LangGraph 라우팅 + Text-to-SQL + 문서 RAG)'
research_goals: 'idea.md의 AI 검색 스택 기술 타당성 검증, 구현 리스크·대안 도출'
user_name: 'Dnjsg'
date: '2026-06-16'
web_research_enabled: true
source_verification: true
---

# 기술 연구 보고서: AI 자연어 검색 아키텍처

**날짜:** 2026-06-16
**작성자:** Dnjsg
**연구 유형:** 기술 연구 (Technical Research)
**대상 프로젝트:** bmad-encar-demo (엔카·헤이딜러 류 중고차 직거래 데모)

---

## 1. Research Overview (연구 개요 및 방법론)

### 연구 주제
중고차 직거래 서비스의 **구매자용 AI 채팅 어시스턴트** — "3천만원 이하 흰색 SUV 추천해줘" 같은
자연어 한 문장으로 매물을 검색하는 기능의 아키텍처 타당성 검증.

### 연구 목표
- `docs/idea.md`에 정의된 AI 검색 스택(LangGraph + Text-to-SQL + 문서 RAG + Gemini + pgvector)이
  기술적으로 타당한지 확인
- 구현 시 핵심 리스크와 대안을 근거(출처)와 함께 정리
- PRD·아키텍처 단계로 넘어가기 전 의사결정 근거 제공

### 방법론
- **2025~2026 최신 웹 데이터** 기반 조사, 3개 영역 병렬 리서치 수행
  (① LangGraph/Text-to-SQL ② pgvector/임베딩 RAG ③ 무료 등급/배포)
- 핵심 주장마다 **출처 URL**과 **신뢰도** 표기
- 신뢰도 표기 기준:
  - **[확실]** — 공식 문서/다수 출처로 교차 검증됨
  - **[보통]** — 일반적 권고이나 버전·환경에 따라 달라질 수 있음
  - **[미확인]** — 단일 출처·최신성 불확실. **구현 전 공식 문서로 반드시 재확인 필요**

### 용어 메모 (처음 등장 용어 설명)
- *RAG* (Retrieval-Augmented Generation, 검색 증강 생성): LLM이 외부 데이터를 먼저 검색해 근거로 답을 생성.
- *LLM* (Large Language Model, 대규모 언어 모델): 자연어를 이해·생성하는 AI 모델.
- *Text-to-SQL*: 자연어 질문을 SQL 쿼리로 변환하는 기술.
- *임베딩(embedding)*: 텍스트를 의미 기반 숫자 벡터로 변환한 것. 유사도 검색에 사용.
- *pgvector*: PostgreSQL에서 벡터 유사도 검색을 가능하게 하는 확장 기능.

---

## 2. 연구 범위 확정

본 연구는 사용자 선택에 따라 **AI 검색 아키텍처를 중심**으로,
이와 직접 엮인 임베딩·DB·배포 영역까지 **폭넓게** 다룬다.

| 영역 | 다룸 | 비고 |
|---|---|---|
| LangGraph 오케스트레이션·라우팅 | ✅ | 핵심 |
| Text-to-SQL 경로 + 안전장치 | ✅ | 핵심 (보안 비중 큼) |
| 문서 RAG (pgvector + 임베딩) | ✅ | 핵심 |
| LLM·임베딩 모델 선택, Gemini 무료 등급 | ✅ | AI 검색 직접 연관 |
| FastAPI 통합·배포 | ✅ | idea.md 충돌점 발견 |
| 일반 CRUD(Next.js/기본 API/인증) | ❌ | 표준 영역, 별도 검증 불필요 |

> *CRUD* (Create·Read·Update·Delete): 데이터의 생성·조회·수정·삭제. 일반적 웹 개발 표준 영역.

---

## 3. AI 검색 오케스트레이션 (LangGraph)

### 3.1 전체 흐름
idea.md의 4단계 흐름(라우터 → SQL RAG / 문서 RAG → 답변 생성)은
LangGraph의 표준 패턴과 정확히 일치하며 타당하다. **[확실]**

```
[사용자 질문]
      │
      ▼
 ① 라우터 노드 (의도 분류)
      │
      ├─ 조건형 질문 → ② Text-to-SQL 경로 (매물 DB 정밀 필터)
      │
      └─ 의미/상식형 질문 → ③ 문서 RAG 경로 (임베딩 유사도 검색)
                    │
                    ▼
              ④ 답변 생성 노드 (자연어 답변 + 매물 카드)
```

### 3.2 라우터 노드 구현 방식
- **권장**: LLM 분류 노드 + **구조화 출력(Pydantic 스키마)** 으로 의도를 강제.
  예: `{"intent": "listing_search" | "faq", "confidence": float}` → 환각·형식 오류 감소. **[확실]**
- LangGraph 최신(1.0대) 패턴은 노드가 `Command(goto="다음노드", update={...})`를 반환해
  **노드 내부에서 라우팅을 결정**하는 방식. 기존 `add_conditional_edges`도 유효. **[보통]**
  - 출처: [Thinking in LangGraph (LangChain 공식)](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)
- 두 경로(Text-to-SQL / 문서 RAG)는 **별도 노드**로 분리하고, 원시 결과를 저장한 뒤
  마지막 **답변 생성 노드**로 수렴시키는 구조가 디버깅·확장에 유리. **[보통]**

  > *노드(node)*: 그래프에서 하나의 처리 단계. *엣지(edge)*: 노드 간 연결(흐름).

### 3.3 LangGraph 성숙도 및 대안
- LangGraph는 1.0대로 **프로덕션 사용 가능** 수준. 단, 0.1→0.2대에서 호환성 깨지는 변경 이력이 있어
  버전 고정 권장. **[보통]**
- 대안:
  - **LangChain 1.0** — LangGraph 위에 얹힌 상위 API. 단순 라우터+툴+RAG라면 더 간단. **[보통]**
  - **PydanticAI / CrewAI / Haystack** — 각각 타입 안전·멀티에이전트·RAG 특화. 본 과제엔 과함. **[보통]**
- **본 과제 권장**: LangChain 1.0 + LangGraph 조합으로 시작하되,
  라우터·SQL·RAG·답변생성을 명시적 노드 함수로 설계해 향후 순수 LangGraph 이전 여지를 남긴다. **[보통]**

> ⚠️ 과제용 데모 관점: idea.md가 LangGraph를 고른 이유(흐름 시각화·provider 비종속)는 타당.
> 다만 "라우터+2경로"만 필요하다면 LangGraph의 고급 기능(체크포인트·휴먼인더루프)은 **선택 사항**이며,
> 초기엔 단순 구현으로 시작해도 무방하다.

---

## 4. Text-to-SQL 경로

### 4.1 SQL Agent vs SQL Chain
| 방식 | 특징 | 권장 |
|---|---|---|
| **SQL Agent** (ReAct 반복) | 스키마 조회 → 쿼리 생성 → 오류 시 자가 수정. 복잡 질의에 강함 | ✅ 권장 |
| SQL Chain (단발 생성) | 단순 질의만. 오류 복구 불가 | 단순 케이스 한정 |

- 실제 DB와 상호작용하는 프로덕션에선 **Agent 방식이 표준**. 토큰은 더 쓰지만 정확도가 크게 높음. **[보통]**
  - 출처: [Build a custom SQL agent (LangChain 공식)](https://docs.langchain.com/oss/python/langgraph/sql-agent)
- 표준 툴 3종: `sql_db_list_tables`, `sql_db_schema`(CREATE문+샘플행), `sql_db_query`. **[확실]**

### 4.2 안전장치 — 다층 방어 (idea.md의 "SELECT 전용 + 판매완료 제외" 구체화) 🔒

> **핵심 결론: 프롬프트 규칙만으로는 안전하지 않다.** LLM이 생성한 SQL은
> **결정론적(deterministic) 검증**을 반드시 거쳐야 한다. **[확실]**
> 출처: [Text-to-SQL Security: 10 Risks Before Production](https://www.dpriver.com/blog/text-to-sql-security-10-risks-before-production-deployment/)

| 계층 | 조치 | 본 과제 적용 |
|---|---|---|
| 1. DB 접근 제어 | **읽기전용 롤**(SELECT만 GRANT) + `statement_timeout`(예: 10~30s) | 필수 |
| 2. 앱 레벨 검증 | `sqlparse`로 파싱 → **SELECT문만 허용**, DROP/DELETE/UPDATE 등 차단 | 필수 |
| 3. 스키마 바인딩 | 허용된 테이블/컬럼만 LLM에 제공 → **환각 컬럼 방지** | 필수 |
| 4. 행 범위 강제 | WHERE에 `status != 'sold'` 자동 주입 → 판매완료 매물 제외 | 필수 |
| 5. 비용 추정 | `EXPLAIN`으로 과도 스캔 쿼리 사전 차단, 기본 `LIMIT` 강제 | 권장 |
| 6. 감사 로그 | 원질문·생성SQL·결과수·오류 기록 | 권장(선택) |

- Supabase는 PostgreSQL이므로 **읽기전용 DB 롤 + RLS(Row Level Security)** 로 1·4계층을 DB단에서 강제 가능. **[확실]**

  > *RLS* (Row Level Security, 행 수준 보안): 행 단위로 접근을 제어하는 PostgreSQL 기능.

### 4.3 실패 모드와 완화책
| 실패 모드 | 완화 |
|---|---|
| 환각 컬럼 참조 | 스키마 사전 제공 + 컬럼 검증, 오류 메시지 재주입 후 재시도 |
| 모호한 필터("저렴한") | 라우터에서 되묻기(가격대 확인) 또는 합리적 기본값 명시 |
| 빈 결과 환각 | "조건에 맞는 매물 없음" 고정 응답, 결과수 0이면 카드 미반환 |
| 과도 조회("차 보여줘") | 기본 `LIMIT 50` 주입 |
| 다단계 쿼리 실패 | 오류를 LLM에 재주입해 **최대 3회** 재시도(무한루프 방지) |
| 결과셋 과대 → 컨텍스트 초과 | 상위 N개만 LLM 전달, 페이지네이션 |
- 출처: [Building a Powerful SQL Agent with LangGraph (Part 2)](https://medium.com/@hayagriva99999/building-a-powerful-sql-agent-with-langgraph-a-step-by-step-guide-part-2-24e818d47672)

### 4.4 Text-to-SQL용 모델 선택
- Gemini Flash로 **단순~중간 난이도 매물 조건 질의**는 충분히 처리 가능. **[보통]**
- 일부 출처가 "Gemini-SQL2 / Gemini 3.1 Pro가 BIRD 벤치마크 80% 상회" 등을 주장하나,
  **모델명·수치는 단일 출처이고 공식 모델 카드 확인 불가** → **[미확인]. 단정 금지, 구현 전 재확인.**
- **권고**: Flash로 시작하고, 복잡 질의 정확도가 부족하면 그때 상위 모델 검토. (저비용 데모 우선)

---

## 5. 문서 RAG 경로 (Supabase pgvector + Gemini 임베딩)

### 5.1 pgvector 설정
- Supabase 호스팅 Postgres에 pgvector **기본 내장** → `create extension vector` 만으로 활성화. **[확실]**
- 유사도 연산자: `<->`(L2), `<=>`(코사인), `<#>`(내적).
  Gemini 임베딩은 정규화 벡터이므로 **코사인 `<=>` 권장**. **[보통]**
  - 출처: [Supabase pgvector 문서](https://supabase.com/docs/guides/ai/vector-columns)

### 5.2 인덱스: HNSW vs IVFFlat
- **본 과제 권장: HNSW.** 수천~수만 행(매물 + FAQ 문서) 규모에서 일관된 지연·높은 재현율. **[보통]**
  - 시작 파라미터 예: `m=16, ef_construction=200`, 조회 시 `ef_search=40`.
- IVFFlat은 1천만+ 대규모 정적 데이터용. **빈 테이블에 만들면 안 되고** 마이그레이션에 넣지 말 것. **[보통]**
  - 출처: [pgvector Index Selection: IVFFlat vs HNSW](https://medium.com/@philmcc/pgvector-index-selection-ivfflat-vs-hnsw-for-postgresql-vector-search-6eff26aaa90c)

  > *HNSW* (Hierarchical Navigable Small World): 근사 최근접 이웃 검색용 그래프 인덱스.

### 5.3 임베딩 모델·차원
- **차원 일치 필수**: 임베딩 모델 출력 차원 = pgvector 컬럼 차원(`vector(N)`). 불일치 시 동작 안 함. **[확실]**
- 확인 결과(2026-06): 구버전 `text-embedding-004`·`gemini-embedding-001`은 폐기됨. 현행 임베딩 모델은
  **차원 128~3072 설정 가능(기본 3072), 입력 최대 8,192토큰**. **데모는 768 또는 1536 권장**(저장공간 절약). **[보통]**
  - ⚠️ 정확한 **현행 모델명**은 출처가 엇갈려 **구현 직전 [공식 임베딩 문서](https://ai.google.dev/gemini-api/docs/embeddings)에서 확정.** **[미확인]**
- idea.md 방침(생성 LLM과 동일 SDK·키로 임베딩 통일)은 관리 단순화 측면에서 타당. **[보통]**

### 5.4 청킹 전략
> *청킹(chunking)*: 긴 문서를 검색 단위로 잘게 나누는 작업.

- FAQ/구매 가이드: **200~400토큰**, 자기완결적이면 오버랩 불필요. **[보통]**
- 매물 설명: 대개 짧으므로 **통째로 1청크**, 매우 길면(>500단어) 경량 청킹. **[보통]**
- 매물의 구조화 정보(가격·연식·옵션)는 청킹하지 말고 **별도 컬럼**으로 유지해 관계형 필터에 사용. **[보통]**

### 5.5 ⚠️ 핵심 함정 — 필터 + 벡터 동시 사용
- pgvector는 **사전 필터링을 하지 않는다.** 먼저 유사도로 후보를 뽑고 **그다음** 필터를 적용 →
  "가격<3천만 + 유사도 상위 10" 같은 질의에서 **결과가 10개보다 적게** 나올 수 있음. **[확실]**
- 완화책(우선순위):
  1. **`SET hnsw.iterative_scan = on`** (pgvector 0.8.0+, Supabase 지원) — 충분한 결과 나올 때까지 스캔. **[보통]**
  2. 자주 거르는 컬럼(가격·연식·차종·색상)에 **인덱스** 생성 후 사전 필터 → 벡터 랭킹.
  3. **후보 과다 조회**(예: 50개 뽑아 앱에서 필터 후 상위 10).
- 출처: [No Pre-filtering in pgvector Means Reduced Recall](https://dev.to/franckpachot/no-pre-filtering-in-pgvector-means-reduced-ann-recall-1aa1)

> **시사점**: idea.md의 "조건형 질문은 Text-to-SQL 경로"가 이 함정을 **자연스럽게 회피**한다.
> 가격·연식 등 정밀 조건은 SQL 경로(정확한 WHERE)로, 의미 검색만 벡터 경로로 보내는 분리가 바람직하다.
> 벡터+필터를 한 쿼리에 섞는 것은 의미형 질의에 한해 신중히 사용.

### 5.6 하이브리드 검색(BM25 + 벡터)
- Postgres에서도 BM25(키워드 랭킹) + 벡터 + RRF 결합이 가능해졌으나, 구현 복잡도 증가. **[보통]**

  > *BM25*: 키워드 빈도 기반 전통적 검색 랭킹 알고리즘. *RRF*(Reciprocal Rank Fusion): 여러 순위를 합치는 기법.
- **권고**: MVP는 **벡터 단독**으로 시작. 정확 일치(모델명·차량번호) 누락 불만이 나오면 그때 하이브리드 추가. **[보통]**

  > *MVP* (Minimum Viable Product, 최소 기능 제품): 핵심 기능만 갖춘 초기 제품.

---

## 6. LLM·임베딩 선택 & Gemini 무료 등급 한계

### 6.1 무료 등급 rate limit
> *rate limit*: API 호출 빈도 제한(분당/일당 요청·토큰 수).

- 공식 문서 확인 결과(2026-06): **Gemini Flash 무료 등급 ≈ 10 RPM · 250 RPD · 250K TPM**,
  **임베딩 ≈ 100 RPM · 1,000 RPD**. 데모(검색 1건당 호출 1~2회) 수준이면 충분. **[보통]**
  - 확인처: [Gemini 한도](https://ai.google.dev/gemini-api/docs/rate-limits)
  - ⚠️ **정확한 최신 모델명**(예: 더 최신 flash 버전)은 출처가 엇갈려 **구현 시 콘솔에서 확정**. **[미확인]**
- **데모(동시 사용자 소수·가벼운 검색) 수준이면 무료 등급으로 대체로 충분**하다는 게 공통된 결론. **[보통]**
- 주의: 일일 요청 한도가 낮을 수 있어 **시연 직전 대량 임베딩 생성/테스트는 분산** 권장.

### 6.2 ⚠️ 데이터 프라이버시 (중요)
- **무료 등급에서는 입력 프롬프트·응답이 모델 개선(학습)에 사용될 수 있다.** 유료 등급은 미사용. **[보통]**
- 매물 검색 질의에 개인정보(연락처 등)가 섞이지 않도록 주의. 민감정보는 프롬프트에 넣지 않는 설계.
  - 출처: [Gemini Free Tier Data Privacy](https://docs.bswen.com/blog/2026-03-23-gemini-free-tier-data-privacy/)

---

## 7. FastAPI 통합 & 배포 ⚠️ 핵심 리스크 (idea.md 충돌)

### 7.1 발견된 충돌점
- `idea.md`는 **"배포: Vercel(프론트엔드 + 백엔드)"** 로 FastAPI 백엔드도 Vercel에 올리도록 명시.
- 그러나 리서치 결과 **Vercel은 LangGraph 같은 장시간 Python 백엔드에 부적합**:
  - 서버리스 함수 실행 시간 **무료/Hobby 최대 5분(300초)**, 응답 페이로드 4.5MB 제한. **[보통]**
  - LLM 다단계 추론·임베딩·폴링 채팅과 잘 안 맞음(타임아웃·콜드스타트). **[보통]**
  - 출처: [Vercel Functions Limitations](https://vercel.com/docs/functions/limitations)

  > *서버리스(serverless)*: 서버를 직접 관리하지 않고 요청 시 함수가 실행되는 배포 방식.
  > *콜드스타트(cold start)*: 유휴 상태 함수가 처음 호출될 때 발생하는 초기 지연.

### 7.2 권장 대안
| 호스팅 | 실행시간 | 무료 등급 | 적합도 |
|---|---|---|---|
| **Google Cloud Run** ✅ | 길음(수십 분) | 월 200만 요청·vCPU-초 무료 | LangGraph 백엔드에 가장 적합 |
| Railway | 무제한(컨테이너) | $5 크레딧(이후 월 $5~) | 간단한 UX, 차선 |
| Render(무료) | 무제한 | 750시간/월, 유휴 시 spin-down | 콜드스타트 김(30~60s) |
| Vercel | 5분 | 넉넉 | ❌ 백엔드엔 비권장 |

- 채팅은 idea.md대로 **폴링 방식**이면 WebSocket 불필요 → 일반 HTTP 백엔드로 충분. **[확실]**

> 📌 **재검토 노트 (2026-06-16): 경부하 시연 스코프에서는 Vercel 통일이 적합.**
> 위 "부적합" 판정은 *요청 하나가 수십 초~수 분 도는 무거운 다단계 에이전트 파이프라인*을 가정한 것이다.
> 본 과제의 실제 조건(시연용·경부하, 검색 요청당 짧은 Gemini 호출 1~2회로 수초 내 종료)은 그 가정에 해당하지 않는다.
> 공식 Vercel 문서 재확인 결과: Python(ASGI) 런타임이 FastAPI를 그대로 구동하며, Hobby 함수 시간 제한은
> **최대 300초**(수초 요청엔 무관), 번들 한도 **500MB**(langgraph+langchain+google-genai ≈ 150~300MB로 적재 가능),
> Fluid Compute로 콜드스타트도 경부하에선 사실상 무시 가능. **[보통]**
> - 유의 3가지: ① 무상태 → 채팅 이력은 Supabase 저장(폴링과 호환) ② Supabase 연결 풀링 ③ 무거운 의존성 회피.
> - 결론: **데모는 Vercel 단일 배포 채택**. 부하 증가 시 백엔드만 Cloud Run으로 분리하는 것을 차선으로 둔다.
> - 출처: [Deploy FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python), [Function Duration](https://vercel.com/docs/functions/configuring-functions/duration)

  > *폴링(polling)*: 클라이언트가 주기적으로 서버에 새 메시지를 물어보는 방식.

---

## 8. 리스크 & 권고 요약 (의사결정 표)

| # | 항목 | 권장 | 근거 | 신뢰도 |
|---|---|---|---|---|
| 1 | 오케스트레이션 | LangGraph(+LangChain 1.0), 명시적 노드 설계 | idea.md 흐름과 표준 패턴 일치 | 보통 |
| 2 | 라우터 | 구조화 출력 기반 의도 분류 | 환각·형식 오류 감소 | 확실 |
| 3 | Text-to-SQL | SQL **Agent** 방식 | 오류 자가수정, 정확도↑ | 보통 |
| 4 | **SQL 안전장치** | **다층 방어**(읽기전용 롤·검증·스키마 바인딩·행 강제) | 프롬프트만으론 불안전 | **확실** |
| 5 | 벡터 인덱스 | HNSW | 중소 규모에 일관된 성능 | 보통 |
| 6 | 임베딩 차원 | 모델 출력 = 컬럼 차원 일치 | 불일치 시 미동작 | 확실 |
| 7 | **필터+벡터** | 정밀 조건은 SQL 경로로 분리, `iterative_scan` | pgvector 사전필터 없음 | 확실 |
| 8 | 하이브리드 검색 | MVP는 벡터 단독, 필요 시 추가 | 복잡도 대비 ROI | 보통 |
| 9 | Gemini 등급 | 데모는 무료, **프라이버시 주의** | 무료는 학습 사용 가능 | 보통 |
| 10 | **배포** | **Vercel 통일**(경부하 시연 한정) | 짧은 요청·300초 한도 내, 7장 재검토 노트 참조. 부하↑ 시 백엔드만 Cloud Run | 보통 |
| 11 | 모델명·수치 | 구현 전 공식 문서 재확인 | 단일 출처·최신성 불확실 | **미확인** |

### 구현 전 반드시 확정할 [미확인] 항목
1. Gemini **생성 모델·임베딩 모델의 정확한 이름·차원·무료 등급 한도** (공식 문서)
2. Text-to-SQL에 쓸 모델 등급(Flash로 충분한지 실제 질의로 검증)
3. pgvector / LangGraph **버전 고정** 값

---

## 9. 출처 목록

### LangGraph & Text-to-SQL
- [Thinking in LangGraph (LangChain 공식)](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)
- [Build a custom SQL agent (LangChain 공식)](https://docs.langchain.com/oss/python/langgraph/sql-agent)
- [Building a Powerful SQL Agent with LangGraph (Part 2)](https://medium.com/@hayagriva99999/building-a-powerful-sql-agent-with-langgraph-a-step-by-step-guide-part-2-24e818d47672)
- [LangChain 1.0 vs LangGraph 1.0 (2026)](https://www.clickittech.com/ai/langchain-1-0-vs-langgraph-1-0/)

### 보안 (Text-to-SQL)
- [Text-to-SQL Security: 10 Risks Before Production](https://www.dpriver.com/blog/text-to-sql-security-10-risks-before-production-deployment/)
- [Preventing SQL Injection Attacks in Postgres](https://www.crunchydata.com/blog/preventing-sql-injection-attacks-in-postgresql)
- [Techniques for improving text-to-SQL (Google Cloud)](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)

### pgvector & 임베딩 RAG
- [Supabase pgvector / Vector Columns 문서](https://supabase.com/docs/guides/ai/vector-columns)
- [pgvector Index Selection: IVFFlat vs HNSW](https://medium.com/@philmcc/pgvector-index-selection-ivfflat-vs-hnsw-for-postgresql-vector-search-6eff26aaa90c)
- [No Pre-filtering in pgvector Means Reduced Recall](https://dev.to/franckpachot/no-pre-filtering-in-pgvector-means-reduced-ann-recall-1aa1)
- [Gemini API Embeddings (Google 공식)](https://ai.google.dev/gemini-api/docs/embeddings)

### 무료 등급 & 배포
- [Google AI 가격/한도](https://ai.google.dev/pricing)
- [Gemini Free Tier Data Privacy](https://docs.bswen.com/blog/2026-03-23-gemini-free-tier-data-privacy/)
- [Vercel Functions Limitations](https://vercel.com/docs/functions/limitations)
- [Google Cloud Run Pricing](https://cloud.google.com/run/pricing)

---

## 부록: 연구 범위 확정 기록

**Research Topic:** AI 자연어 검색 아키텍처 (LangGraph 라우팅 + Text-to-SQL + 문서 RAG)
**Research Goals:** idea.md의 AI 검색 스택 기술 타당성 검증, 구현 리스크·대안 도출
**연구 초점(사용자 선택):** AI 검색 아키텍처
**연구 깊이(사용자 선택):** 전체 폭넓게
**Scope Confirmed:** 2026-06-16

---

*본 문서는 BMad Method 기술 연구 워크플로로 생성되었으며, 2026-06-16 기준 웹 리서치에 기반한다.*
*[미확인] 표기 항목은 구현 착수 전 공식 문서로 반드시 재검증할 것.*
