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

export default function ListingCardImage({
  url,
  count,
  alt,
}: {
  url?: string | null;
  count?: number | null;
  alt: string;
}) {
  const [failed, setFailed] = useState(false);

  // 계약-외 값 방어(conventions.md §4): 빈 문자열도 "사진 없음"으로 본다 — `!url`이 이미 ''를 거른다.
  const showPhoto = Boolean(url) && !failed;
  // 음수 count는 0으로 깎는다(§4). 배지는 1장 이상일 때만 뜬다.
  const photoCount = Math.max(0, count ?? 0);

  return (
    <div className="relative aspect-[5/3] w-full overflow-hidden rounded-t-card bg-placeholder-bg">
      {showPhoto ? (
        <>
          {/*
            평범한 <img>를 쓴다(next/image 아님) — 이유:
              · 저장본이 이미 작다(9.3이 업로드 전 긴 변 ≤1600px·WebP·q0.82로 줄인다, 실측 196~205KB)
              · next.config.ts에 images.remotePatterns가 없어 next/image는 설정 추가가 선행이다
              · 공개 URL이 고정이라 브라우저·CDN 캐시가 그대로 먹는다
            크롭은 저장본을 다시 만들지 않고 클라 렌더 크롭으로만 한다(object-cover 중앙, I14).
            aspect-[5/3]가 자리를 미리 잡아 지연 로드에도 레이아웃이 밀리지 않는다(NFR7).
          */}
          {/* eslint-disable-next-line @next/next/no-img-element -- 위 주석의 결정(저장본이 이미 최적화됨) */}
          <img
            src={url as string}
            alt={alt}
            loading="lazy"
            decoding="async"
            onError={() => setFailed(true)}
            className="h-full w-full object-cover"
          />
          {photoCount >= 1 && (
            /*
              "N장" 배지 — 사진 위 우하단.
              backdrop-filter가 없어도 읽혀야 한다(구형 WebView에서 no-op, UX-DR6). 그래서
              **반투명 다크 pill이 기본**이고 blur는 지원될 때만 얹는다.
              대비 실측(2026-07-19): 최악 조건(완전 흰 사진 위, blur 미지원)에서도
              흰 글자 on black/80 합성 = #333333 → **12.63:1** (AA 4.5:1 여유 통과).
            */
            <span className="pointer-events-none absolute bottom-2 right-2 rounded-badge bg-black/80 px-2 py-0.5 text-xs font-semibold text-white supports-[backdrop-filter]:backdrop-blur-sm">
              {photoCount}장
            </span>
          )}
        </>
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
            className="h-7 w-7"
          >
            <path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2.2l1.2-2h8.2l1.2 2h2.2A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5v-9Z" />
            <circle cx="12" cy="13" r="3.2" />
          </svg>
          <span className="text-meta font-medium">사진 준비중</span>
        </div>
      )}
    </div>
  );
}
