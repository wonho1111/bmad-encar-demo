// 시세 진단 데이터 모델 + 순수 표시 헬퍼(5단계, web MarketDiagnosis.tsx 미러) — 상태 없는
// 타입·함수만 둔다. 렌더 위젯은 market_diagnosis_card.dart(카드)·market_diagnosis_chart.dart
// (산점도)·market_diagnosis_table.dart(다건 요약표)에 분리돼 있다.
//
// 데이터 출처: api/app/market_price.py diagnose()의 반환 dict 그대로 — 숫자는 전부 SQL·TabPFN이
// 낸 값이고, 이 파일은 그 값을 파싱·배치 판단만 한다(재계산 금지). 유일한 예외는 아래
// _rungDisplay 표 — 완화 사다리 단계별로 "어떤 조건이 해제됐는지"를 칩 취소선으로 보여주기
// 위한 **표시 전용** 복제본이다(실제 필터링에는 관여하지 않는다 — 정본은
// api/app/market_price.py의 LADDER, web MarketDiagnosis.tsx RUNG_DISPLAY와 동일 락스텝).
//
// ⚠️ web의 isValidMarketDiagnosis는 "형태만" 보고(느슨한 통과), 세부 필드가 깨져도 컴포넌트가
// null-safe하게 그린다(undefined가 그냥 화면에 새는 식). Dart는 강타입이라 그럴 수 없다 — 이
// 파일의 fromMap들은 필수 필드가 타입에 안 맞으면 **그 객체 전체를 버린다**(웹보다 엄격한
// 의도된 차이, 작업 보고서 참조).
import '../listings/listing.dart' show asInt;

/// 진단 대상 매물 요약(listing) — web MarketDiagnosisListing 미러.
class MarketDiagnosisListing {
  const MarketDiagnosisListing({
    required this.id,
    required this.manufacturer,
    required this.model,
    required this.year,
    required this.mileage,
    required this.price,
    required this.fuel,
    required this.transmission,
    required this.displacement,
    required this.accidentFree,
    required this.accidentStatus,
    required this.region,
  });

  final String id;
  final String manufacturer;
  final String model;
  final int year;
  final int mileage;
  final int price;
  final String fuel;
  final String transmission; // '자동'|'수동'
  final int displacement;
  final bool accidentFree;
  final String? accidentStatus; // '무사고'|'단순교환'|'사고'|null
  final String region;

  static MarketDiagnosisListing? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final fuel = raw['fuel'];
    final transmission = raw['transmission'];
    final region = raw['region'];
    final accidentFree = raw['accident_free'];
    final year = asInt(raw['year']);
    final mileage = asInt(raw['mileage']);
    final price = asInt(raw['price']);
    final displacement = asInt(raw['displacement']);

    if (id is! String ||
        manufacturer is! String ||
        model is! String ||
        fuel is! String ||
        transmission is! String ||
        region is! String ||
        accidentFree is! bool ||
        year == null ||
        mileage == null ||
        price == null ||
        displacement == null) {
      return null;
    }

    return MarketDiagnosisListing(
      id: id,
      manufacturer: manufacturer,
      model: model,
      year: year,
      mileage: mileage,
      price: price,
      fuel: fuel,
      transmission: transmission,
      displacement: displacement,
      accidentFree: accidentFree,
      accidentStatus: raw['accident_status'] is String ? raw['accident_status'] as String : null,
      region: region,
    );
  }
}

/// 비교군 매물 한 건(comps) — web MarketDiagnosisComp 미러.
class MarketDiagnosisComp {
  const MarketDiagnosisComp({
    required this.id,
    required this.model,
    required this.year,
    required this.mileage,
    required this.price,
  });

  final String id;
  final String model;
  final int year;
  final int mileage;
  final int price;

  static MarketDiagnosisComp? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final model = raw['model'];
    final year = asInt(raw['year']);
    final mileage = asInt(raw['mileage']);
    final price = asInt(raw['price']);
    if (id is! String || model is! String || year == null || mileage == null || price == null) {
      return null;
    }
    return MarketDiagnosisComp(id: id, model: model, year: year, mileage: mileage, price: price);
  }
}

/// 사분위 통계(stats) — web MarketDiagnosisStats 미러.
class MarketDiagnosisStats {
  const MarketDiagnosisStats({
    required this.min,
    required this.q1,
    required this.median,
    required this.q3,
    required this.max,
  });

  final int min;
  final int q1;
  final int median;
  final int q3;
  final int max;

  static MarketDiagnosisStats? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final min = asInt(raw['min']);
    final q1 = asInt(raw['q1']);
    final median = asInt(raw['median']);
    final q3 = asInt(raw['q3']);
    final max = asInt(raw['max']);
    if (min == null || q1 == null || median == null || q3 == null || max == null) return null;
    return MarketDiagnosisStats(min: min, q1: q1, median: median, q3: q3, max: max);
  }
}

