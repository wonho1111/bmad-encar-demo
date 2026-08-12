// 매물 탐색 화면(FR9·11 재현) — 필터 입력 + 판매중(on_sale) 매물 카드 목록.
// 키워드(모델명)·차종·색상·연료·변속기·지역·가격범위·연식범위로 좁힌다.
// 0건/조회실패/로딩을 구분해 안내(AsyncValue). 카드 누르면 상세로 이동.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../wishlist/wishlist_providers.dart';
import 'listing_card.dart';
import 'listing_detail_screen.dart';
import 'listing_filters.dart';
import 'listings_providers.dart';

class SearchScreen extends ConsumerStatefulWidget {
  // 차종 칩(spec-16-8 AC2) 목적지 계약 — 값이 있으면 진입 즉시 그 필터로 조회한다(수동 검색
  // 버튼 없이). 둘 다 null이면(홈의 "전체" 칩) 무필터로 조회한다 — 컨트롤러가 이전 진입에서
  // 다른 필터를 들고 있어도 이 진입이 그 값을 항상 되돌린다(후속 코드리뷰 spec-16-8 2차 리뷰
  // P1: 예전엔 둘 다 null이면 아예 스킵해서, SUV 칩 → 뒤로가기 → "전체" 칩으로 들어오면
  // searchControllerProvider(앱 전역 싱글턴)가 SUV 입력·결과를 그대로 들고 있어 "전체" 라벨
  // 아래 SUV 매물만 보이는 AC2 위반이 있었다).
  const SearchScreen({super.key, this.initialBodyType, this.initialFuel});

  final String? initialBodyType;
  final String? initialFuel;

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _keyword = TextEditingController();
  final _priceMin = TextEditingController();
  final _priceMax = TextEditingController();
  final _yearMin = TextEditingController();
  final _yearMax = TextEditingController();

  String? _bodyType;
  String? _color;
  String? _fuel;
  String? _transmission;
  String? _region;
  // ✎ 2026-08-13 — 신뢰속성 필터(web /search와 같은 축). 뱃지 기준(accident_status)이다.
  String? _accidentStatus;
  bool _singleOwnerOnly = false;
  bool _nonSmokerOnly = false;

  @override
  void initState() {
    super.initState();
    _bodyType = widget.initialBodyType;
    _fuel = widget.initialFuel;

    // "필터 진입 경합" 방어(spec-16-8 Design Notes) — searchControllerProvider는 앱 전역
    // 싱글턴이라, 이번이 이 세션의 첫 진입이면 provider의 build()가 빈 필터 초기조회를
    // Future.microtask로 예약해 둔다. 그 예약이 **우리보다 먼저 큐에 서게** 강제로 provider를
    // 먼저 살린 뒤(동기), 우리 필터 조회는 별도 microtask로 그 다음 순번에 세운다 — 그러면
    // SearchController.search()의 requestId 채번 순서가 항상 "자동 빈 조회 → 우리 필터 조회"가
    // 되어, 응답이 어떤 순서로 와도 최종 화면은 필터 결과를 보여준다(호출 순서 재배치로 해결).
    //
    // ⚠️ (후속 코드리뷰 spec-16-8 2차 리뷰 P1) 둘 다 null("전체" 칩)이어도 이 아래 블록을
    // 그대로 타야 한다 — 예전엔 여기서 조기 return해 "전체" 진입이 컨트롤러를 전혀 건드리지
    // 않았고, 그러면 컨트롤러가 이전 진입(예: SUV 칩)의 입력·결과를 그대로 들고 있어 "전체"
    // 라벨 아래 SUV 결과가 보이는 버그가 났다. updateInput에 null을 그대로 넘기면
    // ListingFilterInput(bodyType: null, fuel: null) = 무필터라 "전체"의 의미와 정확히 같다.
    ref.read(searchControllerProvider.notifier);
    Future.microtask(() {
      // 이 마이크로태스크가 실행되기 전에 화면이 dispose될 수 있다(예: 칩 탭 직후 빠르게
      // 뒤로가기) — 그러면 disposed 상태의 ConsumerState에서 ref.read/setState를 호출해
      // 예외가 난다(코드리뷰 발견, spec-16-8 Review Triage Log #3).
      if (!mounted) return;
      final notifier = ref.read(searchControllerProvider.notifier);
      notifier.updateInput(ListingFilterInput(
        bodyType: widget.initialBodyType,
        fuel: widget.initialFuel,
      ));
      notifier.search();
    });
  }

  @override
  void dispose() {
    _keyword.dispose();
    _priceMin.dispose();
    _priceMax.dispose();
    _yearMin.dispose();
    _yearMax.dispose();
    super.dispose();
  }

