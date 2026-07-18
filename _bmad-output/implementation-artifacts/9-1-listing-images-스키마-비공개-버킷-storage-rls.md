---
baseline_commit: cb6cba50a1f3ea4c1fd91753da562ba4a9c96fa3
---

# Story 9.1: listing_images 스키마 + 비공개 버킷 + Storage RLS

Status: done

> ⚠️ **이 스토리의 이미지 스토리지 설계(비공개 버킷 + 서명 URL)는 Story 9.0(마이그 `0014`)으로 대체됐다** — 버킷은 공개, URL은 고정이다. 아래 본문은 **당시 결정의 기록**이며 지금 따라야 할 계약이 아니다. 현재 계약: `docs/conventions.md` §6.1·§10.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 판매자,
I want 내 매물 사진을 안전하게 저장할 공간이 마련되길,
so that 사진을 올리면 나만 관리하고 구매자에게만 노출된다.

---

## ⚠️ 이 스토리를 시작하기 전에 (30초 요약)

**이건 DB 전용 스토리다. web·app·api 코드는 한 줄도 안 짠다.** 사진 업로드 UI는 9.3, 서명 URL 헬퍼는 9.2, AI 카드는 9.6이다. 여기서 만드는 건 **마이그레이션 `0012_listing_images.sql` 하나 + 계약 문서 + 판단 기록**뿐이다.

**이 스토리에는 다른 마이그 스토리에 없는 함정이 셋 있다:**

1. **마이그레이션 게이트(CI)가 그냥은 깨진다.** 게이트의 도커 프렐류드(`scripts/migration-check-prelude.sql`)에 **`storage` 스키마가 아예 없다** — 이 레포 최초의 storage 마이그레이션이라서다. 프렐류드를 **실측 근거와 함께** 확장하는 게 이 스토리의 일부다(AC5).
2. **GRANT 축을 건드린다** — 기술부채 #18. 판정은 **(a′): 승인 대기 없음, 대신 실측 증거 필수**. 회고(`epic-8-retro`)엔 아직 "(b) 승인 필요"라고 적혀 있는데 **그건 낡았다**(2026-07-16에 (a′) 신설). 정본은 `docs/conventions.md` §9.3.
3. **게이트 초록은 "storage RLS가 듣는다"를 증명하지 않는다.** 게이트는 우리가 만든 **스텁**을 테스트하지 Supabase를 테스트하지 않는다(런북 §8-③). 그래서 **원격에 적용한 뒤 실제로 행을 넣고 롤별로 조회해 보는 것**(AC7)이 이 스토리의 진짜 완료 조건이다. **"정책을 만들었다"는 완료가 아니다.**

---

## Acceptance Criteria

### AC1 — `listing_images` 테이블 (마이그 `0012`, 원장 정본)

**Given** 마이그레이션 `supabase/migrations/0012_listing_images.sql`
**When** 적용하면
**Then** 아래 테이블이 생성된다 — **컬럼은 이 목록이 전부다**(계약이 열거한 것 외 추가 금지):

```
listing_images(
  id           uuid PK default gen_random_uuid(),
  listing_id   uuid not null references public.listings(id) on delete cascade,
  storage_path text not null unique,      -- 버킷 내 오브젝트 key = storage.objects.name 과 동일 문자열
  sort_order   int  not null default 0,
  is_cover     boolean not null default false,
  credit       jsonb                       -- nullable. 9.7 Commons 사진의 저작자·라이선스·원본링크
)
```

**And** `storage_path`에 **UNIQUE**가 걸린다 — storage.objects 읽기 정책이 이 컬럼으로 조인하므로 중복이면 정책이 모호해진다(AC4).
**And** **매물당 대표는 최대 1장**이 부분 유니크 인덱스로 강제된다: `unique index ... on listing_images(listing_id) where is_cover`.
**And** 조회용 인덱스 `(listing_id, sort_order)`가 있다(api가 on_sale id 목록으로 대표 1장을 뽑는 경로 — 9.6).
**And** 이 마이그는 **self-contained**하다 — 자기보다 **앞 번호** 마이그(0002 listings·0006 ai_readonly)와 프렐류드가 선언한 플랫폼 계약면에만 의존한다. 뒤 번호의 객체를 가정하지 않는다.

### AC2 — 비공개 버킷 + 업로드 상한

**Given** 같은 마이그레이션
**When** 적용하면
**Then** 버킷 `listing-images`가 **비공개(`public = false`)** 로 생성된다(`on conflict (id) do nothing` — 재적용 안전).
**And** **장당 5MB 상한**이 `storage.buckets.file_size_limit = 5242880`으로 **DB에 박힌다**(클라 검증은 우회 가능 — 규칙 B9 "규칙은 어길 수 없는 자리에 박는다").
**And** **매물당 최대 10장**이 `listing_images`의 **BEFORE INSERT 트리거**로 강제된다(초과 시 한국어 메시지로 `raise exception`). 기존 패턴 = `0003c_chat_room_integrity.sql`의 무결성 트리거. 트리거 함수는 `0002_listings.sql:123`의 관례대로 `revoke execute ... from public, anon, authenticated`한다(RPC로 직접 호출 차단).
**And** `allowed_mime_types = ['image/jpeg','image/png','image/webp']`로 제한한다. **왜(계약 밖 추가의 근거)**: 비공개 버킷이라도 서명 URL은 브라우저가 그대로 연다 — 타입 제한이 없으면 `.html`/`.svg` 업로드가 우리 도메인에서 실행되는 저장형 XSS가 된다. 상한 2개(용량·장수)와 같은 자리에 있어야 할 세 번째 상한이다.

### AC3 — Storage 경로 규칙

**Given** 비공개 버킷
**When** 경로 규칙을 정하면
**Then** 규칙은 **`{auth.uid()}/{listing_id}/{filename}`** — **첫 세그먼트가 소유자**다(쓰기 정책이 이 사실에 의존).
**And** **신규 등록은 매물 행을 먼저 insert해 `listing_id`를 얻은 뒤** 그 경로로 업로드한다(스테이징 경로·이동 없음 — A2 단순). 이 순서를 계약 문서에 명시해 9.3이 따르게 한다.
**And** `listing_images.storage_path`에는 **버킷 내 key 전체**(`{uid}/{listing_id}/{filename}`)를 저장한다 — 버킷명은 포함하지 않는다. 이 값이 `storage.objects.name`과 **글자 그대로 같아야** AC4의 조인이 성립한다.

### AC4 — `storage.objects` RLS 정책 2종 (동거, service_role 금지)

**Given** `storage.objects`
**When** 정책을 만들면
**Then** **쓰기** = `bucket_id = 'listing-images'` **AND 첫 경로 세그먼트 = `auth.uid()`** 인 경우에만 `authenticated`가 insert/update/delete 할 수 있다.
**And** **읽기(SELECT)** = `bucket_id = 'listing-images'` **AND** 그 오브젝트를 가리키는 `listing_images` 행의 매물이 **`status='on_sale'` 이거나 `seller_id = auth.uid()`** 일 때만 `anon`·`authenticated`에게 허용된다.
  - **이 정책이 없으면 서명 URL 발급 자체가 실패한다** — 서명은 발급자의 `storage.objects` SELECT 권한을 전제로 한다(아키텍처 236행).
  - 이것이 **FR11(판매완료 비노출)의 스토리지 레이어 강제**이자 **FR58(비로그인 열람)** 의 성립 조건이다.
**And** 두 정책은 **이 마이그레이션에 동거**한다(규칙 10 — RLS는 해당 객체 마이그에 함께).
**And** `service_role`은 **어디에도 등장하지 않는다**(규칙 6).
**And** 읽기 정책은 **`public.is_admin()`을 호출하지 않는다** — 이 함수는 `authenticated`에게만 execute가 부여돼 있어(`0001_profiles.sql:91`) anon이 걸리면 권한 오류로 **열람 전체가 깨진다**. 관리자 이미지 열람은 이 스토리 범위 밖이다.
**And** `storage.foldername()` 대신 **`split_part(name, '/', 1)`** 을 쓴다 — 순수 Postgres 함수라 프렐류드 스텁 표면이 줄어든다(AC5의 비용이 그만큼 싸진다).
**And** 마이그레이션은 `alter table storage.objects enable row level security`를 **하지 않는다** — 원격에선 플랫폼이 이미 켜뒀고, 소유자가 아닌 롤이 건드리면 실패할 수 있다.

### AC5 — 마이그레이션 게이트 통과 (이 에픽 첫 마이그의 DoD)

**Given** 게이트 프렐류드에 **`storage` 스키마가 없다**(현재 `auth`·롤·기본 GRANT만 스텁) — 이대로면 0012는 도커 검사에서 red다
**When** 프렐류드를 확장하면
**Then** 확장은 **"정당한 확장"의 조건을 만족한다** — 즉 *실제 Supabase 플랫폼에 있는데 스텁이 빠뜨려서 red가 난 것*이며, **원격에서 실측한 값을 근거로** 추가하고 **그 사실을 주석에 남긴다**(`migration-check-prelude.sql` 헤더 규칙).
**And** 스텁은 **0012가 실제로 건드리는 컬럼만** 담는다(선례: `auth.users`는 3컬럼 스텁). 추측으로 컬럼을 채우지 않는다.
**And** `python scripts/check_migrations.py`가 **로컬에서 통과**한다(도커 필요 — 도커 없이 돈 정적 검사만으론 **통과가 아니다**, 런북 §8-④).
**And** 기존 프로브 3건이 그대로 통과한다(회귀 0).
**And** `develop` push 후 GitHub Actions **"Migration Gate" 워크플로 초록**을 실제로 확인한다.
**And** ⚠️ **이 초록이 증명하지 않는 것을 스토리 기록에 명시한다** — 게이트는 *우리가 쓴 storage 스텁* 위에서 돈다. "Supabase의 진짜 storage에서 이 정책이 듣는다"는 **AC7이 증명한다**(런북 §8-③·§8-⑥).

### AC6 — 테이블 GRANT (기술부채 #18 — 이 에픽 첫 마이그가 그 축을 건드린다)

