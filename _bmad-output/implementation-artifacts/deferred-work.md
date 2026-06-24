# Deferred Work

## 🔍 검토 필요 — 미확정 (Epic 6 후 데모 사용 발견, 2026-06-24, party-mode 토론)

> 아래 2건은 **"할지 말지 아직 결정 안 됨"** 상태다. Epic 6 직후 사용자가 데모를 직접 써보며 발견한 4개 항목 중, 작은 2건(역할별 채팅 카피·폴링 3초)은 그날 핫픽스로 처리했고(커밋은 `fix(chat)` 참조), **나머지 2건(아래)은 "검토 필요"로 보류**한다. 무조건 구현이 아니라, Epic 7(Flutter) 착수 전 정보구조·디자인 결정과 함께 **다시 판단**할 사안이다.
>
> 토론 멤버(party-mode): 📋John(PM) 🎨Sally(UX) 🏗️Winston(Architect) 💻Amelia(Dev). 처리옵션 = A(회고/백로그) · B(즉시 핫픽스) · C(불필요).

- **[검토필요] 판매자의 '전체 매물 탐색' 진입 동선 빈약** [web/src/components/layout/AppHeader.tsx, web/src/app/(user)/search] — 판매자는 본인 매물 관리(/sell) 위주 동선이고, 구매자용 `/search`·`/listings`는 로그인하면 접근은 가능하나 **판매자에게 그리로 가는 진입 버튼이 없다**. ⚠️핵심: 이건 **결함이 아니다.** 판매자가 본인 매물에 문의→buyer=seller 꼬임은 이미 3중 차단(DB `CHECK(buyer<>seller)` + `0003c` 트리거 + UI '문의하기' 숨김)돼 있다. 남은 건 "판매자가 남의 차도 보고 싶을 수 있다"는 *신규 유스케이스*지 버그가 아님.
  - 토론 합의: **John=A(백로그), Sally=C(불필요, 새 버튼 추가 명시 반대 — 역할 혼란만 키움), Winston=C(권한경계 건드리면 RLS 재검증 비용 큼, 설계노트만), Amelia=C(가설 미검증, 추측 기능 금지).** → **다수가 "지금 코드 안 짬".** 단 "역할은 계정이 아니라 행위(판매자=잠재 구매자)"라는 설계 노트는 남길 가치 있음.
  - 판단 보류 이유: 데모 핵심 가치(판다→문의온다 / 산다→AI검색→문의)는 이 동선 없이 완결됨. **Epic 7 정보구조에서 역할 전환 UX를 재검토**할 때 함께 결정. 추측으로 버튼 추가 금지.

- **[검토필요] 헤더/레이아웃 정렬 일관성(사용자=상단 vs 관리자=중앙)** [web/src/components/layout/AppHeader.tsx, web/src/app/(admin)/layout.tsx] — 구매자/판매자 화면은 `AppHeader`(상단 정렬), 관리자 화면은 `(admin)/layout`(중앙 정렬 등) 기준이 달라 톤이 갈린다. 통일하려면 **공통 셸 추출 = 리팩터**(1줄 핫픽스 아님), admin 전 페이지 회귀 표면이 생김.
  - 토론 합의: **만장일치 A(회고/백로그), B(즉시 핫픽스) 반대.** 근거: ①다른 화면이라 평가자가 나란히 비교할 일 적음(상처<취향, Sally) ②**admin 중앙정렬이 의도된 차별화일 수 있어 버그로 단정 금지**(Amelia) ③데모 마감 직전 레이아웃 리팩터는 위험 대비 보상 나쁨(John).
  - 🏗️Winston 핵심 통찰: **"web 셸 정리 = 모바일 재작업 절감"은 부분적으로만 참.** Flutter는 React 셸을 재사용 못 한다(재사용되는 건 스키마·RLS·API 계약). 모바일은 위젯 트리를 새로 짠다. → **옮겨가는 건 코드가 아니라 "역할별 내비/정렬 규칙"이다.** 따라서 권고 = *CSS 셸 리팩터는 보류, 대신 "어떤 역할이 어떤 내비/정렬을 보는가" 규칙을 글로 문서화*해 Epic 7이 입력으로 쓰게. 정 거슬리면 `(admin)`만 상단 정렬로 맞추는 1줄 CSS는 별건으로 가능(셸 통합과 무관).
  - 판단 보류 이유: Epic 7 디자인 토큰/내비 매트릭스 정의 시 한 번에 정리하는 게 맞음. **지금 손대면 회귀 위험만.**

**메타 결정(만장일치): 쪼갠다.** 손 가벼운 2건(채팅 카피·폴링)은 즉시 처리 완료, 무게 있는 2건(위)은 "의도를 글로 남기고 Epic 7에서 재판단". main 병합은 평소대로 사용자 승인 시에만.

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
