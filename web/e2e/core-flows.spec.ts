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
import {
  assertLocalSupabase,
  fetchChatRoomIdForSeedUser,
  fetchOnSaleListingIdWithPhoto,
  login,
  runPsql,
  SEED_USER,
} from './helpers';
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

  // 화면에 그려진 **전체 건수**를 읽는다 — 카드 수가 아니다.
  // ⚠️ 카드 수로 비교하면 안 된다(2026-08-06 실측, DW-689): `/search`는 `PAGE_SIZE = 24`로
  // 잘라 그리므로 조건에 걸린 건수가 24를 넘으면 필터 전후가 **둘 다 24**가 되어, 필터가
  // 정상 동작해도 "줄어들지 않았다"로 실패한다. 실제로 Story 13-10이 매물을 93→158건으로
  // 늘리자(서울 43건 > 24) 이 단언이 red가 됐다. 즉 옛 단언은 필터가 아니라 **데이터 규모**를
  // 보고 있었다. 총 건수는 페이지네이션과 무관하므로 데이터가 더 늘어도 이 검사는 살아 있다.
  const totalOf = async () => {
    const text = await page.getByText(/\d+건의 매물/).first().innerText();
    const n = Number(text.match(/(\d+)건의 매물/)?.[1]);
    expect(Number.isInteger(n), `총 건수 문구를 못 읽었다(받은 값: "${text}")`).toBe(true);
    return n;
  };

  await page.goto('/search');
  const totalCount = await totalOf();
  expect(totalCount, '전체 매물이 1건 이상이어야 비교가 의미 있음').toBeGreaterThan(0);
  expect(await cards().count(), '첫 페이지에 카드가 그려져야 함').toBeGreaterThan(0);

  // 필터 하나 적용 — 지역=서울.
  await page.getByLabel('지역').selectOption('서울');
  await page.getByRole('button', { name: '검색' }).click();
  await page.waitForURL((url) => url.searchParams.get('region') === '서울');
  const filteredCount = await totalOf();
  expect(filteredCount, '필터 적용 후 결과가 0건이면 안 됨').toBeGreaterThan(0);
  expect(filteredCount, '필터 적용 후 전체 건수가 줄어야 함(실측 비교)').toBeLessThan(totalCount);

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
  // ✎ 2026-08-13(#2 상세 재구성) — 요약 카드에도 주요 제원 6칸(연식·주행거리·연료·배기량·지역·
  //   색상)이 생겨 같은 라벨이 화면에 2개씩 있다. 그래서 **"차량정보" 섹션 안으로 범위를 좁혀**
  //   찾는다. 페이지 전체에서 찾으면 strict mode 위반으로 죽는데, 그건 "라벨이 사라졌다"가 아니라
  //   "두 군데 있다"는 뜻이라 이 검사가 보려던 것과 다르다.
  const vehicleSection = page.locator('section').filter({ hasText: '차량정보' });
  for (const label of ['가격', '연식', '주행거리', '지역']) {
    await expect(
      vehicleSection.getByText(label, { exact: true }),
      `상세 화면 "차량정보"에 "${label}" 라벨이 보여야 함`,
    ).toBeVisible();
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

  // 상세 라우트 2개(spec-15-2, DW-697 ③) — 목록 4개에 이어 대표 상세를 각각 확인한다.
  const listingId = await fetchOnSaleListingIdWithPhoto();
  await page.goto(`/admin/listings/${listingId}`);
  await expect(
    page.getByText(/불러오지 못했습니다|찾을 수 없습니다/),
    `/admin/listings/${listingId}: 에러 문구가 없어야 함`,
  ).toHaveCount(0);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

  // 관리자 채팅방 열람 — isSeller 기준 좌/우 배치(DW-697 ③, admin/chats/[roomId]/page.tsx의
  // `isSeller ? 'items-end' : 'items-start'` 분기). 시드 방(fetchChatRoomIdForSeedUser)은 buyer·
  // seller 발신 메시지가 둘 다 있어 두 배치를 모두 실측할 수 있다(supabase/seed-local/data 확인).
  const roomId = fetchChatRoomIdForSeedUser();
  await page.goto(`/admin/chats/${roomId}`);
  await expect(
    page.getByText(/불러오지 못했습니다|찾을 수 없습니다/),
    `/admin/chats/${roomId}: 에러 문구가 없어야 함`,
  ).toHaveCount(0);
  const messageItems = page.locator('main ul li');
  const messageCount = await messageItems.count();
  expect(messageCount, `/admin/chats/${roomId}: 대화 내용(li)이 1개 이상 렌더돼야 좌/우 배치를 단언할 수 있음`).toBeGreaterThan(0);
  // 개별 일치 확인만으로는 이 단언이 허수아비가 될 수 있다(코드리뷰 patch) — 시드 방의 발신자가
  // 전부 한쪽(예: 전부 구매자)으로 쏠리면, 아래 루프는 매 메시지가 "자기 자신의 라벨과 일치"하는
  // 것만 확인할 뿐 items-end/items-start 두 배치가 실제로 **둘 다** 렌더됐는지는 확인하지 못한다
  // — 즉 좌/우 구분 자체가 깨져도(예: isSeller 분기가 통째로 사라져 전부 items-start가 돼도) 시드
  // 데이터가 우연히 한쪽뿐이면 초록으로 통과한다. 그래서 두 배치가 각각 최소 1건씩 나왔는지도 함께 센다.
  let sellerCount = 0;
  let otherCount = 0;
  for (let i = 0; i < messageCount; i++) {
    const li = messageItems.nth(i);
    // 각 메시지의 첫 줄(senderLabel, "판매자"/"구매자"/"기타 …")로 isSeller 여부를 판별해,
    // 그 판정과 실제 렌더된 정렬 클래스(items-end=우측/items-start=좌측)가 일치하는지 확인한다.
    const label = await li.locator('span').first().innerText();
    const isSeller = label.startsWith('판매자');
    const expectedClass = isSeller ? /items-end/ : /items-start/;
    await expect(li, `"${label}" 메시지의 좌/우 배치가 isSeller 판정과 어긋남`).toHaveClass(expectedClass);
    if (isSeller) sellerCount++;
    else otherCount++;
  }
  expect(sellerCount, '판매자 메시지가 최소 1건 있어야 좌우 배치 대비가 성립함').toBeGreaterThan(0);
  expect(otherCount, '구매자/기타 메시지가 최소 1건 있어야 좌우 배치 대비가 성립함').toBeGreaterThan(0);
});

