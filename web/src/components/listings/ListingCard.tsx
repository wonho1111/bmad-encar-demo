// 매물 카드 — 구매자 목록(FR9)·향후 AI 검색 결과(Epic 4)가 공유하는 표시용 컴포넌트.
// 현재 사진 렌더 없음(image_url 계약 자리는 예약, 값 채움·표시는 Epic 9). ListingCard 필드 계약(conventions §4)만 보여준다:
//   id, manufacturer, model, year, price, mileage, region
// 단위 표시는 conventions §3 규칙대로 — price=원, mileage=km, 천단위 콤마(toLocaleString('ko-KR')).
// 카드 클릭 시 상세(/listings/[id])로 가는 링크를 둔다(상세 페이지 자체 구현은 Story 3-2).
//
// 상태 없는 표현용 컴포넌트(서버/클라이언트 어디서든 렌더 가능). 스타일은 sell 목록 li와 일관.
import Link from 'next/link';
import { UNITS } from '@/lib/constants';
import { topOptions } from '@/lib/options';
import ListingCardImage from './ListingCardImage';
import TrustAttributes from './TrustAttributes';
import WishButton from './WishButton';

// 카드에 노출할 옵션 칩 최대 개수(conventions §11.2 "카드=상위 3~4").
const CARD_OPTION_COUNT = 4;

// ListingCard 필드 계약(conventions §4) — 목록·AI결과 카드가 공유하는 최소 요약 필드.
export type ListingCardData = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number; // 원(KRW) 정수
  mileage: number; // km 정수
  region: string;
  seller_name?: string | null; // 판매자 표시 이름(이메일 @앞부분, 0007 비정규화). 없으면(AI결과 등) 미표시.
  // 증분 신규 — 전부 optional·nullable(값 채움은 후속 에픽)
  image_url?: string | null; // 대표 사진의 공개 URL. null이면 "사진 준비중" 플레이스홀더 — Epic 9
  view_count?: number | null; // Epic 11
  image_count?: number | null; // Epic 9
  fuel?: string | null; // 연료(가솔린/디젤/하이브리드/전기/LPG) — Epic 10(10.1), 대장 #67
  accident_status?: '무사고' | '단순교환' | '사고' | null; // Epic 10(10.1 컬럼 생성)
  is_single_owner?: boolean | null; // Epic 10(10.1 컬럼 생성)
  is_non_smoker?: boolean | null; // Epic 10(10.1 컬럼 생성)
  options?: string[] | null; // 장비 통제어휘 배열(text[]) — Epic 10(10.3), docs/conventions.md §11
};

