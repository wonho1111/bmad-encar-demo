'use client';

// 랜딩 히어로: AI 자연어 검색 진입점 (spec-11-3, FR33) — 딥 petrol 밴드 + 흰 검색 pill + 제안칩 4개.
//
// 핵심 계약(에픽 AC개정 2026-07-14 "체감≠실행"):
//   입력창은 로그인 여부와 무관하게 항상 활성 상태다(비활성화·자물쇠·사전 안내 금지 — 시도 전에
//   거절하지 않는다). 실제 분기는 "제출하는 순간"에만 일어난다:
//     · 비로그인 → /ai/search를 호출하지 않고 질의를 sessionStorage에 보존한 채 로그인 게이트로.
//     · 로그인 → /ai로 이동해 그 질의를 1회 자동 실행(핸드오프는 heroSearchHandoff 단일 출처,
//       ChatAssistant가 마운트 시 소비).
//   제안칩 클릭도 "그 문장으로 즉시 제출"과 동일하게 취급한다(입력창에 먼저 채우지 않는다).
//
// 마운트 시에는 반대 방향 핸드오프(비로그인 제출 → 로그인 성공 → '/' 복귀)를 소비한다: 입력창에
// 질의를 복원만 하고 자동 실행하지 않는다(사용자가 다시 눌러야 함 — 새로고침·뒤로가기로 인한
// 중복 이동 방지). 이 컴포넌트가 클라이언트인 이유: 입력값·마운트 복원(useEffect)·제출 시 라우팅
// 분기가 전부 브라우저 상태·이벤트라 서버 컴포넌트로는 불가능하다.
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { consumeHeroSearchHandoff, setHeroSearchHandoff } from '@/lib/heroSearchHandoff';

// 입력 상한(spec Always) — ChatAssistant의 MAX_QUERY_LENGTH(1000, 서버 SearchRequest.query 상한과
// 일치)와 값만 다른 같은 스타일의 가드. 히어로는 "체감" 단계라 별도 500자 상한을 둔다(AC7).
const MAX_QUERY_LENGTH = 500;

// 제안칩 4종 — landing-1.html 목업 원문 그대로(Code Map).
const SUGGESTIONS = [
  '가성비 좋은 첫차',
  '4천만원대 전기 SUV',
  '주행거리 짧은 무사고 세단',
  '7인승 디젤 패밀리카',
] as const;

