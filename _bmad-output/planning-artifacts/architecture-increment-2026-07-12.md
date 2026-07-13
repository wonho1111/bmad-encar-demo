---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-07-13'
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-07-11/prd.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-07-11/addendum.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-07-11/reconcile-inputs.md
  - _bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md
  - _bmad-output/planning-artifacts/increment-open-decisions.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/project-context.md
  - docs/conventions.md
  - docs/db-schema-guide.md
  - _bmad-output/planning-artifacts/research-current-rag-implementation.md
  - _bmad-output/planning-artifacts/research-langx-rag-patterns.md
  - _bmad-output/planning-artifacts/research-supabase-viewcount-rpc.md
  - _bmad-output/planning-artifacts/research-data-options.md
  - _bmad-output/planning-artifacts/research-data-trust-attributes.md
  - _bmad-output/planning-artifacts/research-account-nav-model.md
workflowType: 'architecture'
architectureScope: 'increment'
baselineArchitecture: '_bmad-output/planning-artifacts/architecture.md'
project_name: 'bmad-encar-demo'
user_name: 'Dnjsg'
date: '2026-07-12'
---

# Architecture Decision Document — 증분 (Increment)

_이 문서는 완성된 원본 `architecture.md`(2026-06-18) 위에 이번 증분(이미지·실시간 채팅·RAG 고도화·UI 개편·역할 통합)의 기술 결정만 얹는다. 원본은 참조 기준선(baseline)으로 보존한다. 섹션은 단계별 협업으로 추가된다._

## 확정된 설계 제약 (착수 전 사용자 확정)

- **★ 지배 원칙: 바퀴 재발명 금지 (Reuse-First)** — 이 증분의 모든 결정에 우선 적용한다. 신규 시스템이 아니라 기존 위 확장이므로, **기존 인프라·패턴·검증된 라이브러리를 재사용/확장**하고 커스텀 신규 구축을 피한다. 구체: 이미지=Supabase Storage · 실시간=Supabase Realtime(직접 웹소켓 서버 금지) · 보안=기존 `sql_guard`/`ai_readonly`/RLS/무결성 트리거 확장 · RAG=기존 LangGraph StateGraph·corpus 로더·임베딩 파이프라인 위에 노드만 추가(interrupt()/체크포인터 등 무거운 신규 인프라 미도입) · 옵션·신뢰속성=정규화 테이블 신설 대신 기존 `text[]`·컬럼 승격. "시니어 엔지니어가 과설계라 할까?"를 매 결정마다 자문(A2). (사용자 확정, 2026-07-12)
- **RAG 가이드 지식 반영 방식 = (b) 질의 시점 확장** — 가이드 문서 본문에서 상식 기준(예: "패밀리카 → SUV/RV/5인승+")을 읽어 **검색 조건/가중치로 변환**해, 매물 설명에 해당 표현이 없어도 적합 매물이 검색 결과에 뜨게 한다. **단, 답변 텍스트는 기존 결정론적 방식 유지** — 가이드 본문으로 설명 문장을 LLM 생성하지 않는다(방식 (c) 미채택: 비결정론·추가 LLM 호출 회피, A2 단순함 우선). `answer_node`의 "LLM 자유 재작성 금지" 설계와 FR47 고정 거절 문구 유지.
- **관리자 웹 = UI 통일 스코프 추가 (UI-only, 사용자 확정 2026-07-12)** — 원래 PRD는 관리자를 "최소 변경/전면개편 범위 밖"으로 축소. 사용자 결정으로 **운영자용 관리자 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)을 신규 디자인 시스템으로 통일 + PC/모바일 브라우저 반응형** 적용한다. **신규 기능·개발/운영 배관(스토리지 정리·미처리 큐·신고/차단)은 없음**(다음 증분). 목업=`ux-designs/admin-web-increment-2026-07-12/admin-mockups-2.html`. **D5 반응형 무결성(project-context 규칙13) 필수 준수** — 필터 버튼·라벨 줄바꿈 어긋남 금지. **PRD/epics 정식 역반영은 후속 `bmad-prd` 세션**(status:final PRD를 중간에 임의 편집하지 않음).

---

## Project Context Analysis (증분)

_원본 architecture.md(baseline) 위 증분. 신규 FR26~58 + 원본 FR 개정(FR1/3/5/6/10/15/17/20/21). Step 2 party-mode 검토(Amelia/John/Sally/Mary) 반영본._

### Requirements Overview

**Functional Requirements (신규 FR26~58, 8개 기능군 — 아키텍처 관점):**

- **F7 이미지(FR26~29)** — 원본의 "사진 제외" 결정을 뒤집는다. `listings`에 nullable 이미지 도입(기존 100건 보존), Supabase Storage 업로드(anon+Storage RLS, service_role 금지), `ListingCard` 계약에 대표사진 필드 추가(목록·상세 갤러리·AI 카드 FR17/28 공통). 미결=OI-3.
- **F8 카드·신뢰속성·옵션·찜·판매자(FR30~32,55,56)** — 신뢰속성(무사고/1인소유/비흡연)을 옵션과 **별개 컬럼**으로 분리(전부 판매자 자기신고 티어+면책 라벨). 옵션은 `text[]` 유지 + 앱레이어 priority 상수(정규화 테이블은 과설계). 찜=신규 테이블+RLS. 판매자 정보=집계 쿼리.
- **F9 랜딩(FR33~35)** — AI 검색 히어로 + 인기/최신 그리드. "인기"=`view_count` 정렬 → `increment_listing_view()` SECURITY DEFINER RPC(anon 실행, service_role 금지). OI-5 확정.
- **F10 반응형·디자인시스템(FR36~38)** — 단일코드 반응형(그리드→캐러셀, 사이드바→바텀시트, 내비→햄버거), Tailwind v4 @theme 토큰. 인프라 변경 없음(프론트+라우팅 IA만).
- **F11 Flutter(FR39)** — 웹 셸 재사용 불가, 별도 위젯 구현. 디자인 언어·계약만 docs/conventions.md로 공유(계약 drift 관리 필요).
- **F12 실시간 채팅(FR40~42,57)** — 폴링→웹소켓/구독. 멱등키(client_message_id) 중복방지, 재연결 시 "마지막 수신 이후" 1회 보정 select(구독만으론 replay 안 됨), 안읽음 카운트 배지. 기존 chat_messages/RLS/무결성 트리거(0003c)·2000자 제약(0010) 보존. 미결=OI-4.
- **F13 RAG 고도화(FR43~51)** — 라우터 3분기→4분기(REJECT/CLARIFY/SQL/HYBRID, `RouterDecision` Literal·`_fallback_route`·`_route_decision` 3곳 락스텝). 하이브리드=단일쿼리 WHERE+ORDER BY embedding<=>(★신규 SQL도 sql_guard 통과 + status='on_sale' 강제=보안 블로커, AC-SEC-1). 되묻기=무상태(interrupt() 미사용, answer 반환+멀티턴 이어붙이기). 가이드 content=(b)질의확장(검색 반영, 답변은 결정론 유지) + 거리 컷오프. 커넥션풀(FR50, 선행). LangSmith 무료 트레이싱(env 2개).
- **F14 역할통합(FR52~54,58)** — 별도 워크스트림. profiles.role 존치(is_admin 의존)+CHECK 완화, 소유권 기반 접근제어로 통일, 비로그인 열람·AI검색 허용(게이트는 행동에만).