// ── C7 [desktop] buyer 계정으로 관리자 화면 접근 차단 ─────────────────────
test('C7 buyer가 /admin에 접근하면 차단된다', async ({ page }) => {
  await login(page); // buyer@test.com

  await page.goto('/admin');
  // (admin)/layout.tsx의 requireRole(ADMIN) — 비관리자는 홈(/)으로 리다이렉트.
  await page.waitForURL((url) => url.pathname === '/');
  expect(new URL(page.url()).pathname, 'buyer의 /admin 접근은 requireRole(ADMIN)이 홈으로 보내야 함').toBe('/');
});

// ── C8 [desktop] 판매자 역할이 아닌 기존 계정으로 /sell 접근 (spec-14-3, FR52) ──
// 소유권 기반 게이트 회귀 검사 — sell/layout.tsx가 requireRole(SELLER)에서 requireUser()로
// 바뀐 뒤에도 판매자 역할이 아닌 계정이 홈으로 튕기지 않고 매물 등록 화면에 도달하는지 확인한다.
// 읽기 전용(폼 제출 없음) — 이 스펙 파일의 절대 규칙을 지킨다.
test('C8 판매자 역할이 아닌 기존 계정이 /sell에 접근하면 매물 등록 화면이 렌더된다', async ({ page }) => {
  // 전제를 주석이 아니라 DB로 고정한다(C4가 sold id를 psql로 실측하는 것과 같은 관례).
  // 이게 없으면 시드·가입 트리거가 바뀌었을 때 이 테스트는 "로그인 사용자가 /sell에 간다"로
  // 조용히 약해지면서도 계속 초록이라, 정작 검사해야 할 FR52를 안 보게 된다.
  // 계정은 SEED_USER 상수에서 읽는다 — 리터럴로 적으면 상수를 다른 계정으로 바꿨을 때
  // "role을 검사한 계정"과 "실제로 로그인한 계정"이 갈라진 채로 초록이 된다.
  // ✎ 2026-08-06 역할 통합(0029)으로 시드 계정의 role이 'buyer' → 'user'가 됐다.
  //   그래서 "role이 정확히 'buyer'인가"로는 더 이상 고정할 수 없다. 하지만 이 검사가
  //   지켜야 하는 것은 원래 그 값이 아니라 **"판매자 역할이 아닌 계정도 /sell에 간다"**이다.
  //   그 뜻 그대로 단언하면 통합 전(buyer)에도 후(user)에도 옳다.
  const seedRole = runPsql(
    `select p.role from profiles p join auth.users u on u.id = p.id where u.email='${SEED_USER.email}'`,
  ).trim();
  expect(seedRole, '시드 계정의 role을 읽지 못했다').not.toBe('');
  expect(
    ['seller', 'admin'].includes(seedRole),
    `C8은 판매자·관리자가 아닌 계정으로 FR52를 검사한다 — 받은 role='${seedRole}'`,
  ).toBe(false);

  await login(page); // SEED_USER = buyer@test.com

  await page.goto('/sell');
  // 먼저 화면이 뜨는 것을 기다린다 — 리다이렉트가 있었다면 이 heading은 나오지 않는다.
  // (goto 직후 pathname만 읽으면 아직 리다이렉트가 끝나지 않은 상태를 통과로 볼 수 있다.)
  await expect(
    page.getByRole('heading', { name: '매물 등록' }),
    '/sell이 매물 등록 폼을 렌더해야 함(FR52)',
  ).toBeVisible();
  // 홈으로 튕기지 않아야 한다(구 동작이었다면 requireRole(SELLER)이 '/'로 리다이렉트했을 것).
  expect(
    new URL(page.url()).pathname,
    '판매자 역할이 아닌 계정도 /sell에 그대로 머물러야 함(홈 리다이렉트 없음)',
  ).toBe('/sell');
});

