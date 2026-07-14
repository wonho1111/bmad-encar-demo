# Story 8.6: AC-DEPLOY-1 배포 순서 + 마이그레이션 게이트

Status: review

## Story

As a 개발·배포 담당,
I want 증분 배포 순서와 마이그레이션 번호 규칙을 먼저 못박길,
so that db·api·web·app 분리 배포에서 계약이 깨지거나 롤백이 꼬이지 않는다.

> **이 스토리의 성격 — 읽고 시작할 것.** 산출물이 **문서 + 검사 도구 + CI 워크플로**다. 제품 기능이 아니라 **Epic 9~16이 딛고 설 안전장치**다. Epic 9~16은 마이그레이션을 8개 더 추가하므로(원장 0012~0019), 이 게이트가 없으면 각 에픽이 "번호가 맞나? 신규 환경에서 되나?"를 매번 손으로 확인하거나 그냥 넘긴다.
>
> **핵심 제약(조사로 확정됨, 가정 아님):** 이 프로젝트엔 **로컬 Supabase 스택도 supabase CLI도 CI도 없다.** 마이그레이션은 **Supabase MCP `apply_migration`으로 원격 호스티드 DB에 에이전트가 직접 적용**해 왔다. 그리고 그 원격 DB는 **dev·preview·운영이 공유하는 단 하나의 프로젝트**다. 이 세 가지가 이 스토리 설계 전체를 규정한다. **이 스토리가 그중 "CI 없음"을 끝낸다**(GitHub Actions 신설 — 사용자 확정).
>
> ### 🔑 이 스토리가 답하는 근본 질문 (party-mode 2026-07-14 확정)
>
> **"`supabase/migrations/`의 파일들은 *로그*인가 *레시피*인가?"** — 이 팀은 이걸 결정한 적이 없다. Amelia는 레시피라 가정하고 에픽에 "번호순=적용순=개발순" 불변식을 박았고, 실제로는 **로그처럼 굴러왔다**(살아있는 DB 하나에 뭘 했는지의 기록). 둘 다 문서엔 없었다. 그래서 `0004`가 뒤 번호 `0006`을 가정해도 아무도 몰랐고 아무 문제도 없었다 — **fresh DB를 한 번도 만든 적이 없으니까.**
>
> **사용자 결정: 레시피다.** 근거 3가지(이게 "왜"다 — 지우지 마라. 이유 없는 규칙은 다음 사람이 또 뒤집는다):
> 1. **원격 Supabase 프로젝트가 하나뿐이라 그게 날아가면 복구 = fresh DB다. 현재 복구 경로가 없다.** ← 이게 지금 이 결정을 떠받치는 **주 기둥**이다.
> 2. ~~외주/납품 성격이라 "레포만으로 DB가 선다"가 인수 조건에 들어갈 수 있다.~~ → **2026-07-14 정정: 납품 계획 없음(사용자 확인). 이 근거는 지금 비어 있다.** 살아나면 "맨 Postgres에서도 서는가"가 쟁점이 되고, 그땐 Dev Notes "플랫폼 기본 GRANT" 별항의 마지막 항목이 답이다.
> 3. **Epic 9~16이 마이그 8개를 더 얹는다.** 지금 1건인 순서 뒤틀림이 20개 파일에선 몇 건이 될지 모른다.
>
> **범위 한정(사용자 확정 2026-07-14): Supabase 전제.** "레포만으로 DB가 선다"는 **Supabase 프로젝트 위에서** 참이면 된다. 맨 Postgres 이식성은 목표가 아니다 — 없는 시나리오를 위해 짓지 않는다(A2).
>
> **불변식의 정확한 이름**(Winston·Amelia 합의 — "번호순=적용순"이라 부르지 마라):
> > **각 마이그는 자기가 필요로 하는 선행 상태를 스스로 만들거나(멱등 가드), 번호가 더 작은 마이그에만 의존한다. 원격 적용 이력의 순서는 상관없다.**
>
> 즉 **번호 갭은 무죄**(0003·0005 자리 비워둬도 무해), **역방향 의존만 유죄**. 번호가 곧 의존 그래프의 위상순서라는 선언이고, 그게 성립해야 fresh DB 재현이 가능하다.

## Acceptance Criteria

**Given** db·api·web·app 3~4개 배포 타깃
**When** 증분을 배포하면

1. 배포 순서 **db(마이그)→api(Cloud Run)→web(Vercel)→app(수동)** 와 nullable 하위호환·부분배포(db+api 신, web 구) 정합성·단계 실패 시 역순 롤백을 담은 **배포 런북(runbook) 문서**가 산출된다(AC-DEPLOY-1).
2. **마이그 순서 CI 체크(실행 가능한 스크립트)** 가 산출된다 — fresh DB에 0001부터 번호순 전체 적용이 성공하고, 번호 공백(gap)·out-of-order·비-self-contained(앞 마이그 상태 가정)를 **실패로 잡는다**. 각 에픽 첫 마이그 스토리는 이 체크를 통과해야 한다.
   - **"CI"는 은유가 아니라 GitHub Actions다**(사용자 확정). 사람이 기억해야 도는 체크는 6개월 뒤 안 돈다(Winston). 워크플로 파일을 **이 스토리에서 실제로 만들고 실제로 돌려 초록을 확인**한다. 배포 파이프라인과 **독립**이며 **원격 DB에 SQL을 보내지 않는다**(빈 컨테이너를 매번 새로 띄우고 버린다).
6. **[게이트의 사각지대 명기]** 게이트가 **보지 않는 것**을 게이트 문서 자체에 적는다 — 핵심은 **게이트의 초록은 "마이그 + 선언된 Supabase 계약면 = 도는 DB"를 뜻하지 "마이그만으로 = 도는 DB"를 뜻하지 않는다**는 것. 출입증(테이블 GRANT) 발급이 마이그가 아니라 프렐류드/플랫폼에 있어, **맨 Postgres로는 이 레포만으로 못 선다**(Supabase 전제라 지금은 무해 — 사용자 확정). 별도 이슈로 박제.
3. 마이그 번호는 **"마이그레이션 원장"** 표(`epics-increment-2026-07-12.md:252`)가 정본이며, 현 에픽 순서대로 **0011~0019**를 확정한다(0011=8.5 listings anon SELECT 삽입으로 +1 시프트됨. 아키텍처의 0011~0018은 논리 라벨이었고 실제 번호는 이 원장이 우선).
4. **[게이트 자체의 red→green 증명]** 위 체크가 실제로 무는지를, 위반 사례를 **일부러 만들어** 각각 red로 떨어뜨린 뒤 원복해 증명한다(gap·중복번호·프렐류드 밖 의존 최소 3종). *"체크를 만들었다"가 아니라 "체크가 잡는다"가 완료 기준이다.*
5. **[범위 경계]** 이 스토리는 **마이그레이션을 새로 추가하지 않는다**(원장 0012~0019는 각 에픽 소유). 다만 게이트가 적발한 **기존 파일의 self-containment 결함은 정본 in-place 수정으로 고친다** — 이 레포의 확립된 규약이며(Dev Notes "원격 이력의 정체"), 현재 **0004 1건이 확정 적발 상태**다(아래 "0004 문제"). 그 외 0001~0011은 손대지 않는다.

## Tasks / Subtasks

- [x] **Task 1 — 사실 확인부터: 원격 마이그 이력 실측 대조** (AC: 3)
  - [x] Supabase MCP `list_migrations`로 원격 이력을 뜬다. **아래 Dev Notes의 "원격 이력 실측" 표와 대조**하고, 이 스토리 착수 시점에 달라진 게 있으면 그것부터 보고한다.
  - [x] 확인할 사실 3가지: ① 원격에만 있고 레포엔 파일이 없는 마이그 5건(0002b·0002c·0002d·0003b·0003c_revoke_trigger_execute) ② 실제 적용 순서가 번호순이 **아님**(0006→0004→0003→0005) ③ `0011_listings_anon_select`가 `listings_anon_select`(번호 없음)로 **한 번 더** 적용됨.
  - [x] **이 3가지는 결함이 아니라 설명 가능한 이력이다**(Dev Notes "원격 이력의 정체" 참조). 게이트가 이것들을 대상으로 삼지 **않는다**는 점을 런북에 명시한다 — 게이트의 대상은 **레포 파일**이지 원격 이력이 아니다.

