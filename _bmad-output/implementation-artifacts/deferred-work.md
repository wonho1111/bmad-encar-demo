# Deferred Work

## Deferred from: code review of story-8-4-ac-db-1-커넥션-풀-롤-격리-커넥션-풀-fr50 (2026-07-14)

- **`psycopg[binary,pool]` 버전 미고정** [api/pyproject.toml, api/requirements.txt] — `ConnectionPool(..., open=True)` 생성자 패턴이 최신 `psycopg_pool`에서 지양되는 추세라, 버전 미고정 상태로는 향후 업그레이드 시 경고/동작 변경 위험. 버전 핀 추가를 고려.
- **누수 부재 테스트가 psycopg_pool의 비공식 보장(동일 물리 커넥션 재사용)에 의존** [api/tests/test_readonly.py] — `max_size=1`이 순차 재사용을 강제하긴 하나, 헬스체크 등으로 커넥션이 교체될 가능성은 라이브러리가 공식 보장하는 계약이 아님. 향후 psycopg_pool 내부 동작이 바뀌면 테스트가 잘못된 이유로 통과/flaky해질 수 있음.
- **DSN 포트(:6543) 전제가 주석에만 있고 코드로 검증되지 않음** [api/app/db/readonly.py, api/app/config.py] — `.env`가 실수로 :5432(세션 풀러)를 가리켜도 코드가 조용히 그대로 동작함. `SET LOCAL`은 풀러 종류와 무관하게 동작하므로 롤 누수가 재발하진 않지만, 의도한 성능 특성을 잃음. 우선순위 낮음.

---

## 🟢 결정 완료 — 메인화면 개편 타이밍 (2026-06-24, party-mode 2라운드)

> Epic 6 후 데모 사용에서 나온 검토 3건(정렬 불일치 · 관리자 돌아가기 · 메인화면 개편)을 party-mode 2라운드로 결정.
> 멤버: 📋John(PM) 🎨Sally(UX) 🏗️Winston(Architect) 💻Amelia(Dev). **핵심 합의: web 개편은 모바일 "기준선"이 아니다 — 이월되는 건 React 코드가 아니라 "역할별 내비/정보구조 규칙(문서)". 모바일을 미루는 게 가장 비싼 결정 → Flutter 직행 우선.**

**최종 결정 표** (각 항목: 지금즉시 / Epic7직전 / Epic7후 / Cut)

| 항목 | 결정 | 비고 |
|---|---|---|
| 역할별 정렬 통일 | **✅ 지금즉시 — 완료** | 관리자 홈을 구매자/판매자와 동일 상단정렬로(`min-h-screen justify-center` 제거). |
| 관리자 상세 '돌아가기' | **✅ 지금즉시 — 완료** | `router.back()` + 폴백(히스토리 없으면 `/admin/listings`). `?from=` 쿼리안은 표면 넓어 기각. |
| ① 로그인 본인정보 영역 | **✅ 완료(`49b0f05`)** | 역할 배지 + 이름(이메일 @앞부분). 이후 카드를 엔카풍 메뉴(구매문의·판매중 건수)로 보강(`681b702`). |
| ② 매물탐색 메인 렌더 | **✅ 완료 — 미리보기판(`49b0f05`)** | 최근 N건 읽기전용 카드 + 더보기→/search. 홈은 필터·URL 미소유. **"홈이 탐색을 직접 품기"는 여전히 Epic7 후(보류).** |
| ③ AI채팅 진입 개선(플로팅) | **✅ 완료(`49b0f05`)** | 우하단 떠 있는 AI 검색 링크(가벼운 전역 진입). |
| ④ 반응형(데스크톱 넓게) | **Cut(보류)** | 만장일치. 전 화면 레이아웃 회귀 폭탄 + 모바일 이월 0. Flutter가 따로 함. |
| ⑤ 관리자 대시보드 | **Cut/보류** | UI는 web 전용 표현(버려짐). 집계쿼리(데이터 계약)만 모바일 관리자 확정 시 별도. |

