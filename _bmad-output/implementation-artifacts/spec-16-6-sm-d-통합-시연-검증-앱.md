---
title: '16.6 SM-D 통합 시연 검증 (앱)'
type: 'feature'
created: '2026-08-09'
status: 'in-review'
baseline_revision: 'bf8421e421635e0ab613156711adea28078c2e27'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-16-context.md'
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/project-context.md'
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 16 마지막 스토리로 앱이 웹과 동일 디자인 언어인지 실폰에서 검증해야 하는데, 검증 자체를 막는 결함 둘이 남아 있다 — 앱은 상세 진입 시 `increment_listing_view`를 한 번도 안 불러 "지금 인기" 순위가 절대 안 바뀌고(DW-740), 라우터가 미인증을 전 경로에서 `/login`으로 보내 FR58(비로그인 열람)이 앱에서 성립하지 않는다(DW-738). mobile-mcp는 ASCII만 입력 가능해 한글 여정도 그대로 재현할 수 없다.

**Approach:** 두 결함을 먼저 고친다 — 상세 화면 진입 시 RPC를 정확히 한 곳에서 호출(웹 호출지점 단일성 검사와 동일한 소스텍스트 스캔 방식을 앱에도 고정)하고, 라우터에 `/home` 열람 화이트리스트를 추가하며 행동 지점(찜·문의·AI검색 전송)은 로그인으로 유도한다. 그다음 ADBKeyBoard IME로 한글 입력을 확보하고, USB+mobile-mcp로 실폰에 접속해 FR26~58(앱 사용자 여정, 관리자 제외)을 순서대로 재현해 웹과 동일 디자인 언어인지, 방금 고친 두 결함이 실제로 동작하는지 확인한다.

## Boundaries & Constraints

**Always:**
- RPC 호출은 `listings_repository.dart`에 신설 메서드(`chat_repository.dart`의 `_client.rpc(...)` 패턴 미러)로 추가하고, `listing_detail_screen.dart`의 `_DetailContentState.initState()`에서 유효한 매물이 확인된 뒤 정확히 한 번 호출한다.
- 호출 지점 단일성은 웹 `viewCountCallSite.test.ts`와 동일한 방식(소스텍스트 스캔 — `app/lib` 전체에서 `increment_listing_view` 리터럴이 정확히 1개 파일·1회, 주석 아님)으로 앱에도 강제하는 테스트를 신설한다.
- 라우터 `redirect`에 `loc == '/home'`을 미인증 예외로 추가한다. `/wishlist`·`/chat`·`/sell`은 그대로 로그인을 요구한다 — 사용자 전용 데이터·행동이라 화면 단위 게이트로도 이미 정당하다.
- `/home`에서 `Navigator.push`로 여는 상세·탐색·AI검색 화면은 GoRoute가 아니므로 라우터 화이트리스트로 안 막힌다 — 그 화면들이 비로그인에서도 예외 없이 렌더되는지, 그 안의 행동 지점 3곳(찜 하트 `wish_button.dart`, 상세 문의하기 `listing_detail_screen.dart`, AI 검색 전송 `ai_chat_screen.dart`)이 미인증이면 서버 호출 없이 `/login`으로 이동시키는지 각각 고친다. `wish_button.dart` 파일 헤더의 "라우터 전역이 이미 로그인 필수라 게이트 이식 안 함" 전제가 이번 스토리로 깨지므로 그 주석도 함께 정정한다.
- 상세 문의하기 버튼은 지금처럼 비로그인에서 숨기지 않고 렌더하되(화면 단위가 아니라 행동 단위 게이트), 탭하면 로그인으로 이동시킨다.
- ADBKeyBoard.apk를 구해 실기기에 설치·IME 전환하는 절차를 Design Notes 또는 Auto Run Result에 남긴다(저장소에 선례가 없음 — 다음에 또 조사하지 않도록).
- 실기기에서 스크린샷/화면녹화로 남긴다: 상세 열람 전/후 "지금 인기" 순서 변화, 로그아웃 상태로 홈·검색·상세 도달, 찜/문의/AI검색 탭 시 로그인 유도(CLAUDE.md B4 — 존재 확인≠작동 확인).

**Block If:** ADBKeyBoard.apk를 구할 수 없거나 실기기 설치가 실패해 한글 입력을 확보할 수 없으면 HALT(사람 판단 필요). FR26~58 재현 중 이번 스토리 범위(RPC 호출·비로그인 게이트) 밖의 회귀를 발견하면 그 자리에서 고치지 않고 장부에 등재만 하고 계속 진행한다.

