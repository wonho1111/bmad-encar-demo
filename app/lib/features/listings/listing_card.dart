// 매물 카드 위젯 — 탐색 목록·AI 검색 결과·홈 미리보기가 공유한다(web ListingCard 의 Flutter 판).
// 사진 5:3 대표 + "N장" 배지(Story 16.2, web ListingCardImage.tsx 미러) +
// 요약(제조사·모델·연식 / 가격(강조) / 주행·연료·지역, Story 10.1·대장 #67) + (있으면) 판매자 이름.
// 누르면 매물 상세로 이동(onTap 콜백을 받아 상위가 라우팅 — 화면 의존을 줄임).
// 디자인: 웹 DESIGN.md 라이트 팔레트(Story 16.1) — 흰 카드 + border-hairline, 가격을 굵게 강조.
//
// 신뢰속성 뱃지·찜 버튼(Story 16.3, web ListingCard.tsx 2026-08-05 레이아웃 미러 — spec-16-3
// Design Notes: 정본은 epic-16-context.md의 산문이 아니라 이 웹 코드다). 찜 버튼은 web
// `top-full mt-1`을 그대로 미러해 사진 "아래"(경계에 걸치지 않고 완전히 밖)에 건다 —
// 실측(코드리뷰): 사진 경계에 절반 겹치던 이전 배치는 사진 우하단 "N장" 배지와 겹쳤다(P1).
// 그 결과 버튼은 카드 안(정보 영역 위)에 온전히 들어오므로 카드 자체의 clip은 다시 켠다(P2 —
// "카드를 자르면 안 된다"던 이전 전제는 실측상 거짓이었다). 사진 위쪽 모서리만 별도
// `ClipRRect`로 둥글게 유지한다.
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import '../wishlist/wish_button.dart';
import 'listing.dart';
import 'listing_photo_widgets.dart';
import 'listing_trust_widgets.dart';

/// 대표사진 가로:세로 비율 — `_CardPhoto`의 `AspectRatio`와 아래 `LayoutBuilder`의
/// `photoHeight`(찜 버튼 위치 계산용) 두 곳이 이 상수 하나를 공유한다. 예전엔 두 곳에
/// `5/3`·`3/5` 리터럴이 따로 있어, 비율이 바뀌면 한쪽만 고쳐지고 찜 버튼이 사진 경계에서
/// 어긋날 수 있었다(코드리뷰 지적).
const double _cardPhotoAspectRatio = 5 / 3;

/// 사진 폭(LayoutBuilder가 준 `constraints.maxWidth`)에서 안전한 사진 높이를 계산한다(찜 버튼
/// `Positioned.top` 계산용). `maxWidth`가 무한/0 이하일 수 있는 자리(예: 폭 제약 없는 가로
/// 리스트에 이 카드가 놓이는 경우)를 방어한다 — 그러지 않으면 이 값이 Infinity가 되어
/// `Positioned.top`이 비정상 값을 받는다(`_CardPhoto`의 `cacheWidth` 가드와 같은 원칙).
/// `@visibleForTesting`: 위젯 전체를 실제로 무한 폭 부모(가로 스크롤 등)에 렌더하면 `_CardPhoto`
/// 쪽 별개의 `Column`(`CrossAxisAlignment.stretch`)이 이 값과 무관하게 먼저 죽는다(Flutter가
/// "무한 폭 + stretch"를 허용하지 않는 별개의 제약, 실측 확인 — listing_card.dart의 다른 부분과
/// 얽힌 기존 결함이라 이 스토리 범위 밖). 그래서 위젯 테스트로는 이 가드 자체를 격리해서 볼 수
/// 없어 순수함수로 뽑아 직접 잰다.
@visibleForTesting
double safeCardPhotoHeight(double maxWidth) {
  final safeWidth = maxWidth.isFinite && maxWidth > 0
      ? maxWidth
      : 300.0; // 일반적인 폰 폭 근사치(임의지만 안전한 폴백일 뿐 — 정상 경로에선 안 쓰인다).
  return safeWidth / _cardPhotoAspectRatio;
}

class ListingCard extends StatelessWidget {
  const ListingCard({super.key, required this.listing, this.onTap, required this.wished});