**🏗️ Winston 핵심 산출물 — "역할별 내비/정보구조 규칙 문서 1장"** → **✅ 작성 완료(`fcfea8a`, `_bmad-output/planning-artifacts/nav-ia-rules.md`)**. (역할×진입점 매트릭스 / 역할별 1차 내비 / 복귀 규칙 / 플랫폼 불변식)

**진행 상태(2026-06-25 갱신):** "Epic7 직전" 묶음(①·②미리보기·③·내비 문서) **전부 완료 + develop·main 반영 + 운영 배포 검증**. **남은 보류 = ④반응형 · ⑤관리자 대시보드 · "②홈이 탐색 직접 품기"(전체판).** 추가로 데모 폴리시(판매자/구매자 이름 표시 0007~0009)도 완료.

---

## ✅ 검증 완료 (2026-06-24) — 판매자 본인 매물 문의 차단(원 검토 1번)

- **판매자가 본인 매물에 문의채팅을 보내는 buyer=seller 꼬임 → 3중 안전장치 전부 작동 확인.** Epic 5(5-2)와 그 코드리뷰(High 지적 → 옵션 A "무결성은 DB로 못박기")에서 구현됨. **결함 없음 → 토론 안건에서 제외.**
  - **① UI 숨김** [web/src/app/(user)/listings/[id]/page.tsx:153] — `user.id !== listing.seller_id`일 때만 '문의하기' 렌더. **E2E 확인**: seller-seed2로 본인 매물 상세 진입 시 버튼 미노출(Playwright, 2026-06-24).
  - **② DB BEFORE INSERT 트리거** [supabase/migrations/0003c_chat_room_integrity.sql `enforce_chat_room_seller`] — 클라가 보낸 seller_id를 무시하고 매물 실제 소유자로 강제 덮어씀(위조 차단). 본인이 소유자면 seller_id=buyer_id가 됨.
  - **③ DB CHECK 제약** [supabase/migrations/0003_chat.sql:33 `chat_rooms_buyer_ne_seller`] — buyer_id<>seller_id 강제. **실증**: UI 우회 직접 INSERT 시 `violates check constraint "chat_rooms_buyer_ne_seller"` (errcode 23514)로 거부됨(2026-06-24).
  - 설계 노트(이월): "역할은 계정이 아니라 행위(판매자=잠재 구매자)" — 판매자가 남의 차도 보고 싶을 수 있다는 신규 유스케이스는 메인화면 개편/Epic 7 정보구조에서 함께 검토.

---

## ✅ 해소됨 (Story 1.4, 2026-06-20)

