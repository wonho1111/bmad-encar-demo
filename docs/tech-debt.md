# 기술부채 정리 (Technical Debt Register)

> *기술부채(technical debt)* — 지금 당장은 돌아가지만, "나중에 갚아야 할 빚"처럼 남겨둔 미완성·임시방편·미검증 항목. 방치하면 이자(장애·재작업)가 붙는다.

- **작성일:** 2026-07-10 · **대장 일원화:** 2026-07-15
- **출처:** 각 스토리 코드리뷰 이월 + 에픽 회고 1~8 + 코드 스캔(TODO)
- **기준 상태:** Epic 1~8 + 회고 done. 증분 Epic 9~16 backlog.
- **읽는 법:** 🔴 = 운영/제출 전 필수 · 🟡 = 조건부(지금 무해, 조건 바뀌면 위험) · 🟢 = 품질·테스트 보강 · 🔒 = 구조적 보류(규칙을 바꿔야 풀림) · ⚪ = 의도적 보류(부채 아님, 참고용) · 📅 = 스토리로 예약됨(부채 아님 — 계획된 작업)
- **배포 순서·마이그레이션 게이트:** `docs/deployment-runbook.md` 참조.

---

## 요약 대시보드

| 우선순위 | 건수 | 한 줄 |
|---|---|---|
| 🔴 필수 | 1 | 안드로이드 서명 (#2) |
| 🟡 조건부 | **18** | 재오픈 차단 · 타입 · **테이블 GRANT(#18 — Epic 9가 건드림)** · 관리자 운영 실사용 미확인 · 거래일 `sold_at` 부재 · **게이트 구조적 대가 3종(#22~24 — Epic 13이 건드림)** · psycopg 버전핀 · 폐기토큰 401 · **시드 멱등 delete(#27 — Epic 9·10이 건드림)** · **문서부채 4종(#28~31)** · *(📅 예약: #6 멱등키 · #7 폴링배너 · #11 옵션쉼표)* |
| 🟢 품질/테스트 | **16** | AI 정규화 회귀테스트 · FR17 경로 · Riverpod 컨트롤러 · 누수테스트 의존 · DSN 포트 · anon 테스트 중복 · 시드 self-heal · FocusTrap 2종 · ErrorState tone · error useState · **Pretendard self-host(#40 — 결정됐으나 스토리 미배정)** · 런북 §8 누락 · 가이드라인 레포밖 · *(📅 예약: #15 LIMIT · #16 거리컷오프)* |
| 🔒 구조적 보류 | 1 | 완전 계정 삭제 (#21 — `service_role` 키 금지가 프로젝트 규칙) |
| 📅 스토리로 예약됨 | 2 (+5) | `RowSkeleton`(Epic 12·15) · FocusTrap `role="dialog"` 규약(Epic 11) *(+ 위 섹션 내 📅 표기 5건)* |
| ⚪ 의도적 보류 | 3 | 관리자 대시보드(Cut) · 찜 인기신호 · 문서기반 차량상태 |
| ✅ 해소 | **3** (+3) | DB 커넥션 풀(8.4) · 채팅 본문 길이(0010) · open-redirect(8.5) *(+ 부록: 4-1 이월 3건이 4.2·4.6·4.7에서 해소된 것으로 2026-07-15 실측 확인)* |

> **건수가 21 → 41로 늘어난 건 부채가 늘어서가 아니다.** `deferred-work.md`에 흩어져 있던 열린 항목을 여기로 흡수했고(대장 일원화), 이번 검토에서 문서부채 5건(#28~31·#41~42)을 새로 등록했다. **미룬 것도 적는 게 대장의 일이다** — 안 적으면 "안 한 것"과 "했는지 모르는 것"이 구별되지 않고, 후자가 더 비싸다.

> **⚠️ 이 대장이 유일한 열린 일 장부다.** "지금 뭐가 열려 있나"는 **이 파일 하나로** 답한다(CLAUDE.md B8).
>
> **회고 액션·코드리뷰 지적은 반드시 여기 등록하고, 해소하면 여기서 닫는다.** 회고는 "왜"를 갖고, 이 대장이 "무엇/상태"를 갖는다.
>
> **경위(왜 그렇게 결정했나)는 `_bmad-output/implementation-artifacts/deferred-work.md`**에 있다 — 그 파일은 **경위 보관용으로 동결됐고 열린 일을 갖지 않는다**(2026-07-15 통합). 결정 근거(party-mode·실측 반증)를 찾을 때만 본다.
>
> <details><summary>왜 이렇게 됐나 (2026-07-15 통합 경위)</summary>
>
> Epic 8 회고가 **대장 4개**(`sprint-status.yaml`·이 파일·`deferred-work.md`·회고 8개)를 진단하고 A1으로 이 파일을 단일 출처로 정했으나, 그 문장이 *"이 파일 **또는** `deferred-work.md`에 등록한다"* 였다. **"또는"이 남은 순간 대장은 계속 2개였고**, 실해가 났다 — #18(테이블 GRANT)이 여기선 "(b) 사용자 승인 필수", `deferred-work.md`에선 "(a) dev 자율로 안전"으로 **정반대 판정**을 들고 있었다(코드리뷰가 (a)→(b)로 정정했는데 한쪽만 고침). Epic 9의 첫 마이그레이션이 정확히 그 축을 건드린다. 2026-07-15에 열린 항목을 전부 여기로 흡수하고 `deferred-work.md`를 동결해 "또는"을 없앴다.
> </details>

---

## 🔴 운영/제출 전 반드시 처리

### 2. 안드로이드 릴리스 서명 미설정
- **위치:** `app/android/app/build.gradle.kts:30` (코드 내 유일한 TODO)
- **내용:** release 빌드가 아직 debug 서명 설정을 씀. `// TODO: Add your own signing config for the release build.`
- **왜 위험:** 정식 스토어 배포·서명된 APK 산출 불가.
- **해소:** 실제 배포 시 keystore 생성 + `signingConfigs` 설정. (Epic 7 회고 이월, app은 현재 수동 배포 전이라 즉시 영향은 없음)

> ℹ️ 구 #3(앱 픽셀 E2E 미검증)·#4(AI 라이브 호출 0회)는 **2026-07-11 실폰 무선 디버깅 검증으로 해소** → 하단 `부록: 해소된 부채` 참조.

---

## 🟡 조건부 부채 (지금 무해, 조건이 바뀌면 위험)

> *조건부(conditional)* — 현재 코드 경로에선 발생하지 않지만, 특정 기능·규모·입력이 도입되면 터지는 부채.

### 5. AI API DB 커넥션 풀링·타임아웃·async 블로킹 부재
- **위치:** `api/app/db/readonly.py`, `api/app/auth.py`
- **내용:** `readonly_connection()`이 호출마다 새 psycopg 연결을 열고 풀이 없음 → 동시 부하 시 Supabase Session 풀러(:5432, 낮은 연결한도) 고갈 가능. `connect_timeout` 미설정이라 풀러가 멈추면 무한 대기. 동기 호출이 `async def` 안에서 실행돼 이벤트 루프 블록.
- **트리거:** AI 검색 동시 사용자가 늘어날 때.
- **해소:** 실제 DB 경로가 붙은 지금, 커넥션 풀 + `connect_timeout` + 스레드풀/async 드라이버 도입. (원래 4.3에서 도입 예정이었던 항목)
- ✅ **해소 완료 (Story 8.4, `e1057df`)** — `api/app/db/readonly.py`에 `psycopg_pool.ConnectionPool` 도입(`max_size=8`), `SET LOCAL ROLE`로 트랜잭션 스코프 롤 격리, `asyncio.to_thread`로 논블로킹화, `PoolTimeout` → 503 한국어 안내. 8.5 코드리뷰가 죽은 풀 영구 캐시·liveness·종료 훅까지 보강. *(✎ 2026-07-15 회고: 이 항목은 8.4가 해소했는데 대장이 🟡로 남아 있었다 — drift 3건 중 하나.)*

### 6. 채팅 커밋 후 응답 유실 시 중복 전송 (멱등키 부재)
- **위치:** `web/.../chat/[roomId]/ChatRoomMessages.tsx` (handleSubmit catch)
- **내용:** INSERT가 DB엔 성공했으나 응답이 네트워크에서 끊기면 catch가 입력을 복원 → 사용자 재전송 → 서로 다른 id의 중복 메시지 영속(id 기준 dedupe로 못 막음).
- **트리거:** 불안정 네트워크에서 전송 중 끊김.
- **해소:** 멱등키(클라 생성 uuid를 PK로) 도입.
- 📅 **예약됨: `12-1-멱등키-마이그레이션`** (backlog) — 부채가 아니라 계획된 작업이다.

### 7. 채팅 폴링 영구 실패 시 무알림
- **위치:** 동상 (폴링 effect)
- **내용:** 첫 로드 실패는 한국어 에러로 표시(loud)하지만, 세션 만료·방 삭제로 폴링이 매 주기 영구 실패하면 아무 표시 없이 대화가 멈춘 것처럼 보임(silent). loud/silent 비대칭.
- **트리거:** 장시간 방치 후 세션 만료, 관리자의 방 삭제.
- **해소:** N회 연속 실패 후 비차단 배너(재연결/오프라인 표시).
- 📅 **예약됨: `12-4-재연결-배너-갭-보정`** (backlog). Epic 12가 폴링을 Realtime으로 걷어내므로 이 항목의 형태 자체가 바뀐다.

### 8. 채팅 본문 최대 길이 가드 없음
- **위치:** `web/src/lib/messages.ts` (sendMessage / 입력창)
- **내용:** `body`가 `text`(무제한), 클라는 `trim()`만. 초대용량 붙여넣기가 그대로 INSERT → 행·폴링 페이로드 비대화.
- **트리거:** 대용량 텍스트 붙여넣기.
- **해소:** 입력창 `maxLength` + 서버측 길이 컷.
- ✅ **해소 완료 (2026-07-11, `b720370`)** — 3층 강제: DB CHECK(`0010_chat_message_length.sql`, `char_length(body) <= 2000`) + web 입력창 `maxLength` + `sendMessage` 길이 가드. 값은 `web/src/lib/constants.ts`의 `CHAT.MESSAGE_MAX_LENGTH`가 미러링. 계약은 `docs/conventions.md` §7. *(✎ 2026-07-15 회고: drift 3건 중 하나.)*

### 9. sold→on_sale 재오픈 DB 미차단 (단방향 트리거 없음)
- **위치:** `supabase/migrations/0002_listings.sql`, `web/.../sell/ListingActions.tsx`
- **내용:** `listings_update_own` RLS는 소유권만 보고 status 전이 방향을 강제하지 않음. 본인 sold 매물을 `update status='on_sale'`로 재오픈하는 것이 DB 차원에서 가능(현재 UI엔 재오픈 경로 없어 무해).
- **트리거:** 재오픈 UI 도입 시.
- **해소:** BEFORE UPDATE 트리거(`old.status='sold' → 거부`) 또는 RLS WITH CHECK로 단방향 고정 명시.

### 10. open-redirect 검증 규약 미정
- **위치:** `web/src/proxy.ts`, `web/.../login/page.tsx`
- **내용:** proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만 로그인 화면은 안 읽고 항상 `/`로 이동(현재 무해).
- **트리거:** "로그인 후 원래 위치 복귀" 기능 도입 시.
- **해소:** `redirectedFrom` 값이 `/`로 시작하는 상대경로인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트 방지.
- ✅ **해소 완료 (Story 8.5, `5bc6463`)** — 트리거가 실제로 발동했다(비로그인 열람을 열며 "로그인 후 복귀"가 필요해짐). `web/src/lib/auth/redirect.ts`의 `resolveSafeRedirect`가 `//`·`http(s):`·역슬래시를 차단하고, 8.5 코드리뷰가 `/login` 자기참조 데드엔드까지 추가 차단. **web 최초의 단위 테스트**(`redirect.test.ts` + Vitest)로 방어 케이스 고정.
- 📌 **이 항목의 교훈(회고 2026-07-15)**: Epic 1·2·3·4 회고에 **네 번 연속 "이연"** 으로 등장했고 매번 *"현재 미사용이라 무해"* 로 넘겼다. **그 판단은 네 번 다 옳았다** — 실제로 필요해진 8.5에서 고쳤다. **미루는 판단은 틀린 게 아니다. 고친 뒤 대장을 안 닫은 것만 틀렸다.**

### 11. options(text[]) 쉼표 포함 값 라운드트립 손실
- **위치:** `web/.../sell/SellForm.tsx`
- **내용:** 수정 폼이 options를 쉼표로 join/split. 폼 밖(시드·API)에서 한 배열원소에 쉼표를 넣으면 첫 수정 저장 시 둘로 쪼개짐(현재 폼 입력만으론 발생 안 함).
- **트리거:** 시드/가이드/임베딩에서 쉼표 포함 옵션 도입 시.
- **해소:** 입력 구분자 변경(줄바꿈) 또는 칩(chip) UI.
- 📅 **예약됨: `10-3-옵션-통제어휘-우선순위-상수-저장구조-정비`** (backlog) — 통제어휘·저장구조 정비가 이 라운드트립 문제를 함께 닫는다.

### 12. `OwnListing.status` 타입이 `string` (union 미사용)
- **위치:** `web/src/app/(user)/sell/page.tsx:21`
- **내용:** cosmetic. `LISTING_STATUS.ON_SALE` 비교는 정상이나 union 타입이면 오타·미정의 status 비교를 컴파일타임에 잡음.
- **해소:** 다른 select 타입 정리 시 union으로 좁힘.

### 18. 테이블 GRANT가 마이그에 없고 Supabase 플랫폼 기본에 의존
- **위치:** 마이그레이션 전체(`0011_listings_anon_select.sql`의 `anon`+`listings`만 예외 — 명시 REVOKE/GRANT로 이 의존을 끊었음).
- **내용:** `grant select on <table> to authenticated`가 어느 마이그레이션에도 없다(profiles·chat_rooms·chat_messages 포함). `authenticated` 데이터 경로 전체가 Supabase 플랫폼이 기본으로 발급하는 GRANT(`pg_default_acl`)에 암묵 의존한다. 마이그레이션 게이트(Story 8.6)의 프렐류드가 이 기본 GRANT를 실측 재현해 fresh DB에서도 통과하지만, 그건 **Supabase 플랫폼 위에서만** 참이다.
- **오늘 무해한 이유:** Supabase 전제(사용자 확정, 납품 계획 없음)이고, 재해 복구 시에도 새 Supabase 프로젝트가 같은 기본 GRANT를 자동으로 준다.
- **트리거(언제 문제되나):** 자체 호스팅·타 클라우드 이관·"맨 Postgres로도 선다"는 납품 요구가 생기는 순간.
- **8.5가 우연히 발견한 사실:** anon+listings에 대해서만 이 의존을 끊었다 — **체계적으로 찾은 게 아니라 다른 일(FR58) 하다 우연히 걸린 것**이다. 나머지(authenticated 전 경로)가 얼마나 되는지 아무도 세어본 적 없다.
- **해소:** 각 테이블 마이그에 명시 `grant select ... to authenticated`를 추가한 뒤, 프렐류드(`scripts/migration-check-prelude.sql`)의 `alter default privileges` 한 줄을 제거한다. 비용 ≈ 테이블당 1~2줄.
- **⚠️ 착수 시 판정: (b) — 사용자 승인이 필요하다** (`docs/conventions.md` §9.3). *(2026-07-15 코드리뷰 정정: 이 항목은 원래 "(a) 해당 — dev 자율로 안전"이라 적혀 있었으나 **틀렸다.** §9.3 (a)는 3조건을 **전부** 만족해야 하는데, 조건①이 "수정이 **멱등 가드 추가만**"이고 조건③이 "기존 객체 정의 불변 — **GRANT 대상 변경은 이 틀 밖**"이다. 명시 GRANT 추가는 가드가 아니고 정확히 GRANT 대상 변경이라 **두 조건을 동시에 어긴다**. 규칙을 만든 커밋이 그 규칙의 첫 적용 사례에서 스스로를 위반하고 있었던 것 — 이대로 뒀으면 다음 사람이 이 항목을 근거로 마이그 여러 개에 GRANT를 자율 추가하고 사후 보고해 §9.3 방어선이 첫 실사용에서 뚫렸을 것이다.)*
- **참고:** "원격 델타 0"은 사실이다(원격엔 플랫폼이 이미 같은 GRANT를 발급했으므로 재적용해도 상태가 안 변한다). 그러나 §9.3의 (a)/(b)는 **델타만이 아니라 변경의 성격**으로 가른다 — 델타 0이어도 GRANT 대상을 건드리면 (b)다.
- ⛔ **되살리지 말 것 — 실측으로 반증된 주장**: *"게이트가 초록이어도 fresh DB는 `authenticated`가 매물을 못 읽는다"* → **2026-07-14 도커 실측 결과 거짓.** 프렐류드가 플랫폼 기본 GRANT를 선언하므로 잘 읽는다(`has_table_privilege(authenticated, listings, select)` = **t**). 이 주장은 party-mode에서 "가장 무서운 발견"으로 채택돼 AC·런북·메모리까지 박혔다가 실측 한 번에 뒤집혔다. **진짜 남은 비용은 따로 있다** — 게이트의 초록은 *"마이그 + 선언된 Supabase 계약면 = 도는 DB"* 를 뜻하지 *"마이그만으로 = 도는 DB"* 를 뜻하지 않는다.
- **⚠️ 2026-07-15 대장 일원화 시 정정**: `deferred-work.md`가 이 항목을 **"판정규칙 (a) 해당(원격 델타 0 → 안전)"** 으로 들고 있었다 — 위 (b) 판정과 **정반대**다. 코드리뷰가 (a)→(b)로 정정했는데 한쪽만 고쳐서 생긴 라이브 모순이었고, 통합하며 (b)로 통일했다. **Epic 9의 첫 마이그레이션이 이 축을 건드린다** — 착수 시 이 항목을 근거로 GRANT를 자율 추가하지 말 것.
- **근거:** `docs/deployment-runbook.md` §8-① · `_bmad-output/implementation-artifacts/8-6-ac-deploy-1-배포-순서-마이그레이션-게이트.md`

---

### 19. Epic 6 관리자 4화면 운영 실사용 미확인 (Epic 6 회고 이월)
- **위치:** 운영 `https://bmad-encar-demo.vercel.app/admin` (회원·매물·거래·채팅)
- **내용:** Epic 6 회고가 액션으로 남긴 "main 배포 반영 후 운영 /admin 4화면 실사용 확인"이 **수행 흔적이 없다.** `main` 병합·배포 자체는 확인됨(`94c62ec`, Vercel Production READY). 코드는 preview E2E로 검증됐으므로 결함 가능성은 낮으나 **운영 화면을 사람이 본 적이 없다.**
- **트리거:** 데모·제출 시연 직전.
- **해소:** 운영 /admin 4화면 클릭 1회.
- 📌 *(2026-07-15 회고 A2 등록: Epic 6 회고 → Epic 7 회고가 추적하지 않아 1개월간 소실됐던 항목. 회고 체인 끊김의 실물.)*

### 20. 거래일이 `updated_at` 근사 (정확한 `sold_at` 부재, Epic 6 회고 이월)
- **위치:** 관리자 거래 내역 화면 · `listings` 테이블
- **내용:** 거래일을 `updated_at`으로 근사 표시한다. **타임존 차이로 ±1일 어긋날 수 있다.** 실측 확인: `supabase/migrations/` 전수 grep 결과 `sold_at` 컬럼 **0건 = 미구현 확정**.
- **트리거:** 거래일 정확도가 요구될 때(정산·리포트 등). 데모 범위에선 무해.
- **해소:** `sold_at timestamptz` 컬럼 추가(nullable, additive) + 구매완료 액션에서 기록 + KST 표시. 마이그 신규 1장.
- 📌 *(2026-07-15 회고 A2 등록. Epic 6 회고가 "정확과 간이를 투명하게 구분해 남긴다"는 좋은 판단으로 남긴 항목인데, 대장에 등록하지 않아 추적이 끊겼다.)*

### 21. 🔒 완전 계정 삭제 불가 — 구조적 보류 (Epic 6 회고 이월)
- **위치:** 관리자 회원 관리 (`profiles` 행만 삭제)
- **내용:** 회원 "삭제"가 `profiles` 행만 제거하고 **`auth.users`의 로그인 계정 자체는 남는다.** 삭제하려면 `service_role` 키 + `auth.admin.deleteUser()`가 필요한데, **`service_role` 키 금지가 이 프로젝트의 확립된 규칙**이다(`_bmad-output/project-context.md` 규칙 6 · `docs/conventions.md` §5).
- **왜 🔒인가:** 다른 부채처럼 "나중에 하면 되는 것"이 아니다. **해소하려면 프로젝트 보안 규칙 자체를 바꿔야 한다.** 규칙을 유지하는 한 영구 보류다.
- **트리거:** 개인정보 완전 삭제가 법적·계약적으로 요구될 때. 그 순간 **규칙 6 재검토가 선행**돼야 한다(사용자 승인 필요).
- 📌 *(2026-07-15 회고 A2 등록. 이전엔 "미해결"로만 떠돌았으나 실은 **결정된 절충**이다 — 라벨을 정확히 하는 게 이 등록의 목적.)*

### 22. 게이트의 `--single-transaction`이 `create index concurrently`류를 원천 차단 (8.6 리뷰 이월)
- **위치:** `scripts/check_migrations.py:143`
- **내용:** 게이트가 마이그를 단일 트랜잭션으로 적용한다. `create index concurrently`·`vacuum`·`alter system`·`reindex`는 트랜잭션 안에서 못 돈다 → 원격 `apply_migration`에선 통과하는데 **게이트만 `cannot run inside a transaction block`으로 red**.
- **오늘 무해한 이유:** 실측 — 현재 마이그 12개 전량에 해당 구문 **0건**.
- **트리거:** **Epic 13(RAG)이 무중단 HNSW 인덱스를 얹는 순간.**
- **해소:** `--single-transaction`을 되돌리지 말 것(게이트 출력이 거짓말하는 걸 막는 근거로 도입됨). **진짜 문제는 게이트가 마이그 작성 방식을 몰래 제약하는데 그 제약이 어느 문서에도 없다는 것** → `docs/deployment-runbook.md` §8 사각지대에 추가.

### 23. `0004`·`0006`의 `create role ai_readonly` 이중 보유 = 조용한 드리프트 장치 (8.6 리뷰 이월)
- **위치:** `supabase/migrations/0004_guide_documents.sql:52-56` · `0006_readonly_role.sql:24-28`
- **내용:** 둘 다 `if not exists` 멱등 가드라, 미래에 0006을 `login`·`connection limit` 등 **다른 속성으로 고치면 fresh DB에선 0004가 먼저 만들고 0006은 no-op** → 롤이 0006 의도와 다르게 생성된다. 에러 0건 + 프로브 3건 통과 = **게이트 초록**, 그런데 원격은 0006 정의를 가져 **fresh ≠ 원격**.
- **트리거:** 0006의 롤 정의를 바꿔야 할 때.
- **왜 이렇게 뒀나:** 8.6의 in-place 수정(party-mode 안 A, 사용자 확정)이 치른 구조적 대가. 런북 §8-②가 "fresh DB == 원격을 보증하지 않는다"를 이미 인정하나, **그 사각지대의 원인을 이 패치가 하나 더 만들었다**는 사실은 안 적혔다.

### 24. 프렐류드 `auth.users` 3컬럼 스텁이 실제 플랫폼보다 좁다 — 양방향 오류 (8.6 리뷰 이월)
- **위치:** `scripts/migration-check-prelude.sql:531-535`
- **내용:** **false red** — 미래 마이그가 `created_at`·`last_sign_in_at`·`phone`을 참조하면 원격은 정상인데 게이트만 red. **false green** — 실제 `auth.users.email`은 `varchar(255)`+unique인데 스텁은 `text`+무제약이라, **unique 위반을 유발하는 마이그가 fresh에선 통과하고 원격에서 터진다.**
- **오늘 무해한 이유:** 실측 — 현재 마이그 중 해당 컬럼 참조 0건.
- **트리거:** 마이그가 `auth.users`의 3컬럼 밖을 참조할 때.
- **해소:** 스텁을 실제 플랫폼 정의에 맞춤. 런북 §8-③은 *"프렐류드가 선언한 것에 대한 의존은 안 잡힌다"* 만 인정하고 **선언이 실제보다 좁아서 생기는 오류**는 다루지 않는다.

### 25. `psycopg[binary,pool]` 버전 미고정 (8.4 리뷰 이월)
- **위치:** `api/pyproject.toml` · `api/requirements.txt`
- **내용:** `ConnectionPool(..., open=True)` 생성자 패턴이 최신 `psycopg_pool`에서 지양되는 추세라, 버전 미고정 상태로는 업그레이드 시 경고/동작 변경 위험.
- **트리거:** 의존성 업그레이드 시. **해소:** 버전 핀 추가.

### 26. 취소·삭제된 토큰 보유자가 공개 페이지에서 401 데드엔드 (8.5 리뷰 이월)
- **위치:** `web/src/lib/api/aiSearch.ts:60-62`
- **내용:** `supabase.auth.getSession()`은 `expires_at`이 미래이기만 하면 서버에 묻지 않고 캐시 세션을 돌려준다 → 이미 폐기된(계정 삭제·세션 강제만료·타 기기 비번변경) 토큰인 줄 모른 채 `Authorization` 헤더에 붙인다. 서버는 401 "유효하지 않은 인증 토큰입니다."를 던지고 사용자는 빨간 알럿을 본다. **재시도해도 동일** — 쿠키가 안 지워져 같은 토큰이 계속 나간다. 역설: `/ai`는 **공개** 페이지라 같은 사람이 시크릿창에선 멀쩡히 쓴다.
- **트리거:** 드문 경로(폐기된 토큰 보유).
- **해소:** 401 시 헤더 없이 1회 재시도, 또는 `signOut()` 후 anon 재요청. 서버측 401은 `conventions.md` §8 계약상 의도된 동작이므로 **방어는 클라이언트 몫**. ⚠️ *"무효 토큰 사용자를 조용히 anon으로 떨어뜨릴 것인가"* 는 **제품 판단이 필요**하다.

### 27. 시드 멱등 delete가 `listings` 자식 테이블 FK를 가정하지 않음 (2-5 리뷰 이월)
- **위치:** `supabase/seed.sql`
- **내용:** 재실행 시 시드 매물을 delete 후 **새 uuid로 재삽입**한다. 현재 `listings`는 leaf 테이블이라 무해하나, `listings.id`를 FK로 참조하는 테이블이 생기면 (a) delete가 막히거나 (b) 외부가 들고 있던 옛 listing id가 dangling 된다.
- **⚠️ 트리거가 실제로 온다:** **Epic 10.5 `wishlists`(마이그 0015 예정)가 `listings`의 첫 자식 테이블이다.** Epic 9 `listing_images`도 마찬가지(`ON DELETE CASCADE`라 delete는 통과하지만 이미지 행이 조용히 사라진다).
- **해소:** 시드 멱등 전략 재설계 — 고정 id 사용 또는 자식 정리 순서 명시. **Epic 9·10 착수 시 함께 판단.**

### 28. `e2e-checklist.md`가 정상 동작을 실패로 판정 (문서 부채)
- **위치:** `docs/e2e-checklist.md:24`
- **내용:** *"비로그인으로 … **보호 경로(`/search` 등) 접근 시 로그인으로 리다이렉트(307)**"* 라 적혀 있으나, **Story 8.5 이후 `/search`는 열람(anon 허용)이다** — `conventions.md` §8 · `web/src/proxy.ts:26` → `PROTECTED_PREFIXES = ['/admin','/sell','/ai','/chat']`(`/search` 없음).
- **왜 위험:** 이 체크리스트를 그대로 수행하면 **멀쩡한 코드를 "고치는" 회귀**를 유발한다. E2E 크로스체크가 이 문서를 대본으로 쓴다.
- **해소:** §8 계약(열람/행동)에 맞춰 항목 재작성. **E2E 착수 전 필수.**

### 29. CI가 web·api·app 테스트를 한 번도 안 돌린다 (B9 구멍)
- **위치:** `.github/workflows/` (워크플로가 `migration-gate.yml` **하나뿐**)
- **내용:** 유일한 CI의 `paths:` 필터가 `supabase/migrations/**`·`scripts/**`·워크플로 자신이라, **그 밖을 건드리는 push엔 게이트가 아예 안 돈다.** 결과: `api/tests/` 16파일(pytest) · web vitest(`redirect.test.ts` 등) · `app/test/` 10파일 77테스트가 **CI에서 한 번도 실행되지 않는다.** git hook도 0개.
- **왜 위험:** `project-context.md` 규칙 12(테스트 층별 표준)와 AC-DB-1 롤 누수 테스트가 **로컬에서 누가 치기 전엔 아무것도 지키지 않는다.** CLAUDE.md B9("규칙은 실행되는 검사로 바꾼다")의 정면 구멍.
- **해소:** 층별 테스트 워크플로 추가(api pytest · web vitest · app flutter test). 비용 낮음(전부 이미 존재하는 테스트를 돌리기만 하면 됨).

### 30. `db-schema-guide.md`가 마이그레이션 3장을 모른다 (문서 부채)
- **위치:** `docs/db-schema-guide.md:8` · `:204` · §4 표
- **내용:** *"스키마 단일 출처: `supabase/migrations/`(**0001~0009**)"* 라 적혀 있으나 실측 **12개**다. §4 표에서 `0010`(채팅 길이 CHECK)·`0011`(anon SELECT)·`0003c`(chat_rooms 무결성 트리거)가 누락(0003c는 §2-3 본문엔 있음).
- **트리거:** 발표·시연에서 이 문서를 스키마 설명서로 쓸 때. **해소:** 표 갱신. 증분이 마이그 8장을 더 얹으므로 **Epic 9~16 종료 후 한 번에** 하는 게 쌀 수 있다.

### 31. `architecture.md`(baseline)가 현재와 다른 사실을 명령형으로 적고 있다 (문서 부채)
- **위치:** `_bmad-output/planning-artifacts/architecture.md` (2026-06-18 동결)
- **내용:** 배포 **Vercel 우선**(:218 — 실제는 api=Cloud Run, Vercel은 480MB>250MB로 폐기) · 생성 모델 **`gemini-flash-latest`**(:50 — 실제 `gemini-3.1-flash-lite` 고정) · **Next 16.2.7**(:82 — 실제 16.2.9). Vercel 번들 한도도 **500MB(:51) vs 250MB(project-context)** 로 두 값이다.
- **왜 위험:** `:505`가 *"모든 아키텍처 결정을 문서 그대로 따른다"* 고 **요구**한다. `architecture-increment-2026-07-12.md:79`가 "배포 드리프트 정정"이라 선언하지만 **baseline 본문은 안 고쳐졌다.**
- **판단 필요:** "동결된 baseline = 역사"로 두고 상단에 *"현행은 증분 문서"* 경고만 붙일지, 본문을 고칠지. **선택지 A(경고 배너)가 쌈** — 동결 문서를 고치면 "동결"의 의미가 사라진다.

## 🟢 품질 / 테스트 보강 (기능 정상, 회귀 보호 부족)

> *회귀(regression)* — 잘 되던 게 나중 변경으로 조용히 깨지는 것. 자동 테스트가 없으면 못 알아챔.

### 13. AI 단위 정규화·차형 매핑 결정론적 단위테스트 부재
- **위치:** `api/tests/`
- **내용:** "3천만원→price≤30000000", "세단→body_type IN(...)" 근거가 LLM 프롬프트 + 라이브 1회에만 존재. 프롬프트 변경 시 조용히 깨질 수 있음.
- **해소:** LLM 출력을 모킹한 정규화·매핑 회귀 테스트 추가.

### 14. FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버
- **위치:** `api/tests/test_auth.py`
- **내용:** 200 테스트가 `sql_rag_node`를 통째로 monkeypatch → 실제 0건→`_ANSWER_EMPTY`(FR17) 경로와 `body_type IN(...)` SQL의 가드 통과가 단위테스트로 미확인.
- **해소:** 노드 내부 분기·가드 IN-절 통과 케이스 테스트 보강.

### 15. LIMIT 비정수형 처리 미흡
- **위치:** `api/app/db/sql_guard.py:129`
- **내용:** `\blimit\s+(\d+)`가 `LIMIT 0`(오해성 0건)·`LIMIT -5`·`LIMIT (10)`·`OFFSET`-only를 정상 인식 못 함. temp=0라 발생 가능성 낮고 대부분 fail-safe.
- **해소:** LIMIT 정규화/하한 검증 강화.
- 📅 **예약됨: `13-1-sql-guard-하이브리드-정비-g2-baseline`** (backlog).

### 16. 가이드 RAG 유사도 임계값(거리 컷오프) 없음
- **위치:** `api/app/graph/doc_rag_node.py:64-68`
- **내용:** 가이드 검색이 거리와 무관하게 항상 최근접 1건(`ORDER BY embedding <=> q LIMIT 1`) → 의미상 동떨어진 가이드도 "근거"로 첨부돼 오도 가능.
- **해소:** 코사인 거리 컷오프(`WHERE embedding <=> q < threshold`) 적용. (4.5 answer_node 소관으로 명시됨)
- 📅 **예약됨: `13-6-가이드-문서-content-활용-거리-컷오프`** (backlog).

### 17. Flutter **Riverpod 컨트롤러** 단위 테스트 부재 (Epic 7 이월)
- **위치:** `app/lib/features/**/` 의 Riverpod 컨트롤러
- **내용:** 전역 Supabase 의존 때문에 **컨트롤러 계층**은 단위 테스트를 못 쓰고 live 스모크로 갈음했다.
- ⚠️ **범위 정정 (2026-07-15 회고 — 실측)**: Epic 7 회고의 *"컨트롤러 단위 테스트 부재"* 라는 표현이 **"Flutter에 테스트가 없다"로 오독됐다.** 실제로는 `app/test/`에 **10개 파일 · 테스트 77개**가 있다(`listing_form_test` 17 · `listing_filters_test` 11 · `listing_model_test` 12 · `ai_search_test` 8 · `widget_test` 8 · `chat_model_test` 6 · `listing_error_test` 4 · `chat_dedupe_test` 4 · `listing_form_edit_test` 5 · `number_format_test` 2). 없는 건 **`ProviderContainer` 기반 컨트롤러 테스트뿐**이고, 순수 함수·모델·파싱·검증 로직은 커버돼 있다.
- **트리거:** `_bmad-output/project-context.md` 규칙 12가 이미 조건부로 규정 — *"컨트롤러 로직이 복잡해질 때"*. 즉 **신규 부채가 아니라 이미 관리 중인 조건부 항목**이다.
- **해소:** Supabase를 리포지토리로 감싸 fake 주입 → `ProviderContainer.test`로 폴링 상태 전이·필터 조합 검증.

### 32. 누수 부재 테스트가 `psycopg_pool`의 비공식 보장에 의존 (8.4 리뷰 이월)
- **위치:** `api/tests/test_readonly.py`
- **내용:** `max_size=1`이 순차 재사용을 강제하긴 하나, **"동일 물리 커넥션 재사용"은 라이브러리가 공식 보장하는 계약이 아니다.** 헬스체크 등으로 커넥션이 교체되면 테스트가 **잘못된 이유로 통과**하거나 flaky해진다.
- **해소:** 롤 누수를 커넥션 동일성이 아닌 방식으로 단언(예: `SET LOCAL` 스코프 자체를 검증).

### 33. DSN 포트(`:6543`) 전제가 주석에만 있고 코드로 검증되지 않음 (8.4 리뷰 이월)
- **위치:** `api/app/db/readonly.py` · `api/app/config.py`
- **내용:** `.env`가 실수로 `:5432`(세션 풀러)를 가리켜도 코드가 조용히 그대로 동작한다. `SET LOCAL`은 풀러 종류와 무관해 **롤 누수는 재발하지 않으나 의도한 성능 특성을 잃는다.** 우선순위 낮음.

### 34. anon 허용 테스트가 두 파일에 중복 — 약한 사본 포함 (8.5 리뷰 이월)
- **위치:** `api/tests/test_auth.py:367-377` · `api/tests/test_ai_search.py:339-348`
- **내용:** `test_search_without_token_allowed_anon`가 동명·동일 monkeypatch로 양쪽에 있고, `test_ai_search.py` 사본은 `assert r.json()["listings"] == []` **본문 검증이 빠진 약한 버전**이라 응답 계약이 퇴행해도 초록으로 통과한다.
- **해소:** *"인증 계약 테스트는 `test_auth.py` 소유"* 라는 **파일 경계 결정이 선행**돼야 함. (8.5가 만든 중복이 아니라 pre-existing 구조를 갱신한 것)

### 35. 고아 `auth.users`(profiles 없음) 시 시드 재실행 중단 (2-5 리뷰 이월)
- **위치:** `supabase/seed.sql:163-174`
- **내용:** 시드 계정이 `auth.users`엔 있으나 `profiles`가 없는 손상 상태에서 재실행하면 안전장치 `raise exception`이 전체 시드를 중단시킨다. **의도된 fail-loud**(조용한 실패보다 즉시 드러냄)지만 자가복구 경로는 없다.
- **해소:** 시드 자동화 강화 시 `profiles` 부재 시 직접 삽입하는 self-heal 경로 검토.

### 36. FocusTrap — 언마운트·숨김된 트리거로 복귀 시 조용히 no-op (8.2 리뷰 이월)
- **위치:** `web/src/components/ui/FocusTrap.tsx:243-246`
- **내용:** 트랩이 닫힐 때 `triggerRef.current`로 포커스를 복귀시키는데, 그 요소가 그 사이 DOM에서 제거·숨겨졌으면 `.focus()`가 **조용히 아무 일도 안 한다**(크래시 없음, 포커스가 `<body>`로 남음).
- **트리거:** 트리거가 리스트 아이템처럼 삭제될 수 있는 맥락에서 소비될 때. **해소:** 폴백(컨테이너·상위 랜드마크로 이동).

### 37. FocusTrap — `open=false`일 때 `children` 전체 언마운트, 내부 상태 소실 (8.2 리뷰 이월)
- **위치:** `web/src/components/ui/FocusTrap.tsx:249`
- **내용:** 닫히면 `null`을 반환해 자식을 완전히 언마운트한다. **폼 입력값·스크롤 위치가 매번 사라지는 동작이 문서화돼 있지 않다.**
- **트리거:** 실제 모달/바텀시트를 붙이는 Epic 11. **해소:** 의도와 맞는지 확인하고, 상태 보존이 필요하면 CSS로 숨기는 방식으로.

### 38. ErrorState — `tone="danger"`가 텍스트 색만 바꾸고 버튼은 톤 무관 동일 (8.2 리뷰 이월)
- **위치:** `web/src/components/ui/ErrorState.tsx:167-179`
- **내용:** cosmetic. 파괴적/위험 에러와 일반 에러가 **버튼 상으로는 시각 구분되지 않는다.** `tone="danger"`를 쓰는 소비 화면이 생기면 버튼도 톤 분기할지 검토.

### 39. 단일 `error` useState를 `handleComplete`·`handleDelete`가 공유 (2-4 리뷰 이월)
- **위치:** `web/src/app/(user)/sell/ListingActions.tsx`
- **내용:** cosmetic. 각 핸들러 시작 시 `setError(null)`로 초기화하지만 성공 경로엔 명시 초기화가 없다. 한 행에 버튼이 모여 있어 실사용 혼선은 작음. 핸들러가 더 늘면 분리 검토.

### 40. Pretendard 폰트가 CDN `<link>` — 렌더 블로킹 + FOUT/CLS (8.1 리뷰 이월, **결정됨·스토리 미배정**)
- **위치:** `web/src/app/layout.tsx`
- **내용:** 뿌리가 같은 2건 — ① jsDelivr CDN stylesheet를 `<head>`에서 로드해 **느린(실패 아님) CDN이 first paint를 지연**시킬 수 있음(폴백 스택은 명확한 실패만 구제, latency는 못 구제). ② 수동 `<link>`가 next/font의 자동 `size-adjust`/`ascent-override` fallback을 잃어 **스왑 시 텍스트 리플로우(CLS)**.
- **✅ 방향 확정(사용자 결정 2026-07-13):** `next/font/local`로 **self-host 전환** → 한 번에 종결. Pretendard는 Google Fonts에 없어 `next/font/google`은 불가하나 `local`은 가능.
- **구현 노트:** Pretendard **Variable** `.woff2`를 `web/` 안에 배치(폰트 바이너리가 저장소에 추가됨) → `next/font/local`로 로드 → `globals.css`의 `--font-sans` 우선순위 연결 → `layout.tsx`의 수동 `<link>`+`preconnect` 제거. ⚠️ **Next 16 관례 다름** — 코드 전 `node_modules/next/dist/docs/`의 next/font 가이드 선독(`web/AGENTS.md` 원칙). 검증: computed `font-family`=Pretendard · FOUT/CLS 관찰 · `next build` · 라이트/다크 E2E.
- **⚠️ 상태:** **작업으로 승격 확정됐으나 스토리가 배정되지 않았다.** 데모 실배포/실사용 전환 시점. 방치하면 이 항목이 "결정만 되고 아무도 안 하는" 자리에 남는다.

### 41. `deployment-runbook.md` §8 사각지대 목록에 `paths:` 필터 누락 (문서 부채)
- **위치:** `docs/deployment-runbook.md` §8
- **내용:** §8은 스스로 *"이 목록의 정직함이 곧 게이트 신뢰의 근거이므로, 빠뜨린 항목은 단순 누락보다 비싸다"*(:116)라고 선언해 놓고, **"이 CI는 마이그·스크립트를 안 건드리는 push엔 존재하지도 않는다"**(#29)를 빠뜨렸다. #22(`--single-transaction`이 마이그 작성 방식을 몰래 제약)도 미기재.
- **해소:** §8에 두 항목 추가. **#22·#29와 함께 처리.**

### 42. Epic 8 회고 산출물 `개발-가이드라인-MVP에서-증분까지.md`가 레포 밖 (문서 부채)
- **위치:** `C:\Users\dnjsg\workspace\docs\개발-가이드라인-MVP에서-증분까지.md` (이 git 저장소 **바깥**)
- **내용:** Epic 8 회고 A4 산출물이고 `epic-8-retro-2026-07-15.md:236`이 인용하는데, **git 추적 밖이라 버전관리·이관에서 빠진다.** 회고가 스스로 결함 클래스로 꼽은 *"존재한 적 없는 파일 인용"* 의 변종(존재하지만 추적 안 됨).
- **판단 필요:** 이 문서는 **이 프로젝트가 아니라 다음 프로젝트용**(범용 교훈)이라 레포 밖이 의도일 수 있다. 그렇다면 회고의 인용을 "레포 밖 문서"로 명시하는 것으로 족하다.

---

## 📅 스토리로 예약됨 (부채 아님 — 계획된 작업)

> 대장에 열려 있으나 **이미 Epic 9~16 스토리가 소유**하는 항목. 여기 있는 건 "빚"이 아니라 "일정"이다.
> 위 🟡·🟢 섹션에도 📅 표기로 예약된 항목이 있다(#6→12-1 · #7→12-4 · #11→10-3 · #15→13-1 · #16→13-6).

- **`RowSkeleton`(행 조합) 부재** [`web/src/components/ui/Skeleton.tsx`] — 8.2 AC3 원문은 "스켈레톤 로딩(카드/행 조합)"을 요구하나 `CardSkeleton`(카드형)만 있다. **이월 사유(사용자): 소비처 생길 때 화면 기준으로** — 지금 임의로 만들면 재작업 위험. → **Epic 12(채팅 목록)·Epic 15(관리자 테이블)** 에서 그 화면 기준으로 추가.
- **모달·바텀시트 `role="dialog"` 부착 규약** [`web/src/components/ui/FocusTrap.tsx`] — **소비 스토리 규약(사용자 확정):** 모달·바텀시트·로그인 게이트 소비 스토리는 FocusTrap 컨테이너에 `role="dialog"` + `aria-modal="true"` + `aria-labelledby`를 **반드시** 부착한다(UX-DR22 접근성 바닥). 드롭다운·리스트박스는 `menu`/`listbox` role. 8.2 코드리뷰에서 FocusTrap이 `...rest`를 컨테이너 div로 전달하도록 patch돼 부착이 가능해졌다. → **Epic 11**(`11-2-상단-내비-재구성` 드롭다운·필터 바텀시트) 등 소비 에픽에서 적용.

---

## ⚪ 의도적 보류 (부채 아님 — 제품 결정, 참고용)

> party-mode(2026-06-24 · 2026-07-13)로 확정. 되살릴 필요 없으나 재검토 시 근거 참조.

- **관리자 대시보드 (Cut/보류):** UI는 web 전용 표현. 집계 쿼리(데이터 계약)만 모바일 관리자 확정 시 별도. *(2026-07-15 실측: Epic 15는 `15-1-관리자-6화면-디자인-리스킨`·`15-2-관리자-반응형`·`15-3-회원관리-역할통합-반영`으로 **대시보드 스토리가 없다** → Cut 유효.)*
- **찜 기반 "인기 매물" 신호 (보류, 2026-07-13 party-mode):** 랜딩 "인기 매물"을 조회수 단독이 아니라 **찜 수 반영 복합 신호**(`score = view_count + w·wishlist_count`)로. **왜 보류:** `favorite_count` 컬럼을 지금 만드는 건 YAGNI + 시드에 찜 데이터가 없어 전부 0(콜드스타트 함정). **이미 된 대비:** `wishlists(user_id, listing_id)`가 증분(FR55·마이그 0015)에 생기므로 찜 수는 `COUNT(*) GROUP BY listing_id`로 **언제든 파생 가능** — 스키마 재작업 불필요. **이어받을 때:** (a) 인덱스 `wishlists(listing_id)` 1줄 additive (b) 집계 쿼리 권장(트리거 카운터는 정합성 부채 — 원천이 있으니 COUNT) (c) **임계값 게이팅**(5명↑만 노출, "0명 찜" 낙인 방지) + 카드 하단 중립 회색 메타(초록/앰버 안 씀) (d) 봇 방어(view dedup) 없으면 조회수 오염 → 찜 가중치 크게.
- **문서 기반 차량 상태 관리 (보류, 2026-07-13 party-mode):** 성능점검표·보험처리이력을 **자체 간소 양식(MD/PDF) 문서 기반**으로 관리 + 등록 시 상태 컬럼 자동 반영 + 다운로드. **확정된 설계(보류하되 박제):** **OCR·임베딩 없음**(자체 구조화 양식이라 파싱 불필요) · **신뢰 모델은 자기신고+면책 유지**(등급 격상 안 함 — 업계도 성능표·보험이력 오류로 플랫폼 무보증이 표준, 문서는 **"참고자료"로만**). **스키마(그때):** `listing_documents(listing_id fk ON DELETE CASCADE, doc_type enum('inspection','insurance'), storage_path, created_at)` + `usage_type`(자가용/영업용/렌트/리스). **이미 된 대비:** 증분 아키텍처 ADR-IMG-01이 서명URL 헬퍼·업로드 RLS·버킷 경로를 **"이미지 전용"이 아니라 아티팩트 범용**으로 짓도록 지침화 → 배관 재작업 불필요. **⚠️ 이어받기 전 확인 권장(미검증):** 개인 직거래(C2C)의 성능점검기록부 **법적 의무 범위** · 각 사 인기 랭킹 공식.

> **⚠️ 2026-07-15 정정 — Cut이 뒤집힌 2건은 여기서 뺐다.** 대장이 *"만장일치 Cut, 되살릴 필요 없음"* 이라 적고 있었으나 증분이 되살렸다:
> - **데스크톱 반응형** — `8-2-ui-프리미티브-반응형-상태-접근성`이 **done**이고 `11-5-반응형-뷰포트-e2e-감사-sm-b`·`15-2-관리자-반응형`이 backlog. 게다가 `project-context.md` 규칙 13(D5 반응형 무결성)이 **"전 UI governing·관리자 예외 없음"** 으로 격상돼 있다. **Cut이 아니다** → 📅 예약됨.
> - **"홈이 탐색을 직접 품기"** — `11-3-ai-히어로-랜딩-히어로-차종-칩`·`11-4-인기-최신-매물-그리드`가 홈을 재설계한다. *(단, "홈이 필터·URL을 직접 소유"하는 전체판인지는 Epic 11 스토리 스펙에서 확인 필요 — 히어로+그리드가 곧 필터 소유는 아니다.)*

---

## 부록: 해소된 부채 (참고)

- **[구 🔴 #1] 시드 계정 평문 비밀번호 커밋** — **2026-07-11 세션변수 주입으로 해소.** `supabase/seed.sql`(및 생성기 `_bmad-output/.../seed-expansion-block.sql`·`gen_seed_expansion_sql.py`)에서 데모 시드 계정의 평문 비밀번호를 제거하고, 실행 시 PostgreSQL 세션 변수 `app.seed_password`로 주입(`current_setting`)하도록 변경. 미설정 시 시드 상단 게이팅 블록이 예외로 즉시 중단(fail-closed). 데모/E2E 로그인 비번은 저장소 미추적 파일 `supabase/.env.seed`(템플릿 `supabase/seed-secret.example`)로 이관. 로그인 문서(`docs/e2e-test-cases.md`·`e2e-checklist.md`)도 비번 칸을 파일 참조로 교체. 라이브 데모 DB는 멱등 시드라 기존 계정 비번 불변(로테이션 안 함) → 배포된 web·Flutter 데모 계속 작동. (과거 BMAD 스토리 아티팩트의 평문 언급은 불변 기록이라 미변경.)
- **[구 🔴 #3] 앱 픽셀 E2E 미검증** — **2026-07-11 실폰 무선 디버깅으로 해소.** Flutter 앱 6개 화면 흐름(구매자 탐색·상세 / 판매자 등록·관리 / 채팅 / AI검색)을 실기기에서 직접 눌러 렌더·동작 확인. Epic 7 개발 당시 검증 PC(RAM 6GB) 한계로 미수행했던 것을 실기기 검증으로 마감.
- **[구 🔴 #4] AI 검색 라이브 호출 0회** — **2026-07-11 실폰 검증으로 해소.** 앱에서 AI 매물검색을 실제 호출 → 매물 카드 정상 노출 확인(`API_BASE_URL` 주입 + 라이브 응답 실증). 정적 계약 갈음이 실제 동작으로 승격됨.
- **Supabase 클라이언트 env 누락 가드** — Story 1.4에서 `getSupabaseEnv()`로 일원화 해소.
- **판매자 본인 매물 문의 차단(buyer=seller)** — Epic 5에서 3중 안전장치 실증, 검토 안건에서 제외. ① UI 숨김 [`listings/[id]/page.tsx:153`] ② BEFORE INSERT 트리거 [`0003c_chat_room_integrity.sql` `enforce_chat_room_seller` — 클라가 보낸 `seller_id`를 매물 실소유자로 강제 덮어씀] ③ CHECK 제약 [`0003_chat.sql:33` `chat_rooms_buyer_ne_seller`]. **실증**: UI 우회 직접 INSERT 시 errcode 23514로 거부(2026-06-24).
- **관리자 상세 '돌아가기'·역할별 정렬 통일** — Epic 7 직전 즉시 완료.
- **메인화면 개편 ①본인정보·②매물탐색 미리보기판·③AI채팅 플로팅 진입** — 2026-06-24 party-mode 2R 결정 → `49b0f05`·`681b702` 완료 + 운영 배포 검증.
- **역할별 내비/정보구조 규칙 문서** — Winston 산출물 `fcfea8a` → `_bmad-output/planning-artifacts/nav-ia-rules.md`.

### 2026-07-15 대장 일원화 시 **실측으로 해소 확인**된 이월 3건 (4-1 코드리뷰)

`deferred-work.md`에 열린 채 남아 있었으나 후속 스토리가 이미 닫았음을 코드로 확인했다 — 열린 채로 옮겼으면 대장 오염이었다:

- **`context` 필드 크기·스키마 제약 없음(DoS 여지)** → **4.6이 해소.** `api/app/schemas/ai.py:47` → `context: list[ConversationTurn] | None = Field(default=None, max_length=12)` + 원소 타입 강제 + `ConversationTurn.content` `max_length=2000`. 주석이 명시: *"원소 타입·최대 턴 수(12)를 강제해 4.5까지 무제한이던 DoS 여지를 닫는다."*
- **CORS 기본 origin이 preview/https 미포함** → **4.7이 해소.** `api/app/main.py:48-52` → `cors_origins`(정확 매칭 목록) + `cors_origin_regex`(preview처럼 매번 바뀌는 오리진) 2단 구성.
- **`0006 ALTER DEFAULT PRIVILEGES`가 동일 소유자 테이블만 적용 → `guide_documents`에 명시 GRANT 필요** → **4.2가 해소.** `supabase/migrations/0004_guide_documents.sql:58` → `grant select on public.guide_documents to ai_readonly;` + `:61` 가시성 정책. 파일 주석이 *"GRANT만으론 행 안 보임 — 정책 필수"* 로 함정까지 기록.

---

## 다음 액션

### Epic 9 착수 전 (읽고 시작할 것)
1. **#18 테이블 GRANT — 판정 (b)다.** Epic 9의 첫 마이그가 이 축을 건드린다. **이 항목을 근거로 GRANT를 자율 추가하지 말 것**(§9.3 3조건 중 ①③ 위반). 필요하면 사용자 승인부터.
2. **#27 시드 멱등 delete** — Epic 9 `listing_images`·Epic 10 `wishlists`가 `listings`의 첫 자식 테이블이다. 시드 재실행 전략을 먼저 판단.

### 상시
3. **#29 CI 구멍** — web·api·app 테스트가 CI에서 한 번도 안 돈다. 비용 낮고(이미 있는 테스트를 돌리기만) 효과 큼. B9 정면 위반이라 우선순위 높게 볼 만함.
4. **#28 e2e-checklist 오기재** — E2E 크로스체크 **착수 전 필수**. 안 고치면 정상 동작을 실패로 판정해 멀쩡한 코드를 고치는 회귀를 유발한다.

### 제출·운영 전
5. **🔴 #2 안드로이드 서명** — 남은 🔴 1건.
6. **E2E 크로스체크 테스트** — 웹(https://bmad-encar-demo.vercel.app) ↔ Flutter(실폰) 동일 테스트셋으로 **불일치(divergence) 적발**. 실폰 단발 검증(구 #3·#4)은 끝났으나 웹↔모바일 체계적 대조는 성격이 다르므로 별도 잔존. **선행: #28.**
7. **#40 Pretendard self-host** — 결정만 되고 스토리가 없다. 데모 실배포 전환 시점에 배정할 것.

### Epic 13 착수 전
8. **#22~24 게이트 구조적 대가 3종** — 특히 **#22**: 무중단 HNSW 인덱스(`create index concurrently`)를 얹는 순간 게이트만 red가 난다. 착수 전에 읽을 것.