  final ListingCardData listing;
  final VoidCallback? onTap;
  // 찜 여부 — wire 필드가 아니라 호출부가 wishedListingIdsProvider 결과로 주입하는 sibling
  // prop이다(docs/conventions.md §4 "찜 여부는 ListingCard wire 필드가 아니다", spec-16-3
  // Design Notes와 동일 원칙). required — 기본값(false)을 뒀던 예전 버전은, 이 카드를 새로
  // 쓰는 화면이 wished를 깜빡 빠뜨려도 컴파일이 통과해 "하트가 항상 비어 보이는" 실패가
  // 조용히 배포될 수 있었다(코드리뷰 지적 P14 — 정확히 이 스토리가 막으려던 "화면마다 하트
  // 상태가 어긋난다"는 실패를 기본값 자체가 다시 열어 둔 셈이다).
  final bool wished;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      elevation: 0,
      color: AppColors.surfaceRaised,
      // 찜 버튼이 사진 "아래"(경계 밖, web top-full 미러 — P1)에 오므로 카드 폭 안에
      // 온전히 들어온다(실측: 카드 높이 ≈ photoHeight+88, 버튼 하단 = photoHeight+48) —
      // 그래서 카드 자체를 다시 자른다(잉크 스플래시가 둥근 모서리 밖으로 번지는 것도 막는다).
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.borderHairline),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // 사진 높이 — 찜 버튼을 그 아래에 놓기 위한 계산(web top-full 미러). 가드
          // 로직은 위 safeCardPhotoHeight 참조.
          final photoHeight = safeCardPhotoHeight(constraints.maxWidth);
          return Stack(
            clipBehavior: Clip.none,
            children: [
              ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
                child: InkWell(
                  onTap: onTap,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _CardPhoto(listing: listing),
                      Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // 제조사·모델·연식 — 한 줄 요약. 우측 여백은 찜 버튼이 사진 바로
                            // 아래에서 이 줄까지 겹치는 구간(P1) 확보용(web pr-14 미러).
                            Padding(
                              padding: const EdgeInsets.only(right: 52),
                              child: Text(
                                '[${listing.manufacturer}] ${listing.model} · ${listing.year}년',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600, color: AppColors.inkPrimary),
                              ),
                            ),
                            const SizedBox(height: 3),
                            // 가격 — 굵게 강조(원·천단위 콤마). 찜 버튼 하단(photoHeight+48)이
                            // 이 줄까지 겹치므로 위 제목 줄과 같은 우측 여백을 준다(web pr-14
                            // 미러 — meta 줄은 버튼 아래라 여백이 필요 없다, P1).
                            Padding(
                              padding: const EdgeInsets.only(right: 52),
                              child: Text(
                                wonText(listing.price),
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 15,
                                    color: AppColors.inkPrimary),
                              ),
                            ),
                            const SizedBox(height: 3),
                            // 주행거리·연료·지역 — 보조 정보(muted). web ListingCard.tsx meta 줄과
                            // 같은 모양(`주행 · 연료 · 지역`, 대장 #67) — fuel이 없으면(계약-외 값)
                            // 그 마디만 생략한다. 한 줄 가로 유지(D5) — 넘치면 줄바꿈이 아니라
                            // ellipsis로 자른다.
                            Text(
                              <String?>[kmText(listing.mileage), listing.fuel, listing.region]
                                  .where((s) => s != null && s.isNotEmpty)
                                  .join(' · '),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5),
                            ),
                            // 판매자 표시 이름(있을 때만). AI 결과처럼 값이 없으면 줄 자체를 숨긴다.
                            if (listing.sellerName != null && listing.sellerName!.isNotEmpty) ...[
                              const SizedBox(height: 2),
                              Text(
                                '판매자 ${listing.sellerName}',
                                style: const TextStyle(color: AppColors.inkMuted, fontSize: 11),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // 신뢰속성 뱃지 — 사진 좌상단 오버레이, 면책 없음(spec-16-3 Boundaries). IgnorePointer:
              // 오버레이가 InkWell(카드 탭) 위에 겹치므로 그대로 두면 뱃지 라벨을 탭했을 때 카드
              // 탭 자체가 먹히지 않는다(코드리뷰 지적, web `pointer-events-none` 미러).
              Positioned(
                left: 8,
                right: 8,
                top: 8,
                child: IgnorePointer(
                  child: TrustAttributesCardOverlay(
                    accidentStatus: listing.accidentStatus,
                    isSingleOwner: listing.isSingleOwner,
                    isNonSmoker: listing.isNonSmoker,
                  ),
                ),
              ),
              // 찜(♡) — 사진 밖, 사진 하단 경계 바로 아래(web `top-full mt-1` 미러, P1 —
              // 예전엔 경계에 절반 겹쳐 우하단 "N장" 배지와 겹쳤다, 코드리뷰 실측).
              Positioned(
                right: 8,
                top: photoHeight + 4,
                child: WishButton(listingId: listing.id, initialWished: wished),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// 카드 상단 5:3 대표사진 — 없으면 플레이스홀더, 로드 실패도 같은 플레이스홀더로 폴백.
/// "N장" 배지는 `imageCount>=1`이면 사진 로드 성공 여부와 무관하게 표시한다(장수는 DB 행 수
/// 그대로가 아니라 계약-검증을 통과한 행 수다 — listings_repository.dart의 pickCoverImages 참조).
class _CardPhoto extends StatelessWidget {
  const _CardPhoto({required this.listing});

  final ListingCardData listing;

  @override
  Widget build(BuildContext context) {
    final url = listing.imageUrl;
    // 계약-외 값 정규화(conventions.md §4): 음수 count는 0으로 하한 처리(장수는 계약-검증을
    // 통과한 행 수 기준이다 — listings_repository.dart의 pickCoverImages 참조).
    final rawCount = listing.imageCount ?? 0;
    final count = rawCount < 0 ? 0 : rawCount;

    return AspectRatio(
      aspectRatio: _cardPhotoAspectRatio,
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (url == null || url.isEmpty)
            const PhotoPlaceholder()
          else
            LayoutBuilder(
              builder: (context, constraints) {
                // 표시 크기로 디코드해 메모리 사용을 실제 셀 크기에 맞춘다(원본 대신 셀 픽셀
                // 크기로 디코드 — 목록의 카드 수만큼 원본 전체를 메모리에 올리지 않는다).
                final width =
                    constraints.maxWidth * MediaQuery.devicePixelRatioOf(context);
                final cacheWidth = width.isFinite && width > 0 ? width.round() : null;
                return Image.network(
                  url,
                  fit: BoxFit.cover,
                  cacheWidth: cacheWidth,
                  errorBuilder: (context, error, stackTrace) {
                    // 사진은 부가정보 — 로드 실패를 "판매자가 사진을 안 올림"과 구분해 남긴다.
                    debugPrint('매물 카드 사진 로드 실패($url): $error');
                    return const PhotoPlaceholder();
                  },
                );
              },
            ),
          if (count >= 1)
            Positioned(bottom: 8, right: 8, child: PhotoCountBadge(text: '$count장')),
        ],
      ),
    );
  }
}
