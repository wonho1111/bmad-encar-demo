---
title: '17.2 조회수 옆문 차단 + 쓰기 경로 전수조사를 실행되는 검사로'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: 'b47316abe73e04e53b734f2cf71a85589580ef26'
final_revision: '0b77236fae277066c4bf5a7bf16360fad84073d0' # 이 줄 자체는 다음 커밋에 기록
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-17-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-17-1-정지-회원-쓰기-차단-rls.md'
---

<intent-contract>

## Intent

**Problem:** 17.1이 정지 회원의 쓰기를 막았는데 **두 가지가 남았다.**

1. **정문은 잠갔는데 옆문 하나가 열려 있다.** `public.increment_listing_view(uuid)`(0020)는
   SECURITY DEFINER라 RLS를 통째로 우회하고, 본문이 `public.listings`를 UPDATE한다.
   **오케스트레이터가 로컬 55322에서 직접 재현했다(2026-08-11, 트랜잭션 롤백):**
   같은 정지 회원 세션에서
   - `update public.listings set price=... where id=<X>` → **0행** (17.1이 막는다 ✅)
   - `select public.increment_listing_view('<X>')` → `view_count` **0 → 1** (뚫린다 ❌)
   - 참고로 `set local role anon`에서도 1 → 2로 증가 — **이 경로는 계속 살아 있어야 한다**(FR58, 비로그인 상세 열람).

   17.1의 불변식은 *"정지 계정은 **매물**·사진·파일·관리자 RPC 어느 경로로도 쓰기를 성공시킬 수
   없다"* 였고 `view_count`는 `public.listings`의 컬럼이다. 즉 **스토리가 스스로 내건 약속의 구멍**이다.
   17.1이 "안 막는다"로 판정하며 적은 사유는 *"anon도 호출하므로 `profiles` 신원 자체가 없는
   호출자가 있다"* 인데 — 그건 **anon에 게이트를 걸기 어렵다**는 사실이지 **authenticated인 정지
   회원을 통과시켜야 할 이유가 아니다**([[DW-805]]).

2. **"무엇을 막고 무엇을 안 막는가"라는 결론이 전부 산문이다.** 17.1은 `pg_policies`·`pg_proc`
   실측으로 21개 정책 + 11개 SECURITY DEFINER 함수 전량에 판정을 붙였지만, 그 판정을 강제하는
   **실행되는 검사가 0건**이다. 새 마이그레이션이 `authenticated` 대상 non-SELECT 정책을
   추가하면서 정지 조건도 안 걸고 판정도 안 적어도 **아무것도 red가 되지 않는다**([[DW-803]]).
   이게 가설이 아니라는 증거: 17.1의 손으로 센 숫자가 **실제로 틀렸고**(막는다 15→16, 안 막는다
   6→5) 합계만 우연히 21로 맞아 자기검사를 통과했다. 2차 리뷰가 `pg_policies` 재실측으로 잡았다.

**Value:** (1) 정지된 사람이 **아무 매물의 조회수나 계속 부풀릴 수 있다.** 조회수는 **다른 사용자에게
보이는 값**(목록 인기순 정렬 · 상세 표시)이라, 찜([[DW-801]])·안읽음 커서([[DW-802]])를 면제할 때 쓴
기준(*"본인만 보는 개인화 데이터"*)이 여기엔 성립하지 않는다. 같은 전수조사 안에서 기준이 갈린다.
(2) 그 전수조사 결론의 완전성이 **다음 마이그레이션 한 줄에 조용히 깨진다.** CLAUDE.md B9가 정확히
이 상황을 지목한다 — *"주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다."*

**두 항목을 한 스토리로 묶은 이유(오케스트레이터가 정한 게 아니라 대장이 지정했다):**
[[DW-805]]의 `trigger:`가 *"…또는 [[DW-803]]의 전수조사 강제 검사를 만드는 스토리에서 — 그 검사가
이 항목의 판정을 기계가 읽는 형태로 옮길 때 함께 결정한다"* 고 적혀 있다. DW-805는 "막는다"로
판정을 뒤집는 일이고, DW-803은 그 판정 전체를 기계가 읽게 만드는 일이다. 따로 하면 매니페스트를
두 번 고쳐야 하고, 그 사이에 두 정본이 어긋난다.

## Boundaries & Constraints

**Always:**

