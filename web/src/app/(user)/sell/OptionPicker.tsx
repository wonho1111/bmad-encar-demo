'use client';

// 옵션 하이브리드 피커 (등록·수정 공용) — Story 10.4.
//
// 왜 필요한가: `SellForm`의 옵션 입력은 지금까지 줄바꿈 텍스트에어리어였다(Story 10.3이 남긴
// 임시 UI) — 판매자가 표준 옵션명을 외워 정확히 타이핑해야 했다. 이 컴포넌트는 그 자리를
// 인기 8칩 + "전체 옵션 더보기"(검색+카테고리 체크리스트) + 선택 요약바로 대체해, 통제어휘
// 밖 값을 칩/체크로는 **구조적으로 입력 불가능**하게 만든다(docs/conventions.md §11.3 쓰기
// 검증을 UI 층에서 승격).
//
// controlled 컴포넌트다 — 폼 상태(FormState.options: 줄바꿈 문자열)는 SellForm이 그대로 들고,
// 이 컴포넌트는 표현층일 뿐이다(A3 외과적 변경 — 폼 코어를 한 줄도 안 건드리기 위한 설계,
// 자세한 근거는 spec Design Notes 참조). SellForm이 parseOptionsInput/serializeOptions로
// value(string[])를 브리지한다.
import { useId, useState } from 'react';
import {
  CONTROLLED_OPTIONS,
  OPTION_CATEGORY_ORDER,
  POPULAR_OPTIONS,
  isRareOption,
  toggleOption,
} from '@/lib/options';

type OptionPickerProps = {
  value: string[];
  onChange: (next: string[]) => void;
};

export default function OptionPicker({ value, onChange }: OptionPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState('');
  const searchInputId = useId();

  const selected = new Set(value);
  const normalizedQuery = query.trim().toLowerCase();

  function handleToggle(name: string) {
    onChange(toggleOption(value, name));
  }

  function handleRemove(name: string) {
    onChange(value.filter((n) => n !== name));
  }

  // 카테고리별 검색 필터(공백 trim·대소문자 무시 substring). 매칭 없는 카테고리는 숨긴다.
  const visibleCategories = OPTION_CATEGORY_ORDER.map((category) => ({
    category,
    options: CONTROLLED_OPTIONS[category].filter(
      (name) => normalizedQuery === '' || name.toLowerCase().includes(normalizedQuery),
    ),
  })).filter((entry) => entry.options.length > 0);

  const noMatches = normalizedQuery !== '' && visibleCategories.length === 0;

  return (
    <div className="flex flex-col gap-3">
      {/* 선택 요약바 — value 전 항목을 제거 가능한 칩으로(통제어휘 밖 값도 보존·노출, 조용한
          드롭 금지 — 레거시 비표준값 방어, spec Design Notes). */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border-hairline bg-surface-raised px-3 py-2.5">
        <span className="shrink-0 text-sm font-bold text-brand-petrol-strong">
          선택한 옵션 {value.length}개
        </span>
        {value.map((name) => (
          <span
            key={name}
            className="inline-flex items-center gap-1.5 rounded-full border border-border-hairline bg-surface-base py-1 pr-1 pl-3 text-xs font-medium text-ink-secondary"
          >
            {name}
            <button
              type="button"
              onClick={() => handleRemove(name)}
              aria-label={`${name} 옵션 제거`}
              className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-border-hairline text-[10px] leading-none text-ink-secondary"
            >
              ✕
            </button>
          </span>
        ))}
      </div>

      {/* 인기 옵션 8칩 */}
      <div className="flex flex-wrap gap-2">
        {POPULAR_OPTIONS.map((name) => {
          const isSelected = selected.has(name);
          return (
            <button
              key={name}
              type="button"
              aria-pressed={isSelected}
              onClick={() => handleToggle(name)}
              className={
                isSelected
                  ? 'inline-flex items-center gap-1 rounded-full border border-brand-petrol bg-brand-petrol px-4 py-2 text-sm font-semibold text-white'
                  : 'inline-flex items-center gap-1 rounded-full border border-border-hairline bg-surface-raised px-4 py-2 text-sm font-medium text-ink-secondary'
              }
            >
              {isSelected && <span aria-hidden="true">✓</span>}
              {name}
            </button>
          );
        })}
      </div>

      {/* 전체 옵션 더보기 토글 */}
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center justify-center gap-1.5 rounded-lg border border-border-hairline bg-surface-base px-3 py-2.5 text-sm font-bold text-ink-secondary"
      >
        전체 옵션 더보기
        <span
          aria-hidden="true"
          className={`text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}
        >
          ▾
        </span>
      </button>

      {expanded && (
        <div className="flex flex-col gap-3 rounded-xl border border-border-hairline bg-surface-base p-4">
          <label htmlFor={searchInputId} className="flex flex-col gap-1">
            <span className="text-sm font-medium">옵션 검색</span>
            <input
              id={searchInputId}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="예: 파노라마"
              className="rounded border border-border-hairline bg-surface-raised px-3 py-2 text-sm"
            />
          </label>

          {noMatches && (
            <p role="status" aria-live="polite" className="text-sm text-ink-muted">
              검색 결과가 없어요.
            </p>
          )}

          {visibleCategories.map(({ category, options }) => (
            <div
              key={category}
              className="flex flex-col gap-2 border-t border-border-hairline pt-3 first:border-t-0 first:pt-0"
            >
              <p className="text-xs font-bold tracking-wide text-ink-muted">{category}</p>
              <div className="grid grid-cols-1 gap-x-3 gap-y-1 sm:grid-cols-2">
                {options.map((name) => {
                  const isSelected = selected.has(name);
                  return (
                    <label
                      key={name}
                      className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${
                        isSelected ? 'bg-brand-petrol/10' : ''
                      }`}
                    >
                      <input type="checkbox" checked={isSelected} onChange={() => handleToggle(name)} />
                      <span className="flex-1 text-sm text-ink-primary">{name}</span>
                      {isRareOption(name) && (
                        <span className="shrink-0 rounded-full bg-brand-petrol/10 px-2 py-0.5 text-[10px] font-bold text-brand-petrol-strong">
                          희소
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
