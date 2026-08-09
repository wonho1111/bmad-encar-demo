---
title: '16.7 앱 사진 업로더'
type: 'feature'
created: '2026-08-09'
status: 'in-progress'
baseline_revision: '1bdd2ad61965bde6a1d9398aa0eca358e66aa388'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Flutter 앱 등록/수정 폼에 사진 업로드 UI가 전혀 없다(`sell_screen.dart` 주석 "사진 없음"). 웹 Story 9.3이 이미 확정한 사진 저장 계약을 앱이 미러링하지 않으면 앱 판매자는 사진을 영영 못 올린다(DW-352). 또한 `listing_images` 쓰기 정책 3개(insert/update/delete)에 `sold` 차단이 없어(DW-390) 앱이 이 구멍을 그대로 물려받는다.

**Approach:** `docs/conventions.md` §10/§10.1(정본 — 9.3 스토리 문서 자체가 "지금 계약은 여기"라고 명시)을 그대로 이식한다: OS 네이티브 피커로 고른 사진을 폼 제출 시점에 순차 업로드하고, 신규 `listing_images` 쓰기 정책 마이그레이션으로 `sold` 매물 쓰기를 DB에서 막는다.

## Boundaries & Constraints

**Always:**
- 저장 경로 `{user_id}/{listing_id}/{filename}`, 파일명은 **uuid**(결정론적 파일명 아님 — 업서트 금지, 재시도는 새 uuid로 재시도). 이 규칙은 이미 DB 트리거(`0013`)가 강제하므로 앱이 재검증할 필요는 없다.
- 업로드 전 클라이언트에서 긴 변 ≤1600px·WebP q0.82로 재인코딩(WebP 실패 시 JPEG q0.85 폴백). 원본 5MB 상한과 별개.
- 대표(cover) = `sort_order` 0(파생값). 대표 교체는 반드시 두 문장(① 매물 전체 `is_cover=false` → ② 대상 1장 `true`) — 단일 UPDATE는 부분 유니크 인덱스 위반으로 죽는다.
- 사진 1장 삭제 = ① Storage 오브젝트 → ② `listing_images` 행 순서(①실패 시 ②안함). 매물 전체 삭제 = ① `listings` 행 → ② 사진 오브젝트 정리(베스트에포트, 실패해도 삭제 자체는 되돌리지 않음).
- 업로드 대상이 새로 고른 파일뿐인 기존 저장 행은 `sort_order`만 갱신한다. `sort_order`는 실제 저장 성공 개수 기준 연속 정수로 재매김(화면 인덱스 아님).
- 사진 선택·삭제·순서변경은 화면 로컬 상태일 뿐이며 실제 업로드/삭제/DB 반영은 폼 제출 시점에 한 번에(등록·수정 동일 경로). 등록은 `listings` INSERT로 `listing_id`를 먼저 얻은 뒤 업로드한다.
- 개별 사진 업로드/삭제 실패는 폼 제출 자체를 막지 않는다 — 인라인 오류 + 재시도(용량초과·포맷거부는 재시도 불가, 네트워크 실패는 재시도 가능).
- `listing_images` insert/update/delete 3정책 모두에 `and l.status <> 'sold'`를 추가해 DB가 강제한다(DW-390 해소, CLAUDE.md B9 — 화면 방어로 대체하지 않는다).
- 매물 삭제(`ListingsRepository.deleteListing`) 시 사진 오브젝트도 정리한다(행 삭제 **전에** 경로를 조회해 두고, 행 삭제 후 정리 — cascade가 행을 먼저 지우면 어떤 파일을 지울지 알 방법이 없어진다).

**Block If:** 다음 마이그레이션 번호(0031)가 이미 다른 작업으로 선점돼 원격 마이그레이션 이력과 로컬 번호가 어긋나면(동시 작업 충돌) — 번호를 임의로 밀어넣지 않는다.

**Never:** 이미지 편집(크롭·회전) · 동영상 업로드 · 웹 업로더 UI 이월(드롭존 없음, 네이티브 피커만) · `listing_images` 10장/5MB/MIME 서버 상한 로직 변경(이미 확정, 앱은 클라 1차 방어만 추가).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 신규 등록 + 사진 3장 | 갤러리에서 3장 선택 후 등록 | listing INSERT → 3장 순차 업로드 → 0번=대표 | 없음 |
| 5MB 초과 파일 선택 | 6MB 이미지 선택 | 목록에 인라인 오류로 표시, 정원(N/10)에서 제외, 재시도 버튼 없음 | 다른 파일 선택만 가능 |
| 10장 초과 선택 | 이미 8장 있는데 5장 추가 선택 | 앞 2장만 받고 "3장은 제외했어요" 안내 | 서버 트리거가 최종 방어 |
| 업로드 중 네트워크 실패 | 리사이즈 성공, Storage 업로드 실패 | 그 항목만 인라인 오류(재시도 가능)로 표시, 폼 제출은 성공 처리 | 재시도 탭 시 다음 제출에서 재업로드 |
| 사진 삭제 시 Storage 삭제 실패 | 기존 사진 제거 시도, 오브젝트 삭제 실패 | 해당 항목은 목록 맨 뒤로 이동, error 표시, `listing_images` 행은 유지 | DB 행을 지우지 않아 고아 방지 |
| sold 매물에 쓰기 시도 | sold 매물의 `listing_id`로 직접 insert/update/delete 시도(방어 우회 가정) | DB 정책이 0행/거부로 막는다 | 화면은 애초에 sold 매물 수정 진입점이 없음(my_listings_screen) |

