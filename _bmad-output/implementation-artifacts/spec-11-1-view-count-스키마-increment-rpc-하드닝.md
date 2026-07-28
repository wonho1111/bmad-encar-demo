---
title: '11.1 view_count 스키마 + increment RPC 하드닝'
type: 'feature'
created: '2026-07-27'
status: 'done'
baseline_revision: '7dc9c950541d23e95f675a07f502610f92c2cf4b'
final_revision: 'c600dcdaf5f5aa6c96e9b213515fe727b09fba2c'
review_loop_iteration: 2
followup_review_recommended: true
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `listings`에 조회수 컬럼이 없어 "인기 매물" 정렬(Story 11.4)을 만들 수 없고, 컬럼을 그냥 추가하면 판매자가 자기 매물의 `view_count`를 직접 조작(RLS는 행만 막고 컬럼은 못 막음)할 수 있다.

**Approach:** `listings.view_count int not null default 0` 컬럼 + `increment_listing_view(p_listing_id)` SECURITY DEFINER RPC를 추가하고, 컬럼 직접 UPDATE는 `authenticated`에서 회수해 RPC를 유일한 쓰기 통로로 만든다. 상세 페이지(`/listings/[id]`) 서버 컴포넌트가 매물을 찾은 뒤 이 RPC를 1회 호출한다.

## Boundaries & Constraints

**Always:**
- 마이그레이션 번호는 착수 시 `supabase/migrations/` 실제 파일 목록의 `max+1`로 정한다(계획 문서의 번호는 참고용, 소진돼 있을 수 있다 — 이번 조사 시점 기준 다음 빈 번호는 `0020`이나 착수 시 재확인한다).
- `increment_listing_view`는 `security definer` + `set search_path = ''`(또는 최소 `public` 고정, 함수 안 모든 테이블 참조는 `public.` 스키마 접두를 명시) + `revoke all ... from public` 후 `grant execute ... to anon, authenticated`. `get_seller_public_summary`(`0019_seller_public_summary.sql`)와 동일한 하드닝 패턴을 그대로 따른다(리서치 `research-supabase-viewcount-rpc.md`가 Supabase 메인테이너 권장안과 일치함을 확인함).
- `revoke update (view_count) on public.listings from authenticated;`로 컬럼 단위 직접 쓰기를 막는다 — RLS는 행만 막고 컬럼은 못 막으므로 이게 유일한 방어선(Supabase 공식 문서 인용, 리서치 문서 §2).
- 함수 본문은 "이 id의 view_count를 1 증가"라는 단일 동작만 한다 — 임의 컬럼/값을 받는 범용 UPDATE로 확장하지 않는다.
- RPC 호출은 상세 페이지(`web/src/app/(user)/listings/[id]/page.tsx`)의 매물 확인(`if (!listing)` 통과) **이후 정확히 한 곳**에서만 한다. `ListingCard`·AI 응답 카드 등 목록/카드 렌더링 경로는 절대 이 RPC를 호출하지 않는다 — 이것이 AC의 "AI 카드 렌더링 시 중복 증가하지 않는다"를 만족하는 유일한 방법이다(카드는 순수 표시 컴포넌트이고 데이터 페칭을 하지 않으므로, 이 규칙을 지키는 한 자동으로 성립한다).
- RPC 실패는 `sellerSummaryError`와 동일한 패턴으로 서버 콘솔에만 로그하고 페이지 렌더를 막지 않는다(조회수 증가는 상세 페이지 핵심 기능이 아니다).
- 각 에픽 첫 마이그레이션 스토리는 마이그레이션 게이트(CI, `scripts/check_migrations.py` + `migration-gate.yml`) 통과가 DoD다(conventions.md §9.4) — 이 스토리가 Epic 11의 첫 마이그레이션이다.

**Block If:**
- `supabase/migrations/`의 실제 최신 번호가 조사 시점(`0019`)과 달라 다음 빈 번호가 불분명한 경우 — 없음(착수 시 재확인만 하면 되므로 블로킹 아님, 참고로 남김).

**Never:**
- `view_count`를 `anon`의 컬럼 SELECT 화이트리스트(`0011_listings_anon_select.sql`)에 추가하지 않는다 — 그 목록의 주석이 명시하듯 "컬럼 추가해도 anon엔 기본적으로 안 보이는 것이 의도된 동작"이며, 실제 노출(인기 그리드)은 Story 11.4의 몫이다.
- 상세 페이지에 조회수 표시 UI를 추가하지 않는다(AC는 증가만 요구, 표시는 11.4 그리드 범위).
- `increment_listing_view`에 rate limit·세션당 1회 제한·IP 기준 중복 방지 로직을 넣지 않는다 — 데모 규모에서 악용 위협이 사실상 없고(리서치 문서 §Q3 결론), A2(단순함) 원칙을 벗어난다. 실사용 서비스로 발전 시 필요하다는 점만 이 스펙 Design Notes에 남긴다.
- `sold` 매물에 대해 RPC 호출을 막는 별도 상태 체크를 함수 안에 넣지 않는다 — 상세 페이지가 이미 `on_sale`만 조회하므로(`buyerListingsQuery`) 호출 지점에서 sold 매물은 애초에 도달하지 않고, RPC 자체는 데이터를 반환하지 않아 FR11(판매완료 비노출) 위반 소지가 없다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 상세 페이지 정상 진입 | 존재하는 `on_sale` 매물 id | 페이지 렌더 후 해당 매물의 `view_count`가 DB에서 +1 | RPC 실패 시 콘솔 로그만, 페이지는 정상 렌더 |
| authenticated가 컬럼 직접 UPDATE 시도 | `supabase.from('listings').update({view_count: 999}).eq('id', 본인매물)` | 거부(`42501` 또는 컬럼 권한 오류) | 클라이언트가 에러를 받는다(이 스토리는 방어만, UI 처리 불요) |
| RPC를 anon/authenticated 롤로 직접 호출 | `select public.increment_listing_view(id)` (`set local role anon` 또는 `authenticated`) | 성공 — `view_count` +1 | 없음(정상 동작) |
| RPC를 그 외 롤(또는 `public`)로 호출 | `set local role`을 anon/authenticated 외로 두거나 PUBLIC 경유 | 거부(EXECUTE 권한 없음) | 없음(하드닝 검증 대상) |

</intent-contract>

## Code Map

