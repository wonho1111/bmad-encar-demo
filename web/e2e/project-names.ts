// Playwright 프로젝트 이름 상수 (코드리뷰 patch) — playwright.config.ts의 `projects` 배열과
// 스펙 파일들의 `test.skip(testInfo.project.name !== '...')` 가드가 이 값 하나를 공유한다.
// *.spec.ts 네이밍이 아니므로 러너가 이 파일 자체를 테스트로 수집하지 않는다(helpers.ts와 동일).
//
// 예전엔 두 곳에 매직 스트링으로 각각 박혀 있었다 — `playwright.config.ts`에서 프로젝트
// 이름을 하나만 바꿔도(오타 정정·재명명 등) 스펙 쪽 문자열은 그대로 남아 `test.skip` 조건이
// 항상 참이 되어 nav-interactions.spec.ts·image-fallback.spec.ts의 7개 테스트가 전부 조용히
// 스킵되고, 그런데도 실행은 exit 0으로 끝난다(B9 — 규칙은 어길 수 없는 자리에 박는다). 상수
// 하나를 공유하면 이름을 바꿀 때 타입 에러로 드러난다.
export const PROJECT_NAMES = {
  desktop: 'desktop-1280x800',
  tablet: 'tablet-800x1024',
  mobile: 'mobile-390x844',
} as const;
