// 시세 진단 카드 그림(③, DW-862 재구성) — 가격 축 하나짜리 'AI 가격 곡선 + 비슷한 차 실제 가격 점'.
//
// 기존 MarketDiagnosisChart.tsx(주행거리×가격 산점도)는 그대로 두고(접힘 영역으로 이동, 그 파일은
// 손대지 않음) 이 컴포넌트를 새로 추가한다 — 사용자가 먼저 보는 그림은 "이 매물이 가격 분포 어디에
// 있나"이지 "주행거리와의 관계"가 아니라서 축을 하나로 줄였다(2026-09-05 확정 설계).
//
// tabpfn.quantiles(q10~q90)가 있으면 밀도 곡선을 그린다(아래 buildDensityCurve). quantiles가
// 없으면 곡선 없이 점 + q1·q3 음영 구간만 그린다(설계 4항).
import type { MarketDiagnosisComp, MarketDiagnosisStats } from './MarketDiagnosis';

const VIEW_W = 640;
const VIEW_H = 210;
const X0 = 46;
const X1 = 610;
const Y_TOP = 24; // 곡선 정점
const Y_BASE = 150; // 가격 축(기준선) — 점·곡선 바닥이 여기 놓인다
const Y_TICK = 172;

function roundUpTo(value: number, step: number): number {
  return Math.ceil(value / step) * step;
}
function roundDownTo(value: number, step: number): number {
  return Math.floor(value / step) * step;
}

export type Quantiles5 = { q10: number; q25: number; q50: number; q75: number; q90: number };

// 2026-09-14 재작업(DW-885, 운영 실측): 종전엔 분위수마다 고정 높이(0.22/0.65/1/0.65/0.22)를
// 박고 Catmull-Rom 스플라인으로 이었다 — q25·q50처럼 이웃 분위수가 서로 가까우면 스플라인이
// 오버슈트해 정점 근처가 움푹 파였다(운영 캡처 8건 중 다수에서 확인). 대신 "분위수 구간에
// 질량이 얼마나 있는가"를 먼저 정하고 밀도(질량÷폭)를 계산한 뒤, 그 값을 그리드에서 가우시안
// 커널로 평활해 폴리라인(직선 구간 연결, 스플라인 아님)으로 그린다 — 오버슈트가 구조적으로
// 없어 파임이 생기지 않는다(구간이 좁을수록 밀도가 높아져 정점이 그쪽으로 자연히 몰릴 뿐).
const DENSITY_GRID_POINTS = 72; // 요구 범위(60~80) 안의 확정값

type DensitySegment = { lo: number; hi: number; mass: number };

function densitySegments(q: Quantiles5): DensitySegment[] {
  const w1 = q.q25 - q.q10;
  const w2 = q.q90 - q.q75;
  return [
    { lo: q.q10 - w1, hi: q.q10, mass: 0.1 },
    { lo: q.q10, hi: q.q25, mass: 0.15 },
    { lo: q.q25, hi: q.q50, mass: 0.25 },
    { lo: q.q50, hi: q.q75, mass: 0.25 },
    { lo: q.q75, hi: q.q90, mass: 0.15 },
    { lo: q.q90, hi: q.q90 + w2, mass: 0.1 },
  ];
}

function densityAt(x: number, segments: DensitySegment[]): number {
  for (const seg of segments) {
    if (x >= seg.lo && x <= seg.hi) {
      const width = seg.hi - seg.lo;
      return width > 0 ? seg.mass / width : 0;
    }
  }
  return 0;
}

/**
 * 분위수 5단(q10~q90)에서 구간별 밀도(질량÷폭)를 계산해 가우시안 커널로 평활한 뒤 정점을 1로
 * 정규화한 곡선 점들을 낸다. x는 가격(원), y는 0~1 정규화 밀도. 순수 함수(단위테스트 대상,
 * MarketDiagnosisPriceChart.test.ts).
 */
