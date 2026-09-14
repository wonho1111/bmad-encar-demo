// 시세 진단 카드 재구성(2026-09-14, DW-862)의 ③ 그림 — "AI 가격 곡선 + 비슷한 차 실제 가격
// 점". 가격 축 하나짜리 CustomPainter(새 패키지 추가 금지, A2). tabpfn.quantiles(q10·q25·
// q50·q75·q90)가 있으면 밀도 곡선을 그리고, 없으면 곡선 없이 점 + q1·q3 구간만 그린다
// (헤드라인 폴백과 같은 원칙 — 예측 분포가 없으면 실측 통계로만 보여준다).
//
// 기존 산점도(market_diagnosis_chart.dart, 주행거리×가격 2축)는 그대로 남아 카드의 접힘
// 영역으로 자리만 옮긴다 — 이 파일은 그걸 대체하는 게 아니라 카드 기본 노출 자리에 새로 더한
// 그림이다.
//
// 2026-09-14 2차 재작업(DW-885, 운영 실측, web MarketDiagnosisPriceChart.tsx 미러): 종전엔
// 분위수마다 고정 높이(0.05/0.55/1/0.55/0.05)를 박고 이차 베지어로 이었다 — q25·q50처럼
// 이웃 분위수가 서로 가까우면 곡선이 오버슈트해 정점 근처가 움푹 파였다(운영 캡처 다수에서
// 확인). 대신 "분위수 구간에 질량이 얼마나 있는가"를 먼저 정하고 밀도(질량÷폭)를 계산한 뒤,
// 그 값을 그리드에서 가우시안 커널로 평활해 폴리라인(직선 구간 연결, 스플라인 아님)으로
// 그린다(buildDensityCurve) — 오버슈트가 구조적으로 없어 파임이 생기지 않는다. 곡선은 q10·
// q90 밖 꼬리(폭은 이웃 구간과 동일)까지 그리므로 축 범위도 그만큼 넓혔다. 점(비교군 실제
// 가격)은 겹침 방지로 기준선 위에 흩뿌리던 것을 그만두고 comps 전부를 기준선 위에 그대로
// 찍는다(웹과 동일 — 겹침 자체가 밀도를 보여준다).
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'market_diagnosis.dart';

const double _viewW = 640;
const double _viewH = 210;
const double _x0 = 46;
const double _x1 = 610;
const double _yTop = 24; // 곡선 정점
const double _yBase = 150; // 가격 축(기준선) — 점·곡선 바닥이 여기 놓인다
const double _yTick = 172;

/// market_diagnosis_chart.dart의 동명 헬퍼와 같은 반올림 규칙(축 눈금을 보기 좋은 자리에
/// 맞춘다) — private 함수라 그 파일에서 재사용할 수 없어 그대로 복제한다(둘 다 한 줄짜리
/// 순수 함수라 공용 모듈로 뺄 만큼은 아니다).
int _roundUpTo(num value, int step) => (value / step).ceil() * step;
int _roundDownTo(num value, int step) => (value / step).floor() * step;

// 밀도 곡선 — web DENSITY_GRID_POINTS 미러(요구 범위 60~80 안의 확정값).
const int _densityGridPoints = 72;

class _DensitySegment {
  const _DensitySegment({required this.lo, required this.hi, required this.mass});
  final double lo;
  final double hi;
  final double mass;
}

List<_DensitySegment> _densitySegments(MarketDiagnosisQuantiles q) {
  final w1 = (q.q25 - q.q10).toDouble();
  final w2 = (q.q90 - q.q75).toDouble();
  return [
    _DensitySegment(lo: q.q10 - w1, hi: q.q10.toDouble(), mass: 0.10),
    _DensitySegment(lo: q.q10.toDouble(), hi: q.q25.toDouble(), mass: 0.15),
    _DensitySegment(lo: q.q25.toDouble(), hi: q.q50.toDouble(), mass: 0.25),
    _DensitySegment(lo: q.q50.toDouble(), hi: q.q75.toDouble(), mass: 0.25),
    _DensitySegment(lo: q.q75.toDouble(), hi: q.q90.toDouble(), mass: 0.15),
    _DensitySegment(lo: q.q90.toDouble(), hi: q.q90 + w2, mass: 0.10),
  ];
}

double _densityAt(double x, List<_DensitySegment> segments) {
  for (final seg in segments) {
    if (x >= seg.lo && x <= seg.hi) {
      final width = seg.hi - seg.lo;
      return width > 0 ? seg.mass / width : 0;
    }
  }
  return 0;
}

