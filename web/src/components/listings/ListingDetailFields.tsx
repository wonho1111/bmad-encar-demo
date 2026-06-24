// 매물 상세의 "내용 표시부" 공유 컴포넌트 — 데이터를 받아 화면만 그리는 프레젠테이션 컴포넌트.
//
// 왜 분리했나(단일 출처):
//   구매자 상세((user)/listings/[id])와 관리자 상세((admin)/admin/listings/[id])가
//   똑같이 "15필드 + 옵션 + 설명"을 보여준다. 이 마크업을 양쪽에 복붙하면 한쪽만 고쳐져 어긋나기(drift) 쉽다.
//   그래서 표시 마크업만 이 한 곳에 모으고, 두 페이지는 이 컴포넌트를 함께 쓴다.
//
// 무엇을 안 넣었나(의도):
//   · 데이터 조회·상태 필터(구매자=on_sale만 / 관리자=전체)는 각 페이지의 책임 — 여기선 안 한다.
//   · 제목·상태 배지·"문의하기"·삭제·뒤로가기 등 맥락이 다른 요소도 각 페이지가 따로 그린다.
//   · 여기는 "공통 본문(기본 정보·옵션·설명)"만 담당한다.
import { UNITS } from '@/lib/constants';

// 표시에 필요한 매물 필드(FR5 15필드 중 본문에 쓰는 값). seller_id·status 등 페이지별 로직용 필드는 제외.
export type ListingDetailFieldsData = {
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

export default function ListingDetailFields({
  listing,
}: {
  listing: ListingDetailFieldsData;
}) {
  // 단위·표시 규칙(conventions §3): 천단위 콤마 + 단위.
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;
  const mileageText = `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}`;
  const displacementText = `${listing.displacement.toLocaleString('ko-KR')}${UNITS.displacement}`;
  const options = listing.options ?? [];

  return (
    <>
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
    </>
  );
}