- **불변식을 먼저 못박는다:**
  *"`profiles.status='suspended'`인 계정은 `public.listings`에 **어떤 경로로도** 쓰기를 성공시킬 수
  없다 — RLS 정책이든 SECURITY DEFINER 함수든. 반대로 **비로그인(anon)의 조회수 증가는 지금과
  똑같이 동작한다.**"*
  뒷문장이 앞문장만큼 중요하다. 비로그인을 같이 막으면 FR58(비로그인 상세 열람)의 조회수 집계가
  죽고, 그건 이 스토리가 만든 회귀다.

- **`increment_listing_view`의 가드는 함수 본문 안에 둔다.** 이 함수는 SECURITY DEFINER라
  RLS가 대신 걸러 주지 않는다 — `docs/conventions.md` §6의 "SECURITY DEFINER 함수 축" 항목이
  같은 성질을 이미 문서화했다(*"함수 본문의 인라인 조건이 유일한 강제 지점"*). 0019
  `get_seller_public_summary`·0030 `admin_restore_sold_listing`과 **같은 형태**로 쓴다.

- **anon 통과를 "우연"이 아니라 "설계"로 만든다.** `auth.uid()`가 NULL이면 `not exists(...)`가
  참이 되어 통과하는데, 이건 SQL의 부수효과가 아니라 **의도**다. 각주에 그 의도를 적고,
  **검사로도 고정한다**(비로그인 호출이 성공하는 단언). 안 적으면 다음 사람이 "NULL 처리가
  빠졌다"고 판단해 `coalesce`를 붙여 비로그인을 막는다.

- **매니페스트는 판정을 옮기는 것이지 새로 만드는 게 아니다.** 정본은 `docs/conventions.md` §8이고
  (project-context 규칙 1 — "값은 한쪽에만 산다"), 매니페스트는 `0032` 9절의 판정을 **기계가 읽는
  형태로 옮긴 사본**이다. 세 곳(§8 · `0032` 9절 · 매니페스트)의 항목 집합이 어긋나면 그 자체가
  결함이다 — 검사가 그 어긋남도 잡아야 한다.

- **매니페스트 검사는 "목록에 없는 게 나오면 실패"여야 한다.** 화이트리스트 대조다. *"정지 조건이
  걸린 정책이 N개 이상"* 같은 하한 검사로 쓰지 않는다 — 그건 새 정책이 추가돼도 계속 통과한다.
  실측 쿼리는 `0032` 9절이 쓴 것을 그대로 재사용한다:
  `select schemaname, tablename, policyname, cmd from pg_policies where cmd <> 'SELECT' and 'authenticated' = any(roles)`
  + `select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.prosecdef and n.nspname='public'`

- **새 인프라를 만들지 않는다(A2).** 검사는 `api/tests/integration`에 pytest 한 건으로 만든다 —
  `api-db` CI 잡이 실제로 돌리는 자리이고, 실 Postgres가 이미 붙어 있다. 매니페스트 전용 파일
  포맷(YAML 파서 등)을 새로 도입하지 않는다. 검사 파일 안의 파이썬 자료구조로 충분하다.
  ⚠️ `scripts/check_migrations.py`의 `PROBES`에 넣는 선택지도 있지만(대장 fix_sketch가 제시),
  그 배열은 `(라벨, 단일쿼리, 기대문자열)` 3튜플이라 **집합 대조를 표현할 수 없다.** 굳이 넣으려면
  구조를 바꿔야 하는데 그건 이 스토리가 요청받은 범위 밖이다 — pytest 쪽을 택하고 **왜 그쪽인지
  근거를 Design Notes에 남긴다**(다음 사람이 같은 선택지를 다시 조사하지 않게).

- **red를 두 가지 방식으로, 서로 다른 표기로 증명한다**(CLAUDE.md B4 · 메모리
  `guard-proof-must-vary-shape` — 자기가 쓴 표기로만 깨면 그 검사가 실제로 무엇을 보는지
  증명되지 않는다):
  - 조회수 축: ⓐ 가드 조건 자체를 지운다 ⓑ 가드는 두되 조건을 `= 'active'`처럼 **반대 의미**로
    바꾼다 — ⓑ는 비로그인 통과 단언이 red가 되어야 한다(anon은 `profiles` 행이 없으므로).
  - 매니페스트 축: ⓐ 매니페스트에서 항목 하나를 지운다(실측엔 있는데 목록엔 없음 → red)
    ⓑ **새 정책을 실제로 하나 만들어** 본다(임시 마이그레이션 → red 확인 → 원복).
    ⓑ가 이 검사의 진짜 임무다 — ⓐ만으로는 "매니페스트 편집을 잡는다"까지만 증명된다.

