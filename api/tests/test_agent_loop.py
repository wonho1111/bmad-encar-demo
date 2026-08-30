"""agent.py(run_search_agent) 툴콜링 루프 단위 테스트 — LLM·도구를 전부 가짜로 치환해
네트워크·DB 없이 오케스트레이션 로직만 검증한다(4단계 부품 B).

실제 실행(라이브 LLM+DB, 실측 3질의)은 4단계 부품 B 작업 보고에 JSON 전문으로 남긴다.
여기서는 결정론적인 배선만 격리해 확인한다:
  (1) 스텝 상한(_MAX_STEPS=6) — 가짜 LLM이 매 스텝 도구를 요청해도 정확히 6번만 호출되고
      그 이후는 강제로 structured-output 최종화로 넘어가는지(초과 호출 없음)
  (2) selected_listing_ids 검증 — 도구가 실제로 돌려준 id 밖의 값은 최종 listings에서 버려지는지
  (3) clarify 응답 구조 — clarify가 채워지면 listings는 항상 빈 목록인지
  (4) market_diagnosis 전달 — market_price_stats 도구의(마지막) artifact가 그대로 노출되는지
  (5) 결정론적 REJECT 사전 차단 — 금융·세금·보험 신호가 있으면 LLM을 아예 호출하지 않고
      guard_node로 직행하는지(router_node._FINANCE_SIGNALS 재사용, 비용 0 경로)
"""

from langchain_core.messages import ToolMessage

from app.graph import agent as agent_module
from app.schemas.ai import ClarifyPayload, ListingCard


class _FakeAIMessage:
    """LLM의 AIMessage 흉내 — tool_calls만 있으면 충분하다(agent.py는 이 속성만 읽는다)."""

    def __init__(self, tool_calls=None, content=""):
        self.tool_calls = tool_calls or []
        self.content = content


