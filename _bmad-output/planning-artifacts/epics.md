---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/prd.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/addendum.md
  - _bmad-output/planning-artifacts/architecture.md
---

# bmad-encar-demo - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for bmad-encar-demo, decomposing the requirements from the PRD and Architecture requirements into implementable stories. (UX Design 문서는 작성되지 않았으며, 아키텍처가 화면·라우트 구조로 대체한다.)

## Requirements Inventory

### Functional Requirements

**F1. 인증·계정**
- FR1: 사용자는 이메일/비밀번호로 가입하며, 가입 시 역할(구매자/판매자)을 선택한다. (Supabase Auth, 소셜 로그인 제외)
- FR2: 사용자는 로그인/로그아웃할 수 있다.
- FR3: 역할별 접근 제어 — 역할(구매자/판매자/관리자)에 따라 사용 기능이 다르다.
- FR4: 관리자 계정이 별도로 존재한다(시드 또는 별도 경로 생성).

**F2. 매물 등록·관리 (판매자)**
- FR5: 판매자는 차량 매물을 등록한다(15필드: 제조사·모델·차종·연식·가격·주행거리·색상·연료·변속기·배기량·인승·지역·사고이력·옵션·설명). **사진 제외**(RAG 목표 집중, Supabase Storage 미사용).
- FR6: 판매자는 본인 매물만 조회/수정/삭제할 수 있다.
- FR7: 등록한 매물은 즉시 노출된다(관리자 사전 승인 없음).
- FR8: 판매자는 본인 매물을 "구매 완료" 처리하여 판매 완료 상태로 전환한다(판매자만, 상대 지정 불필요).

**F3. 매물 탐색 (구매자)**
- FR9: 구매자는 키워드/필터(가격·연식·차종·색상·연료·변속기·지역 등)로 매물을 검색한다.
- FR10: 구매자는 매물 상세를 조회한다(설명·옵션·상태 포함, 사진 없음).
- FR11: 판매 완료 매물은 구매자의 모든 화면(필터·AI·목록·상세)에서 노출되지 않는다(단일 규칙).

**F4. AI 검색 어시스턴트 (핵심)**
- FR12: 구매자는 AI 채팅 어시스턴트에 자연어 한 문장으로 매물을 검색한다.
- FR13: 라우터가 질문 의도를 분류한다 — (A) 구조형 / (B) 질적·의미형 / (C) 매물 무관.
- FR14: (A) 구조형 → Text-to-SQL로 매물 DB를 정밀 필터링한다(SELECT 전용·범위 제한, FR11 준수).
- FR15: (B) 질적·의미형 → 문서 기반 RAG(pgvector)로 매물을 추천한다. 코퍼스 = ① 매물 설명·옵션 텍스트 + ② 차량 상식·가이드 문서.
- FR16: (C) 매물 무관 → 정중히 거절하고 매물 검색으로 유도한다(순수 상식 Q&A 미제공).
- FR17: 답변은 자연어 설명 + 매물 카드로 반환한다. 0건이면 조건 완화 안내를 반환한다.
- FR18: 멀티턴 — 직전 대화 맥락은 클라이언트가 보관해 후속 질문을 지원한다. 서버·DB에 AI 대화 미저장.

**F5. 문의 채팅 (구매자 ↔ 판매자)**
- FR19: 구매자가 문의를 보내면 양쪽에 동일한 채팅방이 생성된다.
- FR20: 양측이 폴링 방식으로 메시지를 주고받는다.
- FR21: 채팅 메시지는 DB에 저장된다(AI 대화 이력과 별개).

**F6. 관리자**
- FR22: 회원 목록 조회 + 정지/삭제.
- FR23: 전체 매물 조회 + (부적절 매물) 삭제.
- FR24: 거래 내역(판매 완료 매물 목록) 조회.
- FR25: 채팅방 열람 + 삭제.

### NonFunctional Requirements

- NFR1: 성능 — AI 검색 응답 통상 수 초(Gemini 호출 1~2회), 채팅 폴링 준실시간(3~5초).
- NFR2: 보안·권한 — Text-to-SQL 결정론적 안전장치(① 읽기 전용 DB 롤 ② 기본 LIMIT 강제 ③ 실행 전 쿼리 검증: SELECT 전용·테이블/컬럼 화이트리스트). 본인 매물만 수정/삭제(FR6), 역할별 접근 제어(FR3), RLS 적용.
- NFR3: 플랫폼 — 반응형 웹(사용자·관리자) + Flutter 앱에서 핵심 기능 동작.
- NFR4: 배포·확장 — Vercel 단일 배포(무상태), 상태는 Supabase 저장. 차선: 백엔드만 Cloud Run/Railway 분리.
- NFR5: 데이터·프라이버시 — 채팅 메시지 영속, AI 대화 이력 미저장(클라이언트 보관, 세션 종료 시 소멸).
- NFR6: 비용 — Gemini 무료 등급 · Vercel Hobby · Supabase 무료/저가 티어 범위.

### Additional Requirements

(아키텍처 도출 — 구현·인프라·일관성 요구사항)

