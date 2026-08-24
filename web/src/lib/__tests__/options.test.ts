// 옵션 통제어휘·우선순위·순수 헬퍼 단위테스트 (Story 10.3).
//
// 왜 이 파일이 존재하나: `options.ts`가 카드 우선순위·상세 그룹핑·쓰기 검증의 단일 코드
// 출처다(docs/conventions.md §11). 특히 #11(대장) 라운드트립은 이 테스트가 유일한 강제
// 장치다 — 화면(SellForm)이 아니라 순수함수에서 red를 실측한다(project-context 규칙12
// "서버 컴포넌트 밖 순수 유틸은 Vitest로 보강").
//
// 커버리지 테스트는 시드(`supabase/seed-local/data/listings.json`)의 distinct 옵션명을 직접
// 읽어 `CONTROLLED_OPTIONS`와 대조한다 — 하나라도 빠지면 red(conventions §11.1 불변식).

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  ALL_CONTROLLED_OPTIONS,
  COMMON_OPTIONS,
  CONTROLLED_OPTIONS,
  HIGH_PRIORITY_OPTIONS,
  OPTION_CATEGORY_ORDER,
  POPULAR_OPTIONS,
  groupByCategory,
  isRareOption,
  optionPriority,
  optionsChanged,
  parseOptionsInput,
  partitionOptions,
  serializeOptions,
  toggleOption,
  topOptions,
} from '../options';

// --- 커버리지: 시드의 distinct 옵션이 전부 통제어휘에 있는가 -----------------------------

function readSeedDistinctOptions(): string[] {
  const seedPath = fileURLToPath(
    new URL('../../../../supabase/seed-local/data/listings.json', import.meta.url),
  );
  const rows = JSON.parse(readFileSync(seedPath, 'utf-8')) as Array<{ options?: string[] | null }>;
  const set = new Set<string>();
  for (const row of rows) {
    for (const opt of row.options ?? []) set.add(opt);
  }
  return [...set];
}

describe('CONTROLLED_OPTIONS 커버리지 (conventions §11.1 불변식)', () => {
  it('시드의 distinct 옵션명이 전부 통제어휘에 있고, 각각 정확히 1개 카테고리에 속한다', () => {
    const seedOptions = readSeedDistinctOptions();
    expect(seedOptions.length).toBeGreaterThan(0); // 시드가 비어있으면 이 테스트 자체가 무의미하다

    const missing = seedOptions.filter((name) => !ALL_CONTROLLED_OPTIONS.has(name));
    expect(missing).toEqual([]);
  });

  it('카테고리 간 중복 없음 — 각 옵션명은 정확히 1개 카테고리 소속', () => {
    const seen = new Map<string, string>();
    for (const category of OPTION_CATEGORY_ORDER) {
      for (const name of CONTROLLED_OPTIONS[category]) {
        expect(seen.has(name)).toBe(false);
        seen.set(name, category);
      }
    }
  });
});

// --- COMMON_OPTIONS·HIGH_PRIORITY_OPTIONS 무결성 (docs/conventions.md §11.2 정본과의 락스텝) ---
// 왜 이 블록이 필요한가(코드리뷰): §11.2가 티어 목록의 값 정본인데, 코드(options.ts)가 그
// 목록에서 이름 하나를 빠뜨려도(예: '나파가죽시트' 누락) 위 커버리지 테스트는 못 잡는다 —
// 커버리지는 "통제어휘 안에 있는가"만 보지 "올바른 티어에 있는가"는 안 본다. 그래서 (a) 두
// 티어 목록의 이름이 전부 통제어휘 소속인지, (b) 두 목록이 문서에 선언된 값과 **정확히**
// 일치하는지를 별도로 못박는다 — 문서·코드 중 한쪽만 바뀌면 이 블록이 red가 된다.

