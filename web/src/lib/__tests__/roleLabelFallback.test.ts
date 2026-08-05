// ROLE_LABEL 인덱싱 폴백 강제 검사 (Story 14.1 3차 리뷰, CLAUDE.md B9 —
// "주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 이 검사가 생겼나:
//   `ROLE_LABEL`은 `Record<UserRole, string>`(전사상 맵)으로 선언돼 있고, 그 타입을 **참으로
//   만들어주던 것**이 `profiles.role`의 3값 CHECK였다. Story 14.1의 0027이 그 CHECK를 걷어내면서
//   DB는 더 이상 role의 어휘를 강제하지 않는다 — 즉 `ROLE_LABEL[누군가의_role]`은 이제
//   `undefined`가 될 수 있는데, 타입은 여전히 `string`이라고 말한다(런타임 구멍).
//   실제로 2차 리뷰에서 관리자 회원관리 화면 한 곳만 폴백이 없어 라벨이 빈칸이 되고 정지·삭제
//   확인 문구가 "undefined ○○ 회원"이 되는 경로가 발견됐다. 그건 **그 한 곳을 고쳐서** 닫혔지만,
//   다음 화면이 폴백 없이 인덱싱하는 것을 막는 것은 아무것도 없었다(주석 한 줄이 전부였다).
//   Story 14.2가 새 기본 role 값을 도입하면 그 순간부터 실제로 터진다.
//
// 무엇을 단언하나:
//   web/src의 모든 `ROLE_LABEL[...]` 인덱싱은 둘 중 하나여야 한다 —
//     (a) 키가 `USER_ROLE.*` 상수다 → 맵에 반드시 있는 키라 폴백이 필요 없다(레이아웃 2곳).
//     (b) 그 외(런타임 값으로 인덱싱) → 바로 뒤에 `??` 폴백이 붙어 있어야 한다.
//
// 이 검사가 **안 보는 것**(추측 아니라 실측):
//   · 폴백 **값**이 사람이 읽을 만한지는 안 본다. 현재 형제 화면들의 폴백은 `?? profile.role`
//     (원본 문자열 노출)이고, role이 `' '` 같은 공백이면 라벨은 여전히 빈칸으로 보인다.
//     그건 DB가 그런 값을 허용한다는 별개 사실의 결과이고, 이 검사의 관심은 `undefined`가
//     화면에 나가지 않는 것까지다.
//   · `ROLE_LABEL`을 다른 이름으로 재바인딩해(`const L = ROLE_LABEL; L[x]`) 우회하는 경우 —
//     이 리포에 그런 선례가 없고, 있다면 그 자체가 더 큰 스멜이라 범위 밖으로 둔다.
//   · web/src 밖(Flutter 앱)의 역할 라벨 — 거긴 enum 파싱 경로가 아예 달라 별개다
//     (app/lib/features/auth/user_role.dart 주석 참고).
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC_ROOT = fileURLToPath(new URL('../../', import.meta.url));

// `ROLE_LABEL[<키>]` 한 건과, 그 뒤에 `??`가 붙었는지를 함께 잡는다.
// 키에 `]`가 없다는 가정은 이 리포의 모든 사용처에서 성립한다(중첩 인덱싱 없음).
const INDEXING = /ROLE_LABEL\[([^\]]*)\]\s*(\?\?)?/g;

function collectSourceFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry === '.next' || entry === '__tests__') continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...collectSourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.tsx?$/.test(entry)) {
      files.push(full);
    }
  }
  return files;
}

type Site = { file: string; key: string; hasFallback: boolean };

function collectSites(): Site[] {
  const sites: Site[] = [];
  for (const file of collectSourceFiles(SRC_ROOT)) {
    const content = readFileSync(file, 'utf-8');
    for (const match of content.matchAll(INDEXING)) {
      sites.push({
        file: relative(SRC_ROOT, file),
        key: match[1].trim(),
        hasFallback: match[2] !== undefined,
      });
    }
  }
  return sites;
}

describe('ROLE_LABEL 인덱싱은 폴백 없이는 못 쓴다', () => {
  it('런타임 값으로 인덱싱하는 모든 곳에 `??` 폴백이 있다', () => {
    // 0027(Story 14.1) 이후 DB가 role 어휘를 강제하지 않으므로, 맵에 없는 키가 들어올 수 있다.
    const unguarded = collectSites()
      .filter((s) => !s.key.startsWith('USER_ROLE.'))
      .filter((s) => !s.hasFallback);

    expect(unguarded).toEqual([]);
  });

  it('폴백 없이 인덱싱해도 되는 곳은 USER_ROLE 상수 키뿐이다', () => {
    // 상수 키는 맵에 반드시 존재하므로 안전하다. 다만 "어디가 상수 키인지"를 여기 고정해 두면,
    // 새로 늘어날 때 이 테스트가 먼저 눈에 걸린다(조용히 늘어나는 것을 막는다).
    const constantKeySites = collectSites()
      .filter((s) => s.key.startsWith('USER_ROLE.'))
      .map((s) => `${s.file}: ROLE_LABEL[${s.key}]`)
      .sort();

    expect(constantKeySites).toEqual([
      'app/(admin)/layout.tsx: ROLE_LABEL[USER_ROLE.ADMIN]',
      'app/(user)/sell/layout.tsx: ROLE_LABEL[USER_ROLE.SELLER]',
    ]);
  });

  it('검사 대상이 실제로 존재한다 (정규식이 아무것도 못 찾는 상태를 통과로 오인하지 않는다)', () => {
    // 이 파일이 조용히 무력화되는 가장 흔한 방식은 "매치가 0건인데 전부 통과"다.
    expect(collectSites().length).toBeGreaterThanOrEqual(9);
  });
});
