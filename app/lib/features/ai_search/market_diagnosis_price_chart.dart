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
// 컴팩트(폭 480dp 미만) 뷰박스 — 실기기 지적 A2: 고정 비율(640×210)이라 폭 380dp에서 높이가
// ~135까지 눌려 곡선·라벨이 뭉갰다. 논리 폭을 줄이고 높이를 키워 세로로 더 여유를 준다(축
// 라벨 폰트는 그대로 11이라 상대적으로 더 커진다).
const double _viewWCompact = 360;
const double _viewHCompact = 260;
const double _x0 = 46;
const double _x1 = 610;
const double _yTop = 24; // 곡선 정점
const double _yBase = 150; // 가격 축(기준선) — 점·곡선 바닥이 여기 놓인다
const double _yTick = 172;

// 5색 판정 구간 갱신(web MarketDiagnosisPriceChart.tsx five-zone.patch 미러) — "이 매물"·
// "AI 적정가" 라벨이 겹칠 때 어긋나게 띄울 자리가 기존 상단 여백(_yTop=24px)만으론 부족해
// 위쪽에 여백을 추가로 둔다(web의 viewBox `0 -18 ...` 확장과 동일 목적, Flutter는 viewBox가
// 없어 canvas.translate로 흉내낸다 — 아래 paint() 참조).
const double _topMargin = 18;

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

  // 2026-09-15 재작업(운영 캡처, web buildDensityCurve 미러): 격자를 분위수 꼬리 경계(segments
  // 끝)에서 그대로 자르면 그 자리의 밀도가 0이 아니어서 곡선이 상자처럼 뚝 끊긴다. 질량
  // (segments·mass)은 그대로 두고 평활용 격자만 양쪽으로 대역폭의 2.5배 넓혀 바깥(밀도 0인)
  // 구간까지 커널이 스며들게 해 곡선이 양끝에서 자연히 0 근처로 내려가게 한다.
  final tailExtension = bandwidth * 2.5;
  final gridMin = segments.first.lo - tailExtension;
  final gridMax = segments.last.hi + tailExtension;
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

// 5색 판정 구간(매우 저렴→저렴→적정→다소 높음→높음) — web five-zone.patch의 rect 색 배열 미러.
const List<Color> priceZoneColors = [
  Color(0xFF1E8A5A),
  Color(0xFF6DB38F),
  Color(0xFFA7B1BC),
  Color(0xFFE09A4F),
  Color(0xFFCF533E),
];

class PriceZoneBound {
  const PriceZoneBound({required this.from, required this.to, required this.color});
  final double from;
  final double to;
  final Color color;
}

