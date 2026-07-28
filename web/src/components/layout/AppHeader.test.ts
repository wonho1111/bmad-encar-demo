// AppHeader 분기 검사(Story 11.2 코드리뷰 지적, CLAUDE.md B9 "규칙은 어길 수 없는 자리에
// 박는다") — admin/consumer 두 갈래를 지키는 자동 검사가 지금까지 하나도 없었다. (admin)/layout.tsx
// 에서 variant="admin" 한 줄만 지워지면 관리자 콘솔에 소비자 내비(찜·채팅·프로필▾ 등)가 뜨는데,
// lint·tsc·vitest·build가 전부 green으로 통과한다(리뷰 실측) — spec의 명시 인수조건인데 아무것도
// 못 잡는다는 뜻이다.
//
// 왜 .test.ts(jsdom 없이)인가: 이 리포 표준은 E2E(Playwright) 우선이고 vitest는 "서버 컴포넌트
// 밖 순수 유틸이 생기면 그것만 단위테스트로 보강"하는 예외 조항이다(vitest.config.ts 주석). AppHeader
// 는 서버 컴포넌트지만 훅 없는 동기 함수 컴포넌트라 ListingCard.test.ts와 같은 기법 — 함수를
// **직접 호출**해 React 엘리먼트 트리(순수 객체)를 받고 노드를 순회 — 이 그대로 적용된다. SiteNav·
// Logo·LogoutButton은 JSX(<SiteNav .../>)로만 참조되고 실제로 호출되지 않으므로('use client'·훅이
// 있어도) import한 함수 참조와 identity 비교가 문제없이 동작한다(실측 확인, 아래 vitest 실행 결과 참고).
//
// 이 검사가 지키는 불변식:
//   (1) consumer 분기는 SiteNav(email·currentPath 전달)와 Logo를 반드시 그리고, admin 분기는
//       둘 다 그리지 않는다 — variant 하나가 관리자 콘솔에 소비자 내비가 새는지를 결정한다.
//   (1-1, 3차 코드리뷰 지적 P2) admin 분기가 <LogoutButton />도 반드시 그리는지 — 관리자는
//       (admin)/layout.tsx의 requireAdmin()을 통과해야만 이 헤더에 닿으므로 로그인 링크로 대체될
//       일이 없고, admin 콘솔에서 이 버튼이 로그아웃의 유일한 수단이다. 리뷰에서 실측: 이 버튼을
//       admin 분기에서 지워도 lint·tsc·vitest가 전부 green이었다 — 관리자가 못 나가는 회귀를
//       아무것도 못 잡는다는 뜻.
//   (2) web/src/app/(admin)/ 아래 모든 AppHeader 호출부는 variant="admin"을 함께 전달한다
//       (소스 스캔 — viewCountCallSite.test.ts와 같은 기법).
//   (3, 3차 코드리뷰 지적 P3) 거꾸로 (admin)/ 바깥의 모든 호출부는 variant="admin"을 전달하지
//       **않는다** — (2)만 있으면 컨슈머 페이지에 variant="admin"이 잘못 추가돼도 아무것도 못
//       잡는다(리뷰 실측: search/page.tsx의 호출부에 그 prop 한 줄만 추가해도 기존 검사는 전부
//       green이었다 — 그 한 줄이 이 스토리의 소비자 내비 전체를 지운다).
//
// 3차 코드리뷰 지적 P1 — 소스 스캔 정규식 자체에 결함이 2가지 있었다(지금은 고쳐짐):
//   · 예전 `/<AppHeader\b[^>]*\/?>/g`는 `[^>]*`가 첫 `>`에서 멈춘다 — 호출부 prop에 화살표
//     함수나 비교 연산자처럼 `>`가 들어가면(예: `onClick={() => {}}`) 태그가 실제로 끝나기 전에
//     잘려 그 뒤에 오는 `variant="admin"`을 통째로 놓치고, 정상 코드인데도 실패한다.
//     지금은 attribute를 값 문법(따옴표 문자열 또는 한 겹까지 중첩 허용하는 `{...}` 표현식)으로
//     파싱해 진짜 태그 종료(`/>` 또는 `>`)에서만 멈춘다(아래 APP_HEADER_TAG).
//   · 예전 단언은 문자 그대로 `variant="admin"`만 인정해 동치 표현 `variant={'admin'}` /
//     `variant={"admin"}`은 그대로 통과시켰다(아무도 못 잡음). 지금은 세 표기를 모두 인정하는
//     정규식(VARIANT_ADMIN)으로 판정한다.
//
// 이 검사가 안 보는 것(추측 아니라 구조적 한계): 실제 브라우저에서 admin 콘솔에 소비자 내비가
// 진짜로 안 보이는지(레이아웃·스타일·CSS 숨김 여부)는 E2E 몫이다. variant prop 경로가 아니라 다른
// 경로(예: SiteNav 내부 로직 오작동으로 관리자에게 소비자 링크가 새는 경우)는 이 파일 범위 밖 —
// SiteNav 자체는 admin 분기에서 아예 호출되지 않으므로 그런 경로는 애초에 없다. ATTR_VALUE는
// `{...}` 중첩을 한 겹까지만 따라가므로, prop 값 안에 객체 리터럴이 두 겹 이상 중첩되면 태그
// 매치가 실패할 수 있다 — 이 리포의 실제 호출부엔 그런 패턴이 없어 범위 밖으로 둔다.
//
// ✎ Story 12.5(FR57) 추가 — AppHeader는 consumer 분기·로그인 시 `chat_unread_count()` RPC를
// 호출하려고 비동기 컴포넌트로 바뀌었다. 그래서 이 파일의 직접 호출 기법도 `await AppHeader(...)`
// 로 바뀐다(함수 자체 호출은 그대로 — 훅이 없으므로 여전히 React 렌더러 없이 안전하다). 실제
// `@/lib/supabase/server`(next/headers `cookies()` 사용 — 요청 스코프 밖인 vitest에서는 호출
// 자체가 실패한다)는 `vi.mock`으로 가짜 클라이언트로 치환해 RPC 호출 여부·반환값만 확인한다.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Link from 'next/link';
import SiteNav from './SiteNav';
import Logo from '@/components/ui/Logo';
import LogoutButton from '@/components/auth/LogoutButton';

