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
import {
  assertLocalSupabase,
  buildMockListings,
  fetchOnSaleListingIdWithPhoto,
  login,
  mockAiSearch,
  SEED_USER,
} from './helpers';
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

  // 홈에 떠 있는 AI 진입(플로팅) 부재 — UX 확정 D12가 *"웹엔 FAB 없어 일관"* 을 **전제로**
  // 앱의 "FAB 없음"까지 결정했는데, 실제 웹엔 2026-06-25부터 플로팅 'AI 검색' 버튼이 있었고
  // 그 어긋남을 한 달 넘게 아무도 몰랐다(2026-08-07 제거). 문서에 적어두면 또 놓치므로 검사로 박는다.
  //
  // 라벨이 아니라 **떠 있다는 성질**로 잡는다 — 다른 이름·아이콘으로 되살아나도 걸리게 하려고
  // `/ai`로 가는 링크의 computed position이 fixed/sticky인지를 본다(라벨만 보면 문구를 바꾸는
  // 순간 검사가 조용히 통과한다). 상단바 'AI로 찾기'는 static이라 여기 안 걸린다.
  test('B5b [mobile 390] 홈에 떠 있는 AI 진입이 없다(D12 — 웹엔 FAB 없음)', async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스');

    await login(page);
    await page.goto('/');

    const floatingAiCount = await page.evaluate(() =>
      [...document.querySelectorAll('a[href="/ai"]')].filter((el) => {
        const pos = getComputedStyle(el).position;
        return pos === 'fixed' || pos === 'sticky';
      }).length,
    );
    expect(floatingAiCount, '홈에 떠 있는 /ai 진입이 있으면 안 된다').toBe(0);

    // 그런데 "없다"만 보면 AI로 갈 길이 통째로 사라져도 초록이 된다 — 진입로가 남아 있는지 같이 본다.
    // 모바일에선 상단바 링크가 햄버거 안이라, 상시로 보이는 AI 진입은 히어로 입력창이다.
    await expect(heroInput(page)).toBeVisible();
  });

  test('B6 [desktop] /account 렌더', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page);
    await page.goto('/account');

    await expect(page.getByText(SEED_USER.email, { exact: true })).toBeVisible();
    // ✎ 2026-08-06 역할 통합(0029): 역할 라벨이 '구매자' → '회원'이 됐다. 구매/판매 구분이
    //   사라졌으므로 이 계정에 남는 표시는 '회원' 하나다. 바로 아래 'buyer'는 역할이 아니라
    //   **표시 이름**(profiles.name)이라 그대로다 — 둘을 헷갈리면 안 된다.
    await expect(page.getByText('회원', { exact: true })).toBeVisible();
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
      '판매자 역할이 아닌 계정도 /sell의 매물 등록 화면에 도달해야 함(FR52)',
    ).toBeVisible();

    expect(new URL(page.url()).pathname, '일반 계정의 /sell 접근은 더 이상 홈으로 튕기지 않음').toBe(
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

// spec-15-2 관리자 반응형 — AdminSidebar의 I/O 매트릭스 3행(데스크톱 active 표시·모바일
// 슬라이드인 열기/Tab순환/Esc닫힘·리사이즈 자동닫힘). 나머지 1행(D5 가로스크롤 없음)은
// viewport-audit.spec.ts가 맡는다. AdminSidebar.tsx는 SiteNav.tsx의 FocusTrap-dialog +
// matchMedia 패턴을 그대로 이식했으므로, 위 B3(Esc+포커스 복귀)·B5(햄버거 노출) 테스트와
// 같은 방식으로 검증한다.
test.describe('spec-15-2 관리자 사이드바', () => {
  test('D1 [desktop] 사이드바 active 표시', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin/members');

    // spec-15-3(FR61) — 회원관리 역할 표시가 구매자/판매자가 아니라 admin/일반 축인지, 이미 이
    // 화면을 방문하는 지점에서 함께 확인한다(I/O 매트릭스 "회원관리 역할 표시" 행, 코드리뷰 지적
    // — 이 텍스트를 단언하는 검사가 이전엔 없었다). 행(`li`) 단위로 앵커링한다 — 그냥 화면
    // 어딘가에 "관리자"·"일반" 글자가 있는지만 보면 두 라벨을 서로 바꿔치기해도(관리자 행이
    // "일반"으로, 일반 행이 "관리자"로 잘못 뜨는 회귀) 통과해버린다(코드리뷰 adversarial 지적,
    // AdminSidebar.test.ts가 3차 리뷰에서 겪은 것과 같은 실패 모드). 본인 행은 "나" 배지로
    // 식별한다(page.tsx의 isSelf 렌더 규칙). 시드 계정(seed-local/01_accounts.sql, 0029 역할
    // 통합 후)은 admin@test.com만 role='admin'이고 나머지 8개는 전부 role='user'이므로,
    // 로그인한 admin 본인 행은 "관리자", 다른 아무 행이나 "일반"이어야 한다.
    const selfRow = page.locator('main li').filter({ hasText: '나' });
    await expect(selfRow).toHaveCount(1);
    await expect(selfRow.getByText('관리자', { exact: true })).toBeVisible();

    const otherRow = page.locator('main li').filter({ hasNotText: '나' }).first();
    await expect(otherRow.getByText('일반', { exact: true })).toBeVisible();

    const activeLink = page.getByRole('link', { name: '회원관리' });
    await expect(activeLink).toHaveAttribute('aria-current', 'page');

    const dashboardLink = page.getByRole('link', { name: '대시보드' });
    await expect(dashboardLink).not.toHaveAttribute('aria-current', 'page');

    // 코드리뷰 patch — 상세 라우트에서도 부모 항목이 active여야 한다. `isActiveHref`가 단순
    // 일치가 아니라 `startsWith`인 **유일한 이유**가 이 경우인데(목록/상세가 같은 항목을 켜야
    // 한다), 위 목록 경로 단언은 `pathname === href` 절만으로도 통과해서 그 분기를 한 번도
    // 지나지 않는다 — 함수를 `pathname === href`로 되돌려도 D1이 초록이었다.
    const listingId = await fetchOnSaleListingIdWithPhoto();
    await page.goto(`/admin/listings/${listingId}`);
    await expect(page.getByRole('link', { name: '매물 관리' })).toHaveAttribute('aria-current', 'page');
    // 그리고 '/admin'만은 정확 일치여야 한다 — startsWith를 그대로 적용하면 모든 /admin/* 에서
    // 대시보드가 항상 켜진 채로 보인다(AdminSidebar.tsx의 예외 분기).
    await expect(page.getByRole('link', { name: '대시보드' })).not.toHaveAttribute('aria-current', 'page');
  });

  // 코드리뷰 patch — 스펙의 마지막 인수조건("대시보드 허브의 기존 4개 링크와 각 상세 화면의
  // 뒤로가기 버튼이 사이드바 추가 후에도 그대로 존재한다")을 보는 검사가 하나도 없었다. 사이드바가
  // 생겼으니 허브 버튼은 중복이라며 지우는 건 다음 사람에게 아주 자연스러운 판단인데, 지우면
  // 기존 스위트가 전부 초록인 채로 통과한다.
  test('D1b [desktop] 사이드바가 기존 페이지 내비를 대체하지 않는다', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '데스크톱 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin');

    // 대시보드 허브의 4개 링크 버튼 — 사이드바의 같은 목적지 링크와 구분하려고 <main> 안으로 스코프한다.
    const hub = page.locator('main');
    for (const href of ['/admin/members', '/admin/listings', '/admin/transactions', '/admin/chats']) {
      await expect(hub.locator(`a[href="${href}"]`), `허브의 ${href} 링크가 사라졌음`).toHaveCount(1);
    }

    // 상세 화면의 뒤로가기 버튼도 그대로다.
    const listingId = await fetchOnSaleListingIdWithPhoto();
    await page.goto(`/admin/listings/${listingId}`);
    await expect(page.getByRole('button', { name: '돌아가기' })).toBeVisible();
  });

  test('D2 [mobile 390] 슬라이드인 열기 — Tab 순환·Esc 닫힘', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin/members');

    const trigger = hamburgerTrigger(page);
    await trigger.click();

    const dashboardLink = page.getByRole('link', { name: '대시보드' });
    const chatsLink = page.getByRole('link', { name: '채팅관리' });
    await expect(dashboardLink).toBeVisible();

    // 열릴 때 첫 포커서블(대시보드)로 이동(FocusTrap.tsx 계약).
    let focused = await page.evaluate(() => document.activeElement?.textContent);
    expect(focused, '패널이 열리면 첫 nav item(대시보드)으로 포커스가 이동해야 함').toBe('대시보드');

    // 마지막 item(채팅관리)까지 Tab으로 이동한 뒤, 한 번 더 누르면 첫 item으로 순환해야 한다.
    await chatsLink.focus();
    await page.keyboard.press('Tab');
    focused = await page.evaluate(() => document.activeElement?.textContent);
    expect(focused, 'Tab이 패널 밖으로 안 나가고 첫 item으로 순환해야 함').toBe('대시보드');

    const triggerHandle = await trigger.elementHandle();
    await page.keyboard.press('Escape');
    await expect(dashboardLink).toHaveCount(0);
    const focusMatchesTrigger = await page.evaluate(
      (el) => el === document.activeElement,
      triggerHandle,
    );
    expect(focusMatchesTrigger, 'Esc 닫힘 후 포커스가 햄버거 트리거로 복귀해야 함').toBe(true);
  });

  test('D3 [mobile 390] 데스크톱 폭으로 리사이즈되면 패널이 자동으로 닫힌다', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스 — 390px에서 시작해야 함');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin/members');

    await hamburgerTrigger(page).click();
    const dashboardLink = page.getByRole('link', { name: '대시보드' });
    await expect(dashboardLink).toBeVisible();

    // 760px 붕괴 기준(spec-15-2 Always) 이상으로 리사이즈 — matchMedia 리스너가 패널을 강제로 닫아야 한다.
    await page.setViewportSize({ width: 900, height: 844 });

    await expect(hamburgerTrigger(page)).not.toBeVisible();
    // 열려 있던 모바일 패널의 대시보드 링크는 사라지고, 데스크톱 고정 사이드바의 회원관리(active)만 남는다.
    await expect(page.getByRole('link', { name: '회원관리' })).toHaveAttribute('aria-current', 'page');

    // 코드리뷰 patch — 여기까지의 두 단언은 **CSS만으로 충족된다**. 모바일 트리거와 패널을 감싼
    // 컨테이너가 `min-[760px]:hidden`이라 900px에서는 display:none이 되고, 그러면 matchMedia
    // 자동닫힘을 통째로 지워 menuOpen이 true로 남아도 (a)햄버거는 안 보이고 (b)회원관리는 데스크톱
    // 사이드바 것 하나만 잡힌다 — 즉 기능을 삭제해도 초록이었다(실측: 이 단언들만으로는 red가 안 남).
    // 그래서 다시 모바일 폭으로 되돌려 **상태가 실제로 닫혔는지**를 본다. 자동닫힘이 없으면
    // 여기서 이전 화면의 패널이 되살아나 잡힌다.
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(hamburgerTrigger(page)).toBeVisible();
    await expect(
      hamburgerTrigger(page),
      '리사이즈 자동닫힘이 동작했다면 좁아진 뒤 패널은 닫힌 상태여야 함',
    ).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByRole('link', { name: '대시보드' })).toHaveCount(0);
  });

  // 코드리뷰 patch(spec-15-2) — AdminSidebar.tsx는 SiteNav.tsx의 outside-pointerdown-close를
  // 그대로 이식했는데(menuContainerRef 밖 pointerdown이면 닫힘), 그 SiteNav 쪽은
  // nav-interactions.spec.ts가 이미 별도로 덮고 있던 반면 이 새 컴포넌트는 D1~D3 어디도 그
  // 축(바깥 클릭 닫힘)을 보지 않았다 — D2(Tab 순환·Esc)·D3(리사이즈 자동닫힘)와 나란히 세 번째
  // 닫힘 경로를 실측한다.
  test('D4 [mobile 390] 패널 바깥을 클릭하면 닫힌다', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin/members');

    await hamburgerTrigger(page).click();
    const dashboardLink = page.getByRole('link', { name: '대시보드' });
    await expect(dashboardLink).toBeVisible();

    // 코드리뷰 patch — 예전엔 `page.mouse.click(200, 700)`으로 "패널이 안 닿는 하단 좌표"를 쳤다.
    // 그 좌표가 무엇 위에 떨어지는지는 아무것도 보장하지 않는데, 이 화면의 회원 행에는 `MemberActions`의
    // **정지 버튼이 확인창 없이 즉시 profiles를 UPDATE**한다 — 시드 회원이 몇 명이냐/행 높이가
    // 얼마냐에 따라 좌표가 그 위로 미끄러지면, "DB에 쓰지 않는다(읽기 전용)"고 파일 머리에 선언한
    // 스펙이 조용히 시드 계정을 정지시키고 그 뒤 모든 로그인 테스트가 엉뚱한 이유로 깨진다.
    // 대신 확실히 비활성인 요소(상단바의 이메일 텍스트)를 친다 — 패널보다 위에 있어 겹치지 않고,
    // menuContainerRef 바깥이며, 클릭해도 아무 일도 일어나지 않는다.
    await page.getByText(ADMIN_USER.email, { exact: true }).click();

    await expect(dashboardLink).toHaveCount(0);
    // 그리고 "닫혔다"와 "다른 데로 이동해 버려서 사라졌다"를 구분한다 — toHaveCount(0)만으로는
    // 바깥클릭 핸들러를 지워도 (클릭이 이동을 유발했다면) 초록이 될 수 있다.
    await expect(page).toHaveURL(/\/admin\/members$/);
    await expect(hamburgerTrigger(page)).toHaveAttribute('aria-expanded', 'false');
  });

  // 코드리뷰 patch(spec-15-2 3차) — AdminSidebar.tsx는 "경로가 바뀌면 패널을 닫는다"를 렌더 중
  // 상태 조정으로 갖고 있는데(prevPathname), 그 줄을 지나는 검사가 하나도 없었다. 이건 원본
  // SiteNav.tsx엔 **없는** 동작이라(거기는 usePathname을 안 쓴다) 이식 대칭성으로도 안 덮인다.
  // 패널 안 링크는 각자 onClick으로 닫으므로 D2·D4는 이 줄을 지워도 전부 초록이고,
  // AdminSidebar.test.ts는 라우터 밖 1회 렌더라 구조적으로 볼 수 없다.
  test('D5 [mobile 390] 패널을 연 채 뒤로가기로 경로가 바뀌면 패널이 닫힌다', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.mobile, '모바일 전용 케이스');

    await login(page, ADMIN_USER.email, ADMIN_USER.password);
    await page.goto('/admin');

    // ⚠️ 여기서 `page.goto('/admin/members')`를 쓰면 이 테스트는 **실패할 수 없다**(실측):
    //    goto는 문서를 통째로 새로 로드하므로 뒤로가기도 문서 로드가 되고, 그러면 AdminSidebar가
    //    새로 마운트되면서 menuOpen이 useState(false) 초기값으로 돌아간다 — 즉 경로변경 자동닫힘을
    //    통째로 지워도 초록이었다. 앱 안의 링크를 눌러 **클라이언트 내비게이션**으로 이동해야
    //    컴포넌트가 살아남고, 뒤로가기가 "마운트는 그대로 + pathname만 바뀜"이 되어 그 줄을 지난다.
    await page.locator('main').locator('a[href="/admin/members"]').first().click();
    await expect(page).toHaveURL(/\/admin\/members$/);

    await hamburgerTrigger(page).click();
    await expect(page.getByRole('dialog', { name: '관리자 메뉴' })).toBeVisible();

    // 링크 클릭이 아니라 브라우저 뒤로가기 — 화면은 /admin으로 바뀌는데 패널 상태만 남으면
    // 새 화면 위에 이전 화면에서 연 메뉴가 그대로 덮인다.
    await page.goBack();
    await expect(page).toHaveURL(/\/admin$/);
    await expect(
      hamburgerTrigger(page),
      '경로가 바뀌었으면 패널은 닫힌 상태여야 함',
    ).toHaveAttribute('aria-expanded', 'false');
    // 패널이 닫혔으므로 열려 있을 때만 그려지는 dialog가 없어야 한다(사이드바 링크 자체는
    // 데스크톱 nav에도 있으므로 링크 개수가 아니라 dialog로 판정한다).
    await expect(page.getByRole('dialog', { name: '관리자 메뉴' })).toHaveCount(0);
  });
});
