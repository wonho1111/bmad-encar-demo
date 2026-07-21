// 갤러리 **순서**를 코드로 못박는 검사 (Story 9.5 AC3 / 대장 #59 — 9.4가 남긴 절반).
//
// 왜 이 검사가 또 필요한가: 9.4는 목록 카드의 **대표 1장**만 고정했다(`coverImages.test.ts`).
// 상세 갤러리는 **전 장의 순서**가 화면에 그대로 나오므로, 2차 정렬 키 `id`가 빠지면
// "새로고침할 때마다 사진 순서가 바뀌는" 증상이 목록보다 훨씬 눈에 띄게 난다(#47-2 —
// `sort_order` 동률을 막는 DB 제약이 일부러 없다).
//
// **이 검사가 안 보는 것(추측이 아니라 실측 기준):**
//  · DB 쿼리(`fetchListingGalleryUrls`)가 실제로 `.order('sort_order').order('id')`를 거는지 —
//    Supabase 클라이언트가 필요한 경로라 순수 함수 검사로는 못 본다. 대신 이 함수가 **입력
//    순서를 믿지 않게** 만들어, 쿼리가 정렬을 빠뜨려도 화면 결과는 흔들리지 않게 했다(2층 방어).
//  · 그 쿼리 경로의 회귀는 Task 5 실브라우저 관찰로만 확인된다(이 리포엔 Playwright 설정이 없다).
import { describe, it, expect } from 'vitest';
import { galleryImages } from './galleryImages';
import { coverImages, type ListingImageRow } from './coverImages';

const row = (o: Partial<ListingImageRow> & { id: string }): ListingImageRow => ({
  listing_id: 'L1',
  storage_path: `path/${o.id}.webp`,
  sort_order: 0,
  ...o,
});

describe('galleryImages', () => {
  it('sort_order 오름차순으로 늘어놓는다', () => {
    expect(
      galleryImages([
        row({ id: 'b', sort_order: 2 }),
        row({ id: 'a', sort_order: 0 }),
        row({ id: 'c', sort_order: 1 }),
      ]),
    ).toEqual(['path/a.webp', 'path/c.webp', 'path/b.webp']);
  });

  it('sort_order가 동률이면 id 오름차순으로 가른다 (#59 — 2차 키가 없으면 조회마다 순서가 바뀐다)', () => {
    expect(
      galleryImages([
        row({ id: 'zz', sort_order: 0 }),
        row({ id: 'aa', sort_order: 0 }),
        row({ id: 'mm', sort_order: 0 }),
      ]),
    ).toEqual(['path/aa.webp', 'path/mm.webp', 'path/zz.webp']);
  });

  it('입력 순서가 어떻게 섞여 들어와도 결과가 같다 (결정론)', () => {
    const rows = [
      row({ id: 'd', sort_order: 1 }),
      row({ id: 'a', sort_order: 0 }),
      row({ id: 'c', sort_order: 1 }),
      row({ id: 'b', sort_order: 0 }),
    ];
    const expected = ['path/a.webp', 'path/b.webp', 'path/c.webp', 'path/d.webp'];
    // 같은 행 집합을 여러 순열로 넣어도 출력이 흔들리지 않아야 한다.
    expect(galleryImages(rows)).toEqual(expected);
    expect(galleryImages([...rows].reverse())).toEqual(expected);
    expect(galleryImages([rows[2], rows[0], rows[3], rows[1]])).toEqual(expected);
  });

  it('입력 배열을 제자리에서 뒤집지 않는다 (호출부가 넘긴 배열은 그대로 남는다)', () => {
    const rows = [row({ id: 'b', sort_order: 1 }), row({ id: 'a', sort_order: 0 })];
    galleryImages(rows);
    expect(rows.map((r) => r.id)).toEqual(['b', 'a']);
  });

  it('사진 0장이면 빈 배열이다 (오류가 아니다 — conventions §10.2 "대표 0장은 정상 상태")', () => {
    expect(galleryImages([])).toEqual([]);
  });

  it('첫 장은 coverImages가 고른 대표와 항상 같다 (대표 판별을 두 군데서 하지 않는다)', () => {
    const rows = [
      row({ id: 'zz', sort_order: 0 }),
      row({ id: 'aa', sort_order: 0 }),
      row({ id: 'b', sort_order: 3 }),
    ];
    expect(galleryImages(rows)[0]).toBe(coverImages(rows).get('L1')?.coverPath);
  });
});
