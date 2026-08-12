// 정지된 계정의 화면 동작 — 관리자 콘솔 차단(DW-806) + 차단된 쓰기의 안내 문구 구분(DW-804 (b)).
// spec-17-3-정지-관리자-콘솔-차단-거부-안내-구분.
//
// 17.1(RLS)이 정지 회원의 쓰기를 DB에서 이미 전부 막았다(supabase/migrations/0032). 이 스펙은
// "그 강제를 화면이 옳게 설명하는가"만 다룬다 — 강제력 자체는 여기서 다시 검사하지 않는다(그건
// api/tests/integration/test_suspended_write_block_real_db.py 몫). 그래서 이 파일의 단언은 전부
// "화면에 뜨는 문구"와 "DB 값이 실제로 안 바뀌었는가"(사전 검사가 아니라는 증거, 위 두 검사가
// 동시에 성립해야 스토리의 불변식을 지킨 것이다)에 집중한다.
//
// ⚠️ 공유 시드 계정(admin@test.com·seller@test.com)을 정지시키지 않는다 — 다른 스펙 파일이
// `fullyParallel: true`(playwright.config.ts)로 같은 시각에 그 계정들을 쓴다. 대신 이 파일이
// 만들고 지우는 전용 계정을 쓴다(core-flows.spec.ts C9와 동일 관례).
import { expect, test } from '@playwright/test';
import { assertLocalSupabase, login, runPsql } from './helpers';
import { PROJECT_NAMES } from './project-names';

assertLocalSupabase();

function sqlLit(s: string): string {
  return s.replace(/'/g, "''");
}

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, '이 감사는 desktop 프로젝트에서만 돈다.');
});

/**
 * REST(PostgREST) 요청이 실제로 `listings` 엔드포인트에 도달했는지 기다려 확인한다.
 *
 * 왜 필요한가(spec-17-3 AC "사전 검사가 아님을 고정") — 화면 문구·DB 값(psql)만 보면 "DB가
 * 실제로 거부했다"와 "화면이 미리 막아 요청 자체를 안 보냈다"를 구분하지 못한다. 후자는
 * 정확히 스토리의 불변식("강제력은 DB에만 있다")을 화면 코드가 조용히 어기는 형태다.
 * `e2e/helpers.ts`의 `mockAiSearch`(요청을 가로채 `requestCount()`로 세는 관례)·
 * `image-fallback.spec.ts`의 abort 카운터와 같은 "네트워크로 실제 왕복을 관측해 증명"
 * 관례를 따르되, 여기서는 가로채지 않는다 — 가로채면 응답이 목업이 되어 그 자체가 "진짜 DB
 * 왕복"이라는 증거를 잃는다. 대신 실제로 돌아온 응답을 기다려 그 요청이 나갔음을 확인한다.
 */
function waitForListingsRequest(page: import('@playwright/test').Page, method: 'POST' | 'PATCH' | 'DELETE') {
  return page.waitForResponse(
    (res) => res.url().includes('/rest/v1/listings') && res.request().method() === method,
    { timeout: 10_000 },
  );
}

/**
 * "DB가 실제로 0행으로 거부했다"를 **응답 자체로** 확인한다.
 *
 * ⚠️ 왜 url()을 단언하지 않는가(2026-08-11 후속 코드리뷰 patch): 이전 판은 여기서
 * `expect(res.url()).toContain('/rest/v1/listings')`를 했는데, 그 값은 위 waitForListingsRequest의
 * predicate가 **이미 걸러 놓은** 것이라 절대 실패할 수 없는 단언이었다(3개 리뷰 렌즈가 독립 지적).
 * 그러면 실제로 짐을 지는 것은 waitForResponse의 타임아웃뿐이고, "요청이 나갔다"만 알 뿐
 * "DB가 거부했다"는 확인되지 않는다. predicate가 보장하지 않는 것 — 상태 코드와 본문 — 을 본다.
 * 쓰기 호출부가 전부 `.select('id')`를 붙이므로 PostgREST는 return=representation으로
 * 200 + JSON 배열을 주고, RLS로 막히면 그 배열이 비어 있다.
 */
