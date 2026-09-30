// 카카오 등 OAuth 로그인 콜백 실패 → 한국어 메시지 (Story 18.1 AC3).
//
// 왜 별도 파일인가: `/auth/callback`(서버 라우트 핸들러)은 실패하면 원본 provider 에러를 그대로
// 붙이지 않고 `?error=oauth` 한 가지 신호만 실어 `/login`으로 돌려보낸다(원본 메시지 비노출).
// 그 신호를 사람이 읽을 문구로 바꾸는 지점이 여기다 — redirect.ts와 같은 이유로 순수 함수로
// 빼서 단위테스트로 못박는다(서버 라우트·리다이렉트 흐름은 E2E로만 잡히므로).
export function toKoreanOAuthError(error: string | null | undefined): string | null {
  if (error !== 'oauth') return null;
  return '카카오 로그인에 실패했습니다. 다시 시도해 주세요.';
}
