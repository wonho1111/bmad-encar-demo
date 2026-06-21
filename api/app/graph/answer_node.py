"""답변 조립 노드 — 공통 계약 보장 + FR17 0건 안내(FR17).

경로 노드(A: sql_rag_node / B: doc_rag_node / C: guard_node)가 만든 결과를 받아
최종 `{answer, listings[]}` 계약으로 정규화한다. 그래프의 마지막 노드다.

설계(함정 #3 — 과잉구현 금지): 여기서 LLM으로 답변을 다시 쓰지 않는다.
  경로 A·B 노드는 이미 충분한 한국어 answer를 만들고, guard는 거절 문구를 만든다.
  answer_node의 역할은 "새 답 생성"이 아니라 다음 둘에 한정한다:
    1) 계약 일관성 보장 — answer는 str, listings는 list로 항상 채워서 내보낸다.
    2) FR17 0건 fallback 통일 — 어떤 경로든 listings가 비었는데 answer까지 비어 있으면,
       빈손으로 돌려보내지 않고 조건 완화/재질문을 유도하는 공통 안내를 주입한다.
  (경로 노드가 자기 0건 문구를 이미 채웠다면 그 문구를 존중하고 fallback을 덮어쓰지 않는다.)

[Source: story 4.5 answer_node 설계; FR17; 함정 #3(LLM 재작성 금지)]
"""

import logging

logger = logging.getLogger(__name__)

# FR17 — 어느 경로든 결과가 0건이고 노드가 안내 문구조차 못 채운 경우의 공통 fallback.
# "조용한 빈 결과"를 막아 사용자가 다음 행동(조건 완화·재질문)을 하도록 유도한다.
_EMPTY_FALLBACK = (
    "조건에 맞는 매물을 찾지 못했어요. "
    "가격대나 차종 조건을 넓히거나 원하시는 용도를 알려주시면 다시 찾아드릴게요."
)


def answer_node(result: dict) -> dict:
    """경로 노드 결과(dict)를 받아 공통 계약 {answer, listings[]}로 정규화한다(FR17).

    - listings: 누락/None이면 빈 목록으로 보정(계약상 항상 list).
    - answer: 누락/공백이고 listings도 0건이면 FR17 공통 fallback 주입.
    - LLM 재호출 없음(함정 #3) — 노드가 만든 answer를 그대로 살린다.
    """
    listings = result.get("listings") or []
    answer = (result.get("answer") or "").strip()

    if not answer:
        # 노드가 answer를 비워 보냈을 때만 보정한다.
        if listings:
            # 매물은 있는데 문구가 없다 — 최소한의 건수 안내라도 채운다(빈 답 금지).
            answer = f"조건에 맞는 매물 {len(listings)}건을 찾았어요."
        else:
            answer = _EMPTY_FALLBACK  # FR17 — 0건 + 빈 문구 → 조건 완화/재질문 유도.
        logger.info("answer_node 빈 answer 보정 → %r (listings=%d)", answer, len(listings))

    return {"answer": answer, "listings": listings}
