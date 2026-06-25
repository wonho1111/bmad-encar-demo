// 7.1 토대 단위 테스트.
// 위젯/화면 테스트는 Supabase 전역 초기화에 의존해 무겁고 깨지기 쉬우므로,
// 여기서는 초기화가 필요 없는 "순수 로직"(역할 enum·에러 한국어 변환)을 검증한다.
// 화면 렌더·인증 E2E 는 flutter build web + Playwright 로 따로 확인한다(스토리 Task 5).
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_errors.dart';
import 'package:app/features/auth/user_role.dart';

void main() {
  group('UserRole', () {
    test('가입 가능 역할은 buyer/seller 뿐(admin 제외)', () {
      expect(UserRole.signupRoles, [UserRole.buyer, UserRole.seller]);
      expect(UserRole.signupRoles.contains(UserRole.admin), isFalse);
    });

    test('value 는 DB(profiles.role)·web constants 와 일치', () {
      expect(UserRole.buyer.value, 'buyer');
      expect(UserRole.seller.value, 'seller');
      expect(UserRole.admin.value, 'admin');
    });

    test('fromValue 는 문자열→enum, 미상은 null', () {
      expect(UserRole.fromValue('seller'), UserRole.seller);
      expect(UserRole.fromValue(null), isNull);
      expect(UserRole.fromValue('unknown'), isNull);
    });
  });

  group('한국어 에러 변환', () {
    test('잘못된 자격은 구분 없이 동일 문구(code 기반)', () {
      final msg = toKoreanLoginError(
          const AuthException('Invalid login credentials', code: 'invalid_credentials'));
      expect(msg, '이메일 또는 비밀번호가 올바르지 않습니다.');
    });

    test('이메일 미인증 안내(code 기반)', () {
      final msg = toKoreanLoginError(
          const AuthException('Email not confirmed', code: 'email_not_confirmed'));
      expect(msg, contains('이메일 인증'));
    });

    test('중복 이메일 가입 안내(code 기반)', () {
      final msg = toKoreanSignupError(
          const AuthException('User already registered', code: 'user_already_exists'));
      expect(msg, contains('이미 가입된 이메일'));
    });

    test('약한 비밀번호 안내(message 기반 폴백)', () {
      final msg = toKoreanSignupError(
          const AuthException('weak password: password is too short'));
      expect(msg, contains('비밀번호'));
    });

    test('알 수 없는 에러는 일반 안내로 폴백', () {
      final msg = toKoreanLoginError(Exception('boom'));
      expect(msg, contains('오류가 발생'));
    });
  });
}
