# 기술부채 정리 (Technical Debt Register)

> *기술부채(technical debt)* — 지금 당장은 돌아가지만, "나중에 갚아야 할 빚"처럼 남겨둔 미완성·임시방편·미검증 항목. 방치하면 이자(장애·재작업)가 붙는다.

- **작성일:** 2026-07-10
- **출처:** `_bmad-output/implementation-artifacts/deferred-work.md`(코드리뷰 이월분) + Epic 7 회고 + 코드 스캔(TODO)
- **기준 상태:** 모든 에픽(1~7) + 회고 done. develop = main = 원격 완전 동기, 워킹트리 클린, 릴리스 태그 `v1.0.0`.
- **읽는 법:** 🔴 = 운영/제출 전 필수 · 🟡 = 조건부(지금 무해, 조건 바뀌면 위험) · 🟢 = 품질·테스트 보강 · ⚪ = 의도적 보류(부채 아님, 참고용)

---

## 요약 대시보드

| 우선순위 | 건수 | 한 줄 |
|---|---|---|
| 🔴 필수 | 1 | 안드로이드 서명 (※ 시드 평문 비번은 2026-07-11 세션변수 주입으로 해소 → 부록. 앱 픽셀 E2E·AI 라이브 호출도 실폰 검증으로 해소 → 부록) |
| 🟡 조건부 | 8 | DB 커넥션 풀·채팅 멱등키·폴링 무알림·본문 길이·재오픈 차단·오픈리다이렉트·options 쉼표·타입 |
| 🟢 품질/테스트 | 5 | AI 정규화 회귀테스트 · FR17 경로 · LIMIT 파싱 · 가이드 거리 컷오프 · 컨트롤러 단위테스트 |
| ⚪ 의도적 보류 | 3 | 데스크톱 반응형(Cut) · 관리자 대시보드(Cut) · "홈이 탐색 직접 품기" |

---

## 🔴 운영/제출 전 반드시 처리

### 2. 안드로이드 릴리스 서명 미설정
- **위치:** `app/android/app/build.gradle.kts:30` (코드 내 유일한 TODO)
- **내용:** release 빌드가 아직 debug 서명 설정을 씀. `// TODO: Add your own signing config for the release build.`
- **왜 위험:** 정식 스토어 배포·서명된 APK 산출 불가.
- **해소:** 실제 배포 시 keystore 생성 + `signingConfigs` 설정. (Epic 7 회고 이월, app은 현재 수동 배포 전이라 즉시 영향은 없음)

> ℹ️ 구 #3(앱 픽셀 E2E 미검증)·#4(AI 라이브 호출 0회)는 **2026-07-11 실폰 무선 디버깅 검증으로 해소** → 하단 `부록: 해소된 부채` 참조.

---

## 🟡 조건부 부채 (지금 무해, 조건이 바뀌면 위험)

> *조건부(conditional)* — 현재 코드 경로에선 발생하지 않지만, 특정 기능·규모·입력이 도입되면 터지는 부채.

### 5. AI API DB 커넥션 풀링·타임아웃·async 블로킹 부재
- **위치:** `api/app/db/readonly.py`, `api/app/auth.py`
- **내용:** `readonly_connection()`이 호출마다 새 psycopg 연결을 열고 풀이 없음 → 동시 부하 시 Supabase Session 풀러(:5432, 낮은 연결한도) 고갈 가능. `connect_timeout` 미설정이라 풀러가 멈추면 무한 대기. 동기 호출이 `async def` 안에서 실행돼 이벤트 루프 블록.
- **트리거:** AI 검색 동시 사용자가 늘어날 때.
- **해소:** 실제 DB 경로가 붙은 지금, 커넥션 풀 + `connect_timeout` + 스레드풀/async 드라이버 도입. (원래 4.3에서 도입 예정이었던 항목)

### 6. 채팅 커밋 후 응답 유실 시 중복 전송 (멱등키 부재)
- **위치:** `web/.../chat/[roomId]/ChatRoomMessages.tsx` (handleSubmit catch)
- **내용:** INSERT가 DB엔 성공했으나 응답이 네트워크에서 끊기면 catch가 입력을 복원 → 사용자 재전송 → 서로 다른 id의 중복 메시지 영속(id 기준 dedupe로 못 막음).
- **트리거:** 불안정 네트워크에서 전송 중 끊김.
- **해소:** 멱등키(클라 생성 uuid를 PK로) 도입. 데모 범위 밖이라 보류.

### 7. 채팅 폴링 영구 실패 시 무알림
- **위치:** 동상 (폴링 effect)
- **내용:** 첫 로드 실패는 한국어 에러로 표시(loud)하지만, 세션 만료·방 삭제로 폴링이 매 주기 영구 실패하면 아무 표시 없이 대화가 멈춘 것처럼 보임(silent). loud/silent 비대칭.
- **트리거:** 장시간 방치 후 세션 만료, 관리자의 방 삭제.
- **해소:** N회 연속 실패 후 비차단 배너(재연결/오프라인 표시).