- [x] **Task 2 — 부트스트랩 프렐류드 작성** (AC: 2)
  - [x] 신규: `scripts/migration-check-prelude.sql`
  - [x] 내용 = **우리 마이그레이션이 Supabase 플랫폼에 의존한다고 "선언하는" 계약면**. Dev Notes "프렐류드 계약면" 목록 그대로. 그 이상도 이하도 만들지 않는다 — **최소성이 게이트의 이빨**이다(프렐류드에 없고 앞 마이그도 안 만든 것에 의존하면 실패).
  - [x] 파일 상단 주석에 **"여기 있는 것 = 우리가 Supabase에 의존한다고 인정한 것. 추가하려면 그 의존이 정당한지 먼저 답할 것"** 을 명시(프렐류드를 늘려 red를 무마하는 우회 차단).

- [x] **Task 3 — 체크 스크립트 작성** (AC: 2)
  - [x] 신규: `scripts/check_migrations.py` — **Python 표준 라이브러리만**. DB 드라이버 불필요(SQL은 컨테이너 안 `psql`로 실행 — Dev Notes "왜 psycopg가 아닌가" 참조).
  - [x] **정적 검사**(도커 없이도 도는 층): ① 파일명 규약 `^\d{4}[a-z]?_[a-z0-9_]+\.sql$` ② 번호 밀집(0001~max 공백 없음) ③ 바닥번호 중복 없음 ④ 접미사 파일은 같은 바닥번호 파일이 선행 존재.
  - [x] **동적 검사**: `docker run pgvector/pgvector:pg17` → 프렐류드 → **파일명 정렬 순서**(= 번호순, 접미사는 알파벳순)로 전량 적용 → 전부 성공해야 통과. 끝나면 컨테이너를 **반드시 정리**(성공·실패·중단 무관, `try/finally`).
  - [x] ⚠️ **파일당 `psql --single-transaction -v ON_ERROR_STOP=1`** + **첫 실패 시 즉시 전체 중단**(뒤 파일 계속 적용 금지). 둘 다 필수다 — 없으면 실패한 마이그의 앞부분이 커밋된 채 뒤 파일들이 "OK"로 통과해, **게이트 출력이 거짓말을 한다**(0004가 44행에서 죽어도 테이블·인덱스는 남고 0005~0011이 전부 통과해 "0004 하나만 문제"로 보인다. 실제론 guide_documents가 RLS 없이 열린 반쪽 상태다).
  - [x] **self-containment 프로브 3건**(post-apply, 데이터·행 불필요 — 카탈로그 조회). **3건이 서로 다른 실패 축을 증인해야 한다**:
    - ① 컬럼 GRANT 축: `has_any_column_privilege('anon','public.listings','select')` = **true**
    - ② 컬럼 차단 축: `has_column_privilege('anon','public.listings','embedding','select')` = **false**
    - ③ **RLS 정책 축**: `pg_policies`에 `guide_documents_ai_readonly_select` 존재 = **true**
  - [x] ⚠️ ①에 `has_table_privilege`를 쓰지 마라 — **false가 정답이라 가짜 red가 난다.** `0011:28`이 `revoke select on public.listings from anon`으로 테이블 권한을 **일부러 회수**하고 `0011:38~`이 컬럼 스코프로만 재부여했기 때문이다(8.5의 설계 의도). 이걸 결함으로 오인해 0011을 고치지 마라.
  - [x] ⚠️ ③을 GRANT 프로브로 바꾸지 마라 — `0006:30`의 `grant select on all tables in schema public to ai_readonly`가 **가려버려서 항상 true가 뜬다**(0004가 통째로 실패해도). 이 레포가 두 번 경고한 함정이 *"GRANT만으론 행이 안 보인다 — 정책 필수"*(`0004:43`·`0006:12`)인데, GRANT만 보는 프로브는 그 함정을 정확히 비껴간다.
  - [x] 종료코드: 통과 0 / 위반 1. 위반은 **어느 파일의 무엇이 왜** 인지 한국어로 출력. 도커 없으면 정적 층만 돌고 **명확히 "동적 검사 건너뜀"을 출력하며 실패로 처리**(조용한 통과 금지).

- [x] **Task 3b — GitHub Actions 워크플로 신설** (AC: 2)
  - [x] 신규: `.github/workflows/migration-gate.yml`. **이 레포 최초의 CI다** — `.github/`가 아예 없으므로 디렉터리부터 생긴다.
  - [x] 트리거: `push`(develop·main) + `pull_request`. **paths 필터**로 `supabase/migrations/**`·`scripts/**`·워크플로 자신이 바뀔 때만 돈다(무관한 push에 노이즈 금지).
  - [x] 잡 본문은 **3스텝이면 끝나야 한다**: `actions/checkout` → `actions/setup-python`(3.11) → `python scripts/check_migrations.py`. **의존성 설치 스텝이 없다**(stdlib only). 스텝이 늘어난다면 Task 3의 설계가 틀린 것이니 돌아가라.
  - [x] `ubuntu-latest` 러너엔 도커가 이미 있다 → 스크립트가 자기 컨테이너를 띄우는 방식 그대로 **로컬과 CI가 같은 명령**으로 돈다. GH Actions `services:`를 쓰지 마라 — 스크립트가 두 갈래(로컬/CI)가 되고, 그 순간 "로컬에선 되는데 CI에선"이 시작된다.
  - [x] 액션 버전은 **핀**하고(`@v4`/`@v5` 등), 착수 시점의 최신 안정 버전을 확인해 쓴다.
  - [x] ⚠️ **배포 파이프라인을 건드리지 마라.** Vercel·Cloud Run 자동 배포는 GitHub 연동으로 이미 돌고 있다(B3). 이 워크플로는 그것들과 **완전히 독립**이며 배포를 트리거하지도 차단하지도 않는다. secrets 불필요(원격 DB에 접속 안 함).
  - [x] **실제로 push해서 초록을 확인**한다(B4). Actions 탭 결과가 증거다 — yml을 쓴 것으로 완료 보고하지 마라.

- [x] **Task 4 — 배포 런북 작성** (AC: 1)
  - [x] 신규: `docs/deployment-runbook.md`. 목차는 Dev Notes "런북에 반드시 들어갈 것" 8개 항목 전부.
  - [x] ⚠️ **가장 중요한 절**: "**Supabase는 dev·preview·운영이 공유하는 단일 프로젝트다**" — 마이그 적용 순간 운영에도 반영된다. 이것이 db 마이그가 **반드시 additive·nullable**이어야 하는 이유이자, db가 배포 순서 **맨 앞**인 이유다. 8.5가 이걸 실증했다(마이그만 적용된 상태에서 구 운영 코드 무손상 확인).
  - [x] **db 롤백은 없다**를 명문화 — forward-only라 역마이그가 없다. 그래서 db 단계의 롤백 전략 = "additive만 해서 롤백이 필요 없게 만든다" + 정 필요하면 **보상 마이그(전진)**. 이걸 안 적으면 다음 사람이 사고 시 `drop`을 친다.
  - [x] `docs/tech-debt.md`·`docs/conventions.md`에서 런북을 가리키는 한 줄 링크를 추가(발견 가능성). **문서 내용 복제 금지** — 링크만.

