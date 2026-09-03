// 다건 시세 진단 요약표 (2026-08-31, 사용자 승인 설계 변경) — market_diagnoses(SearchResponse의
// 신규 복수 필드)가 2건 이상일 때 ChatAssistant가 이 표를 렌더한다. 기존 단건 흐름
// (MarketDiagnosis + 산점도 차트 1개)은 그대로 두고, "여러 매물을 한 번에 진단"한 대화에서만
// 이 표로 갈아탄다 — 마지막 1건 차트만 덜렁 붙어 나머지 진단 결과가 안 보이던 혼란(사용자
// 실측 P2, 2026-08-31)을 없애기 위함이다.
//
// 행: 매물(모델·연식·주행) · 가격 · 적정가(TabPFN) · 판정 배지. 숫자는 전부 서버가 낸 값
// 그대로(MarketDiagnosis.tsx와 동일 원칙 — 재계산하지 않는다).
import { formatPrice } from '@/lib/price';
import { formatManKm, type MarketDiagnosisData } from './MarketDiagnosis';

function verdictBadgeClass(verdict: MarketDiagnosisData['verdict']): string {
  if (verdict === '저렴') return 'bg-trust-green-bg text-trust-green-ink';
  if (verdict === '높음') return 'bg-warn-amber-bg text-warn-amber-ink';
  return 'border border-border-hairline text-ink-secondary';
}

export default function MarketDiagnosisTable({ diagnoses }: { diagnoses: MarketDiagnosisData[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border-hairline">
      <table className="w-full min-w-[560px] text-sm">
        <thead>
          <tr className="border-b border-border-hairline bg-surface-raised text-left text-caption text-ink-muted">
            <th className="px-3 py-2 font-medium">매물</th>
            <th className="px-3 py-2 font-medium">가격</th>
            <th className="px-3 py-2 font-medium">적정가</th>
            <th className="px-3 py-2 font-medium">판정</th>
          </tr>
        </thead>
        <tbody>
          {diagnoses.map((d) => (
            <tr key={d.listing.id} className="border-b border-border-hairline last:border-0">
              <td className="px-3 py-2">
                <div className="font-medium text-ink-primary">
                  {d.listing.manufacturer} {d.listing.model}
                </div>
                <div className="text-caption text-ink-muted">
                  {d.listing.year}년식 · {formatManKm(d.listing.mileage)}
                </div>
              </td>
              <td className="px-3 py-2 font-semibold text-price-emphasis">{formatPrice(d.listing.price)}</td>
              <td className="px-3 py-2">
                {d.tabpfn.price !== null ? (
                  formatPrice(d.tabpfn.price)
                ) : (
                  <span className="text-caption text-ink-muted">표본 부족</span>
                )}
              </td>
              <td className="px-3 py-2">
                {d.verdict ? (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-semibold ${verdictBadgeClass(d.verdict)}`}
                  >
                    {d.verdict}
                    {d.verdict_basis === '적정가' && (
                      <span className="text-[10px] font-normal opacity-80">(적정가 기준)</span>
                    )}
                  </span>
                ) : (
                  <span className="text-caption text-ink-muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
