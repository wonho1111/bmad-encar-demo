---
title: '12.1 멱등키 마이그레이션'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_revision: '7d07f19653d0b7869b7d899bbf5de03e6ea3b524'
final_revision: '6a5f29c'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: []
---

<intent-contract>

## Intent

**Problem:** `chat_messages`에 중복 방지 수단이 없다. Epic 12가 폴링을 실시간 전송으로 바꾸면(Story 12.3), 네트워크가 끊긴 채 재전송하면 같은 메시지가 두 번 저장될 수 있다(FR41). 이 DB 토대가 없으면 뒤 스토리(12.3 송수신, 12.4 재연결 갭 보정)가 중복 제거를 할 자리가 없다.

**Approach:** `chat_messages`에 nullable `client_message_id uuid` 컬럼 + `UNIQUE(room_id, client_message_id)` 제약(CR1)을 추가하는 additive 마이그레이션 한 건. 클라이언트가 메시지마다 랜덤 id를 만들어 실어 보내고(이 프로젝트가 이미 `crypto.randomUUID()`로 쓰는 패턴), 같은 값으로 재전송되면 `INSERT ... ON CONFLICT (room_id, client_message_id) DO NOTHING`이 조용히 무시한다 — 이 SQL 패턴 자체는 앱 코드(12.3) 몫이고, 이 스토리는 그게 가능하도록 스키마·제약만 놓는다.

## Boundaries & Constraints

**Always:**
- 마이그레이션 파일명은 착수 직전에 `supabase/migrations/`를 다시 세어 `max+1`로 정한다(추측 금지, 계획 시점 실측값은 `0022`이나 착수 시점에 재확인). `NNNN_이름.sql` 형식, 알파벳 접미사 금지(§9.2).
- `client_message_id`는 **nullable**로 추가한다 — 기존 행·기존 스키마를 깨지 않는 additive 컬럼이다(I13). 기본값·백필 없음.
- `UNIQUE(room_id, client_message_id)`는 정확히 이 두 컬럼 조합이다(CR1 — 실제 컬럼명은 `room_id`).
- 이 마이그레이션은 self-contained해야 한다 — 자신보다 큰 번호의 마이그에 의존하지 않는다(`scripts/check_migrations.py` 게이트가 실제로 검증).
- 기존 `chat_messages` 관련 제약 2개(`chat_messages_body_not_blank` 0003, `chat_messages_body_max_len` 2000자 0010)와 `chat_rooms`의 seller_id 강제 트리거(0016, 로그인 라벨 "0003c")가 이 변경 후에도 그대로 동작함을 **실제 INSERT로 검증**하는 실DB 통합 테스트를 새로 추가한다(AC-CHAT-1 — 동일 키 2회 INSERT → 행 1개, 트리거 부작용 0).
- RLS 정책·GRANT는 이 스토리에서 건드리지 않는다 — 새 컬럼은 기존 `chat_messages` 정책(0003)이 그대로 덮는다(컬럼 추가는 행 정책에 영향 없음).

**Block If:**
- `chat_messages.client_message_id`(또는 동일 목적의 컬럼)가 이미 존재한다 — 스키마 드리프트나 부분 실행 흔적일 수 있으므로 임의로 덮어쓰거나 드롭하지 않고 블록한다.

