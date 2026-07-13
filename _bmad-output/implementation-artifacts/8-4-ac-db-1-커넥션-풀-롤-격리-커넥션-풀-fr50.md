# Story 8.4: AC-DB-1 커넥션 풀 롤 격리 + 커넥션 풀(FR50)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a AI 검색 사용자,
I want AI가 DB를 읽을 때 안전하고 빠르게 처리되길,
so that 부하 상황에서도 권한 누수 없이 안정적으로 검색된다.

> **이 스토리의 성격 (개발자 필독):** 증분(Epic 8~16)의 **기술 파운데이션**이자 **RAG(Epic 13) 선행 디리스크** 스토리다. 기존 Epic 4 AI API의 DB 접근 레이어(`api/app/db/readonly.py`) **딱 한 파일을 수술**해, 트랜잭션 풀러(:6543) 커넥션을 재사용해도 `ai_readonly` 롤이 다음 요청으로 새지 않도록 **트랜잭션 스코프로 격리**한다. 여기서 롤 격리를 안 세우면 Epic 13의 하이브리드 SQL이 롤 누수·sold 우회 위험에 노출된다(그래서 RAG보다 먼저 한다). RAG 신규 로직과 **완전히 독립**이라 red→green으로 조기 검증 가능하다. **A3 외과적 변경**: 손대는 곳은 `readonly.py`(본체) + 그 테스트 + 의존성/설정 주석뿐이다 — 4분기 라우팅·sql_guard·그래프 노드·스키마는 **범위 밖**이다.

## Acceptance Criteria

원문(`epics-increment-2026-07-12.md` Story 8.4, 383~397행) BDD:

**Given** 트랜잭션 풀러(:6543)를 통한 AI 읽기 경로
**When** AI 검색이 DB를 읽으면

1. **(AC-DB-1 트랜잭션 롤 격리)** 매 쿼리를 `BEGIN; SET LOCAL ROLE ai_readonly; <SELECT>; COMMIT;` 으로 감싸 실행하고 **세션 레벨 `SET ROLE`을 쓰지 않는다**. (`SET LOCAL`은 트랜잭션이 끝나면 롤이 자동 원복 → 물리 커넥션이 풀로 반납될 때 깨끗함)
2. **(누수 부재 증명 — red→green)** 동일 물리 커넥션을 재사용하는 연속/동시 2요청에서 **2번째 요청의 실행 롤이 직전 `ai_readonly`로 새지 않음**을 증명하는 테스트가 통과한다. 세션 `SET ROLE`이면 실패(red), `SET LOCAL`이면 통과(green)여야 한다.
3. **(FR50/NFR8 — 풀·타임아웃·논블로킹)** 커넥션 풀 + `connect_timeout` + async 논블로킹이 도입된다. (구체 형태는 Dev Notes "핵심 설계 결정 ①②③" 권고안을 따른다)
4. **(I1 — 기존 결정 대체 + 주석 갱신)** `readonly.py`의 기존 `:5432 세션 풀러 + 세션 SET ROLE + autocommit` 결정이 `:6543 트랜잭션 풀러 + SET LOCAL + 풀` 방식으로 대체되고, 모듈 docstring·관련 주석(`config.py`의 "Session pooler 문자열")이 새 방식으로 갱신된다.
5. **(회귀 0 — 조기 디리스크)** 이 변경이 기존 Epic 4 AI 검색(경로 A `sql_rag_node`·경로 B `doc_rag_node`)을 깨지 않음을 회귀로 확인한다. **`run_select(query, params=None) -> list[tuple]` 공개 시그니처는 절대 바꾸지 않는다**(4개 테스트가 monkeypatch로 의존 — 아래 "하드 제약").

## Tasks / Subtasks

- [x] **Task 1 — 의존성 추가: psycopg 커넥션 풀 (AC: 3)**
  - [x] `api/pyproject.toml`과 `api/requirements.txt` 두 곳의 `psycopg[binary]` → **`psycopg[binary,pool]`** 로 확장(`psycopg_pool` 패키지 포함). 둘 다 고쳐야 배포(Cloud Run, requirements 기준)와 로컬(pyproject)이 일치한다.
  - [x] `api/`에서 `pip install -e .` (또는 `pip install "psycopg[binary,pool]"`)로 설치 확인 → `python -c "import psycopg_pool; print(psycopg_pool.__version__)"` 성공(3.3.1).

