// 반응형 뷰포트 감사 본체 (spec-11-5) — FR36/D5: 랜딩·`/search`·상세·`/ai` 4화면 × 3뷰포트에서
// 그리드 재배치(4/2/1열)와 가로스크롤 없음을 자동으로 잡는다. 지금까지 이 레포엔 Playwright
// 스펙이 0개였다(#86) — 이 파일이 첫 스펙이다.
//
// "그리드 열수 재배치" 단언은 실제로 카드 그리드를 쓰는 화면(랜딩·`/search`, `ResponsiveGrid` 컴포넌트)에만
// 적용한다 — 상세(`/listings/[id]`)는 2열 정보/요약 셸이고 `/ai`는 카드가 있어도 세로 리스트라 D5의
// "4/2/1 그리드"에 해당하지 않는다(project-context 규칙13 원문·`ResponsiveGrid.tsx` 주석 참조). 다만
// "가로스크롤 없음"은 프로젝트 헤더 주석의 "이 스토리는 감사(assert)이지 재설계가 아니다" 원칙에 따라
// 4화면 전부에서 확인한다(AC1 문구가 요구하는 최소 교집합).
//
// 랜딩(`/`)은 그리드가 **두 개**다(`PopularRecentGrid.tsx` — "지금 인기"·"방금 올라온 매물").
// 코드리뷰 patch: 예전엔 `[role="list"]`의 `.first()`만 재서 두 번째("최신") 그리드의 열 수가
// 한 번도 확인되지 않았다 — 각 섹션을 제목(heading)으로 스코프해 **둘 다** 확인한다.
import { expect, test } from '@playwright/test';
import {
  assertGridColumnsOrEmptyState,
  assertNoHorizontalOverflow,
  assertSingleLine,
  buildMockListings,
  fetchChatRoomIdForSeedUser,
  fetchOnSaleListingIdWithPhoto,
  login,
  mockAiSearch,
} from './helpers';

// 뷰포트별 기대 그리드 열 수 — project-context 규칙13(D5): ≥1100=4열·640~1099=2열·<640=1열.
// **프로젝트 이름이 아니라 실제 viewport 폭으로 판정한다(코드리뷰 patch, P6)** — 예전엔
// `projectName.startsWith('desktop'|'tablet'|'mobile')`로 이름 문자열을 봤는데, 프로젝트
// 이름은 그대로 두고 `playwright.config.ts`의 viewport 값만 바꾸면(예: desktop을 900px로) 이
// 매칭이 렌더되는 실제 폭과 무관한 열 수를 기대값으로 계속 내놓는다 — 이름과 폭이 어긋나도
// 아무도 모른 채 조용히 통과한다. `testInfo.project.use.viewport`에서 폭을 직접 읽는다.
function expectedColsFor(testInfo: import('@playwright/test').TestInfo): number {
  const viewport = testInfo.project.use.viewport;
  // 조용히 기본값으로 처리하지 않는다(코드리뷰 patch) — viewport 설정 자체가 없으면(예: 디바이스
  // 프리셋만 쓰고 커스텀 viewport를 빼먹음) 무엇을 기대해야 할지 판단할 근거가 없다.
  if (!viewport) {
    throw new Error(
      `Playwright 프로젝트 "${testInfo.project.name}"에 viewport 설정이 없음 — expectedColsFor는 실제 렌더 폭을 알아야 D5 열 수를 판정할 수 있음`,
    );
  }
  if (viewport.width >= 1100) return 4;
  if (viewport.width >= 640) return 2;
  return 1;
}