- **Supabase 클라이언트 env 누락 가드 부재** (1-1·1-2 코드리뷰 이연 2건) — `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화. 누락 시 어떤 변수(`NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`)가 비었는지 명시한 한국어 에러를 throw하고, `client.ts`·`server.ts`·`session.ts`가 공유한다. proxy(`web/src/proxy.ts`)는 env 누락 시 한국어 경고 로그 + 요청 통과(`NextResponse.next()`)로 graceful 처리. → `process.env.…!` 비-널 단언 제거 완료.

---

## Deferred from: code review of story 5-3 (2026-06-24)

- **폴링 지속 실패 시 무알림** [web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx 폴링 effect] — 초기 로드 실패는 한국어 에러로 표시하지만, 세션 만료·방 삭제 등으로 폴링이 매 주기 영구 실패하면 사용자에게 아무 표시 없이 대화가 멈춘 것처럼 보인다(첫 로드는 loud, 폴링 실패는 silent의 비대칭). NFR1의 "일시 실패는 조용히 재시도" 정책과 충돌하지는 않으므로 회귀 아님. 향후 "재연결/오프라인 표시" 개선 시 N회 연속 실패 후 비차단 배너를 띄우는 방식 검토.
- **커밋 후 응답 유실 시 중복 전송** [web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx handleSubmit catch] — INSERT가 DB에 성공했으나 응답이 네트워크에서 끊기면 catch가 입력을 복원하고 사용자가 재전송 → 서로 다른 id의 중복 메시지가 영속된다(dedupe는 id 기준이라 못 막음). 멱등키(클라 생성 uuid를 PK로)가 정석이나 데모 범위 밖. 중복 우려가 커지면 도입.
- **본문 최대 길이 가드 없음** [web/src/lib/messages.ts sendMessage / 입력창] — `body`가 `text`(무제한)이고 클라이언트는 `trim()`만 한다. 초대용량 붙여넣기가 그대로 INSERT되어 행·이후 폴링 페이로드를 비대화시킬 수 있다. 입력창 `maxLength` + 서버측 길이 컷으로 하드닝 가능(회귀 아님).

## Deferred from: code review of story 1-4 (2026-06-20)

- **`redirectedFrom` 소비처 부재 + open-redirect 검증 규약 미정** [web/src/proxy.ts, web/src/app/(auth)/login/page.tsx] — proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만, 로그인 화면은 이를 읽지 않고 항상 `/`로 이동한다(현재 무해). 향후 "로그인 후 원래 가려던 곳으로 복귀" 스토리에서 `redirectedFrom`을 사용할 때, 반드시 값이 `/`로 시작하는 **상대경로**인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트를 막을 것. 보호경로가 `/admin` 1개뿐이라 현재 영향은 작음.

## Deferred from: code review of story 2-3 (2026-06-20)

- **options(text[]) 라운드트립이 쉼표 포함 외부생성 값에 손실 가능** [web/src/app/(user)/sell/SellForm.tsx] — 수정 폼이 options를 쉼표로 join(미리채움)/split(저장)한다. 그래서 폼 밖(시드·API)에서 한 배열원소에 쉼표를 포함해 넣은 옵션은 첫 수정·저장 때 두 개로 쪼개진다. pre-existing(2-2 등록 폼도 동일 규칙). 현재 폼 입력만으로는 쉼표 포함 원소가 만들어지지 않아 영향 없음. 시드 매물(2-5)·가이드/임베딩(Epic 4)에서 쉼표 포함 옵션을 도입할 경우, 입력 구분자를 바꾸거나(예: 줄바꿈) 옵션을 칩(chip) UI로 받는 방식을 검토할 것.

## Deferred from: code review of story 2-4 (2026-06-20)

- **sold→on_sale DB 재오픈 미차단(단방향 트리거 없음)** [supabase/migrations/0002_listings.sql, web/src/app/(user)/sell/ListingActions.tsx] — `listings_update_own` RLS는 소유권만 보고 status 전이 방향을 강제하지 않는다. 본인 sold 매물을 `update status='on_sale'`로 재오픈하는 것이 DB 차원에서 가능하다. 2-1 설계가 의도적으로 단방향 트리거를 두지 않았고, 본 스토리 범위 주의에 "재오픈 UI는 범위 밖(과잉구현 금지)"으로 명시됨 — 현재 UI에는 재오픈 경로가 없어 영향 없음. 향후 "구매 완료 단방향 고정" 또는 "재오픈 기능"을 정식 도입할 때, BEFORE UPDATE 트리거(`old.status='sold' → 거부`)나 RLS WITH CHECK로 정책을 명시할 것.
- **단일 `error` useState를 handleComplete·handleDelete가 공유** [web/src/app/(user)/sell/ListingActions.tsx] — 두 핸들러가 같은 `error` 슬롯을 쓴다. 각 핸들러 시작 시 `setError(null)`로 초기화하지만 성공 경로에서는 명시 초기화가 없다. 2-3에서 내려온 패턴. 한 행에 버튼이 모여 있어 실사용 혼선은 작음. 핸들러가 더 늘면 핸들러별 에러 상태 분리를 검토.
- **`OwnListing.status` 타입이 `string`(union `ListingStatus` 미사용)** [web/src/app/(user)/sell/page.tsx:21] — 2-2부터 내려온 cosmetic. `LISTING_STATUS.ON_SALE` 비교는 정상 동작하나, union 타입을 쓰면 오타·미정의 status 비교를 컴파일타임에 잡을 수 있다. 다른 select 타입 정리 시 함께 union으로 좁힐 것.

## Deferred from: code review of story 2-5 (2026-06-20)

- **데모 자격증명 평문 커밋(seller-seed@test.com / seller123)** [supabase/seed.sql] — 시드 전용 판매자 계정이 평문 비밀번호로 저장소에 커밋된다. 기존 admin 시드(1.5)의 동일 패턴을 상속했고, ⚠️ 주석과 스토리 Completion Notes에 "운영 전 교체"가 명시돼 있다. 환경별 게이팅(운영 DB에 시드 미적용)은 본 스토리 범위 밖. 운영 배포 전 비밀번호 교체 또는 시드 환경 분리를 정식 도입할 것.
- **고아 auth.users(profiles 없음)/handle_new_user 트리거 비활성 시 재실행 중단** [supabase/seed.sql:163-174] — 시드 판매자 계정이 auth.users엔 있으나 profiles가 없는 손상 상태(트리거 비활성/0001 미적용/외부 생성 고아)에서 재실행하면 안전장치 `raise exception`이 전체 시드를 중단시킨다. admin 시드와 동일한 의도된 fail-loud 가드(조용한 실패보다 즉시 드러냄)지만 자가복구 경로는 없다. 시드 자동화를 강화할 경우 profiles 부재 시 직접 삽입하는 self-heal 경로를 검토.
- **멱등 delete가 향후 listings 자식 테이블 FK를 가정하지 않음** [supabase/seed.sql:178] — 재실행 시 시드 매물을 delete 후 새 uuid로 재삽입한다. 현재 listings는 leaf 테이블이라 무해하나, 향후 즐겨찾기·구매기록 등 listings.id를 FK로 참조하는 테이블이 생기면 (a) delete가 막히거나 (b) 외부가 들고 있던 옛 listing id가 dangling 된다. 그런 자식 테이블 도입 시 시드 멱등 전략(고정 id 사용·자식 정리 순서)을 재설계할 것.

## Deferred from: code review of story 4-1 (2026-06-21)

- **DB 경로 견고화 — 커넥션 풀링·connect_timeout·async 블로킹 부재** [api/app/db/readonly.py, api/app/auth.py] — `readonly_connection()`은 호출마다 새 psycopg 연결을 열고 풀이 없어 동시 부하 시 Supabase Session 풀러(:5432, 낮은 연결한도)를 고갈시킬 수 있다. `connect_timeout` 미설정이라 풀러가 멈추면 요청이 무한 대기한다. 또 `get_current_user`·psycopg 호출이 동기인데 `async def` 안에서 실행돼 이벤트 루프를 블록한다. 4.1은 stub이라 `run_select`가 실제로 호출되지 않아 현재 영향 없음. 실제 DB 경로가 붙는 4.3에서 풀링·타임아웃·스레드풀/async 드라이버를 함께 도입할 것.
- **`context` 필드 크기·스키마 제약 없음(대용량 DoS 여지)** [api/app/schemas/ai.py:13] — `context: list | None`이 원소 타입·길이 제한이 없어 수 MB의 중첩 배열을 그대로 수용한다. spec이 "받아두되 무시(4.6)"로 의도한 필드라 현재 미사용·무해. 멀티턴 맥락을 실제로 읽는 4.6에서 원소 스키마·최대 길이를 강제할 것.
- **CORS 기본 origin이 127.0.0.1/Vercel preview/https 미포함** [api/app/main.py:24] — 기본값 `http://localhost:3000`은 `http://127.0.0.1:3000`·https·다른 포트·Vercel preview 도메인과 정확히 일치하지 않아, 해당 출처의 브라우저 호출이 차단된다. 코드 버그가 아니라 배포 설정 사안. 웹이 이 API를 실제 소비하는 4.7 배포 시 환경변수 `CORS_ORIGINS`에 preview/운영 도메인을 명시할 것.
- **0006 ALTER DEFAULT PRIVILEGES는 동일 소유자 생성 테이블만 적용** [supabase/migrations/0006_readonly_role.sql:33] — `alter default privileges ... grant select`는 이 ALTER를 실행한 롤이 만든 테이블에만 자동 적용된다. 4.2 `guide_documents`를 다른 소유자가 생성하면 `ai_readonly`가 SELECT를 못 받아 AI가 조용히 0건을 반환할 수 있다. 4.2 마이그레이션에서 `guide_documents`에 ai_readonly SELECT GRANT + permissive 정책을 명시적으로 추가할 것(스토리 Dev Notes에도 동일 메모 있음).