- [x] **Task 5 — 0004 self-containment 수정 + 게이트 red→green 증명** (AC: 4, 5)
  - [x] **red 1 — 천연(0004, 이 스토리의 주력 증거)**: 아무것도 안 심고 체크를 돌리면 **이미 red다**. 예상 출력: `0004_guide_documents.sql : FAIL — role "ai_readonly" does not exist`. 이 원문을 먼저 기록한다. *(인위적 red보다 이게 낫다 — 게이트가 첫 실행에서 실재 결함을 잡았다는 증거다.)*
  - [x] **green 1 — 0004 수정**: `0004_guide_documents.sql`의 `grant select on public.guide_documents to ai_readonly`(44행) **앞에**, `0006_readonly_role.sql:22-26`의 멱등 DO 블록을 **그대로 복사**해 넣는다. 새 패턴 발명 금지 — 레포에 이미 있는 패턴이다. 상단 주석에 "0006과 중복 생성이지만 양쪽 다 멱등이라 번호순·역순 어느 쪽으로 적용해도 안전"을 1줄.
  - [x] **green 1 검증**: 재실행 → 0004 통과 + **0006도 통과**(0006의 DO 블록이 이미 있는 롤을 만나 no-op) 확인. 두 번째가 핵심이다 — 0004의 수정이 0006을 깨면 실패다.
  - [x] **원격 영향 확인**: 원격엔 `ai_readonly`가 이미 있으므로 이 수정은 **재적용해도 no-op**이다 → **따라잡기 패치 불필요**. 이 판단 근거를 Dev Agent Record에 적는다(재적용하지 말 것 — 원격 이력은 건드리지 않는다). 판정 규칙상 **(a)**에 해당한다(3조건 전부 만족).
  - [x] **주석 갱신**(Amelia): `0004:2-3`의 *"적용 순서: 0001 → 0002 → 0004 → 0006(이미 적용)"* 과 `0006:18-20` 번호 갭 메모는 **실행되지 않는 지시문**이다 — 주석은 계약이 아니다. 이제 SQL 가드가 그 계약을 지므로, 두 주석을 **"과거에 이 순서로 적용했다"는 사실 기록**으로 바꾼다(현재 요구사항인 척하지 않게). **주석과 SQL이 모순 없음**이 검증 항목.
  - [x] **0006:22-26은 그대로 둔다** — 삭제도 변경이고, no-op이라 비용 0이다(A3 외과적).
  - [x] **red 2(gap)**: 빈 `0013_zzz_probe.sql` 임시 생성(현 max=0011 → 0012 공백) → 체크 **실패** 확인 → 삭제.
  - [x] **red 3(중복번호)**: `0011_dup_probe.sql` 임시 생성 → 체크 **실패** 확인 → 삭제.
  - [x] **red 4(계약면 밖 의존)**: 임시 `0012_probe.sql`에 `grant select on public.listings to undeclared_role;` → apply **실패** 확인 → 삭제. *(프렐류드에서 롤을 빼는 방식은 쓰지 마라 — 프렐류드 자신이 `alter default privileges ... to anon`을 하므로 0001에 닿기도 전에 프렐류드 단계에서 죽는다. 그건 "프렐류드가 자기와 정합하다"를 증명할 뿐 계약면 밖 의존을 증명하지 못한다.)*
  - [x] **green 최종**: 전량 통과(종료코드 0). 각 red의 **실제 출력 원문**을 Dev Agent Record에 붙인다 — "실패했다"가 아니라 메시지 그대로.

- [x] **Task 6 — 원장·계약 반영** (AC: 3)
  - [x] `epics-increment-2026-07-12.md:252` 원장 **본표(258~266행)는 이미 0011~0019로 정본화돼 있다**(8.5가 시프트 반영 완료). **재작성하지 말고 대조만** 하고, 어긋나면 그때만 고친다.
  - [x] ✎ **같은 파일 106행은 시프트가 안 됐다** — *"예: role=원장 0018, wishlists=원장 0013"* 이라 적혀 있는데 본표는 role=**0019**, wishlists=**0014**다. 본표가 정본이므로 106행 예시만 고친다(이걸 안 고치면 다음 사람이 106행을 읽고 번호를 틀린다 — 8.5가 말한 계보 끊김의 축소판이다).
  - [x] `docs/conventions.md`에 **마이그레이션 파일명 규약**을 한 절로 추가 — `NNNN_이름.sql`(정본) + `NNNN[b-z]_이름.sql`(**따라잡기 패치**: 정본 파일을 in-place 수정했을 때 *이미 살아있는* DB만 따라오게 하는 멱등 패치). 이 규약은 이미 실무에서 쓰이고 있는데 **어디에도 안 적혀 있다** — 그게 이 태스크의 이유다.
  - [x] 런북에 "각 에픽 첫 마이그 스토리는 게이트(CI) 통과가 DoD"를 못박는다.
  - [x] ⭐ **"레시피 결정"을 이유와 함께 박는다**(Mary 요구 — 이 태스크의 핵심): `docs/conventions.md`에 *"`supabase/migrations/`는 **레시피**다 — 레포 파일만으로 빈 DB가 서야 한다"* + **위 Story 박스의 근거 3가지를 그대로**. 이유를 안 적으면 다음 사람이 또 *"실제와 안 맞는 규칙 아닌가?"* 를 묻는다. 정당한 질문인데 답이 매설돼 있어서다.
  - [x] ⭐ **판정 규칙 (a)/(b)를 문서에 박는다**(사용자 승인 완료 — Winston·Amelia 합의안). 위반 마이그 M이 뒤 번호 N의 객체를 가정할 때:
    - **(a) → dev 자율**(사후 보고). 3조건 **전부** 만족 시: ① 수정이 **멱등 가드 추가만**(`do $$ ... if not exists ... end $$` 계열) ② 원격 재적용 시 **상태 델타 0**을 실측 확인 ③ **기존 객체 정의 불변**(컬럼 타입·제약·정책 술어·GRANT 대상 변경은 틀 밖).
    - **(b) → 멈추고 사용자 승인.** 3조건 중 하나라도 어기면. 특히 **원격에 따라잡기 패치(`NNNNb`)가 필요해지는 순간 = 살아있는 공유 DB를 건드리는 순간 = 무조건 승인.**
  - [x] ⭐ **암묵 규약을 정본으로 승격**(Mary: *"그게 문서에 있었으면 이번 안건은 애초에 안건이 아니었다"*). 위 파일명 규약 항과 **한 절로 묶어** 쓴다 — 지금 세션이 통째로 이 문서 한 줄의 부재 때문에 벌어졌다.

- [x] **Task 6b — 사각지대 명기 + 별도 이슈 박제** (AC: 6)
  - [x] 런북 "게이트의 사각지대" 절에 위 Dev Notes의 **"게이트가 증명하는 것과 안 하는 것"** 3항목을 그대로 옮긴다. **초록불의 의미를 정확히 한정하는 게 목적**이다.
  - [x] ⚠️ **쓰지 말아야 할 문장**: *"게이트가 초록이어도 authenticated가 못 읽는다"* — **실측 결과 거짓이다**(위 실측 블록). 설계 토론에서 나왔던 그럴듯한 주장이고, 이 스토리 초안에도 한 번 박혔다가 실측으로 뒤집혔다. 되살리지 마라.
  - [x] `docs/tech-debt.md`에 **별도 항목으로 박제**(사용자 확정 — 8.6 범위 밖). "검토 필요" 같은 미지근한 라벨 금지. 내용: **제목** = "테이블 GRANT가 마이그에 없고 Supabase 플랫폼 기본에 의존" · **위치** = 마이그 전체(0011의 anon+listings만 예외) · **오늘 무해한 이유** = Supabase 전제 + 복구 시에도 새 Supabase가 같은 기본값을 준다 · **언제 문제되나** = 자체 호스팅·타 클라우드 이관·맨 Postgres 납품 요구가 생기는 순간 · **해소 방향** = 각 테이블 마이그에 명시 GRANT 추가 후 프렐류드의 `alter default privileges` 한 줄 제거(판정규칙 (a) 해당 — 원격 델타 0이라 안전) · **비용** ≈ 테이블당 1~2줄.
  - [x] 8.5가 anon+listings에 대해서만 이 의존을 끊었다는 사실을 함께 적는다 — **체계적으로 찾은 게 아니라 다른 일 하다 우연히 걸린 것**이다. 나머지가 얼마나 되는지 아무도 세어본 적 없다.

- [x] **Task 7 — 실행·검증·보고** (AC: 2, 4)
  - [x] 최종 `python scripts/check_migrations.py` 로컬 실행 → 통과 출력 캡처.
  - [x] **push 후 GitHub Actions 초록 확인** — Actions 탭 결과가 증거다(B4).
  - [x] 런북의 배포 순서 서술이 **실제와 일치하는지** 확인: `develop` push → Vercel preview + Cloud Run dev 자동 배포가 맞는지 실제 관찰(B4 — 문서만 쓰고 "맞겠지" 금지).
  - [x] 커밋(B2, 한국어 의도). `main` 병합은 사용자 승인 시에만(B3).

## Dev Notes

### 손대는 파일 지도

