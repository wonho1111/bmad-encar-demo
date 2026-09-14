// 시세 진단 카드 — web MarketDiagnosis.tsx를 이식한 5단계 카드를 2026-09-14(DW-862)에
// 재구성했다. 숫자는 전부 SQL·TabPFN이 낸 값 그대로(재계산 금지), 통계값에만 만원 반올림
// (formatStatPrice), 매물 호가는 반올림 없이(wonText) 표시한다(web price.ts 경고 준수) —
// 이 원칙은 재구성 전과 동일하다.
//
// 재구성 요지: 예전엔 assistant 자유 서술(answer)을 헤드라인 자리에 그대로 넣었지만, 이제
// 헤드라인·한 문장 판정 둘 다 market_diagnosis.dart의 순수 함수(headlineText·
// verdictSentence)가 구조화된 값(tabpfn.quantiles·percentile 등)만으로 만든다 — LLM 자유
// 서술에 기대던 숫자 표현을 없애 "100대 중 90대" 같은 과신 표현이 카드에 섞일 여지 자체를
// 지운다. answer 파라미터는 호출부(ai_chat_screen.dart)가 여전히 넘기지만(콜사이트 변경은
// 범위 밖) 이 카드는 더 이상 쓰지 않는다.
//
// 기존 통계·산점도·비교군 칩은 지우지 않고 ExpansionTile("자세히", 기본 닫힘) 안으로
// 옮겼다 — 초보 사용자가 한눈에 볼 정보(헤드라인·판정·타일 2개)와 더 볼 사람만 펼치는
// 근거를 분리한다.
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';
import 'market_diagnosis_chart.dart';
import 'market_diagnosis_price_chart.dart';

class MarketDiagnosisCard extends StatelessWidget {
  const MarketDiagnosisCard({super.key, required this.data, required this.answer});

  final MarketDiagnosisData data;
  final String answer;

  @override
  Widget build(BuildContext context) {
    final listing = data.listing;
    final stats = data.stats;
    final chips = buildCriteriaChips(data);
    final hasOldChart = stats != null && data.comps.isNotEmpty;
    final verdictBadge = buildVerdictBadge(data.verdict, data.verdictBasis);
    final showPercentileChip = shouldShowPercentileChip(data.percentile, data.criteria.sampleCount);
    final headline = headlineText(data);
    final sentence = verdictSentence(data.percentile);
    final compareLabel = tabpfnDiffLabel(listing.price, data.tabpfn.price);

    return Column(
      key: const Key('market_diagnosis_card'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ① 헤드라인 — "이런 조건이면 보통 A~B만원"(tabpfn.quantiles 우선, 없으면 stats 폴백).
        Text(
          headline ?? '비교할 시세 데이터가 부족해요',
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: AppColors.inkPrimary),
        ),
        const SizedBox(height: 6),

        // ② 한 문장 판정 + 기존 판정 배지(작게) + 기준 라벨 + 백분위 미니칩.
        Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          runSpacing: 4,
          children: [
            if (sentence != null)
              Text(sentence, style: const TextStyle(fontSize: 13, color: AppColors.inkSecondary)),
            if (verdictBadge != null) _VerdictBadgeView(badge: verdictBadge, verdict: data.verdict),
            // 2026-09-03: '분위수'(예측 분포 5단) 추가 — web verdictBasisLabel 미러. '적정가'는 구 응답 호환.
            if (data.verdictBasis == '분위수')
              const Text('(예측 분포 기준)', style: TextStyle(fontSize: 11, color: AppColors.inkMuted)),
            if (data.verdictBasis == '적정가')
              const Text('(적정가 기준)', style: TextStyle(fontSize: 11, color: AppColors.inkMuted)),
            if (showPercentileChip)
              _OutlineTag(text: '하위 ${(data.percentile! * 100).round()}% 가격대'),
          ],
        ),
        const SizedBox(height: 12),

        // ③ 그림 — AI 가격 곡선(quantiles) + 비슷한 차 실제 가격 점 + 이 매물 세로선.
        MarketDiagnosisPriceChart(
          listing: listing,
          stats: stats,
          comps: data.comps,
          quantiles: data.tabpfn.quantiles,
        ),
        const SizedBox(height: 12),

        // ④ 타일 2개 — 지금 올라온 비슷한 차의 중간 가격 / AI가 본 적정가. 비교 문구는
        // 하나만(타일 사이 아래 한 줄) 낸다 — 어느 타일이 기준인지 숫자를 두 번 안 보여줘도
        // "AI 적정가보다 N% 높음/낮음" 한 문장으로 충분하다.
        // ⚠️ crossAxisAlignment.stretch를 쓰지 않는다 — 이 카드는 채팅 말풍선(ListView 안,
        // 높이 미확정 컨테이너)에서 렌더되므로 stretch가 Row 높이로 무한대(Infinity)를
        // 자식에 강제해 레이아웃이 깨진다(실측: RenderConstrainedBox `h=Infinity` 단언 실패).
        Row(
          children: [
            Expanded(
              child: _StatCell(
                label: '지금 올라온 비슷한 차 ${data.criteria.sampleCount}대의 중간 가격',
                value: stats != null ? formatStatPrice(stats.median) : '—',
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _StatCell(
                label: 'AI가 본 적정가',
                value: data.tabpfn.price != null ? wonText(data.tabpfn.price!) : '표본 부족',
                note: data.tabpfn.price == null ? data.tabpfn.note : null,
                emphasis: true,
              ),
            ),
          ],
        ),
        if (compareLabel != null) ...[
          const SizedBox(height: 6),
          Text(compareLabel, style: const TextStyle(fontSize: 12, color: AppColors.inkMuted)),
        ],
        const SizedBox(height: 8),

        // ⑤ 자세히(접힘, 기본 닫힘) — 비교군 통계·완화 사다리 고지·기존 산점도·비교 매물 목록.
        Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            key: const Key('market_diagnosis_details'),
            tilePadding: EdgeInsets.zero,
            childrenPadding: const EdgeInsets.only(top: 4),
            initiallyExpanded: false,
            title: const Text('자세히', style: TextStyle(fontSize: 13, color: AppColors.inkSecondary)),
            children: [
              if (stats != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    '비교군 통계 · 최저 ${formatStatPrice(stats.min)} · 1분위 ${formatStatPrice(stats.q1)} · '
                    '중앙값 ${formatStatPrice(stats.median)} · 3분위 ${formatStatPrice(stats.q3)} · '
                    '최고 ${formatStatPrice(stats.max)}',
                    style: const TextStyle(fontSize: 12, color: AppColors.inkMuted),
                  ),
                ),

              // 완화 사다리 발동 고지 — desc(가변 문자열) 뒤에 "기준으로"라는 고정 명사를 붙여
              // 조사 문법이 항상 자연스럽게 한다(web과 동일 이유). step==0이면 아무 문구도
              // 내지 않는다("기준 완화 없음" 같은 부정형 문구는 재구성에서 없앴다).
              if (data.criteria.step > 0)
                Container(
                  key: const Key('market_diagnosis_relax_banner'),
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration:
                      BoxDecoration(color: AppColors.warnAmberBg, borderRadius: BorderRadius.circular(8)),
                  child: Text(
                    '${data.criteria.desc} 기준으로 넓혀 ${data.criteria.sampleCount}건과 비교했어요.',
                    style:
                        const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.warnAmberInk),
                  ),
                ),

              const Text('이런 차와 비교했어요:', style: TextStyle(fontSize: 12, color: AppColors.inkMuted)),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [for (final chip in chips) _CriteriaChipView(chip: chip)],
              ),
              const SizedBox(height: 12),

