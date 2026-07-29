'use client';

// 방 목록(/chat)의 안읽음 배지가 뒤로가기 복귀 시 옛 값으로 되살아나는 문제(대장 #215)의 최소 수정
// (Story 12.6, 스펙이 사전 승인한 두 예외 중 하나) — 실측(같은 스토리 검증 중): 방에 진입해 읽음
// 처리(last_read_at 갱신)가 서버에 실제로 반영된 뒤 브라우저 뒤로가기로 이 페이지에 돌아오면,
// Next Router Cache가 "읽음 처리 전" RSC 렌더를 그대로 복원해 배지가 줄어들지 않은 채로 보였다
// (같은 상태에서 새로고침하면 정확한 값이 나온다 — 계산 자체는 옳고 뒤로가기 경로만 어긋난다).
//
// ⚠️ **스펙은 이 트리거를 `pageshow`(`event.persisted`, bfcache 복원)로, 배치 위치를 `/chat` 페이지
// 자신으로 지정했으나, 이 스토리의 실측(Playwright로 직접 확인)에서 둘 다 성립하지 않았다**:
//   1) `pageshow`는 이 앱의 back/forward 전환에서 전혀 발생하지 않는다(Next.js App Router가
//      popstate를 자체 가로채 클라이언트 라우팅만 수행할 뿐 실제 문서 언로드/bfcache 복원이 없기
//      때문 — `pageshow`는 진짜 문서 단위 내비게이션/bfcache에서만 온다). 실제로 발생하는 것은
//      `popstate`다(같은 실측으로 확인).
//   2) 그런데 `popstate`를 이 컴포넌트를 `/chat` 페이지(`page.tsx`)에서 렌더해 감지해도 배지가
//      갱신되지 않았다 — `/chat/[roomId]`로 이동하는 순간 이 페이지 트리가 즉시 **언마운트**되고
//      (실측 로그로 확인), `popstate`는 그 뒤 브라우저가 뒤로가기를 실행하는 시점에 발생하는데,
//      그 시점엔 아직 `/chat` 페이지가 다시 마운트되기 **전**이라 리스너가 없다. 리스너가 있는
//      새 인스턴스는 그 popstate 이후에야 만들어지므로, 자신을 되살리는 바로 그 이벤트를 구조적으로
//      놓친다(닭이 먼저냐 달걀이 먼저냐 문제 — 어떤 브라우저 이벤트를 고르든 페이지 자신에
//      두는 한 못 잡는다).
// 그래서 이 컴포넌트는 `/chat` 자신이 아니라 **루트 레이아웃**(`app/layout.tsx`)에서 렌더한다 —
// `(user)` 라우트 그룹엔 전용 layout이 없어 루트 레이아웃이 `/chat`·`/chat/[roomId]` 둘의 유일한
// 공통 조상이고, 그래서 이 전환 동안 **언마운트되지 않는** 유일한 자리다. `popstate` 발생 시점에
// `location.pathname`이 `/chat`일 때만 `router.refresh()`를 호출해, 다른 화면의 뒤로가기에는 영향을
// 주지 않는다(다른 라우트로의 확장이 아니라 이 한 페이지의 새로고침 트리거를 살아있는 자리로 옮긴
// 것뿐이다). router.refresh()는 서버 컴포넌트(`/chat` 페이지의 채팅방 목록·배지 계산)를 최신
// 데이터로 다시 렌더한다 — 이 파일은 그 트리거만 배선할 뿐 배지 계산 로직 자체(AppHeader·
// chat_unread_count())는 건드리지 않는다(A3 — 외과적 변경 중 "필요한 최소"의 재정의는 위치이지 범위가
// 아니다).
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ChatListBfcacheRefresh() {
  const router = useRouter();

  useEffect(() => {
    function handlePopState() {
      // /chat으로 뒤로가기 복귀할 때만 새로고침한다 — 다른 라우트의 뒤로가기에는 영향 없음.
      // 끝 슬래시를 지우고 비교한다(코드리뷰 patch) — 정규화 없이 '/chat'과 엄격 비교하면 직접 URL
      // 입력·외부 링크로 올 수 있는 '/chat/' 변형에서 이 컴포넌트가 고치려는 바로 그 버그(#215)가
      // 조용히 재발한다. 끝 슬래시를 모두 지운 뒤 남는 게 빈 문자열이 되는 경우는 '/'뿐이라
      // '/chat'과 절대 같아지지 않는다.
      const path = window.location.pathname.replace(/\/+$/, '');
      if (path === '/chat') {
        router.refresh();
      }
    }
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [router]);

  return null;
}
