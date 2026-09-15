// 시세 진단 카드 그림(③, DW-862 재구성) — 가격 축 하나짜리 'AI 가격 곡선 + 비슷한 차 실제 가격 점'.
//
// 기존 MarketDiagnosisChart.tsx(주행거리×가격 산점도)는 그대로 두고(접힘 영역으로 이동, 그 파일은
// 손대지 않음) 이 컴포넌트를 새로 추가한다 — 사용자가 먼저 보는 그림은 "이 매물이 가격 분포 어디에
// 있나"이지 "주행거리와의 관계"가 아니라서 축을 하나로 줄였다(2026-09-05 확정 설계).
//
// tabpfn.quantiles(q10~q90)가 있으면 밀도 곡선을 그린다(아래 buildDensityCurve). quantiles가
// 없으면 곡선 없이 점 + q1·q3 음영 구간만 그린다(설계 4항).
import { useId } from 'react';

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

  // 2026-09-15 재작업(운영 캡처): 격자를 분위수 꼬리 경계(segments 끝)에서 그대로 자르면 그
  // 자리의 밀도가 0이 아니어서 곡선이 상자처럼 뚝 끊긴다. 질량(segments·mass)은 그대로 두고
  // 평활용 격자만 양쪽으로 대역폭의 2.5배 넓혀 바깥(밀도 0인) 구간까지 커널이 스며들게 해
  // 곡선이 양끝에서 자연히 0 근처로 내려가게 한다.
  const tailExtension = bandwidth * 2.5;
  const gridMin = segments[0].lo - tailExtension;
  const gridMax = segments[segments.length - 1].hi + tailExtension;
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
  verdict = null,
}: {
  listingPrice: number;
  stats: MarketDiagnosisStats | null;
  comps: MarketDiagnosisComp[];
  quantiles: Quantiles5 | null;
  // 덱 5쪽 미리보기 전용(임시) — "이 매물 N만 → {배지 판정}" 라벨에 쓴다. 호출부가 안 넘기면
  // undefined→null로 떨어져 기존 라벨 그대로 나온다.
  verdict?: string | null;
}) {
  const densityClipId = useId();
  const compPrices = comps.map((c) => c.price);
  const densityCurve = quantiles ? buildDensityCurve(quantiles) : [];
  // 밀도 곡선은 q10·q90 밖 꼬리를 지나 평활 대역폭의 2.5배까지 더 그린다(위 buildDensityCurve
  // 재작업) — 축 범위도 그 넓힌 격자(densityCurve 양 끝)를 포함해야 곡선이 잘리지 않는다.
  const domainValues = quantiles
    ? [...compPrices, listingPrice, densityCurve[0].x, densityCurve[densityCurve.length - 1].x]
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
          // 덱5 미리보기(임시) — 위 여백 18px 확장(0 -18 ...). '이 매물'·'AI 적정가' 라벨이 겹칠 때
          // 어긋나게 띄울 자리가 기존 상단 여백(Y_TOP=24px)만으론 부족해 넓혔다(기존 요소 위치는
          // 그대로, 빈 공간만 늘어남).
          viewBox={`0 -18 ${VIEW_W} ${VIEW_H + 18}`}
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
              {/* 덱5 미리보기(임시, five-zone.patch) — 곡선 아래 음영을 분위수 경계 5구간으로
                  색칠. fillPath(곡선 모양) 을 clipPath로 삼아 그 모양 안쪽만 구간별 rect로 칠한다. */}
              <defs>
                <clipPath id={densityClipId}>
                  <path d={fillPath} />
                </clipPath>
              </defs>
              <g clipPath={`url(#${densityClipId})`}>
                {[
                  { from: curveScreenPoints[0]?.x ?? X0, to: xScale(quantiles.q10), color: '#1E8A5A' }, // 매우 저렴
                  { from: xScale(quantiles.q10), to: xScale(quantiles.q25), color: '#6DB38F' }, // 저렴
                  { from: xScale(quantiles.q25), to: xScale(quantiles.q75), color: '#A7B1BC' }, // 적정
                  { from: xScale(quantiles.q75), to: xScale(quantiles.q90), color: '#E09A4F' }, // 다소 높음
                  {
                    from: xScale(quantiles.q90),
                    to: curveScreenPoints[curveScreenPoints.length - 1]?.x ?? X1,
                    color: '#CF533E', // 높음
                  },
                ].map((zone, i) => (
                  <rect
                    key={`zone-${i}`}
                    x={zone.from}
                    y={Y_TOP}
                    width={Math.max(zone.to - zone.from, 0)}
                    height={Y_BASE - Y_TOP}
                    fill={zone.color}
                    opacity={0.55}
                  />
                ))}
              </g>
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

          {quantiles && (
            <>
              {/* 덱5 미리보기(임시) — 기준선 위 q25~q75 괄호선 + "보통 A~B만" 라벨 */}
              <line
                x1={xScale(quantiles.q25)}
                y1={Y_BASE - 14}
                x2={xScale(quantiles.q75)}
                y2={Y_BASE - 14}
                stroke="var(--ink-secondary)"
                strokeWidth={1}
              />
              <line
                x1={xScale(quantiles.q25)}
                y1={Y_BASE - 18}
                x2={xScale(quantiles.q25)}
                y2={Y_BASE - 10}
                stroke="var(--ink-secondary)"
                strokeWidth={1}
              />
              <line
                x1={xScale(quantiles.q75)}
                y1={Y_BASE - 18}
                x2={xScale(quantiles.q75)}
                y2={Y_BASE - 10}
                stroke="var(--ink-secondary)"
                strokeWidth={1}
              />
              <text
                x={(xScale(quantiles.q25) + xScale(quantiles.q75)) / 2}
                y={Y_BASE - 21}
                textAnchor="middle"
                fontSize={10}
                fill="var(--ink-secondary)"
              >
                보통 {Math.round(quantiles.q25 / 10_000).toLocaleString('ko-KR')}~{manLabel(quantiles.q75)}
              </text>

              {/* q50 — 점선 세로선 + "AI 적정가 N만" 라벨. '이 매물' 라벨과 x가 가까우면(70px 미만)
                  겹치므로 이 라벨을 더 위로 어긋나게 띄운다. */}
              <line
                x1={xScale(quantiles.q50)}
                y1={Y_TOP - 2}
                x2={xScale(quantiles.q50)}
                y2={Y_BASE}
                stroke="var(--ink-secondary)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
              <text
                x={xScale(quantiles.q50)}
                y={Math.abs(xScale(listingPrice) - xScale(quantiles.q50)) < 70 ? Y_TOP - 30 : Y_TOP - 10}
                textAnchor="middle"
                fontSize={10}
                fontWeight={600}
                fill="var(--ink-secondary)"
              >
                AI 적정가 {manLabel(quantiles.q50)}
              </text>
            </>
          )}

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
            {verdict ? `이 매물 ${manLabel(listingPrice)} → ${verdict}` : `이 매물 ${manLabel(listingPrice)}`}
          </text>
        </svg>
      </div>
      <p className="mt-1 text-caption text-ink-muted">
        {quantiles
          ? '색 = 판정 구간(매우 저렴~높음) · 점 = 비슷한 차 실제 등록가 · 굵은 선 = 이 매물 · 점선 = AI 적정가'
          : '점 = 비슷한 차 실제 등록가 · 음영 = 가격 중간 50% 구간 · 굵은 선 = 이 매물'}
      </p>
    </div>
  );
}
