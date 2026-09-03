'use client';

// 매물 검색 필터 폼 (FR9) — 키워드 + 7종 필터를 입력받아 URL 쿼리스트링으로 검색을 건다.
//
// 왜 URL 쿼리스트링인가:
//   필터 상태를 URL(/search?region=서울&fuel=전기 …)에 담으면 새로고침·뒤로가기·링크 공유에 강하고,
//   서버 컴포넌트(page.tsx)가 그 값을 읽어 DB를 조회한다(상태를 한 곳=URL에만 둔다 — 단순·견고).
//   적용 버튼을 누르면 router.push로 URL을 바꾸고, 서버 컴포넌트가 새 결과를 렌더한다.
//
// 드롭다운 옵션은 LISTING_OPTIONS 단일출처를 그대로 쓴다(하드코딩·재발명 금지 — DB CHECK와 일치).
// 연식 범위는 LISTING_RANGES.year. 첫 옵션 "전체"(빈 값) = 해당 필터 미적용.
//
// ✎ 2026-09-01 사용자 지시(개선 UI 통일 1) — 이 필터를 매물 등록 폼(SellForm)과 **배치·컴포넌트
//   수준까지 동일**하게 맞춘다: 섹션 순서(제조사→모델→차종→연식→가격→주행거리→색상→연료→변속기→
//   배기량→인승→지역→신뢰정보→옵션)와 한 그리드(grid-cols-1 sm:grid-cols-2)에 담는 배치 문법을
//   그대로 가져온다. 범위 입력(연식·가격·주행거리·배기량·인승)만 SellForm엔 없는 축이라 "최소~최대"
//   두 입력을 같은 그리드 슬롯 하나에 넣는 전용 렌더러(renderRange)로 대응한다. 옵션은 SellForm의
//   OptionPicker를 **그대로 재사용**한다 — 새 시각 언어를 만들지 않는다(아래 옵션 블록 주석 참조).
import { useId, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LISTING_OPTIONS, LISTING_RANGES, UNITS } from '@/lib/constants';
import Button from '@/components/ui/Button';
// 라벨·입력칸 클래스는 /sell 등록 폼과 **한 벌을 공유**한다(2026-08-13 사용자 결정 — 두 화면이
// 같은 구조인데 밀도·배경이 달랐다). 자세한 경위는 formField.ts 주석 참조.
import { FIELD_CONTROL_CLASS, FIELD_LABEL_CLASS } from '@/components/ui/formField';
// 옵션 선택 UI — 전용 OptionFilterPicker를 따로 두지 않고 SellForm의 OptionPicker를 그대로
// 재사용한다(2026-09-01). interface(value: string[] · onChange)가 이미 동일하고, OptionPicker에
// 있는 "쓰기 전용" 관심사(통제어휘 밖 값 보존)도 필터엔 문제가 되지 않는다 — 필터의 선택지는
// 항상 체크박스·칩에서만 나오므로 통제어휘 밖 값이 애초에 만들어질 수 없다(직전 OptionFilterPicker는
// 그래서 로직 차이 없이 시각만 달랐던 순수 표현 중복이었다 — 이번에 제거).
import OptionPicker from '@/app/(user)/sell/OptionPicker';

// 현재 URL 쿼리값(서버가 넘겨준 초기값)으로 폼을 채운다 → 새로고침해도 필터가 유지된다.
export type SearchFilterValues = {
  q: string; // 키워드(모델명 부분일치)
  // 제조사(개선 2, 2026-09-01) — 등록 폼(SellForm)엔 있었는데 필터엔 없던 축. 등록↔검색 대칭 요구.
  manufacturer: string;
  body_type: string;
  color: string;
  fuel: string;
  transmission: string;
  region: string;
  price_min: string;
  price_max: string;
  year_min: string;
  year_max: string;
  // 주행거리·배기량·인승 범위(개선 2) — 등록 폼엔 단일값 입력이 있는데 필터엔 그 축 자체가
  // 없었다. 가격·연식과 같은 범위(min~max) 관례로 맞춘다.
  mileage_min: string;
  mileage_max: string;
  displacement_min: string;
  displacement_max: string;
  seats_min: string;
  seats_max: string;
  // 신뢰속성 필터(2026-08-13 사용자 요청) — 상세·카드에 뱃지로 보여주던 값으로 거를 수 있게 한다.
  //   accident_status: ''(전체) | 무사고 | 단순교환 | 사고 — **뱃지 기준**이다(사용자 결정).
  //     예전 "무사고 차량" 체크박스가 쓰던 accident_free는 필터에서 쓰지 않는다(그건 이제 파생값이고
  //     소비처가 AI 검색 하나뿐이다).
  //   single_owner·non_smoker: '1'(신고한 것만) | ''(전체). 체크박스라 두 값뿐이다 —
  //     "1인소유가 아닌 차만"은 만들지 않는다: 값이 없는 매물은 "아니다"가 아니라 "말하지 않음"이라
  //     그런 필터는 무엇을 고르는지 스스로도 정의할 수 없다.
  accident_status: string;
  single_owner: string;
  non_smoker: string;
  // 옵션(개선 2) — 다중 선택, "전부 보유"(AND) 의미. 다른 필드와 달리 string[]이라 아래
  // applyFilters/resetFilters/pageHref에서 개별 처리한다(URL엔 같은 키를 반복 — ?options=a&options=b).
  options: string[];
};

