'use client';

// 뒤로/앞으로가기로 되살아난 화면을 서버 최신 상태로 다시 그린다 (대장 DW-525 해소, 2026-07-29).
//
// **무슨 문제인가:** Next.js App Router는 스크롤 복원을 위해 back/forward 내비게이션을 **항상
// Router Cache에서** 되살린다 — 서버를 다시 부르지 않고 "그 페이지를 처음 열었을 때 서버가 만든
// 결과"를 그대로 복원한다. 그래서 그 사이에 바뀐 서버 파생 상태가 옛값으로 되돌아온다:
//   · 찜 하트(♡/♥) — 카드에서 찜한 뒤 다른 화면 갔다 뒤로가기 → 안 찜한 상태로 되돌아감(사용자 지적)
//   · 안읽음 배지 — 방에 들어가 읽고 뒤로가기 → 줄어들지 않은 옛 숫자(대장 DW-515/구 #215)
// 둘 다 **화면만** 틀리고 DB는 정확하다(주소로 새로 들어가면 맞는 값이 나온다). 그런데 사용자는
// 화면을 믿고 다시 누르므로, 찜에서는 방금 저장한 찜을 스스로 취소해 **데이터까지 틀어진다.**
//
// **이력 — 왜 이 파일이 원래 `ChatListBfcacheRefresh`였나:** 구 `#215`(안읽음 배지)를 고칠 때
// Story 12.6이 범위를 "`/chat` 목록 한 페이지"로 못박아 `if (path === '/chat')` 가드를 달았다.
// 그 좁은 가드가 곧바로 `DW-525`로 등재됐고(근본 원인은 라우트를 안 가리는 Next 동작인데 수정만
// 한 경로에 걸려 있다), 찜 하트에서 같은 결함이 그대로 재발했다. **이번에 가드를 걷어낸다** —
// 배지는 `AppHeader`가 소비자용 페이지 전부에 같은 방식으로 그리고 찜 하트도 여러 화면에 있어서,
// "어느 경로만"이라는 목록은 유지될 수 없다(빠뜨리는 순간 같은 버그가 조용히 되살아난다).
//
// **왜 페이지가 아니라 루트 레이아웃에 두나(원 파일에서 실측으로 확인된 사실 — 그대로 유지):**
//   1) 이 앱의 back/forward에서는 `pageshow`가 아니라 `popstate`가 온다. Next.js App Router가
//      popstate를 자체 가로채 클라이언트 라우팅만 할 뿐 실제 문서 언로드가 없기 때문이다.
//   2) 그런데 리스너를 대상 페이지 자신에 두면 못 잡는다 — 다른 화면으로 이동하는 순간 그 페이지
//      트리가 **언마운트**되고, `popstate`는 그 뒤 뒤로가기 시점에 오는데 그때는 아직 페이지가
//      다시 마운트되기 **전**이라 리스너가 없다. 자신을 되살리는 바로 그 이벤트를 구조적으로 놓친다.
//   그래서 이 전환 동안 언마운트되지 않는 유일한 자리 = 루트 레이아웃이다.
//
// `pageshow`도 함께 듣는다(DW-525가 지적한 나머지 절반): 외부 사이트로 나갔다 브라우저 뒤로가기로
// 돌아오는 **cross-document bfcache 복원**은 `popstate`가 아니라 `pageshow`(`persisted=true`)로
// 온다. 그때는 문서가 통째로 복원되므로 화면이 더 오래된 상태다.
//
// **대가(정직하게 적어 둠):** 뒤로가기 한 번마다 서버 렌더가 1회 더 돈다. 이 앱은 페이지마다 DB
// 왕복이 여러 번이라 공짜가 아니다(대장의 왕복 비용 항목과 같은 축). 그래도 "화면이 거짓말을 하고
// 사용자가 그 거짓말을 믿고 눌러 데이터를 망가뜨리는" 쪽보다 싸다고 봤다. 왕복 자체를 줄이는 일은
// 성능 묶음에서 따로 다룬다.
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function BackNavRefresh() {
  const router = useRouter();

  useEffect(() => {
    // 앱 내부 back/forward — Next가 popstate를 가로채 Router Cache에서 복원한 직후 서버를 다시 부른다.
    function handlePopState() {
      router.refresh();
    }
    // 문서 단위 bfcache 복원(외부 사이트 → 뒤로가기). persisted=false는 평범한 최초 로드라 제외한다
    // — 그 경우엔 방금 서버에서 받아온 화면이므로 새로고침이 순수한 낭비다.
    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) router.refresh();
    }
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('pageshow', handlePageShow);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('pageshow', handlePageShow);
    };
  }, [router]);

  return null;
}
