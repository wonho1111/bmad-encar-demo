"""라이브 스모크 — 실제 Gemini로 4개 라우트(SQL·CLARIFY·REJECT·HYBRID) 대표 질의를 소량 확인한다.

⚠️ 쿼터 보호: 실제 과금·호출이 일어나므로 **기본 실행에서는 스킵**한다.
  ✎ 2026-07-30 정정: 이 자리에 있던 "무료 티어 일일 쿼터(약 20 req/day)"는 **사실이 아니다** —
  이 프로젝트의 Gemini 키는 유료 티어다(사용자 확인). 그 낡은 문구가 리포 안의 유일한 근거라,
  Story 13.1의 무인 세션이 그걸 읽고 44개 질의 baseline 캡처를 "쿼터를 넘긴다"며 3건만 하고
  미뤘다(DW-554). 근거가 틀리면 판단도 틀린다 — 스킵 자체는 유지하되(과금은 실제로 발생),
  이유를 사실로 바꾼다.
  켜는 법: 환경변수 RUN_LIVE_SMOKE=1 + GEMINI_API_KEY + DATABASE_URL(경로 A는 DB 필요).
  켜졌을 때만 실제 LLM/DB를 호출한다. 429(쿼터 초과)·키부재는 실패가 아니라 skip 처리한다.

판정의 권위는 결정론 테스트(test_demo_acceptance.py)에 있다. 이 스모크는 "실물도 도는지"
  눈으로 1회 확인하는 보조 수단일 뿐, 통과 여부가 SM3/CM1 판정을 좌우하지 않는다.
[Source: story 4.8 AC5; api/docs/ai-demo-queries.md]
"""

import logging
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
    assert out["route"] == "SQL"


def test_live_smoke_pathB():
    """경로 B 대표 1건 — CLARIFY가 실제로 되묻기 페이로드를 돌려주는지(13.4, SM3).

    route만 보고 통과하면 13.3의 DW-577류 공백(라벨은 맞는데 실제 실행 경로를 못 구분)을
    되풀이하므로, clarify 페이로드 자체를 직접 단언한다.
    """
    out = _run_or_skip("패밀리카로 무난한 거")
    assert isinstance(out["answer"], str) and out["answer"]
    assert isinstance(out["listings"], list)
    assert out["route"] == "CLARIFY"
    assert out["listings"] == []
    assert out["clarify"] is not None
    assert out["clarify"]["chips"]


def test_live_smoke_clarify_cap_forces_results():
    """되묻기 상한 초과 시 서버가 실제로 clarify 없이 결과를 강제 제시하는지(13.4 DW-563, B4).

    6턴(12개 항목)짜리 더미 context를 실어 같은 CLARIFY 대표 질의를 재호출한다 — 상한 강제가
    라이브로 실제 동작하는지 확인한다(단위테스트의 모킹된 doc_rag_node가 아니라 실물).
    """
    dummy_context = [
        {"role": "user", "content": "그냥 무난한 차"},
        {"role": "assistant", "content": "조건을 조금만 좁혀볼게요"},
    ] * 6  # 6턴 = clarify_turns 6 >= _CLARIFY_TURN_CAP(3)
    out = _run_or_skip("패밀리카로 무난한 거", dummy_context)
    # route 단언이 없으면 이 테스트는 상한 강제를 전혀 증명하지 못한다 — clarify가 None인 것은
    # SQL·HYBRID·REJECT 어느 라우트에서나 참이라, 상한 분기를 통째로 지워도 초록으로 남는다.
    # (context가 실제 contextualize_query를 거치며 질의가 재작성되므로 라우트가 바뀔 수 있다.)
    assert out["route"] == "CLARIFY"
    assert out["clarify"] is None
    assert isinstance(out["listings"], list)
    if out["listings"]:
        # 강제 폴백이 실제로 doc_rag_node를 탔다는 라이브 증거 — 매물이 나왔으면 고정 안내가 붙는다.
        from app.graph.graph import _CLARIFY_CAP_NOTICE

        assert _CLARIFY_CAP_NOTICE in out["answer"]


