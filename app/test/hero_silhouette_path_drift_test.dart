// DW-772 해소 — 앱(`home_screen.dart` `_CarSilhouettePainter`) ↔ 웹
// (`web/src/components/landing/HeroSearch.tsx` 인라인 `<svg>`) 차 실루엣 도형 대조.
//
// **왜 이 파일이 생겼나(코드리뷰 3패스, 실측):** spec-16-10이 같은 목업 도형을 두 표면에
// **손으로 옮겨 적은 사본 두 벌**로 만들었는데, 앱 사본에는 좌표를 고정하는 검사가 하나도
// 없었다. `home_ai_entry_test.dart`의 `paints..path(includes/excludes)`는 점 5개만 샘플링해서
// 지붕선을 17px 옮겨도(`cubicTo(188,54,224,45,276,45)` → `(188,54,224,62,276,62)`) 전 스위트가
// green이었다. 웹 사본은 `d` 문자열 전문을 고정하지만 자기 상수와만 비교하므로, 두 사본은
// 서로 모르게 갈라질 수 있었다. 스펙 Always가 요구한 건 "**동일 path 데이터**"이므로,
// 그 동일성 자체를 실행되는 검사로 만든다(CLAUDE.md B9 — 주석은 계약이 아니다).
//
// **방식은 리포의 기존 앱↔웹 드리프트 가드와 같다**(`app_theme_color_drift_test.dart`가 웹
// `globals.css`를 상대경로로 직접 읽어 대조한다). 사본을 하나 더 만들지 않고 두 **정본 소스**를
// 읽어 서로 대조한다 — 이 파일이 세 번째 사본이 되면 막으려는 실패를 스스로 재현한다.
// 읽기·파싱 실패는 폴백 없이 테스트를 명시적으로 실패시킨다(같은 이유).
//
// **이 검사가 보지 않는 것**(추측이 아니라 기법상 한계): 목업 `consistency-1.html` 원본과의
// 대조는 하지 않는다 — 두 구현이 **함께** 목업에서 벗어나면 여기선 안 잡힌다. 목업 대조는
// 육안·스크린샷 몫이다. 또 배치(위치·크기·투명도)는 여기 대상이 아니다(앱은
// `carSilhouetteOffset` 단위테스트와 `paints` 단언이, 웹은 `HeroSearch.test.ts`가 각자 본다) —
// 목업이 표면별로 다른 배치 규칙을 주기 때문에 배치는 애초에 같을 필요가 없고, **도형만**
// 같아야 한다.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 도형 하나를 표기와 무관하게 비교할 수 있는 형태로 적은 것.
/// 명령 문자 + 숫자들을 한 줄 문자열로 만든다(예: `C 30 120 74 112 122 110`).
/// SVG의 아크는 파라미터가 7개(rx ry rot large sweep x y), Flutter의 `arcToPoint`는 4개
/// (x y radius clockwise)라 표기가 다르다 — 아래에서 양쪽을 같은 정규형
/// `A <r> <x> <y> <sweep>`으로 접는다(sweep 1 = SVG sweep-flag 1 = Flutter clockwise: true).
typedef Shape = List<String>;

String _n(num v) => v.toString();

