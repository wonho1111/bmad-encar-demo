---
title: '이미지·카드 재설계 (앱)'
type: 'feature'
created: '2026-08-07'
status: 'done'
baseline_revision: '766e6eef62ae32b797a741b83402ebba308849c8'
final_revision: '98ba11c6c1fd3c14e875b7c6bf74dfb936cbf278'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-16-context.md'
  - '{project-root}/docs/conventions.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 앱의 `listing_card.dart`·`listing_detail_screen.dart`는 사진을 전혀 그리지 않는다(모델엔 `imageUrl`/`imagePath`/`imageCount` 타입 슬롯만 있고 값이 채워지지 않음, `listings_repository.dart`가 `listing_images`를 조회하지 않기 때문). 웹은 이미 카드 대표사진·상세 갤러리를 렌더 중이라 앱만 사진 없는 목록으로 남아 있다.
**Approach:** `listings_repository.dart`가 `listing_images`를 조회해 대표사진 URL·장수(목록)와 전체 갤러리 URL(상세)을 붙이고, 카드에 5:3 대표사진+"N장" 배지+플레이스홀더를, 상세에 스와이프 갤러리+"k/N" 카운터를 추가한다. `getPublicUrl` 헬퍼(이미 존재, 미사용)로 웹과 동일하게 **공개 URL**을 클라이언트가 직접 만든다(서명 아님 — 아래 Design Notes 참조). 트리거된 장부 2건(DW-729 색 토큰 드리프트, DW-730 하드코딩 색 리터럴)도 이 스토리가 직접 만지는 파일 범위에서 함께 해소한다.

## Boundaries & Constraints

**Always:**
- 대표사진 = `listing_images`에서 `(sort_order, id)` 오름차순 최솟값 행. `is_cover` 컬럼은 절대 읽지 않는다(conventions.md §10.1, 쓰기 전용 파생값).
- 카드: 5:3 `AspectRatio` + `BoxFit.cover`. 사진 없음(`imageUrl` null/빈문자열)이면 "사진 준비중" 플레이스홀더(`AppColors.placeholderBg`). 로드 실패(`errorBuilder`)도 같은 플레이스홀더로 폴백.
- "N장" 배지는 `imageCount >= 1`이면 **사진 로드 성공 여부와 무관하게** 표시한다(장수는 DB 진실이지 이미지 로드 성공과 별개) — 불투명(반투명 아님) 검정 pill, 우하단.
- 상세 갤러리: `PageView` 스와이프 + "k/N" 카운터(0장이면 갤러리 영역이 placeholder, 크래시 없음 — CM-A).
- URL은 `app/lib/core/supabase/storage_helper.dart`의 기존 `getPublicUrl(bucket, path)`로 클라이언트가 만든다(api는 여전히 `storage_path`만 반환, conventions.md §10 CR2 불변).
- `listing_images` 쿼리는 `order by sort_order, id`를 항상 명시한다(2차 정렬키 누락은 실측된 과거 버그 패턴, §10.2).
- DW-729/DW-730은 이 스토리가 실제로 수정하는 파일(`listing_card.dart`, `listing_detail_screen.dart`)에 한정해 해소하고, `deferred-work.md`의 두 항목을 그 범위에 맞게 갱신한다(닫거나 잔여 범위로 좁힌다 — 신규 미등재).

**Block If:**
- 이 앱의 Supabase anon/로그인 세션으로 `listing_images`를 조회했는데 RLS가 실제로 거부하면(설계상 `select_own`/공개 `on_sale` 정책이 이미 허용함을 확인했지만, 실행 중 그 확인과 다른 결과가 나오면) 임의 우회(예: 다른 롤 키 사용)를 추가하지 말고 HALT한다.

**Never:**
- 웹 `ListingCardImage`의 하이드레이션-레이스 이중 감지(`onError` + `ref` 콜백)를 이식하지 않는다 — Flutter는 SSR이 없어 그 레이스 자체가 없다. `errorBuilder` 하나로 충분하다.
- 갤러리에 썸네일 스트립을 추가하지 않는다 — AC가 요구하는 건 스와이프+카운터뿐이며, 웹의 부가 기능이다(A2, 범위 최소화).
- DW-730의 나머지 23곳(chat/auth/sell 등 이 스토리가 안 만지는 파일)을 건드리지 않는다.
- `ListingCardData`의 기존 필드 구조(§4.1 락스텝 대상)를 바꾸지 않는다 — 이미 있는 타입 슬롯에 값만 채운다. `ListingDetail`도 필드 추가(`imageUrls`)만 하고 기존 필드는 안 건드린다.
- 서명 URL·TTL(3600초) 개념을 재도입하지 않는다 — 공개 버킷 전환(Story 9.0, `0014` 마이그레이션)으로 이미 제거됐다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 사진 있는 매물 카드 | `listing_images` N행 존재 | 대표사진(최소 `sort_order,id`) 5:3 cover + "N장" 배지 | 없음 |
| 사진 0장 매물 카드 | `listing_images` 0행 | "사진 준비중" 플레이스홀더, 배지 없음 | 없음 |
| 깨진 이미지 URL | `imageUrl` 있으나 파일 없음/404 | 사진은 플레이스홀더로 폴백, "N장" 배지는 그대로 유지 | `errorBuilder` |
| 상세 갤러리 스와이프 | N>1장 | 스와이프마다 "k/N" 카운터 갱신 | 없음 |
| 상세 갤러리 0장 | `listing_images` 0행 | 플레이스홀더 표시, 크래시 없음(CM-A) | 없음 |

</intent-contract>

## Code Map

- `app/lib/features/listings/listing.dart` -- `ListingDetail`에 `imageUrls`(`List<String>`, 기본 `const []`) 필드 + `withImages(List<String>)` 부착 헬퍼 추가 -- `fromMap`이 읽는 단일 `listings` row엔 없는 데이터(별도 `listing_images` 조인 결과)라 부착 지점이 필요
- `app/lib/features/listings/listings_repository.dart` -- `fetchListings`: 반환된 매물 id들로 `listing_images(listing_id, storage_path, sort_order, id)`를 배치 조회 → 매물별 대표사진(`sort_order,id` 최솟값)·장수 계산 → `getPublicUrl`로 공개 URL 생성 → 각 `ListingCardData.imageUrl`/`imageCount` 채움. `fetchListing`: 해당 id의 `listing_images` 전량을 `sort_order,id` 순 조회 → 공개 URL 리스트로 변환 → `ListingDetail.withImages`로 부착 -- web `attachCoverImages`/`fetchListingGalleryUrls`(`web/src/lib/listings.ts`)의 미러, §4.1 락스텝이 지목한 값-채움 지점
- `app/lib/features/listings/listing_photo_widgets.dart` (신규) -- `PhotoPlaceholder`(카메라 아이콘 + "사진 준비중", `AppColors.placeholderBg`) + 불투명 dark pill 배지 위젯(카드 "N장" · 갤러리 "k/N" 공유) -- 두 화면이 쓰는 동일 시각 요소를 한 곳에(web의 `PhotoPlaceholder`/뱃지 분리 구조 미러)
- `app/lib/features/listings/listing_card.dart` -- Column 최상단(패딩 밖)에 5:3 사진 셀 삽입(위쪽 모서리만 라운드), `imageUrl` 없으면 `PhotoPlaceholder`, 있으면 `Image.network(fit: cover, errorBuilder: → PhotoPlaceholder)`, `imageCount>=1`이면 배지. 같은 파일의 기존 `Color(0xFFA1A1AA)`(판매자 이름, 옛 zinc 팔레트 잔재 — 16.1이 놓친 자리, `Colors.*` grep엔 안 걸림)를 `AppColors.inkMuted`로 교체
- `app/lib/features/listings/listing_detail_screen.dart` -- "기본 정보" 블록 앞에 `ListingGallery(imageUrls: listing.imageUrls)` 삽입. 기존 `Colors.red`·`Colors.grey`·`Colors.green[100]`·`Colors.green[800]`·`Colors.grey[600]`×2(6곳, DW-730)를 역할별 `AppColors` 토큰으로 교체: red→danger, grey 계열→inkMuted, green[100]→trustGreenBg, green[800]→trustGreenInk
- `app/test/listing_card_test.dart` (신규) -- `imageUrl` 있음/없음/로드실패 3가지 + `imageCount` 0/1/N 배지 표시여부 단언
- `app/test/listing_gallery_test.dart` (신규) -- 0장 placeholder(크래시 없음) + N장 스와이프 시 "k/N" 갱신 단언
- `app/test/app_theme_color_drift_test.dart` (신규, DW-729) -- `AppColors` 17종과 웹 라이트 팔레트 hex 대조
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-729 `status: resolved`(+`resolution:`), DW-730 잔여범위·새 `trigger:`로 갱신(기존 항목 수정, 신규 등재 아님)