| 파일 | 변경 | AC |
|---|---|---|
| `scripts/migration-check-prelude.sql` | **신규** — Supabase 플랫폼 계약면 최소 재현 | 2 |
| `scripts/check_migrations.py` | **신규** — 정적+동적 게이트, stdlib only | 2, 4 |
| `.github/workflows/migration-gate.yml` | **신규** — 이 레포 **최초의 CI**. 3스텝, secrets 불필요 | 2 |
| `docs/deployment-runbook.md` | **신규** — 배포 순서·부분배포·역순 롤백·**사각지대** | 1, 6 |
| `docs/conventions.md` | ✎ **마이그 정책 1절** — 파일명 규약 + in-place/따라잡기 규약 + **레시피 결정(이유 포함)** + 판정규칙 (a)/(b) + 런북 링크 | 3 |
| `docs/tech-debt.md` | ✎ **authenticated GRANT 부재 신규 항목** + 런북 링크 1줄 | 6 |
| `epics-increment-2026-07-12.md` | 원장 본표 **대조만** + 106행 예시 시프트 정정 | 3 |
| `supabase/migrations/0004_guide_documents.sql` | ✎ **in-place** — `ai_readonly` 멱등 생성 가드 삽입(0006에서 복사). **유일한 마이그 수정** | 4, 5 |
| `supabase/migrations/**` (0004 제외) | ❌ **손대지 않음** — 이미 원격 적용됨, forward-only | 5 |

### 원격 이력 실측 (2026-07-14, `list_migrations` 원본)

```
20260619110118 0001_profiles                          20260623192311 0003c_chat_room_integrity
20260619205810 0002_listings                          20260623192556 0003c_revoke_trigger_execute  ← 레포에 파일 없음
20260619210838 0002b_listings_created_at_immutable ← 파일 없음    20260623233045 0005_admin_policies
20260619211544 0002c_listings_price_bigint         ← 파일 없음    20260624155041 0007_listings_seller_name
20260619214354 0002d_listings_year_dynamic_max     ← 파일 없음    20260624163457 0008_chat_room_names
20260620160711 0006_readonly_role                   ← 적용순 역전  20260624171504 0009_profiles_name
20260620174443 0004_guide_documents                 ← 적용순 역전  20260711095642 0010_chat_message_length
20260623090355 0003_chat                            ← 적용순 역전  20260714075257 0011_listings_anon_select
20260623091055 0003b_chat_review_hardening          ← 파일 없음    20260714111347 listings_anon_select ← 번호 없이 재적용
```

### 원격 이력의 정체 — 이것이 이 스토리의 핵심 인사이트

레포 파일 목록과 원격 이력이 **1:1로 일치하지 않는다.** 처음 보면 "드리프트 사고"로 읽히지만 **아니다. 의도된 패턴이고, 마이그 자신의 주석이 자백한다:**

- `0002b`: *"0002_listings.sql 파일과 동일 정의로 동기화"*
- `0003b`: *"**0003_chat.sql 본문도 동일하게 갱신됨(신규 환경 재생성 시 한 번에 생성). 기존 원격은 이 0003b로 따라잡는다.**"*
- `0003c_revoke_trigger_execute`: *"파일 `0003c_chat_room_integrity.sql`에 이미 인라인 포함됨 — 단일 출처"*

즉 이 프로젝트의 실제 규약은:

> **레포 파일 = 신규 환경(fresh DB)의 정본이자 단일 출처.** 정본 파일은 코드리뷰 지적이 나오면 **in-place로 수정**된다.
> **원격 전용 접미사 패치 = 이미 살아있는 DB만 정본을 따라잡게 하는 멱등 패치.** 신규 환경엔 불필요하므로 파일로 남기지 않는다.

**세 가지 귀결(전부 게이트 설계를 규정한다):**

1. **게이트의 대상은 레포 파일뿐**이다. 원격 이력은 대상이 아니다 — 파일 없는 5건은 결함이 아니다.
2. **fresh-DB 검사는 정확히 옳은 검사다.** 레포 파일이 신규 환경 정본이라고 규약이 선언했으므로, "레포 파일만으로 빈 DB가 서는가"가 곧 그 선언의 검증이다.
3. **게이트가 증명하지 *못하는* 것**: "fresh DB == 살아있는 원격 DB". 정본 in-place 수정 + 따라잡기 패치 방식은 이 등가를 **사람의 성실성에 의존**한다. 런북에 이 사각지대를 **적어라**. 게이트가 다 막아준다고 착각시키는 게 더 위험하다.

`listings_anon_select`(번호 없는 재적용)는 8.5에서 AC 개정으로 0011 내용을 고쳐 다시 적용하며 `name`에 번호를 빠뜨린 것이다. **이름 규약 위반이지 기능 문제 아님** — 런북의 "적용 시 name은 파일명 stem 그대로" 항목의 실제 사례로 인용하라.

### 프렐류드 계약면 (Task 2의 정확한 범위)

마이그레이션 전수 조사 결과, Supabase 플랫폼 의존 표면은 **작고 경계가 뚜렷하다**(추측 아님 — grep 실측):

| 필요한 것 | 쓰는 곳 | 프렐류드가 만들 것 |
|---|---|---|
| `auth` 스키마 | 0001 | `create schema auth` |
| `auth.users` | 0001 (FK + 가입 트리거) | `id uuid pk`, `email text`, `raw_user_meta_data jsonb` — **트리거가 읽는 컬럼만** |
| `auth.uid()` | 0001 RLS | 스텁 함수(`current_setting('request.jwt.claim.sub', true)::uuid`) |
| 롤 `anon`·`authenticated` | 0001·0002·0003c·0007~0009·0011 | `create role ... nologin` |
| 롤 `postgres` | 0006 (`grant ai_readonly to postgres`) | 컨테이너 기본 슈퍼유저가 `postgres` — 그대로 씀 |
| `vector` 확장 | 0002·0004 | 이미지에 포함(`create extension if not exists vector`는 마이그가 자체 수행) |
| **플랫폼 기본 GRANT** | ⚠️ 아래 별항 | **실측값 그대로** — 아래 별항의 SQL을 **추측으로 고쳐 쓰지 말 것** |

**`service_role`은 쓰이지 않는다**(규칙 6 — service_role 키 금지와 정합). 만들지 마라.

**⚠️ 플랫폼 기본 GRANT — 이 스토리에서 가장 오해하기 쉬운 대목. 실측했으니 그대로 따르라.**

조사 결과 **`grant select on public.listings to authenticated`가 어느 마이그에도 없다.** profiles·chat_rooms·chat_messages도 마찬가지다. 즉 **authenticated 데이터 경로 전체가 Supabase 플랫폼 기본 권한에 암묵 의존한다**(0011이 `anon`+`listings`에 대해서만 명시 GRANT/REVOKE로 그 의존을 끊었다 — 8.5의 성과).

**그래서 fresh DB에서 authenticated가 못 읽는가? 아니다 — 잘 읽는다.** 프렐류드가 그 자동 발급을 재현하기 때문이다. 2026-07-14 도커 실측:

```
authenticated_listings_읽기 | anon_listings_읽기 | anon_embedding_읽기
 t                          | t                  | f
set role authenticated; select count(*) from listings;  →  성공
```

**이 문단이 존재하는 이유**: 설계 토론에서 *"게이트가 초록이어도 그 fresh DB는 authenticated가 listings를 못 읽는다"* 는 주장이 나왔고 그럴듯했다. **실측하니 거짓이었다.** 같은 논증을 다시 만들어 프렐류드를 뜯어고치지 마라 — 재고 싶으면 위 명령을 다시 돌려라.

**프렐류드에 쓸 정확한 SQL (실측값 — 추측으로 바꾸지 말 것):**

```sql
-- 2026-07-14 운영 Supabase 실측(pg_default_acl). 아래는 그 값의 재현이지 추정이 아니다.
--   원본: postgres 롤의 기본권한 = {anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm, ai_readonly=r}
--   (arwdDxtm = insert·select·update·delete·truncate·references·trigger·maintain)
--   ai_readonly=r은 0006이 만든 것이므로 프렐류드가 아니라 마이그의 몫 — 여기 넣지 마라.
alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;
```

