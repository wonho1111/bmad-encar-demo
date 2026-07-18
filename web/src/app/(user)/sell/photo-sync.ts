'use client';

// 매물 사진을 화면 상태 → DB·Storage에 반영한다 (AC3·AC5·AC6·AC8·AC9·AC10).
// 브라우저 전용(SellForm 제출 시점에 호출) — 상단 'use client'가 실제로 그걸 강제한다.
// (전엔 주석으로만 "브라우저 전용"이라 적혀 있고 지시자가 없었다. toPhotoItems가 정확히 같은
//  종류의 실수로 런타임 500을 냈던 적이 있다 — photo-item.ts 주석 참조. 코드리뷰 2026-07-19.)
//
// 등록과 수정이 **같은 함수**를 탄다. 등록은 "기존 사진이 0장인 수정"과 정확히 같기 때문이다
// — 분기를 두면 한쪽만 고치는 버그가 생긴다.
//
// 지켜야 하는 순서가 두 개 있고, 둘 다 실측에서 나온 것이다:
//   ① **삭제: Storage 오브젝트 먼저 → listing_images 행 나중** (Task 0 실측, tech-debt #51)
//      행을 먼저 지우면 읽기 정책(행 조인 의존)이 객체를 숨겨 소유자도 못 지우는 고아가 된다.
//      ⚠️ 오브젝트 삭제가 실패하면 행도 지우지 않는다 — 행만 지우면 정확히 그 고아가 만들어진다.
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
  /** 행 삭제·sort_order 갱신·대표 지정처럼 "저장은 됐지만 뒷정리가 어긋난" 조용한 실패의 한국어 사유.
   *  failedCount와 별개다 — 사진 자체는 저장됐으므로 재제출을 막을 이유는 아니지만, 화면과 DB가
   *  갈라진 채로 "성공"이라고만 말하면 안 되기 때문에 둔다(코드리뷰 2026-07-19). */
  warnings: string[];
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

  const next: PhotoItem[] = [];
  let failedCount = 0;
  const warnings: string[] = [];

  // ── 1) 삭제 — 화면에서 사라진 기존 사진 ────────────────────────────────
  const keptRowIds = new Set(photos.map((p) => p.rowId).filter(Boolean));
  for (const gone of initialPhotos.filter((p) => p.rowId && !keptRowIds.has(p.rowId))) {
    // ⚠️ 순서 ① — 오브젝트 먼저. 반대로 하면 영구 고아가 된다(위 주석).
    const objectDeleted = gone.storagePath ? await deleteListingImageObject(gone.storagePath) : true;
    if (!objectDeleted) {
      // 오브젝트가 안 지워졌는데 행을 지우면, 그 오브젝트는 읽기 정책(행 조인 의존) 때문에
      // 소유자에게도 영영 안 보이는 고아가 된다(#46) — 그래서 행 삭제를 건너뛰고 실패로 남긴다.
      console.error('[sell] 사진 오브젝트 삭제 실패 — 고아 방지를 위해 행은 지우지 않음:', gone.storagePath);
      warnings.push('사진을 삭제하지 못했어요. 다시 시도해주세요.');
      failedCount += 1;
      next.push({ ...gone, status: 'error', error: '사진을 삭제하지 못했어요. 다시 시도해주세요.', retryable: false });
      continue;
    }
    const { error } = await supabase.from('listing_images').delete().eq('id', gone.rowId!);
    if (error) {
      console.error('[sell] listing_images 행 삭제 실패:', gone.rowId, error);
      warnings.push('사진 삭제 정보를 정리하지 못했어요.');
    }
  }

  // ── 2) 업로드 — 새로 고른 사진을 화면 순서대로 **순차** 처리 ───────────
  // 순차인 이유(AC9): 10장 상한 트리거가 count-후-insert라 동시 삽입이 경합하면 새는 것이
  // 코드상 명백하다(#49). 병렬로 올리면 빠르지만 그 경합을 우리가 직접 만들게 된다.
  for (const p of photos) {
    // 이미 저장된 사진(기존 행)은 업로드 대상이 아니다.
    if (p.storagePath) {
      next.push(p);
      continue;
    }
    // 검증 실패(용량초과·포맷거부) 항목 — 애초에 업로드된 적이 없고 다시 시도해도 결과가
    // 같다(retryable:false). 목록엔 남기되(AC3), **이번 실행이 만든 실패가 아니므로** 세지
    // 않는다 — 안 세면 매번 재제출 때마다 failedCount가 이 항목으로 채워져 이동이 영구히
    // 막히던 문제가 사라진다(코드리뷰 2026-07-19).
    if (p.status === 'error' && p.retryable === false) {
      next.push(p);
      continue;
    }
    if (!p.file) {
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
  // sort_order는 화면 인덱스가 아니라 **실제로 저장(갱신)에 성공한 개수**로 매긴다 — 화면
  // 인덱스를 그대로 쓰면 중간 항목의 실패가 뒤 항목의 번호를 당겨주지 않아 구멍이 남고,
  // 대표(=0번)가 엉뚱한 행에 붙는다(코드리뷰 2026-07-19). 실패하면 카운터를 올리지 않아
  // 다음 생존 항목이 그 자리를 그대로 메운다.
  const saved = next.filter((p) => p.storagePath);
  let savedCount = 0;
  let order = 0;

  for (const p of saved) {
    if (p.rowId) {
      // 기존 행 — 순서만 다시 매긴다. is_cover는 여기서 건드리지 않는다(4단계에서 한 번에).
      // .select('id')로 실제 갱신된 행 수를 본다 — 다른 세션이 먼저 지운 행이면 error는 null이지만
      // 0행이라 "성공"이 아니다(SellForm.tsx의 listings UPDATE와 같은 패턴).
      const { data, error } = await supabase
        .from('listing_images')
        .update({ sort_order: order })
        .eq('id', p.rowId)
        .select('id');
      if (error || !data || data.length === 0) {
        console.error('[sell] sort_order 갱신 실패:', p.rowId, error);
        warnings.push('사진 순서를 저장하지 못한 항목이 있어요.');
        continue; // 카운터를 올리지 않는다 — 구멍 방지.
      }
      order += 1;
      continue;
    }
    // 새 행 — is_cover는 항상 false로 넣는다. 대표 지정은 4단계가 전담한다(부분 유니크 인덱스 충돌 회피).
    const { data, error } = await supabase
      .from('listing_images')
      .insert({ listing_id: listingId, storage_path: p.storagePath, sort_order: order, is_cover: false })
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
      continue; // 카운터를 올리지 않는다 — 구멍 방지.
    }
    savedCount += 1;
    order += 1;
    // INSERT 성공 시 rowId를 화면 상태에 되돌려준다 — 안 하면 재제출 때 이 항목이 "기존 행"으로
    // 인식되지 않아 같은 storage_path로 재INSERT를 시도하고, unique 위반 → 실패 분기가 방금
    // 저장한 오브젝트를 지운다(역고아, 코드리뷰 2026-07-19 발견).
    const idx = next.indexOf(p);
    if (idx >= 0) next[idx] = { ...p, rowId: data.id };
  }

  // ── 4) 대표 기록 — **반드시 2문장**(AC8) ────────────────────────────────
  // 이 매물 전체를 false로 내린 뒤 0번 1장만 true로 올린다. 한 문장으로 뒤집으면
  // 부분 유니크 인덱스에 걸려 duplicate key로 죽는다(실측, #47-1).
  // survivors[0]은 3단계에서 sort_order=0을 실제로 받은 행과 항상 일치한다 — 실패한 항목은
  // storagePath가 비워져(위) 이 필터에서 이미 빠지기 때문이다.
  const survivors = next.filter((p) => p.storagePath);
  const { error: resetError } = await supabase.from('listing_images').update({ is_cover: false }).eq('listing_id', listingId);
  if (resetError) {
    console.error('[sell] is_cover 초기화 실패:', resetError);
    warnings.push('대표 사진 정보를 정리하지 못했어요.');
    // ⚠️ 리셋이 실패하면 다음 문장(true 지정)을 아예 쏘지 않는다 — 부분 유니크 인덱스에 걸려
    // 어차피 실패하고, 조용히 "대표 0장" 상태만 남기 때문이다(코드리뷰 2026-07-19).
  } else if (survivors.length > 0) {
    const { error: setError } = await supabase
      .from('listing_images')
      .update({ is_cover: true })
      .eq('listing_id', listingId)
      .eq('storage_path', survivors[0].storagePath!);
    if (setError) {
      console.error('[sell] 대표 지정 실패:', setError);
      warnings.push('대표 사진을 지정하지 못했어요.');
    }
  }

  // 같은 사유가 사진 수만큼 쌓이므로 중복을 없앤다 — SellForm이 ' · '로 이어 붙여 보여주기 때문에
  // 안 없애면 "순서를 저장하지 못했어요 · 순서를 저장하지 못했어요 · …"가 그대로 사용자에게 간다.
  return { photos: next, savedCount, failedCount, warnings: [...new Set(warnings)] };
}
