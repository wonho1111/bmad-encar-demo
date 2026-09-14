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
  (6) 멀티턴 재검색 차단(DW-855) — answer_guards.block_research_on_followup이 True인 턴에서
      모델이 그래도 search_listings를 부르면, 실제 실행 없이 거절 ToolMessage만 받고 같은
      스텝 예산 안에서 compare_listings로 회복해 최종 응답이 나오는지
"""

from langchain_core.messages import SystemMessage, ToolMessage

from app.graph import agent as agent_module
from app.graph import agent_tools
from app.graph import answer_guards
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


def test_market_diagnosis_suppressed_when_multiple_listings_recommended(monkeypatch):
    """추천 흐름(카드 2장 이상)에서는 진단 차트를 노출하지 않는다 — 마지막 1건 차트만 덜렁
    붙는 혼란(사용자 실측 지적, 2026-08-31)의 결정론 억제 규칙."""
    diagnosis = {"verdict": "저렴", "percentile": 0.1}
    card1 = ListingCard(id="aaa", manufacturer="현대", model="그랜저 IG", year=2018, price=1, mileage=1, region="서울")
    card2 = ListingCard(id="bbb", manufacturer="현대", model="그랜저 IG", year=2019, price=2, mileage=2, region="전북")

    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "bbb"}, "id": "call-2"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="가격 대비 좋은 2건을 추천해요.", selected_listing_ids=["aaa", "bbb"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[card1, card2]),
         "market_price_stats": _FakeTool("market_price_stats", artifact=diagnosis)},
    )

    result = agent_module.run_search_agent("그랜저 IG 가성비 좋은 것 추천해줘")
    assert len(result["listings"]) == 2
    assert result["market_diagnosis"] is None  # 카드 2장 이상 → 차트 억제.


def test_market_diagnosis_kept_when_single_listing(monkeypatch):
    """카드 1장(시세 진단 흐름)에서는 진단이 그대로 노출된다 — 억제 규칙의 경계 확인."""
    diagnosis = {"verdict": "적정", "percentile": 0.5}
    card1 = ListingCard(id="aaa", manufacturer="현대", model="그랜저 IG", year=2019, price=1, mileage=1, region="전북")

    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-2"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="이 매물 시세입니다.", selected_listing_ids=["aaa"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[card1]),
         "market_price_stats": _FakeTool("market_price_stats", artifact=diagnosis)},
    )

    result = agent_module.run_search_agent("이 매물 시세 알려줘")
    assert len(result["listings"]) == 1
    assert result["market_diagnosis"] == diagnosis  # 카드 1장 → 진단 유지.


def test_clarify_dropped_when_listings_also_selected(monkeypatch):
    """매물과 clarify가 둘 다 채워진 모순 응답 — 검색 결과가 우선, clarify는 버린다
    (회귀 실측 S1, 2026-08-31: 카드 0장 + '찾았다' 서술 + 되묻기 조합 방지)."""
    card1 = ListingCard(id="aaa", manufacturer="기아", model="쏘렌토 MQ4", year=2021, price=1, mileage=1, region="서울")
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="쏘렌토 매물을 찾았어요.",
        selected_listing_ids=["aaa"],
        clarify=ClarifyPayload(question="예산은요?", chips=["2천만", "3천만"]),
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[card1])},
    )

    result = agent_module.run_search_agent("쏘렌토 있어?")
    assert [c.id for c in result["listings"]] == ["aaa"]  # 매물 유지
    assert result["clarify"] is None  # 모순된 clarify는 버려짐


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


# ───────── (6) listing_id 프롬프트 주입(5단계, "AI 시세 진단" 버튼) ─────────

def test_listing_id_is_injected_into_system_prompt(monkeypatch):
    """listing_id를 주면 시스템 프롬프트(첫 메시지)에 그 id가 포함되는지 확인한다.

    실제로 market_price_stats를 호출하는지까지는(그건 LLM의 판단이라 여기서 강제할 수 없다 —
    agent.py 모듈 docstring "도구 강제 호출은 하지 않음, 프롬프트 유도"). 이 테스트가 고정하는
    건 "프롬프트에 id가 실제로 실려 가는가"라는 배선 한 겹뿐이다.
    """
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="시세를 알려드려요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})

    agent_module.run_search_agent("이 매물 시세 알려줘", listing_id="abc-123")

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    assert len(system_messages) == 1
    assert "abc-123" in system_messages[0].content
    assert "market_price_stats" in system_messages[0].content


def test_no_listing_id_keeps_base_system_prompt(monkeypatch):
    # 대조군 — listing_id를 안 주면(기존 채팅 질의) 시스템 프롬프트가 그대로다(회귀 0).
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})

    agent_module.run_search_agent("3천만원 이하 SUV")

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    assert system_messages[0].content == agent_module._SYSTEM_PROMPT


# ───────── (7) 멀티턴 매물 참조 — 직전 대화 요약 블록(사용자 실측 결함 수정) ─────────
#
# 배경: 직전 턴에서 추천한 매물을 두고 "그중 두 번째 시세 알려줘"·"그 5개 비교해줘"라고 물으면
# 에이전트가 재검색만 반복했다(원인: context가 텍스트뿐이라 직전 매물 id가 다음 턴에 전달되지
# 않음). ConversationTurn.listing_ids(schemas/ai.py)로 id를 실어 보내고, agent.py가 그 id들로
# DB를 조회해(SELECT만) 시스템 프롬프트에 "[직전 대화에서 보여준 매물]" 블록을 붙인다.


def _fake_run_select_for(rows_by_call):
    """agent_module.run_select를 몽키패치할 가짜 — 호출될 때마다 rows_by_call을 그대로 돌려준다.

    SQL에 "color"가 있으면(agent._cards_for_ids가 agent_tools._SEARCH_SELECT_COLUMNS로 color
    까지 조회하는 지점, C50·C59 속성 좁힘용) 각 행 끝에 color 값(None)을 붙여 열 폭을 맞춘다 —
    호출부 대부분(12열 rows_by_call)은 색상을 직접 검증하지 않으므로 None으로 충분하다. 그 외
    호출(_recent_listings_prompt_block의 SELECT_COLUMNS, 12열)은 그대로 돌려준다."""

    def _fake(sql, params):
        if "color" in sql:
            return [(*row, None) for row in rows_by_call]
        return rows_by_call

    return _fake


def test_recent_listing_ids_become_system_prompt_summary_block(monkeypatch):
    """context의 가장 최근 어시스턴트 턴 listing_ids가 DB 조회를 거쳐 시스템 프롬프트
    요약 블록으로 들어가는지 확인한다(DB 조회는 run_select를 몽키패치해 네트워크 없이 검증)."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    # contextualize_query(맥락 재작성 LLM)는 이 테스트의 관심사가 아니다 — 실제 LLM 호출을
    # 막고 query를 그대로 통과시킨다(격리, 네트워크 없는 단위테스트 유지).
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    # SELECT_COLUMNS 순서(id, manufacturer, model, year, price, mileage, region, fuel,
    # accident_status, is_single_owner, is_non_smoker, options)와 동일한 폭의 가짜 행.
    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [
        {"role": "user", "content": "1000만원 이하 실속형 차 추천해줘"},
        {"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]},
    ]
    agent_module.run_search_agent("그중 두 번째 매물 시세 분석해줘", context=context)

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    prompt = system_messages[0].content
    assert "[직전 대화에서 보여준 매물]" in prompt
    assert "1. 현대 아반떼 AD 2017년식" in prompt
    assert "(id: aaa)" in prompt
    assert "2. 기아 쏘렌토 2020년식" in prompt
    assert "(id: bbb)" in prompt


def test_nonexistent_listing_id_is_silently_ignored(monkeypatch):
    """DB에 없는(팔렸거나 잘못된) id는 조용히 무시된다 — 나머지 id는 정상 포함되고 루프가
    죽지 않는다(강건성)."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    # WHERE id = ANY(...)라 DB가 애초에 존재하는 행만 돌려준다 — "ghost"는 결과에 없다.
    rows = [("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None)]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [
        {"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa", "ghost"]},
    ]
    result = agent_module.run_search_agent("아까 그 차 시세 알려줘", context=context)

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    prompt = system_messages[0].content
    assert "1. 현대 아반떼 AD 2017년식" in prompt
    assert "ghost" not in prompt
    assert result["answer"] == "ok"  # 루프가 죽지 않고 정상 완주.


def test_context_without_listing_ids_behaves_like_before(monkeypatch):
    """어시스턴트 턴에 listing_ids가 없으면(기존 클라이언트·되묻기 응답 등) 요약 블록 없이
    기존과 동일하게 동작한다(회귀 0) — DB 조회 자체가 일어나지 않는지도 확인한다.

    ⚠️ "[직전 대화에서 보여준 매물]"이라는 문구 자체는 정적 시스템 프롬프트([직전 목록 참조]
    절)에도 안내문으로 등장하므로(요약 블록이 실제로 있을 때만 참조하라는 지시), 단순
    substring 검사로는 늘 참(거짓 양성)이 된다 — 실제 블록은 "\\n\\n[직전 대화에서 보여준
    매물]\\n1."처럼 헤더 뒤에 번호 매긴 항목이 바로 붙는 형태이므로 그 결합 패턴으로 검사한다.
    """
    captured_messages: list = []
    select_calls: list = []

    def _track_run_select(sql, params):
        select_calls.append((sql, params))
        return []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "run_select", _track_run_select)
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    context = [
        {"role": "user", "content": "3천만원 이하 SUV"},
        {"role": "assistant", "content": "조건에 맞는 매물이 없어 다시 여쭤볼게요."},
    ]
    agent_module.run_search_agent("음... 그럼 세단은?", context=context)

    assert select_calls == []  # listing_ids가 없으므로 DB 조회 자체가 일어나지 않는다.
    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    assert "[직전 대화에서 보여준 매물]\n1." not in system_messages[0].content


def test_scans_past_listingless_assistant_turn_for_latest_shown_listings(monkeypatch):
    """직전 실측 회귀(그랜저 진단 여러 턴 → 쏘렌토 추천 → 시세 문의 → 주어 없는 후속 질의)
    변종 대응: 가장 최근 어시스턴트 턴에 listing_ids가 없어도(예: 순수 안내 응답), 그 이전
    턴들 중 listing_ids를 가진 **가장 최근** 것까지 계속 찾는다 — "실없는 응대" 한 턴 때문에
    직전에 실제로 보여준 매물 목록이 통째로 사라지면 안 된다."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    rows = [("bbb", "기아", "쏘렌토 하이브리드", 2021, 32000000, 78000, "부산", None, None, None, None, None)]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [
        {"role": "user", "content": "쏘렌토 하이브리드 추천해줘"},
        {"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["bbb"]},
        {"role": "user", "content": "78000km짜리 시세 분석"},
        # 이 턴엔 listing_ids가 없다(순수 안내 응답) — 그래도 위 "bbb" 턴이 여전히 유효해야 한다.
        {"role": "assistant", "content": "잠시만요, 확인해볼게요."},
    ]
    agent_module.run_search_agent("아니 시세분석해달라고", context=context)

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    prompt = system_messages[0].content
    assert "[직전 대화에서 보여준 매물]" in prompt
    assert "(id: bbb)" in prompt
    # 주어 없는 후속 질의를 오래된 주제로 건너뛰지 말라는 지침이 프롬프트에 실제로 있어야 한다.
    assert "오래된 주제로 건너뛰지 마라" in prompt


