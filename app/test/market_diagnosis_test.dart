// AI 시세 진단(5단계) 데이터 모델·순수 표시 헬퍼 단위테스트 — web MarketDiagnosis.test.ts
// 케이스를 그대로 미러한다(RUNG_DISPLAY·verdict 배지·백분위 노출 규칙). DOM 없이 순수 함수만
// 검증한다(app 기존 관례 — market_diagnosis.dart는 상태 없는 표현 로직만 둔다).
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/ai_search/market_diagnosis.dart';

Map<String, Object?> _wireListing({
  String id = 'l-1',
  String manufacturer = '기아',
  String model = '셀토스',
  int year = 2021,
  int mileage = 33000,
  int price = 22000000,
  String fuel = '가솔린',
  String transmission = '자동',
  int displacement = 1998,
  bool accidentFree = true,
  String? accidentStatus = '무사고',
  String region = '경기',
}) {
  return {
    'id': id,
    'manufacturer': manufacturer,
    'model': model,
    'year': year,
    'mileage': mileage,
    'price': price,
    'fuel': fuel,
    'transmission': transmission,
    'displacement': displacement,
    'accident_free': accidentFree,
    'accident_status': accidentStatus,
    'region': region,
  };
}

Map<String, Object?> _wireDiagnosis({int step = 0, List<Object?>? comps}) {
  return {
    'listing': _wireListing(),
    'criteria': {'step': step, 'desc': '테스트 단계', 'sample_count': 23},
    'stats': {'min': 19000000, 'q1': 21000000, 'median': 23000000, 'q3': 25000000, 'max': 27000000},
    'percentile': 0.3,
    'verdict': '저렴',
    'verdict_basis': '적정가',
    'tabpfn': {'price': 23500000, 'note': 'TabPFN 예측'},
    'comps': comps ?? const [],
  };
}

MarketDiagnosisData _diagnosisWithStep(int step) {
  final data = MarketDiagnosisData.fromMap(_wireDiagnosis(step: step));
  if (data == null) {
    fail('테스트 픽스처 자체가 파싱에 실패했다 — fromMap 회귀');
  }
  return data;
}

