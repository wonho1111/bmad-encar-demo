// 채팅 멱등 전송(client_message_id) 단위테스트 (Story 12.3 — B9 "실행되는 검사").
//
// 이 파일이 검사하는 것:
//   `sendMessage`가 (1) client_message_id를 INSERT에 실제로 싣는지, (2) 23505(유니크 위반)를
//   에러로 올리지 않고 (room_id, client_message_id)로 기존 행을 조회해 그 행으로 수렴시키는지,
//   (3) 그 조회마저 실패하면 안전하게 일반 에러로 폴백하는지, (4) 조회된 행이 sender_id·body가
//   호출자 자신의 전송과 어긋나면(= 자기 행이 아니면) 성공으로 취급하지 않는지, (5) 23505가 아닌
//   다른 에러는 기존(12.3 이전)과 동일하게 일반 에러로 처리되는지(회귀 없음)를 확인한다.
//
// **이 검사가 안 보는 것**: 실제 DB의 RLS·UNIQUE 제약 자체(진짜 23505가 나는지)는 여기서
// 검증하지 않는다 — supabase 클라이언트 체인을 손으로 흉내 낸 mock이라, "23505가 오면 이
// 함수가 무엇을 하는가"라는 순수 로직만 본다. 실제로 두 번 INSERT해 1행 수렴을 확인하는 것은
// 로컬 Supabase 스택으로 손수 검증한다(Story 문서의 red/green 실측 기록, Verification 절 참조).
import { describe, expect, it, vi } from 'vitest';
import type { SupabaseClient } from '@supabase/supabase-js';
import {
  dedupeById,
  fetchMessages,
  flushMessageQueue,
  reuseFailedKey,
  sendMessage,
  type ChatMessageRow,
  type QueuedMessage,
  type SendMessageResult,
} from '../messages';

type ChainResult = { data: unknown; error: unknown };

/**
 * sendMessage가 거치는 두 경로(INSERT→select→single / 재조회 select→eq→eq→single)를 흉내 내는
 * 최소 mock. 둘 다 `.from('chat_messages')`를 부르므로 같은 `from`이 두 메서드(`insert`·`select`)를
 * 함께 들고 있으면 충분하다(실제 호출에서 한 번의 sendMessage 실행은 둘 중 하나만 밟는다).
 */
function makeSupabaseMock({
  insertResult,
  selectResult,
}: {
  insertResult: ChainResult;
  selectResult?: ChainResult;
}) {
  const singleForSelect = vi.fn().mockResolvedValue(selectResult ?? { data: null, error: null });
  const eq2 = vi.fn(() => ({ single: singleForSelect }));
  const eq1 = vi.fn(() => ({ eq: eq2 }));
  const selectForLookup = vi.fn(() => ({ eq: eq1 }));

  const singleForInsert = vi.fn().mockResolvedValue(insertResult);
  const selectForInsert = vi.fn(() => ({ single: singleForInsert }));
  const insert = vi.fn(() => ({ select: selectForInsert }));

  const from = vi.fn(() => ({ insert, select: selectForLookup }));

  return {
    client: { from } as unknown as SupabaseClient,
    insert,
    selectForLookup,
    eq1,
    eq2,
  };
}

function row(overrides: Partial<ChatMessageRow> = {}): ChatMessageRow {
  return {
    id: 'm1',
    room_id: 'r1',
    sender_id: 'u1',
    body: '안녕하세요',
    created_at: '2026-07-29T00:00:00.000Z',
    client_message_id: 'c1',
    ...overrides,
  };
}

describe('sendMessage — client_message_id 전달', () => {
  it('INSERT 페이로드에 client_message_id를 그대로 싣는다', async () => {
    const saved = row();
    const { client, insert } = makeSupabaseMock({ insertResult: { data: saved, error: null } });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ message: saved });
    expect(insert).toHaveBeenCalledWith(
      expect.objectContaining({
        room_id: 'r1',
        sender_id: 'u1',
        body: '안녕하세요',
        client_message_id: 'c1',
      }),
    );
  });
});