// docs/conventions.md §11.2 "COMMON_OPTIONS(보편, 강제 최저 티어)" 원문을 그대로 옮긴 것 —
// 값이 바뀌면 그 문서를 먼저 고치고 이 배열을 따라 갱신한다.
const EXPECTED_COMMON_FROM_DOC = [
  '후방카메라', '후방센서', '후방감지센서', '주차센서', '스마트키', '블루투스', '에어백',
  '에어컨', '라디오', '파워스티어링', '하이패스', '애플카플레이', '무선충전', '열선시트',
  '크루즈컨트롤', 'LED헤드램프', '가죽시트', '후석알림',
];

// docs/conventions.md §11.2 "희소·셀링포인트(high)" 원문 그대로("오디오 브랜드 8종"은
// §11.1 표의 실제 8개 브랜드명으로 펼침).
const EXPECTED_HIGH_FROM_DOC = [
  '선루프', '파노라마선루프', '파노라마글래스루프', 'HUD', '헤드업디스플레이', '증강현실HUD',
  '통풍시트', '어라운드뷰', '서라운드뷰', '어댑티브크루즈', '스마트크루즈', '차선유지보조',
  '후측방경고', '후측방모니터', '오토파일럿', '나파가죽', '나파가죽시트', '카본인테리어',
  'JBL사운드', '렉시콘사운드', '마크레빈슨', '메리디안사운드', '뱅앤올룹슨', '부메스터사운드',
  '하만카돈', '프리미엄오디오', 'V2L', '초고속충전', '릴렉션시트', '앰비언트라이트',
  '요크스티어링', '콰트로', 'M스포츠패키지', 'M서스펜션', '매트릭스LED', '후석엔터테인먼트',
  '뒷좌석모니터',
];

describe('COMMON_OPTIONS·HIGH_PRIORITY_OPTIONS 무결성', () => {
  it('두 티어 목록의 모든 이름이 통제어휘(CONTROLLED_OPTIONS) 소속이다', () => {
    for (const name of COMMON_OPTIONS) {
      expect(ALL_CONTROLLED_OPTIONS.has(name)).toBe(true);
    }
    for (const name of HIGH_PRIORITY_OPTIONS) {
      expect(ALL_CONTROLLED_OPTIONS.has(name)).toBe(true);
    }
  });

  it('COMMON_OPTIONS가 docs/conventions.md §11.2 선언과 정확히 일치한다', () => {
    expect([...COMMON_OPTIONS].sort()).toEqual([...EXPECTED_COMMON_FROM_DOC].sort());
  });

  it('HIGH_PRIORITY_OPTIONS가 docs/conventions.md §11.2 선언과 정확히 일치한다(나파가죽시트 누락 회귀 방지)', () => {
    expect([...HIGH_PRIORITY_OPTIONS].sort()).toEqual([...EXPECTED_HIGH_FROM_DOC].sort());
  });
});

// --- POPULAR_OPTIONS·isRareOption (docs/conventions.md §11.4, Story 10.4) ----------------
// 왜 이 블록이 필요한가: POPULAR_OPTIONS에 비캐노니컬명("내비"·"크루즈" 등)이 섞이면 등록
// 피커가 통제어휘 밖 값을 저장하려 들어 §11.3 쓰기 검증에서 막힌다 — 이 불변식 테스트가
// 그 함정을 코드 리뷰 없이도 잡는다(spec AC7, red/green 실측은 구현 후 별도로 수행).

describe('POPULAR_OPTIONS 불변식 (conventions §11.4)', () => {
  it('8종이다', () => {
    expect(POPULAR_OPTIONS).toHaveLength(8);
  });

  it('모든 원소가 캐노니컬명이다 — ALL_CONTROLLED_OPTIONS(통제어휘) 소속', () => {
    const missing = POPULAR_OPTIONS.filter((name) => !ALL_CONTROLLED_OPTIONS.has(name));
    expect(missing).toEqual([]);
  });
});

