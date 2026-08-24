// 채팅 메시지 버블 줄바꿈 계약 (Story 12.3 코드리뷰 patch, CLAUDE.md B9 + D5 반응형 무결성).
//
// 왜 필요한가 (추측이 아니라 실측):
//   버블은 `max-w-[80%] whitespace-pre-wrap`만 걸고 있었다. `whitespace-pre-wrap`은 **공백에서만**
//   줄을 바꾸므로, 공백 없는 긴 문자열(붙여넣은 URL 등 — 본문 상한은 CHAT.MESSAGE_MAX_LENGTH)은
//   쪼개지지 않고 버블 밖으로 삐져나간다. 코드리뷰 중 시드 방에 200자짜리 URL 한 건을 실제로 넣고
//   390px에서 측정하니 `scrollWidth 672 > clientWidth 390` — 대장 #169가 닫으려던 바로 그 결함이
//   같은 화면에서 재현됐다. `break-words`(overflow-wrap: break-word)를 세 버블에 걸어 해소했다.
//
// 왜 E2E가 아니라 소스 스캔인가:
//   ① 이 조건을 E2E로 만들려면 공유 로컬 DB에 긴 메시지를 넣어야 하는데, `viewport-audit.spec.ts`는
//      3개 뷰포트 프로젝트가 동시에 도는 구조라 한쪽의 삽입이 다른 쪽 읽기에 새어 들어가 무관한
//      케이스까지 red로 만든다(실측으로 확인).
//   ② web의 E2E는 CI에 배선돼 있지 않다(`_bmad-output/project-context.md` §12, `docs/tech-debt.md`
//      #168) — E2E에만 두면 push마다 도는 가드가 되지 못한다. 이 스캔은 `npm test`에 포함된다.
//
// 이 검사가 **안 보는 것**: 실제 렌더 폭(브라우저 레이아웃). 클래스가 붙어 있다는 것과 390px에서
//   실제로 안 넘친다는 것은 다르다 — 후자는 위 실측 1회와 `viewport-audit`의 시드 방 케이스가 맡는다.
//
// spec-15-2(DW-701 + DW-697 ①) 확장: 관리자 채팅방 열람(`admin/chats/[roomId]/page.tsx`)도 같은
//   `max-w-[80%]` 버블 계약을 쓰는데, 그 버블 클래스는 백틱 템플릿 리터럴(`` `...${...}` ``)이라
//   기존 정규식(따옴표 전용)이 못 잡았다 — 잡았다면 폭 3개(기존 3개 + 관리자 1개)가 나와야 하는데
//   실제로는 여전히 3개였다(관리자 파일을 넣기 전 실측). 백틱 분기를 추가하고 관리자 파일을
//   별도로 스캔해 파일별 개수를 각각 단언한다.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const REPO_ROOT = fileURLToPath(new URL('../../../../../../../', import.meta.url));
const USER_COMPONENT = join(REPO_ROOT, 'web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx');
const ADMIN_COMPONENT = join(REPO_ROOT, 'web/src/app/(admin)/admin/chats/[roomId]/page.tsx');

// 버블은 `max-w-[80%]`로 폭이 제한된 요소(내 메시지·상대 메시지·pending·관리자 판매자/그외)다.
// 폭 제한이 있는데 줄바꿈 규칙이 없으면 그 요소는 반드시 넘친다 — 그래서 "max-w-[80%]가 있는 모든
// 클래스 문자열"을 찾아 하나도 빠짐없이 break-words를 갖는지 본다(버블이 하나 더 생겨도 자동으로
// 검사 대상이 된다).
// (줄바꿈을 넘지 않게 따옴표 분기는 `\n`을 제외한다 — 안 그러면 앞쪽 다른 따옴표에서 시작한 매치가
//  여러 줄을 통째로 삼켜 버블 하나를 놓친다. 실제로 그렇게 2개만 잡히는 것을 확인하고 고쳤다.)
// 백틱(템플릿 리터럴) 분기는 `\n`을 제외하지 않는다 — 관리자 버블은 `className={`...${식}`}`처럼
//   여는/닫는 백틱 사이에 실제 줄바꿈이 있는 여러 줄 템플릿이라, `\n`을 제외하면 애초에 안 잡힌다.
//   대신 백틱 자체는 내용에 나타나지 않으므로 `[^`]*`만으로 여는 백틱부터 닫는 백틱까지 안전하게 닫힌다.
const BUBBLE_CLASS =
  /'[^'\n]*max-w-\[80%\][^'\n]*'|"[^"\n]*max-w-\[80%\][^"\n]*"|`[^`]*max-w-\[80%\][^`]*`/g;

function scanBubbleClasses(componentPath: string): string[] {
  return [...readFileSync(componentPath, 'utf8').matchAll(BUBBLE_CLASS)].map((m) => m[0]);
}

describe('채팅 메시지 버블 — 공백 없는 긴 본문이 버블 밖으로 넘치지 않는다', () => {
  const bubbles = scanBubbleClasses(USER_COMPONENT);

  it('폭이 제한된 버블 클래스가 3개(내 메시지·상대 메시지·pending) 잡힌다', () => {
    expect(bubbles).toHaveLength(3);
  });

  it('모든 버블이 break-words를 갖는다', () => {
    for (const cls of bubbles) {
      expect(cls, `이 버블에 break-words가 없습니다: ${cls}`).toMatch(/\bbreak-words\b/);
    }
  });
});

describe('관리자 채팅방 열람 버블(spec-15-2, DW-697 ①) — 같은 줄바꿈 계약', () => {
  const bubbles = scanBubbleClasses(ADMIN_COMPONENT);

  it('폭이 제한된 버블 클래스가 1개(판매자/그외 공용 span, 백틱 템플릿) 잡힌다', () => {
    expect(bubbles).toHaveLength(1);
  });

  it('버블이 break-words를 갖는다', () => {
    for (const cls of bubbles) {
      expect(cls, `이 버블에 break-words가 없습니다: ${cls}`).toMatch(/\bbreak-words\b/);
    }
  });
});
