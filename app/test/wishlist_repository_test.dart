// 찜(wishlist) 판정 단위테스트(Story 16.3) — `isWishlistBlocked` 순수 predicate만 다룬다
// (web isWishedListingBlocked 미러). 실제 Supabase 조회(toggle·fetchWishlist 등)는 이
// 리포의 표준(다른 레포지토리 테스트들과 동일 — listings_repository는 순수 처리부만 단위테스트,
// 실 조회는 수동 실측/E2E)에 따라 여기서 다루지 않는다.
import 'package:app/features/wishlist/wishlist_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show PostgrestException;

void main() {
  group('isWishlistBlocked — on_sale/sold/null 3상태', () {
    test('embed 있음 + status=on_sale → 차단 아님(false, 정상 카드)', () {
      expect(isWishlistBlocked(const {'status': 'on_sale'}, 'on_sale'), isFalse);
    });

    test('embed 있음 + status=sold(본인 소유) → 차단(true, 회색 타일)', () {
      expect(isWishlistBlocked(const {'status': 'sold'}, 'sold'), isTrue);
    });

    test('embed=null(RLS 차단, 타인 소유 sold) → 차단(true)', () {
      expect(isWishlistBlocked(null, null), isTrue);
    });

    test('allowlist 판정: status가 on_sale이 아닌 제3의 값(select 드리프트 등)도 차단', () {
      // FR11 "기본 차단" 정신 — denylist("sold일 때만 차단")이 아니라 on_sale이 명시적으로
      // 확인될 때만 통과시킨다(web 코드리뷰 2026-07-22 P4와 동일 근거).
      expect(isWishlistBlocked(const {'status': 'unknown_status'}, 'unknown_status'), isTrue);
      expect(isWishlistBlocked(const {'status': null}, null), isTrue);
    });
  });

  group('WishlistEntry.fromMap', () {
    test('listing_id가 없으면 null(계약 위반 행 제외)', () {
      expect(WishlistEntry.fromMap({'created_at': '2026-08-07T00:00:00Z'}), isNull);
    });

    test('listings 임베드가 null이어도(RLS 차단) 엔트리 자체는 만들어진다', () {
      final entry = WishlistEntry.fromMap({
        'listing_id': 'l1',
        'created_at': '2026-08-07T00:00:00Z',
        'listings': null,
      });
      expect(entry, isNotNull);
      expect(entry!.listingId, 'l1');
      expect(entry.embed, isNull);
    });

    test('listings 임베드가 있으면 Map으로 파싱된다', () {
      final entry = WishlistEntry.fromMap({
        'listing_id': 'l1',
        'created_at': '2026-08-07T00:00:00Z',
        'listings': {'status': 'on_sale', 'manufacturer': '현대'},
      });
      expect(entry!.embed!['manufacturer'], '현대');
    });
  });

  group('isIgnorableWishInsertError — 유니크 위반만 무시한다(코드리뷰 지적 P12)', () {
    // toggle()은 모든 테스트에서 가짜(fake)로 갈아 끼워지므로(wish_button_test.dart 등) 이
    // 무시 분기 자체는 어떤 테스트로도 실행되지 않았다(코드리뷰 실측) — isWishlistBlocked와
    // 같은 추출 원칙으로 판정만 떼어 직접 단언한다.
    test('23505(유니크 위반) → true(무시)', () {
      expect(
        isIgnorableWishInsertError(
          const PostgrestException(message: 'duplicate key value', code: '23505'),
        ),
        isTrue,
      );
    });

    test('다른 코드 → false(rethrow 대상)', () {
      expect(
        isIgnorableWishInsertError(
          const PostgrestException(message: 'permission denied', code: '42501'),
        ),
        isFalse,
      );
    });
  });

  test(
      'wishlistListingColumns — 신뢰속성 3컬럼(accident_status·is_single_owner·is_non_smoker)을 '
      '포함한다(코드리뷰 지적 P10 — listings_repository.dart의 listingDetailColumns와 같은 근거: '
      '이 상수가 private이고 아무 테스트도 안 봐서, 신뢰속성 3컬럼이 빠져도 찜 목록 카드가 '
      '조용히 뱃지를 잃는 것을 스위트가 못 잡았다)', () {
    expect(wishlistListingColumns, contains('accident_status'));
    expect(wishlistListingColumns, contains('is_single_owner'));
    expect(wishlistListingColumns, contains('is_non_smoker'));
  });
}