// hoisting 때문에 vi.mock 팩토리 안에서 바깥 변수를 쓸 수 없어(photo-sync.test.ts와 동일 관례),
// 기록·조작은 vi.hoisted로 만든 객체에 둔다.
const h = vi.hoisted(() => ({
  rpcCalls: [] as string[],
  rpcResult: { data: 0 as unknown, error: null as unknown },
}));

vi.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({
    rpc: async (fn: string) => {
      h.rpcCalls.push(fn);
      return h.rpcResult;
    },
  }),
}));

// vi.mock 호출은 Vitest가 파일 최상단으로 끌어올리므로(hoisting), 아래 정적 import보다 소스상
// 뒤에 있어도 AppHeader는 항상 위 가짜 createClient를 물게 된다(photo-sync.test.ts와 동일 관례).
import AppHeader from './AppHeader';

type ElementNode = { type: unknown; props?: { children?: unknown; [key: string]: unknown } };

function isElementNode(node: unknown): node is ElementNode {
  return typeof node === 'object' && node !== null && 'type' in node && 'props' in node;
}

function collectNodes(node: unknown, out: ElementNode[] = []): ElementNode[] {
  if (node == null || typeof node === 'boolean') return out;
  if (Array.isArray(node)) {
    node.forEach((child) => collectNodes(child, out));
    return out;
  }
  if (isElementNode(node)) {
    out.push(node);
    collectNodes(node.props?.children, out);
  }
  return out;
}

function collectText(node: unknown): string[] {
  if (node == null || typeof node === 'boolean') return [];
  if (typeof node === 'string' || typeof node === 'number') return [String(node)];
  if (Array.isArray(node)) return node.flatMap(collectText);
  if (isElementNode(node)) return collectText(node.props?.children);
  return [];
}

