// 옵션 통제어휘·우선순위 — web `web/src/lib/options.ts` 미러(spec-16-9 Code Map, DW-760 해소).
// 정본: docs/conventions.md §11(카테고리 배치·티어·71개 통제어휘). 값을 바꾸려면 그 문서를
// 먼저 고친다.
//
// 카드 옵션 칩 선택(topOptions)의 유일한 로직 출처 — `listing_card.dart`가 이 모듈만 쓴다.
// web은 카테고리별 전량 그룹핑(groupByCategory)·인기 8종(POPULAR_OPTIONS)·통제어휘 검증
// (partitionOptions) 등도 갖지만, 이 스토리는 카드 축(topOptions/optionPriority)만 교정
// 대상이라 그 나머지는 포트하지 않는다(A2 — 안 쓰는 로직을 미리 옮기지 않는다).

/// 통제어휘 전체 — `optionPriority`의 known/unknown 판정 기준(conventions §11.1, 71개).
/// web `CONTROLLED_OPTIONS`(카테고리별 배열)를 평평하게 합친 것과 동일 집합이다 — 이 스토리는
/// 카드가 카테고리를 구분해 보여주지 않으므로(그건 상세 화면의 groupByCategory 몫, 포트 밖)
/// 카테고리 구조 자체는 옮기지 않는다.
const Set<String> allControlledOptions = {
  // 안전
  '에어백', '후측방경고', '후측방모니터', '차선유지보조', '후방카메라', '후방센서', '후방감지센서',
  '주차센서', '원격주차', '혼다센싱', '후석알림',
  // 편의/멀티미디어
  '내비게이션', '애플카플레이', '블루투스', '무선충전', '무선업데이트', '크루즈컨트롤', '스마트크루즈',
  '어댑티브크루즈', '스마트키', '에어컨', '라디오', '어라운드뷰', '서라운드뷰', '버추얼콕핏', 'HUD',
  '헤드업디스플레이', '증강현실HUD', '뒷좌석모니터', '후석엔터테인먼트', '하이패스',
  'JBL사운드', '렉시콘사운드', '마크레빈슨', '메리디안사운드', '뱅앤올룹슨', '부메스터사운드',
  '하만카돈', '프리미엄오디오',
  // 시트
  '열선시트', '통풍시트', '가죽시트', '나파가죽', '나파가죽시트', '레더시트', '메모리시트', '릴렉션시트',
  // 외관/내장
  'LED헤드램프', '매트릭스LED', '선루프', '파노라마선루프', '파노라마글래스루프', '앰비언트라이트',
  '전동트렁크', '전동슬라이딩도어', '슬라이딩도어', '카본인테리어', '요크스티어링', '파워스티어링',
  '열선스티어링', 'M스포츠패키지', 'M서스펜션', '콰트로',
  // 기타옵션
  '7인승', '8인승', '9인승', '11인승', 'V2L', '초고속충전', '급속충전지원', '오토파일럿',
};

/// 보편·저순위(강제 최하위 티어) — conventions §11.2.
const Set<String> commonOptions = {
  '후방카메라', '후방센서', '후방감지센서', '주차센서', '스마트키', '블루투스', '에어백', '에어컨',
  '라디오', '파워스티어링', '하이패스', '애플카플레이', '무선충전', '열선시트', '크루즈컨트롤',
  'LED헤드램프', '가죽시트', '후석알림',
};