## Tasks & Acceptance

**Execution:**
- `app/lib/features/listings/listing.dart` -- `ListingDetail.imageUrls`/`withImages` 추가 -- 갤러리가 그릴 데이터의 부착 지점
- `app/lib/features/listings/listings_repository.dart` -- `fetchListings`/`fetchListing`에 `listing_images` 조회·매핑 추가 -- 카드·상세 양쪽의 실제 값 채움(§4.1 락스텝 대상 call site)
- `app/lib/features/listings/listing_photo_widgets.dart` (신규) -- `PhotoPlaceholder` + 카운트/배지 pill 위젯 -- 카드·갤러리 공유
- `app/lib/features/listings/listing_card.dart` -- 사진 셀 + 배지 삽입, `Color(0xFFA1A1AA)` 토큰화 -- 카드 AC
- `app/lib/features/listings/listing_detail_screen.dart` -- `ListingGallery` 삽입, 기존 6개 색 리터럴 토큰화(DW-730) -- 상세 AC + 장부 해소
- `app/test/listing_card_test.dart` -- I/O 매트릭스 카드 3행 단언
- `app/test/listing_gallery_test.dart` -- I/O 매트릭스 갤러리 2행 단언
- `app/test/app_theme_color_drift_test.dart` -- DW-729 해소용 드리프트 단언. `web/src/app/globals.css`를 상대경로로 못 읽으면(테스트 샌드박스 제약) 17개 hex를 리터럴 상수로 테스트에 박고 옆에 "이 값은 globals.css 정본과 반드시 같아야 한다"는 근거 주석을 남긴다. 채택 전 값 하나를 일부러 틀리게 바꿔 red 확인 후 되돌린다
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-729/DW-730 갱신 -- 장부 규칙(B8), 트리거 소진 반영