- **프로브 원복은 백업본으로 한다**(메모리 `probe-revert-never-git-checkout`).
  `git checkout`은 커밋 안 된 다른 패치까지 날린다(이 레포에서 실제로 발생).

- **기대값을 피검사 대상에서 다시 계산하지 않는다**(메모리 `self-consistent-assertions-never-fail`).
  정책 이름·함수 이름·`'suspended'`·`'active'`는 **글자 그대로 박는다.** `0032`에서 읽어 오거나
  `pg_policies` 결과로 기대값을 만들면 무엇을 넣어도 green이 된다.

- **검사 옆에 "이 검사가 안 보는 것"을 실측해서 적는다**(Epic 13 회고 약속).
  최소한 이건 사실이므로 반드시 포함한다: 이 매니페스트 검사는 `cmd <> 'SELECT'`이고
  `'authenticated' = any(roles)`인 정책만 본다 — **`anon`·`ai_readonly` 전용 쓰기 정책이 생기면
  안 보인다.**

- 끝나면 [[DW-805]]·[[DW-803]]을 `resolution:`과 함께 done으로 닫는다(CLAUDE.md B8).

**Block If (멈추고 escalate):**

- 조회수 가드가 **비로그인 호출을 막는다**는 것이 실측으로 확인되고 우회 형태를 못 찾으면 — FR58과
  정면 충돌이므로 멈추고 묻는다.
- 매니페스트 대조 검사가 **로컬과 CI에서 서로 다른 정책 집합**을 본다는 것이 확인되면 멈추고 묻는다
  (플랫폼 기본 정책·프렐류드 차이 때문일 수 있다 — 그 경우 검사의 기준선 자체를 사용자가 정해야 한다).

**Never:**

- **`increment_listing_view`의 시그니처·반환형·호출 지점을 바꾸지 않는다.** 웹 상세 서버
  컴포넌트가 부르는 계약 그대로 둔다. 본문 안 조건 추가만 한다.
- **anon의 `execute` GRANT를 회수하지 않는다.** 그건 조회수 집계를 통째로 끄는 것이고, 이 스토리가
  요청받은 게 아니다.
- **기존 마이그레이션 파일을 수정하지 않는다.** 새 번호(`0034` 이후)로 추가한다
  (CLAUDE.md B3 · conventions §9.1). `create or replace function`은 §9.1이 허용한 전진 패턴이다.
- **`0032`의 정책을 다시 손대지 않는다.** 이 스토리는 함수 하나 + 검사 하나다.
- **판정을 "안 막는다"로 유지하는 선택을 조용히 하지 않는다.** 대장 fix_sketch가 그 선택지도
  열어 뒀지만(*"조회수는 불변식 밖"*), 위 Value가 반대 근거를 실측으로 들었다. 뒤집으려면
  **왜 조회수는 찜·안읽음과 같은 범주인지**를 실측으로 보이고 Design Notes에 적는다.
- **화면·앱 코드를 건드리지 않는다.** 이 스토리는 DB + 검사다.
- **운영(`main`) 배포·원격 DB 적용을 하지 않는다.** 로컬 검증까지만 — 원격 적용은 사용자 승인
  사안이다(CLAUDE.md B3).

</intent-contract>

## Code Map

- `supabase/migrations/0020_listings_view_count.sql:37-54` -- `increment_listing_view(uuid)` 원본.
  `language sql` · `security definer` · `set search_path = ''` · 본문은
  `update public.listings set view_count = view_count + 1 where id = p_listing_id`.
  `revoke all ... from public` 후 `grant execute ... to anon, authenticated`. **이 GRANT 구성을 보존한다.**
- `supabase/migrations/0020_listings_view_count.sql:142-175` -- `listings_set_timestamps()` 트리거.
  `view_count`가 바뀐 UPDATE에서는 `updated_at`을 갱신하지 않는다. **가드가 UPDATE를 0행으로
  만들면 트리거는 애초에 안 돈다** — 이 축에 회귀가 없음을 확인만 하고 건드리지 않는다.
- `supabase/migrations/0032_suspended_write_block.sql:359-` -- 9절 전수조사 판정 전문(21정책 + 11함수).
  매니페스트가 옮겨 담을 원본이자, `increment_listing_view` 판정("해당 없음 — anon도 호출")이
  적혀 있는 자리. **판정이 바뀌므로 이 주석도 새 마이그레이션에서 갱신 표기가 필요하다**
  (기존 파일 수정 금지 → 새 파일 각주에 "0032 9절의 이 판정을 뒤집는다 + 이유"를 적는다).
