// 관리자 "판매완료 되돌리기" **배선** 계약 검사 (Story 15.4 후속 코드리뷰 patch, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가 (실측한 사각지대):
//   0030이 만든 DB 재료(admin_restore_sold_listing RPC의 권한·멱등·컬럼 불변)는 실DB 테스트
//   (`api/tests/integration/test_restore_sold_listing_rpc_real_db.py`)가 고정한다. 그 파일의 헤더도
//   "web ListingAdminActions.tsx가 이 RPC를 실제로 호출하는지는 **정적 스캔·수동 확인 몫**"이라고
//   명시한다 — 그런데 그 정적 스캔이 없었다.
//   web 쪽 유일한 검증은 `web/e2e/write-flows.spec.ts` E6인데, `.github/workflows/tests.yml`은
//   E2E를 배선하지 않는다(그 파일 헤더가 직접 그렇게 적고 있다 — 로컬 `npm run test:e2e` 전용).
//   그래서 아래 중 무엇을 깨뜨려도 CI 4개 잡(api·api-db·web·app)이 전부 green이었다:
//     ① RPC 이름 문자열 오타/삭제 → 버튼이 조용히 아무 일도 안 함
//     ② 명명 인자 키 `p_listing_id` 변경 → PostgREST가 함수를 못 찾음
//     ③ isSold 게이트 반전/삭제 → on_sale 매물에도 되돌리기 버튼 노출
//     ④ 두 페이지가 `status` prop 전달을 빠뜨림 → 버튼이 영영 안 뜸(tsc는 잡지만, select 문자열에서
//        `status`를 빼는 쪽은 `.returns<T>()`/`.maybeSingle<T>()`가 검증 없는 캐스트라 안 잡힌다)
//     ⑤ `disabled={busy}` 공유 가드 되돌리기 → 삭제·되돌리기 동시 실행 레이스 복구
//     ⑥ 0행 거부 분기 삭제 → RPC가 막아도 화면은 성공처럼 보임 (3차 코드리뷰 추가)
//     ⑦ 성공 후 router.refresh() 삭제 → 되돌려도 행이 계속 "판매완료"로 남음 (3차 코드리뷰 추가)
//   ⑥·⑦은 3차 코드리뷰가 **실제로 지워서** 확인했다 — 지운 채로 vitest·lint·tsc가 전부 green이었다.
//
// 왜 소스 스캔인가: 이 리포의 web은 컴포넌트를 렌더하는 단위테스트를 두지 않는다
//   (project-context.md §12 — web은 E2E 우선, @testing-library 미도입). 대신 같은 리포가 이미 쓰는
//   기법을 따른다 — `viewCountCallSite.test.ts`(0020 RPC 호출부)·`unreadWiringContract.test.ts`와
//   동일한 "소스에 박힌 계약을 정적으로 고정" 방식이다.
//
// 이 검사가 **안 보는 것**(추측이 아니라 구조적 한계):
//   · 버튼을 눌렀을 때 런타임에 RPC가 실제로 성공/거부되는지 — 그건 실DB 테스트(권한·멱등 축)와
//     E2E E6(왕복 축)의 몫이다. 여기서는 "코드가 그 호출을 갖고 있는가"만 본다.
//   · 0행일 때 화면에 뜨는 한국어 오류 **문구가 실제로 렌더되는지** — 분기의 *존재*는 위 ⑥이
//     고정하지만, 그 문구가 브라우저에 그려지는지는 렌더 테스트가 없어 미검증이다
//     (비관리자는 (admin)/layout.tsx의 requireRole 게이트에 막혀 이 분기에 도달할 수 없고,
//      도달 경로는 화면이 낡은 세션뿐이라 E2E로도 재현 비용이 크다).
//   · 상세 화면에서 되돌리기를 눌렀을 때의 동선(refresh vs redirect) — E6이 상세에서 버튼 **존재**만
//     확인하고 클릭은 목록에서 한다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const ACTIONS = new URL('../ListingAdminActions.tsx', import.meta.url);
const LIST_PAGE = new URL('../page.tsx', import.meta.url);
const DETAIL_PAGE = new URL('../[id]/page.tsx', import.meta.url);

const RPC_NAME = 'admin_restore_sold_listing';

function read(url: URL): string {
  return readFileSync(fileURLToPath(url), 'utf8');
}