export default function SearchFilters({ initial }: { initial: SearchFilterValues }) {
  const router = useRouter();
  const [values, setValues] = useState<SearchFilterValues>(initial);
  // 옵션 필드 그룹 라벨("옵션 …" 헤딩)과 role="group" 컨테이너를 aria-labelledby로 연결
  // (SellForm과 동일 패턴, 코드리뷰).
  const optionsLabelId = useId();

  // 문자열 필드(대부분)의 단일 핸들러 — 필드명 = state 키. options(string[])는 제외한다
  // (아래 updateOptions가 따로 담당 — 값 타입이 달라 이 제네릭에 섞으면 타입이 어긋난다).
  function update<K extends Exclude<keyof SearchFilterValues, 'options'>>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  // options 전용 핸들러(개선 2) — OptionPicker가 다중 선택 결과를 그대로 넘긴다.
  function updateOptions(next: string[]) {
    setValues((prev) => ({ ...prev, options: next }));
  }

  // 적용: 빈 값은 URL에서 제외(깔끔한 쿼리스트링) 후 /search로 push.
  //   options는 string[]이라 일반 루프에서 빼고, 같은 키를 반복해 붙인다(?options=a&options=b —
  //   page.tsx가 Next.js searchParams의 다중값 배열로 그대로 읽는다).
  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    (Object.entries(values) as [keyof SearchFilterValues, string | string[]][]).forEach(([key, value]) => {
      if (key === 'options') {
        (value as string[]).forEach((opt) => params.append('options', opt));
        return;
      }
      const v = (value as string).trim();
      if (v !== '') params.set(key, v);
    });
    const query = params.toString();
    router.push(query ? `/search?${query}` : '/search');
  }

  // 초기화: 모든 필터를 비우고 전체 목록으로.
  function resetFilters() {
    const empty: SearchFilterValues = {
      q: '', manufacturer: '', body_type: '', color: '', fuel: '', transmission: '', region: '',
      price_min: '', price_max: '', year_min: '', year_max: '',
      mileage_min: '', mileage_max: '', displacement_min: '', displacement_max: '', seats_min: '', seats_max: '',
      accident_status: '', single_owner: '', non_smoker: '',
      options: [],
    };
    setValues(empty);
    router.push('/search');
  }

  // 드롭다운 한 개를 그리는 helper — "전체"(빈 값) + LISTING_OPTIONS 항목. SellForm의 각 <select>
  // label과 같은 모양(FIELD_LABEL_CLASS + FIELD_CONTROL_CLASS)이라 신뢰정보의 사고이력에도 그대로 쓴다.
  function renderSelect(key: Exclude<keyof SearchFilterValues, 'options'>, label: string, options: readonly string[]) {
    return (
      <label className="flex flex-col gap-1">
        <span className={FIELD_LABEL_CLASS}>{label}</span>
        <select
          value={values[key]}
          onChange={(e) => update(key, e.target.value)}
          className={FIELD_CONTROL_CLASS}
        >
          <option value="">전체</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </label>
    );
  }

  // 범위 입력(최소~최대) 한 쌍을 그리는 helper — SellForm엔 없는 축(연식·가격·주행거리·배기량·인승은
  // 거기선 단일값)이라 직접 재사용할 컴포넌트가 없다. 대신 같은 라벨·입력칸 스타일(FIELD_LABEL_CLASS·
  // FIELD_CONTROL_CLASS)로 같은 그리드 슬롯 하나에 들어가는 "입력 두 개"로 맞춘다(사용자 지시).
  function renderRange(
    minKey: Exclude<keyof SearchFilterValues, 'options'>,
    maxKey: Exclude<keyof SearchFilterValues, 'options'>,
    label: string,
    numAttrs?: { min?: number; max?: number },
  ) {
    return (
      <div className="flex flex-col gap-1">
        <span className={FIELD_LABEL_CLASS}>{label}</span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            {...numAttrs}
            value={values[minKey]}
            onChange={(e) => update(minKey, e.target.value)}
            placeholder="최소"
            className={`w-full ${FIELD_CONTROL_CLASS}`}
          />
          <span className="text-ink-muted">~</span>
          <input
            type="number"
            {...numAttrs}
            value={values[maxKey]}
            onChange={(e) => update(maxKey, e.target.value)}
            placeholder="최대"
            className={`w-full ${FIELD_CONTROL_CLASS}`}
          />
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={applyFilters}
      className="flex flex-col gap-4 rounded-card border border-border-hairline p-4"
    >
      {/* 등록 폼(SellForm)과 같은 한 그리드·같은 순서: 제조사→모델(키워드)→차종→연식→가격→주행거리→
          색상→연료→변속기→배기량→인승→지역. 설명·사진 자리만 등록 폼에서 생략한다(사용자 지시). */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {renderSelect('manufacturer', '제조사', LISTING_OPTIONS.manufacturer)}

        {/* 모델 — 등록 폼은 정확히 한 값을 받지만 검색은 부분일치 키워드라 라벨만 그에 맞춘다
            (배치·입력칸 스타일은 동일). */}
        <label className="flex flex-col gap-1">
          <span className={FIELD_LABEL_CLASS}>키워드(모델명)</span>
          <input
            type="text"
            value={values.q}
            onChange={(e) => update('q', e.target.value)}
            placeholder="예: 아반떼, 쏘렌토"
            className={FIELD_CONTROL_CLASS}
          />
        </label>

        {renderSelect('body_type', '차종', LISTING_OPTIONS.body_type)}
        {renderRange('year_min', 'year_max', '연식(년)', {
          min: LISTING_RANGES.year.min,
          max: LISTING_RANGES.year.max,
        })}
        {renderRange('price_min', 'price_max', `가격(${UNITS.price})`, { min: 0 })}
        {renderRange('mileage_min', 'mileage_max', `주행거리(${UNITS.mileage})`, {
          min: LISTING_RANGES.mileage.min,
        })}
        {renderSelect('color', '색상', LISTING_OPTIONS.color)}
        {renderSelect('fuel', '연료', LISTING_OPTIONS.fuel)}
        {renderSelect('transmission', '변속기', LISTING_OPTIONS.transmission)}
        {renderRange('displacement_min', 'displacement_max', `배기량(${UNITS.displacement})`, {
          min: LISTING_RANGES.displacement.min,
        })}
        {renderRange('seats_min', 'seats_max', '인승(명)', {
          min: LISTING_RANGES.seats.min,
          max: LISTING_RANGES.seats.max,
        })}
        {renderSelect('region', '지역', LISTING_OPTIONS.region)}
      </div>

      {/* 신뢰 정보 — SellForm의 신뢰정보 fieldset과 같은 구조(카드 테두리+legend, 드롭다운 한 줄 +
          체크박스 두 줄). 판매자 자기신고(무사고·1인소유·비흡연)로 거른다 — 카드·상세의 뱃지와 같은 값. */}
      <fieldset className="flex flex-col gap-3 rounded-card border border-border-hairline p-3">
        <legend className={`px-1 ${FIELD_LABEL_CLASS}`}>신뢰 정보</legend>

        {renderSelect('accident_status', '사고이력', LISTING_OPTIONS.accident_status)}

        {/* 체크 = "그렇다고 신고한 매물만". 미체크 = 조건 없음(전체) — 체크를 풀었다고 해서
            "1인소유가 아닌 차"를 찾는 게 아니다. */}
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.single_owner === '1'}
            onChange={(e) => update('single_owner', e.target.checked ? '1' : '')}
          />
          <span className={FIELD_LABEL_CLASS}>1인소유</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.non_smoker === '1'}
            onChange={(e) => update('non_smoker', e.target.checked ? '1' : '')}
          />
          <span className={FIELD_LABEL_CLASS}>비흡연</span>
        </label>
      </fieldset>

      {/* 옵션(개선 2) — SellForm과 **같은 컴포넌트**(OptionPicker)를 그대로 재사용(칩 요약+체크리스트,
          위 import 주석 참조). 라벨 문구만 필터의 질의 의미(전부 보유 AND)를 알리도록 다르다. */}
      <div role="group" aria-labelledby={optionsLabelId} className="flex flex-col gap-1">
        <span id={optionsLabelId} className={FIELD_LABEL_CLASS}>
          옵션(다중 선택 — 선택한 옵션 전부 보유한 매물만)
        </span>
        <OptionPicker value={values.options} onChange={updateOptions} />
      </div>

      <div className="flex gap-3">
        <Button type="submit" variant="primary">
          검색
        </Button>
        <Button type="button" variant="secondary" onClick={resetFilters}>
          초기화
        </Button>
      </div>
    </form>
  );
}