async function expectZeroRowRejection(
  res: import('@playwright/test').Response,
  what: string,
): Promise<void> {
  expect(res.status(), `${what}: 요청이 DB까지 갔지만 응답이 200이 아니다`).toBe(200);
  expect(await res.json(), `${what}: DB가 0행으로 거부하지 않았다(행이 실제로 바뀌었다)`).toEqual([]);
}

/** write-flows.spec.ts E1과 동일한 15필드 최소 입력(사진 없음) — 이 파일 안에서 3번 재사용. */
async function fillListingForm(page: import('@playwright/test').Page, model: string) {
  await page.getByLabel('제조사').selectOption('현대');
  await page.getByLabel('모델').fill(model);
  await page.getByLabel('차종').selectOption('준중형차');
  await page.getByLabel('연식 (년)').fill('2021');
  await page.getByLabel('가격 (원)').fill('12345000');
  await page.getByLabel('주행거리 (km)').fill('50000');
  await page.getByLabel('색상').selectOption('흰색');
  await page.getByLabel('연료').selectOption('가솔린');
  await page.getByLabel('변속기').selectOption('자동');
  await page.getByLabel('배기량 (cc)').fill('1600');
  await page.getByLabel('인승 (명)').fill('5');
  await page.getByLabel('지역').selectOption('서울');
  // ✎ 2026-08-13 — 신뢰 정보 입력이 새로 생겼고 사고이력은 **필수**다(안 고르면 등록이 막힌다).
  //   이 스펙의 관심사는 정지 게이트라 값 자체는 아무거나 좋다 — 등록이 통과하기만 하면 된다.
  //   ("미체크는 NULL로 저장된다" 같은 신뢰 정보 자체의 계약은 write-flows.spec.ts E1이 본다.)
  await page.getByLabel('사고이력').selectOption('무사고');
}

