// Epic 11 마무리 인수조건 — 정식 스위트 승격판(2026-07-28, 대장 #182). 원래 일회성 감사
// 스펙(a-epic11-core.spec.ts)이 잡던 축(폰트 self-host 실제 로드, 브라우저→DB view_count
// 왕복, 랜딩 "전체 보기"·sold 제외·비로그인 42501 회귀)을 그대로 web/e2e/ 정식 스위트로
// 옮긴다 — 이 축은 다른 정식 스펙(nav-interactions·viewport-audit·image-fallback)이 보지
// 않는다.
import { test, expect } from '@playwright/test';
import { assertLocalSupabase, fetchOnSaleListingIdWithPhoto, runPsql } from './helpers';
import { PROJECT_NAMES } from './project-names';

// 운영 안전 가드 — 파일이 로드되는 즉시(테스트 실행 전) 확인한다. A4처럼 runPsql을 안 쓰는
// 케이스도 있어(로그인 없이 랜딩만 본다지만 시드 계정 유무 자체가 로컬/운영에 따라 달라
// 실패가 불투명해진다), runPsql 내부의 가드만으로는 이 파일 전체를 못 덮는다.
assertLocalSupabase();

// 이 감사는 데스크톱 뷰포트 축만 본다(모든 케이스가 [desktop] 설계) — mobile-390x844 프로젝트에서는
// 스킵해 중복 실행(특히 A2의 view_count 증가 중복)을 피한다. tablet-800x1024 프로젝트도 이 조건에
// 걸려 함께 스킵된다.
test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '이 감사는 desktop 프로젝트에서만 돈다.');
});