- AR1: 스타터 스캐폴딩 — 경량 폴더 모노레포(`web`/`app`/`api`/`supabase` 한 저장소 공존), 각 파트 공식 CLI 부트스트랩. 버전: Next.js 16.2.7 · Flutter 3.44.0 · FastAPI 0.137.1 · LangGraph 1.2.4. **→ Epic 1 첫 스토리.**
- AR2: DB 마이그레이션 6종 — `0001_profiles`(+profiles RLS) · `0002_listings`(15필드+status+embedding, 사진 제외, +소유권·FR11 비노출 RLS) · `0003_chat`(+참여자 RLS) · `0004_guide_documents` · `0005_admin_policies`(관리자 전권 교차 정책) · `0006_readonly_role`. **RLS 배치 원칙:** 각 테이블 RLS는 그 테이블 마이그레이션에 동거(0001→0006 순서 적용 시 에픽 시점마다 필요한 RLS가 이미 존재) — 관리자 전권 교차 정책만 `0005`로 분리. 단일 스키마 출처 = `supabase/migrations/`.
- AR3: AI 전용 읽기 전용 Postgres 롤 + SELECT 검증·기본 LIMIT 강제(`api/db/sql_guard.py`) — NFR2 결정론적 안전장치.
- AR4: pgvector HNSW 인덱스, 임베딩 `vector(768)` 차원 정합(생성·저장·검색 전 구간 일치). 임베딩 모델 `gemini-embedding-001`(768).
- AR5: 폴리글랏 일관성 규칙 강제 — 통신선 snake_case, 단위(km·원·cc), AI 응답 `{answer, listings[]}`·에러 `{error:{code,message}}` 공통 포맷. (ESLint/flutter_lints/ruff로 강제)
- AR6: 환경변수 주입 — Gemini API 키 · Supabase URL/키 · `GEMINI_EMBEDDING_DIM=768`. Supabase 연결 풀링 설정(무상태 서버리스 대응).
- AR7: 시드 데이터 — 관리자 계정 · 샘플 매물 · 가이드 문서(`supabase/seed.sql`). CHECK 목록값 = UI 드롭다운·Text-to-SQL 허용값·질의셋과 동일.
- AR8: 구현 시점 확정(오픈이슈) — OI2(Text-to-SQL 방식: SQL Agent vs 제약 Chain + 라우터 Pydantic 스키마) · OI5(데모 질의셋: 구조형/질적/회색/무관 + 차형 용어 매핑) · OI6(RAG 코퍼스 실제 문서 내용).
- AR9: Flutter 모바일 앱(NFR3) — 범위 = **구매자 여정 + 판매자 여정**(매물 등록·관리·구매완료 포함), **관리자만 제외**(web 전용). web이 확정한 Supabase 스키마/RLS + `/ai/search` 계약을 재사용. 별도 **Epic 7**으로 분리.
- AR10: **Supabase Storage 미사용** — 사진 개념 전면 제거에 따라 파일 저장소·업로드 경로·모바일 카메라/갤러리 권한 모두 불필요(공유 계약은 DB 테이블 + `/ai/search`로 한정).

### UX Design Requirements

(해당 없음 — UX Design 명세 문서 미작성. 화면·라우트 구조는 architecture.md의 프로젝트 구조 정의를 따른다.)

### FR Coverage Map

| FR | Epic | 설명 |
|----|------|------|
| FR1 | Epic 1 | 역할 선택 가입 |
| FR2 | Epic 1 | 로그인/로그아웃 |
| FR3 | Epic 1 | 역할별 접근 제어(RBAC) |
| FR4 | Epic 1 | 관리자 계정 |
| FR5 | Epic 2 | 매물 등록(15필드, 사진 제외) |
| FR6 | Epic 2 | 본인 매물만 수정/삭제(소유권 RLS) |
| FR7 | Epic 2 | 즉시 노출 |
| FR8 | Epic 2 | "구매 완료" 상태 전환 |
| FR9 | Epic 3 | 키워드/필터 검색 |
| FR10 | Epic 3 | 매물 상세 조회 |
| FR11 | Epic 3 | 판매완료 비노출(단일 규칙) |
| FR12 | Epic 4 | AI 자연어 검색 진입 |
| FR13 | Epic 4 | 라우터 3분류 |
| FR14 | Epic 4 | 경로 A Text-to-SQL |
| FR15 | Epic 4 | 경로 B 문서 RAG |
| FR16 | Epic 4 | 경로 C 가드 |
| FR17 | Epic 4 | 자연어+매물카드 응답, 0건 안내 |
| FR18 | Epic 4 | 멀티턴(클라이언트 보관) |
| FR19 | Epic 5 | 채팅방 생성 |
| FR20 | Epic 5 | 폴링 송수신 |
| FR21 | Epic 5 | 메시지 DB 영속 |
| FR22 | Epic 6 | 회원 조회·정지/삭제 |
| FR23 | Epic 6 | 전체 매물 조회·삭제 |
| FR24 | Epic 6 | 거래내역 조회 |
| FR25 | Epic 6 | 채팅방 열람·삭제 |
| FR5~21 (구매자·판매자분) | Epic 7 | 위 기능을 Flutter 앱에서 재현(관리자 FR22~25 제외) |

→ **FR1~25 전부 매핑.** Epic 7은 새 FR이 아니라 기존 FR을 모바일에서 재현하는 플랫폼 에픽(NFR3·AR9).

## Epic List

> **설계 결정 반영(파티 모드 합의):** 순서 1→2→3→4→5→6, 앱은 별도 **Epic 7**(Epic 4 직후 착수, 단 골격 스토리는 Epic 1 직후 선행). 계약(임베딩 768·읽기전용 롤·status enum·RLS 네이밍)은 Epic 1에 집중. **사진 개념 전면 제거**(Storage 미사용). 검증(SM3·CM1·CM2·SM1 통합 시연)은 명시 스토리/AC로.

