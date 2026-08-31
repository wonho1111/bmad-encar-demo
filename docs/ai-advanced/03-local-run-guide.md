# 03 — 로컬 실행 가이드 (데스크톱 시연용)

> 정본. PDF 사본은 이 문서를 렌더한 것. 갱신은 여기서 먼저.

## 구성도

```
[브라우저 localhost:3000]
        │
        ▼
┌─ 웹 (Next.js, :3000) ─────────── web/.env.local ─┐
│  매물 목록·상세·로그인 ──────────► 클라우드 Supabase │
│  AI 채팅·시세 카드 ──┐                             │
└─────────────────────│─────────────────────────────┘
                      ▼
┌─ API (FastAPI, :8000) ─────────── api/.env ───────┐
│  툴콜링 에이전트(Gemini flash-lite)                │
│   ├ search_listings / market_price_stats ──► 클라우드 Supabase(읽기전용 롤)
│   ├ search_guides ──► 임베딩 검색 + ──► 리랭커(:8801)
│   ├ TabPFN 적정가(프로세스 내, CPU)                │
│   └ LangSmith 트레이스(자동)                       │
└───────────────────────────────────────────────────┘
                      ▼
┌─ 리랭커 사이드카 (:8801, GPU cuda) ───────────────┐
│  BAAI/bge-reranker-v2-m3 상주 (죽어도 API는 벡터순 폴백) │
└───────────────────────────────────────────────────┘
```

## 실행 (터미널 3개, 이 순서대로)

```bash
# ① 리랭커 (첫 로드 ~25초, "리랭커 모델 로드 완료 device=cuda" 나오면 준비됨)
bash /home/whlee/workspace/bmad-encar-demo/scripts/dev-reranker.sh

# ② API (리랭커 주소를 환경변수로 알려주며 실행)
cd /home/whlee/workspace/bmad-encar-demo/api && RERANKER_URL=http://127.0.0.1:8801 .venv/bin/uvicorn app.main:app --port 8000

# ③ 웹
cd /home/whlee/workspace/bmad-encar-demo/web && npm run dev
```

- 순서 이유: ②가 ①의 주소를 받아야 하고(없어도 뜨지만 리랭커 미사용), ③은 ②가 있어야 AI 기능이 산다.
- 종료: 각 터미널 Ctrl+C. 코드 수정 후엔 **API만 재시작하면 반영**(웹은 자동 리로드, 리랭커는 모델만 쓰므로 재시작 불필요).

## 상태 확인

```bash
curl -s http://127.0.0.1:8801/health   # {"status":"ok","device":"cuda"}
curl -s http://127.0.0.1:8000/health   # API 응답 확인
```

브라우저: `localhost:3000` → 로그인 → 매물 상세 → [AI 시세 진단].

## 설정 파일 지도

| 파일 | 내용 | 주의 |
|---|---|---|
| `api/.env` | Supabase·DB·Gemini·LangSmith 키 | gitignore. 이동 시 메신저 금지(Zone.Identifier 유출 사고 이력) |
| `web/.env.local` | Supabase(클라우드)·API 주소(`localhost:8000`) | 로컬 Supabase로 바꾸면 API와 DB가 갈라짐 — 백업본 `.bak-localsupabase` 참고 |
| `RERANKER_URL` | API 실행 시 환경변수로만 | 미설정 = 리랭커 없이 벡터순(오류 아님) |

## 기계 검증 3종 (전부 읽기전용, api/ 에서)

```bash
.venv/bin/python scripts/verify_market_engine.py --sample 60   # 시세 엔진 불변식(전수는 --sample 생략)
.venv/bin/python scripts/verify_answer_numbers.py --limit 20   # LLM 설명문 수치 환각 검사(LangSmith 소급)
.venv/bin/python scripts/verify_agent_regression.py            # E2E 골든 22질의(실 LLM, ~2분·몇십 원)
```

## 트러블슈팅 (실제 겪은 것)

| 증상 | 원인 | 조치 |
|---|---|---|
| 웹 "AI 검색 서버에 연결하지 못했습니다" | API(:8000) 안 떠 있음 | ② 실행 |
| 웹 매물 목록 "불러오지 못했습니다" + ECONNREFUSED 55321 | web/.env.local이 로컬 Supabase를 봄 | 클라우드 값으로 (현재 상태 유지) |
| 리랭커 브라우저 접속 시 Not Found | 정상 — 첫 화면 없음 | `/health`로 확인 |
| 시세 카드에 적정가 "표본 부족" | 해당 모델군 매물 10건 미만 | 정상 동작(시드 3모델은 거의 항상 나옴) |
| 진단 차트가 안 나옴 | 추천 응답(카드 2장 이상)은 의도적으로 차트 억제 | 매물 1건 지목 질의로 |
