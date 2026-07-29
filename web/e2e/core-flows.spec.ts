// C 회귀 스위트 — 정식 스위트 승격판(2026-07-28, 대장 #182). Epic 1~6 핵심 사용자 흐름이
// 살아 있는지 확인하는 원래 일회성 감사 스펙(c-regression.spec.ts)을 그대로 옮긴다.
//
// 절대 규칙(원래 감사와 동일하게 유지):
//   1) web/src/ 제품 코드는 절대 수정하지 않는다.
//   2) 읽기 전용이다 — DB에 INSERT/UPDATE/DELETE 하지 않는다. 폼 제출도 하지 않는다.
//
// desktop-1280x800 프로젝트에서만 돈다(설계상 [desktop] 표기 — mobile 중복 실행 불필요).
// tablet-800x1024 프로젝트도 이 조건에 걸려 함께 스킵된다.
import { expect, test } from '@playwright/test';
import { assertLocalSupabase, fetchOnSaleListingIdWithPhoto, login, runPsql } from './helpers';
import { PROJECT_NAMES } from './project-names';

assertLocalSupabase();

const ADMIN_USER = { email: 'admin@test.com', password: 'seller123' }; // supabase/.env.seed — 전 계정 공유 비밀번호

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '이 감사는 desktop 프로젝트에서만 돈다');
});