### 8. 채팅 본문 최대 길이 가드 없음
- **위치:** `web/src/lib/messages.ts` (sendMessage / 입력창)
- **내용:** `body`가 `text`(무제한), 클라는 `trim()`만. 초대용량 붙여넣기가 그대로 INSERT → 행·폴링 페이로드 비대화.
- **트리거:** 대용량 텍스트 붙여넣기.
- **해소:** 입력창 `maxLength` + 서버측 길이 컷.

### 9. sold→on_sale 재오픈 DB 미차단 (단방향 트리거 없음)
- **위치:** `supabase/migrations/0002_listings.sql`, `web/.../sell/ListingActions.tsx`
- **내용:** `listings_update_own` RLS는 소유권만 보고 status 전이 방향을 강제하지 않음. 본인 sold 매물을 `update status='on_sale'`로 재오픈하는 것이 DB 차원에서 가능(현재 UI엔 재오픈 경로 없어 무해).
- **트리거:** 재오픈 UI 도입 시.
- **해소:** BEFORE UPDATE 트리거(`old.status='sold' → 거부`) 또는 RLS WITH CHECK로 단방향 고정 명시.

### 10. open-redirect 검증 규약 미정
- **위치:** `web/src/proxy.ts`, `web/.../login/page.tsx`
- **내용:** proxy가 보호경로 차단 시 `/login?redirectedFrom=<pathname>`을 동봉하지만 로그인 화면은 안 읽고 항상 `/`로 이동(현재 무해).
- **트리거:** "로그인 후 원래 위치 복귀" 기능 도입 시.
- **해소:** `redirectedFrom` 값이 `/`로 시작하는 상대경로인지 검증(`//`·`http(s):`·역슬래시 차단)해 오픈 리다이렉트 방지.

### 11. options(text[]) 쉼표 포함 값 라운드트립 손실
- **위치:** `web/.../sell/SellForm.tsx`
- **내용:** 수정 폼이 options를 쉼표로 join/split. 폼 밖(시드·API)에서 한 배열원소에 쉼표를 넣으면 첫 수정 저장 시 둘로 쪼개짐(현재 폼 입력만으론 발생 안 함).
- **트리거:** 시드/가이드/임베딩에서 쉼표 포함 옵션 도입 시.
- **해소:** 입력 구분자 변경(줄바꿈) 또는 칩(chip) UI.

### 12. `OwnListing.status` 타입이 `string` (union 미사용)
- **위치:** `web/src/app/(user)/sell/page.tsx:21`
- **내용:** cosmetic. `LISTING_STATUS.ON_SALE` 비교는 정상이나 union 타입이면 오타·미정의 status 비교를 컴파일타임에 잡음.
- **해소:** 다른 select 타입 정리 시 union으로 좁힘.

---

## 🟢 품질 / 테스트 보강 (기능 정상, 회귀 보호 부족)

> *회귀(regression)* — 잘 되던 게 나중 변경으로 조용히 깨지는 것. 자동 테스트가 없으면 못 알아챔.

### 13. AI 단위 정규화·차형 매핑 결정론적 단위테스트 부재
- **위치:** `api/tests/`
- **내용:** "3천만원→price≤30000000", "세단→body_type IN(...)" 근거가 LLM 프롬프트 + 라이브 1회에만 존재. 프롬프트 변경 시 조용히 깨질 수 있음.
- **해소:** LLM 출력을 모킹한 정규화·매핑 회귀 테스트 추가.

### 14. FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버
- **위치:** `api/tests/test_auth.py`
- **내용:** 200 테스트가 `sql_rag_node`를 통째로 monkeypatch → 실제 0건→`_ANSWER_EMPTY`(FR17) 경로와 `body_type IN(...)` SQL의 가드 통과가 단위테스트로 미확인.
- **해소:** 노드 내부 분기·가드 IN-절 통과 케이스 테스트 보강.

### 15. LIMIT 비정수형 처리 미흡
- **위치:** `api/app/db/sql_guard.py:129`
- **내용:** `\blimit\s+(\d+)`가 `LIMIT 0`(오해성 0건)·`LIMIT -5`·`LIMIT (10)`·`OFFSET`-only를 정상 인식 못 함. temp=0라 발생 가능성 낮고 대부분 fail-safe.
- **해소:** LIMIT 정규화/하한 검증 강화.

