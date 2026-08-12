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

// ✎ 2026-08-13 2차 지적 #2로 이 시나리오의 전제가 사라졌다. 원래 (c)는 "390px에서 프로필▾과
//   햄버거가 **동시에 보이던** 시절"의 상호배타를 봤는데, 이제 프로필▾은 ≥760px 전용이고 좁은
//   폭에선 프로필 항목이 햄버거 패널 **안에** 있다 — 둘이 함께 열릴 수가 없다.
//   대신 그 코드가 지금 실제로 막는 것을 본다: **프로필▾을 넓은 폭에서 열어 둔 채 폭을 줄이면,
//   그 드롭다운은 `display:none`이 되면서도 상태가 살아남아 "보이지 않는 FocusTrap"이 된다.**
//   그러면 트랩의 전역 focusin 리스너가 포커스를 도로 끌어가 햄버거 패널을 조작할 수 없게 된다.
//   SiteNav의 matchMedia 핸들러가 그때 프로필을 닫는데, 그 한 줄을 지워도 아무 검사가 없었다.
test('(c) 프로필▾을 연 채 좁은 폭으로 줄이면 프로필이 닫히고 햄버거를 정상 조작할 수 있다', async ({
  page,
}) => {
  await login(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/search');

  await profileTrigger(page).click();
  await expect(page.getByRole('link', { name: '내 매물 관리' })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });

  // 상태 자체가 닫혀야 한다 — "안 보인다"만 보면 CSS(min-[760px]:flex)만으로 충족돼
  // matchMedia 닫힘을 통째로 지워도 통과한다(실측으로 확인한 함정, D3와 같은 부류).
  await expect(profileTrigger(page)).toHaveAttribute('aria-expanded', 'false');

  // 그리고 실제로 조작 가능한지까지 본다 — 살아남은 트랩이 포커스를 붙들고 있으면 여기서 걸린다.
  await hamburgerTrigger(page).click();
  await expect(hamburgerPanel(page)).toBeVisible();
  await expect(hamburgerPanel(page).getByRole('link', { name: '내 매물 관리' })).toBeVisible();
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