## Deferred from: code review of 4-3-경로-a-text-to-sql-안전장치 (2026-06-21)

- **AC4 단위 정규화·차형(세단) 매핑 결정론적 단위테스트 부재** [api/tests/] — "3천만원"→`price<=30000000`, "세단"→`body_type IN(...)` 등 AC4 충족 근거가 LLM 프롬프트 + 라이브 1회에만 존재한다. 결정론적 회귀 보호가 없어 LLM/프롬프트 변경 시 조용히 깨질 수 있다. LLM 출력을 모킹한 정규화·매핑 회귀 테스트를 후속으로 추가할 것.
- **FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버** [api/tests/test_auth.py] — 200 테스트가 `sql_rag_node`를 통째로 monkeypatch해, 실제 0건→`_ANSWER_EMPTY`(FR17) 경로와 `body_type IN(...)` SQL이 가드를 실제 통과하는지가 단위테스트로 확인되지 않는다. 노드 내부 분기·가드 IN-절 통과 케이스 테스트를 보강할 것.
- **LIMIT 비정수형(0/음수/`(10)`/OFFSET-only) 처리 미흡** [api/app/db/sql_guard.py:129] — `\blimit\s+(\d+)`가 `LIMIT 0`(오해성 0건)·`LIMIT -5`·`LIMIT (10)`·`OFFSET`-only를 정상 인식 못 해 잘못된 SQL 또는 오해성 빈 결과를 만든다. temp=0 프롬프트 특성상 발생 가능성은 낮고 대부분 fail-safe(오류→재시도→query_failed)라 후속으로 미룸. LIMIT 정규화/하한 검증을 강화할 것.
- **[4.5 설계 메모] 모호/광범위 질의는 "되묻기(clarify)"로 처리할 것** [api/app/graph/ — 4.5 라우터 스토리] — 4.3은 `DEFAULT_LIMIT=5`(brief "약 5개" 정합)로 확정. 다만 "차 보여줘" 같은 모호 질의를 그냥 5건으로 채우는 건 임시방편이며, 올바른 대응은 라우터(4.5)에서 "예산/차종이 어떻게 되세요?"라고 되묻는 것이다(research §4.3 "모호한 필터 → 라우터에서 되묻기"). **4.5 스토리 AC에 "모호·광범위 질의 → 조건 확인 되묻기(clarify/경로 C)"를 명시할 것. LIMIT 숫자 상향으로 풀지 말 것.**

