# 02. 백엔드 API — FastAPI (AI 검색 전용 서버)

> 이 백엔드는 **"AI 검색 한 가지"만** 담당하는 Python 서버입니다. 회원가입·매물등록 같은 일반 기능은 프론트가 Supabase로 직접 가므로 여기 없습니다.
> 대상 코드: `api/app/` (단, `graph/` 폴더의 AI 로직은 [03번 문서](03-langgraph-ai.md)에서 따로 다룹니다).

이 문서는 "요청이 들어와서 응답이 나가기까지의 뼈대(인증·검증·안전장치)"를 다룹니다. 실제 AI 두뇌(LangGraph)는 03번에서.

---

## 2-1. FastAPI가 뭔가요

- *FastAPI*: Python으로 웹 API 서버를 만드는 프레임워크. "이 주소로 요청이 오면 이 함수를 실행해라"를 간단히 선언합니다.
- *API(Application Programming Interface)*: 프로그램끼리 데이터를 주고받는 규약. 여기선 "프론트 ↔ AI 서버" 사이의 약속.
- *엔드포인트(endpoint)*: API의 각 주소(예: `POST /ai/search`). "무엇을 하는 창구"인지를 나타냄.

이 서버의 유일한 핵심 엔드포인트는 **`POST /ai/search`** 입니다. (그 외 `/health`는 "서버 살아있나?" 점검용)

---

## 2-2. 파일별 역할 한눈에

| 파일 | 역할 |
|------|------|
| `main.py` | 서버 시작점. 라우터 등록, CORS, 공통 에러 포맷 |
| `config.py` | 환경변수(비밀값·설정) 로드 |
| `auth.py` | 로그인 토큰(JWT) 검증 — 로그인한 사람만 AI 검색 가능 |
| `schemas/ai.py` | 요청·응답 데이터의 "모양" 정의 (Pydantic) |
| `routers/ai.py` | `/ai/search` 창구. 인증→그래프 호출→응답 |
| `db/readonly.py` | "읽기 전용" DB 접속 |
| `db/sql_guard.py` | AI가 만든 SQL을 실행 전에 검사하는 **안전장치** |
| `embeddings.py` | Gemini로 텍스트를 임베딩 벡터로 변환 |

---

## 2-3. 요청이 들어와 응답이 나가기까지 (전체 흐름)

사용자가 "3천만원 이하 흰색 SUV 추천해줘"를 입력하면, 브라우저/앱이 이런 요청을 보냅니다:

```
POST /ai/search
Authorization: Bearer <로그인 토큰>
{ "query": "3천만원 이하 흰색 SUV 추천해줘",
  "context": [ ...이전 대화(있으면)... ] }
```

서버 처리 순서:

```
① main.py        요청 도착. CORS 검사(허용된 출처인가?)
       ↓
② schemas/ai.py  요청 모양 검증 (query 1~1000자? context 12턴 이하?)  ← 틀리면 422
       ↓
③ auth.py        토큰 검증 (로그인한 사람 맞나?)                        ← 없으면 401
       ↓
④ routers/ai.py  run_search(query, context) 호출 → LangGraph(03번)로 위임
       ↓             ├ 경로 A: 자연어→SQL→sql_guard 검사→읽기전용 실행
       ↓             ├ 경로 B: 임베딩 유사도 검색
       ↓             └ 경로 C: 정중한 거절
       ↓
⑤ routers/ai.py  결과를 {answer, listings[]} 로 응답               ← 200 OK
```

각 단계를 아래에서 풉니다.

---

## 2-4. main.py — 서버의 현관

- `app = FastAPI(...)` 로 앱을 만들고, `app.include_router(ai.router)` 로 `/ai` 창구를 연결합니다.
- **CORS 설정** — 어느 웹사이트(출처)가 이 API를 불러도 되는지 허용 목록을 둡니다.
  - *CORS(Cross-Origin Resource Sharing)*: 브라우저 보안 규칙. "다른 도메인의 API를 함부로 못 부르게" 막는 것을, 허용 목록으로 풀어줌. (예: `localhost:3000`, Vercel preview 주소)
- **공통 에러 핸들러 3종** — 어떤 에러든 항상 같은 모양 `{"error":{"code":..., "message":...}}` 으로 응답하게 통일. 서버 내부 오류(500)는 자세한 스택은 로그에만 남기고 사용자에겐 일반 문구만 보여줌(정보 누출 방지).