void main() {
  group('formatManKm', () {
    test('정수 만 단위는 소수점 없이 "N만km"', () {
      expect(formatManKm(30000), '3만km');
    });

    test('소수 만 단위는 소수 1자리로 "N.N만km"', () {
      expect(formatManKm(33000), '3.3만km');
    });
  });

  group('buildCriteriaChips', () {
    test('step=0(완화 없음)이면 모든 조건 칩이 active다', () {
      final chips = buildCriteriaChips(_diagnosisWithStep(0));
      expect(chips.every((c) => c.active), isTrue);
      // 연식 밴드 ±2년(step0), 대상 2021년 → 2019~2023년식.
      expect(chips.map((c) => c.label), contains('2019~2023년식'));
    });

    test('step=3(트림 해제 — 동일 세대 계열)이면 모델·사고 칩만 비활성이고 연료는 유지된다', () {
      final chips = buildCriteriaChips(_diagnosisWithStep(3));
      CriteriaChip byLabel(String label) => chips.firstWhere((c) => c.label == label);

      expect(byLabel('셀토스').active, isFalse); // 세대(모델 정확 일치) 해제.
      expect(byLabel('가솔린').active, isTrue); // 연료 조건은 아직 유지.
      expect(byLabel('무사고').active, isFalse); // 사고 조건 해제(이전 단에서 이미 해제됨).
    });

    test('step=5(연료·사고·세대 조건 전부 해제)면 그 세 칩만 비활성(취소선)이다', () {
      final chips = buildCriteriaChips(_diagnosisWithStep(5));
      CriteriaChip byLabel(String label) => chips.firstWhere((c) => c.label == label);

      expect(byLabel('셀토스').active, isFalse);
      expect(byLabel('가솔린').active, isFalse);
      expect(byLabel('무사고').active, isFalse);
      expect(byLabel('자동').active, isTrue, reason: '변속기는 사다리가 건드리지 않는다');
    });
  });

  group('buildVerdictBadge', () {
    test('verdict가 있으면 그 값을 그대로 배지로 쓴다(tone=verdict)', () {
      final badge = buildVerdictBadge('저렴', '사분위');
      expect(badge?.text, '저렴');
      expect(badge?.tone, 'verdict');
    });

    test('verdict가 null이고 표본 부족이면 중립 문구를 낸다(tone=neutral)', () {
      final badge = buildVerdictBadge(null, '표본 부족');
      expect(badge?.text, '표본 부족 — 판정 보류');
      expect(badge?.tone, 'neutral');
    });

    test('verdict도 null이고 표본 부족도 아니면(비교군 자체 없음) 배지를 아예 안 낸다', () {
      expect(buildVerdictBadge(null, null), isNull);
    });
  });

  group('shouldShowPercentileChip', () {
    test('표본 2건이면 percentile이 있어도 숨긴다(경계: 3건 미만)', () {
      expect(shouldShowPercentileChip(0.3, 2), isFalse);
    });

    test('표본 3건이면 percentile이 있을 때 보여준다(경계: 3건부터)', () {
      expect(shouldShowPercentileChip(0.3, 3), isTrue);
    });

    test('percentile 자체가 null이면 표본 수와 무관하게 숨긴다', () {
      expect(shouldShowPercentileChip(null, 10), isFalse);
    });
  });
  // 이 그룹이 안 보는 것: _rungDisplay 표 자체가 백엔드 LADDER와 실제로 일치하는지는 여기서
  // 확인할 수 없다(api·web·app 세 파일에 각각 선언된 상수라 자동 비교가 안 된다) — web과 동일
  // 한계, 사다리를 바꿀 때 사람이 세 표를 함께 고쳐야 한다는 사실은 여전히 주석으로만 지켜진다.

  // MarketDiagnosisData.fromMap 파싱 가드 — 정상/형태불량/누락 케이스(웹 aiSearch.test.ts의
  // isValidMarketDiagnosis 케이스 확장 — Dart는 강타입이라 세부 필드까지 검증한다).
  group('MarketDiagnosisData.fromMap — 파싱 가드', () {
    test('정상 wire 전체를 파싱한다', () {
      final data = MarketDiagnosisData.fromMap(_wireDiagnosis());
      expect(data, isNotNull);
      expect(data!.listing.model, '셀토스');
      expect(data.criteria.sampleCount, 23);
      expect(data.stats?.median, 23000000);
      expect(data.percentile, 0.3);
      expect(data.verdict, '저렴');
      expect(data.verdictBasis, '적정가');
      expect(data.tabpfn.price, 23500000);
    });

    test('Map이 아니면 null', () {
      expect(MarketDiagnosisData.fromMap('garbage'), isNull);
      expect(MarketDiagnosisData.fromMap(null), isNull);
    });

    test('listing이 Map이 아니면 전체를 버린다', () {
      final wire = _wireDiagnosis()..['listing'] = 'oops';
      expect(MarketDiagnosisData.fromMap(wire), isNull);
    });

    test('listing 필수 필드(price)가 없으면 전체를 버린다', () {
      final listing = _wireListing()..remove('price');
      final wire = _wireDiagnosis()..['listing'] = listing;
      expect(MarketDiagnosisData.fromMap(wire), isNull);
    });

    test('criteria가 Map이 아니면 전체를 버린다', () {
      final wire = _wireDiagnosis()..['criteria'] = 'oops';
      expect(MarketDiagnosisData.fromMap(wire), isNull);
    });

    test('comps가 List가 아니면 전체를 버린다', () {
      final wire = _wireDiagnosis()..['comps'] = 'oops';
      expect(MarketDiagnosisData.fromMap(wire), isNull);
    });

    test('comps 원소 하나가 깨져도 그 원소만 빠지고 나머지는 살린다', () {
      final wire = _wireDiagnosis(comps: [
        {'id': 'c1', 'model': 'K5', 'year': 2020, 'mileage': 40000, 'price': 20000000},
        {'id': 'broken'}, // 필드 누락 → 제외.
      ]);
      final data = MarketDiagnosisData.fromMap(wire);
      expect(data, isNotNull);
      expect(data!.comps.length, 1);
      expect(data.comps.single.id, 'c1');
    });

    test('stats가 null이면 stats도 null(표본 0건과 같은 정상 상태)', () {
      final wire = _wireDiagnosis()
        ..['stats'] = null
        ..['percentile'] = null
        ..['verdict'] = null
        ..['verdict_basis'] = null;
      final data = MarketDiagnosisData.fromMap(wire);
      expect(data, isNotNull);
      expect(data!.stats, isNull);
      expect(data.percentile, isNull);
      expect(data.verdict, isNull);
    });

    test('stats 필드 일부가 깨지면 stats 전체가 null로 안전 폴백한다(카드 전체는 살린다)', () {
      final wire = _wireDiagnosis()..['stats'] = {'min': 1, 'q1': 2, 'median': 3, 'q3': 4};
      final data = MarketDiagnosisData.fromMap(wire);
      expect(data, isNotNull);
      expect(data!.stats, isNull);
    });

    test('tabpfn이 없거나 깨지면 {price:null, note:""}로 안전 폴백한다', () {
      final wire = _wireDiagnosis()..['tabpfn'] = 'oops';
      final data = MarketDiagnosisData.fromMap(wire);
      expect(data, isNotNull);
      expect(data!.tabpfn.price, isNull);
      expect(data.tabpfn.note, '');
    });
  });

  // parseMarketDiagnoses — 2건 미만이면 null(web isValidMarketDiagnoses 미러).
  group('parseMarketDiagnoses', () {
    test('유효 원소가 2건 이상이면 그대로 반환한다', () {
      final result = parseMarketDiagnoses([_wireDiagnosis(), _wireDiagnosis()]);
      expect(result, isNotNull);
      expect(result!.length, 2);
    });

    test('유효 원소가 1건뿐이면 null(표를 그릴 이유가 없다)', () {
      expect(parseMarketDiagnoses([_wireDiagnosis()]), isNull);
    });

    test('원소 중 하나가 깨져도 나머지 유효 원소가 2건 이상이면 살아남는다', () {
      final result = parseMarketDiagnoses([_wireDiagnosis(), _wireDiagnosis(), 'garbage']);
      expect(result, isNotNull);
      expect(result!.length, 2);
    });

    test('List가 아니면 null', () {
      expect(parseMarketDiagnoses('oops'), isNull);
      expect(parseMarketDiagnoses(null), isNull);
    });
  });
}