- [x] **Task 2 — `readonly.py` 재구현: 지연 초기화 풀 + 트랜잭션 격리 (AC: 1, 3, 4, 5)**
  - [x] **모듈 docstring 전면 재작성(I1)**: "세션 풀러(:5432) + 세션 SET ROLE + autocommit" 서술을 **"트랜잭션 풀러(:6543) + 커넥션 풀 + `BEGIN; SET LOCAL ROLE ai_readonly; …; COMMIT;`"** 로 교체. "왜 :6543 + SET LOCAL인가" 문단 명시. FR11(sold는 쿼리가 WHERE로 책임) 경고는 그대로 유지.
  - [x] **지연 싱글턴 풀** 도입: 모듈 전역 `_pool = None`. `_get_pool()`이 최초 호출 시 `require("DATABASE_URL", ...)`로 검증 후 `ConnectionPool(dsn, min_size=1, max_size=8, open=True, kwargs={...})`를 1회 생성해 캐시. import 시점엔 풀을 열지 않음(확인: DATABASE_URL 없이 `from app.db.readonly import run_select` 성공).
  - [x] 풀 `kwargs`에 `connect_timeout=10`과 `prepare_threshold=None`(트랜잭션 풀러 준비문 비활성) 적용.
  - [x] `run_select(query, params=None) -> list[tuple]` **공개 시그니처·반환형 불변** — 내부만 `readonly_connection()`(풀 대여→트랜잭션→SET LOCAL ROLE→yield→트랜잭션 커밋→풀 반납)로 교체.
  - [x] **`readonly_connection()` 유지 + 재작성**: "트랜잭션+SET LOCAL이 이미 적용된 풀 커넥션을 yield"하도록 재작성(제거 대신 유지 — Task 4 라이브 테스트가 계속 이 이름을 사용해 기존 테스트 구조와의 연속성 유지). 세션 SET ROLE + 생 connect 옛 구현은 완전히 제거됨.

- [x] **Task 3 — 엔드포인트 논블로킹화 (AC: 3)**
  - [x] **핵심 설계 결정 ①(권고안 B) 채택**: `api/app/routers/ai.py`의 라우트에서 `result = await asyncio.to_thread(run_search, req.query, req.context)`로 변경. try-except 구조·에러 포맷은 그대로(`to_thread`가 던진 예외는 동일하게 잡힘).
  - [x] `graph.py`·노드는 동기 그대로 둠(변경 없음 — 회귀 표면 최소화).

- [x] **Task 4 — AC-DB-1 누수 부재 테스트 (red→green) (AC: 2, 5)**
  - [x] `api/tests/test_readonly.py`를 **롤 격리 라이브 테스트**로 재작성(기존 SELECT-ok/write-blocked 단언 보존·흡수, `single_connection_pool` fixture로 `min_size=1,max_size=1` 강제).
  - [x] `test_select_ok_and_write_blocked`: SELECT `> 0`행 + INSERT `InsufficientPrivilege` 거부(NFR2) — 통과.
  - [x] `test_role_does_not_leak_across_reused_connection`: 같은 물리 커넥션 재대여 후 `SELECT current_user`가 `ai_readonly`가 아님을 단언 — **red→green 실측 확인**: `SET LOCAL ROLE`→`SET ROLE`로 임시 되돌려 실행하니 실제로 `AssertionError`(누수 발견, red) 확인 → `SET LOCAL ROLE`로 원복 후 재실행해 통과(green) 재확인.
  - [x] **⚠️ 실측 중 발견한 중요 사실(운영 함의)**: red 실험 중 Supabase **Supavisor 트랜잭션 풀러(:6543) 자신도 백엔드 커넥션을 재사용**하며, 세션 `SET ROLE`이 그 백엔드 세션에 눌어붙어 **완전히 새로운 클라이언트 커넥션(우리 앱 풀과 무관)에도 `ai_readonly`가 새는 것을 raw psycopg 커넥션으로 직접 확인**했다(`current_user=ai_readonly, session_user=postgres`). `RESET ROLE`을 여러 백엔드 세션에 걸쳐 실행해 정리 후 baseline(`postgres`)으로 복구, green 재확인함. **이는 AC-DB-1이 막으려는 위험이 우리 앱 풀 안에서뿐 아니라 풀러 계층에서도 실제로 벌어짐을 실측으로 증명** — `SET LOCAL`이 선택이 아니라 필수인 이유의 직접 증거.

