// 매물 필터 — 드롭다운 옵션(단일 출처 미러)과 입력 검증 로직(web search/page.tsx 이식).
//
// ⚠️ 옵션 목록은 web lib/constants.ts LISTING_OPTIONS = supabase 0002_listings CHECK 와 "바이트 일치".
//    값·순서·문자를 그대로 복사한다. 어긋나면(drift) 고른 값이 DB CHECK 에 걸려 0건이 된다.
//
// 검증 함수들은 순수 함수(부수효과 없음)라 단위 테스트로 회귀를 빠르게 잡는다.

/// 매물 고정 목록 필드의 허용값(드롭다운 옵션). web LISTING_OPTIONS 미러.
class ListingOptions {
  static const List<String> bodyType = [
    '경차', '소형차', '준중형차', '중형차', '대형차', '스포츠카',
    'SUV', 'RV', '경승합차', '승합차', '화물차', '기타',
  ];
  static const List<String> color = [
    '흰색', '검정', '회색', '은색', '파랑', '빨강', '갈색', '녹색', '기타',
  ];
  static const List<String> fuel = ['가솔린', '디젤', '하이브리드', '전기', 'LPG'];
  static const List<String> transmission = ['자동', '수동'];
  static const List<String> region = [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
  ];
}

/// "목록에 있는 값일 때만" 통과시킨다(목록 밖 임의 값은 무시 → 쿼리 오염 방지). 빈 값이면 null(미적용).
/// web pickOption 이식.
String? pickOption(String? v, List<String> options) {
  if (v == null) return null;
  final s = v.trim();
  return s.isNotEmpty && options.contains(s) ? s : null;
}

/// 정수 파싱 — "순수 숫자열"일 때만 통과(미적용이면 null). web asInt 이식.
///   부호·소수점·지수·16진은 모두 거른다. 안전 정수(2^53-1) 이하만 — bigint 범위 초과 조회에러 방지.
int? parseIntFilter(String? v) {
  if (v == null) return null;
  final s = v.trim();
  if (s.isEmpty) return null;
  if (!RegExp(r'^\d+$').hasMatch(s)) return null; // 순수 숫자열만.
  final n = int.tryParse(s);
  if (n == null) return null;
  // JS Number.MAX_SAFE_INTEGER 와 같은 상한(9007199254740991). web 동작과 일치.
  if (n > 9007199254740991) return null;
  return n;
}

/// LIKE 패턴 메타문자(\ % _)를 이스케이프 — 사용자가 친 '%'·'_'를 "그 글자 자체"로 검색하게 한다.
/// 안 하면 '%' 입력이 "전부 일치"가 돼 키워드 필터가 무력화된다. web escapeLike 이식.
String escapeLike(String s) {
  return s.replaceAllMapped(RegExp(r'[\\%_]'), (m) => '\\${m[0]}');
}

/// 화면에서 모은 필터 입력값(원문 문자열). 검색 버튼을 누르면 ResolvedFilters 로 정규화한다.
class ListingFilterInput {
  const ListingFilterInput({
    this.keyword = '',
    this.bodyType,
    this.color,
    this.fuel,
    this.transmission,
    this.region,
    this.priceMin = '',
    this.priceMax = '',
    this.yearMin = '',
    this.yearMax = '',
  });

  final String keyword; // 모델명 부분일치
  final String? bodyType;
  final String? color;
  final String? fuel;
  final String? transmission;
  final String? region;
  final String priceMin;
  final String priceMax;
  final String yearMin;
  final String yearMax;
}

/// 검증·정규화된 필터(레포가 쿼리에 그대로 적용). min>max 는 swap 으로 보정된 상태.
class ResolvedFilters {
  const ResolvedFilters({
    this.keyword,
    this.bodyType,
    this.color,
    this.fuel,
    this.transmission,
    this.region,
    this.priceMin,
    this.priceMax,
    this.yearMin,
    this.yearMax,
  });

  final String? keyword; // 이미 escapeLike 적용된 패턴 본문(없으면 null)
  final String? bodyType;
  final String? color;
  final String? fuel;
  final String? transmission;
  final String? region;
  final int? priceMin;
  final int? priceMax;
  final int? yearMin;
  final int? yearMax;

  /// 입력 → 검증·정규화. web SearchPage 의 파싱부(pickOption·asInt·swap·escapeLike)를 한 곳에 모은다.
  factory ResolvedFilters.fromInput(ListingFilterInput input) {
    final kw = input.keyword.trim();
    var priceMin = parseIntFilter(input.priceMin);
    var priceMax = parseIntFilter(input.priceMax);
    var yearMin = parseIntFilter(input.yearMin);
    var yearMax = parseIntFilter(input.yearMax);

    // 최소>최대로 거꾸로 입력하면 0건이 나와 혼란 → 둘 다 유효할 때만 swap 해 정상 범위로 보정.
    if (priceMin != null && priceMax != null && priceMin > priceMax) {
      final t = priceMin;
      priceMin = priceMax;
      priceMax = t;
    }
    if (yearMin != null && yearMax != null && yearMin > yearMax) {
      final t = yearMin;
      yearMin = yearMax;
      yearMax = t;
    }

    return ResolvedFilters(
      keyword: kw.isNotEmpty ? escapeLike(kw) : null,
      bodyType: pickOption(input.bodyType, ListingOptions.bodyType),
      color: pickOption(input.color, ListingOptions.color),
      fuel: pickOption(input.fuel, ListingOptions.fuel),
      transmission: pickOption(input.transmission, ListingOptions.transmission),
      region: pickOption(input.region, ListingOptions.region),
      priceMin: priceMin,
      priceMax: priceMax,
      yearMin: yearMin,
      yearMax: yearMax,
    );
  }
}