---

## 2-5. config.py — 설정/비밀값 로드 (fail-loud 원칙)

- `pydantic-settings`로 `.env` 파일의 값(Supabase URL, `GEMINI_API_KEY`, DB 주소 등)을 읽습니다.
- 특징: **비밀값이 없어도 서버는 일단 켜집니다.** 대신 실제로 그 값이 필요한 순간(`require()` 호출)에 명확한 한국어 에러를 던집니다.
  - *fail-loud(요란하게 실패)*: 문제를 조용히 숨기지 않고, 바로 분명한 에러로 알리는 방식 → 디버깅이 쉬움.
- 모델 버전을 `gemini-3.1-flash-lite`처럼 **명시**해 둡니다(별칭은 어느 날 바뀔 수 있어 위험).

---

## 2-6. auth.py — 누가 로그인했는지 검증 (JWT)

- *JWT(JSON Web Token)*: 로그인하면 받는 "신분증 같은 암호화 토큰". 요청마다 같이 보내면 서버가 "이 사람 누구"인지 확인.
- `get_current_user()` 함수가 핵심:
  1. 요청 헤더의 `Bearer 토큰`을 꺼냄. 없으면 **401(미인증)**.
  2. Supabase에 "이 토큰 유효해?"라고 물어봄(`client.auth.get_user(token)`).
  3. 토큰이 가짜면 **401**, Supabase 자체가 잠깐 장애면 **503**(일시적 오류라 사용자를 부당하게 막지 않으려 구분).
- 이 함수를 `Depends(get_current_user)`로 엔드포인트에 붙이면, **로그인 검증이 자동으로** 끼어듭니다.
  - *의존성 주입(Dependency Injection)*: "이 함수 실행 전에 먼저 이걸 처리해줘"를 FastAPI가 대신 해주는 구조. 인증·DB연결 등에 씀.

---

## 2-7. schemas/ai.py — 데이터의 "모양" 약속 (Pydantic)

- *Pydantic*: 데이터의 형태(타입·길이·필수 여부)를 클래스로 선언하면, 들어온 JSON을 자동 검증·변환해 주는 라이브러리.
- 주요 모델:
  - `SearchRequest`: 요청. `query`(1~1000자, 공백만 금지), `context`(최대 12턴).
  - `ConversationTurn`: 대화 한 턴. `role`("user"/"assistant"), `content`(1~2000자).
  - `ListingCard`: 매물 카드 7필드(id, 제조사, 모델, 연식, 가격, 주행거리, 지역). 사진 없음.
  - `SearchResponse`: 응답. `answer`(자연어 문장) + `listings`(카드 목록).
  - `RouterDecision`: AI가 질문을 A/B/C 중 무엇으로 분류했는지(03번에서 사용).

> 모양이 안 맞으면 FastAPI가 자동으로 422 에러를 돌려줍니다. 코드를 안 짜도 검증이 됩니다.

---

## 2-8. routers/ai.py — `/ai/search` 창구

```python
@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, user=Depends(get_current_user)):
    try:
        result = run_search(req.query, req.context)   # ← LangGraph(03번) 호출
    except SqlGuardError as exc:
        raise HTTPException(400, ...)   # AI가 만든 SQL이 안전장치에 걸림 → 400
    except Exception:
        raise HTTPException(500, ...)   # 그 외 장애 → 500
    return SearchResponse(answer=result["answer"], listings=result["listings"])
```

- `Depends(get_current_user)`로 **인증을 강제**(미인증이면 함수 자체가 실행 안 됨).
- 실제 AI 작업은 `run_search()`(LangGraph)에 위임하고, 여기선 **인증 + 에러 분류 + 응답 포장**만 담당.

---

## 2-9. db/readonly.py — 읽기 전용 DB 접속

- AI 검색은 절대 데이터를 바꾸면 안 되므로, DB에 접속한 직후 **`SET ROLE ai_readonly`** 로 권한을 "읽기 전용"으로 낮춥니다(01번 0006 참고).
- 이 롤로는 INSERT/UPDATE/DELETE가 DB 차원에서 거부됩니다 → AI가 실수로(혹은 악용으로) 데이터를 바꿀 수 없음.
- `run_select(query, params)` 로 SELECT만 실행합니다.
- *연결 풀러(pooler)*: DB 접속을 효율적으로 재사용하는 중간 계층. 여기선 `SET ROLE`이 유지되는 Session pooler(포트 5432)를 써야 함.