export default function ListingCard({
  listing,
  wished = false,
  authed = false,
}: {
  listing: ListingCardData;
  // 찜 여부·로그인 여부 — ListingCardData(wire 계약)에 넣지 않는 sibling prop이다(찜은 wire
  // 필드가 아니다, docs/conventions.md §4·65). 호출부(page.tsx·search/page.tsx·wishlist/page.tsx)가
  // 사용자별 오버레이 조회 결과를 여기로 주입한다.
  wished?: boolean;
  authed?: boolean;
}) {
  const title = `[${listing.manufacturer}] ${listing.model} · ${listing.year}년`;
  // 희소 옵션 우선(topOptions), 상위 CARD_OPTION_COUNT개만 카드에 노출(conventions §11.2).
  const cardOptions = topOptions(listing.options, CARD_OPTION_COUNT);

  return (
    // 루트가 <article>인 이유(AC4): 찜 버튼이 카드 안에 있어야 하는데 `<a>` 안의 `<button>`은
    // 유효하지 않은 HTML이다. 그래서 링크는 **내용만** 덮고, 버튼은 링크 밖에 절대배치한다.
    <article className="relative overflow-hidden rounded-card border border-border-hairline bg-surface-raised shadow-card transition-shadow hover:shadow-card-hover dark:shadow-none">
      <Link href={`/listings/${listing.id}`} className="flex flex-col">
        {/* ① 사진 (5:3) — 없거나 로드 실패면 "사진 준비중" 플레이스홀더 */}
        <ListingCardImage url={listing.image_url} count={listing.image_count} alt={title} />

        <div className="flex flex-col gap-1 p-[18px]">
          {/* ② 신뢰속성 행 — TrustAttributes가 뱃지·면책을 한 몸으로 emit한다(B9, Story 10.2).
              값이 전부 없으면 컴포넌트가 null을 반환해 슬롯이 비고, 빈 높이·빈 테두리는 남지 않는다(AC1). */}
          <TrustAttributes variant="card" listing={listing} />

          {/* ③ 차량명 — 폭이 좁아도 줄바꿈으로 접지 않고 …으로 자른다(D5).
              pr-14(56px)는 우상단 찜 버튼(44px+오프셋 8px)과 겹치지 않게 이 줄에만 둔 여백이다. */}
          <h3 className="truncate pr-14 text-card-title font-semibold text-ink-primary">{title}</h3>

          {/* ④ meta — **한 줄 가로 유지**. 공간이 부족하면 truncate만(D5, 세로로 접지 않는다).
              AC 문구대로 `주행 · 연료 · 지역`(+ 있으면 판매자)를 표시한다(대장 #67 해소, Story 10.1).
              fuel이 없으면(계약-외 값 정규화) 그 마디를 통째로 생략 — 빈 자리("· ·")를 남기지 않는다.
              ⚠️ fuel은 `isValidListing`(aiSearch.ts)의 필수 7필드 검사 대상이 아니라서 /ai/search가
              비-string을 보내도 그대로 통과한다 — `typeof` 가드 없이 배열에 넣으면 `[object Object]`가
              렌더될 수 있다(app `listing.dart`는 fromMap에서 이미 이렇게 방어한다). string일 때만 표시.
              pr-14: 찜 버튼이 이 줄까지 내려오므로 차량명과 같은 여백을 둔다. */}
          <p className="truncate whitespace-nowrap pr-14 text-meta font-medium text-ink-muted">
            {[
              `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}`,
              typeof listing.fuel === 'string' ? listing.fuel : null,
              listing.region,
              listing.seller_name,
            ]
              .filter(Boolean)
              .join(' · ')}
          </p>

          {/* ⑤ 가격 — 카드에서 **시각적으로 가장 큰 요소**(26px/800 vs 차량명 16px/600). */}
          <p className="text-price font-extrabold text-price-emphasis">
            {listing.price.toLocaleString('ko-KR')}
            {UNITS.price}
          </p>

          {/* ⑥ 옵션 칩 — 우선순위 상위 3~4개(희소 우선, 보편은 topOptions의 자연 fallback로
              채워짐, conventions §11.2). 값이 없으면 슬롯 자체를 렌더하지 않는다(AC1, 빈 잉크
              없음). 폭이 좁아지면 각 칩이 `shrink`+`truncate`로 줄어들 뿐 세로로 접히거나
              2줄로 밀리지 않는다(D5) — `flex-nowrap`이라 줄바꿈 자체가 없다. */}
          {cardOptions.length > 0 && (
            <div className="flex flex-nowrap items-center gap-1.5 overflow-hidden">
              {cardOptions.map((opt) => (
                <span
                  key={opt}
                  className="min-w-0 shrink truncate whitespace-nowrap rounded-chip border border-border-hairline px-2 py-0.5 text-caption font-medium text-ink-secondary"
                >
                  {opt}
                </span>
              ))}
            </div>
          )}
        </div>
      </Link>

      {/* 찜(♡) — 낙관적 토글·로그인 게이트·복귀 자동반영은 WishButton이 전담(Story 10.5).
          자리: 사진 밖, 정보 영역 우상단(WishButton 내부가 같은 5:3 감싸개 + top-full로 재현). */}
      <WishButton listingId={listing.id} initialWished={wished} authed={authed} />
    </article>
  );
}