**Non-Functional Requirements:**
- NFR1(개정): 채팅 실시간(폴링 아님). AI 응답 수 초 유지.
- NFR2(불변): RLS·SELECT전용·service_role 키 금지 — 이미지 업로드·view_count·realtime 전부 준수.
- NFR3(개정): 단일코드 반응형 웹(m-dot 아님). Flutter는 동일 디자인 언어 별도 구현.
- NFR6(유지): 무료/저가 티어.
- NFR7(신규): 이미지 저비용 스토리지·서빙(썸네일/lazy-load), 목록카드 대표 1장.
- NFR8(신규): AI 검색 경로 커넥션 풀+타임아웃+async 논블로킹.

**Scale & Complexity:**
- Primary domain: 풀스택 증분(web·app·api·db 4파트 전부 touch).
- Complexity level: 중(medium) — 신규 아키텍처가 아니라 기존 위 확장. 난도 상승 지점=하이브리드 검색의 보안 접점, 실시간 transport, 이미지 스토리지×FR11 상호작용.
- Estimated architectural components affected: 8개 기능군 / 신규·개정 마이그레이션 4~6개(0011~).

### Technical Constraints & Dependencies

- **service_role 금지(규칙6, 절대)**: 이미지 업로드·view_count·realtime 전부 anon/authenticated key + RLS/RPC로만. 우회 금지.
- **임베딩 768 고정**: 하이브리드가 벡터 경로를 확장해도 gemini-embedding-001(768) ↔ pgvector vector(768) 불변.
- **하위호환·additive 마이그레이션**: 기존 100건 nullable 보존, 임베딩 보존, non-null 신규 금지.
- **배포 순서 의존**: db(마이그레이션)→api(Cloud Run)→web(Vercel). 신규 필드 nullable 하위호환 필수(3자 분리 배포). **부분배포/롤백 정합성 명시**(예: web 먼저·api 미배포 시 hybrid 500) — 단계 실패 시 중단·역순 롤백 규칙 필요(AC-DEPLOY-1).
- **배포 드리프트 정정**: 원본 architecture.md는 Vercel 우선 서술이나 실제 api는 Cloud Run 2서비스(encar-ai-api/-dev, 서울) 운영 중 — 본 증분 문서가 실제 상태로 갱신.
- **Supabase Realtime 특성**: 끊긴 구간 replay 없음 → 갭 보정 select가 폴링을 완전 대체 못함. 갭보정은 **서버 권위 커서(seq/id) 전제**(클라 시계 금지, Sally).
- **AI 안전장치 통과(sql_guard/ai_readonly, 미결정 아님·확정 코드변경)**: 하이브리드 신규 SQL이 `sql_guard.validate_select_sql()` 화이트리스트(벡터 `<=>` 연산자·`::vector` 캐스트 포함) 통과 + `status='on_sale'` 강제 유지 필수(AC-SEC-1).
- **커넥션 풀러 롤 격리(HIGH)**: 트랜잭션 풀러(:6543) 커넥션 재사용으로 `SET ROLE ai_readonly`가 다음 요청에 누수. 트랜잭션 스코프 격리 필수(AC-DB-1).

### Cross-Cutting Concerns Identified

1. **판매완료 비노출(FR11) 확장 — 강제지점 3→4** — 기존 3지점(RLS 0002 · sql_guard.py · 문서RAG필터)에 **하이브리드 벡터 검색 경로가 4번째 신규 강제지점**으로 추가(Amelia). 이제 확장 표면=이미지 공개URL(sold 사진 잔존)·view_count RPC·하이브리드 SQL·상세 URL 직접접근 404. 새 조회 경로마다 이 필터를 함께 적용(단일 규칙 원칙 계승). 앱 레벨 필터링 금지.
2. **RLS 기반 보안 / service_role 금지** — 이미지·view_count·realtime 신규 경로 전반. SECURITY DEFINER 함수(view_count)는 하드닝 규칙(search_path 고정·REVOKE FROM PUBLIC) 필수(AC-SEC-2).
3. **공유 계약 ListingCard(conventions.md §4)** — 이미지·(선택)신뢰속성·view_count 필드를 web·app·api **동시 개정**(계약 drift 1순위 위험). 이미지 필드는 단일 URL이 아니라 **변형 세트 {thumb/card/full} + null 허용 + 상태(없음/처리중/실패)**로 설계(Sally). AI 응답 카드도 동일 계약 공유(ai_readonly SELECT 화이트리스트에 image 필드 포함, AC-CONTRACT-1).
4. **AI 안전장치(sql_guard/ai_readonly)** — 하이브리드 신규 SQL 생성 경로 편입 + 커넥션 풀러 롤 격리.
5. **웹/앱 디자인 언어 공유 vs 구현 분리** — 토큰 원천 관리(공용 JSON vs 수동 이중화) 결정 필요, 계약은 conventions.md 단일출처.
6. **멀티턴 상태(되묻기·조합형)** — 무상태 유지하며 클라이언트 이어붙이기로 구현. **상태 소유권(서버 vs 클라 왕복) 명시 필요**(Sally — 새로고침 시 멀티턴 증발 방지). AI 4응답유형은 서버가 **구조화 사유 데이터**(예 `narrowed_by`)를 내려 결정론 템플릿이 조립(0건·REJECT 다양성을 문장이 아닌 데이터 조합에서, Sally/John).
7. **F14 역할통합의 워크스트림 분리** — 인증·RLS 변경을 이미지/UI 커밋과 분리 관리. **단 분리 ≠ 독립**(John): F14의 전제를 F9(내 차 팔기 진입)·F12(역할 판정)가 참조하는 인바운드 의존 여부 확인. role CHECK 완화가 기존 RLS role 비교를 안 깨는지 grep 검증(AC-F14-1).
8. **데이터 생애주기·고아정리(Mary)** — 아래 표. 이미지·view_count·신뢰속성 각각에 생성·수정·sold·삭제 시점의 정리 주체를 명시(현재 "미정"은 결정 회피).
9. **관측성 사각(Mary)** — LangSmith는 api RAG만 관측. 웹소켓 구독실패·이미지 업로드실패는 구조화 로그 한 줄. 추가로 **"성공의 관측 불가"**(서명URL 만료로 조용히 깨지는 이미지, 조용히 2배 뛰는 view_count)를 인지 — 전면 APM은 과설계(다음 증분).

### 데이터 생애주기 표 (Mary 지적 — cross-cutting 8 상세)

| 데이터 | 생성 | 수정 | sold | 삭제 | 정리 주체 |
|---|---|---|---|---|---|
| 이미지(image_urls) | 등록 시 업로드 | 사진 교체 → 옛 파일 **고아** | 공개버킷이면 공개URL 잔존(FR11 우회: 상세·찜·채팅썸네일·랜딩 4표면) | text[] cascade 없음 → 스토리지 **고아** | **미결 → OI-3에서 결정**(비공개+서명URL 유력, 정리 주체 지정) |
| view_count | default 0 | — | 정렬에서 제외(FR11) | 행과 함께 삭제 | RPC 단일 쓰기통로, AI 카드 렌더 시 **중복증가 방지**(멱등/조회 정의) |
| 신뢰속성(accident_status/is_single_owner/is_non_smoker) | nullable, 미입력 가능 | 판매자 수정 | — | 행과 함께 | 기존 100건=NULL="미입력" **제3상태**(초록뱃지도 사고표시도 아님, 면책 라벨) |

