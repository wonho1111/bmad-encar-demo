---
project_name: 'bmad-encar-demo'
user_name: 'Dnjsg'
date: '2026-07-15'
sections_completed: ['technology_stack', 'critical_implementation_rules', 'testing_rules', 'version_gotchas']
existing_patterns_found: 12
status: 'complete'
rule_count: 13
optimized_for_llm: true
---

# Project Context for AI Agents

_이 파일은 이 프로젝트에서 코드를 구현할 때 AI 에이전트가 반드시 따라야 할 **구현 규칙**을 담는다. LLM이 놓치기 쉬운 "당연하지 않은" 세부에 집중한다._

## ⚠️ 이 파일과 `docs/conventions.md`의 관계 (먼저 읽을 것)

**둘은 범위가 다르다. 값은 한쪽에만 산다.**

| | 무엇을 갖나 |
|---|---|
| **`docs/conventions.md`** | **크로스-파트 계약 = 값의 정본.** web·app·api·db 경계를 가로지르는 값(임베딩 차원·wire 네이밍·단위·응답/에러 포맷·ListingCard 필드·FR11·채팅 길이·접근 게이트·마이그레이션 정책). |
| **이 파일** | **구현 규칙 = 코드 쓰는 법.** 스택/버전·최신버전 함정·폴더 구조·테스트 층별 표준·반응형 무결성·브랜치. |

**규칙 2~8·10은 계약이라 값을 여기 복사하지 않는다 — `conventions.md`를 가리키기만 한다.**
이전엔 여기에 요약본을 뒀는데 **요약이 원본보다 늙어서** 틀린 값("4초 폴링"·"마이그 0001~0009"·"사진 필드 없음")이 에이전트에 주입됐다. 값을 한 군데만 두면 어긋날 자리가 없다. (2026-07-15 정리)

> **열린 일 장부는 `docs/tech-debt.md` 하나다** — "지금 뭐가 열려 있나"는 거기서 답한다.

---

## Technology Stack & Versions

**폴리글랏 모노레포** — 4개 파트가 한 레포에 공존:

| 파트 | 스택 | 핵심 버전 |
|---|---|---|
| `web/` | Next.js **App Router** + React + TypeScript(strict) + Tailwind | next 16.2.9 · react 19.2.4 · tailwindcss v4 · TS 5 |
| `api/` | FastAPI + LangGraph (AI 검색 전용 백엔드) | fastapi 0.137.1 · langgraph 1.2.4 · Python ≥3.10 · psycopg[binary,pool] · langchain-google-genai |
| `app/` | Flutter + Riverpod | Dart SDK ^3.12.2 · supabase_flutter 2.15 · flutter_riverpod 3.3 · http 1.6 |
| `supabase/` | Postgres + pgvector + RLS | 번호순 마이그레이션 (파일 목록이 정본 — 개수·범위를 문서에 적지 않는다) |

- **배포:** web=Vercel, api=Cloud Run(서울, 운영 `encar-ai-api`·개발 `encar-ai-api-dev`), app=수동. (Vercel은 api 번들 한도 초과로 폐기됨 — **api는 반드시 Cloud Run**.) 절차·순서는 `docs/deployment-runbook.md`.
- **AI 모델:** 생성 `gemini-3.1-flash-lite`(고정) · 임베딩 `gemini-embedding-001`.
- **⚠️ 최신버전 함정(옛 문법 금지):** Tailwind **v4**는 `tailwind.config.js`가 아니라 CSS `@theme` 기반(CSS-first) 설정. React **19**/Next **16 App Router**는 서버 컴포넌트가 기본이며 `'use client'`는 필요한 곳에만. **Next 16은 훈련데이터의 Next와 다르다** — web 작업 전 `node_modules/next/dist/docs/`를 먼저 읽는다(`web/AGENTS.md`).

---

## Critical Implementation Rules

### 1. 공유 계약은 `docs/conventions.md`가 단일 출처
web·app·api·db 경계를 가로지르는 값은 **전부 거기 정의돼 있다.** 코드보다 그 문서를 먼저 고친다. 이 파일과 어긋나면 **`conventions.md`가 맞다.**

### 2. 임베딩 차원 고정
→ **정본: `docs/conventions.md` §1.** 생성·저장·검색 전 구간이 일치해야 AI 검색이 동작한다. 값은 거기 있다.

### 3. 통신선(wire)은 `snake_case`, 코드 내부는 언어 관례
→ **정본: `docs/conventions.md` §2.** DB 컬럼·JSON 페이로드는 snake_case. TS/Dart 내부는 camelCase 매핑, Python은 그대로. ❌ JSON에 `sellerId` 직접 노출 금지(Supabase 반환과 불일치 → 매핑 버그).

