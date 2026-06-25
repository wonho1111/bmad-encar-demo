// 본인 매물 관리 컨트롤러(7.4, FR6·8 재현) — Riverpod 3 Notifier.
//
// 책임:
//   · 본인 매물 목록 로드(seller_id 필터 + RLS) → AsyncValue 로 화면에 흘린다.
//   · 삭제(delete) / 구매완료(markSold) 액션 → 성공이면 목록 새로고침, 0행이면 한국어 거부.
// 수정(edit)은 7.3 SellController(edit 모드)가 담당하므로 여기엔 없다.
//
// 0행 패턴(중요): Supabase 는 RLS 로 막힌 UPDATE/DELETE 를 예외가 아니라 "영향 행 0개"로 돌려준다.
//   → repo.deleteListing/markSold 가 돌려준 affected==0 이면 거부 메시지로 분기한다(예외 catch 만으론 못 잡음).
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/supabase/supabase_client.dart';
import 'listing.dart';
import 'listing_errors.dart';
import 'listings_providers.dart';

/// 본인 매물 관리 화면 상태 = (목록 AsyncValue) + (액션 진행 중 id) + (액션 거부/오류 메시지).
class MyListingsState {
  const MyListingsState({
    this.listings = const AsyncValue.loading(),
    this.busyId,
    this.actionError,
  });

  final AsyncValue<List<OwnListing>> listings;
  final String? busyId; // 삭제/구매완료 진행 중인 매물 id(버튼 비활성·중복 클릭 차단용). 없으면 null.
  final String? actionError; // 액션(삭제/구매완료) 실패·거부 한국어 메시지. 없으면 null.

  MyListingsState copyWith({
    AsyncValue<List<OwnListing>>? listings,
    String? busyId,
    String? actionError,
  }) {
    return MyListingsState(
      listings: listings ?? this.listings,
      // busyId/actionError 는 "지우기"가 필요해 명시 null 허용(copyWith 호출부가 항상 의도 전달).
      busyId: busyId,
      actionError: actionError,
    );
  }
}

class MyListingsController extends Notifier<MyListingsState> {
  @override
  MyListingsState build() {
    // 빌드 직후 본인 매물 목록을 비동기로 로드.
    Future.microtask(load);
    return const MyListingsState();
  }

  /// 본인 매물 목록 로드/새로고침. 세션 없으면 에러로 표시.
  Future<void> load() async {
    state = state.copyWith(listings: const AsyncValue.loading());
    try {
      final user = supabase.auth.currentUser;
      if (user == null) {
        state = state.copyWith(
          listings: AsyncValue.error('로그인이 필요합니다.', StackTrace.current),
        );
        return;
      }
      final repo = ref.read(listingsRepositoryProvider);
      final list = await repo.fetchOwnListings(sellerId: user.id);
      state = MyListingsState(listings: AsyncValue.data(list));
    } catch (e, st) {
      state = MyListingsState(listings: AsyncValue.error(e, st));
    }
  }

  /// 삭제(FR6) — 성공이면 목록 새로고침, 0행이면 한국어 거부(타인·없음). 진행 중 중복 클릭 차단.
  Future<void> delete(String id) async {
    if (state.busyId != null) return;
    // 액션 시작 시 직전 거부/오류 배너를 지운다(web ListingActions 가 handler 첫줄에서 setError(null) 하는 것과 동일).
    //   안 지우면 앞 액션이 남긴 거부 문구가 새 액션 진행 중에도 떠 있어 오해를 준다.
    state = state.copyWith(listings: state.listings, busyId: id, actionError: null);
    try {
      final repo = ref.read(listingsRepositoryProvider);
      final affected = await repo.deleteListing(id);
      if (affected == 0) {
        state = state.copyWith(
          listings: state.listings,
          actionError: ownDeleteDeniedMessage,
        );
        return;
      }
      await load(); // 성공 → 목록에서 즉시 제거 반영.
    } catch (e) {
      // ignore: avoid_print
      print('[my_listings] delete 실패: $e');
      state = state.copyWith(
        listings: state.listings,
        actionError: toKoreanListingError(e),
      );
    }
  }

  /// 구매 완료(FR8) — on_sale→sold. 성공이면 새로고침, 0행이면 한국어 거부(타인·없음·이미 sold). 중복 클릭 차단.
  Future<void> markSold(String id) async {
    if (state.busyId != null) return;
    // 액션 시작 시 직전 거부/오류 배너 제거(delete 와 동일 이유).
    state = state.copyWith(listings: state.listings, busyId: id, actionError: null);
    try {
      final repo = ref.read(listingsRepositoryProvider);
      final affected = await repo.markSold(id);
      if (affected == 0) {
        state = state.copyWith(
          listings: state.listings,
          actionError: ownMarkSoldDeniedMessage,
        );
        return;
      }
      await load(); // 성공 → 배지가 "판매완료"로 갱신.
    } catch (e) {
      // ignore: avoid_print
      print('[my_listings] markSold 실패: $e');
      state = state.copyWith(
        listings: state.listings,
        actionError: toKoreanListingError(e),
      );
    }
  }
}

final myListingsControllerProvider =
    NotifierProvider.autoDispose<MyListingsController, MyListingsState>(
  MyListingsController.new,
);