/// 비교 기준(criteria) — web `{step, desc, sample_count}` 미러.
class MarketDiagnosisCriteria {
  const MarketDiagnosisCriteria({required this.step, required this.desc, required this.sampleCount});

  final int step;
  final String desc;
  final int sampleCount;

  static MarketDiagnosisCriteria? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final step = asInt(raw['step']);
    final desc = raw['desc'];
    final sampleCount = asInt(raw['sample_count']);
    if (step == null || desc is! String || sampleCount == null) return null;
    return MarketDiagnosisCriteria(step: step, desc: desc, sampleCount: sampleCount);
  }
}

/// TabPFN(적정가 예측 모델) 결과 — web `{price, note}` 미러. 형태가 깨지면(웹과 달리) 전체를
/// 버리지 않고 "예측 없음"(price:null, note:'')으로 안전 폴백한다 — tabpfn은 진단의 핵심 축이
/// 아니라 통계 3칸 중 한 칸일 뿐이라, 이 조각만으로 카드 전체를 버릴 이유가 없다.
class MarketDiagnosisTabpfn {
  const MarketDiagnosisTabpfn({required this.price, required this.note});

  final int? price;
  final String note;

  static MarketDiagnosisTabpfn fromMap(Object? raw) {
    if (raw is! Map) return const MarketDiagnosisTabpfn(price: null, note: '');
    final note = raw['note'];
    return MarketDiagnosisTabpfn(price: asInt(raw['price']), note: note is String ? note : '');
  }
}

/// 시세 진단 결과 전체 — web MarketDiagnosisData 미러(api/app/market_price.py diagnose() 반환).
class MarketDiagnosisData {
  const MarketDiagnosisData({
    required this.listing,
    required this.criteria,
    required this.stats,
    required this.percentile,
    required this.verdict,
    required this.verdictBasis,
    required this.tabpfn,
    required this.comps,
  });

  final MarketDiagnosisListing listing;
  final MarketDiagnosisCriteria criteria;
  final MarketDiagnosisStats? stats;
  final double? percentile; // 0~1
  final String? verdict; // '저렴'|'적정'|'높음'|null
  final String? verdictBasis; // '적정가'|'사분위'|'표본 부족'|null
  final MarketDiagnosisTabpfn tabpfn;
  final List<MarketDiagnosisComp> comps;

  /// wire(dict) → 진단 데이터. listing/criteria가 Map이 아니거나 comps가 List가 아니거나
  /// listing/criteria의 필수 필드가 깨지면 전체를 버린다(null) — api가 이 dict 형태를
  /// Pydantic으로 보장하지 않으므로(server: `market_diagnosis: dict | None`), 이 파일이 앱의
  /// 유일한 방어선이다(web isValidMarketDiagnosis와 같은 목적).
  static MarketDiagnosisData? fromMap(Object? raw) {
    if (raw is! Map) return null;

    final listing = MarketDiagnosisListing.fromMap(raw['listing']);
    if (listing == null) return null;

    final criteria = MarketDiagnosisCriteria.fromMap(raw['criteria']);
    if (criteria == null) return null;

    final rawComps = raw['comps'];
    if (rawComps is! List) return null;
    final comps = <MarketDiagnosisComp>[];
    for (final c in rawComps) {
      final comp = MarketDiagnosisComp.fromMap(c);
      if (comp != null) comps.add(comp); // 깨진 comp 원소 하나만 제외(카드 전체는 살린다).
    }

    final statsRaw = raw['stats'];
    final stats = statsRaw == null ? null : MarketDiagnosisStats.fromMap(statsRaw);

    final percentile = raw['percentile'];
    final verdict = raw['verdict'];
    final verdictBasis = raw['verdict_basis'];

    return MarketDiagnosisData(
      listing: listing,
      criteria: criteria,
      stats: stats,
      percentile: percentile is num ? percentile.toDouble() : null,
      verdict: verdict is String ? verdict : null,
      verdictBasis: verdictBasis is String ? verdictBasis : null,
      tabpfn: MarketDiagnosisTabpfn.fromMap(raw['tabpfn']),
      comps: comps,
    );
  }
}

/// wire의 market_diagnoses(복수, 2건 이상일 때만 채워짐)를 파싱한다 — 각 원소를 fromMap으로
/// 걸러 유효한 것만 남기고, 2건 미만이면 null(표를 그릴 이유가 없다 — 백엔드 계약과 동일,
/// web isValidMarketDiagnoses 미러).
List<MarketDiagnosisData>? parseMarketDiagnoses(Object? value) {
  if (value is! List) return null;
  final valid = <MarketDiagnosisData>[];
  for (final item in value) {
    final d = MarketDiagnosisData.fromMap(item);
    if (d != null) valid.add(d);
  }
  return valid.length >= 2 ? valid : null;
}

