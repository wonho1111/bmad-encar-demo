// 앱 부트스트랩의 **세션 만료 복구** 검사 (DW-836, 2026-08-13).
//
// 왜 이 파일이 생겼나: 실기기(갤럭시 S21)에서 실제로 밟았다. 폰에 남아 있던 예전 세션이 만료된
// 상태로 앱을 켜니 첫 화면이 "설정 필요"였고, 화면에는 로그인으로 가는 길이 없어 **앱 데이터를
// 지워야** 뚫렸다. 게다가 영문 예외 원문(`AuthApiException(... refresh_token_not_found)`)이 그대로
// 노출됐다. 세션 만료는 고장이 아니라 정상 수명주기(며칠 뒤 재실행·앱 재설치·토큰 회수)라,
// 데모 중 가장 밟기 쉬운 막다른 길이었다.
//
// ⚠️ **이 파일이 덮지 못하는 것(솔직히 적어 둔다)**: "인증 스트림이 error 상태가 되는" 그 순간
//    자체는 여기서 재현하지 못했다. 이 Riverpod 버전에서 StreamProvider를 override해 오류를
//    흘리면 상태가 `AsyncLoading(hasError: true)`로 남고 `.when()`이 **loading**으로 매핑된다(실측:
//    Stream.error / 컨트롤러 addError / create에서 throw 세 방식 모두 동일). 실기기에서는 실제로
//    error 분기가 그려졌으므로(스크린샷) 트리거 자체는 **기기 관측**이 근거다.
//    그래서 여기서는 그 뒤의 두 가지를 고정한다 — 둘 다 다음 사람이 조용히 되돌릴 수 있는 자리다:
//      ⓐ 정책: 어떤 오류를 "세션 문제"로 볼 것인가(`isExpiredSessionError`)
//      ⓑ 복구 화면이 실제로 하는 일(`ExpiredSessionRecovery`) — 세션을 정리하고 로그인으로 보낸다
import 'package:app/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  group('ⓐ 정책 — 무엇을 "세션 문제"로 보는가', () {
    test('인증 오류(만료된 갱신 토큰 포함)는 세션 문제다 — 설정 화면으로 보내지 않는다', () {
      expect(
        isExpiredSessionError(
          const AuthException(
            'Invalid Refresh Token: Refresh Token Not Found',
            code: 'refresh_token_not_found',
          ),
        ),
        isTrue,
        reason: '실기기에서 실제로 온 오류다 — 이걸 설정 문제로 보면 사용자가 앱 데이터를 지우는 '
            '것 말고 할 수 있는 게 없다',
      );
      // code로 좁히지 않는다: 만료·회수·서명불일치 등 다른 인증 오류도 결론은 같다(다시 로그인).
      expect(isExpiredSessionError(const AuthException('any auth failure')), isTrue);
    });

    test('그 밖의 오류는 여전히 설정 문제로 남는다(반대편 고정)', () {
      expect(
        isExpiredSessionError(Exception('환경변수를 못 읽었다')),
        isFalse,
        reason: '설정 오류까지 로그인 화면으로 보내면 원인이 화면에서 사라진다',
      );
    });
  });

  group('ⓑ 복구 화면 — 세션을 정리하고 앱을 계속 쓸 수 있는 화면으로 보낸다', () {
    // ✎ 실측으로 기대를 바로잡았다: 정리 후 도착지는 로그인 화면이 **아니라 홈**이다.
    //   이 앱은 FR58로 비로그인 열람을 허용하므로, 세션이 없는 사용자를 로그인으로 몰지 않고
    //   둘러볼 수 있는 홈으로 보낸다(app_router의 redirect 규칙). 이 검사가 고정하려는 것은
    //   "어디로 가느냐"의 특정 화면이 아니라 **막다른 길이 아니다**라는 것이다.
    testWidgets('정리가 끝나면 "설정 필요"가 아니라 앱 본화면(홈)이 뜬다', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(child: ExpiredSessionRecovery()),
      );

      // ⚠️ `pumpAndSettle`을 쓰면 안 된다 — 정리 중 화면의 CircularProgressIndicator가 끝없이
      //   애니메이션해 절대 settle되지 않는다(실측: 타임아웃). 프레임을 명시적으로 돌린다.
      // 제품 코드가 signOut에 3초 타임아웃을 걸어 두므로(네트워크가 막혀도 갇히지 않게)
      // 그보다 넉넉히 돌린다.
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 500));
      }

      expect(
        find.byKey(const Key('config_error')),
        findsNothing,
        reason: '복구 화면이 다시 설정 안내로 떨어지면 원래의 막다른 길로 되돌아간다',
      );
      expect(
        find.text('차장님'),
        findsWidgets,
        reason: '세션을 정리했으면 라우터가 앱 본화면으로 보내야 한다 — 스피너나 안내 화면에 '
            '머물면 사용자는 여전히 갇힌다(앱 데이터 삭제 말고는 길이 없던 그 상태)',
      );
      // 하단 탭이 있다 = 셸까지 정상적으로 올라왔다(빈 화면·부분 렌더가 아니다).
      expect(find.text('내차팔기'), findsWidgets);
    });
  });
}