// psql로 sold 매물 id 전량을 읽는다(읽기 전용 — SELECT만). C4가 "판매완료는 안 보인다"를 실측하는 근거.
function fetchSoldListingIds(): string[] {
  const out = runPsql(`select id from listings where status='sold' order by id`);
  return out
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

// ── C1 [desktop] 로그인 → 로그아웃 왕복 (Epic 1) ──────────────────────────
test('C1 로그인 → 로그아웃 왕복, /account 보호', async ({ page }) => {
  await login(page); // buyer@test.com

  // 로그인 상태 표식 — SiteNav는 email이 있을 때만 프로필▾ 트리거(aria-haspopup="true")를 그린다.
  const profileTrigger = page.locator('button[aria-haspopup="true"]');
  await expect(profileTrigger, '로그인 후 프로필▾ 트리거가 보여야 함').toBeVisible();

  // 로그아웃 — 프로필 드롭다운 안의 LogoutButton.
  //   목적지는 **공개 랜딩(/)** 이다(대장 DW-547, 2026-07-29에 `/login`에서 바꿈) — FR58이
  //   비로그인 열람을 허용하므로 로그아웃한 사용자를 아무것도 못 보는 화면에 두지 않는다.
  await profileTrigger.click();
  await page.getByRole('button', { name: '로그아웃' }).click();
  await page.waitForURL((url) => url.pathname === '/');

  // 로그아웃 후 (이미 도착한) 홈에서 "로그인" 링크가 다시 보이는지(비로그인 데스크톱 분기).
  await expect(
    page.getByRole('link', { name: '로그인' }).first(),
    '로그아웃 후 홈에 "로그인" 링크가 다시 보여야 함',
  ).toBeVisible();

  // 보호 경로 /account — proxy.ts PROTECTED_PREFIXES가 비로그인을 /login으로 튕긴다.
  await page.goto('/account');
  await page.waitForURL((url) => url.pathname === '/login');
  expect(new URL(page.url()).pathname, '/account는 비로그인 시 /login으로 리다이렉트되어야 함').toBe('/login');
});

// ── C2 [desktop] 매물 목록 검색·필터 (Epic 3-1) ───────────────────────────
// 병렬 간섭 메모(write-flows.spec.ts 5번 항목 분석과 짝) — 아래 단언은 모두 같은 테스트
// 실행 안에서 방금 조회한 totalCount 대비 **상대 비교**(toBeGreaterThan(0)/toBeLessThan)이지
// 특정 절대 건수를 하드코딩하지 않는다. 그래서 write-flows.spec.ts가 동시에 매물 1건을
// 만들었다 지워도(그 매물은 region='서울'로 등록되지만 keyword는 'E2E감사0728'로 '스타리아'와
// 무관) 이 비교는 흔들리지 않는다.
test('C2 매물 목록 검색·필터', async ({ page }) => {
  const cards = () => page.locator('[role="listitem"]');

  await page.goto('/search');
  const totalCount = await cards().count();
  expect(totalCount, '전체 매물 카드가 1개 이상이어야 비교가 의미 있음(로컬 DB on_sale 95건)').toBeGreaterThan(0);

  // 필터 하나 적용 — 지역=서울(실측 사전조회: on_sale 95건 중 24건).
  await page.getByLabel('지역').selectOption('서울');
  await page.getByRole('button', { name: '검색' }).click();
  await page.waitForURL((url) => url.searchParams.get('region') === '서울');
  const filteredCount = await cards().count();
  expect(filteredCount, '필터 적용 후 결과가 0건이면 안 됨').toBeGreaterThan(0);
  expect(filteredCount, '필터 적용 후 카드 수가 전체보다 줄어야 함(실측 비교)').toBeLessThan(totalCount);

  // 키워드 검색 — 모델명 "스타리아"(실측 사전조회: on_sale 3건).
  await page.goto('/search');
  await page.getByLabel('키워드(모델명)').fill('스타리아');
  await page.getByRole('button', { name: '검색' }).click();
  await page.waitForURL((url) => url.searchParams.get('q') === '스타리아');
  const keywordCards = cards();
  const keywordCount = await keywordCards.count();
  expect(keywordCount, '키워드 검색 결과가 1건 이상이어야 함').toBeGreaterThan(0);
  for (let i = 0; i < keywordCount; i++) {
    await expect(keywordCards.nth(i).locator('h3'), `${i}번째 카드 제목에 키워드가 포함돼야 함`).toContainText(
      '스타리아',
    );
  }

  // 존재하지 않을 검색어 — 빈 상태 문구(에러 문구가 아니라).
  await page.goto('/search');
  await page.getByLabel('키워드(모델명)').fill('zzzz없는차zzzz');
  await page.getByRole('button', { name: '검색' }).click();
  await page.waitForURL((url) => url.searchParams.get('q') === 'zzzz없는차zzzz');
  await expect(
    page.getByText('조건에 맞는 매물이 없습니다'),
    '존재하지 않는 검색어는 빈 상태 문구를 보여야 함',
  ).toBeVisible();
  // page.getByRole('alert')는 안 쓴다 — Next.js가 항상 심어두는 `#__next-route-announcer__`
  // (라우트 전환을 스크린리더에 알리는 내부 라이브 리전)도 role="alert"라, 이 앱에선 "에러 없음"의
  // 신호로 못 쓴다(실측: 빈 상태에서도 role=alert가 1개 잡힘). 대신 search/page.tsx가 실제 조회
  // 실패 때만 그리는 문구 패턴으로 판별한다.
  await expect(page.getByText(/불러오지 못했습니다/), '빈 상태는 에러 문구가 아니어야 함').toHaveCount(0);
});

// ── C3 [desktop] 매물 상세 필수 정보 (Epic 3-2) ───────────────────────────
test('C3 매물 상세 필수 정보', async ({ page }) => {
  const listingId = await fetchOnSaleListingIdWithPhoto();
  await page.goto(`/listings/${listingId}`);

  // 핵심 스펙 라벨 — VehicleInfoSection(ListingDetailSections.tsx)의 Field 라벨 그대로.
  for (const label of ['가격', '연식', '주행거리', '지역']) {
    await expect(page.getByText(label, { exact: true }), `상세 화면에 "${label}" 라벨이 보여야 함`).toBeVisible();
  }

  // 사진 갤러리 렌더.
  await expect(
    page.locator('img[data-testid="listing-photo"]').first(),
    '사진 갤러리(대표 이미지)가 렌더돼야 함',
  ).toBeVisible();

  // 문의 CTA — 데스크톱 aside/모바일 하단 바 두 인스턴스가 DOM에 함께 있으므로 보이는 쪽만 확인.
  await expect(
    page.locator('[data-testid="inquiry-cta"]:visible'),
    '문의 CTA가 보여야 함',
  ).toBeVisible();
});

// ── C4 [desktop] 판매완료 매물은 목록·검색에 안 나온다 (Epic 3-3, FR11) ───
// 병렬 간섭 메모 — soldIds는 이 테스트 실행 시점에 psql로 직접 조회한다(하드코딩 목록이 아님).
// write-flows.spec.ts의 매물이 이 순간 sold 상태라 해도, 제품 자체가 /search를 status='on_sale'로만
// 걸러 조회하므로(search/page.tsx) sold로 전환된 매물은 애초에 /search 카드 목록에 나타나지 않는다
// — 그래서 soldIds에 잡히든 안 잡히든 intersection은 흔들리지 않는다.
test('C4 판매완료 매물 비노출 + 직접 URL 접근 관측', async ({ page }) => {
  const soldIds = fetchSoldListingIds();
  expect(soldIds.length, '로컬 DB에 sold 매물이 있어야 이 검사가 의미 있음(실측 8건)').toBeGreaterThan(0);

  await page.goto('/search');
  const hrefs = await page
    .locator('[role="listitem"] a[href^="/listings/"]')
    .evaluateAll((els) => els.map((el) => el.getAttribute('href') ?? ''));
  expect(hrefs.length, '검색 결과 카드가 0개면 교집합 비교 자체가 무의미').toBeGreaterThan(0);

  const cardIds = hrefs.map((h) => h.replace('/listings/', ''));
  const intersection = cardIds.filter((id) => soldIds.includes(id));
  expect(intersection, `/search 카드에 sold 매물이 섞여 있음: ${intersection.join(', ')}`).toHaveLength(0);

  // sold 매물 상세로 직접 URL 접근 — 관측 + 소스 정의 대조.
  // 소스(listings/[id]/page.tsx): buyerListingsQuery가 status='on_sale'만 통과시키므로 sold는
  // `!listing` 분기로 합류 → notFound()가 아니라 EmptyState(role="status", 중립 톤, HTTP 200)를
  // 그린다고 명시돼 있다("판매완료는 오류가 아니라 정상적인 결과다" 주석). 이 정의와 대조해 단언한다.
  const targetSoldId = soldIds[0];
  const response = await page.goto(`/listings/${targetSoldId}`);
  expect(response?.status(), '소스가 notFound()를 쓰지 않으므로 HTTP 200이어야 함').toBe(200);
  await expect(
    page.getByRole('status'),
    'EmptyState(role=status)로 "매물을 찾을 수 없어요."가 떠야 함(소스 정의와 일치)',
  ).toContainText('매물을 찾을 수 없어요');
});

// ── C5 [desktop] 비로그인 접근 제어 (Epic 1-4 / 8-5) ──────────────────────
test('C5 비로그인 접근 제어', async ({ page }) => {
  // proxy.ts PROTECTED_PREFIXES = ['/admin', '/sell', '/ai', '/chat', '/wishlist', '/account'].
  // 이 케이스가 요구한 4개 경로 전부 그 목록 안에 있다 → 전부 /login + redirectedFrom을 기대한다.
  for (const path of ['/sell', '/admin', '/ai', '/account']) {
    await page.goto(path);
    await page.waitForURL((url) => url.pathname === '/login');
    const url = new URL(page.url());
    expect(url.pathname, `${path} 비로그인 접근은 /login으로 튕겨야 함`).toBe('/login');
    expect(url.searchParams.get('redirectedFrom'), `${path}의 redirectedFrom이 원래 경로를 담아야 함`).toBe(path);
  }
});

// ── C6 [desktop] 관리자 화면이 실제로 뜬다 (Epic 6) ───────────────────────
test('C6 관리자 화면 렌더 — 회원/매물/거래/채팅 관리', async ({ page }) => {
  await login(page, ADMIN_USER.email, ADMIN_USER.password);

  for (const path of ['/admin/members', '/admin/listings', '/admin/transactions', '/admin/chats']) {
    await page.goto(path);
    // page.getByRole('alert')는 안 쓴다 — C2와 같은 이유(Next.js `#__next-route-announcer__`가
    // 항상 role="alert"를 갖는다). 각 admin 페이지가 조회 실패 때만 그리는 "...불러오지
    // 못했습니다" 문구 패턴으로 판별한다.
    await expect(page.getByText(/불러오지 못했습니다/), `${path}: 에러 문구가 없어야 함`).toHaveCount(0);
    const rowCount = await page.locator('main ul li').count();
    expect(rowCount, `${path}: 데이터 행(li)이 1개 이상 렌더돼야 함`).toBeGreaterThan(0);
  }
});

// ── C7 [desktop] buyer 계정으로 관리자 화면 접근 차단 ─────────────────────
test('C7 buyer가 /admin에 접근하면 차단된다', async ({ page }) => {
  await login(page); // buyer@test.com

  await page.goto('/admin');
  // (admin)/layout.tsx의 requireRole(ADMIN) — 비관리자는 홈(/)으로 리다이렉트.
  await page.waitForURL((url) => url.pathname === '/');
  expect(new URL(page.url()).pathname, 'buyer의 /admin 접근은 requireRole(ADMIN)이 홈으로 보내야 함').toBe('/');
});
