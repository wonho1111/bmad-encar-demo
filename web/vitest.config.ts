// Vitest 설정 — 순수 유틸 단위테스트 전용(project-context 규칙12).
//
// 이 프로젝트 web의 테스트 표준은 **E2E(Playwright) 우선**이다(Next.js 공식이 async 서버
// 컴포넌트는 단위테스트 대신 E2E를 권장). Vitest는 그 예외 조항 —
// "서버 컴포넌트 밖 순수 유틸이 생기면 그것만 단위테스트로 보강" — 을 위해서만 둔다.
// 그래서 jsdom·React Testing Library를 붙이지 않는다(컴포넌트를 여기서 테스트하지 않는다).
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
