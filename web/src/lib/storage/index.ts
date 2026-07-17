// 비공개 스토리지 아티팩트용 서명 URL 헬퍼 (아티팩트 범용 — 특정 버킷·이미지 로직을 하드코딩하지 않는다).
// ⚠️ server components·route handlers·server actions에서만 호출한다(서버 클라이언트를 사용하므로
// 브라우저 번들에 포함되면 안 된다). app(Flutter)의 클라측 미러는 core/supabase/storage_helper.dart.
import { createClient } from '@/lib/supabase/server';

/** 서명 URL 유효기간(초). 정본: docs/conventions.md §10. 호출부에서 3600을 다시 쓰지 않는다. */
export const SIGNED_URL_TTL = 3600 as const;

/**
 * 단건 서명 URL 발급. RLS 미통과·객체 미존재 등 실패 시 throw하지 않고 `null`을 반환한다
 * (소비처는 image_url null → "사진 준비중" 플레이스홀더를 그린다, docs/conventions.md §4).
 */
export async function getSignedUrl(bucket: string, path: string): Promise<string | null> {
  const supabase = await createClient();
  const { data, error } = await supabase.storage.from(bucket).createSignedUrl(path, SIGNED_URL_TTL);
  if (error || !data) return null;
  return data.signedUrl;
}

/**
 * 배치 서명 URL 발급(NFR7 — 카드 N장을 N번 왕복하지 않고 1회 호출한다).
 * 반환 배열은 입력 `paths` 순서를 보존하며, 항목별 실패는 `null`로 매핑한다.
 */
export async function getSignedUrls(bucket: string, paths: string[]): Promise<(string | null)[]> {
  if (paths.length === 0) return [];

  const supabase = await createClient();
  const { data, error } = await supabase.storage.from(bucket).createSignedUrls(paths, SIGNED_URL_TTL);
  if (error || !data) return paths.map(() => null);

  // Supabase는 요청 path를 그대로(byte-identical)·입력 순서대로 반향하므로 path 매칭이 안전하다
  // (storage-api signObjectUrls + storage-js 2.108.2 소스 실측, 9.2 리뷰 2026-07-18).
  const byPath = new Map(data.map((item) => [item.path, item.signedUrl ?? null]));
  return paths.map((path) => byPath.get(path) ?? null);
}
