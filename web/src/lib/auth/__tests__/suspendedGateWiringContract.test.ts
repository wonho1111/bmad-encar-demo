// 정지(suspended) 게이트 **배선·순서** 계약 검사 (spec-17-3 후속 코드리뷰 patch, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가 (실측한 사각지대):
//   17.3의 로직 자체는 guard.test.ts·status.test.ts가 고정한다. 하지만 두 파일 모두 자기 하단의
//   "안 보는 것"에 **배선은 안 본다**고 직접 적었다 — guard.test.ts는 "page.tsx의 관리자 랜딩
//   분기가 이 조건과 락스텝인지"를, status.test.ts는 "ListingActions.tsx·SellForm.tsx가 실제로 이
//   함수들을 호출하는지"를 각각 web/e2e/suspended-access.spec.ts에 넘겼다.
//   그런데 `.github/workflows/tests.yml`(22행)이 **E2E는 이 워크플로에 배선돼 있지 않다**고 직접
//   적고 있다(로컬 `npm run test:e2e` 전용 — DW-468, wont-do 2026-08-10, E2E는 CI에 붙이지 않기로
//   확정됐다). 그래서 아래 중 무엇을
//   깨뜨려도 CI 4개 잡(api·api-db·web·app)이 전부 green이었다:
//     ① page.tsx의 `status === 'active'` 조건 제거 → 정지된 관리자에게 /admin ↔ / 무한 리다이렉트
//        (ERR_TOO_MANY_REDIRECTS — 이 스토리가 만들 수 있는 가장 큰 사고, 스펙 AC가 직접 지목)
//     ② guard.ts의 `.select('role, status')`를 `.select('role')`로 되돌림 → 정지된 관리자가
//        콘솔 열람 복귀(0032가 admin SELECT 정책을 is_admin() 그대로 뒀으므로 DB가 안 받쳐 준다)
//     ③ 4개 쓰기 경로 중 하나에서 getOwnStatus/writeRejectionMessage 제거 → DW-804(b) 증상 재발
//        ("자기 매물인데 소유권 문제라고 말한다")
//     ④ getOwnStatus 호출을 거부 판정 **앞으로** 끌어올림 → 화면이 사전 검사가 되어 강제력의
//        자리가 앱 코드로 옮겨간다(스토리 불변식·CLAUDE.md B9 위반). 문구는 그대로라 E2E조차
//        문구만으로는 못 잡고, 오직 "호출 순서"만이 이걸 구분한다.
//   ④가 이 파일의 존재 이유다 — 나머지 검사 전부가 "무엇이 뜨는가"를 보고, 이것만 "언제 부르는가"를 본다.
//
// 왜 소스 스캔인가: 이 리포의 web은 컴포넌트를 렌더하는 단위테스트를 두지 않는다
//   (project-context.md §12 — web은 E2E 우선, @testing-library 미도입). 대신 같은 리포가 이미 쓰는
//   기법을 그대로 따른다 — restoreSoldWiringContract.test.ts·unreadWiringContract.test.ts·
//   queueRetryWiringContract.test.ts와 동일한 "소스에 박힌 계약을 정적으로 고정" 방식이다.
//
// 기대값은 **글자 그대로 박는다**(메모리 self-consistent-assertions-never-fail, 스펙 Always 절):
//   'role, status'·'active'·'getOwnStatus' 등을 상수에서 import해 오면, 상수가 바뀔 때 요청과
//   기대가 함께 바뀌어 이 검사가 영원히 통과한다.
//
// 이 검사가 **안 보는 것**(추측이 아니라 구조적 한계):
//   · 런타임에 실제로 리다이렉트가 유한 번에 끝나는지 — 그건 브라우저 몫이다
//     (web/e2e/suspended-access.spec.ts A그룹이 ERR_TOO_MANY_REDIRECTS 없음을 확인한다).
//   · 화면에 뜨는 문구가 실제로 렌더되는지 — 여기서는 "그 코드가 호출을 갖고 있는가"만 본다.
//   · getOwnStatus가 리턴한 값을 호출부가 **옳게 쓰는지** — 그건 status.test.ts(순수 로직)와
//     E2E(실제 문구) 몫이다. 여기서는 호출의 존재와 순서만 본다.
//   · 관리자 콘솔 **쓰기** 액션(MemberActions.tsx 등)의 거부 문구 — 이 스토리 범위 밖이다
//     (deferred-work.md에 별도 등재).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const GUARD = new URL('../guard.ts', import.meta.url);
const HOME_PAGE = new URL('../../../app/page.tsx', import.meta.url);
const ADMIN_LAYOUT = new URL('../../../app/(admin)/layout.tsx', import.meta.url);
const LISTING_ACTIONS = new URL('../../../app/(user)/sell/ListingActions.tsx', import.meta.url);
const SELL_FORM = new URL('../../../app/(user)/sell/SellForm.tsx', import.meta.url);

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

