'use client';

// 상세 요약 카드의 "AI 시세 진단" 버튼 (5단계) — 목업 detail-1.html 정답지 STEP1의
// `.btn-highlight-ring`(문의하기 버튼 위 한 줄, 레이아웃 변형 없음).
//
// 클릭하면(로그인 상태):
//   1) "이 매물 시세 알려줘 — {제조사} {모델} {연식} · {주행km} · {가격만원}" 프리필 질의를 만든다.
//   2) heroSearchHandoff(기존 히어로 검색 핸드오프 단일 출처)에 그 질의 + listingId를 실어 저장한다.
//   3) /ai로 이동 — ChatAssistant가 마운트 시 이 핸드오프를 소비해 1회 자동으로 검색을 실행한다
//      (히어로 검색과 완전히 같은 메커니즘, listingId만 추가로 실어 보낸다).
//
// 비로그인이면 기존 InquiryCta의 anon 분기와 동일하게 로그인 게이트로 보낸다(별도 안내문
// "로그인하고 시세 진단" — "로그인하고 문의하기"와 같은 패턴 재사용).
//
// mode는 InquiryCta와 동일하게 page.tsx(서버)가 계산해 내려준다(AC7과 같은 3분기 재사용) —
// owner(본인 매물)도 자기 매물 시세는 볼 수 있어야 하므로 anon만 별도 취급한다.
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { buttonClasses } from '@/components/ui/Button';
import { setHeroSearchHandoff } from '@/lib/heroSearchHandoff';
import { formatPrice } from '@/lib/price';
import { formatManKm } from '@/components/ai/MarketDiagnosis';
import type { InquiryCtaMode } from './InquiryCta';

export type MarketDiagnosisButtonListing = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  mileage: number;
  price: number;
};

function buildPrefillQuery(listing: MarketDiagnosisButtonListing): string {
  return `이 매물 시세 알려줘 — ${listing.manufacturer} ${listing.model} ${listing.year} · ${formatManKm(listing.mileage)} · ${formatPrice(listing.price)}`;
}

export default function MarketDiagnosisButton({
  mode,
  listing,
  loginHref,
}: {
  mode: InquiryCtaMode;
  listing: MarketDiagnosisButtonListing;
  loginHref: string;
}) {
  const router = useRouter();

  if (mode === 'anon') {
    // 비로그인 — 기존 "로그인하고 문의하기"와 동일한 처리(어포던스는 보이고 게이트는 클릭에만).
    return (
      <Link href={loginHref} className={buttonClasses({ variant: 'secondary', className: 'w-full' })}>
        로그인하고 시세 진단
      </Link>
    );
  }

  async function handleClick() {
    // useInquiryAction.start()·HeroSearch.submit()과 동일한 방어: mode는 서버 렌더 시점 값이라
    // 그 사이 세션이 만료됐을 수 있다. 클릭 시점에 다시 확인해, 만료됐으면 로그인 게이트로 보낸다.
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      router.push(loginHref);
      return;
    }
    setHeroSearchHandoff({ query: buildPrefillQuery(listing), autoRun: true, listingId: listing.id });
    router.push('/ai');
  }

  return (
    <button
      type="button"
      onClick={() => void handleClick()}
      className={buttonClasses({ variant: 'secondary', className: 'w-full' })}
    >
      AI 시세 진단
    </button>
  );
}
