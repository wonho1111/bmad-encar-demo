// E2E 공용 헬퍼 — 여러 스펙 파일이 재사용하는 로그인·데이터 조회·단언 유틸.
// *.spec.ts 네이밍이 아니므로 Playwright 러너가 이 파일 자체를 테스트로 수집하지 않는다.
import type { Locator, Page } from '@playwright/test';
import { expect } from '@playwright/test';

// 시드 계정(supabase/seed-local/01_accounts.sql) — 로컬 스택 전용 고정 비밀번호(seller123,
// supabase/.env.seed). 운영 계정이 아니다.
export const SEED_USER = { email: 'buyer@test.com', password: 'seller123' };

/** 로그인 폼을 채우고 제출해, 로그인 후 화면(기본은 홈)까지 기다린다. */
export async function login(page: Page, email = SEED_USER.email, password = SEED_USER.password) {
  await page.goto('/login');
  await page.getByLabel('이메일').fill(email);
  await page.getByLabel('비밀번호').fill(password);
  await page.getByRole('button', { name: '로그인' }).click();
  // 로그인 성공 시 /login을 벗어난다(redirectedFrom 없으면 홈으로).
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
}

/**
 * 문서 전체가 뷰포트보다 가로로 넘치지 않는지 확인한다(D5·#84의 핵심 단언).
 * scrollWidth > clientWidth면 어딘가에 뷰포트보다 넓은 요소가 있다는 뜻이다.
 * (코드리뷰 patch: `#155`는 이 단언이 못 잡는다 — `/search`가 폭 ≤376px에서 만드는 가로
 * 스크롤인데, 이 매트릭스의 가장 좁은 프로젝트(mobile-390x844)보다도 좁아 구조적으로 관측
 * 범위 밖이다. #155는 별도 트리거로 계속 열려 있다.)
 */
export async function assertNoHorizontalOverflow(page: Page) {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth, `scrollWidth(${scrollWidth}) <= clientWidth(${clientWidth}) 이어야 함(가로 스크롤 없음)`).toBeLessThanOrEqual(
    clientWidth,
  );
}

/**
 * `display:grid` 컨테이너의 실제 렌더 열 수를 계산한다(computed `grid-template-columns`의
 * 트랙 개수를 센다 — Tailwind arbitrary variant가 실제로 의도한 브레이크포인트에서 이겼는지는
 * 클래스 존재가 아니라 **계산된 트랙 수**로만 확인할 수 있다, 과거 640/1100 순서 버그가 실측 사례).
 */
export async function assertGridColumns(locator: Locator, expectedCols: number) {
  const trackCount = await locator.evaluate((el) => {
    const cols = getComputedStyle(el).gridTemplateColumns;
    return cols.trim() === '' || cols === 'none' ? 0 : cols.trim().split(/\s+/).length;
  });
  expect(trackCount, `그리드 열 수는 ${expectedCols}이어야 함(실제: ${trackCount})`).toBe(expectedCols);
}

/**
 * 그리드 열 수를 확인하되, 매물이 0건이거나 조회가 실패해 그리드 자체가 안 그려지는 경우
 * (`PopularRecentGrid.tsx`의 빈 상태/에러 분기, `search/page.tsx`의 동일 패턴)를 로케이터
 * 타임아웃(불투명한 실패)이 아니라 **명시적으로** 구분한다(코드리뷰 patch) — `[role="list"]`가
 * 없으면 곧장 `.evaluate()`를 거는 대신, 먼저 빈 상태/에러 문구가 실제로 있는지 확인한다.
 *
 * **에러와 빈 상태를 같은 취급으로 묶지 않는다(코드리뷰 patch, B4).** 예전엔 두 문구를 한
 * 정규식(`/매물이 없습니다|불러오지 못했습니다/`)으로 합쳐 "그리드가 없으면 통과"로 쳤다 —
 * 그러면 `PopularRecentGrid.tsx:41`("매물을 불러오지 못했습니다.")·`search/page.tsx:199`
 * ("매물 목록을 불러오지 못했습니다")처럼 **매물 조회 자체가 실패한 상태**도 이 스토리의 핵심
 * 단언(4/2/1 그리드 재배치)을 아무것도 측정하지 않은 채 그냥 통과해 버렸다. 조회 실패는 "감사
 * 대상이 없어서 통과"가 아니라 **감사를 못 한 실패**다 — 에러 문구가 보이면 곧장 fail시킨다.
 * "매물이 없습니다" 류 **진짜 빈 상태**만 그리드 없이도 통과 가능한 결과로 인정하고, 그 문구조차
 * 없으면(그리드도 없고 에러도 없고 빈 상태 문구도 없음) "침묵 상태"로 역시 fail시킨다.
 */
