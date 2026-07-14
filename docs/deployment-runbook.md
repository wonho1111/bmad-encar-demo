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
| `db 구 / api 신 / web 신` | ❌ **금지** | api·web이 아직 없는 컬럼/테이블을 참조 → 500. **순서 위반이므로 절대 만들지 않는다** |

**규칙**: db는 항상 api·web보다 먼저이거나 같이 가야 한다. db가 뒤처진 조합은 존재해선 안 된다.

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

1. **적용 전 필수**: `python scripts/check_migrations.py` 로컬 통과 확인(`scripts/migration-check-prelude.sql` + 전체 마이그를 fresh 컨테이너에 적용해 self-containment 검증).
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

> **왜 이 절이 필수인가**: 게이트 옆에 "이 게이트는 X를 안 본다"가 붙어 있어야 다음 사람이 초록불을 오해하지 않는다.

---

## 참고

- 마이그레이션 파일명 규약·레시피 결정·판정규칙: `docs/conventions.md` §9
- 게이트 스크립트: `scripts/check_migrations.py`, `scripts/migration-check-prelude.sql`
- 스토리 원문: `_bmad-output/implementation-artifacts/8-6-ac-deploy-1-배포-순서-마이그레이션-게이트.md`