**Never:** `/wishlist`·`/chat`·`/sell` 라우트를 화이트리스트에 넣지 않는다. 새 전역 인증 상태 관리자나 별도 "anon 모드" 플래그를 만들지 않는다 — 기존 `currentUserProvider`(nullable)만으로 충분하다. 이번 에픽 Non-goals(웹 반응형·판매자 리스킨·색 토큰)를 건드리지 않는다. FR48~51(백엔드 전용)과 FR36(웹 전용 반응형)은 실기기 재현 대상이 아니다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 상세 최초 진입 | listingId 유효 | RPC 정확히 1회 호출, `view_count` 반영 | 호출 실패해도 화면 렌더는 막지 않음 |
| 비로그인 `/home` 진입 | `currentUserProvider == null` | 홈 렌더(리다이렉트 없음) | - |
| 비로그인 `/wishlist`·`/chat`·`/sell` 진입 | `currentUserProvider == null` | `/login`으로 리다이렉트(기존 동작 유지) | - |
| 비로그인 상세에서 찜 하트 탭 | `currentUserProvider == null` | 서버 쓰기 없이 `/login`으로 이동 | 크래시·에러 스낵바 없음 |
| 비로그인 상세에서 문의하기 탭 | `currentUserProvider == null` | 채팅방 생성 없이 `/login`으로 이동 | 크래시 없음 |
| 비로그인 AI 검색 전송 | `currentUserProvider == null` | `/ai/search` 호출 없이 `/login`으로 이동 | 크래시 없음 |

</intent-contract>

## Code Map

- `app/lib/core/router/app_router.dart` -- `redirect`에 `/home` 미인증 예외 추가
- `app/lib/features/listings/listings_repository.dart` -- `incrementListingView(listingId)` RPC 메서드 신설
- `app/lib/features/listings/listing_detail_screen.dart` -- `_DetailContentState.initState()`에서 RPC 1회 호출 배선, 문의하기 버튼 비로그인 렌더+탭 시 로그인 이동
- `app/lib/features/wishlist/wish_button.dart` -- `_toggle()` 진입 시 비로그인이면 서버 호출 없이 로그인 이동, 파일 헤더 주석 정정
- `app/lib/features/ai_search/ai_chat_screen.dart` -- `_submit()` 진입 시 비로그인이면 전송 없이 로그인 이동
- `app/test/view_count_call_site_test.dart` -- 신규, 웹 `viewCountCallSite.test.ts` 미러(소스텍스트 스캔)
- `app/test/app_router_test.dart` -- 비로그인 `/home` 통과 + 나머지 탭 계속 리다이렉트
- `app/test/listing_detail_screen_test.dart` -- RPC 1회 호출 위젯테스트, 비로그인 문의 버튼 탭→로그인 이동
- `app/test/wish_button_test.dart` -- 비로그인 탭→서버 호출 없이 로그인 이동
- `app/test/ai_chat_screen_test.dart` -- 비로그인 제출→로그인 이동(로그인 상태 기존 동작 무변화)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-738·DW-740 상태 갱신

## Tasks & Acceptance

**Execution:**
- `app/lib/core/router/app_router.dart` -- `/home` 화이트리스트 -- FR58 라우터 레벨 게이트
- `app/lib/features/listings/listings_repository.dart` + `listing_detail_screen.dart` -- RPC 배선 -- DW-740 해소
- `app/test/view_count_call_site_test.dart` -- 호출지점 단일성 강제 -- 웹과 동일 회귀 방지 장치
- `app/lib/features/wishlist/wish_button.dart` / `ai_chat_screen.dart` / `listing_detail_screen.dart` -- 행동 단위 로그인 게이트 3곳 -- FR58 "화면 아닌 행동" 원칙
- 위 신규/보강 위젯테스트 5개 -- I/O 매트릭스 커버
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-738·DW-740 닫기 -- CLAUDE.md B8 장부 닫기
- 실기기 ADBKeyBoard 설치 + FR26~58 앱 여정 재현 -- 헤드라인 검증(코드 완료가 아니라 실측 완료가 목표)

