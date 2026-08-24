// 채팅 행/칩 호버 대비 회귀 가드 (spec-15-2, DW-699, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가 (추측이 아니라 실측):
//   `chat/page.tsx`의 방 목록 행, `chat/[roomId]/page.tsx`의 "매물 상세" 칩, `admin/chats/page.tsx`의
//   "매물 상세" 버튼은 원래 `hover:bg-surface-raised`/`hover:bg-surface-base`로 라이트 모드 호버를
//   표시했다. 그런데 body 배경이 이미 `--surface-base`(#FAFAF8)이고 카드류는 `--surface-raised`
//   (#FFFFFF)라, 두 색의 대비는 1.045:1(실측 계산: WCAG relative luminance 공식) — 육안상 거의
//   변화가 없다. spec-15-2가 세 곳 모두 `hover:border-brand-petrol`(다른 축 신호, 새 토큰 추가 없음)로
//   바꿨다.
//
// 왜 소스 스캔인가: `messageBubbleWrap.test.ts`와 동일 이유(project-context.md §12 — web은 E2E
//   우선, 이 async 서버 컴포넌트들은 단위테스트로 렌더하지 않는다) — 그 파일과 같은 "소스에 박힌
//   계약을 정적으로 고정" 기법을 그대로 쓴다.
//
// 이 검사가 **안 보는 것**: 실제 브라우저에서 호버 시 대비가 몇 대 몇으로 보이는지(그건 위 실측
//   계산과 코드리뷰 1회 관찰이 맡았다). 여기서는 "그 대비를 만들어내는 클래스 조합이 소스에
//   그대로 남아 있는지"만 고정한다 — 즉 누군가 이 hover 클래스를 다시 `hover:bg-surface-*`로
//   되돌리면(대비가 다시 죽으면) 그 사실만 잡는다.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const CHAT_LIST_PAGE = new URL('../page.tsx', import.meta.url);
const CHAT_ROOM_PAGE = new URL('../[roomId]/page.tsx', import.meta.url);
const ADMIN_CHAT_LIST_PAGE = new URL('../../../(admin)/admin/chats/page.tsx', import.meta.url);
// 코드리뷰 patch — `/search`의 페이지네이션 칩도 같은 계약 아래로 들여온다. 이 파일이 처음 만들어질
// 때는 채팅 3개 화면만 봤는데, **같은 커밋의 DW-696 zinc 치환이 이 칩에 `hover:bg-surface-raised`를
// 새로 심었다** — DW-699가 죽었다고 판정한 바로 그 조합이 가드 밖에서 되살아난 것이다. 규칙을 만든
// 커밋이 그 규칙을 어겼는데 가드가 못 봤다는 뜻이므로, 가드의 대상 목록을 화면이 아니라 "이 클래스
// 조합을 쓰는 곳"으로 넓힌다.
const SEARCH_PAGE = new URL('../../search/page.tsx', import.meta.url);

// DW-699가 손댄 링크/버튼은 전부 `border border-border-hairline`이 있는 행·칩이다(카드 그 자체가
// 아니라 카드 안의 개별 인터랙티브 요소) — 그 표식과 `hover:`가 같은 className 문자열 안에 함께
// 있는 것만 골라낸다(순서 무관, lookahead). admin/chats/page.tsx의 "방 열람" 링크(hover:underline)는
// border-border-hairline이 없는 별개 요소라 이 정규식엔 안 걸린다 — 그 링크는 DW-699 대상이 아니다.
//
// 코드리뷰 patch — 작은따옴표 분기를 더한다. 원래는 `"..."`만 봤는데, 클래스가 JSX 속성이 아니라
// `const pagerLinkClass = '...'`처럼 따로 뽑히면(실제로 search/page.tsx가 그렇다) 스캔이 0건이 되고
// 아래 개수 단언만 빨개진다 — "호버가 죽었다"가 아니라 "포맷이 바뀌었다"고 말하는 셈이라, 다음
// 사람이 규칙을 고치는 대신 가드를 느슨하게 만들도록 유도한다.
const HOVER_ROW_CLASS =
  /"(?=[^"\n]*\bborder-border-hairline\b)(?=[^"\n]*\bhover:)[^"\n]*"|'(?=[^'\n]*\bborder-border-hairline\b)(?=[^'\n]*\bhover:)[^'\n]*'/g;

function scanHoverRowClasses(fileUrl: URL): string[] {
  return [...readFileSync(fileUrl, 'utf8').matchAll(HOVER_ROW_CLASS)].map((m) => m[0]);
}

describe.each([
  ['chat/page.tsx (방 목록 행)', CHAT_LIST_PAGE],
  ['chat/[roomId]/page.tsx (매물 상세 칩)', CHAT_ROOM_PAGE],
  ['admin/chats/page.tsx (매물 상세 버튼)', ADMIN_CHAT_LIST_PAGE],
  ['search/page.tsx (페이지네이션 칩)', SEARCH_PAGE],
])('%s — 호버가 hover:border-brand-petrol을 쓴다(DW-699)', (_label, fileUrl) => {
  const classes = scanHoverRowClasses(fileUrl);

  it('테두리+호버 조합 클래스가 정확히 1개 잡힌다', () => {
    expect(classes).toHaveLength(1);
  });

  // 아래 두 검사는 `for...of`라 `classes`가 비면 **한 번도 실행되지 않고 초록**이 된다(코드리뷰
  // 지적). 지금은 위 개수 단언이 그 상태를 막아 주지만, 화면에 두 번째 호버 행이 생겨 누가 개수
  // 단언을 느슨하게 푸는 순간 이 두 검사는 조용히 무의미해진다 — 그래서 각자 자기 전제를 직접 건다.
  it('hover:border-brand-petrol을 포함한다', () => {
    expect(classes.length, '스캔이 0건이면 아래 루프가 통째로 건너뛰어져 이 검사가 무의미해진다').toBeGreaterThan(0);
    for (const cls of classes) {
      expect(cls, `이 클래스에 hover:border-brand-petrol이 없습니다: ${cls}`).toMatch(
        /hover:border-brand-petrol\b/,
      );
    }
  });

  it('죽은 대비(hover:bg-surface-base/hover:bg-surface-raised)로 되돌아가지 않았다', () => {
    expect(classes.length, '스캔이 0건이면 아래 루프가 통째로 건너뛰어져 이 검사가 무의미해진다').toBeGreaterThan(0);
    for (const cls of classes) {
      expect(cls, `이 클래스가 죽은 호버로 되돌아갔습니다: ${cls}`).not.toMatch(
        /hover:bg-surface-(?:base|raised)\b/,
      );
    }
  });
});
