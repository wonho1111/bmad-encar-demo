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


def test_route_SQL_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="SQL"))
    assert rn.router_node("3천만원 이하 흰색 SUV") == "SQL"


def test_route_HYBRID_structured_passthrough(monkeypatch):
    # 조합형(신규, 13.2) — 구조 조건(가격)과 의미/느낌 조건("무난한 패밀리카")이 함께 있는 질의.
    _patch_llm(monkeypatch, decision=RouterDecision(route="HYBRID"))
    assert rn.router_node("3천만원 이하로 무난한 패밀리카") == "HYBRID"


def test_route_CLARIFY_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="CLARIFY"))
    assert rn.router_node("패밀리카로 무난한 거") == "CLARIFY"


def test_route_REJECT_structured_passthrough(monkeypatch):
    _patch_llm(monkeypatch, decision=RouterDecision(route="REJECT"))
    assert rn.router_node("오늘 날씨 어때?") == "REJECT"


def test_structured_output_failure_falls_back_to_CLARIFY_when_car_signal(monkeypatch):
    # 구조화 출력 파싱 실패 + 질의에 매물 신호("SUV") → 보정으로 CLARIFY.
    _patch_llm(monkeypatch, raise_exc=ValueError("parse error"))
    assert rn.router_node("괜찮은 SUV 추천해줘") == "CLARIFY"


def test_structured_output_failure_falls_back_to_REJECT_when_no_signal(monkeypatch):
    # 구조화 출력 실패 + 매물 신호 없음 → 보정으로 REJECT(무관 처리).
    _patch_llm(monkeypatch, raise_exc=ValueError("parse error"))
    assert rn.router_node("안녕 반가워") == "REJECT"


def test_fallback_route_signal_detection():
    # 순수 보정 함수 단위 — 신호 있으면 CLARIFY, 없으면 REJECT(SQL·HYBRID로는 폴백하지 않음).
    assert rn._fallback_route("연비 좋은 전기차") == "CLARIFY"
    assert rn._fallback_route("BMW 보여줘") == "CLARIFY"
    assert rn._fallback_route("1+1은 뭐야") == "REJECT"


def test_fallback_route_sends_finance_knowledge_to_REJECT_like_the_prompt_does():
    """폴백도 프롬프트와 같은 판정을 해야 한다 — 금융·세금·보험 일반지식은 REJECT.

    review-5 실측: `_LISTING_SIGNALS`의 "차"가 "차이"·"자동차세"·"자동차보험" 안에서 부분
    매칭돼, 프롬프트가 REJECT로 못박은 질의 4개 중 3개가 폴백에서 CLARIFY로 샜다. 폴백이
    도는 유일한 순간(LLM 구조화 출력 실패)에 보험·세금 질문이 doc_rag로 흘러 엉뚱한 매물이
    나가는 경로다 — 프롬프트 규칙만 잠그고 폴백을 안 잠그면 규칙이 반쪽만 지켜진다.
    """
    for q in ("할부랑 리스 차이가 뭐야?", "취득세 얼마 나와?",
              "자동차세 계산해줘", "자동차보험 어떻게 들어?"):
        assert rn._fallback_route(q) == "REJECT", f"금융·세금·보험 질의가 샜다: {q!r}"
    # 대조군 — 금융 단어가 섞였어도 매물을 찾는 질의는 여전히 CLARIFY(과잉 거절 금지).
    assert rn._fallback_route("리스 차량 매물 보여줘") == "CLARIFY"


def test_system_prompt_routes_finance_knowledge_to_REJECT():
    """프롬프트 표류 방지 — 금융·세금·보험 일반지식을 REJECT로 보내는 규칙이 프롬프트에 박혀 있어야 한다.

    party-mode 2026-06-23 결정(안건3): "할부·리스·취득세" 같은 일반지식은 어떤 매물을 보여줄지
    바꾸지 않으므로 CLARIFY가 아니라 REJECT(거절). 실제 분류 동작은 라이브 LLM에서 확인하지만,
    여기서는 프롬프트가 이 규칙을 잃지 않게 잠근다(규칙이 빠지면 라우터가 다시 CLARIFY로 샌다).
    """
    prompt = rn._SYSTEM_PROMPT
    assert "할부" in prompt and "취득세" in prompt
    # 금융·세금·보험 키워드가 REJECT 분류 규칙과 함께 등장해야 한다.
    assert "금융" in prompt and "REJECT로 분류" in prompt


