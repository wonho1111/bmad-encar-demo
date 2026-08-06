// 스토리 11-2(상단 내비 재구성) + 11-3(AI 히어로 랜딩) — 정식 스위트 승격판(2026-07-28,
// 대장 #182). 원래 일회성 감사 스펙(b-nav-hero.spec.ts)이 잡던 축(로그인/역할별 내비 구성,
// 프로필 드롭다운 키보드 상호작용, 히어로 게이트·핸드오프 왕복, 차종 칩 파라미터, 입력 상한)을
// 그대로 옮긴다 — 기존 정식 nav-interactions.spec.ts는 열기/닫기 등 순수 상호작용 4종만 보고
// 이 축(내비 항목 구성 자체, 히어로)은 보지 않는다.
//
// 이 파일은 DB에 쓰지 않는다(읽기 전용) — 그래도 assertLocalSupabase()를 거는 이유: 시드
// 계정(buyer@test.com 등)으로 로그인하는데, 그 계정이 운영엔 없거나(로그인 실패로만 보임)
// 있어도(실제 사람 계정) 실패가 불투명해지기 때문.
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import { assertLocalSupabase, login, SEED_USER, mockAiSearch, buildMockListings } from './helpers';
import { PROJECT_NAMES } from './project-names';

assertLocalSupabase();

// 시드 계정(supabase/seed-local/01_accounts.sql) — 전 계정 공용 비밀번호(supabase/.env.seed).
const ADMIN_USER = { email: 'admin@test.com', password: 'seller123' };

// aria-haspopup 값으로 트리거를 고정한다(nav-interactions.spec.ts와 동일 관례 — aria-label은
// 열림/닫힘에 따라 문구가 바뀌어 불안정하다. SiteNav.tsx: 햄버거="dialog", 프로필="true").
function profileTrigger(page: Page) {
  return page.locator('button[aria-haspopup="true"]');
}
function hamburgerTrigger(page: Page) {
  return page.locator('button[aria-haspopup="dialog"]');
}
function heroInput(page: Page) {
  return page.getByLabel('AI 검색 질의 입력');
}