- [x] **Task 5 — 회귀 + 라이브 검증 (AC: 5)**
  - [x] **결정론 회귀(무-DB)**: `pytest tests/test_sql_rag_node.py tests/test_doc_rag_node.py tests/test_demo_acceptance.py tests/test_ai_search.py` → 68 passed. 전체 스위트 `pytest tests/` → **165 passed, 3 skipped**(라이브 트랙). `run_select` 시그니처 불변 실증.
  - [x] **라이브 스모크**: Task 4 격리 테스트 통과(green) + Supabase MCP(`execute_sql`, `information_schema.role_table_grants`)로 `ai_readonly`가 5개 테이블(chat_messages·chat_rooms·guide_documents·listings·profiles) 전부 **SELECT만** 보유(INSERT/UPDATE/DELETE 없음) 확인(NFR2 무영향).
  - [x] **엔드투엔드**: 로컬 uvicorn(`:8123`) 기동 → `/health` 200 → buyer@test.com 로그인 토큰으로 `/ai/search` curl 2건 — **경로 A**("3천만원 이하 SUV") 200 + 5건(가격 필터 정확), **경로 B**("가족용 안전한 차") 200 + 5건(의미 검색+가이드 근거). 서버 로그 경고·에러 0. 새 풀+`SET LOCAL`+`asyncio.to_thread` 전체 파이프라인이 실제로 정상 동작함을 실측 확인. 서버 정상 종료·임시 토큰/쿼리 파일 정리 완료.

### Review Findings

- [x] [Review][Patch] 풀 고갈(pool exhaustion) 시 `PoolTimeout`을 잡아 즉시 503+한국어 안내로 실패시킴 [api/app/routers/ai.py, api/app/db/readonly.py] — **적용 완료(2026-07-14)**. `ConnectionPool(..., timeout=5)`로 대여 대기시간을 30초→5초로 단축하고, `routers/ai.py`에 `except PoolTimeout:` 절을 추가해 503(`pool_exhausted`, "지금 사용자가 많아 요청을 처리할 수 없습니다. 잠시 후 다시 시도해주세요.")을 즉시 반환한다. 회귀 확인: `pytest tests/` 165 passed, 3 skipped(변화 없음).
- [x] [Review][Patch] `_get_pool()` 지연 싱글턴 초기화에 락 없음(경합 조건) [api/app/db/readonly.py:37-49] — **적용 완료(2026-07-14)**. `threading.Lock()`으로 더블체크락 적용(`_pool_lock`) — 락 밖에서 1차 확인 후, 락 안에서 재확인하고 없을 때만 `ConnectionPool` 생성. `run_select` 시그니처·동작 불변. 회귀 확인: `pytest tests/test_readonly.py` 2 passed(라이브, 롤 누수 부재 테스트 포함).
- [x] [Review][Defer] `psycopg[binary,pool]` 버전 미고정 [api/pyproject.toml, api/requirements.txt] — deferred, pre-existing 없음(신규 의존성). `ConnectionPool(..., open=True)` 생성자 패턴은 최신 `psycopg_pool`에서 지양되는 추세라, 버전 미고정 상태로는 향후 업그레이드 시 경고/동작 변경 위험. 버전 핀 추가를 고려.
- [x] [Review][Defer] 누수 부재 테스트가 psycopg_pool의 비공식 보장(동일 물리 커넥션 재사용)에 의존 [api/tests/test_readonly.py] — `max_size=1`이 순차 재사용을 강제하긴 하나, 헬스체크 등으로 커넥션이 교체될 가능성은 라이브러리가 공식 보장하는 계약이 아님. 향후 psycopg_pool 내부 동작이 바뀌면 테스트가 잘못된 이유로 통과/flaky해질 수 있음 — 주석으로 전제를 명시하거나 커넥션 identity를 직접 단언하는 보강 고려.
- [x] [Review][Defer] DSN 포트(:6543) 전제가 주석에만 있고 코드로 검증되지 않음 [api/app/db/readonly.py, api/app/config.py] — `.env`가 실수로 :5432(세션 풀러)를 가리켜도 코드가 조용히 그대로 동작함. 다만 `SET LOCAL`은 풀러 종류와 무관하게 Postgres 자체에서 트랜잭션 스코프로 동작하므로 **롤 누수 위험이 재발하지는 않음** — 잃는 건 의도한 성능 특성뿐. 우선순위 낮음.

