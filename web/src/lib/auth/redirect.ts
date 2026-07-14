// 로그인 후 복귀 경로 검증 (FR58 — docs/conventions.md §8 "행동 게이트 + 원위치 복귀").
//
// 왜 별도 파일인가: 이건 이 앱의 유일한 오픈 리다이렉트 방어선이다. 화면 컴포넌트 안에 숨어 있으면
//   ① 테스트할 수 없고(서버/클라이언트 컴포넌트는 E2E로만 잡힌다)
//   ② 리팩터 중 조용히 깨져도 CI가 아무 말을 안 한다.
// 순수 함수로 빼두면 단위테스트로 못을 박을 수 있다(project-context 규칙12 —
// "서버 컴포넌트 밖 순수 유틸이 생기면 그것만 Vitest로 보강").

// 로그인 후 이 경로들로는 되돌려보내지 않는다 — 로그인을 막 끝낸 사람을 로그인 폼으로
// 다시 보내면 빠져나갈 수 없는 막다른 길이 된다(`/login?redirectedFrom=/login`).
const AUTH_PATHS = ['/login', '/signup'];

/**
 * `redirectedFrom` 쿼리값이 안전한 내부 경로일 때만 그대로 쓰고, 아니면 홈('/')으로 폴백한다.
 *
 * 거부 대상:
 *   · null·빈 문자열 — 돌아갈 곳이 없음
 *   · '/'로 시작하지 않는 값 — 'https://evil.com' 같은 절대 URL(외부 이탈)
 *   · '//'로 시작 — 프로토콜상대 URL('//evil.com'을 브라우저는 외부로 해석한다)
 *   · '/\'로 시작 — 일부 브라우저가 위와 동일하게 해석하는 변종
 *   · 인증 경로 자신 — 로그인 직후 로그인 폼으로 되돌아가는 데드엔드 방지
 */
export function resolveSafeRedirect(redirectedFrom: string | null | undefined): string {
  if (!redirectedFrom) return '/';
  if (!redirectedFrom.startsWith('/')) return '/';
  if (redirectedFrom.startsWith('//') || redirectedFrom.startsWith('/\\')) return '/';
  // 쿼리·해시가 붙어 있어도 경로 부분만 떼어 판정한다('/login?next=x'도 데드엔드다).
  const path = redirectedFrom.split(/[?#]/)[0];
  if (AUTH_PATHS.includes(path)) return '/';
  return redirectedFrom;
}
