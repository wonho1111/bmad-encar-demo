// 시세 진단 렌더 블록 — ChatAssistant 어시스턴트 말풍선 안에서 SearchResponse.market_diagnosis가
// 있을 때만 그려지는 컴포넌트(상세 페이지 "AI 시세 진단" 버튼과 AI 검색 응답이 같은 컴포넌트를
// 공유 — 버튼(MarketDiagnosisButton.tsx)은 /ai로 이동시켜 이 컴포넌트를 그리는 같은 검색 흐름을
// 1회 자동 실행한다). 상태 없는 표현용 컴포넌트.
//
// 데이터 출처: api/app/market_price.py diagnose()의 반환 dict 그대로 — 숫자는 전부 SQL·TabPFN이
// 낸 값이고(그 파일 모듈 docstring: "수치는 전부 SQL/모델이 낸다"), 이 컴포넌트는 그 값을 배치·
// 표시만 한다(재계산 금지). 유일한 예외는 아래 RUNG_DISPLAY 표 — 완화 사다리 단계별로 "어떤 조건이
// 해제됐는지"를 칩 취소선으로 보여주기 위한 **표시 전용** 복제본이다(실제 필터링에는 관여하지
// 않는다 — 정본은 api/app/market_price.py의 LADDER, 그 표가 바뀌면 이 표도 함께 바꿔야 한다).
//
// 2026-09-14 재구성(DW-862, 사용자 결정 2026-09-05): 카드가 "비교군 9건과 비교, 하위 22%, 중앙값,
// 분위수" 같은 산출 과정을 예측 내용보다 앞세운다는 시연 피드백을 반영 — 헤드라인·판정 문장을
// LLM이 지어내는 문장(answer) 대신 이 파일의 결정론적 텍스트로 바꾸고, 기계적 통계·산점도·비교
// 매물 목록은 기본 닫힘 "자세히" 영역으로 옮겼다. answer prop은 ChatAssistant 호출 시그니처
// 호환을 위해 타입에는 남기되(그쪽 코드는 손대지 않는다) 더는 화면에 그리지 않는다 — LLM 답변이
// 바로 그 "기계적 정보 나열"을 그대로 옮겨 말하곤 했기 때문이다(agent_tools.py
// _format_market_diagnosis가 도구 결과를 중앙값·백분위·범위 숫자로 먼저 요약해 LLM에 준다).
import { formatPrice, formatStatPrice } from '@/lib/price';
import MarketDiagnosisChart from './MarketDiagnosisChart';
import MarketDiagnosisPriceChart from './MarketDiagnosisPriceChart';

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
  // 2026-09-03: 예측 분포 5단(다소 저렴/다소 높음 추가, api/app/market_price.py _verdict_by_quantiles).
  verdict: '저렴' | '다소 저렴' | '적정' | '다소 높음' | '높음' | null;
  // 판정 기준(2026-08-31 추가, additive) — tabpfn 분위수가 있으면 "분위수"(예측 분포 5단,
  // 2026-09-03 전환; 구 응답의 "적정가"도 라벨만 다르게 계속 받는다), 없으면 "사분위"(q1/q3
  // 폴백). verdict가 null이고 비교군 자체가 없으면(sample_count 0) 이 값도 null. verdict가
  // null인데 비교군이 1~2건(소표본)이면 "표본 부족"(2026-08-31 F4 수정 — 표본이 너무 적어
  // 판정을 보류한다, api/app/market_price.py MIN_VERDICT_SAMPLE).
  verdict_basis: '분위수' | '적정가' | '사분위' | '표본 부족' | null;
  // quantiles: TabPFN 예측 분포의 분위수(원 단위, 2026-09-03 additive) — 표본 부족·미설치면 null.
  // cdf_at_price: 분위수 곡선 위에서 이 매물 price의 누적 비율(0~1, 2026-09-14 DW-885 additive) —
  // verdict(배지)와 같은 산출식이라 한 문장 판정도 이 값을 우선 쓴다(resolveJudgementRatio 참조).
  // quantiles가 없으면(TabPFN 미예측) 이 값도 null.
  tabpfn: {
    price: number | null;
    note: string;
    quantiles?: { q10: number; q25: number; q50: number; q75: number; q90: number } | null;
    cdf_at_price?: number | null;
  };
  comps: MarketDiagnosisComp[];
};

