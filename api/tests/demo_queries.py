"""OI5 데모 질의셋 — 4.8 검증의 단일출처 미러(파이썬 데이터).

권위 출처는 `api/docs/ai-demo-queries.md`의 표 ①②③④다. 이 파일은 그 표를 코드가
순회·판정할 수 있게 파이썬 자료구조로 옮긴 것이며, **질의 문자열은 문서와 정확히 일치**해야
한다(drift 금지). 문서를 고치면 이 파일도 같이 고친다.

기대 경로 표기: ①②④는 문서의 "기대 분류"(A/B/C)를 그대로 옮긴다. ③ 회색지대만은 문서가
"B 우선이되 A로 가도 무방"으로 적은 합격 규칙을 코드 판정용 단일 라벨 "AB"로 합친다 —
문서 표 ③의 마무리 규칙("둘 중 어디로 가도 매물/추천을 주면 합격")과 동일한 의미다(라벨만 통합).

각 항목은 (query, expected_route) 쌍이다. expected_route 의미:
  · "A" = 구조형(경로 A, Text-to-SQL)
  · "B" = 질적·의미형(경로 B, 문서 RAG)
  · "C" = 매물 무관(경로 C, 정중한 거절)
  · "AB" = 회색지대(③) — A 또는 B 어디로 가도 매물/추천을 주면 합격(거절·빈손만 아니면 됨).
[Source: api/docs/ai-demo-queries.md ①②③④]
"""

# ── ① 구조형 → 경로 A (ai-demo-queries.md 표 ①) ──────────────────────
STRUCTURED_A = [
    "3천만원 이하 흰색 SUV",
    "2020년 이후 제네시스",
    "10만km 미만 디젤",
    "서울 경차 보여줘",
]

# ── ② 질적·의미형 → 경로 B (ai-demo-queries.md 표 ②) ────────────────
SEMANTIC_B = [
    "패밀리카로 무난한 거",
    "초보운전자에게 좋은 차",
    "연비 좋은 전기차 추천",
    "가성비 좋은 차 없을까?",
]

# ── ③ 회색지대(애매 — B 우선, A로 가도 무방) (ai-demo-queries.md 표 ③) ─
GRAY_AB = [
    "출퇴근용 적당한 차",
    "괜찮은 SUV 있어?",
    "너무 비싸지 않은 중형차",
]

# ── ④ 매물 무관 → 경로 C (가드 거절) (ai-demo-queries.md 표 ④) ───────
UNRELATED_C = [
    "오늘 날씨 어때?",
    "파이썬 코드 짜줘",
    "안녕",
    "1+1은 뭐야?",
]


# (query, expected_route) 평면 리스트 — 라우터/그래프 판정 순회용.
DEMO_QUERIES = (
    [(q, "A") for q in STRUCTURED_A]
    + [(q, "B") for q in SEMANTIC_B]
    + [(q, "AB") for q in GRAY_AB]
    + [(q, "C") for q in UNRELATED_C]
)
