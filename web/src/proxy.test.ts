// PROTECTED_PREFIXES 멤버십 검사(Story 11.2 3차 코드리뷰 지적 P6, CLAUDE.md B9 "규칙은 어길 수
// 없는 자리에 박는다") — 이 배열에서 '/account'(이 스토리가 추가한 항목) 한 줄만 지워져도
// lint·tsc·vitest·build가 전부 green이다. 페이지 쪽엔 requireUser()라는 2차 게이트가 있어 비로그인
// 사용자에게 데이터가 새지는 않는다 — 하지만 requireUser()는 redirectedFrom을 실어주지 않으므로,
// proxy.ts가 먼저 안 막으면 로그인 후 사용자가 원래 가려던 '/account'로 못 돌아온다(리다이렉트
// 목적지 상실, UX 회귀). 이 배열은 export되지 않으므로(모듈 내부 상수) viewCountCallSite.test.ts와
// 같은 소스 스캔 기법 — 파일을 문자열로 읽어 배열 리터럴 안에 각 경로가 있는지 확인 — 을 그대로 쓴다.
//
// 이 검사가 안 보는 것: 배열에 경로 문자열이 들어 있는지(멤버십)만 본다 — 그 경로가 실제로
// 요청 시점에 매칭되는지(proxy() 함수의 isProtected 계산, pathname === p || startsWith(`${p}/`))는
// 이 파일 범위 밖이다. 그 매칭 로직 자체를 바꾸는 회귀(예: startsWith를 includes로 바꿔 엉뚱한
// 경로까지 걸리게 하는 것)는 여기서 못 잡는다 — 로직 검증은 실제 요청을 흘려보내는 E2E나 별도
// 단위테스트의 몫이다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const PROXY_FILE = fileURLToPath(new URL('./proxy.ts', import.meta.url));

describe('PROTECTED_PREFIXES 멤버십', () => {
  it('PROTECTED_PREFIXES 배열 리터럴이 6개 보호 경로를 모두 포함한다', () => {
    const content = readFileSync(PROXY_FILE, 'utf-8');
    const arrayMatch = content.match(/const PROTECTED_PREFIXES = (\[[^\]]*\])/);

    expect(arrayMatch).not.toBeNull(); // 선언 자체를 못 찾으면(이름·형태 변경) 이 검사는 무의미
    const arrayLiteral = arrayMatch![1];

    // '/account'는 이 스토리(Story 11.2)가 추가한 항목 — 지워지면 로그인 후 redirectedFrom으로
    // '/account'에 되돌아오는 경로가 조용히 사라진다.
    for (const path of ['/admin', '/sell', '/ai', '/chat', '/wishlist', '/account']) {
      expect(arrayLiteral).toContain(`'${path}'`);
    }
  });
});
