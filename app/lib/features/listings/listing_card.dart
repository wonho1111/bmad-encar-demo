// 매물 카드 위젯 — 탐색 목록·AI 검색 결과·홈 미리보기가 공유한다(web ListingCard 의 Flutter 판).
// 사진 5:3 대표 + "N장" 배지(Story 16.2, web ListingCardImage.tsx 미러) +
// 정보 영역(사진 → 신뢰속성 행 → 차량명 → meta → 가격 → 옵션 칩, spec-16-9 DW-760 해소 —
// DESIGN.md 레이아웃 B를 따른다. 이 스토리에 한해 정본은 web 코드가 아니라 스파인/목업이다,
// spec-16-9 Design Notes).
// 디자인: 웹 DESIGN.md 라이트 팔레트(Story 16.1) — 흰 카드 + border-hairline, 가격이 카드에서
// 가장 큰 텍스트(26px/800/priceEmphasis).
//
// 신뢰속성 행·찜 버튼·옵션 칩(Story 16.3·16.9). 찜 버튼은 web `top-full mt-1`을 그대로 미러해
// 사진 "아래"(경계에 걸치지 않고 완전히 밖)에 건다 — 실측(코드리뷰): 사진 경계에 절반 겹치던
// 이전 배치는 사진 우하단 "N장" 배지와 겹쳤다(P1). 그 결과 버튼은 카드 안(정보 영역 위)에
// 온전히 들어오므로 카드 자체의 clip은 다시 켠다(P2 — "카드를 자르면 안 된다"던 이전 전제는
// 실측상 거짓이었다). 사진 위쪽 모서리만 별도 `ClipRRect`로 둥글게 유지한다. 정보 영역의 맨
// 위 두 줄(신뢰속성 행·차량명)에 우측 여백을 주는 이유도 동일 — 찜 버튼이 사진 바로 아래
// 그 구간에 걸쳐 있다.
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import '../wishlist/wish_button.dart';
import 'listing.dart';
import 'listing_photo_widgets.dart';
import 'listing_trust_widgets.dart';
import 'options.dart';

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
                            // 신뢰속성 행 — 사진 바로 아래 전용 행(오버레이 아님, spec-16-9
                            // DW-760 해소). 우측 여백은 찜 버튼이 사진 바로 아래에서 이 줄까지
                            // 겹치는 구간(P1) 확보용(web pr-14 미러) — 값이 없으면 이 행 자체가
                            // 0높이라 이 Padding도 사실상 없는 것과 같다.
                            Padding(
                              padding: const EdgeInsets.only(right: 52),
                              child: TrustAttributesCardRow(
                                accidentStatus: listing.accidentStatus,
                                isSingleOwner: listing.isSingleOwner,
                                isNonSmoker: listing.isNonSmoker,
                              ),
                            ),
                            // 제조사·모델·연식 — 한 줄 요약. 우측 여백은 위와 같은 이유(찜 버튼
                            // 겹침 구간, 신뢰속성 행이 없을 때는 이 줄이 그 구간의 첫 줄이 된다).
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
                            const SizedBox(height: 4),
                            // meta 한 줄 — 주행·연료·지역·판매자를 합친다(spec-16-9 DW-760 해소:
                            // 예전엔 판매자가 별도 줄이었다). web ListingCard.tsx meta 줄과 같은
                            // 모양(대장 #67) — 값이 없으면 그 마디만 생략한다. 한 줄 가로 유지
                            // (D5) — 넘치면 줄바꿈이 아니라 ellipsis로 자른다. 우측 여백은 위
                            // 두 줄과 같은 이유(찜 버튼 겹침 구간, 코드리뷰 지적 P1) — 신뢰속성이
                            // 없으면(SizedBox.shrink) 이 줄이 그 구간의 첫 줄이 되므로 여기도
                            // 빠지면 안 된다.
                            Padding(
                              padding: const EdgeInsets.only(right: 52),
                              child: Text(
                                <String?>[
                                  kmText(listing.mileage),
                                  listing.fuel,
                                  listing.region,
                                  if (listing.sellerName != null &&
                                      listing.sellerName!.isNotEmpty)
                                    '판매자 ${listing.sellerName}',
                                ].where((s) => s != null && s.isNotEmpty).join(' · '),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5),
                              ),
                            ),
                            const SizedBox(height: 6),
                            // 가격 — 카드에서 가장 큰 텍스트(spec-16-9 DW-760 해소: 예전엔 15px/
                            // inkPrimary로 차량명과 거의 같은 무게였다). DESIGN.md typography.scale
                            // "price"(26/800) + priceEmphasis(이미 있는 토큰, 새 토큰 불필요).
                            Text(
                              wonText(listing.price),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 26,
                                  color: AppColors.priceEmphasis),
                            ),
                            const SizedBox(height: 8),
                            // 희소옵션 칩 — topOptions 우선순위 상위 3개 + 오버플로, 0개여도
                            // 플레이스홀더로 슬롯을 예약한다(spec-16-9 DW-760 해소: 예전엔 옵션
                            // 칩 자체가 없었다).
                            _OptionChipsRow(options: listing.options),
                          ],
                        ),
                      ),
                    ],
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

