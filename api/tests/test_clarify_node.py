"""clarify_node 단위 테스트 — 고정 페이로드 형식(13.4, CR5 "추가 LLM 없음").

LLM/DB를 호출하지 않는 결정론 노드이므로 모킹 없이 직접 호출해 형식만 확인한다.
"""

from app.graph.clarify_node import _CLARIFY_QUESTION, clarify_node


def test_clarify_node_returns_expected_shape():
    out = clarify_node("패밀리카로 무난한 거")
    assert out.keys() == {"answer", "listings", "clarify"}
    assert isinstance(out["answer"], str) and out["answer"]
    assert out["listings"] == []
    assert out["clarify"].keys() == {"question", "chips"}


def test_clarify_node_answer_and_clarify_question_are_single_source():
    # answer와 clarify.question은 같은 고정 문자열이다(단일 출처, EXPERIENCE.md Voice 표 문구).
    out = clarify_node("아무 질의")
    assert out["answer"] == out["clarify"]["question"]


def test_clarify_node_chips_are_three_nonempty_strings():
    out = clarify_node("아무 질의")
    chips = out["clarify"]["chips"]
    assert isinstance(chips, list)
    assert len(chips) == 3
    assert all(isinstance(c, str) and c for c in chips)
    # 위 세 줄만으로는 가짜 게이트다 — `_CLARIFY_CHIPS`를 실수로 문자열 "abc"로 바꿔도
    # 노드가 `list(...)`로 감싸 `['a','b','c']`가 되므로 전부 통과한다(실측 확인). 그건 500이
    # 아니라 "한 글자짜리 칩 3개"가 사용자에게 그대로 나가는 조용한 실패다. 길이 하한으로 막는다.
    # 이 검사가 **안 보는 것**: 칩 문구 자체의 적절성(가격·차종·연료 세 축인지)은 의도적으로
    # 고정하지 않는다 — 제품 판단으로 바뀔 수 있는 값이라 테스트로 얼리지 않는다.
    assert all(len(c) >= 2 for c in chips)


def test_clarify_node_question_matches_ux_voice_wording():
    """되묻기 문구는 이 노드의 **유일한** 사용자 노출 출력이다(listings는 항상 []).

    형식만 보는 검사는 문구가 빈 문자열·엉뚱한 말로 바뀌어도 전부 초록이다. 형제 노드인
    guard_node가 문구의 핵심 단어("매물"·"예산")를 실제로 단언하는 선례를 그대로 따른다.
    문구 정본은 EXPERIENCE.md Voice 표 "AI 되묻기(FR46)"다.
    """
    out = clarify_node("아무 질의")
    assert "조건을 조금만 좁혀볼게요" in out["answer"]
    # 칩을 누르는 것과 직접 입력하는 것이 동등한 경로임을 문구가 알려줘야 한다(EXPERIENCE.md).
    assert "칩" in _CLARIFY_QUESTION and "직접 입력" in _CLARIFY_QUESTION
