// DW-729 해소 — `AppColors`(app) ↔ web `globals.css` 라이트 팔레트 hex 대조.
// 목적은 "지금 값이 맞다"가 아니라 "앞으로 한쪽만 바뀌면 여기서 잡힌다"는 실행되는 검사를 두는
// 것이다(CLAUDE.md B9 — conventions.md에 색 절을 새로 만드는 사본 방식은 채택하지 않는다,
// spec-16-2 Design Notes 참조: 요약 사본이 원본보다 늙는 실패를 이 프로젝트가 이미 겪었다).
//
// web을 상대경로로 읽을 수 있으면(이 리포 레이아웃에서 `app/`이 cwd일 때 `../web/...`) 그 파일을
// 정본으로 직접 대조한다 — 사본을 하나 더 만들지 않는 것이 B9의 핵심이다. 읽기 실패는 폴백 없이
// 테스트를 명시적으로 실패시킨다(아래 `main()` 참조 — 조용한 대체가 이 검사가 막으려는 실패
// 모드를 재도입하기 때문).
import 'dart:io';

import 'package:app/core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// AppColors 필드명 → web CSS 변수명(대시 표기). web `--color-amber-ink`는 `--ink-primary`와
// 같은 값이라 앱에 별도 토큰이 없어 대조 대상에서 뺀다. AppColors의 `onPetrol`·`onPetrolMuted`는
// petrol 배경 위 잉크를 위한 앱 전용 토큰(web은 opacity로 표현)이라 web 대응 변수가 없어 역시
// 뺀다 — DW-729 evidence가 말한 "17종"이 아래 17개다.
const Map<String, String> _cssVarByAppColorName = {
  'surfaceBase': 'surface-base',
  'surfaceRaised': 'surface-raised',
  'inkPrimary': 'ink-primary',
  'inkSecondary': 'ink-secondary',
  'inkMuted': 'ink-muted',
  'borderHairline': 'border-hairline',
  'brandPetrol': 'brand-petrol',
  'brandPetrolStrong': 'brand-petrol-strong',
  'petrolDeepest': 'petrol-deepest',
  'accentAmber': 'color-accent-amber', // @theme static 블록(라이트/다크 공용, 스왑 안 됨)
  'priceEmphasis': 'price-emphasis',
  'trustGreenBg': 'trust-green-bg',
  'trustGreenInk': 'trust-green-ink',
  'placeholderBg': 'placeholder-bg',
  'warnAmberBg': 'warn-amber-bg',
  'warnAmberInk': 'warn-amber-ink',
  'danger': 'danger',
};

Map<String, Color> _appColorsByName() => {
      'surfaceBase': AppColors.surfaceBase,
      'surfaceRaised': AppColors.surfaceRaised,
      'inkPrimary': AppColors.inkPrimary,
      'inkSecondary': AppColors.inkSecondary,
      'inkMuted': AppColors.inkMuted,
      'borderHairline': AppColors.borderHairline,
      'brandPetrol': AppColors.brandPetrol,
      'brandPetrolStrong': AppColors.brandPetrolStrong,
      'petrolDeepest': AppColors.petrolDeepest,
      'accentAmber': AppColors.accentAmber,
      'priceEmphasis': AppColors.priceEmphasis,
      'trustGreenBg': AppColors.trustGreenBg,
      'trustGreenInk': AppColors.trustGreenInk,
      'placeholderBg': AppColors.placeholderBg,
      'warnAmberBg': AppColors.warnAmberBg,
      'warnAmberInk': AppColors.warnAmberInk,
      'danger': AppColors.danger,
    };

/// `_cssVarByAppColorName`(수기 매핑)에도 없고 web 대응 변수도 없어 의도적으로 대조 대상에서
/// 뺀 앱 전용 토큰(app_theme.dart 28~31행 주석 참조: web은 opacity로 표현하는 값을 앱은 별도
/// 색으로 뒀다). 아래 완전성 테스트가 이 집합을 "빠뜨린 게 아니라 일부러 뺐다"의 근거로 쓴다.
const Set<String> _explicitlyExcludedAppColorNames = {'onPetrol', 'onPetrolMuted'};

