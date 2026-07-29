# Deferred Work — 열린 일 장부 (open-items ledger)

> ## 여기가 유일한 열린 일 장부다. "지금 뭐가 열려 있나"는 이 파일 하나로 답한다.
>
> 미룬 항목·이월·코드리뷰 defer·회고 액션은 **전부 여기에** `### DW-<번호>`로 등재한다
> (CLAUDE.md B8). 이 파일은 **append-only** — 기존 항목을 지우거나 고쳐 쓰지 않는다.
> 끝나면 지우지 말고 `status: done <날짜>` + `resolution:`으로 닫는다.
>
> | 찾는 것 | 가야 할 곳 |
> |---|---|
> | **지금 뭐가 열려 있나?** | **이 파일** |
> | 지켜야 하는 계약은? | `docs/conventions.md`(크로스-파트) · `_bmad-output/project-context.md`(구현 규칙) |
> | 왜 그렇게 정했나? | `docs/decisions-archive.md` · 각 에픽 회고 |
> | 2026-07-29 이전에 닫힌 부채는? | `docs/tech-debt.md` (전방 동결 — 닫힌 항목 경위 + 이관 색인) |
>
> ### 항목 형식
> 정본은 `.claude/skills/bmad-loop-sweep/deferred-work-format.md`가 소유한다.
> ```
> ### DW-<번호>: <한 줄 제목>
>
> origin: <워크플로 + 산출물 + 날짜>
> location: <file:line 또는 컴포넌트, 없으면 n/a>
> severity: <critical | high | medium | low>
> reason: <왜 지금 안 하고 미뤘나>
> trigger: <언제 다시 볼지 — 조건으로 쓴다>
> status: open
> ```
> `trigger:`는 표준 밖 필드지만 **반드시 적는다**(CLAUDE.md B8: "'이월'만 적으면 다음 작업이
> 장부가 아니라 상위 문서를 보고 만들어져 조용히 또 밀린다"). 엔진이 이 필드를 무시할 뿐
> 파싱을 깨지 않는 것은 2026-07-29에 `sweep --dry-run`으로 실측 확인했다.
>
> ### 번호 규칙
> - `DW-1`~`DW-9` — bmad-loop 엔진이 리뷰 예산 소진 시 직접 append 한 것
> - `DW-302`~`DW-534` — 2026-07-29 `docs/tech-debt.md`에서 이관(`구 #N` → `DW-(N+300)`).
>   제목의 `[구 #N]`은 **지우지 마라** — 리포 곳곳의 옛 참조 600여 곳이 이걸로 찾아간다.
> - 새 항목은 파일에서 가장 큰 번호 다음부터.

---

## 이 파일의 유래 (2026-07-29 장부 통합)

2026-07-15에 이 파일은 "동결"되고 `docs/tech-debt.md`가 유일한 장부가 됐었다. 그 결정은
근거가 있었지만(장부가 2개일 때 #18 테이블 GRANT가 정반대 판정으로 1일간 공존한 사고),
**도구를 이길 수 없었다**:

> BMAD·bmad-loop 상류가 `deferred-work.md`를 유일한 ledger로 규정한다. 로컬 스킬 전체와
> 양쪽 상류 README에서 `tech-debt`는 **0건**이다.
>
> 방어 1층(`_bmad/custom/*.toml` 프롬프트 주입)은 엔진이 프롬프트를 안 읽어서 안 닿았다.
> 방어 2층(PreToolUse 훅)은 엔진이 Claude 세션이 아니라 파이썬 프로세스라 **호출조차 되지
> 않았다.** 그 결과 `DW-1`~`DW-9`가 "⛔ 여기 쓰지 마라"라고 적힌 파일에 그대로 쌓였다.
>
> 그리고 통합 직전 실측에서 `bmad-loop sweep --dry-run`이 이 파일의 경위 산문을
> **"옛 형식으로 적힌 열린 일 61건"으로 오독**했다 — 사람이 sweep을 치는 순간 파일 전체가
> 재작성될 상태였다.

그래서 방향을 뒤집었다. 경위 산문은 `docs/decisions-archive.md`로 분리했고,
`docs/tech-debt.md`의 열린 항목은 전부 여기로 옮겼다.

---

### DW-1: Follow-up review still recommended for 11-0-pretendard-self-host-전환 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-0-pretendard-self-host-전환.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260727-203454-d410; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-2: Follow-up review still recommended for 11-1-view-count-스키마-increment-rpc-하드닝 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-1-view-count-스키마-increment-rpc-하드닝.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260727-223439-2318; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-3: Follow-up review still recommended for 11-2-상단-내비-재구성 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-2-상단-내비-재구성.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260727-223439-2318; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-4: Follow-up review still recommended for 11-5-반응형-뷰포트-e2e-감사-sm-b after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-5-반응형-뷰포트-e2e-감사-sm-b.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260728-105733-33e0; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-5: Follow-up review still recommended for 12-1-멱등키-마이그레이션 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-1-멱등키-마이그레이션.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260728-203648-2fc6; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-6: Follow-up review still recommended for 12-3-실시간-송수신-전환-폴링-제거 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-3-실시간-송수신-전환-폴링-제거.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-7: Follow-up review still recommended for 12-4-재연결-배너-갭-보정 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-4-재연결-배너-갭-보정.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-8: Follow-up review still recommended for 12-5-안읽음-배지-방-목록-정렬 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-5-안읽음-배지-방-목록-정렬.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-9: Follow-up review still recommended for 12-6-실시간-채팅-검증-sm-e after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-6-실시간-채팅-검증-sm-e.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-302: [구 #2] 안드로이드 릴리스 서명 미설정

origin: 장부 통합 이관(구 docs/tech-debt.md #2) — 원출처: (표기 없음)
location: `app/android/app/build.gradle.kts:30` (코드 내 유일한 TODO)
severity: critical
reason: 앱 스토어 배포가 현재 계획에 없어(사용자 확인 2026-07-16) 트리거가 없다 — 배포를 실제로 하기로 정하는 순간 우선순위가 되살아난다.
status: open

- **위치:** `app/android/app/build.gradle.kts:30` (코드 내 유일한 TODO)
- **내용:** release 빌드가 아직 debug 서명 설정을 씀. `// TODO: Add your own signing config for the release build.`
- **왜 위험:** 정식 스토어 배포·서명된 APK 산출 불가.
- **해소:** 실제 배포 시 keystore 생성 + `signingConfigs` 설정. (Epic 7 회고 이월, app은 현재 수동 배포 전이라 즉시 영향은 없음)
- 📌 **앱 스토어 배포는 계획에 없다 (사용자 확인 2026-07-16).** 트리거가 없으므로 실질 우선순위는 🔴가 아니다 — 배포를 실제로 하기로 정하는 순간 되살아난다. 이 항목이 🔴로 남아 있는 건 "정식 배포 시 반드시 필요"라는 사실 자체는 변하지 않아서다.

> ℹ️ 구 #3(앱 픽셀 E2E 미검증)·#4(AI 라이브 호출 0회)는 **2026-07-11 실폰 무선 디버깅 검증으로 해소** → 하단 `부록: 해소된 부채` 참조.

---

### DW-305: [구 #5] AI API DB 커넥션 풀링·타임아웃·async 블로킹 부재

origin: 장부 통합 이관(구 docs/tech-debt.md #5) — 원출처: (표기 없음)
location: `api/app/db/readonly.py`, `api/app/auth.py`
severity: medium
reason: `readonly_connection()`이 호출마다 새 연결을 열고 풀이 없어 동시 부하 시 커넥션 풀러가 고갈될 수 있었고, timeout 미설정과 동기 호출의 이벤트 루프 블로킹도 함께 있었다.
trigger: AI 검색 동시 사용자가 늘어날 때.
status: done 2026-07-29
resolution: Story 8.4가 해소 — `api/app/db/readonly.py`에 psycopg_pool.ConnectionPool 실재(2026-07-29 실측). 풀링·타임아웃·async 블로킹 3축 전부 처리됨

- **위치:** `api/app/db/readonly.py`, `api/app/auth.py`
- **내용:** `readonly_connection()`이 호출마다 새 psycopg 연결을 열고 풀이 없음 → 동시 부하 시 Supabase Session 풀러(:5432, 낮은 연결한도) 고갈 가능. `connect_timeout` 미설정이라 풀러가 멈추면 무한 대기. 동기 호출이 `async def` 안에서 실행돼 이벤트 루프 블록.
- **트리거:** AI 검색 동시 사용자가 늘어날 때.
- **해소:** 실제 DB 경로가 붙은 지금, 커넥션 풀 + `connect_timeout` + 스레드풀/async 드라이버 도입. (원래 4.3에서 도입 예정이었던 항목)
- ✅ **해소 완료 (Story 8.4, `e1057df`)** — `api/app/db/readonly.py`에 `psycopg_pool.ConnectionPool` 도입(`max_size=8`), `SET LOCAL ROLE`로 트랜잭션 스코프 롤 격리, `asyncio.to_thread`로 논블로킹화, `PoolTimeout` → 503 한국어 안내. 8.5 코드리뷰가 죽은 풀 영구 캐시·liveness·종료 훅까지 보강. *(✎ 2026-07-15 회고: 이 항목은 8.4가 해소했는데 대장이 🟡로 남아 있었다 — drift 3건 중 하나.)*

### DW-306: [구 #6] 채팅 커밋 후 응답 유실 시 중복 전송 (멱등키 부재)

origin: 장부 통합 이관(구 docs/tech-debt.md #6) — 원출처: (표기 없음)
location: `web/.../chat/[roomId]/ChatRoomMessages.tsx` (handleSubmit catch)
severity: low
reason: 멱등키 도입은 `12-1-멱등키-마이그레이션`으로 backlog에 이미 예약된 계획된 작업이라 부채로 별도 처리하지 않는다.
trigger: 불안정 네트워크에서 전송 중 끊김.
status: open

- **위치:** `web/.../chat/[roomId]/ChatRoomMessages.tsx` (handleSubmit catch)
- **내용:** INSERT가 DB엔 성공했으나 응답이 네트워크에서 끊기면 catch가 입력을 복원 → 사용자 재전송 → 서로 다른 id의 중복 메시지 영속(id 기준 dedupe로 못 막음).
- **트리거:** 불안정 네트워크에서 전송 중 끊김.
- **해소:** 멱등키(클라 생성 uuid를 PK로) 도입.
- 📅 **예약됨: `12-1-멱등키-마이그레이션`** (backlog) — 부채가 아니라 계획된 작업이다.

### DW-307: [구 #7] 채팅 폴링 영구 실패 시 무알림

origin: 장부 통합 이관(구 docs/tech-debt.md #7) — 원출처: (표기 없음)
location: 동상 (폴링 effect)
severity: low
reason: 재연결 배너 보정은 `12-4-재연결-배너-갭-보정`으로 backlog 예약돼 있고, Epic 12가 폴링을 Realtime으로 대체하면 이 항목의 형태 자체가 바뀐다.
trigger: 장시간 방치 후 세션 만료, 관리자의 방 삭제.
status: open

- **위치:** 동상 (폴링 effect)
- **내용:** 첫 로드 실패는 한국어 에러로 표시(loud)하지만, 세션 만료·방 삭제로 폴링이 매 주기 영구 실패하면 아무 표시 없이 대화가 멈춘 것처럼 보임(silent). loud/silent 비대칭.
- **트리거:** 장시간 방치 후 세션 만료, 관리자의 방 삭제.
- **해소:** N회 연속 실패 후 비차단 배너(재연결/오프라인 표시).
- 📅 **예약됨: `12-4-재연결-배너-갭-보정`** (backlog). Epic 12가 폴링을 Realtime으로 걷어내므로 이 항목의 형태 자체가 바뀐다.

### DW-308: [구 #8] 채팅 본문 최대 길이 가드 없음

origin: 장부 통합 이관(구 docs/tech-debt.md #8) — 원출처: (표기 없음)
location: `web/src/lib/messages.ts` (sendMessage / 입력창)
severity: medium
reason: `body`가 무제한 `text` 컬럼이고 클라이언트는 `trim()`만 하므로 초대용량 붙여넣기가 그대로 INSERT돼 행·폴링 페이로드가 비대해질 수 있었다.
trigger: 대용량 텍스트 붙여넣기.
status: done 2026-07-29
resolution: 0010_chat_message_length.sql + web MESSAGE_MAX_LENGTH=2000 실재 확인(2026-07-29 실측)

- **위치:** `web/src/lib/messages.ts` (sendMessage / 입력창)
- **내용:** `body`가 `text`(무제한), 클라는 `trim()`만. 초대용량 붙여넣기가 그대로 INSERT → 행·폴링 페이로드 비대화.
- **트리거:** 대용량 텍스트 붙여넣기.
- **해소:** 입력창 `maxLength` + 서버측 길이 컷.
- ✅ **해소 완료 (2026-07-11, `b720370`)** — 3층 강제: DB CHECK(`0010_chat_message_length.sql`, `char_length(body) <= 2000`) + web 입력창 `maxLength` + `sendMessage` 길이 가드. 값은 `web/src/lib/constants.ts`의 `CHAT.MESSAGE_MAX_LENGTH`가 미러링. 계약은 `docs/conventions.md` §7. *(✎ 2026-07-15 회고: drift 3건 중 하나.)*

### DW-310: [구 #10] open-redirect 검증 규약 미정

origin: 장부 통합 이관(구 docs/tech-debt.md #10) — 원출처: (표기 없음)
location: `web/src/proxy.ts`, `web/.../login/page.tsx`
severity: medium
reason: proxy가 붙이는 `redirectedFrom` 값을 로그인 화면이 검증 없이 사용하면 오픈 리다이렉트로 이어질 수 있었다(당시엔 로그인 화면이 이 값을 읽지 않아 무해).
trigger: "로그인 후 원래 위치 복귀" 기능 도입 시.
status: done 2026-07-29
resolution: Story 8.5가 해소 — web/src/lib/auth/redirect.ts의 resolveSafeRedirect 실재, 규칙은 docs/conventions.md §8에 정본화됨

- **위치:** `web/src/proxy.ts`, `web/.../login/page.tsx`
- **내용:** proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만 로그인 화면은 안 읽고 항상 `/`로 이동(현재 무해).
- **트리거:** "로그인 후 원래 위치 복귀" 기능 도입 시.
- **해소:** `redirectedFrom` 값이 `/`로 시작하는 상대경로인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트 방지.
- ✅ **해소 완료 (Story 8.5, `5bc6463`)** — 트리거가 실제로 발동했다(비로그인 열람을 열며 "로그인 후 복귀"가 필요해짐). `web/src/lib/auth/redirect.ts`의 `resolveSafeRedirect`가 `//`·`http(s):`·역슬래시를 차단하고, 8.5 코드리뷰가 `/login` 자기참조 데드엔드까지 추가 차단. **web 최초의 단위 테스트**(`redirect.test.ts` + Vitest)로 방어 케이스 고정.
- 📌 **이 항목의 교훈(회고 2026-07-15)**: Epic 1·2·3·4 회고에 **네 번 연속 "이연"** 으로 등장했고 매번 *"현재 미사용이라 무해"* 로 넘겼다. **그 판단은 네 번 다 옳았다** — 실제로 필요해진 8.5에서 고쳤다. **미루는 판단은 틀린 게 아니다. 고친 뒤 대장을 안 닫은 것만 틀렸다.**

### DW-311: [구 #11] options(text[]) 쉼표 포함 값 라운드트립 손실

origin: 장부 통합 이관(구 docs/tech-debt.md #11) — 원출처: (표기 없음)
location: `web/.../sell/SellForm.tsx`
severity: medium
reason: 웹 SellForm의 쉼표 join/split은 옵션 값에 쉼표가 섞이면 라운드트립이 깨졌다. 웹은 줄바꿈 구분으로 고쳤으나 app `listing_form.dart`는 이 스토리 범위 밖이라 대장 #113(Epic 16)으로 트리거를 이관했다.
trigger: 시드/가이드/임베딩에서 쉼표 포함 옵션 도입 시.
status: open

- **위치:** `web/.../sell/SellForm.tsx`
- **내용:** 수정 폼이 options를 쉼표로 join/split. 폼 밖(시드·API)에서 한 배열원소에 쉼표를 넣으면 첫 수정 저장 시 둘로 쪼개짐(현재 폼 입력만으론 발생 안 함).
- **트리거:** 시드/가이드/임베딩에서 쉼표 포함 옵션 도입 시.
- **해소:** 입력 구분자 변경(줄바꿈) 또는 칩(chip) UI.
- ✅ **해소 완료 (Story 10.3, web 한정)** — `SellForm.tsx`의 옵션 입력을 쉼표 join/split에서 줄바꿈
  구분(`web/src/lib/options.ts`의 `parseOptionsInput`/`serializeOptions`, 순수함수)으로 바꿨다.
  #11 재현 케이스(`'a, b\nc'` → `['a, b', 'c']`, 쉼표 든 원소 보존)를 `options.test.ts`가
  라운드트립으로 못박는다 — **red/green 실측**: `parseOptionsInput`을 쉼표 split로 임시 되돌리자
  라운드트립 3건 red(나머지 14/18은 그대로 green), 줄바꿈으로 원복하자 18/18 green.
  app `listing_form.dart`는 이 스토리 범위 밖(대장 #113로 Epic 16 트리거 이관, B8 "미룬 것도
  적는다" — 웹만 닫혔다고 대장이 조용히 닫히면 안 된다).

### DW-312: [구 #12] `OwnListing.status` 타입이 `string` (union 미사용)

origin: 장부 통합 이관(구 docs/tech-debt.md #12) — 원출처: (표기 없음)
location: `web/src/app/(user)/sell/page.tsx:21`
severity: medium
reason: cosmetic 이슈로, 다른 select 타입을 정리할 때 함께 union으로 좁히면 되는 낮은 우선순위 항목이다.
status: open

- **위치:** `web/src/app/(user)/sell/page.tsx:21`
- **내용:** cosmetic. `LISTING_STATUS.ON_SALE` 비교는 정상이나 union 타입이면 오타·미정의 status 비교를 컴파일타임에 잡음.
- **해소:** 다른 select 타입 정리 시 union으로 좁힘.

### DW-318: [구 #18] 테이블 GRANT가 마이그에 없고 Supabase 플랫폼 기본에 의존

origin: 장부 통합 이관(구 docs/tech-debt.md #18) — 원출처: (표기 없음)
location: 마이그레이션 전체(`0011_listings_anon_select.sql`의 `anon`+`listings`만 예외 — 명시 REVOKE/GRANT로 이 의존을 끊었음).
severity: medium
reason: Supabase 플랫폼을 쓰는 것이 사용자가 확정한 전제이고 납품 계획이 없어(재해 복구 시에도 새 Supabase 프로젝트가 같은 기본 GRANT를 자동으로 준다) 오늘은 무해하다.
trigger: 자체 호스팅·타 클라우드 이관·"맨 Postgres로도 선다"는 납품 요구가 생기는 순간.
status: open

- **위치:** 마이그레이션 전체(`0011_listings_anon_select.sql`의 `anon`+`listings`만 예외 — 명시 REVOKE/GRANT로 이 의존을 끊었음).
- **내용:** `grant select on <table> to authenticated`가 어느 마이그레이션에도 없다(profiles·chat_rooms·chat_messages 포함). `authenticated` 데이터 경로 전체가 Supabase 플랫폼이 기본으로 발급하는 GRANT(`pg_default_acl`)에 암묵 의존한다. 마이그레이션 게이트(Story 8.6)의 프렐류드가 이 기본 GRANT를 실측 재현해 fresh DB에서도 통과하지만, 그건 **Supabase 플랫폼 위에서만** 참이다.
- **오늘 무해한 이유:** Supabase 전제(사용자 확정, 납품 계획 없음)이고, 재해 복구 시에도 새 Supabase 프로젝트가 같은 기본 GRANT를 자동으로 준다.
- **트리거(언제 문제되나):** 자체 호스팅·타 클라우드 이관·"맨 Postgres로도 선다"는 납품 요구가 생기는 순간.
- **8.5가 우연히 발견한 사실:** anon+listings에 대해서만 이 의존을 끊었다 — **체계적으로 찾은 게 아니라 다른 일(FR58) 하다 우연히 걸린 것**이다. 나머지(authenticated 전 경로)가 얼마나 되는지 아무도 세어본 적 없다.
- **해소:** 각 테이블 마이그에 명시 `grant select ... to authenticated`를 추가한 뒤, 프렐류드(`scripts/migration-check-prelude.sql`)의 `alter default privileges` 한 줄을 제거한다. 비용 ≈ 테이블당 1~2줄.
- **⚠️ 착수 시 판정: (a′) — dev 자율 + 실측 증거 첨부** (`docs/conventions.md` §9.3, 2026-07-16 사용자 결정으로 신설).
  - **승인 대기 없이 진행하되**, 적용 전에 원격 현재 권한을 실제로 떠서(`information_schema.role_table_grants` / `has_table_privilege`) **델타 0임을 출력으로 남긴다.** 델타가 0이 아니면 그때 멈추고 승인.
  - **넓히는 방향(새 롤·새 컬럼 노출·`to public`)이면 델타 0이어도 (b) 승인.** 이 항목의 해소는 "이미 플랫폼이 준 권한을 마이그에 명시"라 넓히는 게 아니다 — 넓히면 그 순간 범위가 바뀐 것이니 멈춰라.
  - *(경위: 원래 "(a) dev 자율"이라 적혀 있던 걸 2026-07-15 코드리뷰가 "(b) 승인 필요"로 정정했다 — §9.3 (a)의 조건①③을 동시에 어기므로 옳은 정정이었다. 2026-07-16에 사용자가 **승인이라는 병목 대신 실측 증거**를 택해 (a′)를 신설했다. 승인은 사람이 "예"라고 하는 것이라 GRANT를 정확하게 만들지 못하지만, 실측은 만든다.)*
- **참고:** "원격 델타 0"은 사실이다(원격엔 플랫폼이 이미 같은 GRANT를 발급했으므로 재적용해도 상태가 안 변한다). 그러나 §9.3의 (a)/(b)는 **델타만이 아니라 변경의 성격**으로 가른다 — 델타 0이어도 GRANT 대상을 건드리면 (b)다.
- ⛔ **되살리지 말 것 — 실측으로 반증된 주장**: *"게이트가 초록이어도 fresh DB는 `authenticated`가 매물을 못 읽는다"* → **2026-07-14 도커 실측 결과 거짓.** 프렐류드가 플랫폼 기본 GRANT를 선언하므로 잘 읽는다(`has_table_privilege(authenticated, listings, select)` = **t**). 이 주장은 party-mode에서 "가장 무서운 발견"으로 채택돼 AC·런북·메모리까지 박혔다가 실측 한 번에 뒤집혔다. **진짜 남은 비용은 따로 있다** — 게이트의 초록은 *"마이그 + 선언된 Supabase 계약면 = 도는 DB"* 를 뜻하지 *"마이그만으로 = 도는 DB"* 를 뜻하지 않는다.
- **⚠️ 2026-07-15 대장 일원화 시 정정 (경위 — 아래 2026-07-16 정정이 이 줄을 대체한다)**: `deferred-work.md`가 이 항목을 **"판정규칙 (a) 해당(원격 델타 0 → 안전)"** 으로 들고 있었다 — 당시 (b) 판정과 **정반대**다. 코드리뷰가 (a)→(b)로 정정했는데 한쪽만 고쳐서 생긴 라이브 모순이었고, 통합하며 (b)로 통일했다.
  - ~~"착수 시 이 항목을 근거로 GRANT를 자율 추가하지 말 것"~~ → **낡음. 지금 판정은 위의 (a′)다**(2026-07-16 사용자 결정으로 신설 — 승인 대신 **실측 증거**). Story 9.1이 이 절차대로 진행했다.
  - 🔁 **이 항목은 같은 방식으로 두 번째 모순을 낳았다 (9.1 코드리뷰 적발, 2026-07-16).** 위 줄이 *"한쪽만 고쳐서 생긴 라이브 모순"*을 경고하는 바로 그 문장인데, 9.1이 (a′)를 신설하고 아래에 5줄을 **덧붙이기만** 하고 이 줄을 안 고쳐 **같은 항목 안에 정반대 지시 두 개**가 공존했다. **경고문은 자기 자신을 지키지 못한다**(CLAUDE.md B9 — 문서는 계약이 아니다). 항목에 줄을 더할 땐 **위쪽에 그걸 부정하는 줄이 있는지부터** 본다.
- 🔗 **인수조건으로 심어짐 (2026-07-16)** — `epics-increment-2026-07-12.md` **Story 9.1**에 (a′) 절차를 AC로 박았다(이 에픽의 첫 마이그가 그 축을 건드리므로). 규칙 정본인 `docs/conventions.md`는 dev 에이전트에 자동 주입되지만, **주입은 "알게" 하고 AC는 "하게" 한다** — 둘 다 둔다.
- **근거:** `docs/deployment-runbook.md` §8-① · `_bmad-output/implementation-artifacts/8-6-ac-deploy-1-배포-순서-마이그레이션-게이트.md`
- ✅ **Story 9.1이 이번에 명시한 범위 (2026-07-16, `0012_listing_images.sql`) — 닫지 않음.**
  - **적용 전 실측**(델타 확인): `information_schema.role_table_grants`를 원격에서 떠본 결과 `listing_images`는 신규 테이블이라 비교 대상 자체가 없었다(기존 5개 테이블 — `chat_messages`·`chat_rooms`·`guide_documents`·`listings`·`profiles`만 GRANT 존재, 이번 마이그가 건드리지 않아 그 축의 델타는 0).
  - **신규 테이블에 대해 명시한 것**: `anon`은 0011과 같은 모양(`revoke select` 후 컬럼 스코프 `grant select(id, listing_id, storage_path, sort_order, is_cover, credit)`). `ai_readonly`는 0004 선례대로 `grant select on public.listing_images to ai_readonly` 명시.
  - **명시하지 않고 남긴 것**: `authenticated`에 대한 `listing_images` 명시 GRANT는 **이번에 추가하지 않았다** — 플랫폼 기본(`alter default privileges`)에 그대로 위임. 이유: AC6이 "새로 만드는 테이블만 명시"라 했고, 그 범위는 anon·ai_readonly(명시 GRANT 관례)로 한정했다 — authenticated까지 명시하는 건 #18의 "나머지 테이블(authenticated 전 경로)" 축을 건드리는 것이라 범위 밖.
  - ⚠️ **"anon 컬럼 차단"이라 부르지 마라 (9.1 코드리뷰 정정, 2026-07-16).** `listing_images`는 컬럼이 6개이고 `grant select (...)`도 **6개 전부**를 재부여한다 → **차단되는 컬럼은 0개다.** `revoke`+전체컬럼 `grant`는 테이블 GRANT와 동치다. **이 조치의 실효는 딱 하나** — *"앞으로 이 테이블에 컬럼을 추가해도 anon엔 자동으로 안 보인다"*(`0011:38-39` 주석이 그 효과를 정확히 서술한다). 그건 진짜 가치가 있지만 **차단이 아니라 예방이다.** "차단"이라 적으면 다음 사람이 **차단이 이미 걸려 있다고 믿고 민감 컬럼을 추가한다** — 있지도 않은 보안 성질을 선언하는 건 부채보다 비싸다. (`listings`는 다르다 — `0011`은 `embedding`·`updated_at`을 **실제로 제외**해 진짜 차단이 걸려 있다.)
  - **남은 범위(변화 없음)**: `profiles`·`chat_rooms`·`chat_messages`·`guide_documents`·`listings`의 `authenticated` GRANT 명시 및 프렐류드의 `alter default privileges` 제거는 여전히 열려 있다.
  - ➕ **9.1이 새로 늘린 범위 (코드리뷰 적발, 2026-07-16) — 위 "남은 범위"가 실제보다 좁았다.** `0012`는 `storage.objects`에 정책 2종을 만들면서 **GRANT는 한 줄도 주지 않는다.** 프렐류드의 `alter default privileges`는 `in schema public`이라 **storage에 미치지 않는다** → anon·authenticated가 `storage.objects`를 읽고 쓰는 근거는 **전적으로 Supabase 플랫폼이 미리 발급한 GRANT**다 = 이 항목의 정의 그 자체. 즉 **이 스토리가 부채를 한 칸 늘려놓고 대장에는 늘어난 사실을 안 적었다** — 이 항목 자신이 `:122`에서 경고한 실패 모드(*"나머지가 얼마나 되는지 아무도 세어본 적 없다"*)의 반복이다. **해소 범위에 `storage.objects`·`storage.buckets` 축을 포함할 것.**
  - 🧾 **원본 덤프는 `9-1-*.md` Debug Log 5-1에 있다** (코드리뷰가 보정 첨부). 요약본이 가렸던 사실: **`anon`이 전 테이블에 DELETE·INSERT·UPDATE·TRUNCATE를 갖는다** — `0012`/`0011`이 회수한 건 SELECT 하나뿐이고, anon 쓰기를 막는 건 "anon용 쓰기 RLS 정책이 없어서 기본 deny" **단 하나**다. 위 "해소"가 `grant select`만 말하는 것은 이 축을 덜 세는 것이다.
- 📌 **코드리뷰 이월 (2026-07-16, Story 9.1 리뷰 — 이 변경이 만든 게 아닌 기존 축)**: 프렐류드의 `alter default privileges ... **grant all** on tables to anon, authenticated`(`scripts/migration-check-prelude.sql:66-67`)는 SELECT뿐 아니라 **INSERT/UPDATE/DELETE/TRUNCATE까지** 준다. 0012는 `revoke **select** ... from anon`만 하므로 **anon은 `listing_images`에 쓰기 GRANT를 보유**한다(다른 테이블도 동일). 지금 막고 있는 것은 "anon용 쓰기 RLS 정책이 없어서 기본 deny" **단 하나** — 누군가 anon 정책을 잘못 넓히거나 RLS가 스치면 즉시 뚫린다. 위 "해소"가 `grant select`만 말하는 것은 이 축을 덜 세는 것이다. **이 항목이 위임이라 부르는 것의 실제 내용은 TRUNCATE 포함 전권이다.**

---

### DW-319: [구 #19] Epic 6 관리자 4화면 운영 실사용 미확인 (Epic 6 회고 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #19) — 원출처: (표기 없음)
location: 운영 `https://bmad-encar-demo.vercel.app/admin` (회원·매물·거래·채팅)
severity: medium
reason: Epic 6 회고가 남긴 '운영 /admin 4화면 실사용 확인' 액션이 Epic 7 회고로 이어지지 않고 1개월간 추적에서 소실됐다.
trigger: 데모·제출 시연 직전.
status: open

- **위치:** 운영 `https://bmad-encar-demo.vercel.app/admin` (회원·매물·거래·채팅)
- **내용:** Epic 6 회고가 액션으로 남긴 "main 배포 반영 후 운영 /admin 4화면 실사용 확인"이 **수행 흔적이 없다.** `main` 병합·배포 자체는 확인됨(`94c62ec`, Vercel Production READY). 코드는 preview E2E로 검증됐으므로 결함 가능성은 낮으나 **운영 화면을 사람이 본 적이 없다.**
- **트리거:** 데모·제출 시연 직전.
- **해소:** 운영 /admin 4화면 클릭 1회.
- 📌 *(2026-07-15 회고 A2 등록: Epic 6 회고 → Epic 7 회고가 추적하지 않아 1개월간 소실됐던 항목. 회고 체인 끊김의 실물.)*

### DW-320: [구 #20] 거래일이 `updated_at` 근사 (정확한 `sold_at` 부재, Epic 6 회고 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #20) — 원출처: (표기 없음)
location: 관리자 거래 내역 화면 · `listings` 테이블
severity: medium
reason: 거래일을 `updated_at`으로 근사 표시해 타임존 차이로 ±1일 어긋날 수 있으나, 데모 범위에서는 무해하다.
trigger: 거래일 정확도가 요구될 때(정산·리포트 등). 데모 범위에선 무해.
status: open

- **위치:** 관리자 거래 내역 화면 · `listings` 테이블
- **내용:** 거래일을 `updated_at`으로 근사 표시한다. **타임존 차이로 ±1일 어긋날 수 있다.** 실측 확인: `supabase/migrations/` 전수 grep 결과 `sold_at` 컬럼 **0건 = 미구현 확정**.
- **트리거:** 거래일 정확도가 요구될 때(정산·리포트 등). 데모 범위에선 무해.
- **해소:** `sold_at timestamptz` 컬럼 추가(nullable, additive) + 구매완료 액션에서 기록 + KST 표시. 마이그 신규 1장.
- 📌 *(2026-07-15 회고 A2 등록. Epic 6 회고가 "정확과 간이를 투명하게 구분해 남긴다"는 좋은 판단으로 남긴 항목인데, 대장에 등록하지 않아 추적이 끊겼다.)*

### DW-321: [구 #21] 🔒 완전 계정 삭제 불가 — 구조적 보류 (Epic 6 회고 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #21) — 원출처: (표기 없음)
location: 관리자 회원 관리 (`profiles` 행만 삭제)
severity: low
reason: 삭제하려면 `service_role` 키 + `auth.admin.deleteUser()`가 필요한데 `service_role` 키 금지가 이 프로젝트의 확립된 규칙이라, 규칙을 유지하는 한 영구 보류다.
trigger: 개인정보 완전 삭제가 법적·계약적으로 요구될 때. 그 순간 **규칙 6 재검토가 선행**돼야 한다(사용자 승인 필요).
status: open

- **위치:** 관리자 회원 관리 (`profiles` 행만 삭제)
- **내용:** 회원 "삭제"가 `profiles` 행만 제거하고 **`auth.users`의 로그인 계정 자체는 남는다.** 삭제하려면 `service_role` 키 + `auth.admin.deleteUser()`가 필요한데, **`service_role` 키 금지가 이 프로젝트의 확립된 규칙**이다(`_bmad-output/project-context.md` 규칙 6 · `docs/conventions.md` §5).
- **왜 🔒인가:** 다른 부채처럼 "나중에 하면 되는 것"이 아니다. **해소하려면 프로젝트 보안 규칙 자체를 바꿔야 한다.** 규칙을 유지하는 한 영구 보류다.
- **트리거:** 개인정보 완전 삭제가 법적·계약적으로 요구될 때. 그 순간 **규칙 6 재검토가 선행**돼야 한다(사용자 승인 필요).
- 📌 *(2026-07-15 회고 A2 등록. 이전엔 "미해결"로만 떠돌았으나 실은 **결정된 절충**이다 — 라벨을 정확히 하는 게 이 등록의 목적.)*

### DW-322: [구 #22] 게이트의 `--single-transaction`이 `create index concurrently`류를 원천 차단 (8.6 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #22) — 원출처: (표기 없음)
location: `scripts/check_migrations.py:143`
severity: medium
reason: 실측 결과 현재 마이그레이션 12개 전량에 `create index concurrently` 등 트랜잭션 불가 구문이 0건이라 오늘은 무해하다.
trigger: **Epic 13(RAG)이 무중단 HNSW 인덱스를 얹는 순간.**
status: open

- **위치:** `scripts/check_migrations.py:143`
- **내용:** 게이트가 마이그를 단일 트랜잭션으로 적용한다. `create index concurrently`·`vacuum`·`alter system`·`reindex`는 트랜잭션 안에서 못 돈다 → 원격 `apply_migration`에선 통과하는데 **게이트만 `cannot run inside a transaction block`으로 red**.
- **오늘 무해한 이유:** 실측 — 현재 마이그 12개 전량에 해당 구문 **0건**.
- **트리거:** **Epic 13(RAG)이 무중단 HNSW 인덱스를 얹는 순간.**
- **해소:** `--single-transaction`을 되돌리지 말 것(게이트 출력이 거짓말하는 걸 막는 근거로 도입됨). **진짜 문제는 게이트가 마이그 작성 방식을 몰래 제약하는데 그 제약이 어느 문서에도 없다는 것** → `docs/deployment-runbook.md` §8 사각지대에 추가.

### DW-323: [구 #23] `0004`·`0006`의 `create role ai_readonly` 이중 보유 = 조용한 드리프트 장치 (8.6 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #23) — 원출처: (표기 없음)
location: `supabase/migrations/0004_guide_documents.sql:52-56` · `0006_readonly_role.sql:24-28`
severity: medium
reason: 8.6에서 in-place 수정(party-mode 안 A, 사용자 확정)을 택한 데 따른 구조적 대가로 남겨둔 것이다.
trigger: 0006의 롤 정의를 바꿔야 할 때.
status: open

- **위치:** `supabase/migrations/0004_guide_documents.sql:52-56` · `0006_readonly_role.sql:24-28`
- **내용:** 둘 다 `if not exists` 멱등 가드라, 미래에 0006을 `login`·`connection limit` 등 **다른 속성으로 고치면 fresh DB에선 0004가 먼저 만들고 0006은 no-op** → 롤이 0006 의도와 다르게 생성된다. 에러 0건 + 프로브 3건 통과 = **게이트 초록**, 그런데 원격은 0006 정의를 가져 **fresh ≠ 원격**.
- **트리거:** 0006의 롤 정의를 바꿔야 할 때.
- **왜 이렇게 뒀나:** 8.6의 in-place 수정(party-mode 안 A, 사용자 확정)이 치른 구조적 대가. 런북 §8-②가 "fresh DB == 원격을 보증하지 않는다"를 이미 인정하나, **그 사각지대의 원인을 이 패치가 하나 더 만들었다**는 사실은 안 적혔다.

### DW-324: [구 #24] 프렐류드 `auth.users` 3컬럼 스텁이 실제 플랫폼보다 좁다 — 양방향 오류 (8.6 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #24) — 원출처: (표기 없음)
location: `scripts/migration-check-prelude.sql:531-535`
severity: medium
reason: 실측 결과 현재 마이그레이션 중 `auth.users`의 3컬럼(스텁 범위) 밖을 참조하는 곳이 0건이라 오늘은 무해하다.
trigger: 마이그가 `auth.users`의 3컬럼 밖을 참조할 때.
status: open

- **위치:** `scripts/migration-check-prelude.sql:531-535`
- **내용:** **false red** — 미래 마이그가 `created_at`·`last_sign_in_at`·`phone`을 참조하면 원격은 정상인데 게이트만 red. **false green** — 실제 `auth.users.email`은 `varchar(255)`+unique인데 스텁은 `text`+무제약이라, **unique 위반을 유발하는 마이그가 fresh에선 통과하고 원격에서 터진다.**
- **오늘 무해한 이유:** 실측 — 현재 마이그 중 해당 컬럼 참조 0건.
- **트리거:** 마이그가 `auth.users`의 3컬럼 밖을 참조할 때.
- **해소:** 스텁을 실제 플랫폼 정의에 맞춤. 런북 §8-③은 *"프렐류드가 선언한 것에 대한 의존은 안 잡힌다"* 만 인정하고 **선언이 실제보다 좁아서 생기는 오류**는 다루지 않는다.

### DW-325: [구 #25] `psycopg[binary,pool]` 버전 미고정 (8.4 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #25) — 원출처: (표기 없음)
location: `api/pyproject.toml` · `api/requirements.txt`
severity: medium
reason: 버전을 미고정 상태로 두면 향후 `psycopg_pool` 업그레이드 시 경고·동작 변경 위험이 있다는 것으로, 업그레이드 시점에 핀을 추가하면 된다.
trigger: 의존성 업그레이드 시.
status: open

- **위치:** `api/pyproject.toml` · `api/requirements.txt`
- **내용:** `ConnectionPool(..., open=True)` 생성자 패턴이 최신 `psycopg_pool`에서 지양되는 추세라, 버전 미고정 상태로는 업그레이드 시 경고/동작 변경 위험.
- **트리거:** 의존성 업그레이드 시. **해소:** 버전 핀 추가.

### DW-326: [구 #26] 취소·삭제된 토큰 보유자가 공개 페이지에서 401 데드엔드 (8.5 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #26) — 원출처: (표기 없음)
location: `web/src/lib/api/aiSearch.ts:60-62`
severity: medium
reason: 드문 경로(이미 폐기된 토큰 보유)에서만 발생하고, 서버측 401은 계약상 의도된 동작이라 방어는 클라이언트 몫으로 남겨뒀다.
trigger: 드문 경로(폐기된 토큰 보유).
status: open

- **위치:** `web/src/lib/api/aiSearch.ts:60-62`
- **내용:** `supabase.auth.getSession()`은 `expires_at`이 미래이기만 하면 서버에 묻지 않고 캐시 세션을 돌려준다 → 이미 폐기된(계정 삭제·세션 강제만료·타 기기 비번변경) 토큰인 줄 모른 채 `Authorization` 헤더에 붙인다. 서버는 401 "유효하지 않은 인증 토큰입니다."를 던지고 사용자는 빨간 알럿을 본다. **재시도해도 동일** — 쿠키가 안 지워져 같은 토큰이 계속 나간다. 역설: `/ai`는 **공개** 페이지라 같은 사람이 시크릿창에선 멀쩡히 쓴다.
- **트리거:** 드문 경로(폐기된 토큰 보유).
- **해소:** 401 시 헤더 없이 1회 재시도, 또는 `signOut()` 후 anon 재요청. 서버측 401은 `conventions.md` §8 계약상 의도된 동작이므로 **방어는 클라이언트 몫**. ⚠️ *"무효 토큰 사용자를 조용히 anon으로 떨어뜨릴 것인가"* 는 **제품 판단이 필요**하다.

### DW-327: [구 #27] 시드 멱등 delete가 `listings` 자식 테이블 FK를 가정하지 않음 (2-5 리뷰 이월)

origin: 장부 통합 이관(구 docs/tech-debt.md #27) — 원출처: (표기 없음)
location: `supabase/seed.sql`
severity: medium
reason: 데모/과제용 단일 공유 DB에서 `seed.sql` 재실행은 드문 수동 작업이고, 지금 39건 INSERT문 전체를 고정 id로 바꾸는 건 이 스토리 범위 밖의 큰 변경이라 Epic 10.5 시점에 다시 판단하기로 이월했다.
trigger: **Epic 10.5 `wishlists`(마이그 0015 예정)**가 `listings`의 첫 자식 테이블이다. Epic 9 `listing_images`도 마찬가지(`ON DELETE CASCADE`라 delete는 통과하지만 이미지 행이 조용히 사라진다).
status: done 2026-07-29
resolution: 측정 과제는 끝났고 미해결 결함은 DW-389(구 #89)가 승계 — 같은 결함을 두 항목이 들지 않는다

- **위치:** `supabase/seed.sql`
- **내용:** 재실행 시 시드 매물을 delete 후 **새 uuid로 재삽입**한다. 현재 `listings`는 leaf 테이블이라 무해하나, `listings.id`를 FK로 참조하는 테이블이 생기면 (a) delete가 막히거나 (b) 외부가 들고 있던 옛 listing id가 dangling 된다.
- **⚠️ 트리거가 실제로 온다:** **Epic 10.5 `wishlists`(마이그 0015 예정)가 `listings`의 첫 자식 테이블이다.** Epic 9 `listing_images`도 마찬가지(`ON DELETE CASCADE`라 delete는 통과하지만 이미지 행이 조용히 사라진다).
- **해소:** 시드 멱등 전략 재설계 — 고정 id 사용 또는 자식 정리 순서 명시.
- 🔗 **인수조건으로 심어짐 (2026-07-16)** — 대장에만 두면 아무도 안 읽는다(CLAUDE.md B5. Epic 6 회고 액션이 1개월 소실된 게 그 실물 — #19·#20). `epics-increment-2026-07-12.md`의 **두 곳**에 AC로 박았다:
  - **Story 9.1**(FK가 태어나는 곳) — 전략을 (a)고정 id / (b)자식 정리 순서 / (c)근거 있는 이월 중 택해 **기록에 남긴다**. Epic 10.5 `wishlists`가 두 번째 자식이라는 것도 함께 본다.
  - **Story 9.7**(시드를 실제로 돌리는 곳) — **두 번 연속 실행해 이미지 행 수가 유지되는지 센다.** ⚠️ **"에러 없음"으로 갈음 금지** — `ON DELETE CASCADE`는 조용히 지우므로 **에러 0건이 곧 정상이 아니다.** 이게 이 항목의 핵심이다.
  - 한 곳만 심으면 다른 스토리가 그냥 지나간다 — 판단(9.1)과 검증(9.7)은 다른 일이다.
- ✅ **Story 9.1 판단 완료(2026-07-16) — (c) 근거 있는 이월을 택함(닫지 않음).**
  - **실측**: `supabase/seed.sql:196`이 여전히 `delete from public.listings where seller_id = v_seller_id;` 후 새 uuid로 재삽입(고정 id 아님) — 확인됨. `listing_images.listing_id`는 `ON DELETE CASCADE`(0012).
  - **왜 지금 무해한가**: Story 9.1은 `seed.sql`을 고치지 않고 `listing_images`에 행을 넣지도 않는다(DB 전용 스토리, 사진 시딩은 9.7의 일) — 그래서 오늘 시점엔 지울 이미지 행 자체가 0건이다.
  - **9.7이 실제로 할 일(여기서 미리 못박음)**: 9.7이 사진을 시드에 추가할 때는 **같은 seed.sql 실행 안에서** listings delete+재삽입 **직후** 그 새 `listing_id`로 이미지를 삽입해야 한다(옛 이미지는 cascade로 같이 지워지고, 새 이미지가 새 id로 다시 채워짐) — 이게 사실상 (b) 자식 정리 순서를 만족시킨다. 9.7의 AC(두 번 연속 실행 후 이미지 행 수 카운트)가 이걸 실측으로 검증한다.
  - **진짜 위험은 seed.sql 밖에 있다**: seed.sql이 모르는 데이터 — **실사용자가 그 시드 매물에 올린 사진**·**Epic 10.5 `wishlists`의 실제 찜 기록** — 은 (b)로 못 구제한다. seed.sql은 자기가 만든 행만 다시 만들 뿐, 그 사이 사용자가 쌓은 데이터를 복원할 방법이 없다. **Epic 10.5 착수 시 이 사실을 근거로 (a) 고정 id를 재고할 것** — wishlists는 사용자 행동의 결과물이라 이미지보다 유실 시 체감 피해가 크다.
  - **이월 사유**: 데모/과제용 단일 공유 DB(런북 §2)에서 `seed.sql` 재실행은 드문 수동 작업이고, 지금 당장 39건 INSERT문 전체를 고정 id로 바꾸는 건 이 스토리 범위(DB 전용, 마이그 1개) 밖의 큰 변경이다. (a)로 미리 확정하지 않고 10.5 시점에 그때의 요구(찜 데이터 보존 필요성)를 보고 다시 판단하는 게 낫다.
- ✅ **Story 9.7 측정 완료(2026-07-21) — 이 항목이 요구한 실측이 끝났다. 결과: 사진은 살아남지 못한다.**
  - **어떻게 쟀나**: 원격에서 `seed.sql`을 재실행하는 것은 그 자체가 파괴적이라(아래 참조) **빈 Postgres를 새로 세워** 쟀다. 이 환경엔 도커·psql·sudo가 전부 없어 **PGlite(WASM PostgreSQL 16.4 + pgvector)** 를 썼다 — 프렐류드 → 마이그 0001~0015 전량 → `seed.sql` 1회차 → 시드 매물 5건에 `listing_images` 더미 10행 + `chat_rooms` 1건 삽입 → `seed.sql` 2회차.
    - ⚠️ **측정 환경의 한계를 밝힌다**: CI 게이트는 pg17, 이 측정은 pg16이다. 또 PGlite에 `pgcrypto`가 없어 `extensions.crypt`/`gen_salt`를 스텁으로 대체했다(비밀번호 해시 — **측정 대상인 delete-재삽입·CASCADE와 무관**하고 이 DB에서 로그인을 하지 않는다).
  - **측정값**:

    | 항목 | 재실행 전 A | 재실행 후 B |
    |---|---|---|
    | `listing_images` | 10행 | **0행** |
    | `chat_rooms` | 1행 | **0행** |
    | `listings` | 97행 | 97행 (수만 같다) |
    | 매물 `id` 보존 | — | **0/97건** (전부 새 uuid) |

  - 🚨 **에러는 한 건도 나지 않았다.** 이 항목이 처음부터 경고한 *"`ON DELETE CASCADE`는 조용히 지우므로 에러 0건이 곧 정상이 아니다"* 가 실측으로 재현됐다. **행 수를 세지 않았다면 "정상"으로 보고됐을 것이다.**
  - ✎ **정정 — 이 항목 본문의 *"`listing_images`(또는 `wishlists`)가 `listings`의 첫 자식 테이블"* 은 사실이 아니다.** `chat_rooms`(0003, Epic 5)가 훨씬 먼저 있었고 그것도 `ON DELETE CASCADE`다. 즉 **자식 테이블이 생기면 위험해진다는 미래형 전제 자체가 틀렸고, 위험은 Epic 5부터 이미 실재했다.** 위 측정에서 채팅방이 함께 사라진 것이 그 증거다.
  - ✎ **정정 — 본문의 *"Epic 10.5 `wishlists`(마이그 0015 예정)"* 의 번호는 무효다.** `0015`는 Story 9.7이 `listings_update_not_sold`에 썼다(#54 해소). `wishlists`는 그만큼 뒤 번호로 밀린다 — 원장 표도 함께 볼 것.
  - **Epic 10.5 인계(이 항목의 다음 판단 지점, 변경 없음)**: 매물 id가 **전량 새로 발급되는 것이 실측으로 확정**됐으므로, `wishlists`(사용자가 직접 찜한 기록)는 `seed.sql` 재실행 한 번에 전부 dangling 된다. 10.5 착수 시 **(a) 고정 id를 다시 검토할 근거가 추측이 아니라 숫자로 존재한다.**
  - **운영 결론(런북 §9에 한 줄로 박음)**: 이 DB에서 `seed.sql` 재실행은 **사진·채팅 이력을 파괴하고 Storage에 고아 파일을 남긴다**(Storage 오브젝트는 CASCADE 대상이 아니다). 하려면 백업 후, 재실행 뒤 `seed_listing_photos.py`를 다시 돌려야 한다.

### DW-328: [구 #28] `e2e-checklist.md`가 정상 동작을 실패로 판정 (문서 부채)

origin: 장부 통합 이관(구 docs/tech-debt.md #28) — 원출처: (표기 없음)
location: `docs/e2e-checklist.md:24`
severity: medium
reason: 증분 Epic 9~16이 화면·계약을 대폭 바꾸므로 지금 대본을 고쳐도 Epic 9 하나만 끝나면 다시 낡는다 — 증분이 끝난 뒤 새로 짜는 것이 더 싸다고 판단해 대본 자체를 폐기했다.
status: done 2026-07-29
resolution: 대본 폐기로 종결 — docs/e2e-test-cases.md·e2e-checklist.md·ai-e2e-hard-queryset.json·run_ab_eval.py 4개 파일 부재 확인(2026-07-29 실측)

- **위치:** `docs/e2e-checklist.md:24`
- **내용:** *"비로그인으로 … **보호 경로(`/search` 등) 접근 시 로그인으로 리다이렉트(307)**"* 라 적혀 있으나, **Story 8.5 이후 `/search`는 열람(anon 허용)이다** — `conventions.md` §8 · `web/src/proxy.ts:26` → `PROTECTED_PREFIXES = ['/admin','/sell','/ai','/chat']`(`/search` 없음).
- **왜 위험:** 이 체크리스트를 그대로 수행하면 **멀쩡한 코드를 "고치는" 회귀**를 유발한다. E2E 크로스체크가 이 문서를 대본으로 쓴다.
- ✅ **해소 — 대본 폐기로 종결 (2026-07-16, 사용자 결정).** 처음엔 §8 계약에 맞춰 두 대본을 정정했으나(같은 오기재가 양쪽에 있었다), 이어서 **E2E 자산 전체를 폐기**하기로 했다. 삭제: `docs/e2e-test-cases.md`(304줄) · `docs/e2e-checklist.md`(148줄) · `api/docs/ai-e2e-hard-queryset.json` · `api/scripts/run_ab_eval.py`.
- **왜 정정이 아니라 폐기인가**: 증분 Epic 9~16이 화면·계약을 대폭 바꾼다(이미지·신뢰속성·랜딩 개편·실시간 채팅·역할 통합·AI 4분기). **지금 대본을 고쳐도 Epic 9 하나만 끝나면 다시 늙는다.** 증분이 끝난 뒤 새로 짜는 게 싸다. 필요하면 git 이력에서 꺼낸다.
- 📌 **교훈(이건 남는다)**: 계약이 바뀐 건 8.5(2026-07-14)인데 대본은 안 따라왔고, 그대로 수행했으면 **정상 동작을 실패로 판정해 멀쩡한 코드를 고칠** 뻔했다. **문서는 조용히 늙는다 — 코드였다면 그 자리에서 빨간불이 났다.** 새로 짤 때는 **P0 케이스를 Playwright 스펙(코드)으로** 만들 것. 산문 대본은 같은 실패를 반복한다.

### DW-329: [구 #29] CI가 web·api·app 테스트를 한 번도 안 돌린다 (B9 구멍)

origin: 장부 통합 이관(구 docs/tech-debt.md #29) — 원출처: (표기 없음)
location: `.github/workflows/` (워크플로가 `migration-gate.yml` **하나뿐**)
severity: medium
reason: CI를 신설해 기본 결함은 해소했으나, E2E 자동화(P0 케이스의 Playwright 스펙화)는 별도 스토리 규모라 남겨뒀다.
status: done 2026-07-29
resolution: 2026-07-16 .github/workflows/tests.yml(api·web·app 3잡) 배선으로 해소. 잔여인 E2E CI 배선은 DW-468(구 #168)이 갖는다

- **위치:** `.github/workflows/` (워크플로가 `migration-gate.yml` **하나뿐**)
- **내용:** 유일한 CI의 `paths:` 필터가 `supabase/migrations/**`·`scripts/**`·워크플로 자신이라, **그 밖을 건드리는 push엔 게이트가 아예 안 돈다.** 결과: `api/tests/` 16파일(pytest) · web vitest(`redirect.test.ts` 등) · `app/test/` 10파일 77테스트가 **CI에서 한 번도 실행되지 않는다.** git hook도 0개.
- **왜 위험:** `project-context.md` 규칙 12(테스트 층별 표준)와 AC-DB-1 롤 누수 테스트가 **로컬에서 누가 치기 전엔 아무것도 지키지 않는다.** CLAUDE.md B9("규칙은 실행되는 검사로 바꾼다")의 정면 구멍.
- ✅ **해소 완료 (2026-07-16, `.github/workflows/tests.yml`)** — api·web·app 3잡 병렬. `migration-gate.yml`은 마이그 전용으로 경로 분리 유지.
  - **실증된 필요성**: 로컬에서 pytest를 처음 돌리자 **8개 파일이 수집 단계에서 전멸**했다 — Story 8.4가 추가한 `psycopg_pool`이 로컬 환경에 설치된 적이 없었다(`requirements.txt`엔 있는데 venv엔 없음). **CI가 있었으면 8.4 시점에 바로 빨간불이 났을 일.** 설치 후 167 통과.
  - **red→green 증명**: web `resolveSafeRedirect`의 오픈 리다이렉트 방어선을 일부러 뚫음 → **4 failed**, 되돌림 → **6 passed**. 검사가 실제로 문다.
  - **⚠️ secrets를 넣지 마라 — 그게 안전장치다.** CI 조건(`api/.env` 부재)을 실제로 재현해 확인: **165 passed, 5 skipped** — 운영 DB 접속 2건(`test_readonly`)·과금 호출 3건(`test_live_smoke`)이 정확히 자동 skip됐다. `api/.env`는 `.gitignore`라 레포에 없다. `DATABASE_URL`·`GEMINI_API_KEY`를 CI 시크릿에 넣는 순간 이 게이트는 결정론 검사에서 **라이브·과금·비결정 검사**로 바뀐다.
  - **이 게이트가 안 보는 것**(워크플로 주석에 실측해서 명시): **E2E — Playwright 스펙이 레포에 0개다**(`docs/e2e-*.md`는 사람이 읽는 수동 대본이지 코드가 아니다). web은 유닛 1파일(6건)뿐 — 표준이 "E2E 우선, Vitest는 순수 유틸 예외"라 원래 그렇다. *(✎ 2026-07-28: Story 11.5가 `web/e2e/` 스위트(스펙 3파일 + `playwright.config.ts`)를 실제로 만들어 **이 문장은 더 이상 사실이 아니다** — `#86` 해소분. 원문은 경위로 남긴다. 다만 CI 배선은 여전히 없다 → `#168`.)*
- 📌 **남은 것**: E2E 자동화(P0 케이스 → Playwright 스펙)는 **별도 스토리 규모**. 지금은 계약이 바뀌어도 대본이 조용히 늙는다(#28이 그 실물이었다).

### DW-331: [구 #31] `architecture.md`(baseline)가 현재와 다른 사실을 명령형으로 적고 있다 (문서 부채)

origin: 장부 통합 이관(구 docs/tech-debt.md #31) — 원출처: (표기 없음)
location: `_bmad-output/planning-artifacts/architecture.md` (2026-06-18 동결)
severity: medium
reason: 이 문서는 BMAD 공식 산출물(2026-06-18 동결, 역사적 결정 기록)이라 본문을 고치면 그 근거를 잃는다 — 증분은 원본을 덮어쓰지 않고 별도 문서를 얹는 BMAD 방식을 따라 배너만 달았다.
status: done 2026-07-29
resolution: _bmad-output/planning-artifacts/architecture.md 상단에 baseline 동결 배너 실재 확인(2026-07-29 실측)

- **위치:** `_bmad-output/planning-artifacts/architecture.md` (2026-06-18 동결)
- **내용:** 배포 **Vercel 우선**(:218 — 실제는 api=Cloud Run, Vercel은 480MB>250MB로 폐기) · 생성 모델 **`gemini-flash-latest`**(:50 — 실제 `gemini-3.1-flash-lite` 고정) · **Next 16.2.7**(:82 — 실제 16.2.9). Vercel 번들 한도도 **500MB(:51) vs 250MB(project-context)** 로 두 값이다.
- **왜 위험:** `:505`가 *"모든 아키텍처 결정을 문서 그대로 따른다"* 고 **요구**한다. `architecture-increment-2026-07-12.md:79`가 "배포 드리프트 정정"이라 선언하지만 **baseline 본문은 안 고쳐졌다.**
- ✅ **해소 완료 (2026-07-16) — 본문은 안 고치고 배너를 달았다.**
  - **왜 본문 수정이 아닌가**: 이건 **BMAD 공식 산출물**(frontmatter `stepsCompleted:[1..8]`·`status:complete`·`completedAt:2026-06-18`)이고, "2026-06-18에 이 근거로 이렇게 결정했다"는 **역사**다. 고치면 그 근거를 잃는다. 증분은 원본을 덮어쓰지 않고 **별도 문서를 얹는 게 BMAD 방식**이고, 이 프로젝트는 이미 그렇게 하고 있었다(`architecture-increment-2026-07-12.md`). 진짜 문제는 "원본이 틀렸다"가 아니라 **"원본이 자기가 최신인 척한다"**였다.
  - **어디에 달았나 — 두 곳**: ① 문서 상단(첫인상) ② `Implementation Handoff`의 *"모든 아키텍처 결정을 문서 그대로 따른다"* 바로 위 — **에이전트가 실제로 "그대로 따르라"를 읽는 지점**이라 거기가 진짜 소비처다. 한 곳만 달면 두 번째를 읽는 에이전트는 못 본다.
  - **낡은 값 4종을 실측해서 표로**: 배포처(Vercel→Cloud Run) · 생성 모델(`gemini-flash-latest`→`gemini-3.1-flash-lite`) · 버전(Next 16.2.7→16.2.9, Flutter 3.44.0→Dart ^3.12.2) · 폴링(3~5초→코드가 정본).
  - 📌 **작업 중 자기 결함 1건**: 배너 초안에 `:50`·`:218` 같은 **줄 번호를 적었는데 배너를 넣느라 줄이 밀려 즉시 틀렸다.** Epic 8 회고가 꼽은 결함 클래스(*"주석이 가리키는 줄 번호가 같은 커밋 때문에 어긋남"*)를 그 자리에서 재현한 것. **줄 번호를 빼고 문자열 인용으로 바꿨다** — 문서는 줄이 밀리므로 줄 번호로 가리키지 않는다.

### DW-389: [구 #89] 시드 재실행이 **사진·채팅을 전부 지운다**

origin: 장부 통합 이관(구 docs/tech-debt.md #89) — 원출처: `#27` 승계 — 결함은 미해결, 2026-07-21 코드리뷰 등재, 🟡 조건부
location: `supabase/seed.sql` · `supabase/migrations/0012_listing_images.sql`(`on delete cascade`)
severity: high
reason: 운영 반영은 마이그레이션으로만 하고 `seed.sql`은 데모 데이터 초기화용이라 평시에는 돌지 않기 때문에 오늘은 무해하다.
trigger: `seed.sql` 재실행이 필요해지는 시점 · ~~**Epic 10.5**(고정 id 전환 판단) — 10.5 인수조건에 체크박스로 심었다(B5).~~ → **판단 완료(아래).**
status: open

- **위치:** `supabase/seed.sql` · `supabase/migrations/0012_listing_images.sql`(`on delete cascade`)
- **내용:** `seed.sql`은 재실행 시 깨끗한 상태를 만들려고 `listings`를 delete 후 재삽입한다. 그런데 자식 테이블이 `on delete cascade`라 **매물이 지워질 때 사진(`listing_images`)과 채팅방도 함께 지워진다.** Story 9.7 실측(빈 Postgres): `listing_images` **10행 → 0행**, `chat_rooms` **1행 → 0행**, 매물 id 보존 **0/97**.
- **왜 #27을 닫고 이걸 새로 여나:** #27의 과제는 *"정말 지워지는지 측정하라"*였고 **측정은 끝났다**. 하지만 `seed.sql`은 **한 줄도 안 바뀌었고**, #27이 *"9.7이 할 일(여기서 미리 못박음)"* 로 지정한 조치(같은 `seed.sql` 실행 안에서 새 `listing_id`로 이미지 삽입)는 **미이행**이다. 측정 과제가 끝났다고 결함까지 닫으면 **열린 일 장부에서 위험이 사라진다** — 그러면 Epic 10.5 착수자가 대장이 아니라 "다음 액션" 절을 읽어야만 이 일을 알게 된다(#27 본문 스스로 *"대장에만 두면 아무도 안 읽는다 — Epic 6 회고 액션 1개월 소실이 그 실물"* 이라 경고한 그 형태).
- **지금 무해한 이유:** 운영 반영은 마이그레이션으로만 하고 `seed.sql`은 데모 데이터 초기화용이라 평시에 안 돈다. 운영 결론은 런북 §9에 있다.
- **트리거:** `seed.sql` 재실행이 필요해지는 시점 · ~~**Epic 10.5**(고정 id 전환 판단) — 10.5 인수조건에 체크박스로 심었다(B5).~~ → **판단 완료(아래).**
- **해소:** (a) 매물 id를 고정해 delete+재삽입을 없애거나 (b) 사진·채팅을 같은 `seed.sql` 실행 안에서 새 id로 재삽입.
- ⚠️ **측정 환경의 한계는 `#99`에 있다** — 이 숫자는 pg16 PGlite에서 잰 것이고 원격에서 재현하지 않았다.
- ✅ **Story 10.5 판단 완료(2026-07-22) — 현행 유지(b 방향도 이 스토리에서 하지 않음), 닫지 않고 이월.**
  `wishlists`가 `listings`의 두 번째 cascade 자식(`chat_rooms`에 이어)이 되면서 재시드 시 찜도 함께
  삭제되는 것이 실측대로 재확인됐다. 그럼에도 **이 스토리에서 (a) 고정 id 전환을 하지 않는다:**
  ① 재시드는 데모 리셋 전용이고, 갓 시드된 DB엔 잃을 찜이 없다 — 찜은 사용자 상호작용으로만
  생기고, "유실 체감이 크다"던 2b의 예상 근거는 운영 영속성 축인데 찜은 시드되지 않으며 운영에선
  재시드가 돌지 않는다. ② 고정 id 전환은 사진·채팅까지 걸린 delete+재삽입 전략 전체를 바꾸는
  교차 리팩터라 단일 찜 스토리에 끼워 넣으면 A2(과설계 회피)·A3(외과적 변경) 위반이다 — 전용
  스토리 몫. **새 트리거**: 운영/스테이징에 재시드가 필요해지는 시점, 또는 고정-id 전용 스토리가
  착수될 때.

### DW-390: [구 #90] **sold 매물의 "사진"은 여전히 자유롭게 교체된다** — `0015`가 막은 것은 `listings` 컬럼뿐

origin: 장부 통합 이관(구 docs/tech-debt.md #90) — 원출처: 2026-07-21 코드리뷰 원격 DB 실측, 🟡 조건부
location: `supabase/migrations/0012_listing_images.sql:119-150`(`listing_images_insert_own`·`update_own`·`delete_own`)
severity: high
reason: sold 매물은 FR11(기능 요구사항 11번)로 구매자 경로 어디에도 노출되지 않고, web 수정 화면도 이미 sold를 막고 있어 오늘은 무해하다.
trigger: **Epic 16.2**(앱 사진 업로더) — 그때 web과 같은 화면 방어를 또 짜지 말고 `listing_images` 쓰기 3정책에 `and l.status <> 'sold'`를 넣는다.
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:119-150`(`listing_images_insert_own`·`update_own`·`delete_own`)
- **내용:** RLS 조건은 **테이블마다 따로 붙는다.** `0015`는 `listings`에만 `status <> 'sold'`를 넣었고, `listing_images`의 쓰기 정책 3개는 여전히 *"이 사진이 달린 매물의 주인이 나인가"* 만 본다. **원격 `pg_policies` 조회로 확인**(2026-07-21): 세 정책 어디에도 status 조건이 없다. 즉 판매완료된 매물의 사진을 추가·교체·삭제하는 것은 **DB가 막지 않는다.**
- **지금 무해한 이유:** sold 매물은 FR11로 구매자 경로 어디에도 안 보이므로 사진이 바뀌어도 볼 사람이 없다. web 수정 화면도 sold를 막는다(`sell/[id]/edit/page.tsx:72`).
- **왜 그래도 적나:** `0015`를 만든 이유 자체가 *"화면 층 방어는 화면이 하나 늘 때마다 까먹는다 → 데이터 계층에 박는다"*(B9)였다. 사진 축은 **여전히 화면에서만 막고 있다.** Epic 16.2가 만들 앱 사진 업로더에는 그 화면 방어가 없다.
- **트리거:** **Epic 16.2**(앱 사진 업로더) — 그때 web과 같은 화면 방어를 또 짜지 말고 `listing_images` 쓰기 3정책에 `and l.status <> 'sold'`를 넣는다.
- 📌 이 스토리의 결정: *"지금 피해가 없으니 마이그를 하나 더 올리지 않고 등재 후 16.2로 이월"*(사용자 결정 2026-07-21).

### DW-391: [구 #91] 오조작으로 sold가 되면 **어떤 롤로도 되돌릴 수 없다**

origin: 장부 통합 이관(구 docs/tech-debt.md #91) — 원출처: `0015`의 대가, 2026-07-21 코드리뷰 등재, 🟡 조건부
location: `supabase/migrations/0015_listings_update_not_sold.sql:28` × `0005_admin_policies.sql:48`
severity: high
reason: 데모 단계이고 구매완료는 판매자가 의도적으로 누르는 동작이라 오늘은 무해하지만, 이미 한 번 실제로 되돌릴 방법이 없어 SQL로 직접 복구한 사례가 있다.
trigger: 실사용자가 구매완료를 오조작하는 시점 · 재오픈 UI 도입 시.
status: open

- **위치:** `supabase/migrations/0015_listings_update_not_sold.sql:28` × `0005_admin_policies.sql:48`
- **내용:** `0015`가 `using`으로 sold 행을 UPDATE 대상에서 빼면서 **판매자도 관리자도 복구 경로가 없다.** 0005는 `listings`에 관리자 **DELETE** 정책만 만들고 UPDATE는 만들지 않았다(*"UPDATE는 현재 관리 요구사항에 없어 추가하지 않는다"*). 마지막 수단인 `service_role`은 프로젝트 규칙상 금지(`conventions.md` §5).
- **추측이 아니다 — 이미 한 번 밟았다.** Story 9.7이 `0015` 원격 검증 중 테스트로 매물 하나를 sold로 바꿨다가 되돌리지 못해 **DB에 직접 SQL을 쳐서 복구**했다(`9-7-…md:432`). 그 사실을 *"정책이 작동한다는 뜻밖의 증거"* 로만 적고 대장·런북 어디에도 남기지 않은 것을 코드리뷰가 짚었다.
- **지금 무해한 이유:** 데모 단계고 구매완료는 판매자가 의도적으로 누르는 동작이다.
- **트리거:** 실사용자가 구매완료를 오조작하는 시점 · 재오픈 UI 도입 시.
- **해소(선택지와 대가):** ① 관리자 UPDATE 정책 추가 → 복구는 되지만 관리자가 sold 매물을 임의로 고칠 수 있게 돼 `0015`가 막으려던 것이 반쯤 열린다 ② 복구 전용 경로(status만 되돌리는 좁은 정책·RPC). **지금은 둘 다 안 하고 런북 §10에 복구 SQL을 적어두는 것으로 갈음**(사용자 결정 2026-07-21 — 데모 단계에서 복구 UI는 과잉, A2).

### DW-392: [구 #92] **sold 매물 DELETE는 계속 허용** — 수정은 막고 삭제는 여는 비대칭

origin: 장부 통합 이관(구 docs/tech-debt.md #92) — 원출처: 2026-07-21 코드리뷰 등재, 🟡 조건부
location: `supabase/migrations/0002_listings.sql:117`(`listings_delete_own` — status 조건 없음)
severity: high
reason: 판매자가 자기 매물을 지우는 것은 원래 허용된 동작이고, 거래 내역 보존이 아직 요구사항으로 명시된 적이 없어 오늘은 무해하다.
trigger: 거래 내역·정산이 요구사항이 되는 시점(#20과 함께 본다).
status: open

- **위치:** `supabase/migrations/0002_listings.sql:117`(`listings_delete_own` — status 조건 없음)
- **내용:** `0015`의 목적이 *"거래가 끝난 매물의 정보 변경 방지"*인데, 판매자는 그 매물을 **통째로 지울 수 있다.** 지우면 `/admin/transactions`(`status='sold'` 조회)의 거래 내역이 사라지고 `chat_rooms`·`listing_images`도 CASCADE로 함께 사라진다 — 수정보다 파괴적이다. 이 비대칭이 `0015` 주석 어디에도 언급되지 않는다.
- **지금 무해한 이유:** 판매자가 자기 매물을 지우는 것은 원래 허용된 동작이고, 거래 내역 보존 요구사항이 아직 명시된 적 없다(`sold_at` 미구현 = #20과 같은 축).
- **트리거:** 거래 내역·정산이 요구사항이 되는 시점(#20과 함께 본다).

### DW-393: [구 #93] `status <> 'sold'`는 화이트리스트가 아니라 **블랙리스트**다

origin: 장부 통합 이관(구 docs/tech-debt.md #93) — 원출처: 2026-07-21 코드리뷰 등재, 🟡 조건부
location: `supabase/migrations/0015_listings_update_not_sold.sql:28`
severity: high
reason: `0002`의 CHECK 제약이 `on_sale`/`sold` 두 값만 허용해 3번째 상태가 아직 존재할 수 없으므로 오늘은 무해하다.
trigger: `listings.status`에 값을 추가하는 마이그레이션. **그 마이그가 이 항목을 함께 본다.**
status: open

- **위치:** `supabase/migrations/0015_listings_update_not_sold.sql:28`
- **내용:** 조건이 *"sold가 아니면 통과"*라, 3번째 상태(`reserved`·`hidden` 등)가 추가되면 **새 상태는 자동으로 수정 허용**이 된다. `status = 'on_sale'`(화이트리스트)이었다면 새 상태는 기본 차단이 된다.
- **지금 무해한 이유:** `0002`의 CHECK가 `on_sale`/`sold` 두 값만 허용한다 — 3번째 상태가 존재할 수 없다.
- **트리거:** `listings.status`에 값을 추가하는 마이그레이션. **그 마이그가 이 항목을 함께 본다.**

### DW-394: [구 #94] 백필 스크립트가 **RLS 롤로 바뀌면 sold 8건이 조용히 누락**된다

origin: 장부 통합 이관(구 docs/tech-debt.md #94) — 원출처: 2026-07-21 코드리뷰 등재, 🟡 조건부
location: `api/scripts/backfill_embeddings.py:94` × `0015_listings_update_not_sold.sql:28`
severity: high
reason: 백필 스크립트가 현재 테이블 소유자 연결(RLS 우회)을 쓰고 있는 동안은 무해하다.
trigger: 백필 접속을 앱 롤로 바꾸거나 PostgREST 경로로 옮길 때.
status: open

- **위치:** `api/scripts/backfill_embeddings.py:94` × `0015_listings_update_not_sold.sql:28`
- **내용:** 백필은 `where embedding is null` 전체(sold 포함)를 돌며 UPDATE한다. 지금은 `DATABASE_URL`이 테이블 소유자 연결이라 RLS를 우회하지만, 이 접속이 `authenticated`·앱 롤로 바뀌거나 같은 백필을 PostgREST 경로로 옮기면 **sold 매물은 에러 없이 0행**이 된다. **RLS 거부는 예외가 아니라 0행이라서**, 스크립트의 *"N건 적재 완료"* 출력은 그대로 나오고 아무도 눈치채지 못한다.
- **지금 무해한 이유:** 소유자 연결 유지 중.
- **트리거:** 백필 접속을 앱 롤로 바꾸거나 PostgREST 경로로 옮길 때.

### DW-416: [구 #116] 찜 실패 토스트가 전역 인프라 없이 `WishButton` 로컬 transient로만 존재한다

origin: 장부 통합 이관(구 docs/tech-debt.md #116) — 원출처: 2026-07-22 Story 10.5 등재, 🟡 조건부
location: `web/src/components/listings/WishButton.tsx`(로컬 `useState` + `setTimeout` 자동 소멸)
severity: high
reason: 찜 실패 알림의 소비처가 `WishButton` 한 곳뿐이라 전역 토스트 인프라 없이 로컬 구현으로도 아직 중복·drift가 없다.
trigger: 2번째 소비처가 생기는 시점 — 그때 `WishButton`의 로컬 토스트 로직을 공용 `Toast`/`useToast` primitive로 승격하고 두 소비처가 그걸 같이 쓴다.
status: open

- **위치:** `web/src/components/listings/WishButton.tsx`(로컬 `useState` + `setTimeout` 자동 소멸)
- **내용:** 이 레포엔 토스트 인프라가 전무했다(`role="alert"` 인라인만 존재). 찜 실패 알림이 첫 소비처인데, 전역 `sonner` 등 라이브러리를 새로 들이는 대신(A2 — 첫 소비처는 로컬로 충분) `WishButton` 내부에 `role="status"` + `setTimeout(3000ms)` 자동 소멸로 최소 구현했다. 다른 화면(예: 채팅 전송 실패)이 같은 방식의 "조용한 알림"을 필요로 하면 지금은 각자 또 로컬로 구현해야 한다 — 공용 primitive가 없다.
- **지금 무해한 이유:** 소비처가 1곳뿐이라 중복·drift가 아직 없다.
- **트리거:** 2번째 소비처가 생기는 시점 — 그때 `WishButton`의 로컬 토스트 로직을 공용 `Toast`/`useToast` primitive로 승격하고 두 소비처가 그걸 같이 쓴다.

### DW-417: [구 #117] 찜 목록의 "삭제된 매물" 배지는 구조적으로 도달 불가 — UX-DR20 원문의 절반만 실현

origin: 장부 통합 이관(구 docs/tech-debt.md #117) — 원출처: 2026-07-22 Story 10.5 등재, 🟡 조건부
location: `web/src/lib/wishlist.ts`(`isWishedListingBlocked`) · `supabase/migrations/0018_wishlists.sql`(FK `on delete cascade`)
severity: high
reason: 하드삭제 후에도 찜 관계를 남기고 삭제 배지를 보여주려면 매물 제목 등을 저장하는 스냅샷 컬럼이 필요한데, 이는 epic이 정한 스키마 최소화·마이그레이션 additive 원칙에 반해 지금은 구현하지 않는다.
trigger: "삭제된 매물도 찜 이력에 남기고 싶다"는 요구가 명시적으로 생기는 시점(스냅샷 컬럼 설계가 별도 스토리로 필요).
status: open

- **위치:** `web/src/lib/wishlist.ts`(`isWishedListingBlocked`) · `supabase/migrations/0018_wishlists.sql`(FK `on delete cascade`)
- **내용:** UX-DR20 원문은 찜 목록에 "판매완료"·"삭제된 매물" 두 배지를 나열하지만, epic이 지정한 PK(`user_id, listing_id`)는 두 컬럼 다 NOT NULL이라 `listing_id`에 `on delete set null`을 쓸 수 없다. `restrict`는 판매자의 매물 삭제(FR6)를 막아 부적합하므로, 레포 관례대로 `on delete cascade`가 유일한 정합적 선택이다 — 그 결과 매물이 하드삭제되면 그 찜 행도 함께 사라져 **찜 목록에 "삭제된 매물" 상태로 남는 행 자체가 생기지 않는다.** 남는 회색 케이스는 sold 하나뿐이다(`isWishedListingBlocked`가 처리).
- **지금 무해한 이유:** 사용자 경험상 손실이 없다 — 매물이 지워지면 찜 목록에서도 조용히 사라질 뿐, "삭제된 매물"이라는 걸 알려주지 않는 것뿐이다(빈 배지보다 나쁘지 않다).
- **왜 안 고치나(A2):** "하드삭제 후에도 찜 관계를 남기고 삭제 배지를 보여준다"를 구현하려면 매물 제목 등을 저장하는 스냅샷 컬럼이 필요한데, 이는 epic이 지정한 스키마 최소화·마이그레이션 additive 원칙에 정면으로 반한다(Story 10.5 spec Design Notes).
- **트리거:** "삭제된 매물도 찜 이력에 남기고 싶다"는 요구가 명시적으로 생기는 시점(스냅샷 컬럼 설계가 별도 스토리로 필요).
- ✅ **cascade 실측 완료(2026-07-22, 코드리뷰 지적 반영, B4).** 위 "삭제되면 찜 행도 함께 사라진다"는 선언이었을 뿐 측정 기록이 없었다. 로컬 Supabase에서 트랜잭션으로 확인: 전용 매물 1건 insert → 그 매물을 찜(wishlists 1건 insert) → **삭제 전** `wishlists` 조회 1행 → 매물 하드 `delete` → **삭제 후** 같은 조건 조회 **0행**(cascade로 실제로 사라짐 확인) → rollback으로 부작용 없이 원복.

### DW-313: [구 #13] AI 단위 정규화·차형 매핑 결정론적 단위테스트 부재

origin: 장부 통합 이관(구 docs/tech-debt.md #13) — 원출처: (표기 없음)
location: `api/tests/`
severity: medium
reason: 3천만원→price 상한, 세단→body_type 매핑 같은 단위·차형 정규화 근거가 LLM 프롬프트와 라이브 호출 1회에만 존재해, 프롬프트가 바뀌면 조용히 깨질 수 있다.
status: open

- **위치:** `api/tests/`
- **내용:** "3천만원→price≤30000000", "세단→body_type IN(...)" 근거가 LLM 프롬프트 + 라이브 1회에만 존재. 프롬프트 변경 시 조용히 깨질 수 있음.
- **해소:** LLM 출력을 모킹한 정규화·매핑 회귀 테스트 추가.

### DW-314: [구 #14] FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버

origin: 장부 통합 이관(구 docs/tech-debt.md #14)
location: `api/tests/test_auth.py`
severity: medium
reason: 200 테스트가 `sql_rag_node`를 통째로 monkeypatch하여, 실제 0건→`_ANSWER_EMPTY`(FR17) 경로와 `body_type IN(...)` SQL의 가드 통과가 단위테스트로 미확인 상태다.
status: open

- **위치:** `api/tests/test_auth.py`
- **내용:** 200 테스트가 `sql_rag_node`를 통째로 monkeypatch → 실제 0건→`_ANSWER_EMPTY`(FR17) 경로와 `body_type IN(...)` SQL의 가드 통과가 단위테스트로 미확인.
- **해소:** 노드 내부 분기·가드 IN-절 통과 케이스 테스트 보강.

### DW-315: [구 #15] LIMIT 비정수형 처리 미흡

origin: 장부 통합 이관(구 docs/tech-debt.md #15)
location: `api/app/db/sql_guard.py:129`
severity: low
reason: temp=0라 발생 가능성 낮고 대부분 fail-safe이다.
status: open

- **위치:** `api/app/db/sql_guard.py:129`
- **내용:** `\blimit\s+(\d+)`가 `LIMIT 0`(오해성 0건)·`LIMIT -5`·`LIMIT (10)`·`OFFSET`-only를 정상 인식 못 함. temp=0라 발생 가능성 낮고 대부분 fail-safe.
- **해소:** LIMIT 정규화/하한 검증 강화.
- 📅 **예약됨: `13-1-sql-guard-하이브리드-정비-g2-baseline`** (backlog).

### DW-316: [구 #16] 가이드 RAG 유사도 임계값(거리 컷오프) 없음

origin: 장부 통합 이관(구 docs/tech-debt.md #16)
location: `api/app/graph/doc_rag_node.py:64-68`
severity: low
reason: 가이드 검색이 거리와 무관하게 항상 최근접 1건(`ORDER BY embedding <=> q LIMIT 1`)만 가져와, 의미상 동떨어진 가이드도 "근거"로 첨부돼 오도할 수 있다.
status: open

- **위치:** `api/app/graph/doc_rag_node.py:64-68`
- **내용:** 가이드 검색이 거리와 무관하게 항상 최근접 1건(`ORDER BY embedding <=> q LIMIT 1`) → 의미상 동떨어진 가이드도 "근거"로 첨부돼 오도 가능.
- **해소:** 코사인 거리 컷오프(`WHERE embedding <=> q < threshold`) 적용. (4.5 answer_node 소관으로 명시됨)
- 📅 **예약됨: `13-6-가이드-문서-content-활용-거리-컷오프`** (backlog).

### DW-317: [구 #17] Flutter **Riverpod 컨트롤러** 단위 테스트 부재

origin: 장부 통합 이관(구 docs/tech-debt.md #17) — 원출처: Epic 7 이월
location: `app/lib/features/**/` 의 Riverpod 컨트롤러
severity: medium
reason: 전역 Supabase 의존 때문에 컨트롤러 계층은 단위 테스트를 못 쓰고 live 스모크로 갈음했으며, `_bmad-output/project-context.md` 규칙 12가 "컨트롤러 로직이 복잡해질 때"라는 조건부로 이미 관리 중인 항목이라 신규 부채가 아니다.
trigger: `_bmad-output/project-context.md` 규칙 12가 이미 조건부로 규정 — *"컨트롤러 로직이 복잡해질 때"*. 즉 **신규 부채가 아니라 이미 관리 중인 조건부 항목**이다.
status: open

- **위치:** `app/lib/features/**/` 의 Riverpod 컨트롤러
- **내용:** 전역 Supabase 의존 때문에 **컨트롤러 계층**은 단위 테스트를 못 쓰고 live 스모크로 갈음했다.
- ⚠️ **범위 정정 (2026-07-15 회고 — 실측)**: Epic 7 회고의 *"컨트롤러 단위 테스트 부재"* 라는 표현이 **"Flutter에 테스트가 없다"로 오독됐다.** 실제로는 `app/test/`에 **10개 파일 · 테스트 77개**가 있다(`listing_form_test` 17 · `listing_filters_test` 11 · `listing_model_test` 12 · `ai_search_test` 8 · `widget_test` 8 · `chat_model_test` 6 · `listing_error_test` 4 · `chat_dedupe_test` 4 · `listing_form_edit_test` 5 · `number_format_test` 2). 없는 건 **`ProviderContainer` 기반 컨트롤러 테스트뿐**이고, 순수 함수·모델·파싱·검증 로직은 커버돼 있다.
- **트리거:** `_bmad-output/project-context.md` 규칙 12가 이미 조건부로 규정 — *"컨트롤러 로직이 복잡해질 때"*. 즉 **신규 부채가 아니라 이미 관리 중인 조건부 항목**이다.
- **해소:** Supabase를 리포지토리로 감싸 fake 주입 → `ProviderContainer.test`로 폴링 상태 전이·필터 조합 검증.

### DW-332: [구 #32] 누수 부재 테스트가 `psycopg_pool`의 비공식 보장에 의존

origin: 장부 통합 이관(구 docs/tech-debt.md #32) — 원출처: 8.4 리뷰 이월
location: `api/tests/test_readonly.py`
severity: medium
reason: `psycopg_pool`의 "동일 물리 커넥션 재사용"은 라이브러리가 공식 보장하는 계약이 아니라, 헬스체크 등으로 커넥션이 교체되면 테스트가 잘못된 이유로 통과하거나 flaky해질 수 있다.
status: open

- **위치:** `api/tests/test_readonly.py`
- **내용:** `max_size=1`이 순차 재사용을 강제하긴 하나, **"동일 물리 커넥션 재사용"은 라이브러리가 공식 보장하는 계약이 아니다.** 헬스체크 등으로 커넥션이 교체되면 테스트가 **잘못된 이유로 통과**하거나 flaky해진다.
- **해소:** 롤 누수를 커넥션 동일성이 아닌 방식으로 단언(예: `SET LOCAL` 스코프 자체를 검증).

### DW-333: [구 #33] DSN 포트(`:6543`) 전제가 주석에만 있고 코드로 검증되지 않음

origin: 장부 통합 이관(구 docs/tech-debt.md #33) — 원출처: 8.4 리뷰 이월
location: `api/app/db/readonly.py` · `api/app/config.py`
severity: medium
reason: `.env`가 실수로 `:5432`(세션 풀러)를 가리켜도 코드가 조용히 그대로 동작하며, `SET LOCAL`은 풀러 종류와 무관해 롤 누수는 재발하지 않고 의도한 성능 특성만 잃어 우선순위가 낮다.
status: open

- **위치:** `api/app/db/readonly.py` · `api/app/config.py`
- **내용:** `.env`가 실수로 `:5432`(세션 풀러)를 가리켜도 코드가 조용히 그대로 동작한다. `SET LOCAL`은 풀러 종류와 무관해 **롤 누수는 재발하지 않으나 의도한 성능 특성을 잃는다.** 우선순위 낮음.

### DW-334: [구 #34] anon 허용 테스트가 두 파일에 중복 — 약한 사본 포함

origin: 장부 통합 이관(구 docs/tech-debt.md #34) — 원출처: 8.5 리뷰 이월
location: `api/tests/test_auth.py:367-377` · `api/tests/test_ai_search.py:339-348`
severity: medium
reason: "인증 계약 테스트는 `test_auth.py` 소유"라는 파일 경계 결정이 선행돼야 해소할 수 있어 미뤘다.
status: open

- **위치:** `api/tests/test_auth.py:367-377` · `api/tests/test_ai_search.py:339-348`
- **내용:** `test_search_without_token_allowed_anon`가 동명·동일 monkeypatch로 양쪽에 있고, `test_ai_search.py` 사본은 `assert r.json()["listings"] == []` **본문 검증이 빠진 약한 버전**이라 응답 계약이 퇴행해도 초록으로 통과한다.
- **해소:** *"인증 계약 테스트는 `test_auth.py` 소유"* 라는 **파일 경계 결정이 선행**돼야 함. (8.5가 만든 중복이 아니라 pre-existing 구조를 갱신한 것)

### DW-335: [구 #35] 고아 `auth.users`(profiles 없음) 시 시드 재실행 중단

origin: 장부 통합 이관(구 docs/tech-debt.md #35) — 원출처: 2-5 리뷰 이월
location: `supabase/seed.sql:163-174`
severity: medium
reason: 손상 상태를 즉시 드러내는 의도된 fail-loud 동작이라, 자가복구 경로는 시드 자동화를 더 강화할 때 검토하기로 미뤘다.
status: open

- **위치:** `supabase/seed.sql:163-174`
- **내용:** 시드 계정이 `auth.users`엔 있으나 `profiles`가 없는 손상 상태에서 재실행하면 안전장치 `raise exception`이 전체 시드를 중단시킨다. **의도된 fail-loud**(조용한 실패보다 즉시 드러냄)지만 자가복구 경로는 없다.
- **해소:** 시드 자동화 강화 시 `profiles` 부재 시 직접 삽입하는 self-heal 경로 검토.

### DW-336: [구 #36] FocusTrap — 언마운트·숨김된 트리거로 복귀 시 조용히 no-op

origin: 장부 통합 이관(구 docs/tech-debt.md #36) — 원출처: 8.2 리뷰 이월
location: `web/src/components/ui/FocusTrap.tsx:243-246`
severity: medium
reason: 트리거 요소가 그 사이 DOM에서 제거·숨겨지면 `.focus()`가 조용히 아무 일도 안 해(크래시 없음, 포커스가 `<body>`로 남음) 즉시 문제로 드러나지 않는다.
trigger: 트리거가 리스트 아이템처럼 삭제될 수 있는 맥락에서 소비될 때.
status: open

- **위치:** `web/src/components/ui/FocusTrap.tsx:243-246`
- **내용:** 트랩이 닫힐 때 `triggerRef.current`로 포커스를 복귀시키는데, 그 요소가 그 사이 DOM에서 제거·숨겨졌으면 `.focus()`가 **조용히 아무 일도 안 한다**(크래시 없음, 포커스가 `<body>`로 남음).
- **트리거:** 트리거가 리스트 아이템처럼 삭제될 수 있는 맥락에서 소비될 때. **해소:** 폴백(컨테이너·상위 랜드마크로 이동).

### DW-337: [구 #37] FocusTrap — `open=false`일 때 `children` 전체 언마운트, 내부 상태 소실

origin: 장부 통합 이관(구 docs/tech-debt.md #37) — 원출처: 8.2 리뷰 이월
location: `web/src/components/ui/FocusTrap.tsx:249`
severity: medium
reason: 닫히면 `null`을 반환해 자식을 완전히 언마운트하며, 폼 입력값·스크롤 위치가 매번 사라지는 동작이 문서화돼 있지 않다.
trigger: 실제 모달/바텀시트를 붙이는 Epic 11.
status: open

- **위치:** `web/src/components/ui/FocusTrap.tsx:249`
- **내용:** 닫히면 `null`을 반환해 자식을 완전히 언마운트한다. **폼 입력값·스크롤 위치가 매번 사라지는 동작이 문서화돼 있지 않다.**
- **트리거:** 실제 모달/바텀시트를 붙이는 Epic 11. **해소:** 의도와 맞는지 확인하고, 상태 보존이 필요하면 CSS로 숨기는 방식으로.

### DW-338: [구 #38] ErrorState — `tone="danger"`가 텍스트 색만 바꾸고 버튼은 톤 무관 동일

origin: 장부 통합 이관(구 docs/tech-debt.md #38) — 원출처: 8.2 리뷰 이월
location: `web/src/components/ui/ErrorState.tsx:167-179`
severity: medium
reason: cosmetic 이슈로, 파괴적/위험 에러와 일반 에러가 버튼 상으로는 시각 구분되지 않을 뿐이라 소비 화면이 생길 때 검토하기로 미뤘다.
status: open

- **위치:** `web/src/components/ui/ErrorState.tsx:167-179`
- **내용:** cosmetic. 파괴적/위험 에러와 일반 에러가 **버튼 상으로는 시각 구분되지 않는다.** `tone="danger"`를 쓰는 소비 화면이 생기면 버튼도 톤 분기할지 검토.

### DW-339: [구 #39] 단일 `error` useState를 `handleComplete`·`handleDelete`가 공유

origin: 장부 통합 이관(구 docs/tech-debt.md #39) — 원출처: 2-4 리뷰 이월
location: `web/src/app/(user)/sell/ListingActions.tsx`
severity: medium
reason: cosmetic 이슈이며 한 행에 버튼이 모여 있어 실사용 혼선은 작아, 핸들러가 더 늘면 분리를 검토하기로 미뤘다.
status: open

- **위치:** `web/src/app/(user)/sell/ListingActions.tsx`
- **내용:** cosmetic. 각 핸들러 시작 시 `setError(null)`로 초기화하지만 성공 경로엔 명시 초기화가 없다. 한 행에 버튼이 모여 있어 실사용 혼선은 작음. 핸들러가 더 늘면 분리 검토.

### DW-341: [구 #41] `deployment-runbook.md` §8 사각지대 목록에 `paths:` 필터 누락

origin: 장부 통합 이관(구 docs/tech-debt.md #41) — 원출처: 문서 부채
location: `docs/deployment-runbook.md` §8
severity: medium
reason: §8이 스스로 "이 목록의 정직함이 곧 게이트 신뢰의 근거이므로, 빠뜨린 항목은 단순 누락보다 비싸다"라 선언해 놓고 두 항목(#22·#29)을 정작 빠뜨렸다.
status: open

- **위치:** `docs/deployment-runbook.md` §8
- **내용:** §8은 스스로 *"이 목록의 정직함이 곧 게이트 신뢰의 근거이므로, 빠뜨린 항목은 단순 누락보다 비싸다"*(:116)라고 선언해 놓고, **"이 CI는 마이그·스크립트를 안 건드리는 push엔 존재하지도 않는다"**(#29)를 빠뜨렸다. #22(`--single-transaction`이 마이그 작성 방식을 몰래 제약)도 미기재.
- **해소:** §8에 두 항목 추가. **#22·#29와 함께 처리.**

> ℹ️ **구 #42(개발 가이드라인 문서가 레포 밖)는 닫혔다 (2026-07-16).** 그 문서의 교훈이 상위 `workspace/CLAUDE.md`(표준 작업 지침 B8·B9 등)에 녹여져 정본이 됐다. 레포 밖에 있는 건 결함이 아니라 **의도** — 이 프로젝트가 아니라 다음 프로젝트용 범용 교훈이기 때문이다.

### DW-343: [구 #43] `listing_images` 10장 상한이 UPDATE로 우회된다

origin: 장부 통합 이관(구 docs/tech-debt.md #43) — 원출처: 9.1 리뷰 이월 — `0013`이 좁혔으나 **미해소**
location: `supabase/migrations/0012_listing_images.sql:166-168`(트리거가 `before insert` 전용) + `:228-241`(`listing_images_update_own`이 `listing_id` 변경 허용)
severity: medium
reason: 업로더 UI(9.3)가 아직 없어 `listing_images`에 행을 넣는 경로 자체가 없어 오늘은 무해하다.
trigger: 9.3 업로더가 UPDATE 경로를 여는 순간.
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:166-168`(트리거가 `before insert` 전용) + `:228-241`(`listing_images_update_own`이 `listing_id` 변경 허용)
- **내용:** 판매자가 자기 매물끼리 `listing_id`를 옮겨 상한을 넘긴다. **`0013`이 절반만 막았다 — 실측으로 확인:**
  - `listing_id`**만** 바꾸는 UPDATE → **거부됨**(`0013`의 경로 트리거가 경로 2번째 세그먼트 불일치를 잡는다).
  - `storage_path`를 **함께** 고치면 → **통과.** 실측: B를 10장으로 채운 뒤 `update ... set listing_id=B, storage_path='{seller}/B/a1.jpg'` → **B가 11장**. 트리거를 만족시키며 우회된다.
  - ⚠️ **"0013이 부수적으로 해결했다"고 적지 마라** — 재보고 확인한 사실이다(B4).
- **오늘 무해한 이유:** 업로더 UI(9.3)가 아직 없어 `listing_images`에 행을 넣는 경로 자체가 없다(원격 실측: 0행).
- **트리거:** 9.3 업로더가 UPDATE 경로를 여는 순간.
- **해소:** 트리거를 `before insert or update of listing_id`로 넓힌다(한 줄). **AC2가 "BEFORE INSERT 트리거로 강제"라 수단을 지정한 게 원인** — 스펙을 함께 고칠 것.
- **🔸 9.3 판정(2026-07-18) — 여전히 열려 있다.** 9.3은 이 항목이 지목한 **우회 경로를 열지 않았다**: 업로더는 `listing_id`를 바꾸는 UPDATE를 어디서도 하지 않는다(사진을 다른 매물로 옮기는 기능 없음). `listing_images`에 대한 UPDATE는 `sort_order`·`is_cover`뿐이다. **그러나 트리거 자체는 고치지 않았다** — 즉 이 구멍은 그대로다. 9.3은 "밟지 않았다"이지 "메웠다"가 아니다.

### DW-345: [구 #45] 관리자가 sold 매물 사진의 **바이너리**를 못 본다

origin: 장부 통합 이관(구 docs/tech-debt.md #45) — 원출처: 9.1 리뷰 이월
location: `supabase/migrations/0012_listing_images.sql:277-288` (읽기 정책에 `is_admin()` 분기 없음)
severity: medium
reason: `listing_images_select_admin`으로 메타행은 보이지만 `storage.objects` 읽기 정책에 `is_admin()` 분기가 없어 서명 URL 발급이 안 돼, 관리자 매물상세에서 사진이 깨진다.
trigger: 9.4·9.5가 카드/갤러리를 만들어 관리자 화면이 실제로 사진을 렌더할 때. **선행 확인: Epic 6 관리자 매물상세가 사진을 렌더하는가?**
status: done 2026-07-29
resolution: Story 9.0이 해소 — 0014_listing_images_public_bucket.sql이 읽기 정책을 authenticated 단일 정책 + is_admin()으로 전환

- **위치:** `supabase/migrations/0012_listing_images.sql:277-288` (읽기 정책에 `is_admin()` 분기 없음)
- **내용:** `listing_images_select_admin`(`0012:215`)으로 **메타행은 보이는데** `storage.objects`는 **0건** → 서명 URL 발급 불가 → Epic 6 관리자 매물상세(`/admin/listings/[id]`, sold 포함)에서 깨진 이미지. 도커 실측 확인. **메타는 보이고 파일은 안 보이는 비대칭.**
- **`0012:276` 주석이 댄 이유("anon이 `is_admin()`에 걸리면 열람 전체가 깨진다")는 옳지만 결손을 정당화하지 못한다** — `to authenticated` 별도 정책을 하나 더 두면 해소되고, 같은 파일의 `listing_images`가 정확히 그 분리 패턴을 쓴다. 제약이 아니라 선택이었다.
- **트리거:** 9.4·9.5가 카드/갤러리를 만들어 관리자 화면이 실제로 사진을 렌더할 때. **선행 확인: Epic 6 관리자 매물상세가 사진을 렌더하는가?**
- **해소:** `storage.objects` 읽기 정책을 anon용/authenticated용으로 나누고 authenticated 쪽에 `or public.is_admin()` 추가.
- **✅ 해소 (Story 9.0, 2026-07-19 — `0014`):** 정확히 그렇게 했다. 읽기 정책을 `to authenticated` 단일 정책으로 바꾸고 `split_part(name,'/',1) = auth.uid()::text **or public.is_admin()**`를 넣었다(anon은 이 정책 대상이 아니게 되어 `0012:276` 주석이 걱정하던 문제가 성립하지 않는다 — 공개 버킷의 익명 읽기는 `/object/public/` 경로가 담당하고 RLS를 타지 않는다).
  - **실측(2026-07-19, 원격):** 관리자 세션으로 `storage.objects` 조회 **1건**(전 0건). 비소유자 0건·anon 0건으로 권한이 새지 않는 것도 함께 확인.

### DW-346: [구 #46] 고아 Storage 오브젝트 — 매물 삭제 시 파일이 영구 잔존

origin: 장부 통합 이관(구 docs/tech-debt.md #46) — 원출처: 9.1 리뷰 이월
location: `supabase/migrations/0012_listing_images.sql:120` (`on delete cascade`) — `storage.objects`를 정리하는 트리거·FK 부재
severity: medium
reason: 고아가 `storage_path` 위조의 표적을 상시 공급하던 진짜 위험은 `0013`이 위조를 막아 사라졌고, 남은 건 용량 누적뿐이라 위험도를 하향했다.
trigger: 사진이 실제로 쌓이기 시작할 때(9.3·9.7). 데모 규모(매물 100건×10장)에선 무해.
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:120` (`on delete cascade`) — `storage.objects`를 정리하는 트리거·FK 부재
- **내용:** 매물이 지워지면 `listing_images` 행은 cascade로 **조용히** 사라지고 버킷의 바이너리는 남는다. 아무도 열 수 없지만 용량은 계속 먹는다(과금).
- **위험도 하향(2026-07-16):** 원래 이 항목의 진짜 위험은 **고아가 `storage_path` 위조의 표적을 상시 공급**하는 것이었으나, `0013`이 위조를 막아 **그 축은 사라졌다.** 남은 건 용량 누적뿐.
- **#27이 cascade의 침묵을 길게 논하면서 논한 대상은 "시드 재실행 시 행 유실"뿐이고 고아 파일은 어디에도 없었다** — 대장이 하나라면 여기 있어야 한다(B8).
- **트리거:** 사진이 실제로 쌓이기 시작할 때(9.3·9.7). 데모 규모(매물 100건×10장)에선 무해.
- **🔸 실제 발현 1건 (2026-07-18, 9.3 Task 0):** `listing-images` 버킷에 지울 수 없는 프로브 객체 2개가 남았다 — `12dfba00-…/probe-a.png`, `12dfba00-…/x/y.png`(각 70바이트). 경로가 3세그먼트 계약을 만족하지 않아 `listing_images` 행을 붙일 수 없고(경로 트리거가 거부), **행이 없으면 소유자에게도 안 보여 Storage API로 못 지운다**(#51 규명 결과). SQL 직접 삭제도 `storage.protect_delete()`가 차단(`42501`). **지우려면 Supabase 대시보드(=`service_role` 경로)뿐이다** — 사용자 조치 항목. 이 사례가 이 항목의 비용을 구체화한다: 고아는 "용량만 먹는" 게 아니라 **정상 권한으로는 회수 불가**다.
- **해소:** `listing_images` AFTER DELETE 트리거에서 오브젝트 삭제, 또는 주기적 정리. **DB에서 파일을 지우려면 storage 확장 의존이 생기므로 범위를 보고 판단할 것.**
- **🔻 위험도 대폭 하향 — "회수 불가"가 사라졌다 (Story 9.0, 2026-07-19 — `0014`):** 이 항목의 비용 대부분은 *고아를 **정상 권한으로 지울 수 없다***는 것이었고, 그 원인은 `storage.objects` SELECT 정책이 `listing_images` 행과 조인해야 참이 된다는 점이었다. `0014`가 정책을 **경로 기반**으로 바꿔 **행이 없어도 소유자·관리자에게 보이고 지울 수 있다.**
  - **실측(2026-07-19, 원격):** 행 없는 고아 객체가 소유자 세션에 **0건 → 1건**으로 보임. 관리자도 1건. 비소유자·anon 0건.
  - **✎ 위 "실제 발현" 기록 정정:** 프로브 객체 **2개**라고 적혀 있었으나 2026-07-19 실측 시 버킷에 남은 객체는 `12dfba00-…/x/.emptyFolderPlaceholder` **1개**뿐이다. 그 사이 정리된 것으로 보이며, 어느 시점에 사라졌는지는 기록이 없다 — **당시 기록이 지금 사실과 다르다는 것만 적어 둔다.**
  - **남은 것:** 고아가 *생기는* 경로 자체는 그대로다(#56 동시 편집 실패 등). 다만 이제는 **회수 가능한 용량 누적**이지 영구 손실이 아니다. 관리자 매물 삭제가 사진을 안 지우던 구멍은 9.0에서 **막았다**(아래 #66).

### DW-347: [구 #47] `listing_images` 설계 공백 4건 — 소비처가 9.3~9.5

origin: 장부 통합 이관(구 docs/tech-debt.md #47) — 원출처: 9.1 리뷰 이월
location: `supabase/migrations/0012_listing_images.sql`
severity: medium
reason: 전부 소비처가 아직 없어 지금 결정하면 재작업 위험이 있어, 그 화면을 만들 때 함께 정하기로 했다.
trigger: 9.3(업로더) · 9.4(카드) · 9.5(갤러리).
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql`
- **내용:** 전부 **소비처가 아직 없어** 지금 결정하면 재작업 위험. 그 화면을 만들 때 함께 정한다.
  1. **대표사진 교체가 단일 UPDATE로 실패**(`:138-139`) — 부분 유니크 인덱스는 DEFERRABLE 불가라 자연스러운 `update ... set is_cover=(id=:new) where listing_id=:L`이 `duplicate key`로 죽는다(도커 실측). **클라가 반드시 2문장(먼저 전부 false, 그 다음 true)으로 짜야 하는데 그 제약이 어디에도 없다.** → 9.3·9.5 착수 시 `conventions.md §10`에 명시.
  2. **`sort_order` tie-break 부재**(`:122`) — 전부 기본값 `0`이면 `order by sort_order` 결과가 매 쿼리 달라진다. → `unique(listing_id, sort_order)` 또는 `order by sort_order, id` 규약.
  3. **10장 초과 에러에 `errcode` 없음**(`:159`) — SQLSTATE가 일반 `P0001`이라 클라가 **한국어 메시지 문자열 매칭**으로만 구별한다. 메시지를 다듬는 순간 조용히 깨진다. → `raise ... using errcode='...'`.
  4. **대표 0장 허용**(`:123`) — `is_cover default false`라 대표 없는 매물이 정상 상태. UX D3 카드가 표시할 썸네일이 없다. 의도인지 불명 → 9.4가 카드를 만들 때 결정(0장 허용이면 §10에 명시).
- **트리거:** 9.3(업로더) · 9.4(카드) · 9.5(갤러리).
- **🔸 9.3 판정(2026-07-18) — 4건 중 3건은 클라 규약으로 다뤘고, DB는 그대로다:**
  1. **대표 교체 2문장** → ✅ **계약으로 승격.** `docs/conventions.md §10.1`에 명문화 + `photo-sync.ts`가 그 순서로 구현(이유를 코드 주석에 남김). *단 DB는 여전히 단일 UPDATE를 허용하므로, 규약을 모르는 다음 소비처는 같은 함정을 밟는다.*
  2. **`sort_order` tie-break 부재** → 🔸 **회피만 함.** 업로더가 항상 연속 정수 0..n-1로 다시 매기고, 읽는 쪽은 `order by sort_order, id`로 2차 정렬한다. **`unique(listing_id, sort_order)` 제약은 추가하지 않았다** — 순서 재배치 중 중간 상태에서 충돌하기 때문. 구멍은 남아 있다.
  3. **10장 초과 `errcode` 없음** → ⚪ **손대지 않음.** 대신 클라가 먼저 막아 이 예외에 도달하지 않게 했다(AC9). **한국어 메시지 매칭에 의존하는 코드는 새로 만들지 않았다.**
  4. **대표 0장 허용** → 🔸 **클라가 정상 경로에서만 보장 — 판정 정정(코드리뷰 2026-07-19).** 원래 "✅ 클라가 보장"은 해피패스 1회 관찰만 근거였고, 실제로는 아래 3가지가 빠져 있었다(전부 패치 완료, `photo-sync.test.ts`로 회귀 고정):
     - `rowId`를 저장 후 되돌려주지 않아 재제출이 같은 사진을 다시 INSERT하려다 실패하고, 그 실패 분기가 방금 저장한 오브젝트를 지웠다(역고아).
     - 오브젝트 삭제가 실패해도 `listing_images` 행을 지워 버려, `#46`이 막으려던 영구 고아가 삭제 경로에서도 발생했다.
     - 중간 INSERT 실패 시 `sort_order`에 구멍이 남고, 대표가 `sort_order=0`이 아닌 행에 붙었다(이 스토리의 핵심 불변식 위반).
     
     **✎ 2026-07-19 코드리뷰 2차 — 위 "전부 패치 완료"가 과했다.** 세 번째 항목(대표가 `sort_order=0`이 아닌 행에 붙음)은 **INSERT 갈래만** 고쳐져 있었고, **기존 행의 `sort_order` UPDATE가 실패하는 갈래에서 같은 결함이 그대로 재현**됐다(리뷰가 재현 실행으로 증명). 아울러 아래 2건이 추가로 발견돼 함께 패치됐다:
     - 오브젝트 삭제에 실패한 사진을 목록 **맨 앞**에 되돌려 놓아, 사용자가 **지우려던** 사진이 `sort_order=0` + `is_cover=true`를 받았다.
     - 행 DELETE·`is_cover` 두 UPDATE에 `.select()`가 없어 **0행(RLS 차단)을 성공으로** 처리했다 — 특히 대표 지정 0행은 직전 리셋과 겹쳐 조용히 "대표 0장"을 만들었다.

     **해소 방식:** 대표를 4단계에서 재계산하지 않고 **3단계에서 실제로 `sort_order=0`을 받은 행**을 기억해 그 행에만 건다(같은 값을 두 군데서 따로 계산하지 않는다). 회귀는 `photo-sync.test.ts`에 red 확인 후 고정했고, **가짜 Supabase가 `where` 조건까지 기록하도록 하네스를 고쳤다** — 전엔 `.eq('storage_path', …)`·`.eq('listing_id', …)`를 지워도 전 테스트가 통과했다(계약을 안 지키는 검사였다).

     **✅ 2026-07-19 Story 9.4 — 4번 항목("대표 0장 허용")은 닫는다.** 카드를 만들며 결정했다: **대표 0장은 정상 상태이고, 읽는 쪽은 `sort_order` 첫 행을 대표로 본다**(`is_cover` 미사용). `conventions.md §10.2`에 명문화했고 `coverImages.test.ts`가 강제한다. 사진 0장 매물은 "사진 준비중" 플레이스홀더로 그린다. *(1·2·3번 항목은 그대로 — DB는 여전히 단일 UPDATE를 허용하고, `unique(listing_id, sort_order)`도 `errcode`도 없다.)*

     **남은 한계(패치 후에도 그대로):** `is_cover` 2문장(false→true) 중 리셋 문장의 DB 호출 자체가 실패하면(네트워크 등) `PhotoSyncResult.warnings`로 사용자에게 알릴 뿐 자동 재시도·롤백은 하지 않는다 — 그 세션에서 대표 0장이 남을 수 있다. *DB 기본값(`false`)도 그대로라 다른 경로로 들어온 행은 여전히 대표 0장이 될 수 있다.*

### DW-348: [구 #48] `listing_images`의 FR11 강제가 **실행되는 검사 없이 약속으로만** 존재

origin: 장부 통합 이관(구 docs/tech-debt.md #48) — 원출처: 9.1 리뷰 이월
location: `supabase/migrations/0012_listing_images.sql:253-254` (`listing_images_ai_readonly_select ... using (true)`)
severity: medium
reason: `sql_guard`의 `ALLOWED_COLUMNS`가 `listings` 단일 테이블이라 현재 `listing_images`를 JOIN할 수 없고, `ai_readonly`는 `nologin` 롤이라 사용자 대면 노출이 아니어서 오늘은 무해하다.
trigger: **Story 9.6**(api가 `listing_images`에서 대표 사진 `storage_path`를 읽는 곳). 누군가 `sql_guard`에 테이블을 하나 더 허용하는 순간.
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:253-254` (`listing_images_ai_readonly_select ... using (true)`)
- **내용:** 이 정책은 **sold 매물의 사진 메타도 전부 연다. 이건 의도된 것이다** — 아키텍처 CR2가 확정했고 재논의 대상이 아니다. FR11 강제는 **api가 on_sale id로 스코프를 좁히는 데서** 일어난다.
- **그런데 그 강제가 지금 어디에도 실행되는 형태로 없다:**
  - 방어 ①"api가 on_sale id로 좁힌다" · 방어 ②"`sql_guard`가 `listing_images`와 JOIN하지 않는다" — **둘 다 Story 9.6에 대한 약속**이다.
  - 지금 `sql_guard`가 `listing_images`를 JOIN하지 못하게 막는 **검사는 0개**다. `0012:252` 주석이 *"sql_guard는 listings 단일 테이블을 유지하고 JOIN하지 않는다(9.6의 일)"*라 적혀 있을 뿐 — **주석은 계약이 아니다**(CLAUDE.md B9).
  - `conventions.md §6`은 sold가 *"AI SQL 포함 모든 경로"*에서 비노출이라 선언하고, 9.1이 그 §6에 storage RLS를 강제 지점으로 **추가**했다. 정작 ai 경로는 `using(true)`다.
- **오늘 무해한 이유:** `sql_guard`의 `ALLOWED_COLUMNS`가 `listings` 단일 테이블이라 현재 `listing_images`를 JOIN할 수 없다. `ai_readonly`는 **`nologin` 롤**이라 사용자가 직접 붙을 수 없고 api의 SELECT 전용 경로에서만 쓰인다 — **사용자 대면 노출이 아니다.**
- **트리거:** **Story 9.6**(api가 `listing_images`에서 대표 사진 `storage_path`를 읽는 곳). 누군가 `sql_guard`에 테이블을 하나 더 허용하는 순간.
- **해소 (9.6 AC로 심을 것 — B5 "약속은 문서 말고 인수조건으로"):** `sql_guard`가 `listing_images`를 JOIN하면 **실패하는 테스트 하나**. 주석 네 줄보다 그 검사 하나가 낫다.

</details>

### DW-349: [구 #49] 10장 트리거 동시성 경합 — **미측정**

origin: 장부 통합 이관(구 docs/tech-debt.md #49) — 원출처: 9.1 리뷰 이월
location: `supabase/migrations/0012_listing_images.sql:154-156` (`select count(*)`에 `for update`·advisory lock 부재)
severity: medium
reason: 리뷰의 도커 세션이 단일 커넥션이라 재현하지 못했다. 이 항목은 가설이며, 해소 전에 먼저 재봐야 한다(B4).
trigger: 9.3 업로더가 사진을 병렬 업로드할 때(현실적으로 닿는 경로 — 10장을 한꺼번에 올린다).
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:154-156` (`select count(*)`에 `for update`·advisory lock 부재)
- **내용:** Read Committed에선 미커밋 행이 안 보이므로 두 트랜잭션이 각각 9장을 보고 **둘 다 통과 → 11장**. 카운트-후-삽입에 직렬화 장치가 전무한 건 코드상 명백하다.
- **⚠️ 실측 아님:** 리뷰의 도커 세션이 단일 커넥션이라 **재현하지 못했다.** 이 항목은 **가설**이다 — 해소 전에 먼저 재라(B4 "선언 전에 실측하라").
- **트리거:** 9.3 업로더가 사진을 병렬 업로드할 때(현실적으로 닿는 경로 — 10장을 한꺼번에 올린다).
- **해소:** `listing_id`에 advisory lock, 또는 상한을 인덱스/제약으로 표현. **#43과 같은 자리에서 함께 볼 것.**
- **🔸 9.3 판정(2026-07-18) — 경합을 만들지 않는 것으로 **회피**했고, 가설은 **여전히 미측정**이다.** 업로더는 `listing_images` INSERT를 **순차(직렬)** 로 보낸다(`photo-sync.ts`, 계약은 `conventions.md §10.1`). 그래서 단일 사용자가 10장을 한꺼번에 올려도 동시 삽입이 발생하지 않는다. **단 (a) DB의 직렬화 장치는 여전히 0개이고, (b) 이 항목이 가설이라고 못 박은 "두 트랜잭션이 각각 9장을 보고 통과" 시나리오를 9.3도 재현 시도하지 않았다** — 두 클라이언트가 동시에 같은 매물에 올리는 상황(예: 두 탭)은 지금도 샐 수 있다. 여전히 **가설**로 남긴다.

### DW-350: [구 #50] 9.1 기록 누락 4건

origin: 장부 통합 이관(구 docs/tech-debt.md #50) — 원출처: 9.1 리뷰 이월 — 문서 부채, 지금 아무도 안 다침
location: n/a
severity: medium
reason: "내일 누군가 이걸 읽고 틀린 행동을 하는가?"(사용자 판단 기준, 2026-07-16)에 4건 모두 "아니오"라서 이월했다. 같은 리뷰의 다른 6건(모순·거짓 안전감)은 "예"라서 즉시 고쳤다.
trigger: 2번 → Story 9.2. 3번 → CI가 또 안 돌 때. 1·4번 → 프렐류드/§6을 다음에 건드릴 때.
status: open

- **판단 기준(사용자, 2026-07-16):** *"내일 누군가 이걸 읽고 틀린 행동을 하는가?"* — 아래 4건은 **아니오**라서 이월했다. 같은 리뷰의 다른 6건(모순·거짓 안전감)은 **예**라서 즉시 고쳤다.
1. **게이트 프렐류드의 false-**green** 축이 기록에 없다** [`scripts/migration-check-prelude.sql:69-94`] — 스토리 기록(Debug Log 3)은 false-**red**만 적었다(`owner` 등 미포함 컬럼). 그러나 원격 실측한 `storage.buckets.type (USER-DEFINED, **NOT NULL**)`을 스텁에서 뺐고, 스텁의 `objects.id default gen_random_uuid()`는 **실측 항목에 없는 추측**인데 AC7 시나리오가 실제로 그 기본값에 의존한다. **#24가 이미 이 실패 모드를 false green이라 명명해 뒀다 — 더 위험한 쪽이 안 적혔다.** (원격 apply가 성공했으므로 이 축의 구체 위험은 아직 실현되지 않았다.)
2. **✅ 9.2에서 정합화됨(2026-07-18) — `SIGNED_URL_TTL = 3600s`가 이제 실제로 구현됐다**[`web/src/lib/storage/index.ts`·`app/lib/core/supabase/storage_helper.dart`] **그런데도 잔존 창은 그대로 남아 있다:** 서명 URL은 **발급 시점에만** RLS를 검사하고 TTL(3600s) 동안 재검사하지 않아, `on_sale`→`sold` 전환 **직전** 발급된 대표 URL이 최대 1시간 생존한다. `docs/conventions.md` §6의 "모든 경로에서 비노출" 주장은 **이 축에선 성립하지 않는다**(데모 수용 한계 — §6에 교차참조 각주 추가함). 해소 방안(TTL 단축·서명 URL 무효화)은 이번 스토리에서 구현하지 않는다(A2, 별도 액션으로만 남김). **✅ 항목 무효화 (Story 9.0, 2026-07-19):** 서명 URL 자체가 없어졌다 — 버킷이 공개로 바뀌어 TTL·잔존 창 개념이 사라졌다. 이 축은 "1시간 뚫림"에서 **"명시 수용"**으로 대체됐다(`docs/conventions.md` §6.1). **역설적으로 이 항목이 전환의 결정적 근거였다** — 비공개+서명의 복잡도를 다 치르고도 이 창이 열려 있었기 때문이다.
3. **CI 미트리거의 원인이 미해결인데 "웹훅 유실"로 종결됐다** [`9-1-*.md` Debug Log 5] — 코드리뷰 실측: `56c47af`는 `supabase/migrations/**`와 `scripts/**`를 **둘 다** 건드려 `paths` 필터에 정확히 걸린다. 즉 경로 필터로는 설명되지 않으며, "웹훅 지연/유실"은 관측(run 부재 + Status Page 정상)과 **양립할 뿐 입증된 원인이 아니다.** 재발 시 같은 자리에서 또 6분을 태운다. **#41(런북 §8에 `paths:` 필터 누락)과 같은 자리에서 볼 것.**
4. **§6 괄호의 범위가 모호하다** [`docs/conventions.md` §6] — storage 문구를 추가한 뒤 원래 있던 *"(구현은 Epic 2~4, anon 경로는 Epic 8.5)"* 가 그대로 남아 **Epic 9 항목까지 포괄하는 것처럼** 읽힌다.
- **트리거:** 2번 → Story 9.2. 3번 → CI가 또 안 돌 때. 1·4번 → 프렐류드/§6을 다음에 건드릴 때.

### DW-351: [구 #51] `storage.objects` 인증 DELETE/LIST가 RLS 정책과 GRANT가 둘 다 맞는데도 403/빈 결과

origin: 장부 통합 이관(구 docs/tech-debt.md #51) — 원출처: 9.2 실측, 원인 미상
location: `storage.objects` — `listing_images_objects_owner_delete` 정책(`0013_listing_images_path_integrity.sql`)
severity: medium
reason: 9.2는 삭제 기능을 구현하지 않아(getSignedUrl/getSignedUrls만) 9.1~9.2 어디에도 사용자가 자기 사진을 지우는 화면·API 호출이 없어 오늘은 무해하다.
trigger: **Story 9.3**(업로더 — 사진 교체·삭제 UI를 만드는 순간 정면으로 부딪힌다). 착수 전 먼저 이 현상이 재현되는지 원격에서 재확인할 것(B4).
status: done 2026-07-29
resolution: Story 9.3 Task 0에서 닫힘 — 버그가 아니라 삭제 순서 제약이었고, 그 순서 계약은 docs/conventions.md §10에 정본화됨

- **위치:** `storage.objects` — `listing_images_objects_owner_delete` 정책(`0013_listing_images_path_integrity.sql`)
- **내용:** 9.2 원격 검증(Task 6) 중 실측: 본인 소유 오브젝트를 **authenticated JWT로 Storage API `DELETE /object/{bucket}/{path}`(단건)·`DELETE /object/{bucket}`(배치 prefixes)** 호출 시 둘 다 실패했다 — 단건은 `403 Access denied`, 배치는 `200`이지만 매치 0건(조용히 안 지워짐). 같은 경로에 대한 `POST /object/list/{bucket}`(목록 조회)도 authenticated로 **빈 배열**을 반환했다. 반면:
  - **RLS qual은 정확하다** — `bucket_id='listing-images' AND split_part(name,'/',1)=auth.uid()::text`이고 소유자 uuid가 실제로 일치함을 SQL로 직접 확인(`storage.objects.owner_id` = 요청자 uid).
  - **GRANT도 정상** — `information_schema.role_table_grants`에서 `authenticated`에게 `storage.objects`의 DELETE·SELECT·INSERT·UPDATE가 전부 부여돼 있음을 확인.
  - **INSERT(업로드)·서명(SELECT 경유)은 같은 세션·같은 토큰으로 정상 작동**했다 — 문제는 DELETE·LIST 두 동사에 국한된다.
  - `service_role` 키로는 즉시 성공(`200 Successfully deleted`) — RLS 우회 경로는 멀쩡하므로 **RLS 정책 자체의 논리 오류는 아니다.** Storage API 서버(Postgres RLS와 별개인 애플리케이션 레이어)가 DELETE/LIST 두 동사에서 추가 권한 검사를 하거나 다른 세션/역할 컨텍스트로 쿼리를 실행하는 것으로 추정되나 **근본 원인은 미상**(9.2는 이 원인규명을 하지 않았다 — 범위 밖).
- **오늘 무해한 이유:** 9.2는 삭제 기능을 구현하지 않는다(getSignedUrl/getSignedUrls만). 9.1~9.2 어디에도 사용자가 자기 사진을 지우는 화면·API 호출이 없다.
- **트리거:** **Story 9.3**(업로더 — 사진 교체·삭제 UI를 만드는 순간 정면으로 부딪힌다). 착수 전 먼저 이 현상이 재현되는지 원격에서 재확인할 것(B4).
- **해소:** 원인 규명 우선(Supabase Storage 서버 버전·설정 확인, 또는 Supabase 지원 문의) → 필요시 `service_role`을 쓰는 서버측 삭제 API 경유(단, `docs/conventions.md §5`의 "service_role 키는 어디에도 두지 않는다"와 충돌하므로 **party-mode로 대안 먼저 검토**: RPC 함수로 감싸 `security definer`화하는 방안이 유력).

> ### ✅ **닫힘 (2026-07-18, Story 9.3 Task 0) — 버그가 아니라 순서 제약이었다.**
> **재현은 됐고, 원인을 규명했다.** 9.3이 착수 전 원격에서 재측정한 결과 위 증상은 그대로 재현됐다(단건 DELETE `403 Access denied` · LIST `200` 0건 · 배치 `200` 매치 0건 · `storage.objects` SQL 직접 조회로 실제 미삭제 확인).
>
> **원인:** `storage.objects`의 **유일한 SELECT 정책** `listing_images_objects_read`(원격 `pg_policies` 직접 조회로 확인)는 `listing_images` 행과 `storage_path = objects.name`으로 **조인해야** 참이 된다. Storage API의 **DELETE·LIST는 대상 객체를 먼저 SELECT로 찾는다.** → **`listing_images` 행이 없는 객체는 소유자에게도 보이지 않고**, 그것이 `403`/`0건`으로 나타난다. 9.2의 관찰(“RLS qual·GRANT 정상인데 실패”)과 모순되지 않는다 — **9.2는 행 없는 객체로 시험했다.**
>
> **가설을 실험으로 확인:** 같은 객체에 `listing_images` 행을 **먼저 넣고** 재시도 → LIST `200` **1건**, SIGN **`200`**, DELETE **`200 Successfully deleted`**.
>
> **결론:** `service_role`도 `security definer` RPC도 **필요 없다**(계획했던 `0014` 마이그레이션 취소). 대신 **삭제 순서가 계약이 된다** — `docs/conventions.md §10`에 명시:
> **① Storage 오브젝트 삭제 → ② `listing_images` 행 삭제.** 반대로 하면 객체가 즉시 안 보이게 되어 **영구 고아**가 된다(#46 직결).
>
> **함께 확인된 것:** `x-upsert: true` 업로드도 같은 뿌리로 `403 new row violates row-level security policy`가 된다(업서트가 존재확인 SELECT를 거친다). **업로더는 upsert를 쓰지 않는다** — 파일명이 uuid라 충돌 자체가 없다.
>
> **남은 것:** 이 규명 과정에서 경로 계약(3세그먼트)을 만족하지 못하는 프로브 객체 2개(각 70바이트)가 **위 규칙으로 지울 수 없는 상태로 남았다** → #46에 실제 발현 사례로 등재. SQL 직접 삭제는 `storage.protect_delete()`가 막는다(`42501`).

### DW-352: [구 #52] Flutter 앱에 매물 사진 업로더가 어느 에픽에도 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #52) — 원출처: 계획 공백, 9.3 작성 중 발견
location: `app/lib/features/listings/sell_screen.dart` — 주석 원문 *"사진 없음(업로드 위젯 없음)"*. `app/pubspec.yaml`에 `image_picker`·`file_picker`·`camera` **없음**(grep 0건).
severity: medium
reason: 앱은 아직 사진을 표시하지도 않아(`listing.dart:47` `imageUrl`은 예약만 됨) 웹 업로더가 생기면 앱은 9.x 소비 스토리(16-2)에서 표시부터 붙는 순서라 오늘은 무해하다.
trigger: Epic 16 착수 시. **그 전에 `epics-increment-2026-07-12.md`의 Epic 16에 스토리를 실제로 추가해야 한다**(문서에 없으면 sprint-planning이 다시 만들어도 또 빠진다) — `correct-course` 소관.
status: open

- **위치:** `app/lib/features/listings/sell_screen.dart` — 주석 원문 *"사진 없음(업로드 위젯 없음)"*. `app/pubspec.yaml`에 `image_picker`·`file_picker`·`camera` **없음**(grep 0건).
- **내용:** Story 9.3 AC 원문(`epics-increment-2026-07-12.md:489-506`)은 "매물 등록/수정 폼"이라고만 하고 플랫폼을 한정하지 않는다. 그런데 **Epic 16(Flutter 앱 증분 반영) 6개 스토리 어디에도 사진 업로더가 없다** — 16-2는 "이미지 **카드** 재설계(앱)"로 **읽기 측**이다. 즉 현재 계획을 그대로 끝내면 **앱 판매자는 사진을 영영 못 올린다**(웹에서만 가능).
- **결정(사용자, 2026-07-18):** **(A) 9.3은 web만.** 앱 업로더는 **Epic 16에 별도 스토리로 추가**한다. 근거: 증분 구조가 "Epic 9~15=web·api / Epic 16=앱 미러링"이고, 앱 업로더는 새 의존성 + 카메라/갤러리 권한이 붙는 별개 크기의 일이라 9.3에 합치면 스토리가 비대해진다.
- **오늘 무해한 이유:** 앱은 아직 사진을 **표시**하지도 않는다(`listing.dart:47` `imageUrl`은 예약만 됨). 웹 업로더가 생기면 앱은 9.x 소비 스토리(16-2)에서 표시부터 붙는다.
- **트리거:** Epic 16 착수 시. **그 전에 `epics-increment-2026-07-12.md`의 Epic 16에 스토리를 실제로 추가해야 한다**(문서에 없으면 sprint-planning이 다시 만들어도 또 빠진다) — `correct-course` 소관.
- **해소:** Epic 16에 `16-7-앱-사진-업로더` 신설. 9.3이 확정한 계약(경로 규약·1600px WebP 저장본·대표=순서 0번·순차 INSERT)을 그대로 미러링하면 된다.

### DW-353: [구 #53] 폼 이탈 가드가 `<Link>` 내부 이동을 막지 못한다

origin: 장부 통합 이관(구 docs/tech-debt.md #53) — 원출처: 9.3 구현 중 확인, 프레임워크 한계
location: `web/src/app/(user)/sell/SellForm.tsx` — `beforeunload` 리스너 + `attemptLeave()`.
severity: medium
reason: 판매 폼에서 나가는 자연스러운 동선은 [취소]와 [제출]이고 둘 다 처리돼, 헤더 로고를 눌러 나가는 경우에만 작성 내용이 조용히 사라져 오늘은 무해하다.
trigger: 사용자가 사진 여러 장을 올린 뒤 헤더 링크로 이탈해 데이터를 잃는 순간. 폼이 더 무거워질수록(사진 10장) 손실 체감이 커진다.
status: open

- **위치:** `web/src/app/(user)/sell/SellForm.tsx` — `beforeunload` 리스너 + `attemptLeave()`.
- **내용:** 매물 등록/수정 폼의 이탈 가드(AC7)는 **세 경로 중 두 개만** 막는다.

  | 이탈 경로 | 막히나 | 근거 |
  |---|---|---|
  | 새로고침·탭 닫기·주소창 직접 이동 | ✅ | `beforeunload`. **실측**(2026-07-18): dirty 상태에서 Playwright의 페이지 이동이 60초 타임아웃으로 멈췄고 **요청이 서버 로그에 도달하지 않았다** = 브라우저가 페이지를 못 떠났다 |
  | 폼 자체의 [취소] 버튼 | ✅ | `<Link>`를 **버튼으로 바꿔** 직접 확인 다이얼로그(FocusTrap)를 띄운다. 실측: 변경 있음 → 다이얼로그 노출, 변경 없음 → 경고 없이 즉시 이동 |
  | **헤더 로고·내비 등 다른 `<Link>`** | ❌ **안 막힌다** | Next.js App Router에 **클라이언트 라우팅 이동을 가로채는 공식 API가 없다**(`next/navigation`에 `useBlocker`류 미제공). `beforeunload`는 문서 언로드에만 발화하므로 소프트 내비게이션에서는 아예 안 뜬다 |

- **⚠️ "막았다"고 적지 않는다** — 이 표의 3행이 이 항목이 존재하는 이유다. 세 경로 중 둘만 막혔다.
- **오늘 무해한 이유:** 판매 폼에서 나가는 자연스러운 동선은 [취소]와 [제출]이고 둘 다 처리된다. 헤더 로고를 눌러 나가는 경우에만 작성 내용이 조용히 사라진다.
- **트리거:** 사용자가 사진 여러 장을 올린 뒤 헤더 링크로 이탈해 데이터를 잃는 순간. 폼이 더 무거워질수록(사진 10장) 손실 체감이 커진다.
- **해소 후보:** (a) 폼이 dirty인 동안 헤더 내비를 `<Link>` 대신 `attemptLeave()`를 부르는 버튼으로 바꾸는 공용 래퍼, (b) Next가 내비게이션 인터셉트 API를 제공할 때 교체. **(a)는 레이아웃 전역을 건드리므로 9.3 범위 밖으로 두었다**(A3 외과적 변경).

### DW-354: [구 #54] 수정 폼을 열어둔 사이 매물이 `sold`가 되면 그대로 수정된다

origin: 장부 통합 이관(구 docs/tech-debt.md #54) — 원출처: 9.3 리뷰 이월, 🟡 조건부
location: `web/src/app/(user)/sell/[id]/edit/page.tsx:72`(진입 차단) · `SellForm.tsx` 제출 경로 · `supabase/migrations/0002_listings.sql` `listings_update_own`.
severity: high
reason: 판매자 본인이 두 곳에서 동시에 같은 매물을 조작하는 동선이 드물어 오늘은 무해하다.
trigger: 관리자 화면·앱이 판매 상태를 바꾸는 경로가 늘어날수록 창이 넓어진다.
status: done 2026-07-29
resolution: Story 9.7이 해소 — 0015_listings_update_not_sold.sql의 using(auth.uid()=seller_id and status <> 'sold') 실재 확인

- **위치:** `web/src/app/(user)/sell/[id]/edit/page.tsx:72`(진입 차단) · `SellForm.tsx` 제출 경로 · `supabase/migrations/0002_listings.sql` `listings_update_own`.
- **내용:** `sold` 차단은 **서버 렌더 시점 1회뿐**이다. 폼을 열어둔 채 다른 탭·앱에서 구매완료 처리하면, 원래 탭의 제출은 status를 재확인하지 않고 통과한다. DB 정책도 `auth.uid() = seller_id`만 볼 뿐 status 조건이 없다.
- **⚠️ 문서-코드 불일치:** `edit/page.tsx`의 주석은 이 방어를 "이중 방어"라 적었지만, 실제로는 **화면 층 단일 방어**다. B9("규칙은 어길 수 없는 자리에 박는다") 기준 미이행.
- **오늘 무해한 이유:** 판매자 본인이 두 곳에서 동시에 같은 매물을 조작하는 동선이 드물다.
- **트리거:** 관리자 화면·앱이 판매 상태를 바꾸는 경로가 늘어날수록 창이 넓어진다.
- **해소 후보:** `listings_update_own`의 `using`에 `status <> 'sold'` 추가(전진 마이그레이션). 앱 코드가 아니라 DB에 박아야 화면이 늘어도 안 샌다.

- **📅 예약: Story 9.7 마이그레이션.** `listings_update_own`에 `status <> 'sold'`를 넣는 전진 마이그레이션으로 처리한다 — 앱 코드로 막으면 화면이 늘 때 또 빠진다(B9). 9.7 스토리 AC에 체크박스로 심을 것.
- ✅ **해소 (Story 9.7, 2026-07-21) — `supabase/migrations/0015_listings_update_not_sold.sql`.**
  - **red(적용 전) 실측**: 시드 판매자 JWT로 sold 매물 `price` PATCH → **HTTP 200 · 1행 변경**. 즉 이 항목이 "화면 층 단일 방어"라고 적은 것은 정확했고, 실제로 뚫려 있었다.
  - **green(적용 후) 실측**(빈 Postgres에 정책만 갈아끼워 대조):

    | 시나리오 | 적용 전 | 적용 후 |
    |---|---|---|
    | sold 매물 UPDATE | 1행 (뚫림) | **0행 (막힘)** |
    | on_sale 매물 정상 수정 | 1행 | 1행 (회귀 없음) |
    | on_sale → sold 전환 (FR7 구매완료) | 1행 | 1행 (살아 있음) |

  - ⚠️ **`using`에만 걸고 `with check`에는 걸지 않았다.** `with check`(=변경 **후** 행)에 `status <> 'sold'`를 걸면 on_sale→sold 전환 자체가 막혀 **FR7 구매완료 기능이 통째로 죽는다.** 위 표의 세 번째 줄이 그것을 지키는 검증이다.
  - **소비처 코드 변경 0줄.** web `SellForm.tsx`·`ListingActions.tsx`와 app `listings_repository.dart`가 이미 "UPDATE 결과 0행 = 권한 없음"으로 안내하고 있어, RLS 거부(에러가 아니라 0행)가 그대로 흡수된다.

### DW-355: [구 #55] 서명 URL(TTL 3600) 만료 후 수정 화면 미리보기 복구 수단이 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #55) — 원출처: 9.3 리뷰 이월, 🟡 조건부
location: `web/src/app/(user)/sell/[id]/edit/page.tsx`(서버측 `getSignedUrls` 1회 배치) → `photo-item.ts`의 `previewUrl`에 고정.
severity: high
reason: 갤러리(Story 9.5)가 같은 서명 URL을 쓰므로 갱신 로직을 거기서 한 번에 만들기로 미뤘다 — 지금 따로 만들면 두 번 만들게 된다.
trigger: 사진이 많아 편집이 길어지는 매물, 또는 탭을 열어둔 채 자리를 비우는 경우.
status: done 2026-07-29
resolution: Story 9.0의 공개 URL 전환으로 **문제 자체가 소멸** — 만료가 없으므로 '만료 후 복구'가 성립하지 않는다. SIGNED_URL_TTL 상수도 삭제됨

- **위치:** `web/src/app/(user)/sell/[id]/edit/page.tsx`(서버측 `getSignedUrls` 1회 배치) → `photo-item.ts`의 `previewUrl`에 고정.
- **내용:** 갱신 로직이 없어, 수정 화면을 **1시간 이상 열어두면** 기존 사진이 전부 깨진 이미지가 된다. 삭제·순서 조작은 `storagePath` 기반이라 계속 동작하는 것이 오히려 위험하다 — 사용자가 "사진이 사라졌다"고 오인해 멀쩡한 사진을 지울 수 있다.
- **트리거:** 사진이 많아 편집이 길어지는 매물, 또는 탭을 열어둔 채 자리를 비우는 경우.
- **해소 후보:** 이미지 `onError`에서 서명 URL 재발급 요청, 또는 만료 임박 시 주기적 갱신.

- **📅 예약: Story 9.5(상세 갤러리) AC.** 갤러리가 같은 서명 URL을 쓰므로 갱신 로직을 거기서 한 번에 만든다 — 지금 따로 만들면 두 번 만들게 된다.
- **✅ 항목 소멸 (Story 9.0, 2026-07-19):** 공개 URL은 만료되지 않으므로 "만료 후 복구"라는 문제가 존재하지 않는다. 9.5에 예약했던 갱신 로직도 **만들 필요가 없다**(예약 해제).

### DW-356: [구 #56] 다른 탭·세션이 10장을 채우면 업로드된 오브젝트가 영구 고아로 남는다

origin: 장부 통합 이관(구 docs/tech-debt.md #56) — 원출처: 9.3 리뷰 이월, 🟡 조건부 — #43·#46·#49 합성 발현
location: `web/src/app/(user)/sell/photo-sync.ts` — 업로드 루프 → 행 INSERT 루프 → 실패 시 정리 시도.
severity: high
reason: #43(트리거가 INSERT만 봄)·#49(경합 미측정)·#46(고아 회수 불가)의 합성이라 클라이언트 패치로 닫히지 않는다 — 서버 강제 + 고아 정리 경로가 있어야 한다.
trigger: 판매자가 두 기기·두 탭에서 같은 매물을 편집하는 순간. 데모에서는 드물다.
status: open

- **위치:** `web/src/app/(user)/sell/photo-sync.ts` — 업로드 루프 → 행 INSERT 루프 → 실패 시 정리 시도.
- **내용:** 탭 A가 먼저 저장해 10장을 채우면, 탭 B는 **업로드는 전부 성공시킨 뒤** 행 INSERT가 `enforce_listing_images_max_10`에 걸린다. 정리 시도는 **행이 없어 읽기 정책상 객체가 안 보이므로 실패한다**(코드 주석도 "실패할 수 있다"고 인정만 하고 넘어감).
- **왜 개별 수정이 아니라 이월인가:** #43(트리거가 INSERT만 봄)·#49(경합 미측정)·#46(고아 회수 불가)의 합성이라, 클라이언트 패치로 닫히지 않는다. **서버 강제 + 고아 정리 경로**가 있어야 한다.
- **트리거:** 판매자가 두 기기·두 탭에서 같은 매물을 편집하는 순간. 데모에서는 드물다.

- **~~📅 예약: Epic 9 회고에서 재평가.~~** → **재평가 완료 (Epic 9 회고, 2026-07-21).**
- **✎ 재평가 결과 — 성격이 바뀌었다. 열어 두되 자리를 옮긴다.** 이 항목이 쓰인 시점의 전제는 "정리 시도가 **행이 없어 객체가 안 보여** 실패한다"였다. **Story 9.0의 공개 버킷 전환(마이그 `0014`)이 읽기 정책을 경로 기반으로 바꾸면서 그 전제가 사라졌다** — 행이 없어도 소유자에게 객체가 보인다(9.0 실측: 소유자 1행, 전에는 0행). 즉 **"회수 불가"가 아니라 "회수 수단은 있으나 그걸 부르는 UI가 없다"**로 내려앉았다.
- **📅 예약: Epic 16.2(앱 사진 업로더)** — 같은 쓰기 경로를 다시 여는 자리다. `#85`(storage_path 모양 미검증)·`#90`(sold 사진 교체)과 **한 축**이므로 그때 함께 본다. 지금 단독으로 고치면 근거 없이 설계를 늘린다(A2).

### DW-395: [구 #95] 시드 스크립트 잔여 3종 — 부분 시딩·중단 고아·`--limit` 의미

origin: 장부 통합 이관(구 docs/tech-debt.md #95) — 원출처: 2026-07-21 코드리뷰 이월, 🟢 품질
location: `scripts/seed_listing_photos.py`
severity: medium
reason: 이 스크립트는 데모 데이터 준비용 1회성 도구고, 전량 시딩은 이미 끝났다(90매물·180장). A3(외과적 변경) 기준으로 이번 스토리 요청에 추적되지 않는다.
trigger: 시드 사진을 다시 채워야 하는 시점(신규 매물 추가 · `seed.sql` 재실행 후 복구 — 런북 §9).
status: open

- **위치:** `scripts/seed_listing_photos.py`
- **① 부분 시딩된 매물은 영구히 부분 상태로 남는다** (`:312` `if row["id"] in already: continue`) — `already`가 *"행이 1개 이상 있는 매물"* 이라, 3장을 목표로 하다 2장에서 실패한 매물은 **재실행해도 절대 보충되지 않는다.** Storage 파일만 지워진 고아 행도 "이미 시딩됨"으로 센다.
- **② 업로드 성공 후 중단되면 Storage 고아가 남고 회수 수단이 없다** (`:357-393`) — INSERT 실패 시의 정리는 있지만 **업로드~INSERT 사이의 중단**(Ctrl-C·타임아웃·네트워크 끊김)은 `try/finally`가 없어 정리 코드에 도달하지 않는다. Storage 오브젝트는 CASCADE 대상이 아니라 영구 고아가 되고 어떤 경로로도 탐지되지 않는다.
- **③ `--limit`이 "채운 매물 수"가 아니라 "시도한 매물 수"다** (`:317`) — targets가 Commons 검색 **이전에** 확정되므로, 검색 0건·다운로드 실패로 건너뛴 매물이 슬롯을 소모한다. `--limit 40`이 실제로는 30매물만 채울 수 있다.
- **왜 지금 안 고치나:** 이 스크립트는 데모 데이터 준비용 1회성 도구고, 전량 시딩은 이미 끝났다(90매물·180장). A3(외과적 변경) 기준으로 이번 스토리 요청에 추적되지 않는다.
- **트리거:** 시드 사진을 다시 채워야 하는 시점(신규 매물 추가 · `seed.sql` 재실행 후 복구 — 런북 §9).
- *(같은 파일의 `--limit 0` 경계·미매칭 무음 스킵·표기 정규화·`raise_for_status` 누락은 **2026-07-21 코드리뷰에서 고쳤다** — 이 항목은 남은 3종이다.)*

### DW-396: [구 #96] 시드 검색어 품질 3종 — `≈` 표기 불일치 · 연식 박힌 검색어 · 제조사 축 붕괴 키

origin: 장부 통합 이관(구 docs/tech-debt.md #96) — 원출처: 2026-07-21 코드리뷰 이월, 🟢 품질
location: `scripts/seed_listing_photos.py`의 `SEARCH_TERMS`
severity: medium
reason: 지금 고치는 것도, 지우는 것도 A3상 이번 요청에 추적되지 않으며, 다음 시딩에서 미매칭 집계 출력이 실제 사용 여부를 알려주므로 그대로 둔다.
trigger: 시드 사진 품질이 데모에서 문제로 지적되는 시점 · 매물 데이터에 제조사 정규화를 넣는 시점 · 신규 매물 추가 후 미매칭 집계에 항목이 뜨는 시점.
status: open

- **위치:** `scripts/seed_listing_photos.py`의 `SEARCH_TERMS`
- **① `≈`(계열 혼입 수용) 표기가 일관되지 않다** — `("기아","봉고3")`엔 *"≈ 형제차 K2500/K2700이 섞임"* 을 달았는데, 동일 성격인 `("현대","포터2")`(구형 Porter I 혼입)·`("KG모빌리티","렉스턴")`(리브랜딩 이전 차량)엔 없다. 주석 규약이 스스로 *"≈ 없는 건 정확하다"* 는 뜻을 만들어 놓고 위반한다.
- **② 검색어에 연식을 박아 결과가 시간에 따라 흔들린다** — `("쉐보레","트레일블레이저"): "Chevrolet Trailblazer 2020"`. Commons 전문검색이라 "2020"은 파일명·설명 문자열 매칭에 의존하고, 해당 파일이 정리·개명되면 **그 모델만 조용히 0건**이 된다(스크립트는 스킵을 에러로 올리지 않는다).
- **③ `("기타", "볼보 XC60")` — 제조사 축이 무너진 키** — 제조사 컬럼이 `기타`인 데이터에 맞춰 모델 문자열에 브랜드를 넣었다. 볼보 다른 차종이 들어오면 개별 열거해야 하고, 제조사 정규화가 나중에 이뤄지면(`볼보`) 이 키는 **조용히 죽는다**.
- **④ 서로 다른 모델이 같은 검색어를 공유해 사진이 겹친다** — `("현대","그랜저 GN7")`과 `("현대","그랜저 GN7 하이브리드")`가 같은 `"Hyundai Grandeur GN7"`을 쓴다(`아반떼 MD`/`아반떼MD` 등도 동일). `gsrsearch`는 관련도순 고정 결과이고 `gsroffset`도 매물 간 중복 배제(seen set)도 없어 **같은 파일을 받는다.** 표기 변형(`아반떼MD`)은 의도된 것이지만 **하이브리드/일반은 실제로 다른 매물**이라, 목록 한 화면에 **똑같은 사진의 카드가 나란히** 뜬다. *(데모 규모에서 수용 — 사용자 결정 2026-07-21.)*
- **관련 ⓐ:** 시드 사진 중 **"매칭은 됐지만 다른 차"** 인 건수는 세어진 적이 없다 — Story 9.7의 *"미매칭 0종"* 은 *"Commons가 결과를 돌려줬다"* 를 잰 것이지 ***"맞는 차다"*** 를 잰 것이 아니다. 제목 육안 확인은 후보 59종에 대한 **표본 점검**이었다. 즉 "0종"은 성공의 증거가 아니라 **실패를 다른 칸으로 옮긴 결과**다(실제 실패 모드는 사유표의 세 칸 밖에 있었다 — "매칭됐지만 다른 차").
- **관련 ⓑ — 76종 중 상당수가 한 번도 실행되지 않았다:** 대응표를 15종 → 76종으로 늘린 근거는 *"향후 50건(인기 국산 준중형·중형·대형 세단)이 들어올 때 다시 안 고치게"* 인데, 실제 추가분에는 **테슬라 모델3/S/Y · BMW M4 · 렉서스 ES300h · 혼다 CR-V · 아우디 Q5/A6 · 폭스바겐 티구안** 등 그 서술과 무관한 수입 SUV·전기차가 다수다. 그리고 *"미매칭 0종"* = **현 매물 90건이 전부 매칭됐다** = **그 밖의 검색어는 이번에 한 번도 실행되지 않았다** → **틀린 검색어가 있어도 발견되지 않는다.** A2(추측성 확장 금지) 기준으로도 정당화가 없다. *(지금 지우지는 않는다 — 지우는 것도 A3상 이번 요청에 추적되지 않고, 다음 시딩에서 ①의 미매칭 집계 출력이 실제 사용 여부를 알려준다.)*
- **트리거:** 시드 사진 품질이 데모에서 문제로 지적되는 시점 · 매물 데이터에 제조사 정규화를 넣는 시점 · 신규 매물 추가 후 미매칭 집계에 항목이 뜨는 시점.

### DW-397: [구 #97] 공백만 있는 `url`이 **"사진 있음"으로 판정**된다

origin: 장부 통합 이관(구 docs/tech-debt.md #97) — 원출처: 2026-07-21 코드리뷰 이월, 🟢 품질 — `#85` 축
location: `web/src/components/listings/ListingCardImage.tsx:45` (`const showPhoto = Boolean(url) && !failed`)
severity: medium
reason: 현재 데이터에 그런 값이 없어(`storage_path` 180행 전부 정상 모양) 오늘은 무해하며, 모양을 검증하는 곳이 하나도 없다는 것은 `#85`로 별도 관리된다.
trigger: `#85`(storage_path 모양 검증 — Epic 16.2)와 함께.
status: open

- **위치:** `web/src/components/listings/ListingCardImage.tsx:45` (`const showPhoto = Boolean(url) && !failed`)
- **내용:** `Boolean('')`은 false지만 `Boolean(' ')`은 **true**다. 공백 `src`는 브라우저가 **현재 문서 URL로 해석**해 페이지 HTML을 다시 내려받고, 그게 이미지로 디코드 실패해야 비로소 폴백이 뜬다. 그 요청은 **HTTP 200**이라 *"네트워크 4xx/5xx 0건"* 검증도 그대로 통과한다.
- **왜 지금 무해한가:** 현재 데이터에 그런 값이 없다(`storage_path` 180행 전부 정상 모양). 다만 **모양을 검증하는 곳이 하나도 없다는 것이 `#85`** 이므로, 같은 축의 소비처 방어로 함께 본다.
- **해소:** `Boolean(url?.trim())`.
- **트리거:** `#85`(storage_path 모양 검증 — Epic 16.2)와 함께.

### DW-398: [구 #98] `count`가 **정수·상한 검증 없이** 배지에 렌더된다

origin: 장부 통합 이관(구 docs/tech-debt.md #98) — 원출처: 2026-07-21 코드리뷰 이월, 🟢 품질
location: `web/src/components/listings/ListingCardImage.tsx:47,111` (`Math.max(0, count ?? 0)`)
severity: medium
reason: `0012`의 BEFORE INSERT 트리거가 매물당 10장을 강제하고 count는 DB `count(*)` 파생값이라 소수·무한대가 나올 경로가 없어 오늘은 무해하다.
trigger: 사진 장수를 DB 집계가 아닌 곳(캐시·클라 계산)에서 받게 되는 시점.
status: open

- **위치:** `web/src/components/listings/ListingCardImage.tsx:47,111` (`Math.max(0, count ?? 0)`)
- **내용:** 음수만 깎는다. 소수(`2.5` → "2.5장"), 10장 상한을 넘는 값(`999`), `Infinity`("Infinity장")가 그대로 찍히고 배지 폭이 카드를 넘어 **390px에서 D5 반응형 금기(레이아웃 어긋남)** 를 만든다.
- **왜 지금 무해한가:** `0012`의 BEFORE INSERT 트리거가 매물당 10장을 강제하고, count는 DB `count(*)` 파생값이라 소수·무한대가 나올 경로가 없다.
- **해소:** `Math.min(10, Math.floor(Math.max(0, count ?? 0)))` — `conventions.md` §4의 계약-외 값 정규화 원칙과 같은 자리.
- **트리거:** 사진 장수를 DB 집계가 아닌 곳(캐시·클라 계산)에서 받게 되는 시점.

### DW-418: [구 #118] 찜 RLS 격리·FK cascade가 **실행되는 회귀 테스트 없이** 1회 수동 실측에만 의존한다

origin: 장부 통합 이관(구 docs/tech-debt.md #118) — 원출처: 2026-07-22 Story 10.5 코드리뷰 등재, 🟢 품질
location: `supabase/migrations/0018_wishlists.sql`(`wishlists_select_own`/`insert_own`/`delete_own` + FK `on delete cascade`) · 커밋된 테스트 부재
severity: medium
reason: 정책·cascade가 현재 올바르게 선언되어 있고 수동 red-green 테스트로 실제로 걸러지는 것까지 확인되어 있어 당장 위험하지 않기 때문에, 커밋된 자동 회귀 테스트는 아직 추가하지 않았다.
trigger: RLS 롤 임퍼소네이션 테스트 하네스가 레포에 도입되는 시점(그때 wishlists 격리·cascade를 커밋 테스트로 고정) · 또는 `wishlists`의 RLS/FK를 다음에 수정할 때(수정과 함께 회귀 검사를 심는다).
status: open

- **위치:** `supabase/migrations/0018_wishlists.sql`(`wishlists_select_own`/`insert_own`/`delete_own` + FK `on delete cascade`) · 커밋된 테스트 부재
- **내용:** 10.5의 두 안전장치 — (1) 본인 RLS 격리("타인은 남의 찜 0행"), (2) `null=sold` 추론이 기대는 FK cascade("매물 삭제 시 찜 행도 사라짐") — 는 착수 시 **로컬 Supabase 수동 실측 1회**로만 확인됐고(sprint-status·`#117` 기록), **커밋돼 매번 도는 검사가 없다.** 레포에 RLS 임퍼소네이션 테스트 하네스 자체가 없다(`api/tests/integration/*_real_db.py`는 superuser로 붙어 RLS를 우회, `check_migrations.py`의 RLS 프로브는 `pg_policies` **존재**만 확인 — "존재 확인 ≠ 작동 확인", B4/B9). Story 2-1(listings RLS)도 같은 수동 관례였다 — 이건 이 스토리 한정이 아니라 레포 공통 축이다.
- **지금 무해한 이유:** 정책·cascade가 현재 올바르게 선언돼 있고 수동 red-green으로 실제 거르는 것까지 확인됐다(그 시점엔 안 샌다, `#117`).
- **무엇을 못 잡나:** 훗날 누군가 `wishlists_select_own`을 `using(true)`로 넓히거나 정책/FK를 바꾸면 — 모든 사용자의 찜이 서로에게 열리거나, 삭제된 매물이 "판매완료"로 오표시되는데 — `npm run test`·마이그 게이트 어디도 red가 안 뜬다(격리는 아무 자동검사가 안 보고, cascade 단위테스트는 `null`을 손으로 넣을 뿐 실제 삭제를 안 돌린다).
- **트리거:** RLS 롤 임퍼소네이션 테스트 하네스가 레포에 도입되는 시점(그때 wishlists 격리·cascade를 커밋 테스트로 고정) · 또는 `wishlists`의 RLS/FK를 다음에 수정할 때(수정과 함께 회귀 검사를 심는다).

### DW-362: [구 #62] `getSignedUrls` 결과를 **배열 위치로** 사진 행에 짝지운다

origin: 장부 통합 이관(구 docs/tech-debt.md #62) — 원출처: 9.3 코드리뷰 2차 이월, 🟡 조건부
location: `web/src/app/(user)/sell/[id]/edit/page.tsx` — `rows.map((r, i) => ({ ..., url: signedUrls[i] }))`
severity: high
reason: `getSignedUrls`는 9.2 스토리 산출물이라 이번 변경 범위 밖이었고, 계약을 고정할 자리는 소비처가 아니라 헬퍼 쪽이라 판단해 미뤘다.
status: done 2026-07-29
resolution: Story 9.0이 `getSignedUrls` 자체를 삭제 — 행별 getPublicUrl 호출로 바뀌어 배열 위치 매칭이라는 구조가 없어졌다(문제 자체가 소멸). grep 0건 확인

- **위치:** `web/src/app/(user)/sell/[id]/edit/page.tsx` — `rows.map((r, i) => ({ ..., url: signedUrls[i] }))`
- **내용:** 배치 서명 헬퍼가 **입력과 같은 개수·같은 순서로**, 실패분까지 자리를 지켜 돌려준다는 계약에 의존한다. `conventions.md §10`은 실패 시 `null` 반환이라 적어 위치 매칭과 정합하지만, **그 계약을 고정하는 검사는 0건**이다(`lib/storage/index.ts`에도, 소비처에도).
- **터지면:** 실패 항목이 드롭되거나 순서가 바뀌는 순간, 첫 실패 이후 **모든 사진이 남의 서명 URL**을 갖는다 — 엉뚱한 이미지 옆에 그 사진의 ✕ 버튼이 놓여 **사용자가 다른 사진을 지운다.**
- **왜 지금 안 고치나:** `getSignedUrls`는 9.2 산출물이고 이번 변경 범위 밖이다(A3). 고칠 자리는 소비처가 아니라 헬퍼의 계약이다.
- **해소 (9.5 AC로 심을 것 — B5):** `getSignedUrls`가 입력 길이와 순서를 보존하고 실패를 `null`로 채운다는 것을 **실패를 섞어 넣어** 검증하는 테스트 1건. 또는 소비처가 위치가 아니라 `storage_path` 키로 짝짓게 바꾼다.
- **✅ 항목 소멸 (Story 9.0, 2026-07-19):** `getSignedUrls` 자체가 삭제됐다. 소비처는 이제 각 행의 `storage_path`로 `getPublicUrl`을 **행별로** 호출하므로 배열 위치 매칭이라는 구조가 없다. 9.5 예약 해제.

### DW-364: [구 #64] `crypto.randomUUID()`는 secure context 밖에서 undefined

origin: 장부 통합 이관(구 docs/tech-debt.md #64) — 원출처: 9.3 코드리뷰 2차 이월, 🟢 품질
location: `web/src/app/(user)/sell/photo-item.ts:40`(React key) · `photo-sync.ts:38`(저장 파일명)
severity: medium
reason: 운영 환경은 Vercel HTTPS라 secure context 문제가 실사용에 영향을 주지 않고, 이 코드는 이전 리뷰에서 고친 key 충돌 문제의 정당한 대체재이기 때문에 지금 폴백을 넣지 않았다.
status: open

- **위치:** `web/src/app/(user)/sell/photo-item.ts:40`(React key) · `photo-sync.ts:38`(저장 파일명)
- **내용:** `crypto.randomUUID`는 HTTPS·localhost 등 **secure context에서만** 노출된다. 평문 HTTP 오리진(LAN IP로 여는 로컬 테스트 등)에서는 수정 페이지가 500나고 업로드는 일반 예외로 떨어진다(진단 문구 없음).
- **왜 낮은가:** 운영은 Vercel HTTPS라 **실사용 영향 없음.** 1차 리뷰가 고친 모듈 카운터 key 충돌의 대체재로 들어온 것이고, 그 교환 자체는 옳다.
- **해소 후보:** 폴백 1줄(`crypto.randomUUID?.() ?? \`${Date.now()}-${Math.random()}\``). 단 **필요해진 근거(실제로 그 환경에서 테스트한다는 사실)가 생겼을 때** 넣는다 — 지금 넣으면 안 쓰는 분기를 미리 만드는 것이다(A2).

### DW-365: [구 #65] 판매완료(sold) 매물의 사진 URL이 계속 열린다 — **명시 수용**

origin: 장부 통합 이관(구 docs/tech-debt.md #65) — 원출처: Story 9.0, 사용자 결정 2026-07-19, ⚪ 의도적 보류
location: `listing-images` 버킷(`public=true`, `0014_listing_images_public_bucket.sql`) · 계약 서술은 `docs/conventions.md` §6.1
severity: low
reason: 이전 설계(비공개 버킷+서명 URL)는 복잡도를 다 치르고도 TTL 동안 똑같이 뚫려 있어 효과가 없었고, `sold`는 되돌릴 수 있는 상태인데 파일 삭제는 되돌릴 수 없어 파일을 지우지 않기로 사용자가 명시적으로 결정했다.
trigger: 없음(닫을 항목이 아니다). ⚠️ **이 항목은 "못 막은 것"이 아니라 "안 막기로 한 것"이다** — 다시 막으려 들기 전에 §6.1과 이 항목을 먼저 읽을 것.
status: open

- **위치:** `listing-images` 버킷(`public=true`, `0014_listing_images_public_bucket.sql`) · 계약 서술은 `docs/conventions.md` §6.1
- **내용:** 판매중일 때 사진 URL을 저장해 둔 사람은 그 매물이 `sold`가 된 뒤에도 파일을 열 수 있다. 매물 자체는 목록·검색·상세·AI 어디에도 나타나지 않는다(FR11 강제 지점 불변) — **주소를 이미 아는 사람만** 접근한다. 파일명이 uuid라 추측·열거는 불가.
- **왜 열어 뒀나:** 이전 설계(비공개 버킷 + 1시간 서명 URL)는 이 복잡도를 다 치르고도 TTL 동안 똑같이 뚫려 있었다(#50-2). 비용은 전부 내고 효과는 못 얻으면서 #45·#46·#50-2·#55·#62를 만들어 냈다.
- **왜 `sold`에서 파일을 지우지 않나:** `sold`는 되돌릴 수 있는 상태 변경인데 파일 삭제는 되돌릴 수 없다. 그리고 Story 15.1이 "관리자는 sold 포함 열람"을 이미 요구한다.
- **트리거:** 없음(닫을 항목이 아니다). ⚠️ **이 항목은 "못 막은 것"이 아니라 "안 막기로 한 것"이다** — 다시 막으려 들기 전에 §6.1과 이 항목을 먼저 읽을 것.
- **⚪ 상태: 의도적 보류.** 재검토 조건은 "실제 사용자 신고" 또는 "데모가 아닌 상용 전환".

### DW-368: [구 #68] 시드 사진 스크립트가 **스토리 밖에서** 만들어지고 부분 실행됐다

origin: 장부 통합 이관(구 docs/tech-debt.md #68) — 원출처: 코드리뷰 2026-07-19 등재, 🟡 조건부
location: `scripts/seed_listing_photos.py` (커밋 `9ecb69f`) · `sprint-status.yaml`의 `9-7-시드-사진-...: backlog`
severity: high
reason: 잔여 작업이 실제로 backlog에 남아 있고, 스토리 생성은 착수 시점에 컨텍스트를 채워 만드는 것이 정상 절차라 미리 만들면 반쪽짜리 문서가 하나 더 생기기 때문에 지금 만들지 않았다.
trigger: 9.7 착수. **급하지 않다** — 전량 시딩이 필요한 시점은 9.7 자신이 종료 게이트이고, 제출·데모 마감일자는 어느 문서에도 없다(2026-07-19 실측).
status: done 2026-07-29
resolution: Story 9.7이 체크박스 4건 전부 소화하고 항목을 닫았다 — 시딩 완료 + 마이그레이션 파일 실재 확인(2026-07-29 실측)

- **위치:** `scripts/seed_listing_photos.py` (커밋 `9ecb69f`) · `sprint-status.yaml`의 `9-7-시드-사진-...: backlog`
- **내용:** Wikimedia Commons에서 실차 사진을 받아 매물에 붙이는 **Story 9.7 소싱 절차의 구현**인데, 9.7은 `backlog`이고 스토리 파일이 없다. 원격 Supabase에 **매물 5건 / 사진 10장**을 실제로 넣은 상태다(9.0 검증·9.4 카드 개발에 볼 사진이 필요했다).
- **경계는 이미 정해져 있었다 — 장부에만 안 들어왔다.** 커밋 메시지가 *"9.7 전량 시딩과 시드 2회 재실행 검증(#27)은 여전히 9.7의 일"* 이라 명시했고, Discord(2026-07-18 23:53)에도 *"소량은 지금, 전량·2회 검증은 9.7"* 합의가 있다. **판단은 옳았고 기록 위치가 틀렸다**(B8 — 미룬 것도 대장에 적는다).
- **9.7에 남은 일 (스토리 생성 시 인수조건 체크박스로 심을 것 — B5):**
  - [x] 100건 전량 시딩 — **on_sale 95건 중 90건**(사진 180장). 나머지 5건은 비-시드 판매자라 대상 밖(대응표 미매칭 0종)
  - [x] **시드 2회 연속 실행 후 `listing_images` 행 수 유지 확인**(#27 — "에러 0건 ≠ 정상", `ON DELETE CASCADE`가 조용히 지울 수 있다). 1회차·2회차 매물 id 동일 여부 기록
        → ⚠️ **확인 결과 "유지"가 아니었다: 10행 → 0행.** 체크박스는 *"확인한다"*였고 확인은 끝났으나 **답이 부정**이다. 결함은 `#89`로 승계했다 — 이 박스가 체크됐다고 위험이 사라진 게 아니다.
  - [x] `listings_update_own`에 `status <> 'sold'` 추가하는 마이그레이션(#54) — `0015`, red-green 후 원격 적용
  - [x] SM-A·CM-A·G3 검증(이 스토리가 exit-gate)
  - *(✎ 2026-07-21 코드리뷰: 위 4개가 **미체크인 채로 항목만 ✅ 해소**였다 — 체크박스와 결론이 같은 항목 안에서 충돌하던 자리라 실제 결과를 적어 닫는다. 특히 두 번째는 문구가 "유지 확인"인데 결과가 유지 아님이라, 체크만 하고 지나가면 정반대로 읽힌다.)*
  - *(✎ 2026-07-20 Story 9.5 코드리뷰: **"저작자 표시(credit) 화면 렌더" 항목을 제거했다.** 같은 날 #70이 ⚪ 의도적 보류로 닫혔는데(사용자 결정 — 공개 배포를 유지할 의사가 없어 표시 의무의 발생 조건이 없다) 여기 체크박스만 살아 있었다. 그대로 두면 B5 절차가 **취소된 작업을 9.7의 인수조건으로 심는다** — 대장이 자기모순이 되는 자리라 지운다. 되살아나는 조건은 #70에 있다.)*
- **왜 지금 9.7 스토리를 만들지 않았나:** 잔여 작업이 실제로 남은 정상 `backlog`이고, 스토리 생성은 `create-story`가 컨텍스트를 채워서 하는 일이다. 미리 만들면 반쪽짜리 문서가 하나 더 생긴다.
- **트리거:** 9.7 착수. **급하지 않다** — 전량 시딩이 필요한 시점은 9.7 자신이 종료 게이트이고, 제출·데모 마감일자는 어느 문서에도 없다(2026-07-19 실측).
- **부수:** 이 스크립트의 버그 3건(`sort_order` 구멍 · 업로드 후 INSERT 실패 시 고아 · 사전조회 페이지네이션 없음)과 라이선스 필터(#69)는 **코드리뷰에서 이미 수정됐다.** 남은 것은 위 목록뿐.
- ✅ **해소 (Story 9.7, 2026-07-21) — 위 체크박스 4건 전부 소화. 항목을 닫는다.**
  - **"100건 전량 시딩"은 문자 그대로는 불가능했고, 그 사실을 착수 전에 측정해 범위를 바꿨다.** 사용자 결정 = **A안("되는 만큼 전량", 커버리지 수치 목표를 세우지 않는다)**. 수치를 약속하면 Commons에 없는 모델을 채우려다 라이선스 필터를 느슨하게 만들 유인이 생긴다 — 그게 정확히 #69였다.
  - **결과**: `SEARCH_TERMS` 15종 → 76종. 시드 판매자 3명의 `on_sale` 90건 **미매칭 0건**, 사진 170장 신규 삽입 → **`listing_images` 10행/5매물 → 180행/90매물**, `credit` 180/180, 대표사진 매물당 정확히 1장.
  - **사진 없이 남은 `on_sale` 5건은 결함이 아니다** — 비밀번호를 모르는 비-시드 사용자 소유라 대상 밖이고, **AC2(사진 없는 매물 하위호환)의 실검증 재료**다. 목록 한 화면에 사진 카드와 플레이스홀더가 실제로 섞여 보이는 것을 확인했다.
  - ⚠️ **밟을 뻔한 함정 — "검색 결과가 있다"는 "그 차종이다"가 아니다.** Commons `gsrsearch`는 정확 일치가 아니라 관련도 순 전문검색이라, 후보 59종이 **전부 `allowed=3`** 으로 나왔다. 그대로 믿었다면 엉뚱한 차 사진이 붙었을 것이다. 반환 제목을 눈으로 확인하고 **대조군(존재하지 않는 차 이름 → 0건)** 으로 검색이 실제로 거르고 있음을 확인한 뒤에야 채웠다. 계열이 섞이는 자리(봉고3→K2500/K2700 형제차, 레이→컨셉카 일부)는 스크립트 주석에 `≈`로 표시했다.
  - **못 채운 모델 사유표**: **없다(0종).** 시드 판매자 소유 `on_sale` 90건 전부가 대응표에 매칭됐고, 검색 0건·허용 라이선스 없음으로 건너뛴 모델도 실행 로그상 0건이다.

### DW-369: [구 #69] 시드 라이선스 필터가 NC/ND를 통과시켰다 — **현재 위반 0건**

origin: 장부 통합 이관(구 docs/tech-debt.md #69) — 원출처: 코드리뷰 2026-07-19 발견·수정, 🟢 품질
location: `scripts/seed_listing_photos.py` (구 `ALLOWED_LICENSE_PREFIXES` / `startswith`)
severity: medium
reason: 이미 수정되었으나, "과제용이라 저작권은 넘어가도 된다"는 판단이 한 번 나왔던 자리라 같은 질문이 다시 나올 때 근거를 다시 세우지 않아도 되도록 기록만 남겨 둔다.
status: done 2026-07-29
resolution: 접두 매칭을 토큰 단위 `is_license_allowed()`로 교체하고 import 시 실행되는 assert 자체검사에 경계 사례를 못박음 — 함수 실재 확인(2026-07-29 실측)

- **위치:** `scripts/seed_listing_photos.py` (구 `ALLOWED_LICENSE_PREFIXES` / `startswith`)
- **내용:** `"cc by"` 접두 매칭이라 `CC BY-NC-SA`·`CC BY-ND`·`CC BY-NC-ND`가 전부 통과했다. docstring은 `CC-BY/CC-BY-SA/CC0/PD만`이라 적혀 있어 **문서와 코드가 갈렸다.** ND(2차 저작물 금지)가 특히 문제였다 — 이 스크립트는 1600px WebP로 **재인코딩·축소**하므로 그 자체가 금지된 2차 저작물이다.
- **실측(2026-07-19, 원격 DB 조회):** 이미 올라간 10장은 `CC BY-SA 4.0` 8 · `CC0` 1 · `CC BY 2.0` 1 — **NC·ND가 하나도 들어오지 않았다.** 실사고가 아니라 잠재 결함이었다.
- **✅ 수정:** 접두 매칭을 버리고 토큰 단위로 `nc`·`nd` 성분을 배제하는 순수 함수 `is_license_allowed()`로 교체. import 시 실행되는 `assert` 자체검사에 경계 사례를 못박음(`CC BY-SA 4.0`·`CC0`·`CC BY 2.0` 통과 / `CC BY-NC-SA 4.0`·`CC BY-ND 4.0`·`CC BY-NC-ND 3.0` 거부).
- **왜 대장에 남기나:** 수정됐지만 **"과제용이니 저작권은 넘어가도 된다"는 판단이 한 번 나왔던 자리**라, 다음에 같은 질문이 오면 근거(실측 0건 + 필터 강화)를 다시 세우지 않아도 되게 남긴다.

### DW-370: [구 #70] CC BY/BY-SA 사진 9장의 **저작자 표시 의무가 이행되지 않고 있다**

origin: 장부 통합 이관(구 docs/tech-debt.md #70) — 원출처: 코드리뷰 2026-07-19 등재 → ⚪ **의도적 보류**, 사용자 결정 2026-07-20
location: `scripts/seed_listing_photos.py`(저장은 함) ↔ `web/src/lib/images/coverImages.ts:16`(일부러 안 받음) · 렌더 코드 없음
severity: low
reason: 이 프로젝트는 과제·연습용이라 제출물이 아니고 공중 배포·송신 의사가 없어 CC BY 표시 의무가 발생하는 조건 자체가 없다고 사용자가 판단해 구현하지 않기로 결정했다.
status: open

- **위치:** `scripts/seed_listing_photos.py`(저장은 함) ↔ `web/src/lib/images/coverImages.ts:16`(일부러 안 받음) · 렌더 코드 없음
- **내용:** 시드는 저작자·라이선스·원본링크를 `listing_images.credit`(jsonb)에 **저장한다.** 그런데 그 값을 **화면에 표시하는 코드가 어디에도 없다.** 현재 10장 중 **9장**(`CC BY-SA 4.0` 8 + `CC BY 2.0` 1)이 표시 의무 대상이다.
- **왜 중요한가:** **비상업 이용이어도 CC BY 계열의 저작자 표시 의무는 면제되지 않는다.** NC/ND(#69)는 "상업이 아니니 무관"으로 넘어갈 수 있지만 BY는 그렇지 않다. 세 리뷰 레이어가 모두 이걸 못 짚었고, 실제 라이선스를 DB에서 조회하다 나왔다 — **"있는 것"과 "동작하는 것"의 차이**(B4)가 데이터 계층에서도 똑같이 났다: `credit`은 **있는데** 아무것도 **안 한다.**
- **오늘 무해하지 않은 이유:** 사이트가 실제로 배포돼 있다. 다만 사용자 판단(2026-07-19)으로 **과제 종료 후 배포를 내릴 예정**이라 위험 창이 한정적이다.
- **📅 예약: Story 9.5(상세 페이지 사진 갤러리)** — 갤러리가 `credit`을 읽을 자연스러운 첫 소비처다. **9.5 인수조건 체크박스로 심을 것**(B5): "사진에 `credit`(저작자·라이선스·원본링크)을 표시한다". 9.7의 전량 시딩(#68) 전에 심어야 100장으로 늘 때 함께 커버된다.
- **⚪ 결정 (사용자, 2026-07-20): 구현하지 않는다. 9.5 예약 해제.**
  - **판단 근거:** 이 프로젝트는 과제·연습용이고 제출물이 아니다(화면공유 시연 + 개인 열람). CC BY 계열의 표시 의무는 **공중에 배포·송신할 때** 발생하는데, 사용자가 배포를 공개로 유지할 의사가 없다(위 "과제 종료 후 배포를 내릴 예정"과 같은 판단의 연장).
  - **제시했던 선택지:** 표시 방식 A(갤러리 아래 한 줄)·B(ⓘ 팝오버)·C(하단 "사진 출처" 섹션) 3안을 실제 데이터로 목업까지 만들어 비교했고, 셋 다 구현 부담은 동등했다(조회 `select`에 `credit` 1컬럼 + 렌더 몇 줄). 즉 **비용이 아니라 필요 없음이 이유다.**
  - ⚠️ **되살아나는 조건:** `bmad-encar-demo.vercel.app`(Production)이 **공개 URL로 떠 있는 동안은 의무가 실재한다.** 배포를 내리거나 접근을 막으면 소멸한다. **공개 배포를 계속 유지하는 쪽으로 방향이 바뀌면 이 항목은 그 시점에 되살아난다** — 그때 위 3안 중 하나를 고르면 된다(목업 근거는 Story 9.5 Dev Notes §7).
  - **데이터는 그대로 둔다:** `listing_images.credit`은 계속 저장한다(시드 스크립트 무변경). 표시만 안 하는 것이라 나중에 켜는 비용이 낮다.
- ✎ **2026-07-21 코드리뷰 — 결정은 그대로지만 전제가 자기 작업으로 바뀌었다(사용자 확인 필요).**
  - **규모가 18배가 됐다.** 이 항목이 ⚪로 닫힐 때 대상은 **사진 9장**이었다. Story 9.7의 전량 시딩으로 `credit`이 채워진 사진은 **180장 전량**이 됐고, 버킷은 `0014`로 **공개 전환**돼 CC BY/BY-SA 원본이 **공개 접근 가능**하다.
  - **이게 결정을 뒤집나? 아니다.** 보류의 근거는 *"공개 배포를 유지할 의사가 없다"* 이지 *"장수가 적다"* 가 아니었다. 논리는 그대로 성립한다.
  - **그럼 왜 적나:** 위 "되살아나는 조건"이 ***"Production이 공개 URL로 떠 있는 동안은 의무가 실재한다"*** 인데, **배포는 여전히 떠 있고**(9.7 §4가 프로덕션 URL을 실제로 조회했다) 노출 규모만 18배가 됐다. **보류의 전제(위험 창이 한정적)가 자기 작업으로 커졌는데 항목을 열어보지도 않은 것**이 문제다 — 상위 결정을 인용만 하고 그 전제가 변했는지 안 보는 자리다.
  - 📌 **사용자에게 필요한 것 하나:** 과제 종료 후 배포를 내릴 계획이 **여전히 유효한지** 한 번 확인. 유효하면 이 항목은 ⚪ 그대로 두고, 공개를 계속 유지할 방향이면 위 3안 중 하나를 고른다(비용은 여전히 낮다 — `select`에 `credit` 1컬럼 + 렌더 몇 줄).

### DW-371: [구 #71] AI 응답 카드가 사진 있는 매물에도 "사진 준비중"을 표시한다

origin: 장부 통합 이관(구 docs/tech-debt.md #71) — 원출처: 코드리뷰 2026-07-19 등재, 🟢 품질
location: `web/src/components/ai/ChatAssistant.tsx:138` (`<ListingCard listing={l} />` — `attachCoverImages`를 거치지 않는다)
severity: medium
reason: 현재 AI 검색을 쓰는 사용자가 없어 실제 피해가 없고, 사진 경로를 붙이는 작업은 Story 9.6이 맡기로 이미 계획돼 있는데 9.7 시드가 9.6보다 먼저 실행되며 생긴 일시적인 공백이라 지금 고치지 않았다.
trigger: Story 9.6 착수 시 자동 소멸. 그 전에 AI 검색을 시연·공개해야 할 일이 생기면 그때는 플레이스홀더만 억제한다(좁은 대화 컬럼에 5:3 박스가 생기는 시각적 영향도 함께 사라진다).
status: open

- **위치:** `web/src/components/ai/ChatAssistant.tsx:138` (`<ListingCard listing={l} />` — `attachCoverImages`를 거치지 않는다)
- **내용:** AI 검색 결과는 api가 돌려주는데 `api/app/schemas/ai.py`의 `image_url`은 **항상 `None`**이다. 9.4가 `ListingCard`에 `ListingCardImage`를 넣으면서, 값이 없으면 5:3 "사진 준비중" 플레이스홀더가 그려진다. **시드(#68) 실행 전에는 모든 매물이 진짜로 0장이라 무해했으나, 지금은 사진 6장짜리 매물이 AI 답변에서만 0장이라고 말한다** — 화면이 사실과 다른 것을 단언한다.
- **왜 지금 안 고쳤나 (사용자 결정 2026-07-19):** 현재 AI 검색을 쓰는 사용자가 없어 실해가 없고, **계획 부재가 아니라 미착수**다 — `9-6-ai-응답-카드-사진`이 정확히 api에 사진 경로를 붙이는 스토리다. 9.7 시드가 9.6보다 먼저 실행되는 바람에 생긴 **일시적인 창**이다.
- **트리거:** Story 9.6 착수 시 자동 소멸. 그 전에 AI 검색을 시연·공개해야 할 일이 생기면 그때는 플레이스홀더만 억제한다(좁은 대화 컬럼에 5:3 박스가 생기는 시각적 영향도 함께 사라진다).

</details>

### DW-372: [구 #72] `getPublicUrl` web·dart 미러가 서로 다른 기법을 쓰는데 드리프트를 잡는 장치가 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #72) — 원출처: 코드리뷰 2026-07-19 이월, 🟢 품질
location: `web/src/lib/storage/index.ts:15-18` ↔ `app/lib/core/supabase/storage_helper.dart`
severity: medium
reason: 지금 각 플랫폼의 인코딩 규칙이 갈리는지 검증하는 공유 테스트를 만들어도 실제로 쓰이는 케이스가 없어(저장 키가 전부 uuid), 지금 만들면 안 쓰는 코드를 미리 만드는 것이라 미뤘다(A2).
trigger: 저장 키에 특수문자가 들어가는 변경(원본 파일명 보존 등). 그때 한 플랫폼에선 열리고 다른 쪽에선 400이 나며, #73 때문에 **앱은 조용히 플레이스홀더로 떨어진다.**
status: open

- **위치:** `web/src/lib/storage/index.ts:15-18` ↔ `app/lib/core/supabase/storage_helper.dart`
- **내용:** web은 `encodeURIComponent`로 URL을 **손수 조립**하고(`{url}/storage/v1/object/public/{bucket}/{path}`), Dart는 **SDK의 `getPublicUrl`에 위임**한다. `conventions.md` §10은 둘을 "두 곳에 미러"라 부르지만 인코딩 규칙이 같다는 보장이 없다 — `encodeURIComponent`는 `!'()*`를 남기고 `#?`를 이스케이프하는데 SDK 규칙은 다를 수 있고 버전에 따라 바뀔 수도 있다.
- **왜 안 잡히나:** `index.test.ts`는 **구현 자신의 공식**에 대고 단언하므로 드리프트를 원리적으로 못 잡는다. Dart 쪽엔 테스트가 없다. 9.0의 Debug Log는 uuid 파일명(인코딩이 no-op인 **유일한** 경우) 하나를 수동 curl로 확인했다.
- **오늘 무해한 이유:** 저장 키가 전부 uuid라 특수문자가 없다.
- **트리거:** 저장 키에 특수문자가 들어가는 변경(원본 파일명 보존 등). 그때 한 플랫폼에선 열리고 다른 쪽에선 400이 나며, #73 때문에 **앱은 조용히 플레이스홀더로 떨어진다.**
- **해소 방향:** 양 플랫폼이 공유하는 벡터 테이블(입력 경로 → 기대 URL)을 만들어 양쪽에서 같은 케이스를 돌린다. 지금 하면 안 쓰는 케이스를 위한 작업이라 미룬다(A2).
- **✎ 2026-07-20 Story 9.5 — 상속하지만 노출을 넓히지는 않는다(판단 결과 기록).** 상세 갤러리도 같은 `getPublicUrl`을 쓰므로 드리프트가 나면 함께 깨진다. 다만 **web 안에서 헬퍼를 하나 더 부르는 것**일 뿐 web↔dart 사이에 **새로운 비교면이 생기지는 않는다**(앱 상세는 Story 16.2). 저장 키가 전부 uuid라 오늘 무해하다는 조건도 그대로다 — **트리거·해소 방향 변경 없음.**

### DW-375: [구 #75] 저장형 XSS 근거가 **오리진을 잘못 지목한다** — 같은 문장이 4곳에 복사됨

origin: 장부 통합 이관(구 docs/tech-debt.md #75) — 원출처: 코드리뷰 2026-07-19 이월, 🟢 품질
location: `supabase/migrations/0014_listing_images_public_bucket.sql` 헤더 · `docs/conventions.md` §10 · Story 9.0 Dev Notes
severity: medium
reason: 위협 모델 문구가 실제로는 앱 오리진이 아니라 Supabase 프로젝트 호스트를 가리켜야 하는데, 사본이 4곳에 흩어져 있어 한 곳만 고치면 다시 갈리기 때문에 네 곳을 동시에 정정해야 하는 작업으로 남겨 두었다.
status: open

- **위치:** `supabase/migrations/0014_listing_images_public_bucket.sql` 헤더 · `docs/conventions.md` §10 · Story 9.0 Dev Notes
- **내용:** *".html/.svg가 올라가면 **우리 도메인에서** 실행되는 저장형 XSS가 된다"* 고 적혀 있으나, 객체는 `{SUPABASE_URL}/storage/v1/object/public/…` 즉 **Supabase 프로젝트 호스트**에서 서빙된다. **앱 오리진이 아니다.**
- **실제 노출면:** ① Supabase 오리진에서 실행되는 스크립트(그 오리진엔 대시보드 세션이 붙는다) ② 프로젝트 명의의 임의 파일 호스팅.
- **왜 방치하면 위험:** 잘못 적힌 위협 모델은 **없는 것보다 나쁘다.** 나중에 "`allowed_mime_types`를 완화해도 되나?"를 검토하는 사람이 *"앱 도메인은 무관하네"* 라고 **정확히 판단하고 분석을 종료**해 버린다 — 진짜 노출면을 못 보고.
- **해소:** 4곳의 문구를 동시에 정정한다(사본이 여러 개라 한 곳만 고치면 또 갈린다).

### DW-383: [구 #83] 상세 갤러리 썸네일이 **원본을 그대로 받는다** — AC2 미충족을 알고 수용

origin: 장부 통합 이관(구 docs/tech-debt.md #83) — 원출처: 코드리뷰 2026-07-20, 🟡 조건부 · 사용자 결정
location: `web/src/components/listings/ListingGallery.tsx`(썸네일 `<img src={url}>`가 대표와 같은 원본 URL) · `web/src/lib/listings.ts`의 `fetchListingGalleryUrls`
severity: high
reason: Supabase 이미지 변환은 유료 플랜 전용이라 막혀 있고(403 실측), 업로드 시 썸네일 생성은 I14(저장본을 다시 만들지 않는다)와 부딪히며, `next/image`는 아직 도메인 설정이 안 돼 있고 Vercel 과금 대상이라, 데모 규모(1~3장)에서는 실사용에 지장이 없다고 판단해 현 상태를 수용했다.
status: open

- **위치:** `web/src/components/listings/ListingGallery.tsx`(썸네일 `<img src={url}>`가 대표와 같은 원본 URL) · `web/src/lib/listings.ts`의 `fetchListingGalleryUrls`
- **무엇이 어긋났나:** Story 9.5 AC2가 *"첫 화면에 대표 1장 + 썸네일들만 로드한다. **큰 사진을 N장 미리 받지 않는다**"*(NFR7)라고 했는데, 썸네일이 80×56px 자리에 **1600px 원본**을 받는다. 완료 노트 #3은 이 구성이 "AC2를 만족한다"고 적었으나, AC2가 규정한 것은 DOM에 든 큰 `<img>` 개수가 아니라 **내려받는 바이트**다.
- **실측 (2026-07-20 코드리뷰, `curl`로 직접 잼):** 사진 3장 매물 `ff73b989` → 고유 원본 3개 **1,063 KB**(217 / 421 / 423 KB, 전부 1600px). 대표와 첫 썸네일은 같은 URL이라 4개 `<img>`가 3번 받는다.
- **왜 이렇게 됐나 (설계상 필연):** 이 프로젝트엔 **사진 크기가 한 종류뿐이다.** 9.3이 업로드 시 긴 변 ≤1600px·WebP로 줄여 저장하고 끝이며, 작은 판본을 만들지 않는 것은 I14(*"저장본을 다시 만들지 않는다"*)에 따른 **의도적 결정**이다. 썸네일이 쓸 작은 파일이 애초에 없었다.
- **왜 지금 안 고치나 (사용자 결정 2026-07-20):** 선택지를 다 재보고 골랐다.
  - **Supabase 이미지 변환은 막혀 있다** — 실측 `HTTP 403 {"error":"FeatureNotEnabled"}`. 유료 플랜 기능이라 이 프로젝트에선 못 쓴다. (코드를 짜기 전에 재서 확인했다)
  - **업로드 시 썸네일 규격 생성**은 I14와 부딪히고 업로드 코드·저장 경로·마이그레이션까지 번져 9.5 범위를 크게 넘는다.
  - **`next/image`**는 `next.config.ts`에 도메인 등록이 선행돼야 하고(현재 설정 파일이 비어 있다) Vercel 이미지 최적화가 과금 대상이다.
  - 데모 규모(사진 1~3장 = 약 1MB)에선 실사용에 지장이 없고, 9.5는 이미 브라우저 검증이 끝난 상태라 지금 이미지 경로를 건드리면 그 검증이 무효가 된다.
- **⚠️ 트리거 (이때 다시 연다):**
  - **#68 전량 시딩** — 매물당 사진이 5~10장이 되면 상세 1건이 **3~4MB**가 된다. 여기가 실제로 아파지는 지점이다.
  - **16.2 앱 상세** — 모바일 앱은 데이터 사용량에 더 민감하다.
  - **9.6 AI 응답 카드 사진** — 같은 패턴을 복사하지 말 것. 새 소비처를 만들 때 이 항목을 먼저 읽는다.
  - 실사용·공개 배포로 방향이 바뀔 때. 그때의 정답은 `next/image`(가장 싸게 되는 길)다.
- **함께 볼 것:** #80(용량 근거 숫자가 틀렸고, 그 숫자가 `next/image` 미채택 결정의 근거였다) · #73(조회 실패와 "사진 0장"이 구별 안 되는 문제)
- ✅ **2026-07-20 Story 9.6 — 이 항목이 지목한 대로 "먼저 읽고", 패턴을 복사하되 숫자를 실측했다.**
  - **결정: 같은 `ListingCardImage` 경로를 쓴다(새 최적화 도입 없음).** 9.5에서 사용자가 C안(현 상태 수용)으로 정했고, AI 카드만 다른 이미지 경로를 쓰면 목록/상세/AI가 3벌로 갈린다. AC8이 요구한 것도 "복사하지 말라"가 아니라 **"몰래 상속하지 말고 측정해서 기록하라"**였다.
  - **실측 (2026-07-20, `curl`로 대표사진 5장을 직접 받아 잼 — AI 카드가 실제로 고르는 그 파일들):**

    | 매물 | 대표사진 |
    |---|---|
    | 제네시스 GV70 | **274 KB** |
    | BMW X3 | **336 KB** |
    | 토요타 캠리 | **152 KB** |
    | 현대 팰리세이드 | **260 KB** |
    | 기아 카니발 | **217 KB** |
    | **AI 답변 1회 = 카드 5장 전부 사진일 때** | **1,241 KB (1,270,924 bytes)** |

  - **상세(#83 원문 3장 1,063KB)와 성격이 다르다:** 상세는 **한 매물의 여러 장**이고, AI 카드는 **여러 매물의 대표 1장씩**이다. 그래서 AI 쪽은 "사진 많은 매물" 하나가 아니라 **결과 개수(현재 LIMIT 5)** 가 상한을 정한다 — 매물당 사진이 10장이 돼도 AI 카드가 받는 양은 안 늘어난다(대표 1장만 받으므로). **#68 전량 시딩의 영향을 상세만큼 크게 받지 않는 경로**다.
  - **오늘 실측이 작게 나온 이유(과소평가 주의):** 44건 중 **사진이 있는 매물이 5건뿐**이라, 실제 브라우저 세션에서는 카드 5장 중 1장만 사진이 떴다(약 274KB). 위 1,241KB는 **5장 전부 사진일 때의 최악값**을 따로 계산한 것이다 — 시딩이 끝나면 이쪽이 일상값이 된다.
  - **브라우저 전송량은 못 쟀다(측정 한계, 추측 아님):** Supabase Storage 응답에 `Timing-Allow-Origin`이 없어 `PerformanceResourceTiming.transferSize`가 **0으로 나온다**(실측 확인). 그래서 위 숫자는 브라우저 계측이 아니라 `curl` 다운로드 크기다 — 압축·캐시 효과는 반영돼 있지 않다.
    - ✎ 2026-07-21 Story 9.7 재확인: 전량 시딩 후에도 동일하다. `responseStatus`·`encodedBodySize` 모두 교차출처 리소스 50건에서 `0`으로 관측됐다. **이 한계는 데이터가 늘어도 안 없어진다** — 브라우저 계측이 필요하면 Storage 응답 헤더를 바꿔야 한다.
- ✅ **2026-07-21 Story 9.7 — 트리거(#68 전량 시딩) 도달. 재측정했고, 예측한 3~4MB는 오지 않았다.**
  - **실측 (사진 3장짜리 상세 1건 — 현재 최다 장수):** 이미지 3장 합계 **995 KB**(436 / 350 / 208 KB) + HTML 32 KB = **약 1,028 KB.**
  - **왜 예측이 빗나갔나 — 예측이 틀린 게 아니라 전제가 안 왔다.** 이 항목은 *"매물당 5~10장이 되면"* 을 조건으로 달았는데, 시드 스크립트는 장수를 `[3,1,2,3,1,2,3,1]` 로 순환시켜 **일부러 1~3장으로 섞는다**("N장" 배지와 플레이스홀더가 한 화면에 같이 보여야 검증이 되므로). 그래서 **매물당 최대는 여전히 3장**이고 상세 1건은 9.5 때(1,063KB)와 거의 같다.
  - **즉 이 트리거는 소진되지 않았다.** 진짜 아파지는 조건은 "전량 시딩"이 아니라 **"매물당 사진 장수 증가"** 였다 — 트리거 문구를 그렇게 정정한다. 실사용자가 10장까지 올리는 경로(`/sell` 업로더는 이미 10장 상한)가 열리면 그때 도달한다.
  - **다만 목록 쪽 총량은 처음으로 유의미해졌다:** 대표사진 90장 합계 **약 20.1 MB**, 한 화면(4열×3행=12장) 환산 **약 2.7 MB**. 상세보다 **목록이 먼저 아파지는 구조**다 — 다음에 이 항목을 열 때는 상세가 아니라 목록부터 본다.
  - **남은 트리거**: 매물당 사진 장수 증가 · 16.2 앱 상세 · 실사용/공개 배포. 답은 여전히 `next/image`.
  - ~~**트리거 변경 없음.** 다시 열 지점은 여전히 #68 전량 시딩 · 16.2 앱 · 실사용 배포~~ ✎ **2026-07-21 코드리뷰: 이 줄을 지운다.** 바로 위 두 줄이 트리거를 *"매물당 사진 장수 증가"* 로 **정정했는데** 이 줄만 *"변경 없음 · #68 전량 시딩"* 이라 정반대를 말하고 있었다(대시보드는 정정 쪽을 인용 → 다음 사람이 둘 중 하나를 동전 던지기로 고른다). **#68 전량 시딩은 이미 도달했고 트리거로서 소진됐다.** 이 스토리의 AC7이 *"항목에 줄을 더할 땐 위쪽에 그걸 부정하는 줄이 있는지부터 본다"* 고 명시했는데 그대로 반복된 자리다.

### DW-380: [구 #80] 사진 용량 근거 **"실측 196~205KB"가 실제와 다르다** (실측 217·421·423 KB) — 여러 결정이 이 숫자에 기대고 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #80) — 원출처: 코드리뷰 2026-07-20 이월, 🟢 품질/문서
location: `_bmad-output/implementation-artifacts/9-5-…md`(AC2 본문·Dev Notes) · `9-4-…md` · `web/src/components/listings/ListingGallery.tsx` 헤더 주석
severity: medium
reason: 숫자 자체를 고치는 것은 쉽지만 그 숫자가 `next/image` 미채택 등 이미 내려진 결정의 근거였기 때문에, 고치려면 그 결정들도 함께 재검토해야 해서 #83과 묶어 다루려고 미뤘다.
trigger: #83이 다시 열릴 때 같이(=#68 전량 시딩). 또는 9.4 카드 이미지를 손대는 스토리.
status: done 2026-07-29
resolution: Story 9.7이 `ListingCardImage.tsx` 주석을 실측값으로 정정 — 확인 완료. 결정(next/image 미채택)을 다시 볼 자리는 DW-383(구 #83)이 갖는다

- **위치:** `_bmad-output/implementation-artifacts/9-5-…md`(AC2 본문·Dev Notes) · `9-4-…md` · `web/src/components/listings/ListingGallery.tsx` 헤더 주석
- **실측 (2026-07-20, 코드리뷰):** 사진 3장 매물 `ff73b989`의 원본을 직접 받아 쟀다 — **217 KB / 421 KB / 423 KB**, 셋 다 **1600px** 폭. 9.3의 다운스케일(긴 변 ≤1600px·WebP·q0.82)은 **지켜지고 있다**(치수는 맞다). 틀린 것은 **용량 숫자**이고, 2건이 인용값의 **2배 이상**이다.
- **왜 중요한가:** "저장본이 이미 196~205KB로 작다"가 **두 결정의 근거로 쓰였다** — ① `next/image`를 쓰지 않기로 한 것(9.4·9.5), ② 썸네일 별도 규격을 만들지 않기로 한 것(9.5 Completion Note #3). 근거 숫자가 2배 틀리면 그 절충의 무게가 달라진다. 결정 자체가 틀렸다는 뜻은 아니고, **재검토 없이 다음 스토리로 인용되면 안 된다**는 뜻이다.
- **왜 이월:** 숫자를 고치는 것은 쉽지만, 고치면 위 두 결정을 다시 봐야 한다 — 그건 **#83과 같은 자리**라 함께 다뤄야 한다. (#83은 "현 상태 수용"으로 닫혔고, 그 수용의 근거 중 하나가 바로 이 숫자다)
- **아직 안 고친 자리:** `web/src/components/listings/ListingCardImage.tsx:54`와 9.4 스토리 문서에 "196~205KB"가 그대로 남아 있다. 9.5의 `ListingGallery.tsx` 헤더 주석은 코드리뷰에서 정정했다(A3 — 이 스토리가 만든 자리만 고쳤다).
- **트리거:** #83이 다시 열릴 때 같이(=#68 전량 시딩). 또는 9.4 카드 이미지를 손대는 스토리.
- ✎ **2026-07-20 Story 9.6 — 세 번째 독립 실측이 이 정정을 다시 확인했다.** AI 카드가 고르는 대표사진 5장을 `curl`로 직접 재니 **152 / 217 / 260 / 274 / 336 KB** — **5장 전부가 "196~205KB" 범위 밖**이고(152는 하한 아래, 나머지 넷은 상한 위) 최대값은 상한의 **1.6배**다. *(✎ 2026-07-20 코드리뷰 정정: 원래 "5장 중 4장"이라 적혀 있었으나 검산하면 5/5다. 이 항목의 존재 이유가 "검산 안 한 숫자가 결정을 오염시켰다"인데 정정 문장이 같은 실수를 반복했다.)* 이제 이 숫자가 틀렸다는 근거는 서로 다른 스토리의 실측 2건(#83의 217·421·423, 9.6의 위 5건)이다.
- ⚠️ **아직 안 고친 자리는 그대로다:** `web/src/components/listings/ListingCardImage.tsx:54`의 주석과 9.4 스토리 문서에 "196~205KB"가 **남아 있다.** 9.6은 그 파일을 **의도적으로 건드리지 않았다**(A3 — 이 스토리의 web 변경은 `aiSearch.ts` 매핑 한 겹으로 한정했고, 카드 컴포넌트는 범위 밖으로 명시돼 있었다). **9.6이 그 주석을 읽는 소비처를 하나 더 늘렸으므로**(AI 카드) 틀린 숫자를 믿을 사람이 늘었다는 점은 기록해 둔다 — 위 트리거("9.4 카드 이미지를 손대는 스토리")에서 반드시 함께 고칠 것.
- ✅ **해소 (Story 9.7, 2026-07-21) — 트리거 도달(전량 시딩 + 카드 이미지 경로를 실측하는 스토리). 주석을 실측값으로 정정했다.**
  - **모집단이 처음으로 충분해졌다.** 이전 실측은 3장·5장짜리 표본이었는데, 이번엔 **대표사진 90장 전부**를 `HEAD`로 재서 분포를 얻었다:

    | 최소 | 중앙값 | 평균 | 최대 | "196~205KB" 구간에 드는 장수 |
    |---|---|---|---|---|
    | **50 KB** | **197 KB** | **229 KB** | **615 KB** | **90장 중 1장** |

  - 🔍 **이 항목의 진짜 교훈이 여기서 드러난다.** 중앙값이 197KB라 **"196~205KB"는 우연히 중앙값 근처였다** — 그래서 세 번의 소표본 실측 동안 "완전히 엉뚱한 숫자"로는 안 보였다. 틀린 것은 **값이 아니라 형태**다: 실제 분포는 50~615KB로 **12배 편차**인데, 그걸 **폭 9KB짜리 좁은 범위로 단언**해 놓은 것이 오류였다. 200KB 초과 45장(절반) · 300KB 초과 18장.
  - ✅ **정정 반영**: `ListingCardImage.tsx`의 주석을 위 분포로 교체했다. **결론(`next/image` 미채택)은 바꾸지 않는다** — 중앙값 기준으로 "저장본이 작다"는 여전히 성립하고, 결정을 다시 볼 자리는 #83(그쪽에서 "목록이 상세보다 먼저 아파진다"로 갱신됨)이다.
  - **남은 자리**: 9.4 스토리 문서(`9-4-…md`)의 "196~205KB"는 **과거 시점의 기록물**이라 고치지 않는다(A3 — 스토리 문서는 그때의 판단을 보존하는 경위 문서다. 제약이 아니라 경위이므로 정본은 코드 주석 쪽이다).

### DW-381: [구 #81] 정렬 비교 로직이 **두 벌**이다 — `galleryImages`·`coverImages`

origin: 장부 통합 이관(구 docs/tech-debt.md #81) — 원출처: 코드리뷰 2026-07-20 이월, 🟢 품질
location: `web/src/lib/images/galleryImages.ts:32-35` · `web/src/lib/images/coverImages.ts`
severity: medium
reason: 합치려면 비교자를 공용 모듈로 빼고 양쪽 import를 바꿔야 하는데, 지금 그걸 하면 9.4가 검증해 둔 `coverImages` 경로를 이 스토리 범위 밖에서 건드리게 된다(A3).
trigger: 세 번째 소비처가 생길 때 — 그때는 테스트로 묶는 것보다 합치는 게 싸다. (후보: 9.6 AI 응답 카드 사진, 16.2 앱 상세)
status: open

- **위치:** `web/src/lib/images/galleryImages.ts:32-35` · `web/src/lib/images/coverImages.ts`
- **내용:** AC3은 *"대표 판별 로직을 새로 만들지 않는다 — 계산 자리는 `coverImages.ts` 하나다"* 라고 못 박았는데, `galleryImages.ts`가 `sort_order` → `id` 비교자를 **자기 것으로 하나 더** 갖는다. 두 함수의 모양이 다르므로(여러 매물의 대표 1장 vs 한 매물의 전 장) 재사용이 자명하지 않았던 것은 사실이다.
- **왜 지금 위험하지 않은가:** `galleryImages.test.ts`가 `galleryImages(rows)[0] === coverImages(rows).get(...)?.coverPath`를 **단언**해 두 벌이 갈리는 순간 red가 난다. 규칙 위반이지만 **검사로 묶여 있다**(B9의 취지는 충족).
- **왜 이월:** 합치려면 비교자를 공용 모듈로 빼고 양쪽 import를 바꿔야 하는데, 지금 그걸 하면 9.4가 검증해 둔 `coverImages` 경로를 이 스토리 범위 밖에서 건드린다(A3).
- **트리거:** 세 번째 소비처가 생길 때 — 그때는 테스트로 묶는 것보다 합치는 게 싸다. (후보: 9.6 AI 응답 카드 사진, 16.2 앱 상세)
- ✅ **2026-07-20 Story 9.6 — 세 번째 소비처가 생겼는데 비교자는 안 늘었다(2벌 유지).**
  - **어떻게:** AI 카드의 대표 판별을 **파이썬 코드가 아니라 SQL이** 한다 — `listing_cards.py`의 고정쿼리가 `DISTINCT ON (listing_id)` + `ORDER BY listing_id, sort_order, id`로 매물별 첫 행을 고르고, 파이썬은 돌아온 행을 **다시 정렬하지 않고** 그대로 받는다. 그래서 세 번째 비교자 사본이 만들어지지 않았다.
  - **강제 장치:** `api/tests/test_listing_cards.py::test_query_orders_by_sort_order_then_id` — `ORDER BY i.listing_id, i.sort_order, i.id`를 **통째로** 단언하고, `is_cover`를 읽지 **않는지**도 본다(파생값을 읽으면 목록 카드와 대표가 갈린다).
  - ✎ **2026-07-20 코드리뷰 정정:** 원래 `"sort_order" in q and "id" in q` 부분문자열 단언이었다. `"id"`가 **`"listing_id"`의 부분문자열**이라 2차 키 `i.id`를 **지워도 통과했다**(실측: 8/8 green). 이 항목이 우려한 회귀(2차 키 유실 → 호출마다 대표가 바뀜)를 정작 그 강제 장치가 못 잡고 있었다.
  - **⚠️ 그래서 이 항목의 성격이 바뀌었다:** 이제 같은 규칙이 **3곳**에 서로 다른 형태로 산다 — TS 비교자 2벌(`coverImages.ts`·`galleryImages.ts`) + **SQL `ORDER BY` 1벌**. TS 두 벌은 `galleryImages.test.ts`가 서로 대조해 묶여 있지만, **SQL 쪽은 그 대조 밖에 있다**(언어가 달라 같은 테스트로 묶을 수 없다). 즉 web의 규칙이 바뀌면 api가 조용히 뒤처질 수 있다 — 대신 규칙 자체가 `conventions.md` §10.2에 정본으로 있고 양쪽이 그걸 인용한다.
  - **트리거 갱신:** 여전히 "합치는 게 싸질 때"지만, 이제 후보는 **16.2 앱 상세**(Dart 비교자가 네 번째로 생길 자리)다. 그때는 TS 2벌 통합보다 **§10.2를 어기면 red가 나는 크로스-언어 벡터 테이블**이 더 값싼 답일 수 있다(#72가 같은 모양의 문제를 갖고 있다 — 함께 볼 것).

### DW-385: [구 #85] `listing_images.storage_path`의 **모양을 검증하는 곳이 하나도 없다**

origin: 장부 통합 이관(구 docs/tech-debt.md #85) — 원출처: 코드리뷰 2026-07-20 이월, 🟢 품질
location: `supabase/migrations/0012_listing_images.sql:21`(`storage_path text not null unique` — CHECK 제약 없음) · RLS `listing_images_insert_own`(`:119`)은 **매물 소유권만** 확인하고 경로 모양은 안 본다 · `web/src/lib/storage/index.ts`의 `getPublicUrl`
severity: medium
reason: 9.6이 만든 문제가 아니라 0012부터 있던 결함이고, 제대로 막으려면 DB CHECK 제약을 더하는 마이그레이션이 필요한데 9.6의 Dev Notes §0이 `supabase/migrations/**`를 범위 밖으로 못박아 두었다(A3).
trigger: 사진 업로드 경로를 다시 손대는 스토리 — **Epic 16.2(앱 사진 업로더)** 가 새 쓰기 경로를 여는 자리다. 그 전에 `listing_images`에 마이그레이션을 걸 일이 생기면 같이 처리.
status: open

- **위치:** `supabase/migrations/0012_listing_images.sql:21`(`storage_path text not null unique` — CHECK 제약 없음) · RLS `listing_images_insert_own`(`:119`)은 **매물 소유권만** 확인하고 경로 모양은 안 본다 · `web/src/lib/storage/index.ts`의 `getPublicUrl`
- **내용:** 계약(§10)은 `{user_id}/{listing_id}/{filename}` 3단 경로를 요구하지만 **강제하는 검사가 DB·api·web 어디에도 없다.** 판매자가 자기 매물에 `../../foo`나 선행 `/`가 든 경로를 넣으면 그대로 저장되고, `getPublicUrl`의 `encodeSegments`는 `/`로 쪼개 각 조각만 인코딩하는데 `encodeURIComponent('..') === '..'`라 **traversal 조각이 그대로 살아남는다.**
- **왜 지금 실해가 작은가(실측 아님, 코드 경로 추적):** 브라우저가 URL을 정규화해 다른 Storage 엔드포인트를 때리고 404가 나면 `ListingCardImage`의 2겹 폴백이 잡아 **"사진 준비중" 플레이스홀더**로 떨어진다. 깨진 아이콘은 안 뜬다. 즉 **검증자가 할 일을 폴백이 대신하고 있다.**
- **왜 이월:** 9.6이 만든 문제가 아니다(0012부터 그랬다). 제대로 막으려면 DB CHECK 제약을 더하는 마이그레이션이 필요한데, 그건 9.6의 Dev Notes §0이 `supabase/migrations/**`를 범위 밖으로 못 박은 자리다(A3).
- **해소 방향:** `check (storage_path ~ '^[^/]+/[^/]+/[^/]+$')` 마이그레이션 1건. **기존 행이 전부 이 모양인지 먼저 실측**한 뒤 걸 것(안 그러면 마이그가 실패한다). 앱 코드로 막는 건 화면 하나 더 만들 때 까먹으므로 데이터 계층이 맞다(B9).
- **트리거:** 사진 업로드 경로를 다시 손대는 스토리 — **Epic 16.2(앱 사진 업로더)** 가 새 쓰기 경로를 여는 자리다. 그 전에 `listing_images`에 마이그레이션을 걸 일이 생기면 같이 처리.

### DW-388: [구 #88] E2E 도구(Playwright MCP)의 **클릭·키 입력이 페이지에 도달하지 않는다** — **네 번째 발생**, 원인 미규명

origin: 장부 통합 이관(구 docs/tech-debt.md #88) — 원출처: 2026-07-21 갱신, 🟢 품질
location: n/a
severity: medium
reason: 네 차례 관찰했지만 원인을 특정하지 못했고(환경·오버레이·ref 방식 가설은 모두 기각됨) 재현 조건이 간헐적이라, 근본 원인을 좁히기 전까지는 우회 규칙(재진입 → 그래도 안 되면 JS 우회)으로만 대응하고 있다.
trigger: **Epic 11.5(SM-B 뷰포트 E2E 감사)** — 첫 Playwright 스펙을 세우는 자리라 여기서 안 풀면 스펙 전체가 우회 코드로 덮인다. #86(검증 산출물 재실행 불가)과 같은 자리에서 함께 처리한다.
status: open

- **증상:** `browser_click`·`browser_press_key`가 **성공을 보고하는데 페이지에는 아무 이벤트도 안 온다.** 실패도, 콘솔 에러도, 네트워크 요청도 없다 — 조용한 무동작이다.
- **왜 등재하나:** **세 번째다.** Story 9.6 dev(Debug Log §4) · 9.6 코드리뷰 E2E 서브에이전트 · 이번 직접 조사. 앞의 두 번은 각각 우회하고 "도구 문제"로 넘겼는데, **넘긴 기록이 대장에 없어서 세 번째 사람이 처음부터 다시 진단했다**(B8 — 미룬 것도 적는다).

- **실측 (2026-07-20, 운영 배포 `bmad-encar-demo.vercel.app/ai`, buyer 계정):**

  | 무엇 | 결과 |
  |---|---|
  | `document`에 capture 리스너를 걸고 `browser_click` → `pointerdown`·`click`·`submit` | **전부 0건** (3회 재현, 스냅샷·ref 갱신 후에도 동일) |
  | 같은 리스너에서 `btn.click()` (페이지 안 JS) | `click`(isTrusted:false) + **`submit`(isTrusted:true)** 정상, 검색 5건 실제 수행 |
  | `browser_press_key('Enter')` (입력란 포커스 상태) | **0건**, 미제출 |
  | `browser_click`으로 입력란 클릭 | 이벤트 0건인데 **`document.activeElement`는 바뀜** |
  | 같은 세션 `/login`에서 `browser_click`으로 로그인 버튼 | **정상 작동**(로그인돼 `/`로 이동) |

- **틀린 것으로 밝혀진 기존 진단:** 9.6 Debug Log §4는 *"입력값이 React state에 반영되지 않아서"* 라고 적었다. **아니다** — React fiber의 `__reactProps$.value`를 직접 읽어 DOM 값과 **동일하게 동기화돼 있음**을 확인했다. 폼도 정상이다(`onSubmit` 부착됨, 버튼 `type=submit`·`disabled=false`·`pointer-events:auto`, `elementFromPoint`가 그 버튼을 반환, 폼·버튼 각 1개, iframe·중복 마운트 없음).
- **패턴 (관찰된 규칙, 원인 아님):** **페이지에 JS를 주입하는 조작**(`browser_evaluate`, `fill()` 기반 `browser_type`)은 **작동**하고, **브라우저의 실제 입력 파이프라인을 타는 조작**(`browser_click`, `browser_press_key`)은 **도달하지 않는다.**
- ⚠️ **원인은 규명 못 했다.** 왜 같은 세션의 `/login`에서는 클릭이 먹었는지 설명하지 못한다. 추측을 근거로 적지 않는다.
- **제품 결함이 아님은 확정:** 사용자가 실제 브라우저에서 직접 눌러 정상 동작을 확인했다(2026-07-20, 스크린샷 — 답변 + 카드 4장). 페이지 안 프로그램적 클릭도 끝까지 성공한다.

- **당장의 작업 규칙 (다음 사람이 바로 쓸 것):**
  1. **클릭·키 입력 뒤에는 반드시 "무슨 일이 일어났는지"를 단언한다.** 도구가 성공을 보고해도 믿지 않는다 — 이번 건의 본질이 *성공 보고 + 무동작*이다.
  2. 아무 일도 안 일어났으면 `browser_evaluate`로 우회한다(네이티브 setter로 값 주입 → `input` 이벤트 dispatch → `form.requestSubmit()` 또는 `btn.click()`).
  3. **우회했다는 사실을 결과에 남긴다.** 그러면 "사람 손 경로는 미검증"임이 보고서에 보인다.
- ✎ **2026-07-20 추가 조사 — 환경 가설 기각, 그리고 재현이 사라졌다(간헐성 확인).**
  사용자가 *"개발 장비가 외부에 있고 SSH(Tailscale)로 접속해 작업한다 — 이게 원인일까"* 라고 물어 **측정으로 답했다.**

  | 무엇을 쟀나 | 값 | 뜻 |
  |---|---|---|
  | `navigator.userAgent` | **HeadlessChrome/149** | 헤드리스라 **디스플레이를 아예 안 쓴다** → SSH·원격 데스크톱 유무와 무관 |
  | `document.visibilityState` / `hidden` / `hasFocus()` | `visible` / `false` / **`true`** | 창이 가려지거나 포커스를 잃은 상태가 **아니다**(그 가설 기각) |
  | `example.com`에서 `browser_click` | **정상**(링크 눌려 이동) | 브라우저·세션의 입력 경로 자체는 **멀쩡** |
  | 전송 버튼 위 `elementsFromPoint` 스택 | BUTTON→FORM→…→HTML, 큰 오버레이 **0개** | 투명 레이어가 가로채는 것도 **아니다** |

  → **환경(SSH/Tailscale/헤드리스)·앱·오버레이·ref 방식 전부 기각됐다.**

  **그리고 결정적으로, 재현이 사라졌다.** 같은 세션에서 조사 초반엔 **3회 연속 무동작**이었는데, `example.com`을 거쳐 `/ai`로 다시 들어간 뒤로는 **4회 연속 정상**이다(CSS 셀렉터·스냅샷 ref 둘 다, 입력 후 클릭까지 포함해 검색이 실제로 수행됨). 코드는 한 줄도 안 바뀌었다.

  **관찰된 유일한 차이:** 실패 구간은 `/login`에서 로그인 → **앱의 클라이언트 사이드 리다이렉트**로 `/`에 간 뒤 `/ai`로 이동한 경로였다. 성공 구간은 그 리다이렉트를 거치지 않았다. **가설일 뿐 증명하지 않았다** — 다만 다음 사람이 좁혀 볼 첫 지점이다.

- ✎ **2026-07-21 네 번째 발생 — 위 가설을 그대로 재현했고, 같은 세션 안에 대조군이 생겼다** (Epic 9 종료 후 전체 테스트, develop Preview 배포).

  이번엔 **한 세션 안에서 성공과 실패가 모두 관찰돼** 지금까지 중 가장 깨끗한 대조가 됐다.

  | 순서 | 무엇 | `browser_click` | 로그인 리다이렉트를 거쳤나 |
  |---|---|---|---|
  | ① | 상세 갤러리 `[다음 사진]` | **정상** — 카운터 `1/3 → 2/3`, 대표 img src 교체 확인 | ❌ 아직 비로그인 |
  | ② | `/login` 로그인 버튼 | **정상** — `/`로 이동, 계정 표시됨 | ❌ (리다이렉트를 *만든* 쪽) |
  | ③ | `/ai` 전송 버튼 | **무동작** — 본문 136자 그대로, 요청 0건 | ✅ 로그인 → CSR 리다이렉트 → `/ai` |
  | ④ | `/ai` `browser_type(submit:true)` (Enter) | **무동작** — 동일 | ✅ 같은 경로 |
  | ⑤ | `browser_evaluate` 네이티브 setter + `submit` dispatch | **정상** — 카드 5장·사진 5장 렌더 | — (JS 주입이라 해당 없음) |

  → **①이 결정적이다.** 같은 세션·같은 도구·같은 배포에서 로그인 **전**에는 클릭이 먹었고, 로그인 리다이렉트를 거친 **뒤**에는 안 먹었다. 2026-07-20이 "가설일 뿐"이라 적은 그 경로가 **독립 세션에서 재현**된 것이다. 여전히 원인은 아니고 **상관**이다 — 그러나 이제 우연으로 보기는 어렵다.

  **작업 규칙 2번을 정정한다.** 2026-07-20이 *"JS 우회보다 먼저 페이지를 다시 열 것 — 재진입이 입력 경로를 되살렸다"* 고 적었는데, **이번엔 `/ai` 재진입(`browser_navigate`)으로 살아나지 않았다.** 07-20의 회복은 단순 재진입이 아니라 **`example.com`(다른 오리진)을 경유한 뒤**였다. 재진입만으로는 부족할 수 있으므로 규칙을 이렇게 읽어라: **① 다른 오리진을 한 번 경유해 재진입 → ② 그래도 안 되면 JS 우회.**

  **이번 검증에서 미검증으로 남은 것:** `/ai`에서 **사람이 마우스로 전송을 누르는 경로**. 9.6·9.6리뷰에 이어 세 번째로 이 자리가 비었다 — 이 항목이 닫히기 전까지 `/ai` 제출은 계속 JS 우회로만 확인된다.

- **⚠️ 작업 규칙 갱신 (앞의 3개를 이걸로 대체):**
  1. **클릭·키 입력 뒤에는 반드시 결과를 단언한다** (이건 그대로 — 본질이 *성공 보고 + 무동작*이다).
  2. 무동작이면 **JS 우회보다 먼저 `browser_navigate`로 페이지를 다시 연다.** 이번 실측에서 재진입이 진짜 입력 경로를 되살렸다. **JS 우회는 사람 손 경로를 검증 못 하게 만드므로 최후 수단이다** — 9.6에서 두 번 다 곧장 JS로 넘어가는 바람에 "사람이 누르면 되는가"가 미검증으로 남았다.
  3. 그래도 안 되면 JS로 우회하되, **우회했다는 사실을 결과에 반드시 남긴다.**
- **해소 방향:** 위 "클라이언트 사이드 리다이렉트 직후" 가설부터 좁힌다(로그인 → 리다이렉트 → `/ai` 경로를 여러 번 반복해 재현률을 잰다). 재현되면 Playwright MCP 이슈로 보고할 재료가 된다. 재현이 안 되면 규칙 2번으로 충분하다.
- ✎ **2026-07-21 Story 9.7 — "네 번째 관측"이라고 적었다가 **철회**했다. 도구는 정상이었고 내가 엉뚱한 곳을 봤다.**
  - **무슨 일이 있었나**: `browser_take_screenshot(filename: "search-1280.png")`·`browser_network_requests(filename: "net-search.txt")`가 성공을 보고했는데 `.playwright-mcp/`에 파일이 없었다. 이 항목의 증상(*성공 보고 + 무동작*)과 모양이 같아 **네 번째 발생으로 등재했다.**
  - **사실**: 두 파일 다 **정상 생성돼 있었다.** 다만 저장 위치가 `.playwright-mcp/`가 아니라 **레포 루트**였다(응답의 `./search-1280.png`는 문자 그대로 cwd 기준이었다 — `filename`을 생략했을 때만 `.playwright-mcp/` 아래로 간다). `git status`에 두 파일이 잡히면서 드러났다.
  - 🔻 **이 오진 자체가 이 항목의 교훈을 위반한 사례라 남긴다.** 이 항목의 첫 번째 작업 규칙이 *"도구가 성공을 보고해도 믿지 않고 결과를 단언한다"* 인데, **나는 반대 방향으로 같은 실수를 했다 — 도구가 실패했다고 단언하면서 그 단언을 검증하지 않았다.** `ls`를 한 디렉터리에서만 하고 "없다"고 결론지었다. **의심도 측정해야 한다**(B4 — 재보기 전엔 선언하지 않는다. 결함이 있다는 선언도 선언이다).
  - **작업 규칙에 한 줄 추가**: 4. **"도구가 고장났다"는 결론도 증거를 요구한다.** 특히 이 항목처럼 *이미 알려진 결함*이 있으면 새 증상을 거기에 갖다 붙이기 쉽다 — 그러면 **대장이 없는 결함을 키운다.** 파일이 안 보이면 **cwd 기준으로 레포 전체를 먼저 찾는다.**
- **트리거:** **Epic 11.5(SM-B 뷰포트 E2E 감사)** — 첫 Playwright 스펙을 세우는 자리라 여기서 안 풀면 스펙 전체가 우회 코드로 덮인다. #86(검증 산출물 재실행 불가)과 같은 자리에서 함께 처리한다.

---

### DW-403: [구 #103] `0002b_listings_created_at_immutable`이 **원격 원장에는 있는데 그 보호장치가 원격 DB에 없다**

origin: 장부 통합 이관(구 docs/tech-debt.md #103) — 원출처: #101 조사 중 발견, 2026-07-21 등재, 🟡 조건부
location: 원격 마이그 원장 `20260619210838 / 0002b_listings_created_at_immutable` · `public.listings`
severity: high
reason: created_at을 못 고치게 막는 장치가 언제·왜 사라졌는지 확인할 수 없고(0002b 마이그레이션 원문이 레포에 없음) 지금은 정렬에 영향받는 기능이 없어 위험이 실현되지 않으므로, 정렬·노출 순서를 다루는 스토리에서 재판단하기로 미뤘다.
status: open

- **위치:** 원격 마이그 원장 `20260619210838 / 0002b_listings_created_at_immutable` · `public.listings`
- **실측 (2026-07-21, 원격 DB 직접 조회):** 이름이 말하는 "등록일시(`created_at`)를 나중에 못 고치게 막는" 장치를 **세 경로 모두에서 찾지 못했다.**

  | 찾은 곳 | 결과 |
  |---|---|
  | `listings`의 트리거 | 6개 — `created_at` 관련 **없음** |
  | `listings`의 CHECK 제약 | 12개 — 전부 값 범위(제조사·연식·가격 등), `created_at` **없음** |
  | `listings.created_at`의 컬럼 권한 | `authenticated`에 `UPDATE` **허용됨** (revoke 흔적 없음) |
- **그래서 지금 무슨 일이 가능한가:** 판매자가 자기 매물의 `created_at`을 임의로 바꿀 수 있다 — 목록이 최신순 정렬이면 **오래된 매물을 맨 위로 끌어올릴 수 있다.** (RLS `listings_update_own`은 "자기 매물인지"만 보지 어느 컬럼인지는 안 본다.)
- **⚠️ 미확정:** 원래 그런 장치를 만들었다가 나중 마이그가 덮어썼는지, 처음부터 다른 방식이었는지 **확인 못 했다.** `0002b`는 레포에 커밋된 적이 없어(`conventions.md` §9.2가 명시) **내용을 볼 수 없다.**
- **로컬 개발 DB와는 무관:** 로컬은 원격과 동일한 상태이므로(컬럼 50·정책 35·트리거 6 일치) 재현에 문제 없다. **이건 원격 자체의 열린 질문이다.**
- **📅 재판단 시점: `listings` 정렬·노출 순서를 건드리는 스토리(Epic 11.4 인기·최신 매물 그리드).** 그때 "최신순"이 조작 가능한지가 실제 문제가 된다.

### DW-405: [구 #105] 브랜치별 DB 설정 자동 전환이 **`main`에서는 아직 안 돈다** — 훅 파일이 그 브랜치에 없기 때문

origin: 장부 통합 이관(구 docs/tech-debt.md #105) — 원출처: 2026-07-21 등재 → **`develop`은 같은 날 병합으로 해소**, `main`은 열린 채, 🟡 조건부
location: `.githooks/post-checkout` · `scripts/use-env.sh` (현재 `test/bmad-loop` 브랜치에만 존재)
severity: high
reason: 어긋나는 방향이 안전한 쪽이라(운영이어야 할 자리에 로컬이 남을 뿐 반대 방향은 없다) 급하지 않았고, 이 문제는 별도 작업이 아니라 훅 파일이 병합으로 그 브랜치에 도달하면 자동 해소되는 성격이라 main 병합 승인 시점까지 미뤘다.
status: open

- **위치:** `.githooks/post-checkout` · `scripts/use-env.sh` (현재 `test/bmad-loop` 브랜치에만 존재)
- **무엇:** 체크아웃 훅은 **이동한 뒤의 작업트리**에서 실행된다. `main`으로 옮기면 그 순간 `.githooks/post-checkout`과 `scripts/use-env.sh`가 **작업트리에서 사라지므로** 훅이 아예 돌지 않는다.
- **실측 (2026-07-21, 커밋 후 실제 체크아웃):**

  | 브랜치 | 훅 파일 | 스크립트 | `web/.env.local`이 가리키는 곳 |
  |---|---|---|---|
  | `test/bmad-loop` | 있음 | 있음 | `127.0.0.1:55321` (로컬) ✅ |
  | `main` | **없음** | **없음** | `127.0.0.1:55321` (로컬) ⚠️ **운영이어야 함** |

- **⚠️ 왜 지금 당장 위험하지는 않은가:** 어긋나는 방향이 **안전한 쪽**이다. `main`·`develop`에서 로컬을 보는 것은 데이터가 안 보이거나 접속 오류가 날 뿐이고, **운영 DB를 실수로 건드리는 반대 방향은 일어나지 않는다.** `use-env.sh`의 브랜치 규칙 자체도 "`main`·`develop`만 운영, 나머지 전부 로컬"이라 같은 방향으로 설계했다(모르는 브랜치 → 로컬).
- **브랜치 규칙 (2026-07-21 사용자 결정으로 갱신):** 처음엔 `main`만 운영으로 뒀으나 **`develop`도 운영**으로 바꿨다. `develop`은 Vercel 프리뷰로 배포되고 그 배포본은 어차피 운영 DB를 보므로, 로컬에서만 다른 DB를 보면 *"내 화면에선 되는데 배포하면 다르다"* 가 생긴다. **로컬 DB는 자동 개발 루프 전용(`test/*` 등)으로 좁혔다.**
- **해소 조건:** 이 두 파일이 `develop`·`main`에 도달하면 자동으로 해소된다. 즉 **별도 작업이 아니라 병합 시점의 문제**다.
- **✅ `develop` 해소 (2026-07-21, 병합 후 실측):** `test/bmad-loop` → `develop` 병합 후 실제로 브랜치를 오가며 재측정했다.

  | 이동 | `web/.env.local` | 판정 |
  |---|---|---|
  | `test/bmad-loop` → `develop` | `psrnsasx...supabase.co` | ✅ 훅이 돌아 운영으로 바뀜 |
  | `develop` → `test/bmad-loop` | `127.0.0.1:55321` | ✅ 로컬로 되돌아옴 |
  | `test/bmad-loop` → `main` (직행) | `127.0.0.1:55321` | ❌ **안 바뀜** — main에 훅 파일이 없다 |

- **⚠️ `main`은 아직 열려 있다.** `main` 병합은 사용자 명시 승인이 필요하다(CLAUDE.md B3 — 운영 반영). 승인 전까지 `main`에서는 직전 브랜치의 설정이 그대로 남는다. **방향은 여전히 안전한 쪽**이다(운영이어야 할 자리에 로컬이 남을 뿐, 그 반대는 없다).
- **📅 `main` 병합 시 위 표의 3행을 재측정한다.** 운영 주소로 바뀌면 이 항목을 닫는다.
- **대안(택하지 않음):** 훅을 `.git/hooks/`(브랜치 무관, 추적 안 됨)에 두면 지금 당장 모든 브랜치에서 돈다. 하지만 로직이 **추적본과 비추적본 두 벌**이 되어 조용히 어긋날 자리가 생긴다(#101이 정확히 그 종류의 사고였다). 병합 한 번으로 해결되는 문제에 드리프트 장치를 심지 않는다.

### DW-406: [구 #106] bmad-loop의 `verify` 게이트에 **E2E가 한 줄도 없다** — 넣을 스펙이 레포에 0개이기 때문

origin: 장부 통합 이관(구 docs/tech-debt.md #106) — 원출처: 2026-07-22 bmad-loop 도입 중 등재, 🟢 품질
location: `.bmad-loop/policy.toml` `[verify]` · `web/`(Playwright 부재) · `app/`(`integration_test/` 부재)
severity: medium
reason: 핵심 화면 흐름을 실행하는 E2E 스펙이 레포에 아예 없어서(Playwright 설정 0건, app integration_test 0건) 게이트에 넣을 대상 자체가 없었고, 별도 스토리로 스펙을 먼저 만든 뒤 게이트에 추가하기로 미뤘다.
trigger: 별도 스토리로 핵심 흐름 2~3개(로그인 · 매물등록 · 검색)를 Playwright로 작성 → 그때 `[verify] commands`에 추가한다.
status: open

- **위치:** `.bmad-loop/policy.toml` `[verify]` · `web/`(Playwright 부재) · `app/`(`integration_test/` 부재)
- **무엇:** 무인 개발 루프(bmad-loop)가 스토리마다 커밋 직전 돌리는 게이트를 5개로 채웠다 — `pytest` / `npm run lint` / `npm test` / `flutter analyze` / `flutter test`. **실측 36.4초, 전부 exit=0, 일부러 깨뜨려 exit=1로 막히는 것까지 확인.** 그런데 **화면이 실제로 동작하는지 보는 층이 통째로 없다.**
- **왜 없나(추측 아님, 실측):** `playwright.config.*` **0건**, `web/`에 Playwright 의존성 **없음**, `app/integration_test/` **없음**. `.github/workflows/tests.yml` 주석이 이미 인정하고 있다 — *"E2E — Playwright 스펙이 레포에 0개다. docs/e2e-*.md는 사람이 읽는 수동 대본이지 코드가 아니다."* (그 `docs/e2e-*.md`조차 지금은 존재하지 않는다.) *(✎ 2026-07-28: Story 11.5가 `web/e2e/` 스위트(스펙 3파일 + `playwright.config.ts`)를 실제로 만들어 **이 문장은 더 이상 사실이 아니다** — `#86` 해소분. 원문은 경위로 남긴다. 다만 CI 배선은 여전히 없다 → `#168`.)*
- **지침은 이미 있는데 재료가 없다:** `_bmad-output/project-context.md` §11(*"web=브라우저 E2E, api=HTTP/curl, app=실폰 mobile-mcp"*)이 `bmad-dev-auto`의 `persistent_facts`로 **매 실행 컨텍스트에 자동 로드된다.** 즉 루프는 "E2E를 하라"는 지시를 받고 있으나 **실행할 코드가 없다.** 막힌 곳은 지침이 아니라 재료다.
- **무엇을 못 보나:** 부품이 전부 통과해도 **연결이 끊긴 것**은 안 잡힌다 — 버튼이 안 눌림, API 주소 오류, 로그인 후 오이동. 단위 195건(api)+96건(web)+77건(app)이 전부 초록이어도 사용자는 아무것도 못 할 수 있다.
- **지금 이 층을 무엇이 대신하나:** 사람/에이전트가 세션마다 브라우저 MCP로 직접 조작(§B4). **무인 루프에는 그 사람이 없다.** `policy.toml`의 `[gates] mode = "per-epic"`이 에픽 경계에서 멈춰 사람을 부르므로, **현재 이 층의 유일한 보증 지점은 에픽 관문의 수동 확인**이다.
- **트리거:** 별도 스토리로 핵심 흐름 2~3개(로그인 · 매물등록 · 검색)를 Playwright로 작성 → 그때 `[verify] commands`에 추가한다.

### DW-407: [구 #107] 실기동 HTTP 스모크를 **의도적으로 넣지 않았다** — 지금은 지킬 대상이 비어 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #107) — 원출처: 2026-07-22 등재, ⚪ 의도적 보류
location: `api/app/main.py:23-33`(lifespan) · `.bmad-loop/policy.toml` `[verify]`
severity: low
reason: 기동 실패 중 lifespan 안의 오류만 스모크가 추가로 잡을 수 있는데, 지금 lifespan은 아무 작업도 하지 않는 빈 상태라(비밀값 없이도 `/health`가 떠야 하는 설계) 깨질 코드가 없는 자리를 지키는 검사가 되어 비용만 남기 때문에 넣지 않았다.
status: open

- **위치:** `api/app/main.py:23-33`(lifespan) · `.bmad-loop/policy.toml` `[verify]`
- **무엇을 검토했나:** uvicorn을 실제로 띄우고 `curl`로 두드리는 스모크(`/health` 200 · 본문 계약 · openapi에 `/ai/search` 존재 · 무토큰 401). 시제품을 만들어 **통과 4.1초 / 기동 깨뜨리면 exit=1 / 복구 후 exit=0**까지 확인했다.
- **왜 안 넣었나(실측으로 뒤집힌 판단):** 처음엔 *"기동 실패는 pytest가 못 본다"* 고 봤으나 **틀렸다.** 실제로 재보니 —

  | 일부러 낸 고장 | pytest | 실기동 스모크 |
  |---|---|---|
  | 모듈 레벨 오류(`main.py`에 `raise`) | **exit=2 잡음** | 잡음 |
  | lifespan 안의 오류 | **exit=0 통과** ← 놓침 | **exit=1 잡음** |

  pytest도 `from app.main import app`으로 앱을 불러오므로 import 단계 고장은 같이 터진다. **스모크가 유일하게 잡는 건 lifespan 고장 하나뿐이다.**
- **그런데 그 자리가 비어 있다:** 현재 lifespan은 기동 시 **아무것도 하지 않는다**(`yield`만; 종료 때 `close_pool()`). 비밀값 없이도 `/health`가 떠야 한다는 `config.py` 설계 때문에 일부러 비워둔 것이다. 즉 **깨질 코드가 없는 자리를 지키는 검사**가 되어, 매 스토리 4초와 스크립트 1개의 비용만 남는다(A2).
- **되살릴 신호(이것만 보면 된다):** **`api/app/main.py`의 lifespan에 기동 작업이 추가되는 순간** — DB 풀 사전 개방 · 캐시 예열 · 외부 서비스 연결 확인 등. 그때부터 pytest 사각지대가 실재하게 된다.
- **시제품 위치:** 세션 스크래치패드(`smoke-api.sh`). 영구 보관 아님 — 되살릴 때 재작성해도 20줄 수준이다.
- **함께 확인된 한계:** 무효 토큰 401 축은 이 스모크로 검증 **불가**다. 토큰이 실제로 오면 `api/app/auth.py:56`이 `SUPABASE_URL`을 요구해(`require()`) 비밀값 없는 환경에서는 500이 난다 — **앱 버그가 아니라 검사 범위 밖.** 이 축은 비밀값이 있는 환경(에픽 관문의 수동 curl)에서 확인한다.

### DW-408: [구 #108] 신뢰속성 3컬럼에 값을 넣는 경로가 없다(쓰기 UI 부재) — Story 10.1 Design Notes에서 식별

origin: 장부 통합 이관(구 docs/tech-debt.md #108) — 원출처: (표기 없음)
location: Epic 10 전 스토리 범위 — 판매자가 `accident_status`·`is_single_owner`·`is_non_smoker`를 입력하는 폼이 어디에도 없다(10.2=표시, 10.3/10.4=옵션, 10.5=찜, 10.6=판매자 정보 — 등록 폼을 손대는 스토리가 없다).
severity: medium
reason: Epic 10 요구사항 문서(epic-10-context.md)에 신뢰속성 입력 UI가 없고, 표시(10.2) 스토리가 쓰기 폼까지 만드는 것은 범위 확장이라 시드 데이터로만 값을 채우고 등록 폼 UI는 만들지 않기로 판정했다.
status: open

- **위치:** Epic 10 전 스토리 범위 — 판매자가 `accident_status`·`is_single_owner`·`is_non_smoker`를 입력하는 폼이 어디에도 없다(10.2=표시, 10.3/10.4=옵션, 10.5=찜, 10.6=판매자 정보 — 등록 폼을 손대는 스토리가 없다).
- **내용:** Story 10.1이 컬럼(`supabase/migrations/0017_listings_trust_attributes.sql`)과 값이 흐르는 경로(SELECT_COLUMNS·ALLOWED_COLUMNS·web/app select·프롬프트)를 전부 열었지만, 값을 **넣을** 사람이 없다. 기존 100건은 전부 NULL이고, 신규 등록도 이 3필드를 받지 않는다.
- **터지면:** 10.2가 신뢰 뱃지를 렌더해도 실제로 뱃지가 뜨는 매물이 0건이라 화면에서 검증할 게 없다(수동 시드 없이는 눈으로 못 본다). 10.7(통합 검증)도 같은 벽에 부딪힌다.
- **트리거: 10.2 착수 시** — 뱃지를 렌더할 실제 값이 있는지 먼저 확인할 것(수동 SQL 시드로 최소 1건 `accident_status`/`is_single_owner`/`is_non_smoker`를 채워야 뱃지 경로를 눈으로 검증할 수 있다). 등록 폼에 신뢰속성 입력 UI를 실제로 추가할지는 Epic 10 범위 밖 판단이 필요하다(현재 요구사항엔 없음, epic-10-context.md 확인).
- ✅ **판정 완료(Story 10.2, 2026-07-22) — (a)를 택함. 폼 UI는 만들지 않는다(닫지 않음, 쓰기 UI 부재는 그대로 열려 있다).**
  - **한 것:** `supabase/seed.sql`(운영/fresh DB 정본)에 대표 4건 — 무사고+1인소유+비흡연 2건(아반떼 CN7·K5 DL3)·사고 1건(스파크)·단순교환 1건(트레일블레이저) — 에 additive UPDATE로 값을 심었다(delete-재삽입 대상인 39/58건 INSERT 자체는 안 건드림). 로컬 전용 `supabase/seed-local/03_trust_demo.sql`(신규, 멱등 UPDATE)도 같은 4상태를 대표성 있게 심는다 — 두 파일 모두 두 번 실행해도 결과가 같음을 실측(로컬은 재실행 후 트리거 대상 행수 불변, seed.sql은 트랜잭션 내 실행 후 ROLLBACK으로 부작용 없이 결과만 확인).
  - **왜 (b, 등록 폼)를 안 했나:** epic-10-context.md 요구사항에 신뢰속성 입력 UI가 없고(대장 #108 스스로가 확인한 사실), 이 스토리(10.2=표시)가 쓰기 폼까지 만드는 건 스코프 확장이다(A2 단순함 우선). Epic 10 나머지 스토리(10.3~10.7)도 등록 폼을 손대지 않는다(epic-10-context.md Stories 목록 재확인).
  - **여전히 열려 있는 것:** 신규 등록 매물은 이 3필드를 입력받지 않으므로 계속 NULL로 들어간다 — 시드 매물에서만 뱃지가 보인다. 등록 폼 입력 UI가 필요해지면(운영 실사용 전환 등) 별도 스토리로 신설.
- **트리거(갱신):** 등록 폼에 신뢰속성 입력이 실제로 필요해지는 시점(운영 전환·요구사항 추가) — 그때 폼 UI 스토리를 신설할지 판단.

### DW-409: [구 #109] `/search`·`/listings/[id]`(web) — anon은 신뢰속성 3컬럼을 조회하지 못한다(GRANT 미승인) — Story 10.1 구현 중 실측 발견, Story 10.2가 범위 확장

origin: 장부 통합 이관(구 docs/tech-debt.md #109) — 원출처: (표기 없음)
location: `web/src/app/(user)/search/page.tsx` · `web/src/app/(user)/listings/[id]/page.tsx` · GRANT 정본은 `supabase/migrations/0011_listings_anon_select.sql` · 판정 규칙은 `docs/conventions.md` §9.3
severity: medium
reason: conventions.md §9.3이 anon 노출 컬럼을 넓히는 GRANT 변경은 델타가 0이어도 사용자 승인이 필수라고 못박는데, 이 스토리는 접근권한 정책을 넓히는 스토리가 아니라서 승인 없이 GRANT를 확장하지 않았다.
trigger: Story 10.2 착수 시(신뢰 뱃지를 실제로 그리는 시점) — anon에게도 뱃지를 보여줄지 제품 판단 필요. 보여주기로 하면 `0011` 이후 새 마이그레이션으로 `grant select (accident_status, is_single_owner, is_non_smoker) on public.listings to anon`을 추가하고, §9.3 (b) 절차대로 **사용자 승인**을 받는다.
status: open

- **위치:** `web/src/app/(user)/search/page.tsx` · `web/src/app/(user)/listings/[id]/page.tsx` · GRANT 정본은 `supabase/migrations/0011_listings_anon_select.sql` · 판정 규칙은 `docs/conventions.md` §9.3
- **내용:** `/search`는 anon(비로그인)도 여는 열람 경로(conventions.md §8)인데, anon은 `0011`이 컬럼 단위로 명시한 목록만 읽을 수 있다. `accident_status`·`is_single_owner`·`is_non_smoker`는 그 목록에 없다 — **실측(2026-07-22, PostgREST에 anon key로 직접 요청)**: `select=id,fuel` → 200 정상, `select=id,accident_status,is_single_owner` → `42501 permission denied for table listings`(컬럼 하나만 막히는 게 아니라 **요청 전체가 실패**한다). `fuel`은 이미 0011에 있어 문제없다.
- **왜 컬럼을 안 넓혔나:** `docs/conventions.md` §9.3은 anon 노출 컬럼을 "넓히는" GRANT 변경을 **델타 0이어도 (b) 사용자 승인 필수**로 못박는다(9.3 "새 컬럼 노출이면 무조건 (b)"). 이 스토리(10.1)는 "값이 흐르게 하는" 스토리이지 접근권한 정책을 넓히는 스토리가 아니라서, 승인 없이 GRANT를 확장하지 않았다.
- **지금 취한 조치(회피, 승인 아님):** `search/page.tsx`가 로그인 여부(`user`)로 select 문자열을 분기한다 — 로그인 사용자는 신뢰속성 3컬럼을 함께 조회하고, anon은 기존과 동일하게 `fuel`까지만 조회한다(회귀 없음, 신뢰속성은 애초에 #108 때문에 전부 NULL이라 지금 당장 잃는 정보는 없다).
- **터지면:** #108이 해소돼 실제 값이 생긴 뒤에도, **비로그인 방문자에게는 신뢰 뱃지(10.2)가 영영 안 보인다** — 로그인 전 탐색 단계에서 신뢰도를 보여준다는 Epic 10 취지와 어긋난다.
- **트리거:** Story 10.2 착수 시(신뢰 뱃지를 실제로 그리는 시점) — anon에게도 뱃지를 보여줄지 제품 판단 필요. 보여주기로 하면 `0011` 이후 새 마이그레이션으로 `grant select (accident_status, is_single_owner, is_non_smoker) on public.listings to anon`을 추가하고, §9.3 (b) 절차대로 **사용자 승인**을 받는다.
- ⚠️ **Story 10.2가 트리거에 도달했다(2026-07-22) — 여전히 open, 범위만 확장됐다.** 이 스토리의 스펙(`Block If`)이 명시적으로 GRANT 마이그레이션을 만들지 말라고 못박았다 — 이 무인 실행에 §9.3 (b)의 사용자 승인 창구가 없기 때문이다. 그래서 `search/page.tsx`가 이미 쓰던 로그인 분기 패턴을 `listings/[id]/page.tsx`(상세 select)에도 **그대로** 적용해 anon 회귀 없이 뱃지 렌더만 열었다 — 회피의 범위가 목록 1곳에서 목록+상세 2곳으로 늘었을 뿐, GRANT는 여전히 넓히지 않았다.
- **해소:** 위 트리거(제품이 "anon도 반드시 봐야 한다"로 확정하는 시점)에 승인받은 GRANT 마이그레이션 적용 + `search/page.tsx`·`listings/[id]/page.tsx` **두 곳** 모두의 `user` 분기 제거.

### DW-410: [구 #110] `rows_to_cards` 계약-외 강등이 4슬롯뿐 — 숫자·필수 str 7슬롯은 순서 어긋난 LLM SQL에 `/ai/search` 500

origin: 장부 통합 이관(구 docs/tech-debt.md #110) — 원출처: 2026-07-22 Story 10.1 후속 리뷰 등재, 🟡 조건부
location: `api/app/graph/listing_cards.py:83-101`(`rows_to_cards`) · 근본 원인은 `api/app/db/sql_guard.py`가 SELECT 프로젝션 **순서**를 `SELECT_COLUMNS`에 고정하지 않음(파일 상단 주석이 이미 인정)
severity: high
reason: 이 7슬롯은 10.1 이전 7컬럼 시절부터 있던 선재 결함이라 10.1이 새로 만든 문제가 아니고, 근본 해결(SELECT 프로젝션 순서 고정)은 보안 민감한 sql_guard를 신중히 다뤄야 해서 컬럼 추가 스토리 범위를 넘는다고 보고 미뤘다.
trigger: sql_guard에 SELECT 프로젝션 **순서 고정**을 도입할 때, 또는 `rows_to_cards`가 읽는 컬럼이 더 늘어날 때(예: 10.2에서 신뢰속성이 렌더되며 상세 select가 확장). 그때 4슬롯 `None` 강등 + 7슬롯 `SqlGuardError` 재시도로 **전체 슬롯을 일관되게** 방어할지 결정한다.
status: open

- **위치:** `api/app/graph/listing_cards.py:83-101`(`rows_to_cards`) · 근본 원인은 `api/app/db/sql_guard.py`가 SELECT 프로젝션 **순서**를 `SELECT_COLUMNS`에 고정하지 않음(파일 상단 주석이 이미 인정)
- **무엇:** P1/P2/FP1 패치가 `fuel`·신뢰속성 3필드(인덱스 7~10)만 계약-외 값을 `None`으로 강등한다. 그런데 숫자 슬롯 `int(r[3])`/`int(r[4])`/`int(r[5])`(year·price·mileage)과 필수 str 슬롯 `r[1]`(manufacturer)·`r[2]`(model)·`r[6]`(region)은 방어가 없다. sql_guard는 컬럼 화이트리스트만 보고 순서를 고정하지 않으므로, **폭은 11로 맞지만 순서를 바꾼** LLM SQL이 숫자 슬롯에 문자열을(→ `int()` `ValueError`) 또는 str 슬롯에 int를(→ pydantic `ValidationError`) 넣을 수 있다. 이건 `SqlGuardError`가 아니라서 `sql_rag_node`의 `except SqlGuardError` 재생성 루프를 빠져나가 `/ai/search` 500이 된다 — P1/FP1이 4슬롯에 대해 닫은 바로 그 실패 모드가 나머지 7슬롯에 남아 있다.
- **실측:** 리뷰어 4개 레인 중 2개(적대·엣지케이스)가 독립 수렴, 엣지케이스가 pydantic v2로 `int()`/`str` 필드 거부를 실증. 코드 확인: 89~92행 `int(r[3..5])`·`r[1]`/`r[2]`/`r[6]`에 try/except나 타입 가드 없음.
- **왜 이 스토리가 만든 게 아닌가(→ defer):** 이 7슬롯(id/manufacturer/model/year/price/mileage/region)은 10.1 이전 **7컬럼 시절부터** 있었고 당시에도 reorder된 7컬럼 SQL이 같은 500을 냈다. 10.1은 **새로 추가한** 4 nullable 슬롯에만 방어를 넣었을 뿐 기존 7슬롯의 선재(先在) 결함을 만들지 않았다. 리뷰가 부수적으로 표면화. 근본 해결은 sql_guard가 SELECT 프로젝션 순서를 `SELECT_COLUMNS`에 고정하는 것이며(슬롯별 try/except는 밴드에이드), sql_guard는 보안 민감(B9)이라 신중히 다뤄야 한다 — "컬럼 추가" 스토리의 범위를 넘는다.
- **왜 지금 무해:** 프롬프트 규칙 1이 LLM에 `SELECT_COLUMNS` 순서 보존을 지시하고 sql_guard가 컬럼을 화이트리스트로 막으므로, "폭 11 + 순서 뒤바뀜 + 타입 충돌 조합"이 동시에 성립할 확률이 낮다. 조건이 성립하면 500.
- **트리거:** sql_guard에 SELECT 프로젝션 **순서 고정**을 도입할 때, 또는 `rows_to_cards`가 읽는 컬럼이 더 늘어날 때(예: 10.2에서 신뢰속성이 렌더되며 상세 select가 확장). 그때 4슬롯 `None` 강등 + 7슬롯 `SqlGuardError` 재시도로 **전체 슬롯을 일관되게** 방어할지 결정한다.

### DW-411: [구 #111] 클라이언트 `.select(...)` 락스텝을 지키는 자동 검사가 없다 — #67 형태의 조용한 재발 가능

origin: 장부 통합 이관(구 docs/tech-debt.md #111) — 원출처: 2026-07-22 Story 10.1 후속 리뷰 등재, Story 10.2가 범위 확장, 🟢 품질
location: `web/src/app/page.tsx`(홈 프리뷰) · `web/src/app/(user)/search/page.tsx`(검색) · `web/src/app/(user)/listings/[id]/page.tsx`(상세, 10.2 신규) · `app/lib/features/listings/listings_repository.dart`(`fetchListings`) — 네 곳의 인라인 `.select(...)` 문자열. 락스텝 정본은 `docs/conventions.md` §4.1
severity: medium
reason: select에서 컬럼이 빠져도 잡아내는 자동 검사를 만들기엔 서버 컴포넌트의 인라인 select 문자열이라 문자열 포함 단언이 취약하고, 화면 렌더 검증은 프로젝트 규칙상 E2E 전용이라 이 스토리에서 즉시 만들지 않고 등재만 했다.
trigger: 세 번째 소비처(예: Epic 16.2 app 상세)가 같은 컬럼을 또 손으로 select할 때, 또는 네 곳 중 하나에서 컬럼 누락 회귀가 실제로 발생할 때. 그때 (a) select 문자열이 §4.1 락스텝 컬럼을 포함하는지 검증하는 경량 테스트를 추가할지, (b) select를 공유 상수/헬퍼로 추출해 한 곳에서 관리할지(로그인 분기 자체도 포함) 판단한다.
status: open

- **위치:** `web/src/app/page.tsx`(홈 프리뷰) · `web/src/app/(user)/search/page.tsx`(검색) · `web/src/app/(user)/listings/[id]/page.tsx`(상세, 10.2 신규) · `app/lib/features/listings/listings_repository.dart`(`fetchListings`) — 네 곳의 인라인 `.select(...)` 문자열. 락스텝 정본은 `docs/conventions.md` §4.1
- **무엇:** 카드·상세에 값이 흐르려면 이 네 select 문자열이 `fuel`·신뢰속성 컬럼을 포함해야 하는데, 이를 강제하는 자동 검사가 하나도 없다 — §4.1 **산문만이** 락스텝 지점을 문서화한다. api 쪽 `ALLOWED_COLUMNS`는 정확-집합 테스트(`test_sql_guard.py`의 `test_allowed_columns_is_exactly_*`)로 못박혔지만, 클라이언트 select 문자열은 대응하는 가드가 없다.
- **실측:** 리뷰어 2개 레인(검증갭·의도정합)이 지적. `grep -rln 'search/page|components/listings' web/src --include=*.test.*` → 0건(어떤 web 테스트도 이 파일을 import하지 않음). Dart도 모델(`listing_model_test.dart`)만 테스트하고 `listings_repository.dart` select는 검사하지 않는다.
- **왜 defer:** 대장 #67(카드 meta 연료 누락)이 바로 이 형태의 결함이었다 — select에서 컬럼이 빠져도 아무 테스트가 안 깨진다. 10.1이 #67을 닫았지만 **재발을 막는 가드는 만들지 않았다.** B9("규칙은 어길 수 없는 자리에 박는다 — 주석·문서는 계약이 아니다")에 어긋난다. 서버 컴포넌트의 인라인 select 문자열이라 자동 검사가 다소 까다롭고(문자열 포함 단언은 취약), 화면 렌더 검증은 프로젝트 규칙상 E2E-only(#106) — 그래서 이 스토리에서 즉시 패치하지 않고 등재한다.
- **터지면:** 네 곳 중 하나에서 컬럼이 조용히 빠지면 카드 meta가 `주행 · 지역`으로 회귀(#67 재발)하거나 신뢰 섹션이 로그인 상태에서도 안 뜨되 CI는 초록. 누군가 실제로 눈으로 볼 때까지 안 잡힌다.
- ⚠️ **Story 10.2가 트리거에 도달했다(2026-07-22) — 가드는 여전히 안 만들고 defer를 이어간다, 대신 위험 범위가 넓어진 사실을 갱신한다.** 10.2는 `search/page.tsx`가 쓰던 "로그인 여부로 select 분기" 패턴을 `listings/[id]/page.tsx`(상세)에도 그대로 반복 구현했다 — anon 분기 로직이 이제 **2곳에 각각 손으로** 쓰여 있고(공유 헬퍼 없음), 그중 하나가 조용히 어긋나면(예: 상세 select에서 `trustColumns` 삽입을 빠뜨림) 로그인 사용자인데도 신뢰 섹션이 안 뜨는 회귀가 CI 초록인 채로 발생할 수 있다. 이 스토리는 그 가드를 새로 만들지 않았다(위 "왜 defer" 사유가 그대로 적용 — 스코프 확장 없이 표시만 다시 확인).
- **트리거:** 세 번째 소비처(예: Epic 16.2 app 상세)가 같은 컬럼을 또 손으로 select할 때, 또는 네 곳 중 하나에서 컬럼 누락 회귀가 실제로 발생할 때. 그때 (a) select 문자열이 §4.1 락스텝 컬럼을 포함하는지 검증하는 경량 테스트를 추가할지, (b) select를 공유 상수/헬퍼로 추출해 한 곳에서 관리할지(로그인 분기 자체도 포함) 판단한다.

### DW-412: [구 #112] 상세에 사고 정보가 두 컬럼으로 따로 뜬다 — `accident_status`(뱃지)와 `accident_free`('사고이력' 행)가 교차검증 없이 나란히 렌더

origin: 장부 통합 이관(구 docs/tech-debt.md #112) — 원출처: 2026-07-22 Story 10.2 코드리뷰 등재, 🟡 조건부
location: `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` — `TrustInfoSection`(신뢰정보 = `accident_status` 뱃지)과 `VehicleInfoSection`의 '사고이력' Field(`accident_free` bool). 두 컬럼은 마이그 `0017_listings_trust_attributes.sql`이 **의도적으로 분리**한 것이다(10.1: `accident_free`는 드롭 금지·additive, DB에 교차 제약 없음).
severity: high
reason: 두 컬럼(`accident_free`/`accident_status`) 분리는 10.1의 의도적 결정이고, 어긋난 데이터를 만들 쓰기 경로(#108)가 아직 없어 실제 모순이 발생할 수 없기 때문에 지금 두 표시를 합치지 않았다.
trigger: #108(쓰기 경로)이 해소되는 시점, 또는 Epic 10.7(신뢰속성·옵션 통합 검증)에서 두 사고 표시를 조정할 때. 그때 (a) 한쪽을 다른 쪽에서 파생시키거나(단일 출처), (b) `accident_status`가 있으면 '사고이력' 행을 숨기거나, (c) 렌더 시 두 값 정합성 단언을 넣을지 판단한다.
status: open

- **위치:** `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` — `TrustInfoSection`(신뢰정보 = `accident_status` 뱃지)과 `VehicleInfoSection`의 '사고이력' Field(`accident_free` bool). 두 컬럼은 마이그 `0017_listings_trust_attributes.sql`이 **의도적으로 분리**한 것이다(10.1: `accident_free`는 드롭 금지·additive, DB에 교차 제약 없음).
- **무엇:** 10.2가 상세에 `accident_status` 뱃지를 그리면서, 같은 화면에 사고 정보가 **두 곳**(신뢰정보 뱃지 + 차량정보 '사고이력' 행)에서 나온다. 두 값이 어긋나면(예: `accident_free=false`인데 `accident_status='무사고'`) **초록 '무사고' 뱃지 바로 아래 '사고이력 있음' 행**이 떠, CM-C("신뢰속성을 검증됨으로 오도하지 않는다")를 정면으로 위반하는 자기모순 화면이 된다.
- **실측:** 리뷰어(적대) 지적. **현재는 발생하지 않는다** — 시드(`seed.sql`·`seed-local/03_trust_demo.sql`)가 `accident_free`↔`accident_status`를 일관되게 심고(무사고↔`accident_free=true`, 사고/단순교환↔`accident_free=false`), 신뢰속성을 넣는 쓰기 경로가 아직 없다(#108). 그래서 데이터가 어긋날 자리가 지금은 없다.
- **왜 지금 defer:** 두 컬럼 분리는 10.1의 의도적 결정이고(0017), 10.2 스펙도 '사고이력' 행을 그대로 두라고 명시했다(별개 필드). 어긋난 데이터를 만들 쓰기 경로가 없어 실제 모순은 발생 불가능하다. 지금 두 표시를 합치는 건 스코프 밖(A2 단순함 우선).
- **터지면:** 신뢰속성 쓰기 UI(#108)가 생겨 사용자가 `accident_free`와 `accident_status`를 따로 입력·수정할 수 있게 되면, 둘이 어긋난 매물이 상세에서 자기모순 화면(초록 무사고 뱃지 + 사고이력 있음)을 낸다.
- **트리거:** #108(쓰기 경로)이 해소되는 시점, 또는 Epic 10.7(신뢰속성·옵션 통합 검증)에서 두 사고 표시를 조정할 때. 그때 (a) 한쪽을 다른 쪽에서 파생시키거나(단일 출처), (b) `accident_status`가 있으면 '사고이력' 행을 숨기거나, (c) 렌더 시 두 값 정합성 단언을 넣을지 판단한다.
- **10.7 검토(2026-07-22):** 통합검증(검증 전용 스코프)에서 재검토했고 **두 표시를 조정하지 않았다.** 근거: 합치기·정합성 단언 도입은 A2(단순함) 범위 밖이고, 어긋난 데이터를 만들 쓰기 경로(#108)가 아직 없어 실제 모순이 발생 불가능하다. 항목은 **열린 채로 유지**하며 주 트리거는 #108로 둔다.

### DW-413: [구 #113] app `listing_form.dart`가 여전히 옵션을 쉼표로 join/split한다 — #11의 app 미러가 안 됨

origin: 장부 통합 이관(구 docs/tech-debt.md #113) — 원출처: 2026-07-22 Story 10.3에서 식별, 대장은 하나·미룬 것도 적는다 B8
location: `app/lib/features/listings/listing_form.dart:89`(`(d.options ?? const <String>[]).join(', ')`)·`:230`(`.split(',')`).
severity: medium
reason: 이 스토리(10.3)의 Boundaries가 app 폼 수정을 명시적으로 금지하고 있고, Epic 16이 통제어휘·상수·폼 미러를 한 번에 맡을 자리라 지금 손대면 web/app 락스텝이 오히려 깨진다고 판단해 미뤘다.
trigger: Epic 16 착수 시 — `web/src/lib/options.ts`(통제어휘·`topOptions`·`groupByCategory`·`parseOptionsInput`/`serializeOptions`)를 app `lib/features/listings/options.dart`(가칭)로 미러링하는 스토리에서, `listing_form.dart`의 옵션 입력을 줄바꿈 구분(`parseOptionsInput` 동일 로직)으로 함께 바꾼다.
status: open

- **위치:** `app/lib/features/listings/listing_form.dart:89`(`(d.options ?? const <String>[]).join(', ')`)·`:230`(`.split(',')`).
- **내용:** Story 10.3이 web `SellForm.tsx`의 옵션 저장을 쉼표 join/split에서 줄바꿈 구분(`web/src/lib/options.ts`)으로 바꿔 #11(옵션 값에 쉼표가 있으면 수정 저장 시 쪼개지는 문제)을 **web만** 닫았다. app은 이 스토리 범위 밖(Boundaries "app(Flutter) 폼 #11 미러 수정 금지 → Epic 16")이라 그대로 뒀고, 지금도 web과 동일한 결함을 그대로 가진다.
- **왜 지금 안 고치나:** 이 스토리(10.3)의 Boundaries가 app 폼 수정을 명시적으로 금지한다 — Epic 16(Flutter 앱 증분 반영)이 통제어휘·상수·폼 미러를 한 번에 맡는 자리이고, 10.3에서 손대면 web/app이 서로 다른 시점에 부분적으로만 고쳐져 락스텝이 깨진다(§11 "이원화 금지"와 같은 이유로 미러링 시점도 갈라놓지 않는다).
- **터지면:** app 등록/수정 폼에서 쉼표가 든 옵션 값(예: 시드·API로 들어온 값)을 수정 저장하면 web과 동일하게 두 개로 쪼개진다.
- **트리거:** Epic 16 착수 시 — `web/src/lib/options.ts`(통제어휘·`topOptions`·`groupByCategory`·`parseOptionsInput`/`serializeOptions`)를 app `lib/features/listings/options.dart`(가칭)로 미러링하는 스토리에서, `listing_form.dart`의 옵션 입력을 줄바꿈 구분(`parseOptionsInput` 동일 로직)으로 함께 바꾼다.
- **해소:** app 통제어휘 상수·순수 헬퍼 이식 + `listing_form.dart` 구분자를 줄바꿈으로 변경 + 라운드트립 회귀 테스트(`listing_form_edit_test.dart`에 web `options.test.ts`의 #11 케이스와 동일한 재현 테스트 추가) — web이 10.3에서 한 것과 같은 패턴.

### DW-419: [구 #119] `get_seller_public_summary` RPC가 anon에게 **임의 uuid의 가입월**을 노출한다

origin: 장부 통합 이관(구 docs/tech-debt.md #119) — 원출처: 2026-07-22 Story 10.6 코드리뷰 defer, 🟡 조건부
location: `supabase/migrations/0019_seller_public_summary.sql`(SECURITY DEFINER, `grant execute … to anon, authenticated`).
severity: high
reason: 스코프를 좁히려면 서브쿼리·조건이 붙어야 해서 A2(단순화 우선) 원칙과 상충하고, 데모 범위에서는 현행 방식이 정합적이라고 판단해 미뤘다.
trigger: 운영 전환 또는 개인정보 노출 재검토 시(0007 `seller_name`과 함께 본다). 그때 (a) `created_at`을 판매중 매물 ≥1인 판매자에만 반환하거나, (b) 월 단위로 절삭해 반환하거나, (c) 함수를 `authenticated` 전용으로 좁힌다.
status: open

- **위치:** `supabase/migrations/0019_seller_public_summary.sql`(SECURITY DEFINER, `grant execute … to anon, authenticated`).
- **내용:** 함수가 `p_seller_id`로 받은 uuid의 `profiles.created_at`을 정의자 권한으로 읽어 돌려준다 — 대상이 실제 판매자인지, 호출자가 그 매물과 관계있는지 검사하지 않는다. anon도 실행 가능하므로 uuid만 알면 그 사용자(구매자·관리자 포함)의 가입월을 알 수 있다.
- **왜 지금 실해가 작나:** (a) 가입월 노출은 FR56이 상세에 **공개 표시를 요구**하는 값이고, (b) 판매자 uuid는 공개 매물(`listings.seller_id`)에서만 실질적으로 얻을 수 있어 비판매자 uuid는 어디에도 안 뜬다(추측 난이도=uuid). 0007이 `seller_name`을 공개 노출하며 남긴 "데모 한정·운영 전 개인정보 재검토"와 같은 성격이고, 이 스토리 스펙 Design Notes도 그 판단을 명시했다.
- **왜 이월:** 스코프를 좁히려면(판매자 전용/매물 소유 확인) 서브쿼리·조건이 붙어 A2(단순화)와 상충한다. 데모 범위에선 현행이 정합적.
- **트리거:** 운영 전환 또는 개인정보 노출 재검토 시(0007 `seller_name`과 함께 본다). 그때 (a) `created_at`을 판매중 매물 ≥1인 판매자에만 반환하거나, (b) 월 단위로 절삭해 반환하거나, (c) 함수를 `authenticated` 전용으로 좁힌다.
- **해소:** 미해소(위 트리거에서 판단).

### DW-420: [구 #120] `authenticated` 롤의 테이블 기본 GRANT를 심는 마이그레이션이 없다 — 로컬 `db reset` 시 로그인 경로가 깨진다

origin: 장부 통합 이관(구 docs/tech-debt.md #120) — 원출처: 2026-07-22 Story 10.6 코드리뷰 defer, 🟡 조건부
location: `supabase/migrations/**`(authenticated 롤에 `listings`·`profiles`·`chat_rooms` 등 기본 GRANT를 주는 파일이 없음). anon은 `0011`이 컬럼 화이트리스트로 명시하지만 authenticated는 어디에도 없다.
severity: high
reason: 근본 해소는 authenticated 기본 GRANT를 마이그레이션으로 명시하는 일인데, 운영 실권한과의 정합을 먼저 실측하고 §9.3(b) 사용자 승인도 받아야 해서 단일 스토리 범위를 넘어 미뤘다.
trigger: (a) 로컬에서 authenticated 경로를 재현·자동검증해야 할 때, 또는 (b) 신규 환경 부트스트랩/셀프-컨테인(§9.1)이 요구될 때, 또는 (c) Supabase 플랫폼 기본 권한이 바뀌어 운영이 실제로 깨질 때. 그때 **운영 실권한을 먼저 실측**해 동일 GRANT를 마이그레이션으로 박는다.
status: open

- **위치:** `supabase/migrations/**`(authenticated 롤에 `listings`·`profiles`·`chat_rooms` 등 기본 GRANT를 주는 파일이 없음). anon은 `0011`이 컬럼 화이트리스트로 명시하지만 authenticated는 어디에도 없다.
- **내용:** 로컬 Supabase Docker 스택에서 `supabase db reset`을 돌리면 authenticated 롤이 public 테이블 기본 권한 없이 비어, 로그인 사용자 경로(문의·찜·본인 매물 등)가 `42501`로 깨진다. Story 10.6 브라우저 검증 중 실측됨 — 검증을 위해 세션 전용으로 `grant`를 직접 실행(커밋 안 함).
- **왜 지금 실해가 작나:** 이 스토리가 만든 문제가 아니다 — 어떤 마이그레이션도 authenticated 전체 GRANT를 준 적이 없고, 앱은 운영 Supabase의 **플랫폼 기본 권한에 암묵 의존**해 Epic 1~9가 정상 배포·동작해 왔다. 운영엔 영향 없음(⚠️ 단 이는 **미검증 가정** — 아래 트리거 참조).
- **왜 이월:** 근본 해소는 authenticated 기본 GRANT를 `0011`이 anon에 한 것처럼 마이그레이션으로 명시하는 일인데, 운영 실권한과의 정합 실측·§9.3(b) 승인이 필요해 단일 스토리 범위 밖이다.
- **트리거:** (a) 로컬에서 authenticated 경로를 재현·자동검증해야 할 때, 또는 (b) 신규 환경 부트스트랩/셀프-컨테인(§9.1)이 요구될 때, 또는 (c) Supabase 플랫폼 기본 권한이 바뀌어 운영이 실제로 깨질 때. 그때 **운영 실권한을 먼저 실측**해 동일 GRANT를 마이그레이션으로 박는다.
- **해소:** 미해소(위 트리거에서 처리).

### DW-421: [구 #121] 상세 페이지 섹션 조립(순서·존재)이 자동 테스트로 안 잡힌다 — page.tsx가 async 서버컴포넌트

origin: 장부 통합 이관(구 docs/tech-debt.md #121) — 원출처: 2026-07-22 Story 10.7 코드리뷰 defer, 🟡 조건부
location: `web/src/app/(user)/listings/[id]/page.tsx:241-253`(신뢰정보→차량→옵션→판매자 4섹션을 JSX 형제로 배선하는 지점) vs `web/src/app/(user)/listings/[id]/__tests__/detailSectionsAssembly.test.ts`(신규).
severity: high
reason: 화면 렌더 검증은 프로젝트 규칙상 E2E 전용인데 이 스토리는 그 E2E 인프라를 세우는 범위가 아니라서, 섹션 조립을 잡는 자동 검사를 이 스토리에서 만들지 않았다.
trigger: ~~E2E(Playwright) 스펙을 레포에 처음 넣을 때(#106 해소 시) — 상세 페이지 섹션 순서/존재를 그 첫 E2E 대상에 포함한다.~~ 또는 상세 페이지 섹션 구성을 다시 손대는 스토리가 나올 때 그 자리에서 렌더 순서 가드를 함께 심는다.
status: open

- **위치:** `web/src/app/(user)/listings/[id]/page.tsx:241-253`(신뢰정보→차량→옵션→판매자 4섹션을 JSX 형제로 배선하는 지점) vs `web/src/app/(user)/listings/[id]/__tests__/detailSectionsAssembly.test.ts`(신규).
- **내용:** SM-C 주장("신뢰정보→차량→옵션→판매자 순서로 별개 섹션")은 `page.tsx`가 네 섹션을 이 순서로 배선하는지에 달려 있는데, `page.tsx`는 `async` 서버컴포넌트라 이 스토리가 카드에 쓴 "동기 함수호출 트리" 테스트 기법이 원천적으로 안 통한다(테스트 파일 스스로 ⚠️ 주석으로 인정). 신규 테스트는 `TrustInfoSection`·`OptionsSection`을 **각각 독립 호출**해 내부 조립만 본다. 결과: 누가 `page.tsx`에서 `<OptionsSection>` 줄을 지우거나 순서를 바꿔도 lint·tsc·vitest·build 전부 green. 코드리뷰 2개 레인(엣지케이스·검증갭)이 독립 수렴.
- **왜 이 스토리가 안 고쳤나:** 화면 렌더 검증은 프로젝트 규칙상 E2E-only(대장 #106)이고, 이 스토리는 그 E2E 인프라를 세우는 범위가 아니다. #106의 구체적 한 사례라 별도로 등재한다.
- **트리거:** ~~E2E(Playwright) 스펙을 레포에 처음 넣을 때(#106 해소 시) — 상세 페이지 섹션 순서/존재를 그 첫 E2E 대상에 포함한다.~~ 또는 상세 페이지 섹션 구성을 다시 손대는 스토리가 나올 때 그 자리에서 렌더 순서 가드를 함께 심는다.
- **✎ 2026-07-28 (Epic 11 회고) 트리거 재지정 — 첫 트리거는 소진됐는데 조치는 안 됐다.** Story 11.5가 레포 최초의 Playwright 스위트(`web/e2e/*.spec.ts` 3파일)를 실제로 만들었으므로 *"E2E를 처음 넣을 때"* 는 **이미 발동했다.** 그런데 상세 페이지 섹션 조립 검사는 `web/e2e/**` 어디에도 들어가지 않았다 — 11-5의 감사 대상 4화면(랜딩·`/search`·상세·`/ai`)에 상세가 있는데도 그 스펙은 가로스크롤·문의 CTA만 본다. **이건 회고가 짚은 반복 패턴 C("심겠다고 적은 자리에 안 심긴다", `#152`와 같은 형태)의 사례다.** 트리거가 알림일 뿐 강제가 아니라서 조용히 지나갔다.
- **트리거(재지정):** **`#168`의 E2E CI 배선 스토리** — 그 스토리가 `web/e2e/**`를 손대는 다음 확정 자리다. 그 자리에서 `viewport-audit.spec.ts`의 상세 케이스에 **4섹션(신뢰정보→차량→옵션→판매자) 렌더 순서·존재 단언**을 추가하고, `page.tsx`에서 `<OptionsSection>` 줄을 지워 red 확인 후 원복해 green 확인한다(B4). **또는** 상세 페이지 섹션 구성을 다시 손대는 스토리가 먼저 오면 그쪽이 앞선다.
- **해소:** 미해소(위 재지정 트리거에서 처리).

### DW-422: [구 #122] 시드 불변식 게이트(seed-local/*.sql)가 CI에서 실행되지 않는다 — 회귀를 사람 수동으로만 잡는다

origin: 장부 통합 이관(구 docs/tech-debt.md #122) — 원출처: 2026-07-22 Story 10.7 코드리뷰 defer, 🟢 품질
location: `supabase/seed-local/03_trust_demo.sql:74-100`(신규 `do $$ … raise exception` 사후 게이트). CI(`.github/workflows/*.yml`)·`check_migrations.py`(migrations/만 스캔) 어디에도 seed-local 실행이 없음(실측).
severity: medium
reason: seed-local은 로컬 데모 데이터 전용이고 원래부터 CI 검증 대상이 아닌 구조라, 이 스토리가 만든 결함이 아니라고 보고 CI 배선을 미뤘다.
trigger: seed-local을 CI에서 돌리기로 하거나(예: 데모 환경 자동 프로비저닝), seed 게이트가 지키는 불변식이 실제 기능 회귀로 이어질 수 있게 될 때. 그때 `scripts/seed-local.sh` 2회 실행 + 게이트 확인을 CI 잡으로 추가한다.
status: open

- **위치:** `supabase/seed-local/03_trust_demo.sql:74-100`(신규 `do $$ … raise exception` 사후 게이트). CI(`.github/workflows/*.yml`)·`check_migrations.py`(migrations/만 스캔) 어디에도 seed-local 실행이 없음(실측).
- **내용:** 10.7이 "희소 옵션이 실제로 시드에 들어갔는지" 검증하는 게이트를 심었지만, seed-local 스크립트 자체가 CI 자동화에 없어서 **사람이 로컬에서 두 번 돌려야만** 작동을 확인할 수 있다. 앞으로 이 SQL의 존재검사·append 술어를 깨도 어떤 자동 검사도 잡지 못한다. B4의 "존재≠작동"이 반대 방향으로 성립 — 게이트는 존재하나 정상 검증 경로(CI)에서 안 돈다. 게이트 로직 자체는 정상(적대 리뷰어가 로컬 DB 재실행·롤백 트랜잭션으로 확인, predicate-drift에만 발동).
- **왜 지금 무해:** seed-local은 로컬 데모 데이터 전용이고 운영/CI 대상이 아니다(설계상 migrations만 CI 검증). 이 스토리가 만든 결함이 아니라 seed-local이 원래 CI 밖이라는 기존 구조.
- **트리거:** seed-local을 CI에서 돌리기로 하거나(예: 데모 환경 자동 프로비저닝), seed 게이트가 지키는 불변식이 실제 기능 회귀로 이어질 수 있게 될 때. 그때 `scripts/seed-local.sh` 2회 실행 + 게이트 확인을 CI 잡으로 추가한다.
- **해소:** 미해소(위 트리거에서 처리).

### DW-424: [구 #124] self-host 폰트의 fallback metric 보정이 한글엔 안 걸린다 — `src: local(Arial)`이라 Android/Linux에선 아예 무효

origin: 장부 통합 이관(구 docs/tech-debt.md #124) — 원출처: 2026-07-27 Story 11-0 후속리뷰 defer, 🟡 조건부
location: `web/src/app/layout.tsx`의 `localFont()` 호출이 생성한 fallback 페이스 — 빌드 산출물 `web/.next/static/chunks/*.css`에서 실측.
severity: high
reason: next/font/local의 adjustFontFallback 옵션이 Arial/Times New Roman만 지원하고 한글 지표 옵션이 없는 프레임워크 자체의 한계이며, 한글 기준 수치를 실측으로 도출하는 일은 이번 스토리('로딩 방식 전환')의 범위를 넘어서 미뤘다.
trigger: Story 11.3(히어로) 작업 시 — 첫인상 화면에서 한글 스왑 리플로우가 실제로 눈에 띄는지 먼저 관측하고, 띄면 `declarations`로 한글 지표를 직접 주입한다. 또는 폰트 로딩 방식을 다시 손대는 스토리가 생길 때 그 자리에서 함께 처리.
status: open

- **위치:** `web/src/app/layout.tsx`의 `localFont()` 호출이 생성한 fallback 페이스 — 빌드 산출물 `web/.next/static/chunks/*.css`에서 실측.
- **내용:** next/font가 만든 보정 페이스가 `@font-face{font-family:pretendard Fallback;src:local(Arial);ascent-override:93.76%;descent-override:23.75%;size-adjust:101.55%}`다. **Arial엔 한글 글리프가 없어** `lang="ko"` 본문에는 이 override가 원천적으로 발동하지 않고, 한글은 보정 없는 `system-ui`/`Malgun Gothic`으로 떨어진다. 더구나 Arial이 설치돼 있지 않은 환경(Linux·Android)에선 `local(Arial)` 자체가 resolve 실패라 **라틴에도** 보정이 0이다(리뷰어가 `fc-list`로 Arial 0건인 박스에서 한글·라틴 폭이 보정 유무와 무관하게 동일함을 실측).
- **왜 이 스토리가 안 고쳤나:** 프레임워크 한계다 — `next/font/local`의 `adjustFontFallback`은 `'Arial' | 'Times New Roman' | false`만 받고 한글 지표 옵션이 없다(Next 16 문서 `font.md` 확인). 우회하려면 `declarations`로 한글 기준 `size-adjust`/`ascent-override`를 직접 계산해 넣어야 하는데, 그 수치를 실측으로 도출하는 것은 11-0의 "로딩 방식 전환" 범위 밖이다. 코드 주석(`layout.tsx`)에는 라틴 한정임이 이미 명시돼 있다.
- **트리거:** Story 11.3(히어로) 작업 시 — 첫인상 화면에서 한글 스왑 리플로우가 실제로 눈에 띄는지 먼저 관측하고, 띄면 `declarations`로 한글 지표를 직접 주입한다. 또는 폰트 로딩 방식을 다시 손대는 스토리가 생길 때 그 자리에서 함께 처리.
- **해소:** 미해소(위 트리거에서 처리).

### DW-425: [구 #125] `<Logo>`가 레포 어디에서도 렌더되지 않는다 — 800 weight 회귀 카나리아가 배선 없이 존재만 한다

origin: 장부 통합 이관(구 docs/tech-debt.md #125) — 원출처: 2026-07-27 Story 11-0 후속리뷰 defer, 🟢 품질
location: `web/src/components/ui/Logo.tsx` — 정의만 있고 import 0건(`grep -rn "ui/Logo\|<Logo" web/src` 실측: 히트는 정의 파일 자신뿐, `AppHeader.tsx`의 히트는 무관한 `<LogoutButton />`).
severity: medium
reason: 11-0의 Never가 `Logo.tsx` 수정을 금지했고, 배선(어느 화면에 어떤 크기로 넣을지)은 폰트 로딩이 아니라 UI 구성 결정이다.
trigger: Epic 11의 헤더·브랜딩을 손대는 스토리(11.3 히어로 또는 내비 재구성) — 그때 `<Logo>`를 실제 배선하거나, 안 쓸 거면 컴포넌트를 정리한다. 어느 쪽이든 그 시점에 800 weight 렌더를 실경로로 한 번 확인한다.
status: open

- **위치:** `web/src/components/ui/Logo.tsx` — 정의만 있고 import 0건(`grep -rn "ui/Logo\|<Logo" web/src` 실측: 히트는 정의 파일 자신뿐, `AppHeader.tsx`의 히트는 무관한 `<LogoutButton />`).
- **내용:** Story 8.1이 만든 브랜드 로고 컴포넌트가 **어느 화면에도 배선돼 있지 않다.** 실제 굵은-weight 렌더 경로는 `web/src/components/layout/AppHeader.tsx`의 `font-semibold` 링크뿐이다. 11-0이 폰트 전환의 회귀 카나리아로 `<Logo>`("차" 800 weight)를 지정했으나, 렌더되지 않는 컴포넌트라 확인은 동일 마크업을 DOM에 주입하는 방식으로 대체됐다 — 클래스가 폰트를 잘 받는다는 것은 확인되지만, **컴포넌트를 관찰한 것은 아니다.** B4의 "'존재 확인'은 '작동 확인'이 아니다"에 정확히 걸린다.
- **왜 이 스토리가 안 고쳤나:** 11-0의 Never가 `Logo.tsx` 수정을 금지했고, 배선(어느 화면에 어떤 크기로 넣을지)은 폰트 로딩이 아니라 UI 구성 결정이다.
- **트리거:** Epic 11의 헤더·브랜딩을 손대는 스토리(11.3 히어로 또는 내비 재구성) — 그때 `<Logo>`를 실제 배선하거나, 안 쓸 거면 컴포넌트를 정리한다. 어느 쪽이든 그 시점에 800 weight 렌더를 실경로로 한 번 확인한다.
- **해소:** 미해소(위 트리거에서 처리).

### DW-426: [구 #126] self-host 전환의 first-paint 효과가 미측정 — 요청 수는 줄고 첫 방문 전송량은 자릿수로 늘었다

origin: 장부 통합 이관(구 docs/tech-debt.md #126) — 원출처: 2026-07-27 Story 11-0 후속리뷰 defer, 🟡 조건부
location: `web/src/app/fonts/PretendardVariable.woff2`(2,057,688 B) + `web/src/app/layout.tsx`의 `localFont()` — 빌드 산출물의 `<link rel="preload" as="font">`를 라우트별로 확인(프리렌더 `login`·`signup`에만 존재, 아래 내용 참조). *(✎ 2026-07-27 후속리뷰: 최초 등재 시 이 줄에 "전 라우트 확인"이라고 적었으나 아래 내용과 모순이었다 — 실측대로 정정)*
severity: high
reason: 11-0의 Never가 정적 서브셋 파이프라인 신설을 명시적으로 금지했다. 측정 인프라 부재는 대장 #99와 같은 축.
trigger: Story 11.3(히어로) 작업 시 — 그 화면이 "첫인상이 가장 크게 노출되는" 곳이므로, 거기서 전/후 LCP 또는 첫 화면 폰트 전송 바이트를 한 번 재고 판단한다. 과하면 그때 `pyftsubset` 등으로 KS X 1001 + 라틴 서브셋을 만들거나 `preload: false`를 검토한다.
status: open

- **위치:** `web/src/app/fonts/PretendardVariable.woff2`(2,057,688 B) + `web/src/app/layout.tsx`의 `localFont()` — 빌드 산출물의 `<link rel="preload" as="font">`를 라우트별로 확인(프리렌더 `login`·`signup`에만 존재, 아래 내용 참조). *(✎ 2026-07-27 후속리뷰: 최초 등재 시 이 줄에 "전 라우트 확인"이라고 적었으나 아래 내용과 모순이었다 — 실측대로 정정)*
- **내용:** 교체된 CDN dynamic-subset을 직접 재봤다 — CSS 59,900 B + `unicode-range` 92분할, 청크당 약 34~44KB(subset.0=34,568 / 2=43,920 / 45=34,664 / 91=37,996 B). 페이지는 실제 쓰는 범위만 받으므로 통상 수십~수백 KB였다. self-host는 **단일 1.96MiB를 전량 preload**한다. 즉 #40이 겨냥한 "CDN 지연이 first paint를 늦춘다"에 대해 렌더 블로킹 외부 스타일시트 제거는 확실한 이득이지만, **순효과가 정말 개선인지는 전/후 어느 수치로도 측정되지 않았다**(11-0의 검증 항목은 `fonts.check`·jsdelivr 요청 0건·build/lint — 타이밍·전송량 지표 0건). 부수 관측: preload 태그가 프리렌더 라우트(`/login`·`/signup`)에만 붙고 동적 렌더 라우트(`/`·`/search`)엔 안 붙어, 정작 히어로가 놓일 화면에서는 폰트 발견이 CSS 파싱 이후로 밀린다.
- **왜 이 스토리가 안 고쳤나:** 11-0의 Never가 정적 서브셋 파이프라인 신설을 명시적으로 금지했다. 측정 인프라 부재는 대장 #99와 같은 축.
- **트리거:** Story 11.3(히어로) 작업 시 — 그 화면이 "첫인상이 가장 크게 노출되는" 곳이므로, 거기서 전/후 LCP 또는 첫 화면 폰트 전송 바이트를 한 번 재고 판단한다. 과하면 그때 `pyftsubset` 등으로 KS X 1001 + 라틴 서브셋을 만들거나 `preload: false`를 검토한다.
- **해소:** 미해소(위 트리거에서 처리).

### DW-430: [구 #130] 상세 페이지가 독립적인 조회 3건을 순차 await로 체인해 회피 가능한 요청 폭포를 만든다

origin: 장부 통합 이관(구 docs/tech-debt.md #130) — 원출처: 2026-07-27 Story 11-1 코드리뷰 defer, 🟢 품질
location: `web/src/app/(user)/listings/[id]/page.tsx` — 사진 갤러리 URL 조회(`fetchListingGalleryUrls`) → `get_seller_public_summary` RPC → `increment_listing_view` RPC(신규, Story 11-1) 세 호출이 서로 결과를 참조하지 않는데도 순차 `await`로 이어져 있다.
severity: medium
reason: 셋 중 하나(조회수 RPC)만 병렬화하면 나머지 둘은 그대로 순차라 waterfall이 사실상 안 없어지고, 셋 다 고치려면 이 스토리가 손대지 않은 기존 코드(갤러리·판매자요약 호출)까지 리팩터해야 한다.
trigger: 이 페이지의 SSR 지연이 실측으로 문제가 될 때(예: 실사용자 체감 지연 보고, Lighthouse/APM 계측 도입) — 그때 세 호출을 한 번에 `Promise.all`로 묶는다.
status: open

- **위치:** `web/src/app/(user)/listings/[id]/page.tsx` — 사진 갤러리 URL 조회(`fetchListingGalleryUrls`) → `get_seller_public_summary` RPC → `increment_listing_view` RPC(신규, Story 11-1) 세 호출이 서로 결과를 참조하지 않는데도 순차 `await`로 이어져 있다.
- **내용:** 세 조회 모두 서로 독립적이라 `Promise.all`로 병렬 실행이 가능한데, 순차 체인이라 상세 페이지의 서버 응답 시간(TTFB)이 세 왕복 시간의 합이 된다. 갤러리+판매자요약 두 개는 Story 10.6 이전부터 있던 기존 패턴이고, 이번 Story 11-1이 조회수 RPC를 같은 패턴으로 세 번째로 추가했을 뿐이다(blind-hunter 코드리뷰 지적). 이 페이지 하나만 고치는 건 이 스토리 범위를 벗어난다(A3, 외과적 변경).
- **왜 지금 안 고치나:** 셋 중 하나(조회수 RPC)만 병렬화하면 나머지 둘은 그대로 순차라 waterfall이 사실상 안 없어지고, 셋 다 고치려면 이 스토리가 손대지 않은 기존 코드(갤러리·판매자요약 호출)까지 리팩터해야 한다.
- **트리거:** 이 페이지의 SSR 지연이 실측으로 문제가 될 때(예: 실사용자 체감 지연 보고, Lighthouse/APM 계측 도입) — 그때 세 호출을 한 번에 `Promise.all`로 묶는다.

### DW-431: [구 #131] `listings.seller_name`이 등록 시점(INSERT)에만 위조를 막고 이후 UPDATE로는 판매자가 직접 바꿀 수 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #131) — 원출처: 2026-07-27 Story 11-1 코드리뷰 defer, 🟡 조건부
location: `supabase/migrations/0007_listings_seller_name.sql`(BEFORE INSERT 트리거만 존재) vs `supabase/migrations/0020_listings_view_count.sql`(이번 스토리가 `authenticated`의 `listings` UPDATE 권한을 컬럼 단위로 전면 재감사하며 만든 GRANT 목록에 `seller_name`을 그대로 포함).
severity: high
reason: 0007은 등록(INSERT) 시점의 위조만 BEFORE INSERT 트리거로 막고 BEFORE UPDATE 트리거가 없어 판매자가 등록 후 직접 UPDATE로 `seller_name`을 원하는 값으로 바꿀 수 있는데, 이번 0020 마이그레이션의 GRANT 재감사에서도 이 gap이 그대로 물려받아졌다.
trigger: `listings`의 UPDATE 권한을 다시 감사하는 다음 마이그레이션, 또는 판매자 표시 이름 위조가 실제 이슈로 보고될 때 — BEFORE UPDATE 트리거를 추가해 INSERT와 대칭을 맞춘다.
status: open

- **위치:** `supabase/migrations/0007_listings_seller_name.sql`(BEFORE INSERT 트리거만 존재) vs `supabase/migrations/0020_listings_view_count.sql`(이번 스토리가 `authenticated`의 `listings` UPDATE 권한을 컬럼 단위로 전면 재감사하며 만든 GRANT 목록에 `seller_name`을 그대로 포함).
- **내용:** 0007은 매물 등록(INSERT) 시 `seller_name`을 이메일 로컬파트로 자동 채우는 BEFORE INSERT 트리거만 두었다 — BEFORE UPDATE 트리거는 이 리포 어디에도 없다(grep으로 확인: `before update`에 seller_name 로직 없음). 즉 판매자가 등록 후 `supabase.from('listings').update({ seller_name: '...' }).eq('id', 본인매물)`을 직접 호출하면 원하는 값으로 바꿀 수 있다. 이번 0020 마이그레이션이 `authenticated`의 `listings` UPDATE 권한을 컬럼 단위로 전부 다시 감사하는 유일한 기회였지만, 이 gap은 그대로 물려받아 `seller_name`을 UPDATE 가능 컬럼 목록에 포함시켰다(회귀를 만들지 않으려는 그 스토리의 범위 결정이었지, 이 gap을 새로 만든 것은 아니다).
- **트리거:** `listings`의 UPDATE 권한을 다시 감사하는 다음 마이그레이션, 또는 판매자 표시 이름 위조가 실제 이슈로 보고될 때 — BEFORE UPDATE 트리거를 추가해 INSERT와 대칭을 맞춘다.

### DW-432: [구 #132] 상세 페이지의 RPC 배선(`get_seller_public_summary`·`increment_listing_view`)이 실제로 호출되는지 검증하는 테스트가 전무하다

origin: 장부 통합 이관(구 docs/tech-debt.md #132) — 원출처: 2026-07-27 Story 11-1 코드리뷰 defer, 🟡 검증갭
location: `web/src/app/(user)/listings/[id]/page.tsx`의 두 `supabase.rpc(...)` 호출 지점 vs `web/src/app/(user)/listings/[id]/__tests__/`(`detailSectionsAssembly.test.ts`·`sellerInfo.test.ts` 둘 다 순수 함수만 테스트, `page.tsx`를 import하거나 `supabase.rpc`를 mock하지 않음. repo 전체 grep으로도 `*.test.ts(x)` 안의 `rpc(` 호출 0건 확인).
severity: high
reason: `get_seller_public_summary`·`increment_listing_view` 두 RPC 호출 지점 모두 `page.tsx`를 import하거나 `supabase.rpc`를 mock하는 테스트가 없어, 이 리포는 서버 컴포넌트의 RPC 배선을 코드리뷰로만 확인해 온 것이 지금까지의 관례다.
trigger: web에 서버 컴포넌트 레벨에서 Supabase 클라이언트를 mock하는 테스트 하네스가 도입될 때 — 그때 이 두 호출 지점을 함께 커버한다.
status: open

- **위치:** `web/src/app/(user)/listings/[id]/page.tsx`의 두 `supabase.rpc(...)` 호출 지점 vs `web/src/app/(user)/listings/[id]/__tests__/`(`detailSectionsAssembly.test.ts`·`sellerInfo.test.ts` 둘 다 순수 함수만 테스트, `page.tsx`를 import하거나 `supabase.rpc`를 mock하지 않음. repo 전체 grep으로도 `*.test.ts(x)` 안의 `rpc(` 호출 0건 확인).
- **내용:** `get_seller_public_summary`(Story 10.6)는 이미 이 gap을 갖고 있었고, `increment_listing_view`(Story 11-1, 이번 diff)가 같은 파일에 같은 패턴으로 추가되며 gap을 하나 더 늘렸다. 실DB 통합 테스트(`test_seller_summary_real_db.py`·`test_view_count_rpc_real_db.py`)는 "RPC 자체가 옳게 동작하는가"는 실측하지만 "page.tsx가 실제로 그 RPC를 부르는가"는 검증 대상 밖이라고 각 파일 docstring이 명시적으로 선언하고 있다 — 이 리포는 서버 컴포넌트의 RPC 배선을 코드리뷰로만 확인하는 것이 지금까지의 관례다(verification-gap·intent-alignment 리뷰 공통 지적).
- **트리거:** web에 서버 컴포넌트 레벨에서 Supabase 클라이언트를 mock하는 테스트 하네스가 도입될 때 — 그때 이 두 호출 지점을 함께 커버한다.

### DW-433: [구 #133] 실DB 통합 테스트 전부가 Postgres 롤 임퍼소네이션만 검증하고 실제 PostgREST/HTTP RPC 경로는 한 번도 거치지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #133) — 원출처: 2026-07-27 Story 11-1 코드리뷰 defer, 🟢 품질
location: `api/tests/integration/test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`·`test_fr11_cover_images_real_db.py`·신규 `test_view_count_rpc_real_db.py` — 전부 `psycopg`로 직접 연결해 `set local role`로 역할만 바꾸는 동일 패턴.
severity: medium
reason: 이 테스트들은 Postgres가 실제로 권한을 강제하는지는 검증하지만 그 아래 계층인 PostgREST 노출(스키마 설정·함수명 일치 등)은 검증 범위 밖이라, 그 계층만의 실패는 테스트 스위트가 전부 초록인 채로 웹에서만 발생할 수 있다.
trigger: web에 E2E(브라우저→서버→DB 전 구간) 테스트 계층이 도입되거나(#106과 같은 축), PostgREST 노출 설정 자체가 회귀 대상으로 의심될 때.
status: open

- **위치:** `api/tests/integration/test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`·`test_fr11_cover_images_real_db.py`·신규 `test_view_count_rpc_real_db.py` — 전부 `psycopg`로 직접 연결해 `set local role`로 역할만 바꾸는 동일 패턴.
- **내용:** 이 테스트들은 "SQL에 그 글자가 있는 것과 Postgres가 실제로 강제하는 것은 다르다"(B4)는 원칙은 지키지만, 그 아래 계층(PostgREST가 이 함수를 실제로 노출하는지, `db-schemas` 설정, 함수명·파라미터명이 REST 경로에서 실제로 일치하는지)은 검증 범위 밖이다(blind-hunter 코드리뷰 지적). 웹은 `supabase.rpc(...)`로 이 계층을 거치므로, 이 계층만의 실패(예: 노출 스키마 설정 누락)는 이 테스트 스위트 전부가 초록인 채로 웹에서만 발생할 수 있다.
- **트리거:** web에 E2E(브라우저→서버→DB 전 구간) 테스트 계층이 도입되거나(#106과 같은 축), PostgREST 노출 설정 자체가 회귀 대상으로 의심될 때.

### DW-435: [구 #135] 0020의 GRANT 화이트리스트가 `embedding`·`id`를 포함한다 — 판매자가 자기 매물의 검색 벡터와 기본키를 직접 바꿀 수 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #135) — 원출처: 2026-07-27 Story 11-1 후속리뷰 defer, 🟡 조건부
location: `supabase/migrations/0020_listings_view_count.sql`의 `grant update (...) on public.listings to authenticated` 목록 중 `id`·`embedding` 항목.
severity: high
reason: 0020 이전에도 authenticated는 테이블 단위 UPDATE로 두 컬럼을 이미 쓸 수 있었다(플랫폼 기본 GRANT) — 회귀가 아니라 성문화다. 목록에서 빼면 임베딩 backfill 경로가 어떤 롤로 도는지 먼저 확정해야 하는데(확인 안 됨), 그 조사는 조회수 스토리 범위 밖이다(A3).
trigger: `listings` UPDATE 권한을 다시 감사하는 다음 마이그레이션 — #131과 같은 자리에서 함께 처리한다. 그때 임베딩 backfill 주체 롤을 먼저 실측하고, 판매자에게 불필요한 컬럼(`id`·`embedding`·`seller_id`·`created_at`)을 목록에서 걷어낸다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql`의 `grant update (...) on public.listings to authenticated` 목록 중 `id`·`embedding` 항목.
- **내용:** #131(`seller_name`)과 같은 축이지만 영향이 더 크다. 0020은 authenticated의 `listings` UPDATE 권한을 **명시적 화이트리스트로 성문화**하면서 `embedding`(AI 의미검색 벡터)과 `id`(기본키)를 그대로 넣었다. 실측(스크래치 PG18): 소유 판매자 롤로 `update public.listings set embedding = '...'` 성공, `update ... set id = '3333…'` 도 성공해 행의 정체성이 바뀌었다. `embedding`은 판매자가 손수 조율하면 경로 B 의미검색에서 임의 질의에 1등으로 뜰 수 있고, `id` 변경은 공유·북마크된 `/listings/[id]` URL을 조용히 404로 만든다(자식 행이 있으면 FK로 에러). `0011`이 anon에게 `embedding` **읽기**를 차단 대상으로 명시한 것과 대조된다 — 읽기는 막고 쓰기는 축복한 셈.
- **왜 지금 안 고치나:** 0020 이전에도 authenticated는 테이블 단위 UPDATE로 두 컬럼을 이미 쓸 수 있었다(플랫폼 기본 GRANT) — 회귀가 아니라 **성문화**다. 목록에서 빼면 임베딩 backfill 경로가 어떤 롤로 도는지 먼저 확정해야 하는데(확인 안 됨), 그 조사는 조회수 스토리 범위 밖이다(A3).
- **트리거:** `listings` UPDATE 권한을 다시 감사하는 다음 마이그레이션 — #131과 **같은 자리에서 함께** 처리한다. 그때 임베딩 backfill 주체 롤을 먼저 실측하고, 판매자에게 불필요한 컬럼(`id`·`embedding`·`seller_id`·`created_at`)을 목록에서 걷어낸다.

### DW-436: [구 #136] 조회수는 "웹 상세 열람"만 센다 — Flutter 앱 상세는 RPC를 부르지 않고, 단일성 검사도 `web/src`만 본다

origin: 장부 통합 이관(구 docs/tech-debt.md #136) — 원출처: 2026-07-27 Story 11-1 후속리뷰 defer, 🟢 품질
location: `app/lib/features/listings/listing_detail_screen.dart`(상세 화면인데 `.rpc(` 호출 0건 — 앱 전체에 RPC 호출 자체가 없다) vs `web/src/app/(user)/listings/[id]/page.tsx`. 검사 쪽은 `web/src/app/(user)/listings/[id]/__tests__/viewCountCallSite.test.ts`의 `SRC_ROOT`가 `web/src`로 고정.
severity: medium
reason: 이 리포의 기존 관례가 웹 우선이다(Story 10.6의 `get_seller_public_summary`도 앱은 채택하지 않았다 — 앱에 `.rpc(` 호출이 0건인 것이 그 증거). 관례 자체를 바꾸는 것은 조회수 스토리의 범위 밖이다.
trigger: Story 11.4에서 인기 순위를 제품에 노출할 때 — 그 시점에 (a) 앱도 올릴지 (b) 웹 전용 지표로 문서에 못박을지를 결정하고, 어느 쪽이든 단일성 검사의 스캔 범위를 그 결정에 맞춘다. 또는 Epic 16(앱 작업)에서 앱이 RPC를 처음 쓰게 될 때.
status: open

- **위치:** `app/lib/features/listings/listing_detail_screen.dart`(상세 화면인데 `.rpc(` 호출 0건 — 앱 전체에 RPC 호출 자체가 없다) vs `web/src/app/(user)/listings/[id]/page.tsx`. 검사 쪽은 `web/src/app/(user)/listings/[id]/__tests__/viewCountCallSite.test.ts`의 `SRC_ROOT`가 `web/src`로 고정.
- **내용:** 두 화면은 "매물 상세 진입"이라는 **같은 관측 계약**인데 웹만 조회수를 올린다. 그래서 `view_count`의 실제 의미는 "상세 열람 수"가 아니라 "**웹** 상세 열람 수"이고, Story 11.4의 인기 순위는 모바일 트래픽 비중만큼 왜곡된다 — 이게 의도된 절충인지 누락인지 어느 문서에도 없다. 함께: 단일성 검사가 `web/src`의 `.ts/.tsx`만 스캔하므로 앱이 나중에 카드 렌더 경로에서 이 RPC를 부르면 검사는 green인 채 불변식이 깨진다.
- **왜 지금 안 고치나:** 이 리포의 기존 관례가 웹 우선이다(Story 10.6의 `get_seller_public_summary`도 앱은 채택하지 않았다 — 앱에 `.rpc(` 호출이 0건인 것이 그 증거). 관례 자체를 바꾸는 것은 조회수 스토리의 범위 밖이다.
- **트리거:** Story 11.4에서 인기 순위를 **제품에 노출**할 때 — 그 시점에 (a) 앱도 올릴지 (b) 웹 전용 지표로 문서에 못박을지를 결정하고, 어느 쪽이든 단일성 검사의 스캔 범위를 그 결정에 맞춘다. 또는 Epic 16(앱 작업)에서 앱이 RPC를 처음 쓰게 될 때.

### DW-437: [구 #137] `docs/db-schema-guide.md`(발표용 스키마 설명)가 실제 스키마보다 늙었다

origin: 장부 통합 이관(구 docs/tech-debt.md #137) — 원출처: 2026-07-27 Story 11-1 후속리뷰 defer, 🟢 품질
location: `docs/db-schema-guide.md`의 `listings` 컬럼 표와 마이그레이션 인덱스 절.
severity: medium
reason: 이 스토리가 만든 드리프트가 아니라 누적된 것이고(0017·0012~0019 구간), 인접 문서를 "개선"하지 않는다는 A3에 걸린다. 요약표 📅 행에 이미 "`db-schema-guide` 표 갱신(증분 후)"으로 잡혀 있으나 번호가 없어 추적되지 않았다 — 이 항목이 그 번호다.
trigger: Epic 11 종료 시점(증분 스키마 변경이 멎는 자리) 또는 발표·시연 자료를 만들 때 — 그때 표를 실제 `information_schema`에서 다시 뽑아 한 번에 맞춘다.
status: open

- **위치:** `docs/db-schema-guide.md`의 `listings` 컬럼 표와 마이그레이션 인덱스 절.
- **내용:** 컬럼 표에 0017의 신뢰속성 3종이 빠져 있고 마이그레이션 인덱스는 0009에서 멈춰 있다. Story 11-1이 `view_count`를 더해 격차가 한 칸 더 벌어졌다. project-context가 이 파일을 **발표용 스키마 설명**으로 지정했으므로, 시연·리뷰 자리에서 읽히는 바로 그 문서가 스키마를 잘못 설명하게 된다.
- **왜 지금 안 고치나:** 이 스토리가 만든 드리프트가 아니라 누적된 것이고(0017·0012~0019 구간), 인접 문서를 "개선"하지 않는다는 A3에 걸린다. 요약표 📅 행에 이미 "`db-schema-guide` 표 갱신(증분 후)"으로 잡혀 있으나 번호가 없어 추적되지 않았다 — 이 항목이 그 번호다.
- **트리거:** Epic 11 종료 시점(증분 스키마 변경이 멎는 자리) 또는 발표·시연 자료를 만들 때 — 그때 표를 실제 `information_schema`에서 다시 뽑아 한 번에 맞춘다.

### DW-439: [구 #139] `anon`·`authenticated`가 `listings`에 대해 TRUNCATE·REFERENCES·TRIGGER·MAINTAIN을 계속 보유한다

origin: 장부 통합 이관(구 docs/tech-debt.md #139) — 원출처: 2026-07-28 Story 11-1 후속리뷰 2차 defer, 🟢 품질
location: `supabase/migrations/0020_listings_view_count.sql` 5번 블록(`revoke insert, update, delete … from anon`) — 8개 테이블 권한 중 3개만 회수한다. #18(플랫폼 기본 GRANT 축)과 같은 뿌리.
severity: medium
reason: PostgREST에 TRUNCATE 동사가 없어 브라우저/anon 키 경로로는 도달할 수 없고, `revoke all`은 해법이 아니다 — 0011이 anon에게 준 컬럼 SELECT까지 날아가 비로그인 열람이 즉시 깨진다(실측 확인). 남은 4개를 이름으로 골라 회수하는 것은 조회수 스토리 범위 밖의 권한 정리다.
trigger: #18(플랫폼 기본 GRANT)을 정리하는 마이그레이션을 만들 때 — 그때 `listings`뿐 아니라 전 테이블에 대해 `truncate, references, trigger, maintain`을 anon·authenticated에서 한 번에 회수하고, `has_table_privilege` 8종 단언을 실DB 테스트에 심는다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql` 5번 블록(`revoke insert, update, delete … from anon`) — 8개 테이블 권한 중 3개만 회수한다. #18(플랫폼 기본 GRANT 축)과 같은 뿌리.
- **내용:** 0020 적용 후 실측 `relacl` = `anon=Dxtm`, `authenticated=rdDxtm`. 리뷰어가 `set local role anon; truncate public.listings cascade;`를 실제로 실행해 성공시켰고, FK를 타고 `chat_rooms`·`listing_images`·`wishlists`·`chat_messages`까지 비워졌다. **TRUNCATE는 RLS를 아예 우회한다.** 개념적으로 더 날카로운 건 남아 있는 `TRIGGER` 비트다 — BEFORE UPDATE 트리거의 NEW 튜플 조작은 컬럼 권한을 통째로 우회하므로, 그게 가능하면 이 마이그레이션이 세운 컬럼 단위 방어가 무의미해진다(현재는 두 롤에 `public` 스키마 CREATE 권한이 없어 트리거를 못 만든다 — 실측 확인).
- **왜 지금 안 고치나:** PostgREST에 TRUNCATE 동사가 없어 브라우저/anon 키 경로로는 도달할 수 없다(직접 Postgres 연결이 있어야 하는데 그건 이미 다른 얘기다). 그리고 **`revoke all`은 해법이 아니다** — 0011이 anon에게 준 컬럼 SELECT까지 날아가 비로그인 열람이 즉시 깨진다(실측 확인). 남은 4개를 이름으로 골라 회수하는 것은 조회수 스토리 범위 밖의 권한 정리다.
- **트리거:** #18(플랫폼 기본 GRANT)을 정리하는 마이그레이션을 만들 때 — 그때 `listings`뿐 아니라 전 테이블에 대해 `truncate, references, trigger, maintain`을 anon·authenticated에서 한 번에 회수하고, `has_table_privilege` 8종 단언을 실DB 테스트에 심는다.

### DW-440: [구 #140] `created_at`이 INSERT 화이트리스트에 있어 등록 시점 등록일 위조가 가능하다

origin: 장부 통합 이관(구 docs/tech-debt.md #140) — 원출처: 2026-07-28 Story 11-1 후속리뷰 2차 defer, 🟢 품질
location: `supabase/migrations/0020_listings_view_count.sql` 4번 블록의 `grant insert (… id, embedding, created_at, updated_at …)` 목록. #135(UPDATE 축의 `embedding`·`id`)의 **INSERT 쪽 짝**이다.
severity: medium
reason: 목록에서 빼면 등록 경로(SellForm·Flutter `sell_controller`)가 실제로 어떤 컬럼을 보내는지 먼저 실측해야 하고(빼면 등록이 깨질 수 있다), 그 조사는 #135와 같은 자리에서 함께 하는 것이 맞다.
trigger: #135와 동일 — `listings` 쓰기 권한을 다시 감사하는 다음 마이그레이션. 그때 UPDATE·INSERT 두 축의 화이트리스트를 함께 좁히고, `created_at`은 BEFORE INSERT 트리거로 `now()` 강제를 검토한다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql` 4번 블록의 `grant insert (… id, embedding, created_at, updated_at …)` 목록. #135(UPDATE 축의 `embedding`·`id`)의 **INSERT 쪽 짝**이다.
- **내용:** 0002는 `created_at` 위조를 **BEFORE UPDATE 트리거로만** 막는다("소유자가 UPDATE에 created_at을 끼워 넣어 최신 등록처럼 위장하는 것을 차단"). INSERT 경로엔 대응 방어가 없어, 판매자가 등록 요청에 `created_at`을 실어 보내면 원하는 등록일로 박을 수 있다 — 등록일 정렬 신뢰성이 UPDATE 축에서만 지켜지고 INSERT 축에선 안 지켜진다. 0020이 이 권한을 **명시적 화이트리스트로 성문화**했다(그 전에는 테이블 단위 기본 GRANT로 암묵적으로 있던 것 — 회귀는 아니다).
- **왜 지금 안 고치나:** 목록에서 빼면 등록 경로(SellForm·Flutter `sell_controller`)가 실제로 어떤 컬럼을 보내는지 먼저 실측해야 하고(빼면 등록이 깨질 수 있다), 그 조사는 #135와 **같은 자리에서 함께** 하는 것이 맞다.
- **트리거:** #135와 동일 — `listings` 쓰기 권한을 다시 감사하는 다음 마이그레이션. 그때 UPDATE·INSERT 두 축의 화이트리스트를 함께 좁히고, `created_at`은 BEFORE INSERT 트리거로 `now()` 강제를 검토한다.

### DW-441: [구 #141] `listings_set_timestamps` 조건이 "view_count**만**"이 아니라 "view_count가 바뀌면"이라, 혼합 UPDATE가 `updated_at`을 건너뛴다

origin: 장부 통합 이관(구 docs/tech-debt.md #141) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟡 조건부
location: `supabase/migrations/0020_listings_view_count.sql` 6번 블록 `public.listings_set_timestamps()`의 `if new.view_count is not distinct from old.view_count then new.updated_at := now(); end if;`.
severity: high
reason: 현재 어떤 클라이언트 경로로도 이 트리거 조건에 도달할 수 없고(view_count 쓰기 권한은 이미 회수됨), 제안된 수정은 pgvector가 없는 샌드박스에서 vector 컬럼을 `to_jsonb`가 어떻게 다루는지 검증할 수 없어 모든 UPDATE가 지나가는 트리거에 미검증 변경을 넣는 것을 피했다.
trigger: pgvector가 실제로 있는 환경(로컬 Supabase Docker 스택 또는 원격)에서 `to_jsonb(<listings 행>)`이 vector 컬럼에 대해 정상 동작함을 실측할 수 있을 때 — 그때 조건을 "오직 view_count만 바뀐 경우"로 좁히고, `price`+`view_count` 혼합 UPDATE가 `updated_at`을 갱신하는지 단언하는 테스트를 함께 심는다. 또는 `view_count`를 다른 컬럼과 함께 쓰는 정당한 경로(백필 스크립트 등)가 처음 생길 때 — 그 순간 도달 가능해진다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql` 6번 블록 `public.listings_set_timestamps()`의 `if new.view_count is not distinct from old.view_count then new.updated_at := now(); end if;`.
- **내용:** 함수 옆 주석은 "view_count**만** 바뀐 UPDATE(=조회수 증가)는 수정으로 치지 않는다"라고 읽히지만, 실제 조건은 "view_count가 바뀌었는가" 하나뿐이다. 그래서 `view_count`를 **다른 컬럼과 함께** 바꾸는 UPDATE는 그 다른 컬럼이 진짜 수정이어도 `updated_at`이 갱신되지 않는다. 실측(스크래치 PG18, 마이그 20개 적용): `update public.listings set price = 31111111, view_count = view_count + 1` → `price`는 31111111로 바뀌었는데 `updated_at`은 이전 값 그대로. `updated_at`은 관리자 거래내역 화면이 **거래일**로 쓰는 값이다(#20·`db-schema-guide.md`).
- **왜 지금 안 고치나:** ① **현재 어떤 클라이언트 경로로도 도달할 수 없다** — 0020의 3·4번 블록이 `authenticated`에서, 5번 블록이 `anon`에서 `view_count` 쓰기를 회수했고(실측: `has_column_privilege` 전 조합 false), `service_role` 키는 프로젝트 규칙상 어디에도 두지 않는다(project-context 규칙 6). 남는 경로는 운영자가 직접 psql로 도는 경우뿐이다. ② 제안된 수정(`to_jsonb(new) - 'view_count' - 'updated_at'` 행 전체 비교)은 **운영에서 검증할 수 없다** — 운영의 `embedding`은 `vector(768)`인데 이 샌드박스엔 pgvector가 없어 `to_jsonb(record)`가 vector 컬럼을 어떻게 다루는지 실측 불가다. 검증 못 한 변경을 **모든 listings UPDATE가 지나가는 트리거**에 넣는 것은 도달 불가 결함을 고치려고 도달 가능 경로를 거는 것이다(B4). 참고로 비용 자체는 실측했다 — 6.9KB 임베딩 기준 조회 1회당 0.168ms → 0.363ms(+0.2ms)로, **성능은 반대 이유가 아니다.**
- **트리거:** pgvector가 실제로 있는 환경(로컬 Supabase Docker 스택 또는 원격)에서 `to_jsonb(<listings 행>)`이 vector 컬럼에 대해 정상 동작함을 실측할 수 있을 때 — 그때 조건을 "오직 view_count만 바뀐 경우"로 좁히고, `price`+`view_count` 혼합 UPDATE가 `updated_at`을 **갱신하는지** 단언하는 테스트를 함께 심는다. 또는 `view_count`를 다른 컬럼과 함께 쓰는 정당한 경로(백필 스크립트 등)가 처음 생길 때 — 그 순간 도달 가능해진다.

### DW-442: [구 #142] `public.set_updated_at()`이 참조 트리거 0건인 고아가 됐고, 학습 문서는 아직 그것이 살아 있다고 가르친다

origin: 장부 통합 이관(구 docs/tech-debt.md #142) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟢 품질
location: `supabase/migrations/0002_listings.sql`이 만든 `public.set_updated_at()` · `supabase/migrations/0020_listings_view_count.sql` 6번 블록(`drop trigger if exists listings_set_updated_at`) · `docs/learning/01-db.md:107`.
severity: medium
reason: 함수 삭제는 0002의 소유물을 지우는 별도 판단이고(A3 — 이번 변경이 고아로 만들었을 뿐, 지우는 것은 다른 결정이다), 학습 문서 갱신은 이 스토리가 만든 드리프트 한 줄을 넘어 문서 전반의 정합성 문제다(#137과 같은 축).
trigger: #137(`db-schema-guide.md` 표 갱신)을 처리할 때 함께 — 그 자리에서 학습 문서의 트리거 설명도 `listings_set_timestamps()` 기준으로 고치고, `set_updated_at()`을 남길지(다른 테이블이 나중에 쓸 공용 함수로) 지울지를 한 번에 정한다. 0020의 주석은 이번 패스에서 실측에 맞게 정정했다(과거 주석은 "다른 테이블도 쓸 수 있다"고 단정했으나 거짓이었다).
status: open

- **위치:** `supabase/migrations/0002_listings.sql`이 만든 `public.set_updated_at()` · `supabase/migrations/0020_listings_view_count.sql` 6번 블록(`drop trigger if exists listings_set_updated_at`) · `docs/learning/01-db.md:107`.
- **내용:** 0020이 `listings_set_updated_at` 트리거를 `listings_set_timestamps`로 교체하면서, `set_updated_at()`을 쓰던 **마지막 사용처가 사라졌다**. 실측(0020까지 적용한 스크래치 DB): 이 함수를 참조하는 non-internal 트리거 **0건**, 리포 전체 grep에서도 `0002`·`0020` 밖 참조 0건 — `listings`가 유일한 사용자였다. 함께: `docs/learning/01-db.md:107`이 여전히 "`set_updated_at()` 트리거 — 매물을 수정할 때마다 `updated_at`을 자동 갱신, 동시에 `created_at` 고정"이라고 **현재 동작인 것처럼** 설명한다. 이제 `listings`의 그 임무는 `listings_set_timestamps()`가 하고, `updated_at` 갱신엔 조회수 예외가 붙는다(#141).
- **왜 지금 안 고치나:** 함수 삭제는 0002의 소유물을 지우는 별도 판단이고(A3 — 이번 변경이 고아로 만들었을 뿐, 지우는 것은 다른 결정이다), 학습 문서 갱신은 이 스토리가 만든 드리프트 한 줄을 넘어 문서 전반의 정합성 문제다(#137과 같은 축).
- **트리거:** #137(`db-schema-guide.md` 표 갱신)을 처리할 때 **함께** — 그 자리에서 학습 문서의 트리거 설명도 `listings_set_timestamps()` 기준으로 고치고, `set_updated_at()`을 남길지(다른 테이블이 나중에 쓸 공용 함수로) 지울지를 한 번에 정한다. 0020의 주석은 이번 패스에서 실측에 맞게 정정했다(과거 주석은 "다른 테이블도 쓸 수 있다"고 단정했으나 거짓이었다).

### DW-443: [구 #143] 마이그레이션 게이트가 "재적용"을 한 번도 시험하지 않는다 — 0020이 실제로 그 구멍에 빠졌다

origin: 장부 통합 이관(구 docs/tech-debt.md #143) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟡 조건부
location: `scripts/check_migrations.py:246-249`(`run_dynamic_checks`가 `ordered`를 **한 번만** 적용한다) · `supabase/migrations/0020_listings_view_count.sql` 6번 블록.
severity: high
reason: `check_migrations.py`는 게이트 인프라이고, 여기에 2회차 적용 패스를 넣는 것은 조회수 스토리의 범위 밖이다(A3). 넣으면 20개 마이그 전부가 새 계약(멱등)을 지게 되므로, 먼저 전량이 실제로 재적용 가능한지 실측해야 한다.
trigger: 게이트 구조 자체를 손대는 다음 작업(#22~24가 예약한 Epic 13 게이트 정비) — 그때 `run_dynamic_checks`에 "같은 컨테이너에 전량을 한 번 더 적용하고 exit 0을 요구"하는 2차 패스를 추가한다. 오늘 돌리면 초록이어야 하며, 그렇지 않은 파일이 나오면 그 자체가 발견이다.
status: open

- **위치:** `scripts/check_migrations.py:246-249`(`run_dynamic_checks`가 `ordered`를 **한 번만** 적용한다) · `supabase/migrations/0020_listings_view_count.sql` 6번 블록.
- **내용:** 이 리포의 마이그레이션은 전부 `add column if not exists`·`create or replace`·`drop ... if exists`로 **재적용 가능하게** 쓰여 있는데, 게이트는 빈 컨테이너에 전량을 1회 적용할 뿐이라 그 성질을 아무도 검사하지 않는다. 실제로 이번 스토리가 그 구멍에 빠졌다 — 0020은 트리거 **이름을 바꾸는** 첫 마이그레이션이라 옛 이름만 `drop if exists` 했고, 이미 0020이 적용된 DB에 다시 적용하면 `ERROR: trigger "listings_set_timestamps" for relation "listings" already exists`로 죽었다(실측 exit 3). `create trigger`엔 `or replace`·`if not exists`가 없어 drop이 유일한 수단이다. 이번 패스에서 `drop trigger if exists listings_set_timestamps`를 추가해 고쳤고 재적용 exit 0을 확인했지만, **그 성질을 지키는 검사는 여전히 없다** — 그 한 줄을 지워도 게이트·pytest·vitest가 전부 초록이다. 재적용이 가상의 시나리오가 아니라는 근거: `docs/deployment-runbook.md:101,125`가 `listings_anon_select`(0011)를 원격에 실제로 재적용한 사례를 기록하고 있다.
- **왜 지금 안 고치나:** `check_migrations.py`는 게이트 인프라이고, 여기에 2회차 적용 패스를 넣는 것은 조회수 스토리의 범위 밖이다(A3). 넣으면 20개 마이그 전부가 새 계약(멱등)을 지게 되므로, 먼저 전량이 실제로 재적용 가능한지 실측해야 한다.
- **트리거:** 게이트 구조 자체를 손대는 다음 작업(#22~24가 예약한 Epic 13 게이트 정비) — 그때 `run_dynamic_checks`에 "같은 컨테이너에 전량을 한 번 더 적용하고 exit 0을 요구"하는 2차 패스를 추가한다. 오늘 돌리면 초록이어야 하며, 그렇지 않은 파일이 나오면 그 자체가 발견이다.

### DW-445: [구 #145] `view_count`가 `int`라 21억에서 오버플로하고, 그 뒤 해당 매물의 상세 진입은 매번 조용히 실패한다

origin: 장부 통합 이관(구 docs/tech-debt.md #145) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟢 품질
location: `supabase/migrations/0020_listings_view_count.sql` 1번 블록 `view_count int not null default 0` + 2번 블록 `view_count = view_count + 1`.
severity: medium
reason: intent-contract가 `int not null default 0`을 명시했고 스코프 권한은 intent에 있다(2차 리뷰에서 `bigint` 제안이 같은 이유로 기각됐다). 데모 규모에서 21억 회 호출은 발생하지 않는다.
trigger: 실사용 트래픽을 받는 서비스로 전환할 때 — 그때 `alter table public.listings alter column view_count type bigint;` 전진 마이그레이션 한 줄로 처리한다(데이터가 적을 때가 압도적으로 싸다). 또는 조회수 남용 방어(intent가 배제한 rate limit·dedup)를 도입하는 자리에서 함께 판단한다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql` 1번 블록 `view_count int not null default 0` + 2번 블록 `view_count = view_count + 1`.
- **내용:** `int`(int4) 상한은 2,147,483,647이다. `increment_listing_view`는 `anon`에게 EXECUTE가 열려 있고 레이트리밋·중복제거가 **의도적으로** 없으므로(intent의 Never — 데모 규모 판단), 상한 도달은 이론이 아니라 호출 횟수 문제다. 도달하면 그 행의 RPC가 영구히 `22003 integer out of range`로 실패하는데, `page.tsx`는 실패를 `console.error`로 삼키므로 **화면은 멀쩡하고** 카운터만 21.4억에 고정된 채 요청마다 서버 로그가 오염된다.
- **왜 지금 안 고치나:** intent-contract가 `int not null default 0`을 **명시**했고 스코프 권한은 intent에 있다(2차 리뷰에서 `bigint` 제안이 같은 이유로 기각됐다). 데모 규모에서 21억 회 호출은 발생하지 않는다.
- **트리거:** 실사용 트래픽을 받는 서비스로 전환할 때 — 그때 `alter table public.listings alter column view_count type bigint;` 전진 마이그레이션 한 줄로 처리한다(데이터가 적을 때가 압도적으로 싸다). 또는 조회수 남용 방어(intent가 배제한 rate limit·dedup)를 도입하는 자리에서 함께 판단한다.

### DW-446: [구 #146] 로컬 시드의 명시 컬럼 목록이 "시끄러운 실패"를 "조용한 누락"으로 바꿨고, 나머지 4개 삽입문은 여전히 `select *`다

origin: 장부 통합 이관(구 docs/tech-debt.md #146) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟡 조건부
location: `supabase/seed-local/02_data.sql:26-46`(`listings` 삽입문 — 25컬럼 하드코딩) · 같은 파일 51·59·65·71줄(`listing_images`·`chat_rooms`·`chat_messages`·`guide_documents`는 그대로 `select * from jsonb_populate_recordset(...)`).
severity: high
reason: 대안(`data/listings.json` 103행에 `"view_count": 0` 추가)은 다음 컬럼에서 같은 함정을 또 만난다고 스펙이 판단했다. 나머지 4개 테이블엔 오늘 문제가 없고(전부 nullable), 없는 문제를 미리 고치는 것은 A2 위반이다. 시드를 도는 CI 잡 자체가 없어 자동 검사를 붙이려면 새 잡이 필요하다.
trigger: ① `listings`에 컬럼을 추가하는 다음 마이그레이션 — 그때 이 목록도 락스텝 갱신 대상이므로 `docs/conventions.md` §4.1 체크리스트에 이 파일을 추가할지 함께 정한다. ② 또는 4개 테이블 중 하나에 `not null` 컬럼을 추가할 때 — 그 자리에서 해당 삽입문도 명시 목록으로 바꾼다.
status: open

- **위치:** `supabase/seed-local/02_data.sql:26-46`(`listings` 삽입문 — 25컬럼 하드코딩) · 같은 파일 51·59·65·71줄(`listing_images`·`chat_rooms`·`chat_messages`·`guide_documents`는 그대로 `select * from jsonb_populate_recordset(...)`).
- **내용:** 0020이 `view_count not null`을 추가하면서 `select *`가 시드를 통째로 죽였고(실측 재현), 이번 스토리가 `listings` 삽입문만 명시 컬럼 목록으로 바꿔 고쳤다. 그 대가로 **실패 모양이 뒤집혔다** — 앞으로 `listings`에 nullable 컬럼이 추가되고 `data/listings.json`에 그 값이 들어와도, 목록에 없으면 **아무 에러 없이 조용히** 비워진 채 시드된다. 기존 `select *`는 같은 상황에서 즉시 깨졌다. 그리고 이 목록은 GRANT 목록 2개(0020의 UPDATE·INSERT 화이트리스트)에 이은 **세 번째 25컬럼 사본**인데, 앞의 둘과 달리 `information_schema`에서 실시간 도출해 대조하는 테스트가 **없다**. 함께: 나머지 4개 삽입문은 손대지 않았으므로(A3 — 이 변경이 깨뜨린 것만 고친다), 그 테이블들 중 하나에 `not null` 컬럼이 추가되면 오늘 겪은 것과 **똑같은 전면 시드 실패**가 재발한다.
- **왜 지금 안 고치나:** 대안(`data/listings.json` 103행에 `"view_count": 0` 추가)은 다음 컬럼에서 같은 함정을 또 만난다고 스펙이 판단했다. 나머지 4개 테이블엔 오늘 문제가 **없고**(전부 nullable), 없는 문제를 미리 고치는 것은 A2 위반이다. 시드를 도는 CI 잡 자체가 없어(`tests.yml`은 pytest·vitest·flutter만, `migration-gate.yml`은 `check_migrations.py`만) 자동 검사를 붙이려면 새 잡이 필요하다.
- **트리거:** ① `listings`에 컬럼을 추가하는 **다음 마이그레이션** — 그때 이 목록도 락스텝 갱신 대상이므로 `docs/conventions.md` §4.1 체크리스트에 이 파일을 추가할지 함께 정한다. ② 또는 4개 테이블 중 하나에 `not null` 컬럼을 추가할 때 — 그 자리에서 해당 삽입문도 명시 목록으로 바꾼다.

### DW-447: [구 #147] `view_count`가 무엇을 세는 값인지 어디에도 정의돼 있지 않다 — 실제로는 "웹 상세 **서버 렌더** 횟수"다

origin: 장부 통합 이관(구 docs/tech-debt.md #147) — 원출처: 2026-07-28 Story 11-1 후속리뷰 3차 defer, 🟢 품질
location: `supabase/migrations/0020_listings_view_count.sql`의 `comment on column`("누적 조회수") · `web/src/app/(user)/listings/[id]/page.tsx:38`(`export const dynamic = 'force-dynamic'`) · `docs/conventions.md`(정의 없음).
severity: medium
reason: 이 스토리의 AC는 "상세 진입 시 +1"만 요구하고 표시·라벨은 11.4 몫이다(intent의 Never가 상세 페이지의 조회수 표시 UI를 금지). 정의를 지금 못박아도 소비처가 없어 검증할 대상이 없다.
trigger: Story 11.4에서 이 값을 화면에 노출할 때 — 그 시점에 (a) 컬럼 comment와 `docs/conventions.md`에 정의를 한 줄로 못박고("순 방문자가 아니라 웹 상세 서버 렌더 횟수, 중복제거·봇 필터 없음"), (b) UI 라벨을 그 정의에 맞춘다("조회" vs "방문"). #136과 같은 자리에서 함께 답한다.
status: open

- **위치:** `supabase/migrations/0020_listings_view_count.sql`의 `comment on column`("누적 조회수") · `web/src/app/(user)/listings/[id]/page.tsx:38`(`export const dynamic = 'force-dynamic'`) · `docs/conventions.md`(정의 없음).
- **내용:** 이 라우트는 `force-dynamic`이라 요청마다 서버에서 렌더되고, 렌더될 때마다 RPC가 +1 한다. 그래서 실제 의미는 "몇 명이 봤나"가 아니라 "**서버가 이 페이지를 몇 번 렌더했나**"다 — 새로고침·뒤로가기로 인한 재요청·크롤러 접근이 전부 포함되고, 중복제거도 봇 필터도 없다(intent가 명시적으로 배제). #136이 잡은 왜곡("웹 전용 지표 — Flutter 앱은 안 올린다")보다 **한 단계 앞선 왜곡**이라 별도 항목으로 둔다.
- **왜 지금 안 고치나:** 이 스토리의 AC는 "상세 진입 시 +1"만 요구하고 표시·라벨은 11.4 몫이다(intent의 Never가 상세 페이지의 조회수 표시 UI를 금지). 정의를 지금 못박아도 소비처가 없어 검증할 대상이 없다.
- **트리거:** **Story 11.4에서 이 값을 화면에 노출할 때** — 그 시점에 (a) 컬럼 comment와 `docs/conventions.md`에 정의를 한 줄로 못박고("순 방문자가 아니라 웹 상세 서버 렌더 횟수, 중복제거·봇 필터 없음"), (b) UI 라벨을 그 정의에 맞춘다("조회" vs "방문"). #136과 **같은 자리에서 함께** 답한다 — 둘 다 "이 숫자가 무엇을 뜻하는가"라는 한 질문의 다른 면이다. 정의를 나중에 바꾸면 기존 누적값과 섞여 되돌릴 수 없다.

### DW-450: [구 #150] "내 정보(닉네임 등) 편집 기능 미구현" — `/account`는 읽기 전용

origin: 장부 통합 이관(구 docs/tech-debt.md #150) — 원출처: 2026-07-28 Story 11-2 defer, 🟡 조건부
location: `web/src/app/(user)/account/page.tsx`(신규, 읽기전용) · `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md`(Component Patterns, "내 정보 수정(프로필▾ → 내 정보)": 닉네임 변경 필수·공백/길이 검증·저장/취소·성공 토스트).
severity: high
reason: 편집을 구현하려면 `profiles` UPDATE RLS(`profiles_update_self` 신설) + 컬럼 단위 GRANT 하드닝이 필요하다(Story 11.1의 view_count 쓰기 통로 하드닝과 동형의 별도 마이그레이션 작업). 이 스토리의 intent-contract가 "신규 DB 마이그레이션 없음 — 읽기 전용 표시만 한다"를 Never로 명시했다.
trigger: 향후 "계정 관리" 스토리가 생길 때 — 그 스토리의 인수조건에 (a) 닉네임 검증·저장/취소·토스트, (b) `profiles_update_self` RLS + GRANT 마이그레이션을 명시해서 심는다(B5).
status: open

- **위치:** `web/src/app/(user)/account/page.tsx`(신규, 읽기전용) · `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md`(Component Patterns, "내 정보 수정(프로필▾ → 내 정보)": 닉네임 변경 필수·공백/길이 검증·저장/취소·성공 토스트).
- **내용:** EXPERIENCE.md는 "내 정보" 화면의 편집 동작을 상세히 명세했지만, 이를 구현하는 스토리가 백로그 어디에도 없다(Epic 6~14 전수 확인, spec-11-2 Design Notes). 이번 스토리는 프로필▾ 드롭다운의 "내 정보" 항목이 가리킬 목적지가 없으면 죽은 링크(클릭 시 404)가 되는 문제만 해소하려고, 이메일·역할·이름을 보여주기만 하는 최소 페이지를 만들었다. 편집 폼·저장·검증·토스트는 전부 없다.
- **왜 지금 안 고치나:** 편집을 구현하려면 `profiles` UPDATE RLS(`profiles_update_self` 신설) + 컬럼 단위 GRANT 하드닝이 필요하다(Story 11.1의 view_count 쓰기 통로 하드닝과 동형의 별도 마이그레이션 작업). 이 스토리의 intent-contract가 "신규 DB 마이그레이션 없음 — 읽기 전용 표시만 한다"를 Never로 명시했다.
- **트리거:** 향후 "계정 관리" 스토리가 생길 때 — 그 스토리의 인수조건에 (a) 닉네임 검증·저장/취소·토스트, (b) `profiles_update_self` RLS + GRANT 마이그레이션을 명시해서 심는다(B5 — 회고 약속은 인수조건으로 심어야 이행된다).

### DW-451: [구 #151] `requireUser()`(2차 방어 게이트)가 `redirectedFrom`을 안 실어 보내 `proxy.ts`(1차 게이트)와 로그인 후 복귀 동작이 다르다

origin: 장부 통합 이관(구 docs/tech-debt.md #151) — 원출처: 2026-07-28 Story 11-2 코드리뷰 defer, 🟢 품질
location: `web/src/lib/auth/guard.ts`의 `requireUser()`(`redirect('/login')`, 파라미터 없음) — `/wishlist`·`/ai`·`/search`·`/chat`·`/account` 등 `proxy.ts`가 1차로 보호하는 거의 모든 페이지가 서버 컴포넌트 안에서 이 함수를 2차 방어로 같이 쓴다.
severity: medium
reason: `requireUser()`를 쓰는 호출부 전체(5곳 이상)가 현재 경로를 인자로 넘기도록 시그니처를 바꿔야 해서, 이 스토리의 범위(상단 내비 재구성)를 벗어나는 별도 변경이다.
trigger: `requireUser()`를 다음으로 건드리는 스토리에서 — 시그니처에 `currentPath` 인자를 추가하고 `redirectedFrom`을 실어 보내도록 한 번에 고친다(호출부 전체를 훑어야 하므로 개별 스토리에서 부분 수정하지 않는다).
status: open

- **위치:** `web/src/lib/auth/guard.ts`의 `requireUser()`(`redirect('/login')`, 파라미터 없음) — `/wishlist`·`/ai`·`/search`·`/chat`·`/account` 등 `proxy.ts`가 1차로 보호하는 거의 모든 페이지가 서버 컴포넌트 안에서 이 함수를 2차 방어로 같이 쓴다.
- **내용:** 정상 경로에서는 `proxy.ts`의 `PROTECTED_PREFIXES`가 먼저 걸러 `/login?redirectedFrom=<원래경로>`로 보내 로그인 후 원위치 복귀가 된다. 하지만 1차 게이트가 어떤 이유로든(레이스, 캐시, 신규 보호 경로 추가 누락 등) 안 걸리고 `requireUser()`만 발동하는 드문 경로에서는 그냥 `/login`으로만 보내 로그인 후 홈으로 떨어진다 — 이 스토리(11-2)가 새로 만든 문제가 아니라 기존 `requireUser()` 자체의 설계이고, 이번 코드리뷰가 `/account` 게이트를 보다가 우연히 발견했다.
- **왜 지금 안 고치나:** `requireUser()`를 쓰는 호출부 전체(5곳 이상)가 현재 경로를 인자로 넘기도록 시그니처를 바꿔야 해서, 이 스토리의 범위(상단 내비 재구성)를 벗어나는 별도 변경이다.
- **트리거:** `requireUser()`를 다음으로 건드리는 스토리에서 — 시그니처에 `currentPath` 인자를 추가하고 `redirectedFrom`을 실어 보내도록 한 번에 고친다(호출부 전체를 훑어야 하므로 개별 스토리에서 부분 수정하지 않는다).

### DW-452: [구 #152] 비로그인 홈(`/`)에는 상단 내비가 아예 없다 — Story 11.2가 만든 소비자 내비가 랜딩에서만 안 보인다

origin: 장부 통합 이관(구 docs/tech-debt.md #152) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟡 조건부
location: `web/src/app/page.tsx:178-194`(비로그인 분기, 주석 "비로그인 상태: 로그인/회원가입 링크를 중앙에 (상단바·로그아웃 없음)") — 로그인 분기(`:107`)는 `<AppHeader ... currentPath="/" />`를 렌더하지만 비로그인 분기는 `<main>`만 반환한다.
severity: high
reason: intent-contract의 Never가 `app/page.tsx`를 명시적으로 울타리 쳐서(랜딩 히어로·인기/최신 그리드는 Story 11.3/11.4 몫, 헤더 렌더 호출부만 유지) 손대지 않았다. 비로그인 홈은 Story 11.3(랜딩 히어로)이 통째로 다시 그릴 화면이라, 여기서 헤더만 얹으면 11.3이 곧 덮어쓴다.
trigger: Story 11.3(랜딩 히어로)의 인수조건으로 심는다(B5). "Given 비로그인 사용자가 홈(`/`)을 열면, when 상단을 보면, then 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록이 `/search`와 동일하게 보인다."
status: open

- **위치:** `web/src/app/page.tsx:178-194`(비로그인 분기, 주석 "비로그인 상태: 로그인/회원가입 링크를 중앙에 (상단바·로그아웃 없음)") — 로그인 분기(`:107`)는 `<AppHeader ... currentPath="/" />`를 렌더하지만 비로그인 분기는 `<main>`만 반환한다.
- **내용:** spec-11-2의 AC1은 "비로그인 사용자가 데스크톱에서 **아무 공개 페이지**를 열면 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록이 보인다"인데, 공개 페이지 중 홈(`/`)만 헤더 호출부 자체가 없어 이 AC가 홈에서 미충족이다(실측: `AppHeader` 호출부 10곳 전수 확인, 홈은 로그인 분기에만 있음). `/search`·`/listings/[id]`에서는 정상 노출된다. 즉 비로그인 방문자가 가장 먼저 닿는 화면에서만 신규 내비가 안 보인다.
- **왜 지금 안 고치나:** intent-contract의 Never가 `app/page.tsx`를 명시적으로 울타리 쳤다 — "랜딩 히어로·인기/최신 그리드(Story 11.3/11.4)에 손대지 않는다 … 홈 페이지(`app/page.tsx`)의 본문 콘텐츠는 그대로 둔다(헤더 렌더 호출부만 그대로 유지, 수정 없음)". 비로그인 홈은 Story 11.3(랜딩 히어로)이 통째로 다시 그릴 화면이라, 여기서 헤더만 얹으면 11.3이 곧 덮어쓴다.
- **트리거:** **Story 11.3(랜딩 히어로)의 인수조건으로 심는다**(B5 — 회고 약속은 인수조건으로 심어야 이행된다). 심을 문구: "Given 비로그인 사용자가 홈(`/`)을 열면, when 상단을 보면, then 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록이 `/search`와 동일하게 보인다." 대장에만 적고 11.3 스펙에 안 심으면 조용히 또 밀린다.

### DW-453: [구 #153] 소비자 헤더가 `roleLabel`을 더는 렌더하지 않는데 6개 페이지가 그걸 만들려고 요청마다 `profiles`를 조회한다

origin: 장부 통합 이관(구 docs/tech-debt.md #153) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟢 품질
location: `web/src/components/layout/AppHeader.tsx`의 consumer 분기(`roleLabel` prop을 받기만 하고 어디에도 안 쓴다 — `SiteNav`는 `email`·`currentPath`만 받는다) · 호출부 `web/src/app/(user)/search/page.tsx` · `ai/page.tsx` · `listings/[id]/page.tsx` · `wishlist/page.tsx` · `chat/page.tsx` · `chat/[roomId]/page.tsx`.
severity: medium
reason: intent-contract의 Never가 "8개 기존 `AppHeader` 호출부의 `roleLabel`/`email`/`currentPath` prop 시그니처를 바꾸지 않는다"를 명시했다. 조회를 걷어내려면 호출부를 다 건드려야 해서 이 스토리 범위 밖이다.
trigger: Epic 14(역할 통합)가 실제 `role`을 헤더까지 스레딩할 때 — 그 시점에 `roleLabel`(문자열) 대신 `role`을 넘기도록 한 번에 바꾸고, 소비처 없는 조회를 페이지별로 확인해 함께 제거한다.
status: open

- **위치:** `web/src/components/layout/AppHeader.tsx`의 consumer 분기(`roleLabel` prop을 받기만 하고 어디에도 안 쓴다 — `SiteNav`는 `email`·`currentPath`만 받는다) · 호출부 `web/src/app/(user)/search/page.tsx` · `ai/page.tsx` · `listings/[id]/page.tsx` · `wishlist/page.tsx` · `chat/page.tsx` · `chat/[roomId]/page.tsx`.
- **내용:** 11-2 이전 헤더는 역할라벨·이메일을 화면에 찍었고, 그래서 각 페이지가 `profiles.select('role')`을 돌려 `roleLabel`을 넘겼다. 11-2가 그 표시를 프로필▾ 드롭다운으로 대체하면서 consumer 분기는 `roleLabel`을 버리게 됐는데, 호출부의 조회는 그대로 남았다. 이 라우트들은 전부 `force-dynamic`이라 **요청마다** 쓰이지 않는 DB 왕복이 한 번씩 더 돈다(기능 오류는 없고 지연·부하만 는다). 일부 페이지는 같은 `role`을 다른 용도로도 쓰므로 전수가 죽은 건 아니다 — 페이지별로 실제 소비처를 확인해야 한다.
- **왜 지금 안 고치나:** intent-contract의 Never가 "8개 기존 `AppHeader` 호출부의 `roleLabel`/`email`/`currentPath` prop 시그니처를 바꾸지 않는다"를 명시했다. 조회를 걷어내려면 호출부를 다 건드려야 해서 이 스토리 범위 밖이다.
- **트리거:** **Epic 14(역할 통합)가 실제 `role`을 헤더까지 스레딩할 때** — 그 시점에 `roleLabel`(문자열) 대신 `role`을 넘기도록 한 번에 바꾸고, 소비처 없는 조회를 페이지별로 확인해 함께 제거한다. `nav-links.ts`의 `getConsumerNavLinks(role)`가 그 값을 받을 자리다.

### DW-454: [구 #154] 드롭다운·모달 ARIA 규약(사용자 확정)과 `SiteNav` 구현이 어긋난 채로 남았다

origin: 장부 통합 이관(구 docs/tech-debt.md #154) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟡 조건부
location: `web/src/components/layout/SiteNav.tsx`의 프로필▾ 드롭다운(role 미부착)·햄버거 패널(`role="dialog"` + `aria-modal="true"` + `aria-label`) · 규약 원문은 이 파일 790행("**모달·바텀시트 `role="dialog"` 부착 규약** — 소비 스토리 규약(**사용자 확정**): … `role="dialog"` + `aria-modal="true"` + `aria-labelledby`를 **반드시** 부착한다(UX-DR22 접근성 바닥). 드롭다운·리스트박스는 `menu`/`listbox` role. → **Epic 11**(`11-2-상단-내비-재구성` 드롭다운·필터 바텀시트) 등 소비 에픽에서 적용").
severity: high
reason: 규약대로 되돌리려면 `FocusTrap`에 방향키 탐색을 새로 구현해야 하고, 배경 inert 처리는 별개 메커니즘이다. 둘 다 "내비 재구성" 범위를 넘고, 무엇보다 규약을 지킬지 완화할지가 사용자 판단이라 무인 실행이 임의로 정할 자리가 아니다.
trigger: `FocusTrap`을 손대는 다음 소비 스토리(필터 바텀시트 등) 착수 시 — 그 자리에서 사용자에게 (a) 규약대로 `menu` role + 방향키 탐색을 구현할지, (b) "Tab 순환 popover는 role 미부착"으로 규약을 완화할지 물어 790행 규약 자체를 갱신한다.
status: open

- **위치:** `web/src/components/layout/SiteNav.tsx`의 프로필▾ 드롭다운(role 미부착)·햄버거 패널(`role="dialog"` + `aria-modal="true"` + `aria-label`) · 규약 원문은 이 파일 790행("**모달·바텀시트 `role="dialog"` 부착 규약** — 소비 스토리 규약(**사용자 확정**): … `role="dialog"` + `aria-modal="true"` + `aria-labelledby`를 **반드시** 부착한다(UX-DR22 접근성 바닥). 드롭다운·리스트박스는 `menu`/`listbox` role. → **Epic 11**(`11-2-상단-내비-재구성` 드롭다운·필터 바텀시트) 등 소비 에픽에서 적용").
- **내용:** 세 가지가 규약과 다르다. (a) 프로필▾에 규약이 요구한 `menu` role이 없다 — 11-2의 1차 코드리뷰가 "WAI-ARIA menu 패턴은 방향키·Home/End 탐색을 함의하는데 여기선 Tab 순환만 구현돼 있어 role이 거짓말이 된다"는 이유로 **의도적으로 제거**했다. 기술적으로 틀린 판단은 아니지만, **사용자 확정 규약을 실행 중 리뷰 코멘트가 뒤집은 것**이라 사람의 재확인이 필요하다. 2차 리뷰에서는 최소 정합성만 맞췄다(트리거의 `aria-haspopup`을 `"menu"`→`"true"`로 — role 없이 메뉴 패턴을 약속하던 모순 제거). (b) 햄버거 패널이 `aria-labelledby`가 아니라 `aria-label`을 쓴다. (c) `aria-modal="true"`라고 선언했지만 배경이 실제로 inert가 아니다 — 스크린리더 가상 커서로 뒤 콘텐츠를 계속 읽을 수 있고 body 스크롤도 살아 있다. 키보드 조작(Tab 순환·Esc·포커스 복귀)은 정상 동작함을 실측 확인했으므로 "못 쓰는" 상태는 아니다.
- **왜 지금 안 고치나:** (a)를 규약대로 되돌리려면 `FocusTrap`에 방향키 탐색을 새로 구현해야 하고(공유 컴포넌트 변경), (c)는 배경 inert 처리라는 별개 메커니즘이다. 둘 다 "내비 재구성" 범위를 넘고, 무엇보다 **규약을 지킬지 완화할지가 사용자 판단**이라 무인 실행이 임의로 정할 자리가 아니다.
- **트리거:** **`FocusTrap`을 손대는 다음 소비 스토리(필터 바텀시트 등) 착수 시** — 그 자리에서 사용자에게 (a) 규약대로 `menu` role + 방향키 탐색을 `FocusTrap`에 구현할지, 아니면 (b) "Tab 순환 popover는 role 미부착"으로 규약을 완화할지 물어 **790행 규약 자체를 갱신**한다. 어느 쪽이든 `aria-labelledby`와 배경 inert는 함께 처리한다. 규약과 코드가 갈린 채로 다음 소비처가 생기면 그 소비처도 동전을 던지게 된다(B8).

### DW-455: [구 #155] `/search`가 폭 ≤376px에서 문서 가로 스크롤을 만든다

origin: 장부 통합 이관(구 docs/tech-debt.md #155) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 중 실측 발견, 🟢 품질
location: `web/src/app/(user)/search/page.tsx`의 본문(헤더 아님 — 아래 실측 참조).
severity: medium
reason: 이 스토리(상단 내비 재구성)가 만든 문제가 아니고, 범인을 특정하려면 `/search` 본문 요소를 하나씩 재야 한다 — 내비 스토리의 범위 밖이다.
trigger: `/search` 결과 화면 본문을 손대는 다음 스토리에서 — #84와 같은 자리에서 함께 답한다. 착수 시 320/360px에서 `scrollWidth`를 먼저 재서 범인 요소를 특정하고, `min-w`/`truncate`/열 축소로 흡수한다.
status: open

- **위치:** `web/src/app/(user)/search/page.tsx`의 본문(헤더 아님 — 아래 실측 참조).
- **내용:** 실브라우저 측정(로컬 Supabase + dev 서버, Playwright): `/search`의 `document.documentElement.scrollWidth`가 뷰포트와 무관하게 **376px로 고정**이라 320px에서 +56px, 360px에서 +16px 가로 스크롤이 생긴다(390px 이상은 정상). **로그인/비로그인 수치가 완전히 동일**하고, 같은 측정에서 `header`와 그 안쪽 행의 `scrollWidth`는 모든 폭에서 뷰포트와 정확히 일치했다 — 즉 **11-2가 만든 상단 내비가 원인이 아니라** `/search` 본문(필터 행·결과 그리드 등)에 최소폭 376px를 강제하는 요소가 있다는 뜻이다. D5(반응형 무결성: 레이아웃 어긋남·깨짐 절대 금기) 위반이고, #84(`/ai`가 390px에서 12px 넘침)와 같은 종류의 형제 항목이다.
- **왜 지금 안 고치나:** 이 스토리(상단 내비 재구성)가 만든 문제가 아니고, 범인을 특정하려면 `/search` 본문 요소를 하나씩 재야 한다 — 내비 스토리의 범위 밖이다.
- **트리거:** **`/search` 결과 화면 본문을 손대는 다음 스토리에서** — #84와 **같은 자리에서 함께** 답한다(둘 다 "좁은 폭에서 본문이 안 줄어든다"는 한 문제의 다른 페이지다). 착수 시 320/360px에서 `scrollWidth`를 먼저 재서 범인 요소를 특정하고, `min-w`/`truncate`/열 축소로 흡수한다(D5는 세로 접기를 금지한다).

### DW-456: [구 #156] `docs/conventions.md` §8·`nav-ia-rules.md`의 라우트 목록이 `proxy.ts`보다 늙었다 — `/wishlist`·`/account` 누락

origin: 장부 통합 이관(구 docs/tech-debt.md #156) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟢 품질
location: `docs/conventions.md` §8(접근 게이트 계약, 177·181·187행) · `_bmad-output/planning-artifacts/nav-ia-rules.md:9`(라우트 인벤토리) · 실제 정본이 돼버린 `web/src/proxy.ts:15-30`(주석 + `PROTECTED_PREFIXES`).
severity: medium
reason: 이 스토리가 새로 만든 드리프트가 아니고(선례가 이미 있음), 계약 문서 §8을 고치는 것은 값의 정본을 건드리는 일이라 내비 스토리가 곁다리로 처리할 자리가 아니다.
trigger: 다음으로 `PROTECTED_PREFIXES`에 경로를 추가하는 스토리에서 — 그 스토리의 인수조건에 §8 목록과 `nav-ia-rules.md` 인벤토리를 같은 커밋에서 함께 갱신한다는 조항을 심고, 밀린 `/wishlist`·`/account`도 함께 올린다.
status: open

- **위치:** `docs/conventions.md` §8(접근 게이트 계약, 177·181·187행) · `_bmad-output/planning-artifacts/nav-ia-rules.md:9`(라우트 인벤토리) · 실제 정본이 돼버린 `web/src/proxy.ts:15-30`(주석 + `PROTECTED_PREFIXES`).
- **내용:** `proxy.ts`는 자기 주석에서 §8을 "계약 원문"이라 가리키는데, 정작 §8은 `/wishlist`를 경로 형태로 안 적고(같은 문장에서 `/ai`·`/sell`·`/chat`은 전부 백틱 경로로 적으면서 찜만 "찜(Epic 10.5)"이라는 기능명), `/account`는 아예 한 글자도 없다(파일 전체 grep 0건). `nav-ia-rules.md:9`의 인벤토리는 2026-06-24 작성분 그대로라 `/wishlist`·`/account` 둘 다 없다. **이 드리프트는 `/account`가 처음이 아니라 `/wishlist`(Story 10.5)부터 이미 있었다** — 즉 "보호 경로를 추가하면서 상위 계약 문서를 같이 안 고친다"는 반복 실패 모드이고, `/account`는 두 번째 사례다. B8("상위 문서의 제약은 하위로 흘린다")이 역방향으로 깨진 상태다.
- **왜 지금 안 고치나:** 이 스토리가 새로 만든 드리프트가 아니고(선례가 이미 있음), 계약 문서 §8을 고치는 것은 값의 정본을 건드리는 일이라 내비 스토리가 곁다리로 처리할 자리가 아니다.
- **트리거:** **다음으로 `PROTECTED_PREFIXES`에 경로를 추가하는 스토리에서** — 그 스토리의 인수조건에 "§8의 경로 목록과 `nav-ia-rules.md` 인벤토리를 같은 커밋에서 함께 갱신한다"를 심고(B5), 그때 밀린 `/wishlist`·`/account`도 함께 올린다. 더 확실한 방법은 `PROTECTED_PREFIXES`와 §8 목록이 어긋나면 실패하는 소스 스캔 검사를 두는 것이다(B9 — 문서는 계약이 아니다).

### DW-457: [구 #157] `FocusTrap`이 **바깥 클릭**으로 닫힐 때도 트리거로 포커스를 되돌려(`preventScroll` 없음) 스크롤이 위로 튄다

origin: 장부 통합 이관(구 docs/tech-debt.md #157) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟢 품질
location: `web/src/components/ui/FocusTrap.tsx`의 언마운트 cleanup(`triggerRef.current?.focus();` — 옵션 없는 평범한 `focus()`) · 이 동작을 처음 마주치는 소비처가 `web/src/components/layout/SiteNav.tsx`의 outside-click 닫기(`mousedown` 핸들러 2개).
severity: medium
reason: `FocusTrap`은 여러 화면이 공유하는 컴포넌트라, "어떻게 닫혔는지"를 구분해 복귀 여부를 정하는 시그니처 변경이 필요하다 — 기존 모든 소비처의 포커스 동작에 영향을 준다. 내비 스토리 범위 밖이다.
trigger: `FocusTrap`을 다음으로 손대는 스토리에서 #36과 함께 — 닫힘 사유를 인자로 받아 (a) Esc·트리거 닫힘에만 복귀하고, (b) 복귀 시에도 `focus({ preventScroll: true })`를 쓰도록 한 번에 고친다.
status: open

- **위치:** `web/src/components/ui/FocusTrap.tsx`의 언마운트 cleanup(`triggerRef.current?.focus();` — 옵션 없는 평범한 `focus()`) · 이 동작을 처음 마주치는 소비처가 `web/src/components/layout/SiteNav.tsx`의 outside-click 닫기(`mousedown` 핸들러 2개).
- **내용:** `FocusTrap`은 열릴 때 `document.activeElement`를 트리거로 기억해 두고, 닫힐 때 무조건 그리로 포커스를 되돌린다. Esc·트리거 재클릭으로 닫을 때는 옳은 동작이다. 그런데 11-2가 추가한 **바깥 클릭 닫기**에서는 사용자가 이미 다른 곳을 누르고 있는데도 포커스가 헤더의 트리거로 끌려간다 — 헤더는 sticky가 아니라서 페이지를 내린 상태였다면 브라우저가 트리거를 화면에 넣으려고 **위로 스크롤**한다(`preventScroll: true`가 없다). 결과적으로 클릭 직후 화면이 튀고, 다음 Tab이 카드가 아니라 내비에서 다시 시작한다. 이 스토리가 `FocusTrap`의 첫 outside-click 소비처라 새로 드러났을 뿐, 원인은 `FocusTrap` 자체 설계다(#36과 같은 자리).
- **왜 지금 안 고치나:** `FocusTrap`은 여러 화면이 공유하는 컴포넌트라, "어떻게 닫혔는지"(Esc/트리거/바깥클릭)를 구분해 복귀 여부를 정하는 시그니처 변경이 필요하다 — 기존 모든 소비처의 포커스 동작에 영향을 준다. 내비 스토리 범위 밖이다.
- **트리거:** **`FocusTrap`을 다음으로 손대는 스토리에서 #36과 함께** — 닫힘 사유를 인자로 받아 (a) Esc·트리거 닫힘에만 복귀하고, (b) 복귀 시에도 `focus({ preventScroll: true })`를 쓰도록 한 번에 고친다. 소비처 전체를 훑어야 하므로 개별 스토리에서 부분 수정하지 않는다(#154와 같은 자리에서 처리하면 `FocusTrap`을 한 번만 연다).

### DW-458: [구 #158] `<Logo>` 배선(#125)의 트리거가 Story 11-2에서 소진됐는데 #125가 안 닫혔고, #125가 요구한 "800 weight 실경로 확인"도 미이행

origin: 장부 통합 이관(구 docs/tech-debt.md #158) — 원출처: 2026-07-28 Story 11-2 2차 코드리뷰 defer, 🟢 품질
location: 이 파일 #125(1539-1544행, "해소: 미해소(위 트리거에서 처리)") · 실제 배선은 `web/src/components/layout/AppHeader.tsx`의 consumer 분기(`<Link href="/" aria-label="홈으로 이동"><Logo size="sm" /></Link>`).
severity: medium
reason: 이번 실행(bmad-dev-auto 후속리뷰)은 기존 대장 항목의 status·해소를 수정하지 말라는 지시 아래 돌아, #125를 직접 닫지 않고 이 신규 항목으로만 남겼다. 실체(배선)는 이미 코드에 있으므로 남은 것은 장부 정리 + 800 weight 실측 1회뿐이다.
trigger: 다음 대장 점검 또는 Story 11.3 착수 시(둘 중 먼저 오는 쪽) — 헤더 로고의 `getComputedStyle(...).fontWeight`가 800로 나오는지 실측하고, 그 결과와 함께 #125를 닫는다.
status: open

- **위치:** 이 파일 #125(1539-1544행, "해소: 미해소(위 트리거에서 처리)") · 실제 배선은 `web/src/components/layout/AppHeader.tsx`의 consumer 분기(`<Link href="/" aria-label="홈으로 이동"><Logo size="sm" /></Link>`).
- **내용:** #125의 트리거는 "Epic 11의 헤더·브랜딩을 손대는 스토리(11.3 히어로 또는 **내비 재구성**) — 그때 `<Logo>`를 실제 배선하거나, 안 쓸 거면 컴포넌트를 정리한다. **어느 쪽이든 그 시점에 800 weight 렌더를 실경로로 한 번 확인한다**"였다. Story 11-2가 바로 그 "내비 재구성"이고 `<Logo>`를 실제로 배선했으므로 트리거는 소진됐다. 그런데 (a) #125는 여전히 "해소: 미해소"이고 상단 요약행에도 열린 것으로 남아 있으며, (b) 요구된 800 weight 렌더 실측 확인은 어디에도 기록이 없다. B8("일을 끝내면 대장을 닫는다 — 안 닫으면 '안 한 것'과 '했는지 모르는 것'이 구별되지 않고, 후자가 더 비싸다")이 트리거를 소진한 바로 그 스토리에서 깨졌다.
- **왜 지금 안 고치나:** 이번 실행(bmad-dev-auto 후속 리뷰)은 **기존 대장 항목의 status·해소를 수정하지 말라는 지시** 아래 돌았다(항목의 상태·종결은 오케스트레이터 소관). 그래서 #125를 직접 닫지 않고 이 신규 항목으로만 남긴다. 실체(배선)는 이미 코드에 있으므로 남은 것은 **장부 정리 + 800 weight 실측 1회**뿐이다.
- **트리거:** **다음 대장 점검 또는 Story 11.3 착수 시(둘 중 먼저 오는 쪽)** — 그때 (a) 실브라우저에서 헤더 로고의 `getComputedStyle(...).fontWeight`가 800로 나오는지 한 번 재고, (b) 그 결과와 함께 #125를 "해소: Story 11-2에서 `AppHeader` consumer 분기에 배선"으로 닫는다. 재보기 전에 닫지 않는다(B4 — 존재 확인은 작동 확인이 아니다).

### DW-459: [구 #159] 구매자·관리자에게도 "내 차 팔기"·"내 매물 관리"가 1급 내비로 뜨고, 누르면 말없이 홈으로 튕긴다

origin: 장부 통합 이관(구 docs/tech-debt.md #159) — 원출처: 2026-07-28 Story 11-2 3차 코드리뷰 defer, 🟡 조건부
location: `web/src/components/layout/nav-links.ts`의 `getConsumerNavLinks(role)`(role을 `void role`로 버리고 항상 같은 3개 반환) · 호출부 `web/src/components/layout/SiteNav.tsx`(`getConsumerNavLinks(null)` 고정) · 착지점 `web/src/app/(user)/sell/layout.tsx`의 `requireRole('seller')` → `redirect('/')`.
severity: high
reason: 이 스토리 intent-contract의 Never가 `requireRole('seller')` 동작 변경을 명시적으로 금지했고, 인수조건 하나가 그 리다이렉트를 "회귀 아님"으로 직접 검증한다. 현행 동작은 이 스토리가 만든 것이 아니라 승계한 것이다.
trigger: Epic 14(역할 통합)가 실제 `role`을 헤더까지 스레딩할 때 — #153과 같은 자리에서 함께 답한다. 그 시점에 (a) `role`을 받게 하고, (b) `/sell` 항목을 빼거나 (c) 안내 화면으로 보내는 것 중 사용자에게 물어 정한다.
status: open

- **위치:** `web/src/components/layout/nav-links.ts`의 `getConsumerNavLinks(role)`(role을 `void role`로 버리고 항상 같은 3개 반환) · 호출부 `web/src/components/layout/SiteNav.tsx`(`getConsumerNavLinks(null)` 고정) · 착지점 `web/src/app/(user)/sell/layout.tsx`의 `requireRole('seller')` → `redirect('/')`.
- **내용:** `/sell`로 가는 진입점이 헤더에 **세 개**다 — 가운데 내비 "내 차 팔기", 프로필▾ "내 매물 관리", 비로그인 우측 "내 차 등록". 판매자가 아닌 로그인 사용자(buyer·admin)가 어느 것을 눌러도 `requireRole('seller')`가 **아무 안내 없이** 홈으로 되돌린다. 화면상 아무 일도 안 일어난 것처럼 보이는 막다른 길이다. `nav-ia-rules.md` §2는 "내 매물 등록·관리"를 **판매자 전용** 항목으로 못박고 있어 IA 계약과도 어긋난다. `getConsumerNavLinks`는 정확히 이 분기를 위해 만들어진 확장 지점인데 실제 role이 헤더까지 흐르지 않아 `null`로 고정돼 있다(#153이 기록한 "`roleLabel` 문자열만 넘기고 `role`은 안 넘긴다"의 뒷면).
- **왜 지금 안 고치나:** 이 스토리 intent-contract의 Never가 `requireRole('seller')` 동작 변경을 명시적으로 금지했고("buyer가 `/sell` 진입 시 홈으로 리다이렉트되는 기존 동작은 이 스토리 범위 밖 — Epic 14 역할 통합이 다룬다"), 인수조건 하나가 그 리다이렉트를 **"회귀 아님"으로 직접 검증**한다. 즉 현행 동작은 이 스토리가 만든 것이 아니라 승계한 것이다.
- **트리거:** **Epic 14(역할 통합)가 실제 `role`을 헤더까지 스레딩할 때 — #153과 같은 자리에서 함께 답한다.** 그 시점에 (a) `AppHeader`가 `roleLabel`(문자열) 대신 `role`을 받게 하고, (b) `getConsumerNavLinks(role)`가 판매자가 아닌 사용자에게 `/sell` 항목을 빼거나, (c) 빼지 않기로 한다면 `/sell` 착지 시 "판매자 등록이 필요합니다" 안내 화면으로 보낸다(무언 리다이렉트를 없애는 쪽이 핵심이다). 셋 중 무엇을 택할지는 그때 사용자에게 묻는다 — IA 규칙(§2)과 "시도 전에 거절하지 않는다"(11.3 AC 개정 원칙)가 서로 다른 답을 가리키기 때문이다.

### DW-461: [구 #161] 관리자 헤더는 "중고차 직거래", 소비자 헤더는 "차장님" — 같은 앱의 서비스명이 갈렸다

origin: 장부 통합 이관(구 docs/tech-debt.md #161) — 원출처: 2026-07-28 Story 11-2 3차 코드리뷰 defer, 🟢 품질
location: `web/src/components/layout/AppHeader.tsx`의 admin 분기(하드코딩 문자열 `중고차 직거래`) vs consumer 분기(`<Logo size="sm" />` → `web/src/components/ui/Logo.tsx`가 "차" 배지 + "차장님" 워드마크를 렌더).
severity: medium
reason: intent-contract의 Always가 "관리자 페이지는 기존 최소 헤더를 그대로 유지한다"를 명시했다. 브랜드 문자열만 바꾸는 것이 그 제약을 어기는지 아닌지가 애매하고, 무인 실행이 임의로 정할 자리가 아니다.
trigger: 관리자 화면(`(admin)` 레이아웃·콘솔)을 손대는 다음 스토리 착수 시 — admin 헤더의 하드코딩 문자열을 `<Logo size="sm" />`로 바꾸거나, 최소한 서비스명 문자열을 `lib/constants.ts` 한 곳에서 가져오게 한다.
status: open

- **위치:** `web/src/components/layout/AppHeader.tsx`의 admin 분기(하드코딩 문자열 `중고차 직거래`) vs consumer 분기(`<Logo size="sm" />` → `web/src/components/ui/Logo.tsx`가 "차" 배지 + "차장님" 워드마크를 렌더).
- **내용:** Story 11-2가 consumer 헤더에 `<Logo>`를 배선하면서 소비자 화면의 서비스명이 "차장님"(UX-DR9/D7 확정 브랜드)으로 바뀌었다. admin 분기는 "기존 최소 헤더를 그대로 유지"하라는 intent에 따라 손대지 않았고, 그 결과 **관리자가 보는 서비스명만 옛 임시 문자열로 남았다.** 기능 결함은 없지만, 같은 제품에서 역할에 따라 브랜드명이 다르게 보인다. intent가 admin 헤더를 동결한 의도가 "브랜드명까지 동결"이었는지는 스펙 어디에도 없다 — 판단이 갈린 적 없이 그냥 범위 밖이었다.
- **왜 지금 안 고치나:** intent-contract의 Always가 "관리자 페이지는 기존 최소 헤더를 그대로 유지한다"를 명시했다. 브랜드 문자열만 바꾸는 것이 그 제약을 어기는지 아닌지가 애매하고, 무인 실행이 임의로 정할 자리가 아니다.
- **트리거:** **관리자 화면(`(admin)` 레이아웃·콘솔)을 손대는 다음 스토리 착수 시** — 그 자리에서 admin 헤더의 하드코딩 문자열을 `<Logo size="sm" />`로 바꾸거나(권장 — 브랜드 정본을 한 컴포넌트로 모음), 최소한 서비스명 문자열을 `lib/constants.ts` 한 곳에서 가져오게 한다. 지금처럼 두 곳에 각각 적혀 있으면 다음 브랜드 변경 때 한쪽만 늙는다.

### DW-462: [구 #162] 새 내비에 "지금 어디에 있는지" 표시가 없다 — `currentPath`가 들어와 있는데 로그인 링크에만 쓴다

origin: 장부 통합 이관(구 docs/tech-debt.md #162) — 원출처: 2026-07-28 Story 11-2 3차 코드리뷰 defer, 🟢 품질
location: `web/src/components/layout/SiteNav.tsx` — `currentPath` prop을 받아 `loginHref`의 `redirectedFrom` 조립에만 쓰고, 내비 링크(`navLinks.map`)에는 `aria-current="page"`도 활성 스타일도 붙이지 않는다.
severity: medium
reason: intent-contract의 I/O 매트릭스가 현재 위치 표시를 요구하지 않았고, 활성 상태를 어떻게 보이게 할지는 디자인 결정이라 무인 실행이 임의로 정하면 UX 문서와 어긋날 수 있다.
trigger: Story 11.3/11.4가 랜딩 내비를 손볼 때 — UX 문서(`EXPERIENCE.md`·`DESIGN.md`)의 활성 상태 토큰을 확인해 `aria-current="page"` + 시각 표시를 함께 넣는다.
status: open

- **위치:** `web/src/components/layout/SiteNav.tsx` — `currentPath` prop을 받아 `loginHref`의 `redirectedFrom` 조립에만 쓰고, 내비 링크(`navLinks.map`)에는 `aria-current="page"`도 활성 스타일도 붙이지 않는다.
- **내용:** "내 차 사기·AI로 찾기·내 차 팔기"가 1급 진입점이 됐는데, `/search`에 있든 `/ai`에 있든 세 링크가 똑같이 보인다. 스크린리더 사용자에겐 현재 위치 정보가 아예 없고(`aria-current` 부재), 눈으로 보는 사용자에겐 시각적 활성 표시가 없다. 필요한 데이터(`currentPath`)는 **이미 컴포넌트 안까지 들어와 있다** — 배선만 안 됐다.
- **왜 지금 안 고치나:** intent-contract의 I/O 매트릭스가 현재 위치 표시를 요구하지 않았고, 활성 상태를 **어떻게 보이게 할지**(밑줄·색·굵기)는 디자인 결정이라 무인 실행이 임의로 정하면 UX 문서와 어긋날 수 있다. `aria-current`만 붙이고 시각 표시를 빼면 보조기술과 눈에 보이는 화면이 서로 다른 말을 하게 된다.
- **트리거:** **Story 11.3/11.4가 랜딩 내비를 손볼 때** — 그 자리에서 UX 문서(`EXPERIENCE.md`·`DESIGN.md`)의 활성 상태 토큰을 확인해 `aria-current="page"` + 시각 표시를 **함께** 넣는다. 둘 중 하나만 넣지 않는다.

### DW-463: [구 #163] 로그인 여부를 `email` 유무로만 판별한다 — 이메일 없는 계정은 로그인해도 익명 내비를 본다

origin: 장부 통합 이관(구 docs/tech-debt.md #163) — 원출처: 2026-07-28 Story 11-2 3차 코드리뷰 defer, 🟢 품질
location: `web/src/components/layout/SiteNav.tsx`의 `email ? (찜·채팅·프로필▾) : (로그인·내 차 등록)` 분기 · 값의 출처는 각 페이지의 `user.email`(Supabase `User.email`은 타입상 `string | undefined`).
severity: medium
reason: 고치려면 `AppHeader`가 `email` 대신(또는 추가로) 명시적인 로그인 여부 boolean을 받아야 하고, 그건 intent-contract의 Never가 동결한 "8개 기존 호출부의 prop 시그니처"를 건드리는 일이다.
trigger: 이메일 외 로그인 수단(소셜 로그인·전화번호 인증 등)을 도입하는 스토리 착수 시 — `AppHeader`/`SiteNav`가 `isAuthenticated` 같은 명시적 신호를 받도록 바꾼다. #159(role 스레딩)와 같은 시그니처 변경 한 번에 처리하는 것이 싸다.
status: open

- **위치:** `web/src/components/layout/SiteNav.tsx`의 `email ? (찜·채팅·프로필▾) : (로그인·내 차 등록)` 분기 · 값의 출처는 각 페이지의 `user.email`(Supabase `User.email`은 타입상 `string | undefined`).
- **내용:** 로그인 사용자에게만 주는 모든 진입점(찜·채팅·프로필▾, 따라서 **로그아웃까지**)이 `email` 문자열 하나에 매달려 있다. 이메일 없는 계정이 존재하면 그 사용자는 인증돼 있는데도 "로그인·내 차 등록"만 보이고 로그아웃할 방법이 화면에 없다. **지금은 도달 불가다** — 이 프로젝트의 가입은 이메일+비밀번호뿐이라 `email`은 항상 채워진다(그래서 🟢). 다만 "로그인했나"라는 질문에 이메일 문자열로 답하는 구조 자체가 취약하다.
- **왜 지금 안 고치나:** 고치려면 `AppHeader`가 `email` 대신(또는 추가로) 명시적인 로그인 여부 boolean을 받아야 하고, 그건 intent-contract의 Never가 동결한 "8개 기존 호출부의 prop 시그니처"를 건드리는 일이다.
- **트리거:** **이메일 외 로그인 수단(소셜 로그인·전화번호 인증 등)을 도입하는 스토리 착수 시** — 그 스토리에서 `AppHeader`/`SiteNav`가 `isAuthenticated` 같은 명시적 신호를 받도록 바꾼다. #159(role 스레딩)와 **같은 시그니처 변경 한 번에** 처리하는 것이 싸다.

### DW-465: [구 #165] 히어로 검색의 로그인 분기·핸드오프 소비 로직에 자동 회귀검사가 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #165) — 원출처: 2026-07-28 Story 11-3 코드리뷰 defer, 🟡 조건부
location: `web/src/components/landing/HeroSearch.tsx`(마운트 시 핸드오프 복원 effect, `submit()`의 로그인 분기) · `web/src/components/ai/ChatAssistant.tsx`(마운트 시 핸드오프 소비 + 1회 자동실행 effect).
severity: high
reason: `useEffect`는 SSR/`renderToStaticMarkup`에서 실행되지 않으므로(11-2가 `SiteNav.test.ts`에서 이미 문서화한 동일 한계) jsdom+React Testing Library 없이는 이 로직에 못 닿는다. 이 리포의 vitest 설정(`environment:'node'`, `.test.ts`만 포함, `.tsx` 제외)은 순수 함수만 단위테스트하고 나머지는 E2E로 미루는 프로젝트 관례(`vitest.config.ts` 주석)를 그대로 지킨 것이라, jsdom/RTL 도입이나 Playwright 스위트 신설은 "히어로+차종칩" 스토리 범위를 넘는 인프라 투자다.
trigger: **`#160`(11-2가 이미 심어 둔, `SiteNav`의 상호작용에 자동 회귀검사가 없다는 항목)과 같은 E2E 층을 세우는 Story 11.5(반응형 뷰포트 E2E 감사) 착수 시** — 그 자리에서 로그인 분기(게이트 vs 즉시실행)·마운트 시 핸드오프 복원(자동실행 없음)·`/ai` 자동실행 1회·새로고침 재실행 안 됨, 4가지를 함께 고정한다. `#160`과 같은 E2E 층이 필요한 이유가 같다(effect 기반 로직은 구조적으로 E2E 몫).
status: open

- **위치:** `web/src/components/landing/HeroSearch.tsx`(마운트 시 핸드오프 복원 effect, `submit()`의 로그인 분기) · `web/src/components/ai/ChatAssistant.tsx`(마운트 시 핸드오프 소비 + 1회 자동실행 effect).
- **내용:** 11-3 코드리뷰 3개 레이어(adversarial·edge-case-hunter·verification-gap)가 독립적으로 같은 지점을 짚었다 — `authed` 분기로 `/ai` 자동실행 vs 로그인 게이트를 가르고, "재실행 방지"(새로고침 시 재과금 금지)를 보장하는 이 로직 전체가 `useEffect`/이벤트 핸들러 안에 있어 순수함수 단위테스트로 못 잡는다. `heroSearchHandoff.test.ts`는 저장소 자체(읽고-쓰고-지우는 함수)만 잠갔을 뿐, "누가 이 값을 소비하는가"를 가르는 이 두 컴포넌트의 분기 로직은 테스트가 0건이다. `web/src/**/*.test.*` 전수 검색 결과 `HeroSearch`·`ChatAssistant`를 마운트/렌더하는 테스트가 없고, 이 리포에는 아직 커밋된 Playwright E2E 스위트 자체가 없다(로컬 MCP 세션으로 수동 확인하는 것이 현재 유일한 검증 수단, 11-3 구현 시 실제로 그렇게 수행함).
- **왜 지금 안 고치나:** `useEffect`는 SSR/`renderToStaticMarkup`에서 실행되지 않으므로(11-2가 `SiteNav.test.ts`에서 이미 문서화한 동일 한계) jsdom+React Testing Library 없이는 이 로직에 못 닿는다. 이 리포의 vitest 설정(`environment:'node'`, `.test.ts`만 포함, `.tsx` 제외)은 순수 함수만 단위테스트하고 나머지는 E2E로 미루는 프로젝트 관례(`vitest.config.ts` 주석)를 그대로 지킨 것이라, jsdom/RTL 도입이나 Playwright 스위트 신설은 "히어로+차종칩" 스토리 범위를 넘는 인프라 투자다.
- **트리거:** **`#160`(11-2가 이미 심어 둔, `SiteNav`의 상호작용에 자동 회귀검사가 없다는 항목)과 같은 E2E 층을 세우는 Story 11.5(반응형 뷰포트 E2E 감사) 착수 시** — 그 자리에서 로그인 분기(게이트 vs 즉시실행)·마운트 시 핸드오프 복원(자동실행 없음)·`/ai` 자동실행 1회·새로고침 재실행 안 됨, 4가지를 함께 고정한다. `#160`과 같은 E2E 층이 필요한 이유가 같다(effect 기반 로직은 구조적으로 E2E 몫).

### DW-466: [구 #166] 인기/최신 그리드의 빈 상태·단별 조회 실패·동률 tie-break·양단 중복 노출 4가지가 자동 검사 0건이다

origin: 장부 통합 이관(구 docs/tech-debt.md #166) — 원출처: 2026-07-28 Story 11-4 구현 시 Matrix Test Audit 지적, 🟡 조건부
location: `web/src/components/landing/PopularRecentGrid.tsx`(`ListingGridSection`의 `'error' in section`/`length === 0` 분기) · `web/src/lib/listings.ts`(`fetchSection`의 단별 독립 실패 처리, `.order('view_count'|'created_at', …).order('id', …)` tie-break).
severity: high
reason: ①·②는 `#165`·`#160`과 같은 이유로 jsdom/RTL 도입이 필요한 인프라 투자다. ③·④는 로컬 스택에 전용 시드 데이터(동률 view_count 쌍, 인기이면서 최신인 매물)를 별도로 준비해야 안전하게 재현되는데, 이 스토리 범위(그리드 자체 구현)를 넘는 시드 작업이다.
trigger: Story 11.5(반응형 뷰포트 E2E 감사) 착수 시 — 그 자리가 이미 `#160`·`#165`로 effect/DOM 기반 로직의 E2E 계약을 세우기로 예정돼 있으므로, 랜딩 그리드의 빈 상태·단별 실패 격리 2가지를 같은 층에서 함께 고정한다. tie-break·중복 노출 2가지는 그 E2E 착수 시 전용 시드 데이터(동률 view_count 쌍 포함)를 함께 준비해 커버한다.
status: open

- **위치:** `web/src/components/landing/PopularRecentGrid.tsx`(`ListingGridSection`의 `'error' in section`/`length === 0` 분기) · `web/src/lib/listings.ts`(`fetchSection`의 단별 독립 실패 처리, `.order('view_count'|'created_at', …).order('id', …)` tie-break).
- **내용:** spec-11-4의 I/O & Edge-Case Matrix 6행 중 2행(비로그인·로그인 매물 존재)은 `normalizeAnonTrustColumns` 단위테스트 + 로컬 Supabase Playwright MCP 수동 확인으로 커버됐지만, 나머지 4행 — ① on_sale 매물 0건(빈 상태 문구), ② 인기 단만 조회 실패(다른 단은 정상 렌더), ③ view_count 동률 시 id desc tie-break로 결정적 순서, ④ 인기·최신 양단에 같은 매물이 중복 노출되는 것(허용된 동작) — 은 자동 검사도 수동 확인도 받지 못했다. ①·②는 JSX 조건부 렌더라 이 리포의 순수함수 전용 vitest(`environment:'node'`, `.tsx` 제외)로 못 닿고(`#165`와 동일 한계), ③·④는 실제 Supabase 쿼리 체인·데이터 상태가 필요해 로컬 DB에 동률/중복 데이터를 인위로 심어야 하는데 공유 개발 DB를 훼손할 위험이 있어 이번 구현·검증 패스에서 보류했다. **코드리뷰 추가 확인(adversarial 지적):** ①·②의 미검증 범위는 JSX 렌더뿐 아니라 그 렌더가 참조하는 `fetchSection`의 `{error:true}` 반환 로직 자체(쿼리 실패 시 분기)에도 그대로 적용된다 — Supabase client를 mock한 단위테스트가 없어 이 분기가 리팩터로 조용히 깨져도 vitest는 계속 초록이다. jsdom/RTL 없이도 mock 가능한 부분이라 원칙적으론 분리해 고칠 수 있지만, 이 스토리에서 함께 보류하고 같은 트리거로 이관한다(범위를 넓히면 A2 위반).
- **왜 지금 안 고치나:** ①·②는 `#165`·`#160`과 같은 이유로 jsdom/RTL 도입이 필요한 인프라 투자다. ③·④는 로컬 스택에 전용 시드 데이터(동률 view_count 쌍, 인기이면서 최신인 매물)를 별도로 준비해야 안전하게 재현되는데, 이 스토리 범위(그리드 자체 구현)를 넘는 시드 작업이다.
- **트리거:** Story 11.5(반응형 뷰포트 E2E 감사) 착수 시 — 그 자리가 이미 `#160`·`#165`로 effect/DOM 기반 로직의 E2E 계약을 세우기로 예정돼 있으므로, 랜딩 그리드의 빈 상태·단별 실패 격리 2가지를 같은 층에서 함께 고정한다. tie-break·중복 노출 2가지는 그 E2E 착수 시 전용 시드 데이터(동률 view_count 쌍 포함)를 함께 준비해 커버한다.

### DW-467: [구 #167] 마이그레이션 게이트가 `anon`의 `view_count` SELECT 권한(#134 해소분)을 구체적으로 확인하지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #167) — 원출처: 2026-07-28 Story 11-4 코드리뷰 defer, 🟡 조건부
location: `scripts/check_migrations.py`의 anon 컬럼 권한 프로브(`#134`·`#144` 관련 코드리뷰가 실측) · `supabase/migrations/0021_listings_view_count_anon_grant.sql`의 `grant select (view_count) on public.listings to anon;`.
severity: high
reason: `check_migrations.py`는 여러 스토리가 공유하는 게이트 인프라라, 이번 스토리 범위에서 손대면 그 파일을 소유한 다른 검사들에까지 영향이 번질 수 있다(A3). `embedding` 차단을 확인하는 기존 프로브와 대칭되는 `view_count` 전용 프로브를 추가하는 형태가 유력하지만, 게이트 구조 자체를 손대는 결정은 이 스토리(그리드 구현)의 권한 밖이다.
trigger: 게이트 구조를 정비하는 다음 작업(`#143`이 이미 예약한 Epic 13 게이트 정비와 같은 축) 또는 Story 11.5(E2E 감사) 착수 시 — 어느 쪽이든 `embedding`(차단, `'f'` 기대)과 대칭되는 `view_count`(허용, `'t'` 기대) 프로브를 `check_migrations.py`의 PROBES에 추가하거나, anon 역할로 `fetchPopularAndRecentListings(supabase, null)`을 실제 로컬 스택에 돌려 `popular`가 `{error:true}`가 아님을 단언하는 통합 테스트를 신설한다.
status: open

- **위치:** `scripts/check_migrations.py`의 anon 컬럼 권한 프로브(`#134`·`#144` 관련 코드리뷰가 실측) · `supabase/migrations/0021_listings_view_count_anon_grant.sql`의 `grant select (view_count) on public.listings to anon;`.
- **내용:** verification-gap·adversarial 두 레이어가 독립적으로 같은 지점을 짚었다 — 이 게이트의 anon 컬럼 권한 프로브는 "anon이 `listings`의 아무 컬럼이나 하나라도 SELECT할 수 있는가"만 확인하는 범용 검사다. `0011`이 이미 `created_at`·`id` 등 여러 컬럼을 anon에게 열어뒀으므로, 이 프로브는 `view_count` 권한의 유무와 무관하게 항상 통과(`'t'`)한다. 즉 `0021`의 `grant select (view_count) ...`이 다음 마이그레이션에서 실수로 되돌려져도(예: 컬럼 권한을 재구성하는 리팩터가 이 줄을 빠뜨림), 이 게이트도 vitest(`normalizeAnonTrustColumns`만 순수 함수 검증, 실제 DB 왕복은 범위 밖)도 그 회귀를 못 잡는다. 소비 지점은 `web/src/app/page.tsx`의 비로그인 분기 → `fetchSection(authed=false, orderColumn='view_count')` — 권한이 없으면 42501로 `{error:true}`가 되어 "지금 인기" 단이 조용히 에러 문구로 렌더된다. `authenticated`는 테이블 SELECT를 그대로 가지고 있어 영향받지 않는 비대칭이라(`#134`가 이미 경고한 것과 동일한 함정), 로그인 상태로만 확인하면 이 회귀를 절대 못 본다.
- **왜 지금 안 고치나:** `check_migrations.py`는 여러 스토리가 공유하는 게이트 인프라라, 이번 스토리 범위에서 손대면 그 파일을 소유한 다른 검사들에까지 영향이 번질 수 있다(A3). `embedding` 차단을 확인하는 기존 프로브와 대칭되는 `view_count` 전용 프로브를 추가하는 형태가 유력하지만, 게이트 구조 자체를 손대는 결정은 이 스토리(그리드 구현)의 권한 밖이다.
- **트리거:** 게이트 구조를 정비하는 다음 작업(`#143`이 이미 예약한 Epic 13 게이트 정비와 같은 축) 또는 Story 11.5(E2E 감사) 착수 시 — 어느 쪽이든 `embedding`(차단, `'f'` 기대)과 대칭되는 `view_count`(허용, `'t'` 기대) 프로브를 `check_migrations.py`의 PROBES에 추가하거나, anon 역할로 `fetchPopularAndRecentListings(supabase, null)`을 실제 로컬 스택에 돌려 `popular`가 `{error:true}`가 아님을 단언하는 통합 테스트를 신설한다.

### DW-468: [구 #168] CI에 e2e job이 배선돼 있지 않다 — Playwright는 로컬 전용이다

origin: 장부 통합 이관(구 docs/tech-debt.md #168) — 원출처: 2026-07-28 Story 11.5, 🟡 조건부
location: `.github/workflows/tests.yml`(web 잡은 `lint`+`vitest`만) · `web/playwright.config.ts` · `web/e2e/*.spec.ts`.
severity: high
reason: CI에서 Playwright를 돌리려면 (a) 헤드리스 Chromium 설치(`npx playwright install --with-deps chromium`), (b) 로컬 Supabase 스택을 CI 컨테이너 안에서 기동(마이그레이션 전량 적용 + 시드), (c) `web/.env.local` 대응 시크릿(anon key 등) 관리가 추가로 필요하다 — 이미 `api-db` 잡이 하는 "실DB 컨테이너 기동" 패턴을 재사용할 수는 있지만, 세 가지를 한 번에 결정하는 것은 이 스토리(E2E 스펙 작성) 범위를 넘는 별도 인프라 작업이다.
trigger: **스토리로 만들어 처리한다(사용자 의사: CI에 붙이길 원함).** 순서 = ①CI 전용 시드 픽스처(`buyer@test.com` + 사진 1장 매물) → ②`supabase start` 기반 `e2e` 잡 신설 → ③처음엔 `continue-on-error: true`로 **비차단** 운영하며 flaky 여부 관찰 → ④안정 확인 후 필수 게이트로 승격.
status: open

- **위치:** `.github/workflows/tests.yml`(web 잡은 `lint`+`vitest`만) · `web/playwright.config.ts` · `web/e2e/*.spec.ts`.
- **내용:** Story 11.5가 레포 최초의 Playwright E2E 스위트를 세웠지만, `npm run test:e2e`를 CI에서 자동으로 돌리는 job은 만들지 않았다(스펙 Never 항목 — "로컬 재실행 가능성(#86)까지가 이 스토리의 범위"). 그래서 지금은 `web/e2e/**`를 건드리는 PR이 push돼도 이 스위트가 자동으로 검증되지 않고, 사람이 로컬에서 `npm run test:e2e`를 직접 돌려야만 한다.
- **왜 지금 안 고치나:** CI에서 Playwright를 돌리려면 (a) 헤드리스 Chromium 설치(`npx playwright install --with-deps chromium`), (b) 로컬 Supabase 스택을 CI 컨테이너 안에서 기동(마이그레이션 전량 적용 + 시드), (c) `web/.env.local` 대응 시크릿(anon key 등) 관리가 추가로 필요하다 — 이미 `api-db` 잡이 하는 "실DB 컨테이너 기동" 패턴을 재사용할 수는 있지만, 세 가지를 한 번에 결정하는 것은 이 스토리(E2E 스펙 작성) 범위를 넘는 별도 인프라 작업이다.
- **✎ 2026-07-28 실측으로 범위 정정 (사용자가 "CI에 붙이자"고 결정한 뒤 착수 직전 조사):** 위 (a)(b)(c) 중 **(b) 시드가 진짜 장벽**이고, `api-db` 잡 패턴 재사용만으로는 **안 된다.**
  - **`api-db` 패턴으로 부족하다** — 그 잡은 **맨 Postgres** 컨테이너다(psycopg 직결). 그런데 웹앱은 `supabase-js`로 **PostgREST·GoTrue(인증)** 에 붙는다(`NEXT_PUBLIC_SUPABASE_URL`). 즉 E2E엔 Postgres가 아니라 **Supabase 스택 전체**가 필요하다 → CI에서 `supabase start`(CLI)가 필요하고, 이는 `api-db`가 하는 일과 다른 종류다.
  - **커밋된 시드가 E2E 요구를 못 채운다(실측):** `web/e2e/helpers.ts:8`의 `SEED_USER`는 **`buyer@test.com`** 인데 `supabase/seed.sql`이 만드는 계정은 `admin@test.com`·`seller-seed@test.com`·`seller@test.com` **3개뿐이고 buyer는 없다**(grep 0건). 또 `helpers.ts:141`이 `listing_images`를 REST로 조회해 사진 있는 매물을 찾는데 `seed.sql`은 `listing_images`를 **한 건도 넣지 않는다**(grep 0건).
  - **풍부한 데이터 경로는 CI에서 쓸 수 없다** — 그건 `scripts/seed-local.sh`인데 **운영 스토리지에서 사진을 내려받고** `supabase/.env.seed`(gitignore, 평문 비번)를 요구한다. CI에 운영 자격증명을 넣는 것은 이 워크플로 상단의 **"secrets를 넣지 마라"** 규칙과 정면 충돌한다.
  - **`web/.env.dev`·`.env.local`도 gitignore**라 CI가 직접 만들어야 한다(로컬 스택 anon 키는 고정값이라 `supabase status`로 얻을 수 있어 이건 장벽 아님).
  - **결론:** "잡 하나 추가"가 아니라 **CI 전용 시드 픽스처를 새로 만드는 작업**이다 — `buyer@test.com` 계정 + 사진 1장 이상이 붙은 매물이 필요하고, 사진은 레포에 픽스처 파일로 커밋하거나 CI에서 생성해 로컬 스토리지에 업로드해야 한다. `seed.sql`을 고치면 **운영 시드 경로에도 영향**이 가므로 별도 파일(`supabase/seed-ci.sql`)이 맞는지까지 설계 판단이 필요하다.
  - ⚠️ **시드 없이 잡부터 붙이면 첫 실행부터 빨간불이고**, 그건 "검사가 있는데 아무도 안 믿는" 최악을 만든다 — 붙이는 순서가 중요하다.
- **트리거:** **스토리로 만들어 처리한다(사용자 의사: CI에 붙이길 원함).** 순서 = ①CI 전용 시드 픽스처(`buyer@test.com` + 사진 1장 매물) → ②`supabase start` 기반 `e2e` 잡 신설 → ③처음엔 `continue-on-error: true`로 **비차단** 운영하며 flaky 여부 관찰 → ④안정 확인 후 필수 게이트로 승격.
- **✎ 2026-07-28 (Epic 11 회고, `#172`가 지정한 대장 정리 시점): 트리거를 날짜 없는 조건에서 자리로 못박는다 → `#143`·`#167`이 이미 예약한 Epic 13 게이트 정비.** 같은 축(CI 게이트)의 작업이라 한 자리에서 함께 본다. 기존 사용자 의사("CI에 붙이길 원함")는 그대로 유효하고, **그 전에 요건이 생기면 앞당긴다**는 보조 절로 유지한다.
- **⚠️ 2026-07-28 실측으로 드러난 선행조건 — 이걸 먼저 안 하면 이 항목은 무의미하다:** E2E 잡을 새로 붙이기 전에 **이미 있는 CI가 초록이어야 한다.** 실측: `develop`의 `Tests` 워크플로가 **2026-07-22부터 red**(`api (실DB 통합)` 잡, GitHub Actions run `29934287931`)이고 아무도 보지 않았다. **"검사가 있는데 아무도 안 믿는" 상태를 이 항목이 우려했는데, 그 상태가 이미 존재한다** → `#180`·`#181` 먼저.
- **✎ 2026-07-28 감사 실측 — 이 항목이 없어서 실제로 무엇을 못 잡았나(추측 아님):** 이날 일회성으로 설계·실행한 E2E 31건이 **전부 통과**했다(폰트 self-host 브라우저 실측, `view_count` 브라우저→DB 왕복 +1, 히어로 게이트·자동실행 1회, 접근제어 4경로, sold 비노출, 등록→채팅→구매완료 쓰기 왕복). **즉 이 축은 지금 정상이며, 이 항목이 막는 것은 "앞으로 깨져도 모르는 것"이다.** 그 31건의 상시 승격 후보는 `#182`.

### DW-469: [구 #169] 채팅방 메시지 입력창도 `#84`와 동일한 원인으로 390px에서 가로로 넘친다

origin: 장부 통합 이관(구 docs/tech-debt.md #169) — 원출처: 2026-07-28 Story 11.5 코드리뷰 verification-gap 지적, 🟢 품질
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx:174`(입력창 `<input>` — `flex-1` + 기본 `size` 힌트, 컨테이너는 `max-w-2xl`+`mx-auto`인 `<main>`).
severity: medium
reason: Story 11.5의 스펙(Never 항목)은 이 스토리가 손대는 프로덕션 코드를 `#84`(`ChatAssistant.tsx`) 1건으로 못박았다 — 채팅방 화면은 이 스토리가 감사하기로 정한 4개 화면(랜딩·목록·상세·`/ai`)에 들어있지 않아 범위 밖이다(A3). `#84`의 수정(`size={1}` + `min-w-0`)이 그대로 통할 가능성이 높지만(원인이 동일), 별도 화면에 적용해 재실측하는 일은 이 스토리의 권한 밖이다.
trigger: 채팅 화면(`web/src/app/(user)/chat/**`)을 다음에 손대는 스토리 착수 시 — 또는 반응형 감사 범위를 채팅까지 넓히는 결정이 내려질 때. 그 자리에서 `#84`와 동일한 수정(`size={1}`, `min-w-0`)을 적용하고 390px에서 재실측한 뒤, `web/e2e/viewport-audit.spec.ts`에 채팅방 화면을 감사 대상으로 추가한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx:174`(입력창 `<input>` — `flex-1` + 기본 `size` 힌트, 컨테이너는 `max-w-2xl`+`mx-auto`인 `<main>`).
- **내용:** `#84`가 `/ai`에서 잡은 것과 형태가 완전히 같은 결함이다 — `<main>`이 `mx-auto`라 부모 stretch 대신 자기 content 기준 "선호 폭"(fit-content)만 차지하는데, 그 계산이 `flex-1`(flex-basis:0%)로 실제 렌더될 폭과 무관하게 `<input>`의 기본 `size` 힌트를 그대로 반영해 main이 뷰포트보다 넓어진다. Story 11.5 코드리뷰(verification-gap 레이어)가 로컬 스택에서 실제로 로그인해 실측했다: 390×844 뷰포트, 시드 채팅방(`buyer@test.com`)에서 `document.documentElement.scrollWidth=402` vs `clientWidth=390` — `#84`가 고치기 전 `/ai`에서 쟀던 것과 같은 402px다.
- **왜 지금 안 고치나:** Story 11.5의 스펙(Never 항목)은 이 스토리가 손대는 프로덕션 코드를 `#84`(`ChatAssistant.tsx`) 1건으로 못박았다 — 채팅방 화면은 이 스토리가 감사하기로 정한 4개 화면(랜딩·목록·상세·`/ai`)에 들어있지 않아 범위 밖이다(A3). `#84`의 수정(`size={1}` + `min-w-0`)이 그대로 통할 가능성이 높지만(원인이 동일), 별도 화면에 적용해 재실측하는 일은 이 스토리의 권한 밖이다.
- **트리거:** 채팅 화면(`web/src/app/(user)/chat/**`)을 다음에 손대는 스토리 착수 시 — 또는 반응형 감사 범위를 채팅까지 넓히는 결정이 내려질 때. 그 자리에서 `#84`와 동일한 수정(`size={1}`, `min-w-0`)을 적용하고 390px에서 재실측한 뒤, `web/e2e/viewport-audit.spec.ts`에 채팅방 화면을 감사 대상으로 추가한다.

### DW-470: [구 #170] `#127` 폰트 CDN 가드가 `layout.tsx` 한 파일만 본다 — `globals.css`의 `@import url(https://…)`·다른 레이아웃은 무방비

origin: 장부 통합 이관(구 docs/tech-debt.md #170) — 원출처: 2026-07-28 Story 11.5 후속 코드리뷰 defer, 🟢 품질
location: `web/src/app/fonts.budget.test.ts:10,49`(스캔 대상이 `./layout.tsx` 하나) · 무방비 경로는 `web/src/app/globals.css` · `web/src/app/(admin)/layout.tsx` · `web/src/app/(user)/sell/layout.tsx`.
severity: medium
reason: 이 스토리의 intent-contract(Always)가 `#127` 검사의 관측 범위를 **"`layout.tsx` 소스 문자열 + `fonts/` 총 용량만"** 으로 명시적으로 못박았다 — 대장 원문("vitest 한 건")을 그대로 옮긴 것이다. 관측 범위를 넓히는 것은 그 계약을 벗어나므로 이 리뷰의 권한 밖이다(A3). 같은 리뷰가 짚은 **디렉터리 용량 재귀 미순회**는 계약 안("`fonts/` 총 용량")의 버그라 이번 패스에서 고쳤다(하위 폴더 파일이 예산을 우회하던 문제).
trigger: `web/src/app/globals.css` 또는 루트 외 레이아웃(`(admin)`·`(user)/sell`)의 스타일·폰트 로딩을 손대는 다음 스토리 착수 시 — 또는 `#40`/`#127` 축(폰트 자산)을 다시 여는 스토리. 그 자리에서 `fonts.budget.test.ts`의 스캔 대상을 `web/src/**/layout.tsx` 전량 + `globals.css`로 넓히고, `@import url(http…)`와 `rel="preload|preconnect"`의 외부 오리진도 함께 금지한 뒤 일부러 깨서 red 확인 후 원복해 green 확인한다(B4).
status: open

- **위치:** `web/src/app/fonts.budget.test.ts:10,49`(스캔 대상이 `./layout.tsx` 하나) · 무방비 경로는 `web/src/app/globals.css` · `web/src/app/(admin)/layout.tsx` · `web/src/app/(user)/sell/layout.tsx`.
- **내용:** `#127`이 요구한 규칙은 "폰트를 외부 CDN에서 받지 않는다"인데, 그 규칙을 강제하는 검사는 루트 `layout.tsx`의 **소스 문자열만** 읽는다. 세 후속 리뷰 레이어(adversarial·edge-case·verification-gap)가 독립적으로 같은 구멍을 짚었다: (a) `globals.css`에 `@import url("https://fonts.googleapis.com/…")` 한 줄을 넣으면 `layout.tsx:3`이 그 CSS를 import하므로 **모든 페이지에 CDN 폰트가 되살아나는데** 검사는 그 파일을 아예 읽지 않아 green이다 — 그 파일은 이미 `@import "tailwindcss"`를 쓰고 있어 `@import` 문법이 살아 있는 경로임이 실측으로 확인된다. (b) 나머지 두 레이아웃에 `<link>`를 넣는 경로도 동일하게 무방비다. `rel="preload"`/`preconnect` 형태의 재유입도 현재 검사(`rel="stylesheet"`만 봄)를 통과한다.
- **왜 지금 안 고치나:** 이 스토리의 intent-contract(Always)가 `#127` 검사의 관측 범위를 **"`layout.tsx` 소스 문자열 + `fonts/` 총 용량만"** 으로 명시적으로 못박았다 — 대장 원문("vitest 한 건")을 그대로 옮긴 것이다. 관측 범위를 넓히는 것은 그 계약을 벗어나므로 이 리뷰의 권한 밖이다(A3). 같은 리뷰가 짚은 **디렉터리 용량 재귀 미순회**는 계약 안("`fonts/` 총 용량")의 버그라 이번 패스에서 고쳤다(하위 폴더 파일이 예산을 우회하던 문제).
- **트리거:** `web/src/app/globals.css` 또는 루트 외 레이아웃(`(admin)`·`(user)/sell`)의 스타일·폰트 로딩을 손대는 다음 스토리 착수 시 — 또는 `#40`/`#127` 축(폰트 자산)을 다시 여는 스토리. 그 자리에서 `fonts.budget.test.ts`의 스캔 대상을 `web/src/**/layout.tsx` 전량 + `globals.css`로 넓히고, `@import url(http…)`와 `rel="preload|preconnect"`의 외부 오리진도 함께 금지한 뒤 일부러 깨서 red 확인 후 원복해 green 확인한다(B4).

### DW-471: [구 #171] 반응형 감사가 브레이크포인트 경계값(639/640/1099/1100)을 한 번도 렌더하지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #171) — 원출처: 2026-07-28 Story 11.5 후속 코드리뷰 defer, 🟢 품질
location: `web/playwright.config.ts`의 3개 프로젝트(1280×800·800×1024·390×844) · 검사 대상은 `web/src/components/listings/ResponsiveGrid.tsx`(`grid-cols-1` / `min-[640px]:grid-cols-2` / `min-[1100px]:grid-cols-4`).
severity: medium
reason: 이 스토리의 intent-contract(Always)가 뷰포트 매트릭스를 **"정확히 데스크톱 1280×800 · 태블릿 800×1024 · 모바일 390×844"** 로 못박았다(9.6/9.7/#84가 이미 실측에 쓴 값과의 연속성이 이유). 프로젝트를 추가하는 것은 그 계약을 벗어난다(A3).
trigger: `ResponsiveGrid.tsx`의 브레이크포인트 값이나 `EXPERIENCE.md`의 ≥1100/640~1099/<640 구간을 손대는 다음 스토리 착수 시 — 또는 D5 감사 범위를 넓히는 결정이 내려질 때. 그 자리에서 `playwright.config.ts`에 경계 프로젝트(639·640·1099·1100)를 추가하고 각각 1·2·2·4열을 단언한다.
status: open

- **위치:** `web/playwright.config.ts`의 3개 프로젝트(1280×800·800×1024·390×844) · 검사 대상은 `web/src/components/listings/ResponsiveGrid.tsx`(`grid-cols-1` / `min-[640px]:grid-cols-2` / `min-[1100px]:grid-cols-4`).
- **내용:** 새 E2E 감사는 각 구간의 **한가운데** 폭만 잰다. 경계 자체(639→1열, 640→2열, 1099→2열, 1100→4열)는 어느 뷰포트에서도 렌더되지 않으므로, 임계값이 한 칸 밀리는 회귀(`min-[641px]` 같은 오타·순서 뒤집힘)는 세 프로젝트 전부 green인 채 출하된다. 이 클래스는 가상의 위험이 아니다 — `web/e2e/helpers.ts`의 `assertGridColumns` 주석이 "과거 640/1100 순서 버그가 실측 사례"라고 직접 적고 있다.
- **왜 지금 안 고치나:** 이 스토리의 intent-contract(Always)가 뷰포트 매트릭스를 **"정확히 데스크톱 1280×800 · 태블릿 800×1024 · 모바일 390×844"** 로 못박았다(9.6/9.7/#84가 이미 실측에 쓴 값과의 연속성이 이유). 프로젝트를 추가하는 것은 그 계약을 벗어난다(A3).
- **트리거:** `ResponsiveGrid.tsx`의 브레이크포인트 값이나 `EXPERIENCE.md`의 ≥1100/640~1099/<640 구간을 손대는 다음 스토리 착수 시 — 또는 D5 감사 범위를 넓히는 결정이 내려질 때. 그 자리에서 `playwright.config.ts`에 경계 프로젝트(639·640·1099·1100)를 추가하고 각각 1·2·2·4열을 단언한다.

### DW-473: [구 #173] D5 "내부 가로배치 세로화 없음" 감사가 **실제로 접힐 수 있는 유일한 행**을 한 번도 재지 않는다 — 신뢰속성 행이 시드에 0회 렌더

origin: 장부 통합 이관(구 docs/tech-debt.md #173) — 원출처: 2026-07-28 Story 11.5 3차 코드리뷰 defer, 🟢 품질
location: `web/src/components/listings/TrustAttributes.tsx:122`(`variant="card"` 분기의 `flex flex-wrap`) · 감사 쪽은 `web/e2e/viewport-audit.spec.ts`의 `assertFirstCardMetaLineSingleLine`(대상은 `web/src/components/listings/ListingCard.tsx:83`의 `[data-testid="listing-meta"]`).
severity: medium
reason: 지금 단언을 심으면 시드가 그 행을 안 그리므로 **죽은 코드**가 된다(0건 매칭이면 스킵이거나 항상 실패). 실효 있게 고치려면 시드 데이터에 사고이력·정밀진단 등 신뢰속성을 가진 매물을 넣어야 하는데, 그건 감사 스토리가 아니라 시드 스토리의 일이고 이 스토리의 intent-contract(Never — 시각 디자인·기존 컴포넌트 재설계 금지)와 A3(외과적 변경) 양쪽에 걸린다.
trigger: `scripts/seed-local.sh`/`supabase/seed.sql`의 매물 속성을 손대는 다음 스토리(예: `#89` 시드 재실행 축) 착수 시 — 신뢰속성이 있는 매물을 시드에 포함시키고, 그 자리에서 `TrustAttributes` 카드 분기에 `data-testid`를 달아 390px에서 단일행 단언을 심는다. 일부러 긴 라벨을 넣어 red 확인 후 원복해 green 확인한다(B4).
status: open

- **위치:** `web/src/components/listings/TrustAttributes.tsx:122`(`variant="card"` 분기의 `flex flex-wrap`) · 감사 쪽은 `web/e2e/viewport-audit.spec.ts`의 `assertFirstCardMetaLineSingleLine`(대상은 `web/src/components/listings/ListingCard.tsx:83`의 `[data-testid="listing-meta"]`).
- **내용:** D5 원문이 세로화 금지 대상으로 **이름을 대서 지목한 것이 "신뢰속성 행"**인데, 감사가 재는 것은 meta 줄이다. meta 줄은 `truncate whitespace-nowrap`이고 Tailwind의 `truncate`가 이미 `white-space:nowrap`을 emit하므로 **구조적으로 2줄이 될 수 없다** — 이 검사가 잡는 것은 "접힘"이 아니라 "truncate 계약의 소실"이다(3차 리뷰에서 주석을 그렇게 정정하고 computed `white-space`/`text-overflow` 단언을 덧붙였다). 반면 신뢰속성 행은 `flex-wrap`이라 **카드 안에서 유일하게 진짜로 접힐 수 있는 요소**인데, 로컬 시드 데이터에 해당 속성이 없어 `display`가 null이 되고 **95개 카드 전부에서 0회 렌더된다**(실측: `/search` 3뷰포트 전부에서 `trustRows: 0`). 즉 감사 커버리지가 "약하다"가 아니라 **0**이다. 그러므로 이 행이 390px에서 실제로 접히는지 여부는 지금 아무도 모른다 — 검사도 없고 관측된 적도 없다.
- **왜 지금 안 고치나:** 지금 단언을 심으면 시드가 그 행을 안 그리므로 **죽은 코드**가 된다(0건 매칭이면 스킵이거나 항상 실패). 실효 있게 고치려면 시드 데이터에 사고이력·정밀진단 등 신뢰속성을 가진 매물을 넣어야 하는데, 그건 감사 스토리가 아니라 시드 스토리의 일이고 이 스토리의 intent-contract(Never — 시각 디자인·기존 컴포넌트 재설계 금지)와 A3(외과적 변경) 양쪽에 걸린다.
- **트리거:** `scripts/seed-local.sh`/`supabase/seed.sql`의 매물 속성을 손대는 다음 스토리(예: `#89` 시드 재실행 축) 착수 시 — 신뢰속성이 있는 매물을 시드에 포함시키고, 그 자리에서 `TrustAttributes` 카드 분기에 `data-testid`를 달아 390px에서 단일행 단언을 심는다. 일부러 긴 라벨을 넣어 red 확인 후 원복해 green 확인한다(B4).

### DW-475: [구 #175] `web/e2e/**`는 **어떤 게이트에서도 타입체크되지 않는다** — `PROJECT_NAMES`의 "이름 바꾸면 타입 에러로 드러난다"는 방어가 실행되지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #175) — 원출처: 2026-07-28 Story 11.5 3차 코드리뷰 defer, 🟢 품질
location: `.github/workflows/tests.yml`의 web 잡(스텝이 `npm ci` → `npm run lint` → `npm test`뿐) · 주장을 담은 쪽은 `web/e2e/project-names.ts:5-9`의 주석.
severity: medium
reason: 이 스토리의 intent-contract(Never)가 **"CI(`.github/workflows/tests.yml`)에 새 e2e job을 추가하지 않는다"** 로 못박았다. 타입체크 스텝 추가는 e2e job은 아니지만 같은 워크플로 파일의 CI 게이트 변경이고, `#168`이 예약해 둔 "CI 안정화" 결정과 같은 자리에서 함께 판단해야 중복·모순이 생기지 않는다.
trigger: `#168`(CI e2e 배선)을 실제로 여는 시점 — 그보다 먼저 와도 좋다. web 잡에 `npx tsc --noEmit`(또는 `npm run build`) 스텝 한 줄을 추가하고, 일부러 잘못된 `PROJECT_NAMES` 키를 넣어 CI가 red가 되는지 확인한 뒤 원복해 green 확인한다(B4). 브라우저 설치·Supabase 기동이 필요 없으므로 `#168` 전체보다 훨씬 싸다.
status: open

- **위치:** `.github/workflows/tests.yml`의 web 잡(스텝이 `npm ci` → `npm run lint` → `npm test`뿐) · 주장을 담은 쪽은 `web/e2e/project-names.ts:5-9`의 주석.
- **내용:** `project-names.ts`는 "상수 하나를 공유하면 이름을 바꿀 때 **타입 에러로 드러난다**"고 적어 두었는데, 그 타입 에러를 실제로 내는 것은 `tsc`이고 **CI는 `tsc`를 한 번도 돌리지 않는다**(`npm run build`도 web 잡에 없다). eslint는 여기서 type-aware 설정이 아니라 타입 그래프를 읽지 않는다. 실측: `web/e2e/`에 존재하지 않는 `PROJECT_NAMES` 키를 참조하는 파일을 넣고 돌리면 `npm run lint`는 **exit 0**(무출력), `npx tsc --noEmit`은 **exit 2**(TS2339)다. 즉 e2e 트리는 **실행도 안 되고(#168) 타입체크도 안 되는** 이중 사각지대에 있어, 수동 실행 사이에 조용히 썩을 수 있다. B9("규칙은 어길 수 없는 자리에 박는다") 기준으로 규칙이 실행되지 않는 자리에 있다.
- **왜 지금 안 고치나:** 이 스토리의 intent-contract(Never)가 **"CI(`.github/workflows/tests.yml`)에 새 e2e job을 추가하지 않는다"** 로 못박았다. 타입체크 스텝 추가는 e2e job은 아니지만 같은 워크플로 파일의 CI 게이트 변경이고, `#168`이 예약해 둔 "CI 안정화" 결정과 같은 자리에서 함께 판단해야 중복·모순이 생기지 않는다.
- **트리거:** `#168`(CI e2e 배선)을 실제로 여는 시점 — 그보다 먼저 와도 좋다. web 잡에 `npx tsc --noEmit`(또는 `npm run build`) 스텝 한 줄을 추가하고, 일부러 잘못된 `PROJECT_NAMES` 키를 넣어 CI가 red가 되는지 확인한 뒤 원복해 green 확인한다(B4). 브라우저 설치·Supabase 기동이 필요 없으므로 `#168` 전체보다 훨씬 싸다.

### DW-476: [구 #176] E2E 로케이터가 의존하는 `data-testid`·`aria-haspopup` 계약이 **CI가 도는 어떤 테스트에도 고정돼 있지 않다**

origin: 장부 통합 이관(구 docs/tech-debt.md #176) — 원출처: 2026-07-28 Story 11.5 3차 코드리뷰 defer, 🟢 품질
location: 프로덕션 쪽 훅 — `web/src/components/listings/ListingCard.tsx:83`(`listing-meta`) · `ListingCardImage.tsx`·`ListingGallery.tsx`(`listing-photo`) · `web/src/app/(user)/listings/[id]/InquiryCta.tsx:86`(`inquiry-cta`) · `web/src/components/layout/SiteNav.tsx:138,191`(`aria-haspopup`). 소비처 — `web/e2e/viewport-audit.spec.ts`·`helpers.ts`·`nav-interactions.spec.ts`.
severity: medium
reason: 이 스토리의 intent-contract(Never)가 **"기존 vitest 단위테스트를 수정하거나 대체하지 않는다"** 로 못박았고, 새 vitest를 심는 것도 이 스토리가 정의한 층(E2E 감사 + `#127` 정적 검사 1건) 밖이다. `#175`와 같은 자리에서 함께 판단하는 편이 일관된다.
trigger: `#175`와 같은 시점(웹 CI 게이트를 손대는 다음 작업) — 또는 위 5개 파일 중 하나를 리팩터하는 스토리 착수 시. `SiteNav.test.ts`가 이미 쓰는 소스 스캔 방식 그대로 훅 문자열의 존재를 단언하는 vitest 한 건을 심고, 훅을 지워 red 확인 후 원복해 green 확인한다(B4).
status: open

- **위치:** 프로덕션 쪽 훅 — `web/src/components/listings/ListingCard.tsx:83`(`listing-meta`) · `ListingCardImage.tsx`·`ListingGallery.tsx`(`listing-photo`) · `web/src/app/(user)/listings/[id]/InquiryCta.tsx:86`(`inquiry-cta`) · `web/src/components/layout/SiteNav.tsx:138,191`(`aria-haspopup`). 소비처 — `web/e2e/viewport-audit.spec.ts`·`helpers.ts`·`nav-interactions.spec.ts`.
- **내용:** 이 훅들은 **"셀렉터가 0건 매칭해 검사가 조용히 통과하는 것"을 막으려고** Story 11.5가 프로덕션 코드에 심은 것이다(B9). 그런데 그 훅의 존재를 확인하는 테스트가 `web/src/**/*.test.ts`(= CI가 실제로 도는 집합)에 **하나도 없다** — `grep`으로 확인하면 0건이다. 그래서 리팩터가 `data-testid`를 떨어뜨리거나 `aria-haspopup="true"`를 `"menu"`로 바꾸면 **CI는 green인 채** 감사 층이 실행 불가능해지고, 그 사실은 다음에 누군가 로컬에서 `npm run test:e2e`를 돌릴 때(= 영영 안 돌 수도 있다) 비로소 드러난다. 방어를 심었는데 그 방어가 실행되지 않는 자리에 있는 형태로, `#175`와 같은 축이다.
- **왜 지금 안 고치나:** 이 스토리의 intent-contract(Never)가 **"기존 vitest 단위테스트를 수정하거나 대체하지 않는다"** 로 못박았고, 새 vitest를 심는 것도 이 스토리가 정의한 층(E2E 감사 + `#127` 정적 검사 1건) 밖이다. `#175`와 같은 자리에서 함께 판단하는 편이 일관된다.
- **트리거:** `#175`와 같은 시점(웹 CI 게이트를 손대는 다음 작업) — 또는 위 5개 파일 중 하나를 리팩터하는 스토리 착수 시. `SiteNav.test.ts`가 이미 쓰는 소스 스캔 방식 그대로 훅 문자열의 존재를 단언하는 vitest 한 건을 심고, 훅을 지워 red 확인 후 원복해 green 확인한다(B4).

### DW-477: [구 #177] 상세 화면의 이미지 전면 장애 감사는 **사진 1장만** 시험한다 — 갤러리가 나머지를 마운트하지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #177) — 원출처: 2026-07-28 Story 11.5 3차 코드리뷰 defer, 🟢 품질
location: `web/src/components/listings/ListingGallery.tsx`(현재 인덱스 사진 하나만 `<img>`로 렌더) · 감사 쪽은 `web/e2e/image-fallback.spec.ts`의 상세 케이스.
severity: medium
reason: 전량을 시험하려면 캐러셀을 N-1회 넘기며 매번 단언해야 하는데, 그건 이 스토리가 정의한 "전면 장애 재현" 시나리오를 넘어 **갤러리 상호작용 E2E**라는 별개 표면이다(A3 — 요청받지 않은 범위 확장). 갤러리 접근성·정렬은 이미 `#79`(해소)·`#81` 축에서 따로 다뤄 왔다.
trigger: `ListingGallery.tsx`를 손대는 다음 스토리 착수 시 — 또는 `#81`(정렬 로직 2벌)을 여는 시점. 그 자리에서 상세 케이스에 "다음 사진" 버튼으로 전량 순회하며 각 장의 폴백을 단언하는 루프를 추가하고, 사진이 2장 이상인 매물을 고르도록 `fetchOnSaleListingIdWithPhoto`에 `having count(*) > 1` 조건을 넣는다.
status: open

- **위치:** `web/src/components/listings/ListingGallery.tsx`(현재 인덱스 사진 하나만 `<img>`로 렌더) · 감사 쪽은 `web/e2e/image-fallback.spec.ts`의 상세 케이스.
- **내용:** `#73`/`#86` 해소 기록은 "목록·상세·`/ai` **세 소비처 모두에서 전량**"이라고 적었는데, 상세에서는 그게 **구조적으로 성립하지 않는다.** 갤러리는 `urls[index]` 한 장만 DOM에 올리므로 스크롤로 나머지를 노출시킬 방법이 없다(목록의 `loading="lazy"`와 달리 지연로딩이 아니라 **미마운트**다). 3차 리뷰가 이 사실을 상세 케이스 주석에 실측으로 명시하고 단언을 "살아남은 사진 `<img>` 0개 + 플레이스홀더 ≥1"로 정직하게 좁혔지만, 캐러셀 2~N번째 사진의 폴백은 **여전히 시험되지 않는다.** 목록(`/search`)은 이번 패스에서 진짜 전량(90/90)으로 고쳐졌다.
- **왜 지금 안 고치나:** 전량을 시험하려면 캐러셀을 N-1회 넘기며 매번 단언해야 하는데, 그건 이 스토리가 정의한 "전면 장애 재현" 시나리오를 넘어 **갤러리 상호작용 E2E**라는 별개 표면이다(A3 — 요청받지 않은 범위 확장). 갤러리 접근성·정렬은 이미 `#79`(해소)·`#81` 축에서 따로 다뤄 왔다.
- **트리거:** `ListingGallery.tsx`를 손대는 다음 스토리 착수 시 — 또는 `#81`(정렬 로직 2벌)을 여는 시점. 그 자리에서 상세 케이스에 "다음 사진" 버튼으로 전량 순회하며 각 장의 폴백을 단언하는 루프를 추가하고, 사진이 2장 이상인 매물을 고르도록 `fetchOnSaleListingIdWithPhoto`에 `having count(*) > 1` 조건을 넣는다.

### DW-478: [구 #178] `#155`(`/search` 376px 가로 넘침)의 유력 원인이 `#84` 수정 과정에서 규명됐으나 그 항목에 기록되지 못했다

origin: 장부 통합 이관(구 docs/tech-debt.md #178) — 원출처: 2026-07-28 Story 11.5 3차 코드리뷰 defer, 🟢 품질
location: `docs/tech-debt.md`의 기존 항목 `#155`(현재 "범인 미특정"으로 남아 있음) · 실제 코드는 `web/src/app/(user)/search/page.tsx:186`의 `<main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">`.
severity: medium
reason: (a) 기존 항목 본문 갱신은 이 세션의 호출 지시(기존 대장 항목 수정 금지)에 걸린다 — `#172`·`#174`와 같은 사유. (b) 코드 수정 자체도 이 스토리의 감사 매트릭스 최소 폭이 390px이라 `#155`(≤376px에서만 발현)를 **관측할 수단이 없는 상태**에서 손대는 꼴이 된다(A1 — 검증 못 하는 수정은 하지 않는다).
trigger: `#155`를 실제로 여는 시점 — 또는 `#169`(채팅방)를 고치는 스토리 착수 시(같은 메커니즘이라 한 자리에서 함께 보는 것이 싸다). 그 자리에서 376px 뷰포트를 하나 띄워 `<main>`의 `scrollWidth`를 재고, `size={1}`(또는 컨테이너에 `w-full`)로 고쳐 red→green을 실측한다.
status: open

- **위치:** `docs/tech-debt.md`의 기존 항목 `#155`(현재 "범인 미특정"으로 남아 있음) · 실제 코드는 `web/src/app/(user)/search/page.tsx:186`의 `<main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">`.
- **내용:** Story 11.5가 `#84`를 고치면서 밝힌 원인은 **"`mx-auto`가 걸린 `<main>`이 fit-content 폭을 갖고, 그 max-content 계산이 `<input>`의 기본 `size` 힌트를 끌어올린다"** 였다(그래서 수정이 `min-w-0`이 아니라 `size={1}`이었다). `/search`의 `<main>`은 **같은 모양**(`mx-auto max-w-6xl … p-6`)이고 필터 입력들을 담고 있어, `#155`도 같은 메커니즘일 가능성이 높다 — 같은 원인의 세 번째 화면인 채팅방은 이미 `#169`로 등재됐다. `#155` 본문 자신이 *"`#84`와 둘 다 '좁은 폭에서 본문이 안 줄어든다'는 한 문제의 다른 페이지"* 라고 적고 있어, 이 가설은 그 항목이 기다리던 답에 정확히 대응한다. **적어두지 않으면 다음 사람이 처음부터 다시 규명해야 한다.**
- **왜 지금 안 고치나:** (a) 기존 항목 본문 갱신은 이 세션의 호출 지시(기존 대장 항목 수정 금지)에 걸린다 — `#172`·`#174`와 같은 사유. (b) 코드 수정 자체도 이 스토리의 감사 매트릭스 최소 폭이 390px이라 `#155`(≤376px에서만 발현)를 **관측할 수단이 없는 상태**에서 손대는 꼴이 된다(A1 — 검증 못 하는 수정은 하지 않는다).
- **트리거:** `#155`를 실제로 여는 시점 — 또는 `#169`(채팅방)를 고치는 스토리 착수 시(같은 메커니즘이라 한 자리에서 함께 보는 것이 싸다). 그 자리에서 376px 뷰포트를 하나 띄워 `<main>`의 `scrollWidth`를 재고, `size={1}`(또는 컨테이너에 `w-full`)로 고쳐 red→green을 실측한다.

### DW-479: [구 #179] `recommended` 리뷰 스킵이 **마이그레이션이 든 스토리**에도 걸린다 — 규모·위험과 리뷰량이 반비례했다

origin: 장부 통합 이관(구 docs/tech-debt.md #179) — 원출처: 2026-07-28 Epic 11 실행 관측, 🟡 조건부
location: `.bmad-loop/policy.toml`의 `[review] trigger = "recommended"` vs Epic 11 실행 로그(`.bmad-loop/runs/20260728-105733-33e0/journal.jsonl`).
severity: high
reason: 정책이 `recommended`(권장)일 때 dev 세션의 자기평가로 독립 리뷰를 건너뛰는데, 실제로 건너뛴 두 스토리(11-3, DB 마이그레이션이 든 11-4)가 오히려 크고 위험한 스토리였다 — 리뷰량이 위험도가 아니라 dev 자신의 자기평가에 좌우된 것이다.
trigger: Epic 12 착수 시 그 런을 `always`로 띄웠는지 확인하고, 끝나면 "마이그 스토리에 독립 리뷰가 실제로 붙었는지"를 로그로 확인해 이 항목을 닫는다. 선택지: (a) 현행 유지(토큰 절약 우선) (b) `trigger = "always"`로 복귀 (c) **조건부** — `supabase/migrations/**`가 diff에 있으면 `recommended`와 무관하게 독립 리뷰 강제. (c)가 이 프로젝트 규칙과 가장 정합적이다 — CLAUDE.md B3이 *"DB는 되돌리기가 없다"* 로 마이그레이션을 가장 무거운 축으로 다루는데, 정작 그 축에서 검토를 아끼는 것은 앞뒤가 안 맞는다. 다만 bmad-loop이 diff 조건부 트리거를 지원하는지는 **미확인**(추측 금지 — 착수 시 실측할 것).
status: open

- **위치:** `.bmad-loop/policy.toml`의 `[review] trigger = "recommended"` vs Epic 11 실행 로그(`.bmad-loop/runs/20260728-105733-33e0/journal.jsonl`).
- **내용:** `recommended`는 dev 세션이 "독립 리뷰 불필요"로 판정하면 opus 리뷰 세션을 건너뛴다. #123에서 **작동 자체는 실증**됐는데, 실제로 걸린 두 스토리가 하필 이랬다:

  | 스토리 | dev 토큰 | 독립리뷰 | 내용 |
  |---|---|---|---|
  | 11-3 | **95.2M**(에픽 최대) | **0회** | 랜딩 히어로 검색·차종 칩·AI 채팅 연동 신규 599줄 |
  | 11-4 | 46.5M | **0회** | **DB 마이그레이션 `0021`**(anon GRANT + 인덱스) 포함 |
  | 11-1 | 49.7M | 2회(1회는 timeout) | 리뷰가 **18건** 지적 → #130~#147 등재 |

  11-1(작은 스키마 작업)은 리뷰가 18건을 잡았는데, **그보다 큰 11-3과 DB를 건드리는 11-4는 0건 검토**됐다. 리뷰량이 위험도가 아니라 **dev 자신의 자기평가**에 달려 있고, 자기평가는 자기가 못 본 것을 셀 수 없다.
- **⚠️ 오해 금지 — "리뷰가 전혀 없었다"는 아니다:** `bmad-dev-auto`는 세션 **안에** 자체 리뷰 단계(step-04)를 갖고 있고 그건 돌았다. 11-4에선 그 자체 리뷰가 `fetchSection`을 `try/catch`로 감싸는 패치를 냈다. 건너뛴 것은 **별도 세션으로 도는 opus 독립 리뷰**다. 자기 코드를 자기가 보는 것과 다른 세션이 보는 것의 차이이고, 이 프로젝트는 그 차이를 이미 규칙으로 인정하고 있다(CLAUDE.md B4 *"코드리뷰는 새 세션에서 돈다 — 작업한 세션이 자기 작업을 보면 같은 사각지대를 갖는다"*).
- **왜 지금 무해한가(확정 아님):** 11-4의 마이그레이션 `0021`은 **사후에 사람이 읽어 확인**했다 — GRANT 1줄 + 부분 인덱스 1개로 좁고, `#134`가 요구한 내용과 정확히 일치하며, 근거가 주석에 남아 있다. 즉 이번 건은 결과적으로 문제없다. **문제는 결과가 아니라 "그 판단을 아무도 강제하지 않았다"는 구조다.**
- **왜 이 에픽에서 안 고쳤나:** 정책은 도는 런에 실시간 반영되지 않고(#123 경위), 발견 시점에 남은 스토리가 11-4·11-5뿐이라 바꿔도 적용될 자리가 없었다.
- **✅ 결정됨 (2026-07-28, 사용자): (d) 하이브리드.** 평소는 `trigger = "recommended"` 유지, **마이그레이션이 예정된 런만 `always`로 시작**한다. (c)(diff 조건부 강제)는 **엔진이 지원하지 않음이 확정** — `REVIEW_TRIGGER_MODES = {"always","recommended"}` 둘뿐이다(`bmad_loop/policy.py` 실측). 첫 적용 지점 = **Epic 12**(`12-1 멱등키 마이그레이션`으로 시작하므로 그 런을 `always`로 띄운다).
- **트리거(잔여):** Epic 12 착수 시 그 런을 `always`로 띄웠는지 확인하고, 끝나면 "마이그 스토리에 독립 리뷰가 실제로 붙었는지"를 로그로 확인해 이 항목을 닫는다. 선택지: (a) 현행 유지(토큰 절약 우선) (b) `trigger = "always"`로 복귀 (c) **조건부** — `supabase/migrations/**`가 diff에 있으면 `recommended`와 무관하게 독립 리뷰 강제. (c)가 이 프로젝트 규칙과 가장 정합적이다 — CLAUDE.md B3이 *"DB는 되돌리기가 없다"* 로 마이그레이션을 가장 무거운 축으로 다루는데, 정작 그 축에서 검토를 아끼는 것은 앞뒤가 안 맞는다. 다만 bmad-loop이 diff 조건부 트리거를 지원하는지는 **미확인**(추측 금지 — 착수 시 실측할 것).

### DW-483: [구 #183] 화면 1개를 여는 데 인증 서버(`/auth/v1/user`)를 17~27번 부른다 — 링크 프리페치가 `getUser()`를 증폭시킨다

origin: 장부 통합 이관(구 docs/tech-debt.md #183) — 원출처: 2026-07-28 실측, 🟡 조건부
location: `web/src/proxy.ts`·`web/src/lib/auth/guard.ts`·`web/src/lib/supabase/session.ts` + 각 라우트의 서버 컴포넌트(`app/page.tsx`·`(user)/search/page.tsx`·`(user)/listings/[id]/page.tsx`·`(user)/ai/page.tsx`·`(user)/chat/page.tsx`·`(user)/sell/page.tsx`·`(user)/wishlist/page.tsx` 등 — `getUser()` 호출 지점 **24곳/18파일**).
severity: high
reason: Epic 11은 마감됐고 이건 **성능·아키텍처 축**이라 스토리 범위 밖이다. 고치려면 (a) 운영 실측으로 배율 확인 → (b) `getUser()` 호출 지점을 "인증이 꼭 서버 검증돼야 하는 곳"과 "상위 값을 받아 쓰면 되는 곳"으로 분류 → (c) `Link prefetch` 정책 조정 여부 판단, 세 단계가 필요하다. **지금은 무해하다**(데모 규모, 로컬은 `workers: 4`로 회피됨).
trigger: **Epic 13(성능·게이트 정비) 착수 시** — 또는 그 전에 운영에서 인증 레이트리밋·지연이 관측되면 앞당긴다. 그 자리에서 위 (a)(b)(c)를 순서대로 하고, 고친 뒤 **같은 방법으로 다시 재서**(문서 요청 1건 vs 브라우저 이동 1회) 배율이 실제로 줄었는지 확인한다 — "고쳤다"가 아니라 "숫자가 줄었다"로 닫는다(B4).
status: open

- **위치:** `web/src/proxy.ts`·`web/src/lib/auth/guard.ts`·`web/src/lib/supabase/session.ts` + 각 라우트의 서버 컴포넌트(`app/page.tsx`·`(user)/search/page.tsx`·`(user)/listings/[id]/page.tsx`·`(user)/ai/page.tsx`·`(user)/chat/page.tsx`·`(user)/sell/page.tsx`·`(user)/wishlist/page.tsx` 등 — `getUser()` 호출 지점 **24곳/18파일**).
- **어떻게 발견했나:** E2E 스위트를 8워커로 돌릴 때 로컬 GoTrue가 간헐적으로 504를 뱉어(`#182` ③) 그 원인을 쫓다가, "한 실행에 `/user` 5,231건"이 **정상인지** 확인하려고 직접 쟀다.
- **실측(추측 아님, 2026-07-28 로컬 운영빌드 + 시드 계정 `buyer@test.com`):**
  - 비로그인 랜딩 1회 → `/user` **0회**(세션 쿠키가 없으니 아예 안 부른다)
  - **문서 요청 1건**(브라우저 라우터를 안 거치는 순수 `fetch('/')`) → **2회**. ← 서버 렌더 자체는 정상이다(프록시 1 + 페이지 1).
  - **브라우저로 랜딩 1회 이동** → **27회**. `/search` 이동 → **17회**.
  - 차이의 원인을 네트워크 로그로 직접 확인: 랜딩 1회 이동이 만든 **RSC 프리페치(`?_rsc=`) 요청이 48건**이었다(내비 3 + 차종칩 6 + 카드 링크 + 전체보기 + 찜·채팅·판매 …, **게다가 같은 URL이 서로 다른 `_rsc` 토큰으로 두 번씩**). 프리페치는 그 라우트의 서버 컴포넌트를 실제로 실행하므로 **링크 하나당 `getUser()` 한 번 이상**이 따라 붙는다.
  - 스위트 전체: 테스트 53건에 `/user` **5,231건**(테스트당 평균 98회).
- **왜 문제인가:** `getUser()`는 쿠키를 읽는 게 아니라 **인증 서버로 네트워크 왕복을 한다**(`getSession()`과 다른 점). 그래서 **인증 트래픽이 "화면에 보이는 링크 수"에 비례해 늘어난다.** 로컬에선 도커 내부 DNS를 포화시켜 테스트를 붉게 만들었고(`#182` ③ — 그래서 `workers: 4`로 낮췄다), 운영에선 페이지뷰당 수십 번의 Supabase 인증 API 호출 = 지연·요금·레이트리밋 노출이다.
- **아직 모르는 것(정직하게 남긴다):** ① **운영에서도 같은 배율인지 재지 않았다** — Vercel 엣지/Next의 프리페치 캐시가 로컬과 다르게 동작할 수 있다. ② 같은 URL이 두 번씩 프리페치된 이유(hover + viewport 중복인지, 다른 원인인지)를 규명하지 않았다. ③ `getUser()` 24곳 중 몇 곳이 **정말 필요한지**(예: `getSession()`으로 충분한 자리, 상위에서 한 번 구해 내려주면 되는 자리) 분류하지 않았다.
- **왜 지금 안 고치나:** Epic 11은 마감됐고 이건 **성능·아키텍처 축**이라 스토리 범위 밖이다. 고치려면 (a) 운영 실측으로 배율 확인 → (b) `getUser()` 호출 지점을 "인증이 꼭 서버 검증돼야 하는 곳"과 "상위 값을 받아 쓰면 되는 곳"으로 분류 → (c) `Link prefetch` 정책 조정 여부 판단, 세 단계가 필요하다. **지금은 무해하다**(데모 규모, 로컬은 `workers: 4`로 회피됨).
- **트리거:** **Epic 13(성능·게이트 정비) 착수 시** — 또는 그 전에 운영에서 인증 레이트리밋·지연이 관측되면 앞당긴다. 그 자리에서 위 (a)(b)(c)를 순서대로 하고, 고친 뒤 **같은 방법으로 다시 재서**(문서 요청 1건 vs 브라우저 이동 1회) 배율이 실제로 줄었는지 확인한다 — "고쳤다"가 아니라 "숫자가 줄었다"로 닫는다(B4).

### DW-485: [구 #185] `scripts/check_migrations.py`의 동적 self-containment 프로브 3종이 `chat_messages`·`chat_rooms`를 전혀 안 본다

origin: 장부 통합 이관(구 docs/tech-debt.md #185) — 원출처: 2026-07-28 Story 12-1 코드리뷰 adversarial 지적, 🟢 품질
location: `scripts/check_migrations.py`의 동적 검사 3개 프로브(컬럼 GRANT·컬럼 차단·RLS 정책 — 전부 `listings`/`guide_documents` 대상). `0022_chat_idempotency_key.sql`을 포함해 chat 관련 마이그(`0003`·`0010`·`0016`·`0022`)는 게이트를 통과해도 이 3개 프로브 중 어느 것도 실제로 chat 스키마 상태를 확인하지 않는다.
severity: medium
reason: 게이트에 새 프로브를 추가하는 것은 이 스토리의 범위(멱등키 컬럼·제약 추가)를 넘는 별도 인프라 작업이고, 현재 실질적 위험은 이미 무해하다 — chat 스키마의 실제 동작 검증은 실DB 통합테스트(`api/tests/integration/test_chat_idempotency_real_db.py` 등)가 별도로 맡고 있어 이중 안전망 없음이 아니라 "다른 층이 담당" 상태다.
trigger: chat 관련 마이그레이션에 GRANT/RLS처럼 프로브가 실측 확인해야 할 축(예: `realtime.messages` 정책, Story 12.2)이 새로 생길 때 — 그 스토리에서 함께 프로브 추가 여부를 판단한다.
status: open

- **위치:** `scripts/check_migrations.py`의 동적 검사 3개 프로브(컬럼 GRANT·컬럼 차단·RLS 정책 — 전부 `listings`/`guide_documents` 대상). `0022_chat_idempotency_key.sql`을 포함해 chat 관련 마이그(`0003`·`0010`·`0016`·`0022`)는 게이트를 통과해도 이 3개 프로브 중 어느 것도 실제로 chat 스키마 상태를 확인하지 않는다.
- **내용:** 이번 스토리(12.1)가 원인이 아니라 게이트가 처음 설계될 때(Story 8.6)부터 있던 커버리지 범위다 — 코드리뷰가 `0022`를 보다가 우연히 짚었을 뿐이다. 실제 영향: 게이트가 초록이어도 그것이 "chat_messages·chat_rooms의 컬럼·제약·정책이 기대대로다"를 증명하지는 못한다(예: 이번 스토리의 `client_message_id`/`UNIQUE(room_id, client_message_id)`가 조용히 다른 모양으로 존재해도 이 게이트만으로는 못 잡는다 — 실제 정합성은 `api/tests/integration/test_chat_idempotency_real_db.py`의 실INSERT 테스트가 커버한다).
- **왜 지금 안 고치나:** 게이트에 새 프로브를 추가하는 것은 이 스토리의 범위(멱등키 컬럼·제약 추가)를 넘는 별도 인프라 작업이고, 현재 실질적 위험은 이미 무해하다 — chat 스키마의 실제 동작 검증은 실DB 통합테스트(`api/tests/integration/test_chat_idempotency_real_db.py` 등)가 별도로 맡고 있어 이중 안전망 없음이 아니라 "다른 층이 담당" 상태다.
- **트리거:** chat 관련 마이그레이션에 GRANT/RLS처럼 프로브가 실측 확인해야 할 축(예: `realtime.messages` 정책, Story 12.2)이 새로 생길 때 — 그 스토리에서 함께 프로브 추가 여부를 판단한다.

### DW-486: [구 #186] Story 12.3·12.4의 인수조건이 `client_message_id`를 한 번도 이름으로 요구하지 않는다 — 12.1이 놓은 멱등키가 소비되지 않을 구조

origin: 장부 통합 이관(구 docs/tech-debt.md #186) — 원출처: 2026-07-28 Story 12-1 후속 코드리뷰, 🟡 기능
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`의 Story 12.3 인수조건(멱등키를 "낙관적 전송(멱등키로 중복 차단)"이라고만 언급, 컬럼명·생성 주체·생성 시점 없음) + 실제 전송 경로 `web/src/lib/messages.ts`의 `sendMessage`, `app/lib/features/chat/chat_repository.dart`.
severity: high
reason: 12.1의 Never 절이 클라이언트 배선을 명시적으로 12.3 범위로 잘랐다. 여기서 `messages.ts`를 고치면 그 경계를 넘고, 12.2(브로드캐스트)가 아직 없어 ③의 확정 경로를 지금 설계해도 검증할 대상이 없다.
trigger: **Story 12.3 스펙 작성 시** — 그 자리에서 인수조건 3개를 심는다: (a) 전송 시 `crypto.randomUUID()`로 메시지 1건당 1회 키를 만들어 실어 보낸다(web·app 양쪽), (b) 중복 전송이 0행을 돌려줄 때 `(room_id, client_message_id)`로 기존 행을 조회해 낙관적 말풍선을 확정한다, (c) 재전송이 행 1개로 수렴함을 실제 전송 경로(PostgREST)로 확인한다. 12.4 스펙 작성 시엔 dedup 키를 "멱등키, 없으면 행 id"로 못 박는다.
status: open

- **위치:** `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`의 Story 12.3 인수조건(멱등키를 "낙관적 전송(멱등키로 중복 차단)"이라고만 언급, 컬럼명·생성 주체·생성 시점 없음) + 실제 전송 경로 `web/src/lib/messages.ts`의 `sendMessage`, `app/lib/features/chat/chat_repository.dart`.
- **내용:** 세 갈래가 한 덩어리다. ① **의무가 안 심겼다** — 12.1은 컬럼과 제약만 놓고 "클라이언트가 채우는 건 12.3"이라고 범위를 그었는데, 12.3의 인수조건엔 그 요구가 없다. 12.3이 그대로 끝나면 모든 행의 `client_message_id`가 NULL이고, NULL끼리는 유니크 제약이 충돌하지 않으므로 FR41(중복 방지)이 **조용히 미구현**으로 남는다(이 사실은 이제 `test_null_client_message_id_is_not_deduplicated_by_on_conflict`가 검사로 고정하고 있다). ② **문법이 안 맞는다** — 12.1의 스펙·마이그 주석·테스트가 전부 `INSERT ... ON CONFLICT DO NOTHING` 원시 SQL을 전제하는데, 실제 전송은 supabase-js/PostgREST를 통과한다. supabase-js `.insert()`엔 그 옵션이 없고 대응물은 `.upsert(..., { onConflict: 'room_id,client_message_id', ignoreDuplicates: true })`인데, 이건 무시된 행에 대해 **표현을 안 돌려준다** — 현재 호출부가 쓰는 `.select().single()`은 0행을 받아 PGRST116으로 던진다. ③ **확정 신호가 없다** — 재전송은 정의상 클라이언트가 확정을 못 받은 상황인데, 무시된 INSERT는 반환 행도 없고 (12.2가 붙일) DB 브로드캐스트도 발화하지 않는다. 낙관적 말풍선이 pending에서 못 벗어난다. 12.4의 갭 보정도 같은 축이다 — "멱등키로 중복 제거"라고 규정했는데 키가 nullable이라 NULL 구간 행은 dedup 신원이 없다(`client_message_id ?? row.id`처럼 서버 id로 떨어지는 규칙이 필요).
- **왜 지금 안 고치나:** 12.1의 Never 절이 클라이언트 배선을 명시적으로 12.3 범위로 잘랐다. 여기서 `messages.ts`를 고치면 그 경계를 넘고, 12.2(브로드캐스트)가 아직 없어 ③의 확정 경로를 지금 설계해도 검증할 대상이 없다.
- **트리거:** **Story 12.3 스펙 작성 시** — 그 자리에서 인수조건 3개를 심는다: (a) 전송 시 `crypto.randomUUID()`로 메시지 1건당 1회 키를 만들어 실어 보낸다(web·app 양쪽), (b) 중복 전송이 0행을 돌려줄 때 `(room_id, client_message_id)`로 기존 행을 조회해 낙관적 말풍선을 확정한다, (c) 재전송이 행 1개로 수렴함을 실제 전송 경로(PostgREST)로 확인한다. 12.4 스펙 작성 시엔 dedup 키를 "멱등키, 없으면 행 id"로 못 박는다.

### DW-487: [구 #187] 로컬 Supabase 스택에 0020~0022를 psql로 손으로 적용해 CLI 이력 테이블과 어긋났을 수 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #187) — 원출처: 2026-07-28 Story 12-1 검증 중 발생, 🟡 기능
location: 로컬 Supabase Docker 스택(포트 55322)의 `supabase_migrations.schema_migrations` 테이블 vs `supabase/migrations/` 파일 목록.
severity: high
reason: 12.1의 범위(멱등키 컬럼·제약)와 무관하고, 착수 전부터 있던 상태다. 지금 스택을 리셋하면 진행 중인 검증 환경이 날아간다.
trigger: **다음 `supabase db reset` 또는 다음 로컬 E2E 실행 시** — 그 자리에서 `select * from supabase_migrations.schema_migrations`를 실제로 떠서 0001~0022가 전부 들어 있는지 확인하고, 빠졌으면 리셋해 파일에서 다시 만든다. "고쳤다"가 아니라 "이력 행이 22개다"로 닫는다.
status: open

- **위치:** 로컬 Supabase Docker 스택(포트 55322)의 `supabase_migrations.schema_migrations` 테이블 vs `supabase/migrations/` 파일 목록.
- **내용:** 12.1 검증을 시작할 때 로컬 스택은 0019까지만 적용돼 있었다(0020·0021 미적용). 검증을 진행하려고 0020~0022를 psql로 직접 적용했는데, 그러면 스키마는 최신이 되지만 CLI가 "무엇을 적용했나"를 기록하는 이력 테이블은 갱신되지 않는다. 이건 §9.2가 상세히 적어둔 사고와 같은 계열이다 — `0003c_chat_room_integrity.sql`이 CLI에 조용히 `Skipping`돼 로컬 fresh DB에만 `chat_rooms` 위조 방지 트리거가 없었던 일. 스펙의 Residual risks에 적히긴 했으나 대장에 없어서 "열린 일"로 세어지지 않았다(B8 — 미룬 것도 여기 적는다).
- **왜 지금 안 고치나:** 12.1의 범위(멱등키 컬럼·제약)와 무관하고, 착수 전부터 있던 상태다. 지금 스택을 리셋하면 진행 중인 검증 환경이 날아간다.
- **트리거:** **다음 `supabase db reset` 또는 다음 로컬 E2E 실행 시** — 그 자리에서 `select * from supabase_migrations.schema_migrations`를 실제로 떠서 0001~0022가 전부 들어 있는지 확인하고, 빠졌으면 리셋해 파일에서 다시 만든다. "고쳤다"가 아니라 "이력 행이 22개다"로 닫는다.

### DW-488: [구 #188] `api/tests/integration/`에 `conftest.py`가 없어 시드 헬퍼가 파일마다 복제된다

origin: 장부 통합 이관(구 docs/tech-debt.md #188) — 원출처: 2026-07-28 Story 12-1 후속 코드리뷰, 🟢 품질
location: `api/tests/integration/` 5개 파일 전부 — `TEST_DATABASE_URL` skip 가드, `auth.users`+`profiles` 생성, `listings` INSERT 컬럼 목록을 각자 다시 구현한다. `find api/tests -name conftest.py` → 0건.
severity: medium
reason: 공통 픽스처 추출은 12.1이 안 만든 파일 4개를 함께 고치는 일이라 "바뀐 줄이 요청에 추적된다"(A3 외과적 변경)를 어긴다. 12.1 하나만 보면 이득이 없다.
trigger: **Epic 12에서 실DB 통합 테스트 파일을 하나 더 추가할 때**(12.2의 `realtime.messages` 정책 검증이 유력) — 6번째 복제를 만들기 전에 `conftest.py`로 skip 가드·`_create_user`·`_insert_listing`을 올린다. 그 자리에서 tests.yml의 격리 규칙(현재 주석뿐)도 픽스처로 강제할지 함께 판단한다(#143·B9와 같은 축).
status: open

- **위치:** `api/tests/integration/` 5개 파일 전부 — `TEST_DATABASE_URL` skip 가드, `auth.users`+`profiles` 생성, `listings` INSERT 컬럼 목록을 각자 다시 구현한다. `find api/tests -name conftest.py` → 0건.
- **내용:** 복제가 이미 결함을 만들었다 — 12.1의 첫 구현이 형제 파일의 `_create_seller`를 옮기다 판매자 유저에도 `role: "buyer"`를 하드코딩했고 코드리뷰에서 잡혔다. `_LISTING_COLS`처럼 15개 컬럼을 나열한 상수도 파일마다 따로 산다. Epic 12에 스토리가 5개 더 남아 있어 그대로 두면 복제본이 계속 늘어난다. 지금 위험이 낮은 이유는 각 파일이 uuid로 유일 키를 쓰고 스스로 정리하기 때문이고, 실제 피해는 `listings`에 NOT NULL 컬럼이 추가되는 순간 5개 파일이 각각 깨지는 형태로 온다.
- **왜 지금 안 고치나:** 공통 픽스처 추출은 12.1이 안 만든 파일 4개를 함께 고치는 일이라 "바뀐 줄이 요청에 추적된다"(A3 외과적 변경)를 어긴다. 12.1 하나만 보면 이득이 없다.
- **트리거:** **Epic 12에서 실DB 통합 테스트 파일을 하나 더 추가할 때**(12.2의 `realtime.messages` 정책 검증이 유력) — 6번째 복제를 만들기 전에 `conftest.py`로 skip 가드·`_create_user`·`_insert_listing`을 올린다. 그 자리에서 tests.yml의 격리 규칙(현재 주석뿐)도 픽스처로 강제할지 함께 판단한다(#143·B9와 같은 축).

### DW-489: [구 #189] `#186`의 전제 중 12.4 부분이 사실과 다르다 — 12.4 인수조건은 `client_message_id`를 명시적으로 요구한다

origin: 장부 통합 이관(구 docs/tech-debt.md #189) — 원출처: 2026-07-28 Story 12-1 3차 코드리뷰 실측, 🟢 품질, 기존 항목 무수정 정정
location: `docs/tech-debt.md` #186의 **제목**과 본문 ① vs `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:930`.
severity: medium
reason: `#186`이 "12.3·12.4 모두 client_message_id를 요구하지 않는다"고 썼지만, 실제로는 12.4 인수조건(:930)이 이미 그 컬럼명을 dedup 키로 명시 요구하고 있어 12.4에 대한 주장만 틀렸다(12.3 지적은 여전히 유효하다).
trigger: **Story 12.3 스펙 작성 시** — #186을 집어드는 그 자리에서 이 항목을 함께 읽고, 12.4에 심을 인수조건은 "없는 요구를 새로 만든다"가 아니라 "이미 있는 요구(:930)에 NULL 구간 fallback 규칙을 더한다"로 잡는다.
status: done 2026-07-29
resolution: DW-486(구 #186)의 전제를 바로잡는 정정 메모라 원항목에 병합 — epics-increment:122가 client_message_id를 명시 요구함을 확인

- **위치:** `docs/tech-debt.md` #186의 **제목**과 본문 ① vs `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:930`.
- **내용:** #186은 제목에서 *"Story 12.3·12.4의 인수조건이 `client_message_id`를 한 번도 이름으로 요구하지 않는다"* 고 단정했다. **12.4에 대해서는 틀렸다** — `epics-increment-2026-07-12.md:930`이 *"…재조회로 상대방이 보낸 놓친 메시지를 병합한다(dedup 키=`client_message_id`)(AC-CHAT-2)"* 로 컬럼명을 **명시적으로** 요구한다(같은 문서 :122의 AC-CHAT-2 정의도 동일). #186 본문 말미의 실질 지적("키가 nullable이라 NULL 구간 행은 dedup 신원이 없다 → `client_message_id ?? row.id` 규칙이 필요")은 **여전히 유효**하고, **12.3에 대한 지적도 유효**하다(12.3 인수조건엔 실제로 컬럼명·생성 주체·생성 시점이 없다). 틀린 것은 "12.4도 요구하지 않는다"는 범위 주장 하나다.
- **왜 기존 항목을 고치지 않았나:** 이번 무인 실행 지시가 **기존 대장 항목의 수정·재개봉·재작성을 금지**했다(항목의 상태와 처리는 오케스트레이터 소유). 그래서 #186을 in-place로 고치지 않고 정정 사실만 신규 항목으로 남긴다.
- **트리거:** **Story 12.3 스펙 작성 시** — #186을 집어드는 그 자리에서 이 항목을 함께 읽고, 12.4에 심을 인수조건은 "없는 요구를 새로 만든다"가 아니라 "이미 있는 요구(:930)에 NULL 구간 fallback 규칙을 더한다"로 잡는다.

### DW-490: [구 #190] CI 재현 환경에서 `tests/integration`은 이미 전량 초록이다 — "기존 red 1건"은 CI 상태가 아니라 로컬 스택의 GRANT 공백이었다

origin: 장부 통합 이관(구 docs/tech-debt.md #190) — 원출처: 2026-07-28 Story 12-1 3차 코드리뷰 실측, 🟡 기능, 기존 항목 무수정 정정
location: CI `api-db` 잡 재현(일회용 `pgvector/pgvector:pg17` + `scripts/migration-check-prelude.sql` + 마이그 0001~0022 전량) vs 로컬 Supabase Docker 스택(포트 55322).
severity: high
reason: CI 재현 컨테이너에서는 `tests/integration` 53건이 이미 전부 통과하고, 로컬에서만 나던 실패는 CI 상태가 아니라 로컬 스택에만 있는 `profiles` 테이블 anon 권한 공백(로컬 db reset이 플랫폼 기본 GRANT를 남기지 않음) 때문이었다.
trigger: **`test/bmad-loop`을 `develop`에 병합하기 직전**(`#181`의 ②단계) — 병합 후 CI가 실제로 초록인지 확인한다. 초록이면 `#138`·`#180`을 닫고, 아니면 여기서 다시 본다. 로컬 스택으로 `api-db`를 대신 검증하는 것은 이 실측 이후로 금지한다(결과가 다르다는 것이 증명됐다).
status: open

- **위치:** CI `api-db` 잡 재현(일회용 `pgvector/pgvector:pg17` + `scripts/migration-check-prelude.sql` + 마이그 0001~0022 전량) vs 로컬 Supabase Docker 스택(포트 55322).
- **내용(추측 아니라 실측):** CI 재현 컨테이너에서 `pytest tests/integration` → **53 passed, 0 failed**. 두 축 모두 이미 해소돼 있다 — `#180`의 테스트는 `test_anon_can_select_whitelisted_columns_including_view_count`로 **이미 교정돼 있고**(0021 이후 사양에 맞춰진 이름), `#138`의 `test_anon_can_read_joined_at_despite_profiles_rls`도 **통과한다**. 반면 **로컬 스택에서는 후자가 `InsufficientPrivilege: permission denied for table profiles`로 실패**한다. 원인은 권한 차이다: `has_table_privilege('anon','public.profiles','SELECT')`가 CI 재현 컨테이너에서는 **t**, 로컬 스택에서는 **f**(대장 `#120`과 같은 축 — 로컬 `db reset`이 플랫폼 기본 GRANT를 남기지 않는다).
- **왜 중요한가:** 12-1의 1·2차 패스가 로컬 스택에서 돌린 결과(`51 passed, 1 failed`)를 *"이미 대장 #138에 등재된 기존 red"* 로 보고했다. **귀속이 틀렸다** — #138이 기록한 증상은 `DID NOT RAISE InsufficientPrivilege`(권한이 **있어서** 안 나던 것)인데, 실제 로컬 실패는 정반대인 `permission denied`(권한이 **없어서** 나는 것)다. 즉 "알려진 red"로 넘긴 신호가 실제로는 검증 환경이 CI와 다르다는 별개 사실이었다. 로컬 스택은 `api-db` 잡의 대역이 될 수 없다.
- **선행조건 축에 주는 의미:** `#138`·`#180`·`#181`이 전부 *"Epic 12 착수 전 선행"* 을 트리거로 달고 있는데, 그중 **테스트 축 2건(#138·#180)은 이미 충족된 것으로 실측된다.** 남는 것은 `#181`의 **관측 축** — `test/bmad-loop`이 push되지 않아 CI가 Epic 11·12 작업을 아직 한 번도 본 적이 없다는 사실(`git rev-list --left-right --count origin/develop...HEAD` → `0 2`, `origin/test/bmad-loop`도 baseline에 머물러 있음).
- **왜 기존 항목을 안 고쳤나:** 이번 실행 지시가 기존 대장 항목 수정을 금지했다. `#138`·`#180`을 `✅ 해소`로 닫는 판단은 **오케스트레이터/사용자 몫**으로 남긴다 — 이 항목은 그 판단에 쓸 실측만 제공한다.
- **트리거:** **`test/bmad-loop`을 `develop`에 병합하기 직전**(`#181`의 ②단계) — 병합 후 CI가 실제로 초록인지 확인한다. 초록이면 `#138`·`#180`을 닫고, 아니면 여기서 다시 본다. 로컬 스택으로 `api-db`를 대신 검증하는 것은 이 실측 이후로 금지한다(결과가 다르다는 것이 증명됐다).

### DW-491: [구 #191] 에이전트 세션이 **공유 `.venv`를 부수고 원복하지 않는다** — 그 뒤 모든 스토리의 verify 게이트가 조용히 깨진다

origin: 장부 통합 이관(구 docs/tech-debt.md #191) — 원출처: 2026-07-29 Epic 12 실행 중 실측, 🔴 필수
location: `api/.venv`(레포 밖 산출물이지만 `[verify]` 게이트의 첫 명령 `cd api && .venv/bin/python -m pytest -q`가 여기에 의존) · `.bmad-loop/policy.toml`의 `[verify] commands`.
severity: critical
reason: 환경 자체는 즉시 복구했다(`websockets 15.0.1`, `pip check` 충돌 0). 남은 것은 **재발 방지**인데, 두 가지 축 중 무엇을 택할지 판단이 필요하다: (a) 규칙 축 — CLAUDE.md/스킬 프롬프트에 "환경도 원복" 조항을 넣는다(주석·문서는 계약이 아니다, B9 — 약함) · (b) 구조 축 — verify 게이트 앞에 **환경 무결성 검사**(`pip check` + 핵심 import 스모크)를 넣어 **깨진 환경을 코드 실패로 오인하지 않게** 한다(B9에 맞음, 다만 게이트가 느려지고 "환경 실패"와 "코드 실패"를 엔진이 구분해 주지 않으면 이월 처리가 여전히 잘못된다).
trigger: **Epic 12 재개 직전**(같은 일이 남은 4스토리에서 반복될 수 있다) — 최소한 (b)의 값싼 판본, 즉 `[verify] commands` 맨 앞에 `bash -lc 'cd api && .venv/bin/pip check'`를 넣는 것부터 검토한다. 그리고 **Epic 12 회고에서 (a)/(b) 중 어느 축으로 못박을지 결정**한다.
status: open

- **위치:** `api/.venv`(레포 밖 산출물이지만 `[verify]` 게이트의 첫 명령 `cd api && .venv/bin/python -m pytest -q`가 여기에 의존) · `.bmad-loop/policy.toml`의 `[verify] commands`.
- **무슨 일이 있었나(로그 원문):** Epic 12 Story 12-2의 **리뷰 세션(review-1)** 이 이렇게 실행했다.
  ```
  pip uninstall -y -q websockets
  ```
  의존성 가정을 시험하려는 의도로 보이나 **되돌리지 않았다.** `websockets`는 `langsmith`·`realtime`·`langgraph-sdk`·`google-genai`·`langgraph-api` **5개 패키지가 요구**하는 전이 의존성이라, 사라지자 `app.main` → `routers.ai` → `graph.graph` → `langgraph` 체인의 import가 죽어 **`api` 테스트 11개 파일이 수집 단계에서 전멸**했다(`ModuleNotFoundError: No module named 'websockets'`, `11 errors during collection`).
- **왜 위험한가:** 이 명령은 `[verify]`의 **첫 번째 게이트**다. 그러므로 이 시점 이후의 **모든 스토리가 코드와 무관하게 verify에서 막힌다** — 그리고 `[scm] rollback_on_failure = true`라 막힌 스토리는 **자동 롤백 + 이월**된다. 즉 한 세션의 환경 오염이 **에픽 전체를 조용히 무너뜨릴 수 있다.** 실제로 12-2가 이월됐고(작업물 자체는 멀쩡했다 — 아래), 12-3이 그 위에서 시작하던 중 사람이 멈췄다.
- **실측으로 갈랐다(코드 결함 아님):** 이월된 12-2의 보존 브랜치(`attempt-preserve/20260728-203648-2fc6-808e3ab1`, 3커밋 1,289줄)를 체크아웃해 재보니 **똑같이 깨졌고**, **베이스라인(`fbdd5a0`, 12-1 완료 시점)으로 돌아가도 똑같이 깨졌다** → 코드가 아니라 환경이다. `websockets<16`(15.0.1) 재설치 후 베이스라인 `206 passed`, 12-2 보존본은 **5개 게이트 전부 통과**(api 209 passed / lint 0 / vitest 239 / flutter analyze 0 issues / flutter test 80).
- **뿌리는 규칙의 공백이다:** CLAUDE.md B4가 *"검증용 데이터는 넣고 반드시 원복한다"* 고 못박은 것은 **DB 데이터**뿐이다. **실행 환경(패키지·전역 설정)에는 같은 규칙이 없다.** 에이전트는 "테스트를 위해 잠깐 지웠다가 되돌린다"를 데이터에선 지키지만 환경에선 안 지킨다 — 지키라고 적힌 적이 없기 때문이다.
- **왜 지금 안 고치나:** 환경 자체는 즉시 복구했다(`websockets 15.0.1`, `pip check` 충돌 0). 남은 것은 **재발 방지**인데, 두 가지 축 중 무엇을 택할지 판단이 필요하다: (a) 규칙 축 — CLAUDE.md/스킬 프롬프트에 "환경도 원복" 조항을 넣는다(주석·문서는 계약이 아니다, B9 — 약함) · (b) 구조 축 — verify 게이트 앞에 **환경 무결성 검사**(`pip check` + 핵심 import 스모크)를 넣어 **깨진 환경을 코드 실패로 오인하지 않게** 한다(B9에 맞음, 다만 게이트가 느려지고 "환경 실패"와 "코드 실패"를 엔진이 구분해 주지 않으면 이월 처리가 여전히 잘못된다).
- **✎ 2026-07-29 추가 발견 — 이월 사유 문구가 원인을 가린다(같은 사고의 두 번째 얼굴):** 이 사고를 진단하는 데 시간이 걸린 이유는 엔진이 남긴 사유가 **`"review did not converge within budget (still recommending a follow-up pass)"`** 였기 때문이다. 그 문구만 보면 "리뷰 사이클을 늘려야 하나?"로 읽힌다 — 실제로 그렇게 오독해서 `max_review_cycles`를 올리는 안을 세웠다가 사용자가 되물어 바로잡았다. **엔진 소스 실측**(`engine.py:1631` 주변)으로 확정한 진짜 분기는 이것이다:
  ```python
  if refileable_followup and not self._isolated and self._verify_review(task).ok:
      self._record_review_budget_followup(task); self._commit(task); return   # ← 12-1이 탄 길
  self._defer(task, "review did not converge within budget (...)")            # ← 12-2가 탄 길
  ```
  두 스토리의 **유일한 차이는 `_verify_review(task).ok`**(= frontmatter status==done AND sprint==done AND **verify 명령 통과**)였다. 즉 12-1·12-2 **둘 다** 리뷰 2회를 돌고 **둘 다** "후속 필요"라고 했지만, 12-1은 검증이 초록이라 *"예산 소진 → 커밋하고 후속은 deferred-work로 이관"* 으로 갔고 12-2는 검증이 빨간불이라 이월됐다. **리뷰 사이클 수는 애초에 원인이 아니었다.** 소스 주석은 이 경우를 *"(b) … verify failing: a genuine failure"* 로 명확히 구분해 두었는데 **사유 문구엔 그게 드러나지 않는다.**
  아울러 같은 오독을 유발한 것이 하나 더 있다: `[token-budget-exceeded]`(12-1, weighted 9.92M > 상한 2M). 이건 `advance(task, Phase.DONE)` **이후에** 찍히는 **순수 로그**이고 뒤에 어떤 분기도 없다(`engine.py:1696`) — 아무것도 멈추지 않는다. `max_tokens_per_story`는 현재 **관측 신호일 뿐 제어값이 아니다**(다만 매 스토리가 5배씩 넘겨 신호로서도 무의미해진 상태다).
- **트리거:** **Epic 12 재개 직전**(같은 일이 남은 4스토리에서 반복될 수 있다) — 최소한 (b)의 값싼 판본, 즉 `[verify] commands` 맨 앞에 `bash -lc 'cd api && .venv/bin/pip check'`를 넣는 것부터 검토한다. 그리고 **Epic 12 회고에서 (a)/(b) 중 어느 축으로 못박을지 결정**한다.

### DW-493: [구 #193] `#185`(마이그레이션 게이트 프로브가 chat/realtime을 안 봄)의 트리거가 도래했다 — 프로브 확장 대신 전용 실DB 테스트로 대체하기로 판단

origin: 장부 통합 이관(구 docs/tech-debt.md #193) — 원출처: 2026-07-28 Story 12-2, 🟢 품질, 기존 항목 무수정
location: `#185`의 트리거 문구("chat 관련 마이그레이션에 GRANT/RLS처럼 프로브가 실측 확인해야 할 축(예: `realtime.messages` 정책, Story 12.2)이 새로 생길 때") vs `supabase/migrations/0023_chat_realtime_broadcast.sql`(정확히 그 축 — `realtime.messages`의 참가자 한정 SELECT 정책).
severity: medium
reason: `#185`가 예고한 트리거(chat/realtime 마이그레이션)가 이번 스토리에서 실제로 왔고, 대응은 게이트 프로브 확장이 아니라 전용 실DB 통합테스트(`test_chat_realtime_broadcast_real_db.py`) 신설로 판단했다.
trigger: 다음 chat/realtime 관련 마이그레이션이 GRANT/RLS 축을 또 건드릴 때 — 그때도 "프로브 확장 vs 전용 테스트" 판단을 반복할지, 아니면 이번까지 누적된 사례(12.1·12.2)를 근거로 `check_migrations.py`에 실제로 프로브를 추가할지를 그 자리에서 다시 결정한다(지금은 후자로 옮길 만큼의 누적이 아니라고 본 판단이다).
status: open

- **위치:** `#185`의 트리거 문구("chat 관련 마이그레이션에 GRANT/RLS처럼 프로브가 실측 확인해야 할 축(예: `realtime.messages` 정책, Story 12.2)이 새로 생길 때") vs `supabase/migrations/0023_chat_realtime_broadcast.sql`(정확히 그 축 — `realtime.messages`의 참가자 한정 SELECT 정책).
- **내용:** #185가 예고한 트리거가 이번 스토리(12.2)에서 실제로 왔다. 대응은 `scripts/check_migrations.py`의 정적 프로브 3종(listings/guide_documents 고정 목록)을 확장하는 것이 아니라 — 그건 이 스토리 범위를 넘는 별도 게이트 인프라 변경이다 — `api/tests/integration/test_chat_realtime_broadcast_real_db.py`로 대체했다(스펙 Design Notes에 이미 근거가 적혀 있다: 12.1이 자신의 제약도 프로브가 아닌 전용 실DB 테스트로 검증한 전례). 이 전용 테스트는 트리거 발동(방송 행 생성)과 RLS(당사자 허용/제3자 차단) 둘 다 `set local role authenticated` + `request.jwt.claim.sub` + `set local realtime.topic`으로 실제 인가 경로를 재현해 확인한다 — 정적 프로브(존재 여부만 봄)보다 오히려 신뢰도가 높다(B4 "존재 확인은 작동 확인이 아니다"). 이 판단으로 `#185`는 "아직 안 옴"에서 "왔고, 처리 방식을 골랐다"로 넘어갔지만, 게이트 자체의 커버리지 갭(#185 원문의 지적)은 여전히 남아 있다 — 이번 결정은 "이 트리거는 프로브가 아니라 전용 테스트로 받는다"는 정책 판단이지, 게이트를 넓힌 게 아니다.
- **왜 기존 항목(`#185`)을 안 고쳤나:** 이번 무인 실행 지시가 기존 대장 항목의 수정·재개봉·재작성을 금지했다(항목의 상태와 처리는 오케스트레이터/사용자 소유). 그래서 `#185`를 닫거나 고치지 않고 처리 판단만 신규 항목으로 남긴다.
- **트리거:** 다음 chat/realtime 관련 마이그레이션이 GRANT/RLS 축을 또 건드릴 때 — 그때도 "프로브 확장 vs 전용 테스트" 판단을 반복할지, 아니면 이번까지 누적된 사례(12.1·12.2)를 근거로 `check_migrations.py`에 실제로 프로브를 추가할지를 그 자리에서 다시 결정한다(지금은 후자로 옮길 만큼의 누적이 아니라고 본 판단이다).

### DW-494: [구 #194] `#188`(conftest.py 부재)이 이번 스토리로 "해소"된 것으로 오독되면 안 된다 — 신규 `conftest.py`는 새 파일 1개만 쓰고, 기존 5개는 여전히 복제 상태다

origin: 장부 통합 이관(구 docs/tech-debt.md #194) — 원출처: 2026-07-28 Story 12-2, 🟢 품질, 기존 항목 무수정
location: `api/tests/integration/conftest.py`(신설) vs `#188`이 지목한 5개 파일(`test_fr11_cover_images_real_db.py`·`test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`·`test_view_count_rpc_real_db.py`·`test_chat_idempotency_real_db.py`).
severity: medium
reason: 기존 5개 파일을 `conftest.py`로 옮기는 것은 이번 스토리(12.2)가 만들지 않은 파일 4개를 함께 고치는 일이라 "바뀐 줄이 요청에 추적된다"(A3 외과적 변경)를 어긴다 — `#188`이 이미 같은 이유로 이관을 미뤄뒀다.
trigger: **다음 실DB 통합 테스트 파일을 추가할 때**(Epic 12 남은 스토리 중 유력) — 그 자리에서 기존 5개 + 신규 1개(이번 스토리의 `test_chat_realtime_broadcast_real_db.py`) 전부를 `conftest.py`로 전체 이관할지 다시 판단한다. 파일이 6개→7개로 늘어날수록 "그때 옮긴다"는 판단의 근거(복제 비용)가 커진다.
status: open

- **위치:** `api/tests/integration/conftest.py`(신설) vs `#188`이 지목한 5개 파일(`test_fr11_cover_images_real_db.py`·`test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`·`test_view_count_rpc_real_db.py`·`test_chat_idempotency_real_db.py`).
- **내용:** 이번 스토리(12.2)가 `#188`의 트리거("실DB 통합 테스트 파일을 하나 더 추가할 때")를 충족시켜 `conftest.py`를 만들었지만, **소비하는 곳은 신규 파일 `test_chat_realtime_broadcast_real_db.py` 하나뿐이다.** 기존 5개 파일은 스펙 범위 밖이라 옮기지 않았고(스펙 Always 절 — "기존 5개 파일은 이번 스토리 범위 밖이라 그대로 둔다"), 각자 자기 `_create_user`/`_insert_listing`/skip 가드 사본을 그대로 갖고 있다. 즉 `#188`이 지적한 **복제 자체는 여전히 5곳에 남아 있다** — 그중 하나(`test_chat_idempotency_real_db.py`)가 12.1에서 실제로 만들었던 role 하드코딩류 결함(형제 파일을 옮겨쓰다 판매자 유저에도 `role="buyer"`를 박은 사례, `#188` 본문 참조)이 재발할 수 있는 표면은 이번 조치로 줄지 않았다. `conftest.py`가 존재한다는 사실만으로 `#188`을 "해소됨"으로 읽으면 안 된다 — 파일이 생긴 것과 복제가 없어진 것은 다른 사실이다.
- **왜 지금 안 고치나:** 기존 5개 파일을 `conftest.py`로 옮기는 것은 이번 스토리(12.2)가 만들지 않은 파일 4개를 함께 고치는 일이라 "바뀐 줄이 요청에 추적된다"(A3 외과적 변경)를 어긴다 — `#188`이 이미 같은 이유로 이관을 미뤄뒀다.
- **왜 기존 항목(`#188`)을 안 고쳤나:** 이번 실행 지시가 기존 대장 항목의 수정·재개봉·재작성을 금지했다. `#188`을 닫거나 고치지 않고 범위 정정만 신규 항목으로 남긴다.
- **트리거:** **다음 실DB 통합 테스트 파일을 추가할 때**(Epic 12 남은 스토리 중 유력) — 그 자리에서 기존 5개 + 신규 1개(이번 스토리의 `test_chat_realtime_broadcast_real_db.py`) 전부를 `conftest.py`로 전체 이관할지 다시 판단한다. 파일이 6개→7개로 늘어날수록 "그때 옮긴다"는 판단의 근거(복제 비용)가 커진다.

### DW-495: [구 #195] Realtime Broadcast 전달 실패가 조용히 삼켜지거나(플랫폼 `realtime.send()`) 트랜잭션 전체를 되돌린다(`realtime.broadcast_changes()` 자체가 못 불릴 때) — 어느 쪽도 관측되지 않는다

origin: 장부 통합 이관(구 docs/tech-debt.md #195) — 원출처: 2026-07-28 Story 12-2 코드리뷰 adversarial+edge-case 교차 지적, 🟡 기능, defer
location: `supabase/migrations/0023_chat_realtime_broadcast.sql`의 `public.chat_messages_broadcast()`(트리거 함수, `realtime.broadcast_changes()` 호출부에 예외 처리 없음) + Supabase 플랫폼의 `realtime.send()`(이 스토리가 만든 게 아니라 플랫폼이 배포하는 실제 함수 — `scripts/migration-check-prelude.sql`의 신규 스텁이 원본 그대로 복사해 그 특성이 드러났다: 내부에서 `exception when others then raise warning`으로 모든 실패를 흡수하고 재전파하지 않는다).
severity: high
reason: ①은 Supabase 플랫폼 자체 함수라 이 레포에서 고칠 수 있는 대상이 아니다(스텁은 원본 재현이 목적이라 다르게 만들면 게이트 신뢰도가 떨어진다). ②는 지금 예외 처리를 추가하는 게 오히려 "일어날 수 없는 시나리오에 방어 코드를 두지 말라"(CLAUDE.md A2)와 충돌할 수 있다 — Realtime이 꺼진 상태는 스펙의 Block If가 이미 "배포 전 사용자 확인"으로 잡아둔 전제조건이라, 그 전제가 깨진 뒤의 동작까지 지금 설계하는 건 범위 밖이다.
trigger: **Story 12.3(폴링 제거) 착수 시** — 방송이 유일한 전달 경로가 되는 시점이므로, 그 자리에서 최소한 ①의 관측 수단(예: 방송 실패율을 보는 로그 알람, 또는 클라이언트 측 "메시지는 저장됐지만 실시간 반영이 안 됨" 감지)이 필요한지 재판단한다. ②는 그 전에 원격 프로젝트의 Realtime 활성화 상태를 사용자가 확인하면(스펙 Block If) 실질적으로 닫힌다.
status: open

- **위치:** `supabase/migrations/0023_chat_realtime_broadcast.sql`의 `public.chat_messages_broadcast()`(트리거 함수, `realtime.broadcast_changes()` 호출부에 예외 처리 없음) + Supabase 플랫폼의 `realtime.send()`(이 스토리가 만든 게 아니라 플랫폼이 배포하는 실제 함수 — `scripts/migration-check-prelude.sql`의 신규 스텁이 원본 그대로 복사해 그 특성이 드러났다: 내부에서 `exception when others then raise warning`으로 모든 실패를 흡수하고 재전파하지 않는다).
- **내용:** 두 갈래 실패 경로가 있고 둘 다 관측되지 않는다. ① `realtime.send()`가 내부적으로 실패(권한·제약·디스크 등)하면 `raise warning`만 남기고 **삼켜진다** — 트리거를 호출한 `chat_messages` INSERT는 정상 커밋되고, 방송만 조용히 안 나간 채 아무도 모른다(플랫폼 자체 설계, 이 레포가 만든 게 아님). ② 반대로 `realtime.broadcast_changes()` 함수 자체가 호출 불가능한 상태(Realtime 확장 비활성화 등, 스펙 Block If가 이미 짚은 시나리오)면 `PERFORM` 호출이 함수 해석 단계에서 실패해 **트리거 함수 자신의 예외 처리 없이 그대로 전파** — `chat_messages` INSERT 자체가 롤백돼 채팅 저장까지 막힌다. **오늘 당장의 실사용 영향은 0이다** — Story 12.3 이전이라 폴링이 여전히 유일한 전달 경로이고, 이 브로드캐스트는 아직 아무도 구독하지 않는다. 12.3에서 폴링을 걷어내는 순간부터 ①은 "메시지는 저장됐는데 상대가 못 받음(무음 실패)"로, ②는 "Realtime이 잠깐 불안정하면 채팅 자체가 죽음"으로 실제 영향이 생긴다.
- **왜 지금 안 고치나:** ①은 Supabase 플랫폼 자체 함수라 이 레포에서 고칠 수 있는 대상이 아니다(스텁은 원본 재현이 목적이라 다르게 만들면 게이트 신뢰도가 떨어진다). ②는 지금 예외 처리를 추가하는 게 오히려 "일어날 수 없는 시나리오에 방어 코드를 두지 말라"(CLAUDE.md A2)와 충돌할 수 있다 — Realtime이 꺼진 상태는 스펙의 Block If가 이미 "배포 전 사용자 확인"으로 잡아둔 전제조건이라, 그 전제가 깨진 뒤의 동작까지 지금 설계하는 건 범위 밖이다.
- **트리거:** **Story 12.3(폴링 제거) 착수 시** — 방송이 유일한 전달 경로가 되는 시점이므로, 그 자리에서 최소한 ①의 관측 수단(예: 방송 실패율을 보는 로그 알람, 또는 클라이언트 측 "메시지는 저장됐지만 실시간 반영이 안 됨" 감지)이 필요한지 재판단한다. ②는 그 전에 원격 프로젝트의 Realtime 활성화 상태를 사용자가 확인하면(스펙 Block If) 실질적으로 닫힌다.

### DW-496: [구 #196] 0023이 서는 전제 3가지가 **원격에서만 답할 수 있는데 아직 안 물었다** — 스텁은 로컬 기준 실측이고, 실제 `realtime.messages`는 파티션 테이블이며, Realtime이 불가용하면 채팅 저장 자체가 막힌다

origin: 장부 통합 이관(구 docs/tech-debt.md #196) — 원출처: 2026-07-28 Story 12-2 후속 코드리뷰 실측, 🟡 기능, 기존 항목 무수정
location: `scripts/migration-check-prelude.sql`의 realtime 스텁(헤더가 "로컬 스택(:55322)에서 실측"이라고 스스로 밝힘) vs 같은 파일 상단 :7-9의 규칙("정당한 확장은 **원격에서 확인한 뒤** 그 사실을 주석에 남긴다") + `supabase/migrations/0023_chat_realtime_broadcast.sql`.
severity: high
reason: 셋 다 원격 프로젝트에 물어야 답이 나오고, 그 접근은 사용자 몫이다(이 레포는 `service_role` 키를 두지 않는다 — `conventions.md` §5). 스텁을 파티션 테이블로 바꾸는 것도 지금은 과설계다 — 이 레포의 마이그·테스트 어느 것도 파티셔닝에 의존하지 않고, 스텁의 목적은 게이트가 적용 실패로 죽지 않게 하는 것이지 플랫폼 장애를 재현하는 게 아니다.
trigger: **이 브랜치를 원격(개발 또는 운영) Supabase 프로젝트에 적용하기 직전.** 그 자리에서 사용자가 셋을 한 번에 확인한다 — ⓐ 프로젝트에 Realtime/Broadcast가 켜져 있는가(안 켜져 있으면 적용 즉시 채팅 저장이 죽는다), ⓑ 원격의 `pg_get_functiondef('realtime.send'::regproc)`가 프렐류드 스텁과 같은가(특히 `private` 기본값), ⓒ `realtime.messages`의 파티션 유지가 자동인가. 확인 결과는 프렐류드 헤더 주석에 원격 실측으로 갱신한다(:7-9 규칙 충족).
status: done 2026-07-29
resolution: 2026-07-29 원격 실측으로 ⓐⓑ 통과·ⓓ 성립. 잔여인 파티션 무음 실패는 DW-532(구 #232)가 승계. 근거는 scripts/migration-check-prelude.sql 헤더에 기록됨

- **위치:** `scripts/migration-check-prelude.sql`의 realtime 스텁(헤더가 "로컬 스택(:55322)에서 실측"이라고 스스로 밝힘) vs 같은 파일 상단 :7-9의 규칙("정당한 확장은 **원격에서 확인한 뒤** 그 사실을 주석에 남긴다") + `supabase/migrations/0023_chat_realtime_broadcast.sql`.
- **내용:** 세 가지가 한 축에 묶인다 — 전부 "CI·로컬에서는 구조적으로 확인할 수 없고 원격에서만 답이 나온다".
  - ① **스텁의 근거가 로컬이다.** 프렐류드 규칙은 원격 실측을 요구하는데 이번 realtime 스텁은 로컬 Supabase Docker 스택에서 `pg_get_functiondef`로 복사했다. 로컬·원격이 같은 realtime 확장이라는 전제는 합리적이지만 **확인된 사실은 아니다.** 특히 `realtime.send(payload, event, topic, private default true)`의 `private` 기본값이 원격 버전에서 다르면, 트리거는 인자 3개만 넘기므로 방송이 **공개 채널**로 나가고 이번에 만든 RLS는 관문이 아니게 된다.
  - ② **실제 `realtime.messages`는 `inserted_at` range 파티션 테이블이다**(로컬 실측: `relkind='p'`). 프렐류드 스텁은 평범한 테이블이라, 해당 날짜 파티션이 없을 때 나는 `no partition of relation "messages" found for row` 실패가 **CI에서는 구조적으로 일어날 수 없다.** 그 실패는 `realtime.send()`의 `exception when others then raise warning`에 삼켜져 "메시지는 저장되고 방송만 조용히 사라짐"이 된다(#194 ①의 구체적 발생 경로). 즉 `assert len(rows) == 1` 류의 단언은 그 실패 모드가 없는 땅 위에서만 참이 보장된다.
  - ③ **#194 ②의 "오늘 영향 0"은 배포 시점 기준으로는 틀리다.** 0023이 적용되는 순간부터 `chat_messages` INSERT는 `realtime.broadcast_changes()`가 호출 가능하다는 데 의존한다 — Realtime 확장이 없거나 꺼져 있으면 트리거가 예외를 그대로 올려 **메시지 저장 자체가 실패**한다. 폴링이 유일한 전달 경로라 "실시간이 안 되는 것"은 오늘 영향이 0이지만, "채팅이 아예 안 되는 것"은 12.3을 기다리지 않는다. 스펙 Block If가 같은 사실을 이미 짚고 있으므로 **새로운 위험이 아니라 시점의 정정**이다: 재판단 시점은 12.3 착수가 아니라 **원격 적용 직전**이다.
- **왜 지금 안 고치나:** 셋 다 원격 프로젝트에 물어야 답이 나오고, 그 접근은 사용자 몫이다(이 레포는 `service_role` 키를 두지 않는다 — `conventions.md` §5). 스텁을 파티션 테이블로 바꾸는 것도 지금은 과설계다 — 이 레포의 마이그·테스트 어느 것도 파티셔닝에 의존하지 않고, 스텁의 목적은 게이트가 적용 실패로 죽지 않게 하는 것이지 플랫폼 장애를 재현하는 게 아니다.
- **왜 기존 항목(`#195`)을 안 고쳤나:** 이번 실행 지시가 기존 대장 항목의 수정·재개봉·재작성을 금지했다. `#195`의 트리거(12.3 착수 시)를 고치지 않고, ③의 시점 정정을 여기 신규로 남긴다 — 둘 중 **먼저 오는 것은 이 항목의 트리거**다.
- **트리거:** **이 브랜치를 원격(개발 또는 운영) Supabase 프로젝트에 적용하기 직전.** 그 자리에서 사용자가 셋을 한 번에 확인한다 — ⓐ 프로젝트에 Realtime/Broadcast가 켜져 있는가(안 켜져 있으면 적용 즉시 채팅 저장이 죽는다), ⓑ 원격의 `pg_get_functiondef('realtime.send'::regproc)`가 프렐류드 스텁과 같은가(특히 `private` 기본값), ⓒ `realtime.messages`의 파티션 유지가 자동인가. 확인 결과는 프렐류드 헤더 주석에 원격 실측으로 갱신한다(:7-9 규칙 충족).
- **✅ 해소 (2026-07-29, 원격 실측 — 프렐류드 헤더에 갱신 완료):** 셋 다 물었다. **ⓐ 통과** — `pg_publication` supabase_realtime 1건 + `realtime.broadcast_changes()` 존재 + anon 키로 실제 채널 구독이 `SUBSCRIBED`. 따라서 ③의 최악(0023 적용 즉시 `chat_messages` 저장이 죽는다)은 **발생하지 않는다.** **ⓑ 통과** — 원격 `realtime.send`가 스텁과 동일하고 `private boolean DEFAULT true`다. ①이 우려한 "기본값이 다르면 공개 채널로 새어 RLS가 관문이 아니게 된다"는 **기각**. **ⓒ 부분 통과 → `#232`로 승계** — 원격도 range 파티션(`relkind='p'`)이 맞고 유지도 자동이지만 **"Realtime 테넌트가 활성일 때만"** 이다. 확인 시작 시점엔 파티션이 **0개**여서 ②가 말한 무음 실패가 **원격에서 실제로 재현됐다**(`23514 no partition ... found for row`, 롤백함). 클라이언트 1회 구독으로 5일치가 생성돼 지금은 정상이나, 그 조건부 위험은 `#232`가 갖는다.

### DW-497: [구 #197] 0023의 "INSERT 정책 불필요" 전제가 기대는 **BYPASSRLS는 원격에서 확인된 적이 없다** — `#196`의 원격 확인 목록에 이 항목이 빠져 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #197) — 원출처: 2026-07-28 Story 12-2 3차 코드리뷰 실측, 🟡 기능, 기존 항목 무수정·신규 등재
location: `supabase/migrations/0023_chat_realtime_broadcast.sql` 헤더(⚠️ "INSERT 정책이 필요 없는 이유") + `api/tests/integration/test_chat_realtime_broadcast_real_db.py` ⑧(`test_broadcast_function_is_security_definer_owned_by_bypassrls_role`).
severity: high
reason: 원격 프로젝트에 물어야만 답이 나온다(이 레포는 `service_role` 키를 두지 않는다 — `conventions.md` §5). 코드로 미리 막으려면 `realtime.messages`에 INSERT 정책을 하나 얹어야 하는데, 그건 스펙 Never 절이 명시적으로 금지한 것이고 필요 없을 가능성이 높은 상태에서 쓰기 표면을 넓히는 일이다(A2).
trigger: **`#196`와 동일 — 이 브랜치를 원격 Supabase 프로젝트에 적용하기 직전.** 그 자리에서 ⓓ를 하나 더 확인한다: 마이그레이션을 적용하는 롤로 `select rolbypassrls from pg_roles where rolname = current_user` → `t`인가(또는 적용 후 `public.chat_messages_broadcast()`의 소유자를 같은 질의로 확인). `f`라면 적용 전에 사용자와 상의한다 — 그 경우에만 INSERT 정책 추가를 재검토한다.
status: done 2026-07-29
resolution: 2026-07-29 원격 실측 — 적용 롤 postgres의 rolbypassrls=t 확인, 'INSERT 정책 불필요' 전제가 원격에서도 성립. 재확인 지점은 프렐류드 헤더 ⓓ

- **위치:** `supabase/migrations/0023_chat_realtime_broadcast.sql` 헤더(⚠️ "INSERT 정책이 필요 없는 이유") + `api/tests/integration/test_chat_realtime_broadcast_real_db.py` ⑧(`test_broadcast_function_is_security_definer_owned_by_bypassrls_role`).
- **내용:** 0023은 `realtime.messages`에 INSERT 정책을 두지 않는다. 방송 INSERT가 RLS를 통과하는 이유는 트리거 함수가 SECURITY DEFINER이고 **그 함수의 소유자(= 마이그레이션을 적용한 롤)가 `rolbypassrls`** 이기 때문이다. 즉 이 스토리의 쓰기 축 전체가 "적용 롤의 속성" 하나에 걸려 있다.
  - ⑧이 그 두 속성(`prosecdef` + 소유자의 `rolbypassrls`)을 실제로 조회하긴 한다. 하지만 **로컬·CI에서 함수 소유자는 언제나 `postgres` 슈퍼유저**라 `rolbypassrls=t`가 구조적으로 참이다 — 이 검사는 원격에서 돌지 않으므로, 원격 적용 롤이 그 속성을 갖지 않는 경우를 잡을 수 있는 자리가 아니다(실측: 로컬 `select rolbypassrls, rolsuper from pg_roles where rolname='postgres'` → `t, t`).
  - 실패하면 조용하다: 방송 INSERT가 RLS에 거부되고, 그 예외를 플랫폼 `realtime.send()`의 `exception when others then raise warning`이 삼킨다 → **메시지는 저장되는데 방송만 사라진다**(`#195` ①·`#196` ②와 같은 무음 실패 계열). 로컬에서 `security definer`를 떼어 이 경로를 실제로 재현한 기록이 테스트 ⑫ docstring에 있다.
- **왜 지금 안 고치나:** 원격 프로젝트에 물어야만 답이 나온다(이 레포는 `service_role` 키를 두지 않는다 — `conventions.md` §5). 코드로 미리 막으려면 `realtime.messages`에 INSERT 정책을 하나 얹어야 하는데, 그건 스펙 Never 절이 명시적으로 금지한 것이고 필요 없을 가능성이 높은 상태에서 쓰기 표면을 넓히는 일이다(A2).
- **`#196`와의 관계:** 같은 축(원격에서만 답할 수 있는 0023의 전제)이고 **확인 시점도 같다.** `#196`의 목록이 ⓐ Realtime 활성화 · ⓑ `realtime.send` 정의 · ⓒ 파티션 유지 셋뿐이라 이 항목이 빠져 있는데, 기존 항목은 수정하지 않는 규칙이라 여기 신규로 남긴다. 원격 확인 때 **`#196`와 함께 한 번에 처리**할 것.
- **트리거:** **`#196`와 동일 — 이 브랜치를 원격 Supabase 프로젝트에 적용하기 직전.** 그 자리에서 ⓓ를 하나 더 확인한다: 마이그레이션을 적용하는 롤로 `select rolbypassrls from pg_roles where rolname = current_user` → `t`인가(또는 적용 후 `public.chat_messages_broadcast()`의 소유자를 같은 질의로 확인). `f`라면 적용 전에 사용자와 상의한다 — 그 경우에만 INSERT 정책 추가를 재검토한다.
- **✅ 해소 (2026-07-29, 원격 실측):** 원격에서 `select current_user, rolbypassrls, rolsuper from pg_roles where rolname = current_user` → **`postgres` / `rolbypassrls=t` / `rolsuper=f`**. 즉 적용 롤이 슈퍼유저는 아니지만 BYPASSRLS는 갖고 있어, 0023이 `realtime.messages`에 INSERT 정책을 두지 않는 전제가 **원격에서도 성립한다.** 스펙 Never 절(INSERT 정책 추가 금지)을 어길 이유가 없다. **다만 이 속성은 적용 롤에 딸린 것이라 롤이 바뀌면 다시 물어야 하고**, 실패해도 조용하다는 성질은 그대로다 — 그 재확인 지점을 프렐류드 헤더 ⓓ에 남겼다.

### DW-498: [구 #198] Story 12.3 — 실시간 구독·전송을 웹만 채우고 앱(`app/lib/features/chat/**`)은 손대지 않기로 판단

origin: 장부 통합 이관(구 docs/tech-debt.md #198) — 원출처: 2026-07-29 Story 12-3, 🟢 품질, 기존 항목 무수정
location: `_bmad-output/implementation-artifacts/spec-12-3-실시간-송수신-전환-폴링-제거.md`의 Design Notes 첫 문단("왜 웹 한정인가") vs `docs/tech-debt.md` #186 본문("Story 12.3·12.4의 인수조건이 client_message_id를 요구하지 않는다"는 제목 아래 "web·app 양쪽"이라는 언급) vs 에픽 문서의 Epic 16 Story 16.4 소개.
severity: medium
reason: 에픽 문서가 이미 앱 쪽 실시간 채팅을 별도 스토리(Epic 16 Story 16.4)로 분리해 두었으므로, 이번 스토리(12.3)는 Epic 12가 놓는 DB 토대(멱등키·Broadcast+RLS)만 웹에서 완성하면 된다고 판단했다.
trigger: Epic 16 착수 시(Story 16.4) — 그 자리에서 `docs/conventions.md` §12(이번 스토리가 신설한 구독 토픽·private+setAuth·payload 파싱·멱등 전송 계약)를 Dart로 그대로 미러링한다. 웹 쪽 계약이 이 문서 §12로 이미 단일 출처화돼 있으므로, 16.4는 "무엇을 따라야 하는지"를 처음부터 다시 규명할 필요가 없다.
status: done 2026-07-29
resolution: DW-486(구 #186)의 전제를 바로잡는 정정 메모라 원항목에 병합 — epics-increment에 Story 16.4(앱 채팅)가 별도로 존재함을 확인

- **위치:** `_bmad-output/implementation-artifacts/spec-12-3-실시간-송수신-전환-폴링-제거.md`의 Design Notes 첫 문단("왜 웹 한정인가") vs `docs/tech-debt.md` #186 본문("Story 12.3·12.4의 인수조건이 client_message_id를 요구하지 않는다"는 제목 아래 "web·app 양쪽"이라는 언급) vs 에픽 문서의 Epic 16 Story 16.4 소개.
- **내용:** #186이 쓰인 시점엔 "web·app 양쪽"을 전제한 문구가 있었지만, 에픽 문서는 이미 Epic 16 Story 16.4를 "실시간 채팅(앱)"으로 분리해뒀고 16.4 자신이 "Realtime Broadcast·멱등키·chat_room_reads(Epic 12)"를 **전제조건으로 인용**한다 — 즉 12.3이 완성하는 것은 앱이 나중에 그대로 가져다 쓸 **웹 코드**가 아니라 Epic 12가 놓은 **DB 토대**(0022 멱등키, 0023 Broadcast+RLS)다. Epic 12의 어느 스토리 인수조건에도 앱 파일이 등장하지 않고, Epic 16 소개도 "웹 기능이 안정된 뒤 미러링"이라 명시한다. 그래서 이번 스토리는 `web/**`(`ChatRoomMessages.tsx`·`messages.ts`)만 고치고 Flutter 쪽(`app/lib/features/chat/**`)은 그대로 뒀다 — 스펙 Never 절이 이를 명시적으로 못박았다.
- **왜 기존 항목(`#186`)을 안 고쳤나:** 대장 항목은 그 항목이 등재된 시점의 판단을 담는 기록이고, 지금 필요한 것은 "그 이후 상황이 어떻게 달라졌는가"를 새로 남기는 것이지 과거 기록을 소급해 고치는 것이 아니다(B8 — 문서는 경위/제약을 섞지 않는다). `#186`의 본문·트리거는 그대로 두고, 이번 판단 근거만 신규 항목으로 남긴다.
- **트리거:** Epic 16 착수 시(Story 16.4) — 그 자리에서 `docs/conventions.md` §12(이번 스토리가 신설한 구독 토픽·private+setAuth·payload 파싱·멱등 전송 계약)를 Dart로 그대로 미러링한다. 웹 쪽 계약이 이 문서 §12로 이미 단일 출처화돼 있으므로, 16.4는 "무엇을 따라야 하는지"를 처음부터 다시 규명할 필요가 없다.
- ✎ **2026-07-29 Story 12.6 재확인.** 스펙(spec-12-6) AC가 "Flutter 앱의 채팅 화면이 이번 실시간 검증과 비교해 여전히 폴링 기반임을 확인·기록"을 요구해 `app/lib/features/chat/chat_room_screen.dart`를 다시 읽었다 — `Timer.periodic(_pollInterval, ...)`(3초 폴링), 재연결 배너·오프라인 큐·갭보정 없음, 이 항목이 서술한 상태와 동일. 코드 변경 없음(참고 확인만, 스펙 Never 절 — 이번 스토리는 앱에 실시간을 구현하지 않는다).

### DW-499: [구 #199] `#195` 재판단(트리거 도래) — Story 12.3(폴링 제거) 착수 시점에도 브로드캐스트 실패율 관측 인프라를 만들지 않기로 결정

origin: 장부 통합 이관(구 docs/tech-debt.md #199) — 원출처: 2026-07-29 Story 12-3, 🟡 기능, defer, 기존 항목 무수정
location: `docs/tech-debt.md` #195의 트리거 문구("Story 12.3(폴링 제거) 착수 시 — ... 그 자리에서 최소한 ①의 관측 수단이 필요한지 재판단한다") vs 스펙 Design Notes 두 번째 문단("#195 재판단(트리거 도래)").
severity: high
reason: `#195`가 예고한 트리거(12.3 착수)가 왔지만, 재연결 갭보정(12.4)이 유실을 닫고 순수 실패는 원격 전제에 걸린 비-코드 결함이며 새로고침 시 전체 재조회가 안전망으로 남는다는 세 근거로 여전히 관측 인프라를 만들지 않기로 재확인했다.
trigger: 다음으로 이 축을 다시 여는 시점은 둘 중 하나다 — ① Story 12.4(재연결 갭보정) 구현 중 "그래도 관측이 필요한가"가 다시 논의될 때, 또는 ② 원격 배포 후(`#196`·`#197`의 확인 시점) 실제로 "메시지는 저장됐는데 상대가 못 받았다"는 신고가 들어올 때 — 그 자리에서 최소 관측 수단(예: 클라이언트 측 "실시간 반영 지연 감지" 또는 서버 로그 기반 실패율)을 다시 판단한다.
status: open

- **위치:** `docs/tech-debt.md` #195의 트리거 문구("Story 12.3(폴링 제거) 착수 시 — ... 그 자리에서 최소한 ①의 관측 수단이 필요한지 재판단한다") vs 스펙 Design Notes 두 번째 문단("#195 재판단(트리거 도래)").
- **내용:** #195가 예고한 트리거가 이번 스토리에서 실제로 왔다. 재판단 결과는 "여전히 만들지 않는다"다 — 근거 셋: (1) **바로 다음 Story 12.4**가 재연결 갭보정(끊긴 동안 놓친 메시지를 커서로 재조회)을 붙이므로, 연결이 끊겼다 다시 붙는 경로의 유실은 그 스토리가 닫는다. (2) 연결이 살아있는데 방송만 조용히 안 오는 **순수 실패**는 원격 전제(`#195` ①·`#196`·`#197` — 원격 `realtime.send()`의 삼킴, 파티션 유지, BYPASSRLS 여부)에 걸려 있어 로컬·CI에서 재현 가능한 **코드 결함이 아니다**. (3) 방 최초 진입 시 전체 조회(`fetchMessages`, 커서 없음)는 폴링 제거 후에도 그대로 유지해, 방을 새로고침하면 언제든 최신 상태로 복구된다 — 방송이 조용히 실패해도 사용자가 "새로고침하면 늦게라도 보인다"는 안전망이 남는다.
- **왜 기존 항목(`#195`)을 안 고쳤나:** `#195`의 트리거 문구·본문은 그대로 두고, 트리거가 도래한 뒤의 재판단 근거만 신규 항목으로 남긴다(B8 — 경위는 새 항목에, 기존 기록은 그대로).
- **트리거:** 다음으로 이 축을 다시 여는 시점은 둘 중 하나다 — ① Story 12.4(재연결 갭보정) 구현 중 "그래도 관측이 필요한가"가 다시 논의될 때, 또는 ② 원격 배포 후(`#196`·`#197`의 확인 시점) 실제로 "메시지는 저장됐는데 상대가 못 받았다"는 신고가 들어올 때 — 그 자리에서 최소 관측 수단(예: 클라이언트 측 "실시간 반영 지연 감지" 또는 서버 로그 기반 실패율)을 다시 판단한다.

### DW-500: [구 #200] 관리자 대화 열람 화면이 채팅 본문을 `break-words` 없이 렌더한다 — 사용자 화면에서 실측으로 닫은 `#169`(390px 가로 오버플로)가 같은 데이터로 관리자 쪽에만 남았다

origin: 장부 통합 이관(구 docs/tech-debt.md #200) — 원출처: 2026-07-29 Story 12-3 후속 코드리뷰 verification-gap 지적, 🟢 품질, defer
location: `web/src/app/(admin)/admin/chats/[roomId]/page.tsx:161` — `<span className="whitespace-pre-wrap text-sm">{m.body}</span>`.
severity: medium
reason: 관리자 대화 열람 화면이 사용자 채팅방과 같은 `chat_messages.body`를 렌더하면서도 `break-words`가 없어, 사용자 화면에서 이미 고친 것과 같은 390px 가로 오버플로 결함이 그대로 남아 있다.
trigger: 관리자 화면(`app/(admin)/**`)을 다음에 손대는 스토리 착수 시 — 그 자리에서 `break-words`를 적용하고 `messageBubbleWrap.test.ts`의 스캔 대상에 이 파일을 추가한다. 관리자 반응형은 D5(반응형 UI 무결성)가 "관리자 화면도 예외 없음"이라 이미 못박고 있으므로 별도 판단이 필요 없다.
status: open

- **위치:** `web/src/app/(admin)/admin/chats/[roomId]/page.tsx:161` — `<span className="whitespace-pre-wrap text-sm">{m.body}</span>`.
- **내용:** Story 12.3 후속 리뷰가 사용자 채팅방(`ChatRoomMessages.tsx`)에서 "공백 없는 긴 본문(붙여넣은 URL 등)이 버블 밖으로 넘친다"를 **실측으로 재현**(390px에서 `scrollWidth 672 > clientWidth 390`)하고 버블 3곳에 `break-words`를 적용해 닫았다. 관리자 대화 열람 화면은 **같은 `chat_messages.body`** 를 렌더하는데 줄바꿈 규칙이 없어 같은 결함이 그대로 있다. 본문 길이 상한은 `CHAT.MESSAGE_MAX_LENGTH`(2000자)이므로 공백 없는 긴 문자열은 실제로 들어올 수 있다.
- **실측:** `grep -rn 'break-words|break-all' web/src --include=*.tsx` → 이번 스토리가 넣은 `ChatRoomMessages.tsx` 3곳뿐. 관리자 화면을 여는 검사도 없다 — `web/e2e/core-flows.spec.ts:180`은 목록(`/admin/chats`)만 방문하고 방 상세(`/admin/chats/[roomId]`)를 여는 E2E는 존재하지 않으며, 이번에 만든 `messageBubbleWrap.test.ts`의 스캔 대상 파일도 `ChatRoomMessages.tsx` 하드코딩이다.
- **왜 이번에 안 고쳤나:** Story 12.3의 변경이 만든 결함이 아니라 그 리뷰가 **부수적으로 발견한 기존 결함**이다(이 diff는 관리자 화면을 전혀 건드리지 않았다). 사용자 화면 쪽 `#169` 이행 범위 밖이라 이번 스토리에서 고치면 요청에 추적되지 않는 변경이 된다(CLAUDE.md A3 — 외과적 변경). 고치는 것 자체는 `break-words` 한 단어 + 스캔 검사 대상 한 줄 추가로 끝난다.
- **트리거:** 관리자 화면(`app/(admin)/**`)을 다음에 손대는 스토리 착수 시 — 그 자리에서 `break-words`를 적용하고 `messageBubbleWrap.test.ts`의 스캔 대상에 이 파일을 추가한다. 관리자 반응형은 D5(반응형 UI 무결성)가 "관리자 화면도 예외 없음"이라 이미 못박고 있으므로 별도 판단이 필요 없다.

### DW-501: [구 #201] Broadcast Replay의 ≤25건/72시간 한도는 이 데모 규모에서 사실상 도달하지 않는다 — 그래도 커서 재조회를 항상 병행하기로 판단

origin: 장부 통합 이관(구 docs/tech-debt.md #201) — 원출처: 2026-07-29 Story 12.4, 🟢 품질, 기존 항목 무수정
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(채널 config의 `broadcast.replay`) · `docs/conventions.md` §12.5.
severity: medium
reason: Realtime Replay의 25건/72시간 한도는 이 데모의 1:1 채팅 규모에서 실제로 도달하지 않지만, 스펙은 한도 도달 여부와 무관하게 커서 재조회를 항상 병행하도록 못박았다.
trigger: 이 앱이 그룹 채팅·다자 참여·공지성 브로드캐스트처럼 한 방에 메시지가 폭증하는 형태로 확장되면(현재 스코프 밖) — 그 시점에 25건/72h 한도가 실제로 걸리는지 재측정하고, 걸린다면 커서 재조회의 조회 빈도·페이로드 크기를 다시 본다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(채널 config의 `broadcast.replay`) · `docs/conventions.md` §12.5.
- **내용:** Replay 요청은 `{ since, limit }` 두 인자를 받는다 — `limit`은 선택이고 **최대 25**, `since`는 **필수**다(`@supabase/realtime-js` README). ✎ **2026-07-29 후속 리뷰 정정:** 이 항목을 처음 쓸 때 "최근 25건·72시간이 플랫폼 기본값"이라고 적었으나, 라이브러리 문서가 정하는 것은 **`limit`의 상한 25뿐**이고 **72시간은 우리가 고른 값**이다(`since = Date.now() - 72h`). 즉 25는 "기본값"이 아니라 "허용 최대치를 그대로 요청한 것"이고, 72h는 우리 선택이다. 이 데모의 채팅은 1:1 문의 채팅(구매자·판매자 각 1명)이고 시드·수동 검증 데이터를 봐도 방 하나에 메시지가 두 자릿수를 넘는 경우가 없다 — 25건 한도에 실제로 걸리는 시나리오(한 방에서 72시간 안에 25건 넘게, 그것도 전부 "끊긴 동안"에만 오가는 경우)는 이 규모에서 사실상 발생하지 않는다. 그럼에도 스펙(Always·Never)은 이 한도를 client 코드로 재구현·우회하지 말고 **커서 재조회(`fetchMessages`, `created_at >= cursor`)를 항상 병행**하도록 못박았다 — 한도 도달 여부와 무관하게 재조회가 이미 갭을 메우는 유일하고 신뢰 가능한 경로이기 때문이다(Replay는 "있으면 좋은" 최적화, 커서 재조회가 "항상 맞는" 백스톱).
- **왜 새 항목인가:** 스펙의 실행 태스크가 "이번에 내린 판단(예: replay 25건/72h 한도 초과가 이 데모 규모에서 사실상 미도달)을 신규 항목으로 등재"를 명시적으로 요구했다(B8 — 판단과 근거를 기록해 다음 사람이 "왜 한도 초과 대비 코드가 없나"를 추측하지 않게 한다).
- **트리거:** 이 앱이 그룹 채팅·다자 참여·공지성 브로드캐스트처럼 한 방에 메시지가 폭증하는 형태로 확장되면(현재 스코프 밖) — 그 시점에 25건/72h 한도가 실제로 걸리는지 재측정하고, 걸린다면 커서 재조회의 조회 빈도·페이로드 크기를 다시 본다.

### DW-502: [구 #202] Broadcast Replay가 이미 삭제된 `chat_messages` 행의 방송을 되살릴 수 있다 — 이번 스토리의 verification 중 실제로 걸림(E2E red), 로컬 DB 정리로 해소

origin: 장부 통합 이관(구 docs/tech-debt.md #202) — 원출처: 2026-07-29 Story 12.4 verification 중 실측
location: `realtime.messages`(Supabase 플랫폼 테이블, replay가 읽는 원장) vs `public.chat_messages`(0003, append-only) — 두 테이블은 삭제에 대해 동기화되지 않는다.
severity: high
reason: ChatRoomMessages.tsx가 replay로 받은 각 행이 "지금도 chat_messages에 실제로 존재하는가"를 검증하려면 행마다 별도 존재확인 조회가 필요한데, 이는 replay의 "네트워크 왕복 없이 즉시 반영" 이점을 없앤다. 또한 이 시나리오는 정상 제품 흐름에서 발생하지 않으므로 코드 방어보다 수동 검증 절차 쪽을 고치는 것이 맞는 층이다.
trigger: 다음에 이 "가장 오래된 시드 방"으로 수동 실시간 검증을 하며 `chat_messages`를 직접 SQL로 지우는 경우 — 그 자리에서 §12.5의 정리 SQL로 `realtime.messages` 잔여 행도 함께 지운다. 만약 사용자 삭제 기능이 실제로 생기면(현재 스코프 밖) 이 축은 "함정"이 아니라 "실제 제품 결함"으로 재분류해야 하므로 그 스토리 착수 시 재판단한다.
status: open

- **위치:** `realtime.messages`(Supabase 플랫폼 테이블, replay가 읽는 원장) vs `public.chat_messages`(0003, append-only) — 두 테이블은 삭제에 대해 동기화되지 않는다.
- **내용:** Story 12.4의 `web/e2e/viewport-audit.spec.ts` "채팅방 — 가로 오버플로 없음" 검사를 처음 돌렸을 때 mobile 프로젝트만 `scrollWidth 672 > clientWidth 390`으로 red였다. 원인을 추측하지 않고 `chat_messages`·`realtime.messages`를 직접 조회해 확인: 시드 채팅방(`fetchChatRoomIdForSeedUser`가 고르는 "가장 오래된 방" — 여러 스토리가 실시간 기능을 수동 검증할 때 재사용해 온 방)에 과거 수동 검증(Story 12.1~12.3, "실시간 검증"·"멱등 테스트"·"joingap-probe"·"rt-probe"·200자 URL 등)이 남긴 `chat_messages` 행은 이미 직접 SQL로 지워져 있었는데, 그 방송 payload는 `realtime.messages`에 최대 72시간 보존돼 있었다. 이번에 새로 켠 `broadcast.replay`가 그 잔여 payload를 재생해, **이미 지워진 메시지가 재연결(최초 구독 포함)마다 화면에 되살아났다** — 그중 하나가 200자짜리 URL이라 390px 버블 오버플로를 재현시켰다.
- **왜 제품 결함이 아니라 로컬 개발 환경 함정인가:** `chat_messages`는 0003 헤더가 명시한 대로 사용자 흐름에서는 append-only다 — 구매자·판매자 UI에 메시지 삭제 기능이 없다. 이 불일치는 **개발자가 직접 SQL로 chat_messages 행을 지우며 실시간 기능을 수동 검증했을 때만** 나타난다.
  - ✎ **2026-07-29 후속 리뷰 정정(실측):** 위 문장을 처음 쓸 때 "정상 앱 흐름에는 DELETE 경로가 **없다**"고 단정했는데, 이는 사실이 아니다 — `0005_admin_policies.sql`에 관리자용 `chat_rooms_delete_admin`·`chat_messages_delete_admin` 정책이 있고(FR25), 관리자 화면 `web/src/app/(admin)/admin/chats/ChatAdminActions.tsx`에 **방 삭제 버튼이 실제로 출고돼 있다**(0003의 `on delete cascade`로 그 방 메시지도 함께 지워진다). 다만 결론(defer·로컬 함정)은 유지된다: 방 삭제는 **방 자체를 없애므로** 그 뒤로 어떤 참가자도 그 토픽을 다시 구독할 수 없어 replay가 되살릴 화면이 존재하지 않고, 단건 메시지 삭제는 정책만 있고 **그걸 호출하는 UI가 없다**. 즉 "제품 경로가 아예 없다"가 아니라 "제품 경로는 있으나 그 경로가 되살아난 방송을 볼 수 있는 화면을 남기지 않는다"가 정확한 근거다.
- **조치(이번에 한 일):** 해당 방의 `realtime.messages` 중 대응하는 `chat_messages` 행이 더 이상 없는 것만 골라 삭제해 로컬 스택을 정리했다(`delete from realtime.messages where topic='chat:room:{roomId}' and (payload->'record'->>'id') not in (select id::text from chat_messages where room_id='{roomId}')` — 9건 삭제, 재실행 후 green 확인). 스키마·코드는 건드리지 않았다(데이터 정리만).
- **왜 defer(코드로 안 막았나):** ChatRoomMessages.tsx가 replay로 받은 각 행이 "지금도 chat_messages에 실제로 존재하는가"를 검증하려면 행마다 별도 존재확인 조회가 필요한데, 이는 replay의 "네트워크 왕복 없이 즉시 반영" 이점을 없앤다. 또한 이 시나리오는 정상 제품 흐름에서 발생하지 않으므로(위 근거) 코드 방어보다 **수동 검증 절차 쪽을 고치는 것이 맞는 층**이다 — `docs/conventions.md` §12.5에 정리 SQL을 남겨 다음에 같은 방식으로 수동 검증하는 사람이 뒷정리도 함께 하게 한다.
- **트리거:** 다음에 이 "가장 오래된 시드 방"으로 수동 실시간 검증을 하며 `chat_messages`를 직접 SQL로 지우는 경우 — 그 자리에서 §12.5의 정리 SQL로 `realtime.messages` 잔여 행도 함께 지운다. 만약 사용자 삭제 기능이 실제로 생기면(현재 스코프 밖) 이 축은 "함정"이 아니라 "실제 제품 결함"으로 재분류해야 하므로 그 스토리 착수 시 재판단한다.

### DW-504: [구 #204] 오프라인 큐 flush가 **영구히 멈출 수 있다** — supabase-js 호출에 타임아웃이 없어 `isFlushing` 가드가 풀리지 않는 경로

origin: 장부 통합 이관(구 docs/tech-debt.md #204) — 원출처: 2026-07-29 Story 12.4 3차 후속 리뷰 adversarial 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `flushQueue()` — `isFlushing = true` → `await flushMessageQueue(...)` → `finally { isFlushing = false }`.
severity: high
reason: 제대로 막으려면 새 타임아웃 메커니즘(`Promise.race`+`AbortController`)을 도입해야 하는데, 이는 이 파일의 모든 네트워크 호출(온라인 전송 포함)에 걸리는 구조 변경이라 3차 리뷰 패스가 즉석에서 넣을 층이 아니다(A2·A3). 발생 확률도 낮다(연결은 살아 있는데 서버가 침묵할 때만 열리는 경로).
trigger: ① `ChatRoomMessages.tsx`(또는 `messages.ts`)에 네트워크 타임아웃을 도입하는 작업이 생길 때 — 그 자리에서 flush에도 함께 건다. ② Epic 16 Story 16.4가 이 절을 Flutter로 미러링할 때 — Dart `http`는 타임아웃이 명시적이라 그 시점에 이 축을 어떻게 다룰지 정해야 한다. ③ 실사용에서 "메시지가 안 보내지는데 아무 안내도 없다"는 신고가 나오면 이 경로를 최우선 의심한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `flushQueue()` — `isFlushing = true` → `await flushMessageQueue(...)` → `finally { isFlushing = false }`.
- **내용:** flush 도중 요청 하나가 **끝내 응답도 실패도 하지 않으면**(TCP는 붙었는데 서버가 답을 안 주는 경우) 그 `await`가 영영 settle되지 않아 `finally`가 실행되지 않고, `isFlushing`이 true로 잠긴다. 그 뒤의 모든 재연결은 `flushRequestedAgain = true`만 세우고 즉시 반환하므로 **큐가 영구 정체되고 화면에는 아무 신호도 뜨지 않는다**(미전송 안내는 flush가 *완료*돼야 뜬다). 이 전제는 추측이 아니다 — 같은 파일의 R5 패치 주석이 *"supabase-js 호출엔 타임아웃이 없어 그 구간이 길어질 수 있다"* 를 **자기 근거로** 쓰고 있다. 즉 코드가 전제를 인정한 뒤 그 전제의 최악 경로를 안 막았다.
- **같은 뿌리의 두 번째 증상 — 끊김 감지가 25~35초 늦다(edge-case 레이어 실측):** `@supabase/realtime-js`의 `HEARTBEAT_INTERVAL = 25000` · `DEFAULT_TIMEOUT = 10000`이라, 네트워크가 실제로 죽어도 채널이 `CHANNEL_ERROR`/`TIMED_OUT`을 올리기까지 약 25~35초가 걸린다. 그 구간에는 `disconnectedRef`가 여전히 false라 제출이 **온라인 경로**로 내려가고, 응답 없는 `sendMessage`가 `sending = true`를 붙잡는다 — 배너도 안 뜬 상태에서 입력창·전송 버튼이 잠기고 이후 제출이 조용히 반려된다. R5 패치는 "배너가 뜬 뒤"의 잠금만 풀었으므로 이 앞구간은 그대로 남아 있다. 근본 처방은 위와 같다(타임아웃).
- **왜 지금 안 고치나:** 제대로 막으려면 `Promise.race` + `AbortController`(또는 끊김 신호로 중단)라는 **새 타임아웃 메커니즘**을 이 파일에 도입해야 하는데, 그건 이 스토리가 만든 결함의 국소 수정이 아니라 이 파일의 모든 네트워크 호출(온라인 전송 포함 — 거기도 같은 문제가 있다)에 걸리는 구조 변경이다. A2·A3 기준으로 3차 리뷰 패스가 즉석에서 넣을 층이 아니다. 발생 확률도 낮다(네트워크가 끊기면 fetch는 보통 reject한다 — 이 경로는 "연결은 살아 있는데 서버가 침묵"할 때만 열린다).
- **트리거:** ① `ChatRoomMessages.tsx`(또는 `messages.ts`)에 네트워크 타임아웃을 도입하는 작업이 생길 때 — 그 자리에서 flush에도 함께 건다. ② Epic 16 Story 16.4가 이 절을 Flutter로 미러링할 때 — Dart `http`는 타임아웃이 명시적이라 그 시점에 이 축을 어떻게 다룰지 정해야 한다. ③ 실사용에서 "메시지가 안 보내지는데 아무 안내도 없다"는 신고가 나오면 이 경로를 최우선 의심한다.

### DW-505: [구 #205] 오프라인 큐잉의 2000자 길이 가드가 **실제로 도달 가능한 경로인지 확인되지 않았다** — `maxLength`가 이미 막고 있을 수 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #205) — 원출처: 2026-07-29 Story 12.4 3차 후속 리뷰 verification-gap 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 오프라인 분기 길이 검증(`body.length > CHAT.MESSAGE_MAX_LENGTH`) vs 같은 파일 입력창의 `maxLength={CHAT.MESSAGE_MAX_LENGTH}`.
severity: medium
reason: 가드 자체는 무해한 방어적 중복이라 지우는 게 이득은 아니지만, 대장·스펙에 미확인 주장이 사실처럼 적혀 있고 같은 규칙이 두 사본(온라인/오프라인)으로 존재하는데 어느 쪽도 테스트가 없다는 게 실체다. 제대로 정리하려면 길이 검증을 순수 함수로 뽑아야 하는데 이는 동작하는 코드의 구조 변경이라 이 패스 범위 밖이다(A3).
trigger: `CHAT.MESSAGE_MAX_LENGTH` 관련 작업이 다시 생길 때(예: 길이 상한 변경, 첨부·이미지 메시지 도입) — 그 자리에서 ① 2001자 붙여넣기를 브라우저로 1회 실측해 이 항목의 진위를 확정하고, ② 검증 규칙을 순수 함수 하나로 합쳐 경계값 테스트를 붙인다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 오프라인 분기 길이 검증(`body.length > CHAT.MESSAGE_MAX_LENGTH`) vs 같은 파일 입력창의 `maxLength={CHAT.MESSAGE_MAX_LENGTH}`.
- **내용:** 이 가드는 2026-07-29 1차 후속 리뷰가 medium으로 판정해 넣은 것이고, 그때 기록한 재현 경로는 *"붙여넣기로 2000자 초과 메시지가 큐에 들어가면 재연결마다 실패해 그 뒤 모든 메시지까지 영구히 막힌다"* 였다. 그런데 같은 입력창에 `maxLength`가 걸려 있고 브라우저 `maxlength`는 **붙여넣기에도 적용**되며 `body = input.trim()`이라 길이가 늘어날 수도 없다 — 즉 그 재현 경로는 실제로는 도달 불가일 가능성이 높다. **이번 패스에서 브라우저로 재현해보지 않았으므로 단정하지 않는다.** 또한 가드를 무력화해도(`if (false)`) 전체 테스트가 green이다(3차 리뷰 실측) — 정본 사본인 `sendMessage`의 길이 검증조차 `messages.test.ts`에 경계값 케이스가 없다.
- **왜 지금 안 고치나:** 가드 자체는 무해한 방어적 중복이고(온라인 경로와 같은 규칙을 오프라인에도 적용한 것), 지우는 것이 이득이 아니다. 실체는 두 가지 — ① 대장·스펙에 **미확인 주장이 사실처럼 적혀 있다**, ② 같은 규칙이 두 사본으로 존재하는데 어느 쪽도 테스트가 없다. 둘 다 정리하려면 `messages.ts`에 길이 검증을 순수 함수로 뽑아 양쪽이 같은 함수를 부르게 하고 경계값(2000/2001) 테스트를 붙이는 편이 맞는데, 그건 동작하는 코드의 구조 변경이라 이 패스 범위 밖이다(A3).
- **트리거:** `CHAT.MESSAGE_MAX_LENGTH` 관련 작업이 다시 생길 때(예: 길이 상한 변경, 첨부·이미지 메시지 도입) — 그 자리에서 ① 2001자 붙여넣기를 브라우저로 1회 실측해 이 항목의 진위를 확정하고, ② 검증 규칙을 순수 함수 하나로 합쳐 경계값 테스트를 붙인다.

### DW-507: [구 #207] 오프라인 큐잉 기능 전체가 **라이브러리 한 버전의 소스 독해** 위에 서 있는데 의존성은 캐럿 범위다

origin: 장부 통합 이관(구 docs/tech-debt.md #207) — 원출처: 2026-07-29 Story 12.4 3차 후속 리뷰 verification-gap 지적
location: `web/package.json`의 `"@supabase/supabase-js": "^2.108.2"`(캐럿) vs `docs/conventions.md` §12.5 첫 항 + `ChatRoomMessages.tsx`의 구독 콜백 분기.
severity: high
reason: 처방 후보 두 가지가 다 이 패스의 층이 아니다 — 버전 정확 고정(캐럿 제거)은 의존성 정책 결정이고, 버전 단언 테스트는 lock 갱신마다 무관한 red를 만들어 소음이 되고 결국 무시된다(B9). 실제로 필요한 것은 "버전을 올릴 때 이 전제를 다시 실측한다"는 절차이고, 그 절차가 사는 자리는 대장이다.
trigger: `@supabase/supabase-js`(또는 `realtime-js`)의 버전을 올릴 때 — 그 자리에서 §12.5 첫 항의 실측(네트워크 드롭 시 어떤 status가 오는가, 자동 재조인이 여전히 도는가)을 브라우저에서 1회 재현해 확인하고, 결과를 §12.5에 갱신한다. Epic 16 Story 16.4가 Flutter로 미러링할 때도 Dart 클라이언트에서 같은 실측을 처음부터 다시 해야 한다 — JS 실측 결과를 그대로 옮기면 안 된다.
status: open

- **위치:** `web/package.json`의 `"@supabase/supabase-js": "^2.108.2"`(캐럿) vs `docs/conventions.md` §12.5 첫 항 + `ChatRoomMessages.tsx`의 구독 콜백 분기.
- **내용:** "네트워크 드롭은 `CHANNEL_ERROR`/`TIMED_OUT`으로만 오고 `CLOSED`로는 오지 않는다"는 명제는 `@supabase/realtime-js` **2.108.2 소스를 직접 읽어** 확인한 실측이고, 배너·오프라인 큐잉·flush·갭보정이 **전부** 그 위에 서 있다(`disconnectedRef`를 true로 만드는 자리가 그 한 분기뿐이다 — `CLOSED` 분기는 건드리지 않는다). 그런데 의존성은 캐럿 범위라 lock 갱신 한 번으로 마이너가 올라간다. 만약 어떤 마이너가 드롭을 `CLOSED`로 표면화하거나 자동 재조인 타이밍을 바꾸면 이 기능들이 **통째로 죽고 제출은 다시 온라인 경로로 내려가는데**, `npm test`도 CI도 전부 green이다(런타임 status 전이는 tsc도 소스 스캔도 볼 수 없는 축이다).
- **왜 지금 안 고치나:** 처방 후보 두 가지가 다 이 패스의 층이 아니다 — ① 버전 정확 고정(캐럿 제거)은 **의존성 정책 결정**이라 리뷰 패스가 임의로 바꿀 수 없고, ② "`realtime-js` 버전이 2.108.2가 아니면 red" 같은 버전 단언 테스트는 lock을 갱신할 때마다 무관한 red를 만들어 **소음이 되고 결국 무시된다**(B9가 경계하는 실패 형태 그대로다). 실제로 필요한 것은 "버전을 올릴 때 이 전제를 다시 실측한다"는 **절차**이고, 그 절차가 사는 자리는 대장이다.
- **트리거:** `@supabase/supabase-js`(또는 `realtime-js`)의 버전을 올릴 때 — 그 자리에서 §12.5 첫 항의 실측(네트워크 드롭 시 어떤 status가 오는가, 자동 재조인이 여전히 도는가)을 브라우저에서 1회 재현해 확인하고, 결과를 §12.5에 갱신한다. Epic 16 Story 16.4가 Flutter로 미러링할 때도 Dart 클라이언트에서 같은 실측을 **처음부터 다시** 해야 한다 — JS 실측 결과를 그대로 옮기면 안 된다.

### DW-509: [구 #209] `AppHeader`의 안읽음 RPC 호출이 `#183`(getUser 증폭) 층에 하나 더 얹힌다

origin: 장부 통합 이관(구 docs/tech-debt.md #209) — 원출처: 2026-07-29 Story 12.5
location: `web/src/components/layout/AppHeader.tsx` — consumer 분기·로그인 시(`email` 존재) `createClient()`로 별도 Supabase 클라이언트를 만들어 `chat_unread_count()`를 호출한다. 이 페이지를 여는 서버 컴포넌트(예: `(user)/chat/page.tsx`)는 이미 자기 자신의 `getUser()`·프로필 조회를 마친 뒤 `<AppHeader email=... />`를 렌더하므로, 화면 1개당 네트워크 왕복이 그만큼 더 늘어난다.
severity: medium
reason: `#183`이 이미 "고치려면 (a) 운영 실측 (b) `getUser()` 호출 지점 분류 (c) 프리페치 정책 조정, 세 단계가 필요하고 Epic 13 착수 시로 미룬다"고 정한 판단을 이 스토리가 뒤집을 근거를 새로 만들지 않았다. `chat_unread_count()` 자체는 단순 COUNT라 개별 호출 비용은 낮고(A2) 데모 규모에서는 무해하다.
trigger: `#183`의 트리거(Epic 13 착수, 또는 운영에서 인증·RPC 레이트리밋이 관측될 때)와 동일하다 — 그 자리에서 `getUser()` 재구조화와 함께 `chat_unread_count()` 호출도 "상위에서 한 번 구해 내려주는" 형태로 같이 정리할지 판단한다.
status: open

- **위치:** `web/src/components/layout/AppHeader.tsx` — consumer 분기·로그인 시(`email` 존재) `createClient()`로 별도 Supabase 클라이언트를 만들어 `chat_unread_count()`를 호출한다. 이 페이지를 여는 서버 컴포넌트(예: `(user)/chat/page.tsx`)는 이미 자기 자신의 `getUser()`·프로필 조회를 마친 뒤 `<AppHeader email=... />`를 렌더하므로, 화면 1개당 네트워크 왕복이 그만큼 더 늘어난다.
- **내용:** `#183`이 이미 "화면 1개를 여는 데 `/auth/v1/user`를 17~27번 부른다"를 실측으로 기록해 뒀다. 이 스토리는 그 근본 구조(호출부마다 자기 supabase 클라이언트를 새로 만드는 관례)를 바꾸지 않고 그 위에 `chat_unread_count()` RPC 호출을 **소비자 헤더가 렌더될 때마다** 하나 더 얹었다 — AppHeader가 9개 호출부 중 8곳(admin 제외)에서 쓰이므로, 로그인 상태의 소비자 페이지 전체에 이 RPC가 새로 딸린다.
- **왜 지금 안 고치나:** `#183`이 이미 "고치려면 (a) 운영 실측 (b) `getUser()` 호출 지점 분류 (c) 프리페치 정책 조정, 세 단계가 필요하고 Epic 13(성능·게이트 정비) 착수 시로 미룬다"고 정했다 — 이 스토리가 그 판단을 뒤집을 근거를 새로 만들지 않았다. `chat_unread_count()` 자체는 SECURITY INVOKER 단순 COUNT라 개별 호출 비용은 낮고(A2), 데모 규모에서는 무해하다.
- **트리거:** `#183`의 트리거(Epic 13 착수, 또는 운영에서 인증·RPC 레이트리밋이 관측될 때)와 동일하다 — 그 자리에서 `getUser()` 재구조화와 함께 `chat_unread_count()` 호출도 "상위에서 한 번 구해 내려주는" 형태로 같이 정리할지 판단한다.

### DW-510: [구 #210] 방이 열린 채 실시간으로 본 메시지는 재진입 전까지 안읽음 배지에 남는다

origin: 장부 통합 이관(구 docs/tech-debt.md #210) — 원출처: 2026-07-29 Story 12.5
location: `web/src/app/(user)/chat/[roomId]/page.tsx`(방 진입 시 1회 `markChatRoomRead`) · `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(실시간 구독·큐 상태기계, 이 스토리가 손대지 않음).
severity: medium
reason: 스펙(spec-12-5) intent-contract의 Never 절이 이 축을 명시적으로 범위 밖에 뒀다 — "방이 열려 있는 동안 새 메시지마다 `last_read_at`을 다시 갱신하지 않는다"(과설계 방지, A2·A3). 실시간 도착마다 DB write를 추가하면 쓰기 증폭이 생기는데 이 데모 규모에서 그 비용을 감수할 근거가 없다.
trigger: 실사용에서 "배지가 안 줄어든다"는 혼란이 보고되면, `ChatRoomMessages.tsx`의 구독 콜백에 디바운스된 `markChatRoomRead` 호출을 추가하는 안을 이 항목에서 재판단한다(그 파일의 상태기계를 건드리는 결정이라 별도 승인 필요). Epic 16 Story 16.4(Flutter 미러링)도 동일 판단이 필요하다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/page.tsx`(방 진입 시 1회 `markChatRoomRead`) · `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(실시간 구독·큐 상태기계, 이 스토리가 손대지 않음).
- **내용:** `chat_room_reads.last_read_at`은 **방에 서버 렌더로 진입하는 시점**에만 갱신된다. 방을 열어 둔 채 상대의 메시지가 실시간 구독(§12.5)으로 여러 건 도착해 화면에 이미 보였더라도, 페이지를 재진입(새로고침·재방문)하지 않고 나가면 그 메시지들은 다음 진입 전까지 `chat_unread_count()` 집계에 그대로 남는다 — 사용자는 이미 읽었는데 배지 숫자가 줄지 않는 것으로 보인다.
- **왜 지금 안 고치나:** 스펙(spec-12-5) intent-contract의 Never 절이 이 축을 명시적으로 범위 밖에 뒀다 — "방이 열려 있는 동안 새 메시지마다 `last_read_at`을 다시 갱신하지 않는다"(과설계 방지, A2·A3 — 이미 3차 리뷰를 거친 `ChatRoomMessages.tsx`의 구독·큐 상태기계에 손대지 않는다). 실시간 도착마다 DB write를 추가하면 메시지 폭주 시 쓰기 증폭이 생기고, 이 데모 규모에서 그 비용을 감수할 근거가 없다.
- **트리거:** 실사용에서 "배지가 안 줄어든다"는 혼란이 보고되면, `ChatRoomMessages.tsx`의 구독 콜백에 디바운스된 `markChatRoomRead` 호출을 추가하는 안을 이 항목에서 재판단한다(그 파일의 상태기계를 건드리는 결정이라 별도 승인 필요). Epic 16 Story 16.4(Flutter 미러링)도 동일 판단이 필요하다.

### DW-511: [구 #211] 로컬 Supabase 스택에서 `authenticated`/`anon`의 테이블 기본 권한이 통째로 빠져 있었다 — 전 기능이 로컬에서 42501로 죽는 상태였다

origin: 장부 통합 이관(구 docs/tech-debt.md #211) — 원출처: 2026-07-29 Story 12.5 구현 검증 중 실측
location: 이 프로젝트 로컬 Docker 스택(`supabase_db_bmad-encar-demo` 컨테이너)의 `pg_default_acl` — `defaclrole=postgres`(마이그레이션이 실행되는 롤) 항목이 테이블에 대해 `anon=Dxtm`·`authenticated=Dxtm`만 갖고 있었다(D=TRUNCATE, x=REFERENCES, t=TRIGGER, m=MAINTAIN — SELECT/INSERT/UPDATE/DELETE 넷 다 빠짐). 대조군 `defaclrole=supabase_admin` 항목은 정상적으로 `arwdDxtm`(전체)을 갖고 있다.
severity: critical
reason: 이 발견은 Story 12.5 범위(FR57)가 아니라 프로젝트 전체의 로컬 개발 인프라 결함이라 이 스토리 diff에 섞으면 A2(무관 범위 확장) 위반이다. 조치는 세션(이 컨테이너 인스턴스)에만 적용돼 파일로 남지 않았으므로 다음 `supabase db reset`(또는 새 볼륨) 때 재현된다.
trigger: ① 다음 로컬 `supabase db reset` 후 아무 기능이나(로그인 후 매물 목록 등) 먼저 1회 확인해 이 증상이 재현되는지 본다. ② 재현되면, 0006의 `ai_readonly` 패턴(마이그레이션으로 `alter default privileges` + 기존 테이블 일괄 GRANT 선언)을 그대로 따라 anon/authenticated용 영구 마이그레이션을 신설할지 사용자에게 확인한다 — 이 항목이 그 결정을 위한 실측 근거다. ③ 원격(호스팅) Supabase 프로젝트는 이 문제와 무관하다(그쪽의 `defaclrole` 기본값은 별도로 정상 설정돼 있음 — 0020 주석의 "Supabase 원격 + 이 레포 게이트 프렐류드 둘 다 재현" 문구가 이미 그 사실을 전제하고 있다).
status: open

- **위치:** 이 프로젝트 로컬 Docker 스택(`supabase_db_bmad-encar-demo` 컨테이너)의 `pg_default_acl` — `defaclrole=postgres`(마이그레이션이 실행되는 롤) 항목이 테이블에 대해 `anon=Dxtm`·`authenticated=Dxtm`만 갖고 있었다(D=TRUNCATE, x=REFERENCES, t=TRIGGER, m=MAINTAIN — SELECT/INSERT/UPDATE/DELETE 넷 다 빠짐). 대조군 `defaclrole=supabase_admin` 항목은 정상적으로 `arwdDxtm`(전체)을 갖고 있다.
- **어떻게 발견했나·실측(추측 아님):** Story 12.5 구현을 검증하려고 `has_table_privilege('authenticated','public.chat_rooms','SELECT')` 등을 직접 조회하니 전부 `f`. 의심 즉시 실제 REST API(`buyer@test.com` 로그인 토큰)로 `chat_rooms`·`listings`·`profiles`·`wishlists` 조회를 시도해 전부 `42501 permission denied`를 재현했다 — **이 스토리의 새 테이블만이 아니라 프로젝트의 모든 기존 테이블(이미 여러 에픽에 걸쳐 "done"으로 닫힌 기능들 포함)이 로컬에서 동일하게 막혀 있었다.** 서브에이전트(구현 담당)도 구현 중 같은 증상을 발견했으나 "이번 스토리가 만든 문제가 아니다"로 판단해 `supabase db reset`으로 되돌렸는데, `db reset`은 **마이그레이션 재생 방식**이라 이 컨테이너 레벨 기본값 자체를 복구하지 못하므로 되돌린 뒤에도 여전히 깨진 상태였다(재확인으로 검증됨).
- **왜 이게 문제인가:** `0012_listing_images.sql`·`0020_listings_view_count.sql` 등 여러 마이그레이션 주석이 "authenticated 테이블 기본 SELECT/INSERT/UPDATE는 플랫폼 기본(`alter default privileges ... grant all to anon, authenticated`)에 위임하고 여기서는 명시 GRANT를 안 한다"고 **명시적으로 그 전제 위에서 설계돼 있다** — 즉 이 전제가 깨지면 이 레포의 코드가 아니라 **로컬 환경 자체**가 전체 앱을 무력화한다. `ai_readonly`용 기본값(0006이 마이그레이션으로 직접 선언)은 정상 작동해 살아남았는데, anon/authenticated용 기본값은 어느 마이그레이션에도 선언돼 있지 않고 컨테이너 최초 부팅(`docker-entrypoint-initdb.d`, 볼륨이 비어 있을 때만 실행)에만 의존하고 있었다 — 그래서 `supabase db reset`(같은 볼륨 위에서 DB만 drop+recreate)로는 재생되지 않는다.
- **조치(이번에 한 일, 세션 내 라이브 수정 — 마이그레이션 파일 아님):** `ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT/INSERT/UPDATE/DELETE ON TABLES TO authenticated, anon`(+ sequences/functions)로 앞으로 생성될 테이블의 기본값을 복구하고, `GRANT SELECT/INSERT/UPDATE/DELETE ON ALL TABLES IN SCHEMA public TO authenticated`(+동일하게 `anon`도)로 기존 테이블도 즉시 복구했다. **`listings`의 0020 하드닝(authenticated의 view_count INSERT/UPDATE 제외)과 `listings`·`listing_images`의 0011/0012 하드닝(anon 컬럼 화이트리스트)이 되돌아가지 않도록, 같은 조치 안에서 각 마이그레이션의 REVOKE+컬럼별 GRANT를 그대로 재적용**했다 — 처음엔 `anon` 쪽 재적용을 빠뜨렸다가, 코드리뷰 패치로 신설한 `api/tests/integration/test_chat_unread_real_db.py`를 포함해 전체 `api-db` 스위트(73건)를 돌리자 `test_seller_summary_real_db.py`의 기존 테스트 1건이 그 누락을 실제로 잡아냈다(anon이 `profiles`를 못 읽어 42501) — 즉시 anon 쪽도 동일하게 재적용해 73건 전부 green으로 복구했다. 재확인 결과 `authenticated`의 `view_count` UPDATE는 여전히 `f`, `anon`의 `listings.embedding`·`listing_images` 비화이트리스트 컬럼도 여전히 `f`(차단 유지), 나머지 표면은 정상. Story 12.5 자체 검증(REST API로 안읽음 카운트 계산·감소·타인 방 읽음기록 삽입 거부까지 실측)과 `npm run lint`/`tsc`/`vitest`(279건, 코드리뷰 패치 2건 포함)/`api-db` pytest(73건)/Playwright 실브라우저(배지·정렬·읽음처리 전부 눈으로 확인)는 이 조치 이후 전부 수행했다.
- **왜 마이그레이션 파일로 만들지 않았나(지금은):** 이 발견은 Story 12.5의 범위(FR57)가 아니라 **프로젝트 전체의 로컬 개발 인프라** 결함이라 이 스토리의 diff에 섞으면 A2(무관 범위 확장) 위반이다. 다만 이 조치는 **세션(이 컨테이너 인스턴스)에만 적용**돼 있고 파일로 남지 않았으므로, 다음에 누군가 `supabase db reset`(또는 새 볼륨으로 `supabase start`)을 돌리면 **이 문제가 다시 재현된다.**
- **트리거:** ① 다음 로컬 `supabase db reset` 후 아무 기능이나(로그인 후 매물 목록 등) 먼저 1회 확인해 이 증상이 재현되는지 본다. ② 재현되면, 0006의 `ai_readonly` 패턴(마이그레이션으로 `alter default privileges` + 기존 테이블 일괄 GRANT 선언)을 그대로 따라 anon/authenticated용 **영구 마이그레이션**을 신설할지 사용자에게 확인한다 — 이 항목이 그 결정을 위한 실측 근거다. ③ 원격(호스팅) Supabase 프로젝트는 이 문제와 무관하다(그쪽의 `defaclrole` 기본값은 별도로 정상 설정돼 있음 — 0020 주석의 "Supabase 원격 + 이 레포 게이트 프렐류드 둘 다 재현" 문구가 이미 그 사실을 전제하고 있다).
- ✎ **2026-07-29 Story 12.6 사전 점검.** 스펙(spec-12-6) Always 절이 명시한 대로 검증 착수 전 `select has_table_privilege('authenticated','public.chat_messages','select');`를 재확인했다 — 결과 `t`(정상). 컨테이너가 12.5 이후 재기동·재생성(`supabase db reset`·새 볼륨)되지 않아 세션 내 임시 조치가 그대로 살아있는 상태였다(트리거 ①의 조건 — "다음 reset"이 아직 오지 않음). 재적용 불필요, 별도 조치 없이 계속 진행. 이 항목은 여전히 열려 있다(영구 마이그레이션 여부는 미결).

### DW-512: [구 #212] `chat_unread_count()`가 시간 창 없이 사용자의 전체 대화 이력을 매번 스캔한다

origin: 장부 통합 이관(구 docs/tech-debt.md #212) — 원출처: 2026-07-29 Story 12.5 코드리뷰 adversarial 지적
location: `supabase/migrations/0024_chat_room_reads.sql`의 `chat_unread_count()` — 내가 당사자인 모든 방의 `chat_messages`를 조건절로 필터링만 할 뿐, 최근 N일 등의 시간 창이나 페이지네이션이 없다.
severity: high
reason: 데모 규모(시드 계정 몇 개, 메시지 수십~수백 건)에서는 무해하다(A2 — 불필요한 최적화 금지). 시간 창을 넣으면 FR57 공식을 변경하는 것이라 스펙 권한(architecture 문서가 이미 확정한 공식) 밖의 임의 변경이 된다.
trigger: 실사용 규모로 전환되거나(Epic 13 성능·게이트 정비 등) 메시지 이력이 계정당 수천 건 이상으로 누적되는 시점 — 그 자리에서 EXPLAIN ANALYZE로 실측하고, 필요하면 인덱스 보강 또는 "최근 N개월만 안읽음으로 집계" 같은 명시적 제품 결정을 별도로 받는다.
status: open

- **위치:** `supabase/migrations/0024_chat_room_reads.sql`의 `chat_unread_count()` — 내가 당사자인 모든 방의 `chat_messages`를 조건절로 필터링만 할 뿐, 최근 N일 등의 시간 창이나 페이지네이션이 없다.
- **내용:** FR57 AC의 공식(`created_at > last_read_at AND sender_id != {me}`) 자체가 시간 창을 두지 않으므로 **정확성 문제는 아니다** — 오래전에 안 읽은 메시지도 계속 안읽음으로 잡히는 것이 의도된 동작이다. 다만 이 RPC는 로그인한 소비자 화면 대부분(`AppHeader`)에서 매 렌더마다 호출되므로(대장 `#209`), 계정의 누적 메시지 수가 늘어날수록 이 COUNT의 스캔 비용이 커진다 — 그 성장 축 자체가 지금까지 실측·기록된 적이 없다.
- **왜 지금 안 고치나:** 데모 규모(시드 계정 몇 개, 메시지 수십~수백 건)에서는 무해하다(A2 — 불필요한 최적화 금지). 시간 창을 넣으면 FR57 공식을 변경하는 것이라 스펙 권한(architecture 문서가 이미 확정한 공식) 밖의 임의 변경이 된다.
- **트리거:** 실사용 규모로 전환되거나(Epic 13 성능·게이트 정비 등) 메시지 이력이 계정당 수천 건 이상으로 누적되는 시점 — 그 자리에서 EXPLAIN ANALYZE로 실측하고, 필요하면 인덱스 보강 또는 "최근 N개월만 안읽음으로 집계" 같은 명시적 제품 결정을 별도로 받는다.

### DW-513: [구 #213] `last_read_at`을 DB(`now()`)가 아니라 web 서버 시계(`new Date()`)가 정한다

origin: 장부 통합 이관(구 docs/tech-debt.md #213) — 원출처: 2026-07-29 Story 12.5 후속 코드리뷰 adversarial+edge-case 교차 지적
location: `web/src/lib/chat.ts`의 `markChatRoomRead` — upsert 페이로드에 `last_read_at: new Date().toISOString()`을 실어 보낸다. `chat_room_reads.last_read_at`에는 `default now()`(DB 시계)가 있지만, upsert의 충돌(재진입) 경로에서는 컬럼 기본값을 쓸 방법이 없어 값이 항상 앱 서버에서 온다.
severity: medium
reason: 제대로 고치려면 `mark_chat_room_read(p_room_id)` 같은 RPC를 새로 만들어 갱신 통로를 DB 안으로 옮겨야 하는데, 실제 피해는 (a) 클라우드 NTP 동기 환경에서 1초 미만 오차 구간, (b) 자기 배지만 망가뜨리는 자해 경로 둘뿐이라 지금 감수 비용이 더 크다(A2). 스펙(spec-12-5)도 "서버에서 지금 시각으로 upsert"까지만 규정하고 어느 시계인지는 열어 뒀다.
trigger: ① 안읽음 관련 갱신 통로를 어떤 이유로든 RPC로 옮기게 될 때(예: `#210`의 실시간 디바운스 갱신을 도입하는 순간 — 그때 어차피 RPC가 필요하다) 같이 처리한다. ② 배지 숫자가 실제와 어긋난다는 보고가 들어오면 두 시계 차부터 실측한다(`select now()` vs 앱 서버 시각).
status: open

- **위치:** `web/src/lib/chat.ts`의 `markChatRoomRead` — upsert 페이로드에 `last_read_at: new Date().toISOString()`을 실어 보낸다. `chat_room_reads.last_read_at`에는 `default now()`(DB 시계)가 있지만, upsert의 충돌(재진입) 경로에서는 컬럼 기본값을 쓸 방법이 없어 값이 항상 앱 서버에서 온다.
- **내용:** 안읽음 공식의 커트라인(`created_at > last_read_at`)에서 `created_at`은 Postgres 시계, `last_read_at`은 Next 서버 시계라 **두 시계가 비교된다.** 앱 서버가 앞서 있으면 그 오차 구간에 도착한 메시지가 도착 즉시 "읽음"으로 묻히고, 뒤처져 있으면 방금 읽은 메시지가 안읽음으로 남는다. 또 이 값은 클라이언트 경로(anon key + RLS)로 쓰이므로 사용자가 직접 먼 미래 시각을 넣어 자기 배지를 영구히 0으로 만들 수도 있다 — RLS가 본인 행으로 한정하므로 **자해에 그치고 타인에겐 영향이 없다**. CLAUDE.md B9("중요한 값은 서버·DB가 직접 구한다")의 축이다.
- **왜 지금 안 고치나:** 제대로 고치려면 `mark_chat_room_read(p_room_id)` 같은 RPC를 새로 만들어(`insert … on conflict do update set last_read_at = now()`) 갱신 통로를 DB 안으로 옮겨야 한다 — 마이그레이션 1건 + 호출부 변경이고, 실제 피해는 (a) 클라우드 NTP 동기 환경에서 1초 미만 오차 구간, (b) 자기 배지만 망가뜨리는 자해 경로 둘뿐이라 지금 감수 비용이 더 크다(A2). 스펙(spec-12-5)도 "서버에서 지금 시각으로 upsert"까지만 규정하고 어느 시계인지는 열어 뒀다.
- **트리거:** ① 안읽음 관련 갱신 통로를 어떤 이유로든 RPC로 옮기게 될 때(예: `#210`의 실시간 디바운스 갱신을 도입하는 순간 — 그때 어차피 RPC가 필요하다) 같이 처리한다. ② 배지 숫자가 실제와 어긋난다는 보고가 들어오면 두 시계 차부터 실측한다(`select now()` vs 앱 서버 시각).

### DW-514: [구 #214] `last_message_at` 트리거가 INSERT만 본다 — 관리자가 마지막 메시지를 지우면 방이 목록 상단에 고정된다

origin: 장부 통합 이관(구 docs/tech-debt.md #214) — 원출처: 2026-07-29 Story 12.5 후속 코드리뷰 edge-case-hunter 지적
location: `supabase/migrations/0024_chat_room_reads.sql`의 `chat_messages_touch_room_last_message`(AFTER **INSERT** only) + `0005_admin_policies.sql`의 `chat_messages_delete_admin`(FR25 — 관리자 개별 메시지 삭제).
severity: medium
reason: 고치려면 AFTER DELETE(+ UPDATE OF created_at) 트리거를 하나 더 두고 `max()`로 재계산해야 하는데, 이는 `greatest()` 단조증가 규칙과 충돌하는 두 번째 쓰기 통로를 만드는 일이라 설계 판단이 필요하다. 관리자 메시지 삭제는 운영 예외 경로이고 데모 규모에서 실제로 쓰인 적이 없다(A2).
trigger: 관리자 채팅 모더레이션(FR25 메시지 삭제)이 실제 운영 흐름으로 쓰이기 시작하거나, "지운 대화가 목록 위에 계속 뜬다"는 보고가 들어올 때 — 그 자리에서 "삭제 시 재계산 트리거" vs "단조증가 유지" 중 어느 쪽을 정본으로 삼을지 결정한다. Epic 16.4(Flutter 미러링)는 같은 컬럼을 읽기만 하므로 이 결정과 무관하다.
status: open

- **위치:** `supabase/migrations/0024_chat_room_reads.sql`의 `chat_messages_touch_room_last_message`(AFTER **INSERT** only) + `0005_admin_policies.sql`의 `chat_messages_delete_admin`(FR25 — 관리자 개별 메시지 삭제).
- **내용:** 트리거가 삽입만 따라가고 삭제·`created_at` 변경은 보지 않는다. 관리자가 어떤 방의 **가장 마지막 메시지**를 삭제하면 `chat_rooms.last_message_at`은 이미 없는 메시지의 시각을 계속 가리키고, `greatest()` 단조증가 가드 때문에 **되돌아갈 길도 없다** — 그 방은 실제 대화가 더 오래됐는데도 목록 상단에 영구히 남는다. 정확성이 아니라 정렬 표시의 문제이고, 트리거 경로가 아니라 관리자 삭제 경로에서만 발생한다.
- **왜 지금 안 고치나:** 고치려면 AFTER DELETE(+ UPDATE OF created_at) 트리거를 하나 더 두고 `max()`로 재계산해야 하는데, 이는 `greatest()` 단조증가 규칙과 충돌하는 두 번째 쓰기 통로를 만드는 일이라 설계 판단이 필요하다(단조증가는 동시 전송 시 정렬 역전을 막으려고 코드리뷰에서 일부러 넣은 가드다). 관리자 메시지 삭제는 운영 예외 경로이고 데모 규모에서 실제로 쓰인 적이 없다(A2).
- **트리거:** 관리자 채팅 모더레이션(FR25 메시지 삭제)이 실제 운영 흐름으로 쓰이기 시작하거나, "지운 대화가 목록 위에 계속 뜬다"는 보고가 들어올 때 — 그 자리에서 "삭제 시 재계산 트리거" vs "단조증가 유지" 중 어느 쪽을 정본으로 삼을지 결정한다. Epic 16.4(Flutter 미러링)는 같은 컬럼을 읽기만 하므로 이 결정과 무관하다.

### DW-516: [구 #216] `markChatRoomRead`의 upsert가 **단조증가가 아니다** — 같은 컬럼 축에 넣은 `last_message_at` 가드와 비대칭이다

origin: 장부 통합 이관(구 docs/tech-debt.md #216) — 원출처: 2026-07-29 Story 12.5 3차 후속 리뷰 edge-case-hunter 지적
location: `web/src/lib/chat.ts`의 `markChatRoomRead` — `.upsert({...}, { onConflict: 'user_id,room_id' })`는 `on conflict do update set last_read_at = excluded.last_read_at`을 만든다(비교 없음).
severity: medium
reason: supabase-js의 upsert로는 `greatest()`를 표현할 수 없어 `#213`과 똑같이 RPC 신설이 필요하다 — 두 항목의 수정 지점이 같은 한 줄이므로 따로 고치는 것이 낭비다. 실제 피해는 초 단위 오차 구간에서 이미 읽은 메시지 몇 건이 다시 뜨는 정도이고, 다음 진입에 곧바로 해소된다.
trigger: **`#213`을 처리할 때 같이** — 그 RPC의 갱신문을 `do update set last_read_at = greatest(chat_room_reads.last_read_at, excluded.last_read_at)`로 쓴다. `#213`만 닫고 이 항목을 열어 두는 일이 없게, 그 자리에서 두 항목을 함께 닫는다.
status: open

- **위치:** `web/src/lib/chat.ts`의 `markChatRoomRead` — `.upsert({...}, { onConflict: 'user_id,room_id' })`는 `on conflict do update set last_read_at = excluded.last_read_at`을 만든다(비교 없음).
- **내용:** 같은 스토리가 `chat_rooms.last_message_at`에는 `greatest(기존값, 새 값)` 단조증가 가드를 **일부러 넣었는데**(0024, 코드리뷰 patch — 커밋 순서가 시각순과 어긋나도 정렬 기준이 되돌아가지 않게), 짝이 되는 `last_read_at`에는 같은 가드가 없다. 두 탭·느린 요청이 빠른 요청에 추월당하는 경우·web 인스턴스 간 시계 편차에서 **더 이른 시각이 나중에 덮어써질 수 있고**, 그러면 이미 읽은 메시지가 배지에 다시 나타난다. 대장 `#213`과 **축이 다르다** — `#213`은 "값을 어느 시계가 정하나", 이건 "그 값이 되돌아갈 수 있나"다. `#213`의 처방(RPC로 `now()`)만 적용하고 `greatest()`를 빼면 이 축은 남는다.
- **왜 지금 안 고치나:** supabase-js의 upsert로는 `greatest()`를 표현할 수 없어 `#213`과 똑같이 RPC 신설이 필요하다 — 두 항목의 수정 지점이 같은 한 줄이므로 따로 고치는 것이 낭비다. 실제 피해는 초 단위 오차 구간에서 이미 읽은 메시지 몇 건이 다시 뜨는 정도이고, 다음 진입에 곧바로 해소된다.
- **트리거:** **`#213`을 처리할 때 같이** — 그 RPC의 갱신문을 `do update set last_read_at = greatest(chat_room_reads.last_read_at, excluded.last_read_at)`로 쓴다. `#213`만 닫고 이 항목을 열어 두는 일이 없게, 그 자리에서 두 항목을 함께 닫는다.

### DW-517: [구 #217] `chat_rooms` 시드 삽입문도 명시 컬럼 목록으로 바뀌어 `#146`이 예고한 "조용한 누락" 쪽에 합류했다 — `#146` 본문의 현황 서술이 낡았다

origin: 장부 통합 이관(구 docs/tech-debt.md #217) — 원출처: 2026-07-29 Story 12.5 3차 후속 리뷰 adversarial+edge-case 교차 지적
location: `supabase/seed-local/02_data.sql`의 `chat_rooms` 삽입문(7컬럼 하드코딩). `#146`은 이 문장을 "`select * from jsonb_populate_recordset(...)` 그대로"라고 적고 있는데, Story 12.5가 `last_message_at not null`을 추가하면서 시드가 통째로 죽어(`null value in column last_message_at ... violates not-null constraint`) 명시 목록으로 바꿨다. `#146`이 예측한 재발이 **실제로 일어났고**, 그 처방도 `#146`이 `listings`에 대해 쓴 것과 같은 방식이었다.
severity: medium
reason: `#146`은 이 리뷰 세션이 수정할 수 없는 기존 항목(오케스트레이터 소유)이고, 그 본문의 "나머지 4개는 여전히 `select *`"라는 현황 서술이 지금은 사실과 다르다 — 그래서 정정 기록으로만 남긴다(`#189`가 `#186`에 대해 쓴 것과 같은 방식). 처방·트리거는 `#146`이 정본이다.
trigger: `#146`을 처리할 때 함께 — 그 자리에서 `chat_rooms`도 대상에 넣는다(컬럼 목록을 `information_schema`와 대조하는 시드 게이트 1개면 두 테이블을 동시에 덮는다). 대장 `#122`(seed-local이 CI에서 안 돌아간다)와 같이 처리하면 그 게이트가 실제로 실행되는 자리까지 확보된다.
status: done 2026-07-29
resolution: DW-446(구 #146)의 현황을 바로잡는 정정 메모라 원항목에 병합 — 처방·트리거는 DW-446이 정본

- **위치:** `supabase/seed-local/02_data.sql`의 `chat_rooms` 삽입문(7컬럼 하드코딩). `#146`은 이 문장을 "`select * from jsonb_populate_recordset(...)` 그대로"라고 적고 있는데, Story 12.5가 `last_message_at not null`을 추가하면서 시드가 통째로 죽어(`null value in column last_message_at ... violates not-null constraint`) 명시 목록으로 바꿨다. `#146`이 예측한 재발이 **실제로 일어났고**, 그 처방도 `#146`이 `listings`에 대해 쓴 것과 같은 방식이었다.
- **내용:** 그래서 `#146`이 지적한 대가가 이제 두 테이블에 걸린다 — 앞으로 `chat_rooms`에 nullable 컬럼이 추가되고 스냅샷 JSON에 값이 들어와도, 목록에 없으면 **아무 에러 없이 조용히** 비워진 채 시드된다. 남은 `select *` 삽입문은 3개(`listing_images`·`chat_messages`·`guide_documents`)이고, 그중 하나에 `not null` 컬럼이 추가되면 같은 전면 시드 실패가 또 난다. `information_schema`에서 컬럼 목록을 실시간 도출해 대조하는 검사는 여전히 없다(`#146`이 지적한 그대로).
- **왜 별도 항목인가:** `#146`은 이 리뷰 세션이 수정할 수 없는 기존 항목이고(오케스트레이터 소유), 그 본문의 "나머지 4개는 여전히 `select *`"라는 현황 서술이 지금은 사실과 다르다. 다음 사람이 `#146`만 읽고 `chat_rooms`를 `select *`로 알면 판단을 잘못한다 — 그래서 **정정 기록으로만** 남긴다(`#189`가 `#186`에 대해 쓴 것과 같은 방식). 처방·트리거는 `#146`이 정본이다.
- **트리거:** `#146`을 처리할 때 함께 — 그 자리에서 `chat_rooms`도 대상에 넣는다(컬럼 목록을 `information_schema`와 대조하는 시드 게이트 1개면 두 테이블을 동시에 덮는다). 대장 `#122`(seed-local이 CI에서 안 돌아간다)와 같이 처리하면 그 게이트가 실제로 실행되는 자리까지 확보된다.

### DW-518: [구 #218] 관리자가 **소비자** 채팅방 라우트를 열면 Realtime 구독이 계속 CHANNEL_ERROR로 끊긴다

origin: 장부 통합 이관(구 docs/tech-debt.md #218) — 원출처: 2026-07-29 Story 12.5 3차 후속 리뷰 검증 중 실측
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(12.3/12.4의 실시간 구독) + `supabase/migrations/0022~0023`의 Broadcast 참가자 인가(방 당사자만 `chat:room:<id>` 토픽 구독 허용) + `0005_admin_policies.sql`의 `chat_rooms_select_admin`.
severity: medium
reason: 고치려면 소비자 방 페이지가 "관리자면 `/admin/chats/<id>`로 보낸다" 같은 라우팅 판단을 하거나 구독 자체를 당사자 조건으로 막아야 하는데, 둘 다 이 스토리(안읽음·정렬) 범위 밖이고 12.3/12.4가 3차까지 리뷰한 구독 상태기계를 건드린다(A3).
trigger: 관리자 채팅 모더레이션 화면(FR25)을 손대는 다음 스토리, 또는 Epic 12 회고에서 실시간 인가 축을 정리할 때 — 그 자리에서 "관리자는 소비자 방 라우트에 들어오지 않게 막는다" vs "들어와도 구독은 걸지 않는다" 중 하나를 정본으로 정한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(12.3/12.4의 실시간 구독) + `supabase/migrations/0022~0023`의 Broadcast 참가자 인가(방 당사자만 `chat:room:<id>` 토픽 구독 허용) + `0005_admin_policies.sql`의 `chat_rooms_select_admin`.
- **실측(로컬 스택 + dev 서버, admin@test.com으로 `/chat/<남의 방>` 진입, 2026-07-29):** 서버 로그에 `[chat/room] 실시간 구독 끊김: CHANNEL_ERROR Error: Unauthorized: You do not have permissions to read from this Channel topic: chat:room:<roomId>`가 방문할 때마다 반복 기록됨.
- **내용:** 관리자에게는 `chat_rooms_select_admin`(참여자 정책과 OR 합성) 때문에 남의 방이 **조회는 되므로** 소비자용 방 페이지가 정상 렌더되고, 그 안의 실시간 구독까지 시도한다. 그런데 Broadcast 인가는 당사자만 허용하므로 매번 거부된다. 관리자에겐 전용 화면(`/admin/chats/[roomId]`)이 따로 있어 실사용 경로는 아니지만, `/chat/<id>`에 리다이렉트가 없어 도달 가능하고 도달하면 계속 에러만 쌓인다. **이 스토리가 만든 것이 아니다** — 12.2~12.4의 실시간 인가와 0005의 관리자 SELECT 정책이 만나는 자리이고, 이번 리뷰의 관리자 축 검증 중 부수적으로 관측됐다(같은 축의 안읽음 쪽 결함은 `0025`와 이번 패치로 닫았다).
- **왜 지금 안 고치나:** 고치려면 소비자 방 페이지가 "관리자면 `/admin/chats/<id>`로 보낸다" 같은 라우팅 판단을 하거나 구독 자체를 당사자 조건으로 막아야 하는데, 둘 다 이 스토리(안읽음·정렬) 범위 밖이고 12.3/12.4가 3차까지 리뷰한 구독 상태기계를 건드린다(A3).
- **트리거:** 관리자 채팅 모더레이션 화면(FR25)을 손대는 다음 스토리, 또는 Epic 12 회고에서 실시간 인가 축을 정리할 때 — 그 자리에서 "관리자는 소비자 방 라우트에 들어오지 않게 막는다" vs "들어와도 구독은 걸지 않는다" 중 하나를 정본으로 정한다.

### DW-520: [구 #220] "다시 보내기" 재시도 버튼에 진행 중 표시(로딩 상태)가 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #220) — 원출처: 2026-07-29 Story 12.6 코드리뷰 adversarial+edge-case 교차 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼(`#206` 최소 수정) — `isFlushing`은 reconnect effect 안의 평범한 클로저 변수라 컴포넌트 state가 아니다.
severity: medium
reason: `isFlushing`을 state로 승격하려면 12.4가 3차까지 리뷰한 재연결·큐잉 상태기계에 렌더 트리거를 추가하는 구조 변경이 필요하다 — `#206`이 명시한 "가장 작은 수정"(재시도 버튼 추가) 범위를 넘는다(A3).
trigger: `ChatRoomMessages.tsx`의 재연결/큐 상태기계를 다시 손대는 다음 작업 — 그 자리에서 `isFlushing`을 state로 승격할지 판단한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼(`#206` 최소 수정) — `isFlushing`은 reconnect effect 안의 평범한 클로저 변수라 컴포넌트 state가 아니다.
- **내용:** 이 저장소의 공용 `Button` 컴포넌트(`web/src/components/ui/Button.tsx`)는 정확히 "처리 중엔 비활성+문구 표시"용 `loading`/`loadingText` prop을 이미 갖고 있지만, `isFlushing`이 state가 아니라 못 걸었다. flush가 진행 중이든 실패했든 버튼 모양이 같아, 사용자가 눌러도 반응이 없어 보여 반복 클릭할 수 있다.
- **왜 지금 안 고치나:** `isFlushing`을 state로 승격하려면 12.4가 3차까지 리뷰한 재연결·큐잉 상태기계에 렌더 트리거를 추가하는 구조 변경이 필요하다 — `#206`이 명시한 "가장 작은 수정"(재시도 버튼 추가) 범위를 넘는다(A3).
- **트리거:** `ChatRoomMessages.tsx`의 재연결/큐 상태기계를 다시 손대는 다음 작업 — 그 자리에서 `isFlushing`을 state로 승격할지 판단한다.

### DW-521: [구 #221] "다시 보내기" 재시도 버튼에 연타 방지(쿨다운)가 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #221) — 원출처: 2026-07-29 Story 12.6 코드리뷰 adversarial 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼(`#206` 최소 수정).
severity: medium
reason: 데모 규모에서 실측된 피해가 없고, 쿨다운 로직 추가는 이번 최소 수정 범위 밖의 방어적 복잡도다(A2 — 없는 시나리오를 위해 짓지 않는다).
trigger: 실사용에서 연타로 인한 과다 요청이 실제로 관측되거나, `#220`(로딩 상태 승격)을 처리하게 될 때 — 같은 state 승격 작업에 얹어 함께 처리한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼(`#206` 최소 수정).
- **내용:** 자동 재시도(재연결 트리거)는 실제 재연결 이벤트로 빈도가 자연히 제한되는데, 수동 버튼은 그런 제한이 없어 실제 장애 상황에서 연타하면 매번 새 flush 시도가 나간다. 백엔드가 `client_message_id` + UNIQUE 제약으로 멱등하므로 데이터 피해는 없고 낭비뿐이다.
- **왜 지금 안 고치나:** 데모 규모에서 실측된 피해가 없고, 쿨다운 로직 추가는 이번 최소 수정 범위 밖의 방어적 복잡도다(A2 — 없는 시나리오를 위해 짓지 않는다).
- **트리거:** 실사용에서 연타로 인한 과다 요청이 실제로 관측되거나, `#220`(로딩 상태 승격)을 처리하게 될 때 — 같은 state 승격 작업에 얹어 함께 처리한다.

### DW-522: [구 #222] `ChatListBfcacheRefresh`가 Next.js의 문서화되지 않은 popstate 처리 순서에 의존하는데 이를 지켜주는 자동 테스트가 없다

origin: 장부 통합 이관(구 docs/tech-debt.md #222) — 원출처: 2026-07-29 Story 12.6 코드리뷰 adversarial+verification-gap 교차 지적
location: `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`(`#215` 최소 수정) — 뒤로/앞으로가기 전환에서 `pageshow`가 아니라 `popstate`가 오고, `/chat` 페이지 자신에 리스너를 두면 재마운트 전에 이벤트를 놓친다는 실측(콘솔 계측) 위에 전체가 서 있다.
severity: high
reason: jsdom 등 DOM 렌더링 테스트 도구 도입은 이 저장소 전체의 테스트 아키텍처 결정이라(기존에 의도적으로 배제된 선택) 이 스토리의 최소 수정 범위에서 단독으로 판단할 수 없다(A2·A3).
trigger: `#222`와 같은 트리거(Next.js 버전을 올릴 때) — 그 자리에서 뒤로가기 popstate 처리를 브라우저로 재실측한다. 또는 이 저장소에 jsdom 도입을 별도로 결정하게 될 때 — 그 자리에서 실제 렌더링 테스트로 교체한다.
status: open

- **위치:** `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`(`#215` 최소 수정) — 뒤로/앞으로가기 전환에서 `pageshow`가 아니라 `popstate`가 오고, `/chat` 페이지 자신에 리스너를 두면 재마운트 전에 이벤트를 놓친다는 실측(콘솔 계측) 위에 전체가 서 있다.
- **내용:** 이 실측은 이번 스토리 구현 중 직접 확인한 사실이지만, 그걸 지켜주는 자동 테스트가 없다 — `jsdom`이 이 저장소에 설치돼 있지 않아(`vitest.config.ts` 주석이 이미 "jsdom·RTL은 여전히 안 붙인다"로 명시한 기존 방침) 실제 `popstate` 이벤트를 디스패치해 확인하는 테스트를 못 붙이고, 대신 소스 스캔 방식의 `bfcacheRefreshContract.test.ts`(리스너 등록/해제, `router.refresh()`가 `/chat` 가드 안에 있는지, 루트 레이아웃이 컴포넌트를 렌더하는지)만 신설했다. 다음 Next.js 업그레이드가 이 popstate 처리 순서를 바꾸면 CI는 초록인 채로 배지 갱신만 조용히 다시 깨질 수 있다(`#207`의 supabase-js 버전 의존과 같은 위험 종류).
- **왜 지금 안 고치나:** jsdom 등 DOM 렌더링 테스트 도구 도입은 이 저장소 전체의 테스트 아키텍처 결정이라(기존에 의도적으로 배제된 선택) 이 스토리의 최소 수정 범위에서 단독으로 판단할 수 없다(A2·A3).
- **트리거:** `@supabase/supabase-js`·Next.js 버전을 올릴 때(`#207`과 같은 트리거) — 그 자리에서 뒤로가기 popstate 처리를 브라우저로 재실측한다. 또는 이 저장소에 jsdom 도입을 별도로 결정하게 될 때 — 그 자리에서 실제 렌더링 테스트로 교체한다.

### DW-523: [구 #223] `#215` 수정(popstate 가드)이 루트 레이아웃에 있어 채팅과 무관한 모든 페이지의 뒤로가기에서도 실행된다

origin: 장부 통합 이관(구 docs/tech-debt.md #223) — 원출처: 2026-07-29 Story 12.6 코드리뷰 adversarial 지적
location: `web/src/app/layout.tsx`의 `<ChatListBfcacheRefresh />` — `(user)` 라우트 그룹에 전용 layout이 없어 `/chat`·`/chat/[roomId]`의 유일한 공통 조상이 루트 레이아웃뿐이라 이 자리를 택했다.
severity: medium
reason: `(user)` 라우트 그룹에 전용 layout을 신설해 이 리스너를 옮기는 것은 라우트 구조 변경이라 이 스토리(채팅 검증)의 최소 수정 범위 밖이다(A3).
trigger: 같은 패턴(단일 페이지 사정으로 루트 레이아웃에 리스너·부수효과를 추가)이 두 번째로 필요해지는 시점 — 그 자리에서 `(user)` 라우트 그룹 전용 layout 신설 여부를 판단한다.
status: open

- **위치:** `web/src/app/layout.tsx`의 `<ChatListBfcacheRefresh />` — `(user)` 라우트 그룹에 전용 layout이 없어 `/chat`·`/chat/[roomId]`의 유일한 공통 조상이 루트 레이아웃뿐이라 이 자리를 택했다.
- **내용:** 앱의 모든 페이지에서 뒤로/앞으로가기 시 이 popstate 핸들러가 매번 실행된다. 지금은 내부 `location.pathname === '/chat'` 가드로 안전하지만, "특정 페이지 하나의 사정"을 위해 앱 전체 레이아웃에 리스너를 박는 패턴이 반복되면 `layout.tsx`가 주인 없는 부수효과 모음집처럼 비대해질 위험이 있다.
- **왜 지금 안 고치나:** `(user)` 라우트 그룹에 전용 layout을 신설해 이 리스너를 옮기는 것은 라우트 구조 변경이라 이 스토리(채팅 검증)의 최소 수정 범위 밖이다(A3).
- **트리거:** 같은 패턴(단일 페이지 사정으로 루트 레이아웃에 리스너·부수효과를 추가)이 두 번째로 필요해지는 시점 — 그 자리에서 `(user)` 라우트 그룹 전용 layout 신설 여부를 판단한다.

### DW-524: [구 #224] 큐가 다른 경로로 비워지면 "N건 미전송" 안내가 화면에 박제되고 재시도 버튼으로도 못 지운다

origin: 장부 통합 이관(구 docs/tech-debt.md #224) — 원출처: 2026-07-29 Story 12.6 후속 코드리뷰 adversarial+edge-case 교차 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `flushQueue()` 도입부 — `const queueSnapshot = ...; if (queueSnapshot.length === 0) return;`(빈 큐 조기 반환)이 `setQueueStuckNotice(null)` 없이 바로 빠져나간다.
severity: high
reason: 이 조기 반환과 안내 칸은 둘 다 12.4가 만든 기존 코드로 이번 스토리가 만든 결함이 아니고, Story 12.6의 인텐트가 "`#206`·`#215` 외의 새 결함은 코드로 고치지 않고 대장에 등재한다"를 명시적 범위 제한으로 못박았다. 수정 자체는 한 줄이지만 재연결·큐 상태기계의 안내 해제 규칙을 바꾸는 것이라 실측 없이 넣지 않는다.
trigger: `ChatRoomMessages.tsx`의 재연결/큐 상태기계를 다시 손대는 다음 작업 — `#220`(`isFlushing` state 승격)과 같은 자리이므로 그때 함께 처리하고, 부분 실패 → 에코 도착 → 버튼 클릭 순서를 로컬 스택에서 실제로 재현해 확인한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `flushQueue()` 도입부 — `const queueSnapshot = ...; if (queueSnapshot.length === 0) return;`(빈 큐 조기 반환)이 `setQueueStuckNotice(null)` 없이 바로 빠져나간다.
- **내용:** `queueStuckNotice`("메시지 N건을 아직 보내지 못했습니다…")를 지우는 자리는 flush가 **끝까지 돌아 큐를 다 비운** 경로 하나뿐이다. 그런데 큐는 그 경로 말고도 비워질 수 있다 — 부분 실패로 안내가 뜬 뒤, 실제로는 DB에 저장됐지만 응답만 유실됐던 메시지의 Broadcast 에코가 도착하면 `removePendingById`가 그 항목을 큐에서 걷어간다(같은 파일이 주석으로 이미 인정하는 경로다). 그 상태에서 큐는 비었는데 안내는 남고, 사용자가 새로 붙은 "다시 보내기"를 눌러도 `flushQueue`가 빈 스냅샷을 보고 즉시 반환해 **안내가 영원히 안 지워진다**. 실제로는 전부 전송됐는데 "미전송"이라고 알리는 거짓 경보이고, 탈출구는 방 전환이나 새로고침뿐이다.
- **왜 지금 안 고치나:** 이 조기 반환과 안내 칸은 둘 다 12.4가 만든 기존 코드로 이번 스토리가 만든 결함이 아니고, Story 12.6의 인텐트가 "`#206`·`#215` 외의 새 결함은 코드로 고치지 않고 대장에 등재한다"를 명시적 범위 제한으로 못박았다. 수정 자체는 한 줄(`if (queueSnapshot.length === 0) { setQueueStuckNotice(null); return; }`)이지만, 그 한 줄이 재연결·큐 상태기계의 안내 해제 규칙을 바꾸는 것이라 실측 없이 넣지 않는다.
- **트리거:** `ChatRoomMessages.tsx`의 재연결/큐 상태기계를 다시 손대는 다음 작업 — `#220`(`isFlushing` state 승격)과 같은 자리이므로 그때 함께 처리하고, 부분 실패 → 에코 도착 → 버튼 클릭 순서를 로컬 스택에서 실제로 재현해 확인한다.

### DW-525: [구 #225] `#215` 수정이 `/chat`에서만 돌아 다른 페이지로 뒤로가기하면 안읽음 배지가 여전히 옛값이다

origin: 장부 통합 이관(구 docs/tech-debt.md #225) — 원출처: 2026-07-29 Story 12.6 후속 코드리뷰 verification-gap+edge-case 교차 지적
location: `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`의 `if (path === '/chat') router.refresh();` 가드 — 그리고 `#215`가 이 수정으로 "✅ 해소"로 닫힌 사실.
severity: high
reason: Story 12.6의 인텐트와 `#215`의 처방이 둘 다 "`/chat` 목록 페이지"의 뒤로가기 배지로 범위를 명시했고, 그 범위는 실제로 닫혔다. 전 경로로 넓히려면 `#223`(리스너가 앱 전체에 있음)·`#209`/`#183`(왕복 비용)과 정면으로 맞물리는 설계 판단이라 확인 전용 스토리에서 단독으로 정할 일이 아니다.
trigger: `#223`(`(user)` 전용 layout 신설 판단)을 처리할 때 함께 — 리스너를 옮기는 그 자리에서 "배지를 가진 모든 경로로 넓힐 것인가"를 같이 정한다. 그전에 위 실측 한계부터 해소한다(`/listings/[id]`에서 뒤로가기 재현).
status: open

- **위치:** `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`의 `if (path === '/chat') router.refresh();` 가드 — 그리고 `#215`가 이 수정으로 "✅ 해소"로 닫힌 사실.
- **내용:** `#215`가 기록한 근본 원인("Next는 스크롤 복원을 위해 back/forward를 항상 Router Cache에서 되살린다")은 라우트를 가리지 않는 Next 동작인데, 수정은 착지 경로가 `/chat`일 때만 새로고침한다. 안읽음 배지는 `AppHeader`가 `chat_unread_count()` RPC로 계산해 소비자용 페이지 **10곳 전부**에 같은 방식으로 렌더한다(`/`, `/listings/[id]`, `/search`, `/wishlist`, `/ai`, `/account`, `/sell`, `/chat/[roomId]` 등). 그래서 `/listings/[id]` → 문의하기 → `/chat/<roomId>`(읽음 기록) → 브라우저 뒤로가기 → `/listings/[id]` 같은 자연스러운 흐름에서는 같은 증상이 그대로 남는다. 또 같은 이유로 **cross-document bfcache 복원**(외부 사이트로 나갔다 브라우저 뒤로가기로 복귀 — 이때는 `popstate`가 아니라 `pageshow`+`event.persisted`가 온다)도 이 리스너가 못 잡는다. 컴포넌트 이름이 `...BfcacheRefresh`인데 실제로는 `popstate`만 듣는 것도 여기서 온다.
- **실측 한계(정직하게 남김):** 이 항목은 소스(모든 `AppHeader` 호출 지점이 동일하게 배지를 계산한다는 사실)와 `#215` 자신이 적어둔 근본 원인으로부터 도출했다. 나머지 9개 경로에서 브라우저로 직접 재측정하지는 **않았다** — 처리할 때 먼저 재현부터 확인한다.
- **왜 지금 안 고치나:** Story 12.6의 인텐트와 `#215`의 처방이 둘 다 "**`/chat` 목록 페이지**의 뒤로가기 배지"로 범위를 명시했고, 그 범위는 실제로 닫혔다. 전 경로로 넓히려면 가드를 걷어내고 모든 뒤로가기에서 `router.refresh()`를 돌려야 하는데, 그건 `#223`(리스너가 앱 전체에 있음)·`#209`/`#183`(왕복 비용)과 정면으로 맞물리는 설계 판단이라 확인 전용 스토리에서 단독으로 정할 일이 아니다.
- **트리거:** `#223`(`(user)` 전용 layout 신설 판단)을 처리할 때 함께 — 리스너를 옮기는 그 자리에서 "배지를 가진 모든 경로로 넓힐 것인가"를 같이 정한다. 그전에 위 실측 한계부터 해소한다(`/listings/[id]`에서 뒤로가기 재현).

### DW-526: [구 #226] 재시도 버튼의 끊김 가드가 실시간 웹소켓 상태를 보는데 정작 전송은 HTTP다

origin: 장부 통합 이관(구 docs/tech-debt.md #226) — 원출처: 2026-07-29 Story 12.6 후속 코드리뷰 adversarial 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼 — `disabled={isDisconnected}` + `onClick`의 `if (!disconnectedRef.current)` 가드.
severity: medium
reason: 어느 쪽이 옳은지는 "웹소켓이 끊긴 채로 HTTP 전송을 시도하게 둘 것인가"라는 제품·설계 판단이고, 판단하려면 소켓만 끊긴 상태를 실제로 만들어 insert가 성공하는지부터 실측해야 한다. 확인 전용 스토리의 최소 수정 범위를 넘는다(A2·A3).
trigger: `#220`(`isFlushing` state 승격)이나 `#224`(안내 해제 규칙)를 처리하며 이 버튼 주변을 다시 손댈 때 — 그 자리에서 로컬 스택으로 "웹소켓만 차단 + HTTP 정상" 상태를 만들어 재시도가 실제로 성공하는지 재본 뒤 정한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 재시도 버튼 — `disabled={isDisconnected}` + `onClick`의 `if (!disconnectedRef.current)` 가드.
- **내용:** `disconnectedRef`/`isDisconnected`는 Realtime **채널 구독 상태**(`CHANNEL_ERROR`·`TIMED_OUT`)에서만 세팅된다. 그런데 이 버튼이 부르는 `flushQueue()` → `sendMessage()`는 `supabase.from('chat_messages').insert(...)`, 즉 웹소켓과 무관한 **PostgREST HTTP 요청**이다. 그래서 "웹소켓만 끊기고 네트워크는 멀쩡한" 상태(토큰 갱신·서버 재기동 등으로 흔하다)에서는 재시도가 성공할 수 있는데도 버튼이 비활성으로 잠긴다 — 재시도 수단이 가장 필요한 상황에서 막히는 셈이다. 반대로 진짜 오프라인이면 insert가 실패해 항목이 큐에 그대로 남으므로(기존 동작) 가드를 없애도 데이터 피해는 없다.
- **이번에 한 것:** 가드 자체는 유지하되 "멀쩡해 보이는데 눌러도 아무 일 없는" 조용한 실패만 없앴다(`disabled` 추가로 잠긴 상태를 시각적으로 드러냄). 가드를 없앨지, `navigator.onLine`처럼 실제 전송 경로의 생사를 보는 신호로 바꿀지는 동작 변경이라 따로 둔다.
- **왜 지금 안 고치나:** 어느 쪽이 옳은지는 "웹소켓이 끊긴 채로 HTTP 전송을 시도하게 둘 것인가"라는 제품·설계 판단이고, 판단하려면 소켓만 끊긴 상태를 실제로 만들어 insert가 성공하는지부터 실측해야 한다. 확인 전용 스토리의 최소 수정 범위를 넘는다(A2·A3).
- **트리거:** `#220`(`isFlushing` state 승격)이나 `#224`(안내 해제 규칙)를 처리하며 이 버튼 주변을 다시 손댈 때 — 그 자리에서 로컬 스택으로 "웹소켓만 차단 + HTTP 정상" 상태를 만들어 재시도가 실제로 성공하는지 재본 뒤 정한다.

### DW-527: [구 #227] 방을 옮기면 아직 못 보낸 오프라인 큐가 **경고 없이 통째로 버려진다**

origin: 장부 통합 이관(구 docs/tech-debt.md #227) — 원출처: 2026-07-29 Story 12.6 2차 후속 리뷰 edge-case-hunter 지적
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 roomId 전환 리셋 블록 — `setPendingQueueAndRef([])`와 `setQueueStuckNotice(null)`이 나란히 있다.
severity: high
reason: 코드 자체는 12.4 것이라 이번 스토리가 만든 결함은 아니지만, 이번 스토리가 그 옆에 "다시 보내기" 버튼(`#206`)을 붙여 "이 메시지는 복구할 수 있다"고 사용자에게 약속했기 때문에 그 약속이 방 전환 한 번으로 조용히 깨지는 비대칭이 새로 생겼다. 인텐트가 "`#206`·`#215` 외의 새 결함은 코드로 고치지 않는다"로 범위를 못박아 이번엔 등재만 한다.
trigger: `#220`(`isFlushing` state 승격)이나 `#224`(안내 해제 규칙)로 이 큐 상태기계를 다시 손댈 때 — 같은 자리이므로 함께 정한다. 선택지는 ① 방 전환 시 큐가 비어있지 않으면 확인을 받는다, ② 큐를 roomId별로 보존한다(초기화 대신 스코프 분리), ③ 지금대로 두되 최소한 버려진다는 사실을 알린다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 roomId 전환 리셋 블록 — `setPendingQueueAndRef([])`와 `setQueueStuckNotice(null)`이 나란히 있다.
- **내용:** 방 전환은 A방의 잔상이 B방에 비치지 않게 pending 버블·안내·큐를 전부 지운다(12.4가 의도적으로 넣은 초기화다). 그런데 그 큐에는 **아직 서버에 도달하지 못한 사용자의 실제 메시지**가 들어 있을 수 있다 — 오프라인에서 친 메시지, 또는 flush 부분 실패로 남은 항목이다. 방 목록으로 돌아가거나 다른 방을 여는 순간 그 메시지들은 확인 절차도 경고도 없이 사라지고, 화면의 "N건 미전송" 안내까지 같이 지워져 **사라졌다는 사실 자체가 안 남는다**. 로컬 저장(localStorage 등)이 없어 새로고침에도 동일하다.
- **왜 이제 와서 등재하나:** 코드 자체는 12.4 것이고 이번 스토리가 만든 결함이 아니다. 다만 이번 스토리가 그 옆에 "다시 보내기" 버튼(`#206`)을 붙여 **"이 메시지는 복구할 수 있다"고 사용자에게 약속**했기 때문에, 그 약속이 방 전환 한 번으로 조용히 깨지는 비대칭이 새로 생겼다. 인텐트가 "`#206`·`#215` 외의 새 결함은 코드로 고치지 않는다"로 범위를 못박아 이번엔 등재만 한다.
- **실측 한계(정직하게 남김):** 소스 독해로 확인했다(리셋 블록이 큐를 무조건 비운다). 브라우저로 "오프라인에서 2건 치고 방 전환" 시나리오를 직접 돌려 사라지는 것을 눈으로 보지는 **않았다** — 처리할 때 재현부터 한다.
- **트리거:** `#220`(`isFlushing` state 승격)이나 `#224`(안내 해제 규칙)로 이 큐 상태기계를 다시 손댈 때 — 같은 자리이므로 함께 정한다. 선택지는 ① 방 전환 시 큐가 비어있지 않으면 확인을 받는다, ② 큐를 roomId별로 보존한다(초기화 대신 스코프 분리), ③ 지금대로 두되 최소한 버려진다는 사실을 알린다.

### DW-528: [구 #228] `#215` 수정이 기대는 **문서화되지 않은 Next 내부 동작이 `#222`가 적은 것 말고도 2건 더** 있다

origin: 장부 통합 이관(구 docs/tech-debt.md #228) — 원출처: 2026-07-29 Story 12.6 2차 후속 리뷰 adversarial 지적
location: `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`의 `useEffect(..., [router])` + `if (path === '/chat') router.refresh();`.
severity: high
reason: ②는 `router`를 ref에 담고 의존성을 비우면 없앨 수 있지만, 지금 동작하는 코드의 구조 변경이고 확인 전용 스토리의 범위 밖이다(A3). ①은 애초에 고칠 대상이 아니라 기록해야 할 의존이다.
trigger: `#222`와 같은 트리거(Next.js 버전을 올릴 때) — 그 자리에서 브라우저로 뒤로가기 배지 갱신을 재실측하고, 깨졌다면 여기 ①·② 중 어느 가정이 무너졌는지부터 확인한다.
status: open

- **위치:** `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`의 `useEffect(..., [router])` + `if (path === '/chat') router.refresh();`.
- **내용:** `#222`는 "popstate가 `/chat` 재마운트보다 먼저 온다"는 **순서** 의존만 기록했다. 같은 코드가 기대는 것이 두 가지 더 있다.
  ① **`router.refresh()`의 무효화 범위.** popstate가 발생하는 시점에 브라우저 URL은 이미 `/chat`이지만 Next 라우터의 내부 상태는 아직 `/chat/[roomId]`다(`#222`가 기록한 바로 그 순서 때문이다). 즉 이 호출은 "`/chat`을 새로고침"하는 것이 아니라 **Router Cache 전체를 무효화**하는 것으로 동작하고, 그래서 뒤이어 마운트되는 `/chat`이 새 데이터를 받는다. 만약 Next가 `refresh()`를 현재 세그먼트로 좁히는 최적화를 넣으면(충분히 있을 법하다) 방 라우트만 새로고침되고 `/chat`은 캐시에서 복원돼 **배지가 조용히 재발**한다 — 코드는 `path === '/chat'` 가드 때문에 `/chat`을 겨냥한 것처럼 읽히므로 디버깅하는 사람을 오도한다.
  ② **`useRouter()` 반환값의 참조 안정성.** 의존성 배열이 `[router]`라, 전환 중 router 객체의 신원(identity)이 바뀌면 리스너가 해제·재등록되면서 바로 그 popstate를 놓칠 수 있다 — 이 파일이 헤더 주석 10줄을 들여 피하려 한 "닭이 먼저냐 달걀이 먼저냐" 실패가 그대로 재현되는 경로다. 현재 동작한다는 것은 실측으로 확인됐지만(배지가 갱신됐다), 안정성이 보장된다는 문서 근거는 없다.
- **실측 한계(정직하게 남김):** 두 항목 모두 소스와 `#222`가 기록한 순서 실측에서 **도출한 추론**이다. 라우터 캐시 무효화 범위를 계측하거나 router 신원 변화를 로깅해 확인하지는 **않았다**.
- **왜 지금 안 고치나:** ②는 `router`를 ref에 담고 의존성을 비우면 없앨 수 있지만, 지금 동작하는 코드의 구조 변경이고 확인 전용 스토리의 범위 밖이다(A3). ①은 애초에 고칠 대상이 아니라 **기록해야 할 의존**이다.
- **트리거:** `#222`와 **같은 트리거**(Next.js 버전을 올릴 때) — 그 자리에서 브라우저로 뒤로가기 배지 갱신을 재실측하고, 깨졌다면 여기 ①·② 중 어느 가정이 무너졌는지부터 확인한다.

### DW-529: [구 #229] web CI에 `next build` 단계가 없어 **RSC 경계 위반이 CI 초록으로 통과**한다

origin: 장부 통합 이관(구 docs/tech-debt.md #229) — 원출처: 2026-07-29 Story 12.6 2차 후속 리뷰 verification-gap 지적
location: `.github/workflows/tests.yml`의 `web` 잡 — 스텝이 `npm ci` → `npm run lint` → `npm test`뿐이다(빌드 없음).
severity: high
reason: `npm run build`를 CI에 추가하면 web 잡 시간이 크게 늘고(Turbopack 풀빌드) 빌드에 필요한 환경변수(`NEXT_PUBLIC_*`) 처리 방침도 함께 정해야 하는 CI 파이프라인 정책 변경이라, 확인 전용 스토리에서 단독으로 결정할 일이 아니다. `docs/tech-debt.md` `#168`(E2E를 CI에 안 넣은 결정)과 같은 종류의 판단이다.
trigger: ① 실제로 배포 빌드가 RSC 경계 위반으로 한 번이라도 깨질 때 — 그 자리에서 "CI 시간 vs 배포 실패" 절충을 다시 잰다. ② `#168`(E2E CI 편입)을 처리할 때 — 어차피 web 잡의 시간·시크릿 정책을 다시 짜므로 빌드 스텝도 같이 정한다.
status: open

- **위치:** `.github/workflows/tests.yml`의 `web` 잡 — 스텝이 `npm ci` → `npm run lint` → `npm test`뿐이다(빌드 없음).
- **실측(이번에 직접 돌려 확인):** `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx`에서 `'use client'` 한 줄을 지우면 — 이 파일은 **서버 컴포넌트인 루트 레이아웃이 직접 import**하므로 앱 전체가 못 빌드된다 — `npm run lint`와 `npm test`(290건)는 **전부 통과**하고, `npm run build`만 실패한다(`You're importing a module that depends on 'useRouter'/'useEffect' into a React Server Component module`, 2 errors). 즉 CI는 초록인 채로 **배포 빌드에서야** 터진다. 이번 스토리가 `#215` 수정으로 루트 레이아웃에 클라이언트 컴포넌트를 처음 매단 탓에 이 사각지대의 폭발 반경이 "한 라우트"에서 "전 라우트"로 커졌다.
- **이번에 한 것:** 이 한 축만 `bfcacheRefreshContract.test.ts`에 정적 단언(`'use client'`가 첫 줄에 있다)으로 막아 뒀다(뮤테이션 red→green 확인). 하지만 이건 **이 파일 하나**를 막은 것이지 RSC 경계 위반 전반을 막은 것이 아니다 — 다음에 누가 다른 클라이언트 컴포넌트를 서버 컴포넌트에 매달면 같은 방식으로 CI를 통과한다.
- **왜 지금 안 고치나:** `npm run build`를 CI에 추가하면 web 잡 시간이 크게 늘고(Turbopack 풀빌드), 빌드에 필요한 환경변수(`NEXT_PUBLIC_*`) 처리 방침을 함께 정해야 한다 — CI 파이프라인 정책 변경이라 확인 전용 스토리에서 단독으로 결정할 일이 아니다. `docs/tech-debt.md` `#168`(E2E를 CI에 안 넣은 결정)과 같은 종류의 판단이다.
- **트리거:** ① 실제로 배포 빌드가 RSC 경계 위반으로 한 번이라도 깨질 때 — 그 자리에서 "CI 시간 vs 배포 실패" 절충을 다시 잰다. ② `#168`(E2E CI 편입)을 처리할 때 — 어차피 web 잡의 시간·시크릿 정책을 다시 짜므로 빌드 스텝도 같이 정한다.

### DW-530: [구 #230] 재시도 버튼 배선의 **실행 순서 불변식**이 검사로 고정돼 있지 않다

origin: 장부 통합 이관(구 docs/tech-debt.md #230) — 원출처: 2026-07-29 Story 12.6 2차 후속 리뷰 verification-gap 뮤테이션 실증
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` — 방 전환 리셋(`flushQueueRef.current = () => {}`, async IIFE 안)과 실제 배선(`flushQueueRef.current = () => void flushQueue()`, effect 바디)이 서로 다른 자리에 있다.
severity: medium
reason: 제대로 고치는 방법은 두 갈래인데 둘 다 이번 범위 밖이다 — 리셋을 async IIFE 밖으로 옮겨 어휘 순서를 실행 순서와 맞추는 것은 동작하는 12.4 상태기계의 초기화 위치 변경이라 A3, "리셋이 첫 `await`보다 앞에 있다"를 정적 단언으로 추가하는 것은 창 경계를 늘리는 취약한 검사라 이득이 불분명하다.
trigger: `#220`(`isFlushing` state 승격)으로 이 effect를 다시 손댈 때 — 어차피 초기화·배선 자리를 다시 그리므로, 그 자리에서 ①(순서를 구조로 보장)을 함께 적용한다.
status: open

- **위치:** `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` — 방 전환 리셋(`flushQueueRef.current = () => {}`, async IIFE 안)과 실제 배선(`flushQueueRef.current = () => void flushQueue()`, effect 바디)이 서로 다른 자리에 있다.
- **내용:** 버튼이 동작하려면 **리셋이 배선보다 먼저** 실행돼야 한다. 지금은 리셋이 IIFE의 첫 `await` 앞에 있어 동기적으로 먼저 돌기 때문에 성립한다 — 즉 **텍스트 위치가 아니라 실행 순서**가 불변식이다. 뮤테이션 실증(이번 리뷰): 그 IIFE 맨 앞에 `await Promise.resolve();` 한 줄만 끼우면 리셋이 다음 마이크로태스크로 밀려 **배선을 덮어써** 버튼이 영구 no-op이 되는데(= `#206`이 조용히 재발), `queueRetryWiringContract.test.ts`의 위치 검사는 텍스트 위치만 보므로 스위트 288건이 그대로 통과했다.
- **이번에 한 것:** 검사가 이 축을 못 본다는 사실을 `queueRetryWiringContract.test.ts` 헤더 주석에 실측과 함께 명시했다(CLAUDE.md B4 — "그 검사가 안 보는 것을 검사 옆에 적는다"). 고정은 하지 않았다.
- **왜 지금 안 고치나:** 제대로 고치는 방법은 두 갈래인데 둘 다 이번 범위 밖이다 — ① 리셋을 async IIFE 밖(effect 바디, 배선 바로 위)으로 옮겨 **어휘 순서 = 실행 순서**로 만든다(동작하는 12.4 상태기계의 초기화 위치 변경이라 A3). ② "리셋이 첫 `await`보다 앞에 있다"를 정적 단언으로 추가한다(창 경계를 또 하나 늘리는 취약한 검사라 이득이 불분명하다).
- **트리거:** `#220`(`isFlushing` state 승격)으로 이 effect를 다시 손댈 때 — 어차피 초기화·배선 자리를 다시 그리므로, 그 자리에서 ①(순서를 구조로 보장)을 함께 적용한다.

### DW-532: [구 #232] `realtime.messages` 파티션 유지는 "자동"이 아니라 **"Realtime 테넌트가 활성일 때 자동"** — 원격은 확인 직전까지 파티션이 0개였고 그 상태에선 방송이 조용히 사라진다

origin: 장부 통합 이관(구 docs/tech-debt.md #232) — 원출처: 2026-07-29 원격 실측
location: 원격 프로젝트 `psrnsasxpkpwqdukjdmt`의 `realtime.messages` / `supabase/migrations/0023_chat_realtime_broadcast.sql` / `scripts/migration-check-prelude.sql` realtime 스텁 문단.
severity: high
reason: 마이그레이션으로 파티션을 만드는 건 플랫폼 소유 객체를 우리가 관리하겠다는 뜻이라 과설계이고(A2), 실사용 중에는 Realtime 서비스가 유지한다. 감시를 붙이는 것도 `#99`(측정 인프라 부재)와 같은 축이라 별도 판단이다.
trigger: **① 운영에서 "채팅 메시지는 저장되는데 상대가 못 본다"가 보고되면 제일 먼저 이걸 본다** — `select count(*) from pg_inherits i join pg_class c on c.oid=i.inhparent join pg_namespace n on n.oid=c.relnamespace where n.nspname='realtime' and c.relname='messages'` 가 0이면 이 항목이다(복구는 클라이언트 1회 구독). **② Epic 13(성능·게이트 정비)에서 관측 수단을 논할 때 같이 판단**한다.
status: open

- **위치:** 원격 프로젝트 `psrnsasxpkpwqdukjdmt`의 `realtime.messages` / `supabase/migrations/0023_chat_realtime_broadcast.sql` / `scripts/migration-check-prelude.sql` realtime 스텁 문단.
- **어떻게 나왔나:** `#196` ⓒ("파티션 유지가 자동인가")를 확인하다 나왔다. 확인 시작 시점의 원격에는 `realtime.messages`의 **자식 파티션이 0개**였고, 그 상태에서 INSERT는 `23514 no partition of relation "messages" found for row`로 실패했다(실측, 롤백함). anon 키로 **클라이언트를 한 번 구독시키자**(`SUBSCRIBED`) Realtime 서비스가 곧바로 5일치(`messages_2026_07_28`~`08_01`)를 만들었고, 그 뒤 같은 경로가 1행 성공했다(`private=t`).
- **왜 위험한가:** 파티션이 없을 때 나는 실패는 **플랫폼 `realtime.send()`의 `exception when others then raise warning`이 삼킨다.** 그래서 `chat_messages` INSERT는 성공하고 **방송만 사라진다** — 12.3이 폴링을 제거했으므로 받는 쪽은 **새로고침 전까지 아무것도 못 본다.** 앱은 정상으로 보이고 에러도 안 난다(`#194`①·`#195`①·`#197`과 같은 무음 실패 계열).
- **지금은 왜 무해한가:** 이 프로젝트가 Realtime을 **한 번도 쓴 적이 없어서** 비어 있었던 것이고, 실사용이 시작되면 서비스가 유지한다(로컬 스택은 6일치를 갖고 있다 — 실측). 즉 "처음 한 번" 문제이며 지금은 채워져 있다.
- **남는 조건:** 파티션 생성 주체가 **DB 안이 아니라 Realtime 서비스**다(`realtime` 스키마에 파티션 유지 함수가 없고 `pg_cron`도 없음 — 실측). 따라서 **테넌트가 오래 무활동이면 다시 비어 같은 무음 실패가 재발할 수 있다.** 이 레포에는 그걸 알아챌 관측 수단이 없다.
- **왜 지금 안 고치나:** 마이그레이션으로 파티션을 만드는 건 플랫폼 소유 객체를 우리가 관리하겠다는 뜻이라 과설계이고(A2), 실사용 중에는 서비스가 유지한다. 감시를 붙이는 것도 `#99`(측정 인프라 부재)와 같은 축이라 별도 판단이다.
- **트리거:** **① 운영에서 "채팅 메시지는 저장되는데 상대가 못 본다"가 보고되면 제일 먼저 이걸 본다** — `select count(*) from pg_inherits i join pg_class c on c.oid=i.inhparent join pg_namespace n on n.oid=c.relnamespace where n.nspname='realtime' and c.relname='messages'` 가 0이면 이 항목이다(복구는 클라이언트 1회 구독). **② Epic 13(성능·게이트 정비)에서 관측 수단을 논할 때 같이 판단**한다.

### DW-533: [구 #233] 무인 루프의 verify 게이트는 `tests/integration`을 **구조적으로 못 돌린다** — Epic 12의 실DB 테스트가 CI에 닿아서야 red가 났다

origin: 장부 통합 이관(구 docs/tech-debt.md #233) — 원출처: 2026-07-29 develop 병합 직후 실측
location: `.bmad-loop/policy.toml` `[verify].commands`의 `cd api && .venv/bin/python -m pytest -q` vs `api/tests/integration/conftest.py:33-35`(`TEST_DATABASE_URL`이 없으면 모듈 전체 skip) vs `.github/workflows/tests.yml`의 `api (실DB 통합)` 잡.
severity: critical
reason: verify에 실DB 층을 넣으려면 일회용 postgres 컨테이너를 띄우고 프렐류드+마이그를 붓는 준비 단계가 필요한데, 그건 `check_migrations.py`·E2E를 verify에서 뺀 것과 같은 결합(도커 의존)을 다시 들이는 일이라, 넣을지 `#168`(E2E를 CI에)과 함께 CI 쪽으로 몰지는 별개 판단이다.
trigger: **Epic 13 착수 전** — `#168`과 **같은 자리에서 함께 판단**한다(둘 다 "루프가 안 보는 층을 어디서 볼 것인가"라는 한 질문의 두 갈래다). 그 전까지의 임시 방편: **에픽 마감 시 `develop` 병합 전에** 일회용 컨테이너로 `tests/integration` 전량을 한 번 돌린다(이번에 실제로 그렇게 잡았다).
status: open

- **위치:** `.bmad-loop/policy.toml` `[verify].commands`의 `cd api && .venv/bin/python -m pytest -q` vs `api/tests/integration/conftest.py:33-35`(`TEST_DATABASE_URL`이 없으면 모듈 전체 skip) vs `.github/workflows/tests.yml`의 `api (실DB 통합)` 잡.
- **무슨 일이 있었나:** Epic 12를 `develop`에 병합하자 CI `api (실DB 통합)` 잡이 즉시 red가 됐다 — `test_chat_unread_real_db.py` **4건**이 `InsufficientPrivilege: permission denied for schema auth`로 죽었다. 원인은 프렐류드에 `grant usage on schema auth`가 없던 것(→ 같은 커밋에서 고침, red→green 실측). **문제는 결함 자체가 아니라 그것이 여기까지 온 경로다.**
- **왜 루프가 못 잡았나(구조적):** 루프의 verify는 `TEST_DATABASE_URL` 없이 pytest를 돌린다 → `tests/integration`은 **전부 skip**된다(실측: 그 파일만 돌리면 `10 skipped`). 즉 **12-5가 새로 만든 실DB 테스트는 루프가 한 번도 실행한 적이 없다.** 스토리는 6개 다 `done`으로 닫혔고 리뷰도 2회씩 돌았지만, 이 층은 아무도 안 밟았다. dev 세션이 자기 로컬에서 손으로 돌린 기록은 있으나(#211 문단) **게이트가 아니라 사람의 습관**이었다.
- **왜 🔴인가:** `#181`이 *"검사층 전체가 관측 안 됨"* 으로 잡았던 것과 같은 축인데, 그때 고친 건 "CI가 red인 걸 아무도 안 봤다"였고 **"루프가 CI가 보는 것을 안 본다"는 그대로 남아 있었다.** 그래서 에픽 전체가 끝난 뒤에야 red가 드러났다 — 되돌리기 비싼 시점이다. 이번엔 원인이 프렐류드 두 줄이라 싸게 끝났지만, 같은 구조면 다음엔 스토리 코드일 수 있다.
- **왜 지금 안 고치나:** verify에 실DB 층을 넣으려면 일회용 postgres 컨테이너를 띄우고 프렐류드+마이그를 붓는 준비 단계가 필요하다(로컬 재현은 `#233` 이 항목의 실측 절차 그대로 — 약 10초). 그런데 그건 `check_migrations.py`·E2E를 verify에서 뺀 것과 **같은 결합**(도커 의존)을 다시 들이는 일이라, 넣을지/`#168`(E2E를 CI에)과 함께 CI 쪽으로 몰지는 별개 판단이다.
- **트리거:** **Epic 13 착수 전** — `#168`과 **같은 자리에서 함께 판단**한다(둘 다 "루프가 안 보는 층을 어디서 볼 것인가"라는 한 질문의 두 갈래다). 그 전까지의 임시 방편: **에픽 마감 시 `develop` 병합 전에** 일회용 컨테이너로 `tests/integration` 전량을 한 번 돌린다(이번에 실제로 그렇게 잡았다).

### DW-534: [구 #234] 원격 DB가 레포의 마이그레이션과 같은지 **확인하는 수단이 없다** — 손으로 옮기다 실제로 한 줄이 달라졌다

origin: 장부 통합 이관(구 docs/tech-debt.md #234) — 원출처: 2026-07-29 0022~0025 원격 적용 중 실측
location: `supabase/migrations/0024_chat_room_reads.sql:90-106`(`chat_rooms_touch_last_message`) · 원격 프로젝트 `psrnsasxpkpwqdukjdmt` · `docs/deployment-runbook.md`(원격 적용 절차).
severity: high
reason: 자동 대조를 붙이려면 CI가 원격에 붙어야 하는데 이 레포는 `service_role` 키를 두지 않는다(`conventions.md` §5) — 권한 축을 새로 열어야 하는 결정이라 별개 판단이다. 당장의 값싼 대안은 적용을 손으로 옮기지 않는 것(파일 내용을 그대로 전달)과 적용 직후 로직 해시 대조이며, 이번에 실제로 쓴 절차가 그것이다.
trigger: **다음번 원격 마이그레이션 적용 직전** — 그 자리에서 (a) 파일 원문을 그대로 적용하고 (b) 적용 후 이번과 같은 로직 해시 대조를 돌린다. 절차를 `deployment-runbook.md`에 못박을지는 그때 판단한다(지금 적으면 문서만 늘고 실행되지 않는다 — B9).
status: open

- **위치:** `supabase/migrations/0024_chat_room_reads.sql:90-106`(`chat_rooms_touch_last_message`) · 원격 프로젝트 `psrnsasxpkpwqdukjdmt` · `docs/deployment-runbook.md`(원격 적용 절차).
- **무슨 일이 있었나:** 0022~0025를 원격에 적용하면서 0024 본문을 **손으로 옮겼는데**, 파일은 `set last_message_at = greatest(last_message_at, new.created_at)`(단조증가만 허용 — 코드리뷰가 일부러 넣은 것)인데 적용된 것은 `set last_message_at = new.created_at`(무조건 덮어쓰기)였다. **동작이 다른 코드가 운영에 올라갔다.** 곧바로 파일 원본으로 재적용해 바로잡았고, 로컬과 원격의 함수 3종을 **주석을 뺀 로직 해시로 대조**해 일치를 확인했다(`chat_messages_broadcast`·`chat_rooms_touch_last_message`·`chat_unread_count` 3/3 동일).
- **무엇이 잡았나 / 무엇이 못 잡았나:** 잡은 건 **사후 대조 한 번**뿐이다. 마이그레이션 게이트(`check_migrations.py`)는 빈 컨테이너에 파일을 붓는 검사라 **원격이 그 파일과 같은지는 보지 않는다**(그 파일 헤더가 스스로 "원격 매니지드 DB엔 절대 적용하지 않는다"고 못박고 있다). `migration-gate.yml`도 같다. 즉 **레포↔원격 드리프트를 잡는 자리가 레포 어디에도 없다** — 이번엔 내가 대조했으니 안 것이지, 안 했으면 조용히 남았다.
- **왜 이게 조용한가:** 두 정의 모두 문법이 맞고 트리거도 정상 발화한다. 차이는 **동시 전송처럼 시각 역전이 일어날 때만** 드러난다(방 목록 정렬이 뒤로 되돌아감). 재현 조건이 좁아 눈으로 발견될 가능성이 낮다.
- **왜 지금 안 고치나:** 자동 대조를 붙이려면 CI가 원격에 붙어야 하는데 이 레포는 `service_role` 키를 두지 않는다(`conventions.md` §5) — 권한 축을 새로 열어야 하는 결정이라 별개 판단이다. 당장의 값싼 대안은 **적용을 손으로 옮기지 않는 것**(파일 내용을 그대로 전달)과 **적용 직후 로직 해시 대조**이며, 이번에 실제로 쓴 절차가 그것이다.
- **트리거:** **다음번 원격 마이그레이션 적용 직전** — 그 자리에서 (a) 파일 원문을 그대로 적용하고 (b) 적용 후 이번과 같은 로직 해시 대조를 돌린다. 절차를 `deployment-runbook.md`에 못박을지는 그때 판단한다(지금 적으면 문서만 늘고 실행되지 않는다 — B9).

### DW-535: `RowSkeleton`(행 조합) 부재 — 8.2 AC3가 요구한 두 형태 중 카드형만 있다

origin: 장부 통합 이관(구 docs/tech-debt.md 📅 스토리로 예약됨 절) — 원출처: Story 8.2 AC3, 사용자 이월 결정
location: web/src/components/ui/Skeleton.tsx
severity: low
reason: 소비처가 생길 때 그 화면 기준으로 만들기로 사용자가 이월했다 — 지금 임의로 만들면 재작업 위험.
trigger: Epic 15(관리자 테이블) 착수 시. ⚠️ 원 트리거는 "Epic 12(채팅 목록)·Epic 15"였는데 **Epic 12가 이걸 추가하지 않고 done으로 닫혔다**(2026-07-29 통합 시 실측) — 남은 트리거는 Epic 15 하나뿐이다.
status: open

- **위치:** `web/src/components/ui/Skeleton.tsx`
- **내용:** 8.2 AC3 원문은 "스켈레톤 로딩(카드/행 조합)"을 요구하나 `CardSkeleton`(카드형)만 있다.
- **이월 사유(사용자):** 소비처 생길 때 화면 기준으로 — 지금 임의로 만들면 재작업 위험.
- **트리거:** Epic 15(관리자 테이블)에서 그 화면 기준으로 추가.

### DW-536: `db-schema-guide.md` 스키마 표가 실제 마이그레이션보다 늙었다

origin: 장부 통합 이관(구 docs/tech-debt.md 📅 스토리로 예약됨 절) — 원출처: architecture-increment-2026-07-12.md:327이 갱신 대상으로 지목
location: docs/db-schema-guide.md
severity: low
reason: Epic 9~16이 마이그를 8장 더 얹으므로 지금 고쳐도 금방 다시 늙는다 — 증분이 끝난 뒤 한 번에 한다.
trigger: 증분 종료 후(Epic 16 뒤).
status: open

- **위치:** `docs/db-schema-guide.md`
- **내용:** 현재 *"마이그레이션 `0001~0009`"* 로 적혀 있으나 실측 12개이고, §4 표가 `0010`(채팅 길이 CHECK)·`0011`(anon SELECT)·`0003c`(chat_rooms 무결성 트리거)를 모른다. **부채가 아니라 계획된 작업이다.**
- **주의:** 이 문서는 시연·발표용 스키마 설명서이고 **스키마 정본은 `supabase/migrations/`** 다.
- **트리거:** 증분 종료 후 한 번에.

### DW-537: 찜 기반 "인기 매물" 신호 — 보류(제품 결정, 설계는 박제됨)

origin: 장부 통합 이관(구 docs/tech-debt.md ⚪ 의도적 보류 절) — 원출처: 2026-07-13 party-mode(John·Amelia·Mary·Sally), 사용자 결정
location: n/a (랜딩 "인기 매물" 정렬 로직)
severity: low
reason: `favorite_count` 컬럼을 지금 만드는 건 YAGNI이고, 시드에 찜 데이터가 없어 전부 0이 되는 콜드스타트 함정이 있다. 되살릴 필요는 없으나 재검토 시 아래 설계를 그대로 쓴다.
trigger: 찜 데이터가 실제로 쌓이고 랜딩 정렬을 다시 손대는 스토리가 생길 때.
status: open

- **무엇:** 랜딩 "인기 매물"을 조회수 단독이 아니라 **찜 수 반영 복합 신호**(`score = view_count + w·wishlist_count`)로.
- **왜 보류:** `favorite_count` 컬럼을 지금 만드는 건 YAGNI + 시드에 찜 데이터가 없어 전부 0(콜드스타트 함정).
- **이미 된 대비:** `wishlists(user_id, listing_id)`가 증분(FR55·마이그 0015)에 생기므로 찜 수는 `COUNT(*) GROUP BY listing_id`로 **언제든 파생 가능** — 스키마 재작업 불필요.
- **이어받을 때:** (a) 인덱스 `wishlists(listing_id)` 1줄 additive (b) 집계 쿼리 권장(트리거 카운터는 정합성 부채 — 원천이 있으니 COUNT) (c) **임계값 게이팅**(5명↑만 노출, "0명 찜" 낙인 방지) + 카드 하단 중립 회색 메타(초록/앰버 안 씀) (d) 봇 방어(view dedup) 없으면 조회수 오염 → 찜 가중치 크게.

### DW-538: 문서 기반 차량 상태 관리(성능점검표·보험이력) — 보류(제품 결정, 설계는 박제됨)

origin: 장부 통합 이관(구 docs/tech-debt.md ⚪ 의도적 보류 절) — 원출처: 2026-07-13 party-mode(John·Amelia·Mary·Sally), 사용자 결정
location: n/a (신규 `listing_documents` 테이블 + 등록 폼)
severity: low
reason: 증분 범위 밖으로 사용자가 보류했다. 되살릴 필요는 없으나, 이어받을 때 재설계하지 않도록 확정된 설계를 그대로 보존한다.
trigger: 성능점검표·보험이력을 실제로 다루기로 정하는 순간. ⚠️ 착수 전 **개인 직거래(C2C)의 성능점검기록부 법적 의무 범위**를 먼저 확인할 것(미검증).
status: open

- **무엇:** 성능점검표·보험처리이력을 **자체 간소 양식(MD/PDF) 문서 기반**으로 관리 + 등록 시 상태 컬럼 자동 반영 + 다운로드.
- **확정된 설계(보류하되 박제):** **OCR·임베딩 없음**(자체 구조화 양식이라 파싱 불필요) · **신뢰 모델은 자기신고+면책 유지**(등급 격상 안 함 — 업계도 성능표·보험이력 오류로 플랫폼 무보증이 표준, 문서는 **"참고자료"로만**).
- **스키마(그때):** `listing_documents(listing_id fk ON DELETE CASCADE, doc_type enum('inspection','insurance'), storage_path, created_at)` + `usage_type`(자가용/영업용/렌트/리스).
- **이미 된 대비:** 증분 아키텍처 ADR-IMG-01이 서명URL 헬퍼·업로드 RLS·버킷 경로를 **"이미지 전용"이 아니라 아티팩트 범용**으로 짓도록 지침화 → 배관 재작업 불필요.
- **⚠️ 이어받기 전 확인 권장(미검증):** 개인 직거래(C2C)의 성능점검기록부 **법적 의무 범위** · 각 사 인기 랭킹 공식.
