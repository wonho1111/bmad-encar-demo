// 인증 상태·액션을 Riverpod 으로 노출한다.
// - authStateProvider: Supabase 세션 변화(로그인/로그아웃)를 스트림으로 흘려보낸다.
// - currentUserProvider / currentRoleProvider: 현재 사용자·역할을 파생.
// - authControllerProvider: 가입/로그인/로그아웃 액션 + 진행 상태(AsyncValue).
//
// 역할(role)은 세션의 user_metadata['role'] 에서 읽는다. web 가입이 이 메타데이터를
// 트리거 입력으로 쓰고, 트리거가 profiles 를 채우므로, 같은 값이 메타데이터에도 남는다.
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/supabase_client.dart';
import 'user_role.dart';

/// Supabase 세션 변화 스트림. 화면 분기(미인증/인증)의 단일 출처.
/// supabase_flutter 가 앱 시작 시 저장된 세션을 복원해 첫 이벤트로 흘려준다(세션 지속 AC3).
final authStateProvider = StreamProvider<AuthState>((ref) {
  return supabase.auth.onAuthStateChange;
});

/// 현재 로그인한 사용자(없으면 null). 세션 스트림에 의존해 자동 갱신.
final currentUserProvider = Provider<User?>((ref) {
  // 스트림이 아직 첫 값을 못 줬어도, 이미 복원된 세션이 있으면 그것을 본다.
  ref.watch(authStateProvider);
  return supabase.auth.currentUser;
});

/// 현재 사용자의 역할(메타데이터 기반). 미인증이거나 역할 미상이면 null.
final currentRoleProvider = Provider<UserRole?>((ref) {
  final user = ref.watch(currentUserProvider);
  if (user == null) return null;
  final raw = user.userMetadata?['role'] as String?;
  return UserRole.fromValue(raw);
});

/// 가입/로그인/로그아웃 액션. UI 는 이 컨트롤러의 AsyncValue 로 로딩/에러를 표시한다.
/// Riverpod 3 의 Notifier API 사용(StateNotifier 는 v3 에서 legacy 로 분리됨).
class AuthController extends Notifier<AsyncValue<void>> {
  @override
  AsyncValue<void> build() => const AsyncValue.data(null);

  /// 회원가입(FR1). 역할을 메타데이터에 실어 web 과 동일한 DB 트리거(handle_new_user)가
  /// profiles 를 role·status='active' 로 채우게 한다(앱이 직접 profiles INSERT 하지 않음).
  /// 반환: 안내가 필요한 경우의 메시지(이메일 확인 활성 시) 또는 null(즉시 로그인됨).
  Future<String?> signUp({
    required String email,
    required String password,
    required UserRole role,
  }) async {
    state = const AsyncValue.loading();
    try {
      final res = await supabase.auth.signUp(
        email: email,
        password: password,
        data: {'role': role.value}, // → auth.users.raw_user_meta_data.role (트리거가 읽음)
      );

      // 이메일 확인(Confirm email)이 켜져 있으면 중복 이메일이 에러 없이
      // identities: [] 빈 배열로 돌아온다(이메일 열거 방지). 이를 중복으로 해석한다.
      final identities = res.user?.identities;
      if (identities != null && identities.isEmpty) {
        state = const AsyncValue.data(null);
        throw const AuthException('user_already_exists');
      }

      state = const AsyncValue.data(null);

      // 세션이 즉시 생기면(이메일 확인 비활성) 자동 로그인 → 안내 불필요(null).
      if (res.session != null) return null;
      // 이메일 확인 활성 → 확인 메일 발송, 세션은 확인 후. 안내 문구 반환.
      return '가입 신청이 완료되었습니다. 이메일을 확인해 인증을 완료한 뒤 로그인해주세요.';
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }

  /// 로그인(FR2).
  Future<void> signIn({required String email, required String password}) async {
    state = const AsyncValue.loading();
    try {
      await supabase.auth.signInWithPassword(email: email, password: password);
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }

  /// 로그아웃(FR3). 세션을 파기하면 authStateProvider 가 미인증으로 흘려보낸다.
  Future<void> signOut() async {
    state = const AsyncValue.loading();
    try {
      await supabase.auth.signOut();
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }
}

final authControllerProvider =
    NotifierProvider<AuthController, AsyncValue<void>>(AuthController.new);
