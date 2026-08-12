// 7.4 수정 폼 역변환 단위 테스트 — ListingFormInput.fromDetail + 왕복(round-trip) 검증.
// 기존 매물 상세(ListingDetail) → 폼 입력(문자열) → 다시 validateAndBuildListing 으로 페이로드를 만들 때
//   원래 값이 보존되는지(정수·옵션 배열·설명) 확인한다. 신규 검증을 만들지 않고 7.3 로직을 재사용함을 보장.
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_form.dart';

ListingDetail sampleDetail({
  String status = 'on_sale',
  List<String>? options = const ['선루프', '후방카메라'],
  String? description = '상태 좋음',
  int displacement = 1598,
}) {
  return ListingDetail(
    id: 'id-1',
    sellerId: 'seller-1',
    manufacturer: '현대',
    model: '아반떼 CN7',
    bodyType: '준중형차',
    year: 2021,
    price: 29800000,
    mileage: 103000,
    color: '흰색',
    fuel: '가솔린',
    transmission: '자동',
    displacement: displacement,
    seats: 5,
    region: '서울',
    accidentFree: true,
    accidentStatus: '단순교환',
    isSingleOwner: true,
    status: status,
    options: options,
    description: description,
  );
}

void main() {
  group('ListingFormInput.fromDetail — 역변환', () {
    test('정수→문자열, 옵션 배열→쉼표 문자열, 모든 필드 채움', () {
      final input = ListingFormInput.fromDetail(sampleDetail());
      expect(input.manufacturer, '현대');
      expect(input.model, '아반떼 CN7');
      expect(input.bodyType, '준중형차');
      expect(input.year, '2021'); // 정수 → 문자열
      expect(input.price, '29800000');
      expect(input.mileage, '103000');
      expect(input.color, '흰색');
      expect(input.fuel, '가솔린');
      expect(input.transmission, '자동');
      expect(input.displacement, '1598');
      expect(input.seats, '5');
      expect(input.region, '서울');
      // ✎ 2026-08-13 — 폼은 이제 accidentFree가 아니라 신뢰속성 3개를 되채운다.
      //   is_non_smoker는 sampleDetail이 null로 두므로 **체크 해제**로 와야 한다 —
      //   null(미상)을 false("아니다")로 바꾸면 판매자가 하지 않은 신고를 만드는 것이다.
      expect(input.accidentStatus, '단순교환');
      expect(input.isSingleOwner, true);
      expect(input.isNonSmoker, false);
      expect(input.options, '선루프, 후방카메라'); // 배열 → 쉼표 문자열
      expect(input.description, '상태 좋음');
    });

    test('옵션 null → 빈 문자열, 설명 null → 빈 문자열', () {
      final input = ListingFormInput.fromDetail(
        sampleDetail(options: null, description: null),
      );
      expect(input.options, '');
      expect(input.description, '');
    });

    test('전기차 배기량 0 도 문자열 "0" 으로 보존', () {
      final input = ListingFormInput.fromDetail(sampleDetail(displacement: 0));
      expect(input.displacement, '0');
    });
  });

  group('왕복(round-trip): fromDetail → validateAndBuildListing', () {
    test('역변환한 입력이 다시 유효 페이로드를 만든다(원래 값 보존)', () {
      final input = ListingFormInput.fromDetail(sampleDetail());
      final r = validateAndBuildListing(input);
      expect(r.isOk, isTrue);
      final p = r.payload!;
      expect(p['manufacturer'], '현대');
      expect(p['model'], '아반떼 CN7');
      expect(p['year'], 2021); // 다시 정수
      expect(p['price'], 29800000);
      expect(p['mileage'], 103000);
      expect(p['displacement'], 1598);
      expect(p['seats'], 5);
      // ✎ 2026-08-13 — accident_free는 이제 **파생값**이다(accidentStatus == '무사고').
      //   sampleDetail의 사고이력이 '단순교환'이므로 false가 맞다 — 예전엔 accidentFree를
      //   그대로 실어 날라 true였다. 신뢰속성 3개가 왕복에서 보존되는지도 함께 본다.
      expect(p['accident_status'], '단순교환');
      expect(p['accident_free'], false);
      expect(p['is_single_owner'], true);
      // 미신고는 false가 아니라 null로 나가야 한다(판매자가 아무 말도 하지 않았다).
      expect(p['is_non_smoker'], isNull);
      expect(p['options'], ['선루프', '후방카메라']); // 쉼표 → 다시 배열
      expect(p['description'], '상태 좋음');
    });

    test('빈 옵션·설명 왕복 → 빈 배열·null', () {
      final input = ListingFormInput.fromDetail(
        sampleDetail(options: null, description: null),
      );
      final r = validateAndBuildListing(input);
      expect(r.isOk, isTrue);
      expect(r.payload!['options'], <String>[]);
      expect(r.payload!['description'], isNull);
    });
  });
}
