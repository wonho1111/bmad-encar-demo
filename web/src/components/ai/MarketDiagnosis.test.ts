// buildCriteriaChips/formatManKm 단위테스트 (5단계) — DOM 없이 순수 함수만 검증한다
// (vitest.config.ts 방침: node 환경, 컴포넌트 렌더는 E2E 몫).
//
// 왜 이 함수만 고정하나: RUNG_DISPLAY는 api/app/market_price.py의 LADDER를 표시 전용으로
// 복제한 표다(주석 참조) — 두 표가 어긋나면 칩 취소선이 실제 필터 조건과 다른 거짓 정보를
// 보여준다. 이 테스트는 "지금 이 표가 낸 결과가 기대한 모양인가"를 고정해 그 표를 실수로
// 건드렸을 때 바로 드러나게 한다.
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  buildCompsListView,
  buildCriteriaChips,
  buildJudgementSentence,
  buildPriceRange,
  buildTabpfnDiffLabel,
  buildVerdictBadge,
  formatHeadline,
  resolveJudgementRatio,
  verdictBasisLabel,
  formatManKm,
  shouldShowPercentileChip,
  type MarketDiagnosisComp,
  type MarketDiagnosisData,
} from './MarketDiagnosis';
import MarketDiagnosis from './MarketDiagnosis';

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
    verdict_basis: '적정가',
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

  it('step=3(트림 해제 — 동일 세대 계열)이면 모델·사고 칩만 비활성이고 연료는 유지된다', () => {
    // 2026-08-31 사다리 개정: "트림 해제" 단이 새로 step3에 끼어들었다 — 모델 문자열이 더는
    // 완전 일치가 아니므로(family 접두 매칭) 세대 칩은 비활성이지만, 연료 조건은 세대 해제
    // (step4)까지 유지된다(구 step4와 달리 이 단은 연료를 풀지 않는다).
    const chips = buildCriteriaChips(diagnosisWithStep(3));
    const byLabel = (label: string) => chips.find((c) => c.label === label);

    expect(byLabel('셀토스')?.active).toBe(false); // 세대(모델 정확 일치) 해제
    expect(byLabel('가솔린')?.active).toBe(true); // 연료 조건은 아직 유지
    expect(byLabel('무사고')?.active).toBe(false); // 사고 조건 해제(이전 단에서 이미 해제됨)
  });

  it('step=5(연료·사고·세대 조건 전부 해제)면 그 세 칩만 비활성(취소선)이다', () => {
    // 사다리 개정으로 "전부 해제" 단이 구 step4에서 step5로 밀렸다.
    const chips = buildCriteriaChips(diagnosisWithStep(5));
    const byLabel = (label: string) => chips.find((c) => c.label === label);

    expect(byLabel('셀토스')?.active).toBe(false); // 세대(모델 정확 일치) 해제
    expect(byLabel('가솔린')?.active).toBe(false); // 연료 조건 해제
    expect(byLabel('무사고')?.active).toBe(false); // 사고 조건 해제
    expect(byLabel('자동')?.active).toBe(true); // 변속기는 사다리가 건드리지 않는다
  });
});

// buildVerdictBadge/shouldShowPercentileChip 단위테스트(실측 결함 F4, 2026-08-31) — 비교군이
// 1~2건(소표본)이면 배지 대신 중립 문구, 백분위 칩은 숨긴다.
describe('buildVerdictBadge', () => {
  it('verdict가 있으면 그 값을 그대로 배지로 쓴다(tone=verdict)', () => {
    expect(buildVerdictBadge('저렴', '사분위')).toEqual({ text: '저렴', tone: 'verdict' });
  });

  it('verdict가 null이고 표본 부족이면 중립 문구를 낸다(tone=neutral)', () => {
    expect(buildVerdictBadge(null, '표본 부족')).toEqual({ text: '표본 부족 — 판정 보류', tone: 'neutral' });
  });

  it('5단 판정 값(다소 높음 등)도 그대로 배지 문구가 된다(2026-09-03 예측 분포 전환)', () => {
    expect(buildVerdictBadge('다소 높음', '분위수')).toEqual({ text: '다소 높음', tone: 'verdict' });
  });

  it('verdict도 null이고 표본 부족도 아니면(비교군 자체 없음) 배지를 아예 안 낸다', () => {
    expect(buildVerdictBadge(null, null)).toBeNull();
  });
});

