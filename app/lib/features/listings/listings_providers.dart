// 매물 탐색·상세의 Riverpod providers.
// - listingsRepositoryProvider: 레포 1개 공유.
// - searchControllerProvider: 현재 필터 입력 + 검색 결과(AsyncValue) 보유. 검색 버튼이 갱신을 트리거.
// - listingDetailProvider(id): 상세 1건 비동기 조회(FutureProvider.family).
//
// 7.1 패턴: Riverpod 3 모던 Notifier + AsyncValue(로딩/에러/데이터).
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/supabase/supabase_client.dart';
import 'listing.dart';
import 'listing_filters.dart';
import 'listings_repository.dart';

/// 레포지토리 단일 인스턴스(전역 supabase 클라이언트 사용).
final listingsRepositoryProvider = Provider<ListingsRepository>((ref) {
  return ListingsRepository();
});

/// 매물 상세(id) — FutureProvider.family. 화면이 watch 하면 자동 로딩/에러/데이터 분기.
final listingDetailProvider =
    FutureProvider.family<ListingDetail?, String>((ref, id) async {
  final repo = ref.watch(listingsRepositoryProvider);
  return repo.fetchListing(id);
});

/// 홈 "최근 매물" 미리보기 — 빈 필터(전체 판매중)를 created_at desc 로 받아 상위 몇 건만.
/// fetchListings 가 이미 최신순 정렬이라 take 만 하면 된다. autoDispose 로 홈을 떠나면 캐시 정리.
final recentListingsProvider =
    FutureProvider.autoDispose<List<ListingCardData>>((ref) async {
  final repo = ref.watch(listingsRepositoryProvider);
  final list =
      await repo.fetchListings(ResolvedFilters.fromInput(const ListingFilterInput()));
  return list.take(4).toList();
});

/// 홈 "지금 인기" 섹션(spec-16-8) — view_count desc 상위 4건(web `fetchPopularAndRecentListings`
/// 미러). recentListingsProvider와 동형 — autoDispose로 홈을 떠나면 캐시 정리.
final popularListingsProvider =
    FutureProvider.autoDispose<List<ListingCardData>>((ref) async {
  final repo = ref.watch(listingsRepositoryProvider);
  return repo.fetchPopularListings();
});

/// 수정 진입용 본인 매물 단건(id) — 7.4. 현재 로그인 판매자 본인 매물만 조회(seller_id 필터 + RLS).
/// 0행이면 null(타인·없음) → 수정 화면이 한국어 차단. 세션 없으면 null 로 처리(차단 화면).
/// autoDispose: 수정 화면을 닫으면 캐시를 버려, 다음에 들어올 때 항상 최신 값을 다시 읽는다.
final editListingProvider =
    FutureProvider.autoDispose.family<ListingDetail?, String>((ref, id) async {
  final user = supabase.auth.currentUser;
  if (user == null) return null;
  final repo = ref.watch(listingsRepositoryProvider);
  return repo.fetchOwnListing(id, sellerId: user.id);
});

/// 탐색 화면 상태 = (현재 입력값) + (검색 결과 목록).
class SearchState {
  const SearchState({
    this.input = const ListingFilterInput(),
    this.results = const AsyncValue.data(<ListingCardData>[]),
  });

  final ListingFilterInput input;
  final AsyncValue<List<ListingCardData>> results;

  SearchState copyWith({
    ListingFilterInput? input,
    AsyncValue<List<ListingCardData>>? results,
  }) {
    return SearchState(
      input: input ?? this.input,
      results: results ?? this.results,
    );
  }
}

/// 탐색 컨트롤러. 화면이 입력을 갱신(updateInput)하고, 검색 버튼이 search() 를 부른다.
/// 첫 진입 시 자동으로 빈 필터 검색을 한 번 돌려 전체(판매중) 목록을 보여준다.
class SearchController extends Notifier<SearchState> {
  // "필터 진입 경합" 방어(spec-16-8 Design Notes) — 이 provider는 앱 전역 싱글턴이라 최초
  // 빌드 시 build()가 빈 필터 초기조회를 예약한다. 카테고리 칩으로 이번 세션 첫 진입해 그
  // 초기조회와 겹치면, 두 호출의 **응답이 어떤 순서로 와도** 마지막으로 호출된 쪽(= 가장 큰
  // requestId)만 화면에 반영되게 한다 — 응답 도착 순서가 아니라 **호출 순서**로 승자를 정한다.
  int _requestId = 0;

  @override
  SearchState build() {
    // 빌드 직후 초기 조회를 비동기로 시작(전체 판매중 목록).
    Future.microtask(search);
    return const SearchState(results: AsyncValue.loading());
  }

  /// 필터 입력값 갱신(화면의 폼 변경 반영). 검색은 별도 버튼(search)으로 — 입력마다 조회하지 않는다.
  void updateInput(ListingFilterInput input) {
    state = state.copyWith(input: input);
  }

  /// 현재 입력값을 검증·정규화해 조회. 결과를 AsyncValue 로 화면에 흘린다.
  Future<void> search() async {
    // 이 호출이 곧 "지금까지 중 가장 나중 호출"이 되도록 증가분을 동기 구간에서 확정한다
    // (await 전에 캡처) — 그래야 나중에 이 응답이 와도, 그 사이 더 나중 호출이 있었다면
    // 정확히 걸러진다.
    final requestId = ++_requestId;
    state = state.copyWith(results: const AsyncValue.loading());
    try {
      final filters = ResolvedFilters.fromInput(state.input);
      final repo = ref.read(listingsRepositoryProvider);
      final list = await repo.fetchListings(filters);
      if (requestId != _requestId) return; // 그 사이 더 나중 호출이 있었다 — 이 응답은 낡았다.
      state = state.copyWith(results: AsyncValue.data(list));
    } catch (e, st) {
      if (requestId != _requestId) return;
      state = state.copyWith(results: AsyncValue.error(e, st));
    }
  }
}

final searchControllerProvider =
    NotifierProvider<SearchController, SearchState>(SearchController.new);