### 4. 단위는 저장 단위로 고정, 단위 미명시 금지
→ **정본: `docs/conventions.md` §3.** `mileage`·`price`·`displacement`·`year`의 저장 단위와 자연어 정규화 규칙이 거기 표로 있다.

### 5. 응답·에러 공통 포맷 / `ListingCard` 계약
→ **정본: `docs/conventions.md` §4 + §4.1(계약 변경 체크리스트).**
- `ListingCard` **필드 목록을 여기 복사하지 않는다** — 증분에서 필드가 늘어나는 중이라 사본은 반드시 늙는다.
- 필드를 추가·변경할 땐 §4.1의 **락스텝 갱신 대상 4곳**(conventions → web `ListingCard.tsx` → api `schemas/ai.py` → app `listing.dart`)을 **동시에** 고친다. 실제 값까지 채울 땐 `listing_cards.py`의 `SELECT_COLUMNS`·`sql_guard.py`의 `ALLOWED_COLUMNS`도 함께.
- **계약-외 값 정규화**(빈 문자열 `image_url`·도메인 밖 `accident_status`·음수 count·bool 3상태)는 §4가 규정한다 — 값을 채우는 에픽이 렌더 코드에 반영할 것. `isValidListing`은 필수 필드만 보므로 **소비처가 스스로 방어**한다.

