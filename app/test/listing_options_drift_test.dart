// options.dart(app) ↔ web `web/src/lib/options.ts` 옵션 통제어휘·우선순위 드리프트 가드.
//
// `app/lib/features/listings/options.dart`는 web `web/src/lib/options.ts`의 통제어휘·우선순위
// 티어를 손으로 옮겨 적은 사본이다(정본은 docs/conventions.md §11). 지금은 둘이 같지만, 아무것도
// 그 상태를 지키지 않으면 한쪽만 바뀐 채 계속 green이다. 이 파일의 목적은 "지금 값이 맞다"가
// 아니라 **"앞으로 한쪽만 바뀌면 여기서 잡힌다"**는 실행되는 검사를 두는 것이다(CLAUDE.md B9).
//
// app_theme_color_drift_test.dart·home_chips_contract_test.dart와 같은 방식을 그대로 따른다 —
// web 소스를 상대경로(`flutter test`의 cwd = `app/`)로 직접 읽어 정본과 대조하고, 읽기 실패는
// 폴백 없이 테스트 자체를 실패시킨다(조용한 대체는 이 검사가 막으려는 실패 모드를 재도입한다).
//
// ⚠️ 코드리뷰 지적(P8) — 이 파일이 **안 보는 것**(추측이 아니라 의도적 범위 제한, CLAUDE.md B4):
//   · `optionPriority`/`topOptions` 함수 **본문**은 비교하지 않는다 — 양쪽 다 자기 쪽 단위
//     테스트(`listing_options_test.dart` 계열·web `options.test.ts`)로만 검증되고, 이 드리프트
//     가드는 세 상수 집합(통제어휘·COMMON·HIGH_PRIORITY)과 카드 옵션 개수(`cardOptionCount`)
//     같은 "값"만 대조한다. 정렬 로직 자체가 양쪽에서 다르게 바뀌어도 이 파일은 못 잡는다.
//   · 오버플로 라벨("외 N개")의 정확한 문구·"몇 개를 넘었는가"의 기준(중복 제거 전/후 등)이
//     app·web 사이에서 어긋날 수 있는 지점은 이미 대장에 DW-762로 남아 있다 — 이 가드는 그
//     간극을 고치지 않고 그대로 기록만 해 둔다.
import 'dart:io';

import 'package:app/features/listings/options.dart';
import 'package:flutter_test/flutter_test.dart';

/// `marker`(`export const XXX`) 뒤, **`=` 다음**의 첫 `[`부터 그 배열 자신이 끝나는 `]`까지의
/// 문자열 리터럴을 전부 뽑는다. `=` 다음으로 한정하는 이유 — `HIGH_PRIORITY_OPTIONS: readonly
/// string[] = [...]`처럼 타입 표기 자체에 `[]`가 들어 있어, `=` 앞에서 찾으면 그 타입 표기의
/// `[`에 먼저 걸린다(실측: 이 가드 없이 첫 버전을 돌렸더니 배열을 못 찾은 것으로 나왔다).
/// web `COMMON_OPTIONS`·`HIGH_PRIORITY_OPTIONS`는 둘 다 중첩 배열이 없는 평평한 문자열 배열이라
/// `=` 다음 첫 `]`가 항상 그 배열 자신의 닫는 괄호다.
List<String>? _readFlatStringArray(String content, String marker) {
  final markerStart = content.indexOf(marker);
  if (markerStart < 0) return null;
  final eqIndex = content.indexOf('=', markerStart);
  if (eqIndex < 0) return null;
  final arrayStart = content.indexOf('[', eqIndex);
  if (arrayStart < 0) return null;
  final arrayEnd = content.indexOf(']', arrayStart);
  if (arrayEnd < 0) return null;
  final body = content.substring(arrayStart, arrayEnd);
  final names = RegExp(r"'([^']*)'").allMatches(body).map((m) => m.group(1)!).toList();
  return names.isEmpty ? null : names;
}

