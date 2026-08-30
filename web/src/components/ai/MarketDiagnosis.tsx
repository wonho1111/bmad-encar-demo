// 시세 진단 렌더 블록 (5단계) — ChatAssistant 어시스턴트 말풍선 안에서 SearchResponse.market_diagnosis가
// 있을 때만 그려지는 STEP2 구성(사용자 확정 목업 STEP2 블록을 이식). 상태 없는 표현용 컴포넌트.
//
// 데이터 출처: api/app/market_price.py diagnose()의 반환 dict 그대로 — 숫자는 전부 SQL·TabPFN이
// 낸 값이고(그 파일 모듈 docstring: "수치는 전부 SQL/모델이 낸다"), 이 컴포넌트는 그 값을 배치·
// 표시만 한다(재계산 금지). 유일한 예외는 아래 RUNG_DISPLAY 표 — 완화 사다리 단계별로 "어떤 조건이
// 해제됐는지"를 칩 취소선으로 보여주기 위한 **표시 전용** 복제본이다(실제 필터링에는 관여하지
// 않는다 — 정본은 api/app/market_price.py의 LADDER, 그 표가 바뀌면 이 표도 함께 바꿔야 한다).
//
// ①·⑤가 둘 다 "LLM answer"로 지시됐지만 API가 주는 answer는 하나뿐이라(SearchResponse.answer),
// 같은 문장을 두 번 보여주지 않고 헤드라인 위치(①) 한 곳에만 렌더한다(ChatAssistant가 answer를
// 넘겨준다 — 이 컴포넌트가 렌더되면 ChatAssistant의 기존 평문 버블은 렌더하지 않는다).
//
// ⚠️ mock(사용자 확정 목업)은 자동차365 참고선·표기를 포함하지만, 상위 결정으로 이 프로젝트는
//   그 데이터를 갖고 있지 않아(실데이터 없음) 구현하지 않는다 — 각주는 TabPFN·표본 수 두 줄뿐이다.
import { formatPrice } from '@/lib/price';
import MarketDiagnosisChart from './MarketDiagnosisChart';

export type MarketDiagnosisListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  mileage: number;
  price: number;
  fuel: string;
  transmission: '자동' | '수동';
  displacement: number;
  accident_free: boolean;
  accident_status: '무사고' | '단순교환' | '사고' | null;
  region: string;
};

export type MarketDiagnosisComp = {
  id: string;
  model: string;
  year: number;
  mileage: number;
  price: number;
};

export type MarketDiagnosisStats = {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
};

export type MarketDiagnosisData = {
  listing: MarketDiagnosisListing;
  criteria: { step: number; desc: string; sample_count: number };
  stats: MarketDiagnosisStats | null;
  percentile: number | null;
  verdict: '저렴' | '적정' | '높음' | null;
  tabpfn: { price: number | null; note: string };
  comps: MarketDiagnosisComp[];
};

// 완화 사다리 표시 전용 복제본(정본: api/app/market_price.py LADDER) — 취소선 칩 판단에만 쓴다.
const RUNG_DISPLAY: Record<
  number,
  { yearBand: number; kmBand: number; fuelActive: boolean; accidentActive: boolean; modelExact: boolean }
> = {
  0: { yearBand: 2, kmBand: 30_000, fuelActive: true, accidentActive: true, modelExact: true },
  1: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: true, modelExact: true },
  2: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: false, modelExact: true },
  3: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: false, modelExact: false },
  4: { yearBand: 3, kmBand: 50_000, fuelActive: false, accidentActive: false, modelExact: false },
};

/** 주행거리를 "3.3만km" 식 만 단위로 표시한다(정수면 "3만km", 소수면 소수 1자리). */
export function formatManKm(km: number): string {
  const man = Math.round((km / 10_000) * 10) / 10;
  return `${Number.isInteger(man) ? man : man.toFixed(1)}만km`;
}

export type CriteriaChip = { label: string; active: boolean };

/** 비교 기준 칩(②) 목록을 만든다 — target 속성 + 현재 사다리 단계(criteria.step)의 활성 조건.
 * 순수 함수(단위테스트 대상, MarketDiagnosis.test.ts).
 */
export function buildCriteriaChips(data: MarketDiagnosisData): CriteriaChip[] {
  const { listing, criteria } = data;
  const rung = RUNG_DISPLAY[criteria.step] ?? RUNG_DISPLAY[0];
  const yearLo = listing.year - rung.yearBand;
  const yearHi = listing.year + rung.yearBand;
  const kmLo = Math.max(listing.mileage - rung.kmBand, 0);
  const kmHi = listing.mileage + rung.kmBand;
  const accidentLabel = listing.accident_free ? '무사고' : listing.accident_status || '사고';

  return [
    { label: listing.model, active: rung.modelExact },
    { label: listing.fuel, active: rung.fuelActive },
    { label: listing.transmission, active: true },
    { label: accidentLabel, active: rung.accidentActive },
    { label: `${yearLo}~${yearHi}년식`, active: true },
    { label: `${formatManKm(kmLo)}~${formatManKm(kmHi)}`, active: true },
  ];
}

