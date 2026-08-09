// 인증 후 홈 — AI 히어로(①, 최상단, 전체폭 밴드) + 차종 칩(②) + "지금 인기"·
// "방금 올라온 매물" 2섹션(③, spec-16-8) — 웹 랜딩(Epic 11: HeroSearch·CategoryChips·
// PopularRecentGrid)의 정보구조 미러.
// nav-ia-rules §1·§2: 구매자/판매자 공통 홈(R1 상위집합), 1순위 과업=매물 탐색(R2).
// ⚠️ spec-16-9(DW-755 해소) — 히어로 바로 아래에 있던 별도 매물 탐색 CTA(`_SearchCta`,
//   `Key('go_search')`)를 제거했다. 그 목적지(SearchScreen 무필터 조회)는 차종 칩의 "전체"
//   (petrol 채움 정적 표시)가 대신한다 — 히어로 다음 위젯은 이제 차종 칩 줄이다.
//
// ⚠️ **AI 진입은 2026-08-07에 FAB → 홈 최상단 검색부로 옮겼다.** 원래는 nav-ia-rules R3
//   (*"Flutter에서는 FAB 또는 상시 탭으로"*)를 근거로 FAB였는데, 2026-07-12 UX 확정 D12가
//   그걸 **명시적으로 폐기**했다:
//     *"AI 검색 = FAB 아님. **홈 최상단 큰 검색부**(웹 히어로 딥 petrol 밴드의 앱 번역판).
//       'AI가 제품의 얼굴'이라는 위계를 웹·앱 1:1 대응. (이전 앱의 AI=FAB는 'AI가 부가기능'
//       이던 흔적 → 폐기.)"*
//   근거는 Material Design 안티패턴(검색을 단일 FAB에 넣는 것)과 P2P 관례(FAB=생성 액션)다.
//   같은 날 웹의 떠 있는 'AI 검색' 버튼도 같은 이유로 제거했다(`web/src/app/page.tsx`).
//
// ⚠️ **Story 16.1 반영**: D12의 나머지 절반인 하단 4탭(홈(AI)·찜·채팅·내차팔기)이 라우터 셸
//   (`core/router/app_router.dart`)에 생겼다. 그래서 이 화면은 더 이상 자체 AppBar를 갖지
//   않는다 — 상단 타이틀·우상단 프로필 아바타는 그 셸이 공통으로 제공한다(Scaffold에
//   appBar를 주지 않는 이유). 로그아웃 텍스트버튼·프로필 카드도 그 아바타 메뉴로 이관됐다.
//
// ⚠️ **Story 16.8 반영(DW-736 해소)**: 홈이 웹 Epic 11 정보구조(히어로+실입력+제안칩 →
//   차종 칩 줄 → "지금 인기"·"방금 올라온 매물" 2섹션)를 그대로 물려받는다. 하단 4탭과
//   목적지가 겹치던 Epic 7 잔재 퀵액션 3개(문의 채팅·매물 등록·내 매물 관리, 16.1이 미처
//   안 지운 옛 문)를 **같은 커밋에서** 제거했다 — 새 섹션 추가와 분리하면 그 사이 판매자가
//   매물 등록에 갈 길이 하단 탭뿐이라 막힌다(DW-728 선례와 같은 순서 원칙).
//
//   ⚠️ **셸 경계(spec-16-1 Code Map)**: 이 화면은 하단 4탭 셸의 '홈' 브랜치 루트다 —
//   `StatefulShellRoute`가 브랜치별 Navigator를 보존하므로, 이 화면에서 다른 화면으로
//   `Navigator.push`하면 그 push는 브랜치의 (셸에 감싸인) Navigator에 쌓인다. 셸이 이미
//   AppBar·NavigationBar를 그리고 있으므로, 상세류(AI 채팅·탐색·매물 상세)를 그 안에 쌓으면
//   AppBar가 2개, 하단 탭이 상세 위에 남는 레이아웃 결함이 생긴다(실측 확인, Spec Change Log
//   2026-08-07 #2). 그래서 아래 모든 push는 `rootNavigator: true`로 셸 밖(앱의 진짜 루트
//   Navigator)으로 보낸다.
// 관리자(admin)는 모바일 제외(AR9) → app_router.dart의 redirect가 차단 화면으로 보낸다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../ai_search/ai_chat_screen.dart';
import '../ai_search/chat_message.dart' show maxQueryLength;
import '../listings/listing_card.dart';
import '../listings/listing_detail_screen.dart';
import '../listings/listings_providers.dart';
import '../listings/search_screen.dart';
import '../wishlist/wishlist_providers.dart';