/// `CONTROLLED_OPTIONS`는 카테고리별(`Record<OptionCategory, string[]>`)로 나뉘어 있어 위
/// `_readFlatStringArray`로는 한 카테고리만(첫 `]`에서 멈춤) 잡힌다. 카테고리 블록마다
/// (`안전: [...]` 또는 `'편의/멀티미디어': [...]`) 개별로 잘라 문자열을 전부 합친다.
/// ⚠️ 키 매칭에 `\w+`를 쓰지 않는다 — Dart `RegExp`의 `\w`는 ASCII만 포함해 "안전"·"시트" 같은
/// 한글 카테고리 키를 통째로 놓친다(실측: 이 가드 없이 첫 버전을 돌렸더니 "안전" 카테고리 11개가
/// 결과에서 통째로 빠졌다). 대신 콜론·줄바꿈이 아닌 아무 문자로 키를 매칭한다.
Set<String>? _readWebControlledOptions(String content) {
  final start = content.indexOf('export const CONTROLLED_OPTIONS');
  if (start < 0) return null;
  final end = content.indexOf('\n};', start);
  if (end < 0) return null;
  final block = content.substring(start, end);

  final categoryBlockPattern = RegExp(r'[^:\n]+:\s*\[([\s\S]*?)\]');
  final matches = categoryBlockPattern.allMatches(block).toList();
  if (matches.isEmpty) return null;

  final names = <String>{};
  for (final catMatch in matches) {
    final arrayBody = catMatch.group(1)!;
    names.addAll(RegExp(r"'([^']*)'").allMatches(arrayBody).map((m) => m.group(1)!));
  }
  return names;
}

/// `marker`(`const XXX`) 뒤 `=`부터 세미콜론까지의 정수 리터럴 하나를 뽑는다(위
/// `_readFlatStringArray`와 같은 "`=` 다음만 본다" 원칙 — 타입 표기에 숫자가 섞일 걱정은
/// 없지만 마커 재사용 시 같은 위치 규칙을 유지한다). 정수가 아니거나 못 찾으면 null —
/// 폴백 없이 테스트를 실패시킨다(파일 헤더 주석과 동일 원칙).
int? _readIntConst(String content, String marker) {
  final markerStart = content.indexOf(marker);
  if (markerStart < 0) return null;
  final eqIndex = content.indexOf('=', markerStart);
  if (eqIndex < 0) return null;
  final semiIndex = content.indexOf(';', eqIndex);
  if (semiIndex < 0) return null;
  final body = content.substring(eqIndex + 1, semiIndex).trim();
  return int.tryParse(body);
}

