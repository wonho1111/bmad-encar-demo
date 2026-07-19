// 저장본 규격 계산 테스트 (AC4).
// resizeImage 자체는 canvas(브라우저 API)를 쓰므로 node 환경에서 돌릴 수 없다.
// 그래서 **크기 계산만** 순수 함수로 떼어내 여기서 검증한다 — 나머지(실제 인코딩)는
// Task 6에서 "원본 바이트 vs 저장본 바이트"를 실측해 증명한다.
//
// **이 검사가 안 보는 것:**
//  · 실제 인코딩(WebP·quality 0.82)이 되는지, 파일이 **정말 작아지는지** — canvas가 없어
//    여기서 못 본다. Task 6에서 원본/저장본 바이트를 실측해 증명한다.
//  · 실제 canvas·createImageBitmap 연결(resizeImage 본체) — 여전히 node에서 못 본다.
//  · **폴백 경로는 이제 본다**(#57): toBlob을 주입받는 encodeWithFallback을 아래에서 직접 태운다.
//    단 "구형 Safari가 정말 이렇게 동작하는가"는 여기서 증명되지 않는다 — 이 검사가 고정하는 것은
//    "요청한 타입이 안 나오면 JPEG로 간다"는 우리 쪽 규칙이다.
import { describe, it, expect, vi } from 'vitest';
import {
  computeTargetSize,
  encodeWithFallback,
  extensionFor,
  MAX_IMAGE_EDGE,
  IMAGE_MIME,
  FALLBACK_MIME,
  type ToBlob,
} from './resize';

describe('computeTargetSize', () => {
  it('긴 변이 상한 이하면 원본 크기를 그대로 쓴다 (억지로 키우지 않는다)', () => {
    expect(computeTargetSize(800, 600)).toEqual({ width: 800, height: 600 });
  });

  it('긴 변이 정확히 상한이면 그대로다 (경계 포함)', () => {
    expect(computeTargetSize(MAX_IMAGE_EDGE, 900)).toEqual({ width: MAX_IMAGE_EDGE, height: 900 });
  });

  it('가로가 길면 가로를 상한에 맞추고 비율을 유지한다', () => {
    expect(computeTargetSize(3200, 1600)).toEqual({ width: MAX_IMAGE_EDGE, height: MAX_IMAGE_EDGE / 2 });
  });

  it('세로가 길면 세로를 상한에 맞춘다', () => {
    expect(computeTargetSize(1200, 4800)).toEqual({ width: 400, height: MAX_IMAGE_EDGE });
  });

  it('비율 계산 결과는 정수로 반올림한다 (canvas는 소수 픽셀을 못 받는다)', () => {
    const { width, height } = computeTargetSize(4001, 3000);
    expect(Number.isInteger(width)).toBe(true);
    expect(Number.isInteger(height)).toBe(true);
    expect(width).toBe(MAX_IMAGE_EDGE);
  });

  it('한 변이 0이 되도록 내림하지 않는다 (극단 비율에서도 최소 1px)', () => {
    const { height } = computeTargetSize(8000, 1);
    expect(height).toBeGreaterThanOrEqual(1);
  });
});

// ── WebP → JPEG 폴백 (#57) ───────────────────────────────────────────────────
//
// 가짜 toBlob: "이 브라우저가 만들 수 있는 MIME 목록"을 받아, 목록에 있으면 그 타입의 Blob을,
// 없으면 실측한 실제 브라우저 동작(= PNG 대체)을 흉내 낸다. `null`을 주는 동작도 따로 만든다.
function fakeToBlob(supported: string[], onUnsupported: 'png' | 'null' = 'png'): ToBlob {
  return (callback, type = 'image/png') => {
    if (supported.includes(type)) {
      callback(new Blob(['x'], { type }));
      return;
    }
    // 실측(HeadlessChrome 151, 2026-07-19): 미지원 MIME에 toBlob은 null이 아니라 PNG를 준다.
    callback(onUnsupported === 'png' ? new Blob(['x'], { type: 'image/png' }) : null);
  };
}

describe('encodeWithFallback', () => {
  it('WebP를 만들 수 있으면 WebP를 쓴다', async () => {
    const blob = await encodeWithFallback(fakeToBlob([IMAGE_MIME, FALLBACK_MIME]));
    expect(blob.type).toBe(IMAGE_MIME);
  });

  it('WebP 미지원 브라우저가 PNG로 대체해도 속지 않고 JPEG로 폴백한다 (#57 실측 동작)', async () => {
    const blob = await encodeWithFallback(fakeToBlob([FALLBACK_MIME, 'image/png'], 'png'));
    // ⚠️ 이 한 줄이 #57의 핵심이다 — 예전 코드는 PNG(=null 아님)를 성공으로 보고 그대로 저장했다.
    expect(blob.type).toBe(FALLBACK_MIME);
  });

  it('WebP에 null을 주는 브라우저에서도 JPEG로 폴백한다 (사양 이전 동작도 함께 커버)', async () => {
    const blob = await encodeWithFallback(fakeToBlob([FALLBACK_MIME], 'null'));
    expect(blob.type).toBe(FALLBACK_MIME);
  });

  it('WebP도 JPEG도 못 만들면 규격 밖 파일을 저장하지 않고 실패시킨다', async () => {
    await expect(encodeWithFallback(fakeToBlob(['image/png'], 'png'))).rejects.toThrow(
      '이미지를 변환하지 못했습니다',
    );
  });

  it('폴백으로 나온 JPEG는 확장자도 jpg다 (확장자↔내용 불일치 방지)', async () => {
    const blob = await encodeWithFallback(fakeToBlob([FALLBACK_MIME], 'png'));
    expect(extensionFor(blob)).toBe('jpg');
  });

  // toBlob이 콜백을 영영 안 부르는 경우(대용량 canvas OOM·오염된 canvas 등) 대비 — 진짜로 30초를
  // 기다리지 않고 가짜 타이머로 시간을 앞당긴다.
  it('toBlob이 콜백을 부르지 않으면 30초 뒤 타임아웃 오류로 거절한다(무한 대기 방지)', async () => {
    vi.useFakeTimers();
    try {
      const neverCallsBack: ToBlob = () => {
        // 의도적으로 콜백을 호출하지 않는다 — 실제 브라우저에서 toBlob이 응답하지 않는 상황을 흉내낸다.
      };
      const pending = expect(encodeWithFallback(neverCallsBack)).rejects.toThrow(
        '이미지 변환이 너무 오래 걸려요. 다시 시도해주세요.',
      );
      await vi.advanceTimersByTimeAsync(30_000);
      await pending;
    } finally {
      vi.useRealTimers();
    }
  });
});
