// 매물 등록 화면 (FR5·FR7) — 서버 컴포넌트.
// 게이트는 (user)/sell/layout.tsx의 requireUser()가 로그인만 확인하므로 여기서는 데이터만 준비한다.
// 본인 매물 여부는 role이 아니라 listings RLS의 소유권 정책(seller_id = auth.uid())이 집행한다(spec-14-3).
//
// 구성:
//   1) 등록 폼(SellForm, 클라이언트 컴포넌트) — 15필드 입력·검증·INSERT.
//   2) "내가 등록한 매물" 섹션 — 방금 등록한 매물이 status=on_sale로 "즉시 노출"됨을 확인(FR7).
//      · listings_select_own RLS(2-1)로 본인 매물만 조회된다.
//      · 구매자용 전체 목록·필터·상세는 Epic 3, 수정·삭제는 2-3, 구매완료는 2-4 소관이라 여기 없음(범위 컷).
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { LISTING_STATUS, UNITS } from '@/lib/constants';
import { attachCoverImages } from '@/lib/listings';
import ListingCardImage from '@/components/listings/ListingCardImage';
import Badge from '@/components/ui/Badge';
import SellForm from './SellForm';
import ListingActions from './ListingActions';
import { formatPrice } from '@/lib/price';

// 본인 매물 목록에 보여줄 필드.
// ✎ 2026-08-13 사용자 지적 #8("내차팔기 목록이 너무 데모 같다") — mileage·fuel·region을 추가했다.
//   예전엔 "[현대] 팰리세이드 · 2023년 · 4,112만원" 한 줄이 전부라, 판매자가 자기 매물을 구분할
//   단서가 이름과 값밖에 없었다. 사진 썸네일(attachCoverImages)과 함께 목록 카드 언어에 맞춘다.
type OwnListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  mileage: number;
  fuel: string;
  region: string;
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
    .select('id, manufacturer, model, year, price, mileage, fuel, region, status, created_at')
    .eq('seller_id', user?.id ?? '')
    .order('created_at', { ascending: false })
    .returns<OwnListing[]>();

  if (listingsError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분.
    console.error('[sell] 본인 매물 조회 실패:', listingsError);
  }

  // 대표 사진 — /search·랜딩 카드와 **같은 함수**를 쓴다(사진 조회 규칙을 두 벌로 만들지 않는다).
  // 조회가 실패해도 image_url:null로 떨어져 플레이스홀더가 될 뿐, 목록 자체는 그대로 나온다.
  const listingsWithCover = listings ? await attachCoverImages(supabase, listings) : [];

  return (
    // ✎ 2026-08-13 2차 지적 #4 — 본문 폭을 `max-w-2xl`(672px) → `max-w-6xl`로 열어 `/search`와
    //   맞춘다. 이 화면만 폭이 좁아 "모바일 너비에 맞춰 놓은 것 같다"는 지적을 받았다. 폭만 넓히면
    //   입력칸이 늘어나 더 이상해지므로, 폼은 SearchFilters와 같은 카드 표면 안에 넣고(SellForm)
    //   그 안에서 2열 그리드를 유지한다 — 두 화면이 "카드 안 폼 + 아래 결과 목록"으로 같아진다.
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <section className="flex flex-col gap-1">
        <h1 className="text-section font-bold text-ink-primary">매물 등록</h1>
        <p className="text-sm text-ink-muted">
          차량 정보를 입력해 매물을 등록하면 구매자에게 바로 노출됩니다(관리자 승인 없음).
        </p>
      </section>

      <SellForm />

      {/* ✎ 2026-08-13 사용자 지적 #8 — 이 목록이 "너무 데모 같다"는 지적의 실체는 **행이 글자
          한 줄뿐**이었다는 것이다: 사진도 없고, 연식·값 외에 자기 매물을 구분할 단서도 없고,
          제목을 눌러도 아무 데도 안 갔다. 목록 카드(/search)와 같은 언어로 맞춘다 —
          썸네일 + 제목 + 주행·연료·지역 + 가격 강조 + 상태 배지 + 액션. */}
      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2">
          <h2 className="text-lg font-semibold">내가 등록한 매물</h2>
          {!listingsError && listingsWithCover.length > 0 && (
            <span className="text-meta font-medium text-ink-muted">
              {listingsWithCover.length.toLocaleString('ko-KR')}건
            </span>
          )}
        </div>
        {listingsError ? (
          <p role="alert" className="text-sm text-danger">
            매물 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : listingsWithCover.length === 0 ? (
          // 빈 상태 문구는 UX 확정본(EXPERIENCE.md "내 매물 관리 빈 상태")을 그대로 쓴다 —
          // 이 자리가 바로 그 서피스인데 예전엔 "아직 등록한 매물이 없습니다."라는 다른 문장이었다.
          <p className="text-sm text-ink-muted">
            아직 등록한 매물이 없어요. 위 폼으로 첫 매물을 올려보세요.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {listingsWithCover.map((l) => {
              const onSale = l.status === LISTING_STATUS.ON_SALE;
              const title = `[${l.manufacturer}] ${l.model} · ${l.year}년`;
              const summary = (
                <>
                  {/* 썸네일 — 카드와 같은 실패 처리(ListingCardImage)를 쓰되 작은 자리용 variant. */}
                  <div className="w-[88px] shrink-0">
                    <ListingCardImage url={l.image_url} alt={title} variant="thumb" />
                  </div>
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-body font-semibold text-ink-primary">{title}</span>
                    {/* 한 줄 유지, 좁으면 …로 자른다(D5 — 세로로 접지 않는다). */}
                    <span className="truncate whitespace-nowrap text-meta text-ink-muted">
                      {l.mileage.toLocaleString('ko-KR')}
                      {UNITS.mileage} · {l.fuel} · {l.region}
                    </span>
                    <span className="whitespace-nowrap text-body font-extrabold text-price-emphasis">
                      {formatPrice(l.price)}
                    </span>
                  </div>
                </>
              );

              return (
                <li
                  key={l.id}
                  className="flex items-center justify-between gap-3 rounded-card border border-border-hairline bg-surface-raised p-3 shadow-card dark:shadow-none"
                >
                  {/* 판매중일 때만 상세로 링크한다 — 판매완료 매물의 상세는 구매자에게 비노출이라
                      (FR11) 눌러도 "찾을 수 없어요"가 뜬다. 갈 수 없는 곳으로 보내지 않는다. */}
                  {onSale ? (
                    <Link
                      href={`/listings/${l.id}`}
                      className="flex min-w-0 flex-1 items-center gap-3 rounded-chip hover:opacity-90"
                    >
                      {summary}
                    </Link>
                  ) : (
                    <div className="flex min-w-0 flex-1 items-center gap-3">{summary}</div>
                  )}
                  <div className="flex shrink-0 items-center gap-3">
                    <Badge tone={onSale ? 'active' : 'neutral'}>{onSale ? '판매중' : '판매완료'}</Badge>
                    {/* 본인 매물 관리 진입점 — 구매완료(2-4, FR8)·수정·삭제(2-3, FR6).
                        판매중(on_sale)일 때만 "구매 완료"·"수정" 노출(거래 끝난 매물 변경 방지).
                        삭제는 정리 목적이라 status 무관 허용. */}
                    <ListingActions
                      listingId={l.id}
                      label={`[${l.manufacturer}] ${l.model}`}
                      canEdit={onSale}
                      canComplete={onSale}
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
