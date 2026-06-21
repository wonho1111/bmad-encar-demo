"""contextualize_node 단위 테스트 — FR18 멀티턴 맥락화(AC5/AC6).

LLM을 모킹해 네트워크 없이 검증한다:
  · context 없음(None·[]) → LLM 미호출 + 원 query 그대로(단일턴, 함정 #2).
  · context 있음 → 재작성 LLM 호출되고 결과 반환.
  · 재작성 결과 공백/예외 → 원 query 폴백(조용한 빈 결과 금지, 함정 #3).
  · 키 부재는 context 있을 때만 fail-loud(없으면 통과).
"""

import pytest

from app.graph import contextualize_node
from app.graph.contextualize_node import contextualize_query


class _FakeResp:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    """invoke를 가로채 미리 정한 응답을 돌려주는 가짜 LLM."""

    def __init__(self, content):
        self._content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return _FakeResp(self._content)


def _ctx(*turns):
    """('user','...') 류를 ConversationTurn 비슷한 dict 리스트로."""
    return [{"role": r, "content": c} for r, c in turns]


def test_no_context_returns_query_unchanged_and_no_llm(monkeypatch):
    # context 없으면 LLM을 부르면 안 된다 → _llm을 호출하면 실패하도록 심어 검증.
    def _boom():
        raise AssertionError("단일턴인데 LLM이 호출됨(함정 #2 위반)")

    monkeypatch.setattr(contextualize_node, "_llm", _boom)
    assert contextualize_query("3천만원 이하 SUV", None) == "3천만원 이하 SUV"
    assert contextualize_query("3천만원 이하 SUV", []) == "3천만원 이하 SUV"


def test_with_context_rewrites_query(monkeypatch):
    fake = _FakeLLM("패밀리카로 무난한 차 중 더 저렴한 매물")
    monkeypatch.setattr(contextualize_node, "_llm", lambda: fake)
    ctx = _ctx(("user", "패밀리카로 무난한 거"), ("assistant", "싼타페 등 추천드려요"))
    out = contextualize_query("그 중 더 싼 거", ctx)
    assert out == "패밀리카로 무난한 차 중 더 저렴한 매물"
    assert len(fake.calls) == 1  # 맥락 있으면 정확히 1회 호출


def test_blank_rewrite_falls_back_to_original(monkeypatch):
    # 재작성 결과가 공백이면 원 query로 폴백.
    monkeypatch.setattr(contextualize_node, "_llm", lambda: _FakeLLM("   "))
    ctx = _ctx(("user", "3천만원 이하 SUV"))
    assert contextualize_query("흰색만", ctx) == "흰색만"


def test_llm_exception_falls_back_to_original(monkeypatch):
    class _RaisingLLM:
        def invoke(self, messages):
            raise RuntimeError("일시 오류")

    monkeypatch.setattr(contextualize_node, "_llm", lambda: _RaisingLLM())
    ctx = _ctx(("user", "3천만원 이하 SUV"))
    assert contextualize_query("흰색만", ctx) == "흰색만"


def test_missing_key_fails_loud_only_with_context(monkeypatch):
    # 키 부재 시: context 있으면 require()가 fail-loud, 없으면 통과(LLM 미진입).
    monkeypatch.setattr(contextualize_node.settings, "gemini_api_key", None)
    # 단일턴은 키 없이도 통과.
    assert contextualize_query("3천만원 이하 SUV", None) == "3천만원 이하 SUV"
    # 멀티턴은 키가 없으면 명확히 실패(조용한 오답 금지).
    with pytest.raises(RuntimeError):
        contextualize_query("그 중 더 싼 거", _ctx(("user", "패밀리카")))


def test_rewrite_handles_list_content_blocks(monkeypatch):
    # 일부 Gemini 모델은 content를 [{'type':'text','text':...}] 리스트로 준다(라이브에서 발견).
    # _extract_text가 평탄화해 재작성 문자열을 제대로 뽑아야 한다(폴백으로 새지 않음).
    blocks = [{"type": "text", "text": "패밀리카로 무난한 차 중 더 저렴한 매물"}]
    monkeypatch.setattr(contextualize_node, "_llm", lambda: _FakeLLM(blocks))
    ctx = _ctx(("user", "패밀리카로 무난한 거"))
    out = contextualize_query("그 중 더 싼 거", ctx)
    assert out == "패밀리카로 무난한 차 중 더 저렴한 매물"


def test_only_recent_turns_serialized(monkeypatch):
    # 6턴 초과 맥락이라도 최근 N턴만 직렬화돼 프롬프트에 들어간다(토큰 절약).
    fake = _FakeLLM("재작성됨")
    monkeypatch.setattr(contextualize_node, "_llm", lambda: fake)
    many = _ctx(*[("user", f"질문{i}") for i in range(10)])
    contextualize_query("그거", many)
    human_msg = fake.calls[0][-1][1]  # ("human", text)
    assert "질문0" not in human_msg  # 오래된 턴은 빠짐
    assert "질문9" in human_msg      # 최근 턴은 포함
