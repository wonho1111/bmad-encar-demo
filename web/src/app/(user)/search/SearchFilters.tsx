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
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { LISTING_OPTIONS, LISTING_RANGES, UNITS } from '@/lib/constants';
import Button from '@/components/ui/Button';

// 현재 URL 쿼리값(서버가 넘겨준 초기값)으로 폼을 채운다 → 새로고침해도 필터가 유지된다.
export type SearchFilterValues = {
  q: string; // 키워드(모델명 부분일치)
  body_type: string;
  color: string;
  fuel: string;
  transmission: string;
  region: string;
  price_min: string;
  price_max: string;
  year_min: string;
  year_max: string;
};

export default function SearchFilters({ initial }: { initial: SearchFilterValues }) {
  const router = useRouter();
  const [values, setValues] = useState<SearchFilterValues>(initial);

  // 단일 핸들러로 모든 입력 갱신(필드명 = state 키).
  function update<K extends keyof SearchFilterValues>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  // 적용: 빈 값은 URL에서 제외(깔끔한 쿼리스트링) 후 /search로 push.
  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    (Object.entries(values) as [keyof SearchFilterValues, string][]).forEach(([key, value]) => {
      const v = value.trim();
      if (v !== '') params.set(key, v);
    });
    const query = params.toString();
    router.push(query ? `/search?${query}` : '/search');
  }

  // 초기화: 모든 필터를 비우고 전체 목록으로.
  function resetFilters() {
    const empty: SearchFilterValues = {
      q: '', body_type: '', color: '', fuel: '', transmission: '', region: '',
      price_min: '', price_max: '', year_min: '', year_max: '',
    };
    setValues(empty);
    router.push('/search');
  }

  // 드롭다운 한 개를 그리는 helper — "전체"(빈 값) + LISTING_OPTIONS 항목.
  function renderSelect(key: keyof SearchFilterValues, label: string, options: readonly string[]) {
    return (
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
        <select
          value={values[key]}
          onChange={(e) => update(key, e.target.value)}
          className="rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
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

  return (
    <form
      onSubmit={applyFilters}
      className="flex flex-col gap-4 rounded border border-zinc-200 p-4 dark:border-zinc-800"
    >
      {/* 키워드(모델명) */}
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">키워드(모델명)</span>
        <input
          type="text"
          value={values.q}
          onChange={(e) => update('q', e.target.value)}
          placeholder="예: 아반떼, 쏘렌토"
          className="rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
        />
      </label>

      {/* 드롭다운 5종 — 반응형 그리드 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {renderSelect('body_type', '차종', LISTING_OPTIONS.body_type)}
        {renderSelect('color', '색상', LISTING_OPTIONS.color)}
        {renderSelect('fuel', '연료', LISTING_OPTIONS.fuel)}
        {renderSelect('transmission', '변속기', LISTING_OPTIONS.transmission)}
        {renderSelect('region', '지역', LISTING_OPTIONS.region)}
      </div>

      {/* 가격 범위(원) */}
      <fieldset className="flex flex-col gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">가격({UNITS.price})</span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            value={values.price_min}
            onChange={(e) => update('price_min', e.target.value)}
            placeholder="최소"
            className="w-full rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
          />
          <span className="text-zinc-400">~</span>
          <input
            type="number"
            min={0}
            value={values.price_max}
            onChange={(e) => update('price_max', e.target.value)}
            placeholder="최대"
            className="w-full rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
          />
        </div>
      </fieldset>

      {/* 연식 범위(년) */}
      <fieldset className="flex flex-col gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">연식(년)</span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={LISTING_RANGES.year.min}
            max={LISTING_RANGES.year.max}
            value={values.year_min}
            onChange={(e) => update('year_min', e.target.value)}
            placeholder="최소"
            className="w-full rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
          />
          <span className="text-zinc-400">~</span>
          <input
            type="number"
            min={LISTING_RANGES.year.min}
            max={LISTING_RANGES.year.max}
            value={values.year_max}
            onChange={(e) => update('year_max', e.target.value)}
            placeholder="최대"
            className="w-full rounded border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
          />
        </div>
      </fieldset>

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
