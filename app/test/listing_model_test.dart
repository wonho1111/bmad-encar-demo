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
  });
}