/// `AppColors` 안에 `static const`이지만 색이 아니라서(따라서 web 대조 대상이 아니라서) 완전성
/// 검사의 이름 집합에서 빼야 하는 멤버 이름. 지금은 `AppColors` 전원이 `Color`라 빈 집합이다.
/// 값 모양(이니셜라이저가 `Color(...)`인지 `Colors.x`인지 등)으로 걸러내지 않고 **이름을 직접
/// 나열**하는 이유 — 값 모양 매칭은 표기가 하나 늘 때마다 또 뚫린다(review P1: `Color.fromARGB`·
/// 별칭(`= danger;`) 둘 다 이전 정규식을 통과했다). 이름 목록은 표기와 무관하게 항상 유효하다.
/// 목록이 낡으면(이름이 바뀌거나 지워졌는데 여기를 안 고치면) `_readDeclaredAppColorNames`가
/// 조용히 무시하지 않고 즉시 예외를 던진다 — 아래 함수 참조.
const Set<String> _nonColorStaticConstNames = {};

/// `lib/core/theme/app_theme.dart`(`flutter test`의 cwd = `app/`)를 상대경로로 읽어 `AppColors`가
/// 실제로 선언한 `static const` 색 토큰 이름을 뽑는다. 이 파일 안의 손으로 옮겨 적은 사본
/// (`_cssVarByAppColorName`/`_appColorsByName`)이 아니라 **정본 소스**를 기준으로 삼아야 "토큰을
/// 추가했는데 매핑 테이블에 옮기는 걸 잊었다"를 실제로 잡는다 — 두 사본끼리만 대조하면 똑같이
/// 빠뜨렸을 때 아무것도 못 잡는다(이 파일이 고치기 전 버전의 실제 결함).
/// 못 읽거나 구조를 못 찾으면 null — 호출부는 이걸 폴백으로 조용히 넘기지 않고 테스트 자체를
/// 실패시킨다(아래 `_readWebLightPalette`와 같은 원칙).
Set<String>? _readDeclaredAppColorNames() {
  final file = File('lib/core/theme/app_theme.dart');
  if (!file.existsSync()) return null;

  final content = file.readAsStringSync();
  final classStart = content.indexOf('class AppColors {');
  if (classStart < 0) return null;
  final classEnd = content.indexOf('\n}', classStart);
  if (classEnd < 0) return null;
  final classBody = content.substring(classStart, classEnd);

  // 이전 정규식은 `static const <name> = Color(` / `= Colors.`처럼 **이니셜라이저 표기**까지
  // 요구했다. 그래서 표기가 하나만 달라도(타입 명시 `static const Color x = ...`, 또는
  // `Color.fromARGB`·`Color.fromRGBO`·기존 상수 별칭 `= danger;` 등) 그 토큰은 통째로 안 잡혔다
  // (실측: `probeFromArgb`(fromARGB)·`probeAlias`(별칭) 둘 다 이 완전성 검사가 green인 채로
  // 통과했다 — 타입 표기 축은 이전 리뷰가 고쳤지만 이니셜라이저 표기 축은 남아 있었다). 이제는
  // **선언 머리(`static const <name> =`)만** 매칭한다 — 그 뒤에 뭐가 오든(어떤 값 표기든) 이름은
  // 무조건 잡힌다. 대신 색이 아닌 `static const`가 섞여 들어오는 문제는 값 모양이 아니라 위
  // `_nonColorStaticConstNames`(이름 명시 제외 목록)로 막는다.
  final tokenPattern = RegExp(r'static const\s+(?:Color\s+)?(\w+)\s*=');
  final allNames = {for (final m in tokenPattern.allMatches(classBody)) m.group(1)!};

  // 제외 목록의 이름이 실제 선언에 없다면(개명·삭제 후 목록을 안 고친 경우) 조용히 무시하지
  // 않고 바로 터뜨린다 — 존재하지 않는 이름을 "걸러냈다"고 착각한 채 넘어가면 그 자리에
  // 진짜 색이 아닌 토큰이 몰래 섞여도 아무도 모른다.
  for (final excluded in _nonColorStaticConstNames) {
    if (!allNames.contains(excluded)) {
      throw StateError(
        '_nonColorStaticConstNames에 있는 "$excluded"가 AppColors 선언에 없다 — 이름이 '
        '바뀌었거나 지워졌는데 제외 목록을 같이 안 고쳤다(낡은 제외 목록).',
      );
    }
  }

  final names = allNames.difference(_nonColorStaticConstNames);
  return names.isEmpty ? null : names;
}

