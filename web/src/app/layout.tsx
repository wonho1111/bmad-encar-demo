import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="ko" className="h-full antialiased">
      {/* Pretendard(한글+라틴)를 CDN dynamic-subset로 로드 — Google Fonts에 없어 next/font/google 불가.
          dynamic-subset은 실제 쓰이는 글리프만 내려받는다. 로드 실패 시 globals.css --font-sans의
          시스템 한글 폰트로 폴백. self-host(next/font/local)는 CDN 신뢰성 문제 시 승격 대안(Story 8.1 Dev Notes). */}
      <head>
        <link
          rel="preconnect"
          href="https://cdn.jsdelivr.net"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
        />
      </head>
      {/* suppressHydrationWarning: ColorZilla 등 브라우저 확장이 <body>에 속성(cz-shortcut-listen 등)을
          주입해 생기는 하이드레이션 경고를 억제한다. body 한 단계 속성만 해당되며, 내부 컴포넌트의
          실제 불일치는 그대로 감지된다. (Next.js 공식 권장 — 확장 프로그램 주입 케이스) */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