/// 분위수 5단(q10~q90)에서 구간별 밀도(질량÷폭)를 계산해 가우시안 커널로 평활한 뒤 정점을 1로
/// 정규화한 곡선 점들을 낸다. x는 가격(원), y는 0~1 정규화 밀도. 순수 함수(단위테스트 대상,
/// web buildDensityCurve 미러).
List<({double x, double y})> buildDensityCurve(MarketDiagnosisQuantiles q) {
  final segments = _densitySegments(q);
  final widths = segments.map((s) => s.hi - s.lo).where((w) => w > 0).toList()..sort();
  final medianWidth = widths.isEmpty ? 1.0 : widths[widths.length ~/ 2];
  final bandwidth = math.max(medianWidth * 0.6, 1.0); // 폭 0(분위수 값 중복) 방지

  final gridMin = segments.first.lo;
  final gridMax = segments.last.hi;
  final step = (gridMax - gridMin) / (_densityGridPoints - 1);
  final grid = List<double>.generate(_densityGridPoints, (i) => gridMin + step * i);
  final rawValues = [for (final x in grid) _densityAt(x, segments)];

  final smoothed = List<double>.generate(grid.length, (i) {
    final xi = grid[i];
    var weightedSum = 0.0;
    var weightTotal = 0.0;
    for (var j = 0; j < grid.length; j++) {
      final d = (xi - grid[j]) / bandwidth;
      final w = math.exp(-0.5 * d * d);
      weightedSum += w * rawValues[j];
      weightTotal += w;
    }
    return weightTotal > 0 ? weightedSum / weightTotal : 0.0;
  });

  final peak = smoothed.fold(1e-9, math.max);
  return [for (var i = 0; i < grid.length; i++) (x: grid[i], y: smoothed[i] / peak)];
}

/// "N만" 축약 표기(가격 축 눈금·이 매물 라벨 공용) — web manLabel 미러.
String _manLabel(num price) => '${thousands((price / 10000).round())}만';

