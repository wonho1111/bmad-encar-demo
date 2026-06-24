// 관리자 거래 내역 조회 화면 (FR24) — 서버 컴포넌트, 조회 전용.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 6-3(/admin/listings 전체 매물 관리)의 "조회 전용 · sold 한정" 버전이다.
//   · 차이점 ① status='sold' 필터를 건다(거래 내역 = 판매 완료된 매물).
//   · 차이점 ② 행 액션 컴포넌트(삭제 등)를 두지 않는다(읽기 전용 화면).
// 관리자 세션에선 listings_select_admin(0002, using=is_admin())이 sold 행을 열어주므로,
// RLS 추가 없이 화면에서 status 필터만 걸면 거래 내역이 그대로 온다.
import { createClient } from '@/lib/supabase/server';
import { UNITS, LISTING_STATUS } from '@/lib/constants';

// 목록에 보여줄 최소 필드(요약 표시용).
type SoldListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  status: string;
  created_at: string;
};

export default async function AdminTransactionsPage() {
  const supabase = await createClient();

  // 판매완료(sold) 매물만 최신 등록순 조회 — 거래 내역 = status='sold'.
  //   listings_select_admin(0002, using=is_admin())이 sold 행을 반환하고, 여기서 status 필터로 거래분만 추린다.
  //   error를 함께 받아 "조회 실패"와 "내역 없음"을 구분한다(listings/members 페이지 패턴).
  const { data: listings, error: listingsError } = await supabase
    .from('listings')
    .select('id, manufacturer, model, year, price, status, created_at')
    .eq('status', LISTING_STATUS.SOLD)
    .order('created_at', { ascending: false })
    .returns<SoldListing[]>();

  if (listingsError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/transactions] 거래 내역 조회 실패:', listingsError);
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">거래 내역</h1>
        <p className="text-sm text-zinc-500">
          판매완료된 매물(거래 내역)을 조회합니다. (조회 전용)
        </p>
      </section>

      <section className="flex flex-col gap-3">
        {listingsError ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            거래 내역을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !listings || listings.length === 0 ? (
          <p className="text-sm text-zinc-500">거래 내역이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {listings.map((l) => (
              <li
                key={l.id}
                className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
              >
                <span>
                  [{l.manufacturer}] {l.model} · {l.year}년 ·{' '}
                  {l.price.toLocaleString('ko-KR')}
                  {UNITS.price}
                </span>
                {/* 거래 내역은 전부 sold이므로 "판매완료"(회색) 배지만. 조회 전용이라 액션 버튼 없음. */}
                <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                  판매완료
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