/// `web/src/app/globals.css`를 상대경로(`flutter test`의 cwd = `app/`)로 읽어 라이트 팔레트
/// hex를 뽑는다. 못 읽거나 구조를 못 찾으면 null — 호출부는 이걸 폴백으로 조용히 넘기지 않고
/// 테스트 자체를 실패시킨다(main() 참조).
Map<String, String>? _readWebLightPalette() {
  final file = File('../web/src/app/globals.css');
  if (!file.existsSync()) return null;

  final content = file.readAsStringSync();
  final rootStart = content.indexOf(':root {');
  final darkStart = content.indexOf('@media (prefers-color-scheme: dark)');
  if (rootStart < 0 || darkStart < 0 || darkStart <= rootStart) return null;
  // `:root { ... }` 자신의 닫는 `}`에서 자른다 — 예전엔 다음 `@media` 줄까지 통째로 잘랐는데,
  // 그러면 `:root` 블록이 끝난 뒤(@media 앞) 파일에 적힌 어떤 `--xxx: #......;`도 라이트
  // 팔레트로 같이 흡수됐다(실측 review P2: `:root` 뒤·`@media` 앞에 `--danger: #000000;`를
  // 담은 주석을 끼워 넣었더니 결과 맵이 그 값으로 덮여 대조가 그 값과 비교됐다 — 결과가 맵
  // 리터럴이라 나중 매치가 조용히 이겼다). `\n}`으로 그 블록 자신의 닫는 중괄호를 찾는다.
  final rootBodyEnd = content.indexOf('\n}', rootStart);
  if (rootBodyEnd < 0 || rootBodyEnd >= darkStart) return null;
  final lightBlock = content.substring(rootStart, rootBodyEnd);

  final varPattern = RegExp(r'--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})');
  final result = <String, String>{
    for (final m in varPattern.allMatches(lightBlock))
      m.group(1)!: m.group(2)!.toUpperCase(),
  };

  // accent-amber는 라이트/다크 공용 `@theme static` 블록 소속이라 :root 밖에 있다. 파일
  // 전체에서 찾으면 그 앞(파일 순서상 `@theme static`보다 먼저 오는) 다크 `@media` 블록 안에
  // 같은 이름의 변수가 있어도 그게 먼저 잡힌다(실측 review P3: 다크 블록 안에
  // `--color-accent-amber: #111111;`을 끼워 넣었더니 라이트 고정 앱 토큰이 그 다크 값과
  // 비교됐다). `@theme static` 블록 시작 지점부터만 찾아 그 앞부분을 아예 안 본다.
  final themeStaticStart = content.indexOf('@theme static');
  if (themeStaticStart < 0) return null;
  final amberMatch = RegExp(r'--color-accent-amber:\s*(#[0-9A-Fa-f]{6})')
      .firstMatch(content.substring(themeStaticStart));
  if (amberMatch == null) return null;
  result['color-accent-amber'] = amberMatch.group(1)!.toUpperCase();

  return result;
}

/// Color → '#RRGGBB'(알파 제외). `.value`는 deprecated라 toARGB32 사용.
/// ⚠️ 알파를 버리고 RGB 6자리만 비교한다 — 이게 안전한 이유는 "AppColors는 전부 불투명"이
/// 실제로 검사되기 때문이다(아래 main()의 "완전 불투명" 테스트 참조, review P4). 그 검사 없이
/// 알파만 버리면 `Color(0x80C0392B)`처럼 알파가 섞인 값으로 바뀌어도 RGB는 그대로라 green이
/// 된다(실측: 리뷰가 실제로 이렇게 바꿔 넣었더니 스위트가 green이었다).
String _hexOf(Color c) {
  final argb = c.toARGB32().toRadixString(16).padLeft(8, '0').toUpperCase();
  return '#${argb.substring(2)}';
}

/// Color의 알파 바이트만 2자리 hex로. `_hexOf`가 알파를 버려도 안전한지 확인하는 용도로만 쓴다.
String _alphaOf(Color c) =>
    c.toARGB32().toRadixString(16).padLeft(8, '0').toUpperCase().substring(0, 2);