def test_recent_listing_ids_merge_across_multiple_assistant_turns(monkeypatch):
    """P1 실측 결함(2026-08-31) 수정 확인: "레이는?" 같은 후속 질의가 **두 턴 전** 매물도
    참조할 수 있어야 한다 — 예전엔 "가장 최근 listing_ids 보유 턴 1개"만 썼지만, 이제는
    listing_ids를 실은 어시스턴트 턴을 최신부터 전부 병합한다(중복 제거, 상한 20). 아래
    context는 두 어시스턴트 턴 모두 listing_ids를 갖고 있다 — 병합 후 최근 턴("ccc","ddd")이
    먼저, 이전 턴("aaa","bbb")이 이어서 나와야 한다."""
    captured_messages: list = []
    captured_select_params: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
        ("ccc", "기아", "레이", 2021, 9000000, 30000, "인천", None, None, None, None, None),
        ("ddd", "현대", "아반떼 CN7", 2022, 15000000, 20000, "대전", None, None, None, None, None),
    ]

    def _fake_run_select(sql, params):
        captured_select_params.append(params)
        return rows

    monkeypatch.setattr(agent_module, "run_select", _fake_run_select)

    context = [
        {"role": "user", "content": "1000만원 이하 실속형 차 추천해줘"},
        {"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]},
        {"role": "user", "content": "그중 첫 번째 매물 시세 분석해줘"},
        {"role": "assistant", "content": "적정가로 보여요.", "listing_ids": ["ccc", "ddd"]},
    ]
    agent_module.run_search_agent("레이는?", context=context)

    # DB 조회에 넘긴 id 목록 자체가 병합·순서(최신 턴 먼저)를 지켜야 한다.
    assert captured_select_params[0][0] == ["ccc", "ddd", "aaa", "bbb"]

    system_messages = [m for m in captured_messages if isinstance(m, SystemMessage)]
    prompt = system_messages[0].content
    assert "[직전 대화에서 보여준 매물]" in prompt
    # 병합 후 재부여된 순번(최신 턴이 1·2번, 이전 턴이 3·4번)과 두 턴 전 매물(aaa)이 모두 있어야 한다.
    assert "1. 기아 레이 2021년식" in prompt and "(id: ccc)" in prompt
    assert "3. 현대 아반떼 AD 2017년식" in prompt and "(id: aaa)" in prompt
    assert "4. 기아 쏘렌토 2020년식" in prompt and "(id: bbb)" in prompt


def test_recent_listings_block_names_ids_as_the_only_valid_reference_set(monkeypatch):
    """DW-872 update(2026-09-09 18:08) (c) 실측(C51) — 도구 결과가 5장짜리 카드보다 많을 때
    카드 밖 매물까지 "이 중"에 포함시켰다. [직전 대화에서 보여준 매물] 블록 끝에 실제 id
    목록과 "이 id들만 뜻한다"는 문장이 코드로 박혀 들어가는지 확인한다(프롬프트 말로만
    설명하던 규칙을 값 자체로 다시 못박는 부분)."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda query, context=None: query)

    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    agent_module.run_search_agent("이 중에 저렴한 거", context=context)

    prompt = [m for m in captured_messages if isinstance(m, SystemMessage)][0].content
    assert "직전에 사용자에게 보여준 매물 id" in prompt
    assert "[aaa, bbb]" in prompt  # 병합된 순서 그대로 값 자체가 문장에 실린다.
    assert "이 중/그중" in prompt
    assert "보여주지 않은 매물은 제외" in prompt


# ───────── 다건 시세 진단(market_diagnoses, 2026-08-31) ─────────

class _SequentialFakeTool:
    """호출될 때마다 미리 정한 artifact를 순서대로 돌려주는 가짜 도구(다건 market_price_stats)."""

    def __init__(self, name, artifacts):
        self.name = name
        self._artifacts = list(artifacts)
        self.call_count = 0

    def invoke(self, tool_call):
        artifact = self._artifacts[min(self.call_count, len(self._artifacts) - 1)]
        self.call_count += 1
        return ToolMessage(content="ok", tool_call_id=tool_call["id"], artifact=artifact)


def test_market_diagnoses_populated_when_two_or_more_calls(monkeypatch):
    """market_price_stats가 이번 대화에서 2건 이상 결과를 내면 market_diagnoses(복수)에
    전부 담긴다 — 다건 진단 요약표(웹 C1)가 쓸 재료."""
    diag_a = {"listing": {"id": "aaa"}, "verdict": "적정"}
    diag_b = {"listing": {"id": "bbb"}, "verdict": "저렴"}

    responses = [
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "bbb"}, "id": "call-2"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="두 매물 시세를 알려드려요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"market_price_stats": _SequentialFakeTool("market_price_stats", [diag_a, diag_b])},
    )

    result = agent_module.run_search_agent("이 두 매물 시세 각각 알려줘")

    assert result["market_diagnoses"] == [diag_a, diag_b]
    assert result["market_diagnosis"] == diag_b  # 기존 단건 필드는 마지막 호출 그대로 유지.


# ───────── 프롬프트 규칙 문자열 계약 고정(2026-08-31, 실측 결함 F1·F2·리텍스트 수정) ─────────
#
# LLM 프롬프트 자체는 실행해 검증할 수 없다(비결정적) — 여기서는 "그 규칙 문장이 실제로
# 프롬프트에 실려 있는가"라는 배선 한 겹만 가볍게 고정한다(리팩터 중 문구가 통째로 지워지는
# 사고를 막는 안전망). 문구가 바뀌어도 뜻이 같으면 이 테스트도 같이 고쳐 쓰면 된다 — "절대
# 안 바뀌어야 할 계약"이 아니라 "실수로 안 사라지게 하는 안전망"이다.


def test_system_prompt_covers_remainder_reference_rule():
    # F1: "나머지 두 개랑 비교해줘"처럼 직전 목록에서 이미 다룬 매물을 뺀 나머지를 가리키는
    # 표현도 재검색 없이 그 블록의 id를 쓰라는 규칙이 프롬프트에 있어야 한다.
    assert "나머지" in agent_module._SYSTEM_PROMPT
    assert "이미 다룬" in agent_module._SYSTEM_PROMPT


def test_system_prompt_covers_per_listing_verdict_rule():
    # F2: 여러 매물의 시세 판정을 서술하려면 매물마다 market_price_stats를 각각 호출해야
    # 한다는 규칙(호출 안 한 매물의 판정을 지어내지 말라)이 프롬프트에 있어야 한다.
    assert "각 매물에 대해 이 도구를 각각 호출" in agent_module._SYSTEM_PROMPT


def test_system_prompt_covers_attribute_consistency_rule():
    # 매물 속성(연료·연식 등) 서술이 도구가 돌려준 실제 값과 어긋나면 안 된다는 규칙.
    assert "실제 값과" in agent_module._SYSTEM_PROMPT


def test_system_prompt_covers_market_price_stats_for_followup_price_questions():
    # DW-872 update(2026-09-09 18:08) (d) 실측(C53) — 재검색이 막히자 "목록에 없다"고
    # 답했다. 시세·적정가 후속 질문은 compare_listings가 아니라 market_price_stats로
    # 가라는 규칙이 프롬프트에도 있어야 한다(answer_guards.FOLLOWUP_REFUSAL_TEXT와 같은 안내).
    assert "compare_listings가 아니라" in agent_module._SYSTEM_PROMPT
    assert "market_price_stats를 호출해라" in agent_module._SYSTEM_PROMPT


def test_market_diagnoses_none_when_only_one_call(monkeypatch):
    """market_price_stats 호출이 1건뿐이면 market_diagnoses는 None(기존 단건 market_diagnosis만
    쓰인다) — additive 필드가 불필요하게 채워지지 않는지 확인."""
    diagnosis = {"listing": {"id": "aaa"}, "verdict": "적정"}
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

    result = agent_module.run_search_agent("이 매물 시세 알려줘")

    assert result["market_diagnoses"] is None
    assert result["market_diagnosis"] == diagnosis


def test_original_query_block_added_only_when_rewritten(monkeypatch):
    """재작성이 일어난 턴은 시스템 프롬프트에 [사용자 원문]이 병기된다 — 재작성기가 구워 넣은
    직전 매물 연식이 필터로 승격되는 실측 결함(2026-09-01) 방지 배선."""
    captured = {}

    class _CaptureLLM:
        def invoke(self, messages):
            captured["system"] = messages[0].content
            return _FakeAIMessage(tool_calls=[])

    def _base(monkeypatch_target):
        final = agent_module._AgentFinalOutput(answer="안내.", selected_listing_ids=[], clarify=None)
        _patch_base_llm(monkeypatch, _CaptureLLM(), final)

    _base(monkeypatch)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: "재작성된 질의")
    monkeypatch.setattr(agent_module, "_recent_listings_prompt_block", lambda c: None)

    agent_module.run_search_agent("원문 질의", context=[{"role": "user", "content": "이전 턴"}])
    assert "[사용자 원문]" in captured["system"] and "원문 질의" in captured["system"]

    # 재작성이 일어나지 않으면(동일 반환) 원문 블록도 없다 — 단일턴 회귀 0 보장.
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    agent_module.run_search_agent("원문 질의")
    assert "[사용자 원문]" not in captured["system"]


# ───────── (6) 멀티턴 재검색 차단(DW-855, answer_guards.block_research_on_followup 배선) ─────────

class _BoomTool:
    """거절돼야 할 도구 — 실제로 invoke되면 테스트를 실패시킨다(재검색 차단이 안 먹혔다는 증거)."""

    def invoke(self, tool_call):
        raise AssertionError("search_listings가 거절되지 않고 실제로 실행됐다 — 재검색 차단 실패")


def test_followup_reference_blocks_search_listings_and_recovers_via_compare(monkeypatch):
    """DW-855 회귀(MT5) 재현 — "나머지" 지칭 + 직전 목록 id가 있는 턴에서 모델이 그래도
    search_listings를 부르면, 그 호출은 실행되지 않고 거절 ToolMessage(재검색 금지)만
    돌아온다. 같은 스텝 예산 안에서 모델이 compare_listings로 회복하면 재검색 없이 최종
    응답이 나와야 한다(2026-08-31 실측 회귀의 최소 재현, 이번엔 코드 가드가 직접 막는다)."""
    card_a = ListingCard(id="aaa", manufacturer="기아", model="쏘렌토", year=2021, price=1, mileage=1, region="서울")

    captured_tool_message_contents: list[str] = []

    class _RetryToolLLM:
        """1스텝엔 (잘못된) search_listings 재검색을, 거절을 받은 2스텝엔 compare_listings를
        요청하는 가짜 — 모델이 거절 ToolMessage를 보고 스스로 회복하는 것까지 흉내낸다."""

        def __init__(self):
            self.invoke_count = 0

        def invoke(self, messages):
            self.invoke_count += 1
            if self.invoke_count == 1:
                return _FakeAIMessage(tool_calls=[
                    {"name": "search_listings", "args": {"model_keyword": "쏘렌토"}, "id": "call-1"}
                ])
            if self.invoke_count == 2:
                captured_tool_message_contents.append(messages[-1].content)  # 직전 거절 ToolMessage
                return _FakeAIMessage(tool_calls=[
                    {"name": "compare_listings", "args": {"listing_ids": ["aaa"]}, "id": "call-2"}
                ])
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _RetryToolLLM()
    final_output = agent_module._AgentFinalOutput(
        answer="나머지 매물과 비교했어요.", selected_listing_ids=["aaa"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _BoomTool(), "compare_listings": _FakeTool("compare_listings", artifact=[card_a])},
    )
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(
        [("aaa", "기아", "쏘렌토", 2021, 28000000, 50000, "서울", None, None, None, None, None)]
    ))

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("나머지 매물이랑 비교해줘", context=context)

    assert result["tools_used"] == ["search_listings", "compare_listings"]
    assert captured_tool_message_contents == [answer_guards.FOLLOWUP_REFUSAL_TEXT]
    assert [c.id for c in result["listings"]] == ["aaa"]
    assert result["answer"] == "나머지 매물과 비교했어요."


def test_no_followup_reference_allows_search_listings_normally(monkeypatch):
    """대조군 — 지칭 표현이 없는 새 조건 검색은(직전 목록 id가 있어도) 평소대로 실행된다."""
    card_a = ListingCard(id="bbb", manufacturer="현대", model="싼타페", year=2022, price=1, mileage=1, region="서울")
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="싼타페를 찾았어요.", selected_listing_ids=["bbb"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[card_a])},
    )
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(
        [("aaa", "기아", "쏘렌토", 2021, 28000000, 50000, "서울", None, None, None, None, None)]
    ))

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("이번엔 싼타페로 다시 찾아줘", context=context)

    assert result["tools_used"] == ["search_listings"]
    assert [c.id for c in result["listings"]] == ["bbb"]


def test_followup_guard_uses_raw_query_not_contextualized_rewrite(monkeypatch):
    """2026-09-09 챗봇 검증(20260909) C50 실측 재현 — contextualize_query가 지칭 표현을 지우고
    독립 질의로 재작성해 버리면, 재작성 후 문자열로 재검색 차단을 판정할 경우 지칭 표현이
    이미 사라져 가드가 못 잡는다(실제로 이 재작성이 관찰됐고, 그 결과 재검색이 새 매물을
    끌어와 직전 목록을 무시했다). 재작성 전 원문 query로 판정해야 한다.

    ⚠️ 2026-09-14 개정: 원래 재현 질의("그 중에 무사고인 것만 골라줘")는 이제 answer_guards.
    narrow_by_attribute 템플릿 경로(LLM 미호출)로 먼저 처리된다(그 경로도 원문 query 기준이라
    이 테스트가 원래 확인하려던 "재작성 무시" 자체는 여전히 성립하지만, 그 경로를 검증하는
    테스트는 별도(test_c50/test_c59/§B 신규 테스트)에 있다). 이 테스트는 속성 좁힘 어휘·조건
    전환 제외어(말고/다른/빼고/제외, C48)가 없는 순수 지칭("그 중에 있는 매물 다시 보여줘")
    으로 바꿔, 기존 재검색 차단 가드가 여전히 원문 기준으로 동작하는지만 확인한다."""
    captured_tool_message_contents: list[str] = []

    class _CaptureThenStopLLM:
        def __init__(self):
            self.invoke_count = 0

        def invoke(self, messages):
            self.invoke_count += 1
            if self.invoke_count == 1:
                return _FakeAIMessage(tool_calls=[
                    {"name": "search_listings", "args": {}, "id": "call-1"}
                ])
            captured_tool_message_contents.append(messages[-1].content)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CaptureThenStopLLM()
    final_output = agent_module._AgentFinalOutput(answer="다른 매물도 안내드려요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": _BoomTool()})
    # 재작성기가 지칭 표현 없는 완전히 새 문장으로 바꿔치기한 상황을 흉내낸다(실측 재현).
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: "경차 2천만원 이하")
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(
        [("aaa", "기아", "모닝", 2019, 7900000, 62000, "서울", None, None, None, None, None)]
    ))

    context = [{"role": "assistant", "content": "6건을 찾았어요.", "listing_ids": ["aaa"]}]
    agent_module.run_search_agent("그 중에 있는 매물 다시 보여줘", context=context)

    assert captured_tool_message_contents == [answer_guards.FOLLOWUP_REFUSAL_TEXT]


# ───────── (8) 검색 인자 자동 주입(DW-872 update 2026-09-09 18:08 (f)) ─────────

def test_search_listings_args_auto_filled_from_query_and_result_text_prefixed(monkeypatch):
    """실측(C02·C03) — 'SUV'가 질문에 있어도 도구 인자 없이 query_text에만 실렸다. 모델이
    body_type을 비워 뒀으면 코드가 원문 질의에서 채워 **그 인자로 실제 도구를 실행**하고
    (모델이 이미 준 query_text는 그대로 두고), 도구 결과 텍스트 맨 앞에 "(질문에서 자동
    적용" 접두를 붙여 모델에게 알리는지 확인한다."""
    captured_tool_message_contents: list[str] = []
    received_tool_calls: list[dict] = []

    class _CapturingSearchTool:
        def invoke(self, tool_call):
            received_tool_calls.append(tool_call)
            return ToolMessage(content="1. id=aaa 현대 투싼 SUV", tool_call_id=tool_call["id"], artifact=[])

    class _CaptureThenStopLLM:
        def __init__(self):
            self.invoke_count = 0

        def invoke(self, messages):
            self.invoke_count += 1
            if self.invoke_count == 1:
                return _FakeAIMessage(tool_calls=[
                    {"name": "search_listings", "args": {"query_text": "SUV 추천"}, "id": "call-1"}
                ])
            captured_tool_message_contents.append(messages[-1].content)
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CaptureThenStopLLM()
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": _CapturingSearchTool()})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    agent_module.run_search_agent("SUV 있어?")

    # 모델이 비운 body_type이 원문 질의("SUV 있어?")에서 채워져 실제 실행 인자에 반영된다.
    assert received_tool_calls[0]["args"]["body_type"] == "SUV"
    # 모델이 이미 준 query_text는 덮지 않는다.
    assert received_tool_calls[0]["args"]["query_text"] == "SUV 추천"
    assert captured_tool_message_contents[0].startswith("(질문에서 자동 적용")


def test_search_listings_args_unchanged_when_model_already_filled_them(monkeypatch):
    """모델이 이미 body_type을 채웠으면(예: "세단") 원문에 다른 차종 표현이 있어도 절대
    덮지 않는다 — 자동 주입은 "비어 있을 때만" 채운다."""
    received_tool_calls: list[dict] = []

    class _CapturingSearchTool:
        def invoke(self, tool_call):
            received_tool_calls.append(tool_call)
            return ToolMessage(content="ok", tool_call_id=tool_call["id"], artifact=[])

    tool_llm = _SequenceToolLLM([
        _FakeAIMessage(tool_calls=[
            {"name": "search_listings", "args": {"body_type": "세단"}, "id": "call-1"}
        ]),
        _FakeAIMessage(tool_calls=[]),
    ])
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": _CapturingSearchTool()})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    agent_module.run_search_agent("SUV 아니면 세단 3천만원대")

    assert received_tool_calls[0]["args"]["body_type"] == "세단"


# ───────── (7) 결정론 후처리 배선(DW-869·870) — 답변 id 제거 + 표본 부족 주의 보정 ─────────

def test_final_answer_strips_listing_ids_and_adds_sample_caveat(monkeypatch):
    """최종화 LLM이 답변에 UUID를 그대로 쓰고 표본 부족 주의도 빼먹었다면(가짜 최종 출력으로
    이 상황을 직접 만든다), 반환 전에 코드가 id를 지우고 주의 문구를 붙인다."""
    listing_uuid = "aaaaaaaa-1111-4aaa-8aaa-aaaaaaaaaaaa"
    diagnosis = {
        "listing": {"id": listing_uuid}, "verdict": "적정",
        "criteria": {"sample_count": 2},
    }
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "market_price_stats", "args": {"listing_id": listing_uuid}, "id": "call-1"}
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer=f"이 매물은 적정가입니다 (id: {listing_uuid}).", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"market_price_stats": _FakeTool("market_price_stats", artifact=diagnosis)},
    )

    result = agent_module.run_search_agent("이 매물 시세 알려줘")

    assert listing_uuid not in result["answer"]
    assert "표본이 적어 참고만 하세요" in result["answer"]


