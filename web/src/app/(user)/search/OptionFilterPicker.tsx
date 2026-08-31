'use client';

// 필터 검색용 옵션 다중 선택 (개선 2, 2026-09-01) — 등록 폼(SellForm)의 OptionPicker와 같은
// 옵션 통제어휘 상수(@/lib/options)를 그대로 재사용한다(중복 정의 금지 — 사용자 지시).
//
// OptionPicker를 그대로 재사용하지 않는 이유: 그건 "쓰기"(등록/수정) 전용이라 선택 요약바의
// 제거 칩·통제어휘 밖(레거시) 값 보존 같은 쓰기 검증 관심사가 섞여 있다(OptionPicker.tsx 상단
// 주석 참조). 필터는 항상 통제어휘 **안**에서만 고르므로 그 관심사가 필요 없고, 시맨틱도 다르다
// — SellForm은 "이 매물이 가진 옵션 집합"을, 여기는 "이 조건을 만족해야 하는 옵션 집합"을 고른다
// (질의 쪽은 page.tsx가 .contains()로 전부 보유 AND 의미를 적용한다). 그래서 표현만 옮겨 온
// 전용 컴포넌트를 둔다(A2) — 값 상수는 공유하고 UI 조합만 다르다.
import { useId, useState } from 'react';
import { CONTROLLED_OPTIONS, OPTION_CATEGORY_ORDER, POPULAR_OPTIONS } from '@/lib/options';
import { FIELD_LABEL_CLASS } from '@/components/ui/formField';

type OptionFilterPickerProps = {
  value: string[];
  onChange: (next: string[]) => void;
};

export default function OptionFilterPicker({ value, onChange }: OptionFilterPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState('');
  const searchInputId = useId();

  const selected = new Set(value);
  const normalizedQuery = query.trim().toLowerCase();

  function toggle(name: string) {
    onChange(selected.has(name) ? value.filter((n) => n !== name) : [...value, name]);
  }

  // 카테고리별 검색 필터(OptionPicker와 동일 로직 — 공백 trim·대소문자 무시 substring).
  const visibleCategories = OPTION_CATEGORY_ORDER.map((category) => ({
    category,
    options: CONTROLLED_OPTIONS[category].filter(
      (name) => normalizedQuery === '' || name.toLowerCase().includes(normalizedQuery),
    ),
  })).filter((entry) => entry.options.length > 0);

  const noMatches = normalizedQuery !== '' && visibleCategories.length === 0;

  return (
    <fieldset className="flex flex-col gap-2 text-sm">
      <span className={FIELD_LABEL_CLASS}>옵션(다중 선택 — 선택한 옵션 전부 보유한 매물만)</span>

      {/* 인기 옵션 8칩 — 빠른 선택. */}
      <div className="flex flex-wrap gap-2">
        {POPULAR_OPTIONS.map((name) => {
          const isSelected = selected.has(name);
          return (
            <button
              key={name}
              type="button"
              aria-pressed={isSelected}
              onClick={() => toggle(name)}
              className={
                isSelected
                  ? 'inline-flex items-center gap-1 rounded-full border border-brand-petrol bg-brand-petrol px-3 py-1.5 text-sm font-semibold text-white'
                  : 'inline-flex items-center gap-1 rounded-full border border-border-hairline bg-surface-raised px-3 py-1.5 text-sm font-medium text-ink-secondary'
              }
            >
              {isSelected && <span aria-hidden="true">✓</span>}
              {name}
            </button>
          );
        })}
      </div>

      {/* 전체 옵션 더보기 — 카테고리별 검색+체크리스트(인기 8종 밖의 옵션도 고를 수 있어야 한다). */}
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-fit items-center justify-center gap-1.5 rounded-lg border border-border-hairline bg-surface-raised px-3 py-2 text-sm font-bold text-ink-secondary"
      >
        전체 옵션 더보기
        <span aria-hidden="true" className={`text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▾
        </span>
      </button>

      {expanded && (
        <div className="flex flex-col gap-3 rounded-xl border border-border-hairline bg-surface-raised p-3">
          <label htmlFor={searchInputId} className="flex flex-col gap-1">
            <span className={FIELD_LABEL_CLASS}>옵션 검색</span>
            <input
              id={searchInputId}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="예: 어댑티브크루즈"
              className="rounded border border-border-hairline bg-surface-base px-2 py-1.5 text-sm"
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
                      className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${isSelected ? 'bg-brand-petrol/10' : ''}`}
                    >
                      <input type="checkbox" checked={isSelected} onChange={() => toggle(name)} />
                      <span className="flex-1 text-sm text-ink-primary">{name}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </fieldset>
  );
}
