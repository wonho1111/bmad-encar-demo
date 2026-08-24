// 7.3 매물 등록 폼 검증 단위 테스트 — validateAndBuildListing 순수 함수(web SellForm 규칙 이식).
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/listings/listing_filters.dart';
import 'package:app/features/listings/listing_form.dart';

// 정상 입력 한 벌(개별 테스트가 필요한 필드만 바꿔 쓴다).
ListingFormInput validInput({
  String manufacturer = '현대',
  String model = '아반떼 CN7',
  String bodyType = '준중형차',
  String year = '2021',
  String price = '29800000',
  String mileage = '103000',
  String color = '흰색',
  String fuel = '가솔린',
  String transmission = '자동',
  String displacement = '1598',
  String seats = '5',
  String region = '서울',
  String accidentStatus = '무사고',
  bool isSingleOwner = false,
  bool isNonSmoker = false,
  String options = '선루프, 후방카메라',
  String description = '상태 좋음',
}) {
  return ListingFormInput(
    manufacturer: manufacturer,
    model: model,
    bodyType: bodyType,
    year: year,
    price: price,
    mileage: mileage,
    color: color,
    fuel: fuel,
    transmission: transmission,
    displacement: displacement,
    seats: seats,
    region: region,
    accidentStatus: accidentStatus,
    isSingleOwner: isSingleOwner,
    isNonSmoker: isNonSmoker,
    options: options,
    description: description,
  );
}

