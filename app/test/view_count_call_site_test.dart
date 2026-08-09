// increment_listing_view 호출 지점 단일성 검사(Story 16.6, DW-740 해소) — web
// viewCountCallSite.test.ts(Story 11.1)의 앱 미러(같은 소스텍스트 스캔 방식, CLAUDE.md B9
// "지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 앱은 웹과 층 구조가 다르다(spec-16-6 Design Notes — RPC는 위젯이 아니라 리포지토리
// 계층에 둔다, chat_repository.dart의 _client.rpc(...) 패턴 미러). 그래서 이 파일은 두
// 층을 각각 잠근다:
//   1) RPC 함수명 문자열 'increment_listing_view' 자체는 app/lib 전체에서 정확히 1개 파일
//      (listings_repository.dart), 1회만 등장한다 — view_count 쓰기의 유일한 통로.
//   2) 그 리포지토리 메서드(incrementListingView)를 부르는 곳은 app/lib 전체에서 정확히
//      1개 파일(listing_detail_screen.dart), 1회만 등장하고, `_DetailContentState`의
//      `initState()` 안에서 호출된다 — 상세 화면이 매물 확인 후 처음 빌드될 때 정확히
//      한 번만 발화한다(둘이면 한 열람에 view_count가 2 오른다).
//
// 이 검사가 안 보는 것(web 원본과 동일한 한계):
//   · 런타임에 실제로 몇 번 호출되는지(정적 소스 스캔이지 실행 추적이 아니다) — 실기기
//     확인(spec-16-6 Manual checks)의 몫이다.
//   · 이름을 문자열 리터럴이 아니라 동적으로 조립하는 경우 — 이 리포에 그런 패턴이 없다.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

const _rpcFnName = 'increment_listing_view';
const _repoMethodCall = 'incrementListingView(';
const _repoFile = 'lib/features/listings/listings_repository.dart';
const _screenFile = 'lib/features/listings/listing_detail_screen.dart';

/// `lib/` 전체(테스트·플랫폼 폴더 제외 — `flutter test`의 cwd는 `app/`)의 .dart 파일 경로.
List<String> _collectLibDartFiles() {
  final dir = Directory('lib');
  return [
    for (final entry in dir.listSync(recursive: true))
      if (entry is File && entry.path.endsWith('.dart')) entry.path,
  ];
}

int _countOccurrences(String content, String needle) {
  var count = 0;
  var start = 0;
  while (true) {
    final index = content.indexOf(needle, start);
    if (index < 0) break;
    count++;
    start = index + needle.length;
  }
  return count;
}

