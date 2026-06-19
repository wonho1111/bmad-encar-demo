# Deferred Work

## Deferred from: code review of story 1-1 (2026-06-19)

- **브라우저/서버 Supabase 클라이언트 env 누락 가드 부재** [web/src/lib/supabase/client.ts:7, server.ts:10] — `process.env.…!` 비-널 단언이 컴파일러만 침묵시키고 런타임 가드는 없음. 환경변수 미설정(빌드/배포 시) 시 `createBrowserClient/createServerClient`가 불투명한 에러로 throw. `@supabase/ssr` 표준 패턴이고 오설정 시에만 발생하므로 데모 범위에선 경미. middleware 도입 스토리(역할별 접근 제어)에서 친절한 env 가드와 함께 재검토.