void main() {
  final webPalette = _readWebLightPalette();

  // ⚠️ 읽기 실패를 폴백 사본으로 조용히 대신하지 않는다 — 이 검사의 존재 이유가 "정본을 못
  // 읽으면 낡은 사본으로 계속 통과하는 상태를 막는 것"인데, 조용한 대체는 정확히 그 상태를
  // 만든다. 대신 눈에 띄게 실패시켜, 읽기 경로가 깨졌다는 사실 자체를 신호로 낸다.
  if (webPalette == null) {
    test(
        'web/src/app/globals.css를 읽지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 되지 않는다',
        () {
      fail(
        '../web/src/app/globals.css를 상대경로로 읽지 못했거나(파일 없음) 예상한 구조(:root 블록·'
        '@media dark·--color-accent-amber)를 못 찾았다. flutter test의 cwd가 app/가 아니거나 '
        'globals.css 구조가 바뀌었을 수 있다. 이런 읽기 실패를 낡은 값으로 대신 통과시키지 '
        '않는다(DW-729가 막으려는 실패 모드를 재도입하지 않기 위함).',
      );
    });
    return;
  }

  final appColors = _appColorsByName();

  group('AppColors ↔ web 라이트 팔레트 대조 (DW-729)', () {
    for (final entry in _cssVarByAppColorName.entries) {
      test('AppColors.${entry.key} == web --${entry.value}', () {
        final webHex = webPalette[entry.value];
        expect(webHex, isNotNull,
            reason: 'web globals.css에 --${entry.value}가 없다(변수명이 바뀌었을 수 있음)');
        expect(_hexOf(appColors[entry.key]!), webHex,
            reason:
                'AppColors.${entry.key}가 web --${entry.value}와 어긋났다 — 값을 바꾼 쪽이 '
                '다른 쪽도 같이 고쳐야 한다(docs/conventions.md 값 정본은 web DESIGN.md).');
      });
    }

    test('AppColors 선언 전체가 매핑 테이블(+명시적 제외 목록)과 정확히 일치한다', () {
      final declared = _readDeclaredAppColorNames();
      if (declared == null) {
        fail(
          'lib/core/theme/app_theme.dart를 상대경로로 읽지 못했거나 AppColors 클래스 선언을 '
          '찾지 못했다(flutter test의 cwd가 app/가 아니거나 파일 구조가 바뀌었을 수 있다). 이 '
          '완전성 검사는 읽기 실패를 조용히 통과시키지 않는다(위 web 팔레트 읽기와 같은 원칙).',
        );
      }

      final mappedKeys = _cssVarByAppColorName.keys.toSet();
      final expected = mappedKeys.union(_explicitlyExcludedAppColorNames);

      final missingFromMap = declared.difference(expected);
      final unknownExtra = expected.difference(declared);

      expect(
        missingFromMap,
        isEmpty,
        reason: 'AppColors에 선언됐지만 매핑 테이블에도 제외 목록에도 없는 토큰: $missingFromMap '
            '— 새 토큰을 추가했다면 _cssVarByAppColorName(대조 대상)이나 '
            '_explicitlyExcludedAppColorNames(의도적 제외)에 반영해야 한다.',
      );
      expect(
        unknownExtra,
        isEmpty,
        reason: '매핑 테이블 또는 제외 목록엔 있지만 AppColors 선언엔 없는 토큰: $unknownExtra '
            '— 토큰을 지웠다면 매핑 테이블/제외 목록도 같이 지워야 한다.',
      );
    });

    // `_hexOf`가 알파를 버리고 RGB 6자리만 비교해도 안전하려면 대조 대상 전원이 완전
    // 불투명이어야 한다 — 그 전제 자체를 검사로 확인한다(review P4: `Color(0x80C0392B)`처럼
    // 알파를 섞어도 RGB 비교만으로는 안 잡혀서 스위트가 green이었다).
    test('AppColors 대조 대상 전원이 완전 불투명이다(alpha=FF) — RGB만 비교해도 안전한 전제', () {
      for (final entry in appColors.entries) {
        expect(_alphaOf(entry.value), 'FF',
            reason: 'AppColors.${entry.key}의 알파가 FF가 아니다 — _hexOf는 알파를 버리고 '
                'RGB만 비교하므로, 알파가 섞인 값으로 바뀌어도 이 전제가 없으면 그 변경을 '
                '놓친다. 알파가 있는 색을 실제로 추가하려면 _hexOf·비교 로직을 알파 포함으로 '
                '바꿔야 한다.');
      }
    });
  });
}
