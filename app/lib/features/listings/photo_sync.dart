// 매물 사진을 화면 상태 → DB·Storage에 반영한다(AC3·AC5·AC6·AC8·AC9·AC10).
// web `web/src/app/(user)/sell/photo-sync.ts`의 **부분** 미러 — 순서 계약 둘(① 삭제 순서,
// ② 대표 2문장 쓰기)은 아직 그 파일과 공유하지만, sort_order 번호 매김·대표 선정 알고리즘은
// spec-16-11(2026-08-10)에서 이 파일만 근본적으로 바뀌어 갈라졌다([[DW-788]] — web은 아직
// 옛(0부터 연속) 방식이다). 아래 ①②는 여전히 그 파일의 실측(§10.1)에서 나온 것을 그대로
// 이식한 것이다:
//   ① **삭제: Storage 오브젝트 먼저 → listing_images 행 나중.**
//      오브젝트 삭제가 실패하면 행도 지우지 않는다 — 행만 지우면 고아가 만들어진다.
//   ② **대표 기록: 매물 전체 is_cover=false → 대상 1장만 true.**
//      부분 유니크 인덱스(listing_images_one_cover_per_listing)가 DEFERRABLE이 아니라서
//      단일 UPDATE로 뒤집으면 문장 중간에 대표가 2장이 되는 순간 duplicate key로 죽는다(#47-1).
//
// 등록과 수정이 **같은 함수**를 탄다. 등록은 "기존 사진이 0장인 수정"과 정확히 같기 때문이다.
//
// ⚠️ Dart supabase 클라이언트는 web(thenable {data,error})과 달리 **에러를 throw**한다. 이 함수는
// 개별 사진의 실패가 전체 제출을 막으면 안 된다는 계약(AC3)을 지키기 위해, 각 Postgrest 호출을
// 개별 try/catch로 감싸 하나가 실패해도 나머지 처리를 계속한다 — web 테스트가 `error` 필드로
// 표현하던 실패를 여기서는 예외로 표현할 뿐, "계속 진행한다"는 계약은 동일하다.
import 'dart:typed_data';

import 'package:image_picker/image_picker.dart' show XFile;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../../core/supabase/storage_helper.dart' as storage;
import '../../core/supabase/supabase_client.dart';
import 'listing_images_bucket.dart' show listingImagesBucket;
import 'photo_item.dart';
import 'photo_resize.dart';

/// syncListingPhotos 결과.
class PhotoSyncResult {
  const PhotoSyncResult({
    required this.photos,
    required this.savedCount,
    required this.failedCount,
    required this.warnings,
  });

  /// 화면에 되돌려줄 항목들(실패한 것은 status:error로 표시돼 있다 — AC3).
  final List<PhotoItem> photos;

  /// 이번에 새로 저장된 장수.
  final int savedCount;

  /// 실패한 장수(폼 제출 자체는 막지 않는다 — AC3).
  final int failedCount;

  /// 행 삭제·sort_order 갱신·대표 지정처럼 "저장은 됐지만 뒷정리가 어긋난" 조용한 실패의 한국어
  /// 사유. failedCount와 별개다 — 사진 자체는 저장됐으므로 재제출을 막을 이유는 아니지만, 화면과
  /// DB가 갈린 채로 "성공"이라고만 말하면 안 되기 때문에 둔다.
  final List<String> warnings;
}

/// 저장 파일명 — uuid라 충돌이 없다(그래서 upsert가 필요 없다, storage_helper.dart 주석 참조).
String _newFilename(String ext) => '${const Uuid().v4()}.$ext';

typedef ResizeFn = Future<EncodedPhoto> Function(XFile file);
typedef UploadFn =
    Future<storage.UploadResult> Function(
      String userId,
      String listingId,
      String filename,
      Uint8List bytes,
      String contentType,
    );
typedef DeleteObjectFn = Future<bool> Function(String storagePath);

/// 매물의 사진 파일 경로를 **미리** 읽어 둔다.
///
/// ⚠️ **매물 행을 지우기 전에 불러야 한다.** `listing_images`는 `listings`에 on delete cascade로
/// 매달려 있어서, 매물을 먼저 지우면 이 행들이 함께 사라진다 — 그러면 어떤 파일을 지워야 하는지
/// 알 방법이 영영 없어진다.
Future<({bool ok, List<String> paths})> listListingPhotoPaths(
  String listingId, {
  SupabaseClient? client,
}) async {
  final supa = client ?? supabase;
  try {
    final rows = await supa
        .from('listing_images')
        .select('storage_path')
        .eq('listing_id', listingId);
    return (
      ok: true,
      paths: rows
          .map((r) => r['storage_path'])
          .whereType<String>()
          .toList(),
    );
  } catch (e) {
    // 무엇이 있는지 모르는 상태다 — "사진이 없다"로 갈음하지 않는다(그러면 조용히 고아가 된다).
    // ignore: avoid_print
    print('[sell] 매물 사진 목록 조회 실패: $listingId, $e');
    return (ok: false, paths: <String>[]);
  }
}

