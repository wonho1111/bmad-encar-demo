# CLAUDE.md — bmad-encar-demo

작업 표준(답변 방식·코딩 원칙·커밋/브랜치/테스트 규칙 등)은 상위 `workspace/CLAUDE.md`를 **자동 상속**한다.
이 파일엔 **이 프로젝트 고유의 값·구조·특이사항**만 둔다.

## 개요
- 엔카·헤이딜러 류 **중고차 직거래 서비스**의 핵심 기능 최소 구현 (데모/과제용).
- 상세 기획: `docs/idea.md` · 기술 연구: `_bmad-output/planning-artifacts/research/`
- 산출물: `_bmad-output/` (기획 `planning-artifacts/`, 구현 `implementation-artifacts/`)

## 스택 · 구조 (멀티패키지)
- **web/**: Next.js 16 (App Router) + React 19 + TS + Tailwind v4. npm. `npm run dev` → `:3000`, `npm run build`, `npm run lint`.
- **api/**: FastAPI + LangGraph + Gemini + pgvector. pip.
- **app/**: Flutter (모바일). pub.
- **DB**: Supabase (PostgreSQL + pgvector), project ref `psrnsasxpkpwqdukjdmt`. 비밀키는 `.env`.
- **LLM**: Google Gemini (임베딩 포함). 키·모델은 `.env`/`.env.local`.

## 배포 (3원 배포 — 이 프로젝트의 핵심 특이점)
- **web → Vercel**: project ID `prj_ilOPzABNV6jPP848AeTGMQOhpK5J`, team ID `team_HMqrwcpM05d59YDz98oYQ2U2`. `develop` push = preview, `main` = production. `.vercel/project.json` 있으면 그 값 우선.
- **api → Google Cloud Run** (Vercel 250MB 번들 한도로 컨테이너 전환). 서울 리전 `asia-northeast3`. `develop` push = 개발 서비스 `encar-ai-api-dev` 자동 배포, `main` = 운영 `encar-ai-api`.
- **app → Flutter 수동 배포**.
- **배포 = `develop` push** (수동 `gcloud run deploy`·`vercel deploy` 금지): api를 바꿔도 `develop` push 한 번에 web preview + api dev가 **둘 다 자동 배포**된다. 끝나면 preview 웹을 열어 E2E. 운영 반영 = `main` 병합, **사용자 명시 승인 시에만**.

## 테스트 도구
- **web** = Playwright MCP (브라우저 E2E) · **api** = `curl`/HTTP · **app(모바일)** = Android 에뮬레이터 + `mobile-mcp`, 반복 시나리오는 Maestro. (Expo Go 사용 안 함 — Flutter 불가. iOS 확인은 macOS 필요.)
- 배포/로그 확인 = Vercel MCP.
- **포트**: web `:3000`, api `:8000`.

## 특이사항 / 함정
- 커밋 푸터: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- 사용자 직접 처리 항목: `.env` 실제 키값(Supabase 키·`GEMINI_API_KEY`) 입력, Android Studio·에뮬레이터 설치, MCP 등록 승인, iOS 확인용 Mac.