describe('sendMessage — 멱등 재전송 흡수(23505)', () => {
  it('23505면 (room_id, client_message_id)로 기존 행을 조회해 그 행으로 확정한다(에러 아님)', async () => {
    const existing = row({ id: 'm-existing' });
    const { client, eq1, eq2 } = makeSupabaseMock({
      insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
      selectResult: { data: existing, error: null },
    });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ message: existing });
    // 재조회가 room_id 다음 client_message_id 순으로 좁혀졌는지(체인 순서 회귀 방지).
    expect(eq1).toHaveBeenCalledWith('room_id', 'r1');
    expect(eq2).toHaveBeenCalledWith('client_message_id', 'c1');
  });

  it('23505인데 기존 행 조회마저 실패하면 일반 한국어 에러로 폴백한다(이례적 상황 방어)', async () => {
    const { client } = makeSupabaseMock({
      insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
      selectResult: { data: null, error: { message: 'network hiccup' } },
    });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' });
  });

  it('23505가 아닌 다른 에러(RLS 거부 등)는 기존과 동일하게 일반 에러로 처리한다(회귀 없음)', async () => {
    const { client } = makeSupabaseMock({
      insertResult: { data: null, error: { code: '42501', message: 'permission denied' } },
    });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' });
  });

  // 코드리뷰 patch(low): 재조회한 행이 "호출자 자신의 확정된 전송"이 맞는지(sender_id·body 일치)
  // 확인하지 않으면, 이론상 다른 사람의 행을 성공으로 오인해 반환할 수 있다 — 그 확인이 실제로
  // 동작하는지 sender_id·body 각각 어긋나는 경우로 확인한다.
  it('기존 행의 sender_id가 다르면(호출자 자신의 전송이 아님) 성공으로 취급하지 않고 에러로 폴백한다', async () => {
    const existing = row({ id: 'm-existing', sender_id: 'someone-else' });
    const { client } = makeSupabaseMock({
      insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
      selectResult: { data: existing, error: null },
    });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' });
  });

  it('기존 행의 body가 다르면(같은 키로 다른 내용이 저장된 이례적 상황) 성공으로 취급하지 않고 에러로 폴백한다', async () => {
    const existing = row({ id: 'm-existing', body: '다른 내용' });
    const { client } = makeSupabaseMock({
      insertResult: { data: null, error: { code: '23505', message: 'duplicate key value' } },
      selectResult: { data: existing, error: null },
    });

    const res = await sendMessage(client, 'r1', 'u1', '안녕하세요', 'c1');

    expect(res).toEqual({ error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' });
  });
});

// ── 아래 세 블록은 코드리뷰 2차 패스에서 추가(verification-gap 지적) ───────────────────
// 폴링이 있을 땐 "3초마다 서버가 준 순서 그대로 다시 그린다"가 사실상의 안전망이었다. 폴링을
// 걷어낸 지금은 (1) dedupeById의 정렬이 화면 시간순의 **유일한** 보장이고, (2) fetchMessages의
// gte 커서 분기는 유일한 실행 경로(폴링)를 잃어 12.4가 재채택할 때까지 아무도 안 밟으며,
// (3) 멱등키 재사용 판정은 서로 반대 방향의 두 결함 사이를 가르는 자리다. 셋 다 순수 함수라
// 이 레포의 web 테스트 규칙(순수 유틸만 vitest)에 정확히 들어맞는데 검사가 없었다.

