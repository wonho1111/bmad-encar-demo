# 프로젝트 설정 — project.md (bmad-encar-demo)

> auto-epic / auto-pipeline 등 제네릭 스킬이 이 파일을 프로젝트 상수의 출처로 읽는다.
> ⚠️ 비밀값 금지. 토큰·키·DB 비밀번호는 `.env`/`.env.local`에 두고 여기엔 위치만 가리킨다.
> 멀티패키지(web/ + api/ + app/). auto-epic은 **web/**(Vercel)를 다룬다. api(Cloud Run)·app(Flutter)는 별도 배포.

---

## 배포 (Deployment)

- **서비스**: Vercel (web). 추가로 api → Google Cloud Run, app → 수동(Flutter).
- **project ID**: prj_ilOPzABNV6jPP848AeTGMQOhpK5J
- **team ID**: team_HMqrwcpM05d59YDz98oYQ2U2
- **연결 파일 우선순위**: 저장소에 `.vercel/project.json`이 있으면 그 값을 우선.
- **배포 검증 방식**: Vercel MCP로 state===READY + 빌드 로그 확인.
- **ID 불일치 시**: `list_projects`/`list_teams`로 재확인.

## 백엔드 / DB 서비스

- **DB/백엔드 서비스**: Supabase(PostgreSQL + pgvector), project ref `psrnsasxpkpwqdukjdmt`. 비밀키는 `.env`.
- **API**: api/ = FastAPI(LangGraph, Gemini, pgvector) → Cloud Run(asia-northeast3). 키는 `.env`.
- **LLM**: Google Gemini. 키·모델은 `.env`. 값 미기재.

## 앱 구조 / 명령

- **구조**: 멀티패키지 — **web/**(Next.js 16, App Router) + api/(FastAPI) + app/(Flutter).
- **패키지 매니저**: npm (web), pip (api), pub (app)
- **dev**: (web) `npm run dev`  →  `http://localhost:3000`  (dev 포트: 3000)
- **build**: (web) `npm run build`
- **lint**: (web) `npm run lint`
- **테스트**: 웹=Playwright MCP / API=curl·HTTP / 모바일=Android 에뮬레이터(mobile MCP)

## 산출물 경로 (BMAD)

- **출력 루트**: `_bmad-output`
- **기획 산출물**: `_bmad-output/planning-artifacts`
- **구현 산출물**: `_bmad-output/implementation-artifacts`
- **브레인스토밍**: `_bmad-output/brainstorming`
- **스프린트 상태**: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- **에픽 정의**: `_bmad-output/planning-artifacts/epics.md`
- **스토리 파일**: `_bmad-output/implementation-artifacts/{story_key}.md`

## 산출물 자동 첨부 글롭 (discord-remote.md 7절)

- `_bmad-output/**`
- `docs/**`
> 코드·node_modules·빌드 산출물 제외.

## 브랜치 전략

- **개발**: develop  (commit & push 허용; develop push = Vercel preview + Cloud Run dev 자동 배포)
- **배포**: main  (검증된 코드만. 병합으로만; main = production)

## 커밋 컨벤션

- 형식: `type(scope): 한국어 설명`
- 푸터: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 오케스트레이터

- **mode**: gated  # PRD 직후·아키텍처 직후 2번만 사람 승인

## 자동화 운영 정책 (Phase 1~4 동안 / Phase 5에서)

- **DB(자동화 중)**: 운영 Supabase 연결 제외. 임시는 docker compose(가용 시 local postgres) 또는 JSON/메모리 폴백.
- **배포(자동화 중)**: 제외(로컬 E2E만). 배포·배포 E2E는 BMAD 종료 후 Phase 5에서.