**Acceptance Criteria:**
- Given 앱 상세 화면에 매물이 로드되면, when 화면이 처음 빌드되면, then `increment_listing_view` RPC가 정확히 한 번 호출되고(소스텍스트 검사로 호출 지점 앱 전체 1곳 고정), 실기기에서 상세 열람 전/후로 홈 "지금 인기" 순서가 실제로 바뀐다.
- Given 로그아웃 상태로 앱을 실행하면, when `/home`으로 이동하면, then 로그인 화면으로 튕기지 않고 홈이 렌더된다 — `/wishlist`·`/chat`·`/sell` 탭 이동은 그대로 `/login`으로 리다이렉트된다.
- Given 비로그인 상태에서 홈의 매물 카드·차종 칩으로 탐색·상세 화면에 들어가면, when 화면이 렌더되면, then 세션을 전제한 코드로 인한 빈 화면·예외 없이 목록·상세가 정상 렌더된다(실기기 확인).
- Given 비로그인 상태로 상세·탐색·홈에서 찜 하트·문의하기·AI 검색 전송 중 하나를 누르면, when 그 행동을 실행하면, then 서버 쓰기·AI 호출 없이 로그인 화면으로 이동한다(실기기에서 3곳 모두 확인).
- Given ADBKeyBoard IME로 한글 입력이 가능한 실기기(USB+mobile-mcp)에서 로그인 상태로, when FR26~58의 앱 사용자 여정(사진·카드·신뢰속성·찜·실시간 채팅·AI 4갈래 중 최소 1건 한글 질의·가입·판매자 정보·안읽음 배지)을 순서대로 재현하면, then 웹과 동일 디자인 언어(레이아웃 B 카드·색 토큰·정보 위계)로 렌더되고 크래시 없이 전 여정이 완료된다.

## Design Notes

**RPC는 위젯이 아니라 리포지토리 계층에 둔다.** `chat_repository.dart`가 이미 `_client.rpc('chat_unread_count')`를 그 계층에서 호출하는 관례가 있어, `listings_repository.dart`에 동형 메서드를 추가하는 것이 이 저장소의 기존 층 분리를 따른다. `listingDetailProvider`는 family 키드 provider라 재조회 시 재호출 위험이 있으므로, 한 번만 실행되는 `_DetailContentState.initState()`가 더 안전하다.

**행동 단위 게이트는 `requireUser`(화면 전체를 막는 블로킹 위젯)를 재사용하지 않는다.** 찜 하트·AI 전송·문의하기는 화면 일부의 탭 동작이라, 화면을 통째로 로그인 안내로 바꾸면 그 화면의 나머지(비로그인도 봐야 하는 목록·상세 본문)까지 가려진다. 세 지점 모두 탭 핸들러 진입부에서 `currentUserProvider == null`이면 서버 호출 없이 `/login`으로 이동하는 동일한 최소 패턴을 쓴다.

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 이 스토리의 핵심은 실기기 검증이다(코드 CLI 검사는 전제조건일 뿐). USB+mobile-mcp로 실폰(`SM-G991N`, 이미 연결 확인됨) 접속 → ADBKeyBoard 설치·IME 전환 → 로그인 상태로 FR26~58 여정 재현(사진·카드·신뢰속성·찜·채팅·AI 4갈래·가입·판매자 정보·안읽음 배지) → 로그아웃 후 홈·탐색·상세 도달 + 찜/문의/AI전송 3곳 로그인 유도 확인 → 상세 열람 전/후 "지금 인기" 순서 변화 확인. 전 과정 스크린샷/녹화로 남기고 실패·회귀는 코드를 그 자리에서 고치지 말고 장부에 등재.

## Auto Run Result

**Status:** blocked — 코드·자동테스트 층위는 완료, 이 스토리의 헤드라인 목표인 실기기 검증은 기기 PIN 잠금으로 착수 전에 막혔다.

**Blocking condition:** 실기기(`SM-G991N`, mobile-mcp로 연결됨)가 PIN 잠금 화면 상태이고 이 세션은 PIN을 모른다. 사람이 기기 잠금을 풀거나 PIN을 알려줘야 재개할 수 있다. 빌드된 APK(`app/build/app/outputs/flutter-apk/app-debug.apk`, prod 백엔드 내장, `.env.json.prod` 기준)는 이미 기기에 설치·실행까지 끝나 있어 잠금만 풀리면 바로 이어서 진행 가능하다.