## Deferred from: code review of 4-4-경로-b-문서-rag (2026-06-21)

- **근거 가이드에 유사도 임계값(거리 컷오프) 없음** [api/app/graph/doc_rag_node.py:64-68] — 가이드 검색이 `ORDER BY embedding <=> %s::vector LIMIT 1`로 거리와 무관하게 항상 최근접 1건을 가져와 `answer`에 무조건 `(참고: {제목})`을 붙인다. 의미상 동떨어진 가이드도 "근거"로 첨부돼 사용자를 오도할 수 있다. 단, 4.4 스펙은 answer를 단순 한국어 근거 요약으로 한정하고 정교한 근거→답변 합성은 4.5 `answer_node` 소관으로 명시했다(범위 밖). 4.5 `answer_node` 도입 시 코사인 거리 컷오프(`WHERE embedding <=> q < threshold`)나 거리 기반 첨부 조건을 적용할 것.

---

## 🟡 증분 아키텍처(bmad-create-architecture) 단계 보류 — 추가 기능 2건 (2026-07-13, party-mode)

> 증분 아키텍처 설계(`_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md`) Step 4 중 사용자가 제기한 2개 기능 안건. party-mode(📋John PM·💻Amelia Dev·📊Mary Analyst·🎨Sally UX)로 다방면 검토 후 **이번 증분엔 넣지 않고 보류**(사용자 결정, "구현까지 끝나면 추후 이어서"). 이번 증분엔 **"지금 하면 싼" 최소 대비만 낮은 우선순위**로 심어둠.