  void _runSearch() {
    // 화면 입력을 컨트롤러에 반영한 뒤 검색 실행.
    final input = ListingFilterInput(
      keyword: _keyword.text,
      bodyType: _bodyType,
      color: _color,
      fuel: _fuel,
      transmission: _transmission,
      region: _region,
      accidentStatus: _accidentStatus,
      singleOwnerOnly: _singleOwnerOnly,
      nonSmokerOnly: _nonSmokerOnly,
      priceMin: _priceMin.text,
      priceMax: _priceMax.text,
      yearMin: _yearMin.text,
      yearMax: _yearMax.text,
    );
    final notifier = ref.read(searchControllerProvider.notifier);
    notifier.updateInput(input);
    notifier.search();
  }

  void _openDetail(String id) {
    // rootNavigator: true — 이 화면 자체가 홈의 rootNavigator push로만 도달하므로 지금은
    // 항상 이미 셸 밖이지만, 셸 경계를 파라미터가 아니라 "어느 Navigator에 쌓느냐"로 고정
    // 하는 spec-16-1 원칙을 이 push에도 동일하게 적용한다(Code Map).
    Navigator.of(context, rootNavigator: true).push(
      MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: id)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchControllerProvider).results;
    // 찜 오버레이 — 카드 진입점 3곳(홈·검색·AI)이 공유하는 단일 provider(spec-16-3 Boundaries).
    final wishedIds = ref.watch(wishedListingIdsProvider).value ?? const <String>{};

