// 가입 요청에 role 메타데이터를 싣지 않는다 — 실행되는 검사 (Story 14.2 후속 리뷰,
// CLAUDE.md B9 "주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 이 검사가 생겼나:
//   Story 14.2의 web 쪽 계약은 딱 한 줄이다 — `signUp()`에 `options.data.role`을 안 보낸다.
//   그래야 DB 트리거(0028_handle_new_user_default_role.sql)의 기본값 'user'가 적용되고,
//   FR52("로그인만 하면 누구나 사고팔 수 있다")가 성립한다.
//   그런데 그 계약을 지키는 것이 **주석 한 줄뿐**이었다(실측: 리뷰 세션이 signup/page.tsx에
//   `options: { data: { role: 'seller' } }`를 되돌려 넣고 web CI 잡의 두 명령을 그대로 돌렸더니
//   `npm run lint` exit 0 · vitest 308건 전부 통과 — 아무 것도 안 걸렸다).
//   DB 쪽 절반은 api/tests/integration/test_role_check_relax_real_db.py의 매트릭스가 지키지만,
//   그건 auth.users에 직접 INSERT하므로 **브라우저가 실제로 무엇을 보내는지는 관측하지 않는다**.
//
// 왜 정적 스캔인가(E2E가 아니라):
//   신규 가입→role='user'→/sell 도달을 확인하는 Playwright E2E가 더 강한 검사지만,
//   web/e2e는 CI 잡이 없어(대장 DW-664·DW-679) 게이트가 되지 못한다. 이 파일은 web CI 잡의
//   `npm test`(vitest)에 **배선돼 있다** — 약하지만 실제로 도는 검사다.
//   ⚠️ 단, 그 잡은 `.github/workflows/tests.yml`의 `on.push.branches: [develop, main]` 때문에
//   작업 브랜치(`test/bmad-loop`) push에서는 **안 돈다**(대장 DW-664, 열려 있음). 즉 지금
//   이 검사의 게이트는 "develop 병합 시점"이지 "커밋 시점"이 아니다.
//
// 이 검사가 **안 보는 것**(추측 아니라 실측):
//   · 런타임에 실제로 나가는 요청 바디는 안 본다. 소스에 없으면 안 나간다는 가정이며,
//     `supabase.auth.signUp`을 감싸는 헬퍼가 생기면 그 헬퍼는 이 검사 밖이다.
//   · 다른 화면(Flutter 앱 signup_screen.dart)은 안 본다 — 거긴 여전히 role을 보내고,
//     0028이 그 값을 하위호환으로 반영한다(의도된 상태, 대장 DW-678).
//   · 안내 문구·역할 선택 UI가 화면에 어떻게 보이는지는 안 본다(그건 E2E 몫).
//   · 소스 **전체**에서 `role`이라는 단어 자체는 못 막는다 — JSX의 `role="alert"`/`role="status"`
//     (접근성 속성)가 정당하게 존재하기 때문이다. 그래서 인자 객체 안에서만 `role`을 본다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const PAGE = fileURLToPath(new URL('../page.tsx', import.meta.url));

/**
 * 주석을 지운다 — 주석 안의 "role"이라는 단어를 위반으로 오인하지 않기 위해.
 *
 * `//` 앞에 `:`가 오면 지우지 않는다. 이전 구현은 `https://…` 같은 URL의 프로토콜 슬래시를
 * 줄 주석으로 오인해 **그 줄의 남은 코드를 통째로 지웠다**. 실측(두 구현을 같은 입력에 돌려 비교):
 * signUp 인자에 `emailRedirectTo: 'https://example.test/welcome',`를 넣으면 옛 구현이 잘라낸
 * 인자는 `… emailRedirectTo: 'https:` 에서 끊겼다 — 즉 **그 줄의 URL 뒤에 오는 것은 스캔에 안 보인다**.
 * 같은 줄에 `options: { data: { role: … } }`를 이어 쓰면 조용히 통과한다(거짓 음성). 중괄호
 * 짝맞춤도 URL 줄의 `}`가 지워지면 엉뚱한 위치에서 닫힌다.
 */
function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
}

/**
 * `supabase.auth.signUp({ ... })`의 인자 객체 본문을 중괄호 짝맞춤으로 잘라낸다.
 * 정규식으로 통째로 잡지 않는 이유: 중첩 객체(`options: { data: {...} }`)를 정확히 포함해야 하는데
 * 정규식의 `[^}]*`는 첫 `}`에서 끊겨 바로 그 중첩을 놓친다 — 잡아야 할 것만 골라 놓치는 셈이다.
 */
function extractSignUpArg(src: string): string | null {
  const call = src.indexOf('auth.signUp(');
  if (call === -1) return null;
  const open = src.indexOf('{', call);
  if (open === -1) return null;
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) return src.slice(open, i + 1);
    }
  }
  return null;
}

describe('web 가입 제출은 role 메타데이터를 보내지 않는다 (Story 14.2)', () => {
  const src = stripComments(readFileSync(PAGE, 'utf-8'));
  const arg = extractSignUpArg(src);

  it('검사 대상이 실제로 존재한다 (호출부를 못 찾은 상태를 통과로 오인하지 않는다)', () => {
    // 이 파일이 조용히 무력화되는 가장 흔한 방식은 "찾은 게 0건인데 전부 통과"다.
    // 호출부가 헬퍼로 빠지거나 이름이 바뀌면 여기서 먼저 red가 되어 검사를 옮기게 만든다.
    expect(arg).not.toBeNull();
    expect(arg).toContain('email');
    expect(arg).toContain('password');
  });

  it('signUp 호출부가 정확히 하나다 (두 번째 호출부가 검사 밖으로 새지 않는다)', () => {
    // extractSignUpArg는 **첫** 호출부만 본다. 호출부가 둘이 되면 두 번째는 아무도 안 보는데
    // 위 단언들은 그대로 통과한다(실측 확인). 그 상태를 통과가 아니라 red로 만든다.
    expect(src.split('auth.signUp(').length - 1).toBe(1);
  });

  it('signUp 인자에 options/data/role 키가 없다', () => {
    // `options`가 없으면 `options.data.role`도 있을 수 없다. 세 키를 각각 보는 이유는
    // 실패했을 때 "무엇이 되돌아왔는지"가 메시지에 바로 드러나게 하기 위해서다.
    expect(arg).not.toMatch(/\boptions\s*:/);
    expect(arg).not.toMatch(/\bdata\s*:/);
    expect(arg).not.toMatch(/\brole\b/);
  });

  it('signUp 인자를 스프레드로 채우지 않는다 (간접 전달 우회 차단)', () => {
    // 위 세 단언은 **인자 리터럴 안**만 본다. `const opts = { data: { role: 'seller' } };`를
    // 파일 위쪽에 두고 `signUp({ email, password, ...opts })`로 넘기면 role이 실제로 전송되는데도
    // 전부 통과한다(실측 확인 — 이게 계약을 깨는 가장 값싼 방법이다). 두 갈래로 막는다:
    //   ① 인자 객체에 스프레드가 아예 없을 것
    //   ② 파일 어디에도 `data:` 키가 없을 것 — 객체를 어디서 만들든 `options.data`를 채우려면
    //      결국 `data:`를 써야 한다. (`role:`은 못 쓴다 — JSX의 `role="alert"`가 정당하게 있다.)
    expect(arg).not.toContain('...');
    expect(src).not.toMatch(/\bdata\s*:/);
  });
});
