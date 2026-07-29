// 오프라인 큐 "다시 보내기" 배선 계약 검사 (대장 #206 최소 수정, Story 12.6 코드리뷰 patch,
// CLAUDE.md B9 — "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가 (실측한 사각지대):
//   재시도 버튼의 onClick은 렌더 시점의 지역 함수가 아니라 `flushQueueRef.current`(재연결
//   effect 안에서 매 회차 새로 배선되는 ref)를 호출한다 — 이 간접 참조가 이 버튼이 존재하는
//   유일한 이유다. 만약 누군가 `flushQueueRef.current = () => void flushQueue();` 대입 줄을
//   지우거나 옮기면, 버튼은 여전히 렌더되고 클릭도 되지만 조용히 ref의 **초기값**(no-op)을
//   호출해 아무 일도 일어나지 않는다 — 화면엔 에러도, 콘솔 로그도 없다. `#206`이 조용히
//   재발하는데 이 스토리가 방금 넣은 vitest(282건)·tsc·lint 중 어느 것도 이 축을 보지 않는다
//   (tsc는 ref 타입만 보고, 다른 검사들은 이 버튼을 몰랐다).
//
// 왜 소스 스캔인가: 이 컴포넌트는 async effect·실시간 구독을 가진 클라이언트 컴포넌트라
//   이 리포는 jsdom 없이 렌더해 상호작용을 시험하지 않는다(vitest.config.ts 도입부 주석 —
//   "jsdom·React Testing Library는 여전히 안 붙인다"). `roomTopicContract.test.ts`·
//   `unreadWiringContract.test.ts`와 동일하게 "소스에 박힌 계약을 정적으로 고정"하는 방식을
//   따른다.
//
// 이 검사가 **안 보는 것**: 버튼을 실제로 클릭했을 때 flushQueue가 정말 재전송을 수행하는지
//   (런타임 동작) — 그건 Story 12.6의 수동 2-브라우저 검증(Playwright route 가로채기로 부분
//   실패를 유도한 뒤 재시도 버튼 클릭 → DB 1행만 확인) 몫이다. 여기서는 "onClick이 ref를 참조
//   하고, 그 ref가 재연결 effect 안에서 실제로 채워진다"는 배선 축만 정적으로 고정한다.
//   또 하나(후속 코드리뷰, 뮤테이션 검증): 두 번째 검사는 `flushQueueRef.current = ...` 대입
//   줄의 텍스트와 "어디 있는지(위치)"만 고정한다 — 그 줄이 실제로 **실행되는지(도달 가능성)**는
//   보지 않는다. 그 대입을 `if (roomId === "__never__") flushQueueRef.current = () => void
//   flushQueue();`처럼 항상 거짓인 조건으로 감싸도 이 파일의 검사는 전부 그대로 통과한다(전체
//   스위트 288건 통과 실측) — 정적 소스 스캔이라 조건문 안 조건식의 참/거짓까지는 못 따진다.
//   세 번째(후속 코드리뷰, 뮤테이션 검증): **실행 순서**도 못 본다. 방 전환 리셋
//   (`flushQueueRef.current = () => {}`)과 실제 배선(`= () => void flushQueue()`)은 같은
//   effect 안의 서로 다른 자리에 있고, 리셋이 먼저 돌아야만 배선이 살아남는다. 리셋이 들어있는
//   async IIFE 맨 앞에 `await Promise.resolve();` 한 줄을 끼우면 리셋이 다음 마이크로태스크로
//   밀려 배선을 덮어써 버튼이 영구 no-op이 되는데, 이 파일의 위치 검사(대입이 flushQueue 정의와
//   gapFillFromCursor 정의 사이에 있다)는 텍스트 위치만 보므로 그대로 통과한다(스위트 288건
//   통과 실측). 이 축은 대장 #230으로 등재했다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const COMPONENT = new URL('../ChatRoomMessages.tsx', import.meta.url);

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