// 카드 내부 가로 배치 세로화 없음(D5) — 컨테이너 안 첫 카드의 meta 줄(주행거리·연료·지역)이
// 실제로 한 줄인지 실측한다(클래스 존재가 아니라 렌더된 높이로 확인, B4). `data-testid`로 찾는다
// (코드리뷰 patch) — `.count()`로 감싸 0건이면 조용히 스킵하던 예전 방식은 이 검사가 지키려는
// `whitespace-nowrap` 클래스 자체가 리팩터로 사라져도(D5 회귀) "0건이라 통과"로 속았다.
// 여기서는 로케이터를 그대로 assertSingleLine에 넘긴다 — 요소가 없으면 `.evaluate()`가 기본
// 타임아웃까지 기다리다 명시적으로 실패한다(스킵이 아니라 실패).
//
// **이 검사가 실제로 보는 것 vs 안 보는 것(코드리뷰 patch, B4 실측 — P3)** — 여기서 재는
// `[data-testid="listing-meta"]`는 `truncate whitespace-nowrap`(Tailwind `truncate`가 이미
// `white-space:nowrap`을 포함)이라 **구조적으로 줄바꿈이 불가능한 요소**다. 즉 이 검사가 실제로
// 잡는 것은 "줄바꿈이 일어났는지"가 아니라 "그 truncate 계약(더 이상 접히지 않는다는 보장) 자체가
// 깨졌는지"다 — 아래 `assertTruncatesNotWraps`가 그 계약을 white-space/text-overflow로 직접
// 확인한다. 반면 D5가 접힘 예시로 든 진짜 후보(신뢰속성 뱃지 — `TrustAttributes` variant="card",
// `flex flex-wrap`)는 2026-08-05부터 카드 본문 흐름 밖으로 빠져 사진 위 절대배치로 겹친다
// (`web/src/components/listings/TrustAttributes.tsx`) — 줄바꿈 자체는 그대로 의도된 동작(3개
// 뱃지가 좁은 폭에서 2줄로 접혀도 사진 밖으로 넘치지만 않으면 정상)이라 이 스펙의 관측 대상이
// 아니다(대장에 등재됨, docs/tech-debt.md).
async function assertFirstCardMetaLineSingleLine(container: import('@playwright/test').Locator) {
  const firstCard = container.locator('[role="listitem"]').first();
  // `.first()`를 세기 전 개수부터 확인한다(코드리뷰 patch, P5) — `.first()`로 먼저 좁히면
  // count가 항상 0 또는 1이 되어 "카드 안에 meta 줄이 중복 렌더됐다" 같은 회귀를 못 잡는다.
  const metaLineLocator = firstCard.locator('[data-testid="listing-meta"]');
  await expect(
    metaLineLocator,
    '카드 meta 줄(data-testid="listing-meta")이 정확히 1개가 아님 — 그리드가 비었거나 testid가 사라졌거나(0개), 같은 카드 안에 중복 렌더됐을 수 있음(코드리뷰 patch, P5)',
  ).toHaveCount(1);
  const metaLine = metaLineLocator.first();
  await assertSingleLine(metaLine);
  await assertTruncatesNotWraps(metaLine);
}

/**
 * `truncate` 계약(white-space:nowrap + text-overflow:ellipsis)이 실제로 살아 있는지 확인한다
 * (코드리뷰 patch, P3) — 시드 문자열이 짧으면 `truncate` 클래스를 통째로 지워도 우연히 한 줄
 * 높이 안에 들어가 `assertSingleLine`만으로는 회귀를 못 잡는다. computed style을 직접 봐서,
 * 클래스가 사라지는 순간 문자열 길이와 무관하게 fail하게 만든다.
 */
async function assertTruncatesNotWraps(locator: import('@playwright/test').Locator) {
  const { whiteSpace, textOverflow } = await locator.evaluate((el) => {
    const style = getComputedStyle(el);
    return { whiteSpace: style.whiteSpace, textOverflow: style.textOverflow };
  });
  expect(whiteSpace, `white-space가 nowrap이 아님(${whiteSpace}) — truncate 클래스가 사라지면 줄바꿈이 다시 가능해짐`).toBe('nowrap');
  expect(textOverflow, `text-overflow가 ellipsis가 아님(${textOverflow}) — truncate 클래스가 사라졌을 수 있음`).toBe('ellipsis');
}