describe('isRareOption', () => {
  it('high 티어(선루프)는 희소다', () => {
    expect(isRareOption('선루프')).toBe(true);
  });

  it('common 티어(스마트키)는 희소가 아니다', () => {
    expect(isRareOption('스마트키')).toBe(false);
  });

  it('mid 티어(내비게이션)는 희소가 아니다', () => {
    expect(isRareOption('내비게이션')).toBe(false);
  });

  it('통제어휘 밖 이름은 희소가 아니다', () => {
    expect(isRareOption('존재하지않는옵션')).toBe(false);
  });

  it('Object.prototype 키(toString·constructor·valueOf 등)도 희소가 아니다(prototype 누출 방지)', () => {
    // optionPriority와 같은 이유로 hasOwnProperty를 쓴다 — `in`/일반 조회만 쓰면 상속 키가
    // 함수를 돌려줘 "희소" 태그가 정크 키에도 붙는다(코드리뷰).
    for (const key of ['toString', 'constructor', 'valueOf', 'hasOwnProperty', '__proto__']) {
      expect(isRareOption(key)).toBe(false);
    }
  });
});

// --- toggleOption — 등록 피커 선택 토글(순수 함수, Story 10.4 코드리뷰) --------------------

describe('toggleOption', () => {
  it('없는 이름을 추가하면 끝에 append된다', () => {
    expect(toggleOption(['선루프'], '스마트키')).toEqual(['선루프', '스마트키']);
  });

  it('이미 있는 이름을 다시 넣으면 제거된다(OFF 토글)', () => {
    expect(toggleOption(['선루프', '스마트키'], '선루프')).toEqual(['스마트키']);
  });

  it('결과에 중복이 생기지 않는다', () => {
    const result = toggleOption(['선루프'], '선루프');
    expect(result).toEqual([]);
    expect(new Set(toggleOption(['선루프', '스마트키'], '통풍시트'))).toEqual(
      new Set(['선루프', '스마트키', '통풍시트']),
    );
  });

  it('남은 항목의 순서를 유지한다(끄고 켜도 재정렬하지 않음 — 껐다 켜면 끝으로 이동)', () => {
    // 가운데(스마트키) 제거 — 앞뒤 순서 유지.
    expect(toggleOption(['선루프', '스마트키', '통풍시트'], '스마트키')).toEqual(['선루프', '통풍시트']);
    // 제거 후 재추가 — 끝으로 이동(append 규칙, dirty 비교는 SellForm이 SET으로 흡수).
    const off = toggleOption(['선루프', '스마트키', '통풍시트'], '스마트키');
    expect(toggleOption(off, '스마트키')).toEqual(['선루프', '통풍시트', '스마트키']);
  });
});

// --- optionsChanged — 순서무관 dirty 판정(SellForm AC7, Story 10.4 후속 코드리뷰) -----------
// 왜 이 블록이 필요한가: SellForm이 옵션 dirty를 이 헬퍼로 판정한다. toggleOption이 껐다 켠
// 옵션을 끝으로 append하므로(위 테스트가 증명), 문자열을 그대로 비교하면 net-zero 토글에도
// dirty=true가 돼 허위 이탈경고가 뜬다. 반대로 이 SET 비교가 사라지면 옵션만 편집한 변경이
// dirty로 안 잡혀 이탈경고 없이 조용히 사라진다. 그 회귀를 잡는 검사는 이전 패스엔 없었다.

describe('optionsChanged (SellForm 옵션 dirty)', () => {
  it('같은 집합이면 순서만 달라도 not dirty (net-zero 토글 흡수)', () => {
    expect(optionsChanged(['선루프', '스마트키'], ['스마트키', '선루프'])).toBe(false);
  });

  it('껐다 켜서 끝으로 이동한 결과도 not dirty', () => {
    const initial = ['선루프', '스마트키', '통풍시트'];
    const afterOffOn = toggleOption(toggleOption(initial, '스마트키'), '스마트키'); // ['선루프','통풍시트','스마트키']
    expect(optionsChanged(afterOffOn, initial)).toBe(false);
  });

  it('옵션이 추가되면 dirty', () => {
    expect(optionsChanged(['선루프', '스마트키'], ['선루프'])).toBe(true);
  });

  it('옵션이 제거되면 dirty', () => {
    expect(optionsChanged(['선루프'], ['선루프', '스마트키'])).toBe(true);
  });

  it('빈 집합끼리는 not dirty', () => {
    expect(optionsChanged([], [])).toBe(false);
  });
});

