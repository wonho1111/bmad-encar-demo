// 비공개 스토리지 아티팩트용 서명 URL 헬퍼 (아티팩트 범용 — 특정 버킷·이미지 로직을 하드코딩하지 않는다).
// web `web/src/lib/storage/index.ts`의 클라측 미러(app 은 서버가 없어 클라측 발급이 유일 경로).
import 'package:supabase_flutter/supabase_flutter.dart';

import 'supabase_client.dart';

/// 서명 URL 유효기간(초). web `SIGNED_URL_TTL`의 미러 상수. 정본: docs/conventions.md §10.
const int kSignedUrlTtl = 3600;

/// 단건 서명 URL 발급. RLS 미통과·객체 미존재 등 실패 시 예외를 잡아 `null`을 반환한다
/// (소비처는 imageUrl null → "사진 준비중" 플레이스홀더를 그린다, docs/conventions.md §4).
Future<String?> getSignedUrl(
  String bucket,
  String path, {
  SupabaseClient? client,
}) async {
  final c = client ?? supabase;
  try {
    return await c.storage.from(bucket).createSignedUrl(path, kSignedUrlTtl);
  } catch (_) {
    return null;
  }
}

/// 배치 서명 URL 발급(NFR7 — N장을 N번 왕복하지 않고 1회 호출한다).
/// 반환 리스트는 입력 `paths` 순서를 보존하며, 항목별 실패는 `null`로 매핑한다.
Future<List<String?>> getSignedUrls(
  String bucket,
  List<String> paths, {
  SupabaseClient? client,
}) async {
  if (paths.isEmpty) return [];

  final c = client ?? supabase;
  try {
    final results = await c.storage
        .from(bucket)
        .createSignedUrlsResult(paths, kSignedUrlTtl);
    // Supabase는 요청 path를 그대로(byte-identical)·입력 순서대로 반향하므로 path 매칭이 안전하다
    // (storage-api signObjectUrls + storage_client 2.5.7 소스 실측, 9.2 리뷰 2026-07-18).
    final byPath = <String, String?>{
      for (final r in results)
        r.path: switch (r) {
          SignedUrlSuccess(:final signedUrl) => signedUrl,
          SignedUrlFailure() => null,
        },
    };
    return paths.map((path) => byPath[path]).toList();
  } catch (_) {
    return paths.map((_) => null).toList();
  }
}