### 선결 요구 확정 (party-mode 반영, 사용자 승인 2026-07-12)

아키텍처 진입 전 "병기"를 "결정"으로 전환(John/Mary 지적). 5건 확정:

1. **AI 응답 카드 이미지 — FR 신설 아님, 계약 개정이 실제 조치.** 소유 FR은 **이미 PRD FR28**("AI 검색 응답 카드에도 대표사진, 없으면 '사진 준비중' 플레이스홀더"). **실제 조치 = `docs/conventions.md §4 ListingCard` 계약 개정**: 현재 "사진 없음(썸네일 필드 없음)" → **image 필드 nullable + null 시 5:3 비율 유지 플레이스홀더 렌더**. 변형 세트·서버 크롭은 아키텍처 결정(OI-3)으로.
2. **REJECT/0건 — 판정=결정론 / 표현=고정템플릿 선택(생성 아님).** FR47 "고정 템플릿 유지"와 정합. 다양성은 문구 생성이 아니라 서버가 내려주는 **구조화 사유 데이터**(예 `narrowed_by:["price<3000"]`)를 결정론 템플릿이 조립(0건 막다른 길·거절 다양화를 한 축으로 해소).
3. **FR34 랜딩 ≠ 보류된 "홈 전체판" (Cut 유지).** 보류된 "홈 전체판"의 정의는 **"홈이 필터·URL·페이지네이션을 직접 소유하는 탐색 화면"**(tech-debt 원문) — 로그인 대시보드가 아님. FR34 그리드는 **인기/최신 발췌 + "전체 보기"→/search 진입 = 미리보기판**(PRD FR34 각주에 이미 명문화, 아키텍처는 이를 인용). **아키텍처 제약으로 박음: 랜딩은 필터 상태·URL 쿼리파라미터를 소유하지 않는다. 전체 필터·목록·페이지네이션의 단일 소유자는 `/search`다.**
4. **찜 동기화 + 판매자정보 경계.** 찜=서버(DB) 단일저장, 웹/앱은 조회 시 반영(**실시간 sync 아님** — Reuse-First·A2, FR55에 sync 요구 없음). 판매자정보 경계=**FR56 그대로**(닉네임+가입시점+"다른 매물 N건"; 평판점수·응답률·인증배지는 명시 범위밖).
5. **신뢰속성 자기신고 카피.** "판매자 제공 정보" 면책 라벨 필수(FR30·CM-C·D13). 기존 100건 NULL → "미입력" 제3상태 UI(초록뱃지와 구분).

### 아키텍처가 확정할 선결 기술 AC (dev 진입 전, party-mode/Amelia)

- **AC-DB-1 (커넥션 풀 롤 격리) — 우선순위 최상, F13 RAG 구현 선행.** ① FR50(커넥션 풀·타임아웃·async)과 **동일 작업 단위**. ② 방식: `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`(세션레벨 SET ROLE 금지). ③ **검증 AC**: "동일 물리 커넥션을 재사용하는 동시/연속 2요청에서, 2번째 요청의 실행 롤이 직전 ai_readonly로 새지 않는다"를 증명하는 테스트. ④ 순서: **하이브리드/4분기 착수보다 앞**.
- **AC-SEC-1 (하이브리드 sql_guard 정비)**: `validate_select_sql()`에 벡터 `<=>` 연산자·`::vector` 캐스트 화이트리스트 추가 + `status='on_sale'` AND 강제. 회귀 3케이스(정상 벡터쿼리 통과 / OR·서브쿼리 주입 거부 / status 필터 누락 거부).
- **AC-SEC-2 (view_count RPC 하드닝)**: `SET search_path=''` + `REVOKE EXECUTE FROM PUBLIC` + `GRANT EXECUTE TO anon, authenticated` + `listings.view_count` 직접 UPDATE를 RLS로 봉쇄(RPC가 유일 쓰기통로).
- **AC-CHAT-1 (멱등키)**: `UNIQUE(chat_room_id, client_message_id)` + `ON CONFLICT DO NOTHING`. 기존 0003c BEFORE INSERT 트리거·0010 2000자 제약과 충돌 검증(동일 키 2회 INSERT 시 행 1개·트리거 부작용 0).
- **AC-CHAT-2 (재연결 갭보정)**: dedup 키=`client_message_id`, 서버 권위 커서(seq/id) 전제. 갭보정 재조회분이 이미 표시된 메시지와 중복 안 됨.
- **AC-CONTRACT-1 (ListingCard 이미지 계약)**: `ai_readonly` SELECT 화이트리스트에 image 필드 추가 + AI 응답 스키마 nullable 명문화 + conventions.md §4 반영(선결 요구 확정 1과 연동).
- **AC-DEPLOY-1 (배포·롤백)**: db→api→web 순 + 부분배포 상태(db+api 신, web 구) 정합성 + 단계 실패 시 중단·역순 롤백.
- **AC-F14-1 (역할 CHECK 완화)**: role CHECK 완화가 기존 RLS의 role 비교를 안 깨는지 grep 검증(0002 등).

### 다음 스텝(Core Decisions)에서 확정할 미결정

OI-3 이미지 스토리지(공개/비공개+서명URL·정리주체·변형세트·서버크롭) · OI-4 웹소켓 transport(Supabase Realtime·폴링 잔존 범위·갭보정 커서) · 찜 테이블 스키마 · ListingCard 계약 확장(conventions §4) · 신뢰속성 컬럼 최종(accident_status enum vs bool 승격, nullable/미입력) · 마이그레이션 번호 계획(0011~, RLS 동거 원칙) · F14 스코프(인바운드 의존) · 멀티턴 상태 소유권 · AI 4응답유형 계약(narrowed_by). **+ Reuse-First 자산 인벤토리(재사용 대상 목록: migrations 0001~0010·기존 ListingCard·sql_guard·폴링→Realtime·corpus 로더) 명문화**(Mary — 원칙을 검증 가능 제약으로). **+ OI 번호 정본 단방향 포인터**(increment-open-decisions.md → PRD §7).

---

## Starter Template Evaluation (증분 = 기존 레포 계승)

### Primary Technology Domain
브라운필드 풀스택 증분 — 신규 스타터 템플릿 평가 대상 아님. 기존 레포가 기반이며, Reuse-First 지배 원칙에 따라 스택·구조·패턴을 그대로 계승한다. (신규 스캐폴딩 없음)

