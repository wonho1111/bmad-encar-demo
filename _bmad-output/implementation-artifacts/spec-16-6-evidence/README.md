# spec-16-6 실기기 검증 증거 (2026-08-09, 후속 리뷰 세션)

기기: SM-G991N (`192.168.219.103:36959`, mobile-mcp), prod 백엔드 APK(`com.encardemo.app`).
스펙의 `<intent-contract>` Always 절이 요구하는 스크린샷 증거를 이 세션에서 신규 캡처했다 —
이전 세션(dev-1, 인수 경위)의 실측 서술은 상세했으나 이미지/영상 파일이 남아있지 않았다
(파일시스템 전체 검색으로 확인, review 단계에서 patch로 지적됨).

## 1. "지금 인기" 순서 변화 (AC1)

- REST 실측(anon key, `view_count` 직접 조회):
  - 뷰 전: `기아 모닝=17, 제네시스 G70=3, 테슬라 모델3=3, 현대 싼타페=2`
  - `02-detail-santafe-viewed.png`: 싼타페 상세 화면 진입(RPC 1회 호출 트리거)
  - 뷰 후: `현대 싼타페=3`(2→3, 정확히 +1) — G70·테슬라와 동석 → id 역순 tie-break로 싼타페가 G70을 추월
  - `03-popular-after-santafe-rank3-g70-rank4.png`: 홈 재진입 후 실제 화면에서 순위가
    [모닝, 테슬라, **싼타페**, G70] 순으로 바뀐 것을 확인(싼타페가 3위로 올라오고 G70이 4위로 밀림)
  - "before" 스크린샷은 저장하지 못했으나(온스크린 확인만 함), REST 실측 수치(2→3)와
    사용자 계정 `seller-seed3`(G70/테슬라) 대비 `seller-seed2`(싼타페)의 카드 내용이
    03번 스크린샷에서 실제로 뒤바뀐 것으로 교차 확인된다.

## 2. 로그아웃 상태 도달 가능성 (AC2)

- `05-loggedout-home-reachable.png` — 로그아웃 후 앱 재실행, `/login`으로 튕기지 않고 홈이 그대로 렌더.
- `06-loggedout-detail-reachable.png` — 홈에서 매물 카드 탭 → 상세 화면이 크래시·빈 화면 없이 정상 렌더.
- `04-wishlist-tab-still-requires-login.png` — 대조군: `/wishlist` 탭은 스펙 Never 절대로 여전히
  `/login`으로 리다이렉트됨(회귀 아님, 의도된 동작).

## 3. 행동 지점 3곳 로그인 유도 (AC4)

- `07-loggedout-wishheart-redirects-login.png` — 상세 화면 찜 하트 탭 → 서버 호출 없이 `/login` 이동.
- `08-loggedout-inquiry-redirects-login.png` — 상세 화면 "문의하기" 탭 → 채팅방 생성 없이 `/login` 이동.
- `09-loggedout-aisearch-redirects-login.png` — 홈 AI 검색 제안 칩 탭 → AI 호출 없이 `/login` 이동.

## 참고

`01-popular-before.png`는 "전체보기" 탭이 실제로는 매물 탐색(검색) 화면으로 연결된다는 것을
확인하는 과정에서 캡처된 것으로, 로그인 상태에서 신뢰속성 배지(무사고·1인소유)가 정상
렌더되는 것을 보여주는 부가 증거다(지금 인기 순위 자체의 before 컷은 아님).
