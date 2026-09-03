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
import '../ai_search/ai_chat_screen.dart';
import '../ai_search/market_diagnosis.dart' show formatManKm;
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

/// "AI 시세 진단" 프리필 질의 문구 — web MarketDiagnosisButton.tsx buildPrefillQuery 미러.
/// 주행거리는 market_diagnosis.dart의 formatManKm(만km, 웹과 동일 함수 재사용 — 중복 정의
/// 금지)로, 가격은 기존 wonText(반올림 없음, 웹 formatPrice와 동일 규칙)로 표기한다.
@visibleForTesting
String buildMarketDiagnosisPrefillQuery(ListingCardData listing) {
  return '이 매물 시세 알려줘 — ${listing.manufacturer} ${listing.model} ${listing.year} · '
      '${formatManKm(listing.mileage)} · ${wonText(listing.price)}';
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

  // AI 시세 진단(5단계, web MarketDiagnosisButton.tsx 미러) — 프리필 질의 + 매물 요약 카드 +
  // listingId를 AiChatScreen에 실어 연다. 비로그인이면 문의하기(_openChat)와 동일한 게이트
  // (로그인으로 유도, 서버 호출 없음)를 탄다 — 이 화면의 기존 비로그인 패턴을 그대로 따른다.
  void _openMarketDiagnosis() {
    final myId = ref.read(currentUserProvider)?.id;
    if (myId == null) {
      context.go('/login');
      return;
    }
    // 프리필 카드 재료 = 표준 매물 카드(ListingCardData) 필드 계약(web과 동일, 2026-09-01
    // 표준 카드 교체 결정). 사진은 상세가 이미 들고 있는 갤러리 첫 장을 대표 사진으로 쓴다
    // (ListingDetail엔 imageCount가 따로 없으므로 "url 없으면 count도 0" 규칙을 여기서 직접
    // 지킨다 — ListingCardData.fromMap의 방침과 동일, listing.dart 참조).
    final imageCount = listing.imageUrls.length;
    final summary = ListingCardData(
      id: listing.id,
      manufacturer: listing.manufacturer,
      model: listing.model,
      year: listing.year,
      price: listing.price,
      mileage: listing.mileage,
      region: listing.region,
      sellerName: listing.sellerName,
      imageUrl: imageCount > 0 ? listing.imageUrls.first : null,
      imageCount: imageCount,
      fuel: listing.fuel,
      accidentStatus: listing.accidentStatus,
      isSingleOwner: listing.isSingleOwner,
      isNonSmoker: listing.isNonSmoker,
      options: listing.options,
    );
    Navigator.of(context, rootNavigator: true).push(
      MaterialPageRoute(
        builder: (_) => AiChatScreen(
          initialQuery: buildMarketDiagnosisPrefillQuery(summary),
          initialListingId: listing.id,
          initialListingSummary: summary,
        ),
      ),
    );
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
      // ✎ 2026-08-13 사용자 지적 #5("상세 퀄리티가 웹과 너무 다르다") — **웹 상세의 모바일
      //   순서를 그대로 옮겼다**(web `app/(user)/listings/[id]/page.tsx`).
      //   전(옛 구조): 제목·작은 회색 요약줄 → 갤러리 → 15행 표 한 덩어리 → 신뢰속성 → 옵션 → 설명.
      //   후(지금):   갤러리 → **요약 블록**(제목·연식 / 신뢰칩+짧은 면책 / 큰 가격 / 주요제원
      //              6칸) → 신뢰정보 → 차량정보(+설명) → 옵션 → 판매자정보 → 하단 고정 바.
      //   바뀐 것은 배치와 위계다 — 없던 정보를 지어내지 않았고(판매자정보만 웹이 이미 쓰던 RPC를
      //   앱에도 붙였다), 표의 행도 그대로다.
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          children: [
            // ① 사진 갤러리 — 스와이프 + "k/N" 카운터(Story 16.2). 0장이면 플레이스홀더
            //   (CM-A, 크래시 없음). 웹 모바일도 갤러리가 맨 위다.
            ListingGallery(imageUrls: listing.imageUrls),
            const SizedBox(height: 16),

            // ② 요약 블록(web `.summary-col`) — "스크롤 없이 CTA 옆에서 판단"이 목적이라
            //   제목·신뢰·가격·주요제원이 한 덩어리로 붙어 있다.
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    '[${listing.manufacturer}] ${listing.model} · ${listing.year}년',
                    key: const Key('detail_title'),
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w700, height: 1.35),
                  ),
                ),
                const SizedBox(width: 8),
                // 찜(♡, Story 16.3) — 제목 줄, 문서 흐름 안(inline 변형). 초기 상태는 카드
                // 진입점과 같은 단일 provider(wishedListingIdsProvider)에서 읽어 화면 간
                // 어긋남이 없다. 웹도 요약 카드 제목 줄에 하트를 둔다.
                WishButton(
                  key: const Key('detail_wish_button'),
                  listingId: listing.id,
                  initialWished:
                      ref.watch(wishedListingIdsProvider).value?.contains(listing.id) ??
                          false,
                  variant: WishButtonVariant.inline,
                ),
              ],
            ),
            // ✎ "판매중" 상태 배지를 뺐다 — 이 화면엔 판매중 매물만 도달하므로(sold·삭제는
            //   위 `_MessageBody`로 갈린다) 항상 같은 글자였다. 웹 요약 카드에도 없다.
            const SizedBox(height: 10),
            // 신뢰 칩 + 짧은 면책(web `variant='summary'`). 값이 없으면 아무것도 안 그린다 —
            // 그 경우의 설명은 아래 "신뢰정보" 섹션이 문장으로 답한다.
            TrustAttributesSummaryRow(
              accidentStatus: listing.accidentStatus,
              isSingleOwner: listing.isSingleOwner,
              isNonSmoker: listing.isNonSmoker,
            ),
            // 대표 가격 — 이 화면에서 가장 큰 숫자(웹 `text-price-lg` 30/800). 예전엔 제목 밑
            // 회색 12px 요약줄에 연식과 함께 묻혀 있었다.
            Text(
              wonText(listing.price),
              key: const Key('detail_price'),
              style: const TextStyle(
                  fontSize: 30, fontWeight: FontWeight.w800, color: AppColors.priceEmphasis),
            ),
            const SizedBox(height: 14),
            // 주요 제원 6칸(web `.spec-mini-grid`) — 아래 차량정보 표에 다 있는 값이지만,
            // 구매 판단에 가장 먼저 쓰이는 여섯 개를 스크롤 전에 보게 한다(의도된 중복).
            _SummarySpecGrid(listing: listing),
            const SizedBox(height: 20),

            // ③ 신뢰정보 — 속성별 설명 + 긴 면책(B9 결속). 값이 없어도 섹션은 그린다:
            //   "이 차 무사고인가?"에 화면이 아무 말도 안 하는 상태를 만들지 않는다(웹과 동일).
            _DetailSection(
              title: '신뢰정보',
              child: hasTrustAttributes(
                accidentStatus: listing.accidentStatus,
                isSingleOwner: listing.isSingleOwner,
                isNonSmoker: listing.isNonSmoker,
              )
                  ? TrustAttributesDetailSection(
                      accidentStatus: listing.accidentStatus,
                      isSingleOwner: listing.isSingleOwner,
                      isNonSmoker: listing.isNonSmoker,
                    )
                  : const Text(
                      trustEmptyMessage,
                      key: Key('detail_trust_empty'),
                      style: TextStyle(
                          color: AppColors.inkMuted, fontSize: 13, height: 1.45),
                    ),
            ),

            // ④ 차량정보(FR5 표) + 설명 — 행은 옛 "기본 정보" 표 그대로다(빼지도 더하지도
            //   않았다). "가격" 행만 2026-08-13에 뺀 상태가 유지된다(요약·하단 바와 3중복).
            _DetailSection(
              title: '차량정보',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _row('제조사', listing.manufacturer),
                  _row('모델', listing.model),
                  _row('차종', listing.bodyType),
                  _row('연식', '${listing.year}년'),
                  _row('주행거리', kmText(listing.mileage)),
                  _row('색상', listing.color),
                  _row('연료', listing.fuel),
                  _row('변속기', listing.transmission),
                  _row('배기량', ccText(listing.displacement)),
                  _row('승차인원', '${listing.seats}인승'),
                  _row('지역', listing.region),
                  _row('사고이력', listing.accidentFree ? '무사고' : '사고이력 있음'),
                  if (listing.sellerName != null && listing.sellerName!.isNotEmpty)
                    _row('판매자', listing.sellerName!),
                  const SizedBox(height: 10),
                  const Divider(height: 1, color: AppColors.borderHairline),
                  const SizedBox(height: 10),
                  const Text('설명',
                      style: TextStyle(color: AppColors.inkMuted, fontSize: 12)),
                  const SizedBox(height: 4),
                  // 설명이 없어도 자리를 남긴다(웹과 동일) — "없다"고 말하는 것과 아무 말도
                  // 안 하는 것은 다르다.
                  Text(
                    (listing.description != null && listing.description!.trim().isNotEmpty)
                        ? listing.description!
                        : '등록된 설명이 없습니다.',
                    style: TextStyle(
                      fontSize: 13.5,
                      height: 1.5,
                      color: (listing.description != null &&
                              listing.description!.trim().isNotEmpty)
                          ? AppColors.inkSecondary
                          : AppColors.inkMuted,
                    ),
                  ),
                ],
              ),
            ),

            // ⑤ 옵션 — 전량 표시. ⚠️ 웹은 5개 엔카 카테고리로 묶어 보여주는데(groupByCategory),
            //   앱엔 그 카테고리 표가 없다(`options.dart`엔 우선순위 목록만 있다). 카테고리
            //   표를 통째로 앱에 복제하는 건 이 지적의 범위를 넘어서므로 지금은 한 줄로
            //   나열한다 — 남은 차이로 대장에 남긴다.
            _DetailSection(
              title: '옵션',
              child: (listing.options == null || listing.options!.isEmpty)
                  ? const Text('등록된 옵션이 없습니다.',
                      style: TextStyle(color: AppColors.inkMuted, fontSize: 13))
                  : Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final o in listing.options!)
                          Container(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              border: Border.all(color: AppColors.borderHairline),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(o,
                                style: const TextStyle(
                                    fontSize: 12, color: AppColors.inkSecondary)),
                          ),
                      ],
                    ),
            ),

            // ⑥ 판매자정보(FR56) — 닉네임 + 가입 시점 + 다른 판매중 매물 N건. 웹 상세엔
            //   있었고 앱엔 통째로 없던 카드다.
            _SellerInfoSection(listing: listing),
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
                    const SizedBox(width: 8),
                    // "AI 시세 진단" 진입 버튼(5단계, web MarketDiagnosisButton.tsx 미러) —
                    // 문의하기(FilledButton, primary)와 나란히 OutlinedButton으로 시각 위계를
                    // 낮춰 둔다(문의하기가 이 화면의 주 행동이라는 기존 위계를 유지). 비로그인
                    // 처리는 _openMarketDiagnosis 내부에서 _openChat과 동일 패턴(로그인 게이트,
                    // 서버 호출 없음)을 탄다.
                    OutlinedButton(
                      key: const Key('go_market_diagnosis'),
                      onPressed: _openMarketDiagnosis,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
                      ),
                      child: const Text('AI 시세 진단', style: TextStyle(fontSize: 13)),
                    ),
                    const SizedBox(width: 8),
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

  /// 차량정보 한 줄 — 라벨(왼쪽·muted) / 값(오른쪽·굵게) + 아래 헤어라인. web `Field`와 같은
  /// 배치다(예전엔 라벨 88px 고정 + 값 왼쪽 정렬이라 값들이 가운데에 몰려 표로 안 읽혔다).
  /// **가로 배치를 유지한다** — 값이 길면 세로로 접지 않고 …로 자른다(D5).
  Widget _row(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 9),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.borderHairline)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          Text(label, style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5)),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

