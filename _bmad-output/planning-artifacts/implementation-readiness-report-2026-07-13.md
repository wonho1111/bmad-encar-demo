---
stepsCompleted: ['step-01-document-discovery', 'step-02-prd-analysis', 'step-03-epic-coverage-validation', 'step-04-ux-alignment', 'step-05-epic-quality-review', 'step-06-final-assessment']
overallStatus: 'READY FOR IMPLEMENTATION'
findings: '0 critical · 0 major · 3 minor'
assessmentScope: 'increment-2 (2026-07: 이미지·웹소켓·RAG개선·UI개편)'
documentsUnderAssessment:
  prd: 'prds/prd-bmad-encar-demo-2026-07-11/prd.md + addendum.md'
  ux: 'ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md + EXPERIENCE.md'
  architecture: 'architecture-increment-2026-07-12.md'
  epics: 'epics-increment-2026-07-12.md'
supersededByIncrement:
  - 'architecture.md (2026-06-20, 증분1)'
  - 'epics.md (2026-06-20, 증분1)'
  - 'prds/prd-bmad-encar-demo-2026-06-17/ (증분1)'
  - 'implementation-readiness-report-2026-06-19.md (증분1 점검 결과)'
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-13
**Project:** bmad-encar-demo
**Assessor:** Winston (System Architect)
**Scope:** 증분 2 — 이미지·웹소켓·RAG개선·UI개편

---

## Step 1: Document Inventory

### 평가 대상 문서 (증분 2 — 현행)

| 유형 | 파일 | 상태 |
|---|---|---|
| PRD | `prds/prd-bmad-encar-demo-2026-07-11/prd.md` + `addendum.md` | status: final |
| UX | `ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md` + `EXPERIENCE.md` | status: final |
| Architecture | `architecture-increment-2026-07-12.md` | status: complete |
| Epics & Stories | `epics-increment-2026-07-12.md` | (검증 대상 — untracked 신규) |

### 증분1(구세대) — 참조/이력용, 평가 제외

- `architecture.md` (2026-06-20)
- `epics.md` (2026-06-20)
- `prds/prd-bmad-encar-demo-2026-06-17/`
- `implementation-readiness-report-2026-06-19.md` (증분1 점검 결과)

### 중복(Duplicate) 이슈

- **없음.** whole vs sharded 형태의 동일 문서 중복은 발견되지 않음. 구세대(6월)와 증분(7월) 문서는 서로 다른 세대이며, 이번 점검은 증분(7월) 세트만 평가.

### 누락(Missing) 문서

- **없음.** PRD·UX·Architecture·Epics 4종 모두 증분 세트로 존재.

---

## Step 2: PRD Analysis

> 증분2 PRD는 원본 FR1~25를 기준선으로 두고 **FR26부터 신규/개정만** 정의하는 델타 문서. 아래는 이번 증분이 다루는 FR/NFR 전량.

### Functional Requirements (증분 델타)

**F7 이미지**
- **FR26** 판매자는 매물에 사진 여러 장 등록(선택, 5:3 크롭, nullable — 기존 100건 보존, 매물당 최대 10장, 첫 장=대표)
- **FR27** 사진 없는 매물은 "사진 준비중" 플레이스홀더로 표시(목록·상세 안 깨짐)
- **FR28** (FR10 개정) 상세=대표사진+갤러리, 목록=대표 1장, AI 검색 응답 카드에도 대표사진 반영
- **FR29** 카드에 "N장" 사진 개수 배지(사진 있는 매물 한함)

**F8 카드·신뢰속성·옵션**
- **FR30** 신뢰속성(무사고·1인소유·비흡연)을 옵션과 분리 관리/표시. 3속성 모두 "판매자 신고" 티어로 통일 + "판매자 제공 정보" 면책 라벨 필수(가짜 검증 UI 금지). 신뢰속성=카드 상단, 옵션=하단
- **FR31** 희소 옵션 우선 노출(보편 옵션 저순위, 카드 상위 3~4개, 상세 전량). 기술부채 #11 옵션 저장구조 정비 권장
- **FR32** 카드 정보 위계(차량명→연식→주행→연료→지역), 가격 대형 볼드, 찜 버튼 사진 밖. 비교(compare) 기능 제외
- **FR55** 찜(좋아요) — listing_id 저장, 카드 토글, "찜한 매물" 목록 도달
- **FR56** 판매자 정보 경량 노출(닉네임+가입시점+다른 매물 N건). 평판점수·응답률·인증배지 제외

