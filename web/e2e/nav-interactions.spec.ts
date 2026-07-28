// 내비 상호작용 4종 회귀 검사 (#160) — Story 11-2가 실측으로 잡았던 결함들인데, 지키는 실행 검사가
// 지금까지 0개였다(SiteNav.test.ts는 useEffect가 실행되지 않는 SSR 정적 렌더만 본다, 클릭·리사이즈는
// "구조적으로 이 검사의 사정거리 밖"이라 그 파일 헤더 주석이 직접 명시). 이 파일이 그 층을 메운다.
//
// 4개 시나리오(대장 원문 그대로): (a) 390px 햄버거 열기→바깥클릭 닫힘, (b) Esc 닫힘+포커스 트리거 복귀,
// (c) 프로필▾ 연 상태에서 햄버거 열면 프로필 닫힘(상호배타), (d) 390px에서 열고 1280px로 리사이즈하면
// 패널이 DOM에서 사라지고 aria-expanded="false".
//
// 뷰포트를 테스트 안에서 직접 제어하므로(특히 (d)는 하나의 테스트 안에서 390→1280을 오간다) 3개
// 프로젝트에서 중복 실행할 필요가 없다 — mobile 프로젝트 하나에서만 돈다.
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { login } from './helpers';
import { PROJECT_NAMES } from './project-names';

test.beforeEach(async ({}, testInfo) => {
  test.skip(
    testInfo.project.name !== PROJECT_NAMES.mobile,
    '뷰포트를 테스트 안에서 직접 제어하므로 한 프로젝트에서만 실행한다(중복 방지)',
  );
});

// aria-label은 열림/닫힘에 따라 문구가 바뀌므로(예: "메뉴 열기"↔"메뉴 닫기") 안정적인
// aria-haspopup 값으로 트리거를 고정한다(SiteNav.tsx — 햄버거="dialog", 프로필="true").
function hamburgerTrigger(page: import('@playwright/test').Page) {
  return page.locator('button[aria-haspopup="dialog"]');
}
function profileTrigger(page: import('@playwright/test').Page) {
  return page.locator('button[aria-haspopup="true"]');
}
function hamburgerPanel(page: import('@playwright/test').Page) {
  return page.locator('[role="dialog"][aria-label="메뉴"]');
}

/**
 * 좌표 (x,y)에 실제로 링크·버튼 등 인터랙티브 요소가 없는지 확인한다(코드리뷰 patch) — "바깥
 * 클릭"을 하드코딩 좌표로 시뮬레이션하면, 미래에 그 자리에 매물 카드 링크가 놓일 경우 클릭이
 * 메뉴를 닫는 대신 페이지를 이동시켜 이 테스트가 엉뚱한 이유로 깨지거나(최악엔 조용히 통과)
 * 한다. 클릭 전에 "여기는 정말 빈 배경이다"를 단언해, 좌표가 어긋나면 그 사실 자체가 실패
 * 사유로 또렷이 드러나게 한다.
 */
async function assertPointIsNotInteractive(page: Page, x: number, y: number) {
  const isInteractive = await page.evaluate(
    ([px, py]) => !!document.elementFromPoint(px, py)?.closest('a, button, [role="link"], [role="button"]'),
    [x, y] as [number, number],
  );
  expect(
    isInteractive,
    `(${x}, ${y}) 좌표가 링크·버튼 위에 있음 — "바깥 클릭" 시뮬레이션 좌표를 조정할 것`,
  ).toBe(false);
}

test('(a) 390px에서 햄버거를 열고 바깥을 클릭하면 닫힌다', async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/search');

  await hamburgerTrigger(page).click();
  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'true');
  await expect(hamburgerPanel(page)).toBeVisible();

  // "바깥" = 패널·트리거 컨테이너 밖의 한 점. 패널이 `absolute inset-x-0`라 헤더 바로 아래
  // 본문 상단(제목 등)까지 덮으므로(실측: 패널 y 68~233px, <h1> y 93~125px — 겹침), 페이지 제목이
  // 아니라 패널 아래로 확실히 벗어난 좌표(y=500)를 직접 클릭한다. 클릭 전에 그 좌표가 실제로
  // 매물 카드 링크 등과 겹치지 않는 빈 배경인지 먼저 확인한다(코드리뷰 patch) — /search 결과
  // 개수·레이아웃이 바뀌어 카드가 그 좌표까지 올라오면, 클릭이 메뉴를 닫는 대신 상세 페이지로
  // 이동시켜 이 테스트를 엉뚱하게 깨뜨릴(또는 우연히 통과시킬) 수 있다.
  await assertPointIsNotInteractive(page, 195, 500);
  await page.mouse.click(195, 500);

  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'false');
  await expect(hamburgerPanel(page)).toHaveCount(0);
});

test('(b) Esc로 닫히고 포커스가 트리거로 복귀한다', async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/search');

  await hamburgerTrigger(page).click();
  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'true');

  await page.keyboard.press('Escape');

  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'false');
  await expect(hamburgerPanel(page)).toHaveCount(0);
  await expect(hamburgerTrigger(page)).toBeFocused();
});

test('(c) 프로필▾을 연 상태에서 햄버거를 열면 프로필이 닫힌다(상호배타)', async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/search');

  await profileTrigger(page).click();
  await expect(page.getByRole('link', { name: '내 매물 관리' })).toBeVisible();

  // 마우스 클릭(.click())은 pointerdown도 함께 쏘아 프로필의 "바깥 클릭 닫기" 리스너가
  // 별도로 반응해 버린다 — 그러면 이 테스트가 실제로는 outside-click 메커니즘만 검증하고
  // toggleMenu의 명시적 상호배타 한 줄(setProfileOpen(false))은 지워도 통과해 버린다(실측 확인,
  // 3차 코드리뷰가 지적한 바로 그 사각지대). 키보드 Tab으로 옮기는 것도 안 된다 — 프로필의
  // FocusTrap이 열려 있는 동안 컨테이너 밖으로 나가는 포커스를 전역 focusin 리스너가 즉시
  // 도로 끌어오기 때문(실측 확인, FocusTrap.tsx handleFocusIn — 트랩이 열린 동안은 키보드로
  // 햄버거에 도달하는 것 자체가 불가능하다). 그래서 dispatchEvent('click')로 pointerdown 없이
  // click DOM 이벤트만 보낸다 — 보조기술이 접근성 API로 직접 활성화하는 경로와 동일하며,
  // 이게 바로 명시적 상호배타 코드가 지키는 진짜 대상이다.
  await hamburgerTrigger(page).dispatchEvent('click');

  await expect(hamburgerPanel(page)).toBeVisible();
  await expect(page.getByRole('link', { name: '내 매물 관리' })).toHaveCount(0);
  await expect(profileTrigger(page)).toHaveAttribute('aria-expanded', 'false');
});

test('(d) 390px에서 열고 1280px로 리사이즈하면 패널이 사라지고 aria-expanded=false', async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/search');

  await hamburgerTrigger(page).click();
  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'true');

  await page.setViewportSize({ width: 1280, height: 800 });

  await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'false');
  await expect(hamburgerPanel(page)).toHaveCount(0);
});
