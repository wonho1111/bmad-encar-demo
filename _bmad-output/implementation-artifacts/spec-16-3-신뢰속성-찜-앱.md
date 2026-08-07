---
title: '신뢰속성·찜 (앱)'
type: 'feature'
created: '2026-08-07'
status: 'done'
baseline_revision: 'e623b20ef2e824d79c88b825532120b70f1ef6ee'
final_revision: 'b97eb15d8576f630d23dae97238bcd70685174d9'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-16-context.md'
  - '{project-root}/docs/conventions.md'
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** 앱은 신뢰속성 3필드(`accident_status`·`is_single_owner`·`is_non_smoker`)를 카드용으로는 이미 파싱해 두고도 화면에 그리지 않고, 상세 모델(`ListingDetail`)에는 그 필드 자체가 없다. 찜(하트)은 아예 없다 — 하단 "찜" 탭은 16.1이 남긴 플레이스홀더 화면(`WishlistPlaceholderScreen`)뿐이다. 웹은 이미 두 기능(Story 10.2 신뢰 뱃지, Story 10.5 찜)을 구현했고, DB 스키마·RLS·판정 로직·색 톤이 전부 확정돼 있다.

**Approach:** 웹이 이미 락스텝으로 확정한 계약(신뢰속성 판정 로직·색 톤, `wishlists` 스키마·RLS, 카드 레이아웃)을 그대로 소비해 Flutter 위젯을 새로 만든다. DB/RLS 변경 없음(`0017`·`0018`이 이미 존재). 앱은 라우터 전역이 이미 로그인 필수(`app_router.dart` redirect)이므로 웹의 로그인 게이트·`redirectedFrom` 로직은 이식하지 않는다.

## Boundaries & Constraints

**Always:**
- 신뢰속성 판정은 웹 `TrustAttributes.tsx`의 `getTrustBadges`와 동일: `accident_status`가 `{'무사고','단순교환','사고'}` 밖(빈 문자열 포함)이면 `null`과 동일 취급(미표시). `'무사고'`만 초록 뱃지, 나머지 2값은 초록이 아닌 중립 뱃지(amber 금지). `is_single_owner`/`is_non_smoker`는 정확히 `true`일 때만 초록 칩 — `null`·`false`는 "아님"으로 단정하지 않고 미표시. 뱃지 0개면 카드·상세 모두 빈 슬롯을 그리지 않는다(완전 생략).
- **카드에는 면책 문구를 넣지 않는다**(웹 2026-08-05 결정 — `TrustAttributes.tsx` 현재 코드가 근거, 사진 위 좁은 오버레이 공간이라 뺐다). **상세에는 뱃지와 면책 "판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요."를 한 위젯이 함께 반환**해, 뱃지만 있고 면책이 빠지는 렌더 경로가 코드상 존재하지 않게 한다(B9, 웹 결속 원칙 미러).
- 카드의 신뢰속성 뱃지는 사진(5:3) **좌상단에 오버레이**(반투명 배경+블러, 웹 `badgeClassName('card')` 미러 — 값 유무와 무관하게 카드 높이가 항상 같게). 상세는 기존 `AppColors.trustGreenBg`/`trustGreenInk`(이미 존재)로 초록을, 중립은 `AppColors.borderHairline` 테두리+`inkSecondary` 글자로 표시한다.
- `wishlists`(0018)·신뢰속성 3컬럼(0017)은 이미 존재 — **새 마이그레이션·새 RLS 정책을 만들지 않는다.**
- 앱 전역이 라우터 redirect로 이미 로그인 필수(`app_router.dart:179-201` 실측)이므로, 찜 토글에 별도 로그인 게이트·`/login?redirectedFrom=` 리다이렉트를 만들지 않는다 — `supabase.auth.currentUser`가 non-null임을 전제하고 곧바로 `.id`를 쓴다(기존 관례).
- 낙관적 토글: 누르면 즉시 하트가 채워지고 `wishlists` insert, 재클릭 시 즉시 비워지고 delete. 실패 시 아이콘 롤백 + `ScaffoldMessenger.showSnackBar` 안내(앱 기존 관례 재사용 — 전역 토스트 인프라 신설 금지). 진행 중 연타는 버튼 disabled로 차단.
- 찜 여부를 표시하는 카드 진입점 **3곳 전부**(홈 미리보기 `home_screen.dart`·검색 결과 `search_screen.dart`·AI 결과 `ai_chat_screen.dart`, 웹의 `page.tsx`/`search/page.tsx`/`ChatAssistant.tsx`/`PopularRecentGrid.tsx` 4곳과 대응)에 찜 오버레이를 주입한다 — 한 곳만 하면 화면마다 하트 상태가 어긋난다.
- 찜 오버레이는 로그인 사용자의 전체 찜 id 집합을 한 번에 조회하는 단일 provider로 공급한다(현재 매물 수 스케일이 작아 화면별 id-scoped 조회 대신 전체 집합 재사용 — `fetchListings`가 이미 페이지네이션 없이 전량 조회하는 것과 같은 근거, A2). 찜 토글 성공 시 이 provider를 invalidate해 다른 화면의 카드도 다음 리빌드에 최신 상태를 반영한다.
- 찜 목록 화면(`WishlistPlaceholderScreen` 교체): 본인 찜 매물을 최신순으로. `embed==null`(RLS 차단, 타인 소유 sold) 또는 `status!='on_sale'`(본인 소유 sold)이면 회색 비활성 타일 + "판매완료" 배지로 표시하고 상세 진입을 막는다(FR11, 웹 `isWishedListingBlocked` 판정 미러). 0건이면 "아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요."
- `fetchListing`/`fetchOwnListing`의 select 문자열에 `accident_status, is_single_owner, is_non_smoker`를 추가한다(`fetchListings`는 이미 포함 — `listings_repository.dart:249-251,337-339` 실측 확인, 두 곳만 빠짐). `ListingDetail`에도 3필드 추가(`listing.dart:189-217`에 현재 없음 — `ListingCardData`엔 이미 있음).
- `WishlistRepository`는 `ListingsRepository({SupabaseClient? client})`와 같은 생성자 주입 패턴을 따른다(테스트가 네트워크 없이 override할 수 있게).
- 찜 목록 화면이 on_sale 찜 매물의 대표사진을 보여주려면 `listing_images`를 새로 조회하는 경로가 하나 더 열린다(웹 `/wishlist`가 `attachCoverImages`를 on_sale 찜 id에만 한정해 부르는 것과 동일 패턴, `docs/conventions.md` §6 "규칙7"). **이 새 경로를 `docs/conventions.md` §6의 이미지 축 소비처 목록(앱 하위 목록, Story 16.2가 이미 두 경로를 등록한 자리)에 반드시 추가한다** — 등록 없이 열면 다음 사람이 FR11 강제 지점이 여기 있다는 것 자체를 모른다(§6 2026-07-19 코드리뷰가 지적한 바로 그 실패 모드).

**Block If:** (없음 — 스키마·RLS·판정 로직·색 톤이 전부 웹에서 이미 확정됐고, 앱은 그 계약을 그대로 소비한다.)

