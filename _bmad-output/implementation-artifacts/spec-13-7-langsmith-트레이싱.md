---
title: '13.7 LangSmith 트레이싱'
type: 'feature'
created: '2026-08-02'
status: 'done'
baseline_revision: 'dc4781f2d615063a38d4e67de82fa3f0c880d70d'
final_revision: '23ba7f617249a531835c880d5819efe9471483b4'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 개발자가 라우팅 오분류·SQL 가드 차단·0건 응답·되묻기 발동 빈도를 사후에 눈으로 확인할 관측 수단이 없다(FR51).

**Approach:** LangSmith Developer(무료 티어)를 두 환경변수(`LANGCHAIN_TRACING_V2`·`LANGCHAIN_API_KEY`)만으로 켠다 — `ChatGoogleGenerativeAI`(langchain_google_genai)와 컴파일된 LangGraph `StateGraph`는 이미 LangSmith 전역 콜백 계측을 지원하므로 애플리케이션 소스 코드는 한 줄도 바꾸지 않는다. `.env.example`(루트·api)에 두 키를 문서화한다.

## Boundaries & Constraints

**Always:**
- `api/app/**/*.py` 소스 코드는 변경하지 않는다 — 트레이싱은 `langchain-core`/`langgraph`가 `os.environ`을 직접 읽어 켜는 전역 계측이다.
- 이 두 env는 `api/app/config.py`의 pydantic `Settings`가 관여하지 않는다(그 클래스가 선언한 필드가 아니고 `extra="ignore"`라 조용히 버려진다). 실측 확인: `Settings(env_file=".env")`로 `api/.env`를 읽어도 `LANGCHAIN_TRACING_V2`는 `os.environ`에 나타나지 않는다 — `langsmith` SDK가 직접 `os.environ`을 보므로, **로컬에서 켜려면 그 값이 실제 프로세스 환경변수로 노출돼야 한다**(예: `set -a; source api/.env; set +a` 후 서버/스크립트 실행). Cloud Run은 콘솔/gcloud에 등록한 값을 컨테이너 프로세스 env로 직접 주입하므로 이 문제가 없다.
- `.env.example`(루트 api 섹션)과 `api/.env.example`에 두 키를 동일하게 문서화하고(기존 관례), 위 로컬 노출 방식을 주석으로 남긴다.

**Block If:** LANGCHAIN_API_KEY로 실제 LangSmith 트레이스 기록을 확인할 수 없다면(계정·키 폐기 등 코드 밖 문제로 판단되면) 코드로 우회하지 말고 그 사실을 결과에 남긴다.

**Never:**
- 평가 자동화·LangSmith Deployment는 도입하지 않는다(에픽 non-goal, 카드 미등록 = 월 5000 trace 하드캡 유지).
- `python-dotenv`/`load_dotenv()` 등 새 의존성이나 앱 부팅 코드를 추가해 `.env`를 프로세스 환경변수로 자동 로드하게 만들지 않는다 — "코드 변경 0" AC와, 이 프로젝트가 의도적으로 유지해 온 `config.py`의 Optional+fail-loud 설계를 둘 다 지킨다.
- `docs/deployment-runbook.md`에 Cloud Run 환경변수 목록을 새로 만들지 않는다 — 다른 비밀값(`GEMINI_API_KEY` 등)도 그 문서에 나열돼 있지 않은 기존 관례와 일관되게 예외를 두지 않는다. Cloud Run 콘솔에 두 값을 등록하는 것은 사용자가 직접 해야 할 운영 작업으로 결과에 남긴다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 트레이싱 ON | 두 env가 실제 프로세스 환경변수로 노출된 상태에서 실 질의 실행 | LangSmith 프로젝트에 새 트레이스(run)가 실제로 기록된다 | 트레이싱 실패가 검색 응답 자체에 영향 주지 않음 |
| 트레이싱 OFF(기존 상태) | 두 env가 노출되지 않은 상태에서 동일 질의 실행 | 검색 동작(라우팅·응답)이 기존과 동일, 트레이스 없음 | 없음(회귀 없음) |
| **파일엔 있으나 미노출** | `api/.env`에 값은 있지만 `source` 없이 그냥 서버/스크립트 실행 | OFF와 동일 — 트레이스 없음 | "파일에 값이 있다"와 "켜져 있다"는 다르다는 것을 실측으로 구분하는 핵심 케이스(B4) |

</intent-contract>

## Code Map

- `.env.example` -- 루트 견본, api 섹션에 `LANGCHAIN_TRACING_V2`·`LANGCHAIN_API_KEY` 키 + 로컬 노출 방식 주석 추가
- `api/.env.example` -- api 로컬 견본, 동일 키·주석 미러링(기존 관례: 루트와 api 섹션 동일 유지)

## Tasks & Acceptance

**Execution:**
- `.env.example` -- `# ===== api/.env (...) =====` 섹션에 `LANGCHAIN_TRACING_V2=`·`LANGCHAIN_API_KEY=` 추가, 위 Always 절의 로컬 노출 방식을 한 줄 주석으로 남긴다 -- FR51을 문서로 발견 가능하게 하고, "파일에 값만 넣으면 되는 줄" 착각을 예방.
- `api/.env.example` -- 동일 키·동일 주석 미러링 -- 루트 견본과의 기존 락스텝 관례 유지.

**Acceptance Criteria:**
- Given `LANGCHAIN_TRACING_V2`·`LANGCHAIN_API_KEY`가 실제 프로세스 환경변수로 노출된 상태, when `run_search()`로 실 질의를 실행하면, then LangSmith 프로젝트에 새 트레이스가 실제로 기록된다(LangSmith SDK로 직접 조회해 확인, 존재 확인이 아니라 작동 확인, B4)
- Given 위 두 env가 프로세스에 노출되지 않은 기존 상태, when 동일 질의를 실행하면, then 검색 동작은 트레이싱 유무와 무관하게 동일하고 앱 소스 코드 변경은 0건이다(회귀 없음)
- Given `.env.example`(루트·api), when 견본을 읽으면, then 두 키와 "프로세스 env로 직접 노출해야 로컬에서 켜진다"는 노트가 문서화돼 있다

## Spec Change Log

## Review Triage Log

