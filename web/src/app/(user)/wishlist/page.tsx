// 찜한 매물 목록 (Story 10.5, FR58 "행동" — 개인 페이지) — 서버 컴포넌트.
//
// 동작:
//   1) 로그인 사용자만(proxy가 1차 차단하지만, 개인 데이터 화면이라 페이지에서도 명시적으로 확인한다).
//   2) fetchWishlist로 본인 찜 전체를 최신순(찜한 시각 내림차순)으로 조회.
//   3) isWishedListingBlocked로 on_sale(정상 카드)과 판매완료(회색 비활성 타일)를 가른다
//      (하드삭제된 매물의 찜 행은 cascade로 이미 사라져 여기 나타나지 않는다 — @/lib/wishlist 참조).
//   4) 0건이면 빈 상태 안내, 조회 실패면 한국어 에러 안내(search 페이지와 같은 3분기 구조).
//
// ⚠️ 최신순 정렬(코드리뷰 2026-07-22 P2): on_sale 그룹을 통째로 먼저, 판매완료 그룹을 나중에
//   렌더하면 fetchWishlist의 created_at desc 정렬이 그룹 경계에서 깨진다(방금 찜한 sold가 오래전
//   찜한 on_sale보다 아래로 밀림). 그래서 `entries`를 원래 순서 그대로 **한 번만** 순회하며 그 자리에서
//   ListingCard 또는 BlockedWishTile을 고른다. 대표사진 조회(`attachCoverImages`)는 on_sale
//   임베드만 모아 한 번에 호출하되, 결과를 id→ListingCardData Map으로 만들어 순서 보존 렌더에 쓴다.
//
// 매 요청 최신 DB 상태를 반영해야 한다(방금 취소한 찜이 즉시 사라져야 함). 정적화 방지.
import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, type UserRole } from '@/lib/constants';
import { attachCoverImages } from '@/lib/listings';
import { fetchWishlist, isWishedListingBlocked, type WishlistListingEmbed } from '@/lib/wishlist';
import AppHeader from '@/components/layout/AppHeader';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import RemoveWishButton from '@/components/listings/RemoveWishButton';
import ResponsiveGrid from '@/components/ui/ResponsiveGrid';
import EmptyState from '@/components/ui/EmptyState';
import ErrorState from '@/components/ui/ErrorState';

export const dynamic = 'force-dynamic';

// 판매완료(또는 RLS로 안 보이는 타인 소유 sold) 매물의 회색 비활성 타일. 상세 링크 없음(진입 차단,
// FR11·UX-DR20). embed가 있으면(본인 소유 sold) 차량명을 보여주고, 없으면(타인 소유 sold — RLS가
// 값 자체를 안 줌) 일반 문구로 대신한다 — 없는 정보를 지어내지 않는다.
// listingId는 embed=null일 때도 필요해서(찜 해제 대상 지정) entry.listing_id를 별도로 받는다.
function BlockedWishTile({ listingId, embed }: { listingId: string; embed: WishlistListingEmbed }) {
  const title = embed ? `[${embed.manufacturer}] ${embed.model} · ${embed.year}년` : '판매완료된 매물';
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-border-hairline bg-surface-raised p-8 text-center opacity-60 shadow-card dark:shadow-none">
      <span className="rounded-badge border border-border-hairline px-2 py-0.5 text-caption font-medium text-ink-secondary">
        판매완료
      </span>
      <p className="truncate text-body text-ink-secondary">{title}</p>
      {/* 코드리뷰 2026-07-22 P1: sold 찜은 WishButton이 없어 해제 수단이 없었다(영구 클러터).
          opacity-60은 시각 처리일 뿐 클릭을 막지 않는다(pointer-events를 끄는 곳이 없다) — 이 버튼은 그대로 눌린다. */}
      <RemoveWishButton listingId={listingId} />
    </div>
  );
}

export default async function WishlistPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect('/login?redirectedFrom=/wishlist');
  }

  // 상단바용 역할 라벨(홈·search 패턴 재사용).
  const { data: profile } = await supabase.from('profiles').select('role').eq('id', user.id).single();
  const roleLabel = profile?.role ? (ROLE_LABEL[profile.role as UserRole] ?? profile.role) : null;

  const result = await fetchWishlist(supabase, user.id);

  // on_sale 임베드만 모아 대표사진을 한 번에 조회 → id로 다시 찾을 수 있게 Map으로 만든다.
  // (entries 순서를 그대로 보존한 채 렌더하려면, "무엇을 그릴지"와 "순서"를 분리해야 한다 — P2.)
  let onSaleById = new Map<string, ListingCardData>();
  if (!('error' in result)) {
    const onSaleEmbeds = result.entries
      .map((e) => e.listings)
      .filter((e): e is NonNullable<WishlistListingEmbed> => e !== null && !isWishedListingBlocked(e));
    const withImages = onSaleEmbeds.length > 0 ? await attachCoverImages(supabase, onSaleEmbeds) : [];
    onSaleById = new Map(withImages.map((l) => [l.id, l]));
  }

  // entries를 원래(최신순) 순서 그대로 한 번만 순회하며 그 자리에서 카드/타일을 고른다(P2).
  let tiles: ReactNode[] = [];
  if (!('error' in result)) {
    tiles = result.entries.map((entry) => {
      if (isWishedListingBlocked(entry.listings)) {
        return <BlockedWishTile key={entry.listing_id} listingId={entry.listing_id} embed={entry.listings} />;
      }
      const listing = onSaleById.get(entry.listing_id);
      // isWishedListingBlocked가 false면 embed는 non-null이고 attachCoverImages가 같은 id로
      // 돌려주므로 이 조회는 항상 성공한다 — 방어적으로 못 찾으면 조용히 생략(렌더 전체를 막지 않음).
      if (!listing) return null;
      return <ListingCard key={entry.listing_id} listing={listing} wished authed />;
    });
  }

  return (
    <>
      <AppHeader roleLabel={roleLabel ?? undefined} email={user.email} currentPath="/wishlist" />
      <main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
        <h1 className="text-2xl font-semibold">찜한 매물</h1>

        {'error' in result ? (
          <ErrorState
            tone="danger"
            message="찜 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
          />
        ) : result.entries.length === 0 ? (
          <EmptyState icon="♡" title="아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요." />
        ) : (
          <ResponsiveGrid>{tiles}</ResponsiveGrid>
        )}
      </main>
    </>
  );
}
