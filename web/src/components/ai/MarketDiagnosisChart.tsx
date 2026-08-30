// 시세 진단 산점도(③) — MarketDiagnosis.tsx에서 분리한 SVG 차트(ListingCard/ListingCardImage와
// 동일한 컴포넌트 분리 관례). 사용자 확정 목업의 좌표 계산 로직(x0/x1/yTop/yBottom, xScale/yScale)을
// React로 그대로 이식하되, 목업은 고정값(kmMax=120000 등)이었던 도메인을 이 컴포넌트는 실제 응답
// 데이터(comps·대상 매물·TabPFN 예측)에서 계산한다 — 표본마다 축 범위가 달라야 점들이 잘리지 않는다.
//
// 색은 전부 기존 사이트 CSS 변수(globals.css @theme)를 그대로 참조한다 — 목업과 변수 이름이
// 우연히 같아(brand-petrol·price-emphasis·border-hairline 등) 팔레트를 새로 만들 필요가 없었다.
import type { MarketDiagnosisComp, MarketDiagnosisListing, MarketDiagnosisStats } from './MarketDiagnosis';

const VIEW_W = 640;
const VIEW_H = 320;
const X0 = 60;
const X1 = 610;
const Y_TOP = 20;
const Y_BOTTOM = 260;

/** 값을 step 단위로 올림/내림한다(축 눈금을 보기 좋은 자리에 맞추기 위함). */
function roundUpTo(value: number, step: number): number {
  return Math.ceil(value / step) * step;
}
function roundDownTo(value: number, step: number): number {
  return Math.floor(value / step) * step;
}