- `supabase/migrations/0019_seller_public_summary.sql` -- SECURITY DEFINER 함수 안에 인라인 조건을
  두는 기존 패턴. 새 가드의 형태를 여기 맞춘다.
- `supabase/migrations/0030_listings_restore_sold_rpc.sql` -- 같은 패턴(`where ... and public.is_admin_active()`).
- `docs/conventions.md` §6 "SECURITY DEFINER 함수 축" -- 소비처 목록. `increment_listing_view`가
  **비노출(FR11) 축으로는 여기 없다** — 조회수는 노출이 아니라 쓰기라서. 이 스토리가 §8 쪽에
  등재한다. 규칙7("새 조회 경로를 열면 목록에 강제 지점을 추가")의 쓰기판.
- `docs/conventions.md` §8 -- 정지의 의미 정본. "막지 않는 쓰기" 목록에서 `increment_listing_view`가
  **빠지고** "막는 쓰기"로 이동한다. 매니페스트와 항목 집합이 일치해야 한다.
- `docs/conventions.md` §9.1 -- 마이그레이션 전진 전용 규칙(근거 주석 의무).
- `api/tests/integration/test_suspended_write_block_real_db.py` -- 17.1이 만든 실DB 검사 167건.
  `_as()`·`_create_user`·`_insert_listing`·`_suspend` 헬퍼를 그대로 재사용한다.
  ⚠️ `_insert_listing`은 `body_type='중형차'` 등 **CHECK 제약을 통과하는 값**을 쓴다 — 직접 INSERT를
  새로 쓰지 말고 이 헬퍼를 쓴다(오케스트레이터가 임의 값 `'세단'`으로 재현하다 CHECK로 두 번 실패).
- `api/tests/integration/conftest.py` -- `_DSN`·`pytestmark`·픽스처. 새 검사 파일도 같은 관례.
- `scripts/check_migrations.py:61-77` -- `PROBES` 3튜플 구조(라벨/단일쿼리/기대문자열). 집합 대조를
  못 담는다는 근거의 출처.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-805]]·[[DW-803]] 항목.
  관련 항목 [[DW-801]]·[[DW-802]]·[[DW-799]](같은 전수조사의 다른 "안 막는다" 판정 — **이 스토리는
  이 셋의 판정을 바꾸지 않는다**, 매니페스트에 "안 막는다"로 그대로 옮긴다).

## Tasks & Acceptance

**Execution:**

- `supabase/migrations/0034_view_count_suspended_guard.sql` -- NEW.
  `create or replace function public.increment_listing_view(uuid)` — 기존 본문의 UPDATE에
  정지 회원만 거르는 조건을 더한다. 형태 예시(그대로 쓸 필요는 없으나 **anon 통과가 보장돼야 한다**):
  ```sql
  update public.listings set view_count = view_count + 1
   where id = p_listing_id
     and not exists (
       select 1 from public.profiles
        where id = auth.uid() and status = 'suspended'
     );
  ```
  · `security definer` · `set search_path = ''` · `language sql` 을 **그대로 보존**한다.
  · `create or replace`가 GRANT를 유지하는지 **실측으로 확인**하고, 유지되지 않으면 `revoke/grant`를
    다시 적는다(추론하지 말고 재본다 — 확인 결과를 각주에 남긴다).
  · 각주에 남길 것: ① 왜 `not exists`(비로그인 통과가 의도)인지 ② `0032` 9절의 "해당 없음(anon도
    호출)" 판정을 왜 뒤집는지 ③ 이 함수가 SECURITY DEFINER라 RLS가 대신 안 막는다는 사실.
- `docs/conventions.md` §8 -- `increment_listing_view`를 "막지 않는 쓰기" 목록에서 빼고 "막는 쓰기"에
  등재한다. §6의 "SECURITY DEFINER 함수 축" 소비처 목록에도 **쓰기 항목으로** 추가한다
  (§6 말미가 *"정의자 함수는 조회뿐 아니라 쓰기 경로도 이 목록에 올린다"* 고 이미 요구한다).
  강제 장치(테스트 파일명)를 같은 줄에 적는다 — §6의 다른 항목들과 동일한 형식.