/// 판정 구간 5색의 가격(원 단위) 경계 — web five-zone.patch의 rect 배열과 같은 구간 순서다.
/// curveMin·curveMax는 buildDensityCurve가 낸 꼬리 포함 격자의 양 끝 가격(첫·마지막 점의 x)을
/// 그대로 받는다 — 맨 앞·맨 뒤 구간(매우 저렴/높음)이 q10·q90 밖 꼬리까지 덮도록. 순수 함수
/// (단위테스트 대상) — CustomPainter·Canvas 없이 구간 경계·색만 고정한다(painter는 이 값을
/// xScale로 화면 좌표로 옮겨 그리기만 한다).
List<PriceZoneBound> priceZoneBounds(MarketDiagnosisQuantiles q, double curveMin, double curveMax) {
  return [
    PriceZoneBound(from: curveMin, to: q.q10.toDouble(), color: priceZoneColors[0]),
    PriceZoneBound(from: q.q10.toDouble(), to: q.q25.toDouble(), color: priceZoneColors[1]),
    PriceZoneBound(from: q.q25.toDouble(), to: q.q75.toDouble(), color: priceZoneColors[2]),
    PriceZoneBound(from: q.q75.toDouble(), to: q.q90.toDouble(), color: priceZoneColors[3]),
    PriceZoneBound(from: q.q90.toDouble(), to: curveMax, color: priceZoneColors[4]),
  ];
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
    this.verdict,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats? stats;
  final List<MarketDiagnosisComp> comps;
  final MarketDiagnosisQuantiles? quantiles;
  // "이 매물 N만 → {판정}" 라벨에 쓴다(web verdict prop 미러) — 안 넘기면 null이라 기존
  // 라벨("이 매물 N만") 그대로 나온다.
  final String? verdict;

  @override
  Widget build(BuildContext context) {
    if (quantiles == null && stats == null && comps.isEmpty) {
      return const Text(
        '비교할 가격 데이터가 부족해 그래프를 표시할 수 없어요.',
        style: TextStyle(fontSize: 12, color: AppColors.inkMuted),
      );
    }
    final legend = quantiles != null
        ? '색 = 판정 구간(매우 저렴~높음) · 점 = 비슷한 차 실제 등록가 · 굵은 선 = 이 매물 · 점선 = AI 적정가'
        : '점 = 비슷한 차 실제 등록가 · 음영 = 가격 중간 50% 구간 · 굵은 선 = 이 매물';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // 폭 480dp 미만이면 컴팩트 뷰박스(실기기 지적 A2) — 폭 380dp에서 기존 640×210 고정
        // 비율은 높이가 ~135까지 눌려 곡선·라벨이 뭉갰다. LayoutBuilder로 이 그래프가 실제
        // 받는 폭만 보고 판단한다.
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 480;
            final viewW = compact ? _viewWCompact : _viewW;
            final viewH = compact ? _viewHCompact : _viewH;
            return AspectRatio(
              // 상단 여백(_topMargin)만큼 세로가 늘어난 비율(web viewBox 확장 미러) — painter가
              // 그 여백만큼 translate해 좌표계는 기존 상수(_yTop 등) 그대로 쓴다.
              aspectRatio: viewW / (viewH + _topMargin),
              child: CustomPaint(
                size: Size.infinite,
                painter: _MarketDiagnosisPriceChartPainter(
                  listing: listing,
                  stats: stats,
                  comps: comps,
                  quantiles: quantiles,
                  verdict: verdict,
                  compact: compact,
                ),
              ),
            );
          },
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
    required this.verdict,
    required bool compact,
  })  : viewW = compact ? _viewWCompact : _viewW,
        viewH = compact ? _viewHCompact : _viewH,
        // 컴팩트 모드에선 레이아웃 계산은 그대로 두고 뷰박스 크기만 바꾸므로, 나머지 좌표
        // 상수(_x0 등, 기본 640×210 기준)를 그 비율만큼 그대로 스케일한다(실기기 지적 A2).
        x0 = compact ? _x0 * (_viewWCompact / _viewW) : _x0,
        x1 = compact ? _x1 * (_viewWCompact / _viewW) : _x1,
        yTop = compact ? _yTop * (_viewHCompact / _viewH) : _yTop,
        yBase = compact ? _yBase * (_viewHCompact / _viewH) : _yBase,
        yTick = compact ? _yTick * (_viewHCompact / _viewH) : _yTick;

  final MarketDiagnosisListing listing;
  final MarketDiagnosisStats? stats;
  final List<MarketDiagnosisComp> comps;
  final MarketDiagnosisQuantiles? quantiles;
  final String? verdict;
  final double viewW;
  final double viewH;
  final double x0;
  final double x1;
  final double yTop;
  final double yBase;
  final double yTick;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || size.height <= 0) return;
    final sx = size.width / viewW;
    final sy = size.height / (viewH + _topMargin);

    final q = quantiles;
    final s = stats;

    // 밀도 곡선은 q10·q90 밖 꼬리를 지나 평활 대역폭의 2.5배까지 더 그린다(위 buildDensityCurve
    // 재작업) — 축 범위도 그 넓힌 격자(curve 양 끝)를 포함해야 곡선이 잘리지 않는다.
    final curve = q != null ? buildDensityCurve(q) : const <({double x, double y})>[];
    final compPrices = [for (final c in comps) c.price.toDouble()];
    late final List<double> domainValues;
    late final double pad;
    if (q != null) {
      domainValues = [...compPrices, listing.price.toDouble(), curve.first.x, curve.last.x];
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

    double xScale(num price) => x0 + ((price - priceMin) / (priceMax - priceMin)) * (x1 - x0);

    canvas.save();
    canvas.scale(sx, sy);
    // 상단 여백만큼 아래로 밀어 기존 상수(yTop 등)는 그대로 두고 그 위(음수 y)까지 그릴
    // 자리를 확보한다(web viewBox `0 -18 ...` 확장과 동일 목적).
    canvas.translate(0, _topMargin);

    // 가격 축 + 눈금(5개) + 축 제목.
    final axisPaint = Paint()
      ..color = AppColors.borderHairline
      ..strokeWidth = 1;
    canvas.drawLine(Offset(x0, yBase), Offset(x1, yBase), axisPaint);
    for (var i = 0; i <= 4; i++) {
      final p = priceMin + (priceMax - priceMin) / 4 * i;
      _drawText(
        canvas,
        _manLabel(p),
        Offset(xScale(p), yTick),
        align: TextAlign.center,
        fontSize: 11,
        color: AppColors.inkMuted,
      );
    }
    _drawText(
      canvas,
      '가격 (만원)',
      Offset((x0 + x1) / 2, viewH - 4),
      align: TextAlign.center,
      fontSize: 11,
      color: AppColors.inkMuted,
    );

    // 세로축 설명 — 밀도 단위는 숫자로 봐야 의미가 없어 눈금 대신 "많음/적음"과 짧은 축
    // 제목만 왼쪽 여백(X0 안쪽)에 둔다(회전 텍스트 대신 짧은 라벨, web과 다른 표현 방식이나
    // 같은 정보를 전달한다).
    final labelX = x0 / 2;
    _drawText(canvas, '많음', Offset(labelX, yTop + 8), align: TextAlign.center, fontSize: 9, color: AppColors.inkMuted);
    _drawText(
      canvas,
      '차 밀도',
      Offset(labelX, (yTop + yBase) / 2),
      align: TextAlign.center,
      fontSize: 8,
      color: AppColors.inkMuted,
    );
    _drawText(canvas, '적음', Offset(labelX, yBase - 4), align: TextAlign.center, fontSize: 9, color: AppColors.inkMuted);

    if (q != null) {
      _drawDensityCurve(canvas, curve, xScale, q);
    } else if (s != null) {
      // 폴백 — 곡선 없이 q1~q3 구간만 옅은 띠로(web과 동일, 중앙값 점선·라벨은 없앴다).
      final bandPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.08);
      canvas.drawRect(Rect.fromLTRB(xScale(s.q1), yTop, xScale(s.q3), yBase), bandPaint);
    }

    // 비교군 실제 가격 점 — 전부 기준선 위에 그대로 찍는다(web과 동일, 겹침 자체가 밀도를
    // 보여준다 — 예전처럼 인덱스로 띄우지 않는다).
    final compPaint = Paint()..color = AppColors.brandPetrol.withValues(alpha: 0.55);
    for (final c in comps) {
      canvas.drawCircle(Offset(xScale(c.price), yBase), 4.5, compPaint);
    }

    if (q != null) {
      // q25~q75 괄호선 + "보통 A~B만" 라벨(web five-zone.patch 미러).
      final bracketPaint = Paint()
        ..color = AppColors.inkSecondary
        ..strokeWidth = 1;
      final q25X = xScale(q.q25);
      final q75X = xScale(q.q75);
      canvas.drawLine(Offset(q25X, yBase - 14), Offset(q75X, yBase - 14), bracketPaint);
      canvas.drawLine(Offset(q25X, yBase - 18), Offset(q25X, yBase - 10), bracketPaint);
      canvas.drawLine(Offset(q75X, yBase - 18), Offset(q75X, yBase - 10), bracketPaint);
      _drawText(
        canvas,
        '보통 ${_manLabel(q.q25)}~${_manLabel(q.q75)}',
        Offset((q25X + q75X) / 2, yBase - 21),
        align: TextAlign.center,
        fontSize: 10,
        color: AppColors.inkSecondary,
      );

      // q50 — 점선 세로선 + "AI 적정가 N만" 라벨. '이 매물' 라벨과 x가 가까우면(70px 미만)
      // 겹치므로 이 라벨을 더 위로 어긋나게 띄운다(web과 동일 기준).
      final q50X = xScale(q.q50);
      _drawDashedLine(
        canvas,
        Offset(q50X, yTop - 2),
        Offset(q50X, yBase),
        Paint()
          ..color = AppColors.inkSecondary
          ..strokeWidth = 1.5,
      );
      final overlapsListingLabel = (xScale(listing.price) - q50X).abs() < 70;
      _drawText(
        canvas,
        'AI 적정가 ${_manLabel(q.q50)}',
        Offset(q50X, overlapsListingLabel ? yTop - 30 : yTop - 10),
        align: TextAlign.center,
        fontSize: 10,
        fontWeight: FontWeight.w600,
        color: AppColors.inkSecondary,
      );
    }

    // 이 매물 가격 — 세로선 + 라벨(web과 동일, 별도 마커 점은 없다).
    final targetX = xScale(listing.price);
    canvas.drawLine(
      Offset(targetX, yTop - 6),
      Offset(targetX, yBase),
      Paint()
        ..color = AppColors.priceEmphasis
        ..strokeWidth = 2,
    );
    _drawText(
      canvas,
      verdict != null ? '이 매물 ${_manLabel(listing.price)} → $verdict' : '이 매물 ${_manLabel(listing.price)}',
      Offset(targetX, yTop - 10),
      align: TextAlign.center,
      fontSize: 11,
      fontWeight: FontWeight.bold,
      color: AppColors.priceEmphasis,
    );

    canvas.restore();
  }

  /// buildDensityCurve가 낸 0~1 정규화 밀도 점들을 화면 좌표로 옮겨 판정 구간 5색(clipPath로
  /// 곡선 모양 안쪽만, 2026-09-15 web five-zone.patch 미러 — 옛 단일 회색 음영 대체) +
  /// 폴리라인(직선 구간 연결, 스플라인 아님)으로 그린다.
  void _drawDensityCurve(
    Canvas canvas,
    List<({double x, double y})> curve,
    double Function(num) xScale,
    MarketDiagnosisQuantiles q,
  ) {
    if (curve.isEmpty) return;
    double heightAt(double frac) => yBase - (yBase - yTop) * frac;
    final points = [for (final p in curve) Offset(xScale(p.x), heightAt(p.y))];

    final fillPath = Path()..moveTo(points.first.dx, yBase);
    for (final pt in points) {
      fillPath.lineTo(pt.dx, pt.dy);
    }
    fillPath
      ..lineTo(points.last.dx, yBase)
      ..close();

    // 음영은 판정 구간 5색으로 칠한다 — clipPath(fillPath, 꼬리 포함 곡선 모양) 안쪽만
    // priceZoneBounds(순수 함수)가 낸 구간별 rect로 칠해 상자처럼 도드라지지 않는다.
    canvas.save();
    canvas.clipPath(fillPath);
    for (final zone in priceZoneBounds(q, curve.first.x, curve.last.x)) {
      canvas.drawRect(
        Rect.fromLTRB(xScale(zone.from), yTop, xScale(zone.to), yBase),
        Paint()..color = zone.color.withValues(alpha: 0.55),
      );
    }
    canvas.restore();

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
        oldDelegate.quantiles != quantiles ||
        oldDelegate.verdict != verdict ||
        oldDelegate.viewW != viewW;
  }
}

/// Canvas에 점선 그리기 — Flutter Canvas는 SVG strokeDasharray 같은 내장 점선이 없어 짧은
/// 선분을 이어 흉내낸다(web `stroke-dasharray="4 3"`과 같은 4·3 간격).
void _drawDashedLine(Canvas canvas, Offset start, Offset end, Paint paint, {double dashLength = 4, double gapLength = 3}) {
  final totalLength = (end - start).distance;
  if (totalLength == 0) return;
  final direction = (end - start) / totalLength;
  var drawn = 0.0;
  while (drawn < totalLength) {
    final segmentEnd = math.min(drawn + dashLength, totalLength);
    canvas.drawLine(start + direction * drawn, start + direction * segmentEnd, paint);
    drawn += dashLength + gapLength;
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
