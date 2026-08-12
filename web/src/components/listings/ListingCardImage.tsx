'use client';

// 매물 카드의 사진 영역 (Story 9.4 AC2·3·5).
//
// **왜 이 조각만 클라이언트 컴포넌트인가:** 로드 실패를 잡으려면 `onError`가 필요하고, `onError`는
// 브라우저에서만 일어난다. 카드 전체를 클라이언트로 만들면 목록 100건이 전부 하이드레이션되므로,
// 상태가 필요한 사진 영역만 떼어 낸다(나머지 카드는 서버에서 그대로 렌더된다).
//
// **`onError`가 9.0 이후 더 중요해졌다:** 서명 URL 시절엔 발급 실패가 `null`로 와서 자동으로
// 플레이스홀더가 됐다. 지금 쓰는 `getPublicUrl`은 **파일이 없어도 문자열을 돌려준다**(존재를
// 확인하지 않는다). 그래서 깨진 이미지 아이콘을 막는 장치는 이제 `onError` 하나뿐이다.
import { useState } from 'react';
import Image from 'next/image';

export default function ListingCardImage({
  url,
  count,
  alt,
  variant = 'card',
}: {
  url?: string | null;
  count?: number | null;
  alt: string;
  // 'thumb' — /sell "내가 등록한 매물" 행의 작은 썸네일(2026-08-13 #8). 카드와 **같은 실패 처리**를
  // 쓰되(그게 이 컴포넌트가 존재하는 이유다) 작은 자리에 안 맞는 두 가지만 끈다:
  //   ① "N장" 배지 — 88px 폭에서는 사진을 거의 덮는다.
  //   ② 위쪽만 둥근 모서리 — 썸네일은 카드 상단이 아니라 독립 상자라 네 모서리를 다 둥글린다.
  // 플레이스홀더 문구도 작은 자리에선 아이콘만 남긴다(글자가 안 들어간다).
  variant?: 'card' | 'thumb';
}) {
  const [failed, setFailed] = useState(false);

  // ⚠️ `onError`만으로는 부족하다 — 실브라우저 실측(2026-07-19 코드리뷰)에서 확인했다.
  // 서버가 그린 <img>는 HTML이 도착하는 즉시 로드를 시작하는데, **하이드레이션이 끝나기 전에**
  // 에러가 나면 React가 그 이벤트를 재생하지 않아 onError가 영영 발화하지 않는다. 그러면 AC3이
  // 금지한 "깨진 이미지"가 그대로 남는다. 그리고 파일 없음(404)은 정확히 그렇게 빨리 실패한다 —
  // 즉 가장 흔한 실패가 유일한 방어를 그냥 지나쳤다.
  // 재현: 이미지 호스트를 블랙홀로 보내고 /search 렌더 → 플레이스홀더 대신 alt 텍스트+깨진 아이콘.
  // 그래서 ref 콜백으로 **이미 끝난 로드의 결과를 직접 본다**: complete인데 naturalWidth가 0이면
  // 그 이미지는 실패한 것이다(이벤트를 놓쳤어도 이 상태는 남는다).
  const detectAlreadyFailed = (img: HTMLImageElement | null) => {
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  };
  // url이 바뀌면(목록 재필터링 등으로 컴포넌트 인스턴스가 재사용될 때) failed를 리셋한다.
  // useEffect 대신 "렌더 중 상태 조정" 패턴(React 19 권장) — 커밋 전에 바로잡아 추가 페인트가 없다.
  const [prevUrl, setPrevUrl] = useState(url);
  if (url !== prevUrl) {
    setPrevUrl(url);
    setFailed(false);
  }

  // 계약-외 값 방어(conventions.md §4): 빈 문자열도 "사진 없음"으로 본다 — `!url`이 이미 ''를 거른다.
  const showPhoto = Boolean(url) && !failed;
  // 음수 count는 0으로 깎는다(§4). 배지는 1장 이상일 때만 뜬다.
  const photoCount = Math.max(0, count ?? 0);

  return (
    <div
      className={`relative aspect-[5/3] w-full overflow-hidden bg-placeholder-bg ${
        variant === 'thumb' ? 'rounded-chip' : 'rounded-t-card'
      }`}
    >
      {showPhoto ? (
        /*
          next/image를 쓴다 (2026-07-29 전환, 대장 DW-541). **여기 적혀 있던 "평범한 <img>를 쓰는
          이유" 3가지 중 2가지가 실측으로 거짓임이 밝혀져 결정을 뒤집었다** — 근거가 무너진 결정을
          주석만 남긴 채 유지하면 다음 사람이 그 주석을 믿는다:
            ✗ "저장본이 이미 작다" — 90장 전수 실측(2026-07-21) 최소 50KB·중앙값 197KB·평균 229KB·
              최대 615KB. 게다가 2026-07-29 측정: 저장본이 **1600×1067px인데 카드 표시 폭은 364px**
              (픽셀 수로 약 20배). "작다"의 근거가 없다.
            ✗ "공개 URL이 고정이라 브라우저·CDN 캐시가 그대로 먹는다" — 먹지 않았다. Storage 오브젝트
              181개 중 **180개가 `cache-control: no-cache`**(응답 실측 `cf-cache-status: MISS`)라
              방문할 때마다 전부 다시 받고 있었다.
            ○ "remotePatterns 설정이 선행" — 이건 사실이었고, 이번에 next.config.ts에 추가했다
              (호스트는 NEXT_PUBLIC_SUPABASE_URL에서 끌어온다 — 로컬/운영 호스트가 다르므로).
          next/image가 표시 크기에 맞춰 줄여 주고 최적화 결과를 오래 캐시하므로 두 축이 함께 풀린다.
          원본(Storage)은 건드리지 않는다 — 캐시 헤더를 원본에서 고치려면 180장 재업로드가 필요한데,
          그건 운영 데이터 조작이라 별건이다(측정 근거는 next.config.ts 주석 참조).

          fill + sizes: 감싸개가 aspect-[5/3]로 자리를 잡고 있으므로 폭·높이를 숫자로 줄 수 없다.
          sizes는 D5 그리드 실제 폭을 그대로 적는다 — ≥1100px 4열(본문 max-w-6xl 기준 약 264px) ·
          640~1099px 2열(약 47vw) · <640px 1열(100vw). 이 값이 틀리면 브라우저가 필요보다 큰 변환본을
          고르므로, 그리드 규칙(ResponsiveGrid)이 바뀌면 여기도 같이 봐야 한다.
          크롭은 저장본을 다시 만들지 않고 렌더 크롭으로만 한다(object-cover 중앙, I14).
          aspect-[5/3]가 자리를 미리 잡아 지연 로드에도 레이아웃이 밀리지 않는다(NFR7).
        */
        <Image
          ref={detectAlreadyFailed}
          src={url as string}
          alt={alt}
          fill
          sizes={variant === 'thumb' ? '96px' : '(min-width: 1100px) 264px, (min-width: 640px) 47vw, 100vw'}
          loading="lazy"
          onError={() => setFailed(true)}
          // data-testid: E2E(web/e2e/image-fallback.spec.ts)가 스타일 클래스(object-cover)가 아니라
          // 이 안정적인 훅으로 매물 사진 <img>를 찾는다 — 클래스가 리팩터돼도 검사가 조용히
          // 0건 매칭(거짓 통과)하지 않게 하기 위함(코드리뷰 patch). next/image도 최종적으로 <img>를
          // 그리고 모르는 prop을 그대로 내려보내므로 이 훅은 그대로 유효하다.
          data-testid="listing-photo"
          className="object-cover"
        />
      ) : (
        /*
          "사진 준비중" 플레이스홀더 — 빈 영역·깨진 이미지 아이콘 대신 **의도적으로 보이게** 한다(UX-DR7).
          트리거 3가지를 모두 여기로 모은다: url이 null · 빈 문자열('') · onError(로드 실패).
          문구 색 대비 실측(2026-07-19): ink-muted #676D69 on placeholder-bg #F1EFE9 = **4.60:1**,
          다크 #A6A196 on #2A2924 = **5.66:1** — 양쪽 다 AA 통과라 토큰을 올리지 않았다.
          (스토리의 "약 4.4:1로 미달 가능성" 개략 계산은 실제 값과 달랐다.)
        */
        <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-ink-muted">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className={variant === 'thumb' ? 'h-5 w-5' : 'h-7 w-7'}
          >
            <path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2.2l1.2-2h8.2l1.2 2h2.2A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5v-9Z" />
            <circle cx="12" cy="13" r="3.2" />
          </svg>
          {variant === 'card' && <span className="text-meta font-medium">사진 준비중</span>}
        </div>
      )}
      {variant === 'card' && photoCount >= 1 && (
        /*
          "N장" 배지 — 사진/플레이스홀더 위 우하단. showPhoto 분기 밖에 둔다 — 로드 실패로 사진이
          사라져도(onError) 장수 정보까지 함께 사라지면 안 되기 때문(리뷰에서 지적된 버그).
          backdrop-filter가 없어도 읽혀야 한다(구형 WebView에서 no-op, UX-DR6). 그래서
          **불투명 다크 pill이 기본**이고 blur는 지원될 때만 얹는다(스토리 9.4 AC2).
          ✎ 2026-07-19 코드리뷰: 처음엔 `bg-black/80`(반투명)으로 나갔다. 대비는 통과했지만
            (흰 사진 위 합성 #333 → 12.63:1) AC2가 요구한 것은 **불투명**이고, 그런데도 Task
            체크박스는 AC 문구 그대로 닫혀 있었다 — 구현과 문서가 갈린 채 초록이던 자리다.
            불투명으로 맞춘다: 배경이 무엇이든 흰 글자 on #000 = **21:1**로 고정되고,
            "사진이 밝으면 어떻게 되나"라는 질문 자체가 사라진다.
        */
        <span className="pointer-events-none absolute bottom-2 right-2 rounded-badge bg-black px-2 py-0.5 text-xs font-semibold text-white supports-[backdrop-filter]:backdrop-blur-sm">
          {photoCount}장
        </span>
      )}
    </div>
  );
}
