# 배포 런북 (Deployment Runbook)

> Story 8.6(AC-DEPLOY-1)의 산출물. 증분(Epic 9~16)에서 db·api·web·app을 분리 배포할 때 순서·정합성·롤백을 이 문서가 못박는다.
> 근거: `_bmad-output/implementation-artifacts/8-6-ac-deploy-1-배포-순서-마이그레이션-게이트.md`

---

## 1. 배포 타깃·트리거

| 타깃 | 플랫폼 | 트리거 | 산출물 위치 |
|---|---|---|---|
| **db** | Supabase(단일 프로젝트) | Supabase MCP `apply_migration`을 사람/에이전트가 실행(자동 트리거 없음) | `supabase/migrations/` |
| **api** | Cloud Run(서울) — 운영 `encar-ai-api`·개발 `encar-ai-api-dev` | GitHub 연동 자동 배포. `develop` push → dev 서비스, `main` push → 운영 서비스 | `api/Dockerfile` |
| **web** | Vercel | GitHub 연동 자동 배포. `develop` push → Preview, `main` push → Production(`bmad-encar-demo.vercel.app`) | `web/` |
| **app** | Flutter — **수동** | 사람이 직접 빌드·설치(자동 배포 없음) | `app/` |

⚠️ **api·web은 Git 연동 자동 배포다(B3 — Git 연동 배포).** `develop`/`main`에 push하면 그 브랜치용 배포가 자동 생성된다. **수동 배포 명령을 직접 치지 않는다** — `vercel deploy`, `gcloud run deploy` 등을 임의로 실행하지 않는다.

---

## 2. ⚠️ 단일 공유 Supabase — 이 런북 전체를 규정하는 전제

**dev·preview·운영이 Supabase 프로젝트 하나를 공유한다.** 별도의 dev DB·preview DB가 없다. 그래서:

- 마이그레이션을 적용하는 순간 **운영에도 즉시 반영**된다. "dev에서만 먼저 테스트"란 것이 db 계층엔 존재하지 않는다.
- 이것이 **db 마이그가 반드시 additive·nullable이어야 하는 이유**다 — 컬럼을 지우거나 타입을 바꾸면 구 버전 api·web이 그 자리에서 깨진다.
- 이것이 **db가 배포 순서 맨 앞인 이유**다 — 새 필드를 만드는 쪽(db)이 그걸 읽는 쪽(api·web)보다 먼저 있어야 한다.
- Story 8.5가 이를 실증했다: 마이그(0011)만 적용된 상태에서 구 운영 코드(api·web)가 무손상으로 계속 동작함을 확인.

---

## 3. 배포 순서: db → api → web → app

```
1. db  (Supabase MCP apply_migration)
2. api (Cloud Run — develop/main push로 자동)
3. web (Vercel — develop/main push로 자동)
4. app (Flutter — 수동, 필요 시)
```

**왜 이 순서인가**: 새 필드를 **읽는** 쪽(api·web)보다 **만드는** 쪽(db)이 항상 먼저 있어야 한다. 반대로 하면 api·web이 아직 없는 컬럼을 조회해 500 에러가 난다. app은 수동이라 배포 압박이 없고, 항상 맨 뒤에서 안전하게 따라간다.

---

## 4. 부분배포 정합성 표

증분 배포는 db·api·web이 항상 동시에 맞춰 나가지 않는다(자동 배포 타이밍이 다르고, app은 수동이라 더 뒤처진다). 아래 조합이 안전한지 정리한다.

