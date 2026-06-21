# Story 4.7: AI 검색 UI (FR12)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 구매자,
I want 채팅창에 자연어 한 문장으로 매물을 찾고 싶다,
so that 필터를 일일이 고르는 대신 대화하듯 검색하고, 후속 질문("그 중 더 싼 거")까지 한 입력창에서 이어간다.

> **이 스토리의 본질 — "지금까지 백엔드(4.1~4.6)가 완성한 `/ai/search`를 마침내 사람이 쓰는 화면에 연결한다."** 4.1~4.6에서 만든 것: 인증(Bearer JWT)·라우터(A/B/C)·경로 A(Text-to-SQL)·경로 B(문서 RAG)·경로 C(가드)·answer 조립·멀티턴 맥락화. 그 결과 `POST /ai/search`는 `{query, context}`를 받아 `{answer, listings[]}`를 돌려준다. **4.7은 백엔드를 한 줄도 안 바꾼다.** 웹에 (1) AI 채팅 화면(`(user)/ai`), (2) `/ai/search`를 호출하는 클라이언트 함수(`lib/api/aiSearch.ts`), (3) 대화를 화면에 쌓고 **직전 맥락을 클라이언트 상태로 보관해 후속 질의에 `context`로 동봉**하는 채팅 컴포넌트(`components/ai/ChatAssistant.tsx`)를 추가하는 일이다. 핵심은 (a) **Supabase 세션 토큰을 꺼내 `Authorization: Bearer`로 보내는 인증 배선**, (b) **멀티턴 맥락을 서버가 아니라 클라이언트(React 상태)에만 두는 것**(architecture 무상태 전제 — 새로고침하면 대화 초기화), (c) **답변 텍스트 + 매물카드(`ListingCard` 재사용, 사진 없음)를 렌더하고 카드 클릭 시 `/listings/[id]` 상세로 이동**하는 것이다.
>
> *AI 채팅 어시스턴트: 자연어 질의를 받아 답변과 매물 목록을 돌려주는 대화형 검색 화면.*
> *멀티턴(multi-turn): 한 번 묻고 끝이 아니라 앞 대화를 이어 후속 질문을 주고받는 대화.*
> *클라이언트 상태(client state): 서버가 아니라 브라우저 메모리(React useState)에만 두는 데이터 — 새로고침하면 사라진다.*

## Acceptance Criteria

