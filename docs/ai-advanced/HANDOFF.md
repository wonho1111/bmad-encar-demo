# AI 고도화 과제 — 데스크톱 이어받기 핸드오프

> 새 장비(데스크톱, RAM 16GB + GTX 1060 3GB)의 새 세션이 **첫 입력으로 읽는 문서**.
>
> **진행 현황(2026-08-30 데스크톱)**: §0 체크리스트 완료(CUDA cu126 휠로 GPU 게이트 통과, 리랭커 GPU 1.1초/10건 — 01 문서 §7).
> 2단계 완료(엔카 실측 보정 시드 150건+기존 7건 조정, 02 문서). 3단계 완료(market_price.py+API).
> 4단계 완료(툴콜링 에이전트 agent.py+도구 4종, 리랭커 사이드카 reranker_service.py+scripts/dev-reranker.sh, DW-847·848·849 resolved).
> 5단계 완료(상세 [AI 시세 진단] 버튼→채팅 프리필+listing_id, MarketDiagnosis 산점도 렌더, TabPFN 학습표본은 기본 모델군으로 분리). **과제 5단계 전체 완료** — 남은 것은 사용자 실기 확인·시연 준비. 리랭커는 RERANKER_URL 설정 시에만 활성(미설정=벡터순 폴백, scripts/dev-reranker.sh).
> **제출 구성 확정(2026-09-01, 사용자 결정)**: 웹=Vercel·API=Cloud Run(TabPFN 내장, dev 2Gi 실측 검증), **리랭커는 클라우드 미배포** — 배포 링크는 벡터순 폴백으로 전 기능 동작, 리랭커는 로컬 GPU 실행·문서(01)·실측으로 증빙. 시연 자리에서만 선택적으로 cloudflared 터널 + RERANKER_URL로 GPU 연결(03 가이드 3번).
> 노트북 세션(2026-08-29~30)의 결정·실측·다음 단계를 담는다. 작성 시점 develop 최신 = `c5367c7` 이후.

## 0. 데스크톱 준비 체크리스트 (작업 시작 전 1회)

| # | 할 일 | 왜 |
|---|---|---|
| 1 | `git pull origin develop` (브랜치 develop 확인) | 코드·스킬·문서 전부 여기로 온다 |
| 2 | **노트북의 `api/.env`를 그대로 복사** | gitignore 대상. Gemini·Supabase·DB·LangSmith 키 — 유일하게 손으로 옮길 파일 |
| 3 | `cd api && pip install -r requirements.txt` 또는 uv sync (기존 방식대로) | 파이썬 의존성 |
| 4 | `npx -y skills add vercel-labs/skills --skill find-skills` | find-skills는 전역 설치라 git으로 안 옴. 과제용 스킬 6종은 레포 `.claude/skills/`로 이미 따라옴 |
| 5 | 벤치 재측정: `api/scripts/bench/` 스크립트로 venv 새로 만들어(짧은 경로 권장, 예: `C:\bench\venv` — 노트북에서 MAX_PATH 260자 문제로 subst 우회했음) 리랭커·TabPFN 재실행. **torch는 CUDA 휠로 설치해 GTX 1060(Pascal, sm_61)이 최신 PyTorch에서 지원되는지 먼저 확인** — 미지원이면 CPU 휠 + 플랜B(아래 §3) | 최종 합격 판정은 이 장비 기준. HF 모델(~4.3GB)은 첫 실행 시 자동 다운로드 |
| 6 | (주의) tabpfn은 **반드시 `tabpfn>=2,<3` (2.2.1)** — 8.x는 기본 v3를 집어 PriorLabs 로그인을 요구한다(비상업 라이선스, 배제 확정). 로그인·계정 생성 금지 | 라이선스 결정 사항 |
| 7 | tabpfn 2.2.1과 sentence-transformers 6.x는 **같은 venv 공존 불가**(huggingface-hub 버전 충돌 실측) — 벤치는 venv 분리, 통합 설계는 3단계에서 해결 | 알려진 제약 |

## 1. 지금까지 확정된 것 (전부 develop에 커밋됨)

**직전 작업 — RAG 문서참조 수정 (완료, 5커밋 42e5b1c~968bade + 후속)**
복합 질의 가이드 0건 문제 해결: 코퍼스 개편(8문서·섹션 구조) → top-5 상대 게이트(마진 0.05·상한 0.45, 실측 확정) → 섹션 청킹(32청크) → multi-query RRF → 0건 완화 재시도(연비 사다리 정렬) → 옵션 동의어 9그룹(`_DOMAIN_RULES`) → 신뢰성 문서(08) 복귀. E2E 10질의 검증 완료.

