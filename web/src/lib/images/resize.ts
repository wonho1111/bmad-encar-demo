// 업로드 전 클라이언트 다운스케일·압축 (AC4) — 브라우저 네이티브 canvas만 쓴다(새 의존성 0개).
//
// 왜 필요한가: app(Flutter)은 저장된 **원본**을 그대로 받는다(ADR-IMG-02). 5MB짜리를 그대로
// 올려두면 목록에서 여러 장 다운로드할 때 NFR7(응답 시간)이 깨진다. 그래서 저장하는 순간
// 카드·갤러리에 충분한 크기로 줄여서 올린다. 원본 5MB 상한(validate.ts)과는 별개 장치다.
//
// 저장본 규격의 정본은 docs/conventions.md §10 — 아래 상수는 그 계약을 코드로 옮긴 것이다.

/** 저장본의 긴 변 상한(px). 상세 갤러리(9.5)가 대표 사진을 크게 쓰는 것을 견디는 크기. */
export const MAX_IMAGE_EDGE = 1600;

/** WebP 인코딩 품질. 같은 화질에서 JPEG보다 작다(버킷 MIME 화이트리스트에 이미 포함). */
export const IMAGE_QUALITY = 0.82;

/** 저장본 확장자·MIME. toBlob이 WebP를 못 만드는 환경에서는 JPEG로 폴백한다(아래 resizeImage 참조). */
export const IMAGE_MIME = 'image/webp';

/**
 * 원본 크기 → 저장본 크기. **순수 함수라 단위테스트 대상이다**(resize.test.ts).
 * 긴 변을 MAX_IMAGE_EDGE에 맞추고 비율을 유지한다. 상한 이하면 억지로 키우지 않는다.
 */
export function computeTargetSize(width: number, height: number): { width: number; height: number } {
  const longest = Math.max(width, height);
  if (longest <= MAX_IMAGE_EDGE) return { width, height };

  const scale = MAX_IMAGE_EDGE / longest;
  return {
    // canvas는 소수 픽셀을 받지 못하므로 반올림한다. 극단 비율(예: 8000×1)에서 짧은 변이
    // 0으로 내려가면 canvas가 빈 이미지를 만들므로 최소 1px을 보장한다.
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

/**
 * 이미지 파일을 저장본 규격(긴 변 ≤1600px · WebP · quality 0.82)으로 다시 인코딩한다.
 * 브라우저 전용 — createImageBitmap·canvas를 쓰므로 서버에서 호출하지 않는다.
 *
 * 실패(디코딩 불가·toBlob null)는 throw한다 — 호출부(PhotoUploader)가 그 사진 항목만
 * 인라인 오류로 표시하고 폼 제출은 막지 않는다(AC3).
 */
export async function resizeImage(file: File): Promise<Blob> {
  // imageOrientation:'from-image' — EXIF Orientation(폰 세로사진에 흔한 6/8)을 반영해 디코딩한다.
  // 없으면 90° 돌아간 채로 재인코딩되고(가로/세로가 뒤바뀌어 리사이즈 비율까지 어긋난다), 재인코딩이라
  // 원본 EXIF가 사라져 되돌릴 수 없다(코드리뷰 2026-07-19).
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  try {
    const { width, height } = computeTargetSize(bitmap.width, bitmap.height);

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas 2d 컨텍스트를 만들 수 없습니다');
    ctx.drawImage(bitmap, 0, 0, width, height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, IMAGE_MIME, IMAGE_QUALITY),
    );
    if (blob) return blob;

    // toBlob은 지원하지 않는 MIME에 대해 **에러 대신 null**을 준다(사양). WebP를 못 만드는
    // 환경이면 JPEG로 한 번 더 시도한다 — 여기서 포기하면 그 브라우저는 업로드 자체가 막힌다.
    const fallback = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.85),
    );
    if (!fallback) throw new Error('이미지를 변환하지 못했습니다');
    return fallback;
  } finally {
    // ImageBitmap은 GC 대상이 아니라 명시적으로 놓아줘야 메모리가 회수된다.
    // 10장을 연속 처리하므로 누락하면 모바일에서 눈에 띈다.
    bitmap.close();
  }
}

/** 저장본 Blob의 실제 타입에 맞는 확장자. 파일명 생성(=storage key)에 쓴다. */
export function extensionFor(blob: Blob): string {
  return blob.type === 'image/webp' ? 'webp' : 'jpg';
}