### ① 찜 기반 "인기 매물" 신호 (favorite / wishlist popularity)
- **무엇**: 랜딩 "인기 매물"을 조회수 단독이 아니라 **찜 수를 반영한 복합 신호**로. 예: `score = view_count + w·wishlist_count`.
- **왜 보류**: favorite_count 컬럼을 지금 만드는 건 YAGNI + 시드에 실제 찜 데이터가 없어 전부 0(콜드스타트 함정). (John·Amelia·Mary·Sally 합의)
- **이미 된 대비**: `wishlists(user_id, listing_id)`가 이번 증분(FR55)에 생성됨 → 찜 수는 `COUNT(*) GROUP BY listing_id`로 **언제든 파생 가능**, 스키마 재작업 불필요.
- **이어받을 때**: (a) 인덱스 `wishlists(listing_id)` 추가(1줄 additive) (b) 집계 쿼리(권장) 또는 필요 시 `listings.favorite_count` 역정규화 — 단 원천(wishlists)이 있으니 트리거 카운터는 정합성 부채, Amelia는 COUNT/집계 강권 (c) 표시 시 **임계값 게이팅(5명↑만 노출, "0명 찜" 낙인 방지)** + 카드 하단 중립 회색 메타(초록/앰버 색 안 씀 — Sally) (d) 봇 방어(view dedup) 없으면 조회수 오염 유입 → 찜 가중치 크게(Mary).

### ② 문서 기반 차량 상태 관리 (성능점검표·보험처리이력)
- **무엇**: 중고차 표준인 **성능점검표(사고부위·사고여부·영업용 이력)·보험처리이력(소유자 변경이력)** 데이터를 **자체 간소 양식(MD/PDF) 문서 기반으로 관리** + **매물 등록 시 그 데이터를 상태 컬럼으로 자동 반영** + **문서 다운로드**. (순수 기능 구현이 목표 — 검증/면책 "개선"이 아님)
- **확정된 방식(보류하되 설계 결정은 박제)**: **OCR·임베딩 없음**(자체 구조화 양식이라 파싱 불필요, 의미검색 유스케이스 없음 — Amelia·John). **신뢰 모델은 자기신고+면책 유지**(등급 격상 안 함 — 업계도 성능표·보험이력 오류[자비수리·거짓기재]로 플랫폼 무보증이 표준, 문서는 **"참고자료"로만** 제공 → 거짓 "검증됨" 주장 안 하므로 정직성 문제 없음. D3 초록뱃지·면책 그대로).
- **스키마(이어받을 때)**: `listing_documents(listing_id fk ON DELETE CASCADE, doc_type enum('inspection','insurance'), storage_path, created_at)` + 상태 필드 `usage_type`(자가용/영업용/렌트/리스) 추가(기존 `accident_status` enum·`is_single_owner`와 함께). **이미지 비공개 버킷+서명URL 인프라 재사용**.
- **이번 증분 대비(낮은 우선순위, "지금 하면 싼" 것)**: **이미지 Storage 서명URL 헬퍼·업로드 RLS·버킷 경로 규칙을 "이미지 전용"이 아니라 아티팩트 범용으로 작성** → 향후 `listing_documents`가 배관 재작업 없이 재사용. (증분 아키텍처 ADR-IMG-01에 이 설계 지침 반영)
- **시드 전략**: 기존 100건 = 문서 없음·상태 필드 미입력(as-is). **신규 ~50건(인기 국산 준중형·중형·대형 세단, 사용자가 나중 추가)** = 자체 양식 문서 기반으로 상태 필드 저장 + 다운로드. 문서→태그 도출 로직은 실제 판정 규칙과 일관되게(**주요 골격 수리=유사고 · 외판만 교환=단순교환 · 소유변경 0회=1인소유** — Mary).
- **표시(이어받을 때)**: 문서 있는 매물에 "성능점검표/보험이력 다운로드" 버튼(상세 신뢰 섹션, 비로그인 열람 허용, 서명URL), 없으면 버튼 숨김(기존 100건). 시드 문서는 마스킹 샘플(차대번호 등 개인정보) — Sally.
- **⚠️ 이어받기 전 확인 권장(Mary, 미검증)**: 개인 직거래(C2C)의 성능점검기록부 법적 의무 범위 · 각 사 인기 랭킹 공식.
- **관련**: 이 두 문서 데이터는 기술부채 #11(옵션 text[] 쉼표 라운드트립, `SellForm.tsx`)과 무관하나, 상태 필드 자동반영 로직은 SellForm 확장 시 함께 검토.