void main() {
  final file = File('../web/src/lib/options.ts');
  final content = file.existsSync() ? file.readAsStringSync() : null;

  // ⚠️ 읽기 실패를 폴백 사본으로 조용히 대신하지 않는다 — app_theme_color_drift_test.dart와 같은
  // 이유(정본을 못 읽으면 낡은 사본으로 계속 통과하는 상태를 막는 것이 이 검사의 존재 이유).
  if (content == null) {
    test(
        'web/src/lib/options.ts를 읽지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 되지 '
        '않는다', () {
      fail(
        '../web/src/lib/options.ts를 상대경로로 읽지 못했다(파일 없음). flutter test의 cwd가 '
        'app/가 아니거나 파일이 옮겨졌을 수 있다. 이런 읽기 실패를 낡은 값으로 대신 통과시키지 '
        '않는다.',
      );
    });
    return;
  }

  final webControlled = _readWebControlledOptions(content);
  final webCommon = _readFlatStringArray(content, 'export const COMMON_OPTIONS');
  final webHighPriority = _readFlatStringArray(content, 'export const HIGH_PRIORITY_OPTIONS');

  if (webControlled == null) {
    test(
        'web CONTROLLED_OPTIONS 블록을 파싱하지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 '
        '되지 않는다', () {
      fail('options.ts의 CONTROLLED_OPTIONS 구조가 바뀌어 카테고리 블록을 못 찾았다.');
    });
  } else {
    test('allControlledOptions — web CONTROLLED_OPTIONS(전 카테고리 합)와 집합 일치', () {
      expect(
        allControlledOptions,
        webControlled,
        reason: 'app options.dart의 allControlledOptions가 web CONTROLLED_OPTIONS(카테고리 합)와 '
            '어긋났다 — 옵션을 추가/삭제했다면 두 파일을 같이 고쳐야 한다.',
      );
    });
  }

  if (webCommon == null) {
    test(
        'web COMMON_OPTIONS 블록을 파싱하지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 되지 '
        '않는다', () {
      fail('options.ts의 COMMON_OPTIONS 구조가 바뀌어 배열을 못 찾았다.');
    });
  } else {
    test('commonOptions — web COMMON_OPTIONS와 집합 일치', () {
      expect(
        commonOptions,
        webCommon.toSet(),
        reason: 'app options.dart의 commonOptions가 web COMMON_OPTIONS와 어긋났다.',
      );
    });
  }

  if (webHighPriority == null) {
    test(
        'web HIGH_PRIORITY_OPTIONS 블록을 파싱하지 못했다 — 드리프트 검사가 폴백으로 조용히 '
        'green이 되지 않는다', () {
      fail('options.ts의 HIGH_PRIORITY_OPTIONS 구조가 바뀌어 배열을 못 찾았다.');
    });
  } else {
    test('highPriorityOptions — web HIGH_PRIORITY_OPTIONS와 집합 일치(카드 티어 판정은 순서 무관)',
        () {
      expect(
        highPriorityOptions.toSet(),
        webHighPriority.toSet(),
        reason: 'app options.dart의 highPriorityOptions가 web HIGH_PRIORITY_OPTIONS와 어긋났다 — '
            '티어 판정(optionPriority)은 집합 소속만 보므로 순서는 비교하지 않는다.',
      );
    });
  }

  // 코드리뷰 지적(P8) — `cardOptionCount`(카드 옵션 칩 최대 개수)는 docs/conventions.md
  // §11.2가 4→3으로 한 번 이미 바꾼 값(사용자 결정 2026-07-29)이라 다시 어긋날 수 있는데,
  // 위 세 상수 집합 비교는 이 값을 전혀 보지 않았다. web
  // `web/src/components/listings/ListingCard.tsx`의 `CARD_OPTION_COUNT`와 직접 대조한다.
  final cardFile = File('../web/src/components/listings/ListingCard.tsx');
  final cardContent = cardFile.existsSync() ? cardFile.readAsStringSync() : null;

  if (cardContent == null) {
    test(
        'web ListingCard.tsx를 읽지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 되지 않는다',
        () {
      fail(
        '../web/src/components/listings/ListingCard.tsx를 상대경로로 읽지 못했다(파일 없음). '
        'flutter test의 cwd가 app/가 아니거나 파일이 옮겨졌을 수 있다.',
      );
    });
  } else {
    final webCardOptionCount = _readIntConst(cardContent, 'CARD_OPTION_COUNT');
    if (webCardOptionCount == null) {
      test(
          'web CARD_OPTION_COUNT를 파싱하지 못했다 — 드리프트 검사가 폴백으로 조용히 green이 '
          '되지 않는다', () {
        fail('ListingCard.tsx의 CARD_OPTION_COUNT 선언 형태가 바뀌어 정수를 못 찾았다.');
      });
    } else {
      test('cardOptionCount — web CARD_OPTION_COUNT와 값 일치', () {
        expect(
          cardOptionCount,
          webCardOptionCount,
          reason: 'app options.dart의 cardOptionCount가 web ListingCard.tsx의 '
              'CARD_OPTION_COUNT와 어긋났다 — 카드 옵션 칩 개수를 바꾸려면 두 파일을 같이 '
              '고쳐야 한다(docs/conventions.md §11.2도 함께).',
        );
      });
    }
  }
}
