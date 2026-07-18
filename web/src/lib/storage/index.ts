// 공개 스토리지 아티팩트용 URL 헬퍼 (아티팩트 범용 — 특정 버킷·이미지 로직을 하드코딩하지 않는다).
//
// 서버/브라우저 어디서든 호출된다 — Supabase 클라이언트도, 네트워크 왕복도 필요 없다.
// (Story 9.0 전까지는 비공개 버킷 + 서명 URL이라 "서버에서만 발급 가능"했다. 그 제약은 사라졌다.)
// app(Flutter)의 미러는 core/supabase/storage_helper.dart.
import { getSupabaseEnv } from '@/lib/supabase/env';

/**
 * 공개 버킷 오브젝트의 고정 URL을 만든다.
 *
 * ⚠️ 이 함수는 **파일이 실제로 있는지 확인하지 않는다** — 경로만 있으면 문자열이 나온다.
 * 없는 파일은 브라우저가 로드에 실패하므로, 소비처가 `onError`로 "사진 준비중" 플레이스홀더를
 * 그려야 한다(docs/conventions.md §4).
 */
export function getPublicUrl(bucket: string, path: string): string {
  const { url } = getSupabaseEnv();
  return `${url}/storage/v1/object/public/${encodeSegments(bucket)}/${encodeSegments(path)}`;
}

/**
 * 경로를 `/` 구분자는 살린 채 세그먼트별로 URL 인코딩한다.
 *
 * 왜 세그먼트별인가: `encodeURIComponent`를 경로 전체에 걸면 `/`까지 `%2F`가 되어 경로가 깨진다.
 * 지금 파일명은 uuid라 인코딩할 것이 없지만, 이 헬퍼는 아티팩트 범용이라 공백·한글 파일명이
 * 들어와도 안전해야 한다.
 */
function encodeSegments(pathLike: string): string {
  return pathLike.split('/').map(encodeURIComponent).join('/');
}