/// 당겨서 새로고침 한 항목을 독립적으로 감싼다 — 실패해도 절대 reject하지 않는다(호출부
/// `Future.wait`가 나머지 refresh·onRefresh 자체를 막지 않게, spec-16-8 Review Triage Log #2).
Future<void> _refreshQuietly(Future<Object?> Function() run) async {
  try {
    await run();
  } catch (e) {
    // 실패는 각 섹션 위젯(_PopularListings·_RecentListings)이 이미 AsyncValue.error로
    // 보여준다 — 여기서 다시 던지면 그 정보 없이 다른 refresh까지 함께 취소된다.
    // debugPrint는 남긴다(후속 코드리뷰 spec-16-8 2차 리뷰 P12) — 위에서 인용한 웹
    // fetchSection도 같은 자리에서 console.error를 남긴다. 여기서 조용히 삼키기만 하면 화면엔
    // 각 섹션 위젯의 AsyncValue.error로 남지만, "새로고침 자체가 실패했다"는 흔적은 로그에도
    // 안 남는다 — listings_repository.dart가 이미 쓰는 것과 같은 로깅 방식.
    debugPrint('홈 섹션 새로고침 실패: $e');
  }
}

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // appBar 없음(위 주석) — 셸의 Material 이 InkWell 등에 필요한 Material 조상 역할도
    // 겸하므로 Scaffold(body:) 만으로 충분하다.
    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          // 당겨서 새로고침 → "지금 인기"·"방금 올라온 매물" 둘 다 재조회(등록·판매완료 후
          // 수동 갱신 경로 — 두 섹션 모두 그 변화를 반영해야 한다). 각 refresh를
          // `_refreshQuietly`로 따로 감싼다 — Future.wait는 하나가 실패하면 즉시 reject하고
          // 나머지 하나의 실패는 아무도 catch하지 않는 관찰되지 않은 예외가 된다(코드리뷰
          // 발견, spec-16-8 Review Triage Log #2) — 웹 fetchSection이 지키는 "한 섹션 실패가
          // 다른 섹션·전체 화면을 안 죽인다" 원칙을 새로고침 경로에도 맞춘다. 실패 자체는 이미
          // 각 섹션 위젯이 AsyncValue.error로 보여주므로 여기선 조용히 삼킨다.
          onRefresh: () => Future.wait([
            _refreshQuietly(() => ref.refresh(recentListingsProvider.future)),
            _refreshQuietly(() => ref.refresh(popularListingsProvider.future)),
          ]),
          child: SingleChildScrollView(
            // 내용이 짧아도 당겨서 새로고침이 되도록 항상 스크롤 가능.
            physics: const AlwaysScrollableScrollPhysics(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // AI 히어로 — **홈 최상단**(D12), 화면 폭을 꽉 채우는 밴드(spec-16-9 DW-755
                // 해소, Always: 좌우 여백 0). 아래 Center+ConstrainedBox+Padding **바깥**에
                // 둬야 한다 — 그 안에 있으면 히어로도 480 컨텐츠 폭에 갇혀 양옆에 여백이
                // 남는다(예전 결함). "AI가 제품의 얼굴"이라는 위계를 위치로도 표현한다.
                // 제출(입력 전송·제안 칩 탭 공통)은 그 문장으로 AiChatScreen을 이미 조회를
                // 시작한 상태로 연다(spec-16-8 AC5, 직접 타이핑과 칩 탭이 같은 파이프라인).
                _AiSearchCta(
                  onSubmitQuery: (query) => Navigator.of(context, rootNavigator: true)
                      .push(MaterialPageRoute(
                          builder: (_) => AiChatScreen(initialQuery: query))),
                ),
                Padding(
                  // 하단 패딩: 시스템 내비바 가림 방지. `viewPadding.bottom`이 아니라
                  // `MediaQuery.paddingOf(context).bottom`을 쓴다 — 셸의 `NavigationBar`가
                  // 이미 그 시스템 인셋을 흡수해 Scaffold가 `padding`에서 걷어내므로,
                  // 원본 `viewPadding`을 또 더하면 하단 여백이 이중으로 커진다(spec-16-1 Task).
                  // 상단 패딩(16)이 히어로와 아래 콘텐츠 사이 간격을 겸한다 — _SearchCta 제거
                  // (spec-16-9 Always: 히어로 바로 다음 위젯은 차종 칩) 이후 이 패딩만으로 충분.
                  padding: EdgeInsets.fromLTRB(
                      16, 16, 16, 24 + MediaQuery.paddingOf(context).bottom),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 480),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // 차종 칩 줄(spec-16-8 AC2) — 웹 CategoryChips.tsx의 CATEGORY_CHIPS와
                          // 값·순서 바이트 일치. 탭하면 그 필터로 SearchScreen이 즉시 조회한다.
                          _CategoryChipsRow(
                            onTapChip: (chip) => Navigator.of(context, rootNavigator: true)
                                .push(
                              MaterialPageRoute(
                                builder: (_) => SearchScreen(
                                  initialBodyType: chip.bodyType,
                                  initialFuel: chip.fuel,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),

                          // "지금 인기" 섹션(spec-16-8 AC3) — popularListingsProvider(view_count
                          // desc 4건). 조회 실패는 이 섹션에만 격리된다(웹 fetchSection 미러).
                          _SectionHeader(
                            title: '지금 인기',
                            onMore: () => Navigator.of(context, rootNavigator: true).push(
                              MaterialPageRoute(builder: (_) => const SearchScreen()),
                            ),
                          ),
                          const SizedBox(height: 6),
                          const _PopularListings(),
                          const SizedBox(height: 20),

                          // "방금 올라온 매물" 섹션(구 "최근 매물" 헤더 개칭, recentListingsProvider
                          // 재사용) — created_at desc 4건.
                          _SectionHeader(
                            title: '방금 올라온 매물',
                            onMore: () => Navigator.of(context, rootNavigator: true).push(
                              MaterialPageRoute(builder: (_) => const SearchScreen()),
                            ),
                          ),
                          const SizedBox(height: 6),
                          const _RecentListings(),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 섹션 헤더 — 제목 + "전체보기 ›"(탐색 화면으로). "지금 인기"·"방금 올라온 매물" 두 섹션이
/// 공유한다(웹 PopularRecentGrid.tsx의 ListingGridSection과 같은 이유 — 마크업을 공유해야
/// 한쪽만 스타일이 갈리는 일이 없다).
class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.onMore});

  final String title;
  final VoidCallback onMore;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(title,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.w700)),
        const Spacer(),
        InkWell(
          onTap: onMore,
          child: const Padding(
            padding: EdgeInsets.all(4),
            child: Text('전체보기 ›',
                style: TextStyle(color: AppColors.inkMuted, fontSize: 13)),
          ),
        ),
      ],
    );
  }
}

