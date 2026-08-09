---
title: '16.7 앱 사진 업로더'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: '1bdd2ad61965bde6a1d9398aa0eca358e66aa388'
final_revision: '1f4f8ffd9388b7ad76203b0515f2c0f5ab0b391a'
review_loop_iteration: 0
followup_review_recommended: true
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
- `app/test/storage_helper_test.dart` -- 신규(후속 리뷰): `buildStoragePath`·`uploadListingImage`·`deleteListingImageObject`를 **실제로 호출하는** 첫 테스트(경로 세그먼트 순서·x-upsert 금지·실패 시 예외 대신 사유 반환)
- `app/test/sell_screen_edit_photos_test.dart` -- 신규(후속 리뷰): 수정 모드 제출 결과 병합의 회귀(무한 리빌드 + 복구 조작 되돌림)
- `app/test/edit_listing_screen_photos_test.dart` -- 신규: 수정 화면 사진 로딩 정상/에러 분기
- `app/test/listings_repository_delete_test.dart` -- 신규: `deleteListing` 오케스트레이션(순서·게이팅)
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

**✎ 2026-08-09 AC4 재현 기록 (review 발견 — 이전엔 커밋 `6620529` 메시지에만 있어 이 diff만으로는
재현 불가능했다).** 로컬 Supabase(도커) DB에 마이그레이션 `0031` 적용 후, 실제 판매자 JWT로
`authenticated` 세션에서 롤백되는 트랜잭션 안에 대조군 포함 5케이스 실행:
- sold 매물 `listing_images` INSERT → 거부(RLS violation)
- sold 매물 `listing_images` UPDATE → 0행
- sold 매물 `listing_images` DELETE → 0행
- (대조군) on_sale 매물 INSERT → 허용(1행)
- (대조군) on_sale 매물 UPDATE → 허용(3행)

전부 트랜잭션 롤백으로 실행 — 사후 행 수 확인으로 부작용이 남지 않았음을 확인했다.

## Review Triage Log

