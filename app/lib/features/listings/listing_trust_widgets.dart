// 신뢰속성 판정 + 렌더 위젯 (Story 16.3, spec-16-9로 카드 배치 교정) — web TrustAttributes.tsx의
// Flutter 미러.
//
// 판정 순수함수(getTrustBadges)는 web getTrustBadges와 동일 규칙:
//   accident_status가 {'무사고','단순교환','사고'} 밖(빈 문자열 포함)이면 null과 동일 취급(미표시).
//   '무사고'만 초록, 나머지 2값은 중립(amber 금지). is_single_owner/is_non_smoker는 true일 때만
//   초록 칩 — null·false는 "아님"으로 단정하지 않고 미표시(docs/conventions.md §4 계약-외 값 정규화).
//
// 면책-뱃지 결속(B9): TrustAttributesDetailSection·TrustAttributesCardRow 둘 다 뱃지가
// 하나라도 있으면 면책을 같은 위젯 안에서 함께 반환한다 — 호출부(listing_detail_screen.dart·
// listing_card.dart)가 뱃지만 뽑아 쓰고 면책을 빼는 경로가 코드상 없다(web TrustAttributes.tsx
// 상단 주석과 동일 원칙). ⚠️ 2026-08-09(spec-16-9, DW-760 해소) — 예전엔 카드가 이 결속 대상이
// 아니었다(사진 위 좁은 오버레이라 면책 제외, 웹 2026-08-05 결정). 이제 카드가 사진 오버레이가
// 아니라 사진 **아래 전용 행**(DESIGN.md 레이아웃 B)이 되면서 그 좁은 공간 제약이 사라졌고,
// 스파인이 짧은 "판매자 제공 정보" 면책을 명시해 카드도 이 결속에 들어온다(상세의 긴 UX-DR19
// 문구와는 다른 축약판).
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
///
/// ✎ 2026-08-13 사용자 지시 — [positiveOnly]가 true면 **'사고'·'단순교환'을 뺀다.**
///   카드의 칩은 판매자가 내세우는 긍정 신호의 자리인데, 거기에 부정 상태가 같은 모양으로
///   섞이면 "뱃지가 붙어 있다 = 좋은 차"라는 읽기가 무너진다.
///   ⚠️ **정보를 없애는 게 아니라 자리를 옮기는 것이다** — 상세의 "신뢰정보" 블록
///   (TrustAttributesDetailSection)은 설명과 함께 여전히 다 보여주고, 기본정보 표의
///   `사고여부` 행도 그대로다. 숨기는 것은 맥락 없이 단어만 뜨는 카드 칩뿐이다.
@visibleForTesting
List<TrustBadge> getTrustBadges({
  String? accidentStatus,
  bool? isSingleOwner,
  bool? isNonSmoker,
  bool positiveOnly = false,
}) {
  final badges = <TrustBadge>[];

  if (accidentStatus != null && _validAccidentStatuses.contains(accidentStatus)) {
    if (accidentStatus == '무사고') {
      badges.add(const TrustBadge(key: 'accident', label: '무사고', tone: TrustTone.green));
    } else if (!positiveOnly) {
      badges.add(TrustBadge(key: 'accident', label: accidentStatus, tone: TrustTone.neutral));
    }
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
/// ⚠️ spec-16-9(DW-760 해소) — 예전엔 카드(사진 위 겹침, 반투명+블러)와 상세(문서 흐름 안,
/// 불투명)가 서로 다른 스타일을 썼다(`onCard` 분기). 카드가 더 이상 사진 위 오버레이가 아니라
/// 사진 아래 전용 행이 되면서(TrustAttributesCardRow) 두 자리 모두 같은 불투명 스타일을
/// 쓰게 됐다 — 이제 아무도 참조하지 않는 반투명+블러 분기(과 그 전용 `dart:ui` 의존)는
/// 이 변경이 만든 고아라 함께 제거한다(A3).
class _TrustChip extends StatelessWidget {
  const _TrustChip({required this.badge});

  final TrustBadge badge;

  @override
  Widget build(BuildContext context) {
    final green = badge.tone == TrustTone.green;
    final bg = green ? AppColors.trustGreenBg : Colors.transparent;
    final fg = green ? AppColors.trustGreenInk : AppColors.inkSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(11),
        border: !green ? Border.all(color: AppColors.borderHairline) : null,
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
            style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

/// 카드용 — 사진 바로 아래 전용 행(오버레이 아님, spec-16-9 DW-760 해소). `TrustAttributesCardOverlay`
/// (구 버전, 사진 좌상단 겹침)를 대체한다 — DESIGN.md 레이아웃 B가 신뢰속성을 "사진 바로 아래"
/// 일반 블록으로 요구하고, 짧은 면책("판매자 제공 정보")까지 포함하도록 명시한다(상세의 긴
/// UX-DR19 문구와 다른 축약판 — B9 결속은 지키되 카드는 좁은 자리라 문구만 줄인다).
/// 뱃지가 0개면 아무것도(면책도) 그리지 않는다(값 유무와 무관하게 카드 높이가 항상 같게, AC).
/// ⚠️ 코드리뷰 패치(spec-16-9) — 뱃지 3개(무사고·1인소유·비흡연)가 다 있으면 찜 버튼 여백(52px)
/// 때문에 좁아진 1열 카드에서 `Wrap`이 2줄로 접힐 수 있었다. D5가 "신뢰속성 행"을 명시적으로
/// 지목한 금기(가로 배치를 세로로 접지 않는다)라, 옵션 칩 행(`_OptionChipsRow`)과 같은 기법으로
/// 가로 스크롤로 바꿨다 — 넘치면 잘리기만 하고 2줄로 안 밀린다.
class TrustAttributesCardRow extends StatelessWidget {
  const TrustAttributesCardRow({
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
    // positiveOnly — 카드 칩은 긍정 신호만(2026-08-13 사용자 지시, getTrustBadges 주석 참조).
    final badges = getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
      positiveOnly: true,
    );
    if (badges.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (var i = 0; i < badges.length; i++) ...[
                  if (i > 0) const SizedBox(width: 6),
                  _TrustChip(badge: badges[i]),
                ],
              ],
            ),
          ),
          const SizedBox(height: 3),
          const Text(
            '판매자 제공 정보',
            style: TextStyle(color: AppColors.inkMuted, fontSize: 11),
          ),
        ],
      ),
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
            children: [for (final b in badges) _TrustChip(badge: b)],
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