**Never:**
- DB 마이그레이션 신규 작성 금지(0017/0018이 이미 스키마·RLS를 갖춤).
- 판매자 신뢰속성 입력 폼(등록/수정 화면) 변경 금지 — DW-408(쓰기 UI 부재)은 아직 미착수 상태이고 16.3 트리거가 아니다. 16.3은 표시+찜 범위다.
- 전역 토스트/스낵바 인프라 신설 금지.
- 로그인 게이트·`redirectedFrom` 로직 이식 금지(라우터가 이미 전역 게이트).
- 찜 개수 집계·인기 정렬 신호 구현 금지(웹 10.5와 동일 범위 밖, 스키마도 그런 컬럼이 없다).
- "삭제된 매물" 배지 구현 금지 — `wishlists` FK가 `on delete cascade`라 하드삭제된 매물의 찜 행은 함께 사라져 이 케이스 자체가 도달 불가(웹 DW-417과 동일 근거).
- `accident_free`↔`accident_status` 통합·트리거 동기화(DW-408의 2026-08-02 후속 결정) 구현 금지 — 그건 웹 등록 폼이 실제로 생길 때의 별도 스토리 몫이다. 이 스토리는 두 값을 있는 그대로(상세는 `accident_free` 행 유지 + `accident_status` 뱃지 별도) 표시만 한다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 무사고 | `accident_status='무사고'` | 카드: 사진 좌상단 초록 뱃지(✓+"무사고"); 상세: 같은 뱃지+면책 | 없음 |
| 단순교환/사고 | `accident_status='단순교환'`\|`'사고'` | 중립 톤 뱃지(초록 아님) + (상세만) 면책 | 없음 |
| 계약-외 값 | `accident_status='외판교환'`\|`''` | `null`과 동일(미표시) | 없음 |
| 1인소유/비흡연 | `is_single_owner=true`\|`is_non_smoker=true` | 초록 칩 추가 | 없음 |
| bool 미상 | `is_single_owner=null`\|`false` | 그 칩만 미표시(다른 칩은 그대로) | 없음 |
| 전부 미입력 | 3필드 전부 `null` | 카드: 오버레이 없음; 상세: 섹션 자체 없음 | 없음 |
| 찜 토글 성공 | 하트 클릭(미찜 상태) | 즉시 채움 → insert 확정, 재클릭 시 delete로 비워짐 | 없음 |
| 찜 토글 실패 | insert/delete 실패 | 아이콘 직전 상태로 롤백 + SnackBar | `debugPrint` 로그 |
| 찜 목록 조회 | 로그인 사용자가 찜 탭 진입 | 최신순 카드/타일, 0건이면 EmptyState 문구 | 조회 실패 시 한국어 안내 |
| 찜 목록의 차단 매물 | `embed==null` 또는 `status!='on_sale'` | 회색 비활성 타일 + "판매완료" 배지, 탭해도 상세 진입 안 됨 | 없음 |

</intent-contract>

## Code Map

- `app/lib/features/listings/listing.dart` -- `ListingDetail`에 `accidentStatus`/`isSingleOwner`/`isNonSmoker` 3필드 추가 + `fromMap` 파싱(`ListingCardData`는 이미 있음, `withImages`처럼 필드 나열 갱신 필요) -- 상세 신뢰속성 렌더의 데이터 원천
- `app/lib/features/listings/listings_repository.dart` -- `fetchListing`/`fetchOwnListing`의 select 문자열에 3컬럼 추가(`fetchListings`는 이미 포함) -- 상세 화면이 값을 받게 함
- `app/lib/features/listings/listing_trust_widgets.dart` (신규) -- 신뢰속성 판정 순수함수(`@visibleForTesting`, 웹 `getTrustBadges` 미러) + 카드용(사진 오버레이, 면책 없음)/상세용(뱃지+면책 결속) 두 렌더 모드 위젯 -- `listing_photo_widgets.dart`의 공유위젯 파일 패턴 미러
- `app/lib/features/listings/listing_card.dart` -- 사진 `Stack`을 감싸는 외곽 구조를 추가해 신뢰속성 오버레이(사진 좌상단)+찜 버튼(사진 하단 우측에 겹침, 웹 `top-full` 미러)을 배치, `wished` 파라미터 추가 -- 웹 `ListingCard.tsx`(2026-08-05 레이아웃) 미러
- `app/lib/features/listings/listing_detail_screen.dart` -- "기본 정보" 섹션 뒤에 신뢰속성 위젯(상세 모드) + 찜 버튼(제목 줄) 삽입 -- 상세 AC
- `app/lib/features/wishlist/wishlist_repository.dart` (신규) -- `toggle(listingId, wish: bool)`·`fetchWishlist()`(본인 찜 ⨝ listings 조인)·`fetchWishedListingIds()`·순수 `isWishlistBlocked(embed, status)` 판정(웹 `isWishedListingBlocked` 미러) -- Supabase SDK 직접 호출(api 미경유), `ListingsRepository`와 같은 생성자 주입 패턴
- `app/lib/features/wishlist/wishlist_providers.dart` (신규) -- `wishlistRepositoryProvider` + `wishedListingIdsProvider`(`FutureProvider<Set<String>>`, 전체 집합 1회 조회) + `wishlistProvider`(찜 목록 `AsyncValue`) -- `listings_providers.dart` DI 패턴 재사용
- `app/lib/features/wishlist/wish_button.dart` (신규) -- 낙관적 토글 위젯(누르면 즉시 반영 → 확정, 실패 시 롤백+SnackBar, 연타 차단) -- 카드·상세 화면 공유
- `app/lib/features/wishlist/wishlist_screen.dart` (신규) -- `WishlistPlaceholderScreen` 대체: 목록/빈 상태/판매완료 회색 타일 -- `app_router.dart`의 `tab_wishlist` builder 교체 지점
- `app/lib/core/router/app_router.dart` -- `tab_wishlist` builder를 `WishlistPlaceholderScreen` → `WishlistScreen`으로 교체 -- 실 화면 연결
- `app/lib/features/listings/home_screen.dart`·`search_screen.dart`·`ai_search/ai_chat_screen.dart` -- `ListingCard` 호출부에 `wishedListingIdsProvider` 결과로 `wished` 주입 -- 3개 진입점 전부 일관된 찜 상태(위 Boundaries)
- `app/lib/features/wishlist/wishlist_placeholder_screen.dart` -- 삭제(더 이상 참조되지 않는 고아 파일, A3)
- `docs/conventions.md` §6 -- 이미지 축 소비처 목록(앱 하위 목록)에 찜 목록의 `listing_images` 조회 경로 등록 -- 규칙7 준수(FR11 강제 지점 문서화)
- `app/test/listing_trust_widgets_test.dart` (신규) -- I/O 매트릭스 신뢰속성 6행 단언
- `app/test/wishlist_repository_test.dart` (신규) -- `isWishlistBlocked` predicate 단위테스트(on_sale/sold/null 3상태)
- `app/test/wish_button_test.dart` (신규) -- 토글 낙관적 반영/실패 롤백+SnackBar/연타 차단 위젯테스트
- `app/test/wishlist_screen_test.dart` (신규) -- 목록/빈 상태/판매완료 타일 단언
- `app/test/app_router_test.dart` -- `WishlistScreen` 배선 확인으로 기존 플레이스홀더 텍스트 단언 갱신

## Tasks & Acceptance