- `api/tests/integration/test_write_policy_manifest_real_db.py` -- NEW. 매니페스트 + 대조 검사.
  · 매니페스트: `authenticated` 대상 non-SELECT 정책 전량과 `public` 스키마 SECURITY DEFINER 함수
    전량을 **이름 → 판정("blocked"/"exempt") + 사유 한 줄**로 담는다. 값은 `0032` 9절에서 옮기되
    `increment_listing_view`만 `exempt` → `blocked`로 바뀐다.
  · 검사 ①: 실측 집합과 매니페스트 키 집합이 **정확히 일치**(양방향 차집합이 둘 다 비어야 한다).
    실측에 있는데 매니페스트에 없으면 → "새 쓰기 경로에 판정이 없다"로 실패.
    매니페스트에 있는데 실측에 없으면 → "지워진 정책이 목록에 남았다"로 실패.
  · 검사 ②: `blocked`로 표시된 정책은 정의문에 정지 판정식이 실제로 들어 있는지 확인한다
    (`pg_policies.qual`/`with_check` 또는 `pg_get_functiondef`에 `is_admin_active` 또는
    `status = 'active'` 또는 `status = 'suspended'` 중 하나가 나타나는지). **⚠️ 이건 문자열 검사라
    약하다** — `docs/conventions.md` §6이 이미 같은 함정을 기록해 뒀다(`(status='on_sale' OR true)`로
    무력화해도 문자열 검사는 계속 초록). 그래서 **행위 검사(아래 AC의 실제 쓰기 시도)가 본체이고
    이 검사는 "판정 누락"만 잡는 보조**라는 것을 파일 헤더에 명시한다.
  · 파일 헤더에 "이 검사가 안 보는 것"을 실측해서 적는다(위 Always 마지막 항목 포함).
- `api/tests/integration/test_suspended_write_block_real_db.py` -- 조회수 축 검사를 추가한다
  (기존 파일에 붙인다 — 같은 관심사, 같은 헬퍼. 새 파일을 만들지 않는다).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-805]]·[[DW-803]]을 `resolution:`과
  함께 done. [[DW-801]]·[[DW-802]]·[[DW-799]]는 **열어 둔 채** `trigger:`에 "매니페스트가 이 판정을
  기계가 읽는 형태로 담았다"는 사실을 덧붙인다(판정이 바뀐 게 아니라 형태만 바뀌었다).

**Acceptance Criteria:**

- Given `profiles.status='suspended'`인 회원 세션과 타인의 `on_sale` 매물, when
  `public.increment_listing_view(그 매물 id)`를 호출, then `view_count`가 **증가하지 않는다**(호출
  전후 값이 같다). 함수는 예외를 던지지 않아도 된다(0행 UPDATE).
- **(비로그인 회귀 — 이게 없으면 "전부 막힘"과 구별 불가)** Given `set local role anon` 세션과
  `on_sale` 매물, when `increment_listing_view`를 호출, then `view_count`가 **정확히 1 증가**한다.
- **(활성 회원 회귀)** Given `status='active'`인 로그인 회원, when 같은 호출, then `view_count`가
  **정확히 1 증가**한다.
- Given 정지된 회원이 **자기 매물**의 조회수를 올리려는 경우, when `increment_listing_view` 호출,
  then 증가하지 않는다(소유 여부와 무관 — 정지는 행위자 기준이다).
- **(트리거 회귀)** Given 활성 회원의 정상 조회수 증가, when 호출 후, then `updated_at`이
  갱신되지 않고 `created_at`도 불변(0020의 `listings_set_timestamps()` 계약 유지).
- Given `pg_policies`에서 실측한 `authenticated` 대상 non-SELECT 정책 집합, when 매니페스트 키
  집합과 대조, then **양방향 차집합이 모두 비어 있다**.
- Given `pg_proc`에서 실측한 `public` 스키마 SECURITY DEFINER 함수 집합, when 매니페스트 키 집합과
  대조, then **양방향 차집합이 모두 비어 있다**.
- **(검사가 진짜로 잡는지 — red 증명 ⓑ)** Given 매니페스트에 없는 새 `authenticated` 대상 쓰기
  정책을 임시 마이그레이션으로 하나 추가, when 매니페스트 검사를 실행, then **실패한다.**
  원복 후 다시 통과. (증명 로그를 Design Notes에 남긴다.)
- **(red 증명 ⓐ)** Given `0034`의 가드 조건을 제거한 판, when 조회수 검사를 실행, then 정지 회원
  단언이 실패한다. Given 조건을 `status = 'active'`로 뒤집은 판, when 실행, then **비로그인 단언**이
  실패한다(서로 다른 단언이 red가 되는 것까지 확인 — 같은 단언만 계속 red면 한 축만 증명된 것이다).