Dismiss로 처리(노이즈·이미 스토리에서 결정됨, 6건): `routers/ai.py` 수정이 "외과적" 서술과 충돌한다는 지적(Dev Notes 핵심 설계 결정 ①·Task 3가 이미 명시적으로 승인한 변경) · AC3 논블로킹이 진짜 async 풀이 아니라 스레드 오프로드라는 지적(같은 핵심 설계 결정 ①에서 옵션 B로 의도적 채택) · 테스트에서 `run_select`로 INSERT를 실행하는 것(테스트 전용 코드, 기능적으로는 정상) · 풀 크기/타임아웃 하드코딩(Dev Notes가 "데모 규모라 보수적으로"로 명시한 설계 의도와 일치, CLAUDE.md A2 단순함 우선과도 부합) · 모듈 docstring의 "최초 run_select 호출 때" 표현(호출 체인상 정확함) · FR11 sold 필터링이 새 테스트로 재검증 안 됨(스토리 스코프 밖 — 호출부 책임이며 기존 회귀 68 passed로 커버됨) · 풀 종료(shutdown) 훅 부재(Dev Notes 핵심 설계 결정 ②가 "데모에선 프로세스 종료로도 충분 — 필수는 아니다"로 명시적으로 선택사항 처리).

## Dev Notes

### 하드 제약 (어기면 회귀) — `run_select` 시그니처 불변
`run_select(query: str, params: tuple | None = None) -> list[tuple]` 는 아래 **4개 테스트가 monkeypatch로 의존**한다. 이름·인자·반환형(튜플 리스트, SELECT_COLUMNS 위치 순서)을 바꾸면 즉시 회귀:
- `tests/test_sql_rag_node.py` · `tests/test_doc_rag_node.py`(`fake_run_select(query, params=None)`) · `tests/test_demo_acceptance.py`(`_fake_run_select(sql)`) · 그리고 실제 호출부 `graph/sql_rag_node.py:144`(`run_select(safe_sql)`)·`graph/doc_rag_node.py:55,64`(`run_select(sql, (qvec, LIMIT))`). 내부 구현만 갈아끼우고 **껍데기는 그대로 둔다**.

### 호출부 지도 (무엇을 건드리고 무엇을 안 건드리나)
| 심볼 | 사용처 | 이 스토리에서 |
|---|---|---|
| `run_select` | `sql_rag_node.py:144`, `doc_rag_node.py:55·64`, `scripts/score_ab.py:196·208` | **내부만** 교체(시그니처 불변) |
| `readonly_connection` | `tests/test_readonly.py`만 | 제거 또는 재작성(Task 2) |
| `READONLY_ROLE="ai_readonly"` | readonly.py 내부 | 상수 유지 |
| 라우트 `search` | `routers/ai.py:29` | `await asyncio.to_thread(...)` 1줄(Task 3) |
| `graph.py`·노드·`sql_guard.py`·`schemas/ai.py` | — | **건드리지 않음**(범위 밖) |

