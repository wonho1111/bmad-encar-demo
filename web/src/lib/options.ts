// 옵션 통제어휘·우선순위·순수 헬퍼 — web 미러(단일 코드 출처).
// 정본: docs/conventions.md §11(§11.4 포함 — 인기 8종·희소 판정 규칙). 값(카테고리 배치·티어·
// 인기 8종)을 바꾸려면 그 문서를 먼저 고친다.
//
// 왜 이 파일이 존재하나(Story 10.3, 대장 #11):
//   `listings.options`는 정규화 테이블 없이 text[] 저장을 유지한다(과설계 회피). 대신 이 모듈이
//   (1) 카드가 희소 옵션을 우선 노출하도록 우선순위 정렬(topOptions), (2) 상세가 5개 엔카
//   카테고리로 전량 그룹핑(groupByCategory), (3) 쓰기 시 통제어휘 검증(partitionOptions)을
//   제공한다. 파싱(parseOptionsInput/serializeOptions)을 순수함수로 뽑아 옵션 값에 쉼표가 든
//   원소가 쉼표 split로 쪼개지던 문제(대장 #11)를 단위테스트가 잡게 한다.

/** 엔카 5분류 — 각 표준 옵션명은 정확히 1개 카테고리에 속한다(conventions §11.1). */
export type OptionCategory = '안전' | '편의/멀티미디어' | '시트' | '외관/내장' | '기타옵션';

export const OPTION_CATEGORY_ORDER: readonly OptionCategory[] = [
  '안전',
  '편의/멀티미디어',
  '시트',
  '외관/내장',
  '기타옵션',
];

// 통제어휘 — 시드(`supabase/seed-local/data/listings.json`)의 71개 distinct 옵션명을 전부
// 수록한다. 동의어("HUD"/"헤드업디스플레이"/"증강현실HUD" 등)는 통합하지 않고 각각 별도
// 표준 항목으로 둔다(동의어 통합=정규화라 범위 밖, conventions §11.1).
export const CONTROLLED_OPTIONS: Readonly<Record<OptionCategory, readonly string[]>> = {
  안전: [
    '에어백',
    '후측방경고',
    '후측방모니터',
    '차선유지보조',
    '후방카메라',
    '후방센서',
    '후방감지센서',
    '주차센서',
    '원격주차',
    '혼다센싱',
    '후석알림',
  ],
  '편의/멀티미디어': [
    '내비게이션',
    '애플카플레이',
    '블루투스',
    '무선충전',
    '무선업데이트',
    '크루즈컨트롤',
    '스마트크루즈',
    '어댑티브크루즈',
    '스마트키',
    '에어컨',
    '라디오',
    '어라운드뷰',
    '서라운드뷰',
    '버추얼콕핏',
    'HUD',
    '헤드업디스플레이',
    '증강현실HUD',
    '뒷좌석모니터',
    '후석엔터테인먼트',
    '하이패스',
    // 오디오 브랜드
    'JBL사운드',
    '렉시콘사운드',
    '마크레빈슨',
    '메리디안사운드',
    '뱅앤올룹슨',
    '부메스터사운드',
    '하만카돈',
    '프리미엄오디오',
  ],
  시트: ['열선시트', '통풍시트', '가죽시트', '나파가죽', '나파가죽시트', '레더시트', '메모리시트', '릴렉션시트'],
  '외관/내장': [
    'LED헤드램프',
    '매트릭스LED',
    '선루프',
    '파노라마선루프',
    '파노라마글래스루프',
    '앰비언트라이트',
    '전동트렁크',
    '전동슬라이딩도어',
    '슬라이딩도어',
    '카본인테리어',
    '요크스티어링',
    '파워스티어링',
    '열선스티어링',
    'M스포츠패키지',
    'M서스펜션',
    '콰트로',
  ],
  기타옵션: ['7인승', '8인승', '9인승', '11인승', 'V2L', '초고속충전', '급속충전지원', '오토파일럿'],
};

// 모든 표준 옵션명 → 소속 카테고리(groupByCategory·partitionOptions가 함께 쓰는 조회표).
const OPTION_TO_CATEGORY = new Map<string, OptionCategory>();
for (const category of OPTION_CATEGORY_ORDER) {
  for (const name of CONTROLLED_OPTIONS[category]) {
    OPTION_TO_CATEGORY.set(name, category);
  }
}

/** 통제어휘 전체(카테고리 무관) — partitionOptions의 known/unknown 판정 기준. */
export const ALL_CONTROLLED_OPTIONS: ReadonlySet<string> = new Set(OPTION_TO_CATEGORY.keys());

// 보편·저순위(강제 최하위 티어) — conventions §11.2.
export const COMMON_OPTIONS: ReadonlySet<string> = new Set([
  '후방카메라',
  '후방센서',
  '후방감지센서',
  '주차센서',
  '스마트키',
  '블루투스',
  '에어백',
  '에어컨',
  '라디오',
  '파워스티어링',
  '하이패스',
  '애플카플레이',
  '무선충전',
  '열선시트',
  '크루즈컨트롤',
  'LED헤드램프',
  '가죽시트',
  '후석알림',
]);