### 2026-08-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 3, low 0)
- defer: 6: (high 0, medium 0, low 6)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `LANGCHAIN_TRACING_V2`의 실제 인식 값이 문서화돼 있지 않았다 — `langsmith.utils.tracing_is_enabled()` 소스를 읽고 직접 실행해 확인: 정확히 소문자 `"true"`만 켜지고 `"1"`·`"True"`(대문자)·빈 문자열은 에러 없이 조용히 꺼진 상태로 남는다(이 스토리 자체가 경고하는 "존재≠작동" 함정과 같은 종류). 두 `.env.example` 파일의 LangSmith 주석에 정확한 값 요건을 추가.
  - `[medium]` `[patch]` 두 env 중 하나만 설정된 상태(`TRACING_V2=true`인데 `API_KEY` 비어있음)가 문서화·검증 안 됨 — 직접 실행해 확인: `tracing_is_enabled()`는 API_KEY 유무를 보지 않고 `True`를 반환해 "켜진 것처럼" 보이지만 실제 전송은 조용히 실패한다(백그라운드 스레드에서 `LangSmithAuthError: 401`이 stderr에 남을 뿐, 검색 응답 자체는 영향 없음). 두 파일 주석에 "두 값을 함께 채워야 한다" 경고 추가.
  - `[medium]` `[patch]` 이 스토리가 만드는 관측 기능(FR51)에 저장소에 남는 회귀 테스트가 하나도 없었다(adversarial·verification-gap·intent-alignment 3개 레이어 독립 수렴) — 향후 langchain-core/langgraph 업그레이드로 자동 계측 훅이 바뀌어도 `pytest`는 계속 초록일 위험. 이 프로젝트의 기존 관례(`test_live_smoke.py`, `RUN_LIVE_SMOKE=1` 게이트)를 그대로 따라 `test_live_smoke_langsmith_tracing` 신규 추가(LangSmith env가 프로세스에 노출된 경우에만 실행, `run_search()` 후 `langsmith.Client().list_runs()`로 새 트레이스 발생을 직접 확인, 수집 지연 대비 최대 3회 재시도). 라이브 실행으로 green 확인 + OFF 대조군(env 미노출)으로 skip 경로도 확인.
  - `[low]` `defer` 6건 — 전부 이번 diff에 포함된 `epic-13-context.md`(Story 13.9 재캡파일 재고, 계획 단계에서 필요해 recompile됨)의 내용 갭이며 LangSmith 트레이싱과는 무관(edge-case-hunter 렌즈, DW-611/612가 이미 다루는 것의 인접 미다룸 케이스). DW-613으로 통합 등재, trigger: Story 13.9 step-02 planning.

**Rejected (8건, 이유 요약):**
- `source .env`가 `DATABASE_URL` 등 다른 비밀값까지 프로세스 env에 노출 — 이 프로젝트의 기존 검증 관례(Verification 섹션에 `DATABASE_URL=...` 인라인 노출)와 같은 위험 등급이라 신규 위험 아님.
- Cloud Run 환경변수 등록 작업이 `deferred-work.md`에 없음 — 코드 결함/기존 이슈가 아니라 1회성 운영 작업이라 DW 대상이 아님(Auto Run Result에 명시).
- 무료 티어 5000건 하드캡이 코드로 강제되지 않음 — 에픽이 이미 "카드 미등록" 정책으로 수용한 트레이드오프, 새 정보 아님.
- `LANGCHAIN_PROJECT` 변수 부재로 로컬/운영 트레이스 혼합 — 에픽 AC가 명시적으로 "env 2개"만 요구, 범위 밖 확장.
- 신규 spec의 `warnings: ['oversized']` 플래그 설명 없음 — 이 저장소의 다른 스펙들과 동일한, 설명 불필요한 기계용 플래그.
- 두 `.env.example` 주석 복붙 — 기존 GEMINI_API_KEY 등 다른 키에도 이미 적용된, 의도된 락스텝 관례(commit 17b1976의 사례와는 다른 종류의 중복).
- `epic-13-context.md`의 3곳 락스텝 목록에 `_SYSTEM_PROMPT` 누락 지적 — 13.2가 이미 확정한 락스텝 계약 범위에 대한 이견이며 이 스토리의 권한 밖.
- LangSmith env가 빈 문자열로 노출된("소싱은 했지만 값이 비어있는") 상태 미검증 지적 — 직접 실행해 반증: `get_env_var()`가 빈 문자열을 "미설정"과 동일하게 취급해 OFF와 동일하게 동작함을 확인(이미 문서가 정확히 서술하는 일반화).

