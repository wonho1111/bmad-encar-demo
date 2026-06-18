---
stepsCompleted: ['step-01-document-discovery', 'step-02-prd-analysis', 'step-03-epic-coverage-validation', 'step-04-ux-alignment', 'step-05-epic-quality-review', 'step-06-final-assessment']
documentsIncluded:
  - 'prds/prd-bmad-encar-demo-2026-06-17/prd.md'
  - 'architecture.md'
  - 'epics.md'
---

# Implementation Readiness Assessment Report

**Date:** 2026-06-19
**Project:** bmad-encar-demo

## 1. Document Inventory

| 문서 유형 | 파일 | 상태 |
|-----------|------|------|
| PRD | `prds/prd-bmad-encar-demo-2026-06-17/prd.md` (15KB) | ✅ 포함 |
| Architecture | `architecture.md` (33KB) | ✅ 포함 |
| Epics & Stories | `epics.md` (36KB) | ✅ 포함 |
| UX Design | — | ⚠️ 없음 (부재 명시 후 진행) |

**보조 문서:** PRD 폴더 내 `addendum.md`, `reconcile-idea.md`, `reconcile-research.md`, `review-rubric.md`
**참고 자료(평가 외):** `product-brief-encar-demo-2026-06-16.md`, `research/technical-ai-search-architecture-research-2026-06-16.md`

**중복:** 없음 · **UX 부재:** Step 4 점검 깊이 제한 (데모 프로젝트 특성상 비치명적)

## 2. PRD Analysis

### Functional Requirements (FR1~FR25)

**F1. 인증·계정**
- FR1: 이메일/비밀번호 가입 + 가입 시 역할(구매자/판매자) 선택 (Supabase Auth, 소셜 로그인 제외)
- FR2: 로그인/로그아웃
- FR3: 역할별 접근 제어(구매자/판매자/관리자)
- FR4: 관리자 계정 별도 존재(시드 또는 별도 경로 생성)

**F2. 매물 등록·관리 (판매자)**
- FR5: 매물 등록 — 15필드(제조사·모델·차종·연식·가격·주행거리·색상·연료·변속기·배기량·인승·지역·사고이력·옵션·설명). 사진 미포함(서비스 전체 제외). 차종은 Encar/K-Car식 분류값.
- FR6: 본인 매물만 조회/수정/삭제
- FR7: 등록 즉시 노출(사전 승인 없음)
- FR8: 판매자만 "구매 완료" 처리 → 판매 완료 상태 전환(상대 지정 불필요)

**F3. 매물 탐색 (구매자)**
- FR9: 키워드/필터(가격·연식·차종·색상·연료·변속기·지역) 검색
- FR10: 매물 상세 조회(설명·옵션·상태)
- FR11: 판매 완료 매물은 구매자 모든 화면에서 미노출 (단일 규칙, 전 FR 공통)

**F4. AI 검색 어시스턴트 (핵심)**
- FR12: 자연어 한 문장 매물 검색
- FR13: 라우터 의도 분류 — (A)구조형 / (B)질적·의미형 / (C)무관
- FR14: (A) Text-to-SQL 정밀 필터링 (SELECT 전용·범위 제한, FR11 준수)
- FR15: (B) 문서 기반 RAG — 코퍼스 = ①매물 설명·옵션 텍스트 + ②차량 상식·구매 가이드 문서, pgvector 유사도 검색
- FR16: (C) 무관 질의 정중히 거절 + 매물 검색 유도(순수 상식 Q&A 미제공)
- FR17: 답변 = 자연어 설명 + 매물 카드(최소: 제조사·모델·연식·가격·주행거리·지역). 0건 시 조건 완화 안내
- FR18: 멀티턴 — 대화 맥락 클라이언트 보관, 서버/DB 미저장

**F5. 문의 채팅 (구매자↔판매자)**
- FR19: 문의 시 양측 동일 채팅방 생성
- FR20: 폴링 방식 메시지 교환
- FR21: 채팅 메시지 DB 저장(AI 이력과 별개)

