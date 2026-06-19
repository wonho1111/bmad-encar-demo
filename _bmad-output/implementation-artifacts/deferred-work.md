# Deferred Work

## ✅ 해소됨 (Story 1.4, 2026-06-20)

- **Supabase 클라이언트 env 누락 가드 부재** (1-1·1-2 코드리뷰 이연 2건) — `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화. 누락 시 어떤 변수(`NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`)가 비었는지 명시한 한국어 에러를 throw하고, `client.ts`·`server.ts`·`session.ts`가 공유한다. proxy(`web/src/proxy.ts`)는 env 누락 시 한국어 경고 로그 + 요청 통과(`NextResponse.next()`)로 graceful 처리. → `process.env.…!` 비-널 단언 제거 완료.

---

(현재 미해소 이연 항목 없음)