/** 주석(줄·블록)을 지운다 — 계약은 실행되는 코드에만 있다(unreadWiringContract.test.ts와 동일 유틸). */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
}

describe('오프라인 큐 재시도 버튼 배선 계약 (#206)', () => {
  it('"다시 보내기" 버튼의 onClick이 flushQueueRef.current를 참조한다', () => {
    const code = stripComments(read(COMPONENT));

    // lastIndexOf — 코드리뷰 patch(항목3b)로 미전송 안내 문구 자체에도 "다시 보내기"라는 같은
    // 문자열이 버튼을 가리키며 등장한다(안내가 버튼보다 소스상 앞쪽에 있다). indexOf였다면 그
    // 안내 문구 자리를 "라벨"로 잘못 집어 아래 onClick 검사가 엉뚱한 위치를 본다 — 버튼은 항상
    // JSX 뒤쪽(return문)에 있으므로 마지막 등장을 찾는다.
    const labelAt = code.lastIndexOf('다시 보내기');
    expect(labelAt, '"다시 보내기" 버튼 라벨을 찾지 못했습니다').toBeGreaterThan(-1);

    // 라벨 앞쪽(같은 <Button> 엘리먼트 시작부)에서 onClick을 찾는다 — 뒤가 아니라 앞을 본다
    // (JSX에서 onClick prop은 children보다 먼저 온다). 창의 시작을 "라벨에서 400자 앞"이라는
    // 매직넘버가 아니라 **엘리먼트 자체**(`<Button` 여는 태그)로 잡는다(후속 리뷰 patch) —
    // 글자수로 자르면 버튼에 prop이 몇 줄만 더 붙어도(예: 대장 #220이 예고한 loading·loadingText
    // 추가) onClick이 창 밖으로 밀려 **동작은 멀쩡한데 검사만 빨개진다**. 거짓 RED는 검사를
    // 약화·삭제하게 만드는 가장 흔한 경로라, 경계를 구조로 고정한다.
    const buttonStart = code.lastIndexOf('<Button', labelAt);
    expect(buttonStart, '"다시 보내기" 라벨을 감싸는 <Button 여는 태그를 찾지 못했습니다').toBeGreaterThan(
      -1,
    );
    const before = code.slice(buttonStart, labelAt);
    expect(before, '버튼의 onClick이 flushQueueRef.current를 참조해야 합니다').toMatch(
      /onClick=\{[^}]*flushQueueRef\.current\(\)[^}]*\}/,
    );
    // 끊긴 동안엔 no-op이어야 한다(코드리뷰 patch, 항목1) — disconnectedRef 가드가 같이 있어야
    // "안내가 뜬 뒤 클릭 전에 다시 끊기는" 경합에서 헛클릭이 되지 않는다. `!`(부정)까지 정규식에
    // 박아야 한다 — 뮤테이션 검증: `if (!disconnectedRef.current)`를 `if (disconnectedRef.current)`로
    // 뒤집으면(끊긴 상태에서만 눌리는, 유일하게 렌더되는 상태에서 죽는 버튼) `/disconnectedRef\.current/`
    // 만으로는 여전히 3/3 통과였다 — 극성을 안 보고 있었다는 뜻이라 온 표현을 통째로 고정한다.
    expect(before, '재시도 클릭은 !disconnectedRef.current로 끊긴 상태를 가드해야 합니다').toMatch(
      /if\s*\(\s*!\s*disconnectedRef\.current\s*\)\s*flushQueueRef\.current\(\)\s*;?\s*\}/,
    );
    // 잠긴 상태가 **눈에도** 보여야 한다(후속 리뷰 patch) — onClick 가드만 있으면 버튼은 멀쩡해
    // 보이는데 눌러도 아무 일이 없다(피드백 없는 조용한 실패). 뮤테이션 실증: 이 prop만 지워도
    // 스위트 288건이 전부 통과했다 — 직전 패스가 바로 그 조용한 실패를 없애려고 넣은 줄인데
    // 어떤 검사도 보고 있지 않았다.
    expect(before, '재시도 버튼은 disabled={isDisconnected}로 잠긴 상태를 드러내야 합니다').toMatch(
      /disabled=\{isDisconnected\}/,
    );
  });

  it('미전송 안내의 "어떻게 다시 보내나" 문장이 연결 상태에 따라 갈라진다', () => {
    const code = stripComments(read(COMPONENT));

    // 버튼은 disabled={isDisconnected}로 잠기는데 안내 문구가 "누르면 지금 다시 시도한다"로
    // 고정돼 있으면, 스펙이 지정한 #206 재현 절차(재연결 → 부분 실패 → 재차단)가 정확히 그
    // 모순 상태를 만든다 — 사용자는 누를 수 없는 버튼을 누르라는 안내를 읽는다.
    // (a) state에 박히는 문구에는 버튼 안내가 들어가면 안 된다(= 앞문장은 사실만).
    expect(
      code,
      'setQueueStuckNotice에 넣는 문구에는 버튼 안내를 박지 않는다(연결 상태에 따라 갈라져야 함)',
    ).not.toMatch(/setQueueStuckNotice\(\s*`[^`]*다시 보내기/);
    // (b) render에서 isDisconnected로 갈라 끊긴 동안엔 다른 문장을 보여준다.
    expect(code, '끊긴 동안의 안내 문장이 isDisconnected 분기로 갈라져 있어야 합니다').toMatch(
      /isDisconnected[\s\S]{0,80}\?[\s\S]{0,120}연결이 끊겨 지금은 다시 보낼 수 없습니다/,
    );
  });

  it('flushQueueRef.current 대입이 재연결 effect 안(flushQueue 정의 직후)에 있다', () => {
    const code = stripComments(read(COMPONENT));

    const flushQueueDefAt = code.indexOf('async function flushQueue()');
    const gapFillDefAt = code.indexOf('async function gapFillFromCursor()');
    expect(flushQueueDefAt, 'flushQueue 함수 정의를 찾지 못했습니다').toBeGreaterThan(-1);
    expect(gapFillDefAt, 'gapFillFromCursor 함수 정의를 찾지 못했습니다').toBeGreaterThan(-1);

    // flushQueue 정의가 끝난 뒤 ~ gapFillFromCursor 정의가 시작되기 전 사이에 ref 대입이 있어야
    // 한다 — 렌더(버튼 onClick)가 "이번 회차의" flushQueue를 부를 수 있게 하는 유일한 통로다.
    const between = code.slice(flushQueueDefAt, gapFillDefAt);
    expect(
      between,
      'flushQueueRef.current = ... 대입이 flushQueue 정의와 gapFillFromCursor 정의 사이에 있어야 합니다',
    ).toMatch(/flushQueueRef\.current\s*=\s*\(\)\s*=>\s*void\s+flushQueue\(\)/);
  });

  it('roomId가 바뀔 때(방 전환) flushQueueRef도 다른 형제 ref들과 함께 초기화된다', () => {
    const code = stripComments(read(COMPONENT));

    // 12.4가 이미 이 자리에서 초기화하는 형제 ref(onlineInFlightKeyRef)를 기준점으로 삼아,
    // 그 근처에 flushQueueRef 리셋도 있는지 확인한다(코드리뷰 patch, 항목3 — 방어적 일관성).
    const anchorAt = code.indexOf('onlineInFlightKeyRef.current = null;');
    expect(anchorAt, '방 전환 리셋 블록의 기준 줄(onlineInFlightKeyRef)을 찾지 못했습니다').toBeGreaterThan(
      -1,
    );
    const nearby = code.slice(anchorAt, anchorAt + 200);
    expect(nearby, 'flushQueueRef.current도 이 블록에서 초기화돼야 합니다').toMatch(
      /flushQueueRef\.current\s*=\s*\(\)\s*=>\s*\{\s*\}/,
    );
  });
});