- **왜 `select,insert,update,delete` 4종이 아니라 `all`인가**: 앱이 쓰는 건 4종뿐이라 4종으로도 돈다. 그러나 그건 **우리 추측이 실제와 다른 상태**를 만든다 — 실제 Supabase는 8종을 준다. 프렐류드의 값어치는 "실제 플랫폼을 얼마나 정직하게 재현하는가"에서 나온다. **추측을 줄이는 게 공짜면 줄인다.**
- **`service_role`은 프렐류드에만 등장하고 마이그는 안 쓴다**(규칙 6 — service_role 키 금지). 실측 재현이라 넣을 뿐, 이걸 근거로 마이그에서 service_role을 쓰지 마라.

**self-contained의 확정 정의**(이 프렐류드가 그 기준선이다):
> **선언된 프렐류드 계약면 + 자기보다 앞 번호 마이그레이션, 이 둘만으로 성립하는가.**

이 정의는 실제로 문다 — 프렐류드에 없고 앞 마이그도 안 만든 것에 기대면 apply가 깨진다(Task 5 red 4가 증명, `0004` 천연 red가 실증).

**게이트가 증명하는 것과 안 하는 것(AC 6 — 정확히 이 문장을 런북에 옮겨라):**
- ✅ 증명함: **"마이그 + 선언된 Supabase 계약면 = 도는 DB"** → 재해 복구(새 Supabase 프로젝트를 파면 플랫폼이 같은 기본 GRANT를 준다)와 납품(Supabase 전제)에 **충분하다.**
- ❌ 증명 안 함: **"마이그만으로 = 도는 DB"**. 출입증 발급이 마이그가 아니라 **프렐류드/플랫폼**에 있다. 그래서 **자체 호스팅·타 클라우드의 맨 Postgres로는 이 레포만으로 못 선다.**
- 이 간극을 메우려면 각 테이블 마이그에 명시 GRANT를 넣고 프렐류드에서 위 한 줄을 지우면 된다 — **일부러 안 한다**(사용자 확정 2026-07-14: **Supabase 전제 · 납품 계획 없음**). 없는 시나리오를 위해 짓지 않는다(A2).

`alter default privileges`는 **그 문을 실행한 롤이 만든 테이블에만** 적용된다(이미 물린 적 있음 — `deferred-work.md:81`이 0006에서 같은 함정을 기록). 프렐류드와 마이그를 **같은 롤(`postgres`)로** 실행하면 성립한다. 다른 롤로 나눠 실행하지 마라.

### DDL 성공 ≠ 동작 정상 (권한 프로브가 필요한 이유)

**"apply가 성공했다"는 생각보다 훨씬 약한 보증이다.** 마이그가 `create policy`만 하고 테이블 GRANT가 없어도 **DDL은 멀쩡히 성공한다** — 정책은 만들어지고, 권한은 없고, 아무도 안 죽는다. 런타임에 anon이 403을 맞을 뿐이다.

그래서 apply-성공만으로는 AC 2의 "비-self-contained를 실패로 잡는다"를 **충족 못 한다**. post-apply 프로브 3건이 그 구멍을 메운다. **카탈로그 조회라 시드 데이터도 행도 필요 없다** — 싸고 정확하다.

프로브를 3건 이상으로 늘리지 마라(A2). 목적은 **대표 증인**이지 RLS 전수 검증이 아니다 — 그건 8.5가 이미 실 DB에서 했다. 다만 **3건이 서로 다른 축이어야** 값을 한다(컬럼 GRANT·컬럼 차단·RLS 정책). 3건을 전부 GRANT 축에 몰면, 정작 이 레포가 두 번 경고한 함정(*"GRANT만으론 행이 안 보인다 — 정책 필수"*)을 하나도 못 본다. Task 3의 프로브 명세와 두 개의 ⚠️를 그대로 따르라 — 둘 다 실측으로 확인된 함정이다.

### 왜 psycopg가 아니라 컨테이너 안 psql인가

`api/`가 `psycopg[binary]`를 갖고 있으니 그걸 쓰고 싶어질 것이다. **쓰지 마라:**
- 이 체크는 **레포 차원**(supabase/) 관심사지 api 관심사가 아니다. api venv에 묶으면 "api 설치해야 db 체크가 돈다"가 된다.
- SQL을 `docker exec -i <c> psql -v ON_ERROR_STOP=1 -f -`로 흘리면 **드라이버가 아예 필요 없다.** `psql`은 이미 이미지 안에 있다. `ON_ERROR_STOP=1`이 첫 에러에서 비-0 종료 → 파이썬은 종료코드만 본다.
- 결과: `scripts/check_migrations.py`는 **stdlib만으로 어디서나 돈다.** 새 의존성 0개 → **GitHub Actions 잡이 3스텝으로 끝나고**(Task 3b), 로컬과 CI가 **같은 명령**을 쓴다. 이게 "로컬에선 되는데 CI에선"을 원천 차단한다.

로컬 `psql`은 이 PC에 **없다**(실측). 컨테이너 안 것을 쓴다.

### 도커 환경 (실측 확인됨)

- `docker 29.5.3` **있음**. `supabase` CLI **없음**. 로컬 `psql` **없음**. `python 3.11.6` · `node v24.15.0` 있음.
- 이미지 **`pgvector/pgvector:pg17`** — 원격 매니페스트 존재 확인함. 원격 Supabase가 **PostgreSQL 17.6**(실측)이므로 **pg17로 맞춘다**. pg15/pg16 쓰지 마라(버전 차이로 나는 red는 가짜 red다).
- 컨테이너는 `POSTGRES_PASSWORD` 주고 임시 이름으로 띄운 뒤 **반드시 `finally`에서 `docker rm -f`**. 이 레포는 이미 dev 서버 좀비 프로세스로 데인 적이 있다(`web-dev-server-cleanup` 메모) — 같은 실수를 컨테이너로 반복하지 마라.
- 기동 대기는 `sleep` 고정값 말고 **`pg_isready` 폴링 + 타임아웃**.

### out-of-order를 git diff로 잡으려 하지 마라

"out-of-order(번호를 뒤로 끼워넣기)"를 잡으려고 git 이력을 뒤지고 싶어질 것이다. **불필요하다 — 밀집+유일 검사가 이미 함의한다:**

> 번호가 0001~max로 **빈틈없이 밀집**하고 **바닥번호가 유일**하면, 새로 추가되는 맨번호는 `max+1`이거나(정상) **중복이다**(검출). 뒤로 끼워넣을 자리가 구조적으로 없다.

접미사 파일(`0011b_...`)을 프론티어 뒤에 붙이는 건 **정상**이다 — 그게 따라잡기 패치 규약이다. 실패로 처리하지 마라.

참고: **실제 적용 이력은 이미 번호순이 아니다**(0006→0004→0003→0005, 위 표). 헤더 주석이 *"번호 갭 의도됨"* 이라 밝히며 자리를 예약해 뒀고 나중에 채워졌다. 이건 **과거의 사실**이지 지금 고칠 대상이 아니다. 게이트는 **번호순 적용이 성립하는가**를 보지, 과거에 어떤 순서로 적용했는가를 보지 않는다. **단, 그 "성립"은 지금 거짓이다 — 아래 "0004 문제"를 반드시 먼저 읽어라.**

### 0004 문제 — 게이트가 첫 실행에서 잡을 실재 결함 (도커로 재현 확인함)

**번호순 적용은 현재 상태로 성립하지 않는다.** 스토리 명세대로 프렐류드를 만들고 pg17에 번호순 적용하면 실제로 이렇게 죽는다:

```
>>> 0004_guide_documents.sql : FAIL
psql:<stdin>:44: ERROR:  role "ai_readonly" does not exist
```

- `0004:44` `grant select on public.guide_documents to ai_readonly;` + `0004:48-49` `create policy ... to ai_readonly`
- 그런데 `create role ai_readonly`는 **0006에만** 있다(`0006:22-26`, 전수 grep으로 유일).
- **즉 0004는 자기보다 뒤 번호인 0006의 상태를 가정한다** — 이 스토리가 정의한 self-contained("프렐류드 계약면 + **앞** 번호 마이그만으로 성립")의 정면 위반이다.

**이건 사고가 아니라 의도였다.** 두 파일이 자백한다:
- `0004:2-3`: *"적용 순서: 0001 → 0002 → 0004 → **0006(이미 적용)**"* / *"⚠️ **0006(읽기전용 롤) 적용 후이므로**"*
- `0006:18-20`: *"번호 갭 메모: 0003·0004·0005는 아직 미생성. **0006은 현재 존재하는 테이블에만 의존하므로 먼저 적용 가능.**"*