/// `web/src/components/landing/HeroSearch.tsx`의 인라인 svg에서 `d` 속성과 `<circle>` 2개를
/// 읽어 정규형으로 만든다. 못 읽거나 구조를 못 찾으면 null(호출부가 테스트를 실패시킨다).
({Shape path, Shape circles})? _readWebShape() {
  final file = File('../web/src/components/landing/HeroSearch.tsx');
  if (!file.existsSync()) return null;
  final whole = file.readAsStringSync();

  // ⚠️ 파일 전체에서 찾으면 안 된다 — 같은 파일의 검색 버튼 아이콘 svg에도 `<circle>`이 있어
  // 바퀴가 3개로 읽힌다(이 검사를 처음 돌렸을 때 실제로 그렇게 실패했다). 실루엣 svg 블록
  // (`viewBox="0 0 640 220"`을 가진 것)만 잘라내 그 안에서만 찾는다.
  final viewBoxAt = whole.indexOf('viewBox="0 0 640 220"');
  if (viewBoxAt < 0) return null;
  final svgStart = whole.lastIndexOf('<svg', viewBoxAt);
  final svgEnd = whole.indexOf('</svg>', viewBoxAt);
  if (svgStart < 0 || svgEnd < 0) return null;
  final content = whole.substring(svgStart, svgEnd);

  final dMatch = RegExp(r'<path\s+d="([^"]+)"').firstMatch(content);
  if (dMatch == null) return null;

  // `M6,150 C30,120 74,112 122,110 …` → 명령 문자와 숫자로 토큰화.
  final tokens = RegExp(r'([MCLAZ])|(-?\d+(?:\.\d+)?)')
      .allMatches(dMatch.group(1)!)
      .map((m) => m.group(0)!)
      .toList();

  const argCount = {'M': 2, 'C': 6, 'L': 2, 'A': 7, 'Z': 0};
  final path = <String>[];
  var i = 0;
  while (i < tokens.length) {
    final cmd = tokens[i];
    final count = argCount[cmd];
    if (count == null) return null; // 상대좌표(소문자)·미지원 명령이 들어오면 조용히 넘기지 않는다
    final args = tokens.sublist(i + 1, i + 1 + count).map(num.parse).toList();
    if (args.length != count) return null;
    i += 1 + count;

    if (cmd == 'A') {
      final [rx, ry, rot, large, sweep, x, y] = args;
      // 정규형이 rx 하나만 담으므로, 타원·회전·large-arc가 들어오면 정보가 조용히 버려진다.
      // 그런 값이 나타나면 대조를 하지 말고 실패시킨다.
      if (rx != ry || rot != 0 || large != 0) return null;
      path.add('A ${_n(rx)} ${_n(x)} ${_n(y)} ${_n(sweep)}');
    } else {
      path.add(([cmd] + args.map(_n).toList()).join(' '));
    }
  }

  final circles = RegExp(r'<circle\s+cx="([\d.]+)"\s+cy="([\d.]+)"\s+r="([\d.]+)"')
      .allMatches(content)
      .map((m) => 'circle ${m.group(1)} ${m.group(2)} ${m.group(3)}')
      .toList();
  if (circles.isEmpty) return null;

  return (path: path, circles: circles);
}

