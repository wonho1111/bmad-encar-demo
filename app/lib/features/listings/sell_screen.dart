// 매물 등록 화면(7.3, FR5 재현) — 판매자가 15필드 폼을 채워 listings 를 on_sale 로 생성한다.
// 사진 없음(업로드 위젯 없음). 검증·INSERT 는 SellController 가 담당, 화면은 입력 수집·표시만.
//
// 역할 가드(AC4): 판매자(seller)만 진입. buyer 가 어떻게든 닿으면 입력 대신 안내를 보여준다.
//   (admin 은 main.dart AuthGate 가 이미 차단 — 모바일 제외 AR9.)
// 위젯 패턴은 signup_screen(ConsumerStatefulWidget + SingleChildScrollView + 에러/성공 텍스트)과
//   search_screen(DropdownButtonFormField)을 따른다.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../auth/user_role.dart';
import 'listing.dart' show ListingDetail;
import 'listing_filters.dart' show ListingOptions;
import 'listing_form.dart';
import 'sell_controller.dart';

/// 매물 등록/수정 화면(7.3 등록 + 7.4 수정). 같은 15필드 폼을 재사용한다.
///   · editDetail == null → 등록 모드(INSERT).
///   · editDetail != null → 수정 모드(UPDATE) — 기존 값으로 폼을 채우고, 성공 시 화면을 닫는다(done).
class SellScreen extends ConsumerStatefulWidget {
  const SellScreen({super.key, this.editDetail});

  /// 수정 대상 매물 상세(수정 모드일 때만). null 이면 등록 모드.
  final ListingDetail? editDetail;

  bool get isEdit => editDetail != null;

  @override
  ConsumerState<SellScreen> createState() => _SellScreenState();
}

class _SellScreenState extends ConsumerState<SellScreen> {
  // 텍스트/수치 입력은 TextEditingController, 드롭다운/체크박스는 로컬 변수로 보관한다.
  final _model = TextEditingController();
  final _year = TextEditingController();
  final _price = TextEditingController();
  final _mileage = TextEditingController();
  final _displacement = TextEditingController();
  final _seats = TextEditingController();
  final _options = TextEditingController();
  final _description = TextEditingController();

  String? _manufacturer;
  String? _bodyType;
  String? _color;
  String? _fuel;
  String? _transmission;
  String? _region;
  bool _accidentFree = true;