test.describe('그리드 재배치 + 가로스크롤 없음 — 랜딩(/)', () => {
  // PopularRecentGrid.tsx의 두 <section> 제목 그대로 — 각 섹션을 heading으로 스코프해서 본다.
  const LANDING_SECTION_TITLES = ['지금 인기', '방금 올라온 매물'];

  test('랜딩 — 인기·최신 두 그리드 각각의 열 수와 카드 내부 무결성', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await assertNoHorizontalOverflow(page);

    for (const title of LANDING_SECTION_TITLES) {
      const section = page.locator('section').filter({ has: page.getByRole('heading', { name: title }) });
      // 필터된 로케이터가 정확히 1개인지 먼저 확인한다(코드리뷰 patch) — 바깥 <section>이
      // 두 제목을 모두 감싸는 형태로 마크업이 바뀌면 `.filter()`가 그 바깥 section까지 함께
      // 매칭해 `.first()`가 매번 같은(잘못된) 요소를 골라버린다 — 예전에 실제로 겪은 버그와
      // 같은 종류라 여기서 구조적으로 막는다.
      await expect(
        section,
        `"${title}" 섹션을 감싸는 <section>이 정확히 1개여야 함(0개 또는 중복 매칭 시 그리드를 잘못 측정함)`,
      ).toHaveCount(1);
      await assertGridColumnsOrEmptyState(section, expectedColsFor(testInfo));
      await assertFirstCardMetaLineSingleLine(section);
    }
  });
});

test.describe('그리드 재배치 + 가로스크롤 없음 — /search', () => {
  test('/search — 그리드 열 수와 카드 내부 무결성', async ({ page }, testInfo) => {
    await page.goto('/search');
    await page.waitForLoadState('networkidle');
    await assertNoHorizontalOverflow(page);

    const main = page.locator('main');
    await assertGridColumnsOrEmptyState(main, expectedColsFor(testInfo));
    await assertFirstCardMetaLineSingleLine(main);
  });
});

test.describe('상세(/listings/[id]) — 가로스크롤 없음 + CTA 무결성', () => {
  test('사진 있는 판매중 매물 상세', async ({ page }) => {
    const id = await fetchOnSaleListingIdWithPhoto();
    await page.goto(`/listings/${id}`);
    await page.waitForLoadState('networkidle');
    await assertNoHorizontalOverflow(page);

    // D5: 문의 CTA(비로그인 방문이라 "로그인하고 문의하기" — InquiryCta.tsx의 anon 분기)가
    // 데스크톱 sticky aside·모바일 하단 고정 바 중 실제로 "보이는" 쪽에서 줄바꿈 없이 한 줄을
    // 유지하는지 확인한다(코드리뷰 patch — 기존엔 detail/ai 어느 쪽에도 카드 밖 인터랙티브
    // 요소의 D5 단언이 없었다). 두 배치 모두 DOM엔 항상 있으므로(Tailwind가 display로만 전환)
    // `:visible`로 실제 렌더된 인스턴스만 고른다. `data-testid`로 찾는다(코드리뷰 patch) —
    // 텍스트·클래스 기반 셀렉터가 0건이면 조용히 스킵하던 예전 방식을 없앤다: 못 찾으면 실패한다.
    // `.first()`를 세기 전 개수부터 확인한다(코드리뷰 patch, P5) — `.first()`로 먼저 좁히면
    // count가 항상 0 또는 1이라 "데스크톱 aside·모바일 하단 바가 동시에 보인다" 같은 브레이크포인트
    // 회귀(2개 이상 보임)를 못 잡는다.
    const inquiryCtaVisible = page.locator('[data-testid="inquiry-cta"]:visible');
    await expect(
      inquiryCtaVisible,
      '문의 CTA(data-testid="inquiry-cta")가 정확히 1개 보이지 않음(0개=안 보임, 2개 이상=데스크톱 aside·모바일 하단 바가 동시에 보이는 브레이크포인트 회귀, 코드리뷰 patch P5) — InquiryCta의 anon 분기·lg:block/lg:hidden 전환을 확인할 것',
    ).toHaveCount(1);
    const contactCta = inquiryCtaVisible.first();
    await assertSingleLine(contactCta);
  });
});

