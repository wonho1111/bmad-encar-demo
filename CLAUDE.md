# CLAUDE.md — bmad-encar-demo

이 파일은 `bmad-encar-demo` 프로젝트에 대한 Claude Code 작업 지침입니다.
상위 `workspace/CLAUDE.md`의 지침(용어 설명 방식, 한국어 답변 등)을 **그대로 상속**하며,
아래는 이 프로젝트에만 추가로 적용되는 규칙입니다.

## 프로젝트 개요

- 엔카·헤이딜러 류 **중고차 직거래 서비스**의 핵심 기능 최소 구현 (데모/과제용).
- 상세 기획: `docs/idea.md`
- 기술 연구: `_bmad-output/planning-artifacts/research/`
- 스택: Next.js(웹) · Flutter(앱) · FastAPI+LangGraph(API) · Supabase/PostgreSQL+pgvector(DB) · Gemini(LLM·임베딩)

## 작업 지침

### 1. 코드 수정 시 설명 첨부
- 코드를 추가·수정할 때마다 **무엇을·왜 바꿨는지** 쉬운 말로 요약 설명을 함께 제공한다.
- 비전공자도 이해할 수 있게 한 줄 요약 + 필요한 경우 짧은 보충. 핵심 로직에는 주석도 적절히 단다.
  - *주석(comment)*: 코드 안에 사람이 읽으라고 남기는 설명 문구.
- 설명을 쓴 뒤 "비전공자가 이것만 읽고 '무엇을·왜' 바꿨는지 이해되는가?"를 스스로 한 번 검토하고, 막히면 비유나 한 줄을 더 보탠다.

### 2. Git 관리 (커밋 시점)
- 의미 있는 단위가 끝나면 **적절한 단계에서 커밋**한다. (기능 단위, 스토리 단위 등)
  - *커밋(commit)*: 변경 내용을 git 이력에 한 묶음으로 기록하는 것.
- 한 번에 너무 많은 변경을 몰아 커밋하지 않는다. 커밋 메시지는 변경 의도를 한국어로 명확히 적는다.
- 사용자가 명시적으로 요청하거나 위 기준에 해당할 때 커밋하며, 임의로 push 하지 않는다.

### 3. Git 브랜치 전략
- **개발용 브랜치(develop)** 에서 개발하고, 검증 후 **배포용 브랜치(main)** 에 병합한다.
  - *브랜치(branch)*: 코드 이력의 갈래. 작업을 분리해 안전하게 개발하기 위함.
  - *병합(merge)*: 한 브랜치의 변경을 다른 브랜치로 합치는 것.
- 흐름: `develop`에서 작업·커밋 → 동작 확인 → `main`으로 병합.
- 배포용 `main`에는 동작이 검증된 코드만 올린다. (직접 개발 금지)
- 아직 git 저장소가 없으면, 구현 착수 시점에 `git init` 후 위 두 브랜치를 구성한다.
- **Vercel 연동(web)**: 운영(Production) 브랜치 = `main`, 그 외 브랜치(=`develop` 포함) = 미리보기(preview) 배포. `develop` push 시 preview 배포가 자동 생성된다.
- **Cloud Run 연동(api)**: api(`api/`)는 Vercel이 아니라 **Google Cloud Run**에 배포한다(Vercel은 의존성 번들 250MB 한도로 실패 → 표준 컨테이너로 전환). GitHub 연동으로 **`develop` push 시 개발 서비스 `encar-ai-api-dev`가 자동 배포**되고, `main`은 운영 서비스 `encar-ai-api`(사용자 승인 후 병합 시). 서울 리전(`asia-northeast3`).
- **배포 = `develop` push** (수동 `gcloud run deploy`·`vercel deploy` 하지 말 것): api 코드를 바꿨으면 `develop`에 push만 하면 web preview(Vercel)와 api 개발(Cloud Run)이 **둘 다 자동 배포**된다. 두 배포가 끝나면 **preview 웹을 열어 개발 브랜치 작업분을 E2E 테스트**한다(§6). 운영 반영은 `main` 병합으로만, **병합은 사용자 명시 승인 시에만**.
- **`/auto-epic` 작업 예외**: 자동 개발(아래 7번) 중 배포-테스트 목적의 **`develop` push는 허용**한다. 단 `main` push·병합은 여전히 금지(사용자 명시 요청 시에만).

### 4. 초기 DB 구성은 단순하게
- 초기 데이터베이스 스키마는 **기능 추가·수정이 쉽도록 간단하게** 설계한다.
  - *스키마(schema)*: 테이블·컬럼 등 DB의 구조 정의.
- 처음부터 과도하게 정규화·세분화하지 않고, 핵심 테이블 위주로 시작해 점진적으로 확장한다.
  - *정규화(normalization)*: 데이터 중복을 줄이려 테이블을 쪼개는 설계 기법.
- 스키마 변경은 마이그레이션으로 관리해 추적 가능하게 한다.
  - *마이그레이션(migration)*: DB 구조 변경을 버전처럼 기록·적용하는 작업.

### 5. Epic 종료 시 "직접 해야 할 일" 고지
- 각 **에픽(epic)** 이 끝날 때마다, 사용자가 **직접 처리해야 하는 항목**을 모아서 명확히 알려준다.
  - *에픽(epic)*: 여러 사용자 스토리를 묶은 큰 기능 단위.