void main() {
  test('RPC 함수명은 app/lib 전체에서 정확히 1개 파일(listings_repository.dart), 1회만 등장한다', () {
    // Dart는 백틱을 문자열 리터럴로 인식하지 않는다(웹 TS와 다른 지점 — web 원본이 백틱까지
    // 세는 이유는 템플릿 리터럴로 실제 호출을 숨길 수 있어서다). Dart에서 백틱은 오직
    // `///` 문서 주석의 마크다운 코드 스팬으로만 쓰이므로(이 리포 관례 — 예:
    // chat_repository.dart의 "`chat_unread_count` RPC(0024)"), 백틱까지 세면 정상적인 문서
    // 주석 언급이 "코드 호출"로 오탐된다. 그래서 작은따옴표·큰따옴표 2종만 스캔한다.
    final quoted = ["'$_rpcFnName'", '"$_rpcFnName"'];
    final matches = <String, int>{};

    for (final path in _collectLibDartFiles()) {
      final content = File(path).readAsStringSync();
      final count =
          quoted.fold<int>(0, (sum, q) => sum + _countOccurrences(content, q));
      if (count > 0) matches[path] = count;
    }

    expect(matches.keys.toList(), [_repoFile]);
    expect(matches[_repoFile], 1);
  });

  test('그 RPC 호출은 _client.rpc(...)로 이뤄지고 p_listing_id 키를 쓰며, 주석이 아니다', () {
    final content = File(_repoFile).readAsStringSync();

    // `_client.rpc(` 시작점부터 200자 안에 함수명과 p_listing_id 키가 함께 있어야 한다 —
    // 실제 코드가 여러 줄(rpc(\n  'name',\n  params: {...},\n))로 포맷돼도 잡히도록 줄바꿈
    // 무관 윈도우로 본다(web 원본은 단일 줄 호출이라 같은 줄 검사로 충분했지만, 앱은
    // 리포지토리 메서드 안이라 여러 줄로 포맷된다).
    final rpcCallIndex = content.indexOf('_client.rpc(');
    expect(rpcCallIndex, greaterThanOrEqualTo(0),
        reason: '_client.rpc(...) 호출 자체가 있어야 한다');

    final windowEnd = (rpcCallIndex + 200).clamp(0, content.length);
    final window = content.substring(rpcCallIndex, windowEnd);
    expect(window, contains("'$_rpcFnName'"));
    expect(window, contains('p_listing_id'));

    // 주석 처리 방어 — `_client.rpc(` 가 실제로 시작되는 줄에 `//`가 그 코드보다 앞서 있으면
    // 그 줄 전체가 주석이라는 뜻이다(web 3번째 테스트와 동일 원칙).
    final lineStart = content.lastIndexOf('\n', rpcCallIndex) + 1;
    final lineEndRaw = content.indexOf('\n', rpcCallIndex);
    final lineEnd = lineEndRaw < 0 ? content.length : lineEndRaw;
    final line = content.substring(lineStart, lineEnd);
    final commentIndex = line.indexOf('//');
    final callIndexInLine = line.indexOf('_client.rpc(');
    expect(commentIndex == -1 || commentIndex > callIndexInLine, isTrue,
        reason: '_client.rpc(...) 호출이 주석이 아니라 살아 있는 코드여야 한다');
  });

  test(
      '리포지토리 메서드(incrementListingView) 호출은 app/lib 전체에서 정확히 1개 파일'
      '(listing_detail_screen.dart), 1회만 등장한다', () {
    final matches = <String, int>{};

    for (final path in _collectLibDartFiles()) {
      // 정의 파일(listings_repository.dart) 자신의 메서드 선언(`Future<void>
      // incrementListingView(...)`)은 "호출"이 아니므로 스캔에서 뺀다 — web 원본은 이런
      // 자기참조가 없어(정의·호출이 같은 파일에 없음) 이 예외가 필요 없었지만, 앱은
      // 리포지토리 계층 분리 때문에 이 구분이 필요하다(위 헤더 주석 "층 구조가 다르다").
      if (path == _repoFile) continue;
      final content = File(path).readAsStringSync();
      final count = _countOccurrences(content, _repoMethodCall);
      if (count > 0) matches[path] = count;
    }

    expect(matches.keys.toList(), [_screenFile]);
    expect(matches[_screenFile], 1);
  });

  test('그 호출은 _DetailContentState.initState() 안에 있다(매물 확인 후 정확히 1회 발화)', () {
    final content = File(_screenFile).readAsStringSync();

    final classIndex = content.indexOf('class _DetailContentState');
    expect(classIndex, greaterThanOrEqualTo(0));

    final initStateIndex = content.indexOf('void initState()', classIndex);
    expect(initStateIndex, greaterThanOrEqualTo(0),
        reason: '_DetailContentState가 initState()를 오버라이드해야 한다');

    // initState() 본문은 짧다(주석 몇 줄 + 호출 1줄) — 다음 멤버 선언(`Future<void>
    // _openChat`) 전까지의 구간에서 호출이 나와야 한다.
    final nextMemberIndex = content.indexOf('Future<void> _openChat', initStateIndex);
    expect(nextMemberIndex, greaterThan(initStateIndex));

    final window = content.substring(initStateIndex, nextMemberIndex);
    expect(window, contains(_repoMethodCall),
        reason: 'incrementListingView(...) 호출이 initState() 본문 안에 있어야 한다');
  });
}