export async function assertGridColumnsOrEmptyState(section: Locator, expectedCols: number) {
  const grid = section.locator('[role="list"]');
  const gridCount = await grid.count();
  if (gridCount === 0) {
    const errorVisible = await section
      .getByText(/불러오지 못했습니다/)
      .isVisible()
      .catch(() => false);
    if (errorVisible) {
      expect(
        false,
        '그리드가 없고 "불러오지 못했습니다" 에러 문구가 떴음 — 매물 조회가 실패해 그리드 열 수를 측정할 수 없음(빈 상태와 달리 이건 실패다)',
      ).toBe(true);
      return;
    }
    await expect(
      section.getByText(/매물이 없습니다/),
      '그리드도 없고 빈 상태·에러 문구도 없음(둘 다 아닌 침묵 상태 — PopularRecentGrid/search 분기 확인)',
    ).toBeVisible();
    return;
  }
  await assertGridColumns(grid.first(), expectedCols);
}

/**
 * 요소가 시각적으로 "한 줄"인지 확인한다(D5 — 세로화·줄바꿈 금지 규칙의 실측판).
 * 렌더된 높이가 1줄 분량(line-height + padding·border, 약간의 오차 허용)을 넘으면 줄바꿈이
 * 일어난 것으로 본다. **padding·border를 함께 계산에 넣는 이유(코드리뷰 patch로 실측 확정)**:
 * 이 함수를 `<p class="truncate">` 같은 여백 없는 텍스트 줄에만 쓸 때는 line-height 하나로
 * 충분했지만, 버튼(`px-4 py-2`처럼 수직 padding이 있는 요소)에 그대로 쓰면 정상적인 한 줄
 * 렌더도 line-height보다 커서(padding만큼) 거짓 실패가 난다 — 실측: "전송" 버튼 정상 렌더가
 * 38px인데 line-height*1.5(30px)를 넘어 red가 났다. padding·border를 더한 "이 요소의 정상
 * 한 줄 높이"를 기준선으로 삼아야 버튼·링크에도 같은 함수를 재사용할 수 있다.
 *
 * **오차 허용(1.4배)은 line-height에만 곱한다, padding·border엔 곱하지 않는다(코드리뷰
 * patch — 이전 `(lineHeight + padding + border) * 1.4`는 대수적으로 `padding >= 1.5 * lineHeight`인
 * 순간부터 2줄 렌더(`2L + P`)도 그대로 통과시켰다 — 정확히 이 함수가 막아야 할 패딩 큰 버튼에서
 * 벌어지는 경우다). "정상 한 줄 높이"는 `lineHeight*1.4 + padding + border`로 고정하고, 그
 * 위로 올라가면(줄바꿈이든 뭐든) 무조건 fail이다. 그리고 애초에 렌더가 안 된
 * 요소(`display:none` 등)가 0인 채로 통과하지 않도록 높이가 0보다 큰지부터 먼저 확인한다.
 */
