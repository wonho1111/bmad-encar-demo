# 04. 웹 프론트엔드 — Next.js (React, TypeScript)

> 사용자가 실제로 보는 화면입니다. DB의 데이터가 어떻게 화면에 나오고, 사용자가 어떻게 조작하는지를 다룹니다. 가장 친숙하게 느껴질 파트입니다.
> 대상 코드: `web/src/` (페이지 `app/`, 컴포넌트 `components/`, 헬퍼 `lib/`).

---

## 4-1. 먼저 알아둘 것

- *Next.js*: React 기반 웹 프레임워크. **서버에서 화면을 미리 그려(SSR) 보내주는** 데 강함.
- *React*: 화면을 "컴포넌트(부품)"로 조립하는 UI 라이브러리.
- *TypeScript*: JavaScript에 타입(자료형)을 더한 언어. 실수를 미리 잡아줌.
- *App Router*: Next.js의 폴더-기반 라우팅 방식. **폴더 구조가 곧 URL 구조**입니다.
  - 예) `app/(user)/search/page.tsx` → 주소 `/search`

핵심: 이 웹은 **일반 기능(매물·채팅·로그인)은 Supabase에 직접 접속**하고, **AI 검색만 FastAPI(`/ai/search`)를 호출**합니다.

---

## 4-2. 가장 중요한 두 개념: 서버 컴포넌트 vs 클라이언트 컴포넌트

Next.js App Router에서 모든 화면 파일은 **기본이 "서버 컴포넌트"** 입니다. 맨 위에 `'use client'`를 붙인 것만 "클라이언트 컴포넌트"가 됩니다.

| | 서버 컴포넌트 (기본) | 클라이언트 컴포넌트 (`'use client'`) |
|---|---|---|
| 실행 장소 | 서버 | 브라우저 |
| 잘하는 일 | DB 조회, 화면 미리 그리기 | 버튼 클릭·입력·타이머 등 **상호작용** |
| 할 수 없는 일 | 클릭/상태/타이머 | DB 직접 접근(대신 Supabase SDK로) |
| 예시 | `search/page.tsx`(목록 조회·렌더) | `SearchFilters.tsx`(필터 입력), `ChatRoomMessages.tsx`(폴링) |

> 원칙: **"읽어서 그리기만 하면 서버, 사용자가 만지면 클라이언트."**
> 왜 나눌까요? 서버 컴포넌트는 DB를 안전하게(비밀키 노출 없이) 빨리 읽고, 클라이언트 컴포넌트는 사용자 동작에 즉각 반응합니다. 둘을 섞어 장점만 취합니다.

---

## 4-3. 폴더 구조와 Route Group

```
web/src/app/
├─ layout.tsx          전체 공통 틀(HTML 뼈대, 헤더)
├─ page.tsx            홈 "/" (로그인 여부로 화면 분기)
├─ (auth)/             ← 괄호 그룹: URL엔 안 나옴
│   ├─ login/page.tsx       "/login"
│   └─ signup/page.tsx      "/signup"
├─ (user)/             ← 구매자·판매자 공용
│   ├─ search/page.tsx      "/search" 매물 탐색
│   ├─ listings/[id]/page.tsx  "/listings/123" 매물 상세
│   ├─ sell/...             "/sell" 매물 등록·관리 (판매자)
│   ├─ ai/page.tsx          "/ai" AI 검색
│   └─ chat/...             "/chat" 채팅
└─ (admin)/            ← 관리자 전용
    ├─ layout.tsx           관리자 역할 검사
    └─ admin/...            "/admin/..."
```

- *Route Group `(...)`*: 괄호 폴더는 **URL에 안 나타나고** 화면을 논리적으로 묶는 용도. 그룹마다 `layout.tsx`로 **접근 제어**를 겁니다.
- *`[id]`/`[roomId]` 동적 라우트*: 주소의 변하는 부분(매물 id, 방 id). Next.js 16부턴 `const { id } = await params`로 받습니다.
- *layout.tsx 중첩*: 루트 → 그룹 → 페이지 순으로 레이아웃이 겹겹이 쌓입니다. 예) `(admin)/layout.tsx`가 관리자 검사를 하므로, 그 아래 모든 admin 페이지가 자동 보호됩니다.

---

## 4-4. 인증·접근 제어 (이중 방어)

웹은 권한을 **두 겹**으로 막습니다.