### 6. 보안은 RLS가 지킨다 — `service_role` 키 금지
→ 계약면(키 배치·anon 원칙)의 **정본: `docs/conventions.md` §5.** 구현 측 규칙:
- 클라이언트는 **anon key만**, 접근 제어는 전적으로 RLS. `service_role` 키는 **어디에도 두지 않는다**(이 때문에 "완전 계정 삭제"가 구조적으로 미구현 — `docs/tech-debt.md` #21).
- **`GEMINI_API_KEY`는 오직 `api/.env`에만.** web 브라우저 노출값은 `NEXT_PUBLIC_` 접두사 필수.
- env 누락은 `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화(어떤 변수가 비었는지 한국어로 throw). **`process.env.X!` 비-널 단언 금지.**
- AI SQL은 읽기전용 롤(`0006_readonly_role`) + `api/app/db/sql_guard.py`(sqlparse 토큰 검증)로 **이중 차단**. LLM이 만든 SELECT만 통과.
- **RLS는 행만 통제하고 컬럼은 통제하지 못한다.** 컬럼 차단은 GRANT 몫 — 둘 다 확인한다(§8).

### 7. 판매완료 비노출은 단일 규칙(FR11)
→ **정본: `docs/conventions.md` §6.** `status='sold'`는 구매자의 **모든 경로**에서 노출 안 됨. **새 조회 경로를 추가하면 §6의 강제 지점 목록에 반드시 함께 등록**한다(경로를 열고 필터를 잊는 것이 이 규칙의 유일한 실패 모드).

### 8. 채팅 무결성은 DB로 못박는다
→ 길이 계약의 **정본: `docs/conventions.md` §7.** 구현 측 규칙: `buyer_id <> seller_id` CHECK + BEFORE INSERT 트리거가 **클라가 보낸 `seller_id`를 매물 실소유자로 강제 덮어씀**(위조 차단). **UI 숨김에만 의존하지 않는다.**
- 현재 전송 방식(폴링 주기 등)은 **코드가 정본**이다 — `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `POLL_INTERVAL_MS`. 숫자를 문서에 적지 않는다(Epic 12가 Realtime으로 전환 예정).

### 9. web 폴더·경로 규칙
- 라우트 그룹: `app/(auth)` · `app/(user)` · `app/(admin)`. `components/{ai,auth,layout,listings,ui}`, `lib/{api,auth,supabase}`.
- import 별칭 `@/*` → `./src/*`. TypeScript **strict 켜짐**. UI 문자열은 한국어.

### 10. DB 변경은 번호순 마이그레이션으로만 추적
→ **정본: `docs/conventions.md` §9**(레시피 원칙·파일명 규약·in-place 수정 판정 규칙 (a)/(b)) + `docs/deployment-runbook.md`(적용 절차·게이트).
- 핵심만: `supabase/migrations/NNNN_이름.sql`, **전진(forward-only)**, **RLS 정책은 해당 테이블 마이그레이션에 동거**(별도 파일로 흩지 않음 — 예외는 관리자 전권 교차 정책 `0005_admin_policies.sql` 하나).
- **각 에픽 첫 마이그 스토리는 마이그레이션 게이트(CI) 통과가 DoD.**
- 스키마 설명(발표용): `docs/db-schema-guide.md`.

### 11. 브랜치·검증
`develop`에서 개발→동작 확인→`main` 병합. **`main`엔 검증된 코드만**(직접 개발 금지, 병합은 사용자 승인 시에만). 구현하면 **직접 실행·관찰**해 확인한다: web=브라우저 E2E, api=HTTP/curl, app=실폰 mobile-mcp. 참고: **mobile-mcp는 안드로이드 한글 입력 불가**(ASCII만) — ADBKeyBoard IME로 우회.

### 12. 테스트 규칙 (층별 — 근거: 각 프레임워크 공식 문서 + 테스트 피라미드)
하나로 뭉치지 않는다. 층마다 표준이 다르다:
- **api (FastAPI+LangGraph):** LLM을 fake로 교체해 pytest **결정론적 단위테스트**(라우팅·SQL가드·파라미터 추출). 실제 LLM 품질은 별도 **eval/live-smoke 트랙**(회귀 게이트, 매 커밋마다 돌리지 않음).
- **web (Next.js App Router):** **E2E(Playwright) 우선** — Next.js 공식이 async 서버 컴포넌트는 단위테스트 대신 E2E를 권장. 서버 컴포넌트 밖 순수 유틸(폼 검증 등)이 생기면 그것만 Vitest 단위테스트로 보강.
- **app (Flutter):** 핵심 Riverpod 컨트롤러 로직(폴링 상태 전이·필터 조합 등)은 `ProviderContainer.test`로 **순수 Dart 단위테스트 추가를 고려**(Supabase는 리포지토리로 감싸 fake 주입). 단순 화면은 실폰 E2E 유지. **트리거 = 컨트롤러 로직이 복잡해질 때.**
- **공통:** 구현 후 반드시 직접 실행·관찰. E2E-only는 표면이 작을 때의 **의도적 절충**이지 무기한 표준이 아님.
- ⚠️ **알아둘 것: 이 규칙은 현재 CI가 강제하지 않는다.** 워크플로는 `migration-gate.yml` 하나뿐이고 `paths:` 필터가 마이그·스크립트라, **api/web/app 테스트는 로컬에서 직접 돌려야 한다**(`docs/tech-debt.md` #29).

### 13. 반응형 UI 무결성 (D5 — 전 UI governing, web·app·관리자 공통)
가로폭이 줄면 **그리드 열 수로만 흡수**(4→2→1). 개별 컴포넌트 **내부 가로 배치(신뢰속성 행·meta·옵션 칩·버튼 라벨·필터 버튼)를 세로로 접지 않는다** — 텍스트가 길거나 공간이 부족해도 **줄바꿈 찌그러짐·2줄로 밀리는 버튼·라벨 어긋남 = 금기**. 공간 부족은 `truncate`("…")·"외 N"·열 축소로만 처리. 가장자리 카드 부분 클리핑만 허용(모바일에서 살짝 가려지는 정도). **레이아웃 어긋남·깨짐 = 절대 금기.** 관리자 화면도 예외 없음.
(원문: `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md` D5 · `EXPERIENCE.md` 브레이크포인트 ≥1100=4열·640~1099=2열·<640=1열)

---

## 문서 지도 (어디서 답을 찾나)

| 질문 | 파일 |
|---|---|
| 지켜야 하는 **계약**(경계 값)은? | `docs/conventions.md` ← **정본** |
| 지금 뭐가 **열려 있나**? | `docs/tech-debt.md` ← **유일한 대장** |
| **왜** 그렇게 정했나? | 각 에픽 회고 · `_bmad-output/implementation-artifacts/deferred-work.md`(동결·경위 전용) |
| **배포**·마이그 적용·롤백은? | `docs/deployment-runbook.md` |
| 역할별 **내비/IA** 규칙은? | `_bmad-output/planning-artifacts/nav-ia-rules.md` |
| 현재 **스펙**(증분)은? | `_bmad-output/planning-artifacts/`의 `*-increment-2026-07-12.md` · `prds/prd-*-2026-07-11/` |

---

## Usage Guidelines

**AI 에이전트용:**
- 코드 구현 전 이 파일을 먼저 읽는다. 모든 규칙을 그대로 따른다.
- **경계 값이 필요하면 `docs/conventions.md`를 편다** — 이 파일엔 값이 없다(의도된 것이다).
- 애매하면 더 보수적인 쪽을 택한다. 새 패턴이 생기면 이 파일을 갱신한다.

**사람용:**
- 이 파일은 lean하게 유지한다(에이전트 컨텍스트 효율). **여기에 계약 값을 다시 적지 않는다** — 사본은 반드시 늙는다.
- 계약이 바뀌면 `docs/conventions.md`를 먼저 고친다. 이 파일은 스택·구현 규칙이 바뀔 때만.

_Last Updated: 2026-07-15 (conventions 중복 요약 제거 — 요약이 원본보다 늙어 틀린 값이 주입되던 구조를 끊음)_
