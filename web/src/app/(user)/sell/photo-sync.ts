// 매물 사진을 화면 상태 → DB·Storage에 반영한다 (AC3·AC5·AC6·AC8·AC9·AC10).
// 브라우저 전용(SellForm 제출 시점에 호출).
//
// 등록과 수정이 **같은 함수**를 탄다. 등록은 "기존 사진이 0장인 수정"과 정확히 같기 때문이다
// — 분기를 두면 한쪽만 고치는 버그가 생긴다.
//
// 지켜야 하는 순서가 두 개 있고, 둘 다 실측에서 나온 것이다:
//   ① **삭제: Storage 오브젝트 먼저 → listing_images 행 나중** (Task 0 실측, tech-debt #51)
//      행을 먼저 지우면 읽기 정책(행 조인 의존)이 객체를 숨겨 소유자도 못 지우는 고아가 된다.
//   ② **대표 기록: 매물 전체 is_cover=false → 대상 1장만 true** (도커 실측, #47-1)
//      부분 유니크 인덱스(listing_images_one_cover_per_listing)는 DEFERRABLE이 아니라서
//      단일 UPDATE로 뒤집으면 문장 중간에 대표가 2장이 되는 순간 duplicate key로 죽는다.
import { createClient } from '@/lib/supabase/client';
import { resizeImage, extensionFor } from '@/lib/images/resize';
import { deleteListingImageObject, uploadListingImage } from '@/lib/storage/upload';
import type { PhotoItem } from './photo-item';

export type PhotoSyncResult = {
  /** 화면에 되돌려줄 항목들(실패한 것은 status:'error'로 표시돼 있다 — AC3). */
  photos: PhotoItem[];
  /** 이번에 새로 저장된 장수. */
  savedCount: number;
  /** 실패한 장수(폼 제출 자체는 막지 않는다 — AC3). */
  failedCount: number;
};

/** 저장 파일명 — uuid라 충돌이 없다(그래서 upsert가 필요 없다, upload.ts 주석 참조). */
function newFilename(ext: string): string {
  return `${crypto.randomUUID()}.${ext}`;
}