원격 이력이 이를 확증한다(0006 → 0004 순으로 적용됨). **즉 "번호순 = 적용순"은 이 레포에서 애초에 참이 아니었고, 아무도 몰랐다.** 이 스토리가 그걸 강제로 참으로 만든다.

**처리(결정됨 — AC 5의 예외 1건)**: `0004`에 `0006:22-26`의 **멱등 DO 블록을 그대로 복사**해 롤 생성 가드를 넣는다(Task 5). 왜 이게 안전한가:
- **fresh DB 번호순**: 0004가 롤을 만든다 → 0006의 DO 블록은 이미 있는 롤을 만나 **no-op** → 양쪽 통과.
- **원격(살아있는 DB)**: `ai_readonly`가 이미 존재 → 재적용해도 no-op → **따라잡기 패치조차 불필요.** 원격은 손대지 않는다.
- **규약 정합**: 정본 파일 in-place 수정 = 이 레포가 이미 쓰는 방식(`0002b`·`0003b`가 그 산물). 새 마이그 추가 아님 → 원장 0012~0019 불변.
- **패턴 재발명 금지**: 새 가드를 짜지 마라. 0006의 DO 블록이 이미 정답이고, 복사가 곧 일관성이다.

**0004 말고 다른 위반이 더 있는지는 게이트가 답한다** — 손으로 찾지 말고 돌려라. 나오면 같은 판단 틀(멱등 가드 + 원격 no-op 확인)을 적용하되, **원격에 no-op이 아닌 수정이 필요해지면 멈추고 사용자에게 보고하라**(공유 운영 DB다).

### 런북에 반드시 들어갈 것 (Task 4 목차)

1. **배포 타깃·트리거**: web=Vercel(`develop` push→preview, `main`→운영 `bmad-encar-demo.vercel.app`) · api=Cloud Run 서울(`encar-ai-api-dev`/`encar-ai-api`, `api/Dockerfile`) · db=Supabase 단일 프로젝트 · app=Flutter **수동**. **B3: 수동 배포 명령을 직접 치지 않는다**(Git 연동 자동 배포).
2. **⚠️ 단일 공유 Supabase**: dev·preview·운영이 **DB 하나**를 공유. 마이그 적용 = 운영 즉시 반영. → **db 마이그는 항상 additive·nullable**이어야 하고, 그래서 db가 순서 맨 앞이다.
3. **배포 순서 db→api→web→app + 각 단계의 "왜"**: 새 필드를 읽는 쪽(api·web)보다 **만드는 쪽(db)이 먼저**여야 한다. 반대면 api가 없는 컬럼을 읽고 500.
4. **부분배포 정합성 표**: `db신/api구/web구`(additive라 무영향 — 8.5 실증) · `db신/api신/web구`(web은 신규 필드를 모르므로 무시 → nullable 계약이 이걸 보장) · `db구/api신/web신`(❌ 금지 — 순서 위반).
5. **역순 롤백 web→api→db**: web=Vercel Instant Rollback · api=Cloud Run 이전 리비전으로 트래픽 이전 · **db=역마이그 없음**(아래 6).
6. **⚠️ db 롤백은 존재하지 않는다**: forward-only. 전략은 "additive만 해서 롤백이 필요 없게 만든다". 정 필요하면 **보상 마이그(전진)**. **`drop` 치지 마라** — 공유 DB라 운영이 죽는다.
7. **마이그 적용 절차**: Supabase MCP `apply_migration`, `name` = **파일명 stem 그대로**(`0012_listing_images`). CLI(`supabase db push`) 아님 — 이 프로젝트엔 CLI도 `config.toml`도 없다. **적용 전 `python scripts/check_migrations.py` 통과 필수.** 접미사 따라잡기 패치 규약도 여기 적는다.
8. **게이트의 사각지대(정직하게 — AC 6)**: ① **초록 = "마이그 + 선언된 Supabase 계약면 = 도는 DB"이지 "마이그만으로"가 아니다** — 맨 Postgres로는 못 선다(Supabase 전제라 오늘은 무해) ② fresh DB == 운영 DB를 보증하지 **않는다**(정본 in-place 수정 규약의 대가) ③ 프렐류드가 선언한 것에 대한 의존은 설계상 안 잡힌다 ④ 정적 층만 돈 경우(도커 없음)는 통과가 아니다.
   > **왜 이 절이 필수인가**: 게이트 옆에 "이 게이트는 X를 안 본다"가 붙어 있어야 다음 사람이 초록불을 오해하지 않는다. **단, 사각지대를 적을 땐 그것도 실측해서 적어라** — 이 절의 초안은 실측 안 된 추측("authenticated가 못 읽는다")을 담았다가 도커 실측으로 뒤집혔다.

### 배포·브랜치 (B3)

`develop`에서 작업·커밋 → 동작 확인. **이 스토리는 마이그·런타임 코드를 바꾸지 않으므로**(문서+스크립트) 배포 순서 자체가 무관하다 — 그럼에도 런북이 서술하는 순서가 실제와 맞는지는 Task 7에서 관찰로 확인한다. `main` 병합은 사용자 승인 시에만.

### 이전 스토리 학습 (8.5에서 이어짐)

- **8.5가 이 스토리를 직접 호출했다**: *"`grant select on listings to anon`이 **어느 마이그레이션에도 없어** 플랫폼 기본 GRANT에 암묵 의존한다 → **8.6 self-contained CI 게이트에 걸릴 소지**"*(8.5 Task 1). 8.5는 `listings`/`anon`에 대해서만 이를 끊었다. **나머지(authenticated 전 경로)는 여전히 열려 있고, 위 "플랫폼 기본 GRANT" 별항이 그 처리를 확정한다.**
- **8.5가 AC 3을 이미 갱신했다**: *"8.6 AC의 '0011~0018 확정'은 원장에서 '0011~0019'로 갱신됨"*. Task 6에서 **재작성 말고 대조만** 하라는 이유다.
- **계보 끊김이 진짜 결함**(8.5 최대 교훈): PRD 각주가 아키텍처→에픽→스토리로 전파되지 않아 결함이 구현까지 통과했다. **이 스토리의 산출물(런북·규약)이 정확히 그 계보를 잇는 장치다** — 지금 암묵지로만 존재하는 규약(접미사 패치·MCP 적용·단일 공유 DB)을 문서로 못박지 않으면 다음 사람이 같은 방식으로 흘린다. 런북은 형식 요건이 아니라 **이 교훈의 실행**이다.
- **방어선을 일부러 무너뜨려 red를 확인하는 습관**(8.5·8.4 공통): AC 4가 이 습관의 계승이다. 8.5는 의존성을 되돌려 *"정확히 3건이 `assert 401 == 200`으로 실패"* 를 실측했다. 같은 수준으로 하라.
- **B7 모델 분리**: 8.5 배포본 E2E는 *"설계=opus, 수행=sonnet"* 으로 돌렸다. 이 스토리도 스크립트 실작성·실행은 sonnet 급으로 충분하다.

### 테스트 표준 (규칙 12 층별)

이 스토리는 web/api/app **어느 층도 아니다** — DB·배포 도구 층이다. 그래서 Vitest도 pytest도 아니고 **스크립트 자체가 테스트**다. 검증 = **직접 실행·관찰**(B4): 체크 스크립트를 돌려 통과를 보고, 위반을 심어 실패를 본다(AC 4). **"작성했다"로 완료 보고하지 마라 — 출력이 증거다.**

### 이 스토리가 남기는 교훈 (Epic 8 회고 재료 — 삭제 금지)

이 스토리는 **한 줄도 구현되기 전에** 설계 단계에서만 결함 3종이 나왔다. 회고에서 쓸 수 있게 사실로 남긴다.

1. **"불변식을 요구하기 전에, 그게 이미 깨져 있는지 실측하라."** 에픽에 *"번호순=적용순=개발순이 강제"* 라고 박혔지만(Amelia 명의) **그 전제는 이미 거짓이었다** — 0004가 0006을 가정한 채 1년 가까이 돌고 있었다. 그를 탓할 수 없는 게, 반증은 `0004` 4번째 줄에 있었고 그건 에픽 작성자의 시야 밖이었다. **측정 도구(게이트)가 없어서 게이트의 전제를 검증 못 한 순환.** → 규칙을 **선언**하기 전에 **측정**한다.