describe('shouldShowPercentileChip', () => {
  it('표본 2건이면 percentile이 있어도 숨긴다(경계: 3건 미만)', () => {
    expect(shouldShowPercentileChip(0.3, 2)).toBe(false);
  });

  it('표본 3건이면 percentile이 있을 때 보여준다(경계: 3건부터)', () => {
    expect(shouldShowPercentileChip(0.3, 3)).toBe(true);
  });

  it('percentile 자체가 null이면 표본 수와 무관하게 숨긴다', () => {
    expect(shouldShowPercentileChip(null, 10)).toBe(false);
  });
});

// 이 검사가 안 보는 것: RUNG_DISPLAY 표 자체가 백엔드 LADDER와 실제로 일치하는지는 여기서
// 확인할 수 없다(두 언어·두 파일에 각각 선언된 상수라 자동 비교가 안 된다) — 사다리를 바꿀 때
// 사람이 두 표를 함께 고쳐야 한다는 사실은 여전히 주석으로만 지켜진다.

// 통계값 표기 회귀: percentile_cont 보간 중앙값(만원 단위 깨짐)이 원 표기로 새지 않아야 한다
// (실측 버그 2026-08-31: 표본 8건 중앙값 13,475,000 → "13,475,000원"으로 혼자 길게 표기됨).
import { formatStatPrice } from '@/lib/price';

describe('formatStatPrice', () => {
  it('보간된 중앙값을 만원 반올림해 표기한다', () => {
    expect(formatStatPrice(13_475_000)).toBe('1,348만원');
  });
  it('만원 단위 값은 formatPrice와 동일하다', () => {
    expect(formatStatPrice(17_800_000)).toBe('1,780만원');
  });
  it('반올림 경계(내림)', () => {
    expect(formatStatPrice(13_474_999)).toBe('1,347만원');
  });
});

// verdictBasisLabel — 배지 옆 "(무엇 기준)" 보조 라벨(2026-09-03 예측 분포 전환).
describe('verdictBasisLabel', () => {
  it('분위수 기준이면 예측 분포 라벨을 낸다', () => {
    expect(verdictBasisLabel('분위수')).toBe('(예측 분포 기준)');
  });
  it('구 응답의 적정가 기준도 계속 라벨을 낸다(호환)', () => {
    expect(verdictBasisLabel('적정가')).toBe('(적정가 기준)');
  });
  it('사분위 폴백·표본 부족·null은 라벨 없음', () => {
    expect(verdictBasisLabel('사분위')).toBeNull();
    expect(verdictBasisLabel('표본 부족')).toBeNull();
    expect(verdictBasisLabel(null)).toBeNull();
  });
});

// DW-862 재구성 — 헤드라인(①) 범위: tabpfn 분위수가 있으면 그 값, 없으면 비교군 사분위로 대체하고
// approximate=true를 켠다(화면에서 "비슷한 차 실제 호가 기준" 소문구를 붙이라는 신호).
describe('buildPriceRange', () => {
  it('tabpfn 분위수가 있으면 q25~q75를 쓰고 approximate는 false다', () => {
    const data = diagnosisWithStep(0);
    data.tabpfn.quantiles = { q10: 18_000_000, q25: 20_500_000, q50: 22_500_000, q75: 24_500_000, q90: 26_000_000 };
    expect(buildPriceRange(data)).toEqual({ low: 20_500_000, high: 24_500_000, approximate: false });
  });

  it('tabpfn 분위수가 없으면(undefined) 비교군 사분위(q1~q3)로 대체하고 approximate는 true다', () => {
    const data = diagnosisWithStep(0);
    expect(buildPriceRange(data)).toEqual({ low: 21_000_000, high: 25_000_000, approximate: true });
  });

  it('비교군 통계도 없으면(stats null) null을 낸다', () => {
    const data = diagnosisWithStep(0);
    data.stats = null;
    expect(buildPriceRange(data)).toBeNull();
  });
});

describe('formatHeadline', () => {
  it('만원 단위로 반올림해 "비슷한 조건이면 보통 A~B만원" 문장을 만든다', () => {
    // 2026-09-14 문구 개정(DW-885): "이런 조건이면" → "비슷한 조건이면".
    expect(formatHeadline({ low: 20_500_000, high: 24_500_000, approximate: false })).toBe(
      '비슷한 조건이면 보통 2,050~2,450만원',
    );
  });
});

