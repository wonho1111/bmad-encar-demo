# Epic 15 Context: 관리자 웹 UI 통일 (UI-only)

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

관리자 웹 6화면(대시보드·회원관리·전체매물·매물상세·거래내역·채팅관리)을 사용자 화면과 동일한 신규 디자인 시스템으로 리스킨하고, PC/모바일 단일 코드 반응형을 적용한다. 이 에픽은 **UI-only**다 — 새 관리 기능이나 운영 배관(스토리지 정리, 미처리 큐, 신고/차단)은 추가하지 않는다. 목적은 운영 도구도 사용자 화면과 같은 수준의 완성도로 보이게 하는 것, 그리고 Epic 14(역할 통합)가 바꾼 데이터 의미를 관리자 UI에 반영하는 것이다. Story 15.4만 예외적으로 DB 변경(복구용 RPC 1개)을 동반한다.

## Stories

- Story 15.1: 관리자 6화면 디자인 리스킨 (+ 소비자 잔여 화면 리스킨 추가범위)
- Story 15.2: 관리자 반응형
- Story 15.3: 회원관리 역할통합 반영
- Story 15.4: 관리자 판매완료 되돌리기 (오조작 복구)

## Requirements & Constraints

- **FR59**: 관리자 6화면을 신규 디자인 토큰(페트롤+앰버 `@theme`, 카드/뱃지/버튼/타이포 위계)으로 리스킨 통일한다. 신규 기능·운영 배관은 범위 밖(다음 증분).
- **FR60**: 관리자 웹은 PC/모바일 브라우저 단일 코드 반응형으로 대응해야 하며, D5 반응형 무결성 규칙(project-context 규칙13)을 예외 없이 지켜야 한다(상세는 UX 절 참조).
- **FR61**: 회원관리 화면의 구매자/판매자 구분 필터를 제거하고 admin/일반 구분으로 교체한다. 이 스토리(15.3)가 FR61 정책을 소유한다(Epic 14는 데이터/게이트만 다룸).
- 기존 관리자 기능(FR22 회원 목록+정지/삭제, FR23 전체 매물 조회+삭제, FR24 거래내역 조회, FR25 채팅방 열람+삭제)은 동작을 유지해야 한다 — 리스킨이 기능을 깨서는 안 된다.
- 관리자 전체매물·매물상세는 이미 존재하는 이미지 데이터를 사용자와 동일한 서명 URL 경로로 렌더한다(신규 이미지 기능 없음, 관리자는 sold 매물도 열람 가능).
- **성공 기준은 선언이 아니라 측정**: 리스킨 후 원시 색상 클래스(`zinc-*`) 잔존 수를 다시 세어 0인지 확인한다.
- 15.1의 추가 범위(사용자 결정 2026-07-29, 대장 `DW-546`)로 소비자 화면 10곳도 같은 작업(토큰 치환 + D5 확인)으로 함께 리스킨한다: `search/SearchFilters`, `sell/PhotoUploader`, `chat/[roomId]/ChatRoomMessages`, `chat/[roomId]/page`, `sell/[id]/edit/page`, `chat/page`, `(auth)/signup/page`, `(auth)/login/page`, `sell/page`, `app/page`. 로그인/회원가입 화면은 이미 상단바가 붙어 있으므로(`DW-547`) 레이아웃은 건드리지 않고 본문 스타일만 다룬다.

## Technical Decisions

- 디자인 토큰: Tailwind v4 `@theme`(CSS-first). brand 페트롤 `#0C6E6B`, accent 앰버 `#DC7A2E`, trust green `#1E8E63`, 다크테마 토큰 별도. 이미지 비율 5:3. 목업 원본은 `ux-designs/admin-web-increment-2026-07-12/admin-mockups-2.html`.
- 반응형은 단일 코드(m-dot 별도 사이트 아님): 카드 그리드→모바일 캐러셀, 필터 사이드바→바텀시트 패턴을 관리자 화면에도 적용.
- 역할 통합 배경: `profiles.role` 컬럼은 존치한다(제거 금지 — `is_admin()`과 기존 관리자 RLS가 의존, 제거 시 관리자 기능 전멸). buyer/seller 값만 의미를 잃고, admin 값만 유지된다. "account_type"은 개념적 명명일 뿐 신규 컬럼이나 rename은 없다 — 회원관리 UI가 "admin/일반 구분"이라 할 때는 `role='admin'` 여부를 뜻한다.
- Story 15.4(판매완료 되돌리기)는 이 에픽의 UI-only 원칙에서 벗어나는 유일한 예외다: `status`만 `sold`→`on_sale`로 되돌리는 좁은 `security definer` RPC 1개가 필요하다. 관리자 UPDATE 정책을 통째로 여는 방식(`listings_update_admin`)은 금지 — `0015_listings_update_not_sold.sql`이 막은 "sold 매물 임의 수정"을 반쯤 되여는 것이기 때문이다. RPC는 `is_admin()`을 내부 확인하고 `status='sold'` 행에만 멱등하게 동작하며, 비관리자 호출이 실제로 거부되는지 데이터로 검증한다. 구현 패턴은 기존 회원관리 정지/해제 토글(`MemberActions.tsx`)의 "실행 → 0행이면 한국어 오류 → `router.refresh()`" 흐름을 따르고, 마이그레이션 동반이므로 배포는 DB 먼저다. 복구 절차는 `docs/` 운영 런북의 "직접 SQL로 복구" 항목을 대체하고 옛 SQL은 비상용 백업으로만 남긴다.

## UX & Interaction Patterns

- D5 반응형 무결성(project-context 규칙13, `DESIGN.md` D5·`EXPERIENCE.md` 브레이크포인트)이 관리자 화면에도 예외 없이 적용된다. 브레이크포인트: ≥1100px=4열, 640~1099px=2열, <640px=1열. 가로 배치 요소(필터 버튼·라벨 등)는 좁아져도 세로로 접지 않고, 넘치면 truncate나 "외 N"으로 축약한다. 카드가 화면 가장자리에서 살짝 잘리는 정도만 허용된다.
- 뷰포트 매트릭스 E2E(Epic 11 감사와 동일 기준)로 D5 무결성을 실제 확인해야 한다 — 규칙이 있다는 것과 실제로 깨지지 않는다는 것은 다르므로 재현 테스트로 닫는다.

## Cross-Story Dependencies

- 15.3은 Epic 14의 role CHECK 완화 마이그레이션이 선행돼야 의미를 가진다 — Epic 14는 데이터/접근제어(role·게이트)만 바꾸고, 관리자 UI 반영(FR61)은 15.3이 단독 소유한다(구 14.4 중복 제거됨).
- 15.1·15.2는 순서상 함께 가는 게 자연스럽다(리스킨 없이 반응형만 먼저 하면 다시 손대야 한다).
- 15.4는 독립적인 DB 변경(RPC 마이그레이션)을 가지므로 착수 시 "UI-only 예외"임을 스펙에 명시해야 한다.
- 15.1의 추가범위(소비자 잔여 화면 리스킨)는 대상 화면이 관리자와 겹치지 않아 병렬 진행 가능하다.
