---
title: '16.8 앱 홈 랜딩 미러'
type: 'feature'
created: '2026-08-08'
status: 'done'
baseline_revision: 'c33d4cc025f40f928ee940a962b91db8cac90bd5'
final_revision: 'bf35139'
review_loop_iteration: 0  # 후속 리뷰 재진입 시 규정된 리셋(step-01)
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/mockups/app-home-2.html'
  - '{project-root}/web/src/components/landing/HeroSearch.tsx'
  - '{project-root}/web/src/components/landing/CategoryChips.tsx'
  - '{project-root}/web/src/components/landing/PopularRecentGrid.tsx'
  - '{project-root}/web/src/lib/listings.ts'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 앱 홈이 웹 랜딩(Epic 11: 히어로·차종칩·인기/최신 그리드)의 정보구조를 물려받지 않았고, 하단 4탭과 목적지가 겹치는 Epic 7 잔재 퀵액션 3개(문의 채팅·매물 등록·내 매물 관리)가 남아 있다(DW-736) — 시연에서 가장 먼저 보이는 화면이 웹과 다른 서비스처럼 보인다.

**Approach:** 웹 Epic 11 구현(`HeroSearch`·`CategoryChips`·`PopularRecentGrid`)과 확정 목업(`app-home-2.html`)을 정본으로 홈을 재구성한다 — 히어로(실 입력+제안칩), 차종 칩 줄, "지금 인기"·"방금 올라온 매물" 2섹션을 추가하고, 퀵액션 3개를 **같은 커밋**에서 제거한다.

## Boundaries & Constraints

**Always:**
- 퀵액션 3개(`Key('go_chat')`·`Key('go_sell')`·`Key('go_my_listings')`) 제거와 새 섹션 추가는 반드시 같은 커밋(먼저 지우면 판매자가 매물 등록에 갈 길이 막힌다 — DW-728 순서).
- 인기=`view_count desc`, 최신=`created_at desc`, 각 4건, `id`를 2차 정렬키로(웹 `fetchPopularAndRecentListings`/`POPULAR_RECENT_GRID_COUNT` 미러).
- 차종 칩은 웹 `CategoryChips.tsx`의 `CATEGORY_CHIPS`와 값·순서 바이트 일치: 전체(무필터)/경차(`body_type='경차'`)/SUV(`body_type='SUV'`)/전기(`fuel='전기'`)/화물(`body_type='화물차'`)/승합(`body_type='승합차'`).
- 히어로 제안 칩은 웹 `HeroSearch.tsx`의 `SUGGESTIONS` 4개 그대로: "가성비 좋은 첫차"·"4천만원대 전기 SUV"·"주행거리 짧은 무사고 세단"·"7인승 디젤 패밀리카".
- 기존 `Key('go_ai')`·`Key('go_search')`는 유지한다(기존 `home_ai_entry_test.dart` 무파괴).
- 순서·개수를 좌표·개수로 단언하는 위젯테스트를 추가하고, 채택 전 일부러 순서를 뒤집어 red를 확인한 뒤 되돌려 green을 확인한다(히어로 > 차종칩 > 지금인기 > 최신, 퀵액션 3개 개수=0).
- "지금 인기" 조회 실패는 그 섹션에만 에러 문구를 보이고 히어로·차종칩·"방금 올라온 매물"은 정상 렌더된다(웹 `fetchSection`의 단별 독립 에러 격리 미러).

**Block If:** 없음 — 아래 Never의 두 항목이 이번 스토리 착수 전 사용자 결정(2026-08-08)으로 이미 해소됐다.

**Never:**
- 웹 랜딩 재작업 · 판매자 화면(매물 등록·내 매물 관리) 리스킨 · 색 토큰 작업(DW-729로 기해소) — Epic 16 어느 스토리의 범위도 아니다.
- "세단"·"수입" 차종 칩을 추가하지 않는다 — 목업엔 있지만, DB `body_type` CHECK에 "세단" 단일 값이 없고(준중형·중형·대형 3종에 걸침) "수입"은 원산지 컬럼 자체가 없다. 웹이 이미 같은 이유로 의도적으로 뺐다(`CategoryChips.tsx` 주석, CLAUDE.md B9 "라벨과 다른 결과가 나오는 칩을 만들지 않는다"). 사용자 결정(2026-08-08)으로 웹과 동일한 6개 칩을 따른다.
- `Key('go_search')`(_SearchCta)는 제거하지 않는다 — AC가 명시한 제거 대상 3개에 없다(surgical, CLAUDE.md A3).
- 새 필터 컬럼·RPC·"수입" 판정 로직을 추가하지 않는다. 기존 `body_type`/`fuel` 값만 쓴다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 차종 칩 정상 | 차종 칩("SUV") 탭 | `SearchScreen`이 `body_type=SUV`로 즉시 필터링된 결과를 보여준다(수동 검색 버튼 없이) | No error |
| 인기 조회 실패 | `popularListingsProvider` 에러 | "지금 인기" 섹션만 에러 문구, 히어로·차종칩·"방금 올라온 매물"은 정상 렌더 | 섹션별 독립 격리 |
| 필터 진입 경합 | 카테고리 칩으로 `SearchScreen`에 이번 세션 첫 진입(provider 첫 빌드와 겹침) + 빈 필터 초기조회 응답이 필터 조회 응답보다 늦게 도착 | 최종 화면은 필터링된 결과를 보여준다(늦게 온 빈 필터 응답이 덮어쓰지 않는다) | 레이스 방어 필요 |
| 제안 칩 탭 | 히어로 제안 칩("4천만원대 전기 SUV") 탭 | `AiChatScreen`이 그 문장으로 이미 제출을 시작한 상태로 열린다(입력창에 채우기만 하고 안 보내는 게 아니다) | No error |

</intent-contract>

## Code Map

- `app/lib/features/auth/home_screen.dart` -- `_AiSearchCta`를 실 입력+제안칩 히어로로 확장(Key('go_ai') 유지), 차종 칩 줄 신설, "지금 인기" 섹션 신설, "최근 매물"→"방금 올라온 매물" 헤더 개칭(`recentListingsProvider` 재사용), 퀵액션 3개(go_chat/go_sell/go_my_listings)와 그 전용 `_QuickAction` 클래스 제거
- `app/lib/features/listings/listings_repository.dart` -- `fetchPopularListings({int limit = 4})` 신설(`view_count desc, id desc` + `.limit()`, 기존 `_fetchCovers`/`attachCoverImages` 재사용)
- `app/lib/features/listings/listings_providers.dart` -- `popularListingsProvider` 신설(`FutureProvider.autoDispose`, `recentListingsProvider`와 동형)
- `app/lib/features/listings/search_screen.dart` -- `initialBodyType`/`initialFuel` 생성자 파라미터 추가, `initState`에서 값이 있으면 즉시 필터링 조회
- `app/lib/features/ai_search/ai_chat_screen.dart` -- `initialQuery` 생성자 파라미터 추가, `initState`에서 값이 있으면 기존 `_submit(overrideQuery:)` 경로로 자동 제출
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-736 status를 closed로 갱신
- `app/test/home_ai_entry_test.dart` -- 히어로>차종칩>지금인기>최신 좌표 단언, 퀵액션 3개 개수=0 단언 추가
- `app/test/home_screen_wishlist_test.dart` -- 신규 `popularListingsProvider` 오버라이드 추가(기존 `recentListingsProvider` 오버라이드와 동형)
- `app/test/search_screen_test.dart` -- `initialBodyType`/`initialFuel` 즉시조회 + 초기조회-필터조회 레이스 테스트 추가
- `app/test/ai_chat_screen_test.dart` -- `initialQuery` 자동 제출 위젯테스트 추가

## Tasks & Acceptance