/**
 * 주석(줄·블록)을 지운다 — 계약은 실행되는 코드에만 있고, 주석에 적힌 설명이 검사를 통과시키면 안 된다.
 *
 * ⚠️ 이 정규식은 문자열·템플릿·정규식 리터럴을 구분하지 못한다(3차 코드리뷰 지적). 리터럴 안에
 * `//`(예: URL)가 들어오면 그 줄의 나머지가, `/*`가 들어오면 다음 `*\/`까지가 통째로 지워져 아래
 * 단언들이 **엉뚱한 이유로** red가 되거나(있는 코드를 못 봄) green이 될 수 있다. 지금 세 파일엔
 * 그런 리터럴이 없지만(실측), 전제가 깨지는 순간을 조용히 넘기지 않도록 호출부에서 `expectStripped`로
 * 앵커가 살아남았는지 확인한다.
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

describe('관리자 판매완료 되돌리기 배선 계약 (DW-391 / Story 15.4)', () => {
  it('handleRestore가 RPC 호출 → 0행이면 한국어 오류 → 성공 시 router.refresh()를 모두 갖는다', () => {
    const code = expectStripped(read(ACTIONS), 'supabase.rpc(', 'ListingAdminActions');

    // ⚠️ 단언 범위를 handleRestore **본문으로 좁힌다**(3차 코드리뷰). 파일 전체를 보면
    //    handleDelete의 router.refresh()·0행 분기가 되돌리기 쪽 검사를 대신 통과시킨다.
    const restoreBody = code.slice(
      code.indexOf('async function handleRestore'),
      code.indexOf('async function handleDelete'),
    );
    expect(restoreBody.length, 'handleRestore/handleDelete 함수 경계를 못 찾았다').toBeGreaterThan(0);

    // ① 살아 있는 RPC 호출인가 — 이름이 어딘가 문자열로 있는 것과 다르다(viewCountCallSite.test.ts의 교훈).
    const callPattern = new RegExp(`supabase\\.rpc\\(\\s*(['"\`])${RPC_NAME}\\1`);
    expect(
      callPattern.test(restoreBody),
      `${RPC_NAME} 호출이 사라졌다(버튼이 조용히 무동작이 된다)`,
    ).toBe(true);

    // ② 명명 인자 키 — PostgREST는 명명 인자로 함수를 찾으므로 키가 틀리면 함수 자체를 못 찾는다.
    //    (200자 윈도우 대신 호출부터 인자 객체 닫힘까지를 통째로 매치한다 — 줄바꿈·포맷에 안 흔들린다.)
    expect(
      new RegExp(`supabase\\.rpc\\(\\s*(['"\`])${RPC_NAME}\\1\\s*,\\s*\\{[^}]*p_listing_id`).test(
        restoreBody,
      ),
      'p_listing_id 명명 인자가 RPC 인자 객체에 없다(PostgREST가 함수를 못 찾는다)',
    ).toBe(true);

    // ③ 0행 거부 분기 — RPC는 막혀도 에러가 아니라 0행으로 온다(0030 설계). 이 분기가 사라지면
    //    거부가 **성공처럼** 보인다. E2E(E6)가 유일한 커버였는데 E2E는 CI에 배선돼 있지 않다.
    expect(
      /\.length\s*===\s*0/.test(restoreBody) && /setError\(/.test(restoreBody),
      '0행일 때 오류를 세우는 분기가 사라졌다(거부가 성공처럼 보인다)',
    ).toBe(true);

    // ④ 성공 시 화면 갱신 — 없으면 되돌린 뒤에도 행이 계속 "판매완료"로 남는다(AC1·AC6).
    expect(
      /router\.refresh\(\)/.test(restoreBody),
      '성공 후 router.refresh()가 없다(되돌려도 화면이 그대로다)',
    ).toBe(true);
  });

  it('되돌리기 버튼은 sold 매물에만 렌더된다(LISTING_STATUS.SOLD 게이트)', () => {
    const code = expectStripped(read(ACTIONS), '판매완료 되돌리기', 'ListingAdminActions');

    // 게이트 자체 — status를 SOLD와 비교해 isSold를 만든다.
    expect(/const\s+isSold\s*=\s*status\s*===\s*LISTING_STATUS\.SOLD/.test(code)).toBe(true);

    // ⚠️ 게이트가 버튼을 **감싸는지**를 본다(3차 코드리뷰 실측). 전에는 두 문자열의 등장 순서만
    //    비교해서(labelIndex > gateIndex), 버튼을 `{isSold && (...)}` 밖으로 빼내도 앞쪽에
    //    `{isSold && (`가 남아 있으면 그대로 통과했다 — 실제로 버튼을 게이트 밖으로 옮기고
    //    돌렸더니 4건 전부 green이었다. 게이트 직후에 `<Button`이 열리고 그 안에 라벨이
    //    오는 형태로 고정한다.
    expect(
      /\{isSold && \(\s*<Button[\s\S]{0,600}?판매완료 되돌리기/.test(code),
      'isSold 게이트가 되돌리기 버튼을 감싸지 않는다(on_sale 매물에도 버튼이 뜬다)',
    ).toBe(true);
  });

  it('삭제·되돌리기 두 버튼이 공유 busy 가드를 쓴다(같은 행 동시 실행 차단)', () => {
    const code = expectStripped(read(ACTIONS), 'disabled={busy}', 'ListingAdminActions');

    expect(/const\s+busy\s*=\s*deleting\s*\|\|\s*restoring/.test(code)).toBe(true);

    // ⚠️ 개수를 2로 못박지 않는다(3차 코드리뷰). `.toBe(2)`는 방향이 반대였다 — 세 번째 액션이
    //    busy를 **쓰면** red(3≠2)가 되고, **안 쓰면** green(2)이라 정작 잡아야 할 쪽을 놓쳤다.
    //    불변식으로 바꾼다: onClick 핸들러를 가진 버튼 수 == disabled={busy}를 가진 버튼 수.
    const clickable = (code.match(/onClick=\{handle\w+\}/g) ?? []).length;
    const guarded = (code.match(/disabled=\{busy\}/g) ?? []).length;
    expect(clickable, '핸들러를 가진 버튼을 못 찾았다').toBeGreaterThanOrEqual(2);
    expect(guarded, `버튼 ${clickable}개 중 ${guarded}개만 공유 busy 가드를 쓴다`).toBe(clickable);

    // 각 핸들러의 조기 리턴도 양쪽 상태를 함께 본다(가드는 disabled와 핸들러 양쪽에 있어야 한다).
    expect((code.match(/if\s*\(deleting\s*\|\|\s*restoring\)\s*return/g) ?? []).length).toBe(
      clickable,
    );
  });

  it('목록·상세 두 화면이 status를 조회해 ListingAdminActions에 넘긴다', () => {
    for (const [name, url] of [
      ['목록', LIST_PAGE],
      ['상세', DETAIL_PAGE],
    ] as const) {
      const code = expectStripped(read(url), ".from('listings')", `${name} 화면`);

      // ① select 문자열에 status가 있는가 — `.returns<T>()`/`.maybeSingle<T>()`는 검증 없는 캐스트라
      //    여기서 status를 빼도 tsc가 통과한다(런타임에 undefined → 버튼이 영영 안 뜬다).
      //
      // ⚠️ 두 군데를 좁혔다(3차 코드리뷰):
      //   (a) `.from('listings')`에 **앵커**한다 — 전에는 파일의 첫 `.select(`를 봤기 때문에,
      //       매물 쿼리 앞에 다른 쿼리(예: 커버 이미지 조회)가 생기면 엉뚱한 select를 검사했다.
      //   (b) 부분문자열이 아니라 **컬럼 토큰**으로 비교한다 — `toContain('status')`는
      //       `accident_status`(ListingCard 계약 필드) 같은 이름만 들어와도 통과해, 정작
      //       `status` 컬럼이 빠져도 fail-open이었다.
      const selectMatch = code.match(
        /\.from\(\s*(['"`])listings\1\s*\)[\s\S]{0,400}?\.select\(\s*(['"`])([\s\S]*?)\2/,
      );
      expect(selectMatch, `${name} 화면에서 listings의 .select(...)를 못 찾았다`).not.toBeNull();
      const columns = selectMatch![3].split(',').map((c) => c.trim());
      expect(columns, `${name} 화면의 listings select에 status 컬럼이 없다`).toContain('status');

      // ② 그 값을 컴포넌트에 실제로 넘기는가.
      const usageIndex = code.indexOf('<ListingAdminActions');
      expect(usageIndex, `${name} 화면이 ListingAdminActions를 렌더하지 않는다`).toBeGreaterThanOrEqual(
        0,
      );
      expect(
        code.slice(usageIndex, usageIndex + 400),
        `${name} 화면이 status prop을 넘기지 않는다`,
      ).toMatch(/status=\{/);
    }
  });
});
