// 관리자 매물 상세 (FR23 보강) — 서버 컴포넌트.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 왜 구매자 상세((user)/listings/[id])를 그대로 안 쓰나:
//   구매자 상세는 buyerListingsQuery로 status='on_sale'만 조회한다(FR11). 그런데 관리자는
//   매물 관리·거래 내역·채팅 관리에서 "판매완료(sold)" 매물의 상세도 봐야 한다. 그래서 상태 필터 없이
//   조회하는 관리자 전용 상세를 따로 둔다(listings_select_admin RLS, 0002 = 관리자는 sold 포함 전부 조회).
//
// 화면 본문(15필드·옵션·설명)은 구매자 상세와 동일하므로 공유 컴포넌트 ListingDetailFields로 그린다.
//   제목·상태 배지(판매중/판매완료)·삭제·목록 링크처럼 관리자 맥락 요소만 이 페이지가 직접 그린다.
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { UNITS, LISTING_STATUS } from '@/lib/constants';
import ListingDetailFields, {
  type ListingDetailFieldsData,
} from '@/components/listings/ListingDetailFields';
import ListingAdminActions from '../ListingAdminActions';

// 관리자는 매 진입 시 최신 DB 상태를 봐야 한다(다른 관리자가 그새 삭제·판매완료 처리했을 수 있음). 정적화 방지.
export const dynamic = 'force-dynamic';

// 공유 표시 필드(ListingDetailFieldsData) + 관리자 화면용 식별/상태 필드.
type AdminListingDetail = ListingDetailFieldsData & {
  id: string;
  status: string;
};

export default async function AdminListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params; // Next.js 16: params는 Promise라 await 필요(구매자 상세와 동일 패턴).
  const supabase = await createClient();

  // 상태 필터 없이 단일 매물 조회 — 관리자 RLS가 sold 포함 모든 행을 반환한다(FR11 예외).
  //   maybeSingle(): 0건이면 null(존재하지 않거나 삭제됨). error와 구분해 처리(listings/transactions 패턴).
  const { data: listing, error } = await supabase
    .from('listings')
    .select(
      'id, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, options, description, status',
    )
    .eq('id', id)
    .maybeSingle<AdminListingDetail>();

  if (error) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/listings/detail] 매물 상세 조회 실패:', error);
  }

  const backLink = (
    <Link
      href="/admin/listings"
      className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
    >
      매물 관리로
    </Link>
  );

  // 조회 실패(네트워크·RLS·DB) — "없음"과 구분해 빨강 에러 안내.
  if (error) {
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">매물 상세</h1>
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
        </p>
        {backLink}
      </main>
    );
  }

  // 못 찾음(존재하지 않는 id·이미 삭제됨).
  if (!listing) {
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">매물 상세</h1>
        <p role="alert" className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
          매물을 찾을 수 없습니다. 이미 삭제된 매물일 수 있습니다.
        </p>
        {backLink}
      </main>
    );
  }

  const isOnSale = listing.status === LISTING_STATUS.ON_SALE;
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      {/* 제목 = 제조사·모델 + 상태 배지(판매중=초록/판매완료=회색, 목록 화면과 동일 규칙) */}
      <section className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold">
            [{listing.manufacturer}] {listing.model}
          </h1>
          <span
            className={
              isOnSale
                ? 'rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-300'
                : 'rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'
            }
          >
            {isOnSale ? '판매중' : '판매완료'}
          </span>
        </div>
        <p className="text-sm text-zinc-500">
          {listing.year}년 · {priceText}
        </p>
        {/* 관리자는 여기서도 바로 삭제 가능(목록과 동일 액션). 삭제 후엔 매물 관리 목록으로 이동. */}
        <div className="mt-1">
          <ListingAdminActions
            listingId={listing.id}
            label={`[${listing.manufacturer}] ${listing.model}`}
            redirectTo="/admin/listings"
          />
        </div>
      </section>

      {/* 기본 정보·옵션·설명 = 구매자 상세와 공유하는 표시부(단일 출처). */}
      <ListingDetailFields listing={listing} />

      {backLink}
    </main>
  );
}
