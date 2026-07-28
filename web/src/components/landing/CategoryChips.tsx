// 차종 빠른 진입 칩 (spec-11-3, FR35) — 순수 카탈로그 필터라 AI가 아니라 `/search`로 직접 링크한다.
//   게이트 없음: /search는 보호 경로가 아니므로 로그인 여부와 무관하게 항상 동작(로그인 게이트 로직 없음).
// 서버 컴포넌트 — 클릭이 곧 <Link> 이동이라 클라이언트 상태·이벤트 핸들러가 필요 없다.
//
// 왜 6개뿐인가(목업은 9개): "세단"·"친환경"·"수입"은 LISTING_OPTIONS.body_type/fuel(DB CHECK와
// 바이트 단위 일치가 요구되는 단일 출처)에 대응 값이 없다 — 세단은 3개 body_type에 걸쳐 있고,
// 친환경은 하이브리드+전기 OR 조건이라 /search의 단일 .eq() 구조를 벗어나며(스토리 범위 밖),
// 수입은 원산지 컬럼 자체가 없다. 라벨과 다른 결과가 나오는 칩을 만들지 않는다
// ("존재 확인"≠"작동 확인", CLAUDE.md B9). 근거 전문은 spec Design Notes 참고.
import Link from 'next/link';
import { LISTING_OPTIONS } from '@/lib/constants';

// body_type/fuel 값의 타입을 LISTING_OPTIONS에서 직접 뽑아 쓴다 — 리터럴을 손으로 다시 적지 않고
// 유니언 타입으로 강제하면, 나중에 constants.ts의 철자가 바뀔 때 여기가 타입에러로 즉시 깨진다
// (`npx tsc --noEmit`가 실행되는 검사가 된다 — 주석이 아니라 컴파일러가 화이트리스트를 지킨다).
type BodyType = (typeof LISTING_OPTIONS.body_type)[number];
type Fuel = (typeof LISTING_OPTIONS.fuel)[number];

type CategoryChip =
  | { label: string; query: null }
  | { label: string; query: { body_type: BodyType } }
  | { label: string; query: { fuel: Fuel } };

// 순서·라벨은 Design Notes 확정값 그대로: 전체·경차·SUV·전기·화물·승합.
const CATEGORY_CHIPS: readonly CategoryChip[] = [
  { label: '전체', query: null },
  { label: '경차', query: { body_type: '경차' } },
  { label: 'SUV', query: { body_type: 'SUV' } },
  { label: '전기', query: { fuel: '전기' } },
  { label: '화물', query: { body_type: '화물차' } },
  { label: '승합', query: { body_type: '승합차' } },
];

function hrefFor(chip: CategoryChip): string {
  if (!chip.query) return '/search';
  const [key, value] = Object.entries(chip.query)[0];
  return `/search?${key}=${encodeURIComponent(value)}`;
}

export default function CategoryChips() {
  return (
    <nav aria-label="차종 빠른 진입" className="bg-surface-base">
      {/* overflow-x-auto — 모바일 폭에서 6개가 한 줄에 다 안 들어와도 가로 스크롤로 흡수(줄바꿈 금지,
          AppHeader의 SiteNav·ResponsiveGrid와 같은 반응형 원칙: 가로배치를 세로로 접지 않는다). */}
      <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-6 py-5 scrollbar-hide">
        {CATEGORY_CHIPS.map((chip) => (
          <Link
            key={chip.label}
            href={hrefFor(chip)}
            className="shrink-0 whitespace-nowrap rounded-full border border-border-hairline bg-surface-raised px-4 py-2 text-sm font-semibold text-ink-secondary transition-colors hover:border-brand-petrol hover:text-brand-petrol"
          >
            {chip.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
