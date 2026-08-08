// 매물 등록 화면(7.3, FR5 재현) — 판매자가 15필드 폼을 채워 listings 를 on_sale 로 생성한다.
// 사진 없음(업로드 위젯 없음). 검증·INSERT 는 SellController 가 담당, 화면은 입력 수집·표시만.
//
// 역할 가드(AC4): 판매자(seller)만 진입. buyer 가 어떻게든 닿으면 입력 대신 안내를 보여준다.
//   (admin 은 core/router/app_router.dart의 GoRouter redirect가 이미 차단 — 모바일 제외 AR9.)
// 위젯 패턴은 signup_screen(ConsumerStatefulWidget + SingleChildScrollView + 에러/성공 텍스트)과
//   search_screen(DropdownButtonFormField)을 따른다.
//
// ⚠️ **셸 경계(spec-16-1)**: 이 화면은 두 자리에서 쓰인다 — ① 하단 4탭 셸의 '내차팔기' 브랜치
//   루트(`app_router.dart`, `showAppBar: false`, 항상 등록 모드) ② `my_listings_screen.dart`의
//   "수정" 버튼이 셸 밖 루트 Navigator로 여는 단독 화면(`showAppBar: true`, 기본값 — 뒤로가기가
//   있는 자기 AppBar가 필요). (spec-16-8이 홈의 "매물 등록" 퀵액션을 제거해 그 진입점은 더 이상
//   없다 — 등록은 이제 ①의 '내차팔기' 탭으로만 들어온다.)
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/require_user.dart';
import 'listing.dart' show ListingDetail;
import 'listing_filters.dart' show ListingOptions;
import 'listing_form.dart';
import 'sell_controller.dart';

/// 매물 등록/수정 화면(7.3 등록 + 7.4 수정). 같은 15필드 폼을 재사용한다.
///   · editDetail == null → 등록 모드(INSERT).
///   · editDetail != null → 수정 모드(UPDATE) — 기존 값으로 폼을 채우고, 성공 시 화면을 닫는다(done).
class SellScreen extends ConsumerStatefulWidget {
  const SellScreen({super.key, this.editDetail, this.showAppBar = true});

  /// 수정 대상 매물 상세(수정 모드일 때만). null 이면 등록 모드.
  final ListingDetail? editDetail;

  /// 하단 4탭 셸의 '내차팔기' 브랜치 루트로 쓰일 때는 셸이 이미 공통 AppBar(제목+프로필
  /// 아바타)를 그리므로 이 화면 자신의 AppBar를 끈다(app_router.dart가 false로 넘긴다).
  /// 기본값 true — my_listings_screen.dart의 "수정" 버튼이 여는 단독 화면(editDetail 채워짐,
  /// EditListingScreen 경유)처럼 단독으로 열릴 때는 뒤로가기가 있는 자기 AppBar가 그대로
  /// 필요하다(후속 코드리뷰 spec-16-8 2차 리뷰 P8 — 홈의 "매물 등록" 퀵액션은 spec-16-8에서
  /// 이미 제거됐다. 지금은 이 기본값을 쓰는 단독 진입점이 "수정" 하나뿐이다).
  final bool showAppBar;

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