| 조합 | 정합성 | 이유 |
|---|---|---|
| `db 신 / api 구 / web 구` | ✅ 무영향 | additive 컬럼은 구 코드가 안 읽으므로 존재를 모른 채 그대로 동작(Story 8.5 실증) |
| `db 신 / api 신 / web 구` | ✅ 무영향 | web이 신규 필드를 모르고 렌더하지 않을 뿐 — nullable 계약(`docs/conventions.md` §4)이 이를 보장 |
| `db 신 / api 구 / web 신` | ⚠️ **매 push마다 수 분간 실재** | api(Cloud Run)와 web(Vercel)은 **같은 push 하나에 동시 트리거**되는데 빌드 시간이 다르다(Vercel 대개 1~3분, Cloud Run은 Docker 빌드라 더 느림). **web이 먼저 올라와 아직 구 버전인 api를 호출하는 창이 생긴다.** web이 신규 api 응답 필드를 **요구**하면 그 기간 동안 깨진다 |
| `db 구 / api 신 / web 신` | ❌ **금지** | api·web이 아직 없는 컬럼/테이블을 참조 → 500. **순서 위반이므로 절대 만들지 않는다** |

**규칙**: db는 항상 api·web보다 먼저이거나 같이 가야 한다. db가 뒤처진 조합은 존재해선 안 된다.

**⚠️ api↔web 순서는 강제할 수단이 없다.** §3의 "api→web" 순서는 **같은 push에서 자동 배포되는 한 지킬 수 없다** — 어느 쪽이 먼저 끝날지는 빌드 시간이 정한다. 따라서 `db 신 / api 구 / web 신` 창을 **없앨 수는 없고 견뎌야 한다**:
- **원칙**: web은 **api의 신규 응답 필드를 요구하지 않는다**(nullable 계약 §4 + 소비처 방어적 읽기 — `docs/conventions.md` §4의 "계약-외 값 정규화"). 그러면 이 창은 무해해진다.
- **정 필요하면**: api 변경을 **먼저 별도 push**로 올려 배포 완료를 확인한 뒤 web을 push한다(두 번에 나눠 밀기).

---

## 5. 역순 롤백: web → api → db

장애 시 롤백은 배포의 **역순**으로 진행한다.

1. **web**: Vercel Instant Rollback(직전 Production 배포로 즉시 전환).
2. **api**: Cloud Run 이전 리비전으로 트래픽 이전(리비전 전환은 무중단).
3. **db**: 아래 §6 참조 — **역마이그레이션은 없다.**

---

## 6. ⚠️ db 롤백은 존재하지 않는다

마이그레이션은 **forward-only**다(project-context 규칙 10). `drop table`·`alter ... drop column` 등으로 되돌리는 역마이그레이션 파일을 만들지 않는다.

- **전략**: 애초에 **additive만 해서 롤백이 필요 없게 만든다.** 신규 컬럼은 항상 nullable, 신규 테이블은 기존 테이블에 영향 없이 독립적으로 추가한다.
- **정 되돌림이 필요하면**: **보상 마이그레이션(전진)**을 새로 작성한다 — 예를 들어 잘못 채운 컬럼값을 고치는 `UPDATE`나, 잘못된 정책을 고치는 새 `CREATE POLICY`를 다음 번호로 추가한다. 기존 파일을 지우거나 역방향으로 되돌리지 않는다.
- ❌ **`drop` 계열 명령을 치지 마라.** 이 DB는 dev·preview·운영이 공유하는 단일 프로젝트다(§2) — `drop`은 운영을 즉시 망가뜨린다.

---

## 7. 마이그레이션 적용 절차

> ⭐ **각 에픽의 첫 마이그레이션 스토리는 마이그레이션 게이트(CI) 통과가 DoD(Definition of Done)다** (`docs/conventions.md` §9.4). 게이트는 배포를 막지 않으므로(§8-⑤) **이 절차가 실질적인 문**이다 — 아래 1번을 건너뛰면 아무것도 막아주지 않는다.

