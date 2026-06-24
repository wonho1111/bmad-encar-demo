// 매물 탐색 화면(FR9·11 재현) — 필터 입력 + 판매중(on_sale) 매물 카드 목록.
// 키워드(모델명)·차종·색상·연료·변속기·지역·가격범위·연식범위로 좁힌다.
// 0건/조회실패/로딩을 구분해 안내(AsyncValue). 카드 누르면 상세로 이동.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'listing_card.dart';
import 'listing_detail_screen.dart';
import 'listing_filters.dart';
import 'listings_providers.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

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
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: id)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchControllerProvider).results;

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
            onBodyType: (v) => setState(() => _bodyType = v),
            onColor: (v) => setState(() => _color = v),
            onFuel: (v) => setState(() => _fuel = v),
            onTransmission: (v) => setState(() => _transmission = v),
            onRegion: (v) => setState(() => _region = v),
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
                  padding: const EdgeInsets.all(12),
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
                      listing: l,
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
    required this.onBodyType,
    required this.onColor,
    required this.onFuel,
    required this.onTransmission,
    required this.onRegion,
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
  final ValueChanged<String?> onBodyType;
  final ValueChanged<String?> onColor;
  final ValueChanged<String?> onFuel;
  final ValueChanged<String?> onTransmission;
  final ValueChanged<String?> onRegion;
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
        _dropdown('지역', region, ListingOptions.region, onRegion),
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
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            key: const Key('search_button'),
            onPressed: onSearch,
            child: const Text('검색'),
          ),
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
