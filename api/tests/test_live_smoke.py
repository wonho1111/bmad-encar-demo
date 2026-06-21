"""라이브 스모크 — 실제 Gemini로 경로 A·B·C 대표 질의를 소량(3건 이하) 확인한다.

⚠️ 쿼터 보호: 무료 티어 일일 쿼터(약 20 req/day)를 아끼려고 **기본 실행에서는 스킵**한다.
  켜는 법: 환경변수 RUN_LIVE_SMOKE=1 + GEMINI_API_KEY + DATABASE_URL(경로 A는 DB 필요).
  켜졌을 때만 실제 LLM/DB를 호출한다. 429(쿼터 초과)·키부재는 실패가 아니라 skip 처리한다.

판정의 권위는 결정론 테스트(test_demo_acceptance.py)에 있다. 이 스모크는 "실물도 도는지"
  눈으로 1회 확인하는 보조 수단일 뿐, 통과 여부가 SM3/CM1 판정을 좌우하지 않는다.
[Source: story 4.8 AC5; api/docs/ai-demo-queries.md]
"""

import os

import pytest

# 기본 skip 게이트 — RUN_LIVE_SMOKE=1 일 때만 수집·실행한다.
_LIVE = os.getenv("RUN_LIVE_SMOKE") == "1"
pytestmark = pytest.mark.skipif(
    not _LIVE,
    reason="라이브 스모크 비활성(쿼터 보호). 켜려면 RUN_LIVE_SMOKE=1 설정.",
)


def _run_or_skip(query, context=None):
    """run_search를 실제로 호출하되, 키부재/쿼터(429)/DB부재는 skip으로 흡수한다."""
    from app.graph.graph import run_search

    try:
        return run_search(query, context)
    except Exception as exc:  # 쿼터 429·키부재·DB부재 등 — 실패가 아니라 skip
        msg = str(exc)
        if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
            pytest.skip(f"Gemini 쿼터 초과(429) — 라이브 스모크 skip: {msg[:120]}")
        if "GEMINI_API_KEY" in msg or "DATABASE_URL" in msg:
            pytest.skip(f"키/DB 미설정 — 라이브 스모크 skip: {msg[:120]}")
        raise  # 그 외 진짜 오류는 그대로 드러낸다


def test_live_smoke_pathA():
    """경로 A 대표 1건 — 구조형 질의가 매물(또는 FR17 0건 안내)을 돌려주는지(SM3)."""
    out = _run_or_skip("3천만원 이하 흰색 SUV")
    assert isinstance(out["answer"], str) and out["answer"]
    assert isinstance(out["listings"], list)


def test_live_smoke_pathB():
    """경로 B 대표 1건 — 의미형 추천이 매물(또는 안내)을 돌려주는지(SM3)."""
    out = _run_or_skip("패밀리카로 무난한 거")
    assert isinstance(out["answer"], str) and out["answer"]
    assert isinstance(out["listings"], list)


def test_live_smoke_pathC():
    """경로 C 대표 1건 — 무관 질의가 거절+빈 목록인지(CM1). guard는 LLM 호출 없음.

    라우터(LLM)가 C로 분류하면 guard_node가 빈 목록을 준다. 라우터 호출 1회만 든다.
    """
    out = _run_or_skip("오늘 날씨 어때?")
    assert out["listings"] == [], "무관 질의에는 매물이 없어야 한다(CM1)"
    assert "중고차" in out["answer"]