- `supabase/migrations/0020_listings_view_count.sql` (신규, 번호는 착수 시 재확인) -- `view_count` 컬럼 + `increment_listing_view` RPC + **쓰기 경로 3축(UPDATE·INSERT·anon) 전부**를 막는 GRANT 수술 + `updated_at` 트리거 `when` 가드를 한 파일에(0018·0019 관례: 테이블/RPC와 관련 RLS·GRANT는 동거).
- `web/src/app/(user)/listings/[id]/page.tsx` (~L186-202, `get_seller_public_summary` RPC 호출부 인접) -- 매물 확인 후 `increment_listing_view` RPC 1회 호출 추가.
- `api/tests/integration/test_view_count_rpc_real_db.py` (신규) -- `test_seller_summary_real_db.py`와 동일한 실DB 패턴(`set local role` + 롤백 픽스처)으로 하드닝 검증. **권한 단언은 (anon·authenticated) × (INSERT·UPDATE) 4조합 전부**를 돈다.
- `web/src/app/(user)/listings/[id]/__tests__/viewCountCallSite.test.ts` (신규) -- "호출 지점이 정확히 1곳"이라는 이 스토리의 핵심 불변식을 소스 스캔으로 고정(CLAUDE.md B9 — 주석은 계약이 아니다). **호출 형태 정규식이 아니라 함수명 문자열 자체**를 찾고, 그 호출이 `p_listing_id` 키를 쓰는지와 `if (!listing)` 가드 뒤에 있는지도 함께 단언한다.
- `supabase/seed-local/02_data.sql` (`listings` 삽입문 1개만) -- `select *`를 명시적 컬럼 목록으로 교체. `not null` 신규 컬럼이 `jsonb_populate_recordset`의 명시적 NULL과 충돌해 로컬 시드가 통째로 죽는 것을 막는다.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0020_listings_view_count.sql` -- 아래 5개 블록을 이 순서로, 한 파일에 self-contained하게(OI-5):
  1. `alter table public.listings add column if not exists view_count int not null default 0;` + `comment on column`.
  2. `create or replace function public.increment_listing_view(p_listing_id uuid) returns void language sql security definer set search_path = '' as $$ update public.listings set view_count = view_count + 1 where id = p_listing_id; $$;` + `comment on function` + `revoke all on function ... from public;` + `grant execute ... to anon, authenticated;`.
  3. **UPDATE 축 차단(authenticated).** `revoke update on public.listings from authenticated;` → `grant update (<0020 이전 25개 컬럼>) on public.listings to authenticated;`. **컬럼 단위 REVOKE 한 줄로는 안 막힌다** — 프렐류드/운영의 `alter default privileges ... grant all on tables`가 테이블 단위 UPDATE를 이미 주고 Postgres는 "테이블 권한 OR 컬럼 권한"으로 판정하므로, 테이블 전체를 회수한 뒤 화이트리스트로 되돌리는 2단계여야 한다(0011의 anon SELECT 선례와 동일). 컬럼 목록은 **하드코딩하지 말고 이 파일 작성 시 실제 스키마에서 확인**하되, 목록 자체는 SQL에 명시적으로 적는다(0011 관례).
  4. **INSERT 축 차단(authenticated).** `revoke insert on public.listings from authenticated;` → `grant insert (<0020 이전 25개 컬럼>) on public.listings to authenticated;`. UPDATE만 막으면 판매자가 **등록(INSERT) 시점에** `view_count: 999999`를 그대로 심을 수 있다 — `SellForm.tsx`가 anon 키로 클라이언트에서 직접 `.from('listings').insert(...)` 하므로 PostgREST 호출 한 번이면 된다(리뷰에서 실DB로 재현: 999999가 그대로 저장됨). 이 축을 막지 않으면 "RPC가 유일한 쓰기 통로"라는 이 스토리의 핵심 주장이 거짓이다.
  5. **anon 축 차단.** `revoke insert, update, delete on public.listings from anon;` — anon이 `listings`에 직접 쓰는 정당한 경로는 없다(anon용 쓰기 RLS 정책이 하나도 없다). 지금은 RLS가 0행으로 만들어 조용히 막고 있을 뿐 **GRANT는 열려 있다**(실측: `anon=awdDxtm`, `has_column_privilege('anon',…,'view_count','UPDATE')=true`) — 나중에 anon 쓰기 정책이 하나라도 생기면 즉시 뚫린다. **주석에 "테이블 전체 권한을 회수한다"고 쓰지 말 것** — 실제로 회수되는 건 8개 중 3개고 `TRUNCATE`·`REFERENCES`·`TRIGGER`·`MAINTAIN`은 남는다(실측 `anon=Dxtm`). 또한 **"anon은 쓰기 경로가 없다"고 단정하지 말 것** — anon의 정당한 쓰기 경로는 `increment_listing_view` RPC 하나이며(2번 블록이 anon에게 EXECUTE를 준다) 그래서 *직접* 테이블 쓰기만 회수하는 것이다. `revoke all`은 쓰지 않는다 — 0011이 anon에게 준 컬럼 SELECT까지 날아가 비로그인 열람이 깨진다(실측 확인).
  6. **`listings` 전용 타임스탬프 트리거로 교체.** RPC의 UPDATE가 0002의 `listings_set_updated_at`을 발동시켜 `updated_at`("수정 시각")을 조회마다 덮어쓰는 문제를 막되, **그 트리거의 두 번째 임무를 죽이면 안 된다** — `public.set_updated_at()`는 `updated_at := now()` **와** `created_at := old.created_at`(등록일 위조 차단, 0002가 명시적으로 문서화) **두 가지**를 한다. `when` 절로 트리거 자체를 끄면 두 임무가 **함께** 꺼진다(실측 재현: `update … set created_at='2000-01-01', view_count = view_count + 1` 이 통과해 등록일이 위조됨). 따라서 `when` 절을 쓰지 말고 **listings 전용 트리거 함수를 새로 만든다**: `public.listings_set_timestamps()` — 본문에서 `new.created_at := old.created_at;`은 **항상** 실행하고, `new.updated_at := now();`은 `if new.view_count is not distinct from old.view_count then` 일 때만 실행한다. `drop trigger if exists listings_set_updated_at on public.listings;`(`if exists` 필수 — 이 파일의 다른 블록이 지키는 재적용 안전성 관례와 일치) 후 새 함수로 트리거를 재생성한다. 공유 함수 `public.set_updated_at()`는 **건드리지 않는다**(다른 테이블도 쓸 수 있다). 조건을 `when` 절이 아니라 함수 본문에 두는 두 번째 이유: `when`에 `new.view_count`를 쓰면 트리거가 그 컬럼에 `pg_depend` 의존을 걸어 `alter table … drop column view_count`가 막히고, `drop … cascade`는 트리거를 조용히 없앤다.
  7. **시드 호환.** `view_count`는 `not null`인데 `supabase/seed-local/02_data.sql`의 `insert into public.listings select * from jsonb_populate_recordset(null::public.listings, …)`는 JSON에 없는 키에 **명시적 NULL**을 넣는다 — 명시적 NULL엔 컬럼 기본값이 적용되지 않는다. `data/listings.json`(103행)에 `view_count` 키가 없으므로 이 마이그레이션 이후 **로컬 시드 전체가 첫 단계에서 죽는다**(실측 재현: `null value in column "view_count" … violates not-null constraint`, `\set ON_ERROR_STOP on`이라 listing_images·chat·guide_documents까지 전부 안 실린다 — 이 리포의 문서화된 로컬 E2E 경로가 통째로 막힌다). 고치는 자리는 **`02_data.sql`의 `listings` 삽입문 하나**: `select *`를 명시적 컬럼 목록으로 바꿔 JSON에 없는 컬럼은 기본값이 적용되게 한다. 왜 이 방향인가 — `listings.json` 103행에 값을 넣는 방식은 같은 함정을 다음 컬럼에서 또 만난다. **다른 테이블의 삽입문은 건드리지 않는다**(A3 — 이 변경이 깨뜨린 것만 고친다). 이유를 주석으로 남긴다.
- `web/src/app/(user)/listings/[id]/page.tsx` -- 매물 not-found 분기(`if (!listing)`) 이후, 갤러리/판매자요약 조회와 나란히 `supabase.rpc('increment_listing_view', { p_listing_id: listing.id })`를 호출하고 실패는 `console.error`로만 처리 -- 상세 진입 시 +1, 실패해도 페이지는 정상 렌더(기존 `sellerSummaryError` 패턴과 일관).
- `api/tests/integration/test_view_count_rpc_real_db.py` -- ① anon/authenticated 롤로 RPC 호출 시 성공+증가 ② 반복 호출 시 누적 증가 ③ authenticated 롤로 `update public.listings set view_count = ...` 직접 시도 시 `InsufficientPrivilege` ④ RPC를 anon/authenticated 밖 롤(`ai_readonly`) 경유로 호출 시 거부 ⑤ 존재하지 않는 id 호출은 에러 없이 0행 무해 처리 ⑥ **INSERT 축**: authenticated가 `view_count`를 지정해 `insert` 하면 `InsufficientPrivilege`, 반면 `view_count`를 빼고 등록하면 정상 성공하고 값은 기본값 0 ⑦ **anon 축**: anon이 `view_count`를 UPDATE/INSERT 할 권한 자체가 없음(`has_column_privilege` = false) ⑧ **권한 완전성**: 기대 컬럼 집합을 하드코딩하지 말고 `information_schema.columns`에서 **실시간으로 뽑아** `{전 컬럼} - {view_count}`와 비교한다 — (anon·authenticated) × (INSERT·UPDATE) 4조합 전부. 하드코딩 리터럴은 "0020 이후 새로 추가된 컬럼이 GRANT 목록에서 누락"되는 바로 그 함정을 구조적으로 못 잡는다(리뷰에서 `alter table ... add column`으로 재현: 컬럼이 조용히 쓰기 불가가 됐는데 테스트는 green) ⑨ **`updated_at` 불변**: RPC 호출 전후로 `updated_at`이 바뀌지 않는다(조회가 "수정 시각"을 덮어쓰지 않는다) ⑩ **명명 인자 계약**: 최소 한 곳은 프로덕션과 같은 방식인 `select public.increment_listing_view(p_listing_id => %s)`로 호출한다 — 전부 위치 인자로만 부르면 파라미터명을 바꿔도 테스트가 green인 채 프로덕션만 깨진다(리뷰에서 재현: 이름만 바꾸자 PostgREST 형태 호출은 실패, pytest는 9 passed).
  **아래 ⑪~⑭는 "검사가 한쪽 방향만 본다"는 2차 리뷰 지적에 대응한다 — 실측 결과 트리거를 통째로 지워도 18건이 전부 green이었다. 없애는(deleting)·넓히는(widening) 변형도 red가 돼야 한다.**
  ⑪ **트리거 양방향**: (a) `view_count`를 **안** 바꾸는 평범한 수정(예: `price`)은 `updated_at`을 **갱신한다**(엄격히 증가) — 트리거가 통째로 사라지거나 `after update`로 잘못 재생성되면 red. (b) `created_at` 위조는 **두 경우 모두** 되돌려진다: `view_count`를 함께 바꾸는 UPDATE와 안 바꾸는 UPDATE 양쪽(0002가 문서화한 등록일 위조 차단이 이 스토리 때문에 죽지 않았음을 고정 — 실측 재현된 결함이다). (c) ⑨의 `updated_at` 불변 테스트 안에서 `view_count`가 **실제로 1 증가했음**도 함께 단언한다 — 안 그러면 RPC가 아무것도 안 해도 통과한다(실측: 함수 본문을 no-op으로 바꿔도 green).
  ⑫ **anon DELETE 축**: ⑦·⑧의 파라미터에 `DELETE`를 더한다(테이블 단위이므로 `has_table_privilege`). 5번 블록이 회수하는 3개 축 중 유일하게 검증이 없던 축이다.
  ⑬ **INSERT 회귀를 실제 등록 페이로드로**: `test_authenticated_insert_without_view_count_defaults_to_zero`가 15개 컬럼만 넣어 4번 블록이 재-GRANT한 25개 중 10개를 안 건드린다. `SellForm`/Flutter가 실제로 보내는 컬럼 집합(`options` 배열·`description`·신뢰속성 3종 포함)으로 한 건 더 넣어 등록 경로에 회귀가 없음을 증명한다.
  ⑭ **픽스처 견고성**: 커밋하는 픽스처(`updated_at` 검증용)는 이메일을 실행마다 유일하게(`f"vc-{uuid.uuid4()}@example.com"`) 만든다 — 하드코딩 이메일은 프로세스가 중간에 죽으면 실제 Supabase의 `auth.users` 유니크 제약에 걸려 이후 모든 실행이 red가 된다. `_call_rpc`의 `reset role`은 `try/finally`로 감싼다(예외 시 롤이 새어 다음 단언이 엉뚱한 이유로 통과/실패한다).

**Acceptance Criteria:**
- Given 마이그레이션 적용 전 스키마, when `0020_listings_view_count.sql`을 적용하면, then `listings.view_count`가 존재하고 기본값 0이며, `increment_listing_view(uuid)` 함수가 `security definer`로 존재한다.
- Given 적용된 스키마, when `anon` 또는 `authenticated` 롤로 `increment_listing_view`를 호출하면, then 대상 행의 `view_count`가 정확히 1 증가하고, when `authenticated` 롤로 `view_count` 컬럼을 직접 `UPDATE`하면, then 권한 오류로 거부된다.
- Given 적용된 스키마, when `authenticated` 롤이 `view_count` 값을 지정해 매물을 `INSERT` 하면, then 권한 오류로 거부되고, when `view_count`를 지정하지 않고 `INSERT` 하면, then 정상 등록되며 그 행의 `view_count`는 0이다. (등록 시점 위조 차단 — 이게 없으면 "RPC가 유일한 쓰기 통로"가 거짓이 된다.)
- Given 적용된 스키마, when `anon` 롤의 `listings` 쓰기 권한을 조회하면, then `view_count`에 대한 INSERT·UPDATE 권한이 모두 없다(`has_column_privilege` = false) — RLS 정책 유무와 무관하게 GRANT 층에서 막혀 있다.
- Given `listings`에 `view_count` 이후 새 컬럼이 추가되는 상황, when 권한 완전성 테스트가 돌면, then 기대 집합을 실시간 스키마에서 도출하므로 "새 컬럼이 GRANT 목록에서 누락됨"이 red로 잡힌다(하드코딩 리터럴로는 green으로 통과해버린다).
- Given `on_sale` 매물의 `updated_at`, when `increment_listing_view`가 호출되면, then `updated_at`은 변하지 않고 `view_count`는 1 증가한다 — 조회수 증가가 "수정 시각"(관리자 거래내역이 거래일로 쓰는 값)을 덮어쓰지 않는다.
- Given 같은 매물, when 판매자가 `price` 같은 평범한 컬럼을 수정하면, then `updated_at`은 갱신된다 — 조회수 예외가 트리거를 통째로 죽이지 않았다.
- Given 등록일 위조 시도, when `created_at`을 바꾸는 UPDATE가 `view_count`를 **함께 바꾸든 안 바꾸든**, then `created_at`은 항상 기존 값으로 되돌려진다(0002가 세운 등록일 위조 차단이 이 스토리 때문에 죽지 않는다).
- Given 로컬 시드(`scripts/seed-local.sh` → `supabase/seed-local/02_data.sql`), when 0020 적용 후 시드를 다시 돌리면, then `listings` 103행이 정상 적재되고 뒤따르는 단계(listing_images·chat·guide_documents)도 전부 실린다.
- Given 프로덕션이 PostgREST를 통해 **명명 인자**(`{ p_listing_id: ... }`)로 호출한다는 사실, when 통합 테스트가 돌면, then 최소 한 건은 `p_listing_id => ...` 명명 인자 형태로 호출해 파라미터 이름 계약이 실제로 고정된다.
- Given 구매자가 `on_sale` 매물 상세 페이지에 진입, when 페이지가 서버에서 렌더되면, then 해당 매물의 `view_count`가 DB에서 1 증가한다(직접 psql 조회 또는 API로 전/후 값 비교).
- Given 매물 목록/검색 결과/AI 응답 카드 렌더링, when 그 카드들이 그려져도, then `increment_listing_view`가 호출되지 않는다 — **실행되는 검사로 고정한다**(`viewCountCallSite.test.ts`가 `web/src` 전체를 스캔해 호출 지점이 상세 페이지 1곳뿐임을 단언; 검사 파일에는 "이 검사가 안 보는 것"(런타임 호출 횟수, `web/src` 밖 클라이언트)을 함께 적는다).

## Spec Change Log

### 2026-07-28 — 후속 리뷰 2차 (bad_spec 루프백 #2)

**촉발한 지적 2건 — 둘 다 오케스트레이터가 스크래치 Postgres 18에서 직접 재현했다:**
1. **`view_count int not null`이 로컬 시드를 죽인다.** `supabase/seed-local/02_data.sql`이 `insert into public.listings select * from jsonb_populate_recordset(null::public.listings, …)`를 쓰는데, 이 함수는 JSON에 없는 키에 **명시적 NULL**을 넣고 명시적 NULL엔 컬럼 기본값이 적용되지 않는다. `data/listings.json` 103행엔 `view_count` 키가 없다 → `null value in column "view_count" … violates not-null constraint`. `\set ON_ERROR_STOP on`이라 시드가 1단계에서 통째로 멈춰 사진·채팅·가이드문서까지 전부 안 실린다. **이 리포의 문서화된 로컬 웹 E2E 경로가 막힌다.** 1차 스펙은 마이그레이션·테스트만 보고 시드 소비자를 보지 않았다.
2. **루프백 #1이 지시한 `when` 가드가 등록일 위조 차단을 죽였다.** `public.set_updated_at()`는 임무가 **둘**이다 — `updated_at := now()` **와** `created_at := old.created_at`(0002가 "소유자가 UPDATE에 created_at을 끼워 넣어 최신 등록처럼 위장하는 것을 차단"이라고 명시 문서화). 트리거에 `when`을 걸면 두 임무가 **함께** 꺼진다. 실측: `update … set created_at='2000-01-01', view_count = view_count + 1` → 등록일이 2000-01-01로 박힌다. **1차 루프백의 처방 자체가 결함이었다** — "공유 함수는 건드리지 말고 트리거 쪽에 조건을 달라"고 지시하면서 그 함수가 무슨 일을 하는지 확인하지 않았다.

**무엇을 고쳤나 (전부 `<intent-contract>` 바깥):**
- **Execution 5번 블록** — anon 축만 남기고, 주석에서 "테이블 전체를 회수한다"·"anon은 쓰기 경로가 아예 없다" 두 과장을 **금지 지시로** 바꿨다(실측: 회수되는 건 8개 중 3개, `anon=Dxtm`로 TRUNCATE 등 잔존 / anon의 정당한 쓰기 경로는 RPC 하나가 **있다**). `revoke all` 금지도 명시(0011의 anon 컬럼 SELECT가 함께 날아간다 — 실측 확인).
- **Execution 6번 블록 신설(트리거)** — `when` 절을 **버리고** `listings` 전용 트리거 함수 `public.listings_set_timestamps()`를 새로 만든다: `created_at` 보존은 **항상**, `updated_at` 갱신은 `view_count`가 안 바뀐 UPDATE에서만. `drop trigger if exists`(`if exists` 필수). 부수 효과로 `when`이 걸던 `pg_depend` 컬럼 의존도 사라진다(그게 있으면 `drop column view_count`가 막히고 `cascade`는 트리거를 조용히 지운다).
- **Execution 7번 블록 신설(시드)** — `02_data.sql`의 `listings` 삽입문만 명시적 컬럼 목록으로. 다른 테이블 삽입문은 미변경(A3).
- **Tasks(테스트) ⑪~⑭ 신설** — 트리거 양방향(평범한 수정은 `updated_at`을 올린다 / `created_at` 위조는 두 경우 모두 되돌려진다 / `updated_at` 불변 테스트 안에서 증가도 함께 단언), anon DELETE 축, 실제 등록 페이로드로 INSERT 회귀, 픽스처 견고성(유일 이메일·`try/finally` reset role).
- **Acceptance Criteria** — 위에 대응하는 AC 4개 추가.
- **Verification** — `check_migrations.py`의 **종료 코드**를 그대로 적을 것(Docker 없으면 exit 1이며 게이트는 통과하지 않은 것이다), red/green 목록을 "없애는·넓히는 변형"까지 10종으로 확장, 시드 red/green, CI 등가 실행(`pytest tests/integration` 디렉터리 전체).

**피해야 할 알려진-나쁜 상태 (루프백 #1 목록에 이어서):**
6. 트리거에 `when` 절을 걸어 조회수 UPDATE를 통째로 건너뛰는 것 → `created_at` 위조 차단이 함께 죽는다(실측 재현). 조건은 **함수 본문 안**에 둔다.
7. `updated_at` 검사를 "안 바뀐다" 한 방향으로만 두는 것 → 트리거를 통째로 지워도, `after update`로 잘못 재생성해도, RPC 본문을 no-op으로 만들어도 전부 green이었다(리뷰 실측).
8. 호출 지점 단일성 검사를 `\.rpc\(\s*['"]이름['"]` 형태 정규식으로만 두는 것 → 백틱 리터럴과 `const FN = '이름'` 상수 경유가 통과한다(리뷰 실측 2종). 함수명 문자열 자체를 찾고, `p_listing_id` 키와 `if (!listing)` 뒤 위치까지 함께 단언한다 — page.tsx의 인자 키를 바꿔도 `tsc`·`eslint`·vitest 213건·DB 18건이 전부 green이었다(리뷰 실측).
9. 마이그레이션 주석에 실측보다 강한 단정을 쓰는 것 — 1차 루프백을 촉발한 것이 바로 그 유형("RPC가 유일한 쓰기 통로")인데 교체 주석이 같은 실수를 되풀이했다.
10. `drop trigger`에 `if exists`를 빼는 것 → 게이트는 `ON_ERROR_STOP`으로 도므로 트리거가 없는 DB에선 마이그레이션 전체가 롤백된다.

**KEEP (루프백 #1의 KEEP 전부 유효, 여기에 추가):**
- 3·4번 블록(UPDATE·INSERT 2단계 회수→화이트리스트)은 **검증까지 견고하다** — 리뷰가 좁히는 변형으로 red를 확인했다. 그대로 유지.
- 5번 블록의 `revoke insert, update, delete … from anon` **문장 자체**는 유지(주석 문구만 정정).
- 테스트 ⑧(권한 완전성)의 "기대 집합을 `information_schema.columns`에서 실시간 도출" 방식은 유지 — 새 컬럼 누락을 실제로 red로 잡는 것이 확인됐다.
- 테스트 ⑩(명명 인자)의 **DB 쪽 절반**은 실제로 계약을 고정한다(SQL 파라미터명을 바꾸면 red). 유지하되 웹 쪽 절반을 ⑧이 아니라 호출지점 검사로 보강한다.
- `seeded_committed` 같은 커밋 픽스처가 필요하다는 판단 자체는 옳다 — `now()`가 트랜잭션 내내 고정이라 롤백 픽스처로는 `updated_at` 변화를 관측할 수 없다(1차 구현이 스스로 발견해 고친 함정). 유지하되 이메일만 유일하게.

**이번 루프백 범위에서 의도적으로 제외 (대장에 등재):** `anon`·`authenticated`가 `TRUNCATE`/`REFERENCES`/`TRIGGER`/`MAINTAIN`을 계속 보유(#18 축, PostgREST엔 TRUNCATE 동사가 없어 브라우저 경로로는 도달 불가) · `view_count int`의 21억 상한(intent가 `int`를 명시) · `created_at`·`id`·`embedding`이 INSERT 화이트리스트에도 포함(#135의 INSERT 축) · `test_seller_summary_real_db.py` 1건이 게이트 프렐류드 환경에서 원래부터 실패(이 스토리와 무관, 리뷰가 0019까지만 적용한 DB로 대조 확인).

### 2026-07-27 — 후속 리뷰 1차 (bad_spec 루프백 #1)

**촉발한 지적:** 이 스토리의 핵심 주장인 *"`increment_listing_view` RPC가 `view_count`의 유일한 쓰기 통로"* 가 **거짓**임이 실DB로 재현됐다. 스펙(Code Map·Execution·AC)이 **UPDATE 축 하나만** 다뤘고 나머지 두 축을 열어둔 채로 "유일한 통로"라고 선언했다.

**무엇을 고쳤나 (전부 `<intent-contract>` 바깥):**
- **Execution** — 마이그레이션을 5개 블록으로 재구성. 기존 3번(UPDATE 축)에 더해 **4번(INSERT 축)**·**5번(anon 축 + `updated_at` 트리거 `when` 가드)** 을 신설.
- **Tasks(테스트)** — ⑥~⑩ 신설: INSERT 거부/기본값 0, anon 권한 부재, 권한 완전성 집합을 `information_schema.columns`에서 실시간 도출, `updated_at` 불변, 명명 인자(`p_listing_id =>`) 호출.
- **Acceptance Criteria** — 위 5축에 대응하는 AC 5개 추가. 마지막 AC의 "코드 검토로 확인"을 실행 검사(`viewCountCallSite.test.ts`)로 승격(B9).
- **Verification** — 마이그레이션 게이트 동적 절반의 로컬 재현을 명시(CI는 `develop`/`main`에서만 도므로 이 브랜치에선 한 번도 안 돌았다), red/green 증명 대상 6종 열거.
- **Code Map** — `viewCountCallSite.test.ts`를 정식 산출물로 등재(1차 구현에선 리뷰 patch로 뒤늦게 생겨 Code Map에 없었다).

**피해야 할 알려진-나쁜 상태 (재도출 시 되풀이 금지):**
1. `revoke update`만 하고 `revoke insert`를 빼는 것 → 판매자가 등록 시 `view_count: 999999`를 심는다. **실측 재현됨**(scratch PG18: authenticated가 999999로 INSERT 성공, 행에 그대로 저장). `SellForm.tsx`가 anon 키로 클라이언트에서 직접 insert하므로 PostgREST 호출 한 번이면 도달한다.
2. `authenticated`만 회수하고 `anon`을 "원래 권한 없다"고 단정하는 것 → **거짓이다.** 실측 `relacl`: `anon=awdDxtm`(w=UPDATE 포함), `has_column_privilege('anon',…,'view_count','UPDATE')=true`. 0011은 anon의 **SELECT만** 회수했다. 지금 막고 있는 건 RLS(0행)뿐이며, 이 스토리가 "RLS는 컬럼을 못 막는다"고 선언한 바로 그 층이다. 마이그레이션 주석에 이 단정을 **다시 적지 말 것**.
3. 기대 컬럼 집합을 테스트에 하드코딩하는 것 → 0020 이후 추가되는 컬럼이 GRANT 목록에서 누락돼도 green이다(실측 재현: `add column dealer_note` 후 `has_column_privilege(...)=false`인데 테스트 통과). 3번 블록이 테이블 전체 UPDATE를 회수했기 때문에 **"목록에 없는 컬럼 = 쓰기 불가"가 기본값**이 됐다 — 즉 이 누락은 조용한 기능 고장이다.
4. RPC를 위치 인자로만 테스트하는 것 → 파라미터명을 바꿔도 pytest는 green, PostgREST 경로만 깨진다(실측 재현). Supabase 클라이언트에 `<Database>` 제네릭이 없어 `tsc`도 못 잡고, page.tsx는 에러를 `console.error`로 삼키므로 화면도 멀쩡하다 — 초록 게이트 3개를 통과한 채 `view_count`가 영원히 0에 머무른다.
5. `updated_at`이 조회마다 갱신되게 두는 것 → 실측 재현(RPC 1회에 `23:52:40 → 23:52:53`). `updated_at`은 관리자 거래내역 화면이 **거래일**로 쓰는 값이고(`web/src/app/(admin)/admin/transactions/page.tsx`) `db-schema-guide.md`가 "수정 시각"으로 문서화한 값이다. sold 매물은 상세 페이지가 조회하지 않아 거래일 자체는 오염되지 않지만, `on_sale` 행에서 컬럼의 의미가 조용히 "마지막 조회 시각"으로 바뀐다.

**KEEP (1차 구현에서 잘 됐고 재도출 후에도 반드시 살아 있어야 하는 것):**
- **2단계 REVOKE→GRANT 발견 자체.** 컬럼 단위 `revoke update (view_count)` 한 줄은 **무효**다(플랫폼 기본 GRANT가 준 테이블 단위 권한이 남아 "테이블 OR 컬럼" 판정으로 통과). 이 사실과 그 근거 주석을 마이그레이션에 그대로 유지할 것.
- `security definer` + `set search_path = ''` + 본문 전 테이블 참조에 `public.` 접두 + `revoke all on function ... from public` 후 `grant execute to anon, authenticated`(0019 패턴).
- 함수 본문은 단일 UPDATE — 컬럼/값을 파라미터로 받는 범용 UPDATE로 확장하지 않는다.
- `add column if not exists`(0007·0009·0017 관례).
- page.tsx의 호출은 `if (!listing)` 이후 **정확히 한 곳**, 실패는 `console.error`만 하고 렌더를 막지 않는다(`sellerSummaryError` 패턴).
- `viewCountCallSite.test.ts`의 정적 단일성 검사(B9) — 파일 머리의 "이 검사가 안 보는 것" 주석도 함께.
- 실DB 테스트의 구조: `TEST_DATABASE_URL` 없으면 skip(거짓 통과 금지), 롤백 픽스처, `set local role` 임퍼소네이션, 본인 소유 행으로 시도해 "RLS가 아니라 GRANT가 방어선"임을 분리 증명.
- 기존 통과 테스트 6종(anon/authenticated 증가, 반복 누적, 직접 UPDATE 거부, 다른 컬럼은 여전히 UPDATE 가능, 존재하지 않는 id 무해, `ai_readonly` EXECUTE 거부).
- **Next.js `<Link>` prefetch 조회수 오염 지적은 이미 기각됐다** — 이 라우트는 `export const dynamic = 'force-dynamic'`이고 리포에 `loading.tsx`가 없어 Next 16 공식 문서상 prefetch 자체가 안 된다(실측 확인). 재도출 시 다시 논쟁하지 말 것.

**이번 루프백 범위에서 의도적으로 제외 (다음 리뷰 패스에서 재판정 대상):** `0011` anon SELECT 화이트리스트에 `view_count`가 없어 비로그인 인기 정렬이 42501로 깨진다는 사실(intent의 Never가 Story 11.4의 몫으로 명시) · GRANT 목록에 `embedding`·`id`가 포함돼 판매자가 자기 매물의 검색 벡터·기본키를 바꿀 수 있다는 사실(0020 이전부터 있던 권한이라 회귀는 아님) · Flutter 앱 상세 화면은 조회수를 올리지 않는다는 사실 · `docs/db-schema-guide.md`의 스키마 표 노후.

## Review Triage Log

### 2026-07-28 — Review pass (후속 리뷰 3차, 루프백 없음 — `review_loop_iteration` 2 유지)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 7: (high 0, medium 2, low 5)
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` **0020이 `revoke all` 대신 `revoke insert, update, delete`를 쓰는 이유(= 0011이 anon에게 준 컬럼 SELECT를 살리기 위해)가 주석에만 있고 실행 검사가 없었다.** 실측: 리포 전체에서 `set local role anon`은 `test_seller_summary_real_db.py` 2곳뿐이고 둘 다 `profiles` 대상 — **어떤 테스트도 anon으로 `listings`를 읽지 않는다**. 대장 #139가 바로 이 GRANT를 더 조이자고 제안하고 있어, 그 작업이 비로그인 열람을 깨뜨려도 전 게이트가 초록이다. → `test_anon_can_select_whitelisted_columns_but_view_count_still_denied` 신설(화이트리스트 컬럼 SELECT 성공 + `view_count`는 여전히 거부, 양방향). red/green 직접 확인(화이트리스트 컬럼 회수 → red → `0011` 재적용 → green).
  - `[medium]` `[patch]` **권한 완전성 4조합 중 anon 쪽 2조합이 절대 실패할 수 없었다.** 기대값이 빈 집합이라 쿼리가 0행만 돌려주면 무조건 통과한다 — 실측: `grantee='anon'`도 0행, 오타 `grantee='anonn'`도 0행이라 둘 다 green. "4조합 전부 검증"이라는 주장의 절반이 아무것도 검증하지 않았다. → anon 분기를 `has_column_privilege`로 전 컬럼 개별 질의하도록 교체하고, **프로브가 살아 있음을 증명하는 대조군**(`authenticated`+`price` → True)을 같은 테스트에 심었다. red/green 확인(anon에 `update (price)` 부여 → red).
  - `[medium]` `[patch]` **호출 지점 단일성 검사가 RPC 호출을 통째로 주석 처리해도 초록이었다.** 이 검사는 "따옴표로 감싼 함수명" 등장 횟수만 세므로 살아 있는 코드와 주석을 구별하지 못한다 — 스펙 AC가 이 검사를 "실행되는 검사로 고정한다"고 선언한 것이 거짓이었다. → 기존 두 단언은 그대로 두고(스펙 known-bad #8은 형태 정규식 *단독* 사용을 금지한 것이라 이름 매칭은 유지해야 백틱·상수 우회를 잡는다) "`await supabase.rpc('increment_listing_view'` 형태가 주석이 아닌 코드 줄에 있다"는 세 번째 단언을 **추가**. 실측 확인: 호출 3줄을 주석 처리하면 **새 단언만 red, 기존 2건은 green** — 정확히 지적된 증상이 재현됐다.
  - `[low]` `[patch]` **마이그레이션 주석 2곳이 실측보다 강하게 단정했다(known-bad #9 재발).** ① 트리거 함수 주석이 "view_count**만** 바뀐 UPDATE"라고 읽히지만 조건은 "view_count가 바뀌면"이다 — 실측: `set price = 31111111, view_count = view_count + 1` → price는 바뀌고 `updated_at`은 그대로. ② "공유 함수 `set_updated_at()`는 다른 테이블도 쓸 수 있다"가 거짓 — 이 마이그레이션이 마지막 사용처를 drop해 참조 트리거 **0건**(실측). → 동작은 그대로 두고 주석만 실측에 맞게 정정, 각각 대장 #141·#142 번호를 함께 적었다. 동작을 안 바꾼 이유: ①은 3·4·5번 블록이 `view_count` 쓰기를 회수해 **어떤 클라이언트 경로로도 도달 불가**하고, 제안된 `to_jsonb(new)` 행 비교는 운영의 `vector(768)` 컬럼에 대해 이 환경에서 실측할 수 없다(성능은 반대 이유가 아니었다 — 실측 조회당 0.168ms → 0.363ms).
  - `[low]` `[patch]` **테스트 픽스처 견고성 2건**(스펙 ⑭가 `_call_rpc`에 요구한 것과 같은 축인데 다른 지점에 남아 있었다). ① `test_ordinary_update_bumps_updated_at`의 `set role`/`reset role`이 `try/finally` 밖이라, UPDATE가 예외를 던지면 롤이 새어 teardown이 `permission denied for schema auth`로 죽고 진짜 실패 원인을 가린다. ② `seeded_committed`의 판매자·매물 생성이 `finally`로 정리하는 `try` **바깥**이라 autocommit 상태에서 setup이 실패하면 행이 실제 DB에 남는다. → 둘 다 `try` 안으로. 나머지 `set local role` 지점은 전부 롤백 픽스처의 세이브포인트 안이라 안전함을 확인.
- 반증됨(재확인 후 기각):
  - **RPC가 anon에게 열려 있어 무제한 조작 가능**(2개 렌즈 공통, 5000회 호출로 실증) — intent의 Never가 rate limit·세션당 1회·IP 중복 방지를 **데모 규모 근거로 명시 배제**했고, Design Notes가 "실서비스 전환 시 반드시 필요"로 이미 기록하고 있다. 스코프 권한은 intent에 있다.
  - **`increment_listing_view`를 `conventions.md` §6 SECURITY DEFINER 소비처 목록에 등재하고 `status='on_sale'` 필터를 넣으라** — §6은 FR11(판매완료 **비노출**) 강제 지점 목록이고, 이 RPC는 데이터를 반환하지 않아 노출 표면이 없다. 노출 목록에 비노출 함수를 넣으면 계약 문서가 자기모순에 빠진다(B8). sold 상태 체크는 intent의 Never가 금지했고 이전 두 패스에서도 같은 이유로 기각됐다.
  - **스토리를 done으로 닫는데 `api-db` CI 잡이 red다** — 그 red는 이 스토리와 무관한 기존 실패이며 이미 #138로 등재돼 있고 트리거도 "`develop` 병합 직전"으로 지정돼 있다. 이번 패스에서 0019까지만 적용한 대조 DB로 **직접 재확인**했다(0020 없이도 동일하게 실패).
  - **RPC 영구 실패를 감지할 관측 수단이 없다** — #132(page.tsx RPC 배선 미검증)·#133(REST 계층 미경유)이 이미 같은 축을 덮는다.
  - **인기 매물일수록 행 잠금 경합이 커진다** — 측정 없는 추정이고 데모 규모에서 근거가 없다(A2).
  - **권한 완전성 테스트의 보호 컬럼 집합을 파라미터화하라** — 2차 패스에서 같은 이유로 기각됐다(두 번째 보호 컬럼이 아직 없다, A2 추측성 확장).
  - **호출 지점 검사가 텍스트 위치만 보므로 가드 뒤에 선언된 헬퍼로 호이스팅하면 통과한다** — 작위적 시나리오이고, 이번 패치(`await supabase.rpc(` 형태 단언)로 실질적으로 봉쇄된다.
- deferred (대장 `docs/tech-debt.md`에 **신규 항목으로만** 등재 — 기존 항목은 건드리지 않음. `deferred-work.md`는 2026-07-15 동결로 신규 기입 금지):
  - `[low]` #141 — `listings_set_timestamps` 조건이 "view_count만"이 아니라 "view_count가 바뀌면"이라 혼합 UPDATE가 `updated_at`을 건너뛴다(실측 재현, 현재 도달 불가). 트리거: pgvector 있는 환경에서 `to_jsonb(record)`를 실측할 수 있을 때.
  - `[low]` #142 — `public.set_updated_at()`이 참조 트리거 0건인 고아가 됐고 `docs/learning/01-db.md:107`이 아직 그것을 현재 동작으로 가르친다. 트리거: #137과 같은 자리.
  - `[medium]` #143 — 마이그레이션 게이트가 "재적용"을 한 번도 시험하지 않는다. **이번 스토리가 실제로 그 구멍에 빠졌다**(아래 검증 항목 참조). 트리거: Epic 13 게이트 정비(#22~24).
  - `[low]` #144 — 인기 정렬용으로 만든 `view_count`에 인덱스가 없다(실측: `listings`의 인덱스는 `listings_pkey` 하나뿐). 트리거: Story 11.4 착수 시 #134와 같은 마이그레이션에서 함께.
  - `[low]` #145 — `view_count int`의 21.4억 상한(intent가 `int`를 명시). 트리거: 실사용 트래픽 전환 시.
  - `[medium]` #146 — 시드의 명시 컬럼 목록이 "시끄러운 실패"를 "조용한 누락"으로 바꿨고, 나머지 4개 삽입문은 여전히 `select *`다. 트리거: `listings`에 컬럼을 더하는 다음 마이그레이션, 또는 그 4개 테이블 중 하나에 `not null` 컬럼이 생길 때.
  - `[low]` #147 — `view_count`의 정의가 어디에도 없다(실제로는 "웹 상세 **서버 렌더** 횟수"). 트리거: Story 11.4에서 화면에 노출할 때 #136과 함께.

### 2026-07-28 — Review pass (후속 리뷰 2차, `review_loop_iteration` 1 → 2)
- intent_gap: 0
- bad_spec: 6: (high 2, medium 4)
- patch: 0
- defer: 3: (high 0, medium 1, low 2)
- reject: 5
- addressed_findings:
  - `[high]` `[bad_spec]` **`view_count int not null`이 로컬 시드를 통째로 죽인다.** `02_data.sql`의 `jsonb_populate_recordset` + `select *`가 JSON에 없는 컬럼에 명시적 NULL을 넣고, 명시적 NULL엔 기본값이 안 붙는다. 오케스트레이터 실측 재현: `null value in column "view_count" … violates not-null constraint`. `ON_ERROR_STOP on`이라 뒤따르는 사진·채팅·가이드문서 적재까지 전부 멈춘다 — 이 리포의 문서화된 로컬 E2E 경로가 막힌다. → Execution 7번 블록·AC·Verification 신설, 코드 재도출.
  - `[high]` `[bad_spec]` **루프백 #1이 지시한 트리거 `when` 가드가 등록일 위조 차단을 함께 죽였다.** `set_updated_at()`는 `updated_at` 갱신과 `created_at := old.created_at`(0002가 명시 문서화한 위조 차단) 두 임무를 하는데 `when`은 트리거 자체를 꺼서 둘 다 무력화한다. 오케스트레이터 실측 재현: `set created_at='2000-01-01', view_count = view_count + 1` 이 통과해 등록일이 위조됐다. → `when` 절 폐기, `listings` 전용 트리거 함수(`created_at` 보존은 항상 / `updated_at`은 조건부)로 교체.
  - `[medium]` `[bad_spec]` **`updated_at` 검사가 한 방향만 본다.** "안 바뀐다"만 단언해, 트리거를 통째로 지워도·`after update`로 잘못 재생성해도·RPC 본문을 no-op으로 바꿔도 18건 전부 green이었다(리뷰 3인 각각 실측). → 테스트 ⑪ 신설(평범한 수정은 `updated_at`을 올린다 / `created_at` 위조는 양쪽 경우 모두 되돌려진다 / 불변 테스트 안에서 증가도 함께 단언).
  - `[medium]` `[bad_spec]` **호출 지점 단일성 검사를 두 가지 흔한 표기로 우회할 수 있고, page.tsx의 인자 키는 아무도 고정하지 않는다.** 백틱 리터럴과 `const FN = 'increment_listing_view'` 경유가 통과했고(리뷰 실측), page.tsx의 `p_listing_id`를 다른 이름으로 바꿔도 `tsc`·`eslint`·vitest 213건·DB 18건이 전부 green이었다 — 스펙이 "닫혔다"고 적은 known-bad #4의 웹 쪽 절반이 여전히 열려 있었다. → 함수명 문자열 자체 매칭 + `p_listing_id` 키 단언 + `if (!listing)` 뒤 위치 단언.
  - `[medium]` `[bad_spec]` **5번 블록 주석이 실측보다 강하게 단정한다.** "테이블 전체를 회수한다"지만 실제로는 8개 중 3개고 `anon=Dxtm`로 TRUNCATE 등이 남는다(리뷰 실측: anon으로 `truncate listings cascade` 성공). "anon은 정당한 쓰기 경로가 아예 없다"도 거짓 — 13줄 위에서 anon에게 그 RPC EXECUTE를 준다. 1차 루프백을 촉발한 과장과 **같은 유형이 교체 주석에서 재발**했다. → 주석 문구를 실측에 맞추도록 지시, `revoke all` 금지(0011 SELECT가 날아간다)도 명시.
  - `[medium]` `[bad_spec]` **재적용·격리 견고성 3종.** `drop trigger`에 `if exists`가 없어 트리거 없는 DB에서 게이트가 통째로 롤백된다 · `when` 절이 `view_count`에 `pg_depend`를 걸어 `drop column`을 막고 `cascade`는 트리거를 조용히 지운다 · 커밋 픽스처의 하드코딩 이메일이 프로세스 중단 시 실제 Supabase 유니크 제약에 걸려 이후 모든 실행을 red로 만든다. → 각각 `if exists`, 조건을 함수 본문으로 이동, 유일 이메일 + `try/finally` reset role.
- 반증됨(재확인 후 기각):
  - `revoke all on public.listings from anon`으로 잔여 권한까지 걷어내라는 제안 — 리뷰어 스스로 실측했듯 0011이 anon에게 준 컬럼 SELECT까지 날아가 **비로그인 열람이 깨진다.** 채택하지 않고 금지 지시로 스펙에 남겼다.
  - `view_count`를 `bigint`로 바꾸라는 제안 — intent-contract가 `int not null default 0`을 명시했다(스코프 권한은 intent에 있다). 상한 자체는 대장에 등재.
  - 권한 완전성 테스트의 "보호 컬럼 집합을 파라미터화하라"는 제안 — 현재 형태가 이번 사이클의 목표(새 컬럼 누락을 red로 잡기)를 실제로 달성함이 실측됐고, 두 번째 보호 컬럼은 아직 존재하지 않는다(A2 추측성 확장).
  - `.test.tsx` 확장자 필터 — 리포에 `.test.tsx`가 0건이고, 새 단일성 검사가 함수명 매칭으로 바뀌면서 제외 규칙도 함께 정리된다.
  - `_LISTING_COLS` 15컬럼 문제를 별도 결함으로 세우는 것 — 테스트 ⑬으로 흡수했다.
- deferred (대장 `docs/tech-debt.md`에 **신규 항목으로만** 등재):
  - `[medium]` #138 — `pytest tests/integration` 디렉터리 전체를 게이트 프렐류드 환경에서 돌리면 `test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls` 1건이 실패한다. 리뷰가 0019까지만 적용한 DB로 대조해 **이 스토리와 무관한 기존 실패**임을 확인했다. `develop` 병합 시 CI가 이 브랜치에서 처음 도는데 무관한 이유로 red가 된다.
  - `[low]` #139 — `anon`·`authenticated`가 `listings`에 대해 `TRUNCATE`·`REFERENCES`·`TRIGGER`·`MAINTAIN`을 계속 보유한다(#18 축). anon으로 `truncate … cascade`가 실제로 성공했다(PostgREST엔 TRUNCATE 동사가 없어 브라우저 경로로는 도달 불가).
  - `[low]` #140 — `created_at`이 INSERT 화이트리스트에 포함돼 등록 시점 등록일 위조가 가능하다(UPDATE 축은 트리거가 막지만 INSERT 축엔 방어가 없다). `id`·`embedding`도 INSERT 축에 함께 있다 — #135의 INSERT 쪽 짝.

### 2026-07-27 — Review pass (후속 리뷰 1차, `review_loop_iteration` 0 → 1)
- intent_gap: 0
- bad_spec: 5: (high 1, medium 4)
- patch: 0
- defer: 4: (high 0, medium 2, low 2)
- reject: 9
- addressed_findings:
  - `[high]` `[bad_spec]` **INSERT 축이 열려 있어 "RPC가 유일한 쓰기 통로"가 거짓이었다.** 스펙이 UPDATE 축만 규정해 `revoke insert`가 없었고, 판매자가 등록 시 `view_count`를 임의 값으로 심을 수 있다. 오케스트레이터가 스크래치 Postgres 18(프렐류드 + 마이그 20개)로 직접 재현 — authenticated 롤로 `view_count: 999999` INSERT 성공, 행에 그대로 저장(`has_column_privilege('authenticated',…,'view_count','INSERT')=true`). `SellForm.tsx`가 anon 키로 클라이언트에서 직접 insert하므로 PostgREST 호출 한 번으로 도달한다. → Execution 4번 블록·AC·테스트 ⑥ 신설, 코드 재도출.
  - `[medium]` `[bad_spec]` **anon 축이 열려 있고, 마이그레이션 주석이 그 반대를 사실로 단정했다.** 실측 `relacl` = `anon=awdDxtm`(w=UPDATE 포함), `has_column_privilege('anon',…,'view_count','UPDATE')=true`. 0011은 anon의 SELECT만 회수했다 — 지금 anon 쓰기를 막는 건 RLS(0행)뿐이고, 이 스토리가 "컬럼을 못 막는다"고 선언한 바로 그 층이다. → Execution 5번 블록(`revoke insert, update, delete ... from anon`)·AC·테스트 ⑦ 신설.
  - `[medium]` `[bad_spec]` **권한 완전성 테스트가 기대 컬럼 집합을 하드코딩해, 잡으려던 함정을 구조적으로 못 잡는다.** 3번 블록이 테이블 전체 UPDATE를 회수했으므로 "GRANT 목록에 없는 컬럼 = 쓰기 불가"가 기본값이 됐는데, 리터럴 비교라 0020 이후 추가된 컬럼의 누락은 보이지 않는다(리뷰 재현: `add column dealer_note` 후 권한 false인데 테스트 green). → 기대 집합을 `information_schema.columns`에서 실시간 도출 + (anon·authenticated) × (INSERT·UPDATE) 4조합으로 확장.
  - `[medium]` `[bad_spec]` **RPC 파라미터명 계약을 아무도 검증하지 않는다.** 테스트는 전부 위치 인자로 부르는데 프로덕션(PostgREST/supabase-js)은 명명 인자로 부른다. 이름만 바꾸면 pytest는 green인 채 프로덕션만 PGRST202로 깨지고, Supabase 클라이언트에 `<Database>` 제네릭이 없어 `tsc`도 못 잡으며 page.tsx가 에러를 삼켜 화면도 멀쩡하다 — 초록 게이트 3개를 통과한 채 `view_count`가 영원히 0에 머무른다(리뷰 재현). → 테스트 ⑩·AC 신설.
  - `[medium]` `[bad_spec]` **조회 1회마다 `updated_at`이 갱신돼 컬럼 의미가 조용히 바뀐다.** 0002의 `listings_set_updated_at`이 무조건 BEFORE UPDATE라 RPC의 UPDATE에도 발동한다(오케스트레이터 재현: RPC 1회에 `23:52:40 → 23:52:53`). `updated_at`은 관리자 거래내역이 **거래일**로 쓰고 `db-schema-guide.md`가 "수정 시각"으로 문서화한 값이다. → Execution 5번 블록에 트리거 `when (new.view_count is not distinct from old.view_count)` 가드 신설(공유 함수 `set_updated_at()`는 미변경 — 다른 테이블도 쓴다).
- 반증됨(재확인 후 기각):
  - `sold` 매물에 RPC를 **직접** 호출하면 증가한다는 지적 — 재현은 됐으나(오케스트레이터 실측) intent의 Never가 함수 내 상태 체크를 명시적으로 금지했고, 상세 페이지는 `on_sale`만 조회하므로 호출 지점에서 도달 불가. 함수가 데이터를 반환하지 않아 FR11(판매완료 비노출) 위반 소지도 없다.
  - 판매자가 자기 매물을 새로고침해 조회수를 부풀린다는 지적 — intent의 Never가 악용 방지 로직(rate limit·세션당 1회)을 데모 규모 근거로 명시 배제했다. 소유자 제외도 같은 축의 판단이라 intent 권한 밖.
  - `service_role`이 여전히 전체 UPDATE 권한을 갖는다는 지적 — project-context 규칙 6이 `service_role` 키를 어디에도 두지 못하게 하므로 도달 경로가 없다.
  - 그 외 5건(프리페치 결합을 주석으로 고정 · 배포 순서를 Verification에 명시 · `.test.tsx` 확장자 필터 · 비프로덕션에서 RPC 실패를 throw · pgvector 스텁 때문에 `grant update (embedding)`이 실제 vector 타입으로 미검증) — 노이즈이거나 이미 상위 규약(CLAUDE.md B3)·기존 대장 항목이 덮는다.
- deferred (대장 `docs/tech-debt.md`에 **신규 항목으로만** 등재 — 기존 항목은 건드리지 않음. `deferred-work.md`는 2026-07-15 동결로 신규 기입 금지):
  - `[medium]` #134 — `anon`이 `view_count`를 **읽지** 못한다(0011 화이트리스트 미포함). 비로그인 인기 정렬이 통째로 42501로 깨진다(실측: `select view_count`·`order by view_count` 둘 다 `permission denied for table listings`). intent의 Never가 이 GRANT를 Story 11.4의 몫으로 명시했으므로 이 스토리에선 고치지 않되, **11.4의 선결 조건**으로 대장에 남긴다.
  - `[medium]` #135 — GRANT 목록에 `embedding`·`id`가 포함돼 판매자가 자기 매물의 AI 검색 벡터와 기본키를 직접 바꿀 수 있다. 0020 이전부터 있던 권한이라 회귀는 아니지만(#131과 같은 축, 더 큰 영향) 0020이 명시적 화이트리스트로 성문화했다.
  - `[low]` #136 — Flutter 앱 상세 화면은 조회수를 올리지 않고, 단일성 검사도 `web/src`만 본다. `view_count`의 실제 의미가 "웹 상세 열람"이 되는데 어디에도 기록돼 있지 않다.
  - `[low]` #137 — `docs/db-schema-guide.md`(발표용 스키마 설명)의 listings 컬럼 표·마이그 인덱스가 노후. 이 스토리가 컬럼을 하나 더 늘렸다.

### 2026-07-27 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 1, low 4)
- defer: 4 (medium 2, low 2)
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` `0020_listings_view_count.sql`의 `alter table ... add column view_count ...`가 이 저장소의 컬럼 추가 선례(`0007_listings_seller_name.sql`·`0009_profiles_name.sql`·`0017_listings_trust_attributes.sql`가 전부 `add column if not exists`)와 달리 가드가 없었다(blind-hunter 지적, 실측으로 선례 확인). `if not exists`로 정정.
  - `[low]` `[patch]` 존재하지 않는(또는 이미 삭제된) `listing_id`로 RPC를 호출하면 조용히 0행 UPDATE로 성공 처리되는데 이를 고정하는 테스트가 없었다(blind-hunter·edge-case-hunter 동일 지적). 의도된 동작(에러 없이 무시)임을 테스트로 고정.
  - `[medium]` `[patch]` "호출 지점을 상세 페이지 한 곳으로 한정하는 것이 유일한 안전장치"라는 핵심 불변식이 주석에만 있고 실행되는 검사가 없었다(intent-alignment auditor 지적, CLAUDE.md B9 "주석·문서는 계약이 아니다"). `increment_listing_view` 호출이 웹 소스 트리에 정확히 1곳(상세 페이지)만 있음을 고정하는 테스트를 추가.
  - `[low]` `[patch]` 컬럼 단위 REVOKE/GRANT 하드닝을 위해 하드코딩한 24개 컬럼 GRANT 목록이, 향후 `listings`에 새 컬럼이 추가될 때 이 목록 갱신을 깜빡하면 그 컬럼이 authenticated에 조용히 UPDATE 불가 상태가 되는 유지보수 함정이다(blind-hunter·edge-case-hunter 동일 지적). `0011`이 anon SELECT 목록에 이미 쓴 것과 같은 경고 주석을 추가.
  - `[low]` `[patch]` 회귀 방지 테스트(`test_authenticated_can_still_update_other_columns`)가 `price` 컬럼 하나만 스팟체크해, 다른 컬럼이 실수로 GRANT 목록에서 빠져도 못 잡는다(edge-case-hunter 지적). `information_schema.column_privileges`로 "view_count를 제외한 전 컬럼에 UPDATE 권한이 있고 view_count만 없다"를 한 번에 검증하는 테스트로 보강.
- 반증됨(재확인 후 기각, blind-hunter·edge-case-hunter 원 지적 유지 안 함):
  - edge-case-hunter가 제기한 "Next.js `<Link>` 자동 prefetch가 실제 방문 없이 상세 페이지를 렌더해 조회수를 올릴 수 있다"는 지적을 Next.js 16 공식 문서(`node_modules/next/dist/docs/01-app/02-guides/prefetching.md`, 이 저장소 실치 버전 그대로)와 대조해 직접 확인했다 — "Dynamic page"는 `loading.js`가 없으면 prefetch 자체가 안 된다(공식 표: "Prefetched: No, unless loading.js"). 이 라우트는 `export const dynamic = 'force-dynamic'`이고 `loading.tsx`가 리포 어디에도 없음을 확인(`find` 실측) — 이 시나리오는 지금 설정에서 발생할 수 없다. **재보지 않고 선언하지 않는다(CLAUDE.md B4)는 원칙에 따라 실측으로 기각.**
- deferred (대장 `docs/tech-debt.md`에 신규 항목으로 등재 — `deferred-work.md`는 2026-07-15 동결로 신규 기입 금지, 프로젝트 규칙 우선):
  - `[low]` #130 — 상세 페이지(`listings/[id]/page.tsx`)가 서로 독립적인 조회(갤러리 URL·판매자 요약 RPC·조회수 RPC)를 순차 `await`로 체인해 회피 가능한 요청 폭포(waterfall)를 만든다. 이번 스토리가 세 번째 인스턴스를 추가했을 뿐 기존 패턴(갤러리+판매자요약)에서 이미 있던 것(blind-hunter 지적). 트리거: 이 페이지의 SSR(서버사이드 렌더링) 지연이 실측으로 문제가 될 때.
  - `[medium]` #131 — `listings.seller_name`은 BEFORE INSERT 트리거(0007)로만 위조를 막고 BEFORE UPDATE 트리거는 없어, 판매자가 등록 후 언제든 직접 UPDATE로 표시 이름을 바꿀 수 있다. 이번 마이그레이션이 UPDATE 권한 전체를 재감사하는 유일한 기회였지만 이 gap은 그대로 물려받았다(blind-hunter 지적, grep으로 트리거 부재 확인). 트리거: `listings` UPDATE 권한을 다시 감사하는 다음 마이그레이션, 또는 판매자 표시 이름 위조가 실제 이슈로 보고될 때.
  - `[medium]` #132 — 상세 페이지의 `get_seller_public_summary`·`increment_listing_view` 두 RPC 호출 모두, page.tsx가 실제로 그 RPC를 호출하는지 검증하는 테스트가 전무하다(verification-gap·intent-alignment 공통 지적). 이 저장소의 기존 관례(서버 컴포넌트의 RPC 배선은 코드리뷰로만 확인, 어떤 `*.test.ts(x)`도 `supabase.rpc(...)`를 mock하지 않음)를 그대로 물려받은 것. 트리거: web에 서버 컴포넌트 레벨 테스트 하네스(supabase 클라이언트 mock 등)가 도입될 때.
  - `[low]` #133 — 이 저장소의 실DB 통합 테스트(`test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`·신규 `test_view_count_rpc_real_db.py` 전부)가 `set local role`로 Postgres 역할만 바꿔 검증할 뿐, 실제 프로덕션 경로인 PostgREST/`supabase.rpc()` HTTP 계층은 한 번도 거치지 않는다(blind-hunter 지적). 트리거: web에 E2E 계층이 도입되거나(#106과 유사 축) PostgREST 노출 설정 자체가 회귀 대상이 될 때.

## Design Notes

**하드닝 패턴 선례:** `0019_seller_public_summary.sql`이 이미 이 리포에서 검증된 "SECURITY DEFINER + search_path 고정 + REVOKE ALL FROM PUBLIC + GRANT TO anon,authenticated" 조합을 쓰고 있다. 이번 함수는 그 패턴을 그대로 따르되, 그 함수와 반대로 **쓰기**(UPDATE) 동작이라 컬럼 단위 REVOKE(`authenticated`의 `view_count` 직접 UPDATE 차단)가 추가로 필요하다.

**"멱등"의 실제 의미:** AC의 "AI 카드 렌더링 시 중복 증가하지 않는다"는 DB 레벨의 멱등성(같은 호출을 여러 번 해도 결과가 같음)을 요구하는 게 아니다 — RPC는 호출될 때마다 항상 +1 한다(멱등이 아님, 의도된 동작). 실제로 지켜야 하는 건 **"호출 지점을 상세 페이지 서버 컴포넌트 한 곳으로 한정"**하는 것뿐이다. `ListingCard`는 표시 전용이라 애초에 이 RPC를 호출할 이유가 없으므로, Code Map/Tasks에 적힌 대로만 구현하면 자동으로 만족된다.

**대장 점검 (workflow persistent fact 이행):** 착수 시 `deferred-work.md`에서 `status: open`인 `DW-1`을 발견했다(bmad-loop 엔진이 직접 기입, `docs/tech-debt.md` #129가 이미 이 경로를 설명함). 실체(11-0 리뷰 잔여 권고)는 `docs/tech-debt.md` #124~#128에 이미 전부 등재돼 있어 **중복 이관 불필요** — 이 스토리에서는 아무 것도 하지 않는다(조건 ①).

**anon 남용 방어 미구현 근거:** 리서치 문서(`research-supabase-viewcount-rpc.md` §Q3·§5)가 "동일 매물에 무한 재호출 시 조회수 조작 가능 + Supabase는 DB/RPC 레벨 rate limit을 내장하지 않음"을 확인했지만, 데모 규모(실사용자 트래픽 없음)에서는 실질 위협이 없어 방어 로직을 넣지 않기로 한다(A2). 실서비스 전환 시 반드시 필요한 보완이라는 점만 기록.

## Verification

**Commands:**
- `python3 scripts/check_migrations.py` -- expected: 신규 마이그레이션이 `NNNN_이름.sql` 규약(4자리·유일·밀집)을 통과.
- `cd api && TEST_DATABASE_URL=... pytest tests/integration/test_view_count_rpc_real_db.py -v` -- expected: 신규 테스트 전부 green.
- **마이그레이션 게이트의 동적 절반을 로컬에서 재현한다**(CI `migration-gate.yml`은 `develop`/`main` push·PR에서만 도는데 이 작업은 `test/bmad-loop` 브랜치라 이번 변경엔 한 번도 돈 적이 없다 — 게이트 통과가 이 스토리의 DoD이므로 로컬 재현이 그 대역이다): Docker가 없으면 로컬 Postgres 18로 스크래치 클러스터를 띄우고 `scripts/migration-check-prelude.sql` → `supabase/migrations/*.sql` 전량을 번호순으로 적용. pgvector가 없으면 `create extension ... vector`·`vector(768)`·hnsw 인덱스만 사본에서 무력화하고 **레포 원본은 절대 수정하지 않는다**. 무력화한 부분은 검증되지 않았다고 결과에 명시한다.
- `python3 scripts/check_migrations.py`의 **종료 코드를 결과에 그대로 적는다.** Docker가 없으면 이 스크립트는 정적 검사만 통과시킨 뒤 스스로 "정적 검사만으로는 게이트 통과로 인정하지 않는다 — 실패 처리"를 출력하고 **exit 1** 한다. 마이그레이션 게이트 통과는 intent가 못박은 DoD이므로, "정적 검사 통과"만 적고 게이트가 통과한 것처럼 기록하지 않는다 — 스크래치 Postgres 재현은 **대역이지 게이트가 아니다**.
- **red/green 증명(B4 — "만들었다"가 아니라 "잡는다"가 완료다).** 새 방어선마다 일부러 깨서 red를 확인한 뒤 되돌려 green을 재확인하고, 그 사실을 결과에 기록한다. **좁히는(narrowing) 변형만으로는 부족하다** — 2차 리뷰에서 "없애는/넓히는 변형"이 전부 green으로 통과했다. 최소 이 목록: ① UPDATE 축 회수 제거 ② INSERT 축 회수 제거 ③ anon 축 회수 제거 ④ **트리거를 통째로 drop** ⑤ **트리거를 `after update`로 재생성**(함수가 무력화된다) ⑥ 트리거 함수에서 `created_at` 보존 줄 제거 ⑦ RPC 본문을 no-op으로 교체 ⑧ GRANT 목록에 없는 새 컬럼 추가 ⑨ 호출 지점을 하나 더 추가 — **리터럴 형태와 우회 형태(백틱 리터럴, `const FN = '...'` 상수 경유) 셋 다** ⑩ page.tsx의 인자 키를 `p_listing_id`에서 다른 이름으로 변경.
- **시드 재적용 확인:** 스크래치 클러스터에 마이그레이션 전량 적용 후 `supabase/seed-local/02_data.sql`의 `listings` 삽입문을 실제로 돌려 103행이 들어가는지 확인한다(`\set`·`\cd`가 psql 전용이므로 `seed_local_dir` 변수를 넘겨 실행하거나 해당 삽입문만 떼어 검증). 고치기 **전** 상태에서 not-null 위반으로 죽는 것을 먼저 확인하고(red), 고친 뒤 green을 확인한다.
- **CI 등가 실행:** `TEST_DATABASE_URL=... pytest tests/integration -q`(파일 하나가 아니라 디렉터리 전체 — `.github/workflows/tests.yml`의 `api-db` 잡이 실제로 도는 형태)로 한 번 돌려, 이 스토리가 만든 실패와 기존 실패를 구분해 결과에 적는다.

**Manual checks (if no CLI):**
- 로컬 Supabase(Docker) + `web` dev 서버 기동 후, 특정 `on_sale` 매물의 `view_count`를 psql로 확인 → 그 매물 상세 페이지(`/listings/[id]`)를 브라우저로 열기 → psql로 재확인해 값이 정확히 1 증가했는지 확인. 새로고침 시 다시 +1 되는지도 함께 확인(멱등 아님이 의도임을 실제로 관찰).

## Auto Run Result

_이 절은 **가장 최근 실행(2026-07-28, 후속 리뷰 3차)** 의 결과다. 이전 사이클의 경위는 `## Spec Change Log`와 `## Review Triage Log`가 보관한다._

**요약:** `listings.view_count` 컬럼 + `increment_listing_view` SECURITY DEFINER RPC를 추가하고, 쓰기 경로 3축(authenticated UPDATE·INSERT, anon 직접 쓰기)을 GRANT 층에서 전부 회수해 "RPC가 유일한 쓰기 통로"를 실제로 참으로 만들었다. 조회수 증가가 `updated_at`("수정 시각")을 덮어쓰지 않도록 `listings` 전용 타임스탬프 트리거로 교체하되 `created_at` 위조 차단은 살렸고, `not null` 신규 컬럼이 로컬 시드를 통째로 죽이던 문제도 함께 고쳤다. 상세 페이지 서버 컴포넌트가 매물 확인 후 이 RPC를 정확히 1회 호출한다. 이번 패스 리뷰(4개 렌즈)에서 patch 5건 반영, defer 7건(#141~#147) 대장 신규 등재, reject 7건.

**Files changed:**
- `supabase/migrations/0020_listings_view_count.sql` (신규) -- view_count 컬럼 + RPC 하드닝(0019 패턴) + UPDATE·INSERT·anon 3축 GRANT 수술 + `listings_set_timestamps()` 전용 트리거.
- `web/src/app/(user)/listings/[id]/page.tsx` -- 매물 확인 후 RPC 1회 호출, 실패는 `console.error`만(`sellerSummaryError` 패턴).
- `api/tests/integration/test_view_count_rpc_real_db.py` (신규) -- 실DB 통합 테스트 22건(증가·누적·직접 UPDATE/INSERT 거부·anon 권한 부재·권한 완전성 4조합·`updated_at` 양방향·`created_at` 위조 차단 2경우·명명 인자 계약·실제 등록 페이로드 회귀·**anon 열람 유지**).
- `web/src/app/(user)/listings/[id]/__tests__/viewCountCallSite.test.ts` (신규) -- 호출 지점 단일성 + 인자 키·가드 위치 + **실제 호출 형태**(주석 우회 차단) 3건.
- `supabase/seed-local/02_data.sql` -- `listings` 삽입문만 `select *` → 명시 컬럼 목록(다른 테이블 미변경, A3).
- `docs/tech-debt.md` -- defer 신규 등재(이번 패스 #141~#147, 누적 #130~#147).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- 11-1을 `backlog → done`.

**리뷰 결과 (2026-07-28 3차 패스):** intent_gap 0 · bad_spec 0 · patch 5(medium 3, low 2, 전부 반영) · defer 7(medium 2, low 5) · reject 7. 상세는 `## Review Triage Log` 참조.

**Follow-up review recommendation:** `true` — 이번 패스 patch 점수 = 3×3(medium) + 1×2(low) = **11** (≥5 기준 충족). high 없음.

**검증 수행 (전부 이 세션에서 직접 실행·관찰):**
- `python3 scripts/check_migrations.py` -- 정적 검사(20개 파일) 통과, Docker 부재로 동적 검사 건너뜀, **exit 1**. ⚠️ **마이그레이션 게이트는 통과하지 않았다** — 게이트 통과가 이 스토리의 DoD인데(conventions §9.4) 이 샌드박스엔 Docker가 없다. 아래 스크래치 Postgres 재현은 **대역이지 게이트가 아니다.**
- **게이트 동적 절반의 로컬 재현:** 로컬 Postgres 18로 스크래치 클러스터를 띄우고 `scripts/migration-check-prelude.sql` + 마이그레이션 20개를 번호순 전량 적용 → 성공. **pgvector가 없어 `create extension vector`·`vector(768)`·hnsw 인덱스 2개를 사본에서 무력화했고(레포 원본 미변경), 그 부분은 검증되지 않았다.**
- **검증 중 실제 결함 1건 발견·수정:** 이미 0020이 적용된 DB에 0020을 다시 적용하면 `ERROR: trigger "listings_set_timestamps" for relation "listings" already exists`로 죽었다(**실측 exit 3**). 리포 관례(0007·0008·0016)는 전부 `create trigger` 직전에 **만들 이름**을 `drop trigger if exists` 하는데 0020은 옛 이름만 지웠다. `drop trigger if exists listings_set_timestamps` 한 줄을 추가해 고쳤고 재적용 exit 0을 재확인. 이 성질을 지키는 검사가 없다는 점은 #143으로 등재.
- `TEST_DATABASE_URL=... pytest tests/integration -q` (**디렉터리 전체 = CI `api-db` 잡과 같은 형태**) -- **1 failed, 38 passed.** 실패 1건은 `test_seller_summary_real_db.py::test_anon_can_read_joined_at_despite_profiles_rls`이며, **0019까지만 적용한 대조 DB에서도 동일하게 실패**함을 직접 확인해 이 스토리와 무관한 기존 red임을 재확정했다(대장 #138).
- **red/green 증명 12종** — 전부 일부러 깨서 red 확인 → 되돌려 green 재확인:
  ① UPDATE 축 회수 제거(2 failed) ② INSERT 축 회수 제거(2) ③ anon 축 회수 제거(3) ④ 트리거 통째로 drop(3) ⑤ 트리거를 `after update`로 재생성(3) ⑥ 트리거 함수에서 `created_at` 보존 줄 제거(2) ⑦ RPC 본문 no-op(5) ⑧ GRANT 목록에 없는 새 컬럼 추가(2) ⑨ 두 번째 호출 지점 추가 — **리터럴·백틱·`const FN` 상수 경유 3형태 전부 red** ⑩ page.tsx 인자 키를 `p_listing_id` → 다른 이름(red) ⑪ anon 화이트리스트 컬럼 SELECT 회수(red — 신규 P1 검사) ⑫ anon에 `update (price)` 부여(red — 신규 P2 프로브). 추가로 **RPC 호출 3줄 주석 처리** 시 신규 P3 단언만 red가 되고 기존 2건은 green으로 남는 것을 확인(지적된 증상 그대로 재현).
- **시드 red/green:** 고치기 **전**(`select *`) 상태로 돌려 `null value in column "view_count" ... violates not-null constraint`로 1단계에서 멈추고 뒤따르는 단계가 **전부 0행**임을 확인(red) → 고친 버전으로 `listings` **103행**(`view_count` 합 0) + `listing_images` 180 + `chat_rooms` 5 + `chat_messages` 10 + `guide_documents` 10 전부 적재 확인(green).
- **web:** `tsc --noEmit` clean · `eslint src --max-warnings=0` clean · `vitest run` **17개 파일 215건 전부 green**.
- **최종 확인은 깨끗한 새 DB에서 다시 돌렸다** — 패치 반영 후 데이터베이스를 새로 만들어 마이그레이션 전량 적용 → 재적용 멱등 확인 → 시드 적재 → pytest 전체 → web 3종을 한 번에 재실행했다(서브에이전트 보고를 검증으로 치지 않는다, B4).
- **매트릭스 감사:** intent-contract I/O 매트릭스 4행 중 2·3·4행(authenticated 직접 UPDATE 거부 / anon·authenticated RPC 호출 성공+1 / 그 외 롤 EXECUTE 거부)은 통과한 실DB 테스트가 직접 덮는다. 1행(상세 페이지 진입 시 +1)은 **두 조각으로만** 덮인다 — RPC가 정확히 +1 한다는 DB 테스트 + 호출이 상세 페이지 가드 뒤에 살아 있다는 정적 검사. **브라우저→PostgREST→DB 전 구간을 실행하는 검사는 없다**(아래 참조).

**대장 점검 (workflow persistent fact 이행):** `deferred-work.md`의 `status: open` 항목은 `DW-1` 하나이며, 그 실체(11-0 리뷰 잔여 권고)는 `docs/tech-debt.md` #124~#128에 이미 전부 등재돼 있다 → **DW-1: 이미 #124~#128에 있음**(조건 ①, 중복 이관 불필요). 동결 파일은 건드리지 않았다.

**완료하지 못한 것:**
- **마이그레이션 게이트(DoD) 미통과** — Docker 부재로 `check_migrations.py`가 exit 1이다. 위 스크래치 재현이 동적 절반을 대신했지만 게이트 자체는 통과하지 않았다.
- **브라우저 수동 확인 미수행** — 로컬 Supabase 스택(Docker)과 `web` dev 서버를 띄워 실제 상세 페이지를 방문하고 `view_count` 증가를 psql로 대조하는 절차는 이 샌드박스에 Docker·Supabase CLI가 없어 문자 그대로 실행하지 못했다. 따라서 **Next.js → supabase-js → PostgREST → DB의 실제 HTTP 경로는 한 번도 거치지 않았다**(대장 #133이 이 gap을 기록, #132는 page.tsx 배선 미검증을 기록).
- **pgvector 의존 구문 미검증** — 스크래치 재현에서 `vector(768)`·hnsw 인덱스를 무력화했으므로 그 부분은 이 세션에서 확인되지 않았다.

**잔여 위험:** 대장 #130~#147. 이번 패스가 새로 연 것은 #141~#147이며, 그중 주의할 둘은 **#143**(게이트가 재적용을 안 봐서 이번 스토리가 실제로 그 구멍에 빠졌다 — 지금은 고쳐졌지만 지키는 검사가 없다)과 **#146**(시드 컬럼 목록의 조용한 누락 + 나머지 4개 삽입문에 같은 함정이 남아 있다)이다. **#138**은 병합 전에 반드시 답해야 한다 — `develop` 병합 시 CI가 이 브랜치에서 처음 도는데 이 스토리와 무관한 이유로 red가 난다. 전부 낮음~중간 심각도이며 이 스토리를 막지 않는다.

---

## 원격 적용 전 원문 스냅샷 (2026-07-28, 배포런북 §7-1-b)

`0020_listings_view_count.sql`은 **기존 객체를 교체**한다(트리거 `listings_set_updated_at` drop + 테이블 GRANT 재구성). 런북 §7-1-b가 *"적용 전에 원격의 현재 원문을 떠서 스토리에 붙인다"* 를 요구하므로(Story 9.7에서 원문이 남지 않아 되돌려 확인할 수 없었던 사고가 근거), **원격 `encar-demo`(psrnsasxpkpwqdukjdmt)의 적용 직전 상태**를 아래에 보존한다.

### 교체 대상 트리거 (0020이 drop한다)
```sql
CREATE TRIGGER listings_set_updated_at BEFORE UPDATE ON public.listings
  FOR EACH ROW EXECUTE FUNCTION set_updated_at()
```

### 그 트리거가 쓰던 공유 함수 (0020은 이 함수를 **건드리지 않는다**)
```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
begin
  new.updated_at := now();
  new.created_at := old.created_at;
  return new;
end;
$function$
```
→ 0020 적용 후 이 함수는 **참조 트리거 0건의 고아**가 된다(대장 `#142`가 이미 등재한 사실을 원격에서도 확인).

### 함께 존재하는 트리거 (0020이 건드리지 않음 — 회귀 감시 대상)
```sql
CREATE TRIGGER listings_set_seller_name BEFORE INSERT ON public.listings
  FOR EACH ROW EXECUTE FUNCTION set_listing_seller_name()
```

### 적용 직전 컬럼 GRANT (0020이 재구성한다)
- `authenticated` INSERT/UPDATE — **25개 컬럼 전량 보유**(`view_count`는 아직 없음). 0020이 테이블 단위 권한을 회수하고 같은 25개를 다시 부여한다 → **회귀 없음**을 이 목록으로 대조할 수 있다.
- `anon` INSERT/UPDATE — **25개 컬럼 전량 보유**. 0020의 5번 블록이 이것을 회수한다(정당한 쓰기 경로가 없으므로). 0020 주석의 *"실측: anon이 쓰기 권한을 갖고 있다"* 가 원격에서도 사실임을 확인.
- `anon` SELECT — 20개 컬럼(`embedding`·`updated_at` 제외). **`view_count`가 없다** = 대장 `#134`가 경고한 상태 그대로이며, `0021`이 이것을 고친다.
- `anon`/`authenticated` REFERENCES — 25개 컬럼 보유. 0020·0021 모두 이 축을 건드리지 않는다(대장 `#139`가 등재한 잔여 권한).