export async function assertSingleLine(locator: Locator) {
  const { height, expectedSingleLineHeight } = await locator.evaluate((el) => {
    const style = getComputedStyle(el);
    const parsedLineHeight = parseFloat(style.lineHeight);
    // line-height:normal 등 숫자로 안 파싱되면 font-size의 1.4배를 근사치로 쓴다.
    const lineHeight = Number.isFinite(parsedLineHeight) ? parsedLineHeight : parseFloat(style.fontSize) * 1.4;
    const verticalExtras =
      (parseFloat(style.paddingTop) || 0) +
      (parseFloat(style.paddingBottom) || 0) +
      (parseFloat(style.borderTopWidth) || 0) +
      (parseFloat(style.borderBottomWidth) || 0);
    return {
      height: el.getBoundingClientRect().height,
      // 오차 허용은 line-height 자체에만 곱하고, padding·border는 그대로 더한다(위 주석).
      expectedSingleLineHeight: lineHeight * 1.4 + verticalExtras,
    };
  });
  expect(height, `요소 높이가 0 — display:none 등으로 렌더되지 않아 줄바꿈 여부를 판단할 수 없음`).toBeGreaterThan(0);
  expect(
    height,
    `한 줄 높이(line-height*1.4 + padding·border = ${expectedSingleLineHeight.toFixed(1)}px) 이내여야 하는데 ${height.toFixed(1)}px — 줄바꿈 발생`,
  ).toBeLessThanOrEqual(expectedSingleLineHeight);
}

/** 로컬 Supabase REST(PostgREST)로 사진이 있는 판매중 매물 id 하나를 조회한다(anon 키 — 열람 경로와 동일 권한). */
export async function fetchOnSaleListingIdWithPhoto(): Promise<string> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error('NEXT_PUBLIC_SUPABASE_URL/ANON_KEY가 없습니다 — web/.env.local을 확인하세요.');
  }
  // listing_images에 대한 anon RLS는 on_sale 매물의 행만 보여준다(0012 마이그레이션) — 그래서
  // 이 한 쿼리만으로 "판매중 + 사진 있음"이 동시에 보장된다.
  // order를 명시한다(코드리뷰 patch) — 정렬 없는 limit=1은 실행마다 다른 행을 돌려줄 수 있어
  // 실패가 재현되지 않는다(B4). listing_id 오름차순으로 고정해 같은 매물을 결정적으로 고른다.
  const res = await fetch(`${url}/rest/v1/listing_images?select=listing_id&order=listing_id.asc&limit=1`, {
    headers: { apikey: anonKey, Authorization: `Bearer ${anonKey}` },
  });
  if (!res.ok) {
    throw new Error(`listing_images 조회 실패: ${res.status} ${await res.text()}`);
  }
  const rows = (await res.json()) as Array<{ listing_id: string }>;
  if (rows.length === 0) {
    throw new Error('사진이 있는 판매중 매물이 로컬 DB에 없습니다 — scripts/seed-local.sh를 실행하세요.');
  }
  return rows[0].listing_id;
}

// /ai/search 목업 응답에 쓸 매물 카드 최소 계약(ListingCardData 7필수필드 + image_path/count).
export type MockAiListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  mileage: number;
  region: string;
  image_path?: string;
  image_count?: number;
};

// mockAiSearch가 돌려주는 핸들 — 목업이 실제로 요청을 가로챘는지 스펙이 단언할 수 있게 한다
// (코드리뷰 patch, 아래 mockAiSearch 주석 참조).
export type MockAiSearchHandle = {
  /** 이 목업이 지금까지 실제로 fulfill한 `/ai/search` 요청 수. */
  requestCount(): number;
};