describe('dedupeById — 시간순 불변식(AC#3)과 중복 제거', () => {
  it('도착 순서와 무관하게 (created_at, id) 오름차순으로 정렬한다', () => {
    const later = row({ id: 'm2', created_at: '2026-07-29T00:00:02.000Z' });
    const earlier = row({ id: 'm1', created_at: '2026-07-29T00:00:01.000Z' });
    // 실시간 방송이 초기 로드보다 먼저 도착한 상황 = 늦은 메시지가 배열 앞에 온다.
    expect(dedupeById([later, earlier]).map((m) => m.id)).toEqual(['m1', 'm2']);
  });

  it('created_at이 같으면 id로 안정 정렬한다(동시 전송 경계)', () => {
    const b = row({ id: 'm-b', created_at: '2026-07-29T00:00:01.000Z' });
    const a = row({ id: 'm-a', created_at: '2026-07-29T00:00:01.000Z' });
    expect(dedupeById([b, a]).map((m) => m.id)).toEqual(['m-a', 'm-b']);
  });

  it('같은 id가 두 번 들어오면 첫 등장만 남긴다(자기 응답과 브로드캐스트 에코의 이중 도착)', () => {
    const first = row({ id: 'm1', body: '먼저 도착' });
    const echo = row({ id: 'm1', body: '나중 도착(같은 행)' });
    const out = dedupeById([first, echo]);
    expect(out).toHaveLength(1);
    expect(out[0].body).toBe('먼저 도착');
  });
});

describe('fetchMessages — 증분 커서 분기(Story 12.4가 재채택할 자리)', () => {
  function makeFetchMock(result: ChainResult) {
    const builder = {
      eq: vi.fn((): unknown => builder),
      gte: vi.fn((): unknown => builder),
      order: vi.fn((): unknown => builder),
      returns: vi.fn().mockResolvedValue(result),
    };
    const select = vi.fn(() => builder);
    return { client: { from: vi.fn(() => ({ select })) } as unknown as SupabaseClient, builder };
  }

  it('커서를 주면 gte(>=)로 좁힌다 — gt(>)면 동시각 경계 행을 영영 놓친다(실측 근거는 주석 참조)', async () => {
    const { client, builder } = makeFetchMock({ data: [row()], error: null });

    const res = await fetchMessages(client, 'r1', '2026-07-29T00:00:01.000Z');

    expect(res).toEqual({ messages: [row()] });
    expect(builder.gte).toHaveBeenCalledWith('created_at', '2026-07-29T00:00:01.000Z');
  });

  it('커서가 없으면 gte를 걸지 않는다(방 진입 시 전체 로드)', async () => {
    const { client, builder } = makeFetchMock({ data: [], error: null });

    await fetchMessages(client, 'r1');

    expect(builder.gte).not.toHaveBeenCalled();
  });

  it('조회 실패를 "메시지 0건"과 구분해 { error: true }로 돌려준다', async () => {
    const { client } = makeFetchMock({ data: null, error: { message: 'boom' } });

    expect(await fetchMessages(client, 'r1')).toEqual({ error: true });
  });
});

describe('reuseFailedKey — 실패한 멱등키 재사용 판정', () => {
  const failed = { clientMessageId: 'c-failed', body: '안녕하세요', at: 1_000_000 };
  const WINDOW = 60_000;

  it('같은 본문을 창 안에서 다시 보내면 그 키를 재사용한다(재전송이 중복 행을 만들지 않게)', () => {
    expect(reuseFailedKey(failed, '안녕하세요', 1_030_000, WINDOW)).toBe('c-failed');
  });

  it('창 경계(정확히 windowMs 경과)까지는 재사용한다', () => {
    expect(reuseFailedKey(failed, '안녕하세요', 1_060_000, WINDOW)).toBe('c-failed');
  });

  it('창을 넘기면 재사용하지 않는다 — 넘겨 쓰면 나중의 같은 본문이 옛 행으로 흡수돼 조용히 사라진다', () => {
    expect(reuseFailedKey(failed, '안녕하세요', 1_060_001, WINDOW)).toBeNull();
  });

  it('본문을 고쳐서 보내면 새 메시지이므로 재사용하지 않는다', () => {
    expect(reuseFailedKey(failed, '안녕하세요!', 1_030_000, WINDOW)).toBeNull();
  });

  it('직전 실패 기록이 없으면 재사용할 것이 없다', () => {
    expect(reuseFailedKey(null, '안녕하세요', 1_030_000, WINDOW)).toBeNull();
  });
});

