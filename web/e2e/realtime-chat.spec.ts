// 실시간 채팅(Epic 12, Story 12.1~12.6) 브라우저 실측 E2E — 폴링 → Supabase Realtime Broadcast로
// 갈아끼운 뒤, 실제 실시간 동작 자체를 아무도 브라우저로 확인하지 않은 공백을 메운다(대장 스윕 지시).
//
// 검증 범위:
//   R1. 두 브라우저 실시간 왕복 지연 실측(구매자↔판매자, 양방향) — 옛 폴링 주기(3초)보다 확실히 빠른지.
//   R2. 재연결 배너 + 오프라인 큐잉 + 갭보정(Story 12.4) — 가장 까다로운 케이스. 안 되면 억지로
//       통과시키지 않고 어디까지 확인됐는지 그대로 실패로 드러낸다.
//   R3. 안읽음 배지 + 방 목록 정렬(Story 12.5).
//   R4. 멱등키(Story 12.1) — 같은 (room_id, client_message_id) 재삽입이 DB에서 거부되는지, 화면에도
//       1건만 보이는지.
//
// 절대 규칙(임무 지시, `web/src/**` 등 제품 코드는 읽기만 함):
//   - 시드 채팅방(buyer@test.com ↔ seller-seed2@test.com, fetchChatRoomIdForSeedUser())을 그대로 쓰되,
//     이 스펙이 만든 메시지(본문 접두어 `RT-E2E-`)만 끝에서 지운다 — 시드 채팅방·시드 메시지는 보존.
//   - desktop-1280x800 프로젝트 전용. beforeEach·afterAll 둘 다 프로젝트 가드를 건다 — test.skip은
//     테스트만 건너뛰고 afterAll은 프로젝트마다 실행되므로, 가드가 없으면 tablet/mobile 프로젝트의
//     afterAll이 desktop 프로젝트가 아직 쓰고 있는 데이터를 지우는 사고가 날 수 있다(대장 참조).
//   - 네 케이스가 같은 방(roomId)을 공유하므로 test.describe.serial로 순서를 고정한다 — 병렬 워커가
//     같은 방에 동시에 쓰면 R3의 안읽음 카운트·R1의 지연 측정이 서로 오염된다.
import { test, expect, type Locator } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { assertLocalSupabase, login, runPsql, fetchChatRoomIdForSeedUser, SEED_USER } from './helpers';
import { PROJECT_NAMES } from './project-names';

// 운영 안전 가드 — 모듈 최상단에서 즉시 확인한다(임무 지시 절대 규칙 3). 이 스펙은 실제로
// chat_messages에 쓰고 지우므로, NEXT_PUBLIC_SUPABASE_URL이 로컬이 아니면 여기서 곧장 죽는다.
assertLocalSupabase();

const BUYER = SEED_USER; // buyer@test.com / seller123 (helpers.ts)
// 시드 방(fetchChatRoomIdForSeedUser가 고르는 방)의 상대 판매자 — supabase/seed-local/01_accounts.sql,
// 모든 시드 계정이 같은 비밀번호(SEED_PASSWORD=seller123, supabase/.env.seed)를 쓴다.
const SELLER = { email: 'seller-seed2@test.com', password: 'seller123' };

