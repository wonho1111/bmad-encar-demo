// 관리자 거래 내역 조회 화면 (FR24) — 서버 컴포넌트, 조회 전용.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 6-3(/admin/listings 전체 매물 관리)의 "조회 전용 · sold 한정" 버전이다.
//   · status='sold' 필터를 건다(거래 내역 = 판매 완료된 매물).
//   · 행 삭제 같은 변이 액션은 두지 않는다(읽기 전용 화면).
// 관리자 세션에선 listings_select_admin(0002, using=is_admin())이 sold 행을 열어주므로,
// RLS 추가 없이 화면에서 status 필터만 걸면 거래 내역이 그대로 온다.
//
// 보강(사용자 요청):
//   ① 요약 통계 — 상단에 "총 N건 · 거래액 합계 …원". 가격 합산은 순수 계산(DB 변경 없음).
//   ② 거래일(간이) — 판매 완료 시각은 별도 컬럼(sold_at)이 없다. 대신 updated_at(마지막 수정 시각)을
//      거래일로 근사 표시·정렬한다. 구매완료 처리(2-4)가 status='sold'로 UPDATE할 때 트리거가 updated_at을
//      갱신하므로, 판매 후 수정이 없었다면 사실상 판매 시각과 같다. (정확값이 필요하면 sold_at 컬럼 도입.)
//   ③ 상세 링크 — 각 행을 누르면 관리자 매물 상세(/admin/listings/[id])로 이동한다.
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { UNITS, LISTING_STATUS } from '@/lib/constants';

// 목록에 보여줄 최소 필드(요약 표시용) + updated_at(거래일 근사).
type SoldListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  status: string;
  updated_at: string;
};

export default async function AdminTransactionsPage() {
  const supabase = await createClient();

  // 판매완료(sold) 매물만 거래일(updated_at) 최신순 조회 — 거래 내역 = status='sold'.
  //   거래 내역답게 "최근 거래"가 위로 오도록 updated_at 기준 정렬(등록일 created_at이 아니라).
  //   error를 함께 받아 "조회 실패"와 "내역 없음"을 구분한다(listings/members 페이지 패턴).
  const { data: listings, error: listingsError } = await supabase
    .from('listings')
    .select('id, manufacturer, model, year, price, status, updated_at')
    .eq('status', LISTING_STATUS.SOLD)
    .order('updated_at', { ascending: false })
    .returns<SoldListing[]>();

  if (listingsError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/transactions] 거래 내역 조회 실패:', listingsError);
  }

  const rows = listings ?? [];
  // 요약 통계 — 건수 + 거래액 합계(원). 순수 계산이라 DB 변경 없음.
  const totalCount = rows.length;
  const totalAmount = rows.reduce((sum, l) => sum + l.price, 0);

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
        ) : totalCount === 0 ? (
          <p className="text-sm text-zinc-500">거래 내역이 없습니다.</p>
        ) : (
          <>
            {/* ① 요약 통계 — 총 거래 건수 + 거래액 합계 */}
            <div className="flex items-center justify-between gap-3 rounded border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm dark:border-zinc-800 dark:bg-zinc-900">
              <span className="text-zinc-500">총 거래</span>
              <span className="font-medium">
                {totalCount.toLocaleString('ko-KR')}건 · 거래액 합계{' '}
                {totalAmount.toLocaleString('ko-KR')}
                {UNITS.price}
              </span>
            </div>

            <ul className="flex flex-col gap-2">
              {listings!.map((l) => (
                <li
                  key={l.id}
                  className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
                >
                  {/* ③ 요약을 누르면 관리자 매물 상세로 이동(sold 매물도 조회 가능). */}
                  <Link
                    href={`/admin/listings/${l.id}`}
                    className="flex flex-1 flex-col gap-0.5 hover:underline"
                  >
                    <span className="font-medium">
                      [{l.manufacturer}] {l.model} · {l.year}년 ·{' '}
                      {l.price.toLocaleString('ko-KR')}
                      {UNITS.price}
                    </span>
                    {/* ② 거래일(간이) — updated_at 근사. 날짜만 간결히. */}
                    <span className="text-xs text-zinc-500">
                      거래일 {new Date(l.updated_at).toLocaleDateString('ko-KR')}
                    </span>
                  </Link>
                  {/* 거래 내역은 전부 sold이므로 "판매완료"(회색) 배지만. 조회 전용이라 액션 버튼 없음. */}
                  <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                    판매완료
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </main>
  );
}
