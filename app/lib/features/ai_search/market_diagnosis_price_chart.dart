// 시세 진단 카드 재구성(2026-09-14, DW-862)의 ③ 그림 — "AI 가격 곡선 + 비슷한 차 실제 가격
// 점". 가격 축 하나짜리 CustomPainter(새 패키지 추가 금지, A2). tabpfn.quantiles(q10·q25·
// q50·q75·q90)가 있으면 종 모양 곡선을 그리고, 없으면 곡선 없이 점 + q1·q3 구간만 그린다
// (헤드라인 폴백과 같은 원칙 — 예측 분포가 없으면 실측 통계로만 보여준다).
//
// 기존 산점도(market_diagnosis_chart.dart, 주행거리×가격 2축)는 그대로 남아 카드의 접힘
// 영역으로 자리만 옮긴다 — 이 파일은 그걸 대체하는 게 아니라 카드 기본 노출 자리에 새로 더한
// 그림이다.
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';

const double _viewW = 640;
const double _viewH = 180;
const double _x0 = 16;
const double _x1 = 624;
const double _yTop = 12;
const double _yBaseline = 140;
const double _yLabel = 164;

/// market_diagnosis_chart.dart의 동명 헬퍼와 같은 반올림 규칙(축 눈금을 보기 좋은 자리에
/// 맞춘다) — private 함수라 그 파일에서 재사용할 수 없어 그대로 복제한다(둘 다 한 줄짜리
/// 순수 함수라 공용 모듈로 뺄 만큼은 아니다).
int _roundUpTo(num value, int step) => (value / step).ceil() * step;
int _roundDownTo(num value, int step) => (value / step).floor() * step;

/// 가격 곡선 + 비교군 점 그래프 — AspectRatio로 화면 폭에 반응한다. 표시할 데이터가 전혀
/// 없으면(quantiles·stats·comps 모두 없음) 그래프 대신 안내 문구를 낸다.
class MarketDiagnosisPriceChart extends StatelessWidget {
  const MarketDiagnosisPriceChart({
    super.key,
    required this.listing,
    required this.stats,
    required this.comps,
    required this.quantiles,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats? stats;
  final List<MarketDiagnosisComp> comps;
  final MarketDiagnosisQuantiles? quantiles;

  @override
  Widget build(BuildContext context) {
    if (quantiles == null && stats == null && comps.isEmpty) {
      return const Text(
        '비교할 가격 데이터가 부족해 그래프를 표시할 수 없어요.',
        style: TextStyle(fontSize: 12, color: AppColors.inkMuted),
      );
    }
    return AspectRatio(
      aspectRatio: _viewW / _viewH,
      child: CustomPaint(
        size: Size.infinite,
        painter: _MarketDiagnosisPriceChartPainter(
          listing: listing,
          stats: stats,
          comps: comps,
          quantiles: quantiles,
        ),
      ),
    );
  }
}

class _MarketDiagnosisPriceChartPainter extends CustomPainter {
  _MarketDiagnosisPriceChartPainter({
    required this.listing,
    required this.stats,
    required this.comps,
    required this.quantiles,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats? stats;
  final List<MarketDiagnosisComp> comps;
  final MarketDiagnosisQuantiles? quantiles;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || size.height <= 0) return;
    final sx = size.width / _viewW;
    final sy = size.height / _viewH;

    final prices = <int>[listing.price, ...comps.map((c) => c.price)];
    final q = quantiles;
    if (q != null) prices.addAll([q.q10, q.q25, q.q50, q.q75, q.q90]);
    final s = stats;
    if (s != null) prices.addAll([s.min, s.max]);

    final priceMin = math.max(0, _roundDownTo(prices.reduce(math.min) * 0.95, 1000000));
    final priceMaxRaw = _roundUpTo(prices.reduce(math.max) * 1.05, 1000000);
    final priceMax = priceMaxRaw > priceMin ? priceMaxRaw : priceMin + 1000000;

    double xScale(num price) => _x0 + ((price - priceMin) / (priceMax - priceMin)) * (_x1 - _x0);

    canvas.save();
    canvas.scale(sx, sy);

    // 가격 축 + 눈금(4개).
    final axisPaint = Paint()
      ..color = AppColors.borderHairline
      ..strokeWidth = 1;
    canvas.drawLine(const Offset(_x0, _yBaseline), const Offset(_x1, _yBaseline), axisPaint);
    for (var i = 0; i <= 4; i++) {
      final p = priceMin + (priceMax - priceMin) / 4 * i;
      _drawText(
        canvas,
        '${thousands((p / 10000).round())}만',
        Offset(xScale(p), _yLabel),
        align: TextAlign.center,
        fontSize: 11,
        color: AppColors.inkMuted,
      );
    }

    if (q != null) {
      _drawBellCurve(canvas, q, xScale);
    } else if (s != null) {
      // 폴백 — 곡선 없이 q1~q3 구간만 옅은 띠로.
      final bandPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.10);
      canvas.drawRect(
        Rect.fromLTRB(xScale(s.q1), _yTop, xScale(s.q3), _yBaseline),
        bandPaint,
      );
      _drawDashedVLine(canvas, xScale(s.median), AppColors.brandPetrol);
      _drawText(
        canvas,
        '중앙값 ${thousands((s.median / 10000).round())}만',
        Offset(xScale(s.median), _yTop - 2),
        align: TextAlign.center,
        fontSize: 11,
        color: AppColors.brandPetrol,
      );
    }

    // 비교군 실제 가격 점 — 겹침을 줄이려 인덱스에 따라 기준선 위로 조금씩 다르게 띄운다.
    final compPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.55);
    for (var i = 0; i < comps.length; i++) {
      final y = _yBaseline - 6 - (i % 4) * 7;
      canvas.drawCircle(Offset(xScale(comps[i].price), y), 4, compPaint);
    }

    // 이 매물 가격 — 세로선 + 마커 + 라벨.
    final targetX = xScale(listing.price);
    canvas.drawLine(
      Offset(targetX, _yTop),
      Offset(targetX, _yBaseline),
      Paint()
        ..color = AppColors.priceEmphasis
        ..strokeWidth = 1.5,
    );
    canvas.drawCircle(Offset(targetX, _yBaseline), 5, Paint()..color = AppColors.priceEmphasis);
    _drawText(
      canvas,
      '이 매물 ${thousands((listing.price / 10000).round())}만',
      Offset(targetX, _yTop - 2),
      align: TextAlign.center,
      fontSize: 11,
      fontWeight: FontWeight.bold,
      color: AppColors.priceEmphasis,
    );

    canvas.restore();
  }