### Epic 1: 프로젝트 기반 + 인증·계정
사용자가 역할(구매자/판매자)을 선택해 가입하고 로그인하며, 역할별로 접근이 제어된다. 관리자 계정이 존재한다. (web 스캐폴딩 + 공유 계약 단일출처 확정 포함)
**FRs covered:** FR1, FR2, FR3, FR4
**기반/계약 흡수:** 모노레포+web 스캐폴딩(AR1, app/api는 후행) · `0001_profiles`+profiles RLS · **공유 계약 단일출처**(임베딩 768 상수·읽기전용 롤 권한·`status` enum·RLS 네이밍 — AR4·AR5) · 환경변수(AR6).

### Epic 2: 판매자 매물 등록·관리
판매자가 차량을 등록(15필드, 사진 없음)하고, 본인 매물만 수정/삭제하며, "구매 완료"로 판매완료 전환한다.
**FRs covered:** FR5, FR6, FR7, FR8
**기반 흡수:** `0002_listings`(15필드+status+embedding 컬럼, 사진 제외) · **소유권·status 전환 가드를 DB측(RLS+CHECK/트리거)으로 못박는 스토리**(Winston — 앱 합류 전 선치) · `status`/FR11 비노출 기준 동결 · 샘플 매물 시드 일부(AR7).

### Epic 3: 구매자 매물 탐색
구매자가 키워드/필터로 매물을 검색하고 상세를 조회한다. 판매완료 매물은 모든 경로에서 보이지 않는다.
**FRs covered:** FR9, FR10, FR11
**기반 흡수:** FR11 비노출 RLS(`0002`에 동거) 적용·검증 AC.

### Epic 4: AI 검색 어시스턴트 (핵심 차별점)
구매자가 자연어 한 문장으로 매물을 찾는다 — 라우터 3분류 → Text-to-SQL(A)·문서 RAG(B)·가드(C), 자연어+매물카드 응답, 멀티턴.
**FRs covered:** FR12, FR13, FR14, FR15, FR16, FR17, FR18
**기반 흡수:** `api/` 스캐폴딩(FastAPI+LangGraph) · 읽기전용 롤(AR3) · `0004_guide_documents`+pgvector HNSW(AR4) · **임베딩 backfill 스토리**(기존 매물 768 임베딩 일괄 적재, Winston) · 시드 매물·가이드 코퍼스(OI6)·데모 질의셋(OI5) **소유 스토리 명시** · **검증 AC: SM3(2경로 시연)·CM1(가드 거절)·CM2(SELECT 안전범위 차단)**.

### Epic 5: 문의 채팅
구매자↔판매자가 매물에 대해 폴링 방식으로 대화한다.
**FRs covered:** FR19, FR20, FR21
**기반 흡수:** `0003_chat`(rooms·messages) · 폴링 동작확인 기준("메시지 insert→상대 폴링 1건").

### Epic 6: 관리자
운영자가 회원·매물·거래내역·채팅을 조회/삭제한다. (web 전용)
**FRs covered:** FR22, FR23, FR24, FR25
**기반 흡수:** `(admin)` 라우트 가드 + 관리자 전권 교차 정책(`0005_admin_policies`).

### Epic 7: Flutter 모바일 앱 (구매자 + 판매자)
구매자(AI검색→상세→문의채팅)와 판매자(등록→문의응대→구매완료) 핵심 여정을 모바일 앱에서 수행한다. 관리자 제외. web이 확정한 Supabase 스키마/RLS + `/ai/search` 계약 재사용.
**FRs covered:** (재현) FR1~3, FR5~21 중 구매자·판매자 여정 — 관리자 FR22~25 제외
**착수 시점:** Epic 4 직후. 단 7.1 골격 스토리는 Epic 1 직후 선행.
**슬라이스(Amelia, 사진 제거로 업로드 스토리 소멸):** 7.1 골격(flutter create+인증 연동) → 7.2 구매자(목록·상세·AI검색) → 7.3 판매자 등록(15필드 폼) → 7.4 본인매물 관리+구매완료 → **7.5 SM1 통합 시연 검증**(앱 구매자①·판매자② end-to-end + web 3종 시나리오 리허설).
**크기 통제 기준:** "이 화면이 SM1 시나리오 ①②의 한 스텝인가?" 아니면 컷(풀패리티 금지).

---

## Epic 1: 프로젝트 기반 + 인증·계정

사용자가 역할(구매자/판매자)을 선택해 가입·로그인하고, 역할별로 접근이 통제된다. 관리자 계정이 존재한다. (web 스캐폴딩 + 공유 계약 단일출처 포함)

### Story 1.1: 모노레포 스캐폴딩 + Supabase 연결 + 공유 계약 단일출처

As a 개발자,
I want web 앱 골격과 Supabase 프로젝트를 연결하고 공유 규약(임베딩 768 상수·네이밍·환경변수)을 한 곳에 고정하고 싶다,
So that 이후 모든 기능이 흔들리지 않는 토대 위에서 개발될 수 있다.

**Acceptance Criteria:**