// 티어 점수 — 71개를 개별 점수 매기지 않고 3단으로만 가른다(conventions §11.2, A2 단순함 우선).
const TIER_COMMON = 0;
const TIER_MID = 5;
const TIER_HIGH = 10;

// 희소·셀링포인트(high) — conventions §11.2.
export const HIGH_PRIORITY_OPTIONS: readonly string[] = [
  '선루프',
  '파노라마선루프',
  '파노라마글래스루프',
  'HUD',
  '헤드업디스플레이',
  '증강현실HUD',
  '통풍시트',
  '어라운드뷰',
  '서라운드뷰',
  '어댑티브크루즈',
  '스마트크루즈',
  '차선유지보조',
  '후측방경고',
  '후측방모니터',
  '오토파일럿',
  '나파가죽',
  '나파가죽시트',
  '카본인테리어',
  'JBL사운드',
  '렉시콘사운드',
  '마크레빈슨',
  '메리디안사운드',
  '뱅앤올룹슨',
  '부메스터사운드',
  '하만카돈',
  '프리미엄오디오',
  'V2L',
  '초고속충전',
  '릴렉션시트',
  '앰비언트라이트',
  '요크스티어링',
  '콰트로',
  'M스포츠패키지',
  'M서스펜션',
  '매트릭스LED',
  '후석엔터테인먼트',
  '뒷좌석모니터',
];

/** 옵션명 → 우선순위 점수. HIGH 티어만 명시하고, 나머지는 optionPriority가 COMMON/MID로 가른다. */
export const OPTION_PRIORITY: Readonly<Record<string, number>> = Object.fromEntries(
  HIGH_PRIORITY_OPTIONS.map((name) => [name, TIER_HIGH]),
);

// 인기 옵션 8종(등록 피커 퀵칩) — conventions §11.4. 전부 캐노니컬명이고 ALL_CONTROLLED_OPTIONS의
// 부분집합이다(불변식은 options.test.ts가 강제 — "내비"·"크루즈" 같은 축약형이 섞이면 red).
export const POPULAR_OPTIONS: readonly string[] = [
  '스마트키',
  '내비게이션',
  '후방카메라',
  '열선시트',
  '통풍시트',
  '선루프',
  '크루즈컨트롤',
  '어라운드뷰',
];

/**
 * 옵션명의 우선순위 점수. `OPTION_PRIORITY`(high)에 없으면 COMMON_OPTIONS 소속 여부로
 * 최하위(0)를 가르고, 통제어휘 안의 나머지는 mid 기본값이다(conventions §11.2).
 * ⚠️ 통제어휘 **밖** 이름(정크·레거시 값)은 mid가 아니라 COMMON과 같은 최하위로 강등한다 —
 * 그래야 표준 밖 값이 카드에서 정상 보편 옵션보다 위로 뜨는 일이 없다(코드리뷰).
 */
export function optionPriority(name: string): number {
  // hasOwnProperty로 조회한다 — `OPTION_PRIORITY[name]`만 쓰면 'toString'·'constructor' 같은
  // Object.prototype 상속 키가 함수를 돌려줘 `!== undefined`를 통과하고, 그 정크값이 카드에서
  // 보편 옵션 위로 뜬다(코드리뷰: prototype 키 누출).
  if (Object.prototype.hasOwnProperty.call(OPTION_PRIORITY, name)) return OPTION_PRIORITY[name];
  if (!ALL_CONTROLLED_OPTIONS.has(name)) return TIER_COMMON; // 통제어휘 밖 — 최하위
  return COMMON_OPTIONS.has(name) ? TIER_COMMON : TIER_MID;
}

/**
 * 이름이 희소·셀링포인트(high) 티어 소속인지 — 등록 피커가 "희소" 태그를 붙일지 판정한다
 * (conventions §11.4). `OPTION_PRIORITY`는 HIGH_PRIORITY_OPTIONS만 명시적으로 담으므로
 * hasOwnProperty 체크가 곧 "high 티어 소속"이다(optionPriority와 같은 이유로 `in`/일반 조회
 * 대신 hasOwnProperty를 쓴다 — Object.prototype 상속 키 누출 방지).
 */
export function isRareOption(name: string): boolean {
  return Object.prototype.hasOwnProperty.call(OPTION_PRIORITY, name);
}

/**
 * 옵션 선택 토글(등록 피커, Story 10.4) — 순수 함수라 여기 둔다(OptionPicker.tsx는 'use client'라
 * 테스트에서 직접 import하면 컴포넌트를 끌고 들어온다, 코드리뷰). 이미 있으면 제거, 없으면
 * 끝에 추가(중복 없이, 기존 순서 유지 + 신규는 append).
 */
export function toggleOption(current: readonly string[], name: string): string[] {
  return current.includes(name) ? current.filter((n) => n !== name) : [...current, name];
}

