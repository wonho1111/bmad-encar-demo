// /chat 뒤로가기 배지 새로고침 배선 계약 검사 (대장 #215 최소 수정, Story 12.6 코드리뷰 patch,
// CLAUDE.md B9 — "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 소스 스캔이고 실제 렌더·이벤트 발생 테스트가 아닌가(코드리뷰가 후자를 요청했으나 실측으로
// 확인한 제약):
//   `ChatListBfcacheRefresh.tsx`는 훅(useEffect)이 있는 클라이언트 컴포넌트라 실제로 마운트해
//   `popstate`를 발생시키고 `router.refresh()` 호출을 관찰하려면 jsdom(또는 동급의 DOM 환경)이
//   필요하다. 이 저장소의 `vitest.config.ts`는 **의도적으로** `environment: 'node'`이고 도입부
//   주석이 "jsdom·React Testing Library는 여전히 안 붙인다"를 프로젝트 결정으로 명시한다.
//   실측(`node -e "require.resolve('jsdom')"`, `find node_modules -iname jsdom`) 결과 `jsdom`·
//   `happy-dom`·`react-test-renderer` 전부 설치돼 있지 않다(vitest의 선택적 peer로만 잠겨 있고
//   실제 패키지는 없음) — 새로 설치하는 것은 이 스토리의 "사소한 patch" 범위를 넘는 저장소
//   전체 테스트 아키텍처 결정이라 임의로 하지 않는다. 그래서 이 파일은 같은 폴더의
//   `unreadWiringContract.test.ts`·`[roomId]/__tests__/roomTopicContract.test.ts`와 동일한
//   "소스에 박힌 계약을 정적으로 고정" 방식을 따른다.
//
// 이 검사가 **안 보는 것**: `popstate`가 실제로 발생했을 때 `router.refresh()`가 정말 호출되는지
//   (런타임 동작) — 그건 Story 12.6의 수동 브라우저 검증(실제 back-navigation으로 배지가
//   0.3~3.3초 내 정확한 값으로 갱신됨을 확인) 몫이다. 여기서는 (a) popstate 리스너가 등록·해제
//   되는지, (b) 새로고침 호출이 "/chat 경로일 때만"이라는 가드 **안에** 있는지(다른 경로에서는
//   호출되지 않는다는 사실의 정적 증거), (c) 이 컴포넌트가 실제로 루트 레이아웃에서 렌더되는지
//   (렌더 자체가 빠지면 아무 것도 동작하지 않는다) 세 축만 고정한다.
//   또 하나(후속 코드리뷰, 뮤테이션 검증): (b) 검사는 `if (path === '/chat') { router.refresh(); }`
//   가드의 텍스트와 위치만 고정한다 — `handlePopState`가 실제로 그 줄까지 **도달하는지(제어
//   흐름)**는 보지 않는다. `handlePopState` 맨 앞에 `if (!document.hidden) return;`을 끼워
//   넣어도(브라우저 탭이 안 보일 때만 뒤로가기가 일어나는 실제 상황에서는 항상 여기서 먼저
//   돌아나가 버려 아래 가드까지 내려가지 못한다) 이 파일의 검사도 전체 스위트(288건)도 그대로
//   통과한다 — 정적 소스 스캔이라 함수 앞부분의 조기 반환까지는 못 따진다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const COMPONENT = new URL('../ChatListBfcacheRefresh.tsx', import.meta.url);
const ROOT_LAYOUT = new URL('../../../layout.tsx', import.meta.url);

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
}

describe('/chat 뒤로가기 배지 새로고침 배선 계약 (#215)', () => {
  it('popstate 리스너를 등록하고 cleanup에서 해제한다', () => {
    const code = stripComments(read(COMPONENT));
    expect(code).toMatch(/window\.addEventListener\(\s*'popstate'\s*,\s*handlePopState\s*\)/);
    expect(code).toMatch(/window\.removeEventListener\(\s*'popstate'\s*,\s*handlePopState\s*\)/);
  });

  it("'use client' 지시자가 파일 첫 줄에 있다", () => {
    // 이 컴포넌트는 **서버 컴포넌트인 루트 레이아웃이 직접 import**하고 useRouter·useEffect를
    // 쓴다 — 'use client'가 빠지면 RSC 경계 위반으로 `next build`가 앱 **전체**(모든 라우트)에서
    // 실패한다. 그런데 뮤테이션 실증: 이 줄을 지워도 vitest 288건·`npm run lint`는 전부 통과했다.
    // web CI 잡은 `npm ci`+`npm run lint`+`npm test`만 돌고 `next build` 단계가 없어서(대장 #229),
    // CI가 초록인 채로 배포 빌드에서야 터진다. 그래서 여기서 정적으로 고정한다.
    expect(read(COMPONENT).trimStart(), "파일 첫 줄에 'use client'가 있어야 합니다").toMatch(
      /^['"]use client['"];/,
    );
  });

  it('router.refresh() 호출이 "/chat 경로일 때"라는 가드 안에 있다(다른 경로에서는 호출되지 않는다)', () => {
    const code = stripComments(read(COMPONENT));

    // 비교 대상 path가 **실제 URL 경로에서 온다**는 것까지 고정한다(후속 리뷰 patch) — 뮤테이션
    // 실증: `window.location.pathname`을 `window.location.hash`로 바꾸면 이 컴포넌트는 영구히
    // 아무 일도 하지 않게 되는데(= #215가 조용히 완전 재발), 아래 두 검사는 "정규화가 있다"와
    // "가드 안에 refresh가 있다"만 보기 때문에 스위트 288건이 그대로 통과했다.
    expect(code, "가드가 비교하는 path는 window.location.pathname에서 와야 합니다").toMatch(
      /const\s+path\s*=\s*window\.location\.pathname\s*\.replace\(/,
    );

    // 끝 슬래시 정규화(코드리뷰 patch, 항목4) — '/chat/'도 '/chat'과 같게 취급해야 한다.
    expect(code).toMatch(/\.replace\(\s*\/\\\/\+\$\/\s*,\s*''\s*\)/);

    // router.refresh()가 가드 밖(무조건 호출)으로 빠지면 이 정규식이 못 잡는다 — if 블록의
    // 중괄호 안에서만 refresh 호출을 찾도록 앵커한다.
    expect(code).toMatch(/if\s*\(\s*path\s*===\s*'\/chat'\s*\)\s*\{\s*router\.refresh\(\)\s*;\s*\}/);
  });

  it('루트 레이아웃(app/layout.tsx)이 이 컴포넌트를 실제로 렌더한다', () => {
    const code = stripComments(read(ROOT_LAYOUT));
    expect(code).toMatch(/import\s+ChatListBfcacheRefresh\s+from\s+['"].*ChatListBfcacheRefresh['"]/);
    expect(code).toMatch(/<ChatListBfcacheRefresh\s*\/>/);
  });
});