// <AppHeader ...> 태그 하나를 통째로 매치 — attribute 값이 따옴표 문자열이든 `{...}` 표현식이든
// (화살표 함수·비교 연산자 등으로 그 안에 `>`가 나와도) 진짜 태그 종료에서만 멈춘다(3차 리뷰 P1).
const ATTR_VALUE = `"[^"]*"|'[^']*'|\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}`;
const APP_HEADER_TAG = new RegExp(
  `<AppHeader\\b(?:\\s+[a-zA-Z][\\w-]*(?:=(?:${ATTR_VALUE}))?)*\\s*/?>`,
  'g',
);

// variant="admin"과 동치 표현(variant={'admin'} / variant={"admin"})을 모두 인정한다(3차 리뷰 P1).
const VARIANT_ADMIN = /variant\s*=\s*(?:"admin"|\{\s*(['"])admin\1\s*\})/;

// 소스 파일 목록 수집 — 두 스캔(정방향 P2·역방향 P3)이 공유한다. excludeDirs는 디렉터리 이름을
// 그대로 건너뛴다(역방향 스캔이 '(admin)'을 제외하는 데 쓴다).
function collectSourceFiles(dir: string, excludeDirs: string[] = []): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === '.next' || excludeDirs.includes(entry)) continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...collectSourceFiles(full, excludeDirs));
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith('.test.ts') && !entry.endsWith('.test.tsx')) {
      files.push(full);
    }
  }
  return files;
}

describe('AppHeader — admin/consumer 분기', () => {
  beforeEach(() => {
    h.rpcCalls.length = 0;
    h.rpcResult = { data: 0, error: null };
  });

  it('consumer(기본값): SiteNav에 email·currentPath·unreadCount가 그대로 전달되고, href="/"인 Link 안에 Logo가 있다', async () => {
    h.rpcResult = { data: 5, error: null };
    const tree = await AppHeader({ email: 'a@b.c', currentPath: '/search' });
    const nodes = collectNodes(tree);

    const siteNavNodes = nodes.filter((n) => n.type === SiteNav);
    expect(siteNavNodes).toHaveLength(1);
    expect(siteNavNodes[0].props?.email).toBe('a@b.c');
    expect(siteNavNodes[0].props?.currentPath).toBe('/search');
    // 안읽음 총합(FR57, Story 12.5) — consumer·로그인이면 chat_unread_count() RPC 결과를 그대로 넘긴다.
    expect(siteNavNodes[0].props?.unreadCount).toBe(5);
    expect(h.rpcCalls).toEqual(['chat_unread_count']);

    const homeLinks = nodes.filter((n) => n.type === Link && (n.props as { href?: string })?.href === '/');
    expect(homeLinks).toHaveLength(1);
    const logoInsideLink = collectNodes(homeLinks[0].props?.children).some((n) => n.type === Logo);
    expect(logoInsideLink).toBe(true);
  });

  it('consumer + 비로그인(email 없음): chat_unread_count()를 호출하지 않고 unreadCount는 undefined다', async () => {
    const tree = await AppHeader({ currentPath: '/search' });
    const nodes = collectNodes(tree);

    const siteNavNodes = nodes.filter((n) => n.type === SiteNav);
    // 렌더 여부부터 단언한다 — 없으면 siteNavNodes[0]가 undefined라 아래 unreadCount 단언이
    // "내비가 통째로 사라져도 통과"하는 검사가 된다(후속 코드리뷰 patch).
    expect(siteNavNodes).toHaveLength(1);
    expect(siteNavNodes[0].props?.unreadCount).toBeUndefined();
    expect(h.rpcCalls).toEqual([]);
  });

  it('RPC가 실패해도 헤더는 렌더되고 배지만 빠진다(비차단 폴백)', async () => {
    // 배지는 부가 정보다 — 이 폴백이 깨져 예외가 위로 던져지면 AppHeader를 쓰는 소비자 페이지가
    // 통째로 500이 된다. 하네스에 error 필드는 있었지만 이 분기를 실행하는 테스트가 없었다
    // (후속 코드리뷰 patch — verification-gap 지적).
    h.rpcResult = { data: null, error: { message: 'boom' } };
    // 폴백 경로가 남기는 진단 로그는 이 테스트에서 의도된 출력이라 삼킨다(테스트 출력 오염 방지).
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    const tree = await AppHeader({ email: 'a@b.c', currentPath: '/search' });
    const nodes = collectNodes(tree);

    expect(consoleError).toHaveBeenCalledTimes(1);
    consoleError.mockRestore();

    const siteNavNodes = nodes.filter((n) => n.type === SiteNav);
    expect(siteNavNodes).toHaveLength(1);
    expect(siteNavNodes[0].props?.unreadCount).toBeUndefined();
    expect(h.rpcCalls).toEqual(['chat_unread_count']);
  });

  it('admin: SiteNav도 Logo도 없고, roleLabel·email 문자열은 들어 있고, LogoutButton은 반드시 있다 — chat_unread_count()도 호출하지 않는다', async () => {
    const tree = await AppHeader({ variant: 'admin', email: 'a@b.c', roleLabel: '관리자' });
    const nodes = collectNodes(tree);

    expect(nodes.some((n) => n.type === SiteNav)).toBe(false);
    expect(nodes.some((n) => n.type === Logo)).toBe(false);
    // 3차 리뷰 지적 P2 — admin은 requireAdmin()을 통과해야만 도달하므로 이 버튼이 로그아웃의
    // 유일한 수단이다. 이게 빠지면 관리자가 관리자 콘솔에서 못 나가는데 lint/tsc/vitest는 몰랐다.
    expect(nodes.some((n) => n.type === LogoutButton)).toBe(true);
    // admin 분기는 email이 있어도 RPC를 호출하지 않는다(스펙: "admin 분기·비로그인은 호출 안 함").
    expect(h.rpcCalls).toEqual([]);

    const text = collectText(tree).join(' ');
    expect(text).toContain('관리자');
    expect(text).toContain('a@b.c');
  });
});