**Execution:**
- `app/lib/features/listings/listings_repository.dart` -- `fetchPopularListings` 신설 -- 인기 섹션의 유일한 데이터 출처
- `app/lib/features/listings/listings_providers.dart` -- `popularListingsProvider` 신설 -- 화면이 소비할 Riverpod 진입점
- `app/lib/features/listings/search_screen.dart` -- 초기 필터 파라미터+즉시조회 -- 차종 칩 탭의 목적지 계약
- `app/lib/features/ai_search/ai_chat_screen.dart` -- `initialQuery` 자동 제출 -- 히어로 입력·제안 칩의 목적지 계약
- `app/lib/features/auth/home_screen.dart` -- 히어로 확장+차종칩+지금인기+최신 개칭+퀵액션 3개 제거(같은 커밋) -- 헤드라인 기능
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-736 닫기 -- CLAUDE.md B8 장부 닫기
- `app/test/home_ai_entry_test.dart` -- 순서·개수 위젯테스트 -- I/O 매트릭스 밖 구조 요구사항 커버
- `app/test/home_screen_wishlist_test.dart` -- provider 오버라이드 추가 -- 기존 테스트가 실 네트워크를 안 타게
- `app/test/search_screen_test.dart` -- 즉시조회+레이스 위젯테스트 -- I/O 매트릭스 커버
- `app/test/ai_chat_screen_test.dart` -- 자동 제출 위젯테스트 -- I/O 매트릭스 커버

**Acceptance Criteria:**
- Given 앱 홈을 열면, when 렌더되면, then 딥 petrol 히어로(실 입력+amber 검색 버튼+"말"만 amber 강조 헤드라인+제안 칩 4개)가 최상단에, 그 아래 차종 칩 줄이, 그 아래 "지금 인기"·"방금 올라온 매물" 2섹션이 이 순서로 렌더된다(좌표로 단언).
- Given 차종 칩을 탭하면, when 탐색 화면이 열리면, then 해당 필터(body_type 또는 fuel, "전체"는 무필터)로 이미 조회된 결과가 보인다.
- Given "지금 인기"·"방금 올라온 매물" 각 섹션, when 렌더되면, then 웹과 같은 정렬·건수(인기=view_count desc, 최신=created_at desc, 각 4건)이고 "전체보기"가 탐색 화면으로 이어진다.
- Given Epic 7 퀵액션 3개(go_chat/go_sell/go_my_listings), when 홈이 렌더되면, then 어디에도 없다(개수 0으로 단언되고, 새 섹션 추가와 같은 커밋에서 제거됐다).
- Given 히어로 제안 칩을 탭하면, when 제출되면, then 그 문장으로 AiChatScreen이 이미 조회를 시작한 상태로 열린다(직접 타이핑 제출과 동일 파이프라인).

## Spec Change Log

## Review Triage Log