**Execution:**
- `app/lib/features/listings/listing.dart` -- `ListingDetail` 3필드 추가 + `fromMap`/`withImages` 갱신 -- 상세 렌더 데이터 원천
- `app/lib/features/listings/listings_repository.dart` -- `fetchListing`/`fetchOwnListing` select 확장 -- 상세 select 락스텝
- `app/lib/features/listings/listing_trust_widgets.dart` -- 판정 순수함수 + 카드/상세 위젯 -- I/O 매트릭스 신뢰속성 6행
- `app/lib/features/listings/listing_card.dart` -- 오버레이 배치 + `wished` 파라미터 -- 카드 AC
- `app/lib/features/listings/listing_detail_screen.dart` -- 신뢰속성 섹션 + 찜 버튼 삽입 -- 상세 AC
- `app/lib/features/wishlist/wishlist_repository.dart` -- toggle/fetch/판정 -- 찜 토글·목록의 데이터 계층
- `app/lib/features/wishlist/wishlist_providers.dart` -- provider 3종 -- DI·상태 공급
- `app/lib/features/wishlist/wish_button.dart` -- 낙관적 토글 위젯 -- 찜 상호작용
- `app/lib/features/wishlist/wishlist_screen.dart` -- 목록 화면 -- 찜 탭 AC
- `app/lib/core/router/app_router.dart` -- builder 교체 -- 탭 배선
- `app/lib/features/listings/home_screen.dart`·`search_screen.dart`·`ai_search/ai_chat_screen.dart` -- `wished` 주입 -- 3진입점 일관성
- `app/lib/features/wishlist/wishlist_placeholder_screen.dart` -- 삭제 -- 고아 파일 정리(A3)
- `docs/conventions.md` §6 -- 앱 이미지 축 소비처 목록에 찜 목록 경로 등록 -- 규칙7
- `app/test/listing_trust_widgets_test.dart`·`wishlist_repository_test.dart`·`wish_button_test.dart`·`wishlist_screen_test.dart` -- I/O 매트릭스·판정 단위테스트
- `app/test/app_router_test.dart` -- 배선 단언 갱신

**Acceptance Criteria:**
- Given 신뢰속성 값이 있는 매물, when 목록 카드를 렌더하면, then 사진 좌상단에 판정 규칙대로 뱃지가 오버레이되고 면책 문구는 없다.
- Given 신뢰속성 값이 있는 매물, when 상세 화면을 열면, then 뱃지와 면책 문구가 함께 렌더된다(뱃지만 있고 면책이 빠지는 상태는 코드상 불가능).
- Given 로그인 사용자가 카드/상세의 하트를 누르면, when insert가 성공하면, then 하트가 즉시 채워지고 `wishlists`에 행이 생기며, 재클릭 시 delete되어 비워진다.
- Given insert/delete가 실패하면, when 서버가 거부하면, then 하트가 직전 상태로 롤백되고 SnackBar 안내가 뜬다(연타 중엔 재요청이 나가지 않는다).
- Given 로그인 사용자가 홈·검색·AI 결과 중 한 화면에서 매물을 찜하면, when 다른 화면에서 같은 매물 카드를 다시 렌더하면(탭 전환 등으로 리빌드), then 그 카드도 채워진 하트로 보인다.
- Given 로그인 사용자가 찜 탭에 도달하면, when 찜이 있으면 최신순 카드로, 없으면 빈 상태 문구가 표시된다.
- Given 찜한 매물이 판매완료거나 RLS로 차단되면, when 찜 목록을 렌더하면, then 회색 비활성 타일 + "판매완료" 배지로 보이고 탭해도 상세로 이동하지 않는다.

## Spec Change Log

## Review Triage Log

### 2026-08-08 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (medium 2, low 6)
- defer: 1 (medium 1)
- reject: 8 (low 8)
- addressed_findings:
  - `[medium]` `[patch]` `wishlist_screen.dart`의 정상 카드 분기에 `key`가 없다(차단 타일 분기만 `ValueKey`를 받음) — 목록이 줄어들 때 Flutter가 다른 매물 자리에 `WishButton`의 로컬 상태(진행중·낙관적 하트)를 잘못 재사용할 수 있다(adversarial·edge-case-hunter 렌즈 독립 발견) — `key: ValueKey(listing.id)` 추가
  - `[medium]` `[patch]` `WishButton` 토글 성공 시 `wishedListingIdsProvider`만 invalidate하고 `wishlistProvider`는 건드리지 않아, 찜 목록 화면에서 직접 하트를 취소해도 탭을 나갔다 돌아오기 전까지 타일이 안 사라진다(adversarial 렌즈 발견, verification-gap이 이 재조회 경로의 회귀 테스트 부재를 별도로 지적) — 성공 시 `wishlistProvider`도 함께 invalidate
  - `[low]` `[patch]` 카드 신뢰속성 뱃지의 "반투명 배경+블러"(spec Boundaries 명시)가 반투명만 구현되고 블러가 없다(intent-alignment 렌즈 발견, `BackdropFilter` 부재 실측 확인) — `_TrustChip`의 onCard 분기에 `BackdropFilter`+`ImageFilter.blur` 추가
  - `[low]` `[patch]` `listing_card.dart`의 사진 비율이 `_CardPhoto`의 `AspectRatio(5/3)`와 찜 버튼 위치 계산의 `constraints.maxWidth * 3 / 5` 두 곳에 리터럴로 따로 존재한다(adversarial 렌즈 발견) — 공유 상수로 추출
  - `[low]` `[patch]` 찜 버튼 위치 계산이 `constraints.maxWidth`가 무한(가로 스크롤 등 미제약 폭 컨텍스트)일 때를 방어하지 않는다(edge-case-hunter 렌즈 발견) — 기존 `cacheWidth`의 `isFinite` 가드와 같은 방식으로 방어
  - `[low]` `[patch]` `app_router_test.dart`에 `recentListingsProvider`/`chatRoomsProvider`와 같은 탭 재진입 재조회 회귀 테스트 패턴이 `wishlistProvider`엔 없다(verification-gap 렌즈 발견, `onActivate` 무효화 줄을 지워도 스위트가 green임을 실측) — 같은 패턴으로 테스트 추가
  - `[low]` `[patch]` `listing_model_test.dart`의 `ListingDetail.fromMap` 그룹이 이번에 추가된 `accidentStatus`/`isSingleOwner`/`isNonSmoker` 파싱을 단언하지 않는다(`ListingCardData.fromMap`은 이미 테스트됨, verification-gap 렌즈 발견) — 단언 추가
  - `[low]` `[patch]` `wished` prop이 진입점 3곳(홈·검색·AI) → `ListingCard` → `WishButton`까지 실제로 배선되는지 검증하는 테스트가 없고(verification-gap 렌즈 발견), 상세 화면에서 `TrustAttributesDetailSection`·`WishButton`이 실제 데이터로 렌더되는지도 기존 `listing_detail_screen_test.dart`가 다루지 않는다(intent-alignment 렌즈 발견) — 최소 배선 테스트 추가
- deferred (장부에 신규 등재):
  - `[medium]` `wishedListingIdsProvider`가 로그아웃/계정 전환 시 invalidate되지 않아, 같은 기기에서 계정을 바꾸면 이전 계정이 찜한 매물이 새 계정 화면에도 잠깐 채워진 하트로 보일 수 있다(adversarial 렌즈 발견, `auth_controller.dart`에 실제로 어떤 provider도 정리하지 않음을 실측 확인). `recentListingsProvider`·`chatRoomsProvider`도 같은 패턴(탭 재진입에만 의존, 로그아웃 트리거 없음)이라 이 스토리가 만든 결함이 아니라 기존 아키텍처 전반의 문제.