test.describe('채팅방(/chat/[roomId]) — 가로 오버플로 없음 (대장 #169, Story 12.3)', () => {
  test('로그인 사용자, 시드 채팅방 진입', async ({ page }) => {
    await login(page);
    const roomId = fetchChatRoomIdForSeedUser();
    await page.goto(`/chat/${roomId}`);
    await page.waitForLoadState('networkidle');
    await assertNoHorizontalOverflow(page);
    // #84·#169와 동일 원인(mx-auto 부모의 max-content 계산이 input 기본 size 힌트를 반영) — 입력창이
    // 2줄로 밀리지 않는지 실측한다(D5).
    await assertSingleLine(page.getByLabel('메시지 입력'));
  });
  // ⚠️ 이 케이스가 **안 보는 것**: 시드 방의 메시지는 전부 짧아(최대 20자) **버블** 오버플로는
  //   여기서 잡히지 않는다. 코드리뷰 중 긴 URL 한 건을 실제로 넣어보니 위 단언이 red가 됐다
  //   (scrollWidth 672 > clientWidth 390 — 공백 없는 문자열은 `whitespace-pre-wrap`만으로는 안
  //   쪼개진다). 그 조건을 이 스위트 안에서 만들려면 공유 로컬 DB에 행을 넣어야 하는데, 이 파일은
  //   3개 뷰포트 프로젝트가 **동시에** 도는 구조라 한쪽의 삽입이 다른 쪽 읽기에 새어 들어가
  //   무관한 케이스까지 red로 만든다(실측). 그래서 버블 줄바꿈 계약은 CI에서도 도는 소스 스캔
  //   (`src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts`)으로 고정했다.
});

// 관리자 계정(supabase/.env.seed — 전 계정 공유 비밀번호) — core-flows.spec.ts의 ADMIN_USER와 동일.
const ADMIN_USER = { email: 'admin@test.com', password: 'seller123' };