  /// tabpfn.quantiles(q10·q25·q50·q75·q90)로 종 모양(bell) 곡선을 그린다 — 5점을 기준선 위
  /// 높이로 환산해 이어 붙이는 개략적 형태다(실제 밀도함수 적분이 아니라 분위수 5점을 잇는
  /// 시각적 근사, 정적 카드에 그 이상의 정밀도는 필요 없다).
  void _drawBellCurve(Canvas canvas, MarketDiagnosisQuantiles q, double Function(num) xScale) {
    const weights = [0.05, 0.55, 1.0, 0.55, 0.05];
    final prices = [q.q10, q.q25, q.q50, q.q75, q.q90];
    final curveHeight = _yBaseline - _yTop;
    final points = <Offset>[
      Offset(xScale(prices.first), _yBaseline),
      for (var i = 0; i < prices.length; i++)
        Offset(xScale(prices[i]), _yBaseline - weights[i] * curveHeight),
      Offset(xScale(prices.last), _yBaseline),
    ];

    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 0; i < points.length - 1; i++) {
      final mid = Offset(
        (points[i].dx + points[i + 1].dx) / 2,
        (points[i].dy + points[i + 1].dy) / 2,
      );
      path.quadraticBezierTo(points[i].dx, points[i].dy, mid.dx, mid.dy);
    }
    path.lineTo(points.last.dx, points.last.dy);

    final fillPath = Path.from(path)
      ..lineTo(points.last.dx, _yBaseline)
      ..lineTo(points.first.dx, _yBaseline)
      ..close();
    canvas.drawPath(fillPath, Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.10));
    canvas.drawPath(
      path,
      Paint()
        ..color = AppColors.brandPetrol
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );

    _drawText(
      canvas,
      'AI 예상가 ${thousands((q.q50 / 10000).round())}만',
      Offset(xScale(q.q50), _yTop - 2),
      align: TextAlign.center,
      fontSize: 11,
      fontWeight: FontWeight.bold,
      color: AppColors.brandPetrolStrong,
    );
  }

  void _drawDashedVLine(Canvas canvas, double x, Color color) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1;
    const dashLen = 4.0;
    const gapLen = 3.0;
    var y = _yTop;
    var draw = true;
    while (y < _yBaseline) {
      final next = math.min(y + (draw ? dashLen : gapLen), _yBaseline);
      if (draw) canvas.drawLine(Offset(x, y), Offset(x, next), paint);
      y = next;
      draw = !draw;
    }
  }

  @override
  bool shouldRepaint(covariant _MarketDiagnosisPriceChartPainter oldDelegate) {
    return oldDelegate.listing != listing ||
        oldDelegate.stats != stats ||
        oldDelegate.comps != comps ||
        oldDelegate.quantiles != quantiles;
  }
}

/// SVG text-anchor(start/middle/end)를 흉내낸 텍스트 드로잉 — market_diagnosis_chart.dart의
/// 동명 헬퍼와 같은 이유로 복제(파일 간 private 함수 공유 불가, 각 파일 한 줄짜리).
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
  final dy = anchor.dy - fontSize * 0.8;
  painter.paint(canvas, Offset(dx, dy));
}