- rejected_as_noise (기록용, 근거 포함):
  - 같은 매물을 두 화면에 동시에 띄우고 두 `WishButton`을 거의 동시에 눌러 연타 차단을 우회하는 경합(adversarial 렌즈 발견) — 발생 조건이 좁고(같은 매물의 상세를 rootNavigator에 중복 push), 최악의 경우도 다음 provider 갱신에서 자연 복구되며 DB에는 unique 위반으로 중복 행이 남지 않는다
  - `WishlistRepository.toggle`이 `currentUser!.id`(강제 언랩)를 쓰고 `fetchWishedListingIds`/`fetchWishlist`는 `?.id`를 쓰는 비대칭(adversarial·edge-case-hunter 렌즈 독립 발견) — spec Boundaries가 명시적으로 "toggle은 non-null을 전제하고 곧바로 `.id`를 쓴다"고 지시했고, 세션이 만료된 극단적 경우도 `WishButton`의 try/catch가 일반 실패로 동일하게 받아 사용자 체감은 다르지 않다
  - `fetchWishedListingIds` 조회 실패를 빈 Set으로 조용히 삼킨다(adversarial 렌즈 발견) — 오버레이는 카드 렌더를 막아선 안 되는 부가 신호라는 의도된 설계이고, web 대응 함수도 동일 방침이다
  - `Card.clipBehavior`를 `Clip.none`으로 바꿔 정보 영역이 더 이상 클립되지 않는다(adversarial 렌즈 발견) — 실측 결과 `ClipRRect`가 사진+정보 영역 전체를 이미 감싸고 있어 실제로는 계속 클립되고(모서리만 각짐), 텍스트는 14px 패딩 안에 있어 10px 라운드 모서리 영역에 닿지 않는다
  - `wishedListingIdsProvider`가 로딩 중일 때 하트가 잠깐 "안 찜함"으로 보인다(adversarial 렌즈 발견) — `AsyncValue` 기반 provider 전반(예: `recentListingsProvider`)이 공유하는 표준 로딩 프레임 동작이며 이 스토리가 새로 만든 회귀가 아니다
  - 면책 문구가 web TSX와 Dart에 각각 손으로 복사돼 있고 둘을 묶는 테스트가 없다(adversarial 렌즈 발견) — 이 레포 전체에 그런 교차언어 골든 테스트 관례가 없어(다른 한국어 문자열도 전부 이렇게 중복) 이 스토리만의 결함이 아니다
  - 찜 목록에서 `embed==null`을 항상 "판매완료"로 표시해 삭제와 판매완료를 구분하지 않는다(edge-case-hunter 렌즈 발견) — spec Never 섹션이 이 구분("삭제된 매물 배지")을 명시적으로 범위 밖으로 뒀고, `wishlists` FK가 `on delete cascade`라 하드삭제된 매물의 찜 행 자체가 함께 사라지므로 남은 행의 `embed==null`은 구조적으로 sold만을 뜻한다(web DW-417과 동일 근거)
  - `WishlistRepository.toggle`의 유니크 위반(`23505`) 무시 분기가 테스트되지 않는다(intent-alignment 렌즈 발견) — 이 레포는 네트워크를 직접 호출하는 리포지토리 메서드를 SupabaseClient mock 없이 수동/E2E로만 검증하는 기존 관례를 갖고 있고(`listings_repository`류 테스트도 동일), 이 관례를 벗어나는 새 테스트 인프라 도입은 스코프 확장이다