    return Scaffold(
      appBar: AppBar(title: const Text('매물 탐색')),
      body: Column(
        children: [
          _FilterPanel(
            keyword: _keyword,
            priceMin: _priceMin,
            priceMax: _priceMax,
            yearMin: _yearMin,
            yearMax: _yearMax,
            bodyType: _bodyType,
            color: _color,
            fuel: _fuel,
            transmission: _transmission,
            region: _region,
            accidentStatus: _accidentStatus,
            singleOwnerOnly: _singleOwnerOnly,
            nonSmokerOnly: _nonSmokerOnly,
            onBodyType: (v) => setState(() => _bodyType = v),
            onColor: (v) => setState(() => _color = v),
            onFuel: (v) => setState(() => _fuel = v),
            onTransmission: (v) => setState(() => _transmission = v),
            onRegion: (v) => setState(() => _region = v),
            onAccidentStatus: (v) => setState(() => _accidentStatus = v),
            onSingleOwnerOnly: (v) => setState(() => _singleOwnerOnly = v),
            onNonSmokerOnly: (v) => setState(() => _nonSmokerOnly = v),
            onSearch: _runSearch,
          ),
          const Divider(height: 1),
          Expanded(
            child: results.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    '매물 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
                    key: const Key('search_error'),
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
              data: (listings) {
                if (listings.isEmpty) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        '조건에 맞는 매물이 없습니다. 필터를 완화해 보세요.',
                        key: Key('search_empty'),
                      ),
                    ),
                  );
                }
                return ListView.builder(
                  // 하단 패딩에 시스템 내비바 높이를 더해(edge-to-edge) 마지막 카드가 가리지 않게.
                  padding: EdgeInsets.fromLTRB(
                      12, 12, 12, 12 + MediaQuery.of(context).viewPadding.bottom),
                  itemCount: listings.length + 1,
                  itemBuilder: (context, i) {
                    if (i == 0) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          '${listings.length}건의 매물',
                          style: TextStyle(color: Colors.grey[600], fontSize: 13),
                        ),
                      );
                    }
                    final l = listings[i - 1];
                    return ListingCard(
                      // 필터를 바꿔 목록이 교체되면 Flutter가 같은 위치의 카드 State를 다른
                      // 매물에 재사용해 WishButton의 낙관적 하트 상태가 엉뚱한 매물에 붙는 걸
                      // 막는다(코드리뷰 지적 — wishlist_screen.dart가 이미 쓰는 것과 같은 key).
                      key: ValueKey(l.id),
                      listing: l,
                      wished: wishedIds.contains(l.id),
                      onTap: () => _openDetail(l.id),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// 필터 입력 패널(접을 수 있는 ExpansionTile). 키워드·드롭다운·범위 + 검색 버튼.
class _FilterPanel extends StatelessWidget {
  const _FilterPanel({
    required this.keyword,
    required this.priceMin,
    required this.priceMax,
    required this.yearMin,
    required this.yearMax,
    required this.bodyType,
    required this.color,
    required this.fuel,
    required this.transmission,
    required this.region,
    required this.accidentStatus,
    required this.singleOwnerOnly,
    required this.nonSmokerOnly,
    required this.onBodyType,
    required this.onColor,
    required this.onFuel,
    required this.onTransmission,
    required this.onRegion,
    required this.onAccidentStatus,
    required this.onSingleOwnerOnly,
    required this.onNonSmokerOnly,
    required this.onSearch,
  });

  final TextEditingController keyword;
  final TextEditingController priceMin;
  final TextEditingController priceMax;
  final TextEditingController yearMin;
  final TextEditingController yearMax;
  final String? bodyType;
  final String? color;
  final String? fuel;
  final String? transmission;
  final String? region;
  final String? accidentStatus;
  final bool singleOwnerOnly;
  final bool nonSmokerOnly;
  final ValueChanged<String?> onBodyType;
  final ValueChanged<String?> onColor;
  final ValueChanged<String?> onFuel;
  final ValueChanged<String?> onTransmission;
  final ValueChanged<String?> onRegion;
  final ValueChanged<String?> onAccidentStatus;
  final ValueChanged<bool> onSingleOwnerOnly;
  final ValueChanged<bool> onNonSmokerOnly;
  final VoidCallback onSearch;

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      title: const Text('필터'),
      initiallyExpanded: true,
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        TextField(
          controller: keyword,
          decoration: const InputDecoration(
            labelText: '모델명 (부분일치)',
            isDense: true,
          ),
          onSubmitted: (_) => onSearch(),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _dropdown('차종', bodyType, ListingOptions.bodyType, onBodyType)),
            const SizedBox(width: 8),
            Expanded(child: _dropdown('색상', color, ListingOptions.color, onColor)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _dropdown('연료', fuel, ListingOptions.fuel, onFuel)),
            const SizedBox(width: 8),
            Expanded(child: _dropdown('변속기', transmission, ListingOptions.transmission, onTransmission)),
          ],
        ),
        const SizedBox(height: 8),
        // ✎ 2026-08-13 — 지역 단독 행에 사고이력을 합쳐 **행 수를 늘리지 않는다.** 이 패널은
        //   스크롤되지 않는 Column의 자식이고 그 아래 결과 목록이 남은 높이를 나눠 쓰므로,
        //   행이 하나 늘 때마다 결과가 화면 밖으로 밀린다(실측: 처음에 세로로 쌓았더니 작은
        //   화면에서 71px 오버플로, 한 줄로 줄여도 첫 카드가 안 보였다).
        Row(
          children: [
            Expanded(child: _dropdown('지역', region, ListingOptions.region, onRegion)),
            const SizedBox(width: 8),
            Expanded(
              child: _dropdown(
                '사고이력',
                accidentStatus,
                ListingOptions.accidentStatus,
                onAccidentStatus,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _numField('가격 최소(원)', priceMin)),
            const SizedBox(width: 8),
            Expanded(child: _numField('가격 최대(원)', priceMax)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _numField('연식 최소', yearMin)),
            const SizedBox(width: 8),
            Expanded(child: _numField('연식 최대', yearMax)),
          ],
        ),
        const SizedBox(height: 12),
        // 신뢰 체크박스 2개를 검색 버튼과 **같은 행**에 둔다(위 주석과 같은 이유 — 행을 안 늘린다).
        Row(
          children: [
            _CompactCheck(
              key: const Key('filter_single_owner'),
              label: '1인소유',
              value: singleOwnerOnly,
              onChanged: onSingleOwnerOnly,
            ),
            _CompactCheck(
              key: const Key('filter_non_smoker'),
              label: '비흡연',
              value: nonSmokerOnly,
              onChanged: onNonSmokerOnly,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: FilledButton(
                key: const Key('search_button'),
                onPressed: onSearch,
                child: const Text('검색'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _dropdown(
    String label,
    String? value,
    List<String> options,
    ValueChanged<String?> onChanged,
  ) {
    return DropdownButtonFormField<String?>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        const DropdownMenuItem<String?>(value: null, child: Text('전체')),
        ...options.map((o) => DropdownMenuItem<String?>(value: o, child: Text(o))),
      ],
      onChanged: onChanged,
    );
  }

  Widget _numField(String label, TextEditingController c) {
    return TextField(
      controller: c,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(labelText: label, isDense: true),
    );
  }
}

/// 필터 패널의 좁은 체크박스 — `CheckboxListTile`은 한 줄을 통째로 먹고 높이도 커서 이 패널
/// (스크롤 안 되는 Column의 자식)에 세로로 쌓을 수 없다. 체크박스 + 라벨만 가로로 붙인다.
class _CompactCheck extends StatelessWidget {
  const _CompactCheck({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Checkbox(
          value: value,
          visualDensity: VisualDensity.compact,
          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          onChanged: (v) => onChanged(v ?? false),
        ),
        GestureDetector(
          onTap: () => onChanged(!value),
          child: Text(label, style: const TextStyle(fontSize: 13)),
        ),
        const SizedBox(width: 4),
      ],
    );
  }
}
