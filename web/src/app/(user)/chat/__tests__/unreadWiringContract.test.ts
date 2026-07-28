// 안읽음·정렬 **배선** 계약 검사 (Story 12.5 후속 코드리뷰 patch, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가 (실측한 사각지대):
//   0025/0024가 만든 DB 재료(chat_rooms.last_message_at·chat_room_reads·chat_unread_count())는
//   실DB 테스트(`api/tests/integration/test_chat_unread_real_db.py`)가 값의 정확성을 고정한다.
//   그런데 **그 재료를 실제로 쓰는 두 자리**는 어떤 검사도 보지 않았다:
//     ① 방 목록의 정렬 키 — `.order('last_message_at', …)`를 `created_at`으로 되돌려도
//        lint·tsc·vitest·pytest·Playwright가 전부 green이다. FR57의 두 인수조건 중 하나가
//        통째로 무검증이었다.
//     ② 방 진입 시 `markChatRoomRead` 호출 — 이 줄을 지우면 읽음 기록이 아예 안 남아 배지가
//        영원히 줄지 않는데, 헬퍼 자체의 단위테스트(`web/src/lib/__tests__/chat.test.ts`)는
//        함수를 직접 호출하므로 "페이지가 그것을 부르는가"는 보지 않는다. 인자 순서
//        (roomId, userId)도 둘 다 string이라 tsc가 못 잡는다.
//
// 왜 소스 스캔인가: 이 두 자리는 async 서버 컴포넌트 안이라 이 리포는 단위테스트로 렌더하지
//   않는다(project-context.md §12 — web은 E2E 우선). 대신 같은 리포가 이미 쓰는 기법을 따른다
//   — `roomTopicContract.test.ts`(토픽 문자열 3벌 대조)·`AppHeader.test.ts`(호출부 variant 스캔)와
//   동일한 "소스에 박힌 계약을 정적으로 고정" 방식이다.
//
// 이 검사가 **안 보는 것**(추측 아니라 구조적 한계):
//   · 정렬이 브라우저에서 실제로 최신순으로 보이는지 — 그건 Story 12.6의 수동 2-브라우저 검증과
//     실DB 테스트(값의 정확성)가 나눠 맡는다. 여기서는 "쿼리가 그 컬럼으로 정렬을 건다"만 본다.
//   · `markChatRoomRead`가 런타임에 실제로 성공하는지 — RLS/GRANT 축은 실DB 테스트 ⑨번이 본다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const LIST_PAGE = new URL('../page.tsx', import.meta.url);
const ROOM_PAGE = new URL('../[roomId]/page.tsx', import.meta.url);

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

/** 주석(줄·블록)을 지운다 — 계약은 실행되는 코드에만 있고, 주석에 적힌 예시가 검사를 흔들면 안 된다. */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
}

describe('안읽음·정렬 배선 계약 (FR57)', () => {
  it('방 목록은 last_message_at 내림차순을 1차 정렬로 건다(방 생성순으로 되돌아가지 않는다)', () => {
    const source = read(LIST_PAGE);

    // 주석·문자열이 아니라 **실제 쿼리 체인**만 본다(후속 코드리뷰 patch). 파일 전체를 스캔하면
    // 주석에 적힌 `.order('created_at')` 예시 한 줄이 인덱스를 밀어 거짓 red/green을 만든다 —
    // 이 리포는 실제로 conventions.md §12.6에 같은 형태의 예시 문자열을 갖고 있다.
    const code = stripComments(source);
    const chainStart = code.indexOf("from('chat_rooms')");
    expect(chainStart).toBeGreaterThan(-1);
    const chain = code.slice(chainStart);

    // 이 페이지가 chat_rooms에 거는 .order(...) 호출을 소스 순서대로 뽑는다.
    // 숫자를 포함한 컬럼명도 잡도록 [a-z0-9_]로 넓힌다(예전 [a-z_]는 조용히 못 잡았다).
    const orderKeys = [...chain.matchAll(/\.order\(\s*'([a-z0-9_]+)'/g)].map((m) => m[1]);

    expect(orderKeys.length).toBeGreaterThan(0);
    expect(orderKeys[0]).toBe('last_message_at');
    // 동시각 안정화용 id 2차정렬은 기존 관례라 함께 고정한다(conventions.md §12.6).
    expect(orderKeys[1]).toBe('id');
    // 내림차순이어야 "최신 문의가 위"다.
    expect(chain).toMatch(/\.order\(\s*'last_message_at',\s*\{\s*ascending:\s*false\s*\}\s*\)/);
  });

  it('방 페이지는 markChatRoomRead를 await로, 당사자 확인 뒤에, (client, room.id, user.id) 순서로 호출한다', () => {
    const code = stripComments(read(ROOM_PAGE));

    expect(code).toContain("from '@/lib/chat'");
    // 인자 순서까지 고정한다 — roomId·userId 둘 다 string이라 뒤바뀌어도 tsc는 통과한다.
    // `await`도 함께 고정한다(후속 코드리뷰 patch, 실측): await를 지워도 lint·tsc·vitest가 전부
    // green이었다. async 서버 컴포넌트에서 떠다니는 promise는 응답이 끝나기 전에 완료된다는
    // 보장이 없고, markChatRoomRead는 실패를 콘솔로만 삼키므로 배지가 조용히 안 줄어든다.
    expect(code).toMatch(/await\s+markChatRoomRead\(\s*supabase\s*,\s*room\.id\s*,\s*user\.id\s*\)/);

    // 호출이 **어디에** 있는지도 고정한다(후속 코드리뷰 patch). 인자만 고정하면 이 호출을
    // 가드 위로 끌어올려도 초록이다.
    //   ① `!room` 가드보다 뒤 — 없는 방·RLS 0건에 읽음 기록을 남기지 않는다.
    //   ② 당사자 직접 확인(buyer_id/seller_id 대조)보다 뒤 — RLS 통과 ≠ 당사자다. 0005의
    //      `chat_rooms_select_admin`이 참여자 정책과 OR로 합쳐져 관리자에겐 남의 방도 보인다
    //      (0025가 chat_unread_count()에서 고친 것과 같은 축).
    const guardAt = code.indexOf('if (!room)');
    const participantAt = code.search(/user\?\.id === room\.buyer_id \|\| user\?\.id === room\.seller_id/);
    const callAt = code.search(/await\s+markChatRoomRead\(/);
    expect(guardAt).toBeGreaterThan(-1);
    expect(participantAt).toBeGreaterThan(-1);
    expect(guardAt).toBeLessThan(callAt);
    expect(participantAt).toBeLessThan(callAt);
  });
});