/** SQL 문자열 리터럴용 작은따옴표 이스케이프(helpers.ts의 비공개 동명 헬퍼와 동일 관례). */
function sqlLit(s: string): string {
  return s.replace(/'/g, "''");
}

/** 이 스펙이 보낸 메시지를 한눈에 구분·정리(cleanup)할 수 있는 유니크 태그. */
function uniqueTag(label: string): string {
  return `RT-E2E-${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function countRows(table: string): number {
  return Number(runPsql(`select count(*) from ${table};`));
}

/**
 * locator가 보일 때까지 짧은 간격(25ms)으로 폴링하며 경과 시간(ms)을 잰다 — Playwright의
 * expect().toBeVisible() 기본 폴링(지수 백오프, 최대 수백ms 간격)보다 촘촘하게 재서, R1의 실측
 * 지연값이 단언 자체의 폴링 오차에 크게 좌우되지 않게 한다.
 */
async function waitForVisibleWithElapsed(locator: Locator, timeoutMs: number): Promise<number> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await locator.isVisible().catch(() => false)) {
      return Date.now() - start;
    }
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error(`요소가 ${timeoutMs}ms 안에 보이지 않음`);
}

/** SiteNav 채팅 링크의 aria-label("채팅" 또는 "채팅, 안읽음 메시지 N건")에서 N을 뽑는다. */
function parseUnreadFromAriaLabel(label: string | null): number {
  if (!label) throw new Error('채팅 링크의 aria-label을 읽지 못함(null)');
  if (label === '채팅') return 0;
  const m = label.match(/(\d+)건/);
  if (!m) throw new Error(`채팅 링크 aria-label 형식을 해석하지 못함: "${label}"`);
  return Number(m[1]);
}

test.describe.serial('실시간 채팅 검증 (Story 12.3~12.6, 대장 스윕)', () => {
  let roomId: string;
  let baseline: { messages: number; rooms: number; reads: number };

  test.beforeAll(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, 'desktop-1280x800 전용 스펙');
    roomId = fetchChatRoomIdForSeedUser();
    baseline = {
      messages: countRows('chat_messages'),
      rooms: countRows('chat_rooms'),
      reads: countRows('chat_room_reads'),
    };
    console.log(`[realtime-chat] roomId=${roomId} baseline=${JSON.stringify(baseline)}`);
  });

  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, 'desktop-1280x800 전용 스펙');
  });

  // ⚠️ afterAll에도 같은 가드가 필요하다(임무 지시 절대 규칙 5) — test.skip은 테스트만 건너뛰고
  // afterAll은 프로젝트마다 실행된다. 가드가 없으면 tablet/mobile 프로젝트의 afterAll이 desktop
  // 프로젝트가 아직 쓰고 있는 데이터를 지울 수 있다(과거 실제 사고, 대장 참조) — 이 스펙에서는
  // 필수 방어선이다.
  test.afterAll(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, 'desktop-1280x800 전용 스펙');

    const deleted = runPsql(
      `delete from chat_messages where room_id='${roomId}' and body like 'RT-E2E-%' returning id;`,
    );
    console.log(`[realtime-chat cleanup] 삭제된 RT-E2E- 메시지 id:\n${deleted || '(없음)'}`);

    const after = {
      messages: countRows('chat_messages'),
      rooms: countRows('chat_rooms'),
      reads: countRows('chat_room_reads'),
    };
    console.log(`[realtime-chat cleanup] baseline=${JSON.stringify(baseline)} after=${JSON.stringify(after)}`);

    expect(after.messages, '정리 후 chat_messages 개수가 시작 시점과 일치해야 함(시드 메시지 보존)').toBe(
      baseline.messages,
    );
    expect(after.rooms, '정리 후 chat_rooms 개수가 시작 시점과 일치해야 함(새 방을 만들지 않음)').toBe(
      baseline.rooms,
    );
    expect(
      after.reads,
      '정리 후 chat_room_reads 개수가 시작 시점과 일치해야 함(구매자·판매자 모두 이미 이 방의 읽음 행을 갖고 있어 방문할 때마다 upsert가 갱신만 하고 새 행을 만들지 않아야 함)',
    ).toBe(baseline.reads);
  });

  test('R1 두 브라우저 실시간 왕복 — 지연 실측(양방향)', async ({ browser }) => {
    const buyerCtx = await browser.newContext();
    const sellerCtx = await browser.newContext();
    try {
      const buyerPage = await buyerCtx.newPage();
      const sellerPage = await sellerCtx.newPage();
      await login(buyerPage, BUYER.email, BUYER.password);
      await login(sellerPage, SELLER.email, SELLER.password);

      await Promise.all([buyerPage.goto(`/chat/${roomId}`), sellerPage.goto(`/chat/${roomId}`)]);
      await Promise.all([
        buyerPage.waitForLoadState('networkidle'),
        sellerPage.waitForLoadState('networkidle'),
      ]);
      // Realtime 구독(getSession→setAuth→채널 join)이 화면에 신호를 남기지 않으므로, 소켓 핸드셰이크가
      // 끝났다고 가정할 수 있는 고정 여유를 둔다(로컬 스택이라 통상 1초 미만이지만 여유 있게 잡는다).
      await Promise.all([buyerPage.waitForTimeout(2000), sellerPage.waitForTimeout(2000)]);

      // 방향 1: 구매자 → 판매자
      const tagBuyerToSeller = uniqueTag('R1-BS');
      await buyerPage.getByLabel('메시지 입력').fill(tagBuyerToSeller);
      await buyerPage.getByRole('button', { name: '전송' }).click();
      const elapsedBuyerToSeller = await waitForVisibleWithElapsed(
        sellerPage.getByText(tagBuyerToSeller),
        5000,
      );
      console.log(`[R1] 구매자→판매자 실측 지연: ${elapsedBuyerToSeller}ms`);
      expect(
        elapsedBuyerToSeller,
        `R1 구매자→판매자 지연(${elapsedBuyerToSeller}ms)이 옛 폴링 주기(3000ms)보다 확실히 작아야 함`,
      ).toBeLessThan(3000);

      // 방향 2: 판매자 → 구매자
      const tagSellerToBuyer = uniqueTag('R1-SB');
      await sellerPage.getByLabel('메시지 입력').fill(tagSellerToBuyer);
      await sellerPage.getByRole('button', { name: '전송' }).click();
      const elapsedSellerToBuyer = await waitForVisibleWithElapsed(
        buyerPage.getByText(tagSellerToBuyer),
        5000,
      );
      console.log(`[R1] 판매자→구매자 실측 지연: ${elapsedSellerToBuyer}ms`);
      expect(
        elapsedSellerToBuyer,
        `R1 판매자→구매자 지연(${elapsedSellerToBuyer}ms)이 옛 폴링 주기(3000ms)보다 확실히 작아야 함`,
      ).toBeLessThan(3000);
    } finally {
      await buyerCtx.close();
      await sellerCtx.close();
    }
  });

  test('R2 재연결 배너 + 오프라인 큐잉 + 갭보정', async ({ browser }) => {
    // 끊김 감지·재연결 배너 소멸까지 기본 30초 타임아웃으로는 부족할 수 있다(tech-debt #204: 끊김
    // 감지가 25~35초 걸리는 경로가 알려져 있음) — 넉넉히 잡는다.
    test.setTimeout(240_000);

    const buyerCtx = await browser.newContext();
    const sellerCtx = await browser.newContext();
    try {
      const buyerPage = await buyerCtx.newPage();
      const sellerPage = await sellerCtx.newPage();
      await login(buyerPage, BUYER.email, BUYER.password);
      await login(sellerPage, SELLER.email, SELLER.password);

      await Promise.all([buyerPage.goto(`/chat/${roomId}`), sellerPage.goto(`/chat/${roomId}`)]);
      await Promise.all([
        buyerPage.waitForLoadState('networkidle'),
        sellerPage.waitForLoadState('networkidle'),
      ]);
      await Promise.all([buyerPage.waitForTimeout(2000), sellerPage.waitForTimeout(2000)]);

      // 판매자 네트워크 차단 — ChatRoomMessages.tsx의 channel.subscribe 콜백이 CHANNEL_ERROR/TIMED_OUT을
      // 받아야 배너가 뜬다(소스 확인, Design Notes: CLOSED는 명시적 leave()에서만 발생해 네트워크 드롭
      // 시나리오엔 해당 없음). context.setOffline은 CDP로 오프라인을 흉내내 열린 웹소켓 연결도 끊는다.
      await sellerCtx.setOffline(true);

      const disconnectBanner = sellerPage.getByText(/연결이 끊겼어요/);
      await expect(disconnectBanner, 'R2: 연결 끊김 배너가 떠야 함').toBeVisible({ timeout: 90_000 });

      // 비차단(FR42·UX-DR19) — 입력창·전송 버튼이 잠기지 않아야 한다.
      await expect(
        sellerPage.getByLabel('메시지 입력'),
        'R2: 끊긴 동안 입력창이 잠기지 않아야 함(비차단)',
      ).toBeEnabled();
      await expect(
        sellerPage.getByRole('button', { name: '전송' }),
        'R2: 끊긴 동안 전송 버튼이 잠기지 않아야 함(비차단)',
      ).toBeEnabled();

      // 끊긴 동안 판매자가 메시지 제출 — 네트워크 호출 없이 즉시 pending 큐에 들어가야 한다.
      const queuedTag = uniqueTag('R2-QUEUED');
      await sellerPage.getByLabel('메시지 입력').fill(queuedTag);
      await sellerPage.getByRole('button', { name: '전송' }).click();
      await expect(
        sellerPage.getByText(queuedTag),
        'R2: 끊긴 동안 제출한 메시지가 즉시 pending 버블로 보여야 함',
      ).toBeVisible();

      // 그 사이 구매자가 메시지 1건 전송(판매자는 오프라인이라 방송을 못 받는다 — 재연결 후 갭보정 대상).
      const gapTag = uniqueTag('R2-GAP');
      await buyerPage.getByLabel('메시지 입력').fill(gapTag);
      await buyerPage.getByRole('button', { name: '전송' }).click();
      await expect(buyerPage.getByText(gapTag), 'R2: 구매자 자기 화면엔 즉시 보여야 함').toBeVisible();

      // 판매자를 다시 온라인으로.
      await sellerCtx.setOffline(false);

      const reconnectedBanner = sellerPage.getByText('다시 연결됐어요');
      await expect(reconnectedBanner, 'R2: 재연결(초록) 배너가 떠야 함').toBeVisible({ timeout: 60_000 });
      await expect(
        reconnectedBanner,
        'R2: 재연결 배너가 일정 시간 후(RECONNECT_BANNER_DISMISS_MS=3000ms) 사라져야 함',
      ).toBeHidden({ timeout: 8_000 });

      // 갭보정 — 끊긴 동안 놓친 구매자 메시지가 화면에 채워져야 한다.
      await expect(
        sellerPage.getByText(gapTag),
        'R2: 갭보정으로 끊긴 동안 상대(구매자)가 보낸 메시지가 채워져야 함',
      ).toBeVisible({ timeout: 15_000 });

      // 오프라인 큐 flush — 끊긴 동안 판매자가 큐에 넣었던 메시지가 실제로 DB에 저장돼야 한다.
      await sellerPage.waitForTimeout(3000); // flush(순차 await) 완료 여유.
      const flushedRow = runPsql(
        `select body from chat_messages where room_id='${roomId}' and body='${sqlLit(queuedTag)}';`,
      );
      expect(flushedRow, 'R2: 끊긴 동안 큐잉된 메시지가 재연결 후 실제로 전송돼 DB에 저장돼야 함').toBe(
        queuedTag,
      );
    } finally {
      // R2가 실패로 끝나도 컨텍스트가 offline 상태로 남지 않게 먼저 온라인으로 되돌린 뒤 닫는다.
      await sellerCtx.setOffline(false).catch(() => {});
      await buyerCtx.close();
      await sellerCtx.close();
    }
  });

  test('R3 안읽음 배지 + 방 목록 정렬', async ({ browser }) => {
    test.setTimeout(60_000);

    const buyerCtx = await browser.newContext();
    const sellerCtx = await browser.newContext();
    try {
      const buyerPage = await buyerCtx.newPage();
      const sellerPage = await sellerCtx.newPage();
      await login(buyerPage, BUYER.email, BUYER.password);
      await login(sellerPage, SELLER.email, SELLER.password);

      // 이 방을 먼저 읽음 처리해(진입) R1·R2가 남긴 미열람 잔상을 지운다 — 이후 baseline은 "이 방
      // 기여분 0" 상태에서 잰다(다른 방의 미열람 총합은 델타 비교라 영향 없음).
      await buyerPage.goto(`/chat/${roomId}`);
      await buyerPage.waitForLoadState('networkidle');

      await buyerPage.goto('/search');
      await buyerPage.waitForLoadState('networkidle');
      const chatLink = buyerPage.getByRole('link', { name: /채팅/ });
      const baselineLabel = await chatLink.getAttribute('aria-label');
      const baselineCount = parseUnreadFromAriaLabel(baselineLabel);
      console.log(`[R3] baseline unreadCount=${baselineCount} (label="${baselineLabel}")`);

      // 판매자가 방에 메시지 전송 — 구매자는 방 밖(/search)에 있다.
      await sellerPage.goto(`/chat/${roomId}`);
      await sellerPage.waitForLoadState('networkidle');
      const tag = uniqueTag('R3-UNREAD');
      await sellerPage.getByLabel('메시지 입력').fill(tag);
      await sellerPage.getByRole('button', { name: '전송' }).click();
      await expect(sellerPage.getByText(tag)).toBeVisible();

      // 배지는 서버 컴포넌트(AppHeader)가 매 렌더 계산한다 — 실시간 폴링이 아니므로 새로고침해야 반영된다.
      await buyerPage.reload();
      await buyerPage.waitForLoadState('networkidle');
      const afterLabel = await chatLink.getAttribute('aria-label');
      const afterCount = parseUnreadFromAriaLabel(afterLabel);
      console.log(`[R3] after unreadCount=${afterCount} (label="${afterLabel}")`);
      expect(afterCount, 'R3: 판매자가 보낸 메시지 1건만큼 안읽음 총합이 늘어야 함').toBe(baselineCount + 1);

      // 방 목록 정렬 — 방금 메시지가 온 방이 최상단(last_message_at desc).
      await buyerPage.goto('/chat');
      await buyerPage.waitForLoadState('networkidle');
      const firstRoomLink = buyerPage.locator('main ul > li a').first();
      await expect(
        firstRoomLink,
        'R3: 최신 메시지가 온 방이 방 목록 최상단이어야 함(last_message_at desc)',
      ).toHaveAttribute('href', `/chat/${roomId}`);

      // 구매자가 방에 들어가 읽음 처리 → 배지가 원래 총합으로 돌아와야 한다.
      await buyerPage.goto(`/chat/${roomId}`);
      await buyerPage.waitForLoadState('networkidle');
      await buyerPage.goto('/search');
      await buyerPage.waitForLoadState('networkidle');
      const finalLabel = await chatLink.getAttribute('aria-label');
      const finalCount = parseUnreadFromAriaLabel(finalLabel);
      console.log(`[R3] final unreadCount=${finalCount} (label="${finalLabel}")`);
      expect(finalCount, 'R3: 읽음 처리 후 배지가 원래 총합(baseline)으로 돌아와야 함').toBe(baselineCount);
    } finally {
      await buyerCtx.close();
      await sellerCtx.close();
    }
  });

  test('R4 멱등키 — 같은 client_message_id 재삽입은 DB가 거부하고 화면엔 1건만 남는다', async ({
    page,
  }) => {
    const buyerId = runPsql(`select id from auth.users where email='${sqlLit(BUYER.email)}' limit 1;`);
    expect(buyerId, 'buyer 사용자 id 조회').toBeTruthy();

    const clientMessageId = randomUUID();
    const body = uniqueTag('R4-IDEMP');

    // 1차 삽입 — 정상 성공해야 한다.
    runPsql(
      `insert into chat_messages (room_id, sender_id, body, client_message_id) values ('${roomId}','${buyerId}','${sqlLit(body)}','${clientMessageId}');`,
    );

    // 2차 삽입(같은 room_id·client_message_id) — UNIQUE(chat_messages_room_client_message_unique)
    // 위반으로 거부돼야 한다(runPsql은 psql이 비정상 종료하면 그대로 throw한다).
    let secondInsertRejected = false;
    try {
      runPsql(
        `insert into chat_messages (room_id, sender_id, body, client_message_id) values ('${roomId}','${buyerId}','${sqlLit(body)}','${clientMessageId}');`,
      );
    } catch {
      secondInsertRejected = true;
    }
    expect(
      secondInsertRejected,
      'R4: 같은 (room_id, client_message_id) 재삽입은 UNIQUE 위반으로 거부돼야 함',
    ).toBe(true);

    const dbCount = Number(
      runPsql(
        `select count(*) from chat_messages where room_id='${roomId}' and client_message_id='${clientMessageId}';`,
      ),
    );
    expect(dbCount, 'R4: DB에는 정확히 1건만 있어야 함').toBe(1);

    await login(page, BUYER.email, BUYER.password);
    await page.goto(`/chat/${roomId}`);
    await page.waitForLoadState('networkidle');
    await expect(page.getByText(body), 'R4: 화면에도 정확히 1건만 보여야 함').toHaveCount(1);
  });
});
