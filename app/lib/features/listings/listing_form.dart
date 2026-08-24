// 매물 등록 폼(7.3, FR5 재현) — 입력 모델 + 검증·페이로드 빌드 "순수 함수".
//
// 왜 순수 함수로 빼나: 부수효과(네트워크·setState)가 없어 단위 테스트로 회귀를 빠르게 잡는다.
//   (7.2 listing_filters.dart 의 parseIntFilter·pickOption 과 같은 전략.)
//
// 검증 규칙·한국어 메시지·페이로드 모양은 web SellForm.tsx 의 validateAndBuild 를 그대로 이식했다.
//   · 고정 6필드(제조사·차종·색상·연료·변속기·지역)는 드롭다운 단일출처(ListingOptions) → 목록 밖 값 불가.
//   · 수치 5필드(연식·가격·주행·배기량·인승)는 정수·범위를 클라이언트가 먼저 거른다(DB CHECK 도달 전 차단).
//   · 통신선/DB 와 일치하도록 페이로드 키는 snake_case, 단위는 정수(원·km·cc).
//   · status='on_sale' 동봉(DB 기본값과 같지만 web 처럼 의도 명시 — 즉시 노출 FR7).
//
// 단일 출처(drift 금지): 15필드·CHECK 목록·범위의 원천은 supabase/migrations/0002_listings.sql.

import 'listing.dart' show ListingDetail;
import 'listing_filters.dart' show ListingOptions;

/// 매물 수치 필드 허용 범위 — web LISTING_RANGES 미러(= 0002 CHECK).
/// year 상한은 하드코딩하지 않고 "올해+1"(신차년식)로 계산 — DB CHECK `extract(year from now())::int + 1` 과 일치.
class ListingRanges {
  static const int yearMin = 1990;

  /// 연식 상한 = 올해 + 1(신차년식). 해가 바뀌어도 자동으로 맞는다.
  static int get yearMax => DateTime.now().year + 1;

  static const int seatsMin = 2;
  static const int seatsMax = 11;

  // price·mileage·displacement 는 0 이상(음수 불가). 상한은 DB(int/bigint)에 위임.
  static const int priceMin = 0;
  static const int mileageMin = 0;
  static const int displacementMin = 0;
}

/// 등록 폼의 현재 입력값. 수치는 "문자열"로 보관한다(빈칸과 0 을 구분하기 위함 — web FormState 동일).
class ListingFormInput {
  const ListingFormInput({
    this.manufacturer = '',
    this.model = '',
    this.bodyType = '',
    this.year = '',
    this.price = '',
    this.mileage = '',
    this.color = '',
    this.fuel = '',
    this.transmission = '',
    this.displacement = '',
    this.seats = '',
    this.region = '',
    // ✎ 2026-08-13 — 신뢰속성 3개를 폼이 직접 받는다(web SellForm과 같은 계약).
    //   예전엔 `accidentFree`(bool, 기본 true) 하나뿐이었다: 상세·카드가 뱃지로 보여주는
    //   accident_status·is_single_owner·is_non_smoker를 **앱에서는 넣을 방법이 아예 없었고**,
    //   기본이 true라 아무것도 안 건드리고 등록하면 자동으로 "무사고"로 신고됐다.
    //   `accidentFree`는 이제 폼 입력이 아니라 accidentStatus에서 **파생**한다(buildListingPayload).
    this.accidentStatus = '', // ''(미선택) | 무사고 | 단순교환 | 사고 — 필수
    this.isSingleOwner = false, // 체크=신고함(true). 미체크는 false가 아니라 **null(미신고)** 로 저장.
    this.isNonSmoker = false, // 위와 같음
    this.options = '', // 쉼표 구분 입력 → 배열 변환.
    this.description = '',
  });

  final String manufacturer;
  final String model;
  final String bodyType;
  final String year;
  final String price;
  final String mileage;
  final String color;
  final String fuel;
  final String transmission;
  final String displacement;
  final String seats;
  final String region;
  final String accidentStatus;
  final bool isSingleOwner;
  final bool isNonSmoker;
  final String options;
  final String description;