**F6. 관리자**
- FR22: 회원 목록 조회 + 정지/삭제
- FR23: 전체 매물 조회 + 부적절 매물 삭제
- FR24: 거래 내역(판매 완료 매물) 조회
- FR25: 채팅방 열람 + 삭제

**Total FRs: 25**

### Non-Functional Requirements (NFR1~NFR6)

- NFR1 성능: AI 검색 수 초 내(Gemini 1~2회 호출), 채팅 폴링 준실시간(예 3~5초)
- NFR2 보안·권한: Text-to-SQL SELECT 전용 + 결정론적 안전장치(①읽기전용 DB 롤 ②기본 LIMIT 강제 ③실행 전 쿼리 검증/화이트리스트), 역할별 접근 제어, RLS 권장
- NFR3 플랫폼: 반응형 웹(사용자/관리자) + Flutter 앱에서 핵심 기능 동작
- NFR4 배포·확장: Vercel 단일 배포, 무상태, 상태는 Supabase 저장, 확장 시 백엔드 분리 가능
- NFR5 데이터·프라이버시: 채팅 메시지 영속 저장, AI 대화 이력 미저장(클라이언트 보관)
- NFR6 비용: 저비용 구성(Gemini 무료·Vercel Hobby·Supabase 무료/저가)

**Total NFRs: 6**

### Additional Requirements / Constraints
- 성공 지표 SM1~SM4, 카운터 지표 CM1~CM3 (시연 시나리오 3종, 2경로 RAG 시연, 가드/안전/정합 보장)
- 범위 밖: 결제·계약, 소셜 로그인, 신고, 웹소켓 채팅, AI 이력 서버 저장, 관리자 사전승인, 순수 상식 Q&A
- 오픈 이슈 OI1(해결)~OI6: 모델·차원(768) 확정, Text-to-SQL 방식, 벡터 인덱스, 라이브러리 버전 고정, 데모 질의셋+차형 용어 매핑, RAG 코퍼스 작성

### PRD Completeness Assessment
- **요구사항 명확성: 높음.** FR/NFR이 전역 번호로 고정되고 용어 정의(매물/구매완료/문의채팅/AI채팅)가 선명. 추적성(traceability) 기반이 탄탄.
- **주의:** OI2~OI6은 "구현 전 확정" 항목으로 PRD/아키텍처/스토리에서 닫혀 있는지 후속 단계에서 확인 필요. UX 문서 부재.

## 3. Epic Coverage Validation

### Coverage Matrix (FR → Epic → Story 교차검증)

| FR | Epic | 실제 스토리 | 상태 |
|----|------|------------|------|
| FR1 | Epic 1 | Story 1.2 | ✓ Covered |
| FR2 | Epic 1 | Story 1.3 | ✓ Covered |
| FR3 | Epic 1 | Story 1.4 | ✓ Covered |
| FR4 | Epic 1 | Story 1.5 | ✓ Covered |
| FR5 | Epic 2 | Story 2.1+2.2 | ✓ Covered |
| FR6 | Epic 2 | Story 2.1+2.3 | ✓ Covered |
| FR7 | Epic 2 | Story 2.2 | ✓ Covered |
| FR8 | Epic 2 | Story 2.4 | ✓ Covered |
| FR9 | Epic 3 | Story 3.1 | ✓ Covered |
| FR10 | Epic 3 | Story 3.2 | ✓ Covered |
| FR11 | Epic 3 | Story 3.3 | ✓ Covered |
| FR12 | Epic 4 | Story 4.7 | ✓ Covered |
| FR13 | Epic 4 | Story 4.5 | ✓ Covered |
| FR14 | Epic 4 | Story 4.3 | ✓ Covered |
| FR15 | Epic 4 | Story 4.4 | ✓ Covered |
| FR16 | Epic 4 | Story 4.5 | ✓ Covered |
| FR17 | Epic 4 | Story 4.5 | ✓ Covered |
| FR18 | Epic 4 | Story 4.6 | ✓ Covered |
| FR19 | Epic 5 | Story 5.2 | ✓ Covered |
| FR20 | Epic 5 | Story 5.3 | ✓ Covered |
| FR21 | Epic 5 | Story 5.3 | ✓ Covered |
| FR22 | Epic 6 | Story 6.2 | ✓ Covered |
| FR23 | Epic 6 | Story 6.3 | ✓ Covered |
| FR24 | Epic 6 | Story 6.4 | ✓ Covered |
| FR25 | Epic 6 | Story 6.5 | ✓ Covered |
| (재현) FR1~3·5~21 | Epic 7 | Story 7.1~7.5 | ✓ 모바일 재현 |