### 16. 가이드 RAG 유사도 임계값(거리 컷오프) 없음
- **위치:** `api/app/graph/doc_rag_node.py:64-68`
- **내용:** 가이드 검색이 거리와 무관하게 항상 최근접 1건(`ORDER BY embedding <=> q LIMIT 1`) → 의미상 동떨어진 가이드도 "근거"로 첨부돼 오도 가능.
- **해소:** 코사인 거리 컷오프(`WHERE embedding <=> q < threshold`) 적용. (4.5 answer_node 소관으로 명시됨)

### 17. Flutter 컨트롤러 단위 테스트 부재 (Epic 7 이월)
- **위치:** `app/lib/features/**/` 컨트롤러
- **내용:** 전역 Supabase 의존으로 컨트롤러 단위 테스트 미작성, live 스모크로 갈음.
- **해소:** fake Supabase 클라이언트 도입 시 보강(선택).

---

## ⚪ 의도적 보류 (부채 아님 — 제품 결정, 참고용)

> party-mode 2라운드(2026-06-24)로 확정. 되살릴 필요 없으나 재검토 시 근거 참조.

- **데스크톱 반응형 (Cut):** 만장일치. 전 화면 레이아웃 회귀 위험 + 모바일 이월 0. Flutter가 별도 담당.
- **관리자 대시보드 (Cut/보류):** UI는 web 전용 표현. 집계 쿼리(데이터 계약)만 모바일 관리자 확정 시 별도.
- **"홈이 탐색을 직접 품기" 전체판 (보류):** 현재는 미리보기판(최근 N건 읽기전용 + 더보기→/search). 홈이 필터·URL을 직접 소유하는 전체판은 이후 판단.

---

## 부록: 해소된 부채 (참고)

- **[구 🔴 #1] 시드 계정 평문 비밀번호 커밋** — **2026-07-11 세션변수 주입으로 해소.** `supabase/seed.sql`(및 생성기 `_bmad-output/.../seed-expansion-block.sql`·`gen_seed_expansion_sql.py`)에서 데모 시드 계정의 평문 비밀번호를 제거하고, 실행 시 PostgreSQL 세션 변수 `app.seed_password`로 주입(`current_setting`)하도록 변경. 미설정 시 시드 상단 게이팅 블록이 예외로 즉시 중단(fail-closed). 데모/E2E 로그인 비번은 저장소 미추적 파일 `supabase/.env.seed`(템플릿 `supabase/seed-secret.example`)로 이관. 로그인 문서(`docs/e2e-test-cases.md`·`e2e-checklist.md`)도 비번 칸을 파일 참조로 교체. 라이브 데모 DB는 멱등 시드라 기존 계정 비번 불변(로테이션 안 함) → 배포된 web·Flutter 데모 계속 작동. (과거 BMAD 스토리 아티팩트의 평문 언급은 불변 기록이라 미변경.)
- **[구 🔴 #3] 앱 픽셀 E2E 미검증** — **2026-07-11 실폰 무선 디버깅으로 해소.** Flutter 앱 6개 화면 흐름(구매자 탐색·상세 / 판매자 등록·관리 / 채팅 / AI검색)을 실기기에서 직접 눌러 렌더·동작 확인. Epic 7 개발 당시 검증 PC(RAM 6GB) 한계로 미수행했던 것을 실기기 검증으로 마감.
- **[구 🔴 #4] AI 검색 라이브 호출 0회** — **2026-07-11 실폰 검증으로 해소.** 앱에서 AI 매물검색을 실제 호출 → 매물 카드 정상 노출 확인(`API_BASE_URL` 주입 + 라이브 응답 실증). 정적 계약 갈음이 실제 동작으로 승격됨.
- **Supabase 클라이언트 env 누락 가드** — Story 1.4에서 `getSupabaseEnv()`로 일원화 해소.
- **판매자 본인 매물 문의 차단(buyer=seller)** — Epic 5에서 3중 안전장치(UI 숨김 + BEFORE INSERT 트리거 + CHECK 제약) 실증, 검토 안건에서 제외.
- **관리자 상세 '돌아가기'·역할별 정렬 통일** — Epic 7 직전 즉시 완료.

---

## 다음 액션 (제출 로드맵)

1. **운영 전 보안 마감** — 🔴 #2 안드로이드 서명. (남은 🔴 1건 · #1 시드 비번은 해소 → 부록)
2. **E2E 크로스체크 테스트** — 웹(https://bmad-encar-demo.vercel.app) ↔ Flutter(실폰) 동일 테스트셋으로 **불일치(divergence) 적발**. 실폰 단발 검증(구 #3·#4)은 끝났으나, 웹↔모바일 체계적 대조(57케이스 등)는 성격이 다르므로 별도 잔존.
3. **여력 시 하드닝** — 🟡 #5 DB 풀링(부하 대비 우선), 나머지는 해당 기능 도입 시.