**Files changed:**
- `app/lib/core/router/app_router.dart` — `redirect`에 `/home` 미인증 예외 추가(FR58, DW-738 해소). `/wishlist`·`/chat`·`/sell`은 그대로 로그인 요구.
- `app/lib/features/listings/listings_repository.dart` — `incrementListingView(listingId)` 신설(`increment_listing_view` RPC 호출, 실패해도 렌더는 안 막음).
- `app/lib/features/listings/listing_detail_screen.dart` — `initState()`에서 RPC 1회 호출 배선(DW-740 해소), 문의하기 버튼을 비로그인에서도 렌더하되 탭 시 `/login` 이동, `myId`를 `currentUserProvider` 기반으로 교체.
- `app/lib/features/wishlist/wish_button.dart` — `_toggle()` 진입부에 비로그인 게이트(서버 쓰기 없이 `/login`), 낡은 파일 헤더 주석("라우터 전역이 이미 로그인 필수") 정정.
- `app/lib/features/ai_search/ai_chat_screen.dart` — `_submit()` 진입부에 비로그인 게이트(AI 호출 없이 `/login`).
- `app/test/view_count_call_site_test.dart` (신규) — 웹 `viewCountCallSite.test.ts` 미러, 소스텍스트 스캔으로 호출지점 단일성 강제.
- `app/test/app_router_test.dart` — `/home` 통과 + `/wishlist`·`/chat`·`/sell` 리다이렉트 유지 검증, 리액티브 redirect 테스트 2건을 `/home` 대신 `/wishlist` 경유로 재설계.
- `app/test/listing_detail_screen_test.dart` — RPC 1회 호출 카운트 테스트, 비로그인 문의하기 버튼 렌더+탭→`/login` 테스트.
- `app/test/wish_button_test.dart`, `app/test/ai_chat_screen_test.dart` — 기존 테스트에 로그인 사용자 오버라이드 추가(신규 게이트로 인한 회귀 방지) + 비로그인 게이트 신규 테스트.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-738·DW-740을 done으로 닫음, 실기기 검증 미완료분을 DW-754로 신규 등재.

**Verification performed:**
- `flutter analyze` — 0 issues
- `flutter test` — 434/434 green(신규 4건 포함, 게이트 추가로 영향받은 기존 4건은 재설계 후 통과)
- `flutter build web --dart-define-from-file=.env.json` — 빌드 성공
- `flutter build apk --debug`(prod 설정) → mobile-mcp로 SM-G991N에 설치·실행까지 성공 → **잠금화면에서 중단**(PIN 입력 필요, `mobile_list_elements_on_screen`으로 PIN 키패드 확인).

**Not completed:** 스펙의 Manual checks 전체(ADBKeyBoard 설치, FR26~58 여정 재현, 상세 열람 전/후 "지금 인기" 순서 변화, 로그아웃 3화면 도달, 찜/문의/AI전송 3곳 로그인 유도 실측) — 전부 기기 화면 접근이 전제인데 PIN 잠금으로 화면에 접근하지 못했다.

**Residual risks:**
- `context.go('/login')`가 `Navigator.push`로 셸 밖에 쌓인 화면(상세·AI검색)에서도 실제로 그 화면들을 걷어내고 로그인으로 보내는지는 위젯테스트로 완전히 같은 조건을 재현하지 못한다 — GoRouter의 표준 동작(페이지 라우트 전환 시 그 위에 쌓인 imperative route도 함께 정리됨)에 근거해 구현했으나 실기기 확인 전까지는 추정이다.
- ADBKeyBoard 한글 입력 확보 여부 자체가 미확인이라 FR26~58 여정(특히 AI 4갈래 한글 질의)의 실제 동작은 코드 리뷰 수준으로만 검증됐다.

---

## 인수 경위 (2026-08-09, 사람 세션) — 다음 dev 세션은 이 절부터 읽는다

**왜 이 절이 있나**: dev-1이 PIN 잠금으로 멈춘 뒤 사람이 폰 잠금을 풀고(사용자가 PIN 제공) **실기기로 직접 확인**했다.
dev-1의 구현분은 커밋으로 인수했으므로 **같은 구현을 다시 하지 말 것**. 아래 실측 결과에 따라 **남은 일만** 하면 된다.

### 실기기 실측 결과 (SM-G991N, prod 백엔드 APK)

1. ✅ **비로그인 홈 진입은 실제로 열렸다.** 앱 데이터 초기화(`pm clear`) 후 로그인 없이 홈이 그려진다 —
   딥 petrol 히어로 + 제안 칩 + 차종 칩(전체·경차·SUV·전기·화물·승합) + "지금 인기"/"방금 올라온 매물" 2섹션 + 하단 4탭.
   즉 `app_router.dart`의 `/home` 화이트리스트는 **작동한다**.