### 핵심 설계 결정 ① — async는 "라우트 스레드 오프로드"로 (전면 async 거부)
AC3의 "async 논블로킹"에는 두 해석이 있다(A1 — 말없이 하나 고르지 않고 밝힌다):
- **(A) 전면 async**: `run_select`→`AsyncConnectionPool`, `sql_rag_node`·`doc_rag_node`→`async def`, `graph.py`→`ainvoke`, `run_search`→async, 라우트 `await`. → **거부**. 4파일+수많은 테스트로 연쇄 수술(A3 위배), 게다가 `llm.invoke`가 여전히 **동기 블로킹**이라 DB만 async로 만들어도 이벤트 루프는 안 풀린다(효과도 반쪽).
- **(B, 권고) 최소 오프로드**: `run_select`는 **동기 유지**(풀+SET LOCAL+connect_timeout), 라우트에서 `await asyncio.to_thread(run_search, ...)` 한 줄로 **동기 파이프라인 전체(LLM+DB)를 스레드풀로** 넘겨 이벤트 루프를 놓아준다. 동기 `ConnectionPool`은 스레드-세이프. → 논블로킹을 **일관되게**(LLM 포함) 달성하고 수술은 라우트 1줄. **이걸 택한다.**

> dev 판단: (B)가 A2(단순)·A3(외과적)·정직한 논블로킹 3박자에 맞다. 만약 향후 진짜 고동시성이 필요해지면 그때 전면 async를 별도 스토리로. 지금 미리 하면 과설계.

### 핵심 설계 결정 ② — 지연 싱글턴 풀 (import 시 열지 않음)
`config.py` 설계상 **비밀값(DATABASE_URL) 없이도 앱이 기동**돼야 한다(`/health`·`/docs`·미인증 401 경로). 그래서 풀을 **모듈 import 시점에 열면 안 된다**(그 순간 DATABASE_URL을 강제하게 됨). 대신 **최초 `run_select` 호출 때** 지연 생성하는 싱글턴:
```python
_pool: "psycopg_pool.ConnectionPool | None" = None

def _get_pool() -> "psycopg_pool.ConnectionPool":
    global _pool
    if _pool is None:
        dsn = require("DATABASE_URL", settings.database_url)   # 여기서만 fail-loud
        _pool = psycopg_pool.ConnectionPool(
            dsn, min_size=1, max_size=8, open=True,
            kwargs={"connect_timeout": 10, "prepare_threshold": None},
        )
    return _pool
```
`max_size`는 데모 규모라 보수적으로(예 4~8). (선택) 깔끔한 종료를 원하면 `main.py`에 FastAPI `lifespan`을 추가해 shutdown 시 `_pool.close()` — 데모에선 프로세스 종료로도 충분하니 **필수는 아니다**(넣는다면 최소한으로).

### 핵심 설계 결정 ③ — :6543 트랜잭션 풀러 + SET LOCAL 이 한 세트인 이유
- **세션 풀러(:5432) + 세션 `SET ROLE`**(현행): 커넥션이 세션 단위로 고정될 땐 안전했지만, **커넥션 풀로 물리 커넥션을 재사용**하면 세션에 눌어붙은 `SET ROLE ai_readonly`가 다음 요청으로 **누수**된다(AC-DB-1이 막으려는 바로 그 위험).
- **트랜잭션 풀러(:6543) + `SET LOCAL ROLE`**(목표): 롤 전환이 **트랜잭션 스코프**로 한정 → COMMIT/ROLLBACK 시 자동 원복 → 커넥션이 풀로 돌아갈 때 항상 깨끗. 세 요소(풀·:6543·SET LOCAL)는 **하나의 세트**다.
- **마이그레이션 불필요**: `ai_readonly` 롤과 `grant ai_readonly to postgres` 멤버십은 `0006_readonly_role.sql`에 이미 있다. 연결 롤(postgres)이 `SET LOCAL ROLE ai_readonly` 할 권한 보유 → **새 마이그 없음**.

### 버전 함정 — 트랜잭션 풀러에서 준비문(prepared statement) 비활성
Supabase 트랜잭션 풀러(:6543, Supavisor/pgBouncer 계열)는 커넥션을 트랜잭션 단위로 갈아끼우므로 **서버측 준비문이 깨질 수 있다**(`prepared statement "…" already exists`/`does not exist`). psycopg3는 기본으로 자동 준비문을 쓰므로 **풀 `kwargs={"prepare_threshold": None}`로 비활성**한다(위 코드 반영). 라이브 스모크(Task 5)에서 실제 :6543로 SELECT가 도는지 반드시 확인 — 이 함정은 무-DB 테스트로는 안 잡힌다.