### 2026-08-02 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 5, low 2)
- defer: 9: (high 0, medium 8, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[patch]` 직전 패스가 추가한 `test_live_smoke_langsmith_tracing`의 단언이 **이 호출이 만든 트레이스를 식별하지 않았다** — "before 스냅샷에 없던 run이 1건이라도 있으면 통과"라, 같은 프로젝트(기본값 `default`)에 쓰는 다른 프로세스의 run으로도 통과한다. 스펙이 사용자에게 지시한 Cloud Run 두 서비스 env 등록이 이뤄지면 운영 트래픽이 상시 `default`에 쌓이므로 이 검사는 **영구 green**이 된다(= 검사가 존재하지만 아무것도 안 지킴, 이 스토리가 경고하는 함정 그 자체). 루트 run의 `inputs.query`로 이번 호출의 `trace_id`를 특정한 뒤 그 트레이스에 속한 run만 세도록 교체. 실측 근거: 루트 run(`LangGraph`, `parent_run_id is None`)의 inputs에 질의 원문이 들어 있음을 라이브 조회로 확인.
  - `[medium]` `[patch]` 단언이 `assert new_runs`(비어있지 않음)뿐이라 **자동 계측 두 갈래 중 한쪽이 통째로 죽어도 통과**했다 — LLM 콜백 스팬(langchain-google-genai)과 그래프 노드 스팬(langgraph)은 서로 독립인데, LLM 스팬 1건만 남아도 green. 라이브 조회로 실제 스팬 구성을 측정(root `LangGraph` + `router`·`_route_decision`·`clarify`·`answer` 노드 + `ChatGoogleGenerativeAI` + `RunnableSequence`·`PydanticOutputParser`)한 뒤, `run_type=="llm"` 존재와 **루트가 아닌 chain 스팬** 존재를 각각 단언하도록 교체(노드 이름 하드코딩은 13.9의 노드 개명에 깨지므로 피함).
  - `[medium]` `[patch]` 게이트가 SDK의 env 해석을 손으로 재구현해(`os.environ["LANGCHAIN_TRACING_V2"] != "true"`) **계측이 켜져 있는데도 조용히 skip**됐다. 직접 실행해 확인: `langsmith.utils.get_env_var`의 namespaces는 `("LANGSMITH","LANGCHAIN")`이라 `LANGSMITH_*`가 우선하고, `LANGSMITH_TRACING=true` 하나만 있어도 `tracing_is_enabled()`는 True다(현재 LangSmith 문서가 권장하는 이름이 이쪽). 게이트를 `tracing_is_enabled()` + `get_env_var("API_KEY")`로 교체 — 신 이름만 노출한 상태로 라이브 실행해 **skip이 아니라 PASSED**로 바뀌는 것까지 확인.
  - `[medium]` `[patch]` 조회 대상 프로젝트도 손으로 재구현해(`os.environ.get("LANGCHAIN_PROJECT","default")`) **전송 대상과 어긋날 수 있었다** — 실제 SDK 규칙은 `HOSTED_LANGSERVE_PROJECT_NAME` → `LANGSMITH/LANGCHAIN_PROJECT` → `LANGSMITH/LANGCHAIN_SESSION` → `"default"`의 6갈래(소스 확인). `LANGSMITH_PROJECT`가 설정된 환경에선 트레이스는 A에 쌓이고 테스트는 `default`를 폴링해 "계측이 죽었다"고 오진(false red)한다. `get_tracer_project()`를 그대로 쓰도록 교체.
  - `[medium]` `[patch]` 전송 flush 없이 고정 폴링(3회×2초)으로 **백그라운드 업로더와 경합**했고, 마지막 sleep(2)은 뒤에 아무 검사도 없는 죽은 대기였다. 실측: `wait_for_all_tracers()`는 0.2초에 끝나지만 **서버 색인은 t=3초에 0건 → t≈6초에 8건** — 기존 4초 예산은 아슬아슬하게 부족할 수 있었다(첫 두 번의 폴링이 실제로 0건이었음). `wait_for_all_tracers()`로 전송을 먼저 비우고, 색인 지연은 측정값의 5배인 30초 예산으로 분리.
  - `[medium]` `[patch]` 이 스토리의 실질 산출물인 `.env.example` 주석이 **`LANGSMITH_*` 우선순위를 안 적어** "이 두 값만 채우면 켜진다"·"API_KEY가 비면 하나도 기록되지 않는다"가 거짓이 되는 셸이 존재했다(실행 확인: `LANGSMITH_API_KEY`가 있으면 여기 채운 `LANGCHAIN_API_KEY`는 무시되고 남의 워크스페이스로 전송). 후행 공백·인라인 주석(`true # 메모`)도 조용히 꺼진다는 것(실행 확인)과 함께 두 견본 파일에 추가.
  - `[low]` `[patch]` 테스트 docstring이 "의존성 업그레이드로 계측이 깨져도 아무도 모른다"를 막는다고 선언했지만 **CI에서 안 도는 검사**라 그 실패 모드는 그대로 남는다. B4의 "그 검사가 안 보는 것을 검사 옆에 적는다"를 이행 — CI 미실행(의도된 표준)·CLARIFY 경로만 탐·스팬의 존재만 보고 내용은 안 봄 3가지를 명기하고, 근본 원인(버전 미고정)은 DW-615로 이월.
  - `[low]` `[patch]` `.github/workflows/tests.yml`의 안전 경고가 `test_live_smoke.py (4건)`으로 남아 실제 6건과 어긋났다(직전부터 5건이라 이미 틀렸고 이 스토리가 6번째를 더했다). 6건으로 정정하고, 이 테스트가 Gemini 과금 외에 **LangSmith 무료 trace 쿼터도 소모**한다는 사실을 경고에 추가. 같은 줄의 낡은 "나머지 167건"은 손대는 줄이라 "다수"로 일반화(수치 사본은 반드시 늙는다 — 이 저장소가 이미 겪은 실패).

**Deferred (9건 → DW-614·615·616 신규 등재, 기존 항목 무수정):**
- DW-614(medium, 7건) — `epic-13-context.md`의 Story 13.9 초안에 **적힌 지시 자체가 성립하지 않는** 결함: G2 재캡처 순서가 자기참조라 항상 통과, "조건 추출 우선" 구조에서 REJECT 분기 붕괴, 같은 구조에서 SQL/HYBRID 경계 미정의, 최상급×하이브리드는 `sql_guard`가 2차 정렬키를 차단해 정렬을 표현할 자리 없음(실물 확인), 13.9가 exit-gate 뒤로 가면서 에픽 종료조건 미정의, fake-LLM 단위테스트로는 프롬프트 흔들림 검출 불가, RESET 오염 데이터 teardown 미규정. DW-613("AC가 안 다룬 인접 케이스")과 층위가 달라 중복 아님.
- DW-615(medium, 1건) — `langchain-google-genai` 버전 무고정·`langsmith` 미선언·`api/uv.lock` 미사용·Dockerfile이 매 빌드 재해석(전부 실물 확인). FR51 계측이 재빌드로 끊겨도 배포는 초록.
- DW-616(low, 1건) — 루트/api `.env.example` 락스텝이 관례로만 존재하고 검사가 없음(B9). 이 스토리 산출물 중 유일하게 secrets 없이 CI에서 돌 수 있는 검사가 될 수 있는 자리.

**Rejected (10건, 이유 요약):**
- `LANGSMITH_TRACING=false`+`LANGCHAIN_TRACING_V2=true`면 게이트는 통과하는데 SDK는 꺼져 false red — **직접 실행해 반증**(True 반환). `TRACING_V2`가 `TRACING`보다 먼저 해석되므로 그 조합은 켜진 상태다.
- `langsmith` 미선언이 모듈 전체 collection error를 낸다 — 과장. import가 함수 본문 안이라 수집엔 영향 없고, `langsmith`는 `langchain-core`의 **필수 전이 의존**(`langsmith<1.0.0,>=0.3.45`, 확인)이라 앱이 도는 환경에서 부재할 수 없다. 선언 정책 자체는 DW-615로 이월.
- 공백만 든 API_KEY가 게이트를 통과한다 — SDK `get_env_var`가 공백-only를 미설정으로 취급하므로 patch(게이트를 SDK 판정으로 교체)가 자동 해소. 별건 아님.
- `list_runs`의 404/401을 skip으로 흡수하라 — 인텐트의 **Block If가 정반대를 지시**한다("트레이스를 확인할 수 없으면 코드로 우회하지 말고 사실을 남긴다"). 시끄럽게 실패하는 쪽이 맞다.
- `set -a; source .env`가 다른 비밀값까지 노출 — 재검토해도 기각(개발자 자기 셸 안의 자기 키 2개, 새 노출면 아님). 단 **직전 패스의 기각 근거는 사실오류였다**: "`DATABASE_URL` 인라인 노출과 같은 등급"이라 했으나 `api/.env`엔 `DATABASE_URL`이 없다(확인). 결론은 같고 근거만 정정.
- `LANGCHAIN_PROJECT` 분리를 문서화하라 — patch 1(호출 식별 단언)이 공유 프로젝트 오염 위험을 제거하므로 새 env 없이 해결. 에픽 AC의 "env 2개" 범위 유지.
- 무료 5000 trace 상한 소진과 계측 파손을 구분 못 한다 — 이미 수용된 트레이드오프에 대한 추측성 지적.
- `sprint-status.yaml`은 done인데 스펙은 in-review라 불일치 — **이 리뷰 패스가 만든 일시 상태**(종료 시 done 복귀).
- 신규 테스트가 Code Map·AC에 없다 — 그 테스트는 직전 리뷰 패스의 **patch 산출물**이고, 리뷰 패치가 원 Code Map에 없는 것은 정상이다. 기록은 Auto Run Result의 Files changed가 담당.
- `test_live_smoke`가 CI에서 안 돌아 갭이 안 닫혔다 — 라이브·과금 테스트를 CI 밖에 두는 것은 이 저장소의 **의도된 표준**(project-context 규칙 12, tests.yml이 명시적으로 금지). 대신 "안 보는 것"을 patch로 검사 옆에 명기하고 근본 위험은 DW-615로 이월.

### 2026-08-02 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 2, medium 4, low 3)
- defer: 2: (high 0, medium 0, low 2)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[patch]` 직전 패스가 "두 갈래를 각각 못박았다"고 선언한 `node_spans` 단언이 **LangGraph 노드 계측이 통째로 죽어도 통과**했다 — 단언이 "비루트 chain 스팬"이었는데 그 자리를 langchain-core가 만드는 `RunnableSequence`가 채우기 때문이다(노드 계측과 무관한, LLM 스팬과 **같은** 콜백 경로의 산물). 실측 재현: 루트 + `RunnableSequence` + `ChatGoogleGenerativeAI`만 있는 스팬 집합(노드 0개)에 옛 단언을 적용 → PASS. 즉 두 갈래가 아니라 한 갈래를 두 번 센 것이다. `COMPILED_GRAPH.get_graph().nodes`에서 노드 이름을 구해 그 이름을 가진 스팬을 단언하도록 교체(하드코딩 아니라 그래프에서 파생 — 13.9의 노드 개명에 안 깨진다). 같은 스팬 집합에 새 단언 적용 → FAIL, 정상 집합 → PASS.
  - `[high]` `[patch]` 이 스토리의 **실질 산출물인 견본 주석에 사실이 아닌 문장이 실려 나갔다** — "셸에 LANGSMITH_*가 있으면 그쪽이 이긴다, LANGSMITH_TRACING=true 하나만 있어도 켜진다". 직접 실행해 반증: SDK 해석 순서는 **접미사 우선, 그 안에서 네임스페이스**다. `LANGCHAIN_TRACING_V2=false` + `LANGSMITH_TRACING=true` → `tracing_is_enabled()`는 **False**(견본 주석대로면 True여야 함). 더 나쁜 것은 같은 주석이 경고하는 오타값(`"true "`)이 올바르게 설정한 `LANGSMITH_TRACING=true`를 **덮어서 끈다**는 점 — 두 경고가 서로를 배반한다. 두 견본 파일의 해당 문단을 실제 규칙으로 교체하고, 첫 줄도 "이 두 값만 채우면 켜진다"(파일에 적기만 하면 꺼져 있다는 이 스토리의 핵심을 정면으로 부정)에서 "프로세스 env로 노출돼야 켜진다"로 뒤집었다.
  - `[medium]` `[patch]` 견본이 주장하는 env 해석 규칙을 검증하는 검사가 **하나도 없었다** — 위 high 2번이 그 대가다(틀린 주장이 두 번의 리뷰 패스를 통과했다). `api/tests/test_langsmith_env_contract.py` 신규: 인식값(`true`만, `True`·`1`·후행공백·인라인주석은 꺼짐)·접미사/네임스페이스 우선순위·API_KEY 네임스페이스·"TRACING만 켜도 켜진 것처럼 보임"을 결정론으로 못박는다. **네트워크·키·과금이 없어 CI의 api 잡에서 실제로 돈다** — 이 스토리 산출물 중 CI가 지켜주는 유일한 검사다(B9). 일부러 깨서 확인: 옛 주석의 주장을 그대로 단언 → FAILED, fixture의 `get_env_var.cache_clear()` 제거 → 2건 FAILED(캐시를 안 비우면 검사가 눈을 감는다는 것까지 실측), 되돌려 10건 PASSED.
  - `[medium]` `[patch]` 트레이스 식별이 **하드코딩된 질의 문자열**이라 (a) 같은 질의를 동시에 돌리는 다른 프로세스의 트레이스로 통과하고, (b) 입력 마스킹(`LANGSMITH_HIDE_INPUTS`)이나 그래프 state 키 개명만으로 영구 false red가 됐다. `collect_runs()`로 **이번 호출이 실제로 만든 run id**를 받아 `list_runs(trace_id=...)`로 서버측에서 좁히도록 교체 — 프로젝트 전체를 `limit=100`으로 훑던 것도 함께 사라져, 운영 트래픽이 같은 프로젝트에 쌓여도 우리 트레이스가 페이지 밖으로 밀리지 않는다. 라이브로 반증 확인: 무작위 trace_id 조회 → 0건(식별이 아무거나 잡는 게 아님).
  - `[medium]` `[patch]` 폴링 루프가 **루트가 보이면 즉시 중단**해, 자식 스팬이 아직 색인 전이면 뒤이은 llm·노드 단언이 false red가 됐다(직전 패스가 측정한 "t=3s 0건 → t≈6s 8건"이 바로 부분 색인 구간이다). 세 조건이 다 설 때까지 예산 안에서 계속 폴링하도록 교체.
  - `[medium]` `[patch]` `list_runs(project_name=...)`는 내부에서 `read_project`를 부르고 **프로젝트가 없으면 `LangSmithNotFoundError`를 던진다**(SDK 소스 확인) — 예외가 루프 밖으로 튀어 30초 예산과 우리가 쓴 실패 메시지가 통째로 무용지물이었다. 하필 "계측이 죽어 프로젝트가 아직 안 만들어진" 상태에서 발동한다. 루프 안에서 흡수하도록 교체.
  - `[medium]` `[patch]` 라이브 실행으로 드러난 실제 결함: `collect_runs()`는 루트를 **2개** 돌려준다(`LangGraph` 외에 router 안의 `RunnableSequence`도 자기 콜백 컨텍스트에선 루트). `[0]`을 고르면 서버에 없는 id를 잡아 0건 → red가 났다. 고르지 않고 **후보 전부를 조회해 합집합**으로 바꿔 해소(둘 다 이 프로세스가 방금 만든 UUID라 남의 트레이스는 섞일 수 없다).
  - `[low]` `[patch]` `.github/workflows/tests.yml`의 "그중 1건만 LangSmith 쿼터를 소모한다"가 부정확 — 계측은 프로세스 전역이라 env가 노출되면 **그 파일의 모든 테스트가** 쿼터를 소모한다. 아울러 직전 패스가 "수치 사본은 늙는다"며 옆의 `167건`을 "다수"로 일반화해 놓고 같은 줄에 `6건`을 새로 하드코딩한 자기모순도 제거(건수 없이 "파일 전체"로).
  - `[low]` `[patch]` 스펙 Verification의 사람이 실행하는 3번 명령이 여전히 `project_name='default'` 하드코딩 — 직전 패스가 테스트에선 고쳤지만 사람이 읽는 쪽엔 남아, `LANGSMITH_PROJECT`가 설정된 셸에서 "계측이 죽었다"고 오진하게 돼 있었다. `get_tracer_project()`로 교체. 테스트 docstring의 "안 보는 것"도 보강(라우팅 한 갈래만 탐 + `_run_or_skip`가 인프라 장애를 skip으로 흡수함을 명기).

**Deferred (2건 → DW-617 신규 등재, 기존 항목 무수정):**
- DW-617(low, 2건) — `epic-13-context.md`의 13.9 새 요건 두 문장: (1) "명시 차종 교체 요청은 SQL" 무조건 규칙이 13.2의 4분기 계약(구조+의미=HYBRID)과 정면 충돌, (2) `contextualize_query`에 "이어받을 조건이 0개인 턴"과 "같은 축 재명시 시 누적/대체" 규칙이 미정의. DW-613(빠진 케이스)·DW-614(적힌 지시가 성립 안 함)와 층위가 달라 중복 아님.

**Rejected (10건, 이유 요약):**
- `epic-13-context.md`의 G2 재캡처 자기참조를 이 diff에서 고쳐라 — 이미 DW-614 #1로 등재됐고 그 `trigger:`가 **정확히 13.9 step-02 planning**(=13.9 스펙을 쓰는 순간)을 가리킨다. 장부가 제 역할을 하는 자리라 중복 등재·재수정 불필요.
- 결정론 단위테스트로 프롬프트 흔들림 검출 불가 / 에픽 종료조건 미정의 — 각각 DW-614 #6·#5와 동일 주장.
- 신규 테스트가 Code Map·AC에 없다 — 직전 패스와 같은 판단 유지(리뷰 패치 산출물의 기록처는 Auto Run Result의 Files changed).
- DW-616의 트리거가 "다음에 `.env.example` 키를 바꾸는 스토리"인데 정작 이 스토리가 그 상황이었다 — 지적은 타당하나 **기존 장부 항목의 상태·해소는 오케스트레이터 소유**라 이 패스가 손대지 않는다.
- Cloud Run env 등록을 장부에 등재하라 — 인텐트가 그 자리를 명시적으로 지정했다("사용자가 직접 해야 할 운영 작업으로 **결과에 남긴다**"). 범위 권한은 인텐트에 있다.
- EU 리전·셀프호스팅용 `LANGSMITH_ENDPOINT` 미문서화 — 이 프로젝트에 해당 없는 추측성 확장.
- `_run_or_skip`가 DB·키 부재를 skip으로 흡수해 트레이싱 검사가 인프라 상태를 보고한다 — 이 파일의 기존 관례이고 이 변경이 만든 것이 아니다. 다만 "안 보는 것"에 명기하는 것으로 patch 처리.
- CLARIFY 경로만 커버한다 — 이미 docstring의 "안 보는 것"에 명기돼 있다(문구만 13.9 대비로 보강).
- I/O 매트릭스 2·3행에 저장소 검사가 없다 — 3행("파일엔 있으나 미노출")은 게이트 skip이 곧 그 상태의 관측이고, 2행(OFF 회귀)은 기존 스위트가 env 무관이라는 사실 자체가 근거다.
- 트레이스 식별에 nonce를 심어라 — `collect_runs` 기반 run id 교체(patch 4)가 더 강한 식별을 제공하므로 질의문 변조 불필요.

### 2026-08-03 — 독립 후속 리뷰 패스 (DW-618 소진)

새 세션(직전 세 패스의 문맥 없음)에서 "done이니까 맞다"를 가정하지 않고 **전부 다시 돌려** 확인했다. 기준선: 전체 스위트 **399 passed, 85 skipped**.

- intent_gap: 0 / bad_spec: 0 / patch: 3 (high 0, medium 2, low 1) / defer: 2 (low)

**먼저 확인한 것 — 3차 패스가 "고쳤다"고 선언한 것이 진짜인가(라이브 재현):**
- `test_live_smoke_langsmith_tracing`의 노드 스팬 단언을 **라이브에서 양방향으로** 검증했다. 3차 패스는 합성 스팬 집합으로만 확인했으므로 실제 테스트가 통째로 도는 상태에서 다시 쟀다. (a) 그대로 실행 → **PASSED**(9.4초). (b) `Client.list_runs` 결과에서 그래프 노드 이름(`answer·clarify·guard·hybrid·router·sql`) 스팬만 걸러내 "LangGraph 노드 계측만 죽은 상태"를 재현 → **FAILED**(`assert node_spans`, 38.6초 = 30초 예산 소진 후 실패). **3차의 수정은 실재한다** — 노드 계측을 죽이고 초록을 얻을 수 없다.
- 노드 이름이 langchain-core가 만드는 스팬 이름과 겹치지 않는지도 확인(`add_node` 6개 = `router·sql·hybrid·clarify·guard·answer` vs 계측 산물 `RunnableSequence·ChatGoogleGenerativeAI·PydanticOutputParser·_route_decision`) — 3차가 잡은 "한 갈래를 두 번 세는" 구조가 재발할 자리는 현재 없다.

**addressed_findings:**
  - `[medium]` `[patch]` `test_langsmith_env_contract.py`에 **아무도 지키지 않는 규칙이 하나 있었다** — "빈 값·공백-only는 미설정으로 취급되어 다음 후보로 내려간다". 돌연변이 검사로 실측: `langsmith.utils.get_env_var`에서 `value.strip() != ""` 조건만 뺀 가짜 SDK를 끼워도 **기존 10건이 전부 초록**이었다. 파라미터 검사의 `("", False)`가 그 자리를 덮는 것처럼 보이지만 그건 `"" != "true"`라서 통과하는 것이고, "빈 값이면 자리를 비워 다음 후보로 내려간다"와 "빈 값이 자리를 막는다"를 **구분하지 못한다**(3차가 잡은 "두 번 센다"와 같은 종류의 착시). 이 규칙에 매달린 것이 둘: 견본 주석의 "안 쓸 거면 반드시 비워 둬라"(견본은 실제로 두 키를 빈 값으로 커밋한다)와 라이브 게이트의 `not get_env_var("API_KEY")`. `test_빈값과_공백만_있는_값은_미설정으로_취급된다` 신규 — 같은 가짜 SDK에 **FAILED**, 실제 SDK로 **11 passed**.
  - `[medium]` `[patch]` DW-616(두 견본의 락스텝이 관례로만 존재)을 재확인하다가 **DW-616이 제안한 해법 자체가 성립하지 않는다**는 것을 실측했다 — 두 파일의 키 집합은 이미 일치하지 않는다(`api/.env.example`에만 `CORS_ORIGINS`·`CORS_ORIGIN_REGEX`). "키 집합의 일치"를 그대로 단언하면 첫 실행부터 red다. `api/tests/test_env_example_parity.py` 신규: 측정한 비대칭 2건을 `_KNOWN_API_ONLY`로 **동결**하고(면제가 아니라 동결 — 새 비대칭은 어느 방향이든 red), 양방향으로 검사한다. 일부러 깨서 확인: 루트에만 키 추가 → FAILED, api에만 키 추가 → FAILED, api 견본에서 LangSmith 키 제거 → 2건 FAILED, 원복 → 2 passed. 네트워크·키 없음 → CI의 api 잡에서 실제로 돈다.
  - `[low]` `[patch]` Verification 3번 명령이 **적힌 대로 실행하면 죽는다** — 새 셸에서 그대로 돌려 확인: `LangSmithAuthError: 401`. 앞 명령의 `source .env`가 같은 셸에 남아 있다는 숨은 전제였고, 이 스토리가 없애려는 "파일에 있음 ≠ 노출됨" 함정과 정확히 같은 종류다(13.8 후속 리뷰가 `DATABASE_URL` 누락으로 잡은 것과 동형). `set -a && source .env && set +a`를 그 줄에도 붙이고 이유를 남겼다 — 붙인 뒤 실행하면 방금 기록된 run 3건이 조회된다.

**확인했으나 손대지 않은 것:**
- DW-615(langchain 계열 버전 미고정) — 실물 재확인: `requirements.txt`·`pyproject.toml` 둘 다 `langchain-google-genai` 무버전, `langsmith` 미선언, `api/Dockerfile`은 `pip install -r requirements.txt`, 커밋된 `api/uv.lock`(git 추적됨)은 CI·Dockerfile·스크립트 어디서도 안 쓰인다. **장부의 서술이 전부 정확하다.** 의존성 정책 변경은 이 리뷰(테스트·문서·CI 한정)의 권한 밖이라 그대로 둔다.
- 견본 주석이 "CI에서 실제로 검사한다"고 주장하는 부분 — `.github/workflows/tests.yml`의 api 잡이 `working-directory: api`에서 `python -m pytest -q`(전체)를 돌리므로 그 주장은 참이다(존재 확인이 아니라 배선 확인).

**Deferred (2건 → DW-641 신규 등재, 기존 항목 무수정):**
- DW-641(low, 2건) — (1) 라이브 테스트의 단언 로직이 테스트 함수 본문에 인라인이라 결정론으로 재검증할 방법이 없다(3차·이번 패스 모두 매번 손으로 돌연변이를 만들어 확인했다), (2) `_KNOWN_API_ONLY`의 CORS 비대칭이 의도인지 누락인지 미확인.

## Design Notes

`api/app/config.py`의 pydantic `Settings(env_file=".env")`는 `.env` 파일을 읽어 **자신이 선언한 필드만** 채운다 — `load_dotenv()`처럼 파일 내용을 통째로 `os.environ`에 반영하지 않는다(직접 실행해 확인: `Settings()` 인스턴스화 후에도 `os.environ`엔 `LANGCHAIN_TRACING_V2`가 없다). `langsmith`/`langchain-core`의 자동 계측은 `os.environ`을 직접 읽으므로, `api/.env`에 값을 적어 넣는 것과 "트레이싱이 실제로 켜지는 것" 사이엔 이 프로젝트에 한해 괴리가 있다. Cloud Run은 컨테이너 프로세스 env로 직접 값을 주입해 이 괴리가 없고, 로컬은 실행 전 `source`(또는 인라인 prefix)가 필요하다 — 이 문서화가 이 스토리의 실질적인 산출물이다.

## Verification

**Commands:**
- `cd api && .venv/bin/python -m pytest tests/ -q` -- expected: 기존과 동일하게 전량 통과(회귀 없음, 이 변경이 `.env.example` 문서 2건뿐임을 뒷받침).
- `cd api && set -a && source .env && set +a && DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres .venv/bin/python -c "from app.graph.graph import run_search; print(run_search('가장 저렴한 SUV 보여줘')['route'])"` -- expected: 정상 라우팅 결과 출력(로컬 Supabase 필요).
- 위 명령 직후 `cd api && set -a && source .env && set +a && .venv/bin/python -c "from langsmith import Client; from langsmith.utils import get_tracer_project; c=Client(); runs=list(c.list_runs(project_name=get_tracer_project(), limit=3)); print([(r.name, str(r.start_time)) for r in runs])"` -- expected: 방금 실행한 타임스탬프에 해당하는 새 run이 조회된다(트레이스 실제 기록 확인). 조회 프로젝트를 `'default'`로 하드코딩하지 않는 이유: `LANGSMITH_PROJECT`가 설정된 셸에선 전송 대상과 어긋나 "계측이 죽었다"고 오진한다. `set -a && source .env && set +a`를 이 줄에도 반복하는 이유(✎ 2026-08-03 후속 리뷰, 실행해서 확인): 이게 없으면 `LANGCHAIN_API_KEY`가 프로세스에 없어 `LangSmithAuthError: 401`로 죽는다 — 앞 명령의 셸 상태를 물려받는다는 숨은 전제였고, 하필 이 스토리가 없애려는 "파일에 있음 ≠ 노출됨" 함정 그 자체다.
- 대조군: 위 `source .env` 없이(트레이싱 env 미노출 상태로) 같은 `run_search` 명령을 실행 -- expected: 동일한 라우팅 결과, LangSmith에 새 run 없음(OFF 회귀 없음 + "파일에 있음 ≠ 켜짐" 실측 증거).

**Manual checks (if no CLI):**
- LangSmith 대시보드(smith.langchain.com)에서 해당 프로젝트를 열어 방금 실행한 질의의 trace가 라우터→분기 노드 흐름으로 보이는지 육안 확인.

## Auto Run Result

**Status:** done

**Summary:** LangSmith(무료 관측 도구) 트레이싱을 두 환경변수(`LANGCHAIN_TRACING_V2`·`LANGCHAIN_API_KEY`)만으로 켜는 FR51을 구현했다. 애플리케이션 소스 코드는 한 줄도 바꾸지 않았다 — `langchain_google_genai`의 `ChatGoogleGenerativeAI`와 컴파일된 LangGraph `StateGraph`가 이미 LangSmith 전역 콜백 계측을 지원하기 때문이다. 대신 이 두 값이 `api/app/config.py`의 pydantic `Settings`를 거치지 않고(`extra="ignore"`로 조용히 버려짐) `langsmith` SDK가 `os.environ`을 직접 읽는다는 것을 실측으로 확인해, "파일에 값만 있고 실제로는 안 켜진 상태"라는 함정을 `.env.example`(루트·api) 주석으로 문서화했다. 코드리뷰에서 같은 종류의 함정 2건(정확한 값 요건 미문서화, 부분 설정 무경고)을 추가로 잡아 패치했고, 이 관측 기능 자체를 지키는 회귀 테스트가 저장소에 하나도 없다는 지적을 받아들여 기존 `test_live_smoke.py` 관례를 따르는 게이트 테스트를 신규 추가했다.

**Files changed:**
- `.env.example` -- api 섹션에 `LANGCHAIN_TRACING_V2`·`LANGCHAIN_API_KEY` 키 + 정확한 값 요건·로컬 노출 방식(`set -a; source api/.env; set +a`) 주석 추가.
- `api/.env.example` -- 동일 키·동일 주석 미러링.
- `api/tests/test_live_smoke.py` -- `test_live_smoke_langsmith_tracing` 신규(1차 패치 3). 2차 패스에서 대폭 강화: 게이트를 SDK 판정(`tracing_is_enabled`/`get_env_var`)으로 교체해 `LANGSMITH_*` 이름도 인정, 조회 프로젝트를 `get_tracer_project()`로 통일, 단언을 **이 호출의 trace_id로 한정**하고 llm 스팬·비루트 chain 스팬을 각각 못박음, `wait_for_all_tracers()` + 실측 기반 30초 예산, "이 검사가 안 보는 것" 명기(B4).
- `_bmad-output/implementation-artifacts/epic-13-context.md` -- step-01 라우팅 단계에서 재캡파일(계획 문서 `epics-increment-2026-07-12.md`가 Story 13.9 신설로 이 세션 시작 전에 이미 바뀌어 있었음 — 이 스토리의 작업물이 아니라 워크플로 자체의 캐시 최신화).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-613 신규 open(1차 패스). 2차 패스에서 DW-614·615·616 신규 open 추가(기존 항목은 무수정).
- `.github/workflows/tests.yml` -- (2차 패스) CI 안전 경고의 `test_live_smoke` 건수 4→6 정정 + LangSmith trace 쿼터 소모 경고 추가. (3차 패스) 건수 표기를 아예 제거하고 "env 노출 시 이 파일의 **모든** 테스트가 쿼터를 소모"로 정정. 주석만 변경, 잡 동작 무변경.
- `api/tests/test_langsmith_env_contract.py` -- (3차 패스 신규) 두 견본 파일이 주장하는 env 해석 규칙을 결정론으로 못박는다. 네트워크·키·과금 없음 → **CI에서 실제로 도는 유일한 이 스토리 산출물**.

**Review findings breakdown:** 3회 패스. 1차: patch 3(medium 3)·defer 6(low)·reject 8(low). 2차(후속): patch 8(high 1, medium 5, low 2)·defer 9(→ DW-614·615·616)·reject 10. 3차(후속): 4개 레이어 재실행 — patch 9(high 2, medium 4, low 3) 전부 적용·재검증, defer 2(low → DW-617 신규 등재), reject 10(전부 low). 세 패스 모두 intent_gap 0, bad_spec 0.

3차 패스의 핵심은 **2차가 "고쳤다"고 선언한 것이 실제로는 안 고쳐져 있었다**는 것이다. 2차는 "자동 계측 두 갈래를 각각 못박았다"고 적었지만, 그 두 단언(`llm` 스팬 존재 + 비루트 `chain` 스팬 존재)은 실은 **같은 콜백 경로를 두 번 센 것**이었다 — 비루트 chain 자리를 langchain-core의 `RunnableSequence`가 채우므로 LangGraph 노드 계측이 통째로 죽어도 초록이었다(실측 재현). 동시에, 이 스토리의 진짜 산출물인 견본 주석에는 **실행하면 바로 반증되는 문장**이 두 패스를 통과해 실려 있었다(LANGSMITH_* 우선순위). 두 결함의 공통 원인은 하나다: 문서가 주장하는 것도, 검사가 주장하는 것도 **아무것도 그 주장을 검증하지 않았다.** 그래서 이번 패스는 개별 문장을 고치는 데 그치지 않고 그 주장들을 CI에서 도는 결정론 검사로 옮겨 심었다(B9).

**Follow-up review recommendation:** true (이번 패스 patch high 2건 → 규칙상 true).

**Verification performed (3차 패스, 패치 후 재실행):**
- 전체 스위트(기준선과 같은 조건: 라이브·DB env 미노출) → **397 passed, 85 skipped**. 직전 387에서 +10은 신규 결정론 테스트뿐 — 회귀 없음.
- **신규 결정론 테스트를 일부러 깨서 red 확인(B4)** 2가지: (a) 옛 견본 주석의 주장(`LANGSMITH_TRACING`이 무조건 이긴다)을 그대로 단언 → **FAILED**(즉 이 검사가 있었다면 그 틀린 문장은 못 나갔다), (b) fixture의 `get_env_var.cache_clear()` 제거 → 2건 **FAILED**(캐시를 안 비우면 검사가 눈을 감는다는 것도 실측). 되돌린 뒤 **10 passed**.
- **노드 스팬 단언 red/green 대조(B4):** 스펙이 라이브로 기록해 둔 실제 스팬 구성에서 LangGraph 노드 스팬만 제거한 집합에 — 옛 단언(비루트 chain) → **PASS**(= 안 잡음), 새 단언(그래프 노드명 일치) → **FAIL**(= 잡음). 정상 집합에선 둘 다 PASS. 노드 이름은 `COMPILED_GRAPH.get_graph().nodes`에서 파생하므로 실측값은 `['answer','clarify','guard','hybrid','router','sql']`.
- 우선순위 정정 근거 직접 실행: `LANGCHAIN_TRACING_V2=false` + `LANGSMITH_TRACING=true` → **False**, `LANGCHAIN_TRACING_V2=true` + `LANGSMITH_TRACING=false` → **True**, `LANGCHAIN_TRACING_V2="true "` + `LANGSMITH_TRACING=true` → **False**, `LANGCHAIN_TRACING_V2=""` + `LANGSMITH_TRACING=true` → **True**. 견본 주석이 틀렸음을 확정.
- 라이브 ON(기존 `LANGCHAIN_*` 이름) → **PASSED**(12.9초). 라이브 ON(신 이름 `LANGSMITH_*`만) → **PASSED**. OFF 대조군(두 env 미노출) → **SKIPPED**.
- **라이브에서 실제 red를 만나 원인을 실측으로 규명:** 첫 실행이 0건으로 FAILED → 라이브 조회로 `collect_runs()`가 루트를 2개(`LangGraph`·`RunnableSequence`) 돌려주고 `[0]`이 서버 트레이스 루트가 아님을 확인(서버가 보고한 trace_id 집합은 `LangGraph` id 하나뿐, 그 id로 조회하면 8건). 후보 전부 조회·합집합으로 교체 후 **PASSED**.
- **계측만 끊어 red 확인(B4):** `tracing_context(enabled=False)`로 `run_search`를 감싸 조회는 살리고 전송만 차단 → **우리 메시지로 FAILED**("…이 호출의 트레이스가 기록되지 않았다"). 되돌린 뒤 **PASSED**.
- **식별이 아무거나 잡지 않는지 확인:** 무작위 UUID로 `list_runs(trace_id=...)` → **0건**.
- 회귀 대조군: `run_search("가장 저렴한 SUV 보여줘")`를 ON/OFF로 각각 실행 → 둘 다 `route: CLARIFY`, 동일 답변 문구(트레이싱 유무가 검색 동작에 영향 없음).

**Verification performed (2차 패스, 패치 후 재실행):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **387 passed, 85 skipped** (1차와 동일 — 회귀 없음).
- 라이브 ON(기존 `LANGCHAIN_*` 이름) → **PASSED** (12.8초).
- 라이브 ON(신 이름 `LANGSMITH_TRACING`·`LANGSMITH_API_KEY`만 노출, `LANGCHAIN_*` 제거) → **PASSED**. 패치 전 게이트라면 skip됐을 상태 — 게이트의 조용한 구멍이 닫힌 것을 실제로 확인.
- OFF 대조군(두 env 미노출) → **SKIPPED**(게이트 정상 작동).
- **일부러 깨서 red 확인(B4)** 2가지: (a) 전송 엔드포인트를 죽은 주소로 → FAILED(SDK 연결 오류로 시끄럽게 실패, 조용한 통과 아님), (b) 조회는 살리고 **계측만** 끊음(`tracing_context(enabled=False)`로 `run_search` 감쌈) → **우리 단언이 우리 메시지로 FAILED**("…이 호출의 트레이스가 기록되지 않았다"). 되돌린 뒤 재실행 → **PASSED**(green 복귀 확인).
- 색인 지연 실측: `wait_for_all_tracers()`는 0.2초에 완료되나 서버 조회는 t=3초 0건 → t≈6초 8건. 기존 4초 예산이 부족할 수 있었음을 수치로 확인하고 30초로 교체.
- 트레이스 구조 실측: 루트 `LangGraph`(inputs에 질의 원문 포함) + `router`·`_route_decision`·`clarify`·`answer`(chain) + `ChatGoogleGenerativeAI`(llm) + `RunnableSequence`·`PydanticOutputParser`. 이 측정으로 "루트 식별 + llm 스팬 + 비루트 chain 스팬" 단언을 설계.
- 회귀 대조군: `run_search("가장 저렴한 SUV 보여줘")`를 ON/OFF로 각각 실행 → 둘 다 `route: CLARIFY`, 동일 답변(트레이싱 유무가 검색 동작에 영향 없음).

**Verification performed (1차 패스):**
- `cd api && .venv/bin/python -m pytest tests/ -q` → **387 passed, 85 skipped**(패치 전후 재실행 확인, 새 게이트 테스트 1건이 기본 skip으로 늘어난 것 외 회귀 없음).
- 라이브 ON: `set -a; source .env; set +a` 후 `run_search("가장 저렴한 SUV 보여줘")` 실행 → 정상 응답(`route: CLARIFY`) 직후 `Client().list_runs()`로 신규 트레이스 5건(`answer`·`clarify`·`_route_decision`·`PydanticOutputParser`·`ChatGoogleGenerativeAI`) 확인 — 트레이스 실제 기록 확인(존재확인 아님, B4).
- 라이브 OFF 대조군: 같은 명령을 LangSmith env 미노출 상태로 재실행 → 동일한 라우팅 결과, 새 트레이스 없음(회귀 없음 + "파일에 있음≠켜짐" 실측 증거).
- `test_live_smoke_langsmith_tracing`(패치 3) 라이브 단독 실행 → PASSED. 같은 테스트를 env 미노출 상태로 재실행 → SKIPPED(게이트가 의도대로 작동).
- 정확한 `true` 값 요건(패치 1) 직접 실행 확인: `LANGCHAIN_TRACING_V2=1`·`=True`·`=""` 전부 `tracing_is_enabled()==False`, 정확히 `=true`일 때만 `True`.
- 부분 설정(패치 2) 직접 실행 확인: `TRACING_V2=true`+`API_KEY` 미설정 → `tracing_is_enabled()==True`(검색 응답엔 영향 없음, 백그라운드 스레드에서 401만 발생) — "켜진 것처럼 보이지만 안 됨" 확인.
- `git diff --stat`로 `api/app/**`·`docs/deployment-runbook.md`·`requirements.txt`/`pyproject.toml` 무변경 확인(코드 변경 0 AC 성립).

**Anything not completed:** 없음. 스펙의 세 AC·I/O 매트릭스 3행 전부 라이브 실행으로 확인됐다.

**Residual risks:**
- **Cloud Run 운영 반영은 사용자가 직접 해야 하는 작업이다** — LangSmith 대시보드(smith.langchain.com)에서 발급받은 실제 값을 Cloud Run 콘솔/`gcloud run services update`로 `encar-ai-api`(운영)·`encar-ai-api-dev`(개발) 두 서비스 환경변수에 등록해야 실제 운영 트레이싱이 켜진다. 이 리포는 `.dockerignore`가 `api/.env`를 컨테이너에서 제외하므로 로컬 `.env`만으로는 운영에 반영되지 않는다(왜 필요한지: FR51의 목적인 "사후 관측"이 운영 트래픽에도 적용되려면 이 등록이 필수).
- 이 세션의 실제 LangSmith API 키가 검증 과정에서 여러 차례 실호출됐다(무료 티어 월 5000 trace 한도 내에서 수 건 소비, 과금 아님).
- DW-613(Story 13.9 초안 엣지케이스 6건)은 LangSmith와 무관하지만 이번 diff의 `epic-13-context.md` 재캡파일에서 우연히 발견됐다 — Story 13.9 착수 시(13.8 완료 후) 함께 검토해야 한다.
- **DW-614가 지적한 G2 자기참조는 이 스토리가 아니라 Epic 13 전체의 위험이다** — Story 13.9 스펙을 쓸 때 "기준선 재캡처 → G2 재실행" 순서를 그대로 옮기면 에픽의 유일한 회귀 게이트가 무력화된다. 13.9 착수 전에 반드시 순서를 뒤집어 못박아야 한다.
- **이 회귀 테스트는 여전히 사람이 돌려야만 잡는다.** CI에 라이브·과금 테스트를 넣지 않는 것은 이 저장소의 의도된 표준이므로 그 절충 자체는 유지했지만, 그 대가로 `langchain` 계열 업그레이드가 계측을 끊어도 배포는 초록이다(DW-615). 검사 옆에 "안 보는 것"으로 명기해 두었다.
- 2차 리뷰 검증 과정에서 실제 LangSmith 키로 라이브 호출이 추가로 6회가량 발생했다(무료 티어 월 5000 trace 한도 내, 과금 아님).
- **이 스토리의 "검사가 잡는다"가 세 번째 패스에서야 성립했다.** 1차는 검사를 만들었고, 2차는 그 검사가 남의 트레이스로도 통과함을 잡았고, 3차는 2차가 "고쳤다"고 선언한 노드 스팬 단언이 실은 아무것도 안 지키고 있었음을 잡았다. 남는 교훈은 문서에 적을 게 아니라 이미 심어 뒀다 — 견본이 주장하는 규칙은 이제 `test_langsmith_env_contract.py`가 CI에서 검사한다. 반면 **트레이스가 실제로 기록되는지**는 여전히 사람이 라이브로 돌려야만 확인된다(DW-615).
- 3차 리뷰 검증 과정에서 라이브 호출이 추가로 8회가량 발생했다(무료 티어 한도 내, 과금 아님).
- DW-617(13.9 라우팅 사분면 충돌·맥락 재작성 경계 2건)이 신규 등재됐다 — DW-613·614와 함께 Story 13.9 스펙 작성 시 한꺼번에 봐야 한다. 세 항목 모두 트리거가 같은 지점(13.9 step-02 planning)을 가리킨다.