### NFR / 오픈이슈 커버리지
- NFR2(안전장치): Story 2.1(소유권 RLS·CHECK), 4.1(읽기전용 롤·JWT), 4.3(sql_guard) — ✓
- NFR3(플랫폼): Epic 7 전체 — ✓ / NFR1·4·5·6: 스토리 AC·아키텍처에 반영
- OI2(Text-to-SQL 방식): Story 4.3 / OI5(데모 질의셋·차형 매핑): Story 4.5·4.8 / OI6(RAG 코퍼스 작성): Story 4.2 — ✓ 모두 소유 스토리 명시

### Missing Requirements
- **없음.** PRD FR1~FR25 전부 에픽/스토리에 추적 가능한 구현 경로 보유. 에픽에만 있고 PRD에 없는 "유령 FR"도 없음(Epic 7은 신규 FR이 아닌 모바일 재현).

### Coverage Statistics
- Total PRD FRs: **25**
- FRs covered in epics/stories: **25**
- **Coverage: 100%**
- Additional Requirements(AR1~AR10) 도 Epic 1·2·4·7에 기반 흡수 스토리로 매핑됨.

## 4. UX Alignment Assessment

### UX Document Status
- **Not Found** — 별도 UX 명세 문서 없음. PRD·에픽·아키텍처 모두 "UX 문서 미작성, 화면·라우트 구조로 대체" 명시.

### UX가 함의되는가? (UI implied)
- **예.** 사용자 대면(user-facing) 서비스이며 3개 플랫폼(사용자 웹·관리자 웹·Flutter 앱). 따라서 UX 부재는 단순 무시가 아니라 **대체 충족 여부**를 확인해야 함.

### 대체 충족 검증 (Architecture가 UX 역할 대행)
- 아키텍처 `Project Structure`에 **전 화면이 라우트로 정의**됨: `(auth)/login·signup`, `(user)/search·listings/[id]·ai·sell·chat`, `(admin)/members·listings·transactions·chats`.
- `Requirements to Structure Mapping`이 FR그룹↔화면을 매핑. 사용자 여정(UJ-1~3, PRD §2)이 라우트 흐름으로 추적 가능.
- 매물 카드 표시 필드(`ListingCard`), 단위 표시 포맷(km·원), 한국어 오류 메시지, 로딩/빈 상태 안내(FR17 0건) 등 UI 레벨 규칙도 패턴 섹션에 존재.

### Alignment Issues
- **PRD↔구조:** 일치. UJ 3종이 라우트·스토리로 빠짐없이 표현됨.
- **Architecture 내부 정합:** Starter 섹션의 초기화 명령은 `web-user`+`web-admin`(2앱)이나, `Project Structure`에서 **단일 `web/` + 라우트 그룹**으로 명시 대체(라인 313). 에픽 Story 1.1도 단일 `web/` 채택 → **이미 화해됨(drift 아님)**.

### Warnings
- ⚠️ **(경미) UX 명세 부재** — 시각 디자인·인터랙션 디테일(컴포넌트 상태, 반응형 브레이크포인트, 접근성)은 문서화되지 않음. 데모/과제 범위에서는 **비차단**. 향후 `bmad-ux`로 보강 가능(아키텍처 Gap Analysis도 동일 결론: "Nice-to-Have, 건너뜀").
- 화면 구조·요구사항 추적성은 아키텍처가 충분히 대행하므로 **구현 착수에 지장 없음.**

