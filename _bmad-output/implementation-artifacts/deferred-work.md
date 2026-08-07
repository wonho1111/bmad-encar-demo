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
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-2: Follow-up review still recommended for 11-1-view-count-스키마-increment-rpc-하드닝 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-1-view-count-스키마-increment-rpc-하드닝.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260727-223439-2318; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-3: Follow-up review still recommended for 11-2-상단-내비-재구성 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-2-상단-내비-재구성.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260727-223439-2318; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-4: Follow-up review still recommended for 11-5-반응형-뷰포트-e2e-감사-sm-b after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-11-5-반응형-뷰포트-e2e-감사-sm-b.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260728-105733-33e0; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-5: Follow-up review still recommended for 12-1-멱등키-마이그레이션 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-1-멱등키-마이그레이션.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260728-203648-2fc6; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-6: Follow-up review still recommended for 12-3-실시간-송수신-전환-폴링-제거 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-3-실시간-송수신-전환-폴링-제거.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-7: Follow-up review still recommended for 12-4-재연결-배너-갭-보정 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-4-재연결-배너-갭-보정.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-8: Follow-up review still recommended for 12-5-안읽음-배지-방-목록-정렬 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-5-안읽음-배지-방-목록-정렬.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

### DW-9: Follow-up review still recommended for 12-6-실시간-채팅-검증-sm-e after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-12-6-실시간-채팅-검증-sm-e.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260729-003659-be13; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-07-30
resolution: resolved by sweep bundle dw-epic-11-12-review-budget-followup (run 20260730-113650-eb0d). 근거 = `spec-epic-11-12-review-budget-followup.md` — 9개 커밋(b76ec57·d6548a9·48427e3·51c6154·fbdd5a0·b581b45·4ec2075·dd000bb·dfc3aaa)의 실제 diff를 리뷰 레이어 4종(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)이 새 세션에서 병렬 검토. 원 발견 21건 → 신규 5건 승격(DW-549~553), 16건 기각.

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
status: done 2026-07-30
resolution: already resolved: supabase/migrations/0022_chat_idempotency_key.sql + web/src/lib/messages.ts:127 (insert carries client_message_id) — UNIQUE(room_id, client_message_id) now blocks the duplicate re-send

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
status: done 2026-07-30
resolution: already resolved: web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx:493 CHANNEL_ERROR/TIMED_OUT -> visible banner, :789 realtimeError render; polling removed entirely by Story 12.3 (commit b581b45)

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
status: done 2026-07-30
resolution: already resolved: web/src/lib/options.ts (parseOptionsInput/serializeOptions, newline-delimited) + web/src/lib/__tests__/options.test.ts round-trip; SellForm.tsx no longer comma-joins. App-side listing_form.dart is a separate entry (DW-413)

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
✎ 2026-08-02 사실 정정(사용자 지적으로 재확인) — **이 항목 본문의 "`/ai`는 공개 페이지"라는 전제는 지금 사실이 아니다.** `web/src/proxy.ts:30`의 `PROTECTED_PREFIXES`에 `/ai`가 들어 있어 비로그인은 페이지에 **도달조차 못 하고** `/login`으로 리다이렉트된다(같은 파일 20~21행이 이유를 적어둔다: "검색 1회 = Gemini 호출 3회 내외 = 실제 과금이고, 로그인이 호출자를 식별하는 유일한 수단"). API도 `api/app/routers/ai.py:42`의 `Depends(get_current_user)`로 JWT 필수다. 따라서 본문이 묘사한 "같은 사람이 시크릿창에선 멀쩡히 쓴다"는 역설은 **더 이상 재현되지 않는다** — 이 항목이 등재된 8.5 시점에는 공개였고 이후 과금 울타리로 보호된 것으로 보인다.
✎ 2026-08-02 사용자 결정 — 선택지 [1](세션 만료 안내 + 로그인 링크)로 확정. **다만 착수 시 재현부터 한다**: 위 정정대로 `proxy.ts`가 이미 1차로 막으므로, "폐기된 토큰을 들고 `/ai`에 도달하는" 경로가 아직 남아 있는지(= proxy의 사용자 판정이 서버에 묻는지 캐시를 믿는지)를 먼저 실측하고, 재현이 안 되면 안내 문구를 새로 만들 게 아니라 이 항목을 닫는다. 재현되지도 않는 증상에 UI를 붙이지 않는다.
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
status: resolved (2026-08-07, Story 15.4) — `admin_restore_sold_listing` RPC(`supabase/migrations/0030_listings_restore_sold_rpc.sql`) + 관리자 화면 "판매완료 되돌리기" 버튼으로 위 해소 선택지 ②(복구 전용 좁은 RPC)를 구현. 런북 §10을 이 절차로 대체하고 옛 SQL은 §10-a 비상용 백업으로 격하. 스펙: `_bmad-output/implementation-artifacts/spec-15-4-관리자-판매완료-되돌리기.md`.

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
location: `api/app/db/sql_guard.py:196-224`(LIMIT 검사·주입 블록 — 벡터절 화이트리스트 스텝이
  앞에 끼어들며 129행대에서 이 자리로 이동)
severity: low
reason: temp=0라 발생 가능성 낮고 대부분 fail-safe이다.
status: done 2026-07-30

- **위치:** `api/app/db/sql_guard.py:196-224`
- **내용:** `\blimit\s+(\d+)`가 `LIMIT 0`(오해성 0건)·`LIMIT -5`·`LIMIT (10)`·`OFFSET`-only를 정상 인식 못 함. temp=0라 발생 가능성 낮고 대부분 fail-safe.
- **해소:** LIMIT 정규화/하한 검증 강화.
- 📅 **예약됨: `13-1-sql-guard-하이브리드-정비-g2-baseline`** (backlog).
- **2026-07-30 갱신(`13-1-sql-guard-하이브리드-정비-g2-baseline` 구현) — 4증상 전부 확인 완료:**
  - `LIMIT 0`·`LIMIT -5`(부호 포함 음수·0): 이미 이전 코드리뷰가 `\blimit\s+([-+]?\d+)`로 정규식에
    부호를 넣어 해소해 뒀었다(`limit_invalid`, 이 DW가 그 갱신을 놓치고 있었다 — 지금 확인·기록).
  - `LIMIT (10)`(숫자가 바로 안 붙는 형태): 이번에 `limit_malformed` 신설로 해소 — 조용히
    `LIMIT (10) LIMIT 5`라는 이중 LIMIT을 만들지 않고 명시 거부한다(`api/tests/test_sql_guard.py`의
    `test_parenthesized_limit_rejected_as_malformed`가 고정, red→green으로 실측 확인).
  - `OFFSET`-only(LIMIT 없이 OFFSET만 있는 SQL — 예: `WHERE status='on_sale' OFFSET 10`):
    **처음부터 문제가 없었다.** `\blimit\b` 자체가 없으면 else 분기(`LIMIT {DEFAULT_LIMIT}` 부착)로
    빠지므로 OFFSET 유무와 무관하게 항상 안전하게 처리된다 — 직접 재실행해 확인:
    `validate_select_sql("SELECT id FROM listings WHERE status='on_sale' OFFSET 10")`
    → `"...OFFSET 10 LIMIT 5"` 정상 반환(코드리뷰 패스가 재보기 없이 "미해소"로 단정했던 이전
    기록을 실측으로 정정 — CLAUDE.md B4 "재보기 전엔 선언하지 않는다").
  - 4증상 전부 확인됨(2개는 이전에, 1개는 이번에 해소, 1개는 애초에 무해)에 따라 이 DW를 닫는다.
resolution: `13-1-sql-guard-하이브리드-정비-g2-baseline` 구현 + 코드리뷰 패치 라운드에서 4증상
  전부 재확인 완료(위 상세). `LIMIT (10)` 케이스는 `limit_malformed` 신설로 실제 코드 변경, 나머지
  3개는 재확인만(기존 동작이 이미 안전).

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
status: done 2026-07-30
resolution: already resolved: commit 5bc6463 (Story 8.5) removed test_search_without_token_allowed_anon; grep -rn across api/tests/ now returns 0 hits — /ai/search reverted to always-401 without token, so the duplicated weak assertion no longer exists

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
status: done 2026-07-30
resolution: already resolved: api/tests/test_sql_guard.py:211 test_join_listing_images_rejected, :221 test_select_from_listing_images_rejected, :247 assert ALLOWED_TABLES == {'listings'} — the executable check the entry asked for now exists

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
status: done 2026-07-30
resolution: already resolved: api/app/schemas/ai.py:80 image_path field + api/app/graph/listing_cards.py:187 card.image_path = path; web/src/lib/api/aiSearch.ts resolveCardImage() converts it for ListingCard (Story 9.6)

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
status: done 2026-07-30
resolution: already resolved: supabase/migrations/0013_listing_images_path_integrity.sql:43-46 — trigger listing_images_enforce_storage_path rejects any path whose segment count != 3, whose [1] != seller uuid, [2] != listing_id, or [3] empty; fires BEFORE INSERT OR UPDATE OF listing_id, storage_path (0013 predates this entry, which miscited only 0012)

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
status: done 2026-07-30
resolution: already resolved: supabase/migrations/0020_listings_view_count.sql — listings_set_timestamps() begins 'new.created_at := old.created_at;' unconditionally; confirmed live on remote project via pg_trigger/pg_proc query

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

✎ 2026-08-02 사용자 결정 — 선택지 [2](web 등록·수정 폼에 입력 UI 추가)로 확정한다. 근거는 계획 문서다: `research-data-trust-attributes.md`가 "모든 신뢰속성을 **자기신고**로 통일 처리하는 것이 가장 정직한 모델"이라 정했고, 서류 첨부(DW-538)는 같은 날 **보류**로 확정돼 "서류에서 추출" 경로가 닫혔다 — 남는 공급 경로는 판매자 입력뿐이다.
✎ 2026-08-02 사용자 지시로 **두 컬럼 통합 설계를 확정**한다("둘을 합치거나 예전 것을 없애라"). **컬럼 드롭은 하지 않는다** — `accident_free` 참조가 코드 30개 파일에 퍼져 있고(web 상세·카드·등록폼, Flutter 앱 모델·폼, api의 `sql_guard` 허용컬럼 화이트리스트·Text-to-SQL 프롬프트·채점 하네스, 마이그레이션 0011/0020의 SELECT 목록, 시드 3종, 테스트 다수), 드롭은 이 전부를 동시에 고쳐야 하는 데다 CLAUDE.md B3("DB는 더하기만 — 기존 걸 지우거나 바꾸지 않는다")과 `0017` 주석의 명시적 약속에 정면으로 반한다. 대신 **사용자에게 보이는 층과 쓰기 층에서 실제로 하나가 되게** 합친다:
  1. **입력 하나로** — 등록·수정 폼에서 '무사고' 체크박스를 없애고 `accident_status` 선택(무사고/단순교환/사고) **하나만** 둔다. 판매자가 사고 정보를 두 번 입력하는 자리를 없앤다.
  2. **`accident_free`는 파생값으로 강등** — 사람이 입력하지 않고 `accident_status`에서 계산한다(`무사고`→true, `단순교환`·`사고`→false). 기존 소비처 30곳은 계속 이 컬럼을 읽으므로 안 깨진다.
  3. **강제는 DB에서** — 앱 코드가 아니라 **트리거**로 `accident_status`가 채워질 때 `accident_free`를 자동 동기화한다(B9: 앱 코드로 막으면 화면 하나 더 만들 때 까먹지만 데이터 계층에 박으면 못 어긴다). 기존 100건(`accident_status` NULL)은 건드리지 않는다(B3 additive — backfill 없음).
  4. **표시도 한 곳으로** — 상세에서 사고 정보는 **신뢰 뱃지 한 자리에만** 렌더하고 차량정보의 '사고이력' 행은 제거한다. `accident_status`가 없는 레거시 매물은 그 뱃지 값을 `accident_free`에서 파생해 보여준다(정보가 사라지지 않게).
  → 이 설계가 서면 DW-412의 자기모순(초록 '무사고' 뱃지 아래 '사고이력 있음' 행)은 **표시 자리가 하나뿐이라 구조적으로 불가능**해지고, 값 어긋남은 트리거가 막는다. DW-412는 이 스토리에서 함께 닫는다.
⚠️ **이 폼을 만드는 순간 DW-412가 살아난다.** 지금 상세 화면은 `accident_status`(신뢰 뱃지)와 `accident_free`(차량정보 '사고이력' 행)를 **교차검증 없이 나란히** 렌더하는데, 값이 어긋날 수 있는 쓰기 경로가 없어서 오늘은 사고가 안 난다(DW-412가 "현재는 발생하지 않는다"고 실측 기록). 입력 폼이 들어오면 판매자가 `accident_free=무사고`인데 `accident_status='사고'`를 고를 수 있게 되고, **초록 '무사고' 뱃지 바로 아래 '사고이력 있음' 행**이 뜨는 자기모순 화면이 실제로 가능해진다(CM-C 위반). `0017`의 CHECK는 이 모순을 안 잡는다(마이그레이션 주석이 그렇게 적어둠). 따라서 이 항목의 스토리는 **DW-412를 같은 범위에서 함께 해소**해야 한다 — 두 컬럼을 어떻게 할지(한쪽을 폼에서 빼기 / 파생값으로 잠그기 / 화면에서 한 곳만 노출)를 정하고 DB나 코드 한 곳에서 못 어기게 만든다.
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
status: done 2026-07-30
resolution: already resolved: web/src/components/layout/AppHeader.tsx:13 imports Logo and :80 renders <Logo size="sm" /> inside the consumer home link (commit 48427e3, Story 11.2) — the component is no longer orphaned

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

✎ 2026-08-02 사용자 결정 — 선택지 [1](프로필 자기수정 신설)로 확정. "UX 문서에 명세가 있으면 문서대로 만드는 것이 맞다"는 판단이며, **만들기 전에 목업부터** 만든다.
✎ 2026-08-02 경위 정정(사용자 지적) — 이 항목을 "UX대로 하려다 DB 권한 문제로 읽기전용으로 후퇴했다"로 읽으면 틀리다. 실제 순서는 ① **편집 기능을 만드는 스토리가 애초에 백로그에 없었다**(EXPERIENCE.md의 명세가 에픽·스토리로 변환되지 않은 누락) → ② Story 11.2가 프로필▾ 드롭다운에 '내 정보' 링크를 넣으면서 목적지가 없으면 404가 되므로 **자기 범위 안에서 읽기 전용 페이지만** 급히 만들었고, 그 스토리가 스스로 "신규 DB 마이그레이션 없음"을 Never로 걸어둬 편집을 넣을 수 없었다. 즉 DB 권한은 **막힌 원인이 아니라 11.2가 스스로 그은 경계**이고, 진짜 원인은 스토리 누락이다.
✎ 2026-08-02 범위 정정(사용자 지적) — UX 결정로그의 "B안 마이페이지 탈락"은 **개인 메뉴의 진입 위치**(상단 드롭다운 vs 마이페이지 허브)에 대한 결정이지 "'내 정보' 화면을 만들지 않는다"는 결정이 아니다. 드롭다운이든 허브든 '내 정보' 화면 자체는 별개로 존재해야 한다 — 앞선 보고가 이 둘을 뭉뚱그려 전달했다. (결정로그가 "B안 /me 화면은 Flutter 하단 탭에서 재활용 가능"이라 적은 것도 같은 이유다: 웹은 PRD의 "마이페이지 지양"을 따르고, 앱은 하단 탭 구조라 /me 탭이 자연스럽다는 뜻이지 웹에 화면이 없어도 된다는 뜻이 아니다.)
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
status: done 2026-07-30
resolution: already resolved: web/src/app/page.tsx:119 <AppHeader roleLabel={null} email={null} currentPath="/" /> in the logged-out branch, matching :78 in the logged-in branch (Story 11.3)

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
status: done 2026-07-30
resolution: already resolved: web/src/components/layout/AppHeader.tsx:13,79-81 has the `<Link href="/"><Logo size="sm" /></Link>` wiring, and commit c6086c9 already closed the paired DW-425 with that same evidence; the outstanding "800 weight 실경로 확인" is now an executing browser assertion at web/e2e/landing-and-view-count.spec.ts:51-57 (getComputedStyle(...).fontWeight === '800' on the rendered header Logo). Both halves of this entry are satisfied.

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
status: done 2026-07-30
resolution: already resolved: web/e2e/nav-and-hero.spec.ts:168 B9 (anon submit gated, requestCount 0), :185 B10 (login return restores query, no auto-run), :207 B11 (auto-run exactly once, still 1 after reload) — all four behaviours now asserted (commit eaa4833)

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
status: done 2026-07-30
resolution: already resolved: web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx:867 size={1} on the message input with min-w-0 flex-1 (commit b581b45) — the 390px horizontal overflow fix the entry asked for

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
status: done 2026-07-30
resolution: already resolved: .bmad-loop/policy.toml:140 `trigger = "recommended"` with dated comments recording the 2026-07-28 flip to `always` for the Epic 12 run and the 2026-07-29 revert; sprint-status.yaml epic-11 action A5 = done ('policy.toml trigger=always로 Epic 12 전체를 돌렸고 12-2의 교차-방 유출을 그 덕에 잡았다') and epic-12 action B1 = done. The entry's own closing condition (verify the Epic 12 run used `always`, then close) is met, and bmad_loop/policy.py:16 REVIEW_TRIGGER_MODES={'always','recommended'} settles the previously-unverified diff-conditional question.

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
status: done 2026-07-30
resolution: already resolved: web/src/lib/messages.ts:127 .insert({... client_message_id}) and :135-145 catches 23505 then re-queries the existing row to resolve the optimistic bubble; ChatRoomMessages.tsx:642,657 generate/reuse the key

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
status: done 2026-07-30
resolution: already resolved: Queried the already-running local stack (docker ps: supabase_db_bmad-encar-demo healthy, port 55322): `select version from supabase_migrations.schema_migrations` returns 24 rows, 0001 through 0024 — 0020/0021/0022 are all recorded. The entry's stated closing test ('이력 행이 22개다') passes.

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
status: done 2026-07-30
resolution: already resolved: api/tests/integration/conftest.py now exists (defines _DSN, pytestmark skip guard, _LISTING_COLS, _create_user, _insert_listing) — created by Story 12.2 when it added test_chat_realtime_broadcast_real_db.py, which is exactly this entry's trigger ('6번째 복제를 만들기 전에 conftest.py로 올린다'). The title claim 'conftest.py가 없어' is now false; the remaining partial de-duplication is tracked by its own successor entry DW-494.

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
status: done 2026-07-30
resolution: already resolved: git rev-parse: develop == test/bmad-loop == f9d9637 (already merged); gh run list --branch develop: Tests conclusion=success on headSha f9d9637 (2026-07-29T15:33:15Z) — the entry's verification step is done and green

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
status: done 2026-07-30
resolution: already resolved: scripts/check_env_integrity.sh exists and is wired as the first verify command at .bmad-loop/policy.toml:82 (commit a50465d) — the structural fix the entry proposed

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
status: done 2026-07-30
resolution: already resolved: Both artifacts this decision-record describes exist: supabase/migrations/0023_chat_realtime_broadcast.sql (the realtime.messages participant-scoped SELECT policy) and api/tests/integration/test_chat_realtime_broadcast_real_db.py (the dedicated real-DB test chosen over expanding check_migrations.py probes). The entry's own body states it moved #185 from '아직 안 옴' to '왔고, 처리 방식을 골랐다' — the decision it records is complete; the underlying probe-coverage gap remains open separately as DW-485.

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
- ✎ **파일 이동 (2026-07-29, `DW-525` 해소):** 이 컴포넌트는 `web/src/components/layout/BackNavRefresh.tsx`로 이름·자리가 바뀌었고 계약 검사도 `components/layout/__tests__/backNavRefreshContract.test.ts`로 옮겨졌다(더는 채팅 전용이 아니다). **이 항목의 내용은 그대로 유효하다** — 여전히 소스 스캔일 뿐 실제 `popstate`를 디스패치해 확인하는 런타임 테스트는 없다.

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
- ✎ **전제가 바뀌었다 (2026-07-29, `DW-525` 해소):** 본문의 *"지금은 내부 `location.pathname === '/chat'` 가드로 안전하지만"* 은 더 이상 사실이 아니다 — **그 가드를 걷어냈다.** 이제 모든 페이지의 뒤로가기에서 실행되는 것은 결함이 아니라 **의도된 동작**이다(찜 하트·안읽음 배지가 모든 소비자 화면에 있으므로 경로 목록은 유지될 수 없다). 즉 이 항목의 "무관한 페이지에서도 돈다"는 축은 소멸했고, 남는 것은 *"단일 페이지 사정을 루트 레이아웃에 박는 패턴이 반복되면 `layout.tsx`가 주인 없는 부수효과 모음집이 된다"*는 **구조 우려 축뿐**이다. 그 축은 그대로 열어 둔다(단, 이 리스너는 이제 "단일 페이지 사정"이 아니라 앱 전역 관심사라 `(user)` 전용 layout으로 옮길 대상이 아님 — 옮기면 `(admin)`이 못 받는다).

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
status: done 2026-07-29
resolution: 이 항목이 예고한 재발이 **실제로 일어나 사용자가 잡았다** — 배지가 아니라 **찜 하트**로. `/search`에서 찜 → 다른 화면 → 뒤로가기하면 하트가 들어왔던 시점 상태로 되돌아갔고(로컬 Playwright 재현: DB엔 찜 2행이 있는데 카드는 "찜하기"), 사용자가 그 화면을 믿고 다시 누르면 방금 저장한 찜을 스스로 취소해 **데이터까지 틀어졌다**(운영 `wishlists` 통계 insert 2 / delete 2, 현재 0행). 그래서 이 항목이 남겨둔 설계 판단을 사용자 지시로 결정하고 실행했다: **경로 가드를 걷어낸다.** `ChatListBfcacheRefresh.tsx` → `web/src/components/layout/BackNavRefresh.tsx`로 이름·자리를 옮기고(더는 채팅 전용이 아니므로), `popstate`에서 조건 없이 `router.refresh()`를 호출하며, 이 항목이 지적한 나머지 절반인 **cross-document bfcache 복원**(`pageshow` + `persisted`)도 함께 듣는다. 계약 검사도 뒤집어 고정했다(`backNavRefreshContract.test.ts` — "가드가 없다"가 이제 검사 대상. 가드를 되살리는 뮤테이션으로 red 실측 후 green 복귀 확인). 대가(뒤로가기 1회당 서버 렌더 1회)는 컴포넌트 주석에 명시했고 왕복 비용 축은 `DW-540`~`DW-543` 성능 묶음이 이어받는다. 실측: `/search` 찜 → `/wishlist` → 뒤로가기 → 하트가 실제 DB 상태로 표시됨(로컬 스택, 2026-07-29).

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
- ✎ **①은 소멸, ②는 유효 (2026-07-29, `DW-525` 해소):** 경로 가드를 걷어내면서 ①의 위험 구조가 사라졌다 — 이제 `router.refresh()`가 **Router Cache 전체를 무효화하는 것이 바로 원하는 동작**이고(모든 화면의 찜 하트·배지를 되살려야 한다), 코드가 `/chat`을 겨냥한 것처럼 읽혀 디버깅을 오도하던 문제도 가드와 함께 없어졌다. 다만 Next가 훗날 `refresh()`를 현재 세그먼트로 좁히면 **그때는 모든 화면에서 조용히 재발**하므로, 재실측 트리거 자체는 그대로 살려 둔다. ②(useRouter 반환값 참조 안정성, 의존성 `[router]`)는 코드가 그대로라 **변함없이 유효**하다.

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

### DW-539: 구매자 계정에 "내 매물 관리" 메뉴를 보여주고 나서 홈으로 튕긴다 (역할 통합 Epic 14 대기)

origin: 2026-07-29 사용자 앱 테스트 지적 #1 (Discord)
location: `web/src/components/layout/SiteNav.tsx`(프로필▾ 드롭다운이 역할과 무관하게 "내 매물 관리"를 렌더) ↔ `web/src/app/(user)/sell/layout.tsx`의 `requireRole(USER_ROLE.SELLER)` → 역할 불일치 시 `redirect('/')`.
severity: medium
reason: 근본 해소는 **역할 통합 본체(Epic 14)**다 — PRD F14/FR52~54가 "가입 시 구매자/판매자 선택 제거, 로그인한 사람은 누구나 사고판다"를 이미 확정했고(업계 6/6 표준, `research-account-nav-model.md`), `Story 14.3 소유권 기반 판매 게이트`가 정확히 이 `requireRole(SELLER)` → `requireUser()` 교체다. 사용자 결정(2026-07-29): **"Epic 14를 기다린다"** — 지금 게이트만 먼저 풀면 인증·RLS 축을 UI 커밋과 섞게 되는데, 에픽이 그걸 "별도 워크스트림으로 분리 관리"하라고 명시적으로 못박았다.
trigger: Epic 14 착수 시 — `Story 14.3`의 인수조건에 **"구매자 계정으로 프로필▾ → 내 매물 관리 클릭 시 `/sell`이 실제로 열린다"**를 브라우저 실측 항목으로 넣는다(게이트만 바꾸고 화면을 안 눌러보면 이 증상이 그대로 남는다).
status: open

- **증상(사용자 실측):** 구매자 계정으로 프로필▾ → "내 매물 관리"를 누르면 **아무 반응이 없는 것처럼 보이다가 랜딩으로 돌아온다.** 판매자 계정은 정상 진입.
- **왜 "반응 없음"으로 보이나:** 실제로는 `/sell`로 이동했다가 서버 레이아웃의 역할 가드가 홈으로 리다이렉트한 것이다. 사용자에게는 아무 안내가 없어 "클릭이 먹지 않았다"로 읽힌다.
- **지금 무해하지 않은 이유:** 이건 접근 차단이 정상 동작하는 사례이면서 동시에 **막다른 길**이다(UX-DR20이 금지한 부류). Epic 14까지 남겨두기로 한 만큼, 그때까지는 "왜 못 들어가는지"를 알 방법이 없다.
- **범위 밖(지금 하지 않는 것):** 구매자에게 메뉴를 숨기는 임시 조치. 곧 역할 자체가 사라지므로 지웠다가 되살리는 왕복이 되고, `SiteNav`는 애초에 `getConsumerNavLinks(null)`로 **role-aware 훅 자리를 비워 둔 채** 설계됐다(Epic 14가 그 자리를 채우도록 에픽이 지시).

### DW-540: 페이지를 만드는 Vercel 함수는 미국(iad1)에서 도는데 DB는 서울(ap-northeast-2)이다 — 왕복마다 태평양을 건넌다

origin: 2026-07-29 사용자 "전체적으로 느리다" 지적 #7 → 원인 분석(실측)
location: Vercel 프로젝트 함수 리전 설정(`web/vercel.json` 부재 — 기본값 `iad1`) ↔ Supabase 프로젝트 `psrnsasxpkpwqdukjdmt` 리전 `ap-northeast-2`.
severity: high
reason: 사용자 결정(2026-07-29): **성능 묶음은 다른 수정이 끝난 뒤 마지막에 한다.** 리전 변경은 코드가 아니라 배포 설정 변경이라 되돌리기 쉬운 대신 운영 배포를 건드리므로(B3 운영 반영 = 사용자 승인 사항) 버그 수정 커밋과 섞지 않는다.
trigger: 성능 묶음 착수 시 **가장 먼저** — 이 한 건이 나머지 셋을 합친 것보다 체감이 클 가능성이 높다. 바꾼 뒤 같은 방법으로 재측정해 숫자로 확인한다(아래 측정 방법 그대로).
status: done 2026-07-29
resolution: `web/vercel.json`에 `"regions": ["icn1"]` 추가(커밋 7934be7) — 함수 실행 리전을 서울로 고정. 프로젝트 설정 대신 파일로 둔 이유: 대시보드 설정은 이력·리뷰가 안 남고, 파일이면 develop 프리뷰에서 먼저 검증한 뒤 main 병합으로 운영에 반영된다(B3). ⚠️ **운영 반영은 main 병합 시점이며 사용자 승인 사항** — 이 커밋은 develop 프리뷰까지만 바꾼다. 프리뷰 배포 후 `x-vercel-id`의 두 번째 구간이 `iad1`→`icn1`으로 바뀌는지 확인할 것(그게 이 항목의 종결 증거다).
- **실측(2026-07-29):** 응답 헤더 `x-vercel-id: icn1::iad1::…` — 요청은 서울 엣지(icn1)로 들어오지만 **함수 실행은 iad1(미국 동부)**. Supabase MCP `get_project` 결과 DB 리전은 `ap-northeast-2`(서울).
- **왜 곱하기로 아픈가:** 모든 소비자 페이지가 `force-dynamic`이고 DB 왕복이 **순차로** 여러 번 일어난다. 로그인 홈 기준 `auth.getUser()` → `profiles` → 인기/최신(각각 매물→사진 2단) → 찜 오버레이 = 5~7 왕복이며, 왕복 하나하나가 미국↔서울이다. 왕복 수를 줄이는 것과 **왕복 하나의 길이를 줄이는 것**은 다른 축인데, 지금은 후자가 방치돼 있다.
- **참고 측정치:** 비로그인 `/` TTFB(워밍 후) 0.35s / `/search` TTFB 0.86~0.99s(HTML 압축 전 320KB). 로그인 상태는 왕복이 더 많아 이보다 나쁘다.
- **해소:** Vercel 프로젝트 함수 리전을 `icn1`으로. Hobby 플랜은 리전 1개만 허용되므로 프로젝트 설정 또는 `vercel.json`의 `regions`로 지정한다.

### DW-541: 매물 사진을 1600px 원본 그대로 내려받고(카드 표시 폭 364px) CDN 캐시도 꺼져 있다

origin: 2026-07-29 사용자 "전체적으로 느리다" 지적 #7 → 원인 분석(실측)
location: `web/src/components/listings/ListingCardImage.tsx`(의도적으로 `next/image` 대신 평범한 `<img>`) · Supabase Storage `listing-images` 오브젝트 메타데이터의 `cacheControl`.
severity: high
reason: 사용자 결정(2026-07-29): 성능 묶음은 마지막. 또 두 갈래(리사이즈·캐시 헤더)의 해소 수단이 서로 달라 — 전자는 코드/설정, 후자는 **이미 올라간 180개 오브젝트의 메타데이터 수정** — 한 커밋에 섞으면 되돌리기가 어려워진다.
trigger: 성능 묶음 착수 시 `DW-540` 다음. 캐시 헤더는 신규 업로드 경로(`PhotoUploader`)에 `cacheControl`을 지정하는 것만으로는 **기존 180개가 안 고쳐진다** — 재업로드 또는 메타데이터 갱신을 반드시 함께 계획할 것.
status: done 2026-07-29
resolution: 원본을 안 건드리고 `next/image`로 전환(커밋 b39a2b2) — 크기·캐시 두 축이 함께 풀린다. **캐시 헤더를 원본에서 고치는 길은 측정으로 막혔다**: 운영 `storage.objects`의 `metadata->>'cacheControl'`을 1건 바꿔 봤지만 응답 헤더는 `no-cache` 그대로였다(그 컬럼은 거울일 뿐, serve 시점 헤더는 스토리지 백엔드가 들고 있다). 고치려면 180장 재업로드가 필요해 별건으로 남긴다 — **시험한 1건은 원래 값으로 되돌렸다.** 프로덕션 빌드 실측: `Cache-Control: public, max-age=31536000, must-revalidate` · `image/webp` · **8,128 B(원본 194,160 B 대비 −95.8%)** · 렌더 264px(원본 1600px). 로컬 함정도 함께 잡았다 — Next 16이 사설 IP 원본 최적화를 기본 차단해(SSRF 방어) 로컬에서만 사진이 전부 400이 났고, 로컬 스택을 볼 때만 `dangerouslyAllowLocalIP`를 켜도록 환경 기반으로 갈랐다(운영은 공개 호스트라 방어 유지). 이 파일에 있던 "next/image를 안 쓰는 이유" 3개 중 2개가 거짓임을 근거와 함께 주석에 정정했다.
- **실측 ① 크기(2026-07-29, 운영 `/search` 표본 6장):** 저장본 `1600×1067`급인데 카드 표시 크기는 `364×218`. 픽셀 수로 약 20배. 파일 크기 50~190KB(코드 주석의 90장 전수 실측: 중앙값 197KB · 평균 229KB · 최대 615KB).
- **실측 ② 장수:** `/search` 한 페이지에 `<img>` **90장**(→ `DW-542`와 곱해진다).
- **실측 ③ 캐시:** `storage.objects` 메타데이터 조회 결과 `listing-images` **181개 중 180개가 `cacheControl: no-cache`**(나머지 1개만 `max-age=3600`). 실제 응답도 `cache-control: no-cache` + `cf-cache-status: MISS` — 브라우저도 CDN도 못 쟁여서 **방문할 때마다 원본을 다시 받는다.**
- **왜 `no-cache`인가:** 리포 어디에도 `cacheControl` 지정이 없다(`grep` 0건). 시딩·업로드 경로가 기본값에 맡긴 결과이며, 유일하게 `max-age=3600`인 1개가 supabase-js 기본값으로 올라간 것으로 보인다.
- **해소 방향:** ⓐ 표시 크기에 맞는 변환본을 쓰거나(Supabase Storage 이미지 변환 또는 `next/image` + `remotePatterns`) 저장본 자체를 줄인다 ⓑ 업로드 시 `cacheControl`을 길게 주고 기존 180개 메타데이터를 갱신한다. **ⓑ가 코드 변경이 더 작고 효과는 재방문 전체에 걸린다 — 먼저 해볼 것.**
- **⚠️ 기존 결정과 충돌 확인 필요:** `ListingCardImage.tsx` 주석이 `next/image`를 **의도적으로 쓰지 않기로** 한 근거 3개(저장본이 이미 작다 / `remotePatterns` 설정이 선행 / 공개 URL이 고정이라 캐시가 그대로 먹는다)를 적어 두었는데, 그 중 첫째와 셋째가 위 실측으로 **사실이 아님이 확인됐다**(중앙값 197KB는 "작다"고 보기 어렵고, `no-cache`라 캐시가 안 먹는다). 이어받을 때 그 주석부터 정정할 것.

### DW-542: `/search`가 매물 전량(93~101건)을 한 페이지에 렌더한다 — 페이지네이션 없음

origin: 2026-07-29 사용자 "전체적으로 느리다" 지적 #7 → 원인 분석(실측)
location: `web/src/app/(user)/search/page.tsx`의 목록 쿼리 — `.order(...)`만 있고 `.limit()`이 없다.
severity: medium
reason: 사용자 결정(2026-07-29): 성능 묶음은 마지막. 그리고 페이지네이션은 순수 성능 수정이 아니라 **URL 상태·필터와 맞물리는 UX 변경**이라(랜딩은 필터·URL 쿼리를 소유하지 않고 `/search`가 단독 소유한다는 기존 계약) 설계 판단이 먼저다.
trigger: 성능 묶음에서 `DW-541`(이미지)을 처리한 뒤 — 이미지 비용이 줄면 이 항목의 체감이 얼마나 남는지 다시 재고 결정한다. 무한스크롤/페이지 버튼/더보기 중 무엇을 쓸지는 그때 UX 결정으로 정한다.
status: done 2026-07-29
resolution: `/search`에 페이지네이션 도입(커밋 c3737ec) — 한 페이지 24건(D5의 4열·2열 공배수라 마지막 줄이 안 빈다). 총 건수는 PostgREST `count:'exact'`가 **같은 응답의 Content-Range**로 주므로 왕복이 늘지 않는다(`buyerListingsQuery`에 optional 인자 추가, 기존 호출부 무변경). 페이지 링크는 정규화된 필터값으로 다시 조립하고 `page=1`은 안 붙여 기존 주소·북마크를 보존한다. ⚠️ **착수 전 가정이 틀렸던 것을 실측으로 잡았다** — 범위 밖 page는 0행이 아니라 에러(PGRST103)로 오며, 그대로 두면 "불러오지 못했습니다"라는 엉뚱한 안내가 뜬다. 그 코드만 갈라 "이 페이지에는 매물이 없습니다 + 첫 페이지로"를 보여주고 에러 로그도 남기지 않는다. 실측: 1페이지 24건 + "95건 · 1/4" · `?page=2` 이동 · `?fuel=가솔린`에서 43건·1/2이고 다음 링크가 필터 보존 · `?page=99` 안내.
- ✎ **후속 (2026-07-29, 사용자 요청):** 범위 밖 page에서 안내문을 읽히는 대신 **마지막 페이지로 보낸다**(커밋에 반영). 총 건수는 그 응답에 없으므로(에러라 count가 null) 같은 필터로 **개수만**(`head: true`, 행 미수신) 다시 물어 마지막 페이지를 구한 뒤 `redirect`한다 — **정상 경로엔 비용이 0**이고, 손으로 주소를 고친 드문 길에서만 왕복이 한 번 는다. 주소도 함께 바로잡히므로 북마크·뒤로가기가 정직해진다. ⚠️ `last < page`일 때만 보낸다 — 두 조회 사이에 매물이 늘어나는 경합에서 무한 왕복을 막는 정지 조건이며(엄격히 작아지므로 반드시 끝난다), 걸리면 리다이렉트 없이 기존 안내문으로 떨어진다(막다른 길 없음). 필터 조건은 `applyFilters` 하나로 뽑아 두 조회가 같은 조건을 쓰게 했다(두 벌로 적으면 한쪽만 고쳐져 갈린다). 실측: `?page=99` → 307 → `?page=4`(4/4, 다음 비활성) · `?fuel=가솔린&page=99` → `?fuel=가솔린&page=2` · 0건 필터 + `page=5` → 1페이지(page 파라미터 제거)로 가서 "조건에 맞는 매물이 없습니다" · 정상 `?page=2`는 200 그대로(회귀 없음).
- **실측(2026-07-29):** 운영 `/search` 카드 93건, HTML 압축 전 **320KB**, `<img>` 90장. 로컬 시드에서도 93~95건 전량 렌더 확인.
- **곱셈 효과:** `DW-541`(장당 150~190KB, 캐시 없음)과 곱해지면 한 화면을 끝까지 스크롤할 때 **십수 MB**를 매 방문 새로 받는다.
- **이미 알고는 있었다:** `web/src/lib/listings.ts`의 `COVER_IMAGES_CHUNK_SIZE` 주석이 *"`/search`엔 `.limit()`이 없어 실제로 벌어질 수 있는 크기"*라며 id 목록을 50개씩 쪼개는 방어를 넣어 뒀다 — **증상은 알고 원인은 안 건드린** 상태다.

### DW-543: AI 검색 첫 호출이 Cloud Run 콜드스타트로 4.4초 걸린다

origin: 2026-07-29 사용자 "전체적으로 느리다" 지적 #7 → 원인 분석(실측)
location: Cloud Run 서비스 `encar-ai-api-dev`(asia-northeast3) — 최소 인스턴스 0.
severity: low
reason: 사용자 결정(2026-07-29): 성능 묶음은 마지막. 게다가 이건 **비용을 내면 사라지는 문제**라 기술 판단이 아니라 제품 판단이다(최소 인스턴스 1 = 상시 과금).
trigger: 성능 묶음 마지막 — 또는 **시연/제출 직전**. 데모를 보여주기 직전에만 한 번 깨워 두는 것으로 충분할 수 있다(설정 변경 없이).
status: done 2026-07-29
resolution: **선택지 ⓑ(정직한 표시)를 택했다**(커밋 4704c91) — 검색이 2.5초를 넘기면 "AI 서버를 깨우는 중이에요. 첫 검색은 몇 초 걸릴 수 있어요…"로 문구를 바꾼다. 2.5초 근거: 깨어 있는 서버 응답이 0.065초라 정상 검색은 여기 도달하지 못하고, 콜드스타트 4.4초보다 충분히 짧다. ⓐ(최소 인스턴스 1)는 상시 비용이 붙는 제품 결정이라 하지 않았다 — **원인 자체는 그대로 남아 있고 이 항목이 닫는 것은 "사용자가 이유를 모른 채 기다리는 것"뿐이다.** 상시 대기가 필요해지면(시연 등) 새 항목으로 연다. 타이머는 effect가 아니라 이벤트 핸들러에 건다(effect면 `react-hooks/set-state-in-effect` 위반 — 실측).
- **실측(2026-07-29):** `/health` 첫 호출 **4.425s** → 이후 연속 호출 0.065s / 0.071s / 0.065s. 즉 느린 건 요청 처리가 아니라 **깨우는 시간**이다.
- **사용자 체감:** 랜딩 히어로에서 AI 검색을 처음 누른 사람은 4~5초를 기다린다. 그게 이 서비스의 1급 기능이라 첫인상에 그대로 꽂힌다.
- **해소 선택지:** ⓐ 최소 인스턴스 1(상시 비용) ⓑ 그대로 두고 화면에서 "깨우는 중" 상태를 정직하게 보여주기 ⓒ 시연 직전 수동 웜업. **ⓑ는 코드 변경이지만 공짜다 — 먼저 검토할 것.**

### DW-544: "차장님" 로고가 아직 임시 lockup이다 — 실제 아트워크 제작이 어느 에픽에도 없다

origin: 2026-07-29 사용자 지적 #6 (Discord) — "PRD/UX 할 때 간단한 그림 로고로 하기로 했었다"
location: `web/src/components/ui/Logo.tsx` — 헤더 주석이 스스로 *"실제 아트워크는 추후 제작 — 현재 lockup 임시"* 라고 적고 있다.
severity: low
reason: UX 결정 D7이 **방향만** 확정하고 아트워크 제작을 "별도 제작 단계(추후)"로 명시적으로 미뤘다(*"지금은 방향성만 확정, 블로킹 아님. 구현 시 이 lockup으로 임시 사용."*). 문제는 미룬 것 자체가 아니라 **그 "추후"가 어느 에픽·스토리에도 배정되지 않은 것**이다 — Epic 8~16 어디에도 없다(grep 확인).
trigger: 제출·시연용으로 브랜드 인상을 다듬는 시점, 또는 앱 아이콘이 실제로 필요해지는 시점(D7이 "앱 아이콘 겸용"으로 설계했으므로 Flutter Epic 16이 자연스러운 자리다). 그때 이 항목을 Epic 16 스토리의 인수조건으로 심는다(B5).
status: open

- **지금 화면:** petrol 라운드-스퀘어 배지 안에 한글 "차" + "차장님" 워드마크 — **결정된 방향 A "차 배지" 그대로이며 위반이 아니다.** 사용자가 기억한 "간단한 그림 로고"는 그 다음 단계다.
- **왜 지금 안 하나:** 아트워크는 코드 작업이 아니고, D7이 블로킹 아님으로 명시했다. 다만 적어 두지 않으면 영영 임시본으로 출시된다 — 실제로 Epic 8부터 지금까지 그렇게 왔다.
- **이어받을 때:** `Logo.tsx`는 크기 2종(`sm`/`md`)을 토큰 기반으로 그리므로 배지 안 글자만 SVG로 갈아끼우면 된다. 하드코딩 hex 금지 규칙(Story 8.1)을 유지할 것.

### DW-545: 카드 옵션 칩이 390px에서 93건 중 2건 잘린다("+N" 칩 일부) — 남은 잔여

origin: 2026-07-29 사용자 지적 #10 수정(칩 상한 4→3 + `shrink-0` + "+N") 후 실측으로 남은 잔여
location: `web/src/components/listings/ListingCard.tsx`의 옵션 칩 행(`flex-nowrap` + `overflow-hidden`).
severity: low
reason: 수정의 목표("몇 개를 못 보여주더라도 보이는 글씨는 온전히 읽힌다")는 달성됐다 — 잘리는 것은 맨 끝 **"+N" 개수 칩**이고 옵션 이름 3개는 전부 읽힌다. 남은 2건을 없애려면 글자 폭을 브라우저에서 재서 개수를 동적으로 정해야 하는데(카드 93장 × 측정), 얻는 것에 비해 복잡도가 크다(A2).
trigger: 옵션 이름이 더 긴 값이 통제어휘에 추가되거나(§11.1), 카드 폭이 더 좁아지는 레이아웃 변경이 생길 때 — 그때 다시 실측하고 "글자수 예산" 방식(누적 글자 수 상한으로 개수 결정)을 검토한다.
status: open

- **실측(2026-07-29, 로컬 시드 93건):** 390px 뷰포트(카드 내용 폭 304px) — **2건이 17px 넘침**, 넘치는 부분은 "+1" 칩. 가로 페이지 스크롤은 생기지 않는다(D5 유지). 800px 이상(카드 내용 폭 328px) — 93건 **전부 넘침 0건**.
- **넘치는 예:** `부메스터사운드 · 앰비언트라이트 · 파노라마선루프 · +1`, `오토파일럿 · 파노라마글래스루프 · 프리미엄오디오 · +1` — 희소 옵션 이름이 셋 다 긴 경우에만 발생한다.
- **이 사실은 코드 주석에도 적어 두었다**(`ListingCard.tsx` 옵션 칩 블록) — 다음 사람이 "왜 가끔 +N이 잘리지?"를 추측하지 않게.

### DW-546: 소비자 화면 8개가 아직 신규 디자인 시스템으로 리스킨되지 않았다 — FR37 "전 화면"인데 실행 스토리가 없다

origin: 2026-07-29 사용자 지적 #2 (Discord, 로그인 페이지 UI 일관성) → 전 화면 실측으로 범위 확장
location: `web/src/app/(auth)/login/page.tsx` · `(auth)/signup/page.tsx` · `(user)/chat/page.tsx` · `(user)/chat/[roomId]/page.tsx`·`ChatRoomMessages.tsx` · `(user)/search/SearchFilters.tsx` · `(user)/sell/page.tsx`·`SellForm.tsx`·`PhotoUploader.tsx`·`[id]/edit/page.tsx` · `app/page.tsx`(일부 잔존)
severity: medium
reason: Epic 8은 **토큰과 프리미티브를 만드는** 에픽이고(8.1 토큰·8.2 프리미티브·8.3 카드 계약), 화면별 적용은 각 에픽이 자기 화면을 건드릴 때 따라왔다 — Epic 9=카드·상세, Epic 11=랜딩·내비, Epic 15=관리자 6화면. 그런데 **로그인·회원가입·채팅·검색필터·판매 폼은 어느 에픽의 화면 목록에도 없다.** 즉 미룬 게 아니라 애초에 아무 스토리도 이 화면들을 자기 것으로 안 가졌다.
trigger: **Epic 15에 붙였다(사용자 결정 2026-07-29)** — `epics-increment-2026-07-12.md`의 Story 15.1 하단에 "➕ 추가 범위 — 소비자 잔여 화면 리스킨"으로 대상 화면 목록·실측치·완료 판정(리스킨 후 `zinc-*` 잔존 0)까지 심었다(B5·B8: 지정한 곳에 실제로 심는다). 즉 이 항목은 Epic 13 → 14 → **15** 차례가 오면 관리자 6화면과 함께 처리된다.
status: open

- **실측(2026-07-29, `zinc-*` 원시 클래스 vs `@theme` 토큰 사용 수):**

  | 화면 | zinc | 토큰 |
  |---|---|---|
  | `search/SearchFilters.tsx` | 24 | 0 |
  | `sell/PhotoUploader.tsx` | 22 | 0 |
  | `chat/[roomId]/ChatRoomMessages.tsx` | 20 | 0 |
  | `chat/[roomId]/page.tsx` | 16 | 0 |
  | `sell/[id]/edit/page.tsx` | 9 | 0 |
  | `chat/page.tsx` | 9 | 0 |
  | `(auth)/signup/page.tsx` | 9 | 0 |
  | `(auth)/login/page.tsx` | 9 | 0 |
  | `sell/page.tsx` | 8 | 0 |
  | (참고 — 이미 리스킨된 쪽) `listings/[id]`·`wishlist`·`account`·`OptionPicker` | 0 | 5~26 |

- **왜 눈에 띄나:** 리스킨된 화면(상세·찜목록·내 정보)과 안 된 화면(로그인·채팅)이 **한 세션 안에서 번갈아 나온다.** 로그인은 서비스의 첫 화면이라 첫인상에 그대로 꽂힌다.
- **범위 성격:** 신규 기능 0 — 색·테두리·radius·타이포 토큰 치환과 D5(가로 유지) 확인뿐이다. Epic 15가 관리자에게 하기로 한 것과 정확히 같은 작업이다.
- **함께 볼 것:** `DW-547`(인증 화면에 상단바가 없어 랜딩으로 돌아갈 길이 없다) — 로그인 화면을 손대는 그 자리에서 같이 해결된다.

### DW-547: 로그아웃하면 랜딩이 아니라 `/login`으로 가고, 그 화면엔 빠져나올 길이 없다

origin: 2026-07-29 사용자 지적 #4 (Discord)
location: `web/src/components/auth/LogoutButton.tsx`의 `router.push('/login')` · `web/src/app/(auth)/login/page.tsx`·`signup/page.tsx`(둘 다 `AppHeader`를 렌더하지 않는다)
severity: medium
reason: 이 동작은 Story 1.3(2026-06, FR2)이 쓴 것이고 **그때는 옳았다** — 당시엔 비로그인 사용자가 볼 수 있는 화면이 없었으므로 로그아웃 후 갈 곳이 로그인 화면뿐이었다. 그 전제를 FR58(비로그인 열람 허용, Epic 8.5)이 뒤집었는데 이 두 줄이 함께 갱신되지 않았다. UX 문서 어디에도 "로그아웃 후 목적지"를 명시한 문장은 없다(grep 확인) — 그래서 아무도 어긋남을 못 봤다.
trigger: `DW-546`(로그인·회원가입 리스킨)을 처리하는 그 자리 — 어차피 그 두 파일을 열게 된다. 그 전이라도 `LogoutButton` 한 줄만 먼저 고칠 수 있다.
status: done 2026-07-29
resolution: 로그아웃 목적지를 `/login`→`/`로 바꾸고(FR58 정합), `(auth)/layout.tsx`를 신설해 로그인·회원가입에 상단바를 붙였다(커밋 42028ce). 두 페이지가 `'use client'`라 서버 컴포넌트인 AppHeader를 직접 못 그려 라우트 그룹 레이아웃이 그 자리를 맡는다. `email`을 안 넘기므로 안읽음 RPC는 호출되지 않아 DB 왕복이 늘지 않는다. 헤더가 붙으며 생긴 세로 넘침(`min-h-screen`)만 `flex-1`로 고쳤다(내 변경이 만든 것만). E2E C1의 착지 경로 단언도 `/login`→`/`로 갱신. 실측: `/login`에 헤더·홈 링크 존재 + 넘침 없음 · 로그아웃 → `/` 이동 + 비로그인 내비 표시. ⚠️ **화면 리스킨은 여기 없다** — `DW-546`으로 Epic 15에 붙였다.
- **증상(사용자 실측):** 로그아웃 → `/login`. 거기서 랜딩으로 가려면 **주소창에서 `/login`을 직접 지우는 수밖에 없다.**
- **왜 FR58과 어긋나나:** FR58과 UX 결정이 세운 규칙은 *"비로그인도 랜딩·탐색·상세를 열람할 수 있고, 로그인 게이트는 **행동**(문의·등록·찜)에만 건다"* 이다. 그 규칙대로면 로그아웃한 사용자의 자연스러운 목적지는 **공개 랜딩(`/`)** 이다. 지금은 로그아웃이 사용자를 "아무것도 못 보는 화면"에 가둔다.
- **선례가 이미 있다:** Story 11.3이 같은 부류를 한 번 고쳤다(구 `#152`) — 비로그인 홈에 상단바가 없어 *"로그인·내 차 등록 진입로가 거기 하나뿐"* 이던 문제. 인증 화면 2개만 같은 처리에서 빠졌다.
- **해소(작다):** ⓐ `LogoutButton`의 `router.push('/login')` → `router.push('/')` ⓑ `/login`·`/signup`에 `AppHeader`(또는 최소한 홈으로 가는 로고 링크)를 붙인다. ⓑ는 `DW-546`의 리스킨과 같은 파일이라 함께 하는 게 싸다.
- **⚠️ 확인할 것:** `redirectedFrom` 복귀 흐름은 건드리지 말 것 — 로그인 **성공** 후 원래 가려던 경로로 돌아가는 로직(`resolveSafeRedirect`)은 정상이고 이 항목과 무관하다.

### DW-548: 채팅방 목록에 방별 안읽음 표시가 없다 — Story 12.5가 의도적으로 뺐고, 사용자가 다시 요청

origin: 2026-07-29 사용자 지적 #3 (Discord) ↔ Story 12.5 스펙의 명시적 Never
location: `web/src/app/(user)/chat/page.tsx`(방 목록 렌더) · `supabase/migrations/0025_chat_unread_participant_scope.sql`의 `chat_unread_count()`(총합만 계산)
severity: low
reason: Story 12.5 스펙이 **Never로 명시**했다 — *"방 목록 각 행에 개별 안읽음 점(per-room indicator)을 추가하지 않는다 — FR57 AC가 요구하는 건 내비 배지(총합)와 정렬뿐이다(과설계 금지, A2)."* 그때는 옳은 판단이었다(FR57이 요구한 건 "판매자가 문의를 놓치지 않는다"이고 총합 배지+최신순 정렬로 충족된다). 코드리뷰에서 같은 제안이 올라왔을 때도 이 Never를 근거로 기각했다. 지금 다시 열린 이유는 **사용 경험 근거**다: 총합 배지를 보고 목록에 들어가면 어느 방이 새 메시지인지 알 수 없다.
trigger: 사용자 결정 대기. 하기로 하면 비용은 아래 산정대로 작다.
status: done 2026-07-29
resolution: 마이그 `0026_chat_unread_by_room` + 방 목록 배지(커밋 b3eb223). **Story 12.5의 Never를 사용자 결정으로 뒤집은 것**이라 그 경위를 마이그레이션 주석에 남겼다(다음 사람이 스펙만 보고 위반으로 읽지 않게). 계산식은 `chat_unread_count()`와 글자 그대로 같고 `group by`만 다르다 — 두 배지가 다른 규칙으로 세면 화면이 스스로 모순된다. 새 테이블·컬럼·백필 없음. **참여자 조인이 load-bearing임을 red/green으로 증명**(전부 트랜잭션 rollback): green=참여자 10건/2방·관리자 0건/0방·비참여자 0건/0방, red=조인 제거 시 관리자가 25건/5방(플랫폼 전체)을 봤다. 브라우저 실측: 방별 9·1 + 내비 총합 10(정확히 일치), 방 진입 후 뒤로가기 시 그 방만 소멸(9→없음, 총합 10→1). 운영 DB에도 적용 완료(before: 함수 부재 / after: security_definer=false·참여자 조인 존재·EXECUTE는 authenticated만, anon 없음). **범위 밖(명시): 실시간 감소** — 총합 배지도 페이지 로드 기준이라 방별만 실시간이면 두 배지가 다른 시점을 말한다.
- **비용 산정(코드를 읽고 낸 값, 추측 아님):**
  - **DB:** 마이그레이션 1장 — 기존 `chat_unread_count()`와 **같은 쿼리에 `group by m.room_id`만 붙인** `chat_unread_by_room()` 신설(returns table(room_id uuid, unread int)). 새 테이블·새 컬럼·백필 **전부 불필요** — `chat_room_reads`(0024)와 참여자 조인 가드(0025)가 이미 있다. 기존 함수는 건드리지 않는다(additive, B3).
  - **웹:** `chat/page.tsx`에 `.rpc()` 호출 1줄 + 행마다 배지 렌더 ~10줄. 방 목록은 이미 서버 컴포넌트라 구조 변경 없음.
  - **권한:** 0024·0025와 동일한 `revoke all → grant execute to authenticated` 패턴 복사.
- **대가(정직하게):** `/chat` 진입마다 DB 왕복 1회 추가. 지금은 함수가 미국에서 돌고 DB가 서울이라 왕복 하나가 비싸다(`DW-540`) — 그래서 **`DW-540`을 먼저 하면 이 비용이 저절로 싸진다.**
- **범위 밖(명시):** 카카오톡처럼 **실시간으로** 방별 숫자가 줄어드는 동작. 지금 총합 배지도 페이지 로드 기준이라(스펙 I/O 매트릭스: "다음 페이지 로드부터"), 방별만 실시간으로 만들면 두 배지가 서로 다른 시점을 말하게 된다. 실시간까지 원하면 별건으로 다뤄야 한다.

### DW-549: 조회수 RPC가 anon에 열려 있고 그 값이 랜딩 "인기 매물" 정렬의 입력이다 — 누구나 랭킹을 밀어올릴 수 있다

origin: sweep bundle `dw-epic-11-12-review-budget-followup` (run 20260730-113650-eb0d) — DW-2(11-1) 후속 독립 리뷰에서 blind-hunter가 발견, 세션이 코드로 재확인
location: `supabase/migrations/0020_listings_view_count.sql`(anon GRANT, 커밋 `d6548a9`) → `web/src/lib/listings.ts`(view_count desc 정렬) → `web/src/components/landing/PopularRecentGrid.tsx`
severity: medium
reason: `increment_listing_view` RPC에 레이트리밋·중복호출 방지가 없고 실행 권한이 anon(비로그인 포함)에 열려 있는데, 그 조회수가 랜딩 "인기 매물"의 실제 정렬 기준으로 쓰인다. 클라이언트가 유발한 값이 서버 판단 없이 랭킹에 그대로 반영되는 구조(CLAUDE.md B9 위반 패턴). 기존 DW-445(오버플로)·DW-447(값 의미 미정의)와는 다른 축 — 여기서 문제는 **조작 가능성**이다. 데모 규모 트래픽에선 실질 피해가 작아 즉시 수정 대상은 아니다.
trigger: DW-445(조회수 레이트리밋·오버플로)를 처리할 때 같은 원인을 공유하므로 함께 본다. 또는 랭킹이 실제 사용자에게 의미를 갖는 시점(운영 트래픽·노출 경쟁).
status: open

- **확인 한계(실측 기준):** GRANT 문과 정렬 조건을 코드로 읽어 "공격 가능한 경로가 실재함"까지 확인했고, RPC를 반복 호출해 랭킹이 실제로 뒤바뀌는 것은 **재현하지 않았다**.

### DW-550: 폰트 용량 가드가 크기만 보고 내용물(해시)은 안 본다 — 같은 크기 파일로 바꿔치기하면 통과

origin: sweep bundle `dw-epic-11-12-review-budget-followup` (run 20260730-113650-eb0d) — DW-4(11-5) 후속 독립 리뷰
location: `web/`의 `fonts.budget.test.ts` (커밋 `51c6154`)
severity: low
reason: sha256 해시 비교가 주석에만 적혀 있고 실제 검사 코드로 옮겨지지 않았다. 파일 크기만 검사하므로 크기가 같은 다른 폰트로 교체돼도 가드가 초록이다. "검사를 만들었다"와 "검사가 잡는다"의 간극(CLAUDE.md B4).
trigger: 셀프호스팅 폰트 자산을 교체·추가할 때, 또는 폰트 가드를 다시 손댈 때.
status: open

### DW-551: AppHeader 소스 스캔 정규식이 스프레드 속성 호출부를 못 잡는다

origin: sweep bundle `dw-epic-11-12-review-budget-followup` (run 20260730-113650-eb0d) — DW-3(11-2) 후속 독립 리뷰
location: `AppHeader.test.ts`의 `APP_HEADER_TAG` 정규식 (커밋 `48427e3` 도입; `dd000bb`는 이 정규식을 건드리지 않음)
severity: low
reason: `<AppHeader {...props} />` 형태로 렌더되는 호출부를 정규식이 매칭하지 못해, 그 경로로 헤더가 빠지거나 잘못 쓰여도 검사가 조용히 통과한다. 현재 코드에는 해당 호출부가 없어 오늘은 무해하다.
trigger: 헤더를 스프레드 속성으로 렌더하는 호출부가 처음 생길 때, 또는 이 계약 테스트를 다시 손댈 때.
status: open

### DW-552: 재연결 시 realtimeError를 지우는 조건식이 뒤집혀 있다 (현재는 도달 불가, 잠복)

origin: sweep bundle `dw-epic-11-12-review-budget-followup` (run 20260730-113650-eb0d) — DW-6·DW-7(12-3·12-4) 후속 독립 리뷰
location: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` 재연결 클리어 분기 (상태는 `b581b45`, 문제의 조건은 `4ec2075`)
severity: low
reason: Supabase Realtime 클라이언트의 현재 재연결 콜백 순서 전제에서는 오늘 도달하지 않는 경로다. 다만 트리거가 **우리가 통제하지 못하는 외부 라이브러리 동작**이라, 라이브러리가 순서를 바꾸면 즉시 살아난다(배너가 안 사라지거나 반대로 오류 중에 사라짐). 같은 리뷰에서 "현재 도달 불가"로 기각된 다른 후보들은 도달하려면 이 프로젝트 코드가 먼저 바뀌어야 해서 판정을 달리했다.
trigger: `@supabase/supabase-js`(Realtime) 업그레이드, 또는 재연결 배너 동작을 다시 손댈 때.
status: open

### DW-553: playwright.config.ts에서 빈 문자열 env가 .env.local 값을 이긴다 (같은 파일의 fail-loud 원칙과 불일치)

origin: sweep bundle `dw-epic-11-12-review-budget-followup` (run 20260730-113650-eb0d) — DW-4(11-5) 후속 독립 리뷰
location: `web/playwright.config.ts` (커밋 `51c6154`)
severity: low
reason: 같은 파일의 다른 env 필드는 "값이 없으면 즉시 실패"로 통일돼 있는데 이 필드만 빈 문자열을 조용히 채택한다. CI나 셸에 빈 값이 떠 있으면 `.env.local`을 무시하고 빈 설정으로 E2E가 도는데, 실패 지점이 설정에서 멀어져 원인 추적이 어려워진다.
trigger: E2E를 CI에 배선할 때(DW-468과 같은 자리) — 그때 빈 env가 실제로 흔해진다.
status: open

### DW-554: 44개 질의셋 전량(N=3 flaky 판정 포함) 라이브 캡처 미실행 — G2 baseline은 부분(3건)만 확보

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 구현(Tasks & Acceptance — Never 항목)
location: `api/scripts/run_phase_b.py`(신규 러너) · `api/docs/g2-baseline-partial.json`(현재 산출물, A1/B1/C1 3건만)
severity: low
reason: 44개 질의 × N=3(flaky 판정)을 이 무인 실행 안에서 전량 돌리면 Gemini 무료 티어 일일 쿼터
  (약 20 req/day, `api/tests/test_live_smoke.py` 주석 근거)를 한 번에 넘길 수 있다. 그래서 러너
  자체는 만들어 대표 3개(A1·B1·C1, 경로 A/B/C 각 1건)로 실제 동작을 실측 확인했지만(직접 실행·
  관찰, `api/docs/g2-baseline-partial.json`), 44개 전량 캡처는 **의도적으로 이번에 안 했다**
  (B8 — 미루는 판단은 틀린 게 아니라 안 적는 게 틀린 것).
trigger: 사용자가 Gemini 쿼터 여유를 확인하고 직접 실행할 때(또는 Story 13.8 착수 직전).
status: done 2026-07-30
resolution: **미룬 근거 자체가 사실이 아니었다.** 이 프로젝트의 Gemini 키는 **유료 티어**다(사용자
  확인, 2026-07-29). 위 reason이 인용한 "무료 티어 약 20 req/day"는 `test_live_smoke.py` 헤더의
  낡은 주석이었고, 그게 리포 안의 유일한 근거라 무인 세션이 그걸 읽고 판단했다 — 세션은 절차를
  제대로 밟았고(미룬 것을 등재하고 트리거까지 지정), 틀린 건 근거였다. 그래서 **원인부터 고쳤다**:
  `test_live_smoke.py:3`과 `run_phase_b.py` 헤더의 그 문구를 사실로 정정했다(안 고치면 13.8이
  같은 근거로 또 미룬다 — 게이트 자체는 유지, 실제 과금은 여전히 발생하므로).
  그 뒤 **44개 전량을 실제로 실행했다**(2026-07-30, 로컬 스택):
    `RUN_LIVE_SMOKE=1 DATABASE_URL=...55322 .venv/bin/python scripts/run_phase_b.py --out docs/g2-baseline.json`
    → 44/44 캡처, 실패 0건. 라우트 분포 A=27 · B=5 · C=12, 지연 중앙값 1,853ms.
    채점(`score_ab.py --raw docs/g2-baseline.json --out docs/g2-baseline-report.json`):
    커버리지 **44/44**(errored 0 · missing 0) · `is_partial: false` · 결과집합정확도 **0.938**(clean A, n=27) ·
    라우팅 **50/55** · 오염 0 · dead-end 0 · 게이트 **PASS**.
  ⚠️ **이 기준선을 읽을 때의 조건**(적어두지 않으면 다음 사람이 잘못 비교한다):
    ① **로컬 시드 DB(127.0.0.1:55322) 기준**이다 — 13.8이 다른 DB로 재면 매물이 달라 숫자가 달라지고,
       그건 RAG 회귀가 아니라 데이터 차이다. **같은 로컬 스택으로 재야 비교가 성립한다.**
    ② `flaky_measured: false` · `tokens_measured: false` — flaky 0과 비용 0은 **측정값이 아니라
       미측정**이다(러너가 구조적으로 N=1·토큰 0. DW-565 참조). "흔들림이 없다"로 읽으면 안 된다.
    ③ 라우팅 50/55 = **베이스라인에 이미 오라우팅 5건**이 있다. Story 13.2(4분기 라우팅)가 줄여야 할
       대상이 이 5건이고, 13.8은 이 수치와 대조한다.

- **실행법:** `api/` 에서
  `RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres
  .venv/bin/python scripts/run_phase_b.py --out docs/g2-baseline-full.json`
  (`--subset` 생략 = 44개 전량, 1회씩만 — N=3 flaky 판정까지 하려면 3회 반복 실행 후 병합이
  추가로 필요하다. 이 스토리는 N=1 러너만 만들었다).
- **채점:** `.venv/bin/python scripts/score_ab.py --queryset docs/ai-ab-test-queryset.json
  --raw docs/g2-baseline-full.json --out docs/g2-baseline-report.json` (1파일 모드,
  `baseline_summary` 키).

### DW-555: 하이브리드 벡터절 정규식이 `ORDER BY embedding <=> ...::vector` 정확히 이 모양·이 위치만 인식

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 2(adversarial + edge-case-hunter 중복 확인) — 이번 라운드엔 defer로 triage, 코드 변경 없음
location: `api/app/db/sql_guard.py`(96행대, `no_vector` 정규식: `order\s+by\s+embedding\s*<=>\s*(?:%s|%\(\w+\)s)\s*::\s*vector`)
severity: low
reason: 이 스토리의 I/O 매트릭스가 요구한 정확한 한 가지 모양(별칭 없음·단일 정렬 키)은 화이트리스트를 통과하고, 그 밖의 위치(SELECT 목록 등)는 여전히 `forbidden_column`으로 거부된다 — 의도한 동작. 다만 `ORDER BY (embedding <=> %s::vector)`(괄호로 감쌈)나 `ORDER BY category, embedding <=> %s::vector`(2차 정렬 키와 결합) 같은 변형은 이 정규식에 안 걸려 `embedding`/`vector`가 여전히 미화이트리스트 식별자로 거부된다(직접 재현 확인). I4 원칙상 이 절은 LLM이 아니라 코드(13.3)가 붙이므로, 13.3이 이 정확한 모양으로만 절을 생성하면 문제가 되지 않는다 — 하지만 13.3이 동점 처리 등으로 2차 정렬 키나 별칭을 붙이는 형태를 택하면 하이브리드 경로 전체가 `forbidden_column`으로 막힌다.
trigger: Story 13.3(하이브리드 노드) 스펙 작성 시 — 벡터절에 별칭이나 2차 정렬 키가 필요한지 먼저 확인하고, 필요하면 이 정규식을 그 모양까지 포함하도록 확장한다.
status: done 2026-07-31
resolution: Story 13.3이 `hybrid_rag_node`를 구현하면서 정확히 이 정규식이 기대하는 모양(`SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND (<조건>) ORDER BY embedding <=> %s::vector LIMIT <정수>`)으로만 SQL을 조립한다 — 별칭·2차 정렬키를 붙이지 않는다(`api/app/graph/hybrid_rag_node.py`). `sql_guard.py`의 벡터절 정규식 주석에 이 확인 완료를 남겼다("DW-555: 13.3은 별칭·2차 정렬 없이 정확히 이 모양만 쓰므로 기존 정규식 확장 불필요, 확인 완료"). 로컬 Supabase+GEMINI_API_KEY로 대표 조합형 질의 5건(3천만원 이하로 무난한 패밀리카·가족이랑 타기 좋은 7인승 차 보여줘·연비 좋은 차 중에 2천만원 이하로 보여줘·초보가 몰기 쉬운 작은 차 2천 이하면 좋겠어·연비 좋은 전기차 추천)을 직접 실행해 매번 가드를 통과하거나(3건, 예: `seats = 7`·`body_type IN ('경차', '소형차') AND price <= 20000000`·`fuel = '전기'`) 정상 폴백함을 확인(2건, `NONE`→doc_rag_node)했다(B4 실측). `api/tests/test_hybrid_rag_node.py`가 조립 모양을 회귀 고정한다.

### DW-556: `run_phase_b.py --model` 생략 시 캡처 시점의 baseline 모델명으로 항상 라벨링됨

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 2(adversarial 확인) — 이번 라운드엔 defer로 triage, 코드 변경 없음
location: `api/scripts/run_phase_b.py`(`main()`, `model_name = args.model or settings.gemini_generation_model`)
severity: low
reason: 이 스토리는 baseline 단독 캡처만 다루므로 `--model` 생략이 지금은 안전하다(항상 현재 baseline 모델로 정확히 라벨링됨). 하지만 이 스크립트의 docstring이 이미 명시하듯 Story 13.8이 후보 모델 캡처에 이 스크립트를 재사용할 가능성이 있는데, 그때 `--model`을 깜빡하면 후보 결과가 baseline 모델명으로 조용히 오라벨링돼 A/B 비교 전체가 오염될 수 있다.
trigger: Story 13.8이 후보 모델 캡처를 이 스크립트로 실행하기 직전 — 그 시점에 `--model`을 필수 인자로 바꿀지 검토한다.
status: done 2026-08-02
resolution: **13.8 범위 밖으로 종결(모델 비교 아님)** — `spec-13-8-rag-exit-gate-검증-sm-f-sm-g-g2-cm-b.md`가
  정정한 전제다. 이 항목은 "Story 13.8 = 후보 모델 A/B 채택 판단"을 전제로 defer됐으나,
  `epics-increment-2026-07-12.md`의 실제 13.8 AC(967~1130줄)엔 모델 비교가 없다 — SM-F/SM-G/G2/CM-B
  네 게이트(단일 코드 상태 post-13.7의 회귀 확인)뿐이다. 실제로 13.8은 `run_phase_b.py`를
  `--model` 인자 없이(=현재 baseline 모델 그대로 라벨링) 오늘(2026-08-02) 47문항 재캡처에만
  썼다 — 후보 모델 캡처는 이번에도 하지 않았다. 모델 후보 비교가 실제로 생기면 그때 이 항목을
  다시 열어 `--model` 필수화를 검토한다.

### DW-557: `status='on_sale'` 강제가 "존재 확인"뿐이어서 `NOT status='on_sale'`로 판매완료 매물이 노출된다 (FR11 우회, 실측)

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial 발견, 오케스트레이터가 로컬 DB로 재현) — 선재 결함이라 defer, 이번 스토리는 코드 변경 없음
location: `api/app/db/sql_guard.py`(status 필터 검사: `re.search(r"status\s*=\s*'on_sale'", cleaned)`)
severity: high
reason: 검사가 "`status='on_sale'`라는 문자열이 어딘가 있는가"만 본다. 부정 래퍼는 그 존재 조건을 만족시키면서 술어를 뒤집는다 — `not`·`is`·`true`는 모두 `_SQL_KEYWORDS`에 있어 식별자 스캔도 통과한다. 로컬 DB(판매완료 8건·판매중 95건)로 직접 실행해 확인:
  `SELECT id, status FROM listings WHERE NOT status = 'on_sale' LIMIT 5` → 가드 통과 + 실행 성공 + **실제 `sold` 행 3건 반환**.
  `SELECT id, status FROM listings WHERE status = 'on_sale' IS NOT TRUE LIMIT 5` → 동일하게 통과·같은 sold 행 반환.
  `ai_readonly` 롤의 RLS는 `using(true)`라 2차 방어선이 없다(그 모듈 주석이 이미 그렇게 적고 있다). 베이스라인 `d654beb`에서도 동일하게 재현되므로 이번 변경이 만든 것은 아니지만, FR11("판매완료는 구매자의 모든 경로에서 비노출", `docs/conventions.md` §6)의 유일한 실패 모드가 실제로 열려 있다는 뜻이다. 이번 스토리의 intent는 "status 강제는 하이브리드 SQL에도 **그대로** 적용된다"(기존 동작 보존)여서 강화는 범위 밖이었다.
trigger: Story 13.2(4분기 라우팅) 착수 시 — 라우팅이 SQL 경로를 넓히기 전에 먼저 막는다. 고칠 방향은 "문자열 존재"가 아니라 "최상위 AND 결합항으로서의 술어"를 요구하는 것이고(부정·`IS NOT TRUE`·`<>`·달러쿼팅 차단 포함), 세 형태 각각에 red-first 회귀 테스트를 붙인다.
status: done 2026-07-30
resolution: Story 13.2 최초 구현(문자열 존재 검사)과 review-1(부정 연산자 정규식을 "괄호 깊이 무관 + 6종"으로 확장)이 둘 다 review 라운드에서 실측으로 뚫렸다 — review-1이 넓힌 정규식은 review-2가 따옴표 불리언(`(status='on_sale')='f'`)과 괄호로 감싼 불리언(`(status='on_sale')=(false)`)으로 다시 뚫었다. "알려진 부정 표현을 정규식으로 나열"하는 접근이 두 라운드 연속 실패해 수렴하지 않는 전략임이 실증됐으므로, review-2에서 정규식 나열 접근을 완전히 폐기하고 sqlparse 토큰 기반 구조적 검사로 교체했다: WHERE절을 파싱해 최상위(순수 그룹핑 괄호만 감싼 것은 최상위로 인정) AND 결합항 중 부정·재비교 없이 `status = 'on_sale'`이 정확히 그대로 있는 항이 하나라도 있는지 구조적으로 판정한다(`_has_unnegated_status_on_sale`). review-3은 이 구조적 검사가 반대 방향으로 과잉 차단하는 버그(`WHERE (status='on_sale' AND price<X)`처럼 WHERE절 전체를 바깥 괄호로 감싼 정상 쿼리를 오탈락)를 실측해, AND 분리 전에 WHERE절 전체를 감싼 괄호도 벗기도록 수정했다.
  **정확한 테스트 현황(review-3이 이전 문구의 부정확한 개수·미검증 주장을 지적해 정정)**: `api/tests/test_sql_guard.py`의 DW-557 전용 블록에 **총 15건**(거부 12건 + 정상 통과 3건)이 있다. 거부 12건 중 **11건**은 구조적 검사(`missing_status_filter`)가 의도한 대로 막는 서로 다른 우회 형태(`NOT status`·`NOT (status)`·`NOT ((status))`·`IS NOT TRUE`·`IS FALSE`·`=false`·`<>true`·`!=true`·`='f'`·`=(false)`·review-3이 새로 찾은 "WHERE절 전체를 감싼 뒤 NOT"). **나머지 1건은 예외다** — `(status='on_sale') IS DISTINCT FROM TRUE`는 `missing_status_filter`가 **아니라** `forbidden_table`로 거부된다(원인은 이 스토리의 구조적 검사가 아니라 기존 테이블 화이트리스트 정규식이 "DISTINCT FROM TRUE"의 "FROM TRUE"를 두 번째 FROM절로 오인하는 무관한 우연 — `re.findall`로 직접 재현: `['listings', 'TRUE']`). 이전 resolution 문구가 이 형태를 "막는다"고만 적고 사유를 확인 안 한 채 뭉뚱그렸던 것을 review-3이 지적해, 이번에 전용 테스트(`test_status_on_sale_is_distinct_from_true_rejected`)로 실제 사유(`forbidden_table`)를 그대로 단언하도록 정정했다. 정상 통과 3건은 단독·AND 결합·그룹핑 괄호 status='on_sale'과, review-3이 고친 "WHERE절 전체를 감싼" 정상 형태를 검증한다. `api/tests/test_sql_guard.py`에서 review-3 신규분 red(수정 전 실측: 과잉차단 1건 + 신규 전용 테스트 2건 전부 기대와 다른 결과) → green(수정 후 전부 의도한 코드)으로 실측 확인.

### DW-558: LIMIT·OFFSET 절 파싱이 bare integer 이외 형태를 못 잡아 안전 상한이 우회된다 (4형태 실측)

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial + edge-case-hunter 중복 발견, 오케스트레이터가 재현) — 선재 결함이라 defer
location: `api/app/db/sql_guard.py`(OFFSET 숫자 매처 · LIMIT 숫자 매처 · `limit_malformed` 분기)
severity: high
reason: 숫자 매처가 `\b(limit|offset)\s+([-+]?\d+)`로 **첫 정수만** 잡고 절 전체를 앵커링하지 않는다. `limit_malformed` 분기는 "정규식에 아예 안 걸릴 때"만 발사되므로, 정규식이 부분 매치하는 형태는 전부 검사를 통과한다. DW-315가 닫은 4증상(`LIMIT 0`·`LIMIT -5`·`LIMIT (10)`·OFFSET-only)과는 **다른 형태**이며 그 항목에 카탈로그된 적이 없다. 직접 실행해 확인(전부 베이스라인 `d654beb`에서도 동일):
  - `... LIMIT 5+100` → 통과. `n=5`로 판정되고 SQL은 그대로 실행 → 로컬 DB에서 **95행 전량 반환**(MAX_LIMIT=50 우회, 무제한 과다조회).
  - `... LIMIT 5 OFFSET (999999)` / `... OFFSET 500+600` → 통과. `offset_match`가 `None`이 되어 MAX_OFFSET=1000 검사가 **통째로 건너뛰어진다**(OFFSET에는 `offset_malformed` 짝 분기가 없다).
  - `... LIMIT 10, 5`(MySQL 2인자 형태) → 통과 후 psycopg가 실행 단계에서 거부 → `/ai/search` 500.
  - `... LIMIT 5 LIMIT 999`(이중 LIMIT) → 통과 후 실행 단계 문법 오류 → 500. `sql_rag_node`의 재시도 루프가 직전 SQL을 되먹이므로 재시도 산출물로 나올 수 있는 형태다.
trigger: Story 13.3(하이브리드 노드) 착수 시 — 그 스토리가 벡터절에 `LIMIT k`를 붙이며 이 블록을 다시 만진다. 고칠 방향은 LIMIT/OFFSET 절을 "꼬리에 오는 bare integer" 형태로 **전체 앵커링**하고 그 밖의 모든 형태를 `limit_malformed`/신규 `offset_malformed`로 명시 거부하는 것이다.
status: done 2026-07-31
resolution: `api/app/db/sql_guard.py`의 LIMIT·OFFSET 숫자 매처를 값 뒤(lookahead)가 문장 끝 또는 짝이 되는 절(LIMIT↔OFFSET)로만 이어지도록 전체 앵커링했다(`(?=\s*$|\s+offset\b)`/`(?=\s*$|\s+limit\b)`). 이중 LIMIT/OFFSET은 값 판정 전에 개수 검사로 먼저 거부하고(`limit_malformed`/신규 `offset_malformed`), OFFSET에도 LIMIT과 대칭인 malformed 분기를 신설했다. red→green 실측(B4): 수정 전 코드(baseline)에 `LIMIT 5+100`·`LIMIT 10, 5`·`LIMIT 5 LIMIT 999`·`OFFSET 5 (999999)`·`OFFSET 500+600` 5형태를 넣으면 전부 조용히 통과(PASSED (BUG))했고, 수정 후엔 전부 `limit_malformed`/`offset_malformed`로 거부되며 정상 `LIMIT 5`·`LIMIT 5 OFFSET 10`은 회귀 없이 통과함을 확인했다. `api/tests/test_sql_guard.py`에 6형태 거부 + 2형태 정상 통과 회귀 테스트를 추가했다.

### DW-559: 하이브리드 벡터절이 가드를 통과한 뒤 params 없이 실행돼 400이 500으로 바뀐다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial + edge-case-hunter + verification-gap 3중 확인) — intent의 Never("13.2·13.3의 실제 그래프 배선을 만들지 않는다")가 이 배선을 13.3으로 미루므로 defer
location: `api/app/graph/sql_rag_node.py`(`run_select(safe_sql)` — params 없이 호출) · `api/app/db/sql_guard.py`(벡터절 화이트리스트) · `api/app/routers/ai.py`(광역 except → 500)
severity: medium
reason: 이번 스토리가 화이트리스트한 `ORDER BY embedding <=> %s::vector`는 **미바인드 자리표시자를 담은 SQL을 반환**한다. I4 원칙상 그 절은 코드가 붙이고 params도 코드가 넘기지만, 그 배선(13.3)이 아직 없어서 지금은 정당한 생산자가 없다. LLM이 환각·프롬프트 인젝션으로 그 모양을 뱉으면 가드는 통과시키고, `run_select`는 params 없이 실행해 psycopg 문법 오류가 나고, `sql_rag_node`의 `except SqlGuardError`가 못 잡아 500 `internal_error`가 된다 — 이 변경 전에는 `forbidden_column` 400(한국어 안내 + LLM 1회 자기수정)이었다. 데이터 노출은 없고 에러 품질만 나빠지는 회귀다. 테스트도 가드의 **판정**만 보고 **산출물이 실행 가능한지**는 아무도 안 본다.
trigger: Story 13.3(하이브리드 노드) 구현 시 — 코드가 벡터절과 params를 함께 넘기는 경로를 만들 때 함께 정한다. (a) params를 받는 별도 진입점을 두거나 (b) `run_select`가 `%` 있는 쿼리를 params 없이 실행하지 않게 하거나 (c) 가드 통과 SQL을 실제로 실행해 보는 테스트를 붙인다.
status: done 2026-07-31
resolution: `hybrid_rag_node`(`api/app/graph/hybrid_rag_node.py`)가 정당한 생산자가 됐다 — 가드 통과 직후 `embed_query(query)` → `_vec_literal`(doc_rag_node와 동일 로직)로 만든 벡터 리터럴을 `run_select(safe_sql, (qvec_literal,))`의 params로 실제로 바인딩해 실행한다. `api/tests/test_hybrid_rag_node.py`의 `test_hybrid_assembles_expected_sql_and_binds_embedding_params`가 `run_select`에 전달되는 `params`가 정확히 `(_vec_literal(...),)`인지 배선을 못박는다. 로컬 Supabase+GEMINI_API_KEY 라이브 스모크(`test_live_smoke_hybrid`, DW-555 resolution의 5건 수동 실행)로 실제 psycopg 실행까지 성공함을 확인했다(400이 500으로 바뀌는 회귀 없음).

### DW-560: 에픽·아키텍처 문서의 벡터절 바인드 형태(`$1::vector`·`LIMIT k`)가 psycopg `%s`와 어긋나 가드가 거부한다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial + edge-case-hunter + intent-alignment 3중 확인) — 선재 계획문서/드라이버 불일치라 defer
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(AC-SEC-1·FR45 서술) · `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md`(I4) · `_bmad-output/implementation-artifacts/epic-13-context.md`(위 두 문서에서 복사됨)
severity: medium
reason: 계획문서 3곳이 하이브리드 절을 `ORDER BY embedding <=> $1::vector LIMIT k`로 규정한다. `$1`은 asyncpg/raw 프로토콜 스타일이고 이 프로젝트의 드라이버는 psycopg(`%s`·`%(name)s`)다. 실측: `... ORDER BY embedding <=> $1::vector LIMIT 10` → `forbidden_column` 거부, `... ORDER BY embedding <=> %s::vector LIMIT %s`(문서가 말하는 "LIMIT k를 바인드 파라미터로") → `limit_malformed` 거부. 13.3은 이 문서를 보고 쓰이도록 설계돼 있으므로, 문서를 그대로 따르면 하이브리드 경로가 100% 막힌다. 아키텍처 문서의 "`embedding`/`vector` 식별자를 화이트리스트로 추가" 서술도 1차 리뷰에서 폐기된 접근(위치-무관 화이트리스트)을 가리킨다.
trigger: Story 13.3 스펙 작성 직전 — 계획문서 3곳의 `$1::vector`를 `%s::vector`로, `LIMIT k` 바인드 서술을 코드가 정수로 붙이는 형태로 정정하고, 폐기된 화이트리스트 서술을 위치-스코프 방식으로 갱신한다.
status: done 2026-07-31
resolution: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(AC-SEC-1 서술·Story 13.3 AC 2곳, 3줄)와 `architecture-increment-2026-07-12.md`(하이브리드 검색 서술·I4 서술, 2줄)의 `$1::vector`를 `%s::vector`로, "LIMIT k를 바인드 파라미터로 덧붙임"을 "`%s`는 임베딩 바인드, `LIMIT k`는 코드가 붙이는 정수 리터럴(바인드 아님)"로 정정했다. `epic-13-context.md`는 이번 스토리 Code Map에 없어 손대지 않았다(별도 확인 필요 시 후속). architecture 문서의 "embedding/vector 식별자를 화이트리스트로 추가" 서술도 "위치-스코프로만 화이트리스트(전역 추가 아님)"로 정정했다.

### DW-561: `router_node`의 폴백이 일시적 429/timeout을 삼켜, G2 캡처가 폴백 라우트를 실측값으로 기록한다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(edge-case-hunter 발견) — 선재 라우터 동작이라 defer
location: `api/app/graph/router_node.py`(`structured.invoke` 광역 except → `_fallback_route()`) · `api/scripts/run_phase_b.py`(item별 try/except가 이 예외를 볼 수 없다)
severity: medium
reason: `router_node`가 라우팅 LLM 호출 실패를 잡아 휴리스틱 라우트(매물 신호 있으면 `B`, 없으면 `C`)를 반환하고 **재던지지 않는다**. 그래서 러너의 item별 try/except는 라우터 단계의 429를 절대 못 본다 — 폴백 결과가 정상 측정값과 구별 없이 raw에 들어간다. 쿼터 압박이 가장 심한 상황(44건 전량 캡처, DW-554)이 바로 429가 잦은 상황이고, 폴백 `C`는 가드 안내 답변이라 dead-end로도 안 잡혀 `gate_pass`가 그대로 참이 된다. 그 수치가 이후 모든 RAG 스토리의 기준선이 된다.
trigger: DW-554(44건 전량 라이브 캡처) 실행 직전 — `run_search()`가 폴백 여부를 노출하게 하고(예: `route_fallback` 플래그) 러너가 item별로 기록해, 폴백이 섞인 캡처를 baseline으로 승격하지 않도록 막는다.
status: open

### DW-562: 질의셋의 `primary_path` A/B/C와 13.2가 도입할 라우트 어휘(`REJECT|CLARIFY|SQL|HYBRID`)가 어긋난다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial 발견) — 선재 에픽 설계 긴장이라 defer
location: `api/docs/ai-ab-test-queryset.json`(`primary_path`: A/B/C) · `api/scripts/score_ab.py`(`route_ok()` — 단순 문자열 비교) · `api/docs/g2-baseline-partial.json`(A/B/C로 캡처됨) · `_bmad-output/implementation-artifacts/epic-13-context.md`(13.2가 4분기 라우트 어휘를 도입한다고 규정)
severity: medium
reason: G2 라우팅 채점은 캡처된 `route_last`를 질의셋의 `primary_path`와 문자열로 비교한다. 13.2가 라우트 어휘를 4분기로 바꾸면 재실행은 전부 불일치가 되어 라우팅 정확도가 0/44로 떨어진다 — 실제 회귀가 아닌데 "전면 회귀"로 오판하거나, 질의셋을 다시 쓰면서 baseline이 무효가 된다. 어느 쪽이든 13.1이 baseline을 만든 이유가 사라진다.
trigger: Story 13.2 스펙 작성 시 — 새 라우트 어휘와 질의셋 `primary_path` 사이의 매핑을 그 스펙에서 먼저 정하고 `score_ab.py`의 `route_ok()`에 반영한다(또는 baseline 전량 캡처를 13.2 이후로 미룬다).
status: done 2026-07-30
resolution: Story 13.2가 `score_ab.py`에 `_LEGACY_ROUTE_ALIASES = {"A": "SQL", "B": "CLARIFY", "C": "REJECT"}`를 두고 `route_ok()`가 `primary`/`acceptable`만 이 매핑으로 번역한 뒤 `actual`(항상 신버전)과 비교한다 — 큐리셋(`ai-ab-test-queryset.json`)의 A/B/C 데이터는 손대지 않는다(Never 절). 같은 근본 원인으로 멀티턴 하드 오염 게이트(`score_model()`의 `tr["route"] == "A"` 리터럴)도 `"SQL"`로 함께 갱신했다 — 안 고치면 route_ok만 고쳐도 오염 게이트가 조용히 무력화되는 자리였다. `api/tests/test_ab_scoring.py`에서 red(수정 전 실측: `route_ok("SQL","A",["A"])`가 False) → green으로 확인. review-1·review-2 모두 이 closure를 재작업 대상으로 지정하지 않았다(내용상 정확했다고 확인, Spec Change Log KEEP instructions 참조) — 재구현에서도 그대로 유지. (이 게이트가 HYBRID 경로는 놓친다는 review-2 지적은 별도 사안으로 이번 스토리 범위 밖으로 이월 — moot, 다음 리뷰 패스.)

### DW-563: CLARIFY 턴 상한이 클라이언트 강제로만 규정돼 있다 (유료 API 호출 상한이 상한이 아니다)

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 4(adversarial 발견) — 13.1 범위 밖의 선재 계획 결정이라 defer
location: `_bmad-output/implementation-artifacts/epic-13-context.md`(CLARIFY 턴 상한 서술 · JWT 게이트 과금방어 근거) 및 그 원본 계획문서
severity: medium
reason: 같은 문서가 한쪽에서는 "CLARIFY는 최대 2~3턴까지만 허용, **클라이언트가 횟수를 추적해 강제**"라 쓰고, 다른 쪽에서는 JWT 게이트를 "AI 검색은 실제 유료 API 호출을 발생시키는 행동이라 신원이 곧 과금 방어선(질의당 최대 4회 호출)"이라 정당화한다. 클라이언트만 세는 상한은 상한이 아니다 — 유효한 JWT 하나로 `/ai/search`에 CLARIFY 루프를 직접 반복하면 질의당 4회 유료 호출이 무제한 반복된다. CLAUDE.md B9("클라이언트가 보낸 값은 참고지 신뢰가 아니다") 위반.
trigger: Story 13.4(CLARIFY) 스펙 작성 직전 — 턴 상한을 서버가 검증하는 값으로 바꿀지(예: 서버가 검증하는 `clarify_depth`) 결정하고 계획문서에 그 결정을 박는다.
status: done 2026-07-31
resolution: Story 13.4가 서버 강제로 결정했다 — 새 필드(`clarify_depth` 등)를 만들지 않고, 서버가 이미 매 요청마다 받는 `context`(FR18, 새 인프라 아님)의 길이로 `clarify_turns = len(context or []) // 2`를 직접 계산한다(`api/app/graph/graph.py`의 `run_search`). `_CLARIFY_TURN_CAP = 3` 이상이면 `_clarify_step`이 `clarify_node` 대신 `doc_rag_node`를 직접 호출해 클라이언트 협조 여부와 무관하게 실제 매물을 강제 제시한다. 근거 정리(스펙 Design Notes): (a) `/ai/search`의 실제 과금 방어선은 JWT 인증이고 라우트와 무관하게 이미 모든 요청에 적용되므로 CLARIFY 반복 자체가 추가 비용 취약점은 아니다 — 되묻기 상한의 진짜 목적은 비용 방어가 아니라 "질문만 반복하고 결과를 못 보여주는 막다른 루프"를 막는 UX 보장이다. (b) 그 UX 보장이 순전히 클라이언트 판단(칩 숨김)에만 맡겨져 있던 것이 CLAUDE.md B9 위반이었고, 이번 변경으로 서버가 스스로 결정한다. 잔여 한계(신규 등재하지 않고 그대로 문서화): 클라이언트가 매번 `context: []`로 위장하면 이 계산도 무력화되는데, 이는 무상태 아키텍처의 근본 한계이지 CLARIFY 특유의 결함이 아니며 진짜 세션 저장소 도입은 스토리 범위를 넘는다(13.4 Never 절). 이 잔여 gap과 "애초에 `/ai/search`에 요청 빈도 제한이 전혀 없다"는 더 넓은 사실은 DW-586으로 별도 등재한다.

### DW-564: `lexicographic_winner()`가 커버리지가 다른 두 요약의 절대 개수를 비교한다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 5(adversarial + edge-case-hunter 중복 발견) — 13.8 비교 시점의 설계 결정이라 defer
location: `api/scripts/score_ab.py`(`lexicographic_winner()` 1순위 `result_mean` · 2순위 `routing_correct` · `main()`의 2파일 모드 `regression` 계산)
severity: medium
reason: 사전식 승부는 `routing_correct`를 **절대 개수**로, `result_mean`을 **서로 다른 분모의 평균**으로 비교한다. 실측: 3/44 부분 baseline(라우팅 3/3 완벽)과 44/44 후보(라우팅 44/44 완벽)를 붙이면 "라우팅 정답 3 vs 44"로 후보가 이긴다 — 두 모델 다 완벽한데 승부가 커버리지 차이만으로 갈린다. `regression` 게이트도 같은 축에서 반대 방향으로 틀릴 수 있다. 리뷰 pass 4가 `coverage`/`is_partial`을 요약에 기록했지만 이 비교 함수는 그 값을 읽지 않는다. 정확히 DW-554(44건 전량 캡처 후 13.8이 후보와 비교)가 만드는 구도다.
trigger: Story 13.8 스펙 작성 시(또는 DW-554 전량 캡처 직후 첫 A/B 비교 직전) — 두 요약의 채점된 id 집합이 다르면 비교를 거부할지, 교집합으로 재채점할지, 비율로 비교할지를 그 스펙에서 정하고 `lexicographic_winner()`에 반영한다.
status: done 2026-08-02
resolution: **13.8 범위 밖으로 종결(모델 비교 아님, 위 DW-556과 동일 근거)**. `lexicographic_winner()`는
  후보 모델 채택 판단(2파일 모드)에서만 쓰이는데, 13.8이 실제로 실행한 `score_ab.py` 호출은
  baseline(`docs/g2-baseline.json`)과 오늘 재캡처(`docs/g2-exit-gate-2026-08-02.json`)를 함께
  넣긴 했지만 둘 다 **같은 코드 상태·같은 큐리셋 47/47 완전 커버리지**(`is_partial:false` 양쪽)라
  이 항목이 우려하는 "커버리지가 다른 두 요약의 절대 개수 비교" 왜곡이 애초에 발생할 조건이
  아니었다(실측: 두 요약이 `routing_correct=54/57`·`result_mean=0.894`로 완전 동일 — 재현성
  확인이지 커버리지가 다른 후보 비교가 아니다). 판정도 `lexicographic_winner()`의 랭킹이 아니라
  `regression_block`(단일 불리언, `candidate.result_mean < baseline.result_mean` → False)만 게이트로
  썼다. 모델 후보 비교가 실제로 생기면(커버리지가 다른 두 캡처를 비교하게 되면) 그때 다시 연다.
  ✎ 리뷰(verification-gap 렌즈)가 "요약 수치가 같다"만으로는 파일을 복사한 것과 구분 안 된다는
  의심을 실제로 검증했다 — `docs/g2-baseline.json`과 `docs/g2-exit-gate-2026-08-02.json`을
  `latency_ms` 필드만 제외하고 diff한 결과 route·id·answer·clarify 페이로드는 전부 바이트
  단위로 동일하되 `latency_ms`는 항목마다 다르게 나왔다(진짜 독립된 라이브 재실행이라는
  증거 — 값을 복사했다면 latency까지 같았을 것이다). 요약 수치의 완전 동일은 파일 재사용이
  아니라 진짜 재현성으로 확인됐다.

### DW-565: 유일한 raw 캡처 러너가 구조적으로 N=1·토큰 0이라 사전식 3·4순위(flaky·비용)가 영구 미측정이다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 5(adversarial 발견) — 측정축 확장은 13.8 범위라 defer
location: `api/scripts/run_phase_b.py`(`_run_single`/`_run_multiturn` — 1회 실행·`tokens_in`/`tokens_out` 하드코딩 0) · `api/scripts/score_ab.py`(`flaky_measured`·`tokens_measured` 도출 → 3·4순위 tier 건너뛰기)
severity: medium
reason: 리뷰 pass 4가 "미측정 축이 승부를 내지 않게" 두 tier를 건너뛰도록 고친 것 자체는 옳다. 다만 이 레포가 실제로 만들 수 있는 유일한 raw는 이 러너의 출력뿐이고 그건 항상 N=1·토큰 0이므로, 두 tier가 **영원히 실행되지 않는다** — 사전식 승부는 사실상 결과집합·라우팅·지연 3축으로 줄었고, 그중 지연은 로컬 컨테이너 기준이라 모델 선택 신호로 검증된 적이 없다. 즉 "조작된 값이 결정한다"는 문제는 "결정 근거가 없다"로 옮겨갔을 뿐이다.
trigger: Story 13.8(모델 A/B 채택 판단) 스펙 작성 시 — N>1 반복 실행과 토큰 실측을 러너에 넣을지, 아니면 두 tier를 걷어내고 사전식 기준을 명시적으로 3축으로 줄일지 결정한다.
status: done 2026-08-02
resolution: **13.8 범위 밖으로 종결(모델 비교 아님, 위 DW-556/564와 동일 근거)**. N>1 반복 실행·토큰
  실측 확장은 "사전식 3·4순위(flaky·비용)로 후보 모델을 가른다"는 전제에서만 의미가 있는데,
  13.8은 단일 코드 상태(post-13.7)의 회귀만 확인하므로 flaky·비용 축 자체가 판정에 관여하지
  않는다 — G2 게이트 정의는 `contamination==0 and deadend==0 and errored_n==0 and scored_n>0` +
  `result_mean` 비하락뿐이다(Design Notes). 오늘 재캡처도 러너를 그대로(N=1·토큰 0) 썼고
  `flaky_measured:false`·`tokens_measured:false`로 정직하게 남았다(미측정이지 "흔들림 없음"이
  아님 — DW-554 resolution과 동일 주의). 모델 후보 비교가 실제로 생기면 그때 N>1·토큰 실측
  확장을 결정한다.

### DW-566: 러너 테스트가 `RUN_LIVE_SMOKE=1`을 켠 채 돌아, 쿼터 보호가 모킹 대상 1곳에만 의존한다

origin: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md` 리뷰 pass 5(adversarial 발견) — 게이트 자체는 동작하므로 defer
location: `api/tests/test_run_phase_b.py`(`monkeypatch.setenv("RUN_LIVE_SMOKE", "1")`을 쓰는 테스트들) · `api/scripts/run_phase_b.py`(게이트) · `api/app/graph/graph.py`(import 시점에 `COMPILED_GRAPH = _build_graph()`)
severity: medium
reason: 러너의 쿼터 보호는 스토리 Boundaries의 "Always" 조항인데, 그 게이트를 켜고 도는 테스트들이 **오직 `app.graph.graph.run_search` 몽키패치 하나**로 실제 호출을 막는다. "LLM 클라이언트가 만들어지지 않았다"·"소켓이 안 열렸다"를 단언하는 검사는 없다. 앞으로 라이브 호출 지점이 하나 더 생기거나(임베딩 워밍업·모델 프로브) import 위치가 바뀌면, CI가 매 push마다 실제 Gemini 쿼터를 태우면서도 전량 green일 수 있다. B9("규칙은 어길 수 없는 자리에 박는다") 기준으로 지금은 규칙이 관례에 얹혀 있다.
trigger: ~~DW-554(44건 전량 라이브 캡처) 실행 직전~~, 또는 러너에 라이브 호출 지점이 하나라도 추가될 때 — 테스트에서 실제 LLM 클라이언트 생성 자체가 실패하도록(예: 클라이언트 팩토리를 raise하도록 패치) 이중으로 못박는다.
  ✎ 2026-07-30 **트리거 재지정**: 첫 번째 조건이 소진됐다 — DW-554의 44건 전량 캡처를 오늘 실행했고,
  이 하드닝은 **하지 않았다**(사람이 의도적으로 1회 돌린 것이라 테스트 게이트와 경로가 다르고,
  승인받은 작업 범위 밖이었다). 트리거를 안 옮기면 이 항목은 발동 조건이 없는 채로 조용히 남는다(B8).
  → 새 자리: **Story 13.8(RAG exit gate) 착수 시점** — 거기서 같은 러너로 재캡처하므로 그 전에 못박는다.
    그때까지도 두 번째 조건(라이브 호출 지점 추가)은 그대로 유효하다.
status: open

### DW-567: Follow-up review still recommended for 13-1-sql-guard-하이브리드-정비-g2-baseline after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-1-sql-guard-하이브리드-정비-g2-baseline.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260730-153003-855d; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-568: bmad-loop의 실패-시도 보존(attempt-preserve)이 **한글 파일명에서 항상 실패**한다 — 이 리포에선 안전망이 사실상 꺼져 있다

origin: Epic 13 런 `20260730-153003-855d` 운영 중 실측(13-1 dev-1 타임아웃 시점)
location: bmad-loop 엔진 `engine.py`의 `_preserve_attempt_worktree`(상류 도구) · 영향 대상은 `_bmad-output/implementation-artifacts/spec-*.md` 전부(전 스토리 스펙이 한글 이름)
severity: medium
reason: 루프는 실패한 dev/review 시도를 버리기 전에 `attempt-preserve/*` 브랜치로 백업하는데, 2026-07-30 17:00 13-1 dev-1이 타임아웃됐을 때 그 백업이 실패했다. 저널 원문:
  `git add (snapshot untracked) failed ... fatal: pathspec '"_bmad-output/implementation-artifacts/spec-13-1-sql-guard-\355\225\230\354\235\264..."' did not match any files`
  git이 비ASCII 경로를 `core.quotepath` 규칙으로 이스케이프해 출력하는데, 엔진이 그 **출력 문자열을 그대로 다시 `git add`에 넘겨** 매칭에 실패한다. 결과: dev-1의 90분치 작업(8파일 수정, weighted 6.15M)이 보존 없이 롤백됐다. **이 리포의 스토리 스펙은 전부 한글 이름**이라 앞으로 어떤 스토리가 실패하든 같은 자리에서 같은 이유로 실패한다 — 즉 Epic 12에서 12-2를 살렸던 그 안전망(사용자가 A-1로 채택한 보존본)이 이 리포에선 작동하지 않는다.
  **원리적 한계가 아니라 구현 문제임을 실측으로 확인했다**: 같은 시점에 사람이 `git ls-files --others -z | tar --null -T -`로 같은 한글 파일을 문제없이 보관했다(`backup/13-1-dev2-tracked` 브랜치 + 스크래치패드 사본).
trigger: 다음에 dev/review 세션이 실패해 보존이 필요해지는 시점 — 그 전까지는 실패 직전에 사람이 수동 백업한다(위 tar 방식). 상류(bmad-loop)에 보고하고, 고쳐지기 전까지는 이 항목을 닫지 않는다. bmad-loop 업그레이드 시 재확인.
status: open

### DW-569: 리뷰 서브에이전트가 `ReportFindings`로 보고한 발견이 **부모 세션에 전달되지 않아** 조용히 유실될 수 있다

origin: Epic 13 런 `20260730-153003-855d` 13-1 dev-1 세션 기록 분석(2026-07-30)
location: `.claude/skills/bmad-dev-auto/step-04-review.md`(리뷰 레이어 서브에이전트 호출부) · 리뷰 레이어가 쓰는 `ReportFindings` 도구
severity: medium
reason: dev-1 세션 40.8분 지점에서 adversarial 리뷰 레이어가 결함 **10건**을 찾았는데 부모 세션에는 **4건만 산문 요약**으로 도달했고 나머지 6건은 한 구절씩만 언급됐다. 부모가 이렇게 되물어 복구했다(원문):
  *"I only received a summary describing 4 of the 10 findings in prose ... I cannot see your ReportFindings tool call output directly, only your final text message."*
  즉 리뷰 레이어는 전용 도구로 보고하는데 **부모는 그 도구 출력을 볼 수 없고 최종 텍스트만** 받는다. 이번엔 부모가 개수 불일치를 눈치채 되물었지만, **눈치채지 못하면 발견 6건이 아무 흔적 없이 사라진다** — 리뷰를 여러 레이어로 병렬 실행하는 설계의 값이 통째로 새는 자리다.
trigger: 다음 리뷰 사이클에서 대조로 확인한다 — 리뷰 세션 로그의 "N건 찾았다"와 스펙 `## Review Triage Log`에 실제 등재된 건수를 세어 맞는지 본다(추측 말고 실측). 어긋나면 서브에이전트 프롬프트에 "발견 전량을 최종 텍스트로도 평문 나열하라"를 명시한다.
status: open

### DW-570: 리뷰 세션엔 **유휴 감지가 없어**, API 오류로 죽은 세션을 루프가 타임아웃까지 방치한다

origin: Epic 13 런 `20260730-153003-855d` 13-1 review-1 실측(2026-07-30) — 사용자가 화면을 보고 발견
location: bmad-loop 엔진 `adapters/generic.py`의 `wait_for_completion`(상류 도구) · `.bmad-loop/policy.toml`의 `dev_stall_grace_s`·`dev_stall_nudges`
severity: medium
reason: 2026-07-30 18:04:27 시작한 13-1 review-1이 Anthropic 측 장애(`529 Overloaded`, 상태 페이지에 공식 등재된 진행 중 장애)로 10회 재시도 후 전부 실패하고 **입력 대기 상태로 멈췄다**. 세션 화면은 `0/1.0M 토큰 · $0.00 · 0/min` — 성공한 호출이 0건이었다. 그런데 엔진은 세션 종료를 ①Stop 훅 이벤트 ②창(window) 소멸 **두 가지로만** 판정하는데, 이 세션은 창이 살아 있고 Stop도 안 보냈으므로 "작업 중"으로 보였다. 유휴 감지(`stall_deadline`/wake-nudge)는 소스 주석에 **`dev adapter only`로 명시**돼 리뷰 세션엔 적용되지 않는다.
  결과: 18:34:30에 로그가 멈춘 뒤 **52분간 아무 일도 하지 않았고**, 사람이 화면을 보고 tmux로 프롬프트를 다시 넣지 않았다면 `session_timeout_min`(150분)을 꽉 채운 20:34까지 방치됐을 것이다. 게다가 타임아웃된 세션도 **리뷰 사이클 1회를 소모**하므로(Epic 11의 11-1과 같은 패턴, 구 `#182` 계열), 상한 2회 중 1회가 아무 일도 없이 사라졌을 상황이었다.
  ⚠️ **재발 가능성이 높다**: 해당 장애는 이 항목을 쓰는 시점에도 "조사 중"으로 열려 있다.
trigger: Epic 13 남은 스토리 실행 중 세션이 또 API 오류로 죽을 때 — 그때 (a)사람이 즉시 깨우거나 (b)`bmad-loop status` 감시에 "로그 파일이 N분간 안 자란다" 조건을 넣어 자동 경보한다. 상류(bmad-loop)에 리뷰 세션에도 유휴 감지를 달아달라고 보고한다. Epic 13 회고 확인 항목.
status: open

### DW-571: G2 큐리셋 44개 중 HYBRID 정답 라벨이 없어 HYBRID 분류 정확도를 채점할 수 없다

origin: `spec-13-2-4분기-라우팅.md` Tasks(13.2가 스펙 자체에서 등재를 요구) — HYBRID 신설이 만든 커버리지 공백
location: `api/docs/ai-ab-test-queryset.json`(44개 질의·golden 값 — 13.2는 이 파일을 수정하지 않는다) · `api/scripts/score_ab.py`(`score_model()` — `primary_path`가 HYBRID인 item을 다루는 채점 분기가 없다)
severity: medium
reason: 13.2가 FR43 ④(조합형)를 위해 HYBRID 라우트를 신설했지만, 44개 큐리셋 중 구조 조건과 의미/느낌 조건이 함께 있는 질의(예: "3천만원 이하로 무난한 패밀리카")는 하나도 없다(Design Notes 확인) — 그래서 HYBRID는 골든 예시 없이 신설됐다. `score_model()`의 `if primary == "A": ... elif primary == "B": ... elif primary == "C": ...` 분기에도 HYBRID(신버전 그대로 등장할 primary_path는 아직 없지만, 향후 큐리셋에 HYBRID 예시가 추가되면) 대응 분기가 없어 결과집합 채점(score_path_a류)이 비어 있는 상태로 남는다. routing_correct(라우팅 정확도)만 `route_ok()` 번역으로 채점되고, HYBRID의 "결과가 실제로 맞았는가"는 어떤 지표로도 측정되지 않는다.
trigger: Story 13.3 스펙 작성 시(하이브리드 질의 예시를 큐리셋에 추가하거나 별도 검증 방법을 정한다) — 13.3이 HYBRID의 실제 벡터+SQL 결합 실행을 구현하면서, 큐리셋에 HYBRID `primary_path` 예시(구조+의미 조합 질의, golden predicate)를 추가하고 `score_model()`에 HYBRID 결과집합 채점 분기를 추가할지, 아니면 별도 검증 방법(예: 수동 스모크만)으로 대신할지 그 스펙에서 정한다.
status: done 2026-07-31
resolution: Story 13.3은 (b) 별도 검증 방법을 택했다 — 큐리셋에 HYBRID golden 예시를 신규로 추가하지 않는다(13.2 Never 절 큐리셋 수정 금지 승계 + `_require_legacy_paths`의 전량-마이그레이션 강제를 피하기 위해). 대신 결과집합 자동채점 대신 라이브 스모크(`test_live_smoke_hybrid` + 대표 조합형 질의 5건 수동 실행, DW-555 resolution 참조)로 HYBRID 동작을 직접 확인했다. `score_model()`에 HYBRID 결과집합 채점 분기는 추가하지 않는다(이 결정으로 DW-571을 닫는다 — 결과집합 자동채점 공백은 남지만, 그 공백을 메우지 않기로 명시 결정했다는 점이 다르다).

### DW-572: 큐리셋의 구버전 `A` 라벨이 **올바른 HYBRID 분류를 오답으로 집계**한다 — DW-571의 전제("조합형 질의가 하나도 없다")는 사실과 다르다

origin: `spec-13-2-4분기-라우팅.md` review-4(팔로업 리뷰) — blind-hunter·edge-case-hunter·verification-gap·intent-alignment 4개 레이어가 독립 발견, 오케스트레이터가 큐리셋 전량 파싱으로 재확인
location: `api/docs/ai-ab-test-queryset.json`(항목 A5·G3·G5·G6, 멀티턴 M4/M5의 일부 턴) · `api/scripts/score_ab.py`(`_LEGACY_ROUTE_ALIASES`의 `A→SQL` 1:1 매핑)
severity: medium
reason: 13.2가 구 `A`(구조형)를 `SQL`과 `HYBRID` 둘로 쪼갰는데, 어휘 번역표는 `A→SQL` 1:1이다. 그래서 라우터가 **정확히 맞게** HYBRID로 분류해도 번역된 허용집합(`{SQL}` 또는 `{SQL, CLARIFY}`)에 HYBRID가 없어 라우팅 오답으로 집계된다(실측: `route_ok("HYBRID","A",["A"])=False`, `route_ok("HYBRID","A",["A","B"])=False`). 그리고 DW-571이 근거로 적은 "44개 중 구조+의미 조합형 질의는 하나도 없다"는 **실측으로 거짓**이다 — 큐리셋을 전량 파싱하면 A5 `1500만원 이하 가성비 좋은 차 있어?`(primary=A, acceptable=[A]), G3 `가족이랑 타기 좋은 7인승 차 보여줘`([A,B]), G5 `연비 좋은 차 중에 2천만원 이하로 보여줘`([A,B]), G6 `초보가 몰기 쉬운 작은 차 2천 이하면 좋겠어`([A,B]) 등 최소 4건이 "구조 조건 + 용도·느낌 조건"을 함께 갖고 있고, 새 프롬프트의 최우선 규칙("둘 다 있으면 HYBRID")을 그대로 따르면 이들은 HYBRID로 간다. 즉 다음 G2 전량 캡처 때 회귀가 아닌데 최소 4~6건이 라우팅 오답으로 깎인다. 따라서 필요한 일은 DW-571이 적은 "예시 추가"가 아니라 **기존 A 라벨의 재판정**이다(이 항목은 DW-571을 대체하지 않고 그 전제를 정정한다 — DW-571의 "HYBRID 결과집합 채점 분기 부재"는 그대로 유효하다).
trigger: Story 13.3 스펙 작성 시 — DW-571과 같은 자리에서 함께 결정한다. 선택지는 (a) `A`를 `{SQL, HYBRID}` 집합으로 번역해 허용집합을 넓히거나, (b) 해당 항목들의 `primary_path`를 신어휘로 재라벨링(13.2의 Never 절 "큐리셋 데이터 수정 금지"와 충돌하므로 스펙 수준 결정 필요)하거나, (c) 오답 집계를 그대로 두되 리포트에 "재배정으로 인한 오답 N건"을 분리 표기. 어느 쪽이든 44개 전량 재캡처(DW-554) 전에 정해야 그 캡처의 라우팅 점수가 해석 가능하다.
status: done 2026-07-31
resolution: (a)안 채택 — `api/scripts/score_ab.py`에 `route_ok()` 전용 집합 번역 `_LEGACY_ROUTE_ALIASES_SET = {"A": {"SQL", "HYBRID"}, "B": {"CLARIFY"}, "C": {"REJECT"}}`를 신설하고 `route_ok()`가 `primary`/`acceptable`의 각 값을 이 집합으로 번역해 합집합과 `actual`을 비교하도록 교체했다(`captured_route`/`_require_legacy_paths`가 쓰는 1:1 `_LEGACY_ROUTE_ALIASES`는 손대지 않았다). red→green 실측(B4): 수정 전 `route_ok("HYBRID","A",["A"])`는 False(코드리뷰 재현), 수정 후 True. `route_ok("CLARIFY","A",["A"])`는 여전히 False임도 함께 확인해 집합 번역이 다른 카테고리까지 느슨해지지 않았음을 못박았다(`api/tests/test_ab_scoring.py`의 `test_route_ok_legacy_a_accepts_both_sql_and_hybrid`·`test_route_ok_legacy_b_and_c_unaffected_by_set_translation`). 알려진 트레이드오프(Design Notes): 이 확장은 legacy `A` 44개 중 구조전용 항목의 HYBRID 오분류도 함께 허용한다 — 큐리셋을 안 건드리는 쪽을 우선한 결정이다.

### DW-573: `api/tests/demo_queries.py`가 여전히 구버전 `A/B/AB/C` 어휘 — 문서는 이 파일을 "기대 경로 단일출처"로 가리킨다

origin: `spec-13-2-4분기-라우팅.md` review-4 — verification-gap·intent-alignment 독립 발견, 오케스트레이터가 grep으로 소비처 확인
location: `api/tests/demo_queries.py`(`DEMO_QUERIES` 상수 및 모듈 docstring의 경로 표기) · 이 파일을 정본으로 가리키는 `docs/learning/06-file-reference.md` · `api/docs/ai-demo-queries.md`
severity: low
reason: 13.2가 라우트 어휘를 SQL/HYBRID/CLARIFY/REJECT로 바꿨지만 이 파일은 손대지 않았다. `test_demo_acceptance.py`는 이 파일에서 질의 **리스트만** import하고 라벨은 자기가 신어휘로 주입하므로 지금 깨지지는 않는다. 문제는 `DEMO_QUERIES`(질의와 `"A"/"B"/"AB"/"C"` 라벨의 쌍)가 리포 어디에서도 import되지 않는 **죽은 상수**라 어긋남이 드러나지 않는데, 위 문서 2곳이 이 파일을 "다른 테스트가 참조하는 기대 경로 단일출처"라고 가리킨다는 점이다 — 다음 담당자가 구어휘를 정본으로 읽을 수 있다. 특히 회색지대 라벨 `"AB"`가 가리키는 3개 질의(`출퇴근용 적당한 차`·`괜찮은 SUV 있어?`·`너무 비싸지 않은 중형차`)는 새 taxonomy에서 HYBRID 후보다.
trigger: `api/docs/ai-demo-queries.md`를 손대는 다음 작업 시(그 문서가 아직 "경로 A/B/C" 표기를 쓰고 있어 어차피 같이 고쳐야 한다) — 또는 `DEMO_QUERIES`에 소비처가 처음 생길 때. 고칠 방향은 신어휘로 옮기거나, 소비처가 계속 0이면 상수를 지우고 문서의 "단일출처" 표현을 정정하는 것.
status: open

### DW-574: `sql_guard`의 `status='on_sale'` 구조 검사는 **단일 형상 화이트리스트**다 — "새 변형도 원리상 막힌다"는 주장보다 좁고, 동치의 안전 표현도 함께 거부한다

origin: `spec-13-2-4분기-라우팅.md` review-4 — blind-hunter·edge-case-hunter 독립 발견, 오케스트레이터가 27개 SQL 형태를 직접 넣어 재확인
location: `api/app/db/sql_guard.py`(`_conjunct_is_bare_status_on_sale`) · `api/tests/test_sql_guard.py`(DW-557 블록 주석) · `deferred-work.md`의 DW-557 resolution 문구
severity: low
reason: 이 검사는 "좌변=status 식별자, 연산자 `=`, 우변=`'on_sale'` 문자열"이라는 **정확히 하나의 토큰 형상**만 통과시킨다. 부정 우회를 막는 데는 확실히 성공했지만(실측: 알려진 우회 16형태 전부 거부, review-4가 새로 고안한 괄호+부정 조합 5형태도 전부 거부), 그 대가로 의미상 동치인 안전한 표현도 함께 거부된다 — 실측 거부: `WHERE 'on_sale' = status`(좌우 반전), `WHERE status = ('on_sale')`(우변 괄호), `WHERE status IN ('on_sale')`. 셋 다 베이스라인에서도 거부됐으므로 회귀는 아니지만, DW-557 resolution과 테스트 주석이 "표현 형태가 아니라 구조를 보므로 아직 실측되지 않은 새 변형도 원리상 함께 막힌다"고 적은 것은 **차단 방향에서만 참이고 통과 방향에서는 과장**이다(B4 "재보기 전엔 선언하지 않는다"). 또 `WHERE status = 'ON_SALE'`은 통과하는데(우변을 소문자화해 비교) PostgreSQL 문자열 비교는 대소문자를 구분하므로 이 쿼리는 항상 0행이다 — 누출은 아니지만(안전 방향) 가드는 "FR11 충족"이라고 판정한다. 지금 이걸 엄격하게 바꾸면 0행 안내가 400 오류로 바뀌어 사용자 경험이 오히려 나빠지므로 이번엔 손대지 않았다.
trigger: 13.3에서 하이브리드 벡터+SQL 결합으로 **SQL 표면이 넓어질 때** — 그때 LLM이 내는 SQL 형태가 다양해지므로, (a) 위 동치 표현 중 실제로 나오는 것이 있는지 먼저 측정하고, (b) 검사 옆에 "이 검사가 통과시키지 않는 안전 표현" 목록을 실측해 적고(추측 금지), (c) DW-557 resolution의 과장된 문구를 그때 정정한다.
status: open
✎ 2026-07-31 Story 13.3 실측 갱신(코드 변경 없음, open 유지): 트리거대로 SQL 표면이 넓어졌다
  (`hybrid_rag_node`가 LLM에게 WHERE 구조조건 표현식을 자유 형태로 생성시킨다). 로컬
  Supabase+GEMINI_API_KEY로 대표 조합형 질의 5건을 직접 실행해 관찰한 실제 LLM 산출 조건은
  `NONE`(2건, doc_rag_node 폴백)·`seats = 7`·`body_type IN ('경차', '소형차') AND price <=
  20000000`·`fuel = '전기'`였다 — 전부 `status`를 언급하지 않았다.
  (✎ 후속 리뷰에서 프롬프트를 고친 뒤 5건 재측정: `price <= 30000000`·`price <= 20000000
  AND body_type = 'SUV'`·`fuel = '전기' AND price <= 30000000`·`mileage <= 50000`·`NONE`
  1건 — 역시 `status` 언급 0건. 표본이 5→10건으로 늘었을 뿐 아래 결론은 그대로다.)
  ✎✎ 2026-07-31 후속 리뷰 정정: 이 자리에 원래 "`status`는 이 표면에 노출되지 않는다 —
  구조가 원천적으로 막는다(LLM이 만드는 조건은 SELECT 목록 안의 AND 결합항일 뿐, status
  비교식 자체를 생성할 위치가 없다)"고 적혀 있었는데 **틀렸다.** LLM이 낸 조건은 SELECT
  목록이 아니라 **WHERE절**에 `AND (<조건>)`으로 그대로 이어붙는다 — status 비교식을
  생성할 위치가 정확히 거기 있다. 실측(후속 리뷰에서 실제 `validate_select_sql()` 호출):
  조건이 `status = 'ON_SALE'`이면 조립 SQL이 **가드를 통과**한다(코드가 붙이는 bare
  `status = 'on_sale'` 결합항이 이미 FR11 검사를 충족시키므로 추가 status 술어가 얹혀
  간다). PostgreSQL 문자열 비교는 대소문자를 구분하니 그 쿼리는 항상 0행인데 가드는
  "FR11 충족"이라고 판정한다 — 이 항목이 원래 지적한 바로 그 형태다. 즉 이를 막는 것은
  구조가 아니라 **프롬프트 문장 하나**(`_HYBRID_INSTRUCTIONS` 규칙 3)뿐이며, 그건 실행되는
  검사가 아니다(CLAUDE.md B9). 위 5건 관측은 "Gemini가 마침 규칙을 지켰다"는 **표본**이지
  구조적 차단의 증거가 아니다(B4 "재보기 전엔 선언하지 않는다" — 같은 실수를 이 항목 자신이
  반복했다). 따라서 이 항목이 요구한 (a) 측정은 "13.3 경로 5건 표본에서 관측된 동치 표현
  0건, 단 구조적 차단은 없음"으로만 완료했고,
  (b)(검사 옆 안전 표현 목록)·(c)(DW-557 resolution 과장 문구 정정)는 손대지 않는다 —
  둘 다 코드 변경이 아니라 **문서 갱신**인데, 이 항목의 본래 우려(경로 A/sql_rag_node가
  LLM에게 status를 직접 쓰게 하는 구조)는 13.3 범위 밖이라 여전히 유효하며, 그쪽 경로는
  이번 스토리로 아무것도 바뀌지 않았다. status는 open으로 유지한다.

### DW-575: `A→SQL` 1:1 번역이 만드는 라우팅 오답 4~6건이 **A/B 모델 승자 판정을 뒤집을 수 있다**(임계값이 5)

origin: `spec-13-2-4분기-라우팅.md` review-5 — edge-case-hunter 발견, 오케스트레이터가 큐리셋·`lexicographic_winner` 임계값을 직접 대조
location: `api/scripts/score_ab.py`(`_LEGACY_ROUTE_ALIASES`의 `A→SQL` · `ROUTING_DELTA` · `lexicographic_winner()`)
severity: medium
reason: DW-572는 "구 `A` 라벨이 올바른 HYBRID 분류를 오답으로 집계한다 → 라우팅 점수를 해석할 수 없다"까지만 적었다. 그 뒤가 남아 있다 — `routing_correct`는 `lexicographic_winner()`의 2순위 기준이고 그 임계값 `ROUTING_DELTA`가 **5**다. DW-572가 센 오답이 최소 4~6건이므로, 이 허수 격차가 임계값 바로 위/아래에 앉는다. 즉 두 모델을 비교할 때 **회귀가 아닌 어휘 분할 때문에 승자가 뒤집히고**, 리포트에는 "라우팅 정답 N vs M"이라는 정상적으로 보이는 사유가 찍힌다(`gate_pass`는 오염·dead-end·에러만 보므로 여기서 아무것도 못 걸러준다). 실측 확인: `route_ok("HYBRID","A",["A"])=False`, `route_ok("HYBRID","A",["A","B"])=False` — 라우터가 맞게 분류할수록 점수가 깎인다.
trigger: DW-572와 **같은 자리에서 함께 결정한다**(Story 13.3 스펙 작성 시) — 어휘 재판정 방식을 고르는 그 결정이 이 문제도 같이 닫는다. 만약 (c)안(오답을 그대로 두고 리포트에 분리 표기)을 택한다면, 그 분리된 건수를 `lexicographic_winner()`의 라우팅 비교에서 **빼고** 계산하도록 함께 고쳐야 이 항목이 닫힌다.
status: done 2026-07-31
resolution: DW-572와 같은 수정(route_ok의 `A→{SQL,HYBRID}` 집합 번역)이 이 문제도 함께 닫는다 — 허수 오답 4~6건 자체가 더는 발생하지 않으므로 `ROUTING_DELTA` 임계값 부근에서 승자가 뒤집힐 여지가 사라진다. `lexicographic_winner()`는 손대지 않았다(분리 표기 방식이 아니라 오답 자체를 없애는 방식을 택했으므로 그 함수를 고칠 필요가 없다).

### DW-576: 데모 인수 게이트의 ② 목록이 실측 분류와 어긋난다 — `연비 좋은 전기차 추천`은 CLARIFY가 아니라 HYBRID다

origin: `spec-13-2-4분기-라우팅.md` review-5 — blind-hunter 발견, 오케스트레이터가 로컬 라이브 LLM으로 ②·③ 목록 7개 질의를 전부 재분류해 확인
location: `api/tests/demo_queries.py`(`SEMANTIC_B` 목록) · `api/tests/test_demo_acceptance.py`(`test_sm3_pathB_returns_listings`) · `api/docs/ai-demo-queries.md`(표 ②)
severity: medium
reason: 13.2의 새 프롬프트는 "명시 조건 + 용도·느낌 조건이 둘 다면 HYBRID(최우선)"인데, ② 목록의 `연비 좋은 전기차 추천`은 전기차(=연료, 명시 조건) + `연비 좋은`(느낌)이라 이 규칙대로 HYBRID로 간다. 실측(라이브 LLM): ② 4개 중 `연비 좋은 전기차 추천`만 **HYBRID**, 나머지 3개는 CLARIFY. ③ 회색지대 3개 중 `너무 비싸지 않은 중형차`도 **HYBRID**. 그런데 `test_sm3_pathB_returns_listings`는 `_patch_route(monkeypatch, "CLARIFY")`로 route를 **강제 주입**하므로, 라우터가 실제로 그 질의를 어디로 보내든 게이트는 초록이다 — 즉 SM3(데모 인수)가 이 질의에 대해 아무것도 보장하지 않는다. DW-573은 같은 파일의 "구어휘·죽은 상수·문서가 정본으로 가리킴"을 다루지만, **② 목록 자체의 소속이 실측과 다르다**는 이 사실은 그 항목에 없다.
trigger: DW-573을 손대는 같은 작업에서 함께(`api/docs/ai-demo-queries.md`를 신어휘로 옮길 때) — 그때 ②·③ 목록을 실측 분류로 재배치하고, `test_sm3_pathB_returns_listings`가 route를 강제 주입하는 대신 목록별 기대 route를 받도록 바꿀지 정한다. 데모 시연 전이라면 그 전에 한다(데모 당일 이 질의가 문서와 다른 경로를 탄다).
status: open (부분 해소, 2026-08-02)
✎ 2026-08-02 부분 해소(story 13-8, intent-alignment 리뷰가 발견) — ①②④ 목록을 4분기 어휘로 옮기는 작업(13.8)에서 ②·③의 구체적 질의를 실제로 교체했다: ②에서 `연비 좋은 전기차 추천`(이 항목이 지적한 오분류 질의)을 빼고 `출퇴근하기 편한 차`로, ③ 회색지대 3개도 전부 새 질의로 교체했다 — 이 항목이 근거로 든 구체 질의는 더 이상 파일에 없으므로 그 부분의 실측 증거는 낡았다. 다만 **핵심 결함(route 강제 주입)은 그대로 남는다** — `_patch_route(monkeypatch, route)`는 여전히 라우터를 우회하므로, 새 목록도 실제 분류와 다시 어긋날 수 있고 SM3는 그걸 못 잡는다. 남은 범위를 좁힌다: "②·③ 목록이 실측과 맞는가"는 매번 문서를 고칠 때 수동 확인해야 하고, "SM3가 실제 라우팅을 검증하지 않는다"는 구조적 문제로 남는다.
trigger(갱신): SM3 판정을 라이브 라우터 결과 기반으로 바꿀지(비용·결정론성 트레이드오프 발생) 결정하는 스토리에서 — 그 전까지는 문서·목록을 고칠 때마다 실측 재분류를 수동으로 병행한다.

### DW-577: 라이브 스모크 파일이 `route`를 단언하지 않고 HYBRID 질의도 없어, 4갈래 회귀를 재실행 가능한 형태로 잡지 못한다

origin: `spec-13-2-4분기-라우팅.md` review-5 — blind-hunter·intent-alignment 독립 지적, 오케스트레이터가 파일 내용으로 확인
location: `api/tests/test_live_smoke.py`(경로 A/B/C 3건, `out["route"]` 단언 0건, "HYBRID" 등장 0회)
severity: low
reason: 13.2의 Block If 게이트(G1 — 명시조건 질의가 CLARIFY로 새면 HALT)와 4갈래 관측은 **오케스트레이터가 손으로 5~6개 질의를 돌려** 충족했고, 그 결과는 스펙 산문에만 남았다. 리포의 라이브 스모크 파일은 `answer`가 비지 않았는지와 `listings`가 리스트인지만 보고 `route`는 아예 안 본다 — CLARIFY도 매물을 돌려주므로 G1 위반이 일어나도 이 파일은 `RUN_LIVE_SMOKE=1`로 켜도 초록이다. 즉 다음 사람이 같은 게이트를 다시 확인하려면 이번처럼 손으로 다시 짜야 한다. (프롬프트 표류 자체는 review-4·5가 넣은 프롬프트 잠금 테스트가 CI에서 막지만, 그건 "문자열이 남아 있는가"이지 "LLM이 실제로 그렇게 가르는가"는 아니다 — project-context §12가 실제 LLM 품질을 eval/live-smoke 트랙으로 분리한 그 자리다.)
trigger: Story 13.3에서 HYBRID의 실제 벡터+SQL 결합을 구현할 때 — 그 스토리는 HYBRID가 **다른 노드**를 타게 만들므로 배선 회귀를 잡을 라이브 근거가 필요하다. 그때 `test_live_smoke.py`에 4갈래 각 1건씩 `out["route"]` 단언을 추가한다(HYBRID 질의 포함).
status: open

### DW-578: Follow-up review still recommended for 13-2-4분기-라우팅 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-2-4분기-라우팅.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260730-205944-48e1; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-579: `assert last_error is not None`이 SQL/HYBRID 노드의 재시도 루프 종료를 제어 흐름으로 방어한다 — `-O` 최적화 실행 시 사라지는 방어
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
summary: `sql_rag_node.py`(사전 존재)와 이번 스토리가 같은 패턴으로 새로 만든 `hybrid_rag_node.py` 둘 다, 재시도 루프가 두 번 다 돌고도 return을 못 했을 때 `last_error`가 항상 설정돼 있다는 보장을 `assert`문으로만 지킨다 — 코드를 눈으로 추적하면 성립하지만, Python을 `-O`로 실행하면 이 assert가 통째로 사라져 방어가 없어진다.
evidence: blind-hunter 리뷰(story 13.3)가 두 파일 모두에서 이 패턴을 발견. 지금은 두 곳 다 루프 구조상 `last_error`가 항상 설정된 채로 이 줄에 도달하지만, 나중에 이 루프에 손대는 사람이 실수로 미설정 경로를 만들면 `-O` 실행 환경에서는 조용히 `None`을 반환하고 호출부가 엉뚱한 위치(`SqlGuardError` 대신 `TypeError` 등)에서 죽는다(CLAUDE.md B9 "규칙은 어길 수 없는 자리에 박는다" 위반 소지 — 실행되는 검사가 아니라 주석/관례로만 지켜지는 불변식).
severity: low
trigger: `sql_rag_node`·`hybrid_rag_node`의 재시도 루프를 다음에 다시 손댈 때(재시도 횟수 변경·예외 종류 추가 등) — 그때 `assert`를 명시적 `raise RuntimeError`로 바꾼다. 그 전이라도 배포 실행 커맨드에 `python -O`가 들어오면 즉시 처리한다.
status: open
✎ 2026-07-31 후속 리뷰: 등재 당시 이 프로젝트의 필수 필드인 `severity:`·`trigger:`가 빠져 있었다(CLAUDE.md B8 — "미룬 항목엔 언제·어디서 고칠지를 대장에 함께 적는다"). 항목을 만든 스토리(13.3)의 후속 리뷰에서 두 줄만 보강했다. 상태·resolution은 손대지 않았다.

### DW-580: 하드 오염 게이트가 route 라벨로 판정해, HYBRID가 `doc_rag_node`로 폴백한 턴까지 오염으로 집계한다
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
location: `api/scripts/score_ab.py`(멀티턴 하드 오염 게이트, `captured_route(tr["route"]) in ("SQL","HYBRID")`)
severity: medium
summary: 13.3이 HYBRID를 전용 `hybrid_rag_node`로 재배선하면서 "route=HYBRID면 구조조건이 붙은 SQL이 돌았다"는 게이트의 전제가 깨졌다 — 구조조건을 못 뽑아 `doc_rag_node`로 폴백한 턴은 조건이 하나도 안 붙은 순수 벡터검색인데 route 라벨은 그대로 HYBRID라, 게이트가 그 결과를 하드 오염으로 센다.
evidence: 게이트 바로 위 주석이 "CLARIFY/REJECT에서 같은 차종이 결과에 떠도 그건 의미검색의 우연이지 조건 잔존이 아니다"라고 명시하는데, 폴백 턴은 실행 실체가 정확히 그 CLARIFY/REJECT 케이스(doc_rag_node 벡터검색)와 같다. `contamination > 0` → `gate_pass=False` → `lexicographic_winner`의 `gate` 티어에서 자동 패배. 후속 리뷰 blind-hunter 발견, 오케스트레이터가 `score_ab.py` 해당 분기를 직접 읽어 확인. 13.3에서 코드를 고치지 않은 이유: 스토리 intent가 `score_ab.py` 변경을 `route_ok()`로 한정했다. 대신 게이트 옆 주석에 이 사실을 기록해 뒀다.
trigger: 다음 G2 A/B 캡처를 돌리기 전(멀티턴 HYBRID 턴이 포함된 큐리셋으로 실제 채점할 때) — 그때 게이트 판정 기준을 route 라벨이 아니라 "구조조건이 실제로 적용됐는가"로 바꾸거나, 폴백 턴을 별도로 표시해 제외한다.
status: open

### DW-581: legacy `A` 항목이 HYBRID로 라우팅되면 구조 golden으로 결과채점돼 `result_mean`(1순위 지표)이 조용히 깎인다
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
location: `api/scripts/score_ab.py`(`score_model`의 `if primary == "A": score_path_a(...)` 분기 · `lexicographic_winner` 1순위 `result_mean`)
severity: medium
summary: `route_ok()`는 legacy `A`를 `{SQL,HYBRID}`로 넓혀 라우팅 오답 신호를 없앴지만(DW-572/575), 결과채점 분기는 여전히 **legacy 라벨**만 보고 `score_path_a`를 태운다 — route와 무관하다. 그래서 legacy `A` 항목이 HYBRID로 가면 임베딩 순서로 나온 결과가 구조 golden과 비교된다.
evidence: 큐리셋의 A7(`제일 싼 차 뭐야?`)·A8(`가장 비싼 매물 하나 보여줘`)는 `predicate.order`+`predicate.limit`을 가져 `score_path_a`가 `mode="topn"`(순서까지 정확일치)로 채점한다. `hybrid_rag_node`는 `ORDER BY embedding <=> %s::vector`로만 정렬하고 LIMIT을 5로 고정하므로(스펙이 명시 선택) 이 두 항목은 결정론적으로 0.0이 된다. `result_mean`은 `lexicographic_winner`가 라우팅보다 **먼저** 보는 1순위 지표라, 승자가 뒤집혀도 원인을 지목하는 지표가 어디에도 없다. DW-575가 닫으려던 "임계값 근처에서 승자가 뒤집힌다"는 위험이 ②(라우팅)에서 ①(결과)로 옮겨간 것. 후속 리뷰 blind-hunter·verification-gap 독립 발견, 오케스트레이터가 `score_ab.py:440-456`을 직접 읽어 확인.
trigger: 다음 G2 44문항 캡처를 돌릴 때 — 그때 (a) HYBRID로 간 legacy `A` 항목을 `result_scores_clean_A`에서 분리 집계하거나, (b) 그 항목들의 golden을 신어휘로 마이그레이션한다. 큐리셋 수정 금지 제약(13.2/13.3 승계)을 그때 다시 판단한다.
status: open

### DW-582: HYBRID 경로의 "결과가 맞았는가"를 CI에서 보는 검사가 하나도 없다
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
location: `api/tests/test_live_smoke.py`(`RUN_LIVE_SMOKE=1` 게이트) · `.github/workflows/tests.yml`(api·api-db 잡)
severity: medium
summary: 13.3은 DW-571을 "결과집합 자동채점 대신 라이브 스모크로 검증"이라는 대체 수단으로 닫았는데, 그 라이브 스모크 모듈은 `RUN_LIVE_SMOKE=1`이 없으면 통째로 skip이고 CI 어느 잡도 그 변수를 설정하지 않는다. 단위테스트는 `run_select`를 전부 monkeypatch하므로 실제 DB 왕복이 한 번도 안 일어난다.
evidence: `pytestmark = pytest.mark.skipif(not _LIVE)`, CI `api` 잡은 `python -m pytest -q`(secrets 없음), `api-db` 잡은 `tests/integration`만 도는데 거기 하이브리드/벡터 params 테스트가 없다. 즉 조건추출·조립·랭킹이 회귀해도 전부 초록으로 통과한다. 후속 리뷰 verification-gap·blind-hunter 독립 발견. 13.3에서 라이브 스모크가 폴백과 실제 하이브리드 실행을 구분하지 못하던 문제(답변 문구 미단언)는 이번 후속 리뷰에서 패치했으나, "CI에서 안 돈다"는 구조는 그대로다.
trigger: `api-db` 잡(실DB 통합)에 테스트를 추가할 일이 생길 때 — 가짜 LLM으로 고정 조건을 주입해 실제 pgvector에 `run_select(validate_select_sql(<하이브리드 모양 SQL>), (vec,))`를 돌리는 통합 테스트를 그때 함께 넣는다(GEMINI_API_KEY 불필요).
status: open

### DW-583: `hybrid_rag_node`가 `embedding IS NOT NULL`을 안 붙여 `doc_rag_node`와 필터가 어긋난다
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
location: `api/app/graph/hybrid_rag_node.py`(SQL 조립) · `api/app/graph/doc_rag_node.py:57` · `api/app/db/sql_guard.py`(`ALLOWED_COLUMNS`)
severity: low
summary: 같은 벡터검색인데 `doc_rag_node`는 `AND embedding IS NOT NULL`을 붙이고 `hybrid_rag_node`는 안 붙인다. `embedding`이 NULL이면 `embedding <=> %s::vector`가 NULL이고 PostgreSQL은 ASC에서 NULL을 마지막에 놓으므로, 구조조건에 맞으면서 임베딩이 있는 매물이 5건 미만일 때 임베딩 없는 매물이 "의미적으로 맞는 결과"인 양 끼어든다(예: 임베딩 생성이 아직 안 돈 신규 매물).
evidence: 후속 리뷰 blind-hunter 발견. 오케스트레이터가 실제 `validate_select_sql()`로 확인한 결과, `AND embedding IS NOT NULL`을 조립 SQL에 넣으면 **가드가 차단한다**(`embedding`은 `ALLOWED_COLUMNS`에 없고 벡터절 정규식이 기대하는 위치에서만 허용된다). 즉 트리비얼 패치가 아니라 가드 화이트리스트/정규식 변경이 함께 필요해 13.3 범위에서 처리하지 않았다.
trigger: `sql_guard`의 `ALLOWED_COLUMNS`나 벡터절 정규식을 다음에 손댈 때 — 그때 `embedding IS NOT NULL` 결합항을 함께 허용하고 `hybrid_rag_node` 조립에 추가한다. 그 전이라도 임베딩 미생성 매물이 검색결과에 섞인다는 신고가 들어오면 즉시 처리한다.
status: open

### DW-584: 새 LIMIT/OFFSET 앵커링이 거부하게 된 **정상 SQL 표현 목록**이 검사 옆에 안 적혀 있다
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
location: `api/app/db/sql_guard.py`(LIMIT/OFFSET 앵커링 정규식·중복절 검사)
severity: low
summary: DW-558을 닫은 전체 앵커링은 우회를 확실히 막았지만(실측 확인), 동시에 PostgreSQL이 정상으로 받아들이는 `LIMIT ALL`·`OFFSET n ROWS`·`FETCH FIRST n ROWS ONLY` 같은 표현도 함께 `limit_malformed`/`offset_malformed`로 거부한다. fail-closed 방향이라 안전하지만, **무엇이 거부되는지가 검사 옆에 실측으로 적혀 있지 않다.**
evidence: DW-574가 요구한 (b)항("검사 옆에 이 검사가 통과시키지 않는 안전 표현 목록을 실측해 적는다 — 추측 금지")과 정확히 같은 종류의 공백이고, 13.3은 그 요구를 `_conjunct_is_bare_status_on_sale`에 대해서만 다뤘다(그것도 미완). 스펙이 회귀 없음을 주장한 근거는 `LIMIT n`·`LIMIT n OFFSET m` 두 형태 테스트뿐이다. 후속 리뷰 blind-hunter 발견.
trigger: DW-574의 (b)항을 실제로 처리할 때 함께 — 두 항목이 같은 파일·같은 종류의 작업이므로 한 번에 실측해 적는다.
status: open

### DW-585: 13-3의 후속 리뷰가 한도 중단으로 끝맺지 못했다 — 의도적 재검토 1회가 남아 있다
origin: review-budget-followup (수동 인수)
source_spec: `spec-13-3-하이브리드-검색-sql-벡터.md`
severity: low
summary: 13-3은 리뷰 1차가 `done`으로 끝나 결과가 커밋(`final_revision: 2118001`)됐고, 2차는 **선택적 후속 검토**였다. 그 2차 세션이 2026-07-31 02:09 세션 한도로 중단됐다가 03:26에 깨어났으나 끝맺음 단계를 완수하지 못해, 세션이 시작 시 `in-review`로 바꿔둔 스펙 status를 `done`으로 되돌리지 못했다. 오케스트레이터는 그 순간의 작업 파일만 보고 "리뷰 미수렴"으로 판정해 스토리를 이월 처리하고 커밋 4개를 되돌렸다(run 20260730-205944-48e1, journal `review-result cycle=2 status=in-review` → `story-deferred`).
evidence: 되돌려진 커밋은 엔진이 `attempt-preserve/20260730-205944-48e1-e2e62a24`로 보존해 뒀고, 사람이 그 ref에서 4개 커밋을 그대로 복원했다. 복원 후 정책의 검증 명령 전량을 실제로 실행해 초록을 확인했다 — 환경 무결성 통과, api pytest 337 passed/83 skipped, web lint 무경고, web test 291 passed, flutter analyze 이슈 0. 후속 검토가 실제로 찾아낸 지적은 유실되지 않고 DW-579~584로 이미 등재돼 있다.
trigger: 13-3 코드(`hybrid_rag_node`·`sql_guard` 벡터절)를 다음에 손댈 때, 또는 에픽 13 회고 시 — 그때 독립 리뷰 1회를 의도적으로 돌린다. DW-583(임베딩 NULL 필터)·DW-584(거부되는 정상 SQL 표현 목록)와 같은 파일을 보므로 함께 처리하면 된다.
status: open

### DW-586: `/ai/search`에 사용자당 요청 빈도 제한이 전혀 없다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` DW-563 해결 과정에서 드러난 더 넓은 잔여 gap(스토리 범위 밖이라 코드 변경 없이 등재만)
location: `api/app/routers/ai.py`(`/ai/search` — `get_current_user`로 신원만 확인, 호출 빈도는 어디서도 세지 않음)
severity: medium
reason: DW-563은 CLARIFY 되묻기 상한을 서버가 `context` 길이로 직접 계산해 막았지만, 그건 "되묻기 루프가 결과 없이 반복되는 것"만 막을 뿐이다. 유효한 JWT 하나로 `/ai/search`를 (CLARIFY든 SQL이든 어떤 라우트든) 초당·분당 무제한 반복 호출하는 것 자체를 막는 장치는 이 프로젝트 어디에도 없다 — 인증은 "누가 불렀는지"는 알려주지만 "얼마나 자주 불렀는지"는 제한하지 않는다. 이 gap은 CLARIFY만의 결함이 아니라 `/ai/search` 전체에 해당하며, 진짜 세션/카운터 저장소 도입은 13.4 Never 절이 범위 밖으로 명시했다. `docs/conventions.md` §8도 "계정당 쿼터가 필요해지면 JWT의 사용자 ID로 Postgres 카운트를 걸면 된다"고 방법만 적어두고 실제로 걸려 있지는 않다(존재 확인≠작동 확인 — 아직 아무 정책도 실행되지 않는다).
trigger: 실사용에서 남용/과금 급증 신고가 들어오거나, 에픽 13 회고에서 이 gap을 우선순위로 올릴 때 — 그때 JWT 사용자 ID 기준 Postgres 카운트(예: 분당 N회)로 레이트리밋을 구현하고, 이 항목을 그 구현으로 닫는다.
status: open

### DW-587: `clarify` wire 필드를 소비할 웹 스토리가 없다 — 앱(16.5)만 있고 웹은 필드조차 안 보인다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 후속 코드리뷰(intent-alignment 렌즈) — 스펙 Never 절이 "Story 16.5/웹 대응 스토리 소관"이라 적었으나 실제 에픽 카탈로그 확인 결과 웹 스토리는 존재하지 않았다
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(16.5는 Flutter/앱 전용, 매칭되는 웹 스토리 없음) · `web/src/lib/api/aiSearch.ts`(`SearchResult` 타입에 `clarify` 필드 자체가 없었다)
severity: medium
reason: api는 이번 스토리(13.4)로 `/ai/search` 응답에 `clarify: {question, chips[]} | null`을 실제로 채워 보내기 시작했다. Flutter 앱은 Story 16.5가 이 필드를 렌더할 예정이지만, 웹은 그 필드를 소비할 스토리가 애초에 카탈로그에 없어 계획조차 안 돼 있었다 — 게다가 `aiSearch.ts`의 `SearchResult` 타입에 그 필드가 아예 없어서, 다음에 이 파일을 여는 사람은 서버가 그런 필드를 보낸다는 사실 자체를 알 방법이 없었다(칩 UI 미구현이 아니라 필드의 존재 자체가 안 보이는 문제). 이번 리뷰에서 `SearchResult`에 `clarify?: { question: string; chips: string[] } | null`을 추가해 최소 가시성만 확보했다(파싱·렌더링 로직은 없음, 범위 밖).
trigger: 다음 스프린트 플래닝이 웹 AI 검색 UI를 다시 열 때, 또는 에픽 13/16을 완전히 닫힌 것으로 판단하기 전 — 그때 웹 쪽 되묻기 칩 렌더링 스토리를 신설하고 이 항목을 그 스토리로 닫는다.
status: open
retarget (2026-08-05 회고): **Epic 15(관리자 웹 UI 통일)**. 서버는 `clarify.chips`를 정확히 보내는데 웹이 안 그린다 — 같은 web 워크스트림이라 Epic 15 인수조건 체크박스로 심는다(A4와 동일 처리).

### DW-588: `score_ab.py`의 `doc_hit` 지표가 CLARIFY 항목에 대해 조용히 항상 false가 된다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 리뷰(verification-gap 렌즈 발견) — 이번 스토리의 라우팅 변경이 원인이지만 오프라인 분석 스크립트 조정은 범위 밖이라 defer(13.1~13.3의 `score_ab.py` 드리프트 이월 관례 승계)
location: `api/scripts/score_ab.py`(`doc_hit()` — CLARIFY/"B" 라벨 항목의 answer 문구에 `(참고: <가이드 제목>)` 인용이 있는지로 판정) · `api/app/graph/clarify_node.py`(고정 템플릿 답변이라 그 인용 문구를 절대 포함하지 않음)
severity: medium
reason: `doc_hit`는 원래 CLARIFY가 `doc_rag_node`(실제 의미 RAG, 가이드 문서를 인용할 수 있음)로 임시 배선돼 있던 13.2~13.3 시절의 신호였다. 13.4가 CLARIFY를 상한 이내에서 고정 템플릿(`clarify_node`)으로 재배선하면서, 이제 CLARIFY 항목의 answer는 그 인용 형식을 낼 수 있는 경로 자체를 안 타므로 `doc_hit`가 구조적으로 항상 false가 된다. `score_model()`의 반환 요약에서 `doc_hit`는 `gate_pass`/`result_mean` 등 어떤 판정에도 반영되지 않는 항목별 부가 필드일 뿐이라 지금 당장 어떤 게이트도 무너뜨리지 않지만, 다음에 이 스크립트로 모델 비교나 에픽 13 회고 분석을 돌리는 사람이 "CLARIFY 항목이 가이드 인용을 멈췄다"로 오독할 수 있다.
trigger: `score_ab.py`를 다음에 손댈 때(예: 13.8 모델 A/B 채택 판단, 또는 DW-580/581/582 처리 시) — 그때 `doc_hit`를 CLARIFY 항목에서 아예 스킵하도록 고치거나, 이 지표 자체가 이제 SQL/HYBRID/doc-폴백 항목에만 의미 있다는 사실을 스크립트 주석에 명시한다.
status: open

### DW-589: 아키텍처 불변식 I12가 아직 "되묻기 cap = 클라 강제"라, 다음 스토리가 두 번째 상한을 또 만들 수 있다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 후속 코드리뷰(adversarial 렌즈) — 13.4가 DW-563을 서버 강제로 뒤집었는데 그 결정이 상위 계획문서에는 반영되지 않았다
location: `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md:390`(I12: "무상태이므로 **클라 강제** — 클라가 소유한 멀티턴 상태에서 clarify 횟수(≤2~3) 추적해 초과 시 칩 숨김/일반 검색")
severity: medium
reason: 13.4는 이 불변식을 의도적으로 뒤집었다 — 서버가 `context` 길이로 `clarify_turns`를 직접 계산해 상한을 강제한다(`api/app/graph/graph.py`의 `run_search`·`_clarify_step`, DW-563 resolution). 그런데 I12 본문은 그대로라, 이 불변식을 정본으로 읽는 다음 담당자(웹 칩 렌더링 스토리 DW-587, 또는 앱 Story 16.5)가 클라이언트에도 상한을 구현하면 **서버(3턴)와 클라(2~3턴)가 각자 세는 두 개의 상한**이 생긴다. 그러면 사용자는 자기가 몇 번 더 물을 수 있는지 알 수 없는 시점에 칩이 사라지고, 어느 쪽이 끊었는지 디버깅도 어렵다. 13.4 리뷰 1차에서 "구현 위치가 I12와 어긋난다"는 지적은 "이미 재검토된 결정"으로 reject됐는데, 결정이 바뀐 사실 자체가 상위 문서에 반영되지 않은 것은 그 reject가 다루지 않은 별개 사안이다(project-context.md 규칙 1의 정신 — 어긋나면 한쪽만 정본이어야 한다).
trigger: 웹 칩 렌더링 스토리(DW-587)나 앱 Story 16.5를 착수할 때 **그 스토리 스펙을 쓰기 전에** — 그때 I12 본문을 "서버 강제(+ 클라는 서버가 준 `clarify`가 null이면 칩을 그리지 않는다)"로 정정하고 이 항목을 닫는다. 에픽 13 회고가 먼저 오면 거기서 해도 된다.
status: open

### DW-590: SM3(데모 인수) 판정이 이제 벡터 검색 장애를 못 잡고, PRD·epics의 "두 경로 시연" 문구와도 어긋난다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 후속 코드리뷰(edge-case·intent-alignment 렌즈 합류) — 13.4가 CLARIFY를 `doc_rag_node`에서 고정 템플릿으로 재배선하면서 생긴 상위 문서·게이트 정합 문제(코드는 의도대로이나 판정 기준이 여러 문서에 흩어져 어긋났다)
location: `_bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/prd.md:141`(SM3 "두 경로(SQL 기반·문서 기반 RAG)를 모두 시연") · `_bmad-output/planning-artifacts/epics.md:568`("SQL 경로·문서 RAG 경로가 모두 적절한 매물카드를 반환한다") · `api/tests/test_demo_acceptance.py`(`test_sm3_pathB_returns_listings` — 이름은 listings인데 이제 `listings == []`를 단언) · `api/docs/ai-demo-queries.md`(②·③ 행만 13.4에 맞춰 갱신됨)
severity: medium
reason: 13.4 이후 단일턴 질의가 `doc_rag_node`(벡터 검색)에 도달하는 경로는 두 가지뿐이다 — (a) HYBRID에서 구조조건이 안 뽑혔을 때의 폴백, (b) CLARIFY 상한 초과 강제 폴백. 그래서 "의미형 질의를 던지면 문서 RAG가 매물을 준다"는 SM3 ②의 원래 시연 각본이 더는 성립하지 않는다. 세 가지가 함께 어긋나 있다: (1) PRD·epics는 여전히 옛 문구이고 갱신된 것은 `api/docs/ai-demo-queries.md`뿐이다(하위 문서만 고치면 상위가 정본 행세를 한다 — CLAUDE.md B8), (2) `test_sm3_pathB_returns_listings`는 함수 이름과 단언이 정반대라 이름만 보고 "의미형이 매물을 준다"고 오독하기 쉽다(이름 변경은 이 항목과 함께 처리한다 — 기존 열린 항목 DW-576이 같은 함수명을 참조하고 있어 지금 단독으로 바꾸면 그 참조가 끊긴다), (3) 데모 게이트가 `clarify_node`를 모킹하므로, 임베딩이 전부 NULL이 되거나 pgvector 쿼리가 깨져도 SM3는 초록이다(존재 확인≠작동 확인 — 벡터 경로의 실동작을 보는 결정론 검사가 SM3에서 사라졌다). 라이브 스모크에는 남아 있다(2026-07-31 실측: 상한 초과 강제 폴백이 실제로 매물 5건 + 가이드 문서 인용 "(참고: 패밀리카로 무난한 차종 고르기)"를 반환 — 벡터 경로 자체는 살아 있음을 확인했다). 즉 지금 깨진 것은 기능이 아니라 **판정 체계**다.
trigger: 데모 시연 각본을 확정하기 전, 또는 DW-573/DW-576(같은 `ai-demo-queries.md`·`test_demo_acceptance.py`를 손대는 항목)를 처리하는 같은 작업에서 함께 — 그때 (1) SM3의 "문서 RAG 경로" 시연을 어느 질의로 할지(HYBRID 폴백인지 상한 초과 경로인지) 정해 PRD·epics 문구를 그에 맞추고, (2) 테스트 함수명을 실제 단언에 맞게 바꾸고 참조 3곳을 함께 옮기고, (3) 벡터 경로가 실제로 매물을 돌려주는지 보는 결정론 검사를 SM3에 되살린다.
status: open

### DW-591: 되묻기 상한의 잔여 우회(`context` 위장)를 다시 꺼내볼 트리거가 어느 열린 항목에도 없다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 후속 코드리뷰(adversarial 렌즈) — DW-563을 닫으며 잔여 한계를 닫힌 항목 본문에만 적어 열린 장부에서 사라졌다
location: `_bmad-output/implementation-artifacts/deferred-work.md`(DW-563 resolution 본문 · DW-586) · `api/app/graph/graph.py`(`run_search`의 `clarify_turns = len(context or []) // 2`)
severity: low
reason: 13.4는 되묻기 상한을 서버 강제로 옮겼지만, 클라이언트가 매 요청 `context: []`로 보내면(또는 자기 질의만 담아 홀수 길이로 보내면) 서버 계산이 그대로 무력화된다. 이 사실은 DW-563의 resolution 본문과 13.4 스펙 Design Notes에 정확히 적혀 있지만, DW-563은 이제 done이라 `bmad-loop-sweep`이 훑는 열린 항목이 아니다. 대신 등재된 DW-586의 trigger는 "남용/과금 급증 신고가 들어올 때"인데, 이 우회는 과금 급증으로 나타나지 않는다 — 질의 1회는 라우트와 무관하게 정상 1회 호출이라 사용량 그래프에 아무 신호도 남기지 않는다. 결과적으로 이 잔여 gap을 다시 트리아지할 열린 항목이 하나도 없다(CLAUDE.md B8: "미룬 항목엔 언제·어디서 고칠지를 대장에 함께 적는다" 위반 형태). 지금 당장의 피해는 없다 — 서버가 결과를 강제하지 못할 뿐 사용자가 스스로 되묻기를 반복하는 것은 정상 사용이고, 무상태 아키텍처에서 이보다 강한 강제는 세션 저장소를 요구한다(13.4 Never 절).
trigger: 세션/대화 상태를 서버가 실제로 보관하기로 결정하는 시점(진짜 세션 저장소·체크포인터 도입 논의가 열릴 때), 또는 DW-586(요청 빈도 제한)을 구현할 때 — 둘 중 먼저 오는 쪽에서 이 우회를 함께 막고 이 항목을 닫는다. 그전까지는 "알고 수용한 한계"로 열어 둔다.
status: open

### DW-592: 출시된 Flutter 앱이 `clarify`를 파싱하지 않아, 되묻기 응답이 앱에서 "빈 텍스트"로 퇴행한다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 3차 코드리뷰(verification-gap·adversarial 렌즈 합류) — 13.4는 api 계약까지가 범위라 클라이언트를 손대지 않았는데, 그 결과가 **이미 배포된 앱의 사용자 눈에 보이는 퇴행**이라는 점이 이번에 처음 지적됐다
location: `app/lib/features/ai_search/ai_search_api.dart`(`SearchResult`에 `clarify` 필드 없음, `parseSearchResult`가 읽지도 않음) · `app/lib/features/ai_search/ai_chat_screen.dart`(`_MessageBubble` — content + listings만 렌더) · `_bmad-output/implementation-artifacts/sprint-status.yaml`(`16-5-4분기-ai-응답-되묻기-칩-앱: backlog`)
severity: medium
reason: 13.4 이전에는 CLARIFY가 `doc_rag_node`로 임시 배선돼 있어서, 앱에서 "패밀리카로 무난한 거" 같은 애매한 질의를 던지면 **실제 매물 카드**가 돌아왔다. 13.4가 CLARIFY를 고정 템플릿 되묻기로 재배선하면서 그 응답은 `listings: []` + `clarify: {question, chips}`가 됐다. 그런데 앱은 `clarify`를 파싱조차 하지 않으므로(repo 전체 `*.dart`에서 `clarify` 검색 결과 0건), 사용자에게는 **질문 한 줄만 뜨고 카드도 칩도 없는 화면**이 된다 — FR46의 상한이 막으려던 바로 그 막다른 느낌이 앱에서 먼저 나타난다. 웹은 이번 스토리 리뷰에서 최소한 값을 실어 나르도록 고쳤지만(DW-587), 앱은 필드 자체가 없다. DW-587은 "앱은 Story 16.5가 맡는다"는 근거로 웹만 다뤘는데, 16.5는 `backlog`라 착수 일정이 없다. 즉 api를 운영에 반영하는 순간부터 16.5가 끝날 때까지 앱 사용자에게 이 상태가 노출된다. 지금은 api가 운영에 반영되지 않아 실피해가 없다(로컬/개발만).
trigger: **api(`encar-ai-api` 운영)에 13.4를 반영하기 직전** — 그 배포 판단과 같은 자리에서 (a) 앱에 `clarify` 파싱+칩 렌더를 먼저 넣을지, (b) 16.5를 backlog에서 끌어올릴지, (c) 앱이 따라올 때까지 api 운영 반영을 미룰지 중 하나를 고르고 이 항목을 그 결정으로 닫는다. 16.5 착수가 먼저 오면 거기서 닫아도 된다.
status: open
retarget (2026-08-05 회고): 고칠 자리는 **`16-5-4분기-ai-응답-되묻기-칩-앱`**(백로그에 실재)이고, 그와 **별도로 배포 차단 조건**을 함께 건다: **에픽 13이 `main`(운영)에 병합되기 전에 16-5가 끝나 있거나, 아니면 병합을 미룬다.** 조건만 적고 스토리를 안 가리키면 `#73`이 비판한 "날짜 없는 조건"이 되므로 둘 다 적는다(B8). 2026-08-05 실측으로 **지금은 안 터진다**는 것을 확인했다: 운영 api(`encar-ai-api`)에 `가성비 좋은 차 알려줘`를 직접 호출하니 응답 키가 `['answer','listings']`뿐이고 `clarify` 키가 아예 없다(에픽 13 이전 코드). 앱 Dart 코드에 `clarify` 참조가 0건인 것도 확인 — 즉 '앱이 못 읽는다'는 사실은 맞지만, 운영이 아직 되묻기를 안 보내므로 현재 사용자 피해는 없다. **에픽 13을 운영에 올리는 순간 빈 화면이 된다.**

### DW-593: `/ai/search` 응답 객체 생성이 try/except **밖**이라, 응답 스키마 검증 오류는 CORS 헤더 없는 500이 된다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 3차 코드리뷰(adversarial·edge-case 렌즈 합류) — 13.4가 `clarify`(중첩 모델)를 추가하면서 이 기존 구조의 노출면이 넓어져 드러났다
location: `api/app/routers/ai.py`(`search()` — 마지막 `return SearchResponse(...)` 줄이 `try/except Exception` 블록 바깥에 있다)
severity: medium
reason: 이 파일의 `except Exception` 주석은 왜 이 핸들러가 필요한지를 스스로 길게 설명한다 — 라우트 밖(main.py 전역 핸들러)에서 잡힌 500은 `CORSMiddleware` 바깥에서 만들어져 `Access-Control-Allow-Origin`이 빠지고, 브라우저가 진짜 500을 "CORS 차단/연결 실패"로 오인해 원인을 은폐한다. 그런데 정작 응답 객체를 만드는 마지막 줄은 그 try 밖에 있어서, `SearchResponse`(또는 이제 그 안의 `ClarifyPayload`) 검증이 실패하면 그 실패는 **정확히 그 은폐 경로로** 나간다. 지금은 도달 불가에 가깝다 — `clarify`를 만드는 곳이 고정 상수 노드 하나뿐이고 단위테스트가 그 형태를 고정한다. 도달 가능해지는 시점이 예측되는 것이 이 항목의 요점이다: 13.5/13.6이 `route`·`narrowed_by`를 추가하거나, 되묻기 문구를 LLM이 만들게 바뀌면 그 순간 wire 검증이 실패할 수 있는 값이 생긴다. `listings`도 같은 노출면을 13.4 이전부터 갖고 있었으므로 이 스토리가 만든 결함은 아니다(그래서 이번에 고치지 않았다 — 범위 밖 구조 변경).
trigger: `/ai/search` 응답 스키마에 필드를 다음에 추가할 때(13.5 `route`·13.6 `narrowed_by`가 유력) — 그 스토리에서 `return SearchResponse(...)`를 try 안으로 옮기거나 응답 조립 전에 검증을 한 번 태우고, 일부러 깨진 값을 넣어 500 응답에 CORS 헤더가 붙는지 실측한 뒤 이 항목을 닫는다.
status: done 2026-07-31
resolution: `api/app/routers/ai.py`의 `return SearchResponse(...)`를 `try` 블록 안(`result = await asyncio.to_thread(...)` 바로 다음)으로 옮겼다. `api/tests/test_ai_search.py::test_search_response_validation_error_returns_500_with_cors`가 `narrowed_by=[123]`(스키마 위반)을 모킹해 실제로 500 + `access-control-allow-origin: http://localhost:3000` + `error.code=="internal_error"`를 실측 확인했다(spec-13-5-부드러운-거절.md). 이 보호는 구조적이다 — `answer`·`listings`·`clarify`·`narrowed_by` 네 필드 모두 같은 `return SearchResponse(...)` 한 줄, 같은 `try` 블록 안에서 조립되므로 어느 필드가 스키마를 위반해도 동일한 경로로 500+CORS가 된다. 이번 테스트는 `narrowed_by`를 **대표 사례로** 깨뜨려 그 구조를 실측한 것이며, `clarify`·`listings` 위반을 별도로 각각 실행해 확인하지는 않았다(코드리뷰 2026-07-31 지적 반영 — 과잉 일반화 방지).

### DW-594: 되묻기 칩의 세 축이 UX 정본의 데모 워크스루(인원·예산·연료 / "7인승")와 하나 어긋난다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 3차 코드리뷰(adversarial 렌즈) — 되묻기 문구는 EXPERIENCE.md Voice 표와 글자 그대로 일치시켰는데, 칩 값은 대조되지 않은 채 정해졌다
location: `api/app/graph/clarify_node.py`(`_CLARIFY_CHIPS = ["3천만원 이하", "SUV", "전기차"]` — 가격·차종·연료) · `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md:130`("되묻기 칩(**인원**·예산·연료) — 지수가 "**7인승**" 칩 탭 → petrol 선택 상태 → 좁혀진 결과")
severity: low
reason: 세 축 중 둘(예산≈가격, 연료)은 맞고 하나(인원 → 차종)가 다르다. 기능 결함은 아니다 — 칩은 눌러도 "그 문자열을 다음 질의로 보내는" 것이 전부라 어느 축이든 동작은 같고, 13.4 스펙 Tasks가 이 세 값을 명시적으로 지정했으므로 구현은 스펙대로다. 문제는 **정본이 둘로 갈렸다**는 것이다: EXPERIENCE.md의 데모 워크스루는 "7인승" 칩을 누르는 장면을 각본으로 갖고 있는데 실제 서버는 그 칩을 절대 보내지 않는다. 칩 UI를 만들 사람(웹=DW-587, 앱=Story 16.5)이 UX 문서를 읽고 인원 칩을 전제로 화면을 짜거나, 데모 시연자가 각본대로 눌러보려다 없는 칩을 찾게 된다. 어느 쪽이 옳은지는 제품 판단이라 이번 리뷰가 정하지 않았다(단위테스트도 의도적으로 칩 **내용**은 고정하지 않는다 — `test_clarify_node.py` 주석 참조).
trigger: 데모 시연 각본을 확정할 때, 또는 칩 렌더링 스토리(DW-587 / Story 16.5)의 스펙을 쓸 때 — 둘 중 먼저 오는 쪽에서 "인원 축을 넣을지, EXPERIENCE.md를 차종으로 고칠지"를 정하고 한쪽으로 통일한 뒤 이 항목을 닫는다. DW-590(데모 판정 정합)과 같은 자리에서 처리하면 문서를 한 번만 열어도 된다.
status: open

### DW-595: 오프라인 A/B 러너의 멀티턴 항목이 되묻기 상한과 딱 1턴 차이라, 4턴짜리 항목을 추가하면 조용히 거동이 바뀐다

origin: `spec-13-4-조건-좁혀-되묻기-clarify.md` 3차 코드리뷰(edge-case 렌즈) — 13.4가 도입한 상한이 오프라인 평가 스크립트의 기존 데이터와 맞닿는 지점
location: `api/scripts/run_phase_b.py`(`_run_multiturn` — 턴마다 user+assistant 2개를 무조건 누적, 클라이언트들과 달리 12항목 절단도 없음) · `api/docs/ai-ab-test-queryset.json`(가장 긴 멀티턴 항목 M1·M2 = 3턴) · `api/app/graph/graph.py`(`_CLARIFY_TURN_CAP = 3`)
severity: low
reason: 3턴짜리 항목의 마지막 턴에서 `clarify_turns`는 2다 — 상한 3에 정확히 1 모자란다. 즉 지금은 멀티턴 항목 전부가 상한에 걸리지 않아 13.4 이전과 같은 경로를 탄다. 하지만 (a) queryset에 4턴짜리 항목을 하나 추가하거나, (b) 상한을 2로 낮추면(FR46 문구 "최대 2~3턴"이 2도 허용한다), 그 항목의 마지막 턴은 되묻기 대신 `doc_rag_node` 강제 폴백을 타게 된다 — **queryset을 바꾼 사람은 라우팅을 바꾼 줄 모르고**, 이전 baseline과의 비교는 겉보기에 그대로 성립한다. 어떤 게이트도 이 여유를 검사하지 않고 어디에도 적혀 있지 않다. 지금 깨진 것은 없고, 다음에 이 데이터를 늘릴 때 밟는 함정이다.
trigger: `ai-ab-test-queryset.json`에 멀티턴 항목을 추가·수정할 때, 또는 다음 Phase B 실행(13.8 모델 A/B 채택 판단이 유력) — 그때 `run_phase_b.py`에 "멀티턴 항목의 턴 수가 `_CLARIFY_TURN_CAP` 미만인지" 확인하는 단언이나 주석을 넣고 이 항목을 닫는다. DW-588(같은 A/B 도구의 `doc_hit` 드리프트)과 같은 파일군이라 함께 처리하면 된다.
status: open

### DW-596: Follow-up review still recommended for 13-4-조건-좁혀-되묻기-clarify after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-4-조건-좁혀-되묻기-clarify.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260731-034209-7126; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-597: REJECT `narrowed_by`는 값만 배선되고 실제 "재제안 칩" 탭 UI(web/app)는 없다

origin: `spec-13-5-부드러운-거절.md` — 스펙이 Never 절에서 명시적으로 범위 밖으로 남긴 항목("실제 '재제안 칩' 탭 UI는 만들지 않는다")
location: `web/src/lib/api/aiSearch.ts`(`SearchResult.narrowed_by` 타입+매핑만 있고 렌더 소비처 없음) · `app/lib/features/ai_search/`(REJECT `narrowed_by` 파싱 자체가 없음)
severity: low
reason: 13.5는 서버 계약(`narrowed_by` 고정 상수 배선)까지가 범위다. `clarify.chips`가 13.4에서 값만 배선되고 렌더는 DW-587(웹)·Story 16.5(앱)로 미뤄진 것과 동일한 경계를 REJECT에도 그대로 적용했다 — 탭하면 그 조건으로 재검색하는 UI를 만들려면 별도 컴포넌트 작업(웹·앱 둘 다)이 필요하고 이번 스토리 크기를 넘는다. 지금은 실피해가 없다 — REJECT 응답은 여전히 텍스트 안내(Voice 표 문구)만으로 완결되고, `narrowed_by`가 렌더되지 않아도 사용자 경험이 깨지지 않는다(칩이 "없던 채로 정상 동작"하던 이전 상태와 같다).
trigger: `clarify.chips` 렌더링 스토리(DW-587 웹 / Story 16.5 앱)를 착수할 때 — 같은 컴포넌트(칩 배열 → 탭 가능 버튼 → 재검색)를 REJECT의 `narrowed_by`에도 재사용할 수 있는지 그 자리에서 함께 판단하고 닫는다. 두 필드가 같은 UI 패턴(문자열 배열 → 칩)을 쓰므로 한 번에 처리하면 컴포넌트를 두 번 만들지 않아도 된다.
status: open
retarget (2026-08-05 회고): **Epic 15(관리자 웹 UI 통일)**. DW-587·600과 한 덩어리(웹이 wire 필드를 안 그리는 문제).

### DW-598: SQL/HYBRID 0건 응답에 `narrowed_by`를 확장하는 일반화(실제 추출 SQL 조건 기반)는 범위 밖

origin: `spec-13-5-부드러운-거절.md` — 스펙이 Never 절에서 명시적으로 범위 밖으로 남긴 항목("SQL/HYBRID 경로의 기존 FR17 0건 fallback은 건드리지 않는다")
location: `api/app/graph/answer_node.py`(`_EMPTY_FALLBACK`, Epic 4부터 존재) · `api/app/graph/sql_rag_node.py`·`hybrid_rag_node.py`(SQL로 실제 추출된 구조조건이 narrowed_by로 노출되지 않음)
severity: low
reason: 13.5의 Given/When/Then은 "Given REJECT 경로"로 시작하고, REJECT는 태생적으로 `listings=[]`(0건)이므로 "0건·거절 다양성을 narrowed_by로 표현"하는 요구를 REJECT 자신의 속성으로 좁혀 해석했다(spec Design Notes). SQL/HYBRID 0건 fallback에 "실제 추출된 SQL 조건(가격·차종 등)을 narrowed_by로 노출"하는 확장은 REJECT의 고정 상수와 달리 **실제 조건 추출 로직**이 필요해(SQL 파서 또는 LLM 구조화 출력에서 조건을 다시 뽑아야 함) 이번 스토리의 "고정 상수만" 범위를 크게 넘는다. Story 13.6(가이드 활용) AC에도 이 확장이 언급되지 않아 별도 스토리로 남기는 것이 안전하다.
trigger: FR17 0건 fallback을 개선하는 후속 스토리를 계획할 때(SQL/HYBRID 0건 응답에 실제 조건 완화 제안을 붙이는 요구가 나오면) — 그때 narrowed_by를 REJECT 밖으로 확장할지, 별도 필드를 새로 둘지 판단하고 이 항목을 닫는다.
status: open

### DW-599: FR17 0건 문구(`_EMPTY_FALLBACK`)가 EXPERIENCE.md Voice 표와 다르다

origin: `spec-13-5-부드러운-거절.md` 2차 코드리뷰 — 13.5가 "사용자 노출 문구는 EXPERIENCE.md Voice 표 정본과 글자 그대로 일치"라는 규칙을 세우면서 REJECT 문구 **하나에만** 적용했고, 같은 파일의 형제 문구는 손대지 말라고 Never 절이 못박았다.
location: `api/app/graph/answer_node.py`(`_EMPTY_FALLBACK`) vs `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md:62`(Voice 표 "검색 0건(FR17)" 행)
severity: low
reason: 실측 대조 결과 두 문자열이 다르다 — 코드는 "조건에 맞는 매물을 찾지 못했어요. 가격대나 차종 조건을 넓히거나 원하시는 용도를 알려주시면 다시 찾아드릴게요.", 정본 Voice 표는 "조건에 맞는 매물이 아직 없어요. 조건을 조금 넓혀볼까요?" + 완화 칩. 13.5가 만든 결함은 아니다(`_EMPTY_FALLBACK`은 Epic 4부터 존재). 다만 13.5가 "노출 문구 = Voice 표 정본"이라는 규칙을 새로 세워 놓고 예외를 대장에 남기지 않으면, 다음 사람이 이 불일치가 **결정인지 누락인지** 구별할 수 없다(CLAUDE.md B8 — 미룬 판단은 틀린 게 아니고 안 적는 게 틀린 거다). 실피해는 아직 없다: 두 문구 모두 사용자를 다음 행동으로 유도하며, dead-end 게이트도 양쪽 다 redirect로 판정한다(`REDIRECT_MARKERS` 마커 3 "용도를 알려주시면"이 이 문구를 덮도록 이번 리뷰에서 복구·실측).
trigger: FR17 0건 응답을 손대는 다음 스토리에서(DW-598의 narrowed_by 확장이 유력한 자리다) — 그때 Voice 표 문구로 맞출지, 코드 문구를 정본으로 승격해 EXPERIENCE.md를 고칠지 정하고 닫는다. 어느 쪽이든 `REDIRECT_MARKERS`와 `tests/test_ab_scoring.py::test_redirect_markers_actually_match_the_shipped_answers`를 함께 갱신해야 한다.
status: open

### DW-600: `narrowed_by`를 answer 문장으로 "조립"하는 책임이 미구현인데 어느 항목에도 안 잡혀 있다

origin: `spec-13-5-부드러운-거절.md` 2차 코드리뷰(intent-alignment 감사) — 스펙 `<intent-contract>`가 13.5를 "값 배선까지"로 좁혔으나, 그 상위 정본은 더 넓은 표면을 요구한다.
location: `api/app/graph/answer_node.py`(`narrowed_by`를 판단 없이 통과만 시킴) vs `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:1045`(Story 13.5 AC "…구조화 사유 데이터 `narrowed_by`를 **결정론 템플릿이 조립한다**(CR4)") · `_bmad-output/implementation-artifacts/epic-13-context.md`(L71·L93이 지금도 "answer_node의 결정론 템플릿이 책임진다"고 서술)
severity: low
reason: 정본 AC와 CR4가 쓰는 동사는 "조립"이고, 기대가 사는 표면은 **사용자가 읽는 answer 문장**이다. 실제 구현이 도달한 표면은 **응답 JSON 필드**까지이며, 리포지토리 전체에서 `narrowed_by`와 `answer`를 연결짓는 단언은 0개다(유일한 다중 질의 테스트는 오히려 불변성을 못박는다). 이 격차 중 "칩 UI 렌더"는 DW-597이, "SQL/HYBRID 0건 확장"은 DW-598이 잡고 있으나, **"답변 문장 조립"과 "원 조건(맥락) 복원"** 두 조각은 어느 항목에도 없고 스펙 Design Notes의 산문 근거로만 존재한다. 스펙의 좁은 해석 자체는 FR47의 무상태·결정론 요구와 정합해 이번 스토리에서 뒤집을 사안이 아니다(1·2차 리뷰 모두 동일 판단) — 문제는 **격차가 장부에 없다는 것**이다.
trigger: Story 13.6(가이드 활용)이 `answer_node`의 응답 조립 로직을 손대는 시점 — 같은 함수를 여는 자리이므로 그때 (a) 고정 상수를 한국어 문장으로 렌더해 answer에 붙일지, (b) 정본 AC/`epic-13-context.md` 문구를 "값 배선까지"로 정정할지 택일하고 닫는다. 어느 쪽이든 `narrowed_by`와 `answer`를 연결짓는 단언이 하나는 생겨야 한다.
status: open
retarget (2026-08-05 회고): **Epic 15(관리자 웹 UI 통일)**. DW-587·597과 한 덩어리.

### DW-601: DW-593이 닫은 CORS-500 보호에 남은 노출면 — `response_model` 재검증은 여전히 `try` 밖에서 돈다

origin: `spec-13-5-부드러운-거절.md` 2차 코드리뷰 — DW-593 resolution이 "네 필드 모두 같은 경로로 500+CORS"라고 적었는데, 그 주장은 정확히는 **생성자 검증 층위**에만 해당한다.
location: `api/app/routers/ai.py`(`@router.post("/search", response_model=SearchResponse)` — 데코레이터 인자와 엔드포인트 함수 본문의 `try`)
severity: low
reason: 13.5가 옮긴 것은 `SearchResponse(...)` **생성자 호출**이고, 그건 확실히 `try` 안으로 들어와 CORS 안쪽 500이 된다(테스트로 실측됨). 그러나 FastAPI는 `response_model`로 엔드포인트가 **반환한 뒤** 한 번 더 검증·직렬화하며, 그 단계에서 나는 예외는 함수 밖이라 `except Exception`이 못 잡고 Starlette `ServerErrorMiddleware`(CORSMiddleware 바깥)가 500을 만든다 — DW-593이 처음에 지목한 바로 그 은폐 경로다. 지금은 사실상 도달 불가다(이미 검증된 인스턴스를 그대로 넘기므로). 도달 가능해지는 조건이 예측된다는 점이 이 항목의 요점이다: `@field_serializer` 추가, `response_model_exclude` 사용, 또는 엔드포인트가 모델 대신 dict를 반환하도록 바뀌는 순간. (DW-593 자체는 orchestrator 소관이라 이 리뷰에서 수정하지 않고 신규 항목으로 남긴다.)
trigger: `SearchResponse`에 직렬화 커스터마이징(`@field_serializer`·`model_serializer`·`response_model_*` 옵션)을 처음 도입할 때, 또는 `/ai/search`가 모델 대신 dict를 반환하도록 바뀔 때 — 그 시점에 `response_model=` 인자를 떼거나(반환 애노테이션만으로 문서화는 유지된다) 직렬화 실패도 CORS 안쪽에서 잡히는지 일부러 깨뜨려 실측하고 닫는다.
status: open

### DW-602: 라우터 LLM 장애로 폴백 REJECT를 타면, 사용자가 말한 적 없는 조건이 `narrowed_by`로 실려 나간다

origin: `spec-13-5-부드러운-거절.md` 3차 코드리뷰(adversarial 레이어) — 스펙 Always 절이 "`guard_node`는 고정 상수를 **항상** 반환한다"고 못박아 이번 패스에서 코드로 못 고침
location: `api/app/graph/router_node.py`(`_fallback_route` — 매물 신호 없으면 `"REJECT"`) → `api/app/graph/guard_node.py`(`_GUARD_NARROWED_BY` 무조건 반환) · `docs/conventions.md` §4(`narrowed_by`가 비어 있지 않으면 REJECT라는 판별 규약)
severity: low
reason: `router_node`는 구조화 출력 파싱 실패·일시 형식오류를 잡아 `_fallback_route`로 결정론 보정하고 재던지지 않는다(DW-561과 같은 경로). 그 폴백은 매물 신호가 없으면 `REJECT`를 주므로, Gemini 장애 중에는 **정상 차량 질의도 거절 경로를 탄다**. 13.5 이전에는 그 결과가 "거절 문구 하나"였는데, 이제는 사용자가 한 번도 말한 적 없는 `["price<=30000000", "body_type=SUV", "fuel=전기"]`가 "좁힌 조건"이라는 이름으로 함께 나간다. 지금은 이 값을 렌더하는 소비처가 없어 사용자 눈에 보이지 않지만(값만 배선 — DW-597), 재제안 칩 UI가 생기는 순간 장애 상황에서 **거짓 정보를 사용자에게 표시**하게 된다. 이번 스토리에서 못 고친 이유는 스펙 Intent의 Always 절이 "`query`나 `context`를 읽어 값을 바꾸지 않는다(무상태)"를 계약으로 고정했기 때문이다 — 폴백 여부로 값을 바꾸는 것은 그 계약을 어기는 변경이라 스펙 밖 결정이 필요하다.
trigger: DW-597(재제안 칩 UI)을 실제로 구현하는 시점 — 값이 화면에 보이기 직전이 마지막 방어선이다. 그때 (a) `run_search`가 라우터 폴백 여부를 노출하고(DW-561이 제안한 `route_fallback` 플래그와 같은 자리) 폴백 REJECT면 `narrowed_by`를 비우거나, (b) 칩을 "예시 조건"으로 라벨링해 사용자가 자기 입력의 복원으로 오해하지 않게 하거나 중 택일하고 닫는다.
status: open

### DW-603: Follow-up review still recommended for 13-5-부드러운-거절 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-5-부드러운-거절.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260731-051647-7a0b; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-604: 컷오프 실측(Block-If) 미검증 — 이 구현 세션엔 로컬 Supabase/pgvector가 없다

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 구현 세션(2026-07-31)
location: `api/app/graph/doc_rag_node.py`(`_GUIDE_DISTANCE_CUTOFF = 0.3`) · `api/scripts/run_phase_b.py`+`api/scripts/score_ab.py`(Block-If가 요구하는 실측 도구)
severity: medium
reason: 스펙의 Block-If("`run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4` 실행 → `score_ab.py`로 채점, 컷오프 적용 전/후 `doc_hit` recall이 하락하면 HALT")를 검증하려면 `RUN_LIVE_SMOKE=1` + 로컬 Supabase(pgvector 확장) + `GEMINI_API_KEY`가 필요하다. 이 구현 세션의 샌드박스엔 docker가 없고(`docker: command not found`), sudo도 불가해(`sudo: interactive authentication is required`) `postgresql-18-pgvector` 패키지를 설치할 수 없으며, `DATABASE_URL`도 설정돼 있지 않다(로컬·원격 어느 쪽도 없음) — memory `e2e-selftest-env-blockers.md`가 이미 기록한 것과 같은 종류의 환경 차단이다. 단위테스트(몽키패치로 run_select/embed_query를 가짜로 교체)는 게이트 로직 자체(거리 비교·None 반환)는 red→green으로 실측했지만(`_GUIDE_DISTANCE_CUTOFF`를 1.0으로 풀어 관련 테스트가 실제로 깨지는 것까지 확인), 0.3이라는 값이 실제 임베딩 거리 분포에서 정답 가이드까지 쳐내는지는 실 데이터가 있어야만 답할 수 있는 질문이라 이 세션에서 확인 불가.
trigger: 로컬 Supabase(pgvector)가 뜨는 환경(예: 이전 dev-story 세션이 쓰던 Docker 환경)에서 `RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python scripts/run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4 --out /tmp/g13-6-check.json && .venv/bin/python scripts/score_ab.py --queryset docs/ai-ab-test-queryset.json --raw /tmp/g13-6-check.json --out /tmp/g13-6-report.json`를 실제로 돌려 `doc_hit` recall을 `docs/g2-baseline.json`(컷오프 적용 전 캡처) 채점 결과와 비교한다. 하락하면 `_GUIDE_DISTANCE_CUTOFF`를 조정하거나 스펙 Block-If에 따라 HALT하고, 문제 없으면 이 항목을 닫는다.
status: done 2026-07-31
resolution: 로컬 Supabase(pgvector, 포트 55322 — 매물 103건·가이드 10건 전부 임베딩됨)가 뜬 세션에서 직접 실측했다(사용자 요청, 2026-07-31). ① **전/후 비교 방식 변경**: DW-608이 지적한 대로 커밋된 `docs/g2-baseline.json`(07-30 캡처)과 비교하면 13-4·13-5 변경이 뒤섞이므로, 같은 코드·같은 DB에서 `_GUIDE_DISTANCE_CUTOFF`만 0.3(ON) / 99.0(OFF = 13.6 이전 "항상 인용" 동작)으로 바꾼 **두 팔을 지금 캡처해** 비교했다(subset B1~B7,G1,G4 + HYBRID 커버용 G2,G3,G6 + 멀티턴 M4,M7 = 14건 × 2팔, `run_phase_b.py` 래퍼). 결과 `score_ab.doc_hit` recall = **ON 0/10 · OFF 0/10 — 하락 없음**이므로 Block-If의 HALT 조건은 미충족(스토리 통과). 단 이 0/0은 컷오프 탓이 아니라 doc_refs 항목 10건이 전부 CLARIFY/REJECT로 라우팅돼 `doc_rag_node`에 도달하지 못하기 때문이다(DW-607에 실측 기록). ② 그래서 에픽 13.6 AC가 실제로 요구한 "임계값은 Phase B 질의셋으로 튜닝해 확정"을 직접 수행했다 — 큐리셋 44항목 전체의 최근접 가이드 코사인 거리 실측: 기대 가이드가 있는 질의 10건 = 0.1944~0.3042(중앙 0.2301), 없는 질의 34건 = 0.2418~0.4914(중앙 0.3168). 컷오프 후보별 (정답 통과 / 무관 통과) = **0.25 → 6/10·1/34 · 0.3 → 9/10·8/34 · 0.35 → 10/10·25/34 · 0.4 → 10/10·31/34**. 0.35 이상은 노이즈가 급증하고 0.25는 정답 4건을 잃으므로 **0.3을 실측 확정값으로 유지**한다(완전 무관 질의 C2 김치찌개 0.4914·C1 날씨 0.4750·C3 비트코인 0.4167은 어느 후보값에서도 차단). ③ 노이즈 제거 실동작 관측: 컷오프 OFF에서 G2("너무 비싸지 않은 대형 세단")에 붙던 '차종별 특성과 용도 가이드' 인용이 ON에서 사라졌다. ④ `_GUIDE_DISTANCE_CUTOFF` 주석의 "Phase B 실측으로 확정한다"는 이로써 이행됐다 — 값 변경은 없다(0.3 유지).

### DW-605: 스펙 Block-If의 명명된 subset이 HYBRID를 하나도 커버하지 않는다 — AC1 실물 검증이 test_live_smoke_hybrid()에만 의존

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 후속 코드리뷰(2026-07-31)
location: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md`(`## Verification` → Commands) · `api/docs/ai-ab-test-queryset.json` · `api/tests/test_live_smoke.py`(`test_live_smoke_hybrid`)
severity: medium
reason: 스펙의 Block-If·Verification이 명명한 subset(`run_phase_b.py --subset B1,B2,B3,B4,B5,B6,B7,G1,G4`)을 `api/docs/ai-ab-test-queryset.json`에서 직접 확인한 결과, 이 9개 항목은 전부 `primary_path: "B"` — 즉 순수 벡터검색(`doc_rag_node`)의 인용/컷오프 경로만 태운다. HYBRID로 라우팅되는 항목이 하나도 없어, 이 명령을 (미래에 로컬 Supabase/pgvector 환경이 생겨) 실제로 돌려 `doc_hit` recall이 하락 없음을 확인하더라도 그것은 FR49(컷오프·인용)만 검증할 뿐, 이 스토리의 headline 기능인 AC1(`hybrid_rag_node`의 가이드 질의확장, FR44)은 전혀 검증하지 못한다. AC1의 라이브 확인은 이제 코드리뷰로 강화된 `test_live_smoke_hybrid()`(answer에 "(참고:" 인용 접미사가 실제로 붙는지 확인 — 가이드 주입이 조용히 무동작이면 이 단언이 깨진다)와 스펙의 기존 수동 확인 항목("조립된 SQL에 body_type 조건이 실제로 포함되는지... 눈으로 확인")에만 의존한다. 이 둘 다 이 세션(DW-604와 동일한 샌드박스: docker 없음·sudo 불가·DATABASE_URL 미설정)에서는 미실행 상태다 — 미래 세션이 DW-604의 Block-If 명령만 돌려보고 recall이 유지된다는 이유로 AC1까지 "실물 검증 완료"로 잘못 결론 내리는 것을 막기 위해 이 항목을 별도로 남긴다.
trigger: 로컬 Supabase(pgvector) 환경에서 `cd api && RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres GEMINI_API_KEY=<키> .venv/bin/python -m pytest tests/test_live_smoke.py::test_live_smoke_hybrid -q`를 실제로 돌려 answer에 "(참고:"가 포함되는지 확인한다(가능하면 DW-604의 Block-If subset 실행도 같은 세션에서 함께 수행). 통과하면 AC1이 실물로 확인된 것으로 이 항목을 닫고, "(참고:"가 없으면(가이드가 컷오프를 못 넘겼거나 시스템 프롬프트 주입이 실제로 조건추출에 반영되지 않은 것) `_GUIDE_DISTANCE_CUTOFF`나 `_GUIDE_BLOCK_TEMPLATE` 배선을 재점검한다.
status: done 2026-07-31
resolution: 같은 세션에서 AC1을 라이브로 실물 검증했다. ① `RUN_LIVE_SMOKE=1 DATABASE_URL=... .venv/bin/python -m pytest tests/test_live_smoke.py -q` → **5 passed**(강화된 `test_live_smoke_hybrid` 포함 — 추출 구조조건 로그에 `body_type`·`seats`·`accident_free` 중 하나가 실제로 등장하는지 단언하는 그 테스트). ② 스펙 AC1 원문("반환된 매물의 body_type이 가이드가 제시하는 범주로 실제 좁혀져 있다")은 로그가 아니라 **매물로 직접** 확인했다: `run_search("3천만원 이하로 무난한 패밀리카")` → `find_relevant_guide 거리=0.2550 제목='패밀리카로 무난한 차종 고르기' 컷오프통과=True` → 추출 조건 `price <= 30000000 AND body_type IN ('준중형차','중형차','SUV','RV')` → 반환 5건이 전부 SUV(3)·중형차(2). 같은 가격대 전체 풀(3천만원 이하 on_sale)에는 경차 8·화물차 3·소형차 3·경승합차 2가 있는데 전부 배제됐다 — 매물 설명에 "패밀리카"가 없어도 가이드가 결과를 좁혔다는 관찰 가능한 증거. answer는 `조건에 맞는 매물 5건을 찾았어요. (참고: 패밀리카로 무난한 차종 고르기)`로 결정론 템플릿 + 인용 접미사와 글자 그대로 일치해 AC2도 함께 확인됐다. ③ "명명된 subset이 HYBRID를 하나도 안 태운다"는 이 항목의 원 지적은 오늘 캡처에서도 재확인됐고(B계열 전부 CLARIFY/REJECT), 그 구조적 해결(큐리셋에 HYBRID 라벨 항목 신설)은 DW-609가 이어받는다.

### DW-606: `hybrid_rag_node`의 가이드 인용이 "거리상 가까움"만 확인하고 "실제로 조건추출에 반영됐음"은 확인하지 않는다

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 코드리뷰(2026-07-31, adversarial·edge-case-hunter 레이어 중복 지적)
location: `api/app/graph/hybrid_rag_node.py`(성공 경로의 `if listings and guide and guide[0]: answer += f" (참고: {guide[0]})"`)
severity: low
reason: `guide`는 조건추출 LLM 호출 **이전**에 컷오프(0.3) 이내로 딱 1건만 조회되고, 그 뒤로는 재시도 전체에서 고정이다. 인용 부착 조건은 "listings가 있고 guide가 존재(제목 비어있지 않음)"뿐이라, LLM이 실제로는 그 가이드 매핑을 전혀 쓰지 않고(예: 사용자가 "3천만원 이하 세단만"처럼 이미 완전히 명시적인 조건을 줘서 가이드 없이도 조건을 뽑은 경우) 우연히 거리상 가까운 무관한 가이드가 컷오프를 통과했다면, 그 매물과 무관한 가이드 제목이 "(참고: ...)"로 붙을 수 있다. 코퍼스가 작고(10개) 각 문서가 서로 다른 주제를 다뤄 실제 발생 빈도는 낮을 것으로 판단하지만(완전히 명시적인 질의는 보통 어느 가이드와도 의미상 멀 가능성이 높다), 이론적으로는 실재하는 갭이다. "실제로 반영됐음"을 프로그램적으로 판별하려면 LLM이 출력한 조건 문자열과 가이드가 제안하는 항목(예: body_type 값)의 대응을 검사하는 새 메커니즘이 필요해, 이번 코드리뷰 패스의 patch 범위(트리비얼하게 고칠 수 있는 것)를 넘는다.
trigger: 이 인용 정확도가 실사용에서 실제 불만·오해로 이어지는 사례가 관찰되거나, `hybrid_rag_node`의 LLM 조건추출이 구조화 출력(structured output)으로 바뀌어 "이 조건이 가이드에서 왔는지"를 LLM 스스로 표시할 수 있게 되는 시점 — 그때 인용 조건에 "가이드 유래 조건이 실제로 포함됐는가" 검사를 추가하거나, DW-605의 라이브 검증(test_live_smoke_hybrid)에서 이 케이스가 실제로 관측되면 그 결과를 근거로 우선순위를 재평가한다.
status: open

### DW-607: Block-If의 실측 관측력이 기록된 것보다 훨씬 작다 — 유효 표본 3/9이고 `doc_hit`는 "노이즈 인용"을 원리상 벌하지 못한다

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 후속 코드리뷰(2026-07-31)
location: `api/scripts/score_ab.py`(`doc_hit()` 정의 191행, 채점 분기 465행) · `api/docs/ai-ab-test-queryset.json` · `api/docs/g2-baseline.json`
severity: medium
reason: DW-605는 "명명된 subset 9건이 전부 `primary_path: "B"`라 HYBRID를 커버하지 못한다"까지만 적었는데, 실제로 `g2-baseline.json`(컷오프 적용 전 캡처)을 이번 리뷰에서 직접 채점해 보니 관측력은 그보다 더 작다. (1) 9건 중 5건(B2·B4·B5·B6·B7)은 캡처 당시 실제로 `route_last: "C"`(REJECT)로 빠져 `doc_rag_node`에 도달조차 하지 않았다 — 이들의 `doc_hit=False`는 인용 품질이 아니라 라우팅 결과다. `doc_hit`가 True인 항목은 B1·B3·G1 **3건뿐**이라, 이 지표에서 한 건만 뒤집혀도 33% 변동으로 보인다. (2) `score_ab.py`의 `doc_hit()`는 `any(기대 제목 in answer)` — **기대 제목이 있으면 상**을 줄 뿐, 엉뚱한 제목이 인용돼도 **벌하지 못한다**. 실측 예: G4("그냥 괜찮은 차 아무거나 추천해줘", `doc_refs: null`)의 baseline answer는 "(참고: 초보 운전자에게 적합한 차종)"을 달고 있다 — 이 스토리가 FR49로 없애려는 바로 그 노이즈 인용인데, 컷오프로 이걸 성공적으로 걸러도 `doc_hit` 점수는 정확히 0만큼 변한다. 즉 Block-If가 초록이어도 그건 "회귀가 없다"는 뜻이지 "컷오프가 목적을 달성했다"는 증거가 아니다. 스펙 Never 절이 "신규 노이즈 스코어러를 추가하지 않는다"고 이미 결정했으므로 이번 패스에서는 고치지 않고, 그 트레이드오프의 실제 대가를 측정값으로 남긴다.
trigger: DW-604의 Block-If를 실제로 실행하는 그 세션에서 함께 처리한다 — 실행 결과를 읽을 때 `doc_hit` recall 유지만 보지 말고, (a) `doc_refs: null` 항목(G4 등)의 answer에 "(참고:"가 **사라졌는지**를 눈으로 확인해 컷오프의 노이즈 제거 효과를 직접 관측하고, (b) B2·B4·B5·B6·B7이 여전히 REJECT로 빠지는지 확인한다(빠진다면 그 5건은 이 지표에서 영원히 무신호이므로 subset 재구성이 필요하다). 새 스코어러가 필요하다고 판단되면 그때 스펙 Never 절을 명시적으로 뒤집는 결정을 기록하고 추가한다.
status: done 2026-07-31
resolution: 트리거가 지시한 대로 DW-604 실측 세션에서 함께 처리했다. (a) `doc_refs: null` 항목의 노이즈 인용이 실제로 사라지는지 관측 — 컷오프 OFF에서 G2에 붙던 '차종별 특성과 용도 가이드'가 ON에서 사라졌다(이 항목이 예로 든 G4는 07-30 baseline과 달리 지금 CLARIFY로 라우팅돼 노이즈 인용 자체가 발생하지 않는다). (b) B2·B4·B5·B6·B7 재확인 결과는 이 항목이 기록한 것보다 **더 나쁘다**: B2·B4·B6·B7은 여전히 REJECT, B5는 CLARIFY로 바뀌었고, 13-4 이후 B1·B3·G1·G4·M4·M7까지 CLARIFY로 흡수돼 **doc_refs가 달린 10건 중 `doc_rag_node`에 도달하는 항목이 0건**이다(07-30 baseline에서는 B1·B3·G1·G4 4건이 route B로 도달해 인용을 받았다). 즉 `doc_hit`의 유효 표본은 3/9이 아니라 **0/10**이고, 이 지표는 지금 구조상 항상 0이다(DW-588과 같은 뿌리). 결론: 이 항목이 남긴 "subset 재구성이 필요하다"는 처방은 **효과가 없다** — 재구성 대상이 라우팅 단계에서 사라지기 때문이며, 관측 가능한 형태로 되살리려면 큐리셋에 HYBRID 라벨 항목을 신설해야 한다(DW-609). 측정은 끝났고 남은 처방은 DW-609로 이관하므로 이 항목은 닫는다.

### DW-608: 문서화된 Block-If 명령이 그 명령이 약속한 "전/후 recall 비교"를 원리상 수행하지 못한다

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 3회차 후속 코드리뷰(2026-07-31)
location: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md`(`## Verification` → Commands 2번째 줄) · `api/scripts/score_ab.py`(`--raw` 인자 처리 603·609·617행, `score_model()` 반환 summary 560~590행, `doc_hit` 채점 465행)
severity: medium
reason: DW-604/605/607은 "환경이 없어 못 돌렸다"·"돌려도 감도가 작다"까지만 다뤘다. 이번 리뷰에서 `score_ab.py`를 직접 읽어보니 **명령 자체가 약속을 이행할 수 없다**. (1) 스펙과 DW-604가 적어 둔 명령은 `--raw /tmp/g13-6-check.json` 파일 **하나**만 넘기는데, `score_ab.py`의 1-raw 모드는 소스 주석 그대로 "베이스라인 단독 — A/B 비교(사전식 승부·회귀 게이트) 없이 그 raw 1개의 채점 요약만 기록한다"다(617행). 즉 "컷오프 적용 전/후 비교"가 일어나지 않는다 — 전/후를 보려면 `--raw docs/g2-baseline.json /tmp/g13-6-check.json` 2-raw 모드여야 한다. (2) 게이트 지표인 `doc_hit`은 `score_model()`이 돌려주는 summary 딕셔너리에 **없다** — 465행에서 per-item 레코드(`rec["doc_hit"]`)로만 기록되고 콘솔 출력에도, 회귀 게이트(`gate_pass`는 오염·데드엔드·errored만, `regression_block`은 `result_mean`만 본다)에도 반영되지 않는다. 리포트 JSON의 `per_item`을 직접 세지 않으면 "recall이 하락했나"라는 질문에 답할 자리가 없다. (3) subset 9건 결과를 44항목 queryset으로 채점하면 `is_partial: True`·`missing_n: 35`가 되어, 44건 전량인 `docs/g2-baseline.json`과는 분모가 다르다(직접 확인: baseline results 44건). 결과적으로 미래 세션이 이 명령을 그대로 붙여 실행하면 비교가 수행되지 않았다는 사실을 눈치채지 못한 채 "Block-If 초록"으로 기록하고 DW-604를 닫을 위험이 있다.
trigger: DW-604의 Block-If를 실제로 실행하는 그 세션에서, **명령을 그대로 붙이기 전에** 이 항목을 먼저 읽는다 — (a) `--raw`에 베이스라인과 후보 **2개**를 넘기고, (b) 베이스라인도 같은 subset으로 잘라 채점하거나 subset 없이 전량 재캡처해 분모를 맞추고, (c) `doc_hit` recall은 리포트 JSON의 `per_item`에서 `primary_path == "B"` 항목만 골라 직접 센다(또는 그 세션에서 `score_model()`에 `doc_hit_recall` summary 필드와 콘솔 한 줄을 추가한다 — 이는 스펙 Never 절이 금지한 "신규 노이즈 스코어러"가 아니라 기존 지표의 집계이므로 별개 판단이다). 그리고 스펙 Verification과 DW-604의 명령 문자열을 실제로 동작하는 형태로 정정한다.
status: done 2026-07-31
resolution: 이 항목이 예고한 함정을 확인하고 우회한 절차로 Block-If를 실제 실행했다(2026-07-31). 스펙의 1-raw 명령은 A/B 비교를 하지 않으므로 **그대로 쓰지 않았고**, 대신 같은 코드에서 컷오프만 껐다 켠 두 팔을 각각 캡처한 뒤 `score_ab.doc_hit()`를 직접 호출해 per-item으로 셌다 — 두 팔의 subset이 동일하므로 이 항목이 지적한 `is_partial`·분모 불일치 문제가 원천적으로 생기지 않는다. 실행 절차·수치는 DW-604 resolution에 기록했고, 스펙 `## Verification`에도 동작하는 절차를 정정 주석으로 추가했다. `score_ab.py`에 `doc_hit_recall` 요약 필드를 추가하는 선택지는 **하지 않는다** — 그 지표가 지금 구조상 항상 0이라(DW-607) 요약에 실어도 신호가 없고, 큐리셋이 고쳐지는 시점(DW-609)에 함께 판단하는 편이 낫다.

### DW-609: queryset에 HYBRID 라벨 항목이 애초에 0건이라 "subset 재구성"으로는 AC1을 영구히 관측할 수 없다

origin: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md` 3회차 후속 코드리뷰(2026-07-31)
location: `api/docs/ai-ab-test-queryset.json`(44항목 전체) · `api/scripts/score_ab.py`(`doc_hit` 채점 분기가 `primary == "B"`에만 걸려 있음, 465행)
severity: medium
reason: DW-605는 "명명된 subset 9건이 전부 `primary_path: "B"`"라고, DW-607의 trigger는 "빠진다면 그 5건은 이 지표에서 영원히 무신호이므로 **subset 재구성이 필요하다**"고 적었다. 그런데 이번 리뷰에서 queryset 44항목 **전체**의 `primary_path`를 직접 집계해 보니 항목 단위 A=20·B=9·C=6·멀티턴 9이고, 멀티턴의 턴 단위도 A=16·B=3·C=1이다. 파일 전체에 `HYBRID` 문자열이 0회 등장한다(grep 확인). 즉 **뽑을 HYBRID 항목 자체가 존재하지 않으므로** subset을 다시 고르는 것으로는 이 스토리의 headline 기능(AC1, `hybrid_rag_node`의 가이드 질의확장 FR44)이 A/B 하네스에서 영원히 관측되지 않는다. 이 사실이 기록되지 않으면 DW-605·DW-607을 닫는 세션이 "subset을 다시 골랐다"고 적고도 실제로는 아무것도 달라지지 않은 상태로 항목을 닫게 된다. (참고: 이 리뷰 패스에서 라이브 Gemini로 프롬프트만 따로 실행해 질의확장 자체는 동작함을 관측했다 — 가이드 미주입 시 `price <= 30000000`만, `corpus/02-패밀리카-적합-차종.md` 주입 시 `body_type IN ('준중형차','중형차','SUV','RV') AND price <= 30000000`. 즉 결함이 아니라 **회귀 하네스의 커버리지 공백**이다.)
trigger: DW-604/605의 라이브 검증 세션에서 함께 처리한다 — queryset에 HYBRID 대표 항목을 최소 1~2건 추가하고(예: `"3천만원 이하로 무난한 패밀리카"`에 하이브리드용 `primary_path` 라벨 + `doc_refs: ["02-패밀리카-적합-차종"]` + `predicate`에 price_max와 body_type IN), `score_ab.py`의 `doc_hit` 채점 분기(`primary == "B"`)를 그 라벨까지 포함하도록 넓힌다. 그 전까지 AC1의 유일한 라이브 관측 지점은 `api/tests/test_live_smoke.py::test_live_smoke_hybrid`의 구조조건 로그 단언 하나뿐임을 인정하고, 그 테스트를 반드시 함께 돌린다.
✎ 2026-07-31 사용자 확정(이 항목의 방향을 좁힌다) — ① 이번 증분 RAG 고도화의 목적은 **지식형 질문에 답하는 것이 아니다**. 되묻기·거절을 제외하면 출력은 **매물 답변만**이며, "사고이력 어떻게 확인해?"는 되묻기/거절이 정답이고 "초보운전자 첫차로 뭐가 좋아?"도 되묻기가 적절하다. 즉 13-4 이후 doc_refs 항목이 CLARIFY/REJECT로 흡수된 것은 **회귀가 아니라 의도된 동작**이다(DW-607 resolution이 이를 "더 나쁘다"고 서술했으나, 그 판단은 큐리셋의 옛 전제를 기준으로 한 것이고 제품 의도 기준으로는 정상이다). ② 가이드 문서의 목적은 **매물 추천의 실제 근거로 쓰이는 것**이다 — 이전 구현이 "제목만 붙여 참고한 척"이었던 것을 고치는 게 13-6의 존재 이유였고, 2026-07-31 실측으로 실제 근거 사용이 확인됐다(가이드 거리 0.2550 → `body_type IN ('준중형차','중형차','SUV','RV')` 추출 → 반환 5건 전원 SUV/중형차, 같은 가격대 풀의 경차 8·화물차 3·소형차 3 배제). ③ 따라서 이 항목의 처방은 "subset 재구성"이 아니라 **큐리셋 자체를 더 복잡한(구조조건+의미표현 혼합) 질의로 수정·추가**하는 것으로 확정한다 — 그래야 하이브리드 질의확장이 A/B 하네스에서 관측된다. ④ 착수 시점: **다음 주 토큰 한도 초기화 이후**(2026-07-31 시점 잔여 한도 없음). 13-8(에픽 종료 검증) 착수 **전에** 처리해야 G2 게이트의 `doc_hit`가 무신호를 벗어난다.
✎ 2026-07-31 추가 확정(질의셋 재설계 범위) — ⑤ **기존 항목을 줄여서라도 하이브리드형 질의 수를 늘린다**(사용자 지시). 44항목 유지가 목적이 아니라 4갈래를 고르게 관측하는 것이 목적이다. ⑥ **거절·되묻기가 적절히 나오는지도 충분히 확인 가능한 구성**이어야 한다 — 현재 REJECT 계열은 C1~C6 6건뿐이고, CLARIFY는 **라벨 자체가 없다**(큐리셋은 구버전 `A/B/C` 어휘로만 고정돼 있고 `score_ab._LEGACY_ROUTE_ALIASES`가 `B→CLARIFY`로 번역해 쓰는 중 — 즉 "되묻기가 맞게 발동했는가"를 직접 라벨로 검사하는 항목이 0건이다). ⑦ 따라서 재설계 시 `primary_path`를 **신 4값 어휘(REJECT/CLARIFY/SQL/HYBRID)로 다시 단다** — 번역 계층(`_LEGACY_ROUTE_ALIASES`)에 의존하는 한 DW-573·576·588처럼 "라벨과 실제 동작이 어긋나는" 문제가 계속 재생산된다. ⑧ 기준선(`docs/g2-baseline.json`)은 13-4·13-5 이전(07-30) 캡처라 이미 낡았다 — 재설계와 함께 현재 코드 기준으로 재캡처해야 13-8의 "baseline 이하로 안 떨어짐" 판정이 성립한다(07-31 실측: 같은 질의가 그때는 route B, 지금은 CLARIFY).
status: done 2026-08-02
resolution: 질의셋을 재설계하고 채점기를 확장한 뒤 기준선을 재캡처해 이 항목의 ①~⑧을 전부 이행했다(사용자 지시로 별도 스토리 없이 직접 수행, 2026-08-02).
① **큐리셋 재설계**(`api/docs/ai-ab-test-queryset.json`, 44→47항목/57턴): SQL 16→12 · **HYBRID 0→12**(신설) · **CLARIFY 0→7**(라벨 자체가 처음 생김) · REJECT 6→8(지식형 R7 사고이력·R8 옵션값어치를 gray로 추가 — 사용자 확정대로 거절/되묻기 둘 다 정답) · 멀티턴 9→8(M4를 "되묻기→조건추가→하이브리드" 흐름으로 신설). 라벨은 신 4값 어휘로 전량 재작성했고 구 A/B/C·G 접두사 id는 폐기했다(`--subset`으로 옛 id를 쓰던 명령은 갱신 필요).
② **HYBRID 문항의 정답 설계**: predicate를 "가이드가 제시하는 구조조건까지 반영한 좁혀진 집합"으로 박고 precision으로 채점한다(`score_path_hybrid`) — 가이드를 못 쓰면 같은 가격대의 엉뚱한 차종이 섞여 점수가 떨어지므로 **점수가 곧 FR44의 관측점**이 된다. 재현율을 섞지 않는 이유는 "조건에 맞는 36건 중 상위 5건만 보여주는 것"이 정상 동작이기 때문이다.
③ **번역 계층 제거**(`api/scripts/score_ab.py`): `_LEGACY_ROUTE_ALIASES_SET`·`_require_legacy_paths`를 걷어내고 `ROUTE_LABELS`·`_require_route_labels`로 교체했다 — 이제 구어휘 큐리셋을 먹이면 fail-loud로 거부한다(조용한 0점의 방향만 뒤집힌 재발을 막는다). `route_ok`도 일괄 집합번역 대신 문항별 `acceptable_paths`로만 넓힌다 — 옛 `A→{SQL,HYBRID}` 확장은 "진짜 구조형을 HYBRID로 오분류하는 버그"까지 정답으로 세어 가리고 있었다(당시 문서화된 트레이드오프).
④ **관측 지표 신설**: `doc_hit_n/doc_hit_total`(가이드 인용률)·`clarify_ok_n/clarify_total`(되묻기 발동률)을 **분모까지** 요약과 콘솔에 남긴다 — `0/0`(볼 문항 없음)과 `0/12`(전부 실패)를 같은 "0"으로 읽던 것이 DW-607/609의 뿌리였다. 되묻기는 문구뿐 아니라 **칩 배열이 실제로 담겼는지**까지 본다(러너 `run_phase_b.py`에 `clarify_last`/턴별 `clarify` 캡처를 additive로 추가). 게이트 판정식(오염·dead-end·errored·scored>0)은 건드리지 않았다 — 게이트 조건 변경은 13-8의 판단 몫이다.
⑤ **검사로 못박음**(B9·B4): 신규 채점 경로에 단위테스트 15건을 추가했고, 출고 큐리셋 자체를 검사한다(구어휘 복귀 금지 · 네 갈래 전부 1건 이상 · HYBRID ≥10건 · HYBRID 문항의 predicate/doc_refs 필수 · 존재하지 않는 가이드 stem 금지). **변이 5건으로 red를 실제 확인 후 원복**했다: 하이브리드 채점 precision→F1 되돌리기 / 인용 집계 제거 / 칩 검사 제거 / 되묻기 마커를 옛 문구로 되돌리기 / 큐리셋 H1의 doc_refs 삭제 → 5건 모두 각각 다른 검사가 잡았다. api 스위트 387 passed·84 skipped.
⑥ **기준선 재캡처**(`api/docs/g2-baseline.json`, 라이브 47/47·실패 0): 결과집합정확도 **0.894**(clean SQL+HYBRID n=33) · 라우팅 **54/57** · **가이드 인용 12/13** · **되묻기 발동 9/9** · flaky 0 · 오염 0 · dead-end 0 · **게이트 PASS**. 리포트는 `api/docs/g2-baseline-report.json`. 구 기준선(07-30, 13-4·13-5 이전)은 이 캡처로 대체됐다 — 13-8의 "baseline 이하로 안 떨어짐" 판정이 이제 성립한다.
⑦ **인용률이 12/13인 이유**: 유일한 miss는 H6("2500만원 이하 해치백 있어?")인데, 라우터가 SQL로 분류해 hybrid 경로 자체를 안 탔다(gray 문항이라 결과집합 평균에서는 제외). 이 문항은 "가이드 없이는 못 푸는 질의"를 일부러 넣은 것이라 miss가 정상 관측이다 — 상세는 DW-611.
⑧ 채점 중 드러난 라우터 약점 3건은 **기준선에 그대로 박아 두고**(현재 동작이 곧 기준선이다) 별도 항목으로 넘긴다 — DW-611·DW-612.
남은 것: 없음. 13-8(에픽 종료 검증)이 이 기준선과 도구를 그대로 쓰면 된다.

### DW-611: 최상급만 있는 질의("제일 싼 차 뭐야?")가 SQL이 아니라 CLARIFY로 새고, 같은 뜻의 "가장 비싼 매물 하나 보여줘"는 SQL로 간다

origin: 2026-08-02 기준선 재캡처 실측(DW-609 이행 중)
location: `api/app/graph/router_node.py`(`_SYSTEM_PROMPT` — 최상급/정렬 질의를 담는 갈래가 없다) · 관측 문항 `S6`·`M1.t2`
severity: medium
reason: 재캡처 47/47에서 라우팅 오답 3건 중 2건이 같은 뿌리다. `S6 "제일 싼 차 뭐야?"` → **CLARIFY**(매물 0건, 되묻기 문구), 반면 `S7 "가장 비싼 매물 하나 보여줘"` → **SQL**(1건 정답). 멀티턴에서도 `M1.t2 "제일 싼 거 하나만 알려줘"`(앞선 두 턴에서 SUV·3천만원·서울로 좁힌 상태) → **CLARIFY**로 샜다. 라우터 프롬프트는 갈래를 "명시조건 유무 + 용도·느낌 유무"로만 가르는데 **최상급·정렬 표현(제일 싼/가장 비싼)은 어느 쪽도 아니다.**
✎ 2026-08-02 원인 실측(추측 정정) — 최초 기록은 "'보여줘'류 동사가 붙으면 SQL로 갈리는 것으로 보인다"고 적었으나 **그 가설은 반증됐다**. `router_node`를 변형 12건에 직접 돌린 결과: `제일 싼 차 뭐야?`·`제일 싼 차 보여줘`·`제일 싼 차 알려줘`·`가장 비싼 차 뭐야?` → 전부 **CLARIFY**(동사 무관), `제일 싼 SUV 보여줘`·`가장 비싼 매물 하나 보여줘` → **SQL**. 즉 갈림은 동사가 아니라 **"최상급 말고 다른 구체 조건이 하나라도 있는가"**다 — 차종(SUV)이 있으면 SQL, 최상급 + 일반명사("차"·"거")뿐이면 CLARIFY. 라우터가 최상급을 조건으로 세지 않기 때문이며, S7이 SQL로 간 것은 "매물 **하나**"의 개수 지정이 조건으로 읽힌 것으로 보인다(이 부분은 미확정 추정).
✎ 2026-08-02 함께 드러난 별개 결함 — `contextualize_query("제일 싼 거 하나만 알려줘", <M1의 2턴 맥락>)`이 질의를 **한 글자도 재작성하지 않고 그대로 반환했다**(실측). 즉 REFINE 턴인데 앞선 SUV·3천만원·서울 조건이 독립 질의로 접히지 않았고, 라우터는 조건 없는 문장만 보게 된다 — 이 턴이 CLARIFY로 샌 직접 원인이다. 최상급 규칙을 고쳐도 이쪽을 안 고치면 `M1.t2`의 top-N 채점은 되살아나지 않는다. 같은 스토리에서 함께 다룰 것.
trigger: **Story 13.9(라우팅 안정화 — 최상급·교체요청·맥락재작성)의 인수조건으로 심었다**(2026-08-02, `epics-increment-2026-07-12.md` Epic 13 · `sprint-status.yaml` backlog). 라우터가 최상급·정렬 표현을 구조조건으로 취급하게 하고 `S6`·`M1.t2`가 SQL로 라우팅되는지 재캡처로 확인하며, 맥락 재작성 결함(아래 ✎)도 같은 스토리에서 함께 다룬다. 착수는 13.8 이후다. 그 전까지 이 두 문항의 오답은 기준선(0.894/54·57)에 포함된 상태이며, 고치면 기준선이 **올라가는** 방향이라 13-8의 회귀 게이트를 막지 않는다.
status: done 2026-08-03
resolution: Story 13.9가 처리했다. `router_node._SYSTEM_PROMPT`에 "최상급·정렬 표현(\"제일\"·\"가장\" + 싸다·비싸다 등)은 그 자체로 명시적 구조조건"이라는 규칙과 예시("제일 싼 차 뭐야?"→SQL)를 추가했다(`test_system_prompt_treats_superlatives_as_structural_condition`으로 고정). 별도로 `contextualize_node._REFINE_MARKERS`에 "제일"·"가장"을 추가해 M1.t2류 REFINE 턴이 주제전환으로 오판되던 버그(reason의 ✎ 항목)도 함께 닫았다. **실측 확인(2026-08-03, 라이브 Gemini)**: `contextualize_query("제일 싼 거 하나만 알려줘", <SUV·3천만원·서울 맥락>)` → `"3천만원 이하 서울 지역 SUV 중 가장 저렴한 매물 하나만 알려줘"`로 조건이 실제로 접혔고, 그 재작성 질의를 `router_node()`에 통과시키면 **SQL**로 라우팅됐다 — 재현 확인 완료. `api/docs/ai-demo-queries.md` ⑤절 표를 이 실측값으로 갱신했다. **G2 재기준선 실제 실행으로 최종 확인함**: 라우팅 54/57 → **57/57**, 결과집합정확도 0.894 → **0.954**(하락 없이 개선), 가이드 인용 12/13·되묻기 9/9 유지, 오염 0·dead-end 0, `gate_pass:true`(4축 전부 비하락) — `api/docs/g2-baseline.json`을 이 결과로 교체했다.

### DW-612: 예시를 든 주제전환("아니 쏘렌토 같은 SUV로 바꿔줘")이 CLARIFY로 새서 RESET 오염 게이트가 그 문항에서 무력화된다

origin: 2026-08-02 기준선 재캡처 실측(DW-609 이행 중)
location: `api/app/graph/router_node.py` · `api/app/graph/contextualize_node.py` · 관측 문항 `M6.t1`(`guard_regression: true`)
severity: medium
reason: `M6`는 "차형 교체(준중형→SUV)는 RESET이며 직전 조건이 남으면 오염"을 잡으라고 만든 회귀 문항이다. 재캡처에서 `M6.t0 "아반떼 같은 준중형 보여줘"` → SQL(정답)인데 `M6.t1 "아니 쏘렌토 같은 SUV로 바꿔줘"` → **CLARIFY**(매물 0건)로 샜다. `score_ab.score_model`의 하드 오염 게이트는 `route in ("SQL","HYBRID")`일 때만 발화하므로(CLARIFY/REJECT에서 같은 차종이 떠도 그건 의미검색의 우연이지 조건 잔존이 아니라는 기존 판단), **이 문항은 지금 오염을 볼 수 없다** — 게이트가 초록인 것이 "오염이 없다"가 아니라 "안 보고 있다"는 뜻인 상태가 M6에 한해 재현됐다(DW-607이 doc_hit에서 겪은 것과 같은 구조). 다행히 같은 부류의 `M3`(중형세단→초보 첫차)는 의도대로 CLARIFY가 정답이라 영향이 없고, `M7`(페이지네이션)·`M8`(금융 거절)은 정상 관측된다.
✎ 2026-08-02 원인 실측 — `router_node` 변형 실행 결과 `SUV로 바꿔줘` → **SQL**, `SUV 보여줘` → **SQL**, `아반떼 같은 준중형 보여줘` → **SQL**인데 `쏘렌토 같은 SUV로 바꿔줘` → **CLARIFY**, `아니 쏘렌토 같은 SUV로 바꿔줘` → **CLARIFY**다. 즉 "차명 예시(`X 같은`)"만으로 갈리는 것도, "바꿔줘"만으로 갈리는 것도 아니다(`아반떼 같은 준중형 보여줘`가 SQL이고 `SUV로 바꿔줘`도 SQL이다) — **같은 형태의 질의가 조합에 따라 다르게 분류되는 불안정**이며, 재현 가능한 단일 규칙으로 설명되지 않는다. 프롬프트가 이 형태를 다루는 예시를 갖고 있지 않아 LLM 판단이 표면 표현에 흔들리는 것으로 본다. 또한 `contextualize_query`는 이 턴을 재작성 없이 그대로 반환했다(RESET 턴이므로 조건을 안 넘기는 것 자체는 옳다 — DW-611의 REFINE 사례와 달리 여기선 결함이 아니다). 덧붙여 `SUV`는 명백한 구조조건이므로 되묻기는 측정 문제 이전에 **제품 동작으로도 아쉽다**(사용자가 조건을 줬는데 다시 묻는다).
trigger: **Story 13.9(라우팅 안정화)의 인수조건으로 심었다**(2026-08-02, DW-611과 같은 스토리) — "아니 …로 바꿔줘"처럼 **명시 차종이 들어 있는 교체 요청**이 SQL로 가도록 규칙·예시를 보강하고, `M6.t1`이 SQL로 라우팅돼 오염 게이트가 실제로 발화 가능한 상태가 되는지 확인한다(발화 가능 = 일부러 오염 데이터를 넣었을 때 red가 되는지까지 본다, B4). 그 전까지 `M6`의 오염 커버리지는 없는 것으로 간주한다.
status: done 2026-08-03
resolution: Story 13.9가 처리했다. `router_node._SYSTEM_PROMPT`에 교체요청 규칙("~같은 ~로 바꿔줘"류는 명시 조건만 있으면 SQL, 느낌이 섞이면 HYBRID — 13.2 4분기 계약이 상위)과 대조 예시 두 쌍(`"아니 쏘렌토 같은 SUV로 바꿔줘"→SQL`, `"가족이 타기 좋은 SUV로 바꿔줘"→HYBRID`)을 추가했다(`test_system_prompt_routes_replacement_requests_by_condition_presence`로 고정). **실측 확인(2026-08-03, 라이브 Gemini)**: `router_node("아니 쏘렌토 같은 SUV로 바꿔줘")` → **SQL**(재현 전 CLARIFY였던 것과 대비), `router_node("가족이 타기 좋은 SUV로 바꿔줘")` → **HYBRID**(13.2 계약대로 느낌 섞인 교체요청은 HYBRID로 유지됨을 함께 확인). RESET 오염 게이트가 이제 M6.t1에서 실제로 발화 가능한 상태(route=SQL)가 됐고, **일부러 오염 데이터를 주입해 실제로 검증**했다 — M6.t1(SUV 전용 턴) 결과 id 목록에 준중형차 매물 1건을 인위로 추가한 뒤 채점하니 `오염(하드): 1`·`게이트: FAIL`로 실제 red가 됐다(임시 파일로만 실험, 실제 캡처는 원상태 유지). 존재 확인이 아니라 작동 확인까지 마쳤다(B4).

### DW-610: Follow-up review still recommended for 13-6-가이드-문서-content-활용-거리-컷오프 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-6-가이드-문서-content-활용-거리-컷오프.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260731-180320-15df; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-613: Story 13.9 초안(epic-13-context.md·epics-increment)에 DW-611/612가 안 덮는 인접 엣지케이스 6건이 남아있다

origin: 2026-08-02, 13-7-langsmith-트레이싱 리뷰 패스(edge-case-hunter 렌즈) — epic-13-context.md 재캡파일이 이번 diff에 포함되면서 곁다리로 발견됨. LangSmith 트레이싱과는 무관하고, 전적으로 Story 13.9(라우팅 안정화) 초안의 완성도 문제.
source_spec: `epic-13-context.md`(요건 문단) · `epics-increment-2026-07-12.md`(Epic 13, Story 13.9)
severity: low
reason: Story 13.9 AC가 다루는 "최상급·교체요청·맥락재작성" 범주 안에서, DW-611(가격 최상급)·DW-612(명시 차종 교체)가 좁게 실측·확정한 케이스의 인접 변형이 AC 문구에 아직 안 잡혀 있다 — 각각 실측 없이 발견됐으므로 재현 확인 전까지는 "다뤄야 할 후보"로만 취급한다.
  1. 가격처럼 정렬 가능한 컬럼이 없는 주관적 최상급("제일 좋은 차")이 구조조건인지 되묻기인지 AC에 없음.
  2. 차종을 명시하지 않은 교체 요청("다른 거 보여줘")의 기대 라우팅이 AC에 없음(DW-612는 차종이 명시된 경우만 다룸).
  3. RESET 오염 게이트의 반대 방향(정상 세션을 오탐 차단하는 경우)이 AC 검증 항목에 없음(DW-612는 게이트가 안 걸리는 방향만 다룸).
  4. `contextualize_query`가 예외 없이 "성공"하지만 조건을 잘못 접어넣는 경우(DW-611은 "재작성을 안 함" 케이스만 다룸)의 폴백 조건이 AC에 없음.
  5. epic-13-context.md의 "13.9는 13.8 완료 후 착수" 문구가 "13.8 스토리 종료"와 "13.8이 요구하는 G2 게이트 통과" 중 무엇을 뜻하는지 모호함.
  6. 13.9 완료 후 재캡처한 기준선이 13.8의 G2 게이트 재실행에서 다시 불합격하면 다음 행동(재작업·롤백·에픽 보류)이 문서에 없음.
trigger: **Story 13.9 step-02 planning(스펙 초안 작성) 시** 위 6항목을 인수조건 후보로 검토한다 — 13.9는 13.8 완료 후에만 착수하므로 그 전까지는 열어만 둔다.
✎ 2026-08-03 해소(오케스트레이터) — 이 항목이 지적한 사항을 `epics-increment-2026-07-12.md`의 **Story 13.9 본문에 직접 반영**했다(초안 정리, 커밋은 아래 참조). 장부에 처방만 적어두면 step-02 planning이 그걸 읽지 않을 수 있으므로, 구현자가 반드시 읽는 스토리 문서 자체를 고쳤다.
status: done 2026-08-03
resolution: Story 13.9 초안을 직접 수정해 해소했다 — G2 자기참조를 2단계 판정(이전 기준선으로 판정 → 통과 후에만 갱신)으로 교체, 교체요청의 사분면 귀속을 "의미조건이 섞이면 HYBRID"로 확정(13.2 계약과의 충돌 제거), 성립 불가한 "결정론 단위테스트가 프롬프트 흔들림을 잡는다" 요건 삭제 후 "코드가 판정하는 부분만 결정론 고정 + 프롬프트 흔들림은 라이브 재캡처가 잡는다"로 교체, 추출-후-분기 대안의 REJECT 붕괴·SQL/HYBRID 경계 공백을 Design Notes에 경고로 명시, 최상급×HYBRID 정렬 충돌(sql_guard 2차 정렬키 차단)을 결정 항목으로 등재, RESET 오염 데이터 teardown을 인수조건화, 에픽 착수·종료 조건을 명문화, 승격 안 한 인접 케이스 6건을 "명시적으로 판단하고 이유를 적을 것"으로 남겼다.

### DW-614: Story 13.9 초안에 "적힌 내용 자체가 성립하지 않는" 논리 결함 7건이 있다

origin: 2026-08-02, 13-7-langsmith-트레이싱 **후속 리뷰 패스**(adversarial·edge-case-hunter 렌즈 독립 수렴) — epic-13-context.md 재캡파일이 diff에 포함되며 발견. LangSmith와 무관.
source_spec: `epic-13-context.md`(Requirements·Technical Decisions·Dependencies) · `epics-increment-2026-07-12.md`(Epic 13, Story 13.9)
severity: medium
reason: DW-613과 **층위가 다르다** — DW-613은 "AC가 안 다룬 인접 케이스"(빠진 것)이고, 이 항목은 "문서에 적힌 지시가 서로 모순되거나 실행하면 목적을 배반하는 것"(틀린 것)이다. 중복 없음.
  1. **G2 재실행이 자기참조라 항상 통과한다.** "완료 시 기준선을 재캡처해 13.8의 G2 게이트를 다시 실행해 통과를 확인한다"는 순서상, 변경 후 코드로 캡처한 기준선과 변경 후 코드를 비교하게 된다 — 회귀가 얼마든 나도 동률이라 통과. 에픽의 유일한 회귀 게이트가 하필 그걸 가장 깨기 쉬운 스토리에서 무력화된다. (DW-613 #6은 "재캡처 후 불합격 시 행동 부재"만 다뤄 이 반대 갈래를 안 덮는다.)
  2. **"조건 추출 우선" 대안 구조를 택하면 REJECT 분기가 붕괴한다.** 무관/법적 질의는 정의상 구조조건이 0개라 "추출 실패=되묻기" 규칙에서 CLARIFY로 떨어진다 — 같은 문장이 지키라고 못박은 13.2 4분기 인수조건과 `test_live_smoke_pathC`(route==REJECT)를 동시에 깬다.
  3. **같은 대안 구조에서 SQL/HYBRID 경계가 미정의다.** "추출 실패=되묻기" 한 갈래만 정의하고, 추출 성공 이후 두 갈래를 가르는 기준이 없다(4분기 중 2개의 경계가 빈다).
  4. **최상급 × 하이브리드는 정렬을 표현할 자리가 없다.** 요건은 최상급을 "구조조건으로 SQL 라우팅"까지만 규정하는데, 의미조건이 섞이면 HYBRID이고 그 경로의 `ORDER BY`는 벡터 거리절이 점유한다. `api/app/db/sql_guard.py`(L266~275, DW-555 근거 주석)가 2차 정렬키(`... ::vector, price`)를 **명시적으로 차단**한다 — 실물 확인함. "제일 싼 패밀리카"류에서 최상급이 조용히 버려질 수 있다.
  5. **에픽 종료조건이 재정의되지 않았다.** 13.8이 "exit-gate(G2 미통과 시 에픽 종료 불가)"인데 13.9가 그 뒤로 배치됐다 — 이제 무엇이 종료 판정인지 문서에 없다. (DW-613 #5는 "13.9 *착수* 시점"의 모호함이고, 이건 "에픽 *종료* 시점".)
  6. **"결정론적 단위테스트가 프롬프트 흔들림을 먼저 잡는다"는 요건이 성립 불가.** api 단위테스트의 표준은 LLM을 fake로 교체하는 것(project-context 규칙 12)이라 fake 응답은 프롬프트 변경에 반응하지 않는다. 트리거 조건이 정의상 발동하지 않는 검사를 요건이 요구하고 있다.
  7. **RESET 오염 데이터의 정리·격리가 미규정.** "실제 오염 데이터를 넣어 검사가 실패로 잡히는지 확인"만 있고 teardown이 없다 — 같은 에픽이 공용 DB에서 G2 기준선을 재캡처하므로 잔존 행이 그 캡처에 섞인다.
trigger: **Story 13.9 step-02 planning(스펙 초안 작성) 시** 위 7항목을 먼저 해소한다 — 특히 1번은 스펙에 "G2는 13.9 이전 기준선으로 판정하고, 통과한 뒤에만 기준선을 갱신한다"는 두 단계 순서로 못박아야 한다.
✎ 2026-08-03 해소(오케스트레이터) — 이 항목이 지적한 사항을 `epics-increment-2026-07-12.md`의 **Story 13.9 본문에 직접 반영**했다(초안 정리, 커밋은 아래 참조). 장부에 처방만 적어두면 step-02 planning이 그걸 읽지 않을 수 있으므로, 구현자가 반드시 읽는 스토리 문서 자체를 고쳤다.
status: done 2026-08-03
resolution: Story 13.9 초안을 직접 수정해 해소했다 — G2 자기참조를 2단계 판정(이전 기준선으로 판정 → 통과 후에만 갱신)으로 교체, 교체요청의 사분면 귀속을 "의미조건이 섞이면 HYBRID"로 확정(13.2 계약과의 충돌 제거), 성립 불가한 "결정론 단위테스트가 프롬프트 흔들림을 잡는다" 요건 삭제 후 "코드가 판정하는 부분만 결정론 고정 + 프롬프트 흔들림은 라이브 재캡처가 잡는다"로 교체, 추출-후-분기 대안의 REJECT 붕괴·SQL/HYBRID 경계 공백을 Design Notes에 경고로 명시, 최상급×HYBRID 정렬 충돌(sql_guard 2차 정렬키 차단)을 결정 항목으로 등재, RESET 오염 데이터 teardown을 인수조건화, 에픽 착수·종료 조건을 명문화, 승격 안 한 인접 케이스 6건을 "명시적으로 판단하고 이유를 적을 것"으로 남겼다.

### DW-615: langchain 계열 버전이 안 고정돼 있어, 자동 계측이 조용히 깨질 수 있고 그걸 잡을 검사는 CI에서 안 돈다

origin: 2026-08-02, 13-7-langsmith-트레이싱 후속 리뷰 패스(verification-gap·adversarial 렌즈) — Story 13.7이 추가한 트레이싱 회귀 테스트가 "실제로는 아무것도 자동으로 지키지 못한다"는 지적에서 나온 근본 원인. Story 13.7 자체의 결함이 아니라 저장소 전반의 의존성 정책 문제.
source_spec: `api/requirements.txt` · `api/pyproject.toml` · `api/Dockerfile` · `.github/workflows/tests.yml`
severity: medium
reason: 실물 확인함 — (a) `langchain-google-genai`가 두 매니페스트 모두에서 **버전 무고정**이고 `langsmith`는 아예 미선언(`langchain-core`의 전이 의존 `langsmith<1.0.0,>=0.3.45`로만 들어온다), (b) `api/Dockerfile`은 `pip install --no-cache-dir -r requirements.txt`라 **컨테이너를 다시 빌드할 때마다 재해석**된다, (c) 저장소에 커밋된 `api/uv.lock`은 CI·Dockerfile·스크립트 어디에서도 쓰이지 않는다(`uv sync`/`uv pip`/`uv.lock` 전체 검색 0건). 즉 LangSmith 자동 계측(FR51)이 의존성 업그레이드로 끊겨도 배포는 초록으로 통과하고, 유일한 검사(`test_live_smoke_langsmith_tracing`)는 라이브·과금 테스트라 CI에서 의도적으로 안 돈다(project-context 규칙 12 — 이 절충 자체는 유지가 맞다).
trigger: **다음번 api 의존성 작업(패키지 추가·업그레이드) 또는 Cloud Run 재배포 준비 시.** 선택지: langchain 계열 3종을 핀 고정하거나, `uv.lock`을 CI·Dockerfile에 실제로 배선한다. 둘 다 안 할 거면 "재빌드마다 계측이 갈릴 수 있음"을 배포 런북에 명시한다.
status: open

### DW-616: 루트/api `.env.example` 락스텝이 "관례"로만 존재하고 검사로 강제되지 않는다

origin: 2026-08-02, 13-7-langsmith-트레이싱 후속 리뷰 패스(adversarial·verification-gap 렌즈) — 두 번의 리뷰 패스가 "두 파일 주석 복붙" 지적을 **"의도된 락스텝 관례"라는 근거로 기각**했는데, 정작 그 락스텝을 지키는 장치가 없다는 것이 드러남.
source_spec: `.env.example` · `api/.env.example`
severity: low
reason: CLAUDE.md B9("지켜야 하는 규칙이면 실행되는 검사로 바꾼다") 위반. 두 파일은 이미 문구·경로(`source api/.env` vs `source .env`)·배치가 다르므로 단순 동일성 비교로는 안 되고, **키 이름 집합의 일치**를 보는 검사여야 한다. 이 스토리가 만든 검사들과 달리 이 검사는 secrets·네트워크 없이 CI(api 잡)에서 실제로 돌 수 있는 유일한 종류다. 실패 모드는 "트레이싱을 설정했는데 트레이스가 안 남는다" — 이 스토리가 없애려던 바로 그 함정이다.
trigger: **`.env.example`에 키를 추가·변경하는 다음 스토리 착수 시** 파리티 테스트(`api/tests/`에 루트 견본의 api 섹션 키 집합 == `api/.env.example` 키 집합 단언)를 함께 넣는다.
status: open

### DW-617: Story 13.9 초안에 라우팅 사분면 충돌·맥락 재작성 경계 2건이 더 있다

origin: 2026-08-02, 13-7-langsmith-트레이싱 **3차 리뷰 패스**(edge-case-hunter 렌즈) — epic-13-context.md 재캡파일이 이번 diff에 포함되며 발견. LangSmith와 무관.
source_spec: `epic-13-context.md`(Requirements, 13.9 라우팅 요건 2개 문단)
severity: low
reason: DW-613(AC가 안 다룬 인접 케이스)·DW-614(적힌 지시가 성립하지 않음)와 층위가 또 다르다 — 이건 **새 요건 두 문장이 각각 기존 계약과 충돌하거나 경계를 안 정한 것**이다.
  1. **교체 요청 + 의미조건이 겹치면 어느 사분면인가.** 새 요건은 "명시 차종이 든 교체 요청은 SQL로 라우팅되어야 한다"를 무조건으로 적었는데, 13.2의 4분기 계약은 구조조건+의미조건이 섞이면 HYBRID다. "가족이 타기 좋은 SUV로 바꿔줘"가 두 규칙을 동시에 만족하며 서로 다른 답을 낸다. 같은 문단이 "13.2의 4분기 인수조건은 깨지 않아야 한다"고 못박아 둔 터라 구현자는 둘 중 하나를 반드시 어긴다. (DW-614 #4는 HYBRID **안에서의 정렬 표현** 문제라 이 사분면 귀속 문제와 다르다.)
  2. **이어받을 조건이 없는 턴·조건 폐기 규칙이 없다.** 새 요건은 `contextualize_query`가 "이전 조건을 접어 넣는" 방향만 정의한다. (a) 직전 턴이 CLARIFY/REJECT라 확정 조건이 0개인 상태 — `run_search`가 context를 무조건 넘기므로 실제로 도달 가능한 상태다(`api/app/graph/graph.py` 확인), (b) 같은 축을 다시 명시하는 후속 질의("아니 5천만원대로")에서 이전 값을 **누적할지 대체할지**가 미정의다. DW-613 #4는 "재작성이 성공하지만 잘못 접어넣는" 폴백 얘기라 이 두 갈래를 안 덮는다.
trigger: **Story 13.9 step-02 planning(스펙 초안 작성) 시** DW-613·614와 함께 검토한다 — 특히 1번은 "교체 요청도 의미조건이 섞이면 HYBRID"인지 아닌지를 인수조건에 한 줄로 확정해야 구현자가 계약을 안 어긴다.
✎ 2026-08-03 해소(오케스트레이터) — 이 항목이 지적한 사항을 `epics-increment-2026-07-12.md`의 **Story 13.9 본문에 직접 반영**했다(초안 정리, 커밋은 아래 참조). 장부에 처방만 적어두면 step-02 planning이 그걸 읽지 않을 수 있으므로, 구현자가 반드시 읽는 스토리 문서 자체를 고쳤다.
status: done 2026-08-03
resolution: Story 13.9 초안을 직접 수정해 해소했다 — G2 자기참조를 2단계 판정(이전 기준선으로 판정 → 통과 후에만 갱신)으로 교체, 교체요청의 사분면 귀속을 "의미조건이 섞이면 HYBRID"로 확정(13.2 계약과의 충돌 제거), 성립 불가한 "결정론 단위테스트가 프롬프트 흔들림을 잡는다" 요건 삭제 후 "코드가 판정하는 부분만 결정론 고정 + 프롬프트 흔들림은 라이브 재캡처가 잡는다"로 교체, 추출-후-분기 대안의 REJECT 붕괴·SQL/HYBRID 경계 공백을 Design Notes에 경고로 명시, 최상급×HYBRID 정렬 충돌(sql_guard 2차 정렬키 차단)을 결정 항목으로 등재, RESET 오염 데이터 teardown을 인수조건화, 에픽 착수·종료 조건을 명문화, 승격 안 한 인접 케이스 6건을 "명시적으로 판단하고 이유를 적을 것"으로 남겼다.

### DW-618: Follow-up review still recommended for 13-7-langsmith-트레이싱 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-7-langsmith-트레이싱.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260802-165936-4495; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-08-03
resolution: 독립 후속 리뷰를 실제로 수행했다(2026-08-03, 새 세션·opus, 커밋 `6e427e7`). 3차 패스가 고쳤다고 주장한 high 2건(노드 스팬 이중 계수·견본의 틀린 우선순위 주장)을 **라이브와 돌연변이 양쪽으로 재현해 실제로 고쳐져 있음을 확인**했다 — 그래프 노드 스팬만 제거하면 라이브 테스트가 FAILED가 되어 초록을 얻을 수 없다. 이번 패스가 새로 찾은 것: ① env 계약 검사에 "빈 값·공백은 미설정으로 보고 다음 후보로 내려간다" 규칙을 지키는 검사가 없었다(가짜 SDK를 끼워도 10건 전부 초록 — 3차가 잡은 "한 갈래를 두 번 세기"와 같은 종류) → 검사 신규 추가. ② DW-616이 적어둔 해법(두 `.env.example`의 키 집합 일치 단언)은 그대로 쓰면 첫 실행부터 red다(`api/.env.example`에만 `CORS_ORIGINS`·`CORS_ORIGIN_REGEX` 2개가 더 있음 — 루트 9 vs api 11 실측) → 측정된 비대칭 2건을 **동결**하는 양방향 파리티 검사로 대체. ③ 스펙 `## Verification` 3번 명령이 새 셸에서 401로 죽었다(앞 명령의 `source .env`가 남아 있다는 숨은 전제 — 이 스토리가 없애려던 "파일에 값이 있음 ≠ 프로세스에 노출됨" 함정 그 자체) → 명령 정정. 테스트 399→**402 passed**·85 skipped, 회귀 0. 리뷰 판단은 "추가 패스 불필요"이며 남은 low 2건은 DW-641로 13.9에 묶었다. 이 항목을 닫는다.

### DW-619: `docs/conventions.md` §6 FR11 강제 지점 목록에 하이브리드 벡터검색(`hybrid_rag_node`)이 등록되지 않았다

origin: story 13-8(RAG exit-gate 검증) 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 conventions.md §6 원문으로 확인
location: `docs/conventions.md`(§6 "매물 축" 불릿, 140~145줄) · `api/app/graph/hybrid_rag_node.py`(코드 자체는 `WHERE status='on_sale'`을 실제로 강제하고 있음 — 실측 결함 아님, 등록 누락)
severity: medium
reason: `project-context.md` 규칙7은 "새 조회 경로를 열면 §6의 강제 지점 목록에 반드시 함께 등록한다"고 명시하는데, §6의 "매물 축" 불릿은 여전히 RLS·`sql_guard.py`·문서 RAG 필터 3곳만 나열한다. `hybrid_rag_node`는 13.1~13.3(2026-07-30~31)이 이미 만든, 4번째로 늘어난 FR11 강제 지점인데 그때도 지금(13.8)도 이 목록에 오르지 않았다 — 정확히 규칙7이 경고하는 실패 모드이자, §6 자신이 9.4/9.5/9.6 이미지 축에서 겪었던 것과 같은 종류의 누락(148줄 "이 목록에 한 번도 오른 적이 없었다" 사례와 동형)이다. 코드 자체는 정상 작동한다(13.8의 CM-B 라이브 검증으로 확인) — §6만 읽는 다음 사람이 이 강제 지점의 존재를 모른다는 것이 문제다.
trigger: `docs/conventions.md`를 다음에 손댈 때, 또는 §6을 참조해 새 AI 검색/조회 경로를 여는 다음 스토리 착수 시 — "매물 축" 불릿에 `hybrid_rag_node`(`api/app/graph/hybrid_rag_node.py`, 코드가 `WHERE status='on_sale'` 절을 템플릿으로 붙임, 강제 장치: `api/tests/test_hybrid_rag_node.py`)를 추가한다.
status: done 2026-08-03
resolution: Story 13.9가 `docs/conventions.md` §6 "매물 축" 불릿에 `hybrid_rag_node`(코드가 `WHERE status = 'on_sale'` 절을 템플릿으로 붙임, 강제 장치 `api/tests/test_hybrid_rag_node.py`)를 추가했다. 이제 §6이 FR11 매물 축 강제지점 4곳(RLS·sql_guard·문서 RAG 필터·하이브리드)을 전부 나열하는 정본이 됐다 — DW-625가 요구한 "로스터를 §6에서 뽑는다" 전제가 성립한다.

### DW-620: `epic-13-context.md`(및 상위 계획 문서)의 "가이드 문서 12개"가 실제 활성 코퍼스(10개)와 어긋난다

origin: story 13-8(RAG exit-gate 검증) 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 `api/corpus/` 디렉터리로 실측 확인
location: `_bmad-output/implementation-artifacts/epic-13-context.md`(Requirements) · `api/corpus/`(활성 10개, `_excluded/`에 2개: `08-할부-리스-현금-비교`·`09-보험-세금-기초`) · `api/scripts/score_ab.py`(`DOC_STEM_TO_TITLE` 채점 맵도 10개 항목)
severity: low
reason: "12개"라는 수치는 13.8 이전부터(적어도 13.1~13.6 시점부터) 계획 문서·epic 컨텍스트에 반복돼 온 것으로, 13.8의 diff가 새로 만든 오차가 아니다 — epic-13-context.md 재컴파일(13.8 step-01)도 원본 그대로 옮겼을 뿐이다. 실제로 `doc_rag_node`/`hybrid_rag_node`가 로드하는 코퍼스는 10개뿐이고, 채점 도구의 인용 매핑도 10개와 일치한다. 같은 문단이 청킹 도입 임계값을 "문서 ≥20개"로 적어 두므로, 활성 문서 수를 정확히 아는 게 그 임계값과의 거리 판단에 실질적으로 영향을 준다.
trigger: 가이드 코퍼스 문서를 추가·제외하는 다음 작업(corpus/ 디렉터리를 손대는 스토리) 착수 시 — 그때 "12개"를 "10개(활성) / 12개(전체, 2개 제외)"로 명확히 하거나, `_excluded/`의 2개를 아예 코퍼스 계획에서 제외 확정한다.
✎ 2026-08-03 trigger 재지정(오케스트레이터) — 위 trigger가 가리키는 "다음 스토리"가 백로그에 실재하지 않아 영영 발화하지 않는다는 지적(DW-640)에 따라, **Story 13.9(라우팅 안정화)의 인수조건으로 재지정**한다. 13-9는 `sprint-status.yaml`에 실재하는 backlog 스토리이며, 해당 인수조건을 실제로 심었다(B8: 지정한 곳에 실제로 심는다).
status: done 2026-08-03
resolution: Story 13.9가 `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`의 "가이드 문서 12개" 3곳(FR48, Story 13.6 AC 2곳)을 "활성 10문서, 전체 12개 중 2개는 `_excluded/`"로 정정했다(`api/corpus/`에 활성 10개 + `_excluded/`에 2개 실측 확인, `ls` 결과와 일치). `epic-13-context.md`에는 현재 이 수치가 없어(재확인 결과 이미 사라진 상태) 추가 정정이 불필요했다.

### DW-621: G2 exit-gate는 실행된 형태상 "회귀 검사"가 아니라 "재현성 검사"다

origin: story 13-8(RAG exit-gate 검증) **후속 리뷰** — adversarial·verification-gap·intent-alignment 세 렌즈가 독립적으로 같은 결론, 오케스트레이터가 두 캡처 파일 per-item 대조로 확인
location: `api/docs/g2-baseline.json` ↔ `api/docs/g2-exit-gate-2026-08-02.json` · `api/scripts/score_ab.py`(`regression = candidate.result_mean < baseline.result_mean`) · `_bmad-output/implementation-artifacts/epic-13-context.md`(게이트 정의: "G2(회귀 — Phase B baseline 이하로 떨어지면 실패)")
severity: medium
reason: 에픽 정의상 G2는 "13.1~13.7이 품질을 떨어뜨리지 않았음"을 증명하는 회귀 게이트다. 그런데 비교 대상 baseline은 DW-609가 2026-08-02에 **이미 13.6까지 들어간 코드**로 뜬 것이라, 후보 캡처와 baseline이 **같은 코드 상태**다. 실측: 두 파일의 47개 항목이 `latency_ms`를 빼면 바이트 단위로 동일하고, `git log --since=2026-08-02 -- api/app`은 커밋 0건이다. 즉 `regression_block:false`는 구조적으로 참일 수밖에 없고, 13.1~13.7이 실제로 만든 품질 변화는 양쪽에 똑같이 녹아 있어 이 게이트가 원리적으로 볼 수 없다. 13.8 스펙의 Design Notes는 이 사실을 이미 정직하게 적어 뒀다("어제 캡처와 오늘 재캡처의 재현성 확인이 G2의 실질") — 문제는 **에픽 레벨 게이트 문구는 여전히 "회귀"**라, 이 문서만 읽는 사람은 에픽이 회귀 증거 위에서 닫혔다고 믿는다. 13.8이 만든 결함이 아니라 baseline이 늦게 심긴 데서 온 선재 조건이다(그래서 defer). 재현성 확인 자체는 무가치하지 않다 — 라우팅이 비결정적으로 흔들리지 않음을 증명한다.
trigger: **Story 13.9 완료 후 기준선을 재캡처할 때** — 13.9는 어차피 baseline을 다시 떠야 하므로(epic-13-context.md Cross-Story Dependencies) 그 자리가 정확히 이 결정을 내릴 지점이다. 그때 (a) 13.9 이전 코드로 뜬 캡처를 baseline으로 고정해 진짜 "이전 vs 이후" 비교를 만들거나, (b) 만들 수 없으면 에픽 게이트 문구를 "재현성"으로 정정해 무엇이 증명됐고 무엇이 안 됐는지를 문서가 정직하게 말하게 한다.
status: open

### DW-622: 스킵된 보안 테스트가 통과와 구별되지 않는다 — 환경변수 이름 하나로 게이트가 조용히 사라진다

origin: story 13-8(RAG exit-gate 검증) **후속 리뷰** — adversarial 렌즈가 발견, 오케스트레이터가 스펙에 적힌 커맨드를 그대로 재실행해 재현
location: `api/tests/integration/*_real_db.py`(가드 변수 = `TEST_DATABASE_URL`) · `api/tests/test_readonly.py`(가드 변수 = `DATABASE_URL`) · `.github/workflows/tests.yml`(`api-db` 잡만 `TEST_DATABASE_URL`을 준다)
severity: medium
reason: 13.8은 CM-B(보안 게이트)를 "실DB로 확인했다"고 기록했지만, 스펙에 적힌 커맨드가 `test_fr11_cover_images_real_db.py`에 `DATABASE_URL`을 넘겼다 — 이 파일이 보는 변수는 `TEST_DATABASE_URL`이라 실제로는 `1 skipped`였고, pytest 종료코드가 0이라 초록으로 읽혔다. 같은 이유로 `test_readonly.py`(ai_readonly 롤 격리) 2건도 스킵된 채 "147 passed, 2 skipped"로 통과 보고됐다. **커맨드는 이번 후속 리뷰에서 고쳤고 세 축 전부 실제로 돌려 green을 확인했다**(FR11 실DB 1 passed · ai_readonly 2 passed · SECURITY DEFINER 5 passed) — 그러나 고친 건 이 스토리의 커맨드 한 줄뿐이고, **"보안 테스트가 스킵되면 눈에 띈다"는 구조적 보장은 여전히 없다.** 두 종류의 실DB 테스트가 서로 다른 변수명을 쓴다는 것 자체가 다음 사람에게 같은 함정을 다시 놓는다. CLAUDE.md B9("규칙은 어길 수 없는 자리에 박는다") 위반이다.
trigger: **api 테스트 실행 방식이나 CI 잡을 다음에 손댈 때** — 두 변수명을 하나로 합치거나(하나가 다른 하나를 fallback으로 읽게), 보안 표식(`@pytest.mark.security`)이 붙은 테스트가 스킵되면 스위트를 실패시키는 conftest 훅을 넣는다. 최소한 로컬 실행 문서에 두 변수를 모두 적는다.
status: open

### DW-623: DW-576의 `status:` 값이 sweep 파서 문법 밖이라 장부에서 조용히 사라질 수 있다

origin: story 13-8(RAG exit-gate 검증) **후속 리뷰** — adversarial·edge-case 두 렌즈가 독립 발견
location: `_bmad-output/implementation-artifacts/deferred-work.md`(DW-576 블록의 `status:` 줄, 그리고 같은 블록의 `trigger(갱신):` 줄) · `.claude/skills/bmad-loop-sweep/deferred-work-format.md`(문법 정의) · `.claude/skills/bmad-loop-sweep/automation-mode.md`
severity: medium
reason: 13.8이 DW-576을 부분 종결하며 `status: open (부분 해소, 2026-08-02)`로 적었다. 장부 전체에서 이 값 하나만 문법 밖이다(나머지는 전부 `open` 또는 `done <날짜>`). sweep 스킬은 "`status:` 줄이 `open`인 블록"을 고르고, automation-mode는 "open_ids가 장부의 `status: open` 항목과 **정확히** 일치해야 한다"고 요구한다 — 어긋나면 결과 전체가 무효가 되고 재시도를 태운다. 즉 DW-576(회색지대 route가 `_patch_route`로 강제 주입돼 SM3가 실제 라우팅을 보장하지 못하는 **구조적** 결함)이 열린 것도 닫힌 것도 아닌 상태로 빠질 수 있다. 같은 블록에 `trigger:`와 `trigger(갱신):`가 둘 다 있는 것도 표준 키 하나 원칙에서 벗어난다. **이 항목을 직접 고치지 않은 이유**: 이번 실행의 지시가 "기존 장부 항목은 수정·재개봉·재작성하지 말고 신규만 추가하라"였다 — 기존 항목의 상태·해소는 오케스트레이터 소관이다.
trigger: **오케스트레이터가 다음 sweep을 돌리기 전** — DW-576의 `status:`를 `open`으로 되돌리고 "부분 해소(2026-08-02)"는 본문 주석(`✎`)으로 옮기며, `trigger(갱신):`을 표준 `trigger:` 한 줄로 합친다.
status: open

### DW-624: 13.8 diff가 기존 장부 항목 6건의 사실관계를 바꿨는데 그 항목들이 갱신되지 않았다

origin: story 13-8(RAG exit-gate 검증) **후속 리뷰** — adversarial·edge-case 렌즈 발견, 오케스트레이터가 각 항목 원문과 코드로 대조
location: `_bmad-output/implementation-artifacts/deferred-work.md` — DW-573 · DW-577 · DW-590 · DW-556 · DW-564 · DW-565
severity: low
reason: 세 갈래다. (1) **트리거가 실제로 발동했는데 기록이 없다** — DW-573의 트리거는 "`api/docs/ai-demo-queries.md`를 손대는 다음 작업 시"인데 13.8이 바로 그 파일을 다시 썼고 신어휘 이관도 절반 했지만 항목은 손대지 않은 채 `open`이다(남은 절반: 소비처 0인 죽은 상수 `DEMO_QUERIES`, `docs/learning/06-file-reference.md`의 "단일 출처" 표현). DW-590도 "DW-573/576을 다루는 같은 작업"을 트리거로 적었는데 그 작업이 일어났고 세 항목 전부 미이행이다. (2) **적힌 사실이 이제 거짓이다** — DW-577은 "`test_live_smoke.py`에 `out['route']` 단언 0건, 'HYBRID' 등장 0회"라고 적었는데 현재 그 파일은 SQL/CLARIFY/REJECT/HYBRID 네 route를 전부 단언하고 13.8은 그걸 SM-F/SM-G 증거로 썼다. (3) **닫으면서 다시 열 자리를 안 정했다** — DW-556·564·565는 "모델 후보 비교가 실제로 생기면 그때 다시 연다"는 산문만 남기고 `done`이 됐다. CLAUDE.md B8은 "미룬 항목엔 언제·어디서 고칠지를 대장에 함께 적고, 지정한 곳에도 실제로 심으라"고 요구한다 — 지금 상태면 첫 모델 A/B를 하는 사람이 장부에 "열린 것 없음"을 보고 세 개의 알려진 채점 왜곡 위에서 시작한다. **직접 고치지 않은 이유는 DW-623과 같다**(신규 등재만 허용).
trigger: **오케스트레이터가 다음 sweep을 돌릴 때** DW-623과 함께 처리한다 — DW-573·590에 부분 해소 주석과 좁힌 잔여 범위를, DW-577에 종결(또는 남은 범위)을, DW-556·564·565에 구체적 재개봉 지점("첫 모델 후보 비교 스토리의 스펙 작성 시")을 적는다.
status: open

### DW-625: CM-B의 FR11 강제지점 로스터가 `conventions.md` §6이 아니라 임의 목록에서 나왔다

origin: story 13-8(RAG exit-gate 검증) **후속 리뷰** — adversarial 렌즈 발견, 오케스트레이터가 §6 원문과 실제 실행으로 확인
location: `_bmad-output/implementation-artifacts/spec-13-8-...md`(Always절·AC3의 CM-B 로스터) · `docs/conventions.md` §6(축 3개: 매물·이미지·SECURITY DEFINER 함수) · `api/tests/integration/test_seller_summary_real_db.py`
severity: low
reason: 13.8의 CM-B는 "판매완료 매물이 **4개 지점 어디서도** 노출되지 않음"을 실DB로 확인했다고 적었는데, 그 4개는 §6의 축 분류가 아니라 이 스펙이 따로 세운 목록이었다. §6이 등록한 **SECURITY DEFINER 함수 축**(`get_seller_public_summary` — 정의자 함수 안에선 RLS가 안 걸려 **함수 본문 인라인 조건이 유일한 강제 지점**인, 가장 새기 쉬운 축)은 스펙의 Verification 커맨드 어디에도 없었다. 로스터를 정본 문서에서 뽑지 않고 손으로 나열하면 이런 누락이 조용히 생긴다. **실제 위험은 확인 결과 없다** — 이번 후속 리뷰에서 `test_seller_summary_real_db.py`를 실DB로 돌려 **5 passed**(sold 매물이 몇 건이 추가돼도 카운트에서 계속 빠짐)를 확인했다. 남는 건 "다음 번 CM-B류 검증도 같은 방식으로 축을 빠뜨릴 수 있다"는 절차 결함이다.
trigger: **CM-B(또는 FR11 전수 확인)를 다시 수행하는 다음 스토리 착수 시** — 강제지점 로스터를 손으로 적지 말고 `docs/conventions.md` §6의 축 목록에서 뽑아 세 축을 모두 실행 대상에 넣는다. DW-619(§6에 `hybrid_rag_node` 미등록)를 먼저 처리하면 §6이 정확한 정본이 되어 이 방식이 성립한다.
✎ 2026-08-03 trigger 재지정(오케스트레이터) — 위 trigger가 가리키는 "다음 스토리"가 백로그에 실재하지 않아 영영 발화하지 않는다는 지적(DW-640)에 따라, **Story 13.9(라우팅 안정화)의 인수조건으로 재지정**한다. 13-9는 `sprint-status.yaml`에 실재하는 backlog 스토리이며, 해당 인수조건을 실제로 심었다(B8: 지정한 곳에 실제로 심는다).
status: done 2026-08-03
resolution: 이 항목이 요구한 전제(DW-619 처리로 §6이 정확한 정본이 되는 것)를 Story 13.9가 충족했다 — §6 "매물 축" 불릿에 `hybrid_rag_node`를 추가해 이제 §6이 매물 축 FR11 강제지점 4곳을 전부 나열한다. 같은 스토리가 §6의 **문서 RAG 필터** 축(`doc_rag_node`)에 실DB 검증을 새로 추가해(DW-627, `api/tests/integration/test_doc_rag_node_real_db.py`) 로스터의 실행 커버리지도 넓혔다. 13.9 자체는 CM-B 전수 재실행을 스코프에 두지 않았으므로(그건 13.8이 이미 했다), "다음 CM-B류 검증이 로스터를 §6에서 뽑는다"는 절차가 실제로 성립하는지는 그 다음 CM-B 재실행 시점에 확인된다 — 이 항목은 그 전제(§6 정본화)가 충족된 것으로 닫는다.

### DW-626: G2 회귀 게이트가 네 축 중 `result_mean` 하나만 baseline과 비교한다 — 13.4·13.6 기능이 전멸해도 초록

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — verification-gap 렌즈가 커밋된 캡처를 변형해 실증, adversarial 렌즈가 독립적으로 같은 결론
location: `api/scripts/score_ab.py`(`regression = candidate["result_mean"] < baseline["result_mean"] - 1e-9` · `gate_pass`는 contamination/deadend/errored_n/scored_n만 본다) · `api/scripts/score_ab.py`의 `result_scores_clean` 조립부(primary SQL/HYBRID·non-gray 항목만 들어가 `result_n=33/47`)
severity: medium
reason: 에픽 게이트 문구와 13.8 AC2는 G2가 "품질이 baseline 이하로 안 떨어짐"을 보증한다고 읽히지만, 자동 판정에 들어가는 축은 `result_mean` **하나뿐**이고 그조차 47문항 중 33개의 평균이다. `routing_correct`·`doc_hit_n`·`clarify_ok_n`은 리포트에 기록만 될 뿐 baseline과 비교되지 않는다. **실증(리뷰가 실제로 돌림)**: 커밋된 `docs/g2-exit-gate-2026-08-02.json`을 ① 모든 답변에서 가이드 인용 `(참고: …)` 16곳 제거 → doc_hit 12/13 → 0/13, ② `primary_path=CLARIFY`인 7항목을 SQL 응답으로 치환 → routing 54 → 47, clarify_ok 9/9 → 2/9. **두 경우 모두 `gate_pass:true`·`regression_block:false`로 통과**했다. 즉 13.6이 만든 가이드 질의확장과 13.4가 만든 되묻기가 통째로 죽어도 에픽 종료 게이트가 선다. 13.8은 이 세 축을 사람이 두 리포트를 눈으로 대조해 확인했고(이번엔 정확히 일치) 스펙 AC2도 3차 리뷰에서 그렇게 정정했지만, **사람 확인은 다음 재실행에 상속되지 않는다**(CLAUDE.md B9). 열린 DW-621(재현성 vs 회귀)은 baseline 시점 문제만 다루므로 13.9가 기준선을 다시 떠도 이 축 누락은 그대로 남는다.
trigger: **Story 13.9 완료 후 G2를 재실행하기 직전**(DW-621과 같은 자리 — 그때 기준선을 어차피 다시 뜬다) — `score_ab.py` 2-file 모드의 `regression_block`에 세 축의 비하락을 OR로 합치거나, 두 리포트 JSON을 읽어 네 축을 비교하는 결정론 테스트를 `tests/test_ab_scoring.py`에 넣는다. 어느 쪽이든 "사람이 눈으로 대조"를 실행되는 검사로 바꾸는 것이 요지다.
status: done 2026-08-03
resolution: `score_ab.py`의 `regression_axes` dict가 이제 네 축(`result_mean`·`routing_correct`·`doc_hit_n`·`clarify_ok_n`)을 각각 baseline과 비교하고, `regression_block`은 하나라도 하락하면 True다(리포트에 `regression_axes`·top-level `gate_pass`로 축별 결과를 남김). **양방향 실증(B4)**: `test_regression_block_flags_doc_hit_and_clarify_regression_even_when_result_mean_ties`가 result_mean은 동률인데 doc_hit·clarify만 죽은 raw 쌍으로 red를 재현했고(리뷰가 실증했던 바로 그 시나리오), 4축을 3축으로 되돌리는 뮤테이션을 주입해 이 테스트가 실제로 실패함을 확인한 뒤 원복해 green을 재확인했다. `test_regression_block_false_when_all_four_axes_hold`가 양성 대조군이다.

### DW-627: FR11 강제지점 4곳 중 `doc_rag_node` 축은 실DB 검증이 없어 필터 무력화를 못 잡는다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — verification-gap 렌즈가 뮤테이션으로 실증(원복 확인), adversarial·intent-alignment가 같은 표면 혼동을 독립 지적
location: `api/tests/test_doc_rag_node.py`(`assert "status = 'on_sale'" in listing_q` — 문자열 포함 검사) · `api/app/graph/doc_rag_node.py`(매물 의미검색 `WHERE status = 'on_sale' AND embedding IS NOT NULL`) · `api/tests/integration/`(이 축을 보는 실DB 테스트 없음)
severity: medium
reason: `doc_rag_node`의 매물 의미검색은 **sql_guard를 거치지 않고**(자기 독스트링이 명시), `listings`의 ai_readonly RLS 정책이 `using(true)`라 행 필터도 걸리지 않는다 — 즉 그 `WHERE status = 'on_sale'` 한 줄이 **유일한 FR11 강제 지점**이다. 그런데 그걸 지키는 검사는 생성된 SQL 문자열에 그 글자가 들어 있는지 보는 단위테스트뿐이다. **실증**: `WHERE (status = 'on_sale' OR true)`로 바꾼 뒤 13.8 스펙의 CM-B 커맨드 전량을 그대로 실행하니 유닛 5파일 149 passed·FR11 실DB 1 passed·전체 394 passed로 **스펙에 기록된 수치와 완전히 동일**했다(수행 후 `git checkout` 원복, `grep "OR true" api/app/graph/` 0건 확인). 대조군으로 `hybrid_rag_node`에 같은 변형을 넣으면 14건이 red가 된다 — 그 축은 조립 SQL 전문을 단언하므로 실제로 보호된다. 이 경로는 CLARIFY 상한 초과 강제 제시와 하이브리드 구조조건 추출 실패 폴백이 타므로 죽은 코드가 아니다. FR11은 보안 블로커 등급이고, `test_listing_cards.py`가 자기 독스트링에 "가짜 DB는 조건을 **지우면** 잡지만 **무력화하면**(`OR true`·`AND false`) 전부 초록"이라고 이미 적어 둔 바로 그 한계다.
trigger: **FR11 강제지점을 다시 손대거나 CM-B류 전수 확인을 수행하는 다음 스토리 착수 시**(DW-625와 같은 자리) — `tests/integration/test_fr11_cover_images_real_db.py`와 같은 층(실 Postgres + sold 1건·on_sale 1건 시드)에서 `doc_rag_node`의 매물 쿼리를 실행해 sold id가 결과에 없음을 단언하는 통합 테스트를 추가한다. 문자열 검사는 그대로 두고 층을 하나 얹는 것이다.
✎ 2026-08-03 trigger 재지정(오케스트레이터) — 위 trigger가 가리키는 "다음 스토리"가 백로그에 실재하지 않아 영영 발화하지 않는다는 지적(DW-640)에 따라, **Story 13.9(라우팅 안정화)의 인수조건으로 재지정**한다. 13-9는 `sprint-status.yaml`에 실재하는 backlog 스토리이며, 해당 인수조건을 실제로 심었다(B8: 지정한 곳에 실제로 심는다).
status: done 2026-08-03
resolution: `api/tests/integration/test_doc_rag_node_real_db.py`(신규)를 `test_fr11_cover_images_real_db.py`와 동일 패턴으로 추가했다 — 실 Postgres(로컬 Supabase, `TEST_DATABASE_URL`)에 on_sale 1건·sold 1건(동일 임베딩)을 심고 `doc_rag_node(query, qvec=...)`를 직접 호출해 sold id가 결과에 없음을 단언한다. **양방향 실증(B4)**: `WHERE status = 'on_sale'` → `WHERE (status = 'on_sale' OR true)`로 무력화하자 이 신규 테스트는 실제로 **red**가 됐다(sold id가 결과에 포함됨을 확인) — 동시에 기존 `tests/test_doc_rag_node.py`(문자열 검사)는 같은 뮤테이션에서도 전부 green으로 남아, reason이 지적한 "문자열 검사가 무력화를 못 잡는다"는 공백을 그대로 재현했다. 뮤테이션을 원복해 신규 테스트가 다시 green임을 확인했고, 시드 데이터는 테스트 후 rollback으로 정리해 잔존 행이 없음을 `psql` count로 재확인했다(DW-614 #7과 같은 teardown 원칙).

### DW-628: `test_readonly.py`(ai_readonly 롤 격리)를 실행하는 CI 잡이 하나도 없다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — adversarial 렌즈 발견, 오케스트레이터가 `.github/workflows/tests.yml`과 스킵 가드 원문으로 확인
location: `api/tests/test_readonly.py`(가드 = `settings.database_url`, 즉 `DATABASE_URL`) · `.github/workflows/tests.yml`(`api` 잡은 `DATABASE_URL`을 **의도적으로** 안 준다 — 13줄 주석: "있으면 운영 Supabase에 실제 접속한다" · `api-db` 잡은 `TEST_DATABASE_URL`로 `tests/integration`만 실행)
severity: medium
reason: CM-B가 지키는 세 안전장치 중 하나(커넥션 풀 재사용 시 ai_readonly 롤이 누수되지 않음, Epic 8 AC-DB-1)가 **어느 CI 잡에서도 돌지 않는다**. `api` 잡은 운영 DB 접속 위험 때문에 `DATABASE_URL`을 일부러 비우므로 이 파일이 항상 skip되고, `api-db` 잡은 대상 디렉터리가 `tests/integration`으로 한정돼 이 파일을 수집하지 않는다. 두 결정 각각은 옳은데 교집합에서 이 축이 통째로 빠졌다. 13.8이 기록한 "149 passed, 0 skipped"는 사람이 손으로 한 번 친 로컬 실행이고, 롤 격리를 깨는 커밋이 들어와도 CI는 영구히 초록이다. DW-622는 "스킵이 통과와 구별 안 된다"는 가시성 문제를 다루지, "애초에 CI에서 실행되지 않는다"는 이 사실은 다루지 않는다.
trigger: **CI 워크플로(`tests.yml`)를 다음에 손댈 때**(DW-622와 같은 자리) — `test_readonly.py`를 컨테이너 Postgres에서 돌 수 있게 `TEST_DATABASE_URL`을 읽도록 이식해 `api-db` 잡 범위에 넣는다. 그게 어려우면 최소한 `project-context.md` §12의 "CI에 안 도는 것" 목록에 이 파일을 명시적으로 올린다(지금은 안 올라 있어 돈다고 오해된다).
status: open

### DW-629: DW-622가 제안한 해법(환경변수 fallback)을 그대로 구현하면 통합 테스트가 운영 DB에 쓴다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — adversarial 렌즈 발견, 오케스트레이터가 워크플로 주석과 통합 테스트 픽스처로 확인
location: `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-622 `trigger:` 줄(두 변수명을 합치거나 "하나가 다른 하나를 fallback으로 읽게") · `api/tests/integration/conftest.py` · `.github/workflows/tests.yml`(13줄)
severity: medium
reason: DW-622는 "`TEST_DATABASE_URL`과 `DATABASE_URL` 두 이름이 함정을 만든다"는 옳은 진단을 담았지만, 적어 둔 해법 중 하나가 위험하다 — `tests/integration/*`가 `TEST_DATABASE_URL` 부재 시 `DATABASE_URL`로 폴백하게 만들면, 이 프로젝트에서 `DATABASE_URL`은 **운영 Supabase를 가리키는 변수**다(`tests.yml` 13줄이 명시적으로 그렇게 경고하며 `api` 잡에서 일부러 비운다). 통합 테스트는 사용자·매물을 실제로 INSERT하므로, 개발자 셸에 `DATABASE_URL`이 떠 있는 상태에서 `pytest` 한 번이면 운영 DB에 테스트 데이터가 들어간다. 장부의 산문은 다음 사람이 그대로 구현하는 지시로 읽힌다 — **DW-622의 두 갈래 중 fallback 안은 채택하지 말 것.** (이 항목을 DW-622 본문 수정이 아니라 신규 등재로 남기는 이유: 이번 실행의 지시가 "기존 장부 항목은 수정·재개봉·재작성 금지, 신규만 추가"였다.)
trigger: **DW-622를 실제로 처리하는 그 작업의 착수 시점** — 두 항목을 같이 읽고, fallback이 아니라 나머지 갈래(보안 표식이 붙은 테스트가 스킵되면 스위트를 실패시키는 conftest 훅)로 방향을 고정한다. 변수명을 합쳐야 한다면 방향은 반대여야 한다 — 통합 테스트가 `DATABASE_URL`을 읽는 게 아니라, 운영을 가리킬 수 있는 변수는 통합 테스트에서 아예 못 읽게 막는 쪽이다.
status: open

### DW-630: 라이브 스모크가 전부 스킵돼도 exit 0이라 SM-F/SM-G가 거짓 초록이 될 수 있다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — verification-gap 렌즈 발견, 오케스트레이터가 스킵 가드 원문으로 확인
location: `api/tests/test_live_smoke.py`(파일 전체가 `RUN_LIVE_SMOKE != "1"`에서 collect-skip · `_run_or_skip`이 429·quota·RESOURCE_EXHAUSTED·키/DB 부재를 `pytest.skip`으로 흡수) · 13.8 스펙 Verification 커맨드 1
severity: medium
reason: SM-F(기존 시연 3종 유지)·SM-G(신규 3분기 실동작) 게이트의 유일한 증거가 이 파일의 라이브 실행인데, `RUN_LIVE_SMOKE`를 빠뜨리거나 쿼터가 마르면 `6 skipped`·exit 0이 나온다. 기대값이 "5건 PASSED"라는 사람이 읽는 문장뿐이라, 다음 재실행자가 초록만 보고 SM-F/SM-G를 통과로 기록할 수 있다. **이건 가설이 아니다** — 이 스토리에서 CM-B의 두 축(FR11 실DB·ai_readonly)이 정확히 그 방식으로 스킵인 채 "통과"로 닫혔다가 후속 리뷰에서야 드러났다(그 사건이 DW-622를 만들었다). 다만 DW-622의 범위는 `*_real_db.py`/`test_readonly.py`의 환경변수명과 보안 표식으로 한정돼 이 라이브 축을 포함하지 않는다. 429 자동 스킵 자체는 의도된 쿼터 보호이므로 없애면 안 되고, 필요한 건 "스킵됐다"가 게이트 판정자에게 **보이게** 만드는 것이다.
trigger: **SM-F/SM-G를 다시 판정하는 다음 실행(13.9 종료 검증)의 커맨드를 짤 때** — `RUN_LIVE_SMOKE=1`인데 라이브 표식 테스트가 스킵되면 스위트를 실패시키는 conftest 훅(DW-622가 보안 표식에 제안한 것과 같은 형태로 묶어서), 또는 최소한 커맨드에 `-rs`를 붙이고 기대값을 "6 collected / 0 skipped(langsmith 제외)"처럼 개수로 못박는다.
status: done 2026-08-03
resolution: 13.9 종료 검증에서 `RUN_LIVE_SMOKE=1 ... pytest tests/test_live_smoke.py -v -rs`를 실제로 실행했다 — 결과 **10 passed, 1 skipped**(skip은 langsmith 계측 env 게이트 하나뿐, 사유가 정확히 표시됨). 채택한 것은 trigger의 두 대안 중 **후자**(개수·사유를 -rs로 못박는 절차)다 — conftest 훅(전자)은 이 스토리의 코드 변경 범위(Tasks 목록)에 없어 구현하지 않았다. DW-641이 이 파일의 라이브 단언 로직을 순수 함수로 분리하면서 6개 라이브 테스트 각각에 개별 skipif 마커를 붙였고(모듈 단위 skipif 제거), 그 리팩터가 이번 실측에도 그대로 반영돼 있다.

### DW-631: G2 캡처 아티팩트에 실행 시각·커밋 해시가 없어 "어느 코드 상태의 캡처인가"를 파일로 증명할 수 없다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — verification-gap 렌즈 발견
location: `api/scripts/run_phase_b.py`(`capture()`가 남기는 최상위 메타 = `{"model": …}` 뿐) · `api/docs/g2-baseline.json` · `api/docs/g2-exit-gate-2026-08-02.json`
severity: low
reason: 두 캡처 파일의 최상위 키는 `model`과 `results`뿐이다. 그래서 "이 캡처가 어느 코드에서 떴나"를 파일 자체로는 알 수 없고, 이번 리뷰도 `git log --since=... -- api/app`으로 사후 추론해야 했다(그 추론이 DW-621의 근거다). DW-621이 예정한 **13.9 재기준선 작업**에서는 "13.9 이전 코드로 뜬 캡처"를 기준선으로 고정하는 것이 핵심인데, 그 사실을 파일이 스스로 말하지 못하면 같은 사후 추론을 반복해야 하고 파일이 섞이면 구분할 방법이 없다.
trigger: **DW-621을 처리하는 13.9 재기준선 작업과 같은 자리** — `capture()` 결과 메타에 `captured_at`(ISO)·`git_sha`(`git rev-parse HEAD`)를 함께 기록하고, `score_ab.py`가 리포트에 그대로 실어 준다. 기존 캡처 2개는 메타가 없으므로 소급하지 말고 "메타 없음 = 2026-08-02 이전 캡처"로 둔다.
status: open

### DW-632: `ai-demo-queries.md` ①②④ 표 12행 중 8행이 관측된 적 없는 기대값이다

origin: story 13-8(RAG exit-gate 검증) **3차 리뷰** — adversarial·edge-case 두 렌즈 발견, 오케스트레이터가 큐리셋·라이브 스모크와 대조해 행별로 확인
location: `api/docs/ai-demo-queries.md`(표 ①②④) · `api/tests/demo_queries.py`(`STRUCTURED_A`·`SEMANTIC_B`·`UNRELATED_C`) · `api/docs/ai-ab-test-queryset.json`
severity: low
reason: 이 문서는 스스로를 라우터 기대동작의 "단일출처"라 선언하고 각 행의 "기대 분류"는 *라우터가 그 질의를 어디로 보내는가*에 대한 주장이다. 실측 대조 결과 근거가 있는 것은 4행뿐이다 — `3천만원 이하 흰색 SUV`(SQL)·`패밀리카로 무난한 거`(CLARIFY)·`오늘 날씨 어때?`(REJECT)는 `test_live_smoke.py`가 라이브로 route를 단언하고, `출퇴근용으로 편한 차 추천해줘`는 큐리셋 CL4와 같은 문자열이다. 나머지 8행(`2020년 이후 제네시스`·`10만km 미만 디젤`·`서울 경차 보여줘`·`초보운전자에게 좋은 차`·`가성비 좋은 차 없을까?`·`파이썬 코드 짜줘`·`안녕`·`1+1은 뭐야?`)은 큐리셋에도 라이브 테스트에도 없고, 결정론 테스트는 `_patch_route`로 경로를 강제 주입하므로 실제 분류를 보지 않는다. **3차 리뷰에서 표 앞에 근거 강도를 밝히는 주석을 달아 오해는 막았지만**(어느 4행이 실측인지 명시), 8행의 기대값 자체를 실측으로 뒷받침하는 일은 남는다. 이건 DW-576(SM3가 라우팅을 강제 주입해 실제 라우팅을 보장하지 못함)의 문서 쪽 표면이다.
trigger: **DW-576(회색지대 route 강제 주입)을 구조적으로 해소하는 그 작업에서 함께** — 라이브 라우터 결과 기반 판정을 도입한다면 그 대상 목록이 곧 이 12행이 된다. 그 전에 데모 시연이 잡히면 그때 8행을 한 번 라이브로 돌려 실측 라우트를 표에 병기한다(비용은 질의 8건).
✎ 2026-08-03 trigger 재지정(오케스트레이터) — 위 trigger가 가리키는 "다음 스토리"가 백로그에 실재하지 않아 영영 발화하지 않는다는 지적(DW-640)에 따라, **Story 13.9(라우팅 안정화)의 인수조건으로 재지정**한다. 13-9는 `sprint-status.yaml`에 실재하는 backlog 스토리이며, 해당 인수조건을 실제로 심었다(B8: 지정한 곳에 실제로 심는다).
status: done 2026-08-03
resolution: trigger가 제안한 대로 "데모 시연이 잡힌" 이 스토리에서 8행을 실제로 라이브 1회 돌렸다(2026-08-03, `router_node()` 직접 호출, 라우터 프롬프트 갱신 후). 결과: 8행 전부 문서의 "기대 분류"와 정확히 일치했다(`2020년 이후 제네시스`→SQL, `10만km 미만 디젤`→SQL, `서울 경차 보여줘`→SQL, `초보운전자에게 좋은 차`→CLARIFY, `가성비 좋은 차 없을까?`→CLARIFY, `파이썬 코드 짜줘`→REJECT, `안녕`→REJECT, `1+1은 뭐야?`→REJECT). `ai-demo-queries.md` 상단 노트를 "12행 중 4행만 실측"에서 "12행 전부 실측(13.9가 나머지 8행을 라이브로 확인)"으로 갱신했다 — 단, 이 실측은 문서를 고친 시점의 스냅샷이며 상시 회귀 게이트가 아니라는 것도 명시했다(결정론 테스트는 여전히 `_patch_route` 강제 주입이라 DW-576 자체는 별개로 열려 있다). `demo_queries.py`는 질의 문자열·기대 route 값 자체가 바뀌지 않아 수정 불필요.

### DW-633: Follow-up review still recommended for 13-8-rag-exit-gate-검증-sm-f-sm-g-g2-cm-b after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-8-rag-exit-gate-검증-sm-f-sm-g-g2-cm-b.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260802-213104-8dec; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: done 2026-08-03
resolution: 독립 후속 리뷰(4차)를 실제로 수행했다(2026-08-03, 새 세션·opus, 커밋 `ebf4d8a`·`86e4fb4`). 3차가 남긴 신규 14건(DW-619~632)을 코드·CI 설정과 하나씩 대조해 **틀리거나 과장되거나 이미 해결된 항목 0건**임을 확인했다. 새로 나온 high 2건은 둘 다 **3차가 "일부러 깨서 red를 봤다"고 기록한 검사 자신의 결함**이었다(기록은 사실이었고, 문제는 **한 방향으로만 깨본 것**): ① 회색지대 락스텝 검사가 질의셋을 표의 키로 먼저 걸러 비교해, 표에서 행을 지우면 양쪽이 같이 줄어 통과했다(3행 게이트를 1행으로 잘라도 전량 초록 — 세 레이어가 각각 독립 실증) → 반대 방향까지 보게 수정. ② 기준선 거부 테스트가 **실제 기준선 경로**로 스크립트를 호출해, 가드가 회귀하는 바로 그 순간 `pytest` 한 번이 47문항 기준선을 0으로 비웠다(md5 실측) → 검사를 파괴가 일어나는 층으로 내리고 사후 바이트 대조 추가. 그 외 `## Verification`의 G2 채점 명령이 `DATABASE_URL` 누락으로 실행조차 안 됐고(2차가 같은 유형을 이미 잡았는데 네 번째 명령에 남아 세 패스가 놓침), `ai-demo-queries.md` 서두의 "회색지대는 CLARIFY"가 같은 문서 표 3행 중 2행과 모순이었다. 399 passed·85 skipped, 앱 코드 무변경. 리뷰 권고는 "5차 패스보다 13.9에서 게이트를 실행되는 검사로 바꾸고 양방향 뮤테이션을 관례화하라"이며 이를 13.9 인수조건으로 심었다. 이 항목을 닫는다.

### DW-634: SM3 ①② 게이트에는 노드 식별 단언이 없어 `SQL→hybrid` 오배선이 초록으로 지나간다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — adversarial 렌즈가 뮤테이션으로 실증, 오케스트레이터가 코드로 재확인
location: `api/tests/test_demo_acceptance.py`(`test_sm3_pathA_returns_listings`·`test_sm3_pathB_returns_listings`) · `api/docs/ai-demo-queries.md`(SM3 매핑 표 ①②행)
severity: medium
reason: 3차 리뷰가 회색지대 테스트에는 노드별 카드 id(`s1`/`h1`) 단언을 넣어 분기 오배선을 잡게 만들었지만, 같은 파일의 ① 게이트는 여전히 `assert out["listings"]`(비어있지 않음)만 본다. **실증**: `conditional_edges`를 `"SQL" → hybrid`로 오배선해도 ① 게이트 4건이 전부 초록이다(회색지대 테스트는 red가 되므로 리포 전체로는 탐지되지만, `ai-demo-queries.md`의 SM3 매핑 표가 ① 행의 검사로 지목하는 것은 이 테스트다). 즉 문서가 "이 검사가 ①을 지킨다"고 적은 것과 실제 탐지 범위가 다르다. `_patch_route`가 이미 노드별로 구분되는 카드 id를 주입하므로 각 테스트에 한 줄 추가하면 닫힌다. **이 스토리(13.8)가 만든 결함은 아니다** — ①② 테스트는 13.8 이전부터 이 형태였고, 3차 리뷰가 회색지대만 보강하면서 비대칭이 드러난 것이다.
trigger: **Story 13.9(라우팅 안정화)의 인수조건으로 함께 확인한다** — 13.9는 라우터 분류를 바꾸는 스토리라 분기 오배선 탐지가 정확히 그 자리에서 필요하다. `test_sm3_pathA_returns_listings`에 `assert out["listings"][0]["id"] == "s1"`, `pathB`는 이미 `clarify` 페이로드를 단언하므로 유지. 넣은 뒤 일부러 오배선해 red를 확인한다(B4).
status: open

### DW-635: `score_ab.py --out`에는 기준선 보호 검사가 없고, 자기 독스트링 예시가 커밋된 리포트를 가리킨다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — adversarial·edge-case 두 렌즈 독립 지적
location: `api/scripts/score_ab.py`(`--out` 인자 · 독스트링 1파일 모드 예시) · `api/docs/g2-baseline-report.json`
severity: medium
reason: 13.8 3차 리뷰가 `run_phase_b.py`에 `_PROTECTED_BASELINES` 가드를 넣었고 4차 리뷰가 그것을 `capture()` 층까지 내렸지만, **쌍둥이 스크립트인 `score_ab.py`에는 같은 보호가 전혀 없다.** `--out`은 필수도 아니고(기본값 `docs/ab-eval-report.json`), 독스트링의 1파일 모드 예시가 `--out docs/g2-baseline-report.json`을 그대로 제시한다. 그 파일은 AC2의 **Manual checks가 대조하는 유일한 기준 수치**(54/57·0.8936·12/13·9/9)를 담고 있고, DW-626이 확인했듯 `routing_correct`·`doc_hit_n`·`clarify_ok_n` 세 축은 어떤 자동 게이트도 비교하지 않으므로 이 파일이 세 축의 유일한 기준점이다. 부분 캡처로 한 번 채점하면 47항목 기준이 3항목 리포트로 바뀐다. 가드를 한쪽 스크립트에만 넣은 탓에 보호 범위가 **사람 눈으로만 확인되는 축이 시작되는 바로 그 지점에서 끊긴다.**
trigger: **`score_ab.py`를 다음에 손댈 때**(DW-626이 예정한 13.9 재기준선 작업에서 `regression_block`에 세 축을 합치는 그 자리) — `run_phase_b.py`의 보호 검사를 공용 헬퍼로 빼서 두 스크립트가 함께 부르게 하고, 독스트링 예시의 `--out`을 날짜형 경로로 바꾼다.
status: done 2026-08-03
resolution: `run_phase_b.py`의 `_PROTECTED_BASELINES`를 공용 헬퍼 `api/scripts/baseline_guard.py`(`PROTECTED_BASELINES`·`is_protected()`)로 뽑아 두 스크립트가 함께 참조하게 했다. `score_ab.py`의 `main()`에 `--out` 보호 검사를 추가했고, 독스트링 1파일 모드 예시를 `--out docs/g2-baseline-report.json`에서 `docs/g2-recapture-report.json`(비커밋 날짜형 경로)으로 정정했다. **양방향 실증(B4)**: 보호 검사를 지운 채 `test_out_path_pointing_at_committed_baseline_report_is_rejected`를 돌리자 **실제로 커밋된 `docs/g2-baseline-report.json`이 877줄→16줄로 덮어써졌다**(정확히 이 항목이 경고한 파괴가 재현됨) — `git checkout`으로 즉시 복구하고 보호 검사를 되돌려 테스트가 green임을 재확인했다.

### DW-636: 0건 캡처가 "캡처 완료" + exit 0이고, 커밋된 증거 아티팩트는 보호 밖이다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — edge-case·adversarial 두 렌즈 실증
location: `api/scripts/run_phase_b.py`(`main()`의 종료 처리 — `errored`만 exit 1을 만든다) · `api/scripts/run_phase_b.py`의 `_PROTECTED_BASELINES`(2개 파일만 등록) · `api/docs/g2-exit-gate-2026-08-02.json`
severity: medium
reason: 두 사실이 겹쳐 하나의 조용한 파괴 경로가 된다. (1) `--queryset` 오타나 매칭 0인 `--subset`이면 `capture()`가 루프 진입 전 `_flush()`로 대상 파일을 빈 상태로 만들고 `main()`은 `0개 item 캡처 완료(실패 0건)` + **exit 0**을 낸다 — 이 파일 독스트링이 스스로 세운 원칙("체인이 조용히 진행되지 않게 0이 아닌 코드로 종료")과 어긋난다. (2) `_PROTECTED_BASELINES`는 `g2-baseline.json`·`g2-baseline-partial.json` 2개만 덮고, **13.8의 AC2 증거인 `g2-exit-gate-2026-08-02.json`은 보호 밖**인데 스펙 Verification 커맨드 2번이 `--out`으로 정확히 그 경로를 가리킨다. 즉 13.9가 그 커맨드를 복붙해 돌리다 실패하면 증거가 0항목이 되고 종료코드는 0이다. 보호 집합에 그냥 추가할 수는 없다 — 그러면 문서화된 재캡처 커맨드 자체가 거부된다. 필요한 것은 파일명 열거가 아니라 "git이 추적 중인 캡처는 새 날짜 경로로만 쓴다"는 규칙이다. (복구 자체는 `git restore`로 가능하다 — 진짜 문제는 exit 0이라 아무도 복구를 시도하지 않는 것이다.)
trigger: **`run_phase_b.py`를 다음에 손댈 때** — ① `if not raw["results"]: sys.exit(1)`로 0건 캡처를 실패로 만들고, ② 보호를 "`git ls-files api/docs/*.json`에 잡히는 경로면 거부"로 바꿔 날짜형 새 경로만 허용한다(원래 trigger의 ③은 Story 13.9가 아래 ✎로 이행했다).
✎ 2026-08-03 부분 진척(Story 13.9) — reason의 두 사실 중 (2)만 이번 스토리가 닫았다: 공유 `baseline_guard.PROTECTED_BASELINES`에 `g2-exit-gate-2026-08-02.json`·`g2-exit-gate-report.json`을 추가해 "13.8 AC2 증거가 보호 밖" 공백을 닫았다(`test_run_phase_b.py`의 `test_main_refuses_to_overwrite_committed_baseline` parametrize에 두 파일을 추가해 거부를 실측 확인). **(1)의 0건 캡처 exit 0과 원래 trigger의 ②(git ls-files 기반 동적 보호)는 구현하지 않았다** — Story 13.9의 Tasks 목록이 커밋한 범위는 "보호 패턴 재사용 + docstring 정정"뿐이고, 파일명 열거 대신 동적 판별로 바꾸는 것은 별도 설계 판단이 필요해 스코프 밖으로 남긴다. 위 trigger는 남은 두 항목으로 좁혔다.
status: open

### DW-637: G2 회귀 판정의 **방향**이 `--raw` 인자 순서로만 정해지고 리포트에 그 순서가 안 남는다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — edge-case 렌즈가 양방향 채점으로 실증, 오케스트레이터가 코드·리포트로 재확인
location: `api/scripts/score_ab.py`(`baseline, candidate = summaries[0], summaries[1]` · `report = {"baseline": baseline["name"], "candidate": candidate["name"], …}`) · `api/docs/g2-exit-gate-report.json`
severity: medium
reason: DW-626은 "네 축 중 한 축만 비교한다"를 다루는데, 그 **한 축조차 방향이 검증되지 않는다**. `regression = candidate["result_mean"] < baseline["result_mean"]`이고 둘의 배정은 오직 `--raw`에 준 파일 순서다. **실증**: 결과집합을 훼손한 저하판을 만들어 `--raw <기준선> <저하판>`으로 채점하면 `regression_block:true`, 순서만 뒤집으면 **`regression_block:false`**로 통과한다(result_mean 0.894 vs 0.269). 그런데 리포트의 `baseline`/`candidate` 필드에 들어가는 것은 **파일 경로가 아니라 모델명**이고, 13.8은 같은 모델을 자기 자신과 비교하므로 양쪽 다 `gemini-3.1-flash-lite`다 — 즉 **산출된 아티팩트만 봐서는 어느 파일이 기준선이었는지 알 방법이 전혀 없다**(커밋된 `g2-exit-gate-report.json`에서 직접 확인). 13.9가 재기준선을 뜨면 두 캡처가 서로 다른 코드 상태가 되므로 순서 실수의 대가가 지금보다 커진다(그때는 진짜 회귀가 통과할 수 있다). DW-631(캡처에 시각·커밋 해시 없음)과 인접하지만 같지 않다 — 그건 캡처 파일의 출처, 이건 채점 리포트의 역할 배정이다.
trigger: **DW-626·DW-631을 처리하는 13.9 재기준선 작업과 같은 자리** — 리포트에 `baseline_raw`/`candidate_raw`(원본 파일 경로)를 함께 싣고, 두 raw의 `model`이 같으면 `--baseline`/`--candidate` 명시를 요구하거나 최소한 경고를 찍는다. 순서를 바꿔도 같은 리포트가 나오지 않는지 확인하는 결정론 테스트를 `test_ab_scoring.py`에 함께 넣는다(B4).
status: done 2026-08-03
resolution: 2파일 모드 리포트에 `baseline_raw`/`candidate_raw`(`--raw`에 준 원본 파일 경로 그대로)를 추가했다. 두 raw의 모델명이 같으면(자기비교) 콘솔에 `⚠️ baseline·candidate 모델명이 같습니다 — 파일 경로로만 방향을 구분할 수 있습니다: baseline_raw=..., candidate_raw=...` 경고를 찍는다(trigger가 제시한 "필수 요구" 대신 "경고" 쪽을 택했다 — 자기비교 자체가 정당한 사용 패턴이라 강제 거부는 과잉이라고 판단). `test_ab_scoring.py`에 `test_report_records_raw_file_paths_and_self_comparison_warning`(경고 문구·파일 경로 단언)과 `test_swapping_raw_argument_order_changes_recorded_baseline_direction`(순서를 바꾼 두 리포트가 `baseline_raw`/`candidate_raw`도 함께 뒤집힘을 확인)을 추가했다 — 후자가 정확히 이 항목의 실증 시나리오(방향 뒤집기)를 결정론으로 고정한다.

### DW-638: `--subset`이 id 없는 큐리셋 항목을 만나면 친절한 검증 전에 맨 `KeyError`로 죽는다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — edge-case 렌즈
location: `api/scripts/run_phase_b.py`(`main()`의 `missing = set(subset) - {it["id"] for it in queryset["items"]}`) · 같은 파일 `capture()`의 `missing item id at index {idx}` 사전검증
severity: low
reason: `capture()`는 review pass 5에서 "id 없는 item은 원인을 말해주는 ValueError로 거부"하도록 고쳐졌지만, `main()`의 `--subset` 검증이 **그보다 먼저** `{it["id"] for it in ...}`로 색인하므로 `--subset`을 쓰는 경로에서는 여전히 맨 `KeyError: 'id'`가 난다. 그 수정이 없애려던 증상(어느 item이 문제인지 알 수 없음)이 한 갈래에 그대로 남아 있다. 큐리셋을 손으로 편집하는 작업(13.9가 `acceptable_paths`를 좁히며 하게 된다)에서 마주칠 자리다.
trigger: **큐리셋(`ai-ab-test-queryset.json`)을 편집하는 다음 작업 시**(13.9 라우팅 안정화가 `acceptable_paths`를 조정하는 자리) — `main()`의 subset 검증 앞에 `capture()`와 같은 id 존재 검사를 두거나, subset 필터링을 `capture()` 안으로 밀어 검증 순서를 하나로 만든다.
status: open

### DW-639: `epic-13-context.md`가 "47개 질의" 사본을 새로 심었다 — 같은 커밋이 다른 곳의 하드코딩 수치를 뺀 이유와 정면으로 어긋난다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — adversarial 렌즈, git으로 신규 추가임을 확인(5fd4b67엔 없음)
location: `_bmad-output/implementation-artifacts/epic-13-context.md`(실측 기준선 서술의 "47개 질의") · 대조: `api/scripts/run_phase_b.py`의 `--subset` help(같은 커밋이 "전량(47개)"에서 수치를 뺐다)
severity: low
reason: 13.8의 명시 목적 중 하나가 "수치 사본은 늙는다"(13-7 리뷰가 지적한 패턴)를 고치는 것이었고, 3차 리뷰는 그 이유로 `--subset` help에서 하드코딩된 개수를 제거했다. 그런데 **같은 커밋이 epic 컨텍스트에는 새 수치 사본을 넣었다**. 하필 그 파일은 **Story 13.9의 스펙이 만들어지는 문서**이고, 13.9는 **기준선을 재캡처하는 스토리**라 질의 수가 바뀔 수 있는 바로 그 작업이다. 지금은 값이 맞으므로 코드 동작에 영향은 없다.
trigger: **Story 13.9 step-02 planning(스펙 초안 작성) 시** — 수치를 빼고 `api/docs/ai-ab-test-queryset.json`을 정본으로 가리키는 포인터만 남긴다(`--subset` help가 이미 그렇게 한다). 재캡처로 질의 수가 바뀌면 이 한 줄을 고치는 대신 사본이 애초에 없게 만든다.
status: open

### DW-640: 열린 장부 항목 4건의 `trigger:`가 예정에 없는 스토리에 걸려 있어 영영 발화하지 않을 수 있다

origin: story 13-8(RAG exit-gate 검증) **4차 리뷰(DW-633)** — edge-case 렌즈가 장부 전수 대조로 발견
location: `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-620·DW-625·DW-627·DW-632 `trigger:` 줄 · 대조: DW-621·DW-626·DW-630·DW-631(실재하는 Story 13.9에 묶여 건전)
severity: medium
reason: CLAUDE.md B8은 미룬 항목에 "언제·어디서 고칠지"를 적으라고 요구하는데, 네 항목의 트리거는 **백로그에 존재하지 않는 스토리**를 조건으로 건다 — DW-625·DW-627은 "CM-B류 전수 확인을 수행하는 다음 스토리 착수 시", DW-632는 DW-576에 체인(그 DW-576은 `status:` 값 자체가 sweep 문법 밖이라 DW-623이 열려 있다), DW-620은 문서 드리프트 일반. 그중 **DW-627은 3차 리뷰가 `(status='on_sale' OR true)` 뮤테이션으로 실증한 FR11 보안 공백**(CM-B 커맨드 전량이 초록이었다)이고 severity가 medium인데, 그걸 고칠 담당 스토리가 없다. 반면 같은 패스에서 나온 DW-621·626·630·631은 실재하는 13.9(이미 G2 재캡처를 인수조건으로 가짐)에 묶여 있다 — 즉 이 문제는 장부 전체가 아니라 **이 네 건에 한정된 것**이다. 기존 항목 수정이 이번 실행에서 금지돼 있어 신규 등재로 남긴다.
trigger: **오케스트레이터가 다음 sweep을 돌릴 때** DW-623·DW-624와 함께 처리한다 — 네 항목의 트리거를 실재하는 Story 13.9의 인수조건(체크박스)으로 재지정하고, 지정한 그 자리에도 실제로 심는다(CLAUDE.md B5·B8: "회고 약속은 회고 문서에만 두면 이행되지 않는다"). 특히 **DW-627은 보안 축이므로 13.9 인수조건으로 올리는 것을 기본값으로 본다**.
status: done 2026-08-03
resolution: 네 항목(DW-620·625·627·632) 모두 Story 13.9가 처리를 완료했다(각 항목의 `status: done 2026-08-03`·`resolution:` 참조) — DW-627(보안 축, 실DB 테스트 신설)을 포함해 전부 실제로 발화했다. "예정에 없는 스토리에 걸려 발화하지 않는다"는 이 항목의 우려가 실제로 해소된 것으로 닫는다.

### DW-641: 라이브 트레이싱 단언의 로직이 재검증 불가능한 자리에 있고, 두 견본의 CORS 비대칭은 의도인지 미확인이다

origin: 2026-08-03, story 13-7-langsmith-트레이싱 **독립 후속 리뷰 패스**(DW-618이 남긴 권고를 새 세션에서 소진) — 라이브 양방향 재현 + 돌연변이 검사 과정에서 나옴
location: `api/tests/test_live_smoke.py`(`test_live_smoke_langsmith_tracing` 본문 209~249줄) · `api/tests/test_env_example_parity.py`(`_KNOWN_API_ONLY`) · `.env.example`(api 섹션) · `api/.env.example`(CORS 블록)
severity: low
reason: 실측 확인함 —
  1. **단언 로직이 테스트 함수 본문에 인라인이라 결정론으로 재검증할 방법이 없다.** 노드 스팬 단언(`r.name in node_names`)이 실제로 "노드 계측이 죽은 상태"를 잡는지는 이번 패스에서 라이브로 확인했지만(노드 이름 스팬을 서버 응답에서 걸러내 red 재현), 그 확인은 **매번 손으로 돌연변이를 만들어야만** 가능하다 — 3차 리뷰도 같은 일을 합성 스팬으로 따로 했다. 같은 검증을 두 번 손으로 한 것 자체가 신호다. 판정 로직을 순수 함수(예: `_missing_span_kinds(runs, node_names) -> list[str]`)로 빼면 라이브 없이 결정론 검사가 붙고, 3차가 잡은 "한 갈래를 두 번 세는" 착시도 CI가 지킨다. 지금은 **사람이 라이브로 돌릴 때만** 지켜진다(라이브 실행 자체를 CI로 옮기자는 얘기가 아니다 — 그 절충은 project-context 규칙 12로 유지).
  2. **루트 `.env.example`의 api 섹션과 `api/.env.example`의 키 비대칭 2건(`CORS_ORIGINS`·`CORS_ORIGIN_REGEX`)이 의도인지 누락인지 확인되지 않았다.** 이번 패스가 추가한 파리티 검사는 이 2건을 `_KNOWN_API_ONLY`로 **동결**해 두었을 뿐이다(새 비대칭은 양방향으로 red). DW-616이 제안했던 "키 집합 완전 일치" 단언은 이 상태에서 그대로 red가 나므로 채택할 수 없었다 — 판단(루트 견본에 CORS를 추가할지, 비대칭을 근거와 함께 확정할지)은 견본 파일을 실제로 손대는 스토리의 몫이다.
trigger: **Story `13-9-라우팅-안정화-최상급-교체요청-맥락재작성` 착수 시**(sprint-status.yaml에 실재하는 다음 스토리) — 1번은 13.9가 라우팅 노드를 바꾸면서 이 단언이 실제로 흔들리는 유일한 시점이므로 그때 순수 함수로 분리하고 결정론 검사를 붙인다. 2번은 그보다 먼저 **`.env.example`을 다음에 손대는 스토리**가 있으면 그쪽이 가져가도 된다(DW-616과 같은 자리).
status: done 2026-08-03
resolution: **항목 1(단언 로직 순수 함수화)은 Story 13.9가 처리했다** — `test_live_smoke.py`에 `_missing_span_kinds(runs, node_names) -> list[str]`를 추출해 `test_live_smoke_langsmith_tracing`의 폴링 루프·최종 단언이 이 함수를 호출하게 바꿨다. 모듈 단위 `pytestmark` skipif를 6개 라이브 테스트 각각의 `@_live_only` 데코레이터로 바꿔, 이 순수 함수의 단위테스트(`test_missing_span_kinds_*` 5건)가 `RUN_LIVE_SMOKE`와 무관하게 항상 돈다(**"그 함수만 단위테스트한다"** 요건 충족). 양방향 실증(B4): `node` 판정 분기를 지우자 `test_missing_span_kinds_detects_missing_node_span`·`test_missing_span_kinds_detects_both_missing` 2건이 실제로 red가 됐고, 원복해 green 재확인했다. **항목 2(CORS 견본 비대칭)는 13.9가 다루지 않는다** — `.env.example`을 손대는 스토리가 아니므로 trigger가 예정한 대로 그 스토리에 넘긴다. 이 이월을 "지정한 곳에 심는다"(B8)는 원칙에 따라 DW-642로 재등재했다.

### DW-642: 루트/api `.env.example`의 CORS 키 비대칭 2건이 의도인지 누락인지 아직 미확인이다

origin: DW-641 항목 2를 Story 13.9가 그대로 이월(2026-08-03) — 13.9는 `.env.example`을 손대는 스토리가 아니라 판단을 내리지 않았다.
location: `.env.example`(루트, api 섹션) · `api/.env.example`(CORS 블록) · `api/tests/test_env_example_parity.py`(`_KNOWN_API_ONLY`가 `CORS_ORIGINS`·`CORS_ORIGIN_REGEX` 2건을 동결)
severity: low
reason: `api/.env.example`에만 있는 `CORS_ORIGINS`·`CORS_ORIGIN_REGEX` 2개가 (a) 루트 견본에 일부러 안 옮긴 것인지, (b) 옮기는 걸 깜빡한 것인지 판단된 적이 없다. 현재 파리티 테스트는 이 2건을 `_KNOWN_API_ONLY`로 동결해 새 비대칭만 잡고 이 2건은 통과시킨다 — 안전하지만 "왜 다른가"라는 질문 자체는 열려 있다.
trigger: **`.env.example`(루트 또는 api)을 다음에 손대는 스토리 착수 시** — 그 스토리가 (a) 루트 견본에 CORS 키를 추가해 완전 일치시키거나, (b) "CORS는 api 전용이라 루트엔 안 둔다"를 근거와 함께 확정하고 `_KNOWN_API_ONLY`에 그 근거를 주석으로 남긴다.
status: open

### DW-643: `_bmad-output/implementation-artifacts/epic-13-context.md`의 작업트리 내용이 커밋(HEAD)보다 오래된 판본으로 되돌려져 있다

origin: Story 13.9 작업 중(2026-08-03) 우연히 발견 — 이 파일을 스펙 Code Map이 지정하지 않아 직접 손대지 않았으나, `git status`에서 미커밋 수정으로 나타남.
location: `_bmad-output/implementation-artifacts/epic-13-context.md`
severity: low
reason: `git diff`로 확인한 결과, 작업트리의 현재 내용이 HEAD(커밋 `1cf5d7a`, 13.9 착수 시점의 최신 커밋)에 있는 **더 상세한 판본**(13.9 라우팅 결함·RESET teardown·G2 두-단계 판정 등을 담은 문단)을 **더 단순하고 오래된 문단**으로 되돌린 상태다. 이 세션은 이 파일을 한 번도 Edit하지 않았고(Code Map에도 없음), mtime 분석 결과 이 변경은 세션 시작 전부터 작업트리에 있었던 것으로 보인다(정확한 원인 미상 — 동시에 실행 중이었을 수 있는 다른 프로세스/세션의 산물일 가능성). CLAUDE.md B3(외과적 변경)에 따라 이 스토리 스코프 밖의 변경을 되돌리거나 덮어쓰지 않고 그대로 두었다.
trigger: **다음에 이 파일을 여는 사람이 즉시 판단** — `git diff -- _bmad-output/implementation-artifacts/epic-13-context.md`로 실제 차이를 확인하고, 의도된 변경이 아니면 `git checkout -- <path>`로 HEAD 판본을 복원한다. 의도된 변경(예: 별도 세션이 문서를 의도적으로 단순화)이면 이 항목을 닫고 이유를 남긴다.
status: done 2026-08-03
resolution: 원인이 확인됐다 — 별도 프로세스가 아니라 **이 스토리를 착수한 같은 세션의 step-01**이다. `epics-increment-2026-07-12.md`(직전 커밋 `1cf5d7a`가 13.9 초안을 본문에 반영하며 갱신)가 캐시된 `epic-13-context.md`보다 최신이라 무효 판정돼, `compile-epic-context.md` 절차로 재컴파일됐다(계획 산출물만 소스로 삼음). 더 "상세한" HEAD 판본은 사실 13.8 후속 리뷰가 `compile-epic-context.md` 자신의 규칙("Nothing derivable from the codebase" · "No story-level details" · "describe by purpose, not by source")을 어기고 코드리뷰발 세부사항(상수명·DW 번호·파일 경로)을 되채워 넣은 상태였다 — 재컴파일이 그 규칙 위반을 되돌려 정상화한 것이지 정보가 유실된 게 아니다. **연속성 손실 없음**: 이 스토리의 계획(step-02)은 캐시가 아니라 `epics-increment-2026-07-12.md` 원문을 직접 읽어 13.9 요구사항을 확보했으므로, 재컴파일이 지운 세부사항에 의존하지 않았다. 에픽 13은 이 스토리로 종료되므로 다음 재컴파일 시점도 없다.

### DW-644: `epics-increment-2026-07-12.md`가 되묻기 상한을 "클라이언트가 강제"한다고 적어 실제 코드(서버 강제)와 반대다

origin: Story 13.9 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 `api/app/graph/graph.py`의 `_CLARIFY_TURN_CAP`·`_clarify_step` 원문으로 반대 사실을 확인. Story 13.9 diff가 같은 파일의 다른 자리(가이드 문서 개수, DW-620)를 이미 고쳤으나 이 줄은 스펙 스코프 밖이라 손대지 않음.
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(Story 13.4 되묻기 상한 서술 근처, "클라이언트가 강제" 표현)
severity: medium
reason: 실제로는 서버(`graph.py`의 `_CLARIFY_TURN_CAP`·`_clarify_step`)가 클라이언트 협조와 무관하게 상한을 강제한다 — 이는 DW-563이 이미 "클라이언트만 세는 상한은 상한이 아니다"로 확정한 설계 결정이고 `epic-13-context.md`에는 이 반대 방향(서버 강제)이 이미 정확히 반영돼 있다. 원본 계획 문서에만 뒤집힌 문장이 남아, 이 문서만 읽는 다음 사람이 "클라이언트가 알아서 멈추므로 서버 쪽엔 안전장치가 없다"고 오해하면 향후 변경에서 서버측 강제를 실수로 제거해도 문제로 안 보일 위험이 있다.
trigger: `epics-increment-2026-07-12.md`의 Story 13.4 절을 다음에 손대는 사람 — "클라이언트가 강제"를 "서버(`_CLARIFY_TURN_CAP`)가 강제, 클라이언트는 참고만"으로 정정한다.
status: open

### DW-645: 라우터의 최상급 규칙이 가격 축에만 닫혀 있다 — 연식·주행거리·연비 최상급은 여전히 CLARIFY로 샌다

origin: Story 13.9 후속 리뷰 — edge-case-hunter 렌즈 발견, 오케스트레이터가 `_SYSTEM_PROMPT` 원문과 `_has_superlative` 실행으로 확인.
location: `api/app/graph/router_node.py`(`_SYSTEM_PROMPT` 최상급 규칙·예시), `api/app/graph/hybrid_rag_node.py`(`_SUPERLATIVE_PRICE_RE`), `api/app/graph/contextualize_node.py`(`_SUPERLATIVE_PRICE_RE`)
severity: medium
reason: 13.9가 넣은 규칙은 "제일/가장 + 싸다·비싸다·저렴하다"(가격 형용사)만 구조조건으로 인정한다. 그런데 `listings`에는 정렬 가능한 축이 더 있다 — `year`·`mileage`·`displacement`. "제일 주행거리 짧은 차"·"가장 최신 연식"은 주관적 최상급이 아니라 명백한 구조조건인데도 규칙·예시가 없어 DW-611이 고치려던 CLARIFY 오분류가 그대로 남는다. 스펙 Never 절이 범위 밖으로 명시한 것은 "주관적 최상급"(제일 좋은·가장 예쁜)이지 객관적 정렬축이 아니므로, 이 축은 의도적 유예가 아니라 미처 못 본 자리다. 세 파일이 같은 어휘 정의를 각자 들고 있어(Design Notes의 "공유 유틸 대신 지역 상수" 결정) 축을 넓힐 때 세 곳을 함께 봐야 한다.
trigger: 다음 라우팅·큐리셋 관련 스토리 착수 시(가격 외 정렬축 질의를 큐리셋에 추가하는 시점) — 규칙·예시를 넓히고 재캡처로 실측 확인한다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. 위 correction으로 범위가 축소된 잔여분(비가격 최상급에서 맥락 리셋 판정·캐비엇 문구가 동작하지 않음)만 다룬다.
correction (2026-08-05): **제목의 핵심 주장("연식·주행거리 최상급은 CLARIFY로 샌다")은 실측으로 반증됐다 — 이 항목의 범위를 좁힌다.** 원 등재는 `_SYSTEM_PROMPT` 원문 읽기 + `_has_superlative` 정규식 직접 실행으로 판정했는데, **둘 다 파이프라인의 실제 동작이 아니다**(정규식은 라우팅에 관여하지 않는다 — 아래). 라이브 재현 결과(로컬 API, LangSmith 트레이싱 ON, 2026-08-05):
  · `연식 가장 최신인 차` → **SQL**, 5건 전부 2023년(정렬 정확) ✅
  · `주행거리 제일 적은 차` → **SQL**, `14000·14000·17000·18000·18000`km 오름차순(정렬 정확) ✅
  · `제일 싼차`·`가장 싼거`(붙여쓰기, DW-653이 빠졌다고 본 형태) → **SQL**, 가격 오름차순 정확 ✅
  되묻기로 새는 질의는 **0건**이었다. 이유는 구조에 있다: 4분기 라우팅은 **오직 LLM**(`router_node.py:133-138`, `RouterDecision.route`의 `Literal` 강제)이 정하고, `_SUPERLATIVE_PRICE_RE`는 라우팅에 **전혀 관여하지 않는다** — 그 정규식이 실제로 쓰이는 곳은 ① `contextualize_node._is_topic_shift`(멀티턴 맥락을 유지할지 리셋할지) ② `hybrid_rag_node._has_superlative`(HYBRID 결과에 "가격 정렬 미반영" 캐비엇 문구를 붙일지) 둘뿐이다. 프롬프트의 최상급 예시가 가격에 치우친 것은 사실이나, LLM은 그 예시에 없는 축(연식·주행거리)도 "명시적 조건"으로 일반화해 SQL로 보낸다.
  **남는 진짜 범위(이것만 유효)**: (a) 두 정규식이 가격 축에만 열려 있어 **비가격 최상급에서는 맥락 리셋 판정·캐비엇 문구가 동작하지 않는다**(결과가 틀리는 게 아니라 부가 판단이 빠진다), (b) 프롬프트 예시에 비가격 축이 없어 향후 모델 교체 시 회귀 위험이 남는다. 실피해 등급을 medium → **low**로 낮춘다.
  **교훈(B4)**: 이 항목도, 같이 취소된 DW-656도, 원인이 같다 — **보조 함수·프롬프트 원문을 읽고 사용자 대면 동작을 단정했다.** 최상급·라우팅 관련 주장은 반드시 `/ai/search`를 실제로 호출해 확인할 것.

### DW-646: G2 게이트가 `scored_n` 개수만 비교하고 채점된 **문항 집합**은 비교하지 않는다

origin: Story 13.9 후속 리뷰 — edge-case-hunter 렌즈 발견, 오케스트레이터가 `score_ab.py`의 `coverage` 구조로 확인.
location: `api/scripts/score_ab.py`(`coverage_matches` 계산부), `score_model()`의 `coverage` 딕트
severity: low
reason: 13.9가 넣은 커버리지 가드는 `baseline["coverage"]["scored_n"] == candidate["coverage"]["scored_n"]`로 **개수**만 본다. 개수가 같아도 서로 다른 문항 집합이 채점된 경우(예: baseline은 S계열 3건이 죽고 candidate는 M계열 3건이 죽은 부분 재캡처)는 통과하고, 그러면 분모는 같지만 비교 대상이 달라 개수 3축이 조용히 무의미해진다. `coverage`에 이미 `missing_ids`가 있으므로 채점된 id 집합을 함께 실어 비교하면 닫히지만, `score_model()` 반환 구조를 손대는 일이라 13.9 스코프 밖으로 미룬다.
trigger: `score_ab.py`의 `coverage` 구조를 다음에 손대는 스토리, 또는 부분 재캡처가 실제로 필요해지는 시점 — `scored_ids` 집합 비교로 바꾸고 red/green으로 확인한다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. DW-647과 같은 채점기 파일을 건드리므로 함께 한다.

### DW-647: 큐리셋의 `count_range`를 스코어러가 한 번도 읽지 않는다 — 선언만 있고 검사가 없다

origin: Story 13.9 후속 리뷰 — intent-alignment 렌즈 발견, 오케스트레이터가 `grep count_range api/scripts/` 0건으로 확인.
location: `api/docs/ai-ab-test-queryset.json`(S6·M1.t2·M2.t3 등의 `predicate.count_range`), `api/scripts/score_ab.py`(topn 채점부)
severity: low
reason: 큐리셋은 S6에 `count_range:[1,1]`을 선언하지만 스코어러의 topn 모드는 `returned[:len(gold_order)]`, 즉 **선두 N건만** 비교한다. 실제 2026-08-03 재캡처에서 S6·M2.t3은 5건을 반환했는데도 `result:1.0`이다 — "제일 싼 차 뭐야?"에 `LIMIT 1`이 걸렸는지는 게이트가 보지 않는다. 에픽 13이 반복해 학습한 "선언만 하고 못 잡는 게이트"의 또 다른 사례이며, 스펙 I/O 매트릭스가 `ORDER BY price ASC LIMIT 1`을 기대값으로 적은 것과도 어긋난다. 다만 라우팅 정답률·결과집합 정확도라는 주 지표는 이 축 없이도 성립하므로 회귀는 아니다.
trigger: 큐리셋·스코어러를 다음에 손대는 스토리 — `count_range`를 실제 채점 축으로 넣고, 일부러 개수를 어긋나게 해 red를 확인한다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. DW-652와 반드시 같은 작업에서 — 채점이 개수를 보기 시작하면 S6가 즉시 red가 되므로, 생성 쪽(LIMIT 1)을 같이 안 고치면 게이트만 빨개진다.

### DW-648: 최상급+가격형용사가 비-매물 주제에 붙으면 여전히 맥락이 접힌다 (13.9 P3/P4 수정의 알려진 잔여 구멍)

origin: Story 13.9 후속 리뷰 — edge-case-hunter 렌즈 발견, 오케스트레이터가 수정 후 `_is_topic_shift`를 직접 실행해 잔존 확인.
location: `api/app/graph/contextualize_node.py`(`_is_topic_shift` 3단계, `_SUPERLATIVE_PRICE_RE`)
severity: low
reason: 후속 리뷰가 "제일 좋은 자동차보험 알려줘"류(최상급이지만 가격 형용사 없음)의 오판을 고치면서, 판정 기준을 라우터 프롬프트와 같은 "최상급 부사 + 가격 형용사 결합"으로 맞췄다. 그 결과 `제일 좋은 자동차보험`·`제일 인기있는 여행지`는 정상적으로 리셋되지만, `가장 싼 할부 이자율이 뭐야?`처럼 **가격 형용사를 포함한 비-매물 주제**는 여전히 리파인으로 오판돼 앞선 매물 조건(차종·가격)이 접혀 들어간다. 제대로 닫으려면 비-매물 주제 어휘(보험·할부·이자율·여행 등)를 판정에 넣어야 하는데, 그건 새 어휘 사전을 도입하는 별개 설계라 13.9의 최소 침습 범위 밖이다. 실피해는 REJECT 분기가 뒤에서 걸러 주므로 제한적이다.
trigger: `contextualize_node`의 주제전환 판정을 다음에 손대는 스토리, 또는 비-매물 질의 오분류가 실제 재캡처에서 관측되는 시점.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건.

### DW-649: DW-625·DW-630이 요구한 작업의 일부가 미이행인 채 종결됐다 — 잔여분을 여기서 이어받는다

origin: Story 13.9 후속 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 두 항목의 resolution 원문과 실제 코드로 확인. 기존 항목의 status·resolution은 오케스트레이터 소관이므로 수정하지 않고 잔여 의무만 신규로 등재한다.
location: `api/tests/conftest.py`(라이브 스모크 스킵 감지 훅 부재), 13.8 CM-B 재실행 절차
severity: medium
reason: 두 가지다. (1) DW-630은 "라이브 스모크가 전량 스킵돼도 게이트가 초록으로 보인다"는 문제였고 두 가지 조치(conftest 훅 / 커맨드에 `-rs`+개수 못박기) 중 후자를 택했다고 기록됐으나, 13.9 스펙에 커밋된 커맨드엔 실제로 `-rs`가 없었다(후속 리뷰가 P12로 스펙 커맨드는 정정했다). 남은 것은 **커맨드가 아니라 코드로 강제하는 층** — 사람이 커맨드를 복붙하지 않고 CI가 돌 때도 전량 스킵이 실패로 보이게 하려면 conftest 훅이 필요하다(CLAUDE.md B9: 규칙은 어길 수 없는 자리에 박는다). (2) DW-625는 resolution 자신이 "13.9는 CM-B 전수 재실행을 스코프에 두지 않았으므로 그 다음 CM-B 재실행 시점에 확인된다"고 적고도 종결됐고, 그 확인 의무를 이어받는 항목이 없었다.
trigger: 다음 CM-B(에픽 검증 커맨드 묶음) 전수 재실행 시점 — 그때 (2)의 확인을 수행하고, 같은 작업에서 (1)의 conftest 훅을 넣어 전량 스킵을 red로 만든다(일부러 스킵시켜 red 확인).
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건.

### DW-650: DW-644의 `trigger:`가 실제 파일에 없는 문자열을 인용하고 있어 담당자가 못 찾을 수 있다

origin: Story 13.9 후속 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 `epics-increment-2026-07-12.md` 원문 grep으로 확인. 기존 항목 본문은 오케스트레이터 소관이라 수정하지 않고 정정 사항만 신규로 남긴다.
location: `_bmad-output/implementation-artifacts/deferred-work.md`(DW-644의 location·trigger), `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(1029행 "클라 강제 I12", 173행 UX-DR23, 1412행)
severity: low
reason: DW-644는 정정 대상 표현을 "클라이언트가 강제"로 인용했는데 파일의 실제 표현은 **"클라 강제 I12"**다. 그대로 grep하면 0건이 나와 담당자가 "이미 고쳐졌다"고 판단해 닫아버리기 쉽다. 또 되묻기 상한 서술은 한 자리가 아니라 최소 세 자리(173·1029·1412행)에 흩어져 있어, 한 곳만 고치면 나머지가 남는다. DW-644가 근거로 든 "`epic-13-context.md`에는 서버 강제가 정확히 반영돼 있다"는 서술 자체는 유효하다(같은 커밋의 재컴파일이 그 줄을 지웠던 것을 후속 리뷰 P9가 복원했다).
trigger: DW-644를 실제로 처리하는 사람 — 이 항목을 함께 읽고 "클라 강제 I12"로 검색해 세 자리를 모두 정정한다.
status: open

### DW-651: 스펙이 약속한 "최상급×HYBRID 재검토 트리거" 장부 항목이 실제로는 등재된 적이 없다

origin: Story 13.9 3차 리뷰 — adversarial 렌즈 발견, 오케스트레이터가 `deferred-work.md` 전문 grep(패밀리카·최상급×HYBRID·정렬 미적용·캐비엇) 0건으로 확인.
location: `_bmad-output/implementation-artifacts/spec-13-9-라우팅-안정화-최상급-교체요청-맥락재작성.md`(Design Notes "옵션(b) 채택 근거" 마지막 문장) · `api/app/graph/hybrid_rag_node.py`(캐비엇 부착부)
severity: medium
reason: 스펙 Design Notes는 옵션(b)를 택하면서 "이 조합이 실제로 관측되면(향후 큐리셋에 항목이 생기면) 그때 (a)/(c)를 재검토한다 — deferred-work.md에 그 트리거로 신규 항목을 남긴다"고 명시적으로 약속했는데, 장부에 그 항목이 없다. 그래서 지금 "제일 싼 패밀리카"류는 라우터 프롬프트가 최상급을 구조조건이라 선언해 놓고도 HYBRID 경로에서 정렬을 버리고 캐비엇 문장으로 대체하는 상태이며, 그 사실이 코드 주석과 사용자 응답 문자열에만 산다. DW-645(가격 외 정렬축)·DW-647(count_range 미채점)은 인접하지만 다른 축이다 — 이 항목만이 "최상급이 HYBRID에서 통째로 버려진다"를 다룬다. CLAUDE.md B8("미룬 것도 대장에 적는다 — 미루는 판단은 틀린 게 아니고 안 적는 게 틀린 거다")이 정확히 이 자리를 가리킨다.
trigger: **큐리셋(`api/docs/ai-ab-test-queryset.json`)에 "최상급+의미조건" 항목이 처음 추가되는 시점** — 그때 옵션(a)(SQL로 보내 정렬 살리기)와 (c)(`sql_guard` 2차 정렬키 차단 재검토, 보안 결정)를 실측 근거 위에서 재검토한다. 그 전까지는 옵션(b)(정렬 포기 + 캐비엇 고지)가 확정된 동작이다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. 이 항목의 원래 trigger('큐리셋에 최상급+의미조건 항목이 처음 추가되는 시점')는 2026-08-05 하이브리드 15문항 추가(H13~H27)로 **이미 도래했다** — 그 문항들이 최상급을 안 쓰긴 하지만 큐리셋을 손댄 시점 자체가 재검토 자리였다.

### DW-652: `제일 싼 차 뭐야?`가 여전히 5건을 반환한다 — 큐리셋의 `predicate.limit:1`을 SQL 생성이 지키지 않는다

origin: Story 13.9 3차 리뷰 — adversarial·intent-alignment 렌즈 독립 일치, 오케스트레이터가 커밋된 재캡처 원문으로 확인.
location: `api/app/graph/sql_rag_node.py`(LLM SQL 생성 프롬프트) · `api/app/db/sql_guard.py`(`DEFAULT_LIMIT=5` 주입) · `api/docs/ai-ab-test-queryset.json`(S6의 `predicate: {order: "price ASC", limit: 1}`)
severity: low
reason: 13.9는 S6를 CLARIFY→SQL로 고쳤고 그것이 라우팅 57/57의 근거지만, 커밋된 `docs/g2-recapture-2026-08-03.json`의 S6는 매물 **5건**(`"조건에 맞는 매물 5건을 찾았어요."`)을 반환한다 — 생성 SQL에 `LIMIT 1`이 없어 `sql_guard`의 `DEFAULT_LIMIT=5`가 주입된 결과다. 스펙 I/O 매트릭스가 기대출력으로 적은 `ORDER BY price ASC LIMIT 1`의 **정렬 절반만** 달성된 셈이다. 실피해는 제한적이다 — 정렬은 실제로 맞고(스코어러의 `score_path_a`가 순서 민감 top-1 비교로 `result:1.0`을 준다) 사용자는 최저가 매물을 첫 번째로 본다. DW-647은 이 문제의 **게이트 쪽 절반**(스코어러가 `count_range`를 안 읽어 관측 자체가 안 된다)만 다루고, **생성 쪽 절반**(LLM이 최상급 질의에 `LIMIT 1`을 안 낸다)은 어느 항목도 안 맡고 있다. 13.9의 Code Map·Approach가 `sql_rag_node`를 손대지 않기로 했으므로 이 스토리 범위 밖이지만, 스토리 이름이 된 바로 그 질의라 기록 없이 두면 "S6는 닫혔다"로 읽힌다.
trigger: **DW-647을 처리해 `count_range`가 실제 채점 축이 되는 그 자리** — 채점이 개수를 보기 시작하면 S6가 즉시 red가 되므로, 같은 작업에서 `sql_rag_node` 프롬프트에 "최상급 질의는 `LIMIT 1`" 규칙·예시를 넣고 재캡처로 실측 확인한다. 둘을 따로 하면 게이트만 빨개지고 원인은 안 고쳐진다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. 2026-08-05 라이브 재현으로 현상 재확인: `제일 싼 차 뭐야?` → 생성 SQL이 `ORDER BY price ASC LIMIT 5`. 정렬은 맞고 **개수만 안 줄인다**(DW-656 취소로 확정).

### DW-653: 3차 리뷰 P2가 최상급 정규식을 좁히면서 띄어쓰기 없는 `가장 싼거`·`제일 싼차`가 함께 빠졌다

origin: Story 13.9 3차 리뷰 P2 적용 중 구현 서브에이전트가 자진 신고, 오케스트레이터가 `_has_superlative` 직접 실행으로 확인.
location: `api/app/graph/hybrid_rag_node.py`(`_SUPERLATIVE_PRICE_RE`) · `api/app/graph/contextualize_node.py`(같은 상수, 락스텝)
severity: low
reason: P2는 `가장 싼타페`·`제일 싸지 않은 차`류 오발동을 없애려고 어간형 형용사 뒤에 음절 경계를 요구했다(`(싼|싸|비싼|비싸)(?![가-힣])`, `저렴`은 `저렴한`의 어미 때문에 경계 제외). 그 부작용으로 **띄어쓰기를 생략한** `가장 싼거`·`제일 싼차`가 P2 이전 True에서 False로 바뀌었다 — 어간 바로 뒤에 한글이 붙는다는 점에서 `싼타페`와 정규식상 구분되지 않기 때문이다. 실피해는 작다: 큐리셋의 최상급 문항(S6·S7·M1.t2·M2.t3)은 전부 띄어쓰기 정상형이고, `_REFINE_MARKERS`에 `"더 싼"`이 따로 있어 리파인 신호가 완전히 사라지지는 않는다. 다만 이 좁힘을 고정하는 테스트가 없어, 다음에 정규식을 손대는 사람이 이 경계를 모른 채 되돌리거나 더 좁힐 수 있다.
trigger: **`_SUPERLATIVE_PRICE_RE`를 다음에 손대는 스토리**(DW-645가 연식·주행거리 축으로 넓히는 그 자리) — 그때 형태소 경계를 어간+조사/어미 목록으로 다루도록 바꾸고, `가장 싼거`·`제일 싼차`를 양성 케이스로, `가장 싼타페`를 음성 케이스로 같은 테이블에 함께 고정한다(둘을 한 테스트에서 대조해야 다음 사람이 경계를 본다).
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. 단, 2026-08-05 라이브 실측에서 `제일 싼차`·`가장 싼거`(띄어쓰기 없음)가 **정상적으로 SQL 경로를 타고 가격 오름차순으로 답한다** — 이 정규식은 라우팅에 관여하지 않으므로 사용자 피해는 없다(DW-645 correction 참조). 실피해는 맥락 리셋 판정·캐비엇 부착에 한정된다.

### DW-654: Follow-up review still recommended for 13-9-라우팅-안정화-최상급-교체요청-맥락재작성 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-13-9-라우팅-안정화-최상급-교체요청-맥락재작성.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260803-013219-ca30; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-655: Epic 13의 열린 AI 후속 항목 8건이 **백로그에 없는 작업**을 trigger로 걸고 있다 — DW-640이 닫은 병이 재발했다

origin: Story 13.9 독립 후속 리뷰(DW-654 수행) — 오케스트레이터가 `sprint-status.yaml` 전문과 열린 항목 8건의 `trigger:`를 직접 대조.
location: `_bmad-output/implementation-artifacts/deferred-work.md`(DW-645·646·647·648·649·651·652·653의 `trigger:`) · `_bmad-output/implementation-artifacts/sprint-status.yaml`(Epic 13 블록 — 13-1~13-9 전부 `done`, 남은 항목은 `epic-13-retrospective: optional` 하나)
severity: medium
reason: 위 8건의 trigger를 실측 대조한 결과, **어느 것도 `sprint-status.yaml`에 실재하는 스토리를 가리키지 않는다** — "다음 라우팅·큐리셋 관련 스토리"(DW-645) · "`score_ab.py`의 coverage 구조를 다음에 손대는 스토리"(DW-646) · "큐리셋·스코어러를 다음에 손대는 스토리"(DW-647) · "`contextualize_node`의 주제전환 판정을 다음에 손대는 스토리"(DW-648) · "다음 CM-B 전수 재실행 시점"(DW-649) · "큐리셋에 최상급+의미조건 항목이 처음 추가되는 시점"(DW-651) · "DW-647을 처리하는 그 자리"(DW-652, 없는 스토리에 연쇄) · "`_SUPERLATIVE_PRICE_RE`를 다음에 손대는 스토리(DW-645가 넓히는 자리)"(DW-653, 역시 연쇄). Epic 13은 13-1~13-9가 전부 `done`이라 그 "다음 스토리"가 존재하지 않고, 백로그에 남은 Epic 14(계정 역할 통합)·15(관리자 UI)·16(Flutter 증분)은 어느 것도 AI 검색 RAG 코드를 건드리지 않는다. **이건 DW-640이 4건에 대해 이미 진단하고 닫은 것과 똑같은 병이 8건 규모로 재발한 것이다** — 그때의 해법(trigger를 실재 스토리의 인수조건으로 재지정)이 절차로 남지 않아서다. 지금 Epic 13을 종료하면 8건이 전부 조용히 사라진다(CLAUDE.md B8: "미룬 항목엔 언제·어디서 고칠지를 대장에 함께 적는다 — '이월'만 적으면 조용히 또 밀린다"). 실피해 등급은 medium이다: 8건 중 기능 결함은 DW-645(가격 외 정렬축이 CLARIFY로 샘)·DW-652(`제일 싼 차 뭐야?`가 5건 반환)뿐이고 나머지는 게이트 정밀도·문서 정합이지만, 둘 다 이 에픽의 헤드라인 질의에 직접 걸린다.
trigger: **`epic-13-retrospective`**(`sprint-status.yaml`에 실재하는 항목, 현재 `optional`) — 에픽 13 종료 판단을 하는 그 자리에서 위 8건을 한 번에 훑고, (a) Epic 13에 스토리를 하나 더 열어 흡수할지 (b) 새 에픽으로 묶을지 (c) 명시적으로 수용(닫음)할지를 사용자와 함께 정한 뒤, 남기기로 한 항목의 trigger를 그때 실재하게 된 스토리 키로 재지정한다. 회고를 `optional`로 건너뛰면 이 항목도 함께 사라지므로, **에픽 13은 회고를 돌리기 전에는 닫지 않는다**가 이 항목의 요지다.
status: done
resolution (2026-08-05 회고): **해소.** 이 항목이 요구한 대로 `epic-13-retrospective`에서 열린 AI 후속 항목을 전수 훑고 처분을 정했다 — (a)안을 택해 **에픽 13에 스토리 2개를 신설**(`13-10-검색-데이터-보강`·`13-11-sql-생성-정비-채점축-확장-재캡처`)하고 각 항목의 trigger를 그 실재 스토리 키로 재지정했다(이 파일의 `retarget (2026-08-05 회고):` 줄들). **`epic-13`은 `done`이 아니라 `in-progress`로 뒀다** — 닫힌 에픽 안의 스토리를 가리키면 이 병이 세 번째로 재발하기 때문이다(회고 진행 중 사용자가 지적). 13-11 완료 시 에픽을 닫는다.

### DW-656: `제일 싼 차 뭐야?`는 개수뿐 아니라 **정렬도 틀렸다** — DW-652가 절반만 기록했다

origin: 2026-08-03 사용자 수동 확인 요청으로 오케스트레이터가 커밋된 캡처 원문을 매물 단위로 대조하다 발견. DW-652의 인접 사실이지만 **다른 결함**이다(기존 항목 무수정 원칙에 따라 신규 등재).
location: `api/app/graph/sql_rag_node.py`(LLM SQL 생성 — `ORDER BY`를 안 냄) · `api/docs/g2-baseline.json`의 `S6` · `api/scripts/score_ab.py`(`score_path_a`의 topn 분기)
severity: medium
reason: DW-652는 "`limit:1`을 안 지켜 5건이 나온다"만 적었다. 그런데 커밋된 최신 캡처(13.9 반영본)의 S6 반환 5건을 실제 매물로 펼쳐 보면 **가격 오름차순이 아니다** — `아반떼MD 650만 · 스파크 580만 · 아반떼MD 520만 · 스파크 580만 · 올란도 490만` 순으로, **최저가(490만)가 맨 마지막**이다. 즉 `ORDER BY price ASC` 자체가 생성되지 않았고, "제일 싼 차"라는 질의의 **핵심 의미가 결과에 반영되지 않았다.** 개수만 1건으로 줄여도(DW-652 처방) 정렬이 없으면 **엉뚱한 1건**(650만 아반떼)이 나온다 — 두 결함을 함께 고쳐야 질의가 실제로 답해진다.
  ⚠️ 채점이 이것을 놓친 이유도 함께 기록한다: `score_path_a`는 `predicate`에 `limit`과 `order`가 **둘 다** 있을 때만 topn(순서 민감) 모드로 채점하고, 그 모드는 `returned[:len(gold)]`로 **선두 1건만** 골든과 대조한다. S6의 골든 1건(올란도 490만)이 반환 5건 안에 **포함돼 있기만 하면**… 실제로는 선두가 아니라 5번째라 topn은 0.0이어야 맞는데, 커밋된 리포트의 S6는 `result: 1.0`이다. **채점기와 캡처 중 하나가 어긋나 있으므로 이 항목의 착수 시 그 불일치부터 재현해 원인을 확정한다**(코드를 읽어 추정하지 말 것 — B4).
trigger: **DW-652·DW-645·DW-647을 함께 처리하는 그 작업에서 같이 한다**(DW-655가 제안한 "AI 후속 스토리"의 범위 — 최상급 정렬축 확장 + `LIMIT 1` + `count_range` 채점 + 라이브 재캡처). 정렬은 그 묶음의 첫 항목이다: 정렬이 없으면 `LIMIT 1`은 오히려 결과를 더 나쁘게 만든다. 해당 스토리가 아직 백로그에 없으므로 **에픽 13 회고에서 그 스토리를 만들 때 이 항목을 범위에 포함**한다.
status: invalid
resolution: **2026-08-05 오진으로 확인 — 취소한다.** 이 항목의 전제("최저가가 맨 마지막")가 틀렸다. 원인은 등재 당시의 확인 방법이다: 캡처 파일(`g2-baseline.json`)은 반환 **순서대로** `ids_last`에 id만 저장하는데, 그 id들을 `SELECT ... WHERE id IN (...)`로 조회해 가격을 붙였다. **`IN` 조회의 반환 순서는 인자 순서와 무관**하므로 그 임의 순서를 결과 순서로 착각했다. 실제 `ids_last`를 순서 그대로 펼치면 `올란도 490만 → 아반떼MD 520만 → 스파크 580만 → 스파크 580만 → 아반떼MD 650만`으로 **가격 오름차순이 맞다**. 2026-08-05 라이브 재현(로컬 API, LangSmith 트레이싱 ON)에서도 동일하게 오름차순이었고, 생성 SQL이 `ORDER BY price ASC LIMIT 5`임을 트레이스로 직접 확인했다 — `ORDER BY`는 정상 생성된다. 따라서 `score_path_a`가 S6에 `result:1.0`을 준 것도 채점기·캡처의 불일치가 아니라 **정상 판정**이며, 이 항목이 제기한 "재현해서 원인을 확정하라"는 숙제는 재현으로 해소됐다. 남는 진짜 결함은 **개수뿐**이며 그건 DW-652가 이미 맡고 있다(중복 없음).

### DW-657: 모델명을 `=` 정확일치로 찾아 `아반떼 보여줘`가 **0건**이다 — 세대명이 붙은 국산 인기 차종 전반이 깨진다

origin: 2026-08-05 사용자 보고(5번 "쏘렌토 하나만 나온다") 조사 중 오케스트레이터가 발견. 라이브 재현 + LangSmith 트레이스로 생성 SQL 직접 확인.
location: `api/app/graph/sql_rag_node.py`(LLM SQL 생성 프롬프트 — 스키마 설명 42행이 `model(모델·자유값)`이라고만 적고 매칭 방식을 규정하지 않음)
severity: **high**
reason: LLM이 모델명 조건을 `model = '아반떼'`로 생성한다. 그런데 DB의 `model`은 자유 입력값이라 실제 저장된 값은 `아반떼 MD` · `아반떼MD` · `아반떼 CN7` · `아반떼 하이브리드`뿐이고 **`아반떼`라는 값은 하나도 없다** → 라이브 실측 **0건**(`"조건에 맞는 매물이 없어요"`). 같은 이유로 `쏘렌토 보여줘`는 `쏘렌토 MQ4`가 빠져 2건 중 **1건만** 나온다. 소나타·그랜저·K5 등 세대명·트림명이 붙은 매물 전반이 같은 구조이므로, **모델명 검색이라는 가장 흔한 사용 방식이 광범위하게 깨져 있다.** 큐리셋이 이 결함을 못 잡은 이유도 함께 기록한다: 62항목 중 모델명을 단독 조건으로 쓰는 문항이 없다(`predicate`에 `model` 키 자체가 없고 `build_golden_sql`도 지원하지 않는다) — 게이트의 사각지대다.
trigger: **DW-652·DW-645·DW-647·DW-653을 함께 처리하는 "SQL 생성 프롬프트 + 재캡처" 스토리**(에픽 13 회고에서 생성). 같은 프롬프트 파일을 고치고 같은 재캡처로 검증하므로 반드시 함께 한다. 처방: 모델명은 `ILIKE '%<모델명>%'` 부분일치로 생성하게 규칙·예시를 넣는다. **동시에 큐리셋에 모델명 단독 문항을 최소 1개 추가**하고(`build_golden_sql`에 `model_like` 지원 추가), 일부러 `=`로 되돌려 red를 확인한다 — 안 그러면 다음에 또 조용히 깨진다.
status: open
retarget (2026-08-05 회고): **`13-11-sql-생성-정비-채점축-확장-재캡처`** 인수조건. 이 스토리의 존재 이유이자 최우선 항목이다(high, 실사용자가 바로 만나는 결함).

### DW-658: LangSmith 트레이싱이 **한 번도 켜진 적이 없다** — `.env`에 값이 있는데 `Settings`가 버린다 (Story 13.7 / FR51 산출물 무효)

origin: 2026-08-05 사용자가 "LangSmith로 판단 근거를 보고 싶다"고 요청 → 오케스트레이터가 LangSmith REST API로 직접 조회해 확인.
location: `api/app/config.py:12-38`(`Settings`가 `langchain_*` 필드 미선언 + `extra="ignore"`) · `scripts/dev-api.sh:34-43`(`LANGCHAIN_*`를 export 안 함) · Cloud Run `encar-ai-api-dev` 환경변수
severity: **high**
reason: `api/.env`에 `LANGCHAIN_TRACING_V2=true`와 실제 API 키가 채워져 있으나, 앱은 pydantic-settings로 `.env`를 읽고 `extra="ignore"`라 선언되지 않은 `LANGCHAIN_*`를 **조용히 버린다**. 반면 langsmith SDK는 `Settings`가 아니라 **`os.environ`을 직접** 읽으므로(견본 파일 `api/.env.example:22-40`이 이 사실을 이미 문서화하고 있다) 값이 전달되지 않는다. 실측: 평소 실행 경로에서 `tracing_is_enabled() == False`. LangSmith `default` 프로젝트의 마지막 run이 **2026-08-02**(전부 가짜 LLM 단위테스트 흔적)이고 그 이후 **0건** — 그 사이 배포 서버가 계속 돌았으므로 **로컬·배포 양쪽 모두 꺼져 있었다**. 즉 Story 13.7이 산출물이라고 주장한 관측 능력이 실제로는 존재한 적이 없고, 이번에 사용자가 보고한 결함 2건(5·6번)을 사후 조사할 수단이 없어 **라이브 재현으로 다시 만들어야 했다**. 에픽 13이 다섯 번 반복 학습한 "선언은 있는데 실제로는 안 도는" 패턴의 또 다른 사례다. 임시 해소는 확인됨 — 기동 전 두 값을 OS 환경변수로 export하면 `True`가 되고 트레이스가 실제로 업로드된다(2026-08-05 프로젝트 `repro-2026-08-05`로 실증).
trigger: **다음에 `api/app/config.py` 또는 배포 환경변수를 손대는 스토리**(없다면 에픽 13 회고에서 신규 스토리로 생성 — DW-659와 한 묶음). 처방 3종: ① 앱 기동 시 `.env`의 `LANGCHAIN_*`를 `os.environ`으로 승격 ② Cloud Run에도 동일 환경변수 주입 ③ **실제로 트레이스가 1건이라도 업로드되는지 확인하는 검사**(①②만 하면 또 조용히 꺼져도 아무도 모른다 — B9). ③이 이 항목의 핵심이며, "환경변수 해석 규칙"만 보는 기존 `tests/test_langsmith_env_contract.py`는 이 축을 보지 않는다(그 파일 자신이 "안 보는 것"으로 명시).
status: done
resolution (2026-08-05): **해소.** `api/app/config.py`가 `.env`의 `LANGCHAIN_*`를 모듈 로드 시점에 `os.environ`으로 승격한다(OS 값이 있으면 덮지 않음, pytest 세션은 건너뜀). 커밋 `9988976`. 실측: 평소 실행 경로(`bash scripts/dev-api.sh`)로 기동해 질의 1건 → LangSmith `default` 프로젝트에 `2026-08-05T13:05:56 success` 업로드 확인(08-02 이후 3일 만의 첫 트레이스). 배포(Cloud Run 운영·개발)는 사용자가 환경변수를 넣고 재배포했고, 배포 서버를 직접 호출해 `2026-08-05T13:23:49 success` 트레이스 업로드를 실측 확인했다. 신규 검사 `api/tests/test_langsmith_env_promotion.py`(4건, OS 우선 가드를 지우면 red).

### DW-659: 앱 로그의 INFO가 전부 버려진다 — `logging.basicConfig`가 없어 라우팅 결정·생성 SQL·결과 건수가 아무 데도 안 남는다

origin: 2026-08-05 DW-658과 같은 조사에서 발견. 오케스트레이터가 uvicorn 로깅 설정을 실제로 재현해 확인.
location: `api/app/main.py` · `api/app/config.py`(둘 다 `logging.basicConfig`/`LOG_LEVEL` 없음) · `api/app/graph/*.py`의 `logger.info` 호출부
severity: medium
reason: 그래프 노드들은 진단에 필요한 값을 이미 `logger.info`로 남기도록 짜여 있다 — `router_node.py:147`(질의+결정 경로), `contextualize_node.py:306`(재작성된 질의), `sql_rag_node.py:168`(**생성 SQL 전문**), `hybrid_rag_node.py:206`(추출 구조조건), `doc_rag_node.py:125-127`(질의+결과 건수+근거 가이드). 그런데 `logging.basicConfig`가 어디에도 없어 루트 로거가 파이썬 기본값 WARNING(30)에 머물고, uvicorn이 적용하는 `dictConfig`는 `uvicorn*` 로거만 INFO로 올릴 뿐 `app.graph.*`를 건드리지 않는다(실측 재현 확인). 결과적으로 **위 INFO 로그 전부가 소리 없이 버려지고** WARNING만 서식 없이 stderr로 샌다. 파일 핸들러도 없어 저장되지 않으며, AI 대화를 담는 DB 테이블도 없다(무상태 — 의도된 설계). 그래서 사용자 보고 결함의 사후 조사 수단이 LangSmith(DW-658으로 역시 꺼짐)와 로그 **양쪽 다** 없는 상태였다.
trigger: **DW-658과 같은 스토리에서 함께 처리한다** — 둘 다 "관측 수단이 있다고 믿었는데 없었다"는 같은 병이고, 같은 파일권(`api/app/` 기동부)을 건드린다. 처방: 로그 레벨·서식 설정 1곳 추가(환경변수로 조절 가능하게) + **INFO 한 줄이 실제로 출력되는지 확인하는 검사**. 배포(Cloud Run)는 stdout을 자동 수집하므로 레벨만 열면 수집될 것으로 보이나 **이 PC에 gcloud가 없어 미확인** — 착수 시 실측할 것(B4: 재보기 전엔 선언하지 않는다).
status: done
resolution (2026-08-05): **해소.** `api/app/main.py`가 루트 로거 레벨을 `LOG_LEVEL`(기본 INFO)로 설정하고 stdout + `.logs/api.log`(5MB×3 회전)에 남긴다. 커밋 `9988976`. 실측: 라이브 질의 1건에 `router_node … → route=HYBRID` · `find_relevant_guide 거리=0.2695 …` · `hybrid_rag_node attempt 1 구조조건: …`이 실제로 파일에 기록됨. 웹 쪽(커밋 `dabfd9a`)은 `aiSearch.ts`·`ChatAssistant.tsx`가 실패 원인(네트워크/HTTP 상태+본문/JSON 파싱)을 `console.error`로 남기게 했다 — 실패 3종을 실제 재현해 확인. 신규 검사 `api/tests/test_logging_setup.py`(4건, `setLevel`을 지우면 red). **남는 미확인**: Cloud Run이 stdout을 실제로 수집하는지는 여전히 미확인(gcloud는 2026-08-05에 설치했으나 인증 미완) — 그 확인은 A4(#168)와 함께 Epic 15에서 한다.

### DW-660: 조건이 많이 섞인 질의일수록 가이드가 안 붙는다 — 컷오프 0.3이 짧은 질의 기준으로 잡혀 있다

origin: 2026-08-05 Story 13-11 재캡처에서 가이드 인용이 12/13(92%) → 18/28(64%)로 떨어진 것을 오케스트레이터가 추적. `find_relevant_guide`를 직접 호출해 거리를 실측.
location: `api/app/graph/doc_rag_node.py`(`_GUIDE_DISTANCE_CUTOFF = 0.3`) · `api/docs/ai-ab-test-queryset.json`(H13·H18~H27 등 조건 밀집 문항)
severity: medium
reason: 가이드는 질의 임베딩과 가이드 문서의 코사인 거리가 **0.3 이내일 때만** 주입된다. 그런데 조건을 여러 개 붙일수록 질의 임베딩의 의미 중심이 어느 가이드에서도 멀어져 컷오프를 넘는다. 실측(같은 가이드 '패밀리카로 무난한 차종 고르기'에 대한 거리):
  · `3천만원 이하로 무난한 패밀리카 찾아줘`(21자) → **0.2575** 통과
  · `캠핑 다니기 좋은 차`(11자) → **0.2987** 통과
  · `3천만원 이하 무사고 패밀리카 중에 후방카메라랑 통풍시트 둘 다 있는 걸로 보여줘`(45자) → **0.3005** 탈락(**0.0005 차이**)
  · `4천만원 이하로 캠핑 다니기 좋은 차 중에 파노라마선루프 있고 무사고인 거`(41자) → **0.3182** 탈락
즉 **의미는 같은데 조건을 더 적었다는 이유만으로** 가이드가 떨어져 나간다. 0.3이라는 값은 짧은 개념형 질의 위주였던 옛 큐리셋(47문항)의 거리 분포로 잡힌 것이고, 사용자가 요청해 2026-08-05에 추가한 "신뢰속성·옵션·SQL·참고문서를 최대한 많이 섞은" 문항들이 정확히 그 경계 바로 바깥에 놓인다. 결과 품질 자체는 나쁘지 않다(결과집합 정확도 0.950) — 명시 조건이 많아 가이드 없이도 잘 걸러지기 때문이다. 손해는 **"AI가 문서를 읽고 골랐다"는 근거 표시가 사라지는 것**과, 가이드가 있어야만 되는 매핑(해치백→소형/준중형 등)이 조건에 명시돼 있지 않으면 못 푸는 것이다.
⚠️ 컷오프를 그냥 올리면 안 된다 — 느슨하게 하면 무관한 가이드가 주입돼 엉뚱한 조건이 생긴다(그 위험 때문에 0.3이 실측으로 정해졌다). 후보: (a) 질의 길이·조건 수에 따라 컷오프를 조정 (b) 구조조건을 떼어낸 "의미 부분"만 임베딩해 가이드를 찾기 (c) 컷오프를 재측정해 새 문항 분포까지 포함하는 값으로 다시 잡기 — 어느 쪽이든 **무관한 가이드가 붙는 비율을 함께 재야** 판단할 수 있다.
⚠️ **정정(2026-08-05, 등재 당일)**: 처음에 "결과 정확도엔 영향이 없다(0.950)"고 적었는데 **총평이 개별 문항을 가렸다.** 문항별로 다시 재니:
  · 가이드가 붙은 문항 평균 결과점수 **0.960** vs 안 붙은 문항 **0.778**
  · 특히 **용어 매핑형**이 무너진다 — `H6 2500만원 이하 해치백 있어?` **0.2**, `H18 3천만원 이하 무사고 해치백` **0.2**, `H27 …안전 옵션 갖추고…` **0.2**. 셋 다 라우터가 SQL로 보냈고, 가이드가 없으니 `해치백`→소형차·준중형차 같은 **매핑을 풀 근거가 사라진다**.
  즉 이건 표시(인용 문구)만의 문제가 아니라 **그 문항들에서는 실제 결과가 틀린다.**
⚠️ **다만 이번에 생긴 회귀는 아니다**(실측): 옛 기준선(매물 93건·47문항)에서도 `H6`는 이미 `doc_hit=False`에 결과 **0.0**이었다. 2026-08-05에 추가한 조건 밀집 문항들이 **같은 병의 사례 수를 늘려 눈에 띄게 만든 것**이지, 없던 병을 만든 것이 아니다. 새 기준선이 그 상태를 수치로 고정한다(가이드 인용 18/28, 위 세 문항 0.2) — 이제부터의 악화는 게이트가 잡는다.
trigger: **Epic 15에서 웹이 AI 응답의 `(참고: 문서명)`·되묻기 칩을 실제로 화면에 그리는 자리**(DW-587·597·600과 같은 스토리). 근거: ① 그때 인용률이 **사용자 눈에 보이는 값**이 되어 품질 목표로 삼을지 말지를 그 자리에서 정하게 된다 ② 지금은 서버만 보내고 웹이 안 그려서 64%든 92%든 화면상 차이가 없다. ⚠️ **고치는 코드는 백엔드**(`doc_rag_node` 컷오프·검색 방식)라 Epic 15 스토리의 인수조건으로 "이 항목을 판단한다"만 심고, 실제 수정이 필요하다고 결론나면 그때 AI 스토리를 하나 연다 — 판단 자리와 수정 자리를 구분해 적는다.
status: open

- source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
  summary: `scripts/check_migrations.py`(마이그레이션 게이트)는 이 마이그레이션의 실제 CHECK 내용(즉 buyer/seller가 정말 완화됐는지)을 전혀 검증하지 못한다 — self-containment(파일명·번호·적용 성공 여부·listings/guide_documents 축 3개)만 본다.
  evidence: 리뷰 중 `0027_role_check_relax.sql`의 새 CHECK를 원래의 3값 enum(`role in ('buyer','seller','admin')`)으로 되돌려(=이 스토리의 목적을 완전히 무효화) 같은 게이트를 재실행했더니 **동일하게 exit 0으로 통과**했다(파일은 즉시 원복). 즉 이 스토리의 스펙이 유일한 자동 검증으로 제시한 커맨드가, 이 스토리가 실제로 잘못돼도 못 잡는다. 게이트 자체의 설계 범위(self-containment)가 원래 이렇고 이 스토리가 새로 만든 결함은 아니지만, "CHECK 내용까지 매 마이그마다 자동 검증할지"는 게이트 설계자의 판단이 필요하다.
  trigger: 다음에 `profiles.role`(또는 유사한 도메인 규칙을 강제하는 CHECK) 관련 마이그레이션을 또 작성할 때, 혹은 `scripts/check_migrations.py`를 다른 이유로 손대는 스토리에서 — 그때 "마이그별 내용 검증을 프로브에 추가할지"를 판단한다.

- source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
  summary: `docs/conventions.md §9.1`이 명시적으로 승인한 forward-only 예외 4가지(정책 재생성·트리거 재생성·함수 EXECUTE 회수·GRANT 축소)에 "CHECK 제약을 drop 후 같은 이름으로 재생성"이 들어있지 않다 — 이 스토리(`0027_role_check_relax.sql`)가 그 패턴을 처음 썼는데 문서화되지 않았다.
  evidence: 코드리뷰(adversarial 렌즈)가 지적. §9.1은 "근거 없는 선례 복사"를 막기 위해 각 예외의 안전 조건을 명시해왔는데(예: GRANT 축소는 "축소 방향만" 허용), CHECK 제약은 정책/트리거와 달리 **데이터 무결성을 가른다** — 이번처럼 기존 값의 상위집합으로만 넓히는 경우는 안전하지만, 좁히는 replace는 기존 행을 위반 상태로 만들 수 있다(이 스펙의 Design Notes에 그 위험을 직접 서술해뒀다). 그 안전 조건("넓히는 방향만")을 정확히 문서에 새기지 않으면 다음 사람이 "CHECK도 drop-recreate 하면 된다"고 좁히는 방향으로 오용할 위험이 있다.
  trigger: 다음에 기존 CHECK 제약을 drop 후 재생성하는 마이그레이션을 작성할 때 — 그때 §9.1에 이 예외를 "넓히는 방향만" 조건으로 명시해 추가한다(GRANT 축소 예외의 반대 방향 버전으로 서술).

### DW-661: 마이그레이션 게이트(CI)가 `test/bmad-loop` 브랜치에서 한 번도 돌지 않아, "에픽 첫 마이그 스토리는 게이트 통과가 DoD"가 Epic 14에서 충족되지 않았다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 후속 리뷰(adversarial 렌즈)가 지적, 리뷰 세션이 워크플로 파일과 브랜치 이력으로 확인.
location: `.github/workflows/migration-gate.yml`(트리거 절) · 현재 작업 브랜치 `test/bmad-loop`
severity: medium
summary: `docs/conventions.md` §9.4와 `project-context.md` 규칙 10이 "각 에픽 첫 마이그레이션 스토리는 마이그레이션 게이트(CI) 통과가 DoD"라고 못박았는데, 그 게이트는 `develop`/`main` push 또는 PR에서만 돈다. Epic 14의 첫 마이그(`0027`)는 `test/bmad-loop`에 있고 PR도 없어 게이트가 실행된 적이 없다.
evidence: 워크플로의 트리거가 `develop`/`main`·PR로 한정돼 있고 현재 브랜치는 둘 다 아니다. 이 스토리가 통과를 선언한 것은 로컬 `python3 scripts/check_migrations.py`인데, 스펙 자신이 이걸 "로컬 검증 커맨드"라고 부른다 — 즉 DoD가 지정한 CI 실행과 같은 사실이 아니다. ⚠️ **이 스토리 혼자 해결할 수 없다**: bmad-dev-auto 워크플로는 커밋만 하고 push를 하지 않으며(step-04 "Do not push"), `develop` 병합·push는 CLAUDE.md B3에 따라 사람의 판단 영역이다. 게이트 자체는 정상이고 로컬 재현(동적 Docker 검사 포함)은 exit 0으로 통과했으므로 코드 결함 신고가 아니라 **절차 공백 신고**다.
trigger: **`test/bmad-loop`의 작업을 `develop`으로 처음 병합·push하는 자리에서** — 그때 게이트가 실제로 초록인지 확인하고, 초록이면 이 항목을 닫는다. 무인 루프를 계속 돌릴 계획이면 그 전에 판단할 것: (a) 게이트 트리거에 이 브랜치를 추가할지 (b) 루프가 도는 브랜치를 `develop`으로 바꿀지 (c) 에픽 종료 시 사람이 일괄 확인하는 것으로 DoD 문구를 조정할지. 지금처럼 두면 **에픽마다 같은 공백이 반복된다**.
status: open

### DW-662: 이 장부의 마지막 2개 항목(Story 14.1 1차 리뷰가 등재)이 `### DW-<번호>` 형식을 따르지 않아 번호로 조회되지 않는다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 후속 리뷰(adversarial 렌즈)가 지적. 같은 스토리의 **1차 리뷰 패스**가 만든 것이다.
location: `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-660 바로 뒤 — `- source_spec:` 불릿으로 시작하는 2개 항목(게이트 사각지대 / `conventions.md §9.1` 문서화 공백)
severity: low
summary: 그 2건은 `### DW-<번호>` 제목도, 번호도, `severity:`·`status:`도 없이 불릿으로만 붙어 있다. 장부의 다른 660개 항목과 형식이 다르다.
evidence: bmad-dev-auto의 step-04가 지정하는 defer 형식(`- source_spec:`/`summary:`/`evidence:`)과 이 프로젝트 장부의 정본 형식(`### DW-N` + `origin/location/severity/reason/trigger/status`)이 서로 다른데, 1차 패스가 전자만 따랐다. 결과적으로 그 2건은 **DW 번호로 지목할 수 없고**, 제목(`### DW-`)을 기준으로 항목을 나누는 조회·sweep은 이 둘을 DW-660 본문의 일부로 읽는다. 장부에 올렸다는 기록만 남고 실제로는 검색되지 않는 상태 — CLAUDE.md B8이 막으려는 "미룬 일이 조용히 사라지는" 실패 모드 그 자체다. 내용 자체는 둘 다 유효하다(사실관계 재확인함). ⚠️ **이번 리뷰가 직접 고치지 않은 이유**: 이 실행의 지시가 "기존 장부 항목을 수정·재개·재작성하지 말고 신규 항목만 추가하라(기존 항목의 상태와 처리는 오케스트레이터 소유)"였다. 그래서 신고만 한다.
trigger: **오케스트레이터가 이 장부를 다음에 sweep(정리)할 때** — 그때 두 항목에 DW-661 이전 번호(예: DW-660-a/b) 또는 새 번호를 배정하고 6필드로 승격한다. 함께 판단할 것: bmad-dev-auto의 defer 형식과 이 프로젝트 장부 형식이 다르다는 **구조적 원인**을 스킬 커스터마이즈(`_bmad/custom/bmad-dev-auto.toml`)로 맞출지 — 안 맞추면 dev-auto가 defer할 때마다 같은 불일치가 재발한다.
status: open

### DW-663: 통합테스트 공용 픽스처가 **가입 트리거의 기본 role을 단언**해, Story 14.2가 트리거를 바꾸는 순간 실DB 테스트가 무더기로 깨진다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 3차 리뷰(adversarial·edge-case 두 렌즈가 독립적으로 지적), 리뷰 세션이 `conftest.py`와 사용처를 직접 읽어 확인.
location: `api/tests/integration/conftest.py`의 `_create_user()` — `assert row[0] == role` 줄. 이 헬퍼를 쓰는 파일: `test_role_check_relax_real_db.py`(15건) + `test_chat_realtime_broadcast_real_db.py` 등 형제 파일들(`grep -ln '_create_user' api/tests/integration/*.py`로 확인).
severity: medium
summary: `_create_user()`는 유저를 만든 뒤 "가입 트리거가 `user_metadata`의 role을 그대로 `profiles.role`에 반영했는가"까지 단언한다. Story 14.2는 바로 그 트리거(`handle_new_user`)의 기본 role 로직을 바꾸는 스토리다 — 바뀌는 순간 이 단언이 **픽스처 setup 단계에서** AssertionError를 내고, 그 헬퍼를 쓰는 모든 실DB 테스트가 자기가 검증하려던 것과 무관한 이유로 죽는다.
evidence: `conftest.py`의 해당 단언은 Story 12.1이 겪은 실제 결함(판매자 유저에 role="buyer"를 하드코딩)을 막으려고 **의도적으로** 넣은 것이라 그냥 지우면 그 방어가 사라진다. 즉 14.2는 "트리거를 바꾼다 + 이 단언을 트리거의 새 계약에 맞게 고친다"를 **한 커밋 안에서** 해야 한다. 지금 이 사실이 적힌 곳은 conftest 주석뿐이고, 14.2 스토리 문서에는 없다. Story 14.1이 새로 추가한 테스트 15건도 같은 헬퍼를 쓰므로 폭발 반경이 이번 스토리로 더 커졌다(그래서 여기 등재한다).
trigger: **Story 14.2 착수 시(트리거 기본값을 바꾸는 그 작업 안에서)** — 14.2의 인수조건에 "`conftest._create_user`의 role 단언을 새 트리거 계약에 맞게 갱신하고, `pytest tests/integration` 전체가 초록임을 확인한다"를 심는다. 14.2가 시작될 때 이 항목을 열어 확인할 것.
status: done 2026-08-06
resolution: Story 14.2(0028_handle_new_user_default_role.sql)가 `conftest.py`·`test_chat_idempotency_real_db.py`의 `_create_user()`를 새 트리거 계약(role=None→'user', buyer/seller 그대로, 그 외 전부→'user')에 맞게 갱신했다. `role=None`(메타데이터 자체를 안 보내는 경로) 인자를 새로 지원해 web 신규 가입 경로를 재현한다. `pytest tests/integration` 99건 전체 통과 확인(로컬 pgvector, 0001~0028 전체 적용 후) — 갱신 전 트리거로 되돌려 새로 추가한 4건이 실제로 red가 됨을 먼저 확인한 뒤(B4), 되돌리고 다시 green을 확인했다.

### DW-664: `tests.yml`(api-db·web 잡)도 `test/bmad-loop`에서 안 돈다 — Story 14.1이 새로 만든 검사 15건이 CI에서 한 번도 실행되지 않았다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 3차 리뷰(verification-gap 렌즈)가 지적, 리뷰 세션이 워크플로 트리거 절과 브랜치 위치를 직접 확인.
location: `.github/workflows/tests.yml`의 `on.push.branches: [develop, main]` — 현재 작업 브랜치 `test/bmad-loop`(develop 대비 28커밋 앞, PR 없음)
severity: medium
summary: DW-661은 `migration-gate.yml`(레포만으로 DB가 서는가)만 지목했다. 그런데 Story 14.1이 "검사를 실행되는 자리에 박았다"며 만든 `api/tests/integration/test_role_check_relax_real_db.py`(15건)와 `web/src/lib/__tests__/roleLabelFallback.test.ts`가 실제로 의존하는 것은 **`tests.yml`의 `api-db`·`web` 잡**이고, 그 워크플로도 같은 브랜치 제한을 받는다. 즉 그 검사들이 초록인 근거는 아직 로컬 1회 실행뿐이다.
evidence: `tests.yml`의 트리거는 `push: branches: [develop, main]` + `pull_request`(브랜치 필터 없음). 현재 브랜치는 둘 다 아니고 `gh pr list --head test/bmad-loop`도 0건이다. **DW-661과 원인은 같지만 대상이 다르므로 따로 적는다** — DW-661을 닫을 때 `migration-gate.yml`만 보고 닫으면 이쪽은 그대로 남는다. ⚠️ 이 워크플로(bmad-dev-auto)는 push를 하지 않으므로 여기서 해결할 수 없다. 해결책은 DW-661과 동일한 자리에서 함께 판단하는 것이 자연스럽다: PR 하나를 열면 두 워크플로의 `pull_request` 트리거가 **동시에** 켜진다(둘 다 브랜치 필터가 없다).
trigger: **DW-661을 처리하는 그 자리에서 함께** — `test/bmad-loop`을 `develop`으로 병합·push하거나 draft PR을 여는 시점. 그때 `api-db`·`web` 잡이 실제로 초록인지 확인하고 닫는다.
status: open

### DW-665: 마이그레이션이 CI·원격 적용 경로에서 **원자적이지 않다** — 실패하면 앞부분만 적용된 채 남는다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 3차 리뷰(adversarial·edge-case 렌즈)가 지적, 리뷰 세션이 워크플로의 psql 호출과 `scripts/check_migrations.py`를 대조해 확인.
location: `.github/workflows/tests.yml`의 "마이그레이션 적용" 스텝(`psql -v ON_ERROR_STOP=1 -q -f "$f"`) vs `scripts/check_migrations.py:172`(`--single-transaction` **있음**) · 원격 `apply_migration`(트랜잭션 의미 미문서화, `docs/deployment-runbook.md:126`)
severity: low
summary: 마이그 게이트는 파일을 `--single-transaction`으로 적용하지만 `tests.yml`의 api-db 잡과 원격 적용 경로는 그렇지 않다. 그래서 파일 중간에서 실패하면 **앞선 문장은 이미 커밋된 채** 마이그가 실패로 보고된다. 0027이 구체적 사례다: 이름 드리프트로 사후조건이 발화하거나, `role=''` 행이 있어 `add constraint`가 실패하면, 앞의 `drop constraint`는 이미 적용돼 profiles에 role CHECK가 아예 없는 상태로 남는다.
evidence: 세 적용 경로의 트랜잭션 의미가 서로 다르다는 것은 `docs/deployment-runbook.md:126`이 이미 다른 각도(트랜잭션 밖에서만 되는 문)로 기록해 둔 사실이다. 현재 27개 마이그 중 명시적 `begin;`/`commit;`을 쓰는 파일은 **0개**라, 0027 하나만 감싸면 레포에 없던 관례가 생긴다(게이트의 `--single-transaction`과 중첩되면 동작도 달라진다). 게다가 0027을 그대로 감싸면 이번 리뷰가 추가한 재실행 검사(`test_migration_aborts_when_drop_is_a_no_op` 등 — 파일 본문을 테스트 트랜잭션 안에서 다시 실행한다)가 내부 `commit;` 때문에 격리를 잃는다. 즉 **파일 하나의 문제가 아니라 "마이그레이션을 어떻게 적용하는가"라는 레포 전체 관례의 공백**이라 여기 등재한다. 실패 시에도 메시지가 무엇이 잘못됐는지 정확히 알려주므로 전진 수복은 가능하다(그래서 low).
trigger: **다음 마이그레이션 스토리(Epic 15의 Story 15-4가 마이그레이션 1개를 포함한다)를 착수할 때** — 그때 셋 중 하나로 정한다: (a) `tests.yml`의 적용 스텝에도 `--single-transaction`을 붙여 게이트와 맞춘다(가장 좁은 변경, 파일은 안 건드림) (b) 마이그 파일마다 명시적 트랜잭션을 쓰기로 `docs/conventions.md` §9에 관례를 세운다 (c) 실패 시 부분 적용이 허용되는 것으로 명시하고 런북에 수복 절차를 적는다. 정한 결과를 §9에 적어야 다음 사람이 동전을 던지지 않는다.
status: open

### DW-666: `sprint-status.yaml`이 `epic-14: backlog`인데 그 첫 스토리 `14-1`은 `done` — 파일이 스스로 정의한 상태 전이가 빠졌다

source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
origin: 2026-08-06 Story 14.1 3차 리뷰(adversarial·edge-case 두 렌즈가 독립적으로 지적), 리뷰 세션이 해당 파일의 범례와 값을 직접 읽어 확인.
location: `_bmad-output/implementation-artifacts/sprint-status.yaml` — `epic-14:` 줄과 `14-1-role-check-완화-마이그레이션:` 줄 · 파일 상단 `# last_updated:` 블록
severity: low
summary: 같은 파일 상단 범례가 "backlog → in-progress: 첫 스토리를 만들 때 자동 전이"라고 못박고 있는데, Epic 14는 첫 스토리가 `done`인 지금도 `backlog`로 남아 있다. 또 이 변경에서 `# last_updated:` 블록이 갱신되지 않아, 파일의 유일한 사람용 이력에 Story 14.1이 남지 않았다.
evidence: 파일을 열어 확인함 — `epic-14: backlog` 바로 아래 줄이 `14-1-...: done`이다. 상태로 분기하는 사람·도구가 "Epic 14 미착수"로 읽는데 실제로는 스키마 변경이 이미 커밋돼 있다. ⚠️ **이번 리뷰가 직접 고치지 않은 이유**: `sprint-status.yaml`은 bmad-loop 오케스트레이터가 소유하는 상태 파일이고, 이 실행의 지시가 오케스트레이터 소유 항목의 상태를 건드리지 말라는 것이었다. 그래서 신고만 한다(내용 자체는 사실 확인 완료).
trigger: **오케스트레이터가 Story 14.2를 착수하는 자리에서** — 그때 `epic-14`를 `in-progress`로 올리고 `last_updated`에 14.1·14.2 항목을 남긴다. 함께 볼 것: 전이가 "자동"이라고 적혀 있는데 실제로 자동으로 일어나지 않았다면, 그 자동화가 어디서 끊겼는지(스토리 생성 경로를 안 거치는 무인 루프인지)를 확인해야 같은 누락이 에픽마다 반복되지 않는다.
status: open

### DW-667: Follow-up review still recommended for 14-1-role-check-완화-마이그레이션 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-14-1-role-check-완화-마이그레이션.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260806-023902-0381; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-668: Flutter 앱이 아직 "판매 = 역할" 모델이다 — 같은 계정이 web에선 팔 수 있고 앱에선 차단된다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 후속 리뷰 — adversarial·verification-gap 두 렌즈가 독립적으로 지적, 리뷰 세션이 Dart 파일 4곳을 직접 grep해 확인.
location: `app/lib/features/listings/sell_screen.dart:152` · `my_listings_screen.dart:26` · `edit_listing_screen.dart:28`(모두 `if (role != UserRole.seller)` 하드 게이트) · `app/lib/features/chat/chat_list_screen.dart:39`(빈 채팅목록 문구가 `role == UserRole.seller`로 2분기 — web에서는 이번 스토리가 역할 중립 문구로 통일한 바로 그 코드)
severity: high
summary: Story 14.3이 web의 판매 게이트를 소유권 기반으로 풀었지만 Flutter 앱은 그대로 역할 게이트다. 그래서 `role='buyer'` 계정이 **web에서는 매물을 등록·수정할 수 있는데 앱에서는 차단 화면을 본다** — 같은 계정이 플랫폼에 따라 다른 권한을 갖는, 사용자가 직접 관측 가능한 불일치다. Story 14.2가 가입 트리거 기본값을 바꾸면 더 나빠진다: `app/lib/features/auth/user_role.dart`의 기존 주석이 이미 경고하듯 metadata에 role이 안 실리면 `fromValue(null) → null`이 되어 **신규 가입자는 앱의 판매자 화면 전체에 영영 못 들어간다**.
evidence: 위 4개 파일의 조건문을 직접 확인함. `app/test/`에는 이 게이트를 단언하는 검사가 없다(`widget_test.dart`는 enum 값·파싱만 본다). Story 14.3의 스펙은 Never 절에서 "Flutter 변경은 에픽 범위 밖"이라고 명시하고 "DW 등재는 아직 안 됐다"고 스스로 인정했다 — 이 항목이 그 등재다. **코드를 지금 안 고치는 이유**는 에픽 14의 범위가 web 한정으로 사용자 확정돼 있기 때문이지, 문제가 아니어서가 아니다. 2026-08-06 Story 14.2 리뷰에서 실측 확인됨 — DW-678 참고(같은 리뷰가 severity를 medium→high로 갱신).
trigger: **Epic 16(앱 정합성 에픽)의 첫 스토리를 만들 때 인수조건으로 심는다.** 그보다 먼저 Story 14.2가 가입 트리거 기본값을 바꾸는 시점이 오면, 그 스토리의 리뷰에서 "앱 신규 가입자가 role=null로 전 판매화면 차단"이 실제로 발생하는지 먼저 확인한다(그 경우 severity가 high로 올라간다). (2026-08-06 확인 완료, DW-678로 상세 등재)
resolution: **2026-08-07 확인 — 2026-08-06 `16-0-앱-역할통합-미러링-기존계정-정리`가 해소했다.** 그날 손으로 한 작업이라 이 줄을 닫아준 사람이 없어 열린 채였다(엔진이 돌린 스토리는 스스로 닫는다). 코드로 대조함: 앱 판매 화면 3곳이 전부 공용 게이트를 쓴다 — `sell_screen.dart:152`·`my_listings_screen.dart:25`·`edit_listing_screen.dart:26` 모두 `requireUser(ref, …)`이고 `role != UserRole.seller` 가드는 없다. 2026-08-07 **실기기(갤럭시 S21)** 로도 확인했다: metadata에 role이 없는 시드 계정(`seller@test.com`)으로 로그인해 홈에서 '매물 등록'·'내 매물 관리'가 보이고 등록 폼까지 도달했다.
status: resolved
### DW-669: 정지(`status='suspended'`)된 회원의 판매를 아무것도 막지 않는다 — 게이트에도 RLS에도 status 검사가 없다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 후속 리뷰(edge-case 렌즈) 지적, 리뷰 세션이 마이그레이션과 web 게이트를 직접 grep해 확인.
location: `supabase/migrations/0001_profiles.sql:15`(`status text not null default 'active' check (status in ('active','suspended'))`) · `supabase/migrations/0002_listings.sql`의 INSERT/UPDATE/DELETE 정책(모두 `seller_id = auth.uid()`만 검사) · `web/src/app/(user)/sell/layout.tsx`(`requireUser()` — status를 안 읽는다)
severity: medium
summary: 관리자가 회원을 정지시켜도(`0005_admin_policies.sql`이 제공하는 기능) 그 회원은 계속 로그인해 매물을 등록·수정·삭제할 수 있다. 정지 상태를 읽어 행동을 막는 지점이 web 게이트·RLS 어디에도 없다.
evidence: `grep -rln "suspended"` 결과 매치는 `0001_profiles.sql`(컬럼 정의)·`0005_admin_policies.sql`(관리자가 값을 바꾸는 정책)·`0027_role_check_relax.sql`·`MemberActions.tsx`(관리자 UI)·`constants.ts`(상수)뿐 — **정지 여부로 무언가를 거부하는 코드는 0건**이다. ⚠️ **이것은 Story 14.3이 만든 문제가 아니다**: 이전 게이트 `requireRole(SELLER)`도 role만 봤으므로 정지된 seller는 예전에도 그대로 팔 수 있었다. 다만 게이트가 풀리면서 이제 정지된 **모든** 계정으로 범위가 넓어졌다. 이 프로젝트의 원칙(CLAUDE.md B9 "중요한 값은 데이터 계층이 직접 구한다")대로면 해결 자리는 앱 게이트가 아니라 `listings` RLS에 `exists(select 1 from profiles where id=auth.uid() and status='active')`를 더하는 쪽이다.
trigger: **관리자 회원관리를 손대는 Epic 15 Story 15-3을 착수할 때** — 그 스토리가 "정지"의 의미를 화면에서 다루므로, 정지가 실제로 무엇을 막는지도 그 자리에서 정한다. 정하면 `docs/conventions.md` §8(접근 게이트 계약)에 한 줄로 적어야 다음 사람이 다시 묻지 않는다.
status: open

### DW-670: `profiles` 행이 없는 로그인 사용자가 매물을 등록하면 FK 오류(23503)가 정체불명 문구로 뜬다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 후속 리뷰(edge-case 렌즈) 지적, 리뷰 세션이 `SellForm.tsx`의 에러 매핑과 `0002_listings.sql`의 FK를 직접 확인.
location: `web/src/app/(user)/sell/SellForm.tsx:117-124`(`toKoreanError`가 `23514`·`42501`만 한국어로 매핑) · `supabase/migrations/0002_listings.sql:28`(`seller_id ... references public.profiles(id)`)
severity: low
summary: `auth.users`에는 있으나 `profiles` 행이 없는 세션으로 매물을 등록하면 INSERT가 외래키 위반(23503)으로 실패하는데, 그 코드가 한국어 매핑 목록에 없어 15개 필드를 다 채운 사용자가 무슨 일인지 알 수 없는 일반 오류만 본다.
evidence: `toKoreanError`의 분기를 직접 읽음 — `23514`(CHECK 위반)와 `42501`(RLS 거부)만 처리한다. 그런 사용자가 실제로 생길 수 있는 경로도 실재한다: `web/src/app/(admin)/admin/members/MemberActions.tsx`가 "profiles 행은 DELETE 되지만 `auth.users`는 service_role 키가 없어 못 지운다"고 스스로 명시하고 있어, 관리자가 회원을 지운 뒤에도 그 사람의 세션은 살아 있다. ⚠️ Story 14.3 이전에는 `/sell`의 `requireRole(SELLER)`이 profiles를 읽어 비교했기 때문에 **우연히** 존재 검사 역할을 했고 그런 세션은 홈으로 튕겼다. 게이트가 `requireUser()`로 바뀌며 그 우연한 방어가 사라져 이 경로가 열렸다(발생 조건이 좁아 low).
trigger: **`SellForm.tsx`의 에러 처리나 매물 등록 실패 문구를 다음에 손대는 스토리에서** — 그때 `23503`을 한국어 문구("프로필 정보가 없어 등록할 수 없습니다. 다시 로그인해주세요.")로 매핑한다. 함께 판단할 것: 관리자 회원 삭제가 세션을 무효화하지 못하는 구조(service_role 키 부재) 자체는 별개의 오래된 제약이므로 여기서 풀려 하지 않는다.
status: open

### DW-671: 라우트 게이트를 바꿔도 E2E **전량**을 돌리라는 강제가 없다 — Story 14.3에서 실제로 모순된 테스트를 놓쳤다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 후속 리뷰 — adversarial·verification-gap 두 렌즈가 독립적으로 같은 사고를 지적, 리뷰 세션이 `nav-and-hero.spec.ts`를 열어 확인 후 그 자리에서 테스트를 고쳤다.
location: `web/e2e/*.spec.ts`(9개 파일) · 각 스펙 문서의 `## Verification` 절에 손으로 적는 Playwright 명령
severity: low
summary: Story 14.3은 `/sell` 게이트를 뒤집어 놓고 검증을 `core-flows.spec.ts write-flows.spec.ts` 두 파일로만 돌렸다. 그런데 옛 동작(`buyer가 /sell 접근하면 홈으로`)을 단언하는 테스트는 손대지 않은 `nav-and-hero.spec.ts`(B8)에 있었다. 결과적으로 **`npm run test:e2e` 전량은 red인데 스토리는 초록으로 닫혔다**. 이번 후속 리뷰가 B8을 새 동작으로 뒤집어 개별 사고는 해소했지만, "부분 실행을 검증으로 인정하는" 구조 자체는 그대로다.
evidence: `grep -rn "'/sell'" web/e2e/*.spec.ts` → `core-flows`·`write-flows` 외에 `nav-and-hero.spec.ts:160`이 나온다. 스펙의 Verification Evidence는 두 파일만 실행했다고 명시한다. ⚠️ 이 사고가 **조용히** 지나간 이유는 DW-664가 기록한 별개 사실(E2E 잡이 CI에 아예 없다)과 겹친다 — 사람이 로컬에서 고른 파일만 돌리는 것이 유일한 실행 경로다.
trigger: **다음에 라우트 게이트·접근 제어를 바꾸는 스토리(Epic 15 Story 15-3이 관리자 회원관리를 건드린다)를 계획할 때** — 그 스펙의 Verification에 파일 목록 대신 `npm run test:e2e`(전량)를 적는다. 더 근본적으로는 DW-661·DW-664를 처리해 PR을 여는 자리에서, E2E 잡을 CI에 배선할지(헤드리스 브라우저·로컬 Supabase 컨테이너 필요, `docs/tech-debt.md` #168이 비용을 이미 산정해 뒀다) 함께 판단한다.
status: open

### DW-672: `/sell/[id]/edit`에서 타인 매물 폼을 막는 실주체는 앱측 `seller_id` 필터인데, 그 필터를 지키는 자동 검사가 없다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 3차 리뷰 — adversarial·verification-gap 두 렌즈가 독립 지적, 리뷰 세션이 마이그레이션과 e2e 스위트를 직접 열어 확인.
location: `web/src/app/(user)/sell/[id]/edit/page.tsx:44`(`.eq('seller_id', user?.id ?? '')`) · `supabase/migrations/0002_listings.sql:94-95`(`listings_select_on_sale`)
severity: medium
summary: SELECT RLS는 "on_sale ∪ 본인 ∪ 관리자"의 OR 결합이라 **타인의 판매중 매물도 읽힌다**. 폼이 안 뜨게 막는 것은 RLS가 아니라 이 페이지의 앱측 `seller_id` 필터 한 줄인데, 그 줄이 사라져도 실패하는 테스트가 하나도 없다. 이 스토리로 `/sell/[id]/edit`에 도달할 수 있는 사람이 `role='seller'`에서 로그인 사용자 전원으로 넓어져 노출면이 커졌다.
evidence: `grep -rn "본인 매물만|접근 권한이 없습니다" web/e2e web/src --include=*.spec.ts` → 0건. `write-flows.spec.ts:161`은 **본인** 매물 edit URL만 연다. 스펙 I/O 매트릭스 4행의 유일한 검증 기록은 2차 리뷰 세션의 브라우저 수동 재현 1회다(`## Verification Evidence`). ⚠️ 필터 자체는 지금 정상 동작한다 — 없는 것은 동작이 아니라 **그 동작을 지키는 검사**다. 3차 리뷰에서 이 페이지 헤더 주석이 "본인 매물 여부는 RLS가 집행한다"고 잘못 서술한 것은 고쳤지만(그대로 믿으면 필터를 중복이라 여겨 지울 수 있었다), 주석은 계약이 아니다(CLAUDE.md B9).
trigger: **`web/e2e/write-flows.spec.ts`나 `/sell` 수정 흐름을 다음에 손대는 스토리에서** — 그 자리에 교차 소유자 케이스를 추가한다(BUYER 로그인 → SELLER 소유 on_sale 매물의 `/sell/[id]/edit` 직접 접속 → 안내 문구 노출 + 폼 미렌더 단언). 읽기 전용이라 `core-flows.spec.ts`에 둬도 된다.
status: open

### DW-673: role='buyer' 계정이 실제로 매물을 **등록**할 수 있는지는 어떤 테스트도 확인하지 않는다 — FR52의 절반이 무검사다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 3차 리뷰 — adversarial·edge-case 두 렌즈가 독립 지적, 리뷰 세션이 e2e 스위트 전량을 grep해 확인.
location: `web/e2e/core-flows.spec.ts:212`(C8, 읽기 전용이라 등록 불가) · `web/e2e/write-flows.spec.ts:108,156,216`(등록·수정·구매완료 전부 `seller@test.com`)
severity: medium
summary: C8과 B8은 role='buyer' 계정이 `/sell` **화면에 도달**하는 것까지만 단언한다. 실제로 등록 버튼을 눌러 매물이 생기는지는 아무도 안 본다 — 쓰기 흐름은 전부 `role='seller'` 계정으로만 돈다. 스토리의 인수조건이 "화면이 렌더된다"까지라 이 스토리는 정당하게 닫혔지만, 에픽 목표(FR52 "로그인만 하면 누구나 사고팔 수 있다")의 실질은 검사 밖이다.
evidence: `core-flows.spec.ts` 파일 헤더가 "읽기 전용 — DB에 INSERT/UPDATE/DELETE 하지 않는다. 폼 제출도 하지 않는다"를 절대 규칙으로 못박고 있어 C8이 구조적으로 등록을 검사할 수 없다. `write-flows.spec.ts`의 BUYER 계정 사용은 채팅(180행) 한 곳뿐이다. ⚠️ 지금 동작은 한다 — `listings_insert_own`이 role을 안 보므로 buyer 계정 INSERT는 통과한다(3차 리뷰가 정책 본문을 직접 확인). 없는 것은 **회귀 시 잡아줄 장치**다: Story 14.2가 가입 트리거를 바꾸거나 누군가 INSERT 경로에 role 검사를 되살려도 스위트는 초록을 유지한다.
trigger: **Story 14.2(가입 트리거 기본값 변경)를 구현할 때 그 스토리의 인수조건으로 심는다** — 14.2가 "신규 가입자가 곧바로 팔 수 있다"를 약속하므로 등록 성공까지 단언하는 것이 그 스토리의 자연스러운 DoD다. 자리는 `write-flows.spec.ts`(등록 → 확인 → afterAll에서 삭제하는 기존 관례가 92행에 이미 있다).
status: open

### DW-674: `listings` 소유권 RLS 자체를 지키는 반복 실행 검사가 저장소에 없다 — 이 스토리가 그것을 유일한 방어선으로 승격시켰는데도

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 3차 리뷰(verification-gap 렌즈) 지적, 리뷰 세션이 `api/tests/integration` 전량과 저장소 SQL 테스트를 직접 조사.
location: `supabase/migrations/0002_listings.sql:104-118`(`listings_insert_own`·`listings_delete_own`) · `supabase/migrations/0015_listings_update_not_sold.sql:24-29`(`listings_update_own` 현행판)
severity: medium
summary: Story 14.3이 앱 계층 역할 게이트를 없애면서 "누가 남의 매물을 바꿀 수 있나"의 방어선은 이제 `listings` RLS 하나뿐이다. 그런데 그 정책이 느슨해져도 실패하는 자동 검사가 저장소 어디에도 없다 — 확인 기록은 전부 사람이 psql로 한 번씩 해본 것이다.
evidence: `find . -name '*.sql' -path '*test*'` → 0건(pgTAP 없음). `api/tests/integration`의 10개 파일 중 listings 소유권 거부를 단언하는 파일 없음. 기록된 검증은 Story 2-1·2-3(2026-06)의 수동 임퍼소네이션과 Story 14.3 2차 리뷰 세션의 psql 1회(스펙 `## Verification Evidence`)뿐이다. ⚠️ 실행 자리는 이미 있다 — CI의 `api-db` 잡이 전 마이그레이션을 실제 Postgres에 적용하고, `test_chat_unread_real_db.py:91-106`·`test_role_check_relax_real_db.py:145-155`가 `set local role authenticated` + `set local request.jwt.claim.sub`로 세션을 흉내 내는 관례를 이미 쓴다. 새 인프라가 아니라 그 관례를 한 번 더 쓰는 일이다. 선례도 있다: `0015`가 `listings_update_own`을 drop 후 재생성했다 — 정책은 실제로 교체된다.
trigger: **`listings` RLS 정책을 다음에 건드리는 마이그레이션 스토리에서**(DW-669의 정지 회원 검사를 RLS에 넣는 작업이 유력한 첫 후보다) — 그 마이그레이션과 같은 스토리에서 `api/tests/integration`에 비소유자 UPDATE/DELETE가 0행, 타인 명의 INSERT가 42501임을 단언하는 pytest를 추가한다. 그래야 CI(`api-db` 잡)가 실제로 돌린다.
status: open

### DW-675: admin 계정이 `/sell`에 들어오는 것은 "의도된 결과"로 선언됐지만, 그 선언을 지키는 검사가 없다

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 3차 리뷰 — edge-case·verification-gap 두 렌즈가 독립 지적, 리뷰 세션이 `web/e2e/*.spec.ts` 전량에서 `/sell` 접근 케이스를 grep해 확인.
location: `web/src/app/(user)/sell/layout.tsx:14`(`requireUser()` — role을 아예 안 읽는다) · `web/e2e/core-flows.spec.ts:16`(`ADMIN_USER` 상수는 이미 있다)
severity: low
summary: `requireUser()`는 role을 안 보므로 `{buyer, seller, admin}` 셋 다 통과한다. buyer는 C8·B8이, seller는 `write-flows`가 간접적으로 덮지만 **admin 경로는 아무 케이스도 없다**. 스펙 Design Notes가 admin 진입을 "의도된 귀결"로 명시 선언했고 2차 리뷰가 "admin을 막자"는 제안을 계약 위반이라며 기각까지 했는데, 그 결정은 문서에만 있고 실행되는 검사가 아니다(CLAUDE.md B9 — 주석·문서는 계약이 아니다).
evidence: `grep "'/sell'" web/e2e/*.spec.ts` 전수 → admin 계정으로 `/sell`을 여는 케이스 0건. `admin@test.com`은 `core-flows.spec.ts:16`·`nav-and-hero.spec.ts:18`에 상수로 이미 있지만 `/admin` 케이스(C6·C7·B4)에만 쓰인다. ⚠️ 지금 동작은 정상이다(`requireUser()`가 role을 안 읽으므로 통과). 문제는 누군가 "관리자가 매물 파는 건 이상하다"며 admin 제외 분기를 넣어도 전량 E2E가 초록이라는 것 — 즉 스펙이 계약 위반이라 판정한 바로 그 변경이 무검사로 들어올 수 있다.
trigger: **관리자 화면·권한을 손대는 Epic 15 Story 15-3을 착수할 때** — 그 스토리가 admin 권한 경계를 다루므로 그 자리에서 한 줄 추가한다(`core-flows.spec.ts`의 C8 옆에 ADMIN_USER로 `/sell` 도달을 단언, 읽기 전용이라 그 파일의 절대 규칙에 맞는다). 함께 판단할 것: 그때도 admin 진입을 유지할지 여부 자체를 재확인한다 — 유지가 결론이면 검사로 못박고, 뒤집는다면 스펙 Always부터 고쳐야 한다.
status: done 2026-08-07 — `web/e2e/core-flows.spec.ts`에 `C8b 관리자 계정이 /sell에 접근하면 매물 등록 화면이 렌더된다` 추가(spec-15-3). admin 진입 유지가 결론으로 재확인됐고(스펙 Always 변경 없음), 읽기 전용으로 그 계약을 검사에 못박았다.

### DW-676: `/account`가 "역할: 구매자"를 실제 화면에 표시한다 — 그 값이 더 이상 무엇을 할 수 있는지 말해주지 않는데도

source_spec: `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md`
origin: 2026-08-06 Story 14.3 3차 리뷰(edge-case 렌즈) 지적, 리뷰 세션이 `account/page.tsx`를 직접 열어 렌더 여부를 확인.
location: `web/src/app/(user)/account/page.tsx:65-66`(`<dt>역할</dt><dd>{roleLabel ?? '-'}</dd>`)
severity: low
summary: Story 14.3 이후 `profiles.role`은 판매 가능 여부와 아무 관계가 없다(로그인만 하면 누구나 판다). 그런데 `/account`는 여전히 "역할: 구매자"를 **실제로 렌더**한다 — 매물을 등록해 팔고 있는 사용자가 자기 계정 화면에서 "구매자"라고 읽는다.
evidence: `AppHeader`의 `roleLabel`은 admin 분기에서만 렌더돼 소비자 화면에 안 보이지만(그래서 DW-453의 죽은 prop 문제와는 별개다), `account/page.tsx:65-66`의 `<dd>`는 consumer 화면에 그대로 그려진다 — 3차 리뷰가 파일을 열어 확인했다. ⚠️ DW-453의 범위가 **아니다**: 그 항목은 "6개 페이지가 렌더되지도 않을 `roleLabel`을 만들려고 요청마다 profiles를 조회한다"는 낭비를 다루고, 여기는 값이 실제로 보이는데 그 의미가 낡았다는 문제다. Story 14.3이 만든 버그도 아니다 — 이 스토리가 role의 의미를 축소하면서 **드러난** 표시다.
trigger: **Story 14.2(가입 화면의 역할 선택 정리)를 구현할 때 그 스토리의 인수조건으로 함께 심는다** — 14.2가 "가입 시 역할을 고르는 것이 무의미해졌다"를 다루므로, "이미 가입한 사람에게 역할을 보여주는 것도 무의미한가"를 같은 자리에서 정하는 것이 자연스럽다. 결론이 "숨긴다"면 `<dt>/<dd>` 쌍을 지우고, "관리자만 의미 있다"면 admin일 때만 표시한다. 정한 뒤 `docs/conventions.md`에 role 값의 현재 의미를 한 줄로 남긴다.
status: open

### DW-677: Follow-up review still recommended for 14-3-소유권-기반-판매-게이트 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-14-3-소유권-기반-판매-게이트.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260806-050742-04ee; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-678: web 신규 가입 계정은 metadata에 role이 없어, Flutter 앱의 역할 기반 화면 5곳이 그 계정에서 판매자 기능을 숨긴다

source_spec: `spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 구현 — spec의 Always 절이 이 갭을 신규 DW로 등재하라고 명시했다(스펙 자신이 "이 변경이 여는 새 갭"이라고 인정한 자리, 구현 세션이 직접 확인).
location: `app/lib/features/auth/auth_controller.dart:28`(`currentRoleProvider`, `user_metadata['role']` 파싱) · 그걸 읽는 5개 화면 — `app/lib/features/listings/sell_screen.dart:146` · `edit_listing_screen.dart:25` · `my_listings_screen.dart:23` · `app/lib/features/auth/home_screen.dart:28` · `app/lib/features/chat/chat_list_screen.dart:22` (모두 `ref.watch(currentRoleProvider)`, `grep -rn currentRoleProvider app/lib`로 확인).
severity: medium
summary: 이 스토리(14.2)가 web 가입 화면의 역할 선택 UI·전송을 없애고 트리거 기본값을 'user'로 바꿨다. 그 결과 web에서 새로 가입한 계정은 `auth.users.raw_user_meta_data`에 role 키가 아예 없다. Flutter의 `currentRoleProvider`는 `profiles.role`이 아니라 이 metadata를 읽으므로 `UserRole.fromValue(null) → null`이 되고, 위 5개 화면이 그 null을 "판매자 아님"으로 해석해 판매자 기능을 숨긴다 — web에서는 팔 수 있는 계정이 앱에서는 영구히 못 파는 상태가 된다.
evidence: `app/lib/features/auth/user_role.dart`의 기존 주석(1~8행)이 정확히 이 결과를 예견하고 있었다("14.2는 이 파일과 그 provider를 함께 봐야 한다"). 실제로 web에서 role metadata 없이 가입한 뒤(이 세션이 브라우저로 직접 검증, `spec142-e2e-check@example.test`) `profiles.role='user'`·`raw_user_meta_data`에 role 키 없음을 DB에서 확인했다 — 그 계정으로 Flutter 앱을 실행하는 것까지는 이 스토리 범위 밖이라 하지 않았지만, `currentRoleProvider`의 파싱 로직(`fromValue(null) → null`)과 5개 화면의 분기 조건은 코드로 직접 확인했다. `main.dart:77`도 같은 provider를 읽지만 admin 여부만 판별하는 `AuthGate` 용도라 role=null이어도 buyer/seller와 동일하게 동작하므로 이 항목의 대상 화면 수(5개)에서 제외한다. DW-668(Story 14.3이 이미 등재)과 다른 항목이다 — DW-668은 "role='buyer'인데 web은 소유권 기반이라 열려 있고 앱은 역할 게이트라 막혀 있다"는 기존 계정 불일치를 다루고, 이 항목은 "web 신규 가입 계정은 앱이 파싱할 role 값 자체가 없다"는 이 스토리가 새로 연 갭이다 — 원인도 다르다(DW-668은 앱의 하드 역할 게이트, 이 항목은 metadata 누락). DW-668을 이 리뷰에서 severity high로 갱신함(이 항목이 그 확인 근거).
trigger: **Flutter 쪽 역할 통합 미러링을 다루는 다음 스토리 착수 시**(spec-14-2 Always 절이 지정한 트리거 문구 그대로) — DW-668이 이미 지정한 Epic 16(앱 정합성 에픽) 첫 스토리와 같은 자리에서 함께 처리하는 것이 자연스럽다. 그 스토리는 `currentRoleProvider`가 무엇을 읽을지(예: `profiles.role`을 직접 조회하도록 바꾸거나, 앱도 소유권 기반으로 게이트를 바꾸는 쪽)부터 정해야 한다.
resolution: **2026-08-07 확인 — `16-0`이 해소했다**(위 DW-668과 같은 커밋). 두 축을 다 막았다: ①앱 화면이 역할을 안 본다(3곳 `requireUser`) ②마이그레이션 `0029`가 admin 외 전 계정의 `user_metadata.role` 키를 제거하고 `profiles.role`을 `'user'`로 통일했다. 앱 가입도 더는 역할을 싣지 않는다(`auth_controller.dart:56` — *"data 에 role 을 넣지 않는다 — 트리거의 기본값에 맡긴다(FR52)"*). 실기기 확인은 DW-668 참조.
status: resolved
### DW-679: 신규 web 가입자가 `/sell`에 실제로 들어가는지(FR52) 확인하는 자동화 테스트가 없다

source_spec: `spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 리뷰(adversarial 렌즈) — DB 트리거 레벨(pytest)은 신규 회귀 4건으로 잘 덮였지만, 이 스토리가 존재하는 이유(FR52) 자체를 지키는 화면 레벨 확인은 이번 세션이 브라우저로 수동 1회 확인한 것뿐이라는 지적.
location: `web/e2e/core-flows.spec.ts:208-235`(C8 — 기존 시드 계정 `role='buyer'`가 `/sell`에 들어가는지만 확인. 그 자체 주석이 "트리거가 바뀌면 이 테스트가 조용히 무의미해진다"고 경고하고 있었는데, 이번에 실제로 트리거가 바뀌었다).
severity: medium
summary: Story 14.2가 신규 web 가입자의 기본 role을 'user'로 바꾸고, 그 계정이 `/sell`(소유권 기반 게이트, Story 14.3)에 들어갈 수 있어야 FR52("로그인만 하면 누구나 사고팔 수 있다")가 성립한다. 이 핵심 경로 — "메타데이터 없이 가입 → role='user' → /sell 접근 가능" — 를 지키는 자동화된 E2E 테스트가 없다. C8은 여전히 role='buyer'인 기존 시드 계정만 본다.
evidence: `web/e2e/*.spec.ts` 전체를 검색(core-flows·write-flows·nav-and-hero·nav-interactions·realtime-chat·landing-and-view-count·viewport-audit)해 role=null 신규가입→/sell 경로를 확인하는 테스트가 없음을 확인. 이번 스토리의 구현 세션이 이 경로를 브라우저로 1회 수동 검증했지만(spec Verification 절의 "브라우저로 실제 가입→로그인→로그아웃" 항목), 그 결과가 코드로 남지 않아 이후 누군가 `guard.ts`를 `requireRole(SELLER)`로 되돌리거나 트리거 기본값을 실수로 바꿔도 CI에서 아무 것도 안 걸린다(첫 시도 run 0381이 CRITICAL로 멈췄던 바로 그 모순이 재발해도 자동으로 알 방법이 없다).
trigger: **`web/e2e/*.spec.ts`를 다음으로 손대는 스토리 착수 시** — C8과 같은 패턴으로 "메타데이터 없이 가입 → role='user' → /sell 접근 가능"을 확인하는 E2E 테스트를 추가한다(DW-664가 열려 있는 한 CI에서는 안 돌지만, 로컬 `npm run test:e2e` 회귀 방어로는 유효하다).
status: open

### DW-680: DW-668의 severity를 high로 올린 근거가 "실측"이 아니다 — 앱을 실제로 돌린 적이 없고, 기존 항목을 제자리에서 고쳐 쓰기까지 했다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰(adversarial 렌즈 지적, 이 리뷰 세션이 장부 헤더·DW-668·DW-678 본문을 직접 읽어 확인).
location: `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-668 `severity:`·`evidence:`·`trigger:` 줄(2026-08-06 커밋 `4defd61`이 제자리 수정) · 대조 대상은 같은 커밋의 DW-678 `evidence:`
severity: medium
summary: 두 가지가 겹쳐 있다. (1) DW-668의 `trigger:`는 "앱 신규 가입자가 role=null로 전 판매화면 차단이 **실제로 발생하는지** 먼저 확인한다(그 경우 severity가 high로 올라간다)"였는데, 실제로 한 것은 Dart 소스의 분기 조건을 읽은 것뿐이다. 같은 커밋의 DW-678이 "그 계정으로 Flutter 앱을 실행하는 것까지는 이 스토리 범위 밖이라 하지 않았다"고 스스로 밝히고 있다. 그런데 DW-668의 evidence에는 "실측 확인됨"이라고 적혔다. (2) 그 갱신이 **제자리 수정**이었다 — 이 파일 헤더가 "append-only, 기존 항목을 지우거나 고쳐 쓰지 않는다"로 못박은 규칙 위반이라 2026-08-06 이전의 원래 평가 문구가 복구 불가능하다.
evidence: 장부 헤더 6행 "이 파일은 **append-only** — 기존 항목을 지우거나 고쳐 쓰지 않는다. 끝나면 지우지 말고 `status: done <날짜>` + `resolution:`으로 닫는다." — 유일하게 허용된 제자리 변경은 '닫기'뿐인데 DW-668은 닫힌 것도 항목이 덧붙은 것도 아니다(`git show 4defd61 -- _bmad-output/implementation-artifacts/deferred-work.md`로 `-severity: medium` / `+severity: high` 확인). "실측"에 대해서는 CLAUDE.md B4가 "**존재 확인은 작동 확인이 아니다**"·"정연한 논증도, 여러 에이전트의 합의도 검증이 아니다"로 이 프로젝트의 기준을 이미 정해 두었다. ⚠️ **결론 자체가 틀렸다는 뜻은 아니다** — 코드 분기(`fromValue(null) → null` → 5개 화면이 판매 기능 숨김)는 명확해서 high가 과한 평가로 보이지도 않는다. 틀린 것은 **근거의 등급 표시**이고, 그게 "코드 읽기 = 실측"이라는 선례로 남는 것이 위험하다. 이 항목을 DW-668 본문 수정이 아니라 **새 항목으로** 여는 이유: 이번 리뷰 세션은 오케스트레이터로부터 "기존 장부 항목을 수정·재개봉·재작성하지 말고 신규 항목만 추가하라"는 지시를 받았다.
trigger: **Epic 16(앱 정합성 에픽) 첫 스토리를 만들 때** — 그 스토리는 어차피 실기기/에뮬레이터로 앱을 띄우므로, 그 자리에서 "web 신규가입 계정으로 앱 로그인 → 판매 화면 차단"을 **실제로 재현**하고 그 결과를 DW-668·DW-678의 `resolution:`에 적는다. 그때 이 항목도 함께 닫는다.
✎ 2026-08-07 — **요구한 실측이 이루어졌다.** 이 항목은 *"앱을 실제로 돌린 적이 없이 severity를 high로 올렸다"*는 자기비판이었고, 처분으로 *"Epic 16 첫 스토리에서 앱을 띄워 재현하고 결과를 적어라"*를 걸었다. 2026-08-07 **실기기(갤럭시 S21, 무선 디버깅)** 로 확인했다: metadata에 role이 없는 계정(`seller@test.com`)으로 앱 로그인 → 홈에 '매물 등록'·'내 매물 관리'가 **보이고** → 등록 폼까지 **도달**한다. 즉 DW-668이 서술한 차단은 **더 이상 재현되지 않는다**(16-0이 고쳤기 때문이다). ⚠️ 다만 *"고치기 전에 그 차단을 실제로 재현해 severity를 검증한다"*는 원래 취지는 **영영 못 한다** — 고친 뒤에 확인했기 때문이다. 그 사실을 숨기지 않고 적어둔다: 이 항목의 교훈("실측 없이 등급을 올리지 마라")은 유효하고, 이번엔 **결과만** 실측했다.
status: resolved
### DW-681: `docs/conventions.md`에 role 어휘 절이 아예 없다 — 새 기본값 `'user'`가 크로스-파트 값인데 정본이 없다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰 — adversarial·verification-gap 두 렌즈가 독립적으로 지적, 리뷰 세션이 `grep -niE "role" docs/conventions.md`로 직접 확인.
location: `docs/conventions.md`(없는 절) · 어휘 사본이 흩어져 사는 3곳 — `web/src/lib/constants.ts:24-32`(`USER_ROLE`에 `'user'` 있음) · `supabase/migrations/0028_handle_new_user_default_role.sql:33-38`(그 값을 쓰는 쪽) · `app/lib/features/auth/user_role.dart:1-8`(3값 enum, `'user'` 없음 + 헤더 주석이 이미 거짓)
severity: medium
summary: `profiles.role`의 어휘는 web·app·db 경계를 가로지르는 값인데, 그 값들의 정본이어야 할 `docs/conventions.md`에 role 절이 없다. 0027이 DB CHECK를 걷어내면서 "어휘가 무엇인가"를 말해주는 층이 DB에서도 사라져, 지금 `'user'`의 정의는 코드 주석 3개뿐이고 그중 하나(`user_role.dart`)는 이미 사실과 다르다.
evidence: `_bmad-output/project-context.md` 규칙 1이 "web·app·api·db 경계를 가로지르는 값은 **전부 거기(conventions.md) 정의돼 있다**. 코드보다 그 문서를 먼저 고친다"로 못박았고, `constants.ts` 헤더도 "docs/conventions.md(단일 출처)와 값이 일치해야 한다"고 적혀 있다. 그런데 `grep -niE "role" docs/conventions.md`는 `service_role` 키(§5)·ARIA role(§접근성)·`information_schema.role_table_grants` 쿼리만 반환하고 `profiles.role` 어휘를 다루는 절은 0건이다. `app/lib/features/auth/user_role.dart:2`의 "(DB 트리거 handle_new_user 가 여전히 이 문자열만 배정한다)"는 0028 이후 **거짓**이며, 그 enum엔 `user` 멤버가 없어 `fromValue('user') → null`이다. project-context.md:26이 기록한 이 리포의 반복 실패 모드("요약이 원본보다 늙어 틀린 값이 에이전트에 주입됐다 — 3건 실측")가 재발하기 좋은 자리다.
trigger: ~~Epic 16 첫 스토리에서 `currentRoleProvider`가 무엇을 읽을지 정하는 자리~~ → **그 자리는 2026-08-06 `16-0`으로 지나갔고 이 항목은 이행되지 않았다.** 재지정: **Story 16.1 착수 시** — 앱 코드를 처음 본격적으로 손대는 스토리이고, 하단 4탭이 `currentRoleProvider`(admin 차단, `main.dart:77`)와 만나는 자리다. 그 인수조건으로 심어뒀다(2026-08-07, epics 문서).
✎ 2026-08-07 재확인 — **아직 없다.** `docs/conventions.md`에 role 어휘를 정의하는 절이 없다(grep: RLS·GRANT 문맥의 `service_role`·`role_table_grants`만 나온다). 다만 `0029`가 **DB 컬럼 주석**으로는 정본을 남겼다: *"계정 종류. admin만 특별 취급(is_admin()) — 그 외는 전부 'user'이며 구매/판매 구분이 없다(역할 통합, 0027·0028·0029). 매물 접근 권한은 이 값이 아니라 소유권(seller_id)+RLS로 판정한다."* 즉 **정본이 DB에만 있고 문서에는 없는 상태**다.
resolution: **2026-08-07 Story 16.1이 해소.** `docs/conventions.md`에 `## 14. Role 어휘` 절을 끝에 추가(§1~13 번호는 그대로)했고, `0029` 컬럼 주석을 정본 문구로 그대로 옮겼다. `user_role.dart`의 stale 헤더 주석(DB 트리거가 여전히 buyer/seller만 배정한다는 거짓 주장)은 이 항목의 범위(문서 절 신설)가 아니라 손대지 않았다 — 필요하면 별도 항목으로.
status: resolved
### DW-682: `0028`의 buyer/seller 통과 분기에 제거 트리거가 어디에도 없다 — Flutter가 role 전송을 멈추는 순간 영구 사문화된다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰(adversarial 렌즈) — 리뷰 세션이 `0028` 본문과 `app/lib/features/auth/signup_screen.dart`를 직접 확인.
location: `supabase/migrations/0028_handle_new_user_default_role.sql:33-35`(`if v_meta_role in ('buyer','seller') then v_role := v_meta_role;`) · 그 분기가 존재하는 유일한 이유인 송신부 `app/lib/features/auth/signup_screen.dart`(가입 시 `data: {'role': role.value}` 전송)
severity: low
summary: 0028이 buyer/seller metadata를 그대로 반영하는 분기를 남긴 것은 오직 "Flutter 앱이 아직 role을 보내니까"라는 하위호환 목적인데(spec Design Notes), 그 전제가 사라질 때 이 분기를 걷어내라고 말하는 항목이 장부에 없다. 그 결과 지금 계정 모집단이 **클라이언트별로 갈린다** — 앱 가입자는 buyer/seller, web 가입자는 user.
evidence: 0028의 주석이 그 분기의 근거를 "Flutter 앱은 이번 스토리에서 UI를 안 건드리므로 여전히 role metadata를 보낸다"로 명시한다 — 즉 조건부 코드인데 해제 조건이 코드에도 장부에도 안 적혀 있다. DW-678은 앱이 role을 **읽는** 쪽(`currentRoleProvider`)만 다루고 **보내는** 쪽은 범위에 없다. CLAUDE.md B8: "미룬 항목엔 '언제·어디서 고칠지'를 대장에 함께 적는다 — '이월'만 적으면 조용히 또 밀린다."
trigger: ~~Epic 16에서 Flutter 가입 화면의 역할 선택을 제거할 때(DW-678과 같은 스토리)~~ → **그 조건은 2026-08-06 `16-0`에서 실제로 발동했는데 이 항목은 이행되지 않았다**(앱이 role 전송을 멈췄다 = 분기가 도달 불가가 됐다). 재지정: **Epic 17 `17-1-정지-회원-쓰기-차단-rls`** — 어차피 마이그레이션을 여는 backend-only 에픽이라 사문화 분기 제거를 같은 마이그레이션 묶음에서 처리하는 게 자연스럽다. sprint-status.yaml의 Epic 17 주석에 심어뒀다(2026-08-07).
✎ 2026-08-07 실측 — **분기는 그대로 있고, 이제 진짜로 죽었다.** `0028_handle_new_user_default_role.sql`이 *"metadata.role이 정확히 'buyer' 또는 'seller'면 그대로 반영한다(하위호환 — Flutter 앱은…)"* 를 유지하는데, 그 유일한 공급자였던 Flutter 가입 화면이 `16-0`에서 role 전송을 멈췄다(`auth_controller.dart:56`). 웹은 14.2에서 이미 멈췄다. **즉 이 분기에 도달할 경로가 하나도 없다.**
status: open
### DW-683: `test_fr11_cover_images_real_db.py`의 픽스처는 "판매자를 만들었다"고 믿지만 그 INSERT는 항상 no-op다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰(edge-case 렌즈) — 리뷰 세션이 해당 픽스처와 `0028` 트리거를 직접 읽어 확인.
location: `api/tests/integration/test_fr11_cover_images_real_db.py:67-72`(`insert into auth.users (id, email)` → 메타 없음, 이어서 `insert into public.profiles (id, role) values (%s,'seller') on conflict (id) do nothing`)
severity: low
summary: `auth.users` INSERT의 AFTER 트리거(`handle_new_user`)가 같은 문장에서 이미 profiles 행을 만들어 두므로, 뒤따르는 `on conflict (id) do nothing` INSERT는 **한 번도 적용된 적이 없다**. 이 픽스처가 만든 계정의 role은 `'seller'`가 아니라 트리거 기본값이며, Story 14.2 이후 그 값은 `'buyer'`에서 `'user'`로 바뀌었다.
evidence: 두 문장을 직접 읽어 확인했다 — 트리거가 먼저 행을 만들므로 명시 INSERT는 항상 conflict 경로다. 지금 아무것도 안 깨지는 이유는 `supabase/migrations` 어디에도 `role='seller'`로 분기하는 RLS 정책이나 GRANT가 없기 때문이다(`grep -rn "role = 'seller'" supabase/migrations` → 0건. `is_admin()`만 role을 보고, 그건 `'admin'` 정확일치다). **이 스토리가 만든 문제는 아니다**(그 전에도 'seller'가 아니라 'buyer'였다) — 다만 값이 한 칸 더 멀어졌고, 형제 파일들이 쓰는 `conftest._create_user`는 이제 role 계약을 단언하는데 이 파일만 그 방어 밖에 있다. 나머지 5개 통합 테스트 파일은 `'{"role":"seller"}'` 메타를 명시하거나 `_create_user`를 쓴다.
trigger: **`test_fr11_cover_images_real_db.py`를 다음으로 손대는 스토리 착수 시**, 또는 그보다 먼저 **`profiles.role`을 읽는 RLS 정책·GRANT가 처음 생길 때**(그 순간 이 픽스처는 "판매자가 아닌 행"으로 정책을 시험하며 조용히 통과하게 된다). 고치는 법은 시드 파일들이 이미 쓰는 패턴 — `on conflict` INSERT를 `update public.profiles set role='seller' where id=%s`로 바꾸거나 `conftest._create_user(cur, email, role='seller')`를 쓰는 것.
status: open

### DW-684: 통합 테스트 계정 모집단이 운영과 갈라졌다 — `role='user'` 계정으로 도는 시나리오 테스트가 0건이다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰 2차(adversarial 렌즈) — 리뷰 세션이 `_create_user` 호출부를 전수 확인(`grep -rn "_create_user(" api/tests/`).
location: `api/tests/integration/conftest.py:45`(`def _create_user(cur, email, role="buyer")` — 기본 인자) · 그 기본값을 그대로 쓰는 호출부 12곳(`test_chat_unread_real_db.py`·`test_chat_idempotency_real_db.py`·`test_chat_realtime_broadcast_real_db.py`·`test_role_check_relax_real_db.py`)
severity: medium
summary: Story 14.2가 신규 가입 기본 role을 `'user'`로 바꿨는데, 통합 테스트 헬퍼의 기본 인자는 여전히 `"buyer"`다. 그래서 채팅·안읽음·Realtime·조회 같은 **실제 시나리오** 테스트는 전부 `buyer`/`seller` 계정으로 돌고, `'user'` 계정이 등장하는 곳은 이번에 추가한 트리거 계약 테스트뿐이다. 즉 운영의 신규 가입자 유형(전부 `'user'`)에 대해 시나리오가 한 번도 검사되지 않는다.
evidence: 호출부 전수 확인 결과 `role=` 인자를 명시하는 곳은 seller가 필요한 자리뿐이고, 나머지는 전부 기본값 `"buyer"`를 탄다. 지금 아무것도 안 깨지는 이유는 `supabase/migrations` 어디에도 `profiles.role`로 분기하는 RLS 정책·GRANT가 없기 때문이다(`is_admin()`만 role을 보고 그건 `'admin'` 정확일치). 그래서 **오늘의 버그가 아니라 함정**이다 — `profiles.role`을 읽는 정책이 처음 생기는 날, 그 정책은 실제 사용자 유형에 대해 한 번도 검사되지 않은 채 배포된다. DW-683(`test_fr11_cover_images_real_db.py`의 seller 픽스처가 실은 no-op)과 같은 축의 문제이며, 그 항목이 지목한 "정책이 처음 생길 때"가 이 항목의 발화 시점이기도 하다.
trigger: **`profiles.role`을 읽는 RLS 정책·GRANT가 처음 생기는 스토리 착수 시**(그 스토리의 인수조건에 "정책 테스트를 `role='user'` 계정으로도 돈다"를 심는다), 또는 그보다 먼저 **Epic 16의 앱 role 정합성 스토리에서 `currentRoleProvider`가 무엇을 읽을지 정할 때**. 고치는 법은 `_create_user`의 기본 인자를 `None`(메타데이터 없음 = 운영 신규 가입과 동일)으로 뒤집고, buyer가 실제로 필요한 호출부만 명시하게 하는 것 — DW-683과 한 커밋에서 처리하는 것이 자연스럽다.
resolution: **2026-08-07 확인 — `16-0`이 해소했다.** 시드가 바뀌어 **시나리오 테스트가 도는 계정 모집단 자체가 `role='user'`가 됐다**: `supabase/seed-local/01_accounts.sql`이 admin 1건을 뺀 전 계정을 `'user'`로 만든다(`✎ 2026-08-06 역할 통합(0029)` 주석). 로컬 DB 실측도 일치한다 — `select role, count(*) from profiles` → `admin 1 · user 8`, buyer/seller 0건. 즉 "role='user' 계정으로 도는 시나리오 테스트가 0건"이라는 전제가 사라졌다.
status: resolved
### DW-685: role 관련 DW 5건이 전부 "Epic 16 첫 스토리"를 트리거로 지목했는데, 그 스토리(16.1)에는 role 얘기가 한 줄도 없다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰 2차(adversarial 렌즈) — 리뷰 세션이 `epics-increment-2026-07-12.md`의 Epic 16 절 전문을 직접 읽어 확인.
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:1340-1400`(Epic 16: 16.1 디자인 토큰 미러 + 하단 4탭 내비 · 16.2 이미지·카드 · 16.3 신뢰속성·찜 · 16.4 실시간 채팅 — 어디에도 가입·인증·role 없음) · 그 자리를 지목한 장부 항목 DW-668·DW-678·DW-680·DW-681·DW-682의 `trigger:` 줄
severity: medium
summary: 위 5개 항목은 전부 "Epic 16(앱 정합성 에픽) 첫 스토리를 만들 때 인수조건으로 심는다"를 해제 조건으로 적었다. 그런데 Epic 16의 첫 스토리는 디자인 토큰·내비이고 16.2~16.4도 role과 무관하다. 그리고 epics 문서에도 `sprint-status.yaml`에도 아무것도 심어두지 않았다 — 지정만 하고 심지 않은 상태다.
evidence: CLAUDE.md B8이 정확히 이 실패를 경고한다 — "미룬 항목엔 '언제·어디서 고칠지'를 대장에 함께 적는다. '이월'만 적으면 다음 작업은 대장이 아니라 상위 문서를 보고 만들어지므로 조용히 또 밀린다 — 그 자리를 지정하고, **지정한 곳에도 실제로 심는다**(B5)." 지금은 앞 절반만 됐다. Epic 16을 만드는 사람이 참조할 문서는 epics-increment이고, 거기엔 role 얘기가 없으므로 5건이 통째로 한 번 더 밀린다. 실피해는 DW-678이 이미 기술한 것 — web 신규 가입 계정이 Flutter 앱에서 판매자 기능을 영영 못 본다.
trigger: **Epic 16의 스토리를 실제로 만드는 순간(=`bmad-create-story` 또는 스프린트 계획으로 16.1을 여는 시점)** — 그보다 먼저 손댈 수 있으면 더 좋다: `epics-increment-2026-07-12.md`의 Epic 16 절에 "앱 역할 통합 미러링" 스토리를 하나 추가하고(내용: `currentRoleProvider`가 `profiles.role`을 읽게 하거나 앱 게이트를 소유권 기반으로 전환 + `docs/conventions.md`에 role 어휘 절 추가 + 0028의 buyer/seller 통과 분기 제거 판단), 위 5개 항목의 `trigger:`가 가리키는 대상을 그 스토리로 특정한다. ⚠️ 이 항목을 닫을 때 DW-668·678·680·681·682의 본문을 고치지 말 것 — 장부는 append-only이므로, 새 스토리가 생겼다는 사실은 이 항목의 `resolution:`에 적는다.
resolution: **2026-08-07 확인 — 해소.** 이 항목이 요구한 것은 *"role DW들이 가리킬 실재하는 스토리를 만들라"*였고, 2026-08-06에 **`16-0-앱-역할통합-미러링-기존계정-정리`가 실제로 신설되고 완료**됐다(sprint-status.yaml). 즉 role 항목들의 갈 곳이 16.1이 아니라 16-0으로 정해졌고 그 자리에서 실행됐다. ⚠️ 다만 **그 스토리가 대장을 닫지 않아** DW-668·678·684와 이 항목이 열린 채 남아 있었다 — 오늘 그 뒷정리를 하며 닫는다. (교훈: 사람이 손으로 돌린 스토리는 엔진이 대장을 안 닫는다. 에픽 14 착수 전 13-10·13-11에서도 같은 일이 있었다.)
status: resolved
### DW-686: Flutter 앱 테스트가 14.2가 깨뜨린 계약을 "정상"으로 단언하고 있다 — `flutter test`는 영원히 초록이다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰 2차(verification-gap 렌즈) — 리뷰 세션이 `app/test/widget_test.dart`와 `app/lib/features/auth/user_role.dart`를 직접 읽고, `grep -rln` 으로 앱 테스트가 대상 화면을 하나도 안 건드림을 확인.
location: `app/test/widget_test.dart:24-27`(`expect(UserRole.fromValue(null), isNull)` · `expect(UserRole.fromValue('unknown'), isNull)`) · `app/lib/features/auth/user_role.dart:10-13`(enum에 `user` 멤버 없음 → `fromValue('user')`도 null)
severity: medium
summary: DW-678은 **행동**의 갭(web 신규 가입 계정이 앱 판매화면에서 차단됨)을 등재했다. 이 항목은 그 갭의 **검증층**이 비어 있다는 별개의 사실이다 — 앱 테스트는 "role metadata가 없으면 null이 맞다"를 정답으로 단언하므로, CI의 app 잡(`flutter test`)은 이 스토리가 만든 불일치가 지속되는 내내 초록이다. 즉 앱 쪽에서 이 문제를 red로 알려줄 검사가 하나도 없다.
evidence: `widget_test.dart`가 단언하는 것은 옛 계약(role은 buyer/seller/admin 셋뿐)이고, 0028 이후 DB가 실제로 배정하는 `'user'`는 그 enum에 아예 없다. `grep -rln "sell_screen|my_listings|edit_listing|home_screen|chat_list_screen|currentRoleProvider" app/test/` → 0건(다섯 화면 어느 것도 앱 테스트가 건드리지 않는다). 그래서 "앱 CI가 초록"은 "앱이 정상"이 아니라 "앱이 무엇을 약속하는지 아무도 안 본다"를 뜻한다. **지금 당장 red가 되는 단언을 심는 것은 일부러 CI를 깨는 것**이라 이번 스토리에서 하지 않았다 — 앱이 새 계약을 채택하는 스토리와 같은 커밋에 들어가야 한다.
trigger: ~~Epic 16의 앱 role 정합성 스토리 착수 시~~ → **그 스토리(`16-0`)는 2026-08-06에 끝났고 이 항목은 이행되지 않았다.** 재지정: **Story 16.1 착수 시** — 앱 테스트를 다시 손대는 자리다. 그 인수조건으로 심어뒀다(2026-08-07, epics 문서).
✎ 2026-08-07 실측 — **아직 없다.** `grep -rn 'currentRoleProvider' app/test/` → **0건**. `16-0`이 위젯 테스트 8건을 추가했지만(`require_user_test.dart` 등) 전부 **게이트가 로그인만 보는지**를 보고, `currentRoleProvider`가 role 없는 세션에서 무엇을 돌려주는지는 아무도 단언하지 않는다. 그 provider는 지금도 살아 있고(`auth_controller.dart:28`) `main.dart:77`의 admin 차단이 그 값을 쓴다 — 즉 **쓰이는데 계약이 안 잡혀 있다.**
resolution: **2026-08-07 Story 16.1이 해소.** `app/test/current_role_provider_test.dart`(신규)가 `currentRoleProvider`를 role 없음/`'user'`/`'admin'` 세 세션에서 각각 단언한다(`null`/`null`/`UserRole.admin`) — `require_user_test.dart`의 `_fakeUser`+`ProviderScope(overrides:)` 패턴을 재사용. `flutter test`로 실행·통과 확인(리뷰 세션이 직접 재실행).
status: resolved
### DW-687: web 배포와 원격 `0028` 적용 사이의 창에서 가입한 계정은 영구히 `'buyer'`로 남는다

source_spec: `_bmad-output/implementation-artifacts/spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
origin: 2026-08-06 Story 14.2 후속 리뷰 2차(edge-case 렌즈) — 두 변경의 적용 경로가 다르다는 점을 리뷰 세션이 확인(web=Git 연동 자동 배포, 마이그=수동 적용).
location: `supabase/migrations/0028_handle_new_user_default_role.sql`(아직 원격 미적용) · `web/src/app/(auth)/signup/page.tsx:61`(role 미전송) · 절차 문서 `docs/deployment-runbook.md`
severity: low
summary: 이 스토리의 web 변경과 DB 변경은 한 커밋이지만 **배포 경로가 다르다**. web이 먼저 나가면 그 사이 가입한 계정은 0009의 옛 기본값 `'buyer'`를 받고, forward-only 원칙상 백필이 없으므로 그대로 굳는다. 결과적으로 계정 모집단이 3분된다 — Flutter 가입자(buyer/seller) · 이 창의 web 가입자(buyer) · 그 이후 web 가입자(user).
evidence: CLAUDE.md B3이 이미 순서를 정해두었다 — "배포 순서는 만드는 쪽 → 읽는 쪽: 데이터 구조(DB) 먼저, 그걸 읽는 API·화면이 나중." 이 스토리는 그 순서를 지키면 창이 열리지 않는데, 지금 스펙의 잔여 위험 목록엔 "원격에 0028 미적용"만 적혀 있고 **순서 제약이 명시돼 있지 않다**. 실피해는 크지 않다(판매 게이트는 14.3이 소유권 기반으로 바꿔 role을 안 보고, 영향은 역할 라벨 표시와 Flutter 화면 분기 정도) — 하지만 되돌릴 수 없는 종류라 등재한다. 0027이 DB CHECK를 걷어냈으므로 잘못된 값이 자동으로 걸리지도 않는다.
trigger: **`0028`을 원격(운영) Supabase에 적용할 때 = 이 브랜치를 `main`에 병합하기 직전** — 마이그레이션을 **먼저** 적용하고 그 다음에 web 배포가 나가도록 순서를 고정한다. 이미 창이 열린 뒤라면 그 사이 가입한 계정 목록(`select id, email, created_at from auth.users where created_at between …`)을 확인해 기록만 남긴다(일괄 UPDATE는 이 스펙의 Never 절이 금지한다 — 별도 판단 필요).
status: open

### DW-688: Follow-up review still recommended for 14-2-가입-역할선택-제거-트리거-기본-role after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-14-2-가입-역할선택-제거-트리거-기본-role.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260806-050742-04ee; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-689: E2E `C2 매물 목록 검색·필터`가 13-10 데이터 보강으로 무효화됐다 — 필터가 안 걸려도 초록이 될 수 없어 red
origin: 2026-08-06 Epic 14 마감 E2E 실행(사람). Epic 14가 만든 회귀가 아니다.
location: `web/e2e/core-flows.spec.ts:70-83`
severity: medium
summary: `totalCount`(필터 없음)와 `filteredCount`(지역=서울)를 **첫 페이지의 카드 수**로 세고 `filteredCount < totalCount`를 단언하는데, 둘 다 `PAGE_SIZE`에 걸려 24로 같아져 실패한다.
evidence: 추정이 아니라 실측·산술로 확정했다 — `web/src/app/(user)/search/page.tsx:65`의 `PAGE_SIZE = 24`, 로컬 DB `on_sale` **158건**, `region='서울'` **43건**. 43 > 24이므로 필터를 걸어도 첫 페이지는 24장 그대로다. 테스트 주석 자체가 낡은 전제를 적고 있다("로컬 DB on_sale 95건", "서울 24건") — Story **13-10 검색 데이터 보강**(2026-08-05, 매물 93→158)이 그 전제를 깼다. Epic 14는 `web/src/components/`·검색 경로를 하나도 건드리지 않았다(`git log 12e1db9..HEAD -- web/src/components/` 0건).
why_it_matters: 이 검사는 **필터가 실제로 결과를 좁히는가**를 보는데, 지금은 결과와 무관하게 red다. 즉 필터 회귀를 못 잡는다. 11-4가 11-1의 실DB 테스트를 무효화하고 6일간 아무도 몰랐던 것(#180)과 **같은 유형**이다 — 한 스토리의 변경이 다른 스토리의 검사를 무효화했고, E2E가 verify 게이트에 없어서 에픽 마감까지 아무도 몰랐다.
fix_sketch: 카드 수가 아니라 페이지네이션 총계(헤더의 전체 건수)로 비교하거나, 첫 페이지 안에서 확실히 좁혀지는 조건(예: `region='서울'` 대신 24건 미만인 값)으로 바꾼다. 어느 쪽이든 **일부러 필터를 무력화해 red를 확인**한 뒤 원복해 green을 확인할 것(CLAUDE.md B4 — 만들었다가 아니라 잡는다가 완료다).
trigger: **다음 E2E 전수 실행 직전**(= Epic 15 마감 시점). 그 전에 사용자가 지시하면 즉시.
status: ✅ 해소 (2026-08-06, 사용자 지시로 즉시 수정). `core-flows.spec.ts`의 C2가 카드 수 대신 **화면에 그려진 총 건수**(`{totalCount}건의 매물`)를 읽어 비교하도록 고쳤다 — 총 건수는 페이지네이션과 무관하므로 데이터가 더 늘어도 살아 있다. red/green 실측: `search/page.tsx:180`의 지역 필터를 무력화하자 `Expected: < 158 / Received: 158`로 red(옛 단언이라면 24 vs 24라 필터와 무관하게 red였다), 원복 후 green.

### DW-690: E2E `image-fallback` /search·/ai가 **2026-07-29 next/image 전환 이후 8일간 red**였고 아무도 몰랐다
origin: 2026-08-06 Epic 14 마감 E2E 실행(사람). Epic 14가 만든 회귀가 아니다.
location: `web/e2e/image-fallback.spec.ts:43-46`(abort 라우트 패턴) · 대상 `web/src/components/listings/ListingCardImage.tsx`
severity: medium
summary: 스펙이 `page.route('**/storage/v1/object/public/**')`로 **브라우저의 스토리지 직접 요청**을 가로채 이미지 전면 장애를 재현하는데, 매물 카드가 `next/image`로 바뀐 뒤로는 브라우저가 `/_next/image?url=…`만 요청하고 스토리지는 **서버가** 대신 가져간다. 그래서 abort 카운터가 0이 되고, 스펙에 심어둔 "0-of-0 침묵 통과 방지" 가드가 red를 낸다.
evidence: 커밋 이력으로 시점을 특정했다 — 스펙은 `51c6154`(Story 11-5)가 가드까지 포함해 만들었고 그 뒤 **한 번도 수정되지 않았다**. 카드 이미지는 `b39a2b2`(DW-541, 2026-07-29 "매물 카드 사진을 next/image로 전환 — 장당 194KB → 8KB")가 바꿨다. 같은 실행에서 **상세(`/listings/[id]`)의 같은 테스트는 통과**했는데, `ListingGallery.tsx:141`이 의도적으로 평범한 `<img>`를 쓰기 때문이다(파일 주석에 근거 명시) — 통과/실패가 정확히 그 경계로 갈린다.
why_it_matters: 이 검사가 지키던 것은 **"매물은 뜨는데 사진만 전면 실패해도 깨진 아이콘 0개 + 플레이스홀더 전량 발동"**(대장 #73)이다. 8일간 그 보호가 사실상 없었다. ⚠️ 동시에 **가드가 제 일을 했다** — 카운터가 없었다면 "깨진 이미지 0개"만 보고 **조용히 초록**이 됐을 것이고, 검사가 아무것도 안 보는 상태가 발각되지 않았다.
fix_sketch: abort 패턴에 `**/_next/image**`를 추가(카드 경로)하고 스토리지 패턴은 유지(상세 경로). 고친 뒤 **두 경로 각각에서 카운터가 0이 아님**을 확인할 것 — 한쪽만 걸려도 나머지는 다시 0-of-0이 된다.
trigger: **다음 E2E 전수 실행 직전**(= Epic 15 마감 시점). 그 전에 사용자가 지시하면 즉시.
status: ✅ 해소 (2026-08-06, 사용자 지시로 즉시 수정). abort 라우트에 `**/_next/image**`를 **추가**했다(스토리지 패턴은 유지 — 카드는 next/image, 상세는 평범한 `<img>`라 소비처마다 브라우저가 부르는 URL이 다르다). red/green 실측: `ListingCardImage`의 `onError` 폴백과 `naturalWidth===0` 보정을 둘 다 무력화하자 `/search`·`/ai`가 **"깨진 이미지가 0개여야 함"**으로 red — 전에는 "abort가 한 번도 안 걸렸음"이었으니 이제야 **실제 폴백 동작을 검사**한다. 같은 실행에서 상세는 통과해(거긴 안 깨뜨렸다) red가 정확히 깨뜨린 자리에만 났음도 확인. 원복 후 green.

### DW-691: "신규 가입 계정이 실제로 `/sell`에 도달한다"를 **자동으로 보는 검사가 없다** — 사용자가 명시한 인수 조건인데 사람만 확인했다
origin: 2026-08-06 Epic 14 마감 검증(사람). 세 축 중 이 축만 자동 검사가 없어 손으로 확인했다.
location: `web/e2e/core-flows.spec.ts`(C8 옆이 자연스러운 자리) · 현존 부분검사 `web/src/app/(auth)/signup/__tests__/signupNoRoleMetadata.test.ts` · `api/tests/integration/test_role_check_relax_real_db.py`
severity: medium
summary: 사용자가 에픽 14의 최종 조건으로 **세 계정(기존 buyer·기존 seller·신규 가입)이 전부 `/sell`에 도달**할 것을 명시했다. ①은 E2E `C8`, ②는 E2E `E1~E5`가 본다. **③만 자동 검사가 없다.**
evidence: 14-2가 만든 것은 두 개의 **반쪽 검사**다 — 단위테스트는 "가입 화면이 role metadata를 안 보낸다"까지만 보고, 실DB 통합테스트는 "트리거가 role 없으면 'user'를 넣는다"까지만 본다. **그 둘을 이어붙인 "그래서 그 계정이 /sell에 간다"는 아무도 안 본다.** 14-2는 `web/e2e/`를 하나도 건드리지 않았다(`git show --stat f1ae434 | grep e2e` 0건). 사람이 실브라우저로 확인해 **실제로 통과함**은 확인했으나(가입→role='user' 확인→/sell 폼 렌더), 그 확인은 재실행되지 않는다.
why_it_matters: 이 프로젝트가 반복해서 데인 자리다 — "존재 확인 ≠ 작동 확인"(CLAUDE.md B4). 두 반쪽이 각각 초록인 채로 합이 깨질 수 있다. 예: 판매 게이트가 나중에 다시 역할을 보게 바뀌면(Epic 15의 관리자 역할 통합 반영 등) 단위·통합 테스트는 그대로 초록인데 신규 가입자만 조용히 막힌다. 그게 정확히 14-2가 처음에 에스컬레이션했던 그 결함이다.
fix_sketch: `C8` 바로 옆에 `C9`를 추가한다 — 고유 이메일로 가입 → `runPsql`로 그 계정의 `role`이 트리거 기본값임을 고정(리터럴로 'user'를 적지 말고 "buyer/seller가 아님"을 단언해도 됨) → `/sell`에서 '매물 등록' heading 렌더 확인 → **테스트가 만든 계정 삭제**(write-flows가 쓰는 원복 증명 관례를 따를 것). 폼 제출은 하지 않는다(core-flows는 읽기 전용 스펙).
trigger: **다음 E2E 전수 실행 직전**(= Epic 15 마감 시점) — DW-689·690과 같은 자리에서 함께 고친다. 그 전에 사용자가 지시하면 즉시.
status: ✅ 해소 (2026-08-06, 사용자 지시로 즉시 수정). `core-flows.spec.ts`에 **C9**를 신설했다 — 고유 이메일로 실제 가입 → 가입 화면에 역할 선택이 없음을 단언 → psql로 배정된 role이 buyer/seller가 **아님**을 고정(리터럴 'user'로 적지 않는다 — 지켜야 할 것은 기본값이 무엇인가가 아니라 "판매자 역할이 아닌 계정도 /sell에 간다"이다) → `/sell` 폼 렌더 확인 → `finally`에서 계정 삭제 + 0건 원복 증명. red/green 실측: `sell/layout.tsx`를 옛 `requireRole(USER_ROLE.SELLER)`로 되돌리자 C8·C9 둘 다 red(=C9가 14.2의 원래 에스컬레이션 결함을 실제로 잡는다), 원복 후 green. 실패했을 때도 검증 계정이 남지 않음을 DB로 확인했다.

### DW-692: 기존 계정의 buyer/seller 역할을 없앨 수 있는가 — **조사 완료: 가능하다.** 실행은 별도 결정
origin: 2026-08-06 사용자 질문("기존 계정들의 역할을 없앨 수 있는지 확인 필요"). 에픽 14는 신규 가입만 바꿨고 기존 행은 forward-only 원칙과 14.2 스펙의 `Never`("기존 계정 일괄 UPDATE 금지")로 손대지 않았다.
location: `profiles.role`(기존 9행: buyer 3 · seller 5 · user 1 · admin 1) · 소비처는 아래 evidence
severity: medium
summary: **결론 = 가능하고, DB 층에서는 막는 것이 하나도 없다.** 남은 영향은 **화면 라벨뿐**이다. 다만 되돌릴 수 없는 변경이라(B3) 실행은 스토리로 다룬다.
evidence: 문서가 아니라 DB·코드에서 직접 확인했고, 마지막엔 **실제로 UPDATE를 실행해 보고 롤백**했다(트랜잭션, 부작용 0).
  · **RLS: `role`을 참조하는 정책이 0개다** — `pg_policies`를 조건 검색한 결과 `qual`/`with_check` 어디에도 role이 없다. 즉 역할 값을 바꿔도 행 접근 권한은 전혀 안 움직인다.
  · **`is_admin()`은 `role = 'admin'` 정확일치만 본다** — `pg_proc`에서 본문 확인. admin을 UPDATE 대상에서 빼면 관리자 기능은 무변(FR54 존치).
  · **`requireRole()`의 남은 호출처는 `(admin)/layout.tsx`의 ADMIN 하나뿐이다** — `/sell`은 14.3이 `requireUser()`로 옮겼다. buyer/seller로 막는 자리가 web에 없다.
  · **web의 나머지 `profiles.role` 소비처는 전부 표시용이다** — `search`·`wishlist`·`ai` 페이지의 상단바 `roleLabel`, `admin/members`의 역할 열. 전부 `ROLE_LABEL[...] ?? role` 폴백을 쓰므로 모르는 값이 와도 안 깨진다(14.1이 심고 `roleLabelFallback.test.ts`가 강제).
  · **Flutter 앱은 `profiles.role`을 아예 안 읽는다** — `currentRoleProvider`(auth_controller.dart)가 읽는 것은 세션의 `user_metadata['role']`이다. 즉 이 UPDATE는 앱 화면에 영향이 없다(앱의 판매자 게이트 3곳은 Epic 16 몫으로 그대로 남는다).
  · **실행 실험(2026-08-06, 트랜잭션 후 rollback)**: `update profiles set role='user' where role<>'admin'` → `UPDATE 9`, admin 1명 유지, role 참조 RLS 0개, on_sale 158건·채팅방 5개 불변. 0027이 완화한 CHECK가 새 값을 받아준다는 것도 이 성공 자체가 증거다.
why_it_matters: 지금은 **계정 모집단이 갈라져 있다** — 옛 web/앱 가입자(buyer·seller)와 14.2 이후 web 가입자(user). 화면에는 "구매자"·"판매자"·"회원"이 섞여 보이는데, 역할 통합 이후 그 구분은 **아무 기능도 하지 않는다**(권한은 소유권으로 판정). 즉 뜻 없는 라벨이 남아 사용자와 관리자를 헷갈리게 한다.
open_questions_for_human:
  · 앱 사용자의 `user_metadata['role']`도 함께 지울 것인가 — 지우면 Flutter의 판매자 화면 3곳이 그 계정에 숨겨진다(Epic 16이 앱을 고치기 전까지). **지우지 않는 쪽이 안전**하고, `profiles.role`만 정리해도 web 목적은 달성된다.
  · 시드 스크립트(`supabase/seed-local/01_accounts.sql`·`seed.sql`)가 계정을 buyer/seller로 되돌려 놓으므로, 로컬을 다시 시드하면 원상복귀한다 — 시드도 함께 바꿀지.
  · 되돌릴 수 없다(B3). 누가 원래 판매자였는지는 `listings.seller_id`로 여전히 알 수 있으므로 실질 정보 손실은 없다는 점을 확인했다.
trigger: **Epic 15의 `15-3-회원관리-역할통합-반영` 스토리** — 그 스토리가 이미 "관리자 회원관리 화면의 구매자/판매자 필터 정리(FR61)"를 소유한다. 화면에서 그 구분을 걷어내는 자리와 데이터에서 걷어내는 자리는 같이 판단해야 한다(따로 하면 화면은 정리됐는데 데이터만 남거나 그 반대가 된다). 마이그레이션 1개(일괄 UPDATE)를 그 스토리 범위에 추가할지 사용자가 결정한다.
status: ✅ 해소 (2026-08-06, 사용자 지시 "바로시작"). **A안(앱 게이트를 먼저 풀고 양쪽 데이터를 정리)** 으로 실행했다.
  실행 순서가 핵심이다 — 14.3 → 14.2에서 배운 것과 같다: **문을 먼저 열고 역할을 나중에 지운다.** 반대로 하면 앱에서 아무도 못 판다.
  ① 앱 게이트 3곳(`sell_screen`·`my_listings_screen`·`edit_listing_screen`)이 각자 들고 있던 `role != UserRole.seller` 인라인 가드를 공용 `requireUser(ref, title)`로 교체했다(`lib/features/auth/require_user.dart` 신설 — 웹 `guard.ts`의 `requireUser()`와 같은 자리·같은 모양). 셋이 각자 들고 있으면 하나를 빠뜨려도 나머지가 초록이라 아무도 모른다(웹에서 실제로 난 사고 #180).
  ② 앱 가입 화면의 역할 선택 UI + `signUp(role:)` + `data:{'role':...}` 전송을 제거했다. **이게 빠지면 앞의 정리가 전부 헛일이다** — 앱 가입이 계속 role을 실어 보내면 새 계정마다 buyer/seller가 다시 심긴다.
  ③ `home_screen`의 판매 진입(`if (isSeller)`)을 로그인 사용자 전원에게(`if (canSell)`) 열었다 — 문을 열어도 문패가 안 보이면 도달할 수 없다. 프로필 역할 배지는 '회원' 고정(관리자는 모바일에서 애초에 차단, AR9).
  ④ `chat_list_screen`의 역할별 빈 상태 문구를 역할 중립 문구로 바꿨다 — 한 계정이 양쪽을 다 하므로 어느 쪽으로 갈라도 절반은 틀린 안내가 된다.
  ⑤ 마이그레이션 `0029_unify_existing_account_roles.sql` — admin 제외 전 계정의 `profiles.role`을 'user'로 통일하고 `auth.users.raw_user_meta_data`에서 `role` 키를 제거한다. 사후조건 블록이 두 축 모두 정리됐는지 스스로 확인한다.
  ⑥ 시드 2종(`seed-local/01_accounts.sql`·`seed.sql`)에서 buyer/seller 지정·승격을 걷어냈다 — 안 바꾸면 재시드 때마다 부활해 마이그레이션 결과와 갈라진다.
  검증(전부 실측): `flutter analyze` 0 issues · `flutter test` 87 passed(신규 위젯 테스트 8건 포함) · `check_migrations` 통과 · api 단위 490 · api 실DB 통합 105 passed(0029 경계 검사 2건 신규) · web lint 0 · web vitest 313 · **E2E 62 passed 0 failed**.
  red/green 실측 4건: ⓐ 화면 3곳이 공용 게이트를 쓰는지 보는 검사를 **고치기 전에 먼저 만들어 red 확인**(3건 실패) 후 교체해 green. ⓑ `0029`에서 admin 제외 조건을 빼자 `test_0029_preserves_admin`이 red, 원복 green. ⓒ·ⓓ는 DW-689·690 항목 참조.
  ⚠️ 남은 것: 앱의 **실기기 눈 확인**은 못 했다(이 환경에 안드로이드 기기·에뮬레이터 없음 — `flutter devices`가 리눅스 데스크톱만 잡는다). 위젯 테스트로 대신 고정했고 실물 확인 자리는 Epic 16-6이다. 또한 "앱 가입이 role을 안 보낸다"는 전역 supabase 클라이언트를 가로채야 해서 단위 테스트 층에서 못 본다 — 같은 자리(16-6)에서 본다.


### DW-693: E2E 전수 실행이 **머신 포화 시 비결정적으로 실패**한다 — 기본 워커 수가 이 환경에 과하다
origin: 2026-08-06 역할 통합 마감 검증 중 실측. 제품 결함이 아니라 실행 환경 문제다.
location: `web/playwright.config.ts`(workers 미지정 = Playwright 기본값) · 실행 명령 `npm run test:e2e`
severity: low
summary: 같은 커밋·같은 명령으로 세 번 돌렸는데 **실패 건수와 실패 대상이 매번 달랐다**(6건 → 4건 → 3건). 전부 30~50초 타임아웃이고, `--workers=2`로 줄이면 **62 passed 0 failed**로 초록이다.
evidence: 추측을 배제하려고 원인 후보를 하나씩 잘랐다. ①`git diff 1e9cb33 -- web/src/`가 **0줄** — 제품 코드는 직전 초록 실행과 바이트 동일하다. ②실패한 화면(채팅·`/ai`)이 `profiles.role`을 쓰는 곳은 상단바 라벨 하나뿐이고 폴백이 있다(기능 의존 없음). ③실패 대상이 실행마다 바뀐다(결정적 회귀라면 같은 것이 실패해야 한다). ④`--workers=1`·`--workers=2`에서 전부 통과. ⑤`uptime` **load average 15.8/21.3/16.2 (16코어)**, `free -g` **available 2GB / total 7GB** — 포화 상태. 상주 프로세스가 VS Code 서버·22시간 된 `next dev`(RSS 1.18GB)·`bmad-loop tui`로 이미 무겁다. ⑥첫 실행에서는 PostgREST가 `PGRST002`로 **7초간 503**을 냈다(마이그레이션 DDL이 유발한 스키마 캐시 재적재) — 그 창에 걸린 케이스들이 함께 죽었다.
why_it_matters: 이 상태로는 **E2E 초록/빨강이 신호가 아니라 잡음**이 된다. 회귀를 찾으려 볼 때마다 "이게 진짜인가 포화인가"를 매번 다시 판정해야 하고, 그 판정 비용이 검사의 가치를 깎는다. 실제로 이번에 그 판정에만 실행 4회가 들었다.
fix_sketch: `playwright.config.ts`에 `workers`를 명시한다(이 머신 실측 기준 2가 안전). 다만 CI 러너와 로컬의 여력이 다르므로 `process.env.CI ? N : 2` 형태가 맞는지, 아니면 환경변수로 받을지는 CI 배선(대장 #168)과 함께 판단한다. **워커를 줄이면 실행 시간이 늘어난다**(2.6분 vs 4.3분) — 그 대가를 받아들일지가 결정 포인트다.
trigger: **다음 E2E 전수 실행 직전**(= Epic 15 마감 시점) — DW-689·690과 같은 자리. 그때도 같은 증상이면 그 자리에서 워커 수를 고정한다.
status: open

### DW-694: `0029`를 운영에 적용하면 **이미 배포된 v1.0.0 APK 사용자가 판매를 못 하게 된다** — 앱 재배포가 선행되어야 한다
origin: 2026-08-06 "모바일 테스트를 Epic 15 뒤로 미뤄도 되나" 판단 중 발견. 미룰 수 있느냐를 따지다 **진짜 마감이 Epic 15가 아니라 운영 반영 시점**임이 드러났다.
location: GitHub Release `v1.0.0`(2026-07-05, 운영 Supabase·운영 API를 봄) · `supabase/migrations/0029_unify_existing_account_roles.sql` · 앱 옛 게이트(그 빌드 안의 `role != UserRole.seller`)
severity: **high** — 되돌릴 수 없고, 사용자에게 직접 보이는 기능 상실이다.
summary: 0029는 운영 계정의 `auth.users.raw_user_meta_data`에서 `role` 키를 지운다. 그런데 **배포된 v1.0.0 APK는 그 값을 읽어 판매 화면을 막는 옛 코드**를 담고 있다. 즉 0029가 운영에 적용되는 순간, 그 APK를 쓰는 사람은 `currentRoleProvider`가 null이 되어 매물 등록·내 매물 관리·수정 세 화면에서 "판매자만 이용할 수 있습니다."를 보게 된다.
evidence: ①`gh release list`로 v1.0.0이 실재하고 릴리스 본문에 "백엔드: AI 검색 API는 운영(prod) 서버 연결"이 명시돼 있다. ②그 빌드는 2026-07-05로 16-0(2026-08-06)보다 앞서므로 공용 `requireUser` 게이트가 들어 있지 않다. ③앱이 읽는 역할의 출처가 `profiles.role`이 아니라 세션 metadata임은 `auth_controller.dart:31`에서 확인했고, 0029가 지우는 것이 바로 그 키다.
why_it_matters: 웹 쪽 순서 문제(DW-687)는 "그 사이 가입한 계정만 옛 기본값으로 굳는다"라 영향이 국소적이었다. 이건 다르다 — **이미 남의 손에 있는 빌드**가 서버 데이터 변경만으로 기능을 잃는다. 앱은 서버처럼 한 번에 갱신할 수 없으므로 "고치고 다시 배포"가 즉시 반영되지도 않는다.
resolution_options:
  · (A) **권장** — 앱 실기기 확인 → 새 APK 배포 → **그 다음에** 0029를 운영에 적용. 순서를 지키면 창이 아예 안 열린다.
  · (B) 데모용이라 실사용자가 없다면 감수하고 먼저 적용 — 단 **그 판단을 여기 적고** 릴리스 노트에 "업데이트 필요"를 남길 것.
  · (C) 0029의 metadata 제거(②번 UPDATE)만 빼고 `profiles.role` 통일(①번)만 먼저 적용 — 웹 목적은 달성되고 앱은 안 깨진다. 단 "다 지운다"는 결정이 절반만 이행된 상태로 남으므로 나머지를 언제 할지 함께 정해야 한다.
trigger: **`main` 병합 = 운영 반영을 준비하는 시점** — 그때 (A)(B)(C) 중 하나를 사용자가 고른다. DW-687(마이그 먼저·web 나중)과 **같은 자리에서 함께 판단**한다. 그 전까지는 `test/bmad-loop`·`develop`에만 있으므로 위험이 실현되지 않는다.
status: open

### DW-695: `AppHeader.tsx`(관리자·소비자 전 화면 공유 상단바)가 아직 원시 `zinc-*` 클래스를 쓴다 — DW-546 실측 목록 밖이라 새어 있었다
origin: 2026-08-06 Story 15.1(관리자 6화면 디자인 리스킨) 계획 중 코드베이스 조사에서 발견. DW-546이 2026-07-29에 소비자 화면 10곳을 실측해 리스트업했을 때 `components/layout/AppHeader.tsx`는 그 목록에 없었다(당시 0건이었거나 애초에 안 봤을 가능성) — 지금 조사로는 존재를 확인했다(정확한 건수는 미측정, 이 조사는 파일 존재 여부만 확인함).
location: `web/src/components/layout/AppHeader.tsx`
severity: low — 시각적 불일치일 뿐 기능 결함 아님. 다만 관리자·소비자 16개 화면을 전부 토큰화해도 공유 상단바 하나가 안 바뀌면 리스킨이 "완료"로 안 보인다.
summary: 15.1은 이 파일을 의도적으로 범위 밖에 뒀다(스펙 `spec-15-1-...`의 Never 절 참조) — DW-546이 측정·합의한 16개 파일 밖이라 블라스트 반경이 이 스토리보다 넓어진다(전 화면이 공유하는 셸이므로 건드리면 15.1 범위를 넘는 회귀 위험을 스스로 만든다). 그래서 여기 등재만 하고 손대지 않는다.
trigger: **다음에 `AppHeader.tsx`를 실제로 건드리는 스토리 착수 시**(현재는 소비 스토리 없음) — 또는 Epic 15 마감 시점에 "관리자 6화면·소비자 10화면은 리스킨됐는데 상단바만 원시 색"이라는 잔여 불일치가 눈에 띄면 그 자리에서 판단. 그 전이라도 사용자가 지시하면 즉시.
status: open

### DW-696: 토큰 리스킨이 **화면 단위로는 반쪽**이다 — 대상 파일 밖 4개 파일 14건이 남아 같은 화면 안에서 원시색과 토큰이 섞인다
origin: 2026-08-06 Story 15.1 후속 리뷰 패스에서 리포 전수 grep으로 실측. 15.1은 인텐트가 지정한 16개 **파일**을 기준으로 닫혔고 그 범위 grep은 실제로 0건이다 — 문제는 기준이 파일이었고 사용자가 보는 단위는 **화면**이라는 점이다.
location: `web/src/app/(user)/search/page.tsx`(6건) · `web/src/components/ai/ChatAssistant.tsx`(5건) · `web/src/components/landing/PopularRecentGrid.tsx`(2건) · `web/src/app/(user)/ai/page.tsx`(1건)
severity: low — 시각적 불일치일 뿐 기능 결함 아님.
summary: 15.1이 `SearchFilters.tsx`를 토큰화했지만 그 필터를 감싸는 **부모 페이지** `search/page.tsx`는 원시 `zinc-*` 그대로다. 홈(`app/page.tsx`)도 토큰화됐지만 홈이 렌더하는 `PopularRecentGrid`는 아니다. 결과적으로 검색·홈·AI 세 화면이 한 화면 안에서 절반만 리스킨된 상태다. `AppHeader.tsx`(3건)는 [[DW-695]]가, `(auth)/layout.tsx`(1건)는 DW-547이 이미 소유하므로 여기서는 제외했다.
evidence: `grep -rn "zinc-" web/src/` 전수 실행(2026-08-06) 결과 6개 파일 18건. 그중 15.1 인텐트가 명시적으로 제외한 2개 파일 4건을 뺀 나머지가 위 4개 파일 14건이다. 15.1의 AC grep은 인텐트가 정한 대상 파일 경로만 훑도록 범위가 한정돼 있어(인텐트 Always: "각 대상 파일에서") 이 14건은 초록 신호에 잡히지 않는다 — AC가 틀린 게 아니라 **AC가 답하는 질문이 "화면이 통일됐나"가 아니라 "대상 파일이 치환됐나"**였다.
why_it_matters: 리스킨의 목적은 "사용자 화면과 시각적으로 어긋나지 않게" 하는 것인데, 파일 기준으로 닫으면 목적 기준으로는 안 닫힌다. 지금 검색 화면을 열면 토큰 필터 위에 zinc 페이지가 얹혀 있다 — 15.1 이전보다 오히려 대비가 눈에 띈다.
fix_sketch: 4개 파일을 같은 토큰 집합으로 치환한다(신규 토큰 추가 없음, 15.1과 동일한 방식). 함께 판단할 것: 이 규칙을 `web/src/app/fonts.budget.test.ts` 형태의 vitest 소스 스캔(허용목록 방식)으로 박을지 — 지금은 손으로 치는 grep이라 다음에 누가 `bg-zinc-100`을 다시 넣어도 초록이다(CLAUDE.md B9 "규칙은 어길 수 없는 자리에 박는다").
trigger: **Story 15.2(관리자 반응형) 착수 시** — 15.2가 뷰포트 감사로 이 화면들을 어차피 다시 연다. 15.2의 인수조건 체크박스로 심는다.
status: done 2026-08-06
resolution: closed by spec-15-2(관리자 반응형) — 대상 4개 파일(`search/page.tsx`·`ChatAssistant.tsx`·`PopularRecentGrid.tsx`·`ai/page.tsx`) 14건 `zinc-*`를 15.1과 동일한 토큰으로 치환. `grep -rn "zinc-" <4파일>` 0건 확인.

### DW-697: 관리자 **상세 라우트 2곳을 어떤 자동 검사도 열지 않는다** — 15.1이 그 안에 새 표시 로직을 넣었는데 지키는 검사가 없다
origin: 2026-08-06 Story 15.1 후속 리뷰 패스에서 verification-gap·edge-case 렌즈가 각각 독립적으로 지적, 실측으로 확인.
location: `web/e2e/core-flows.spec.ts` C6(관리자 목록 4개 라우트만 방문) · `web/e2e/viewport-audit.spec.ts`(admin 경로 0건) · `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts`(대상 파일이 `ChatRoomMessages.tsx`로 하드코딩 + "버블 정확히 3개" 단언)
severity: low — 현재 코드는 맞게 동작한다(수동 확인 완료). 위험은 **다음 변경**에 있다.
summary: `/admin/chats/[roomId]`와 `/admin/listings/[id]`는 e2e가 한 번도 열지 않는다(C6은 목록 4개만 방문해 "에러 문구 없음 + li 개수>0"만 본다). 15.1이 관리자 채팅방에 `isSeller` 좌/우 분기와 네 번째 `max-w-[80%]` 말풍선을 새로 넣었는데, 말풍선 줄바꿈 규칙을 지키려고 만들어 둔 `messageBubbleWrap.test.ts`는 사용자 파일 경로가 하드코딩돼 있어 이 새 말풍선을 보지 않는다.
evidence: ①`grep -rn "'/admin" web/e2e/*.spec.ts` → 목록 라우트와 `/admin`만 나오고 상세 라우트는 없다. ②`messageBubbleWrap.test.ts`가 `COMPONENT` 상수로 파일 하나를 고정하고 `toHaveLength(3)`을 단언한다 — 리포 전체 `max-w-[80%]` 사이트는 이제 4곳이다. ③이 결함은 이미 한 번 실현됐다: 15.1 1차 리뷰가 관리자 말풍선에 `break-words`가 빠진 것을 **사람 눈으로** 잡아 패치했고, 그동안 tsc·lint·vitest·e2e는 전부 초록이었다. ④`viewport-audit.spec.ts`의 `page.goto`는 `/`·`/search`·`/listings/{id}`·`/chat/{roomId}`·`/ai`뿐 — 규칙 D5(반응형 무결성)의 뷰포트 매트릭스가 관리자 화면에는 존재하지 않는다.
why_it_matters: 검사가 없는 게 아니라 **검사가 있는데 새 자리를 안 본다**는 점이 비싸다. 다음 사람은 "말풍선 규칙은 테스트가 지킨다"고 믿고 관리자 화면을 고치는데, 그 믿음이 그 파일에서만 거짓이다.
fix_sketch: ①`messageBubbleWrap.test.ts`가 두 말풍선 소스를 모두 훑게 하고 `toHaveLength(3)` 리터럴을 파일별 단언으로 바꾼다. ②`viewport-audit.spec.ts`에 관리자 6경로를 추가한다(D5는 "관리자 화면도 예외 없음"이라고 명시한다). ③C6을 상세 라우트까지 한 단계 넓혀 `isSeller` 좌우 배치를 발신자 라벨 기준으로 단언한다.
trigger: **Story 15.2(관리자 반응형) 착수 시** — 15.2가 관리자 화면의 뷰포트 감사를 소유하므로 ②가 그 스토리의 본체와 같은 자리다. ①③도 함께 15.2의 인수조건 체크박스로 심는다.
status: done 2026-08-06
resolution: closed by spec-15-2 — ① `messageBubbleWrap.test.ts`가 관리자 말풍선(`admin/chats/[roomId]/page.tsx`)까지 스캔하도록 확장(파일별 개수를 각각 단언, DW-701과 같은 자리에서 처리). ② `viewport-audit.spec.ts`에 관리자 6경로(목록 4 + 상세 2)를 추가해 가로스크롤 없음을 3뷰포트에서 확인. ③ `core-flows.spec.ts` C6에 `/admin/listings/[id]`·`/admin/chats/[roomId]`를 추가하고 `isSeller` 기준 좌/우 배치를 단언(코드리뷰 patch로 양쪽 배치가 실제로 각각 1건 이상 나오는지도 함께 확인해, 시드 데이터 편향으로 허수아비 통과가 되지 않게 함).

### DW-698: `bg-brand-petrol` 위 리터럴 `text-white`가 **한 자리 남아** 다크에서 2.98:1로 AA에 미달한다
origin: 2026-08-06 Story 15.1 3차 리뷰 패스에서 adversarial·edge-case·verification-gap 세 렌즈가 각각 독립적으로 지적, 리포 전수 grep + WCAG 재계산으로 실측 확인.
location: `web/src/app/(user)/sell/OptionPicker.tsx:93` (선택된 옵션 칩)
severity: medium — 다크 모드에서 선택된 옵션 라벨이 AA 미달(2.98:1). 기능은 동작하나 읽기 어렵다.
summary: 15.1 2차 리뷰가 "리터럴 `text-white`는 다크에서 스왑되지 않는데 `bg-brand-petrol`은 오히려 밝아진다"는 결함을 5곳(`Button.tsx` primary · 사용자 말풍선 2 · 관리자 말풍선 · 홈 AI FAB)에서 `text-surface-base`로 고쳤는데, 같은 조합이 `OptionPicker.tsx`에 한 곳 더 있었고 그 파일은 15.1의 대상 16개 파일 목록에 없어 손대지 않았다.
evidence: `grep -rn "bg-brand-petrol" web/src/ | grep "text-white"` → 실제 클래스 문자열은 `OptionPicker.tsx:93` 한 건만 남는다(나머지 1건은 `Button.tsx`의 설명 주석). WCAG 상대휘도로 재계산: 다크 `--brand-petrol` #4FA39D 위 #FFFFFF = **2.98:1**(AA 4.5:1 미달) — 2차 패스가 다른 5곳에서 측정해 "명백한 회귀"라고 부른 것과 같은 숫자다. `git show 34cfaf4:…/OptionPicker.tsx`로 이 조합이 15.1 이전부터 있던 것임을 확인했다(이번 diff가 만든 게 아니다).
why_it_matters: 규칙을 "고쳤다"고 기록했는데 같은 규칙이 한 파일 옆에서 여전히 깨져 있다. 더 나쁜 건 이걸 잡는 검사가 리포에 하나도 없다는 것 — `grep -rn "대비\|contrast\|WCAG"`가 vitest 34개 파일과 e2e 전체에서 0건이다. 다음에 누가 `bg-brand-petrol text-white`를 새로 써도 전부 초록이다.
fix_sketch: ①`text-white` → `text-surface-base`로 교체(다른 5곳과 동일, 라이트 5.75 / 다크 5.54). ②함께 판단할 것: `fonts.budget.test.ts` 형태의 vitest 소스 스캔으로 "opacity 없는 `bg-brand-petrol`과 리터럴 `text-white`가 같은 클래스 문자열에 공존하면 red"를 박을지 — 항상 어두운 `bg-petrol-deepest/85`(PhotoUploader, 최악 7.62:1로 안전)는 허용목록으로 뺀다. [[DW-696]]의 fix_sketch가 제안한 zinc 스캔과 같은 자리에 함께 넣는 것이 싸다.
trigger: **`web/src/app/(user)/sell/` 아래를 다음에 건드리는 스토리 착수 시**, 또는 Epic 15 마감 점검 시 — 둘 중 먼저 오는 쪽. 그 스토리의 인수조건 체크박스로 심는다.
status: open

### DW-699: 라이트 모드에서 **호버 피드백이 사실상 없다** — `surface-base`↔`surface-raised` 차이가 1.045:1이다
origin: 2026-08-06 Story 15.1 3차 리뷰 패스에서 adversarial·edge-case 렌즈가 지적, 토큰 hex로 재계산해 확인.
location: `web/src/app/(user)/chat/page.tsx`(방 목록 행) · `web/src/app/(user)/chat/[roomId]/page.tsx`(매물 칩) · `web/src/app/(admin)/admin/chats/page.tsx`(관리자 방 목록 행)
severity: low — 시각 피드백 부재. 클릭은 정상 동작하고 커서·밑줄 등 다른 신호가 있는 자리도 있다.
summary: 15.1 2차 리뷰가 "죽은 호버"를 고치며 `hover:bg-surface-base` → `hover:bg-surface-raised`로 바꿨는데, 라이트 모드에서 두 토큰은 #FAFAF8 대 #FFFFFF로 rgb 차이가 (5,5,7)뿐이다. 다크(#201F1C↔#2B2A26)는 실제로 보이지만 라이트는 여전히 안 보인다.
evidence: `globals.css`의 토큰 hex로 계산: 라이트 대비 **1.045:1**, 다크 **1.147:1**. 15.1 이전(`hover:bg-zinc-50` = #FAFAFA)도 라이트에선 똑같이 죽어 있었으므로 **회귀가 아니라 이월된 결함**이다 — 다만 2차 패스의 트리아지 로그는 이 항목을 "라이트·다크 양쪽"이 고쳐진 것처럼 적었다.
why_it_matters: 표면 토큰 두 개만으로는 라이트 모드 호버를 표현할 수 없다는 사실이 아직 어디에도 안 적혀 있다. 다음 사람이 또 같은 조합으로 "호버를 넣었다"고 믿게 된다.
fix_sketch: ①호버 전용 토큰(`--surface-hover`)을 `globals.css`에 추가하거나, ②표면 대신 다른 축의 신호를 겹친다(`hover:border-brand-petrol` 또는 `hover:underline`). ②가 새 토큰 없이 되므로 싸다. 어느 쪽이든 **바꾼 뒤 실제 델타를 숫자로 적는다**(눈으로 닫지 않는다).
trigger: **Story 15.2(관리자 반응형) 착수 시** — 15.2가 위 3개 화면 중 관리자 목록을 어차피 다시 연다. 15.2의 인수조건 체크박스로 심는다.
status: done 2026-08-06
resolution: closed by spec-15-2 — 3개 파일(`chat/page.tsx`·`chat/[roomId]/page.tsx`·`admin/chats/page.tsx`)의 죽은 호버를 `hover:border-brand-petrol`로 교체(fix_sketch 옵션② 채택, 새 토큰 추가 없음). 회귀 가드로 `hoverContrast.test.ts`를 추가하고, 한 파일을 실제로 옛 클래스로 되돌려 red 확인 → 복구해 green 확인(CLAUDE.md B4).

### DW-700: `(auth)/layout.tsx`의 주석이 **거짓이 됐다** — "로그인·회원가입 본문은 아직 원시색"이라고 적혀 있으나 15.1이 리스킨을 마쳤다
origin: 2026-08-06 Story 15.1 3차 리뷰 패스에서 adversarial 렌즈가 지적, 해당 줄과 리스킨 결과를 대조해 확인.
location: `web/src/app/(auth)/layout.tsx:19` (주석)
severity: low — 주석만의 문제로 렌더 결과에는 영향이 없다.
summary: 그 주석은 "로그인·회원가입 본문은 **아직** 옛 원시 색(`zinc-*`)을 쓰고 있고 그 통일은 Epic 15에서"라고 예고한다. 15.1이 바로 그 두 페이지 본문을 토큰으로 치환했으므로 이제 사실과 다르다. 15.1 인텐트가 "`(auth)/layout.tsx`를 건드리지 않는다"고 명시했기 때문에 이번 패스에서 고치지 않았다.
evidence: `web/src/app/(auth)/login/page.tsx`·`signup/page.tsx`의 `zinc-*` 잔존은 0건(15.1 AC grep으로 재측정). 반면 `layout.tsx:19` 주석은 그대로다. 같은 파일에 남은 `zinc-*` 1건은 클래스가 아니라 이 주석 안의 문자열이다 — [[DW-696]]이 "14건" 산정에서 이 파일을 제외한 근거로 삼은 DW-547은 이미 `status: done 2026-07-29`이므로, 이 주석은 현재 아무도 소유하지 않는다.
why_it_matters: 다음 사람이 auth 레이아웃을 열면 "본문 리스킨이 아직 남았다"는 안내를 받는다 — 이미 끝난 일을 다시 하거나 중복 항목을 대장에 올린다. DW-546이 막으려던 실패 그 자체다.
fix_sketch: 그 문단을 "15.1에서 본문 리스킨 완료"로 갱신하거나 삭제한다. 파일을 건드리는 김에 `zinc-*` 문자열 자체를 없애면 리포 전수 grep의 잡음도 함께 줄어든다.
trigger: **`(auth)/` 아래를 다음에 건드리는 스토리 착수 시**, 또는 Epic 15 마감 점검 시 — 둘 중 먼저 오는 쪽.
status: open

### DW-701: [[DW-697]]의 `fix_sketch ①`을 **그대로 실행하면 아무것도 검사하지 않는다** — 정규식이 백틱 템플릿 리터럴을 못 잡는다
origin: 2026-08-06 Story 15.1 3차 리뷰 패스에서 adversarial 렌즈가 지적, 정규식과 대상 소스를 직접 대조해 확인.
location: `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts:32` (`BUBBLE_CLASS`) · 대상 소스 `web/src/app/(admin)/admin/chats/[roomId]/page.tsx:165`
severity: medium — 가드를 "설치했다"고 기록하면서 실제로는 0개를 검사하게 되는 종류의 실패다.
summary: DW-697은 "`messageBubbleWrap.test.ts`가 두 말풍선 소스를 모두 훑게 한다"를 처방한다. 그런데 그 파일의 `BUBBLE_CLASS`는 홑따옴표·쌍따옴표로 감싼 문자열만 잡도록 쓰여 있고, 15.1이 만든 관리자 말풍선은 **백틱 템플릿 리터럴**(`` className={`w-fit max-w-[80%] break-words …`} ``)이다. 대상 파일만 늘리면 관리자 파일에서 매치가 0건이 되고, "모든 버블이 break-words를 갖는다" 루프는 빈 배열 위를 돌아 **공허하게 통과**한다.
evidence: 정규식은 `/'[^'\n]*max-w-\[80%\][^'\n]*'|"[^"\n]*max-w-\[80%\][^"\n]*"/g` — 백틱 분기가 없다. 관리자 말풍선의 className은 `` `…${isSeller ? … : …}` `` 형태의 템플릿 리터럴이다. 참고로 `toHaveLength(3)` 리터럴도 파일 하나에 묶여 있어 대상이 늘면 반드시 red가 되지만, 그건 DW-697이 이미 적었다.
why_it_matters: DW-697의 위험 서술("검사가 있는데 새 자리를 안 본다")이 그 처방을 따랐을 때 **한 겹 더** 재생산된다. 게다가 실패가 red가 아니라 green으로 나타나므로 아무도 눈치채지 못한다.
fix_sketch: `BUBBLE_CLASS`에 백틱 분기를 더한다(``/`[^`]*max-w-\[80%\][^`]*`/`` — 템플릿 리터럴은 여러 줄일 수 있으므로 `\n` 제외 규칙을 그대로 쓰면 안 된다). 그리고 CLAUDE.md B4대로 **일부러 깨서 red를 확인한 뒤** 되돌려 green을 확인한다 — 관리자 파일에서 `break-words`를 지웠을 때 실제로 실패하는지가 이 항목의 유일한 완료 기준이다.
trigger: **[[DW-697]]의 `fix_sketch ①`을 실행하는 시점** — 즉 Story 15.2 착수 시. 같은 자리에서 함께 처리한다.
status: done 2026-08-06
resolution: closed by spec-15-2 — `BUBBLE_CLASS`에 백틱 템플릿 리터럴 분기를 추가(`` `[^`]*max-w-\[80%\][^`]*` ``, `\n` 제외 규칙은 백틱 분기에 적용하지 않음 — 관리자 버블 클래스가 여러 줄에 걸쳐 있어서). CLAUDE.md B4대로 관리자 버블에서 `break-words`를 실제로 지워 red 확인 → 복구해 green 확인.

### DW-702: Follow-up review still recommended for 15-1-관리자-6화면-디자인-리스킨 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-15-1-관리자-6화면-디자인-리스킨.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260806-184136-ee73; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-703: 관리자 채팅방 좌/우 배치 테스트가 "기타"(당사자 아닌) 발신자 분기를 한 번도 실측하지 않는다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 코드리뷰(adversarial 렌즈)에서 지적, 시드 데이터·`senderLabel` 분기를 대조해 확인.
location: `web/src/app/(admin)/admin/chats/[roomId]/page.tsx` (senderLabel의 `기타 ${senderId.slice(0,8)}` 분기) · `web/e2e/core-flows.spec.ts` C6(새 좌/우 배치 루프)
severity: low — 현재 시드 데이터로는 재현 불가하며 기능 결함이 아니다. 위험은 향후 실제 데이터에 있다.
summary: C6의 새 루프는 시드 방에 실제로 있는 메시지만 순회한다. 그 방엔 구매자·판매자 메시지만 있고 "기타" 발신자가 없어, `senderLabel`의 세 번째 분기와 그에 대응하는 좌측 정렬이 이 테스트로 검증되지 않는다.
fix_sketch: "기타" 발신자가 있는 시드 방(또는 케이스)을 추가하거나, 최소한 이 분기를 겨냥한 단위 테스트를 별도로 둔다.
trigger: 관리자 채팅방 화면을 다음에 건드리는 스토리 착수 시, 또는 실제 운영 데이터에서 "기타" 발신자 메시지가 관측될 때.
status: open

### DW-704: 관리자 채팅방 좌/우 배치 테스트의 기대값이 독립적인 DB 근거가 아니라 같은 렌더의 라벨에서 파생된다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 코드리뷰(adversarial 렌즈)에서 지적.
location: `web/e2e/core-flows.spec.ts` C6 · `web/src/app/(admin)/admin/chats/[roomId]/page.tsx`
severity: low — buyer/seller 컬럼이 소스에서 뒤바뀌는 것과 같은 근본적 데이터 결함이 있어야 드러나는, 좁은 위험이다.
summary: 테스트가 기대 클래스를 도출하는 근거가 독립적인 `room.buyer_id`/`seller_id`가 아니라 같은 렌더 안의 `senderLabel` 문자열이다. `senderLabel`과 `isSeller`가 둘 다 같은 두 컬럼에서 파생되므로, 그 컬럼 자체가 뒤바뀌는 소스단 버그가 나도 라벨과 정렬이 "같이 틀린 채" 서로 일치해 테스트를 통과한다.
fix_sketch: 핵심 케이스 하나는 헬퍼가 DB에서 직접 가져온 buyer_id/seller_id와 비교해 독립적으로 검증한다(예: `fetchChatRoomIdForSeedUser`가 buyer_id도 함께 반환하게 하고, `SEED_USER.email`에 해당하는 메시지는 반드시 `items-start`여야 한다고 별도로 단언).
trigger: `fetchChatRoomIdForSeedUser` 또는 관리자 채팅방 좌/우 배치 로직을 다음에 건드리는 스토리 착수 시.
status: open

### DW-705: `AdminSidebar`(및 원본 `SiteNav`)의 리사이즈 자동닫힘이 포커스를 잃을 수 있다 — 트리거가 이미 숨겨진 상태에서 포커스 복귀를 시도한다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 코드리뷰(adversarial 렌즈)에서 지적, `FocusTrap.tsx` cleanup과 CSS 클래스를 대조해 확인.
location: `web/src/components/ui/FocusTrap.tsx`(cleanup의 `triggerRef.current?.focus()`) · `web/src/components/layout/AdminSidebar.tsx`(햄버거 `min-[760px]:hidden`) · `web/src/components/layout/SiteNav.tsx`(동일 패턴)
severity: low — 접근성 회귀 가능성이나, 이 diff가 새로 만든 결함이 아니라 SiteNav에서 이식된 기존 패턴이다.
summary: `matchMedia` 리스너가 760px 이상에서 패널을 강제로 닫으면 `FocusTrap`이 언마운트되며 트리거로 포커스를 되돌리려 시도하는데, 이 시점에 트리거 버튼은 `min-[760px]:hidden`으로 CSS `display:none` 상태라 실제로 포커스를 받을 수 없다 — 키보드 사용자의 포커스가 조용히 유실될 수 있다. `SiteNav.tsx`의 동일 메커니즘에도 같은 위험이 있다.
fix_sketch: 리사이즈로 닫힐 때는 포커스를 안전한 곳(예: 데스크톱 사이드바의 active 링크)으로 명시적으로 옮기거나, `FocusTrap`이 대상이 숨겨져 있으면 포커스 복귀를 건너뛰게 한다.
trigger: `FocusTrap.tsx` 또는 `SiteNav.tsx`/`AdminSidebar.tsx`의 리사이즈-자동닫힘 로직을 다음에 건드리는 스토리 착수 시, 또는 접근성 감사 시.
status: open

### DW-706: `AdminSidebar`(및 원본 `SiteNav`)의 바깥-클릭-닫힘이 클릭한 요소가 아니라 햄버거 버튼에 포커스를 남길 수 있다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 코드리뷰(edge-case-hunter 렌즈)에서 지적, `pointerdown`/`focusin` 핸들러의 실행 순서를 대조해 확인.
location: `web/src/components/layout/AdminSidebar.tsx`(outside-pointerdown-close) · `web/src/components/ui/FocusTrap.tsx`(`handleFocusIn`) · `web/src/components/layout/SiteNav.tsx`(동일 패턴)
severity: low — 마우스 클릭 동작 자체는 정상 실행된다. 그 직후 키보드/스크린리더로 이어가는 사용자에게만 영향.
summary: 메뉴가 열린 채 바깥의 클릭 가능한 요소를 누르면, pointerdown이 "메뉴를 닫아라"는 상태 변경을 예약하는 것과 거의 동시에 아직 화면에 남아있는 `FocusTrap`의 `focusin` 감지가 "포커스가 밖으로 나갔다"고 판단해 포커스를 도로 끌어온다. 그 다음에야 메뉴가 실제로 닫히며, 최종 포커스는 사용자가 클릭한 요소가 아니라 햄버거 버튼에 남는다. `SiteNav.tsx`에서 그대로 이식된 기존 패턴이다.
fix_sketch: 메뉴를 닫을 때 상태 변경을 동기적으로 즉시 반영하거나(예: `flushSync`), `FocusTrap`이 "닫히는 중"에는 바깥 포커스 재포착을 건너뛰게 한다.
trigger: `FocusTrap.tsx` 또는 `SiteNav.tsx`/`AdminSidebar.tsx`의 바깥-클릭-닫힘 로직을 다음에 건드리는 스토리 착수 시, 또는 접근성 감사 시.
status: open

### DW-707: `fetchChatRoomIdForSeedUser`가 "buyer·seller 메시지가 둘 다 있다"는 전제를 코드로 강제하지 않는다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 코드리뷰(adversarial 렌즈)에서 지적.
location: `web/e2e/helpers.ts`(`fetchChatRoomIdForSeedUser`)
severity: low — 다른 헬퍼들의 fail-loud 관례와 다르다는 지적일 뿐, 현재 시드 데이터로는 문제없이 동작한다.
summary: "가장 오래된 방에 buyer·seller 메시지가 둘 다 있다"는 사실은 여러 테스트(C6 좌/우 배치, viewport-audit 관리자 상세 등)가 기대는 전제인데, 코드가 강제하지 않고 사람이 시드 데이터를 보고 주석으로 적어 둔 가정일 뿐이다. `order by created_at asc limit 1`이 어떤 방을 고를지는 시드 데이터가 바뀌면 달라질 수 있다.
fix_sketch: 헬퍼가 "메시지가 2건 이상이고 buyer·seller 발신이 각 1건 이상"인 방을 직접 쿼리로 고르게 하거나, 최소한 그 조건을 헬퍼 안에서 assert하는 가드를 넣는다(다른 헬퍼들의 fail-loud 관례와 동일하게).
trigger: `fetchChatRoomIdForSeedUser`를 다음에 건드리는 스토리 착수 시, 또는 시드 데이터를 갱신할 때.
status: open

### DW-708: `zinc-*` 금지 규칙에 **실행되는 가드가 없다** — 4파일을 손으로 grep해 닫았고, 그 판단 자체가 DW-696 안에 열린 질문으로 적혀 있었다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 후속 리뷰(verification-gap·adversarial 렌즈가 각각 독립 지적), DW-696 원문과 대조해 확인.
location: `web/src/app/(user)/search/page.tsx` 등 리스킨 대상 전반 · 선례 기법은 `web/src/app/fonts.budget.test.ts`(허용목록 소스 스캔)
severity: low — 지금 화면은 정상이다. 위험은 "규칙이 닫혔다고 기록됐는데 아무도 안 지키는" 상태에 있다.
summary: DW-696의 `fix_sketch`는 처방과 함께 **"함께 판단할 것: 이 규칙을 `fonts.budget.test.ts` 형태의 vitest 소스 스캔으로 박을지 — 지금은 손으로 치는 grep이라 다음에 누가 `bg-zinc-100`을 다시 넣어도 초록이다(CLAUDE.md B9)"** 라는 열린 질문을 함께 적어 뒀는데, 그 질문은 답하지도 이월하지도 않은 채 항목이 `done`으로 닫혔다. 인수조건도 사람이 한 번 치는 grep 명령이라 회귀 시점에 아무도 없다. 실제로 이번 리뷰에서 같은 커밋이 규칙을 어긴 사례(`search/page.tsx` 페이저의 죽은 호버)가 나왔는데, 그건 `hoverContrast.test.ts`라는 **실행되는** 가드를 넓혀서 잡았다 — 대비 축은 가드가 있고 색 토큰 축은 없다는 비대칭이 남았다.
fix_sketch: `fonts.budget.test.ts` 방식의 vitest 소스 스캔으로 `web/src` 전역 `zinc-` 0건을 고정하되, 아직 열려 있는 `AppHeader.tsx`([[DW-695]])와 `(auth)/layout.tsx`를 **이름을 적은 예외**로 둔다 — 그래야 그 두 건이 닫히기를 기다리지 않고 지금 가드를 세울 수 있고, 예외 목록이 곧 남은 부채의 목록이 된다.
trigger: **[[DW-695]]를 처리하는 스토리 착수 시**(그때 예외 목록이 줄어드는 것이 자연스러운 자리다), 또는 그전에 새로 `zinc-*`가 발견될 때.
status: open

### DW-709: `BUBBLE_CLASS`의 백틱 분기가 **앵커가 없어** 인접한 두 템플릿 리터럴 사이를 가로질러 매치될 수 있다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 후속 리뷰(adversarial 렌즈)에서 지적, 정규식과 파일 주석의 근거를 대조해 확인.
location: `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts`(`BUBBLE_CLASS`의 세 번째 분기)
severity: low — 현재 두 대상 파일의 내용에서는 재현되지 않는다. 개수 단언(`toHaveLength`)이 사고를 red로 드러내 주기도 한다.
summary: 따옴표 분기는 `[^'\n]`으로 "한 줄 안에서 닫힌다"는 앵커를 갖고, 그 앵커가 없으면 앞선 따옴표에서 시작한 매치가 여러 줄을 삼켜 버블을 놓친다는 사실이 이 파일 주석에 실측으로 적혀 있다. 백틱 분기는 템플릿 리터럴이 여러 줄이라 그 앵커를 쓸 수 없어 `[^`]*`만 남았는데, 대체 앵커가 없다 — 매치가 **닫는 백틱**에서 시작해 다음 리터럴의 **여는 백틱**에서 끝날 수 있고, 그 사이 코드에 `max-w-[80%]`라는 글자가 있으면(주변 주석이 이미 이 클래스를 논한다) 유령 버블이 하나 잡힌다.
fix_sketch: 백틱 분기를 `className={` 뒤에서만 시작하도록 앵커한다(예: `/className=\{`[^`]*max-w-\[80%\][^`]*`/`) — 캡처 문자열에 접두사가 붙지만 `break-words` 확인에는 영향이 없다. 바꾼 뒤엔 유령 매치를 실제로 만들어 red를 확인한다.
trigger: `messageBubbleWrap.test.ts`를 다음에 건드리는 스토리 착수 시, 또는 채팅 버블이 세 번째 파일로 늘어날 때.
status: open

### DW-710: `AdminSidebar`의 **active 항목만 호버 반응이 없다** — 다섯 항목 중 사용자가 가장 많이 가리키는 하나가 죽은 컨트롤처럼 보인다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 후속 리뷰(edge-case-hunter 렌즈)에서 지적, 두 클래스 상수를 대조해 확인.
location: `web/src/components/layout/AdminSidebar.tsx`(`ACTIVE_LINK_CLASS` vs `LINK_CLASS`)
severity: low — 순전히 시각 피드백 문제이고 기능·접근성 이름에는 영향이 없다.
summary: `LINK_CLASS`에는 `hover:bg-surface-base hover:text-ink-primary`가 있는데 `ACTIVE_LINK_CLASS`에는 hover/focus 변화가 하나도 없다. 현재 보고 있는 화면의 항목에 마우스를 올리면 나머지 네 개와 달리 아무 반응이 없어, 눌리지 않는 컨트롤로 읽힌다.
fix_sketch: `ACTIVE_LINK_CLASS`에 같은 축의 호버(예: `hover:bg-brand-petrol/20`)를 더한다 — 새 토큰 없이 기존 틴트의 농도만 바꾸면 된다. 원본 `SiteNav.tsx`에는 active 개념이 없어 이식할 선례가 없으므로 이 컴포넌트에서 정한다.
trigger: `AdminSidebar.tsx`의 스타일을 다음에 건드리는 스토리 착수 시, 또는 관리자 화면 접근성/시각 감사 시.
status: open

### DW-711: 사이드바 폭 위험 구간(640~1099px)이 **이산점 3개로만 표본화**된다 — 사이드바가 살아 있는 가장 좁은 760~800 경계가 미관측이다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 후속 리뷰(intent-alignment 렌즈)에서 지적, `playwright.config.ts`의 projects와 스펙 Block If를 대조해 확인.
location: `web/playwright.config.ts`(desktop 1280 · tablet 800 · mobile 390) · `web/e2e/viewport-audit.spec.ts`(관리자 스위트)
severity: low — 현재 관리자 화면은 800px에서 실측으로 통과하고, 760~800 구간은 그보다 40px 좁을 뿐이라 여유가 급격히 사라지는 구조가 아니다.
summary: 스펙의 Block If는 "640~1099px **구간**에서 사이드바 240px 때문에 콘텐츠가 안 들어가는가"를 조건으로 걸었는데, 실제 관측은 Playwright 프로젝트가 주는 세 점(1280/800/390)뿐이다. 사이드바는 760px부터 살아나므로 압력이 가장 큰 곳은 760~800 바로 위 구간인데 그 자리를 아무도 안 본다. 구간 조건을 세 점으로 근사한 셈이다.
fix_sketch: 관리자 스위트 안에서 `page.setViewportSize({width: 768, ...})`로 경계 한 점을 추가로 재거나(프로젝트를 늘리지 않고 그 테스트 안에서만), 관리자용 tablet 프로젝트 하나를 768px로 더한다. 어느 쪽이든 그 폭에서 `assertSingleLine`을 함께 건다 — 가로스크롤만으로는 이 구간의 실패 모드(줄바꿈)가 안 보인다.
trigger: 관리자 화면에 요소가 더 붙는 스토리(예: FR61 필터 교체 = Story 15.3) 착수 시 — 행이 무거워지는 순간 이 구간이 먼저 깨진다.
status: open

### DW-712: `hoverContrast.test.ts`에 **백틱 분기가 없다** — 같은 커밋의 `messageBubbleWrap`이 배운 교훈(DW-701)이 나란히 만든 가드에는 안 왔다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 3차 리뷰(edge-case 렌즈)에서 지적, 정규식과 `messageBubbleWrap.test.ts`의 대응 분기를 나란히 읽어 확인.
location: `web/src/app/(user)/chat/__tests__/hoverContrast.test.ts`의 `HOVER_ROW_CLASS`(큰따옴표·작은따옴표 분기만 있음)
severity: low — 지금 스캔 대상 4파일은 전부 따옴표 리터럴이라 실제 누락은 0건이다(실측).
summary: 이 가드는 `"..."`과 `'...'`만 본다. 대상 파일 중 하나가 클래스를 템플릿 리터럴(`` `...${...}` ``)로 바꾸면 스캔이 0건이 되고, 그때 빨개지는 것은 "호버가 죽었다"가 아니라 개수 단언이라 다음 사람이 규칙 대신 가드를 느슨하게 만들도록 유도한다 — DW-701이 `BUBBLE_CLASS`에서 정확히 이 이유로 백틱 분기를 더했는데, 같은 커밋에서 만든 이 형제 가드에는 그 분기가 안 왔다. 실제로 `admin/chats/[roomId]/page.tsx`(한 디렉터리 옆)는 이미 여러 줄 템플릿 리터럴 className을 쓴다.
fix_sketch: `` |`(?=[^`]*\bborder-border-hairline\b)(?=[^`]*\bhover:)[^`]*` `` 분기를 더한다. 다만 DW-709가 지적한 앵커 문제를 같이 안고 가지 않도록, 백틱 분기는 `[^`]*`로 리터럴 경계를 못 넘게 유지하고 여러 줄을 허용할지(`\n` 제외 여부)를 그 시점의 실제 파일 형태를 보고 정한다 — 두 항목을 한 번에 손보는 게 싸다.
trigger: DW-709(`BUBBLE_CLASS` 백틱 앵커)를 손보는 시점 — 같은 기법·같은 함정이라 한 자리에서 같이 정한다. 또는 위 4파일 중 하나가 className을 템플릿 리터럴로 바꿀 때.
status: open

### DW-713: `hoverContrast.test.ts`의 대상이 여전히 **손으로 적은 4파일 목록**이다 — "이 클래스 조합을 쓰는 곳 전부"라고 주석에 써 놓고 구현은 allowlist다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 3차 리뷰(verification-gap 렌즈)에서 지적. 그 렌즈가 이 파일의 정규식을 `web/src/**/*.tsx` 전체에 직접 돌려 대상 밖 2곳을 실측으로 찾아냈다.
location: `web/src/app/(user)/chat/__tests__/hoverContrast.test.ts`의 `describe.each([...])` 4개 URL
severity: low — 가드 밖 2곳(`components/landing/CategoryChips.tsx`, `components/listings/ListingCard.tsx`)은 지금 둘 다 살아 있는 호버 신호를 쓴다(실측). 현재 위반은 0건이다.
summary: 이 가드는 2차 리뷰에서 3파일→4파일로 넓혔고 주석에 "대상 목록을 화면이 아니라 '이 클래스 조합을 쓰는 곳'으로 넓힌다"고 적었는데, 실제 구현은 URL 4개를 손으로 나열한 상태 그대로다. 다섯 번째 화면이 같은 조합을 쓰면 가드가 못 본다 — 그리고 그 일은 이미 한 번 일어났다(DW-696 토큰 치환이 `search/page.tsx`에 죽은 호버를 새로 심었고 3파일 가드가 못 봤다). 같은 실패 모드가 파일 수만 하나 늘어난 채 남아 있다.
fix_sketch: `describe.each`를 손목록이 아니라 `web/src/**/*.tsx` 순회 + 정규식 매치로 만든다(같은 레포의 `src/lib/__tests__/roleLabelFallback.test.ts`가 이미 전역 소스 스캔을 하는 선례다). 정당하게 다른 곳은 이름 붙인 예외 목록에 두면, 그 목록이 곧 남은 부채 목록이 된다 — DW-708(`zinc-*` 실행 가드)과 정확히 같은 모양이라 한 번에 같은 기법으로 처리하는 게 싸다.
trigger: DW-708(`zinc-*` 실행 가드 신설)을 착수하는 시점 — 같은 "손목록 → 전역 스캔 + 예외목록" 전환이라 한 자리에서 함께 만든다.
status: open

### DW-714: 모바일 관리자 패널이 **열린 채로 페이지가 스크롤된다** — 포커스는 갇혀 있는데 갇힌 패널이 화면 밖으로 나갈 수 있다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 3차 리뷰(edge-case 렌즈)에서 지적, `AdminSidebar.tsx`·`FocusTrap.tsx`·`AppHeader.tsx`의 position 조합을 읽어 확인.
location: `web/src/components/layout/AdminSidebar.tsx`(모바일 패널 `absolute inset-x-0 top-full`) · `web/src/components/ui/FocusTrap.tsx`
severity: low — 관리자는 모바일 사용 빈도가 낮고, 패널을 연 채 스크롤하는 것은 의도적 조작에 가깝다. 실사용 재현 보고는 없다.
summary: 패널은 일반 문서 흐름 안의 컨테이너에 `absolute`로 붙어 있고 상단바(`AppHeader`)도 sticky/fixed가 아니다 — 즉 패널이 열려 있어도 페이지 스크롤을 막는 것이 아무것도 없다. 관리자 목록 화면은 길게 스크롤되는데, 스크롤로 패널이 화면 밖으로 나가면 `FocusTrap`의 `focusin` 재포착은 계속 포커스를 그 안으로 끌어당기고 `role="dialog" aria-modal="true"`는 보조기술에 "나머지 페이지는 없는 것"이라고 말한다 — 보이지 않는 곳에 갇힌다. 원본 `SiteNav.tsx`에서 그대로 이식된 구조라 DW-705·706과 같은 계열이지만 축이 다르다(포커스 복귀가 아니라 스크롤).
fix_sketch: 패널이 열려 있는 동안 `document.body.style.overflow = 'hidden'`으로 스크롤을 잠그고 닫힐 때 되돌리거나, 패널을 `fixed`로 띄운다. 어느 쪽이든 `SiteNav.tsx`와 `AdminSidebar.tsx`가 같은 결정을 공유해야 하므로(둘은 같은 패턴) 한쪽만 고치지 않는다 — 이 시점이 DW-705·706과 함께 "이식된 FocusTrap 패널 패턴"을 한 번에 정리할 자리다.
trigger: DW-705 또는 DW-706(같은 패널 패턴의 포커스 결함)을 착수하는 시점 — 세 건 다 같은 두 컴포넌트의 같은 패널을 건드린다.
status: open

### DW-715: I/O 매트릭스가 지목한 라우트(`/admin/listings/[id]` @390)의 **"두 줄 안 됨"을 아무도 재지 않는다** — 단일행 단언은 다른 화면(회원관리)에만 걸려 있다
source_spec: `spec-15-2-관리자-반응형.md`
origin: 2026-08-06 spec-15-2 3차 리뷰(intent-alignment 렌즈)에서 지적. 스펙의 I/O 매트릭스 4행과 `viewport-audit.spec.ts` 관리자 스위트의 단언 배치를 대조해 확인.
location: `web/e2e/viewport-audit.spec.ts`의 관리자 스위트(상세 2경로에는 `assertNoHorizontalOverflow`만 있음)
severity: low — 관리자 상세 2화면은 현재 단일 열 정보 나열이라 접힐 가로 배치 자체가 거의 없다. 3차 리뷰에서 3뷰포트 실행 결과도 green이다.
summary: 스펙의 I/O 매트릭스 4행은 `/admin/listings/[id]` @390에서 "가로스크롤 없음 **+ 라벨·뱃지 두 줄 안 됨"**을 기대한다고 적었는데, 실제로 추가된 단일행 단언(`assertSingleLine`)은 `/admin/members` 행에만 걸렸다. 즉 매트릭스가 지목한 라우트의 후반부 기대는 관측되지 않는다. 3차 리뷰가 회원관리 쪽 단언의 대상(라벨 span → 행 자체)과 표본(본인 행 → 액션 있는 행)을 바로잡았지만, 그 수정은 이 라우트까지 넓히지는 않았다 — 어떤 요소를 재야 의미가 있는지는 그 화면의 실제 구조를 보고 정해야 하기 때문이다.
fix_sketch: `/admin/listings/[id]`에서 실제로 가로 배치인 줄(예: 매물 메타 줄·상태 배지 묶음)에 `data-testid`를 붙이고 그 요소에 `assertSingleLine`을 건다 — 소비자 상세(`/listings/[id]`)가 `[data-testid="inquiry-cta"]`로 이미 쓰는 것과 같은 방식이다. 붙일 만한 가로 배치가 정말 없으면 그 사실을 주석으로 남겨 "안 재는 이유"를 기록한다(측정 없이 넘기지 않는다).
trigger: 관리자 상세 화면에 가로 배치 요소가 추가되는 스토리 착수 시(예: FR61 필터 교체 = Story 15.3, 또는 관리자 상세에 배지·액션이 붙는 변경) — 지금은 잴 대상이 사실상 없다는 것이 미측정의 이유이므로, 대상이 생기는 순간이 볼 시점이다.
status: open

### DW-716: Follow-up review still recommended for 15-2-관리자-반응형 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-15-2-관리자-반응형.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260806-184136-ee73; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-717: DW-669(정지 회원 매물 쓰기 차단)는 Epic 15의 명시적 UI-only 제약과 충돌한다 — RLS 구현은 되돌려졌고 별도 스토리가 필요하다
source_spec: `spec-15-3-회원관리-역할통합-반영.md`
origin: 2026-08-07 Story 15-3 dev-auto 실행 중 오케스트레이터가 리뷰 단계에서 직접 계획 문서 재대조로 발견(4개 리뷰 렌즈는 이 문맥이 없어 못 잡음).
location: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:1242-1312`(Epic 15 "UI-only" 선언 + Story 15.3/15.4 인수조건) · [[DW-669]](정지 게이트 원본 항목, `deferred-work.md`) · `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`(되돌린 코드 전문 저장)
severity: medium
summary: DW-669는 "Epic 15 Story 15-3을 착수할 때 정지가 실제로 무엇을 막는지 그 자리에서 정한다"고 트리거를 지정했는데, epics-increment.md의 Epic 15 선언은 "UI-only, 신규 기능·운영 배관 없음"이고 **DB 변경 예외는 Story 15.4 하나뿐**이라고 명시한다(15.4에만 "이 에픽의 UI-only 범위를 한 칸 넘는 스토리다" 경고가 붙어 있다). Story 15.3의 인수조건 원문에도 DB/RLS 언급이 없다 — "정지/삭제(FR22)가 유지된다"는 기존 UI 액션이 안 깨진다는 뜻이지 새 강제력을 얻는다는 뜻이 아니다. DW-669는 이 선언을 모르거나 반영하지 않은 채 작성됐다(작성일 2026-08-06이 epics-increment.md보다 훨씬 나중인데도 교차 확인이 안 됨).
evidence: `grep -n "Story 15.4" epics-increment-2026-07-12.md` → 1311행 "⚠️ 이 에픽의 'UI-only' 범위를 한 칸 넘는 스토리다 — 마이그레이션 1개(복구 전용 RPC)가 필요하다"가 15.4에만 붙어 있고 15.3 블록(1296-1307행)엔 그런 경고가 없음을 직접 대조 확인. dev-auto 세션이 이미 `supabase/migrations/0030_listings_suspend_gate.sql`(정지 회원 listings INSERT/UPDATE/DELETE 차단)을 짜서 vitest 336/336·playwright 73/73·red/green 자체검증까지 전부 통과시켰으나, 위 충돌을 뒤늦게 발견하고 코드를 되돌렸다(같은 세션이 직접 `git checkout`으로 원복 + 마이그레이션 파일 삭제 + 로컬 DB `supabase db reset`으로 재동기화 확인).
why_it_matters: 되돌리지 않았다면 Epic 15의 스코프 정본(계획 문서)과 실제 배포 코드가 조용히 어긋난 채 넘어갈 뻔했다 — 다음 사람이 "Epic 15는 DB를 안 건드린다"고 믿고 그 가정 위에서 판단하면 틀린다. 또한 이번 코드리뷰(adversarial 렌즈)가 그 RLS 구현 자체의 실측 결함 2건도 찾았다: **관리자용 `listings_delete_admin`은 안 막힘**(정지된 관리자가 여전히 남의 매물 삭제 가능, 로컬 DB 실측 DELETE 성공) · **`listing_images`/`storage.objects` 쓰기 정책도 안 막힘**(정지된 판매자가 여전히 사진 추가·삭제 가능, 로컬 DB 실측 INSERT/DELETE 성공). 재구현할 스토리는 이 두 갭도 함께 닫아야 DW-669의 원래 문제("정지가 실제로 무엇을 막는지")가 온전히 해소된다.
trigger: ✅ **결정됨 (2026-08-07, 사용자) = (b)안 — Epic 15 밖 독립 스토리로 분리.** 신설 `epic-17: 접근 제어 마무리`의 `17-1-정지-회원-쓰기-차단-rls`가 이 항목을 소유한다(`sprint-status.yaml`). (a)안(에픽 15에 예외를 하나 더 추가)을 택하지 않은 이유: Epic 15의 "UI-only"는 예외가 15.4 하나뿐일 때만 제약으로 기능한다 — 두 번째 예외를 뚫는 순간 다음 사람이 "이 에픽은 DB를 안 건드린다"는 가정을 못 쓰게 된다. 재구현 시 아래 두 갭을 범위에 포함할지 그 자리에서 판단할 것. 어느 쪽이든 저장된 패치 파일(`bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`)을 출발점으로 재사용하고, 위 두 갭(admin delete·사진 경로)을 범위에 포함할지 그 자리에서 판단한다.
status: open

### DW-718: 관리자 쓰기 액션(삭제·정지·되돌리기)에 감사 로그(누가·언제)가 전혀 없다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 dev-auto 실행 중 코드리뷰(adversarial 렌즈, 3회 독립 실행 중 2회가 동일 지적) — 2026-08-07.
location: `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx`(삭제·되돌리기) · `web/src/app/(admin)/admin/members/MemberActions.tsx`(정지/해제·삭제) — 관리자 쓰기 액션 전부.
severity: low
summary: `admin_restore_sold_listing` RPC(0030)는 `status`만 바꿀 뿐 누가·언제 되돌렸는지 남기는 로그/컬럼이 없다. 다만 이건 이 스토리가 새로 만든 결함이 아니라 기존 관리자 쓰기 액션(삭제·정지/해제) 전부가 처음부터 공유해 온 패턴이다.
evidence: `MemberActions.tsx`(정지/해제·회원삭제)·`ListingAdminActions.tsx`(매물삭제)를 직접 읽어 확인 — 세 액션 모두 `updated_at` 트리거 갱신 외엔 행위자·시각을 남기는 곳이 없다. 스펙의 "추적 가능" AC(원 epics 문서 Story 15.4)는 런북 문서 대체만 요구했고 실제로 그렇게 구현·검증됨(spec AC7) — 감사 로그는 그 AC의 범위가 아니었다.
why_it_matters: 관리자가 이미 완료된 거래를 되돌리는 것처럼 파급력 있는 조작인데, 사후에 "누가 왜 그랬는지" DB만으로 재구성할 방법이 없다. 데모 단계라 지금은 무해하지만, 실사용자 운영 단계에서는 분쟁·오조작 조사에 필요해진다.
trigger: 관리자 기능이 데모를 벗어나 실사용자 운영에 투입되는 시점 · 또는 관리자 액션 관련 분쟁·오조작이 실제로 발생하는 시점. 그때 이 3개 액션(삭제·정지/해제·되돌리기)을 한 스토리로 묶어 최소 감사 로그(actor_id·action·target·occurred_at)를 설계할 것.
status: open

### DW-719: 관리자 되돌리기 RPC의 "동시(concurrent) 다중 세션" 레이스가 테스트로 검증되지 않음

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 dev-auto 실행 중 코드리뷰(adversarial 렌즈) — 2026-08-07.
location: `api/tests/integration/test_restore_sold_listing_rpc_real_db.py::test_idempotent_on_already_on_sale_row`
severity: low
summary: 멱등성 테스트는 같은 커서로 **순차** 두 번 호출해 확인할 뿐, 두 관리자 세션이 **동시에** 같은 sold 매물을 되돌리는 실제 레이스는 어떤 테스트로도 실행되지 않는다. `0030` 함수 주석은 "레이스 조건에서만 발생"이라고 단언하지만 그 주장 자체가 실측되지 않았다.
evidence: 파일 전체를 읽어 `_call_rpc`가 단일 커서·단일 트랜잭션으로만 호출되는 것을 확인 — 두 개의 별도 DB 커넥션으로 동시 실행하는 테스트가 없다.
why_it_matters: WHERE 절(`status='sold' and public.is_admin()`)이 Postgres MVCC 하에서 실제로 두 동시 UPDATE 중 하나만 행을 잡고 다른 하나는 0행으로 떨어지는지는 이론상 타당하지만(단일 행 UPDATE는 원자적) 이 프로젝트의 다른 실DB 테스트(0020·0025 포함)도 전부 이 축을 검증하지 않는 동일한 패턴이라, 이 스토리만의 결함이 아니라 테스트 스위트 전반의 체계적 공백이다.
trigger: 실DB 통합테스트에 동시성(진짜 병렬 커넥션) 검증 패턴이 처음 도입되는 스토리 — 그때 이 파일도 함께 보강.
status: open

### DW-720: 실DB 통합테스트의 `auth.users` 최소 컬럼 직접 INSERT 패턴이 여러 파일에 중복돼 있다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 dev-auto 실행 중 코드리뷰(adversarial 렌즈) — 2026-08-07.
location: `api/tests/integration/test_view_count_rpc_real_db.py::_create_seller` · `test_restore_sold_listing_rpc_real_db.py::_create_user` (그 외 0025 계열 파일도 동일 패턴 추정, 전수 확인은 안 함).
severity: low
summary: 여러 실DB 테스트 파일이 각자 `insert into auth.users (id, email, raw_user_meta_data) values (...)`로 Supabase Auth 테이블에 최소 컬럼만 직접 꽂는 동일한 패턴을 복붙해 갖고 있다. Supabase/Postgres 이미지가 `auth.users`에 새 NOT NULL 제약을 추가하면 이 패턴을 쓰는 모든 파일이 동시에, 각자 다른 위치에서 불투명한 insert 에러로 깨진다.
evidence: 두 파일을 직접 비교 — 두 `_create_*` 헬퍼가 사실상 동일한 코드(컬럼 3개, 동일 형태의 raw_user_meta_data)를 각자 유지한다.
why_it_matters: 근본 원인이 한 곳(Supabase 이미지 스키마)인데 증상은 파일마다 따로 나타나 디버깅 시간이 커진다 — 공유 헬퍼로 추출하면 한 곳만 고치면 된다.
trigger: 이런 실DB 테스트 파일이 하나 더 생기는 시점(3번째 복붙이 생기기 전) — 그때 `api/tests/integration/conftest.py` 등 공유 위치로 추출.
status: open

### DW-721: `is_admin()`이 `profiles.status`를 안 봐서 **정지된 관리자**도 되돌리기 RPC를 쓸 수 있다 — Epic 17의 RLS 범위로는 이 경로가 안 덮인다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 후속 코드리뷰(adversarial·edge-case-hunter 두 렌즈가 독립적으로 지적) — 2026-08-07.
location: `supabase/migrations/0001_profiles.sql:57-68`(`is_admin()`) × `supabase/migrations/0030_listings_restore_sold_rpc.sql:29` × 신설 스토리 `17-1-정지-회원-쓰기-차단-rls`.
severity: low
summary: `is_admin()`은 `profiles.role='admin'`만 보고 `profiles.status`(`active`/`suspended`)는 보지 않는다. 그래서 관리자 회원 관리에서 **정지된 계정도** `admin_restore_sold_listing`을 호출해 완료된 거래를 되돌릴 수 있다. 게다가 이 RPC는 `SECURITY DEFINER`라 RLS를 우회하므로, DW-669를 이어받은 Epic 17 스토리 `17-1-정지-회원-쓰기-차단-rls`가 **RLS 범위로 설계돼 있으면 이 새 경로는 닫히지 않는다.**
evidence: 실측(2026-08-07, 로컬 Supabase 55322) — `profiles.status='suspended'`인 관리자를 만들고 `set local role authenticated` + JWT sub 임퍼소네이션으로 sold 매물에 RPC를 호출한 결과 `rows=1`, `status`가 `on_sale`로 실제로 바뀌었다(트랜잭션 롤백). `is_admin()` 정의를 직접 읽어 `status` 술어가 없음을 확인.
why_it_matters: 17-1이 "정지 = 쓰기 차단"을 RLS로만 구현하고 끝나면, 팀 전체가 정지 게이트가 완성됐다고 믿는 상태에서 이 경로만 조용히 열려 있게 된다 — DW-669가 원래 잡으려던 문제("정지가 실제로 무엇을 막는가")가 반만 해소된다. 또한 이 축은 15.4의 인수조건 밖이었다(스펙 Never 절이 정지 게이트를 명시적으로 범위 밖으로 뒀다) — 그래서 15.4의 결함이 아니라 17-1이 반드시 흡수해야 할 범위다.
trigger: `17-1-정지-회원-쓰기-차단-rls` 착수 시 — 그 스토리의 인수조건에 **"SECURITY DEFINER RPC 경로(`admin_restore_sold_listing` 포함)도 정지 계정에서 차단된다"**를 반드시 포함할 것(CLAUDE.md B5 — 회고 약속은 다음 스토리의 체크박스로 심는다). 구현 후보: `is_admin()`에 `and status = 'active'` 추가(전역 파급 — 관리자 SELECT 정책까지 함께 좁아지므로 그 영향을 먼저 실측할 것) 또는 RPC 쪽에만 `status='active'` 조건 추가.
status: open

### DW-722: `supabase db reset`로 만든 로컬 스택엔 플랫폼 기본 테이블 GRANT가 없어 로그인 사용자용 앱이 통째로 안 뜬다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 후속 코드리뷰의 검증 단계에서 실측으로 드러남(스펙이 지시한 `supabase db reset` 실행 직후) — 2026-08-07.
location: `scripts/migration-check-prelude.sql:63`(CI만 갖는 재현) × `supabase/migrations/**`(어떤 마이그도 `authenticated`에 테이블 GRANT를 주지 않음) × `supabase/config.toml`.
severity: low
summary: 리포의 마이그레이션은 `anon`·`authenticated`의 테이블 권한을 **Supabase 플랫폼 기본 GRANT**(`alter default privileges in schema public grant all on tables to anon, authenticated`)에 위임한다(0012·0020 주석이 명시). CI는 그걸 `migration-check-prelude.sql`로 재현하고, 원격은 플랫폼이 준다. 그런데 **로컬 `supabase db reset`(CLI 2.111.0)은 재현하지 않는다** — 리셋 직후 `authenticated`에 `listings` SELECT 권한이 아예 없어, 로그인한 사용자가 어떤 화면도 못 연다.
evidence: 실측(2026-08-07). ① 리셋 직후 `has_table_privilege('authenticated','public.listings','SELECT')` = **f**. ② `set local role authenticated`로 조회 시 `permission denied for table listings` + `HINT: GRANT SELECT ON public.listings TO authenticated`. ③ `pg_default_acl`의 `(postgres, public, tables)` 항목이 anon·authenticated에 `Dxtm`(TRUNCATE/REFERENCES/TRIGGER/MAINTAIN)만 주고 `arwd`를 안 준다. ④ 그 상태에서 E2E `write-flows.spec.ts`는 E1의 `login()` 단계에서 즉시 실패한다. ⑤ 기존 실DB 테스트 `test_view_count_rpc_real_db.py`의 `test_authenticated_can_still_update_other_columns`·`test_ordinary_update_bumps_updated_at` 2건도 같은 이유로 로컬에서만 실패한다(CI 동일 컨테이너에서는 116건 전부 통과 — 즉 코드 결함이 아니라 환경 축이다).
why_it_matters: `docs/conventions.md` §9.1이 세운 불변식은 "레포 파일만으로 (Supabase 위에서) DB가 선다"인데, 지금은 **CI에서만 참이고 로컬에서는 거짓**이다. 다음 사람이 리셋 후 앱이 안 뜨는 것을 보면 원인이 GRANT라는 것을 알 길이 없고(권한 오류는 화면에 "매물을 불러오지 못했습니다"로만 보인다), 이번 실행에서도 실제로 시간을 잃었다. 임시 복구법: `alter default privileges in schema public grant all on tables to anon, authenticated, service_role;` + `grant all on all tables in schema public to ...` 실행 후 `0011`·`0012`·`0020`의 좁히는 GRANT 블록을 다시 적용(그래야 anon 컬럼 스코프·view_count 차단이 되살아난다).
trigger: 다음에 로컬 `supabase db reset`을 쓰는 작업 — 그때 `scripts/seed-local.sh`가 시드 전에 이 기준선 GRANT를 함께 세우도록 넣거나(가장 싼 자리), `supabase/config.toml`의 리셋 훅으로 프렐류드 일부를 걸 것. **주의: `migration-check-prelude.sql`을 로컬 Supabase 스택에 통째로 실행하면 안 된다** — 그 파일은 맨 pgvector용이라 `auth.uid()` 스텁 등을 만들어 실제 auth를 덮어쓴다.
status: open

### DW-723: 관리자 회원 액션(`MemberActions.tsx`)에 삭제·정지 공유 busy 가드가 없다 — 15.4가 매물 쪽에서 고친 그 결함이 본보기 파일에 그대로 남았다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 3차 코드리뷰(adversarial 렌즈) — 2026-08-07.
location: `web/src/app/(admin)/admin/members/MemberActions.tsx`(정지/해제 버튼 · 삭제 버튼) ↔ 이미 고쳐진 대조군 `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx:147,159,171`.
severity: low
summary: `MemberActions.tsx`는 정지/해제와 삭제가 각자 자기 `loading` 상태만 보고 서로를 잠그지 않는다 — 한쪽이 진행 중일 때 다른 쪽을 눌러 같은 회원에 두 요청을 동시에 보낼 수 있다. Story 15.4 1차 코드리뷰가 `ListingAdminActions.tsx`에서 정확히 같은 결함을 찾아 `busy = deleting || restoring` 공유 가드로 고쳤는데, 그 패턴의 **본보기였던 파일**은 안 고쳐졌다.
evidence: 두 파일을 직접 대조 — `ListingAdminActions.tsx`는 두 버튼 모두 `disabled={busy}`를 갖고 두 핸들러가 `if (deleting || restoring) return`으로 시작한다. `MemberActions.tsx`는 각 핸들러가 자기 상태만 보고(`if (toggling) return` / `if (deleting) return`), 버튼에 `disabled`를 넘기지 않아 `Button`의 `disabled={disabled || loading}`가 자기 `loading`만 반영한다.
why_it_matters: 15.4의 결함이 아니라 15.4가 **드러낸** 기존 결함이다(범위 밖이라 이 스토리에서 고치지 않는다). 다만 CLAUDE.md B8이 말하는 "미루는 판단은 틀린 게 아니고 안 적는 게 틀린 것"에 해당한다 — 팀이 이 결함을 이미 진단했다는 사실이 어디에도 기록돼 있지 않으면, 다음 사람이 매물 쪽 `busy` 가드를 보고 "회원 쪽엔 왜 없지?"를 처음부터 다시 조사하게 된다. 실사용 영향은 낮다(관리자 1인 조작, 결과는 중복 요청 1건).
trigger: 관리자 회원 관리 화면을 다음에 손대는 스토리 — Epic 17의 정지 게이트 작업(`17-1-정지-회원-쓰기-차단-rls`)이 이 파일을 열 가능성이 높다. 그때 `busy = toggling || deleting` 공유 가드를 두 버튼과 두 핸들러 양쪽에 넣을 것.
status: open

### DW-724: `is_admin()`이 `set search_path = public`이라, 이 함수를 유일한 인가 관문으로 쓰는 SECURITY DEFINER RPC들의 하드닝이 한 칸 무르다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 3차 코드리뷰(adversarial 렌즈) — 2026-08-07.
location: `supabase/migrations/0001_profiles.sql`(`public.is_admin()` — `security definer set search_path = public`) ↔ 이를 호출하는 `0030_listings_restore_sold_rpc.sql`·`0005_admin_policies.sql` 등.
severity: low
summary: 리포의 최신 SECURITY DEFINER 함수들은 `set search_path = ''`(빈 문자열 + 전 참조 스키마 수식)로 하드닝하는데(0019·0020·0030), 그 함수들이 인가 판정을 통째로 위임하는 `is_admin()`은 `set search_path = public`이다. 즉 새 함수만 하드닝하고 **자물쇠 자체는 옛 기준**에 남아 있다.
evidence: `0030`은 `set search_path = ''`를 선언하고 본문에서 `public.listings`·`public.is_admin()`으로 전부 수식한다. `0001`의 `is_admin()` 정의를 직접 읽어 `set search_path = public`임을 확인. 신설된 `test_restore_sold_listing_rpc_real_db.py`는 `0030`의 시그니처·GRANT는 구조적으로 단언하지만 `is_admin()`의 `prosecdef`·`proconfig`는 아무것도 보지 않는다.
why_it_matters: 지금 당장 뚫리는 경로를 실측으로 재현하지는 못했다(`public` 고정 자체가 빈 search_path보다 무를 뿐, 임의 스키마 주입은 아니다) — 그래서 이 항목은 "확인된 취약점"이 아니라 **기준 불일치**로 등재한다. 문제는 새 RPC를 추가할 때마다 하드닝 검사를 그 RPC에만 걸고 위임 대상은 아무도 안 보는 습관이 굳는다는 점이다. DW-721(같은 함수의 `status` 미확인)이 그 습관의 비용을 이미 한 번 보여줬다.
trigger: `is_admin()`을 다음에 수정할 때 — 현재 가장 유력한 자리는 DW-721이 지정한 `17-1-정지-회원-쓰기-차단-rls`(거기서 `status='active'` 술어를 넣게 된다). 같은 편집에서 `search_path`를 `''`로 좁히고 본문 참조를 수식할 것. ⚠️ `is_admin()`은 다수 RLS 정책이 부르므로 변경 후 관리자 SELECT/DELETE 경로를 실DB로 회귀 확인해야 한다.
status: open

### DW-725: 관리자 매물 행의 sold 상태(버튼 2개 나란히)가 반응형 자동 검사에 없다 — D5 근거가 1회성 스크린샷뿐이다

source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
origin: Story 15-4 3차 코드리뷰(adversarial 렌즈) — 2026-08-07.
location: `web/e2e/viewport-audit.spec.ts`(관리자 라우트 순회) × `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx:151`(`flex items-center gap-2`, `flex-wrap` 없음).
severity: low
summary: Story 15.4가 관리자 매물 행에 두 번째 버튼("판매완료 되돌리기")을 넣어 그 행이 처음으로 **버튼 2개 가로 배치**가 됐다. D5(반응형 무결성) 확인은 2차 패스가 390px·1280px × 라이트/다크로 **육안 캡처**해 통과시켰지만, 그 상태를 다시 재현하는 자동 검사는 없다 — `viewport-audit.spec.ts`는 관리자 라우트를 열되 `status='sold'` 행이 화면에 있는지를 보장하지 않기 때문이다.
evidence: `viewport-audit.spec.ts`를 읽어 sold 매물을 고정하는 단계가 없음을 확인. `ListingAdminActions.tsx:151`의 컨테이너에 `flex-wrap`이 없어, 폭이 모자라면 접히는 게 아니라 가로 오버플로가 난다(D5는 접힘도 오버플로도 둘 다 금기).
why_it_matters: project-context 규칙13(D5)은 "관리자 화면도 예외 없음 · 레이아웃 어긋남 = 절대 금기"를 governing으로 선언한다. 지금 그 보증은 특정 매물 요약 문자열 하나로 찍은, 아무도 다시 돌릴 수 없는 캡처에 걸려 있다 — 제조사·모델명이 더 긴 매물이 들어오면 잡을 장치가 없다. (E2E 자체가 CI에 배선돼 있지 않다는 더 큰 축은 `docs/tech-debt.md` #168이 이미 갖고 있다.)
trigger: `viewport-audit.spec.ts`를 다음에 손대는 작업, 또는 E2E를 CI에 배선하는 작업(#168) — 그때 sold 매물을 하나 고정해 관리자 목록을 열고 두 버튼의 y좌표 동일 + 행 우측 끝 ≤ 뷰포트 폭을 단언하는 케이스를 추가할 것(2차 패스가 육안으로 잰 바로 그 두 값).
status: open

### DW-726: Follow-up review still recommended for 15-4-관리자-판매완료-되돌리기 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-15-4-관리자-판매완료-되돌리기.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260807-013500-4548; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

### DW-727: E2E `R4`가 **깨끗한 시드에서는 실패하고, 앞선 실행이 DB를 더럽혀야 통과**한다 — 초록이 잘못된 이유로 나온다
origin: 2026-08-07 Epic 15 마감 E2E에서 실패 → 원인 추적. 15-3 세션이 `supabase db reset`으로 로컬 DB를 새로 시드하면서 드러났다(그 전까지는 누적 상태에 가려 계속 초록이었다).
location: `web/e2e/realtime-chat.spec.ts:322`(R4) 및 같은 파일의 cleanup 단언 · 시드 `supabase/seed.sql`·`seed-local/*`
severity: medium
summary: R4 계열의 정리 단언은 *"구매자·판매자 **모두 이미** 이 방의 `chat_room_reads` 행을 갖고 있어 방문해도 새 행이 안 생긴다"*를 전제한다. 그런데 **시드는 `chat_room_reads`를 하나도 만들지 않는다** — 그 행들은 **E2E 실행 자신이** 남긴 것이다. 그래서 갓 시드한 DB에서는 첫 방문이 행을 만들어 `reads` 1→2가 되고 단언이 깨진다.
evidence: 실측 3단계로 확정했다. ①`grep -rn "chat_room_reads" supabase/seed*.sql supabase/seed-local/*.sql` → **0건**(시드가 안 만든다). ②실패 실행의 로그: `baseline={"reads":1} after={"reads":2}`, 그리고 DB 조회 결과 5개 방 중 read 행이 있는 방은 **1개뿐**(그 방만 reads=2). ③**예측 후 재실행으로 검증**: "앞 실행이 행을 남겼으니 이번엔 통과할 것"이라 예측하고 같은 스펙을 다시 돌리자 `baseline={"reads":2} after={"reads":2}`로 **4/4 통과**했다.
why_it_matters: 이 검사는 **실행 순서에 의존**하며, 실패한 실행이 다음 실행을 통과시킨다. 즉 "초록"이 제품이 옳다는 뜻이 아니라 "앞에서 한 번 돌았다"는 뜻이다. CI처럼 매번 깨끗한 DB에서 도는 환경에서는 **항상 빨간불**이 된다(현재 E2E는 CI에 없어서 안 드러났다 — 대장 #182). 그리고 새로 합류한 사람이 `db reset` 후 처음 돌리면 영문 모를 실패를 본다.
fix_sketch: 두 갈래 중 하나. (a) **시드가 참가자 양쪽의 `chat_room_reads` 행을 만들게 한다** — 테스트가 기대하는 "이미 읽은 방" 상태를 시드가 책임진다(권장: 다른 검사들도 같은 전제를 쓸 수 있다). (b) 테스트가 전제를 스스로 만든다 — 방문 전에 양쪽 read 행을 넣고 시작한다. 어느 쪽이든 **`supabase db reset` 직후 한 번에 통과하는지**로 검증할 것(그게 이 결함의 정의다).
trigger: **다음 E2E 전수 실행 직전**(= Epic 16 마감 시점) — DW-689·690·693과 같은 자리에서 함께 본다. CI에 E2E를 올리는 판단(#182·#168)을 하게 되면 **그때는 필수 선행**이다(깨끗한 DB에서 항상 빨갛기 때문).
status: open

### DW-728: Flutter 앱에 **AI FAB이 아직 붙어 있다** — UX 확정(D12)이 폐기하라고 한 바로 그 물건
origin: 2026-08-07 사용자 질문("플로팅 버튼에 내 차 팔기 넣기로 하지 않았나")에서 기획 재확인 중 발견. 같은 확인에서 **웹** 플로팅은 제거했고(아래 `related`), 앱 쪽만 남았다.
location: `app/lib/features/auth/home_screen.dart:49`(`FloatingActionButton.extended`, `key: Key('ai_fab')`, 라벨 "AI 검색") · 테마 정의는 `app/lib/core/theme/app_theme.dart:93`
severity: low
summary: UX 확정 D12는 앱 홈을 **"하단 4탭(홈(AI)·찜·채팅·내차팔기) + FAB 없음"**으로 정하면서, AI를 FAB에 두는 A안을 명시적으로 폐기했다(*"이전 앱의 AI=FAB는 'AI가 부가기능'이던 흔적 → 폐기"*). 그런데 현재 앱 홈에는 그 AI FAB이 그대로 있다.
evidence: `grep -rn 'FloatingActionButton' app/lib/` → `home_screen.dart:49` 1건. 같은 파일 주석이 근거로 **nav-ia-rules R3**를 인용하고 있다 — 웹에서 제거한 것과 **정확히 같은 형태의 어긋남**이다(옛 문서를 근거로 만든 것이 새 확정 뒤에도 남음). 하단 내비는 아직 없다: `grep -rn 'NavigationBar\|BottomNavigationBar' app/lib/` → **0건**.
why_it_matters: 사용자가 *"앱엔 내 차 팔기 플로팅이 있는 것 아니냐"*고 기억할 만큼 이 영역의 문서·구현이 어긋나 있다. 참고로 **"내 차 팔기를 FAB로"는 B안으로 검토됐다가 기각**됐다(근거: *"탭+FAB 내차팔기 중복"* — 하단탭에 내차팔기가 이미 있어서). 즉 앱의 정답은 A안도 B안도 아닌 **FAB 없음**이다.
fix_sketch: ⚠️ **지금 FAB만 떼면 안 된다.** 앱엔 하단탭이 아직 없어서(위 evidence) FAB이 유일한 AI 진입로다 — 떼는 순간 AI 검색에 갈 길이 사라진다. **하단 4탭을 만드는 스토리와 같은 커밋에서 교체**해야 한다("문 먼저, 그다음 정리" — 2026-08-06 웹 14-3→14-2에서 배운 순서 그대로).
trigger: ~~Story 16.1 착수 시~~ → **같은 날(2026-08-07) 사용자 지시로 앞당겨 처리했다.** 아래 resolution 참조.
related: 웹 쪽 같은 어긋남은 2026-08-07에 **해소**했다 — 홈의 플로팅 'AI 검색'을 제거하고, 되살아나면 잡히도록 E2E `B5b`(`web/e2e/nav-and-hero.spec.ts`)를 신설했다(라벨이 아니라 `position:fixed/sticky`로 잡아 다른 이름으로 되살아나도 걸린다. 일부러 다른 라벨로 되살려 red 확인함).
resolution: **2026-08-07 해소.** `ai_fab`을 떼고 D12가 정한 자리 — **홈 최상단 AI 검색부**(`_AiSearchCta`, `Key('go_ai')`) — 로 옮겼다. **떼기만 하지 않은 이유**: 앱엔 하단 4탭이 아직 없어서 FAB이 유일한 AI 진입로였고, 그것만 제거하면 AI 검색에 갈 길이 사라진다(웹 14-3→14-2에서 배운 "문 먼저, 그다음 정리"). D12 원문도 *"AI 검색 = FAB **아님**. 홈 최상단 큰 검색부"* 로 **옮기라**고 했지 없애라고 한 게 아니다.
  · 검사: `app/test/home_ai_entry_test.dart` 신설(2건) — ①FAB 부재(옛 `ai_fab` 키 포함) ②AI 진입 존재 **+ 매물 탐색 CTA보다 위**(있기만 하면 통과시키면 맨 아래로 밀려도 초록이라 순서까지 고정). **red 확인**: FAB을 되살리고 AI를 아래로 민 상태에서 2건 모두 실패(`Found 1 widget with type "FloatingActionButton"` / `Expected: a value less than <139.0> Actual: <197.0>`) → 원복 후 green.
  · 실기기 확인(갤럭시 S21, 무선 디버깅): FAB 없음 · AI 검색부가 최상단 · **눌러서 AI 화면 도달**까지 확인했다(위젯 테스트가 못 보는 축 — push 이후는 세션이 필요해 테스트에서 안 본다).
  · **남은 것은 16.1 본연의 범위**이지 이월 항목이 아니다: 하단 4탭(홈(AI)·찜·채팅·내차팔기)과 웹 petrol 히어로 밴드 토큰 미러링. 그래서 이 항목은 닫는다 — 16.1 인수조건이 이미 둘 다 명시하고 있다.
  · `app_theme.dart:93`의 `floatingActionButtonTheme`은 **그대로 뒀다**(이제 쓰는 화면이 없다). 지우지 않은 이유는 그 파일 전체가 16.1의 토큰 미러링 대상이라, 지금 손대면 그 스토리와 충돌하기 때문이다. **지우라는 뜻이 아니라 16.1이 볼 것**으로 남긴다.
status: resolved

### DW-729: 앱의 색 토큰 17종이 **웹 팔레트의 사본인데 어긋나도 아무도 모른다** — 대조 검사도, 정본 절도 없다
origin: 2026-08-07 Story 16.1(디자인 토큰 미러 + 하단 4탭) 3회차 리뷰. 4개 리뷰 렌즈 중 2개(adversarial·verification-gap)가 독립적으로 같은 자리를 지목했다.
location: `app/lib/core/theme/app_theme.dart`의 `AppColors`(17종) ↔ `web/src/app/globals.css`의 `:root` 라이트 값 · 비어 있는 자리 = `docs/conventions.md`(색 토큰 절 없음)
severity: low
summary: 16.1이 웹 라이트 팔레트(petrol/amber/trust-green 등) hex를 앱에 그대로 옮겨 적었다. **지금 값은 17/17 정확히 일치한다**(이번 리뷰가 직접 대조 확인) — 즉 **틀린 게 아니라 고정돼 있지 않은 것**이다. 웹이 토큰 하나를 조정하면 앱만 옛 hex에 남고 CI는 계속 초록이다.
evidence: `grep -rn '1E6E6A|F0A339' --include=*.dart --include=*.ts --include=*.yml`(node_modules·build 제외) → `app_theme.dart` 정의부 2건뿐, 테스트·린트 참조 **0건**. `grep -niE 'petrol|amber|trust-green' docs/conventions.md` → **0건**(16.1이 추가한 §14는 role 어휘만 다룬다). 반면 `_bmad-output/implementation-artifacts/epic-16-context.md:60`은 *"시각 토큰의 원본은 웹 DESIGN.md이며 계약 형태로 `docs/conventions.md`에 이월된다"*고 이미 적어놨다 — 그 이월이 안 됐다.
why_it_matters: 이 리포가 **이미 겪은 실패 모드**다 — `_bmad-output/project-context.md:26`이 *"요약이 원본보다 늙어 틀린 값이 에이전트에 주입됐다 — 3건 실측"*으로 기록하고 있고, 그래서 "값은 한쪽에만 산다"를 규칙으로 세웠다. 색 토큰은 그 규칙 밖에 있는 네 번째 사본이다. 게다가 16.2(이미지·카드)·16.3(신뢰속성)이 이 토큰 위에 카드와 뱃지를 그리므로 어긋남이 누적된다.
fix_sketch: 둘 중 하나. (a) `docs/conventions.md`에 색 토큰 절을 신설해 정본을 한 곳에 두고 `app_theme.dart`·`globals.css`가 그 절을 인용하게 한다(§14 role 절을 만든 것과 같은 방식, epic-16-context가 원래 그러기로 적은 것). (b) **실행되는 검사로 못박는다**(CLAUDE.md B9) — `globals.css`의 `:root` 블록을 파싱해 hex를 뽑고 `AppColors`와 대조하는 테스트를 app 잡에 건다. 사람 눈 diff 대조는 계약이 아니다. **채택 전 red 확인**: 앱 hex 한 개를 일부러 틀리게 바꿔 검사가 실제로 잡는지 본다.
scope_note: 16.1의 intent-contract가 요구한 것은 **1회 전사**("라이트 값만 hex 그대로 옮긴다")이지 드리프트 가드가 아니다. 그래서 그 스토리에서 하지 않았고, 여기 적는다.
trigger: **Story 16.2 착수 시**(그 스토리가 이 토큰 위에 카드를 그리므로 가장 먼저 사본이 늙는 자리다). 늦어도 Epic 16 마감 전.
status: done 2026-08-07
resolution: **2026-08-07 Story 16.2가 해소.** fix_sketch (b)를 채택했다(conventions.md에 색 절을 신설하는 (a)는 이 프로젝트가 이미 겪은 "사본이 원본보다 늙는" 실패를 반복하므로 기각 — spec-16-2 Design Notes 근거). `app/test/app_theme_color_drift_test.dart`(신규)가 `web/src/app/globals.css`의 `:root` 라이트 블록 + `@theme static`의 `--color-accent-amber`를 상대경로로 직접 읽어 `AppColors` 17종과 hex 문자열로 대조한다(사본을 늘리지 않고 정본을 직접 읽음 — 파일을 못 읽는 샌드박스에서만 리터럴 폴백 사용). **채택 전 실측**: `AppColors.brandPetrol`을 `#1E6E6A`→`#1E6E6B`로 한 글자 틀리게 바꿔 `flutter test`가 red가 되는 것을 확인했고, 원복해 green(18/18 case: 17종 대조 + 개수 단언)임을 재확인했다.

### DW-730: 앱 전반에 **Material 기본색 리터럴 29곳**이 남아 있고, 토큰 사용을 강제하는 검사가 없다
origin: 2026-08-07 Story 16.1(디자인 토큰 미러 + 하단 4탭) 4회차(후속) 리뷰. adversarial 렌즈가 지목, 리뷰 세션이 직접 세어 확인.
location: `app/lib/**` 전반 — 예: `sell_screen.dart`의 안내문 `Colors.grey`, `ai_chat_screen.dart:125,142`, `chat_list_screen.dart`의 에러/빈상태 아이콘 `Colors.red`·`Colors.grey`, `listing_card.dart` 등
severity: low
summary: 16.1은 `AppColors` 17종을 웹 팔레트에서 미러링하고 "**새** 하드코딩 색 금지"를 규칙으로 세웠다. 그 규칙은 **이번 변경이 새로 도입하는 색**만 막았고(실제로 `onPetrol`·`onPetrolMuted` 토큰 신설로 3곳을 걷어냈다), **선재하던 리터럴 29곳은 그대로**다. 그리고 이 규칙을 실행하는 검사가 없다 — 주석과 스펙 문장뿐이다.
evidence: `grep -rnE 'Colors\.(grey|red|green|white|black|blue|orange|amber)' app/lib --include=*.dart | wc -l` → **29**. `flutter analyze` → 0 issues(이 규칙을 보는 lint 없음). `grep -rn 'AppColors' app/test` → 색 토큰 사용을 강제하는 단언 0건.
why_it_matters: 16.2(카드·이미지)·16.3(신뢰속성 뱃지)이 이 팔레트 위에 화면을 그린다. 의미 토큰과 Material 기본색이 섞인 채로 카드를 다시 그리면 "petrol 계열인데 회색만 튀는" 어긋남이 화면 단위로 굳는다. 또 [[DW-729]]가 제안한 드리프트 대조 검사도 **무엇을 검사 대상으로 볼지**가 정해져 있지 않으면 범위를 못 정한다.
fix_sketch: (a) 리터럴을 의미 토큰으로 옮긴다(`Colors.grey`→`AppColors.inkMuted`, `Colors.red`→`AppColors.danger` 등 — 자리마다 역할을 보고 매핑한다. 일괄 치환 금지: 16.1 Design Notes "색 토큰 분리 지침"이 같은 이유로 사이트별 판단을 요구했다). (b) 규칙을 **실행되는 검사로** 바꾼다(CLAUDE.md B9) — `app_theme.dart` 밖에서 `Colors.<이름>`을 쓰면 실패하는 테스트/lint. **채택 전 red 확인**: 리터럴 하나를 되살려 검사가 잡는지 본다.
scope_note: 16.1의 intent-contract가 요구한 것은 라이트 팔레트 **전사**와 새 하드코딩 금지이지 기존 코드 전면 토큰화가 아니다. 이번 변경이 만든 결함도 아니다(선재) — 그래서 이 스토리에서 하지 않고 여기 적는다.
trigger: **Story 16.2 착수 시** — [[DW-729]]와 같은 자리에서 함께 본다(둘 다 색 토큰의 정본·강제 문제이고, 16.2가 카드를 다시 그리며 이 코드를 직접 만진다).
progress: **2026-08-07 Story 16.2가 이 스토리가 실제로 만지는 2개 파일 범위로 부분 해소.** spec-16-2 Boundaries가 범위를 "listing_card.dart·listing_detail_screen.dart 한정"으로 명시했다(A2/A3 — 무관한 chat/auth/sell 화면을 건드리지 않는다). `listing_card.dart`의 `Color(0xFFA1A1AA)`(옛 zinc 팔레트 잔재, 이 grep 패턴엔 안 걸리지만 같은 결함) → `AppColors.inkMuted`, `listing_detail_screen.dart`의 6곳(`Colors.red`·`Colors.grey`·`Colors.green[100]`·`Colors.green[800]`·`Colors.grey[600]`×2) → `AppColors.danger`/`inkMuted`/`trustGreenBg`/`trustGreenInk`로 역할별 매핑했다. 재실측: `grep -rnE 'Colors\.(grey|red|green|white|black|blue|orange|amber)' app/lib --include=*.dart | wc -l` → **25**(29 - 이번에 고친 6 + 아래 신규 2). ⚠️ **새로 생긴 2곳**: `app/lib/features/listings/listing_photo_widgets.dart`(신규 파일)의 "N장"/"k/N" 배지 pill이 `Colors.black`/`Colors.white`를 쓴다 — 이건 이 항목이 말하는 "토큰화 누락"이 아니라 web `bg-black text-white`와 똑같이 **의도적으로 스왑 안 되는 고정 상수**다(배지는 사진 밝기와 무관하게 항상 불투명 검정이어야 하고, 앱은 라이트 고정이라 다크 스왑 자체가 없다 — AppColors에 넣어도 값이 안 바뀌므로 굳이 이원화하지 않았다). 남은 23곳(chat/auth/sell/main.dart/app_theme.dart 등)은 여전히 미해소 — fix_sketch (a)(리터럴→의미 토큰 매핑)·(b)(실행되는 검사)는 그대로 유효하다.
trigger(잔여 23곳): 그 화면들을 실제로 손대는 다음 스토리 착수 시(Epic 16.3~16.5 후보 — 16.3이 chat 근처를 만지면 그 자리에서 함께 본다). 그전에 규모가 더 늘면(새 화면이 `Colors.*`를 계속 새로 쓰면) 늦어도 Epic 16 마감 전에 별도로 본다.
status: open

### DW-731: Follow-up review still recommended for 16-1-디자인-토큰-미러-하단-4탭-내비 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-16-1-디자인-토큰-미러-하단-4탭-내비.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260807-162721-25ed; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: `epics-increment-2026-07-12.md`의 Story 16.2 AC 원문이 여전히 "앱은 서명 원본 이미지를 Storage에서 받아 렌더한다(api는 storage_path만 반환하므로 앱이 서명)"이라고 적혀 있어, Story 9.0(공개 버킷 전환, `0014_listing_images_public_bucket.sql`)으로 이미 낡은 "서명" 표현이 정정 없이 남아 있다.
  evidence: 같은 문서의 Epic 9 AC 줄들(467·498·574행)은 Story 9.0 반영 시점에 "✎ 정정(2026-07-19/20)" 주석이 소급으로 붙어 있는데, 16.2 AC 블록만 그 정정 패스에서 빠졌다. 이번 스토리는 스펙 Design Notes에 정정 근거(conventions.md §10, migration 0014)를 남기고 "공개 URL"로 바로잡아 진행했지만, 그 정정은 이번에 새로 쓴 스펙 문서에만 있고 원본 계획 문서(`epics-increment-2026-07-12.md`)에는 반영되지 않았다 — 다음 사람이 원본만 보면 다시 "서명"으로 오해할 수 있다.
  trigger: `epics-increment-2026-07-12.md`를 다음에 편집할 기회(다른 스토리 추가·수정 등)에 16.2 AC 줄에도 같은 형식의 "✎ 정정" 주석을 소급 부여한다. 그 전에 누군가 16.2 AC를 문자 그대로 읽고 서명 URL을 재도입하려 하면 그때 즉시 바로잡는다.

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: 앱 `fetchListings`가 페이지네이션 없이 `on_sale` 매물 **전량**을 한 번에 가져온다(`app/lib` 전역에 `.range()`/`.limit()` 0건). Story 16.2가 그 목록에 매물당 사진까지 붙이면서 한 화면이 끌고 오는 비용이 커졌다.
  evidence: 16.2 리뷰 중 실측한 로컬 Storage 원본은 **1600×992 · 161KB · `cache-control: no-cache`**다(공개 URL GET으로 직접 확인). 16.2가 `cacheWidth`로 디코드 크기는 셀 크기에 맞췄지만, 전송량과 행 수 자체는 목록이 무한정 자라는 구조 그대로다. 같은 무제한 id 목록이 `listing_images` 배치 조회의 `.inFilter()`에도 그대로 들어가, 매물 수가 커지면 PostgREST 쿼리스트링 길이 한도에 먼저 닿는다(web은 같은 자리에 50개 청크를 둔다). 페이지네이션 부재 자체는 16.2가 만든 게 아니라 그 이전부터 있던 구조이며, 16.2는 그 위에 사진을 얹어 비용만 키웠다.
  trigger: 앱 목록에 페이지네이션·무한스크롤을 넣는 스토리 착수 시(또는 시드/운영 매물이 100건을 넘을 때). 그때 `.range()` 도입과 `_fetchCovers`의 `.inFilter()` 청크(web `COVER_IMAGES_CHUNK_SIZE=50` 미러)를 **같이** 넣는다 — 목록만 페이징하고 사진 조회를 그대로 두면 청크 문제가 그대로 남는다.

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: `_fetchCovers`의 무제한 `listing_images` 배치 조회는 쿼리스트링 길이보다 **PostgREST 응답 행 수 상한(`max_rows`)에 먼저** 닿고, 그 초과는 에러가 아니라 **잘린 200 응답**으로 와서 16.2가 붙인 try/catch가 아예 발동하지 않는다.
  evidence: `supabase/config.toml:18`에 `max_rows = 1000`(호스티드 기본값도 동일). `_fetchCovers`는 `on_sale` 전량의 id로 `listing_images`를 한 번에 조회하므로, 매물당 사진 5~10장 기준 **매물 100~200건**이면 이미 1000행에 닿는다 — 위의 쿼리스트링 한도(매물 수천 건대)보다 훨씬 이른 지점이다. 잘린 응답은 정상 200이라 `catch`가 안 잡고 `pickCoverImages`도 못 알아채, 뒤쪽 매물은 대표사진이 사라지고 "N장"이 실제보다 적게 표시된다 — **조용한 오답**이지 실패가 아니다. web이 같은 자리에 둔 50개 청크는 응답을 매번 작게 유지해 이 상한에 부수적으로 걸리지 않는다. 위 페이지네이션 항목과 트리거는 이웃하지만 **고장 방식이 다르다**(요청 거부 vs 무성 절단)이라 따로 적는다.
  trigger: 위 페이지네이션 항목과 같은 자리에서 함께 본다(청크를 넣으면 이 항목도 같이 닫힌다). 그 전에라도 매물이 100건을 넘으면 `_fetchCovers`가 받은 행 수를 `max_rows`와 비교해 경고를 남기는 최소 방어를 먼저 넣는다.

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: 홈 화면(`recentListingsProvider`)이 매물 **4건**을 그리려고 `fetchListings`로 `on_sale` 전량을 가져온 뒤 `take(4)` 한다 — 16.2가 그 경로에 매물당 사진 조회까지 얹으면서, 앱의 첫 화면이 코드베이스에서 가장 넓은 `.inFilter()`를 날리고 거의 전부를 버리게 됐다.
  evidence: `app/lib/features/listings/listings_providers.dart`의 `recentListingsProvider`가 `fetchListings(...)` 결과에 `.take(4)`를 적용한다(조회 단계가 아니라 반환 후 자르기). 16.2 이전에는 매물 행만 낭비했지만, 이제 `_fetchCovers`가 그 전량 id로 `listing_images`까지 조회한다. 위 두 항목(페이지네이션·`max_rows`)의 한도에 **가장 먼저 닿을 화면이 홈**인데, 화면에는 카드 4장만 보이므로 증상이 그 자리와 연결되지 않는다.
  trigger: 위 페이지네이션 스토리에서 `.range()`를 도입할 때 홈 경로를 같이 고친다(`fetchListings`에 행 수 상한 인자를 두고 홈이 4를 넘기는 형태). 그 전에 홈이 느려졌다는 신호가 오면 그 자리에서 먼저 본다.

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: 카드·갤러리 사진의 **전송량**은 아무도 소유하고 있지 않다 — 16.2가 원본 크기를 실측하고도 디코드 축(`cacheWidth`)만 고쳤고, `Image.network`에는 디스크 캐시가 없어 앱을 껐다 켤 때마다 보이는 사진을 전부 다시 받는다.
  evidence: 실측 원본 = **1600×992 · 161KB · `cache-control: no-cache`**. `cacheWidth`는 메모리 디코드 크기만 줄이고 네트워크 바이트는 그대로다. Flutter의 `Image.network`는 프로세스 메모리 `ImageCache`만 쓰고 디스크 캐시가 없어 콜드 스타트마다 재다운로드된다. web은 같은 문제를 `next/image`로 처리했다(원본 1600px 대 표시 364px를 측정한 뒤 도입). NFR7("저비용 서빙, 목록 카드 대표 1장")이 걸린 축인데, 위 페이지네이션 항목은 이 문제를 "매물 수" 프레임으로만 잡고 있어 **매물이 적어도 발생하는 장당 전송 비용**은 어느 항목도 소유하지 않는다.
  trigger: 실기기 시연·성능 확인(Epic 16-6 SM-D 통합 시연 검증)에서 사진 로딩이 체감되면 그 자리에서. 늦어도 Epic 16 마감 전에 `cached_network_image`(디스크 캐시) 도입 또는 축소본 파생 저장 중 하나를 결정한다.

- source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
  summary: 장부 항목 `DW-730`의 정본 `trigger:` 줄이 **이미 소진된 조건**("Story 16.2 착수 시")을 그대로 들고 있고, 실제로 살아 있는 잔여 트리거는 표준 밖 키인 `trigger(잔여 23곳):`에 적혀 있다 — `trigger:`를 읽는 사람·sweep은 "이미 지난 조건"만 보게 된다.
  evidence: `deferred-work.md`의 DW-730은 `status: open`이면서 `trigger:`(소진됨)와 `trigger(잔여 23곳):`(실제 조건) 두 줄을 함께 갖고 있다. 정본 포맷(`.claude/skills/bmad-loop-sweep/deferred-work-format.md`)은 항목당 `trigger:` 하나를 규정한다. 1차 리뷰가 같은 항목에서 예약어 오용(`resolution:` → `progress:`)을 이미 한 번 고쳤는데, 같은 편집에서 이 키가 새로 생겼다. **이번 세션은 기존 항목을 수정할 권한이 없어**(오케스트레이터 소유) 여기 신규로만 적는다.
  trigger: 다음 sweep 실행 시 오케스트레이터가 DW-730의 `trigger:`를 잔여 조건(chat/auth/sell을 실제로 만지는 다음 스토리 착수 시, 늦어도 Epic 16 마감 전)으로 갱신하고 `trigger(잔여 23곳):` 줄을 없앤다.

### DW-732: Follow-up review still recommended for 16-2-이미지-카드-재설계-앱 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-16-2-이미지-카드-재설계-앱.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260807-162721-25ed; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: `wishedListingIdsProvider`(찜 오버레이 전체 집합, `app/lib/features/wishlist/wishlist_providers.dart` 신규)가 로그아웃/계정 전환 시 invalidate되지 않는다 — 같은 기기에서 계정을 바꾸면 이전 계정이 찜한 매물이 새 계정 화면에도 잠깐 채워진 하트로 보일 수 있다.
  evidence: 코드리뷰(adversarial 렌즈)가 `app/lib/features/auth/auth_controller.dart`를 실제로 열어 확인 — `signOut()`을 포함해 어떤 auth 상태 변화 지점도 이 provider를 invalidate하지 않는다. 앱은 프로세스 전역 `ProviderScope` 하나뿐(`main.dart`)이라 재로그인해도 provider가 자동 재생성되지 않는다. 다만 `recentListingsProvider`·`chatRoomsProvider`도 동일 패턴(탭 재진입 `onActivate`에만 의존, 로그아웃 트리거 없음)이라 이 스토리가 새로 만든 결함이 아니라 기존 provider 아키텍처 전반이 공유하는 문제다.
  trigger: 로그아웃/계정 전환 시 화면 provider를 정리하는 공용 메커니즘이 도입될 때(예: `authStateProvider` 리스너가 주요 화면 provider들을 일괄 invalidate) — 그 자리에서 `wishedListingIdsProvider`도 같이 등록한다. 그전에 데모 시연 중 계정 전환 후 하트 오표시가 실제로 관찰되면 그때 먼저 본다.

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: 새로 연 `WishlistRepository.fetchCovers`(`app/lib/features/wishlist/wishlist_repository.dart`)가 `_fetchCovers`와 똑같이 무제한 `.inFilter()`로 `listing_images`를 조회한다 — 기존 장부 항목이 기록한 PostgREST `max_rows=1000` **무성 절단**을 그대로 물려받았는데, 그 항목의 `trigger:`는 `_fetchCovers`만 이름으로 지목하고 있다.
  evidence: 코드리뷰(adversarial 렌즈)가 두 코드를 직접 대조 확인 — `wishlist_repository.dart`의 `.inFilter('listing_id', listingIds)`에는 청크가 없고(web은 같은 자리에 `COVER_IMAGES_CHUNK_SIZE=50`), 잘린 응답은 정상 200이라 감싼 try/catch가 발동하지 않는다. 이 스토리는 새 경로를 `docs/conventions.md` §6의 FR11 이미지축 소비처 목록에는 등록했지만, 절단 축(장부) 쪽에는 등록하지 못했다. **이번 세션은 기존 항목을 수정할 권한이 없어**(오케스트레이터 소유) 신규로만 적는다.
  trigger: `_fetchCovers`에 `.inFilter()` 청크를 넣는 바로 그 작업에서 `WishlistRepository.fetchCovers`도 **같이** 고친다(한쪽만 고치면 장부 항목은 닫히는데 찜 목록 경로는 그대로 깨져 있다). 그전에라도 찜 매물이 100건을 넘으면 이 경로부터 본다.

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: 판매완료(또는 RLS 차단)된 찜 매물은 **앱 안에서 해제할 방법이 전혀 없다** — 찜 목록의 회색 차단 타일에는 하트도 `onTap`도 없고, 그 매물은 검색·홈·AI 결과에서 제외되며 상세 진입도 막히기 때문이다. 미러 대상인 web `/wishlist`는 같은 타일에 `RemoveWishButton`을 달아 두었다.
  evidence: 코드리뷰(edge-case-hunter·intent-alignment 렌즈가 독립 발견)가 `app/lib/features/wishlist/wishlist_screen.dart`의 `_BlockedWishTile`과 web `web/src/app/(user)/wishlist/page.tsx`를 대조 확인. web 쪽 버튼에는 도입 근거가 코드에 적혀 있다("sold 찜은 해제 수단이 없어 영구 클러터 — 코드리뷰 2026-07-22 P1"). 앱은 그 결론만 이식되지 않아 같은 클러터가 재발한다. 다만 이 스토리 스펙의 I/O 매트릭스가 차단 타일의 기대 동작을 "회색 비활성 타일 + 판매완료 배지, 탭해도 상세 진입 안 됨"으로 **완결적으로** 규정했고 Never 절이 web 10.5의 다른 기능들도 의도적으로 잘라냈으므로, 스펙 위반이 아니라 스펙이 좁게 잡은 범위의 결과다.
  trigger: Epic 16-6(SM-D 통합 시연 검증)에서 찜 목록을 실제로 시연하기 전에 결정한다 — 데모 계정에 판매완료 찜이 쌓이면 화면에 그대로 보인다. 그때 web `RemoveWishButton`을 미러할지, 아니면 "차단 타일은 표시 전용"을 의도된 앱 동작으로 확정할지 사용자에게 확인한다.

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: `ListingCard`는 폭 제약이 없는 부모(가로 스크롤 등)에 **아예 놓일 수 없다** — 찜 버튼 위치 계산의 `isFinite` 가드(코드리뷰가 추가시킨 것)가 실행되기도 전에, 카드 내부의 별개 `Column(crossAxisAlignment: stretch)`이 "BoxConstraints forces an infinite width"로 먼저 죽는다.
  evidence: 이번 패스에서 그 가드의 회귀 테스트를 쓰려다 실측으로 발견했다 — 무한 폭 부모에 `ListingCard`를 렌더하면 가드 유무와 **무관하게** 같은 예외가 난다(가드는 `Positioned.top` 값에만 관여하는데, Stack의 비-Positioned 자식 레이아웃이 그보다 먼저 돈다). 그래서 가드 자체는 순수함수(`safeCardPhotoHeight`)로 분리해 단위테스트로 고정했고, "무한 폭 부모에서 카드가 산다"는 명제는 여전히 거짓이다. `stretch` 구조는 16.3이 만든 것이 아니라 그 이전부터 있던 카드 구조다.
  trigger: 카드를 가로 스크롤 목록(예: 홈의 "최근 매물" 가로 캐러셀)에 넣는 스토리를 착수할 때 — 그 자리에서 `stretch`를 걷어내거나 카드에 명시적 폭을 주는 형태로 함께 고친다. 그전까지 카드는 세로 목록 전용이라는 전제가 유지된다.

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: 에픽이 Story 16.3에 명시한 세 번째 인수조건 **"옵션 희소도 표시(카드 상위 3~4·상세 카테고리 전량)가 conventions.md 상수를 공유한다"**가 이 스토리의 스펙(`<intent-contract>`)에 아예 옮겨지지 않아 구현되지 않았다 — 그런데 찜 목록 select는 `options`를 이미 요청하고 있어, `docs/conventions.md` §4가 경고하는 "쿼리 비용은 내지만 표시는 안 되는" 상태가 그 자리에 생겼다.
  evidence: 코드리뷰(intent-alignment 렌즈)가 지적한 뒤 오케스트레이터가 직접 원문 확인 — `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`의 Story 16.3 AC 세 번째 절이 정확히 그 문장이고, `spec-16-3-신뢰속성-찜-앱.md`의 Intent·Boundaries·I/O 매트릭스 어디에도 옵션 관련 문장이 없다. 앱 모델은 타입만 갖춰져 있다(`app/lib/features/listings/listing.dart:74`가 "타입 파리티만이다 — 칩 위젯 렌더·app `options.ts` 상수 미러는 Epic 16"이라고 스스로 적어 둠). 칩 위젯은 `app/lib/features/listings/listing_card.dart`·상세 화면 어디에도 없다(grep 0건). web은 `ListingCard.tsx`가 `topOptions(...)`로 상위 3개 + "+N" 칩을, 상세가 카테고리 전량을 이미 그린다. 즉 이 스토리가 만든 결함이 아니라 **스펙이 에픽 AC의 1/3을 떨어뜨린 것**이며, 카드 재설계를 한 16.2도 칩을 도입하지 않았다.
  trigger: Epic 16 마감(회고) 전에 사용자에게 확인해 자리를 지정한다 — 16.3의 잔여로 별도 스토리를 세울지, Epic 16의 남은 스토리(16.4~16.6) 중 한 곳의 인수조건으로 심을지(CLAUDE.md B5·B8: 미룬 항목은 "어디서 고칠지"를 지정하고 그 자리에 실제로 심는다). 그전에라도 찜 목록 select에서 `options`를 빼는 것만으로는 닫히지 않는다(에픽 AC 자체가 표시를 요구한다).

- source_spec: `spec-16-3-신뢰속성-찜-앱.md`
  summary: 찜 목록의 판매완료·RLS차단 회색 타일이 `Opacity(0.6)`로 통째로 흐려져, 그 안의 본문 텍스트 대비가 **2.7:1**로 WCAG AA 기준(일반 텍스트 4.5:1)에 못 미친다 — 하필 "왜 이 매물에 못 들어가는지"를 설명하는 유일한 자리다.
  evidence: 코드리뷰(adversarial 렌즈) 지적 후 오케스트레이터가 직접 계산 확인 — `AppColors.inkSecondary`(#565F5D)를 흰 배경(#FFFFFF)에 그대로 두면 6.58:1인데, `Opacity(0.6)`으로 합성되면 실효색 ≈#9A9F9E가 되어 2.69:1로 떨어진다(`app/lib/features/wishlist/wishlist_screen.dart`의 `_BlockedWishTile`). **다만 이건 앱만의 결함이 아니다**: 미러 원본인 web `web/src/app/(user)/wishlist/page.tsx:39`가 같은 타일에 `opacity-60`을 쓰고 있어, 앱만 고치면 두 화면의 톤이 갈라진다. 그래서 이번 패스는 고치지 않고 등재만 했다.
  trigger: 접근성(대비) 점검을 web·app 동시에 하는 자리에서 함께 고친다 — 어느 쪽이든 먼저 손대게 되면 그때 두 코드를 같이 바꾼다(흐리기를 텍스트가 아니라 **배경 표면**에 주는 방식: 바탕을 `surface-base`/`AppColors.surfaceBase`로 낮추고 글자는 불투명도 100%로 유지). 늦어도 Epic 16-6(SM-D 통합 시연 검증)에서 찜 목록을 실기기로 볼 때 함께 판단한다.

### DW-733: Follow-up review still recommended for 16-3-신뢰속성-찜-앱 after the review budget was exhausted
origin: review-budget-followup
source_spec: `spec-16-3-신뢰속성-찜-앱.md`
severity: low
reason: Review budget (2 cycles) was exhausted with the story finalized (status: done, verify green) while the review pass kept recommending an independent follow-up. The work was committed by bmad-loop run 20260807-162721-25ed; this entry preserves the lingering follow-up recommendation for a deliberate later review.
status: open

- source_spec: `spec-16-4-실시간-채팅-앱.md`
  summary: 채팅방 최초 `SUBSCRIBED` 도달 시 도는 "조회~구독 사이 틈 보정" 재조회(`§12.3`, `_initialSyncDone` 블록)가 성공해도, 그 이전에 초기 로드가 실패해 세워둔 `_loadError`("과거 대화를 불러오지 못했습니다") 안내를 지우지 않는다 — 갭보정(`_gapFillFromCursor`)에는 있는 "자기가 세운 안내만 거둔다" 복구 로직이 이 블록에는 없다.
  evidence: `app/lib/features/chat/chat_room_screen.dart`의 `handleSubscribeStatus`(`!_initialSyncDone` 분기)를 직접 읽어 확인 — `_mergeIncoming(msgs)`만 하고 `_loadError`/`_loadErrorSource`를 건드리지 않는다. 다만 이건 이 스토리가 새로 만든 결함이 아니라 **미러 원본인 web의 동일한 특성**이다 — web `ChatRoomMessages.tsx`의 `if (!initialSyncDone) { ... void (async () => { const res = await fetchMessages(...); if (cancelled || 'error' in res) return; mergeIncoming(res.messages); })(); }` 블록도 똑같이 loadError를 지우지 않는다(직접 확인). 즉 web·app 양쪽에 동일하게 존재하는 특성이라, app만 고치면 "미러링" 원칙(§12.3을 web과 동일하게 따른다)에서 벗어나고 두 구현이 갈라진다.
  trigger: web 쪽을 함께 손대는 자리에서 고친다 — `gapFillFromCursor`가 이미 쓰는 "자기가 세운 안내만 거둔다"(`_loadErrorSource === 'initial'`이면 거둠) 규칙을 이 블록에도 적용하되, web `ChatRoomMessages.tsx`의 해당 블록도 같은 패스에서 함께 고쳐 드리프트를 만들지 않는다.

- source_spec: `spec-16-4-실시간-채팅-앱.md`
  summary: 앱이 백그라운드로 갔다가 돌아왔을 때(OS가 소켓을 정지시키거나 끊었는데 `channel.subscribe()` 상태 콜백이 아무 것도 안 보내는 경우) 갭보정을 트리거할 생명주기 훅(`WidgetsBindingObserver`/`AppLifecycleState.resumed`)이 `ChatRoomScreen`에 없다 — 상태 콜백(channelError/timedOut/subscribed)에만 의존한다.
  evidence: `app/lib/features/chat/chat_room_screen.dart`에 `WidgetsBindingObserver` mixin이나 `didChangeAppLifecycleState` 오버라이드가 없음을 직접 확인(grep 0건). `realtime_client`의 자동 재조인이 백그라운드/포그라운드 전환에서도 실제로 상태 콜백을 정확히 쏘는지는 라이브러리 소스 검토로만 확인했고(설계 스펙 Design Notes 참조), 실제 기기의 OS 레벨 소켓 정지·복귀 상황은 검증하지 못했다 — 이 세션(헤드리스 샌드박스, CanvasKit 크래시)에서는 실기기/정상 브라우저 실측 자체가 불가능했다(스펙 자신의 Manual checks가 이미 이 한계를 인지하고 있었음).
  trigger: 실기기(SM-D 등) 검증 시(Epic 16-6, SM-D 통합 시연 검증 범위) 앱을 백그라운드로 보냈다 몇 분 뒤 복귀시켜 메시지가 자동으로 따라잡히는지 확인한다. 안 따라잡히면 `didChangeAppLifecycleState`에서 `resumed` 시 `_gapFillFromCursor()`를 직접 호출하는 방어 코드를 추가한다.

- source_spec: `spec-16-4-실시간-채팅-앱.md`
  summary: 폴링(3초 `Timer.periodic`)을 걷어내면서 "소켓이 상태 콜백 없이 조용히 멎는" 경우의 최후 백스톱이 사라졌다 — 이전엔 폴링이 결국 다시 물어봐서 따라잡았지만, 지금은 `channelError`/`timedOut`/`subscribed` 콜백이 아예 안 오면 복구 경로가 없다.
  evidence: `app/lib/features/chat/chat_room_screen.dart`에서 `Timer.periodic` 전체 삭제를 diff로 확인. 다만 이건 이번 스토리의 실수가 아니라 **스펙 Never 절이 명시적으로 요구한 설계**다(`spec-16-4-실시간-채팅-앱.md`의 "수동 재구독·채널/소켓 재생성 코드 금지 — 라이브러리의 자동 rejoin에 의존한다") — web `docs/conventions.md` §12.5도 동일하게 "수동 재구독·채널/소켓 재생성 코드는 만들지 않는다"고 못박아 뒀고, web 쪽도 폴링 백스톱 없이 이 위험을 이미 감수하고 있다(web은 Story 12.3에서 폴링을 걷어낸 뒤 12.4~12.6에서도 이 백스톱을 되살리지 않았다).
  trigger: 실사용에서 "메시지가 안 온다"는 신고가 반복되면(특히 특정 네트워크 환경·기기에서), 그 자리에서 `realtime_client`의 실제 재조인 신뢰성을 재실측하고, 그래도 부족하면 web·app 동시에 저빈도(예: 30초) 백업 재조회를 다시 도입할지 결정한다. `docs/conventions.md`의 관련 대장 항목(`@supabase/supabase-js`/`realtime-js` 버전 업그레이드 시 재실측 트리거)과 같은 자리에서 함께 판단한다.

- source_spec: `spec-16-4-실시간-채팅-앱.md`
  summary: 스펙의 Manual checks(로컬 Supabase에서 두 계정으로 실제 실시간 송수신·재연결 실측)가 아직 한 번도 실행되지 않았다 — 자동화 검증(flutter analyze/test, npm test)은 전부 통과했지만, 실제 소켓 동작(private 채널 RLS 평가·broadcast 전달·재연결 자동 rejoin)은 위젯테스트의 상태-콜백 시뮬레이션으로만 검증됐다.
  evidence: 구현 서브에이전트가 실제로 로컬 Supabase(Docker, 마이그레이션 0022~0030 전부 적용 확인, 테스트 계정 buyer@test.com/seller-seed2@test.com 사이 기존 채팅방 존재 확인)와 앱 빌드까지 준비했으나, 이 세션(헤드리스 샌드박스)에서 Playwright로 빌드된 Flutter 웹 앱을 열자 CanvasKit이 `CONTEXT_LOST_WEBGL`로 크래시해 실제 화면 조작이 불가능했다(세션 메모리에 이미 기록된 이 환경의 알려진 한계). intent-alignment 리뷰 렌즈도 독립적으로 "스펙 자신이 유일한 실제 검증 경로라고 명시한 이 수동 확인이 실행됐다는 증거가 diff/스펙 어디에도 없다"고 지적했다.
  trigger: 실기기 또는 정상 Flutter 웹/모바일 실행 환경(이 샌드박스 밖)에서 두 계정으로 직접 채팅방을 열어: (1) 폴링 없이 상대 메시지가 즉시 보이는지 (2) 한쪽 네트워크를 끊었다 복구했을 때 배너 전환과 오프라인 큐 flush가 실제로 동작하는지 (3) 갭보정이 실제로 놓친 메시지를 채우는지 확인한다. 늦어도 Epic 16-6(SM-D 통합 시연 검증)에서 반드시 확인한다.
