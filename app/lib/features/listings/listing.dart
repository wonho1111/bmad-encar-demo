// 매물 데이터 모델 — 목록 카드(요약 7필드)와 상세(15필드+메타)를 표현한다.
// 현재 사진 렌더 없음(image_url 계약 자리는 예약, 값 채움·표시는 Epic 9). DB·JSON 키는 snake_case 그대로 읽는다(통신선 통일, 변환 없음).
//   (web ListingCardData 7필드 계약과 동일: id·manufacturer·model·year·price·mileage·region)
//
// fromMap 은 Supabase select 결과(Map<String,dynamic>) 또는 /ai/search 응답 원소를 받는다.
// 숫자는 int/double/문자열 어느 형태로 와도 안전하게 int 로 바꾼다(서버·드라이버 차이 흡수).

/// 숫자 필드를 안전하게 int 로. null·문자열·double 어떤 형태든 흡수, 실패 시 null.
int? _asInt(Object? v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is double) return v.toInt();
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v.trim());
  return null;
}

/// 매물 목록 카드(요약 7필드). web ListingCardData 와 동일 계약.
/// AI 검색 결과 카드도 이 타입을 공유한다(매물카드 위젯 1개로 재사용).
class ListingCardData {
  const ListingCardData({
    required this.id,
    required this.manufacturer,
    required this.model,
    required this.year,
    required this.price,
    required this.mileage,
    required this.region,
    this.sellerName,
    this.imageUrl,
    this.viewCount,
    this.imageCount,
    this.accidentStatus,
    this.isSingleOwner,
    this.isNonSmoker,
  });

  final String id;
  final String manufacturer;
  final String model;
  final int year;
  final int price; // 원(KRW)
  final int mileage; // km
  final String region;
  final String? sellerName; // 판매자 표시 이름(0007 비정규화). AI 결과 등 없으면 미표시.
  // 증분 신규 — 전부 nullable(DB 컬럼 아직 없음, 값 채움은 후속 에픽)
  final String? imageUrl; // 대표 사진의 공개 URL. null이면 "사진 준비중" 플레이스홀더 — Epic 9
  final int? viewCount; // Epic 11
  final int? imageCount; // Epic 9
  final String? accidentStatus; // '무사고'|'단순교환'|'사고'|null — Dart는 별도 enum 없이 nullable String으로 단순 통과(A2). Epic 10
  final bool? isSingleOwner; // Epic 10
  final bool? isNonSmoker; // Epic 10

  /// Map(Supabase row 또는 /ai/search 원소) → 카드. 7필드가 올바른 타입이 아니면 null(깨진 원소 제외).
  /// web aiSearch.ts 의 isValidListing 런타임 가드와 같은 목적 — 카드 렌더 도중 터지는 것을 막는다.
  static ListingCardData? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final region = raw['region'];
    final year = _asInt(raw['year']);
    final price = _asInt(raw['price']);
    final mileage = _asInt(raw['mileage']);

    if (id is! String ||
        manufacturer is! String ||
        model is! String ||
        region is! String ||
        year == null ||
        price == null ||
        mileage == null) {
      return null; // 계약 위반 원소는 버린다(나머지는 정상 표시).
    }

    final sellerName = raw['seller_name'];
    return ListingCardData(
      id: id,
      manufacturer: manufacturer,
      model: model,
      year: year,
      price: price,
      mileage: mileage,
      region: region,
      sellerName: sellerName is String ? sellerName : null,
      imageUrl: raw['image_url'] is String ? raw['image_url'] as String : null,
      viewCount: _asInt(raw['view_count']),
      imageCount: _asInt(raw['image_count']),
      accidentStatus: raw['accident_status'] is String ? raw['accident_status'] as String : null,
      isSingleOwner: raw['is_single_owner'] is bool ? raw['is_single_owner'] as bool : null,
      isNonSmoker: raw['is_non_smoker'] is bool ? raw['is_non_smoker'] as bool : null,
    );
  }
}