2. **계보 끊김의 역방향.** 8.5는 위(PRD 각주)에서 아래로 안 흘러 터졌고, 이번엔 **아래(SQL 주석)에서 위로 안 올라가** 터졌다. 같은 병의 두 증상이다 — **제약이 사는 정본 위치가 없다.** 정보는 있었고 정확했는데 **아무도 그걸 찾을 의무가 없었다.** 그런 정보는 문서화된 게 아니라 **매설된** 것이다. → `docs/conventions.md`가 그 정본 위치이고, Task 6이 그걸 집행한다. Mary의 한 줄이 이 사건의 최대 증거다: ***"그게 문서에 있었으면 이번 안건은 애초에 안건이 아니었다."***

3. **⭐ 실측 없는 그럴듯한 논증이 party-mode도 통과했다.** *"게이트가 초록이어도 authenticated가 못 읽는다"* 는 주장이 가장 무서운 발견으로 채택돼 AC·Task·런북·메모리에까지 박혔다가, **도커 실측 한 번에 거짓으로 판명**됐다. 논증은 정연했고(GRANT가 마이그에 없다 → 참), 결론만 틀렸다(프렐류드가 그걸 선언한다 → 놓침). 8.5의 교훈 *"'안전한가?'를 물을 땐 어느 축의 안전인지 명시하라"* 를 **그대로 반복한 것**이다. → **"이 프로젝트에서 세 번째 반복"이라고 경고한 그 문장 자체가 네 번째 반복이었다.** 무서운 발견일수록 재라.

4. **주석은 계약이 아니다.** `0004:2-3`의 *"적용 순서: 0001 → 0002 → 0004 → 0006"* 은 **실행되지 않는 배포 절차서**였다. 실행되는 것(SQL 가드)으로 승격시키기 전까진 아무것도 지키지 못한다.

### Project Structure Notes

- `scripts/`엔 이미 `check-embedding-dim.ps1`(1회성 점검)이 있다. **같은 자리, 같은 성격**(레포 차원 점검 도구)이라 여기 둔다. 파일명은 파이썬 관례대로 언더스코어(`check_migrations.py`) — ps1의 하이픈은 PowerShell 관례다. 섞이는 게 아니라 각 언어 관례를 따르는 것.
- 마이그레이션 규칙 10(RLS 동거·번호순 전진) 유지. UI 문자열·출력은 **한국어**.
- 신규 npm/pip 의존성 **0개**가 목표다. 추가하고 싶어지면 그 전에 왜 stdlib으로 안 되는지 답하라.

### References