**F9 랜딩페이지**
- **FR33** 랜딩 첫 화면 = AI 자연어 검색 히어로(검색 입력+예시 질의 칩)
- **FR34** 히어로 아래 매물 그리드 = 인기/최신 2단. 인기=view_count 정렬(SECURITY DEFINER RPC +1), 최근=created_at. 전체 대체 아닌 발췌+전체보기 진입
- **FR35** 차종 빠른 진입(경차·SUV·전기 등 카테고리 칩/그리드)

**F10 UI 개편·반응형**
- **FR36** 단일 코드 반응형(카드 그리드→모바일 캐러셀/1열, 필터 사이드바→바텀시트, 상단 내비→햄버거)
- **FR37** 일관 디자인 시스템 — 페트롤+앰버 팔레트를 CSS 토큰(Tailwind v4 @theme) 중앙 관리
- **FR38** 내비·IA 도달성(매물탐색·등록·AI검색·내채팅·내매물·찜). AI 검색 1급 노출, 문의는 매물 상세에서 개시(전역 '문의' 없음). 구조·배치는 bmad-ux 소관

**F11 Flutter**
- **FR39** Flutter 앱을 웹과 동일 디자인 언어로 개편(이미지·카드 반영). 구현은 별도, 계약은 conventions.md 공유

**F12 실시간 채팅**
- **FR40** (FR20 개정) 폴링→실시간(Supabase Realtime 구독), 즉시 반영
- **FR41** 멱등키(클라 uuid) 도입, 재전송 중복 영속 방지
- **FR42** 재연결/오프라인 비차단 배너 + 재연결 시 갭 보정 select(유실 방지)
- **FR57** 안 읽은 문의 알림 배지 + 방 목록 최신순 정렬

