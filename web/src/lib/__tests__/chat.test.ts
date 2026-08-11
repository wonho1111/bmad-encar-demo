// markChatRoomRead 단위테스트 (Story 12.5, FR57 — B9 "실행되는 검사").
//
// 이 파일이 검사하는 것:
//   markChatRoomRead가 (1) chat_room_reads에 (user_id, room_id) 복합키로 upsert하는지,
//   (2) last_read_at을 ISO 문자열로 실어 보내는지, (3) upsert가 실패해도 throw하지 않고
//   콘솔에만 로그를 남기는지(화면 비차단 — 배지는 부가 정보, I/O 매트릭스 "upsert 실패 시").
//
// **이 검사가 안 보는 것**: 실제 DB의 RLS(참여자 인가)·복합 PK 충돌 처리 자체는 여기서 검증하지
// 않는다 — supabase 체인을 손으로 흉내 낸 mock이라 "무엇을 어떤 인자로 불렀는가"만 본다. 실제
// upsert가 RLS로 거부되는지는 로컬 Supabase 스택으로 손수 검증한다(Verification 절 참조).
import { describe, expect, it, vi } from 'vitest';
import type { SupabaseClient } from '@supabase/supabase-js';
import { chatListingSummary, markChatRoomRead } from '../chat';

type UpsertResult = { data: unknown; error: unknown };

function makeSupabaseMock(result: UpsertResult) {
  const upsert = vi.fn().mockResolvedValue(result);
  const from = vi.fn(() => ({ upsert }));
  return { client: { from } as unknown as SupabaseClient, from, upsert };
}

describe('markChatRoomRead', () => {
  it('chat_room_reads에 (user_id, room_id) 복합키로 last_read_at을 upsert한다', async () => {
    const { client, from, upsert } = makeSupabaseMock({ data: null, error: null });

    await markChatRoomRead(client, 'room-1', 'user-1');

    expect(from).toHaveBeenCalledWith('chat_room_reads');
    expect(upsert).toHaveBeenCalledTimes(1);
    const [payload, options] = upsert.mock.calls[0];
    expect(payload.user_id).toBe('user-1');
    expect(payload.room_id).toBe('room-1');
    expect(typeof payload.last_read_at).toBe('string');
    expect(() => new Date(payload.last_read_at).toISOString()).not.toThrow();
    expect(options).toEqual({ onConflict: 'user_id,room_id' });
  });

  it('upsert가 실패해도 throw하지 않고 콘솔에만 로그를 남긴다(화면 비차단)', async () => {
    const { client } = makeSupabaseMock({ data: null, error: { message: '거부됨' } });
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(markChatRoomRead(client, 'room-1', 'user-1')).resolves.toBeUndefined();
    expect(consoleSpy).toHaveBeenCalledWith('[chat] 읽음 상태 갱신 실패:', { message: '거부됨' });

    consoleSpy.mockRestore();
  });
});

// chatListingSummary 단위테스트 (Story 17.4 코드리뷰 patch — DW-804(a), P8이 아래 null 케이스를
// 한 테스트로 합침).
//
// 이 파일이 검사하는 것: chat/page.tsx·chat/[roomId]/page.tsx가 공유하는 매물 요약 문구가
//   listings 임베드 유무에 따라 정확히 갈리는지. 임베드가 null이 되는 **두 원인**(sold·정지된
//   판매자, 아래 참조)이 같은 폴백 문구로 안전하게 흡수되는지 확인한다.
//
// **이 검사가 안 보는 것**: 이 함수는 순수 함수라 "PostgREST가 실제로 null을 돌려주는가"는
//   검사하지 않는다 — 그건 RLS 문제이고, `api/tests/integration/test_suspended_seller_hidden_real_db.py`
//   (listing_images 축)와 이 스토리의 로컬 실DB 프로브가 실측했다(스펙 Design Notes 참조). 이 파일은
//   "null이 오면 화면이 무엇을 렌더하는가"만 본다 — sold와 suspended 두 원인이 프론트엔드 코드
//   에서는 **구분되지 않고 같은 값(null)으로 도착**하므로, 이 함수 입장에서 두 트리거는 입력이
//   완전히 똑같다(둘 다 `null`). ✎ 2026-08-12 P8: 원래 이 두 트리거를 각각 별도 `it()`으로
//   나눠 뒀는데, 입력·단언이 byte-identical해서 "다른 코드 경로를 검사한다"는 착시만 주고 실제로
//   새로 잡는 회귀는 없었다 — 아래는 그 둘을 하나로 합치되, 주석으로 "왜 하나인지"(두 트리거가
//   이 함수 입장에서 구분 불가능한 같은 입력이라는 사실)를 남겨 다음 사람이 "sold만 되고
//   suspended는 검사가 없다"로 오해하지 않게 한다.
describe('chatListingSummary', () => {
  it('listings 임베드가 있으면 제조사·모델·연식·가격을 조합한 문구를 만든다', () => {
    expect(
      chatListingSummary({ manufacturer: '현대', model: '싼타페', year: 2020, price: 26700000 }),
    ).toBe('[현대] 싼타페 · 2020년 · 26,700,000원');
  });

  it('임베드가 null이면(sold 트리거·정지 판매자 트리거 둘 다) 동일한 폴백 문구를 낸다', () => {
    // 두 트리거(① status='sold', listings_select_on_sale*(0002·0011)·FR11 / ② 판매자 정지,
    // Story 17.4 DW-804(a), listings_select_on_sale*(0035)가 판매자 활성 여부도 거름)는 둘 다
    // 임베드를 null로 만든다 — 이 함수 입장에서 입력이 완전히 같은 값(null)이라 별도 테스트로
    // 나누지 않는다(코드리뷰 patch, P8 — 나눴던 두 테스트가 byte-identical해 테스트 수만 늘고
    // 새로 잡는 회귀가 없었다). 위 헤더 설명 참조.
    expect(chatListingSummary(null)).toBe('판매 완료되었거나 조회할 수 없는 매물');
  });

  it('가격이 0이어도(falsy 값) 임베드가 있는 것으로 취급해 정상 조합한다', () => {
    // `l ? ... : ...`는 l 자체(객체 존재 여부)로 분기한다 — price:0 같은 falsy 필드값 때문에
    // 폴백으로 잘못 빠지지 않는지 고정(회귀 가드).
    expect(chatListingSummary({ manufacturer: '테슬라', model: 'Model 3', year: 2023, price: 0 })).toBe(
      '[테슬라] Model 3 · 2023년 · 0원',
    );
  });
});
