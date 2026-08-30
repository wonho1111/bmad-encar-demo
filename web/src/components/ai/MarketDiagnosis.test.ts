// buildCriteriaChips/formatManKm 단위테스트 (5단계) — DOM 없이 순수 함수만 검증한다
// (vitest.config.ts 방침: node 환경, 컴포넌트 렌더는 E2E 몫).
//
// 왜 이 함수만 고정하나: RUNG_DISPLAY는 api/app/market_price.py의 LADDER를 표시 전용으로
// 복제한 표다(주석 참조) — 두 표가 어긋나면 칩 취소선이 실제 필터 조건과 다른 거짓 정보를
// 보여준다. 이 테스트는 "지금 이 표가 낸 결과가 기대한 모양인가"를 고정해 그 표를 실수로
// 건드렸을 때 바로 드러나게 한다.
import { describe, expect, it } from 'vitest';

import { buildCriteriaChips, formatManKm, type MarketDiagnosisData } from './MarketDiagnosis';

const BASE_LISTING: MarketDiagnosisData['listing'] = {
  id: 'l-1',
  manufacturer: '기아',
  model: '셀토스',
  year: 2021,
  mileage: 33_000,
  price: 22_000_000,
  fuel: '가솔린',
  transmission: '자동',
  displacement: 1998,
  accident_free: true,
  accident_status: '무사고',
  region: '경기',
};

function diagnosisWithStep(step: number): MarketDiagnosisData {
  return {
    listing: BASE_LISTING,
    criteria: { step, desc: '테스트 단계', sample_count: 23 },
    stats: { min: 19_000_000, q1: 21_000_000, median: 23_000_000, q3: 25_000_000, max: 27_000_000 },
    percentile: 0.3,
    verdict: '저렴',
    tabpfn: { price: 23_500_000, note: 'TabPFN 예측' },
    comps: [],
  };
}

describe('formatManKm', () => {
  it('정수 만 단위는 소수점 없이 "N만km"', () => {
    expect(formatManKm(30_000)).toBe('3만km');
  });

  it('소수 만 단위는 소수 1자리로 "N.N만km"', () => {
    expect(formatManKm(33_000)).toBe('3.3만km');
  });
});

describe('buildCriteriaChips', () => {
  it('step=0(완화 없음)이면 모든 조건 칩이 active다', () => {
    const chips = buildCriteriaChips(diagnosisWithStep(0));
    expect(chips.every((c) => c.active)).toBe(true);
    // 연식 밴드 ±2년(step0), 대상 2021년 → 2019~2023년식.
    expect(chips.map((c) => c.label)).toContain('2019~2023년식');
  });

  it('step=4(연료·사고·세대 조건 전부 해제)면 그 세 칩만 비활성(취소선)이다', () => {
    const chips = buildCriteriaChips(diagnosisWithStep(4));
    const byLabel = (label: string) => chips.find((c) => c.label === label);

    expect(byLabel('셀토스')?.active).toBe(false); // 세대(모델 정확 일치) 해제
    expect(byLabel('가솔린')?.active).toBe(false); // 연료 조건 해제
    expect(byLabel('무사고')?.active).toBe(false); // 사고 조건 해제
    expect(byLabel('자동')?.active).toBe(true); // 변속기는 사다리가 건드리지 않는다
  });
});

// 이 검사가 안 보는 것: RUNG_DISPLAY 표 자체가 백엔드 LADDER와 실제로 일치하는지는 여기서
// 확인할 수 없다(두 언어·두 파일에 각각 선언된 상수라 자동 비교가 안 된다) — 사다리를 바꿀 때
// 사람이 두 표를 함께 고쳐야 한다는 사실은 여전히 주석으로만 지켜진다.
