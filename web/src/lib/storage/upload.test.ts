// deleteListingImageObject 회귀 테스트 (코드리뷰 2026-07-19 2차).
//
// 왜 이 파일이 생겼나: 이 함수의 반환값 하나가 "매물을 지울 수 있는가"를 결정하는데, 그 의미가
// **원격 실측으로만 정해진다.** 실측 결과를 주석에만 적으면 다음 사람이 "빈 배열 = 실패겠지"로
// 되돌리고 매물이 영영 안 지워진다(실제로 그렇게 돼 있었다). 여기서 실행되는 검사로 고정한다.
//
// ── 근거가 된 원격 실측 (2026-07-19, psrnsasxpkpwqdukjdmt, 임시 판매자 계정) ──
//   A. 행 없음 + 파일 없음 → remove() error=null, data=[]   ← RLS에 가려진 경우
//   B. 행 있음 + 파일 없음 → remove() error=null, data=[]   ← 파일이 진짜 없는 경우
//   C. 행 있음 + 파일 있음 → remove() error=null, data=[그 경로]  ← 정상 삭제
//   → A와 B의 응답이 **글자 그대로 같다.** 응답만으로는 구별할 수 없다.
//   → 그러나 C가 "행이 있으면 파일이 있을 때 실제로 지워진다"를 증명하므로,
//     **행이 있는 상태에서 빈 배열이면 파일은 진짜 없다.**
//
// ⚠️ 이 검사가 **안 보는 것**: 실제 RLS 동작. 여기서는 Storage 경계를 가짜로 바꾸고 우리 코드가
//    응답을 **어떻게 해석하는지**만 본다. 위 A/B/C 자체는 원격 실측의 몫이고, 재보고 싶으면
//    같은 스크립트를 다시 돌려야 한다(결과는 docs/conventions.md §10.1에 기록).
import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  /** remove()가 돌려줄 것: 지워진 경로 목록, 또는 에러. */
  removeResult: { data: [] as { name: string }[] | null, error: null as { message: string } | null },
  calls: [] as string[][],
}));

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    storage: {
      from: () => ({
        remove: async (paths: string[]) => {
          h.calls.push(paths);
          return h.removeResult;
        },
      }),
    },
  }),
}));

const { deleteListingImageObject } = await import('./upload');

beforeEach(() => {
  h.calls.length = 0;
  h.removeResult = { data: [], error: null };
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('deleteListingImageObject — 반환값의 뜻은 "오브젝트가 이제 없다"', () => {
  it('실제로 지워지면 true (케이스 C)', async () => {
    h.removeResult = { data: [{ name: 'u1/l1/a.webp' }], error: null };
    expect(await deleteListingImageObject('u1/l1/a.webp')).toBe(true);
    expect(h.calls).toEqual([['u1/l1/a.webp']]);
  });

  it('🔴 매치 0건이면 true — 파일이 이미 없다는 뜻이고, 목적은 달성됐다 (케이스 B)', async () => {
    // 전엔 이걸 false(실패)로 돌려줬다. 그 결과 파일 없는 고아 행이 하나라도 있으면
    // 매물 삭제가 **재시도해도 결정론적으로** 막혔다 — 앱 안에 탈출구가 없었다.
    // ⚠️ 이 해석은 **행이 살아 있는 동안 호출한다**는 전제에서만 참이다(아래 계약 검사 참조).
    h.removeResult = { data: [], error: null };
    expect(await deleteListingImageObject('u1/l1/ghost.webp')).toBe(true);
  });

  it('에러면 false — 이때만 진짜 실패다', async () => {
    h.removeResult = { data: null, error: { message: 'network' } };
    expect(await deleteListingImageObject('u1/l1/a.webp')).toBe(false);
  });

  it('null 응답도 false로 본다 (모르는 상태를 성공으로 갈음하지 않는다)', async () => {
    h.removeResult = { data: null, error: null };
    expect(await deleteListingImageObject('u1/l1/a.webp')).toBe(false);
  });
});
