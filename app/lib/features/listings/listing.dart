// 매물 데이터 모델 — 목록 카드(요약 7필드)와 상세(15필드+메타)를 표현한다.
// 현재 사진 렌더 없음(image_url 계약 자리는 예약, 값 채움·표시는 Epic 9). DB·JSON 키는 snake_case 그대로 읽는다(통신선 통일, 변환 없음).
//   (web ListingCardData 7필드 계약과 동일: id·manufacturer·model·year·price·mileage·region)
//
// fromMap 은 Supabase select 결과(Map<String,dynamic>) 또는 /ai/search 응답 원소를 받는다.
// 숫자는 int/double/문자열 어느 형태로 와도 안전하게 int 로 바꾼다(서버·드라이버 차이 흡수).

/// 숫자 필드를 안전하게 int 로. null·문자열·double 어떤 형태든 흡수, 실패 시 null.
/// public(밑줄 없음) — `listings_repository.dart`가 `listing_images.sort_order` 파싱에도
/// 재사용한다(계약값 coercion 로직을 두 곳에 따로 두지 않는다, 이 파일과 같은 방어 원칙).
int? asInt(Object? v) {
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
    this.imagePath,
    this.viewCount,
    this.imageCount,
    this.fuel,
    this.accidentStatus,
    this.isSingleOwner,
    this.isNonSmoker,
    this.options,
  });

  final String id;
  final String manufacturer;
  final String model;
  final int year;
  final int price; // 원(KRW)
  final int mileage; // km
  final String region;
  final String? sellerName; // 판매자 표시 이름(0007 비정규화). AI 결과 등 없으면 미표시.
  // 증분 신규 — 전부 nullable(값 채움은 후속 에픽)
  final String? imageUrl; // 대표 사진의 공개 URL. null이면 "사진 준비중" 플레이스홀더 — Epic 9
  // 대표 사진의 **버킷 상대 경로**(`{user_id}/{listing_id}/{filename}`) — AI 응답(/ai/search) 전용.
  // api는 URL을 만들지 않으므로(conventions.md §10) `image_url` 대신 이 필드가 채워져 온다.
  //
  // Story 16.2가 이 변환을 실제로 구현했다: `ai_search_api.dart`의 `parseSearchResult`가
  // `image_path`를 받아 공개 URL로 바꿔 `image_url` 자리에 넣고, `fromMap`에는 경로 자체를
  // 넘기지 않는다(web `aiSearch.ts`의 `resolveCardImage` 미러). 그 결과 이 `imagePath` 필드는
  // **앱 코드 어디에서도 채워지지 않는다** — Supabase 직접 조회 경로도 안 채우고, AI 응답
  // 경로도 매핑 단계에서 바로 소비해 버려서 안 채운다. 그런데도 남겨 두는 이유는 순전히
  // conventions.md §4.1 계약 락스텝(web `ListingCardData`와 필드 형태를 맞춘다) 때문이다.
  //
  // ⚠️ (✎ 2026-07-20 코드리뷰 정정, 지금도 유효한 방향) 변환은 **응답 매핑 계층에서 한 번**
  //    일어나야지, 렌더 시점에 카드가 경로를 들고 있다가 바꾸면 안 된다 — 그러면 web과 다른
  //    구조가 되고, 그게 §4.1 락스텝이 애초에 막으려던 드리프트다.
  final String? imagePath;
  final int? viewCount; // Epic 11
  final int? imageCount; // Epic 9
  final String? fuel; // 연료(가솔린/디젤/하이브리드/전기/LPG) — Epic 10(10.1), 대장 #67
  final String? accidentStatus; // '무사고'|'단순교환'|'사고'|null — Dart는 별도 enum 없이 nullable String으로 단순 통과(A2). Epic 10(10.1 컬럼 생성)
  final bool? isSingleOwner; // Epic 10(10.1 컬럼 생성)
  final bool? isNonSmoker; // Epic 10(10.1 컬럼 생성)
  // 장비 통제어휘 배열(text[]) — Epic 10(10.3), docs/conventions.md §11.
  // ⚠️ 타입 파리티만이다 — 칩 위젯 렌더·app `options.ts` 상수 미러는 Epic 16(10.1 선례와 동일).
  final List<String>? options;

  /// Map(Supabase row 또는 /ai/search 원소) → 카드. 7필드가 올바른 타입이 아니면 null(깨진 원소 제외).
  /// web aiSearch.ts 의 isValidListing 런타임 가드와 같은 목적 — 카드 렌더 도중 터지는 것을 막는다.
  static ListingCardData? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final region = raw['region'];
    final year = asInt(raw['year']);
    final price = asInt(raw['price']);
    final mileage = asInt(raw['mileage']);

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
    final imageUrl = raw['image_url'] is String ? raw['image_url'] as String : null;
    // "url 없으면 count도 0" — 모든 생산자(Supabase 직접 조회·AI 응답 매핑 등)가 카드를 만들 때
    // 반드시 이 fromMap을 지나므로, 이 한 곳에서만 강제하면 새 생산자가 생겨도 놓칠 수 없다(B9).
    final rawImageCount = asInt(raw['image_count']);
    final imageCount = (imageUrl == null || imageUrl.trim().isEmpty) ? 0 : rawImageCount;
    return ListingCardData(
      id: id,
      manufacturer: manufacturer,
      model: model,
      year: year,
      price: price,
      mileage: mileage,
      region: region,
      sellerName: sellerName is String ? sellerName : null,
      imageUrl: imageUrl,
      imagePath: raw['image_path'] is String ? raw['image_path'] as String : null,
      viewCount: asInt(raw['view_count']),
      imageCount: imageCount,
      fuel: raw['fuel'] is String ? raw['fuel'] as String : null,
      accidentStatus: raw['accident_status'] is String ? raw['accident_status'] as String : null,
      isSingleOwner: raw['is_single_owner'] is bool ? raw['is_single_owner'] as bool : null,
      isNonSmoker: raw['is_non_smoker'] is bool ? raw['is_non_smoker'] as bool : null,
      options: _asStringList(raw['options']),
    );
  }
}

/// options(text[])를 `List<String>?`으로 안전 변환. 리스트가 아니거나 원소가 문자열이 아니면
/// null로 강등한다(계약-외 값 정규화, api `rows_to_cards`와 같은 방어 원칙).
List<String>? _asStringList(Object? v) {
  if (v is! List) return null;
  final result = <String>[];
  for (final item in v) {
    if (item is! String) return null;
    result.add(item);
  }
  return result;
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
    final year = asInt(raw['year']);
    final price = asInt(raw['price']);

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
    this.imageUrls = const [],
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
  // 상세 갤러리 전체 URL(공개 URL, sort_order·id 순). `listings` 단일 row엔 없는 데이터라
  // fromMap이 채우지 않는다 — `listing_images` 별도 조회 후 withImages로 부착한다(Story 16.2).
  final List<String> imageUrls;

  /// `listing_images` 조회 결과(공개 URL 리스트)를 부착한 새 인스턴스를 만든다.
  /// fromMap이 읽는 단일 `listings` row엔 없는 데이터라 부착 지점이 별도로 필요하다.
  ListingDetail withImages(List<String> urls) => ListingDetail(
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
        sellerName: sellerName,
        options: options,
        description: description,
        imageUrls: urls,
      );

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
    final year = asInt(raw['year']);
    final price = asInt(raw['price']);
    final mileage = asInt(raw['mileage']);
    final displacement = asInt(raw['displacement']);
    final seats = asInt(raw['seats']);

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