**Given** 빈 저장소에서
**When** `create-next-app`으로 `web/`(Next.js 16, TS·Tailwind·App Router·src)를 생성하면
**Then** 개발 서버가 기동되고 기본 페이지가 뜬다
**And** `app/`·`api/`는 이 스토리 범위가 아니다(후행 에픽)

**Given** Supabase 프로젝트가 있을 때
**When** `web/lib/supabase/`(client·server)와 `.env.local`(Supabase URL/anon key, `GEMINI_EMBEDDING_DIM=768`)을 설정하면
**Then** 앱이 Supabase에 연결된다

**Given** 폴리글랏 일관성 규칙(AR5)을
**When** 공유 상수/문서로 명문화하면
**Then** 임베딩 차원(768)·통신선 snake_case·단위(km·원·cc) 규약이 단일 출처로 존재한다
**And** `.env.example`에 필요한 환경변수 키가 비밀값 없이 문서화된다

### Story 1.2: 역할 선택 회원가입 (FR1)

As a 신규 사용자,
I want 이메일·비밀번호로 가입하면서 구매자/판매자 역할을 선택하고 싶다,
So that 내 역할에 맞는 기능을 쓸 수 있다.

**Acceptance Criteria:**

**Given** `0001_profiles` 마이그레이션이 적용되면
**When** 스키마를 확인하면
**Then** `profiles(id→auth.users, role check(buyer/seller/admin), status check(active/suspended))`가 존재한다

**Given** 가입 화면에서
**When** 이메일·비밀번호·역할(구매자/판매자)을 입력해 제출하면
**Then** Supabase Auth 계정과 `profiles`(role, status=active) 행이 함께 생성된다

**Given** 이미 가입된 이메일로
**When** 다시 가입을 시도하면
**Then** 한국어 오류 메시지로 거절된다
**And** 역할은 가입 시 1개로 고정된다(둘 다 하려면 계정 2개)

### Story 1.3: 로그인 / 로그아웃 (FR2)

As a 가입한 사용자,
I want 로그인·로그아웃하고 싶다,
So that 내 세션으로 서비스를 이용하거나 안전하게 종료할 수 있다.

**Acceptance Criteria:**

**Given** 유효한 자격으로
**When** 로그인하면
**Then** 세션이 생성되고 역할에 맞는 첫 화면으로 이동한다

**Given** 잘못된 자격으로
**When** 로그인하면
**Then** 한국어 오류 메시지가 표시되고 세션이 생기지 않는다

**Given** 로그인 상태에서
**When** 로그아웃하면
**Then** 세션이 파기되고 보호 화면 접근이 차단된다

### Story 1.4: 역할별 접근 제어 + profiles RLS (FR3)

As a 서비스 운영 주체,
I want 역할(구매자/판매자/관리자)에 따라 화면·데이터 접근을 통제하고 싶다,
So that 권한 밖 기능·데이터에 접근하지 못하게 한다.

**Acceptance Criteria:**

**Given** `middleware.ts` 라우트 가드가 있을 때
**When** 비로그인 사용자가 보호 경로에 접근하면
**Then** 로그인으로 리다이렉트된다

**Given** `0001_profiles`에 동거된 profiles RLS 정책이 적용되면 (별도 RLS 묶음 마이그레이션 대기 없이 Epic 1 시점에 활성)
**When** 사용자가 profiles를 조회하면
**Then** 본인 행만 읽히고, 관리자만 전체를 읽는다

**Given** 판매자 계정으로
**When** 구매자 전용/관리자 전용 기능에 접근하면
**Then** 역할 분기로 차단된다

### Story 1.5: 관리자 계정 시드 (FR4)

As a 운영자,
I want 별도 관리자 계정이 미리 존재하길 원한다,
So that 가입 흐름과 무관하게 관리 기능에 진입할 수 있다.

**Acceptance Criteria:**

**Given** `supabase/seed.sql`이
**When** 실행되면
**Then** `role='admin'` 프로필을 가진 관리자 계정 1개가 생성된다

**Given** 관리자 계정으로
**When** 로그인하면
**Then** 관리자 권한이 인식된다(관리자 화면은 Epic 6)
**And** 일반 가입 경로로는 admin 역할을 선택할 수 없다

## Epic 2: 판매자 매물 등록·관리

판매자가 차량을 등록(15필드, 사진 없음)하고, 본인 매물만 수정/삭제하며, "구매 완료"로 판매완료 전환한다.

### Story 2.1: listings 스키마 + 소유권·status 가드(DB측)

As a 개발자,
I want `listings` 테이블과 소유권·상태전환 규칙을 DB(RLS+CHECK)에 못박고 싶다,
So that 웹·앱 어느 클라이언트가 붙어도 권한·상태 무결성이 한 곳에서 보장된다.

**Acceptance Criteria:**

**Given** `0002_listings` 마이그레이션이 적용되면
**When** 스키마를 확인하면
**Then** FR5 15필드 + `seller_id`·`status check(on_sale/sold)`·`embedding vector(768)`·타임스탬프가 존재한다(사진 컬럼 없음)
**And** 고정 목록(manufacturer·body_type·color·fuel·transmission·region)은 `CHECK`로 강제된다
**And** 소유권 RLS(FR6) + 판매완료 비노출 RLS(FR11)가 **같은 `0002_listings` 마이그레이션에 동거**해 함께 적용된다(별도 RLS 묶음 대기 없음)

**Given** 소유권 RLS가 적용되면
**When** 판매자가 매물을 수정/삭제하면
**Then** `auth.uid() = seller_id`인 본인 매물만 허용된다(FR6 기반)

