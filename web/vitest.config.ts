// Vitest 설정 — 순수 유틸 단위테스트 전용(project-context 규칙12).
//
// 이 프로젝트 web의 테스트 표준은 **E2E(Playwright) 우선**이다(Next.js 공식이 async 서버
// 컴포넌트는 단위테스트 대신 E2E를 권장). Vitest는 그 예외 조항 —
// "서버 컴포넌트 밖 순수 유틸이 생기면 그것만 단위테스트로 보강" — 을 위해서만 둔다.
// 그래서 jsdom·React Testing Library는 여전히 안 붙인다 — 다만 컴포넌트를 아예 안 건드리는 건
// 아니다(3차 코드리뷰 지적 P7, AppHeader.test.ts·SiteNav.test.ts가 실제 반례). DOM이 없어도 되는
// 방식으로만 컴포넌트를 검사한다: 훅 없는 서버 컴포넌트는 함수로 직접 호출해 React 엘리먼트 트리
// (순수 객체)를 순회하고(AppHeader.test.ts), 훅이 있는 클라이언트 컴포넌트는 renderToStaticMarkup
// (react-dom/server)으로 정적 마크업만 뽑아 렌더 결과를 확인하며(SiteNav.test.ts — useEffect는 SSR
// 에서 실행되지 않으므로 렌더 계약만 고정한다), 그 외엔 소스 파일을 문자열로 읽는 스캔 테스트를
// 쓴다. 실제 브라우저 동작(상호작용·CSS·레이아웃)은 여전히 E2E 몫이다.
import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  test: {
    // 순수 함수만 다루므로 node 환경으로 충분하다(브라우저 DOM 불필요).
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
  resolve: {
    // tsconfig의 '@/*' → './src/*' 별칭을 그대로 맞춘다(규칙9).
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
});
