// AI 채팅 "사용자 턴" 미니 매물 카드 (개선 1, 2026-09-01) — 상세 페이지 [AI 시세 진단] 버튼이
// 만든 프리필 질의("이 매물 시세 알려줘 — …")는 지금까지 텍스트뿐이라 어떤 매물인지 말풍선만
// 봐서는 알 수 없었다. 그 사용자 턴 위에 썸네일+핵심 제원을 곁들인 작은 카드를 붙인다.
//
// 왜 기존 ListingCard를 재사용하지 않나: 그건 목록/카드 그리드용으로 클릭 시 상세 이동 링크·찜
// 버튼·옵션 칩·신뢰뱃지까지 갖춘 무거운 컴포넌트라 채팅 버블 폭(오른쪽 정렬, 대화 칼럼 안)에
// 맞지 않고 여기선 그런 부가 동작이 전혀 필요 없다 — 전용 컴팩트 컴포넌트로 새로 둔다(A2).
//
// 썸네일은 평범한 <img>를 쓴다(next/image 아님) — ListingGallery와 같은 판단: 이 카드는 대화당
// 한 번만 그려지고 이미 최적화된 저장본 URL을 그대로 쓰므로 next/image의 최적화 파이프라인이
// 필요 없다(ListingCardImage처럼 그리드에 여러 장이 동시에 뜨는 경우와 다르다).
import { formatPrice } from '@/lib/price';
import { formatManKm } from './MarketDiagnosis';

export type ListingMiniCardData = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  mileage: number;
  price: number;
  imageUrl?: string | null;
};

export default function ListingMiniCard({ listing }: { listing: ListingMiniCardData }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border-hairline bg-surface-raised px-2.5 py-2">
      {listing.imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- 대화당 1회, 이미 최적화된 저장본(ListingGallery와 동일 판단).
        <img
          src={listing.imageUrl}
          alt=""
          className="h-11 w-11 shrink-0 rounded object-cover"
        />
      ) : (
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded bg-placeholder-bg text-caption text-ink-muted">
          사진없음
        </div>
      )}
      <div className="flex flex-col text-right">
        <p className="text-sm font-semibold text-ink-primary">
          {listing.manufacturer} {listing.model} · {listing.year}
        </p>
        <p className="text-caption text-ink-muted">
          {formatManKm(listing.mileage)} · {formatPrice(listing.price)}
        </p>
      </div>
    </div>
  );
}
