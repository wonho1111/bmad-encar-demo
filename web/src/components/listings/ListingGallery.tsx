'use client';

// 매물 상세의 사진 갤러리 (Story 9.5 AC2·AC4·AC9).
//
// **왜 클라이언트 컴포넌트인가:** "지금 몇 번째 사진을 보고 있나"라는 상태와 로드 실패 감지(onError)는
// 브라우저에서만 존재한다. 페이지 나머지(정보 섹션·CTA)는 서버 컴포넌트로 남긴다 — 상세 페이지
// 전체를 클라이언트로 만들면 얻는 것 없이 번들만 커진다.
//
// **구성(DESIGN.md:141):** 대표 사진 5:3 + 하단 썸네일 스트립 + 우하단 "1/N" 카운터 + 좌우 화살표.
// 라이트박스(확대보기)는 Epic 9 Non-goal이라 만들지 않는다.
//
// **어떤 사진을 몇 장 받나(NFR7):** 큰 사진은 **지금 보는 1장만** DOM에 있다(대표 자리의 <img> 하나).
// 썸네일은 같은 URL을 lazy로 받아 두므로, 사진을 넘길 때 대표 자리는 **브라우저 캐시에서 즉시** 뜬다
// (저장본이 이미 작다 — 9.3이 긴 변 ≤1600px·WebP·q0.82로 줄여 실측 196~205KB).
// 별도 썸네일 규격을 만들지 않는 이유도 같다 — 저장본을 다시 만들지 않는다(I14).
import { useState } from 'react';

/** 로드 실패한 사진의 자리에 그리는 "사진 준비중" 판(카드의 플레이스홀더와 같은 언어). */
function PhotoPlaceholder({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-1 bg-placeholder-bg text-ink-muted">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className={compact ? 'h-5 w-5' : 'h-9 w-9'}
      >
        <path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2.2l1.2-2h8.2l1.2 2h2.2A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5v-9Z" />
        <circle cx="12" cy="13" r="3.2" />
      </svg>
      {/* 썸네일 자리(compact)엔 글자를 넣지 않는다 — 44px 칸에 13px 글자를 우겨넣으면 D5가 금지한
          줄바꿈 찌그러짐이 난다. 아이콘만으로도 "사진 아님"은 읽힌다. */}
      {!compact && <span className="text-meta font-medium">사진 준비중</span>}
    </div>
  );
}

