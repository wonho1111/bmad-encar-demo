// 구매자 매물 상세 조회 (FR10) — 서버 컴포넌트.
//
// 동작:
//   1) 동적 라우트 params에서 id를 읽는다(Next.js 16: params는 Promise → await).
//   2) 그 id의 매물을 조회하되 판매중(on_sale)만 — FR11 단일 규칙은 buyerListingsQuery(@/lib/listings)에서 비롯된다.
//   3) 찾으면 FR5 15필드 + 설명·옵션·상태를 표시(사진 없음). 못 찾으면 "찾을 수 없음" 안내,
//      조회 자체가 실패하면 별도 한국어 에러 안내(둘을 구분 — 2-3 edit·3-1 패턴).
//
// 보호: proxy가 /listings 비로그인 1차 차단. 여기선 로그인 사용자(구매자·판매자 공통)가 on_sale을 본다.
//   별도 역할 게이트 없음 — on_sale은 RLS상 모두에게 공개.
//
// FR11 비노출 규칙(판매완료는 구매자에게 안 보임)과 이중 방어 근거는 @/lib/listings 한 곳에 모았다(단일 출처).
//
// CM3(즉시 비노출): cookies() 기반 인증으로 매 요청 DB를 다시 읽는 동적 렌더다.
//   매물이 sold로 바뀌면 재조회 시 즉시 "찾을 수 없음"이 된다. 정적 캐시 잔존 방지로 force-dynamic 명시.
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, UNITS, type UserRole } from '@/lib/constants';
import { buyerListingsQuery } from '@/lib/listings';
import AppHeader from '@/components/layout/AppHeader';
import ListingDetailFields from '@/components/listings/ListingDetailFields';
import InquiryButton from './InquiryButton';

// CM3 보장: 상세도 매 요청 최신 DB 상태 반영(sold 즉시 비노출). 정적화 방지.
export const dynamic = 'force-dynamic';

// 상세 화면에 표시할 FR5 15필드 + 상태(라벨용) + seller_id(문의 버튼 노출 판단용). 사진 없음.
type ListingDetail = {
  id: string;
  seller_id: string; // 이 매물의 판매자(매물주). 본인이면 "문의하기"를 숨긴다(자기 자신과 채팅 불가).
  manufacturer: string;
  model: string;
  body_type: string;
  year: number;
  price: number; // 원(KRW)
  mileage: number; // km
  color: string;
  fuel: string;
  transmission: string;
  displacement: number; // cc
  seats: number;
  region: string;
  accident_free: boolean;
  seller_name: string | null; // 판매자 표시 이름(이메일 @앞부분, 0007). 상세에 표시.
  options: string[] | null; // text[]; 빈 배열·null 가능
  description: string | null; // nullable
  status: string;
};

export default async function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params; // Next.js 16: params는 Promise라 await 필요.
  const supabase = await createClient();

  // 상단바용 역할 라벨(홈·/search 패턴 재사용 — profiles_select_self RLS로 본인 행 읽기).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 단일 매물 조회 — 구매자 관점(판매중만) 시작점 buyerListingsQuery(FR11 단일 출처) + id 일치.
  //   maybeSingle(): 0건이면 null(존재하지 않음·sold·접근 권한 없음). edit 페이지와 동일 패턴.
  const { data: listing, error } = await buyerListingsQuery(
    supabase,
    'id, seller_id, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, seller_name, options, description, status',
  )
    .eq('id', id)
    .maybeSingle<ListingDetail>();

  if (error) {
    // 원본은 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분(AC4).
    console.error('[listings/detail] 매물 상세 조회 실패:', error);
  }

  const header = <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} />;

  // 조회 실패(네트워크·RLS·DB) — "못 찾음"과 구분해 빨강 에러 안내(AC4).
  if (error) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
          <h1 className="text-2xl font-semibold">매물 상세</h1>
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
          </p>
          <Link
            href="/search"
            className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
          >
            매물 탐색으로
          </Link>
        </main>
      </>
    );
  }

  // 못 찾음(존재하지 않는 id·sold·접근 권한 없음) → 구매자에게 비노출(FR11, AC2).
  if (!listing) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
          <h1 className="text-2xl font-semibold">매물 상세</h1>
          <p role="alert" className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            매물을 찾을 수 없습니다. 판매가 완료되었거나 삭제된 매물일 수 있습니다.
          </p>
          <Link
            href="/search"
            className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
          >
            매물 탐색으로
          </Link>
        </main>
      </>
    );
  }

  // 부제목(연식·가격)에 쓸 가격 문자열만 여기서 만든다. 나머지 필드 표시는 ListingDetailFields가 담당.
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;

  return (
    <>
      {header}
      <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
        {/* 제목 = 제조사·모델·연식 요약 + 상태 배지(on_sale만 보이므로 "판매중") */}
        <section className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">
              [{listing.manufacturer}] {listing.model}
            </h1>
            <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-300">
              판매중
            </span>
          </div>
          <p className="text-sm text-zinc-500">
            {listing.year}년 · {priceText}
          </p>
          {/* 문의하기 (FR19) — 이 매물의 판매자와 채팅방을 연다(없으면 생성, 있으면 재사용).
              본인이 이 매물의 판매자면 숨긴다(자기 자신과 채팅 불가 — DB의 CHECK(buyer<>seller)로도 막힘, 앱측 1차 비노출). */}
          {user && user.id !== listing.seller_id && (
            <InquiryButton listingId={listing.id} />
          )}
        </section>

        {/* 기본 정보·옵션·설명 = 관리자 상세와 공유하는 표시부(단일 출처). */}
        <ListingDetailFields listing={listing} />

        <Link
          href="/search"
          className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
        >
          매물 탐색으로
        </Link>
      </main>
    </>
  );
}
