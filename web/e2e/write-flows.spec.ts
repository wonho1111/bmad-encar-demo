// 쓰기 흐름 왕복 — 정식 스위트 승격판(2026-07-28, 대장 #182). 원래 일회성 감사
// 스펙(e-write-flows.spec.ts)을 그대로 옮긴다. 다른 신규 스펙 3개(landing-and-view-count·
// nav-and-hero·core-flows)와 달리 이 스펙만 실제로 DB에 쓴다: 등록(E1)→검색노출(E2)→수정(E3)→
// 문의채팅(E4)→구매완료(E5)→관리자 되돌리기(E6)가 한 매물을 이어서 쓰는 왕복 시나리오다.
// test.describe.serial로 순서를 보장하고 매물 id를 describe 스코프 변수로 공유한다.
//
// 절대 규칙: 시드 데이터(기존 매물·기존 계정·기존 채팅방)는 읽기만 한다. 이 스펙이 직접 만든
// 것(매물 1건 → cascade로 listing_images·chat_rooms·chat_messages·wishlists까지 함께)만
// afterAll에서 지운다.
//
// ⚠️ 운영 안전 가드 — 이 파일이 이 스위트에서 가장 위험한 파일이다(실제 쓰기를 한다). 파일이
// 로드되는 즉시 assertLocalSupabase()를 불러, NEXT_PUBLIC_SUPABASE_URL이 로컬이 아니면 첫
// 테스트가 시작되기도 전에 죽는다(자세한 이유는 helpers.ts의 함수 주석 참조).
import { test, expect } from '@playwright/test';
import { assertLocalSupabase, login, runPsql } from './helpers';
import { PROJECT_NAMES } from './project-names';

assertLocalSupabase();

/** SQL 문자열 리터럴에 안전하게 끼워 넣기 위한 최소 이스케이프(작은따옴표만). */
function sqlLit(s: string): string {
  return s.replace(/'/g, "''");
}

// 이 감사는 데스크톱 뷰포트 축만 본다 — mobile-390x844 프로젝트에서 두 번째로 돌면 같은 왕복이
// 중복 실행돼(특히 매물 재등록·중복 채팅방) 시나리오가 꼬인다. tablet-800x1024 프로젝트도 이
// 조건에 걸려 함께 스킵된다.
test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '이 감사는 desktop 프로젝트에서만 돈다.');
});

const SELLER = { email: 'seller@test.com', password: 'seller123' };
const BUYER = { email: 'buyer@test.com', password: 'seller123' };
const ADMIN = { email: 'admin@test.com', password: 'seller123' }; // supabase/.env.seed — 전 계정 공유 비밀번호
const MODEL = 'E2E감사0728'; // 시드에 없는 식별 문자열 — 나중에 찾고 지우기 쉽게.
const MSG = `${MODEL} 문의합니다`;
const INITIAL_PRICE = 12_345_000;
const UPDATED_PRICE = 13_999_000;
const RESTORED_PRICE = 14_500_000; // E6 — 되돌린 뒤 재수정 시 쓰는 값(UPDATED_PRICE와 구분해 실제로 바뀌었는지 명확히 본다).

// 상세 화면에 **실제로 찍히는 글자**(2026-08-13 가격 표기 만원 전환).
// ⚠️ 여기서 formatPrice()를 부르지 않고 **문자열을 손으로 적는다** — 기대값을 피검사 대상에서
//    다시 계산하면 그 함수가 어떻게 바뀌든 항상 통과한다(자기일관 단언). 값이 바뀌면 이 줄이
//    빨개져야 한다.
//    위 세 값이 우연히 두 분기를 다 밟는다: 12,345,000·13,999,000은 만원 단위로 **안** 떨어져
//    원 표기 폴백이 걸리고, 14,500,000은 떨어져 만원 표기가 된다 — 한 스펙에서 양쪽이 다 시험된다.
const INITIAL_PRICE_TEXT = '12,345,000원';
const UPDATED_PRICE_TEXT = '13,999,000원';
const RESTORED_PRICE_TEXT = '1,450만원';