**Given** status 전환 규칙(CHECK/정책)이 있을 때
**When** `on_sale`↔`sold` 외 값이나 타인 매물 전환을 시도하면
**Then** DB가 거부한다

### Story 2.2: 매물 등록 + 즉시 노출 (FR5, FR7)

As a 판매자,
I want 차량 정보를 입력해 매물을 등록하고 싶다,
So that 구매자에게 바로 노출된다.

**Acceptance Criteria:**

**Given** 판매자로 로그인한 상태에서
**When** 15필드 등록 폼을 채워 제출하면
**Then** `listings` 행이 `status=on_sale`로 생성되고 즉시 목록에 노출된다(관리자 승인 없음)

**Given** CHECK 제약을 위반하는 값(목록 외 차종 등)으로
**When** 제출하면
**Then** 한국어 검증 오류로 거절된다

**And** 단위 규칙(price=원, mileage=km, displacement=cc)대로 저장된다

### Story 2.3: 본인 매물 조회·수정·삭제 (FR6)

As a 판매자,
I want 내가 올린 매물만 조회·수정·삭제하고 싶다,
So that 내 매물을 안전하게 관리한다.

**Acceptance Criteria:**

**Given** 판매자로 로그인한 상태에서
**When** 내 매물 목록을 열면
**Then** 본인 매물만 보인다

**Given** 본인 매물을
**When** 수정/삭제하면
**Then** 반영된다

**Given** 타인 매물 id로
**When** 수정/삭제를 시도하면
**Then** RLS로 차단된다

### Story 2.4: 구매 완료 처리 (FR8)

As a 판매자,
I want 거래가 끝난 매물을 "구매 완료"로 표시하고 싶다,
So that 더 이상 구매자에게 노출되지 않는다.

**Acceptance Criteria:**

**Given** 본인 매물 상세에서
**When** "구매 완료"를 누르면
**Then** `status`가 `sold`로 바뀐다(판매자만, 상대 지정 불필요)

**Given** 이미 `sold`이거나 타인 매물이면
**When** 전환을 시도하면
**Then** 거부된다

### Story 2.5: 샘플 매물 시드

As a 개발자/시연자,
I want 텍스트 필드가 채워진 샘플 매물 다수를 시드하고 싶다,
So that 탐색·AI 검색을 실제 데이터로 검증·시연할 수 있다.

**Acceptance Criteria:**

**Given** `supabase/seed.sql`이
**When** 실행되면
**Then** CHECK 목록값을 따르는 샘플 매물 ≥35건이 생성된다(사진 없음)
**And** `embedding`은 우선 NULL이며 Epic 4에서 일괄 적재(backfill)된다
**And** 시드 값은 UI 드롭다운·Text-to-SQL 허용값과 동일하다
**And** 차종·가격대·연료·지역이 고루 분포해 필터·AI 검색 시연이 풍성하다

## Epic 3: 구매자 매물 탐색

구매자가 키워드/필터로 매물을 검색하고 상세를 조회한다. 판매완료 매물은 모든 경로에서 보이지 않는다.

### Story 3.1: 매물 목록 + 필터 검색 (FR9)

As a 구매자,
I want 키워드/필터로 매물을 검색하고 싶다,
So that 원하는 조건의 매물을 찾는다.

**Acceptance Criteria:**

**Given** 매물 목록 화면에서
**When** 필터(가격·연식·차종·색상·연료·변속기·지역)나 키워드를 적용하면
**Then** 조건에 맞는 `on_sale` 매물만 반환된다

**Given** 조건에 맞는 매물이 없으면
**When** 검색하면
**Then** 빈 상태 안내가 표시된다

**And** 가격·주행거리는 단위 규칙대로 표시된다(예: 29,800,000원 / 103,000km)

### Story 3.2: 매물 상세 조회 (FR10)

As a 구매자,
I want 매물 상세를 보고 싶다,
So that 구매 판단에 필요한 정보를 확인한다.

**Acceptance Criteria:**

**Given** 목록에서 매물을 선택하면
**When** 상세 화면이 열리면
**Then** 15필드 정보 + 설명·옵션·상태가 표시된다(사진 없음)

**Given** `sold` 매물 id로
**When** 상세 접근을 시도하면
**Then** 구매자에게는 노출되지 않는다(FR11)

### Story 3.3: 판매완료 비노출 단일 규칙 (FR11)

As a 서비스,
I want 판매완료 매물을 구매자의 모든 경로에서 숨기고 싶다,
So that 거래 불가능한 매물이 노출되지 않는다.

**Acceptance Criteria:**

**Given** FR11 비노출 RLS/쿼리 공통 규칙이 적용되면 (정책은 `0002_listings`에 동거 — Epic 3 시점에 이미 활성)
**When** 구매자가 목록·필터검색·상세에 접근하면
**Then** `status='sold'` 매물은 어느 경로에서도 보이지 않는다

**Given** 매물이 `sold`로 바뀌면
**When** 구매자가 재조회하면
**Then** 즉시 목록에서 사라진다(데이터 정합 CM3)

## Epic 4: AI 검색 어시스턴트 (핵심 차별점)

구매자가 자연어 한 문장으로 매물을 찾는다 — 라우터 3분류 → Text-to-SQL(A)·문서 RAG(B)·가드(C), 자연어+매물카드 응답, 멀티턴.

