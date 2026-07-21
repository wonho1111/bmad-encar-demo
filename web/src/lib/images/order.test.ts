// 사진 순서 계산 테스트 (AC1·AC3).
//
// ⚠️ 여기엔 "대표"를 계산하는 테스트가 따로 없다. 그건 누락이 아니라 설계다 —
// **대표 = 배열 0번**이므로(사용자 확정 2026-07-18) 순서를 검증하면 대표가 검증된다.
// 대표를 별도 상태로 두면 순서와 어긋날 수 있어서 그 상태 자체를 만들지 않았다.
import { describe, it, expect } from 'vitest';
import { reorder, moveToFront, remove } from './order';

const L = ['a', 'b', 'c', 'd'];

describe('remove', () => {
  it('0번(대표)을 지우면 다음 장이 0번이 된다 = 자동 대표 승격 (AC3)', () => {
    expect(remove(L, 0)).toEqual(['b', 'c', 'd']);
  });

  it('중간을 지워도 나머지 순서는 보존된다', () => {
    expect(remove(L, 2)).toEqual(['a', 'b', 'd']);
  });

  it('마지막 1장을 지우면 빈 배열이 된다 (사진 0장도 정상 상태 — AC2)', () => {
    expect(remove(['only'], 0)).toEqual([]);
  });

  it('범위 밖 인덱스는 아무것도 바꾸지 않는다', () => {
    expect(remove(L, 9)).toEqual(L);
    expect(remove(L, -1)).toEqual(L);
  });

  it('원본 배열을 변형하지 않는다 (React 상태로 쓰므로 불변이어야 한다)', () => {
    const src = [...L];
    remove(src, 0);
    expect(src).toEqual(L);
  });
});

describe('moveToFront', () => {
  it('[대표로] 버튼 = 그 사진을 0번으로 옮기는 것과 정확히 같다 (AC1)', () => {
    expect(moveToFront(L, 2)).toEqual(['c', 'a', 'b', 'd']);
  });

  it('나머지 순서를 보존한다 (끼워넣기지 뒤섞기가 아니다)', () => {
    expect(moveToFront(L, 3)).toEqual(['d', 'a', 'b', 'c']);
  });

  it('이미 0번이면 그대로다', () => {
    expect(moveToFront(L, 0)).toEqual(L);
  });

  it('범위 밖 인덱스는 아무것도 바꾸지 않는다', () => {
    expect(moveToFront(L, 9)).toEqual(L);
  });
});

describe('reorder', () => {
  it('앞에서 뒤로 끌면 그 사이 항목들이 앞으로 당겨진다', () => {
    expect(reorder(L, 0, 2)).toEqual(['b', 'c', 'a', 'd']);
  });

  it('뒤에서 앞으로 끌면 0번이 바뀐다 = 대표가 바뀐다 (AC1 진입점 ①)', () => {
    expect(reorder(L, 3, 0)).toEqual(['d', 'a', 'b', 'c']);
  });

  it('제자리로 끌면 그대로다', () => {
    expect(reorder(L, 1, 1)).toEqual(L);
  });

  it('범위 밖 인덱스는 아무것도 바꾸지 않는다', () => {
    expect(reorder(L, 0, 9)).toEqual(L);
    expect(reorder(L, -1, 0)).toEqual(L);
  });

  it('원본 배열을 변형하지 않는다', () => {
    const src = [...L];
    reorder(src, 0, 3);
    expect(src).toEqual(L);
  });
});
