// 7.2 매물 모델 단위 테스트 — fromMap 의 7필드 가드(깨진 원소 제외)·타입 안전 변환.
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/listings/listing.dart';

void main() {
  group('ListingCardData.fromMap', () {
    test('정상 7필드 → 카드', () {
      final c = ListingCardData.fromMap({
        'id': 'abc',
        'manufacturer': '현대',
        'model': '소나타',
        'year': 2020,
        'price': 25000000,
        'mileage': 35000,
        'region': '서울',
        'seller_name': '홍길동',
      });
      expect(c, isNotNull);
      expect(c!.model, '소나타');
      expect(c.sellerName, '홍길동');
    });

    test('숫자가 문자열·double 로 와도 int 로 변환', () {
      final c = ListingCardData.fromMap({
        'id': 'a',
        'manufacturer': '기아',
        'model': 'K5',
        'year': '2019',
        'price': 20000000.0,
        'mileage': '40000',
        'region': '경기',
      });
      expect(c, isNotNull);
      expect(c!.year, 2019);
      expect(c.price, 20000000);
      expect(c.mileage, 40000);
    });

    test('필수 필드 누락 원소는 null(버려짐)', () {
      expect(
        ListingCardData.fromMap({'id': 'a', 'manufacturer': '현대'}),
        isNull,
      );
      expect(ListingCardData.fromMap(null), isNull);
      expect(ListingCardData.fromMap('not a map'), isNull);
    });

    test('seller_name 없으면 null(AI 결과 등)', () {
      final c = ListingCardData.fromMap({
        'id': 'a',
        'manufacturer': '현대',
        'model': '아반떼',
        'year': 2021,
        'price': 18000000,
        'mileage': 20000,
        'region': '부산',
      });
      expect(c!.sellerName, isNull);
    });

    // Story 10.1 — fuel·신뢰속성 3필드 파싱(대장 #67, conventions §4 계약-외 값 정규화).
    test('fuel·신뢰속성 3필드 정상 파싱', () {
      final c = ListingCardData.fromMap({
        'id': 'a',
        'manufacturer': '현대',
        'model': '아반떼',
        'year': 2021,
        'price': 18000000,
        'mileage': 20000,
        'region': '부산',
        'fuel': '가솔린',
        'accident_status': '단순교환',
        'is_single_owner': true,
        'is_non_smoker': false,
      });
      expect(c!.fuel, '가솔린');
      expect(c.accidentStatus, '단순교환');
      expect(c.isSingleOwner, isTrue);
      expect(c.isNonSmoker, isFalse);
    });

    test('accident_status가 비-String이면 null로 강등되고 행은 살아남는다', () {
      final c = ListingCardData.fromMap({
        'id': 'a',
        'manufacturer': '현대',
        'model': '아반떼',
        'year': 2021,
        'price': 18000000,
        'mileage': 20000,
        'region': '부산',
        'accident_status': 123, // 도메인 밖 타입(계약-외 값)
      });
      expect(c, isNotNull); // 핵심 7필드가 아니므로 행을 버리지 않는다
      expect(c!.accidentStatus, isNull);
    });

    test('is_single_owner가 없으면 false가 아니라 null(미상, bool 3상태)', () {
      final c = ListingCardData.fromMap({
        'id': 'a',
        'manufacturer': '현대',
        'model': '아반떼',
        'year': 2021,
        'price': 18000000,
        'mileage': 20000,
        'region': '부산',
      });
      expect(c!.isSingleOwner, isNull);
      expect(c.isSingleOwner, isNot(false)); // false로 단정하지 않는다(오독 방지)
      expect(c.isNonSmoker, isNull);
      expect(c.fuel, isNull);
    });
  });

  group('ListingDetail.fromMap', () {
    test('정상 상세 → 모델(옵션·설명 포함)', () {
      final d = ListingDetail.fromMap({
        'id': 'x',
        'seller_id': 's1',
        'manufacturer': '현대',
        'model': '그랜저',
        'body_type': '대형차',
        'year': 2022,
        'price': 40000000,
        'mileage': 15000,
        'color': '검정',
        'fuel': '가솔린',
        'transmission': '자동',
        'displacement': 3300,
        'seats': 5,
        'region': '서울',
        'accident_free': true,
        'status': 'on_sale',
        'seller_name': '김판매',
        'options': ['선루프', '내비게이션'],
        'description': '깨끗한 차량입니다.',
      });
      expect(d, isNotNull);
      expect(d!.bodyType, '대형차');
      expect(d.options, ['선루프', '내비게이션']);
      expect(d.accidentFree, isTrue);
    });

    test('옵션 null·설명 null 도 정상', () {
      final d = ListingDetail.fromMap({
        'id': 'x',
        'seller_id': 's1',
        'manufacturer': '기아',
        'model': '모닝',
        'body_type': '경차',
        'year': 2020,
        'price': 8000000,
        'mileage': 50000,
        'color': '흰색',
        'fuel': '가솔린',
        'transmission': '자동',
        'displacement': 998,
        'seats': 4,
        'region': '대구',
        'accident_free': false,
        'status': 'on_sale',
        'options': null,
        'description': null,
      });
      expect(d, isNotNull);
      expect(d!.options, isNull);
      expect(d.description, isNull);
      expect(d.accidentFree, isFalse);
    });

    test('필수 필드 누락은 null', () {
      expect(ListingDetail.fromMap({'id': 'x'}), isNull);
    });

    test('accident_free 가 누락/비bool 이면 null (무사고로 단정 안 함)', () {
      // 15필드는 모두 채우되 accident_free 만 빠진(또는 깨진) 응답.
      // DB 는 NOT NULL bool 이라 정상 경로에선 안 생기지만, 깨진 응답을
      // "무사고" 로 단정하면 중고차에서 오해 소지 → 못 찾음으로 처리한다.
      Map<String, Object?> full() => {
            'id': 'a1',
            'seller_id': 's1',
            'manufacturer': '현대',
            'model': '아반떼',
            'body_type': '준중형차',
            'year': 2021,
            'price': 15000000,
            'mileage': 30000,
            'color': '검정',
            'fuel': '가솔린',
            'transmission': '자동',
            'displacement': 1598,
            'seats': 5,
            'region': '서울',
            'status': 'on_sale',
          };
      // accident_free 키 없음 → null
      expect(ListingDetail.fromMap(full()), isNull);
      // accident_free 가 bool 이 아님 → null
      expect(ListingDetail.fromMap({...full(), 'accident_free': 'true'}), isNull);
      // 정상 bool 이면 매핑 성공
      final ok = ListingDetail.fromMap({...full(), 'accident_free': true});
      expect(ok, isNotNull);
      expect(ok!.accidentFree, isTrue);
    });
  });

  // 7.4 본인 매물 관리 행 모델 — 요약 6필드 + status 보존, 깨진 행 제외.
  group('OwnListing.fromMap', () {
    Map<String, dynamic> full() => {
          'id': 'own-1',
          'manufacturer': '기아',
          'model': 'K5',
          'year': 2022,
          'price': 31000000,
          'status': 'on_sale',
        };

    test('정상 6필드 → 행, status 보존', () {
      final o = OwnListing.fromMap(full());
      expect(o, isNotNull);
      expect(o!.id, 'own-1');
      expect(o.manufacturer, '기아');
      expect(o.model, 'K5');
      expect(o.year, 2022);
      expect(o.price, 31000000);
      expect(o.status, 'on_sale');
    });

    test('sold status 도 그대로 보존(본인은 sold 도 본다)', () {
      final o = OwnListing.fromMap({...full(), 'status': 'sold'});
      expect(o, isNotNull);
      expect(o!.status, 'sold');
    });

    test('숫자 문자열도 안전 변환', () {
      final o = OwnListing.fromMap({...full(), 'year': '2019', 'price': '20000000'});
      expect(o, isNotNull);
      expect(o!.year, 2019);
      expect(o.price, 20000000);
    });

    test('필수 필드 누락/타입 깨짐 → null(그 행 제외)', () {
      expect(OwnListing.fromMap({...full()}..remove('status')), isNull);
      expect(OwnListing.fromMap({...full()}..remove('id')), isNull);
      expect(OwnListing.fromMap({...full(), 'year': 'abc'}), isNull);
      expect(OwnListing.fromMap('not a map'), isNull);
    });
  });
}