/// 본인 매물 관리 목록의 한 행(요약 6필드). web `OwnListing`(sell/page.tsx) 미러.
/// 구매자 카드(ListingCardData)와 달리 status 를 포함한다 — 판매중/판매완료 배지·동작 분기에 쓰기 때문.
/// (본인 매물이라 sold 도 보여야 하므로 status 필수.)
class OwnListing {
  const OwnListing({
    required this.id,
    required this.manufacturer,
    required this.model,
    required this.year,
    required this.price,
    required this.status,
  });

  final String id;
  final String manufacturer;
  final String model;
  final int year;
  final int price; // 원(KRW)
  final String status; // on_sale=판매중 / sold=판매완료(0002 CHECK)

  /// Supabase row → 본인 매물 행. 필수 6필드가 깨졌으면 null(그 행만 제외).
  static OwnListing? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final status = raw['status'];
    final year = _asInt(raw['year']);
    final price = _asInt(raw['price']);

    if (id is! String ||
        manufacturer is! String ||
        model is! String ||
        status is! String ||
        year == null ||
        price == null) {
      return null;
    }
    return OwnListing(
      id: id,
      manufacturer: manufacturer,
      model: model,
      year: year,
      price: price,
      status: status,
    );
  }
}

/// 매물 상세(FR5 15필드 + 상태·판매자·옵션·설명). 사진 없음.
class ListingDetail {
  const ListingDetail({
    required this.id,
    required this.sellerId,
    required this.manufacturer,
    required this.model,
    required this.bodyType,
    required this.year,
    required this.price,
    required this.mileage,
    required this.color,
    required this.fuel,
    required this.transmission,
    required this.displacement,
    required this.seats,
    required this.region,
    required this.accidentFree,
    required this.status,
    this.sellerName,
    this.options,
    this.description,
  });

  final String id;
  final String sellerId; // 매물주. 본인이면 향후 문의 버튼 숨김(7.5).
  final String manufacturer;
  final String model;
  final String bodyType;
  final int year;
  final int price; // 원
  final int mileage; // km
  final String color;
  final String fuel;
  final String transmission;
  final int displacement; // cc
  final int seats;
  final String region;
  final bool accidentFree;
  final String status; // on_sale(상세는 on_sale 만 도달)
  final String? sellerName;
  final List<String>? options; // text[]; 비거나 null 가능
  final String? description;

  /// Supabase row → 상세. 필수 필드가 빠지면 null(못 찾음으로 처리).
  static ListingDetail? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final sellerId = raw['seller_id'];
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final bodyType = raw['body_type'];
    final color = raw['color'];
    final fuel = raw['fuel'];
    final transmission = raw['transmission'];
    final region = raw['region'];
    final status = raw['status'];
    final accidentFree = raw['accident_free'];
    final year = _asInt(raw['year']);
    final price = _asInt(raw['price']);
    final mileage = _asInt(raw['mileage']);
    final displacement = _asInt(raw['displacement']);
    final seats = _asInt(raw['seats']);

    if (id is! String ||
        sellerId is! String ||
        manufacturer is! String ||
        model is! String ||
        bodyType is! String ||
        color is! String ||
        fuel is! String ||
        transmission is! String ||
        region is! String ||
        status is! String ||
        // accident_free 는 DB 가 NOT NULL bool(0002_listings) — 안 오거나 타입이 깨졌으면
        // "무사고" 로 단정하지 않고(중고차에선 오해 소지) 못 찾음으로 처리한다(보수적 기본값).
        accidentFree is! bool ||
        year == null ||
        price == null ||
        mileage == null ||
        displacement == null ||
        seats == null) {
      return null;
    }

    final rawOptions = raw['options'];
    final options = rawOptions is List
        ? rawOptions.whereType<String>().toList()
        : null;
    final sellerName = raw['seller_name'];
    final description = raw['description'];

    return ListingDetail(
      id: id,
      sellerId: sellerId,
      manufacturer: manufacturer,
      model: model,
      bodyType: bodyType,
      year: year,
      price: price,
      mileage: mileage,
      color: color,
      fuel: fuel,
      transmission: transmission,
      displacement: displacement,
      seats: seats,
      region: region,
      accidentFree: accidentFree,
      status: status,
      sellerName: sellerName is String ? sellerName : null,
      options: options,
      description: description is String ? description : null,
    );
  }
}
