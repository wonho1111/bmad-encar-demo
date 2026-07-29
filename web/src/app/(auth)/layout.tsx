// 인증 화면(로그인·회원가입) 공용 레이아웃 — 상단바를 붙이는 것이 유일한 목적이다 (대장 DW-547).
//
// **왜 생겼나:** 이 두 화면엔 상단바가 아예 없어서, 들어오면 **주소창을 직접 고치는 것 말고는
// 나갈 방법이 없었다**(사용자 지적 2026-07-29). 랜딩·탐색은 비로그인도 볼 수 있는데(FR58)
// 정작 로그인 화면에서 그리로 돌아갈 길이 끊겨 있었다.
//
// Story 11.3이 **같은 부류를 이미 한 번 고쳤다**(구 `#152` — 비로그인 홈에 상단바가 없어
// "로그인·내 차 등록 진입로가 거기 하나뿐"이던 문제). 인증 화면 2개만 그 처리에서 빠졌다.
//
// **왜 페이지가 아니라 레이아웃인가:** `login/page.tsx`·`signup/page.tsx`는 둘 다 `'use client'`라
// 서버 컴포넌트인 `AppHeader`를 직접 렌더할 수 없다. 라우트 그룹 레이아웃(서버 컴포넌트)이
// 헤더를 그리고 페이지를 children으로 받는 것이 Next의 정석이고, 두 화면에 같은 코드를 두 벌
// 두지 않아도 된다.
//
// `email`을 넘기지 않으므로 `AppHeader`는 안읽음 카운트 RPC를 **호출하지 않는다**(그 안의 `if (email)`
// 가드) — 이 레이아웃이 DB 왕복을 늘리지 않는다.
//
// ⚠️ **이 레이아웃은 "갇힘"만 푼다 — 화면 자체의 리스킨은 하지 않는다.** 로그인·회원가입 본문은
// 아직 옛 원시 색(`zinc-*`)을 쓰고 있고(대장 `DW-546`, 소비자 8~9화면 공통), 그 통일은 Epic 15에서
// 관리자 6화면과 함께 한다(사용자 결정 2026-07-29).
import type { ReactNode } from 'react';
import AppHeader from '@/components/layout/AppHeader';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {/* currentPath를 안 넘긴다 — 넘기면 헤더의 "로그인" 링크가 `?redirectedFrom=/login`을 달아
          자기 자신으로 돌아오는 고리를 만든다. 여기선 그냥 /login으로 두는 게 맞다. */}
      <AppHeader email={null} />
      {children}
    </>
  );
}