// 완화 사다리 표시 전용 복제본(정본: api/app/market_price.py LADDER) — 취소선 칩 판단에만 쓴다.
//
// 2026-08-31 개정: 백엔드 LADDER에 "트림 해제(동일 세대 계열)" 단이 step3으로 끼어들면서
// 이후 단이 한 칸씩 밀렸다(구 step3 "세대 해제"→4, 구 step4 "연료 해제"→5). step3은 모델
// 문자열이 더는 완전 일치가 아니므로(family 접두 매칭) modelExact=false — 세대 해제(step4)와
// 칩 표시상으론 동일하고, 실제 차이(트림만 확장 vs 세대까지 확장)는 criteria.desc 배지
// 문구로만 구분된다.
const RUNG_DISPLAY: Record<
  number,
  { yearBand: number; kmBand: number; fuelActive: boolean; accidentActive: boolean; modelExact: boolean }
> = {
  0: { yearBand: 2, kmBand: 30_000, fuelActive: true, accidentActive: true, modelExact: true },
  1: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: true, modelExact: true },
  2: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: false, modelExact: true },
  3: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: false, modelExact: false },
  4: { yearBand: 3, kmBand: 50_000, fuelActive: true, accidentActive: false, modelExact: false },
  5: { yearBand: 3, kmBand: 50_000, fuelActive: false, accidentActive: false, modelExact: false },
};

/** 주행거리를 "3.3만km" 식 만 단위로 표시한다(정수면 "3만km", 소수면 소수 1자리). */
export function formatManKm(km: number): string {
  const man = Math.round((km / 10_000) * 10) / 10;
  return `${Number.isInteger(man) ? man : man.toFixed(1)}만km`;
}

export type CriteriaChip = { label: string; active: boolean };