## Deferred from: code review of story 8-2 (2026-07-14)

- **Skeleton — AC3 "카드/행 조합" 중 행(row) 조합 누락** [web/src/components/ui/Skeleton.tsx] — `CardSkeleton`(카드형)만 제공되고 행(row)형 스켈레톤이 없다. AC3 원문은 "스켈레톤 로딩(`<Skeleton>` + 카드/행 조합)"으로 두 조합을 요구하지만, 채팅 목록·관리자 테이블 등 어떤 화면 기준의 행 형태를 만들지 스펙에 정의가 없어 지금 임의로 만들면 재작업 위험이 있다고 판단해 이월. **이월 사유(사용자): 소비처 생길 때 화면 기준으로.** 실제 소비 에픽(12 채팅·15 관리자 등)에서 행 형태가 필요해지면 그 화면 기준으로 `RowSkeleton` 추가할 것.
- **FocusTrap — 언마운트/숨김된 트리거로 복귀 시도 시 조용히 no-op** [web/src/components/ui/FocusTrap.tsx:243-246] — 트랩이 닫힐 때 열리기 전 활성 요소(`triggerRef.current`)로 포커스를 복귀시키는데, 그 요소가 그 사이 DOM에서 제거되거나 숨겨졌으면 `.focus()` 호출이 조용히 아무 일도 하지 않는다(크래시 없음, 포커스가 브라우저 기본값인 `<body>`로 남음). 트리거가 리스트 아이템처럼 삭제될 수 있는 맥락에서 소비될 경우, 포커스 복귀 실패에 대한 폴백(예: 컨테이너나 상위 랜드마크로 이동)을 검토할 것.
- **FocusTrap — `open=false`일 때 `children` 전체 언마운트, 내부 상태 소실** [web/src/components/ui/FocusTrap.tsx:249] — 트랩이 닫히면 `null`을 반환해 자식을 완전히 언마운트한다. 폼 입력값·스크롤 위치 등 자식의 내부 상태가 매번 사라지는 동작이 문서화돼 있지 않다. 실제 모달/바텀시트 UI를 붙이는 소비 에픽(11 내비 드롭다운·필터 바텀시트 등)에서 이 동작이 의도와 맞는지 확인하고, 상태 보존이 필요하면 CSS로 숨기는 방식으로 바꿀 것.
- **ErrorState — `tone="danger"`가 텍스트 색만 바꾸고 재시도 버튼은 톤 무관 동일** [web/src/components/ui/ErrorState.tsx:167-179] — `tone` prop이 메시지 텍스트 색만 전환하고 재시도 버튼 스타일은 항상 동일해, 파괴적/위험 에러와 일반 에러가 버튼 상으로는 시각 구분되지 않는다. 실제로 `tone="danger"`를 쓰는 소비 화면이 생기면 버튼도 톤에 맞춰 스타일 분기할지 검토할 것.
- **FocusTrap — 컨테이너에 `role="dialog"`/`aria-modal="true"` 미부착** [web/src/components/ui/FocusTrap.tsx] — 실제 모달 UI는 소비 에픽 몫(non-goal)이라는 스토리 경계상 FocusTrap 자체는 역할 속성을 강제하지 않는다. **소비 스토리 규약(사용자 확정)**: 모달·바텀시트·로그인 게이트 소비 스토리는 FocusTrap 컨테이너에 `role="dialog"` + `aria-modal="true"` + `aria-labelledby`를 반드시 부착한다(UX-DR22 접근성 바닥). 드롭다운·리스트박스는 `menu`/`listbox` role을 사용한다. 8.2 코드리뷰에서 FocusTrap이 `...rest` props를 컨테이너 div로 전달하도록 patch돼, 이 부착이 가능해졌다(11 내비 드롭다운·필터 바텀시트, 8.5 로그인 게이트 등 소비 에픽에서 반드시 적용할 것).