**Never:**
- Realtime broadcast·`realtime.messages` RLS·토픽 배선을 건드리지 않는다 — Story 12.2 범위다.
- 클라이언트(web·app)가 `client_message_id`를 실제로 생성해 보내도록 만드는 코드를 이 스토리에서 작성하지 않는다 — Story 12.3 범위다. 이 스토리는 DB 스키마·제약과 그것을 증명하는 테스트까지만이다.
- 컬럼을 `NOT NULL`로 만들거나 기존 행에 값을 백필하지 않는다.
- `0003_chat.sql`·`0010_chat_message_length.sql`·`0016_chat_room_integrity.sql`을 in-place로 고치지 않는다 — 새 마이그 파일로만 더한다(B3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 중복 재전송 | 같은 `room_id`+`client_message_id`로 2회 INSERT(`ON CONFLICT (room_id, client_message_id) DO NOTHING`) | 행이 정확히 1개만 존재 | 에러 없음(조용히 무시됨) |
| 다른 방, 같은 클라이언트 id | 같은 `client_message_id`, `room_id`만 다른 2건 INSERT | 두 행 모두 존재(유니크 범위는 방 단위) | 에러 없음 |
| 미도입 구간 메시지(NULL) | `client_message_id`를 지정하지 않고 여러 건 INSERT | 전부 성공(NULL끼리는 유니크 제약에서 충돌하지 않음) | 에러 없음 |
| 본문 길이 회귀 | 2000자 초과 body로 INSERT | 거부됨(기존 0010 CHECK 불변) | `check_violation`(기존과 동일) |

</intent-contract>

## Code Map

- `supabase/migrations/0021_listings_view_count_anon_grant.sql` -- 현재 최댓값(0021) 확인 근거. 착수 시 재확인 후 다음 번호로 새 파일을 만든다.
- `supabase/migrations/0003_chat.sql` -- `chat_messages` 원본 정의(`room_id` 컬럼명, 빈 본문 CHECK). 새 컬럼·제약이 여기 얹힌다.
- `supabase/migrations/0010_chat_message_length.sql` -- 기존 2000자 CHECK. 이 스토리가 깨지 않아야 함을 테스트로 증명.
- `supabase/migrations/0016_chat_room_integrity.sql` -- `chat_rooms` BEFORE INSERT 트리거(seller_id 강제, 로그인 라벨 "0003c"). 새 테스트가 이 트리거와 함께 정상 동작함을 확인.
- `api/tests/integration/test_view_count_rpc_real_db.py` -- 이 레포의 실DB 통합 테스트 관례(픽스처·롤백·`TEST_DATABASE_URL` skip 패턴)의 참고 예시.
- `.github/workflows/tests.yml`(`api-db` job) -- `tests/integration` 전체를 실DB 컨테이너에 돌리는 CI 잡. 새 테스트 파일이 자동으로 여기 포함된다.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0022_chat_idempotency_key.sql`(신규, 번호는 착수 시 재확인) -- `chat_messages`에 nullable `client_message_id uuid` 컬럼 + `UNIQUE(room_id, client_message_id)` 제약 추가 -- FR41·CR1 구현, additive만(I13).
- `api/tests/integration/test_chat_idempotency_real_db.py` -- 신규 실DB 통합 테스트: 동일 `(room_id, client_message_id)` 2회 INSERT가 행 1개로 수렴, 기존 0016 트리거·0010 CHECK 무회귀, NULL 다건 허용, 본문 초과 여전히 거부 -- AC-CHAT-1을 선언이 아니라 실행으로 증명(CLAUDE.md B4).

**Acceptance Criteria:**
- Given 0001~0021이 적용된 빈 DB, when 새 마이그를 적용하면, then `chat_messages.client_message_id` 컬럼과 `UNIQUE(room_id, client_message_id)` 제약이 존재하고 `python scripts/check_migrations.py`가 통과한다.
- Given 동일한 `(room_id, client_message_id)` 쌍으로 두 번 INSERT(`ON CONFLICT (room_id, client_message_id) DO NOTHING`)하면, when 둘 다 실행되면, then 그 쌍에 해당하는 행이 정확히 1개이고 에러가 나지 않는다.
- Given 0016 트리거로 생성된 채팅방(seller_id가 매물 소유자로 강제된 방)에, when `client_message_id`를 실은 메시지를 삽입하면, then 트리거의 seller_id 강제와 0010의 2000자 CHECK가 이전과 동일하게 동작한다(회귀 없음).
- Given 마이그레이션 적용 이전에 존재하던 기존 메시지 행에, when 이 마이그레이션을 적용하면, then 그 행은 영향받지 않고 `client_message_id`는 NULL로 읽힌다(I13, additive).

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 0, low 6)
- defer: 1: (high 0, medium 0, low 1)
- reject: 5
- addressed_findings:
  - `low` `patch` `supabase/migrations/0022_chat_idempotency_key.sql`의 self-containment 주석이 0020·0021을 "자신보다 큰 번호" 예시로 들었으나 실제로는 더 작은(먼저 적용된) 번호라 방향이 반대였다 — 주석을 정정.
  - `low` `patch` `api/tests/integration/test_chat_idempotency_real_db.py`의 `_message_count` 헬퍼가 `client_message_id = %s`로 비교해 NULL 인자를 받으면 SQL 3값 논리상 항상 0을 반환하는 잠복 버그 — `IS NOT DISTINCT FROM`으로 NULL-안전하게 수정(직접 psql로 이전 동작이 실제로 0을 반환함을 재현 확인 후 고침).
  - `low` `patch` 같은 파일의 `_create_user`가 판매자 역할 테스트 유저에도 `role: "buyer"`를 하드코딩(형제 실DB 테스트 `test_view_count_rpc_real_db.py`의 `_create_seller` 관례와 불일치) — `role` 파라미터를 받아 판매자 호출에 `role="seller"`를 전달하도록 수정, 실제로 `profiles.role='seller'`가 반영됨을 확인.
  - `low` `patch` `test_chat_room_seller_enforcement_trigger_unaffected`의 docstring이 "0016 트리거 회귀 확인"을 과잉주장 — 실제 입력(buyer_id=seller_id=매물 소유자)은 트리거가 아예 없어도 0003의 CHECK만으로 거부되므로 트리거 단독 증거가 아니다. docstring을 트리거 강제 자체는 `seeded` 픽스처의 setup 단언이 커버한다고 명확히 하고, 이 테스트는 트리거+CHECK 조합의 시스템 레벨 확인이라고 정정.
  - `low` `patch` 같은 테스트 파일의 "무엇을 못 보나" 절이 형제 실DB 테스트(`test_view_count_rpc_real_db.py`)와 달리 RLS/PostgREST 우회(직접 postgres 접속으로 `set local role`만 흉내냄) 사실을 공개하지 않았다 — 한 줄 추가로 정정(대장 #133과 동일 축).
  - `low` `patch` `.github/workflows/tests.yml`의 `api-db` 잡 주석이 "이제 파일이 2개"로 낡아 있었다(이번 diff로 `tests/integration`이 5개 파일이 됨) — 현재 목록으로 갱신하고, 매 신규 파일마다 다시 낡지 않도록 문구를 일반화.

### 2026-07-28 — Review pass (follow-up, `followup_review_recommended: true`로 재실행)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 2, low 10)
- defer: 3: (high 0, medium 1, low 2)
- reject: 10
- addressed_findings:
  - `medium` `patch` AC-CHAT-1의 중복 재전송 테스트가 두 INSERT를 **같은 트랜잭션**(세이브포인트) 안에서 돌려, Postgres의 speculative insertion 경로만 탔다. 스펙이 말하는 "네트워크가 끊긴 채 재전송"은 첫 요청이 커밋된 뒤 오는 별개 트랜잭션이라 다른 경로다 — 형제 `test_view_count_rpc_real_db.py`의 `seeded_committed` 패턴을 재사용한 autocommit 픽스처 + 테스트 ⑩ 추가. 실행 전/후 `auth.users`·`listings`·`chat_rooms`·`chat_messages` 카운트가 동일함을 실측해 커밋 픽스처가 잔여물을 안 남김을 증명.
  - `medium` `patch` 새 컬럼을 `authenticated` 롤로 쓰고 읽는 경로가 어디서도 실행되지 않았다. 스펙 Always 절의 "새 컬럼은 기존 `chat_messages` 정책(0003)이 그대로 덮는다"는 **소유자 권한이 아니라 authenticated 표면**에 대한 주장인데, 7건 전부 DSN 소유자로 접속해 RLS·GRANT를 우회했다 — `set local role authenticated` + `request.jwt.claim.sub` 테스트 ⑬ 추가(레포 기존 관례). 실측 red 확인: `chat_messages`의 테이블 INSERT를 회수하고 `client_message_id`를 뺀 컬럼별 재부여(= `listings`가 0011→0021에서 실제로 겪은 시나리오)를 걸자 **⑬만 red, 나머지 12건 green**. `reset role`이 중단된 트랜잭션에서 2차 예외를 던져 진짜 원인을 가리던 것도 형제 파일 관례대로 함께 정리.
  - `low` `patch` `ON CONFLICT` 없이 같은 쌍을 두 번 넣었을 때 제약이 실제로 거부하는지(23505)를 아무 테스트도 안 봤다 — ①②는 회피 문법을 쓰므로 제약 자체가 무는지는 증명 못 한다. 현재 앱 코드(`web/src/lib/messages.ts`)가 아직 평범한 INSERT라 지금 도달 가능한 경로이기도 하다 — 테스트 ⑨ 추가.
  - `low` `patch` AC 1행("컬럼과 제약이 존재한다")에 직접 단언이 없었다. 특히 **제약 이름**을 아무도 안 봤는데, 0022의 재적용 멱등 가드가 `conname`을 키로 쓰므로 이름이 바뀌면 가드가 못 알아보고 중복 제약을 만든다 — 컬럼 타입·nullable·기본값 + 제약 이름·정의를 직접 대조하는 테스트 ⑧ 추가. 실측 red 확인: 제약 이름만 바꿨을 때 **⑧만 red**(나머지는 컬럼 조합으로 추론돼 전부 green).
  - `low` `patch` 테스트 ①이 두 INSERT에 **같은 본문**을 넣어, `DO NOTHING`이 `DO UPDATE`(덮어쓰기)로 바뀌어도 개수가 1이라 통과했다. 방 전체 개수(키로 안 거른)도 안 세어 "부작용 0"이 미확인이었다 — 본문을 다르게 넣고 살아남은 행이 첫 번째인지 + 방 전체 1행인지 단언. 실측 red 확인: 헬퍼를 `do update set body = excluded.body`로 바꾸자 ①⑩이 본문 단언에서 red.
  - `low` `patch` `client_message_id`가 NULL이면 `ON CONFLICT DO NOTHING`으로도 중복이 안 막힌다는 사실이 Design Notes 산문에만 있었다 — Story 12.3 이전 구간과 구버전 클라이언트가 정확히 그 상태라 다음 스토리가 반대로 가정할 위험이 있다. "NULL이면 2행이 남는다"를 단언하는 테스트 ⑪로 한계를 고정(B4 "못 보는 것을 검사 옆에 적는다"의 실행판).
  - `low` `patch` 0010의 2000자 CHECK를 초과(2001자) 쪽만 봐서, 상한을 더 조이는 회귀(`< 2000`)는 green으로 지나갔다 — 정확히 2000자가 허용되는지 보는 테스트 ⑫ 추가. 실측 red 확인: CHECK를 `< 2000`으로 바꾸자 **⑫만 red**.
  - `low` `patch` 테스트 파일의 "무엇을 못 보나" 절이 "`set local role`로 롤만 흉내낸다(형제 파일과 동일한 한계)"고 적었으나, 이 파일엔 `set local role`이 **한 번도 없었다**(형제 파일엔 9곳). 공개 문구가 실제보다 커버리지를 넓게 주장하고 있었다 — 실제 상태(소유자 권한 직접 접속, ⑬만 롤 흉내)로 정정.
  - `low` `patch` `test_chat_room_seller_enforcement_trigger_unaffected`의 **이름**이 자기 docstring과 모순됐다(지난 패스가 docstring엔 "트리거 단독 증거가 아니다"라고 적었는데 이름은 여전히 `trigger_unaffected`). CI 로그·grep이 읽는 건 이름이다 — `test_listing_owner_cannot_open_chat_room_on_own_listing`으로 개명하고, 트리거가 실제로 고정되는 자리(`seeded` 픽스처의 setup 단언)를 docstring에 명시.
  - `low` `patch` `.github/workflows/tests.yml`의 `api-db` 주석이 지난 패스에서 일반화되며 **거짓 불변식**을 심었다("각 테스트가 자기 트랜잭션 안에서만 쓰고 끝에 롤백하는 동일 패턴"). 실측: 5개 중 2개(`test_fr11_cover_images_real_db.py`·`test_view_count_rpc_real_db.py`의 `seeded_committed`)가 `autocommit=True`로 **커밋**하고 delete로 정리한다. 또 주석 전체가 전제한 `pytest-randomly`는 이 프로젝트에 설치돼 있지 않아(`api/pyproject.toml` dev extras = pytest·httpx) 순서는 알파벳순 고정이고 무작위 순서로 시험된 적이 없다 — 실제 상태로 정정하고, 지난 패스가 지우면서 함께 잃은 "실패 시 어디를 볼지" 진단 포인터도 복원.
  - `low` `patch` `0022_chat_idempotency_key.sql` 주석 3건 정정 — (a) "멱등은 0001~부터의 관례"는 과잉주장(0010은 맨 `add constraint`라 재적용하면 멈춘다, 실측), (b) `§9.3(a)` 인용이 틀렸다(§9.3은 **정본 in-place 수정 판정 규칙**이지 신규 파일 작성 관례가 아니다 — 이 인용을 근거로 다음 사람이 승인 게이트를 우회할 수 있다), (c) "`add constraint if not exists`가 없어서 DO 블록뿐"이라는 서술이 `create unique index if not exists`라는 실재 대안을 빠뜨린 거짓 이분법 — 대안을 밝히고 이름 있는 제약을 고른 실제 이유(이 테이블의 무결성 규칙이 전부 명명 제약이라 `pg_constraint` 한 곳에서 같이 보인다)로 대체.
  - `low` `patch` `sprint-status.yaml`이 `12-1: done`인데 `epic-12: backlog`로 남아, 같은 파일 헤더의 상태 정의("backlog → in-progress: 첫 스토리 생성 시")와 모순됐다 — Epic 11이 이미 같은 누락을 겪고 회고에서 사후 정정한 자리다. `in-progress`로 전이하고, 이 파일의 `last_updated` 기록 관례(스토리 완료마다 항목 추가)도 함께 이행.

### 2026-07-28 — Review pass (3차, `followup_review_recommended: true`로 재실행)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 2: (high 0, medium 1, low 1)
- reject: 13
- addressed_findings:
  - `medium` `patch` **검증 환경이 CI가 아니었고, 그래서 실패 1건을 잘못된 항목에 귀속했다.** 1·2차 패스가 "CI `api-db` 잡과 동일 범위"라며 돌린 것은 로컬 Supabase 스택이었고, 그 스택은 `anon`의 `profiles` SELECT 권한이 **없다**(CI 프렐류드·운영은 있다). 그래서 난 실패는 대장 #138이 기록한 `DID NOT RAISE`가 아니라 정반대인 `permission denied`였다 — 실행해서 원문으로 확인했다. CI를 실제로 재현해(일회용 pgvector 컨테이너 + `scripts/migration-check-prelude.sql` + 마이그 0001~0022 전량) 다시 돌린 결과 **53 passed, 0 failed**. 스펙의 해당 Verification 줄에 정정 주석을 달고, 실측을 대장 #190에 등재.
  - `low` `patch` `api/tests/integration/test_chat_idempotency_real_db.py` — 0016 트리거 검증이 `bogus_seller_id = buyer_id` **한 가지 입력만** 쓰고 있었다. 0016의 본래 목적은 "임의의 제3자 seller_id를 적어 모르는 사람에게 방을 강제 생성"하는 위조 차단인데, 그 입력을 아무도 안 넣어서 트리거가 *자기충돌만 고치는* 형태로 퇴화해도 13건 전부 green이었다 — 제3자 위조 테스트 ⑭를 추가. **실측 red 확인:** 트리거를 자기충돌 전용으로 퇴화시키자 **⑭만 red, 나머지 13건 green**. 원복 후 14 green 재확인.
  - `low` `patch` 같은 파일의 `_create_user` — 2차 패스가 추가한 `role` 파라미터가 **아무 단언에도 닿지 않았다**(profiles 행 존재만 확인). "판매자를 만들었다"가 검사되지 않는 주장으로 남아 있던 것 — `profiles.role`을 인자와 대조하는 단언을 추가. **실측 red 확인:** 0001 가입 트리거가 `raw_user_meta_data->>'role'`을 무시하고 항상 `'buyer'`를 쓰도록 퇴화시키자 **14건 전부 setup에서 red**(`buyer != seller`). 원복 후 green.
  - `low` `patch` 같은 파일의 ⑩(커밋 경계 재전송) — ①에는 있는 "방 전체 행 수 == 1"(부작용 0) 단언이 ⑩에는 없었다. 스펙이 말하는 실제 재전송 경로는 ⑩ 쪽인데 더 얕게 검사되고 있었다 — 단언 추가. **실측 red 확인:** 재전송이 키 없는 행을 하나 더 남기는 누수를 헬퍼에 심자 ⑩이 red(3 ≠ 1). **같은 누수 조건에서 이 단언을 빼면 ⑩은 green** — 패치 전 버전이 못 잡던 것을 잡는다는 것까지 확인.
  - `low` `patch` `.github/workflows/tests.yml` — 2차 패스가 "실측으로 정정했다"며 쓴 `api-db` 주석이 **착지 시점에 이미 세 군데 틀려 있었다**: (a) `seeded_committed`를 가진 파일로 `test_fr11_cover_images_real_db.py`를 지목했으나 그 파일의 커밋 픽스처 이름은 `seeded`이고, (b) 정작 같은 커밋이 추가한 `test_chat_idempotency_real_db.py`가 목록에서 빠졌으며, (c) "그 픽스처들은 이메일을 uuid로 유일하게 만든다"는 fr11에 대해 거짓이다(하드코딩 `s@t.test`). 파일명 나열을 버리고 확인 명령(`grep -ln autocommit …`)을 적는 방식으로 바꿔 다시 낡지 않게 하고, fr11의 하드코딩 이메일 위험을 명시.
  - `low` `patch` `_bmad-output/implementation-artifacts/sprint-status.yaml` — 2차 패스가 Epic 11의 **과거 기록 줄**에서 스토리와 무관한 공백 1개를 지웠다(`회고 완료 - epic-11` → `회고 완료 -epic-11`). append-only 원장에 남은 무관한 편집이라 원복(A3 외과적 변경).
  - `low` `patch` 이 스펙 파일 — 상단 요약이 "테스트 7건"인데 2차 패스 절은 13건이라, 앞부분만 읽는 소비처(다음 스토리 컨텍스트)가 커버리지를 절반으로 오인할 수 있었다. 상단에 "1차 패스 시점 기록 / 최종 14건" 정정 표시.
- deferred (신규 등재만, 기존 항목 무수정 — 이번 실행 지시):
  - `low` **#189** — 대장 #186의 제목·본문 ①이 "12.3·**12.4**의 인수조건이 `client_message_id`를 이름으로 요구하지 않는다"고 단정했으나, `epics-increment-2026-07-12.md:930`(AC-CHAT-2)은 `dedup 키=client_message_id`를 **명시적으로 요구한다**. 12.3 지적과 NULL 구간 fallback 지적은 유효. 기존 항목을 못 고치므로 정정만 신규 등재.
  - `medium` **#190** — CI 재현 환경에서 `tests/integration` **53 passed 0 failed**이고, #180의 테스트는 이미 교정된 이름(`..._including_view_count`)으로 존재하며 #138의 테스트도 통과한다. 즉 `#138`·`#180`이 "Epic 12 착수 전 선행"으로 걸어둔 조건 중 **테스트 축 2건은 이미 충족**돼 보인다. 닫는 판단은 오케스트레이터 몫이라 실측만 등재.

## Design Notes

`client_message_id` 타입을 `uuid`로 정한 근거: Technical Decisions("클라이언트가 메시지마다 랜덤 id를 생성")가 구체 타입을 못박지 않았지만, 이 레포는 이미 `web/src/app/(user)/sell/photo-item.ts`·`photo-sync.ts`에서 `crypto.randomUUID()`를 랜덤 클라이언트 id 생성에 쓰고 있다 — 같은 관례를 재사용한다(신규 패턴 도입 회피, A2).

`UNIQUE(room_id, client_message_id)`가 NULL을 어떻게 다루는지: Postgres의 유니크 제약은 NULL을 서로 다른 값으로 취급하므로, `client_message_id`가 아직 안 채워진 행(이 스토리 이후~Story 12.3 이전 구간, 또는 영구히 채워지지 않는 과거 행)끼리는 몇 건이 있어도 제약 위반이 나지 않는다 — 이 스토리가 additive(I13)로 남을 수 있는 이유가 이것이다.

## Verification

**Commands:**
- `python scripts/check_migrations.py` -- expected: exit 0, self-containment 정적·동적 검사 모두 통과(도커 필요, 없으면 정적 층만 돌고 실패 처리되므로 로컬에 도커가 없으면 CI 결과로 확인).
- `TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres python -m pytest api/tests/integration/test_chat_idempotency_real_db.py -q` -- expected: 전부 green. 제약을 잠깐 주석 처리해 먼저 red를 확인한 뒤 되돌려 green을 재확인한다(CLAUDE.md B4 "잡는다"가 완료 기준).

## Auto Run Result

> **✎ 3차 패스 정정(2026-07-28)** — 아래 "Auto Run Result"는 **1차 패스 시점의 기록**이다. 테스트 건수(7건)와 리뷰 집계(patch 6건)는 그 시점 값이며, **최종 상태는 테스트 14건 / 3개 패스 누계 patch 25건**이다. 아래 2차·3차 패스 절이 최신이다.

**요약:** `chat_messages`에 nullable `client_message_id uuid` 컬럼 + `UNIQUE(room_id, client_message_id)` 제약을 추가하는 마이그레이션(0022) + 그 제약이 실제 INSERT로 동작함을 증명하는 실DB 통합 테스트 7건(1차 패스 시점, 최종 14건). 클라이언트가 실제로 이 값을 채워 보내는 것(Story 12.3 범위)은 이 스토리에서 다루지 않음 — 4개 독립 리뷰 레이어 중 intent-alignment auditor가 이 범위 판단이 에픽 문서의 스토리 순서(12.1→12.2→12.3)와 정확히 일치함을 확인.

**Files changed:**
- `supabase/migrations/0022_chat_idempotency_key.sql` (신규) — additive 컬럼 + 유니크 제약, 재적용 안전(멱등 가드).
- `api/tests/integration/test_chat_idempotency_real_db.py` (신규) — I/O 매트릭스 4행 + AC-CHAT-1을 실DB INSERT로 검증하는 테스트 7건.
- `docs/tech-debt.md` (수정) — #184(동결 장부 DW-4를 대장으로 이관, 지시된 작업) + #185(이번 코드리뷰가 부수적으로 찾은 마이그레이션 게이트 커버리지 갭, defer).
- `.github/workflows/tests.yml` (수정) — `api-db` 잡의 낡은 "파일 2개" 주석을 현재 5개 파일 목록으로 정정 + 향후 파일 추가에 안 낡도록 문구 일반화(코드리뷰 patch).

**Review findings breakdown** (4개 레이어: adversarial 10건 + edge-case-hunter 4건, dedup 2건 → verification-gap 0건, intent-alignment은 서술형 확인):
- patch 6건(전부 low, 전부 이 파일들에 직접 적용 완료) — 마이그레이션 주석의 방향 오류 정정, 테스트 헬퍼 `_message_count`의 NULL 비교 잠복버그(`=`→`IS NOT DISTINCT FROM`) 수정, 판매자 테스트 유저 역할 하드코딩 정정, 트리거 회귀 테스트 docstring 과잉주장 정정, RLS/PostgREST 우회 미공개 보완, CI 주석 파일수 갱신.
- defer 1건(low) — `scripts/check_migrations.py`의 동적 프로브 3종이 chat 스키마를 전혀 안 봄(이 스토리가 만든 게 아니라 게이트 설계 때부터의 커버리지 범위) → `docs/tech-debt.md` #185로 등재.
- reject 5건 — "IF NOT EXISTS가 스펙의 Block If를 어긴다"는 지적(재검토 결과 Block If는 실행 시점 사전조건이었고 실제로 드리프트가 없었음을 이미 확인했으며, 영구 방어 요구는 A2 단순함 원칙·기존 마이그 전체의 관례와 불일치해 기각) · 동시 마이그 적용 경합(단일 프로젝트·단일 배포자 구조상 비현실적) · 대장 #184 자신의 트리거 표현(기존 #148/#149/#164와 동일 패턴이라 일관성 있음) · 대장 요약 대시보드 미반영(문서 자신이 이미 "건수 불신뢰" 명시) · UNIQUE 제약의 락 비용 미언급(데모 규모에서 무해함을 리뷰어도 인정).

**Follow-up review recommendation:** `true`. patch 6건 전부 low(0 high, 0 medium, 6 low) → 점수 = 3×0 + 1×6 = 6 ≥ 5, 규칙상 true.

**DW-4 처리 결과** (활성화 시 로드한 persistent fact 지시사항): `deferred-work.md`의 `DW-4`(status: open, 11-5 review-budget-followup)를 확인, `docs/tech-debt.md`에 대응 항목이 없어 **#184로 이관함**. 동결 파일 자체는 수정하지 않음.

**Verification 수행:**
- `python scripts/check_migrations.py` → 통과(정적 22개 파일 밀집·순서 확인 + 동적 0001~0022 전체 적용 + 프로브 3종 그린).
- `TEST_DATABASE_URL=... python -m pytest api/tests/integration/test_chat_idempotency_real_db.py -q` → 7 passed(패치 전 7개, 패치 후 재실행 7개 모두 green). 구현 단계에서 UNIQUE 제약을 직접 드롭한 뒤 재실행해 관련 2개 테스트가 red로 실패함을 실측 확인 후 복구해 다시 green 확인(B4).
- 패치 적용 후 `_message_count`의 NULL-safety 수정은 psql로 `= NULL`(0건 매칭) vs `IS NOT DISTINCT FROM NULL`(1건 매칭) 직접 대조해 수정이 실제로 동작을 바꿈을 확인.
- `profiles.role='seller'` 캐스트 수정도 psql로 직접 INSERT해 값이 실제로 반영됨을 확인.

---

## 2차 패스 (후속 리뷰, 2026-07-28)

지난 패스가 `followup_review_recommended: true`로 닫혔기에 **새 세션의 독립 4레이어**로 다시 돌렸다(CLAUDE.md B4 "코드리뷰는 새 세션에서 돈다"). 마이그레이션의 DDL은 한 글자도 안 바뀌었다 — 이미 적용된 마이그를 in-place로 고치는 것은 forward-only 원칙 위반이라, 이번 패스의 변경은 **테스트 커버리지·주석의 사실관계·상태 파일** 세 축에만 들어갔다.

**핵심 발견 2건(medium):** ① AC-CHAT-1을 증명한다던 테스트가 두 INSERT를 같은 트랜잭션에서 돌려, 스펙이 말하는 "네트워크가 끊긴 채 재전송"(= 커밋 경계를 넘는 별개 요청) 경로를 한 번도 안 탔다. ② 스펙 Always 절이 "새 컬럼은 기존 정책이 그대로 덮는다"고 주장하는데, 7건 전부 DB 소유자 권한으로 접속해 RLS·컬럼 GRANT를 우회하고 있었다 — 그 주장이 사는 표면에서 아무것도 실행되지 않았다.

**추가된 파일 변경:**
- `api/tests/integration/test_chat_idempotency_real_db.py` — 7건 → **13건**. 신규 ⑧~⑬(제약 이름·정의 직접 단언 / `ON CONFLICT` 없는 평범한 중복이 23505로 거부 / 커밋 경계 넘는 재전송 수렴 / NULL 키면 중복이 안 막힌다는 한계 고정 / 2000자 허용 경계 / `authenticated` 롤 쓰기·읽기) + 커밋 픽스처 `seeded_committed` + ① 보강 + 과잉주장 테스트명 개명 + "무엇을 못 보나" 사실 정정.
- `supabase/migrations/0022_chat_idempotency_key.sql` — **주석만** 3건 정정(DDL 무변경).
- `.github/workflows/tests.yml` — `api-db` 주석의 거짓 불변식·미설치 플러그인 전제 정정.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `epic-12` backlog→in-progress, `last_updated` 항목 추가.
- `docs/tech-debt.md` — defer 3건을 **신규 #186·#187·#188로만** 등재(기존 항목 무수정 — 이번 실행 지시).

**Follow-up review recommendation:** `true`. patch 12건(high 0, medium 2, low 10) → 점수 = 3×2 + 1×10 = **16 ≥ 5**.

**Defer 3건** (전부 `docs/tech-debt.md` 신규 등재, 트리거를 관측 가능한 이벤트에 앵커):
- **#186** (medium) — Story 12.3·12.4의 인수조건이 `client_message_id`를 이름으로 요구하지 않아, 12.1이 놓은 토대가 소비되지 않을 구조. 더해서 supabase-js `.insert()`는 `ON CONFLICT DO NOTHING`을 못 내보내고 대응물(`.upsert(ignoreDuplicates)`)은 무시된 행에 표현을 안 돌려줘 현재 호출부의 `.single()`이 PGRST116으로 던진다. 트리거 = **Story 12.3 스펙 작성 시**(심을 인수조건 3개를 항목에 명시).
- **#187** (low) — 로컬 Supabase 스택에 0020~0022를 psql로 손으로 적용해 CLI 이력 테이블과 어긋났을 수 있다(§9.2의 `0003c` 사고와 같은 계열). 지난 패스가 Residual risks에만 적고 대장엔 안 넣어 "열린 일"로 안 세어졌다. 트리거 = **다음 `supabase db reset` 또는 로컬 E2E 실행 시**.
- **#188** (low) — `api/tests/integration/`에 `conftest.py`가 없어 시드 헬퍼가 5개 파일에 복제(이미 12.1 1차 구현에서 role 하드코딩 결함을 만들었다). 트리거 = **Epic 12에서 6번째 통합 테스트 파일을 추가할 때**.

**Reject 10건**(요지): 마이그레이션에 타입 드리프트 차단·`conkey` 기반 가드를 넣으라는 요구 2건(Block If는 착수 시점 사전조건이고 실제 드리프트가 없었으며, 실질 위험은 이번에 추가한 ⑧이 검사로 덮는다) · DO 블록을 `create unique index` 한 줄로 교체(이미 적용된 마이그의 DDL in-place 변경 = forward-only 위반, 주석의 잘못된 서술만 고침) · "트리거 부작용 0"이 공허하다는 지적(사실이다 — `chat_messages`엔 트리거가 없다. 그러나 `<intent-contract>` 안이라 리뷰가 고칠 수 없는 자리) · 스펙 frontmatter 3중 모순(전부 이 리뷰 실행이 만드는 정상 상태) · 대장 #184·#185의 문구를 고치라는 지적 2건(실질은 타당하나 **이번 실행 지시가 기존 대장 항목 수정을 금지** — 오케스트레이터 소유) · Story 12.5의 last-read NULL 기본값 미정의(12.5 스펙 작성 시 해소, 이 스토리 무관) · **"제3자 seller_id 위조 케이스가 없어 0016 트리거를 지워도 13건 전부 green"** — 전제가 틀렸다. `seeded` 픽스처가 `bogus_seller_id = buyer_id`를 넣고 소유자로 치환됨을 단언하므로, 트리거를 지우면 `0003_chat.sql:33`의 `CHECK (buyer_id <> seller_id)`에 걸려 **setup이 먼저 깨져 파일 전체가 red**가 된다(코드 실측) · AC4를 "데이터가 이미 있는 pre-0022 DB에 ALTER 적용" 경로로 증명하라(두 하네스 모두 빈 DB에서 빌드하는 구조이고 `ADD COLUMN`의 Postgres 보장이라 비용 대비 가치 없음).

**2차 패스 Verification 수행(전부 직접 실행·관찰):**
- `python scripts/check_migrations.py` → **통과**(정적 + 동적 0001~0022 전량 적용 + 프로브 3종 그린).
- `pytest tests/integration/test_chat_idempotency_real_db.py` → **13 passed**.
- `pytest tests/integration` 전체(CI `api-db` 잡과 동일 범위) → **51 passed, 1 failed**. 실패 1건은 `test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls`로, **이 diff가 건드리지 않은 파일**의 기존 red이며 이미 대장 **#138**에 등재돼 있다(`git diff` 무변경으로 확인).
  > **✎ 3차 패스 정정 — 이 줄의 두 주장이 틀렸다.** (a) *"CI `api-db` 잡과 동일 범위"* 가 아니었다. 이 실행은 **로컬 Supabase 스택**(포트 55322)에서 돌았고, 그 스택은 CI와 권한 상태가 다르다 — `has_table_privilege('anon','public.profiles','SELECT')`가 로컬은 **f**, CI 프렐류드 환경은 **t**. (b) 실패를 **#138로 귀속한 것도 틀렸다**. #138이 기록한 증상은 `DID NOT RAISE InsufficientPrivilege`(권한이 **있어서** 에러가 안 나던 것)인데, 로컬의 실제 실패는 정반대인 `InsufficientPrivilege: permission denied for table profiles`(권한이 **없어서** 나는 것)다. 3차 패스가 CI를 실제로 재현해(일회용 `pgvector/pgvector:pg17` + 프렐류드 + 마이그 0001~0022 전량) 다시 돌린 결과는 **53 passed, 0 failed** — CI 환경에는 red가 없다. 대장 **#190**에 실측 등재.
- **red/green 실측 5회** — (1) 제약 이름만 변경 → ⑧만 red, (2) 제약 드롭 → ① red, (3) 0010 CHECK를 `< 2000`으로 조임 → ⑫만 red, (4) 테이블 INSERT 회수 + `client_message_id` 뺀 컬럼별 재부여 → ⑬만 red(나머지 12건 green), (5) 헬퍼를 `DO UPDATE`로 변경 → ①⑩이 본문 단언에서 red. 매회 원복 후 green 재확인.
- **잔여물 0 증명** — 새 커밋 픽스처가 실제 DB에 행을 남기는지 확인하려고 실행 전/후 `auth.users`·`listings`·`chat_rooms`·`chat_messages` 카운트를 직접 셌다: `9|103|5|10` → `9|103|5|10` 동일.

**Residual artifacts (git status 잔여, 커밋 대상 아님):**
- 이 스펙 파일 자신 — `final_revision`을 커밋 완료 후 HEAD 값으로 기록하는 절차상, 그 기록 자체는 그 커밋 이후의 편집이라 구조적으로 매 실행마다 커밋 뒤에 한 줄 남는다(step-04 Finalize 지시 그대로 수행한 결과).

**Residual risks:**
- 로컬 Supabase Docker 스택의 CLI 마이그레이션 이력 정합은 여전히 미확인 — 다만 이번 패스에서 대장 **#187**로 등재해 트리거를 붙였다(지난 패스에선 이 스펙 파일에만 적혀 있었다).
- `authenticated` 표면 검증(⑬)은 `psycopg`로 롤을 흉내낸 것이지 PostgREST/supabase-js를 실제로 통과하지 않는다 — 요청 헤더·에러 코드·반환 모양은 여전히 미검증이며, 이것이 #186의 ② 항목(`.upsert` 반환 모양)이 12.3에서 실측돼야 하는 이유다.
- Story 12.2(realtime broadcast)·12.3(클라이언트 배선)이 이 컬럼·제약을 실제로 소비하기 전까지는, 이번에 놓은 DB 토대가 프로덕션에서 아무 영향도 주지 않는다(의도된 범위 — Never 절 참조). NULL 키 구간에서 중복 방지가 작동하지 않는다는 사실은 이제 테스트 ⑪이 고정하고 있다.

---

## 3차 패스 (후속 리뷰, 2026-07-28)

2차 패스가 `followup_review_recommended: true`(점수 16)로 닫혔기에 **새 세션의 독립 4레이어**로 다시 돌렸다(CLAUDE.md B4). 마이그레이션은 DDL·주석 모두 **한 글자도 안 바뀌었다** — 이미 적용된 마이그를 in-place로 고치는 것은 forward-only 위반이다. 이번 패스의 변경은 **검증 환경·테스트 커버리지·주석/기록의 사실관계** 세 축에만 들어갔다.

**핵심 발견(medium 1건):** 지난 두 패스가 *"CI `api-db` 잡과 동일 범위"* 라며 검증한 것은 **로컬 Supabase 스택**이었고, 그 스택은 CI와 권한 상태가 다르다. 거기서 난 실패 1건을 *"이미 대장 #138에 등재된 기존 red"* 로 넘겼는데, **증상이 정반대**였다 — #138은 `DID NOT RAISE InsufficientPrivilege`(권한이 있어서 에러가 안 남), 로컬 실패는 `permission denied for table profiles`(권한이 없어서 남). 즉 "알려진 red"라고 넘긴 신호가 실제로는 *검증 환경이 CI가 아니다* 라는 별개 사실이었다. CI를 실제로 재현해 다시 돌리자 **red는 없었다**.

**추가된 파일 변경:**
- `api/tests/integration/test_chat_idempotency_real_db.py` — 13건 → **14건**. 신규 ⑭(제3자 seller_id 위조를 트리거가 실소유자로 덮는지) + `_create_user`의 `role` 단언 + ⑩의 "방 전체 행 수" 단언 + 헤더 ⑭ 항목.
- `.github/workflows/tests.yml` — `api-db` 주석의 사실관계 3건 정정(픽스처 이름·누락 파일·이메일 유일성), 목록 대신 확인 명령을 적는 방식으로 전환.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Epic 11 과거 기록 줄의 무관한 공백 삭제 원복.
- `docs/tech-debt.md` — defer 2건을 **신규 #189·#190으로만** 등재(기존 항목 무수정 — 이번 실행 지시).
- 이 스펙 파일 — 상단 요약의 건수 정정 + 2차 패스 Verification 줄의 잘못된 귀속 정정.

**Follow-up review recommendation:** `true`. patch 7건(high 0, **medium 1**, low 6) → 점수 = 3×1 + 1×6 = **9 ≥ 5**. 다만 medium 1건은 *검증 환경* 결함이었고 이번 패스가 그 환경을 CI 재현으로 바꿔 해소했으므로, 다음 패스의 기대 수확은 앞선 두 패스보다 낮다.

**3차 패스 Verification 수행(전부 직접 실행·관찰, CI 재현 환경):**
- **CI 재현 하네스 구성** — 일회용 `pgvector/pgvector:pg17` 컨테이너(포트 55444)에 `scripts/migration-check-prelude.sql` → `supabase/migrations/*.sql` 0001~0022 번호순 전량 적용. 권한 실측으로 CI 동등성 확인: `has_table_privilege('anon','public.profiles','SELECT')` = **t**(로컬 스택은 f), `has_table_privilege('authenticated','public.chat_messages','INSERT')` = **t**.
- `pytest tests/integration` 전체 → **53 passed, 0 failed**(패치 후 재실행도 동일).
- `python scripts/check_migrations.py` → **통과**(정적 + 동적 0001~0022 전량 적용 + 프로브 3종 그린).
- **red/green 실측 3회** — (1) 0016 트리거를 "자기충돌만 고치는" 형태로 퇴화 → **⑭만 red**(나머지 13 green), 원복 후 14 green. (2) 0001 가입 트리거가 role 메타데이터를 무시하도록 퇴화 → **14건 전부 setup에서 red**(`buyer != seller`), 원복 후 green. (3) 재전송이 키 없는 행을 하나 더 남기는 누수를 헬퍼에 심음 → **⑩ red(3 ≠ 1)**, 그리고 **같은 누수 조건에서 새 단언만 제거하면 ⑩ green** — 패치가 잡는 것을 패치 전 버전은 못 잡았음을 양방향으로 확인.
- 실험에 쓴 컨테이너는 종료·삭제했고, 로컬 Supabase 스택(55322)은 건드리지 않았다.

**Reject 13건**(요지): 마이그레이션의 `add column if not exists`가 스펙 Block If를 어긴다 + 타입 드리프트 `raise exception` 가드 요구(Block If는 착수 시점 사전조건이고 실제 드리프트가 없었으며, 1·2차 패스가 같은 이유로 이미 두 번 기각) · ⑧에 `conkey` 기반 중복 제약 카운트 추가(2차 패스 기각 유지 — 이름 변경은 fresh DB에서 ⑧이 실제로 잡는다) · 재적용 멱등 가드가 검사되지 않음(이미 대장 **#143**) · 이 브랜치가 CI를 지난 적 없음(이미 대장 **#181**, 이번 패스가 CI를 재현해 대신 검증) · `= %s`와 `IS NOT DISTINCT FROM` 혼용(해당 3곳은 NULL을 넘기지 않으므로 결함이 아니다) · ⑬의 f-string 보간(형제 `test_view_count_rpc_real_db.py`에 7곳 있는 **이 레포의 기존 관례**다 — 새 파일이 어긴 게 아니라 따른 것) · psycopg3 `transaction()`이 IDLE 커넥션에서 커밋한다는 잠복 위험(픽스처가 yield 전에 반드시 쓰므로 현재 도달 불가, A2) · ⑬에 GRANT 사전조건 skip 가드 추가(진짜 회귀를 숨기게 된다) · `seeded_committed`의 `_create_user`가 assert 실패 시 커밋된 행을 남길 수 있음(가입 트리거가 이미 깨진 경우에만 발생하고 uuid 이메일이 잔여물을 흡수한다) · `epic-12-context.md`의 "CI 게이트가 강제한다"가 #185와 모순(게이트는 번호·self-containment를 실제로 강제한다 — #185는 *동적 프로브*가 chat을 안 본다는 다른 층 얘기다) · AC4를 "데이터 있는 pre-0022 DB에 ALTER" 경로로 증명(2차 패스 기각 유지) · "트리거 부작용 0"이 공허하다(사실이나 `<intent-contract>` 안이라 리뷰가 못 고치는 자리).

**Residual artifacts (git status 잔여, 커밋 대상 아님):** 이 스펙 파일 자신 — `final_revision`을 커밋 후 HEAD로 적는 절차상 구조적으로 매 실행마다 커밋 뒤 한 줄 남는다.

**Residual risks:**
- CI가 이 작업을 **여전히 한 번도 본 적이 없다**(대장 #181). 이번 패스는 CI 잡을 로컬에서 *재현*했을 뿐이고, 실제 GitHub Actions 실행은 `develop` 병합(사용자 승인 사항)이 있어야 일어난다.
- `authenticated` 표면 검증(⑬)은 여전히 `psycopg`로 롤을 흉내낸 것이지 PostgREST/supabase-js를 통과하지 않는다 — 대장 #133·#186의 축 그대로.
- 로컬 Supabase 스택(55322)의 마이그레이션 이력 정합(#187)과 GRANT 공백(#190)은 그대로 남아 있다. **이 스택으로 `api-db` 잡을 대신 검증하면 안 된다**는 것이 이번 패스의 실측 결론이다.