# ───────── (9) DW-873 — 첫 응답이 도구 호출 없을 때 search_guides 강제 호출 ─────────
#
# 배경: 가이드(구매 지식) 질문 15건 중 13건에서 에이전트가 도구를 한 번도 안 부르고 모델
# 자체 지식으로만 답했다(4회 실측 모두 search_guides 호출 2건뿐). 키워드로 "가이드 질문인지"
# 미리 판별하지 않고, "첫 LLM 응답이 도구 호출 없이 바로 최종 답을 낸다"는 행동 자체를
# 트리거로 삼아 search_guides를 강제로 한 번 실행해본다.


class _BoomGuideTool:
    """search_guides가 호출되면 안 되는 시나리오에서, 실제로 invoke되면 테스트를 실패시킨다."""

    def invoke(self, tool_call):
        raise AssertionError("이미 도구를 부른 턴인데 search_guides가 그래도 강제 호출됐다")


def test_no_tool_call_first_response_forces_search_guides(monkeypatch):
    """(a) 첫 응답이 도구 호출 없이 바로 답을 내면 search_guides가 강제로 호출되고, 가이드가
    1건 이상이면 그 결과를 대화에 얹어 tool_llm을 한 번 더 불러 최종 답을 만든다."""
    responses = [
        _FakeAIMessage(tool_calls=[]),  # 1스텝 — 도구 없이 바로 답하려던 첫 응답.
        _FakeAIMessage(tool_calls=[]),  # 2스텝 — 가이드 보강 후 자연 종료.
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="가이드 내용을 참고해 안내드려요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_guides": _FakeTool("search_guides", content="[침수차 감별 가이드]\n실내 냄새·안전벨트 이물질 확인…")},
    )

    result = agent_module.run_search_agent("침수차량인지 아닌지 구별하는 팁 있을까요")

    assert tool_llm.invoke_count == 2  # 가이드 보강 후 tool_llm을 한 번 더 호출했다.
    assert result["tools_used"] == ["search_guides"]
    assert result["answer"] == "가이드 내용을 참고해 안내드려요."