**F13 RAG 고도화**
- **FR43** 라우팅 4갈래(무관/법적 거절·광범위 되묻기·구조형 SQL·조합형 하이브리드)
- **FR44** 가이드 문서 RAG 실제 활용(content 반영, 참조 판단 분기)
- **FR45** 하이브리드 검색(SQL 필터+임베딩 유사도 단일 쿼리). **★ 필수 보안 AC**: HYBRID SQL도 sql_guard.validate_select_sql() 통과 + status='on_sale' 강제(CM-B)
- **FR46** 조건 좁혀 되묻기(제안형, tappable 칩 응답 가능)
- **FR47** 부드러운 거절(법적/무관 질의, 고정 템플릿 유지)
- **FR48** 가이드 청킹·임베딩(조건부 — ≥20문서/≥800토큰 시에만)
- **FR49** 유사도 거리 컷오프(기술부채 #16)
- **FR50** AI 검색 DB에 커넥션 풀+타임아웃+async 논블로킹(기술부채 #5, RAG 선행)
- **FR51** LangSmith 무료 트레이싱(env 2개, 코드변경 0)

**F14 역할 통합**
- **FR52** (FR1 개정) 가입 시 구매자/판매자 역할선택 제거
- **FR53** (FR3·FR6 개정) 접근 제어를 소유권 기준으로 통일
- **FR54** admin은 별개 유지(통합은 구매자·판매자 두 역할만)
- **FR58** 비로그인 접근 정책 — 랜딩=단일 공개 홈, 비로그인도 열람·AI검색 가능, 로그인 게이트는 행동(문의·등록·찜)에만

**관리자 UI (addendum FR 정식화, 2026-07-13)**
- **FR59** 관리자 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리) 신규 디자인 시스템 리스킨 통일. UI-only(신규 기능·운영 배관 없음)
- **FR60** 관리자 웹 단일 코드 반응형(D5 무결성 필수 준수)
- **FR61** 회원관리 역할통합 반영(구매자/판매자 필터 정리, account_type 축)

**Total FRs (증분): 36개 (FR26~FR61)**

### Non-Functional Requirements (증분 델타)

- **NFR1 (개정)** 문의 채팅 실시간 갱신(웹소켓/구독). AI 응답 수 초 내 유지
- **NFR3 (개정)** 단일 코드 반응형(데스크톱·모바일 웹), Flutter는 동일 디자인 언어 별도 구현
- **NFR7 (신규)** 이미지 저비용 저장·서빙(Supabase Storage, 썸네일·lazy-load)
- **NFR8 (신규)** AI 검색 경로 커넥션 풀·타임아웃(FR50)
- **유지** NFR2(RLS·SELECT 전용·service_role 금지), NFR4(배포), NFR5(AI 이력 미저장), NFR6(저비용)

**Total NFRs (증분): 4개 개정/신규 + 4개 유지**

### Additional Requirements / Constraints

- **성공 지표** SM-A~G(이미지·랜딩·신뢰속성·Flutter·실시간·RAG유지·RAG신규동작)
- **카운터 지표** CM-A(100건 하위호환), CM-B(FR11·채팅무결성·AI안전장치 유지), CM-C(신뢰속성 오도 금지)
- **측정 게이트** G1(CLARIFY 과다발동 방지), G2(RAG 회귀 게이트), G3(이미지 하위호환)
- **마이그레이션 순서(additive)** 0011~0018(이미지·신뢰속성·role완화·view_count RPC·wishlists·멱등키·realtime broadcast·chat_room_reads)
- **배포 순서** db→api(Cloud Run)→web(Vercel), nullable 하위호환
- **F14 분리 관리** 인증·RLS 건드려 위험도 높음 → 별도 워크스트림

### PRD Completeness Assessment (초기)

- **강점**: FR이 명확히 번호화(FR26~61)·개정 표시 일관, 각 FR에 근거(리서치·선례)·ASSUMPTION 명시, 카운터 지표·측정 게이트로 회귀 방어, addendum이 기술 how·보안 AC·마이그 순서까지 락스텝 서술. 아키텍처 완료 후 스코프 조정(관리자 UI·찜 인기신호 보류·문서 차량상태 보류)을 정직하게 역반영.
- **주의 지점(다음 스텝에서 에픽 커버리지 검증 대상)**:
  1. FR45 하이브리드의 **보안 필수 AC**(sql_guard 통과+on_sale 강제)가 에픽/스토리에 블로커 AC로 살아있는지
  2. FR59~61(관리자 UI)은 PRD 본문(final)이 아닌 addendum에서 승격 → 에픽 추적성 확보 여부
  3. 보류 결정(찜 인기신호·문서 차량상태)이 에픽에서 명확히 제외됐는지

---

## Step 3: Epic Coverage Validation

> 에픽 문서(`epics-increment-2026-07-12.md`)는 명시적 **FR Coverage Map**(179~219행) + **FR 소유권 매트릭스**(경계 FR) + **지표 추적 매트릭스**(SM/CM/G)를 보유. 아래는 PRD FR26~61 전량 대조 결과.

### Coverage Matrix

| FR | 요구 요약 | 에픽 매핑 | 상태 |
|---|---|---|---|
| FR26 | 사진 다중 등록 | Epic 9 | ✓ |
| FR27 | "사진 준비중" 플레이스홀더 | Epic 9 | ✓ |
| FR28 | 상세 갤러리·AI카드 대표사진 | Epic 9 | ✓ |
| FR29 | "N장" 배지 | Epic 9 | ✓ |
| FR30 | 신뢰속성 분리·면책 라벨 | Epic 10 | ✓ |
| FR31 | 희소 옵션 우선 | Epic 10 | ✓ |
| FR32 | 카드 정보 위계·가격·찜 위치 | Epic 9(정책소유)+Epic 10(소비) | ✓ |
| FR33 | AI 히어로 랜딩 | Epic 11 | ✓ |
| FR34 | 인기/최신 그리드 | Epic 11 | ✓ |
| FR35 | 차종 빠른 진입 | Epic 11 | ✓ |
| FR36 | 단일 코드 반응형 | Epic 8(정책)+전 UI 에픽 DoD+Epic 11 감사 | ✓ |
| FR37 | @theme 디자인 시스템 | Epic 8 | ✓ |
| FR38 | 내비·IA 도달성 | Epic 11 | ✓ |
| FR39 | Flutter 개편 | Epic 16 | ✓ |
| FR40 | 실시간 채팅 | Epic 12 | ✓ |
| FR41 | 멱등키 | Epic 12 | ✓ |
| FR42 | 재연결 배너·갭보정 | Epic 12 | ✓ |
| FR43 | 4분기 라우팅 | Epic 13 | ✓ |
| FR44 | 가이드 content 활용 | Epic 13 | ✓ |
| FR45 | 하이브리드 검색+AC-SEC-1 | Epic 13 | ✓ |
| FR46 | 되묻기 CLARIFY | Epic 13 | ✓ |
| FR47 | 부드러운 거절 | Epic 13 | ✓ |
| FR48 | 청킹(조건부) | Epic 13 | ✓ |
| FR49 | 거리 컷오프 | Epic 13 | ✓ |
| FR50 | 커넥션 풀·AC-DB-1 | Epic 8(선행)+Epic 13(하이브리드) | ✓ |
| FR51 | LangSmith 트레이싱 | Epic 13 | ✓ |
| FR52 | 역할선택 제거 | Epic 14 | ✓ |
| FR53 | 소유권 접근제어 | Epic 14 | ✓ |
| FR54 | admin 존치 | Epic 14 | ✓ |
| FR55 | 찜 | Epic 10 | ✓ |
| FR56 | 판매자 정보 | Epic 10 | ✓ |
| FR57 | 안읽음 배지·정렬 | Epic 12 | ✓ |
| FR58 | 비로그인 접근 정책 | Epic 8(정책)+Epic 9~14 준수 | ✓ |
| FR59 | 관리자 6화면 디자인 통일 | Epic 15 | ✓ |
| FR60 | 관리자 반응형 | Epic 15 | ✓ |
| FR61 | 회원관리 역할통합 | Epic 15 | ✓ |
| (개정) FR1/3/6 | 역할통합 | Epic 14 | ✓ |
| (개정) FR5 | 이미지 | Epic 9 | ✓ |
| (개정) FR10/17 | 갤러리·AI카드 | Epic 9 | ✓ |
| (개정) FR15 | RAG | Epic 13 | ✓ |
| (개정) FR20/21 | 실시간 | Epic 12 | ✓ |

### Missing Requirements

- **없음.** PRD 증분 FR26~61(36개) 전량이 Epic 8~16에 매핑됨. 원본 개정분(FR1/3/5/6/10/15/17/20/21)도 전량 매핑.

### Epics에는 있으나 PRD 본문에 없는 항목 (역추적)

- **FR59~61(관리자 UI 통일)** — PRD **본문**(status:final, FR26~58)엔 없고 **addendum FR 정식화**(2026-07-13)에서 승격. 에픽은 이를 Epic 15로 소유하며 근거(addendum·Mary 추적성 요구)를 명시 → **추적성 확보됨**(고아 아님).
- **보류(deferred) 명시 확인** — 찜 기반 복합 인기신호·문서 기반 차량상태는 에픽 Non-goals/deferred-work로 명확히 제외. 에픽에 유입 안 됨. ✓

### Coverage Statistics

- **Total PRD FRs (증분):** 36개 (FR26~FR61) + 원본 개정 9개
- **FRs covered in epics:** 36 + 9 (전량)
- **Coverage: 100%** — 누락 0, 고아 0

### 특기 사항 (품질 신호 — 이후 스텝에서 심화 검증)

- 에픽 문서가 단순 매핑을 넘어 **① FR 소유권 매트릭스**(경계 FR을 "정책소유 1 + 소비 N"으로 분리해 "아무도 안 하는 틈" 차단), **② 지표 추적 매트릭스**(SM/CM/G를 검증 스토리로 착지), **③ 마이그레이션 원장 정본**(논리 라벨↔실제 파일번호 이중번호 혼동 방지), **④ 선결 기술 AC**(AC-DB-1·AC-SEC-1/2·AC-CHAT-1~3·AC-CONTRACT-1·AC-DEPLOY-1·AC-F14-1)까지 포함 — 추적성 관점에서 매우 성숙.
- **FR45 보안 필수 AC**(sql_guard 통과+on_sale 강제)가 AC-SEC-1로 살아있고 Epic 13 첫 스토리 blocker AC로 편입됨. ✓
- **위험 기초(Epic 8)** 선격상 — 접근제어·디자인·계약·배포를 별도 기반 에픽으로 분리해 뒤 에픽이 임시코드 위에 쌓이지 않게 함.

---

## Step 4: UX Alignment Assessment

### UX Document Status

**Found.** `DESIGN.md`(시각 스파인, status:final) + `EXPERIENCE.md`(경험 스파인, status:final) + 목업 8종 + 관리자 목업(`admin-mockups-2.html` 별도 폴더). 사용자 대면 웹·Flutter·관리자 전 서피스 커버.

### UX ↔ PRD Alignment (정렬 양호)

- **직접 추적**: 두 UX 문서 모두 frontmatter에서 PRD를 소스로 인용, FR별로 거동을 매핑(신뢰 면책=FR30/CM-C, 랜딩 히어로=FR33~35, 반응형=FR36, 실시간 재연결=FR42, AI 4갈래=FR43~47, 안읽음=FR57, 비로그인=FR58, 역할 통합=OI-1).
- **PRD가 UX에 위임한 결정 소화**: FR38이 "내비 구조·메뉴 개수·마이페이지 여부는 bmad-ux 소관"으로 열어둔 것을 UX가 확정(웹 상단 내비 D8, 앱 하단 4탭 D12, 별도 마이페이지 미신설=프로필 드롭다운). ✓
- **정직성 계약 일치**: FR30 "가짜 검증 UI 금지"를 UX가 Voice 표 면책 문구 + Anti-pattern("검증 UI 위장 금지")으로 구조화. CM-C를 뱃지 컴포넌트 DoD로 강제. ✓

### UX ↔ Architecture Alignment (아키텍처가 UX 요구를 뒷받침 + 일부 정정)

- **아키텍처가 UX를 지지**: D5 반응형 무결성(규칙13)을 아키텍처 Frontend·Enforcement에 명문화, 이미지 3상태(없음/처리중/실패)를 UX-DR7↔아키텍처 Frontend 일치, 5:3 크롭=클라 렌더(I14, `object-fit:cover`/`BoxFit.cover`)로 UX 갤러리 뒷받침, Realtime 재연결 갭보정(UX ④ 플로우 ↔ AC-CHAT-2).
- **아키텍처가 UX 초기 서술을 정정(최종 계약이 우선, 무모순)**:
  1. **이미지 변형세트** — 초기 cross-cutting/일부 UX 뉘앙스는 "변형세트 {thumb/card/full} wire"였으나 **CR3에서 wire=단일 `image_url`, 변형은 클라 렌더 파생**으로 정정. UX 갤러리/썸네일은 렌더 파생이라 충돌 없음. ✓
  2. **AI 응답 계약 필드** — UX는 4갈래 "거동"을 서술, 아키텍처가 정확한 계약(`route`·`narrowed_by`·`clarify`)을 정의(CR4/CR5). 에픽이 흡수. ✓
  3. **상세 섹션 순서** — UX 스파인=신뢰→차량→옵션→판매자(D9/UX-DR24). `mockups/detail-1.html`은 구버전 순서 → UX·아키텍처(MINOR) 모두 "목업 맹종 금지, 스파인이 정답" 명시. ✓

### Warnings (경미 — 블로커 아님)

- **⚠️ (경미) UX frontmatter 범위 표기 지연**: DESIGN·EXPERIENCE의 `description`이 **"FR26~58"**로 표기돼 있으나 실제 PRD는 **FR26~61**(FR59~61 관리자 UI는 addendum 후속 승격). 단, **실질 커버는 됨** — 관리자 6화면은 `UX-DR25` + 별도 `admin-mockups-2.html`로 다뤄지고, 찜(FR55)·판매자정보(FR56)·안읽음(FR57)·비로그인(FR58)도 UX 본문에 전부 반영. **메타데이터 라벨만 옛 스냅샷**이며 콘텐츠 갭 아님. (원하면 description 문자열만 "FR26~61"로 갱신 권장 — 선택)
- **아키텍처·에픽이 UX 목업보다 최신**: `detail-1.html`·`landing-1.html` 구 라벨 등 목업 일부가 스파인보다 옛 버전 → 세 문서 모두 "스파인/정정이 정답" 단방향 포인터를 박아둠. dev는 목업이 아닌 스파인+아키텍처 정정을 따르면 됨. (관리 잘 됨)

### 종합

UX는 PRD·아키텍처와 **높은 수준으로 정렬**돼 있고, 불일치 지점마다 "어느 문서가 정답인가"의 단방향 포인터가 명시돼 있어 dev가 헤맬 여지가 작다. 관리자 UX 범위의 문서 메타 라벨 지연 1건이 유일한 경미 경고이며 구현 블로커가 아니다.

---

## Step 5: Epic Quality Review

> `create-epics-and-stories` 표준(사용자 가치·에픽 독립성·forward dependency 금지·스토리 사이징·AC 품질·DB 생성 타이밍)으로 Epic 8~16(46 스토리)를 엄격 검토. 이 문서는 이미 **독립 2인 클린컨텍스트 검증(frontmatter: 0 blocker/5 minor applied) + party-mode 4인(Winston·Amelia·Sally·Mary)** 검증을 거친 산출물.

### A. 사용자 가치 focus

- **Epic 9~16**: 전부 사용자 가치 중심(이미지·신뢰속성/찜·랜딩·실시간채팅·RAG·역할통합·관리자UI·Flutter). 에픽 제목·목표가 "사용자가 무엇을 할 수 있는가"로 서술됨. ✓
- **Epic 8(증분 기반 게이트)**: 표준 관점에서 **technical-enabler 에픽**(디자인토큰·계약셸·커넥션풀·배포게이트)으로, 통상 red flag. **그러나** 브라운필드 기반 에픽으로 **명시적 정당화 + 사용자 승인**(별도 에픽 격상), 스토리를 As-a 형식으로 서술하려 노력(8.1 사용자·8.2 사용자·8.5 비로그인 방문자). 8.3(계약)·8.4(커넥션풀)·8.6(배포)은 개발자 스토리. → **의도적·정당화된 예외**(아래 🟡#1).

### B. 에픽 독립성 / Forward Dependency (핵심 — 위반 0)

- 에픽 순서 8→9→…→16, **각 에픽이 앞 에픽만 의존**(backward). 순환·전방 의존 없음.
- **Forward reference를 "자리만 시드" 패턴으로 명시 회피** — 매우 성숙:
  - 9.4 찜 버튼 = "위치·시각만, 동작은 Epic 10"
  - 11.2 내비 채팅🔔 = "아이콘 자리만, 안읽음 데이터·집계는 Epic 12(12.5) 소유 … 후행 에픽 미완성에 의존 안 함"
  - 9.5 상세 골격 = "신뢰·판매자 빈 슬롯을 세우고 완결, Epic 10이 채움"
  - → 앞 에픽이 **완결**되고 뒤 에픽이 **채우는** 올바른 방향. Forward dependency 위반 **없음**. ✓

### C. 스토리 사이징 / DB 생성 타이밍

- **DB = 필요한 스토리가 필요할 때 생성**(선행 일괄 생성 안티패턴 회피): 9.1 listing_images · 10.1 신뢰속성 · 10.5 wishlists · 11.1 view_count · 12.1 멱등키 · 12.2 realtime · 12.5 chat_room_reads · 14.1 role. Epic 8은 테이블이 아니라 **계약 셸**만 선점. ✓
- 스토리 크기 적절, 각 스토리 독립 완결 가능. ✓

### D. Acceptance Criteria 품질

- **전 46 스토리가 Given/When/Then BDD 형식**, testable·구체적. Vague criteria("user can login" 류) 없음.
- **에러·엣지 광범위 커버**: 사진 없음/sold/삭제 404·비로그인 게이트·재연결 실패 pending·미입력 NULL 제3상태·업로드 실패 재시도·대표사진 삭제 시 자동 승격·멱등 중복·롤 누수 red→green 등. AC 품질 **매우 높음**. ✓

### E. 브라운필드 / Starter

- 기존 시스템 통합점(기존 RLS·Epic 5 채팅 로직 재사용·기술부채 #11 정비)·하위호환 스토리(9.7=G3/CM-A)·마이그레이션 스토리 다수. 아키텍처가 "브라운필드=스타터 없음, 초기화 스토리 불필요" 명시 → Epic 8이 초기화 대신 기반 게이트. **적절**. ✓

### 🔴 Critical Violations

- **없음.**

### 🟠 Major Issues

- **없음.**

### 🟡 Minor Concerns

1. **Epic 8 = technical-enabler 에픽** — 표준 red flag이나 브라운필드 기반 에픽으로 정당화·사용자 승인·스토리 사용자 서술 노력. 8.3/8.4/8.6은 개발자 스토리. **표준을 엄격 적용하면 flag 대상이지만 근거 타당** → 수용 권고(제거·병합 강제 불필요). 참고로만 기록.
2. **이중 마이그레이션 번호 체계** — 아키텍처 "논리 라벨 0011~0018" ↔ 에픽 "마이그레이션 원장 실제 파일번호"(예 wishlists=원장 0013/논리 0015, role=원장 0018/논리 0013)가 공존. 문서가 "원장이 정본"으로 정리 + 각 스토리에 병기(`(원장 정본 / 아키텍처 논리라벨 XXXX)`)로 완화했으나, dev가 두 체계를 혼동할 **잔여 인지부하** 존재. → 8.6 CI 체크(번호순·gap·self-contained 검증)가 안전망. 잔여만 Minor.
3. **Story 13.6 거리 컷오프 임계값 미확정** — "Phase B 질의셋으로 튜닝해 확정(초기 후보 0.3)". 구현 중 실측 필요(계획됨, blocker 아님).

### Best Practices Compliance Checklist

- [x] Epic delivers user value (Epic 8은 정당화된 예외)
- [x] Epic can function independently (backward-only 의존)
- [x] Stories appropriately sized
- [x] **No forward dependencies** (자리만 시드 패턴으로 명시 회피)
- [x] Database tables created when needed (선행 일괄 생성 없음)
- [x] Clear acceptance criteria (전 스토리 G/W/T, 에러 포함)
- [x] Traceability to FRs maintained (FR 소유권 매트릭스·지표 추적 매트릭스)

### 종합

에픽 문서는 **매우 성숙**하다. 표준의 핵심 관문(forward dependency 금지·DB 적시 생성·AC 품질·추적성)을 모두 통과하며, 오히려 "자리만 시드"·"FR 소유권 매트릭스"·"지표 추적 매트릭스"·"마이그레이션 원장 정본"으로 표준을 초과 달성. Critical·Major 위반 0, Minor 3(전부 수용 가능·계획 반영됨).

---

## Summary and Recommendations

### Overall Readiness Status

## ✅ READY FOR IMPLEMENTATION

증분 2(이미지·웹소켓·RAG·UI개편·역할통합)의 계획 산출물 4종(PRD·UX·Architecture·Epics)은 **구현 착수 준비 완료** 상태다. 차단성(blocker) 결함은 없다.

### 근거 요약

| 검증 렌즈 | 결과 |
|---|---|
| 문서 인벤토리 | 4종 완비, 중복·누락 0 |
| FR 커버리지 | **100%** (FR26~61 + 원본 개정 9건 전량 매핑, 고아 0) |
| UX 정렬 | 양호 — PRD·아키텍처와 높은 정렬, 불일치 지점마다 단방향 포인터 |
| 에픽 품질 | Critical 0 · Major 0 · Minor 3 |
| 하드 제약 | service_role 금지·임베딩768·RLS·FR11·채팅무결성·D5 위반 **0** (아키텍처 독립 3인 검증 통과) |

### Critical Issues Requiring Immediate Action

- **없음.** 착수를 막는 이슈는 발견되지 않았다.

### 착수 전 참고할 경미 사항 (블로커 아님 — 선택적 정비)

1. ~~**[선택] UX 문서 메타 라벨 갱신**~~ — ✅ **정비 완료(2026-07-13)**. DESIGN·EXPERIENCE frontmatter `description`을 "FR26~58" → "FR26~61(관리자 UI 통일 포함)"로 정정. `status:final`·`updated:2026-07-12`는 유지(실질 스펙 불변, 메타 라벨만 정정).
2. **[인지] 이중 마이그레이션 번호** — dev는 **에픽의 "마이그레이션 원장" 표를 정본**으로 따를 것(아키텍처 0011~0018은 논리 라벨). 8.6 CI 체크(번호순·gap·self-contained)가 안전망 — **첫 착수 시 이 CI 체크부터 세우면** 이중번호 혼동을 원천 차단.
3. **[구현 중]** 거리 컷오프 임계값(13.6)은 Phase B 질의셋 실측으로 확정 — 계획됨.

### Recommended Next Steps

1. **관리자 UI 정식 역반영 확인** — addendum이 FR59~61을 정식화했고 에픽(Epic 15)이 소유하므로 추적성은 확보됨. PRD 본문(status:final)은 불변 유지가 맞다. 별도 조치 불필요(이미 정합).
2. **`bmad-create-story`로 첫 스토리 착지** — 구현 순서 정본은 **① Story 8.4 AC-DB-1(커넥션 풀 롤 격리, RAG 선행) → ② 8.1~8.3/8.5/8.6 기반 게이트 → ③ Epic 9 이미지 …**. 첫 개발 진입점 = AC-DB-1(기존 Epic 4 AI API 커넥션 레이어 수술, RAG와 독립적으로 조기 디리스크·red→green 가능).
3. **sprint-planning 갱신** — Epic 8~16을 sprint-status에 반영(원본 Epic 1~7은 done 기준선).
4. **계약 우선 원칙 준수** — 확정 계약은 **`docs/conventions.md`를 먼저 고치고 코드**(규칙1). 특히 ListingCard §4(8.3에서 1회 선점)·신뢰속성·Realtime 토픽 계약.
5. **F14는 별도 워크스트림** — 인증·RLS를 건드리므로 이미지/UI 커밋과 분리 관리(Epic 14).

### Final Note

이번 평가는 **6단계 전 구간을 완주**했고, 발견 이슈는 **Minor 3건(전부 수용 가능·계획 반영)**뿐이며 Critical·Major는 0이다. 이는 이 산출물들이 이미 **독립 클린컨텍스트 검증(아키텍처 3인·에픽 2인) + party-mode 4인 검증**을 거쳐 실질 결함을 사전 적발·정정했기 때문이다(자기채점 편향 회피). **구현에 착수해도 좋다.** 위 경미 사항은 착수를 막지 않으며, 특히 #2(마이그레이션 원장 정본 + 8.6 CI 체크 우선 구축)만 첫 스프린트에서 챙기면 남은 인지부하도 해소된다.

---

_Assessment completed by Winston (System Architect) · 2026-07-13 · 6/6 steps complete_