## 5. Epic Quality Review

### 에픽 사용자 가치 (User Value)
| Epic | 가치 중심? | 판정 |
|------|-----------|------|
| 1 기반+인증·계정 | 가입/로그인/접근제어 (스캐폴딩 스토리 1.1 포함) | ✓ (스캐폴딩은 아키텍처가 스타터 지정 → Epic 1 첫 스토리로 정석) |
| 2 판매자 매물 등록·관리 | 판매자가 차를 판다 | ✓ |
| 3 구매자 매물 탐색 | 구매자가 차를 찾는다 | ✓ |
| 4 AI 검색 어시스턴트 | 자연어로 매물 검색(핵심) | ✓ |
| 5 문의 채팅 | 구매자↔판매자 대화 | ✓ |
| 6 관리자 | 운영 관리 | ✓ |
| 7 Flutter 앱 | 모바일 구매자·판매자 여정 | ✓ |
- **기술 밀어내기(technical milestone) 에픽 없음.** 모든 에픽이 사용자 결과로 표현됨.

### 에픽 독립성 / 의존성 방향
- Epic 2→1, 3→2, 4→2, 5→(2·1), 6→전체, 7→(1~5) — **모두 후방(과거) 의존**. ✓
- Epic 7.1 골격을 "Epic 1 직후 선행" 배치 → 7.1은 인증(Epic 1)만 필요, 7.2~7.5는 Epic 4 직후. **스케줄링일 뿐 전방 의존 아님.** ✓
- **순환 의존 없음.**

### DB 테이블 생성 타이밍
- ✅ **올바른 패턴** — 테이블을 Epic 1에 몰지 않고 "처음 필요한 에픽"에서 생성: `listings`=Epic 2(2.1), `chat`=Epic 5(5.1), `guide_documents`=Epic 4(4.2). 각 에픽 첫 스토리가 자기 토대를 만드는 BMAD "기반 흡수" 패턴.

### Acceptance Criteria 품질
- 전 스토리 **Given/When/Then(BDD) 준수**, 해피패스 + 에러 + 엣지(중복 이메일·sold 접근·CHECK 위반·RLS 차단·0건 안내) 망라. **품질 우수.**

---

### 🔴 Critical Violations
- **없음.**

### 🟠 Major Issues
- **M1. RLS 마이그레이션 타이밍 불일치. — ✅ 해소(2026-06-19, 권고 ⓐ 채택)** architecture.md·epics.md에 반영 완료. RLS를 각 테이블 마이그레이션에 동거(0001=profiles RLS, 0002=listings 소유권·FR11 RLS, 0003=chat 참여자 RLS)시키고 `0005_rls_policies`→`0005_admin_policies`(관리자 전권 교차 정책)로 재정의. 관련 스토리 AC(1.4·2.1·3.3·5.1·6.1)도 "동거" 명시로 갱신. 아래는 원 발견 기록. 아키텍처 AR2가 RLS를 단일 `0005_rls_policies.sql`(0001~0004 **이후** 적용)로 묶었는데, 스토리는 RLS를 더 이른 시점에 요구한다:
  - Story 1.4(Epic 1) "profiles RLS 정책이 적용되면" → 0005 전체가 깔리기 전엔 미충족
  - Story 2.1/2.3(Epic 2) "소유권 RLS가 적용되면" → 마찬가지
  - **영향:** 마이그레이션을 0001→0006 순서로 적용하면 Epic 1·2 시점에 필요한 RLS가 아직 없어 해당 스토리 AC 검증이 막힌다.
  - **권고(택1):** ⓐ RLS를 각 테이블 마이그레이션에 동거(0001에 profiles RLS, 0002에 listings 소유권 RLS …)시키고 0005는 admin·교차 정책만 담거나, ⓑ 0005를 "논리적 묶음"이 아닌 **에픽 진행에 맞춘 분할 적용**으로 재정의. → **구현 첫 스토리(1.1) 또는 2.1에서 확정 권장.**

