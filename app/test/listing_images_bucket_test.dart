// review P5 — listingImagesBucket(app) ↔ migration 0014의 버킷 id 대조.
// listing_images_bucket.dart의 주석("값은 migration 0014와 동기화된 상태를 유지해야 한다")은
// 주석일 뿐 실행되는 검사가 아니다(CLAUDE.md B9). 실측: 값을 'WRONG-bucket-probe'로 바꿔
// 전체 스위트(172건)를 돌려도 green이었다 — 이 상수로 앱의 모든 사진 공개 URL을 만드는데도
// 아무 데서도 안 잡혔다는 뜻이다. app_theme_color_drift_test.dart와 같은 원칙으로 정본
// (마이그레이션 SQL)을 직접 읽어 대조한다 — 손으로 옮겨 적은 사본을 하나 더 만들지 않는다.
import 'dart:io';

import 'package:app/features/listings/listing_images_bucket.dart';
import 'package:flutter_test/flutter_test.dart';

/// `supabase/migrations/0014_listing_images_public_bucket.sql`(`flutter test`의 cwd = `app/`)을
/// 상대경로로 읽어 버킷 id를 뽑는다. 그 파일의 실제 SQL은
/// `insert into storage.buckets (id, name, public, ...) values ('listing-images', 'listing-images', ...)`
/// 형태다 — `values (` 뒤 첫 문자열 리터럴이 버킷 id다. 줄바꿈·주석 위치가 바뀌어도 매칭되게
/// `insert into storage.buckets`부터 `values (` 뒤 첫 리터럴까지를 통째로 찾는다(라인 번호에
/// 기대지 않는다). 못 읽거나 구조를 못 찾으면 null — 호출부는 폴백 없이 테스트 자체를
/// 실패시킨다(app_theme_color_drift_test.dart의 `_readWebLightPalette`와 같은 원칙).
String? _readCanonicalBucketName() {
  final file =
      File('../supabase/migrations/0014_listing_images_public_bucket.sql');
  if (!file.existsSync()) return null;

  final content = file.readAsStringSync();
  final match = RegExp(
    r"insert into storage\.buckets[\s\S]*?values\s*\(\s*'([a-z0-9-]+)'",
  ).firstMatch(content);
  return match?.group(1);
}

void main() {
  final canonical = _readCanonicalBucketName();

  // ⚠️ 읽기 실패를 조용히 통과시키지 않는다 — 정본을 못 읽는 상태를 green으로 덮으면 이
  // 검사가 막으려는 실패 모드(값이 갈라져도 아무도 모른다)를 그대로 재도입한다.
  if (canonical == null) {
    test('migration 0014를 읽지 못했다 — 버킷명 대조가 폴백으로 조용히 green이 되지 않는다', () {
      fail(
        '../supabase/migrations/0014_listing_images_public_bucket.sql을 상대경로로 읽지 '
        '못했거나(파일 없음) `insert into storage.buckets ... values (...)` 구조를 못 찾았다. '
        'flutter test의 cwd가 app/가 아니거나 마이그레이션 파일 구조가 바뀌었을 수 있다.',
      );
    });
    return;
  }

  test('listingImagesBucket이 migration 0014의 버킷 id와 일치한다', () {
    expect(
      listingImagesBucket,
      canonical,
      reason:
          'listing_images_bucket.dart의 listingImagesBucket이 migration 0014에서 실제로 '
          '만든 버킷 id($canonical)와 어긋났다 — 이 값으로 앱의 모든 사진 공개 URL을 만들기 '
          '때문에, 어긋나면 사진이 전부 깨진다.',
    );
  });
}