/// 희소옵션 칩 행(spec-16-9 DW-760 해소) — `options.dart`의 `topOptions`가 유일한 선택 로직
/// 출처다. 옵션이 0개여도 플레이스홀더 칩으로 슬롯을 예약해 카드 높이를 고정한다(AC) — 항상
/// 정확히 한 줄이 그려지므로 옵션 유무와 무관하게 이 행의 높이가 같다. D5(가로 배치를 세로로
/// 접지 않는다) 원칙에 따라 넘치면 줄바꿈 대신 가로 스크롤로 흡수한다(히어로 제안칩·차종 칩과
/// 같은 기법, home_screen.dart 참조).
class _OptionChipsRow extends StatelessWidget {
  const _OptionChipsRow({required this.options});

  final List<String>? options;

  @override
  Widget build(BuildContext context) {
    // 코드리뷰 패치(spec-16-9) — 값을 trim해 정규화한다(빈 문자열 필터링뿐 아니라 값 자체도
    // 정규화). trim만 필터 조건으로 쓰고 원본을 그대로 남기면(예: ' 선루프') optionPriority()의
    // 통제어휘 조회가 실패해 최하위 티어로 강등되고, 앞뒤 공백 유무만 다른 같은 옵션이 서로
    // 다른 문자열로 남아 dedup을 피해 칩이 두 번 뜬다.
    final all = (options ?? const <String>[])
        .map((o) => o.trim())
        .where((o) => o.isNotEmpty)
        .toList(growable: false);
    if (all.isEmpty) {
      return const SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: _OptionChip(label: '등록된 옵션 없음', muted: true),
      );
    }
    final top = topOptions(all, cardOptionCount);
    final overflowCount = all.toSet().length - top.length;
    // 코드리뷰 패치(spec-16-9 P5) — "외 N개"가 가로 스크롤 Row의 마지막 자식이면, 옵션
    // 라벨이 길 때(예: 파노라마글래스루프·헤드업디스플레이·어댑티브크루즈) 칩들이 카드 폭을
    // 넘겨 이 칩이 오른쪽 화면 밖으로 밀려난다 — 사용자가 옆으로 끌지 않으면 "옵션이 더
    // 있다"는 신호가 아예 안 보여 "옵션이 딱 이만큼뿐"으로 잘못 읽힌다(개수 표시는 스크롤
    // 대상이면 안 된다). 그래서 스크롤 영역(top 칩들)만 Expanded로 감싸 넘치는 만큼 자체적으로
    // 잘리게 하고, 오버플로 칩은 그 바깥 Row 끝에 고정해 항상 보이게 한다.
    return Row(
      children: [
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (var i = 0; i < top.length; i++) ...[
                  if (i > 0) const SizedBox(width: 6),
                  _OptionChip(label: top[i]),
                ],
              ],
            ),
          ),
        ),
        if (overflowCount > 0) ...[
          const SizedBox(width: 6),
          _OptionChip(label: '외 $overflowCount개', muted: true),
        ],
      ],
    );
  }
}

/// 옵션 칩 하나 — petrol 아웃라인(테두리만 petrol, 배경은 채우지 않음, DESIGN.md §L128 산문
/// 우선 — spec-16-9 Design Notes: 목업 CSS의 배경-채움은 낡은 해석이다). `muted`(오버플로 "외
/// N개" 칩·옵션 0개 플레이스홀더 칩)만 회색 아웃라인(`borderHairline`/`inkMuted`)으로 구분한다
/// — 코드리뷰 패치: 플레이스홀더가 실제 옵션 칩과 같은 petrol 강조 스타일이면 "값이 없다"는
/// 상태가 마치 강조된 셀링포인트처럼 보인다(웹의 `border-transparent`+`text-ink-muted` 관례와도
/// 일치하도록 통일).
class _OptionChip extends StatelessWidget {
  const _OptionChip({required this.label, this.muted = false});

  final String label;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9), // DESIGN.md rounded.chip
        border: Border.all(
          color: muted ? AppColors.borderHairline : AppColors.brandPetrol,
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: muted ? AppColors.inkMuted : AppColors.brandPetrol,
        ),
      ),
    );
  }
}