/// 미리 확보한 경로들로 오브젝트를 지운다. 행이 이미 사라진 뒤에도 동작한다.
Future<({bool ok, int deleted})> deletePhotoObjectsByPaths(
  List<String> paths, {
  DeleteObjectFn? deleteObjectFn,
  SupabaseClient? client,
}) async {
  final deleteObject =
      deleteObjectFn ??
      (String path) =>
          storage.deleteListingImageObject(listingImagesBucket, path, client: client);
  var deleted = 0;
  var ok = true;
  // 하나가 실패해도 나머지는 계속 시도한다. 첫 실패에서 멈추면 이미 지운 앞부분은 되돌릴 수
  // 없는데 뒤는 손도 못 댄 상태가 남는다(§10.1).
  for (final path in paths) {
    if (await deleteObject(path)) {
      deleted += 1;
      continue;
    }
    // ignore: avoid_print
    print('[sell] 매물 사진 오브젝트 정리 실패 — 회수 가능한 고아로 남는다: $path');
    ok = false;
  }
  return (ok: ok, deleted: deleted);
}

/// 매물 사진을 화면 상태 → DB·Storage에 반영한다.
///
/// [photos]는 현재 화면 상태(추가·삭제·재배치 반영됨), [initialPhotos]는 저장 기준선(무엇을
/// 지웠는지 판단하는 데 쓴다) — 호출부(sell_controller.dart)가 관리한다.
Future<PhotoSyncResult> syncListingPhotos(
  String userId,
  String listingId,
  List<PhotoItem> photos,
  List<PhotoItem> initialPhotos, {
  SupabaseClient? client,
  ResizeFn resizeFn = resizeImage,
  UploadFn? uploadFn,
  DeleteObjectFn? deleteObjectFn,
}) async {
  // 화면도 저장 기준선도 비어 있으면 정말로 할 일이 없다(추가도 삭제도 없음) — 대표 리셋조차
  // 쏠 이유가 없는 매물(사진 0장)에 빈 UPDATE를 날리지 않는다.
  if (photos.isEmpty && initialPhotos.isEmpty) {
    return const PhotoSyncResult(photos: [], savedCount: 0, failedCount: 0, warnings: []);
  }

  final supa = client ?? supabase;
  final upload =
      uploadFn ??
      (String u, String l, String filename, Uint8List bytes, String contentType) =>
          storage.uploadListingImage(
            listingImagesBucket,
            u,
            l,
            filename,
            bytes,
            contentType: contentType,
            client: supa,
          );
  final deleteObject =
      deleteObjectFn ??
      (String path) => storage.deleteListingImageObject(listingImagesBucket, path, client: supa);

  final next = <PhotoItem>[];
  var failedCount = 0;
  final warnings = <String>[];

  // ── 1) 삭제 — 화면에서 사라진 기존 사진 ──────────────────────────────
  // 지우려 했지만 못 지운 사진들은 **맨 뒤에** 붙인다 — 앞에 붙이면 사용자가 지우려던 사진이
  // 0번이 되어 대표 도장을 받는다.
  final undeletable = <PhotoItem>[];
  final keptRowIds = photos.map((p) => p.rowId).whereType<String>().toSet();
  for (final gone in initialPhotos.where(
    (p) => p.rowId != null && !keptRowIds.contains(p.rowId),
  )) {
    // ⚠️ 순서 ① — 오브젝트 먼저. 반대로 하면 고아가 된다(§10.1).
    final objectGone = gone.storagePath != null ? await deleteObject(gone.storagePath!) : true;
    if (!objectGone) {
      // retryable:false다 — 재시도 버튼이 없다(위젯이 retryable에서만 그린다). 문구도 그에
      // 맞춘다: "다시 시도해주세요"는 존재하지 않는 버튼을 가리켜 사용자를 헷갈리게 한다(review
      // 발견, spec-16-7). 실제 복구 동작은 삭제(X) 버튼을 다시 눌러 이 항목을 다시 제거 대상으로
      // 표시하는 것이다.
      warnings.add('사진을 삭제하지 못했어요. 삭제 버튼을 다시 눌러주세요.');
      failedCount += 1;
      undeletable.add(
        PhotoItem(
          key: gone.key,
          previewUrl: gone.previewUrl,
          status: PhotoStatus.error,
          error: '사진을 삭제하지 못했어요. 삭제 버튼을 다시 눌러주세요.',
          retryable: false,
          storagePath: gone.storagePath,
          rowId: gone.rowId,
        ),
      );
      continue;
    }
    var rowGone = true;
    try {
      final removed = await supa
          .from('listing_images')
          .delete()
          .eq('id', gone.rowId!)
          .select('id');
      rowGone = removed.isNotEmpty;
    } catch (e) {
      // ignore: avoid_print
      print('[sell] listing_images 행 삭제 실패: ${gone.rowId}, $e');
      rowGone = false;
    }
    if (!rowGone) {
      // 오브젝트는 지워졌는데 행이 남았다 — 예전엔 warning만 남기고 이 항목을 목록에서
      // **완전히 빼버렸다**. 그러면 사용자는 지워진 줄 알지만 DB엔 "파일 없는 행"이 영구히
      // 남아 10장 정원을 먹고, 대표 선정((sort_order,id) 최솟값)에까지 끼어든다 — 그리고
      // 목록에 없으니 baseline에도 없어 다음 제출에서 재시도조차 안 된다(review 발견,
      // spec-16-7). 오브젝트 삭제 실패와 똑같이 목록 맨 뒤로 되돌려, 삭제 버튼을 다시 눌러
      // 재시도할 수 있게 한다(그때 오브젝트는 이미 없으므로 행 삭제만 다시 시도된다).
      warnings.add('사진 삭제 정보를 정리하지 못했어요. 삭제 버튼을 다시 눌러주세요.');
      failedCount += 1;
      undeletable.add(
        PhotoItem(
          key: gone.key,
          previewUrl: gone.previewUrl,
          status: PhotoStatus.error,
          error: '사진 삭제 정보를 정리하지 못했어요. 삭제 버튼을 다시 눌러주세요.',
          retryable: false,
          storagePath: gone.storagePath,
          rowId: gone.rowId,
        ),
      );
    }
  }

  // ── 2) 업로드 — 새로 고른 사진을 화면 순서대로 **순차** 처리 ───────────
  // 순차인 이유(AC9): 10장 상한 트리거가 count-후-insert라 동시 삽입이 경합하면 새는 것이
  // 코드상 명백하다. 병렬로 올리면 빠르지만 그 경합을 우리가 직접 만들게 된다.
  for (final p in photos) {
    // 이미 저장된 사진(기존 행)은 업로드 대상이 아니다.
    if (p.storagePath != null) {
      next.add(p);
      continue;
    }
    // 검증 실패(용량초과·포맷거부) 항목 — 애초에 업로드된 적이 없고 다시 시도해도 결과가
    // 같다(retryable:false). 목록엔 남기되(AC3), 이번 실행이 만든 실패가 아니므로 세지 않는다.
    if (p.status == PhotoStatus.error && !p.retryable) {
      next.add(p);
      continue;
    }
    if (p.file == null) {
      failedCount += 1;
      next.add(
        PhotoItem(
          key: p.key,
          previewUrl: p.previewUrl,
          status: PhotoStatus.error,
          error: p.error ?? '이 사진은 저장하지 못했어요.',
          retryable: p.retryable,
        ),
      );
      continue;
    }

    try {
      final encoded = await resizeFn(p.file!);
      final result = await upload(
        userId,
        listingId,
        _newFilename(encoded.extension),
        encoded.bytes,
        encoded.mimeType,
      );
      if (result.ok) {
        next.add(
          PhotoItem(
            key: p.key,
            previewUrl: p.previewUrl,
            status: PhotoStatus.uploaded,
            storagePath: result.storagePath,
            file: p.file,
          ),
        );
      } else {
        failedCount += 1;
        next.add(
          PhotoItem(
            key: p.key,
            previewUrl: p.previewUrl,
            status: PhotoStatus.error,
            error: result.reason,
            retryable: true,
            file: p.file,
          ),
        );
      }
    } catch (e) {
      // ignore: avoid_print
      print('[sell] 사진 변환/업로드 예외: $e');
      failedCount += 1;
      next.add(
        PhotoItem(
          key: p.key,
          previewUrl: p.previewUrl,
          status: PhotoStatus.error,
          error: '사진을 처리하지 못했어요. 다시 시도해주세요.',
          retryable: true,
          file: p.file,
        ),
      );
    }
  }

  // 못 지운 사진은 여기서 합류한다 — 목록 맨 뒤(위 주석).
  next.addAll(undeletable);

  // ── 3) 행 기록 — **업로드가 실제 성공한 사진만** 행을 만든다(AC6) ───────
  // spec-16-11(DW-748) 이후 실제 규칙: sort_order 숫자는 아래 candidateOrder()가 "예약된
  // 값(스냅샷 + 이번 실행에서 이미 쓴 값)과 겹치지 않는 값"을 고르는 방식으로 정해진다 — 지켜야
  // 하는 계약은 **유일성**뿐이고 **연속성은 보장하지 않는다**(구멍이 남아도 정상이다). 실패한
  // 행은 새 번호를 못 받고 옛 번호를 그대로 든 채 DB에 남는다.
  //
  // spec-16-11 결함1 근본수정: `status: PhotoStatus.error`인 항목(위 undeletable 등)은 **저장
  // 대상에서만** 뺀다 — `next`(화면 목록)에는 그대로 남아 있어 사용자가 재시도할 수 있다(위
  // ⚠️ 주석). 이 필터가 없던 예전엔 Storage는 지워졌는데 행 삭제만 실패한 항목이 여기서 정상
  // 사진과 똑같이 취급돼 sort_order를 다시 받았고, 그 항목이 saved의 유일한 원소면 반드시
  // order==0(대표)이 됐다 — 파일 없는 행이 대표가 되는 결함(2026-08-10 묶음 코드리뷰 D1).
  final saved = next
      .where((p) => p.storagePath != null && p.status != PhotoStatus.error)
      .toList();
  var savedCount = 0;
  var order = 0;
  // 실제로 저장에 성공한 사진의 경로. 4단계가 대표를 여기에 건다(재계산하지 않는다 — 재계산하면
  // 어느 항목이 탈락하는지에 대한 두 계산의 판단이 갈릴 수 있다).
  String? coverPath;
  // spec-16-11 결함2(DW-748) 이후: 대표는 "sort_order==0"이 아니라 **saved 순서상 처음으로
  // 실제 저장에 성공한 항목**으로 판정한다 — 아래 예약 체계 때문에 대표(화면 맨 앞 사진)가 항상
  // 숫자 0을 받는다는 보장이 없어졌다(그래도 화면 순서상 맨 앞이라는 사실은 그대로다).
  var coverAssigned = false;
  // spec-16-11 후속 코드리뷰 2회차 패치(P1) — sort_order UPDATE 실패 문구를 **조건**으로만
  // 기록해 두고, 실제 문장은 아래 3단계 루프가 끝난 뒤 한 번만 조립한다(warnings.add를 실패
  // 분기마다 직접 부르면, 대표 확정 전에 실패한 행과 확정 후에 실패한 행이 각각 다른 문자열을
  // 넣어 toSet()으로도 못 합쳐지는 중복·모순 문구가 그대로 사용자에게 나간다 — 측정: "…대표
  // 사진이 바뀌었을 수 있어요. · 사진 순서를 저장하지 못한 항목이 있어요.").
  var orderSaveFailed = false;
  var coverMayHaveChanged = false;

  // spec-16-11 결함2(DW-748) — 기존 행 sort_order UPDATE가 실패하면 그 행은 옛 번호를 그대로
  // 들고 DB에 남는다. 이번 호출이 새로 매기는 번호가 그 옛 번호와 겹치면 (sort_order,id) 최솟값
  // 판정에서 사용자가 아래로 내린 사진이 대표가 될 수 있다(listings_repository.dart
  // pickCoverImages — **대표는 is_cover가 아니라 이 규칙으로 읽힌다**, 이 파일 최상단 경고와
  // 동일 근거). 그래서 이 매물의 **현재** sort_order 전체를 미리 한 번 읽어 "아직 비워지지
  // 않았을 수 있는 번호"로 예약해 두고, 새 번호를 고를 때 예약된 번호를 건너뛴다.
  // undeletable(위에서 저장 대상에서 뺀 행)의 옛 번호도 여기 포함된다 — 그 행은 이 루프에서
  // 손대지 않으므로 끝까지 예약 상태로 남는다.
  //
  // Design Notes(spec Design Notes 참조) — 후보 ⓐ(카운터를 올린다)+ⓑ(전체를 한 번에 계산)를
  // 조합했다: ⓐ만으로는 "재정렬 + 실패가 겹친" 경우 새 값이 다른 행의 옛(아직 안 비워진) 값과
  // 우연히 같아지는 것을 못 막는다(옛 값을 모르면 피할 수 없다) — 그래서 옛 값을 먼저 읽는 ⓑ를
  // 더했다. ⓒ(실패 시 이번 저장 전체를 다음으로 미룸)는 이미 성공한 UPDATE를 되돌릴 방법이
  // 없어(원자적 다건 UPDATE는 DB 함수 없이 불가 — Block If) 채택하지 않았다.
  //
  // ⚠️ "중복 없음"만으로는 부족하다 — 대표를 잘못 잡은 상태로 남아 있는 것도 이 스토리가 잡으려는
  // 결함이다(파일 최상단 경고). 그래서 **아직 아무도 대표가 되지 못한 동안**(!coverAssigned)엔,
  // 시도하는 후보에게 예약된 값보다 **반드시 작은** 번호(필요하면 음수)를 준다 — sort_order는
  // 화면에 노출되지 않는 내부 정렬키이고 DB엔 하한 CHECK가 없다(0012_listing_images.sql 실측).
  // 이러면 그 후보가 성공하는 순간 **다른 무엇이 실패해 옛 번호를 그대로 들고 있어도** 항상
  // (sort_order,id) 최솟값으로 이긴다. 최초 후보(화면 맨 앞)가 실패하면 다음 후보가 그 자리를
  // 이어받아 같은 방식으로 다시 시도한다 — 그래서 "화면 맨 앞"이 아니라 "처음 성공한 항목"이
  // 최종 대표가 된다(위 coverAssigned 판정과 정확히 같은 기준). 대표 후보 스스로의 UPDATE가
  // 계속 실패하는 경우(자기 자신을 못 쓰는 경우)까지는 이 장치로도 구할 수 없다 — 그건 아래
  // 강화된 warning으로 사용자에게 알린다.
  // 값 -> 그 값을 아직 들고 있는 행 수. 코드리뷰(2026-08-10)에서 지적된 대로, 이미 옛 번호가
  // 중복된 매물(DW-748이 원래 겨냥한, 아직 정리되지 않은 데이터)에서는 같은 값을 든 행이
  // 둘 이상일 수 있다 — 그중 하나가 성공했다고 그 값 전체를 안전하다고 풀어주면 나머지가 여전히
  // 그 값을 들고 있는데도 다른 행이 같은 값을 다시 배정받을 수 있다. 그래서 개수를 센다.
  final reservedOrders = <int, int>{};
  final oldOrderByRowId = <String, int>{};
  // spec-16-11 후속 코드리뷰 2회차 패치(P2) — 아래 스냅샷 조회가 실제로 성공했는지 기록해
  // 둔다. "대표가 이미 정해졌으니(coverAssigned) 이후 실패는 대표를 못 바꾼다"는 판단은 이
  // 스냅샷이 실제로 읽혔을 때만 참이다 — 못 읽었으면 candidateOrder가 옛 번호와의 충돌을 못
  // 피해 실패 행의 옛 번호가 새로 매긴 값보다 작을 수 있다(경고 문구 조립부 참조).
  var snapshotOk = true;
  // spec-16-11 후속 코드리뷰 패치(P2) — 이 게이트는 "이 호출이 번호를 매기려 하는가"를 물어야
  // 한다("화면이 기존 사진을 들고 왔는가"가 아니다). `initialPhotos`는 호출부가 준 화면
  // 기준선일 뿐이라 비어 있어도 DB에는 번호를 매길 살아 있는 행이 있을 수 있다(예: 이전
  // INSERT의 rowId를 못 읽어 baseline에서 빠진 경우, toPhotoItems가 계약 위반 행을 버린
  // 경우). 아래 3단계가 실제로 번호를 매길 대상은 `saved`이므로 그것을 기준으로 켠다 —
  // 대가: 신규 매물 생성 경로(기존 행이 정말 없는 경우)에서도 빈 결과 GET 1회가 추가된다.
  // 고아 행을 잡기 위한 의도적 비용이다.
  if (saved.isNotEmpty) {
    try {
      final existingRows = await supa
          .from('listing_images')
          .select('id, sort_order')
          .eq('listing_id', listingId);
      for (final r in existingRows) {
        final id = r['id'];
        final so = r['sort_order'];
        if (id is String && so is int) {
          reservedOrders[so] = (reservedOrders[so] ?? 0) + 1;
          oldOrderByRowId[id] = so;
        }
      }
    } catch (e) {
      // 조회 실패해도 저장 자체를 막을 이유는 아니다 — 이 안전망만 못 켠 채(예전과 동일하게)
      // 진행한다. 다만 이 안전망이 꺼졌다는 사실 자체가 "대표가 바뀔 수 있는 상황"이므로(스펙
      // Always: 사실대로 알린다) 조용히 넘어가지 않고 사용자에게도 알린다.
      // ignore: avoid_print
      print('[sell] 기존 sort_order 조회 실패(중복 회피 안전망 비활성): $e');
      warnings.add('기존 사진 순서 정보를 불러오지 못해 일부 안전 점검을 건너뛰었어요. 저장 후 대표 사진을 확인해 주세요.');
      snapshotOk = false;
    }
  }

  // [o]를 아직 다른 행이 들고 있으면 true. 자기 옛 번호([ownOld])는 **자신이 유일한 보유자일
  // 때만** 예외로 false다 — 이미 옛 번호가 중복된 데이터에서는 자기 옛 번호라도 다른 행이 함께
  // 들고 있으면 여전히 true다(바로 아래 주석 참조).
  bool isReserved(int o, int? ownOld) {
    // spec-16-11 후속 코드리뷰 패치(P3) — "자기 옛 자리를 다시 쓰는 것은 항상 안전하다"는
    // 이미 옛 번호가 중복된 데이터(reservedOrders[o] >= 2, DW-748이 원래 겨냥한 상태)에서는
    // 거짓이다 — 그 자리를 든 행이 자신 말고도 남아 있으면 그대로 재사용해도 그 다른 행과
    // 여전히 겹친다. 자신이 그 값의 유일한 보유자일 때만 예외를 준다.
    if (o == ownOld && (reservedOrders[o] ?? 0) <= 1) return false;
    return (reservedOrders[o] ?? 0) > 0;
  }

  // 이 행이 실제로 새 번호를 받아 옛 자리를 비웠을 때 호출한다 — 마지막 한 행이 빠져나갈 때만
  // 그 값을 예약 목록에서 완전히 지운다(위 개수 세기와 짝).
  void releaseReserved(int? o) {
    if (o == null) return;
    final count = reservedOrders[o];
    if (count == null) return;
    if (count <= 1) {
      reservedOrders.remove(o);
    } else {
      reservedOrders[o] = count - 1;
    }
  }

  // 예약된 번호(다른 행이 아직 들고 있을 수 있는 옛 번호)를 건너뛰고 다음 안전한 번호를 고른다.
  int claimOrder(int candidate, int? ownOld) {
    var o = candidate;
    while (isReserved(o, ownOld)) {
      o += 1;
    }
    return o;
  }

  // 이번 항목이 받을 번호를 정한다. 이미 누가 대표가 됐으면(coverAssigned) 예약된 값을 건너뛰는
  // 평범한 claimOrder만 쓴다. **아직 아무도 대표가 아니면** 이 항목이 대표 후보다(위 Design
  // Notes) — 그런데 자기 옛 번호([ownOld])가 (자신을 뺀) 다른 모든 예약값보다 **반드시 더
  // 작을 때만** 그대로 쓴다. `<=`로 완화하면(2회차 후속 코드리뷰가 지적한 DW-748 재발 지점 —
  // ownOld == minOther인 경우) 그 값을 아직 들고 있는 다른 행과 살아 있는 중복을 다시 만든다
  // (측정: row-a=0, row-b=0인 데이터에서 b의 UPDATE가 실패하면 a가 0을 다시 써서 중복이
  // 재생산된다). 반대로 이 조건 자체가 없으면(무조건 내려간다면) 실패가 전혀 없는 평범한
  // 재저장에서도 매번 예약값보다 하나 작은 번호를 새로 받아, 저장을 반복할 때마다 sort_order가
  // 한없이 음수로 밀려난다(코드리뷰 2026-08-10 실측 지적) — 그건 이 스토리가 막으려는 "연속
  // 정수" 계약 위반과 같은 결이다. 정말로 자기보다 작은 값을 다른 행이 아직 들고 있을 때만
  // (ownOld가 minOther보다 작지 않을 때만) 그 값보다 작은 번호(필요하면 음수)로 내려간다.
  int candidateOrder(int? ownOld) {
    if (coverAssigned) return claimOrder(order, ownOld);
    int? minOther;
    for (final entry in reservedOrders.entries) {
      final effectiveCount = entry.key == ownOld ? entry.value - 1 : entry.value;
      if (effectiveCount > 0 && (minOther == null || entry.key < minOther)) {
        minOther = entry.key;
      }
    }
    if (ownOld != null && (minOther == null || ownOld < minOther)) {
      return ownOld;
    }
    return minOther == null ? order : minOther - 1;
  }

  for (final p in saved) {
    if (p.rowId != null) {
      // 기존 행 — 순서만 다시 매긴다. is_cover는 여기서 건드리지 않는다(4단계에서 한 번에).
      final ownOld = oldOrderByRowId[p.rowId];
      order = candidateOrder(ownOld);
      try {
        final data = await supa
            .from('listing_images')
            .update({'sort_order': order})
            .eq('id', p.rowId!)
            .select('id');
        if (data.isEmpty) {
          // spec-16-11 후속 코드리뷰 2회차 패치(P1+P2) — 문자열이 아니라 조건만 기록한다(위
          // orderSaveFailed 선언부 설명 참조). "대표가 이미 정해진 뒤(coverAssigned)면 이
          // 실패 행은 (sort_order,id) 최솟값을 못 이긴다"는 판단은 **예약 스냅샷 조회가 실제로
          // 성공했을 때만**(snapshotOk) 참이다 — 못 읽었으면 candidateOrder가 옛 번호와의
          // 충돌을 못 피해, 이 실패 행의 옛 번호가 새로 매긴 값보다 작을 수 있다(측정: row-a=5,
          // row-b=-3 상태에서 스냅샷 GET이 500, b의 PATCH가 400이면 최종 {a:0, b:-3}으로 대표가
          // 실제로 b에게 넘어간다). 그래서 !coverAssigned뿐 아니라 !snapshotOk도 조건에 넣는다.
          orderSaveFailed = true;
          if (!coverAssigned || !snapshotOk) {
            coverMayHaveChanged = true;
          }
          // DW-748: 이 행은 옛 번호를 그대로 들고 남는다. !coverAssigned인 동안은 candidateOrder가
          // order를 참조하지 않고 minOther로 다시 계산하므로 이 증가는 아직 의미가 없다 — 누군가
          // 대표가 된 뒤(coverAssigned) claimOrder가 order를 쓰기 시작할 때부터 "다음 항목이 이
          // 번호를 다시 쓰지 않는다"는 뜻이 실제로 작동한다.
          order += 1;
          continue;
        }
      } catch (e) {
        // ignore: avoid_print
        print('[sell] sort_order 갱신 실패: ${p.rowId}, $e');
        // 위 data.isEmpty 분기와 같은 이유(P1+P2) — 문자열이 아니라 조건만 기록한다.
        orderSaveFailed = true;
        if (!coverAssigned || !snapshotOk) {
          coverMayHaveChanged = true;
        }
        order += 1; // 위와 동일 이유(DW-748 — coverAssigned 전에는 아직 의미가 없다).
        continue;
      }
      // spec-16-11 후속 코드리뷰 패치(P4) — candidateOrder(ownOld)가 예약 회피를 위해 ownOld가
      // 아닌 값을 돌려준 경우에만 옛 자리가 실제로 비워진다. candidateOrder가 ownOld를 그대로
      // 돌려준 경우(자기 옛 번호를 재사용) 이 행은 여전히 그 값을 들고 있으므로 풀어주면
      // "값 -> 그 값을 아직 들고 있는 행 수" 계약과 모순된다. 현재는 대표 확정 이후 카운터가
      // 단조 증가라 candidateOrder가 ownOld를 그대로 돌려주는 경로와 이 지점이 겹치지 않아
      // 잠재적(latent) 결함이었다 — 그래도 계약을 그대로 지키도록 가드한다.
      if (order != ownOld) {
        releaseReserved(ownOld);
      }
      if (!coverAssigned) {
        coverPath = p.storagePath;
        coverAssigned = true;
      }
      order += 1;
      continue;
    }
    // 새 행 — is_cover는 항상 false로 넣는다. 대표 지정은 4단계가 전담한다(부분 유니크 인덱스 충돌 회피).
    order = candidateOrder(null); // 새 행엔 지킬 "옛 번호"가 없다.
    //
    // ⚠️ try는 **INSERT 한 문장만** 감싼다. 예전엔 성공 이후 코드(`next.indexOf`·`id` 캐스팅)까지
    // 같은 try 안에 있어서, 행이 실제로 만들어진 뒤에 난 예외도 "INSERT 실패"로 간주돼 아래
    // 보상 로직이 **살아 있는 행이 가리키는 파일을 지웠다**(review 발견, spec-16-7).
    final Map<String, dynamic> data;
    try {
      data = await supa
          .from('listing_images')
          .insert({
            'listing_id': listingId,
            'storage_path': p.storagePath,
            'sort_order': order,
            'is_cover': false,
          })
          .select('id')
          .single();
    } catch (e) {
      // 행이 없으면 그 오브젝트는 아무도 못 읽는 고아가 된다 → 즉시 정리를 시도한다.
      final cleaned = await deleteObject(p.storagePath!);
      // ignore: avoid_print
      print(
        '[sell] listing_images INSERT 실패: ${p.storagePath}, $e, '
        '고아 오브젝트 정리 시도: ${cleaned ? '성공' : '실패(고아 잔존)'}',
      );
      final idx = next.indexOf(p);
      if (idx >= 0) {
        next[idx] = PhotoItem(
          key: p.key,
          previewUrl: p.previewUrl,
          status: PhotoStatus.error,
          error: '사진 정보를 저장하지 못했어요.',
          retryable: true,
          file: p.file,
        );
      }
      failedCount += 1;
      continue; // 카운터를 올리지 않는다 — 구멍 방지(INSERT 실패는 옛 번호를 남기지 않으므로 안전).
    }

    // ── 여기부터는 INSERT가 확실히 성공한 뒤다. 무슨 일이 나도 위 보상 삭제로 내려가지 않는다.
    savedCount += 1;
    if (!coverAssigned) {
      coverPath = p.storagePath;
      coverAssigned = true;
    }
    order += 1;
    // INSERT 성공 시 rowId를 화면 상태에 되돌려준다 — 안 하면 재제출 때 이 항목이 "기존 행"으로
    // 인식되지 않아 같은 storage_path로 재INSERT를 시도한다(역고아 방지).
    // `as String` 강제 캐스팅을 쓰지 않는다 — 응답 형태가 예상과 달라도 여기서 예외가 나면
    // 저장은 됐는데 제출 전체가 실패로 보고된다. 못 읽으면 rowId만 비워 둔다.
    final newRowId = data['id'];
    final idx = next.indexOf(p);
    if (idx >= 0) {
      next[idx] = PhotoItem(
        key: p.key,
        previewUrl: p.previewUrl,
        status: p.status,
        storagePath: p.storagePath,
        file: p.file,
        rowId: newRowId is String ? newRowId : null,
      );
    }
  }

  // spec-16-11 후속 코드리뷰 2회차 패치(P1+P2) — 루프 안에서 여러 행이 sort_order UPDATE에
  // 실패해도 문장은 **정확히 하나**만 남긴다(위 orderSaveFailed/coverMayHaveChanged 선언부
  // 설명 참조).
  if (orderSaveFailed) {
    warnings.add(
      coverMayHaveChanged
          ? '사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.'
          : '사진 순서를 저장하지 못한 항목이 있어요.',
    );
  }

  // ── 4) 대표 기록 — **반드시 2문장**(AC8) ────────────────────────────────
  // 이 매물 전체를 false로 내린 뒤 3단계에서 실제로 저장에 성공한 첫 장(coverPath)만 true로
  // 올린다. 한 문장으로 뒤집으면 부분 유니크 인덱스에 걸려 duplicate key로 죽는다(#47-1).
  bool resetFailed;
  try {
    final reset = await supa
        .from('listing_images')
        .update({'is_cover': false})
        .eq('listing_id', listingId)
        .select('id');
    // 0행 자체는 실패가 아니다 — 사진이 0장인 매물엔 내릴 행이 없다. 그러나 대표로 지정할
    // 사진이 있는데(coverPath) 내려진 행이 0개면 앞뒤가 안 맞는다(RLS 차단 등) → 실패로 본다.
    resetFailed = coverPath != null && reset.isEmpty;
  } catch (e) {
    // ignore: avoid_print
    print('[sell] is_cover 초기화 실패: $e');
    resetFailed = true;
  }

  if (resetFailed) {
    warnings.add('대표 사진 정보를 정리하지 못했어요.');
    // ⚠️ 리셋이 실패하면 다음 문장(true 지정)을 아예 쏘지 않는다 — 부분 유니크 인덱스에 걸려
    // 어차피 실패하고, 조용히 "대표 0장" 상태만 남기 때문이다.
  } else if (coverPath != null) {
    try {
      final set = await supa
          .from('listing_images')
          .update({'is_cover': true})
          .eq('listing_id', listingId)
          .eq('storage_path', coverPath)
          .select('id');
      if (set.isEmpty) {
        warnings.add('대표 사진을 지정하지 못했어요.');
      }
    } catch (e) {
      // ignore: avoid_print
      print('[sell] 대표 지정 실패: $coverPath, $e');
      warnings.add('대표 사진을 지정하지 못했어요.');
    }
  }

  // 같은 사유가 사진 수만큼 쌓이므로 중복을 없앤다 — 소비처가 ' · '로 이어 붙여 보여주기 때문에
  // 안 없애면 같은 문구가 여러 번 이어 붙는다.
  return PhotoSyncResult(
    photos: next,
    savedCount: savedCount,
    failedCount: failedCount,
    warnings: warnings.toSet().toList(),
  );
}