export async function syncListingPhotos(
  userId: string,
  listingId: string,
  photos: PhotoItem[],
  initialPhotos: PhotoItem[],
): Promise<PhotoSyncResult> {
  const supabase = createClient();

  // ── 1) 삭제 — 화면에서 사라진 기존 사진 ────────────────────────────────
  const keptRowIds = new Set(photos.map((p) => p.rowId).filter(Boolean));
  for (const gone of initialPhotos.filter((p) => p.rowId && !keptRowIds.has(p.rowId))) {
    // ⚠️ 순서 ① — 오브젝트 먼저. 반대로 하면 영구 고아가 된다(위 주석).
    if (gone.storagePath) await deleteListingImageObject(gone.storagePath);
    const { error } = await supabase.from('listing_images').delete().eq('id', gone.rowId!);
    if (error) console.error('[sell] listing_images 행 삭제 실패:', gone.rowId, error);
  }

  // ── 2) 업로드 — 새로 고른 사진을 화면 순서대로 **순차** 처리 ───────────
  // 순차인 이유(AC9): 10장 상한 트리거가 count-후-insert라 동시 삽입이 경합하면 새는 것이
  // 코드상 명백하다(#49). 병렬로 올리면 빠르지만 그 경합을 우리가 직접 만들게 된다.
  const next: PhotoItem[] = [];
  let failedCount = 0;

  for (const p of photos) {
    // 이미 저장된 사진(기존 행)이거나, 되살릴 수 없는 검증 실패 항목은 업로드 대상이 아니다.
    if (p.storagePath) {
      next.push(p);
      continue;
    }
    if (!p.file || (p.status === 'error' && p.retryable === false)) {
      failedCount += 1;
      next.push({ ...p, status: 'error', error: p.error ?? '이 사진은 저장하지 못했어요.' });
      continue;
    }

    try {
      const blob = await resizeImage(p.file);
      const result = await uploadListingImage(userId, listingId, newFilename(extensionFor(blob)), blob);
      if (result.ok) {
        next.push({ ...p, status: 'uploaded', storagePath: result.storagePath, error: undefined });
      } else {
        failedCount += 1;
        next.push({ ...p, status: 'error', error: result.reason, retryable: true });
      }
    } catch (err) {
      console.error('[sell] 사진 변환/업로드 예외:', err);
      failedCount += 1;
      next.push({ ...p, status: 'error', error: '사진을 처리하지 못했어요. 다시 시도해주세요.', retryable: true });
    }
  }

  // ── 3) 행 기록 — **업로드가 실제 성공한 사진만** 행을 만든다(AC6) ───────
  // 화면 순서를 그대로 연속 정수 sort_order(0..n-1)로 매긴다. 구멍을 남기지 않는 이유:
  // sort_order에 tie-break가 정의돼 있지 않아(#47-2) 값이 겹치면 조회 순서가 매 쿼리 달라진다.
  const saved = next.filter((p) => p.storagePath);
  let savedCount = 0;

  for (let i = 0; i < saved.length; i += 1) {
    const p = saved[i];
    if (p.rowId) {
      // 기존 행 — 순서만 다시 매긴다. is_cover는 여기서 건드리지 않는다(4단계에서 한 번에).
      const { error } = await supabase.from('listing_images').update({ sort_order: i }).eq('id', p.rowId);
      if (error) console.error('[sell] sort_order 갱신 실패:', p.rowId, error);
      continue;
    }
    // 새 행 — is_cover는 항상 false로 넣는다. 대표 지정은 4단계가 전담한다(부분 유니크 인덱스 충돌 회피).
    const { data, error } = await supabase
      .from('listing_images')
      .insert({ listing_id: listingId, storage_path: p.storagePath, sort_order: i, is_cover: false })
      .select('id')
      .single();

    if (error || !data) {
      console.error('[sell] listing_images INSERT 실패:', p.storagePath, error);
      // 행이 없으면 그 오브젝트는 아무도 못 읽는 고아가 된다(#46) → 즉시 정리를 시도한다.
      // ⚠️ 이 시점엔 행이 없어서 오브젝트가 안 보이므로(Task 0 실측) 이 정리는 실패할 수 있다.
      //    "정리했다"가 아니라 "시도했고 결과는 이렇다"로 남긴다.
      const cleaned = await deleteListingImageObject(p.storagePath!);
      console.error('[sell] 고아 오브젝트 정리 시도:', p.storagePath, cleaned ? '성공' : '실패(고아 잔존)');

      const idx = next.indexOf(p);
      if (idx >= 0) next[idx] = { ...p, status: 'error', error: '사진 정보를 저장하지 못했어요.', retryable: true, storagePath: undefined };
      failedCount += 1;
      continue;
    }
    savedCount += 1;
  }

  // ── 4) 대표 기록 — **반드시 2문장**(AC8) ────────────────────────────────
  // 이 매물 전체를 false로 내린 뒤 0번 1장만 true로 올린다. 한 문장으로 뒤집으면
  // 부분 유니크 인덱스에 걸려 duplicate key로 죽는다(실측, #47-1).
  const survivors = next.filter((p) => p.storagePath);
  {
    const { error } = await supabase.from('listing_images').update({ is_cover: false }).eq('listing_id', listingId);
    if (error) console.error('[sell] is_cover 초기화 실패:', error);
  }
  if (survivors.length > 0) {
    const { error } = await supabase
      .from('listing_images')
      .update({ is_cover: true })
      .eq('listing_id', listingId)
      .eq('storage_path', survivors[0].storagePath!);
    if (error) console.error('[sell] 대표 지정 실패:', error);
  }

  return { photos: next, savedCount, failedCount };
}