// --- topOptions — 희소우선·보편fallback·상위N cap·빈배열 --------------------------------

describe('topOptions', () => {
  it('희소 옵션이 보편보다 먼저 온다(priority desc)', () => {
    const result = topOptions(['후방카메라', '스마트키', '선루프', '통풍시트', '내비게이션'], 4);
    // 선루프·통풍시트(high) > 내비게이션(mid) > 후방카메라·스마트키(common, 0). 상위 4개 중
    // 희소 2개가 반드시 포함되고 보편이 밀린다.
    expect(result.slice(0, 2)).toEqual(['선루프', '통풍시트']);
    expect(result).toHaveLength(4);
    expect(result).not.toContain('스마트키'); // common 2개 중 하나는 상위 4에서 밀려남
  });

  it('전부 보편이면 보유한 보편 옵션에서 상위 N개로 채운다(빈 칩 행 금지)', () => {
    const result = topOptions(['후방카메라', '스마트키', '블루투스'], 4);
    expect(result).toEqual(['후방카메라', '스마트키', '블루투스']);
  });

  it('상위 N개로 자른다(cap)', () => {
    const result = topOptions(['선루프', '통풍시트', 'HUD', '어라운드뷰', '나파가죽'], 3);
    expect(result).toHaveLength(3);
  });

  it('빈 배열·null·undefined는 []을 돌려준다', () => {
    expect(topOptions([], 4)).toEqual([]);
    expect(topOptions(null, 4)).toEqual([]);
    expect(topOptions(undefined, 4)).toEqual([]);
  });

  it('동점은 입력 순서를 유지한다(stable)', () => {
    // 후방카메라·스마트키 둘 다 common(0점) — 입력 순서 그대로.
    const result = topOptions(['스마트키', '후방카메라'], 4);
    expect(result).toEqual(['스마트키', '후방카메라']);
  });

  it('입력에 중복이 있어도 결과에 같은 이름이 두 번 뜨지 않는다(카드 칩 중복·React key 충돌 방지)', () => {
    const result = topOptions(['선루프', '스마트키', '선루프', '스마트키'], 4);
    expect(result).toEqual(['선루프', '스마트키']);
  });

  it('DB text[]의 비문자열(NULL) 원소는 건너뛴다(카드 blank 칩 방지)', () => {
    const withNull = ['선루프', null, '스마트키'] as unknown as string[];
    expect(topOptions(withNull, 4)).toEqual(['선루프', '스마트키']);
  });
});

describe('optionPriority', () => {
  it('COMMON_OPTIONS는 0점', () => {
    for (const name of COMMON_OPTIONS) {
      expect(optionPriority(name)).toBe(0);
    }
  });

  it('희소 셀링포인트는 common보다 높다', () => {
    expect(optionPriority('선루프')).toBeGreaterThan(optionPriority('후방카메라'));
  });

  it('통제어휘 밖 이름은 COMMON과 같은 최하위로 강등된다(정크값이 보편보다 위로 뜨면 안 됨)', () => {
    expect(optionPriority('존재하지않는옵션')).toBeLessThanOrEqual(optionPriority('후방카메라'));
  });

  it('Object.prototype 키(toString·constructor·valueOf)도 통제어휘 밖이면 최하위 숫자를 돌려준다', () => {
    // OPTION_PRIORITY[name]만 쓰면 상속 키가 함수를 돌려줘 정크가 보편 위로 뜬다(prototype 누출).
    for (const key of ['toString', 'constructor', 'valueOf', 'hasOwnProperty', '__proto__']) {
      expect(optionPriority(key)).toBe(0);
    }
    // topOptions 정렬에서도 정크가 보편(후방카메라) 위로 올라가지 않는다.
    expect(topOptions(['후방카메라', 'toString'], 2)).toEqual(['후방카메라', 'toString']);
  });

  it('통제어휘 안의 mid 옵션은 여전히 common보다 높고 high보다 낮다', () => {
    expect(optionPriority('내비게이션')).toBeGreaterThan(optionPriority('후방카메라'));
    expect(optionPriority('내비게이션')).toBeLessThan(optionPriority('선루프'));
  });
});

