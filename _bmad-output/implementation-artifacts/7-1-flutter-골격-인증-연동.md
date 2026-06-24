---
baseline_commit: 7b7a5964986c5e13a44d57ebe2f80f535867c895
---
# Story 7.1: Flutter 골격 + 인증 연동

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want Flutter 앱 골격(`app/`)을 만들고 `supabase_flutter` + Riverpod로 web과 동일한 Supabase 프로젝트에 인증을 연결하고 싶다,
so that 모바일 통합 리스크(빌드 toolchain·세션·환경변수 주입)를 Epic 7 초반에 미리 제거하고, 이후 7.2~7.5 화면이 올라설 안전한 토대를 만든다.

## Acceptance Criteria

1. **(AC1 — 골격 생성·빌드)** `app/`가 `flutter create`(org `com.encardemo`)로 생성되고, `flutter analyze`가 0 error로 통과하며 `flutter build web`이 성공한다.
   - *근거*: epics.md 7.1 "Given `app/`가 `flutter create`로 생성되면 / When 앱을 실행하면 / Then 기동된다". 이번 Epic은 실폰/에뮬레이터 대신 **web 빌드로 기동을 검증**한다(handoff §3·테스트 전략).

2. **(AC2 — 인증 연동, FR1~3 재현)** `supabase_flutter` + `flutter_riverpod`가 설정되고, 가입(FR1)/로그인(FR2)/로그아웃(FR3)이 **web과 동일한 Supabase 프로젝트·계정**으로 동작한다.
   - 가입: 이메일·비밀번호 + 역할(구매자/판매자) 선택 → `auth.signUp`의 `data: {'role': ...}`로 역할을 메타데이터에 실어, web과 동일한 DB 트리거 `handle_new_user`가 `profiles`에 role·status='active' 행을 만든다.
   - 로그인: 이메일·비밀번호 → 세션 생성.
   - 로그아웃: 세션 파기 → 미인증 상태로 복귀.
   - web에서 만든 계정으로 앱 로그인이 되고, 앱에서 만든 계정으로 web 로그인이 되어야 한다(같은 `auth.users`).

3. **(AC3 — 세션 지속·역할별 착지)** 앱 재시작 후에도 로그인 세션이 유지(`supabase_flutter` 기본 영속 세션)되고, 인증 상태에 따라 화면이 분기한다: 미인증 → 로그인/가입 화면, 인증 → 역할 홈(buyer·seller 공통 홈, nav-ia-rules §1 R1 상위집합 원칙). **관리자는 모바일 제외(AR9)** — admin 역할로 로그인 시 "관리자는 web에서 이용해주세요" 안내 후 로그아웃(또는 진입 차단).

4. **(AC4 — 환경변수 주입 구조)** Supabase URL·anon key는 **코드에 하드코딩하지 않고** `--dart-define`(또는 `String.fromEnvironment`) 기반 컴파일 타임 주입으로 읽는다. 키 누락 시 한국어로 "어떤 변수가 비었는지" 알리는 가드를 둔다(web `getSupabaseEnv` 선례 이식). `.env`류 실비밀값은 `.gitignore`로 커밋 제외.

5. **(AC5 — 빌드 산출물 정적 검증)** `flutter build web` 산출물을 정적 서버로 띄워 **로그인 화면이 렌더**되는지 Playwright로 자체 확인한다(키가 주입돼 있으면 실제 가입/로그인 1회 스모크까지, 키가 없으면 가드 메시지 렌더까지).

## Tasks / Subtasks