**Acceptance Criteria:**
- Given 사진이 있는 매물, when 목록 화면에서 카드를 렌더하면, then 대표사진이 5:3 `BoxFit.cover`로 보이고 우하단에 불투명 "N장" 배지가 표시된다
- Given 사진이 없는 매물, when 카드를 렌더하면, then "사진 준비중" 플레이스홀더가 보이고 배지는 없다
- Given `imageUrl`은 있으나 실제 파일이 없는 경우, when 카드를 렌더하면, then 이미지는 플레이스홀더로 폴백하되 "N장" 배지는 그대로 남는다
- Given N장(N>1) 사진이 있는 상세 화면, when 사용자가 스와이프하면, then 카운터가 "k/N"으로 갱신된다
- Given 사진이 0장인 매물의 상세 화면, when 화면을 열면, then 갤러리 영역이 플레이스홀더로 표시되고 크래시가 없다
- Given `app_theme_color_drift_test.dart`, when 앱·웹 어느 한쪽 hex 값을 일부러 다르게 바꾸면, then 테스트가 red가 되고 원복하면 다시 green이다
- Given 이 스토리가 종료되면, when `deferred-work.md`를 열면, then DW-729는 `status: resolved`이고 DW-730은 잔여 범위·새 `trigger:`로 갱신돼 있다

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (medium 3, low 6)
- defer: 1 (low 1)
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` `deferred-work.md`의 DW-729/DW-730 닫음 형식이 `.claude/skills/bmad-loop-sweep/deferred-work-format.md`의 정본 규격(`status: done <date>` + 그 직후 `resolution:`)과 어긋났다(DW-729는 `status: resolved`+순서 역전, DW-730은 `status: open`인데 예약어 `resolution:`을 씀) — DW-729는 `status: done 2026-08-07`+`resolution:` 순서로 정정, DW-730은 미완결 상태이므로 `resolution:`을 비예약어 `progress:`로 개명(내용은 그대로)
  - `[low]` `[patch]` `_fetchCovers`의 "청크 불필요" 주석이 존재하지 않는 앱 페이징을 근거로 들었다(`grep -rE '\.range\(|\.limit\('` 0건 확인) — 실제 근거(작은 데모 데이터셋이 단일 `.inFilter()` 쿼리 길이 한도 안에 든다)로 정정
  - `[medium]` `[patch]` 상세 갤러리 조회(`fetchListing`)가 대표사진 선정(`_fetchCovers`)과 달리 `(sort_order,id)` 클라이언트측 2차 방어(#47-2/#59 전례)가 없었다 — 공유 비교자 `compareImageOrder`를 추출해 양쪽에 적용하고, `listings_repository_image_order_test.dart`(6건, 동점 케이스 포함)로 커버리지 추가
  - `[low]` `[patch]` `PhotoPlaceholder.compact`가 어디서도 `true`로 안 쓰이는 죽은 코드(같은 diff의 "썸네일 스트립 이식 안 함" 코멘트와 자기모순, A2 위반) — 파라미터·분기 제거
  - `[low]` `[patch]` `ListingGallery`가 `imageUrls` 교체 시 `_index`를 리셋하지 않아 "5/3" 같은 불가능한 카운터가 될 잠재 결함 — `didUpdateWidget`으로 인덱스·컨트롤러 리셋 추가
  - `[low]` `[patch]` `listing_card_test.dart`의 "성공" 테스트명이 실제로 증명 못 하는 것(Flutter 테스트 바인딩이 모든 HTTP를 항상 실패로 가로챔, SDK 확인)을 증명하는 것처럼 보였다 — 테스트명·주석을 실제 검증 범위(네트워크 응답 전 위젯 트리 구성)로 정정, 단언은 불변
  - `[low]` `[patch]` `fetchOwnListing`(판매자 수정 경로)이 `imageUrls`를 조용히 빈 채로 둔다 — 향후 수정화면에 사진 섹션을 추가하려는 사람이 착각하지 않도록 근거 주석 추가
  - `[low]` `[patch]` `_fetchCovers`의 `sortOrder is! int` 엄격 검사가 코드베이스 전반의 `_asInt` 관용적 강제변환 관례와 불일치 — `listing.dart`의 `_asInt`를 `asInt`로 공개 전환해 재사용
  - `[medium]` `[patch]` 색상 드리프트 테스트(`app_theme_color_drift_test.dart`)가 web CSS 정본을 못 읽으면 조용히 낡은 폴백값으로 넘어가 DW-729가 막으려던 바로 그 실패(값이 갈라져도 아무도 모름)를 재도입할 수 있었다 — 읽기 실패 시 `fail()`로 시끄럽게 실패하도록 정정, 폴백 상수는 자체 일치성 테스트로만 사용
- deferred (장부에 신규 등재):
  - `[low]` `epics-increment-2026-07-12.md`의 Story 16.2 AC 원문이 "서명" 표현을 정정 없이 그대로 갖고 있다(같은 문서의 Epic 9 AC 3곳은 Story 9.0 때 소급 "✎ 정정" 주석을 받았는데 16.2는 그 패스에서 빠짐) — 이번 스토리는 spec Design Notes에 정정 근거를 남기고 진행했으나 원본 계획 문서는 안 고쳤다(intent-alignment 렌즈 발견)
- rejected_as_noise (기록용, 근거 포함):
  - `Image.network`에 `loadingBuilder`가 없어 로딩 중 찰나에 빈 프레임이 보인다 — AC가 요구한 적 없고 web 원본(`ListingCardImage.tsx`/`ListingGallery.tsx`)도 로딩 상태를 별도 처리하지 않는다. web 대비 회귀가 아니다(edge-case-hunter 렌즈 발견)
  - 테스트가 서명 URL 대 공개 URL의 구분(FR11 접근제어 성질)을 검증하지 않는다 — 그 위험은 Story 9.0(마이그레이션 `0014`)이 이미 검토하고 수용한 기존 트레이드오프이며 이 스토리가 만들거나 악화시킨 게 아니다(intent-alignment 렌즈 발견)
  - 색 토큰(DW-729)·하드코딩 색(DW-730) 해소가 Story 16.2의 AC 원문엔 없는 범위다 — 두 항목 모두 장부에 "Story 16.2 착수 시" trigger로 이미 지정돼 있었고, 16-1 스펙이 DW-686/DW-681을 같은 방식으로 접수한 선례가 있어 이 프로젝트의 정상적인 트리거 관행이다(intent-alignment 렌즈 발견)
  - DW-730이 이번에 고친 7곳 자체에 회귀 방지 테스트가 없다 — 나머지 25곳도 똑같이 무방비인 채로 남는(DW-730 자신의 잔여 범위) 상태에서 7곳만 개별 테스트를 다는 것은 낮은 가치이며, DW-730 장부 항목이 fix_sketch (b)(전역 실행 검사)로 이 문제 전체를 이미 소유하고 있다(adversarial 렌즈 발견)

### 2026-08-07 — Review pass (후속 리뷰 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 1, medium 4, low 7)
- defer: 1 (low 1)
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` **AI 검색 결과 카드가 사진 없이 "N장" 배지만 뜨는 자기모순 상태였다.** `ai_chat_screen.dart`는 같은 `ListingCard` 위젯으로 AI 결과를 그리는데, api는 `image_url`을 절대 채우지 않고 `image_path`+`image_count`만 보낸다(`api/app/schemas/ai.py`, conventions.md §10 CR2). 이 스토리가 카드에 사진 셀을 붙이기 전엔 아무도 사진을 안 그려 문제가 없었으나, 붙이고 나니 AI 결과 전건이 "사진 준비중" 위에 "N장"이 얹히게 됐다 — 이 diff가 만든 신규 결함이다. web `resolveCardImage`(`web/src/lib/api/aiSearch.ts`)를 `parseSearchResult`에 미러해 `image_path`→공개 URL 변환을 **응답 매핑 계층에서 한 번** 수행하도록 했고(`listing.dart:53-68` 주석이 이미 이 방향과 "Epic 16의 몫"임을 명시하고 있었다), 경로가 없으면 `image_count`도 0으로 강제해 모순 자체를 없앴다. `getPublicUrl`이 전역 supabase를 요구해 단위테스트에서 못 쓰므로 `imageUrlBuilder` 주입 이음매를 두고 web `aiSearch.test.ts` 미러 4건 추가. 버킷명이 두 곳에서 필요해져 `listing_images_bucket.dart`(web `bucket.ts` 미러)로 앱 정본 상수를 뽑았다
  - `[medium]` `[patch]` 사진 조회(`_fetchCovers`·`fetchListing`의 `listing_images` 쿼리)에 try/catch가 없어, 사진 쿼리 하나가 실패하면 매물 데이터는 이미 받아왔는데도 목록·상세 화면이 통째로 죽었다 — 이 스토리 전에는 사진이 없어도 목록이 멀쩡히 떴으므로 가용성 회귀다. 두 쿼리를 각각 감싸 사진 없는 상태로 우아하게 강등시키고, 실패는 `debugPrint`로 남겨 "판매자가 사진을 안 올림"과 구분되게 했다
  - `[medium]` `[patch]` 색 드리프트 테스트의 "17종 전부다" 단언이 **아무것도 보지 않았다** — 양쪽 다 같은 파일 안에서 손으로 쓴 맵의 길이를 하드코딩된 17과 비교하고 있어, `AppColors`(실제 19개 선언)에 토큰을 추가하고 매핑에 옮기는 걸 잊어도 green이었다. DW-729가 막으려던 실패가 새 토큰에 대해선 그대로 열려 있는데 장부는 done으로 닫혀 있었다. `app_theme.dart`를 실제로 파싱해 선언 집합 == 매핑 키 ∪ 명시적 제외 목록을 대조하도록 교체. **추가 정정(이 세션의 자체 검증에서 발견):** 구현이 처음 쓴 정규식은 `static const <name> = Color(...)`만 잡고 `static const Color <name> = ...`(타입 명시, 똑같이 합법인 Dart)는 놓쳤다 — 구현이 보고한 red/green 증명이 자기가 쓴 표기 형태에서만 성립했다. 타입 표기를 선택사항으로 만들어 양쪽 형태 모두 red가 되는 것을 직접 확인했다
  - `[medium]` `[patch]` `listings_repository_image_order_test.dart`가 `_pickCover`/`_sortGallery`를 **테스트 파일 안에 재구현**해 단언하면서 헤더 주석엔 "두 소비처도 같은 규칙으로 동작함이 보장된다"고 적혀 있었다 — 보장되지 않는다(어떤 테스트도 `ListingsRepository`를 만들지 않는다). 대표사진 누적·카운트 증가·행 스킵·갤러리 파싱을 `pickCoverImages`/`sortGalleryPaths` 순수 함수로 뽑아 `@visibleForTesting`으로 노출하고, 테스트가 재구현 대신 **실제 함수**를 부르게 했다. 헤더 주석도 안 보는 것(Supabase 쿼리 자체·`getPublicUrl`·버킷명)을 명시하도록 정정
  - `[medium]` `[patch]` `Image.network`에 디코드 크기 제한이 없어 원본을 5:3 셀에 풀 해상도로 디코드했다. 로컬 Storage 실측 결과 원본은 **1600×992 · 161KB · `cache-control: no-cache`**(디코드 시 약 6.3MB/장)이고 목록엔 페이지네이션이 없다 — `LayoutBuilder`+`cacheWidth`로 표시 크기에 맞춰 디코드하도록 카드·갤러리 양쪽 수정
  - `[low]` `[patch]` "N장"이 DB 행 수가 아니라 **파싱에 성공한 행 수**인데 코드 주석은 "DB 진실"이라 단언했다(계약-외 행은 카운트 증가 전에 `continue`) — 주석을 실제 의미로 정정하고, 스킵한 행은 `debugPrint`로 남겨 이상 데이터가 조용히 사라지지 않게 했다
  - `[low]` `[patch]` `PhotoCountBadge`가 `Positioned`를 반환해 `Stack` 밖에서 쓰면 런타임에 죽는데 그 제약이 문서에도 assert에도 없었다 — 재사용을 위해 만든 공유 위젯 파일이라 함정이 넓어진다. 주석으로 막지 않고(B9: 주석은 계약이 아니다) `Positioned`를 호출부로 옮겨 제약 자체를 구조적으로 없앴다
  - `[low]` `[patch]` 빈 문자열 `storage_path`가 `is String` 검사를 통과해 대표사진 자리를 차지할 수 있었다(web `resolveCardImage`는 빈 경로를 경로 없음으로 취급) — 두 파싱 루프에 `.trim().isEmpty` 가드 추가
  - `[low]` `[patch]` `listing_card_test.dart`가 `errorBuilder`를 기다리려고 **실시간 1초**를 잤다(`runAsync` + `Future.delayed(1s)`) — CI 부하 시 간헐 실패의 전형이자 고정 비용. 플레이스홀더가 뜨는 즉시 빠져나가는 상한 폴링(50ms×최대 2초)으로 교체
  - `[low]` `[patch]` AC가 요구한 5:3·`BoxFit.cover`·우하단·불투명을 어떤 단언도 고정하지 않았다(테스트는 위젯 타입·텍스트 존재만 확인) — `AspectRatio.aspectRatio == 5/3`, `Image.fit == BoxFit.cover`, 배지 `Positioned(bottom:8,right:8)`, 배지 배경 알파 불투명을 단언으로 추가
  - `[low]` `[patch]` 직전 패스가 loadingBuilder 지적을 "web 원본도 로딩 상태를 별도 처리하지 않는다"는 근거로 기각했는데, 실제 web은 `next/image` + `loading="lazy"` + `aspect-[5/3]`로 자리 선점까지 한다 — 기각 근거가 원본과 달랐다. 결론(별도 loadingBuilder 불필요)은 유지하되 **맞는 근거**로 정정한다: 앱도 `AspectRatio`가 자리를 미리 잡아 지연 로드에도 레이아웃이 밀리지 않는다(NFR7과 같은 성질)
  - `[low]` `[patch]` DW-730 잔여 범위를 스펙이 23으로, 직전 리뷰 로그가 25로 적어 한 문서 안에서 숫자가 갈렸다 — 아래 Auto Run Result에서 두 숫자가 각각 무엇을 세는지 밝혀 정리했다(장부 항목 자체는 오케스트레이터 소유라 건드리지 않았다)