// ── C8b [desktop] 관리자 계정으로 /sell 접근 (DW-675, spec-15-3) ──
// C8과 짝을 이루는 회귀 가드 — /sell 게이트는 requireUser()라 role을 안 보므로 admin도
// 통과한다(spec-14-3 Design Notes가 "의도된 귀결"로 명시 선언). 그런데 그 선언을 지키는
// 자동 검사가 없어(DW-675) admin 제외 분기가 무검사로 들어올 수 있었다. 여기서는 "화면
// 렌더"만 읽기 전용으로 고정한다(RLS·쓰기 경로는 검사하지 않음).
// 읽기 전용(폼 제출 없음) — 이 스펙 파일의 절대 규칙(쓰기 없음)을 지킨다.
test('C8b 관리자 계정이 /sell에 접근하면 매물 등록 화면이 렌더된다', async ({ page }) => {
  await login(page, ADMIN_USER.email, ADMIN_USER.password);

  await page.goto('/sell');
  await expect(
    page.getByRole('heading', { name: '매물 등록' }),
    '/sell이 관리자 계정에도 매물 등록 폼을 렌더해야 함(회귀 없음)',
  ).toBeVisible();
  expect(
    new URL(page.url()).pathname,
    '관리자 계정도 /sell에 그대로 머물러야 함(홈 리다이렉트 없음)',
  ).toBe('/sell');
});

