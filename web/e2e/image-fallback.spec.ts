// 이미지 전면 장애 재현 (#73/#86) — 목록(`/search`)·상세(`/listings/[id]`)·`/ai` 세 소비처 모두에서
// `**/storage/v1/object/public/**` 요청을 abort시키고, 매물 조회는 살려둔 채(#73 실험과 동일 설계 —
// "매물은 뜨는데 사진만 전면 실패") 2겹 폴백(onError + ref 콜백)이 실제로 발화하는지 확인한다.
//
// `loading="lazy"` 때문에 화면 밖 카드는 이미지 요청 자체가 안 나간다(2026-07-21 코드리뷰가 지적한
// 함정 — 90장 중 43장만 시험되고 나머지는 "폴백이 안 뜬 것"이 아니라 "시험되지 않은 것"이었다).
// 그래서 각 화면에서 문서 끝까지 스크롤해 전량을 뷰포트에 넣은 뒤에 측정한다.
//
// 이 스펙 하나로 #86("재실행 가능한 형태")도 함께 닫는다 — 이 파일 자체가 그 재실행 가능한 산출물이다.
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import {
  assertNoBrokenImages,
  assertPlaceholderFallbackFired,
  buildMockListings,
  fetchOnSaleListingIdWithPhoto,
  login,
  mockAiSearch,
  scrollFullPage,
} from './helpers';
import { PROJECT_NAMES } from './project-names';

// abort 실험이 실제로 발동했는지 스펙이 단언할 수 있게 요청 수를 센다(코드리뷰 patch, D1) —
// `assertNoBrokenImages`는 `img[data-testid="listing-photo"]` 중 깨진 것만 세는데,
// `ListingCardImage`는 실패가 확정되면 그 `<img>` 자체를 언마운트하므로 **0개 깨짐이 "폴백이
// 잘 됐다"와 "애초에 abort가 한 번도 안 걸렸다(storage URL 패턴이 바뀌었거나 요청이 없었다)"를
// 구별하지 못한다** — 0-of-0이 조용히 통과한다. abort 카운터는 이 실험이 실제로 가로챈
// 요청 수를 네트워크 계층에서 직접 세므로, 카운터가 0이면 그 자체로 "매물 사진 요소가 애초에
// 없었거나 실험이 아예 안 걸렸다"는 뜻이라 0-of-0을 막는다.
const abortCounts = new WeakMap<Page, { count: number }>();

function getAbortCount(page: Page): number {
  return abortCounts.get(page)?.count ?? 0;
}

// 3개 뷰포트 각각에서 반복할 필요는 없다(전면 장애 재현은 뷰포트가 아니라 소비처가 변수) —
// 데스크톱 프로젝트 하나에서만 돈다(가장 넓어서 한 화면에 더 많은 카드가 노출되고 스크롤 횟수가 적다).
test.beforeEach(async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '소비처가 변수이지 뷰포트가 변수가 아니므로 한 프로젝트에서만 실행');
  const counter = { count: 0 };
  abortCounts.set(page, counter);
  // 이미지 스토리지 요청만 abort — 매물 데이터 조회(REST)는 그대로 통과시킨다(#73의 정확한 조건:
  // "매물은 뜨는데 사진만 전면 실패").
  await page.route('**/storage/v1/object/public/**', (route) => {
    counter.count += 1;
    return route.abort();
  });
});

test('/search — 이미지 전면 장애에도 깨진 아이콘 0개, 플레이스홀더 전량 발동', async ({ page }) => {
  await page.goto('/search');
  await page.waitForLoadState('networkidle');
  await scrollFullPage(page);
  expect(
    getAbortCount(page),
    'abort 실험이 한 번도 안 걸렸음(0회) — storage URL 패턴이 바뀌었거나 매물 사진 요소 자체가 없었을 수 있음(0-of-0 침묵 통과 방지)',
  ).toBeGreaterThan(0);
  await assertNoBrokenImages(page);
  // 카드 수 = listing-meta 개수(ListingCard마다 정확히 1개 렌더, 코드리뷰 patch) — "전량" 발동을
  // 판정하려면 abort와 무관하게 존재하는 카드 총수를 알아야 한다(P2).
  const cardCount = await page.locator('[data-testid="listing-meta"]').count();
  await assertPlaceholderFallbackFired(page, cardCount);
});

test('상세(/listings/[id]) — 이미지 전면 장애에도 깨진 아이콘 0개, 플레이스홀더 전량 발동', async ({ page }) => {
  const id = await fetchOnSaleListingIdWithPhoto();
  await page.goto(`/listings/${id}`);
  await page.waitForLoadState('networkidle');
  await scrollFullPage(page);
  expect(
    getAbortCount(page),
    'abort 실험이 한 번도 안 걸렸음(0회) — storage URL 패턴이 바뀌었거나 매물 사진 요소 자체가 없었을 수 있음(0-of-0 침묵 통과 방지)',
  ).toBeGreaterThan(0);
  await assertNoBrokenImages(page);
  // 상세(ListingGallery)는 현재 보이는 사진(urls[index]) 하나만 마운트하는 구조라 "카드 수"라는
  // 단위가 없다 — 캐러셀의 2..N번째 사진은 이 스펙이 시험하지 못한다(측정된 한계, B4).
  await assertPlaceholderFallbackFired(page);
});

test('/ai — 이미지 전면 장애에도 깨진 아이콘 0개, 플레이스홀더 전량 발동', async ({ page }) => {
  await login(page);
  const mock = await mockAiSearch(page, buildMockListings(6));
  await page.goto('/ai');
  await page.getByLabel('AI 검색 질의 입력').fill('3천만원 이하 SUV');
  await page.getByRole('button', { name: '전송' }).click();
  await page.getByText('테스트 응답').waitFor();
  expect(mock.requestCount(), '/ai/search 목업이 한 번도 호출되지 않음 — 실 백엔드로 새어나갔을 수 있음').toBeGreaterThan(0);
  await scrollFullPage(page);
  expect(
    getAbortCount(page),
    'abort 실험이 한 번도 안 걸렸음(0회) — storage URL 패턴이 바뀌었거나 매물 사진 요소 자체가 없었을 수 있음(0-of-0 침묵 통과 방지)',
  ).toBeGreaterThan(0);
  await assertNoBrokenImages(page);
  // 카드 수 = listing-meta 개수(ListingCard마다 정확히 1개 렌더, 코드리뷰 patch) — "전량" 발동을
  // 판정하려면 abort와 무관하게 존재하는 카드 총수를 알아야 한다(P2).
  const cardCount = await page.locator('[data-testid="listing-meta"]').count();
  await assertPlaceholderFallbackFired(page, cardCount);
});
