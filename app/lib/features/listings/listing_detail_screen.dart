// 매물 상세 화면(FR10·11 재현) — id 로 판매중 매물 1건을 조회해 FR5 15필드 + 옵션·설명을 표시.
// 사진 갤러리(Story 16.2, web ListingGallery.tsx 미러 — 썸네일 스트립은 이식하지 않는다).
// 못 찾음(없음·sold·삭제)·조회 실패를 구분해 안내한다(web listings/[id] 패턴).
// 뒤로가기는 시스템 back(AppBar 기본 ← ) — 출처(탐색/AI결과)로 복귀(nav-ia R5).
import 'package:flutter/foundation.dart' show debugPrint, listEquals;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import '../chat/chat_providers.dart';
import '../chat/chat_repository.dart';
import '../chat/chat_room_screen.dart';
import '../wishlist/wish_button.dart';
import '../wishlist/wishlist_providers.dart';
import 'listing.dart';
import 'listing_photo_widgets.dart';
import 'listing_trust_widgets.dart';
import 'listings_providers.dart';

class ListingDetailScreen extends ConsumerWidget {
  const ListingDetailScreen({super.key, required this.listingId});

  final String listingId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(listingDetailProvider(listingId));

    return Scaffold(
      appBar: AppBar(title: const Text('매물 상세')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        // 조회 실패(네트워크·RLS·DB) — "못 찾음"과 구분해 빨강 에러.
        error: (e, _) => _MessageBody(
          key: const Key('detail_error'),
          icon: Icons.error_outline,
          color: AppColors.danger,
          message: '매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
        ),
        data: (listing) {
          // 못 찾음(없는 id·sold·삭제) → 구매자에게 비노출(FR11).
          if (listing == null) {
            return const _MessageBody(
              key: Key('detail_not_found'),
              icon: Icons.search_off,
              color: AppColors.inkMuted,
              message: '매물을 찾을 수 없습니다. 판매가 완료되었거나 삭제된 매물일 수 있습니다.',
            );
          }
          return _DetailContent(listing: listing);
        },
      ),
    );
  }
}

/// 못찾음/에러 공통 안내 본문.
class _MessageBody extends StatelessWidget {
  const _MessageBody({
    super.key,
    required this.icon,
    required this.color,
    required this.message,
  });

  final IconData icon;
  final Color color;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

/// 상세 본문 — 제목 + 기본정보(15필드) + 옵션 + 설명 + 문의하기(7.5).
///   ConsumerStatefulWidget: "문의하기" 탭 시 방 생성/재사용을 호출하는 동안 버튼을 비활성(중복 클릭 차단)해야 하므로.
class _DetailContent extends ConsumerStatefulWidget {
  const _DetailContent({required this.listing});

  final ListingDetail listing;

  @override
  ConsumerState<_DetailContent> createState() => _DetailContentState();
}

class _DetailContentState extends ConsumerState<_DetailContent> {
  bool _opening = false; // 방 생성/재사용 진행 중(중복 클릭 차단).

  ListingDetail get listing => widget.listing;

  @override
  void initState() {
    super.initState();
    // 조회수 +1(DW-740, Design Notes) — 이 State는 ListingDetailScreen.build()가 매물을
    // 이미 확인한 뒤(listing != null)에만 만들어지므로, initState는 State 인스턴스 생애주기당
    // 정확히 한 번만 실행돼 "매물 확인 후 정확히 1회" 호출 지점이 된다.
    // listingDetailProvider(family)는 재조회 시 다시 부를 위험이 있어(Design Notes) 쓰지
    // 않는다 — fire-and-forget(내부에서 실패를 스스로 삼킨다, listings_repository.dart 참조).
    ref.read(listingsRepositoryProvider).incrementListingView(listing.id);
  }