def test_system_prompt_defines_hybrid_and_its_precedence():
    """프롬프트 표류 방지 — 13.2의 헤드라인 동작(조합형 → HYBRID)이 프롬프트에 박혀 있어야 한다.

    HYBRID 분류는 오직 이 프롬프트 문자열에만 존재한다(_fallback_route는 SQL·HYBRID로
    폴백하지 않고, 다른 HYBRID 테스트는 RouterDecision을 모킹해 분류가 아니라 배선만 본다).
    실측(review-4): 프롬프트에서 HYBRID 카테고리 정의와 아래 우선순위 규칙을 통째로
    지워도 전체 스위트가 131 passed로 초록이었다 — 즉 이 스토리의 핵심 동작이 조용히
    사라져도 CI가 못 잡았다. 위 REJECT 잠금과 같은 방식으로 여기서 못박는다.
    """
    prompt = rn._SYSTEM_PROMPT
    # ① HYBRID 카테고리 정의 자체
    assert "HYBRID (조합형" in prompt, "HYBRID 카테고리 정의가 프롬프트에서 사라졌다"
    # ② 경계 규칙 — 명시 조건과 용도·느낌 조건이 둘 다 있으면 HYBRID(조합형 최우선).
    assert "둘 다" in prompt and "HYBRID다" in prompt, (
        "조합형 최우선 판정 규칙이 사라지면 구조+의미 질의가 다시 SQL로 흡수된다"
    )
    # ③ 네 갈래가 모두 유효값으로 명시돼 있어야 한다(구조화 출력 Literal과 락스텝).
    for route in ("SQL", "HYBRID", "CLARIFY", "REJECT"):
        assert route in prompt


def test_system_prompt_defines_both_sides_of_the_hybrid_boundary():
    """HYBRID 잠금의 반대편(SQL·CLARIFY 카테고리와 두 경계 규칙)도 함께 잠근다.

    review-5 실측: 위 테스트는 HYBRID 쪽만 보므로, CLARIFY 카테고리 블록을 통째로 지워도
    라우터 테스트 10건이 전부 초록이었다. HYBRID 정의문 자체가 "위 SQL의 명시적 조건과,
    아래 CLARIFY의 용도·느낌 조건이 함께"라며 두 이웃 블록을 직접 가리키므로, 그 둘이
    사라지면 HYBRID 정의도 의미를 잃는다 — 경계는 한쪽만 잠그면 안 잠긴 것과 같다.
    """
    prompt = rn._SYSTEM_PROMPT
    # ① 네 카테고리 블록이 각자 제 머리글로 정의돼 있어야 한다.
    for header in ("SQL (구조형", "HYBRID (조합형", "CLARIFY (질적", "REJECT (매물 무관"):
        assert header in prompt, f"카테고리 정의 블록이 사라졌다: {header!r}"
    # ② 경계 규칙 두 줄 — "조건만 있으면 SQL", "조건이 전혀 없으면 CLARIFY".
    assert "명시적 조건만 있고" in prompt, (
        "이 규칙이 사라지면 조건만 있는 질의가 HYBRID·CLARIFY로 샌다(G1 게이트가 보는 자리)"
    )
    assert "CLARIFY는 명시적 조건이 전혀 없고" in prompt, (
        "이 규칙이 사라지면 CLARIFY의 하한이 없어져 조건 있는 질의까지 되묻기로 흡수된다"
    )


def test_system_prompt_treats_superlatives_as_structural_condition():
    """최상급·정렬 표현이 구조조건 규칙에 박혀 있어야 한다(DW-611).

    실측(2026-08-02 재캡처): "제일 싼 차 뭐야?"류가 다른 구체 조건 없이는 CLARIFY로
    샜다 — 라우터가 최상급을 조건으로 세지 않았기 때문이다. 이 문자열들이 사라지면
    같은 회귀가 재발한다.
    """
    prompt = rn._SYSTEM_PROMPT
    assert "최상급" in prompt
    assert "제일 싼 차 뭐야?" in prompt
    assert "가장 비싼" in prompt


def test_system_prompt_routes_replacement_requests_by_condition_presence():
    """교체요청은 별도 갈래가 아니라 SQL/HYBRID 조건 유무로 갈린다(DW-612·DW-617 #1).

    대조 예시 두 쌍이 프롬프트에 있어야 한다 — 명시 차종만 있는 교체요청은 SQL,
    느낌이 섞이면 HYBRID(13.2 4분기 계약이 상위)라는 사실을 프롬프트가 명시해야
    "교체 요청은 무조건 SQL"로 LLM이 오판해 13.2 계약(구조+의미=HYBRID)을 어기지 않는다.
    """
    prompt = rn._SYSTEM_PROMPT
    assert "교체요청" in prompt
    assert "쏘렌토 같은 SUV로 바꿔줘" in prompt
    assert "가족이 타기 좋은 SUV로 바꿔줘" in prompt
    assert "교체요청이라는 이유만으로 CLARIFY로 보내지 않는다" in prompt


def test_missing_api_key_fails_loud(monkeypatch):
    # 키 부재 → require()가 RuntimeError(조용한 빈 결과 금지). _llm 실제 호출.
    monkeypatch.setattr(rn.settings, "gemini_api_key", None)
    with pytest.raises(RuntimeError) as exc:
        rn.router_node("아무 질의")
    assert "GEMINI_API_KEY" in str(exc.value)