- deferred (장부에 신규 등재):
  - `[low]` 앱 `fetchListings`가 페이지네이션 없이 `on_sale` 전량을 가져오는 구조(이 스토리 이전부터 있던 것)에 16.2가 매물당 사진을 얹어 비용을 키웠다. 같은 무제한 id 목록이 `listing_images` 배치 조회의 `.inFilter()`에도 들어가, 매물 수가 커지면 PostgREST 쿼리스트링 한도에 먼저 닿는다(web은 같은 자리에 50개 청크를 둔다). trigger = 목록 페이지네이션 스토리 착수 시 또는 매물 100건 초과 시, `.range()`와 청크를 함께 도입
- rejected_as_noise (기록용, 근거 포함):
  - `.inFilter()`에 web처럼 50개 청크를 두지 않았다 — 스펙 Design Notes가 A2(과설계 방지)로 명시적으로 내린 설계 결정이고, 위 try/catch 패치로 한도 초과가 화면 전체를 죽이는 결합이 끊겼다(사진만 빠지고 목록은 뜬다). 재검토 자리는 위 defer 항목이 소유한다(edge-case·adversarial 렌즈 발견)
  - `ListingDetail.withImages`가 19개 필드를 수동 복사해 향후 필드 추가 시 누락 가능 — Dart의 일반적인 `copyWith` 관용이고, `ListingDetail`의 필드 추가는 conventions.md §4.1 락스텝 체크리스트가 이미 소유한다(edge-case 렌즈 발견)
  - `ListingGallery`가 공유 위젯 파일이 아니라 화면 파일에 있다 — 소비처가 상세 화면 하나뿐이라 아직 "공유" 요소가 아니다. 소비처가 둘이 되는 시점의 이동은 그때의 외과적 변경이며, 지금 옮기는 건 어떤 AC도 요구하지 않는 리팩터다(A3)(adversarial 렌즈 발견)
  - `Image.network`에 `semanticLabel`이, 플레이스홀더에 `Semantics`가 없다 — 접근성은 실제 갭이지만 이 프로젝트엔 이를 규정하는 규약(conventions.md·project-context.md)도 AC도 없다. 규약 없이 한 화면에만 넣으면 나머지 화면과 어긋난 사본이 하나 생길 뿐이다(adversarial 렌즈 발견)
  - 스펙 frontmatter `status`와 `sprint-status.yaml`이 불일치한다 — 이 워크플로 자체의 진행 중 부기다(리뷰 시작 시 `in-review`, 종료 시 `done`). 결함이 아니다(adversarial 렌즈 발견)
  - `fetchOwnListing`이 `imageUrls`를 빈 채로 두는 것을 주석으로만 막았다(B9 위반) — 판매자 수정 화면엔 아직 사진 섹션이 없다. 섹션을 붙이는 스토리는 데이터가 필요해지는 즉시 이 자리를 지나가므로, 지금 타입을 바꾸는 건 추측성 설계다(A2)(adversarial 렌즈 발견)

