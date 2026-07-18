// 저장본 규격 계산 테스트 (AC4).
// resizeImage 자체는 canvas(브라우저 API)를 쓰므로 node 환경에서 돌릴 수 없다.
// 그래서 **크기 계산만** 순수 함수로 떼어내 여기서 검증한다 — 나머지(실제 인코딩)는
// Task 6에서 "원본 바이트 vs 저장본 바이트"를 실측해 증명한다.
//
// **이 검사가 안 보는 것:**
//  · 실제 인코딩(WebP·quality 0.82)이 되는지, 파일이 **정말 작아지는지** — canvas가 없어
//    여기서 못 본다. Task 6에서 원본/저장본 바이트를 실측해 증명한다.
//  · WebP 미지원 브라우저의 JPEG 폴백 경로 — 그 분기는 여기서 한 번도 실행되지 않는다.
import { describe, it, expect } from 'vitest';
import { computeTargetSize, MAX_IMAGE_EDGE } from './resize';

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
