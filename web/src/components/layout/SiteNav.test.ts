// SiteNav 렌더 계약 검사(Story 11.2 3차 코드리뷰 지적 P4·P5, CLAUDE.md B9 "규칙은 어길 수 없는
// 자리에 박는다") — SiteNav는 이 스토리의 소비자 내비 본체인데 지금까지 자동 검사가 0개였다.
// 로그인 상태별 링크 구성(비로그인 로그인/내 차 등록 ↔ 로그인 찜/채팅/프로필▾), redirectedFrom
// 쿼리스트링, 760px 브레이크포인트, 44px 히트영역 — 이 전부가 코드리뷰에서 "지워도 lint·tsc·
// vitest·build가 green"으로 실측 확인됐다.
//
// 왜 이 기법인가: SiteNav는 'use client'이고 useState·useEffect·useRef를 쓰므로 AppHeader.test.ts·
// ListingCard.test.ts처럼 함수를 **직접 호출**하면 안 된다 — React가 훅 디스패처를 못 찾아
// "Cannot read properties of null (reading 'useState')"로 즉시 throw한다(직접 확인함). 대신
// react-dom(런타임 의존성으로 이미 있음)의 renderToStaticMarkup을 쓴다 — 이건 서버 사이드 정적
// HTML 문자열만 만들고 useEffect는 실행하지 않는다(SSR과 동일 계약, 직접 확인함: 아래 vitest
// 실행 결과 기준으로 이 파일 작성 전 스크래치 테스트로 렌더가 throw 없이 정상 동작함을 실측).
// 그래서 이 파일이 고정하는 건 **초기 렌더(mount 직후, 이펙트 이전) 마크업**뿐이다 — outside-click
// 닫기·760px 리사이즈 감지(둘 다 useEffect)·클릭으로 드롭다운을 여는 상호작용은 이 파일 범위 밖
// (jsdom도 이벤트 디스패치도 없다 — E2E 몫).
//
// 로그인(email 있음) 케이스의 프로필▾ 드롭다운 내부(내 정보 href="/account"·내 매물 관리·
// LogoutButton)는 초기 렌더에 아예 없다 — profileOpen이 useState(false)로 시작해서 그 블록이
// `{profileOpen && (...)}`로 조건부 렌더되기 때문(직접 확인함, 아래 실행 결과 참고). 클릭 이벤트 없이
// 그 상태를 true로 만들 방법이 이 SSR-only 기법엔 없으므로, 드롭다운 내부 링크는 이 파일이 아니라
// E2E의 몫으로 남긴다 — 로그인 케이스에서는 초기 렌더에도 항상 보이는 찜·채팅·프로필▾ 트리거만 본다.
import { createElement } from 'react';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import SiteNav from './SiteNav';

describe('SiteNav — 초기 렌더 계약', () => {
  it('비로그인 + currentPath 있음: 로그인 링크가 redirectedFrom을 싣고, 3개 내비 링크가 있고, 찜·채팅은 없다', () => {
    const html = renderToStaticMarkup(createElement(SiteNav, { email: null, currentPath: '/search' }));

    expect(html).toContain('href="/login?redirectedFrom=%2Fsearch"');
    expect(html).toContain('href="/search"');
    expect(html).toContain('href="/ai"');
    expect(html).toContain('href="/sell"');
    expect(html).not.toContain('href="/wishlist"');
    expect(html).not.toContain('href="/chat"');
  });

  it('비로그인 + currentPath 없음: 로그인 링크가 쿼리스트링 없이 정확히 /login이다', () => {
    const html = renderToStaticMarkup(createElement(SiteNav, { email: null }));

    expect(html).toContain('href="/login"');
    expect(html).not.toContain('redirectedFrom');
  });

  it('로그인: 찜·채팅 아이콘 링크와 프로필▾ 트리거가 있고, redirectedFrom 로그인 링크는 없다', () => {
    const html = renderToStaticMarkup(createElement(SiteNav, { email: 'a@b.c', currentPath: '/search' }));

    expect(html).toContain('href="/wishlist"');
    expect(html).toContain('href="/chat"');
    // 프로필▾ 트리거 버튼 — 위 헤더 코멘트 참조: 드롭다운 내부(href="/account" 등)는 profileOpen이
    // 초기값 false라 이 초기 렌더 마크업에 없으므로 여기서 단언하지 않는다(E2E 몫).
    expect(html).toContain('aria-label="프로필 메뉴 열기"');
    expect(html).toContain('프로필');
    expect(html).not.toContain('redirectedFrom');
  });
});

describe('SiteNav — 측정값 고정(760px 브레이크포인트·44px 히트영역)', () => {
  it('소스 스캔(3차 코드리뷰 지적 P5) — 760px과 44px(h-11 w-11)은 mockups 실측치라 값 자체를 고정한다', () => {
    // 이 검사는 **값**만 고정한다 — 760이 750으로, 44px이 다른 값으로 바뀌면 lint·tsc·vitest·
    // build가 전부 green이었다(리뷰 실측). 실제 렌더 결과(그 값이 브라우저에서 레이아웃을 어떻게
    // 바꾸는지)는 여기서 보지 않는다 — 그건 여전히 E2E 몫이다.
    const SITE_NAV_FILE = fileURLToPath(new URL('./SiteNav.tsx', import.meta.url));
    const content = readFileSync(SITE_NAV_FILE, 'utf-8');

    expect(content).toContain("matchMedia('(min-width: 760px)')");

    // "760px이 최소 3번"만 세면 안 잡히는 구멍이 있었다(실측: 4번 중 1번만 750px로 바꿔도
    // ">=3"은 여전히 참) — 그래서 "arbitrary variant 전체 개수"와 "760px인 것의 개수"가
    // 정확히 같은지까지 함께 확인한다. 하나라도 다른 값(750px 등)이면 두 숫자가 어긋난다.
    const anyBreakpointOccurrences = (content.match(/min-\[\d+px\]:/g) ?? []).length;
    const breakpoint760Occurrences = (content.match(/min-\[760px\]:/g) ?? []).length;
    expect(anyBreakpointOccurrences).toBeGreaterThanOrEqual(3);
    expect(breakpoint760Occurrences).toBe(anyBreakpointOccurrences);

    expect(content).toContain('h-11 w-11');
  });
});
