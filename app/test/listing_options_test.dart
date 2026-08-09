// spec-16-9(DW-760 해소) — `options.dart`의 옵션 우선순위 선택 로직 단위테스트(web
// options.test.ts의 topOptions/optionPriority 스위트 미러). 카드 옵션 칩이 이 함수들만 쓰므로
// 여기가 그 선택 로직의 유일한 검증 지점이다.
import 'package:app/features/listings/options.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('optionPriority', () {
    test('희소·셀링포인트(high) 옵션은 10점', () {
      expect(optionPriority('선루프'), 10);
      expect(optionPriority('통풍시트'), 10);
    });

    test('보편(common) 옵션은 0점(최하위)', () {
      expect(optionPriority('스마트키'), 0);
      expect(optionPriority('블루투스'), 0);
    });

    test('통제어휘 안이지만 high/common 어디에도 없으면 mid(5점)', () {
      expect(optionPriority('내비게이션'), 5);
    });

    test('통제어휘 밖(정크·레거시) 값은 mid가 아니라 최하위(0점)로 강등된다', () {
      expect(optionPriority('존재하지않는옵션'), 0);
    });
  });

  group('topOptions', () {
    test('빈 배열/null이면 빈 배열', () {
      expect(topOptions(const [], 3), isEmpty);
      expect(topOptions(null, 3), isEmpty);
    });

    test('희소 옵션이 있으면 우선 노출되고, 동점은 입력 순서를 유지한다(stable)', () {
      final result = topOptions(
        const ['선루프', '통풍시트', '내비게이션', '스마트키', '라디오'],
        3,
      );
      expect(result, ['선루프', '통풍시트', '내비게이션']);
    });

    test('전부 보편이면 자연히 보유한 보편 옵션 상위 n개로 채워진다(별도 fallback 분기 없음)', () {
      final result = topOptions(const ['라디오', '스마트키', '블루투스'], 3);
      expect(result, ['라디오', '스마트키', '블루투스']);
    });

    test('입력 중복은 제거한다(같은 칩이 두 번 뜨는 것 방지)', () {
      final result = topOptions(const ['선루프', '선루프', '스마트키'], 3);
      expect(result, ['선루프', '스마트키']);
    });

    test('n을 초과하면 상위 n개만 반환한다', () {
      final result = topOptions(const ['선루프', '통풍시트', '나파가죽'], 2);
      expect(result, hasLength(2));
      expect(result, ['선루프', '통풍시트']);
    });
  });
}
