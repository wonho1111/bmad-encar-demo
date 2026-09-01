// 다건 시세 진단 요약표 — web MarketDiagnosisTable.tsx 미러. marketDiagnoses(2건 이상)가
// 있을 때 ai_chat_screen.dart가 단건 카드(MarketDiagnosisCard) 대신 이 표를 렌더한다.
// 행: 매물(제조사·모델·연식·주행) · 가격 · 적정가(TabPFN) · 판정. 숫자는 전부 서버가 낸 값
// 그대로(MarketDiagnosisCard와 동일 원칙 — 재계산하지 않는다). 새 패키지(DataTable 등 대신
// 이미 Flutter core에 있는 Table 위젯) 없이 구현한다(A2).
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';

class MarketDiagnosisTable extends StatelessWidget {
  const MarketDiagnosisTable({super.key, required this.diagnoses});

  final List<MarketDiagnosisData> diagnoses;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('market_diagnosis_table'),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.borderHairline),
        borderRadius: BorderRadius.circular(8),
      ),
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Table(
          defaultColumnWidth: const IntrinsicColumnWidth(),
          border: TableBorder(
            horizontalInside: BorderSide(color: AppColors.borderHairline),
          ),
          children: [
            TableRow(
              decoration: const BoxDecoration(color: AppColors.surfaceRaised),
              children: [
                _headerCell('매물'),
                _headerCell('가격'),
                _headerCell('적정가'),
                _headerCell('판정'),
              ],
            ),
            for (final d in diagnoses)
              TableRow(
                children: [
                  _listingCell(d),
                  _bodyCell(
                    wonText(d.listing.price),
                    style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.priceEmphasis),
                  ),
                  _bodyCell(
                    d.tabpfn.price != null ? wonText(d.tabpfn.price!) : '표본 부족',
                    muted: d.tabpfn.price == null,
                  ),
                  _verdictCell(d),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _headerCell(String text) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(text, style: const TextStyle(fontSize: 12, color: AppColors.inkMuted)),
      );

  Widget _bodyCell(String text, {TextStyle? style, bool muted = false}) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          text,
          style: style ?? TextStyle(fontSize: 13, color: muted ? AppColors.inkMuted : AppColors.inkPrimary),
        ),
      );

  Widget _listingCell(MarketDiagnosisData d) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${d.listing.manufacturer} ${d.listing.model}',
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppColors.inkPrimary),
            ),
            Text(
              '${d.listing.year}년식 · ${formatManKm(d.listing.mileage)}',
              style: const TextStyle(fontSize: 11, color: AppColors.inkMuted),
            ),
          ],
        ),
      );

  Widget _verdictCell(MarketDiagnosisData d) {
    if (d.verdict == null) {
      return _bodyCell('—', muted: true);
    }
    Color bg;
    Color fg;
    if (d.verdict == '저렴') {
      bg = AppColors.trustGreenBg;
      fg = AppColors.trustGreenInk;
    } else if (d.verdict == '높음') {
      bg = AppColors.warnAmberBg;
      fg = AppColors.warnAmberInk;
    } else {
      bg = AppColors.surfaceBase;
      fg = AppColors.inkSecondary;
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(d.verdict!, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: fg)),
            if (d.verdictBasis == '적정가') ...[
              const SizedBox(width: 4),
              Text('(적정가 기준)', style: TextStyle(fontSize: 10, color: fg.withValues(alpha: 0.8))),
            ],
          ],
        ),
      ),
    );
  }
}
