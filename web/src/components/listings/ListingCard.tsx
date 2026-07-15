// 매물 카드 — 구매자 목록(FR9)·향후 AI 검색 결과(Epic 4)가 공유하는 표시용 컴포넌트.
// 현재 사진 렌더 없음(image_url 계약 자리는 예약, 값 채움·표시는 Epic 9). ListingCard 필드 계약(conventions §4)만 보여준다:
//   id, manufacturer, model, year, price, mileage, region
// 단위 표시는 conventions §3 규칙대로 — price=원, mileage=km, 천단위 콤마(toLocaleString('ko-KR')).
// 카드 클릭 시 상세(/listings/[id])로 가는 링크를 둔다(상세 페이지 자체 구현은 Story 3-2).
//
// 상태 없는 표현용 컴포넌트(서버/클라이언트 어디서든 렌더 가능). 스타일은 sell 목록 li와 일관.
import Link from 'next/link';
import { UNITS } from '@/lib/constants';

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
  // 증분 신규 — 전부 optional·nullable(DB 컬럼 아직 없음, 값 채움은 후속 에픽)
  image_url?: string | null; // 대표 서명 URL. null이면 "사진 준비중" 플레이스홀더 — Epic 9
  view_count?: number | null; // Epic 11
  image_count?: number | null; // Epic 9
  accident_status?: '무사고' | '단순교환' | '사고' | null; // Epic 10
  is_single_owner?: boolean | null; // Epic 10
  is_non_smoker?: boolean | null; // Epic 10
};

export default function ListingCard({ listing }: { listing: ListingCardData }) {
  return (
    <Link
      href={`/listings/${listing.id}`}
      className="flex flex-col gap-1 rounded border border-zinc-200 px-4 py-3 text-sm transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
    >
      {/* 제조사·모델·연식 — 한 줄 요약 */}
      <span className="font-medium">
        [{listing.manufacturer}] {listing.model} · {listing.year}년
      </span>
      {/* 가격·주행거리·지역 — 단위 규칙(원·km, 천단위 콤마) */}
      <span className="text-zinc-500">
        {listing.price.toLocaleString('ko-KR')}
        {UNITS.price} · {listing.mileage.toLocaleString('ko-KR')}
        {UNITS.mileage} · {listing.region}
      </span>
      {/* 판매자 표시 이름(있을 때만) — 본인 매물 인지 등 식별 편의(0007). AI결과처럼 값이 없으면 줄 자체를 숨긴다. */}
      {listing.seller_name && (
        <span className="text-xs text-zinc-400">판매자 {listing.seller_name}</span>
      )}
    </Link>
  );
}