class _SequenceToolLLM:
    """bind_tools(...)가 돌려주는 가짜 — 미리 정한 AIMessage를 순서대로 돌려준다."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.invoke_count = 0

    def invoke(self, messages):
        msg = self._responses[min(self.invoke_count, len(self._responses) - 1)]
        self.invoke_count += 1
        return msg


class _InfiniteToolLLM:
    """매 호출마다 새 도구 호출을 요청하는 가짜 — 스텝 상한 없이는 무한히 도는 시나리오."""

    def __init__(self, tool_name="search_listings"):
        self._tool_name = tool_name
        self.invoke_count = 0

    def invoke(self, messages):
        self.invoke_count += 1
        call_id = f"call-{self.invoke_count}"
        return _FakeAIMessage(tool_calls=[{"name": self._tool_name, "args": {}, "id": call_id}])


class _FakeStructured:
    """with_structured_output(...)이 돌려주는 가짜 — invoke()가 정해진 최종 출력을 돌려준다."""

    def __init__(self, output):
        self._output = output

    def invoke(self, messages):
        return self._output


class _FakeTool:
    """TOOLS_BY_NAME[name]이 돌려주는 가짜 도구 — invoke(tool_call) -> ToolMessage."""

    def __init__(self, name, artifact=None, content="ok"):
        self.name = name
        self._artifact = artifact
        self._content = content

    def invoke(self, tool_call):
        return ToolMessage(content=self._content, tool_call_id=tool_call["id"], artifact=self._artifact)


def _patch_base_llm(monkeypatch, tool_llm, final_output):
    class _BaseLLM:
        def bind_tools(self, tools):
            return tool_llm

        def with_structured_output(self, schema):
            return _FakeStructured(final_output)

    monkeypatch.setattr(agent_module, "_llm", lambda: _BaseLLM())


# ───────── (1) 스텝 상한 ─────────

def test_step_cap_forces_final_response_after_six_steps(monkeypatch):
    tool_llm = _InfiniteToolLLM()
    final_output = agent_module._AgentFinalOutput(
        answer="스텝 상한까지의 결과로 답변합니다.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME", {"search_listings": _FakeTool("search_listings", artifact=[])}
    )

    result = agent_module.run_search_agent("가족용 SUV 추천해줘")

    # 리터럴 6으로 고정한다(agent_module._MAX_STEPS를 참조하면 상수를 깨도 이 단언이 같이
    # 깨져 자기일관 단언이 된다 — 상수 자체가 옳은 값인지를 검사하는 게 이 테스트의 목적).
    assert tool_llm.invoke_count == 6
    assert len(result["tools_used"]) == 6
    assert result["answer"] == "스텝 상한까지의 결과로 답변합니다."


def test_natural_stop_before_step_cap_does_not_over_call(monkeypatch):
    # 2스텝만에 도구 요청 없이 자연 종료하면 그 이후로는 tool_llm이 더 불리지 않는다.
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="찾았어요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME", {"search_listings": _FakeTool("search_listings", artifact=[])}
    )

    agent_module.run_search_agent("3천만원 이하 SUV")
    assert tool_llm.invoke_count == 2  # 6까지 안 가고 자연 종료 시점에서 멈춘다.


# ───────── (2) selected_listing_ids 검증 ─────────

def test_selected_listing_ids_drops_ids_outside_tool_results(monkeypatch):
    card1 = ListingCard(id="aaa", manufacturer="현대", model="싼타페", year=2020, price=1, mileage=1, region="서울")
    card2 = ListingCard(id="bbb", manufacturer="기아", model="쏘렌토", year=2021, price=2, mileage=2, region="부산")

    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="싼타페를 추천해요.",
        selected_listing_ids=["aaa", "no-such-id"],  # 뒤 id는 도구가 준 적 없는 값.
        clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[card1, card2])},
    )

    result = agent_module.run_search_agent("가족용 SUV 추천해줘")
    assert [c.id for c in result["listings"]] == ["aaa"]  # 벗어난 id는 버려진다.


# ───────── (3) clarify 응답 구조 ─────────

def test_clarify_response_has_no_listings(monkeypatch):
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])  # 도구 호출 없이 바로 되묻기.
    clarify_payload = ClarifyPayload(question="예산을 알려주시겠어요?", chips=["2천만원 이하", "3천만원 이하"])
    final_output = agent_module._AgentFinalOutput(
        answer="예산을 조금만 더 알려주시겠어요?", selected_listing_ids=[], clarify=clarify_payload,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})

    result = agent_module.run_search_agent("차 추천해줘")
    assert result["clarify"] == {"question": "예산을 알려주시겠어요?", "chips": ["2천만원 이하", "3천만원 이하"]}
    assert result["listings"] == []


# ───────── (4) market_diagnosis 전달 ─────────

def test_market_diagnosis_from_last_market_price_stats_call(monkeypatch):
    diagnosis = {"verdict": "적정", "percentile": 0.4}
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="시세를 알려드려요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"market_price_stats": _FakeTool("market_price_stats", artifact=diagnosis)},
    )

    result = agent_module.run_search_agent("그중 두 번째 매물 시세 알려줘")
    assert result["market_diagnosis"] == diagnosis


# ───────── (5) 결정론적 REJECT 사전 차단 ─────────

def test_deterministic_reject_skips_llm_entirely(monkeypatch):
    def _boom():
        raise AssertionError("금융/세금/보험 질의는 LLM을 호출하면 안 된다(결정론 사전 차단)")

    monkeypatch.setattr(agent_module, "_llm", _boom)
    result = agent_module.run_search_agent("자동차세 얼마 나와?")

    assert result["route"] == "AGENT"
    assert result["tools_used"] == []
    assert result["clarify"] is None
    assert result["market_diagnosis"] is None
    assert result["listings"] == []
    assert "차장님" in result["answer"]  # guard_node._GUARD_ANSWER 고정 문구 재사용 확인.


def test_car_related_query_does_not_trigger_deterministic_reject(monkeypatch):
    # 대조군 — 매물 관련 질의는 금융 신호가 없으므로 사전 차단 없이 정상적으로 LLM 루프를 탄다.
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})

    result = agent_module.run_search_agent("3천만원 이하 SUV 보여줘")
    assert tool_llm.invoke_count == 1  # LLM이 실제로 호출됐다(사전 차단되지 않음).
    assert result["answer"] == "ok"