test.describe('관리자 6화면 — 가로스크롤 없음 (spec-15-2, DW-697 ②)', () => {
  // 관리자 화면엔 카드 그리드가 없다(단일 열 리스트/상세) — 그래서 이 스위트의 다른 describe들과
  // 달리 그리드 열수(assertGridColumnsOrEmptyState) 단언은 하지 않는다(spec-15-2 Always, 파일 헤더
  // 주석의 "그리드를 쓰는 화면에만 열수 단언" 원칙과 같은 논리로 스코프). 대신 사이드바(spec-15-2
  // AdminSidebar)가 콘텐츠 폭을 줄여도 6화면(목록 4 + 상세 2) 전부 가로스크롤이 없는지만 본다.
  //
  // 코드리뷰 patch 2건이 여기 들어 있다:
  //   ① **가로스크롤만 보면 이 스토리가 겨냥한 위험을 못 본다.** 스펙의 인수조건은 "가로스크롤이
  //      없고 **배지·라벨이 두 줄로 밀리지 않는다**"이고 Block If는 "회원관리 행의 배지+액션
  //      조합이 줄바꿈됨"인데, 줄바꿈은 오히려 가로스크롤을 **없애는** 방향이다 — 즉 고르던 단언이
  //      정확히 반대로 움직인다. 관리자 행들은 지금 `min-w-0 + truncate`로 압력을 흡수하므로,
  //      그 truncate가 사라지거나 flex-wrap이 붙으면 사이드바가 폭을 240px 먹는 800px 구간에서
  //      두 줄이 된다. 이 파일의 다른 describe들이 전부 그러듯 단일행 단언을 함께 건다.
  //   ② **관리자 화면이 실제로 그려졌는지 아무도 안 봤다.** 세션 만료·권한 회귀로 전부 /login으로
  //      튕겨도 로그인 화면엔 가로스크롤이 없어 7개 단언이 모두 통과한다(C6은 이걸 에러 문구 +
  //      행 수로 막고 있는데 여기엔 없었다).
  test('목록 4 + 상세 2 — 가로스크롤 없음', async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);

    // ✎ 2026-08-13(#9) — `/admin`은 이제 대시보드 허브가 아니라 회원관리로 **전달**된다. 그래서
    //   "요청한 경로에 그대로 있는가"가 아니라 "도착해야 할 경로에 도착했는가"로 본다(둘을 쌍으로
    //   적어, 리다이렉트 대상이 조용히 바뀌면 여기서 걸리게 한다).
    const adminPaths: [request: string, expected: string][] = [
      ['/admin', '/admin/members'],
      ['/admin/members', '/admin/members'],
      ['/admin/listings', '/admin/listings'],
      ['/admin/transactions', '/admin/transactions'],
      ['/admin/chats', '/admin/chats'],
    ];
    for (const [path, expectedPath] of adminPaths) {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      // ② 로그인 화면으로 튕기지 않고 관리자 경로에 도달했는지 먼저 확인한다.
      expect(
        new URL(page.url()).pathname,
        `${path}: 관리자 경로(${expectedPath})에 도달해야 함(로그인 리다이렉트 등 아님)`,
      ).toBe(expectedPath);
      await assertNoHorizontalOverflow(page);
    }

    // ① 회원관리 행 — 관리자 화면 중 한 행에 가장 많은 요소(역할 라벨 + 라벨 + 배지 + 액션 2개)가
    //    들어가 사이드바 압력을 가장 먼저 받는 자리다.
    //
    //    코드리뷰 patch 2건이 이 몇 줄에 겹쳐 있다 — 이 단언은 원래 **잴 수 없는 것을 재고 있었다**:
    //      (가) 재는 **대상**이 틀렸다. `li` 안의 첫 `span`은 라벨 묶음
    //           (`flex min-w-0 items-center gap-2`)인데, 그 안은 `truncate`(whitespace-nowrap)라
    //           애초에 두 줄이 될 수 없다. 정작 Block If가 말하는 것은 "배지+액션 조합이 줄바꿈됨"
    //           = **행(li) 자체**가 두 줄이 되는 것이다. 실측: li에 `flex-wrap`, 액션 div에
    //           `basis-full`을 넣어 액션을 아랫줄로 내려도 라벨 span 높이는 그대로라 green이었고,
    //           줄바꿈은 가로스크롤을 오히려 **없애므로** 옆의 assertNoHorizontalOverflow도 green이었다.
    //           → `li`를 직접 잰다.
    //      (나) 재는 **행**이 틀렸다. 회원 목록은 가입일 오름차순이고 본인 행에는
    //           `MemberActions`를 렌더하지 않는데(members/page.tsx의 isSelf), 먼저 가입한 관리자가
    //           맨 위라 `.first()`는 **액션 버튼이 없는 가장 헐거운 행**을 고를 수 있다. 주석은
    //           "가장 많은 요소가 들어간 행"이라 말하면서 실제로는 반대쪽 끝을 재던 셈이다.
    //           → 액션 버튼을 실제로 가진 행으로 고른다.
    await page.goto('/admin/members');
    await page.waitForLoadState('networkidle');
    const loadedMemberRow = page
      .locator('main ul li')
      .filter({ has: page.getByRole('button', { name: /^(정지|정지 해제)$/ }) })
      .first();
    await expect(loadedMemberRow, '액션 버튼을 가진 회원 행이 1개 이상 있어야 줄바꿈을 판정할 수 있음').toBeVisible();
    await assertSingleLine(loadedMemberRow);

    // 상세 2개(목록 4에 이어 대표 1개씩) — 관리자 RLS는 sold 포함 전 매물·전 채팅방을 보므로
    // buyer 시드 계정 기준으로 뽑은 id를 그대로 재사용해도 관리자 세션에서 항상 열람 가능하다.
    //
    // 코드리뷰 patch — ②의 "경로에 머물렀나" 가드가 위 목록 루프 **안에만** 걸려 있어, 정작 이
    // 스토리가 새로 추가한 상세 2경로는 여전히 무방비였다. 게다가 상세 화면엔 목록에 없는 실패
    // 모드가 하나 더 있다: 조회 실패·없는 id면 짧은 안내문 하나만 그려지는데, 그 화면도
    // 가로스크롤이 없어 단언이 통과한다. 그래서 경로 + 에러문구 부재를 함께 본다.
    //   (`getByRole('alert')`는 쓰지 않는다 — Next dev의 route announcer가 빈 role="alert"를
    //    항상 하나 심어 둬서 어떤 화면에서도 0이 되지 않는다. 실측으로 확인했다. C6과 같이
    //    실제 에러 **문구**를 본다.)
    const listingId = await fetchOnSaleListingIdWithPhoto();
    await page.goto(`/admin/listings/${listingId}`);
    await page.waitForLoadState('networkidle');
    expect(new URL(page.url()).pathname, '매물 상세: 관리자 경로에 머물러야 함').toBe(
      `/admin/listings/${listingId}`,
    );
    await expect(page.getByText(/불러오지 못했습니다|찾을 수 없습니다/)).toHaveCount(0);
    await assertNoHorizontalOverflow(page);

    const roomId = fetchChatRoomIdForSeedUser();
    await page.goto(`/admin/chats/${roomId}`);
    await page.waitForLoadState('networkidle');
    expect(new URL(page.url()).pathname, '채팅방 상세: 관리자 경로에 머물러야 함').toBe(
      `/admin/chats/${roomId}`,
    );
    await expect(page.getByText(/불러오지 못했습니다|찾을 수 없습니다/)).toHaveCount(0);
    await assertNoHorizontalOverflow(page);
  });
});

