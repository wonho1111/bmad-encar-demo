// 관리자 전체 매물 관리 화면 (FR23) — 서버 컴포넌트.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 구성:
//   1) 전체 매물 목록 — listings_select_admin RLS(0002)로 관리자는 "판매완료(sold) 포함" 전체 행을 본다.
//      · ⚠️ FR11(구매자에게 판매완료 비노출)의 예외다. 일반 SELECT 정책은 "on_sale ∪ 본인 ∪ 관리자" OR 결합인데,
//        관리자 세션에선 is_admin()=true라 모든 행이 열린다 → seller_id·status 필터 없이 select 하면 전부(sold 포함) 온다.
//        (SellPage는 "내 매물"만 보려고 seller_id 필터를 넣었지만, 여기선 정반대로 전부 보는 게 목적이라 필터를 뺀다.)
//   2) 행마다 삭제 액션(ListingAdminActions, 클라이언트 컴포넌트) — 부적절 매물 제거(FR23).
//      정지/수정 같은 부가 액션은 관리 요구에 없어 넣지 않는다(범위 컷). 판매완료 처리(2-4)는 판매자 동선이지 관리자 동선이 아니다.
import { createClient } from '@/lib/supabase/server';
import { UNITS, LISTING_STATUS } from '@/lib/constants';
import ListingAdminActions from './ListingAdminActions';

// 목록에 보여줄 최소 필드(요약 표시용).
type AdminListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  status: string;
  created_at: string;
};

export default async function AdminListingsPage() {
  const supabase = await createClient();

  // 전체 매물 최신 등록순 조회 — seller_id·status 필터를 두지 않는다(관리자는 전부 본다).
  //   listings_select_admin(0002, using=is_admin())이 sold 포함 전체 행을 반환한다(FR11 예외).
  //   error를 함께 받아 "조회 실패"와 "매물 없음"을 구분한다(SellPage/MembersPage 패턴).
  const { data: listings, error: listingsError } = await supabase
    .from('listings')
    .select('id, manufacturer, model, year, price, status, created_at')
    .order('created_at', { ascending: false })
    .returns<AdminListing[]>();

  if (listingsError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/listings] 매물 목록 조회 실패:', listingsError);
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">매물 관리</h1>
        <p className="text-sm text-zinc-500">
          판매완료 포함 전체 매물을 조회하고 부적절한 매물을 삭제할 수 있습니다.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        {listingsError ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            매물 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !listings || listings.length === 0 ? (
          <p className="text-sm text-zinc-500">매물이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {listings.map((l) => {
              const isOnSale = l.status === LISTING_STATUS.ON_SALE;
              return (
                <li
                  key={l.id}
                  className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
                >
                  <span>
                    [{l.manufacturer}] {l.model} · {l.year}년 ·{' '}
                    {l.price.toLocaleString('ko-KR')}
                    {UNITS.price}
                  </span>
                  <div className="flex items-center gap-3">
                    {/* 상태 배지: 판매중=초록 / 판매완료=회색 (SellPage 스타일). sold도 그대로 보이는 게 핵심(FR11 예외). */}
                    <span
                      className={
                        isOnSale
                          ? 'rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-300'
                          : 'rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'
                      }
                    >
                      {isOnSale ? '판매중' : '판매완료'}
                    </span>
                    <ListingAdminActions
                      listingId={l.id}
                      label={`[${l.manufacturer}] ${l.model}`}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