test.describe('스토리 11-2 상단 내비', () => {
  test('B1 [desktop] 비로그인 내비 구성', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await page.goto('/');

    await expect(page.getByRole('link', { name: '홈으로 이동' })).toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 사기' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'AI로 찾기' })).toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 팔기' })).toBeVisible();
    await expect(page.getByRole('link', { name: '로그인' })).toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 등록' })).toBeVisible();

    await expect(page.getByRole('link', { name: '찜한 매물' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: '채팅' })).toHaveCount(0);
    await expect(profileTrigger(page)).toHaveCount(0);
  });

  test('B2 [desktop] 로그인 내비 구성', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/search'); // 임의 공개 페이지

    await expect(page.getByRole('link', { name: '홈으로 이동' })).toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 사기' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'AI로 찾기' })).toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 팔기' })).toBeVisible();
    await expect(page.getByRole('link', { name: '찜한 매물' })).toBeVisible();
    await expect(page.getByRole('link', { name: '채팅' })).toBeVisible();
    await expect(profileTrigger(page)).toBeVisible();

    await expect(page.getByRole('link', { name: '로그인' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: '내 차 등록' })).toHaveCount(0);
    // 전역 "문의" 메뉴 부재 — 링크·버튼 어느 role로도 없어야 한다.
    await expect(page.getByRole('link', { name: '문의' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '문의' })).toHaveCount(0);
  });

  test('B3 [desktop] 프로필▾ 드롭다운', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/search');

    const trigger = profileTrigger(page);
    await trigger.click();

    const manageLink = page.getByRole('link', { name: '내 매물 관리' });
    const accountLink = page.getByRole('link', { name: '내 정보' });
    const logoutButton = page.getByRole('button', { name: '로그아웃' });
    await expect(manageLink).toBeVisible();
    await expect(manageLink).toHaveAttribute('href', '/sell');
    await expect(accountLink).toBeVisible();
    await expect(accountLink).toHaveAttribute('href', '/account');
    await expect(logoutButton).toBeVisible();

    // document.activeElement를 트리거 요소와 직접 비교한다(요청된 실측 방식).
    const triggerHandle = await trigger.elementHandle();
    await page.keyboard.press('Escape');
    await expect(manageLink).toHaveCount(0);
    const focusMatchesTrigger = await page.evaluate(
      (el) => el === document.activeElement,
      triggerHandle,
    );
    expect(focusMatchesTrigger, '포커스가 트리거 버튼으로 복귀해야 함').toBe(true);
  });

  test('B4 [desktop] /admin은 최소 헤더', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin');

    await expect(page.getByText('관리자', { exact: true })).toBeVisible();
    await expect(page.getByText(ADMIN_USER.email, { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();

    await expect(page.getByRole('link', { name: '내 차 사기' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'AI로 찾기' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: '내 차 팔기' })).toHaveCount(0);
  });

  test('B5 [mobile 390] 좁은 폭에서 접힘', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스');

    await login(page);
    await page.goto('/search');

    await expect(page.getByRole('link', { name: '내 차 사기' })).not.toBeVisible();
    await expect(page.getByRole('link', { name: 'AI로 찾기' })).not.toBeVisible();
    await expect(page.getByRole('link', { name: '내 차 팔기' })).not.toBeVisible();
    await expect(hamburgerTrigger(page)).toBeVisible();

    // 찜·채팅 아이콘은 뷰포트 무관 상시 노출(intent-contract "Always") — 상단에 그대로 남아 있어야 한다.
    await expect(page.getByRole('link', { name: '찜한 매물' })).toBeVisible();
    await expect(page.getByRole('link', { name: '채팅' })).toBeVisible();
  });

  test('B6 [desktop] /account 렌더', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/account');

    await expect(page.getByText(SEED_USER.email, { exact: true })).toBeVisible();
    await expect(page.getByText('구매자', { exact: true })).toBeVisible();
    await expect(page.getByText('buyer', { exact: true })).toBeVisible();

    await expect(page.locator('input')).toHaveCount(0);
    await expect(page.locator('form')).toHaveCount(0);
  });

  test('B7 [desktop] 비로그인 /account 리다이렉트', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await page.goto('/account');
    await page.waitForURL((url) => url.pathname === '/login');

    const url = new URL(page.url());
    expect(url.pathname).toBe('/login');
    expect(url.searchParams.get('redirectedFrom')).toBe('/account');
  });

  // spec-14-3에서 동작이 뒤집혔다: 이 케이스는 원래 "buyer가 /sell 접근하면 홈으로"였다.
  // /sell 게이트가 requireRole(SELLER) → requireUser()로 바뀌어 role 값과 무관하게 통과하므로
  // 옛 단언(홈 리다이렉트)은 이제 반드시 실패한다 — 삭제하지 않고 새 동작을 지키도록 뒤집는다.
  test('B8 [desktop] buyer가 /sell 접근하면 그대로 머문다(소유권 기반 게이트)', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/sell');
    // 매물 등록 화면이 실제로 렌더될 때까지 기다린 뒤 경로를 읽는다(리다이렉트가 있었다면 못 뜬다).
    await expect(
      page.getByRole('heading', { name: '매물 등록' }),
      'role=buyer도 /sell의 매물 등록 화면에 도달해야 함(FR52)',
    ).toBeVisible();

    expect(new URL(page.url()).pathname, 'buyer의 /sell 접근은 더 이상 홈으로 튕기지 않음').toBe(
      '/sell',
    );
  });
});

