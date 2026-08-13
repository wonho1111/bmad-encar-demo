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
  const TrustBadge({
    required this.key,
    required this.label,
    required this.tone,
    required this.description,
  });
  final String key;
  final String label;
  final TrustTone tone;

  /// 상세 "신뢰정보" 블록에서 라벨 밑에 붙는 한 줄 설명(web TrustAttributes.tsx의 `description`
  /// 원문 그대로). **전부 "판매자가 신고했다" 형태로 쓴다**(CM-C: 우리가 검증했다고 오도 금지).
  /// 이 문장이 있어야 그 블록이 요약의 같은 칩을 그냥 반복하는 게 아니게 된다(2026-08-13 웹에서
  /// 같은 이유로 추가됨 — 모바일에선 요약이 그 블록 바로 위로 내려와 중복이 눈에 띈다).
  final String description;
}

/// accident_status 계약-외 값 정규화(conventions §4): 3값 밖(빈 문자열 포함)이면 null과 동일.
const _validAccidentStatuses = {'무사고', '단순교환', '사고'};

const trustDisclaimer =
    '판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요.'; // UX-DR19

/// 상세 **요약 블록**용 짧은 면책 — web TrustAttributes.tsx의 `DISCLAIMER_SUMMARY` 원문
/// (목업 detail-1.html `.trust-disclaimer-sm`). 같은 화면 아래 신뢰정보 블록이 위 긴 문구를
/// 그대로 다시 보여주므로, 제목·가격 사이의 좁은 자리에서는 한 줄짜리를 쓴다.
const trustDisclaimerSummary = '판매자 제공 정보 · 차장님이 검증한 정보가 아닙니다';

/// 신뢰속성이 하나도 없을 때 상세 "신뢰정보" 섹션이 보여줄 안내 — web TrustInfoSection의
/// 같은 문구. **"없음"은 이제 한 가지 뜻뿐이다**(판매자가 입력하지 않았다) — 2026-08-13의
/// 마이그레이션 0037이 비로그인에게도 같은 3컬럼을 열어, 로그인 여부로 갈리던 옛 분기가
/// 사라졌다.
const trustEmptyMessage = '판매자가 무사고·1인소유·비흡연 여부를 입력하지 않았어요. 계약 전 직접 확인하세요.';

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
      badges.add(const TrustBadge(
        key: 'accident',
        label: '무사고',
        tone: TrustTone.green,
        description: '성능점검 기준으로 사고 이력이 없다고 판매자가 신고했습니다.',
      ));
    } else if (!positiveOnly) {
      badges.add(TrustBadge(
        key: 'accident',
        label: accidentStatus,
        tone: TrustTone.neutral,
        description: accidentStatus == '단순교환'
            ? '사고는 없고 단순 교환 이력만 있다고 판매자가 신고했습니다.'
            : '사고 이력이 있다고 판매자가 신고했습니다.',
      ));
    }
  }
  if (isSingleOwner == true) {
    badges.add(const TrustBadge(
      key: 'single-owner',
      label: '1인소유',
      tone: TrustTone.green,
      description: '등록 이후 소유주 변경 없이 한 명이 계속 소유했다고 신고했습니다.',
    ));
  }
  if (isNonSmoker == true) {
    badges.add(const TrustBadge(
      key: 'non-smoker',
      label: '비흡연',
      tone: TrustTone.green,
      description: '차량 내 흡연 이력이 없다고 판매자가 신고했습니다.',
    ));
  }
  return badges;
}

/// "그릴 게 있는가"만 묻는 호출부용(web `hasTrustAttributes` 미러) — 상세 "신뢰정보" 섹션이
/// 뱃지 분기와 "입력하지 않았어요" 안내 분기를 고르는 데 쓴다. 판정 규칙을 두 번 쓰지 않도록
/// 위 `getTrustBadges` 결과를 그대로 센다.
bool hasTrustAttributes({
  String? accidentStatus,
  bool? isSingleOwner,
  bool? isNonSmoker,
}) =>
    getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
    ).isNotEmpty;

/// 뱃지 하나 — 톤별 배경(초록/중립). 초록은 비색 신호 중복(접근성)으로 ✓ 아이콘도 함께 표시.
/// ⚠️ spec-16-9(DW-760 해소) — 예전엔 카드(사진 위 겹침, 반투명+블러)와 상세(문서 흐름 안,
/// 불투명)가 서로 다른 스타일을 썼다(`onCard` 분기). 카드가 더 이상 사진 위 오버레이가 아니라
/// 사진 아래 전용 행이 되면서(TrustAttributesCardRow) 두 자리 모두 같은 불투명 스타일을
/// 쓰게 됐다 — 이제 아무도 참조하지 않는 반투명+블러 분기(과 그 전용 `dart:ui` 의존)는
/// 이 변경이 만든 고아라 함께 제거한다(A3).
class _TrustChip extends StatelessWidget {
  const _TrustChip({required this.badge, this.onPhoto = false});

  final TrustBadge badge;

  /// 사진 위에 얹히는가(카드 오버레이). 색은 그대로 두고 **그림자만** 더한다 — 밝은 사진
  /// 위에서 옅은 초록 칩의 경계가 묻히지 않게 하는 최소 처치다(배경색을 사진용으로 따로
  /// 만들면 카드와 상세의 칩이 또 갈린다).
  final bool onPhoto;

