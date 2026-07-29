import type { NextConfig } from "next";

// 매물 사진의 원본 호스트(Supabase Storage 공개 버킷)를 next/image에 등록한다 — 대장 DW-541.
//
// **왜 필요해졌나(실측 2026-07-29):** 카드에 364×218px로 그리는 사진을 **1600×1067px 원본 그대로**
// 내려받고 있었고(픽셀 수로 약 20배, 장당 150~190KB), 게다가 Storage 오브젝트 181개 중 180개가
// `cache-control: no-cache`라 브라우저·CDN이 못 쟁여 **방문할 때마다 전부 다시 받았다.**
//
// 캐시 헤더를 원본에서 고치려 했으나 **안 된다는 것을 측정으로 확인**했다: `storage.objects`의
// `metadata->>'cacheControl'`을 고쳐도(운영에서 1건 시험) 실제 응답 헤더는 `no-cache` 그대로였다
// — 그 컬럼은 거울일 뿐이고 serve 시점 헤더는 스토리지 백엔드가 들고 있다. 고치려면 180개를
// 전부 재업로드해야 한다(운영 데이터 조작). 시험한 1건은 원래 값으로 되돌렸다.
//
// 그래서 **원본을 건드리지 않고** 앞단에서 푼다 — next/image가 (1) 표시 크기에 맞춰 줄여 주고
// (2) 최적화 결과를 자기 CDN 캐시에 오래 들고 있으므로, 크기와 캐시 두 축이 함께 해결된다.
//
// 호스트를 하드코딩하지 않고 `NEXT_PUBLIC_SUPABASE_URL`에서 끌어온다 — 로컬 스택(127.0.0.1:55321)과
// 운영(psrnsasxpkpwqdukjdmt.supabase.co)의 호스트가 다르고, 그 값은 이미 `scripts/use-env.sh`가
// 브랜치에 맞춰 갈아끼우는 단일 출처이기 때문이다(같은 값을 두 군데 적으면 갈린다).
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;

// 로컬 Supabase 스택(127.0.0.1:55321)을 보고 있는가. Next 16은 **사설 IP로 해석되는 원본 이미지의
// 최적화를 기본 차단**한다(SSRF 방어) — 실측: 로컬에서 전환 직후 사진 5장이 전부
// `400 Bad Request` + 서버 로그 `upstream image ... resolved to private ip ["127.0.0.1"]`.
// 즉 이 가드를 안 풀면 **로컬 개발에서만 사진이 통째로 안 보인다**(운영은 공개 호스트라 정상).
// 그래서 "지금 로컬 스택을 보고 있을 때만" 빗장을 푼다 — 운영 빌드는 호스트가 supabase.co라
// 이 값이 false로 남아 방어가 그대로 유지된다(환경으로 갈리는 것이지 코드가 갈리는 게 아니다).
function isLocalHost(url: string | undefined): boolean {
  if (!url) return false;
  try {
    const { hostname } = new URL(url);
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]';
  } catch {
    return false;
  }
}

const nextConfig: NextConfig = {
  images: {
    // 값이 없으면 빈 배열 → next/image가 어떤 원격 이미지도 최적화하지 않는다(빌드는 통과하되
    // 런타임에 그 사진만 실패한다). 환경변수 누락이 조용히 넘어가지 않고 화면에서 바로 드러난다.
    remotePatterns: supabaseUrl ? [new URL(`${supabaseUrl}/storage/v1/object/public/**`)] : [],
    dangerouslyAllowLocalIP: isLocalHost(supabaseUrl),
    // 최적화 결과 캐시 하한 1년. 매물 사진 URL은 업로드 시 발급된 UUID 경로라 **내용이 바뀌지 않는다**
    // (사진을 바꾸면 새 경로가 생긴다) — 그래서 길게 잡아도 옛 사진이 남는 문제가 생기지 않는다.
    minimumCacheTTL: 31_536_000,
  },
};

export default nextConfig;
