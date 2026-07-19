// 대표사진 판별 규칙을 **코드로 못박는 검사** (Story 9.4 AC9 / 대장 #59·#47-4).
//
// 왜 이 검사가 필요한가: `conventions.md §10.1`이 "읽는 쪽은 order by sort_order, id로 읽는다"고
// 적어 뒀지만 **강제하는 것이 아무것도 없었다**(#59). 문서 약속은 아무도 실행하지 않는다(B9).
// 그래서 규칙을 검사로 옮긴다.
//
// **이 검사가 안 보는 것:**
//  · DB 쿼리가 실제로 `.order('sort_order').order('id')`를 거는지 — 그건 서버 컴포넌트 쪽이라
//    여기서 못 본다. 대신 이 함수가 **입력 순서를 믿지 않게** 만들어, 쿼리가 정렬을 빠뜨려도
//    화면 결과는 흔들리지 않게 했다(아래 "뒤섞여 들어와도" 테스트).
//  · 그 경로의 회귀는 Task 5 실브라우저 관찰로만 확인된다(이 리포엔 E2E 설정이 없다).
import { describe, it, expect } from 'vitest';
import { coverImages, type ListingImageRow } from './coverImages';

const row = (o: Partial<ListingImageRow> & { id: string }): ListingImageRow => ({
  listing_id: 'L1',
  storage_path: `path/${o.id}.webp`,
  sort_order: 0,
  ...o,
});

describe('coverImages', () => {
  it('sort_order가 가장 낮은 행이 대표다', () => {
    const map = coverImages([
      row({ id: 'b', sort_order: 2 }),
      row({ id: 'a', sort_order: 0 }),
      row({ id: 'c', sort_order: 1 }),
    ]);
    expect(map.get('L1')).toEqual({ coverPath: 'path/a.webp', count: 3 });
  });

  it('sort_order가 동률이면 id가 낮은 쪽이 대표다 (#59 — 2차 키가 없으면 조회마다 순서가 달라진다)', () => {
    const map = coverImages([
      row({ id: 'zz', sort_order: 0 }),
      row({ id: 'aa', sort_order: 0 }),
    ]);
    expect(map.get('L1')?.coverPath).toBe('path/aa.webp');
  });

  it('is_cover=true가 다른 행에 붙어 있어도 sort_order=0 행이 대표다 (#47-4 — is_cover는 파생 결과)', () => {
    // 시드·레거시 행은 is_cover가 전부 false일 수 있고, 동기화가 중간에 실패하면
    // is_cover가 엉뚱한 행에 남을 수도 있다. 그래서 아예 읽지 않는다 —
    // 타입에 is_cover가 없다는 사실 자체가 이 규칙의 강제 장치다.
    const map = coverImages([
      { listing_id: 'L1', id: 'late', storage_path: 'path/late.webp', sort_order: 3 },
      { listing_id: 'L1', id: 'first', storage_path: 'path/first.webp', sort_order: 0 },
    ]);
    expect(map.get('L1')?.coverPath).toBe('path/first.webp');
  });

  it('행이 뒤섞여 들어와도 결과가 같다 (호출부가 정렬을 빠뜨려도 화면이 흔들리지 않는다)', () => {
    const rows = [
      row({ id: 'c', sort_order: 2 }),
      row({ id: 'a', sort_order: 0 }),
      row({ id: 'b', sort_order: 1 }),
    ];
    const forward = coverImages(rows);
    const reversed = coverImages([...rows].reverse());
    expect(forward.get('L1')).toEqual(reversed.get('L1'));
  });

  it('매물별로 따로 센다 (한 페이지의 여러 매물을 한 번에 처리한다)', () => {
    const map = coverImages([
      { listing_id: 'L1', id: 'a', storage_path: 'p/1a.webp', sort_order: 0 },
      { listing_id: 'L2', id: 'b', storage_path: 'p/2b.webp', sort_order: 1 },
      { listing_id: 'L2', id: 'c', storage_path: 'p/2c.webp', sort_order: 0 },
    ]);
    expect(map.get('L1')).toEqual({ coverPath: 'p/1a.webp', count: 1 });
    expect(map.get('L2')).toEqual({ coverPath: 'p/2c.webp', count: 2 });
  });

  it('사진이 0장인 매물은 Map에 아예 없다 (대표 0장은 정상 상태)', () => {
    const map = coverImages([{ listing_id: 'L1', id: 'a', storage_path: 'p/a.webp', sort_order: 0 }]);
    expect(map.has('L2')).toBe(false);
    expect(map.size).toBe(1);
  });

  it('행이 하나도 없으면 빈 Map이다', () => {
    expect(coverImages([]).size).toBe(0);
  });
});