/**
 * 주석(줄·블록)을 지운다 — 계약은 실행되는 코드에만 있고, 주석에 적힌 설명이 검사를 통과시키면
 * 안 된다. 이 스토리는 특히 그렇다: guard.ts·page.tsx의 주석이 `getOwnStatus`와 `status`를
 * 여러 번 언급하므로, 주석을 안 지우면 코드에서 조건을 통째로 지워도 아래 단언들이 green이다.
 *
 * ⚠️ restoreSoldWiringContract.test.ts와 동일한 한계 — 이 정규식은 문자열·템플릿·정규식 리터럴을
 * 구분하지 못한다. 리터럴 안에 `//`가 들어오면 그 줄의 나머지가 통째로 지워져 단언이 엉뚱한
 * 이유로 red가 될 수 있다. 그래서 호출부마다 `expectStripped`로 앵커 생존을 먼저 확인한다.
 */
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, '');
}

/** 주석 제거 후에도 반드시 남아 있어야 하는 앵커를 확인한다 — 과잉 제거를 조용한 통과가 아니라 실패로 만든다. */
function expectStripped(source: string, anchor: string, what: string): string {
  const code = stripComments(source);
  expect(code, `${what}: 주석 제거가 코드까지 지웠다(문자열 리터럴 안의 // 또는 /* 의심)`).toContain(
    anchor,
  );
  return code;
}

/** 함수 본문을 시작 앵커 ~ 끝 앵커로 잘라낸다(끝 앵커가 없으면 파일 끝까지). */
function sliceBody(code: string, startAnchor: string, endAnchor: string | null, what: string): string {
  const start = code.indexOf(startAnchor);
  expect(start, `${what}: 시작 앵커 '${startAnchor}'를 못 찾았다(함수 이름이 바뀌었는가?)`).toBeGreaterThan(-1);
  const end = endAnchor === null ? code.length : code.indexOf(endAnchor, start);
  expect(end, `${what}: 끝 앵커 '${endAnchor}'를 못 찾았다`).toBeGreaterThan(start);
  return code.slice(start, end);
}

/** 문자열 리터럴 또는 정규식 토큰을 `from` 위치부터 찾는다 — 정규식은 String.indexOf가 없어 별도 처리. */
function indexOfToken(body: string, token: string | RegExp, from: number): number {
  if (typeof token === 'string') return body.indexOf(token, from);
  const m = body.slice(from).match(token);
  return m && m.index !== undefined ? from + m.index : -1;
}