- Given 전체 실DB 통합검사(`api/tests/integration`), when 실행, then **17.1 기준 167건이 전부 계속
  통과**하고 새 검사가 추가된 상태로 green(회귀 0건).
- Given `python scripts/check_migrations.py`, when 실행, then 마이그레이션 게이트 통과.
- Given `docs/conventions.md` §8과 매니페스트, when 두 목록의 항목 집합을 비교, then 일치한다
  (문서와 검사가 어긋나면 그 자체가 결함 — 사람이 눈으로 대조하고 결과를 Design Notes에 적는다).

## Design Notes

- **GRANT 유지 실측**: `create or replace function public.increment_listing_view(uuid)`(0034) 적용
  전후로 `anon`·`authenticated`의 EXECUTE 권한을 롤백 트랜잭션 안에서 직접 비교 — **동일하게 유지됨**
  (`create or replace`는 함수 시그니처가 같으면 GRANT를 보존한다는 Postgres 동작이 그대로 확인됨).
  별도 `revoke/grant` 재적용 불필요.
- **매니페스트를 pytest에 둔 근거**: `scripts/check_migrations.py`의 `PROBES`는
  `(라벨, 단일쿼리, 기대문자열)` 3튜플이라 "정책 집합 전체가 매니페스트와 정확히 일치"라는
  **양방향 집합 대조**를 표현할 수 없다(기대문자열 하나로는 21+11개 항목의 존재/누락을 동시에
  못 잡는다). `check_migrations.py`가 나은 점은 마이그레이션 파일 자체의 정적 구조(번호 밀집 등)를
  보는 용도로는 여전히 적합하다는 것 — 이번 검사가 보는 대상(런타임 `pg_policies`/`pg_proc` 상태)과
  범주가 다르다.
- **red 증명 ⓐ·ⓑ 실행 로그**:
  - 조회수 축 ⓐ(가드 조건 제거): 정지 회원 단언 2건(`test_suspended_member_cannot_bump_view_count`,
    `test_suspended_member_cannot_bump_own_listing_view_count`)이 실패, 나머지는 계속 green.
    가드 복원 후 재확인 → 176/176 green.
  - 조회수 축 ⓑ(조건을 `status='active'`로 반전): 비로그인 단언
    (`test_anon_view_count_still_increments`)이 실패(anon은 `profiles` 행이 없어 `exists`가
    항상 거짓) — 정지 회원 단언은 이 형태에서도 우연히 통과하지 않고 여전히 의도대로 막힘.
    서로 다른 단언이 각각 red가 된 것을 확인. 원복 후 green.
  - 매니페스트 축 ⓐ(항목 하나 삭제): 매니페스트에서 `wishlists_insert_own` 삭제 →
    "실측에 있는데 매니페스트에 없다" 실패 메시지로 정확히 죽음. 백업본으로 원복 후 green.
  - 매니페스트 축 ⓑ(실제 정책 신설): 임시 정책 `wishlists_update_own_probe_dw803`을 로컬 DB에
    실제로 만들어 매니페스트 검사 실행 → 같은 형태("매니페스트에 없다")로 실패, 정책 DROP 후
    전체 스위트 재확인 → green. 이 형태가 검사의 진짜 임무(매니페스트 편집이 아니라 **실제 DB
    변경**을 잡는지)를 증명한다.
- **이 검사가 안 보는 것**(실측):
  - 매니페스트 검사는 `cmd <> 'SELECT'`이고 `'authenticated' = any(roles)`인 정책만 본다 —
    `anon`·`ai_readonly` 전용 쓰기 정책이 새로 생기면 이 검사엔 보이지 않는다.
  - `blocked`로 표시된 정책의 판정식 검증은 `pg_policies.qual`/`with_check`·`pg_get_functiondef`
    문자열에 특정 패턴이 있는지만 보는 **문자열 검사**라, `(status='on_sale' OR true)`처럼 조건을
    무력화해도 문자열 검사 자체는 계속 통과할 수 있다(`docs/conventions.md` §6이 이미 기록한
    같은 함정). 그래서 이 검사는 "판정 누락"만 잡는 보조이고, 실제 차단 여부는 위 행위 검사
    (조회수 축 등)가 본체다.

## Review Triage Log