/// 희소·셀링포인트(high) 티어 — conventions §11.2(선루프 계열이 최상위).
const List<String> highPriorityOptions = [
  '선루프', '파노라마선루프', '파노라마글래스루프', 'HUD', '헤드업디스플레이', '증강현실HUD',
  '통풍시트', '어라운드뷰', '서라운드뷰', '어댑티브크루즈', '스마트크루즈', '차선유지보조',
  '후측방경고', '후측방모니터', '오토파일럿', '나파가죽', '나파가죽시트', '카본인테리어',
  'JBL사운드', '렉시콘사운드', '마크레빈슨', '메리디안사운드', '뱅앤올룹슨', '부메스터사운드',
  '하만카돈', '프리미엄오디오', 'V2L', '초고속충전', '릴렉션시트', '앰비언트라이트', '요크스티어링',
  '콰트로', 'M스포츠패키지', 'M서스펜션', '매트릭스LED', '후석엔터테인먼트', '뒷좌석모니터',
];

// 티어 점수 — 71개를 개별 점수 매기지 않고 3단으로만 가른다(conventions §11.2, A2 단순함 우선).
const int _tierCommon = 0;
const int _tierMid = 5;
const int _tierHigh = 10;

/// `highPriorityOptions`만 명시적으로 담는다 — optionPriority가 나머지는 COMMON/MID로 가른다.
final Set<String> _highPriorityLookup = highPriorityOptions.toSet();

/// 카드에 노출할 옵션 칩 최대 개수(정본: docs/conventions.md §11.2, 사용자 결정 2026-07-29로
/// 4→3 확정) — web `web/src/components/listings/ListingCard.tsx`의 `CARD_OPTION_COUNT`
/// 미러(코드리뷰 지적 P8). 예전엔 `listing_card.dart`의 `_OptionChipsRow._maxChips`에 사본이
/// 있어 이 값이 두 곳에 따로 있었다 — 한쪽이 4→3처럼 다시 바뀌어도 다른 쪽·web은 조용히
/// 남는 드리프트가 가능했다. `listing_options_drift_test.dart`가 이 값을 web과 대조한다.
const int cardOptionCount = 3;

/// 옵션명의 우선순위 점수(web `optionPriority` 미러). high 티어가 아니면 `commonOptions` 소속
/// 여부로 최하위(0)를 가르고, 통제어휘 안의 나머지는 mid 기본값이다.
/// ⚠️ 통제어휘 **밖** 이름(정크·레거시 값)은 mid가 아니라 COMMON과 같은 최하위로 강등한다 —
/// 그래야 표준 밖 값이 카드에서 정상 보편 옵션보다 위로 뜨는 일이 없다(web 코드리뷰와 동일 근거).
int optionPriority(String name) {
  if (_highPriorityLookup.contains(name)) return _tierHigh;
  if (!allControlledOptions.contains(name)) return _tierCommon; // 통제어휘 밖 — 최하위
  return commonOptions.contains(name) ? _tierCommon : _tierMid;
}

/// 카드용 상위 N개 — priority desc(동점은 입력 순서 유지, stable), 상위 n개(web `topOptions` 미러).
/// 희소 옵션이 있으면 그게 먼저 오고, 전부 보편이면 자연히 보유한 보편 옵션 상위 n개로 채워진다
/// (별도 fallback 분기 없이 정렬만으로 충족 — conventions §11.2). 빈 배열/null이면 `[]`.
/// 입력 중복은 여기서 제거한다(options: text[]는 원소 유일성이 없고, 중복이 그대로 남으면 카드에
/// 같은 칩이 두 번 뜨고 Flutter key도 충돌한다 — web 코드리뷰와 동일 근거).
List<String> topOptions(List<String>? options, int n) {
  if (options == null || options.isEmpty) return const [];
  final seen = <String>{};
  final deduped = <String>[];
  for (final name in options) {
    if (seen.contains(name)) continue;
    seen.add(name);
    deduped.add(name);
  }
  final indexed = [
    for (var i = 0; i < deduped.length; i++)
      (name: deduped[i], index: i, priority: optionPriority(deduped[i])),
  ];
  indexed.sort((a, b) {
    final byPriority = b.priority.compareTo(a.priority);
    return byPriority != 0 ? byPriority : a.index.compareTo(b.index);
  });
  return [for (final item in indexed.take(n)) item.name];
}