export default function ListingGallery({ urls, title }: { urls: string[]; title: string }) {
  const [index, setIndex] = useState(0);
  // **인덱스 단위로** 실패를 기억한다 — 대표와 썸네일이 같은 URL을 쓰므로 한 번 실패한 사진은
  // 양쪽 모두 플레이스홀더가 된다(둘이 따로 판단하면 큰 자리만/작은 자리만 깨져 보인다).
  const [failed, setFailed] = useState<ReadonlySet<number>>(new Set());
  const markFailed = (i: number) =>
    setFailed((prev) => (prev.has(i) ? prev : new Set(prev).add(i)));

  // ⚠️ **`onError` 하나로는 부족하다 — 2겹이어야 한다** (conventions.md §10.2, 9.4 실브라우저 실측).
  // 서버가 그린 <img>는 HTML이 도착하는 즉시 로드를 시작하는데, **하이드레이션이 끝나기 전에** 실패하면
  // React가 그 이벤트를 재생하지 않아 `onError`가 **영영 발화하지 않는다.** 그리고 파일 없음(404)은
  // 정확히 그렇게 빨리 실패한다 — 가장 흔한 실패가 유일한 방어를 그냥 지나간다.
  // 그래서 ref 콜백으로 **이미 끝난 로드의 결과를 직접 본다**: complete인데 naturalWidth가 0이면 실패다.
  // (`getPublicUrl`은 파일 존재를 확인하지 않으므로, 이 2겹이 깨진 이미지를 막는 유일한 장치다.)
  const detectAlreadyFailed = (i: number) => (img: HTMLImageElement | null) => {
    if (img && img.complete && img.naturalWidth === 0) markFailed(i);
  };

  const count = urls.length;

  // 사진 0장 = 정상 상태다(conventions §10.2). 빈 영역이 아니라 5:3 플레이스홀더를 그린다.
  if (count === 0) {
    return (
      <div className="aspect-[5/3] w-full overflow-hidden rounded-card border border-border-hairline">
        <PhotoPlaceholder />
      </div>
    );
  }

  // 인덱스가 범위를 벗어나지 않게 감싼다(맨 끝 → 처음). 끝에서 버튼을 비활성으로 두지 않는 이유:
  // 상용 중고차 갤러리의 관행이고, 비활성 버튼의 흐린 대비를 사진 위에 얹지 않아도 된다.
  const go = (delta: number) => setIndex((i) => (i + delta + count) % count);

  return (
    // 키보드 ←/→: 갤러리 안의 버튼(화살표·썸네일)에 포커스가 있을 때 동작한다.
    //   컨테이너에 tabIndex를 주지 않는 이유 — 탭 순서에 "아무것도 안 하는 정거장"을 만들지 않기 위해서다.
    //   포커스는 항상 진짜 <button> 위에 있고, 키 이벤트는 거기서 버블링돼 여기로 온다.
    <div
      className="flex flex-col gap-2"
      onKeyDown={(e) => {
        if (count < 2) return;
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          go(-1);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          go(1);
        }
      }}
    >
      {/* ① 대표 사진 5:3 — aspect-ratio가 자리를 미리 잡아 레이아웃 시프트가 0이다(NFR7). */}
      <div className="relative aspect-[5/3] w-full overflow-hidden rounded-card border border-border-hairline bg-placeholder-bg">
        {failed.has(index) ? (
          <PhotoPlaceholder />
        ) : (
          /* 평범한 <img>를 쓴다(next/image 아님) — 9.4와 같은 판단: 저장본이 이미 작고,
             next.config.ts에 images.remotePatterns가 없으며, 공개 URL이 고정이라 캐시가 그대로 먹는다.
             크롭은 저장본을 다시 만들지 않고 클라 렌더 크롭으로만 한다(object-cover 중앙, I14). */
          /* eslint-disable-next-line @next/next/no-img-element -- 위 주석의 결정(저장본이 이미 최적화됨) */
          <img
            key={urls[index]}
            ref={detectAlreadyFailed(index)}
            src={urls[index]}
            alt={`${title} 사진 ${index + 1}/${count}`}
            loading="lazy"
            decoding="async"
            onError={() => markFailed(index)}
            className="h-full w-full object-cover"
          />
        )}

        {count > 1 && (
          <>
            {/* 좌우 화살표 = 진짜 <button>(키보드·스크린리더 도달 가능, aria-label 한국어).
                44×44 터치 타깃. 불투명 다크 원 — 사진이 밝든 어둡든 흰 글리프 대비가 고정된다
                (9.4의 "1/N" 배지가 반투명에서 불투명으로 바뀐 것과 같은 이유). */}
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label="이전 사진"
              className="absolute left-2 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black text-white cursor-pointer"
            >
              <span aria-hidden="true" className="text-lg leading-none">
                ‹
              </span>
            </button>
            <button
              type="button"
              onClick={() => go(1)}
              aria-label="다음 사진"
              className="absolute right-2 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black text-white cursor-pointer"
            >
              <span aria-hidden="true" className="text-lg leading-none">
                ›
              </span>
            </button>
          </>
        )}

        {/* "1/N" 카운터 — 대표 사진 우하단. 사진이 로드에 실패해 플레이스홀더가 떠도 **계속 보인다**
            (분기 밖에 둔 이유: 장수 정보까지 함께 사라지면 안 된다 — 9.4 코드리뷰에서 지적된 버그).
            한 줄 유지: whitespace-nowrap(D5 — 세로로 접지 않는다). */}
        <span className="pointer-events-none absolute bottom-2 right-2 whitespace-nowrap rounded-badge bg-black px-2 py-0.5 text-xs font-semibold text-white">
          {index + 1}/{count}
        </span>
      </div>

      {/* ② 썸네일 스트립 — **가로 유지**. 좁아지면 접지 말고 가로 스크롤한다(D5).
          사진이 1장이면 고를 것이 없어 그리지 않는다(같은 사진 하나짜리 줄 = 의미 없는 잉크). */}
      {count > 1 && (
        <ul className="flex gap-2 overflow-x-auto scrollbar-hide" aria-label="사진 목록">
          {urls.map((url, i) => (
            <li key={url} className="shrink-0">
              <button
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`${i + 1}번째 사진 보기`}
                aria-current={i === index ? 'true' : undefined}
                className={`block h-14 w-20 overflow-hidden rounded-chip border-2 cursor-pointer ${
                  i === index ? 'border-brand-petrol' : 'border-border-hairline'
                }`}
              >
                {failed.has(i) ? (
                  <PhotoPlaceholder compact />
                ) : (
                  /* eslint-disable-next-line @next/next/no-img-element -- 위와 같은 결정 */
                  <img
                    ref={detectAlreadyFailed(i)}
                    src={url}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    onError={() => markFailed(i)}
                    className="h-full w-full object-cover"
                  />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