1. **적용 전 필수**: `python scripts/check_migrations.py` 로컬 통과 확인(`scripts/migration-check-prelude.sql` + 전체 마이그를 fresh 컨테이너에 적용해 self-containment 검증).
   - ⚠️ **도커가 없는 환경에서는 이 스크립트가 종료코드 1로 끝난다** — 그때는 **CI의 `Migration Gate` 실행 결과(run id·headSha·conclusion)를 근거로 남긴다.** 로컬 실패를 "확인함"으로 적지 않는다(`docs/tech-debt.md` #99).
1-b. **기존 객체를 교체하는 마이그(정책·함수·트리거)라면, 적용 전에 원격의 현재 원문을 떠서 스토리에 붙인다.** (✎ 2026-07-21 코드리뷰가 규칙으로 승격 — Story 9.7의 AC4가 이걸 요구했는데 **원문이 어디에도 남지 않았고**, 남은 건 *"원문대로 들어갔다"* 는 사후 서술뿐이었다. 이미 적용된 뒤라 되돌려 확인할 수 없다. `#18`이 반복해 증명한 것이 *"요약본이 가린 사실"* 이다.)
   ```sql
   -- 예: RLS 정책을 바꾸기 전
   select polname,
          pg_get_expr(polqual, polrelid)      as using_expr,
          pg_get_expr(polwithcheck, polrelid) as with_check_expr
     from pg_policy
    where polrelid = 'public.<테이블>'::regclass;
   ```
   - 적용 **후에도** 같은 쿼리를 돌려 두 벌을 나란히 남긴다. "의도대로 들어갔다"는 **before/after 두 벌이 있어야** 확인이지, 한 벌만으로는 주장이다.
2. 적용은 **Supabase MCP `apply_migration`**로 한다. `supabase db push` 등 **CLI가 아니다** — 이 프로젝트엔 Supabase CLI도 `config.toml`도 없다.
3. `apply_migration`의 `name` 파라미터는 **파일명 stem 그대로** 쓴다(예: `0012_listing_images`). 번호를 빠뜨리면 원장과 어긋난다 — `listings_anon_select`(0011의 번호 없는 재적용)가 실제 발생 사례다(§8-③ 참조).
4. **정본 파일 in-place 수정 + 따라잡기 패치 규약** (`docs/conventions.md` §9에 상술):
   - 정본 마이그(`NNNN_이름.sql`)에 코드리뷰 지적 등으로 수정이 필요하면, **in-place로 고친다**(새 번호를 만들지 않는다). fresh DB는 항상 이 정본을 그대로 재현한다.
   - 이미 그 정본을 적용받은 **살아있는 원격 DB**에 그 수정을 반영해야 하면, **따라잡기 패치**(`NNNNb_이름.sql` 등, 알파벳 접미사)를 새로 만들어 **원격에만** 적용한다. 신규 환경은 정본 파일 자체가 이미 최신이므로 따라잡기 패치가 불필요하다 — 파일로 남기지 않는다.
   - 원격에 따라잡기 패치가 필요해지는 순간(=살아있는 공유 DB를 직접 건드리는 순간)은 **사용자 승인이 필요하다**(`docs/conventions.md` §9 판정규칙 (b)).

---

## 8. 게이트의 사각지대 (정직하게)

`.github/workflows/migration-gate.yml`(Story 8.6이 신설한 CI)의 초록불이 **정확히 무엇을 증명하는지, 무엇을 증명하지 않는지** 명시한다. 게이트가 다 막아준다고 착각하면 오히려 더 위험하다.

1. **초록의 정확한 의미**: "**마이그 + 선언된 Supabase 계약면(`scripts/migration-check-prelude.sql`) = 도는 DB**"를 증명한다. "**마이그만으로 = 도는 DB**"를 증명하지 **않는다**. 테이블 GRANT 같은 "출입증" 발급 일부가 마이그가 아니라 프렐류드/Supabase 플랫폼 기본값에 있다 — 그래서 **맨 Postgres(자체 호스팅·타 클라우드)로는 이 레포만으로 못 선다.** 오늘은 무해하다(Supabase 전제·납품 계획 없음 — 사용자 확정 2026-07-14). 상세는 `docs/tech-debt.md`의 "테이블 GRANT 플랫폼 의존" 항목.
2. **fresh DB == 살아있는 원격 DB를 보증하지 않는다.** 정본 in-place 수정 + 따라잡기 패치 규약(§7-4)은 "원격에도 정확히 따라잡기 패치를 적용했는가"를 **사람의 성실성에 의존**한다. 게이트는 로컬 fresh 컨테이너만 검증하고 원격 상태를 조회하지 않는다.
3. **프렐류드가 선언한 것에 대한 의존은 설계상 안 잡힌다.** 예를 들어 `auth.uid()`나 `anon`/`authenticated` 롤 존재를 가정하는 마이그는 정상 통과한다 — 이건 의도된 것이다(Supabase가 실제로 제공하는 것이므로).
4. **정적 검사만 돈 경우(도커 없음)는 통과가 아니다.** 게이트는 도커가 없으면 "동적 검사 건너뜀"을 명시적으로 출력하며 **실패로 처리**한다(조용한 통과 금지).
5. ⚠️ **게이트는 배포를 막지 않는다 — 알릴 뿐이다.** 이 워크플로는 GitHub에 **상태 체크 하나를 띄울 뿐**이고, 브랜치 보호(required check)가 걸려 있지 않아 **red여도 push·머지·Vercel/Cloud Run 자동배포는 그대로 완주한다.**
   - **이건 결함이 아니라 이 프로젝트 흐름에 맞춘 선택이다**(2026-07-15 사용자 확정). required check는 **PR 머지 지점**에서 작동하는 장치인데 이 프로젝트는 PR을 쓰지 않는다(`develop` 직접 push → `main`도 직접 push). 막을 지점 자체가 없고, 직접 push를 브랜치 보호로 막으면 개발 흐름이 통째로 깨진다.
   - **실질 강제 지점은 §7-1의 "적용 전 `check_migrations.py` 통과 필수"** 다. 마이그가 공유 운영 DB에 닿는 유일한 문은 CI가 아니라 **`apply_migration` 호출**이고, 그 앞에 선 절차가 진짜 게이트다.
   - **CI 초록은 "체크가 돌았다"는 뜻이지 "무언가를 막았다"는 뜻이 아니다.**
6. ⚠️ **프로브는 "있는지"만 보고 "듣는지"는 안 본다 — 게이트 초록 ≠ RLS가 의도대로 작동함.** 프로브 3건은 전부 **카탈로그(메타데이터) 조회**다. 특히 ③은 `pg_policies`에 정책 **행이 존재하는지**만 확인하므로, 술어를 `using (true)` → `using (false)`로 바꿔도 **초록이 뜬다**(fresh DB에서 `ai_readonly`가 한 행도 못 읽는데도). 게이트 안엔 `set role`이 없어 프렐류드의 `auth.uid()` 스텁은 **항상 NULL**이다.
   - **의도된 한계다**(2026-07-15 사용자 확정): 프로브의 목적은 **대표 증인**이지 RLS 전수 검증이 아니고, 술어 검증에는 시드 행이 필요해 "행도 시드도 필요 없다"는 설계 전제가 깨진다. **RLS 술어 검증은 Story 8.5가 실 DB 배포본 E2E 28케이스로 이미 했다.**
7. ⚠️ **게이트는 파일이 *없어진 것*을 모른다 — 인벤토리 검사가 아니다.** 밀집 검사는 **정본(접미사 없는) 파일만** 대상이라, 접미사 파일(예: `0003c_chat_room_integrity.sql`)을 지워도 위반 0건으로 **초록**이 난다(실측 확인). 프로브 3건도 `listings`·`guide_documents`만 보므로 chat 계열이 통째로 사라져도 모른다. **접미사 파일을 지우기 전에 반드시 `docs/conventions.md` §9.2의 (가)/(나) 판별을 하라** — (가)는 fresh DB에 필요한 정본이다.
8. **게이트의 대상은 `supabase/migrations/`의 레포 파일뿐이다 — 원격 적용 이력이 아니다.** `list_migrations`로 원격을 뜨면 **레포에 파일이 없는 항목이 5건 나오고**(`0002b_listings_created_at_immutable`·`0002c_listings_price_bigint`·`0002d_listings_year_dynamic_max`·`0003b_chat_review_hardening`·`0003c_revoke_trigger_execute`), **적용 순서도 번호순이 아니며**(0006 → 0004 → 0003 → 0005), `listings_anon_select`처럼 **번호 없이 재적용된 것**도 있다. **이 셋 다 결함이 아니라 설명 가능한 이력이다** — 따라잡기 패치 규약(§7-4)의 산물이거나 과거의 적용 순서일 뿐이다. 게이트는 이것들을 대상으로 **삼지 않는다**. 원격 이력과 레포 파일이 1:1로 안 맞는 걸 보고 "드리프트 사고"로 오인하지 마라.
9. **게이트는 마이그 작성 방식을 조용히 제약한다.** 모든 파일을 `psql --single-transaction`으로 적용하므로 **트랜잭션 밖에서만 되는 문**(`create index concurrently`·`vacuum`·`alter system`·`reindex`)은 원격 `apply_migration`에선 통과해도 **게이트에선 `cannot run inside a transaction block`으로 red**가 난다. 현재 마이그 12개엔 해당 문이 0건이라 무해하나, **Epic 13(RAG)이 무중단 HNSW 인덱스를 얹으면 부딪힌다**(`deferred-work.md`에 박제됨).

> **왜 이 절이 필수인가**: 게이트 옆에 "이 게이트는 X를 안 본다"가 붙어 있어야 다음 사람이 초록불을 오해하지 않는다. **그리고 이 목록의 정직함이 곧 게이트 신뢰의 근거이므로, 빠뜨린 항목은 단순 누락보다 비싸다** — 항목 5~9는 2026-07-15 코드리뷰가 추가했다(초판이 사각지대 4개를 자백하면서 "배포를 막지 않는다"를 빠뜨렸다).
>
> **⚠️ 사각지대를 적을 땐 그것도 실측해서 적어라.** 이 절의 초안은 실측 안 된 추측(*"게이트가 초록이어도 authenticated가 못 읽는다"*)을 담았다가 도커 실측 한 번에 거짓으로 판명돼 삭제됐다. **되살리지 마라.**

---

## 9. 🚨 `seed.sql` 재실행은 파괴적이다

**`supabase/seed.sql`을 다시 돌리면 사진과 채팅 이력이 전부 사라진다. 에러는 한 건도 안 난다.**

> **어디까지 실측이고 어디부터 추론인가** (✎ 2026-07-21 코드리뷰). 원래 제목이 *"실측으로 확정"*이었는데
> 아래에는 **잰 것과 안 잰 것이 섞여 있었다.** 이 프로젝트가 `#80`에서 데인 것이 정확히 그 형태라 갈라 적는다.
> - ✅ **잰 것**: 아래 표의 행 수(`listing_images` 10→0 · `chat_rooms` 1→0 · 매물 id 보존 0/97).
> - ⚠️ **안 잰 것(스키마 추론)**: "Storage 고아 파일이 남는다". AC3이 Storage를 측정 범위에서 **뺐다**
>   (`listing_images` 행만으로 답할 수 있다고 판단). 그럴듯하지만 **관측된 적 없다.**
> - ⚠️ **측정 환경이 CI·운영과 다르다**: pg16 PGlite + `pgcrypto` 스텁(CI는 pg17, 운영은 Supabase).
>   원격에서 재현하지 않았다 — 재현 자체가 파괴적이라서다. 자세한 한계는 `docs/tech-debt.md` #99.

`seed.sql`은 멱등성을 위해 시드 판매자 매물을 `delete` 후 **새 uuid로 재삽입**한다(`:196`·`:413`). `listings`에는
`ON DELETE CASCADE` 자식이 **둘**(`listing_images` 0012 · `chat_rooms` 0003) 있어 함께 지워진다.

**빈 Postgres 실측 (Story 9.7, 2026-07-21):**

| | 재실행 전 | 재실행 후 |
|---|---|---|
| `listing_images` | 10행 | **0행** |
| `chat_rooms` | 1행 | **0행** |
| `listings` | 97행 | 97행 (수만 같고 **id는 0/97건 보존**) |

- ⚠️ **Storage 오브젝트는 CASCADE 대상이 아니다**(추론) → 파일은 남고 그걸 가리키는 행만 사라져 **고아 파일**이 될 것으로 본다.
- ⚠️ **"에러 0건"을 정상으로 읽지 마라.** 확인은 반드시 **행 수**로 한다(`docs/tech-debt.md` #89).

**그래도 해야 한다면 순서:**
1. `listing_images`·`chat_rooms`·`chat_messages`를 먼저 백업(또는 유실을 수용한다고 명시적으로 결정).
2. **재실행 전에 현재 Storage 오브젝트 목록을 떠 둔다** — 3번으로 사진을 다시 채우면 **옛 파일은 아무 행도
   가리키지 않는 고아로 남는다.** 이 단계가 없으면 재실행할 때마다 버킷에 미참조 WebP가 누적되고,
   어느 문서도 그 청소를 지시하지 않는다(✎ 2026-07-21 코드리뷰가 빠진 단계로 지적).
3. `seed.sql` 실행.
4. `scripts/seed_listing_photos.py`를 `--email` 바꿔가며 시드 판매자 수만큼 다시 실행해 사진을 복구.
   - ⚠️ **이 복구 절차는 한 번도 실행해 본 적이 없다.** 사진 시딩은 재실행 **전** 상태에서만 돌았다.
5. 2번에서 뜬 목록과 대조해 **고아 오브젝트를 지운다**(선례: `docs/tech-debt.md` #77 — 사용자 승인 후 정리).
6. 채팅 이력은 **복구 수단이 없다.**

---

## 10. sold 매물을 실수로 만들었을 때 — 되돌리는 유일한 방법

`0015` 적용 이후 **`status='sold'`가 된 매물은 판매자도 관리자도 되돌릴 수 없다.** RLS가 sold 행을
UPDATE 대상에서 아예 빼기 때문에 어느 화면에서 눌러도 **"0행 변경"**으로 끝난다(에러가 아니라 무반응처럼 보인다).
관리자에게는 `listings` UPDATE 정책이 없고(`0005`), `service_role` 키는 프로젝트 금지다(`conventions.md` §5).

**이건 가정이 아니라 이미 한 번 밟았다** — Story 9.7이 `0015` 원격 검증 중 테스트 매물 하나를 sold로 바꿨다가
되돌리지 못해 아래 방법으로 복구했다. 그때 대장·런북에 안 남겨서 코드리뷰가 다시 잡았다(`docs/tech-debt.md` #91).

**복구 방법: DB에 직접 붙어 실행한다**(Supabase SQL Editor 또는 MCP `execute_sql`). RLS는 이 경로에 안 걸린다.

```sql
-- 1) 먼저 대상을 눈으로 확인한다 (id를 모르면 조건으로 좁힌다)
select id, manufacturer, model, price, status, updated_at
  from public.listings
 where status = 'sold'
 order by updated_at desc
 limit 10;

-- 2) 확인한 id 하나만 되돌린다 (where 절 없이 실행하지 말 것)
update public.listings set status = 'on_sale'
 where id = '<확인한 uuid>'::uuid;
```

- ⚠️ **`where` 절을 반드시 id로 좁힌다.** 이 경로는 RLS가 안 막으므로 실수하면 전량이 바뀐다.
- 📌 이건 **운영자 수동 개입**이지 기능이 아니다. 사용자가 스스로 되돌려야 하는 요구가 생기면
  `#91`의 선택지(관리자 UPDATE 정책 / 복구 전용 좁은 정책)를 그때 판단한다.

---

## 참고

- 마이그레이션 파일명 규약·레시피 결정·판정규칙: `docs/conventions.md` §9
- 게이트 스크립트: `scripts/check_migrations.py`, `scripts/migration-check-prelude.sql`
- 스토리 원문: `_bmad-output/implementation-artifacts/8-6-ac-deploy-1-배포-순서-마이그레이션-게이트.md`