def test_live_smoke_pathC():
    """경로 C 대표 1건 — 무관 질의가 거절+빈 목록인지(CM1). guard는 LLM 호출 없음.

    라우터(LLM)가 C로 분류하면 guard_node가 빈 목록을 준다. 라우터 호출 1회만 든다.
    """
    out = _run_or_skip("오늘 날씨 어때?")
    assert out["listings"] == [], "무관 질의에는 매물이 없어야 한다(CM1)"
    assert "중고차" in out["answer"]
    assert out["route"] == "REJECT"
    # 13.5: narrowed_by 고정 상수가 실제로 실려 오는지(비공백 리스트) 확인.
    assert out["narrowed_by"]


def test_live_smoke_hybrid(caplog):
    """조합형(구조+의미) 대표 1건 — HYBRID로 분류되고 hybrid_rag_node가 실제 단일쿼리로
    응답하는지(Story 13.3 AC — 직접 실행·관찰, B4)."""
    caplog.set_level(logging.INFO, logger="app.graph.hybrid_rag_node")
    out = _run_or_skip("3천만원 이하로 무난한 패밀리카")
    assert isinstance(out["answer"], str) and out["answer"]
    assert isinstance(out["listings"], list)
    assert out["route"] == "HYBRID"
    # route만으로는 부족하다 — route는 라우터 노드가 정하고, hybrid_rag_node가 구조조건을
    # 못 뽑아 doc_rag_node로 폴백해도 route는 그대로 HYBRID다. 즉 이 단언만 있으면
    # "하이브리드 단일쿼리가 실제로 돌았다"와 "폴백해서 그냥 벡터검색만 했다"를 구분하지
    # 못한다. 두 노드는 답변 문구가 다르므로 그걸로 실제 실행 경로를 고정한다.
    assert out["answer"].startswith("조건에 맞는 매물")  # doc_rag_node는 "'<질의>'에 어울리는…"
    assert "원하시는 용도나 예산" not in out["answer"]  # doc_rag_node의 0건 문구 배제
    # 매물이 0건이면 아래 인용 단언은 "가이드 주입 고장"이 아니라 "0건"을 잡는 것이므로,
    # 두 실패 원인을 분리해 먼저 확인한다(후속 코드리뷰).
    assert out["listings"], "매물 0건이면 아래 가이드 단언들의 의미가 사라진다"
    # 가이드(api/corpus/02-패밀리카-적합-차종.md)가 컷오프(FR49) 이내로 찾아져 인용됐다는 증거.
    assert "(참고:" in out["answer"]
    # ⚠️ 위 인용 단언만으로는 **부족하다**(후속 코드리뷰, 변이 실측). 인용은
    # `if listings and guide` — 가이드가 거리상 가까운지만 보고, 그 가이드가 조건추출
    # 프롬프트에 실제로 반영됐는지는 보지 않는다. 실제로 _GUIDE_BLOCK_TEMPLATE를 통째로
    # 비워 질의확장을 죽여도 answer에는 "(참고: …)"가 그대로 붙어 이 단언이 통과했다.
    # 그래서 이 스토리의 headline(FR44 질의확장)은 **추출된 구조조건**에서 직접 관찰한다:
    # 조건추출 규칙 2는 "느낌·용도 표현은 버려라"이므로, 가이드 주입이 없으면 이 질의에서
    # LLM이 뽑을 수 있는 건 가격 조건뿐이다. 가이드가 실제로 주입돼 규칙 2를 눌렀을 때만
    # 차종·인승·무사고(guide가 명시하는 구조 컬럼)가 조건에 등장한다.
    condition_logs = " ".join(
        r.getMessage() for r in caplog.records if "구조조건" in r.getMessage()
    )
    assert condition_logs, "hybrid_rag_node의 구조조건 로그가 없다 — 폴백했거나 로깅이 사라졌다"
    assert any(col in condition_logs for col in ("body_type", "seats", "accident_free")), (
        f"가이드 유래 구조조건이 추출되지 않았다(질의확장 미작동 의심): {condition_logs}"
    )
    # body_type 자체를 응답 매물에서 직접 단언하지 않는 이유: body_type은 SELECT_COLUMNS
    # (listing_cards.py)에도 ListingCard wire 계약(app/schemas/ai.py)에도 없어 응답으로
    # 나오지 않는다. 그래서 다음으로 가까운 관측 지점인 추출 조건 로그를 쓴다.
