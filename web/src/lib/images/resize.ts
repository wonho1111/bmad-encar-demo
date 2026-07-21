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

/** 저장본 확장자·MIME. toBlob이 WebP를 못 만드는 환경에서는 JPEG로 폴백한다(아래 encodeWithFallback 참조). */
export const IMAGE_MIME = 'image/webp';

/** WebP를 못 만드는 브라우저에서 쓰는 대체 포맷(구형 Safari 등도 JPEG는 전부 인코딩할 수 있다). */
export const FALLBACK_MIME = 'image/jpeg';

/** 폴백 JPEG 품질. WebP q0.82와 비슷한 체감 화질이 나오는 값. */
export const FALLBACK_QUALITY = 0.85;

/** `canvas.toBlob`과 같은 모양의 함수 — 테스트에서 가짜를 넣을 수 있게 타입으로 뽑았다(#57). */
export type ToBlob = (
  callback: (blob: Blob | null) => void,
  type?: string,
  quality?: number,
) => void;

/**
 * WebP로 인코딩하고, 안 되면 JPEG로 폴백한다. **canvas 없이 단위테스트할 수 있게** `toBlob`을 주입받는다.
 *
 * ⚠️ **왜 `blob !== null`이 아니라 `blob.type`을 보는가 (#57, 2026-07-19 실측):**
 *   원래 코드는 "미지원 MIME이면 toBlob이 null을 준다"는 전제로 폴백을 짰다. **그 전제가 틀렸다.**
 *   HeadlessChrome 151에서 직접 재본 결과, 미지원 MIME(`image/tiff`·`image/avif`·엉터리 문자열)에
 *   toBlob은 null이 아니라 **PNG**를 돌려준다(매직넘버 `89 50 4e 47` 확인, blob.type='image/png').
 *   그래서 WebP 미지원 브라우저에서는 **폴백 분기가 아예 실행되지 않고** PNG가 그대로 저장됐다:
 *     · `extensionFor`가 `.jpg` 이름을 붙여 **확장자와 내용이 어긋난다**
 *     · 1600×1067 실측에서 WebP 553KB / JPEG 503KB인데 **PNG는 4,827KB(약 9배)** — 버킷 5MB 상한에 닿고
 *       AC4의 저장본 규격 보장이 깨진다
 *   요청한 타입이 그대로 나왔는지를 확인하면 null을 주는 브라우저와 PNG를 주는 브라우저를 **둘 다** 잡는다.
 */
/** `toBlob`이 콜백을 영영 안 부르는 경우(저사양 모바일에서 대용량 canvas OOM·오염된 canvas 등)에
 *  대비한 상한. 없으면 Promise가 영원히 pending이라 아무것도 throw하지 않고, 순차 업로드 루프
 *  전체가 멈추는데도 기존 try/catch가 반응하지 않는다(코드리뷰 2026-07-19). */
const ENCODE_TIMEOUT_MS = 30_000;

/** 인코딩 Promise를 타임아웃과 경주시킨다. 성공하면 타이머를 반드시 지운다(안 지우면 다음 페이지
 *  이동 후에도 타이머가 남는다 — dangling timer). */
function withTimeout(promise: Promise<Blob | null>): Promise<Blob | null> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('이미지 변환이 너무 오래 걸려요. 다시 시도해주세요.'));
    }, ENCODE_TIMEOUT_MS);
    promise.then(
      (blob) => {
        clearTimeout(timer);
        resolve(blob);
      },
      (err) => {
        clearTimeout(timer);
        reject(err);
      },
    );
  });
}

export async function encodeWithFallback(toBlob: ToBlob): Promise<Blob> {
  const encode = (mime: string, quality: number) =>
    withTimeout(new Promise<Blob | null>((resolve) => toBlob(resolve, mime, quality)));

  const webp = await encode(IMAGE_MIME, IMAGE_QUALITY);
  if (webp && webp.type === IMAGE_MIME) return webp;

  const jpeg = await encode(FALLBACK_MIME, FALLBACK_QUALITY);
  if (jpeg && jpeg.type === FALLBACK_MIME) return jpeg;

  // WebP도 JPEG도 못 만드는 브라우저 — 여기서 규격 밖 파일을 조용히 저장하느니 실패를 알린다.
  // 호출부(PhotoUploader)가 그 사진 항목만 인라인 오류로 표시하고 폼 제출은 막지 않는다(AC3).
  throw new Error('이미지를 변환하지 못했습니다');
}

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

    // 인코딩·폴백 판정은 encodeWithFallback이 전담한다(canvas 없이 단위테스트되는 유일한 지점, #57).
    return await encodeWithFallback(canvas.toBlob.bind(canvas));
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
