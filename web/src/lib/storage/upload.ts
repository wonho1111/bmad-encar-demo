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
 * **반환값의 뜻은 "지웠다"가 아니라 "오브젝트가 이제 없다"** 이다. 둘은 다르다 — 이미 없던
 * 파일도 "없다"는 목적을 만족하고, 호출부가 알고 싶은 건 그것이기 때문이다.
 *
 * ⚠️ **전제(계약): 이 함수는 해당 `listing_images` 행이 아직 살아 있는 동안 불러야 한다.**
 * 그래야 아래 해석이 참이 된다. 그리고 그 전제는 삭제 순서 계약과 같은 것이다 —
 * 오브젝트 먼저, 행은 나중(docs/conventions.md §10.1).
 *
 * ── 원격 실측 (2026-07-19, 코드리뷰 2차) ──────────────────────────────────
 *   A. 행 없음 + 파일 없음 → error=null, data=[]        ← RLS에 가려진 경우
 *   B. 행 있음 + 파일 없음 → error=null, data=[]        ← 파일이 진짜 없는 경우
 *   C. 행 있음 + 파일 있음 → error=null, data=[그 경로]  ← 정상 삭제
 * A와 B의 응답은 **글자 그대로 같아서 응답만으로는 구별할 수 없다.** 그러나 C가 "행이 있으면
 * 있는 파일은 실제로 지워진다"를 증명하므로, **전제(행 있음)가 지켜지면 빈 배열 = 파일 없음**이다.
 *
 * 전엔 빈 배열을 `false`(실패)로 돌려줬다. 그 결과 파일 없는 고아 행이 하나라도 있으면 매물
 * 삭제가 **재시도해도 결정론적으로** 막혔고 앱 안에 탈출구가 없었다(코드리뷰 2차).
 * 강제 장치: `web/src/lib/storage/upload.test.ts`.
 *
 * 원격 실측(2026-07-18, Task 0)이 밝힌 삭제 순서의 근거는 그대로다: storage.objects의 유일한
 * SELECT 정책은 listing_images 행과 storage_path로 조인해야 참이 되고, Storage API의 DELETE는
 * 대상을 먼저 SELECT로 찾는다 → 행을 먼저 지우면 **영구 고아**가 된다(#46·#51).
 */
export async function deleteListingImageObject(storagePath: string): Promise<boolean> {
  const supabase = createClient();
  const { data, error } = await supabase.storage.from(LISTING_IMAGES_BUCKET).remove([storagePath]);

  if (error) {
    console.error('[sell] 사진 오브젝트 삭제 실패:', storagePath, error);
    return false;
  }
  // data가 아예 없으면(null) 무슨 일이 일어났는지 모르는 상태다 — 모르는 것을 성공으로 갈음하지 않는다.
  if (!Array.isArray(data)) {
    console.error('[sell] 사진 오브젝트 삭제 — 응답을 해석할 수 없음:', storagePath, data);
    return false;
  }
  if (data.length === 0) {
    // 위 실측 B — 전제가 지켜졌다면 파일이 원래 없었다는 뜻이고, 목적은 이미 달성돼 있다.
    console.warn('[sell] 사진 오브젝트가 이미 없음(목적 달성):', storagePath);
  }
  return true;
}
