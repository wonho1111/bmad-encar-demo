// resolveSafeRedirect 단위테스트 — 오픈 리다이렉트 방어를 못 박는다.
//
// 왜 이 함수만 테스트하나: 이건 이 앱의 유일한 리다이렉트 보안 통제다. 조용히 깨지면
// `?redirectedFrom=//evil.com`으로 사용자를 외부로 내보낼 수 있는데, E2E는 이 조합을
// 일일이 돌지 않는다. 순수 함수라 값싸게 전수 고정할 수 있다(규칙12 예외 조항).

import { describe, expect, it } from 'vitest';
import { resolveSafeRedirect } from './redirect';

describe('resolveSafeRedirect', () => {
  it('정상 내부 경로는 그대로 돌려준다', () => {
    expect(resolveSafeRedirect('/listings/abc')).toBe('/listings/abc');
    expect(resolveSafeRedirect('/search?region=서울')).toBe('/search?region=서울');
  });

  it('값이 없으면 홈으로 폴백한다', () => {
    expect(resolveSafeRedirect(null)).toBe('/');
    expect(resolveSafeRedirect(undefined)).toBe('/');
    expect(resolveSafeRedirect('')).toBe('/');
  });

  it('외부 절대 URL을 거부한다', () => {
    expect(resolveSafeRedirect('https://evil.com')).toBe('/');
    expect(resolveSafeRedirect('http://evil.com')).toBe('/');
    // 상대 경로처럼 생겼지만 '/'로 시작하지 않으면 기준이 모호하다 → 거부.
    expect(resolveSafeRedirect('evil.com')).toBe('/');
  });

  it('프로토콜상대 URL을 거부한다 (브라우저가 외부로 해석하는 핵심 우회 경로)', () => {
    expect(resolveSafeRedirect('//evil.com')).toBe('/');
    expect(resolveSafeRedirect('//evil.com/path')).toBe('/');
    expect(resolveSafeRedirect('/\\evil.com')).toBe('/');
  });

  it('인증 경로로는 되돌리지 않는다 (로그인 직후 로그인 폼 = 데드엔드)', () => {
    expect(resolveSafeRedirect('/login')).toBe('/');
    expect(resolveSafeRedirect('/signup')).toBe('/');
    // 쿼리가 붙어도 경로 부분으로 판정한다(중첩 리다이렉트 방지).
    expect(resolveSafeRedirect('/login?redirectedFrom=/login')).toBe('/');
  });

  it('이름이 비슷한 정상 경로는 막지 않는다 (인증 경로 판정이 과하지 않아야 한다)', () => {
    expect(resolveSafeRedirect('/loginhelp')).toBe('/loginhelp');
  });
});
