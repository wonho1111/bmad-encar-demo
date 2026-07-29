import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import ChatListBfcacheRefresh from "./(user)/chat/ChatListBfcacheRefresh";

// Pretendard(한글+라틴) self-host. Google Fonts에 없어 next/font/google 불가 — next/font/local로
// 저장소 내 .woff2를 직접 로드한다(fonts/PretendardVariable.woff2, 라이선스는 fonts/LICENSE.txt).
// CDN <link>와 달리 next/font가 자동으로 fallback metric을 보정해 폰트 스왑 시 리플로우(FOUT/CLS)를 줄인다 —
// 단, adjustFontFallback 기본값은 로컬 폰트 한정 'Arial'(next/font/local엔 한글 지표 옵션이 없음)이라
// 이 보정은 라틴 문자에만 적용되고 한글 본문에는 적용되지 않는다.
// weight를 명시하는 이유: 생략하면 next/font가 @font-face에 font-weight 서술자를 아예 안 넣고, 가변축 해석이
// 엔진 기본값에 맡겨진다(Chromium은 축을 그대로 살리지만 CSS Fonts 4 기본값은 normal=400 고정이라 클램프
// 가능). 값은 이 바이너리의 fvar wght 축을 직접 읽어 맞췄다 — min 45 / default 400 / max 930. 교체 전 CDN
// CSS는 45 920으로 상한을 10 낮게 적고 있었으므로, 그 값을 베끼지 않고 실제 축을 서술한다.
// 출처: github.com/orioncactus/pretendard — dist/web/variable/woff2/PretendardVariable.woff2
//       Version 1.309 (name ID 5), sha256 9599f12fd42fc0bce1cd50b47a0c022e108d7aa64dd0d1bb0ed44f3282d900b4
// 용량 실측(2026-07-27): 이 파일 2,057,688 B(≈1.96MiB, 정적 서브셋 미적용 = 한글 전체 글리프). 교체된 CDN
// dynamic-subset은 CSS 59,900 B + unicode-range 92분할(청크당 약 34~44KB)이라 페이지는 쓰는 범위만 받았다.
// 즉 요청 수는 줄었지만 첫 방문 전송량은 자릿수 단위로 늘었다. preload 태그는 프리렌더 라우트(/login·/signup)
// 에만 붙고 동적 렌더 라우트(/·/search)엔 붙지 않는다 — 빌드 산출물 실측(.next/server/app/*.html).
// 서브셋 파이프라인 신설은 이 스토리 범위 밖(Never)이라 미루되 조용히 넘기지 않는다 — docs/tech-debt.md에
// 트리거와 함께 등재했다. 전/후 first paint는 아직 측정되지 않았다(같은 항목에 기재).
const pretendard = localFont({
  src: "./fonts/PretendardVariable.woff2",
  weight: "45 930",
  variable: "--font-pretendard",
  display: "swap",
});

export const metadata: Metadata = {
  title: "중고차 직거래",
  description: "중고차 직거래 서비스 (데모)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={`h-full antialiased ${pretendard.variable}`}>
      {/* suppressHydrationWarning: ColorZilla 등 브라우저 확장이 <body>에 속성(cz-shortcut-listen 등)을
          주입해 생기는 하이드레이션 경고를 억제한다. body 한 단계 속성만 해당되며, 내부 컴포넌트의
          실제 불일치는 그대로 감지된다. (Next.js 공식 권장 — 확장 프로그램 주입 케이스) */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {/* /chat 뒤로가기 배지 새로고침(대장 #215 최소 수정) — 루트 레이아웃에 두는 이유는
            web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx 파일 상단 주석 참조(요약: /chat과
            /chat/[roomId] 사이를 오갈 때 이 자리만 언마운트되지 않는다). 화면엔 아무것도 렌더하지
            않는다(null) — /chat이 아닌 페이지의 뒤로가기에는 그 컴포넌트 내부 가드가 반응하지 않는다. */}
        <ChatListBfcacheRefresh />
        {children}
      </body>
    </html>
  );
}
