// 홈 차종 칩(categoryChips)·히어로 제안 칩(heroSuggestions) 계약 테스트 —
// 후속 코드리뷰(spec-16-8 2차 리뷰 P5) + T1 보강(검증 갭 해소).
//
// ⚠️ 이전 버전의 결함: "웹과 값·순서 바이트 일치"를 주장하면서 실제로는 이 파일 안의 또 다른
// Dart 리터럴(사본)과만 비교했다 — 웹 CategoryChips.tsx·HeroSearch.tsx가 바뀌어도 이 사본을
// 같이 안 고치면 계약이 깨진 채로 계속 green이었다(두 사본이 똑같이 낡으면 아무것도 못 잡는
// 실패 모드, app_theme_color_drift_test.dart가 이미 겪고 고친 것과 같은 패턴). 이 파일은 그
// 파일의 방식(File(...)로 웹 소스를 상대경로로 직접 읽어 정본과 대조, 읽기 실패는 폴백 없이
// 테스트 자체를 실패시킨다)을 그대로 따른다.
//
// ListingOptions 화이트리스트 대조(아래 두 번째 test)는 남긴다 — 이건 "웹과 다르다"가 아니라
// "bodyType/fuel 오타가 pickOption에서 조용히 null로 떨어져 그 칩이 전체 매물을 보여준다"는
// 별개의 실패를 잡는다(둘 다 필요, 하나가 다른 하나를 대신하지 않는다).
import 'dart:io';

import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/listings/listing_filters.dart';
import 'package:flutter_test/flutter_test.dart';

/// web CategoryChips.tsx의 CATEGORY_CHIPS 항목 하나 — 앱의 CategoryChip과 같은 모양으로 맞춘다.
typedef _WebChip = ({String label, String? bodyType, String? fuel});

/// `web/src/components/landing/CategoryChips.tsx`를 상대경로(`flutter test`의 cwd = `app/`)로
/// 읽어 CATEGORY_CHIPS 배열을 파싱한다. 못 읽거나 구조를 못 찾으면 null — 호출부는 이걸 폴백으로
/// 조용히 넘기지 않고 테스트 자체를 실패시킨다(app_theme_color_drift_test.dart와 동일 원칙).
List<_WebChip>? _readWebCategoryChips() {
  final file = File('../web/src/components/landing/CategoryChips.tsx');
  if (!file.existsSync()) return null;

  final content = file.readAsStringSync();
  final start = content.indexOf('const CATEGORY_CHIPS');
  if (start < 0) return null;
  final end = content.indexOf('];', start);
  if (end < 0) return null;
  final block = content.substring(start, end);

  // `{ label: '전체', query: null }` / `{ label: '경차', query: { body_type: '경차' } }` /
  // `{ label: '전기', query: { fuel: '전기' } }` 세 모양을 전부 잡는다.
  final pattern = RegExp(
    r"\{\s*label:\s*'([^']*)',\s*query:\s*"
    r"(?:null|\{\s*body_type:\s*'([^']*)'\s*\}|\{\s*fuel:\s*'([^']*)'\s*\})\s*\}",
  );
  final matches = pattern.allMatches(block).toList();
  if (matches.isEmpty) return null;

  return [
    for (final m in matches)
      (label: m.group(1)!, bodyType: m.group(2), fuel: m.group(3)),
  ];
}

/// `web/src/components/landing/HeroSearch.tsx`를 상대경로로 읽어 SUGGESTIONS 배열(문자열 4개,
/// 순서 유지)을 파싱한다. 못 읽거나 구조를 못 찾으면 null — 위와 같은 이유로 폴백 없이 실패시킨다.
List<String>? _readWebHeroSuggestions() {
  final file = File('../web/src/components/landing/HeroSearch.tsx');
  if (!file.existsSync()) return null;

  final content = file.readAsStringSync();
  final start = content.indexOf('const SUGGESTIONS');
  if (start < 0) return null;
  final end = content.indexOf('] as const', start);
  if (end < 0) return null;
  final block = content.substring(start, end);

  final matches =
      RegExp(r"'([^']*)'").allMatches(block).map((m) => m.group(1)!).toList();
  return matches.isEmpty ? null : matches;
}

