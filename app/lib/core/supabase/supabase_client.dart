// Supabase 클라이언트 부트스트랩.
// 앱 시작 시 한 번 initialize() 하면, 이후 어디서든 supabase 게터로 같은 인스턴스를 쓴다.
// web과 "동일한 Supabase 프로젝트"에 붙으므로(같은 auth.users·profiles·RLS) 계정이 호환된다.
import 'package:supabase_flutter/supabase_flutter.dart';

import 'env.dart';

/// 앱 부팅 시 호출. 환경변수 가드 → Supabase.initialize 순서.
/// supabase_flutter 는 기본적으로 세션을 로컬에 영속 저장하므로,
/// 앱을 껐다 켜도 로그인 상태가 유지된다(AC3).
Future<void> initSupabase() async {
  SupabaseEnv.assertConfigured(); // 키 누락이면 여기서 한국어로 멈춘다(불투명 실패 방지).
  await Supabase.initialize(
    url: SupabaseEnv.url,
    // web 과 "동일한 키"를 쓰기 위해 legacy anon key 파라미터를 그대로 사용한다.
    // (web 의 NEXT_PUBLIC_SUPABASE_ANON_KEY 와 같은 값. publishableKey 로 바꾸면 키가 달라짐.)
    // ignore: deprecated_member_use
    anonKey: SupabaseEnv.anonKey,
  );
}

/// 전역 Supabase 클라이언트 접근자. initialize 이후에만 유효.
SupabaseClient get supabase => Supabase.instance.client;