1. **`proxy.ts` (미들웨어)** — 모든 요청을 가로채, 로그인 토큰을 갱신하고 **비로그인 사용자를 보호 경로에서 `/login`으로** 보냅니다(빠른 1차 차단).
   - *미들웨어(middleware)*: 요청이 페이지에 닿기 전에 먼저 실행되는 가로채기 코드.
2. **`lib/auth/guard.ts`** — `requireUser()`(로그인 필수), `requireRole(역할)`(특정 역할 필수)로 각 페이지/그룹에서 DB의 실제 역할을 확인(2차 인가).
   - 예) `(user)/sell/layout.tsx`는 `requireRole(SELLER)`, `(admin)/layout.tsx`는 `requireRole(ADMIN)`.

> 그리고 그 아래엔 **DB의 RLS**(01번)가 3차로 버팁니다. 프론트가 실수해도 DB가 최종 방어.

---

## 4-5. Supabase 클라이언트가 왜 3종류?

`lib/supabase/` 에 용도별로 나뉘어 있습니다.

| 파일 | 어디서 쓰나 | 역할 |
|------|------------|------|
| `client.ts` | 클라이언트 컴포넌트(브라우저) | 브라우저용 접속 |
| `server.ts` | 서버 컴포넌트 | 쿠키 기반 세션으로 서버에서 접속 |
| `session.ts` | `proxy.ts` | 매 요청 토큰 갱신·쿠키 설정 |
| `env.ts` | 공통 | 환경변수 검증(없으면 한국어 경고) |

- 서버와 브라우저는 세션을 다루는 방식(쿠키 vs 브라우저 저장소)이 달라 클라이언트를 분리합니다.
- 중요: `getUser()`는 **쿠키를 맹신하지 않고** Supabase Auth 서버에 한 번 더 검증합니다(위조 방지).
- 이 앱은 막강한 `service_role` 키를 **안 씁니다.** 오직 `anon`(익명) 키 + RLS로만 동작 → 키가 새도 RLS가 막음.
- *환경변수 `NEXT_PUBLIC_*`*: 브라우저에 노출돼도 되는 값(예: Supabase URL). 접두사 없는 값은 서버 전용.

---

## 4-6. 핵심 페이지 흐름

### 홈 `page.tsx` (서버 컴포넌트)
- 로그인 안 했으면 로그인/회원가입 링크만, 했으면 역할 배지·내 채팅방 수·판매중 매물 수·최근 매물 4건을 보여줌.
- `export const dynamic = 'force-dynamic'` — 매 요청마다 최신 DB를 반영(캐시 끔). 매물 등록 즉시 노출(FR7)을 보장.

### 매물 탐색 `search/page.tsx` + `SearchFilters.tsx`
- **필터 상태를 URL에 저장**합니다. `SearchFilters`(클라)가 입력을 받아 `/search?region=서울&price_min=2000...`로 `router.push`.
- `search/page.tsx`(서버)가 그 URL을 읽어 DB를 조회해 목록을 그립니다.
- 장점: 새로고침·뒤로가기·링크 공유에 강함(상태가 URL에 있으니까).
- 조회는 항상 `buyerListingsQuery`(아래 4-8)로 시작 → **판매중 매물만**.

### 매물 상세 `listings/[id]/page.tsx`
- 매물 15필드 + 옵션 + 설명을 보여주고, **내 매물이 아니면** "문의하기" 버튼(`InquiryButton`)을 노출.
- 판매완료(sold) 매물은 구매자에게 "찾을 수 없음"으로 처리(FR11).

### AI 검색 `ai/page.tsx` + `ChatAssistant.tsx`
- `ChatAssistant`(클라)가 대화 상태와 **멀티턴 맥락(context)** 을 브라우저 메모리에 들고, `searchAi()`로 FastAPI를 호출.
- 새로고침하면 대화가 초기화됩니다(의도된 무상태 설계).

### 채팅 `chat/[roomId]/page.tsx` + `ChatRoomMessages.tsx`
- 서버 컴포넌트가 당사자인지 확인하고 매물 요약·헤더를 그린 뒤, 메시지 영역은 `ChatRoomMessages`(클라)에 맡깁니다.

---

## 4-7. 채팅 폴링 (실시간처럼 보이기)

웹소켓 대신 **3초마다 새 메시지를 조회**하는 폴링 방식입니다.

```
초기: fetchMessages(roomId)              → 전체 메시지 로드, 커서 = 마지막 시각
3초마다: fetchMessages(roomId, 커서)     → 커서 "이상(gte)"의 새 메시지만
        → mergeIncoming: id로 중복 제거(dedupe) + 시간순 정렬
방 나가면: clearInterval로 타이머 정리
```

