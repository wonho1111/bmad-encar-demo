// 폰트 CDN 재유입·자산 비대 회귀 가드 (#127) — Story 11-0이 세운 "폰트는 외부 CDN에서 받지 않는다"
// 규칙이 지금까지 주석·대장에만 있고 실행되는 검사가 없었다(CLAUDE.md B9 — 규칙은 어길 수 없는
// 자리에 박는다). 브라우저가 필요 없는 정적 검사라 vitest 유닛테스트로 만든다(대장 원문이 "vitest
// 한 건"이라 명시, web/src/app/layout.tsx 소스 문자열 + web/src/app/fonts/ 총 용량만 본다).
import { readFileSync, readdirSync, lstatSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const LAYOUT_FILE = fileURLToPath(new URL('./layout.tsx', import.meta.url));
const FONTS_DIR = fileURLToPath(new URL('./fonts/', import.meta.url));

// 회귀 감지용 상한 — 제품 요구가 아니라 내부 가드 임계값(스토리 확정, Design Notes 참조).
// 현재 실측 2,057,688B(PretendardVariable.woff2) + LICENSE.txt 4,419B ≈ 2,062,107B에
// 약 250KB 버퍼를 더해 2,300,000B로 고정한다.
const FONT_BUDGET_BYTES = 2_300_000;

// 알려진 폰트 CDN 오리진 문자열 — 특정 호스트명 블랙리스트라 "모르는 CDN"은 못 잡는다는 한계가
// 있다(코드리뷰 지적). 그래서 아래 화이트리스트형 검사(자리표시자 정확한 import 출처 + 임의
// 외부 http(s) origin을 가리키는 <link rel="stylesheet"> 전면 금지)를 주된 방어선으로 삼고,
// 이 블랙리스트는 흔한 사례를 빨리 잡는 보조 신호로만 남긴다.
const KNOWN_FONT_CDN_ORIGINS = [
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdn.jsdelivr.net',
  'fastly.jsdelivr.net',
  'unpkg.com',
];

// 재귀적으로 순회한다(코드리뷰 patch) — 이전엔 `readdirSync`+`statSync` 한 겹이라 하위 폴더
// 자체는 inode 크기(~4096B)로만 잡히고, 그 안의 실제 파일 바이트는 세지 않았다. 그러면
// `fonts/<subdir>/Huge.woff2`처럼 서브디렉터리에 큰 폰트를 넣는 것만으로 예산(FONT_BUDGET_BYTES)을
// 완전히 우회할 수 있었다 — 이 파일이 막으려는 바로 그 "자산 비대"를 막지 못하는 구멍이었다.
function fontsDirTotalBytes(dir: string = FONTS_DIR): number {
  let total = 0;
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    // lstatSync + 심볼릭 링크는 건너뛴다(코드리뷰 patch, P9) — statSync는 심볼릭 링크를 따라가므로,
    // 링크된 디렉터리가 순환 구조면 무한 재귀(스택 오버플로)가 나고, 링크된 파일은 원본 바이트를
    // 그대로 세어 이 예산 검사를 심볼릭 링크 하나로 완전히 우회할 수 있었다.
    const stat = lstatSync(full);
    if (stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) {
      total += fontsDirTotalBytes(full);
    } else if (stat.isFile()) {
      total += stat.size;
    }
  }
  return total;
}

/**
 * `<link>` 태그 중 "외부 http(s) origin을 가리키는 stylesheet"가 하나라도 있는지 확인한다
 * (코드리뷰 patch — 화이트리스트형 구조 검사). 태그 전체를 먼저 뽑아 `rel`·`href` 속성을
 * **순서 무관**하게 찾는다: 기존 `/<link\s+rel=.../`는 `rel`이 `<link` 바로 뒤에 와야만 매칭돼
 * `<link href="..." rel="stylesheet">`(속성 순서만 다른 동치 마크업)를 놓쳤다.
 */
function hasExternalStylesheetLink(source: string): boolean {
  const linkTags = source.match(/<link\b[^>]*>/g) ?? [];
  return linkTags.some(
    (tag) => /rel=["']stylesheet["']/.test(tag) && /href=["']https?:\/\//.test(tag),
  );
}

