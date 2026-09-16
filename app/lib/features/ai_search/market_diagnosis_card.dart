// 시세 진단 카드 — web MarketDiagnosis.tsx를 이식한 5단계 카드를 2026-09-14(DW-862)에
// 재구성했다. 숫자는 전부 SQL·TabPFN이 낸 값 그대로(재계산 금지), 통계값에만 만원 반올림
// (formatStatPrice), 매물 호가는 반올림 없이(wonText) 표시한다(web price.ts 경고 준수) —
// 이 원칙은 재구성 전과 동일하다.
//
// 재구성 요지: 예전엔 assistant 자유 서술(answer)을 헤드라인 자리에 그대로 넣었지만, 이제
// 헤드라인·한 문장 판정 둘 다 market_diagnosis.dart의 순수 함수(headlineText·
// resolveJudgementRatio·buildJudgementSentence)가 구조화된 값(tabpfn.quantiles·
// tabpfn.cdfAtPrice·percentile 등)만으로 만든다 — LLM 자유 서술에 기대던 숫자 표현을 없애
// "100대 중 90대" 같은 과신 표현이 카드에 섞일 여지 자체를 지운다. answer 파라미터는
// 호출부(ai_chat_screen.dart)가 여전히 넘기지만(콜사이트 변경은 범위 밖) 이 카드는 더 이상
// 쓰지 않는다.
//
// 2026-09-14 2차 개정(DW-885): 한 문장 판정이 배지(verdict, TabPFN 분위수 기준)와 다른
// 산출식(비교군 percentile)을 써서 어긋나던 결함을 수정 — tabpfn.cdfAtPrice(분위수 곡선
// 기준 누적 비율, verdict와 같은 산출식)가 있으면 그걸 우선 쓰고 없으면 percentile로
// 폴백한다(resolveJudgementRatio). 헤드라인 문구도 "이런 조건이면"→"비슷한 조건이면"으로
// 바뀌었다.
//
// 기존 통계·산점도·비교군 칩은 지우지 않고 ExpansionTile("자세히", 기본 닫힘) 안으로
// 옮겼다 — 초보 사용자가 한눈에 볼 정보(헤드라인·판정·타일 2개)와 더 볼 사람만 펼치는
// 근거를 분리한다.
//
// 2026-09-16 실기기 지적 A7: "자세히" 안의 비교 매물 목록(DW-884, buildCompsListView가
// 60건까지 나열하던 것)을 없앴다 — 점 그림(market_diagnosis_price_chart.dart)이 comps
// 전부를 이미 점으로 찍어 같은 정보를 보여주므로, 텍스트 목록은 접힘 영역만 길게 늘렸다.
// 칩·통계·산점도는 그대로 남는다.
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
    final judgementRatio = resolveJudgementRatio(data.tabpfn.cdfAtPrice, data.percentile);
    final sentence = showPercentileChip && judgementRatio != null ? buildJudgementSentence(judgementRatio) : null;
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
          verdict: data.verdict,
        ),
        const SizedBox(height: 12),

        // ④ 타일 2개 — 지금 올라온 비슷한 차의 중간 가격 / AI가 본 적정가. 비교 문구는
        // 하나만(타일 사이 아래 한 줄) 낸다 — 어느 타일이 기준인지 숫자를 두 번 안 보여줘도
        // "AI 적정가보다 N% 높음/낮음" 한 문장으로 충분하다.
        // ⚠️ Row 바로 위에 crossAxisAlignment.stretch를 못 쓰는 이유(무한 높이 컨테이너 —
        // 이 카드는 채팅 말풍선(ListView 안, 높이 미확정 컨테이너)에서 렌더된다)는 그대로다.
        // 대신 IntrinsicHeight로 Row를 감싸면 Row가 "자식 중 가장 큰 고유 높이"를 먼저 재서
        // Expanded 자식에 유한한 높이를 강제하므로, stretch를 써도 무한대(Infinity)가 전파되지
        // 않는다(실기기 지적 A6 — note가 한쪽에만 있으면 두 타일 높이가 달랐다).
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: _StatCell(
                  key: const Key('market_diagnosis_tile_sample'),
                  label: '지금 올라온 비슷한 차 ${data.criteria.sampleCount}대의 중간 가격',
                  value: stats != null ? formatStatPrice(stats.median) : '—',
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _StatCell(
                  key: const Key('market_diagnosis_tile_tabpfn'),
                  label: 'AI가 본 적정가',
                  value: data.tabpfn.price != null ? wonText(data.tabpfn.price!) : '표본 부족',
                  note: data.tabpfn.price == null ? data.tabpfn.note : null,
                  emphasis: true,
                ),
              ),
            ],
          ),
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
                  child: _StatsSummary(stats: stats),
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

/// 비교군 통계(최저·하위 25%·중앙값·상위 25%·최고) — 예전엔 한 줄 텍스트("비교군 통계 ·
/// 최저 … · 최고 …")라 폭이 좁으면 줄바꿈되며 겹쳤다(실기기 지적 A6). web MarketDiagnosis.tsx의
/// StatCell 5칸 그리드(grid-cols-5)와 같은 값·라벨 쌍을 쓰되, 폭 600dp 미만에서는 앱 전용으로
/// 세로 목록(라벨 왼쪽·값 오른쪽, 한 줄 고정)으로 접는다 — 그 폭에서 5칸을 욱여넣으면 숫자가
/// 다시 줄바꿈된다.
class _StatsSummary extends StatelessWidget {
  const _StatsSummary({required this.stats});
  final MarketDiagnosisStats stats;

  @override
  Widget build(BuildContext context) {
    final entries = [
      ('최저', stats.min),
      ('하위 25%', stats.q1),
      ('중앙값', stats.median),
      ('상위 25%', stats.q3),
      ('최고', stats.max),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= 600) {
          return Row(
            children: [
              for (var i = 0; i < entries.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: _StatGridCell(label: entries[i].$1, value: formatStatPrice(entries[i].$2)),
                ),
              ],
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < entries.length; i++) ...[
              if (i > 0) const SizedBox(height: 4),
              _StatListRow(label: entries[i].$1, value: formatStatPrice(entries[i].$2)),
            ],
          ],
        );
      },
    );
  }
}

class _StatGridCell extends StatelessWidget {
  const _StatGridCell({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.inkPrimary),
        ),
        Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: AppColors.inkMuted)),
      ],
    );
  }
}

class _StatListRow extends StatelessWidget {
  const _StatListRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.inkMuted)),
        const Spacer(),
        Text(
          value,
          maxLines: 1,
          softWrap: false,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.inkPrimary),
        ),
      ],
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({super.key, required this.label, required this.value, this.note, this.emphasis = false});

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