// DW-862 재구성 — 한 문장 판정(②): 비율을 "열 대 중 N대" 비유로 푼다. 실제 비교군 건수(예: "100대
// 중 90대")는 절대 쓰지 않는다 — 이 검사가 그 금지를 직접 고정한다.
// 2026-09-14 문구 개정(DW-885): "이런 조건의 차" → "비슷한 조건의 차".
describe('buildJudgementSentence', () => {
  it('ratio=0.3이면 열에 셋이 이 매물보다 쌉니다', () => {
    expect(buildJudgementSentence(0.3)).toBe('AI 예상으로는 비슷한 조건의 차 열에 셋이 이 매물보다 쌉니다.');
  });

  it('ratio=0에 가까우면(반올림 0) "거의 없습니다" 문구로 바뀐다', () => {
    expect(buildJudgementSentence(0.04)).toBe('AI 예상으로는 비슷한 조건의 차 중 이 매물보다 싼 차가 거의 없습니다.');
  });

  it('ratio=1에 가까우면(반올림 10) "거의 전부입니다" 문구로 바뀐다', () => {
    expect(buildJudgementSentence(0.96)).toBe('AI 예상으로는 비슷한 조건의 차 중 이 매물보다 싼 차가 거의 전부입니다.');
  });

  it('어떤 ratio를 넣어도 실제 대수 표현("100대 중"류)이 나오지 않는다', () => {
    for (const p of [0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1]) {
      const sentence = buildJudgementSentence(p);
      expect(sentence).not.toMatch(/\d+대\s*중/);
      expect(sentence).not.toContain('100대');
      expect(sentence).not.toContain('대 중');
    }
  });
});

// DW-885 — 배지(verdict)와 한 문장 판정이 서로 다른 산출식을 써서 어긋난 결함 수정: 분위수 곡선
// 기반 cdf_at_price가 있으면 그걸 우선 쓰고, 없으면(TabPFN 미예측) 종전 percentile로 폴백한다.
describe('resolveJudgementRatio', () => {
  it('cdf_at_price가 있으면 percentile을 무시하고 그 값을 쓴다', () => {
    expect(resolveJudgementRatio(0.8, 0.3)).toBe(0.8);
  });

  it('cdf_at_price가 null이면(TabPFN 미예측) percentile로 폴백한다', () => {
    expect(resolveJudgementRatio(null, 0.3)).toBe(0.3);
  });

  it('cdf_at_price가 undefined면(구 응답 호환) percentile로 폴백한다', () => {
    expect(resolveJudgementRatio(undefined, 0.3)).toBe(0.3);
  });

  it('cdf_at_price가 0이어도(경계값) percentile로 폴백하지 않는다', () => {
    // 0은 null/undefined가 아니라 "유효한 비율 0.0"이다 — falsy 값 취급 버그를 막는 회귀 검사.
    expect(resolveJudgementRatio(0, 0.9)).toBe(0);
  });

  it('둘 다 없으면 null', () => {
    expect(resolveJudgementRatio(null, null)).toBeNull();
  });
});

// DW-884 — "자세히"의 비교 매물 목록은 60건까지만 나열하고 나머지는 "외 N대"로 요약한다
// (comps 자체는 API에서 최대 500건까지 올 수 있다, MAX_COMPS 500).
describe('buildCompsListView', () => {
  const makeComps = (n: number): MarketDiagnosisComp[] =>
    Array.from({ length: n }, (_, i) => ({ id: `c-${i}`, model: '셀토스', year: 2021, mileage: 10_000, price: 1 }));

  it('60건 이하면 전부 보여주고 moreCount는 0이다', () => {
    const view = buildCompsListView(makeComps(60));
    expect(view.shown).toHaveLength(60);
    expect(view.moreCount).toBe(0);
  });

  it('60건을 넘으면(경계: 61건) 60건만 보여주고 나머지는 moreCount로 센다', () => {
    const view = buildCompsListView(makeComps(61));
    expect(view.shown).toHaveLength(60);
    expect(view.moreCount).toBe(1);
  });

  it('500건이면 60건 + "외 440대"에 해당하는 개수다', () => {
    const view = buildCompsListView(makeComps(500));
    expect(view.shown).toHaveLength(60);
    expect(view.moreCount).toBe(440);
  });
});