<!-- Append-only. 첫 리뷰 패스 전까지 비움. -->

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (low 3low)
- defer: 1 (low 1low)
- reject: 6 (low 6low)
- addressed_findings:
  - `[low]` `[patch]` `api/tests/integration/test_write_policy_manifest_real_db.py`의 `_fetch_policies()` 실측 쿼리(`'authenticated' = any(roles)`)가 `TO authenticated` 절 없이 만든 정책(Postgres가 `roles={public}`로 기본 배정, `authenticated`도 그 일원이라 여전히 적용됨)을 못 본다 — DW-803이 막으려는 실패 모드가 검사 자신에게서 한 단계 위로 재현. `roles && '{authenticated,public}'::name[]`로 넓히고 실측(21건, 추가 없음) 확인, 헤더의 "안 보는 것" 문구 정정.
  - `[low]` `[patch]` `supabase/migrations/0034_view_count_suspended_guard.sql:22`의 "빠뜨린 코alesce"가 한/영이 섞인 오탈자 — 비로그인 조회수 경로를 지키는 핵심 경고 문장 안이라 "빠뜨린 coalesce"로 정정.
  - `[low]` `[patch]` 같은 테스트 파일 헤더의 "`public` 스키마만 본다" 문구가 파일 전체에 적용되는 것처럼 읽히나 실제로는 `_fetch_functions`에만 해당(`_fetch_policies`는 스키마 제한 없음, `storage.objects` 4건 포함) — 문구를 두 함수로 나눠 정정.
- 재검증: `cd api && pytest tests/integration -q` 176 passed(회귀 0) · `python scripts/check_migrations.py` 게이트 통과.
- reject 6건(근거는 각 리뷰 서브에이전트 원문 참조):
  - exempt 항목(정책 5건·함수 7건)의 정의문 내용이 검사되지 않는다는 지적 2건 — 스펙 Task가 검사②를 "blocked 항목의 정의문만" 보도록 명시적으로 좁혔다(불변식이 요구하는 건 blocked 경로가 실제로 막히는가이지 exempt 항목의 내용 불변이 아님). 검사①(키 집합 대조)이 이름 변경·삭제는 여전히 잡는다.
  - `increment_listing_view`가 `not exists(suspended)`(부정형)를 쓰는 게 다른 정책들의 `exists(active)`(긍정형)와 다르다는 지적 — 스펙 Always 절이 이 정확한 부정형을 **비로그인 통과를 위해 명시적으로 지정**했다(긍정형을 쓰면 anon 호출이 `profiles` 행 부재로 막혀 FR58이 깨진다). 스펙이 의도한 설계.
  - `0032`에 남은 "해당 없음(anon도 호출)" 판정이 이번 스토리로 뒤집혔는데 `0032` 안에 정정 포인터가 없다는 지적 — 스펙 Never 절이 "기존 마이그레이션 파일을 수정하지 않는다"를 명시했다. `0034`가 배경 설명을 충분히 담았고 `docs/conventions.md`·`deferred-work.md`가 정정을 기록하므로 대체 경로가 이미 있다.
  - red 증명 ⓑ(임시 정책 생성→확인→드롭)이 diff에 재현 가능한 형태로 안 남았다는 지적 — 스펙 Always 절이 "임시 마이그레이션 → red 확인 → 원복"을 명시적으로 요구했다(프로브를 남기지 않는 것 자체가 스펙 준수).
  - 세 표면(§8 산문·`0032` 9절 주석·매니페스트)의 일치를 검사가 아니라 사람이 눈으로 대조한다는 점이 intent-contract의 상위 Always 문구("검사가 그 어긋남도 잡아야 한다")와 다소 어긋나 보인다는 관찰 — 스펙의 구체적인 Task·AC 절이 "사람이 눈으로 대조하고 결과를 Design Notes에 적는다"로 이미 명시적으로 좁혀 뒀고, 테스트 파일 헤더도 동일하게 스스로 그 경계를 선언한다. 구현이 더 구체적인 지시를 따른 것으로 판단.
- defer 1건: 이번 세션은 로컬 55322(기존 DB에 순차 적용)와 `check_migrations.py`(신선한 도커, 전 마이그레이션 재적용)로만 검증했고, 스펙 Block If가 요구한 "로컬과 CI가 같은 정책 집합을 보는가"는 실제 CI(`api-db` 잡) 실행으로 직접 재확인하지 않았다 — DW-811로 이월(trigger: 다음 CI 통과 시 로그 확인).

## Verification

- `cd api && pytest tests/integration -q` — 전량 green, 회귀 0.
- `python scripts/check_migrations.py` — 게이트 통과.
- red 증명 2축 × 2형태, 각각 원복 후 green 재확인(원복은 백업본으로).
- 로컬 실DB에서 정지/활성/비로그인 3주체 × 조회수 호출을 **직접 실행**해 관찰(존재 확인이 아니라
  작동 확인 — CLAUDE.md B4).