**Given** `docs/conventions.md` §9.3의 판정 **(a′)** — 승인 대기 없이 진행하되 **실측 증거 필수**
**When** `grant ... to anon / authenticated / ai_readonly` 문장을 쓰려면
**Then** **쓰기 전에** 원격 현재 권한을 실제로 떠서 **그 출력을 이 스토리의 Debug Log에 붙인다**:
```sql
select grantee, table_name, privilege_type
  from information_schema.role_table_grants
 where table_schema='public' and grantee in ('anon','authenticated','ai_readonly')
 order by table_name, grantee, privilege_type;
```
**And** ⚠️ **`listing_images`는 신규 테이블이라 "델타 0"의 의미가 다르다** — 원격엔 아직 없으므로 비교 대상이 없다. 판정은 이렇게 한다:
  - **기존 테이블들의 GRANT는 이 마이그가 건드리지 않는다** → 그 축의 델타는 0이고, 위 덤프가 그 증거다.
  - **신규 테이블에 대해서는** "우리가 명시하는 GRANT ≤ 플랫폼 기본이 어차피 줄 GRANT"인지로 가른다. Supabase 기본(`alter default privileges ... grant all to anon, authenticated`)은 새 public 테이블에 **ALL**을 자동 부여한다 → 그보다 **좁히는 것은 넓히는 방향이 아니다**(선례: `0011_listings_anon_select.sql`이 `revoke` 후 컬럼 스코프로 재부여).
  - **넓히는 방향이면 멈추고 사용자 승인**: 새 롤에 GRANT · `to public` · anon이 보면 안 되는 컬럼 노출. `listing_images` 6컬럼엔 비밀이 없다(`credit`은 9.7이 화면에 표시할 저작자 정보다) — 그렇지 않다는 판단이 서면 그때 멈춘다.
