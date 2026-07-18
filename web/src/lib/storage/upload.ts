// 매물 사진 업로드·삭제 — **브라우저 전용** (AC5·AC10).
//
// ⚠️ 같은 폴더의 index.ts(서명 URL)와 파일을 나눈 이유: index.ts는 서버 클라이언트를 import하므로
// 한 파일에 합치면 서버 전용 코드가 브라우저 번들에 딸려간다. 여기는 anon key + Storage RLS로
// 브라우저에서 돈다(SellForm이 이미 브라우저 클라이언트로 insert하는 것과 같은 층).
// service_role은 쓰지 않는다(docs/conventions.md §5).
import { createClient } from '@/lib/supabase/client';
import { LISTING_IMAGES_BUCKET } from './bucket';

/**
 * 경로 규약 `{user_id}/{listing_id}/{filename}` (9.1). 첫 세그먼트가 소유자라는 것을
 * Storage RLS가 검사하고, listing_images 행 쪽은 0013 트리거가 같은 규약을 강제한다.
 * 파일명은 uuid라 충돌이 없다 — 그래서 upsert가 필요 없다(아래 uploadListingImage 주석 참조).
 */
export function buildStoragePath(userId: string, listingId: string, filename: string): string {
  return `${userId}/${listingId}/${filename}`;
}

export type UploadResult =
  | { ok: true; storagePath: string }
  | { ok: false; reason: string };

/**
 * 저장본 Blob 1장을 업로드한다. 실패는 throw하지 않고 사유를 돌려준다 —
 * 사진 1장의 실패가 폼 제출을 막으면 안 되기 때문이다(AC3).
 */
export async function uploadListingImage(
  userId: string,
  listingId: string,
  filename: string,
  blob: Blob,
): Promise<UploadResult> {
  const storagePath = buildStoragePath(userId, listingId, filename);
  const supabase = createClient();

  // ⚠️ upsert를 쓰지 않는다(기본값 false 유지). 원격 실측(2026-07-18, Story 9.3 Task 0):
  //   x-upsert:true는 같은 토큰·같은 경로에서도 403 "new row violates row-level security policy"로
  //   막힌다 — 업서트가 존재확인 SELECT를 거치는데, 그 SELECT가 listing_images 행에 의존하는
  //   읽기 정책에 걸리기 때문이다(docs/tech-debt.md #51). 파일명이 uuid라 덮어쓸 일도 없다.
  const { error } = await supabase.storage.from(LISTING_IMAGES_BUCKET).upload(storagePath, blob, {
    contentType: blob.type,
  });

  if (error) {
    console.error('[sell] 사진 업로드 실패:', storagePath, error);
    return { ok: false, reason: '사진을 올리지 못했어요. 다시 시도해주세요.' };
  }
  return { ok: true, storagePath };
}

/**
 * Storage 오브젝트 1개를 지운다.
 *
 * ⚠️ **호출 순서가 계약이다: 이 함수를 먼저 부르고, 그 다음에 listing_images 행을 지운다.**
 * 원격 실측(2026-07-18, Task 0): storage.objects의 유일한 SELECT 정책은 listing_images 행과
 * storage_path로 조인해야 참이 되고, Storage API의 DELETE는 대상을 먼저 SELECT로 찾는다.
 * → 행을 먼저 지우면 객체가 소유자에게도 안 보이게 되어 **영구 고아**가 된다(#46·#51).
 */
export async function deleteListingImageObject(storagePath: string): Promise<boolean> {
  const supabase = createClient();
  const { data, error } = await supabase.storage.from(LISTING_IMAGES_BUCKET).remove([storagePath]);

  if (error) {
    console.error('[sell] 사진 오브젝트 삭제 실패:', storagePath, error);
    return false;
  }
  // remove()는 매치 0건이어도 에러 없이 빈 배열을 준다(조용한 실패 — Task 0에서 실측).
  // "에러 없음"을 성공으로 갈음하지 않는다.
  return Array.isArray(data) && data.length > 0;
}
