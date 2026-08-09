// 찜(♡) 토글 버튼 (Story 16.3, 로그인 게이트는 16.6 추가) — web WishButton.tsx의 Flutter
// 미러이되, `redirectedFrom`(로그인 후 원래 화면으로 복귀시키는 쿼리) 로직은 이식하지
// 않는다 — 그냥 `/login`으로 보낸다(go_router 스택상 뒤로가기로 복귀 가능).
//
// ⚠️ **이 헤더가 한때 갖고 있던 전제는 16.6에서 깨졌다.** 예전 문구: "앱은 라우터 전역이 이미
// 로그인 필수라 게이트 이식 안 함"(app_router.dart의 redirect가 미인증을 전 경로에서 /login
// 으로 보냈으므로 이 버튼까지 도달할 때는 이미 로그인 상태였다). 16.6이 FR58(비로그인 매물
// 열람, DW-738)을 앱에도 열면서 `/home`이 미인증 예외가 됐고, 이 버튼도 비로그인으로 눌릴 수
// 있는 자리가 됐다 — 그래서 아래 `_toggle()`이 탭 진입부에서 `currentUserProvider`를 직접
// 확인해 서버 쓰기 없이 `/login`으로 보낸다(행동 단위 게이트, `requireUser`를 재사용하지
// 않는 이유는 spec-16-6 Design Notes 참조 — 화면 전체를 막으면 비로그인도 봐야 하는 목록·
// 상세 본문까지 가려진다).
//
// 책임:
//   1) 낙관적 토글: 누르면 즉시 하트가 채워짐/비워짐 → wishlists insert/delete 확정.
//      실패 시 아이콘을 직전 상태로 롤백 + SnackBar 안내(전역 토스트 인프라 신설 금지 —
//      기존 ScaffoldMessenger 관례 재사용, listing_detail_screen.dart _openChat과 동일 패턴).
//   2) 진행 중 연타 차단: pending이면 버튼이 disabled(onTap이 null이라 탭 이벤트 자체가 안 붙는다).
//   3) 토글 성공 시 wishedListingIdsProvider·wishlistProvider를 invalidate — 다른 화면
//      (홈/검색/AI)의 카드는 다음 리빌드에 최신 하트 상태를, 찜 목록 화면 자신은 해제한
//      타일이 즉시 사라지는 것을 반영한다(spec-16-3 Boundaries, AC5).
//   4) 히트영역 44×44 유지, Semantics로 "찜하기"/"찜 취소" 라벨 전환(웹 aria-pressed 미러).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show PostgrestException;

import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import 'wishlist_providers.dart';

/// 찜 버튼 히트영역(44×44) — `listing_card.dart`가 사진 하단 겹침 오프셋 계산에 같은 값을
/// 써야 어긋나지 않는다(코드리뷰 지적 — 5:3 사진비율 상수 중복을 잡은 것과 같은 결함 패턴이
/// 이 값에도 있었다). 한 곳(여기)만 값을 갖고 다른 파일은 이 상수를 가져다 쓴다.
const double kWishButtonSize = 44;

enum WishButtonVariant {
  card, // 카드 안(사진 밖, 사진 하단 우측에 겹침) — 그림자로 배경과 구분.
  inline, // 문서 흐름 안의 평범한 버튼(매물 상세 제목 줄) — 테두리로 경계를 준다.
}

class WishButton extends ConsumerStatefulWidget {
  const WishButton({
    super.key,
    required this.listingId,
    required this.initialWished,
    this.variant = WishButtonVariant.card,
  });

  final String listingId;
  final bool initialWished;
  final WishButtonVariant variant;

  @override
  ConsumerState<WishButton> createState() => _WishButtonState();
}

class _WishButtonState extends ConsumerState<WishButton> {
  bool _wished = false;
  bool _pending = false;

  @override
  void initState() {
    super.initState();
    _wished = widget.initialWished;
  }

