// 신뢰속성 판정 + 렌더 위젯 (Story 16.3) — web TrustAttributes.tsx의 Flutter 미러.
//
// 판정 순수함수(getTrustBadges)는 web getTrustBadges와 동일 규칙:
//   accident_status가 {'무사고','단순교환','사고'} 밖(빈 문자열 포함)이면 null과 동일 취급(미표시).
//   '무사고'만 초록, 나머지 2값은 중립(amber 금지). is_single_owner/is_non_smoker는 true일 때만
//   초록 칩 — null·false는 "아님"으로 단정하지 않고 미표시(docs/conventions.md §4 계약-외 값 정규화).
//
// 면책-뱃지 결속(B9, 상세 한정): TrustAttributesDetailSection은 뱃지가 하나라도 있으면 반드시
// 면책 문구를 같은 위젯 안에서 함께 반환한다 — 호출부(listing_detail_screen.dart)가 뱃지만
// 뽑아 쓰고 면책을 빼는 경로가 코드상 없다(web TrustAttributes.tsx 상단 주석과 동일 원칙).
// 카드는 이 결속 대상이 아니다(웹 2026-08-05 결정 — 사진 위 좁은 오버레이 공간이라 면책 제외).
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

enum TrustTone { green, neutral }

class TrustBadge {
  const TrustBadge({required this.key, required this.label, required this.tone});
  final String key;
  final String label;
  final TrustTone tone;
}

/// accident_status 계약-외 값 정규화(conventions §4): 3값 밖(빈 문자열 포함)이면 null과 동일.
const _validAccidentStatuses = {'무사고', '단순교환', '사고'};

const trustDisclaimer =
    '판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요.'; // UX-DR19

/// 표시할 뱃지 목록을 계산하는 순수함수(web getTrustBadges 미러). `@visibleForTesting`:
/// 테스트가 I/O 매트릭스 6행을 이 함수만으로 직접 단언할 수 있게 노출한다.
@visibleForTesting
List<TrustBadge> getTrustBadges({
  String? accidentStatus,
  bool? isSingleOwner,
  bool? isNonSmoker,
}) {
  final badges = <TrustBadge>[];

  if (accidentStatus != null && _validAccidentStatuses.contains(accidentStatus)) {
    badges.add(
      accidentStatus == '무사고'
          ? const TrustBadge(key: 'accident', label: '무사고', tone: TrustTone.green)
          : TrustBadge(key: 'accident', label: accidentStatus, tone: TrustTone.neutral),
    );
  }
  if (isSingleOwner == true) {
    badges.add(const TrustBadge(key: 'single-owner', label: '1인소유', tone: TrustTone.green));
  }
  if (isNonSmoker == true) {
    badges.add(const TrustBadge(key: 'non-smoker', label: '비흡연', tone: TrustTone.green));
  }
  return badges;
}

/// 뱃지 하나 — 톤별 배경(초록/중립). 초록은 비색 신호 중복(접근성)으로 ✓ 아이콘도 함께 표시.
class _TrustChip extends StatelessWidget {
  const _TrustChip({required this.badge, required this.onCard});

  final TrustBadge badge;
  // card=사진 위 겹침(반투명 배경), detail=문서 흐름 안(불투명 디자인 토큰) — web badgeClassName variant 미러.
  final bool onCard;