/**
 * 옵션 집합이 초기값 대비 실제로 바뀌었는지 — 순서·중복 무관(SET 동등)으로 판정한다.
 * 등록/수정 폼의 dirty·이탈경고(SellForm, AC7)가 옵션에 한해 이 헬퍼를 쓴다.
 * 왜 순서를 무시하나: `toggleOption`이 껐다 다시 켠 옵션을 배열 끝에 append하므로, 같은 옵션
 * 집합(net-zero 토글)이어도 직렬화된 줄바꿈 문자열의 순서가 달라진다 — 문자열을 그대로 비교하면
 * 실제 변경이 없는데도 dirty가 참이 돼 허위 이탈경고가 뜬다(Story 10.4 코드리뷰). 정렬 후 비교로
 * 그 허위 dirty를 흡수한다. 순수 함수라 여기 둔다 — SellForm의 dirty 판정이 이 검사로 고정된다.
 */
export function optionsChanged(current: readonly string[], initial: readonly string[]): boolean {
  return JSON.stringify([...current].sort()) !== JSON.stringify([...initial].sort());
}

/**
 * 카드용 상위 N개 — priority desc(동점은 입력 순서 유지, stable), 상위 n개.
 * 희소 옵션이 있으면 그게 먼저 오고, 전부 보편이면 자연히 보유한 보편 옵션 상위 n개로 채워진다
 * (별도 fallback 분기 없이 정렬만으로 충족 — conventions §11.2). 빈 배열이면 `[]`.
 * 입력 중복은 여기서 제거한다(options: text[]는 원소 유일성이 없고, 중복이 그대로 남으면 카드에
 * 같은 칩이 두 번 뜨고 React key도 충돌한다 — 코드리뷰).
 */
export function topOptions(options: readonly string[] | null | undefined, n: number): string[] {
  if (!options || options.length === 0) return [];
  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const name of options) {
    // 타입은 string[]이지만 DB text[]는 NULL 원소를 담을 수 있다 — 비문자열은 건너뛴다
    // (api rows_to_cards·app _asStringList가 같은 층에서 이미 방어; 카드 blank 칩 방지, 코드리뷰).
    if (typeof name !== 'string' || seen.has(name)) continue;
    seen.add(name);
    deduped.push(name);
  }
  return deduped
    .map((name, index) => ({ name, index, priority: optionPriority(name) }))
    .sort((a, b) => b.priority - a.priority || a.index - b.index)
    .slice(0, n)
    .map((item) => item.name);
}

/**
 * 상세용 카테고리별 그룹핑 — 전량, 통제어휘 밖 값은 `기타옵션`으로 폴백한다.
 * 값이 없는 카테고리는 결과 객체에 키 자체가 없다(호출부가 `OPTION_CATEGORY_ORDER`로 순회하며
 * 빈 카테고리를 생략한다).
 */
export function groupByCategory(
  options: readonly string[] | null | undefined,
): Partial<Record<OptionCategory, string[]>> {
  const result: Partial<Record<OptionCategory, string[]>> = {};
  if (!options) return result;
  // 카드(topOptions)와 동일하게 중복·비문자열을 거른다 — 상세도 같은 text[]를 읽으므로 두 화면이
  // 같은 데이터에 다른 칩을 그리면 안 된다(코드리뷰: 카드는 dedupe, 상세는 안 해 불일치).
  const seen = new Set<string>();
  for (const name of options) {
    if (typeof name !== 'string' || seen.has(name)) continue;
    seen.add(name);
    const category = OPTION_TO_CATEGORY.get(name) ?? '기타옵션';
    const bucket = result[category];
    if (bucket) {
      bucket.push(name);
    } else {
      result[category] = [name];
    }
  }
  return result;
}

/** 이름 목록을 통제어휘 소속(known) / 밖(unknown)으로 가른다. 쓰기 검증(SellForm)의 단일 출처. */
export function partitionOptions(names: readonly string[]): { known: string[]; unknown: string[] } {
  const known: string[] = [];
  const unknown: string[] = [];
  for (const name of names) {
    (ALL_CONTROLLED_OPTIONS.has(name) ? known : unknown).push(name);
  }
  return { known, unknown };
}

/**
 * 줄바꿈 구분 입력 → 배열(대장 #11 해소). 쉼표 split이 아니라 줄바꿈 split이라 한 원소 안의
 * 쉼표가 보존된다. 빈 줄·앞뒤 공백 제거, 중복 제거(입력 순서 유지).
 */
export function parseOptionsInput(text: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const rawLine of text.split('\n')) {
    const trimmed = rawLine.trim();
    if (trimmed === '' || seen.has(trimmed)) continue;
    seen.add(trimmed);
    result.push(trimmed);
  }
  return result;
}

/** 배열 → 줄바꿈 join(parseOptionsInput의 역변환, 폼 read 경로). */
export function serializeOptions(options: readonly string[]): string {
  return options.join('\n');
}