  /// 기존 매물 상세 → 수정 폼 입력값 역변환(7.4 수정 화면용).
  /// 등록 폼은 수치를 "문자열"로 보관하므로 정수→문자열, options 배열→쉼표 문자열로 되돌린다.
  /// status·seller_id 는 폼에서 다루지 않으므로 가져오지 않는다(수정 범위 밖 — 상태 전환은 구매완료 별도 동작).
  factory ListingFormInput.fromDetail(ListingDetail d) {
    return ListingFormInput(
      manufacturer: d.manufacturer,
      model: d.model,
      bodyType: d.bodyType,
      year: d.year.toString(),
      price: d.price.toString(),
      mileage: d.mileage.toString(),
      color: d.color,
      fuel: d.fuel,
      transmission: d.transmission,
      displacement: d.displacement.toString(),
      seats: d.seats.toString(),
      region: d.region,
      // NULL(미상)은 체크 해제로 되돌린다 — 저장 때 다시 null로 나가므로 왕복해도 "아니오"가 되지 않는다.
      accidentStatus: d.accidentStatus ?? '',
      isSingleOwner: d.isSingleOwner == true,
      isNonSmoker: d.isNonSmoker == true,
      // 옵션 배열 → 쉼표 구분 문자열(등록 폼이 다시 쉼표로 split 하므로 왕복 일관).
      options: (d.options ?? const <String>[]).join(', '),
      description: d.description ?? '',
    );
  }

  ListingFormInput copyWith({
    String? manufacturer,
    String? model,
    String? bodyType,
    String? year,
    String? price,
    String? mileage,
    String? color,
    String? fuel,
    String? transmission,
    String? displacement,
    String? seats,
    String? region,
    String? accidentStatus,
    bool? isSingleOwner,
    bool? isNonSmoker,
    String? options,
    String? description,
  }) {
    return ListingFormInput(
      manufacturer: manufacturer ?? this.manufacturer,
      model: model ?? this.model,
      bodyType: bodyType ?? this.bodyType,
      year: year ?? this.year,
      price: price ?? this.price,
      mileage: mileage ?? this.mileage,
      color: color ?? this.color,
      fuel: fuel ?? this.fuel,
      transmission: transmission ?? this.transmission,
      displacement: displacement ?? this.displacement,
      seats: seats ?? this.seats,
      region: region ?? this.region,
      accidentStatus: accidentStatus ?? this.accidentStatus,
      isSingleOwner: isSingleOwner ?? this.isSingleOwner,
      isNonSmoker: isNonSmoker ?? this.isNonSmoker,
      options: options ?? this.options,
      description: description ?? this.description,
    );
  }
}

/// 검증 결과 — 성공이면 INSERT 페이로드(Map), 실패면 사용자용 한국어 message.
/// (web validateAndBuild 의 {ok:true,payload} | {ok:false,message} 와 동일 모양.)
class ListingFormResult {
  const ListingFormResult.ok(this.payload)
      : message = null,
        isOk = true;
  const ListingFormResult.error(this.message)
      : payload = null,
        isOk = false;

  final bool isOk;
  final Map<String, dynamic>? payload; // snake_case, 정수 변환된 INSERT 페이로드(성공 시).
  final String? message; // 한국어 검증 오류(실패 시).
}

/// "순수 숫자열"만 정수로(부호·소수·지수·16진 거름). 빈 값/형식 위반은 null.
/// 정수만 저장(AC2)을 폼이 보장 — DB int/bigint 에 소수를 보내면 일반 에러로만 떨어지므로 여기서 먼저 막는다.
int? _strictInt(String raw) {
  final s = raw.trim();
  if (s.isEmpty) return null;
  if (!RegExp(r'^\d+$').hasMatch(s)) return null;
  return int.tryParse(s);
}