  @override
  Widget build(BuildContext context) {
    final green = badge.tone == TrustTone.green;
    final Color bg;
    final Color fg;
    if (onCard) {
      // 사진 위 오버레이 — 테마 토큰 대신 고정 반투명 hex(web과 동일 이유: 사진은 테마를
      // 따라 바뀌지 않으므로 trust-green 토큰을 배경으로 쓰면 다크 대비가 무너진다).
      bg = green ? const Color(0x731B6E3D) : const Color(0x59000000); // 45%/35%
      fg = Colors.white;
    } else {
      bg = green ? AppColors.trustGreenBg : Colors.transparent;
      fg = green ? AppColors.trustGreenInk : AppColors.inkSecondary;
    }
    final chipRadius = BorderRadius.circular(11);
    final content = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: chipRadius,
        border: (!onCard && !green) ? Border.all(color: AppColors.borderHairline) : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (green) ...[
            Icon(Icons.check, size: 12, color: fg),
            const SizedBox(width: 2),
          ],
          Text(
            badge.label,
            style: TextStyle(
              color: fg,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              // 카드 오버레이 전용 텍스트 그림자 — 반투명 배경(45%/35%)만으로는 밝은 사진 위에서
              // 대비가 약해질 수 있어, 웹이 "최저선"으로 못박은 그림자를 유지한다(spec-16-3,
              // web badgeClassName('card') text-shadow 미러). 상세(불투명 배경)는 불필요.
              shadows: onCard
                  ? const [
                      Shadow(offset: Offset(0, 1), blurRadius: 2, color: Color(0x8C000000)),
                    ]
                  : null,
            ),
          ),
        ],
      ),
    );
    if (!onCard) return content;
    // 카드 오버레이는 "반투명 배경+블러"다(spec-16-3 Boundaries, web backdrop-blur 미러) —
    // 사진 위에 겹치므로 배경색만으로는 사진이 그대로 비쳐 보여 글자 대비가 약하다.
    // ClipRRect로 칩 모양 밖으로 블러가 새지 않게 가둔다(다른 칩·주변 사진까지 흐려지면 안 됨).
    return ClipRRect(
      borderRadius: chipRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 6, sigmaY: 6),
        child: content,
      ),
    );
  }
}

/// 카드용 — 사진 좌상단에 겹치는 뱃지 콘텐츠, 면책 없음(웹 2026-08-05 결정). 뱃지가 0개면
/// 아무것도 그리지 않는다(값 유무와 무관하게 카드 높이가 항상 같게, AC1). `PhotoCountBadge`와
/// 같은 구조 원칙(listing_photo_widgets.dart) — 이 위젯 자체는 위치를 정하지 않는다(build()가
/// 직접 Positioned를 반환하면 Stack 밖에서 쓸 때 런타임에 죽는다, listing_photo_widgets.dart의
/// PhotoCountBadge 주석과 동일 근거). 호출부(`listing_card.dart`)가
/// `Positioned(... child: IgnorePointer(child: TrustAttributesCardOverlay(...)))`로 감싼다 —
/// IgnorePointer는 사진 위 오버레이가 카드 탭(InkWell)을 가로채지 않게 한다(코드리뷰 지적:
/// 뱃지 라벨을 탭해도 상세로 안 들어가던 문제, web `pointer-events-none` 미러).
class TrustAttributesCardOverlay extends StatelessWidget {
  const TrustAttributesCardOverlay({
    super.key,
    required this.accidentStatus,
    required this.isSingleOwner,
    required this.isNonSmoker,
  });

  final String? accidentStatus;
  final bool? isSingleOwner;
  final bool? isNonSmoker;

  @override
  Widget build(BuildContext context) {
    final badges = getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
    );
    if (badges.isEmpty) return const SizedBox.shrink();
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [for (final b in badges) _TrustChip(badge: b, onCard: true)],
    );
  }
}

/// 상세용 — 뱃지 행 + 면책을 한 위젯이 같이 반환한다(B9 결속의 실제 자리). 뱃지 0개면 섹션
/// 자체가 없다(AC3, 자체 여백도 포함하지 않아 빈 슬롯이 남지 않는다).
class TrustAttributesDetailSection extends StatelessWidget {
  const TrustAttributesDetailSection({
    super.key,
    required this.accidentStatus,
    required this.isSingleOwner,
    required this.isNonSmoker,
  });

  final String? accidentStatus;
  final bool? isSingleOwner;
  final bool? isNonSmoker;

  @override
  Widget build(BuildContext context) {
    final badges = getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
    );
    if (badges.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [for (final b in badges) _TrustChip(badge: b, onCard: false)],
          ),
          const SizedBox(height: 8),
          const Text(
            trustDisclaimer,
            style: TextStyle(color: AppColors.inkMuted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
