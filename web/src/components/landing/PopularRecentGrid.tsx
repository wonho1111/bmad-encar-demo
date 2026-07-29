// 랜딩 인기/최신 매물 2단 발췌 그리드 (Story 11.4, FR34) — 서버 컴포넌트.
//
// `CategoryChips` 아래에서 인기(view_count desc)·최신(created_at desc) 각 4건을 보여준다.
// 데이터 조회(`fetchPopularAndRecentListings`)는 `page.tsx`가 미리 해서 props로 넘긴다 — 이
// 컴포넌트는 표시만 한다(page.tsx가 로그인·비로그인 두 분기에서 같은 컴포넌트를 재사용).
//
// 기존 로그인 홈의 "최근 매물" 단일 섹션은 이 그리드의 "최신" 단으로 흡수돼 대체된다(신규 작성이
// 아니라 이관 — Design Notes 참조). "전체 보기"는 `/search`로만 진입한다(필터·쿼리파라미터 없음 —
// 랜딩은 URL 쿼리를 소유하지 않는다).
import Link from 'next/link';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import ResponsiveGrid from '@/components/ui/ResponsiveGrid';
import type { PopularRecentSection } from '@/lib/listings';

// 한 단(인기 또는 최신) — 제목 + "전체 보기" + 그리드/빈 상태/에러 문구를 공통으로 처리한다.
// 두 단이 마크업을 그대로 공유해야 인기 단만 스타일이 갈리는 일이 없다(중복 제거).
function ListingGridSection({
  title,
  section,
  wishedIds,
  authed,
}: {
  title: string;
  section: PopularRecentSection;
  wishedIds: Set<string>;
  authed: boolean;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-section font-bold text-ink-primary">{title}</h2>
        <Link href="/search" className="text-sm text-zinc-500 hover:underline">
          전체 보기 →
        </Link>
      </div>
      {'error' in section ? (
        // 이 단만 실패 — 다른 단·히어로·차종칩 렌더는 막지 않는다(intent-contract Always).
        // 기존 "최근 매물" 섹션의 alert처럼 복구 링크를 함께 둔다 — alert만 듣는 스크린리더
        // 사용자도 그 자리에서 바로 행동할 수 있게(코드리뷰 patch, 위 "전체 보기"는 별개 요소라
        // alert와 함께 읽히지 않는다).
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          매물을 불러오지 못했습니다.{' '}
          <Link href="/search" className="underline">
            매물 전체 보기
          </Link>
        </p>
      ) : section.listings.length === 0 ? (
        <p className="text-sm text-zinc-500">아직 등록된 매물이 없습니다.</p>
      ) : (
        // D5: 가로폭은 열 수로만 흡수한다(≥1100px 4열 · 640~1099px 2열 · <640px 1열).
        <ResponsiveGrid>
          {section.listings.map((l: ListingCardData) => (
            <ListingCard key={l.id} listing={l} wished={wishedIds.has(l.id)} authed={authed} />
          ))}
        </ResponsiveGrid>
      )}
    </section>
  );
}

export default function PopularRecentGrid({
  popular,
  recent,
  wishedIds,
  authed,
}: {
  popular: PopularRecentSection;
  recent: PopularRecentSection;
  // 찜 오버레이 — 두 단의 id를 합쳐 한 번만 조회한 결과(page.tsx의 책임, 사용자별 조회라 여기
  // 데이터 조회에 포함하지 않는다).
  wishedIds: Set<string>;
  authed: boolean;
}) {
  return (
    <div className="flex flex-col gap-8">
      <ListingGridSection title="지금 인기" section={popular} wishedIds={wishedIds} authed={authed} />
      <ListingGridSection title="방금 올라온 매물" section={recent} wishedIds={wishedIds} authed={authed} />
    </div>
  );
}
