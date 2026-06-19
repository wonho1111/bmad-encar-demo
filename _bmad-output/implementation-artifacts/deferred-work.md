# Deferred Work

## Deferred from: code review of story 1-2 (2026-06-19)

- **Supabase 클라이언트 env 누락 가드 부재(재확인)** [web/src/lib/supabase/client.ts, server.ts] — 가입 화면에서 env 미설정 시 `createClient()`가 throw → 화면엔 "네트워크 오류"로 오표기되어 원인 진단이 어렵다. Story 1.1에서 동일 항목을 middleware/접근제어 스토리로 이연했으며, Story 1.4(middleware) 도입 시 친절한 env 가드 + 명확한 한국어 안내로 함께 처리한다.

## Deferred from: code review of story 1-1 (2026-06-19)

- **브라우저/서버 Supabase 클라이언트 env 누락 가드 부재** [web/src/lib/supabase/client.ts:7, server.ts:10] — `process.env.…!` 비-널 단언이 컴파일러만 침묵시키고 런타임 가드는 없음. 환경변수 미설정(빌드/배포 시) 시 `createBrowserClient/createServerClient`가 불투명한 에러로 throw. `@supabase/ssr` 표준 패턴이고 오설정 시에만 발생하므로 데모 범위에선 경미. middleware 도입 스토리(역할별 접근 제어)에서 친절한 env 가드와 함께 재검토.
