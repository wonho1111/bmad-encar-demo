// Supabase 연결에 필요한 환경변수를 한 곳에서 읽고, 누락 시 "어떤 변수가 비었는지"를
// 명확한 한국어 에러로 알린다. (web의 lib/supabase/env.ts 선례를 Flutter로 이식)
//
// 값은 코드에 하드코딩하지 않고 빌드 시점에 주입한다.
//   flutter build web --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_ANON_KEY=...
//   또는  --dart-define-from-file=.env.json  (app/.env.json 은 .gitignore로 보호)
//
// String.fromEnvironment 는 "컴파일 타임 상수"라서 반드시 const 로 읽어야 주입값이 들어온다.
// (값이 비어 있으면 빈 문자열 '' 이 되고, 아래 가드가 한국어로 알려준다.)
class SupabaseEnv {
  // anon key 는 RLS 가 보호하므로 클라이언트 노출이 안전하다(service_role 키는 쓰지 않는다).
  static const String url = String.fromEnvironment('SUPABASE_URL');
  static const String anonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

  // AI 검색(/ai/search)을 부를 FastAPI 주소(7.2). web 의 NEXT_PUBLIC_API_BASE_URL 과 같은 값
  // (Cloud Run dev 서비스 encar-ai-api-dev URL). 매물 탐색·상세는 Supabase 만으로 동작하므로
  // 이 값은 "AI 호출 시점"에만 가드한다(아래 isConfigured 는 Supabase 키만 본다).
  static const String apiBaseUrl = String.fromEnvironment('API_BASE_URL');

  /// 누락된 환경변수가 있으면 무엇이 비었는지 한국어로 알리고 throw 한다.
  /// 불투명한 런타임 에러(예: 빈 URL로 초기화 실패) 대신 원인을 바로 진단하게 한다.
  static void assertConfigured() {
    final missing = <String>[];
    if (url.isEmpty) missing.add('SUPABASE_URL');
    if (anonKey.isEmpty) missing.add('SUPABASE_ANON_KEY');

    if (missing.isNotEmpty) {
      throw StateError(
        'Supabase 환경변수가 설정되지 않았습니다: ${missing.join(', ')}. '
        '빌드 시 --dart-define 또는 --dart-define-from-file 로 값을 주입해주세요 '
        '(app/.env.example 참고). 값은 web의 NEXT_PUBLIC_SUPABASE_* 와 동일합니다.',
      );
    }
  }

  /// 환경변수가 모두 채워졌는지(빌드에 주입됐는지) 여부. 화면에서 가드 안내 분기에 쓴다.
  /// (Supabase 키만 본다 — 탐색·상세는 API 없이도 동작해야 하므로 API_BASE_URL 은 제외.)
  static bool get isConfigured => url.isNotEmpty && anonKey.isNotEmpty;

  /// AI 검색 API 주소가 주입됐는지. AI 채팅 화면이 호출 전에 이걸로 가드한다.
  static bool get isApiConfigured => apiBaseUrl.isNotEmpty;
}
