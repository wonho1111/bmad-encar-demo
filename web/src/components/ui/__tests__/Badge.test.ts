// Badge 프리미티브 계약 검사 (Story 15.1 코드리뷰 patch, CLAUDE.md B9 —
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다. 안 바꾸면 아무도 실행하지 않는다").
//
// 왜 필요한가 (추측이 아니라 이 스토리에서 실제로 두 번 깨진 규칙이다):
//   ① 톤별 박스 모델 — 처음엔 neutral만 border를 가져 같은 목록 행에서 "판매중"(active)과
//      "판매완료"(neutral)의 높이가 1px 어긋났다. 통일하려고 만든 프리미티브가 정렬을 흔든 것이라
//      전 톤에 border를 깔아 고쳤는데, 그 규칙은 지금 Badge.tsx 주석에만 있다. 톤이 하나 더
//      추가되면서 border를 빠뜨려도 tsc·lint·vitest·e2e가 전부 초록이다.
//   ② shrink-0 whitespace-nowrap — 뱃지는 대부분 justify-between 행의 flex item이라 기본
//      flex-shrink가 걸리면 좁은 폭에서 두 줄로 접힌다. 반응형 무결성 규칙 D5가 금지하는 것인데
//      이것도 주석 계약이었다.
//
// 왜 소스 스캔인가: 이 리포의 web은 jsdom/RTL을 두지 않는다(project-context.md §12 — web은 E2E 우선).
//   같은 리포가 이미 쓰는 기법을 따른다 — messageBubbleWrap.test.ts(클래스 문자열 스캔)·
//   AppHeader.test.ts(호출부 스캔)와 동일한 "소스에 박힌 계약을 정적으로 고정" 방식이다.
//
// 이 검사가 **안 보는 것**(구조적 한계, 추측 아님):
//   · 실제 렌더 결과 — 클래스가 붙어 있다는 것과 320px에서 실제로 안 접힌다는 것은 다르다.
//     관리자 화면의 뷰포트 매트릭스는 아직 없다(대장 DW-697, Story 15.2 소유).
//   · 색 대비 — active 톤의 잉크/배경 비율은 이 파일 밖(빌드 CSS + WCAG 계산)에서 실측했다.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SOURCE = readFileSync(fileURLToPath(new URL('../Badge.tsx', import.meta.url)), 'utf8');

/** TONE_CLASSES 객체 리터럴 본문만 잘라낸다(주석에 적힌 톤 이름이 검사를 흔들지 않게). */
function toneEntries(): [string, string][] {
  const start = SOURCE.indexOf('const TONE_CLASSES');
  expect(start, 'TONE_CLASSES 선언을 찾지 못했습니다').toBeGreaterThan(-1);
  const body = SOURCE.slice(start, SOURCE.indexOf('};', start));
  return [...body.matchAll(/^\s*(\w+):\s*'([^']*)'/gm)].map((m) => [m[1], m[2]]);
}

describe('Badge 프리미티브 — 톤이 늘어도 정렬과 D5 줄바꿈 금지가 유지된다', () => {
  it('톤이 4개 모두 잡힌다(스캔이 헛돌지 않는다)', () => {
    expect(toneEntries().map(([name]) => name).sort()).toEqual([
      'active',
      'danger',
      'highlight',
      'neutral',
    ]);
  });

  it('모든 톤이 border 클래스를 갖는다(톤별 높이 어긋남 금지)', () => {
    for (const [name, cls] of toneEntries()) {
      expect(cls, `톤 "${name}"에 border-* 클래스가 없습니다: ${cls}`).toMatch(/\bborder-[\w/-]+\b/);
    }
  });

  it('공통 클래스에 shrink-0 whitespace-nowrap이 박혀 있다(D5: 좁은 폭에서 두 줄로 접지 않는다)', () => {
    const base = SOURCE.slice(SOURCE.indexOf('<span'));
    expect(base).toMatch(/\bshrink-0\b/);
    expect(base).toMatch(/\bwhitespace-nowrap\b/);
  });
});