---

## 2-10. db/sql_guard.py — AI가 만든 SQL 검사 (이 백엔드의 백미)

AI(LLM)에게 "자연어를 SQL로 바꿔줘"라고 시키면 편하지만, **LLM이 위험하거나 엉뚱한 SQL을 만들 수도** 있습니다. 그래서 만들어진 SQL을 **실행 전에 코드가 한 줄씩 검사**합니다. `validate_select_sql()`이 막는 것들:

1. **여러 문장 금지** — `;`로 문장을 이어붙이는 공격(스태킹) 차단.
2. **주석 금지** — `--`, `/* */` 로 검사를 우회하려는 시도 차단.
3. **SELECT만 허용** — INSERT/UPDATE/DELETE/DROP 등 위험 키워드 전부 거부.
4. **OR 금지** — `status='on_sale' OR price<9e9` 처럼 **판매완료 숨김을 무력화**하는 트릭 차단.
5. **서브쿼리 금지** — 중첩 SELECT로 LIMIT 상한을 우회하는 것 차단.
6. **테이블/컬럼 화이트리스트** — `listings` 테이블의 정해진 컬럼만 허용(`SELECT *` 금지, 환각 컬럼 거부).
7. **`status='on_sale'` 필수** — 판매완료 매물이 검색에 새지 않도록 강제.
8. **LIMIT 자동 부여/상한** — 결과 개수를 기본 5개, 최대 50개로 제한.

> *화이트리스트(whitelist)*: "허용 목록만 통과, 나머지는 전부 거부" 방식(블랙리스트보다 안전).
> *SQL 인젝션*: 입력값에 악성 SQL을 섞어 DB를 조작하는 공격.

**핵심 사상 = 다층 방어**: 이 검사(1차)를 뚫더라도, 실행은 무조건 읽기 전용 롤(2차)이라 데이터를 못 바꿉니다. "한 겹이 뚫려도 다음 겹이 막는다."

---

## 2-11. embeddings.py — 텍스트를 의미 벡터로

- Gemini 임베딩 API로 텍스트를 **768개 숫자(벡터)** 로 바꿉니다.
- 받은 벡터를 **L2 정규화**(길이를 1로 맞춤)합니다. 이 모델은 자동 정규화가 안 돼서, 안 하면 코사인 유사도 검색 품질이 떨어집니다.
  - *L2 정규화*: 벡터의 크기를 1로 통일 → 방향(=의미)만으로 비교하게 함.
- NaN/무한대 값이 섞이면 DB에 넣기 전에 막습니다(fail-loud).
- 용도 구분: 문서 저장용(`embed_documents`)과 질문 검색용(`embed_query`)의 task_type이 다릅니다.

---

## 2-12. 핵심 개념 정리 (이 파트에서 꼭 배워야 할 것)

1. **FastAPI 라우팅** — `@router.post(...)`로 엔드포인트 선언, `include_router`로 등록.
2. **Pydantic 스키마** — 요청/응답 모양을 선언하면 검증·변환 자동.
3. **JWT 인증 + 의존성 주입** — `Depends(get_current_user)`로 로그인 검사를 자동화.
4. **읽기 전용 DB 롤** — AI에게 최소 권한만(SELECT) 부여하는 보안.
5. **SQL 인젝션 방어 / 화이트리스트** — LLM이 만든 SQL을 절대 그대로 믿지 않고 검사.
6. **다층 방어(defense in depth)** — 검사(코드) + 권한(DB)을 겹쳐 쌓기.
7. **공통 에러 포맷 + 상태코드** — 400/401/422/500/503의 의미와 일관된 응답.
8. **환경변수 + fail-loud** — 비밀값은 코드 밖에서 주입, 없으면 분명히 알리기.
9. **임베딩과 정규화** — 텍스트→벡터 변환과 코사인 유사도의 전제.
10. **무상태(stateless) 서버** — AI 대화는 DB에 저장 안 하고, 매 요청에 `context`로 같이 보냄.

---

다음: [03-langgraph-ai.md](03-langgraph-ai.md) — `run_search()` 안에서 벌어지는 AI 두뇌의 실제 동작.