### Story 4.1: api 스캐폴딩 + 읽기전용 롤 + JWT 검증

As a 개발자,
I want AI 전용 FastAPI+LangGraph 백엔드와 읽기전용 DB 롤·JWT 검증을 세우고 싶다,
So that 안전한 토대 위에서 AI 검색 노드를 구현한다.

**Acceptance Criteria:**

**Given** `api/`가 스캐폴딩되면
**When** `POST /ai/search`를 호출하면
**Then** FastAPI 앱이 응답하고 OpenAPI 문서가 노출된다

**Given** `0006_readonly_role` 마이그레이션이 적용되면
**When** AI 경로가 DB에 접근하면
**Then** SELECT만 가능한 읽기전용 롤로 실행된다(NFR2)

**Given** Supabase JWT 검증(`auth.py`)이 있을 때
**When** 미인증 요청이 오면
**Then** 401로 거절된다(로그인 구매자만 허용)

### Story 4.2: 문서 RAG 코퍼스 작성 + guide_documents + pgvector HNSW + 임베딩 backfill

As a 개발자,
I want 문서 RAG의 기반이 될 차량 상식·구매 가이드 문서를 직접 작성하고, 코퍼스·벡터 인덱스를 만들어 매물·문서 임베딩을 일괄 적재하고 싶다,
So that 문서 RAG와 의미 검색이 실제 데이터로 동작한다.

**Acceptance Criteria:**

**Given** `0004_guide_documents` 마이그레이션이 적용되면
**When** 스키마를 확인하면
**Then** `guide_documents(title, content, embedding vector(768))` + HNSW 인덱스가 존재한다

**Given** 문서 RAG의 기반이 될 코퍼스(OI6)를
**When** 실제 내용으로 **작성**하면
**Then** 차종별 특성·패밀리카/초보자 적합 차종·유지비/신뢰성 등 가이드 문서가 준비된다(경로 B의 검색 대상)
**And** 작성 문서가 `guide_documents`에 적재된다

**Given** 코퍼스 문서와 시드 매물의 설명·옵션 텍스트가
**When** Gemini 768 임베딩으로 적재되면
**Then** `guide_documents`와 시드 매물 `embedding`이 채워진다(차원 768 일치)

**Given** 시드 매물의 `embedding`이 NULL일 때
**When** backfill 작업을 실행하면
**Then** 설명·옵션 텍스트가 768 임베딩으로 채워진다
**And** 임베딩 차원(768)이 컬럼과 일치한다

### Story 4.3: 경로 A — Text-to-SQL + 안전장치 (FR14)

As a 구매자,
I want 구조형 조건을 자연어로 말하면 정확히 필터된 매물을 받고 싶다,
So that 가격·차종 등 조건 검색을 대화로 한다.

**Acceptance Criteria:**

**Given** Text-to-SQL 노드(`sql_rag_node`)가 있을 때
**When** "3천만원 이하 흰색 SUV" 류 질의가 오면
**Then** 구조 조건으로 필터된 `on_sale` 매물이 반환된다(FR11 준수)

**Given** `sql_guard`가 적용되면
**When** 생성 쿼리를 실행하면
**Then** SELECT 전용·기본 LIMIT·테이블/컬럼 화이트리스트 검증을 통과한 쿼리만 실행된다

**Given** SELECT 외 구문이나 범위 밖 쿼리가
**When** 생성되면
**Then** 실행 전 차단된다(CM2 검증)
**And** 자연어 단위("10만km")가 저장 단위(km 정수)로 정규화된다

### Story 4.4: 경로 B — 문서 기반 RAG (FR15)

As a 구매자,
I want "패밀리카로 무난한 거" 같은 의미형 질문에도 적합 매물을 받고 싶다,
So that 정확한 조건을 몰라도 추천받는다.

**Acceptance Criteria:**

**Given** 문서 RAG 노드(`doc_rag_node`)가 있을 때
**When** 질적/의미형 질의가 오면
**Then** 매물 설명·옵션 텍스트 + 가이드 문서를 pgvector 유사도 검색해 적합 차종/특성 근거를 얻는다

**Given** 근거 조건으로
**When** 매물을 조회하면
**Then** `on_sale` 매물만 추천된다(FR11)

### Story 4.5: 라우터 분류 + 가드 + 답변 조립 (FR13, FR16, FR17)

As a 구매자,
I want 어떤 질문이든 의도에 맞게 처리되고 자연어+매물카드로 답을 받고 싶다,
So that 한 창에서 자연스럽게 검색한다.

**Acceptance Criteria:**

**Given** 라우터 노드가 있을 때
**When** 질의가 오면
**Then** (A)구조형 / (B)질적·의미형 / (C)무관으로 분류된다(FR13)

**Given** 매물과 무관한 질의(C)가
**When** 오면
**Then** 정중히 거절하고 매물 검색으로 유도한다(FR16, CM1 가드)

**Given** 검색 결과가 있을 때
**When** 답변을 조립하면
**Then** `{answer, listings[]}` 공통 계약으로 자연어 설명 + 매물카드를 반환한다

**Given** 결과가 0건이면
**When** 답변하면
**Then** 빈 목록 대신 조건 완화 안내를 반환한다(FR17)
**And** OI5 데모 질의셋(구조형/질적/회색/무관 + 차형 용어 매핑)이 작성된다

### Story 4.6: 멀티턴 맥락 (FR18)

