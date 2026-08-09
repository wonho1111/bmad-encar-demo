# Epic 16 Context: Flutter 앱 증분 반영

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

웹이 이번 증분(이미지·카드·신뢰속성·찜·실시간 채팅·4분기 AI·랜딩)으로 먼저 개편된 뒤, Flutter 앱을 같은 디자인 언어와 기능으로 미러링한다. 웹 셸을 재사용할 수 없어 앱은 별도 위젯으로 구현하되, 색·타이포·카드 구성·API 계약은 웹과 공유해 "웹에서 앱으로 와도 같은 서비스"로 느끼게 한다. 웹 안정화 이후 착수하는 후행 에픽이다.

## Stories

- Story 16.1: 디자인 토큰 미러 + 하단 4탭 내비
- Story 16.2: 이미지·카드 재설계 (앱)
- Story 16.3: 신뢰속성·찜 (앱)
- Story 16.4: 실시간 채팅 (앱)
- Story 16.5: 4분기 AI 응답·되묻기 칩 (앱)
- Story 16.6: SM-D 통합 시연 검증 (앱) — 실폰 검증, 에픽 마지막에 실행
- Story 16.7: 앱 사진 업로더
- Story 16.8: 앱 홈 랜딩 미러

## Requirements & Constraints

- FR39: 앱을 웹과 동일 디자인 언어(색 토큰·카드 구성·신뢰속성/옵션 표시·플레이스홀더 규칙)로 개편.
- FR40~42: 채팅 폴링→실시간 전환, 전송 멱등키(클라 생성 uuid)로 중복 방지, 재연결 시 비차단 배너 + "마지막 수신 이후" 1회 보정으로 갭 메움.
- FR55/FR57: 찜 토글·목록. 채팅 진입점 안읽음 카운트 배지, 방 목록 최신 문의 순.
- FR58: 비로그인도 매물 열람 가능. 로그인 게이트는 화면이 아니라 "행동"(비용 발생 여부) 기준 — AI 검색은 호출당 실제 과금이 나가는 행동이라 로그인 필수, 열람은 서버 자원 읽기뿐이라 무관.
- NFR3: 앱은 웹과 코드 공유 없는 별도 구현이며 디자인 언어만 계승한다.
- AI 입력 500자 상한은 서버 강제. 되묻기 3턴 상한도 서버가 클라 전송 맥락 길이로 세어 강제, 초과 시 `clarify:null` — 클라는 null이면 칩을 안 그리면 된다(맥락 길이 의존이라 완전하진 않음, 알려진 한계).
- 사진 업로드 계약(웹 9.3 확정, 앱도 동일): 경로 `{판매자}/{매물}/{파일명}`, 1600px WebP, 대표=순서 0, 파일명은 (매물+순번)로 결정론적이라 재시도가 덮어씀(고아 방지). 삭제는 ①Storage 오브젝트→②DB 행 순서 고정. `sold` 매물 사진 추가/삭제는 DB 쓰기 정책으로 막는다(화면 방어 아님).

## Technical Decisions

- **이미지 URL = 공개 버킷 + 고정 URL, 서명 URL 아니다.** 2026-07-19 ADR-IMG-02가 비공개+서명 방식을 대체(`getPublicUrl(bucket, path)`로 조립, 만료 없음). api(FastAPI)는 `storage_path`만 반환하고 URL은 web/app이 각자 조립한다. (epics 문서 16.2 원문은 아직 "서명"으로 남아 있으나 아키텍처 문서가 더 최신·정본.)
- **실시간 채팅 = Supabase Realtime "Broadcast from Database".** DB 트리거가 private 채널로 broadcast, 토픽 `chat:room:{room_id}`을 트리거·RLS·클라 구독 3곳이 동일하게 써야 한다(불일치 시 인증·수신 붕괴). 표시 순서는 클라가 `chat_messages.created_at`으로 정렬. 재연결 갭보정 = Broadcast Replay(≤25건/72h) 우선 → 초과분은 `created_at >=` 커서 재조회 + `client_message_id` dedup. Flutter는 `supabase_flutter` Realtime으로 동일 계약.
- **AI 응답 계약**: `{answer, listings[], route: REJECT|CLARIFY|SQL|HYBRID, narrowed_by?, clarify?: {question, chips}}`. answer는 결정론 생성(LLM 자유 재작성 금지). 0건·거절의 다양성은 서버가 내려주는 구조화 사유(`narrowed_by`)를 고정 템플릿이 조립.
- **하단 내비 = `GoRouter StatefulShellRoute`(탭 상태 보존) + Material 3 `NavigationBar`.** 4탭: 홈(AI)·찜·채팅·내차팔기, FAB 없음. 프로필=우상단 아바타. 내 차 사기는 홈 하단 스크롤/필터로 도달.
- 디자인 토큰은 웹 단일 출처(색·타이포·카드 레이아웃 B·초록 신뢰뱃지·amber는 가격/CTA 전용·딥 petrol 히어로는 라이트/다크 동일)를 미러링. 폰트는 Pretendard를 앱에 번들(웹은 CDN).
- 구형 WebView는 `backdrop-filter` blur가 no-op → 불투명 배경 폴백.
- 역할 어휘: `profiles.role`은 `admin`만 특별 취급, 그 외 전부 `user`(구매/판매 구분 없음). 접근 권한은 이 값이 아니라 소유권(`seller_id`)+RLS로 판정. 16.1이 하단 4탭·admin 차단에 이 어휘를 실제로 쓰므로 `docs/conventions.md`에 정본 절로 올리고, `currentRoleProvider`의 무-role 동작을 `app/test/`가 단언하게 한다(지금 단언 0건임을 채택 전 확인).
- 신뢰속성(`accident_status` 텍스트+CHECK `'무사고'|'단순교환'|'사고'`, `is_single_owner`, `is_non_smoker`)은 전부 nullable, 기존 100건 NULL="미입력" 제3상태로 별도 표시, 항상 "판매자 제공 정보" 면책과 한 몸.
- 찜은 DB 단일 저장(`wishlists(user_id, listing_id)` + 본인 RLS), 웹·앱 간 실시간 동기화 없음 — 각자 조회 시점 상태만 반영.