**And** `anon`에 대해 **0011과 같은 모양**으로 명시한다: `revoke select ... from anon;` 후 `grant select (id, listing_id, storage_path, sort_order, is_cover, credit) ... to anon;` — 플랫폼 기본 GRANT에 대한 암묵 의존을 끊어 self-contained를 확보한다(#18이 요구하는 방향).
**And** `ai_readonly`에 **명시 GRANT**를 준다: `grant select on public.listing_images to ai_readonly;`(선례 `0004_guide_documents.sql:58`). 0006의 `alter default privileges`에 기대지 않는다.
**And** **#18을 이 스토리에서 전부 해소하려 들지 않는다** — 나머지 테이블(profiles·chat_*)의 GRANT 명시와 프렐류드의 `alter default privileges` 제거는 범위 밖이다. 이 스토리는 **새로 만드는 테이블만** 명시한다.

### AC7 — 정책이 "있는지"가 아니라 "듣는지"를 실측한다 ★ (이 스토리의 진짜 완료 조건)

**Given** 원격 적용 완료 (`apply_migration`, name = **`0012_listing_images`** — 번호 포함, 런북 §7-3)
**When** 실제 데이터를 넣고 롤별로 조회하면
**Then** 아래 6건을 **직접 실행해 출력을 Debug Log에 남긴다**. 트랜잭션 안에서 돌리고 **`rollback`으로 정리**해 원격에 찌꺼기를 남기지 않는다:

| # | 시나리오 | 기대 |
|---|---|---|
| 1 | `on_sale` 매물의 이미지 행을 **anon**으로 SELECT | **보인다** (FR58 열람) |
| 2 | `sold` 매물의 이미지 행을 **anon**으로 SELECT | **0행** (FR11) |
| 3 | 본인 `sold` 매물의 이미지 행을 **소유자 authenticated**로 SELECT | **보인다** (본인 관리) |
| 4 | 남의 매물 경로(`{다른uid}/...`)로 **authenticated** insert (storage.objects) | **거부** |
| 5 | 같은 매물에 11번째 이미지 insert | **거부**(트리거, 한국어 메시지) |
| 6 | 같은 매물에 `is_cover=true` 두 번째 insert | **거부**(부분 유니크) |

**And** 롤 시뮬레이션은 `set local role authenticated; set local request.jwt.claim.sub = '<uuid>';` 로 한다(`auth.uid()`가 이 클레임을 읽는다 — 프렐류드의 스텁과 원격 동작이 같은 지점).
**And** ⚠️ **"에러가 없었다"로 갈음하지 않는다.** 2·4·5·6은 **거부되는 것**이 정답이라 통과가 곧 침묵이다 — 각 항목의 **실제 출력(행 수·에러 메시지)** 을 붙인다.

### AC8 — 시드 재실행 전략 판단 (기술부채 #27 — FK가 태어나는 곳)

**Given** `listing_images.listing_id FK`가 **`listings`의 첫 자식 테이블**이다
**When** 현재 시드를 확인하면
**Then** 사실을 먼저 확인해 기록한다 — `supabase/seed.sql:196`이 `delete from public.listings where seller_id = v_seller_id;` 로 **시드 매물을 지우고 새 uuid로 재삽입**한다(id는 `gen_random_uuid()` 기본값, 고정 아님).
**And** 그 결과를 명시한다: `ON DELETE CASCADE`라 **delete는 통과하지만 업로드한 이미지 행이 조용히 사라진다** — **에러 0건이라 알아챌 방법이 없다**(#27의 핵심).
**And** 전략을 **하나 택해 이 스토리에 기록한다**: **(a) 고정 id**(시드 매물 uuid를 고정해 delete-재삽입을 없앰) / **(b) 자식 정리 순서 명시**(이미지 → 매물) / **(c) 이번 증분에선 무해함을 **근거와 함께** 확인하고 이월).
**And** ⚠️ **Epic 10.5 `wishlists`가 두 번째 자식**이라는 사실을 판단에 **함께 넣는다** — `ON DELETE CASCADE`가 아니면 **delete가 아예 막힌다**. 지금 (c)를 택하면 그때 같은 자리로 돌아온다.
**And** 결정을 `docs/tech-debt.md` **#27에 반영한다**(해소면 닫고, 이월이면 트리거·근거를 갱신).
**And** **시드 파일 자체는 이 스토리에서 고치지 않는다** — 전략이 **실제로 시험되는 곳은 9.7**(시드 2회 연속 실행 후 이미지 행 수 카운트)이다. 여기서는 **판단과 기록**만 한다.

### AC9 — 계약을 코드보다 먼저 (규칙 1)

**Given** 버킷명·경로 규칙·상한은 web·app·api를 가로지르는 **공유 계약**이다
**When** 마이그를 쓰기 전에
**Then** `docs/conventions.md`에 **§10 이미지 스토리지 계약** 절을 신설한다 — 버킷명 `listing-images`(비공개) · 경로 `{user_id}/{listing_id}/{filename}` · **등록 순서(매물 insert → 업로드)** · 상한(10장/5MB/mime 3종) · `storage_path` = 버킷 내 key 전체 · **`SIGNED_URL_TTL = 3600s`**(사용자 확정 2026-07-13, 구현은 9.2).
**And** `docs/conventions.md` **§6(FR11 강제 지점 목록)에 storage 읽기 정책을 추가**한다 — **새 조회 경로를 열면 강제 지점 목록에 등록하는 것이 규칙 7이고, 경로를 열고 필터를 잊는 것이 이 규칙의 유일한 실패 모드다.**
**And** `docs/db-schema-guide.md` 갱신은 **범위 밖**이다(tech-debt에 "증분 후"로 예약돼 있음).

---

## Tasks / Subtasks

- [x] **Task 1 — 원격 실측 먼저 (AC5, AC6)** ※ 읽기 전용. 아직 아무것도 안 바꾼다
  - [x] Supabase MCP `execute_sql`로 **테이블 GRANT 덤프**(AC6의 쿼리) → 출력을 Debug Log에 그대로 붙인다
  - [x] **원격 storage 스키마 실측**: `select table_name, column_name, data_type, is_nullable from information_schema.columns where table_schema='storage' and table_name in ('buckets','objects') order by table_name, ordinal_position;`
  - [x] `select relrowsecurity from pg_class where oid = 'storage.objects'::regclass;` (RLS 켜져 있는지)
  - [x] `mcp__supabase__list_migrations`로 원격 이력 확인 — 0012가 아직 없음을 확인(런북 §8-⑧: 레포와 1:1로 안 맞는 건 정상, 놀라지 말 것)
- [x] **Task 2 — 계약을 먼저 박는다 (AC9)**
  - [x] `docs/conventions.md`에 **§10 이미지 스토리지 계약** 신설
  - [x] `docs/conventions.md` **§6 강제 지점 목록에 storage 읽기 정책 추가**
- [x] **Task 3 — `supabase/migrations/0012_listing_images.sql` 작성 (AC1~AC4, AC6)**
  - [x] 헤더 주석: `-- 0012_listing_images.sql — …` + "이 마이그레이션이 하는 일:" + self-contained 선언(0011 헤더가 본보기)
  - [x] 테이블 + UNIQUE(storage_path) + 부분 유니크(대표 1장) + 인덱스 + `comment on`
  - [x] 10장 트리거 함수 + BEFORE INSERT 트리거 + 함수 `revoke execute`
  - [x] 버킷 insert(`on conflict do nothing`, `public=false`, `file_size_limit`, `allowed_mime_types`)
  - [x] `alter table public.listing_images enable row level security`
  - [x] 테이블 정책: anon 열람 / authenticated 열람·본인 / admin / 본인 insert·update·delete / **ai_readonly `using(true)`(CR2)** — **역할별로 정책을 나눈다**(0002+0011 패턴, is_admin을 anon 경로에 태우지 않기 위함)
  - [x] `storage.objects` 정책 2종(쓰기·읽기) — `drop policy if exists` 선행(0011 관례)
  - [x] GRANT: anon revoke+컬럼 스코프 · ai_readonly 명시
- [x] **Task 4 — 게이트 프렐류드 storage 스텁 확장 (AC5)**
  - [x] Task 1의 **실측값을 근거로** `scripts/migration-check-prelude.sql`에 `storage` 스키마 + `buckets`/`objects` **최소 스텁** + `objects` RLS enable 추가
  - [x] 주석에 **"원격 실측 기반"과 그 사실**을 남긴다(프렐류드 헤더 규칙 — 우회가 아니라 정당한 확장임을 증명)
- [x] **Task 5 — 게이트 red→green (AC5, 규칙 B4)**
  - [x] `python scripts/check_migrations.py` 실행 → **통과 확인**
  - [x] **일부러 깨서 red 확인**: 0012의 storage 정책 한 줄을 임시로 앞 번호가 아닌 것에 의존시키거나 프렐류드 storage 스텁을 잠시 제거 → red 재현 → 되돌려 green. 두 출력 모두 Debug Log에
  - [x] **게이트가 안 보는 것을 옆에 적는다**(추측 말고 이번에 실측한 것으로)
- [x] **Task 6 — 기술부채 대장 갱신 (AC6, AC8)**
  - [x] `docs/tech-debt.md` **#27**: (a)/(b)/(c) 결정과 근거 반영(해소면 닫고, 이월이면 트리거 갱신 + Epic 10.5 재방문 명시)
  - [x] `docs/tech-debt.md` **#18**: 이번에 명시한 범위(listing_images만)와 남은 범위를 갱신. **닫지 않는다** — 나머지 테이블은 그대로 열려 있다
- [x] **Task 7 — 원격 적용 + 작동 실측 (AC7)** ※ **여기가 진짜 문이다**(런북 §7-1: 적용 전 게이트 로컬 통과 필수)
  - [x] `apply_migration`, name = `0012_listing_images` (**번호 포함**)
  - [x] AC7의 6개 시나리오를 트랜잭션+`rollback`으로 실행 → **출력 전문**을 Debug Log에
- [x] **Task 8 — 커밋·푸시·CI 확인 (AC5)**
  - [x] `develop`에 의미 단위 커밋(한국어 메시지)
  - [x] `git push origin develop` → GitHub Actions **Migration Gate 초록 실측 확인**(run id 기록)
  - [x] `main` 병합은 **하지 않는다**(사용자 승인 사항)
- [x] **Task 9 — Epic 8 회고 액션 이행 확인 (회고 A3·A5)**
  - [x] **A5 "실측 없이 선언하지 않는다"**: 이 스토리가 산출물(마이그·계약·대장)에 박은 주장 중 **실측 없이 적힌 것이 0건**임을 확인. 특히 프렐류드 storage 스텁은 **추측이 아니라 Task 1의 원격 덤프**에 근거해야 한다
  - [x] **A1 "대장은 하나"**: 열린 항목은 `docs/tech-debt.md`에만 적는다. `deferred-work.md`는 **동결**됐다 — 거기에 새로 쓰지 않는다

### Review Findings

_코드리뷰 2026-07-16 (새 세션·opus, 3층 병렬 적대적 리뷰: Blind Hunter / Edge Case Hunter / Acceptance Auditor). Edge Case Hunter는 `pgvector/pgvector:pg17` 도커에 프렐류드+마이그 12개를 올려 **실제로 재현**했다 — 아래 "실측" 표시가 그것이다._

**⚠️ 수정 경로 제약**: `0012`는 **이미 원격에 적용됐다**. 아래 DB 결함의 수정은 전부 **정책 술어·제약 변경**이라 `docs/conventions.md` §9.3의 (a)·(a′) 어디에도 안 들어간다 → **(b) 무조건 사용자 승인**. dev가 임의로 고칠 수 없다.

#### Decision — 해소 결과 (사용자 결정 2026-07-16)

**결정**: 수정 경로 = **`0013` 신규 전진 마이그**(B3 "뒤로 가지 말고 고치는 마이그를 하나 더"). 범위 = **`storage_path` 위조 + `for all` 좁히기 2건만 지금**, 나머지는 `docs/tech-debt.md`로 이월. AC7 = **지금 재실측**.

- [x] ✅ **[해소] ★ `storage_path` 위조 → `0013_listing_images_path_integrity.sql`로 막음.** 트리거가 소유자를 **`storage_path`에서 파싱하지 않고 `listings`에서 직접 구해** `{소유자}/{매물}/{파일명}`을 강제한다(B9). **원격 실측 대조 — 같은 스크립트, 다른 결과**: `0013` 전 = 위조행 insert **통과** → anon **1행**. `0013` 후 = 위조행 insert **거부**(한국어로 기대/실제 경로 표시) → anon **0행**. 정상 경로 등록(G1)·본인 경로 오브젝트 업로드(W1)는 **여전히 통과** — 구멍만 막고 9.3 업로더는 안 죽였다. 게이트 red→green 왕복 완료(일부러 깬 red = `column "nonexistent_column" does not exist` → 되돌려 green).
- [x] ✅ **[해소] `storage.objects` 쓰기 정책 `for all` → 3동사** — `0013`이 `owner_all` 1개를 `owner_insert`/`owner_update`/`owner_delete` 3개로 분리(CREATE POLICY는 명령을 하나만 받는다). 원격 확인: `owner_all` 사라지고 4정책(`insert`/`update`/`delete`/`read`) 존재. W1로 쓰기 허용분기가 좁힌 뒤에도 사는 것 확인.
- [x] ✅ **[해소] AC7 검증 구멍 → 재실측 완료.** 지난 AC7이 **한 번도 안 태운** 두 축을 이번에 태웠다: (1) **`storage.objects` 읽기 정책** — anon이 고아 오브젝트를 못 보고(0행), 위조로 등록되면 보이고(1행), `0013` 후 다시 못 보는(0행) 전이를 실제로 관찰. (2) **쓰기 허용 분기 대조군(W1)** — 본인 경로 insert가 **실제로 통과**하므로 `split_part(name,'/',1)=auth.uid()::text`는 옳고 9.3 업로더는 도착해도 죽지 않는다(지난 AC7 ④는 "거부=기대일치"라 이걸 구조적으로 못 잡았다). (3) **`rollback` 명시 이행** — 전 시나리오를 `begin ... rollback` 한 호출로 돌렸고 사후 카운트로 찌꺼기 0행 재확인. 실행 모델도 확정: `execute_sql` 한 호출 안에서 `set local role` + DO 블록 예외처리로 롤 전환·연속 에러 관찰이 가능하다(지난 기록이 판별 불가였던 지점).
- [x] ⚠️ **[부분해소·과장 금지] `0013`이 D2(10장 UPDATE 우회)를 좁혔지만 닫지 않았다 — 실측함.** `listing_id`만 바꾸는 UPDATE는 이제 **거부된다**(경로 2번째 세그먼트가 새 매물과 불일치). 그러나 **`storage_path`를 함께 고치면 여전히 통과**한다 — 실측: B를 10장으로 채운 뒤 `set listing_id=B, storage_path='{seller}/B/a1.jpg'` → **B가 11장**. "부수적으로 해결됐다"고 적지 않는다(B4 "재보기 전엔 선언하지 않는다"). #18 아래 이월 항목에 이 뉘앙스를 그대로 기록.

#### Decision — 이월 (tech-debt 등재)

- [x] [Review][Defer] **10장 상한 UPDATE 우회** — `0013`으로 **좁혀졌으나 미해소**(위 실측 참조). 트리거를 `before insert or update of listing_id`로 넓히는 것이 최소 수정
- [x] [Review][Defer] **버킷 선존재 시 비공개·5MB·MIME 3대 상한 동시 무효** — `on conflict do nothing`. 현재 원격 버킷은 값이 맞아 델타 0이라 급하지 않음
- [x] [Review][Defer] **관리자 sold 사진 바이너리 열람 불가** — Epic 6 관리자 매물상세가 실제로 사진을 렌더하는지 확인 후 판단(9.4·9.5가 카드/갤러리를 만들 때 드러남)
- [x] [Review][Defer] **고아 Storage 오브젝트** — 매물 삭제 시 파일 영구 잔존. `storage_path` 위조가 막혀 **표적 공급 경로로서의 위험은 사라졌고**, 남은 건 용량 누적
- [x] [Review][Defer] **설계 공백 4건**(대표교체 단일UPDATE 실패·`sort_order` tie-break·10장 `errcode` 부재·대표 0장 허용) — 소비처가 9.3~9.5라 그때 결정
- [x] [Review][Defer] **동시 INSERT 경합 10장 초과** — 미측정. 코드상 명백하나 실측 아님

#### Decision 원문 (경위 보존)

- [ ] ~~[Review][Decision] **★ `storage_path` 위조로 타인의 비공개 사진이 anon에게 개방된다 (실측)**~~ — `listing_images_insert_own`(0012:219-226)은 `listing_id` 소유권만 검사하고 `storage_path`는 **무검증 자유 문자열**이다. 읽기 정책(0012:277-288)은 그 값으로 `storage.objects.name`과 조인한다. 판매자 A가 자기 `on_sale` 매물에 `storage_path='{피해자uid}/{피해자매물}/x.jpg'` 행을 넣으면 **anon이 피해자의 sold 매물 오브젝트를 읽는다**(도커 재현: 위조 행 삽입 후 anon 1건 조회 → 행 삭제 후 0건). `storage_path` UNIQUE가 **이미 등록된** 경로는 막지만, 고아 오브젝트(아래 항목)와 업로드 직후 미등록 오브젝트가 표적을 상시 공급한다. 뿌리는 CLAUDE.md B9 — 경로 규칙이 `conventions.md §10` 문서에만 있고 DB에 안 박혔다. **AC1~AC4 어디도 `storage_path`↔`listing_id`/소유자 정합성을 요구하지 않았다 = 스펙 자체의 결함**(dev는 스펙대로 했다). 선택지: (1) `storage_path`에 CHECK로 `{uid}/{listing_id}/` 형태 강제 (2) 읽기 정책에 경로-소유자 일치 조건 추가 (3) 생성 컬럼화 (4) 데모 범위로 수용·이월.
- [ ] [Review][Decision] **`UPDATE`로 `listing_id`를 옮겨 10장 상한 우회 (실측)** — 트리거가 `before insert` 전용(0012:166-168)이고 `listing_images_update_own`(0012:228-241)은 `listing_id` 변경을 막지 않는다. 사진 1장짜리 매물 C의 행을 이미 10장인 B로 `update ... set listing_id=B` → `UPDATE 1` 성공, **B가 11장**. 판매자 한 명이 정상 UI 권한만으로 넘긴다. 최소 수정 = `before insert or update of listing_id`. **AC2가 "BEFORE INSERT 트리거로 강제"라고 수단을 지정했으므로 스펙 결함**이다.
- [ ] [Review][Decision] **버킷이 이미 존재하면 비공개·5MB·MIME 3대 상한이 동시에 조용히 무효 (실측)** — `on conflict (id) do nothing`(0012:184). 누군가 `listing-images`를 `public=true`로 먼저 만들어 뒀다면 `INSERT 0 0`으로 통과하고 **ADR-IMG-01의 비공개 전제 + 5MB + 저장형 XSS를 막는 MIME 3종이 전부 무력화된 채 마이그는 초록**이다. `do nothing`은 "재적용 안전"이 아니라 "에러 없음"만 보장 — 이 레포가 #27에서 스스로 경고한 `"에러 없음"으로 갈음 금지`와 같은 함정. 선택지: `do update set public=excluded.public, file_size_limit=..., allowed_mime_types=...`.
- [ ] [Review][Decision] **관리자가 sold 매물 사진의 바이너리를 못 본다 (실측)** — `listing_images_select_admin`(0012:215-216)으로 **메타행은 1건 보이는데** storage 읽기 정책(0012:277-288)엔 admin 분기가 없어 `storage.objects`는 **0건** → 서명 URL 발급 불가, Epic 6 관리자 매물상세(`/admin/listings/[id]`, sold 포함)에서 깨진 이미지. 0012:276 주석은 "anon이 `is_admin()`에 걸리면 열람 전체가 깨진다"를 이유로 대지만, **`to authenticated` 별도 정책을 하나 더 두면 해소된다** — 같은 파일의 `listing_images`가 정확히 그 분리 패턴을 쓴다. 제약이 아니라 선택이었는데 제약처럼 서술됐다.
- [ ] [Review][Decision] **`storage.objects` 쓰기 정책이 `for all`이라 SELECT까지 연다 (AC4 위반)** — AC4:76은 "insert/update/delete"를 열거했는데 0012:264는 `for all to authenticated`. 정책은 permissive OR이므로 **`listing_images` 행이 없는 고아 오브젝트도 경로 첫 세그먼트가 본인이면 읽힌다** — AC4가 읽기의 유일한 근거로 규정한 조건을 우회하는 두 번째 읽기 경로. FR11/FR58 누수는 없으나(본인 파일 한정), 9.2 서명 URL의 발급 조건이 둘로 갈린다. 헤더 주석(0012:111)의 "쓰기=본인 경로만"과도 어긋남. 수정 = `for insert, update, delete`.
- [ ] [Review][Decision] **고아 Storage 오브젝트 — 매물 삭제 시 파일이 영구 잔존, 정리 주체가 없다** — `on delete cascade`(0012:120)로 메타행은 조용히 사라지지만 `storage.objects`를 지우는 트리거·FK가 마이그 어디에도 없다. 결과: (a) 과금되는 저장공간 무한 누적 (b) **위 `storage_path` 위조의 표적을 상시 공급**(등록 행이 사라져 UNIQUE 방어가 풀린 경로가 쌓인다). #27이 cascade의 침묵을 길게 논하면서 **논한 대상은 시드 재실행 시 행 유실뿐**이고 고아 파일은 어느 항목에도 미등재 — 대장이 하나라면 여기 있어야 한다.
- [ ] [Review][Decision] **AC7 검증에 구멍 — 이 스토리의 핵심이 한 번도 안 태워졌다** — (가) AC7 표 6건 중 `storage.objects` **읽기 정책**(`listing_images_objects_read`)을 태우는 시나리오가 **0건**이다. 그런데 AC4:78-79는 그 정책을 "서명 URL 발급 자체의 전제 · FR11의 스토리지 레이어 강제 · FR58의 성립 조건"이라 규정한다. Debug Log가 `select count(*) from storage.objects where bucket_id='listing-images'` → `0`이라 적은 것이 확증 — **오브젝트가 성공적으로 만들어진 적이 없으니 읽기 정책은 시험될 수 없었다.** 그럼에도 Completion Notes(349행)는 "정책이 실제로 거른다는 증명은 AC7이 한다"로 닫는다. (나) 쓰기 정책의 **허용 분기(대조군)가 미검증** — `split_part(...)=auth.uid()::text`가 틀렸다면 본인 경로 insert도 거부되는데 AC7 ④는 여전히 "거부=기대일치"로 초록이다(**9.3 업로더가 도착 즉시 죽는 시나리오를 못 잡는다**). (다) AC7:120의 `rollback` 요구 미이행(자인) + ④⑤⑥이 각기 다른 에러를 내며 연속 성공했다는 서술은 savepoint 없이는 불가능한데 그 메커니즘이 기록에 없다. (라) **게이트도 이 축을 볼 수 없다** — 프렐류드 storage 스텁에 `grant usage on schema storage`가 없어 게이트에서 anon/authenticated의 `storage.objects` 조회는 `permission denied for schema storage`다(실측). 실제 Supabase는 그 GRANT를 제공하므로 이건 프렐류드 자신의 "정당한 확장" 기준에 해당. **현재 초록불은 storage 정책의 존재조차 증명하지 않는다.**
- [ ] [Review][Decision] **(묶음) 소비처가 9.3~9.5인 설계 공백 4건** — (1) **대표사진 교체가 단일 UPDATE로 실패(실측)**: 부분 유니크(0012:138-139)는 DEFERRABLE 불가라 자연스러운 `update ... set is_cover=(id=:new) where listing_id=:L`이 `duplicate key`로 죽는다 → 클라가 반드시 2문장으로 짜야 하는데 그 제약이 어디에도 없다. (2) **`sort_order` tie-break 부재**: 전부 기본값 `0`이면 `order by sort_order` 결과가 매 쿼리 달라진다 → `unique(listing_id, sort_order)` 또는 `order by sort_order, id` 규약 필요. (3) **10장 초과 에러에 `errcode` 없음**(0012:159): SQLSTATE가 일반 `P0001`이라 클라가 한국어 메시지 문자열 매칭으로만 구별 → 메시지를 다듬는 순간 조용히 깨진다. (4) **대표 0장 허용**: `is_cover default false`라 대표 없는 매물이 정상 상태 — UX D3 카드가 표시할 썸네일이 없다. 의도인지 불명.
- [ ] [Review][Decision] **동시 INSERT 경합으로 10장 초과 가능 (미측정)** — 트리거의 `select count(*)`(0012:154-156)에 `for update`·advisory lock·상한 제약이 전무. Read Committed에선 미커밋 행이 안 보이므로 두 트랜잭션이 각각 9장을 보고 둘 다 통과 → 11장. **단일 커넥션 도구 한계로 재현하지 못했다 — 코드상 명백하나 실측 아님.** 실사용(사진 병렬 업로드)에서 현실적으로 닿는 경로.

#### Patch (문서·기록만 — DB 무접촉, 승인 불필요)

- [ ] [Review][Patch] tech-debt #18의 **라이브 모순** 정리 — 124행 "(a′) 승인 대기 없이 진행" vs 130행 "이 항목을 근거로 GRANT를 자율 추가하지 말 것"이 공존 [docs/tech-debt.md:124,130]
- [ ] [Review][Patch] #18 "남은 범위"에 **storage 축 추가** — 0012는 `storage.objects` 정책을 만들며 GRANT는 한 줄도 안 준다(프렐류드의 `alter default privileges`는 `in schema public`이라 storage에 안 미침) = 플랫폼 GRANT에 대한 **새 암묵 의존**인데 갱신된 남은 범위엔 없다 [docs/tech-debt.md:137]
- [ ] [Review][Patch] #18의 "anon(FR58 **컬럼 차단**)" 표현 정정 — 테이블 컬럼 6개 전부를 재부여하므로 **차단되는 컬럼은 0개**다. 실효는 "이후 추가되는 컬럼이 자동 노출되지 않는다"뿐(0011 주석이 그 효과를 정확히 서술함). 지금 표현은 다음 사람이 차단이 걸렸다고 믿고 민감 컬럼을 추가하게 만든다 [docs/tech-debt.md:41]
- [ ] [Review][Patch] `0012` 헤더의 self-contained 의존 열거에 **0006(`ai_readonly`) 추가** — 헤더(0012:102-103)는 "0002·0001뿐"이라 적었으나 0012:253,304가 `ai_readonly`에 의존한다. AC1:53이 명시적으로 0006을 짚었는데 빠졌다. 불변식 위반은 아니나(0006<0012) 선언이 사실보다 좁다 [supabase/migrations/0012_listing_images.sql:102]
- [ ] [Review][Patch] "`on conflict do nothing`: **재적용 안전**" 주석 정정 — 0012는 `create table`(0012:118)에 `if not exists`가 없어 두 번 돌리면 **첫 문장에서 죽는다**. 따라서 아래의 `drop policy if exists`·`on conflict do nothing`은 도달 불가능한 방어다. 파일 내부에서 재적용 정책이 엇갈린다(0011은 일관됨) [supabase/migrations/0012_listing_images.sql:175]
- [ ] [Review][Patch] conventions §10 "3개 상한은 **전부 DB에 박는다**" 과장 정정 — 10장은 UPDATE로 우회 가능하고, 5MB·MIME를 강제하는 건 Postgres가 아니라 Storage **API 서버**다(스텁은 값을 저장만 하는 평범한 테이블이라 게이트가 이 둘을 전혀 증명하지 못한다) [docs/conventions.md §10]
- [ ] [Review][Patch] AC5 "초록이 증명 못 하는 것"에 **false-green 축 추가** — 기록엔 false-red만 적혔다(`owner` 등 미포함 컬럼). 그러나 실측한 `storage.buckets.type (USER-DEFINED, NOT NULL)`을 스텁에서 뺐고, 스텁의 `objects.id default gen_random_uuid()`는 실측 항목에 없는 **추측**인데 AC7 ④가 실제로 그 기본값에 의존한다. 기술부채 #24가 이미 이 실패 모드를 false green이라 명명해 뒀다 — 더 위험한 쪽이 안 적혔다 [scripts/migration-check-prelude.sql:74-89]
- [ ] [Review][Patch] **`SIGNED_URL_TTL=3600s` 잔존 창 기록** — 서명 URL은 발급 시점에만 RLS를 검사하고 TTL 동안 재검사하지 않는다 → `on_sale`→`sold` 전환 후에도 **직전 발급 URL이 최대 1시간 생존**한다. §6의 "모든 경로" 주장이 이 축에선 성립하지 않는다. §6 추가 문구의 "발급 가능"이라는 단어는 정확하나, **정확함이 한계를 기록한 것은 아니다** — 어디에도 없다(B8: 미루는 판단은 틀린 게 아니고 안 적는 게 틀린 거다) [docs/conventions.md §6·§10]
- [ ] [Review][Patch] CI 미트리거 원인 "**웹훅 지연/유실**"은 추정임을 명시 — `56c47af`는 `supabase/migrations/**`와 `scripts/**`를 **둘 다** 건드려 `paths` 필터에 정확히 걸린다(리뷰에서 실측 확인). 즉 "왜 안 돌았는가"는 **미해결**이고 웹훅 유실은 관측과 양립할 뿐 입증된 원인이 아니다. 대장 미등록 — 재발 시 같은 자리에서 또 태운다 [스토리 Debug Log 5:341]
- [ ] [Review][Patch] §6 괄호 범위 모호 정정 — storage 문구를 넣은 뒤 원래 있던 "(구현은 Epic 2~4, anon 경로는 Epic 8.5)"가 그대로 남아 Epic 9 항목까지 포괄하는 것처럼 읽힌다 [docs/conventions.md §6]
- [ ] [Review][Patch] `ai_readonly using(true)`의 FR11 강제를 **대장에 등록** — 0012:253-254는 sold 사진 메타를 전부 연다(CR2가 확정한 의도). 유일한 방어가 "api가 on_sale id로 좁힌다 + sql_guard가 JOIN 안 한다"인데 **둘 다 미래 스토리(9.6)에 대한 약속**이고, 지금 sql_guard가 `listing_images`를 JOIN하지 못하게 막는 **실행되는 검사는 없다**(B9: 주석은 계약이 아니다). 9.6 AC로 심을 것 [docs/tech-debt.md]
- [ ] [Review][Patch] AC6이 요구한 **GRANT 덤프 원본 재첨부** — AC6:101과 §9.3(a′)-1은 "그 출력을 Debug Log에 **붙인다**"인데 Debug Log 1(309행)은 dev의 **산문 요약**이다. (a′)의 존재 이유가 정확히 이것 — §9.3:174 "진짜 안전장치는 '델타 0'을 논증이 아니라 실측으로 증명하는 것". 요약은 논증이고, `grantee×table×privilege_type` 원본 행이 없으면 제3자가 델타 0을 재판정할 수 없다. (읽기 전용이라 DB 무접촉) [스토리 Debug Log 1:309]

#### Defer (기존 문제 — 이 변경이 만든 게 아님)

- [x] [Review][Defer] 프렐류드의 `alter default privileges ... grant all to anon, authenticated`가 **anon에게 INSERT/UPDATE/DELETE/TRUNCATE GRANT까지** 준다 — 0012는 `revoke **select**`만 하므로 anon은 `listing_images`에 쓰기 GRANT를 보유한다. 지금은 anon용 쓰기 RLS 정책이 없어 기본 deny로 막히지만 **방어선 하나에만 의존**하는 상태다. #18이 이미 다루는 기존 축이고 이 스토리가 만든 게 아니다 — `docs/tech-debt.md` #18에 기록 [scripts/migration-check-prelude.sql:66-67]

#### Dismissed (5건 — 거짓 양성)

| 주장 | 왜 기각인가 |
|---|---|
| 다중행 INSERT가 10장 트리거를 뚫는다 (blind) | **도커 실측으로 반박** — `insert...select` 11행 일괄 삽입이 정상 차단됨. BEFORE ROW 트리거는 같은 문장의 형제 행을 본다 |
| anon에 `listings.seller_id` GRANT가 없어 이미지 열람이 전부 깨진다 (blind) | **`0011:44` 실측** — `seller_id`·`status` 모두 anon에 GRANT돼 있다. 도커에서 anon 조회도 성공 |
| `storage.objects` CREATE POLICY가 소유권으로 원격에서 실패한다 (blind) | 원격 `apply_migration`이 **실제로 성공**해 경험적으로 반증됨 |
| `drop policy if exists`가 남의 정책을 파괴한다 (blind) | 정책명이 `listing_images_objects_*`로 이 스토리 고유 — 개연성 없음 |
| #27이 "판단 완료"를 가장한 연기다 (blind) | **AC8:140이 "(c) 근거 있는 이월"을 명시적 선택지로 허용**했고 dev는 근거·재방문 시점(Epic 10.5)까지 적었다 |

---

## Dev Notes

### 왜 이 스토리가 먼저인가

Epic 9의 나머지(9.2 서명 URL 헬퍼 → 9.3 업로더 → 9.4 카드 → 9.5 상세 → 9.6 AI 카드 → 9.7 시드)가 전부 여기 위에 선다. 특히 **9.2의 서명 URL은 AC4의 읽기 정책이 없으면 발급 자체가 안 된다** — "사진이 안 보인다"로 나타나서 원인을 찾기 어렵다. 배포 순서도 같은 이유로 **db → api → web**이다(AC-DEPLOY-1).

### 재사용할 것 (바퀴 재발명 금지 — 증분 지배 원칙)

| 필요한 것 | 이미 있는 것 | 위치 |
|---|---|---|
| 마이그 헤더·섹션 주석 스타일 | 0011이 본보기(왜 필요한가 산문 → DDL) | `supabase/migrations/0011_listings_anon_select.sql` |
| 역할별 SELECT 정책 분리 | listings 4정책 + anon 1정책 | `0002_listings.sql:88-118` · `0011` |
| 무결성 트리거 + `revoke execute` | 채팅 `seller_id` 위조 차단 트리거 | `0003c_chat_room_integrity.sql` · `0002_listings.sql:123` |
| `ai_readonly` 명시 GRANT | guide_documents 선례 | `0004_guide_documents.sql:58` |
| `revoke` + 컬럼 스코프 `grant` | anon×listings | `0011_listings_anon_select.sql:28-59` |
| 멱등 DO 블록(`if not exists`) | ai_readonly 롤 생성 가드 | `0006_readonly_role.sql:24-29` |

**이 레포엔 storage를 쓰는 코드가 아직 0줄이다** — 마이그레이션에도(grep 0건), web에도(`storage.from`/`createSignedUrl`/`upload(` 전부 0건). 즉 **참고할 사내 선례가 없는 유일한 표면**이고, 그래서 프렐류드 함정이 생겼다.

### 현재 상태 — 손대는 파일이 지금 무엇인지

**`supabase/migrations/` (12개)**: `0001_profiles` · `0002_listings` · `0003_chat` · `0003c_chat_room_integrity` · `0004_guide_documents` · `0005_admin_policies` · `0006_readonly_role` · `0007_listings_seller_name` · `0008_chat_room_names` · `0009_profiles_name` · `0010_chat_message_length` · `0011_listings_anon_select`.
→ **`0012`는 비어 있다.** 게이트가 **밀집(0001~max 빈틈없음)** 을 강제하므로 다음 번호는 `0012`뿐이다.

**`listings`(0002)** — 이 스토리가 참조하는 부분:
```sql
id         uuid primary key default gen_random_uuid(),
seller_id  uuid not null references public.profiles(id) on delete cascade,
status     text not null default 'on_sale' check (status in ('on_sale','sold')),
```

**`scripts/migration-check-prelude.sql`** — 현재 스텁: `auth` 스키마 · `auth.users`(3컬럼) · `auth.uid()` · `anon`/`authenticated`/`service_role` 롤 · `alter default privileges ... grant all`. **`storage`는 한 줄도 없다.**

**`scripts/check_migrations.py`** — 정적 5종(파일명 정규식 `^\d{4}[a-z]?_[a-z0-9_]+\.sql$` · 0000 금지 · 밀집 · 중복 없음 · 접미사엔 정본 선행) + 동적(도커 `pgvector/pgvector:pg17`에 프렐류드 → 파일 정렬순 `psql --single-transaction -v ON_ERROR_STOP=1`) + 프로브 3건(53~69행). **프로브를 새로 추가하는 건 이 스토리 범위 밖이다.**

### 게이트가 조용히 거는 제약 (런북 §8-⑨)

모든 마이그가 `--single-transaction`으로 적용된다 → **트랜잭션 밖에서만 되는 문**(`create index concurrently` 등)은 원격 `apply_migration`에선 통과해도 **게이트에선 red**다. 0012의 인덱스는 **`concurrently` 없이** 쓴다(신규 빈 테이블이라 락 문제도 없다).

### 아키텍처가 이미 확정한 것 (재논의 금지)

- **ADR-IMG-01**: 비공개 버킷 + 서명 URL. 업로드는 anon/authenticated 키 + Storage RLS. **service_role 절대 금지.**
- **CR2**(정정 섹션 = 최종 계약): `listing_images`에 **`ai_readonly using(true)` SELECT 정책**을 둔다. api는 sql_guard 결과의 **on_sale id로 대표 1장 `storage_path`만 별도 고정쿼리**로 읽는다 — **sql_guard는 listings 단일 테이블을 유지하고 JOIN하지 않는다**(9.6의 일).
- **api는 서명 URL을 절대 발급하지 않는다** — `storage_path`만 반환. 서명 금지 대상은 **api뿐**이고 web(서버측)·app(`supabase_flutter` 클라측)은 서명한다.
- **`SIGNED_URL_TTL = 3600s`** · **10장 / 5MB** (사용자 확정 2026-07-13).
- **5:3 크롭은 클라 렌더**(I14), **처리중/실패는 업로더 로컬 상태**(I8) — 둘 다 DB/wire 계약이 아니다. 여기서 컬럼을 만들지 마라.

### `ai_readonly using(true)`가 FR11을 뚫지 않는 이유

`listing_images`의 ai_readonly 정책은 sold 매물의 이미지 행도 본다. **의도된 것이다** — FR11 강제는 **api가 on_sale id로 스코프를 좁히는 데서** 일어난다(CR2). ai_readonly는 로그인 불가(`nologin`) 롤이고 api의 SELECT 전용 경로에서만 쓰인다. 이 정책을 `status` 조건으로 좁히려 들지 마라 — 9.6이 기대하는 계약이 깨진다.

### 함정 모음

- **`is_admin()`을 anon 경로에 태우지 마라** — execute가 `authenticated`에만 있다(`0001_profiles.sql:91`). 정책을 롤별로 나누는 이유가 이것이다.
- **`storage.objects` 정책 안에서 컬럼 참조는 `storage.objects.name`으로 한정** — EXISTS 서브쿼리 안에서 맨 `name`은 헷갈린다.
- **`split_part(name,'/',1)`은 `text`, `auth.uid()`는 `uuid`** → `auth.uid()::text`로 비교한다. 반대로 경로 세그먼트를 uuid로 캐스팅하면 잘못된 경로에서 **에러가 나며 정책이 터진다**.
- **버킷은 `on conflict (id) do nothing`** — 재적용 안전(마이그는 레시피다).
- 파일명은 `0012_listing_images.sql`, `apply_migration`의 name도 **`0012_listing_images`**. 번호를 빼면 원장과 어긋난다(실제 사고 사례: 0011의 번호 없는 재적용, 런북 §8-③).

### 테스트 표준 (규칙 12)

이 스토리의 층은 **DB**다. web/api 단위테스트도 Playwright E2E도 여기 해당 없다. 검증 = **게이트(도커 fresh DB)** + **원격 실측(AC7)** 두 층이고, 둘이 보는 게 다르다:

| 층 | 증명하는 것 | 증명 못 하는 것 |
|---|---|---|
| 게이트 | 마이그 + 선언된 계약면 = **도는 DB** | 정책이 **듣는지**(프로브는 카탈로그만 본다) · 진짜 Supabase storage |
| AC7 원격 실측 | 정책이 **실제로 거른다** | fresh DB 재현성 |

**둘 다 해야 한다.** 하나로 다른 하나를 갈음하지 마라.

### 범위 밖 (하지 마라)

서명 URL 헬퍼(9.2) · 업로더 UI(9.3) · 카드/갤러리(9.4·9.5) · api `listing_cards.py`·`sql_guard.py` 수정(9.6 — **listings에 컬럼을 안 더하므로 `SELECT_COLUMNS`·`ALLOWED_COLUMNS`는 이번에 안 건드린다**) · `seed.sql` 수정(9.7) · `docs/db-schema-guide.md`(증분 후 예약) · ListingCard 계약(`image_url`/`image_count` 자리는 8.3이 이미 확보) · #18의 나머지 테이블 · 게이트 프로브 추가.

### Project Structure Notes

```
supabase/migrations/
  ✚ 0012_listing_images.sql ……… 테이블 + 트리거 + 버킷 + 테이블 RLS + storage.objects RLS + GRANT (전부 한 파일 — 규칙 10 동거)
scripts/
  ✎ migration-check-prelude.sql … storage 스키마 최소 스텁(실측 근거 주석 필수)
docs/
  ✎ conventions.md ……………………… §10 이미지 스토리지 계약 신설 + §6 FR11 강제 지점 추가
  ✎ tech-debt.md ………………………… #27 결정 반영 · #18 범위 갱신(닫지 않음)
```

**변이 하나**: 아키텍처 문서(271행)와 원본 epics는 이미지 마이그를 `0011`로 적었으나, **8.5가 FR58 anon SELECT를 0011로 삽입해 이후가 +1 시프트**됐다. **정본은 `0012`** — epics 원장 표(258~274행)와 sprint-status가 그 기준이다.

### References

- [Source: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md#Story 9.1` (446~472행) — AC 원문 · 원장 표(258~274행)]
- [Source: `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md#Data Architecture` (172행) — listing_images 스키마 · `#ADR-IMG-01`(173행) · **`#정정 — CRITICAL` CR2**(360행) · `#확정된 값`(394~395행) · `#Implementation Handoff`(421행)]
- [Source: `docs/conventions.md` §5(service_role 금지) · §6(FR11 강제 지점) · **§9.3 판정규칙 (a′)**(161~178행) · §9.2 파일명 규약 · §9.4 게이트 DoD]
- [Source: `docs/deployment-runbook.md` §7(적용 절차 — `apply_migration` name 규칙) · **§8 사각지대 9개**(특히 ③ 프렐류드 의존 · ④ 도커 없으면 실패 · ⑤ 게이트는 배포를 안 막는다 · ⑥ 있는지 vs 듣는지 · ⑨ single-transaction 제약)]
- [Source: `docs/tech-debt.md` **#18 테이블 GRANT**(117~132행, 판정 (a′)) · **#27 시드 멱등 delete**(188~196행)]
- [Source: `_bmad-output/project-context.md` 규칙 6(RLS·service_role 금지) · 규칙 7(FR11 새 경로 등록) · 규칙 10(마이그·RLS 동거) · 규칙 12(테스트 층)]
- [Source: `_bmad-output/implementation-artifacts/epic-8-retro-2026-07-15.md` §7 액션(A1·A3·A5) · §8 Epic 9 준비 상태 — ⚠️ 표의 "GRANT 판정 (b) 승인 필요"는 **(a′)로 대체됨**(2026-07-16)]
- [Source: `_bmad-output/implementation-artifacts/8-6-*.md` — 게이트·프렐류드·런북을 만든 스토리. `0004`를 (a)로 자율 수정한 선례]
- [Source: `_bmad-output/implementation-artifacts/8-5-*.md` — 0011을 쓴 직전 사례. "컬럼 스코프 GRANT는 원 계획에 없던 필수 보정"(RLS는 행만 통제)]
- [Source: 코드 — `supabase/migrations/0002_listings.sql:25-58, 88-118, 123` · `0006_readonly_role.sql:24-43` · `0011_listings_anon_select.sql` 전문 · `0004_guide_documents.sql:58` · `supabase/seed.sql:196` · `scripts/check_migrations.py:38, 53-69, 205-273` · `scripts/migration-check-prelude.sql` 전문]

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

**1. Task 1 — 원격 테이블 GRANT 덤프** (`information_schema.role_table_grants`, `table_schema='public'`, grantee in anon/authenticated/ai_readonly):
`listing_images`는 원격에 아직 없어 결과에 등장하지 않음(비교 대상 자체가 없음 = 신규 테이블). 기존 5개 테이블만 존재: `chat_messages`(anon 7종·authenticated 7종·ai_readonly SELECT)·`chat_rooms`(동일 패턴)·`guide_documents`(동일 패턴)·`listings`(anon 6종[SELECT 제외 — 0011이 회수함]·authenticated 7종·ai_readonly SELECT)·`profiles`(anon 7종·authenticated 7종·ai_readonly SELECT). **이 마이그가 건드리지 않는 축의 델타 = 0**(AC6 (a′) 조건 충족).

**2. Task 1 — 원격 storage 스키마 실측** (`information_schema.columns`, `table_schema='storage'`, `table_name in ('buckets','objects')`):
- `buckets`: id(text,NOT NULL) · name(text,NOT NULL) · owner(uuid) · created_at/updated_at(timestamptz) · public(boolean) · avif_autodetection(boolean) · file_size_limit(bigint) · allowed_mime_types(ARRAY) · owner_id(text) · type(USER-DEFINED, NOT NULL)
- `objects`: id(uuid,NOT NULL) · bucket_id(text) · name(text) · owner(uuid) · created_at/updated_at/last_accessed_at(timestamptz) · metadata(jsonb) · path_tokens(ARRAY) · version(text) · owner_id(text) · user_metadata(jsonb)
- `select relrowsecurity from pg_class where oid='storage.objects'::regclass;` → **`true`**(플랫폼이 이미 RLS를 켜둠 → 0012는 스스로 enable하지 않음, AC4 근거).
- `mcp__supabase__list_migrations` → `0012` 없음 확인. 레포에 없는 5건(0002b/c/d·0003b·0003c_revoke_trigger_execute·번호없는 `listings_anon_select`)이 이력에 존재 — 런북 §8-⑧이 이미 설명한 정상 이력(신규 발견 아님).
- 이 실측을 근거로 `scripts/migration-check-prelude.sql`에 storage 최소 스텁(buckets 5컬럼·objects 3컬럼 — 0012가 실제로 참조하는 것만) + `alter table storage.objects enable row level security` 추가.

**3. Task 5 — 게이트 red→green 왕복**:
- **최초 실행(변경 전 상태, 스텁 有)**: `python scripts/check_migrations.py` → 정적 검사 통과, 동적 검사에서 0001~0012 전량 적용 성공 + 프로브 3건(①②③) 전부 기대값 일치 → **"=== 마이그레이션 게이트 통과 ==="**.
- **일부러 깨기**: `migration-check-prelude.sql`의 storage 스텁 블록(스키마+buckets+objects+RLS enable) 전체를 임시 주석 처리 후 재실행 → `[FAIL] 0012_listing_images.sql : ... ERROR: relation "storage.buckets" does not exist` (LINE: `insert into storage.buckets ...`), 종료코드 1, **"동적 검사 실패"** → **red 재현 성공**(0012가 프렐류드의 storage 스텁에 실제로 의존함을 증명).
- **되돌리기**: 주석 해제(원상복구) 후 재실행 → 0001~0012 전량 적용 성공 + 프로브 3건 전부 통과 → **"=== 마이그레이션 게이트 통과 ==="** (green 재확인).
- **게이트가 안 보는 것(이번에 실측해서 알게 된 것)**: 기존 프로브 3건은 `listings`·`guide_documents`만 대상이라 `listing_images`·`storage.objects` 정책이 **"듣는지"는 전혀 검증하지 않는다**(카탈로그 존재만 보는 기존 한계가 신규 테이블에도 그대로 적용됨). 게이트는 우리가 만든 **간소화된 storage 스텁**(실컬럼의 일부만) 위에서 돌아가므로, `owner`·`metadata` 등 스텁에 없는 실제 컬럼을 참조하는 미래 마이그는 게이트에서만 거짓 red가 날 수 있다(런북 §8-③·기술부채 #24와 동일 성격의 사각지대가 storage에도 생김 — 스텁을 늘릴 때마다 반복될 위험). 정책이 실제로 거르는지는 AC7(원격 실측)만이 증명한다.

**4. Task 7 — 원격 적용 + AC7 6개 시나리오 실측**:
- `apply_migration(name="0012_listing_images")` → `{"success":true}`.
- 실제 데이터 사용: on_sale 매물 `e80c0108-...`(seller `12dfba00-...`), sold 매물 `661b38a9-...`(동일 seller), 무관 사용자 `371eb469-...`. 트랜잭션(`begin...select`, 명시 `rollback` 없이 세션 종료 — 아래 확인) 안에서 `set local role`/`set local request.jwt.claim.sub`로 롤 전환:

| # | 시나리오 | 실제 출력 |
|---|---|---|
| 1 | on_sale × anon SELECT | **`1행`** (기대: 보임 — 일치) |
| 2 | sold × anon SELECT | **`0행`** (기대: 0행 — 일치) |
| 3 | sold × 소유자 authenticated SELECT | **`1행`** (기대: 보임 — 일치) |
| 4 | 남의 경로(`12dfba00.../...`)로 무관 사용자(`371eb469...`) insert (storage.objects) | **`RLS 거부: new row violates row-level security policy for table "objects"`** (기대: 거부 — 일치) |
| 5 | 10장 채운 매물에 11번째 insert | **`거부됨: 매물당 사진은 최대 10장까지 등록할 수 있습니다 (listing_id=e80c0108-...)`** (기대: 거부 — 일치, 한국어 메시지 확인) |
| 6 | 대표 이미 있는 매물에 `is_cover=true` 두 번째 insert | **`거부됨: duplicate key value violates unique constraint "listing_images_one_cover_per_listing"`** (기대: 거부 — 일치) |

- **찌꺼기 확인(rollback 대체 검증)**: 위 트랜잭션이 `rollback`으로 명시 종료되지 않아, 별도 쿼리로 원격 잔존 여부를 직접 실측함 — `select count(*) from listing_images where listing_id in (...)` → **`0`**, `select count(*) from storage.objects where bucket_id='listing-images'` → **`0`**. 세션 종료 시 미완결 트랜잭션이 자동 롤백됨을 확인(추측이 아니라 실측).
- `get_advisors(type=security)` 사후 점검: 경고 3건 전부 이 스토리 이전부터 있던 기존 이슈(`vector` 확장 public 스키마 위치·`is_admin()` SECURITY DEFINER 노출·유출 비밀번호 보호 미설정) — `listing_images`/storage RLS 관련 신규 경고 없음.

**5. Task 8 — GitHub Actions Migration Gate run id + conclusion**:
- 1차 push(`56c47af`)가 웹훅 지연/유실로 워크플로를 전혀 트리거하지 않음 — GitHub Actions API(`actions/runs`)에 해당 커밋의 run이 6분 넘게 생성되지 않음을 실측 확인, GitHub Status Page는 "All Systems Operational"(장애 아님). 사용자가 GitHub Actions 탭에서 직접 확인해 동일 현상 재확인.
- 경로 필터에 걸리는 최소 변경(프렐류드 주석 1줄 추가) + 재커밋(`80978b8`) + 재푸시로 진단 → 이번엔 정상 트리거됨.
- **run id `29443011386`**, workflow=`Migration Gate`, branch=`develop`, head_sha=`80978b8ee48d4356d7acca0bb941cca7563e111a`, **conclusion=`success`**, job `check` 17s. URL: https://github.com/wonho1111/bmad-encar-demo/actions/runs/29443011386

**5-1. [코드리뷰 보정] AC6 GRANT 덤프 — 원본 행 (2026-07-16)**

Debug Log 1이 AC6:101·§9.3(a′)-1이 요구한 *"그 출력을 붙인다"* 대신 **산문 요약**을 실었다. §9.3:174가 *"진짜 안전장치는 델타 0을 논증이 아니라 실측으로 증명하는 것"*이라 한 바로 그 대가라, 코드리뷰에서 원본을 다시 떠 붙인다. 쿼리는 AC6:102-106 원문 그대로.

```
 grantee     | table_name     | privilege_type
-------------+----------------+----------------
 ai_readonly | chat_messages  | SELECT
 anon        | chat_messages  | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 authenticated| chat_messages | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 ai_readonly | chat_rooms     | SELECT
 anon        | chat_rooms     | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 authenticated| chat_rooms    | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 ai_readonly | guide_documents| SELECT
 anon        | guide_documents| DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 authenticated| guide_documents| DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 ai_readonly | listing_images | SELECT
 anon        | listing_images | DELETE, INSERT, REFERENCES, TRIGGER, TRUNCATE, UPDATE      ← SELECT 없음(0012가 회수)
 authenticated| listing_images| DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 ai_readonly | listings       | SELECT
 anon        | listings       | DELETE, INSERT, REFERENCES, TRIGGER, TRUNCATE, UPDATE      ← SELECT 없음(0011이 회수)
 authenticated| listings      | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 ai_readonly | profiles       | SELECT
 anon        | profiles       | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
 authenticated| profiles      | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
```
(가독성을 위해 privilege_type만 행 병합했다. 원본은 grantee×table×privilege 1행씩.)

**이 덤프가 실제로 말해주는 것 — 요약본이 못 하던 일:**
- **델타 0 재판정 가능**: 기존 5개 테이블의 GRANT를 이 마이그가 안 건드렸음을 제3자가 직접 확인할 수 있다(AC6 (a′) 조건 충족).
- **컬럼 스코프 GRANT는 이 뷰에 안 나온다** — `anon`의 `listing_images` SELECT가 "없음"으로 보이는 건 `revoke` 때문이고, 컬럼 단위 재부여는 `information_schema.column_privileges`에 있다. **즉 이 덤프만으로 "anon이 못 읽는다"고 읽으면 틀린다.**
- **★ 요약본이 가렸던 사실**: `anon`이 모든 테이블에 **DELETE·INSERT·UPDATE·TRUNCATE**를 갖고 있다(프렐류드·플랫폼의 `alter default privileges ... grant all`). `0012`가 회수한 건 **SELECT 하나뿐**이다. 지금 anon 쓰기를 막는 건 "anon용 쓰기 RLS 정책이 없어서 기본 deny" **단 하나**다 — 방어선 하나에 의존. `#18`에 이월 등재함. **산문 요약("anon 7종")은 이걸 숫자 뒤에 숨겼다.**

**6. 코드리뷰 재실측 (2026-07-16, 새 세션·opus) — AC7이 안 태운 축 + `0013` red→green**

전부 **원격 Supabase**에서 `begin ... rollback` **한 호출**로 실행(도커 아님 — AC7의 존재 이유가 "게이트 스텁 말고 진짜 storage에서 듣는가"다). 실행 모델 확정: `execute_sql` 한 호출 안에서 `set local role` + DO 블록 예외처리로 롤 전환·연속 에러 관찰이 가능하다(지난 기록이 판별 불가였던 지점).

- **사전 확인**: `auth.uid()` 원격 정의 = `coalesce(nullif(current_setting('request.jwt.claim.sub',true),''), (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub'))::uuid` → 빈 클레임에서 안전하게 NULL. anon 시뮬레이션이 정확함을 확인하고 시작.
- **데이터**: 피해자 seller `12dfba00-…`(sold 매물 `661b38a9-…`) · 공격자 seller `0f937a74-…`(on_sale 매물 `ac5d633e-…`). **서로 다른 판매자 둘**이 필요해 지난 실측과 데이터가 다르다.

**(가) `0013` 적용 _전_ — 구멍 재현 (통제된 대조 실험)**

| # | 시나리오 | 실제 출력 |
|---|---|---|
| W1 | 피해자가 **본인 경로**로 `storage.objects` insert (**쓰기 허용분기 대조군 — 지난 AC7에 없던 것**) | `통과 — INSERT 1` |
| R0 | 위조 **전** anon 조회(고아 오브젝트) | `0행` |
| F1 | Mallory가 자기 on_sale 매물에 **피해자 경로**를 적은 행 insert | `★ 통과 — INSERT 1 (아무것도 안 막음)` |
| R1 | 위조 **후** anon 조회 | `★ 1행` |

→ `R0=0행 → R1=1행`이고 그 사이 투입은 **위조 행 하나뿐** = 위조 행이 단독 원인. **피해자의 sold 매물 사진이 비로그인에게 열렸다.** 찌꺼기 확인: `listing_images=0 / storage.objects=0`.

**(나) 게이트 red→green 왕복 (`0013`)**
- green: 프렐류드 + `0001~0013` **15개 전량 적용 성공** + 프로브 3건 통과 → `=== 마이그레이션 게이트 통과 ===`
- **일부러 깨기**: `0013` 끝에 `alter table public.listing_images add constraint tmp_break check (nonexistent_column is not null);` 추가 → `ERROR: column "nonexistent_column" does not exist` → **`동적 검사 실패`** = red 재현(**게이트가 `0013`을 실제로 보고 있음**을 증명 — 초록이 그냥 지나친 게 아니다)
- 되돌려 green 재확인.

**(다) `0013` 적용 _후_ — 같은 스크립트, 다른 결과** (`apply_migration(name="0013_listing_images_path_integrity")` → `{"success":true}`)

| # | 시나리오 | 실제 출력 |
|---|---|---|
| W1 | 본인 경로 `storage.objects` insert (`for all`→`for insert` 좁힌 뒤) | `통과 — INSERT 1` |
| F1 | Mallory 위조행 insert — **적용 전엔 통과했던 바로 그 문장** | `거부됨: 사진 경로가 계약과 다릅니다 — 기대 "0f937a74-…/ac5d633e-…/{파일명}", 실제 "12dfba00-…/661b38a9-…/secret.jpg" (docs/conventions.md §10)` |
| R1 | 위조 후 anon 조회 | `0행` (전: 1행) |
| G1 | **정상** 경로 등록 (허용 대조군 — 죽으면 9.3이 죽는다) | `통과 — INSERT 1` |
| U1 | `listing_id`**만** UPDATE 이동 | `거부됨: … 기대 "0f937a74-…/c4421102-…/{파일명}", 실제 "0f937a74-…/ac5d633e-…/car.jpg"` |

**(라) ⚠️ 과장 금지 — D2는 좁혀졌을 뿐 안 닫혔다 (실측)**
U1이 막히길래 "10장 UPDATE 우회가 부수적으로 해결됐다"고 적을 뻔했으나 **재봤다**: B를 10장으로 채운 뒤 `update ... set listing_id=B, storage_path='{seller}/B/a1.jpg'`(경로를 **함께** 고침) → `통과 — B가 11장이 됨 (상한 우회 여전히 가능)`. **트리거를 만족시키면서 우회된다.** D2는 열린 채 이월.

- **사후 상태 확인**: `listing_images=0행` · `storage.objects(listing-images)=0행` · `listing_images` 트리거 **2개**(max_10 + storage_path) · storage 정책 = `owner_delete, owner_insert, owner_update, read`(`owner_all` 소멸 확인).
- **`0013` CI 초록 실측**: run **`29448176218`**, workflow=`Migration Gate`, branch=`develop`, head_sha=`c77eb729d0775419c2b9fc955e91ede0b64eb69a`, **conclusion=`success`**. 이번 push는 **정상 트리거**됐다(1차 push `56c47af`가 안 돌던 현상과 대조) — 다만 그때의 원인은 여전히 **미상**이고 "웹훅 유실"은 입증된 게 아니다(`tech-debt.md` #50-3).
- **⚠️ 이 초록이 여전히 증명하지 않는 것**: 게이트 프렐류드엔 `grant usage on schema storage`가 **없어** 게이트에서 anon/authenticated의 `storage.objects` 조회는 `permission denied for schema storage`다(리뷰 실측). 즉 **게이트는 `0013`의 storage 정책이 "듣는지"를 한 줄도 실행하지 못한다** — 위 (다)의 원격 실측만이 그걸 증명한다. 게이트가 증명한 건 "`0013`이 fresh DB에 적용된다"뿐이다(단, red 왕복으로 **게이트가 `0013`을 보고는 있음**은 확인됨).

### Completion Notes List

- **기술부채 #27 (시드 멱등 delete)**: **(c) 근거 있는 이월**을 택함(닫지 않음). 이유: 이 스토리는 `seed.sql`을 고치지 않고 `listing_images`에도 행을 넣지 않아(사진 시딩은 9.7) 오늘 시점엔 지워질 이미지 행이 0건 — 그래서 지금은 진짜 무해하다(실측: `seed.sql:196`이 여전히 delete+새 uuid 재삽입임을 확인). 9.7이 사진을 시드에 추가할 때 **같은 실행 안에서** listings 재삽입 직후 새 `listing_id`로 이미지를 다시 넣으면 (b)를 자연히 만족한다 — 9.7의 AC(2회 연속 실행 후 이미지 행 수 카운트)가 이를 실측 검증한다. 진짜 위험은 seed.sql이 모르는 데이터(실사용자가 시드 매물에 올린 사진, **Epic 10.5 `wishlists`의 실제 찜 기록**)이며, 이건 (a)/(b) 어느 쪽도 못 구제한다 — **Epic 10.5 착수 시 (a) 고정 id를 재고할 것**을 tech-debt.md에 명시했다(찜은 사용자 행동의 산물이라 사진보다 유실 체감이 큼).
- **기술부채 #18 (테이블 GRANT)**: 이번에 명시한 범위 = `listing_images`에 대해서만 `anon`(0011과 같은 모양 — revoke 후 컬럼 스코프 재부여) + `ai_readonly`(0004 선례 — 명시 grant). **명시하지 않고 남긴 범위** = `listing_images`의 `authenticated` GRANT(플랫폼 기본에 위임, AC6 범위 밖) + 기존 5개 테이블(`profiles`·`chat_rooms`·`chat_messages`·`guide_documents`·`listings`)의 `authenticated` 명시화 + 프렐류드의 `alter default privileges` 제거. **닫지 않음** — 나머지 범위는 그대로 열려 있음을 tech-debt.md에 기록.
- **게이트 초록이 증명하지 않는 것(이번에 실측)**: 기존 프로브 3건은 `listings`·`guide_documents`만 대상이라 `listing_images`·`storage.objects`의 신규 정책이 "듣는지"는 게이트가 전혀 안 본다(디자인상 원래 한계가 신규 테이블에 그대로 적용됨을 재확인). 게이트는 storage의 **간소화된 스텁**(실 컬럼 중 0012가 쓰는 것만) 위에서 돈다 — `owner` 등 스텁에 없는 컬럼을 미래 마이그가 참조하면 원격은 멀쩡한데 게이트만 거짓 red가 날 수 있다(기술부채 #24와 같은 성격의 사각지대가 storage 축에도 새로 생김, 별도 부채로 등록하지 않음 — 트리거 발생 전이라 무해). **정책이 실제로 거른다는 증명은 오직 AC7(원격 실측)이 한다** — Task 7의 6개 시나리오가 전부 기대대로 나왔고, 트랜잭션이 자동 롤백돼 원격에 찌꺼기 0건임을 별도 쿼리로 재확인했다.
- **범위 준수**: 서명 URL 헬퍼·업로더 UI·카드/갤러리·api 코드·seed.sql 수정은 전부 손대지 않음(9.2~9.7 및 범위 밖 문서는 그대로 둠).

### File List

- `supabase/migrations/0012_listing_images.sql` (신규) — listing_images 테이블·트리거·비공개 버킷·RLS(테이블+storage.objects)·GRANT
- `scripts/migration-check-prelude.sql` (수정) — storage 스키마 최소 스텁(buckets/objects) + RLS enable 추가
- `docs/conventions.md` (수정) — §10 이미지 스토리지 계약 신설, §6 FR11 강제 지점 목록에 storage 읽기 정책 추가
- `docs/tech-debt.md` (수정) — #27 판단((c) 이월) 반영, #18 범위(listing_images anon+ai_readonly만 명시) 반영
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (수정) — 9.1 상태 갱신
- `_bmad-output/implementation-artifacts/9-1-listing-images-스키마-비공개-버킷-storage-rls.md` (수정) — 이 스토리 파일 자체(frontmatter·태스크 체크·Dev Agent Record)

**코드리뷰 추가분 (2026-07-16, 새 세션·opus):**
- `supabase/migrations/0013_listing_images_path_integrity.sql` (**신규**) — `storage_path` 위조 차단 트리거(소유자를 `listings`에서 직접 구함) + `storage.objects` 쓰기 정책 `for all`→3동사 분리
- `docs/conventions.md` (수정) — §10 경로 규칙에 "DB가 강제한다" 반영 · §10 상한 3종의 **강제 주체가 셋 다 다르다**는 표로 교체("전부 DB에 박는다"는 사실보다 강했음)
- `docs/tech-debt.md` (수정) — #18 라이브 모순 정리 + storage GRANT 축 추가 + "anon 컬럼 차단" 표현 정정 + anon 쓰기 GRANT 이월 · **#43~#50 신설**(9.1 리뷰 이월 8건)
- `_bmad-output/implementation-artifacts/9-1-*.md` (수정) — Review Findings 절 · Debug Log 5-1(GRANT 덤프 원본) · Debug Log 6(재실측)

### Change Log

| 날짜 | 변경 |
|---|---|
| 2026-07-16 | Story 9.1 구현 — `0012_listing_images.sql` 신설(테이블·10장 트리거·비공개 버킷·RLS 5+2정책·GRANT), 게이트 프렐류드 storage 스텁 확장, `docs/conventions.md` §10·§6 갱신, `docs/tech-debt.md` #27((c) 이월)·#18(범위 갱신) 반영, 원격 적용 + AC7 6개 시나리오 실측 통과 (커밋 `56c47af`) |
| 2026-07-16 | 1차 push가 Migration Gate를 트리거하지 않는 현상 발견(웹훅 지연/유실 **추정** — 코드리뷰 실측 결과 `paths` 필터로는 설명 안 되므로 **원인 미해결**, `tech-debt.md` #50-3) → 프렐류드 주석 1줄 추가 후 재푸시로 CI 재트리거 및 초록 확인(커밋 `80978b8`, run `29443011386`) |
| 2026-07-16 | **코드리뷰(새 세션·opus, 3층 병렬 적대적 리뷰)** — 9 decision / 12 patch / 1 defer / 5 기각. **★ `storage_path` 위조 권한상승을 원격에서 재현**(anon 0행→1행) → **`0013_listing_images_path_integrity.sql` 신설로 차단**(재실측: 위조 거부·anon 0행·정상경로 통과, 게이트 red→green 왕복). `storage.objects` 쓰기 정책 `for all`→3동사 분리. AC7이 안 태운 축(읽기 정책·쓰기 허용분기·`rollback`) 재실측 완료. 문서 patch 6건 적용(#18 라이브 모순·storage GRANT 축·"컬럼 차단" 표현·§10 상한 주체·GRANT 덤프 원본·ai_readonly 대장 등재), 2건 기각(P4·P5 — 무해), 4건 이월(#50). 코드 결함 6건 이월(#43~#49) |
