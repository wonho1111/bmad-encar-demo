// 매물 등록 컨트롤러(7.3) — Riverpod 3 Notifier (7.2 SearchController 패턴).
//
// 화면(sell_screen)이 입력을 갱신(updateInput)하고 등록 버튼이 submit() 을 부른다.
// 상태 = 현재 입력값 + 진행상태(로딩) + 결과(error/success). 클라이언트 검증 통과 → INSERT.
//
// 흐름:
//   1) validateAndBuildListing(순수 함수) → 실패면 한국어 message 를 error 로 노출(INSERT 안 함).
//   2) 현재 세션 user 확인(없으면 "로그인이 필요합니다").
//   3) createListing(payload, sellerId: user.id) → 성공이면 listing_id를 받는다.
//   4) (Story 16.7) syncListingPhotos(listing_id) — 사진 반영. 개별 사진 실패는 폼 제출 자체를
//      막지 않는다(AC3) — listing은 이미 저장됐으므로 성공/실패 메시지를 함께 보여준다.
//   5) 로딩 중 재호출은 무시(중복 제출 차단).
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import 'listing_errors.dart';
import 'listing_form.dart';
import 'listings_providers.dart';
import 'photo_item.dart';
import 'photo_sync.dart';

/// 등록 화면 상태 = (현재 입력) + (로딩) + (에러/성공 메시지) + (수정 모드 식별자) + (주인).
/// 7.4에서 수정(edit) 모드 추가: editingId 가 null 이면 등록(INSERT), 값이 있으면 수정(UPDATE).
class SellState {
  const SellState({
    this.input = const ListingFormInput(),
    this.loading = false,
    this.error,
    this.success,
    this.editingId,
    this.done = false,
    this.owner,
    this.photos,
  });

  final ListingFormInput input;
  final bool loading;
  final String? error; // 한국어 검증/등록 오류(없으면 null).
  final String? success; // 등록/수정 성공 안내(없으면 null).
  final String? editingId; // null=등록 모드, 값=수정 대상 매물 id(수정 모드).
  final bool done; // 수정 성공 후 화면 닫기 신호(등록 모드에선 사용 안 함).

  /// syncListingPhotos 결과(Story 16.7) — listing 저장이 성공한 뒤에만 채워진다. 화면(sell_screen)이
  /// owner를 확인한 뒤 이 값을 로컬 업로더 상태로 받아들인다(성공/실패 항목이 그대로 담겨 있다).
  /// null이면 "이번 제출에서 사진 동기화가 일어나지 않았다"(검증 실패 등으로 listing 저장 전에
  /// 끝난 경우) — 화면은 그때 로컬 사진 상태를 그대로 유지해야 한다.
  final List<PhotoItem>? photos;

  /// 이 진행상태/결과를 시작한 **화면 인스턴스**의 식별자(SellScreen 이 자기 것을 넘긴다).
  ///
  /// ⚠️ editingId 만으로는 화면을 구분할 수 없다. 원래 이 상수가 지키던 시나리오는 하단 4탭
  /// 셸의 '/sell' 탭 루트(영구 마운트)와 옛 홈 퀵액션 go_sell이 push하던 **두 번째 등록
  /// 화면**이 둘 다 editingId==null이라 구분이 안 되던 것이었다(실측 재현) — go_sell은
  /// spec-16-8에서 제거돼 이 특정 조합은 지금 재현되지 않는다(후속 코드리뷰 spec-16-8 2차
  /// 리뷰 P8). 다만 '/sell' 탭 루트(등록, editingId=null)와 my_listings_screen.dart의
  /// "수정" 버튼이 여는 수정 화면(editingId=실제 매물 id)은 지금도 같은
  /// sellControllerProvider를 동시에 공유한다 — editingId 값이 우연히 갈리는 데 기대지 않고
  /// 인스턴스 식별자로 명시 구분하기 위해 이 필드를 유지한다.
  final Object? owner;