// ── C9 [desktop] **새로 가입한** 계정으로 /sell 접근 (spec-14-2 + 14-3, FR52) ──
// 왜 C8과 따로 필요한가(DW-691): 에픽 14의 최종 인수 조건은 "기존 buyer · 기존 seller ·
// **신규 가입** 세 계정이 전부 /sell에 간다"인데, 앞의 둘만 자동 검사가 있었다.
// 신규 축에 대해 14.2가 만든 것은 **반쪽 두 개**다 — 단위테스트는 "가입 화면이 role metadata를
// 안 보낸다"까지, 실DB 통합테스트는 "트리거가 role 없으면 기본값을 넣는다"까지만 본다.
// **그 둘을 이어붙인 "그래서 그 계정이 /sell에 간다"는 아무도 안 봤다.** 두 반쪽이 각각 초록인
// 채로 합이 깨질 수 있다 — 판매 게이트가 다시 역할을 보게 바뀌면 둘 다 초록인데 신규 가입자만
// 조용히 막힌다. 그게 정확히 14.2가 처음에 CRITICAL 에스컬레이션으로 멈춰 세웠던 결함이다.
// 읽기 전용(매물 폼 제출 없음) — 이 스펙 파일의 절대 규칙을 지킨다. 계정 생성은 이 테스트가
// 만든 것이므로 끝에서 직접 지운다(write-flows의 원복 증명 관례).
test('C9 새로 가입한 계정이 /sell에 접근하면 매물 등록 화면이 렌더된다', async ({ page }) => {
  // 실행마다 고유해야 재실행이 "이미 존재하는 이메일"로 실패하지 않는다.
  const email = `e2e-c9-${Date.now()}@test.local`;
  const password = 'seller123';

  try {
    await page.goto('/signup');
    // 역할 선택이 **없어야** 한다(FR52 — 14.2가 제거). 있으면 이 테스트의 전제가 무너진다.
    await expect(
      page.getByLabel('역할'),
      '가입 화면에 역할 선택이 남아 있으면 안 됨(14.2가 제거)',
    ).toHaveCount(0);

    await page.getByLabel('이메일').fill(email);
    await page.getByLabel('비밀번호').fill(password);
    await page.getByRole('button', { name: '가입하기' }).click();
    // 가입 성공 = 로그인 상태로 홈 이동.
    await page.waitForURL((url) => url.pathname === '/');

    // 전제를 DB로 고정한다(C8과 같은 관례). 리터럴 'user'로 적지 않는다 — 기본값을 다른 값으로
    // 바꾸면 이 테스트가 "기본값이 무엇인지"를 다투게 되는데, 여기서 지켜야 할 것은 그게 아니라
    // **"판매자 역할이 아닌 계정도 /sell에 간다"**이다. 그래서 buyer/seller가 아님만 단언한다.
    const newRole = runPsql(
      `select p.role from profiles p join auth.users u on u.id = p.id where u.email='${email}'`,
    ).trim();
    expect(newRole, '신규 가입 계정에 role이 배정돼야 함(트리거 기본값)').not.toBe('');
    expect(
      ['buyer', 'seller'].includes(newRole),
      `C9는 역할선택 없이 가입한 계정을 검사한다 — 받은 role='${newRole}'이 구 역할값이면 전제가 깨진 것`,
    ).toBe(false);

    await page.goto('/sell');
    await expect(
      page.getByRole('heading', { name: '매물 등록' }),
      '신규 가입 계정도 /sell에서 매물 등록 폼을 봐야 함(에픽 14 최종 인수 조건)',
    ).toBeVisible();
    expect(
      new URL(page.url()).pathname,
      '신규 가입 계정도 /sell에 그대로 머물러야 함(홈 리다이렉트 없음)',
    ).toBe('/sell');
  } finally {
    // 이 테스트가 만든 계정만 지운다. profiles는 auth.users FK cascade로 함께 사라진다.
    runPsql(`delete from auth.users where email='${email}'`);
    const leftover = runPsql(`select count(*) from auth.users where email='${email}'`).trim();
    expect(leftover, 'C9가 만든 검증 계정이 남으면 안 됨(원복 증명)').toBe('0');
  }
});
