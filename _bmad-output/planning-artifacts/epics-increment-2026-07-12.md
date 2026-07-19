---
stepsCompleted: [1, 2, 3, 4]
scope: increment
validation: 'independent clean-context 2-reviewer pass 2026-07-13 — 0 blocker, 5 minor findings applied'
baselineEpics: _bmad-output/planning-artifacts/epics.md
epicNumberingStartsAt: 8
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-07-11/prd.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-07-11/addendum.md
  - _bmad-output/planning-artifacts/architecture-increment-2026-07-12.md
  - _bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md
  - _bmad-output/planning-artifacts/ux-designs/admin-web-increment-2026-07-12/admin-mockups-2.html
  - _bmad-output/project-context.md
project_name: 'bmad-encar-demo'
user_name: 'Dnjsg'
date: '2026-07-12'
---

# bmad-encar-demo — Epic Breakdown (증분 / Increment)

## Overview

이 문서는 완료된 **원본 Epic 1~7**(`epics.md`, v1.0.0) 위에 얹는 **이미지·UI 고도화 증분**(FR26~58 + 원본 FR 개정)을 구현 가능한 에픽·스토리로 분해한다. 원본 에픽은 기준선(baseline)으로 보존하며, **이 증분의 에픽 번호는 Epic 8부터** 시작한다.

입력: 증분 PRD(FR26~58)·증분 아키텍처(마이그 0011~0018·정정 CR/I 섹션이 최종 계약)·UX 스파인(DESIGN·EXPERIENCE, status:final)·관리자 6화면 목업. 지배 원칙 = **Reuse-First**(기존 스택 확장, 신규 구축 회피) + **A2 단순함 우선**(데모/과제 규모).

> **⚠️ 최종 계약 우선순위:** 증분 아키텍처의 **"Architecture Validation Results → 정정(CR1~6·I1~14)·확정된 값"** 섹션이 앞선 모든 서술과 충돌 시 우선한다. 아래 스토리 AC는 이 정정을 반영해 작성한다.

## Requirements Inventory

### Functional Requirements

> 원본 FR1~25는 `epics.md`가 보유(완료). 아래는 이 증분의 신규(FR26~58) + 원본 개정분.

**F7. 매물 이미지 (신규)**
- FR26: 판매자는 매물에 사진을 여러 장(최대 10장, 장당 5MB) 등록할 수 있다(선택 — 사진 없이도 등록 가능). 고정 비율 5:3. 기존 매물(사진 없음)은 그대로 유효(nullable, non-null 금지). 첫 장 = 대표사진(순서 변경 가능).
- FR27: 사진이 없는 매물은 목록·상세·AI 카드에서 "사진 준비중" 플레이스홀더(아이콘+문구)로 표시한다(빈 영역 금지). 기존 100건이 전부 이 상태.
- FR28 (FR10 개정): 매물 상세는 대표사진 + 갤러리(스와이프/넘김)로 여러 장을 보여준다. 목록 카드·AI 응답 카드(FR17 개정)는 대표사진 1장(없으면 플레이스홀더).
- FR29: 매물 카드에 사진 개수 "N장" 배지를 표시한다(사진 있는 매물 한정).