### 2026-08-08 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 1, medium 3, low 8)
- defer: 0
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` 퀵액션 3개(go_chat/go_sell/go_my_listings) 제거 후 `MyListingsScreen`(내 매물 관리)으로 가는 경로가 앱 전체에 하나도 안 남았다(adversarial·edge-case-hunter 독립 발견, `grep -rn MyListingsScreen app/lib` 실측 — 정의 파일 자신 말고 0건). 웹은 이 화면을 상단 프로필 메뉴(`SiteNav.tsx:197` "내 매물 관리")에 두고 있다 — 앱도 이미 같은 자리(Story 16.1이 만든 `app_router.dart`의 `PopupMenuButton` 프로필 아바타 메뉴)가 있으므로, 거기에 `PopupMenuItem`을 추가해 `MyListingsScreen`으로 연결한다(웹과 동일 정보구조, 새 화면·새 위치 발명 아님).
  - `[medium]` `[patch]` 당겨서 새로고침이 `Future.wait([recentListingsProvider, popularListingsProvider])`로 두 provider를 묶어, 웹 `fetchSection`이 지키는 "한 섹션 실패가 다른 섹션·전체 화면을 안 죽인다" 원칙을 새로고침 경로에서만 어긴다(adversarial·edge-case-hunter·verification-gap 3개 레이어 독립 발견, 이 경로를 실행하는 테스트 자체가 0건이었다). 두 refresh를 각각 독립적으로 감싸(또는 `eagerError:false`) 한쪽 실패가 다른 쪽·onRefresh 자체를 막지 않게 하고, 실제로 한쪽만 실패시켜 다른 섹션이 정상 렌더되는지 확인하는 위젯테스트를 추가한다.
  - `[medium]` `[patch]` `SearchScreen.initState`의 `Future.microtask` 콜백에 `mounted` 가드가 없다(edge-case-hunter 발견) — 그 마이크로태스크가 실행되기 전에 화면이 dispose되면(예: 칩 탭 직후 빠르게 뒤로가기) disposed 상태의 `ConsumerState`에서 `ref.read`/`setState`를 호출해 예외가 난다. 콜백 맨 앞에 `if (!mounted) return;`을 추가한다.
  - `[medium]` `[patch]` `docs/conventions.md` §6(FR11 판매완료 비노출 강제 지점 목록)이 이 프로젝트 자신의 규칙(새 조회 경로를 열면 이 목록에 추가한다)에도 불구하고 이번에 신설된 `fetchPopularListings`→`_fetchCovers` 소비처를 안 담고 있다(adversarial 발견) — 이 문서 자신이 과거 이미지 축 드리프트 사고를 이 누락 패턴으로 겪었다고 기록해 뒀다. §6 목록에 `fetchPopularListings`(홈 "지금 인기" 섹션)를 세 번째 앱 소비처로 추가한다.
  - `[low]` `[patch]` `SearchController.search()`의 요청-경합 방어(`requestId` 카운터)가 성공 응답 분기(patch 대상 아님, 이미 정상)와 실패(에러) 응답 분기 두 곳에 각각 들어 있는데, 새 레이스 테스트(`_RaceFakeRepository`)는 성공 쪽 경합만 재현하고 에러 분기는 어떤 테스트도 거치지 않는다(verification-gap 발견). 뒤늦게 도착한 스테일 응답이 에러로 완료되는 경우에도 이미 반영된 최신 성공 데이터가 안 덮이는지 확인하는 테스트를 추가한다.
  - `[low]` `[patch]` `app/lib/features/listings/sell_screen.dart` 상단 주석이 "이 화면은 두 자리에서 쓰인다 — ① ... ② `home_screen.dart`의 '매물 등록' 퀵액션"이라 적고 있는데 이번 diff가 그 퀵액션 자체를 지웠다(adversarial 발견) — 주석이 이미 사라진 진입점을 정본처럼 가리킨다. 그 문구를 실제로 남은 진입점(내차팔기 탭)으로 정정한다.
  - `[low]` `[patch]` 히어로 입력창의 `TextEditingController`가 제출 후에도 안 비워져, `AiChatScreen`에서 뒤로가기로 홈에 돌아오면 방금 검색한 문장이 그대로 남아 있다(adversarial 발견). 제출 성공 경로에서 컨트롤러를 `clear()`한다.
  - `[low]` `[patch]` 히어로 검색이 빈 문자열/공백만 입력해도 조용히 아무 일도 안 하는 기존 관례(`AiChatScreen._submit`·웹 `HeroSearch.submit`과 동일)를 이번에 새로 만든 히어로 제출 경로도 그대로 따르는데, 이 가드가 실제로 동작하는지 확인하는 테스트가 없었다(adversarial·edge-case-hunter 독립 발견). 동작 자체(조용한 무시)는 기존 관례와 일치하므로 바꾸지 않고, 공백만 입력했을 때 `AiChatScreen`으로 넘어가지 않는지 확인하는 테스트만 추가한다.
  - `[low]` `[patch]` 제안 칩 위젯이 `AppColors.onPetrol`(이미 정의된 토큰, 값은 흰색) 대신 `Colors.white.withValues(...)` 원시 리터럴을 직접 쓴다(adversarial 발견) — 나중에 petrol 배경 위 잉크 색 토큰만 바꾸면 되는 상황에서 이 리터럴이 누락되기 쉬운 토큰-드리프트 시작점이다. 기존 토큰(`AppColors.onPetrol`)을 재사용하도록 교체한다.
  - `[low]` `[patch]` 차종 칩 줄의 탭 영역 높이가 36px로 Material 접근성 권장 최소 터치 타깃(48dp)보다 작다(adversarial 발견). 히트테스트 영역을 48 이상으로 넓힌다(시각적 칩 높이는 유지하고 패딩으로 확장).
  - `[low]` `[patch]` 상위 계획 문서 `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`의 Story 16.8 AC 원문이 아직도 "전체·경차·세단·SUV·전기·수입"을 그대로 담고 있어, 이번에 사용자와 함께 확정한 실제 구현 값(전체·경차·SUV·전기·화물·승합)과 문서상 어긋난다(intent-alignment 발견) — 이 문서 자신이 이미 쓰고 있는 "✎ 정정" 각주 관례(Story 16.6 절 참고)로 차종 칩 목록을 실제 구현값으로 정정하고 근거(DB에 세단·수입 1:1 필터 값 없음, 웹이 이미 화물·승합으로 대체)를 남긴다.
  - `rejected_as_noise` (기록용, 근거 포함):
    - `deferred-work.md`의 신규 DW 항목이 "이번 변경이 만든 결함이 아니다"를 CanvasKit 에러 문자열이 이전 스토리(spec-16-4·16-5)와 같다는 것만으로 단정한다(adversarial 발견, 더 좁혀서 재현해 보라는 요구) — 이 정확히 같은 에러가 서로 다른 위젯 트리를 가진 두 개의 선행 스토리에서 이미 재현됐고, 이 스토리의 스펙 자신이 "CLI가 안 되면 대장에 등재하고 위젯테스트로 대체 확인한 사실을 명시한다"는 폴백을 사전 승인했다 — 추가로 좁혀 재현해도 이미 두 번 확인된 "이 샌드박스의 환경 한계"라는 결론이 바뀔 가능성이 낮아 한계효용이 낮다.
    - `AiChatScreen`의 `initState`가 `didUpdateWidget`으로 `initialQuery` 변경에 재반응하지 않는다(edge-case-hunter 발견) — 이 화면은 이 diff를 포함해 앱 전체에서 항상 `MaterialPageRoute`로 매번 새 위젯 인스턴스로 push되고, 기존 State를 유지한 채 `initialQuery`만 바뀌는 호출 경로가 코드베이스 어디에도 없다(실측: 이 diff와 기존 호출부 전수 확인). 도달 불가능한 시나리오용 방어는 넣지 않는다(CLAUDE.md A2).

### 2026-08-08 — Review pass (후속, followup_review_recommended: true로 재진입)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 1, medium 5, low 7)
- defer: 3 (high 0, medium 0, low 3)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` **"전체" 칩이 무필터가 아니었다** — `search_screen.dart`의 `initState`가 `initialBodyType`·`initialFuel`이 둘 다 null이면 조기 return했는데, `searchControllerProvider`는 non-autoDispose 전역 싱글턴이라 빈 필터 초기조회가 앱 생애 1회만 돈다. 그래서 "SUV 칩 → 뒤로 → 전체 칩" 순서면 필터 패널은 "전체"인데 목록은 SUV 결과가 그대로 남았다(AC2 정면 위반, 스펙 Never가 인용한 CLAUDE.md B9 "라벨과 다른 결과가 나오는 칩 금지"를 스스로 어김). adversarial·edge-case-hunter·verification-gap 3개 레이어 독립 발견. 조기 return을 걷어내 "전체"도 빈 필터로 명시 리셋+재조회하게 했고(기존 경합 방어·`mounted` 가드는 그대로), SUV 상태 뒤 무필터 재진입 테스트를 추가해 red→green 확인.
  - `[medium]` `[patch]` **프로필 메뉴 "내 매물 관리" push가 홈 목록 무효화를 잃었다** — 지난 패스가 되살린 대체 진입점에, 제거된 `go_my_listings` 퀵액션이 달고 있던 `.then((_) => ref.invalidate(recentListingsProvider))`가 옮겨지지 않았다. `rootNavigator` push의 pop은 셸의 `onActivate`도 안 태우므로 구매완료·삭제 후 홈 두 섹션에 그 매물이 계속 남았다(3개 레이어 독립 발견). 두 provider를 함께 무효화하도록 복원하고 재조회 횟수 카운팅 테스트로 red→green 확인.
  - `[medium]` `[patch]` **홈 탭 `onActivate`가 신규 `popularListingsProvider`를 빠뜨렸다** — 홈 브랜치는 `StatefulShellRoute` IndexedStack으로 영구 마운트라 autoDispose가 무력화된다(그 함정은 `app_router.dart` 자신이 문서화해 둔 것). 결과적으로 "지금 인기"는 앱 실행당 1회만 조회됐다. 당겨서 새로고침 경로는 이미 두 provider를 같은 계약으로 다루고 있어 한쪽만 빠진 상태였다. 무효화 추가 + 카운팅 테스트로 red→green 확인(하네스의 고정 오버라이드를 덮을 escape 파라미터 추가 필요).
  - `[medium]` `[patch]` **신설 `fetchPopularListings`를 보는 검사가 0건이었고, 카드 select 12컬럼 리터럴이 `fetchListings`와 중복 복사돼 있었다** — §4.1 락스텝으로 ListingCard 필드가 늘 때 한쪽만 고치면 "지금 인기" 카드만 조용히 필드를 잃는다(이 저장소가 상세 컬럼에서 이미 겪고 닫은 실패 모드). 그 선례 그대로 `listingCardColumns` 상수로 합치고, 두 메서드가 실제로 그 식별자를 참조하는지 + `fetchPopularListings`가 `_buyerQuery`(FR11 강제 지점)·`view_count desc`·`id desc`·`limit`(기본 4, AC3 계약)을 쓰는지 소스텍스트로 단언하는 테스트 신설.
  - `[medium]` `[patch]` **차종 칩·제안 칩 상수가 어떤 화이트리스트에도 묶여 있지 않았다** — 웹은 `LISTING_OPTIONS`에서 뽑은 유니언 타입으로 tsc가 막지만 앱은 생 문자열이고, `ResolvedFilters.fromInput`의 `pickOption`이 목록 밖 값을 조용히 null로 떨어뜨린다. 즉 `'화물차'`를 `'화물'`로 오타 내면 그 칩이 **전체 매물**을 보여주는데(스펙 Never가 금지한 바로 그 상태) 전 스위트가 green이다. 실제로 테스트가 만지는 칩은 6개 중 1개, 제안칩은 4개 중 1개뿐이었다. 두 상수를 테스트에 노출하고 라벨·순서·`ListingOptions` 소속·제안칩 4문장을 단언하는 계약 테스트 신설.
  - `[medium]` `[patch]` **지난 패스가 고친 드리프트를 같은 커밋이 옆 파일에 재생산했다** — `epic-16-context.md`가 차종 칩을 아직 "전체·경차·**세단**·SUV·전기·**수입**", 제안 칩을 목업 3개로 적고 있었다(`epics-increment`에는 "✎ 정정"이 들어간 바로 그 값). 이 파일은 다음 스토리 16.7·16.6이 읽는 입력이라 잘못된 지시가 다시 내려올 자리다. 같은 "✎ 정정" 관례로 실제 구현값과 근거를 심었다.
  - `[low]` `[patch]` `docs/conventions.md` §6에서 서수가 충돌했다 — 158행을 "앱이 연 **세** 경로"로 늘렸는데 159행이 여전히 "앱이 연 **세 번째** 경로(16.3)"라 3번이 둘이었다. 이 목록은 FR11 강제 지점 대장이라 서수가 어긋나면 다음 사람이 자기 경로의 등재 여부를 판단 못 한다. "네 번째"로 정정.
  - `[low]` `[patch]` 제거된 홈 퀵액션을 **현존 진입점처럼** 가리키는 주석이 5곳 남아 있었다(`sell_screen.dart` 3곳·`sell_controller.dart`·`app_router.dart`) — 지난 패스는 `sell_screen.dart` 파일 헤더 한 곳만 고쳤다. 특히 "등록 모드 화면이 동시에 둘"이라는 방어 로직의 전제를 없어진 진입점으로 설명하고 있었다. 살아있는 진입점(`my_listings_screen.dart`의 수정 push는 실제로 살아 있음 — grep 실측)으로 정정했고, 방어 로직 자체는 여전히 유효하므로 지우지 않고 사실대로 다시 적었다.
  - `[low]` `[patch]` 히어로 입력에 **500자 상한이 없었다** — 웹 `HeroSearch.tsx`는 `maxLength={500}` + 제출 시 `.slice(0,500)` 이중 방어인데(제안칩이 입력 경로를 우회하므로 둘 다 필요하다고 그 파일이 명시), 앱은 둘 다 없었다. 초과 입력 시 `AiChatScreen`은 에러 문구만 띄우고 `overrideQuery` 경로라 입력 복원도 안 하며 히어로는 이미 `clear()`한 뒤라 **원문이 어디에도 안 남는다**. 기존 `maxQueryLength` 상수를 재사용해(새 상수 안 만듦) 입력 상한 + 제출 시 절단으로 미러.
  - `[low]` `[patch]` 히어로 제안 칩 터치 타깃이 약 30px로 48dp 미만이었다 — 지난 패스가 **같은 파일에서** 차종 칩만 48로 고쳐, 한 화면 안에서 접근성 기준이 위젯마다 달랐다. 차종 칩과 같은 방식(시각 알약 크기 유지, 히트 영역만 패딩으로 확장)으로 맞춤.
  - `[low]` `[patch]` `_refreshQuietly`가 실패를 **로그 한 줄 없이** 삼켰다 — 미러 원본이라고 주석이 인용한 웹 `fetchSection`은 같은 자리에서 `console.error`를 남긴다. 섹션 위젯의 `AsyncValue.error`로 안 드러나는 종류의 실패는 흔적 없이 사라진다. 저장소가 이미 쓰는 `debugPrint` 스타일로 실패 사실만 남기고 예외는 계속 삼킨다.
  - `[low]` `[patch]` `Key('go_ai')`가 이제 **탭 불가능한 `Container`**(히어로 밴드)에 붙어 있어 이름과 동작이 어긋났다(실제 진입은 `hero_search_button`·`hero_suggestion_*`). 다음 사람이 `tap(go_ai)`로 진입을 검증하는 테스트를 쓰면 조용히 아무 일도 안 일어나고 그걸 통과로 읽는다. 키 옆에 "존재·좌표 확인용 앵커이지 탭 대상이 아니다"를 명시(개칭은 테스트 3곳을 함께 건드려야 해 A3 기준 과함).
  - `[low]` `[patch]` **미검증 가드 2건에 검사를 붙였다** — 지난 패스의 `mounted` 가드는 지워도 전 스위트가 green이었고, Code Map이 약속한 `initialFuel`(전기 칩) 즉시조회 경로는 어떤 테스트도 밟지 않았다. `initialFuel` 테스트는 추가해 red→green 확인. ⚠️ `mounted` 가드는 **red 증명에 실패했고 그 사실을 테스트 옆에 적었다** — `AutomatedTestWidgetsFlutterBinding.pump()`가 같은 `pump()` 안에서 `handleDrawFrame()` 직후 `flushMicrotasks()`를 무조건 부르므로, `initState`가 건 마이크로태스크는 그 `pumpWidget` 호출이 반환되기 전에 반드시 실행된다 → 이 프레임워크의 `pumpWidget`/`pump` 의미론으로는 "마이크로태스크 실행 전 dispose"를 만들 수 없다. 즉 이 가드는 지금 **검사로 고정되지 않은 방어 코드**다(CLAUDE.md B4 "검사가 안 보는 것을 검사 옆에 적는다").
  - `[low]` `[patch]` `deferred-work.md`의 16.8 항목이 `flutter test` 건수를 **334**로, 스펙 Auto Run Result는 **339**로 적어 같은 실행에 대한 두 기록이 갈렸다(최소 하나는 실행 출력이 아니라 기억에서 적힌 것). ⚠️ **이 건만 수정을 적용하지 않았다** — 이번 호출 지시가 "장부에는 신규 항목만 추가, 기존 항목은 수정·재개방·재작성 금지(상태와 해소는 오케스트레이터 소유)"이므로 기존 항목을 고칠 권한이 이 실행에 없다. 대신 **직접 재실행해 확인한 실제 값 349**를 아래 Verification performed에 기록한다. 장부 항목의 숫자 정정은 오케스트레이터 판단으로 남긴다.
  - `deferred` (신규 3건, 전부 선재 — 이 스토리가 만든 것이 아님):
    - `DW-737` 홈 "방금 올라온 매물"이 웹의 SQL `.limit(4)`와 달리 on_sale 전량을 받아 Dart에서 `take(4)`한다(`recentListingsProvider` 재사용의 결과, 보이는 4건은 동일).
    - `DW-738` 앱은 모든 경로에서 미인증을 `/login`으로 보내는데 에픽 요구사항은 "비로그인 매물 열람 가능"을 요구한다 — 16.6 검증자가 확인할 수 없는 요구사항이 문서에 남아 있다.
    - `DW-739` `MyListingsScreen` → 매물 수정(`SellScreen`) push의 셸 경계 테스트가 없다 — 같은 실패 모드(AppBar 2개)를 다른 진입점에서는 이미 검사한다.
  - `rejected_as_noise` (기록용, 근거 포함):
    - `sprint-status.yaml`의 `16-8: done`이 커밋되지 않은 워킹트리 변경이다(adversarial 발견) — 사실이지만 이 파일은 오케스트레이터 소유이고, step-04는 리뷰 diff 밖 워킹트리 변경을 "그대로 두고 잔여 산출물로 보고하라"고 규정한다. 아래 Residual risks에 남긴다.
    - front-matter `review_loop_iteration: 0`인데 본문에 리뷰 기록이 있다(adversarial 발견) — 워크플로 규정상 `done` 스펙을 후속 리뷰로 재진입할 때 이 카운터를 0으로 리셋한다(step-01). 오작동이 아니라 규정된 동작이다.
    - 지난 패스의 신규 장부 항목이 `### DW-<번호>` 헤더 없이 불릿 형식이라 장부 훑기에서 빠진다(adversarial 발견) — 지적 자체는 project-context.md 규정과 맞고, **이번 신규 3건은 `### DW-` 형식으로 등재했다.** 다만 기존 항목의 재포맷은 위와 같은 이유(오케스트레이터 소유)로 이 실행의 권한 밖이라 손대지 않았다.
    - 제안 칩·차종 칩을 빠르게 두 번 탭하면 화면이 2장 쌓이고 `/ai/search`가 2회 호출된다(edge-case-hunter 발견) — 이 앱의 어떤 push 진입점에도 연타 가드가 없어(일관된 기존 관례) 여기만 넣으면 오히려 규칙이 갈린다. 두 번째 화면은 첫 화면 위에 즉시 쌓여 뒤로가기 한 번으로 정리되고, 데모 데이터 규모에서 과금 영향은 무시할 수준이다(CLAUDE.md A2 — 요청 밖 방어 금지).

