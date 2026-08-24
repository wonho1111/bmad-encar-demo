"""경로 CLARIFY — 고정 템플릿 되묻기 노드(FR46, CR5).

`guard_node`(REJECT 고정 템플릿)와 동일한 결정론 패턴: LLM/DB를 일절 호출하지 않고
고정 문자열 질문 1개 + 고정 칩 배열만 반환한다(추가 LLM 호출 없음 — CR5).

되묻기 상한(2~3턴) 초과 시의 강제 폴백은 이 노드가 아니라 `graph.py`의 `_clarify_step`이
`doc_rag_node`를 직접 호출해 처리한다(DW-563) — 이 노드는 "아직 상한 이내"일 때만 불린다.

질문 문구는 EXPERIENCE.md Voice 표 "AI 되묻기(FR46)" 항목과 동일한 단일 출처 문자열이다.
[Source: spec-13-4-조건-좁혀-되묻기-clarify.md Tasks; EXPERIENCE.md Voice 표]
"""

# EXPERIENCE.md Voice 표 "AI 되묻기(FR46)"와 동일 문구(단일 출처) — answer_node를 거쳐도
# 새로 짓지 않고 이 문자열이 그대로 answer/clarify.question 양쪽에 쓰인다.
_CLARIFY_QUESTION = "조건을 조금만 좁혀볼게요 — 칩을 눌러도 되고, 직접 입력해도 돼요."

# 가격·차종·연료 세 축의 대표값 — 탭 시 다음 질의로 이어붙을 후보(칩=타이핑과 동등 경로).
_CLARIFY_CHIPS = ["3천만원 이하", "SUV", "전기차"]


def clarify_node(query: str) -> dict:
    """CLARIFY 경로 — 고정 되묻기 질문+칩을 반환한다(LLM/DB 호출 없음, CR5).

    query는 받기만 하고 쓰지 않는다(결정론 템플릿이라 질의 내용과 무관 — guard_node와 동일 패턴).
    """
    return {
        "answer": _CLARIFY_QUESTION,
        "listings": [],
        "clarify": {"question": _CLARIFY_QUESTION, "chips": list(_CLARIFY_CHIPS)},
    }