## Auto Run Result

**요약**: 17.1이 남긴 옆문([[DW-805]] — `increment_listing_view` SECURITY DEFINER RPC가 정지
회원의 `listings.view_count` 쓰기를 우회 허용)을 새 마이그레이션 `0034`로 닫고, 17.1의 쓰기 경로
전수조사 판정(21개 정책 + 11개 함수)을 산문에서 실행되는 매니페스트 대조 검사로 옮겼다([[DW-803]]).
코드리뷰 4렌즈(adversarial·edge-case·verification-gap·intent-alignment) 병렬 실행 후 patch 3건
(전부 low)을 반영, defer 1건을 대장에 이월했다.

**변경 파일**:
- `supabase/migrations/0034_view_count_suspended_guard.sql` (신규) — `increment_listing_view`를
  `not exists(auth.uid()가 가리키는 profiles 행이 status='suspended')` 가드로 재정의(시그니처·
  GRANT·anon 통과 보존).
- `api/tests/integration/test_write_policy_manifest_real_db.py` (신규, 4건) — `POLICY_MANIFEST`
  (21)·`FUNCTION_MANIFEST`(11) 화이트리스트 + `pg_policies`/`pg_proc` 양방향 차집합 대조 검사
  2건 + blocked 항목 정의문 마커 보조 검사 2건.
- `api/tests/integration/test_suspended_write_block_real_db.py` — 조회수 축 5건 추가(정지 회원
  차단·자기 매물도 차단·비로그인 회귀·활성 회원 회귀·트리거 회귀).
- `docs/conventions.md` — §6(SECURITY DEFINER 함수 축)·§8(접근 게이트 계약)에서
  `increment_listing_view`를 "안 막는다" → "막는다"로 갱신.
- `_bmad-output/implementation-artifacts/deferred-work.md` — [[DW-805]]·[[DW-803]] `resolution:`과
  함께 done. [[DW-799]]·[[DW-801]]·[[DW-802]]는 open 유지, 매니페스트에 판정이 옮겨졌다는 note만
  추가(판정 자체는 안 바뀜). 코드리뷰 defer 1건으로 신규 [[DW-811]] 등재.

**리뷰 findings 분류(1패스)**:
- intent_gap 0 · bad_spec 0 · **patch 3**(전부 low, 전부 수정) · defer 1(low, [[DW-811]]) ·
  reject 6(low) — 상세는 위 Review Triage Log 참조.

**검증 수행(전부 이 실행이 직접 실행·관찰)**:
- `cd api && pytest tests/integration -q` — **176 passed**(패치 전 167 + 신규 9, 회귀 0).
- `python scripts/check_migrations.py` — 게이트 통과(34개 마이그레이션, 신선한 도커 컨테이너).
- GRANT 유지 실측(재정의 전/후 `has_function_privilege` 동일) — `0034` 각주 참조.
- red 증명 4형태 전부 확인·원복(조회수 축 ⓐ가드 제거 ⓑ조건 반전, 매니페스트 축 ⓐ항목 삭제
  ⓑ실제 정책 신설→드롭) — Design Notes 참조.
- 로컬 3주체(정지·비로그인·활성) 직접 호출로 view_count 증분 관찰.

**잔여 리스크**:
- [[DW-811]] — 이번 검증은 로컬 55322 + `check_migrations.py`(신선한 도커)까지만 했고, 실제
  `api-db` CI 잡 실행으로 로컬·CI가 같은 정책 집합을 보는지는 재확인하지 않았다.
- 매니페스트 검사 ②(정의문 문자열 마커 검사)는 스스로 약하다고 문서화돼 있다 —
  `(status='active' OR true)`식 무력화는 통과할 수 있다. 행위 검사(조회수 축 실호출)가 본체.
- `anon`·`ai_readonly` **전용**(둘 다 아닌) 쓰기 정책은 이번 패치로도 여전히 매니페스트 밖이다
  (현재 0건, 실측 확인) — 코드리뷰 patch로 `authenticated`/`public` 축은 넓혔으나 이 축은 스펙
  Always 절이 이미 명시한 한계라 이번 범위 밖으로 유지.
- 웹·앱 클라이언트 코드는 이 스토리가 건드리지 않았다(Never 절) — `increment_listing_view`가
  실제 상세 페이지 호출 경로에서 정지 회원에게 어떻게 보이는지는 이번 실행이 재보지 않았다.
