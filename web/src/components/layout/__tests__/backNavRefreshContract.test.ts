// 뒤로가기 복귀 새로고침 배선 계약 검사 (대장 DW-525 해소 · 구 #215 확장, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// **이 파일의 이력:** 원래는 `(user)/chat/__tests__/bfcacheRefreshContract.test.ts`였고,
// "router.refresh()가 `/chat` 경로일 때**만** 불린다"를 고정하고 있었다. 2026-07-29에 그 가드가
// 제거되면서(찜 하트가 뒤로가기 때 옛 상태로 되살아나는 같은 결함이 다른 화면에서 재발 — DW-525)
// **계약이 뒤집혔다.** 그래서 검사도 함께 뒤집는다: 이제 고정해야 하는 규칙은 "가드가 없다"이다.
// 옛 검사를 그냥 지우지 않고 뒤집어 남기는 이유 — 가드가 조용히 되살아나면(그게 바로 DW-525가
// 기록한 회귀 방향이다) 이 검사가 red가 돼야 한다.
//
// 왜 소스 스캔이고 실제 렌더·이벤트 발생 테스트가 아닌가(원 파일에서 실측으로 확인된 제약 — 그대로):
//   이 컴포넌트는 훅(useEffect)이 있는 클라이언트 컴포넌트라 실제로 마운트해 `popstate`를 발생시키고
//   `router.refresh()` 호출을 관찰하려면 jsdom(또는 동급 DOM 환경)이 필요하다. 이 저장소의
//   `vitest.config.ts`는 **의도적으로** `environment: 'node'`이고 "jsdom·React Testing Library는
//   여전히 안 붙인다"를 프로젝트 결정으로 명시한다(실측: jsdom·happy-dom·react-test-renderer 미설치).
//   그래서 같은 폴더 관례대로 "소스에 박힌 계약을 정적으로 고정"한다.
//
// 이 검사가 **안 보는 것**: 이벤트가 실제로 왔을 때 `router.refresh()`가 정말 호출되는지(런타임
//   동작)와, 핸들러 앞부분에 조기 반환이 끼어드는 경우 — 정적 스캔이라 제어 흐름은 못 따진다.
//   런타임 축은 브라우저 실측 몫이다(2026-07-29: `/search`에서 찜 → 다른 화면 → 뒤로가기 →
//   하트가 실제 DB 상태로 갱신되는 것을 Playwright로 확인).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const COMPONENT = new URL('../BackNavRefresh.tsx', import.meta.url);
const ROOT_LAYOUT = new URL('../../../app/layout.tsx', import.meta.url);

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
}

describe('뒤로가기 복귀 새로고침 배선 계약 (DW-525)', () => {
  it('popstate·pageshow 리스너를 등록하고 cleanup에서 둘 다 해제한다', () => {
    const code = stripComments(read(COMPONENT));
    expect(code).toMatch(/window\.addEventListener\(\s*'popstate'\s*,\s*handlePopState\s*\)/);
    expect(code).toMatch(/window\.removeEventListener\(\s*'popstate'\s*,\s*handlePopState\s*\)/);
    // pageshow = 문서 단위 bfcache 복원(외부 사이트 → 뒤로가기). popstate가 안 오는 경로라
    // 이것까지 있어야 DW-525가 지적한 나머지 절반이 닫힌다.
    expect(code).toMatch(/window\.addEventListener\(\s*'pageshow'\s*,\s*handlePageShow\s*\)/);
    expect(code).toMatch(/window\.removeEventListener\(\s*'pageshow'\s*,\s*handlePageShow\s*\)/);
  });

  it("'use client' 지시자가 파일 첫 줄에 있다", () => {
    // 이 컴포넌트는 **서버 컴포넌트인 루트 레이아웃이 직접 import**하고 useRouter·useEffect를
    // 쓴다 — 'use client'가 빠지면 RSC 경계 위반으로 `next build`가 앱 **전체**(모든 라우트)에서
    // 실패한다. 그런데 뮤테이션 실증(원 파일 시절): 이 줄을 지워도 vitest·`npm run lint`는 전부
    // 통과했다. web CI 잡에 `next build` 단계가 없어서(대장 구 #229) CI가 초록인 채로 배포
    // 빌드에서야 터진다. 그래서 여기서 정적으로 고정한다.
    expect(read(COMPONENT).trimStart(), "파일 첫 줄에 'use client'가 있어야 합니다").toMatch(
      /^['"]use client['"];/,
    );
  });

  it('popstate 새로고침에 경로 가드가 없다(모든 화면의 뒤로가기에서 돈다)', () => {
    const code = stripComments(read(COMPONENT));

    // 핸들러 본문이 refresh 호출 하나뿐이어야 한다 — `if (...) router.refresh()` 형태로 조건이
    // 다시 끼어들면 이 정규식이 못 잡는다(가드 부활 = DW-525 재발).
    expect(
      code,
      'handlePopState는 조건 없이 router.refresh()만 불러야 합니다(경로 가드 부활 금지)',
    ).toMatch(/function\s+handlePopState\(\)\s*\{\s*router\.refresh\(\)\s*;\s*\}/);

    // 옛 가드가 기대던 값 자체가 소스에 남아 있으면 안 된다 — 되살리기 쉬운 흔적을 없앤 상태로 고정.
    expect(code, '경로 비교 가드(location.pathname)가 남아 있으면 안 됩니다').not.toMatch(
      /window\.location\.pathname/,
    );
  });

  it('pageshow는 persisted(bfcache 복원)일 때만 새로고침한다', () => {
    const code = stripComments(read(COMPONENT));
    // persisted=false는 평범한 최초 로드다 — 방금 서버에서 받은 화면을 또 부르면 순수한 낭비이자
    // 모든 첫 진입에 왕복이 1회씩 더 붙는다.
    expect(code).toMatch(/if\s*\(\s*event\.persisted\s*\)\s*router\.refresh\(\)/);
  });

  it('루트 레이아웃(app/layout.tsx)이 이 컴포넌트를 실제로 렌더한다', () => {
    // 렌더 자체가 빠지면 위 계약이 전부 참이어도 아무 일도 일어나지 않는다.
    const code = stripComments(read(ROOT_LAYOUT));
    expect(code).toMatch(/import\s+BackNavRefresh\s+from\s+['"].*BackNavRefresh['"]/);
    expect(code).toMatch(/<BackNavRefresh\s*\/>/);
  });
});
