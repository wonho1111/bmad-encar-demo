# Deferred Work

## ✅ 해소됨 (Story 1.4, 2026-06-20)

- **Supabase 클라이언트 env 누락 가드 부재** (1-1·1-2 코드리뷰 이연 2건) — `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화. 누락 시 어떤 변수(`NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`)가 비었는지 명시한 한국어 에러를 throw하고, `client.ts`·`server.ts`·`session.ts`가 공유한다. proxy(`web/src/proxy.ts`)는 env 누락 시 한국어 경고 로그 + 요청 통과(`NextResponse.next()`)로 graceful 처리. → `process.env.…!` 비-널 단언 제거 완료.

---

## Deferred from: code review of story 1-4 (2026-06-20)

- **`redirectedFrom` 소비처 부재 + open-redirect 검증 규약 미정** [web/src/proxy.ts, web/src/app/(auth)/login/page.tsx] — proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만, 로그인 화면은 이를 읽지 않고 항상 `/`로 이동한다(현재 무해). 향후 "로그인 후 원래 가려던 곳으로 복귀" 스토리에서 `redirectedFrom`을 사용할 때, 반드시 값이 `/`로 시작하는 **상대경로**인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트를 막을 것. 보호경로가 `/admin` 1개뿐이라 현재 영향은 작음.

## Deferred from: code review of story 2-3 (2026-06-20)

- **options(text[]) 라운드트립이 쉼표 포함 외부생성 값에 손실 가능** [web/src/app/(user)/sell/SellForm.tsx] — 수정 폼이 options를 쉼표로 join(미리채움)/split(저장)한다. 그래서 폼 밖(시드·API)에서 한 배열원소에 쉼표를 포함해 넣은 옵션은 첫 수정·저장 때 두 개로 쪼개진다. pre-existing(2-2 등록 폼도 동일 규칙). 현재 폼 입력만으로는 쉼표 포함 원소가 만들어지지 않아 영향 없음. 시드 매물(2-5)·가이드/임베딩(Epic 4)에서 쉼표 포함 옵션을 도입할 경우, 입력 구분자를 바꾸거나(예: 줄바꿈) 옵션을 칩(chip) UI로 받는 방식을 검토할 것.