export function buildDensityCurve(q: Quantiles5): { x: number; y: number }[] {
  const segments = densitySegments(q);
  const widths = segments.map((s) => s.hi - s.lo).filter((w) => w > 0);
  const sortedWidths = [...widths].sort((a, b) => a - b);
  const medianWidth = sortedWidths[Math.floor(sortedWidths.length / 2)] ?? 1;
  const bandwidth = Math.max(medianWidth * 0.6, 1); // 폭 0(분위수 값 중복) 방지

  const gridMin = segments[0].lo;
  const gridMax = segments[segments.length - 1].hi;
  const step = (gridMax - gridMin) / (DENSITY_GRID_POINTS - 1);
  const grid = Array.from({ length: DENSITY_GRID_POINTS }, (_, i) => gridMin + step * i);
  const rawValues = grid.map((x) => densityAt(x, segments));

  const smoothed = grid.map((xi) => {
    let weightedSum = 0;
    let weightTotal = 0;
    for (let j = 0; j < grid.length; j++) {
      const d = (xi - grid[j]) / bandwidth;
      const w = Math.exp(-0.5 * d * d);
      weightedSum += w * rawValues[j];
      weightTotal += w;
    }
    return weightTotal > 0 ? weightedSum / weightTotal : 0;
  });

  const peak = Math.max(...smoothed, 1e-9);
  return grid.map((x, i) => ({ x, y: smoothed[i] / peak }));
}

