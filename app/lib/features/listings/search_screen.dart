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
// 옵션 다중선택 통제어휘 — 카드 칩 로직(options.dart)이 이미 쓰는 단일 출처를 필터도 재사용한다
// (web이 SellForm 상수를 필터에 재사용한 것과 동일 원칙, 2026-09-01).
import 'options.dart' show allControlledOptions;

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
  // 주행거리·배기량·인승 범위(개선 2, 2026-09-01) — 등록 폼엔 단일값 입력이 있는데 필터엔 그
  // 축 자체가 없었다. 가격·연식과 같은 컨트롤러 관례로 맞춘다.
  final _mileageMin = TextEditingController();
  final _mileageMax = TextEditingController();
  final _displacementMin = TextEditingController();
  final _displacementMax = TextEditingController();
  final _seatsMin = TextEditingController();
  final _seatsMax = TextEditingController();

  // 제조사(개선 2) — 등록 폼(sell_screen)엔 있었는데 필터엔 없던 축.
  String? _manufacturer;
  String? _bodyType;
  String? _color;
  String? _fuel;
  String? _transmission;
  String? _region;
  // ✎ 2026-08-13 — 신뢰속성 필터(web /search와 같은 축). 뱃지 기준(accident_status)이다.
  String? _accidentStatus;
  bool _singleOwnerOnly = false;
  bool _nonSmokerOnly = false;
  // 옵션(개선 2) — 다중 선택, "전부 보유"(AND) 의미.
  List<String> _selectedOptions = const [];

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
    _mileageMin.dispose();
    _mileageMax.dispose();
    _displacementMin.dispose();
    _displacementMax.dispose();
    _seatsMin.dispose();
    _seatsMax.dispose();
    super.dispose();
  }

  void _runSearch() {
    // 화면 입력을 컨트롤러에 반영한 뒤 검색 실행.
    final input = ListingFilterInput(
      keyword: _keyword.text,
      manufacturer: _manufacturer,
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
      mileageMin: _mileageMin.text,
      mileageMax: _mileageMax.text,
      displacementMin: _displacementMin.text,
      displacementMax: _displacementMax.text,
      seatsMin: _seatsMin.text,
      seatsMax: _seatsMax.text,
      options: _selectedOptions,
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
      // ✎ 2026-08-13 사용자 지시("웹과 일관성 + 개발용어 제거") — 제목을 웹 상단 메뉴 어휘로
      // 맞춘다. 웹은 이 화면을 "내 차 사기"라 부르는데(nav-links.ts) 앱만 "매물 탐색"이라
      // 불러, 같은 화면을 두 이름으로 부르고 있었다.
      appBar: AppBar(title: const Text('내 차 사기')),
      body: Column(
        children: [
          _FilterPanel(
            keyword: _keyword,
            priceMin: _priceMin,
            priceMax: _priceMax,
            yearMin: _yearMin,
            yearMax: _yearMax,
            mileageMin: _mileageMin,
            mileageMax: _mileageMax,
            displacementMin: _displacementMin,
            displacementMax: _displacementMax,
            seatsMin: _seatsMin,
            seatsMax: _seatsMax,
            manufacturer: _manufacturer,
            bodyType: _bodyType,
            color: _color,
            fuel: _fuel,
            transmission: _transmission,
            region: _region,
            accidentStatus: _accidentStatus,
            singleOwnerOnly: _singleOwnerOnly,
            nonSmokerOnly: _nonSmokerOnly,
            selectedOptions: _selectedOptions,
            onManufacturer: (v) => setState(() => _manufacturer = v),
            onBodyType: (v) => setState(() => _bodyType = v),
            onColor: (v) => setState(() => _color = v),
            onFuel: (v) => setState(() => _fuel = v),
            onTransmission: (v) => setState(() => _transmission = v),
            onRegion: (v) => setState(() => _region = v),
            onAccidentStatus: (v) => setState(() => _accidentStatus = v),
            onSingleOwnerOnly: (v) => setState(() => _singleOwnerOnly = v),
            onNonSmokerOnly: (v) => setState(() => _nonSmokerOnly = v),
            onOptionsChanged: (v) => setState(() => _selectedOptions = v),
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

/// 필터 입력 패널(접을 수 있는 ExpansionTile). 등록 폼(sell_screen)과 같은 축·순서로 통일한다
/// (web SearchFilters.tsx와 동일한 사용자 지시, 2026-09-01) — 제조사→모델(키워드)→차종→연식→
/// 가격→주행거리→색상→연료→변속기→배기량→인승→지역→신뢰정보→옵션.
///
/// ⚠️ web과 다르게 간 점 — 옵션 다중선택: 이 앱의 등록 폼(sell_screen)엔 web SellForm의
///   OptionPicker(칩 요약+인기칩+카테고리 검색) 같은 컴포넌트가 아예 없다(쉼표구분 텍스트필드
///   뿐이다) — 그래서 web처럼 "등록 폼 컴포넌트를 그대로 재사용"할 대상이 없다. 대신 이
///   필터 자체의 기존 시각 언어(드롭다운·체크박스와 같은 밀도)로 다중선택 체크리스트를 새로
///   최소 구현한다(_OptionMultiSelect) — 통제어휘(options.dart의 allControlledOptions, 카드
///   칩 로직이 이미 쓰는 단일 출처)는 재사용한다.
///
/// 필드 수가 많이 늘어(6→13축) 접힌 패널을 항상 펼친 채(initiallyExpanded) 스크롤 없는 Column
/// 안에 그대로 쌓으면 화면 밖으로 넘친다(위 옛 주석이 필드 2개만으로도 겪었던 문제) — 옵션
/// 목록(통제어휘 전체)만 별도로도 71개라 한 화면에 다 펼치면 그 자체로 넘친다. 그래서 드롭다운·
/// 범위·신뢰정보·옵션 전체를 **패널 자체 높이를 제한한 스크롤 영역**(ConstrainedBox+
/// SingleChildScrollView) 안에 넣고, 검색 버튼만 그 밖에 항상 보이게 둔다.
class _FilterPanel extends StatelessWidget {
  const _FilterPanel({
    required this.keyword,
    required this.priceMin,
    required this.priceMax,
    required this.yearMin,
    required this.yearMax,
    required this.mileageMin,
    required this.mileageMax,
    required this.displacementMin,
    required this.displacementMax,
    required this.seatsMin,
    required this.seatsMax,
    required this.manufacturer,
    required this.bodyType,
    required this.color,
    required this.fuel,
    required this.transmission,
    required this.region,
    required this.accidentStatus,
    required this.singleOwnerOnly,
    required this.nonSmokerOnly,
    required this.selectedOptions,
    required this.onManufacturer,
    required this.onBodyType,
    required this.onColor,
    required this.onFuel,
    required this.onTransmission,
    required this.onRegion,
    required this.onAccidentStatus,
    required this.onSingleOwnerOnly,
    required this.onNonSmokerOnly,
    required this.onOptionsChanged,
    required this.onSearch,
  });

  final TextEditingController keyword;
  final TextEditingController priceMin;
  final TextEditingController priceMax;
  final TextEditingController yearMin;
  final TextEditingController yearMax;
  final TextEditingController mileageMin;
  final TextEditingController mileageMax;
  final TextEditingController displacementMin;
  final TextEditingController displacementMax;
  final TextEditingController seatsMin;
  final TextEditingController seatsMax;
  final String? manufacturer;
  final String? bodyType;
  final String? color;
  final String? fuel;
  final String? transmission;
  final String? region;
  final String? accidentStatus;
  final bool singleOwnerOnly;
  final bool nonSmokerOnly;
  final List<String> selectedOptions;
  final ValueChanged<String?> onManufacturer;
  final ValueChanged<String?> onBodyType;
  final ValueChanged<String?> onColor;
  final ValueChanged<String?> onFuel;
  final ValueChanged<String?> onTransmission;
  final ValueChanged<String?> onRegion;
  final ValueChanged<String?> onAccidentStatus;
  final ValueChanged<bool> onSingleOwnerOnly;
  final ValueChanged<bool> onNonSmokerOnly;
  final ValueChanged<List<String>> onOptionsChanged;
  final VoidCallback onSearch;

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      title: const Text('필터'),
      initiallyExpanded: true,
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        // 스크롤 영역(위 클래스 주석) — 이 안의 순서가 web SearchFilters.tsx의 필드 순서다.
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 380),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _dropdown('제조사', manufacturer, ListingOptions.manufacturer, onManufacturer),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: keyword,
                        decoration: const InputDecoration(
                          // ✎ 2026-08-13 — "부분일치"는 검색 구현 방식(SQL ilike)을 그대로 노출한
                          // 개발 용어였다. 웹 필터의 같은 칸 라벨("키워드(모델명)")로 맞춘다.
                          labelText: '키워드(모델명)',
                          isDense: true,
                        ),
                        onSubmitted: (_) => onSearch(),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _dropdown('차종', bodyType, ListingOptions.bodyType, onBodyType)),
                    const SizedBox(width: 8),
                    Expanded(child: _rangeField('연식(년)', yearMin, yearMax)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _rangeField('가격(원)', priceMin, priceMax)),
                    const SizedBox(width: 8),
                    Expanded(child: _rangeField('주행거리(km)', mileageMin, mileageMax)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _dropdown('색상', color, ListingOptions.color, onColor)),
                    const SizedBox(width: 8),
                    Expanded(child: _dropdown('연료', fuel, ListingOptions.fuel, onFuel)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _dropdown('변속기', transmission, ListingOptions.transmission, onTransmission),
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: _rangeField('배기량(cc)', displacementMin, displacementMax)),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: _rangeField('인승(명)', seatsMin, seatsMax)),
                    const SizedBox(width: 8),
                    Expanded(child: _dropdown('지역', region, ListingOptions.region, onRegion)),
                  ],
                ),
                const SizedBox(height: 12),
                // 신뢰 정보 — 등록 폼(sell_screen)과 같은 3축(사고이력·1인소유·비흡연), web
                // SearchFilters.tsx의 신뢰 정보 fieldset과 같은 구성.
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('신뢰 정보', style: TextStyle(fontSize: 12, color: Colors.grey)),
                      const SizedBox(height: 4),
                      _dropdown('사고이력', accidentStatus, ListingOptions.accidentStatus, onAccidentStatus),
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
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                // 옵션(개선 2) — 다중 선택(전부 보유, AND). 위 클래스 주석 참조.
                _OptionMultiSelect(selected: selectedOptions, onChanged: onOptionsChanged),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton(
          key: const Key('search_button'),
          onPressed: onSearch,
          child: const Text('검색'),
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

  /// 범위(최소~최대) 입력 한 쌍 — web renderRange 이식. 연식·가격·주행거리·배기량·인승 5축이
  /// 공유하는 공통 헬퍼(과설계 방지 — 파일을 새로 만들지 않고 이 클래스의 private 메서드로).
  Widget _rangeField(String label, TextEditingController minC, TextEditingController maxC) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 4, left: 2),
          child: Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        ),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: minC,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(hintText: '최소', isDense: true),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 6),
              child: Text('~'),
            ),
            Expanded(
              child: TextField(
                controller: maxC,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(hintText: '최대', isDense: true),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// 옵션 다중선택(전부 보유, AND) — web OptionPicker가 없는 이 앱에서 필터 자체 시각 언어
/// (칩·체크박스)로 최소 구현한 대체재(위 _FilterPanel 클래스 주석 참조). 통제어휘 71개가 한
/// 번에 펼쳐지면 그 자체로 패널을 넘치게 하므로, 이 위젯만 높이를 한정해 내부 스크롤한다.
class _OptionMultiSelect extends StatelessWidget {
  const _OptionMultiSelect({required this.selected, required this.onChanged});

  final List<String> selected;
  final ValueChanged<List<String>> onChanged;

  @override
  Widget build(BuildContext context) {
    final selectedSet = selected.toSet();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '옵션(다중 선택 — 선택한 옵션 전부 보유한 매물만)',
          style: TextStyle(fontSize: 12, color: Colors.grey),
        ),
        const SizedBox(height: 4),
        Container(
          constraints: const BoxConstraints(maxHeight: 140),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            border: Border.all(color: Theme.of(context).dividerColor),
            borderRadius: BorderRadius.circular(4),
          ),
          child: SingleChildScrollView(
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: allControlledOptions.map((name) {
                final isSelected = selectedSet.contains(name);
                return FilterChip(
                  key: ValueKey('filter_option_$name'),
                  label: Text(name, style: const TextStyle(fontSize: 12)),
                  visualDensity: VisualDensity.compact,
                  selected: isSelected,
                  onSelected: (_) {
                    final next = List<String>.from(selected);
                    if (isSelected) {
                      next.remove(name);
                    } else {
                      next.add(name);
                    }
                    onChanged(next);
                  },
                );
              }).toList(),
            ),
          ),
        ),
      ],
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