test.describe('Epic 11 core — 랜딩·view_count', () => {
  test('A1 [desktop] Pretendard self-host가 브라우저에서 실제로 작동한다 (11-0 AC2)', async ({ page }) => {
    const requestedUrls: string[] = [];
    page.on('request', (req) => requestedUrls.push(req.url()));

    await page.goto('/');
    // 웹폰트 로드가 끝날 때까지 대기(document.fonts.ready) — 그 시점까지 나간 요청을 위 리스너가 다 잡는다.
    await page.evaluate(() => document.fonts.ready.then(() => undefined));

    // 단언 ① cdn.jsdelivr.net 요청 0건.
    const jsdelivrRequests = requestedUrls.filter((u) => u.includes('cdn.jsdelivr.net'));
    expect(jsdelivrRequests, `cdn.jsdelivr.net 요청이 있으면 안 됨: ${JSON.stringify(jsdelivrRequests)}`).toEqual([]);

    // 단언 ② body의 computed fontFamily에 Pretendard 포함.
    // 대소문자 무시 매칭(테스트 코드 수정, 실측): next/font/local이 생성한 CSS family 이름은
    // layout.tsx의 소스 변수명(`const pretendard = localFont(...)`)을 그대로 가져다 써서
    // "pretendard"(소문자)로 나온다 — 브랜드 표기 "Pretendard"와 대소문자만 다를 뿐 실제로는
    // 같은 폰트가 적용된 것이므로 대소문자 구분 없이 확인한다.
    const fontFamily = await page.evaluate(() => getComputedStyle(document.body).fontFamily);
    expect(fontFamily.toLowerCase()).toContain('pretendard');

    // 단언 ③ 400/800 weight 둘 다 실제로 로드됨(document.fonts.check).
    const [check400, check800] = await page.evaluate(() => [
      document.fonts.check('400 16px Pretendard'),
      document.fonts.check('800 16px Pretendard'),
    ]);
    expect(check400, '400 weight Pretendard가 로드되지 않음').toBe(true);
    expect(check800, '800 weight Pretendard가 로드되지 않음').toBe(true);

    // 단언 ④ 로고 배지의 800 weight 글자("차")의 computed fontWeight === 800.
    // Logo.tsx: 배지 span(aria-hidden, font-extrabold=800)의 텍스트가 정확히 "차"이고,
    // 워드마크 span은 "차장님"(exact 매칭에서 제외됨) — header 안에 정확히 1개만 매칭된다.
    const badge = page.locator('header').getByText('차', { exact: true });
    await expect(badge).toBeVisible();
    const fontWeight = await badge.evaluate((el) => getComputedStyle(el).fontWeight);
    expect(fontWeight).toBe('800');
  });

  test('A2 [desktop] 매물 상세에 들어가면 view_count가 정확히 1 증가한다 (11-1 마지막 AC)', async ({ page }) => {
    const listingId = await fetchOnSaleListingIdWithPhoto();
    const before = Number(runPsql(`select view_count from listings where id='${listingId}';`));

    // ⚠️ 이 테스트가 이 매물을 방문하는 유일한 곳 — 방문은 1회만(라우트 캐시로 두 번째부턴
    // 서버 렌더가 생략될 수 있음).
    await page.goto(`/listings/${listingId}`);
    await expect(page.locator('main h1')).toBeVisible();
    await page.waitForTimeout(1000);

    const after = Number(runPsql(`select view_count from listings where id='${listingId}';`));
    expect(after, `view_count가 ${before}에서 ${before + 1}이 아니라 ${after}가 됨`).toBe(before + 1);
  });

  test('A3 [desktop] 목록·검색·랜딩을 열어도 view_count는 오르지 않는다 (11-1 마지막 AC의 반대편)', async ({
    page,
  }) => {
    // A2가 쓰는 매물과 겹치지 않는 별도 on_sale 매물(사진 유무 무관).
    const photoListingId = await fetchOnSaleListingIdWithPhoto();
    const listingId = runPsql(
      `select id from listings where status='on_sale' and id <> '${photoListingId}' order by id asc limit 1;`,
    );
    expect(listingId, '테스트용 별도 on_sale 매물을 찾지 못함').not.toBe('');

    const before = Number(runPsql(`select view_count from listings where id='${listingId}';`));

    await page.goto('/search');
    await page.waitForLoadState('networkidle');
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const after = Number(runPsql(`select view_count from listings where id='${listingId}';`));
    expect(after, `목록/검색/랜딩만 열었는데 view_count가 ${before}에서 ${after}로 변함`).toBe(before);
  });

  test('A4 [desktop] 랜딩의 "전체 보기"는 필터 없는 /search로 보낸다 (11-4 AC2)', async ({ page }) => {
    await page.goto('/');
    const allViewLinks = page.getByRole('link', { name: /전체 보기/ });
    // 인기·최신 두 단 각각 하나씩 — 2개가 아니면 이 감사가 검사 대상을 놓친 것이다.
    await expect(allViewLinks).toHaveCount(2);

    for (let i = 0; i < 2; i++) {
      await page.goto('/');
      const link = page.getByRole('link', { name: /전체 보기/ }).nth(i);
      await link.click();
      await page.waitForLoadState('networkidle');
      const url = new URL(page.url());
      expect(url.pathname, `${i}번째 "전체 보기" 클릭 후 경로`).toBe('/search');
      expect(url.search, `${i}번째 "전체 보기" 클릭 후 쿼리파라미터가 비어 있어야 함`).toBe('');
    }
  });

  test('A5 [desktop] 판매완료(sold) 매물은 인기·최신 어느 단에도 없다 (11-4 AC3, FR11)', async ({ page }) => {
    const soldIdsRaw = runPsql(`select id from listings where status='sold' order by id asc;`);
    const soldIds = new Set(
      soldIdsRaw
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
    );

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const hrefs = await page
      .locator('a[href^="/listings/"]')
      .evaluateAll((els) => els.map((el) => el.getAttribute('href')));
    const landingIds = new Set(
      hrefs.filter((h): h is string => !!h).map((h) => h.replace('/listings/', '')),
    );

    // 카드가 0개면 그 자체로 실패(측정 대상이 없으면 의미 없는 통과다).
    expect(landingIds.size, '랜딩에 매물 카드가 0개 — 이 케이스가 아무것도 검사하지 못함').toBeGreaterThan(0);

    const intersection = [...landingIds].filter((id) => soldIds.has(id));
    expect(intersection, `랜딩에 sold 매물이 섞여 있음: ${JSON.stringify(intersection)}`).toEqual([]);
  });

  test('A6 [desktop] 비로그인 랜딩이 42501 없이 인기 단을 렌더한다 (11-4 AC5, 대장 #134 회귀)', async ({
    page,
  }) => {
    const badResponses: string[] = [];
    const consoleErrors: string[] = [];
    page.on('response', (res) => {
      if (res.url().includes('127.0.0.1:55321') && res.status() >= 400) {
        badResponses.push(`${res.status()} ${res.url()}`);
      }
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    // 이 테스트는 login()을 한 번도 호출하지 않는다 — 브라우저 컨텍스트가 항상 비로그인 상태.
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 단언 ① Supabase REST 4xx/5xx 응답 0건.
    expect(badResponses, `Supabase REST 4xx/5xx 응답: ${JSON.stringify(badResponses)}`).toEqual([]);

    // 단언 ② "불러오지 못했습니다" 문구 없음.
    await expect(page.getByText('불러오지 못했습니다')).toHaveCount(0);

    // 단언 ③ 인기 섹션에 매물 카드 1개 이상.
    const popularSection = page.locator('section').filter({ has: page.getByRole('heading', { name: '지금 인기' }) });
    const popularCardCount = await popularSection.locator('a[href^="/listings/"]').count();
    expect(popularCardCount, '인기 섹션에 매물 카드가 0개').toBeGreaterThanOrEqual(1);

    // 단언 ④ 콘솔 에러 중 42501/permission denied 0건.
    const permissionErrors = consoleErrors.filter((t) => /42501|permission denied/i.test(t));
    expect(permissionErrors, `권한 에러 콘솔 로그: ${JSON.stringify(permissionErrors)}`).toEqual([]);
  });
});