              if (hasOldChart)
                MarketDiagnosisChart(
                  listing: listing,
                  stats: stats,
                  comps: data.comps,
                  tabpfnPrice: data.tabpfn.price,
                )
              else
                const Text('비교할 매물이 부족해 그래프를 표시할 수 없어요.',
                    style: TextStyle(fontSize: 12, color: AppColors.inkMuted)),

              if (data.comps.isNotEmpty) ...[
                const SizedBox(height: 12),
                const Text('비교 매물 목록',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.inkSecondary)),
                const SizedBox(height: 6),
                for (final c in data.comps)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Text(
                      '${c.model} · ${c.year}년식 · ${formatManKm(c.mileage)} · ${wonText(c.price)}',
                      style: const TextStyle(fontSize: 12, color: AppColors.inkMuted),
                    ),
                  ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 4),

        // ⑥ 각주 — "호가 기준" 소문구 + TabPFN 표기(작은 글씨). 자동차365 참고선은 상위
        // 결정으로 구현하지 않는다(실데이터 없음, web과 동일).
        const Text(
          '호가 기준 · 적정가 예측: Built with PriorLabs-TabPFN',
          style: TextStyle(fontSize: 12, color: AppColors.inkMuted),
        ),
      ],
    );
  }
}

class _VerdictBadgeView extends StatelessWidget {
  const _VerdictBadgeView({required this.badge, required this.verdict});

  final VerdictBadge badge;
  final String? verdict;

  @override
  Widget build(BuildContext context) {
    final isVerdictTone = badge.tone == 'verdict';
    Color? background;
    Color foreground;
    if (isVerdictTone) {
      if (verdict == '저렴' || verdict == '다소 저렴') {
        background = AppColors.trustGreenBg;
        foreground = AppColors.trustGreenInk;
      } else if (verdict == '높음' || verdict == '다소 높음') {
        background = AppColors.warnAmberBg;
        foreground = AppColors.warnAmberInk;
      } else {
        background = null; // '적정' 등 그 외 값 — web도 border만(채움 없음).
        foreground = AppColors.inkSecondary;
      }
    } else {
      background = null;
      foreground = AppColors.inkSecondary;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        color: background,
        border: background == null ? Border.all(color: AppColors.borderHairline) : null,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(badge.text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: foreground)),
    );
  }
}

class _OutlineTag extends StatelessWidget {
  const _OutlineTag({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.borderHairline),
        color: AppColors.surfaceBase,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(text, style: const TextStyle(fontSize: 12, color: AppColors.inkSecondary)),
    );
  }
}

class _CriteriaChipView extends StatelessWidget {
  const _CriteriaChipView({required this.chip});
  final CriteriaChip chip;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        border: Border.all(color: chip.active ? AppColors.brandPetrol : AppColors.borderHairline),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        chip.label,
        style: TextStyle(
          fontSize: 12,
          color: chip.active ? AppColors.brandPetrol : AppColors.inkMuted,
          decoration: chip.active ? TextDecoration.none : TextDecoration.lineThrough,
        ),
      ),
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({required this.label, required this.value, this.note, this.emphasis = false});

  final String label;
  final String value;
  final String? note;
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.borderHairline),
        borderRadius: BorderRadius.circular(10),
        color: AppColors.surfaceBase,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: emphasis ? AppColors.priceEmphasis : AppColors.inkPrimary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            note != null ? '$label · $note' : label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, color: AppColors.inkMuted),
          ),
        ],
      ),
    );
  }
}