  @override
  void initState() {
    super.initState();
    // 수정 모드: 기존 값으로 화면 입력 + 컨트롤러(startEdit)를 채운다.
    final detail = widget.editDetail;
    if (detail != null) {
      final input = ListingFormInput.fromDetail(detail);
      _model.text = input.model;
      _year.text = input.year;
      _price.text = input.price;
      _mileage.text = input.mileage;
      _displacement.text = input.displacement;
      _seats.text = input.seats;
      _options.text = input.options;
      _description.text = input.description;
      _manufacturer = input.manufacturer;
      _bodyType = input.bodyType;
      _color = input.color;
      _fuel = input.fuel;
      _transmission = input.transmission;
      _region = input.region;
      _accidentFree = input.accidentFree;
      // 빌드 완료 후 컨트롤러에 수정 모드를 알린다(빌드 중 provider 수정 금지 → 다음 프레임).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(sellControllerProvider.notifier).startEdit(detail.id, input);
        }
      });
    }
  }

  @override
  void dispose() {
    _model.dispose();
    _year.dispose();
    _price.dispose();
    _mileage.dispose();
    _displacement.dispose();
    _seats.dispose();
    _options.dispose();
    _description.dispose();
    super.dispose();
  }

  /// 화면 입력을 모아 컨트롤러에 반영한 뒤 등록을 실행.
  void _submit() {
    final input = ListingFormInput(
      manufacturer: _manufacturer ?? '',
      model: _model.text,
      bodyType: _bodyType ?? '',
      year: _year.text,
      price: _price.text,
      mileage: _mileage.text,
      color: _color ?? '',
      fuel: _fuel ?? '',
      transmission: _transmission ?? '',
      displacement: _displacement.text,
      seats: _seats.text,
      region: _region ?? '',
      accidentFree: _accidentFree,
      options: _options.text,
      description: _description.text,
    );
    final notifier = ref.read(sellControllerProvider.notifier);
    notifier.updateInput(input);
    // 수정 모드면 대상 id 를 명시 전달 — 컨트롤러의 editingId 가 (post-frame startEdit 가 아직 안 돈) 첫 프레임에
    //   null 이더라도 등록(INSERT)로 새지 않고 반드시 수정(UPDATE)으로 가게 한다(중복 등록 사고 방지).
    notifier.submit(editingIdOverride: widget.editDetail?.id);
  }

  /// 등록 성공 시 폼 입력 위젯을 비운다(컨트롤러는 입력을 초기화했지만 화면 컨트롤러도 맞춘다).
  void _resetFields() {
    _model.clear();
    _year.clear();
    _price.clear();
    _mileage.clear();
    _displacement.clear();
    _seats.clear();
    _options.clear();
    _description.clear();
    setState(() {
      _manufacturer = null;
      _bodyType = null;
      _color = null;
      _fuel = null;
      _transmission = null;
      _region = null;
      _accidentFree = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final role = ref.watch(currentRoleProvider);

    final isEdit = widget.isEdit;
    final title = isEdit ? '매물 수정' : '매물 등록';

    // ── 역할 가드(AC5): 판매자만 등록/수정 화면 사용 ─────────────────
    if (role != UserRole.seller) {
      return Scaffold(
        appBar: AppBar(title: Text(title)),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              '판매자만 이용할 수 있습니다.',
              key: Key('sell_role_blocked'),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    final sell = ref.watch(sellControllerProvider);

    if (sell.success != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        if (isEdit) {
          // 수정 성공 → 화면을 닫고 목록으로 복귀(true 를 돌려줘 목록이 새로고침하게).
          if (sell.done && Navigator.of(context).canPop()) {
            Navigator.of(context).pop(true);
          }
        } else {
          // 등록 성공 → 화면 입력을 비운다(연속 등록 대비).
          if (_model.text.isNotEmpty) _resetFields();
        }
      });
    }

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  isEdit
                      ? '내 매물 정보를 수정합니다. (구매 완료 처리는 별도 기능입니다.)'
                      : '차량 정보를 입력해 등록하면 구매자에게 바로 노출됩니다(관리자 승인 없음).',
                  style: const TextStyle(fontSize: 13, color: Colors.grey),
                ),
                const SizedBox(height: 16),

                _dropdown('제조사', 'sell_manufacturer', _manufacturer,
                    ListingOptions.manufacturer, (v) => setState(() => _manufacturer = v)),
                const SizedBox(height: 12),
                _text('모델', 'sell_model', _model, hint: '예: 아반떼 CN7'),
                const SizedBox(height: 12),
                _dropdown('차종', 'sell_body_type', _bodyType, ListingOptions.bodyType,
                    (v) => setState(() => _bodyType = v)),
                const SizedBox(height: 12),
                _number('연식 (년)', 'sell_year', _year, hint: '예: 2021'),
                const SizedBox(height: 12),
                _number('가격 (원)', 'sell_price', _price, hint: '예: 29800000'),
                const SizedBox(height: 12),
                _number('주행거리 (km)', 'sell_mileage', _mileage, hint: '예: 103000'),
                const SizedBox(height: 12),
                _dropdown('색상', 'sell_color', _color, ListingOptions.color,
                    (v) => setState(() => _color = v)),
                const SizedBox(height: 12),
                _dropdown('연료', 'sell_fuel', _fuel, ListingOptions.fuel,
                    (v) => setState(() => _fuel = v)),
                const SizedBox(height: 12),
                _dropdown('변속기', 'sell_transmission', _transmission,
                    ListingOptions.transmission, (v) => setState(() => _transmission = v)),
                const SizedBox(height: 12),
                _number('배기량 (cc)', 'sell_displacement', _displacement,
                    hint: '예: 1598 (전기차는 0)'),
                const SizedBox(height: 12),
                _number('인승 (명)', 'sell_seats', _seats, hint: '예: 5'),
                const SizedBox(height: 12),
                _dropdown('지역', 'sell_region', _region, ListingOptions.region,
                    (v) => setState(() => _region = v)),
                const SizedBox(height: 12),

                SwitchListTile(
                  key: const Key('sell_accident_free'),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('무사고 차량'),
                  value: _accidentFree,
                  onChanged: sell.loading
                      ? null
                      : (v) => setState(() => _accidentFree = v),
                ),

                _text('옵션 (쉼표로 구분, 선택)', 'sell_options', _options,
                    hint: '예: 선루프, 후방카메라, 내비게이션'),
                const SizedBox(height: 12),
                _text('설명 (선택)', 'sell_description', _description,
                    hint: '차량 상태·이력 등을 자유롭게', maxLines: 3),
                const SizedBox(height: 16),

                if (sell.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      sell.error!,
                      key: const Key('sell_error'),
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                if (sell.success != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      sell.success!,
                      key: const Key('sell_success'),
                      style: const TextStyle(color: Colors.green),
                    ),
                  ),

                FilledButton(
                  key: const Key('sell_submit'),
                  onPressed: sell.loading ? null : _submit,
                  child: Text(
                    sell.loading
                        ? (isEdit ? '수정 중…' : '등록 중…')
                        : (isEdit ? '수정 완료' : '매물 등록'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── 입력 위젯 헬퍼 ───────────────────────────────────────────────
  Widget _text(String label, String keyName, TextEditingController c,
      {String? hint, int maxLines = 1}) {
    return TextField(
      key: Key(keyName),
      controller: c,
      maxLines: maxLines,
      decoration: InputDecoration(labelText: label, hintText: hint, isDense: true),
    );
  }

  Widget _number(String label, String keyName, TextEditingController c, {String? hint}) {
    return TextField(
      key: Key(keyName),
      controller: c,
      keyboardType: TextInputType.number,
      // 숫자만 입력 가능(소수점·부호 차단) — 정수 저장 규칙을 입력 단계부터 돕는다.
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      decoration: InputDecoration(labelText: label, hintText: hint, isDense: true),
    );
  }

  Widget _dropdown(String label, String keyName, String? value, List<String> options,
      ValueChanged<String?> onChanged) {
    return DropdownButtonFormField<String?>(
      key: Key(keyName),
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        const DropdownMenuItem<String?>(value: null, child: Text('선택')),
        ...options.map((o) => DropdownMenuItem<String?>(value: o, child: Text(o))),
      ],
      onChanged: onChanged,
    );
  }
}
