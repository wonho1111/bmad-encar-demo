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
  bool accidentFree = true,
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
    accidentFree: accidentFree,
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
}