/// 상세의 정보 섹션 껍데기(web `Section`) — 카드 표면 + 섹션 제목. 네 섹션(신뢰정보·차량정보·
/// 옵션·판매자정보)이 같은 표면·같은 제목 위계를 갖게 한 자리에 모은다. 예전 상세엔 표면이
/// 아예 없어 모든 내용이 배경 위에 그냥 떠 있었다(사용자 지적 #5의 "퀄리티" 차이의 큰 부분).
class _DetailSection extends StatelessWidget {
  const _DetailSection({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderHairline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}

/// 주요 제원 6칸(web `.spec-mini-grid`) — 연식·주행거리·연료·배기량·지역·색상을 2열로.
/// 아래 차량정보 표에도 있는 값이다(의도된 중복 — 목적이 다르다: 여기는 "스크롤 전에 판단",
/// 표는 "전체 사양 확인"). `GridView` 대신 Row 2개로 짠다 — 항목이 6개 고정이고 스크롤 안에
/// 중첩 스크롤을 만들지 않기 위해서다.
class _SummarySpecGrid extends StatelessWidget {
  const _SummarySpecGrid({required this.listing});

  final ListingDetail listing;

  @override
  Widget build(BuildContext context) {
    final specs = <(String, String)>[
      ('연식', '${listing.year}년'),
      ('주행거리', kmText(listing.mileage)),
      ('연료', listing.fuel),
      ('배기량', ccText(listing.displacement)),
      ('지역', listing.region),
      ('색상', listing.color),
    ];
    return Container(
      key: const Key('detail_summary_specs'),
      padding: const EdgeInsets.only(top: 14),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.borderHairline)),
      ),
      child: Column(
        children: [
          for (var i = 0; i < specs.length; i += 2)
            Padding(
              padding: EdgeInsets.only(bottom: i + 2 < specs.length ? 12 : 0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: _cell(specs[i])),
                  const SizedBox(width: 16),
                  Expanded(
                    child: i + 1 < specs.length
                        ? _cell(specs[i + 1])
                        : const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _cell((String, String) spec) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(spec.$1,
            style: const TextStyle(color: AppColors.inkMuted, fontSize: 11.5)),
        const SizedBox(height: 2),
        Text(
          spec.$2,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
      ],
    );
  }
}

/// "YYYY년 M월 가입" — web `formatSellerJoinDate`의 앱 미러(순수함수라 단위테스트 대상).
/// null·빈 값·파싱 불가는 전부 null(행 숨김) — RPC 실패와 값 없음을 구분하지 않는다.
/// ⚠️ 한국 서비스이므로 **KST 고정**이다: 기기 타임존을 그대로 쓰면 해외 로밍·에뮬레이터에서
/// 자정 전후 값이 한 달 어긋난다(웹이 같은 이유로 `timeZone: 'Asia/Seoul'`을 명시한다).
/// Flutter는 `Intl.DateTimeFormat` 같은 타임존 지정 수단이 없어 UTC로 파싱한 뒤 +9시간을
/// 직접 더한다(한국은 서머타임이 없어 고정 오프셋으로 정확하다).
@visibleForTesting
String? formatSellerJoinDate(String? joinedAt) {
  if (joinedAt == null || joinedAt.trim().isEmpty) return null;
  final parsed = DateTime.tryParse(joinedAt);
  if (parsed == null) return null;
  final kst = parsed.toUtc().add(const Duration(hours: 9));
  return '${kst.year}년 ${kst.month}월 가입';
}

/// "이 판매자의 다른 판매중 매물 N건" — web `sellerOtherListingsLabel`의 앱 미러.
/// null(조회 실패)이면 null(행 숨김), 0이면 "없어요" 문구로 갈린다.
@visibleForTesting
String? sellerOtherListingsLabel(int? count) {
  if (count == null) return null;
  if (count <= 0) return '이 판매자의 다른 판매중 매물이 없어요.';
  return '이 판매자의 다른 판매중 매물 $count건';
}

/// 판매자정보 카드(FR56) — 닉네임 + 가입 시점 + 다른 판매중 매물 수. 평판·응답률·인증 배지처럼
/// **데이터가 없는 지표는 절대 만들지 않는다**(FR56 Never). 값이 하나도 없으면 카드를 그리지
/// 않는다(빈 섹션 금지) — 그때 문의는 하단 고정 바가 그대로 담당한다.
class _SellerInfoSection extends ConsumerWidget {
  const _SellerInfoSection({required this.listing});

  final ListingDetail listing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref
        .watch(sellerSummaryProvider(
            (sellerId: listing.sellerId, listingId: listing.id)))
        .value;
    final name = listing.sellerName;
    final joinLabel = formatSellerJoinDate(summary?.joinedAt);
    final otherLabel = sellerOtherListingsLabel(summary?.otherOnSaleCount);

    // 조회 중(=summary null)에도 닉네임만으로 카드를 그린다 — 나머지 두 줄은 값이 오면 채워진다.
    if ((name == null || name.isEmpty) && joinLabel == null && otherLabel == null) {
      return const SizedBox.shrink();
    }

    return _DetailSection(
      title: '판매자정보',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (name != null && name.isNotEmpty)
            Text(name,
                key: const Key('detail_seller_name'),
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          if (joinLabel != null) ...[
            const SizedBox(height: 4),
            Text(joinLabel,
                style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5)),
          ],
          if (otherLabel != null) ...[
            const SizedBox(height: 4),
            Text(otherLabel,
                style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5)),
          ],
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