### 사용자 준비물 (에픽 핸드오프 · B5) — DATABASE_URL 교체 필요 ⚠️
코드가 :6543을 "가정"할 뿐, 실제 접속 문자열은 env가 정한다. **동작하려면 사용자가 `DATABASE_URL`을 트랜잭션 풀러 문자열로 바꿔야 한다**:
- **어디서**: Supabase 대시보드 → Project Settings → Database → Connection string → **Transaction pooler(포트 6543)** 값 복사. (세션 풀러 :5432와 사용자명 형식(`postgres.<ref>`)·포트가 다르므로 새로 받아야 한다 — 코드로 :5432→:6543 문자열 치환 금지, 취약함.)
- **적용 위치**: 로컬 `api/.env` + Cloud Run 운영 `encar-ai-api`·개발 `encar-ai-api-dev` 두 서비스의 환경변수.
- **왜**: 세션 풀러(:5432)에 SET LOCAL을 쓰면 트랜잭션 격리 이점이 반감되고, 이 스토리 설계는 :6543 전제다.

### 테스트 표준 (project-context 규칙 12)
- **api**: LLM을 fake로 교체한 **결정론적 단위테스트**가 표준(라우팅·SQL가드·파라미터 추출). 이 스토리의 회귀(Task 5 결정론)는 그 스위트 재실행으로 충분. **라이브 DB 검증**(Task 4 롤 격리)은 `DATABASE_URL` 부재 시 skip + Supabase MCP 교차확인이 기존 4.1 관례(`test_readonly.py` skipif 패턴 그대로).
- **공통**: 구현 후 반드시 직접 실행·관찰(B4). 무-DB 회귀는 로컬에서, 라이브·엔드투엔드는 dev 환경에서.

### 배포·브랜치 (B3, AC-DEPLOY-1)
`develop`에서 작업·커밋 → 동작 확인. 배포 순서상 **api(Cloud Run)만** 영향(web·app·db 무관). DB 마이그레이션이 없어 롤백 리스크 낮음. 단, **Cloud Run env(DATABASE_URL)를 :6543으로 먼저 바꾸지 않으면** 배포본이 이전 :5432 세션 풀러로 붙어 격리 이점이 없다(위 "사용자 준비물"). `main` 병합은 사용자 승인 시에만.

### Project Structure Notes
- api는 Python ≥3.10(`str | None` 유니온·`asyncio.to_thread`(3.9+) 사용 가능). 손대는 파일: `api/app/db/readonly.py`(본체), `api/app/routers/ai.py`(1줄), `api/app/config.py`(주석), `api/tests/test_readonly.py`(재작성), `api/pyproject.toml`·`api/requirements.txt`(의존성). **변이 없음** — 기존 `readonly.py`의 "고정 상수 식별자·fail-loud require·컨텍스트 매니저" 스타일을 그대로 계승한다.
- **건드리지 않을 것(명시적 non-goal)**: 그래프/노드(`graph.py`·`sql_rag_node.py`·`doc_rag_node.py`)·`sql_guard.py`·`schemas/ai.py`·`listing_cards.py`·`scripts/*`(score_ab·backfill는 시그니처 불변이라 자동 호환). 마이그레이션 신규 없음. 4분기 라우팅·하이브리드는 Epic 13 몫.

