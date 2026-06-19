// 판매자 매물 등록 화면 (FR5·FR7) — 서버 컴포넌트.
// 역할 게이트는 (user)/sell/layout.tsx의 requireRole(seller)이 담당하므로 여기서는 데이터만 준비한다.
//
// 구성:
//   1) 등록 폼(SellForm, 클라이언트 컴포넌트) — 15필드 입력·검증·INSERT.
//   2) "내가 등록한 매물" 섹션 — 방금 등록한 매물이 status=on_sale로 "즉시 노출"됨을 확인(FR7).
//      · listings_select_own RLS(2-1)로 본인 매물만 조회된다.
//      · 구매자용 전체 목록·필터·상세는 Epic 3, 수정·삭제는 2-3, 구매완료는 2-4 소관이라 여기 없음(범위 컷).
import { createClient } from '@/lib/supabase/server';
import { UNITS, LISTING_STATUS } from '@/lib/constants';
import SellForm from './SellForm';

// 본인 매물 목록에 보여줄 최소 필드만 선택(요약 표시용).
type OwnListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  status: string;
  created_at: string;
};

export default async function SellPage() {
  const supabase = await createClient();

  // 현재 로그인 판매자 — 본인 매물만 필터하기 위해 id가 필요하다.
  //   ⚠️ RLS만으로는 부족: listings SELECT 정책은 "on_sale ∪ 본인 ∪ 관리자"의 OR 결합이라
  //   필터 없이 select 하면 "남의 판매중 매물"까지 섞여 들어온다(2-1 설계). "내가 등록한 매물"을
  //   정확히 보이려면 앱 쿼리에서 seller_id를 명시 필터해야 한다(2-3 본인매물 관리도 같은 규칙).
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 본인 매물 최신순 조회 — seller_id 명시 필터 + RLS(listings_select_own) 이중.
  // error를 함께 받는다: 빠뜨리면 조회 실패(네트워크·RLS·DB 오류)가 "매물 없음"과 똑같이 보여
  // 방금 등록한 매물이 사라진 것처럼 오인된다(FR7 즉시 노출 신뢰성 훼손). 실패는 한국어로 구분 표시한다.
  const { data: listings, error: listingsError } = await supabase
    .from('listings')
    .select('id, manufacturer, model, year, price, status, created_at')
    .eq('seller_id', user?.id ?? '')
    .order('created_at', { ascending: false })
    .returns<OwnListing[]>();

  if (listingsError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분.
    console.error('[sell] 본인 매물 조회 실패:', listingsError);
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">매물 등록</h1>
        <p className="text-sm text-zinc-500">
          차량 정보를 입력해 매물을 등록하면 구매자에게 바로 노출됩니다(관리자 승인 없음).
        </p>
      </section>

      <SellForm />

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">내가 등록한 매물</h2>
        {listingsError ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            매물 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !listings || listings.length === 0 ? (
          <p className="text-sm text-zinc-500">아직 등록한 매물이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {listings.map((l) => (
              <li
                key={l.id}
                className="flex items-center justify-between rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
              >
                <span>
                  [{l.manufacturer}] {l.model} · {l.year}년 ·{' '}
                  {l.price.toLocaleString('ko-KR')}
                  {UNITS.price}
                </span>
                <span
                  className={
                    l.status === LISTING_STATUS.ON_SALE
                      ? 'rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-300'
                      : 'rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'
                  }
                >
                  {l.status === LISTING_STATUS.ON_SALE ? '판매중' : '판매완료'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