  SellState copyWith({
    ListingFormInput? input,
    bool? loading,
    String? error,
    String? success,
    String? editingId,
    bool? done,
    Object? owner,
    List<PhotoItem>? photos,
  }) {
    return SellState(
      input: input ?? this.input,
      loading: loading ?? this.loading,
      // error/success 는 "지우기"가 필요해 명시적으로 null 을 허용한다(아래 clearMessages 사용).
      error: error,
      success: success,
      editingId: editingId ?? this.editingId,
      done: done ?? this.done,
      owner: owner ?? this.owner,
      photos: photos ?? this.photos,
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
      owner: state.owner,
    );
  }

  /// 제출. 검증 → 세션 확인 → (등록 모드)INSERT / (수정 모드)UPDATE. 결과를 state 로 흘린다.
  ///
  /// editingId: 호출부(SellScreen)가 **항상 명시**한다 — null=등록, 값=그 id 수정.
  ///   ⚠️ **state.editingId로 폴백하지 않는다**(spec-16-1). 하단 4탭 셸이 '/sell' 브랜치를
  ///   영구 마운트하면서 이 provider의 `autoDispose`가 사실상 무력화됐다 — 수정 화면
  ///   (startEdit)을 한 번 거치면 state.editingId가 다음 등록 진입까지 살아남는다. 예전엔
  ///   `editingIdOverride ?? state.editingId`로 폴백해, 등록 탭에서 새 매물을 등록해도
  ///   직전 수정 대상이 그대로 UPDATE로 새는 데이터 손상이 실측됐다(review_loop_iteration 1,
  ///   bug #2, high). 화면이 명시한 값만 신뢰하면 이 leak이 원천 차단된다.
  ///
  /// owner: 호출한 **화면 인스턴스**의 식별자. 이 제출이 만드는 로딩/성공/에러에 그대로 실려,
  ///   각 화면이 `state.owner == 내 식별자`로 "내 결과인지"를 판정한다(SellState.owner 주석 참조).
  ///   생략하면 null 이 실려 어느 화면도 자기 것으로 보지 않는다(테스트가 컨트롤러만 구동할 때).
  ///
  /// photos/baseline(Story 16.7): 화면의 현재 업로더 상태 + 저장 기준선(무엇을 지웠는지 판단하는
  ///   근거, web SellForm.tsx의 baseline과 동일 역할). listing 저장(INSERT/UPDATE)이 성공한
  ///   **뒤에만** syncListingPhotos를 호출한다 — 등록은 listing_id가 이 시점에야 생기고, 수정도
  ///   "매물 정보 자체는 이미 저장됐다"를 지켜야 사진 실패가 폼 제출 전체를 막지 않는다(AC3).
  Future<void> submit({
    required String? editingId,
    Object? owner,
    List<PhotoItem> photos = const [],
    List<PhotoItem> baseline = const [],
  }) async {
    if (state.loading) return; // 중복 제출 차단.

    // 1) 클라이언트 검증(순수 함수). 실패면 쓰기 없이 한국어 오류. editingId 보존.
    final result = validateAndBuildListing(state.input);
    if (!result.isOk) {
      state = SellState(
        input: state.input,
        editingId: editingId,
        error: result.message,
        owner: owner,
      );
      return;
    }

    state = SellState(
      input: state.input,
      loading: true,
      editingId: editingId,
      owner: owner,
    );
    try {
      // 2) 현재 로그인 사용자 확인 — seller_id 명시용(위조는 RLS 가 막지만 명시가 정상 경로).
      //    전역 supabase 싱글턴을 직접 읽지 않고 currentUserProvider를 거친다 — 위젯 테스트가
      //    실제 Supabase.initialize 없이 이 컨트롤러를 구동할 수 있게 한다(chat_list_screen.dart와
      //    같은 이유, spec-16-1 Task).
      final user = ref.read(currentUserProvider);
      if (user == null) {
        state = SellState(
          input: state.input,
          editingId: editingId,
          error: '로그인이 필요합니다. 다시 로그인 후 시도해주세요.',
          owner: owner,
        );
        return;
      }

      final repo = ref.read(listingsRepositoryProvider);

      if (editingId == null) {
        // 3a) 등록 모드 — INSERT(on_sale 즉시 생성). id를 받아야 사진을 올릴 수 있다(AC5).
        final newListingId = await repo.createListing(result.payload!, sellerId: user.id);

        // 매물은 이미 등록됐다 — 여기서부터 실패해도 등록을 되돌리지 않는다(AC3). 등록은
        // "기존 사진이 0장인 수정"이라 baseline은 비어 있다(호출부 기본값).
        final photoResult = await syncListingPhotos(user.id, newListingId, photos, baseline);
        final photoNote = _photoNote(photoResult);

        // 성공 → 폼 초기화 + 성공 안내(즉시 노출 FR7). 사진은 성공/실패와 무관하게 화면과 함께
        // 초기화한다 — 다음 등록을 위한 빈 폼이 원칙이고, 실패한 사진이 남아 있어도 매물 자체는
        // "내 매물"에서 다시 열어 수정하며 재시도할 수 있다(edit_listing_screen.dart가 그 진입점).
        state = SellState(
          input: const ListingFormInput(),
          success: photoNote == null
              ? '매물이 등록되었습니다. 구매자에게 바로 노출됩니다.'
              : '매물이 등록되었습니다. 구매자에게 바로 노출됩니다. ($photoNote)',
          owner: owner,
          photos: const [],
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
            owner: owner,
          );
          return;
        }

        // 매물 정보 저장은 이미 성공했다 — 사진 반영 실패가 이 성공을 되돌리지 않는다(AC3).
        final photoResult = await syncListingPhotos(user.id, editingId, photos, baseline);
        final photoNote = _photoNote(photoResult);

        if (photoNote != null) {
          // 사진 처리가 일부 어긋났다 — 화면에 남겨 재시도할 수 있게 한다(닫으면 실패한 사진
          // 상태를 사용자가 다시 볼 방법이 없다). done은 false로 둔다(화면이 pop하지 않는다).
          state = SellState(
            input: state.input,
            editingId: editingId,
            success: '매물 정보가 수정되었습니다.',
            error: '사진 처리 중 일부가 실패했어요 ($photoNote). 아래에서 다시 시도한 뒤 다시 저장해주세요.',
            owner: owner,
            photos: photoResult.photos,
          );
          return;
        }

        // 성공 → 화면 닫기 신호(done) + 성공 안내. 목록은 재진입 시 새로고침된다.
        state = SellState(
          input: state.input,
          editingId: editingId,
          success: '매물 정보가 수정되었습니다.',
          done: true,
          owner: owner,
          photos: photoResult.photos,
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
        owner: owner,
      );
    }
  }

  /// syncListingPhotos 결과를 한 줄 한국어 사유로 요약한다. 실패·경고가 전혀 없으면 null —
  /// 호출부가 "성공"만 말하고 이 문구를 안내에 덧붙이지 않는다.
  String? _photoNote(PhotoSyncResult r) {
    final reasons = <String>[
      if (r.failedCount > 0) '사진 ${r.failedCount}장 실패',
      ...r.warnings,
    ];
    return reasons.isEmpty ? null : reasons.join(' · ');
  }
}

// autoDispose: 화면이 닫히면 상태를 버린다 → 등록 화면과 수정 화면이 같은 컨트롤러를 쓰더라도
//   서로의 입력/모드가 섞이지 않는다(수정 진입 시 startEdit 로 새로 채우고, 빠져나가면 초기화).
final sellControllerProvider =
    NotifierProvider.autoDispose<SellController, SellState>(SellController.new);