// ── A. 관리자 콘솔 게이트 (DW-806) ──────────────────────────────────────
test.describe.serial('정지된 관리자는 /admin 콘솔에 못 들어간다(DW-806)', () => {
  const email = `e2e-17-3-admin-${Date.now()}@test.local`;
  const password = 'seller123';

  test.afterAll(async () => {
    runPsql(`delete from auth.users where email='${sqlLit(email)}';`);
    const leftover = runPsql(`select count(*) from auth.users where email='${sqlLit(email)}';`).trim();
    expect(leftover, '테스트 관리자 계정이 남으면 안 됨(원복 증명)').toBe('0');
  });

  test('[desktop] 활성 관리자는 /admin에 도달(긍정 대조군) → 정지 후 콘솔이 막히고 무한 리다이렉트 없이 홈에 머문다', async ({
    page,
  }) => {
    // 계정 생성(가입 화면, core-flows.spec.ts C9와 동일 관례) — role은 기본 'user'로 배정된다.
    await page.goto('/signup');
    await page.getByLabel('이메일').fill(email);
    await page.getByLabel('비밀번호').fill(password);
    await page.getByRole('button', { name: '가입하기' }).click();
    await page.waitForURL((url) => url.pathname === '/');

    // 관리자로 승격 — 가입 화면엔 역할 선택이 없다(FR52, 14.2). psql은 관리자 회원관리 화면과
    // 동일한 최종 상태(role='admin')를 만드는 지름길일 뿐, 이 스토리가 다루는 게이트 로직
    // 자체는 UI(브라우저)로 통과한다.
    // (UPDATE ... RETURNING은 psql -t 출력에 "UPDATE 1" 명령 태그 줄이 함께 섞여 나온다 —
    //   기존 관례대로 UPDATE와 확인용 SELECT를 분리한다.)
    runPsql(`update profiles set role='admin' where id=(select id from auth.users where email='${sqlLit(email)}');`);
    const promoted = runPsql(
      `select role from profiles where id=(select id from auth.users where email='${sqlLit(email)}');`,
    ).trim();
    expect(promoted, '테스트 계정을 admin으로 승격하지 못함').toBe('admin');

    // (긍정 대조군) 활성 관리자는 홈 진입 시 곧바로 /admin으로 유도되고(page.tsx 편의 랜딩),
    // 콘솔도 정상 렌더된다 — status 조건 추가가 활성 관리자의 기존 동작을 하나도 바꾸지 않았다.
    // ✎ 2026-08-13(#9) — /admin은 이제 회원관리로 한 번 더 전달된다(허브 화면을 없앴다).
    //    그래서 최종 경로는 /admin/members이고, 보이는 제목도 "관리자 영역"이 아니라 "회원 관리"다.
    await page.goto('/');
    await page.waitForURL((url) => url.pathname === '/admin/members');
    await expect(page.getByRole('heading', { name: '회원 관리' })).toBeVisible();

    // 정지시킨다.
    runPsql(`update profiles set status='suspended' where id=(select id from auth.users where email='${sqlLit(email)}');`);
    const suspended = runPsql(
      `select status from profiles where id=(select id from auth.users where email='${sqlLit(email)}');`,
    ).trim();
    expect(suspended, '테스트 계정을 suspended로 전환하지 못함').toBe('suspended');

    // (무한 리다이렉트 회귀 — 이 스토리가 만들 수 있는 가장 큰 사고) /admin 직접 접근 →
    // 홈으로 리다이렉트되고 그 자리에 머문다. 루프가 있으면 아래 goto 자체가
    // net::ERR_TOO_MANY_REDIRECTS로 throw해 이 테스트가 그대로 실패한다(별도 감지 코드 불필요).
    const resp = await page.goto('/admin');
    expect(resp?.ok(), '/admin 접근이 정상 응답으로 끝나야 함(리다이렉트 루프면 여기 도달 자체가 안 됨)').toBe(
      true,
    );
    expect(new URL(page.url()).pathname, '정지된 관리자는 홈에 머물러야 함(콘솔 미노출)').toBe('/');

    // 홈(/)에 다시 접근해도 /admin으로 되돌아가지 않는다 — page.tsx 관리자 랜딩 분기가
    // requireRole과 락스텝인지의 반대편 확인(왕복).
    await page.goto('/');
    expect(
      new URL(page.url()).pathname,
      '정지된 관리자의 홈 접근이 /admin으로 되튕기면 안 됨(무한 리다이렉트 축의 반대편)',
    ).toBe('/');
  });
});

