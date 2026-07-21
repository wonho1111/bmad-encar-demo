// 매물 카드 — 구매자 목록(FR9)·향후 AI 검색 결과(Epic 4)가 공유하는 표시용 컴포넌트.
// 현재 사진 렌더 없음(image_url 계약 자리는 예약, 값 채움·표시는 Epic 9). ListingCard 필드 계약(conventions §4)만 보여준다:
//   id, manufacturer, model, year, price, mileage, region
// 단위 표시는 conventions §3 규칙대로 — price=원, mileage=km, 천단위 콤마(toLocaleString('ko-KR')).
// 카드 클릭 시 상세(/listings/[id])로 가는 링크를 둔다(상세 페이지 자체 구현은 Story 3-2).
//
// 상태 없는 표현용 컴포넌트(서버/클라이언트 어디서든 렌더 가능). 스타일은 sell 목록 li와 일관.
import Link from 'next/link';
import { UNITS } from '@/lib/constants';
import ListingCardImage from './ListingCardImage';

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
};

export default function ListingCard({ listing }: { listing: ListingCardData }) {
  const title = `[${listing.manufacturer}] ${listing.model} · ${listing.year}년`;

  return (
    // 루트가 <article>인 이유(AC4): 찜 버튼이 카드 안에 있어야 하는데 `<a>` 안의 `<button>`은
    // 유효하지 않은 HTML이다. 그래서 링크는 **내용만** 덮고, 버튼은 링크 밖에 절대배치한다.
    <article className="relative overflow-hidden rounded-card border border-border-hairline bg-surface-raised shadow-card transition-shadow hover:shadow-card-hover dark:shadow-none">
      <Link href={`/listings/${listing.id}`} className="flex flex-col">
        {/* ① 사진 (5:3) — 없거나 로드 실패면 "사진 준비중" 플레이스홀더 */}
        <ListingCardImage url={listing.image_url} count={listing.image_count} alt={title} />

        <div className="flex flex-col gap-1 p-[18px]">
          {/* ② 신뢰속성 행 슬롯 — 값(accident_status·is_single_owner·is_non_smoker)은 Epic 10이 채운다.
              지금은 항상 비어 있으므로 **아무것도 렌더하지 않는다**(빈 높이·빈 테두리 금지, AC1). */}

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

          {/* ⑥ 옵션 칩 슬롯 — 칩 내용은 Epic 10. 값이 없으므로 렌더하지 않는다(AC1). */}
        </div>
      </Link>

      {/*
        찜(♡) — **위치·시각만.** 동작·토글·상태는 Epic 10.5의 몫이라 여기서 만들지 않는다.
        동작이 없는 컨트롤이므로 스크린리더·키보드가 잡지 않게 disabled + aria-hidden + tabIndex=-1.
        자리: 사진 밖, **정보 영역 우상단**. 아래 감싸개는 사진과 같은 5:3 비율로 사진 박스 높이를
        그대로 재현하고, `top-full`로 그 바로 아래(=정보 영역 시작점)에 버튼을 놓는다.
        터치 타깃 44×44(h-11 w-11) — review-accessibility.md [high].
      */}
      <div className="pointer-events-none absolute inset-x-0 top-0 aspect-[5/3]">
        <button
          type="button"
          disabled
          aria-hidden="true"
          tabIndex={-1}
          className="absolute right-2 top-full mt-1 flex h-11 w-11 items-center justify-center rounded-full bg-surface-raised text-lg text-ink-muted shadow-card"
        >
          ♡
        </button>
      </div>
    </article>
  );
}
