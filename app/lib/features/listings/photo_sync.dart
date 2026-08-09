// 매물 사진을 화면 상태 → DB·Storage에 반영한다(AC3·AC5·AC6·AC8·AC9·AC10).
// web `web/src/app/(user)/sell/photo-sync.ts`의 미러 — 지켜야 하는 순서가 둘 있고, 둘 다 그
// 파일의 실측(§10.1)에서 나온 것을 그대로 이식한다:
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

/// 매물의 사진 파일을 정리한다(조회+삭제). **매물 행이 아직 살아 있을 때만** 의미가 있다 — 행이
/// 사라진 뒤엔 조회가 0건이라 아무것도 못 지운다. 매물 삭제 흐름에서는 이 함수 대신
/// listListingPhotoPaths → (매물 삭제) → deletePhotoObjectsByPaths 를 쓴다(listings_repository.dart).
Future<({bool ok, int deleted})> deleteListingPhotoObjects(
  String listingId, {
  SupabaseClient? client,
}) async {
  final result = await listListingPhotoPaths(listingId, client: client);
  if (!result.ok) return (ok: false, deleted: 0);
  return deletePhotoObjectsByPaths(result.paths, client: client);
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
      warnings.add('사진을 삭제하지 못했어요. 다시 시도해주세요.');
      failedCount += 1;
      undeletable.add(
        PhotoItem(
          key: gone.key,
          previewUrl: gone.previewUrl,
          status: PhotoStatus.error,
          error: '사진을 삭제하지 못했어요. 다시 시도해주세요.',
          retryable: false,
          storagePath: gone.storagePath,
          rowId: gone.rowId,
        ),
      );
      continue;
    }
    try {
      final removed = await supa
          .from('listing_images')
          .delete()
          .eq('id', gone.rowId!)
          .select('id');
      if (removed.isEmpty) {
        warnings.add('사진 삭제 정보를 정리하지 못했어요.');
      }
    } catch (e) {
      // ignore: avoid_print
      print('[sell] listing_images 행 삭제 실패: ${gone.rowId}, $e');
      warnings.add('사진 삭제 정보를 정리하지 못했어요.');
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
  // sort_order는 화면 인덱스가 아니라 **실제로 저장(갱신)에 성공한 개수**로 매긴다 — 실패하면
  // 카운터를 올리지 않아 다음 생존 항목이 그 자리를 그대로 메운다(구멍 방지).
  final saved = next.where((p) => p.storagePath != null).toList();
  var savedCount = 0;
  var order = 0;
  // 실제로 sort_order=0을 받은 사진의 경로. 4단계가 대표를 여기에 건다(재계산하지 않는다 —
  // 재계산하면 어느 항목이 탈락하는지에 대한 두 계산의 판단이 갈릴 수 있다).
  String? coverPath;

  for (final p in saved) {
    if (p.rowId != null) {
      // 기존 행 — 순서만 다시 매긴다. is_cover는 여기서 건드리지 않는다(4단계에서 한 번에).
      try {
        final data = await supa
            .from('listing_images')
            .update({'sort_order': order})
            .eq('id', p.rowId!)
            .select('id');
        if (data.isEmpty) {
          warnings.add('사진 순서를 저장하지 못한 항목이 있어요.');
          continue; // 카운터를 올리지 않는다 — 구멍 방지.
        }
      } catch (e) {
        // ignore: avoid_print
        print('[sell] sort_order 갱신 실패: ${p.rowId}, $e');
        warnings.add('사진 순서를 저장하지 못한 항목이 있어요.');
        continue;
      }
      if (order == 0) coverPath = p.storagePath;
      order += 1;
      continue;
    }
    // 새 행 — is_cover는 항상 false로 넣는다. 대표 지정은 4단계가 전담한다(부분 유니크 인덱스 충돌 회피).
    try {
      final data = await supa
          .from('listing_images')
          .insert({
            'listing_id': listingId,
            'storage_path': p.storagePath,
            'sort_order': order,
            'is_cover': false,
          })
          .select('id')
          .single();
      savedCount += 1;
      if (order == 0) coverPath = p.storagePath;
      order += 1;
      // INSERT 성공 시 rowId를 화면 상태에 되돌려준다 — 안 하면 재제출 때 이 항목이 "기존 행"으로
      // 인식되지 않아 같은 storage_path로 재INSERT를 시도한다(역고아 방지).
      final idx = next.indexOf(p);
      if (idx >= 0) {
        next[idx] = PhotoItem(
          key: p.key,
          previewUrl: p.previewUrl,
          status: p.status,
          storagePath: p.storagePath,
          file: p.file,
          rowId: data['id'] as String,
        );
      }
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
      continue; // 카운터를 올리지 않는다 — 구멍 방지.
    }
  }

  // ── 4) 대표 기록 — **반드시 2문장**(AC8) ────────────────────────────────
  // 이 매물 전체를 false로 내린 뒤 3단계에서 실제로 sort_order=0을 받은 1장만 true로 올린다.
  // 한 문장으로 뒤집으면 부분 유니크 인덱스에 걸려 duplicate key로 죽는다(#47-1).
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