void main() {
  group('ListingOptions.manufacturer (0002 CHECK 미러)', () {
    test('15개 제조사 + 기타 포함', () {
      expect(ListingOptions.manufacturer.length, 15);
      expect(ListingOptions.manufacturer.contains('현대'), isTrue);
      expect(ListingOptions.manufacturer.contains('기타'), isTrue);
      expect(ListingOptions.manufacturer.contains('테슬라'), isTrue);
    });
  });

  group('ListingRanges', () {
    test('연식 상한 = 올해 + 1(신차년식)', () {
      expect(ListingRanges.yearMax, DateTime.now().year + 1);
      expect(ListingRanges.yearMin, 1990);
    });
    test('인승 2~11', () {
      expect(ListingRanges.seatsMin, 2);
      expect(ListingRanges.seatsMax, 11);
    });
  });

  group('validateAndBuildListing — 정상', () {
    test('정상 입력 → on_sale 페이로드(15필드·정수·options 배열)', () {
      final r = validateAndBuildListing(validInput());
      expect(r.isOk, isTrue);
      final p = r.payload!;
      expect(p['status'], 'on_sale');
      expect(p['manufacturer'], '현대');
      expect(p['model'], '아반떼 CN7');
      expect(p['body_type'], '준중형차');
      expect(p['year'], 2021); // 정수 변환
      expect(p['price'], 29800000);
      expect(p['mileage'], 103000);
      expect(p['displacement'], 1598);
      expect(p['seats'], 5);
      expect(p['accident_free'], true);
      expect(p['options'], ['선루프', '후방카메라']); // 쉼표 분리·trim
      expect(p['description'], '상태 좋음');
    });

    test('모델·설명 trim, 빈 설명은 null, 전기차 배기량 0 허용', () {
      final r = validateAndBuildListing(validInput(
        model: '  EV6  ',
        description: '   ',
        fuel: '전기',
        displacement: '0',
        options: '',
      ));
      expect(r.isOk, isTrue);
      expect(r.payload!['model'], 'EV6');
      expect(r.payload!['description'], isNull);
      expect(r.payload!['displacement'], 0);
      expect(r.payload!['options'], <String>[]); // 빈 옵션 → 빈 배열
    });

    test('연식 경계값(올해+1) 통과', () {
      final r = validateAndBuildListing(
        validInput(year: '${DateTime.now().year + 1}'),
      );
      expect(r.isOk, isTrue);
    });
  });

  group('validateAndBuildListing — 필수값 누락(한국어 거절)', () {
    test('제조사 미선택', () {
      final r = validateAndBuildListing(validInput(manufacturer: ''));
      expect(r.isOk, isFalse);
      expect(r.message, '제조사를 선택해주세요.');
    });
    test('모델 공백', () {
      final r = validateAndBuildListing(validInput(model: '   '));
      expect(r.isOk, isFalse);
      expect(r.message, '모델명을 입력해주세요.');
    });
    test('지역 미선택', () {
      final r = validateAndBuildListing(validInput(region: ''));
      expect(r.isOk, isFalse);
      expect(r.message, '지역을 선택해주세요.');
    });
  });

  group('validateAndBuildListing — CHECK 위반(범위/형식)', () {
    test('연식 하한 미만(1989) 거절', () {
      final r = validateAndBuildListing(validInput(year: '1989'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('연식'));
    });
    test('연식 상한 초과(올해+2) 거절', () {
      final r = validateAndBuildListing(
        validInput(year: '${DateTime.now().year + 2}'),
      );
      expect(r.isOk, isFalse);
      expect(r.message, contains('연식'));
    });
    test('가격 소수점 거절', () {
      final r = validateAndBuildListing(validInput(price: '1000.5'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('가격'));
    });
    test('주행거리 음수 표기(-5) 거절', () {
      // '-5' 는 순수 숫자열이 아니므로 거절.
      final r = validateAndBuildListing(validInput(mileage: '-5'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('주행거리'));
    });
    test('배기량 빈값 거절', () {
      final r = validateAndBuildListing(validInput(displacement: ''));
      expect(r.isOk, isFalse);
      expect(r.message, contains('배기량'));
    });
    test('인승 범위 밖(1) 거절', () {
      final r = validateAndBuildListing(validInput(seats: '1'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('인승'));
    });
    test('인승 범위 밖(12) 거절', () {
      final r = validateAndBuildListing(validInput(seats: '12'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('인승'));
    });
    test('드롭다운 목록 밖 제조사(직접 주입) 거절', () {
      final r = validateAndBuildListing(validInput(manufacturer: '없는제조사'));
      expect(r.isOk, isFalse);
      expect(r.message, contains('제조사'));
    });
  });

  // ✎ 2026-08-13 신설 — 신뢰속성 저장 계약. 앱은 이 3컬럼을 **한 번도 저장한 적이 없었고**
  //   그걸 잡는 검사도 없어서, "화면엔 뱃지가 있는데 앱으로 등록하면 안 채워지는" 상태가
  //   아무에게도 안 보였다(web에서 같은 구멍을 먼저 발견했다). 그 사각지대를 여기서 닫는다.
  group('신뢰속성 저장 계약(2026-08-13)', () {
    test('사고이력 미선택은 거절한다 — 예전엔 기본 켜진 스위치라 "안 고름"이 곧 무사고 신고였다', () {
      final r = validateAndBuildListing(validInput(accidentStatus: ''));
      expect(r.isOk, isFalse);
      expect(r.message, contains('사고이력'));
    });

    test('accident_free는 입력이 아니라 사고이력에서 파생된다 — 무사고면 true', () {
      final r = validateAndBuildListing(validInput(accidentStatus: '무사고'));
      expect(r.isOk, isTrue);
      expect(r.payload!['accident_status'], '무사고');
      expect(r.payload!['accident_free'], true);
    });

    test('무사고가 아니면 accident_free는 false다', () {
      for (final status in ['단순교환', '사고']) {
        final r = validateAndBuildListing(validInput(accidentStatus: status));
        expect(r.isOk, isTrue, reason: '$status 는 유효한 값이다');
        expect(r.payload!['accident_free'], false,
            reason: '$status 인데 accident_free가 true면 웹 필터(사고이력 기준)와 '
                'AI 검색(accident_free 기준)이 서로 다른 결과를 낸다');
      }
    });

    test('체크 안 한 항목은 false가 아니라 null(미신고)로 저장된다', () {
      final r = validateAndBuildListing(
        validInput(accidentStatus: '무사고', isSingleOwner: true, isNonSmoker: false),
      );
      expect(r.isOk, isTrue);
      expect(r.payload!['is_single_owner'], true);
      // false로 저장하면 "이 차는 비흡연이 아니다"라고 판매자가 신고한 것이 되는데,
      // 그는 아무 말도 하지 않았다(0017이 못박은 3상태 규칙).
      expect(r.payload!['is_non_smoker'], isNull);
    });
  });
}