핵심 포인트:
- **`gte(>=)` 커서**: 같은 시각에 온 메시지를 놓치지 않으려 "이상"으로 조회. 중복은 id로 제거하므로 누락 0.
- **낙관적 업데이트**: 내가 보낸 메시지는 응답을 기다리지 않고 즉시 화면에 추가. 폴링이 같은 걸 또 가져와도 dedupe로 안전.
- *폴링(polling)*: 주기적으로 "새 거 있어?"를 물어보는 방식. 간단하지만 약간의 지연(3~5초)이 있음.

> 보안은 RLS가: 제3자가 roomId를 알아도 당사자가 아니면 0건만 보입니다.

---

## 4-8. lib 헬퍼 — "규칙은 한 곳에"

같은 규칙이 여러 곳에 흩어지면 어긋나기 쉬워서, 핵심 규칙을 헬퍼 함수 한 곳에 모았습니다(단일 출처).

| 헬퍼 | 책임 |
|------|------|
| `lib/listings.ts`의 `buyerListingsQuery` | "구매자는 판매중 매물만"(FR11)의 단일 시작점 |
| `lib/chat.ts`의 `openOrCreateRoom` | 채팅방 생성/재사용 규칙(중복 방지) |
| `lib/messages.ts`의 `fetchMessages`/`dedupeById` | 메시지 조회·중복 제거 규칙 |
| `lib/constants.ts`의 `LISTING_OPTIONS` | 허용값(제조사·차종 등) 목록 |
| `lib/api/aiSearch.ts`의 `searchAi` | FastAPI 호출 규칙(토큰·context 동봉) |

`openOrCreateRoom` 흐름(문의하기 누를 때):
```
1) 기존 방 있나? → 있으면 재사용 (중복 방 방지)
2) 없으면 INSERT (DB 트리거가 seller_id를 진짜 주인으로 강제 — 01번 0003c)
3) 동시 클릭 경합(UNIQUE 충돌) → 다시 조회해 재사용
→ roomId 반환 → /chat/{roomId}로 이동
```

---

## 4-9. 한 시나리오로 잇기: 검색 → 상세 → 문의 → 채팅

```
/search        SearchFilters(클라)가 URL 갱신 → page.tsx(서버)가 on_sale 매물 조회·렌더
   ↓ 카드 클릭 (href=/listings/{id})
/listings/{id} page.tsx(서버)가 매물 조회 → 내 매물 아니면 InquiryButton 표시
   ↓ "문의하기" 클릭 (InquiryButton, 클라)
openOrCreateRoom() → roomId 확보 → router.push(/chat/{roomId})
   ↓
/chat/{roomId} page.tsx(서버) 당사자 확인 → ChatRoomMessages(클라)
   ↓ 메시지 입력·전송(INSERT) + 3초 폴링 수신
대화 성립 (양쪽이 같은 방을 폴링)
```

---

## 4-10. 핵심 개념 정리 (이 파트에서 꼭 배워야 할 것)

1. **SSR vs CSR** — 서버에서 미리 그리기 vs 브라우저에서 상호작용.
2. **서버 컴포넌트 vs 클라이언트 컴포넌트** — 기본은 서버, 만지는 건 `'use client'`.
3. **App Router + Route Group** — 폴더=URL, 괄호 그룹=논리 묶음·접근제어, `[id]`=동적 라우트.
4. **이중(삼중) 인증** — proxy(미들웨어) + guard(역할) + DB RLS.
5. **Supabase 세션/토큰** — 쿠키 자동 갱신, `getUser()` 재검증, anon 키 + RLS만 사용.
6. **URL 상태 vs 메모리 상태** — 필터는 URL(공유·새로고침 강함), AI 대화는 메모리(무상태).
7. **폴링 + 낙관적 업데이트 + dedupe** — 실시간처럼 보이게 하는 패턴.
8. **단일 출처(헬퍼)** — 규칙을 한 곳에 모아 어긋남(drift) 방지.
9. **환경변수 `NEXT_PUBLIC_*`** — 브라우저 노출 가능/불가 구분.
10. **force-dynamic** — 캐시를 꺼 항상 최신 데이터 반영.

---

다음: [05-flutter-mobile.md](05-flutter-mobile.md) — "같은 백엔드, 다른 화면 기술"인 모바일 앱.