test.describe('/ai — 가로 오버플로 없음 (#84) + 입력 폼·카드 무결성', () => {
  test('로그인 사용자, 카드 0개(빈 대화)', async ({ page }) => {
    await login(page);
    await page.goto('/ai');
    await page.waitForLoadState('networkidle');
    await assertNoHorizontalOverflow(page);
    // D5: 전송 버튼이 좁은 폭에서도 2줄로 밀리지 않는지(코드리뷰 patch).
    await assertSingleLine(page.getByRole('button', { name: '전송' }));
  });

  test('로그인 사용자, 카드 N개(목업 검색 결과)', async ({ page }) => {
    await login(page);
    const mock = await mockAiSearch(page, buildMockListings(4));
    await page.goto('/ai');
    await page.getByLabel('AI 검색 질의 입력').fill('3천만원 이하 SUV');
    await page.getByRole('button', { name: '전송' }).click();
    // 답변 텍스트가 도착할 때까지 기다린다(카드가 실제로 그려진 뒤 측정해야 의미가 있다).
    await page.getByText('테스트 응답').waitFor();
    // 목업이 실제로 가로챘는지 확인한다(코드리뷰 patch) — 안 그러면 base URL 정규화 문제로
    // 실 백엔드(과금·비결정적)로 요청이 새어나가도 화면상 응답 텍스트만 보고 통과할 수 있다.
    expect(mock.requestCount(), '/ai/search 목업이 한 번도 호출되지 않음 — 실 백엔드로 새어나갔을 수 있음').toBeGreaterThan(0);
    await assertNoHorizontalOverflow(page);
    // D5: 전송 버튼(카드 렌더 후에도 2줄로 안 밀림) + 카드 meta 줄(주행거리·지역) 무결성(코드리뷰 patch).
    await assertSingleLine(page.getByRole('button', { name: '전송' }));
    // 여기서 `.first()`는 P5가 지적한 "우선순위 문제"가 아니다(코드리뷰 patch 검토 결과) — 카드가
    // N개(목업 4장)라 meta 줄도 정상적으로 N개 나온다. "카드마다 유일해야 한다"는 게 아니라 "적어도
    // 하나는 실제로 렌더됐다"는 존재 확인만 하려는 의도라, 대표로 하나만 뽑아 D5 한 줄 유지를 본다.
    const cardMetaLine = page.locator('[data-testid="listing-meta"]').first();
    await expect(
      cardMetaLine,
      '카드 meta 줄(data-testid="listing-meta")을 찾을 수 없음 — 목업 카드가 실제로 렌더됐는지 확인할 것',
    ).toHaveCount(1);
    await assertSingleLine(cardMetaLine);
    await assertTruncatesNotWraps(cardMetaLine);
  });
});
