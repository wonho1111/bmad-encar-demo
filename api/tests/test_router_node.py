"""router_node 단위 테스트 — LLM 모킹으로 분류·보정·fail-loud를 네트워크 없이 검증(FR13).

실제 분류 품질(라이브 LLM)은 dev-story 라이브 검증에서 OI5 질의셋으로 눈 확인한다.
여기서는 결정론적인 부분만 격리: 구조화 출력 통과 / 환각 라벨 보정 / 신호 기반 fallback / 키 부재 fail-loud.
"""

import pytest

from app.graph import router_node as rn
from app.schemas.ai import RouterDecision


class _FakeStructured:
    """with_structured_output(...)이 돌려주는 객체 흉내 — invoke()가 정해진 값을 반환/예외."""

    def __init__(self, decision=None, raise_exc=None):
        self._decision = decision
        self._raise = raise_exc

    def invoke(self, messages):
        if self._raise is not None:
            raise self._raise
        return self._decision


class _FakeLLM:
    def __init__(self, structured):
        self._structured = structured

    def with_structured_output(self, schema):
        return self._structured


def _patch_llm(monkeypatch, *, decision=None, raise_exc=None):
    structured = _FakeStructured(decision=decision, raise_exc=raise_exc)
    monkeypatch.setattr(rn, "_llm", lambda: _FakeLLM(structured))


def test_route_A_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="A"))
    assert rn.router_node("3천만원 이하 흰색 SUV") == "A"


def test_route_B_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="B"))
    assert rn.router_node("패밀리카로 무난한 거") == "B"


def test_route_C_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="C"))
    assert rn.router_node("오늘 날씨 어때?") == "C"


def test_structured_output_failure_falls_back_to_B_when_car_signal(monkeypatch):
    # 구조화 출력 파싱 실패 + 질의에 매물 신호("SUV") → 보정으로 B.
    _patch_llm(monkeypatch, raise_exc=ValueError("parse error"))
    assert rn.router_node("괜찮은 SUV 추천해줘") == "B"


def test_structured_output_failure_falls_back_to_C_when_no_signal(monkeypatch):
    # 구조화 출력 실패 + 매물 신호 없음 → 보정으로 C(무관 처리).
    _patch_llm(monkeypatch, raise_exc=ValueError("parse error"))
    assert rn.router_node("안녕 반가워") == "C"


def test_fallback_route_signal_detection():
    # 순수 보정 함수 단위 — 신호 있으면 B, 없으면 C.
    assert rn._fallback_route("연비 좋은 전기차") == "B"
    assert rn._fallback_route("BMW 보여줘") == "B"
    assert rn._fallback_route("1+1은 뭐야") == "C"


def test_system_prompt_routes_finance_knowledge_to_C():
    """프롬프트 표류 방지 — 금융·세금·보험 일반지식을 C로 보내는 규칙이 프롬프트에 박혀 있어야 한다.

    party-mode 2026-06-23 결정(안건3): "할부·리스·취득세" 같은 일반지식은 어떤 매물을 보여줄지
    바꾸지 않으므로 B가 아니라 C(거절). 실제 분류 동작은 라이브 LLM에서 확인하지만, 여기서는
    프롬프트가 이 규칙을 잃지 않게 잠근다(규칙이 빠지면 라우터가 다시 B로 샌다).
    """
    prompt = rn._SYSTEM_PROMPT
    assert "할부" in prompt and "취득세" in prompt
    # 금융·세금·보험 키워드가 C 분류 규칙과 함께 등장해야 한다.
    assert "금융" in prompt and "C로 분류" in prompt


def test_missing_api_key_fails_loud(monkeypatch):
    # 키 부재 → require()가 RuntimeError(조용한 빈 결과 금지). _llm 실제 호출.
    monkeypatch.setattr(rn.settings, "gemini_api_key", None)
    with pytest.raises(RuntimeError) as exc:
        rn.router_node("아무 질의")
    assert "GEMINI_API_KEY" in str(exc.value)
