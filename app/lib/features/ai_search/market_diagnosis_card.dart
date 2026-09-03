// 시세 진단 카드(5단계) — web MarketDiagnosis.tsx의 표시 항목을 전부 미러(①~⑥). 상태 없는
// 표현용 위젯 — 숫자는 전부 SQL·TabPFN이 낸 값 그대로(재계산 금지), 통계값에만 만원 반올림
// (formatStatPrice), 매물 호가는 반올림 없이(wonText) 표시한다(web price.ts 경고 준수).
//
// AnswerText(웹의 개행·번호목록 서식) 이식은 이 작업 범위 밖이다 — 이 앱은 기존에도 assistant
// 답변을 plain Text로 그려왔다(ai_chat_screen.dart _MessageBubble), 이 카드의 헤드라인도 같은
// 관례를 따른다(A3 외과적 변경 — 관련 없는 포맷팅 기능을 새로 들여오지 않는다).
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';
import 'market_diagnosis_chart.dart';

class MarketDiagnosisCard extends StatelessWidget {
  const MarketDiagnosisCard({super.key, required this.data, required this.answer});

  final MarketDiagnosisData data;
  final String answer;

  @override
  Widget build(BuildContext context) {
    final listing = data.listing;
    final stats = data.stats;
    final chips = buildCriteriaChips(data);
    final hasChart = stats != null && data.comps.isNotEmpty;
    final verdictBadge = buildVerdictBadge(data.verdict, data.verdictBasis);
    final showPercentileChip = shouldShowPercentileChip(data.percentile, data.criteria.sampleCount);

    // 대상가와 유사매물 중앙값의 차이(④ 통계 3칸 세 번째 칸 보조 라벨) — web과 동일하게 판정
    // 단어를 붙이지 않고 부호 있는 %만 중립적으로 표기한다(배지 기준과 어긋날 수 있어서).
    String? diffLabel;
    if (stats != null && stats.median != 0) {
      final diffPct = ((listing.price - stats.median) / stats.median) * 100;
      final rounded = (diffPct * 10).round() / 10;
      if (rounded == 0) {
        diffLabel = '중앙값과 동일';
      } else if (rounded < 0) {
        diffLabel = '중앙값 대비 $rounded%';
      } else {
        diffLabel = '중앙값 대비 +$rounded%';
      }
    }

    return Column(
      key: const Key('market_diagnosis_card'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ① 판정 헤드라인(answer) + 배지 + 백분위 미니칩.
        Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          runSpacing: 4,
          children: [
            Text(
              answer,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: AppColors.inkPrimary),
            ),
            if (verdictBadge != null) _VerdictBadgeView(badge: verdictBadge, verdict: data.verdict),
            // 2026-09-03: '분위수'(예측 분포 5단) 추가 — web verdictBasisLabel 미러. '적정가'는 구 응답 호환.
            if (data.verdictBasis == '분위수')
              const Text('(예측 분포 기준)', style: TextStyle(fontSize: 12, color: AppColors.inkMuted)),
            if (data.verdictBasis == '적정가')
              const Text('(적정가 기준)', style: TextStyle(fontSize: 12, color: AppColors.inkMuted)),
            if (showPercentileChip)
              _OutlineTag(text: '하위 ${(data.percentile! * 100).round()}% 가격대'),
          ],
        ),
        const SizedBox(height: 12),

        // ② 비교 기준 칩(사다리 조건들) + 요약 문구.
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [for (final chip in chips) _CriteriaChipView(chip: chip)],
        ),
        const SizedBox(height: 6),
        Text(
          '등록 매물 ${data.criteria.sampleCount}건과 비교 · '
          '${data.criteria.step > 0 ? data.criteria.desc : '기준 완화 없음'}',
          style: const TextStyle(fontSize: 12, color: AppColors.inkMuted),
        ),

        // ⑤ 완화 사다리 발동 고지 — desc(가변 문자열) 뒤에 "기준으로"라는 고정 명사를 붙여
        // 조사 문법이 항상 자연스럽게 한다(web과 동일 이유).
        if (data.criteria.step > 0) ...[
          const SizedBox(height: 10),
          Container(
            key: const Key('market_diagnosis_relax_banner'),
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(color: AppColors.warnAmberBg, borderRadius: BorderRadius.circular(8)),
            child: Text(
              '${data.criteria.desc} 기준으로 넓혀 ${data.criteria.sampleCount}건과 비교했어요.',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.warnAmberInk),
            ),
          ),
        ],
        const SizedBox(height: 12),

        // ③ 산점도.
        if (hasChart)
          MarketDiagnosisChart(
            listing: listing,
            stats: stats,
            comps: data.comps,
            tabpfnPrice: data.tabpfn.price,
          )
        else
          const Text('비교할 매물이 부족해 그래프를 표시할 수 없어요.',
              style: TextStyle(fontSize: 12, color: AppColors.inkMuted)),
        const SizedBox(height: 12),

        // ④ 통계 3칸 — 유사 매물 중앙값(만원 반올림) / 모델 예측 적정가 / 이 매물(반올림 없음).
        // ⚠️ crossAxisAlignment.stretch를 쓰지 않는다 — 이 카드는 채팅 말풍선(ListView 안,
        // 높이 미확정 컨테이너)에서 렌더되므로 stretch가 Row 높이로 무한대(Infinity)를
        // 자식에 강제해 레이아웃이 깨진다(실측: RenderConstrainedBox `h=Infinity` 단언 실패).
        Row(
          children: [
            Expanded(
              child: _StatCell(
                label: '유사 매물 중앙값',
                value: stats != null ? formatStatPrice(stats.median) : '—',
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _StatCell(
                label: '모델 예측 적정가',
                value: data.tabpfn.price != null ? wonText(data.tabpfn.price!) : '표본 부족',
                note: data.tabpfn.price == null ? data.tabpfn.note : null,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _StatCell(
                label: '이 매물',
                value: wonText(listing.price),
                note: diffLabel,
                emphasis: true,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // ⑥ 각주 — 자동차365 참고선은 상위 결정으로 구현하지 않는다(실데이터 없음, web과 동일).
        Text(
          '적정가 예측: Built with PriorLabs-TabPFN · 분포: 등록 매물 ${data.criteria.sampleCount}건',
          style: const TextStyle(fontSize: 12, color: AppColors.inkMuted),
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
