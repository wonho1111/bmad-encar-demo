// AdminSidebar 렌더 계약 검사 (spec-15-2 코드리뷰 patch, CLAUDE.md B9 "규칙은 어길 수 없는 자리에 박는다").
//
// 왜 필요한가 (추측이 아니라 실측): 이 컴포넌트를 덮는 단언은 전부 `web/e2e/*.spec.ts`에 있는데,
//   E2E는 **CI에서 안 돈다**(project-context.md §12 — `.github/workflows/tests.yml`의 web 잡은
//   lint + vitest뿐, E2E는 로컬 `npm run test:e2e` 전용이 의도된 결정이다). 반면 이 컴포넌트의
//   원본인 `SiteNav.tsx`는 같은 축(링크 구성·760px 브레이크포인트·44px 히트영역)을 CI에서 도는
//   `SiteNav.test.ts`로 이미 고정해 두고 있다 — 이식하면서 그 가드는 같이 안 왔다.
//   게다가 5개 라벨 중 `매물 관리`·`거래내역`은 E2E를 포함해 **어떤 검사도 이름을 부르지 않는다**
//   (실측: `grep -rn "매물 관리\|거래내역" web/e2e/` → 0건). 지금은 지우거나 href를 바꿔도
//   tsc·lint·vitest·build가 전부 green이다.
//
// 왜 이 기법인가: `SiteNav.test.ts`와 동일하다 — 'use client' + 훅을 쓰는 컴포넌트를 직접 호출하면
//   React가 훅 디스패처를 못 찾아 throw하므로, react-dom의 renderToStaticMarkup으로 **초기 렌더
//   마크업**만 고정한다. useEffect(바깥클릭 닫기·matchMedia 자동닫힘)와 클릭 상호작용은 이 파일
//   범위 밖이고 E2E 몫이다.
//   `usePathname()`은 Next 라우터 컨텍스트 밖에서 null을 돌려주고(직접 확인함), `isActiveHref`가
//   그 경우 false를 반환하도록 이미 방어돼 있어 렌더가 throw 없이 통과한다. 그래서 이 파일은
//   "어떤 항목이 active인가"는 보지 않는다 — 그건 경로가 있어야 판정되므로 E2E(D1) 몫이다.
import { createElement } from 'react';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import AdminSidebar from './AdminSidebar';

// 5개 내비 목적지(spec-15-2 Always) — 라벨과 href를 쌍으로 고정한다. 라벨만 고정하면 href가
// 조용히 바뀌고, href만 고정하면 라벨이 조용히 바뀐다.
const EXPECTED_LINKS: [label: string, href: string][] = [
  ['대시보드', '/admin'],
  ['회원관리', '/admin/members'],
  ['매물 관리', '/admin/listings'],
  ['거래내역', '/admin/transactions'],
  ['채팅관리', '/admin/chats'],
];

// 렌더된 <a>를 [라벨, href] 튜플로 뽑는다(코드리뷰 patch). 원래는 `toContain(href)`와
// `toContain(label)`을 **따로** 걸었는데, 그러면 위 주석이 말하는 "쌍으로 고정"이 실제로는 안 된다 —
// 두 항목의 href를 서로 바꿔치면(거래내역→/admin/chats, 채팅관리→/admin/transactions) 5개 라벨도
// 5개 href도 전부 그대로 존재해서 파일 전체가 green이었다(실측: 스왑 후 9/9 통과). 메뉴 이름과
// 도착 화면이 어긋나는 것은 이 파일이 존재하는 이유 그 자체인데 그걸 못 봤다.
function renderedNavLinks(html: string): [label: string, href: string][] {
  return [...html.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)].map((m) => {
    const href = /href="([^"]*)"/.exec(m[1])?.[1] ?? '';
    return [m[2], href];
  });
}

describe('AdminSidebar — 초기 렌더 계약', () => {
  const html = renderToStaticMarkup(createElement(AdminSidebar));

  it('내비 링크가 라벨·href·순서까지 정확히 일치한다(쌍 고정 + 추가·삭제 둘 다)', () => {
    // 초기 렌더에는 데스크톱 <nav>만 있다(모바일 패널은 menuOpen이 useState(false)라 조건부 렌더
    // 밖). 그래서 <a> 개수가 곧 목적지 개수다.
    //
    // `<a>` 전체를 세는 이유(코드리뷰 patch): 예전엔 `/href="\/admin[^"]*"/`로 셌는데 그러면
    // /admin으로 시작하지 않는 링크(예: '홈으로' → '/')를 **추가해도** 개수가 5로 유지돼
    // "추가·삭제 둘 다 잡는다"는 이름과 달리 추가를 못 잡았다.
    expect(renderedNavLinks(html)).toEqual(EXPECTED_LINKS);
  });

  it('햄버거 트리거가 dialog를 여는 것으로 표시되고 닫힌 상태로 시작한다', () => {
    expect(html).toContain('aria-haspopup="dialog"');
    expect(html).toContain('aria-expanded="false"');
    // 모바일 패널은 초기 렌더에 없다 — 열림 상태의 마크업이 새어나오면 여기서 잡힌다.
    expect(html).not.toContain('aria-modal="true"');
  });

  it('데스크톱 사이드바에 접근 가능한 이름이 붙어 있다', () => {
    expect(html).toContain('aria-label="관리자 메뉴"');
  });
});

