// 시세 진단 카드 그림(③, DW-862 재구성) — 가격 축 하나짜리 'AI 가격 곡선 + 비슷한 차 실제 가격 점'.
//
// 기존 MarketDiagnosisChart.tsx(주행거리×가격 산점도)는 그대로 두고(접힘 영역으로 이동, 그 파일은
// 손대지 않음) 이 컴포넌트를 새로 추가한다 — 사용자가 먼저 보는 그림은 "이 매물이 가격 분포 어디에
// 있나"이지 "주행거리와의 관계"가 아니라서 축을 하나로 줄였다(2026-09-05 확정 설계).
//
// tabpfn.quantiles(q10~q90)가 있으면 종 모양 곡선을 그린다 — Catmull-Rom→3차 베지어 변환(아래
// catmullRomPath)으로 5개 분위수 점을 매끄럽게 잇는다(라이브러리 추가 없이 순수 SVG path 계산).
// quantiles가 없으면 곡선 없이 점 + q1·q3 음영 구간만 그린다(설계 4항).
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

/** Catmull-Rom 스플라인을 3차 베지어 path로 바꾼다(표준 변환식) — 점들을 매끈하게 잇는 용도. */
function catmullRomPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return '';
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? i : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 < points.length ? i + 2 : i + 1];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
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
  quantiles: { q10: number; q25: number; q50: number; q75: number; q90: number } | null;
}) {
  const compPrices = comps.map((c) => c.price);
  const domainValues = quantiles
    ? [...compPrices, listingPrice, quantiles.q10, quantiles.q90]
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

  // 곡선 높이(정점 대비 비율) — q10·q90은 낮게, q50이 정점, q25·q75는 그 중간. 통계적으로 엄밀한
  // 밀도 추정이 아니라 "분포 모양을 눈에 보이게" 하는 표시용 근사치다(간단한 SVG, 라이브러리 없음).
  const heightAt = (frac: number) => Y_BASE - (Y_BASE - Y_TOP) * frac;
  const curvePoints = quantiles
    ? [
        { x: xScale(priceMin), y: Y_BASE },
        { x: xScale(quantiles.q10), y: heightAt(0.22) },
        { x: xScale(quantiles.q25), y: heightAt(0.65) },
        { x: xScale(quantiles.q50), y: heightAt(1) },
        { x: xScale(quantiles.q75), y: heightAt(0.65) },
        { x: xScale(quantiles.q90), y: heightAt(0.22) },
        { x: xScale(priceMax), y: Y_BASE },
      ]
    : [];
  const curvePath = quantiles ? catmullRomPath(curvePoints) : '';

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="xMidYMid meet" className="block h-auto w-full">
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
            {/* AI 가격 곡선 */}
            <path d={`${curvePath} Z`} fill="var(--brand-petrol)" opacity={0.1} />
            <path d={curvePath} fill="none" stroke="var(--brand-petrol)" strokeWidth={2} />
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
      <p className="mt-1 text-caption text-ink-muted">
        {quantiles
          ? '곡선 = AI가 예상하는 가격대 · 점 = 비슷한 차 실제 등록가 · 굵은 선 = 이 매물'
          : '점 = 비슷한 차 실제 등록가 · 음영 = 가격 중간 50% 구간 · 굵은 선 = 이 매물'}
      </p>
    </div>
  );
}
