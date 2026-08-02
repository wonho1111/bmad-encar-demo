"""OI5 데모 질의셋 — 4.8 검증의 단일출처 미러(파이썬 데이터).

권위 출처는 `api/docs/ai-demo-queries.md`의 표 ①②③④다. 이 파일은 그 표를 코드가
순회·판정할 수 있게 파이썬 자료구조로 옮긴 것이며, **질의 문자열은 문서와 정확히 일치**해야
한다(drift 금지). 문서를 고치면 이 파일도 같이 고친다.

기대 경로 표기(13.8 — 4분기 어휘로 정정, DW-609와 동일 이유: 구어휘 A/B/C는 라벨과 실제
동작이 어긋나는 문제를 반복 재생산했다): ①②④는 문서의 "기대 분류"(SQL/CLARIFY/REJECT)를
그대로 옮긴다. ③ 회색지대만은 문서가 "두 경로 중 하나로 가도 매물/되묻기/거절을 주면 합격"으로
적은 규칙을 코드 판정용 단일 라벨 "GRAY"로 합친다. 구어휘 변수명(`STRUCTURED_A`·`SEMANTIC_B`·
`GRAY_AB`·`UNRELATED_C`)은 아직 그대로인데, 이건 하위 호환이 아니라 **아직 안 고친 것**이다
(이 파일 밖 소비처는 `test_demo_acceptance.py` 하나뿐 — 열린 항목 DW-573).

각 항목은 (query, expected_route) 쌍이다. expected_route 의미:
  · "SQL" = 구조형(Text-to-SQL)
  · "CLARIFY" = 질적형(되묻기, 매물 아님)
  · "REJECT" = 매물 무관(정중한 거절)
  · "GRAY" = 회색지대(③) — 허용 경로가 **질의마다 다르다**. 어느 질의가 어느 경로를 허용하는지는
    아래 `GRAY_ALLOWED`가 갖는다(문서 표 ③의 "기대 분류" 칸과 1:1).
[Source: api/docs/ai-demo-queries.md ①②③④]
"""

# ── ① 구조형 → SQL (ai-demo-queries.md 표 ①) ─────────────────────────
STRUCTURED_A = [
    "3천만원 이하 흰색 SUV",
    "2020년 이후 제네시스",
    "10만km 미만 디젤",
    "서울 경차 보여줘",
]

# ── ② 질적형 → CLARIFY (ai-demo-queries.md 표 ②) ─────────────────────
SEMANTIC_B = [
    "패밀리카로 무난한 거",
    "초보운전자에게 좋은 차",
    "출퇴근용으로 편한 차 추천해줘",
    "가성비 좋은 차 없을까?",
]

# ── ③ 회색지대 — 허용 경로는 질의마다 다르다 (ai-demo-queries.md 표 ③) ─────
#
# ⚠️ 교차곱 금지(13.8 후속리뷰): 이전에는 세 질의 × 네 경로를 전부 합격으로 단언해서,
#    문서가 "오답"이라 못박은 조합(지식형 질의가 매물 목록을 주는 것, 가격·인승이 명시된
#    구조형 질의가 거절로 새는 것)까지 게이트가 초록이었다. 허용 경로는 질의별로 쓴다.
# 근거: 각 질의는 `api/docs/ai-ab-test-queryset.json`의 H6·H7·CL7과 같은 문자열이며,
#    아래 허용 집합은 그 항목의 `acceptable_paths`와 일치한다(실측 라우트: SQL·HYBRID·CLARIFY).
GRAY_ALLOWED = {
    "2500만원 이하 해치백 있어?": ("SQL", "HYBRID"),
    "6천만원 이하로 7명 이상 다 탈 수 있는 가족차 보여줘": ("SQL", "HYBRID"),
    "주행거리 많은 차 사도 괜찮을까?": ("CLARIFY", "REJECT"),
}

# 표 ③의 행 수를 여기서 못박는다(13.8 4차 리뷰). 이 dict에서 행이 사라지면 회색지대 게이트가
# 조용히 축소되는데(실측: 3행→1행이어도 `-k gray` 3 passed·전량 초록), test_demo_acceptance.py의
# 큐리셋 락스텝은 큐리셋을 **이 dict의 키로 걸러** 비교하므로 양쪽이 같이 줄어 못 잡았다.
# 검사를 데이터 옆에 두면 어느 소비처에서든 import 시점에 걸린다(CLAUDE.md B9).
# 행을 늘리거나 줄이려면 `ai-demo-queries.md` 표 ③·큐리셋·이 숫자를 함께 고쳐야 한다.
assert len(GRAY_ALLOWED) == 3 and all(GRAY_ALLOWED.values()), (
    "회색지대 표 ③은 3행이고 각 행에 허용 경로가 있어야 한다 — "
    "행·허용경로가 비면 게이트가 파라미터째 사라진다"
)

GRAY_AB = list(GRAY_ALLOWED)

# ── ④ 매물 무관 → REJECT (가드 거절) (ai-demo-queries.md 표 ④) ────────
UNRELATED_C = [
    "오늘 날씨 어때?",
    "파이썬 코드 짜줘",
    "안녕",
    "1+1은 뭐야?",
]


# (query, expected_route) 평면 리스트 — 라우터/그래프 판정 순회용.
DEMO_QUERIES = (
    [(q, "SQL") for q in STRUCTURED_A]
    + [(q, "CLARIFY") for q in SEMANTIC_B]
    + [(q, "GRAY") for q in GRAY_AB]
    + [(q, "REJECT") for q in UNRELATED_C]
)