## Deferred from: code review of story-8.1 (2026-07-13)

### ✅ 결정됨: Pretendard 로딩을 CDN `<link>` → self-host `next/font/local`로 전환 (사용자 결정 2026-07-13)

아래 defer 2건은 **뿌리가 같다**(둘 다 수동 CDN `<link>` 방식의 부작용). self-host로 바꾸면 **한 번에 종결**된다. 데모 범위에선 현행 CDN 수용, **아래 작업으로 승격 확정**.

- **defer #1 — CDN `<link>` 렌더 블로킹** (`web/src/app/layout.tsx`): Pretendard를 jsDelivr CDN stylesheet로 `<head>`에서 로드 → 느린(실패 아님) CDN이 first paint를 지연시킬 수 있음. 명확한 실패(404/거부)는 폴백 스택이 빠르게 구제하지만 latency는 구제 못 함.
- **defer #2 — FOUT/CLS(metric-matched fallback 상실)** (`web/src/app/layout.tsx`): 수동 `<link>`가 next/font의 자동 size-adjust/ascent-override fallback을 잃음 → Pretendard 스왑 시 텍스트 리플로우(CLS).

**왜 self-host:** Pretendard는 Google Fonts에 없어 `next/font/google`은 불가하지만, `next/font/local`(폰트 파일 직접 제공)은 가능. next/font가 ① 폰트 self-host(외부 CDN 의존 제거 → #1 해소) ② 자동 fallback metric 보정(size-adjust → #2 해소)을 공짜로 제공.

**구현 노트(착수 시):**
1. Pretendard **Variable** `.woff2`를 `web/` 안에 배치(예: `web/src/app/fonts/` 또는 `web/public/fonts/`). 폰트 바이너리를 저장소에 추가하게 됨(현행 CDN은 파일 미포함이었음).
2. `next/font/local`로 로드 → `variable`을 `globals.css`의 `--font-sans` 우선순위에 연결(스택 자체는 폴백용으로 유지).
3. `layout.tsx`의 수동 `<link rel="stylesheet">` + `preconnect` 제거, `<html>`에 폰트 클래스 적용.
4. **⚠️ Next 16 관례 다름** — 코드 전 `node_modules/next/dist/docs/`의 next/font 가이드 선독(web/AGENTS.md 원칙). next/font/local API·metadata 관례 확인.
5. 검증: 브라우저 computed `font-family`=Pretendard·FOUT 없음(CLS 관찰)·`next build`·라이트/다크 E2E 재확인.

**시점:** 별도 후속 작업(작은 스토리 규모). 데모 실배포/실사용 전환 시점. **완료 시 위 defer 2건 종결.**
