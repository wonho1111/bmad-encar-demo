---
title: '12.2 Realtime Broadcast + 참가자 인가 RLS'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_revision: 'fbdd5a04e95e6e355a8bbe64f44754f94d747234'
final_revision: '32700f67bd14486f9232cea89744c545a8ca8dc2'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 채팅은 아직 3초 폴링뿐이라(Story 12.3 이전) 판매자가 문의를 실시간으로 못 받는다. 폴링을 없애려면(12.3) 그 전에 "메시지 INSERT를 실시간 채널로 방송하고, 그 채널을 방 당사자만 구독할 수 있게 인가하는" DB 토대가 먼저 있어야 한다 — 지금은 그 토대가 없다.

**Approach:** `chat_messages` AFTER INSERT 트리거가 Supabase Realtime의 "Broadcast from Database" 패턴(`realtime.broadcast_changes()`)으로 `chat:room:{room_id}` 비공개 채널에 방송하고, `realtime.messages`에 그 방의 buyer_id/seller_id만 읽을 수 있는 RLS 정책을 추가한다. `chat_messages` 자체는 손대지 않는다(방송은 그 위 레이어). 클라이언트 구독 코드는 12.3 범위.

## Boundaries & Constraints

**Always:**
- 트리거는 `chat_messages`에 **AFTER INSERT로만** 건다(UPDATE/DELETE는 일반 사용자 경로에서 발생하지 않음 — 불필요한 이벤트 배선 금지, A2).
- 트리거 함수는 SECURITY DEFINER + `set search_path = ''`로 `realtime.broadcast_changes('chat:room:' || NEW.room_id::text, TG_OP, TG_OP, TG_TABLE_NAME, TG_TABLE_SCHEMA, NEW, OLD)`를 호출한다. 토픽 리터럴 `'chat:room:' || room_id::text`는 트리거 함수·RLS 정책 양쪽에 **동일하게** 박는다(한쪽만 바뀌면 조용히 깨짐 — epics AC).
- `realtime.messages`에 추가하는 정책은 **SELECT 1개, `to authenticated`** — `chat_rooms`를 조인해 `auth.uid()`가 그 방의 buyer_id 또는 seller_id일 때만 허용(AC-CHAT-3). **INSERT 정책은 불필요**: 방송 삽입은 SECURITY DEFINER 트리거가 하므로 RLS를 우회한다(실측: `realtime.messages`의 authenticated 테이블 GRANT는 이미 있고 RLS는 켜져 있으나 정책 0건 — 지금은 authenticated 전원이 0건만 보는 상태).
- `chat_messages`의 컬럼·기존 RLS(0003)·트리거(0016)·제약(0010·0022)은 변경하지 않는다.
- 마이그레이션 번호는 착수 시 `supabase/migrations/` 재확인 후 다음 빈 번호(현재 기준 0023)를 쓰고 self-contained해야 한다(자신보다 작은 번호에만 의존, `scripts/check_migrations.py` 게이트 통과).
- 새 실DB 통합 테스트가 (a) 트리거가 INSERT 시 올바른 토픽·payload로 `realtime.messages`에 행을 만드는지, (b) 그 정책이 당사자는 허용·제3자는 차단하는지 **`set local role authenticated` + `request.jwt.claim.sub` + `set local realtime.topic`**로 실측 증명한다(존재 확인이 아니라 작동 확인, CLAUDE.md B4) — Supabase Realtime 서버가 클라이언트 구독 시 하는 것과 동일한 인가 검사를 재현.
- `api/tests/integration/conftest.py`를 신설해 5개 기존 파일이 복제해온 `TEST_DATABASE_URL` skip 가드·`_create_user`·`_insert_listing`을 올리고, 새 테스트 파일이 그것을 쓴다(대장 #188의 "6번째 파일 추가 시" 트리거 충족). 기존 5개 파일은 이번 스토리 범위 밖이라 그대로 둔다(전체 이관은 별도 판단).
- `docs/tech-debt.md`에 신규 등재 2건: ① DW-5(12-1 review-budget-followup) 이관(활성화 시 로드하는 persistent_facts 지시), ② #185(마이그레이션 게이트 프로브가 chat/realtime을 안 봄)의 트리거 도래에 대한 판단 — 게이트 프로브 확장 대신 위 전용 실DB 테스트로 대체하기로 결정한 기록. 두 항목 다 기존 번호는 수정하지 않고 신규 번호로만 남긴다(레포 관례).

**Block If:** 원격(운영) Supabase 프로젝트에서 Realtime 또는 Broadcast 기능이 꺼져 있다면(로컬 `supabase/config.toml`의 `[realtime] enabled = true`는 로컬 개발 스택 설정일 뿐 원격 프로젝트 대시보드 설정과 별개다) — 배포 전 사용자 확인 필요.

**Never:** 클라이언트 구독 코드(`web`/`app`)를 이 스토리에서 만들지 않는다(12.3 범위). `realtime.messages`에 INSERT/UPDATE/DELETE 정책을 추가하지 않는다(불필요, 위 참조). 기존 채팅 메시지에 대한 소급 방송(backfill)을 하지 않는다 — 이 트리거 이후의 신규 INSERT만 방송한다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 당사자 메시지 전송 | buyer 또는 seller가 자기 방에 메시지 INSERT | `realtime.messages`에 `topic='chat:room:{room_id}'`, `extension='broadcast'`인 행 생성 | 없음(정상 경로) |
| 제3자 구독 시도 | 방 당사자가 아닌 authenticated 유저가 그 토픽으로 접근 | RLS가 차단 — 0행 반환(AC-CHAT-3) | 없음(조용한 거부, RLS 표준 동작) |
| 마이그 적용 이전 기존 메시지 | 이 트리거가 생기기 전에 이미 존재하던 chat_messages 행 | 소급 방송 없음 — 신규 INSERT부터만 `realtime.messages`에 반영 | 없음(Never 절, additive) |

</intent-contract>

## Code Map

- `supabase/migrations/0022_chat_idempotency_key.sql` -- 현재 최댓값(0022) 확인 근거. 착수 시 재확인 후 다음 번호.
- `supabase/migrations/0003_chat.sql` -- `chat_messages`/`chat_rooms` 원본 정의 + 기존 RLS. 이 스토리가 건드리지 않음을 보장할 대상.
- `api/tests/integration/test_chat_idempotency_real_db.py` -- `set local role authenticated` + `request.jwt.claim.sub` 롤 흉내 패턴, `_create_user`/`_insert_listing`/skip 가드의 현재 구현(신설 conftest.py로 옮길 대상).
- `.github/workflows/tests.yml`(`api-db` job) -- `tests/integration` 전체를 실DB 컨테이너에 돌리는 CI 잡. 새 conftest.py·테스트 파일이 자동 포함됨.
- `docs/tech-debt.md` -- #185(마이그레이션 게이트 프로브 갭, 이 스토리가 트리거) · DW-5 이관 대상.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0023_chat_realtime_broadcast.sql`(신규, 번호 착수 시 재확인) -- AFTER INSERT 트리거(SECURITY DEFINER)가 `realtime.broadcast_changes()`로 `chat:room:{room_id}` 토픽에 방송 + `realtime.messages` SELECT RLS(당사자 한정) -- AC-CHAT-3 구현.
- `api/tests/integration/conftest.py`(신규) -- `TEST_DATABASE_URL` skip 가드·`_create_user`·`_insert_listing` 공유 fixture(대장 #188).
- `api/tests/integration/test_chat_realtime_broadcast_real_db.py`(신규) -- 위 conftest를 써서 트리거 발동+토픽 정확성, RLS 당사자 허용/제3자 차단을 실측 검증(I/O 매트릭스 3행 + AC-CHAT-3).
- `docs/tech-debt.md`(수정) -- DW-5 이관 신규 등재 + #185 트리거 도래 판단 신규 등재(위 Always 절 참조, 기존 번호 무수정).

**Acceptance Criteria:**
- Given 0001~0022가 적용된 DB, when 0023을 적용하면, then `chat_messages` AFTER INSERT 트리거와 `realtime.messages`의 새 SELECT 정책이 존재하고 `python scripts/check_migrations.py`가 통과한다.
- Given 방 당사자(buyer 또는 seller)가 `chat_messages`에 메시지를 INSERT하면, when 트리거가 발동하면, then `realtime.messages`에 `topic='chat:room:{room_id}'`인 행이 정확히 생성된다.
- Given `set local role authenticated` + 그 방 당사자가 아닌 `auth.uid()` + 같은 토픽, when `realtime.messages`를 SELECT하면, then 0행이 반환된다(제3자 차단).
- Given 같은 조건에서 당사자의 `auth.uid()`, when SELECT하면, then 해당 토픽의 행이 보인다.

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass (후속 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 2, low 9)
- defer: 1: (high 0, medium 1, low 0)
- reject: 3
- addressed_findings:
  - `medium` `patch` 소급 방송 정적 가드가 검사 전에 **`$$...$$`를 무조건 지워** `do $$ ... $$` 익명 블록 안의 백필을 통째로 놓쳤다(실측: `do $$ begin perform realtime.send(...) from public.chat_messages m; end $$;`·`do $$ begin insert into realtime.messages ...; end $$;` 둘 다 통과). 반대 방향도 깨져 있었다 — 함수 본문을 `$fn$...$fn$`처럼 꼬리표로 감싸면 안 지워져 **정상 마이그가 red**가 됐다. 그리고 자기검사(`test_guard_actually_catches_a_backfill`)는 그 제거 단계를 아예 안 거쳐 **실제로 도는 적 없는 경로**를 상대로 "잡는다"를 확인하고 있었다. 파이프라인을 `_offending_match` 하나로 합치고, 제거 대상을 `create [or replace] function ... as $태그$...$태그$` 본문으로 한정(역참조로 꼬리표 짝맞춤)했다. 실제 마이그 파일을 넣어 두 형태 모두 red 확인 후 제거해 green 재확인.
  - `medium` `patch` 방송이 **비공개(private) 채널**로 나가는지를 아무도 확인하지 않았다 — Realtime은 private 채널에만 `realtime.messages` RLS를 물어보는데, 트리거는 `private`를 넘기지 않고 `realtime.send()`의 기본값에 기댄다. 즉 이 스토리의 인가 전체가 **검사받지 않는 플랫폼 함수 기본값** 위에 서 있었다. `_broadcast_rows_for_topic`이 컬럼을 읽고 ①이 단언하도록 확장. 트리거가 `private=false`로 방송하게 바꿔 red 확인(로컬 스택·CI 스텁 양쪽).
  - `low` `patch` 정책의 `extension = 'broadcast'` 항을 어떤 검사도 보지 않았다(⑥은 나머지 두 축만 단언, 동작 테스트는 모든 행이 broadcast라 구별 못 함 — 리뷰어 실측: 항을 빼도 13건 전부 통과). ⑥에 단언 추가, 항을 뺀 정책으로 red 확인.
  - `low` `patch` ⑥이 정책이 **있는지**만 봐서 나중에 쓰기 정책을 얹어도 초록이었다 — 스펙 Never 절("INSERT/UPDATE/DELETE 정책을 두지 않는다")을 정책 집합 동등 비교로 고정.
  - `low` `patch` `authenticated`는 `realtime.messages`에 INSERT GRANT를 **이미 갖고 있고**, 남의 방 토픽으로 가짜 방송을 심는 걸 막는 건 "쓰기 정책이 없다"는 사실뿐인데 이게 실제로 거르는지는 미확인이었다(존재 확인 ≠ 작동 확인). ⑭ `test_authenticated_cannot_forge_a_broadcast` 신설, 임시 INSERT 정책을 얹어 red 확인.
  - `low` `patch` ⑥이 트리거의 `WHEN` 조건절을 못 봤다 — `when (new.body <> '')`를 붙여 일부 메시지만 방송해도 기존 단언 셋이 전부 참이라 통과했다(실측). 단언 추가 후 red 확인.
  - `low` `patch` 소급 방송 가드가 `update public.chat_messages`까지 막아, 새 nullable 컬럼을 채우는 **정상 additive 백필**(CLAUDE.md B3)이 게이트를 red로 만들었다(실측). 트리거가 AFTER INSERT뿐이라 UPDATE로는 방송이 나갈 수 없다 — chat_messages 축을 행 생성 문장(insert/merge/copy)으로 좁히고, UPDATE 배선 회귀는 ⑥이 잡는다는 것을 문서화.
  - `low` `patch` `_select_as_authenticated`가 `set local` GUC 2개를 정리하지 않았다 — `set local`은 세이브포인트가 아니라 **트랜잭션** 범위라 롤만 되돌리면 다음 조회가 직전 뷰어의 신원을 물려받는다(거짓 초록의 씨앗). 롤과 같은 자리에서 함께 지우도록 수정.
  - `low` `patch` 0023 헤더가 EXECUTE 회수로 "SECURITY DEFINER 직접 호출 경로"까지 막는다고 주장했으나 사실이 아니다 — 트리거 함수는 EXECUTE가 있어도 `trigger functions can only be called as triggers`로 거부된다(실측). 실제로 막는 축(PostgREST RPC 노출)만 남기도록 정정.
  - `low` `patch` 정책의 `exists (...)`가 `public.chat_rooms`의 RLS에 의존한다는 사실이 어디에도 없었다 — `chat_rooms_select_participant`를 좁히면 Realtime 구독이 조용히 전원 차단된다(실측: 그 정책 조건을 `false`로 바꾸니 이 스토리 테스트 4건이 red). 0023에 결합 관계를 주석으로 기록.
  - `low` `patch` 두 문서가 서로 반대로 말했다 — 프렐류드 주석은 "어느 테스트도 파티셔닝에 의존하지 않는다"인데 대장 `#195` ②는 "파티션 부재 실패 모드가 CI에선 구조적으로 발생 불가"라 방송 개수 단언이 그 땅에서만 참이다. 프렐류드 주석을 "마이그는 의존 안 하나 **테스트는 다르다**"로 정정하고 `#195`를 상호 참조. 아울러 `docs/conventions.md` §9.1의 새 ❌("이미 존재하던 객체에 대한 GRANT 회수 금지")가 이미 배포된 `0011`·`0012`·`0020`(플랫폼 기본 GRANT를 회수하고 컬럼 화이트리스트로 재부여)을 위반으로 만들고 `create or replace`의 재적용마다 합법·불법이 뒤집히는 문제가 있어, 판정 기준을 "객체의 나이"에서 "같은 파일이 정의하나 / 재부여로 좁히나"로 바꿨다. `api/tests/integration/conftest.py`엔 "헬퍼는 정리하지 않는다, 호출자가 롤백한다"는 계약을 명시(공유 헬퍼만 가져다 쓰는 다음 사람이 놓치면 CI 공용 DB에 고아 행이 쌓인다).
- deferred (신규 등재만):
  - `medium` **#196** — 0023의 "INSERT 정책 불필요" 전제가 기대는 **적용 롤의 `rolbypassrls`가 원격에서 확인된 적이 없다.** ⑧이 그 속성을 조회하긴 하지만 로컬·CI에선 소유자가 언제나 postgres 슈퍼유저라 구조적으로 참이라 잡을 수 없는 자리다. 실패하면 방송 INSERT가 RLS에 거부되고 플랫폼이 예외를 삼켜 **메시지는 저장되고 방송만 사라진다**. `#195`의 원격 확인 목록(ⓐⓑⓒ)에 이 항목이 빠져 있으나 기존 항목은 수정하지 않는 규칙이라 신규로 등재. 트리거는 `#195`와 동일(원격 적용 직전).
- 기각 3건: `from conftest import`가 `__init__.py` 추가 시 깨진다는 재지적(2차 패스에서 같은 근거로 이미 기각 — 실패 모드가 조용한 오답이 아니라 즉시 red인 수집 오류이고 트리거가 투기적, A2) · 모양 검사 3건이 `seeded` 픽스처를 불필요하게 쓴다는 지적(진단 소음 개선치가 픽스처를 하나 더 만드는 비용보다 작다, A2·A3) · `realtime.topic` GUC가 트리거 밖으로 새어 클라이언트가 행 축 값을 스스로 공급할 수 있다는 지적(공급되는 값이 **자기 방 토픽**이라 권한 상승이 없고, 참가자 조건이 그대로 남아 있다 — 제안된 가드 자체가 리포터의 실측과 어긋났다).

### 2026-07-28 — Review pass (후속 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 5, low 5)
- defer: 0
- reject: 4
- addressed_findings:
  - `high` `patch` `realtime.messages` SELECT 정책이 **행의 `topic` 컬럼을 전혀 참조하지 않아** 세션 상수로 평가됐다 — 아무 방 하나의 당사자이기만 하면 토픽 필터 없는 조회로 **모든 방의 방송 본문**이 보였다(로컬 Supabase 스택에서 재현: 방1 구매자가 방2 메시지 읽음). `using`에 `topic = realtime.topic()` 행 축을 추가. 실제 Realtime 서버(:55321)에 private broadcast 채널을 웹소켓으로 구독해 추가 전/후 모두 당사자=ok·제3자=Unauthorized로 동일함을, 그리고 **메시지 0건인 방도 여전히 구독 인가됨**을 실측해 회귀 없음을 확인.
  - `medium` `patch` 실제 클라이언트 경로(`authenticated` 롤 INSERT)가 어느 테스트에서도 실행되지 않아 "트리거가 SECURITY DEFINER라 정책 없이 쓸 수 있다"는 0023의 핵심 전제가 하중을 받은 적이 없었다 — `security definer`를 떼도 기존 9건이 전부 초록이었다. ⑫ `test_authenticated_client_insert_still_broadcasts` 추가.
  - `medium` `patch` `test_migration_owner_role_bypasses_rls`가 **잘못된 대상**(테스트 커넥션의 `current_user`)을 재고 있었다 — CI에선 항상 postgres 슈퍼유저라 구조적으로 실패 불가. 전제가 실제 기대는 두 속성(함수 `prosecdef` + **함수 소유자**의 `rolbypassrls`)을 재도록 교체.
  - `medium` `patch` `seeded` 픽스처에 방이 1개뿐이라 교차-방 오배송이 원리적으로 안 보였다 — 토픽을 `sender_id`로 유도하도록 바꿔도 9건 전부 통과. 같은 구매자를 공유하는 방 2개로 확장하고 ⑨(정책 행 축)·⑩(자기 방 토픽으로만 방송)·⑪(다른 방 당사자 차단)를 추가.
  - `medium` `patch` 소급 방송 금지 정규식이 **가장 자연스러운 백필 형태**(`select realtime.send(...) from public.chat_messages`)를 통째로 놓쳤다(실측: 그 문장을 실행하니 방송 0→2건). 방송 함수 호출·MERGE·COPY·`update only`·따옴표/공백 우회를 포함하도록 확장하고, 주석을 먼저 제거해 거짓 양성도 없앴으며, 가드 자신을 검사하는 테스트를 추가.
  - `medium` `patch` 대장 `#194`가 "오늘 실사용 영향 0 / 트리거=12.3 착수"로 프레이밍해 **배포 게이팅을 놓쳤다** — 0023 적용 순간부터 `chat_messages` INSERT가 Realtime 가용성에 의존한다. 여기에 프렐류드 realtime 스텁이 프렐류드 자신의 규칙(:7-9 "원격에서 확인")과 달리 로컬 기준 실측이라는 점, 실제 `realtime.messages`가 파티션 테이블이라 CI에선 무음 실패 모드가 구조적으로 발생 불가라는 점을 묶어 **대장 `#195` 신규 등재**(트리거: 원격 적용 직전). 기존 `#194`는 수정하지 않음.
  - `low` `patch` DB가 필요 없는 소급 방송 정적 가드가 모듈 전체 `TEST_DATABASE_URL` skip 마크에 묶여 **로컬·`api` 잡에서 아예 안 돌았다**(실측: 환경변수 없이 9 skipped). `api/tests/test_migration_no_backfill.py`로 분리해 DB 없이도 돌게 하고, 검사 범위를 0023 단일 파일에서 0023 이후 전체로 넓힘.
  - `low` `patch` ⑥이 이름만 대조해 트리거를 `after insert or update`나 `before insert`로 바꿔도 통과했다 — `pg_get_triggerdef`로 시점·수준·이벤트를, `pg_policies.qual`로 정책의 두 축을 대조하도록 확장.
  - `low` `patch` ⑤가 방송 **개수**만 봐 같은 NEW를 3번 방송하는 구현도 통과했고, ②는 발신자를 단언하지 않아 ①과 실질적으로 같은 검사였다 — payload 본문 집합과 `sender_id`를 각각 단언.
  - `low` `patch` 0023이 회수한 EXECUTE 권한(public/anon/authenticated)을 아무 테스트도 확인하지 않았다(형제 `test_view_count_rpc_real_db.py`엔 이미 같은 검사가 있다) — ⑬ 추가.
  - `low` `patch` `docs/conventions.md` §9.1의 ❌ "GRANT의 drop 금지"가 0023의 `revoke all on function`과 충돌하게 읽혔다 — "새 객체의 최초 권한 설정"과 "기존 객체의 권한 회수"를 구분하는 ✅ 항목을 추가하고 ❌ 문구를 후자로 한정.
- 기각 4건: `from conftest import`가 `__init__.py` 추가 시 깨진다는 지적(실패 모드가 **조용한 오답이 아니라 즉시 red인 수집 오류**이고 트리거가 투기적이라 A2) · `check_migrations.py`가 §9.1의 drop/create 짝을 기계 검사하지 않는다는 지적(게이트의 정적 한계는 `#185`·`#192`가 이미 같은 축으로 추적 중이라 세 번째 등재는 대장 소음) · `realtime.messages`가 채팅 본문을 이중 저장한다는 지적(실측: 로컬 스택의 파티션이 `messages_2026_07_24`~`_30`의 **롤링 7일 창**이라 플랫폼이 스스로 정리한다 — 무기한 보존이 아니다) · 정책의 문자열 결합 비교가 인덱스를 못 탄다는 재지적(1차 패스에서 EXPLAIN 실측으로 이미 기각한 것과 동일 지적).

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 0, low 5)
- defer: 1: (high 0, medium 1, low 0)
- reject: 5
- addressed_findings:
  - `low` `patch` `supabase/migrations/0023_chat_realtime_broadcast.sql`의 `chat_messages_broadcast()`가 0016의 `enforce_chat_room_seller()`와 달리 EXECUTE 권한 회수(`revoke all ... from public/anon/authenticated`)가 없었다 — 동일 3줄 추가로 정정(일관성, advisor 노이즈 예방).
  - `low` `patch` `test_chat_realtime_broadcast_real_db.py`의 소급 방송 금지 정규식이 스키마 접두사(`public.`/`realtime.`)를 강제해 접두사 없는 미래 문장을 놓칠 수 있었다 — 접두사를 선택적으로 완화, red/green 재확인.
  - `low` `patch` `docs/conventions.md` §9.1이 정책(policy) drop-recreate만 화이트리스트하고 트리거 drop-recreate(0016·0023이 실제로 쓰는 패턴)는 문서에 없었다 — 트리거 항목을 본문에 추가(CLAUDE.md B8).
  - `low` `patch` "`realtime.messages`에 INSERT 정책이 불필요하다"는 설계가 `rolbypassrls=true` 전제 하나에 의존하는데 이를 확인하는 자동 테스트가 없었다 — `test_migration_owner_role_bypasses_rls` 추가.
  - `low` `patch` `docs/tech-debt.md`의 conftest.py 관련 신규 등재가 "새 conftest.py는 새 파일 1개만 쓰고 기존 5개는 그대로"라는 사실을 명시하지 않아 `#188`이 완전히 해소된 것으로 오독될 위험 — #193으로 명시 정정.
- deferred (신규 등재만):
  - `medium` **#194** — Realtime Broadcast 전달 실패가 플랫폼 `realtime.send()`에서 조용히 삼켜지거나(트리거 함수 자체엔 예외 처리가 없어) Realtime 자체가 불가용하면 `chat_messages` INSERT 전체가 롤백될 수 있다. 오늘은 폴링이 유일한 전달 경로라 영향 0, Story 12.3(폴링 제거) 착수 시 재판단 트리거.
- 기각 5건: RLS 정책의 `chat_rooms` 조인이 문자열 결합 비교라 인덱스를 못 태운다는 지적(현재 규모 5행에서 seq scan 비용이 사실상 0임을 EXPLAIN으로 직접 확인 — 데모 규모에서 무해, A2) · 토픽 리터럴이 트리거·정책 두 곳에 중복된다는 지적(테스트가 이미 드리프트를 잡아주고 있어 공유 함수 추상화는 과설계, A2) · 테스트의 `set local` f-string 조립(값이 항상 내부 생성 UUID이고 형제 파일의 기존 관례와 동일, 실제 인젝션 표면 없음) · realtime 스키마 스텁이 실제 플랫폼과 드리프트할 수 있다는 지적(storage.objects 스텁도 동일한 특성을 이미 안고 있는 기존 수용 패턴) · RLS 정책이 `extension='broadcast'`만 다루고 `presence`/`postgres_changes`는 다루지 않는다는 지적(리포터 스스로 "오늘은 버그 아님"이라 명시한 투기적 선제 대응, A2).

## Design Notes

**왜 `realtime.messages`에 INSERT 정책이 필요 없나:** Broadcast from Database 패턴은 Realtime 서버가 아니라 **DB 트리거가 직접 `realtime.messages`에 행을 쓴다**. 트리거 함수가 SECURITY DEFINER이므로 이 INSERT는 RLS를 우회한다 — 클라이언트가 그 테이블에 직접 쓰는 경로가 이 스토리엔 없다(브로드캐스트를 클라가 보내는 기능은 범위 밖).

**RLS를 로컬에서 어떻게 실측하나(웹소켓 없이):** 공식 문서에 따르면 Realtime 서버는 클라이언트가 채널을 구독할 때 `authenticated` 롤 + 그 유저의 JWT 클레임 + 세션 GUC `realtime.topic`을 설정하고 `realtime.messages`를 조회해보는 것으로 인가를 확인한다(`realtime.topic()` 함수가 `current_setting('realtime.topic', true)`를 읽음, `auth.uid()`는 `request.jwt.claim.sub`를 읽음 — 둘 다 로컬 psql에서 `set local`로 그대로 재현 가능). 그래서 실제 웹소켓 연결 없이도 같은 SQL 검사를 실행해 RLS를 검증할 수 있다 — 실측 확인: 로컬 스택의 `realtime.messages`는 RLS 활성화·정책 0건(현재 authenticated 전원 0건).

**#185(게이트 프로브 갭)를 프로브 확장 대신 전용 테스트로 대체:** `scripts/check_migrations.py`의 3개 프로브는 고정 목록(listings/guide_documents 대상)이라 4번째를 추가하는 건 이 스토리 범위를 넘는 게이트 인프라 변경이다. 12.1이 자신의 제약도 프로브가 아닌 전용 실DB 테스트로 검증한 전례를 따른다 — 오히려 실제 authenticated 롤 시뮬레이션이 정적 프로브보다 신뢰도가 높다.

## Verification

**Commands:**
- `python scripts/check_migrations.py` -- expected: exit 0(정적+동적, 도커 필요 — 로컬에 없으면 CI 결과로 확인).
- `TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres python -m pytest api/tests/integration/test_chat_realtime_broadcast_real_db.py -q` -- expected: 전부 green. 트리거 또는 정책을 잠깐 제거해 red 확인 후 되돌려 green 재확인(CLAUDE.md B4).
- `TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres python -m pytest api/tests/integration/ -q` -- expected: 기존 5개 파일 + 신규 파일 전부 green(conftest.py 도입이 기존 테스트를 깨지 않음).

## Auto Run Result

**요약:** `chat_messages` AFTER INSERT 트리거(SECURITY DEFINER)가 Supabase Realtime "Broadcast from Database" 패턴으로 `chat:room:{room_id}` 채널에 방송하고, `realtime.messages`에 방 당사자(buyer/seller)만 SELECT 가능한 RLS 정책 1개를 추가하는 마이그레이션(0023) + 이를 실측 검증하는 실DB 통합 테스트 9건(코드리뷰 patch 2건 포함) + CI 게이트가 이 마이그레이션을 검증할 수 있도록 `migration-check-prelude.sql`에 realtime 스키마 스텁 신설. 클라이언트 구독 코드(web/app)는 Story 12.3 범위라 이 스토리에서 다루지 않음 — intent-alignment auditor가 이 범위 판단이 스펙 Boundaries·Never 절과 정확히 일치함을 확인.

**Files changed:**
- `supabase/migrations/0023_chat_realtime_broadcast.sql`(신규) — AFTER INSERT 트리거 + `realtime.messages` SELECT RLS. EXECUTE 권한 회수 포함(코드리뷰 patch).
- `api/tests/integration/conftest.py`(신규) — `TEST_DATABASE_URL` skip 가드·`_create_user`·`_insert_listing` 공유 fixture(대장 #188 트리거 충족, 신규 파일만 소비).
- `api/tests/integration/test_chat_realtime_broadcast_real_db.py`(신규) — 트리거 발동·토픽 정확성·RLS 당사자 허용/제3자 차단·소급 방송 없음·`rolbypassrls` 전제를 실측하는 테스트 9건.
- `scripts/migration-check-prelude.sql`(수정, 스펙 태스크 목록 밖 — 0023이 참조하는 `realtime.broadcast_changes`/`realtime.messages`/`realtime.topic`이 게이트·CI의 빈 pgvector 컨테이너엔 없어 실제 로컬 Supabase 스택에서 그대로 복사해 스텁으로 추가하지 않으면 게이트 자체가 적용 실패로 죽는다 — storage.objects 스텁과 동일 축의 정당한 확장, docs/conventions.md §9.1).
- `docs/conventions.md`(수정) — §9.1에 트리거 drop-recreate 허용 예외 추가(코드리뷰 patch, 기존 정책 drop-recreate 예외와 동일 근거).
- `docs/tech-debt.md`(수정) — 신규 등재 4건: #191(DW-5 이관, persistent_facts 지시) · #192(#185 트리거 도래 판단 — 프로브 확장 대신 전용 테스트로 대체) · #193(#188이 새 파일 1개만 해소, 기존 5개는 여전히 복제 상태임을 명시, 코드리뷰 patch) · #194(Realtime 방송 실패가 관측 안 됨, defer — 트리거: Story 12.3 착수 시).

**Review findings breakdown** (4개 레이어: adversarial 10건 + edge-case-hunter 3건, dedup 2건 → verification-gap 0건, intent-alignment은 서술형 확인 — 범위 판단이 스펙과 일치함을 재확인):
- patch 5건(전부 low) — `chat_messages_broadcast()`의 EXECUTE 권한 미회수(0016 선례와 불일치) · 소급 방송 금지 정규식이 스키마 접두사를 강제(우회 가능) · `docs/conventions.md` §9.1이 트리거 drop-recreate를 화이트리스트하지 않음 · "INSERT 정책 불필요" 설계의 `rolbypassrls` 전제가 테스트로 안 잠김 · tech-debt #188 관련 신규 등재가 "부분 해소"임을 명시하지 않음. 전부 이 파일들에 직접 적용 완료.
- defer 1건(medium) — Realtime Broadcast 전달 실패가 플랫폼 `realtime.send()`에서 조용히 삼켜지거나 Realtime 자체 불가용 시 `chat_messages` INSERT 전체가 롤백될 수 있음(오늘은 폴링이 유일 경로라 영향 0) → `docs/tech-debt.md` #194로 등재, 트리거는 Story 12.3 착수 시.
- reject 5건 — RLS 정책의 문자열 결합 비교가 인덱스를 못 태운다는 지적(현재 규모 5행에서 EXPLAIN 실측 결과 seq scan 비용이 사실상 0, 데모 규모에서 무해) · 토픽 리터럴 중복(테스트가 이미 드리프트를 잡음, 공유 함수는 과설계) · 테스트의 `set local` f-string 조립(내부 생성 UUID만 사용, 형제 파일과 동일 관례) · realtime 스텁의 플랫폼 드리프트 위험(storage.objects 스텁도 동일 특성의 기존 수용 패턴) · RLS가 `presence`/`postgres_changes`를 안 다룬다는 지적(리포터 스스로 비-버그로 명시한 투기적 우려).

**Follow-up review recommendation:** `true`. patch 5건 전부 low(0 high, 0 medium, 5 low) → 점수 = 3×0 + 1×5 = 5 ≥ 5, 규칙상 true.

**DW-5 처리 결과** (활성화 시 로드한 persistent fact 지시사항): `deferred-work.md`의 `DW-5`(status: open, 12-1 review-budget-followup)를 확인, `docs/tech-debt.md`에 대응 항목이 없어 **#191로 이관함**. 동결 파일 자체는 수정하지 않음.

**Verification 수행 (오케스트레이터가 직접 재실행, 서브에이전트 보고에 의존하지 않음):**
- `python scripts/check_migrations.py` → 통과(정적 23개 파일 밀집·순서 확인 + 동적 0001~0023 전체 적용 + 프로브 3종 그린).
- `TEST_DATABASE_URL=... pytest api/tests/integration/test_chat_realtime_broadcast_real_db.py -q` → 9 passed(코드리뷰 patch 적용 전 7개, 적용 후 9개 — 신규 테스트 2건 포함). 구현 단계에서 트리거·RLS 정책을 각각 잠깐 제거해 red 확인 후 복구해 green 재확인(B4). 신규 patch 테스트(소급 방송 정규식·rolbypassrls)도 동일하게 red→green 확인.
- `TEST_DATABASE_URL=... pytest api/tests/integration/ -q` → 61 passed, 1 failed. 실패 1건(`test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls`)은 이번 변경과 무관한 기존 로컬 스택 전용 GRANT 차이(대장 #190 기 등재) — CI와 동일하게 재현한 일회용 컨테이너(빈 pgvector + 프렐류드 + 0001~0023 전량)에서는 그 테스트를 포함해 전체 green임을 별도로 확인.

**Matrix Test Audit:** I/O 매트릭스 3행 전부 실행·통과하는 커버 테스트 보유 — 1행(당사자 방송)은 ①②, 2행(제3자 차단)은 ③, 3행(소급 방송 없음)은 신설한 정적 파일 검사 ⑦(스펙 계획 단계에는 없었으나 이 감사 과정에서 누락을 발견해 즉시 추가).

**Residual risks:**
- 원격(운영) Supabase 프로젝트의 Realtime/Broadcast 활성화 여부는 미확인 — 스펙 Block If, 배포 전 사용자 확인 필요.
- 대장 #194(방송 실패 무관측) — Story 12.3 착수 시 재판단.
- 대장 #193 — `conftest.py`는 신규 파일 1개만 소비, 기존 5개 실DB 테스트 파일의 복제는 그대로 남음(범위 밖 판단, 다음 실DB 테스트 파일 추가 시 재판단).
- RLS 정책은 세션 GUC `realtime.topic()` 기준으로 인가하므로, 향후 `realtime.messages`에 대한 원시 SQL 조회가 `where topic = ...` 필터 없이 실행되면 인가된 세션이 다른 방의 행도 볼 수 있다 — Realtime 서버 자신의 구독 쿼리는 항상 토픽으로 필터링하므로 정상 경로에선 문제없으나, Story 12.3 클라이언트 구독 코드 작성·리뷰 시 유념할 사항으로 남김.

---

## Auto Run Result — 후속 2차 리뷰 (2026-07-28)

**왜 한 번 더 봤나:** 1차 패스가 `followup_review_recommended: true`로 끝났다(패치 5건 전부 low, 점수 5). 새 세션이 같은 diff를 다시 봤고 — 1차와 달리 이번 리뷰어들은 **주장을 코드로 깨뜨려 확인**했다(mutation testing). 그 결과 1차가 못 본 결함 하나와 검증 공백 여러 개가 나왔다.

**가장 큰 것:** `realtime.messages` SELECT 정책이 **행의 `topic` 컬럼을 참조하지 않았다.** 조건이 `extension='broadcast'` + `exists(...)`뿐이라 행마다 달라지는 값이 없어 **세션 상수**로 평가됐고, 결과적으로 "아무 방 하나의 당사자"이기만 하면 `select * from realtime.messages`(토픽 필터 없이)로 **모든 방의 채팅 본문**이 보였다. 로컬 Supabase 스택에서 그대로 재현했다(방1 구매자가 방2의 메시지 읽음). 오늘 클라이언트가 닿을 수 있는 경로는 아니다(`realtime` 스키마는 PostgREST 노출 대상이 아니고 Realtime 서버는 항상 토픽으로 필터링한다) — 하지만 그건 **정책이 아니라 외부 호출자가 공급하던 안전장치**였고, 이 스토리가 만들려던 것이 바로 그 정책이다(CLAUDE.md B9).

**왜 1차가 못 봤나:** 테스트 헬퍼 `_select_as_authenticated`가 **자기 안에서 `where topic = %s`를 붙이고 있었다.** 즉 테스트가 결함을 가리는 필터를 스스로 공급했다. 방도 1개뿐이라 "자기 방으로 갔는가"와 "아무 데로나 갔는가"가 구별되지 않았다.

**Files changed (이번 패스):**
- `supabase/migrations/0023_chat_realtime_broadcast.sql` — 정책 `using`에 행 축 `topic = realtime.topic()` 추가 + 두 축이 각각 무엇을 판정하는지와 실측 근거를 주석에 기록.
- `api/tests/integration/test_chat_realtime_broadcast_real_db.py` — 방 2개 픽스처(`_Seed` 네임드튜플)로 확장, 신규 검사 4건(⑨ 정책 행 축 · ⑩ 자기 방 토픽으로만 방송 · ⑪ 다른 방 당사자 차단 · ⑫ 실제 authenticated 경로 방송 · ⑬ EXECUTE 회수), ⑥·⑤·②·⑧을 실제로 잡히도록 강화, `set local` 문자열 조립을 `set_config` 바인드 파라미터로 교체. 9건 → 13건.
- `api/tests/test_migration_no_backfill.py`(신규) — 소급 방송 정적 가드를 DB 없는 자리로 분리·확장(0023 이후 전체 파일, 방송 함수 호출·MERGE·COPY·따옴표 우회 포함, 주석 제거, 가드 자기검사 포함).
- `docs/tech-debt.md` — `#195` 신규 등재(0023의 원격 전제 3가지: 스텁의 로컬 기준 실측 · 파티션 부재 시 무음 실패 · Realtime 불가용 시 채팅 저장 자체 실패. 트리거: **원격 적용 직전**). 기존 항목 무수정.
- `docs/conventions.md` — §9.1에서 "새 함수의 최초 권한 설정(revoke)"과 "기존 객체의 GRANT 회수"를 구분.

**Review findings breakdown:** patch 11건(high 1 · medium 5 · low 5) 전부 적용 완료, defer 0건, reject 4건. intent_gap·bad_spec 0건 — 스펙의 Intent·Boundaries는 이번에도 그대로 유효했고(intent-alignment auditor 재확인), 결함은 전부 그 스펙을 코드로 옮기는 층에 있었다.

**Verification 수행 (오케스트레이터가 직접 실행):**
- **정책 변경이 실제 구독을 깨지 않는지** — 로컬 Realtime 서버(:55321)에 private broadcast 채널을 실제 웹소켓으로 구독. 변경 전/후 모두 방 당사자(buyer·seller)=`ok`, 제3자=`Unauthorized`. **메시지가 0건인 방에서도 인가됨**을 확인해 "빈 채널 구독 불가" 회귀가 없음을 실측(이게 이 변경의 유일한 실질 위험이었다). 프로브 데이터·임시 의존성은 전부 정리, 잔여 0건 확인.
- **가드가 잡는지(만들었다가 아니라 잡는다가 완료, B4)** — 5가지를 일부러 깨뜨려 red 확인 후 복구해 green 재확인: ① 정책을 옛 버전으로 되돌림 → ⑨⑥ red · ② 트리거에 UPDATE 배선 → ⑥ red · ③ `security definer` 제거 → ⑫⑧ red · ④ 토픽을 `sender_id`로 유도 → ⑩ red · ⑤ authenticated에 EXECUTE 재부여 → ⑬ red. **CI와 동일한 스텁 환경에서도** ①이 red를 내는 것을 별도로 확인(가드가 실제 도는 땅에서 작동함).
- `python scripts/check_migrations.py` → 통과(정적 + 0001~0023 전량 적용 + 프로브 3종 그린).
- `pytest tests/integration/` (로컬 스택) → 65 passed, 1 failed. 실패 1건(`test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls`)은 이번 변경과 무관한 로컬 스택 전용 GRANT 차이(대장 `#190` 기 등재).
- `pytest tests/integration/` (CI 동등 일회용 pgvector 컨테이너 + 프렐류드 + 0001~0023) → **66 passed**, 전량 green.
- `pytest -q`(DB 없는 `api` 잡 재현) → 209 passed, 71 skipped. 분리한 소급 방송 가드 3건이 **이제 여기서도 돈다**(이전엔 skip).

**Follow-up review recommendation:** `true`. 이번 패스 패치 11건 중 high 1건(정책 행 축) → 규칙상 `true`. 다만 남은 위험의 성격이 바뀌었다 — 코드 축 지적은 이번에 소진에 가깝고, 남은 것은 **원격에서만 답할 수 있는 것**(대장 `#195`)이다.

**Residual risks:**
- **대장 `#195` — 원격 적용 직전에 사용자가 확인해야 할 3가지.** ⓐ 원격 프로젝트에 Realtime/Broadcast가 켜져 있는가(안 켜져 있으면 0023 적용 즉시 **채팅 저장 자체가 실패**한다 — 스펙 Block If) ⓑ 원격의 `realtime.send()` 정의가 프렐류드 스텁과 같은가(특히 `private` 기본값 — 다르면 방송이 공개 채널로 나간다) ⓒ `realtime.messages` 파티션 유지가 자동인가(파티션이 없으면 방송만 조용히 사라진다).
- 대장 `#194`(방송 실패 무관측) — Story 12.3 착수 시 재판단. `#195`의 트리거가 그보다 먼저 온다.
- 대장 `#193` — `conftest.py`는 신규 파일만 소비, 기존 5개의 복제는 그대로.
- 실제 웹소켓 **수신**(구독 후 메시지가 실제로 배달되는지)은 여전히 미검증 — 이번엔 구독 **인가**까지만 실측했다. 배달 축은 클라이언트 구독 코드와 함께 Story 12.3 범위.

---

## Auto Run Result — 후속 3차 리뷰 (2026-07-28)

**왜 또 봤나:** 2차 패스가 `followup_review_recommended: true`로 끝났다(high 1건). 새 세션의 4개 레이어가 같은 diff를 다시 봤고, 이번에도 **주장을 코드로 깨뜨려** 확인했다. 결과: 코드가 만드는 **런타임 결함은 새로 나오지 않았고**(intent_gap·bad_spec 0건, 실제 유출·오배송 없음), 나온 것은 전부 **"이 코드가 지킨다고 주장하는 것을 검사가 실제로는 안 지키고 있던"** 축이다.

**가장 큰 것 — 지난 패스가 만든 소급 방송 가드가 정작 그 형태를 못 잡았다.** `test_migration_no_backfill.py`는 검사 전에 `$$...$$`를 **무조건** 지웠는데, 그건 함수 정의만이 아니라 **`do $$ ... $$` 익명 블록도** 지운다. 백필을 가장 자연스럽게 쓰는 두 형태(`do $$ begin perform realtime.send(...) from public.chat_messages m; end $$;`, `do $$ begin insert into realtime.messages ...; end $$;`)가 그냥 통과했다 — 실제 마이그레이션 파일로 넣어 재현했다. 반대 방향도 깨져 있었다: 함수 본문을 `$fn$...$fn$`처럼 꼬리표로 감싸면 안 지워져 **정상 마이그가 red**가 됐다. 그리고 이 가드의 "잡는다" 자기검사는 그 제거 단계를 아예 거치지 않아, **실제로 도는 적 없는 경로**를 상대로 확인하고 있었다(그래서 스스로 이 사각지대를 못 봤다). 파이프라인을 `_offending_match` 하나로 합쳐 파일 검사와 자기검사가 같은 것을 통과하게 만들고, 제거 대상을 `create [or replace] function ... as $태그$...$태그$` 본문으로 한정했다.

**두 번째 — 이 스토리의 인가 전체가 검사받지 않는 기본값 위에 서 있었다.** Realtime은 **비공개(private) 채널에만** `realtime.messages` RLS를 물어본다. 그런데 트리거는 `private`를 넘기지 않고 플랫폼 `realtime.send()`의 기본값(`true`)에 기대며, 어떤 테스트도 그 컬럼을 읽지 않았다. 기본값이 다른 곳에서는 방송이 공개 채널로 나가고 — 공개 채널엔 정책이 조회되지 않으므로 — 이번 스토리가 만든 참가자 정책이 통째로 무의미해지는데, 테이블을 직접 읽는 테스트는 전부 초록으로 남는다. 한 컬럼을 더 읽어 고정했다.

**Files changed (이번 패스):**
- `api/tests/test_migration_no_backfill.py` — 달러 인용 처리를 양방향으로 고침(`_strip_function_bodies` 신설, 꼬리표 역참조), 파일 검사·자기검사를 `_offending_match`로 통합, `update chat_messages`를 금지 목록에서 제외(정상 백필 오탐), docstring에 "무엇을 못 보나"(마이그 파일 밖은 시야 밖) 명시.
- `api/tests/integration/test_chat_realtime_broadcast_real_db.py` — `private` 컬럼 단언 추가, ⑥에 `extension` 축·정책 집합 동등·`WHEN` 절 부재 단언 추가, ⑭(가짜 방송 차단) 신설, `_select_as_authenticated`의 GUC 누수 정리. 13건 → 14건.
- `supabase/migrations/0023_chat_realtime_broadcast.sql` — 주석만 수정(EXECUTE 회수의 과장된 주장 정정 + `public.chat_rooms` RLS 결합 관계 기록). SQL 동작 무변경.
- `scripts/migration-check-prelude.sql` — 파티션 관련 주석이 `#195` ②와 반대로 읽히던 것을 정정·상호 참조.
- `docs/conventions.md` — §9.1의 GRANT 회수 판정 기준을 "객체의 나이"에서 "같은 파일이 정의하나 / 재부여로 좁히나"로 교체(새 ❌가 이미 배포된 `0011`·`0012`·`0020`을 위반으로 만들고 있었다).
- `api/tests/integration/conftest.py` — "헬퍼는 정리하지 않는다, 호출자가 롤백한다" 계약 명시.
- `docs/tech-debt.md` — `#196` 신규 등재(원격 적용 롤의 `rolbypassrls` 미확인, 트리거는 `#195`와 동일). 기존 항목 무수정.

**Review findings breakdown:** patch 11건(high 0 · medium 2 · low 9) 전부 적용, defer 1건(`#196`), reject 3건. intent_gap·bad_spec 0건 — intent-alignment auditor도 서술형으로 "스펙이 문언으로 지정한 것은 거의 그대로 지켜졌고, 넓힌 부분은 전부 스펙 밖 표면(프렐류드·EXECUTE 회수·문서·대장)"이라고 확인했다.

**Verification 수행 (오케스트레이터가 직접 실행):**
- **가드가 잡는지(B4)** — 6가지를 일부러 깨뜨려 red 확인 후 복구해 green 재확인: ① `do $$` 백필 마이그 파일 2종 투입 → 소급 방송 가드 red · ② 정책에서 `extension` 축 제거 → ⑥ red · ③ `realtime.messages`에 임시 INSERT 정책 추가 → ⑥·⑭ red · ④ 트리거에 `when` 조건절 → ⑥ red · ⑤ 트리거가 `private=false`로 방송 → ① red · ⑥ `chat_rooms_select_participant`를 `false`로 → 실DB 테스트 4건 red(결합 관계 실증). **①②⑤는 CI와 동일한 프렐류드 스텁 환경에서도** red를 내는 것을 별도 확인.
- `python scripts/check_migrations.py` → 통과(정적 + 0001~0023 전량 적용 + 프로브 3종 그린).
- `pytest tests/integration/`(로컬 스택) → **66 passed, 1 failed**. 실패 1건(`test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls`)은 이번 변경과 무관한 로컬 스택 전용 GRANT 차이(대장 `#190` 기 등재).
- `pytest tests/integration/`(CI 동등 일회용 pgvector 컨테이너 + 프렐류드 + 0001~0023 전량) → **67 passed**, 전량 green.
- `pytest -q`(DB 없는 `api` 잡 재현) → **209 passed, 72 skipped**(2차 패스의 71 skip + 이번 신설 ⑭).
- 프로브 정리: 일회용 컨테이너 삭제, 로컬 스택의 정책·트리거·함수 원복 확인, 리뷰 중 생긴 고아 방송 행 8건(대응 `chat_rooms`가 없는 롤백 잔여) 제거해 잔여 0건 확인.

**Follow-up review recommendation:** `true`. 이번 패스 패치 11건 중 high 0건, medium 2·low 9 → 점수 = 3×2 + 1×9 = 15 ≥ 5, 규칙상 `true`. 다만 규칙이 세는 것은 "이번에 고친 양"이지 "남은 위험"이 아니다 — 이번 11건은 전부 **검사의 사각지대**였고 코드가 만드는 런타임 결함은 3개 패스 연속 0건이며, 남은 축은 코드로 답할 수 없는 것(대장 `#195`·`#196` = 원격에서만 확인 가능)뿐이다. 그럼에도 **규칙을 임의로 뒤집지 않는다**(B9: 규칙은 어길 수 없는 자리에 둔다) — 프론트매터는 규칙대로 `true`로 둔다. 판단은 위 문장으로 남긴다: **다음 한 번은 코드 리뷰가 아니라 원격 확인이 되어야 한다.**

**Residual risks:**
- **대장 `#195` + `#196` — 원격 적용 직전에 사용자가 확인할 4가지.** ⓐ Realtime/Broadcast가 켜져 있는가(아니면 0023 적용 즉시 **채팅 저장 자체가 실패**한다 — 스펙 Block If) ⓑ 원격 `realtime.send()`의 `private` 기본값이 스텁과 같은가(다르면 방송이 공개 채널로 나가 이번 RLS가 무의미해진다 — 이번에 테스트로 고정한 건 **로컬·CI 기준값**이다) ⓒ `realtime.messages` 파티션 유지가 자동인가 ⓓ 마이그레이션 적용 롤이 `rolbypassrls`인가.
- 대장 `#194`(방송 실패 무관측) — Story 12.3 착수 시 재판단. `#195`·`#196`의 트리거가 먼저 온다.
- 대장 `#193` — `conftest.py`는 신규 파일만 소비, 기존 5개의 복제는 그대로.
- 실제 웹소켓 **수신**(배달)은 여전히 미검증 — Story 12.3 범위.
- 소급 방송 가드는 `supabase/migrations/*.sql`만 본다. 일회용 `scripts/` SQL·앱 코드·원격 수동 실행은 시야 밖이다(이번에 docstring에 명시).