  // 문의하기 — 그 매물 판매자와의 방을 열고(있으면 재사용) 채팅방으로 이동. 실패는 한국어 SnackBar.
  //   seller_id 는 보내지 않는다(DB 트리거가 매물주로 강제). buyer=본인. 본인 매물이면 버튼이 애초에 안 뜬다.
  Future<void> _openChat() async {
    final myId = ref.read(currentUserProvider)?.id;
    if (myId == null) {
      // 비로그인 문의하기(FR58 행동 게이트, DW-738) — 방 생성(서버 쓰기) 없이 로그인으로 유도.
      context.go('/login');
      return;
    }
    if (_opening) return;
    setState(() => _opening = true);

    final res = await ref.read(chatRepositoryProvider).openOrCreateRoom(
          listingId: listing.id,
          buyerId: myId,
        );
    if (!mounted) return;
    setState(() => _opening = false);

    switch (res) {
      case OpenRoomSuccess(:final roomId):
        // rootNavigator: true — 이 화면이 홈의 최근 매물 카드처럼 셸 브랜치 안에서 도달됐을
        // 수 있으므로, 채팅방을 셸 밖 루트 Navigator에 쌓는다(spec-16-1 셸 경계).
        Navigator.of(context, rootNavigator: true).push(
          MaterialPageRoute(builder: (_) => ChatRoomScreen(roomId: roomId)),
        );
      case OpenRoomFailure(:final message):
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final myId = ref.watch(currentUserProvider)?.id;
    // 본인 매물(buyer=seller)이면 문의 버튼 숨김 — DB CHECK(23514)가 권위지만 UX상 미리 차단.
    final isOwnListing = myId != null && myId == listing.sellerId;

    return Scaffold(
      // spec-16-9(DW-735 해소) — 가격+문의하기를 본문 인라인 버튼 대신 sticky 바로 옮긴다.
      // 본인 매물이면 CTA 자체가 없다(기존 3분기 그대로 유지, 색·라벨도 새로 정하지 않는다).
      // Scaffold가 body 레이아웃에서 이 바의 높이를 자동으로 빼주므로, 옛 수동 하단 패딩
      // (`20 + viewPadding.bottom`, 문의하기 버튼이 시스템 내비바에 안 가리게 하려던 보정)은
      // 목적을 잃어 단순화한다 — 본인 매물(바 없음)은 SafeArea가 대신 그 자리를 보호한다.
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
        // 제목 = 제조사·모델 + 상태 배지(on_sale 만 도달하므로 "판매중").
        Row(
          children: [
            Expanded(
              child: Text(
                '[${listing.manufacturer}] ${listing.model}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.trustGreenBg,
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                '판매중',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.trustGreenInk,
                ),
              ),
            ),
            const SizedBox(width: 8),
            // 찜(♡, Story 16.3) — 제목 줄, 문서 흐름 안(inline 변형). 초기 상태는 카드 진입점과
            // 같은 단일 provider(wishedListingIdsProvider)에서 읽어 화면 간 어긋남이 없다.
            WishButton(
              key: const Key('detail_wish_button'),
              listingId: listing.id,
              initialWished:
                  ref.watch(wishedListingIdsProvider).value?.contains(listing.id) ?? false,
              variant: WishButtonVariant.inline,
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          '${listing.year}년 · ${wonText(listing.price)}',
          style: const TextStyle(color: AppColors.inkMuted),
        ),
        const SizedBox(height: 16),

        // 사진 갤러리 — 스와이프 + "k/N" 카운터(Story 16.2). 0장이면 플레이스홀더(CM-A, 크래시 없음).
        ListingGallery(imageUrls: listing.imageUrls),
        const SizedBox(height: 20),

        // 기본 정보(FR5 15필드).
        const Text('기본 정보', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        _row('제조사', listing.manufacturer),
        _row('모델', listing.model),
        _row('차종', listing.bodyType),
        _row('연식', '${listing.year}년'),
        _row('가격', wonText(listing.price)),
        _row('주행거리', kmText(listing.mileage)),
        _row('색상', listing.color),
        _row('연료', listing.fuel),
        _row('변속기', listing.transmission),
        _row('배기량', ccText(listing.displacement)),
        _row('승차인원', '${listing.seats}인승'),
        _row('지역', listing.region),
        _row('사고여부', listing.accidentFree ? '무사고' : '사고이력 있음'),
        if (listing.sellerName != null && listing.sellerName!.isNotEmpty)
          _row('판매자', listing.sellerName!),

        // 신뢰속성(Story 16.3) — 뱃지+면책이 한 위젯에서 함께 나온다(B9 결속). 값이 전부
        // 없으면 이 위젯은 아무 것도(여백조차) 그리지 않는다(AC3).
        TrustAttributesDetailSection(
          accidentStatus: listing.accidentStatus,
          isSingleOwner: listing.isSingleOwner,
          isNonSmoker: listing.isNonSmoker,
        ),

        // 옵션(있을 때만).
        if (listing.options != null && listing.options!.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('옵션', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: listing.options!
                .map((o) => Chip(label: Text(o, style: const TextStyle(fontSize: 12))))
                .toList(),
          ),
        ],

        // 설명(있을 때만).
        if (listing.description != null && listing.description!.trim().isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('설명', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(listing.description!),
        ],

          ],
        ),
      ),
      // 문의하기(7.5, FR19·FR58, spec-16-9로 sticky 바 이관) — 본인 매물이 아니면 로그인
      // 여부와 무관하게 렌더한다(화면 단위가 아니라 행동 단위 게이트, DW-738) — 비로그인이면
      // 탭할 때 _openChat이 서버 호출 없이 로그인으로 보낸다. 본인 매물이면
      // (myId!=null && myId==sellerId) 여전히 바 자체가 없다(기존 3분기 그대로 유지).
      bottomNavigationBar: isOwnListing
          ? null
          : SafeArea(
              // 시스템 제스처 바 영역을 이 바 스스로 흡수한다(spec-16-9 Design Notes) — Scaffold가
              // body에는 이미 이 바의 높이를 자동으로 빼줬으니, 여기서는 안전영역만 처리한다.
              top: false,
              child: Container(
                key: const Key('detail_sticky_bar'),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
                decoration: const BoxDecoration(
                  color: AppColors.surfaceRaised,
                  border: Border(top: BorderSide(color: AppColors.borderHairline)),
                  boxShadow: [
                    // 떠 있는 요소(DESIGN.md Elevation & Depth) — sticky 바는 더 강한 -12px 계열
                    // 겹 그림자를 쓴다.
                    BoxShadow(color: Color(0x1F000000), blurRadius: 20, offset: Offset(0, -12)),
                  ],
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        wonText(listing.price),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                          color: AppColors.priceEmphasis,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    // 색·라벨은 새로 정하지 않는다(Never) — 위치만 옮긴다. 분기 3개(본인 매물=
                    // 이 자리 자체가 없음/비로그인=탭 시 /login/타인 매물=openOrCreateRoom)도
                    // _openChat 하나에 그대로 유지한다.
                    FilledButton.icon(
                      key: const Key('go_chat_inquiry'),
                      onPressed: _opening ? null : _openChat,
                      icon: _opening
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.chat_bubble_outline),
                      label: Text(_opening ? '여는 중…' : '문의하기'),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 88,
            child: Text(label, style: const TextStyle(color: AppColors.inkMuted)),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

/// 상세 사진 갤러리 — PageView 스와이프 + "k/N" 카운터(web ListingGallery.tsx의 축약판,
/// 썸네일 스트립은 이식하지 않는다 — AC가 요구하는 건 스와이프+카운터뿐, A2 범위 최소화).
/// 0장이면 PageView를 만들지 않고 플레이스홀더만 그린다(CM-A, 크래시 없음).
class ListingGallery extends StatefulWidget {
  const ListingGallery({super.key, required this.imageUrls});

  final List<String> imageUrls;

  @override
  State<ListingGallery> createState() => _ListingGalleryState();
}

class _ListingGalleryState extends State<ListingGallery> {
  final _controller = PageController();
  int _index = 0;

  @override
  void didUpdateWidget(ListingGallery oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 사진 목록이 바뀐 채로 이 위젯 인스턴스가 재사용되면(예: provider 재조회) 이전 _index가
    // 새 리스트 길이를 넘어설 수 있다 — "5/3" 같은 불가능한 카운터를 막기 위해 0으로 되돌린다.
    if (!listEquals(widget.imageUrls, oldWidget.imageUrls)) {
      _index = 0;
      if (_controller.hasClients) {
        _controller.jumpToPage(0);
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final urls = widget.imageUrls;
    final count = urls.length;

    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: AspectRatio(
        aspectRatio: 5 / 3,
        child: LayoutBuilder(
          builder: (context, constraints) {
            // 표시 크기로 디코드해 메모리 사용을 실제 셀 크기에 맞춘다(원본 대신 셀 픽셀
            // 크기로 디코드 — 스와이프로 여러 장을 열어도 원본 전체를 메모리에 쌓지 않는다).
            final width =
                constraints.maxWidth * MediaQuery.devicePixelRatioOf(context);
            final cacheWidth = width.isFinite && width > 0 ? width.round() : null;
            return Stack(
              fit: StackFit.expand,
              children: [
                if (count == 0)
                  const PhotoPlaceholder()
                else
                  PageView.builder(
                    controller: _controller,
                    itemCount: count,
                    onPageChanged: (i) => setState(() => _index = i),
                    itemBuilder: (context, i) => Image.network(
                      urls[i],
                      fit: BoxFit.cover,
                      cacheWidth: cacheWidth,
                      errorBuilder: (context, error, stackTrace) {
                        // 사진은 부가정보 — 로드 실패를 "판매자가 사진을 안 올림"과 구분해 남긴다.
                        debugPrint('매물 상세 갤러리 사진 로드 실패(${urls[i]}): $error');
                        return const PhotoPlaceholder();
                      },
                    ),
                  ),
                // "k/N" 카운터 — 사진이 로드에 실패해 플레이스홀더가 떠도 계속 보인다
                // (분기 밖에 둔 이유: 장수 정보까지 함께 사라지면 안 된다, web과 동일 원칙).
                if (count >= 1)
                  Positioned(
                    bottom: 8,
                    right: 8,
                    child: PhotoCountBadge(text: '${_index + 1}/$count'),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
