// increment_listing_view 호출 지점 단일성 검사(Story 11.1, CLAUDE.md B9 —
// "주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 0020_listings_view_count.sql·page.tsx 주석이 "호출 지점을 상세 페이지 서버 컴포넌트 한 곳으로
// 한정하는 것이 유일한 안전장치(카드 렌더 경로는 호출하지 않음)"라고 선언하지만, 그 불변식은
// 지금까지 주석에만 있었다.
//
// 2차 코드리뷰(2026-07-28) 실측 지적: `.rpc\(\s*['"]이름['"]` 형태의 "호출 모양" 정규식은
// (a) 백틱 리터럴(`` supabase.rpc(`increment_listing_view`, ...) ``)과
// (b) `const FN = 'increment_listing_view'; supabase.rpc(FN, ...)` 같은 상수 경유
// 둘 다 통과시킨다(리뷰 실측). 그래서 이 검사는 "호출 모양"이 아니라 **함수명 문자열 자체**
// (따옴표 종류 무관 — '/"/`)를 찾는다 — 이름이 어디에 어떤 형태로 나타나든 잡힌다.
// 대신 "따옴표로 감싼 정확한 이름"만 찾으므로, 이 이름을 따옴표 없이 언급하는 일반 주석(이
// 파일·page.tsx의 설명 문장처럼)은 걸리지 않는다.
//
// 추가로 단언하는 것(2차 리뷰 지적 — 인자 키·위치를 아무도 고정하지 않았다):
//   · 그 호출이 `p_listing_id` 키를 쓰는가(프로덕션 PostgREST 명명 인자 계약과 일치해야 한다).
//   · 그 호출이 `if (!listing)` 가드보다 **뒤**에 있는가(매물 확인 전에 호출하면 sold·존재하지
//     않는 매물 id로도 RPC가 발화할 수 있다).
//   · P3(코드리뷰 2026-07-28 재지적) — 위 두 단언은 "이름이 어딘가 문자열로 등장한다"만
//     본다. page.tsx의 `await supabase.rpc('increment_listing_view', ...)` 호출 전체를
//     `//`로 주석 처리해도 이름 등장 횟수(1)·p_listing_id 위치·가드 뒤 위치 세 단언이
//     전부 그대로 통과함이 리뷰에서 실측됐다 — 즉 "실행되는 검사로 고정한다"는 이 파일의
//     목적 자체가 거짓이었다. 그래서 `await supabase.rpc('increment_listing_view'` 형태의
//     매치가 같은 줄에서 `//`보다 앞에 있는지(=주석이 아닌 실제 코드인지)를 추가로 확인한다.
//
// 이 검사가 **안 보는 것**:
//   · 런타임에 실제로 몇 번 호출되는지(정적 소스 스캔이지 실행 추적이 아니다) — 그건
//     `api/tests/integration/test_view_count_rpc_real_db.py`와 수동 확인의 몫이다.
//   · `web/src` 밖(Flutter 앱 등)의 클라이언트 — 대장 #136에 이미 등재된 별개 gap이다.
//   · 이름을 문자열 리터럴이 아니라 동적으로 조립(예: 문자열 연결)하는 경우 — 이 리포에 그런
//     패턴이 없고, 있다면 그 자체가 훨씬 더 큰 스멜이라 범위 밖으로 둔다.
//   · `/* ... */` 블록 주석이나 여러 줄에 걸친 주석으로 호출을 숨기는 경우 — 아래 새 검사는
//     한 줄 안의 `//`만 본다. 이 리포에 `.rpc(` 호출을 블록 주석으로 숨긴 선례가 없어 범위 밖.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC_ROOT = fileURLToPath(new URL('../../../../../', import.meta.url));
const DETAIL_PAGE = join(SRC_ROOT, 'app/(user)/listings/[id]/page.tsx');

const FN_NAME = 'increment_listing_view';
// 따옴표(', ", `) 어느 쪽으로 감싸도 잡는다 — 호출 모양이 아니라 이름 자체를 찾는다.
const QUOTED_NAME = new RegExp(`(['"\`])${FN_NAME}\\1`, 'g');

function collectSourceFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === '.next' || entry === '__tests__') continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...collectSourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !entry.endsWith('.test.ts') && !entry.endsWith('.test.tsx')) {
      files.push(full);
    }
  }
  return files;
}

describe('increment_listing_view 호출 지점 단일성', () => {
  it('web/src 전체에서 정확히 1개 파일, 1곳에서만 이름이 등장한다', () => {
    const matches = collectSourceFiles(SRC_ROOT)
      .map((file) => ({
        file,
        occurrences: (readFileSync(file, 'utf-8').match(QUOTED_NAME) ?? []).length,
      }))
      .filter(({ occurrences }) => occurrences > 0);

    expect(matches.map((m) => m.file)).toEqual([DETAIL_PAGE]);
    expect(matches[0]?.occurrences).toBe(1);
  });

  it('그 호출은 p_listing_id 키를 쓰고, 매물 not-found 가드(if (!listing)) 뒤에 있다', () => {
    const content = readFileSync(DETAIL_PAGE, 'utf-8');

    const guardIndex = content.indexOf('if (!listing)');
    const nameMatch = QUOTED_NAME.exec(content);
    QUOTED_NAME.lastIndex = 0; // exec()는 전역 플래그 정규식에 상태를 남긴다 — 다음 테스트 오염 방지.

    expect(guardIndex).toBeGreaterThanOrEqual(0);
    expect(nameMatch).not.toBeNull();
    const nameIndex = nameMatch!.index;
    expect(nameIndex).toBeGreaterThan(guardIndex);

    // 호출 인자 키 검사 — 이름이 나온 지점 바로 뒤 구간(옵션 객체가 오는 자리)에 p_listing_id가 있는가.
    const callWindow = content.slice(nameIndex, nameIndex + 200);
    expect(callWindow).toContain('p_listing_id');
  });

  it('그 등장은 주석이 아니라 살아 있는 호출 코드다', () => {
    // P3(코드리뷰 2026-07-28) — 위 두 테스트는 이름의 "등장"만 보므로, 호출 전체를 `//`로
    // 주석 처리해도 둘 다 통과한다(리뷰 실측). `await supabase.rpc('increment_listing_view'`
    // 형태(따옴표 3종 허용, 공백 유연)로 매치하되, 그 매치가 같은 줄의 `//`보다 뒤에 있으면
    // 그 줄 전체가 주석이라는 뜻이므로 실패시킨다.
    const CALL_PATTERN = /await\s+supabase\.rpc\(\s*(['"`])increment_listing_view\1/;
    const content = readFileSync(DETAIL_PAGE, 'utf-8');
    const lines = content.split('\n');
    const callLineIndex = lines.findIndex((line) => CALL_PATTERN.test(line));

    expect(callLineIndex).toBeGreaterThanOrEqual(0);

    const line = lines[callLineIndex];
    const match = CALL_PATTERN.exec(line);
    const commentIndex = line.indexOf('//');

    expect(match).not.toBeNull();
    expect(commentIndex === -1 || commentIndex > match!.index).toBe(true);
  });
});