describe('web/src/app/(admin)/ 아래 <AppHeader 호출부는 전부 variant="admin"을 함께 전달한다', () => {
  it('소스 스캔 — <AppHeader 태그가 나오는 모든 곳에 variant="admin"(동치 표현 포함)이 같은 태그 안에 있다', () => {
    const ADMIN_ROOT = fileURLToPath(new URL('../../app/(admin)/', import.meta.url));

    const files = collectSourceFiles(ADMIN_ROOT);
    expect(files.length).toBeGreaterThan(0); // 스캔 대상 자체가 없으면 이 검사는 늘 green이라 무의미

    let checkedCallSites = 0;
    for (const file of files) {
      const content = readFileSync(file, 'utf-8');
      const tagMatches = content.match(APP_HEADER_TAG) ?? [];
      for (const tag of tagMatches) {
        checkedCallSites += 1;
        expect(VARIANT_ADMIN.test(tag)).toBe(true);
      }
    }
    expect(checkedCallSites).toBeGreaterThan(0); // <AppHeader 호출부를 실제로 하나도 못 찾으면 이 검사도 무의미
  });
});

describe('web/src/app/(admin)/ 바깥의 <AppHeader 호출부는 전부 variant="admin"을 전달하지 않는다', () => {
  it('소스 스캔(역방향, 3차 리뷰 P3) — (admin)/를 제외한 모든 <AppHeader 호출부에 variant="admin"이 없다', () => {
    const APP_ROOT = fileURLToPath(new URL('../../app/', import.meta.url));

    const files = collectSourceFiles(APP_ROOT, ['(admin)']);
    expect(files.length).toBeGreaterThan(0); // 스캔 대상 자체가 없으면 이 검사는 늘 green이라 무의미

    let checkedCallSites = 0;
    for (const file of files) {
      const content = readFileSync(file, 'utf-8');
      const tagMatches = content.match(APP_HEADER_TAG) ?? [];
      for (const tag of tagMatches) {
        checkedCallSites += 1;
        expect(VARIANT_ADMIN.test(tag)).toBe(false);
      }
    }
    expect(checkedCallSites).toBeGreaterThan(0); // <AppHeader 호출부를 실제로 하나도 못 찾으면 이 검사도 무의미
  });
});