/**
 * `rel="stylesheet"` 링크의 `href`가 JSX 표현식(`href={...}`)인 경우를 잡는다(코드리뷰 patch, P8) —
 * `hasExternalStylesheetLink`는 `href="http..."`처럼 **문자열 리터럴**만 본다. `href={CDN_URL}`
 * 같은 표현식은 값이 변수·환경변수 등 무엇이든 될 수 있어 이 파일이 소스만 읽고 정적으로
 * "외부 오리진이 아니다"를 증명할 수 없다 — 증명할 수 없는 값은 안전하다고 통과시키지 않고
 * 그 자체로 실패시킨다(화이트리스트형 방어: 모르면 통과가 아니라 실패).
 */
function hasStylesheetLinkWithExpressionHref(source: string): boolean {
  const linkTags = source.match(/<link\b[^>]*>/g) ?? [];
  return linkTags.some((tag) => /rel=["']stylesheet["']/.test(tag) && /href=\{/.test(tag));
}

describe('fonts.budget — #127 폰트 CDN 재유입·자산 비대 가드', () => {
  it('layout.tsx에 외부 폰트 CDN 오리진 문자열이 없다(재유입 방지)', () => {
    const source = readFileSync(LAYOUT_FILE, 'utf-8');
    for (const origin of KNOWN_FONT_CDN_ORIGINS) {
      expect(source, `${origin} 문자열이 layout.tsx에 있으면 안 됨(CDN 재유입)`).not.toContain(origin);
    }
    // 화이트리스트형 핵심 단언 — "알려진 호스트명"이 아니라 **임의의 외부 http(s) origin을
    // 가리키는 stylesheet link 자체**를 전면 금지한다(속성 순서 무관, 위 hasExternalStylesheetLink).
    expect(
      hasExternalStylesheetLink(source),
      '외부 http(s) origin을 가리키는 <link rel="stylesheet">가 있으면 안 됨(순서·호스트명 무관)',
    ).toBe(false);
    expect(
      hasStylesheetLinkWithExpressionHref(source),
      '<link rel="stylesheet" href={...}>처럼 href가 JSX 표현식이면 안 됨 — 표현식 값은 정적으로 어느 오리진을 가리키는지 알 수 없어(CDN_URL 같은 변수일 수 있음) "외부 CDN 아님"을 이 가드가 증명하지 못함',
    ).toBe(false);
    // next/font/local을 여전히 쓰고 있는지(자산 self-host 방식 자체가 유지되는지) + next/font/google로
    // 슬쩍 바뀌지 않았는지(그러면 Pretendard처럼 Google Fonts에 없는 폰트는 빌드가 깨지지만, 다른
    // 폰트로 교체되며 이 축이 조용히 뒤집힐 수 있다)도 함께 고정한다.
    // 따옴표 리터럴로 고정하지 않는다(코드리뷰 patch, P8) — layout.tsx가 이 레포에서 유일하게
    // 큰따옴표 import를 쓰는 파일이라, 포매터가 작은따옴표로 통일하는 순간(폰트 자체는 안 바뀌어도)
    // 이 단언이 이유 없이 red가 됐다. 아래 부정 단언과 같은 방식으로 따옴표 무관 정규식을 쓴다.
    expect(source).toMatch(/from\s+["']next\/font\/local["']/);
    // 실제 import 문만 본다(문자열 포함이 아니라) — 이 파일 헤더 주석이 설명 목적으로
    // "next/font/google 불가"라고 정당하게 언급하므로, 단순 toContain은 그 주석에 오탐한다.
    expect(source, 'next/font/google로 바뀌면 안 됨(self-host 원칙 이탈)').not.toMatch(
      /from\s+["']next\/font\/google["']/,
    );
  });

  it(`web/src/app/fonts/ 총 용량이 ${FONT_BUDGET_BYTES.toLocaleString('ko-KR')}B 이하다(회귀 버퍼 포함)`, () => {
    const total = fontsDirTotalBytes();
    expect(total, `fonts/ 총 용량(${total}B)이 상한(${FONT_BUDGET_BYTES}B)을 넘음`).toBeLessThanOrEqual(FONT_BUDGET_BYTES);
  });
});