### 계승하는 기반 (Selected "Starter" = 기존 모노레포)
폴리글랏 모노레포 4파트, 버전은 레포 고정값(project-context.md가 단일 출처):
- **web/** Next.js App Router 16.2.9 · React 19.2.4 · TypeScript 5(strict) · Tailwind v4(@theme)
- **api/** FastAPI 0.137.1 · LangGraph 1.2.4 · Python ≥3.10 · psycopg[binary] · langchain-google-genai
- **app/** Flutter(Dart ^3.12.2) · supabase_flutter 2.15 · flutter_riverpod 3.3 · http 1.6
- **supabase/** Postgres + pgvector + RLS · 번호순 마이그레이션 0001~0010(전진형)
- 배포: web=Vercel · api=Cloud Run(서울, encar-ai-api/-dev) · app=수동
- AI: 생성 gemini-3.1-flash-lite(고정) · 임베딩 gemini-embedding-001(768)

### 계승되는 아키텍처 결정 (스타터가 이미 정해둔 것 = 원본 architecture.md)
- 코드 조직: web 라우트 그룹 (auth)/(user)/(admin) · components/{ai,auth,layout,listings,ui} · lib/{api,auth,supabase}
- 상태·라우팅: 서버 컴포넌트 기본('use client' 최소) · Flutter Riverpod
- 테스트: api=pytest 결정론 단위+eval 트랙 · web=Playwright E2E 우선 · app=핵심 컨트롤러 단위+실폰 E2E
- 보안: anon key + RLS · sql_guard/ai_readonly · 무결성 트리거 · service_role 금지
- 계약: snake_case wire · ListingCard · 응답/에러 포맷 (docs/conventions.md 단일 출처)

### 증분이 새로 여는 기술 표면 (전부 기존 스택 내부, 신규 의존성/스타터 없음)
1. **Supabase Realtime** (F12 실시간 채팅) — 이미 설치된 supabase-js/supabase_flutter의 Realtime 구독 기능 활성화. 신규 라이브러리 없음. (transport 확정은 OI-4, Step 4)
2. **Supabase Storage** (F7 이미지) — 동일 Supabase 클라이언트의 Storage. 신규 의존성 없음. (공개/비공개 버킷·서명URL 확정은 OI-3, Step 4)
3. **LangSmith 트레이싱** (F13 관측성) — langsmith 0.8.18이 이미 전이 의존성으로 설치됨. env 2개(LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY)로 활성화, 코드 변경 0.
- 위 3개 모두 "새 스타터/프레임워크 도입"이 아니라 **기존 스택의 미사용 기능 활성화**다.

**Note:** 초기화 스토리 불필요(기존 레포). 증분의 첫 구현 스토리는 AC-DB-1(커넥션 풀 롤 격리, FR50 선행)이며, 이미지/실시간/RAG 스키마 마이그레이션(0011~)이 그 뒤를 잇는다.

---

## Core Architectural Decisions

_심화검토(2026-07-12/13, advanced-elicitation + party-mode) 개정 반영본. 확정 제약(Reuse-First·RAG (b)·운영 가정 렌즈) 하에서 결정._

### Decision Priority Analysis
**Critical (구현 차단):** 커넥션 풀 롤 격리(AC-DB-1, RAG 선행) · 이미지 스키마·스토리지(`listing_images` + 비공개버킷+서명URL) · 하이브리드 sql_guard 정비(AC-SEC-1) · 실시간 transport(Broadcast from Database) · ListingCard 계약 개정(AC-CONTRACT-1).
**Important (구조 형성):** 신뢰속성 `accident_status` enum · 옵션 통제어휘 · 찜(FR55) · view_count 하드닝 · 4분기 라우팅 · FR57 read-state · 마이그 0011~0018.
**Deferred (→ `implementation-artifacts/deferred-work.md`):** 찜 기반 인기신호 · 문서기반 차량상태(성능표/보험이력) · RAG 청킹 · 신고/차단 · 스토리지 정리 자동화 · 전면 APM · 이미지 모더레이션 · 관리자 신규기능(청소부). **PRD 역반영 대상:** 관리자 UI 통일(admin-mockups-2, UI-only 스코프 추가).

### Data Architecture
- **이미지 = `listing_images` 테이블(0011)**: `id · listing_id FK(ON DELETE CASCADE) · storage_path(비공개 버킷 key) · sort_order · is_cover bool · credit jsonb(저작자/라이선스/원본)`. RLS: listing 소유자만 insert/update/delete, select는 listings 정책 연동(sold 숨김 상속).
- **ADR-IMG-01 이미지 스토리지 = 비공개 버킷 + 서명 URL (+ 완화 3종)**: 업로드 anon+Storage RLS(본인 경로), service_role 금지. FR11=비공개+RLS로 소스 강제(sold→서명URL 미발급→비노출). 완화: ① 목록 `createSignedUrls` 배치 발급 ② **api는 서명URL이 아니라 storage_path만 반환**(ai_readonly 최소권한 유지) ③ 만료 넉넉히+클라 재발급. 변형(thumb/card/full)=Next.js Image(web) 원본 파생, app은 서명 원본. 근거=pre-mortem·red-team·가중매트릭스(FR11은 PASS/FAIL 게이트). **[낮은 우선순위 설계지침]** 서명URL 헬퍼·업로드 RLS·버킷 경로 규칙을 이미지 전용이 아니라 **아티팩트 범용**으로 작성(향후 deferred 문서 기능이 배관 재작업 없이 재사용).
- **신뢰속성(0012, 전부 nullable=미입력 제3상태)**: `accident_status` enum(무사고/단순교환/사고) + `is_single_owner` bool + `is_non_smoker` bool. (운영 가정 렌즈에서 bool→enum 상향 — "단순교환" 표현·확장성). 기존 100건=NULL 유지(backfill 안 함). "판매자 제공 정보" 면책 필수. sql_guard 화이트리스트·AI 프롬프트 스키마·ListingCard·web/app 매퍼 락스텝.
- **옵션**: `text[]` 유지 + **쓰기 시 표준 옵션명 상수 검증(controlled vocabulary)** + 기술부채 #11(쉼표 라운드트립, `SellForm.tsx`) 정비. 정규화 테이블 없음.
- **찜(0015, FR55 기본만)**: `wishlists(user_id, listing_id, created_at, PK(user_id,listing_id))` + 본인 RLS. 토글·내 찜 목록. **인기신호(favorite count)는 보류(deferred-work ①)** — wishlists가 COUNT 원천이라 향후 인덱스+집계로 승격.
- **view_count(0014, OI-5)**: `listings.view_count int default 0` + `increment_listing_view()` RPC + 하드닝(AC-SEC-2). AI 카드 렌더 시 중복증가 금지.
- **마이그레이션(additive, forward-only, RLS 동거)**: `0011 listing_images · 0012 신뢰속성 · 0013 role CHECK 완화 · 0014 view_count+RPC · 0015 wishlists · 0016 chat 멱등키 · 0017 realtime broadcast · 0018 chat_room_reads`.
- **ListingCard 계약 개정(conventions §4, AC-CONTRACT-1)**: `image_url`(대표 서명 URL, nullable → null이면 "사진 준비중" 5:3 플레이스홀더) + `view_count`. web/app/api 동시 개정.

### Authentication & Security
- 이미지 업로드: anon + Storage RLS(본인 경로), 비공개 버킷, service_role 금지.
- **AC-DB-1 커넥션 풀 롤 격리 (우선순위 최상·RAG 선행)**: `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`. 검증 테스트: 동일 물리 커넥션 재사용 동시/연속 2요청에서 롤 누수 없음. FR50과 동일 작업 단위.
- **AC-SEC-1 하이브리드 sql_guard**: `validate_select_sql()`에 `<=>`·`::vector` 화이트리스트 + `status='on_sale'` 강제. 회귀 3케이스(정상 통과/OR·서브쿼리 거부/status 누락 거부).
- **AC-SEC-2 view_count RPC 하드닝**: `search_path=''`·`REVOKE EXECUTE FROM PUBLIC`·`GRANT anon/authenticated` + 직접 UPDATE RLS 봉쇄(RPC가 유일 쓰기통로).
- **AC-CHAT-1 멱등키(0016)**: `client_message_id` + `UNIQUE(chat_room_id, client_message_id)` + `ON CONFLICT DO NOTHING`. 0003c 트리거·0010 2000자 충돌 검증.
- **AC-F14-1 role CHECK 완화(0013)**: role 존치(is_admin 의존), buyer/seller 무의미화·admin 존치. 기존 RLS role 비교 grep 검증. 별도 워크스트림.

### API & Communication Patterns
- **실시간 transport = Supabase Realtime "Broadcast from Database"(0017)**: 트리거(`realtime.broadcast_changes`) + `realtime.messages` RLS + private 채널. **chat_messages 스키마 불변(소스 오브 트루스)**. Supabase 공식 권장(확장성·타이핑/읽음 확장). 순서=클라가 chat_messages `created_at` 정렬 렌더(전송순서 무관 → Broadcast 순서 미보장 상쇄). 재연결 갭보정=Broadcast Replay(≤25/72h) 우선 + 초과분 chat_messages 재조회. Flutter=supabase_flutter Realtime 동일.
- **AC-CHAT-2 갭보정 커서**: 서버 `created_at` + `id` tiebreak(Supabase Replay도 타임스탬프 커서). 재조회분 dedup 키=`client_message_id`.
- **FR57 안읽음(0018)**: `chat_room_reads(user_id, room_id, last_read_at)` → 안읽음 카운트 = `created_at > last_read_at` 집계. 방 목록 최신순.
- **4분기 라우팅(FR43)**: `add_conditional_edges` 확장(REJECT/CLARIFY/SQL/HYBRID), RouterDecision Literal·`_fallback_route`·`_route_decision` **3곳 락스텝**.
- **하이브리드 검색(FR45)**: 단일 쿼리 `WHERE status='on_sale' AND <구조조건> ORDER BY embedding <=> $1::vector`(sql_guard 통과, RRF 없음). 구조조건 미추출 시 기존 벡터검색 유지(회귀 없음).
- **가이드 (b) 질의확장**: 가이드 content로 검색조건 확장(답변은 결정론 유지, LLM 설명생성 안 함).
- **AI 응답 계약**: `{answer, listings[], route, narrowed_by?}`. 0건·거절=**구조화 사유 데이터**(narrowed_by)로 결정론 템플릿 조립(문장 다양화 아님). 되묻기=제안형 질문+tappable 칩(추가 LLM 없음). answer_node 결정론·고정 거절 유지(FR47).
- **멀티턴 상태 소유권=클라이언트**: 대화 턴 클라 보관·동봉(contextualize_query, 무상태). interrupt()/체크포인터 미도입.
- **LangSmith 트레이싱**: env 2개(코드 변경 0).

### Frontend Architecture
- 서버 컴포넌트 기본('use client' 최소) · AI 멀티턴=클라 보관 · Flutter Riverpod.
- 반응형: 단일코드(FR36) + **D5 반응형 무결성(project-context 규칙13) 강제** — 세로화·줄바꿈 어긋남 금지, 관리자 포함.
- 이미지: 대표=서명 URL, null→플레이스홀더 **3상태(없음/처리중/실패)**. 비동기 업로드(폼 비차단)→"처리중"과 "준비중" 구분(방금 올린 판매자 불안 방지).
- 관리자: 6화면 디자인 시스템 통일+반응형(admin-mockups-2, UI-only 스코프 추가).

### Infrastructure & Deployment
- **AC-DEPLOY-1 배포 순서**: db(마이그)→api(Cloud Run)→web(Vercel), nullable 하위호환, 부분배포 정합성 + 단계 실패 시 중단·역순 롤백.
- 유지: api=Cloud Run(서울)·web=Vercel·app=수동. AI=gemini-3.1-flash-lite·임베딩768.
- 관측성: LangSmith(api RAG) + 웹소켓/이미지 실패 구조화 로그(전면 APM=deferred).

### Decision Impact Analysis
**Implementation Sequence:**
1. AC-DB-1 커넥션 풀 롤 격리(RAG 선행) → 2. 마이그 0011~0018 → 3. ListingCard 계약 개정 → 4. 이미지(업로드·서명URL·플레이스홀더 3상태) → 5. 신뢰속성·옵션·찜·view_count → 6. 실시간 채팅(Broadcast from DB+멱등+갭보정+안읽음) → 7. RAG 4분기(하이브리드+sql_guard+가이드 (b)+되묻기+LangSmith) → 8. UI 개편·반응형(사용자+관리자) → 9. Flutter 반영.
**F14 역할통합 = 별도 워크스트림**(인증·RLS, 커밋 분리).
**Cross-Component Dependencies:** ListingCard 계약(web/app/api 락스텝) · 신뢰속성 스키마 연쇄 · 이미지 서명URL(3클라) · 배포 순서 하위호환 · 하이브리드 SQL×sql_guard 보안 접점 · 이미지 Storage 헬퍼 아티팩트 범용(향후 문서 재사용).

---

## Implementation Patterns & Consistency Rules (증분)

_기존 `docs/conventions.md`·`project-context.md`(규칙 1~13)의 패턴을 그대로 계승한다. 아래는 이 증분이 새로 여는 충돌 지점의 규칙만. 확정 값은 `docs/conventions.md`에 반영(단일 출처)._

### Naming
- **신규 wire 필드는 전부 snake_case**(규칙 3): `image_url · view_count · accident_status · is_single_owner · is_non_smoker · client_message_id · sort_order · is_cover · last_read_at`. TS/Dart 내부는 camelCase 매핑, JSON엔 snake_case만 노출.
- **enum 값은 기존 CHECK 관례(한국어)에 맞춘다**: `accident_status` = `'무사고'·'단순교환'·'사고'` (영문 코드 금지 — body_type·color·region 한국어 관례와 일관).
- **Realtime 토픽 형식 = `chat:room:{room_id}`** (기능 네임스페이스 `chat:` + 방 단위). 0017 트리거·`realtime.messages` RLS·클라 구독 3곳이 동일 사용.
- **마이그레이션 파일**: `supabase/migrations/00NN_이름.sql`, RLS는 해당 테이블 마이그에 동거(규칙 10).

### Format
- **이미지 필드 계약(conventions §4 개정)**: `image_url` = 대표 이미지의 서명 URL(nullable). `null`이면 클라가 "사진 준비중" 5:3 플레이스홀더 렌더(계약의 일부). AI 응답 카드도 동일 계약 공유. 상태 3종(없음/처리중/실패)은 클라 로컬 상태.
- **서명 URL 만료 = 단일 상수**(예 `web/src/lib/storage`의 `SIGNED_URL_TTL`), 호출부 하드코딩 금지. 목록은 `createSignedUrls` 배치 1회.
- **AI 응답 계약**: `{ answer: string, listings: ListingCard[], route: 'REJECT'|'CLARIFY'|'SQL'|'HYBRID', narrowed_by?: string[] }`. `narrowed_by` = 0건·거절 시 사유 술어 라벨(예 `["price<=30000000"]`). 에러는 기존 `{error:{code,message(한국어)}}`.

### Communication (Realtime · AI)
- **Realtime 계약(하나의 단위로 고정)**: ① 토픽 = `chat:room:{room_id}` ② 이벤트 = 메시지 삽입(`broadcast_changes`) ③ 페이로드 = 삽입된 `chat_messages` 행 형태(snake_case). **이 계약을 0017 트리거(토픽 생성)·`realtime.messages` RLS(토픽 파싱)·클라 구독이 동일하게 사용**(불일치 시 인증·수신 붕괴).
- **서명 URL 발급 금지 대상 = api(FastAPI)뿐** *(정정 2026-07-13, epics 단계: 기존 "서버만" 문구는 아래 332행 "web/app이 서명"과 모순 — Flutter 앱은 서버가 없는 클라이언트다. 근거: PRD FR39·NFR7·ADR-IMG-01에서 앱은 `supabase_flutter`로 서명 원본을 받으므로 클라측 서명이 유일 경로. 따라서 규칙은 "서버만"이 아니라 "api만 금지")*: **web=서버 컴포넌트/route(서버측 발급)**, **app(Flutter)=`supabase_flutter` Storage(클라측 발급)**, **api는 절대 서명 안 하고 `storage_path`만 반환**(ai_readonly 최소권한). 헬퍼는 **아티팩트 범용**(`getSignedUrl(bucket, path)`). 서명 성립 전제 = 발급 주체가 `storage.objects` SELECT 권한 보유(비공개 버킷 RLS: on_sale이거나 본인 소유 — epics 9.1).
- **Realtime 수명주기**: `setAuth()` → private 채널 subscribe → 언마운트 시 unsubscribe.
- **재연결 갭보정**: Broadcast Replay(≤25/72h) 우선, 초과분 `SELECT ... WHERE created_at > {cursor} ORDER BY created_at, id`. dedup 키 = `client_message_id`.
- **멱등키**: 클라가 uuid v4를 `client_message_id`로 생성·전송. 서버 `ON CONFLICT DO NOTHING`.

### Process
- **AI DB 읽기는 매 쿼리 트랜잭션 격리**: `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`(AC-DB-1). ❌ 세션 레벨 `SET ROLE`.
- **4분기 라우팅 3곳 락스텝**: `RouterDecision` Literal · `_fallback_route` · `_route_decision` 세 곳 모두 갱신.
- **읽음 상태**: 방 진입/열람 시 `chat_room_reads.last_read_at` 갱신 → 안읽음 = `created_at > last_read_at` 집계.
- **하이브리드 SQL은 반드시 sql_guard 통과 + `status='on_sale'`**(AC-SEC-1), 앱 레벨 필터 금지.

### 신규 AC (Realtime 보안)
- **AC-CHAT-3 (Realtime 참가자 인가)**: `realtime.messages` RLS가 토픽 `chat:room:{room_id}`를 파싱해 "요청자가 그 room의 buyer/seller인가"를 검사(0017). private 채널 + `setAuth` 전제. **채팅 실시간 보안의 핵심 지점**.

### Enforcement
**모든 AI 에이전트 MUST:**
- 신규 wire 필드 snake_case + enum은 한국어 값(기존 CHECK 관례).
- api는 서명 URL 발급 금지(`storage_path`만) · 서명은 서버 헬퍼(아티팩트 범용).
- Realtime 토픽/이벤트/페이로드 = 단일 계약, 3곳(트리거·RLS·클라) 일치 · AC-CHAT-3 참가자 검사.
- 4분기 3곳 락스텝 · AI 읽기 `SET LOCAL ROLE` · 하이브리드 sql_guard 통과.
- D5 반응형 무결성(규칙 13) — 관리자 포함.
- 확정 계약은 `docs/conventions.md`에 먼저 반영 후 코드(규칙 1, 단일 출처).

**Anti-patterns:** api가 서명 URL 반환 · 세션 `SET ROLE` · 라우트 한 곳만 추가 · `image_url`을 공개 URL로 저장 · enum 영문 코드 · 서명 만료 하드코딩 · 앱 레벨 sold 필터 · Realtime 토픽 형식이 트리거/RLS/클라 간 불일치.

---

## Project Structure & Boundaries (증분 델타)

_브라운필드 — 기존 4파트 구조 위에 증분이 더하는 것만 표기. `✚`=신규 파일/폴더, `✎`=수정._

### 프로젝트 트리 (증분 델타)
```
supabase/migrations/
  0001~0010 …………………………………… (기존)
  ✚ 0011_listing_images.sql ……… listing_images + 비공개 버킷·Storage RLS(아티팩트 범용)
  ✚ 0012_trust_status.sql ……… accident_status enum·is_single_owner·is_non_smoker
  ✚ 0013_role_check_relax.sql … F14 role CHECK 완화(admin 존치)
  ✚ 0014_view_count.sql ………… view_count + increment_listing_view() RPC(하드닝)
  ✚ 0015_wishlists.sql ………… wishlists(찜)
  ✚ 0016_chat_idempotency.sql … chat_messages.client_message_id + UNIQUE
  ✚ 0017_chat_realtime.sql …… broadcast 트리거 + realtime.messages RLS(AC-CHAT-3)
  ✚ 0018_chat_room_reads.sql … 읽음 상태(안읽음 배지)

web/src/
  app/
    page.tsx …………………………… ✎ 랜딩(홈): AI 히어로 + 인기/최신 그리드 + 차종 칩(FR33~35)
    (user)/
      listings/[id]/ ………… ✎ 갤러리·신뢰뱃지·판매자정보(FR28/30/56)
      sell/ …………………………… ✎ 사진 업로더·신뢰속성 입력·옵션 통제어휘(FR26/30/31)
      chat/[roomId]/ ……… ✎ 폴링 제거→Realtime 구독·멱등·재연결 배너(FR40~42)
      ✚ wishlist/ ………………… 찜 목록(FR55)
    (admin)/admin/ ……………… ✎ 6화면 디자인시스템 리스킨 + 회원관리 필터(admin-mockups-2, FR52~54)
  components/
    listings/ ………………………… ✎ ListingCard(이미지·조회수)·ListingDetailFields(갤러리·신뢰속성) ✚ ImageGallery·ImageUploader·TrustBadges·WishlistButton·OptionPicker
    ai/ ………………………………………… ✎ 4분기 응답 UI ✚ ClarifyChips(되묻기)
    layout/ …………………………… ✎ 상단 내비 재구성(FR38)
    ui/ ……………………………………… ✎ 반응형 프리미티브(D5) · 토큰(@theme)
  lib/
    ✚ storage/ ……………………… 서명 URL 헬퍼(아티팩트 범용, createSignedUrls 배치, SIGNED_URL_TTL)
    supabase/ ………………………… ✎ Realtime broadcast 구독·setAuth
    messages.ts ………………… ✎ 멱등키·갭보정
    constants.ts ……………… ✎ 옵션 통제어휘·priority·신뢰속성 라벨
  app/globals.css ……………… ✎ Tailwind v4 @theme 팔레트 토큰(FR37)

api/app/
  graph/
    router_node.py ……………… ✎ 4분기(REJECT/CLARIFY/SQL/HYBRID) Literal·_fallback_route
    graph.py ……………………………… ✎ _route_decision·add_conditional_edges 확장(3곳 락스텝)
    ✚ clarify_node.py ………… 되묻기(무상태, answer 반환)
    doc_rag_node.py ……………… ✎ 하이브리드 승격 + 가이드 content (b)질의확장 + 거리 컷오프
    answer_node.py ……………… ✎ narrowed_by 구조화 사유(결정론 유지)
    listing_cards.py …………… ✎ image=storage_path 반환(api는 서명 안 함)
  db/
    sql_guard.py ………………… ✎ <=>·::vector 화이트리스트 + status='on_sale' 강제(AC-SEC-1)
    readonly.py ……………………… ✎ 커넥션 풀 + BEGIN;SET LOCAL ROLE;COMMIT(AC-DB-1) + async
  schemas/ai.py ………………………… ✎ route 4값·narrowed_by·ListingCard image
  config.py …………………………………… ✎ LangSmith env 2개

app/lib/ (Flutter)
  features/
    listings/ ……………………… ✎ 갤러리·신뢰뱃지·찜·카드 재설계(FR39)
    chat/ ……………………………………… ✎ supabase_flutter Realtime·멱등·재연결(FR40~42)
    ✚ wishlist/ ……………………… 찜 목록
    ai_search/ …………………………… ✎ 4분기 응답·되묻기 칩
  core/theme/ …………………………… ✎ 디자인 토큰 미러(웹과 동일 언어, D14)
  core/supabase/ …………………… ✎ Realtime·Storage 서명 URL
  main.dart / router …………… ✎ 하단 4탭(GoRouter StatefulShellRoute, D12)

docs/
  conventions.md ………………………… ✎ §4 ListingCard 개정 + 신규 절(신뢰속성·Realtime 계약·이미지)
  db-schema-guide.md ……………… ✎ 신규 테이블/컬럼
```

### Architectural Boundaries (기존 경계 계승 + 증분 배치)
- **Client ↔ Supabase 직접(SDK+RLS)**: 이미지 Storage·Realtime 채팅·찜·view_count RPC 전부 이 경계에서 처리(FastAPI 경유 안 함). service_role 금지.
- **FastAPI = AI 검색 전용**(`/ai/search`, ai_readonly 롤): 하이브리드 검색·4분기·되묻기. **api는 서명 URL 발급 안 함 → `storage_path`만 반환**(web/app이 서명).
- **Realtime 경계**: 0017 트리거(DB) → `realtime.messages`(private) → 클라 구독. 토픽 `chat:room:{room_id}` 3곳 일치(AC-CHAT-3).
- **배포 경계**: db(Supabase 마이그)→api(Cloud Run)→web(Vercel)·app(수동). nullable 하위호환(AC-DEPLOY-1).

### Requirements → Structure 매핑
- **F7 이미지** → 0011 · components/listings(Gallery/Uploader) · lib/storage · listing_cards.py(path)
- **F8 신뢰속성/옵션/찜/판매자** → 0012·0015 · components/listings(TrustBadges/OptionPicker/WishlistButton) · (user)/wishlist · constants
- **F9 랜딩** → 0014(view_count) · app/page.tsx
- **F10 반응형·토큰** → globals.css · components/ui(D5)
- **F11 Flutter** → app/lib/features·core/theme
- **F12 실시간채팅** → 0016·0017·0018 · (user)/chat · lib/supabase·messages.ts · features/chat
- **F13 RAG** → graph/*(router·clarify·hybrid·answer)·sql_guard·readonly·schemas·config
- **F14 역할통합(별도 워크스트림)** → 0013 · (admin)/admin(회원관리) · 판매 게이트
- **관리자 UI 통일(UI-only 스코프 추가)** → (admin)/admin 6화면(admin-mockups-2)

---

## Architecture Validation Results

_검증 방식: **깨끗한 컨텍스트의 독립 리뷰어 3인(opus)**이 원문(PRD·UX·conventions·project-context·실제 마이그레이션·`sql_guard.py`·`readonly.py`·`0003_chat.sql`)을 직접 grep 대조하며 적대적 검증(자기채점 편향 회피, `verify-in-clean-context`). 커버리지 / 일관성·제약 / 구현준비도 3렌즈._

> **⚠️ 아래 "정정(Corrections)"은 앞선 모든 섹션과 충돌 시 우선한다(단일 진실). dev는 이 섹션을 최종 계약으로 따른다.**

### 하드 제약 정합 — 통과 확인 (적대적으로 팠으나 위반 없음)
service_role 금지(규칙6) · 임베딩 768(규칙2) · 마이그 번호 무충돌(0011~0018) · RLS 동거(규칙10) · D5 반응형(규칙13) · 커넥션 풀 롤 격리 방향(SET LOCAL) · **CM-B(FR11 sold 비노출)은 비공개버킷+서명URL+status='on_sale' 강제로 아키텍처적으로 견고** · CM-A(100건 보존)·CM-C(면책) 확인.

### 정정 — CRITICAL (그대로면 마이그 실패·기능 파손·계약 붕괴)
- **CR1 컬럼명**: AC-CHAT-1 `UNIQUE(chat_room_id, …)` → **`UNIQUE(room_id, client_message_id)`**(실제 컬럼=`room_id`, 0003_chat.sql). 0016·0017·0018·토픽의 방 식별자 전부 `room_id`로 통일.
- **CR2 이미지×AI 안전장치**: "ai_readonly 화이트리스트에 image 필드 추가"는 무효(listings에 이미지 컬럼 없음). → **① `listing_images`에 `ai_readonly using(true)` SELECT 정책 추가(0011) ② api는 sql_guard 결과 on_sale id로 `listing_images` 대표 1장 storage_path를 별도 고정쿼리로 조회**(sql_guard는 listings 단일테이블 유지, JOIN 안 함). FR11=on_sale id 스코프로 유지.
- **CR3 image_url 계약**: wire = **단일 `image_url`(대표 서명 URL, nullable)** 로 확정. 변형(thumb/card/full)은 **클라 렌더 파생**(web Next.js Image)이지 wire 계약 아님. (cross-cutting #3의 "변형세트" 문구 철회)
- **CR4 narrowed_by**: `string[]` = **저장단위(원) 정규화 술어**(예 `["price<=30000000"]`, 만원 예시 폐기). 한국어 렌더 매핑 소유자 = `answer_node` 결정론 템플릿.
- **CR5 CLARIFY 칩**: AI 응답 계약에 `clarify?: { question: string, chips: string[] }` 추가(route='CLARIFY' 전용). 칩은 추가 LLM 없이 제안 렌더.
- **CR6 갭보정 커서**(uuid 비단조 문제): **`created_at >= {cursor}` (strict > 아님) + `client_message_id` dedup**(신규 컬럼 없음). 동일 타임스탬프 메시지 누락 방지. 표시 정렬 = created_at.

### 정정 — IMPORTANT
- **I1 readonly.py 대체 명시**: AC-DB-1(:6543 트랜잭션 풀러 + `SET LOCAL ROLE` + autocommit 제거)이 **현행 `readonly.py`의 :5432 세션풀러+세션 SET ROLE+autocommit 결정을 대체**함(주석 갱신 포함).
- **I2 비로그인 AI검색**: api 델타에 **`auth.py` 수정 추가** — `/ai/search` JWT 게이트를 비로그인 허용으로 완화(FR58). ai_readonly·sql_guard 안전장치는 유지.
- **I3 FR52 가입/트리거**: F14 델타에 **`(auth)/signup` 역할선택 UI 제거 + `0001 handle_new_user` 트리거의 신규 가입 기본 role 배정** 추가(역할선택 제거 시 role 기본값 필요).
- **I4 sql_guard 하이브리드**: AC-SEC-1에 **`embedding` 컬럼·`vector` 식별자도 화이트리스트 추가**. 벡터절은 **LLM이 아니라 코드가 `ORDER BY embedding <=> $1::vector LIMIT k`를 바인드 파라미터로 덧붙임**(LLM은 WHERE 구조조건만 생성 → sql_guard 통과, 벡터는 코드).
- **I5 view_count 봉쇄**: "직접 UPDATE를 RLS로 봉쇄"는 부정확(RLS는 행 단위). → **`REVOKE UPDATE(view_count) FROM authenticated`**(컬럼 권한)으로 RPC 유일 쓰기통로 강제.
- **I6 안읽음 필터**: 안읽음 = `created_at > last_read_at **AND sender_id != {me}**`(내 발신 제외).
- **I7 FR29 N장**: ListingCard 계약에 **`image_count`** 추가. api는 on_sale 스코프로 `listing_images` count 반환.
- **I8 이미지 처리상태**: 처리중·실패는 **업로더 본인 세션의 로컬 상태**(업로드 중 UI). wire는 null/url만. 등록 시 이미지 업로드 후 대표 세팅 완료→노출.
- **I9 멀티턴 지속화**: 클라 멀티턴 상태를 **sessionStorage에 지속**(세션 내 새로고침 생존).
- **I10 Realtime 페이로드**: `broadcast_changes` 엔벨로프(`{schema,table,operation,record,…}`), 클라는 **`payload.record` 파싱**. 이벤트 문자열 명시(INSERT).
- **I11 AI 입력 상한**: `schemas/ai.py`에 **500자 서버측 검증(422)** 추가(클라 상한만으론 우회).
- **I12 되묻기 cap**: 무상태이므로 **클라 강제** — 클라가 소유한 멀티턴 상태에서 clarify 횟수(≤2~3) 추적해 초과 시 칩 숨김/일반 검색.
- **I13 "스키마 불변" 문구 한정**: "broadcast를 위한 chat_messages 스키마 변경 없음(멱등 컬럼 `client_message_id`는 별개 additive)".
- **I14 5:3 크롭**: **클라 렌더 크롭**(web `object-fit:cover`·app `BoxFit.cover`, 중앙 기준), 저장은 원본. web/app 동일 구도.

### 확정된 값 (사용자, 2026-07-13)
- **`SIGNED_URL_TTL` = 3600s(1시간)**. FR11: sold 전환 후 기발급 URL은 최대 1시간 유효(노출 창 짧음, 수용).
- **매물당 최대 10장 / 장당 5MB**(OI-3 잔여 결정). 업로드 RLS·NFR7 저비용 정합.
- **갭보정 커서 = `created_at >=` + `client_message_id` dedup**(신규 컬럼 없음).
- **accident_status 표시**: `무사고`=초록 신뢰뱃지 · `단순교환`·`사고`=중립 상태칩(초록 아님, 가치중립 사실 표시). 면책(판매자 제공) 유지.
- **`accident_status` 타입 = `text + CHECK`**(native enum 아님, 기존 body_type/color/region 관례 일치).

### 정정 — MINOR (dev 단계 이월/보강)
- G1(CLARIFY 과다발동)·G2(RAG 회귀)를 **dev 테스트 게이트 AC로 승격**(Phase B 하니스 베이스라인 실측 후 배포).
- **강제 테스트 AC 추가**: D5 반응형 무결성(뷰포트별 E2E) · "api는 서명 URL 반환 안 함"(응답 단언) · 4분기·Realtime 토픽 3곳 일치(grep 테스트).
- D9 상세 순서: `mockups/detail-1.html`은 **구버전 순서(옵션↔차량)** — 스파인(DESIGN 본문)이 정답, 목업 맹종 금지 경고.
- backdrop-filter blur 구형 Flutter WebView no-op → **불투명 폴백**(Flutter 델타에 재강조).
- 하이브리드 `LIMIT` 명시(기존 벡터경로 관례 상속) · FR44 가이드참조 판단 노드 위치 스토리 단계 확정 · FR56 "다른 매물 N건"을 FR11 강제지점에 명시 열거.

### Architecture Completeness Checklist
- [x] 요구사항 커버리지: FR26~58·개정FR·NFR·SM/CM/G 전수 대조(누락 0, 부분은 위 정정으로 해소)
- [x] 하드 제약 정합: service_role·768·RLS·FR11·채팅무결성·D5 위반 0
- [x] 구현 준비도: 계약·AC 모호점 정정 완료(room_id·image·narrowed_by·CLARIFY·커서 등)
- [x] 구조·경계: 증분 델타 매핑 + api `auth.py`·signup·트리거 보강
- [x] 의도적 deferred(찜 인기신호·문서기반 상태·청킹)는 정당, REQUIRED 기본 전부 커버

### Architecture Readiness Assessment
**Overall Status: READY FOR IMPLEMENTATION** (위 정정 반영 조건).
**Confidence: 높음** — 독립 3인 검증이 원문까지 파고들어 실질 결함을 사전 적발·정정. 차단성 결함 잔존 없음.
**Key Strengths:** FR11 4중 강제(비공개+서명URL·on_sale 강제)·Reuse-First(기존 스택 확장)·운영 가정 렌즈(enum·Broadcast)·보안 AC 촘촘(풀러 격리·sql_guard·RPC 하드닝).
**Future Enhancement:** 찜 인기신호·문서기반 차량상태·청킹·전면 APM·푸시 알림(전부 deferred-work.md).

### Implementation Handoff
- 이 문서(특히 정정 섹션)를 최종 계약으로 따른다. 확정 계약은 **`docs/conventions.md`에 먼저 반영 후 코드**(규칙1).
- **첫 구현 스토리 = AC-DB-1(커넥션 풀 롤 격리, RAG 선행)** → 마이그 0011~0018 → 계약 개정 → 이미지 → 신뢰속성/옵션/찜/view_count → 실시간채팅 → RAG 4분기 → UI/반응형 → Flutter. F14=별도 워크스트림.