As a 구매자,
I want 직전 대화에 이어 후속 질문을 하고 싶다,
So that "그 중 더 싼 거" 같은 맥락 대화를 한다.

**Acceptance Criteria:**

**Given** 클라이언트가 직전 대화 맥락을 보관할 때
**When** 후속 질의에 맥락을 동봉해 보내면
**Then** 서버는 그 맥락을 반영해 답한다(서버 무상태)

**Given** 새로고침/세션 종료 시
**When** 다시 보면
**Then** AI 대화 이력은 저장되지 않아 초기화된다(서버·DB 미저장)

### Story 4.7: AI 검색 UI (FR12)

As a 구매자,
I want 채팅창에 자연어로 입력해 매물을 찾고 싶다,
So that 필터 대신 대화로 검색한다.

**Acceptance Criteria:**

**Given** `web`의 AI 채팅 화면에서
**When** 자연어 질의를 입력하면
**Then** `/ai/search`를 호출해 자연어 답변 + 매물카드 목록을 렌더한다

**Given** 매물카드를
**When** 누르면
**Then** 해당 매물 상세로 이동한다
**And** 매물카드는 텍스트 필드만 표시한다(사진 없음)

### Story 4.8: AI 검증 — SM3·CM1·CM2 합격 판정

As a 시연자/평가자,
I want 데모 질의셋으로 AI 동작을 통과/실패로 판정하고 싶다,
So that 과제 핵심 목표가 검증됐음을 보인다.

**Acceptance Criteria:**

**Given** OI5 데모 질의셋을
**When** 실행하면
**Then** SQL 경로·문서 RAG 경로가 모두 적절한 매물카드를 반환한다(SM3)

**Given** 무관 질의를
**When** 실행하면
**Then** 전부 정중히 거절된다(CM1)

**Given** 안전장치를
**When** 점검하면
**Then** SELECT 전용·범위 제한을 벗어나는 쿼리가 0건 실행된다(CM2)

## Epic 5: 문의 채팅

구매자↔판매자가 매물에 대해 폴링 방식으로 대화한다.

### Story 5.1: chat 스키마 + RLS

As a 개발자,
I want 채팅방·메시지 테이블과 참여자 한정 RLS를 만들고 싶다,
So that 당사자만 대화를 읽고 쓴다.

**Acceptance Criteria:**

**Given** `0003_chat` 마이그레이션이 적용되면
**When** 스키마를 확인하면
**Then** `chat_rooms(listing_id, buyer_id, seller_id)`·`chat_messages(room_id, sender_id, body, created_at)`가 존재한다
**And** 참여자 한정 RLS가 **같은 `0003_chat` 마이그레이션에 동거**해 함께 적용된다

**Given** RLS가 적용되면
**When** 제3자가 채팅방/메시지에 접근하면
**Then** 차단된다(참여자만 허용)

### Story 5.2: 문의 채팅방 생성·진입 (FR19)

As a 구매자,
I want 매물에 문의를 보내 채팅방을 열고 싶다,
So that 판매자와 직접 대화한다.

**Acceptance Criteria:**

**Given** 매물 상세에서
**When** 문의하기를 누르면
**Then** 구매자·판매자 양쪽에 동일한 채팅방이 생성(또는 기존 방 재사용)된다

**Given** 채팅방 목록에서
**When** 방을 선택하면
**Then** 해당 대화로 진입한다

### Story 5.3: 폴링 메시지 송수신 (FR20, FR21)

As a 채팅 당사자,
I want 메시지를 주고받고 싶다,
So that 거래 조건을 협의한다.

**Acceptance Criteria:**

**Given** 채팅방에서
**When** 메시지를 보내면
**Then** `chat_messages`에 저장된다(영속)

**Given** 폴링(3~5초)이 동작할 때
**When** 상대가 메시지를 보내면
**Then** 내 화면에 갱신되어 나타난다(메시지 insert → 상대 폴링 1건 수신)

## Epic 6: 관리자

운영자가 회원·매물·거래내역·채팅을 조회/삭제한다. (web 전용)

### Story 6.1: admin 라우트 가드 + admin RLS

As a 개발자,
I want `/admin`을 admin만 통과시키고 관리자 RLS 정책을 적용하고 싶다,
So that 운영 기능이 관리자에게만 열린다.

**Acceptance Criteria:**

**Given** `(admin)` 라우트 가드와 `0005_admin_policies`(관리자 전권 교차 정책)가 적용되면
**When** 비관리자가 `/admin`에 접근하면
**Then** 1차 미들웨어 + 2차 RLS로 차단된다

**Given** 관리자 계정으로
**When** `/admin`에 접근하면
**Then** 관리자 화면이 열린다

### Story 6.2: 회원 관리 (FR22)

As a 관리자,
I want 회원을 조회하고 정지/삭제하고 싶다,
So that 이상 회원을 관리한다.

**Acceptance Criteria:**

**Given** 회원 관리 화면에서
**When** 목록을 열면
**Then** 전체 회원이 보인다

**Given** 한 회원을
**When** 정지/삭제하면
**Then** `profiles.status`가 바뀌거나 계정이 제거된다

### Story 6.3: 전체 매물 관리 (FR23)

As a 관리자,
I want 모든 매물을 조회하고 부적절 매물을 삭제하고 싶다,
So that 서비스 건전성을 유지한다.

**Acceptance Criteria:**