**AI 고도화 과제 확정 스코프** (프리랜서 창업과정 과제 — as-is: LLM API 호출 → to-do: HF 모델 탐색·장착 + skills.sh 스킬 조합)
- **메인 2기능**: ① 매물 추천 고도화(툴콜링 에이전트 + RAG + HF 리랭커) ② **내부 시드 기반** 시세 진단(선언형 매칭 기준 + 완화 사다리 + SQL 통계 + TabPFN 적정가 + 산점도)
- **진입점 확정**: 상세 페이지 요약카드에 [AI 시세 진단] 아웃라인 버튼(문의하기 위) + AI 채팅 자연어("두 번째 셀토스 시세 봐줘"). **목록 카드는 변경 없음**(케밥·칩 안 넣기로 결정)
- **목업(사용자 확정)**: https://claude.ai/code/artifact/bf7e2af2-028e-4aa1-bc62-c12766040de9
- 엔카 크롤링 배제(robots.txt Disallow·약관·판례 검토 후 사용자 결정), 비전 허위매물 탐지 배제. 외부 데이터는 `source` 컬럼 구조만 열어둠 + 자동차365 공공 평균가 참고선(선택)
- BMAD 절차 안 씀. 산출물 문서는 `docs/ai-advanced/`

**1단계 완료 — 부품 실측** (상세: [01-model-skill-selection.md](01-model-skill-selection.md))
- 스킬 6종 프로젝트 설치(hf-cli·train-sentence-transformers·langchain-rag·langgraph-python-quickstart·supabase-postgres-best-practices·fastapi)
- 리랭커: **BAAI/bge-reranker-v2-m3 품질 확정**(코퍼스 실측 6/8 > 한국어 파인튠 5/8). 노트북 CPU 55초/10건 → **데스크톱 GPU 측정이 실행 방식 게이트**
- TabPFN: **v2 확정**(tabpfn==2.2.1, Apache + "Built with PriorLabs-TabPFN" 표기 의무). R² 0.92·MAE 111만원·피크 462MB
- 벤치 스크립트·노트북 결과: `api/scripts/bench/`

## 2. 다음 단계 (순서대로, **단계 사이에 멈추고 사용자 승인**)

| 단계 | 내용 | 핵심 결정사항 |
|---|---|---|
| **2. 시드** | 감가 규칙 생성기(`--preview`/`--apply` 분리) → 아반떼·쏘렌토·그랜저 각 40~60건 + **기존 시드 조정안**(규칙 대비 ±25% 이탈 목록) → **미리보기 보고·승인 후에만 DB 적재** → backfill(임베딩은 IS NULL만) | 가격=기준가−연식·주행 감가+옵션·무사고 웃돈±5% 노이즈, 난수 시드 고정, options는 DB 실존 문자열만, 기존 시드 스크립트(apply_listings_expansion.py) 관행 재사용. 검증: 가격~주행 상관 음수 |
| **3. 시세 엔진** | 선언형 기준 목록(필터: 모델 접두 정규화 "아반떼%"·연료·변속기·사고 / 밴드: 연식±2·주행±3만 / 가점: 옵션 교집합) + 완화 사다리 + SQL 통계(중앙값·사분위·백분위) + TabPFN 적정가 + 표본 수 항상 명시 | 수치는 전부 SQL/모델, LLM은 설명문만. fastapi·supabase 스킬 사용 |
| **4. 에이전트 전환** | LangGraph 4분기 → 툴콜링 루프. 도구: search_listings·search_guides(RAG+리랭커)·market_price_stats·compare_listings. 스텝 상한 필수 | DW-847(동적 되묻기)·DW-848(정렬 축)·DW-849(결과 되추림) 흡수 — 장부 참조. LangSmith 트레이스로 루프 관제 |
| **5. 진입점+차트** | 상세 [AI 시세 진단] 버튼 → AI 채팅 프리필 / 응답 스키마에 구조화 통계 추가(더하기만) → 웹 산점도 렌더(사분위 밴드·대상 마커·TabPFN 다이아몬드) | 비로그인은 "로그인하고 시세 진단"(FR58 정책). 목업이 화면 정답지 |

## 3. 리랭커 플랜 B (데스크톱 GPU 실패 시)
gte-multilingual-reranker-base(0.3B) · ONNX 양자화(통상 2~4배) · 재정렬 후보 10→5 축소 — 조합 가능. 어느 쪽이든 실측 후 결정.

## 4. 작업 규칙 (사용자 확정, 세션 간 유효)
- **분담**: 구현·테스트 수행·데이터 수집·단순/반복 = sonnet 서브에이전트(상위 모델이 diff·실측 검수 필수 — sonnet 초안이 DB에 없는 값을 쓴 실증 있음) / 사고·분석·판단·보고·**스킬 탐색** = 상위 모델 직접
- **단계 사이에는 멈춘다** — 다음 단계는 사용자가 시작하라고 할 때
- develop에서 작업·커밋(자동 push 허용), main 병합은 명시 승인. DB 적재·기존 데이터 수정은 미리보기 승인 후
- 열린 일은 전부 `_bmad-output/implementation-artifacts/deferred-work.md`(DW-843~849 참조)
- 선언 전 실측(측정 없이 결론 금지), 검사는 red 확인 후 green