/**
 * `/ai/search` 호출을 가로채 고정 응답을 돌려준다 — 실제 FastAPI·Gemini 호출 없이(비용 없이)
 * ChatAssistant가 매물 카드를 N장 렌더한 상태를 만든다(뷰포트 감사·이미지 폴백 스펙 공용).
 * 이 목업이 검증하는 것은 **프런트엔드 레이아웃**이지 AI 응답 품질이 아니다 — 백엔드 계약(api/app/schemas/ai.py)
 * 자체는 api 쪽 pytest(결정론적 단위테스트)가 별도로 지킨다(project-context §12).
 *
 * **끝 슬래시 정규화(코드리뷰 patch)** — `web/src/lib/api/aiSearch.ts:50`의 `getApiBaseUrl()`이
 * `base.replace(/\/+$/, '')`로 끝 슬래시를 지우고 호출하는데, 이 헬퍼가 그걸 안 맞추면
 * `NEXT_PUBLIC_API_BASE_URL`에 끝 슬래시가 붙은 환경에서 `page.route`가 앱이 실제로 부르는
 * URL과 다른 문자열에 등록돼 **한 번도 가로채지 못한다** — 그러면 스펙이 실제 백엔드(과금·
 * 비결정적)로 새어나가는데도 조용히 통과했다. 아래 `requestCount()`가 이 실패를 드러낸다:
 * 호출부가 렌더가 끝난 뒤 `requestCount() > 0`을 단언하면, 가로채지 못한 경우 0으로 남아
 * 즉시 잡힌다.
 */
export async function mockAiSearch(
  page: Page,
  listings: MockAiListing[],
  answer = '테스트 응답',
): Promise<MockAiSearchHandle> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
  const normalizedBase = apiBase.replace(/\/+$/, '');
  let count = 0;
  await page.route(`${normalizedBase}/ai/search`, async (route) => {
    count += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ answer, listings }),
    });
  });
  return { requestCount: () => count };
}

/**
 * `loading="lazy"` 이미지를 전량 뷰포트에 넣기 위해 문서 끝까지 여러 번 스크롤한다(#73 —
 * 화면 밖 카드는 애초에 이미지 요청 자체가 안 나가므로, 스크롤 없이는 폴백이 시험되지 않은
 * 채로 green을 자칭하게 된다 — 2026-07-21 코드리뷰가 지적한 바로 그 함정).
 *
 * **좌표계를 한쪽으로 통일한다(코드리뷰 patch)** — 예전엔 문서 높이를 `document.body.scrollHeight`로
 * 재면서 "바닥 도달"은 `window.scrollY + innerHeight`(뷰포트 기준, `documentElement`가 스크롤되는
 * 값)와 비교했다. 이 앱의 셸이 `min-h-screen flex`라 `body`가 `documentElement`보다 짧아질 수 있어,
 * 실제로는 안 내려갔는데도 `reachedBottom`이 먼저 true가 되어 아래쪽 lazy 이미지가 뷰포트에
 * 들어가기 전에 스크롤을 멈춰버렸다 — 이 헬퍼가 막으려던 바로 그 `#73` 사각지대를 헬퍼 스스로
 * 재현하는 셈이었다. `document.documentElement.scrollHeight`로 양쪽을 통일한다.
 *
 * 반복 안에 실제로 문서 끝(scrollY + innerHeight ≈ scrollHeight)에 닿았는지까지 확인한다
 * (코드리뷰 patch) — 그냥 돌고 조용히 멈추면, 콘텐츠가 그보다 많이 자랄 때 뒷부분 카드가
 * "시험되지 않은 채 통과"하는 #73과 똑같은 함정을 이 헬퍼 스스로 재현하게 된다. **바닥 도달뿐
 * 아니라 높이가 안정됐는지(`scrollHeight === lastHeight`)도 함께 요구한다(코드리뷰 patch)** —
 * 도달만 보면, 마지막 반복에도 콘텐츠가 계속 자라는 중(무한 스크롤 등)인데 그 순간 우연히
 * `reachedBottom`이 true인 경우까지 "완전히 스크롤됨"으로 조용히 통과시킨다.
 *
 * **바닥으로 곧장 점프하지 않고 뷰포트 높이의 0.8배씩 전진한다(코드리뷰 patch, P1)** — 예전엔
 * 매 반복 `scrollTo(0, doc.scrollHeight)`로 바닥까지 한 번에 점프했는데, 그러면 중간 대역
 * 카드는 뷰포트에 한 번도 걸치지 않은 채 건너뛰어져 `loading="lazy"` 이미지 요청 자체가 안
 * 나간다 — `#73`이 막으려던 바로 그 사각지대를 이 헬퍼 스스로 재현한 것이다(실측: `/search`
 * 95장 카드 중 abort가 82건만 걸렸고, 8장은 요청 자체가 안 나가 `naturalWidth===0`도 아닌 채
 * "완전히 시험되지 않은" 상태로 green을 통과했다). 0.8배(1.0이 아니라)는 다음 스텝의 뷰포트가
 * 이전 스텝과 20% 겹치게 해 스텝 경계에 걸친 카드도 확실히 한 번은 뷰포트 안에 들어오게 한다.
 *
 * **반복 상한을 매직넘버 15로 고정하지 않는다(코드리뷰 patch, P1)** — 문서 높이 대비 스텝 수로
 * 상한을 계산해, 카드가 많아 문서가 길어져도(예: `/search` 95장) 캡이 자동으로 함께 늘어난다.
 */
