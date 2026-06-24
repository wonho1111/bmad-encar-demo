// Supabase 인증 에러를 사용자용 한국어 메시지로 변환한다.
// (web 의 login/signup 페이지 toKoreanLoginError·toKoreanError 선례를 이식.)
// 원본 영어 메시지·코드는 화면에 직접 노출하지 않는다. 잘못된 자격은 보안상
// "이메일/비밀번호 중 무엇이 틀렸는지" 구분하지 않고 동일 문구로 안내한다.
import 'package:supabase_flutter/supabase_flutter.dart';

String toKoreanLoginError(Object error) {
  if (error is AuthException) {
    final code = error.code;
    final m = error.message.toLowerCase();
    if (code == 'invalid_credentials' || m.contains('invalid login credentials')) {
      return '이메일 또는 비밀번호가 올바르지 않습니다.';
    }
    if (code == 'email_not_confirmed' || m.contains('email not confirmed')) {
      return '이메일 인증이 완료되지 않았습니다. 받은 메일에서 인증을 완료해주세요.';
    }
  }
  return '로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}

String toKoreanSignupError(Object error) {
  if (error is AuthException) {
    final code = error.code;
    final m = error.message.toLowerCase();
    if (code == 'user_already_exists' ||
        m.contains('already registered') ||
        m.contains('already been registered')) {
      return '이미 가입된 이메일입니다. 다른 이메일을 사용하거나 로그인해주세요.';
    }
    if (m.contains('password')) {
      return '비밀번호가 너무 짧거나 약합니다. 더 긴 비밀번호를 사용해주세요.';
    }
    if (m.contains('email')) {
      return '유효한 이메일 주소를 입력해주세요.';
    }
  }
  return '가입 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}
