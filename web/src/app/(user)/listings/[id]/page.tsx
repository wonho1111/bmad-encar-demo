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

// CM3 보장: 상세도 매 요청 최신 DB 상태 반영(sold 즉시 비노출). 정적화 방지.
export const dynamic = 'force-dynamic';

// 상세 화면에 표시할 FR5 15필드 + 상태(라벨용). 사진 없음.
type ListingDetail = {
  id: string;
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
  options: string[] | null; // text[]; 빈 배열·null 가능
  description: string | null; // nullable
  status: string;
};

// 라벨-값 한 줄. 단위·표시는 호출부에서 이미 한국어 문자열로 만들어 넘긴다.
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-zinc-100 py-2 text-sm last:border-0 dark:border-zinc-800">
      <span className="text-zinc-500">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}

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
    'id, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, options, description, status',
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

  // 단위·표시 규칙(conventions §3): 천단위 콤마 + 단위.
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;
  const mileageText = `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}`;
  const displacementText = `${listing.displacement.toLocaleString('ko-KR')}${UNITS.displacement}`;
  const options = listing.options ?? [];

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
        </section>

        {/* 기본 정보(15필드 중 수치·고정목록 필드) */}
        <section className="flex flex-col">
          <h2 className="mb-1 text-lg font-semibold">기본 정보</h2>
          <Field label="제조사" value={listing.manufacturer} />
          <Field label="모델" value={listing.model} />
          <Field label="차종" value={listing.body_type} />
          <Field label="연식" value={`${listing.year}년`} />
          <Field label="가격" value={priceText} />
          <Field label="주행거리" value={mileageText} />
          <Field label="색상" value={listing.color} />
          <Field label="연료" value={listing.fuel} />
          <Field label="변속기" value={listing.transmission} />
          <Field label="배기량" value={displacementText} />
          <Field label="승차인원" value={`${listing.seats}인승`} />
          <Field label="지역" value={listing.region} />
          <Field label="사고이력" value={listing.accident_free ? '무사고' : '사고이력 있음'} />
        </section>

        {/* 옵션(text[]) — 빈 배열이면 안내 */}
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">옵션</h2>
          {options.length === 0 ? (
            <p className="text-sm text-zinc-500">등록된 옵션이 없습니다.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {options.map((opt, i) => (
                <li
                  key={`${opt}-${i}`}
                  className="rounded border border-zinc-200 px-2 py-0.5 text-xs dark:border-zinc-700"
                >
                  {opt}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 설명(nullable) — 비면 안내, 있으면 줄바꿈 보존 */}
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">설명</h2>
          {listing.description && listing.description.trim() !== '' ? (
            <p className="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
              {listing.description}
            </p>
          ) : (
            <p className="text-sm text-zinc-500">등록된 설명이 없습니다.</p>
          )}
        </section>

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