**Given** 매물 관리 화면에서
**When** 목록을 열면
**Then** 판매완료 포함 모든 매물이 보인다(관리자는 FR11 비노출 예외)

**Given** 한 매물을
**When** 삭제하면
**Then** 제거된다

### Story 6.4: 거래 내역 조회 (FR24)

As a 관리자,
I want 판매 완료된 매물 목록을 보고 싶다,
So that 거래 내역을 파악한다.

**Acceptance Criteria:**

**Given** 거래 내역 화면에서
**When** 열면
**Then** `status='sold'` 매물 목록이 보인다

### Story 6.5: 채팅 관리 (FR25)

As a 관리자,
I want 채팅방을 열람하고 삭제하고 싶다,
So that 문제 대화를 점검·정리한다.

**Acceptance Criteria:**

**Given** 채팅 관리 화면에서
**When** 채팅방을 열면
**Then** 대화 내용을 열람할 수 있다

**Given** 한 채팅방을
**When** 삭제하면
**Then** 방과 메시지가 제거된다

## Epic 7: Flutter 모바일 앱 (구매자 + 판매자)

구매자(AI검색→상세→문의채팅)와 판매자(등록→문의응대→구매완료) 핵심 여정을 모바일 앱에서 수행한다. 관리자 제외. web이 확정한 Supabase 스키마/RLS + `/ai/search` 계약 재사용. (7.1 골격은 Epic 1 직후 선행, 본 에픽 나머지는 Epic 4 직후 착수)

### Story 7.1: Flutter 골격 + 인증 연동 (Epic 1 직후 선행)

As a 개발자,
I want Flutter 앱 골격과 Supabase 인증을 연결하고 싶다,
So that 모바일 통합 리스크를 일찍 제거한다.

**Acceptance Criteria:**

**Given** `app/`가 `flutter create`로 생성되면
**When** 앱을 실행하면
**Then** 에뮬레이터/디바이스에서 기동된다

**Given** `supabase_flutter` + Riverpod가 설정되면
**When** 가입/로그인/로그아웃을 하면
**Then** web과 동일한 Supabase 계정으로 동작한다(FR1~3 재현)

### Story 7.2: 구매자 — 매물 탐색·상세·AI 검색 (재현 FR9·10·12~18)

As a 구매자(모바일),
I want 앱에서 매물을 검색·열람하고 AI로 찾고 싶다,
So that 폰으로 차를 찾는다.

**Acceptance Criteria:**

**Given** 앱에서
**When** 필터 검색/상세 조회를 하면
**Then** `on_sale` 매물만 보인다(FR9·10·11 재현, 사진 없음)

**Given** 앱 AI 채팅에서
**When** 자연어 질의를 보내면
**Then** `/ai/search`를 호출해 자연어 답변 + 매물카드를 받는다(FR12~18 재현)

### Story 7.3: 판매자 — 매물 등록 (재현 FR5)

As a 판매자(모바일),
I want 앱에서 매물을 등록하고 싶다,
So that 폰으로 차를 내놓는다.

**Acceptance Criteria:**

**Given** 판매자로 로그인한 앱에서
**When** 15필드 폼을 채워 제출하면
**Then** `listings` 행이 `on_sale`로 생성된다(사진 없음 — 업로드 화면 없음)

**Given** CHECK 위반 값으로
**When** 제출하면
**Then** 한국어 검증 오류로 거절된다

### Story 7.4: 판매자 — 본인 매물 관리·구매완료 (재현 FR6·8)

As a 판매자(모바일),
I want 앱에서 내 매물을 관리하고 구매완료 처리하고 싶다,
So that 이동 중에도 거래를 마무리한다.

**Acceptance Criteria:**

**Given** 앱에서
**When** 본인 매물을 수정/삭제하면
**Then** 본인 것만 허용된다(FR6 재현, RLS 공유)

**Given** 본인 매물을
**When** "구매 완료" 처리하면
**Then** `sold`로 전환된다(FR8 재현)

### Story 7.5: 구매자·판매자 문의 채팅 (재현 FR19~21)

As a 앱 사용자,
I want 앱에서 문의 채팅을 주고받고 싶다,
So that 모바일에서 거래 대화를 한다.

**Acceptance Criteria:**

**Given** 앱 매물 상세에서
**When** 문의하기를 누르면
**Then** 채팅방이 생성/재사용된다(FR19 재현)

**Given** 앱 채팅방에서
**When** 폴링(3~5초)으로 메시지를 주고받으면
**Then** 양측에 갱신되고 DB에 영속된다(FR20·21 재현)

### Story 7.6: SM1 통합 시연 검증

As a 시연자,
I want 핵심 시연 시나리오를 앱·웹에서 처음부터 끝까지 통과시키고 싶다,
So that 과제 제출 기준(SM1)을 충족함을 증명한다.

**Acceptance Criteria:**

**Given** 앱에서
**When** 구매자 여정(① AI검색→상세→문의채팅)을 실행하면
**Then** 끊김 없이 완주한다

**Given** 앱에서
**When** 판매자 여정(② 등록→문의응대→구매완료)을 실행하면
**Then** 끊김 없이 완주한다

**Given** web에서
**When** SM1 3종 시나리오(①구매자 ②판매자 ③관리자)를 리허설하면
**Then** 모두 end-to-end로 동작한다(SM1)
**And** SM2(필터검색)·SM3(AI 2경로)·SM4(대표 질의) 합격이 확인된다