export async function scrollFullPage(page: Page) {
  const { initialScrollHeight, initialInnerHeight } = await page.evaluate(() => ({
    initialScrollHeight: document.documentElement.scrollHeight,
    initialInnerHeight: window.innerHeight,
  }));
  // 필요 스텝 수(문서높이 / 0.8뷰포트)에 여유를 2배 두고, 짧은 페이지에서도 최소 15회는 보장한다.
  const maxIterations = Math.max(15, Math.ceil(initialScrollHeight / (initialInnerHeight * 0.8)) * 2);

  let lastHeight = -1;
  let reachedBottom = false;
  let stabilized = false;
  for (let i = 0; i < maxIterations; i++) {
    const state = await page.evaluate(() => {
      const doc = document.documentElement;
      window.scrollBy(0, window.innerHeight * 0.8);
      return {
        scrollHeight: doc.scrollHeight,
        scrollY: window.scrollY,
        innerHeight: window.innerHeight,
      };
    });
    await page.waitForTimeout(150);
    // 1px 오차 허용(서브픽셀 레이아웃) — scrollY + 뷰포트 높이가 문서 높이에 도달했으면 바닥이다.
    reachedBottom = state.scrollY + state.innerHeight >= state.scrollHeight - 1;
    stabilized = state.scrollHeight === lastHeight;
    if (stabilized && reachedBottom) break;
    lastHeight = state.scrollHeight;
  }
  expect(
    reachedBottom && stabilized,
    `문서 끝까지 스크롤하지 못했거나(reachedBottom=${reachedBottom}) 높이가 아직 안정되지 않음(stabilized=${stabilized}, ${maxIterations}회 반복 초과) — 콘텐츠가 예상보다 길어 아래쪽 카드가 시험되지 않았을 수 있음(#73과 동일한 함정)`,
  ).toBe(true);
}

/**
 * 매물 사진 `<img>`(카드·갤러리 공용, `data-testid="listing-photo"`) 중 로드가 끝났는데
 * `naturalWidth===0`(깨진 이미지)인 것이 하나도 없는지 확인한다 — 2겹 폴백(onError + ref
 * 콜백)이 실제로 발화했는지를 보는 단언이지, 이미지가 있는지 없는지를 보는 게 아니다(B4).
 * 스타일 클래스(`object-cover`)가 아니라 전용 `data-testid`로 찾는다 — 클래스가 리팩터로
 * 사라지면 셀렉터가 0건 매칭해 이 검사가 조용히 통과(거짓 양성)해 버리기 때문(코드리뷰 patch).
 */
