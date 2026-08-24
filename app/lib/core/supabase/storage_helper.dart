// 공개 스토리지 아티팩트용 URL 헬퍼 (아티팩트 범용 — 특정 버킷·이미지 로직을 하드코딩하지 않는다).
// web `web/src/lib/storage/index.ts`의 미러.
//
// Story 9.0 전까지는 비공개 버킷 + 서명 URL이었다(발급 왕복·1시간 만료·실패 시 null).
// 공개 버킷으로 바뀌면서 URL은 경로에서 바로 조립된다 — 네트워크 왕복도, 만료도, 실패도 없다.
//
// 쓰기측 헬퍼(Story 16.7) — web `web/src/lib/storage/upload.ts`의 미러. 경로 규칙·upsert 금지
// 사유는 그 파일의 주석과 동일하다(docs/conventions.md §10.1).
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'supabase_client.dart';

/// 공개 버킷 오브젝트의 고정 URL을 만든다.
///
/// ⚠️ 파일이 실제로 있는지 확인하지 않는다 — 경로만 있으면 문자열이 나온다.
/// 없는 파일은 이미지 로드가 실패하므로, 소비처가 `errorBuilder`로 "사진 준비중"을 그려야 한다
/// (docs/conventions.md §4).
String getPublicUrl(String bucket, String path) {
  return supabase.storage.from(bucket).getPublicUrl(path);
}

/// 경로 규약 `{user_id}/{listing_id}/{filename}`(§10) — 첫 세그먼트가 소유자라는 것을
/// Storage RLS가 검사하고, listing_images 행 쪽은 0013 트리거가 같은 규약을 강제한다.
/// 파일명은 uuid라 충돌이 없다 — 그래서 upsert가 필요 없다(아래 uploadListingImage 주석 참조).
String buildStoragePath(String userId, String listingId, String filename) {
  return '$userId/$listingId/$filename';
}

/// 업로드 결과 — 실패는 throw하지 않고 사유를 돌려준다(사진 1장의 실패가 폼 제출을 막으면 안 된다, AC3).
class UploadResult {
  const UploadResult.ok(this.storagePath) : ok = true, reason = null;
  const UploadResult.error(this.reason) : ok = false, storagePath = null;

  final bool ok;
  final String? storagePath;
  final String? reason;
}

/// 저장본 바이트 1장을 업로드한다.
///
/// ⚠️ upsert를 쓰지 않는다(기본값 false 유지) — web upload.ts의 원격 실측(2026-07-18)과 동일하게
/// x-upsert:true는 같은 토큰·같은 경로에서도 403으로 막힌다(업서트가 존재확인 SELECT를 거치는데
/// 그 SELECT가 listing_images 행에 의존하는 읽기 정책에 걸린다, docs/tech-debt.md #51 계승).
/// 파일명이 uuid라 애초에 덮어쓸 일도 없다.
Future<UploadResult> uploadListingImage(
  String bucket,
  String userId,
  String listingId,
  String filename,
  Uint8List bytes, {
  required String contentType,
  SupabaseClient? client,
}) async {
  final storagePath = buildStoragePath(userId, listingId, filename);
  final supa = client ?? supabase;

  try {
    await supa.storage
        .from(bucket)
        .uploadBinary(
          storagePath,
          bytes,
          fileOptions: FileOptions(contentType: contentType, upsert: false),
        );
    return UploadResult.ok(storagePath);
  } catch (e) {
    debugPrint('[sell] 사진 업로드 실패: $storagePath, $e');
    return const UploadResult.error('사진을 올리지 못했어요. 다시 시도해주세요.');
  }
}

/// Storage 오브젝트 1개를 지운다.
///
/// **반환값의 뜻은 "지웠다"가 아니라 "오브젝트가 이제 없다"**다. web upload.ts의 원격 실측
/// (2026-07-19)과 동일한 이유로, 이미 없던 파일도 "없다"는 목적을 만족한다.
///
/// ⚠️ **전제(계약): 이 함수는 해당 `listing_images` 행이 아직 살아 있는 동안 불러야 한다**
/// (삭제 순서 계약, docs/conventions.md §10.1 — 오브젝트 먼저, 행은 나중).
Future<bool> deleteListingImageObject(
  String bucket,
  String storagePath, {
  SupabaseClient? client,
}) async {
  final supa = client ?? supabase;
  try {
    await supa.storage.from(bucket).remove([storagePath]);
    return true;
  } catch (e) {
    debugPrint('[sell] 사진 오브젝트 삭제 실패: $storagePath, $e');
    return false;
  }
}