def test_no_tool_call_first_response_with_zero_guides_returns_out_of_scope_answer(monkeypatch):
    """(b, DW-876) search_guides를 강제로 호출했지만 관련 가이드가 0건(상대 게이트 탈락)이면,
    모델이 자체 지식으로 낸 첫 응답을 버리고 guard_node와 동일한 고정 거절+유도 문구로
    답한다(근거 없이 "안내했다"고 답하는 정직성 결함 방지, C63·C67 실측). structured-output
    최종화(_finalize)까지 가지 않고 여기서 바로 반환하므로 tool_llm은 1회만 호출된다."""
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])  # 응답 1개뿐 — 더 불리면 IndexError.
    final_output = agent_module._AgentFinalOutput(
        answer="원래 답변을 그대로 드립니다.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_guides": _FakeTool("search_guides", content=agent_module.NO_GUIDES_FOUND_TEXT)},
    )

    result = agent_module.run_search_agent("오늘 날씨 어때요")

    assert tool_llm.invoke_count == 1  # 가이드 0건이라 tool_llm을 다시 부르지 않았다.
    assert result["tools_used"] == ["search_guides"]  # 호출 자체는 시도했다(다른 도구와 동일 관례).
    # guard_node의 고정 거절 문구로 교체됐다(모델의 원래 답변이 아니다).
    assert result["answer"] == agent_module.guard_node("오늘 날씨 어때요")["answer"]
    assert result["answer"] != "원래 답변을 그대로 드립니다."
    assert result["listings"] == []
    assert result["clarify"] is None