export async function assertNoBrokenImages(page: Page) {
  const brokenCount = await page.evaluate(() => {
    const imgs = Array.from(document.querySelectorAll<HTMLImageElement>('img[data-testid="listing-photo"]'));
    return imgs.filter((img) => img.complete && img.naturalWidth === 0).length;
  });
  expect(brokenCount, '깨진 이미지(로드 끝났는데 naturalWidth=0)가 0개여야 함').toBe(0);
}

/**
 * "사진 준비중" 플레이스홀더가 "전량" 발동했는지 확인한다(코드리뷰 patch, P2) — 예전엔
 * `count > 0`만 봐서, abort와 무관하게 원래 사진이 없는 카드의 플레이스홀더만으로도 통과할 수
 * 있었다(실측: `/search` 95장 중 5장은 애초에 사진이 없어 abort 없이도 플레이스홀더가 뜬다).
 * "전량"을 실제로 보려면 두 가지를 함께 봐야 한다:
 *   ① 로드 실패한 사진 `<img>`는 `ListingCardImage`/`ListingGallery`가 언마운트하므로, abort
 *      이후 `img[data-testid="listing-photo"]`가 하나도 남아 있지 않아야 한다(살아남은 `<img>`가
 *      있으면 그 카드는 아직 폴백이 발화하지 않았다는 뜻).
 *   ② 카드 그리드(`/search`·`/ai`)처럼 "카드 수"가 명확한 화면은 플레이스홀더 개수가 카드 수와
 *      정확히 같아야 "전량"이다 — `expectedCardCount`를 넘기면 이 정확 일치를 확인한다.
 * 상세(`ListingGallery`)는 현재 보이는 사진 하나만 마운트하는 구조라(호출부 주석 참조) "카드 수"라는
 * 단위 자체가 없다 — `expectedCardCount`를 생략하면 ①만 확인하고, 플레이스홀더가 최소 1개는
 * 떴는지(발화 자체는 했는지)만 본다.
 */
export async function assertPlaceholderFallbackFired(page: Page, expectedCardCount?: number) {
  const remainingPhotos = await page.locator('img[data-testid="listing-photo"]').count();
  expect(
    remainingPhotos,
    `abort 상태인데도 사진 <img>가 ${remainingPhotos}개 남아 있음 — 아직 폴백이 발화하지 않은 카드가 있다는 뜻(전량 발동 아님)`,
  ).toBe(0);
  const placeholderCount = await page.getByText('사진 준비중').count();
  if (expectedCardCount === undefined) {
    expect(placeholderCount, '이미지 abort 상태에서 "사진 준비중" 플레이스홀더가 최소 1개는 떠야 함(폴백 발화 실측)').toBeGreaterThan(0);
    return;
  }
  expect(
    placeholderCount,
    `플레이스홀더 개수(${placeholderCount})가 카드 수(${expectedCardCount})와 다름 — "전량" 발동이 아니라 일부만 발동했을 수 있음`,
  ).toBe(expectedCardCount);
}

/**
 * N장짜리 목업 매물 배열을 만든다(id는 유니크 UUID 모양이면 충분 — 실제 DB 존재 여부는 무관).
 * 마지막 세그먼트를 `padStart(12, '0')`로 고정 폭 채운다 — 원래 `...00000${i}` 템플릿은 `i`의
 * 자릿수만큼 세그먼트가 길어져 `count>=11`(i=10)부터 13자리가 되어 UUID 모양이 깨졌다(코드리뷰
 * patch). 지금은 4/6개만 호출하지만 어떤 count에서도 안전하게 고정한다.
 */
export function buildMockListings(count: number, imagePath = 'mock/photo.webp'): MockAiListing[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`,
    manufacturer: '현대',
    model: `테스트카 ${i + 1}`,
    year: 2022,
    price: 20_000_000 + i * 1_000_000,
    mileage: 30_000,
    region: '서울',
    image_path: imagePath,
    image_count: 1,
  }));
}