  @override
  Widget build(BuildContext context) {
    final green = badge.tone == TrustTone.green;
    final bg = green ? AppColors.trustGreenBg : Colors.transparent;
    final fg = green ? AppColors.trustGreenInk : AppColors.inkSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        // 중립 칩은 배경이 투명이라 사진 위에서는 글자만 뜬다 — 오버레이에서는 흰 면을 깔아
        // 최소 대비를 지킨다(상세·문서 흐름 안에서는 지금까지처럼 투명 + 헤어라인 테두리).
        color: onPhoto && !green ? AppColors.surfaceRaised : bg,
        borderRadius: BorderRadius.circular(11),
        border: !green ? Border.all(color: AppColors.borderHairline) : null,
        boxShadow: onPhoto
            ? const [BoxShadow(color: Color(0x24000000), blurRadius: 6, offset: Offset(0, 1))]
            : null,
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

/// 카드용 — **사진 위 좌상단에 겹치는 칩 묶음**(web `TrustAttributes variant='card'` 미러).
///
/// ✎ 2026-08-13 사용자 지적 #4("신뢰속성 태그 위치가 웹과 다르다") — 자리를 웹으로 되돌렸다.
///   경위: 웹은 처음부터 사진 위 오버레이(2026-08-05 사용자 승인)인데, 앱은 spec-16-9가
///   DESIGN.md "레이아웃 B"(신뢰속성 = 사진 **아래** 일반 블록 + 짧은 면책)를 따르면서 갈렸다.
///   그때는 스파인이 정본이라는 판단이었지만, 이번엔 사용자가 두 화면을 나란히 보고 웹 쪽으로
///   통일하라고 정했다 — **스파인과 충돌하는 결정이므로 여기 남긴다**(되돌릴 땐 이 문단을 보고
///   웹도 함께 바꿀 것).
///   ⚠️ 함께 사라진 것: 카드의 짧은 면책 "판매자 제공 정보". 웹 카드에도 없다 — 사진 위 좁은
///   자리에 면책 한 줄까지 얹으면 뱃지·사진 둘 다 읽기 어려워진다는 같은 이유다(웹
///   TrustAttributes.tsx 상단 주석). 면책은 상세의 신뢰정보 블록이 속성별 설명과 함께 그대로
///   진다(TrustAttributesDetailSection) — B9 결속은 **상세 한정**으로 좁아진다.
///
/// 배경은 웹처럼 반투명+블러로 하지 않고 기존 불투명 칩 스타일을 그대로 쓴다(A2) — 블러는
/// 카드마다 `BackdropFilter`가 붙어 목록 스크롤 비용이 커지는데, 불투명 칩은 어떤 사진 위에서도
/// 대비가 무너지지 않는다. 사진 위에서 칩이 떠 보이도록 옅은 그림자만 얹는다.
/// 뱃지가 0개면 아무것도 그리지 않는다(사진만 남는다).
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
    // positiveOnly — 카드 칩은 긍정 신호만(2026-08-13 사용자 지시, getTrustBadges 주석 참조).
    final badges = getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
      positiveOnly: true,
    );
    if (badges.isEmpty) return const SizedBox.shrink();
    // IgnorePointer — 이 칩들은 사진 위에 떠 있을 뿐 눌리는 대상이 아니다. 안 감싸면 칩이
    // 덮은 만큼 카드 탭(상세로 이동)이 죽는다(web의 `pointer-events-none`과 같은 이유).
    return IgnorePointer(
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [for (final b in badges) _TrustChip(badge: b, onPhoto: true)],
      ),
    );
  }
}

/// 상세 **요약 블록**용 — 칩 한 줄 + 짧은 면책(web `variant='summary'` 미러, 2026-08-13 지적 #4).
/// 제목·가격 사이에 놓여 "스크롤 없이 판단"을 돕는 자리라 긴 면책 대신 한 줄짜리를 쓴다.
/// 문구가 짧아졌을 뿐 **뱃지엔 면책이 딸려 나온다**는 결속은 그대로다(B9) — 긴 면책은 아래
/// 신뢰정보 블록(TrustAttributesDetailSection)이 그대로 진다.
class TrustAttributesSummaryRow extends StatelessWidget {
  const TrustAttributesSummaryRow({
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
    // positiveOnly — 요약 칩도 카드와 같이 긍정 신호만(2026-08-13 사용자 지시). 사고·단순교환은
    // 바로 아래 신뢰정보 블록이 설명과 함께 보여준다.
    final badges = getTrustBadges(
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
      positiveOnly: true,
    );
    if (badges.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [for (final b in badges) _TrustChip(badge: b)],
          ),
          const SizedBox(height: 6),
          const Text(
            trustDisclaimerSummary,
            style: TextStyle(color: AppColors.inkMuted, fontSize: 11.5),
          ),
        ],
      ),
    );
  }
}

/// 상세 "신뢰정보" 블록 — 속성마다 **칩 + 무슨 뜻인지 한 줄**을 쌓고 그 아래 긴 면책(B9 결속의
/// 실제 자리). 뱃지 0개면 아무것도 그리지 않는다(그 경우의 안내 문구는 이 위젯을 담는 섹션이
/// 대신 그린다 — listing_detail_screen.dart).
///
/// ✎ 2026-08-13 — 예전엔 칩 한 줄 + 면책이었다. 그러면 같은 화면 위쪽 요약 블록의 칩과 **같은
///   것을 두 번** 보게 된다(웹이 같은 날 같은 이유로 설명 줄을 붙였다). 설명이 붙으면서 이
///   블록은 "그 뱃지가 정확히 무슨 뜻인가"를 답하는 다른 내용이 된다.
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final b in badges)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _TrustChip(badge: b),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    b.description,
                    style: const TextStyle(
                        color: AppColors.inkSecondary, fontSize: 12, height: 1.45),
                  ),
                ),
              ],
            ),
          ),
        const Divider(height: 1, color: AppColors.borderHairline),
        const SizedBox(height: 10),
        const Text(
          trustDisclaimer,
          style: TextStyle(color: AppColors.inkMuted, fontSize: 12, height: 1.45),
        ),
      ],
    );
  }
}