### References
- [Source: epics-increment-2026-07-12.md#Story 8.4 (383~397행)] — AC 원문(BDD)
- [Source: epics-increment-2026-07-12.md#Epic 8 개요(276~278행)] — "기존 Epic 4 커넥션 레이어 수술 → RAG와 독립 조기 디리스크"
- [Source: architecture-increment-2026-07-12.md#AC-DB-1(118·183행)] — `BEGIN; SET LOCAL ROLE ai_readonly; …; COMMIT;`, 동일 물리 커넥션 재사용 누수 없음 검증, FR50 동일 작업 단위
- [Source: architecture-increment-2026-07-12.md#I1(367행)] — `readonly.py` :5432 세션풀러+세션 SET ROLE+autocommit 결정을 :6543 트랜잭션풀러+SET LOCAL로 대체(주석 갱신 포함)
- [Source: architecture-increment-2026-07-12.md#Process(242행)] — "AI DB 읽기는 매 쿼리 트랜잭션 격리, ❌ 세션 SET ROLE"
- [Source: architecture-increment-2026-07-12.md#프로젝트 트리(311행)] — `readonly.py ✎ 커넥션 풀 + BEGIN;SET LOCAL ROLE;COMMIT + async`
- [Source: architecture-increment-2026-07-12.md#Risks(82행)] — 트랜잭션 풀러 커넥션 재사용으로 SET ROLE 누수 위험(HIGH) → 트랜잭션 스코프 격리 필수
- [Source: api/app/db/readonly.py:1-44] — 현행 구현(수술 대상): :5432 세션풀러 + `SET ROLE` + `autocommit=True` + 매 호출 생 connect
- [Source: api/app/routers/ai.py:28-52] — 라우트 `async def search` → 동기 `run_search` 호출(오프로드 대상)
- [Source: api/app/graph/graph.py:115-131] — `run_search` → `COMPILED_GRAPH.invoke`(동기)
- [Source: api/app/graph/sql_rag_node.py:144] · [api/app/graph/doc_rag_node.py:55,64] — `run_select` 실제 호출부(시그니처 계약)
- [Source: api/tests/test_readonly.py:1-39] — 재작성 대상 라이브 테스트(skipif·>0 단언·write-blocked 패턴 계승)
- [Source: api/tests/test_sql_rag_node.py:42 · test_doc_rag_node.py:16-38 · test_demo_acceptance.py:100-106] — `run_select` monkeypatch(시그니처 불변 근거)
- [Source: api/app/config.py:21-22] — `database_url` 주석("Session pooler 문자열") 갱신 대상
- [Source: supabase/migrations/0006_readonly_role.sql] — `ai_readonly` 롤·`grant ai_readonly to postgres` 멤버십(마이그 불필요 근거)
- [Source: _bmad-output/project-context.md#규칙6·규칙12] — service_role 금지·ai_readonly 이중방어 / 층별 테스트 표준
- [Source: api/pyproject.toml · api/requirements.txt] — `psycopg[binary]` → `psycopg[binary,pool]` 확장 대상

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- `pytest tests/test_readonly.py -v` — SET LOCAL 구현: 2 passed(green).
- red 실측: `readonly.py`를 임시로 `SET ROLE`(세션)로 되돌려 `test_role_does_not_leak_across_reused_connection` 실행 → `AssertionError`(`'ai_readonly' != 'ai_readonly'` 실패, red) 확인 → 원복 후 2 passed 재확인(green).
- red 실험 중 발견: Supavisor 트랜잭션 풀러(:6543) 자체가 백엔드 커넥션을 재사용해, 완전히 새로운 raw psycopg 커넥션에서도 `current_user=ai_readonly`(누수) 확인됨. `RESET ROLE`을 여러 백엔드 세션에 순회 실행해 baseline(`postgres`)으로 복구.
- `pytest tests/test_sql_rag_node.py tests/test_doc_rag_node.py tests/test_demo_acceptance.py tests/test_ai_search.py` — 68 passed.
- `pytest tests/` 전체 — 165 passed, 3 skipped(라이브 트랙, DATABASE_URL 있어도 별도 마킹된 것 제외), 회귀 0.
- Supabase MCP `execute_sql`(`information_schema.role_table_grants`) — `ai_readonly`는 5개 테이블 전부 SELECT만 보유.
- 로컬 uvicorn(`:8123`) `/health` 200 → `buyer@test.com` 로그인 토큰으로 `/ai/search` 경로 A·B 각 200 확인(서버 로그 경고·에러 0).

### Completion Notes List

- Task 1: `psycopg[binary]` → `psycopg[binary,pool]`로 `api/pyproject.toml`·`api/requirements.txt` 동시 확장. `psycopg_pool` 3.3.1 설치·import 확인.
- Task 2: `api/app/db/readonly.py` 전면 재작성 — 지연 싱글턴 `ConnectionPool`(min=1, max=8, `connect_timeout=10`, `prepare_threshold=None`) 도입. `readonly_connection()`을 "풀 대여 → `conn.transaction()` → `SET LOCAL ROLE ai_readonly` → yield → 트랜잭션 COMMIT(롤 자동 원복) → 풀 반납" 구조로 재작성. `run_select(query, params=None) -> list[tuple]` 공개 시그니처·반환형 불변. 세션 `SET ROLE`+생 connect 옛 구현 완전 제거(I1). `api/app/config.py`의 `database_url` 주석을 "Transaction pooler :6543" 기준으로 갱신.
- Task 3: `api/app/routers/ai.py`의 라우트에서 `run_search` 동기 호출을 `await asyncio.to_thread(run_search, req.query, req.context)`로 교체(라우트 1줄 변경). try-except 구조·에러 포맷 불변. `graph.py`·노드는 미변경(동기 유지).
- Task 4: `api/tests/test_readonly.py`를 롤 격리 라이브 테스트로 재작성. `single_connection_pool` fixture(`min_size=1, max_size=1`, `monkeypatch`로 `readonly._pool` 교체)로 동일 물리 커넥션 재사용을 강제. `test_select_ok_and_write_blocked`(SELECT>0행+INSERT 거부)·`test_role_does_not_leak_across_reused_connection`(누수 부재) 2개. red→green을 코드를 임시로 되돌려 실측 확인(Debug Log 참조). **부수 발견**: Supavisor 풀러 자체도 백엔드 커넥션을 재사용해 세션 SET ROLE이 새로운 클라이언트 커넥션에도 누수됨을 raw psycopg로 직접 확인 — AC-DB-1(SET LOCAL)의 필요성을 한층 더 강하게 뒷받침하는 실측 근거.
- Task 5: 결정론 회귀(68+165 passed, 시그니처 불변 실증) + Supabase MCP DB 차원 권한 교차 확인(SELECT만 보유) + 로컬 엔드투엔드 curl(경로 A·B 둘 다 200, 새 파이프라인 전체 정상 동작). 이 과정에서 `api/.env`·`api/.env.example`·루트 `.env.example`의 `DATABASE_URL` 주석·값을 세션 풀러(:5432)에서 트랜잭션 풀러(:6543)로 갱신(스토리 "사용자 준비물" 항목 — 로컬은 직접 반영, **Cloud Run 운영/개발 두 서비스의 env는 사용자 승인 없이 건드리지 않음**, 아래 참고).
- 이 스토리는 `readonly.py`(본체)+`routers/ai.py`(1줄)+`config.py`(주석)+`test_readonly.py`(재작성)+의존성 2곳+env 문서 3곳만 건드렸다. 그래프/노드·`sql_guard.py`·`schemas/ai.py`·마이그레이션은 계획대로 범위 밖으로 유지했다(non-goal 준수).

### File List

- `api/pyproject.toml`
- `api/requirements.txt`
- `api/app/db/readonly.py`
- `api/app/config.py`
- `api/app/routers/ai.py`
- `api/tests/test_readonly.py`
- `api/.env` (로컬 비밀값 — git 미추적, `DATABASE_URL` 포트 5432→6543 전환)
- `api/.env.example`
- `.env.example`
- `_bmad-output/implementation-artifacts/8-4-ac-db-1-커넥션-풀-롤-격리-커넥션-풀-fr50.md`

### Change Log

- 2026-07-14: Story 8.4 구현 — `readonly.py`를 지연 싱글턴 커넥션 풀 + 트랜잭션 스코프 `SET LOCAL ROLE`(AC-DB-1)로 재구현, 라우트를 `asyncio.to_thread`로 논블로킹화(FR50/NFR8), 롤 누수 부재 red→green 테스트 신설. 결정론 회귀 165 passed·Supabase MCP DB 교차확인·로컬 엔드투엔드 curl(경로 A·B) 전부 정상. red 실험 중 Supavisor 풀러 자체의 세션 오염 위험을 실측 발견·정리. `DATABASE_URL`을 트랜잭션 풀러(:6543)로 로컬 전환(Cloud Run 운영 env는 미변경, 배포 전 사용자 조치 필요).