/// 주행거리를 "3.3만km" 식 만 단위로 표시한다(정수면 "3만km", 소수면 소수 1자리).
/// web formatManKm 미러 — "AI 시세 진단" 프리필 문구(listing_detail_screen.dart)에서도
/// 재사용한다(중복 정의 금지).
String formatManKm(int km) {
  final man = (km / 10000 * 10).round() / 10;
  final isInt = man == man.roundToDouble();
  return isInt ? '${man.round()}만km' : '${man.toStringAsFixed(1)}만km';
}

/// 비교 기준 칩 하나 — web CriteriaChip 미러.
class CriteriaChip {
  const CriteriaChip({required this.label, required this.active});
  final String label;
  final bool active;
}

class _Rung {
  const _Rung({
    required this.yearBand,
    required this.kmBand,
    required this.fuelActive,
    required this.accidentActive,
    required this.modelExact,
  });
  final int yearBand;
  final int kmBand;
  final bool fuelActive;
  final bool accidentActive;
  final bool modelExact;
}

/// 완화 사다리 표시 전용 복제본(정본: api/app/market_price.py LADDER) — web RUNG_DISPLAY 미러.
/// 취소선 칩 판단에만 쓴다(실제 필터링과 무관) — 사다리가 바뀌면 세 표(api·web·app)를 함께
/// 고쳐야 한다는 사실은 여전히 주석으로만 지켜진다(web과 동일 한계, 아래 buildCriteriaChips
/// 하단 주석 참조).
const Map<int, _Rung> _rungDisplay = {
  0: _Rung(yearBand: 2, kmBand: 30000, fuelActive: true, accidentActive: true, modelExact: true),
  1: _Rung(yearBand: 3, kmBand: 50000, fuelActive: true, accidentActive: true, modelExact: true),
  2: _Rung(yearBand: 3, kmBand: 50000, fuelActive: true, accidentActive: false, modelExact: true),
  3: _Rung(yearBand: 3, kmBand: 50000, fuelActive: true, accidentActive: false, modelExact: false),
  4: _Rung(yearBand: 3, kmBand: 50000, fuelActive: true, accidentActive: false, modelExact: false),
  5: _Rung(yearBand: 3, kmBand: 50000, fuelActive: false, accidentActive: false, modelExact: false),
};

/// 비교 기준 칩(②) 목록을 만든다 — target 속성 + 현재 사다리 단계(criteria.step)의 활성 조건.
/// 순수 함수(단위테스트 대상, web buildCriteriaChips 미러).
List<CriteriaChip> buildCriteriaChips(MarketDiagnosisData data) {
  final listing = data.listing;
  final rung = _rungDisplay[data.criteria.step] ?? _rungDisplay[0]!;
  final yearLo = listing.year - rung.yearBand;
  final yearHi = listing.year + rung.yearBand;
  final kmLo = listing.mileage - rung.kmBand < 0 ? 0 : listing.mileage - rung.kmBand;
  final kmHi = listing.mileage + rung.kmBand;
  final accidentLabel = listing.accidentFree ? '무사고' : (listing.accidentStatus ?? '사고');

  return [
    CriteriaChip(label: listing.model, active: rung.modelExact),
    CriteriaChip(label: listing.fuel, active: rung.fuelActive),
    CriteriaChip(label: listing.transmission, active: true),
    CriteriaChip(label: accidentLabel, active: rung.accidentActive),
    CriteriaChip(label: '$yearLo~$yearHi년식', active: true),
    CriteriaChip(label: '${formatManKm(kmLo)}~${formatManKm(kmHi)}', active: true),
  ];
}
// 이 함수가 안 보는 것(web 동일 한계): _rungDisplay 표 자체가 백엔드 LADDER와 실제로 일치하는지는
// 여기서 확인할 수 없다(세 언어·세 파일에 각각 선언된 상수라 자동 비교가 안 된다) — 사다리를
// 바꿀 때 사람이 세 표를 함께 고쳐야 한다는 사실은 여전히 주석으로만 지켜진다.

/// 판정 배지 표시값 — web VerdictBadge 미러.
class VerdictBadge {
  const VerdictBadge({required this.text, required this.tone});
  final String text;
  final String tone; // 'verdict' | 'neutral'
}

/// 배지 대신 무엇을 보여줄지 결정하는 순수 함수(소표본 과신 판정 방지, web buildVerdictBadge 미러).
VerdictBadge? buildVerdictBadge(String? verdict, String? verdictBasis) {
  if (verdict != null) return VerdictBadge(text: verdict, tone: 'verdict');
  if (verdictBasis == '표본 부족') return const VerdictBadge(text: '표본 부족 — 판정 보류', tone: 'neutral');
  return null;
}

/// 백분위("하위 N% 가격대") 칩은 표본이 이 값 미만이면 숨긴다(백엔드 MIN_VERDICT_SAMPLE과
/// 동일 기준, web MIN_PERCENTILE_SAMPLE 미러) — 비교군 1~2건의 백분위는 verdict와 마찬가지로
/// 판정 근거가 못 된다.
const int minPercentileSample = 3;

bool shouldShowPercentileChip(double? percentile, int sampleCount) {
  return percentile != null && sampleCount >= minPercentileSample;
}
