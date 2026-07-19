// 매물별 "대표사진 + 사진 장수"를 한 번에 구하는 순수 함수 (Story 9.4 AC9).
//
// 왜 컴포넌트가 아니라 여기인가:
//   9.3 코드리뷰가 남긴 교훈 — **대표 대상을 두 군데서 따로 계산하면 화면과 DB가 갈린다.**
//   그래서 "어느 행이 대표인가"를 정하는 자리를 이 함수 하나로 못박는다. 카드는 계산하지 않고
//   결과만 받는다. (그리고 순수 함수라 Vitest로 검사할 수 있다 — web 표준은 .ts만 단위테스트.)
//
// 대표 판별 규칙(정본: docs/conventions.md §10.1):
//   **`sort_order` → `id` 순으로 정렬했을 때의 첫 행이 대표다. `is_cover`는 읽지 않는다.**
//   · `is_cover`는 순서의 **파생 결과**로 기록될 뿐이고(order.ts 주석 참조), 시드·레거시 행은
//     전부 `is_cover=false`일 수 있다 — 그것만 믿으면 사진이 있는데도 대표가 없다고 나온다.
//   · `sort_order`에 tie-break가 없어(#47-2) 2차 키 `id`가 없으면 **조회할 때마다 순서가 달라진다.**
//     그래서 DB 정렬(`.order('sort_order').order('id')`)과 **같은 규칙**을 여기서도 명시적으로 건다 —
//     호출부가 정렬을 빠뜨려도 결과가 흔들리지 않게(#59).

/** 이 함수가 보는 최소 컬럼. 실제 테이블에는 `is_cover`·`credit`도 있지만 **일부러 받지 않는다**. */
export type ListingImageRow = {
  listing_id: string;
  storage_path: string;
  sort_order: number;
  id: string;
};

export type CoverImage = {
  /** 대표사진의 버킷 내 경로. URL 조립은 호출부가 getPublicUrl로 한다. */
  coverPath: string;
  /** 그 매물의 사진 총 장수("N장" 배지용). 항상 1 이상 — 0장 매물은 Map에 아예 없다. */
  count: number;
};

/**
 * `listing_images` 행 배열 → 매물별 { 대표 경로, 장수 }.
 *
 * **사진이 0장인 매물은 Map에 넣지 않는다** — "키는 있는데 값이 비었다"는 상태를 만들면
 * 소비처가 `?.coverPath` 유무로 또 분기해야 한다. 없으면 없는 것이 읽기 쉽다.
 * (대표 0장은 정상 상태다 — conventions.md §10.1)
 */
export function coverImages(rows: readonly ListingImageRow[]): Map<string, CoverImage> {
  // 대표 "행"을 들고 다닌다 — 경로만 들면 비교할 때마다 원본 행을 되찾아야 한다.
  const winners = new Map<string, { row: ListingImageRow; count: number }>();

  for (const row of rows) {
    const current = winners.get(row.listing_id);
    if (!current) {
      winners.set(row.listing_id, { row, count: 1 });
      continue;
    }
    current.count += 1;
    // 지금까지의 대표보다 앞서는 행이면 대표를 바꾼다. 정렬된 입력을 가정하지 않는 이유는
    // 위 주석대로 — 호출부의 정렬 누락이 화면에 새어 나오지 않게 하기 위해서다.
    if (comesFirst(row, current.row)) current.row = row;
  }

  return new Map(
    [...winners].map(([listingId, w]) => [listingId, { coverPath: w.row.storage_path, count: w.count }]),
  );
}

/** a가 b보다 `sort_order` → `id` 순서에서 앞서는가(DB의 `order('sort_order').order('id')`와 같은 규칙). */
function comesFirst(a: ListingImageRow, b: ListingImageRow): boolean {
  return a.sort_order !== b.sort_order ? a.sort_order < b.sort_order : a.id < b.id;
}