</intent-contract>

## Code Map

- `supabase/migrations/0031_listing_images_sold_write_block.sql` -- 신규: `listing_images_insert_own`/`update_own`/`delete_own` 3정책에 `and l.status <> 'sold'` 추가(DW-390)
- `app/pubspec.yaml` -- `image_picker`(갤러리/카메라 피커), `flutter_image_compress`(WebP 리사이즈) 의존성 추가
- `app/android/app/src/main/AndroidManifest.xml` -- `android.permission.CAMERA` 추가(갤러리는 시스템 포토피커라 권한 불필요)
- `app/lib/core/supabase/storage_helper.dart` -- 쓰기측 헬퍼 추가: `buildStoragePath`·`uploadListingImage`·`deleteListingImageObject`(웹 `lib/storage/upload.ts` 미러, upsert 금지)
- `app/lib/features/listings/photo_item.dart` -- 신규: `PhotoItem` 모델 + `MAX_PHOTOS=10`(웹 `photo-item.ts` 미러)
- `app/lib/features/listings/photo_resize.dart` -- 신규: 1600px·WebP q0.82 리사이즈(JPEG q0.85 폴백), `flutter_image_compress` 사용
- `app/lib/features/listings/photo_sync.dart` -- 신규: `syncListingPhotos`(삭제→업로드→행 기록→대표 2문장) + `listListingPhotoPaths`/`deletePhotoObjectsByPaths`(매물 삭제용), 웹 `photo-sync.ts` 미러
- `app/lib/features/listings/photo_uploader_widget.dart` -- 신규: 가로 스크롤 썸네일 목록(재배치 가능) + "+"(카메라/갤러리 바텀시트) + N/10 카운터 + 대표 배지·[대표로]·삭제·인라인 오류/재시도
- `app/lib/features/listings/sell_screen.dart` -- `List<PhotoItem>` 상태 추가, `PhotoUploaderWidget` 배선
- `app/lib/features/listings/sell_controller.dart` -- `submit()`이 listing 저장 성공 후 `syncListingPhotos` 호출, 결과 병합
- `app/lib/features/listings/edit_listing_screen.dart` -- 진입 시 기존 `listing_images` 조회 → `toPhotoItems` 상당으로 초기 목록 구성
- `app/lib/features/listings/listings_repository.dart` -- `createListing`이 `id`를 반환하도록 변경(`.select('id').single()`); `deleteListing`에 사진 정리 배선
- `app/test/photo_sync_test.dart` -- 신규: syncListingPhotos 단위테스트(I/O 매트릭스)
- `app/test/photo_resize_test.dart` -- 신규: 리사이즈 규격 단위테스트
- `app/test/sell_screen_photo_test.dart` -- 신규: 업로더 위젯테스트(추가/삭제/재배치/정원/오류표시)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-352/DW-390 상태를 `done 2026-08-09`로 갱신

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0031_listing_images_sold_write_block.sql` -- insert/update/delete 정책에 sold 차단 추가 -- DW-390 해소, DB 레벨 강제(B9)
- `app/pubspec.yaml`, `app/android/.../AndroidManifest.xml` -- 신규 의존성·카메라 권한 -- 네이티브 피커 전제조건
- `app/lib/core/supabase/storage_helper.dart` -- 경로 조립/업로드/삭제 헬퍼 -- 웹과 동일 계약 이식
- `app/lib/features/listings/photo_item.dart`, `photo_resize.dart`, `photo_sync.dart` -- 순수 모델·리사이즈·동기화 로직 -- 웹 3.9 계약 미러(단위테스트 대상)
- `app/lib/features/listings/photo_uploader_widget.dart` -- 업로더 UI -- UX-DR13(드롭존+카운터+대표배지+재정렬)
- `app/lib/features/listings/sell_screen.dart`, `sell_controller.dart`, `edit_listing_screen.dart`, `listings_repository.dart` -- 폼·컨트롤러·리포지토리 배선 -- 등록/수정 단일 경로로 사진 반영
- `app/test/*` -- 단위·위젯테스트 -- I/O 매트릭스 커버
- `deferred-work.md` -- DW-352/DW-390 닫기 -- CLAUDE.md B8 장부 닫기

**Acceptance Criteria:**
- Given 등록 폼에서 사진 3장을 고르고 제출, when 그 매물을 다시 열면(수정 화면), then 3장이 고른 순서대로 보이고 첫 번째 사진에 "대표" 배지가 붙어 있다.
- Given 수정 폼에서 기존 사진 1장을 삭제하고 제출, when 그 매물을 다시 열면, then 삭제한 사진은 더 이상 보이지 않고 남은 사진들이 빈 자리 없이 이어서 보인다.
- Given 이미 10장이 등록된 매물의 수정 화면, when 사진을 더 추가하려 하면, then 화면이 추가를 막고 "N/10"으로 꽉 찼음을 보여준다(서버 트리거는 별개 방어선으로 유지, 화면 우회를 가정한 값 아님).
- Given 로컬/개발 환경에서 sold 매물의 `listing_id`로 `listing_images` insert/update/delete를 직접 시도하면(화면엔 이 진입점이 없음 — 방어선 확인용), when 요청을 보내면, then RLS가 거부(0행/정책 위반)한다.
- Given 매물을 삭제하면, when Storage 버킷에서 그 매물 경로를 다시 조회하면, then 오브젝트가 더 이상 없다(정리 실패가 매물 삭제 자체를 막지는 않는다).

## Design Notes

**epics 문서 AC 원문("결정론적 파일명으로 재시도가 덮어쓰기")은 낡은 서술이다.** `_bmad-output/implementation-artifacts/9-3-사진-업로더-등록-수정.md`가 자체적으로 "이 설계는 Story 9.0으로 대체됐다. 지금 계약은 `docs/conventions.md` §6.1·§10"이라고 명시한다. 실제 정본(§10.1)은 **uuid 파일명 + upsert 금지**다(존재확인 SELECT가 RLS에 걸려 403이 나는 게 원격 실측으로 확인됨). "재시도가 덮어쓴다"가 아니라 "재시도는 새 uuid라 애초에 충돌이 없다"가 맞는 서술이라 그대로 이식한다.

**웹은 새 의존성 0개(브라우저 canvas)로 리사이즈하지만 Dart엔 그런 내장 인코더가 없다.** `flutter_image_compress`(WebP 지원, Android/iOS)를 신규 의존성으로 들인다 — 이 프로젝트는 Android 전용(ios 폴더 없음)이라 플랫폼 호환은 문제되지 않는다.

**사진 선택은 로컬 상태일 뿐, 실제 업로드는 폼 제출 시점에 한 번에 일어난다**(웹과 동일 이유: 신규 등록은 `listing_id`가 생기기 전엔 올릴 경로가 없다). 재시도 버튼도 별도 업로드를 트리거하지 않고 로컬 상태만 `idle`로 되돌린다 — 실제 재업로드는 다음 제출에서 일어난다.

**✎ 2026-08-09 인수 경위 — 구현은 이미 커밋돼 있다(`6620529`).** 이 스토리의 첫 dev 세션
(run `20260809-013506-d92f`)이 마지막 실측 도중 `systemd-oomd`에 죽었고, 엔진에 세션 기록이
남지 않아 `resume`이 작업을 지우는 경로로 가게 돼 사람이 인수해 커밋했다. 따라서 **Code Map의
파일은 전부 존재하고 `flutter analyze`(0 issues)·`flutter test`(398 passed)가 초록**이다.
아래 Verification을 다시 돌려 확인하되, **처음부터 다시 구현하지 말 것** — 남은 일은 검증과
리뷰다. AC4(sold 쓰기 차단)는 로컬 DB 실측으로 닫혔고(대조군 포함 5케이스, 커밋 메시지에 원문),
AC5(매물 삭제 시 오브젝트 정리)는 SQL로 측정이 불가능해(`storage.protect_delete()` 트리거)
**DW-743**으로 등재했다 — 다시 시도하지 말고 그 항목을 그대로 둔다.

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build apk --debug --dart-define-from-file=.env.json` -- expected: 빌드 성공(Android 전용)

**Manual checks (if no CLI):**
- 로컬 Supabase(도커)에 마이그레이션 적용 후, 시드 판매자 JWT로 sold 매물의 `listing_images`에 직접 insert/delete curl 시도 → 거부(0행/정책 위반) 확인, on_sale 매물은 여전히 허용되는지 대조.
- 실제 안드로이드 기기(또는 에뮬레이터+모의 카메라)에서 카메라/갤러리 권한 요청이 실제로 뜨는지 확인. 불가능하면(샌드박스 제약) `deferred-work.md`에 등재하고 위젯테스트로 대체 확인한 사실을 명시한다.