/// `lib/features/auth/home_screen.dart`의 `_carPath()` 본문과 `paint()`의 `drawCircle` 호출을
/// 읽어 같은 정규형으로 만든다(`flutter test`의 cwd = `app/`).
({Shape path, Shape circles})? _readAppShape() {
  final file = File('lib/features/auth/home_screen.dart');
  if (!file.existsSync()) return null;
  final whole = file.readAsStringSync();

  // 웹 쪽과 같은 이유로 범위를 좁힌다 — `drawCircle`이 다른 위젯에 생기면 바퀴로 오인된다.
  final classStart = whole.indexOf('class _CarSilhouettePainter');
  if (classStart < 0) return null;
  final content = whole.substring(classStart);

  final bodyStart = content.indexOf('Path _carPath() => Path()');
  if (bodyStart < 0) return null;
  final bodyEnd = content.indexOf('..close();', bodyStart);
  if (bodyEnd < 0) return null;
  final body = content.substring(bodyStart, bodyEnd);

  const svgCmdByDart = {'moveTo': 'M', 'cubicTo': 'C', 'lineTo': 'L'};
  final path = <String>[];
  // `..moveTo(6, 150)` / `..cubicTo(...)` / `..lineTo(...)` /
  // `..arcToPoint(const Offset(482, 192), radius: const Radius.circular(42), clockwise: false)`
  final callPattern = RegExp(r'\.\.(\w+)\(([^;]*?)\)\s*(?=\.\.|$)', dotAll: true);
  for (final m in callPattern.allMatches(body)) {
    final name = m.group(1)!;
    final args = m.group(2)!;
    final nums = RegExp(r'-?\d+(?:\.\d+)?')
        .allMatches(args)
        .map((x) => num.parse(x.group(0)!))
        .toList();

    if (svgCmdByDart.containsKey(name)) {
      path.add(([svgCmdByDart[name]!] + nums.map(_n).toList()).join(' '));
    } else if (name == 'arcToPoint') {
      // Offset(x, y) … Radius.circular(r) 순서로 숫자가 나온다.
      if (nums.length != 3) return null;
      final clockwise = RegExp(r'clockwise:\s*(true|false)').firstMatch(args)?.group(1);
      if (clockwise == null) return null; // SDK 기본값(true)에 기대지 않는다 — 명시가 계약이다
      path.add('A ${_n(nums[2])} ${_n(nums[0])} ${_n(nums[1])} ${clockwise == 'true' ? '1' : '0'}');
    } else {
      return null; // 새 명령이 추가되면 조용히 무시하지 않고 실패시킨다
    }
  }
  if (path.isEmpty) return null;
  path.add('Z'); // `..close()`

  final circles = RegExp(
          r'drawCircle\(const Offset\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\),\s*(\d+(?:\.\d+)?)')
      .allMatches(content)
      .map((m) => 'circle ${m.group(1)} ${m.group(2)} ${m.group(3)}')
      .toList();
  if (circles.isEmpty) return null;

  return (path: path, circles: circles);
}

void main() {
  final web = _readWebShape();
  final app = _readAppShape();

  // 읽기·파싱 실패를 조용한 폴백으로 대신하지 않는다 — 그러면 이 검사가 막으려는 상태
  // ("사본이 갈라졌는데 아무도 모른다")를 그대로 만든다.
  if (web == null || app == null) {
    test('실루엣 도형 정본 두 개를 읽지 못했다 — 드리프트 검사가 조용히 green이 되지 않는다', () {
      fail(
        'web=${web == null ? "읽기/파싱 실패" : "ok"}, app=${app == null ? "읽기/파싱 실패" : "ok"}. '
        '../web/src/components/landing/HeroSearch.tsx의 <path d="…">·<circle>, 또는 '
        'lib/features/auth/home_screen.dart의 _carPath()·drawCircle 구조를 찾지 못했다 '
        '(flutter test의 cwd가 app/가 아니거나, 지원하지 않는 path 명령·상대좌표·타원 아크가 '
        '들어왔을 수 있다). 낡은 값으로 통과시키지 않는다.',
      );
    });
    return;
  }

  group('차 실루엣 도형 앱↔웹 대조 (DW-772)', () {
    test('path 명령·좌표가 두 표면에서 완전히 같다', () {
      expect(app.path, web.path,
          reason: '앱 `_carPath()`와 웹 <path d="…">가 갈라졌다 — 스펙 Always가 요구한 것은 '
              '"동일 path 데이터"다. 한쪽을 고쳤다면 다른 쪽도 같이 고쳐야 한다.');
    });

    test('바퀴 원 2개가 두 표면에서 완전히 같다', () {
      expect(app.circles, web.circles,
          reason: '바퀴 좌표·반지름이 갈라졌다(앱 drawCircle ↔ 웹 <circle>)');
      expect(app.circles.length, 2, reason: '목업은 바퀴가 2개다 — 개수 자체가 계약이다');
    });

    // 위 두 검사가 "둘 다 비었다"로 공허하게 통과하지 않는지. 파싱이 조용히 0개를 돌려주면
    // 리스트끼리는 같아서(둘 다 빈 리스트) green이 된다.
    test('파싱이 실제로 도형을 뽑았다(공허한 통과 방지)', () {
      expect(app.path.length, greaterThan(10));
      expect(web.path.length, app.path.length);
      expect(app.path.first, 'M 6 150');
      expect(app.path.last, 'Z');
    });
  });
}