test.describe('스토리 11-3 AI 히어로 랜딩', () => {
  test('B9 [desktop] 비로그인 히어로 제출 = 게이트', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    const handle = await mockAiSearch(page, []);
    await page.goto('/');

    await heroInput(page).fill('2천만원 이하 SUV');
    await page.getByRole('button', { name: '검색' }).click();

    await page.waitForURL((url) => url.pathname === '/login');
    const url = new URL(page.url());
    expect(url.pathname).toBe('/login');
    expect(url.searchParams.get('redirectedFrom')).toBe('/');
    expect(handle.requestCount(), 'AI 호출이 나가지 않아야 함').toBe(0);
    await expect(page.getByText(/잔여/)).toHaveCount(0);
  });

  test('B10 [desktop] 로그인 복귀 시 질의 복원, 자동 실행 없음', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    const query = '2천만원 이하 SUV';
    const handle = await mockAiSearch(page, []);
    await page.goto('/');
    await heroInput(page).fill(query);
    await page.getByRole('button', { name: '검색' }).click();
    await page.waitForURL((url) => url.pathname === '/login');

    // 리다이렉트된 로그인 화면에서 실제 로그인(helpers.login과 동일 폼 조작, 이미 /login이므로 goto 생략).
    await page.getByLabel('이메일').fill(SEED_USER.email);
    await page.getByLabel('비밀번호').fill(SEED_USER.password);
    await page.getByRole('button', { name: '로그인' }).click();
    await page.waitForURL((url) => !url.pathname.startsWith('/login'));

    expect(new URL(page.url()).pathname).toBe('/');
    await expect(heroInput(page)).toHaveValue(query);
    expect(new URL(page.url()).pathname).not.toBe('/ai');
    expect(handle.requestCount(), '복귀만으로는 AI 호출이 나가면 안 됨').toBe(0);
  });

  test('B11 [desktop] 로그인 사용자 제출 → /ai 1회 자동 실행, 새로고침 시 재실행 없음', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/');
    const handle = await mockAiSearch(page, buildMockListings(3), '테스트 응답 3건');

    await heroInput(page).fill('4천만원대 전기 SUV');
    await page.getByRole('button', { name: '검색' }).click();

    await page.waitForURL((url) => url.pathname === '/ai');
    expect(new URL(page.url()).pathname).toBe('/ai');
    await expect(page.getByText('테스트 응답 3건')).toBeVisible();
    await expect(page.locator('section[aria-label="AI 대화 기록"] article')).toHaveCount(3);
    expect(handle.requestCount(), '자동 실행 1회').toBe(1);

    await page.reload();
    await page.waitForLoadState('networkidle');
    expect(handle.requestCount(), '새로고침 후에도 재실행되면 안 됨').toBe(1);
  });

  test('B12 [desktop] 차종 칩 → /search 파라미터', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    // CategoryChips.tsx 확인: SUV → { body_type: 'SUV' }, 전기 → { fuel: '전기' } (hrefFor가 만드는 쿼리키).
    await page.goto('/'); // 비로그인 컨텍스트(게이트 없이 통과해야 함을 함께 확인)
    const chips = page.getByRole('navigation', { name: '차종 빠른 진입' });
    await chips.getByRole('link', { name: 'SUV', exact: true }).click();
    await page.waitForURL((url) => url.pathname === '/search');
    let url = new URL(page.url());
    expect(url.pathname).toBe('/search');
    expect(url.searchParams.get('body_type')).toBe('SUV');

    await page.goto('/');
    await chips.getByRole('link', { name: '전기', exact: true }).click();
    await page.waitForURL((url) => url.pathname === '/search');
    url = new URL(page.url());
    expect(url.pathname).toBe('/search');
    expect(url.searchParams.get('fuel')).toBe('전기');
  });

  test('B13 [desktop] 히어로 입력 500자 상한', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');
    test.setTimeout(90_000); // 501회 키스트로크 시뮬레이션은 fill()보다 느리다(maxLength 실집행 확인을 위해 필요).

    await page.goto('/');
    const input = heroInput(page);
    // fill()은 .value를 직접 대입해 브라우저의 maxlength 처리(타이핑 시에만 적용)를 우회할 수 있다
    // — pressSequentially로 실제 키 입력을 흉내내 maxLength=500이 진짜로 집행되는지 실측한다.
    await input.pressSequentially('a'.repeat(501), { delay: 0 });

    const value = await input.inputValue();
    expect(value.length, '실제 input value 길이는 500이어야 함').toBe(500);
    await expect(page.getByText('500/500')).toBeVisible();
  });
});
