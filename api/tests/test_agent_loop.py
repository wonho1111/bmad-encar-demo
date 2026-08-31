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

from langchain_core.messages import SystemMessage, ToolMessage

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
    """agent_module.run_select를 몽키패치할 가짜 — 호출될 때마다 rows_by_call을 그대로 돌려준다."""

    def _fake(sql, params):
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
