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

/// 등록 화면 상태 = (현재 입력) + (로딩) + (에러/성공 메시지) + (수정 모드 식별자).
/// 7.4에서 수정(edit) 모드 추가: editingId 가 null 이면 등록(INSERT), 값이 있으면 수정(UPDATE).
class SellState {
  const SellState({
    this.input = const ListingFormInput(),
    this.loading = false,
    this.error,
    this.success,
    this.editingId,
    this.done = false,
  });

  final ListingFormInput input;
  final bool loading;
  final String? error; // 한국어 검증/등록 오류(없으면 null).
  final String? success; // 등록/수정 성공 안내(없으면 null).
  final String? editingId; // null=등록 모드, 값=수정 대상 매물 id(수정 모드).
  final bool done; // 수정 성공 후 화면 닫기 신호(등록 모드에선 사용 안 함).

  SellState copyWith({
    ListingFormInput? input,
    bool? loading,
    String? error,
    String? success,
    String? editingId,
    bool? done,
  }) {
    return SellState(
      input: input ?? this.input,
      loading: loading ?? this.loading,
      // error/success 는 "지우기"가 필요해 명시적으로 null 을 허용한다(아래 clearMessages 사용).
      error: error,
      success: success,
      editingId: editingId ?? this.editingId,
      done: done ?? this.done,
    );
  }
}

class SellController extends Notifier<SellState> {
  @override
  SellState build() => const SellState();

  /// 수정 모드 초기화 — 기존 매물 값을 폼에 채우고 editingId 를 설정한다(7.4 수정 화면 진입 시 호출).
  void startEdit(String listingId, ListingFormInput initial) {
    state = SellState(input: initial, editingId: listingId);
  }

  /// 입력값 갱신(폼 변경 반영). 입력이 바뀌면 직전 에러/성공 메시지는 지운다.
  /// editingId(모드)는 보존한다 — 입력만 바뀌었다고 등록/수정 모드가 바뀌면 안 된다.
  void updateInput(ListingFormInput input) {
    state = SellState(
      input: input,
      loading: state.loading,
      editingId: state.editingId,
    );
  }

  /// 제출. 검증 → 세션 확인 → (등록 모드)INSERT / (수정 모드)UPDATE. 결과를 state 로 흘린다.
  ///
  /// editingIdOverride: 화면이 수정 모드 id 를 명시 전달하면 그것을 우선한다.
  ///   startEdit 가 post-frame 으로 늦게 도는 첫 프레임에 submit 이 들어와도 등록(INSERT)로 새지 않게 하는 안전장치.
  Future<void> submit({String? editingIdOverride}) async {
    if (state.loading) return; // 중복 제출 차단.
    final editingId = editingIdOverride ?? state.editingId;

    // 1) 클라이언트 검증(순수 함수). 실패면 쓰기 없이 한국어 오류. editingId 보존.
    final result = validateAndBuildListing(state.input);
    if (!result.isOk) {
      state = SellState(
        input: state.input,
        editingId: editingId,
        error: result.message,
      );
      return;
    }

    state = SellState(input: state.input, loading: true, editingId: editingId);
    try {
      // 2) 현재 로그인 사용자 확인 — seller_id 명시용(위조는 RLS 가 막지만 명시가 정상 경로).
      final user = supabase.auth.currentUser;
      if (user == null) {
        state = SellState(
          input: state.input,
          editingId: editingId,
          error: '로그인이 필요합니다. 다시 로그인 후 시도해주세요.',
        );
        return;
      }

      final repo = ref.read(listingsRepositoryProvider);

      if (editingId == null) {
        // 3a) 등록 모드 — INSERT(on_sale 즉시 생성).
        await repo.createListing(result.payload!, sellerId: user.id);
        // 성공 → 폼 초기화 + 성공 안내(즉시 노출 FR7).
        state = const SellState(
          input: ListingFormInput(),
          success: '매물이 등록되었습니다. 구매자에게 바로 노출됩니다.',
        );
      } else {
        // 3b) 수정 모드 — UPDATE(15필드, status·seller_id 미포함). 0행이면 RLS 차단(타인)·없음.
        //     payload 에 status 가 들어있어(validateAndBuild 가 'on_sale' 동봉) 수정 시 상태가 덮어쓰이는 걸 막는다.
        final payload = Map<String, dynamic>.from(result.payload!)..remove('status');
        final affected = await repo.updateListing(editingId, payload);
        if (affected == 0) {
          state = SellState(
            input: state.input,
            editingId: editingId,
            error: ownEditDeniedMessage,
          );
          return;
        }
        // 성공 → 화면 닫기 신호(done) + 성공 안내. 목록은 재진입 시 새로고침된다.
        state = SellState(
          input: state.input,
          editingId: editingId,
          success: '매물 정보가 수정되었습니다.',
          done: true,
        );
      }
    } catch (e) {
      // 원본 에러·코드는 화면에 노출 금지(콘솔만), 사용자에겐 한국어.
      // ignore: avoid_print
      print('[sell] listings 쓰기 실패(editingId=$editingId): $e');
      state = SellState(
        input: state.input,
        editingId: editingId,
        error: toKoreanListingError(e),
      );
    }
  }
}

// autoDispose: 화면이 닫히면 상태를 버린다 → 등록 화면과 수정 화면이 같은 컨트롤러를 쓰더라도
//   서로의 입력/모드가 섞이지 않는다(수정 진입 시 startEdit 로 새로 채우고, 빠져나가면 초기화).
final sellControllerProvider =
    NotifierProvider.autoDispose<SellController, SellState>(SellController.new);
