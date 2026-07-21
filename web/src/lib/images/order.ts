// 사진 순서 계산 — DOM·Supabase 없이 배열만 다루는 순수 함수 (AC1·AC3).
//
// ⚠️ **대표를 계산하는 함수가 여기 없는 것은 의도다.**
// 대표 = 배열 0번이다(사용자 확정 2026-07-18). 대표를 별도 상태로 두면 순서와 대표가
// 각각 움직여 진실이 두 군데 생기고 반드시 어긋난다. 그래서 상태를 하나로 두고,
// "대표로 지정"은 moveToFront(= 0번으로 이동)라는 **순서 조작 하나**로만 표현한다.
// DB의 is_cover는 이 규칙의 파생 결과로 기록한다(sort_order = 0인 행만 true).
//
// 세 함수 모두 원본 배열을 변형하지 않는다 — React 상태로 쓰기 때문에 불변이어야
// 리렌더가 정상 발생한다.

const inRange = (items: readonly unknown[], i: number) => Number.isInteger(i) && i >= 0 && i < items.length;

/** index 항목을 제거한다. 0번(대표)을 지우면 다음 장이 0번이 되어 **자동으로 대표가 승격**된다(AC3). */
export function remove<T>(items: readonly T[], index: number): T[] {
  if (!inRange(items, index)) return [...items];
  return [...items.slice(0, index), ...items.slice(index + 1)];
}

/** from 위치 항목을 뽑아 to 위치에 끼워 넣는다(드래그 순서 변경). 나머지 상대 순서는 보존된다. */
export function reorder<T>(items: readonly T[], from: number, to: number): T[] {
  if (!inRange(items, from) || !inRange(items, to)) return [...items];
  const next = [...items];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

/**
 * index 항목을 맨 앞으로 옮긴다 = **[대표로] 버튼의 동작**.
 * 별도 필드를 건드리지 않고 reorder(items, index, 0)과 정확히 동일하다(AC1 진입점 ②).
 */
export function moveToFront<T>(items: readonly T[], index: number): T[] {
  return reorder(items, index, 0);
}