  /// 이 화면 인스턴스의 식별자. 공유 sellControllerProvider 의 상태가 "내가 시작한 것"인지
  /// 판정하는 데 쓴다 — editingId 만으로는 부족하다(후속 코드리뷰 spec-16-8 2차 리뷰 P8로
  /// 갱신: "등록 모드 화면이 동시에 둘" 뜨던 옛 경로(go_sell 퀵액션)는 spec-16-8에서 사라졌지만,
  /// '/sell' 탭 루트(등록, editingId=null, IndexedStack으로 영구 마운트)와 my_listings의
  /// "수정" 버튼이 rootNavigator로 여는 수정 화면(editingId=해당 매물 id)이 여전히 같은
  /// sellControllerProvider를 공유한 채 **동시에** 마운트될 수 있다 — 둘의 editingId는
  /// 지금은 다르지만(null vs 실제 id), 우연히 값이 갈리는 데 기대지 않고 인스턴스 식별자로
  /// 명시 구분한다. SellState.owner 주석 참조).
  final Object _owner = Object();

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
    } else {
      // 등록 모드 새 진입 — sellControllerProvider는 하단 4탭 셸의 '/sell' 브랜치가
      // 영구 마운트하는 인스턴스와 같은 것을 공유한다(수정 화면도 이 provider를 쓴다).
      // 그래서 이전에 다른 화면 인스턴스가 남긴 success/error가 이 새 등록 화면에
      // 유령 배너로 새어 보일 수 있다 — 열자마자 지운다(review, spec-16-1 P3). 빌드 중
      // provider 수정은 금지라 위 수정 모드와 같은 방식으로 다음 프레임에 미룬다.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        // 다른 화면의 제출이 진행 중이면 건드리지 않는다 — 무효화하면 새 컨트롤러의
        // loading 이 false 라 그쪽 버튼이 다시 눌려 같은 매물이 두 번 INSERT 될 수 있다
        // (app_router.dart의 탭 활성화 무효화와 같은 이유).
        if (!mounted) return;
        if (ref.read(sellControllerProvider).loading) return;
        ref.invalidate(sellControllerProvider);
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
    // 등록/수정 모드는 항상 이 화면의 생성자 인자(widget.editDetail)로만 정한다 — 컨트롤러의
    // state.editingId로 폴백하지 않는다(spec-16-1). '/sell' 탭이 하단 셸에 영구 마운트되면서
    // sellControllerProvider의 autoDispose가 무력화됐고, 예전엔 submit()이 state.editingId로
    // 폴백해 직전 수정 대상 id가 다음 등록에 새어 UPDATE로 잘못 나갔다(실측된 데이터 손상 버그).
    notifier.submit(editingId: widget.editDetail?.id, owner: _owner);
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
    final isEdit = widget.isEdit;
    final title = isEdit ? '매물 수정' : '매물 등록';

    // ── 게이트: 로그인만 본다(역할 통합, FR52·FR53) ──────────────────
    // 옛 가드는 `role != UserRole.seller`로 막았다 — 웹 14.3이 requireRole(SELLER) →
    // requireUser()로 완화한 것을 앱에 미러링한다. 등록자 본인만 수정/삭제하는 것은
    // 계정 역할이 아니라 소유권(RLS)이 강제한다.
    final blocked = requireUser(ref, title, showAppBar: widget.showAppBar);
    if (blocked != null) return blocked;

    final sell = ref.watch(sellControllerProvider);
    // 이번 상태(성공/에러/진행중)가 "이 화면이 시작한 것"인지 **인스턴스 식별자**로 판정한다.
    // sellControllerProvider가 등록 탭 루트와 수정 화면(my_listings_screen.dart → 이 화면을
    // editDetail 채워 여는 경로) 사이에 공유되므로(등록 탭은 셸 브랜치 영구 마운트, 수정
    // 화면은 그 위에 rootNavigator push라 동시에 마운트될 수 있다), 남의 결과에 반응하면
    // 사고가 난다.
    //
    // ⚠️ 예전엔 editingId로 판정했는데 그걸론 **등록 화면 둘**을 구분하지 못했다(옛 홈
    // 퀵액션 go_sell이 push한 두 번째 등록 화면과 '/sell' 탭 루트 — 둘 다 editingId==null).
    // 실측: 한쪽에서 등록에 성공하면 다른 쪽의 미저장 초안이 지워지고 유령 성공 배너가 떴다
    // (review, spec-16-1 후속 리뷰). go_sell은 spec-16-8에서 제거돼 그 특정 경로는 지금
    // 재현되지 않지만(후속 코드리뷰 spec-16-8 2차 리뷰 P8), 인스턴스 식별자 판정 자체는
    // 등록 탭 루트·수정 화면이 여전히 같은 provider를 동시에 공유한다는 사실 때문에 그대로
    // 필요하다 — editingId가 우연히 갈리는 데(null vs 실제 id) 기대지 않는다.
    final mine = sell.owner != null && sell.owner == _owner;
    // 진행중(loading)도 같은 기준으로 거른다 — 안 그러면 남의 제출이 도는 동안 이 화면의
    // 등록 버튼이 "등록 중…"으로 잠기고, SellController.submit()의 `if (state.loading) return`
    // 때문에 눌러도 아무 일이 안 일어난다(실측 재현).
    final busy = mine && sell.loading;

    if (sell.success != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        // build() 시점에 캡처한 `sell`이 아니라 지금 시점의 최신 상태를 다시 읽는다 —
        // 이 콜백이 실행되기 전에 다른 화면의 제출이 이미 상태를 더 바꿔놨을 수 있다.
        final current = ref.read(sellControllerProvider);
        if (current.success == null) return; // 이미 다른 화면이 소비/초기화했다.
        final currentMine = current.owner != null && current.owner == _owner;
        if (!currentMine) return;
        if (isEdit) {
          // 수정 성공 → 화면을 닫고 목록으로 복귀(true 를 돌려줘 목록이 새로고침하게).
          if (current.done && Navigator.of(context).canPop()) {
            Navigator.of(context).pop(true);
          }
        } else {
          // 등록 성공 → 화면 입력을 비운다(연속 등록 대비).
          if (_model.text.isNotEmpty) _resetFields();
        }
      });
    }

    return Scaffold(
      appBar: widget.showAppBar ? AppBar(title: Text(title)) : null,
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: SingleChildScrollView(
            // 하단 패딩: `viewPadding.bottom`이 아니라 `MediaQuery.paddingOf(context).bottom`을
            // 쓴다 — 탭 루트로 쓰일 때 셸의 NavigationBar가 이미 그 시스템 인셋을 흡수하므로,
            // 원본 viewPadding을 또 더하면 하단 여백이 이중으로 커진다(spec-16-1 Task).
            padding: EdgeInsets.fromLTRB(
              20,
              20,
              20,
              20 + MediaQuery.paddingOf(context).bottom,
            ),
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

                _dropdown(
                  '제조사',
                  'sell_manufacturer',
                  _manufacturer,
                  ListingOptions.manufacturer,
                  (v) => setState(() => _manufacturer = v),
                ),
                const SizedBox(height: 12),
                _text('모델', 'sell_model', _model, hint: '예: 아반떼 CN7'),
                const SizedBox(height: 12),
                _dropdown(
                  '차종',
                  'sell_body_type',
                  _bodyType,
                  ListingOptions.bodyType,
                  (v) => setState(() => _bodyType = v),
                ),
                const SizedBox(height: 12),
                _number('연식 (년)', 'sell_year', _year, hint: '예: 2021'),
                const SizedBox(height: 12),
                _number('가격 (원)', 'sell_price', _price, hint: '예: 29800000'),
                const SizedBox(height: 12),
                _number(
                  '주행거리 (km)',
                  'sell_mileage',
                  _mileage,
                  hint: '예: 103000',
                ),
                const SizedBox(height: 12),
                _dropdown(
                  '색상',
                  'sell_color',
                  _color,
                  ListingOptions.color,
                  (v) => setState(() => _color = v),
                ),
                const SizedBox(height: 12),
                _dropdown(
                  '연료',
                  'sell_fuel',
                  _fuel,
                  ListingOptions.fuel,
                  (v) => setState(() => _fuel = v),
                ),
                const SizedBox(height: 12),
                _dropdown(
                  '변속기',
                  'sell_transmission',
                  _transmission,
                  ListingOptions.transmission,
                  (v) => setState(() => _transmission = v),
                ),
                const SizedBox(height: 12),
                _number(
                  '배기량 (cc)',
                  'sell_displacement',
                  _displacement,
                  hint: '예: 1598 (전기차는 0)',
                ),
                const SizedBox(height: 12),
                _number('인승 (명)', 'sell_seats', _seats, hint: '예: 5'),
                const SizedBox(height: 12),
                _dropdown(
                  '지역',
                  'sell_region',
                  _region,
                  ListingOptions.region,
                  (v) => setState(() => _region = v),
                ),
                const SizedBox(height: 12),

                SwitchListTile(
                  key: const Key('sell_accident_free'),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('무사고 차량'),
                  value: _accidentFree,
                  onChanged: busy
                      ? null
                      : (v) => setState(() => _accidentFree = v),
                ),

                _text(
                  '옵션 (쉼표로 구분, 선택)',
                  'sell_options',
                  _options,
                  hint: '예: 선루프, 후방카메라, 내비게이션',
                ),
                const SizedBox(height: 12),
                _text(
                  '설명 (선택)',
                  'sell_description',
                  _description,
                  hint: '차량 상태·이력 등을 자유롭게',
                  maxLines: 3,
                ),
                const SizedBox(height: 16),

                // `mine`이 아닌 error/success는 안 그린다 — 등록 탭 루트와 수정 화면이
                // sellControllerProvider를 공유하므로, 안 걸러내면 남의(다른 editingId)
                // 결과 배너가 이 화면에도 유령처럼 보인다(review, spec-16-1 P3).
                if (mine && sell.error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      sell.error!,
                      key: const Key('sell_error'),
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ),
                if (mine && sell.success != null)
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
                  onPressed: busy ? null : _submit,
                  child: Text(
                    busy
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
  Widget _text(
    String label,
    String keyName,
    TextEditingController c, {
    String? hint,
    int maxLines = 1,
  }) {
    return TextField(
      key: Key(keyName),
      controller: c,
      maxLines: maxLines,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        isDense: true,
      ),
    );
  }

  Widget _number(
    String label,
    String keyName,
    TextEditingController c, {
    String? hint,
  }) {
    return TextField(
      key: Key(keyName),
      controller: c,
      keyboardType: TextInputType.number,
      // 숫자만 입력 가능(소수점·부호 차단) — 정수 저장 규칙을 입력 단계부터 돕는다.
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        isDense: true,
      ),
    );
  }

  Widget _dropdown(
    String label,
    String keyName,
    String? value,
    List<String> options,
    ValueChanged<String?> onChanged,
  ) {
    return DropdownButtonFormField<String?>(
      key: Key(keyName),
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        const DropdownMenuItem<String?>(value: null, child: Text('선택')),
        ...options.map(
          (o) => DropdownMenuItem<String?>(value: o, child: Text(o)),
        ),
      ],
      onChanged: onChanged,
    );
  }
}