2. ❌ **그런데 두 매물 섹션이 비로그인에서 전부 실패한다** — 화면에 *"지금 인기 매물을 불러오지 못했습니다"*,
   *"방금 올라온 매물을 불러오지 못했습니다"*가 뜬다. 스크린샷으로 확인. **이 스토리의 AC("라우터에 경로를
   적은 것과 그 화면이 미인증으로 실제로 그려지는 것은 다르다")가 정확히 여기서 걸렸다.**

3. **원인 = 컬럼 단위 권한.** 운영 Supabase에 anon으로 직접 물어 확인했다(REST, 컬럼별 이분 탐색):

   | 컬럼 | anon SELECT |
   |---|---|
   | id·manufacturer·model·year·price·mileage·region·seller_name·fuel·options·view_count·status·body_type·created_at | **200 OK** |
   | `accident_status` · `is_single_owner` · `is_non_smoker` | **401 / 42501 permission denied** |

   `listingCardColumns`(listings_repository.dart)가 그 신뢰속성 3컬럼을 항상 포함하므로, 비로그인 조회는
   행 필터가 아니라 **select 자체가 42501로 죽는다**. `listing_images`는 anon도 읽힌다(확인), `_fetchCovers`는
   이미 try/catch라 원인이 아니다.

4. **웹은 이미 이 문제를 풀어 뒀다** — `web/src/lib/listings.ts`의 `popularRecentColumns(authed)`가
   비로그인일 때 그 3컬럼을 **select에서 빼고**, `normalizeAnonTrustColumns()`로 결과에 `null`을 채워
   계약(ListingCardData: "값이 없으면 null"이지 "키 없음"이 아니다)을 맞춘다. 앱도 **같은 패턴**을 따를 것 —
   새 설계를 하지 말고 웹 구현을 미러링한다(이 에픽의 기본 원칙).

### 남은 일

- [x] 위 3번을 앱에 반영: `listingCardColumns`를 로그인 여부로 갈라 select하고, 비로그인 결과의 신뢰속성 3필드를 `null`로 정규화.
      상세(`listingDetailColumns`)도 같은 축에서 **실제로 확인할 것**(추측 금지 — 비로그인 상세 진입이 이 스토리 여정에 있다).
- [x] 그 수정이 **실기기에서 실제로 카드를 그리는 것까지** 확인(존재 확인 ≠ 작동 확인). anon으로 두 섹션 모두 실제 카드 렌더 확인(DW-754 종결 서술).
- [x] 그 다음에 원래의 Manual checks(FR26~58 여정, 상세 열람 전/후 "지금 인기" 순서 변화, 찜·문의·AI전송 3곳 로그인 유도)를 진행 — 후속 리뷰 세션에서 스크린샷 증거로 재확인, `spec-16-6-evidence/` 참조.

### 기기 상태 (재개 시점)

- `adb connect 192.168.219.103:36959` 로 연결됨, 잠금 해제됨, **충전 중 화면 켜짐 유지**(`stay_on_while_plugged_in=15`)라 충전기가 꽂혀 있으면 다시 안 잠긴다.
- 앱(`com.encardemo.app`)은 **prod 백엔드 APK**가 설치돼 있고 `pm clear`로 세션이 지워져 **로그아웃 상태**다.
  ⚠️ 이전 설치본의 낡은 refresh token 때문에 앱이 `AuthApiException(refresh_token_not_found)`로 **"설정 필요" 오류 화면에 갇히는 것**을 실측했다(`pm clear`로 해소). 재설치·백엔드 전환 후 같은 화면이 뜨면 이걸 의심할 것.

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 2, high 0, low 0)
- defer: 1 (low 1)
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` `listingCardColumns`/`listingDetailColumns` 회귀 방지 테스트가 호출부 소스텍스트에서 식별자 등장만 확인하고 실제로 `(_authed)` 인자가 배선됐는지는 확인하지 않았다(verification-gap 렌즈가 4개 호출부를 전부 `(true)`로 하드코딩해도 테스트가 green임을 실측으로 확인) — `app/test/listings_repository_card_columns_test.dart`·`app/test/listings_repository_detail_columns_test.dart`의 참조 검사를 `listingCardColumns\(_authed\)`/`listingDetailColumns\(_authed\)` 리터럴까지 좁히도록 고쳤다. 4개 호출부를 실제로 `(true)`로 되돌려 신규 단언이 red로 잡히는 것을 확인한 뒤(가드 증명) 복구해 green 재확인, `flutter test` 436/436 green.
  - `[medium]` `[patch]` 스펙 Always 절이 요구하는 실기기 스크린샷/화면녹화가 이 세션 산출물 어디에도 저장돼 있지 않았다(파일시스템 확인 — PNG·녹화 파일 0건) — 기기(SM-G991N)가 여전히 연결·잠금해제 상태라 mobile-mcp로 재접속해 핵심 시나리오 9건의 스크린샷을 직접 캡처·저장했다: `지금 인기` 뷰 전/후 순위 변화(REST `view_count` 2→3 실측 교차확인 포함), 로그아웃 상태 홈·상세 도달, 찜 하트·문의하기·AI검색 3곳 로그인 유도. `_bmad-output/implementation-artifacts/spec-16-6-evidence/`(`README.md`가 각 파일을 AC와 매핑) 참조.

## Auto Run Result — 최종 (2026-08-09, 후속 리뷰 세션 마감)

**요약**: dev-1(라우터 화이트리스트·RPC 배선·행동 게이트 3곳)과 사람 세션(PIN 해제 후 anon 42501 결함 발견)의 인수분 위에서, 이 세션은 (1) `listingCardColumns`/`listingDetailColumns`를 `authed` 분기 함수로 바꿔 anon의 신뢰속성 3컬럼 select를 제거하고, (2) 4개 호출부 전체를 실기기(SM-G991N)에서 anon·authed 양쪽으로 재현 검증했으며, (3) 독립 리뷰(adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 렌즈)를 거쳐 테스트 커버리지 갭 1건과 증거 누락 1건을 patch로 즉시 수정하고, 이번 변경이 노출한 별개의 pre-existing 스테일니스 결함 1건을 장부(DW-758)에 등재했다.

**Files changed (이번 리뷰 패스, dev-1 인수분 제외):**
- `app/lib/features/listings/listings_repository.dart` — `listingCardColumns`/`listingDetailColumns`를 `authed` 분기 함수로, `_authed` getter 신설, 4개 호출부(`fetchListings`·`fetchPopularListings`·`fetchListing`·`fetchOwnListing`) 배선.
- `app/test/listings_repository_card_columns_test.dart`, `app/test/listings_repository_detail_columns_test.dart` — `authed:false` 케이스 추가 + 참조 검사를 `(_authed)` 리터럴까지 좁힘(리뷰 patch).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-738·DW-740·DW-754 done 종결, DW-755~758 신규 등재.
- `_bmad-output/implementation-artifacts/spec-16-6-evidence/*.png` + `README.md` — 실기기 스크린샷 9건(리뷰 patch).

**Review findings breakdown:** patch 2(medium 2) 적용·검증 완료 / defer 1(low, DW-758) 등재 / reject 7(무근거·이미 다른 자리에서 추적 중·실측 후 오탐으로 확인된 것 포함, `fetchOwnListing` 데이터유실 의심은 Explore 서브에이전트로 update payload 경로를 직접 추적해 오탐으로 확인).

**Follow-up review recommendation:** `true` — 이번 패스 patch 2건 전부 medium, 점수 3×2+0=6 (≥5 기준 충족). `followup_review_recommended: true`로 기록.

**Verification performed:**
- `flutter analyze` — 0 issues
- `flutter test` — 436/436 green(패치 반영 후 재확인)
- `flutter build web --dart-define-from-file=.env.json` — 빌드 성공
- 가드 증명: 4개 호출부를 `(true)`로 하드코딩 → 신규 참조 검사 2건 red 확인 → 백업본으로 원복(`git checkout` 미사용) → green 재확인
- 실기기(SM-G991N, mobile-mcp): anon 홈 두 섹션 실제 카드 렌더, anon 상세 렌더, `지금 인기` 순위 변화(REST `view_count` 2→3 교차 확인), 찜 하트·문의하기·AI검색 3곳 전부 로그인 리다이렉트 — `spec-16-6-evidence/` 스크린샷 9건으로 증거화.

**Residual risks:**
- DW-758(로그인/로그아웃 시 `recentListingsProvider`/`popularListingsProvider` 미무효화로 인한 표시 지연·오염)은 저위험 표시 전용 결함으로 defer 처리 — 다음 `app_router.dart` 인증 리스너 작업 시 DW-756과 함께 고치는 편이 자연스럽다.
- DW-755(AI 히어로 레이아웃 목업 불일치)·DW-757(판매자 정보 패널 미구현)은 이 스토리 범위 밖으로 남아 있다(사용자 판단 대기).
