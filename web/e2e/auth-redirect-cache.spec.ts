// 로그인 후 복귀(redirectedFrom)가 **클라이언트 라우터 캐시에 막히지 않는지** 실측한다
// (2026-08-13 사용자 지적 #7 — "로그아웃 → 로그인 후 내차팔기 들어가면 로그인 화면이 다시 뜬다").
//
// 무엇을 잡는 검사인가:
//   비로그인 상태로 보호 경로(/sell)를 누르면 proxy가 /login?redirectedFrom=%2Fsell로 보낸다.
//   그 순간 Next.js 클라이언트 라우터 캐시에 "/sell = 로그인 화면"이라는 결과가 남는다.
//   여기서 로그인에 성공한 뒤 `router.push('/sell')`을 하면 라우터가 서버에 다시 묻지 않고 그
//   캐시를 재생해 **로그인 화면이 그대로 다시 뜬다**. 이 검사는 그 재생을 잡는다.
//
// ⚠️ **dev 모드에서는 재현되지 않는다 — 반드시 운영 빌드로 돌려야 한다.** dev는 <Link> 프리페치가
//    꺼져 있어 캐시가 채워지지 않는다(실측). playwright.config.ts의 webServer가 이미
//    `next build && next start`라 이 스위트는 조건을 만족한다.
//
// 읽기 전용이다 — DB에 아무것도 쓰지 않는다(로그인만 한다).
import { expect, test } from '@playwright/test';
import { assertLocalSupabase, SEED_USER } from './helpers';
import { PROJECT_NAMES } from './project-names';

assertLocalSupabase();

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '이 검사는 desktop 프로젝트에서만 돈다');
});

test('비로그인 → 보호 경로 클릭 → 로그인 → 원래 가려던 화면으로 실제로 들어간다', async ({ page }) => {
  // 1) 비로그인으로 홈에 들어가 상단바의 "내 차 팔기"를 누른다 → 로그인 화면으로 튕긴다.
  //    (이 클릭이 라우터 캐시에 "/sell = 로그인 화면"을 심는 지점이다.)
  await page.goto('/');
  await page.locator('header').getByRole('link', { name: '내 차 팔기' }).click();
  await page.waitForURL(/\/login\?redirectedFrom=%2Fsell/);

  // 2) 그 화면에서 그대로 로그인한다.
  await page.getByLabel('이메일').fill(SEED_USER.email);
  await page.getByLabel('비밀번호').fill(SEED_USER.password);
  await page.getByRole('button', { name: '로그인' }).click();

  // 3) 여기가 핵심 — 로그인 화면에 머물지 않고 /sell로 실제 진입해야 한다.
  //    회귀 시 URL은 /login?redirectedFrom=%2Fsell에 그대로 남고 아래 waitForURL이 타임아웃으로 죽는다.
  await page.waitForURL(/\/sell$/);

  // URL만 보고 통과시키지 않는다(캐시 재생은 URL이 아니라 **그려진 화면**의 문제다) —
  // 매물 등록 화면의 제목이 실제로 그려졌는지까지 확인한다.
  await expect(
    page.getByRole('heading', { name: '매물 등록' }),
    '로그인 후 /sell의 "매물 등록" 화면이 실제로 그려져야 함(로그인 폼이 재생되면 안 됨)',
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: '로그인' }),
    '로그인 화면이 다시 그려지면 안 됨(클라이언트 라우터 캐시 재생 회귀)',
  ).toHaveCount(0);
});
