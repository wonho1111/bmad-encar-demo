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
import { markChatRoomRead } from '../chat';

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
