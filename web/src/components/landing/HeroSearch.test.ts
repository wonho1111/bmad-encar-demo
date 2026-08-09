// HeroSearch 히어로 배경 실루엣 렌더 계약 검사(spec-16-10 코드리뷰 2패스 지적).
//
// 왜 이 파일이 생겼나: spec-16-10이 이 스토리의 **유일한 웹 산출물**로 차 실루엣 <svg>를 넣었는데,
// 그걸 보는 자동 검사가 0건이었다 — 코드리뷰의 세 렌즈가 같은 사실에 독립적으로 수렴했다.
// 실제로 지워도 `npm run lint`·`next build`·`vitest run`이 전부 green이고, Playwright E2E는
// 애초에 CI에 없다(.github/workflows/tests.yml — 의도적 결정). 즉 이 파일이 없으면 웹 실루엣은
// "조용히 사라져도 아무도 모르는" 상태다.
//
// 왜 이 기법인가: HeroSearch는 'use client'이고 useState·useEffect·useRouter를 쓰므로 함수를 직접
// 호출할 수 없다(React가 훅 디스패처를 못 찾는다). SiteNav.test.ts와 같은 renderToStaticMarkup
// (react-dom/server)으로 초기 렌더 마크업만 뽑는다 — useEffect는 SSR에서 실행되지 않으므로 이
// 파일이 고정하는 건 **마운트 직후 마크업**뿐이다. useRouter·supabase 클라이언트는 브라우저 전용
// 컨텍스트를 요구하므로 vi.mock으로 대체한다(AppHeader.test.ts·ListingCard.test.ts 선례).
//
// 이 파일이 보지 않는 것(추측이 아니라 기법상 불가): 실제 브라우저에서 계산된 위치·크기(Tailwind
// 임의값이 CSS로 컴파일되는지, -bottom-[6%]가 몇 px로 떨어지는지)는 마크업만으로는 알 수 없다.
// 그건 E2E/육안 몫이며, spec-16-10 코드리뷰 2패스에서 실제 브라우저로 390px·1440px를 실측했다.
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import HeroSearch from './HeroSearch';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));
vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({ auth: { getUser: async () => ({ data: { user: null } }) } }),
}));

// 앱(app/lib/features/auth/home_screen.dart `_CarSilhouettePainter._carPath`)과 목업
// (consistency-1.html `.silhouette`)이 쓰는 것과 **글자 그대로 같은** path 데이터.
// 여기를 고치면 앱 쪽도 같이 고쳐야 한다 — 지금은 두 사본을 비교하는 검사가 없다([[DW-772]]).
const CAR_PATH =
  'M6,150 C30,120 74,112 122,110 L168,72 C188,54 224,45 276,45 L398,47 C452,49 496,71 528,110 ' +
  'L590,122 C618,128 634,144 634,168 L634,192 L566,192 A42,42 0 0 0 482,192 L246,192 ' +
  'A42,42 0 0 0 162,192 L26,192 C14,192 6,183 6,170 Z';

describe('HeroSearch — 차 실루엣 배경 장식(spec-16-10)', () => {
  for (const authed of [false, true]) {
    it(`authed=${authed}: 목업과 같은 viewBox·path·바퀴 2개를 배경으로 렌더한다`, () => {
      const html = renderToStaticMarkup(createElement(HeroSearch, { authed }));

      expect(html).toContain('viewBox="0 0 640 220"');
      expect(html).toContain(CAR_PATH);
      expect(html).toContain('cx="204"');
      expect(html).toContain('cx="524"');
      // 장식이므로 스크린리더에서 숨고 클릭을 먹지 않아야 한다.
      expect(html).toContain('aria-hidden="true"');

      // 코드리뷰 3패스 지적 — 위 단언은 "svg가 있다"까지만 본다. **배경 장식으로 성립시키는
      // 클래스**(absolute·fill-white·-right-[4%]·opacity-[.10])와 preserveAspectRatio는
      // 아무도 안 봤다: 실측으로 `absolute`+`fill-white`를 지워도, `-right-[4%]`를
      // `-left-[4%]`로 뒤집고 preserveAspectRatio를 `none`으로 바꿔도 이 파일이 3/3 green이었다.
      // `absolute`가 빠지면 svg가 흐름 안 블록이 돼 <h1>을 아래로 밀고, `fill-white`가 빠지면
      // petrol 그라데이션 위에 검정 10%가 되어 사실상 안 보인다 — 둘 다 "svg는 있는데 배경이
      // 아닌" 상태다. 클래스가 다른 요소에서 우연히 매칭되지 않도록 **이 svg의 여는 태그만**
      // 잘라내 그 안에서 단언한다.
      const svgTag = html.slice(
        html.indexOf('<svg'),
        html.indexOf('>', html.indexOf('viewBox="0 0 640 220"')) + 1,
      );
      expect(svgTag).toContain('viewBox="0 0 640 220"'); // 잘라내기가 실제로 그 태그를 잡았는지
      expect(svgTag).toContain('preserveAspectRatio="xMaxYMid meet"');
      for (const cls of [
        'absolute',
        'pointer-events-none',
        'fill-white',
        '-right-[4%]',
        'opacity-[.10]',
        // 배치 = 목업의 **웹** 프레임 규칙(consistency-1.html:170 `.silhouette`) — 앱 프레임의
        // top 기준을 웹에 복사하면 높이가 유동적인 <section>에서 무너진다(2패스 실측: 390px에서
        // 잉크의 25%만 보였다). bottom 기준 + 640px 상한이 그 교정이다.
        '-bottom-[6%]',
        'w-[min(58%,640px)]',
      ]) {
        expect(svgTag).toContain(cls);
      }
      // 앱 프레임의 top 기준으로 되돌아가지 않았는지. ⚠️ 이 클래스명을 **한 덩어리 문자열로 적지
      // 않는다** — Tailwind v4는 `src/**`의 모든 파일(테스트 포함)을 문자열 스캔해 후보 클래스를
      // 뽑으므로, 여기에 그대로 적으면 금지하려던 그 유틸리티가 프로덕션 CSS로 방출된다
      // (코드리뷰 3패스 실측: 클린 빌드한 `.next/static/chunks/*.css`에 `top:-14%`가 실제로
      // 들어 있었고, 리포 전체에서 그 문자열의 유일한 출처가 이 줄이었다).
      expect(svgTag).not.toContain('-top-' + '[14%]');
    });
  }

  it('실루엣이 콘텐츠보다 먼저(= 아래에 깔리게) 나온다', () => {
    // z-index 없이 트리 순서만으로 배경이 되므로, svg가 헤드라인 뒤로 밀리면 콘텐츠를 덮는다.
    const html = renderToStaticMarkup(createElement(HeroSearch, { authed: false }));
    const svgAt = html.indexOf('viewBox="0 0 640 220"');
    const h1At = html.indexOf('<h1');
    // 둘 다 실제로 있어야 한다 — 없으면 indexOf가 -1이라 아래 비교가 조용히 통과한다(실측 확인:
    // svg 블록을 통째로 지우는 뮤테이션에서 이 테스트만 green으로 남았다).
    expect(svgAt).toBeGreaterThanOrEqual(0);
    expect(h1At).toBeGreaterThanOrEqual(0);
    expect(svgAt).toBeLessThan(h1At);
  });
});