void main() {
  final webChips = _readWebCategoryChips();
  final webSuggestions = _readWebHeroSuggestions();

  // ⚠️ 읽기 실패를 폴백 사본으로 조용히 대신하지 않는다 — app_theme_color_drift_test.dart와
  // 같은 이유(정본을 못 읽으면 낡은 사본으로 계속 통과하는 상태를 막는 것이 이 검사의 존재
  // 이유). 대신 눈에 띄게 실패시켜 읽기 경로가 깨졌다는 사실 자체를 신호로 낸다.
  if (webChips == null) {
    test(
        'web/src/components/landing/CategoryChips.tsx를 읽지 못했다 — 미러 계약 검사가 '
        '폴백으로 조용히 green이 되지 않는다', () {
      fail(
        '../web/src/components/landing/CategoryChips.tsx를 상대경로로 읽지 못했거나 '
        'CATEGORY_CHIPS 배열 구조를 못 찾았다. flutter test의 cwd가 app/가 아니거나 '
        'web 파일 구조가 바뀌었을 수 있다.',
      );
    });
  } else {
    test('categoryChips — web CategoryChips.tsx의 CATEGORY_CHIPS와 개수·순서·라벨 바이트 일치', () {
      expect(
        categoryChips.length,
        webChips.length,
        reason: 'web CATEGORY_CHIPS는 ${webChips.length}개인데 앱 categoryChips는 '
            '${categoryChips.length}개다 — 항목 추가/삭제가 한쪽에만 반영됐다',
      );
      expect(
        categoryChips.map((c) => c.label).toList(),
        webChips.map((c) => c.label).toList(),
        reason: '순서·라벨이 web CategoryChips.tsx의 CATEGORY_CHIPS와 바이트 일치해야 한다',
      );
    });

    test('categoryChips — web CategoryChips.tsx의 bodyType/fuel 필터값이 항목별로 바이트 일치', () {
      for (var i = 0; i < categoryChips.length && i < webChips.length; i++) {
        final app = categoryChips[i];
        final web = webChips[i];
        expect(
          app.bodyType,
          web.bodyType,
          reason: '"${app.label}" 칩의 bodyType이 web과 다르다(app=${app.bodyType}, '
              'web=${web.bodyType}) — 값이 갈리면 같은 라벨이 다른 결과를 보여준다',
        );
        expect(
          app.fuel,
          web.fuel,
          reason: '"${app.label}" 칩의 fuel이 web과 다르다(app=${app.fuel}, web=${web.fuel})',
        );
      }
    });
  }

  if (webSuggestions == null) {
    test(
        'web/src/components/landing/HeroSearch.tsx를 읽지 못했다 — 미러 계약 검사가 '
        '폴백으로 조용히 green이 되지 않는다', () {
      fail(
        '../web/src/components/landing/HeroSearch.tsx를 상대경로로 읽지 못했거나 SUGGESTIONS '
        '배열 구조를 못 찾았다. flutter test의 cwd가 app/가 아니거나 web 파일 구조가 '
        '바뀌었을 수 있다.',
      );
    });
  } else {
    test('heroSuggestions — web HeroSearch.tsx의 SUGGESTIONS와 값·순서 바이트 일치', () {
      expect(heroSuggestions, webSuggestions);
    });
  }

  // categoryChips 전체를 화이트리스트(ListingOptions)에 대조 — 위 web 대조와는 다른 실패를
  // 잡는다: bodyType/fuel이 web과는 같아도 애초에 DB CHECK/드롭다운 화이트리스트 밖이면
  // pickOption이 조용히 null로 떨어뜨려 "전체 매물"을 보여준다(라벨-결과 불일치).
  test('categoryChips — 6개, 화이트리스트(ListingOptions) 소속, "전체"는 무필터', () {
    expect(categoryChips.length, 6);

    for (final chip in categoryChips) {
      if (chip.bodyType != null) {
        expect(
          ListingOptions.bodyType,
          contains(chip.bodyType),
          reason: '"${chip.label}" 칩의 bodyType("${chip.bodyType}")이 ListingOptions.bodyType '
              '화이트리스트 밖이면, pickOption이 이 값을 조용히 null로 떨어뜨려 "전체 매물"을 '
              '보여주는 라벨-결과 불일치가 생긴다',
        );
      }
      if (chip.fuel != null) {
        expect(
          ListingOptions.fuel,
          contains(chip.fuel),
          reason: '"${chip.label}" 칩의 fuel("${chip.fuel}")이 ListingOptions.fuel 화이트리스트 '
              '밖이면 같은 이유로 라벨-결과가 어긋난다',
        );
      }
    }

    final all = categoryChips.firstWhere((c) => c.label == '전체');
    expect(all.bodyType, isNull, reason: '"전체"는 무필터여야 한다(bodyType null)');
    expect(all.fuel, isNull, reason: '"전체"는 무필터여야 한다(fuel null)');
  });
}