function verdictToneClass(verdict: MarketDiagnosisData['verdict']): string {
  if (verdict === '저렴') return 'bg-trust-green-bg text-trust-green-ink';
  if (verdict === '높음') return 'bg-warn-amber-bg text-warn-amber-ink';
  return 'border border-border-hairline text-ink-secondary';
}

function StatCell({
  label,
  value,
  note,
  emphasis,
}: {
  label: string;
  value: string;
  note?: string;
  emphasis?: boolean;
}) {
  return (
    <div className="rounded-[10px] border border-border-hairline bg-surface-base p-2.5 text-center">
      <div className={`text-[15px] font-bold ${emphasis ? 'text-price-emphasis' : 'text-ink-primary'}`}>
        {value}
      </div>
      <div className="mt-0.5 text-caption text-ink-muted">{note ? `${label} · ${note}` : label}</div>
    </div>
  );
}

export default function MarketDiagnosis({ data, answer }: { data: MarketDiagnosisData; answer: string }) {
  const { listing, criteria, stats, percentile, verdict, tabpfn, comps } = data;
  const chips = buildCriteriaChips(data);
  const hasChart = stats !== null && comps.length > 0;

  // 대상가와 유사매물 중앙값의 차이(④ 통계 3칸 세 번째 칸 보조 라벨) — stats가 있을 때만 계산.
  const diffLabel = (() => {
    if (!stats || stats.median === 0) return null;
    const diffPct = ((listing.price - stats.median) / stats.median) * 100;
    const rounded = Math.round(diffPct * 10) / 10;
    if (rounded === 0) return '중앙값과 동일';
    return rounded < 0 ? `저렴 ${rounded}%` : `높음 +${rounded}%`;
  })();

  return (
    <div className="flex w-full flex-col gap-4">
      {/* ① 판정 헤드라인(LLM answer) + 백분위 미니칩 */}
      <div className="flex flex-wrap items-center gap-2">
        <p className="whitespace-pre-wrap text-[17px] font-bold leading-snug text-ink-primary">{answer}</p>
        {verdict && (
          <span className={`shrink-0 whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption font-semibold ${verdictToneClass(verdict)}`}>
            {verdict}
          </span>
        )}
        {percentile !== null && (
          <span className="shrink-0 whitespace-nowrap rounded-full border border-border-hairline bg-surface-base px-2.5 py-0.5 text-caption text-ink-secondary">
            하위 {Math.round(percentile * 100)}% 가격대
          </span>
        )}
      </div>

      {/* ② 비교 기준 칩(사다리 조건들) */}
      <div>
        <div className="flex flex-wrap gap-1.5">
          {chips.map((chip) => (
            <span
              key={chip.label}
              className={
                chip.active
                  ? 'rounded-full border border-brand-petrol px-2.5 py-1 text-caption text-brand-petrol'
                  : 'rounded-full border border-border-hairline px-2.5 py-1 text-caption text-ink-muted line-through'
              }
            >
              {chip.label}
            </span>
          ))}
        </div>
        <p className="mt-1.5 text-caption text-ink-muted">
          등록 매물 {criteria.sample_count}건과 비교 · {criteria.step > 0 ? criteria.desc : '기준 완화 없음'}
        </p>
      </div>

      {/* STEP3: 완화 사다리 발동 고지 — desc(가변 문자열) 뒤에 "로"/"으로" 조사를 직접 붙이면
          받침 유무에 따라 문법이 깨진다("해제(으)로"처럼 두 후보를 그대로 노출하는 사고를
          코드리뷰에서 실측). "기준으로"는 desc가 아니라 고정 명사 "기준"에 붙으므로 desc가
          무엇이든 항상 자연스럽다. */}
      {criteria.step > 0 && (
        <div className="rounded-lg bg-warn-amber-bg px-3 py-2 text-sm font-medium text-warn-amber-ink">
          {criteria.desc} 기준으로 넓혀 {criteria.sample_count}건과 비교했어요.
        </div>
      )}

      {/* ③ SVG 산점도 */}
      {hasChart ? (
        <MarketDiagnosisChart listing={listing} stats={stats} comps={comps} tabpfnPrice={tabpfn.price} />
      ) : (
        <p className="text-caption text-ink-muted">비교할 매물이 부족해 그래프를 표시할 수 없어요.</p>
      )}

      {/* ④ 통계 3칸 */}
      <div className="grid grid-cols-3 gap-2.5">
        <StatCell label="유사 매물 중앙값" value={stats ? formatPrice(stats.median) : '—'} />
        <StatCell
          label="모델 예측 적정가"
          value={tabpfn.price !== null ? formatPrice(tabpfn.price) : '표본 부족'}
          note={tabpfn.price === null ? tabpfn.note : undefined}
        />
        <StatCell label="이 매물" value={formatPrice(listing.price)} note={diffLabel ?? undefined} emphasis />
      </div>

      {/* ⑥ 각주 — 자동차365 참고선은 상위 결정으로 구현하지 않는다(실데이터 없음). */}
      <p className="text-caption text-ink-muted">
        적정가 예측: Built with PriorLabs-TabPFN · 분포: 등록 매물 {criteria.sample_count}건
      </p>
    </div>
  );
}
