---
baseline_commit: cb6cba50a1f3ea4c1fd91753da562ba4a9c96fa3
---

# Story 9.1: listing_images 스키마 + 비공개 버킷 + Storage RLS

Status: in-progress

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
- [ ] **Task 8 — 커밋·푸시·CI 확인 (AC5)**
  - [ ] `develop`에 의미 단위 커밋(한국어 메시지)
  - [ ] `git push origin develop` → GitHub Actions **Migration Gate 초록 실측 확인**(run id 기록)
  - [ ] `main` 병합은 **하지 않는다**(사용자 승인 사항)
- [ ] **Task 9 — Epic 8 회고 액션 이행 확인 (회고 A3·A5)**
  - [ ] **A5 "실측 없이 선언하지 않는다"**: 이 스토리가 산출물(마이그·계약·대장)에 박은 주장 중 **실측 없이 적힌 것이 0건**임을 확인. 특히 프렐류드 storage 스텁은 **추측이 아니라 Task 1의 원격 덤프**에 근거해야 한다
  - [x] **A1 "대장은 하나"**: 열린 항목은 `docs/tech-debt.md`에만 적는다. `deferred-work.md`는 **동결**됐다 — 거기에 새로 쓰지 않는다

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

**5. Task 8 — GitHub Actions Migration Gate run id + conclusion**: 아래 File List 커밋 후 채움.

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

### Change Log

| 날짜 | 변경 |
|---|---|
| 2026-07-16 | Story 9.1 구현 — `0012_listing_images.sql` 신설(테이블·10장 트리거·비공개 버킷·RLS 5+2정책·GRANT), 게이트 프렐류드 storage 스텁 확장, `docs/conventions.md` §10·§6 갱신, `docs/tech-debt.md` #27((c) 이월)·#18(범위 갱신) 반영, 원격 적용 + AC7 6개 시나리오 실측 통과 |