// ── 병렬 간섭 분석(정식 config는 fullyParallel: true — 이 파일이 다른 스펙과 동시에 돈다) ──
// region='서울'·현대·준중형차 매물 1건이 실제 DB에 떠 있고, 그 status는 **두 번** on_sale 구간을
// 갖는다: (a) E1 등록 ~ E5 구매완료 전, (b) E6이 되돌린 뒤 ~ E6 마지막 재구매완료 전
// (2026-08-07 코드리뷰 patch — E6 추가로 on_sale 창이 하나에서 둘로 늘었는데 이 문단은 여전히
// "E1~E5" 한 구간만 말하고 있었다. 아래 판정들은 "on_sale이든 sold든 견딘다"는 논리라 결론은
// 그대로지만, 전제 문장이 파일의 실제 수명주기와 어긋난 채로 남아 있었다).
// 그 창(window) 동안 다른 스펙이 카드 수·필터 결과를 보면 +1이 낄 수 있다는
// 뜻이다. 아래는 이 리포의 나머지 스펙이 그 +1을 실제로 견디는지 **코드를 읽어** 판정한 결과다
// (추측이 아니라 각 파일의 실제 단언 방식 근거).
//
//   · core-flows.spec.ts C2(매물 목록 검색·필터) — 견딤. totalCount/filteredCount 모두 같은
//     테스트 실행 안에서 방금 조회한 값이고, 단언은 `toBeGreaterThan(0)`·`toBeLessThan(totalCount)`
//     같은 **상대 비교**뿐 절대 건수를 하드코딩하지 않는다(주석의 "95건"·"24건"은 정보용일
//     뿐 단언에 안 쓰인다). 키워드 검색은 '스타리아'를 찾는데 이 파일의 MODEL은
//     'E2E감사0728'이라 겹치지 않는다.
//   · core-flows.spec.ts C4(판매완료 비노출) — 견딤. soldIds는 그 테스트가 psql로 그 순간
//     직접 조회하고, /search는 제품 코드(search/page.tsx)가 항상 status='on_sale'만 걸러
//     조회한다 — 그래서 이 파일의 매물이 아직 on_sale이든(교집합 대상 아님) 마침 E5로 막
//     sold가 됐든(그 순간부터 /search 쿼리 자체가 걸러낸다) 교집합은 흔들리지 않는다.
//   · image-fallback.spec.ts(플레이스홀더 전량 발동) — 견딤. `cardCount`를
//     `page.locator('[data-testid="listing-meta"]').count()`로 **그 테스트가 스크롤·abort를
//     다 마친 뒤 직접 세어** 넘기지, 고정값이 아니다. 이 파일의 매물은 사진을 올리지 않으므로
//     (E1 주석 참조) 이미지 abort 실험과 무관하게 원래도 플레이스홀더가 뜨는 부류에 합류할
//     뿐이고, cardCount·placeholderCount가 항상 같은 스냅샷에서 함께 세어지므로 어긋나지 않는다.
//   · viewport-audit.spec.ts(그리드 열 수) — 견딤. 열 수는 `getComputedStyle(...).gridTemplateColumns`
//     (뷰포트 폭 기반 CSS 브레이크포인트)로 재지, 카드 개수에서 유도하지 않는다 — 카드가
//     1개 늘어도 트랙 수 자체는 그대로다. 다만 랜딩 "방금 올라온 매물" 섹션이 created_at
//     내림차순이라 이 파일의 신규 매물이 일시적으로 "첫 카드"가 될 수 있는데,
//     `assertFirstCardMetaLineSingleLine`이 보는 것은 그 카드의 meta 줄(주행거리·연료·지역)
//     한 줄 렌더 여부이고 이 파일이 등록하는 매물도 그 필드를 전부 채우므로(E1) 값 자체는
//     정상 렌더된다 — 다만 어떤 카드가 "첫 카드"로 뽑히느냐가 실행마다 달라진다는 점은 이
//     스펙이 원래도 가진 성질(시드 데이터 자체도 계속 갱신됨)이라 이 파일이 새로 만드는
//     위험은 아니다.
//   · landing-and-view-count.spec.ts A5(sold 랜딩 비노출) — 견딤. C4와 동일 논리: 랜딩 쿼리도
//     on_sale만 통과시키므로 sold 전환 시점과 무관하게 교집합이 비게 유지된다. A2/A3(view_count)은
//     "사진 있는 매물"이거나 "id 오름차순 첫 매물"을 결정론적으로 골라 쓰는데, 이 파일의 매물은
//     사진이 없고 id도 무작위 UUID라 그 두 조회에 우연히 뽑힐 확률은 사실상 0에 가깝다(관측된
//     문제는 아니고, 이론적 여지만 남겨 적어둔다 — 실패가 나면 이 주석부터 의심할 것).
//   · nav-and-hero.spec.ts — 매물 개수·목록에 의존하는 단언이 없어(내비 구성·히어로 게이트만
//     본다) 애초에 간섭 대상이 아니다.
test.describe.serial('쓰기 흐름 왕복 — 등록→검색→수정→문의채팅→구매완료→관리자되돌리기', () => {
  let listingId: string | undefined;
  let roomId: string | undefined;

  // 앞이 실패해도 반드시 돈다(afterAll) — 정리가 실패에 딸려 안 돌면 시드가 오염된다.
  //
  // ⚠️ **프로젝트 가드가 여기에도 반드시 있어야 한다**(2026-07-28 승격 직후 실측으로 잡은 결함).
  // 위 `beforeEach`의 `test.skip`은 **테스트만** 건너뛰지 `afterAll`은 못 막는다 — Playwright는
  // 이 describe가 스케줄된 **프로젝트마다**(desktop·tablet·mobile 3번) afterAll을 실행한다.
  // 가드가 없으면 tablet/mobile의 afterAll이 아무것도 만들지 않았으면서 아래 "모델명 재탐색"
  // 분기로 들어가, **desktop이 아직 E2~E5로 쓰고 있는 그 매물을 찾아 지운다.**
  //
  // 실측 근거(추측 아님): 전체 스위트를 돌리며 psql로 0.5초마다 이 매물을 관측했더니 매물이
  // **약 16초만 존재하다 사라졌고**(E1 7.9s + E2 4.2s로 이미 12초 소모), 그 순간 진행 중이던
  // 테스트가 실패했다. 실패 지점이 실행마다 E2↔E3로 옮겨 다닌 것도(타이밍에 따라) 이걸로
  // 설명된다. 실패 화면에는 검색 결과가 "조건에 맞는 매물이 없습니다"로 찍혀 있었다 — DB에는
  // 있는데 화면에 없는 게 아니라, **그 시점엔 DB에서도 이미 지워져 있었다.**
  test.afterAll(async ({}, testInfo) => {
    if (testInfo.project.name !== PROJECT_NAMES.desktop) return; // 이 프로젝트는 아무것도 만들지 않았다
    let idToClean = listingId;
    if (!idToClean) {
      // 실행 중 변수 공유가 끊긴 경우(예: 워커 재시작)에도 모델명으로 재탐색해 정리를 시도한다.
      const found = runPsql(`select id from listings where model='${sqlLit(MODEL)}' order by created_at desc limit 1;`);
      idToClean = found || undefined;
    }
    if (idToClean) {
      // listings 삭제 하나로 listing_images·chat_rooms·chat_messages·wishlists가 전부 cascade 삭제된다
      // (FK confdeltype='c' 확인됨). 사진을 올리지 않았으므로 storage.objects는 애초에 만들어지지 않았다.
      runPsql(`delete from listings where id='${idToClean}';`);
    }
  });

  test('E1 [desktop] 판매자가 매물을 등록하면 즉시 on_sale로 노출된다', async ({ page }) => {
    await login(page, SELLER.email, SELLER.password);
    await page.goto('/sell');

    // 사진 업로드는 SellForm의 validateAndBuild()가 검증하지 않는 선택 필드(소스 확인) — 스킵한다.
    await page.getByLabel('제조사').selectOption('현대');
    await page.getByLabel('모델').fill(MODEL);
    await page.getByLabel('차종').selectOption('준중형차');
    await page.getByLabel('연식 (년)').fill('2021');
    await page.getByLabel('가격 (원)').fill(String(INITIAL_PRICE));
    await page.getByLabel('주행거리 (km)').fill('50000');
    await page.getByLabel('색상').selectOption('흰색');
    await page.getByLabel('연료').selectOption('가솔린');
    await page.getByLabel('변속기').selectOption('자동');
    await page.getByLabel('배기량 (cc)').fill('1600');
    await page.getByLabel('인승 (명)').fill('5');
    await page.getByLabel('지역').selectOption('서울');
    // ✎ 2026-08-13 — 신뢰 정보 입력이 새로 생겼다(그전엔 폼에 아예 없어서 저장 자체가 불가능했다).
    //   사고이력은 **필수**라 안 고르면 여기서 등록이 막힌다. 1인소유는 체크하고 비흡연은 **일부러
    //   비워 둔다** — 아래에서 "미체크는 false가 아니라 NULL(미신고)"을 실제 DB 값으로 확인하려고.
    await page.getByLabel('사고이력').selectOption('무사고');
    await page.getByLabel(/1인소유/).check();

    await page.getByRole('button', { name: '매물 등록' }).click();

    await expect(page.getByRole('status')).toContainText('매물이 등록되었습니다', { timeout: 10_000 });

    const id = runPsql(`select id from listings where model='${sqlLit(MODEL)}' order by created_at desc limit 1;`);
    expect(id, 'DB에 방금 등록한 매물이 없음').not.toBe('');
    listingId = id;

    const status = runPsql(`select status from listings where id='${id}';`);
    expect(status, `방금 등록한 매물(${id})의 status`).toBe('on_sale');

    // 신뢰 정보가 **실제로 저장됐는지** DB에서 직접 본다(2026-08-13). 화면에 뱃지가 뜨는지가
    // 아니라 값이 들어갔는지를 보는 이유: 이 3컬럼은 2026-07에 만들어졌는데 **쓰는 코드가 한 번도
    // 없었고**, 그걸 잡는 검사도 없어서 "화면엔 기능이 있는데 저장이 안 되는" 상태가 한 달 넘게
    // 아무에게도 안 보였다. 그 사각지대를 여기서 닫는다.
    //   ⓐ accident_status = 고른 값 그대로
    //   ⓑ accident_free = **파생값**(무사고 → true). 이 컬럼은 AI 검색이 쓰므로 계속 채워져야 한다
    //      (api/app/graph/sql_rag_node.py 지시문이 사고 질문을 이 컬럼으로 판단하라고 명시).
    //   ⓒ is_single_owner = t(체크함)
    //   ⓓ is_non_smoker = **NULL**(미체크). f가 아니다 — 판매자는 "비흡연이 아니다"라고 말한 적이
    //      없다. `is null` 자체를 SQL에서 판정해 문자열 비교의 애매함('' vs 'f')을 피한다.
    const trust = runPsql(
      `select accident_status, accident_free, is_single_owner, (is_non_smoker is null) from listings where id='${id}';`,
    );
    expect(trust, `등록된 신뢰 정보(매물 ${id}) — 순서: 사고이력|무사고파생|1인소유|비흡연이NULL인가`).toBe(
      '무사고|t|t|t',
    );
  });

  test('E2 [desktop] 등록한 매물이 검색에 즉시 보이고 입력값이 그대로 보인다', async ({ page }) => {
    test.skip(!listingId, 'E1이 실패해 listingId가 없음');

    await page.goto('/search');
    await page.getByLabel('키워드(모델명)').fill(MODEL);
    await page.getByRole('button', { name: '검색' }).click();
    await page.waitForLoadState('networkidle');

    const cardLink = page.getByRole('link', { name: new RegExp(`\\[현대\\] ${MODEL}`) });
    await expect(cardLink).toBeVisible();
    await cardLink.click();

    await page.waitForURL(new RegExp(`/listings/${listingId}$`));
    await expect(page.getByTestId('detail-price')).toHaveText(INITIAL_PRICE_TEXT);
  });

  test('E3 [desktop] 본인 매물 가격 수정이 반영된다', async ({ page }) => {
    test.skip(!listingId, 'E1이 실패해 listingId가 없음');

    await login(page, SELLER.email, SELLER.password);
    await page.goto('/sell');

    const row = page.locator('li').filter({ hasText: MODEL });
    await row.getByRole('link', { name: '수정' }).click();
    await page.waitForURL(new RegExp(`/sell/${listingId}/edit$`));

    await page.getByLabel('가격 (원)').fill(String(UPDATED_PRICE));
    await page.getByRole('button', { name: '수정 저장' }).click();
    await page.waitForURL('**/sell');

    await page.goto(`/listings/${listingId}`);
    await expect(page.getByTestId('detail-price')).toHaveText(UPDATED_PRICE_TEXT);

    const dbPrice = runPsql(`select price from listings where id='${listingId}';`);
    expect(dbPrice, `DB의 price 값(매물 ${listingId})`).toBe(String(UPDATED_PRICE));
  });

  test('E4 [desktop] 구매자 문의로 채팅방이 생기고 메시지가 오가며 판매자도 그 메시지를 본다', async ({
    page,
    browser,
  }) => {
    test.skip(!listingId, 'E1이 실패해 listingId가 없음');

    await login(page, BUYER.email, BUYER.password);
    await page.goto(`/listings/${listingId}`);

    // 로그인+타인 매물 = mode 'inquiry'. 문의 버튼은 화면에 셋(요약 카드·모바일 하단 바·판매자정보
    // 카드)이 DOM에 있고 데스크톱에선 요약 카드 것과 판매자정보 카드 것이 **둘 다 보인다**
    // (2026-08-13 #2 — 목업의 `.seller-contact-btn` 추가). 요약 카드 쪽을 고른다: 이름이 정확히
    // "문의하기"인 것은 그쪽뿐이다(판매자정보 카드는 "판매자에게 문의하기").
    await page.locator('aside').getByRole('button', { name: '문의하기', exact: true }).click();
    await page.waitForURL(/\/chat\/[0-9a-f-]+$/, { timeout: 15_000 });
    roomId = new URL(page.url()).pathname.split('/').pop();
    expect(roomId, '문의하기 클릭 후 이동한 채팅방 URL에서 roomId 추출').toBeTruthy();

    await page.getByLabel('메시지 입력').fill(MSG);
    await page.getByRole('button', { name: '전송' }).click();
    await expect(page.getByText(MSG)).toBeVisible();

    const roomRow = runPsql(`select id from chat_rooms where id='${roomId}' and listing_id='${listingId}';`);
    expect(roomRow, 'DB에 그 방이 이 매물로 존재').toBe(roomId);
    const msgRow = runPsql(`select body from chat_messages where room_id='${roomId}' and body='${sqlLit(MSG)}';`);
    expect(msgRow, 'DB에 보낸 메시지가 존재').toBe(MSG);

    // 판매자가 같은 방에서 그 메시지를 보는지 — 별도 브라우저 컨텍스트(세션 충돌 방지).
    const sellerContext = await browser.newContext();
    try {
      const sellerPage = await sellerContext.newPage();
      await login(sellerPage, SELLER.email, SELLER.password);
      await sellerPage.goto(`/chat/${roomId}`);
      await expect(sellerPage.getByText(MSG)).toBeVisible();
    } finally {
      await sellerContext.close();
    }
  });

  test('E5 [desktop] 구매완료 처리하면 검색에서 사라지고 상세는 "찾을 수 없음" 안내로 바뀐다', async ({
    page,
  }) => {
    test.skip(!listingId, 'E1이 실패해 listingId가 없음');

    await login(page, SELLER.email, SELLER.password);
    await page.goto('/sell');

    const row = page.locator('li').filter({ hasText: MODEL });
    page.once('dialog', (dialog) => dialog.accept()); // window.confirm 실수방지 다이얼로그 수락
    await row.getByRole('button', { name: '구매 완료' }).click();
    await expect(row.getByText('판매완료')).toBeVisible({ timeout: 10_000 });

    const status = runPsql(`select status from listings where id='${listingId}';`);
    expect(status, `구매완료 처리 후 매물(${listingId}) status`).toBe('sold');

    await page.goto('/search');
    await page.getByLabel('키워드(모델명)').fill(MODEL);
    await page.getByRole('button', { name: '검색' }).click();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('link', { name: new RegExp(MODEL) })).toHaveCount(0);

    const detailResponse = await page.goto(`/listings/${listingId}`);
    expect(detailResponse?.status(), '구매완료 매물 상세 직접 접근 HTTP 상태').toBe(200);
    await expect(page.getByRole('status').getByText('매물을 찾을 수 없어요.')).toBeVisible();
  });

  test('E6 [desktop] 관리자가 판매완료를 되돌리면 판매자가 다시 정상 수정·구매완료할 수 있다', async ({
    page,
    browser,
  }) => {
    test.skip(!listingId, 'E1~E5 중 하나가 실패해 listingId가 없음');

    // 관리자가 매물 관리 목록에서 sold 매물의 "판매완료 되돌리기"를 누른다(DW-391, Story 15.4,
    // ListingAdminActions.tsx → admin_restore_sold_listing RPC, 0030).
    await login(page, ADMIN.email, ADMIN.password);

    // 코드리뷰 patch — 런북 §10은 "목록·상세 **양쪽**에서 이 버튼이 보인다"고 약속하는데, 상세
    //   화면(`[id]/page.tsx`)이 status prop을 넘기는 배선은 어느 테스트도 렌더한 적이 없었다
    //   (다른 관리자 상세 E2E는 전부 on_sale 매물을 골라 열어서 이 버튼이 애초에 안 뜬다).
    //   여기서 sold 상태의 상세를 한 번 열어 버튼 존재만 확인한다 — 클릭은 목록에서 한다
    //   (되돌리기의 실제 왕복 시나리오는 목록 동선이 정본이므로 그쪽을 바꾸지 않는다).
    await page.goto(`/admin/listings/${listingId}`);
    await expect(page.getByRole('button', { name: '판매완료 되돌리기' })).toBeVisible();

    await page.goto('/admin/listings');
    // ⚠️ 행을 MODEL이 아니라 **listingId로 좁힌다**(3차 코드리뷰). /sell은 판매자 본인 매물만
    //   보여주지만 이 화면은 정반대로 전 판매자·전 상태를 필터 없이 보여준다 — 중단된 이전
    //   실행이 남긴 같은 MODEL 매물이 하나라도 있으면 locator가 2건이 되어 strict mode로 죽는다.
    const adminRow = page.locator('li').filter({
      has: page.locator(`a[href$="/admin/listings/${listingId}"]`),
    });
    await adminRow.getByRole('button', { name: '판매완료 되돌리기' }).click();
    await expect(adminRow.getByText('판매중')).toBeVisible({ timeout: 10_000 });
    // 코드리뷰 patch — 배지 문구뿐 아니라 되돌리기 버튼 자체도 사라져야 한다(isSold 게이트가
    //   되돌린 뒤에도 계속 올바르게 판정된다는 증거, on_sale 매물엔 이 버튼이 없어야 함).
    await expect(adminRow.getByRole('button', { name: '판매완료 되돌리기' })).toHaveCount(0);
    // 3차 코드리뷰 patch — 0행 거부 경로가 조용히 지나가지 않게 오류 알림 부재를 명시 확인한다.
    //   위 배지는 서버 재렌더 결과라 "RPC가 거부됐는데 다른 이유로 화면이 바뀐" 경우를 못 가른다.
    await expect(adminRow.getByRole('alert')).toHaveCount(0);

    const restoredStatus = runPsql(`select status from listings where id='${listingId}';`);
    expect(restoredStatus, `되돌리기 후 매물(${listingId}) status`).toBe('on_sale');

    // 3차 코드리뷰 patch — AC1은 "status가 on_sale로 바뀌고 **목록에 재노출**된다"인데, 위
    //   단언들은 전부 관리자 화면(sold도 보이는 화면)과 DB 컬럼이라 "재노출"을 관측하지 못했다.
    //   FR11이 실제로 사는 표면은 구매자 경로다 — 로그인 안 한 익명 컨텍스트로 검색해 다시
    //   보이는지 본다(E4가 sold일 때 안 보이는 것을 확인하는 것과 짝을 이룬다).
    const anonContext = await browser.newContext();
    try {
      const anonPage = await anonContext.newPage();
      await anonPage.goto(`/search?q=${encodeURIComponent(MODEL)}`);
      await expect(
        anonPage.locator(`a[href$="/listings/${listingId}"]`).first(),
        '되돌린 매물이 비로그인 검색 결과에 다시 노출되지 않는다(AC1 "목록에 재노출")',
      ).toBeVisible({ timeout: 15_000 });
    } finally {
      await anonContext.close();
    }

    // 되돌리기 전엔 0015(RLS)가 sold 행의 UPDATE를 판매자에게도 0행으로 막는다 — 되돌린 뒤
    // 판매자가 다시 정상적으로 수정할 수 있는지가 왕복 검증의 핵심(회귀 없음, 스펙 I/O 매트릭스 5행).
    await login(page, SELLER.email, SELLER.password);
    await page.goto('/sell');
    const sellerRow = page.locator('li').filter({ hasText: MODEL });
    await sellerRow.getByRole('link', { name: '수정' }).click();
    await page.waitForURL(new RegExp(`/sell/${listingId}/edit$`));

    await page.getByLabel('가격 (원)').fill(String(RESTORED_PRICE));
    await page.getByRole('button', { name: '수정 저장' }).click();
    await page.waitForURL('**/sell');

    // 코드리뷰 patch — E3와 동일하게 DB뿐 아니라 렌더된 상세 페이지도 확인한다(되돌리기→재수정
    //   경로 전용 캐시/렌더 결함은 E3의 일반 수정 경로로는 못 잡는다).
    await page.goto(`/listings/${listingId}`);
    await expect(page.getByTestId('detail-price')).toHaveText(RESTORED_PRICE_TEXT);

    const restoredPrice = runPsql(`select price from listings where id='${listingId}';`);
    expect(restoredPrice, `되돌리기 후 재수정된 DB price 값(매물 ${listingId})`).toBe(String(RESTORED_PRICE));

    await page.goto('/sell');

    // 재구매완료 처리까지 정상 동작해야 왕복이 완성된다.
    const rowAfterEdit = page.locator('li').filter({ hasText: MODEL });
    page.once('dialog', (dialog) => dialog.accept()); // window.confirm 실수방지 다이얼로그 수락
    await rowAfterEdit.getByRole('button', { name: '구매 완료' }).click();
    await expect(rowAfterEdit.getByText('판매완료')).toBeVisible({ timeout: 10_000 });

    const finalStatus = runPsql(`select status from listings where id='${listingId}';`);
    expect(finalStatus, `재구매완료 처리 후 매물(${listingId}) status`).toBe('sold');
  });
});