// 주석을 걷어낸 코드만 남긴다(코드리뷰 patch). 아래 측정값 단언들이 원래는 파일 원문을 그대로
// 봤는데, 이 컴포넌트의 주석이 자기가 쓰는 값을 설명하느라 `240px = w-60`·`히트영역 44×44px
// (h-11 w-11)`라고 **문자 그대로** 적어 둬서, 실제 className에서 그 클래스를 지워도 주석이 단언을
// 대신 충족했다(실측: w-60→w-96, h-11 w-11→h-8 w-8로 바꿔도 9/9 통과). 이 파일이 지키려는 두 숫자
// (240px 사이드바 폭·44px 접근성 히트영역)가 사실상 무방비였다는 뜻이다.
// 줄 주석을 **먼저** 지운다: 이 파일에는 `// ... /admin/* 경로에서 ...`처럼 줄 주석 안에 `/*`가
// 들어간 줄이 있어서, 블록 주석을 먼저 지우면 거기서부터 다음 `*/`(30줄 아래 JSX 주석)까지가
// 통째로 사라진다 — 실제로 그렇게 짰다가 matchMedia 단언이 엉뚱하게 빨개졌다.
function codeWithoutComments(fileUrl: URL): string {
  return readFileSync(fileURLToPath(fileUrl), 'utf-8')
    .replace(/^[ \t]*\/\/.*$/gm, '')
    .replace(/\/\*[\s\S]*?\*\//g, '');
}

describe('AdminSidebar — 측정값 고정(760px 브레이크포인트·44px 히트영역)', () => {
  const sidebarCode = codeWithoutComments(new URL('./AdminSidebar.tsx', import.meta.url));
  // 코드리뷰 patch — 레이아웃 파일도 함께 본다. 이 사이드바를 **콘텐츠 옆에** 놓는 것은
  // `(admin)/layout.tsx`의 `min-[760px]:flex`이고, 그건 이 컴포넌트 밖에 있다. 원래 이 스캔은
  // AdminSidebar.tsx만 읽어서, 레이아웃의 flex 래퍼를 통째로 지우면 사이드바가 콘텐츠 **위에**
  // 전폭으로 쌓이는데도(= 이 스토리의 본체가 사라지는데도) vitest 340건·E2E 48건이 전부 green이었다
  // (실측). 전폭으로 쌓이면 가로스크롤도 안 생기므로 viewport-audit도 못 본다.
  const layoutCode = codeWithoutComments(new URL('../../app/(admin)/layout.tsx', import.meta.url));

  it('소스 스캔 — 760px과 h-11 w-11은 SiteNav에서 이식한 실측치라 값 자체를 고정한다', () => {
    // `SiteNav.test.ts`와 같은 이유·같은 방식이다: 이 값들이 바뀌어도 lint·tsc·vitest·build는
    // 전부 green이라, 값 자체를 여기서 고정하지 않으면 어디서도 안 잡힌다.
    // 특히 CSS 붕괴점(`min-[760px]:`)과 JS 자동닫힘 기준(`matchMedia`)이 **같은 수**여야 한다 —
    // 한쪽만 바뀌면 그 사이 폭에서 햄버거는 숨었는데 패널은 살아 있는 구간이 생긴다.
    expect(sidebarCode).toContain("matchMedia('(min-width: 760px)')");

    // 두 파일을 합쳐서 센다 — 브레이크포인트는 컴포넌트와 레이아웃에 걸쳐 있고, 한쪽만 옮기면
    // 그 사이 폭에서 셸이 어긋난다(햄버거는 숨었는데 사이드바는 아직 안 붙는 식).
    const shellCode = `${sidebarCode}\n${layoutCode}`;
    const anyBreakpointOccurrences = (shellCode.match(/min-\[\d+px\]:/g) ?? []).length;
    const breakpoint760Occurrences = (shellCode.match(/min-\[760px\]:/g) ?? []).length;
    expect(anyBreakpointOccurrences).toBeGreaterThanOrEqual(2);
    expect(breakpoint760Occurrences).toBe(anyBreakpointOccurrences);

    expect(sidebarCode).toContain('h-11 w-11');
    // 사이드바 폭 240px = w-60(spec-15-2 Always).
    expect(sidebarCode).toContain('w-60');
  });

  it('레이아웃이 데스크톱에서 사이드바를 콘텐츠 옆에 놓는다(위가 아니라)', () => {
    // 이 스토리의 본체 = "데스크톱 고정 사이드바 + 콘텐츠 나란히". 그 배치를 만드는 것은
    // 레이아웃의 flex 래퍼 하나뿐이라, 여기서 그 자리를 직접 고정한다.
    expect(layoutCode).toMatch(/min-\[760px\]:flex\b/);
    // 콘텐츠 쪽 min-w-0 — 사이드바가 240px을 먹는 640~1099px 구간에서 긴 텍스트가 flex 최소폭에
    // 밀려 가로스크롤을 만드는 것을 막는다(D5). 지우면 그 구간에서만 깨지므로 눈에 잘 안 띈다.
    expect(layoutCode).toMatch(/min-w-0[^"']*flex-1|flex-1[^"']*min-w-0/);
  });
});