### 2026-08-07 — Review pass (후속 리뷰 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 16 (medium 4, low 12)
- defer: 4 (low 4)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` **색 드리프트 검사가 여전히 "저자가 쓴 표기"에서만 성립했다 — 2차가 같은 구멍을 한 축(타입 표기)만 넓혔던 자리다.** 완전성 검사의 정규식이 초기화식 모양(`Color(`·`Colors.`)까지 매칭해, `Color.fromARGB(...)`·`Color.fromRGBO(...)`·별칭(`= danger;`)으로 선언한 새 토큰은 통째로 안 보였다(리뷰가 실제로 넣어 green 확인). 선언 머리(`static const <이름> =`)만 매칭하고 "색이 아닌 멤버"는 명시 제외 목록으로 다루도록 교체했으며, 제외 목록이 낡으면 시끄럽게 실패하게 했다. **이번엔 표기를 6가지로 바꿔가며 red를 확인**했다(`Color(`·타입명시·`fromARGB`·`fromRGBO`·별칭·`Colors` 별칭) — 이 검사가 DW-729를 닫은 근거이므로 한 축만 시험하면 같은 실수가 반복된다
  - `[medium]` `[patch]` **사진을 화면에 실제로 붙이는 로직 전체가 어떤 테스트도 실행하지 않았다.** 리뷰가 `fetchListings`의 `image_url`/`image_count` 부착을 통째로 지우고 `withImages`도 없앴는데 전체 스위트가 그대로 green이었다(172/172) — 기능이 사라져도 CI가 못 잡는 상태였다. 부착·URL 조립부를 `attachCoverImages`/`buildGalleryUrls` 순수 함수로 뽑아(`@visibleForTesting`) 테스트가 **실제 함수**를 부르게 하고 7건을 추가했다. 배선을 4가지 다른 방식으로 깨(URL 제거·장수 제거·정렬 제거·covers 조회 무시) 전부 red, 원복 green을 직접 확인
  - `[medium]` `[patch]` **버킷명 상수가 아무 검사도 안 받고 있었다** — 리뷰가 `listingImagesBucket`을 틀린 값으로 바꿔도 전체 스위트가 green이었다(앱의 모든 사진 URL이 이 상수로 조립되므로 사진이 전부 깨지는 변경인데도). 파일에 있던 "migration 0014와 동기화 유지" 주석은 계약이 아니다(B9) — `0014_listing_images_public_bucket.sql`을 실제로 읽어 대조하는 검사를 추가했고, 틀린 값 → red, 원복 → green을 확인
  - `[medium]` `[patch]` **`conventions.md` §6이 스스로 요구하는 등록 의무를 이번 변경이 이행하지 않았다.** §6은 `listing_images` 조회 경로 목록을 두고 "새 조회 경로를 열면 여기에 추가한다(규칙7)"고 못박고, 심지어 같은 절이 **과거에 똑같이 빠뜨린 사고**를 ✎ 주석으로 기록하고 있다. 16.2가 앱에 조회 경로 2개(`_fetchCovers`·`fetchListing` 갤러리)를 새로 열었는데 둘 다 목록에 없었다 — 등록하고, 각 경로가 어떻게 좁혀지는지(둘 다 `_buyerQuery` 결과 id만 사용, 앱 세션이라 `0012`의 on_sale RLS가 DB에서도 이중 방어)와 **자동 강제 장치는 아직 없다**는 사실까지 함께 적었다
  - `[low]` `[patch]` 드리프트 검사가 web 라이트 팔레트를 자를 때 `:root`의 닫는 중괄호가 아니라 다음 `@media` 줄까지 잘라, 그 사이에 있는 아무 텍스트(주석 포함)나 빨아들였다(리뷰가 주석 하나로 비교값을 바꿔 실증) — `:root` 블록 자체의 끝에서 자르도록 정정
  - `[low]` `[patch]` `--color-accent-amber`를 파일 전체에서 `firstMatch`로 찾아, 다크 블록에 같은 변수가 생기면 라이트 고정 토큰을 다크 값과 비교하게 돼 있었다(리뷰가 다크 블록에 넣어 실증) — `@theme static` 블록 안으로 검색 범위를 좁힘
  - `[low]` `[patch]` 양쪽 모두 알파를 버리고 6자리 RGB만 비교해 불투명도 변경이 통과했다(`Color(0x80C0392B)` → green) — 매핑된 토큰이 전부 알파 `0xFF`임을 별도로 단언하게 해 RGB-only 비교가 안전한 이유를 검사로 만들었다. `0x80...` → red 확인
  - `[low]` `[patch]` 2차가 폴백 경로에서 걷어낸 `_fallbackWebLightPalette`(웹 팔레트 17개 사본)가 "참고용"으로 남고, 그 안 읽히는 사본을 지키는 전용 테스트까지 붙어 있었다 — **사본을 늘리지 않는 게 이 파일의 존재 이유**인데 스스로를 어긴 자리다. 상수와 그 테스트를 삭제
  - `[low]` `[patch]` 상세 화면이 갤러리를 실제로 그리는 배선(`ListingGallery(imageUrls: listing.imageUrls)`)을 검증하는 테스트가 없었다 — 그 줄을 지워도 전체 green(기존 갤러리 테스트는 위젯을 직접 pump하고, 라우터 테스트는 "없음" 분기만 본다). 실제 상세 화면을 pump해 카운터가 뜨는지 보는 테스트 추가, 줄 제거 → red 확인
  - `[low]` `[patch]` 2차가 넣은 `didUpdateWidget` 인덱스 리셋(사진 수가 줄었을 때 "5/3" 같은 불가능한 카운터 방지)에 테스트가 없어, override를 통째로 지워도 green이었다 — 3장 → 스와이프 → 1장 재pump 케이스 추가
  - `[low]` `[patch]` 두 사진 쿼리의 `try`가 순수 매핑 함수 호출까지 감싸고 있었다. Dart의 `catch (e)`는 `Error`도 잡으므로, 2차가 테스트 가능하게 막 뽑아낸 바로 그 함수들에 버그가 생기면 "사진 조회 실패"로 둔갑해 조용히 사진 없는 화면이 된다 — 가용성을 지키려고 넣은 강등이 버그 은폐막을 겸하게 된 셈이라, `try`를 `await` 한 줄로 좁혔다
  - `[low]` `[patch]` 대표사진 승자를 정하는 단 한 줄의 변수명 `currentComesFirst`가 실제 의미(**새 행**이 앞선다)의 반대였다 — 이름을 믿고 "고치는" 사람이 대표사진 선정을 뒤집어도 어떤 테스트도 못 잡는 자리라 `newRowComesFirst`로 개명(비교식은 불변)
  - `[low]` `[patch]` 계약 위반 행을 건너뛸 때 `debugPrint`가 **행 전체(map)를 통째로** 찍었다 — `storage_path` 첫 구간이 소유자 `user_id`(§10)이고 `debugPrint`는 release에서도 살아 있어, 컬럼 하나가 계속 어긋나면 새로고침마다 기기 로그로 샌다. `id`만 남기도록 축소
  - `[low]` `[patch]` "URL 없으면 장수도 0" 불변식이 두 생산자(AI 응답 매핑·저장소 경로)에 **손으로 각각** 쓰여 있고 공유 규칙으로는 어디에도 없었다 — 2차가 high로 잡은 "사진 없이 N장 배지만 뜨는 카드"가 세 번째 생산자에서 그대로 재발할 수 있는 구조다. 모든 생산자가 반드시 지나는 `ListingCardData.fromMap` 한 곳으로 옮겼다(B9)
  - `[low]` `[patch]` `imagePath` 필드 주석이 "앱 카드에 사진을 붙이는 것은 **Epic 16의 몫**"이라고 미래형으로 남아 있었다 — 이 diff가 그 일을 끝내고 `parseSearchResult`가 경로를 버리게 되면서 아무도 채우지 않는 필드가 됐는데, 주석만 읽으면 이미 끝난 일을 다시 하라고 지시하는 셈이다. 과거형으로 정정(구현 위치·§4.1 락스텝용으로만 남긴 슬롯임을 명시)
  - `[low]` `[patch]` 스펙 Design Notes가 "앱의 페이지당 매물 수는 훨씬 작다"는 **1차가 이미 거짓으로 판정한 근거**를 그대로 갖고 있었다(페이지 자체가 없다 — `.range()`/`.limit()` 0건). 1차는 같은 문장의 코드 주석만 고쳤고 스펙은 놔뒀다 — 다음 사람이 "왜 청크를 안 뒀나"를 찾을 때 읽는 건 스펙이다. 코드 주석과 같은 참인 근거로 정정
- deferred (장부에 신규 등재 4건 — 기존 항목은 수정하지 않았다):
  - `[low]` PostgREST `max_rows = 1000`(`supabase/config.toml:18`)이 무제한 `listing_images` 배치 조회를 **에러가 아니라 잘린 200 응답**으로 끊는다 — 2차가 넣은 try/catch가 아예 발동하지 않는 조용한 오답이고, 쿼리스트링 길이 한도보다 훨씬 이른 지점(매물 100~200건)에서 닿는다. 기존 페이지네이션 항목과 트리거는 이웃하지만 고장 방식이 달라 따로 적었다
  - `[low]` 홈 화면이 카드 4장을 그리려고 `on_sale` 전량 + 그 전량의 사진을 조회한다(`recentListingsProvider`가 `fetchListings` 결과에 `take(4)`) — 위 한도들에 가장 먼저 닿을 화면인데 증상이 그 자리와 연결되지 않는다
  - `[low]` 사진 **전송량**을 소유한 항목이 없다 — 실측 원본 1600×992·161KB·`no-cache`이고 `Image.network`엔 디스크 캐시가 없어 콜드 스타트마다 재다운로드된다. 2차의 `cacheWidth`는 디코드(메모리) 축만 고쳤다. 기존 항목은 "매물 수" 프레임이라 매물이 적어도 나는 장당 비용은 무주공산이다
  - `[low]` DW-730의 정본 `trigger:`가 이미 소진된 조건("Story 16.2 착수 시")을 들고 있고 살아 있는 조건은 표준 밖 키 `trigger(잔여 23곳):`에 있다 — 이번 세션은 기존 항목 수정 권한이 없어 신규로만 등재했다(오케스트레이터 소유)
- rejected_as_noise (기록용, 근거 포함):
  - 스펙 I/O 매트릭스에 2차가 추가한 두 동작(사진 쿼리 실패 시 우아한 강등, AI 카드 `image_path` 매핑)이 없다 — 매트릭스는 `<intent-contract>` 안이라 이 워크플로가 intent_gap HALT 없이는 손댈 수 없는 자리다. 그런데 두 동작 모두 해석이 하나뿐이라 intent gap이 아니다(넣자고 전체를 되돌릴 근거가 없다). 두 동작은 트리아지 로그와 Auto Run Result에 남는다(edge-case 렌즈 발견)
  - `ListingDetail.imageUrls`가 "사진 없음"·"조회 실패"·"미조회"를 `const []` 하나로 뭉갠다 — 조회 실패 시 카드는 "3장"인데 상세는 "사진 준비중"이라 앱이 자기모순을 보인다. 실재하는 결함이지만 닫으려면 nullable 타입 + 어떤 AC도 요구하지 않은 새 실패 UI를 만들어야 한다(A2). 발생 조건은 쿼리 실패 한정이고 새로고침으로 회복된다(adversarial 렌즈 발견)
  - 대표사진 선정 로직이 web `coverImages.ts`와 앱에 두 벌 존재한다(§10.2는 계산 지점 1곳을 말한다) — 앱은 별도 위젯으로 새로 구현하되 계약만 공유한다는 Epic 16의 전제 자체에서 나오는 것이고, 그 계약(`(sort_order,id)` 최솟값)은 양쪽이 같다(intent-alignment 렌즈 발견)
  - 이번 스토리가 장부에 신규 항목을 등재한 것이 Boundaries의 "신규 미등재"와 어긋난다 — 그 문장은 **DW-729/DW-730을 어떻게 다룰지**(새 항목으로 대체하지 말고 그 두 항목을 갱신하라)를 규정한 것이고, 리뷰가 발견한 별개 항목의 등재를 금지한 것이 아니다(intent-alignment 렌즈 발견)
  - Block If(RLS 실측)의 증거가 산출물이 아니라 스펙 산문뿐이다 — 2차에서 실제로 실행하고(anon 조회 → 행 반환, 공개 URL GET → 200) 그 결과를 기록했다. 스펙은 이 확인에 산출물을 요구하지 않는다(intent-alignment 렌즈 발견)
  - `Image.network`에 `loadingBuilder`가 없다(3회 연속 지적) — 2차에서 맞는 근거로 정리를 끝냈다: `AspectRatio`가 자리를 미리 잡아 지연 로드에도 레이아웃이 밀리지 않는다. 새 근거가 나오지 않았다(edge-case 렌즈 발견)

## Design Notes

**AC 원문의 "서명"은 낡은 표현이다.** `epics-increment-2026-07-12.md`의 16.2 AC는 "앱은 서명 원본 이미지를 Storage에서 받아 렌더한다(api는 storage_path만 반환하므로 앱이 서명)"이라고 적었지만, 이는 Story 9.0(`0014_listing_images_public_bucket.sql`)이 버킷을 **공개**로 전환하며 없앤 설계다(서명 URL은 발급 시점에만 RLS를 재확인하고 1시간 TTL 동안 유효해, `sold` 전환 후에도 유효한 채로 남는 실효성 문제가 있었다 — 마이그레이션 주석에 근거). 정본(`conventions.md §10`)은 지금도 "api는 URL을 절대 만들지 않는다(`storage_path`만 반환)"를 유지하지만, 클라이언트가 만드는 건 **서명 URL이 아니라 공개 URL**(`getPublicUrl`, 만료 없음)이다. AC의 "누가 URL을 만드는가"라는 핵심 의도는 그대로이고 메커니즘 단어만 낡았으므로, 이 스펙은 현재 코드에 맞는 "공개 URL"로 정정해 진행한다(intent gap 아님 — 대체 불가한 유일한 정답이 conventions.md에 이미 있다).

**DW-729를 conventions.md 절 대신 실행 테스트로 해소하는 이유(CLAUDE.md B9).** conventions.md에 색 토큰 절을 새로 만드는 방식(fix_sketch (a))은 이 프로젝트가 이미 겪은 실패(요약 사본이 원본보다 늙는 문제, `project-context.md:26`)를 값이 아니라 "테스트가 지키는 불변식"으로 대신 만든다 — 사본을 늘리지 않고 어긋남만 잡는다.

**DW-730 범위를 이 스토리가 만지는 2개 파일로 좁힌 이유(A2/A3).** 남은 23곳은 chat·auth·sell 등 이 스토리와 무관한 화면이다. 트리거는 "16.2 착수 시"였지 "16.2가 전부 고친다"가 아니었고, 무관한 파일을 건드리는 건 외과적 변경 원칙(A3)에 어긋난다. `deferred-work.md` 갱신 태스크가 잔여 23곳을 다음 트리거로 이월한다.

**배치 쿼리에 web처럼 50개 청크를 두지 않는 이유.** web의 청크는 PostgREST `.in()` 쿼리스트링 길이 한도(대량 매물) 때문이다. 앱에는 애초에 **페이지네이션이 없다** — `fetchListings`는 `on_sale` 전량을 한 번에 반환한다(`app/lib` 전역에 `.range()`/`.limit()` 0건, grep 확인). 그런데도 청크를 안 두는 이유는 "매물 수가 적어서"가 아니라 **데모 데이터 규모 자체가 작아** 단일 `.inFilter()` 쿼리스트링이 PostgREST URL 길이 한도 안에 들기 때문이다(과설계 방지, A2) — `listings_repository.dart`의 해당 주석과 같은 근거다. 재검토는 장부(`deferred-work.md`)의 관련 항목이 소유한다.

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 128건 + 신규 카드/갤러리/드리프트 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 실기기/에뮬레이터 기반 시각 확인(사진 비율·배지 위치·스와이프 제스처감)은 이 스토리 범위가 아니다 — Epic 16-6(SM-D 통합 시연 검증)이 실기기에서 확인한다.

## Auto Run Result

**Status:** done

**요약:** 앱의 매물 카드·상세 화면에 사진을 처음으로 붙였다. `listings_repository.dart`가 `listing_images`를 조회해 카드용 대표사진(최소 `(sort_order,id)`)·장수와 상세용 전체 갤러리 URL을 공개 URL(`getPublicUrl`, 서명 아님 — Story 9.0 이후 공개 버킷)로 만들어 붙이고, 카드는 5:3 사진+"N장" 배지+플레이스홀더를, 상세는 스와이프 갤러리+"k/N" 카운터를 새로 그린다. 트리거된 장부 2건(DW-729 색 토큰 드리프트, DW-730 하드코딩 색 리터럴)을 이 스토리가 만지는 파일 범위에서 함께 해소했다.

**변경 파일:**
- `app/lib/features/listings/listing.dart` — `ListingDetail.imageUrls`/`withImages()` 추가, `_asInt`를 `asInt`로 공개 전환(1차 리뷰 패치 8)
- `app/lib/features/listings/listings_repository.dart` — `fetchListings`/`fetchListing`에 `listing_images` 조회·대표사진 선정·갤러리 URL 부착 추가, `compareImageOrder` 공유 비교자 추출(1차 패치 3), `fetchOwnListing`에 의도 주석(1차 패치 7). **2차:** 두 사진 쿼리에 try/catch(우아한 강등)+실패 로그, 행 매핑을 `pickCoverImages`/`sortGalleryPaths` 순수 함수로 추출(`@visibleForTesting`), 빈 `storage_path` 가드, 버킷 상수를 공유 파일로 이동
- `app/lib/features/listings/listing_images_bucket.dart` (2차 신규) — 앱의 버킷명 정본 상수. web `bucket.ts` 미러
- `app/lib/features/ai_search/ai_search_api.dart` (2차) — `parseSearchResult`가 `image_path`→공개 URL을 만들어 `image_url`에 넣고 경로는 버린다(web `resolveCardImage` 미러). 경로 없으면 `image_count`도 0. `imageUrlBuilder` 주입 이음매로 단위테스트 가능
- `app/lib/features/listings/listing_photo_widgets.dart` (신규) — `PhotoPlaceholder`·`PhotoCountBadge` 공유 위젯. **2차:** `Positioned`를 호출부로 옮겨 Stack 전용 함정 제거
- `app/lib/features/listings/listing_card.dart` — 5:3 사진 셀+"N장" 배지 삽입, 옛 하드코딩 색 토큰화. **2차:** `cacheWidth` 디코드 상한, 로드 실패 로그, 배지 `Positioned` 호출부 이동
- `app/lib/features/listings/listing_detail_screen.dart` — `ListingGallery`(스와이프+"k/N") 삽입, DW-730 대상 6곳 토큰화. **2차:** 카드와 동일한 `cacheWidth`·로드 실패 로그·`Positioned` 이동
- `app/test/listing_card_test.dart`, `app/test/listing_gallery_test.dart`, `app/test/app_theme_color_drift_test.dart`, `app/test/listings_repository_image_order_test.dart` (전부 1차 신규) — I/O 매트릭스·DW-729·대표사진/갤러리 정렬 커버리지. **2차:** 드리프트 완전성 검사를 `app_theme.dart` 실파싱으로 교체(+타입 명시 선언도 잡도록 정규식 정정), 정렬 테스트가 재구현 대신 실제 함수 호출, 1초 실시간 sleep 제거, 5:3·cover·배지 위치·불투명 단언 추가
- `app/test/ai_search_test.dart` (2차) — `image_path`→`image_url` 매핑 4건(web `aiSearch.test.ts` 미러). 경로 없는데 `image_count`만 있는 모순 케이스를 명시 단언
- `app/test/app_router_test.dart` — 카드가 커져 뷰포트 밖으로 밀린 기존 테스트에 `ensureVisible` 1줄 추가(회귀 아님, 스펙 변경의 기계적 결과)
- `app/test/listing_images_bucket_test.dart` (3차 신규) — 버킷명 상수를 마이그레이션 `0014` 정본과 대조(주석을 검사로, B9)
- `app/test/listing_detail_screen_test.dart` (3차 신규) — 상세 화면이 갤러리를 **실제로 그리는지** 배선 검증(위젯 단독 pump가 아니라 화면을 통해)
- `docs/conventions.md` (3차) — §6 FR11 이미지 축 소비처 목록에 앱의 새 `listing_images` 조회 경로 2건 등록(§6이 스스로 요구하는 규칙7 의무, 강제 장치 부재도 함께 명시)
- `_bmad-output/implementation-artifacts/deferred-work.md` — 1차: DW-729 `status: done`+`resolution:`, DW-730 `progress:`(부분 해소)로 갱신 + defer 1건(epics 문서 "서명" 미정정). **2차:** defer 1건(목록 페이지네이션 부재 + `.inFilter()` 청크) 신규 등재 — 기존 항목은 수정하지 않았다

**리뷰 결과:**
- **1차 패스** (4개 레이어: adversarial·edge-case-hunter·verification-gap·intent-alignment, 병렬): patch 9건(medium 3, low 6) · defer 1건 · reject 4건 · intent_gap·bad_spec 0건
- **2차 패스(후속 리뷰, 같은 4개 레이어 재실행):** patch 12건(high 1, medium 4, low 7) · defer 1건(low) · reject 6건 · intent_gap·bad_spec 0건. 최대 발견은 **AI 검색 결과 카드가 사진 없이 "N장" 배지만 뜨는 신규 결함**(4개 레이어 중 4개 모두가 독립적으로 지적) — 1차 패스가 놓친 소비처다
- **3차 패스(후속 리뷰, 같은 4개 레이어 재실행):** patch 16건(medium 4, low 12) · defer 4건(low) · reject 6건 · intent_gap·bad_spec 0건. 이번 패스의 성격은 앞 두 패스와 다르다 — **새 기능 결함이 아니라 "검사가 검사하지 않고 있던 자리"가 주제**였고, 세 렌즈가 그것을 각자 실측으로 증명했다. 리뷰어들이 코드를 일부러 망가뜨려 보니 **사진 부착 로직 전체·상세 화면 갤러리 배선·버킷명 상수**를 통째로 지워도 스위트가 172/172 green이었다. 즉 2차까지 "테스트 10건 추가"로 늘어난 커버리지가 실제로는 순수 함수 주변에만 있었고, 기능이 사라지는 변경은 아무것도 잡지 못했다. 색 드리프트 검사도 2차가 한 축만 넓힌 탓에 다른 표기의 새 토큰에 여전히 열려 있었다(DW-729가 done으로 닫혀 있는 상태에서)

**후속 리뷰 권장:** true — 3차 패스 patch 16건의 점수가 `3×4 + 1×12 = 24` ≥ 5라 규칙상 true. high는 0건이고(2차의 high 같은 기능 결함은 이번에 없었다) 발견의 대부분이 **검증 층**이었다는 점, 그리고 이번 패스가 그 검증 층을 실측으로 닫았다는 점은 함께 기록해 둔다.

**검증(오케스트레이터가 직접 재실행해 확인, 구현·리뷰 에이전트 보고에 의존하지 않음):**
- `flutter analyze` → 0 issues
- `flutter test` → **182 passed**, 0 failed (2차 172 → 3차 신규 10건: 부착 로직 7 + 버킷명 1 + 상세화면 배선 1 + 갤러리 재pump 1, 여기에 폐기 1건·알파 단언 1건 증감 반영)
- `flutter build web --dart-define-from-file=.env.json` → 빌드 성공(`app/build/web/`)
- **3차: 새로 넣은 검사가 실제로 잡는지 형태를 바꿔가며 직접 red/green 확인**(서브에이전트 보고를 신뢰하지 않고 재실행) — ① 사진 부착 배선을 4가지로 훼손(URL 제거·장수 제거·갤러리 정렬 제거·covers 조회 무시) → 전부 red, 원복 green ② 색 토큰을 6가지 표기로 주입(`Color(`·타입명시·`fromARGB`·`fromRGBO`·토큰 별칭·`Colors` 별칭) → 전부 red ③ **web 쪽** `globals.css`의 `--danger` 한 글자 훼손 → red ④ 알파만 변경(`0xFF`→`0x80`) → red ⑤ 버킷명 훼손 → red ⑥ 상세 화면의 갤러리 배선 제거 → red. 전 항목 원복 후 green 재확인
  - ⚠️ 이 재실행에서 **서브에이전트가 시험하지 않은 표기(별칭 선언)에서도 red인지**를 별도로 확인했다 — 2차에서 "구현이 자기가 쓴 표기에서만 red를 증명했다"는 같은 실수가 3차 리뷰 패치에도 재발할 수 있었던 자리다
- **DW-729 드리프트 검사 red/green을 4가지 방식으로 재증명** — ① `AppColors`에 타입 명시 토큰(`static const Color ...`) 주입 → red ② 타입 추론 토큰(`static const ... = Color(...)`) 주입 → red ③ **web 쪽** `globals.css`의 `--brand-petrol` hex 1글자 훼손 → red ④ 전부 원복 → green. ③은 AC가 "앱·웹 **어느 한쪽**"을 요구했는데 1차 패스가 앱 쪽만 깨봤던 자리다. ①은 이번에 새로 발견한 구멍으로, 구현이 처음 쓴 파서가 자기가 시험한 표기 형태만 잡고 있었다
- **스펙 Block If(RLS 실측)를 처음으로 실제 실행** — 1·2차 모두 그전까진 "정책이 존재함"만 확인했다(B4: 존재 확인 ≠ 작동 확인). 로컬 Supabase에 anon 키로 `listing_images`를 직접 조회해 **행이 실제로 반환됨**을 확인 → RLS 거부 없음, Block If 미발동. 이어서 공개 URL을 **인증 헤더 없이** GET해 `200 image/webp 161KB`, 없는 경로는 `400`(→ `errorBuilder` 폴백 경로가 실재함)까지 확인해 조회→URL→렌더 사슬을 끝까지 실측
- 저장 원본 실측: **1600×992 · 161KB · `cache-control: no-cache`** — `cacheWidth` 패치가 추측이 아니라 측정에 근거함을 확인(디코드 약 6.3MB/장)

**잔여 위험:**
- 실기기 시각·터치 확인(사진 비율·배지 위치·스와이프 제스처감)은 스펙이 처음부터 Epic 16-6(SM-D 통합 시연 검증)으로 이관 — 위젯테스트가 5:3·cover·배지 위치·불투명까지 단언하게 됐지만, 실제 화면 밀도와 제스처감은 여전히 미확인이다.
- **저장소의 Supabase 쿼리 문자열 자체는 여전히 어떤 테스트도 실행하지 않는다.** 3차 패치로 사진 부착·URL 조립·버킷명까지는 자동 검사가 생겼지만(`attachCoverImages`/`buildGalleryUrls`/`listing_images_bucket_test`), `.from('listing_images').select(...).inFilter/.eq/.order` 체이닝이 실제로 그렇게 만들어지는지는 여전히 코드 읽기와 수동 실측(anon 조회 + 공개 URL GET)으로만 확인됐다. 특히 `.order('id')`(2차 정렬키)를 지워도 red가 나지 않는다 — 클라이언트측 재정렬이 결과를 덮기 때문이다. 가짜 Supabase 클라이언트를 주입하는 통합 테스트가 남은 자리다.
- **`fetchOwnListing`(판매자 수정 경로)은 여전히 `imageUrls`를 빈 채로 둔다** — 주석으로만 표시돼 있고(B9 관점의 알려진 절충), 그 화면에 사진 섹션이 생기는 스토리가 이 자리를 지나가야 닫힌다.
- 3차에서 등재한 defer 4건(응답 행 수 상한 `max_rows`·홈 화면 전량 조회·사진 전송 비용·DW-730 트리거 키)은 **전부 열린 채로 남는다** — 앞의 셋은 매물 수가 늘어야 드러나고, 마지막은 오케스트레이터만 고칠 수 있다.
- DW-730 잔여는 **23곳**(이 스토리가 안 만진 chat/auth/sell/main.dart 등)이고, 장부의 **25**는 거기에 이 스토리가 새로 만든 의도적 고정 상수 2곳(`listing_photo_widgets.dart`의 불투명 배지 `Colors.black`/`Colors.white`)을 더한 grep 실측치다 — 두 숫자는 세는 대상이 다르다. 장부(25)가 정본이다.
- `epics-increment-2026-07-12.md`의 16.2 AC 원문이 낡은 "서명" 표현을 그대로 갖고 있다 — 정정 근거는 스펙 Design Notes에만 있고 원본 계획 문서는 안 고쳤다(1차 defer 항목).
- `Image.network`에 로딩 중 상태(loadingBuilder) 처리가 없어 로드 중 찰나에 빈 프레임이 보일 수 있다 — AC 요구사항이 아니고, `AspectRatio`가 자리를 미리 잡아 레이아웃이 밀리지 않으므로 patch로 올리지 않았다(reject; 1차 패스의 기각 근거가 web 원본을 잘못 인용했던 것을 2차에서 정정).