/// 가격 곡선 + 비교군 점 그래프 — AspectRatio로 화면 폭에 반응한다. 표시할 데이터가 전혀
/// 없으면(quantiles·stats·comps 모두 없음) 그래프 대신 안내 문구를 낸다. 곡선 아래엔 범례
/// 문구를 한 줄 덧붙인다(web과 같은 문구).
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
    final legend = quantiles != null
        ? '곡선 높이 = 비슷한 차가 몰린 정도 · 점 = 비슷한 차 실제 등록가 · 굵은 선 = 이 매물'
        : '점 = 비슷한 차 실제 등록가 · 음영 = 가격 중간 50% 구간 · 굵은 선 = 이 매물';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        AspectRatio(
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
        ),
        const SizedBox(height: 4),
        Text(legend, style: const TextStyle(fontSize: 11, color: AppColors.inkMuted)),
      ],
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

    final q = quantiles;
    final s = stats;

    // 밀도 곡선은 q10·q90 밖 꼬리(q10−w1~q90+w2)까지 그린다 — 축 범위도 그만큼 넓혀야
    // 곡선이 잘리지 않는다(quantiles.q10/q90만 넣던 종전보다 넓음, DW-885 재작업).
    final compPrices = [for (final c in comps) c.price.toDouble()];
    late final List<double> domainValues;
    late final double pad;
    if (q != null) {
      final w1 = (q.q25 - q.q10).toDouble();
      final w2 = (q.q90 - q.q75).toDouble();
      domainValues = [...compPrices, listing.price.toDouble(), q.q10 - w1, q.q90 + w2];
      pad = math.max(math.max((q.q90 - q.q10) * 0.35, q.q50 * 0.05), 500000.0);
    } else {
      domainValues = [
        ...compPrices,
        listing.price.toDouble(),
        if (s != null) s.min.toDouble(),
        if (s != null) s.max.toDouble(),
      ];
      pad = 0;
    }
    final rawMin = domainValues.reduce(math.min) - pad;
    final rawMax = domainValues.reduce(math.max) + pad;
    final priceMin = math.max(0, _roundDownTo(rawMin * (q != null ? 1 : 0.95), 1000000));
    final priceMaxRounded = _roundUpTo(rawMax * (q != null ? 1 : 1.05), 1000000);
    final priceMax = priceMaxRounded > priceMin ? priceMaxRounded : priceMin + 1000000;

    double xScale(num price) => _x0 + ((price - priceMin) / (priceMax - priceMin)) * (_x1 - _x0);

    canvas.save();
    canvas.scale(sx, sy);

    // 가격 축 + 눈금(5개) + 축 제목.
    final axisPaint = Paint()
      ..color = AppColors.borderHairline
      ..strokeWidth = 1;
    canvas.drawLine(const Offset(_x0, _yBase), const Offset(_x1, _yBase), axisPaint);
    for (var i = 0; i <= 4; i++) {
      final p = priceMin + (priceMax - priceMin) / 4 * i;
      _drawText(
        canvas,
        _manLabel(p),
        Offset(xScale(p), _yTick),
        align: TextAlign.center,
        fontSize: 11,
        color: AppColors.inkMuted,
      );
    }
    _drawText(
      canvas,
      '가격 (만원)',
      const Offset((_x0 + _x1) / 2, _viewH - 4),
      align: TextAlign.center,
      fontSize: 11,
      color: AppColors.inkMuted,
    );

    // 세로축 설명 — 밀도 단위는 숫자로 봐야 의미가 없어 눈금 대신 "많음/적음"과 짧은 축
    // 제목만 왼쪽 여백(X0 안쪽)에 둔다(회전 텍스트 대신 짧은 라벨, web과 다른 표현 방식이나
    // 같은 정보를 전달한다).
    const labelX = _x0 / 2;
    _drawText(canvas, '많음', const Offset(labelX, _yTop + 8), align: TextAlign.center, fontSize: 9, color: AppColors.inkMuted);
    _drawText(
      canvas,
      '차 밀도',
      const Offset(labelX, (_yTop + _yBase) / 2),
      align: TextAlign.center,
      fontSize: 8,
      color: AppColors.inkMuted,
    );
    _drawText(canvas, '적음', const Offset(labelX, _yBase - 4), align: TextAlign.center, fontSize: 9, color: AppColors.inkMuted);

    if (q != null) {
      _drawDensityCurve(canvas, q, xScale);
    } else if (s != null) {
      // 폴백 — 곡선 없이 q1~q3 구간만 옅은 띠로(web과 동일, 중앙값 점선·라벨은 없앴다).
      final bandPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.08);
      canvas.drawRect(Rect.fromLTRB(xScale(s.q1), _yTop, xScale(s.q3), _yBase), bandPaint);
    }

    // 비교군 실제 가격 점 — 전부 기준선 위에 그대로 찍는다(web과 동일, 겹침 자체가 밀도를
    // 보여준다 — 예전처럼 인덱스로 띄우지 않는다).
    final compPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.55);
    for (final c in comps) {
      canvas.drawCircle(Offset(xScale(c.price), _yBase), 4.5, compPaint);
    }

    // 이 매물 가격 — 세로선 + 라벨(web과 동일, 별도 마커 점은 없다).
    final targetX = xScale(listing.price);
    canvas.drawLine(
      Offset(targetX, _yTop - 6),
      Offset(targetX, _yBase),
      Paint()
        ..color = AppColors.priceEmphasis
        ..strokeWidth = 2,
    );
    _drawText(
      canvas,
      '이 매물 ${_manLabel(listing.price)}',
      Offset(targetX, _yTop - 10),
      align: TextAlign.center,
      fontSize: 11,
      fontWeight: FontWeight.bold,
      color: AppColors.priceEmphasis,
    );

    canvas.restore();
  }

  /// buildDensityCurve가 낸 0~1 정규화 밀도 점들을 화면 좌표로 옮겨 채움(옅은 배경) +
  /// 폴리라인(직선 구간 연결, 스플라인 아님)으로 그린다.
  void _drawDensityCurve(Canvas canvas, MarketDiagnosisQuantiles q, double Function(num) xScale) {
    final curve = buildDensityCurve(q);
    if (curve.isEmpty) return;
    double heightAt(double frac) => _yBase - (_yBase - _yTop) * frac;
    final points = [for (final p in curve) Offset(xScale(p.x), heightAt(p.y))];

    final fillPath = Path()..moveTo(points.first.dx, _yBase);
    for (final pt in points) {
      fillPath.lineTo(pt.dx, pt.dy);
    }
    fillPath
      ..lineTo(points.last.dx, _yBase)
      ..close();
    canvas.drawPath(fillPath, Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.1));

    final strokePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (final pt in points.skip(1)) {
      strokePath.lineTo(pt.dx, pt.dy);
    }
    canvas.drawPath(
      strokePath,
      Paint()
        ..color = AppColors.brandPetrol
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
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