describe('buildTabpfnDiffLabel', () => {
  it('이 매물이 적정가보다 비싸면 "N% 높음"', () => {
    expect(buildTabpfnDiffLabel(23_000_000, 20_000_000)).toBe('AI 적정가보다 15% 높음');
  });

  it('이 매물이 적정가보다 싸면 "N% 낮음"', () => {
    expect(buildTabpfnDiffLabel(18_000_000, 20_000_000)).toBe('AI 적정가보다 10% 낮음');
  });

  it('적정가가 없으면(표본 부족) null', () => {
    expect(buildTabpfnDiffLabel(20_000_000, null)).toBeNull();
  });
});

// DW-862 렌더 계약 — 훅 없는 컴포넌트라 renderToStaticMarkup으로 초기 마크업만 고정한다
// (SiteNav.test.ts와 동일 관례, vitest.config.ts 주석의 예외 조항).
describe('MarketDiagnosis — 렌더 계약(DW-862 재구성)', () => {
  it('헤드라인·판정 문장을 그리고, 실제 대수 표현("100대 중")은 어디에도 없다', () => {
    const data = diagnosisWithStep(0);
    data.tabpfn.quantiles = { q10: 18_000_000, q25: 20_500_000, q50: 22_500_000, q75: 24_500_000, q90: 26_000_000 };
    const html = renderToStaticMarkup(createElement(MarketDiagnosis, { data, answer: 'LLM이 지어낸 문장' }));

    expect(html).toContain('비슷한 조건이면 보통 2,050~2,450만원');
    expect(html).toContain('열에 셋이 이 매물보다 쌉니다');
    expect(html).not.toContain('대 중');
    expect(html).not.toContain('100대 중');
    // answer(LLM 자유 문장)는 더는 화면에 그리지 않는다 — 기계적 정보를 그대로 옮겨 말하곤 했기 때문.
    expect(html).not.toContain('LLM이 지어낸 문장');
  });

  it('tabpfn.cdf_at_price가 있으면 percentile 대신 그 값으로 한 문장 판정을 계산한다(DW-885)', () => {
    // percentile=0.3(열에 셋)이지만 cdf_at_price=0.8을 주면 문장은 cdf 기준(열에 여덟)이어야
    // 한다 — 배지(verdict, 분위수 5단 기준)와 문장이 서로 다른 산출식을 쓰던 결함의 재현·고정.
    const data = diagnosisWithStep(0);
    data.tabpfn.quantiles = { q10: 18_000_000, q25: 20_500_000, q50: 22_500_000, q75: 24_500_000, q90: 26_000_000 };
    data.tabpfn.cdf_at_price = 0.8;
    const html = renderToStaticMarkup(createElement(MarketDiagnosis, { data, answer: '' }));

    expect(html).toContain('열에 여덟이 이 매물보다 쌉니다');
    expect(html).not.toContain('열에 셋이 이 매물보다 쌉니다');
  });

  it('접힘 영역(자세히)은 기본 닫힘이다(open 속성 없음)', () => {
    const data = diagnosisWithStep(0);
    const html = renderToStaticMarkup(createElement(MarketDiagnosis, { data, answer: '' }));

    expect(html).toContain('<details');
    expect(html).not.toContain('<details open');
    expect(html).toContain('자세히');
  });

  it('tabpfn 분위수가 없으면 헤드라인에 "비슷한 차 실제 호가 기준" 소문구가 붙는다', () => {
    const data = diagnosisWithStep(0);
    const html = renderToStaticMarkup(createElement(MarketDiagnosis, { data, answer: '' }));

    expect(html).toContain('비슷한 차 실제 호가 기준');
  });
});

// 조사 — "하나"는 받침이 없어 "하나가", 나머지 수사는 "이"(2026-09-15 실측 C07 "열에 하나이").
it('한 문장 판정의 조사가 수사에 맞는다(하나가 / 둘이)', () => {
  expect(buildJudgementSentence(0.1)).toContain('열에 하나가 이 매물보다');
  expect(buildJudgementSentence(0.2)).toContain('열에 둘이 이 매물보다');
});
