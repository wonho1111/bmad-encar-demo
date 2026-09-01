// 시세 진단 산점도(③) — web MarketDiagnosisChart.tsx(SVG)의 좌표 계산을 그대로 이식한
// CustomPainter(새 패키지 추가 금지, A2). 목업의 고정 뷰박스(640×320)를 논리 좌표계로 두고
// canvas.scale로 실제 위젯 크기에 맞춘다(SVG viewBox와 동일한 스케일링 원리).
//
// 색은 app_theme.dart AppColors를 쓴다(web이 globals.css 변수를 쓰는 것과 같은 원칙 — 새
// 팔레트를 만들지 않는다). 애니메이션·툴팁 등 인터랙션은 넣지 않는다(웹도 정적 SVG, 과설계 금지).
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';

const double _viewW = 640;
const double _viewH = 320;
const double _x0 = 60;
const double _x1 = 610;
const double _yTop = 20;
const double _yBottom = 260;

/// 값을 step 단위로 올림/내림한다(축 눈금을 보기 좋은 자리에 맞추기 위함). web roundUpTo/
/// roundDownTo 미러.
int _roundUpTo(num value, int step) => (value / step).ceil() * step;
int _roundDownTo(num value, int step) => (value / step).floor() * step;

/// 시세 진단 산점도 위젯 — AspectRatio 2:1(640:320)로 화면 폭에 반응한다.
class MarketDiagnosisChart extends StatelessWidget {
  const MarketDiagnosisChart({
    super.key,
    required this.listing,
    required this.stats,
    required this.comps,
    required this.tabpfnPrice,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats stats;
  final List<MarketDiagnosisComp> comps;
  final int? tabpfnPrice;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: _viewW / _viewH,
      child: CustomPaint(
        size: Size.infinite,
        painter: _MarketDiagnosisChartPainter(
          listing: listing,
          stats: stats,
          comps: comps,
          tabpfnPrice: tabpfnPrice,
        ),
      ),
    );
  }
}

class _MarketDiagnosisChartPainter extends CustomPainter {
  _MarketDiagnosisChartPainter({
    required this.listing,
    required this.stats,
    required this.comps,
    required this.tabpfnPrice,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats stats;
  final List<MarketDiagnosisComp> comps;
  final int? tabpfnPrice;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || size.height <= 0) return;
    final sx = size.width / _viewW;
    final sy = size.height / _viewH;

    final mileages = [...comps.map((c) => c.mileage), listing.mileage];
    final prices = [...comps.map((c) => c.price), listing.price, stats.min, stats.max];
    if (tabpfnPrice != null) prices.add(tabpfnPrice!);

    final kmMax = math.max(_roundUpTo(mileages.reduce(math.max) * 1.1, 10000), 10000);
    final priceMin = math.max(0, _roundDownTo(prices.reduce(math.min) * 0.95, 1000000));
    final priceMaxRaw = _roundUpTo(prices.reduce(math.max) * 1.05, 1000000);
    final priceMax = priceMaxRaw > priceMin ? priceMaxRaw : priceMin + 1000000;

    double xScale(num km) => _x0 + (km / kmMax) * (_x1 - _x0);
    double yScale(num price) =>
        _yTop + ((priceMax - price) / (priceMax - priceMin)) * (_yBottom - _yTop);

    canvas.save();
    canvas.scale(sx, sy);

    final axisPaint = Paint()
      ..color = AppColors.borderHairline
      ..strokeWidth = 1;
    canvas.drawLine(const Offset(_x0, _yBottom), const Offset(_x1, _yBottom), axisPaint);
    canvas.drawLine(const Offset(_x0, _yTop), const Offset(_x0, _yBottom), axisPaint);

    // x축 눈금(5개) + "주행거리 (km)" 라벨.
    for (var i = 0; i < 5; i++) {
      final t = (kmMax / 4 * i).round();
      _drawText(
        canvas,
        '${thousands((t / 10000).round())}만',
        Offset(xScale(t), _yBottom + 16),
        align: TextAlign.center,
        fontSize: 11,
        color: AppColors.inkMuted,
      );
    }
    _drawText(
      canvas,
      '주행거리 (km)',
      const Offset((_x0 + _x1) / 2, _viewH - 6),
      align: TextAlign.center,
      fontSize: 11,
      color: AppColors.inkMuted,
    );

    // y축 눈금 + 그리드(5개).
    final gridPaint = Paint()
      ..color = AppColors.borderHairline.withValues(alpha: 0.5)
      ..strokeWidth = 0.5;
    for (var i = 0; i < 5; i++) {
      final p = priceMin + (priceMax - priceMin) / 4 * i;
      final y = yScale(p);
      _drawText(
        canvas,
        '${thousands((p / 10000).round())}만',
        Offset(_x0 - 8, y),
        align: TextAlign.right,
        fontSize: 11,
        color: AppColors.inkMuted,
      );
      canvas.drawLine(Offset(_x0, y), Offset(_x1, y), gridPaint);
    }

    // 사분위 밴드(q1~q3) — 연한 채움.
    final bandPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.06);
    final bandTop = yScale(stats.q3);
    final bandBottom = yScale(stats.q1);
    canvas.drawRect(
      Rect.fromLTWH(_x0, bandTop, _x1 - _x0, math.max(bandBottom - bandTop, 0)),
      bandPaint,
    );

