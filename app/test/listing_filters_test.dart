// 7.2 필터 검증 단위 테스트 — web search/page.tsx 검증 로직을 이식한 순수 함수.
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/listings/listing_filters.dart';

void main() {
  group('parseIntFilter', () {
    test('순수 숫자열만 통과', () {
      expect(parseIntFilter('30000000'), 30000000);
      expect(parseIntFilter('  100  '), 100);
    });
    test('빈 값·부호·소수·지수·16진은 미적용(null)', () {
      expect(parseIntFilter(''), isNull);
      expect(parseIntFilter(null), isNull);
      expect(parseIntFilter('-5'), isNull);
      expect(parseIntFilter('1.5'), isNull);
      expect(parseIntFilter('1e9'), isNull);
      expect(parseIntFilter('0x10'), isNull);
      expect(parseIntFilter('abc'), isNull);
    });
    test('안전 정수 상한 초과는 미적용(bigint 범위 보호)', () {
      expect(parseIntFilter('9007199254740991'), 9007199254740991);
      expect(parseIntFilter('9007199254740992'), isNull);
    });
  });

  group('pickOption', () {
    test('목록에 있는 값만 통과, 밖은 무시', () {
      expect(pickOption('SUV', ListingOptions.bodyType), 'SUV');
      expect(pickOption('비행기', ListingOptions.bodyType), isNull);
      expect(pickOption('', ListingOptions.bodyType), isNull);
      expect(pickOption(null, ListingOptions.bodyType), isNull);
    });
  });

  group('escapeLike', () {
    test('LIKE 메타문자(\\ % _)를 이스케이프', () {
      expect(escapeLike('50%'), r'50\%');
      expect(escapeLike('a_b'), r'a\_b');
      expect(escapeLike(r'x\y'), r'x\\y');
      expect(escapeLike('소나타'), '소나타'); // 일반 문자는 그대로
    });
  });

  group('ResolvedFilters.fromInput', () {
    test('가격 min>max 는 swap 으로 보정', () {
      final f = ResolvedFilters.fromInput(
        const ListingFilterInput(priceMin: '5000', priceMax: '1000'),
      );
      expect(f.priceMin, 1000);
      expect(f.priceMax, 5000);
    });
    test('연식 min>max 도 swap', () {
      final f = ResolvedFilters.fromInput(
        const ListingFilterInput(yearMin: '2024', yearMax: '2018'),
      );
      expect(f.yearMin, 2018);
      expect(f.yearMax, 2024);
    });
    test('한쪽만 있으면 그쪽만 적용', () {
      final f = ResolvedFilters.fromInput(
        const ListingFilterInput(priceMin: '1000'),
      );
      expect(f.priceMin, 1000);
      expect(f.priceMax, isNull);
    });
    test('키워드는 trim + escapeLike 적용', () {
      final f = ResolvedFilters.fromInput(
        const ListingFilterInput(keyword: '  50%할인  '),
      );
      expect(f.keyword, r'50\%할인');
    });
    test('빈 키워드는 null(미적용)', () {
      final f = ResolvedFilters.fromInput(const ListingFilterInput(keyword: '   '));
      expect(f.keyword, isNull);
    });
    test('목록 밖 드롭다운 값은 무시', () {
      final f = ResolvedFilters.fromInput(
        const ListingFilterInput(region: '하와이', fuel: '디젤'),
      );
      expect(f.region, isNull);
      expect(f.fuel, '디젤');
    });
  });
}