/// 제안 칩 4종 — web HeroSearch.tsx의 SUGGESTIONS 그대로(spec-16-8 Always). 목업의 3개가
/// 아니라 웹의 4개를 쓴다(웹이 이미 안정 운영 중인 정본, Design Notes).
/// `@visibleForTesting`(후속 코드리뷰 spec-16-8 2차 리뷰 P5) — 이 리스트는 Dart 컴파일러의
/// 타입 검사를 받지 않는 자유 문자열이라, 오타가 나도 컴파일은 그대로 통과한다. 웹의
/// SUGGESTIONS와 값·순서가 바이트 일치해야 한다는 계약을 지키는 검사가 없었다 — 상수를
/// top-level로 꺼내 테스트가 직접 그 계약을 단언하게 한다.
@visibleForTesting
const List<String> heroSuggestions = [
  '가성비 좋은 첫차',
  '4천만원대 전기 SUV',
  '주행거리 짧은 무사고 세단',
  '7인승 디젤 패밀리카',
];

/// AI 히어로 — 웹 HeroSearch.tsx의 앱 번역판(D12, spec-16-8로 실 입력+제안칩까지 확장).
/// petrol 그라데이션(brand-petrol-strong → petrol-deepest, DESIGN.md AI 히어로 밴드 규칙)으로
/// "AI가 제품의 얼굴"이라는 위계를 나타낸다(D12).
/// ⚠️ spec-16-9(DW-755 해소) — 화면 폭을 꽉 채우는 밴드로 바뀌었다(좌우 여백 0, 아래 두 모서리만
/// 둥글게 — 위는 각져 홈 탭 AppBar와 맞닿는다). 배경에 amber/petrol 글로우 + 차 실루엣 라인아트도
/// 추가한다(spec-16-1 시절의 "재현하지 않는다"는 결정을 이 스토리가 뒤집는다 — Design Notes:
/// 정밀 아트가 아니라 존재 자체가 요구사항이라 RadialGradient+저투명도 Icon으로 충분하다).
/// amber는 검색 버튼 하나에만 쓴다(DESIGN.md "화면당 amber는 손에 꼽을 정도로") — amber 위
/// 글자는 규칙대로 어두운 잉크(`inkPrimary`), 흰색 금지.
class _AiSearchCta extends StatefulWidget {
  const _AiSearchCta({required this.onSubmitQuery});