/**
 * 토큰들이 **이 순서대로** 나타나는지 확인한다 — 이 파일의 핵심 단언.
 *
 * 왜 존재만으로 부족한가: `getOwnStatus`가 파일 어딘가에 있다는 것과, 그것을 **거부를 받은 뒤에**
 * 부른다는 것은 완전히 다른 계약이다. 사전 검사로 끌어올려도 "존재" 검사는 계속 green이고,
 * 사용자에게 뜨는 문구도 똑같다 — 오직 순서만이 불변식("강제력은 DB에만")을 지킨다.
 *
 * 마지막 토큰은 정규식(`writeRejectionMessage(`+`status`가 첫 인자)일 수 있다(2026-08-11 3차
 * 코드리뷰 red 프로브 실측) — 문자열 `'writeRejectionMessage('`만 보면 `getOwnStatus`가 반환한
 * `status`를 실제로 넘기는지는 안 본다: `const status = await getOwnStatus(supabase); void status;`로
 * 조회만 해 놓고 `writeRejectionMessage(PROFILE_STATUS.ACTIVE, fallback)`처럼 **다른 값**을 넘겨도
 * 문자열 토큰은 여전히 green이었다 — 배선은 있지만 조회 결과가 실제로 안 쓰이는 "죽은 배선".
 */
function expectOrder(body: string, tokens: (string | RegExp)[], what: string): void {
  let cursor = -1;
  for (const [i, token] of tokens.entries()) {
    const at = indexOfToken(body, token, cursor + 1);
    expect(
      at,
      `${what}: '${token}'을 앞 토큰 뒤에서 못 찾았다 — 배선이 지워졌거나 순서가 뒤집혔다(사전 검사화 의심)`,
    ).toBeGreaterThan(cursor);

    // ⚠️ "뒤에 있다"만 보면 부족하다(2026-08-11 red 프로브가 실제로 뚫었다): 거부 판정 **앞에도**
    //    같은 호출을 하나 더 두면(앞에서 조회해 막고, 뒤 분기는 그대로 남겨 둠) 위 단언은 뒤엣것을
    //    찾아 계속 green이다. 그게 바로 사전 검사화의 실제 모양이다. 그래서 이 토큰의 **첫 등장**이
    //    곧 순서상의 그 자리여야 한다고 못박는다 — 앞에 하나라도 더 있으면 red.
    if (i > 0) {
      expect(
        indexOfToken(body, token, 0),
        `${what}: '${token}'이 '${tokens[0]}'(거부 판정)보다 **앞에서도** 호출된다 — 화면이 미리 막는 사전 검사가 됐다(스토리 불변식 위반: 강제력은 DB에만)`,
      ).toBe(at);
    }
    cursor = at;
  }
}