- 고지 대상 예시:
  - 테스트·동작 확인(직접 실행해 봐야 하는 시나리오)
  - 외부 접근 설정: API 키 발급, 환경변수 입력, OAuth/도메인 설정 등
    - *환경변수(environment variable)*: 코드 밖에서 주입하는 설정값(키·비밀번호 등).
  - 배포 관련 설정(Vercel·Cloud Run·Supabase 콘솔에서 직접 해야 할 것)
  - 결제·할당량 등 계정 단위로 사용자만 할 수 있는 작업
- 항목별로 "왜 필요한지 + 어디서 하는지"를 한 줄로 덧붙인다.

### 6. 구현 단계 테스트 방식
- **원칙**: 코드를 구현하면 가능한 한 Claude가 **직접 실행·관찰**해 동작을 확인한 뒤 보고한다. 사람이 매번 수동으로 띄워보지 않아도 되게 한다. 실패하면 출력 로그와 함께 **사실대로** 보고한다.
- **실행 방식**: dev 서버는 백그라운드 태스크로 띄운다 (Bash `run_in_background`). 기동 확인(health check) 후 테스트하고, 작업이 끝나면 프로세스를 정리한다.
  - *백그라운드 태스크(background task)*: 명령을 띄워둔 채 다른 작업을 이어가는 비동기 실행.
  - *health check*: 서버가 정상 기동했는지 응답으로 확인하는 점검.
- **포트 규칙**: 웹 `:3000`, API `:8000` (실제 실행 스크립트 확정 시 이 값으로 갱신).
- **웹 (Next.js)**: **Playwright MCP**로 실제 브라우저를 열어 화면을 클릭·입력하며 E2E 자체 테스트한다.
  - *MCP(Model Context Protocol)*: AI가 외부 도구·서버와 연결되는 표준 규약.
  - *Playwright*: 실제 브라우저(Chromium 등)를 자동 조작하는 테스트 도구. *E2E(End-to-End)*: 사용자가 실제로 쓰는 흐름 전체를 통과시키는 테스트.
- **백엔드 (FastAPI)**: 브라우저가 아니라 **HTTP로** 검증한다 — `curl`/HTTP 직접 호출, 또는 웹 클라이언트를 통한 E2E.
- **모바일 (Flutter, Epic 7)**: **Android 에뮬레이터 + `mobile-mcp`** 로 네이티브 자체 테스트하고, 반복 시나리오는 **Maestro**로 보완한다. 가벼운 UI 점검은 Flutter 웹 빌드 + Playwright로도 가능. **Expo Go는 사용하지 않는다**(React Native 전용이라 Flutter엔 불가). iOS 확인은 macOS가 필요해 별도 기기로 한다.
  - *에뮬레이터(emulator)*: PC에서 가상의 스마트폰을 띄워 앱을 돌리는 도구. *mobile-mcp*: 에뮬레이터/실기기를 자동 조작하는 모바일판 MCP(Playwright MCP의 모바일 버전 격). *Maestro*: 모바일 UI 흐름을 간단한 스크립트로 작성·반복 실행하는 테스트 도구.
- **사용자 직접 처리 항목** (왜 / 어디서):
  - `.env` 실제 키값 입력 (Supabase 키, `GEMINI_API_KEY`) — 코드 밖 비밀값이라 사용자만 넣을 수 있음 / 각 환경의 `.env` 파일.
  - Android Studio·에뮬레이터 설치 — 모바일 자체 테스트 실행 기반 / 로컬 PC.
  - Playwright·mobile MCP 등록 승인 — MCP 최초 연결 시 승인 프롬프트 / Claude Code.
  - iOS 확인용 Mac·클라우드 기기 — iOS 시뮬레이터는 macOS 전용 / 별도 기기.

### 7. 에픽 자동 개발 (`/auto-epic`)
- 사용자가 **`/auto-epic [에픽번호]`** 명령(또는 "에픽 자동 돌려" 류 키워드)으로 호출하면, **`.claude/skills/auto-epic/SKILL.md` 절차를 그대로 따른다.**
  - *오케스트레이터(orchestrator)*: 여러 서브에이전트를 순서대로 부려 작업을 조율하는 진행자.
- 한 번에 **최대 한 에픽**만 자동 진행하고, 끝나면 멈춰 **사용자가 최종 검증**한다. 다음 에픽 자동 진행 금지.
- 스토리마다 새 서브에이전트로 BMad 공식 절차(`bmad-create-story`→`bmad-dev-story`→`bmad-code-review`)를 돌리고, 에픽 종료 시 로컬 Playwright + `develop` preview 배포(Vercel MCP 로그)로 자체 검증한다.
- **실행은 auto 권한 모드 권장** — 무인 진행에 필요(plan 모드는 실행 불가, acceptEdits는 Bash/MCP마다 승인 요구).
  - *권한 모드(permission mode)*: 도구 실행을 얼마나 자동 승인할지 정하는 설정. shift+tab으로 전환.

## 참고
- 상위 `workspace/CLAUDE.md`의 **용어 설명 규칙**(영어 약자·기술/도메인/업무 용어를 처음 등장 시 한 줄로 설명)을
  본 프로젝트의 모든 답변에 동일하게 적용한다.