/// 폼 입력 → 검증·정규화 → INSERT 페이로드. 부수효과 없음(테스트 친화).
/// web SellForm.validateAndBuild 규칙·메시지를 그대로 이식했다.
ListingFormResult validateAndBuildListing(ListingFormInput form) {
  // ── 필수 텍스트/드롭다운(빈값 거절) ──────────────────────────────
  if (form.manufacturer.isEmpty) {
    return const ListingFormResult.error('제조사를 선택해주세요.');
  }
  if (form.model.trim().isEmpty) {
    return const ListingFormResult.error('모델명을 입력해주세요.');
  }
  if (form.bodyType.isEmpty) {
    return const ListingFormResult.error('차종을 선택해주세요.');
  }
  if (form.color.isEmpty) {
    return const ListingFormResult.error('색상을 선택해주세요.');
  }
  if (form.fuel.isEmpty) {
    return const ListingFormResult.error('연료를 선택해주세요.');
  }
  if (form.transmission.isEmpty) {
    return const ListingFormResult.error('변속기를 선택해주세요.');
  }
  if (form.region.isEmpty) {
    return const ListingFormResult.error('지역을 선택해주세요.');
  }
  // 사고이력은 **필수**다(2026-08-13, web과 같은 규칙). 예전엔 기본 켜진 스위치라
  // "안 고른 상태"가 곧 "무사고 신고"였다 — 판매자가 명시적으로 고르게 한다.
  if (form.accidentStatus.isEmpty) {
    return const ListingFormResult.error('사고이력을 선택해주세요.');
  }

  // ── 드롭다운 값이 정말 목록 안인지 한 번 더(방어) ────────────────
  // UI 가 ListingOptions 로만 채우므로 정상 경로에선 통과하나, 목록 밖 값이 흘러들면 DB CHECK 전에 막는다.
  if (!ListingOptions.manufacturer.contains(form.manufacturer)) {
    return const ListingFormResult.error('제조사 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.bodyType.contains(form.bodyType)) {
    return const ListingFormResult.error('차종 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.color.contains(form.color)) {
    return const ListingFormResult.error('색상 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.fuel.contains(form.fuel)) {
    return const ListingFormResult.error('연료 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.transmission.contains(form.transmission)) {
    return const ListingFormResult.error('변속기 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.accidentStatus.contains(form.accidentStatus)) {
    return const ListingFormResult.error('사고이력 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }
  if (!ListingOptions.region.contains(form.region)) {
    return const ListingFormResult.error('지역 선택값이 올바르지 않습니다. 목록에서 다시 선택해주세요.');
  }

  // ── 수치(정수 변환 + 범위 검증) ─────────────────────────────────
  final year = _strictInt(form.year);
  if (year == null || year < ListingRanges.yearMin || year > ListingRanges.yearMax) {
    return ListingFormResult.error(
      '연식은 ${ListingRanges.yearMin}~${ListingRanges.yearMax}년 사이의 정수로 입력해주세요.',
    );
  }
  final price = _strictInt(form.price);
  if (price == null || price < ListingRanges.priceMin) {
    return const ListingFormResult.error('가격은 0원 이상의 정수로 입력해주세요(소수점 불가).');
  }
  final mileage = _strictInt(form.mileage);
  if (mileage == null || mileage < ListingRanges.mileageMin) {
    return const ListingFormResult.error('주행거리는 0km 이상의 정수로 입력해주세요(소수점 불가).');
  }
  final displacement = _strictInt(form.displacement);
  if (displacement == null || displacement < ListingRanges.displacementMin) {
    return const ListingFormResult.error('배기량은 0cc 이상의 정수로 입력해주세요(전기차는 0, 소수점 불가).');
  }
  final seats = _strictInt(form.seats);
  if (seats == null || seats < ListingRanges.seatsMin || seats > ListingRanges.seatsMax) {
    return ListingFormResult.error(
      '인승은 ${ListingRanges.seatsMin}~${ListingRanges.seatsMax}명 사이의 정수로 입력해주세요.',
    );
  }

  // ── options: 쉼표 구분 → trim → 빈 항목 제외 배열(text[]) ─────────
  final options = form.options
      .split(',')
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toList();

  // ── 설명: trim 후 빈값이면 null(웹 동일) ────────────────────────
  final desc = form.description.trim();
  final description = desc.isEmpty ? null : desc;

  return ListingFormResult.ok({
    'manufacturer': form.manufacturer,
    'model': form.model.trim(),
    'body_type': form.bodyType,
    'year': year, // 정수
    'price': price, // 원(정수)
    'mileage': mileage, // km(정수)
    'color': form.color,
    'fuel': form.fuel,
    'transmission': form.transmission,
    'displacement': displacement, // cc(정수)
    'seats': seats, // 정수
    'region': form.region,
    'accident_status': form.accidentStatus,
    // `accident_free`는 **파생값**이다(2026-08-13, web SellForm과 같은 규칙).
    //   컬럼을 안 지우는 이유: AI 검색이 이걸 쓴다(api/app/graph/sql_rag_node.py 지시문 —
    //   "사고 관련 질문은 accident_status가 아니라 accident_free로 판단하라"). 없애면
    //   "무사고 차 추천해줘"가 깨진다. 그래서 남기고 자동으로 채운다.
    //   ⚠️ 앱이 이 파생을 안 하면 **웹 필터(accident_status 기준)와 AI 검색(accident_free 기준)이
    //   서로 다른 결과를 내는 행**이 앱 등록마다 쌓인다 — 그게 이 줄이 존재하는 이유다.
    'accident_free': form.accidentStatus == '무사고',
    // 미체크는 false가 아니라 null(미신고). false는 "1인소유가 아니다"라는 신고인데
    // 판매자는 아무 말도 하지 않았다(0017이 못박은 3상태 규칙).
    'is_single_owner': form.isSingleOwner ? true : null,
    'is_non_smoker': form.isNonSmoker ? true : null,
    'options': options, // text[]
    'description': description, // null 가능
    'status': 'on_sale', // 즉시 노출(기본값과 같으나 의도 명시 — FR7)
  });
}
