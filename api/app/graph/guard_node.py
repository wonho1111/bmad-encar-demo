"""가드 노드 — 경로 C(매물 무관) 정중한 거절(FR16·FR47, CM1).

라우터가 "C"(중고차 매물 검색과 무관한 잡담·상식·다른 주제)로 분류한 질의를 받아,
순수 상식 Q&A를 제공하지 않고(FR16) 정중히 거절하면서 매물 검색으로 자연스럽게 유도한다.

설계: LLM을 호출하지 않고 고정 템플릿으로 답한다. 거절 문구는 질의 내용과 무관하게 동일하면
  되므로(상식 답을 주지 않는 게 목적) 결정론적·비용 0의 고정 문자열이 가장 단순·안전하다.
  → 비결정성·지연·비용을 만들지 않으면서 CM1(가드) 사상을 그대로 만족한다.

4.5는 이 함수를 그래프(graph.py)의 경로 C 노드로 쓴다. 시그니처는 다른 경로 노드와 통일
  (query 받아 {"answer", "listings"} 반환)해 answer_node가 동일하게 받아 계약을 보장한다.

13.5: 답변 문구를 EXPERIENCE.md Voice 표("AI 거절(FR47, 고정)")와 글자 그대로 일치시키고,
  `narrowed_by`(REJECT 전용 고정 상수, CR4 저장단위 정규화 술어 형식)를 함께 반환한다.
  `query`를 읽어 값을 바꾸지 않는다(무상태·결정론 — CLARIFY의 `_CLARIFY_CHIPS`와 동일 철학).
[Source: story 4.5 guard_node 설계; spec-13-5-부드러운-거절.md; FR16·FR47; conventions CM1]
"""

import logging

logger = logging.getLogger(__name__)

# 정중한 거절 + 매물 검색 유도 — 매물과 무관한 질의(C)에 항상 이 문구로 답한다(FR16/FR47/CM1).
# EXPERIENCE.md Voice 표("AI 거절(FR47, 고정)")와 글자 그대로 일치시킨 정본 문구다(13.5) —
# LLM 재작성 없음, 질의 내용과 무관하게 항상 동일(무상태·결정론).
# ⚠️ "매물을 찾아드릴게요" 부분 문자열을 반드시 포함해야 한다 — api/scripts/score_ab.py의
#   REDIRECT_MARKERS(is_redirect(), G1류 dead-end 게이트)가 이 문자열로 판정한다.
_GUARD_ANSWER = (
    "저는 중고차 찾기를 도와드리는 차장님이에요 🚗 "
    "그건 답하기 어렵지만, 원하는 차 조건을 말씀해 주시면 딱 맞는 매물을 찾아드릴게요."
)

# REJECT 전용 고정 상수 — CR4 저장단위 정규화 술어 형식(CLARIFY 3축과 동일 계열).
# query/context를 읽어 값을 바꾸지 않는다(무상태 — LLM 호출 없음, CR5와 동일 철학의 REJECT 버전).
_GUARD_NARROWED_BY = ("price<=30000000", "body_type=SUV", "fuel=전기")


def guard_node(query: str) -> dict:
    """매물 무관 질의(경로 C)에 정중한 거절 + 검색 유도 answer를 반환한다(FR16·FR47).

    listings는 항상 빈 목록([])이다. LLM/DB를 호출하지 않으므로 키·네트워크 없이도 동작한다.
    narrowed_by는 항상 동일한 고정 상수 3개다(무상태·결정론, 13.5).
    """
    logger.info("guard_node 질의=%r → 정중한 거절(경로 C)", query)
    return {"answer": _GUARD_ANSWER, "listings": [], "narrowed_by": list(_GUARD_NARROWED_BY)}
