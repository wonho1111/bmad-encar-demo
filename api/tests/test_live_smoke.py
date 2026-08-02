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
import time

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


def test_live_smoke_langsmith_tracing():
    """LangSmith 트레이싱(FR51, Story 13.7)이 실제로 트레이스를 남기는지(B4 — 존재 확인이 아니라
    작동 확인). RUN_LIVE_SMOKE=1만으로는 부족해 별도 게이트를 둔다: LangSmith 계측 env는
    app.config.Settings가 모르는 값(extra="ignore")이라 프로세스 환경변수로 직접 노출돼
    있어야만 켜진다(spec-13-7 Design Notes) — 안 켜져 있으면 skip한다.

    게이트는 env 이름을 손으로 비교하지 않고 SDK 판정(`tracing_is_enabled()`/`get_env_var()`)을
    그대로 쓴다. SDK의 해석 순서는 **접미사 우선, 그 안에서 네임스페이스**다(실측 확인):
    `TRACING_V2` 자리가 `TRACING` 자리보다 먼저고, 같은 자리 안에서만 `LANGSMITH_`가
    `LANGCHAIN_`를 이긴다. 이름을 하드코딩하면 "계측은 켜졌는데 테스트만 skip"되는 조용한
    구멍이 생긴다 — 이 스토리가 경고하는 "존재≠작동"과 같은 함정. 정확한 규칙은
    `api/tests/test_langsmith_env_contract.py`가 secrets 없이 결정론으로 못박는다.

    ⚠️ 이 검사가 **안 보는 것**(추측 아니라 실측, B4):
      · CI에서 안 돈다 — tests.yml이 RUN_LIVE_SMOKE·LangSmith env를 의도적으로 안 넣는다
        (라이브·과금 테스트는 CI 밖이 이 저장소의 표준: project-context 규칙 12). 따라서
        의존성 업그레이드로 계측이 깨지는 것은 **사람이 이 테스트를 돌려야만** 잡힌다.
        (자동 감지가 없는 근본 원인 = langchain 계열 버전 미고정 — deferred-work DW-615)
      · 라우팅 한 갈래만 탄다 — 아래 질의가 현재 타는 경로 하나만 보고, 나머지 라우트
        (SQL·HYBRID·REJECT) 노드의 트레이스 여부는 확인하지 않는다. Story 13.9가 라우팅을
        바꾸면 어느 갈래를 타는지도 바뀌지만, 노드 이름을 그래프에서 구하므로 검사 자체는
        깨지지 않는다(무엇을 안 보는지의 범위만 달라진다).
      · 스팬의 **존재**만 본다 — 트레이스 안의 입력·출력 값이 맞는지는 보지 않는다.
      · `_run_or_skip`가 DB·키 부재와 429를 skip으로 흡수하므로, 인프라가 죽어 있으면
        계측이 멀쩡한지 여부와 무관하게 초록(skip)이 된다.
    """
    from langsmith.utils import get_env_var, get_tracer_project, tracing_is_enabled

    if not tracing_is_enabled() or not get_env_var("API_KEY"):
        pytest.skip(
            "LangSmith 계측 env가 프로세스에 노출돼야 함(LANGSMITH_/LANGCHAIN_ 둘 다 인정)"
            " — RUN_LIVE_SMOKE와 별개 게이트, api/.env.example 참조"
        )

    from langchain_core.tracers.context import collect_runs
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langsmith import Client
    from langsmith.utils import LangSmithNotFoundError

    from app.graph.graph import COMPILED_GRAPH

    client = Client()
    project = get_tracer_project()  # 전송 대상 프로젝트를 SDK와 동일한 규칙으로 구한다

    # 이 호출의 트레이스를 **콜백이 돌려준 실제 run id**로 특정한다. "질의 문자열이 같은
    # 새 run"으로 추측하면 (a) 같은 프로젝트를 쓰는 다른 프로세스(동시 로컬 세션, Cloud Run
    # 운영 트래픽)의 트레이스로 통과할 수 있고, (b) 입력 마스킹(LANGSMITH_HIDE_INPUTS=true)
    # 이나 그래프 state 키 개명만으로 영구 false red가 된다 — 둘 다 실물 확인한 경로다.
    query = "가장 저렴한 SUV 보여줘"
    with collect_runs() as collected:
        out = _run_or_skip(query)
    assert isinstance(out["answer"], str) and out["answer"]

    assert collected.traced_runs, (
        "run_search 실행에 LangChain 콜백이 아예 붙지 않았다 — 전역 계측이 꺼진 상태(B4)"
    )
    # collect_runs는 루트를 **여러 개** 돌려줄 수 있다(실측: LangGraph 말고 router 안의
    # RunnableSequence도 자기 콜백 컨텍스트에선 루트로 잡힌다). 서버에서 실제 트레이스
    # 루트인 것은 그중 하나뿐이므로 [0]을 고르면 틀린 id를 잡는다 — 고르지 말고 후보를
    # 전부 조회해 합친다. 어느 쪽이든 이 프로세스가 방금 만든 UUID라 남의 트레이스는 섞일 수 없다.
    candidate_ids = {r.id for r in collected.traced_runs}

    wait_for_all_tracers()  # 백그라운드 전송 스레드를 먼저 비운다(서버 색인 지연과 분리)

    # 노드 이름은 컴파일된 그래프에서 구한다 — 하드코딩하면 13.9의 노드 개명에 깨지고,
    # "비루트 chain 스팬"으로 대신하면 langchain-core가 만드는 RunnableSequence가 그 자리를
    # 채워 **노드 계측이 통째로 죽어도 통과**한다(실측으로 재현 확인).
    node_names = set(COMPILED_GRAPH.get_graph().nodes) - {"__start__", "__end__"}

    # 서버 색인 지연 실측(2026-08-02): t=3s엔 0건, t≈6s에 8건. 루트가 먼저 색인되고 자식
    # 스팬이 뒤따를 수 있으므로 "루트가 보이면 중단"이 아니라 **세 조건이 다 설 때까지**
    # 기다린다 — 아니면 색인 도중 상태를 "계측이 끊겼다"로 오진한다(false red).
    mine, run_types, node_spans = [], set(), []
    deadline = time.time() + 30
    while True:
        found = {}
        for tid in candidate_ids:
            try:
                for r in client.list_runs(project_name=project, trace_id=tid):
                    found[r.id] = r
            except LangSmithNotFoundError:
                pass  # 프로젝트가 아직 생성 전 — 예산 안에서 재시도한다
        mine = list(found.values())
        run_types = {r.run_type for r in mine}
        node_spans = [r for r in mine if r.name in node_names]
        if mine and "llm" in run_types and node_spans:
            break
        if time.time() >= deadline:
            break
        time.sleep(2)

    assert mine, (
        f"run_search({query!r}) 실행 후 LangSmith 프로젝트 {project!r}에 이 호출의 트레이스"
        f"({sorted(str(i) for i in candidate_ids)})가 기록되지 않았다"
        "(설정은 있는데 실제로 작동하지 않는 상태 — B4)"
    )
    # 자동 계측은 두 갈래로 독립이다: LangGraph 노드 스팬과 LLM 콜백 스팬.
    # 개수만 세면 한쪽이 통째로 죽어도 통과하므로 두 갈래를 각각 못박는다.
    assert "llm" in run_types, (
        f"LLM 스팬이 없다 — ChatGoogleGenerativeAI 계측이 끊겼다: {sorted(run_types)}"
    )
    assert node_spans, (
        "그래프 노드 스팬이 없다 — LangGraph 노드 계측이 끊겼다"
        f"(기대한 노드 {sorted(node_names)} 중 하나도 없음, 실제: {sorted(r.name for r in mine)})"
    )