// Story 12.4 — 오프라인 큐 flush 알고리즘(순서 보존 + 실패 항목 재큐잉). 화면(ChatRoomMessages)에서
// 네트워크·React 상태를 떼어낸 순수 로직만 검증한다(B9).
describe('flushMessageQueue — 오프라인 큐 순차 flush(Story 12.4 Always)', () => {
  function queued(clientMessageId: string, body: string): QueuedMessage {
    return { clientMessageId, body };
  }

  it('전부 성공하면 큐가 순서대로 전송되고 remaining이 빈 배열이 된다', async () => {
    const q = [queued('c1', '하나'), queued('c2', '둘'), queued('c3', '셋')];
    const sendOrder: string[] = [];
    const sendFn = vi.fn(async (msg: QueuedMessage): Promise<SendMessageResult> => {
      sendOrder.push(msg.clientMessageId);
      return { message: row({ id: `m-${msg.clientMessageId}`, client_message_id: msg.clientMessageId, body: msg.body }) };
    });

    const result = await flushMessageQueue(q, sendFn);

    expect(sendOrder).toEqual(['c1', 'c2', 'c3']); // 동시 발송이 아니라 순차(순서 보존).
    expect(result.remaining).toEqual([]);
    expect(result.sent.map((m) => m.client_message_id)).toEqual(['c1', 'c2', 'c3']);
  });

  it('중간 항목이 실패하면 그 항목부터 뒤 전부를 remaining에 남기고 즉시 멈춘다(순서 보존)', async () => {
    const q = [queued('c1', '하나'), queued('c2', '둘'), queued('c3', '셋')];
    const sendFn = vi.fn(async (msg: QueuedMessage): Promise<SendMessageResult> => {
      if (msg.clientMessageId === 'c2') return { error: '네트워크 오류' };
      return { message: row({ id: `m-${msg.clientMessageId}`, client_message_id: msg.clientMessageId, body: msg.body }) };
    });

    const result = await flushMessageQueue(q, sendFn);

    // c1은 이미 보냈으니 sent에, c2(실패)·c3(아직 시도 안 함)는 순서 그대로 remaining에 — c3를
    // 먼저 보내면 순서가 깨지고, c2를 버리면 그 메시지가 유실된다.
    expect(sendFn).toHaveBeenCalledTimes(2); // c3는 호출조차 되지 않는다(순서를 지키려고 멈춤).
    expect(result.sent.map((m) => m.client_message_id)).toEqual(['c1']);
    expect(result.remaining).toEqual([queued('c2', '둘'), queued('c3', '셋')]);
  });

  it('sendFn이 던지면 그 항목부터 remaining에 남기되 이미 보낸 행은 sent로 돌려준다', async () => {
    // 후속 리뷰 patch(R6) — sendMessage는 { error } 반환뿐 아니라 예외를 던질 수도 있다(호출부인
    // ChatRoomMessages가 이미 그 전제로 try/catch를 쓴다). 잡지 않으면 이 함수가 통째로 reject해
    // 이미 DB에 저장된 앞쪽 행(c1)이 호출부에 전달되지 않고 pending 버블로 남는다.
    const q = [queued('c1', '하나'), queued('c2', '둘'), queued('c3', '셋')];
    const sendFn = vi.fn(async (msg: QueuedMessage): Promise<SendMessageResult> => {
      if (msg.clientMessageId === 'c2') throw new Error('network down');
      return { message: row({ id: `m-${msg.clientMessageId}`, client_message_id: msg.clientMessageId, body: msg.body }) };
    });

    const result = await flushMessageQueue(q, sendFn);

    expect(sendFn).toHaveBeenCalledTimes(2); // c3는 호출되지 않는다(순서 보존).
    expect(result.sent.map((m) => m.client_message_id)).toEqual(['c1']); // 성공분은 유실되지 않는다.
    expect(result.remaining).toEqual([queued('c2', '둘'), queued('c3', '셋')]);
  });

  it('빈 큐는 아무것도 호출하지 않고 빈 결과를 돌려준다', async () => {
    const sendFn = vi.fn();
    const result = await flushMessageQueue([], sendFn);
    expect(sendFn).not.toHaveBeenCalled();
    expect(result).toEqual({ remaining: [], sent: [] });
  });
});