// ── B. 판매자 쓰기 거부 안내 문구 (DW-804 (b)) ────────────────────────────
test.describe.serial('정지된 판매자의 쓰기 거부는 정지 사유로 안내된다(DW-804 (b))', () => {
  const email = `e2e-17-3-seller-${Date.now()}@test.local`;
  const password = 'seller123';
  const MODEL_MAIN = `E2E1733M-${Date.now()}`; // 정지 축 4경로(수정·삭제·구매완료·등록)가 재사용
  const MODEL_RACE = `E2E1733R-${Date.now()}`; // 긍정 대조군(이미 삭제됨) 전용
  const MODEL_NEW = `E2E1733N-${Date.now()}`; // 정지 중 신규 등록 시도(42501) 전용
  let mainListingId: string | undefined;

  test.afterAll(async () => {
    // listings는 auth.users cascade로 함께 삭제된다(write-flows.spec.ts와 동일 전제, FK confdeltype='c').
    runPsql(`delete from auth.users where email='${sqlLit(email)}';`);
    const leftover = runPsql(`select count(*) from auth.users where email='${sqlLit(email)}';`).trim();
    expect(leftover, '테스트 판매자 계정이 남으면 안 됨(원복 증명)').toBe('0');
  });

  test('[desktop] B1 계정을 만들고 정지 테스트용 매물을 등록한다', async ({ page }) => {
    await page.goto('/signup');
    await page.getByLabel('이메일').fill(email);
    await page.getByLabel('비밀번호').fill(password);
    await page.getByRole('button', { name: '가입하기' }).click();
    await page.waitForURL((url) => url.pathname === '/');

    await page.goto('/sell');
    await fillListingForm(page, MODEL_MAIN);
    await page.getByRole('button', { name: '매물 등록' }).click();
    await expect(page.getByRole('status')).toContainText('매물이 등록되었습니다', { timeout: 10_000 });

    const id = runPsql(`select id from listings where model='${sqlLit(MODEL_MAIN)}' order by created_at desc limit 1;`);
    expect(id, 'DB에 방금 등록한 매물이 없음').not.toBe('');
    mainListingId = id;
  });

  test('[desktop] B2 (긍정 대조군, 이미 삭제됨) 활성 계정 — 그새 사라진 자기 매물 삭제는 정지 문구가 아니라 기존 소유권 문구가 뜬다', async ({
    page,
  }) => {
    test.skip(!mainListingId, 'B1이 실패해 mainListingId가 없음');
    await login(page, email, password);
    await page.goto('/sell');

    await fillListingForm(page, MODEL_RACE);
    await page.getByRole('button', { name: '매물 등록' }).click();
    await expect(page.getByRole('status')).toContainText('매물이 등록되었습니다', { timeout: 10_000 });

    // 화면엔 이미 렌더돼 있는 채로, DB에서만 직접 지운다 — "다른 경로로 방금 삭제됨" 레이스를
    // 재현한다(이 계정은 아직 정지 전이므로 status='active'인 채로 0행을 받는 경로).
    const raceId = runPsql(`select id from listings where model='${sqlLit(MODEL_RACE)}' order by created_at desc limit 1;`);
    expect(raceId, 'DB에 레이스용 매물이 없음').not.toBe('');
    runPsql(`delete from listings where id='${raceId}';`);

    const row = page.locator('li').filter({ hasText: MODEL_RACE });
    page.once('dialog', (dialog) => dialog.accept());
    const [raceDeleteResponse] = await Promise.all([
      waitForListingsRequest(page, 'DELETE'),
      row.getByRole('button', { name: '삭제' }).click(),
    ]);
    await expectZeroRowRejection(
      raceDeleteResponse,
      '이미 삭제된 매물 삭제 시도가 실제로 DB까지 가서 0행으로 거부됐는지 확인(화면이 사전에 막은 게 아님)',
    );

    // page.getByRole('alert')는 안 쓴다 — Next.js가 항상 심어두는 `#__next-route-announcer__`도
    // role="alert"라 strict mode 위반이 난다(core-flows.spec.ts C2와 동일 이유). 텍스트로 찾는다.
    await expect(
      page.getByText('본인 매물만 삭제할 수 있습니다'),
      '이미 삭제된 매물 삭제 시도는 소유권/존재 문구로 안내돼야 함',
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText('정지된 계정입니다'),
      '활성 계정은 정지 문구가 뜨면 안 됨(긍정 대조군의 핵심)',
    ).toHaveCount(0);
  });

  test('[desktop] B3 계정을 정지시킨다', async () => {
    runPsql(`update profiles set status='suspended' where id=(select id from auth.users where email='${sqlLit(email)}');`);
    const status = runPsql(
      `select status from profiles where id=(select id from auth.users where email='${sqlLit(email)}');`,
    ).trim();
    expect(status, '테스트 계정을 suspended로 전환하지 못함').toBe('suspended');
  });

  test('[desktop] B4 정지된 판매자 — 구매 완료 시도는 정지 문구로 안내되고 매물 status는 그대로다', async ({
    page,
  }) => {
    test.skip(!mainListingId, 'B1이 실패해 mainListingId가 없음');
    await login(page, email, password);
    await page.goto('/sell');

    const row = page.locator('li').filter({ hasText: MODEL_MAIN });
    page.once('dialog', (dialog) => dialog.accept());
    const [completeResponse] = await Promise.all([
      waitForListingsRequest(page, 'PATCH'),
      row.getByRole('button', { name: '구매 완료' }).click(),
    ]);
    await expectZeroRowRejection(
      completeResponse,
      '구매완료 시도가 실제로 DB까지 가서 0행으로 거부됐는지 확인(화면이 사전에 막은 게 아님)',
    );

    // getByRole('alert')는 안 쓴다 — Next.js의 route-announcer도 role="alert"라 strict mode
    // 위반이 난다(위 B2 주석과 동일 이유).
    await expect(page.getByText('정지된 계정입니다')).toBeVisible({ timeout: 10_000 });

    const status = runPsql(`select status from listings where id='${mainListingId}';`);
    expect(status, '정지 회원의 구매완료 시도는 0행으로 거부돼야 함(status 불변)').toBe('on_sale');
  });

  test('[desktop] B5 정지된 판매자 — 삭제 시도는 정지 문구로 안내되고 매물은 그대로 남는다', async ({ page }) => {
    test.skip(!mainListingId, 'B1이 실패해 mainListingId가 없음');
    await login(page, email, password);
    await page.goto('/sell');

    const row = page.locator('li').filter({ hasText: MODEL_MAIN });
    page.once('dialog', (dialog) => dialog.accept());
    const [deleteResponse] = await Promise.all([
      waitForListingsRequest(page, 'DELETE'),
      row.getByRole('button', { name: '삭제' }).click(),
    ]);
    await expectZeroRowRejection(
      deleteResponse,
      '정지 회원의 삭제 시도가 실제로 DB까지 가서 0행으로 거부됐는지 확인(화면이 사전에 막은 게 아님)',
    );

    // getByRole('alert')는 안 쓴다 — Next.js의 route-announcer도 role="alert"라 strict mode
    // 위반이 난다(위 B2 주석과 동일 이유).
    await expect(page.getByText('정지된 계정입니다')).toBeVisible({ timeout: 10_000 });

    const remaining = runPsql(`select count(*) from listings where id='${mainListingId}';`).trim();
    expect(remaining, '정지 회원의 삭제 시도는 0행으로 거부돼야 함(매물이 그대로 있어야 함)').toBe('1');
  });

  test('[desktop] B6 정지된 판매자 — 본인 매물 수정 화면은 열리지만(열람은 안 막힘) 저장 시 정지 문구가 뜨고 값은 불변이다', async ({
    page,
  }) => {
    test.skip(!mainListingId, 'B1이 실패해 mainListingId가 없음');
    await login(page, email, password);
    await page.goto(`/sell/${mainListingId}/edit`);

    // 17.1이 열람은 안 좁혔다 — 정지 회원도 본인 매물 수정 화면 자체는 정상 렌더돼야 한다.
    await expect(page.getByRole('heading', { name: '매물 수정' })).toBeVisible();
    await expect(page.getByText('매물을 찾을 수 없거나 접근 권한이 없습니다')).toHaveCount(0);

    await page.getByLabel('가격 (원)').fill('9990000');
    const [updateResponse] = await Promise.all([
      waitForListingsRequest(page, 'PATCH'),
      page.getByRole('button', { name: '수정 저장' }).click(),
    ]);
    await expectZeroRowRejection(
      updateResponse,
      '정지 회원의 수정 저장 시도가 실제로 DB까지 가서 0행으로 거부됐는지 확인(화면이 사전에 막은 게 아님)',
    );

    // getByRole('alert')는 안 쓴다 — Next.js의 route-announcer도 role="alert"라 strict mode
    // 위반이 난다(위 B2 주석과 동일 이유).
    await expect(page.getByText('정지된 계정입니다')).toBeVisible({ timeout: 10_000 });

    // ⚠️ 양성 단언으로 확인한다(2026-08-11 후속 코드리뷰 patch). 이전 판은 `.not.toBe('9990000')`
    //    이었는데, 행이 통째로 사라져 runPsql이 빈 문자열을 돌려줘도 통과했다(B5가 이미 삭제를
    //    시도하는 파일이라 그 상태가 실제로 가능하다). 원래 값을 글자 그대로 박아 "안 바뀌었다"를
    //    실제로 측정한다 — fillListingForm이 넣는 12345000이다.
    const price = runPsql(`select price from listings where id='${mainListingId}';`).trim();
    expect(price, '정지 회원의 수정 시도는 0행으로 거부돼야 함(가격이 등록 당시 값 그대로여야 함)').toBe(
      '12345000',
    );
  });

  test('[desktop] B7 정지된 판매자 — 새 매물 등록 시도(42501)는 정지 문구로 안내되고 행이 생기지 않는다', async ({
    page,
  }) => {
    await login(page, email, password);
    await page.goto('/sell');

    await fillListingForm(page, MODEL_NEW);
    const [insertResponse] = await Promise.all([
      waitForListingsRequest(page, 'POST'),
      page.getByRole('button', { name: '매물 등록' }).click(),
    ]);
    // 등록만 신호가 다르다(0행이 아니라 42501 — with check 위반). 그 차이를 검사가 직접 구분한다
    // (스펙 AC: "경로마다 신호가 다르다는 것까지 검사가 구분한다"). 코드는 글자 그대로 박는다.
    //
    // ⚠️ 다른 4개 0행 경로(expectZeroRowRejection)는 status()와 본문을 **함께** 본다(2026-08-11
    // 3차 코드리뷰 patch) — 여기만 본문의 code만 봤다. 그리고 `.json()`은 응답이 JSON이 아니면
    // (프록시 에러·HTML 등) 파싱 자체가 opaque하게 throw해, 실패 메시지가 "42501이 아니다"가 아니라
    // 알아보기 힘든 JSON 파싱 스택으로 남는다. 여기서는 실제로 관측된 값을 그대로 박는다 —
    // PostgREST는 42501(insufficient_privilege)을 HTTP 403으로 매핑한다(로컬 스택에서 실측 확인).
    const insertStatus = insertResponse.status();
    const insertRawBody = await insertResponse.text();
    let insertBody: { code?: string } | undefined;
    try {
      insertBody = JSON.parse(insertRawBody);
    } catch {
      insertBody = undefined; // 아래 단언이 원문(raw body)을 실패 메시지에 그대로 실어 나른다.
    }
    expect(
      insertStatus,
      `등록 시도의 응답 상태가 403(42501의 PostgREST 매핑)이 아니다(원문: ${insertRawBody})`,
    ).toBe(403);
    expect(
      insertBody?.code,
      `등록 시도가 42501(with check 위반)로 거부되지 않았다 — 화면이 사전에 막았거나 DB가 안 막았다(원문: ${insertRawBody})`,
    ).toBe('42501');

    // getByRole('alert')는 안 쓴다 — Next.js의 route-announcer도 role="alert"라 strict mode
    // 위반이 난다(위 B2 주석과 동일 이유).
    await expect(page.getByText('정지된 계정입니다')).toBeVisible({ timeout: 10_000 });

    const created = runPsql(`select count(*) from listings where model='${sqlLit(MODEL_NEW)}';`).trim();
    expect(created, '정지 회원의 등록 시도(42501)는 거부되고 행이 생기면 안 됨').toBe('0');
  });
});

// 이 스위트가 **안 보는 것**(실측 기반):
//   · "타인 매물"을 직접 조작해 소유권 문구를 재확인하는 경로 — /sell 목록(page.tsx)이
//     seller_id로 필터링하고 /sell/[id]/edit도 동일 필터라 UI로는 애초에 타인 listingId가
//     ListingActions/SellForm에 전달될 수 없다(코드 확인). B2(이미 삭제됨)가 같은 fallback
//     문구 경로를 검증하는 것으로 대신한다 — 두 사유가 이 계층에서 같은 신호(status='active' +
//     0행)이기 때문에(web/src/lib/auth/status.test.ts 참고) 실질적으로 같은 것을 본다.
//   · 정지된 판매자의 채팅 발신 문구 — 17.1이 DB에서 이미 막았지만(chat_messages_insert_participant)
//     이 스토리 범위는 /sell 화면뿐이다(스펙 Never 절).
//   · 앱(Flutter)의 동일 경로 — 스펙 Never 절이 명시적으로 범위 밖으로 뒀다. 대장에 별도 항목으로
//     등재한다(DW-812, deferred-work.md).