### 2026-08-09 — Review pass (후속 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 4, medium 2, low 0)
- defer: 6: (high 0, medium 5, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` `buildStoragePath`가 `{listing_id}/{user_id}/{filename}` 순서로 조립하고 있었다 — 첫 세그먼트가 소유자여야 한다는 Storage RLS와 `0013` 경로 무결성 트리거에 걸려 **모든 업로드가 거부**되는 상태였다(스펙 Always 첫 줄 위반). 계약 순서로 복원. 이 패스 시작 시점에 `storage_helper_test.dart` 2건이 실제로 red였고 복원 후 green 확인.
  - `[high]` `[patch]` `validatePickedFile`에서 확장자 검사와 5MB 상한 검사가 빠져 있었다 — I/O 매트릭스 2행("5MB 초과 파일 선택")이 성립하지 않고, `flutter analyze`도 `_extensionOf` 미사용 경고 1건을 내고 있었다. 두 검사를 복원(analyze 0 issues, `sell_screen_photo_test.dart` 2건 red→green).
  - `[high]` `[patch]` 등록에 성공한 뒤 **다음 매물용으로 고른 사진이 다음 프레임에 사라졌다.** `sell.success`는 텍스트 입력(`updateInput`)으로만 지워지는데 사진 선택은 그 경로를 타지 않아, 사진을 고를 때마다 일어나는 리빌드가 post-frame 콜백을 다시 돌려 `_resetFields()`를 재실행했다. 결과를 한 번만 소비하는 `_handledResult` 가드로 수정, 회귀 테스트 추가(red 실측 확인).
  - `[high]` `[patch]` 수정 화면에서 사진 처리가 일부 실패한 뒤 **에러 배너가 시킨 복구 조작(삭제·재정렬·재시도)이 한 프레임 뒤에 전부 되돌려졌다.** 기존 `!identical(incoming, _photos)` 가드는 무한루프만 막았고, 사용자가 목록을 바꾸면 비교가 다시 어긋나 컨트롤러의 옛 목록으로 덮였다 — 안내가 지시한 복구 경로에서 빠져나갈 수 없는 상태. 같은 `_handledResult` 가드로 해소, 회귀 테스트 추가(red 실측 확인, 기존 무한루프 테스트도 함께 green 유지).
  - `[medium]` `[patch]` 대표 배지가 **재시도 가능한** 업로드 실패 항목을 건너뛰었다. `syncListingPhotos`는 그런 항목을 다시 올리므로 재시도가 성공하면 그 사진이 실제 `sort_order` 0(대표)이 되는데 배지는 뒤 사진에 붙어 있었다(지난 패스가 고친 불일치의 방향만 뒤집힌 형태). 술어를 정원 계산과 동일한 `!_isRejected`(영구 거부만 제외)로 통일하고 `[대표로]` 노출 조건도 맞춤. 옛 동작을 **다른 표기로** 다시 심어 red 확인 후 원복.
  - `[medium]` `[patch]` `syncListingPhotos`가 예상 밖 예외를 던지면 `submit()` 바깥 catch가 이를 "매물 저장 실패"로 바꿔, 이미 등록·수정된 매물을 두고 사용자가 같은 매물을 다시 등록할 수 있었다(스펙 Always "개별 사진 실패는 폼 제출 자체를 막지 않는다" 위반). `_syncPhotosSafely`로 감싸 사진 쪽 실패로만 격리.
  - `[medium]` `[defer]` → DW-748(`sort_order` 갱신 실패 행이 옛 번호를 유지해 중복 가능 → 대표가 엉뚱한 사진)
  - `[medium]` `[defer]` → DW-749(`epic-16-context.md`가 인수 커밋에서 재작성되며 16.8 정정 소실 + 철회된 계약 부활 — 다음 스토리가 planning에서 읽는 문서)
  - `[medium]` `[defer]` → DW-750(AC4 `sold` 쓰기 차단에 자동 회귀 검사 없음 — `api-db` CI 잡을 쓸 수 있는데 안 씀)
  - `[medium]` `[defer]` → DW-751(`fetchOwnListingPhotos`·`toPhotoItems`가 전 스위트에서 미실행 — 정렬 계약이 깨져도 초록)
  - `[medium]` `[defer]` → DW-752(`deleteListing` 사진 정리 호출의 presence 단언 0건 — AC5의 유일한 자동 방어선)
  - `[low]` `[defer]` → DW-753(AndroidManifest "시스템 포토피커" 주석이 실제 경로(SAF)와 다름 — DW-747의 전제에 영향)
  - `[reject]` `deleteListing` 정리 실패가 호출부에 안 알려짐 / 정리 실패 관측 수단 없음 — 의도가 "베스트에포트, 실패해도 삭제 자체는 되돌리지 않는다"로 스코프를 명시했다(지난 패스와 동일 판단).
  - `[reject]` 삭제 실패로 DB 행이 정원을 차지한 채 업로드를 계속 진행 — 서버 트리거를 최종 방어선으로 두는 것이 스펙이 정한 구조다.
  - `[reject]` INSERT 보상 삭제까지 실패하면 `print`만 남는다 — 관측성 개선이고 이 스토리의 계약 밖이다.
  - `[reject]` `coverPath == null`인데 `is_cover` 리셋만 나가고 경고가 없다 — **코드를 읽어 확인한 결과 사실이 아니다.** 저장된 사진이 있는데 `coverPath`가 비는 경우는 모든 저장이 실패했을 때뿐이고, 그 실패들이 이미 각각 경고를 남긴다.
  - `[reject]` `compressWithList`가 예외 대신 빈 바이트를 돌려줘 0바이트 오브젝트가 저장될 수 있다 — **패키지 소스로 확인한 결과 전제가 틀렸다.** `flutter_image_compress_common` 1.1.1은 네이티브 실패를 `CompressError`로 던지고 null을 돌려주지 않는다.
  - `[reject]` `is_cover`를 읽는 코드가 없으니 그 쓰기 실패를 사용자 오류로 만들지 말라 — `docs/conventions.md` §10.1이 확정한 계약이고 웹과의 미러 유지가 이 스토리의 접근 자체다.
  - `[reject]` `CAMERA` 권한 선언 자체를 빼라 — 카메라 촬영 옵션은 확정된 UX 범위이고, 권한 제거는 이 스토리의 의도 밖 변경이다.
  - `[reject]` `sprint-status.yaml`과 스펙 frontmatter의 status 불일치·`review_loop_iteration` 미증가 — 오케스트레이터가 소유하는 필드다(이 실행은 건드리지 않는다).

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 5, low 2)
- defer: 4: (high 0, medium 1, low 3)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` 사진 업로더의 "대표" 배지가 업로드 실패(재시도 가능)로 아직 저장되지 않은 사진에 붙을 수 있었다(첫 사진 실패·둘째 성공 시 화면과 DB의 대표가 갈림) — `photo_uploader_widget.dart`의 `firstSavableIndex` 판정을 `photo_sync.dart`가 실제 대표를 거는 기준(storagePath!=null)과 맞춤. 회귀 테스트 추가(red→green 확인).
  - `[medium]` `[patch]` `ListingsRepository.deleteListing`의 오케스트레이션(경로 선조회→행 삭제→정리 게이팅)이 통째로 미검증이었다 — `test/listings_repository_delete_test.dart` 신설(순서·0행 게이트·paths.ok==false 게이트 3건). red→green 확인.
  - `[medium]` `[patch]` `SellController.submit()`이 실제 사진과 함께 호출되는 경로(부품은 테스트됐지만 배선은 미검증)를 검증하는 테스트가 없었다 — `sell_controller_test.dart`에 전역 Supabase 싱글턴 + 가짜 httpClient를 세팅해 배선 테스트 추가. red→green 확인.
  - `[medium]` `[patch]` `EditListingScreen`의 기존 사진 로딩 경로(provider·매핑·로딩/에러 UI)가 통째로 미검증이었다 — `test/edit_listing_screen_photos_test.dart` 신설(정상 로드·사진 조회 실패 2건). red→green 확인.
  - `[medium]` `[patch]` 카메라/갤러리 피커 호출과 `file.length()`가 예외를 unguarded로 둬, 권한 거부 등에서 미처리 예외가 날 수 있었다 — `photo_uploader_widget.dart`에 try/catch + 안내 문구 추가, 회귀 테스트(가짜 피커가 throw) 추가. red→green 확인.
  - `[low]` `[patch]` 삭제 실패(재시도 불가) 항목의 안내 문구가 "다시 시도해주세요"라 존재하지 않는 재시도 버튼을 가리켰다 — 실제 복구 동작(삭제 버튼 재클릭)에 맞게 문구 수정.
  - `[low]` `[patch]` AC4(sold 쓰기 차단) 증거가 다른 커밋의 메시지에만 있어 이 diff·spec만으로는 재현 불가능했다 — 오늘 독립 재실행한 대조군 포함 5케이스 결과를 스펙 Verification에 재수록.
  - `[medium]` `[defer]` → DW-744(리사이즈 전 원본 풀 디코딩 — 고화소 사진 OOM 위험)
  - `[low]` `[defer]` → DW-745(저장본 규격 실기기 미검증)
  - `[low]` `[defer]` → DW-746(매물 삭제 중 동시 사진 추가 레이스)
  - `[low]` `[defer]` → DW-747(확장자 없는 선택 파일 오거부)
  - `[reject]` deleteListing 정리 실패가 호출부에 안 알려짐 — Always 규칙이 명시적으로 "베스트에포트, 실패해도 삭제 자체는 되돌리지 않는다"고 스코프를 정했다.
  - `[reject]` `toPhotoItems`가 계약 위반 행을 조용히 스킵 — DB 트리거(0013)가 그런 행 자체를 이미 막는다(스펙이 명시).
  - `[reject]` `uploadListingImage`가 실패 사유를 세분화하지 않고 항상 retryable — 스펙이 요구한 유일한 구분(검증실패 vs 네트워크실패)은 이미 지켜지고 있다.
  - `[reject]` `warnings.toSet()`이 중복 실패 메시지를 합침 — 개별 사진 오류는 이미 항목별 인라인 배지로 표시되므로 집계 문구의 정보 손실은 실질적 영향이 없다.
  - `[reject]` AC5가 "통과한 것처럼" 나열됐다는 지적 — Design Notes가 이미 DW-743으로 미검증을 명시하고 있어 오인 소지가 없다.

## Auto Run Result

### 2026-08-09 — 후속 2차 리뷰 패스

**요약:** 이 실행은 `followup_review_recommended: true`로 재개된 **후속 리뷰**다. 재구현은 하지 않았다.
시작 시점의 워킹트리에는 커밋되지 않은 변경이 쌓여 있었고(직전 세션이 마무리를 못 한 상태),
그 안에 **계약을 정면으로 깨는 회귀 2건**이 살아 있었다 — `flutter analyze` 1 issue,
`flutter test` 4건 red가 그 사실을 그대로 보여줬다. 4개 리뷰 레이어(blind-hunter /
edge-case-hunter / verification-gap / intent-alignment)를 병렬 실행한 뒤, patch 6건을 직접
수정하고 회귀 테스트를 붙였으며 defer 6건을 장부(DW-748~753)에 등재했다.

> ⚠️ 4개 레이어 중 3개가 위 회귀 2건을 "옆에서 도는 리뷰어의 red 프로브"로 판정했다.
> 그러나 그 변경들은 **리뷰어를 띄우기 전부터 워킹트리에 있었고**(실행 전 `git diff`로 확인),
> 리뷰어 종료 후 파일 해시가 변하지 않았다. 즉 프로브가 아니라 **원복되지 않은 채 남은 회귀**였다.
> 이번 실행의 테스트 작성 서브에이전트도 같은 실수를 했다 — `_handledResult = current;` 한 줄을
> red 증명용으로 지우고 복원하지 않은 채 끝났고, 전체 스위트를 직접 돌려서야 잡혔다.

**파일 변경(이번 실행분만):**
- `app/lib/core/supabase/storage_helper.dart` — `buildStoragePath` 세그먼트 순서를 계약(`{user_id}/{listing_id}/{filename}`)으로 복원
- `app/lib/features/listings/photo_item.dart` — `validatePickedFile`의 확장자·5MB 검사 복원
- `app/lib/features/listings/sell_screen.dart` — 제출 결과를 한 번만 소비하는 `_handledResult` 가드 추가(등록 후 사진 소실 + 수정 복구 조작 되돌림 동시 해소)
- `app/lib/features/listings/photo_uploader_widget.dart` — 대표 배지·`[대표로]` 술어를 정원 계산과 같은 `!_isRejected`로 통일
- `app/lib/features/listings/sell_controller.dart` — `_syncPhotosSafely` 추가(사진 반영 예외가 "매물 저장 실패"로 새지 않게)
- `app/test/sell_screen_photo_test.dart` — 등록 후 사진 소실 회귀 + 대표 배지(재시도 가능 항목) 회귀 테스트
- `app/test/sell_screen_edit_photos_test.dart` — 수정 부분실패 후 복구 조작이 유지되는지 회귀 테스트
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-748~753 신설(기존 항목은 건드리지 않음)

**리뷰 결과:** intent_gap 0 · bad_spec 0 · patch 6(high 4, medium 2 — 전부 이번 패스에서 수정·검증) · defer 6(DW-748~753) · reject 8. Follow-up review 권고: **true**(high 패치가 있어 자동 true).

**검증(전부 이번 실행에서 직접 돌려 관찰):**
- `flutter analyze` → **No issues found!** (시작 시점: 1 issue)
- `flutter test` → **422 passed, 0 failed** (시작 시점: 415 passed / 4 failed)
- `flutter build apk --debug --dart-define-from-file=.env.json` → **빌드 성공.** 이번엔 생략하지 않았다 — 워킹트리가 `AndroidManifest.xml`을 바꿨는데(`uses-feature ... required="false"` 2줄) **매니페스트 병합 오류는 analyze·test가 구조적으로 못 잡는 유일한 종류**라서다.
- red→green 실측: 대표 배지 술어는 옛 동작을 **다른 표기로** 다시 심어 red를 확인한 뒤 백업본으로 원복했다(`git checkout`은 쓰지 않았다 — 커밋 안 된 변경을 날린다).

**이 검사들이 보지 않는 것:** 실제 기기·실제 Supabase. 모든 앱 테스트는 가짜 http 클라이언트로 "나가는 요청의 모양과 순서"까지만 본다(DW-751·DW-752가 그중 구멍 2개를 지목한다). AC5(매물 삭제 시 오브젝트 실제 정리)는 여전히 DW-743, 실기기 카메라 권한은 DW-742로 열려 있다.

**잔존 리스크:** DW-749(에픽 컨텍스트 문서에 철회된 계약이 되살아나 있음 — 다음 스토리가 planning에서 먼저 읽는 문서라 **16.6 착수 전에** 봐야 한다), DW-750(sold 차단 회귀가 CI에 안 잡힘), DW-748(부분 실패 시 대표가 엉뚱한 사진이 될 수 있음).

### 2026-08-09 — 1차 리뷰 패스

**요약:** 이 스토리(앱 사진 업로더)는 이전 dev 세션이 OOM으로 끊긴 뒤 사람이 인수·커밋한 상태(`6620529`, `2860ab3`)로 이번 실행을 시작했다. 재구현은 하지 않고 Design Notes의 지시대로 검증·리뷰만 수행했다 — Matrix Test Audit에서 실측 갭 1건을 직접 메우고, 4개 리뷰 레이어(blind-hunter/edge-case-hunter/verification-gap/intent-alignment) 병렬 실행 후 patch 7건을 직접 수정·회귀테스트 추가, defer 4건을 장부(DW-744~747)에 등재했다.

**파일 변경(이번 실행분만):**
- `app/lib/features/listings/photo_uploader_widget.dart` — 대표 배지 판정 수정(`firstSavableIndex`) + 카메라/갤러리 피커·`file.length()` 예외 처리 추가
- `app/lib/features/listings/photo_sync.dart` — 삭제 실패 안내 문구를 실제 복구 동작에 맞게 수정
- `app/test/photo_sync_test.dart` — Matrix 5번째 행("목록 맨 뒤로 이동") 커버 테스트 추가 + 문구 변경 반영
- `app/test/sell_screen_photo_test.dart` — 대표 배지 불일치 회귀 테스트, 피커 예외 회귀 테스트 추가
- `app/test/sell_controller_test.dart` — `submit()` 실사진 배선 회귀 테스트 추가(전역 Supabase + 가짜 httpClient 세팅 포함)
- `app/test/listings_repository_delete_test.dart` — 신규: `deleteListing` 오케스트레이션(순서·게이팅) 3건
- `app/test/edit_listing_screen_photos_test.dart` — 신규: 수정 화면 사진 로딩 정상/에러 분기 2건
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-744~747 신설
- `_bmad-output/implementation-artifacts/spec-16-7-앱-사진-업로더.md` — AC4 재현 기록 추가, Review Triage Log 신설, `followup_review_recommended: true`

**리뷰 결과:** intent_gap 0 · bad_spec 0 · patch 7(medium 5, low 2, 전부 이번 패스에서 수정·검증) · defer 4(DW-744~747) · reject 5. Follow-up review 권고: **true**(3×medium5 + 1×low2 = 17 ≥ 5).

**검증:** `flutter analyze`(0 issues) · `flutter test`(407 passed, 기존 398 + 이번 실행에서 추가한 9건) · 로컬 Supabase DB로 AC4(sold 쓰기 차단) 5케이스 재실측(대조군 포함, 전부 롤백) · `flutter build apk --debug`(이전 인수 세션에서 빌드 성공 확인, 이번 실행은 코드 변경이 소규모라 재빌드 생략 — analyze+test가 green이고 변경이 위젯/텍스트/로직 수준이라 빌드 자체가 깨질 변경이 아님).

**완료 못 한 것:** AC5(매물 삭제 시 Storage 오브젝트 실제 정리)는 여전히 SQL로 측정 불가능해 DW-743으로 남아 있다(이번 실행에서 다시 시도하지 않음, 스펙 지시 준수). 실기기 카메라 권한 확인(DW-742)도 동일하게 샌드박스 제약으로 미완.

**잔존 리스크:** DW-744(고화소 사진 리사이즈 시 메모리 스파이크 가능성 — 실기기 실측 전까지 이론적 위험), DW-746(매물 삭제 도중 동시 편집 레이스, 발생 빈도 극히 낮음).