export default function MarketDiagnosisChart({
  listing,
  stats,
  comps,
  tabpfnPrice,
}: {
  listing: MarketDiagnosisListing;
  stats: MarketDiagnosisStats;
  comps: MarketDiagnosisComp[];
  tabpfnPrice: number | null;
}) {
  const mileages = [...comps.map((c) => c.mileage), listing.mileage];
  const prices = [...comps.map((c) => c.price), listing.price, stats.min, stats.max];
  if (tabpfnPrice !== null) prices.push(tabpfnPrice);

  const kmMax = Math.max(roundUpTo(Math.max(...mileages) * 1.1, 10_000), 10_000);
  const priceMin = Math.max(0, roundDownTo(Math.min(...prices) * 0.95, 1_000_000));
  const priceMaxRaw = roundUpTo(Math.max(...prices) * 1.05, 1_000_000);
  // priceMin과 같아지면(표본 가격이 전부 동일 등) 0 나눗셈이 나므로 최소 1구간을 보장한다.
  const priceMax = priceMaxRaw > priceMin ? priceMaxRaw : priceMin + 1_000_000;

  const xScale = (km: number) => X0 + (km / kmMax) * (X1 - X0);
  const yScale = (price: number) => Y_TOP + ((priceMax - price) / (priceMax - priceMin)) * (Y_BOTTOM - Y_TOP);

  const xTickCount = 5;
  const xTicks = Array.from({ length: xTickCount }, (_, i) => Math.round((kmMax / (xTickCount - 1)) * i));
  const yTickCount = 5;
  const yTicks = Array.from(
    { length: yTickCount },
    (_, i) => priceMin + ((priceMax - priceMin) / (yTickCount - 1)) * i,
  );

  const manLabel = (price: number) => `${Math.round(price / 10_000).toLocaleString('ko-KR')}만`;
  const manKmLabel = (km: number) => `${Math.round(km / 10_000).toLocaleString('ko-KR')}만`;

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="xMidYMid meet" className="block h-auto w-full">
        {/* 축 */}
        <line x1={X0} y1={Y_BOTTOM} x2={X1} y2={Y_BOTTOM} stroke="var(--border-hairline)" strokeWidth={1} />
        <line x1={X0} y1={Y_TOP} x2={X0} y2={Y_BOTTOM} stroke="var(--border-hairline)" strokeWidth={1} />

        {/* x축 눈금 */}
        {xTicks.map((t) => (
          <text
            key={`xt-${t}`}
            x={xScale(t)}
            y={Y_BOTTOM + 16}
            textAnchor="middle"
            fontSize={11}
            fill="var(--ink-muted)"
          >
            {manKmLabel(t)}
          </text>
        ))}
        <text x={(X0 + X1) / 2} y={VIEW_H - 6} textAnchor="middle" fontSize={11} fill="var(--ink-muted)">
          주행거리 (km)
        </text>

        {/* y축 눈금 + 그리드 */}
        {yTicks.map((p) => (
          <g key={`yt-${p}`}>
            <text x={X0 - 8} y={yScale(p) + 4} textAnchor="end" fontSize={11} fill="var(--ink-muted)">
              {manLabel(p)}
            </text>
            <line
              x1={X0}
              y1={yScale(p)}
              x2={X1}
              y2={yScale(p)}
              stroke="var(--border-hairline)"
              strokeWidth={0.5}
              opacity={0.5}
            />
          </g>
        ))}

        {/* 사분위 밴드(q1~q3) — 연한 채움 */}
        <rect
          x={X0}
          y={yScale(stats.q3)}
          width={X1 - X0}
          height={Math.max(yScale(stats.q1) - yScale(stats.q3), 0)}
          fill="var(--brand-petrol)"
          opacity={0.06}
        />

        {/* 중앙값 점선 */}
        <line
          x1={X0}
          y1={yScale(stats.median)}
          x2={X1}
          y2={yScale(stats.median)}
          stroke="var(--brand-petrol)"
          strokeWidth={1.5}
          strokeDasharray="5,4"
        />
        <text x={X1 - 4} y={yScale(stats.median) - 6} textAnchor="end" fontSize={11} fill="var(--brand-petrol)">
          중앙값 {manLabel(stats.median)}
        </text>

        {/* 비교군 점들 */}
        {comps.map((c) => (
          <circle key={c.id} cx={xScale(c.mileage)} cy={yScale(c.price)} r={4.5} fill="var(--brand-petrol)" opacity={0.55} />
        ))}

        {/* 대상 매물 ↔ TabPFN 예측 연결 점선 */}
        {tabpfnPrice !== null && (
          <line
            x1={xScale(listing.mileage)}
            y1={yScale(listing.price)}
            x2={xScale(listing.mileage)}
            y2={yScale(tabpfnPrice)}
            stroke="var(--ink-muted)"
            strokeWidth={1}
            strokeDasharray="2,2"
          />
        )}

        {/* 대상 매물 마커 */}
        <circle cx={xScale(listing.mileage)} cy={yScale(listing.price)} r={11} fill="var(--price-emphasis)" opacity={0.18} />
        <circle cx={xScale(listing.mileage)} cy={yScale(listing.price)} r={7} fill="var(--price-emphasis)" />
        <text
          x={xScale(listing.mileage) + 11}
          y={yScale(listing.price) + 4}
          fontSize={11}
          fontWeight={700}
          fill="var(--price-emphasis)"
        >
          이 매물 {manLabel(listing.price)}
        </text>

        {/* TabPFN 예측 다이아몬드 */}
        {tabpfnPrice !== null &&
          (() => {
            const dx = xScale(listing.mileage);
            const dy = yScale(tabpfnPrice);
            const s = 6.5;
            return (
              <>
                <polygon
                  points={`${dx},${dy - s} ${dx + s},${dy} ${dx},${dy + s} ${dx - s},${dy}`}
                  fill="var(--brand-petrol-strong)"
                />
                <text x={dx + 11} y={dy - 6} fontSize={11} fontWeight={700} fill="var(--brand-petrol-strong)">
                  적정가 예측 {manLabel(tabpfnPrice)}
                </text>
              </>
            );
          })()}
      </svg>
    </div>
  );
}