// --- groupByCategory — 기타옵션 폴백 ---------------------------------------------------

describe('groupByCategory', () => {
  it('5카테고리 혼재 + 통제어휘 밖 값 → 전량 노출, 밖 값은 기타옵션으로', () => {
    const grouped = groupByCategory(['후방카메라', '내비게이션', '가죽시트', '선루프', '7인승', '가상현실HUD']);
    expect(grouped['안전']).toEqual(['후방카메라']);
    expect(grouped['편의/멀티미디어']).toEqual(['내비게이션']);
    expect(grouped['시트']).toEqual(['가죽시트']);
    expect(grouped['외관/내장']).toEqual(['선루프']);
    // '7인승'(통제어휘 안, 기타옵션 카테고리)과 '가상현실HUD'(통제어휘 밖 폴백) 둘 다 기타옵션에.
    expect(grouped['기타옵션']).toEqual(['7인승', '가상현실HUD']);
  });

  it('빈 배열·null·undefined는 빈 객체', () => {
    expect(groupByCategory([])).toEqual({});
    expect(groupByCategory(null)).toEqual({});
    expect(groupByCategory(undefined)).toEqual({});
  });

  it('중복 값은 한 번만 그룹핑한다(카드 topOptions와 동일 — 두 화면 일관)', () => {
    expect(groupByCategory(['선루프', '선루프', '후방카메라'])).toEqual({
      안전: ['후방카메라'],
      '외관/내장': ['선루프'],
    });
  });

  it('DB text[]의 비문자열(NULL) 원소는 건너뛴다(blank 칩 방지)', () => {
    const withNull = ['선루프', null, undefined] as unknown as string[];
    expect(groupByCategory(withNull)).toEqual({ '외관/내장': ['선루프'] });
  });
});

// --- partitionOptions — known/unknown -------------------------------------------------

describe('partitionOptions', () => {
  it('통제어휘 안/밖을 나눈다', () => {
    const { known, unknown } = partitionOptions(['선루프', '없는옵션', '스마트키']);
    expect(known).toEqual(['선루프', '스마트키']);
    expect(unknown).toEqual(['없는옵션']);
  });

  it('전부 known이면 unknown은 빈 배열', () => {
    expect(partitionOptions(['선루프', '스마트키']).unknown).toEqual([]);
  });
});

// --- #11 라운드트립: parseOptionsInput/serializeOptions -------------------------------

describe('parseOptionsInput / serializeOptions (대장 #11 해소)', () => {
  it('줄바꿈 split이라 원소 안의 쉼표가 보존된다(#11 핵심 재현)', () => {
    expect(parseOptionsInput('a, b\nc')).toEqual(['a, b', 'c']);
  });

  it('빈 줄·앞뒤 공백을 제거한다', () => {
    expect(parseOptionsInput('  선루프  \n\n  통풍시트\n')).toEqual(['선루프', '통풍시트']);
  });

  it('중복을 제거한다(입력 순서 유지)', () => {
    expect(parseOptionsInput('선루프\n스마트키\n선루프')).toEqual(['선루프', '스마트키']);
  });

  it('serializeOptions는 줄바꿈 join으로 역변환한다(라운드트립)', () => {
    const original = ['스마트키, 후방카메라', '선루프'];
    expect(parseOptionsInput(serializeOptions(original))).toEqual(original);
  });
});