### 2026-08-08 — Review pass (follow-up, 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 16 (high 0, medium 4, low 12)
- defer: 3 (medium 2, low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[medium]` `[patch]` 카드 신뢰속성 뱃지가 카드 탭을 삼킨다 — 오버레이가 `InkWell` 위에 겹치는데 웹 원본의 `pointer-events-none`이 이식되지 않았다(adversarial 렌즈가 프로브 위젯테스트로 `taps=0` 실측). `Positioned(... child: IgnorePointer(...))`로 감쌈
  - `[medium]` `[patch]` 카드 진입점 3곳(홈·검색·AI)의 `ListingCard`에 `key`가 없어 `WishButton`의 낙관적 하트 상태가 다른 매물로 샌다 — 1차 패스가 같은 결함을 `wishlist_screen.dart` 한 곳만 고쳤다(adversarial 렌즈가 프로브로 `leakedFilledHeart=true` 실측, edge-case-hunter 독립 발견). 세 곳 모두 `key: ValueKey(id)` 추가
  - `[medium]` `[patch]` `wishlistProvider`가 wire 값에 `e.embed?['status'] as String?` 하드 캐스트를 써, 한 행만 어긋나도 찜 탭 전체가 에러 화면이 된다(레포 전역은 `is String` 방어 파싱, adversarial·edge-case-hunter 독립 발견) — 엔트리당 1회 방어 파싱으로 교체(중복 평가도 함께 제거)
  - `[medium]` `[patch]` `wishedListingIdsProvider`가 non-autoDispose인데 무효화 지점이 찜 토글 성공 하나뿐이라, 앱 기동 시 조회가 한 번 실패하면(빈 Set으로 조용히 삼킴) 프로세스가 사는 동안 모든 하트가 빈 채로 굳는다(adversarial 렌즈 발견) — 홈 탭 `onActivate`에 무효화 추가(검색·AI는 탭이 아니라 홈에서 push되는 화면이라 이 한 곳이 세 진입점을 함께 복구)
  - `[low]` `[patch]` `TrustAttributesCardOverlay.build`가 뱃지 유무에 따라 `Positioned`/`SizedBox`를 갈라 반환한다 — `listing_photo_widgets.dart`가 `PhotoCountBadge`에서 정확히 이 패턴을 "구조로 막는 편이 문서화보다 낫다"며 걷어낸 선례를 주석으로 인용하면서 정반대로 구현했다(edge-case-hunter 렌즈 발견). 호출부가 위치를 정하도록 되돌림
  - `[low]` `[patch]` `Clip.none` 전환으로 `InkWell` 잉크 스플래시가 카드 10px 모서리 밖으로 네모나게 번진다 — 1차 패스가 "안쪽 `ClipRRect`가 잡아준다"는 근거로 reject했으나, 잉크는 가장 가까운 조상 `Material`(=Card, `ClipRRect`보다 위) 레이어에 그려지므로 그 판단이 틀렸다(adversarial 렌즈가 Flutter `material.dart` 소스로 반증, edge-case-hunter 독립 발견). `InkWell.customBorder`로 잉크 모양만 카드 모서리에 맞춤
  - `[low]` `[patch]` 카드 뱃지에서 웹이 "최저선"이라고 명시한 텍스트 그림자가 빠졌다 — 웹은 배경 불투명도를 85%→70%→45%/35%로 낮추면서 흰 글자+semibold+`text-shadow`를 대비 하한으로 남겼다고 `badgeClassName` 주석에 적어 뒀다(intent-alignment 렌즈 발견). onCard 스타일에만 `shadows:` 추가
  - `[low]` `[patch]` `WishButton._toggle`이 `await` 뒤 `mounted` 확인 없이 `ref.invalidate`를 호출해, 토글 직후 화면을 떠나면 성공한 쓰기가 "찜 토글 실패"로 로깅되고 두 provider 무효화가 통째로 건너뛰어진다(edge-case-hunter 렌즈 발견) — `if (!mounted) return;` 추가
  - `[low]` `[patch]` `_pending`으로 `onTap`이 null인 동안에도 `Semantics(button: true)`가 활성 버튼이라고 낭독한다(adversarial 렌즈가 시맨틱 트리 프로브로 실측) — `enabled: !_pending` 추가
  - `[low]` `[patch]` 찜 버튼 44×44가 `listing_card.dart`의 상수와 `wish_button.dart`의 리터럴로 따로 산다 — 1차 패스가 사진 비율에서 고친 것과 같은 중복인데 바로 옆 코드에 남아 있었다(adversarial 렌즈 발견). `kWishButtonSize` 하나로 통일
  - `[low]` `[patch]` `WishlistRepository._wishlistListingColumns`가 ListingCard 목록 select의 **네 번째** 자리인데 `docs/conventions.md` §4.1 락스텝 목록은 여전히 3곳만 적고 있다 — 대장 #67(9.4가 필드는 계약에 넣고 select엔 안 물어 조용히 빠진 사례)이 열렸던 바로 그 자리다(adversarial 렌즈 발견). §4.1에 등록
  - `[low]` `[patch]` `listing_card_test.dart`가 카드의 신뢰속성 배선을 전혀 보지 않아, `ListingCard`의 오버레이 블록을 통째로 지워도 스위트가 green이다(verification-gap 렌즈가 뮤테이션으로 실증, intent-alignment 독립 지적) — 뱃지 렌더/미렌더 + 뱃지 탭이 카드 `onTap`을 발화하는지 단언 추가
  - `[low]` `[patch]` 홈·AI 진입점의 `wished:` 주입을 보는 테스트가 없어 두 곳을 동시에 지워도 green이다(검색 화면만 배선 테스트 존재, verification-gap 렌즈가 뮤테이션으로 실증) — 두 화면 배선 테스트 신규
  - `[low]` `[patch]` 토글 성공 후의 두 provider 무효화(1차 패스의 자기 패치 포함)를 아무도 관찰하지 않아 두 줄을 지워도 green이다(verification-gap 렌즈가 뮤테이션으로 실증) — 조회 횟수 카운팅 테스트 추가
  - `[low]` `[patch]` `wishlistProvider` 본문(§6에 방금 등록한 FR11 id 좁히기·`_blockedTitle`·대표사진 부착)은 어떤 테스트로도 **실행되지 않는다** — 모든 테스트가 provider 자체를 override한다(verification-gap 렌즈 발견, intent-alignment 독립 지적). fake 레포로 본문을 직접 도는 테스트 신규 + §6의 과장된 커버리지 문구 정정
  - `[low]` `[patch]` 상세 select의 신뢰속성 3컬럼을 보는 검사가 없어, 두 select에서 지워도 상세 신뢰속성 섹션이 조용히 사라질 뿐 스위트는 green이다(AC2의 유일한 데이터 경로, verification-gap 렌즈가 뮤테이션으로 실증) — 컬럼 목록을 명명 상수로 뽑아 두 메서드가 공유하게 하고 단언 추가
- deferred (장부에 신규 등재, 기존 항목은 건드리지 않음):
  - `[medium]` `WishlistRepository.fetchCovers`가 `_fetchCovers`와 같은 무제한 `.inFilter()`라 PostgREST `max_rows=1000` 무성 절단을 물려받았는데, 기존 장부 항목의 트리거는 `_fetchCovers`만 지목한다 — 한쪽만 고치면 항목은 닫히고 찜 경로는 깨진 채 남는다
  - `[medium]` 판매완료·RLS차단 찜 매물을 앱 안에서 해제할 경로가 전혀 없다(web `/wishlist`는 같은 타일에 `RemoveWishButton`을 두고 그 근거를 코드에 남겼다) — 스펙 I/O 매트릭스가 차단 타일 동작을 완결적으로 규정해 스펙 위반은 아니지만, 데모에서 찜이 쌓이면 그대로 보인다
  - `[low]` `ListingCard`는 폭 제약 없는 부모에 아예 놓일 수 없다 — 찜 버튼의 `isFinite` 가드가 돌기 전에 카드 내부의 별개 `Column(stretch)`이 먼저 죽는다(이번 패스에서 그 가드의 회귀 테스트를 쓰려다 실측 발견, 16.3이 만든 구조가 아님)
- rejected_as_noise (기록용, 근거 포함):
  - 카드 뱃지 행이 `Wrap`이라 폭이 좁으면 세로로 접혀 D5(개별 컴포넌트 내부 가로 배치를 접지 않는다)를 어긴다(edge-case-hunter 렌즈 발견) — 미러 원본인 web `TrustAttributes.tsx` 카드 분기가 `flex flex-wrap`이고 주석이 "뱃지가 3개 다 있어도 사진 폭을 넘지 않고 flex-wrap으로 줄바꿈된다"고 그 동작을 2026-08-05 승인 사항으로 명시한다. D5가 지목한 "신뢰속성 행"은 그 이전의 본문 흐름 안 행이고, 사진 위 오버레이는 웹이 명시적으로 접기를 택한 자리다
  - `didUpdateWidget`이 `_pending` 중이면 동기화를 건너뛰고 이후 재시도하지 않는다(edge-case-hunter 렌즈 발견) — 제안된 수정(`finally`에서 `widget.initialWished`로 재동기화)은 provider 재조회가 끝나기 **전에** 실행돼 낙관적으로 채운 하트를 눈앞에서 되돌린다. 고치려는 것보다 큰 회귀를 만든다
  - 재조회가 실패하면 `AsyncValue.error`가 찜 목록 전체를 에러 화면으로 대체한다(edge-case-hunter 렌즈 발견) — `recentListingsProvider`·`chatRoomsProvider` 등 이 레포의 모든 `AsyncValue` 화면이 공유하는 표준 동작이며 이 스토리가 만든 회귀가 아니다(1차 패스가 로딩 프레임 지적을 같은 근거로 reject한 것과 동일)
  - `key: const Key('wish_button')`이 모든 인스턴스가 공유하는 상수라 특정 매물의 버튼을 지목할 수 없다(adversarial 렌즈 발견) — 형제 관계가 아니라 런타임 충돌은 없고, 사용자 영향이 0인 반면 테스트 3개 파일의 참조를 바꿔야 한다. 이번 패스가 추가한 배선 테스트들은 아이콘 카운트로 충분히 단언된다
  - 스펙 자체의 메타데이터 자기모순 — `review_loop_iteration: 0`인데 트리아지 로그엔 1차 패스 기록이 있고, `warnings`가 방치돼 있으며, "테스트 기존 3종 확장"이라 적고 4개를 나열(adversarial 렌즈 발견) — `review_loop_iteration`은 `done` 스펙 재리뷰 시 워크플로가 0으로 리셋하는 값(설계된 동작)이고, 나열 수 불일치는 이번 패스의 Auto Run Result 재작성으로 해소된다

### 2026-08-08 — Review pass (follow-up, 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 16 (high 0, medium 3, low 13)
- defer: 2 (medium 2)
- reject: 11 (low 11)
- addressed_findings:
  - `[medium]` `[patch]` **찜 버튼이 사진 "N장" 배지를 가린다** — 웹 원본은 `absolute right-2 top-full mt-1`로 찜 버튼을 사진 **밖 아래**에 걸고 배지는 사진 안 우하단(`bottom-2 right-2`)이라 겹치지 않는데, 앱은 버튼을 사진 하단 경계에 **절반 겹쳐** 놓아 같은 우측 8px 라인에서 배지를 덮었다(edge-case-hunter 렌즈가 위젯 테스트로 두 rect 겹침 실측). 스펙 Design Notes도 원래 "사진 박스 바로 아래(`top-full`)"라고 적고 있었다 — `top: photoHeight + 4`로 이동하고, 웹이 제목·meta에 `pr-14`를 둔 것과 같은 이유로 가격 줄에도 우측 52px 여백 추가. 겹침 회귀 테스트 신규
  - `[medium]` `[patch]` **로그로 개인정보가 샌다** — `debugPrint('...: $e')`가 `PostgrestException` 전문을 찍는데, `wishlists` 유니크 위반 응답의 `details`에는 `Key (user_id, listing_id)=(uuid, uuid)`가 들어 있다. 이 레포는 `listings_repository.dart`에 "행 전체를 찍지 않는다 — 기기 로그로 샌다, debugPrint는 release에서도 살아 있다"는 규칙을 이미 적어 뒀다(adversarial 렌즈 발견) — 세 로그 지점 모두 예외 타입 + `code`만 남기도록 변경
  - `[medium]` `[patch]` **빈 뱃지 가드 테스트가 공허했다** — "뱃지 0개면 아무것도 안 그린다" 테스트가 `find.byType(Positioned) findsNothing`을 단언하는데, 2차 패스가 위치 결정을 호출부로 넘긴 뒤로 이 위젯은 어느 분기에서도 `Positioned`를 반환하지 않아 항상 통과했다(adversarial 렌즈가 가드를 지우고 실제로 green 확인, intent-alignment 독립 지적). AC1("값 유무와 무관하게 카드 높이 동일")을 실제로 잡는 단언으로 교체
  - `[low]` `[patch]` `Clip.none` 전환의 전제가 실측상 거짓이었다 — "찜 버튼이 카드 밖으로 걸쳐서 clip을 끈다"고 적혀 있으나 버튼 rect는 옛 배치에서도 카드 rect 안에 완전히 들어 있었다(adversarial 렌즈가 rect 실측). `Clip.antiAlias` 복원 + 2차 패스가 그 때문에 넣었던 `customBorder` 제거. "버튼 rect ⊂ 카드 rect" 회귀 테스트 신규
  - `[low]` `[patch]` `WishButton._toggle`의 `if (!mounted) return;`이 두 `invalidate` **앞**에 있어, 토글 직후 화면을 떠나면 쓰기는 성공했는데 어느 화면도 갱신되지 않는다(`wishedListingIdsProvider`는 non-autoDispose라 세션 내내 낡은 채 남는다). adversarial·verification-gap 독립 발견 — `await` 전에 컨테이너를 잡아 무조건 invalidate하도록 변경
  - `[low]` `[patch]` `didUpdateWidget`이 `listingId` 교체를 처리하지 않아, 정확성이 호출부 4곳의 `ValueKey`에만 의존한다(edge-case-hunter 발견) — 위젯 자체에서 무조건 리셋(B9: 규칙은 어길 수 없는 자리에)
  - `[low]` `[patch]` `docs/conventions.md` §4.1 락스텝 select 목록이 **목록 select 4곳만** 적고 상세 select(web `listings/[id]/page.tsx`·app `listingDetailColumns`)를 빠뜨렸다 — 이 스토리가 상세 select에 신뢰속성 3컬럼이 없어 `listingDetailColumns`를 새로 만든 바로 그 자리다(adversarial 발견). 상세 자리 등재
  - `[low]` `[patch]` 두 select 상수가 anon에서 `42501 permission denied`로 **select 전체를 실패시킨다**는 사실이 앱 코드 어디에도 없다 — web은 그래서 신뢰속성 컬럼을 `user ? ... : ''`로 가른다(adversarial 발견). 두 상수에 그 의존성과 강제 지점(라우터 전역 redirect)을 주석으로 기록
  - `[low]` `[patch]` 뮤테이션으로 실증된 회귀 테스트 공백 8건(verification-gap 렌즈가 각각 대상 줄을 지우고 green 확인) — 홈 탭의 찜-id 무효화·찜 화면 카드의 채워진 하트·`wishlistListingColumns`의 신뢰속성 3컬럼·`_entryStatus`의 비-String 가드·`listingDetailColumns`가 두 메서드에 실제로 쓰이는지(내용만 보던 테스트를 소스 사용처 단언으로 보강)·`23505` 무시 분기(순수 술어로 추출해 양방향 단언)·44×44 히트영역과 Semantics(label·enabled·toggled)·토글 중 언마운트 경로
  - `[low]` `[patch]` `ListingCard.wished`의 기본값 `false`가 조용한 함정 — 앞으로 카드를 쓰는 새 화면은 하트가 자동으로 생기되 상태는 항상 빈 채로 나오고 아무도 못 잡는다(intent-alignment 발견). `required`로 바꿔 컴파일 단계에서 강제
- deferred (장부에 신규 등재, 기존 항목은 건드리지 않음):
  - `[medium]` 에픽의 Story 16.3 AC 세 번째 절("옵션 희소도 표시 — 카드 상위 3~4·상세 카테고리 전량")이 이 스펙의 `<intent-contract>`에 옮겨지지 않아 미구현. 앱 모델엔 `options` 타입만 있고 칩 위젯은 없는데 찜 목록 select는 `options`를 이미 요청 중 — §4가 경고하는 "쿼리 비용은 내지만 표시는 안 되는" 상태
  - `[medium]` 차단 타일 `Opacity(0.6)`로 본문 대비 2.69:1(AA 4.5 미달, 직접 계산 확인) — 다만 미러 원본 web `/wishlist`도 `opacity-60`이라 앱만 고치면 톤이 갈라진다. web·app 동시 수정 자리로 이월
- rejected_as_noise (기록용, 근거 포함):
  - 찜 id 조회 실패를 빈 Set으로 삼켜 "모름"과 "찜 안 함"이 같게 보이고, 그 상태로 탭하면 insert→`23505` 무시로 **영원히 해제 불가**가 된다(adversarial·edge-case-hunter 독립 발견) — 코드를 직접 읽어 확인한 결과 이 연쇄는 성립하지 않는다. `toggle(listingId, wish: next)`는 목표 상태를 명시로 받고 `23505`를 "최종 상태는 찜됨"으로 처리하므로, 잘못 빈 하트도 한 번 누르면 **채워진 상태로 정합해지고** 재탭으로 정상 해제된다(추가 1탭이 전부). 빈 Set 삼키기 자체는 1차 패스가 web 동일 방침을 근거로 이미 reject
  - `toggle`의 `currentUser!` 비대칭(1차 패스 reject와 동일 주장) · 재조회 실패 시 `AsyncValue.error`가 목록 전체를 대체(2차 패스 reject와 동일 주장) — 새 근거 없음
  - `wishedListingIdsProvider`의 로그아웃 미정리(1차 패스에서 이미 장부 등재) · 차단 타일의 찜 해제 수단 부재(2차 패스에서 이미 장부 등재) — 신규 등재 대상이 아니라 기존 항목
  - `safeCardPhotoHeight`의 폴백이 도달 불가한데 공개 API + 전용 테스트를 갖는다(adversarial 발견) — 그 도달 불가 사실 자체는 2차 패스가 이미 장부에 등재했고, 가드를 지우는 것은 등재된 문제를 닫는 게 아니라 기록을 지우는 쪽이다
  - 카드 뱃지의 칩별 `BackdropFilter`가 스크롤 목록에서 비싸다(adversarial 발견) — 블러는 스펙 Boundaries가 명시한 요구사항이고, 지적 자체가 측정 없이 CSS 비용 모델을 옮겨 온 추정이다(B4는 양쪽에 적용된다). 실기기 프로파일은 Epic 16-6 범위
  - `isWishlistBlocked(embed, status)`의 두 인자가 어긋날 수 있다(adversarial 발견) — 유일한 호출부가 같은 embed에서 status를 뽑아 넘기고 FR11 판정은 테스트로 고정돼 있다. 순수 취향의 시그니처 변경
  - `searchAiOverride`가 Riverpod 대신 생성자 시접이라 DI가 두 갈래(adversarial 발견) — 이 레포엔 이미 `@visibleForTesting` 시접 관례가 자리잡았고(`ai_search_api.dart`의 `imageUrlBuilder` 함수 인자 시접 포함, 코드가 그걸 근거로 인용) 관례 위반이 아니다
  - 상세의 `accident_free` 행과 `accident_status` 뱃지가 모순될 수 있다(edge-case-hunter 발견) — 스펙 Never 절이 두 값의 통합을 명시적으로 범위 밖에 뒀고, 어긋날 쓰기 경로가 아직 없다(Design Notes·장부 DW-412 전제)
  - 카드 오버레이의 웹 대응 불투명도 hex가 색 드리프트 검사 밖이다(intent-alignment 발견) — 이 레포에 교차언어 골든 테스트 관례가 없다는 이유로 1차 패스가 면책 문구 중복을 reject한 것과 같은 근거

## Design Notes

**카드 레이아웃은 `epic-16-context.md`의 산문이 아니라 웹 현재 코드를 따른다.** `epic-16-context.md`(Aug 7 컴파일)는 "사진 바로 아래 신뢰속성 전용 행 → 차량명", "찜(♡)은 사진 밖 우상단 원형 버튼"이라고 적었지만, 이는 `epics-increment-2026-07-12.md`의 원안 문구를 그대로 옮긴 것이고 웹이 **2026-08-05에 사용자 승인으로 레이아웃을 바꾼 뒤** 그 계획 문서·컴파일된 컨텍스트가 갱신되지 않은 상태다. 실제 `web/src/components/listings/ListingCard.tsx`·`TrustAttributes.tsx`·`WishButton.tsx`(전부 "2026-08-05 사용자 승인" 주석 포함)는 신뢰속성 뱃지를 사진 위 좌상단에 절대배치로 겹치고(면책 제거), 찜 버튼은 사진 박스 바로 아래(`top-full`)에 건다. Epic 16의 Cross-Story Dependency 자체가 "이미 확정된 ListingCard 계약을 그대로 소비한다 — 재정의하지 않는다"고 못박으므로, 정본은 코드다. 이건 intent gap이 아니다 — 대체 불가한 유일한 정답(현재 배포된 웹 코드)이 있고, 계획 문서 쪽이 그저 늙은 것이다.

**신뢰속성 3컬럼과 `accident_free`는 별개다(혼동 금지).** `ListingDetail`엔 이미 `accidentFree`(bool, NOT NULL, "사고여부" 행)가 있다 — `accident_status`(신뢰속성, 3값+null)를 이것과 합치거나 어느 한쪽을 없애지 않는다. 두 값이 실제로 어긋날 수 있는 쓰기 경로가 아직 없어(DW-408 미착수) 오늘은 자기모순 화면이 발생하지 않는다(DW-412 실측 기록과 동일 전제).

**찜은 wire 필드가 아니다.** `ListingCardData`/`ListingDetail`에 `wished`를 넣지 않는다 — 카드/상세 위젯이 별도 파라미터로 받는다(`docs/conventions.md` §4 "찜 여부는 ListingCard wire 필드가 아니다"와 동일 원칙, 웹 sibling prop 패턴 미러).

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 182건 + 신규 신뢰속성/찜 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 로컬 Supabase에서 앱 계정으로 실제 찜 insert/delete가 성공하는지 1회 실측(RLS 정책 자체는 웹 Story 10.5가 이미 red/green 검증했으므로 재검증이 아니라 앱 경로의 배선 확인 목적).
- 실기기 시각 확인(뱃지 오버레이 가독성·찜 버튼 히트영역)은 Epic 16-6(SM-D 통합 시연 검증) 범위.

## Auto Run Result

**Status:** done

**요약:** 앱의 매물 카드·상세 화면에 신뢰속성 뱃지(무사고/1인소유/비흡연, 웹 `TrustAttributes.tsx` 판정 로직 미러)를 처음으로 붙이고, 하단 "찜" 탭의 플레이스홀더를 실제 찜 토글·목록 화면으로 교체했다. DB 스키마·RLS는 이미 존재해(`0017`·`0018`) 새 마이그레이션 없이, 웹이 이미 확정한 계약(판정 로직·색 톤·`wishlists` 조인·`isWishedListingBlocked` 판정)만 Flutter로 새로 구현했다. 찜 상태는 홈 미리보기·검색 결과·AI 결과 3개 진입점 전부에서 일관되게 보이도록 전체 찜 id 집합을 공유하는 단일 provider로 공급했다. 이후 2차(후속) 리뷰 패스에서 카드 탭 흡수·위젯 상태 누수 등 16건을, 3차(후속) 패스에서 찜 버튼이 사진 배지를 가리는 배치 오류·로그 개인정보 유출·공허하던 가드 테스트 등 16건을 추가로 수정했다(아래).

**변경 파일(1차 구현 + 2차·3차 리뷰 패치 합산):**
- `app/lib/features/listings/listing.dart` — `ListingDetail`에 `accidentStatus`/`isSingleOwner`/`isNonSmoker` 3필드 추가(`fromMap`·`withImages` 포함)
- `app/lib/features/listings/listings_repository.dart` — `fetchListing`/`fetchOwnListing` select에 3컬럼 추가, 그 컬럼 목록을 공유 명명 상수 `listingDetailColumns`로 추출(2차), `pickCoverImages`를 `WishlistRepository`가 재사용할 수 있게 공개 함수로 전환
- `app/lib/features/listings/listing_trust_widgets.dart` (신규) — 신뢰속성 판정 순수함수 + 카드용(사진 좌상단 오버레이, 반투명+블러+텍스트 그림자, 면책 없음)/상세용(뱃지+면책 결속) 위젯. 2차에서 위치 결정을 호출부로 넘김
- `app/lib/features/listings/listing_card.dart` — Stack 구조로 재설계해 신뢰속성 오버레이(2차: `IgnorePointer`)+찜 버튼 배치, `wished` 파라미터(3차: `required`), 사진 비율·버튼 크기 공유 상수, 폭 가드 순수함수(`safeCardPhotoHeight`). 3차에서 찜 버튼을 사진 아래로 완전히 내리고(`top: photoHeight + 4`, web `top-full mt-1` 미러 — "N장" 배지 가림 해소) 가격 줄에 우측 여백 추가, `Clip.antiAlias` 복원 + 2차의 `customBorder` 제거
- `app/lib/features/listings/listing_detail_screen.dart` — 신뢰속성 섹션 + 제목 줄 인라인 찜 버튼 삽입
- `app/lib/features/wishlist/wishlist_repository.dart` (신규) — `toggle`/`fetchWishedListingIds`/`fetchWishlist`/`fetchCovers` + 순수 `isWishlistBlocked` 판정, `ListingsRepository`와 동일한 생성자 주입 패턴. 3차에서 select 상수를 공개(`wishlistListingColumns`)해 검사 가능하게 하고, `23505` 무시 판정을 순수 술어 `isIgnorableWishInsertError`로 추출, 로그를 예외 타입+코드만 남기도록 변경
- `app/lib/features/wishlist/wishlist_providers.dart` (신규) — `wishlistRepositoryProvider`/`wishedListingIdsProvider`(전체 집합 1회 조회)/`wishlistProvider`. 2차에서 wire `status`를 방어 파싱으로 교체
- `app/lib/features/wishlist/wish_button.dart` (신규) — 낙관적 토글 위젯(즉시 반영, 실패 롤백+SnackBar, 연타 차단, 성공 시 두 provider 무효화). 2차에서 `mounted` 가드·`Semantics(enabled:)`·`kWishButtonSize` 공개. 3차에서 `await` 전에 잡아 둔 컨테이너로 무효화를 무조건 실행(이탈해도 갱신 보장), `listingId`가 바뀌면 위젯 스스로 상태 리셋, 로그 개인정보 제거
- `app/lib/features/wishlist/wishlist_screen.dart` (신규) — 찜 목록 화면(정상 카드/판매완료 회색 타일/빈 상태/에러, 항목마다 `ValueKey`)
- `app/lib/features/wishlist/wishlist_placeholder_screen.dart` — 삭제(더 이상 참조되지 않는 고아 파일)
- `app/lib/core/router/app_router.dart` — `tab_wishlist` builder를 `WishlistScreen`으로 교체 + 탭 재활성화 시 `wishlistProvider`(1차)·`wishedListingIdsProvider`(2차) 무효화
- `app/lib/features/auth/home_screen.dart`·`listings/search_screen.dart`·`ai_search/ai_chat_screen.dart` — 3 진입점 전부 `wishedListingIdsProvider`로 `wished` 주입 + `key: ValueKey(id)`(2차). `ai_chat_screen.dart`엔 테스트 주입 시접 `searchAiOverride`(`@visibleForTesting`) 추가
- `docs/conventions.md` — §6에 앱이 연 세 번째 이미지축 소비처(`WishlistRepository.fetchCovers`) 등록(규칙7)·커버리지 문구 정정, §4.1 락스텝 select 목록에 찜 목록 select 등록. 3차에서 §4.1에 **상세 select 자리**(web `listings/[id]/page.tsx`·app `listingDetailColumns`)를 추가 등재
- 테스트: 신규 9종(`listing_trust_widgets_test`·`wishlist_repository_test`·`wish_button_test`·`wishlist_screen_test`·`search_screen_test` + 2차의 `home_screen_wishlist_test`·`ai_chat_screen_test`·`wishlist_providers_test`·`listings_repository_detail_columns_test`) + 기존 4종 확장(`app_router_test`·`listing_card_test`·`listing_model_test`·`listing_detail_screen_test`)

**리뷰 결과 — 2차(후속) 패스, 4개 레이어 병렬(adversarial·edge-case-hunter·verification-gap·intent-alignment):** patch 16건(medium 4, low 12) · defer 3건(medium 2, low 1) · reject 5건 · intent_gap·bad_spec 0건.
medium 4건 요지 — (1) 신뢰속성 뱃지가 `InkWell` 위에 겹쳐 뱃지를 탭하면 카드가 안 열린다(웹의 `pointer-events-none` 미이식, 프로브로 `taps=0` 실측), (2) 카드 3진입점에 `key`가 없어 목록이 바뀔 때 하트 상태가 다른 매물로 샌다(1차 패스가 찜 목록 화면 한 곳만 고쳤던 같은 결함), (3) 찜 목록 provider가 wire `status`에 하드 캐스트를 써 한 행만 어긋나도 탭 전체가 에러, (4) 찜 id 집합 provider가 기동 시 한 번 실패하면 프로세스가 사는 동안 모든 하트가 빈 채로 굳는다. low 12건은 잉크 클립·텍스트 그림자·`mounted` 가드·접근성·상수 중복·문서 락스텝 등록과, 뮤테이션으로 실증된 회귀 테스트 공백 5건(카드 배선·홈/AI 배선·토글 무효화·`wishlistProvider` 본문·상세 select 컬럼).

**리뷰 결과 — 3차(후속) 패스, 4개 레이어 병렬(adversarial·edge-case-hunter·verification-gap·intent-alignment):** patch 16건(medium 3, low 13) · defer 2건(medium 2) · reject 11건 · intent_gap·bad_spec 0건.
medium 3건 요지 — (1) 찜 버튼이 사진의 "N장" 배지를 덮는다(웹은 버튼을 사진 **밖 아래**에 거는데 앱은 경계에 절반 겹쳤다, 두 rect 겹침 실측), (2) `debugPrint('...: $e')`가 `PostgrestException` 전문을 찍어 릴리스 로그에 `user_id`·`listing_id`가 남는다(이 레포가 이미 명문화한 금지 규칙 위반), (3) "뱃지 0개면 아무것도 안 그린다" 테스트가 존재하지 않는 위젯 타입을 단언해 항상 통과했다(AC1이 사실상 무방비였다). low 13건은 `Clip.none` 되돌리기·이탈 시 무효화 누락·`listingId` 교체 방어·`ListingCard.wished` 필수화·문서 락스텝 등록·anon 42501 의존성 기록과, 뮤테이션으로 실증된 회귀 테스트 공백 8건.

**검증(오케스트레이터가 직접 재실행해 확인, 구현·리뷰 에이전트 보고에 의존하지 않음):**
- `flutter analyze` → 0 issues
- `flutter test` → **240 passed**, 0 failed (1차 219 → 2차 228 → 3차 테스트 패치 반영)
- `flutter build web --dart-define-from-file=.env.json` → 빌드 성공
- 1차 구현 세션이 로컬 Supabase(Docker, `buyer@test.com` 세션)로 앱과 동일한 REST 호출을 재현: `wishlists` insert/delete 실측 성공(DB 확인 후 정리), `fetchListing`/`fetchWishlist` join select도 신뢰속성 3컬럼 포함해 실제 데이터로 성공 확인
- 2차 리뷰의 발견 4건(뱃지 탭 흡수·위젯 상태 누수·시맨틱 트리·잉크 클립)은 리뷰 서브에이전트가 프로브 코드를 실제로 실행하거나 Flutter 프레임워크 소스를 열어 실증했고, 테스트 패치 5건은 각각 대상 코드를 지워 red를 본 뒤 복원해 green을 재확인했다(B4)
- 3차 패치의 검사 증명은 **구현 에이전트의 red/green 보고를 믿지 않고 오케스트레이터가 형태를 바꿔 다시 깨 확인**했다(같은 표기에서만 성립하는 증명을 배제) — 찜 버튼 위치를 옛 공식이 아닌 다른 값(`photoHeight - 10`)으로, `listingId` 리셋 분기를 삭제가 아닌 조건 무력화(`if (false)`)로, 빈 뱃지 가드를 제거가 아닌 반환 위젯 교체(`Wrap(children: [])`)로, 홈 탭 무효화를 주석 처리로 각각 변형한 결과 대응하는 4개 테스트가 정확히 red가 됐고, 백업본 원복 후 240건 전부 green으로 복귀했다(`git checkout` 미사용 — 커밋 안 된 작업을 날리지 않기 위해)

**잔여 위험:**
- 찜 목록 대표사진 조회(`fetchCovers`)가 무제한 `.inFilter()`라 기존 장부의 `max_rows=1000` 무성 절단을 물려받았다 — 신규 등재(기존 항목의 트리거는 `_fetchCovers`만 지목).
- 판매완료·RLS차단 찜 매물을 앱 안에서 해제할 경로가 없다(web엔 있음) — 신규 등재, Epic 16-6 시연 전 결정.
- `ListingCard`는 폭 제약 없는 부모(가로 스크롤)에 놓일 수 없다 — 신규 등재(16.3이 만든 구조 아님).
- `wishedListingIdsProvider`가 로그아웃/계정 전환 시 정리되지 않는다 — 1차 패스에서 이미 등재(기존 provider 아키텍처 전반의 문제).
- `WishlistRepository`의 Supabase 직접 호출 경로(`toggle`의 유니크 위반 분기 등)는 이 레포의 기존 관례대로 자동 mock 테스트 대상이 아니라 수동/E2E 확인에 의존한다.
- 카드 신뢰속성 뱃지·찜 버튼의 실기기 시각 확인(가독성·히트영역)은 스펙이 처음부터 Epic 16-6(SM-D 통합 시연 검증)으로 이관.
- `ai_chat_screen.dart`에 테스트 전용 주입 시접(`searchAiOverride`)이 프로덕션 생성자에 추가됐다 — `API_BASE_URL`이 컴파일타임 상수라 이 화면의 카드 렌더 경로를 테스트로 밟을 다른 방법이 없어 택했고, 레포에 이미 있는 `@visibleForTesting` 관례를 따랐다(3차 패스가 이 관례의 선례를 `ai_search_api.dart`의 `imageUrlBuilder`에서 확인해 유지 결정).
- **에픽 Story 16.3의 세 번째 인수조건(옵션 희소도 표시)이 이 스펙에 옮겨지지 않아 미구현이다** — 3차 패스에서 발견해 신규 등재. 자리(어느 스토리가 가져갈지)는 사용자 결정이 필요하다.
- 차단 타일의 대비가 AA 미달(2.69:1)인데 미러 원본 web도 같은 `opacity-60`이라 앱만 고치면 톤이 갈라진다 — web·app 동시 수정 자리로 신규 등재.
- 3차 패스에서 찜 버튼이 사진 아래로 내려가며 카드 정보 영역과 세로로 더 가까워졌다 — 위젯 테스트로 겹침 없음은 고정했으나 **실기기 시각 확인은 여전히 Epic 16-6 범위**.
- 후속 리뷰 권장 여부: **true** — 이번 패스 patch 점수 `3×3(medium) + 1×13(low) = 22` ≥ 5(고정 규칙).