### 🟡 Minor Concerns
- **m1. 기술 토대 스토리(2.1·2.5·4.1·4.2·7.1·7.6).** DB/스캐폴딩/시드/검증 전용으로 직접적 사용자 가치는 약함. 단 "처음 필요 시점"에 위치하고 BMAD 기반 흡수 패턴에 부합 → **수용 가능**(기술 에픽 위반 아님).
- **m2. Story 2.5 → Epic 4 backfill 전방 참조.** "embedding 우선 NULL, Epic 4에서 적재" — Story 2.5는 NULL로 **독립 완료 가능**하고 임베딩은 Epic 4 전까지 불필요. 전방 *의존*이 아닌 *참조* → 양호하나 인지 필요.
- **m3. 차형 용어 매핑(세단·해치백)** 은 OI5로 이연됨(Story 4.5·4.8). 이미 추적 중 → 데모 질의셋 작성 시 누락 주의.

### Best Practices Compliance Checklist
- [x] 에픽이 사용자 가치 전달 · [x] 에픽 독립 기능 · [x] 스토리 적정 사이징
- [x] 전방 의존성 없음(M-수준 아님) · [x] DB 테이블 적시 생성 · [x] 명확한 AC · [x] FR 추적성 유지
- [x] 스타터 템플릿 → Epic 1 첫 스토리(1.1)로 반영

## 6. Summary and Recommendations

### Overall Readiness Status
**READY** — 구현 착수 가능. 차단(Critical) 이슈 없음. 유일한 Major였던 **M1(RLS 마이그레이션 타이밍)은 2026-06-19 문서에 반영·해소**되어 잔여 차단 요소 없음.

| 항목 | 결과 |
|------|------|
| 문서 인벤토리 | PRD·Architecture·Epics 완비, UX 부재(비차단) |
| FR 커버리지 | **25/25 = 100%** |
| NFR·AR·OI 매핑 | 모두 소유 스토리 보유 |
| UX 정합 | 아키텍처가 화면 구조로 대행, 정합 |
| 에픽 품질 | Critical 0 / Major 1 / Minor 3 |

### Critical Issues Requiring Immediate Action
- **없음.** 즉시 차단 요소 없음.

### 착수 전 정리 권장 (Major)
1. **M1 — ✅ 완료.** RLS를 각 테이블 마이그레이션에 동거, `0005_admin_policies`로 재정의. architecture.md·epics.md 반영 끝. 추가 조치 불필요.

### Recommended Next Steps
1. **Story 1.1 착수** — M1 반영 완료, 마이그레이션 구조 확정됨. 바로 스캐폴딩 시작 가능.
2. **구현 시점 오픈이슈 처리** — OI2(Text-to-SQL 방식, Story 4.3) · OI5(데모 질의셋+차형 매핑, Story 4.5·4.8) · OI6(RAG 코퍼스 작성, Story 4.2). 모두 소유 스토리에 배정됨 — 해당 스토리에서 산출.
3. **사용자 직접 처리 항목 준비**(아래 핸드오프 참조) — Supabase 프로젝트·Gemini 키·환경변수.
4. (선택) **m1~m3 인지** — 기술 토대 스토리·backfill 전방참조·차형 매핑 누락 주의. 별도 조치 불필요.
5. (선택) **UX 보강** — 필요 시 `bmad-ux`로 시각/인터랙션 명세 추가(데모엔 불필요).

### Final Note
본 평가는 **4개 카테고리(문서·커버리지·UX·에픽품질)에서 총 4건의 이슈**(Major 1 · Minor 3)를 식별했으며 **Critical은 0건**입니다. M1만 착수 첫 스토리에서 정리하면 그대로 구현을 진행해도 좋습니다. 산출물의 추적성·일관성·안전장치 설계 수준이 매우 높아, 데모/과제 기준으로 **구현 준비 완료(Confidence: High)** 로 판정합니다.

---
**Assessor:** Winston (System Architect, PM hat) · **Date:** 2026-06-19