    // 중앙값 점선 + 라벨.
    _drawDashedLine(
      canvas,
      Offset(_x0, yScale(stats.median)),
      Offset(_x1, yScale(stats.median)),
      AppColors.brandPetrol,
      1.5,
      const [5, 4],
    );
    _drawText(
      canvas,
      '중앙값 ${thousands((stats.median / 10000).round())}만',
      Offset(_x1 - 4, yScale(stats.median) - 6),
      align: TextAlign.right,
      fontSize: 11,
      color: AppColors.brandPetrol,
    );

    // 비교군 점들(반투명).
    final compPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.55);
    for (final c in comps) {
      canvas.drawCircle(Offset(xScale(c.mileage), yScale(c.price)), 4.5, compPaint);
    }

    // 대상 매물 ↔ TabPFN 예측 연결 점선.
    if (tabpfnPrice != null) {
      _drawDashedLine(
        canvas,
        Offset(xScale(listing.mileage), yScale(listing.price)),
        Offset(xScale(listing.mileage), yScale(tabpfnPrice!)),
        AppColors.inkMuted,
        1,
        const [2, 2],
      );
    }

    // 대상 매물 마커(halo + 점) + 라벨.
    final targetCenter = Offset(xScale(listing.mileage), yScale(listing.price));
    canvas.drawCircle(targetCenter, 11, Paint()..color = AppColors.priceEmphasis.withValues(alpha: 0.18));
    canvas.drawCircle(targetCenter, 7, Paint()..color = AppColors.priceEmphasis);
    _drawText(
      canvas,
      '이 매물 ${thousands((listing.price / 10000).round())}만',
      targetCenter + const Offset(11, 4),
      align: TextAlign.left,
      fontSize: 11,
      fontWeight: FontWeight.bold,
      color: AppColors.priceEmphasis,
    );

    // TabPFN 예측 다이아몬드 + 라벨.
    if (tabpfnPrice != null) {
      final dx = xScale(listing.mileage);
      final dy = yScale(tabpfnPrice!);
      const s = 6.5;
      final diamond = Path()
        ..moveTo(dx, dy - s)
        ..lineTo(dx + s, dy)
        ..lineTo(dx, dy + s)
        ..lineTo(dx - s, dy)
        ..close();
      canvas.drawPath(diamond, Paint()..color = AppColors.brandPetrolStrong);
      _drawText(
        canvas,
        '적정가 예측 ${thousands((tabpfnPrice! / 10000).round())}만',
        Offset(dx + 11, dy - 6),
        align: TextAlign.left,
        fontSize: 11,
        fontWeight: FontWeight.bold,
        color: AppColors.brandPetrolStrong,
      );
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _MarketDiagnosisChartPainter oldDelegate) {
    return oldDelegate.listing != listing ||
        oldDelegate.stats != stats ||
        oldDelegate.comps != comps ||
        oldDelegate.tabpfnPrice != tabpfnPrice;
  }
}

/// SVG의 text-anchor(start/middle/end)를 흉내낸 텍스트 드로잉 — Canvas는 기본 좌상단 기준이라
/// 정렬을 직접 계산한다. 세로 위치는 baseline 근사(피그마 수준 정밀도는 필요 없다 — 정적 카드,
/// 애니메이션·픽셀 완전일치 요구 없음).
void _drawText(
  Canvas canvas,
  String text,
  Offset anchor, {
  required TextAlign align,
  required double fontSize,
  required Color color,
  FontWeight fontWeight = FontWeight.normal,
}) {
  final painter = TextPainter(
    text: TextSpan(text: text, style: TextStyle(fontSize: fontSize, color: color, fontWeight: fontWeight)),
    textDirection: TextDirection.ltr,
  )..layout();

  double dx;
  switch (align) {
    case TextAlign.right:
      dx = anchor.dx - painter.width;
      break;
    case TextAlign.center:
      dx = anchor.dx - painter.width / 2;
      break;
    default:
      dx = anchor.dx;
  }
  // SVG의 y는 텍스트 baseline이다 — 대략 fontSize의 0.8배만큼 위가 텍스트 상단이 되게 보정한다.
  final dy = anchor.dy - fontSize * 0.8;
  painter.paint(canvas, Offset(dx, dy));
}

/// 점선을 직접 그린다(패키지 추가 금지, A2) — dash/gap 길이를 번갈아가며 짧은 선분을 잇는다.
void _drawDashedLine(
  Canvas canvas,
  Offset from,
  Offset to,
  Color color,
  double strokeWidth,
  List<double> dashPattern,
) {
  final paint = Paint()
    ..color = color
    ..strokeWidth = strokeWidth;
  final total = (to - from).distance;
  if (total == 0) return;
  final direction = (to - from) / total;
  final dashLen = dashPattern[0];
  final gapLen = dashPattern.length > 1 ? dashPattern[1] : dashPattern[0];
  var distance = 0.0;
  var draw = true;
  while (distance < total) {
    final segment = draw ? dashLen : gapLen;
    final next = math.min(distance + segment, total);
    if (draw) {
      canvas.drawLine(from + direction * distance, from + direction * next, paint);
    }
    distance = next;
    draw = !draw;
  }
}
