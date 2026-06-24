// 7.3 등록 DB 에러 → 한국어 변환 단위 테스트(toKoreanListingError, web toKoreanError('create') 이식).
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:app/features/listings/listing_errors.dart';

void main() {
  group('toKoreanListingError', () {
    test('23514(check_violation) → 허용 목록/범위 안내', () {
      final e = const PostgrestException(
        message: 'new row for relation "listings" violates check constraint',
        code: '23514',
      );
      expect(toKoreanListingError(e), contains('허용 목록/범위'));
    });

    test('42501(RLS 거부) → 본인 명의 안내', () {
      final e = const PostgrestException(
        message: 'new row violates row-level security policy',
        code: '42501',
      );
      expect(toKoreanListingError(e), contains('본인 명의'));
    });

    test('그 외 코드 → 일반 등록 오류 안내', () {
      final e = const PostgrestException(message: 'boom', code: '500');
      expect(toKoreanListingError(e), contains('매물 등록 중 오류'));
    });

    test('PostgrestException 아닌 일반 예외 → 일반 등록 오류 안내', () {
      expect(toKoreanListingError(Exception('네트워크')), contains('매물 등록 중 오류'));
    });
  });
}
