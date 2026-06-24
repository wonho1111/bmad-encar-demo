// 매물 등록 시 DB 에러를 사용자용 한국어 메시지로 변환한다.
// (web SellForm.tsx 의 toKoreanError('create') 선례 이식.)
//
// 원본 영어 메시지·에러코드는 화면에 직접 노출하지 않는다(콘솔/디버그 로그용).
// Postgres 표준 에러코드(SQLSTATE)로 분기:
//   · 23514 = check_violation — 고정목록 밖 값·범위 위반(클라이언트 검증을 우회해 DB 까지 닿은 경우의 최종 방어).
//   · 42501 = insufficient_privilege — RLS 거부(seller_id 위조 등 본인 명의 아님).
import 'package:supabase_flutter/supabase_flutter.dart';

/// 등록(INSERT) 실패 에러 → 한국어 안내. PostgrestException.code 우선, 그 외엔 일반 안내.
String toKoreanListingError(Object error) {
  if (error is PostgrestException) {
    final code = error.code ?? '';
    if (code == '23514') {
      // CHECK 위반 — 허용 목록/범위를 벗어남.
      return '입력값이 허용 목록/범위를 벗어났습니다. 선택 항목과 숫자 범위를 확인해주세요.';
    }
    if (code == '42501') {
      // RLS 거부 — 본인 명의로만 등록 가능(seller_id 위조 차단).
      return '본인 명의로만 매물을 등록할 수 있습니다. 다시 로그인 후 시도해주세요.';
    }
  }
  return '매물 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}