### 2026-08-09 — Review pass (3차, followup_review_recommended: true로 재진입)
- intent_gap: 0
- bad_spec: 0
- patch: 20 (high 0, medium 10, low 10)
- defer: 1 (high 0, medium 0, low 1)
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` **히어로가 자동 제출한 질의가 실패하면 사용자 원문이 어디에도 안 남았다** — 홈이 `_controller.clear()`로 입력을 버리고, `AiChatScreen`은 낙관적 user 버블을 `_messages.removeLast()`로 걷어내며, 실패 롤백 `if (overrideQuery == null) _input.text = query;`가 `overrideQuery` 경로라 복원을 건너뛴다. 2차 패스가 500자 초과 케이스에 대해 진단했던 "원문이 어디에도 안 남는다"와 같은 결과가 **일반 네트워크 실패 경로**에 그대로 있었다. `_submit`에 `restoreInputOnFailure`를 더해 히어로 자동 제출 실패만 입력을 복원한다(화면 안 되묻기 칩 탭의 초안 보존 동작은 테스트로 고정돼 있어 그대로 둠).
  - `[medium]` `[patch]` **칩 상수 계약 테스트가 웹이 아니라 자기 사본과 대조하고 있었다** — Always가 요구한 것은 "웹 `CategoryChips.tsx`·`HeroSearch.tsx`와 바이트 일치"인데, 2차 패스가 신설한 `home_chips_contract_test.dart`는 같은 파일 안의 또 다른 Dart 리터럴과 비교해 **웹이 칩을 바꾸면 앱은 계속 green**이었다. 이 저장소가 project-context.md에 "요약이 원본보다 늙어 틀린 값이 주입됐다(3건 실측)"고 적어 둔 실패 모드의 재도입이다. 이미 있는 선례(`app_theme_color_drift_test.dart`가 웹 CSS를 `File`로 직접 읽고, 못 읽으면 폴백 없이 실패)를 따라 웹 두 파일을 실제로 파싱해 대조하도록 바꿨다. red 확인 2종: 앱 상수 변조 → red, 웹 파일 경로 차단 → red(조용히 통과하지 않음).
  - `[medium]` `[patch]` **프로필 메뉴의 `.then` 무효화가 생애주기 가드 없이 `ref`를 쓴다** — `flutter_riverpod` 3.3.2의 `_assertNotDisposed()`는 assert가 아니라 **모든 빌드 모드에서 `StateError`를 던진다**. `MyListingsScreen`이 열려 있는 동안 세션 만료·로그아웃이 나면 `app_router.dart` 자신의 redirect가 셸(=이 버튼)을 파괴하고, 뒤이은 pop이 이 콜백을 깨운다. `onError`가 없어 미처리 비동기 예외로 샌다. 같은 커밋이 `search_screen.dart`에는 `if (!mounted) return;`을 넣어 둔 자리라 규칙이 갈려 있었다. `wish_button.dart`가 이미 쓰는 방식(await 전에 `ProviderScope.containerOf`를 잡아 둠)으로 통일.
  - `[medium]` `[patch]` **히어로가 제안 칩 탭에서도 입력창을 비웠다** — 사용자가 타이핑해 둔 초안이 칩 한 번에 사라진다. 이 저장소는 바로 아래 계층에서 **정반대 결론을 이미 확정**해 뒀다(`ai_chat_screen.dart`의 `if (overrideQuery == null) _input.clear();` + "칩 탭 전 초안은 칩 전송과 무관하다(review)" 주석 + 그 동작을 고정하는 통과 중인 테스트). 웹 `HeroSearch.submit`도 칩 클릭 시 query 상태를 안 건드린다. `_submit(query, {fromChip})`으로 갈라 칩 경로만 보존하게 맞췄다.
  - `[medium]` `[patch]` **당겨서 새로고침 테스트가 "새로고침이 실제로 일어나는지"를 안 봤다** — 단언 3개가 전부 새로고침 **전에도 참**이라(popular 오버라이드가 항상 throw하므로 `popular_error`는 최초 빌드부터 떠 있다) `onRefresh` 본문을 통째로 지워도, popular 한 줄만 지워도 전 스위트가 green이었다. 2차 패스가 red 증명했다고 기록한 것은 `_refreshQuietly` 래퍼를 걷어낸 **다른 줄**이었다. provider별 재조회 횟수(각 2회)를 세는 단언을 추가.
  - `[medium]` `[patch]` **차종 칩이 필터를 싣고 가는지 아무도 안 봤다(AC2)** — 칩 상수와 `SearchScreen` 수신부는 각각 검증되지만 그 둘을 잇는 구간이 무검증이라, `SearchScreen(initialBodyType:, initialFuel:)`을 `const SearchScreen()`으로 바꿔도 349건 전부 green이었다. 그 상태 = **6개 칩 전부가 "전체 매물"을 여는 것**으로, 2차 패스 P1이 다른 형태로 잡았던 바로 그 라벨-결과 불일치다. 레포에 실제로 도달한 필터를 단언하도록 보강.
  - `[medium]` `[patch]` **히어로가 질의를 넘기는지 아무도 안 봤다(AC5)** — `AiChatScreen(initialQuery: query)`를 `const AiChatScreen()`으로 바꿔도 green이었다. 그 상태 = 히어로·제안 칩이 **빈 채팅 화면만** 열어 사용자가 방금 친 문장을 다시 타이핑해야 하는 것.
  - `[medium]` `[patch]` **"지금 인기" 섹션이 카드를 그리는 코드가 한 번도 실행된 적 없었다(AC3)** — 저장소 전체에서 `popularListingsProvider`를 **데이터 있는 상태로** 오버라이드하는 테스트가 0건(전부 빈 리스트·에러·카운팅 스텁)이었다. 찜 배선을 깨도 green이었고, 그 상태는 같은 매물이 홈 두 섹션에서 서로 다른 하트로 보이는 것 — spec-16-3이 "카드 진입점 3곳이 단일 provider를 공유한다"로 확정한 계약 위반이다.
  - `[medium]` `[patch]` **"전체보기"를 누르는 테스트가 0건이었다(AC3)** — 두 `onMore`를 `() {}`로 비워도 green. 그 상태 = 인기·최신 섹션에서 전체 목록으로 나가는 유일한 문이 죽은 링크가 되는 것.
  - `[medium]` `[patch]` **정렬 "방향"을 단언하는 검사가 없었다** — 소스텍스트 테스트가 `.order('view_count'`·`.order('id'`·`.limit(`은 봤지만 `ascending: false`는 안 봐서, `ascending: true`로 바꾸면 **"지금 인기"가 조회수 최하위 4건을 보여주면서** 전 스위트가 green이었다. 두 `.order(` 모두 방향까지 단언하도록 추가.
  - `[low]` `[patch]` 히어로 500자 상한(입력 `maxLength` + 제출 시 절단) 두 자리 모두 어떤 테스트도 안 밟아, `maxQueryLength * 10`으로 풀어도 green이었다(2차 패스 P9가 적용했다고 기록한 가드). 초과 입력 → 정확히 상한만큼만 넘어가고 길이 에러가 안 뜨는지 단언 추가.
  - `[low]` `[patch]` 제출 후 `_controller.clear()`(1차 패스 패치)도 지워도 green이었다. 검색 버튼 제출 후 입력창이 비는지 / 칩 제출 후엔 초안이 남는지를 각각 단언 추가(위 medium 패치와 짝).
  - `[low]` `[patch]` **"방금 올라온 매물" 섹션의 에러 문구가 옛 이름("최근 매물")을 그대로 쓰고 있었다** — 화면에 없는 섹션 이름의 에러를 사용자가 본다. 헤더와 같은 말로 맞추고, `_PopularListings`에만 있던 것과 대칭으로 `Key('recent_error')`를 붙여 반대 방향(최신 실패 → 히어로·차종칩·"지금 인기" 정상 렌더) 격리 테스트를 심었다(Always의 섹션별 격리가 한 방향만 검사돼 있었다).
  - `[low]` `[patch]` `conventions.md` §6이 `fetchPopularListings`를 "id를 좁혀 `listing_images`를 조회한다"는 근거로 FR11 이미지 축 강제 지점에 등재했는데, 실제로 그러는지 보는 검사가 없어 `_fetchCovers` 호출을 빼도 green이었다(그 상태 = "지금 인기" 카드 전부가 사진 플레이스홀더로 회귀). 소스텍스트 단언에 두 식별자 추가.
  - `[low]` `[patch]` `chat_list_screen.dart`의 파일 헤더와 `showAppBar` 문서 주석이 **삭제된 홈 "문의 채팅" 퀵액션을 현존 진입점처럼** 가리키고, `showAppBar` 기본값 true의 존재 이유를 그 없어진 진입점으로 설명하면서 근거로 "spec-16-1 Never: 퀵액션 유지"를 인용했다(이번 스토리가 뒤집은 Never다). 2차 패스가 같은 종류의 주석 5곳을 훑으면서 이 파일만 빠졌다 — 실측(grep) 결과대로 다시 적었다.
  - `[low]` `[patch]` `sell_screen_test.dart`의 테스트 이름·주석이 **이 커밋이 삭제한 시나리오**("/sell 탭 루트와 홈 go_sell 퀵액션이 동시에 뜬다")를 서술한다 — 테스트는 상황을 합성하므로 green이고, 2차 패스는 소스 쪽 주석만 고쳤다. 회귀 테스트가 존재하지 않는 실패 모드를 문서화한 채 남아 실제 위험을 가린다. 지금 실재하는 쌍(내 매물 관리의 수정 push)으로 정정(단언·로직 무변경).
  - `[low]` `[patch]` `conventions.md` §6에서 2차 패스가 서수는 "네 번째"로 고쳤지만 같은 줄 본문이 여전히 "**위 두 경로와** 같은 세션으로 붙으므로"였다 — 앞선 앱 경로는 이제 셋이다. FR11 강제 지점 대장이라 개수가 어긋나면 다음 사람이 자기 경로의 등재 여부를 판단 못 한다.
  - `[low]` `[patch]` `epics-increment-2026-07-12.md`의 Story 16.8 AC에서 **제안 칩 목록이 아직 목업 3개**였다 — 2차 패스가 바로 다음 줄(차종 칩)에 "✎ 정정"을 심으면서 이 줄만 건너뛰었다. 같은 관례로 웹 `SUGGESTIONS` 4개(파일을 실제로 읽어 인용)와 근거를 심고, 섹션 헤더가 "최신"이 아니라 "방금 올라온 매물"로 나갔다는 사실도 함께 적었다.
  - `[low]` `[patch]` `epic-16-context.md`가 이번 재컴파일에서 비로그인 열람 범위를 "목록·상세·**홈**"으로 **넓혔는데**, 앱은 모든 경로를 `/login`으로 보내 그 요구사항이 앱에서 성립하지 않는다(DW-738이 이미 등재한 모순을 같은 커밋이 오히려 확대). 이 파일은 다음 스토리 16.7·16.6이 읽는 입력이라 잘못된 지시가 다시 내려올 자리다 — "웹 한정 + DW-738이 결정을 추적 중"으로 ✎ 정정.
  - `[low]` `[patch]` 스펙 Design Notes의 `_SearchCta` 유지 근거("하단 4탭과 목적지가 겹치지 않아 제거 근거가 없다")가 **같은 커밋이 동일 목적지 진입점을 3개 더 만들면서** 사실과 어긋났다. Never가 제거를 금지하므로 위젯은 그대로 두되, 유지 근거를 "중복을 알고도 범위 밖이라 남긴다"로 정정하고 판단을 16.6으로 넘겼다.
  - `deferred` (신규 1건, 선재 — 이 스토리가 만든 것이 아님):
    - `DW-740` 앱은 `view_count`를 읽기만 하고 `increment_listing_view` RPC를 어디서도 부르지 않는다(실측: app 전역 0건, 앱의 RPC 호출은 채팅 2건뿐) — 앱만 쓰는 시연에서 "지금 인기"가 `id desc` 고정 목록으로 퇴화한다. trigger: Epic 16-6 착수 시.
  - `rejected_as_noise` (기록용, 근거 포함):
    - edge-case 레이어가 "워킹트리가 HEAD가 아니다 — `home_screen.dart`에서 2차 패스 패치 3건이 되돌려져 있다"고 보고했다 — **병렬로 돌던 verification-gap 레이어가 그 순간 뮤테이션 실험 중이던 파일을 관측한 것**이다(그 레이어는 실험 후 백업본으로 원복했고 "byte-identical to HEAD"를 보고했다). 리뷰 종료 후 직접 확인: `git status`에 `app/` 변경 0건. 다만 그 레이어가 부수적으로 **측정한 커버리지 구멍 3건은 진짜였고** 위 패치로 닫았다.
    - `deferred-work.md`의 16.8 항목이 `flutter test` 건수를 334로 적고 있다(실제는 이번 실행 기준 360) — 사실이지만 이번 호출 지시가 "장부에는 신규 항목만 추가, 기존 항목 수정·재개방·재작성 금지"이므로 이 실행의 권한 밖이다. 2차 패스에 이어 두 번째 등장이며, 정정 여부는 오케스트레이터 판단으로 남긴다.
    - 실기기/브라우저 육안 렌더 미검증(intent-alignment: "기대는 렌더 표면에, 증거는 전부 위젯 트리 표면에 있다") — 사실이지만 1차 패스에서 이미 장부에 등재됐고, 계획 문서가 Epic 16-6(실기기 mobile-mcp 통합 시연 검증)이 이 화면을 포함해 검증하도록 반영해 뒀다. 이 샌드박스의 CanvasKit `CONTEXT_LOST_WEBGL` 한계는 선행 스토리 2건에서 재현된 환경 제약이다.
    - `SearchScreen.initState`의 `mounted` 가드가 여전히 red 증명 불가 — 2차 패스가 원인까지 규명해(`AutomatedTestWidgetsFlutterBinding.pump()`가 같은 호출 안에서 `flushMicrotasks()`를 부르므로 "마이크로태스크 실행 전 dispose"를 만들 수 없다) 그 사실을 테스트 파일 옆에 적어 뒀다. 이번 리뷰가 재확인했으나 **새 정보가 없어** 다시 올리지 않는다.

## Design Notes

**차종 칩 6개는 목업이 아니라 웹의 실제 구현을 따른다.** 목업(`app-home-2.html`)은 "전체·경차·세단·SUV·전기·수입"을 보여주지만, "세단"·"수입"은 DB에 1:1 필터 값이 없어 웹이 이미 의도적으로 빼고 "화물"·"승합"으로 채운 6개를 쓰고 있다(`CategoryChips.tsx` 주석). 계획 단계에서 이 불일치를 발견해 사용자에게 확인했고(2026-08-08), "라벨과 실제 필터가 어긋나는 칩을 새로 만들지 않는다"는 웹의 기존 판단을 앱도 따르기로 결정했다.

**히어로 제안 칩은 목업의 3개가 아니라 웹의 4개(`SUGGESTIONS`)를 쓴다.** 목업은 앱 전용 축약본이고 별도 근거가 없다 — 웹 쪽이 자체 목업(`landing-1.html`)에서 그대로 가져온 4개이자 이미 안정적으로 운영 중인 정본이라, 위 차종 칩과 같은 원칙(웹 우선)을 적용한다.

**`_SearchCta`(go_search)는 손대지 않는다.** AC가 명시한 제거 대상은 정확히 3개(go_chat/go_sell/go_my_listings)이고 go_search는 그 목록에 없다 — 하단 4탭 어디와도 목적지가 겹치지 않는다(채팅·내차팔기 탭과 달리 "탐색" 탭은 없다).

✎ **정정 2026-08-09(3차 코드리뷰).** 위 근거는 "하단 탭과의 중복"만 따진 것인데, **같은 커밋이 목적지가 완전히 동일한 `const SearchScreen()` 진입점을 3개 더 만들었다** — "전체" 칩 · "지금 인기" 전체보기 · "방금 올라온 매물" 전체보기. 즉 이 카드는 이제 한 화면 안에서 네 번째 같은 문이고, 확정 목업 `app-home-2.html`에도 웹 랜딩에도 없다. 그럼에도 **유지가 맞다** — 이 스토리의 Never가 `Key('go_search')` 제거를 명시적으로 금지했고(surgical, CLAUDE.md A3), 그 금지는 사용자 결정으로 들어온 것이라 리뷰가 뒤집을 자리가 아니다. 다만 유지 근거는 "겹치지 않아서"가 아니라 **"중복을 알고도 이번 스토리 범위 밖이라 남긴다"**로 읽어야 한다. 이 카드의 존치·제거 판단은 홈 정보구조를 실기기로 대조하는 Epic 16-6(SM-D 통합 시연 검증) 자리로 넘긴다.

**필터 진입 경합**: `searchControllerProvider`는 앱 전역 싱글턴이라 최초 빌드 시 빈 필터 초기조회를 자동으로 예약한다(`build()`의 `Future.microtask(search)`). 차종 칩 탭이 이 provider의 첫 읽기와 겹치면 `initState`의 필터 조회와 그 자동 빈 조회가 동시에 진행돼, 응답 도착 순서에 따라 빈 결과가 필터 결과를 덮어쓸 수 있다. 어떤 방식으로 막든(요청 토큰, 호출 순서 재배치 등) 최종 화면은 항상 필터 결과를 보여줘야 한다(I/O 매트릭스).

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 로컬/개발 API로 앱 홈을 열어 히어로·차종칩·인기/최신 섹션이 실제로 이 순서로 보이는지, 차종 칩 탭이 실제로 필터링된 탐색 결과로 이어지는지 1회 실측. 이 세션(헤드리스 샌드박스)이 CanvasKit `CONTEXT_LOST_WEBGL`로 렌더를 못 띄우면(spec-16-4/16-5 선례) 대장에 등재하고 위젯테스트로 대체 확인한 사실을 명시한다.

## Auto Run Result

**Summary:** 앱 홈을 웹 랜딩(Epic 11)과 같은 정보구조로 재구성했다 — 실 입력+제안칩 히어로, 차종 칩 6개(전체·경차·SUV·전기·화물·승합, 웹과 바이트 일치), "지금 인기"(view_count desc)·"방금 올라온 매물"(created_at desc) 2섹션을 같은 순서로 추가하고, Epic 7 잔재 퀵액션 3개(go_chat/go_sell/go_my_listings)를 같은 커밋에서 제거했다(DW-736 해소). 계획 단계에서 목업과 웹 실제 구현이 차종 칩 값에서 충돌하는 것을 발견해 사용자 확인 후 웹을 정본으로 확정했고, 코드리뷰에서 그 제거가 "내 매물 관리" 화면을 앱에서 완전히 도달 불가하게 만드는 것을 잡아 프로필 메뉴에 대체 진입점을 추가했다.

**Files changed:**
- `app/lib/features/auth/home_screen.dart` — 히어로 재구성, 차종 칩 신설, "지금 인기" 신설, "최근 매물"→"방금 올라온 매물" 개칭, 퀵액션 3개+`_QuickAction` 제거, 새로고침 섹션별 격리, 컨트롤러 clear, 토큰 정리, 칩 터치 영역 확장
- `app/lib/core/router/app_router.dart` — 프로필 메뉴에 "내 매물 관리" 항목 추가(리뷰 패치)
- `app/lib/features/listings/listings_repository.dart` — `fetchPopularListings` 신설
- `app/lib/features/listings/listings_providers.dart` — `popularListingsProvider` 신설, 요청-경합 방어(requestId) 추가
- `app/lib/features/listings/search_screen.dart` — `initialBodyType`/`initialFuel` + 즉시조회 + `mounted` 가드(리뷰 패치)
- `app/lib/features/listings/sell_screen.dart` — 진입점 주석 정정(리뷰 패치)
- `app/lib/features/ai_search/ai_chat_screen.dart` — `initialQuery` 자동 제출
- `docs/conventions.md` — FR11 소비처 목록에 `fetchPopularListings` 추가(리뷰 패치)
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` — Story 16.8 AC 차종 칩 목록 "✎ 정정" 각주(리뷰 패치)
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-736 닫음, CanvasKit 렌더 미실행 사실 신규 등재
- `_bmad-output/implementation-artifacts/epic-16-context.md` — Story 16.8 반영해 재컴파일
- `app/test/home_ai_entry_test.dart`, `app/test/home_screen_wishlist_test.dart`, `app/test/search_screen_test.dart`, `app/test/ai_chat_screen_test.dart`, `app/test/app_router_test.dart` — 신규/보강 위젯테스트
- `app/test/home_refresh_test.dart` — 신규(새로고침 섹션별 격리 테스트)

**2차(후속) 리뷰 패스에서 추가로 바뀐 파일:**
- `app/lib/features/listings/search_screen.dart` — "전체" 칩 무필터 명시 리셋(조기 return 제거)
- `app/lib/core/router/app_router.dart` — 프로필 메뉴 push에 두 provider 무효화 복원, 홈 탭 `onActivate`에 `popularListingsProvider` 추가, 퀵액션 주석 정정
- `app/lib/features/listings/listings_repository.dart` — 카드 select 12컬럼을 `listingCardColumns` 상수로 합침(두 조회 경로 공유)
- `app/lib/features/auth/home_screen.dart` — 히어로 500자 상한, 제안 칩 48dp 히트 영역, `_refreshQuietly` 실패 로그, `go_ai` 앵커 주석, 칩 상수 테스트 노출
- `app/lib/features/listings/sell_screen.dart`·`sell_controller.dart` — 제거된 퀵액션을 가리키던 주석 정정
- `docs/conventions.md` — §6 FR11 강제 지점 목록의 서수 정정(세 번째 → 네 번째)
- `_bmad-output/implementation-artifacts/epic-16-context.md` — 차종 칩·제안 칩 "✎ 정정"(세단·수입 → 화물·승합, 제안칩 3개 → 웹 4개)
- `_bmad-output/implementation-artifacts/deferred-work.md` — 신규 DW-737·738·739 등재(기존 항목은 미수정)
- `app/test/listings_repository_card_columns_test.dart`·`app/test/home_chips_contract_test.dart` — 신규 계약 테스트
- `app/test/search_screen_test.dart`·`app/test/app_router_test.dart` — 신규 회귀 테스트(전체 칩 리셋·프로필 메뉴 무효화·탭 재활성화 무효화·initialFuel 즉시조회·조기 dispose)

**3차(후속) 리뷰 패스에서 추가로 바뀐 파일:**
- `app/lib/features/ai_search/ai_chat_screen.dart` — `_submit`에 `restoreInputOnFailure` 추가(히어로 자동 제출 실패 시 원문 복원)
- `app/lib/features/auth/home_screen.dart` — 제안 칩 제출은 입력창을 비우지 않게(`fromChip`), "방금 올라온 매물" 에러 문구 개칭 + `Key('recent_error')`
- `app/lib/core/router/app_router.dart` — 프로필 메뉴 `.then` 무효화를 `ProviderScope.containerOf`로 전환(셸 파괴 후 `ref` 사용 시 `StateError`)
- `app/lib/features/chat/chat_list_screen.dart` — 삭제된 홈 퀵액션을 가리키던 헤더·`showAppBar` 주석 정정(주석만)
- `app/test/home_chips_contract_test.dart` — 웹 `CategoryChips.tsx`·`HeroSearch.tsx`를 실제로 읽어 대조하도록 재작성(사본 대조 폐기)
- `app/test/home_refresh_test.dart` — provider별 재조회 횟수(각 2회) 단언 추가
- `app/test/app_router_test.dart` — 칩→레포 필터 전달, 히어로→`initialQuery` 전달, "전체보기" 2건 신규 단언
- `app/test/home_screen_wishlist_test.dart` — "지금 인기" 섹션의 데이터 분기(카드 렌더·찜 배선·탭→상세) 최초 커버
- `app/test/home_ai_entry_test.dart` — 히어로 500자 절단·제출 후 clear·칩 초안 보존·최신 실패 격리(대칭) 신규
- `app/test/listings_repository_card_columns_test.dart` — `ascending: false`(정렬 방향)·`_fetchCovers`/`attachCoverImages` 단언 추가
- `app/test/sell_screen_test.dart` — 삭제된 시나리오를 서술하던 테스트 이름·주석 정정(단언 무변경)
- `docs/conventions.md`·`_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`·`_bmad-output/implementation-artifacts/epic-16-context.md` — §6 경로 개수, 제안 칩 ✎ 정정, 비로그인 열람 웹-한정 ✎ 정정
- `_bmad-output/implementation-artifacts/deferred-work.md` — 신규 DW-740 등재(기존 항목 미수정)

**Review findings breakdown:**
- 1차 패스: patch 12건(high 1, medium 3, low 8) 전부 적용·검증. defer 0건. reject 2건.
- 2차(후속) 패스: patch 13건(high 1, medium 5, low 7) — 12건 적용·검증 완료, 1건(장부 테스트 건수 정정)은 **이번 호출의 "기존 장부 항목 수정 금지" 지시로 미적용**하고 정확한 값을 아래에 기록. defer 3건(DW-737·738·739 신규 등재). reject 4건(sprint-status 미커밋 — 오케스트레이터 소유이자 리뷰 diff 밖; `review_loop_iteration: 0` — 후속 리뷰 재진입 시 규정된 리셋; 기존 장부 항목 재포맷 — 권한 밖; 칩 연타 중복 push — 앱 전역에 연타 가드가 없는 기존 관례, A2).

- 3차(후속) 패스: patch 20건(high 0, medium 10, low 10) 전부 적용·검증. defer 1건(DW-740 신규 등재). reject 4건(워킹트리 오관측 — 병렬 리뷰어의 뮤테이션 실험을 본 것; 장부 테스트 건수 정정 — 권한 밖; 육안 렌더 미검증 — 기등재·16.6 담당; `mounted` 가드 미증명 — 새 정보 없음).

**Follow-up review recommendation:** `true` — 이번(3차) 패스 patch에 high는 없지만 점수 계산이 임계값을 크게 넘는다: 3×medium(10) + 1×low(10) = **40** ≥ 5 → `true`. 실질적 근거도 있다 — 이번 패스가 잡은 medium 10건 중 6건이 **"고친 것이 아니라 아무도 안 보고 있던 것"**(칩→필터 전달·히어로→질의 전달·인기 카드 렌더·전체보기·정렬 방향·새로고침 실행 여부)이었고, 그 6건은 전부 349건 green 상태에서 뮤테이션으로 드러났다. 검사가 새로 10건 넘게 늘어난 직후이므로 그 검사들 자체를 한 번 더 볼 가치가 있다.

**Verification performed (2차 패스, 전부 이 세션에서 직접 실행·관찰):**
- `flutter analyze` — **0 issues**
- `flutter test` — **349건 전체 green** (2차 패치로 신규 테스트 10건 추가)
- `flutter build web --dart-define-from-file=.env.json` — **빌드 성공**(`✓ Built build/web`)
- red→green 증명(CLAUDE.md B4 "만들었다가 아니라 잡는다가 완료"):
  - `home_refresh_test.dart` — `_refreshQuietly`를 걷어내고 맨 `Future.wait`로 되돌리자 **실제로 red**, 되돌리니 green. 이 가드는 진짜 잡는다(1차 패스에서 미증명이던 것을 이번에 실측).
  - "전체" 칩 리셋·프로필 메뉴 무효화·탭 재활성화 무효화 — 각각 수정 전 red, 수정 후 green 확인.
  - ⚠️ **`mounted` 가드는 red 증명에 실패했다** — 가드를 지워도 스위트가 계속 green이다. 원인까지 확인했다: `AutomatedTestWidgetsFlutterBinding.pump()`가 `handleDrawFrame()` 직후 같은 호출 안에서 `flushMicrotasks()`를 무조건 부르므로 `initState`가 건 마이크로태스크는 그 `pumpWidget`이 반환되기 전에 반드시 실행된다. 즉 이 테스트 프레임워크에서는 "마이크로태스크 실행 전 dispose"를 만들 수 없다. 이 사실을 테스트 파일 안에 그대로 적어 뒀다(검사가 못 보는 것을 검사 옆에).
- 원복은 전부 백업본으로 했다(`git checkout` 미사용 — 커밋 안 된 패치까지 날아가는 실측 사례가 있다).
- Manual check(실제 렌더 육안 확인)은 여전히 미실행 — 이 헤드리스 샌드박스의 CanvasKit `CONTEXT_LOST_WEBGL` 한계(선행 스토리 2건에서 동일 에러 재현). 1차 패스에서 이미 장부에 등재됨.

**Verification performed (3차 패스, 전부 이 세션에서 직접 실행·관찰):**
- `flutter analyze` — **0 issues**(`No issues found!`)
- `flutter test` — **360건 전체 green**(3차 패치로 신규 테스트 11건 추가, 349 → 360)
- `flutter build web --dart-define-from-file=.env.json` — **빌드 성공**(`✓ Built build/web`)
- red→green 증명 — 이번에 추가한 검사 9종 전부 실제 뮤테이션으로 red 확인 후 원복·green 확인. 대표 뮤테이션: 칩의 `SearchScreen(initialBodyType:, initialFuel:)` → `const SearchScreen()`; `AiChatScreen(initialQuery:)` → `const AiChatScreen()`; 두 `onMore` → `() {}`; `onRefresh`에서 popular 한 줄 삭제; `.order('view_count', ascending: true)`; `_fetchCovers` 호출 제거; 500자 상한 → `maxQueryLength * 10`; `_controller.clear()` 삭제; 웹 `CategoryChips.tsx` 경로 차단(폴백 없이 실패하는지).
- ⚠️ **하위 에이전트의 red 보고를 그대로 믿지 않고, 형태를 바꾼 뮤테이션으로 직접 재검증했다**(이 저장소에 "서브에이전트의 red/green 증명은 자기가 쓴 표기에서만 성립할 수 있다"는 실측 사례가 있다). 검증 2종: ① 칩 필터 인자를 **지우는** 대신 `initialBodyType: chip.fuel` / `initialFuel: chip.bodyType`로 **서로 뒤바꿔** 보았고 → 해당 2건 red. ② 찜 배선을 문자열 변조 대신 `wished: false` 상수로 바꿔 보았고 → 해당 1건 red. 원복 후 다시 360 green·analyze 0 확인.
- 원복은 전부 백업본으로 했다(`git checkout` 미사용).
- Manual check(실제 렌더 육안 확인)은 3차 패스에서도 미실행 — 이 헤드리스 샌드박스의 CanvasKit `CONTEXT_LOST_WEBGL` 한계. 1차 패스에서 이미 장부에 등재됨.

**Residual risks:**
- **"인기"의 쓰기 절반이 앱에 없다(DW-740, 신규)** — 앱은 `increment_listing_view`를 어디서도 부르지 않으므로 앱만 쓰는 시연에서 "지금 인기"가 `id desc` 고정 목록으로 퇴화할 수 있다. 위젯테스트는 provider를 오버라이드하므로 이걸 보는 검사가 없고, 육안 확인도 아직 미실행이다 — **지금 이 사실을 관측 중인 검사가 하나도 없다.** Epic 16-6 착수 시 결정 필요.
- **`mounted` 가드는 검사로 고정되지 않은 방어 코드다** — 위 실측대로 이 프레임워크에서는 그 시나리오를 재현할 수 없다. 실제 기기에서만 도달 가능한 경로일 수 있고, 지금은 코드 리뷰로만 지켜진다.
- **실기기/브라우저 육안 렌더 확인 미실행** — Epic 16-6(SM-D 통합 시연 검증, 실기기 mobile-mcp)이 이 화면을 포함해 검증하도록 계획 문서에 반영돼 있다(순서: 16.8 → 16.7 → 16.6). 특히 이번에 히어로 입력에 `maxLength`를 걸면서 카운터를 숨겼는데(`counterText: ''`), 알약 높이가 그대로인지는 눈으로 봐야 확실하다.
- **`deferred-work.md`의 16.8 항목이 `flutter test` 건수를 334로 적고 있다** — 실제 확인값은 2차 패스 시점 349, 3차 패스 종료 시점 **360**이다. 기존 장부 항목 수정이 이번 실행의 권한 밖이라 그대로 뒀다(2차·3차 연속으로 남는 항목). 오케스트레이터가 정정 여부를 판단할 항목.
- **잔여 산출물(이 변경의 일부가 아님)**: `_bmad-output/implementation-artifacts/sprint-status.yaml`이 워킹트리에 수정된 채 남아 있다(`16-8: done`). 이 실행이 만든 변경이 아니고 리뷰 diff 밖이라 커밋하지 않고 그대로 둔다.
