// 구매자 상세의 **정보 섹션**(차량정보 · 옵션) — 이 라우트 전용 표시부 (Story 9.5 AC1·AC5).
//
// ⚠️ **왜 `components/listings/ListingDetailFields.tsx`를 고치지 않고 새로 만들었나 (AC10).**
//   저 컴포넌트는 **관리자 매물 상세와 공유**한다(`(admin)/admin/listings/[id]/page.tsx`).
//   구매자 상세만 섹션 순서를 바꾸고 디자인 토큰을 입히는데 공유 컴포넌트를 제자리에서 뒤집으면,
//   이 스토리 범위 밖인 **관리자 화면이 함께 바뀐다**(관리자 리스킨은 Epic 15의 몫이다).
//   그래서 구매자 전용 레이아웃을 이 라우트 폴더에 두고, 공유 컴포넌트는 관리자가 계속 쓰게 둔다.
//   두 화면이 잠시 다른 마크업을 갖는 것은 **의도된 상태**이며, Epic 15가 관리자를 같은 토큰으로
//   올릴 때 합류 여부를 판단한다.
//
// 상태 없는 서버 컴포넌트다(표시만 한다). 값 채우기·조회는 page.tsx의 책임.
import { UNITS } from '@/lib/constants';

// FR5 15필드 중 **본문에 쓰는 값**(seller_id·status 등 페이지 로직용 필드는 제외).
// 15필드 내역 = 이 표 13행 + 옵션 + 설명. seller_name은 FR5 15필드 **밖**이다
// (0007이 넣은 비정규화 표시값 — 값이 없으면 행 자체를 숨긴다).
export type ListingDetailSectionsData = {
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
  seller_name?: string | null;
  options: string[] | null; // text[]; 빈 배열·null 가능
  description: string | null; // nullable
};

/** 섹션 껍데기 — 4개 섹션이 같은 카드 표면·제목 위계를 갖게 한 자리에 모은다. */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-card border border-border-hairline bg-surface-raised p-5 shadow-card dark:shadow-none">
      <h2 className="text-section font-bold text-ink-primary">{title}</h2>
      {children}
    </section>
  );
}

// 라벨-값 한 줄. **가로 배치를 유지한다** — 폭이 좁아도 세로로 접지 않고, 값이 길면 …로 자른다(D5).
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border-hairline py-2 last:border-0">
      <span className="shrink-0 whitespace-nowrap text-meta font-medium text-ink-muted">{label}</span>
      <span className="truncate text-body font-medium text-ink-primary">{value}</span>
    </div>
  );
}

/** ② 차량정보 — FR5 표 13행(+판매자 표시명) + 설명. 필드를 새로 만들지도, 빼지도 않는다(AC5). */
export function VehicleInfoSection({ listing }: { listing: ListingDetailSectionsData }) {
  // 단위·표시 규칙(conventions §3): 천단위 콤마 + 단위.
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;
  const mileageText = `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}`;
  const displacementText = `${listing.displacement.toLocaleString('ko-KR')}${UNITS.displacement}`;

  return (
    <Section title="차량정보">
      <div className="flex flex-col">
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
        {/* 판매자 표시 이름(있을 때만) — 등록 시 트리거가 자동 기록한 값(이메일 @앞부분). */}
        {listing.seller_name && <Field label="판매자" value={listing.seller_name} />}
      </div>

      {/* 설명 = 15필드의 하나. 표 행이 아니라 자유 텍스트라 표 아래에 둔다(AC5). */}
      <div className="flex flex-col gap-1 border-t border-border-hairline pt-3">
        <h3 className="text-meta font-medium text-ink-muted">설명</h3>
        {listing.description && listing.description.trim() !== '' ? (
          <p className="whitespace-pre-wrap text-body text-ink-secondary">{listing.description}</p>
        ) : (
          <p className="text-body text-ink-muted">등록된 설명이 없습니다.</p>
        )}
      </div>
    </Section>
  );
}

/**
 * ③ 옵션 — 지금 있는 칩 목록을 옮기기만 한다.
 * **카테고리 분류·희소옵션 강조는 Epic 10.3/10.4의 몫이며 여기서 만들지 않는다.**
 */
export function OptionsSection({ listing }: { listing: ListingDetailSectionsData }) {
  const options = listing.options ?? [];

  return (
    <Section title="옵션">
      {options.length === 0 ? (
        <p className="text-body text-ink-muted">등록된 옵션이 없습니다.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {options.map((opt, i) => (
            <li
              key={`${opt}-${i}`}
              className="whitespace-nowrap rounded-chip border border-border-hairline px-2.5 py-1 text-caption font-medium text-ink-secondary"
            >
              {opt}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