/** 비교 기준 칩(접힘 영역) 목록을 만든다 — target 속성 + 현재 사다리 단계(criteria.step)의 활성 조건.
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

// 2026-08-31 개정(F4, 소표본 과신 판정): 배지 대신 무엇을 보여줄지 결정하는 순수 함수 —
// DOM 없이 단위테스트로 고정한다(MarketDiagnosis.test.ts, buildCriteriaChips와 동일 관례).
export type VerdictBadge = { text: string; tone: 'verdict' | 'neutral' } | null;

export function buildVerdictBadge(
  verdict: MarketDiagnosisData['verdict'],
  verdictBasis: MarketDiagnosisData['verdict_basis'],
): VerdictBadge {
  if (verdict) return { text: verdict, tone: 'verdict' };
  if (verdictBasis === '표본 부족') return { text: '표본 부족 — 판정 보류', tone: 'neutral' };
  return null;
}

// 판정 문장(백분위 기반)을 보여줄지 여부 — 표본이 MIN_VERDICT_SAMPLE(3, 백엔드와 동일 기준)
// 미만이면 숨긴다(비교군 1~2건의 백분위는 verdict와 마찬가지로 판정 근거가 못 된다, F4).
const MIN_PERCENTILE_SAMPLE = 3;

export function shouldShowPercentileChip(percentile: number | null, sampleCount: number): boolean {
  return percentile !== null && sampleCount >= MIN_PERCENTILE_SAMPLE;
}

// 판정 기준 보조 라벨 — 배지 옆에 "(무엇 기준)"을 붙인다. 순수 함수로 두고 단위테스트로 고정
// (MarketDiagnosis.test.ts). 2026-09-03: '분위수'(예측 분포 5단) 추가, '적정가'는 구 응답 호환.
export function verdictBasisLabel(verdictBasis: MarketDiagnosisData['verdict_basis']): string | null {
  if (verdictBasis === '분위수') return '(예측 분포 기준)';
  if (verdictBasis === '적정가') return '(적정가 기준)';
  return null;
}

function verdictToneClass(verdict: MarketDiagnosisData['verdict']): string {
  if (verdict === '저렴' || verdict === '다소 저렴') return 'bg-trust-green-bg text-trust-green-ink';
  if (verdict === '높음' || verdict === '다소 높음') return 'bg-warn-amber-bg text-warn-amber-ink';
  return 'border border-border-hairline text-ink-secondary';
}

// 헤드라인(①) 범위 — tabpfn 분위수(q25~q75)가 있으면 그 값, 없으면 비교군 사분위(q1~q3)로
// 대체한다(approximate=true, "비슷한 차 실제 호가 기준" 소문구를 붙이라는 신호). 순수 함수
// (단위테스트 대상).
export type PriceRange = { low: number; high: number; approximate: boolean };

export function buildPriceRange(data: MarketDiagnosisData): PriceRange | null {
  const q = data.tabpfn.quantiles;
  if (q) return { low: q.q25, high: q.q75, approximate: false };
  if (data.stats) return { low: data.stats.q1, high: data.stats.q3, approximate: true };
  return null;
}

function toManString(won: number): string {
  return Math.round(won / 10_000).toLocaleString('ko-KR');
}

export function formatHeadline(range: PriceRange): string {
  return `비슷한 조건이면 보통 ${toManString(range.low)}~${toManString(range.high)}만원`;
}

// 한 문장 판정(②) — 비율을 "열에 N(한글 수사)이 이 매물보다 쌉니다" 형태로 푼다. 실제 비교군 건수
// (예: "100대 중 90대")를 쓰지 않는다 — sample_count가 작을 때(예: 9건) 그 숫자를 그대로 말하면
// 표본이 작다는 인상을 주고, 사용자가 실제 대수로 오해하기 쉽다(DW-862). "열"은 항상 10으로 고정한
// 비유 단위다. 순수 함수(단위테스트 대상) — 비율은 호출부에서 resolveJudgementRatio·
// shouldShowPercentileChip으로 먼저 걸러진 값만 넘긴다.
const KOREAN_COUNT = ['', '하나', '둘', '셋', '넷', '다섯', '여섯', '일곱', '여덟', '아홉'];

// 2026-09-14 개정(DW-885, 운영 실측): 판정 배지(verdict, 분위수 5단)와 이 문장이 서로 다른
// 산출식(문장은 비교군 percentile, 배지는 TabPFN 분위수)을 써서 어긋났다 — 배지는 "적정"인데
// 문장은 "열에 여덟이 더 쌉니다" 같은 사례가 실측됐다. tabpfn.cdf_at_price(분위수 곡선 위에서
// verdict와 같은 방식으로 구한 누적 비율)가 있으면 그걸 우선 쓰고, 없으면(TabPFN 미예측) 종전
// percentile로 폴백한다. 순수 함수(단위테스트 대상).
export function resolveJudgementRatio(
  cdfAtPrice: number | null | undefined,
  percentile: number | null,
): number | null {
  if (cdfAtPrice !== null && cdfAtPrice !== undefined) return cdfAtPrice;
  return percentile;
}

export function buildJudgementSentence(ratio: number): string {
  const n = Math.round(Math.max(0, Math.min(1, ratio)) * 10);
  if (n <= 0) return 'AI 예상으로는 비슷한 조건의 차 중 이 매물보다 싼 차가 거의 없습니다.';
  if (n >= 10) return 'AI 예상으로는 비슷한 조건의 차 중 이 매물보다 싼 차가 거의 전부입니다.';
  // "열에 아홉" 꼴(사용자 확정 문구 2026-09-05). "열 대 중 N대"는 실제 대수로 읽혀 금지 — E2E 실측(2026-09-14)에서 걸림.
  return `AI 예상으로는 비슷한 조건의 차 열에 ${KOREAN_COUNT[n]}${n === 1 ? '가' : '이'} 이 매물보다 쌉니다.`;
}

// 타일 2개 아래 백분율 비교(④) — 기준은 항상 tabpfn.price(모델 예측 적정가) 하나뿐이다. 순수 함수.
export function buildTabpfnDiffLabel(listingPrice: number, tabpfnPrice: number | null): string | null {
  if (tabpfnPrice === null || tabpfnPrice === 0) return null;
  const diffPct = Math.round(((listingPrice - tabpfnPrice) / tabpfnPrice) * 100);
  if (diffPct === 0) return 'AI 적정가와 거의 같아요';
  return diffPct > 0 ? `AI 적정가보다 ${diffPct}% 높음` : `AI 적정가보다 ${Math.abs(diffPct)}% 낮음`;
}

// "자세히" 비교 매물 목록(⑤) 상한 — 점(그림)은 comps 전부 찍지만(MarketDiagnosisPriceChart),
// 목록은 줄마다 텍스트라 MAX_COMPS(API, 최대 500건)를 그대로 나열하면 접힘 영역이 지나치게
// 길어진다(2026-09-14 DW-884, 운영 실측). 60건까지만 보여주고 나머지는 "외 N대" 한 줄로 요약한다.
const MAX_COMPS_LIST = 60;

export function buildCompsListView(comps: MarketDiagnosisComp[]): {
  shown: MarketDiagnosisComp[];
  moreCount: number;
} {
  if (comps.length <= MAX_COMPS_LIST) return { shown: comps, moreCount: 0 };
  return { shown: comps.slice(0, MAX_COMPS_LIST), moreCount: comps.length - MAX_COMPS_LIST };
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

// answer(LLM 자유 문장)는 더는 화면에 그리지 않지만(위 파일 상단 코멘트), ChatAssistant가 여전히
// 이 필드를 싣고 호출하므로 타입에는 남겨 시그니처를 맞춘다(그쪽 코드는 이 작업 범위 밖).
export default function MarketDiagnosis({ data }: { data: MarketDiagnosisData; answer: string }) {
  const { listing, criteria, stats, percentile, verdict, tabpfn, comps } = data;
  const chips = buildCriteriaChips(data);
  const verdictBadge = buildVerdictBadge(verdict, data.verdict_basis);
  const basisLabel = verdictBasisLabel(data.verdict_basis);
  const showJudgement = shouldShowPercentileChip(percentile, criteria.sample_count);
  const judgementRatio = resolveJudgementRatio(tabpfn.cdf_at_price, percentile);
  const priceRange = buildPriceRange(data);
  const tabpfnDiffLabel = buildTabpfnDiffLabel(listing.price, tabpfn.price);
  const hasChart = stats !== null || !!tabpfn.quantiles;
  const compsListView = buildCompsListView(comps);

  return (
    <div className="flex w-full flex-col gap-4">
      {/* ① 헤드라인 — 적정가 범위(예측 분포 있으면 q25~q75, 없으면 비교군 사분위) */}
      <div>
        {priceRange ? (
          <>
            <p className="text-[17px] font-bold leading-snug text-ink-primary">{formatHeadline(priceRange)}</p>
            {priceRange.approximate && (
              <p className="mt-0.5 text-caption text-ink-muted">비슷한 차 실제 호가 기준</p>
            )}
          </>
        ) : (
          <p className="text-[17px] font-bold leading-snug text-ink-primary">
            비슷한 조건의 매물이 부족해 가격대를 계산할 수 없어요.
          </p>
        )}
      </div>

      {/* ② 한 문장 판정 + 기존 판정 배지(작게) */}
      <div className="flex flex-wrap items-center gap-2">
        {showJudgement && judgementRatio !== null && (
          <p className="text-sm font-medium text-ink-primary">{buildJudgementSentence(judgementRatio)}</p>
        )}
        {verdictBadge && (
          <span
            className={`shrink-0 whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption font-semibold ${
              verdictBadge.tone === 'verdict'
                ? verdictToneClass(verdict)
                : 'border border-border-hairline text-ink-secondary'
            }`}
          >
            {verdictBadge.text}
          </span>
        )}
        {basisLabel && (
          <span className="shrink-0 whitespace-nowrap text-caption text-ink-muted">{basisLabel}</span>
        )}
      </div>

      {/* ③ 가격 축 그림 — AI 가격 곡선(있으면) + 비슷한 차 실제 가격 점 + 이 매물 세로선 */}
      {hasChart ? (
        <MarketDiagnosisPriceChart
          listingPrice={listing.price}
          stats={stats}
          comps={comps}
          quantiles={tabpfn.quantiles ?? null}
        />
      ) : (
        <p className="text-caption text-ink-muted">비교할 매물이 부족해 그래프를 표시할 수 없어요.</p>
      )}

      {/* ④ 타일 2개 + 적정가 대비 백분율(하나만) */}
      <div className="grid grid-cols-2 gap-2.5">
        <StatCell
          label={`지금 올라온 비슷한 차 ${criteria.sample_count}대의 중간 가격`}
          value={stats ? formatStatPrice(stats.median) : '—'}
        />
        <StatCell
          label="AI가 본 적정가"
          value={tabpfn.price !== null ? formatPrice(tabpfn.price) : '표본 부족'}
          note={tabpfn.price === null ? tabpfn.note : undefined}
        />
      </div>
      {tabpfnDiffLabel && <p className="text-caption text-ink-secondary">{tabpfnDiffLabel}</p>}

      {/* ⑤ 접힘 영역(기본 닫힘) — 기존 비교군 통계·사다리 단계·산점도·비교 매물 목록 */}
      <details className="rounded-lg border border-border-hairline">
        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-ink-secondary">
          자세히
        </summary>
        <div className="flex flex-col gap-3 border-t border-border-hairline px-3 py-3">
          {criteria.step > 0 && (
            <div className="rounded-lg bg-warn-amber-bg px-3 py-2 text-sm font-medium text-warn-amber-ink">
              {criteria.desc} 기준으로 넓혀 {criteria.sample_count}건과 비교했어요.
            </div>
          )}

          <div>
            <p className="text-caption text-ink-muted">이런 차와 비교했어요:</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
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
          </div>

          {stats && (
            <div className="grid grid-cols-5 gap-1.5">
              <StatCell label="최저" value={formatStatPrice(stats.min)} />
              <StatCell label="하위 25%" value={formatStatPrice(stats.q1)} />
              <StatCell label="중앙값" value={formatStatPrice(stats.median)} />
              <StatCell label="상위 25%" value={formatStatPrice(stats.q3)} />
              <StatCell label="최고" value={formatStatPrice(stats.max)} />
            </div>
          )}

          {stats && comps.length > 0 && (
            <MarketDiagnosisChart listing={listing} stats={stats} comps={comps} tabpfnPrice={tabpfn.price} />
          )}

          {comps.length > 0 && (
            <ul className="flex flex-col gap-1 text-caption text-ink-secondary">
              {compsListView.shown.map((c) => (
                <li key={c.id}>
                  {c.model} {c.year}년식 · {formatManKm(c.mileage)} · {formatPrice(c.price)}
                </li>
              ))}
              {compsListView.moreCount > 0 && <li>외 {compsListView.moreCount}대</li>}
            </ul>
          )}
        </div>
      </details>

      {/* ⑥ 각주 */}
      <p className="text-caption text-ink-muted">
        적정가 예측: TabPFN 모델 · 비교 매물은 호가(등록가) 기준
      </p>
    </div>
  );
}
