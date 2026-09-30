// toKoreanOAuthError 단위테스트 — `/auth/callback`이 실어 보내는 `?error=oauth` 신호가
// 실제로 한국어 문구로 바뀌는지, 그리고 무관한 값은 건드리지 않는지 고정한다.
import { describe, expect, it } from 'vitest';
import { toKoreanOAuthError } from './oauthError';

describe('toKoreanOAuthError', () => {
  it('oauth 신호는 한국어 실패 문구로 바꾼다', () => {
    expect(toKoreanOAuthError('oauth')).toBe('카카오 로그인에 실패했습니다. 다시 시도해 주세요.');
  });

  it('값이 없으면 메시지도 없다(오류 배너를 띄우지 않음)', () => {
    expect(toKoreanOAuthError(null)).toBeNull();
    expect(toKoreanOAuthError(undefined)).toBeNull();
  });

  it('다른 쿼리값은 이 함수의 신호가 아니므로 무시한다', () => {
    expect(toKoreanOAuthError('')).toBeNull();
    expect(toKoreanOAuthError('access_denied')).toBeNull();
  });
});