1. **(AC1 — AI 채팅 화면 진입·렌더, FR12)** `web`에 AI 채팅 화면(`/ai`, `(user)/ai/page.tsx`)이 생긴다. 로그인 사용자(구매자·판매자 공통)가 접근 가능하고, 비로그인은 `proxy.ts`가 `/login`으로 1차 차단한다(`PROTECTED_PREFIXES`에 `/ai` 추가). 화면 상단은 공용 `AppHeader`(역할·이메일·로그아웃), 본문은 **대화 기록 영역 + 질의 입력창(텍스트 + 전송 버튼)** 으로 구성된다. 홈(`/`)에 "AI 검색" 진입 링크를 추가해 도달 가능하게 한다. [Source: epics.md#Story 4.7(549-556); architecture.md(350)]
2. **(AC2 — 자연어 질의 → `/ai/search` 호출 → 답변·매물카드 렌더, FR12 핵심)** 입력창에 자연어 질의를 넣고 전송하면 `POST {API_BASE}/ai/search`를 호출(`lib/api/aiSearch.ts`)해 `{answer, listings[]}`를 받아, **자연어 답변 텍스트**와 **매물카드 목록**을 대화 흐름에 렌더한다. 매물카드는 기존 `ListingCard`(`components/listings/ListingCard.tsx`)를 그대로 재사용한다 — **텍스트 필드(제조사·모델·연식·가격·주행거리·지역)만 표시, 사진 없음**(AC: "매물카드는 텍스트 필드만 표시"). `listings`가 0건이면 답변 텍스트만 보이고(서버가 FR17대로 빈손 대신 안내문을 줌) 카드 영역은 비운다. [Source: epics.md#Story 4.7(551,556); api/app/schemas/ai.py SearchResponse]
3. **(AC3 — 매물카드 클릭 → 상세 이동)** 답변에 딸린 매물카드를 누르면 **해당 매물 상세(`/listings/[id]`)로 이동**한다. `ListingCard`가 이미 `<Link href={`/listings/${id}`}>`로 감싸 이 동작을 제공하므로 **재사용만으로 충족**(별도 핸들러 금지 — 재발명 방지). [Source: epics.md#Story 4.7(553-555); ListingCard.tsx:24-27; listings/[id]/page.tsx 존재(3-2 done)]
4. **(AC4 — 멀티턴 맥락을 클라이언트가 보관·동봉, FR18)** 클라이언트가 **직전 대화(사용자 질의/어시스턴트 답변)를 React 상태로 보관**하다가, 후속 질의를 보낼 때 `context`로 동봉한다 — `context`는 `[{role:"user"|"assistant", content:string}]` 형태, **최대 12턴**(초과분은 최근 12턴만 잘라 보냄 — 서버 422 회피), 각 content 최대 2000자(초과 시 안전 절단). 빈 대화(첫 질의)는 `context` 미동봉(또는 `[]`)로 단일턴 동작. **서버·DB에 대화를 저장하지 않으며, 새로고침/페이지 이탈 시 대화가 초기화**된다(맥락은 클라이언트 상태에만 존재 — 무상태). [Source: architecture.md(52,398); 4-6 story(context 스키마 12턴·2000자); api/docs/ai-demo-queries.md(68)]
5. **(AC5 — 인증·로딩·에러 상태 처리)** `/ai/search`는 인증 필수(`Authorization: Bearer <supabase access_token>`)다. 클라이언트는 **Supabase 브라우저 클라이언트에서 현재 세션의 `access_token`을 꺼내** 헤더에 실어 보낸다(`lib/supabase/client.ts` 재사용). 요청 중에는 **로딩 표시**(전송 버튼 비활성·"검색 중…" 등), 실패 시(네트워크·401·400·500) **사용자에게 한국어 에러 안내**를 대화에 보여준다(조용한 실패 금지 — 4.x fail-loud 계승). 빈 질의(공백만)는 전송하지 않는다(클라 1차 검증). [Source: architecture.md(292); auth.py; main.py 공통 에러 포맷]
6. **(AC6 — E2E 자체 검증)** dev 서버(:3000)를 백그라운드로 띄우고 health check 후 **Playwright MCP로 실제 브라우저에서 AI 채팅 흐름을 E2E 점검**한다 — (a) `/ai` 진입·화면 렌더, (b) 질의 입력→전송→답변·매물카드 렌더, (c) 카드 클릭→`/listings/[id]` 상세 이동, (d) 후속 질의 시 직전 맥락이 `context`로 동봉되는지(네트워크 요청 본문 확인). API(:8000)가 키/DB로 실제 응답 가능하면 라이브로, 못 띄우면 그 사실을 보고하고 **API 호출 계약(URL·헤더·body·context 동봉)을 UI 단위/네트워크 가로채기로 검증**한다. lint·typecheck·build 통과. [Source: CLAUDE.md §6; 4-6 검증 방식 계승]

### 범위 밖 (이 스토리에서 구현하지 않음 — 과잉구현 금지)

- ❌ **백엔드(`/ai/search`·그래프·노드·스키마) 변경** → 4.1~4.6 done. 4.7은 **웹 UI만**. API는 한 줄도 안 고친다(호출만). `context` 스키마(12턴·2000자)는 4.6 확정값을 **그대로 따라 보내기만** 한다.
- ❌ **대화 이력 DB 저장·세션 영속·서버 보관** → architecture "무상태 전제·AI 대화 전용 테이블 없음" 위배. 맥락은 **클라이언트 React 상태에만**(AC4). 새 마이그레이션·새 테이블·서버 캐시 절대 금지.
- ❌ **스트리밍 응답(SSE/토큰 스트림)** → `/ai/search`는 단발 JSON 응답이다. 데모는 요청→응답 1회로 충분. 스트리밍 UI 미구현.
- ❌ **새 매물카드 컴포넌트 제작** → `ListingCard` 재사용(재발명 금지). 카드 클릭 상세 이동도 `ListingCard`의 기존 `<Link>`로 충족(AC3).
- ❌ **AI 통합 검증 매트릭스(SM3/CM1/CM2)** → 4.8. 4.7은 화면이 동작함을 E2E로 확인하는 선까지.
- ❌ **TanStack Query 도입** → architecture가 폴링·채팅(Epic 5)용으로 언급하나, AI 검색은 단발 호출이라 `useState`+`fetch`로 충분. 새 의존성 추가 금지(아래 "라이브러리" 참조). dev 판단으로 도입 시 근거를 남길 것.
- ❌ **Flutter 앱 AI 검색**(7-2) → 별도 에픽. 단, `lib/api/aiSearch.ts`의 `context` 형태·헤더 규약은 Flutter도 따를 단일출처이니 ai-demo-queries.md(68)와 어긋나지 않게 한다.

## Tasks / Subtasks

- [x] **Task 1 — API base URL 환경변수 + `lib/api/aiSearch.ts` 호출 함수** (AC: 2, 5)
  - [x] 1.1 `web/.env.local`에 `NEXT_PUBLIC_API_BASE_URL`(`http://localhost:8000`) 추가 + 주석으로 의미·배포 교체 안내.
  - [x] 1.2 `web/src/lib/api/aiSearch.ts` 신규 — `searchAi({query, context, accessToken})`. POST + Bearer 헤더 + body `{query, context?}`. 200 파싱·비200은 `{error:{code,message}}` 읽어 한국어 Error throw(상태코드 폴백 포함). 네트워크 실패도 한국어 변환.
  - [x] 1.3 타입 — `SearchResult`·`ConversationTurn` 정의, `ListingCardData`는 ListingCard에서 import(중복 금지). base URL 누락 시 한국어 가드.
  - [x] 1.4 base URL 끝 슬래시 정규화(`replace(/\/+$/,'')`)로 이중 슬래시 방지.

- [x] **Task 2 — AI 채팅 컴포넌트 `components/ai/ChatAssistant.tsx`** (AC: 1, 2, 3, 4, 5)
  - [x] 2.1 `'use client'` + `useState`(messages·input·loading·error). 대화는 클라이언트 상태에만(무상태).
  - [x] 2.2 전송 핸들러: trim·빈값/중복 차단 → `getSession()` access_token → `buildContext(messages)` → `searchAi()` → assistant 턴 추가.
  - [x] 2.3 `buildContext`: 현재 query는 `query`로(중복 금지), 직전까지를 context로. 최근 12턴·content 2000자 절단. assistant content = answer 텍스트만.
  - [x] 2.4 렌더: user/assistant 말풍선 + 매물카드(`ListingCard` 재사용). 로딩 "검색 중…"·버튼 disabled. 에러 role="alert".
  - [x] 2.5 입력 폼 `<form onSubmit>` + input + 전송 Button(재사용). Enter 전송·로딩 중 disabled.

- [x] **Task 3 — AI 채팅 페이지 `(user)/ai/page.tsx` + 라우트 보호 + 진입 링크** (AC: 1)
  - [x] 3.1 `(user)/ai/page.tsx` 신규 — 서버 컴포넌트, search/page.tsx 패턴(AppHeader·role) + `<ChatAssistant />`.
  - [x] 3.2 `proxy.ts` PROTECTED_PREFIXES에 `/ai` 추가 + 주석.
  - [x] 3.3 홈에 "AI 검색" 링크 추가(buttonClasses 재사용).

- [x] **Task 4 — 자체 테스트(E2E + lint/build)** (AC: 6)
  - [x] 4.1 `npx tsc --noEmit` 0·`npx eslint` 0·`npm run build` 성공(/ai 라우트 등록 확인).
  - [x] 4.2 web dev(:3001 — :3000 점유로 자동 이동)·API(:8000, 실키·실DB) 백그라운드 기동 + health 200. CORS_ORIGINS에 :3001 추가해 재기동.
  - [x] 4.3 Playwright MCP E2E(로그인 seller-seed) — /ai 렌더, 단일턴 라이브 3건(흰색 SUV 2건·서울 경차 5건·패밀리카 5건) answer+카드, 카드 클릭→/listings/[id] 상세 이동, 멀티턴 context 동봉 request body 2회 하드 캡처, 에러 UI·롤백·새로고침 초기화 확인.
  - [x] 4.4 dev·API 프로세스 정리.

- [x] **Task 5 — 보고·산출물 정리** (AC: 전체)
  - [x] 5.1 Completion Notes 기록.
  - [x] 5.2 File List 기록.

## Dev Notes

### ⚠️ 결정적 함정 — 반드시 숙지

**함정 #1 — Next.js 16은 당신이 아는 그 Next.js가 아니다(web/AGENTS.md).** `web/AGENTS.md`가 명시: "This is NOT the Next.js you know — APIs, conventions, file structure가 학습데이터와 다를 수 있다. 코드 작성 전 `node_modules/next/dist/docs/`의 관련 가이드를 읽어라." 특히 `middleware.ts`→`proxy.ts` 개명(이미 적용됨), `searchParams`/`cookies()` 비동기(await 필수), 클라이언트 컴포넌트 `'use client'` 규칙. **기존 web 코드(`search/page.tsx`, `SellForm.tsx` 등 client 컴포넌트)의 실제 패턴을 그대로 따르고**, 불확실하면 해당 docs를 먼저 읽는다. 학습데이터의 옛 Next.js 관행으로 추측 코딩 금지.
[Source: web/AGENTS.md; proxy.ts:1-11; search/page.tsx:58]

**함정 #2 — 멀티턴 맥락을 서버에 보내 "기억"시키려 하지 마라(무상태 위배 = FR18·architecture).** 서버 `/ai/search`는 **매 요청 독립 처리**한다 — 직전 대화는 서버가 모른다. 멀티턴은 **클라이언트가 직전 대화를 `context`로 매번 동봉**해서만 성립한다(4.6이 이 `context`를 읽어 질의를 재작성). 그러니 4.7 클라이언트는 (a) 대화를 React 상태로 쌓고, (b) 후속 질의마다 직전 턴들을 `context`로 직렬화해 보낸다. **localStorage·쿠키·서버 저장 금지** — "새로고침하면 대화 초기화"(FR18 둘째 AC)가 정상 동작이다. 이걸 어기고 영속화하면 무상태 전제를 깬다.
[Source: architecture.md(52,398); 4-6 story 함정 #1; ai-demo-queries.md(67)]

**함정 #3 — `context` 스키마(12턴·2000자)를 클라이언트에서 어겨 422를 자초하지 마라.** 서버는 `context`를 `list[ConversationTurn] | None`(최대 12턴, 각 content min 1·max 2000자)로 **강제**한다(4.6). 대화가 길어지면 클라이언트가 **최근 12턴만 잘라** 보내야 한다(전체를 보내면 13턴째부터 422 validation_error). content가 2000자를 넘으면 안전 절단. role은 정확히 `"user"`/`"assistant"`만(다른 값 422). 빈 `content`(공백만) 금지 — 어차피 전송 전 trim·빈값 차단. **이 규약의 단일출처는 `api/docs/ai-demo-queries.md`(68)와 `api/app/schemas/ai.py`** — 거기 값을 그대로 따른다(드리프트 금지).
[Source: api/app/schemas/ai.py:29-49; ai-demo-queries.md(68); 4-6 story AC1]

**함정 #4 — 매물카드를 새로 만들지 마라. `ListingCard` 재사용 = 카드 클릭 상세 이동이 공짜로 따라온다.** `components/listings/ListingCard.tsx`는 **목록·AI결과가 공유하도록 설계됐다**(파일 상단 주석: "구매자 목록(FR9)·향후 AI 검색 결과(Epic 4)가 공유"). 이미 `<Link href={`/listings/${id}`}>`로 감싸 **AC3(카드 클릭→상세 이동)을 그냥 충족**한다. `ListingCardData` 타입(id·manufacturer·model·year·price·mileage·region 7필드)도 API `SearchResponse.listings`(`schemas/ai.py`의 `ListingCard` 7필드)와 **정확히 일치**한다 — 그대로 매핑된다. 새 카드·새 onClick·새 타입 만들면 재발명·드리프트다.
[Source: ListingCard.tsx:1-40; api/app/schemas/ai.py:60-69; listings/[id]/page.tsx 존재]

**함정 #5 — 인증 토큰을 빼먹으면 100% 401이다.** `/ai/search`는 `get_current_user`로 보호된다 — **유효한 Bearer 토큰 없으면 401**. 클라이언트는 **Supabase 브라우저 클라이언트의 세션에서 `access_token`을 꺼내** `Authorization: Bearer <token>`로 보내야 한다. `const supabase = createClient(); const { data: { session } } = await supabase.auth.getSession(); const token = session?.access_token;`. 세션이 없으면(로그아웃 상태) 사용자에게 "로그인이 필요합니다" 안내(이론상 proxy가 막지만 방어). 토큰 만료 시 Supabase가 자동 갱신하므로 매 요청 `getSession()`으로 최신 토큰을 얻는다.
[Source: architecture.md(292); auth.py:43-77; supabase/client.ts]

### 핵심 설계 — 데이터 흐름(웹 → API → 웹)

```
[ChatAssistant.tsx (client)]
  사용자 입력 query
   → supabase.auth.getSession() → access_token
   → context = 직전 messages를 {role,content}[]로 직렬화(최근 12턴, content 2000자 절단)
   → searchAi({ query, context, accessToken })            (lib/api/aiSearch.ts)
        → POST ${NEXT_PUBLIC_API_BASE_URL}/ai/search
           headers: Authorization: Bearer <token>, Content-Type: application/json
           body: { query, context }
        ← 200 { answer, listings[] }   |   비200 { error:{code,message} }
   → messages에 assistant 턴 추가: { role:'assistant', content: answer, listings }
   → 렌더: answer 텍스트 + listings.map(ListingCard)  (카드 클릭 → /listings/[id])
```

- **응답 계약**: `{answer: string, listings: ListingCard[]}` (snake_case, 4.1 확정). `listings` 각 원소 = `{id, manufacturer, model, year, price, mileage, region}` → `ListingCardData`와 1:1.
- **에러 계약**: 비200은 `{error:{code, message}}`. 코드 예: `unauthorized`(401)·`validation_error`(422)·`http_error`/sql_guard(400)·`internal_error`(500)·`auth_unavailable`(503). 클라이언트는 message를 그대로 보여주거나 코드별 한국어 매핑. **CORS**: API `main.py`가 `cors_origins`(기본 localhost:3000)만 허용 → 로컬 web(:3000)은 통과. 배포 시 web 도메인을 API CORS에 추가해야 함(사용자 직접 처리 고지).
[Source: schemas/ai.py SearchResponse/ErrorResponse; main.py:27-35,49-66]

### 파일 구조 (생성/수정 대상) — architecture가 이미 경로를 박아둠

```
신규:
  web/src/app/(user)/ai/page.tsx               # AI 채팅 화면(서버 컴포넌트). architecture.md(350) 확정 경로.
  web/src/components/ai/ChatAssistant.tsx       # 대화 UI(클라이언트). architecture.md(358) 확정 경로.
  web/src/lib/api/aiSearch.ts                   # /ai/search 호출 함수. architecture.md(361) 확정 경로.
수정:
  web/src/proxy.ts                              # PROTECTED_PREFIXES에 '/ai' 추가.
  web/src/app/page.tsx                          # 홈에 "AI 검색" 진입 링크.
  web/.env.local                                # NEXT_PUBLIC_API_BASE_URL 추가(로컬 :8000).
재사용(안 건드림):
  web/src/components/listings/ListingCard.tsx   # 매물카드(클릭→상세). 그대로 import.
  web/src/components/layout/AppHeader.tsx        # 상단바. search/page.tsx처럼 사용.
  web/src/components/ui/Button.tsx               # 전송 버튼.
  web/src/lib/supabase/client.ts                # 브라우저 클라(세션 토큰 획득).
```
- **만들지 않음**: 백엔드 일체(4.1~4.6 done), 새 매물카드, 대화 저장(DB·localStorage), 새 의존성, TanStack Query.
[Source: architecture.md#Project Structure(350,358,361); search/page.tsx 패턴]

### 이전 스토리 학습 (적용할 패턴)

- **4.6 멀티턴**: `context` = `[{role,content}]`, 최대 12턴·content 2000자. 빈/없으면 단일턴. 서버 무상태(클라가 동봉). 4.7은 그 `context`를 **실제로 만들어 보내는 클라이언트 측**이다.
- **search/page.tsx(3-1) 패턴 재사용**: 서버 컴포넌트에서 `createClient()` → `auth.getUser()` → profiles role 조회 → `AppHeader`에 roleLabel·email 전달. `(user)/ai/page.tsx`도 동일 골격.
- **client 컴포넌트 패턴(SellForm/SearchFilters)**: `'use client'` + `useState` + `useRouter`. 폼 제출·로딩·에러 처리 관용구를 따른다.
- **env 가드 패턴(`getSupabaseEnv`)**: 누락 env는 불투명 throw 대신 어떤 변수가 비었는지 한국어로 알린다 — `NEXT_PUBLIC_API_BASE_URL`에도 적용.
- **fail-loud(4.3~4.6)**: 호출 실패를 조용히 삼키지 말고 사용자에게 한국어로 보인다(AC5).

### 라이브러리·환경

- **추가 의존성 없음** — `fetch`(브라우저 내장)·`@supabase/ssr`(설치됨, 세션 토큰)·React `useState`로 충분. 새 패키지(axios·swr·tanstack-query) 설치 금지(데모 단순화). 도입이 꼭 필요하면 근거를 Completion Notes에 남길 것.
- **환경변수**: `NEXT_PUBLIC_API_BASE_URL`(신규, web/.env.local) — 브라우저 fetch 대상이라 `NEXT_PUBLIC_` 필수. 로컬은 `http://localhost:8000`. 기존 `NEXT_PUBLIC_SUPABASE_URL/ANON_KEY`는 세션 토큰 획득에 그대로 사용.
- **API(:8000) 라이브 조건**: `api/.env`의 `GEMINI_API_KEY`·`DATABASE_URL`·`SUPABASE_URL`·`SUPABASE_ANON_KEY`가 있어야 실제 응답. 없으면 401/500이 나거나 기동 불가 → **UI·네트워크 계약 검증으로 대체**(AC6)하고 그 사실을 보고. **거짓 "완료" 금지.**

### 자체 테스트 방식 (CLAUDE.md §6)

- **웹 = Playwright MCP로 실제 브라우저 E2E.** dev 서버는 백그라운드(`run_in_background`) 기동 → health check → 테스트 → 정리.
  - 로그인(기존 시드 계정) → `/ai` → 질의 전송 → 답변·카드 렌더 → 카드 클릭 상세 이동 → 후속 질의 context 동봉(네트워크 요청 본문) 확인.
  - API 라이브면 실제 `{answer, listings}` 확인. 미가동이면 `browser_network_requests`로 `/ai/search` 요청의 URL·`Authorization` 헤더·body(query·context)를 검증하고 에러 UI(AC5) 확인.
- **lint/typecheck/build** 통과 필수(Next.js 16 빌드가 서버/클라이언트 컴포넌트 경계 오류를 잡는다).

### 사용자 직접 처리 항목 (왜 / 어디서)

- **`web/.env.local`의 `NEXT_PUBLIC_API_BASE_URL`** — 웹이 호출할 AI API 주소. 로컬은 `http://localhost:8000`(dev가 기본값 넣음). **배포 시 실제 API URL(Vercel Python 서버리스 또는 Cloud Run)** 로 교체 필요 / `web/.env.local`(로컬)·Vercel 환경변수(배포).
- **`api/.env`의 `GEMINI_API_KEY`·`DATABASE_URL`** — `/ai/search`가 실제 답·매물을 주려면 필수(라이브 E2E 조건). 없으면 UI/계약 검증까지만 / `api/.env`.
- **API CORS에 web 배포 도메인 추가** — 배포 환경에서 브라우저가 API를 호출하려면 `api`의 `cors_origins`에 web 도메인을 넣어야 함(로컬 localhost:3000은 이미 허용) / `api/.env`의 `CORS_ORIGINS`.
- **Playwright MCP 승인** — 최초 연결 시 승인 프롬프트 / Claude Code.

### 알려진 이연(Deferred) — 이번 스토리에서 다시 따지지 말 것

- **스트리밍 응답 UI** — `/ai/search`가 단발 JSON이라 범위 밖. 향후 SSE 도입 시 별도 스토리.
- **양방향 되묻기(clarify) 대화 루프**(4.5/4.6 defer) — 서버가 먼저 되묻는 루프는 미구현. 4.7은 사용자 질의→답변 흐름.
- **대화 영속/공유** — 무상태 전제상 의도적으로 안 함(AC4).

## Project Structure Notes

- architecture.md(350·358·361)가 세 신규 파일 경로(`(user)/ai/page.tsx`·`components/ai/ChatAssistant.tsx`·`lib/api/aiSearch.ts`)를 **이미 확정**했다. 그대로 따른다(변형 금지).
- 라우트 그룹 `(user)`는 인증된 사용자 영역(search·listings·sell과 동거). `/ai`도 여기 둔다. `proxy.ts` `PROTECTED_PREFIXES`에 `/ai` 추가로 비로그인 차단(search·listings와 동일 정책 — 역할 게이트 없음, 로그인 사용자 공통).
- 변이 없음: 카드 7필드 ↔ API 7필드 ↔ `ListingCardData` 7필드가 모두 일치(드리프트 0).

## References

- [Source: epics.md#Story 4.7(541-556)] — AC 원문: 자연어 입력→`/ai/search`→답변+매물카드, 카드 클릭 상세 이동, 텍스트 필드만(사진 없음).
- [Source: epics.md#FR12(37,99)] — 구매자는 AI 채팅 어시스턴트에 자연어 한 문장으로 검색.
- [Source: architecture.md(52,398)] — 무상태 전제·AI 대화 전용 테이블 없음·멀티턴 맥락은 클라이언트 상태에만.
- [Source: architecture.md(292)] — 인증: 클라가 Supabase 세션 토큰 보관 → AI 호출 시 `Authorization: Bearer <jwt>` 동봉.
- [Source: architecture.md(350,358,361)] — 신규 파일 경로 확정(ai/page.tsx·ChatAssistant.tsx·aiSearch.ts).
- [Source: api/app/schemas/ai.py(29-74)] — SearchRequest(query·context 12턴·2000자)·SearchResponse(answer·listings 7필드)·ErrorResponse.
- [Source: api/app/routers/ai.py(28-42)] — POST /ai/search, Depends(get_current_user), 200/400/401/422/500.
- [Source: api/app/auth.py(43-77)] — Bearer JWT 검증·401·503.
- [Source: api/app/main.py(27-66)] — CORS(localhost:3000)·공통 에러 포맷 {error:{code,message}}.
- [Source: web/src/components/listings/ListingCard.tsx(1-40)] — 재사용 매물카드(목록·AI 공유), 클릭→/listings/[id].
- [Source: web/src/app/(user)/search/page.tsx(53-181)] — 서버 컴포넌트 골격(AppHeader·role·렌더) 재사용 패턴.
- [Source: web/src/app/(user)/search/SearchFilters.tsx] — client 컴포넌트(useState·useRouter·폼) 패턴.
- [Source: web/src/lib/supabase/client.ts] — 브라우저 Supabase 클라(세션 access_token 획득).
- [Source: web/src/proxy.ts(19)] — PROTECTED_PREFIXES(여기에 '/ai' 추가).
- [Source: web/AGENTS.md] — Next.js 16 주의(학습데이터와 다름, docs 먼저 읽기).
- [Source: api/docs/ai-demo-queries.md(55-68)] — 멀티턴 context 형태 단일출처(12턴·2000자).
- [Source: _bmad-output/implementation-artifacts/4-6-멀티턴-맥락.md] — context 스키마·무상태·맥락화 동작.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (dev-story 워크플로우). 백엔드 AI: 기존 `/ai/search`(라우터 + 경로 A/B/C + 맥락화, 4.1~4.6 done) 그대로 호출.

### Debug Log References

- **검증 스택**: web는 단위 test runner 미설치(package.json scripts = dev/build/start/lint). 그래서 "테스트" = `tsc --noEmit`(타입) + `eslint`(린트) + `next build`(서버/클라 경계) + **Playwright MCP 실브라우저 E2E**(CLAUDE.md §6 웹 방식). 전부 통과.
- **빌드/타입/린트**: `npx tsc --noEmit` exit 0, `npx eslint` exit 0, `npm run build` 성공 — `/ai` 라우트가 ƒ(dynamic)로 등록됨.
- **라이브 E2E(실 API :8000 + 실 Gemini + 실 Supabase DB)**:
  - 로그인(seller-seed@test.com) → 홈에 "AI 검색" 링크 노출 → `/ai` 진입(미인증 시 307 → /login 확인).
  - 단일턴 라이브 성공 3건: ① "3천만원 이하 흰색 SUV"(경로 A) → answer "매물 2건" + 현대 싼타페 TM·폭스바겐 티구안 카드. ② "서울 경차 보여줘"(A) → 5건(스파크·모닝·레이·쏘울·티볼리). ③ "패밀리카로 무난한 거 추천해줘"(경로 B) → 5건 + 근거 가이드 표기.
  - **AC3**: 스파크 카드 클릭 → `/listings/7faa5ad5-...` 상세 페이지 렌더 확인.
  - **AC4 멀티턴 request body 하드 캡처(fetch 가로채기)**: 후속 "그 중 더 싼 거" 전송 시 body = `{"query":"그 중 더 싼 거","context":[{"role":"user","content":"패밀리카로 무난한 거 추천해줘"},{"role":"assistant","content":"...5건을 찾았어요..."}]}` — **현재 질의는 query로, 직전 대화만 context로**(중복 없음) 동봉됨을 눈으로 확인.
  - **AC4 무상태**: 새로고침 후 대화가 빈 초기 화면으로 리셋됨(클라이언트 상태에만 존재).
  - **AC5 에러/롤백**: 후속 질의가 Gemini 429에 걸렸을 때 빨간 한국어 alert("AI 검색 서버에 연결하지 못했습니다") 노출 + 실패 턴 롤백(대화에 답 없는 버블 안 남김) + 입력값 복원 확인.
- **외부 제약(코드 무관)**: Gemini **무료 티어 일일 쿼터(20 req/day) 초과 시 429 RESOURCE_EXHAUSTED**가 간헐 발생. 단일턴은 라우터+경로 LLM, 멀티턴은 거기에 맥락화 LLM 1회가 더해져 쿼터를 빨리 소진한다. 쿼터 창이 열린 동안 단일턴 3건·멀티턴 request 동봉을 라이브로 확인했고, 쿼터 소진 구간은 에러 UI·롤백 동작 검증에 활용. **유료 키/쿼터 상향 시 멀티턴 answer까지 라이브로 완결됨**(코드 결함 아님 — escalate 항목).
- **환경 메모(Windows)**: 기동 시 :3000이 이미 점유(이전 dev 잔여 프로세스)라 Next.js가 자동으로 :3001로 이동. API CORS는 기본 localhost:3000만 허용하므로, 테스트 동안 `CORS_ORIGINS=...,http://localhost:3001` 환경변수로 주입해 재기동(`.env` 파일은 미변경, 원복 불필요).

### Completion Notes List

- **백엔드 무수정 원칙 준수**: API(`/ai/search`·그래프·노드·스키마)는 한 줄도 안 고쳤다. 4.7은 웹 3개 신규 + 3개 수정 + env 1줄. `context` 스키마(12턴·2000자)는 4.6 확정값을 클라이언트가 그대로 지켜 보낸다(`buildContext`의 `slice(-12)`·`slice(0,2000)`).
- **API base URL 도입**: 웹↔API는 별도 오리진이라 `NEXT_PUBLIC_API_BASE_URL`(브라우저 fetch라 NEXT_PUBLIC_ 필수)을 신설. 끝 슬래시 정규화로 `//ai/search` 방지. 누락 시 한국어 가드(getSupabaseEnv 철학).
- **인증 배선**: 매 전송마다 `supabase.auth.getSession()`으로 최신 access_token을 꺼내 `Authorization: Bearer`로 보낸다(토큰 만료 자동 갱신 활용). 토큰 없으면 호출 전 한국어 에러.
- **멀티턴 맥락 = 클라이언트 상태에만**: `messages`(useState)에 대화를 쌓고, 후속 전송 시 `buildContext`가 직전 턴들을 `{role,content}[]`로 직렬화(현재 query는 제외 → 중복 금지). localStorage·쿠키·DB 미사용 → 새로고침=초기화(FR18·무상태). assistant 턴 content는 answer 텍스트만(매물카드는 content에 안 실음).
- **매물카드·상세이동 재사용**: 새 컴포넌트/타입 0개. `ListingCard`(내장 `<Link href=/listings/[id]>`)와 `ListingCardData`(API 7필드와 1:1)를 그대로 써 AC3가 추가 코드 없이 충족.
- **E2E 발견·반영한 개선(롤백)**: 라이브 중 "전송 실패 시 낙관적으로 추가한 사용자 버블이 대화에 남아 다음 context를 오염시킨다"를 관찰. catch에서 **마지막 user 턴 롤백 + 입력값 복원**을 추가해, 실패 질의가 history·context에 새지 않고 즉시 재시도 가능하게 했다(재검증으로 깨끗한 멀티턴 context 확인).
- **에러 fail-loud(AC5)**: 네트워크 실패·401·400·422·5xx를 한국어 안내로 표면화(조용한 실패 금지, 4.x 철학 계승). 로딩 중 입력·버튼 disabled로 연타 차단.
- **의존성 추가 0**: fetch·@supabase/ssr·React useState만으로 구현(axios·swr·tanstack-query 미도입 — 데모 단순화, 범위 밖 준수).
- **새 의존성/마이그레이션/대화저장 없음**: 범위 밖 항목(스트리밍·clarify·영속·Flutter) 미구현 확인.

### File List

신규:
- `web/src/lib/api/aiSearch.ts` — `/ai/search` 호출 함수(Bearer 인증·context 동봉·한국어 에러 변환). 타입(`SearchResult`·`ConversationTurn`).
- `web/src/components/ai/ChatAssistant.tsx` — AI 채팅 UI(클라이언트). 대화 상태·멀티턴 context 직렬화(`buildContext`)·매물카드 렌더·로딩/에러/실패 롤백.
- `web/src/app/(user)/ai/page.tsx` — AI 검색 화면(서버 컴포넌트). AppHeader + ChatAssistant.

수정:
- `web/src/proxy.ts` — PROTECTED_PREFIXES에 `/ai` 추가(비로그인 1차 차단).
- `web/src/app/page.tsx` — 홈에 "AI 검색"(/ai) 진입 링크 추가.
- `web/.env.local` — `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` 추가(주석 포함).

재사용(무수정): `components/listings/ListingCard.tsx`·`components/layout/AppHeader.tsx`·`components/ui/Button.tsx`·`lib/supabase/client.ts`. 백엔드 일체 무수정.

## Change Log

- 2026-06-21: 4.7 AI 검색 UI(FR12·FR18) 구현 — `/ai` 채팅 화면 + `lib/api/aiSearch.ts`(Bearer 인증 호출) + `ChatAssistant`(멀티턴 context 클라이언트 보관·동봉). 매물카드는 ListingCard 재사용(클릭→상세 이동). proxy `/ai` 보호 + 홈 진입 링크. tsc/eslint/build 통과. Playwright 라이브 E2E: 단일턴 3건·카드 클릭 상세 이동·멀티턴 context 동봉(request body 캡처)·무상태 초기화·에러/롤백 확인. Gemini 무료 쿼터(20/day) 초과 시 멀티턴 answer 라이브는 간헐 429(코드 무관, escalate). Status → review.

## Escalation (사람 결정/처리 필요)

- **(E1) Gemini 무료 티어 일일 쿼터(20 req/day)** — 멀티턴은 맥락화 LLM이 1회 더 붙어 쿼터를 빨리 소진한다. 라이브 멀티턴 answer 완결 확인은 쿼터 여유 시에만 가능했고, 소진 구간은 429로 에러 UI를 탔다. 코드 결함 아님. **시연/평가 전 유료 키 또는 쿼터 상향 권장**(api/.env의 GEMINI_API_KEY). 이는 4.8 통합검증과도 직결.
- **(E2) 배포 시 사용자 직접 처리** — (a) Vercel(또는 Cloud Run) 배포 후 실제 API URL을 web `NEXT_PUBLIC_API_BASE_URL`(로컬은 localhost:8000)로 교체, (b) API `CORS_ORIGINS`에 web 배포 도메인 추가(로컬 :3000은 이미 허용; 테스트 중 :3001은 환경변수로 임시 허용). 둘 다 코드 밖 설정값이라 사람만 가능.
