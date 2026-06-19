# Deferred Work

## ✅ 해소됨 (Story 1.4, 2026-06-20)

- **Supabase 클라이언트 env 누락 가드 부재** (1-1·1-2 코드리뷰 이연 2건) — `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화. 누락 시 어떤 변수(`NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`)가 비었는지 명시한 한국어 에러를 throw하고, `client.ts`·`server.ts`·`session.ts`가 공유한다. proxy(`web/src/proxy.ts`)는 env 누락 시 한국어 경고 로그 + 요청 통과(`NextResponse.next()`)로 graceful 처리. → `process.env.…!` 비-널 단언 제거 완료.

---

## Deferred from: code review of story 1-4 (2026-06-20)

- **`redirectedFrom` 소비처 부재 + open-redirect 검증 규약 미정** [web/src/proxy.ts, web/src/app/(auth)/login/page.tsx] — proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만, 로그인 화면은 이를 읽지 않고 항상 `/`로 이동한다(현재 무해). 향후 "로그인 후 원래 가려던 곳으로 복귀" 스토리에서 `redirectedFrom`을 사용할 때, 반드시 값이 `/`로 시작하는 **상대경로**인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트를 막을 것. 보호경로가 `/admin` 1개뿐이라 현재 영향은 작음.

## Deferred from: code review of story 2-3 (2026-06-20)

- **options(text[]) 라운드트립이 쉼표 포함 외부생성 값에 손실 가능** [web/src/app/(user)/sell/SellForm.tsx] — 수정 폼이 options를 쉼표로 join(미리채움)/split(저장)한다. 그래서 폼 밖(시드·API)에서 한 배열원소에 쉼표를 포함해 넣은 옵션은 첫 수정·저장 때 두 개로 쪼개진다. pre-existing(2-2 등록 폼도 동일 규칙). 현재 폼 입력만으로는 쉼표 포함 원소가 만들어지지 않아 영향 없음. 시드 매물(2-5)·가이드/임베딩(Epic 4)에서 쉼표 포함 옵션을 도입할 경우, 입력 구분자를 바꾸거나(예: 줄바꿈) 옵션을 칩(chip) UI로 받는 방식을 검토할 것.

## Deferred from: code review of story 2-4 (2026-06-20)

- **sold→on_sale DB 재오픈 미차단(단방향 트리거 없음)** [supabase/migrations/0002_listings.sql, web/src/app/(user)/sell/ListingActions.tsx] — `listings_update_own` RLS는 소유권만 보고 status 전이 방향을 강제하지 않는다. 본인 sold 매물을 `update status='on_sale'`로 재오픈하는 것이 DB 차원에서 가능하다. 2-1 설계가 의도적으로 단방향 트리거를 두지 않았고, 본 스토리 범위 주의에 "재오픈 UI는 범위 밖(과잉구현 금지)"으로 명시됨 — 현재 UI에는 재오픈 경로가 없어 영향 없음. 향후 "구매 완료 단방향 고정" 또는 "재오픈 기능"을 정식 도입할 때, BEFORE UPDATE 트리거(`old.status='sold' → 거부`)나 RLS WITH CHECK로 정책을 명시할 것.
- **단일 `error` useState를 handleComplete·handleDelete가 공유** [web/src/app/(user)/sell/ListingActions.tsx] — 두 핸들러가 같은 `error` 슬롯을 쓴다. 각 핸들러 시작 시 `setError(null)`로 초기화하지만 성공 경로에서는 명시 초기화가 없다. 2-3에서 내려온 패턴. 한 행에 버튼이 모여 있어 실사용 혼선은 작음. 핸들러가 더 늘면 핸들러별 에러 상태 분리를 검토.
- **`OwnListing.status` 타입이 `string`(union `ListingStatus` 미사용)** [web/src/app/(user)/sell/page.tsx:21] — 2-2부터 내려온 cosmetic. `LISTING_STATUS.ON_SALE` 비교는 정상 동작하나, union 타입을 쓰면 오타·미정의 status 비교를 컴파일타임에 잡을 수 있다. 다른 select 타입 정리 시 함께 union으로 좁힐 것.

## Deferred from: code review of story 2-5 (2026-06-20)

- **데모 자격증명 평문 커밋(seller-seed@test.com / seller123)** [supabase/seed.sql] — 시드 전용 판매자 계정이 평문 비밀번호로 저장소에 커밋된다. 기존 admin 시드(1.5)의 동일 패턴을 상속했고, ⚠️ 주석과 스토리 Completion Notes에 "운영 전 교체"가 명시돼 있다. 환경별 게이팅(운영 DB에 시드 미적용)은 본 스토리 범위 밖. 운영 배포 전 비밀번호 교체 또는 시드 환경 분리를 정식 도입할 것.
- **고아 auth.users(profiles 없음)/handle_new_user 트리거 비활성 시 재실행 중단** [supabase/seed.sql:163-174] — 시드 판매자 계정이 auth.users엔 있으나 profiles가 없는 손상 상태(트리거 비활성/0001 미적용/외부 생성 고아)에서 재실행하면 안전장치 `raise exception`이 전체 시드를 중단시킨다. admin 시드와 동일한 의도된 fail-loud 가드(조용한 실패보다 즉시 드러냄)지만 자가복구 경로는 없다. 시드 자동화를 강화할 경우 profiles 부재 시 직접 삽입하는 self-heal 경로를 검토.
- **멱등 delete가 향후 listings 자식 테이블 FK를 가정하지 않음** [supabase/seed.sql:178] — 재실행 시 시드 매물을 delete 후 새 uuid로 재삽입한다. 현재 listings는 leaf 테이블이라 무해하나, 향후 즐겨찾기·구매기록 등 listings.id를 FK로 참조하는 테이블이 생기면 (a) delete가 막히거나 (b) 외부가 들고 있던 옛 listing id가 dangling 된다. 그런 자식 테이블 도입 시 시드 멱등 전략(고정 id 사용·자식 정리 순서)을 재설계할 것.