export default function MarketDiagnosisPriceChart({
  listingPrice,
  stats,
  comps,
  quantiles,
}: {
  listingPrice: number;
  stats: MarketDiagnosisStats | null;
  comps: MarketDiagnosisComp[];
  quantiles: Quantiles5 | null;
}) {
  const compPrices = comps.map((c) => c.price);
  // 밀도 곡선은 q10·q90 밖 꼬리(q10−w1 ~ q90+w2)까지 그린다 — 축 범위도 그만큼 넓혀야 곡선이
  // 잘리지 않는다(quantiles.q10/q90만 넣던 종전보다 넓음, DW-885 재작업).
  const domainValues = quantiles
    ? [
        ...compPrices,
        listingPrice,
        quantiles.q10 - (quantiles.q25 - quantiles.q10),
        quantiles.q90 + (quantiles.q90 - quantiles.q75),
      ]
    : [...compPrices, listingPrice, ...(stats ? [stats.min, stats.max] : [])];

  const pad = quantiles
    ? Math.max((quantiles.q90 - quantiles.q10) * 0.35, quantiles.q50 * 0.05, 500_000)
    : 0;
  const rawMin = Math.min(...domainValues) - pad;
  const rawMax = Math.max(...domainValues) + pad;
  const priceMin = Math.max(0, roundDownTo(rawMin * (quantiles ? 1 : 0.95), 1_000_000));
  const priceMaxRounded = roundUpTo(rawMax * (quantiles ? 1 : 1.05), 1_000_000);
  const priceMax = priceMaxRounded > priceMin ? priceMaxRounded : priceMin + 1_000_000;

  const xScale = (price: number) => X0 + ((price - priceMin) / (priceMax - priceMin)) * (X1 - X0);

  const tickCount = 5;
  const ticks = Array.from(
    { length: tickCount },
    (_, i) => priceMin + ((priceMax - priceMin) / (tickCount - 1)) * i,
  );
  const manLabel = (price: number) => `${Math.round(price / 10_000).toLocaleString('ko-KR')}만`;

  // 곡선 높이(정점 대비 비율) — buildDensityCurve가 낸 0~1 정규화 밀도를 화면 y좌표로 옮긴다.
  const heightAt = (frac: number) => Y_BASE - (Y_BASE - Y_TOP) * frac;
  const densityCurve = quantiles ? buildDensityCurve(quantiles) : [];
  const curveScreenPoints = densityCurve.map((p) => ({ x: xScale(p.x), y: heightAt(p.y) }));
  const polylinePoints = curveScreenPoints.map((p) => `${p.x},${p.y}`).join(' ');
  const fillPath =
    curveScreenPoints.length > 0
      ? [
          `M ${curveScreenPoints[0].x} ${Y_BASE}`,
          ...curveScreenPoints.map((p) => `L ${p.x} ${p.y}`),
          `L ${curveScreenPoints[curveScreenPoints.length - 1].x} ${Y_BASE}`,
          'Z',
        ].join(' ')
      : '';

  return (
    <div className="w-full">
      <div className="flex items-stretch gap-1">
        {/* 세로축 설명 — 밀도 단위는 숫자로 봐야 의미가 없어 눈금 대신 "많음/적음"만 표시한다.
            가운데 축 제목은 CSS writing-mode(글자를 한 자씩 세로로 쌓음, 2026-09-15 운영 실측 —
            읽기 어려움)를 버리고 svg 안에서 rotate(-90)으로 눕혀 한 줄로 읽히게 한다(아래). */}
        <div className="flex w-4 shrink-0 flex-col items-center justify-between py-1 text-center" aria-hidden>
          <span className="text-[9px] leading-none text-ink-muted">많음</span>
          <span className="text-[9px] leading-none text-ink-muted">적음</span>
        </div>
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="xMidYMid meet"
          className="block h-auto min-w-0 flex-1"
        >
          {/* 세로축 제목 — 왼쪽 여백(X0 안쪽)에서 -90도 회전한 한 줄 텍스트(위 주석 참조). */}
          <text
            x={16}
            y={(Y_TOP + Y_BASE) / 2}
            transform={`rotate(-90 16 ${(Y_TOP + Y_BASE) / 2})`}
            textAnchor="middle"
            fontSize={9}
            fill="var(--ink-muted)"
          >
            비슷한 조건의 차가 얼마나 있을지
          </text>

          {/* 축 */}
          <line x1={X0} y1={Y_BASE} x2={X1} y2={Y_BASE} stroke="var(--border-hairline)" strokeWidth={1} />
          {ticks.map((t) => (
            <text key={`t-${t}`} x={xScale(t)} y={Y_TICK} textAnchor="middle" fontSize={11} fill="var(--ink-muted)">
              {manLabel(t)}
            </text>
          ))}
          <text x={(X0 + X1) / 2} y={VIEW_H - 4} textAnchor="middle" fontSize={11} fill="var(--ink-muted)">
            가격 (만원)
          </text>

          {quantiles ? (
            <>
              {/* 밀도 곡선(폴리라인) — 음영은 곡선 전체(꼬리 포함, fillPath) 아래를 덮는다.
                  2026-09-15 운영 실측: 0.1이면 상자처럼 도드라져 더 옅게(0.08, stats 폴백
                  음영과 동일 값)로 낮췄다. */}
              <path d={fillPath} fill="var(--brand-petrol)" opacity={0.08} />
              <polyline points={polylinePoints} fill="none" stroke="var(--brand-petrol)" strokeWidth={2} />
            </>
          ) : (
            stats && (
              // tabpfn 없음 — 곡선 대신 q1~q3 음영 구간만.
              <rect
                x={xScale(stats.q1)}
                y={Y_TOP}
                width={Math.max(xScale(stats.q3) - xScale(stats.q1), 0)}
                height={Y_BASE - Y_TOP}
                fill="var(--brand-petrol)"
                opacity={0.08}
              />
            )
          )}

          {/* 비슷한 차 실제 가격 점(가격 축 위 점) */}
          {comps.map((c) => (
            <circle key={c.id} cx={xScale(c.price)} cy={Y_BASE} r={4.5} fill="var(--brand-petrol)" opacity={0.55} />
          ))}

          {/* 이 매물 — 세로선 */}
          <line
            x1={xScale(listingPrice)}
            y1={Y_TOP - 6}
            x2={xScale(listingPrice)}
            y2={Y_BASE}
            stroke="var(--price-emphasis)"
            strokeWidth={2}
          />
          <text
            x={xScale(listingPrice)}
            y={Y_TOP - 10}
            textAnchor="middle"
            fontSize={11}
            fontWeight={700}
            fill="var(--price-emphasis)"
          >
            이 매물 {manLabel(listingPrice)}
          </text>
        </svg>
      </div>
      <p className="mt-1 text-caption text-ink-muted">
        {quantiles
          ? '곡선 높이 = 비슷한 차가 몰린 정도 · 점 = 비슷한 차 실제 등록가 · 굵은 선 = 이 매물'
          : '점 = 비슷한 차 실제 등록가 · 음영 = 가격 중간 50% 구간 · 굵은 선 = 이 매물'}
      </p>
    </div>
  );
}