export default function HeroSearch({ authed }: { authed: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState('');

  // 마운트 1회: 비로그인 제출 후 로그인 성공 → '/' 복귀 케이스만 여기서 소비한다(로그인 사용자의
  // autoRun:true 핸드오프는 /ai로 직행하므로 여기 도달하지 않는다 — ChatAssistant가 대신 소비).
  // 읽는 즉시 삭제(1회용)이므로 다음 새로고침엔 이미 비어 있어 다시 채워지지 않는다.
  //   queueMicrotask + cleanup 없음(WishButton.tsx와 동일 관례): React Strict Mode는 개발 모드에서
  //   마운트 effect를 (실행→cleanup→실행) 2회 왕복시킨다. setTimeout으로 지연시키면 그 cleanup이
  //   예약을 취소해버려 복원이 영영 안 일어나는 조용한 버그가 난다(WishButton.tsx가 실측으로 문서화한
  //   바로 그 함정). queueMicrotask는 취소 수단이 없어 2회차 호출은 consumeHeroSearchHandoff가 이미
  //   비운 storage를 보고 그냥 return하고, 1회차가 예약한 microtask만 최종적으로 실행된다.
  useEffect(() => {
    // autoRun:false만 내 몫이다 — autoRun:true는 ChatAssistant(/ai) 몫이라 여기선 손대지 않는다
    // (11-3 코드리뷰 지적: 무조건 소비하면 로그인 사용자의 자동실행 핸드오프를 여기서 가로챌 수 있었다).
    const handoff = consumeHeroSearchHandoff(false);
    if (!handoff) return;
    queueMicrotask(() => setQuery(handoff.query));
  }, []);

  // 제출 공통 경로 — 입력 제출과 제안칩 클릭이 여기로 합류한다(spec: "칩 클릭 = 입력 제출과 동일").
  async function submit(rawQuery: string) {
    // 방어적 길이 재확인 — <input maxLength>가 타이핑·붙여넣기를 대체로 막지만, 제안칩은 그 경로를
    // 안 거치므로(ChatAssistant의 1000자 가드와 동일 스타일) 여기서 한 번 더 자른다.
    const trimmed = rawQuery.trim().slice(0, MAX_QUERY_LENGTH);
    if (trimmed === '') return;

    if (authed) {
      // `authed`는 서버 렌더 시점 값이다 — 그 사이 세션이 만료되면 authed=true인 채로 여기까지 온다.
      // 재검증 없이 autoRun:true 핸드오프부터 써버리면, 뒤이은 /ai 이동이 proxy.ts에 의해 로그인으로
      // 튕겨나가도 그 핸드오프는 sessionStorage에 고아로 남아 나중에 엉뚱한 시점에 자동실행될 수
      // 있다(재과금 위험 — 11-3 코드리뷰 지적). WishButton.tsx의 applyToggle과 동일하게 클릭 시점에
      // 다시 확인한다.
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        // 로그인: 게이트 없이 /ai로 이동해 1회 자동 실행. autoRun을 읽는 즉시 지워 재과금을 막는다.
        setHeroSearchHandoff({ query: trimmed, autoRun: true });
        router.push('/ai');
        return;
      }
      // 세션이 실제로는 만료된 상태 — 아래 비로그인 분기로 그대로 흘려보낸다(재시도해도 안 되는
      // "실패" 취급이 아니라, !authed 클릭과 동일하게 로그인 게이트로 보낸다).
    }

    // 비로그인(또는 위에서 세션 만료가 확인된 경우): /ai/search를 호출하지 않는다. 질의만 보존하고
    //   로그인 게이트로 보낸다. redirectedFrom=%2F(=`/`) — 로그인 성공 후 이 히어로로 돌아와 위
    //   마운트 effect가 복원한다.
    setHeroSearchHandoff({ query: trimmed, autoRun: false });
    router.push('/login?redirectedFrom=%2F');
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void submit(query);
  }

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand-petrol-strong to-petrol-deepest px-6 py-14 sm:px-10 sm:py-16">
      <div className="relative mx-auto flex max-w-3xl flex-col items-start gap-4">
        <h1 className="text-display font-extrabold leading-tight text-white">
          원하는 차를 <span className="text-accent-amber">말</span>로 찾으세요
        </h1>
        <p className="max-w-xl text-body text-white/75">
          &ldquo;3천만원대 무사고 흰색 SUV&rdquo;처럼 그냥 말하듯 검색하면, AI가 조건에 맞는 직거래
          매물을 바로 골라줍니다.
        </p>

        {/* 검색 pill — D5: 모든 뷰포트에서 가로 1행(아이콘+입력+카운터+버튼) 유지, 세로 스택 금지. */}
        <form
          onSubmit={handleSubmit}
          className="flex w-full max-w-xl flex-nowrap items-center gap-2 rounded-full bg-surface-raised py-2 pl-5 pr-2 shadow-float"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
            className="h-[18px] w-[18px] shrink-0 text-ink-muted"
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M21 21l-4.3-4.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={MAX_QUERY_LENGTH}
            placeholder="예: 3천만원 이하 하이브리드 세단 추천해줘"
            aria-label="AI 검색 질의 입력"
            // 시도 전에 거절하지 않는다(Always) — disabled·readOnly를 어떤 로그인 상태에서도 붙이지 않는다.
            className="min-w-0 flex-1 bg-transparent text-sm text-ink-primary outline-none placeholder:text-ink-muted"
          />
          <span className="shrink-0 whitespace-nowrap text-caption text-ink-muted" aria-hidden="true">
            {query.length}/{MAX_QUERY_LENGTH}
          </span>
          <button
            type="submit"
            className="shrink-0 whitespace-nowrap rounded-full bg-accent-amber px-5 py-2.5 text-sm font-extrabold text-amber-ink sm:px-6 sm:py-3"
          >
            검색
          </button>
        </form>

        {/* 제안칩 4개 — petrol 반투명 상시 제안(대화 중 되묻기 칩과는 다른 별도 스타일, 섞지 않는다). */}
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => void submit(s)}
              className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-caption font-medium text-white/90 transition-colors hover:bg-white/15"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