- 스토리 원문 AC — [Source: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:420-432`]
- 마이그레이션 원장(정본, 0011~0019) — [Source: `epics-increment-2026-07-12.md:252-268`]
- AC-DEPLOY-1 원문 — [Source: `architecture-increment-2026-07-12.md:78, 122, 207, 334`]
- 마이그 번호 = 논리 라벨 경고 — [Source: `epics-increment-2026-07-12.md:274, 106`]
- 배포 실태(Vercel/Cloud Run/자동배포·운영 URL) — [Source: `docs/learning/00-overview.md:123-136`]
- CI 부재·데모 수준 배포 — [Source: `planning-artifacts/architecture.md:131, 221` — **원본** 파일이지 increment 아님]
- 마이그 적용 = MCP `apply_migration`(CLI 아님) — [Source: `_bmad-output/implementation-artifacts/5-1-chat-스키마-rls.md:69`]
- 로컬 Supabase 스택 없음(`db reset` 불가) — [Source: `supabase/seed.sql:9-11`]
- 따라잡기 패치 규약의 자백 — [Source: `supabase/migrations/` 원격 이력 `0002b`·`0003b`·`0003c_revoke_trigger_execute` 주석(본문 인용)]
- `alter default privileges` 소유자 함정 — [Source: `_bmad-output/implementation-artifacts/deferred-work.md:81`]
- RLS 동거 원칙 — [Source: `planning-artifacts/architecture.md:199` — **원본** 파일]
- 0004의 0006 역참조 자백 — [Source: `supabase/migrations/0004_guide_documents.sql:2-3, 43-49` · `0006_readonly_role.sql:18-20, 22-26, 30`]
- 8.5의 8.6 인계(self-contained·원장 시프트) — [Source: `_bmad-output/implementation-artifacts/8-5-fr58-비로그인-접근-토대.md:31, 42, 44, 193`]
- 8.5 배포·롤백 순서 서술 — [Source: `8-5-...md` §배포·브랜치]
- **party-mode 결정(2026-07-14, Winston·Amelia·John·Mary)** — 안 A(0004 in-place 멱등 가드) 채택 · "레시피 결정" + 근거 3가지 · 불변식 재명명("번호순=적용순" ✗ → "앞 번호까지만 가정") · 판정규칙 (a)/(b)+3조건 · CI=GitHub Actions 신설 · authenticated GRANT는 범위 밖·사각지대 명기. **John의 반대안 D(게이트 폐기)는 "fresh DB 시나리오 없음"을 전제했고, 사용자가 3가지 근거로 그 전제를 반증해 기각됨** — 그 근거가 곧 Story 박스의 "레시피" 이유다.
- 비용=신원 원칙(§8) — [Source: `docs/conventions.md:99-107`]
- 프로젝트 규칙(마이그·RLS·service_role 금지·테스트 층) — [Source: `_bmad-output/project-context.md` 규칙 6·10·11·12]

## Dev Agent Record

### Agent Model Used

Sonnet 5 (project-context 규칙 B7 — 스크립트 실작성·실행은 sonnet 급)

### Debug Log References

**red 1 (천연 — 0004 원래 상태, 수정 전 최초 실행)**:
```
── 동적 검사 (pgvector/pgvector:pg17) ──
[OK] 프렐류드 적용 성공
[OK] 0001_profiles.sql 적용 성공
[OK] 0002_listings.sql 적용 성공
[OK] 0003_chat.sql 적용 성공
[OK] 0003c_chat_room_integrity.sql 적용 성공
[FAIL] 0004_guide_documents.sql :
CREATE EXTENSION
CREATE TABLE
COMMENT
COMMENT
CREATE INDEX
CREATE INDEX
psql:<stdin>:15: NOTICE:  extension "vector" already exists, skipping
psql:<stdin>:44: ERROR:  role "ai_readonly" does not exist
```
예상과 정확히 일치(Dev Notes "0004 문제" 절 참조).

**green 1 (0004에 0006:22-26 멱등 DO 블록 복사 삽입 후 재실행)**: 0001~0011 전체 통과 + 프로브 3건 전부 통과, 종료코드 0(전체 로그는 아래 "green 최종"과 동일 — 0006도 no-op으로 통과 확인됨).

**red 2 (gap — `0013_zzz_probe.sql` 빈 파일 임시 생성, 현재 max=0011)**:
```
❌ [번호 공백] 0012_*.sql 이 없다 — 정본 마이그 번호는 0001~0013까지 빈틈없이 밀집해야 한다
정적 검사 실패: 1건 위반
```
검증 후 파일 삭제.

**red 3 (중복번호 — `0011_dup_probe.sql` 임시 생성)**:
```
❌ [번호 중복] 0011_* 파일이 2개다: 0011_dup_probe.sql, 0011_listings_anon_select.sql
정적 검사 실패: 1건 위반
```
검증 후 파일 삭제.

**red 4 (계약면 밖 의존 — `0012_probe.sql`에 `grant select on public.listings to undeclared_role;` 임시 생성)**:
```
[OK] 0011_listings_anon_select.sql 적용 성공
[FAIL] 0012_probe.sql :
psql:<stdin>:2: ERROR:  role "undeclared_role" does not exist
동적 검사 실패
```
검증 후 파일 삭제.

**green 최종 (모든 red 프로브 파일 삭제 후 재실행)**:
```
── 정적 검사 (12개 파일) ──
✅ 정적 검사 통과

── 동적 검사 (pgvector/pgvector:pg17) ──
[OK] 프렐류드 적용 성공
[OK] 0001_profiles.sql 적용 성공
[OK] 0002_listings.sql 적용 성공
[OK] 0003_chat.sql 적용 성공
[OK] 0003c_chat_room_integrity.sql 적용 성공
[OK] 0004_guide_documents.sql 적용 성공
[OK] 0005_admin_policies.sql 적용 성공
[OK] 0006_readonly_role.sql 적용 성공
[OK] 0007_listings_seller_name.sql 적용 성공
[OK] 0008_chat_room_names.sql 적용 성공
[OK] 0009_profiles_name.sql 적용 성공
[OK] 0010_chat_message_length.sql 적용 성공
[OK] 0011_listings_anon_select.sql 적용 성공
[OK] 프로브 ① 컬럼 GRANT 축: anon이 listings 일부 컬럼을 읽을 수 있다 — 't' 확인
[OK] 프로브 ② 컬럼 차단 축: anon이 listings.embedding은 못 읽는다 — 'f' 확인
[OK] 프로브 ③ RLS 정책 축: guide_documents_ai_readonly_select 정책이 존재한다 — 't' 확인

✅ 동적 검사 통과
=== 마이그레이션 게이트 통과 ===
```

### Completion Notes List

- **Task 1**: 원격 `list_migrations` 실측이 스토리 작성 시점 표와 완전히 일치(변동 없음) — 3가지 사실(파일 없는 5건·적용순 역전·번호 없는 재적용) 전부 재확인.
- **Task 2**: `scripts/migration-check-prelude.sql` 신규 작성. Dev Notes의 실측 SQL(auth 스키마·auth.users·auth.uid() 스텁·anon/authenticated/service_role 롤·`alter default privileges ... grant all`)을 그대로 반영, 추측 없음. ai_readonly·vector 확장은 마이그 자체가 만들므로 프렐류드에 넣지 않음(최소성).
- **Task 3**: `scripts/check_migrations.py` 신규 작성(stdlib only). 정적 4종 + 동적(도커 pg17, `--single-transaction -v ON_ERROR_STOP=1` + 첫 실패 즉시 중단) + 프로브 3건(`has_any_column_privilege`·`has_column_privilege`·`pg_policies`, Dev Notes의 두 함정 회피 그대로 구현). Windows 로컬 실행 시 cp949 인코딩 문제 2건 발견해 수정(`sys.stdout.reconfigure(encoding="utf-8")`, `subprocess.run(..., encoding="utf-8")`) — CI(ubuntu, UTF-8 로케일)에는 영향 없는 로컬 전용 이슈였음.
- **Task 3b**: `.github/workflows/migration-gate.yml` 신규(레포 최초 CI). `actions/checkout@v7`·`actions/setup-python@v6`(2026-07 시점 최신 안정, WebSearch로 확인) 3스텝. paths 필터로 무관 push 노이즈 차단.
- **Task 4**: `docs/deployment-runbook.md` 신규, Dev Notes 목차 8개 항목 전부 반영. `docs/conventions.md`·`docs/tech-debt.md`에 링크 1줄씩 추가(내용 복제 없음).
- **Task 5**: red 1(천연)~red 4 전부 실제 도커 재현 후 원문을 위 Debug Log에 기록. `0004_guide_documents.sql`에 `0006:22-26`과 동일한 멱등 DO 블록 복사 삽입(새 패턴 발명 없음) — green 1에서 0004·0006 양쪽 통과 확인(0006 쪽은 no-op). 원격은 `ai_readonly`가 이미 존재하므로 **재적용/따라잡기 패치 불필요**로 판단(판정규칙 (a) 3조건 전부 충족 — 멱등 가드 추가만·원격 델타 0·기존 객체 정의 불변) → dev 자율 처리, 원격 건드리지 않음. `0004:2-3`·`0006:18-20` 주석을 "과거 사실 기록"으로 갱신.
- **Task 6**: 원장 표(epics-increment-2026-07-12.md:258-266)는 이미 8.5가 0011~0019로 정본화 완료 — 대조만 하고 재작성 안 함. 같은 파일 106행의 예시(role=0018, wishlists=0013)만 시프트 반영해 정정(role=0019, wishlists=0014). `docs/conventions.md`에 §9(마이그레이션 정책: 파일명 규약·판정규칙·"레시피" 결정+근거 3가지·불변식 재명명) 신규 절 추가.
- **Task 6b**: 게이트 사각지대 3항목을 런북 §8에 그대로 반영(반증된 "authenticated가 못 읽는다" 주장은 되살리지 않음). `docs/tech-debt.md`에 신규 항목 #18(테이블 GRANT 플랫폼 의존) 박제 — 8.5가 우연히 발견한 사실 포함.
- **Task 7**: 로컬 게이트 최종 통과 출력 캡처(위 "green 최종"). GitHub Actions push 확인·배포 순서 실측 관찰은 아래 Change Log에 기록.

### File List

- `scripts/migration-check-prelude.sql` (신규)
- `scripts/check_migrations.py` (신규)
- `.github/workflows/migration-gate.yml` (신규)
- `docs/deployment-runbook.md` (신규)
- `docs/conventions.md` (수정 — §9 마이그레이션 정책 절 추가 + 런북 링크)
- `docs/tech-debt.md` (수정 — 항목 #18 추가 + 런북 링크)
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` (수정 — 106행 예시 시프트 정정)
- `supabase/migrations/0004_guide_documents.sql` (수정 — ai_readonly 멱등 생성 가드 삽입 + 주석 갱신)
- `supabase/migrations/0006_readonly_role.sql` (수정 — 번호 갭 주석을 과거 사실 기록으로 갱신)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (수정 — 8.6 상태 갱신)

### Change Log

| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-07-14 | 스토리 생성(ready-for-dev) | epics 8.6 AC + 원격 이력·도커·GRANT 실측 조사 |
| 2026-07-14 | **party-mode 결정 반영(사용자 확정)** — ① **안 A 채택**(0004 in-place 멱등 가드, 원격 델타 0) ② **"레시피 결정" + 근거 3가지**를 Story 박스에 명문화(John의 안 D 기각 근거) ③ **불변식 재명명** — "번호순=적용순=개발순"은 과했고 실측으로 반증됨(Amelia 부분 철회) → "앞 번호까지만 가정"(번호 갭 무죄·역방향 의존만 유죄) ④ **AC 2에 GitHub Actions 신설 확정** — `.github/workflows/migration-gate.yml`(Task 3b 신설). *"사람이 기억해야 도는 체크는 6개월 뒤 안 돈다"*(Winston) ⑤ **AC 6 신설** — 게이트 사각지대 명기(Task 6b), authenticated GRANT 부재는 범위 밖·tech-debt 박제 ⑥ **판정규칙 (a)/(b)+3조건 승인** — 틀 안이면 dev 자율, 원격 따라잡기 패치 필요 시만 에스컬레이션 ⑦ **암묵 규약 정본 승격**(Mary: *"그게 문서에 있었으면 이번 안건은 애초에 안건이 아니었다"*) ⑧ 0004:2-3·0006:18-20 주석을 사실 기록으로 갱신(주석은 계약이 아니다) |
| 2026-07-14 | 독립 검증(깨끗한 컨텍스트·opus) 반영 — 치명 2·중요 4·사소 2 정정 | 검증자가 도커로 실제 재현. ① **0004→0006 역참조로 번호순 적용이 실제 실패** → AC 5에 in-place 예외 + "0004 문제" 절 + Task 5 재설계(천연 red 채택) ② **프로브 ①이 가짜 red**(`has_table_privilege`는 0011 컬럼 스코프 때문에 false가 정답) → `has_any_column_privilege`로 교체 ③ 프로브 3건이 전부 GRANT 축이라 정책 함정을 못 봄 → ③을 `pg_policies` 축으로 교체 ④ `--single-transaction`+첫 실패 중단 누락 → 게이트가 거짓 출력 ⑤ red 3(프렐류드 롤 제거)이 자기정합만 증명 → 미선언 롤 의존으로 교체 ⑥ `architecture.md` 원본/increment 혼동 표기 ⑦ 원장 106행 시프트 미반영 |
| 2026-07-15 | **구현 완료(review)** — 프렐류드·게이트 스크립트·GH Actions·런북 신규 산출, 0004 in-place 수정(red→green 실증 4종), conventions.md §9·tech-debt.md #18 신규, 원장 106행 정정. 로컬 게이트 실행 최종 통과(0건 위반) | Task 1~7 전체 구현 + 직접 실행·관찰(B4) |