def test_tool_call_already_made_this_turn_skips_forced_search_guides(monkeypatch):
    """(c) 같은 턴에서 이미 도구를 한 번이라도 불렀다면(1스텝에 search_listings 호출), 그 뒤
    자연 종료(2스텝, 도구 없음)에는 강제 search_guides를 적용하지 않는다."""
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="검색 결과로 답변드려요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"search_listings": _FakeTool("search_listings", artifact=[]), "search_guides": _BoomGuideTool()},
    )

    result = agent_module.run_search_agent("3천만원 이하 SUV 보여줘")

    assert tool_llm.invoke_count == 2  # 기존 배선 그대로(가이드 강제 호출로 늘어나지 않음).
    assert result["tools_used"] == ["search_listings"]  # search_guides는 tools_used에 없다.
    assert result["answer"] == "검색 결과로 답변드려요."


def test_forced_search_guides_gate_rejects_off_topic_guide(monkeypatch):
    """(e, DW-876) 강제 호출 블록이 실제 search_guides 도구(스텁 아님)를 부르는 상황에서,
    어휘 근거 게이트가 주제 밖 가이드(질의 "명의이전" vs 가이드 "전기차 보조금")를 걸러
    NO_GUIDES_FOUND_TEXT로 되돌리면, (b)와 동일하게 guard_node 거절 문구로 답한다."""
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])  # 응답 1개뿐 — 더 불리면 IndexError.
    final_output = agent_module._AgentFinalOutput(
        answer="원래 답변을 그대로 드립니다.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    # 실제 search_guides 도구를 그대로 쓴다(스텁이 아니라 게이트 로직까지 함께 탄다) —
    # DB·임베딩 호출부만 가짜로 치환한다.
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(
        agent_tools, "find_relevant_guides_fused",
        lambda q, qvec: [("전기차 보조금 가이드", "국고보조금과 지자체보조금을 확인하세요.")],
    )
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_guides": agent_tools.search_guides})

    result = agent_module.run_search_agent("명의이전 절차가 복잡한가요?")

    assert tool_llm.invoke_count == 1  # 게이트가 0건 취급해 tool_llm을 다시 부르지 않았다.
    assert result["tools_used"] == ["search_guides"]
    assert result["answer"] == agent_module.guard_node("명의이전 절차가 복잡한가요?")["answer"]
    assert result["answer"] != "원래 답변을 그대로 드립니다."


def test_no_tool_call_first_response_with_conditions_forces_search_listings(monkeypatch):
    """(d, DW-876 (c)) 첫 응답이 도구 호출 없이 바로 답을 냈는데 질의에 매물 조건 어휘(예:
    "세단" — answer_guards.infer_missing_args가 인식하는 닫힌 어휘)가 있으면 search_guides가
    아니라 search_listings를 강제한다 — C71류("적당한 주행거리…세단 보여주세요")가 가이드
    게이트로 새던 결함(DW-876) 방지."""
    responses = [
        _FakeAIMessage(tool_calls=[]),  # 1스텝 — 도구 없이 바로 답하려던 첫 응답.
        _FakeAIMessage(tool_calls=[]),  # 2스텝 — 강제 검색 결과를 보고 자연 종료.
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="조건에 맞는 세단을 안내드려요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)

    class _BoomGuideTool2:
        def invoke(self, tool_call):
            raise AssertionError("조건이 있는 질문인데 search_guides가 강제 호출됐다")

    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {
            "search_listings": _FakeTool("search_listings", artifact=[]),
            "search_guides": _BoomGuideTool2(),
        },
    )

    result = agent_module.run_search_agent("적당한 주행거리가 어느 정도예요? 그 안에서 세단 보여주세요")

    assert tool_llm.invoke_count == 2  # 강제 검색 후 한 번 더 불려 최종 답을 만들었다.
    assert result["tools_used"] == ["search_listings"]  # search_guides는 아예 호출되지 않았다.
    assert result["answer"] == "조건에 맞는 세단을 안내드려요."


# ───────── (10) 직전 목록 지칭 결정론 해석 배선(DW-855 3차 재검증) ─────────


class _CapturingFakeTool:
    """invoke가 실제로 받은 tool_call args를 기록하는 가짜 도구(DW-855 인자 교체 검증용)."""

    def __init__(self, name, artifact=None, content="ok"):
        self.name = name
        self._artifact = artifact
        self._content = content
        self.received_args = []

    def invoke(self, tool_call):
        self.received_args.append(tool_call.get("args"))
        return ToolMessage(content=self._content, tool_call_id=tool_call["id"], artifact=self._artifact)


def test_ordinal_reference_replaces_empty_market_price_stats_listing_id(monkeypatch):
    """"그중 두 번째" 같은 순번 지칭을 코드가 직전 목록 카드에서 직접 풀어
    (answer_guards.resolve_list_reference), 모델이 listing_id를 비워 부른 market_price_stats
    호출에 그 id를 채워 넣는지 확인한다(인자 교체 — DW-855 3차 재검증 후속)."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def __init__(self):
            self.invoke_count = 0

        def invoke(self, messages):
            captured_messages.extend(messages)
            self.invoke_count += 1
            if self.invoke_count == 1:
                return _FakeAIMessage(
                    tool_calls=[{"name": "market_price_stats", "args": {"listing_id": ""}, "id": "call-1"}]
                )
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="적정가로 보여요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    market_tool = _CapturingFakeTool(
        "market_price_stats", artifact={"listing": {"id": "bbb"}, "verdict": "적정"}
    )
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"market_price_stats": market_tool})

    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    result = agent_module.run_search_agent("그중 두 번째 매물 시세 분석해줘", context=context)

    assert market_tool.received_args == [{"listing_id": "bbb"}]  # 순번 2 → bbb로 교체됐다.
    assert result["answer"] == "적정가로 보여요."


# ───────── (10b) 챗봇 답변 검증 2026-09-14(C59·C60) — 해석 id 항상 교체 + 중복 호출 병합 ─────────

def test_resolved_reference_always_overrides_model_chosen_id_within_recent_list(monkeypatch):
    """C60 — 모델이 "더 저렴한 쪽"을 직전 목록 안의 다른(더 비싼) id로 잘못 채워도, 해석된
    id(최저가)로 무조건 교체된다(예전엔 "직전 목록 안"이면 손대지 않아 이 결함이 그대로
    통과했다)."""
    captured_messages: list = []

    class _CapturingToolLLM:
        def __init__(self):
            self.invoke_count = 0

        def invoke(self, messages):
            captured_messages.extend(messages)
            self.invoke_count += 1
            if self.invoke_count == 1:
                # 모델이 직전 목록 "안"의 더 비싼 매물(bbb)을 잘못 골랐다.
                return _FakeAIMessage(
                    tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "bbb"}, "id": "call-1"}]
                )
            return _FakeAIMessage(tool_calls=[])

    tool_llm = _CapturingToolLLM()
    final_output = agent_module._AgentFinalOutput(answer="더 저렴한 쪽 시세예요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    market_tool = _CapturingFakeTool("market_price_stats", artifact={"listing": {"id": "aaa"}, "verdict": "저렴"})
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"market_price_stats": market_tool})

    # aaa(9,260,000원)가 bbb(25,000,000원)보다 저렴하다 — "더 저렴한 쪽"의 정답은 aaa.
    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    result = agent_module.run_search_agent("그중에 더 저렴한 쪽 시세 확인해줘", context=context)

    assert market_tool.received_args == [{"listing_id": "aaa"}]  # bbb가 아니라 해석된 aaa로 교체됐다.
    assert result["answer"] == "더 저렴한 쪽 시세예요."


def test_duplicate_market_price_stats_calls_in_same_step_are_merged(monkeypatch):
    """C60 — 모델이 같은 스텝에 market_price_stats를 서로 다른 id로 2번 부르면(둘 다 해석
    id로 덮이므로 사실상 중복 호출), 실제로는 1번만 실행된다 — 중복 실행되면 market_diagnoses
    에 같은 진단이 2건 쌓여 "다건 진단"으로 잘못 노출되는 부작용이 생긴다."""
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "market_price_stats", "args": {"listing_id": "bbb"}, "id": "call-1"},
            {"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-2"},
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="더 저렴한 쪽 시세예요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    market_tool = _CapturingFakeTool("market_price_stats", artifact={"listing": {"id": "aaa"}, "verdict": "저렴"})
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"market_price_stats": market_tool})

    rows = [
        ("aaa", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    result = agent_module.run_search_agent("그중에 더 저렴한 쪽 시세 확인해줘", context=context)

    assert market_tool.received_args == [{"listing_id": "aaa"}]  # 2번이 아니라 1번만 실행됐다.
    assert result["market_diagnoses"] is None  # 중복이 안 쌓였으니 "다건 진단"으로 잘못 노출되지 않는다.
    assert result["tools_used"].count("market_price_stats") == 1


def test_duplicate_calls_not_merged_when_no_resolved_reference(monkeypatch):
    """대조군 — 해석된 지칭 id가 없는 턴(순번·극값·비교 지칭이 없음)에서는 같은 도구를
    여러 번 불러도(예: 서로 다른 매물 2건을 각각 진단) 병합하지 않고 그대로 둘 다 실행된다."""
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-1"},
            {"name": "market_price_stats", "args": {"listing_id": "bbb"}, "id": "call-2"},
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="두 매물 시세예요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    market_tool = _CapturingFakeTool("market_price_stats", artifact={"listing": {"id": "aaa"}, "verdict": "저렴"})
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"market_price_stats": market_tool})

    result = agent_module.run_search_agent("아반떼랑 쏘렌토 시세 각각 알려줘")

    assert market_tool.received_args == [{"listing_id": "aaa"}, {"listing_id": "bbb"}]  # 둘 다 실행됨.
    assert result["tools_used"].count("market_price_stats") == 2


# ───────── (10c) 챗봇 답변 검증 2026-09-14(C54) — _apply_reference_resolution의 compare_listings
# 다건 처리 ─────────
#
# 배경: "1번이랑 3번 비교해줘"에서 resolve_list_reference가 예전엔 순번 하나만 풀어(1번만)
# always-override가 compare_listings 인자를 [1번]으로 깎았고, 같은 호출이 3회 반복됐다(C54).
# 순번 다건 해석(위 (5b))이 된 지금도, 해석 결과가 우연히 1건뿐일 때 모델이 이미 채운 다건
# 인자를 존중해야 정보 손실이 없다 — 아래는 _apply_reference_resolution 자체를 직접 검증한다.

def test_apply_reference_resolution_compare_listings_overrides_when_two_or_more_resolved():
    args, changed = agent_module._apply_reference_resolution(
        "compare_listings", {"listing_ids": ["wrong"]}, ["id1", "id3"]
    )
    assert changed is True
    assert args["listing_ids"] == ["id1", "id3"]


def test_apply_reference_resolution_compare_listings_keeps_model_args_when_single_resolved():
    # 해석 결과가 1건뿐이고 모델이 이미 다건 인자를 채웠으면 손대지 않는다.
    args, changed = agent_module._apply_reference_resolution(
        "compare_listings", {"listing_ids": ["id1", "id2"]}, ["id1"]
    )
    assert changed is False
    assert args["listing_ids"] == ["id1", "id2"]


def test_apply_reference_resolution_compare_listings_fills_empty_args_when_single_resolved():
    # 해석 결과가 1건뿐이라도 모델이 인자를 아예 비웠으면 그 1건으로 채운다.
    args, changed = agent_module._apply_reference_resolution("compare_listings", {}, ["id1"])
    assert changed is True
    assert args["listing_ids"] == ["id1"]


def test_apply_reference_resolution_market_price_stats_still_always_overrides():
    # market_price_stats는 종전대로 해석 id 1건으로 무조건 교체한다(회귀 0).
    args, changed = agent_module._apply_reference_resolution(
        "market_price_stats", {"listing_id": "wrong"}, ["id1", "id3"]
    )
    assert changed is True
    assert args["listing_id"] == "id1"


def test_c54_multiple_ordinal_compare_listings_deduped_to_single_correct_call(monkeypatch):
    """C54 — "1번이랑 3번 비교해줘"에서 모델이 같은 스텝에 compare_listings를 (잘못된 단건
    인자로) 3번 불러도, 해석된 [id1, id3]로 전부 교체된 뒤 인자가 완전히 같아진 호출끼리
    합쳐져 실제로는 1번만 실행된다."""
    compare_tool = _CapturingFakeTool("compare_listings", artifact=[])
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "compare_listings", "args": {"listing_ids": ["id1"]}, "id": "call-1"},
            {"name": "compare_listings", "args": {"listing_ids": ["id1"]}, "id": "call-2"},
            {"name": "compare_listings", "args": {"listing_ids": ["id1"]}, "id": "call-3"},
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="1번과 3번을 비교했어요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"compare_listings": compare_tool})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    rows = [
        ("id1", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("id2", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
        ("id3", "기아", "K5", 2019, 15000000, 80000, "인천", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "3건을 찾았어요.", "listing_ids": ["id1", "id2", "id3"]}]
    result = agent_module.run_search_agent("1번이랑 3번 비교해줘", context=context)

    assert compare_tool.received_args == [{"listing_ids": ["id1", "id3"]}]  # 딱 1번만 실행됐다.
    assert result["tools_used"].count("compare_listings") == 1


def test_dedup_keeps_both_calls_when_post_replacement_args_differ(monkeypatch):
    """C54(항목 3c) — 도구 이름만 보고 합치면(예전 방식) 안 된다는 걸 잠근다. 해석된 지칭
    id가 1건뿐이면 compare_listings 인자는 모델 것이 그대로 유지되므로(위 (10c)), 같은
    스텝에서 모델이 서로 다른(둘 다 정당한) 조합으로 compare_listings를 두 번 부르면 교체
    후에도 인자가 다르다 — 이때는 병합하지 않고 둘 다 실행돼야 한다."""
    compare_tool = _CapturingFakeTool("compare_listings", artifact=[])
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "compare_listings", "args": {"listing_ids": ["id1", "id2"]}, "id": "call-1"},
            {"name": "compare_listings", "args": {"listing_ids": ["id1", "id3"]}, "id": "call-2"},
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(answer="두 조합 다 비교했어요.", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"compare_listings": compare_tool})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    rows = [
        ("id1", "현대", "아반떼 AD", 2017, 9260000, 106062, "서울", None, None, None, None, None),
        ("id2", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", None, None, None, None, None),
        ("id3", "기아", "K5", 2019, 15000000, 80000, "인천", None, None, None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    # "1번" 지칭 하나뿐이라 해석 결과가 1건(id1)이다 — compare_listings 인자는 모델 것을 그대로
    # 둔다(위 (10c)), 즉 두 호출의 교체 후 인자가 서로 다르게 유지된다.
    context = [{"role": "assistant", "content": "3건을 찾았어요.", "listing_ids": ["id1", "id2", "id3"]}]
    result = agent_module.run_search_agent("1번 매물 두 조합으로 비교해줘", context=context)

    assert compare_tool.received_args == [{"listing_ids": ["id1", "id2"]}, {"listing_ids": ["id1", "id3"]}]
    assert result["tools_used"].count("compare_listings") == 2


# ───────── (11) C36·C71 — search_listings 미호출 사후 강제(post-loop, has_listing_intent) ─────────
#
# 배경: aeba16a 100건 평가에서 남은 5건 중 2건. C36("여자친구랑 드라이브 다니기 좋은 차")는
# search_guides만 불렸고 0건이라 조기 "범위 밖" 거절로 샜다(추천 질문인데). C71("적당한
# 주행거리가 어느 정도예요? 그 안에서 세단 보여주세요")은 모델이 search_guides를 스스로
# 불러 기존 "첫 응답에 도구 호출 없음" 트리거를 아예 안 탔다. 트리거를 "search_listings
# 미호출" 자체로 바꿔 루프 종료 후 한 번 더 확인한다(answer_guards.has_listing_intent).

def test_c36_guide_zero_hit_with_recommend_words_does_not_reject_and_forces_search(monkeypatch):
    """C36 — 조건 어휘는 없지만 "좋은 차"(추천 문구)가 있으면, search_guides가 0건이어도
    guard_node 거절로 바꾸지 않고 루프 종료 후 search_listings를 강제 실행해 답한다."""
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])  # 응답 1개뿐 — 더 불리면 IndexError.
    final_output = agent_module._AgentFinalOutput(
        answer="드라이브에 어울리는 차를 안내드려요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {
            "search_guides": _FakeTool("search_guides", content=agent_module.NO_GUIDES_FOUND_TEXT),
            "search_listings": _FakeTool("search_listings", artifact=[]),
        },
    )

    result = agent_module.run_search_agent("여자친구랑 드라이브 다니기 좋은 차")

    assert tool_llm.invoke_count == 1  # 가이드 0건 이후 tool_llm을 다시 부르지 않았다(finalize만).
    assert result["tools_used"] == ["search_guides", "search_listings"]
    assert result["answer"] == "드라이브에 어울리는 차를 안내드려요."
    # guard_node의 고정 거절 문구가 아니다 — "범위 밖"으로 잘리지 않았다.
    assert result["answer"] != agent_module.guard_node("여자친구랑 드라이브 다니기 좋은 차")["answer"]


def test_c71_model_calls_search_guides_itself_still_forces_search_listings(monkeypatch):
    """C71 — 모델이 (강제 블록을 거치지 않고) search_guides를 스스로 호출해 자연 종료해도,
    질의에 조건 어휘("세단")가 있으므로 루프 종료 후 search_listings가 강제 실행된다."""
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "search_guides", "args": {"query_text": "주행거리 세단"}, "id": "call-1"}
        ]),
        _FakeAIMessage(tool_calls=[]),  # 가이드 결과를 보고도 검색 없이 자연 종료.
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="조건에 맞는 세단을 안내드려요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {
            "search_guides": _FakeTool("search_guides", content="[주행거리 가이드]\n연식 대비 기준…"),
            "search_listings": _FakeTool("search_listings", artifact=[]),
        },
    )

    result = agent_module.run_search_agent("적당한 주행거리가 어느 정도예요? 그 안에서 세단 보여주세요")

    assert tool_llm.invoke_count == 2  # 강제 블록(step==0)은 안 탔다 — 모델이 직접 불렀으므로.
    assert result["tools_used"] == ["search_guides", "search_listings"]
    assert result["answer"] == "조건에 맞는 세단을 안내드려요."


# ───────── (12) C48 — 조건 전환 후속질의("그거 말고 하이브리드만") ─────────

def test_c48_exclusion_word_switches_condition_instead_of_blocking(monkeypatch):
    """C48 — 직전 목록 지칭 재검색 차단 대상 턴이라도 제외어("말고")가 있으면 거절하지 않고,
    첫 턴 원문 + 이번 턴 원문을 합쳐 infer_missing_args로 인자를 채운 뒤 그대로 실행한다."""
    captured_tool = _CapturingFakeTool("search_listings", artifact=[])
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "search_listings", "args": {"fuel": "하이브리드"}, "id": "call-1"}
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="하이브리드만 골랐어요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": captured_tool})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for([]))

    context = [
        {"role": "user", "content": "4천만원 이하 세단 좀 보여줘"},
        {"role": "assistant", "content": "3건을 찾았어요.", "listing_ids": ["aaa"]},
    ]
    result = agent_module.run_search_agent("그거 말고 하이브리드만", context=context)

    # 거절 ToolMessage가 아니라 실제로 실행됐고, 첫 턴의 세단·예산 조건이 합쳐져 채워졌다.
    assert captured_tool.received_args == [
        {"fuel": "하이브리드", "body_type": "세단", "price_max": 40_000_000}
    ]
    assert result["answer"] == "하이브리드만 골랐어요."


def test_c48_exclusion_word_skips_narrow_template_even_when_cards_present(monkeypatch):
    """챗봇 답변 검증 2026-09-14(C48 부작용) — 직전 목록에 실제 카드가 있어(narrow_by_attribute가
    빈 리스트를 돌려줄 수 있는 상황) "그거 말고 하이브리드만"을 받아도, 제외어가 있으면
    속성 좁힘 템플릿(narrow_by_attribute)이 발동하지 않고 _followup_switch의 재검색 경로로
    간다 — 전에는 템플릿이 먼저 잡아 "직전 목록에 하이브리드 없음"으로 끝났다(C48)."""
    captured_tool = _CapturingFakeTool("search_listings", artifact=[])
    responses = [
        _FakeAIMessage(tool_calls=[
            {"name": "search_listings", "args": {"fuel": "하이브리드"}, "id": "call-1"}
        ]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="하이브리드만 골랐어요.", selected_listing_ids=[], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": captured_tool})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    # 직전 목록에 가솔린 매물만 있다 — narrow_by_attribute를 그대로 태우면 하이브리드
    # 매치가 0건이라 "없습니다" 템플릿으로 빠진다.
    rows = [("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None)]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [
        {"role": "user", "content": "4천만원 이하 세단 좀 보여줘"},
        {"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]},
    ]
    result = agent_module.run_search_agent("그거 말고 하이브리드만", context=context)

    assert "narrow_by_attribute" not in result["tools_used"]
    assert result["tools_used"] == ["search_listings"]
    assert result["answer"] == "하이브리드만 골랐어요."


def test_narrow_template_fires_without_exclusion_word(monkeypatch):
    """대조군 — 같은 카드 구성이라도 제외어 없이 "그 중에 하이브리드만"이면 기존대로 속성
    좁힘 템플릿이 발동한다(LLM 미호출, 코드가 "없습니다" 답변을 직접 조립)."""
    _patch_boom_base_llm(monkeypatch)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    rows = [("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None)]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("그 중에 하이브리드만", context=context)

    assert result["tools_used"] == ["narrow_by_attribute"]
    assert result["listings"] == []
    assert result["answer"] == "직전 목록에는 하이브리드인 매물이 없습니다. 조건을 넓혀 다시 찾아드릴까요?"


# ───────── (13) C50·C59 — 직전 목록 속성 좁힘 ─────────

def test_c50_narrows_final_listings_to_accident_free_subset(monkeypatch):
    """C50 — "그 중에 무사고인 것만 골라줘"는 모델의 selected_listing_ids와 무관하게 코드가
    계산한 무사고 부분집합으로 최종 listings를 확정한다(모델이 반대로 답하는 결함 방지)."""
    tool_llm = _SequenceToolLLM([_FakeAIMessage(tool_calls=[])])
    final_output = agent_module._AgentFinalOutput(
        answer="무사고 매물만 안내드려요.", selected_listing_ids=["aaa", "bbb"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    rows = [
        ("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", "가솔린", "단순교환", None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    result = agent_module.run_search_agent("그 중에 무사고인 것만 골라줘", context=context)

    assert [c.id for c in result["listings"]] == ["aaa"]  # 무사고 1건만 남는다.


def test_c59_color_narrow_with_no_match_forces_empty_listings(monkeypatch):
    """C59 — "여기서 흰색만 있어?"인데 흰색이 하나도 없으면, 모델이 compare_listings로 이미
    seen_listings에 "aaa"를 채워놓고 그걸 selected_listing_ids로 골랐어도 최종 listings는
    빈 목록으로 확정된다("조건에 맞는 매물 없음") — 코드가 계산한 색상 집합이 우선한다."""
    card_a = ListingCard(id="aaa", manufacturer="현대", model="아반떼", year=2017, price=1, mileage=1, region="서울")
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "compare_listings", "args": {"listing_ids": ["aaa"]}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="흰색 매물은 없어요.", selected_listing_ids=["aaa"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"compare_listings": _FakeTool("compare_listings", artifact=[card_a])},
    )
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    base_row = ("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None)

    def _fake_run_select(sql, params):
        if "color" in sql:
            return [(*base_row, "검정")]
        return [base_row]

    monkeypatch.setattr(agent_module, "run_select", _fake_run_select)

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("여기서 흰색만 있어?", context=context)

    assert result["listings"] == []


# ───────── (14) 챗봇 답변 검증 2026-09-14(B, C50·C59) — 속성 좁힘 템플릿(LLM 미호출) ─────────

class _BoomToolLLM:
    """LLM이 실제로 호출되면 테스트를 실패시키는 가짜 — 템플릿 경로는 LLM을 아예 안 부른다."""

    def invoke(self, messages):
        raise AssertionError("속성 좁힘 템플릿 경로인데 tool_llm이 호출됐다 — LLM 루프를 안 타야 한다")


def _patch_boom_base_llm(monkeypatch):
    class _BoomBaseLLM:
        def bind_tools(self, tools):
            return _BoomToolLLM()

        def with_structured_output(self, schema):
            raise AssertionError("속성 좁힘 템플릿 경로인데 with_structured_output이 호출됐다")

    monkeypatch.setattr(agent_module, "_llm", lambda: _BoomBaseLLM())


def test_narrow_by_attribute_template_skips_llm_entirely(monkeypatch):
    """C50 — 좁힘 조건만 있는 순수 후속 질의는 LLM을 한 번도 안 부르고(tool_llm.invoke,
    structured_output.invoke 둘 다) 코드가 답변 본문까지 조립한다."""
    _patch_boom_base_llm(monkeypatch)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    rows = [
        ("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None),
        ("bbb", "기아", "쏘렌토", 2020, 25000000, 50000, "부산", "가솔린", "단순교환", None, None, None),
    ]
    monkeypatch.setattr(agent_module, "run_select", _fake_run_select_for(rows))

    context = [{"role": "assistant", "content": "2건을 찾았어요.", "listing_ids": ["aaa", "bbb"]}]
    result = agent_module.run_search_agent("그 중에 무사고인 것만 골라줘", context=context)

    assert result["tools_used"] == ["narrow_by_attribute"]
    assert [c.id for c in result["listings"]] == ["aaa"]
    assert result["answer"].startswith("직전 목록 중 무사고인 매물은 1건입니다.")
    assert result["clarify"] is None
    assert result["market_diagnosis"] is None
    assert result["market_diagnoses"] is None


def test_narrow_by_attribute_template_empty_match_still_skips_llm(monkeypatch):
    """C59 — 조건에 맞는 매물이 0건이어도 템플릿이 "없습니다" 문구로 답하고 LLM은 안 부른다."""
    _patch_boom_base_llm(monkeypatch)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    base_row = ("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None)

    def _fake_run_select(sql, params):
        if "color" in sql:
            return [(*base_row, "검정")]
        return [base_row]

    monkeypatch.setattr(agent_module, "run_select", _fake_run_select)

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("여기서 흰색만 있어?", context=context)

    assert result["tools_used"] == ["narrow_by_attribute"]
    assert result["listings"] == []
    assert result["answer"] == "직전 목록에는 흰색인 매물이 없습니다. 조건을 넓혀 다시 찾아드릴까요?"


def test_narrow_by_attribute_mixed_intent_keeps_existing_llm_path(monkeypatch):
    """단, 좁힘 조건 외 요구(시세 등)가 섞이면("그중 흰색 시세 봐줘") 템플릿 대신 기존 경로
    (LLM 루프 + 해석 id를 도구 인자로)를 그대로 쓴다 — 템플릿은 시세 질문에 답할 수 없다."""
    card_a = ListingCard(id="aaa", manufacturer="현대", model="아반떼", year=2017, price=1, mileage=1, region="서울")
    diagnosis = {"listing": {"id": "aaa"}, "verdict": "적정"}
    responses = [
        _FakeAIMessage(tool_calls=[{"name": "market_price_stats", "args": {"listing_id": "aaa"}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ]
    tool_llm = _SequenceToolLLM(responses)
    final_output = agent_module._AgentFinalOutput(
        answer="흰색 매물 시세를 알려드려요.", selected_listing_ids=["aaa"], clarify=None,
    )
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(
        agent_module, "TOOLS_BY_NAME",
        {"market_price_stats": _FakeTool("market_price_stats", artifact=diagnosis)},
    )
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)
    base_row = ("aaa", "현대", "아반떼", 2017, 9260000, 106062, "서울", "가솔린", "무사고", None, None, None)

    def _fake_run_select(sql, params):
        if "color" in sql:
            return [(*base_row, "흰색")]
        return [base_row]

    monkeypatch.setattr(agent_module, "run_select", _fake_run_select)

    context = [{"role": "assistant", "content": "1건을 찾았어요.", "listing_ids": ["aaa"]}]
    result = agent_module.run_search_agent("그중 흰색 시세 봐줘", context=context)

    # 템플릿(narrow_by_attribute만)이 아니라 실제 LLM 루프를 탔다 — market_price_stats가 불렸다.
    assert result["tools_used"] == ["market_price_stats"]
    assert result["answer"] == "흰색 매물 시세를 알려드려요."
    assert result["market_diagnosis"] == diagnosis


# ───────── (16) 챗봇 답변 검증 2026-09-14(E, C68) — accident_free_only 자동 주입 배선 ─────────

def test_search_listings_args_auto_filled_with_accident_free_only(monkeypatch):
    """C68 — "사고 이력 없는 차"가 질문에 있으면 search_listings 실행 인자에
    accident_free_only=True가 자동으로 채워진다(모델이 비워 뒀을 때만)."""
    received_tool_calls: list[dict] = []

    class _CapturingSearchTool:
        def invoke(self, tool_call):
            received_tool_calls.append(tool_call)
            return ToolMessage(content="ok", tool_call_id=tool_call["id"], artifact=[])

    tool_llm = _SequenceToolLLM([
        _FakeAIMessage(tool_calls=[{"name": "search_listings", "args": {}, "id": "call-1"}]),
        _FakeAIMessage(tool_calls=[]),
    ])
    final_output = agent_module._AgentFinalOutput(answer="ok", selected_listing_ids=[], clarify=None)
    _patch_base_llm(monkeypatch, tool_llm, final_output)
    monkeypatch.setattr(agent_module, "TOOLS_BY_NAME", {"search_listings": _CapturingSearchTool()})
    monkeypatch.setattr(agent_module, "contextualize_query", lambda q, c=None: q)

    agent_module.run_search_agent("사고 이력 없는 차 찾아줘")

    assert received_tool_calls[0]["args"]["accident_free_only"] is True