## UX & Interaction Patterns

- 히어로 밴드: 딥 petrol 그라데이션, "원하는 차를 **말**로 찾으세요"(말만 amber 강조) + 알약형 입력 + amber 검색 버튼. 제안 칩 4개는 목업이 아니라 웹 `HeroSearch.tsx`의 `SUGGESTIONS`가 정본(가성비 좋은 첫차·4천만원대 전기 SUV·주행거리 짧은 무사고 세단·7인승 디젤 패밀리카).
- 차종 칩: 전체·경차·SUV·전기·화물·승합("세단"·"수입"은 DB `body_type`/`fuel`에 대응값이 없어 웹이 이미 대체한 라벨을 따름). 탭하면 해당 필터로 이동.
- "지금 인기"(view_count desc)·"방금 올라온 매물"(created_at desc) 2섹션, 각 4건 + 전체보기. 앱은 웹의 가로 2단이 아니라 세로 2섹션.
- Epic 7 잔재 퀵액션(문의 채팅·매물 등록·내 매물 관리 3버튼)은 히어로/칩/2섹션 신설과 **같은 커밋**에서 제거 — 먼저 지우면 하단 탭이 그 화면을 아직 못 여는 동안 판매자가 등록 경로를 잃는다.
- 매물 카드(레이아웃 B): 사진 5:3 커버 → 신뢰속성 행(초록 칩+면책) → 차량명 → meta(주행·연료·지역) → 가격 최상위 강조 → 희소옵션 칩(상위 3~4개, 상세는 카테고리 전량). 사진 우하단 "N장" 배지, 없으면 "사진 준비중" 플레이스홀더. 상세는 스와이프 갤러리+"1/N" 카운터.
- 사진 업로드는 OS 갤러리/카메라 네이티브 피커(크롭·회전·동영상은 범위밖), 업로드 전 클라이언트 리사이즈/압축.
- 매물 상세 진입 시 `increment_listing_view` RPC 호출 필요 — 지금은 웹 상세 페이지만 부르므로 앱 전용 세션에서 view_count가 안 오르고 "지금 인기"가 id desc 고정 목록으로 퇴화한다. 웹의 호출 지점 단일성 검사(`viewCountCallSite.test.ts`)와 같은 방식으로 앱도 호출 지점을 하나로 고정(둘이면 한 열람에 2가 오름).

## Cross-Story Dependencies

- **실행 순서(정본=sprint-status.yaml)는 문서 번호와 다르다**: 16.1→16.2→16.3→16.4→16.5→**16.8→16.7→16.6**. 16.6(실폰 통합 검증)은 16.8이 만드는 홈과 16.7이 만드는 업로더가 존재해야 검증이 성립하므로 마지막에 돈다 — 상세 열람 전/후로 "지금 인기" 순서가 실제로 바뀌는 것까지 실폰에서 확인해야 완료다(존재 확인≠작동 확인).
- 16.8은 웹 Epic 11 랜딩(`HeroSearch`·`CategoryChips`·`PopularRecentGrid`)과 확정 목업 `app-home-2.html`을 그대로 따르는 미러 작업, 새로 디자인하지 않는다.
- 16.7은 웹 Story 9.3이 확정한 업로드 계약(경로·저장 규격·삭제 순서·sold 정책)을 그대로 준수, 새 규약을 만들지 않는다.
- 16.1~16.5는 각각 웹 Epic 9(이미지)·10(신뢰속성·찜)·12(실시간 채팅)·13(AI 4분기)이 이미 안정화한 기능을 앱에 옮기는 작업으로, 해당 웹 기능이 선행 조건이다.
