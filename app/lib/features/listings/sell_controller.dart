// 매물 등록 컨트롤러(7.3) — Riverpod 3 Notifier (7.2 SearchController 패턴).
//
// 화면(sell_screen)이 입력을 갱신(updateInput)하고 등록 버튼이 submit() 을 부른다.
// 상태 = 현재 입력값 + 진행상태(로딩) + 결과(error/success). 클라이언트 검증 통과 → INSERT.
//
// 흐름:
//   1) validateAndBuildListing(순수 함수) → 실패면 한국어 message 를 error 로 노출(INSERT 안 함).
//   2) 현재 세션 user 확인(없으면 "로그인이 필요합니다").
//   3) createListing(payload, sellerId: user.id) → 성공이면 success + 폼 초기화, 실패면 한국어 변환.
//   4) 로딩 중 재호출은 무시(중복 제출 차단).
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/supabase/supabase_client.dart';
import 'listing_errors.dart';
import 'listing_form.dart';
import 'listings_providers.dart';

/// 등록 화면 상태 = (현재 입력) + (로딩) + (에러/성공 메시지).
class SellState {
  const SellState({
    this.input = const ListingFormInput(),
    this.loading = false,
    this.error,
    this.success,
  });

  final ListingFormInput input;
  final bool loading;
  final String? error; // 한국어 검증/등록 오류(없으면 null).
  final String? success; // 등록 성공 안내(없으면 null).

  SellState copyWith({
    ListingFormInput? input,
    bool? loading,
    String? error,
    String? success,
  }) {
    return SellState(
      input: input ?? this.input,
      loading: loading ?? this.loading,
      // error/success 는 "지우기"가 필요해 명시적으로 null 을 허용한다(아래 clearMessages 사용).
      error: error,
      success: success,
    );
  }
}

class SellController extends Notifier<SellState> {
  @override
  SellState build() => const SellState();

  /// 입력값 갱신(폼 변경 반영). 입력이 바뀌면 직전 에러/성공 메시지는 지운다.
  void updateInput(ListingFormInput input) {
    state = SellState(input: input, loading: state.loading);
  }

  /// 등록 제출. 검증 → 세션 확인 → INSERT. 결과를 state(error/success)로 흘린다.
  Future<void> submit() async {
    if (state.loading) return; // 중복 제출 차단.

    // 1) 클라이언트 검증(순수 함수). 실패면 INSERT 없이 한국어 오류.
    final result = validateAndBuildListing(state.input);
    if (!result.isOk) {
      state = SellState(input: state.input, error: result.message);
      return;
    }

    state = SellState(input: state.input, loading: true);
    try {
      // 2) 현재 로그인 사용자 확인 — seller_id 명시용(위조는 RLS 가 막지만 명시가 정상 경로).
      final user = supabase.auth.currentUser;
      if (user == null) {
        state = SellState(input: state.input, error: '로그인이 필요합니다. 다시 로그인 후 시도해주세요.');
        return;
      }

      // 3) INSERT(on_sale 즉시 생성).
      final repo = ref.read(listingsRepositoryProvider);
      await repo.createListing(result.payload!, sellerId: user.id);

      // 성공 → 폼 초기화 + 성공 안내(즉시 노출 FR7).
      state = const SellState(
        input: ListingFormInput(),
        success: '매물이 등록되었습니다. 구매자에게 바로 노출됩니다.',
      );
    } catch (e) {
      // 원본 에러·코드는 화면에 노출 금지(콘솔만), 사용자에겐 한국어.
      // ignore: avoid_print
      print('[sell] listings insert 실패: $e');
      state = SellState(input: state.input, error: toKoreanListingError(e));
    }
  }
}

final sellControllerProvider =
    NotifierProvider<SellController, SellState>(SellController.new);