  final ValueChanged<String> onSubmitQuery;

  @override
  State<_AiSearchCta> createState() => _AiSearchCtaState();
}

class _AiSearchCtaState extends State<_AiSearchCta> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit(String query, {bool fromChip = false}) {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;
    // 500자 상한 방어적 자르기(후속 코드리뷰 spec-16-8 2차 리뷰 P9, web HeroSearch.tsx의
    // `.slice(0, MAX_QUERY_LENGTH)`와 같은 이유) — 아래 TextField의 maxLength가 직접 타이핑
    // 경로는 이미 막지만, 제안 칩 탭은 입력창을 거치지 않고 문장을 바로 이 함수로 넘긴다.
    // 자르지 않으면 AiChatScreen._submit이 500자 초과를 거부하는데, 그 경로(overrideQuery)는
    // 입력을 복원하지 않고 이 화면은 이미 clear()해 원문이 통째로 사라진다(chat_message.dart의
    // maxQueryLength를 그대로 재사용 — 두 번째 500 상수를 새로 만들지 않는다).
    final truncated = trimmed.characters.length > maxQueryLength
        ? trimmed.characters.take(maxQueryLength).toString()
        : trimmed;
    widget.onSubmitQuery(truncated);
    // 제출 성공 후 입력을 비운다(코드리뷰 발견) — 안 비우면 AiChatScreen에서 뒤로가기로
    // 홈에 돌아왔을 때 방금 검색한 문장이 그대로 남아 있다. 단, 제안 칩 탭(fromChip)은
    // 예외다 — 칩 탭 전에 독립적으로 타이핑해 둔 초안이 있을 수 있고, 그건 칩 전송과
    // 무관하다(후속 코드리뷰 spec-16-8 발견). 이 예외는 이미 ai_chat_screen.dart._submit의
    // `if (overrideQuery == null) _input.clear();`(칩 탭이면 입력창을 안 건드림, 웹
    // HeroSearch.submit도 칩 클릭에서 query 상태를 안 건드림)로 한 단계 아래에서 이미 확정된
    // 결정이라, 이 히어로만 반대로 매번 지우면 그 결정과 어긋난다(ai_chat_screen_test.dart
    // '칩 탭으로 제출해도 입력창에 남아있던 사용자 초안 텍스트는 그대로 유지된다'가 그 결정을
    // 고정한다).
    if (!fromChip) _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      // go_ai — 이 히어로 밴드 전체(Container)에 붙은 존재·좌표 확인용 앵커일 뿐, 탭 대상이
      // 아니다(후속 코드리뷰 spec-16-8 2차 리뷰 P8). 실제 제출 진입점은 아래
      // hero_search_button(검색 버튼)·hero_suggestion_*(제안 칩)이다 — 이 Container 배경을
      // 눌러도 onTap이 없어 아무 반응이 없으므로 `tester.tap(find.byKey(Key('go_ai')))`를
      // 쓰는 테스트를 새로 만들지 않는다(조용히 아무 일도 안 하고 통과해 버린다).
      key: const Key('go_ai'),
      width: double.infinity,
      // 화면 폭을 꽉 채우는 밴드(spec-16-9 DW-755 해소, Always: 좌우 여백 0) — 좌우 패딩을
      // 없애고 위쪽은 각지게(홈 탭 AppBar와 맞닿음), 아래 두 모서리만 둥글게 한다.
      clipBehavior: Clip.hardEdge,
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(22),
          bottomRight: Radius.circular(22),
        ),
        // 코드리뷰 패치(spec-16-9 P1) — 축(begin/end)이 대각선(topLeft→bottomRight)이면 히어로
        // 상단 우측 모서리가 이미 petrolDeepest 쪽으로 상당히 이동해(390x220 밴드 기준 ~76%),
        // 홈 탭 AppBar(단색 brandPetrolStrong = 이 그라데이션의 시작색과만 같다)와 만나는 경계
        // 오른쪽 절반에서 색이 눈에 띄게 꺾인다(AC①: "AppBar와 같은 배경색으로 이어져 경계가
        // 안 보인다" 위반). topCenter→bottomCenter로 바꾸면 히어로의 윗변 전체가 시작색과
        // 같아져 AppBar와 만나는 가로선 전체가 이어진다 — 시작색만 맞추는 게 아니라 축 자체가
        // 이 이음매를 만든다는 점이 핵심이라, 나중에 리팩터가 "그냥 대각선이 예뻐서" 되돌리지
        // 않도록 여기 남긴다.
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [AppColors.brandPetrolStrong, AppColors.petrolDeepest],
        ),
      ),
      child: Stack(
        children: [
          // 배경 장식 — 우상단 amber/petrol 글로우 + 우측 차 실루엣 라인아트(spec-16-9 Always,
          // DW-755 해소). 정밀 벡터 재현이 아니라 "존재 자체"가 요구사항이라(Design Notes)
          // RadialGradient + 저투명도 Icon으로 충분하다. Stack의 먼저 오는 자식이라 아래 헤드라인·
          // 입력창·제안칩(뒤에 오는 Padding)에 항상 깔린다 — 침범하지 않는다.
          Positioned(
            top: -30,
            right: -30,
            child: Container(
              key: const Key('hero_glow'),
              width: 170,
              height: 170,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.accentAmber.withValues(alpha: 0.30),
                    AppColors.accentAmber.withValues(alpha: 0),
                  ],
                ),
              ),
            ),
          ),
          // 코드리뷰 패치(spec-16-9) — AC 문구("우상단")·목업(consistency-1.html `.silhouette`,
          // right:-8%·top:-14%)과 달리 우하단에 있었다. 우상단(글로우와 같은 모서리, 칩·검색창을
          // 침범하지 않는 자리)으로 옮긴다.
          Positioned(
            top: -6,
            right: -36,
            child: Icon(
              Icons.directions_car_filled,
              key: const Key('hero_car_silhouette'),
              size: 150,
              color: AppColors.onPetrol.withValues(alpha: 0.12),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 헤드라인 — "말"만 amber 강조(웹·목업 공통 마이크로카피, spec-16-8 AC1).
                RichText(
                  text: const TextSpan(
                    style: TextStyle(
                        color: AppColors.onPetrol, fontSize: 19, fontWeight: FontWeight.w800),
                    children: [
                      TextSpan(text: '원하는 차를 '),
                      TextSpan(text: '말', style: TextStyle(color: AppColors.accentAmber)),
                      TextSpan(text: '로 찾으세요'),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                // 실 입력 pill — 흰 배경 + amber 검색 버튼(spec-16-8 AC1).
                Container(
                  padding: const EdgeInsets.fromLTRB(14, 4, 4, 4),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceRaised,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          key: const Key('hero_query_input'),
                          controller: _controller,
                          // 500자 상한(후속 코드리뷰 spec-16-8 2차 리뷰 P9) — web HeroSearch.tsx의
                          // `maxLength={MAX_QUERY_LENGTH}`와 동일 방어. 타이핑 경로는 이 한 줄로
                          // 막히고, 제안 칩 경로는 위 _submit의 방어적 자르기가 대신 막는다.
                          maxLength: maxQueryLength,
                          decoration: const InputDecoration(
                            isDense: true,
                            border: InputBorder.none,
                            hintText: '예: 3천만원대 무사고 흰색 SUV',
                            // 시각적 알약 크기를 그대로 유지한다 — maxLength를 주면 Flutter가 기본
                            // 글자수 카운터를 그 아래에 그리는데, 이 좁은 pill 레이아웃은 그 자리를
                            // 계산하지 않았다(웹 HeroSearch.tsx에도 이 카운터가 없다).
                            counterText: '',
                          ),
                          onSubmitted: _submit,
                        ),
                      ),
                      FilledButton(
                        key: const Key('hero_search_button'),
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.accentAmber,
                          foregroundColor: AppColors.inkPrimary,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        onPressed: () => _submit(_controller.text),
                        child: const Text('검색', style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                // 제안 칩 행 — 가로 스크롤(D5, 2줄로 밀리는 버튼 금지, ai_chat_screen.dart의
                // _ClarifyChips와 같은 원칙).
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      for (var i = 0; i < heroSuggestions.length; i++) ...[
                        if (i > 0) const SizedBox(width: 7),
                        _SuggestionChip(
                          label: heroSuggestions[i],
                          onTap: () => _submit(heroSuggestions[i], fromChip: true),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 히어로 제안 칩 한 개 — 반투명 petrol 알약(웹 HeroSearch.tsx 제안칩 스타일 미러).
class _SuggestionChip extends StatelessWidget {
  const _SuggestionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: ValueKey('hero_suggestion_$label'),
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Padding(
        // 히트 영역만 넓힌다(48dp, Material 접근성 최소 터치 타깃) — 시각적 알약(아래
        // Container)은 그대로 둔다. 차종 칩 줄(_CategoryChipsRow)이 이미 쓰는 것과 같은
        // 기법이다(후속 코드리뷰 spec-16-8 2차 리뷰 P10 — 같은 커밋·같은 교정에서 이 제안
        // 칩만 빠져 vertical:7 + 11.5pt ≈ 30px로 남아 있었다).
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
          decoration: BoxDecoration(
            // 원시 Colors.white 리터럴 대신 이미 정의된 토큰(AppColors.onPetrol, 값은 흰색과
            // 동일)을 재사용한다(코드리뷰 발견) — petrol 배경 위 잉크 색 토큰만 바꾸면 되는
            // 상황에서 리터럴이 누락되기 쉬운 토큰-드리프트 시작점이었다.
            color: AppColors.onPetrol.withValues(alpha: 0.14),
            border: Border.all(color: AppColors.onPetrol.withValues(alpha: 0.22)),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(label,
              style: const TextStyle(
                  color: AppColors.onPetrol, fontSize: 11.5, fontWeight: FontWeight.w600)),
        ),
      ),
    );
  }
}

/// 차종 칩 하나의 목적지 — body_type 또는 fuel 필터, 둘 다 null이면 무필터("전체").
class CategoryChip {
  const CategoryChip(this.label, {this.bodyType, this.fuel});

  final String label;
  final String? bodyType;
  final String? fuel;
}

// 순서·라벨은 웹 CategoryChips.tsx의 CATEGORY_CHIPS와 값·순서 바이트 일치(spec-16-8 Always).
// "세단"·"수입"은 목업에 있지만 DB body_type/fuel에 1:1 대응 값이 없어 뺐다 — 웹이 이미 같은
// 이유로 뺀 6개를 그대로 따른다(Design Notes, CLAUDE.md B9).
// `@visibleForTesting`(후속 코드리뷰 spec-16-8 2차 리뷰 P5) — bodyType/fuel은 자유 문자열이라
// 오타(예: '화물차' → '화물')가 나도 컴파일은 통과한다. `ResolvedFilters.fromInput`의
// `pickOption`은 화이트리스트(ListingOptions) 밖 값을 조용히 null로 떨어뜨리므로, 그런 오타
// 칩은 "전체 매물"을 보여주며 라벨과 다른 결과를 낸다(spec의 Never 위반) — 이 상수를 top-level로
// 꺼내 테스트가 모든 항목을 ListingOptions 화이트리스트에 직접 대조하게 한다.
@visibleForTesting
const List<CategoryChip> categoryChips = [
  CategoryChip('전체'),
  CategoryChip('경차', bodyType: '경차'),
  CategoryChip('SUV', bodyType: 'SUV'),
  CategoryChip('전기', fuel: '전기'),
  CategoryChip('화물', bodyType: '화물차'),
  CategoryChip('승합', bodyType: '승합차'),
];

/// 차종 빠른 진입 줄(spec-16-8 AC2) — 가로 스크롤(D5, 웹 CategoryChips.tsx의
/// overflow-x-auto 미러: 좁은 화면에서 6개가 한 줄에 다 안 들어와도 줄바꿈하지 않는다).
class _CategoryChipsRow extends StatelessWidget {
  const _CategoryChipsRow({required this.onTapChip});

  final ValueChanged<CategoryChip> onTapChip;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      key: const Key('category_chips'),
      // 행 전체 높이는 48(Material 접근성 최소 터치 타깃) — 시각적 칩 높이(36)는 아래
      // Container가 그대로 유지하고, 그 위아래 6px씩을 InkWell 히트 영역에만 더한다
      // (코드리뷰 발견: 기존 36px 탭 영역이 48dp 미만이었다).
      height: 48,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: categoryChips.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final chip = categoryChips[i];
          // "전체"는 항상 petrol 채움(선택) 상태로 정적 표시한다(spec-16-9 Always) — 이 화면엔
          // 실제 필터 선택 추적이 없다(어느 칩을 눌러도 화면을 그대로 두고 SearchScreen을 새로
          // 연다), 그래서 이건 진짜 "선택 상태"가 아니라 "전체"가 기본값임을 알리는 장식이다.
          // 나머지 5개는 기존 아웃라인 스타일 그대로.
          final selected = chip.label == '전체';
          return InkWell(
            key: ValueKey('category_chip_${chip.label}'),
            borderRadius: BorderRadius.circular(999),
            onTap: () => onTapChip(chip),
            child: Padding(
              // 히트 영역만 넓힌다 — 시각적 칩(아래 Container)은 그대로 36 높이.
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Container(
                height: 36,
                padding: const EdgeInsets.symmetric(horizontal: 13),
                decoration: BoxDecoration(
                  color: selected ? AppColors.brandPetrol : AppColors.surfaceRaised,
                  border:
                      selected ? null : Border.all(color: AppColors.borderHairline),
                  borderRadius: BorderRadius.circular(999),
                ),
                alignment: Alignment.center,
                child: Text(chip.label,
                    style: TextStyle(
                        color: selected ? AppColors.onPetrol : AppColors.inkSecondary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600)),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// "지금 인기" 매물 미리보기 — popularListingsProvider(view_count desc, 4건, spec-16-8).
/// 조회 실패는 이 섹션에만 에러 문구를 남기고 히어로·차종칩·"방금 올라온 매물"은 정상
/// 렌더된다(spec-16-8 Always, 웹 fetchSection의 단별 독립 에러 격리 미러 — 이 위젯이
/// _RecentListings와 별개 ConsumerWidget이라 한쪽의 AsyncValue.error가 다른 쪽 렌더를
/// 막지 않는다).
class _PopularListings extends ConsumerWidget {
  const _PopularListings();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(popularListingsProvider);
    // 찜 오버레이 — 카드 진입점 3곳(홈·검색·AI)이 공유하는 단일 provider(spec-16-3 Boundaries).
    final wishedIds = ref.watch(wishedListingIdsProvider).value ?? const <String>{};
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, _) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Text('지금 인기 매물을 불러오지 못했습니다.',
            key: Key('popular_error'),
            style: TextStyle(color: AppColors.inkMuted)),
      ),
      data: (listings) {
        if (listings.isEmpty) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('등록된 매물이 없습니다.',
                style: TextStyle(color: AppColors.inkMuted)),
          );
        }
        return Column(
          // 카드가 카드 폭을 꽉 채우도록 stretch(없으면 내용 너비로 줄어 가운데 정렬돼 들쭉날쭉).
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final l in listings)
              ListingCard(
                // 목록이 갱신될 때(당겨서 새로고침 등) Flutter가 같은 위치의 카드 State를 다른
                // 매물에 재사용해 WishButton의 낙관적 하트 상태가 엉뚱한 매물에 붙는 걸 막는다
                // (코드리뷰 지적 — wishlist_screen.dart가 이미 쓰는 것과 같은 key).
                key: ValueKey(l.id),
                listing: l,
                wished: wishedIds.contains(l.id),
                onTap: () => Navigator.of(context, rootNavigator: true).push(
                  MaterialPageRoute(
                      builder: (_) => ListingDetailScreen(listingId: l.id)),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// "방금 올라온 매물" 목록(구 "최근 매물") — recentListingsProvider 를 watch 해 로딩/에러/빈/
/// 데이터 분기.
class _RecentListings extends ConsumerWidget {
  const _RecentListings();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(recentListingsProvider);
    // 찜 오버레이 — 카드 진입점 3곳(홈·검색·AI)이 공유하는 단일 provider(spec-16-3 Boundaries).
    final wishedIds = ref.watch(wishedListingIdsProvider).value ?? const <String>{};
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, _) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Text('방금 올라온 매물을 불러오지 못했습니다.',
            key: Key('recent_error'),
            style: TextStyle(color: AppColors.inkMuted)),
      ),
      data: (listings) {
        if (listings.isEmpty) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('등록된 매물이 없습니다.',
                style: TextStyle(color: AppColors.inkMuted)),
          );
        }
        return Column(
          // 카드가 카드 폭을 꽉 채우도록 stretch(없으면 내용 너비로 줄어 가운데 정렬돼 들쭉날쭉).
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final l in listings)
              ListingCard(
                // 목록이 갱신될 때(당겨서 새로고침 등) Flutter가 같은 위치의 카드 State를 다른
                // 매물에 재사용해 WishButton의 낙관적 하트 상태가 엉뚱한 매물에 붙는 걸 막는다
                // (코드리뷰 지적 — wishlist_screen.dart가 이미 쓰는 것과 같은 key).
                key: ValueKey(l.id),
                listing: l,
                wished: wishedIds.contains(l.id),
                onTap: () => Navigator.of(context, rootNavigator: true).push(
                  MaterialPageRoute(
                      builder: (_) => ListingDetailScreen(listingId: l.id)),
                ),
              ),
          ],
        );
      },
    );
  }
}
