// 매물 1건의 **사진 전 장을 화면 순서대로** 늘어놓는 순수 함수 (Story 9.5 AC3).
//
// `coverImages`(9.4)와의 관계 — 같은 규칙, 다른 모양:
//   · `coverImages` = 매물 **여러 건**의 **대표 1장 + 장수**  (목록 카드용)
//   · `galleryImages` = 매물 **한 건**의 **전 장 순서**        (상세 갤러리용)
//   두 함수 모두 정렬 규칙은 `docs/conventions.md §10.1`의 **`sort_order` → `id`** 하나다.
//   그래서 `galleryImages(rows)[0]`은 `coverImages(rows)`의 대표와 **항상 같다**
//   (`galleryImages.test.ts`가 그걸 단언한다 — 대표 판별이 두 갈래로 갈리지 않게).
//
// 왜 정렬을 여기서 또 거는가(2층 방어, B9):
//   호출부의 DB 쿼리도 `.order('sort_order').order('id')`를 건다. 둘 중 하나만 있어도 결과는
//   같지만, **쿼리에서 정렬을 빠뜨리는 실수는 아무도 안 깨지고 조용히 지나간다**(#59가 정확히
//   그 상태였다). 순수 함수 쪽에 박아 두면 검사로 고정할 수 있다.
import type { ListingImageRow } from './coverImages';

/**
 * `listing_images` 행 배열 → 화면에 그릴 순서대로 정렬된 `storage_path` 배열.
 *
 * **입력 순서를 믿지 않는다** — 어떤 순서로 들어와도 같은 결과가 나온다.
 * URL 조립(`getPublicUrl`)은 호출부의 몫이다(이 함수는 버킷·환경변수를 모른다 — 그래야 테스트가 순수해진다).
 *
 * 사진 0장이면 빈 배열. **오류가 아니라 정상 상태**이며, 화면이 "사진 준비중" 플레이스홀더를
 * 그린다(`conventions.md §10.2`).
 */
export function galleryImages(rows: readonly ListingImageRow[]): string[] {
  // 복사본을 정렬한다 — 호출부가 넘긴 배열을 제자리에서 뒤집으면 호출부가 그 배열을 다시 쓸 때
  // 순서가 이미 바뀌어 있는 원격 부작용이 생긴다.
  return [...rows].sort(compare).map((r) => r.storage_path);
}

/** `sort_order` → `id` (DB의 `order('sort_order').order('id')`와 **같은 규칙**). */
function compare(a: ListingImageRow, b: ListingImageRow): number {
  if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}
