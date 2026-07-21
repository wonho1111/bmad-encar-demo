// 공개 스토리지 아티팩트용 URL 헬퍼 (아티팩트 범용 — 특정 버킷·이미지 로직을 하드코딩하지 않는다).
// web `web/src/lib/storage/index.ts`의 미러.
//
// Story 9.0 전까지는 비공개 버킷 + 서명 URL이었다(발급 왕복·1시간 만료·실패 시 null).
// 공개 버킷으로 바뀌면서 URL은 경로에서 바로 조립된다 — 네트워크 왕복도, 만료도, 실패도 없다.
import 'supabase_client.dart';

/// 공개 버킷 오브젝트의 고정 URL을 만든다.
///
/// ⚠️ 파일이 실제로 있는지 확인하지 않는다 — 경로만 있으면 문자열이 나온다.
/// 없는 파일은 이미지 로드가 실패하므로, 소비처가 `errorBuilder`로 "사진 준비중"을 그려야 한다
/// (docs/conventions.md §4).
String getPublicUrl(String bucket, String path) {
  return supabase.storage.from(bucket).getPublicUrl(path);
}