**F8. 카드·신뢰속성·옵션·찜·판매자 (신규)**
- FR30: 신뢰속성(무사고·1인소유·비흡연)을 옵션(장비)과 분리해 관리·표시한다. 세 속성 모두 "판매자 신고" 티어 → "판매자 제공 정보" 면책 라벨 필수(가짜 검증 UI 금지). 배치 = 신뢰속성 카드 상단, 옵션 하단.
- FR31: 매물 카드는 희소성 있는 옵션을 우선 노출한다(보편 옵션 저순위, 희소 옵션 상위). 카드=상위 3~4개, 상세=카테고리별 전량. 옵션 저장구조 정비(기술부채 #11, `SellForm.tsx` 쉼표 라운드트립).
- FR32: 카드 정보 위계 = 차량명 → 연식 → 주행거리 → 연료 → 지역 한 줄 + 가격 대형 볼드. 찜 버튼은 사진 밖(정보 영역). 비교(compare) 기능은 범위 밖.
- FR55: 찜(좋아요) — 로그인 사용자는 매물을 찜하고(listing_id 저장, 카드 토글), "찜한 매물" 목록에 도달할 수 있다.
- FR56: 판매자 정보 노출 — 매물 상세에 경량 판매자 섹션(닉네임 + 가입 시점 + "이 판매자의 다른 매물 N건"). 평판점수·응답률·인증배지는 범위 밖.

**F9. 랜딩페이지 (신규)**
- FR33: 랜딩(홈) 첫 화면은 AI 자연어 검색을 주인공으로(히어로 검색 입력 + 예시 질의 칩).
- FR34: 히어로 아래 매물 그리드 — 인기(view_count 정렬)/최근 등록(created_at) 2단 발췌 + "전체 보기"→/search. 랜딩은 필터 상태·URL 쿼리를 소유하지 않는다(전체 목록의 단일 소유자 = /search).
- FR35: 랜딩에 차종 빠른 진입(경차·SUV·전기 등 카테고리 칩/그리드).

**F10. UI 개편·반응형 (신규/개정)**
- FR36: 사용자 웹은 단일 코드 반응형(데스크톱↔모바일). 카드 그리드→모바일 캐러셀/1열, 필터 사이드바→바텀시트, 상단 내비→햄버거.
- FR37: 전 화면에 일관된 디자인 시스템(페트롤+앰버 팔레트를 Tailwind v4 @theme 토큰으로 중앙 관리, 카드/뱃지/버튼/타이포 위계 통일).
- FR38: 사용자는 매물 탐색·등록·AI 검색·내 채팅·내 매물 관리·찜에 명확한 경로로 도달. AI 검색 1급 노출, 문의는 매물 상세 "문의하기"로만 개시(전역 문의 메뉴 없음).

**F11. Flutter 앱 UI 개편 (신규)**
- FR39: Flutter 앱을 웹과 동일 디자인 언어(색 토큰·카드 구성·신뢰속성/옵션·플레이스홀더)로 개편. 이미지(F7)·카드 재설계(F8) 반영. 웹 셸 재사용 불가 → 별도 위젯, 계약은 conventions.md 공유.

**F12. 실시간 문의 채팅 (FR20/21 개정)**
- FR40 (FR20 개정): 문의 채팅을 폴링 → 실시간(구독)으로 전환. 메시지 즉시 반영.
- FR41: 멱등키(클라 생성 uuid)로 재전송 중복 방지.
- FR42: 연결 끊김 시 재연결/오프라인 비차단 배너. 재연결 시 "마지막 수신 이후" 1회 보정 select로 갭 메움(유실 방지).
- FR57: 안 읽은 문의 알림 — 채팅 진입점에 안읽음 카운트 배지 + 방 목록 최신 문의 순 정렬.

**F13. AI 검색 RAG 고도화 (FR13~18 확장)**
- FR43: 라우팅 4갈래 — ① 무관/법적 → 부드러운 거절 ② 광범위/애매 → 조건 좁혀 되묻기 ③ 구조형 → Text-to-SQL ④ 조합형 → SQL+벡터 하이브리드.
- FR44: 가이드 문서 RAG 실제 활용 — 가이드 코퍼스를 필요 시 선택 참조(content 반영). 참조 판단 분기.
- FR45: 하이브리드 검색(SQL+벡터 조합) — 정형 조건+의미 조건 혼합 질의를 한 질의에서 조합. **★필수 AC(보안 블로커): HYBRID 생성 SQL도 예외 없이 sql_guard 통과 + status='on_sale' 강제(AC-SEC-1).**
- FR46: 조건 좁혀 되묻기 — 광범위 질의에 제안형 되묻기. tappable 칩 응답 병존(자유 타이핑 유지, 추가 LLM 비용 없음).
- FR47: 부드러운 거절 — 법적/무관 질의를 고정 템플릿(무상태·결정론)으로 정중히 거절, 매물 검색 유도.
- FR48: 가이드 문서 청킹·임베딩(조건부) — 현 규모(12문서) 미도입. ≥20문서/≥800토큰 시 ## 헤딩 청킹.
- FR49: 유사도 거리 컷오프 — 동떨어진 문서/매물이 근거로 첨부되지 않게(기술부채 #16).
- FR50: AI 검색 DB 접근에 커넥션 풀 + 타임아웃 + async 논블로킹(RAG 착수 전 선행).
- FR51: 관측성 — LangSmith Developer 무료 트레이싱만(env 2개, 코드 변경 0). 평가 자동화·Deployment 미도입.

**F14. 계정 역할 통합 (원본 FR1/3/6 개정 — 별도 워크스트림)**
- FR52 (FR1 개정): 가입 시 구매자/판매자 역할 선택 제거. 로그인 사용자 누구나 사고팔 수 있다.
- FR53 (FR3/6 개정): 접근 제어는 소유권 기준으로 통일(등록=누구나, 수정/삭제/구매완료=등록자만).
- FR54: 관리자(admin)는 별개로 유지(FR4). 통합 대상은 구매자·판매자 두 역할뿐.
- FR58: 비로그인 접근 정책 — 랜딩=홈(단일 공개 페이지). 비로그인도 **매물 열람(목록·상세)** 가능. 로그인 게이트는 "행동"(**AI 검색**·문의·등록·찜)에만. *(개정 2026-07-14: AI 검색은 호출당 Gemini 실비가 발생하는 **행동**이므로 로그인 필수 — 자세한 근거는 Story 8.5 및 `docs/conventions.md` §8.)*

**F15. 관리자 웹 UI 통일 (신규 — addendum FR 정식화, UI-only)**
- FR59: 관리자 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)을 신규 디자인 시스템(@theme 토큰)으로 리스킨 통일. 신규 기능·운영 배관 없음.
- FR60: 관리자 웹 PC/모바일 반응형(D5 무결성 준수, 관리자도 예외 없음).
- FR61: 회원관리 화면에 역할 통합(F14) 반영 — 무의미해진 구매자/판매자 구분 필터 정리 → admin/일반 축(=`role='admin'` 여부, **신규 컬럼 아님**).

**원본 FR 개정 요약:** FR1/3/6(역할통합 F14) · FR5(이미지 F7) · FR10/17(갤러리·AI카드 사진 F7) · FR15(RAG F13) · FR20/21(실시간 F12).

### NonFunctional Requirements

- NFR1 (개정): 문의 채팅은 실시간 갱신(폴링 아님). AI 검색 응답 수 초 유지.
- NFR3 (개정): 단일 코드 반응형 웹(m-dot 아님). Flutter는 동일 디자인 언어 별도 구현.
- NFR7 (신규): 이미지는 선택. 저비용 스토리지·서빙(썸네일·lazy-load), 목록 카드 대표 1장만 로드. 스토리지 = Supabase Storage.
- NFR8 (신규): AI 검색 경로에 커넥션 풀·타임아웃 적용(FR50).
- 유지: NFR2(RLS·SELECT 전용 안전장치·service_role 금지) · NFR4(배포) · NFR5(AI 이력 미저장) · NFR6(저비용).

### Additional Requirements

> 증분 아키텍처가 확정한 기술 요구·마이그레이션·선결 AC. 스토리 AC의 근거이며, 특히 보안·계약 AC는 해당 기능 스토리의 **차단성(blocker) AC**로 편입한다.

**마이그레이션 (additive, forward-only, RLS 동거 — 규칙 10):**

> ⚠️ **아래 0011~0018 번호는 아키텍처 논리 라벨**이다. **실제 파일 번호는 문서 상단 "마이그레이션 원장" 표가 정본**(에픽/개발 순서로 재부여 — 예: role=원장 0019, wishlists=원장 0014). 이중 번호 혼동 방지. (2026-07-15 정정: 8.5의 0011 삽입으로 시프트된 원장과 이 예시가 어긋나 있었음 — 본표 258~266행이 정본.)

- 0011 `listing_images`(id·listing_id FK ON DELETE CASCADE·storage_path·sort_order·is_cover·credit jsonb) + 비공개 버킷 + Storage RLS(본인 경로) + `ai_readonly using(true)` SELECT 정책(CR2).
- 0012 신뢰속성: `accident_status text + CHECK('무사고'·'단순교환'·'사고')` + `is_single_owner bool` + `is_non_smoker bool`(전부 nullable=미입력 제3상태, 기존 100건 NULL 유지·backfill 없음).
- 0013 role CHECK 완화(F14, buyer/seller 무의미화·admin 존치·is_admin 의존 보존).
- 0014 `listings.view_count int default 0` + `increment_listing_view()` RPC + 하드닝(AC-SEC-2).
- 0015 `wishlists(user_id, listing_id, created_at, PK(user_id,listing_id))` + 본인 RLS.
- 0016 chat 멱등키: `client_message_id` + **`UNIQUE(room_id, client_message_id)`**(CR1 — 실제 컬럼 room_id) + `ON CONFLICT DO NOTHING`.
- 0017 chat realtime: `realtime.broadcast_changes` 트리거 + `realtime.messages` RLS(AC-CHAT-3) + private 채널, 토픽 `chat:room:{room_id}`.
- 0018 `chat_room_reads(user_id, room_id, last_read_at)` — 안읽음 카운트.

**선결 기술 AC (dev 진입 전 확정 계약):**
- AC-DB-1 (최우선·RAG 선행): 커넥션 풀 롤 격리 `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`(세션 SET ROLE 금지). 검증 = 동일 물리 커넥션 재사용 2요청에서 롤 누수 없음. FR50과 동일 작업 단위. `readonly.py`의 현행 :5432 세션풀러+세션 SET ROLE 결정을 :6543 트랜잭션 풀러+SET LOCAL로 대체(I1).
- AC-SEC-1: 하이브리드 sql_guard 정비 — `validate_select_sql()`에 `<=>`·`::vector`·`embedding`·`vector` 화이트리스트(I4) + `status='on_sale'` 강제. 벡터절은 LLM이 아니라 코드가 `ORDER BY embedding <=> $1::vector LIMIT k` 바인드 파라미터로 덧붙임(I4). 회귀 3케이스(정상 통과/OR·서브쿼리 거부/status 누락 거부).
- AC-SEC-2: view_count RPC 하드닝 — `SET search_path=''` + `REVOKE EXECUTE FROM PUBLIC` + `GRANT anon,authenticated` + **`REVOKE UPDATE(view_count) FROM authenticated`**(I5, RPC 유일 쓰기통로). AI 카드 렌더 시 중복증가 금지.
- AC-CHAT-1: 멱등키(0016) — `UNIQUE(room_id, client_message_id)` + `ON CONFLICT DO NOTHING`. 기존 0003c BEFORE INSERT 트리거·0010 2000자 제약과 충돌 검증(동일 키 2회 INSERT → 행 1개·트리거 부작용 0).
- AC-CHAT-2: 재연결 갭보정 — 커서 = **`created_at >=` (strict > 아님, CR6) + `client_message_id` dedup**. Broadcast Replay(≤25/72h) 우선, 초과분 재조회. 표시 정렬 = created_at + id tiebreak.
- AC-CHAT-3: Realtime 참가자 인가 — `realtime.messages` RLS가 토픽 `chat:room:{room_id}`를 파싱해 요청자가 그 room의 buyer/seller인지 검사(0017). private 채널 + setAuth 전제. **채팅 실시간 보안 핵심.**
- AC-CONTRACT-1: ListingCard 이미지 계약 — wire = **단일 `image_url`(대표 사진의 공개 URL, nullable — ✎ 2026-07-19 Story 9.0 전엔 "서명 URL")**(CR3, 변형세트 wire 아님) + `view_count` + `image_count`(I7). null이면 "사진 준비중" 5:3 플레이스홀더. AI 응답 카드 동일 계약. api는 서명 안 하고 storage_path만 반환(CR2 — on_sale id로 listing_images 대표 1장 별도 고정쿼리). conventions.md §4 개정 선행.
- AC-DEPLOY-1: 배포 순서 db(마이그)→api(Cloud Run)→web(Vercel), nullable 하위호환, 부분배포 정합성 + 단계 실패 시 중단·역순 롤백.
- AC-F14-1: role CHECK 완화(0013)가 기존 RLS의 role 비교를 안 깨는지 grep 검증(0002 등). signup 역할선택 제거 + `0001 handle_new_user` 트리거 신규 가입 기본 role 배정(I3). ~~`/ai/search` JWT 게이트 비로그인 허용 완화(I2)~~ → **철회(2026-07-14)**: `/ai/search`는 **JWT 필수 유지**. AI 검색은 호출당 Gemini 실비가 발생하는 **행동**이며, `ai_readonly`·`sql_guard`는 DB 권한을 지키지 **API 키 지출을 지키지 않는다**. 인증은 유일한 과금 울타리이므로 제거하지 않는다(Story 8.5 참조).

**확정된 값 (사용자, 2026-07-13):**
- ~~`SIGNED_URL_TTL` = 3600s(1시간). sold 전환 후 기발급 URL 최대 1시간 유효(수용).~~ → **폐기(2026-07-19, Story 9.0)**: 공개 버킷 전환으로 서명·TTL 개념이 사라졌다. 대체 = `docs/conventions.md` §6.1(sold 후 URL 접근 명시 수용).
- 매물당 최대 10장 / 장당 5MB.
- `accident_status` 표시: `무사고`=초록 신뢰뱃지 · `단순교환`·`사고`=중립 상태칩(초록 아님).
- `accident_status` 타입 = text + CHECK(native enum 아님).
- AI 응답 계약: `{ answer, listings: ListingCard[], route: 'REJECT'|'CLARIFY'|'SQL'|'HYBRID', narrowed_by?: string[], clarify?: {question, chips[]} }`. `narrowed_by` = 저장단위(원) 정규화 술어(CR4, 예 `["price<=30000000"]`). clarify는 route='CLARIFY' 전용(CR5). AI 입력 500자 서버측 검증(422, I11).

**핵심 관심사(cross-cutting):**
- FR11(판매완료 비노출) 강제지점 3→4 확장 — 기존(RLS 0002·sql_guard·문서RAG필터) + **하이브리드 벡터 경로**(4번째). 확장 표면 = 이미지 서명URL(sold 미발급)·view_count(정렬 제외)·하이브리드 SQL(on_sale 강제)·상세 URL 직접접근 404. 앱 레벨 필터 금지.
- 4분기 라우팅 3곳 락스텝: `RouterDecision` Literal · `_fallback_route` · `_route_decision`.
- Realtime 계약 3곳 일치(트리거·RLS·클라 구독): 토픽 `chat:room:{room_id}` + INSERT 이벤트 + `broadcast_changes` 엔벨로프(클라는 `payload.record` 파싱, I10).

### UX Design Requirements

> UX 스파인(DESIGN.md 시각·EXPERIENCE.md 경험, status:final). 목업(`mockups/`)은 참고이며 **스파인이 정답**.

**디자인 토큰·시스템**
- UX-DR1: Tailwind v4 `@theme` 팔레트 토큰 중앙화(라이트/다크 hex 전부) — 표면·잉크·petrol(신뢰/구조)·amber(가격/CTA 전용)·trust-green(신뢰속성)·상태색. 색 변경 저비용. (`globals.css`)
- UX-DR2: Pretendard 폰트 일원화(한글+라틴, web=CDN/self-host·Flutter=번들). 타이포 스케일(가격 26/800 > 차량명 16/600 > meta 13/500 muted) 위계 강제.
- UX-DR3: CRAFT BAR — 겹 그림자(2단)·강한 타이포 위계·넉넉한 여백·카드 radius 16. "데모 티" 방지.

**컴포넌트 (신규/개정)**
- UX-DR4: 매물 카드(레이아웃 B) — 사진 5:3 → 신뢰속성 전용 행(초록 칩+면책 11px) → 차량명 → meta → 가격 최상위 → 희소옵션 칩(3~4, 밀도 높으면 "대표 1개+외 N"). 찜♡=사진 밖 우상단 원형. "N장"=사진 위 다크 pill 우하단.
- UX-DR5: 신뢰 뱃지(초록) — `trust-green-bg/ink` + ✓ 글리프, 무사고·1인소유·비흡연 부분표시 허용, amber 금지, 클릭 액션 없음(정보 표시 전용).
- UX-DR6: "N장" 배지 — 사진 위 다크 pill(`backdrop-filter` 구형 WebView no-op → 불투명 폴백).
- UX-DR7: "사진 준비중" 플레이스홀더 — `placeholder-bg` + 카메라 글리프 + 조용한 문구, 의도적으로 보이게(깨진 느낌 금지). 3상태(없음/처리중/실패, 처리중·실패는 업로더 세션 로컬).
- UX-DR8: AI 히어로 밴드 — 딥 petrol 그라데이션 + H1 글로우/메시 + H2 대형 차 실루엣 라인아트. 흰 검색 pill + amber "검색" 버튼 + petrol 반투명 제안칩. 헤드라인 일부 음절 amber.
- UX-DR9: 로고(방향 A "차 배지") — petrol 라운드-스퀘어 배지 + "차" + "차장님" 워드마크. (임시 lockup)
- UX-DR10: 버튼 — primary CTA = amber(검색·문의) 또는 solid petrol. **amber CTA 글자·아이콘 = 어두운 잉크(#1A1E1D), 흰색 절대 금지(테마 스왑 제외)**. 모바일 주요 버튼 ≥52px.
- UX-DR11: 칩 2종 구분 — 상시 제안칩(petrol 반투명) vs 맥락 칩(되묻기/거절, 탭 시 petrol 채움 "선택됨").
- UX-DR12: 사진 갤러리(상세) — 대표 5:3 + 썸네일 스트립 + "1/N" 카운터 + 좌우 화살표(웹)/스와이프(앱).
- UX-DR13: 사진 업로더(등록/수정) — 드롭존 + "3/10" 카운터 + "대표" 배지 + 순서변경/삭제. 업로드 실패·용량초과=인라인 오류+재시도(폼 차단 아님). 대표 삭제 시 다음 순서 자동 대표 승격.
- UX-DR14: 옵션 하이브리드 피커 — 인기옵션 8칩 + "전체 옵션 더보기" 카테고리 아코디언 체크리스트 + 옵션 검색창. 희소옵션 "희소" 태그. 선택=칩 요약+개수. (엔카 5분류: 외관/내장·안전·편의/멀티미디어·시트·기타)
- UX-DR15: 채팅 메시지 버블 — 내 메시지=petrol 채움 우측 / 상대=surface-raised 좌측. 타임스탬프·읽음·pending(반투명). 낙관적 전송 + 멱등 중복차단. 입력 2000자 상한(실시간 카운터).

**IA·내비·보이스**
- UX-DR16: 웹 상단 내비 — 로고·내 차 사기·AI로 찾기·내 차 팔기 | (비로그인) 로그인·내 차 등록 / (로그인) 찜♡·채팅🔔(안읽음 배지)·프로필▾(내 매물 관리·내 정보·로그아웃). 모바일=링크 햄버거, 찜·채팅 아이콘 상단 상시.
- UX-DR17: 앱 하단 4탭(FAB 없음) — 홈(AI검색)·찜·채팅·내차팔기. 프로필=우상단 아바타. 내 차 사기=홈 하단 스크롤/필터. `GoRouter StatefulShellRoute` + Material 3 `NavigationBar`.
- UX-DR18: 소비자 자연어 라벨(개발용어 금지) — "내 차 사기·AI로 찾기·내 차 팔기·문의하기·찜". "매물 탐색·탐색" 금지.
- UX-DR19: 마이크로카피 세트(EXPERIENCE Voice 표) — 신뢰 면책·빈 상태(찜/채팅/내매물)·404·폼 이탈 경고·검색 0건·AI 거절(고정)·AI 되묻기·오프라인 배너·에러(401/403/500) 한국어 문구 확정.

**상태·플로우·반응형**
- UX-DR20: 서피스별 상태 패턴(empty/loading/error) — 찜(sold/삭제=회색+비활성 배지+진입 차단)·내 매물 관리·목록·채팅 목록(오프라인 배너)·AI 0건·사진 없음·상세(sold 미노출·본인 소유=문의 대신 "내 매물 관리")·상세 URL 직접접근(미존재/삭제/sold=404 중립 톤)·폼(업로드 실패·이탈 경고)·전역(권한 위반 RLS 차단·401 게이트 후 복귀).
- UX-DR21: 반응형 브레이크포인트 — ≥1100px=4열 · 640~1099px=2열 · <640px=1열/캐러셀(1.2장). **D5 반응형 무결성(project-context 규칙13): 카드 내부 가로 배치 세로화 금지, 폭은 열 수로만 흡수, 줄바꿈 어긋남=금기, 관리자 포함.**
- UX-DR22: 접근성 바닥 — 대비 AA(load-bearing 조합, amber CTA 어두운 글자)·비색 신호 중복·터치타깃 ≥44px(주요 ≥52)·포커스 트랩(모달/바텀시트/드롭다운/게이트)·한국어 스크린리더 라벨(아이콘 버튼·안읽음·aria-pressed/selected)·AI 대화 aria-live·reduced-motion.
- UX-DR23: 인터랙션 프리미티브 — 찜 낙관적 토글(로그인 게이트·실패 롤백)·되묻기 칩 select(상한 2~3턴, 초과 시 결과 강제 제시)·sticky 상세 문의 CTA(모바일 하단 고정 바)·optimistic send(멱등)·AI 입력 500자·폼 이탈 가드(dirty 감지).
- UX-DR24: 상세 페이지 섹션 순서 = **신뢰정보 → 차량정보 → 옵션 → 판매자정보**(D9, `detail-1.html`은 구버전 순서이며 스파인이 정답).

**관리자 (UI-only 스코프 추가, 사용자 확정 2026-07-12)**
- UX-DR25: 관리자 웹 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)을 신규 디자인 시스템으로 통일 + PC/모바일 브라우저 반응형(D5 무결성 준수). **신규 기능·개발/운영 배관 없음**(다음 증분). 목업=`admin-mockups-2.html`. F14 반영(회원관리 구매자/판매자 필터 정리).

### FR Coverage Map

> 증분 FR26~61 + 원본 개정분(FR1/3/5/6/10/15/17/20/21)이 전부 에픽에 매핑됨(누락 0). 경계에 걸친 FR(32·36·58·ListingCard 계약)은 위 **FR 소유권 매트릭스**에서 정책소유·소비를 분리했다.

- FR26 → Epic 9 (사진 업로드·다중·5:3·nullable)
- FR27 → Epic 9 ("사진 준비중" 플레이스홀더)
- FR28 (FR10 개정) → Epic 9 (상세 갤러리·목록/AI 대표사진)
- FR29 → Epic 9 ("N장" 배지)
- FR30 → Epic 10 (신뢰속성 분리·면책 라벨)
- FR31 → Epic 10 (옵션 희소도 우선·통제어휘·#11)
- FR32 → Epic 9 (카드 정보 위계·가격 대형·찜 위치·compare 제외) *(뱃지·옵션 콘텐츠 소비=Epic 10)*
- FR33 → Epic 11 (AI 히어로 랜딩)
- FR34 → Epic 11 (인기 view_count/최신 그리드·전체보기)
- FR35 → Epic 11 (차종 빠른 진입 칩)
- FR36 → Epic 8 (반응형 프리미티브·D5 규칙, 정책소유) *(각 UI 에픽 DoD 내장 + Epic 11 뷰포트 감사)*
- FR37 → Epic 8 (@theme 디자인 토큰 중앙화)
- FR38 → Epic 11 (내비·IA 도달성)
- FR39 → Epic 16 (Flutter 앱 개편)
- FR40 (FR20 개정) → Epic 12 (실시간 전환)
- FR41 → Epic 12 (멱등키)
- FR42 → Epic 12 (재연결 배너·갭보정)
- FR43 → Epic 13 (4분기 라우팅)
- FR44 → Epic 13 (가이드 content 활용)
- FR45 → Epic 13 (하이브리드 검색·AC-SEC-1)
- FR46 → Epic 13 (되묻기 CLARIFY)
- FR47 → Epic 13 (부드러운 거절)
- FR48 → Epic 13 (청킹 — 조건부, 현재 미도입)
- FR49 → Epic 13 (거리 컷오프)
- FR50 → Epic 8 (커넥션 풀·AC-DB-1, 접근제어 토대로 격상) *(RAG 하이브리드는 Epic 13)*
- FR51 → Epic 13 (LangSmith 트레이싱)
- FR52 (FR1 개정) → Epic 14 (역할선택 제거)
- FR53 (FR3/6 개정) → Epic 14 (소유권 기반 접근제어)
- FR54 → Epic 14 (admin 존치)
- FR55 → Epic 10 (찜)
- FR56 → Epic 10 (판매자 정보)
- FR57 → Epic 12 (안읽음 배지·방 목록 정렬)
- FR58 → Epic 8 (비로그인 anon **열람** 토대·게이트는 행동에만[AI 검색 포함], 정책소유) *(Epic 9~14 진입점이 준수)*
- FR59 → Epic 15 (관리자 6화면 디자인 통일)
- FR60 → Epic 15 (관리자 반응형)
- FR61 → Epic 15 (회원관리 역할통합 반영)
- 원본 FR5 개정 → Epic 9 · FR10 개정 → Epic 9 · FR15 개정 → Epic 13 · FR17 개정 → Epic 9 · FR20/21 → Epic 12 · FR1/3/6 → Epic 14

## FR 소유권 매트릭스 (경계에 걸친 FR — Mary 검증 반영)

> "언급"과 "소유"를 구분한다. 두 에픽에 걸친 FR은 **정책 소유 1 + 소비 N**으로 못박아 "아무도 안 하는 틈"을 막는다.

| FR / 계약 | 정책 소유 에픽 | 소비(준수) 에픽 |
|---|---|---|
| FR32 카드 정보 위계·뱃지 슬롯 | **Epic 9** (카드 레이아웃 B 확정) | Epic 10(뱃지·옵션 콘텐츠를 슬롯에 채움) |
| FR36 반응형 | **Epic 8** (반응형 프리미티브·D5 무결성 규칙) | 전 UI 에픽 스토리 DoD 내장 + Epic 11 뷰포트 E2E 감사 + Epic 15 관리자 |
| FR58 비로그인 접근 | **Epic 8** (anon **열람** 토대·"게이트는 행동에만" 계약 — AI 검색=행동) | Epic 9·10·11·13·14 진입점이 이 계약 준수 |
| ListingCard 계약(§4) | **Epic 8 (8.3)** — 전 필드 nullable **1회 선점**(image·view_count·image_count·신뢰속성) | 소비=값만 채움: Epic 9(image)·10(신뢰속성)·11(view_count)·16(Flutter). **찜은 wire 필드 아님**(사용자별 오버레이). 값 채울 때 web·api·app **동시 갱신** |

## 지표 추적 매트릭스 (SM/CM/G → 검증 에픽·스토리 — 빈칸=증발)

> 성공·카운터·게이트 지표는 "기능 FR"이 아니라 "검증 FR"이다. 각 지표를 **검증 스토리로 착지**시킨다(스토리 단계에서 스토리 ID 확정).

| 지표 | 검증 스토리 (ID 확정) |
|---|---|
| SM-A 사진 표시·100건 안깨짐 | **9.4~9.6**(표시) + **9.7**(안깨짐=G3) |
| SM-B 랜딩·반응형 재배치 | **11.5** |
| SM-C 신뢰속성(면책)·희소옵션 구분 | **10.2**(면책·뱃지) + **10.3**(희소옵션 우선노출) + **10.7**(통합 검증) |
| SM-D Flutter 동일 디자인 언어 | **16.6** |
| SM-E 실시간 채팅 송수신·재연결 | **12.6**(실시간 왕복·재연결 수동 검증) |
| SM-F RAG 시연 3종 유지 | **13.8** exit-gate |
| SM-G RAG 신규 분기 동작(하이브리드·되묻기·거절) | **13.3**(하이브리드)·**13.4**(되묻기)·**13.8** exit-gate |
| CM-A 기존 100건 하위호환 | **9.7**(=G3) |
| CM-B FR11 sold 비노출·채팅무결성·AI안전 유지 | **9.2/9.6**(이미지 sold)·**12.3**(채팅 무결성)·**13.8**(AI) |
| CM-C 신뢰속성 오도 금지·면책 필수 | **10.2**(면책 DoD 강제) |
| G1 CLARIFY 과다발동율 | **13.4**(라벨 질의셋 baseline) |
| G2 RAG 회귀 게이트 | **13.1**(baseline) + 매 RAG 스토리 재실행 + **13.8** exit-gate |
| G3 이미지 하위호환 | **9.7** |

## 마이그레이션 원장 (정본 — 현 에픽 순서 = 번호 순서, item 12)

> ~~forward-only 번호순 마이그레이션은 번호순=적용순=개발순이 강제다.~~ **⚠️ 이 표현은 철회됐다(Story 8.6, 2026-07-14 party-mode + 도커 실측).** 실측해 보니 **이 전제는 애초에 거짓이었다** — 원격 적용 순서는 번호순이 아니었고(0006→0004→0003→0005), `0004`가 뒷번호 `0006`을 가정한 채 1년 가까이 돌고 있었다. 정확한 불변식은 이것이다(`docs/conventions.md` §9.1이 정본):
>
> > **각 마이그는 자기가 필요로 하는 선행 상태를 스스로 만들거나(멱등 가드), 번호가 더 작은 마이그에만 의존한다. 원격 적용 이력의 순서는 상관없다.**
>
> 즉 **번호 갭은 무죄, 역방향 의존만 유죄**다. (파일 번호의 밀집은 별개 규칙 — out-of-order 삽입을 막는 번호 관리 장치이지 의존성 규칙이 아니다. §9.2 참조.)
>
> 아키텍처의 `0011~0018`은 논리 라벨이었고, **아래가 실제 파일 번호의 정본**(현 에픽/스토리 순서로 재부여). 기존 `0001~0010`은 원본. 각 마이그는 self-contained(8.6 CI 체크 통과).

| 파일 번호 | 내용 | 소유 스토리 | (아키텍처 논리 라벨) |
|---|---|---|---|
| 0011 | listings anon SELECT(on_sale, FR58 비로그인 열람) | **8.5** | (신규 — FR58 접근 토대) |
| 0012 | listing_images + 비공개 버킷·Storage RLS | **9.1** | 0011 |
| 0013 | 신뢰속성(accident_status text+CHECK·is_single_owner·is_non_smoker) | **10.1** | 0012 |
| 0014 | wishlists(찜) | **10.5** | 0015 |
| 0015 | view_count + increment_listing_view() RPC 하드닝 | **11.1** | 0014 |
| 0016 | chat 멱등키(client_message_id + UNIQUE(room_id,…)) | **12.1** | 0016 |
| 0017 | chat realtime broadcast 트리거 + realtime.messages RLS | **12.2** | 0017 |
| 0018 | chat_room_reads(안읽음) | **12.5** | 0018 |
| 0019 | role CHECK 완화(admin 존치) | **14.1** | 0013 |

> **📌 8.5 삽입(2026-07-14):** FR58 비로그인 열람을 위한 `listings` anon SELECT 마이그가 `0011`로 삽입되어 기존 0011~0018이 **0012~0019로 +1 시프트**됨(사용자 승인). forward-only라 "0011 앞" 삽입 불가 → 개발 순서(8.5가 9.1보다 선행)대로 재부여. 아래 각 스토리의 "Given 마이그레이션 00NN"·"기반 스토리" 번호는 이 표를 정본으로 갱신됨.

## Epic List

> **번호는 원본 Epic 1~7 다음인 Epic 8부터 (총 9개, Epic 8~16).** party-mode 독립검증(Winston·Amelia·Sally·Mary) 반영본. 각 에픽은 독립적으로 사용자 가치를 전달하되, **위험한 기초(접근제어·배포순서)는 별도 기반 에픽(Epic 8)으로 격상**(사용자 확정) — 뒤 에픽이 딛고 설 땅을 먼저 깐다. 나머지 마이그레이션·계약은 해당 기능 에픽의 첫 스토리로 접는다.
>
> **⚠️ 마이그레이션 번호 (Amelia):** 아키텍처의 `0011~0018`은 **논리 그룹핑 라벨**이다. forward-only 번호순 마이그레이션은 **번호순=적용순=개발순**이 강제이므로, **실제 파일 번호는 sprint/authoring 시점의 개발 순서로 순차 재부여**한다(내용이 계약, 번호는 값싸다). 예: Epic 13(역할)이 Epic 11(채팅) 뒤면 role 마이그는 0016~0018보다 **뒤 번호**. 각 에픽 첫 스토리 AC에 "이 마이그는 self-contained(앞선 마이그의 특정 상태를 가정하지 않음)"를 검증 항목으로 박는다.
>
> **⚠️ 반응형은 별도 에픽이 아니다 (Sally·Mary):** FR36 반응형·D5 무결성은 **각 UI 컴포넌트 스토리의 완료 기준(DoD)에 내장**한다("나중에 몰아서 반응형"=안티패턴). Epic 11이 뷰포트 E2E **감사**만 소유.

### Epic 8: 증분 기반 게이트 (전제조건 — 접근제어·디자인·계약·배포)
모든 후속 에픽이 딛고 서는 **땅을 먼저 깐다.** 사용자에게 바로 보이는 기능은 아니지만, 이게 없으면 Epic 9~16이 임시 코드 위에 쌓여 되돌려야 할 부채가 된다(사용자 확정으로 별도 에픽 격상). 4개 기둥: ① **디자인 시스템 파운데이션**(@theme 토큰·Pretendard·CRAFT BAR·반응형 프리미티브+D5 규칙·빈/로딩/에러 **상태 프리미티브**·**접근성 기준**) ② **ListingCard 계약 셸**(image_url nullable·view_count·image_count 자리, conventions §4) ③ **접근제어 토대**(AC-DB-1 커넥션 풀 롤 격리 + FR50 · FR58 비로그인 anon 읽기·게이트는 행동에만) ④ **배포 순서 게이트**(AC-DEPLOY-1).
**FRs covered:** FR37, FR50, FR58, (기반) FR36 · **계약/AC:** AC-CONTRACT-1·AC-DB-1·AC-DEPLOY-1 · **UX:** UX-DR1,2,3,21,22
**핵심:** AC-DB-1은 기존 Epic 4 AI API 커넥션 레이어를 수술 → RAG 코드와 **독립적으로 조기 디리스크**(red-green 가능). 여기서 롤 격리를 안 세우면 Epic 12 하이브리드 SQL이 롤 누수·status 우회 위험.

### Epic 9: 매물 이미지
매물에 **사진이 생긴다** — 판매자는 여러 장 올리고, 구매자는 목록·상세 갤러리·AI 응답 카드에서 대표사진을 본다. 사진 없는 기존 100건은 "사진 준비중"으로 안 깨진다(CM-A/G3). 카드 레이아웃 B를 확정하고, **상세 페이지 골격(신뢰→차량→옵션→판매자 빈 섹션)을 먼저 세워** Epic 10이 채우게 한다(Sally).
**FRs covered:** FR26, FR27, FR28, FR29, FR32 · (개정) FR5, FR10, FR17
**기반 스토리:** 0012 listing_images(비공개 버킷·Storage RLS·ai_readonly SELECT) + 서명 URL 헬퍼(아티팩트 범용, TTL 3600) · api storage_path만 반환(CR2)
**검증:** G3 이미지 하위호환(image_url NULL→플레이스홀더·구행 무변경) · "api는 서명 URL 반환 안 함" contract test
**Non-goals:** 이미지 모더레이션 · 비교표(compare) · 옵션 금전가치 환산 (범위 밖)

### Epic 10: 신뢰속성·옵션·찜·판매자 정보
매물 카드/상세가 **신뢰도 있게** 읽힌다 — 무사고·1인소유·비흡연 신뢰속성(면책 라벨 필수·CM-C), 희소 옵션 우선 노출, 찜(관심 매물 모으기·재방문), 판매자 정보 섹션. Epic 9가 세운 상세 골격의 각 섹션을 채운다.
**FRs covered:** FR30, FR31, FR55, FR56
**기반 스토리:** 0013 신뢰속성(accident_status text+CHECK·is_single_owner·is_non_smoker, nullable 제3상태) · 0014 wishlists
**검증:** CM-C 면책 라벨이 신뢰 뱃지와 **한 몸으로** 렌더(뱃지 컴포넌트 DoD에 구조적 강제, Sally)
**Non-goals:** 후기·평판·별점 · 응답률·인증배지 · 옵션 정규화 테이블 (범위 밖 — 자기신고+면책 유지)

### Epic 11: AI 히어로 랜딩 + 내비
서비스 진입점이 **AI 검색 히어로 랜딩**이 된다 — 딥 petrol 히어로 + 인기(view_count)/최신 2단 그리드 + 차종 칩. 상단 내비를 소비자 자연어로 재구성한다(Epic 9/10의 완성된 카드를 재사용). 반응형 **뷰포트 E2E 감사**를 여기서 소유(최대 반응형 표면).
**FRs covered:** FR33, FR34, FR35, FR38 · (감사) FR36
**기반 스토리:** 0015 view_count + increment_listing_view() RPC 하드닝(AC-SEC-2)
**참고:** 내비를 **role-aware 훅 자리**로 선설계(Epic 13이 역할 분기로 재작성하지 않도록, Amelia). 랜딩은 필터 상태·URL 쿼리를 소유하지 않음(전체 목록 단일 소유자=/search).

### Epic 12: 실시간 문의 채팅
문의 채팅이 **폴링 → 실시간**으로 바뀐다 — 메시지 즉시 반영, 재연결 배너(유실 없는 갭보정), 멱등키 중복 방지, 안읽음 배지. 판매자가 문의를 놓치지 않는다. 기존 채팅 무결성 3중 장치(RLS·트리거·CHECK)는 보존한다(CM-B).
**FRs covered:** FR40, FR41, FR42, FR57 · (개정) FR20, FR21
**기반 스토리:** 멱등키(UNIQUE(room_id, client_message_id)·AC-CHAT-1) · realtime broadcast + RLS 참가자 인가(AC-CHAT-3) · chat_room_reads(안읽음)
**Non-goals:** 신고·차단 · 브라우저/모바일 푸시 알림 · 타이핑 인디케이터 (다음 증분)

### Epic 13: AI 검색 RAG 고도화
AI 검색이 **상용 수준**으로 올라간다 — 4분기 라우팅(거절·되묻기·구조형·하이브리드), SQL+벡터 하이브리드, 가이드 문서 실제 활용(b 질의확장), 거리 컷오프, LangSmith 관측성. *(커넥션 풀 롤 격리 AC-DB-1은 Epic 8에서 선행 완료 → 여기선 그 위에 하이브리드를 얹는다.)*
**FRs covered:** FR43, FR44, FR45, FR46, FR47, FR48, FR49, FR51 · (개정) FR15
**첫 스토리:** sql_guard 하이브리드 정비(AC-SEC-1: `<=>`·`::vector`·embedding 화이트리스트 + status='on_sale' 강제) · **G2 baseline 하니스 심기**(Phase B 재사용)
**검증:** SM-F/SM-G(3종 유지+신규 분기 동작) exit-gate · G1(CLARIFY 과다발동율) 되묻기 스토리 AC · G2(회귀) 매 RAG 스토리 재실행+exit-gate
**Non-goals:** 청킹(FR48 조건부 — ≥20문서/≥800토큰 시에만) · 평가 자동화·LangSmith Deployment · interrupt()/체크포인터 (범위 밖)

### Epic 14: 계정 역할 통합 나머지 (별도 워크스트림)
가입 시 **구매자/판매자 역할 선택이 사라지고**, 누구나 사고팔 수 있다(소유권 기반 접근제어). **인증·RLS를 건드리므로 UI/이미지 커밋과 분리 관리.** *(비로그인 열람·AI검색 토대 FR58은 Epic 8에서 선행 → 여기선 역할 병합 본체.)*
**FRs covered:** FR52, FR53, FR54 · (개정) FR1, FR3, FR6
**기반 스토리:** role CHECK 완화(admin 존치·AC-F14-1 grep 검증) · signup 역할선택 제거 + 트리거 기본 role(I3) · 판매 게이트 requireRole→requireUser · 관리자 회원관리 필터 협조(Epic 15와 연동)

### Epic 15: 관리자 웹 UI 통일 (UI-only)
관리자 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)을 **신규 디자인 시스템으로 통일 + PC/모바일 반응형**(D5 무결성, 관리자도 예외 없음). **신규 기능·운영 배관 없음.** *(PRD 역반영 완료 — addendum FR59~61 정식화, Mary 요구 반영.)*
**FRs covered:** FR59, FR60, FR61 · F14 반영(FR61 회원 필터)
**Non-goals:** 관리자 신규 기능 · 대시보드 통계 고도화 · 스토리지 고아 청소 · 신고/차단 큐 (다음 증분)

### Epic 16: Flutter 앱 증분 반영
Flutter 앱이 **웹과 동일 디자인 언어**로 개편된다 — 이미지·카드 재설계·신뢰속성·찜·실시간 채팅·4분기 AI·하단 4탭. 웹 셸 재사용 불가라 별도 위젯이되, 계약(색·비율·필드)은 conventions.md 공유. 웹 기능이 안정된 뒤 미러링.
**FRs covered:** FR39 · (재현) FR26~58 중 앱 사용자 여정 — 관리자 제외
**Non-goals:** 브라우저/모바일 푸시 · 안드로이드 릴리스 서명(기술부채 #2, 별도 사용자 액션) · 관리자 앱 이월

---

## Epic 8: 증분 기반 게이트 (전제조건 — 접근제어·디자인·계약·배포)

모든 후속 에픽(9~16)이 딛고 서는 땅을 먼저 깐다. 디자인 시스템·상태·접근성 프리미티브, ListingCard 공유 계약 셸, DB 접근제어 토대(롤 격리·비로그인), 배포 순서 게이트. 사용자에게 바로 보이는 기능은 아니지만, 이게 없으면 뒤 에픽이 임시 코드 위에 쌓여 되돌려야 할 부채가 된다.

### Story 8.1: 디자인 시스템 토큰 파운데이션

As a 차장님 서비스 사용자,
I want 전 화면이 일관된 페트롤+앰버 디자인 언어(색·타이포·그림자)로 보이길,
So that 데모 티 안 나고 믿음직한 제품으로 느껴진다.

**Acceptance Criteria:**

**Given** Tailwind v4(@theme, CSS-first) 환경
**When** DESIGN.md frontmatter의 색 토큰을 정의하면
**Then** 표면·잉크·brand-petrol·accent-amber·trust-green·상태색이 **라이트/다크 양쪽** CSS 변수로 중앙화되고, 색 변경이 한 곳에서 이뤄진다(UX-DR1)
**And** Pretendard가 web(CDN 또는 self-host)에 로드되고 타이포 스케일(display/section/card-title/price/body/meta/caption)이 토큰화된다(UX-DR2)
**And** amber CTA 글자·아이콘은 어두운 잉크(#1A1E1D)로 **고정**(테마 자동 스왑 제외)되어 대비 8.02:1을 유지한다
**And** price-emphasis·trust-green-ink·ink-muted 등 load-bearing 대비 조합이 WCAG AA를 충족한다(DESIGN.md 조정치)
**And** CRAFT BAR(겹 그림자·카드 radius 16·4pt 여백 리듬)가 재사용 토큰/유틸로 확립된다(UX-DR3)
**And** 로고 lockup(방향 A "차 배지" — petrol 라운드-스퀘어 배지 + "차" + "차장님" 워드마크)이 토큰 기반 컴포넌트로 구현된다(UX-DR9, 내비·앱 아이콘 겸용). *실제 아트워크는 추후 제작 — 현재 lockup 임시 사용.*

### Story 8.2: UI 프리미티브 — 반응형·상태·접근성

As a 사용자,
I want 데스크톱·모바일 어디서든 화면이 안 깨지고 로딩·빈·에러 상태가 명확하길,
So that 어떤 상황에서도 서비스를 신뢰하고 쓸 수 있다.

**Acceptance Criteria:**

**Given** 단일 코드 반응형 프리미티브
**When** 뷰포트 폭이 바뀌면
**Then** 그리드가 ≥1100px=4열 · 640~1099px=2열 · <640px=1열/모바일 캐러셀(1.2장)로 **열 수만** 바꾸고, 컴포넌트 내부 가로 배치(신뢰속성 행·meta·옵션 칩·버튼 라벨)를 **세로화하지 않는다**(D5 무결성, 공간 부족은 truncate·"외 N"·열 축소로 처리)(FR36, UX-DR21)
**And** 공용 상태 프리미티브(스켈레톤 로딩·빈 상태·에러 폴백)가 정의되어 카드·목록·상세·랜딩·채팅이 상속한다
**And** 접근성 기준이 프리미티브에 내장된다 — 비색 신호 중복(색+아이콘/텍스트), 터치타깃 ≥44px(주요 버튼 ≥52px), 포커스링=brand-petrol, 포커스 트랩(모달·바텀시트·드롭다운·게이트), 한국어 스크린리더 라벨, reduced-motion(UX-DR22)
**And** 대표 뷰포트(데스크톱·태블릿·모바일)에서 D5 무결성 위반(줄바꿈 어긋남·2줄로 밀리는 버튼·라벨 어긋남)이 **없음**을 확인한다

### Story 8.3: ListingCard 공유 계약 셸 개정

As a web·app·api 개발자,
I want ListingCard 계약에 이미지·조회수 필드 자리를 먼저 확정하길,
So that 이후 에픽들이 계약 drift 없이 같은 데이터 셰이프를 공유한다.

**Acceptance Criteria:**

**Given** docs/conventions.md §4(ListingCard 계약, 단일 출처)
**When** 계약을 개정하면
**Then** ListingCard 계약에 이번 증분의 **모든 신규 필드 자리를 한 번에** nullable로 선점한다 — `image_url`(대표 서명 URL) · `view_count` · `image_count`(CR3·I7) + **신뢰속성** `accident_status`·`is_single_owner`·`is_non_smoker`(Epic 10이 값만 채움) — 전부 snake_case wire로 명문화한다(AC-CONTRACT-1). **계약은 여기서 1회 확정하고 뒤 에픽은 값만 채운다**(2회 개정 방지, Winston)
**And** `image_url`이 null이면 클라가 "사진 준비중" 5:3 플레이스홀더를 렌더함이 **계약의 일부**로 규정된다(변형 세트는 클라 렌더 파생이지 wire 계약 아님)
**And** 찜(wishlist) 상태는 ListingCard **wire 필드가 아니다** — "내가 찜했는지"는 사용자별 오버레이라 별도 조회/조인으로 처리한다(계약 오염 방지, Epic 10.5)
**And** AI 응답 카드도 동일 ListingCard 계약을 공유함이 문서화된다
**And** 소비할 이미지·신뢰속성 데이터가 아직 없어도 web/app 매퍼가 nullable 신규 필드로 컴파일·렌더된다(기존 100건 하위호환)
**And** "계약에 필드를 추가·변경할 땐 web·api·app 3소비처를 동시 갱신"이 크로스-에픽 체크리스트로 박힌다(Winston)

### Story 8.4: AC-DB-1 커넥션 풀 롤 격리 + 커넥션 풀(FR50)

As a AI 검색 사용자,
I want AI가 DB를 읽을 때 안전하고 빠르게 처리되길,
So that 부하 상황에서도 권한 누수 없이 안정적으로 검색된다.

**Acceptance Criteria:**

**Given** 트랜잭션 풀러(:6543)를 통한 AI 읽기 경로
**When** AI 검색이 DB를 읽으면
**Then** 매 쿼리를 `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;`으로 감싸 실행하고 **세션 레벨 `SET ROLE`을 쓰지 않는다**(AC-DB-1)
**And** 동일 물리 커넥션을 재사용하는 연속/동시 2요청에서 **2번째 요청의 실행 롤이 직전 ai_readonly로 새지 않음**을 증명하는 테스트가 통과한다(red→green)
**And** 커넥션 풀 + `connect_timeout` + async 논블로킹이 도입된다(FR50, NFR8)
**And** `readonly.py`의 기존 :5432 세션풀러+세션 SET ROLE 결정이 이 방식으로 대체되고 주석이 갱신된다(I1)
**And** 이 변경이 기존 Epic 4 AI 검색을 깨지 않음을 회귀로 확인한다(RAG 신규 로직과 독립 — 조기 디리스크)

### Story 8.5: FR58 비로그인 열람 토대

As a 비로그인 방문자,
I want 로그인 없이 매물을 둘러보길,
So that 가입 전에 "여기 살 만한 차가 있는지" 확인하고 결정할 수 있다.

> **개정 이력 (2026-07-14, 코드리뷰 + party-mode)**: 최초 AC는 `/ai/search`의 JWT 게이트 **완화**를 요구했으나 **철회**됐다. 근거: AI 검색 1회 = Gemini 호출 3회 내외 = **실제 과금**이며, JWT는 호출자를 식별하는 **유일한 수단**이자 곧 유일한 과금 울타리였다. `ai_readonly`·`sql_guard`는 DB 권한을 지키지 **API 키 지출을 지키지 않는다**(I2의 안전 검토가 비용 축을 누락). 대안이었던 익명 N회 제한은 Cloud Run 다중 인스턴스에서 카운터 공유가 불가해 표시 숫자를 보장 못 하므로 폐기(Redis+VPC 도입은 과설계 — A2). **FR58 원문의 "매물 열람과 AI 검색"은 and로 이어진 두 항목이라 분해 가능하며, 앞 절(열람)만 남긴다** — FR58의 정신(랜딩 공개·열람 자유)은 100% 유지된다. PRD 각주 *"AI 검색 Gemini 비용이 문제되면 그 전송 버튼에 로그인 게이트/rate-limit을 붙여 쉽게 조인다"* 가 예고한 조정이며, 그중 **더 싸고 확실한 쪽(로그인 게이트)** 을 택한 것이다.

**Acceptance Criteria:**

**Given** 비로그인(anon) 사용자
**When** 매물 목록·상세에 접근하면
**Then** 열람이 허용된다(FR58 — 매물 RLS anon SELECT 경로 확인, sold 비노출 FR11은 유지)
**And** anon SELECT는 **행뿐 아니라 컬럼도 스코프**된다 — RLS엔 컬럼 차원이 없으므로 `grant select (필요 컬럼)`으로 `embedding` 등 비노출 컬럼을 차단한다
**And** `/ai/search`는 **JWT 필수를 유지**한다(비용 발생 = 행동, AC-F14-1 개정 참조). `/ai`는 `proxy.ts` 보호 경로에 남는다
**And** 로그인 게이트는 **"행동"(AI 검색·문의·매물 등록·찜)에만** 적용됨이 계약으로 확립되고, 게이트 통과 후 **원위치 복귀**가 규정된다
**And** 역할 통합 본체(FR52~54, signup·트리거·role CHECK)는 이 스토리 범위 밖(Epic 14)이며 여기선 열람 토대만 다룬다(FR58 정책 소유 = Epic 8)

### Story 8.6: AC-DEPLOY-1 배포 순서 + 마이그레이션 게이트

As a 개발·배포 담당,
I want 증분 배포 순서와 마이그레이션 번호 규칙을 먼저 못박길,
So that db·api·web·app 분리 배포에서 계약이 깨지거나 롤백이 꼬이지 않는다.

**Acceptance Criteria:**

**Given** db·api·web·app 3~4개 배포 타깃
**When** 증분을 배포하면
**Then** 배포 순서 **db(마이그)→api(Cloud Run)→web(Vercel)→app(수동)** 와 nullable 하위호환·부분배포(db+api 신, web 구) 정합성·단계 실패 시 역순 롤백을 담은 **배포 런북(runbook) 문서**가 산출된다(AC-DEPLOY-1)
**And** **마이그 순서 CI 체크(실행 가능한 스크립트)** 가 산출된다 — fresh DB에 0001부터 번호순 전체 적용이 성공하고, 번호 공백(gap)·out-of-order·비-self-contained(앞 마이그 상태 가정)를 **실패로 잡는다**(Amelia). 각 에픽 첫 마이그 스토리는 이 체크를 통과해야 한다
**And** 마이그 번호는 아래 **"마이그레이션 원장"** 표(문서 상단)가 정본이며, 현 에픽 순서대로 0011~0019를 확정한다(0011=8.5 listings anon SELECT 삽입으로 +1 시프트됨. 아키텍처의 0011~0018은 논리 라벨이었고 실제 번호는 이 원장이 우선)

---

## Epic 9: 매물 이미지

매물에 사진이 생긴다 — 판매자는 여러 장 올리고, 구매자는 목록·상세 갤러리·AI 응답 카드에서 대표사진을 본다. 사진 없는 기존 100건은 "사진 준비중"으로 안 깨진다(CM-A/G3). 카드 레이아웃 B를 확정하고, 상세 페이지 골격(신뢰→차량→옵션→판매자 빈 섹션)을 먼저 세워 Epic 10이 채우게 한다.

### Story 9.1: listing_images 스키마 + 비공개 버킷 + Storage RLS

> ✎ **정정 (2026-07-19, Story 9.0):** 아래의 "비공개 버킷 + 서명 URL(TTL 3600)" 전제는 **ADR-IMG-02(공개 버킷 + 고정 URL)로 대체**됐다. 현재 계약은 `docs/conventions.md` §6.1·§10. 아래 원문은 당시 계획의 기록으로 남긴다.


As a 판매자,
I want 내 매물 사진을 안전하게 저장할 공간이 마련되길,
So that 사진을 올리면 나만 관리하고 구매자에게만 노출된다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0012**(원장 정본, 내용 = listing_images)
**When** 적용하면
**Then** `listing_images(id, listing_id FK ON DELETE CASCADE, storage_path, sort_order, is_cover bool, credit jsonb)` 테이블이 생성되고 **self-contained**(앞선 마이그의 특정 상태를 가정하지 않음)하다
**And** 비공개 Storage 버킷이 생성되고, Storage 경로 규칙 = `{auth.uid()}/{listing_id}/{filename}`(첫 세그먼트=소유자)이다. **신규 등록은 매물 행을 먼저 insert해 listing_id를 얻은 뒤** 그 경로로 업로드한다(A2 단순, 스테이징 경로 회피)
**And** `storage.objects`에 **두 RLS 정책**이 동거한다(규칙10, service_role 금지·규칙6): ① **쓰기** = 본인 경로(첫 세그먼트=auth.uid())만 insert/update/delete · ② **읽기(SELECT)** = anon/authenticated가 **서명 URL을 발급하려면 반드시 필요** — 해당 이미지의 매물이 `status='on_sale'`이거나 본인 소유일 때만 SELECT 허용(FR11 sold 비노출을 스토리지 레이어에서도 강제 + FR58 비로그인 열람 가능). *이 정책이 없으면 anon 서명 시 사진이 미표시된다.*
**And** `listing_images` **테이블** SELECT는 listings 정책과 연동(sold 숨김 상속)되고 `ai_readonly using(true)` SELECT 정책이 추가된다(CR2)
**And** 매물당 최대 10장 / 장당 5MB 상한이 업로드 경로 제약으로 반영된다

**Given** 이 스토리가 만드는 `listing_images.listing_id FK`는 **`listings`의 첫 자식 테이블**이다 (기술부채 #27의 트리거가 바로 여기서 발동한다)
**When** 시드 재실행 전략을 판단하면
**Then** 현재 `supabase/seed.sql`이 **시드 매물을 delete 후 새 uuid로 재삽입**한다는 사실을 확인하고, 그 결과를 명시한다 — `ON DELETE CASCADE`라 **delete는 통과하지만 업로드한 이미지 행이 조용히 사라진다**(에러 0건 = 알아챌 방법 없음)
**And** 전략을 하나 택해 스토리 기록에 남긴다: **(a) 고정 id 사용**(시드 매물 uuid를 고정해 delete-재삽입 자체를 없앰) 또는 **(b) 자식 정리 순서 명시**(이미지 → 매물 순) 또는 **(c) 이번 증분에선 무해함을 근거와 함께 확인하고 이월**
**And** ⚠️ **Epic 10.5 `wishlists`가 두 번째 자식**이다. `ON DELETE CASCADE`가 아니면 **delete가 아예 막힌다** — 지금 (c)를 택하면 그때 다시 온다. 판단 시 함께 본다.
**And** 결정을 `docs/tech-debt.md` #27에 반영한다(해소면 닫고, 이월이면 트리거를 갱신한다)

**Given** 마이그레이션에 **테이블 GRANT를 명시하려는 경우**(기술부채 #18 — 이 에픽의 첫 마이그가 그 축을 건드린다)
**When** `grant select ... to authenticated` 같은 문장을 추가하려면
**Then** `docs/conventions.md` **§9.3 (a′)** 를 따른다 — **승인 대기 없이 진행하되**, 추가 **전에** 원격 현재 권한을 실제로 떠서(`information_schema.role_table_grants` / `has_table_privilege`) **델타 0임을 확인하고 그 출력을 스토리 기록에 남긴다**
**And** 델타가 0이 아니거나 **넓히는 방향**(새 롤·새 컬럼 anon 노출·`to public`)이면 **멈추고 사용자 승인**을 받는다

### Story 9.2: 서명 URL 헬퍼 (아티팩트 범용)

> ✎ **정정 (2026-07-19, Story 9.0):** 아래의 "비공개 버킷 + 서명 URL(TTL 3600)" 전제는 **ADR-IMG-02(공개 버킷 + 고정 URL)로 대체**됐다. 현재 계약은 `docs/conventions.md` §6.1·§10. 아래 원문은 당시 계획의 기록으로 남긴다.


As a web·app 개발자,
I want 비공개 사진을 안전하게 보여줄 서명 URL 발급을 한 곳에서 관리하길,
So that 만료·배치 발급이 일관되고 향후 다른 아티팩트도 배관 재작업 없이 재사용한다.

**Acceptance Criteria:**

**Given** 비공개 버킷
**When** 대표/갤러리 이미지를 표시하려 서명 URL을 발급하면
**Then** 서명은 **각 소비 클라이언트/서버가** 하고, **금지 대상은 api(FastAPI)뿐이다** — web=서버 컴포넌트/route(서버측 발급), app(Flutter)=`supabase_flutter` Storage(**클라측 발급**, 앱엔 서버가 없음). 범용 헬퍼 `getSignedUrl(bucket, path)`는 `SIGNED_URL_TTL = 3600s` **단일 상수**를 쓴다(호출부 하드코딩 금지). *(아키텍처 236행 "서버만" 문구를 332행 "web/app이 서명"과 정합화 — "서버만"이 아니라 "api만 금지"가 정확)*
**And** 목록은 `createSignedUrls` **배치 1회**로 발급한다(NFR7 저비용)
**And** **api는 서명 URL을 발급하지 않고 `storage_path`만 반환**한다(ai_readonly 최소권한, CR2) — "api 응답에 서명 URL 문자열 부재 + storage_path 존재"를 contract test로 단언
**And** sold/삭제 매물은 서명 URL이 발급되지 않아 FR11 비노출이 **소스에서** 강제된다(CM-B)

### Story 9.3: 사진 업로더 (등록/수정)

As a 판매자,
I want 매물 등록·수정 시 사진을 여러 장 올리고 대표를 지정하길,
So that 구매자가 내 차를 사진으로 먼저 본다.

**Acceptance Criteria:**

**Given** 매물 등록/수정 폼
**When** 사진을 올리면
**Then** 드롭존 + "N/10" 카운터로 **최대 10장·장당 5MB**까지 업로드되고 첫 장이 대표가 되며 순서 변경·대표 재지정이 된다(FR26, UX-DR13)
**And** 사진은 **선택**이며 없어도 등록된다("사진은 선택이에요. 없어도 등록되지만, 있으면 문의가 훨씬 잘 와요.")
**And** 업로드 실패·용량초과는 **인라인 오류 + 재시도**(폼 제출 차단 아님)이고, 대표사진 삭제 시 다음 순서 사진이 자동 대표 승격한다
**And** **업로드 전 클라이언트가 이미지를 리사이즈/압축**한다 — 원본 5MB 상한과 별개로, 저장본을 카드/갤러리에 적합한 크기·품질로 다운스케일한다(앱은 서명 **원본**을 받으므로(ADR-IMG-01), 목록에서 수 MB 다중 다운로드 방지 = NFR7). *web은 추가로 Next.js Image로 파생 변형 렌더.*
**And** 경로는 9.1 규칙 `{user_id}/{listing_id}/`를 따른다(신규 등록은 매물 insert 후 업로드)
**And** 처리중·실패는 업로더 본인 세션의 로컬 상태이며 wire에는 null/url만 나간다(I8)
**And** 변경(특히 업로드한 사진)이 있는 채 이탈 시 이탈 경고 다이얼로그가 뜬다(변경 없으면 무경고)(UX-DR23)

### Story 9.4: 매물 카드 레이아웃 B (대표사진·N장·플레이스홀더·위계)

As a 구매자,
I want 목록 카드에서 대표사진·가격·핵심 정보를 한눈에 보길,
So that 빠르게 훑고 관심 매물을 고른다.

**Acceptance Criteria:**

**Given** ListingCard 계약(8.3)과 디자인 토큰(8.1)
**When** 카드를 렌더하면
**Then** 레이아웃 B(사진 5:3 → 신뢰속성 행 슬롯 → 차량명 → meta(주행·연료·지역) → **가격 최상위**(26/800 price-emphasis) → 옵션 칩 슬롯)로 표시된다(FR32, UX-DR4)
**And** 사진이 있으면 "N장" 다크 pill 배지(backdrop-filter 미지원 시 불투명 폴백), 없으면 "사진 준비중" 플레이스홀더(placeholder-bg + 카메라 글리프)를 보인다(FR27, FR29, UX-DR6/7)
**And** 찜 버튼(♡)은 **사진 밖** 정보 영역 우상단에 자리한다(찜 동작·토글은 Epic 10, 여기선 위치·시각만)(FR32)
**And** 이미지는 대표 1장만 로드한다(썸네일·lazy-load, NFR7)
**And** 카드 스토리 DoD로 반응형/D5 무결성을 확인한다(신뢰속성 행·옵션 칩·meta의 내부 가로배치 세로화 금지)

### Story 9.5: 상세 페이지 골격 + 사진 갤러리

As a 구매자,
I want 매물 상세에서 사진 갤러리를 넘겨보고 정보가 신뢰→차량→옵션→판매자 순으로 정리되길,
So that 구매 결정을 순서대로 신뢰 있게 내린다.

**Acceptance Criteria:**

**Given** 매물 상세 화면
**When** 진입하면
**Then** 페이지 골격이 **신뢰정보 → 차량정보 → 옵션 → 판매자정보** 순서의 섹션으로 세워지고(UX-DR24, D9), 신뢰·판매자 섹션은 Epic 10이 채울 **빈 슬롯**으로 존재한다
**And** 사진 갤러리 = 대표 5:3 + 하단 썸네일 스트립 + "1/N" 카운터 + 좌우 화살표(웹)/스와이프(앱)로 여러 장을 넘겨본다(FR28, UX-DR12)
**And** 기존 차량정보 15필드가 새 순서·디자인 토큰으로 재배치된다(사진 없으면 갤러리 자리에 플레이스홀더)
**And** 미존재·삭제·판매완료(sold) ID로 상세 URL 직접 접근 시 **404 중립 화면**("매물을 찾을 수 없어요. 삭제됐거나 판매완료된 매물일 수 있어요." + "매물 목록으로")이 뜬다(FR11, UX-DR20)
**And** sticky 문의 CTA 자리(모바일 하단 고정 바)를 마련한다(문의 개시는 기존 Epic 5 로직 재사용, 여기선 배치·본인 소유 시 "내 매물 관리" 노출)

### Story 9.6: AI 응답 카드 사진

As a AI 검색 사용자,
I want AI가 추천한 매물 카드에도 대표사진이 보이길,
So that 검색 결과를 사진으로 바로 판단한다.

**Acceptance Criteria:**

**Given** AI 검색 응답(FR17 개정)
**When** 매물 카드를 반환하면
**Then** api는 sql_guard 결과의 **on_sale id로 `listing_images` 대표 1장 `storage_path`만** 별도 고정쿼리로 반환하고(sql_guard는 listings 단일테이블 유지, JOIN 안 함)(CR2), web이 **공개 URL(고정, 만료 없음)** 로 렌더한다 *(✎ 2026-07-20 Story 9.6 정정: 원문은 "서명 URL"이었으나 **Story 9.0이 공개 버킷 + 고정 URL로 전환**했다(`0014`). 서명하지 않고 `getPublicUrl()`로 조립한다 — `docs/conventions.md` §10)*
**And** 사진이 없으면 동일한 "사진 준비중" 플레이스홀더를 보인다(ListingCard 계약 공유)
**And** `image_count`도 반환되어 "N장" 배지가 AI 카드에도 적용된다(I7)
**And** sold 매물은 storage_path가 반환되지 않아 노출되지 않는다(FR11 4번째 강제지점 정합, CM-B)

### Story 9.7: 시드 사진 + 이미지 하위호환 검증 (G3/CM-A)

As a 데모 운영자,
I want 기존 매물에 실차 사진을 채우고 사진 없는 매물도 안 깨지길,
So that 데모가 실제 서비스처럼 보이고 기존 100건이 정상 표시된다.

**Acceptance Criteria:**

**Given** Wikimedia Commons API
**When** 시드 모델(제조사+모델)로 실차 사진을 매칭하면
**Then** CC-BY/PD 실차 사진을 Storage에 업로드하고 `credit jsonb`(저작자·라이선스·원본링크)를 이미지별로 저장·표시한다(㉠)
**And** 사진 없는 기존 매물(image_url NULL)이 목록·상세·AI 카드에서 "사진 준비중"으로 렌더되고 **0건 에러가 없다**(G3/CM-A 실측)
**And** 시드 사진 생성은 데모 데이터 채우기 작업(FR 아님)이며 기존 임베딩·매물 데이터를 보존한다(CM-A)

**Given** Story 9.1이 택한 시드 재실행 전략 (기술부채 #27 — 여기가 그 전략이 **실제로 시험되는** 곳이다)
**When** **시드를 두 번 연속 실행**하면
**Then** 업로드한 사진이 **살아남는다** — 재실행 후 `listing_images` 행 수를 세어 1회차와 같음을 확인한다. **"에러가 없었다"로 갈음하지 않는다**: `ON DELETE CASCADE`는 조용히 지우므로 **에러 0건이 곧 정상이 아니다**(#27의 핵심)
**And** 재실행 후에도 목록·상세에서 사진이 정상 표시된다(브라우저 실측)
**And** 1회차와 2회차의 매물 `id`가 같은지 다른지를 기록한다 — 다르면 delete-재삽입이 여전히 일어나는 것이고, 그 경우 **Epic 10.5 `wishlists`(두 번째 자식)에서 되살아난다**는 사실을 `docs/tech-debt.md` #27에 남긴다

---

## Epic 10: 신뢰속성·옵션·찜·판매자 정보

매물 카드/상세가 신뢰도 있게 읽힌다 — 무사고·1인소유·비흡연 신뢰속성(면책 라벨 필수·CM-C), 희소 옵션 우선 노출, 찜(관심 매물 모으기·재방문), 판매자 정보 섹션. Epic 9가 세운 상세 골격의 빈 섹션을 채운다.

### Story 10.1: 신뢰속성 스키마 + 락스텝 반영

As a 판매자,
I want 무사고·1인소유·비흡연을 옵션과 별개로 신고할 수 있길,
So that 구매자가 내 차의 신뢰 정보를 옵션과 구분해 본다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0013**(원장 정본, 내용 = 신뢰속성)
**When** 적용하면
**Then** `accident_status text + CHECK('무사고'·'단순교환'·'사고')` + `is_single_owner bool` + `is_non_smoker bool`이 전부 **nullable(미입력 제3상태)**로 추가되고 self-contained하다(기존 100건 NULL 유지·backfill 없음)
**And** 이 스키마 변경이 `sql_guard` 화이트리스트 · AI 프롬프트 스키마 · ListingCard 계약 · web/app 매퍼까지 **락스텝**으로 동시 반영된다(drift 금지)
**And** 기존 `accident_free`에서 승격되며 값이 보존된다(additive, 드롭 금지)
**And** RLS 정책은 기존 listings 정책을 상속한다(규칙10)

### Story 10.2: 신뢰 뱃지 표시 + 면책 라벨

As a 구매자,
I want 카드·상세에서 무사고 여부를 한눈에 보되 그게 판매자 신고임을 알길,
So that 신뢰 정보를 참고하되 검증된 것으로 오해하지 않는다.

**Acceptance Criteria:**

**Given** 신뢰속성 데이터(10.1)
**When** 카드·상세를 렌더하면
**Then** `무사고`=초록 신뢰 뱃지(trust-green + ✓), `단순교환`·`사고`=중립 상태칩(초록 아님, 가치중립 사실 표시)로 표시된다(확정값, amber 금지)
**And** 신뢰 뱃지 옆/상세에 **"판매자 제공 정보" 면책 라벨**이 **뱃지와 한 몸으로** 렌더된다(뱃지 있으면 면책도 반드시, CM-C·FR30, Sally)
**And** 상세 신뢰 섹션에 "판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요." 문구가 표시된다(UX-DR19)
**And** 미입력(NULL) 신뢰속성은 초록 뱃지도 사고 표시도 아닌 제3상태(미표시)로 처리된다
**And** 신뢰 뱃지는 색 단독이 아닌 색+아이콘+텍스트로 표기된다(접근성, 비색 신호 중복)

### Story 10.3: 옵션 통제어휘 + 우선순위 상수 + 저장구조 정비

As a 판매자·구매자,
I want 옵션이 표준화되고 희소한 옵션이 먼저 보이길,
So that 등록이 일관되고 카드에서 차별화 옵션이 눈에 띈다.

**Acceptance Criteria:**

**Given** 옵션 데이터(`text[]` 유지, 정규화 테이블 없음)
**When** 옵션을 저장·표시하면
**Then** 쓰기 시 표준 옵션명 상수(controlled vocabulary)로 검증되고, `COMMON_OPTIONS`(보편·저순위)·`OPTION_PRIORITY`(옵션명→점수) 상수가 conventions.md 단일 출처로 선언된다(web TS·app Dart 이원화 금지)(FR31, addendum)
**And** 기술부채 #11(옵션 쉼표 문자열 라운드트립 손실, `SellForm.tsx`)이 배열/정규화 저장으로 정비된다
**And** 카드는 priority desc **상위 3~4개**만(희소 옵션 없으면 보편 fallback), 상세는 카테고리별 전량 노출한다

### Story 10.4: 옵션 하이브리드 피커 (등록)

As a 판매자,
I want 인기 옵션은 빠르게 고르고 희소 옵션은 검색으로 추가하길,
So that 많은 옵션을 부담 없이 정확히 입력한다.

**Acceptance Criteria:**

**Given** 매물 등록/수정 폼
**When** 옵션을 선택하면
**Then** 기본은 인기옵션 8칩(스마트키·내비·후방카메라·열선시트·통풍시트·선루프·크루즈·어라운드뷰)으로 대부분 끝난다(UX-DR14, D11)
**And** "전체 옵션 더보기" = 카테고리 아코디언 체크리스트(엔카 5분류: 외관/내장·안전·편의/멀티미디어·시트·기타) + **옵션 검색창**으로 희소 옵션을 구조적으로 선택한다(희소 옵션엔 "희소" 태그)
**And** 선택은 칩 요약 + 개수로 표시되고 DB엔 옵션 배열로 저장된다
**And** 반응형/D5 무결성이 피커 스토리 DoD로 확인된다

### Story 10.5: 찜 (wishlist)

As a 로그인 사용자,
I want 마음에 든 매물을 찜하고 모아 보길,
So that 나중에 다시 찾아와 비교·결정한다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0014**(원장 정본, 내용 = wishlists — 아키텍처 논리라벨 0015)
**When** 적용하면
**Then** `wishlists(user_id, listing_id, created_at, PK(user_id,listing_id))` + 본인 RLS가 생성되고 self-contained하다
**And** 카드 찜(♡) 토글은 **낙관적 반영**(즉시 채워짐) → 서버 확정, 실패 시 롤백 + 조용한 토스트다(UX-DR23)
**And** 비로그인 사용자가 찜을 누르면 로그인 게이트 후 원위치 복귀하고 찜이 반영된다(FR58 소비)
**And** "찜한 매물" 목록 화면에 도달하고, 빈 상태는 "아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요."다(UX-DR19)
**And** 찜 목록의 sold/삭제 매물은 회색 + "판매완료"/"삭제된 매물" 비활성 배지 + 상세 진입 차단으로 표시된다(FR11, UX-DR20)
**And** 찜은 서버(DB) 단일 저장이며 실시간 sync가 아니다(Reuse-First, 인기신호=보류)

### Story 10.6: 판매자 정보 섹션

As a 구매자,
I want 상세에서 판매자가 어떤 사람인지 가볍게 확인하길,
So that P2P 거래의 "이 사람 믿을 만한가" 불안을 던다.

**Acceptance Criteria:**

**Given** Epic 9가 세운 상세 골격의 판매자 섹션 슬롯
**When** 상세를 렌더하면
**Then** 경량 판매자 정보(닉네임 + 가입 시점 + "이 판매자의 다른 매물 N건")가 집계 쿼리로 표시된다(FR56)
**And** "다른 매물 N건"은 FR11 강제지점을 준수해 on_sale 매물만 집계한다
**And** 평판 점수·응답률·인증 배지는 표시하지 않는다(데이터 없음, 범위 밖 — 가짜 표시 금지)

### Story 10.7: 신뢰속성·옵션 통합 검증 (SM-C)

As a 데모 운영자,
I want 카드/상세에서 신뢰속성(면책 포함)과 희소 옵션 우선 노출이 구분돼 보임을 검증하길,
So that 이 에픽의 핵심 성공 지표(SM-C)가 착지한다.

**Acceptance Criteria:**

**Given** 신뢰속성·옵션·찜·판매자 정보가 구현된 상태
**When** 대표 매물의 카드·상세를 확인하면
**Then** SM-C(신뢰속성이 옵션과 **구분**되어 보이고, 면책 라벨이 뱃지와 함께 표시되며, 희소 옵션이 우선 노출)가 실측 확인된다
**And** CM-C(신뢰속성을 "검증됨"으로 오도하지 않음 — 면책 필수)가 재확인된다
**And** 미입력(NULL) 신뢰속성 매물이 제3상태(초록 아님·사고 표시 아님)로 안 깨지고 렌더된다

---

## Epic 11: AI 히어로 랜딩 + 내비

서비스 진입점이 AI 검색 히어로 랜딩이 된다 — 딥 petrol 히어로 + 인기(view_count)/최신 2단 그리드 + 차종 칩. 상단 내비를 소비자 자연어로 재구성한다(Epic 9/10의 완성된 카드 재사용). 반응형 뷰포트 E2E 감사를 여기서 소유.

### Story 11.0: Pretendard self-host 전환 (기술부채 #40)

As a 방문자,
I want 첫 화면 글자가 지연 없이 곧바로 제 모양으로 뜨길,
So that 히어로(11.3)의 첫인상이 폰트가 덜컥 바뀌며 무너지지 않는다.

> **왜 Epic 11 첫 스토리인가:** 이 부채의 증상(첫 페인트 지연 + 글자 덜컥임=FOUT/CLS)이 **11.3 히어로가 노리는 바로 그 화면**에서 가장 도드라진다. 큰 글자 + 첫 진입이라 폰트 스왑이 그대로 보인다. 히어로를 만들기 전에 바닥을 깔아야 한다. (Story 8.1이 낳은 부채 — 8.1 코드리뷰 defer #1·#2, 뿌리가 같아 self-host 전환 1건으로 동시 종결. 방향은 2026-07-13 사용자 확정.)

**Acceptance Criteria:**

**Given** 현재 `web/src/app/layout.tsx`가 Pretendard를 jsDelivr CDN `<link rel="stylesheet">`(dynamic-subset) + `preconnect`로 로드하고 폰트 파일이 레포에 없는 상태
**When** `next/font/local`로 self-host 전환하면
**Then** Pretendard Variable `.woff2`가 `web/` 안에 배치되고 **OFL 1.1 라이선스 텍스트가 동봉**된다
**And** `globals.css`의 `--font-sans`가 로컬 폰트 변수를 우선 참조한다(폴백 스택 `system-ui, -apple-system, …`은 유지)
**And** `layout.tsx`의 수동 `<link rel="stylesheet">` + `preconnect`가 제거된다
**And** 8.1이 명시한 보존 항목(`suppressHydrationWarning` · `min-h-full flex flex-col` · `h-full antialiased`)은 **그대로 둔다**

**Given** 전환 후 브라우저에서 랜딩을 열면
**When** 실측하면
**Then** computed `font-family`가 Pretendard이고 `document.fonts.check()`가 400/800 weight에 true(8.1과 동일 검증 방식)
**And** **네트워크 탭에 `cdn.jsdelivr.net` 요청이 더는 없다**(제거 검증 — "지웠다"가 아니라 "안 나간다"를 본다)
**And** `<Logo>` 컴포넌트("차" 800 weight)가 라이트/다크 양쪽에서 회귀 없다(8.1 산출물 확인)
**And** `next build` 통과

**Dev Notes (착수 시 실측할 것 — 추측 금지):**
- ⚠️ **폰트 파일 용량을 먼저 재라.** 현재 CDN은 **dynamic-subset**(쓰는 글자만 내려받음)이라 가벼웠다. self-host는 **정적 서브셋을 따로 만들지 않는 한 한글 전체(11,172 음절)를 통째로** 받는다 → **요청 수↓ vs 페이로드↑ 맞바꿈**. 받아서 `ls -la`로 재고, 과하면 서브셋 생성을 검토한다. *(이 트레이드오프는 기존 tech-debt #40 노트에 없었다 — 2026-07-16 조사에서 발견.)*
- **가변축은 `45 920`이다** (흔히 가정하는 `100 900`이 아님). `next/font/local`에서 `weight`는 가변 폰트면 **생략 가능** — 명시할 거면 이 값을 써야 한다.
- 조달: GitHub `orioncactus/pretendard` releases → `dist/web/variable/woff2/PretendardVariable.woff2`. 라이선스 **OFL 1.1**(상업적 사용·재배포 허용, 라이선스 파일 동봉이 관례).
- ⚠️ **Next 16 문서 선독**(`web/AGENTS.md` 원칙): `node_modules/next/dist/docs/`의 `01-app/01-getting-started/13-fonts.md`·`03-api-reference/02-components/font.md`. *(2026-07-16 확인: `next/font/local` API에 Next 16 특유의 함정은 없었다 — 표준 시그니처 그대로. `adjustFontFallback` 기본값이 로컬은 `'Arial'` 문자열이라는 점만 Google 쪽과 다르나 그대로 두면 된다.)*
- **DB·API 무관.** 건드리는 파일 3~4개(폰트 바이너리 + LICENSE, `layout.tsx`, `globals.css`). 작은 스토리.
- 검증은 `11-5-반응형-뷰포트-e2e-감사-sm-b`가 시각 게이트로 이미 있으므로 별도 회귀 장치를 새로 만들 필요 없다.

### Story 11.1: view_count 스키마 + increment RPC 하드닝

As a 구매자,
I want 인기 있는 매물이 조회수 기준으로 정렬돼 보이길,
So that 다른 사람들이 많이 본 매물을 참고한다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0015**(원장 정본, 내용 = view_count + RPC)
**When** 적용하면
**Then** `listings.view_count int default 0` + `increment_listing_view(id)` **SECURITY DEFINER RPC**가 생성되고 self-contained하다(OI-5)
**And** RPC는 하드닝된다 — `SET search_path=''` + `REVOKE EXECUTE FROM PUBLIC` + `GRANT EXECUTE TO anon, authenticated`(AC-SEC-2)
**And** `REVOKE UPDATE(view_count) FROM authenticated`(컬럼 권한)로 **RPC가 유일한 쓰기 통로**가 된다(I5, 직접 UPDATE 봉쇄)
**And** 상세 진입 시 카운터 +1이 되며, **AI 카드 렌더 시 중복 증가하지 않는다**(멱등/조회 정의)

### Story 11.2: 상단 내비 재구성

As a 사용자,
I want 사고·팔고·AI 검색·내 활동에 명확한 경로로 도달하길,
So that 메뉴에서 헤매지 않고 원하는 기능을 찾는다.

**Acceptance Criteria:**

**Given** 웹 상단 내비
**When** 렌더하면
**Then** 로고 · 내 차 사기 · AI로 찾기 · 내 차 팔기 | (비로그인) 로그인·내 차 등록 / (로그인) 찜♡ · 채팅🔔 · 프로필▾(내 매물 관리·내 정보·로그아웃)로 구성된다(UX-DR16, FR38)
**And** AI 검색이 1급으로 노출되고, 전역 "문의" 메뉴는 없다(문의는 상세에서만 개시)
**And** 라벨은 소비자 자연어("내 차 사기"·"AI로 찾기")이며 개발용어("매물 탐색"·"탐색")를 쓰지 않는다(UX-DR18)
**And** 내비는 **role-aware 훅 자리**로 선설계되어 Epic 14 역할 분기가 내비 파일을 재작성하지 않는다(Amelia)
**And** 채팅🔔의 **안읽음 배지 데이터·집계는 Epic 12(Story 12.5) 소유** — 이 스토리는 아이콘 **자리만** 배치한다(9.4 찜 버튼 시드와 동일 방식, 후행 에픽 미완성에 의존 안 함)
**And** 모바일 웹은 링크→햄버거, 찜·채팅 아이콘은 상단 상시다(UX-DR21)

### Story 11.3: AI 히어로 랜딩 (히어로 + 차종 칩)

As a 방문자,
I want 첫 화면에서 AI 검색으로 바로 차를 찾아보길,
So that 차장님이 어떤 서비스인지 즉시 체감한다.

> **AC 개정 (2026-07-14, Story 8.5 코드리뷰 + party-mode)**: AI 검색이 **로그인 필수**로 확정되면서(호출당 Gemini 실비 = 행동, 아키텍처 I2' 원칙) 구 AC *"비로그인도 히어로 검색을 사용할 수 있다"* 는 성립하지 않는다. **다만 이 스토리의 목적은 살아 있다** — 원문이 "차장님이 어떤 서비스인지 즉시 **체감**한다"이지 "AI를 **실행**한다"가 아니기 때문이다. 체감 ≠ 실행. 그래서 히어로는 **끄지 않고**(비활성화·자물쇠 금지 — 시도 전에 거절하지 않는다), 제출 시 게이트를 띄우되 **입력한 문장을 보존했다가 로그인 복귀 시 복원**한다. 비로그인 방문자가 얻는 "진짜 매물이 있구나"라는 가치는 **Story 11.4(인기·최신 매물 그리드)가 히어로 아래에서 이미 제공**한다(11.3 신규 작업 아님).
> **자동실행은 채택하지 않는다**: 복원 후 자동으로 검색을 태우면 트리거가 *페이지 로드*에 매달려 새로고침·뒤로가기·이중렌더가 전부 **재과금**이 되고, 막으려면 멱등성 가드(상태머신)를 얹어야 한다. 찜(♡)은 무료·멱등이라 자동 실행이 안전하지만 **AI는 두 번 실행되면 두 번 청구된다.** 마지막 실행은 항상 사용자의 클릭이다.

**Acceptance Criteria:**

**Given** 랜딩(홈) 첫 화면
**When** 진입하면
**Then** 딥 petrol 히어로 밴드(그라데이션 + H1 글로우 + H2 차 실루엣) + 흰 검색 pill + amber "검색" 버튼 + petrol 반투명 제안칩이 표시된다(FR33, UX-DR8)
**And** 히어로 아래 차종 빠른 진입 칩(경차·SUV·전기 등)이 검색어 없는 사용자의 진입 장벽을 낮춘다(FR35)
**And** 히어로 입력창은 **로그인 여부와 무관하게 동일하게 살아 있다** — 비활성화·자물쇠·"로그인 필요" 사전 안내를 붙이지 않는다(시도 전에 거절하지 않는다)
**And** **[비로그인]** 입력창에 질의를 넣고 제출하거나 **예시 칩을 클릭하면**(칩 = 그 문장으로 즉시 검색 시도 — 입력과 동일 취급) `/ai/search`를 호출하지 않고 **로그인 게이트**로 보낸다. 그 문장을 sessionStorage에 보존하고 `redirectedFrom`에 복귀 경로를 담는다(FR58 소비 — 게이트는 행동에만)
**And** **[비로그인]** 로그인 성공 후 복귀하면 **입력창에 원 질의가 복원**된다. **자동 실행하지 않는다**(사용자가 검색을 한 번 더 누른다). 복원 직후 sessionStorage 값은 제거한다(1회용 — 다음 방문에 옛 질문이 튀어나오지 않게)
**And** **[로그인]** 입력 제출·칩 클릭은 게이트 없이 즉시 AI 검색을 실행한다
**And** 잔여 횟수·"무료 검색 N번 남았어요" 류 카운터는 **어디에도 표시하지 않는다**(익명 N회 허용안 폐기에 따름 — 지킬 수 없는 숫자는 표시하지 않는다)
**And** AI 검색 입력은 500자 상한 + 실시간 카운터·초과 방지다(UX-DR23, I11)
**And** 반응형/D5 무결성이 확인된다(히어로 헤드라인 amber 음절 대비 유지)

### Story 11.4: 인기/최신 매물 그리드

As a 방문자,
I want 히어로 아래에서 인기·최신 매물을 바로 훑어보길,
So that 검색 전에도 어떤 매물이 있는지 감을 잡는다.

**Acceptance Criteria:**

**Given** 완성된 매물 카드(Epic 9/10)와 view_count(11.1)
**When** 랜딩을 렌더하면
**Then** 인기(view_count 정렬)/최근 등록(created_at 정렬) **2단 발췌 그리드**가 표시된다(FR34)
**And** "전체 보기"가 /search로 진입하며, **랜딩은 필터 상태·URL 쿼리파라미터를 소유하지 않는다**(전체 목록·페이지네이션의 단일 소유자 = /search)
**And** sold 매물은 그리드·정렬에서 제외된다(FR11)
**And** 카드 그리드가 반응형(4/2/1열)으로 재배치된다(D5)

### Story 11.5: 반응형 뷰포트 E2E 감사 (SM-B)

As a 개발자,
I want 랜딩·목록·상세·카드가 전 뷰포트에서 안 깨짐을 자동 검증하길,
So that 반응형 회귀를 배포 전에 잡는다.

**Acceptance Criteria:**

**Given** 완성된 사용자 화면들(랜딩·목록·상세·카드)
**When** 뷰포트 매트릭스(데스크톱 ≥1100·태블릿 640~1099·모바일 <640)로 E2E를 돌리면
**Then** 그리드가 4/2/1열로 재배치되고 컴포넌트 내부 가로배치의 세로화·줄바꿈 어긋남·2줄 버튼이 **없음**을 단언한다(FR36 감사, D5)
**And** SM-B(랜딩 AI 히어로 + 인기/최신 그리드 동작 + 반응형 재배치)가 실측 확인된다

---

## Epic 12: 실시간 문의 채팅

문의 채팅이 폴링 → 실시간으로 바뀐다 — 메시지 즉시 반영, 재연결 배너(유실 없는 갭보정), 멱등키 중복 방지, 안읽음 배지. 기존 채팅 무결성 3중 장치(RLS·트리거·CHECK)는 보존한다(CM-B).

### Story 12.1: 멱등키 마이그레이션

As a 사용자,
I want 네트워크가 끊겨 재전송돼도 메시지가 중복되지 않길,
So that 대화 기록이 깨끗하게 유지된다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0016**(원장 정본, 내용 = chat 멱등키 — 아키텍처 논리라벨 0016)
**When** 적용하면
**Then** `chat_messages.client_message_id` + **`UNIQUE(room_id, client_message_id)`**(CR1) + `ON CONFLICT DO NOTHING`이 추가되고 self-contained하다
**And** 기존 0003c BEFORE INSERT 트리거(seller_id 강제)·0010 2000자 제약과 충돌하지 않음을 검증한다(동일 키 2회 INSERT → 행 1개·트리거 부작용 0)(AC-CHAT-1)
**And** `client_message_id`는 additive 컬럼이며 기존 메시지·스키마를 깨지 않는다(I13)

### Story 12.2: Realtime Broadcast + 참가자 인가 RLS

As a 대화 당사자,
I want 내가 참여한 방의 메시지만 실시간으로 받길,
So that 남의 대화가 새지 않고 안전하게 채팅한다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0017**(원장 정본, 내용 = chat realtime broadcast — 아키텍처 논리라벨 0017)
**When** 적용하면
**Then** `realtime.broadcast_changes` 트리거 + `realtime.messages` RLS + private 채널이 구성되고, 토픽 형식은 `chat:room:{room_id}`로 트리거·RLS·클라 구독 **3곳이 동일**하다(불일치 시 인증·수신 붕괴)
**And** `realtime.messages` RLS가 토픽을 파싱해 **요청자가 그 room의 buyer/seller인지** 검사한다(AC-CHAT-3, private 채널 + setAuth 전제)
**And** chat_messages 스키마는 소스 오브 트루스로 불변이다(broadcast는 그 위 계층)

### Story 12.3: 실시간 송수신 전환 (폴링 제거)

As a 사용자,
I want 문의 메시지가 폴링 지연 없이 즉시 오가길,
So that 판매자와 실시간으로 대화한다.

**Acceptance Criteria:**

**Given** Realtime 구독(12.2)
**When** 메시지를 주고받으면
**Then** 기존 4초 증분 폴링이 제거되고 구독으로 즉시 반영된다(FR40, FR20 개정)
**And** 전송은 낙관적(즉시 pending 버블 → 서버 확정, 멱등키로 중복 차단)이다(UX-DR15)
**And** 클라는 `broadcast_changes` 엔벨로프의 `payload.record`(INSERT)를 파싱하고, 표시 순서는 chat_messages **`created_at` + `id` tiebreak** 정렬로 렌더한다(AC-CHAT-2와 동일 커서, 동일 타임스탬프 메시지 순서 안정화)(I10)
**And** 메시지는 DB 저장이 유지되고(FR21), 입력 2000자 상한 + 실시간 카운터가 동작한다(기구현 재사용)
**And** 채팅 무결성 3중 장치(RLS·트리거·CHECK buyer≠seller)가 실시간 전환 후에도 유지된다(CM-B)

### Story 12.4: 재연결 배너 + 갭 보정

As a 사용자,
I want 연결이 끊겨도 계속 쓰고 재연결 시 놓친 메시지를 받길,
So that 불안정한 네트워크에서도 대화가 유실되지 않는다.

**Acceptance Criteria:**

**Given** 실시간 구독 중 연결 끊김
**When** 끊기면
**Then** 비차단 배너("연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요.")가 뜨고 끊긴 채로 계속 타이핑·전송(pending 큐)한다(FR42, UX-DR19)
**And** 재연결 시 큐가 전송(멱등 중복 없음)되고 배너가 초록("다시 연결됐어요")으로 전환 후 사라진다
**And** 재연결 시 Broadcast Replay(≤25/72h) 우선 + 초과분은 `WHERE created_at >= {cursor}`(strict > 아님, CR6) 재조회로 상대방이 보낸 놓친 메시지를 병합한다(dedup 키=`client_message_id`)(AC-CHAT-2)
**And** 재연결 성공은 색+텍스트("다시 연결됐어요")로 표기된다(접근성 비색 신호 중복)

### Story 12.5: 안읽음 배지 + 방 목록 정렬

As a 판매자,
I want 안 읽은 문의가 배지로 보이고 최신 문의가 위에 오길,
So that 실시간 전환의 실제 가치 — 문의를 놓치지 않는다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0018**(원장 정본, 내용 = chat_room_reads — 아키텍처 논리라벨 0018)
**When** 적용하면
**Then** `chat_room_reads(user_id, room_id, last_read_at)`가 생성되고 self-contained하다(FR57)
**And** 채팅 진입점(내비 🔔)에 안읽음 카운트 배지가 표시되고, 안읽음 = `created_at > last_read_at` **AND `sender_id != {me}`**(내 발신 제외)로 집계된다(I6)
**And** 방 목록이 최신 문의 순으로 정렬된다
**And** 방 진입/열람 시 `last_read_at`이 갱신된다
**And** 안읽음 배지는 점 + 숫자 텍스트로 표기된다(접근성)

### Story 12.6: 실시간 채팅 검증 (SM-E)

As a 데모 운영자,
I want 실시간 송수신·재연결·유실 없음을 실제로 확인하길,
So that 자동 테스트로 안 잡히는 실시간/오프라인 거동을 수동 검증한다(SM-E).

**Acceptance Criteria:**

**Given** 두 브라우저(구매자·판매자) 세션과 실시간 채팅
**When** 메시지를 주고받고 한쪽 네트워크를 끊었다 재연결하면
**Then** SM-E(폴링 지연 없이 즉시 송수신 + 재연결 상태 표시)가 실측 확인된다
**And** 끊긴 동안 상대가 보낸 메시지가 재연결 후 **유실 없이** 병합되고(갭보정), 재전송이 중복되지 않음(멱등)을 확인한다
**And** CM-B(채팅 무결성 3중 장치: RLS·트리거·CHECK buyer≠seller)가 실시간 전환 후에도 유지됨을 확인한다
**And** 실폰(앱)·웹 교차(divergence) 여지가 있으면 기록한다([[e2e-crosscheck-plan]] 연계)

---

## Epic 13: AI 검색 RAG 고도화

AI 검색이 상용 수준으로 올라간다 — 4분기 라우팅, SQL+벡터 하이브리드, 가이드 문서 실제 활용, 거리 컷오프, LangSmith 관측성. (커넥션 풀 롤 격리 AC-DB-1은 Epic 8에서 선행 완료.)

### Story 13.1: sql_guard 하이브리드 정비 + G2 baseline

As a 개발자,
I want 하이브리드 SQL이 안전장치를 통과하고 회귀 기준선을 잡길,
So that 보안을 지키면서 RAG를 개선하고 품질 후퇴를 감지한다.

**Acceptance Criteria:**

**Given** `sql_guard.validate_select_sql()`
**When** 하이브리드 벡터 쿼리를 검증하면
**Then** `<=>`·`::vector`·`embedding`·`vector` 화이트리스트가 추가되고 `status='on_sale'` AND가 **강제**된다(AC-SEC-1, I4)
**And** 벡터절은 LLM이 아니라 **코드가** `ORDER BY embedding <=> $1::vector LIMIT k`를 바인드 파라미터로 덧붙인다(LLM은 WHERE 구조조건만 생성)(I4)
**And** 회귀 3케이스가 통과한다 — 정상 벡터쿼리 통과 / OR·서브쿼리 주입 거부 / status 필터 누락 거부
**And** Phase B 회귀 하니스 baseline(~44 질의셋)을 심어 이후 RAG 스토리가 재실행할 기준선을 확보한다(G2)

### Story 13.2: 4분기 라우팅

As a AI 검색 사용자,
I want 내 질문 의도가 정확히 분류되길,
So that 상황에 맞는 답(검색·되묻기·거절)을 받는다.

**Acceptance Criteria:**

**Given** 라우터 노드
**When** 질문을 라우팅하면
**Then** 4갈래(REJECT/CLARIFY/SQL/HYBRID)로 분류한다 — 무관/법적→거절, 광범위→되묻기, 구조형→Text-to-SQL, 조합형→하이브리드(FR43)
**And** `RouterDecision` Literal · `_fallback_route` · `_route_decision` **3곳이 락스텝**으로 확장된다(하나 빠지면 신 라우트를 조용히 흡수하는 회귀)
**And** 4값 분기·CLARIFY 발동에 결정론적 단위테스트가 신설된다
**And** CLARIFY는 "조건 전무 극단 질의"에만 좁게 발동한다(라우터 프롬프트 신호)

### Story 13.3: 하이브리드 검색 (SQL+벡터)

As a AI 검색 사용자,
I want "4천 이하 SUV 중 통풍시트 있는 차" 같은 혼합 질의가 되길,
So that 정형 조건과 의미 조건을 한 번에 만족하는 매물을 찾는다.

**Acceptance Criteria:**

**Given** HYBRID 경로(sql_guard 정비 완료, 13.1)
**When** 정형+의미 혼합 질의가 오면
**Then** 단일 쿼리 `WHERE status='on_sale' AND <구조조건> ORDER BY embedding <=> $1::vector LIMIT k`로 SQL 필터 + 유사도를 조합한다(RRF 없음)(FR45)
**And** 생성 SQL은 예외 없이 sql_guard를 통과하고 status='on_sale'을 강제한다(AC-SEC-1, 보안 블로커)
**And** 구조조건을 못 뽑으면 기존 벡터검색으로 폴백해 회귀가 없다
**And** SM-G(조합형 질의에서 하이브리드가 SQL 필터+유사도 조합 결과 반환)를 대표 질의로 확인한다

### Story 13.4: 조건 좁혀 되묻기 (CLARIFY)

As a AI 검색 사용자,
I want 너무 막연한 질문엔 조건을 좁혀주는 되묻기를 받길,
So that 0건/엉뚱한 결과 대신 원하는 방향으로 안내받는다.

**Acceptance Criteria:**

**Given** CLARIFY 경로(신규 노드)
**When** 광범위 질의가 오면
**Then** `interrupt()`/체크포인터 없이 되묻기 문장을 answer로 반환하고, 사용자 다음 메시지를 기존 멀티턴 `contextualize_query`로 이어붙인다(무상태)(FR46)
**And** 응답 계약에 `clarify: { question, chips[] }`(route='CLARIFY' 전용)가 담겨 제안형 되묻기 + tappable 칩이 렌더된다(추가 LLM 없음)(CR5)
**And** 칩은 타이핑과 동등 경로이고 자유 타이핑이 항상 병존한다(탭 시 petrol 채움 "선택됨")
**And** 되묻기 상한 = 최대 2~3턴이며, 초과 시 현재 조건으로 결과를 강제 제시하고 "검색 후 필터" 안내한다(무한 되묻기 금지, 클라 강제 I12)
**And** G1(CLARIFY 과다발동율)을 Phase B 질의셋으로 실측해 명시조건 질의가 CLARIFY로 새지 않음을 확인한다

### Story 13.5: 부드러운 거절

As a AI 검색 사용자,
I want 중고차와 무관한 질문엔 정중한 안내를 받길,
So that 막다른 길 대신 매물 검색으로 자연스럽게 돌아간다.

**Acceptance Criteria:**

**Given** REJECT 경로
**When** 법적/무관 질의가 오면
**Then** 고정 템플릿(무상태·결정론)으로 정중히 거절하고 매물 검색으로 유도한다("저는 중고차 찾기를 도와드리는 차장님이에요 🚗 …")(FR47, LLM 자유 재작성 없음)
**And** 0건·거절의 다양성은 문구 생성이 아니라 서버가 내려주는 **구조화 사유 데이터** `narrowed_by`(저장단위 원 정규화 술어, 예 `["price<=30000000"]`)를 결정론 템플릿이 조립한다(CR4)
**And** 거절 응답에 원 조건 재제안 칩을 제시한다(막다른 길 아님)

### Story 13.6: 가이드 문서 content 활용 + 거리 컷오프

As a AI 검색 사용자,
I want "패밀리카" 같은 상식 표현으로도 적합 매물이 뜨길,
So that 매물 설명에 그 단어가 없어도 원하는 차를 찾는다.

**Acceptance Criteria:**

**Given** 가이드 문서 코퍼스(12문서)
**When** 질의를 처리하면
**Then** 가이드 content에서 상식 기준(예 "패밀리카→SUV/RV/5인승+")을 읽어 **검색 조건/가중치로 변환**한다((b) 질의확장, FR44)
**And** 답변 텍스트는 기존 결정론 방식을 유지한다(가이드 본문으로 설명 문장을 LLM 생성하지 않음)
**And** 코사인 거리 `<=>`가 임계값 이하일 때만 content를 답변 근거로 사용한다(거리 컷오프, FR49). **임계값은 하드코딩 상수가 아니라 Phase B 질의셋으로 튜닝해 확정**한다(초기 후보 0.3 → 배포 전 실측으로 고정, 노이즈 부착률로 판정)
**And** 청킹은 도입하지 않는다(현 12문서=page-level, FR48 조건부 — ≥20문서/≥800토큰 시에만)

### Story 13.7: LangSmith 트레이싱

As a 개발자,
I want 라우팅 분포·가드 차단·되묻기 발동을 사후에 눈으로 보길,
So that AI 검색 동작을 관측하고 오분류를 잡는다.

**Acceptance Criteria:**

**Given** LangSmith Developer(무료)
**When** 트레이싱을 켜면
**Then** env 2개(`LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`)로 활성화되고 **코드 변경이 0**이다(자동 계측)(FR51)
**And** 라우팅 오분류·SQL 가드 차단·0건 응답·되묻기 발동 빈도를 트레이스로 추적한다
**And** 평가 자동화·Deployment는 도입하지 않는다(카드 미등록=5000 trace/월 하드캡)

### Story 13.8: RAG exit-gate 검증 (SM-F/SM-G/G2/CM-B)

As a 개발자,
I want RAG 개선 후에도 기존 시연이 유지되고 신규 분기가 동작함을 증명하길,
So that 품질 후퇴 없이 에픽을 종료한다.

**Acceptance Criteria:**

**Given** 4분기·하이브리드·가이드·되묻기·거절이 구현된 상태
**When** 회귀 하니스와 대표 질의를 돌리면
**Then** SM-F(원본 AI 검색 시연 3종: 구조형·질적형·가드 유지)가 통과한다
**And** SM-G(신규 분기 동작: 하이브리드 조합·되묻기 제안·부드러운 거절 각 1개 이상)가 확인된다
**And** G2(RAG 회귀 게이트)가 Phase B baseline(13.1) 이하로 떨어지지 않는다 — 통과 못하면 에픽 미종료
**And** CM-B(AI 안전장치: sql_guard·ai_readonly·FR11 sold 비노출)가 실시간/하이브리드 전환 후에도 유지된다

---

## Epic 14: 계정 역할 통합 나머지 (별도 워크스트림)

가입 시 구매자/판매자 역할 선택이 사라지고, 누구나 사고팔 수 있다(소유권 기반 접근제어). 인증·RLS를 건드리므로 UI/이미지 커밋과 분리 관리. (비로그인 열람 토대 FR58은 Epic 8에서 선행.)

### Story 14.1: role CHECK 완화 마이그레이션

As a 개발자,
I want role 컬럼을 유지하면서 buyer/seller 구분만 무의미화하길,
So that 관리자 기능을 깨지 않고 역할 통합의 토대를 놓는다.

**Acceptance Criteria:**

**Given** 마이그레이션 **0019**(원장 정본, 내용 = role CHECK 완화 — 아키텍처 논리라벨 0013)
**When** 적용하면
**Then** `profiles.role` CHECK가 완화되어 buyer/seller가 무의미화되고 **admin은 존치**된다(is_admin()·0005 의존 보존)(FR54, self-contained)
**And** role CHECK 완화가 기존 RLS의 role 비교(0002 등)를 안 깨는지 grep으로 검증한다(AC-F14-1)
**And** 기존 계정 데이터가 보존된다(forward 마이그레이션)
**And** **이번 증분은 컬럼 rename을 하지 않는다(확정)** — `profiles.role` 컬럼명은 그대로 두고(is_admin()·0005·기존 RLS 의존, rename 시 전멸) **값 의미만 admin vs 일반 2축으로 축소**한다(buyer/seller 무의미화). "account_type"은 미래 개인 vs 사업자 축을 위한 **개념적 명명**일 뿐 이번 증분에 신규 컬럼·rename은 없다. 아래 스토리·관리자 UI가 "account_type 기준"이라 할 때 = **role='admin' 여부(admin/일반) 구분**을 뜻한다

### Story 14.2: 가입 역할선택 제거 + 트리거 기본 role

As a 신규 사용자,
I want 가입할 때 구매자/판매자를 고르지 않아도 되길,
So that 가입 후 언제든 사고팔 수 있다.

**Acceptance Criteria:**

**Given** 회원가입 화면
**When** 가입하면
**Then** 역할 선택 UI가 제거된다(FR52) — "차를 사고파는 건 가입 후 언제든 할 수 있어요."(UX-DR19)
**And** `0001 handle_new_user` 트리거가 신규 가입에 기본 role을 배정한다(역할선택 제거 시 기본값 필요)(I3)
**And** 기존 로그인/로그아웃(FR2)이 깨지지 않는다

### Story 14.3: 소유권 기반 판매 게이트

As a 로그인 사용자,
I want 별도 판매자 자격 없이 매물을 등록·관리하길,
So that 누구나 판매자이자 구매자가 된다.

**Acceptance Criteria:**

**Given** 매물 등록·수정·삭제·구매완료 경로
**When** 접근하면
**Then** 웹 판매 게이트가 `requireRole(SELLER)` → `requireUser()`로 완화되어 로그인 사용자 누구나 등록한다(FR53)
**And** 수정/삭제/"구매 완료"는 그 매물의 등록자만 가능하다(소유권 기준, 기존 RLS 재사용 — 사실상 무변경)
**And** 남의 매물 수정/삭제 시도는 소유권 RLS로 차단되고 UI에 미노출된다(UX-DR20)

> *관리자 회원관리 화면의 구매자/판매자 필터 정리(FR61)는 Epic 15(Story 15.3)가 소유한다 — Epic 14는 데이터/접근제어(role·게이트)만 바꾸고, 관리자 UI 반영은 Epic 15로 단일화(구 14.4 중복 제거).*

---

## Epic 15: 관리자 웹 UI 통일 (UI-only)

관리자 6화면을 신규 디자인 시스템으로 통일 + PC/모바일 반응형(D5 무결성, 관리자도 예외 없음). 신규 기능·운영 배관 없음. (PRD 역반영 완료 — addendum FR59~61.)

### Story 15.1: 관리자 6화면 디자인 리스킨

As a 관리자,
I want 관리 화면들이 사용자 화면과 같은 디자인 언어로 통일되길,
So that 운영 도구도 일관되고 프리미엄하게 보인다.

**Acceptance Criteria:**

**Given** 관리자 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)과 디자인 토큰(8.1)
**When** 리스킨하면
**Then** @theme 토큰(페트롤+앰버)·카드/뱃지/버튼/타이포 위계로 통일된다(FR59, admin-mockups-2 참조)
**And** **신규 기능·개발/운영 배관(스토리지 청소·미처리 큐·신고/차단)은 추가하지 않는다**(UI-only)
**And** 관리자 **전체매물·매물상세**는 이미 존재하는 이미지 데이터를 **사용자와 동일한 서명 URL 경로(9.2)로 렌더**한다(데이터가 이미 있으므로 표시하는 것은 UI-only 범위 내 — 관리자만 sold 포함 열람). 신규 이미지 편집 기능은 없음
**And** 기존 관리자 기능(회원관리·전체매물·거래내역·채팅관리, FR22~25)이 동작을 유지한다

### Story 15.2: 관리자 반응형

As a 관리자,
I want 관리 화면을 PC·모바일 브라우저 어디서든 쓰길,
So that 이동 중에도 운영한다.

**Acceptance Criteria:**

**Given** 리스킨된 관리자 6화면
**When** 뷰포트가 바뀌면
**Then** 단일 코드 반응형으로 PC/모바일에 대응한다(FR60)
**And** D5 반응형 무결성을 준수한다 — 필터 버튼·라벨 줄바꿈 어긋남·레이아웃 깨짐이 **없다**(관리자도 예외 없음, 규칙13)
**And** 뷰포트 매트릭스 E2E로 무결성을 확인한다(Epic 11 감사와 동일 기준)

### Story 15.3: 회원관리 역할통합 반영

As a 관리자,
I want 회원관리에서 역할 통합이 UI로 정리되길,
So that 통합 후 회원을 혼란 없이 관리한다.

**Acceptance Criteria:**

**Given** 역할 통합(Epic 14)이 반영된 상태
**When** 회원관리 화면을 렌더하면
**Then** 무의미해진 구매자/판매자 구분 필터가 제거·정리되고 **admin/일반**(=`role='admin'` 여부, 신규 컬럼 아님) 구분으로 표시된다(FR61 — 이 스토리가 FR61 정책 소유)
**And** admin 권한 표시·정지/삭제(FR22)가 유지된다

---

## Epic 16: Flutter 앱 증분 반영

Flutter 앱이 웹과 동일 디자인 언어로 개편된다 — 이미지·카드 재설계·신뢰속성·찜·실시간 채팅·4분기 AI·하단 4탭. 웹 셸 재사용 불가라 별도 위젯이되, 계약(색·비율·필드)은 conventions.md 공유. 웹 기능이 안정된 뒤 미러링.

### Story 16.1: 디자인 토큰 미러 + 하단 4탭 내비

As a 앱 사용자,
I want 앱이 웹과 같은 색·타이포·구조로 보이길,
So that 웹에서 앱으로 와도 같은 서비스로 느낀다.

**Acceptance Criteria:**

**Given** 웹 디자인 토큰(DESIGN.md·conventions.md 단일 출처)
**When** 앱 테마를 구성하면
**Then** 색·토큰·타이포(Pretendard 번들)·카드 레이아웃 B·초록 신뢰뱃지·amber 가격·플레이스홀더가 웹과 동일하게 미러링된다(FR39, D14)
**And** 하단 4탭(홈(AI)·찜·채팅·내차팔기, FAB 없음)이 `GoRouter StatefulShellRoute`(탭 상태 보존) + Material 3 `NavigationBar`로 구현된다(UX-DR17, D12)
**And** 프로필은 우상단 아바타, 내 차 사기는 홈 하단 스크롤/필터에서 도달한다
**And** backdrop-filter blur는 구형 WebView no-op → 불투명 폴백을 쓴다

### Story 16.2: 이미지·카드 재설계 (앱)

As a 앱 사용자,
I want 앱에서도 매물 사진을 카드·상세 갤러리로 보길,
So that 모바일에서 사진 중심으로 매물을 훑는다.

**Acceptance Criteria:**

**Given** listing_images·서명 URL(Epic 9)
**When** 앱에서 매물을 렌더하면
**Then** 카드 대표사진(5:3, BoxFit.cover)·"N장" 배지·"사진 준비중" 플레이스홀더가 표시된다(FR39)
**And** 상세는 사진 갤러리(스와이프 + "1/N" 카운터)로 여러 장을 넘겨본다
**And** 앱은 서명 원본 이미지를 Storage에서 받아 렌더한다(api는 storage_path만 반환하므로 앱이 서명)
**And** 사진 없는 매물이 안 깨진다(CM-A 앱 확인)

### Story 16.3: 신뢰속성·찜 (앱)

As a 앱 사용자,
I want 앱에서도 신뢰 뱃지(면책 포함)와 찜을 쓰길,
So that 웹과 동일하게 신뢰 정보를 보고 관심 매물을 모은다.

**Acceptance Criteria:**

**Given** 신뢰속성·wishlists(Epic 10)
**When** 앱에서 렌더·조작하면
**Then** 무사고=초록 뱃지·단순교환/사고=중립칩 + "판매자 제공 정보" 면책이 한 몸으로 표시된다(CM-C)
**And** 찜 토글(낙관적·로그인 게이트·실패 롤백)과 찜 목록 화면이 동작한다(FR55)
**And** 옵션 희소도 표시(카드 상위 3~4·상세 카테고리 전량)가 conventions.md 상수를 공유한다

### Story 16.4: 실시간 채팅 (앱)

As a 앱 사용자,
I want 앱에서도 문의가 실시간으로 오가고 놓친 메시지를 받길,
So that 이동 중에도 판매자와 실시간 대화한다.

**Acceptance Criteria:**

**Given** Realtime Broadcast·멱등키·chat_room_reads(Epic 12)
**When** 앱에서 채팅하면
**Then** `supabase_flutter` Realtime 구독으로 즉시 송수신하고(폴링 아님), 토픽 `chat:room:{room_id}` 계약을 웹과 공유한다(FR40)
**And** 멱등키 중복 방지·재연결 배너·"마지막 수신 이후" 갭보정이 동작한다(FR41, FR42)
**And** 안읽음 배지·방 목록 최신순이 표시된다(FR57)
**And** 채팅 무결성(RLS·트리거·CHECK)이 유지된다(CM-B)

### Story 16.5: 4분기 AI 응답·되묻기 칩 (앱)

As a 앱 사용자,
I want 앱 홈의 AI 검색이 4갈래로 똑똑하게 답하길,
So that 웹과 동일한 AI 경험을 모바일에서 누린다.

**Acceptance Criteria:**

**Given** 4분기 RAG(Epic 13)
**When** 앱 홈 AI 검색을 쓰면
**Then** 구조형·하이브리드·되묻기·거절 4갈래 응답이 렌더되고, Riverpod 검색 상태를 웹과 동일 형태로 미러링한다(D14)
**And** 되묻기 칩(tappable, petrol 선택 상태)이 자유 타이핑과 병존하고 상한 2~3턴을 지킨다
**And** AI 입력 500자 상한이 적용된다

### Story 16.6: SM-D 통합 시연 검증 (앱)

As a 데모 운영자,
I want 앱이 웹과 동일 디자인 언어로 개편됐음을 실폰에서 검증하길,
So that 멀티 서피스 일관성을 시연한다.

**Acceptance Criteria:**

**Given** 개편된 Flutter 앱(16.1~16.5)
**When** 실폰(USB + mobile-mcp)에서 재현 여정을 돌리면
**Then** SM-D(앱이 웹과 동일 디자인 언어로 이미지·카드 반영)가 확인된다
**And** 재현 대상 = FR26~58 중 앱 사용자 여정(관리자 제외)이며, 웹 결정을 상속하고 델타(하단 4탭·스와이프·OS back)만 다르다
**And** 한글 입력 제약(mobile-mcp ASCII만)은 ADBKeyBoard IME로 우회해 검증한다
