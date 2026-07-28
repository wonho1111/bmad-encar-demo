// nav-links.ts 단위테스트 — vitest.config.ts 규약(순수 유틸은 단위테스트로 보강, 규칙12).
// 지금은 role 무관 동일 3개 링크만 검증한다. Epic 14가 role 분기를 넣으면 이 테스트도
// 역할별 기대값으로 확장한다(그때 이 테스트가 회귀 방지선이 된다).
import { describe, expect, it } from 'vitest';
import { getConsumerNavLinks } from './nav-links';

describe('getConsumerNavLinks', () => {
  it('내 차 사기·AI로 찾기·내 차 팔기 3개를 이 순서로 반환한다', () => {
    expect(getConsumerNavLinks(null)).toEqual([
      { label: '내 차 사기', href: '/search' },
      { label: 'AI로 찾기', href: '/ai' },
      { label: '내 차 팔기', href: '/sell' },
    ]);
  });
});