- [x] **Task 1 — Flutter 골격 생성** (AC: #1)
  - [x] `flutter create --org com.encardemo app` 로 저장소 루트에 `app/` 생성 (PATH에 `~/flutter/bin` 필요)
  - [x] `flutter config --enable-web` 확인(이미 활성). 불필요 플랫폼 폴더(예: ios/macos/windows 일부)는 남겨도 무방하나 web 빌드가 핵심
  - [x] 루트 `.gitignore`에 Flutter 항목 이미 존재(`.dart_tool/`, `build/`, `*.iml`) — 추가로 `app/.env`류·`app/web/build` 누락분 점검
  - [x] `flutter pub get` 성공 확인

- [x] **Task 2 — 의존성·환경변수 토대** (AC: #2, #4)
  - [x] `pubspec.yaml`에 `supabase_flutter`, `flutter_riverpod`(architecture: `^3.3.2`) 추가 후 `flutter pub get`
  - [x] `lib/core/supabase/env.dart` — `String.fromEnvironment('SUPABASE_URL')`·`SUPABASE_ANON_KEY` 읽고 누락 시 한국어 에러(web `env.ts` 선례 이식)
  - [x] `lib/core/supabase/supabase_client.dart` — `Supabase.initialize(url, anonKey)` 부트스트랩 + `client` 접근자
  - [x] `app/.env.example`(또는 README)에 빌드 시 `--dart-define-from-file` 또는 `--dart-define` 사용법 문서화. 실제 키는 `app/.env`(gitignore)로

- [x] **Task 3 — 인증 레이어 (Riverpod)** (AC: #2, #3)
  - [x] `lib/features/auth/` 에 auth 상태 provider: `supabase.auth.onAuthStateChange` 스트림을 `StreamProvider`/`Notifier`로 노출(미인증/인증/역할)
  - [x] 역할 조회: 세션의 `user.userMetadata['role']` 우선, 필요 시 `profiles` 조회 폴백(RLS상 본인 행은 읽힘)
  - [x] signUp/signIn/signOut 액션 함수 — web `signup`/`login`/`LogoutButton` 동작 포팅(역할 메타데이터·에러 한국어 변환 포함)
  - [x] Supabase 에러 → 한국어 메시지 변환 헬퍼(web `toKoreanLoginError`/`toKoreanError` 선례 이식: invalid_credentials, user_already_exists, 약한 비밀번호 등)

- [x] **Task 4 — 화면·라우팅** (AC: #2, #3)
  - [x] 로그인 화면(이메일·비밀번호), 가입 화면(이메일·비밀번호·역할 라디오 buyer/seller), 홈(인증 후, 역할·이메일 표시 + 로그아웃 버튼)
  - [x] `main.dart` — `ProviderScope` + auth 상태에 따른 화면 분기(미인증→Auth, buyer/seller→Home, admin→안내 후 차단)
  - [x] Material 기본 위젯 사용(architecture: 앱은 기본 Material). 화면 구성은 7.2~ 에서 확장되므로 7.1은 토대만(풀패리티 금지)

- [x] **Task 5 — 검증** (AC: #1, #5)
  - [x] `flutter analyze` 0 error 확인(로그 보고)
  - [x] `flutter build web` 성공 확인(로그 보고)
  - [x] 산출물(`app/build/web`)을 정적 서버로 띄우고 Playwright로 로그인 화면 렌더 확인. 키 주입 시 가입→로그아웃→로그인 스모크 1회

## Dev Notes

### 핵심 계약(이월 자산 — 코드 아님, 규칙·계약만)
- **동일 Supabase 프로젝트**: web과 같은 프로젝트(`psrnsasxpkpwqdukjdmt.supabase.co`)·같은 `auth.users`·같은 `profiles`/RLS를 쓴다. 모바일은 새 백엔드를 만들지 않는다. (handoff §1·§4, nav-ia-rules §4)
- **연결값**: `SUPABASE_URL`·`SUPABASE_ANON_KEY`는 web의 `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY`와 **같은 값**. anon key는 RLS가 보호하므로 클라이언트 노출 안전(service_role 사용 금지). (.env.example §app, architecture)
  - 실제 값은 Supabase MCP로 확인 가능(URL `https://psrnsasxpkpwqdukjdmt.supabase.co`, anon key는 legacy JWT). 빌드 검증용으로 `app/.env`(gitignore)에 넣어 `--dart-define-from-file`로 주입한다. **키 값을 코드/커밋에 박지 말 것.**
- **가입 트리거 계약(재현 핵심)**: web `signup`은 `options: { data: { role } }`로 역할을 `auth.users.raw_user_meta_data.role`에 싣고, DB 트리거 `handle_new_user`가 이를 읽어 `profiles`를 채운다. Flutter도 `supabase.auth.signUp(..., data: {'role': role})`로 **동일 트리거 경로**를 타야 한다(앱이 직접 profiles INSERT 하지 않음). (web/src/app/(auth)/signup/page.tsx:65-69)
- **역할 enum**: `buyer`·`seller`·`admin` (profiles.role CHECK). 가입 가능 역할은 buyer/seller만(admin은 web 트리거가 차단). (web/src/lib/constants.ts:25-30)
- **역할별 착지(nav-ia-rules §1)**: buyer→홈, seller→홈(구매자 홈 상위집합 = 구매자 동선 + 판매 진입, R1), admin→**모바일 제외**(AR9, 안내 후 차단). 7.1은 홈을 "토대"로만(역할·이메일·로그아웃). 탐색 미리보기/AI FAB 등은 7.2부터.

### web 인증 동작(포팅 대상 — React→Flutter 위젯트리 새로 짬, 동작·에러문구만 이월)
- 로그인: `supabase.auth.signInWithPassword({email, password})`, 세션 없으면 거짓성공 방지, 에러는 한국어 변환(invalid_credentials/email_not_confirmed). [Source: web/src/app/(auth)/login/page.tsx]
- 가입: `signUp` 후 `data.user.identities.length === 0`이면 "이미 가입된 이메일"(이메일 확인 켜진 경우 중복 신호), 비밀번호 6자 미만 사전 차단. [Source: web/src/app/(auth)/signup/page.tsx]
- 로그아웃: `supabase.auth.signOut()` 후 미인증 화면으로. [Source: web/src/components/auth/LogoutButton.tsx]
- 환경변수 가드: 누락 시 "어떤 변수가 비었는지" 한국어 throw. [Source: web/src/lib/supabase/env.ts]

### 아키텍처 준수(가드레일)
- **스택 고정**: Flutter 3.44(설치본 3.44.3, 패치 차이 무방) + `flutter_riverpod ^3.3.2` + `supabase_flutter`. AI 호출은 추후 dio/http(7.2). [Source: architecture.md L83, L127, L213]
- **폴더 구조**: `lib/core/{supabase, router, theme, format}/` + `lib/features/{auth, listings, ai_search, chat}/`. 7.1은 `core/supabase`·`features/auth`(+ 최소 router)만 채운다. [Source: architecture.md L368-376]
- **Riverpod 컨벤션**: provider명 `<name>Provider`, 비동기는 `AsyncValue`(로딩/에러/데이터), 상태는 항상 불변 갱신. [Source: architecture.md L285, L290]
- **인증 흐름**: 클라이언트가 Supabase 세션 토큰 보관 → (7.2~) AI 호출 시 `Authorization: Bearer <jwt>`. 7.1은 세션 보관·복원까지. [Source: architecture.md L295]
- **에러/로딩**: 사용자 노출은 한국어, 내부 로그는 코드·원인. 앱은 `AsyncValue.error`/`AsyncLoading`로 지역(local) 처리. [Source: architecture.md L290-291]
- **린트**: `flutter_lints` + `dart analyze`로 강제(flutter create 기본 포함). [Source: architecture.md L302]
- **org 옵션**: `flutter create --org com.encardemo app`. [Source: architecture.md L97]

### 통합 토대로서의 엄격성(handoff)
- 7.1은 토대라 인증 연동이 애매하면 자율 통과보다 **escalate**. 특히 가입 트리거 경로(role 메타데이터→profiles)가 web과 동일하게 동작하는지 확인이 핵심.
- 이번 Epic 검증은 **실폰/에뮬레이터/Chrome 데스크톱 없이 `flutter build web` + Playwright**. `flutter run -d chrome`·`-d linux` 금지(toolchain 미비). [입력 프롬프트·handoff §3]

### Project Structure Notes
- 신규 디렉터리: 저장소 루트 `app/`(전체 Flutter 프로젝트). 기존 `web/`·`api/`·`supabase/`와 형제. 모노레포 폴더 구조와 정합(architecture L111, L368).
- `.gitignore` 루트에 Flutter 블록 이미 존재(`.dart_tool/`, `build/`, `*.iml`) — `app/build/`·`app/.dart_tool/` 자동 제외됨. `app/.env`는 루트 `.env.*` 규칙으로 이미 제외(단 `app/.env` 경로가 루트 패턴에 잡히는지 점검, 안 잡히면 `app/.gitignore` 또는 루트에 추가).
- 충돌·변이: 없음. 단 `flutter create`가 만드는 `app/` 표준 산출물이 많으므로(여러 플랫폼 폴더) 커밋 시 빌드/툴 산출물만 제외하고 소스는 포함.

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1] — AC 원문
- [Source: _bmad-output/planning-artifacts/nav-ia-rules.md#§1, §4] — 역할 착지·공유 계약
- [Source: _bmad-output/implementation-artifacts/epic7-entry-handoff.md] — 테스트 전략·이월 자산·escalate 정책
- [Source: _bmad-output/planning-artifacts/architecture.md#L83-L127, L213, L285-302, L368-376] — 스택·폴더·컨벤션
- [Source: web/src/app/(auth)/signup/page.tsx, login/page.tsx] — 가입·로그인 동작·에러 문구
- [Source: web/src/components/auth/LogoutButton.tsx] — 로그아웃
- [Source: web/src/lib/supabase/env.ts, client.ts] — 환경변수 가드·클라이언트 생성
- [Source: web/src/lib/constants.ts#USER_ROLE] — 역할 enum
- [Source: .env.example#app] — app 환경변수 계약(SUPABASE_URL/ANON_KEY = web과 동일값)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (BMad dev-story 서브에이전트)

### Debug Log References

- `flutter create --org com.encardemo --platforms web,android app` → 42 files, 성공
- `flutter pub add supabase_flutter flutter_riverpod` → supabase_flutter ^2.15.0, flutter_riverpod ^3.3.2
- `flutter analyze` → **No issues found!** (초기 14건 → Riverpod 3 Notifier API 전환 + anonKey 이그노어로 해소)
- `flutter test` → **All tests passed!** (8 tests: UserRole 3 + 한국어 에러변환 5)
- `flutter build web --dart-define-from-file=.env.json` → **✓ Built build/web** (main.dart.js 2.6M; 번들에 Supabase URL·anon key·역할값·한국어 문자열(\uXXXX) 컴파일 확인)
- HTTP 스모크(live Supabase, web과 동일 프로젝트 `psrnsasxpkpwqdukjdmt`):
  - signup(data:{role:seller}) → access_token 발급(이메일확인 OFF=즉시세션), `profiles` 행 role=seller·status=active·name 자동기록(트리거 handle_new_user 동작 확인)
  - login(정답) → 200 / login(오답) → 400 (FR2 + invalid_credentials 경로)

### Completion Notes List

- **구현 요약**: `app/` Flutter 골격 생성 + `supabase_flutter`/`flutter_riverpod`로 인증 연동. web과 동일 Supabase 프로젝트를 쓰며, 가입은 web과 똑같이 role을 메타데이터에 실어 DB 트리거가 profiles를 채우는 경로(앱이 직접 INSERT 안 함)를 탄다.
- **Riverpod 3 주의**: `flutter_riverpod ^3.3.2`에서 `StateNotifier`/`StateNotifierProvider`가 legacy로 분리됨. 모던 `Notifier<AsyncValue<void>>` + `NotifierProvider`로 구현(7.2~ 일관 적용 권장).
- **환경변수 주입**: 코드 하드코딩 금지. `String.fromEnvironment` + `--dart-define-from-file=.env.json`(gitignore). 키 누락 시 한국어 가드 화면(`ConfigErrorScreen`)으로 폴백 — 앱이 통째로 죽지 않게.
- **역할 착지**: buyer/seller→공통 홈(nav-ia §1 R1), admin→차단 안내 후 로그아웃(AR9 모바일 제외).
- **escalate(사용자 직접 처리)**:
  1. **`.env` 실키 주입** — 빌드 검증엔 Supabase MCP로 얻은 실값을 `app/.env.json`(gitignore, 커밋 제외)에 넣어 통과시켰음. 저장소엔 `app/.env.example`만 들어감. 이후 개발/배포 빌드 시 사용자가 `app/.env.json` 구성 필요(값=web의 NEXT_PUBLIC_SUPABASE_*와 동일).
  2. **Playwright 라이브 브라우저 렌더 검증 미수행** — MCP가 `chrome` 채널(`/opt/google/chrome/chrome`) 고정인데 미설치, Playwright 번들 chromium도 `libnspr4.so` 등 시스템 라이브러리 누락(설치에 sudo/apt 필요). 대신 ① 빌드 산출물 정적 검증(번들에 env·문자열 컴파일 확인) ② live Supabase HTTP 스모크(가입→profiles 트리거→로그인→오답차단)로 AC1·AC2를 실증. 화면 픽셀 렌더 확인은 사용자가 `flutter run -d chrome`(데스크톱 Chrome) 또는 시스템 의존성 설치 후 가능.
- **테스트 데이터 잔여**: live Supabase에 `flutter71test*@example.com` 2건 생성됨(스모크용). 안전 분류기가 auth.users DELETE를 차단해 미삭제. RLS 격리된 무해 계정이나, 정리하려면 Supabase 콘솔 Authentication에서 삭제 권장.

### File List

신규:
- `app/` (flutter create 표준 산출물 전체: `pubspec.yaml`, `lib/main.dart`(덮어씀), `web/`, `android/`, `test/widget_test.dart`(덮어씀) 등)
- `app/lib/core/supabase/env.dart` — 환경변수 가드(web env.ts 이식)
- `app/lib/core/supabase/supabase_client.dart` — Supabase.initialize 부트스트랩
- `app/lib/features/auth/user_role.dart` — 역할 enum(web constants 일치)
- `app/lib/features/auth/auth_errors.dart` — Supabase 에러 한국어 변환
- `app/lib/features/auth/auth_controller.dart` — Riverpod auth 상태·액션(Notifier)
- `app/lib/features/auth/login_screen.dart` — 로그인(FR2)
- `app/lib/features/auth/signup_screen.dart` — 가입+역할선택(FR1)
- `app/lib/features/auth/home_screen.dart` — 인증 후 홈(토대)
- `app/lib/features/auth/admin_blocked_screen.dart` — 관리자 모바일 차단(AR9)
- `app/.env.example` — 환경변수 주입 사용법 문서(커밋됨)

수정:
- `app/lib/main.dart` — ProviderScope + Supabase init + auth 게이트로 전면 재작성
- `app/test/widget_test.dart` — 기본 카운터 테스트 → 7.1 토대 단위 테스트로 교체

커밋 제외(gitignore): `app/.env.json`, `app/build/`, `app/.dart_tool/`