  @override
  void didUpdateWidget(WishButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    // listingId 자체가 바뀌면(예: ListView가 key 없이 이 자리의 매물을 다른 매물로 재사용)
    // 이 위젯은 완전히 다른 매물을 가리키게 된 것이다 — _pending 여부와 무관하게 무조건
    // 새 initialWished로 리셋한다(B9: 호출부의 ValueKey는 2차 방어일 뿐, 이 위젯 자체가
    // 안전해야 한다). 그러지 않으면 직전 매물의 낙관적/pending 상태가 새 매물에 그대로
    // 들러붙는다.
    if (widget.listingId != oldWidget.listingId) {
      _wished = widget.initialWished;
      _pending = false;
      return;
    }
    // 다른 화면에서 토글해 wishedListingIdsProvider가 invalidate되면 이 카드가 리빌드되며
    // initialWished가 바뀐다 — 진행 중(_pending)이 아닐 때만 동기화한다(낙관적 반영 도중에
    // 덮어써서 화면이 깜빡이며 되돌아가는 것을 막는다).
    if (!_pending && widget.initialWished != oldWidget.initialWished) {
      _wished = widget.initialWished;
    }
  }

  Future<void> _toggle() async {
    if (_pending) return;
    if (ref.read(currentUserProvider) == null) {
      // 비로그인 찜(FR58 행동 게이트, DW-738) — 서버 쓰기(wishlists insert/delete) 없이
      // 로그인으로 유도. 낙관적 반영도 시작하지 않는다(아래 setState 전에 반환).
      context.go('/login');
      return;
    }
    final next = !_wished;
    // await 전에 컨테이너를 미리 잡아둔다 — `ref`(ConsumerState)는 위젯이 disposed되면 더 못
    // 쓰지만, 이 컨테이너 참조는 계속 유효하다. 하트를 누르자마자 화면을 나가면(await 도중
    // dispose) 서버 쓰기는 성공했는데도 예전엔 `if (!mounted) return;`이 두 invalidate
    // 앞에 있어 통째로 스킵됐다(코드리뷰 지적) — wishedListingIdsProvider는 non-autoDispose라
    // 다른 화면들이 세션 내내 그 낡은 값을 계속 본다.
    final container = ProviderScope.containerOf(context, listen: false);
    setState(() {
      _pending = true;
      _wished = next; // 낙관적 반영 — 서버 확정 전에 즉시 아이콘부터 바꾼다.
    });
    try {
      final repo = ref.read(wishlistRepositoryProvider);
      await repo.toggle(widget.listingId, wish: next);
      // 토글 성공은 mounted 여부와 무관하게 항상 무효화한다(위 주석) — setState 등 UI
      // 갱신에만 mounted 가드를 남긴다.
      container.invalidate(wishedListingIdsProvider);
      // 찜 목록 화면 자체도 무효화한다 — 그 화면 안에서 하트를 눌러 해제하면(위 provider만
      // invalidate할 경우) 하트는 바로 비지만 타일은 탭을 나갔다 들어올 때까지 남아있었다
      // (코드리뷰 지적).
      container.invalidate(wishlistProvider);
    } catch (e) {
      // 예외 전체($e)를 찍지 않는다 — PostgrestException.toString()엔 서버 details가 그대로
      // 실려 wishlists 유니크 위반이면 "Key (user_id, listing_id)=(<uuid>, <uuid>)"처럼 개인
      // 식별값이 남는다(listings_repository.dart pickCoverImages 주석과 동일 원칙 — debugPrint는
      // release에서도 살아 있다). 모양(타입·코드)만 남긴다.
      debugPrint('[wishlist] 찜 토글 실패: ${e.runtimeType}'
          '${e is PostgrestException ? '(${e.code})' : ''}');
      if (!mounted) return;
      setState(() => _wished = !next); // 롤백 — 직전 상태로 복귀.
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(const SnackBar(content: Text('찜 처리에 실패했어요. 잠시 후 다시 시도해주세요.')));
    } finally {
      if (mounted) setState(() => _pending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final onCard = widget.variant == WishButtonVariant.card;
    return Semantics(
      button: true,
      enabled: !_pending, // 진행 중엔 onTap이 null이라 실제로 눌러도 반응 없다 — 스크린리더도 그렇게 안다.
      toggled: _wished,
      label: _wished ? '찜 취소' : '찜하기',
      child: SizedBox(
        key: const Key('wish_button'),
        width: kWishButtonSize,
        height: kWishButtonSize,
        child: Material(
          color: AppColors.surfaceRaised,
          shape: CircleBorder(
            side: onCard
                ? BorderSide.none
                : const BorderSide(color: AppColors.borderHairline),
          ),
          elevation: onCard ? 2 : 0,
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: _pending ? null : _toggle,
            child: Center(
              child: Icon(
                _wished ? Icons.favorite : Icons.favorite_border,
                color: AppColors.inkPrimary,
                size: 20,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