describe('정지 게이트 배선 계약 A — /admin 콘솔과 홈 랜딩의 락스텝 (DW-806)', () => {
  it('requireRole이 role과 status를 한 번에 읽고 active만 통과시킨다', () => {
    const code = expectStripped(read(GUARD), 'export async function requireRole', 'guard.ts');
    const body = sliceBody(code, 'export async function requireRole', null, 'requireRole');

    // ⓪ requireRole은 guard.ts의 마지막 선언이라 endAnchor를 null(파일 끝)로 둔다 — 그런데 그러면
    //    "파일 끝"이 실제로 이 함수가 끝나는 자리라는 전제가 검사되지 않은 채로 남는다. 아래 진짜
    //    조건을 지우고 파일 끝에 같은 패턴만 흉내 낸 죽은 코드(예: 안 쓰이는 export 함수)를
    //    덧붙이면, null 슬라이스가 그 디코이까지 통째로 삼켜 아래 단언들이 디코이 쪽에서 매치해
    //    green으로 남는다 — 그래서 파일이 정말로 이 함수의 닫는 중괄호에서 끝나는지를 먼저 못박는다.
    expect(
      code.trimEnd().endsWith('return user;\n}'),
      'guard.ts 파일이 requireRole의 닫는 중괄호에서 끝나지 않는다(뒤에 코드가 추가됐다 — 디코이로 이 검사를 우회할 수 있다)',
    ).toBe(true);

    // ① 두 컬럼을 실제로 읽는가 — 이걸 'role'로 되돌리면 status가 항상 undefined가 되어
    //    조건이 무의미해진다(guard.test.ts의 가짜 클라이언트는 select 인자를 무시하므로 못 잡는다).
    expect(
      /\.select\(\s*(['"`])role,\s*status\1\s*\)/.test(body),
      "requireRole이 .select('role, status')로 두 컬럼을 읽지 않는다 — status가 undefined가 되어 게이트가 무너진다",
    ).toBe(true);

    // ② active 비교가 살아 있는가.
    expect(
      body.includes('PROFILE_STATUS.ACTIVE'),
      'requireRole에 PROFILE_STATUS.ACTIVE 비교가 없다(정지된 관리자가 콘솔에 다시 들어온다)',
    ).toBe(true);

    // ③ 그 비교가 role 검사와 **같은 리다이렉트 조건**에 묶여 있는가.
    expect(
      /if\s*\([^)]*profile\?\.role\s*!==\s*role[^)]*profile\?\.status\s*!==\s*PROFILE_STATUS\.ACTIVE[^)]*\)/.test(
        body,
      ),
      'role 불일치와 status 비활성이 하나의 리다이렉트 조건에 함께 묶여 있지 않다',
    ).toBe(true);
  });

  it('홈의 관리자 랜딩 분기가 같은 status 조건을 요구한다(무한 리다이렉트 방지의 반대편)', () => {
    const code = expectStripped(read(HOME_PAGE), 'redirect(', 'page.tsx');

    // requireRole이 정지된 관리자를 /로 보내는데 여기가 role만 보면 다시 /admin으로 되돌려
    // /admin → / → /admin … 이 된다. 두 조건은 **반드시 함께** 움직인다.
    expect(
      /\.select\(\s*(['"`])role,\s*status\1\s*\)/.test(code),
      "page.tsx가 .select('role, status')로 status를 읽지 않는다(랜딩 분기가 status를 볼 수 없다)",
    ).toBe(true);

    // ⚠️ 두 비교 사이를 `[^)]*`(아무 문자)가 아니라 `&&`로 못박는다(2026-08-11 3차 코드리뷰
    //    red 프로브 실측): `[^)]*`는 `&&`↔`||` 교체를 구분하지 못했다 — `page.tsx:73`의 `&&`를
    //    `||`로 바꾸면 **로그인한 모든 활성 사용자**가 role만 admin이면 조건을 통과해 /admin으로
    //    보내지고(정지 여부와 무관하게 role만 봐도 통과), 그중 비관리자는 requireRole한테 다시
    //    홈으로 튕겨나가 `/admin → / → /admin → …` 무한 리다이렉트가 난다 — 이 파일 헤더가 막으려는
    //    사고 ①이다. 이 검사는 이전엔 그 교체에 green이었다.
    expect(
      /if\s*\(\s*profile\.role\s*===\s*USER_ROLE\.ADMIN\s*&&\s*profile\.status\s*===\s*PROFILE_STATUS\.ACTIVE\s*\)\s*\{\s*redirect\(\s*(['"`])\/admin\1/.test(
        code,
      ),
      "홈의 /admin 랜딩 분기가 role만 보고 status를 안 본다(또는 &&가 아닌 다른 연산자다) — 정지된 관리자에게 무한 리다이렉트가 난다",
    ).toBe(true);
  });

  it('(admin)/layout.tsx가 실제로 requireRole(USER_ROLE.ADMIN)을 await한다 — 콘솔 열람의 유일한 차단(DW-806, docs/conventions.md §8 예외)', () => {
    // 왜 필요한가: guard.test.ts는 requireRole의 순수 로직만 보고, 위 두 테스트는 guard.ts·page.tsx를
    // 각각 독립적으로 본다 — 정작 "그 함수가 /admin 라우트에 실제로 배선돼 있는가"를 아무도 안 본다.
    // requireRole(USER_ROLE.ADMIN) 호출을 requireUser()로 바꿔도(로그인만 확인, role·status 미확인)
    // 위 두 단위 검사는 전부 green이다 — 0032가 admin SELECT 정책을 is_admin() 그대로 둬서 DB가
    // 안 받쳐 주므로, 이 한 줄이 지워지면 정지된 관리자가 회원 개인정보·채팅 로그를 다시 열람한다.
    const code = expectStripped(read(ADMIN_LAYOUT), 'requireRole', '(admin)/layout.tsx');
    expect(
      /await\s+requireRole\(\s*USER_ROLE\.ADMIN\s*\)/.test(code),
      '(admin)/layout.tsx가 requireRole(USER_ROLE.ADMIN)을 await하지 않는다 — 콘솔 접근 통제가 배선에서 빠졌다',
    ).toBe(true);
  });
});

describe('정지 게이트 배선 계약 B — 4개 쓰기 경로가 거부 "뒤에" 사유를 조회한다 (DW-804 (b))', () => {
  // 순서 토큰의 의미: [거부 판정] → [사유 조회] → [문구 선택].
  // 가운데를 앞으로 끌어올리면(사전 검사) expectOrder가 red가 된다 — 이 파일의 존재 이유다.
  it('구매완료(ListingActions.handleComplete)', () => {
    const code = expectStripped(read(LISTING_ACTIONS), 'async function handleComplete', 'ListingActions.tsx');
    const body = sliceBody(code, 'async function handleComplete', 'async function handleDelete', 'handleComplete');
    expectOrder(body, ['length === 0', 'getOwnStatus(', /writeRejectionMessage\(\s*status\s*,/], '구매완료 경로');
  });

  it('삭제(ListingActions.handleDelete)', () => {
    const code = expectStripped(read(LISTING_ACTIONS), 'async function handleDelete', 'ListingActions.tsx');
    // ⚠️ endAnchor를 null(파일 끝)이 아니라 컴포넌트의 JSX `return (`로 못박는다(2026-08-11 3차
    //    코드리뷰 red 프로브 실측): handleDelete가 파일의 마지막 함수라 null을 쓰면, 배선을 지우고
    //    파일 끝에(= 이 함수 뒤에) 두 헬퍼를 부르는 죽은 함수 하나를 덧붙여도 그 디코이까지 body에
    //    통째로 들어와 expectOrder가 여전히 green이었다 — "첫 등장이 곧 그 자리"라는 전제가 무너진다.
    //    `return (`는 handleDelete 안에서는 안 쓰이고(핸들러는 전부 `return;`) 컴포넌트 본문에서
    //    딱 한 번만 나오므로 안전한 경계다.
    const body = sliceBody(code, 'async function handleDelete', 'return (', 'handleDelete');
    expectOrder(body, ['length === 0', 'getOwnStatus(', /writeRejectionMessage\(\s*status\s*,/], '삭제 경로');
  });

  it('수정 0행(SellForm.handleSubmit)', () => {
    const code = expectStripped(read(SELL_FORM), 'async function handleSubmit', 'SellForm.tsx');
    // 위 handleDelete와 동일한 이유로 null 대신 컴포넌트 JSX `return (`로 경계를 못박는다.
    //    handleSubmit 안의 다른 `return`은 전부 값 없는 `return;`이라 `return (`와 안 겹친다.
    const body = sliceBody(code, 'async function handleSubmit', 'return (', 'handleSubmit');
    expectOrder(body, ['length === 0', 'getOwnStatus(', /writeRejectionMessage\(\s*status\s*,/], '수정 0행 경로');
  });

  it('등록·수정 42501(SellForm.toKoreanError)', () => {
    const code = expectStripped(read(SELL_FORM), 'async function toKoreanError', 'SellForm.tsx');
    const body = sliceBody(code, 'async function toKoreanError', 'async function handleSubmit', 'toKoreanError');
    // 42501은 "소유권 위조"와 "정지"가 합류하는 자리 — 코드를 글자 그대로 박는다.
    expectOrder(body, ["'42501'", 'getOwnStatus(', /writeRejectionMessage\(\s*status\s*,/], '42501 경로');
  });

  it('getOwnStatus 호출은 전부 쓰기 거부 핸들러 본문 안에만 있다(컴포넌트 스코프·useEffect 사전조회 금지)', () => {
    // 왜 필요한가(2026-08-11 3차 코드리뷰 red 프로브 실측): 위 expectOrder 4건은 전부 "핸들러
    // 본문 안"에서만 순서를 본다 — 핸들러 밖(컴포넌트 최상단·useEffect)에 getOwnStatus를 또 하나
    // 심어 status를 미리 읽어 두고, 그 값으로 버튼 자체를 감춰도(`{!suspended && <Button .../>}`)
    // 이 파일의 나머지 검사는 전부 green이었다 — 화면이 진짜 사전 검사 게이트로 바뀌었는데
    // "핸들러 순서"만 보는 검사로는 못 잡는 사각지대다. 그래서 파일 전체의 getOwnStatus( 호출
    // 수와, 위에서 이미 좁혀 본 핸들러 본문들 안의 호출 수를 비교한다 — 다르면 핸들러 밖에도
    // 호출이 있다는 뜻이다.
    const targets = [
      {
        url: LISTING_ACTIONS,
        what: 'ListingActions.tsx',
        bodies: (code: string) => [
          sliceBody(code, 'async function handleComplete', 'async function handleDelete', 'handleComplete'),
          sliceBody(code, 'async function handleDelete', 'return (', 'handleDelete'),
        ],
      },
      {
        url: SELL_FORM,
        what: 'SellForm.tsx',
        bodies: (code: string) => [
          sliceBody(code, 'async function toKoreanError', 'async function handleSubmit', 'toKoreanError'),
          sliceBody(code, 'async function handleSubmit', 'return (', 'handleSubmit'),
        ],
      },
    ] as const;

    for (const { url, what, bodies } of targets) {
      const code = expectStripped(read(url), 'getOwnStatus(', what);
      const totalCount = (code.match(/getOwnStatus\(/g) ?? []).length;
      const inHandlers = bodies(code).reduce(
        (sum, body) => sum + (body.match(/getOwnStatus\(/g) ?? []).length,
        0,
      );
      expect(
        inHandlers,
        `${what}: getOwnStatus( 호출 ${totalCount}건 중 ${inHandlers}건만 쓰기 거부 핸들러 본문 안에 있다 — ` +
          `나머지는 컴포넌트 스코프·useEffect 등에서 미리 조회한다(화면이 사전 검사 게이트가 됐다, 스토리 불변식 위반)`,
      ).toBe(totalCount);
    }
  });

  it('네 경로 모두가 헬퍼를 쓴다 — 한 자리가 다른 세 자리를 대신 통과시키지 못한다', () => {
    // 위 4개는 각 핸들러 본문으로 좁혀 봤다(restoreSoldWiringContract.test.ts의 교훈 — 파일 전체를
    // 보면 한 곳의 배선이 나머지를 대신 통과시킨다). 여기서는 import 자체가 살아 있는지만 본다.
    for (const [url, what] of [
      [LISTING_ACTIONS, 'ListingActions.tsx'],
      [SELL_FORM, 'SellForm.tsx'],
    ] as const) {
      const code = stripComments(read(url));
      expect(
        /import\s*\{[^}]*getOwnStatus[^}]*writeRejectionMessage[^}]*\}\s*from\s*(['"`])@\/lib\/auth\/status\1/.test(
          code,
        ),
        `${what}가 @/lib/auth/status에서 두 헬퍼를 import하지 않는다(단일 조회 경로 원칙이 깨졌다)`,
      ).toBe(true);
    }
  });
});
