"""4단계 에이전트 전환(run_search_agent, agent.py) 성능 회귀 검증기.

목적: 직전 RAG 개선 세션(커밋 42e5b1c~968bade, "E2E 10질의 검증")이 확인했던 동작과
  DW-847(동적 되묻기)·DW-848(정렬 축) resolved 지점이, 그래프 기반 run_search(graph.py)에서
  툴콜링 에이전트 run_search_agent(agent.py)로 넘어온 뒤에도 여전히 성립하는지 실측한다.

질의 출처(우선순위):
  1. `api/docs/ai-ab-test-queryset.json` — 2026-08-02 재설계된 골든 질의셋(S=SQL 14·H=HYBRID 27·
     CL=CLARIFY 7·R=REJECT 8·M=멀티턴 8, 총 64항목). score_ab.py/run_phase_b.py가 채점에 쓰던
     것과 동일 출처 — "직전 RAG 수정 작업"이 실제로 검증 기준으로 삼았던 질의셋이다.
  2. `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-847·DW-848 resolution에 박힌
     실측 질의 원문("차 추천해줘", "3천만원 이하 하이브리드 SUV 연식 최신순") — 4단계 완료
     당시 사람이 직접 돌려 확인한 질의라 그대로 재사용한다.
  3. `api/scripts/bench/bench_reranker.py`의 QUERIES(8건, 리랭커 품질 벤치용) — 이번 회귀에는
     보충하지 않는다(1·2에서 이미 10건을 넘겨 충분).

기계 판정 가능한 것만 본다(LLM 응답은 비결정적 — 문구 완전일치 단언 금지):
  - "search": listings가 min_listings건 이상 반환돼야 한다.
  - "reject": listings가 0건이어야 한다(매물 무관 질의에 매물을 지어내면 회귀).
  - "clarify_ok": listings>=1 이거나 clarify가 채워져야 한다(모호 질의는 둘 다 정답 —
    되묻기 대신 에이전트가 가이드 지식으로 실제로 검색해도 정답으로 인정, 4단계의 의도된
    확장이다. DW-847 참조).
  - "sorted_year_desc": listings의 year가 비증가(내림차순)여야 한다.
  - "guide": answer에 expected_keywords 중 1개 이상(소문자 비교)이 있어야 한다.
  각 항목에 tools_expected(부분집합)를 얹으면 tools_used가 그 도구들을 포함하는지도 본다.

멀티턴(MULTITURN_CASES): 사용자 실측 결함(직전 턴 매물을 두고 "그중 두 번째 시세 알려줘"·
  "그 5개 비교해줘"라고 물으면 에이전트가 재검색만 반복) 수정을 검증한다. 1턴을 실제로 실행한
  결과(listings)로 ConversationTurn(role=assistant, listing_ids=...) 딕셔너리를 조립해 2턴의
  context로 넘긴다 — run_search_agent가 실제로 받는 형태(웹 buildContext와 동일 조립)를 그대로
  재현한다. 판정은 kind별로 다르다(아래 judge_multiturn 참조).

실행:
  cd api && .venv/bin/python scripts/verify_agent_regression.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.agent import run_search_agent  # noqa: E402

# ── 질의 목록 ────────────────────────────────────────────────────────────────
# id: 출처 문서의 원 id를 그대로 보존(추적용). kind: 판정 방식. 나머지는 kind별 부가 기대값.
QUERIES: list[dict] = [
    # --- SQL(구조조건 검색) — ai-ab-test-queryset.json S그룹. 실제 매물이 나와야 한다.
    {"id": "S1", "query": "3천만원 이하 SUV 보여줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "S4", "query": "디젤 SUV 7인승 이상으로 알려줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "S8", "query": "현대 SUV 중에 주행거리 3만km 이하인 거", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "S13", "query": "아반떼 보여줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "S14", "query": "쏘렌토 있어?", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},

    # --- HYBRID(구조조건+의미 narrowing) — H그룹. 가이드 지식으로 조건을 뽑아도 결국 매물이 나와야 한다.
    {"id": "H1", "query": "3천만원 이하로 무난한 패밀리카 찾아줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "H2", "query": "2천만원 이하로 초보운전자가 몰기 편한 차 보여줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "H9", "query": "2천만원 이하로 주차하기 쉬운 작은 차 알려줘", "kind": "search",
     "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "H19", "query": "4천만원 이하로 장거리 출퇴근 유지비 적고 어댑티브크루즈 있는 무사고 차",
     "kind": "search", "min_listings": 1, "tools_expected": ["search_listings"]},
    {"id": "H26", "query": "2018년 이후 무사고 중형·대형 세단 중에 내비게이션 있고 장거리 운전이 편한 차",
     "kind": "search", "min_listings": 1, "tools_expected": ["search_listings"]},

    # --- CLARIFY(모호) — CL그룹. 옛 그래프는 고정 되묻기만 냈지만, 에이전트는 가이드 지식으로
    # 실제 검색해도 된다(DW-847이 이 확장을 의도적으로 만들었다) — 그래서 관대하게 둘 다 정답.
    {"id": "CL1", "query": "초보운전자 첫차로 뭐가 좋아?", "kind": "clarify_ok"},
    {"id": "CL3", "query": "그냥 괜찮은 차 아무거나 추천해줘", "kind": "clarify_ok"},
    {"id": "CL6", "query": "사회 초년생이 탈만한 저렴한 차 추천해줘", "kind": "clarify_ok"},
    {"id": "CL7", "query": "주행거리 많은 차 사도 괜찮을까?", "kind": "clarify_ok"},

    # --- REJECT(매물 무관) — R그룹. 매물을 지어내면(listings>0) 회귀.
    {"id": "R1", "query": "오늘 서울 날씨 어때?", "kind": "reject"},
    {"id": "R2", "query": "김치찌개 맛있게 끓이는 법 알려줘", "kind": "reject"},
    {"id": "R3", "query": "비트코인 지금 사도 돼?", "kind": "reject"},
    {"id": "R4", "query": "차 살 때 할부랑 리스 뭐가 달라?", "kind": "reject"},
    {"id": "R6", "query": "자동차 보험료 어떻게 하면 아낄 수 있어?", "kind": "reject"},
    # R7은 _FINANCE_SIGNALS 키워드(할부·보험 등)가 없어 결정론 사전차단을 안 타는 REJECT
    # 후보다 — 에이전트가 순수 LLM 판단만으로도 매물 무관 지식 질문임을 여전히 걸러내는지
    # 보는 항목(사전차단에 안전망으로 얹혀가던 게 아니라 진짜 판단력을 보는 케이스).
    {"id": "R7", "query": "중고차 살 때 사고이력이랑 침수차 어떻게 확인해?", "kind": "reject"},

    # --- DW-848 resolved 지점 — search_listings의 sort_by=year_desc 화이트리스트 경로가
    # 에이전트 루프 끝까지(최종 구조화 출력의 listings 순서까지) 실제로 내림차순을 유지하는지.
    {"id": "DW848-sort", "query": "3천만원 이하 하이브리드 SUV 연식 최신순", "kind": "sorted_year_desc",
     "min_listings": 2, "tools_expected": ["search_listings"]},

    # --- DW-847 resolved 지점 — 고정 템플릿이 아니라 맥락 기반 동적 되묻기(또는 실제 검색)가
    # 나오는지. 원 트리거 문구 그대로("차 추천해줘"는 예산·용도·차종이 전혀 없는 완전 모호 질의).
    {"id": "DW847-dynamic-clarify", "query": "차 추천해줘", "kind": "clarify_ok"},
]


# ── 멀티턴 케이스 ────────────────────────────────────────────────────────────
# 1턴을 실제로 실행해 얻은 listings로 2턴 context를 조립한다(judge_multiturn 참조).
MULTITURN_CASES: list[dict] = [
    # --- MT1: "그중 N번째 시세" — 재검색 대신 market_price_stats로 직행하는지.
    {"id": "MT1", "turn1": "1,000만원 이하 실속형 차 추천해줘", "turn2": "그중 두 번째 매물 시세 분석해줘",
     "kind": "mt_market_diagnosis"},
    # --- MT2: "그 매물들 전부 비교해줘" — compare_listings가 실제로 불리는지.
    {"id": "MT2", "turn1": "1,000만원 이하 실속형 차 추천해줘", "turn2": "그 매물들 전부 비교해줘",
     "kind": "mt_compare"},
    # --- MT3(코디네이터 추가) — 주어 없는 후속 시세 요청이 직전 목록(1턴 결과) 밖의 매물로
    # 새지 않는지("그랜저 여러 턴 뒤 쏘렌토 추천 → 시세 문의" 변종의 최소 재현: 1턴이 이미
    # "직전 목록"을 만들어 둔 상태에서 2턴이 주어 없이 시세만 요구한다).
    {"id": "MT3", "turn1": "쏘렌토 하이브리드 추천해줘", "turn2": "아니 시세분석해달라고",
     "kind": "mt_no_resubject_diagnosis"},
    # --- MT6(2026-08-31 실측 결함 F2, 다건 판정 환각 회귀) — "이 매물들 전부 시세 분석해줘"
    # 처럼 여러 매물의 시세 판정을 한 번에 요청받으면, 매물마다 market_price_stats를 각각
    # 호출해야 한다(1건만 호출하고 나머지는 판정을 지어내면 회귀). 호출 "횟수"를 보므로
    # tools_expected(부분집합, 존재 여부만 봄)로는 못 잡는다 — judge_multiturn에서 직접 센다.
    {"id": "MT6", "turn1": "2천만원 이하 세단 추천해줘", "turn2": "이 매물들 전부 시세 분석해줘",
     "kind": "mt_market_stats_multi_call"},
    # --- MT7(2026-08-31 E2E 2라운드 실측 결함 R1, "직전 목록 없는데 지시어" 재검색 도피 회귀)
    # — 1턴 "차 추천해줘"는 예산·용도·차종이 전혀 없어 되묻기(clarify)로 끝나야 한다(매물 0건,
    # 즉 [직전 대화에서 보여준 매물] 블록이 2턴에 생기지 않는다). 그 상태에서 2턴이 "그중"류
    # 지시어 없이 주어 없는 시세 분석을 요청하면("아니 시세분석해달라고"), 에이전트가 가리킬
    # 매물이 아예 없으므로 search_listings로 엉뚱한 매물을 새로 찾거나 market_price_stats를
    # 부르면 안 되고(둘 다 없는 대상을 지어내는 것), clarify로 어떤 차량인지 되물어야 한다.
    {"id": "MT7", "turn1": "차 추천해줘", "turn2": "아니 시세분석해달라고",
     "kind": "mt_no_block_reclarify"},
]


# ── 3턴 케이스 ───────────────────────────────────────────────────────────────
# P1(실측 결함, 2026-08-31): "레이는?"류 후속 질의가 두 턴 전 매물을 못 참조했다 —
# _recent_assistant_listing_ids가 "가장 최근 listing_ids 보유 턴 1개"만 쓰던 것을 "여러 턴
# 병합"으로 고친 지점(agent.py)을 실제 3턴 흐름으로 검증한다. 1·2턴은 실제로 실행하고, 각
# 턴의 assistant listing_ids는 웹 ChatAssistant.tsx의 listingIdsOf와 동일 규칙
# (_client_listing_ids)으로 뽑아 3턴 context에 함께 싣는다 — 실제 클라이언트가 보내는 형태를
# 그대로 재현해야, "2턴 전 매물 참조"가 서버 로직만이 아니라 클라 조립까지 포함해 실제로
# 동작하는지 확인할 수 있다.
THREE_TURN_CASES: list[dict] = [
    # --- MT4(코디네이터 추가, P1 검증) — 1턴 검색 → 2턴 "그중 첫 번째" 시세 진단(매물카드는
    # 0장, market_diagnosis만 채워짐) → 3턴 주어 없는 "두 번째 매물은?" — 3턴이 1턴 목록의
    # "두 번째" 매물을 가리키려면 1턴 listing_ids가 2턴을 건너 3턴까지 살아 있어야 한다.
    {"id": "MT4", "turn1": "1,000만원 이하 경차 추천해줘", "turn2": "그중 첫 번째 매물 시세 분석해줘",
     "turn3": "두 번째 매물은?", "kind": "mt4_second_listing_no_resubject"},
    # --- MT5(2026-08-31 실측 결함 F1, "나머지 두 개랑 비교" 재검색 도피 회귀) — 1턴 추천 목록
    # 중 1건을 2턴에서 진단한 뒤, 3턴이 "나머지"(진단 안 한 것들)를 비교해달라고 하면 재검색
    # (search_listings) 없이 1턴 목록의 id로 compare_listings를 불러야 한다. LangSmith
    # 원자료로 확정된 실측 결함(직전 트레이스에서 에이전트가 search_listings를 2번 새로 불러
    # 그 결과로 비교한 사례)의 최소 재현.
    {"id": "MT5", "turn1": "3천만원 이하 SUV 추천해줘", "turn2": "그중 첫 번째 시세 봐줘",
     "turn3": "나머지 두 개랑 뭐가 다른지 비교해줘", "kind": "mt5_no_resubject_compare_from_prior_list"},
]


def _client_listing_ids(result: dict) -> list[str] | None:
    """웹 ChatAssistant.tsx의 listingIdsOf와 동일 규칙 — 이 턴이 "실제로 보여준" 매물 id들을
    뽑는다(카드 목록이 있으면 그 id들, 없고 단건 시세 진단만 있으면 그 진단 대상 id 1개,
    둘 다 없으면 None). 3턴 러너가 실제 클라이언트의 context 조립을 그대로 재현하는 데 쓴다.
    """
    listings = result.get("listings") or []
    if listings:
        return [c.id for c in listings]
    diagnosis = result.get("market_diagnosis")
    if diagnosis:
        return [diagnosis["listing"]["id"]]
    return None


# ── 판정 함수 ────────────────────────────────────────────────────────────────

def _check_tools_expected(result: dict, expects: dict) -> str | None:
    """tools_expected(부분집합)가 있으면 검사. 위반 시 사유 문자열, 통과면 None."""
    tools_expected = expects.get("tools_expected")
    if not tools_expected:
        return None
    tools_used = set(result.get("tools_used") or [])
    missing = [t for t in tools_expected if t not in tools_used]
    if missing:
        return f"tools_expected 미충족: {missing} (실제 tools_used={result.get('tools_used')})"
    return None


def judge(expects: dict, result: dict) -> tuple[bool, str]:
    """(pass 여부, 사유) 반환. 사유는 PASS든 FAIL이든 남긴다(로그용)."""
    kind = expects["kind"]
    listings = result.get("listings") or []
    clarify = result.get("clarify")
    tool_reason = _check_tools_expected(result, expects)

    if kind == "search":
        min_n = expects.get("min_listings", 1)
        if len(listings) < min_n:
            return False, f"listings {len(listings)}건 < min_listings {min_n}"
        if tool_reason:
            return False, tool_reason
        return True, f"listings {len(listings)}건"

    if kind == "reject":
        if len(listings) != 0:
            ids = [l.id for l in listings]
            return False, f"매물 무관 질의인데 listings {len(listings)}건 반환됨: {ids}"
        return True, "listings 0건(거절/무관 판단 유지)"

    if kind == "clarify_ok":
        if clarify is not None:
            chips = clarify.get("chips") if isinstance(clarify, dict) else None
            return True, f"clarify 채움(chips={chips})"
        if len(listings) >= 1:
            if tool_reason:
                return False, tool_reason
            return True, f"clarify 대신 실제 검색: listings {len(listings)}건"
        return False, "clarify도 없고 listings도 0건(막다른 응답)"

    if kind == "sorted_year_desc":
        min_n = expects.get("min_listings", 1)
        if len(listings) < min_n:
            return False, f"listings {len(listings)}건 < min_listings {min_n}"
        years = [l.year for l in listings]
        if any(years[i] < years[i + 1] for i in range(len(years) - 1)):
            return False, f"year 내림차순 아님: {years}"
        if tool_reason:
            return False, tool_reason
        return True, f"year 내림차순 확인: {years}"

    if kind == "guide":
        keywords = [k.lower() for k in expects.get("expected_keywords", [])]
        answer_low = (result.get("answer") or "").lower()
        hit = [k for k in keywords if k in answer_low]
        if not hit:
            return False, f"expected_keywords {keywords} 중 answer에 매칭 0개"
        if tool_reason:
            return False, tool_reason
        return True, f"키워드 매칭: {hit}"

    return False, f"알 수 없는 kind: {kind}"


def judge_multiturn(expects: dict, result1: dict, result2: dict) -> tuple[bool, str]:
    """(pass 여부, 사유) 반환 — 멀티턴 kind별 판정. result1=1턴(문맥 없음) 결과,
    result2=2턴(1턴 listings로 조립한 context 포함) 결과."""
    kind = expects["kind"]
    tools_used = set(result2.get("tools_used") or [])
    listings2 = result2.get("listings") or []

    if kind == "mt_market_diagnosis":
        if result2.get("market_diagnosis") is None:
            return False, "market_diagnosis가 None(시세 진단이 아니라 재검색/다른 응답으로 샌 것으로 의심)"
        if len(listings2) >= 2:
            return False, f"listings {len(listings2)}건 >= 2(단일 매물 시세 진단이 아니라 재추천으로 보임)"
        if "market_price_stats" not in tools_used:
            return False, f"tools_used에 market_price_stats 없음: {result2.get('tools_used')}"
        return True, f"market_diagnosis 확인 + listings {len(listings2)}건 + market_price_stats 호출됨"

    if kind == "mt_compare":
        if "compare_listings" not in tools_used:
            return False, f"tools_used에 compare_listings 없음: {result2.get('tools_used')}"
        return True, f"compare_listings 호출 확인(tools_used={result2.get('tools_used')})"

    if kind == "mt_no_resubject_diagnosis":
        # 단순화한 판정(코디네이터 지시) — search_listings로 새 조건 재검색을 하지 않았고
        # (직전 목록 밖으로 새 매물을 찾지 않았다는 증거), market_price_stats 호출 또는
        # clarify(대상 특정 되묻기) 중 하나로 "진단 의도"를 실제로 처리했는지만 본다.
        if "search_listings" in tools_used:
            return False, (
                f"search_listings 재검색 발생(새 조건으로 매물을 새로 찾은 것으로 의심): "
                f"tools_used={result2.get('tools_used')}"
            )
        handled = ("market_price_stats" in tools_used) or (result2.get("clarify") is not None)
        if not handled:
            return False, (
                f"market_price_stats도 clarify도 없음: tools_used={result2.get('tools_used')} "
                f"clarify={result2.get('clarify')}"
            )
        return True, (
            f"재검색 없음 + market_price_stats={'market_price_stats' in tools_used} "
            f"clarify_present={result2.get('clarify') is not None}"
        )

    if kind == "mt_market_stats_multi_call":
        # MT6(F2, 다건 판정 환각) — "이 매물들 전부 시세 분석해줘"는 매물마다 도구를 각각
        # 불러야 한다. set이 아니라 리스트로 세야 "1건만 부르고 텍스트로 나머지를 지어냈다"를
        # 잡을 수 있다(set이면 1회 호출과 여러 회 호출이 똑같이 "있음"으로만 보인다).
        tools_used_list = result2.get("tools_used") or []
        n_calls = tools_used_list.count("market_price_stats")
        if n_calls < 2:
            return False, (
                f"market_price_stats 호출 {n_calls}회 < 2회(다건 판정 환각 의심 — 호출 안 한 "
                f"매물의 저렴/높음을 텍스트로만 지어냈을 수 있음): tools_used={tools_used_list}"
            )
        return True, f"market_price_stats 호출 {n_calls}회 확인(매물마다 실제로 도구를 불렀음)"

    if kind == "mt_no_block_reclarify":
        # MT7(R1, "직전 목록 없는데 지시어" 재검색 도피 회귀) — 1턴이 매물 0건(되묻기)으로
        # 끝나 2턴에 [직전 대화에서 보여준 매물] 블록이 없는 상태다. 이때 가리킬 매물이
        # 아예 없으므로 search_listings·market_price_stats 둘 다 부르면 안 되고(존재하지
        # 않는 대상을 지어내는 것), clarify로 되물어야 한다.
        if "search_listings" in tools_used:
            return False, (
                f"직전 목록 없는데 search_listings 재검색 발생(엉뚱한 매물을 새로 찾은 것으로 "
                f"의심): tools_used={result2.get('tools_used')}"
            )
        if "market_price_stats" in tools_used:
            return False, (
                f"직전 목록 없는데 market_price_stats 호출됨(대상 없이 진단을 지어낸 것으로 "
                f"의심): tools_used={result2.get('tools_used')}"
            )
        if result2.get("clarify") is None:
            return False, "clarify 없음(대상이 불명확한데 되묻지 않음)"
        if listings2:
            return False, f"listings {len(listings2)}건(직전 목록이 없는데 매물이 반환됨)"
        return True, "재검색·진단 도구 미호출 + clarify 존재 + listings 0건 확인"

    return False, f"알 수 없는 kind: {kind}"


def judge_three_turn(expects: dict, result3: dict, turn1_listing_ids: list[str] | None = None) -> tuple[bool, str]:
    """(pass 여부, 사유) 반환 — 3턴 kind별 판정. result3가 판정 대상(1·2턴은 context 조립용
    재료)이지만, MT5는 "비교 대상이 1턴 목록 안에 있는가"를 보려면 turn1_listing_ids가 필요하다."""
    kind = expects["kind"]
    tools_used = set(result3.get("tools_used") or [])

    if kind == "mt4_second_listing_no_resubject":
        # MT3(mt_no_resubject_diagnosis)와 동일한 판정 사상 — 재검색으로 새지 않고, 진단
        # 또는 대상 특정 되묻기 중 하나로 실제 처리됐는지만 본다(3턴 확장판).
        if "search_listings" in tools_used:
            return False, (
                f"search_listings 재검색 발생(1턴 목록 밖으로 새 매물을 찾은 것으로 의심): "
                f"tools_used={result3.get('tools_used')}"
            )
        handled = ("market_price_stats" in tools_used) or (result3.get("clarify") is not None)
        if not handled:
            return False, (
                f"market_price_stats도 clarify도 없음: tools_used={result3.get('tools_used')} "
                f"clarify={result3.get('clarify')}"
            )
        return True, (
            f"재검색 없음 + market_price_stats={'market_price_stats' in tools_used} "
            f"clarify_present={result3.get('clarify') is not None}"
        )

    if kind == "mt5_no_resubject_compare_from_prior_list":
        # MT5(F1, "나머지 두 개랑 비교해줘" 재검색 도피 회귀) — 핵심 판정은 재검색 부재 +
        # compare_listings 호출. "비교 대상 id가 1턴 목록 안에 있는가"는 가능하면(compare
        # 결과가 최종 응답의 listings에 실제로 담겼을 때만) 추가로 확인한다 — 담기지 않아도
        # (도구는 불렀지만 최종화 LLM이 selected_listing_ids를 못 채운 경우) 핵심 판정은
        # 그대로 유효하므로 그 경우엔 이 서브체크를 건너뛴다(스펙의 "(가능하면)" 반영).
        if "search_listings" in tools_used:
            return False, (
                f"search_listings 재검색 발생(1턴 목록 밖에서 새 매물로 비교했을 것으로 의심): "
                f"tools_used={result3.get('tools_used')}"
            )
        if "compare_listings" not in tools_used:
            return False, f"tools_used에 compare_listings 없음: {result3.get('tools_used')}"
        compared_ids = [c.id for c in (result3.get("listings") or [])]
        if turn1_listing_ids and compared_ids:
            outside = [cid for cid in compared_ids if cid not in turn1_listing_ids]
            if outside:
                return False, (
                    f"compare 대상이 1턴 목록 밖: outside={outside} "
                    f"turn1_listing_ids={turn1_listing_ids} compared_ids={compared_ids}"
                )
        return True, (
            f"재검색 없음 + compare_listings 호출 확인 + compared_ids={compared_ids} "
            f"(turn1_listing_ids={turn1_listing_ids})"
        )

    return False, f"알 수 없는 kind: {kind}"


# ── 실행 ─────────────────────────────────────────────────────────────────────

def run_once() -> tuple[list[dict], float]:
    """QUERIES 전체를 문맥 없이(단발) 순차 실행. (결과 행 목록, 총 소요초) 반환."""
    rows: list[dict] = []
    t_start = time.time()
    for expects in QUERIES:
        qid, query = expects["id"], expects["query"]
        t0 = time.time()
        try:
            result = run_search_agent(query, context=None, listing_id=None)
            elapsed = time.time() - t0
            ok, reason = judge(expects, result)
            rows.append({
                "id": qid, "query": query, "kind": expects["kind"],
                "pass": ok, "reason": reason, "elapsed": elapsed,
                "tools_used": result.get("tools_used"),
                "n_listings": len(result.get("listings") or []),
                "answer": result.get("answer"),
                "clarify": result.get("clarify"),
            })
        except Exception as exc:  # 도구/LLM 예외도 FAIL로 집계(회귀일 수 있으니 죽이지 않는다)
            elapsed = time.time() - t0
            rows.append({
                "id": qid, "query": query, "kind": expects["kind"],
                "pass": False, "reason": f"예외 발생: {exc!r}", "elapsed": elapsed,
                "tools_used": None, "n_listings": None, "answer": None, "clarify": None,
            })
        status = "PASS" if rows[-1]["pass"] else "FAIL"
        print(f"[{status}] {qid:22s} ({rows[-1]['elapsed']:5.1f}s) {rows[-1]['reason']}")
    total = time.time() - t_start
    return rows, total


def run_multiturn_once() -> tuple[list[dict], float]:
    """MULTITURN_CASES 전체를 실행한다. 1턴은 문맥 없이(run_once와 동일) 실제로 실행하고,
    그 결과의 listings id로 어시스턴트 턴(listing_ids 포함)을 조립해 2턴 context로 넘긴다 —
    웹 buildContext(ChatAssistant.tsx)가 실제로 만드는 형태를 그대로 재현한다(듀ck 타이핑
    dict — agent.py의 contextualize_node·_recent_assistant_listing_ids가 dict/Pydantic
    둘 다 받아들이므로 여기선 dict로 충분하다)."""
    rows: list[dict] = []
    t_start = time.time()
    for case in MULTITURN_CASES:
        qid, turn1_query, turn2_query = case["id"], case["turn1"], case["turn2"]
        t0 = time.time()
        try:
            result1 = run_search_agent(turn1_query, context=None, listing_id=None)
            listing_ids1 = [c.id for c in (result1.get("listings") or [])]
            context = [
                {"role": "user", "content": turn1_query},
                {"role": "assistant", "content": result1.get("answer") or "", "listing_ids": listing_ids1},
            ]
            result2 = run_search_agent(turn2_query, context=context, listing_id=None)
            elapsed = time.time() - t0
            ok, reason = judge_multiturn(case, result1, result2)
            rows.append({
                "id": qid, "query": f"{turn1_query!r} → {turn2_query!r}", "kind": case["kind"],
                "pass": ok, "reason": reason, "elapsed": elapsed,
                "tools_used": result2.get("tools_used"),
                "n_listings": len(result2.get("listings") or []),
                "answer": result2.get("answer"),
                "clarify": result2.get("clarify"),
                "turn1_listing_ids": listing_ids1,
            })
        except Exception as exc:  # 도구/LLM 예외도 FAIL로 집계(회귀일 수 있으니 죽이지 않는다)
            elapsed = time.time() - t0
            rows.append({
                "id": qid, "query": f"{turn1_query!r} → {turn2_query!r}", "kind": case["kind"],
                "pass": False, "reason": f"예외 발생: {exc!r}", "elapsed": elapsed,
                "tools_used": None, "n_listings": None, "answer": None, "clarify": None,
                "turn1_listing_ids": None,
            })
        status = "PASS" if rows[-1]["pass"] else "FAIL"
        print(f"[{status}] {qid:22s} ({rows[-1]['elapsed']:5.1f}s) {rows[-1]['reason']}")
    total = time.time() - t_start
    return rows, total


def run_three_turn_once() -> tuple[list[dict], float]:
    """THREE_TURN_CASES 전체를 실행한다. 1·2턴을 실제로 순차 실행하고, 각 턴의 assistant
    listing_ids를 _client_listing_ids(웹 listingIdsOf와 동일 규칙)로 뽑아 다음 턴 context에
    누적해 싣는다 — 3턴째에 1턴 목록까지 살아 있어야 하는 P1 시나리오를 그대로 재현한다."""
    rows: list[dict] = []
    t_start = time.time()
    for case in THREE_TURN_CASES:
        qid, turn1_query, turn2_query, turn3_query = case["id"], case["turn1"], case["turn2"], case["turn3"]
        t0 = time.time()
        try:
            result1 = run_search_agent(turn1_query, context=None, listing_id=None)
            ids1 = _client_listing_ids(result1)
            context = [{"role": "user", "content": turn1_query}]
            turn1_assistant = {"role": "assistant", "content": result1.get("answer") or ""}
            if ids1:
                turn1_assistant["listing_ids"] = ids1
            context.append(turn1_assistant)

            result2 = run_search_agent(turn2_query, context=context, listing_id=None)
            ids2 = _client_listing_ids(result2)
            context.append({"role": "user", "content": turn2_query})
            turn2_assistant = {"role": "assistant", "content": result2.get("answer") or ""}
            if ids2:
                turn2_assistant["listing_ids"] = ids2
            context.append(turn2_assistant)

            result3 = run_search_agent(turn3_query, context=context, listing_id=None)
            elapsed = time.time() - t0
            ok, reason = judge_three_turn(case, result3, turn1_listing_ids=ids1)
            rows.append({
                "id": qid, "query": f"{turn1_query!r} → {turn2_query!r} → {turn3_query!r}",
                "kind": case["kind"],
                "pass": ok, "reason": reason, "elapsed": elapsed,
                "tools_used": result3.get("tools_used"),
                "n_listings": len(result3.get("listings") or []),
                "answer": result3.get("answer"),
                "clarify": result3.get("clarify"),
                "turn1_listing_ids": ids1,
                "turn2_listing_ids": ids2,
            })
        except Exception as exc:  # 도구/LLM 예외도 FAIL로 집계(회귀일 수 있으니 죽이지 않는다)
            elapsed = time.time() - t0
            rows.append({
                "id": qid, "query": f"{turn1_query!r} → {turn2_query!r} → {turn3_query!r}",
                "kind": case["kind"],
                "pass": False, "reason": f"예외 발생: {exc!r}", "elapsed": elapsed,
                "tools_used": None, "n_listings": None, "answer": None, "clarify": None,
                "turn1_listing_ids": None, "turn2_listing_ids": None,
            })
        status = "PASS" if rows[-1]["pass"] else "FAIL"
        print(f"[{status}] {qid:22s} ({rows[-1]['elapsed']:5.1f}s) {rows[-1]['reason']}")
    total = time.time() - t_start
    return rows, total


def print_table(rows: list[dict], total: float) -> None:
    print("\n" + "=" * 100)
    print(f"{'id':22s} {'kind':16s} {'결과':6s} {'소요':>6s}  사유")
    print("-" * 100)
    n_pass = 0
    for r in rows:
        status = "PASS" if r["pass"] else "FAIL"
        n_pass += r["pass"]
        print(f"{r['id']:22s} {r['kind']:16s} {status:6s} {r['elapsed']:5.1f}s  {r['reason']}")
    print("-" * 100)
    print(f"총 {len(rows)}건 중 {n_pass} PASS / {len(rows) - n_pass} FAIL — 소요 {total:.1f}s")
    print("=" * 100)


def main() -> int:
    rows, total = run_once()
    print("\n--- 멀티턴 케이스 ---")
    mt_rows, mt_total = run_multiturn_once()
    print("\n--- 3턴 케이스 ---")
    mt3_rows, mt3_total = run_three_turn_once()
    all_rows = rows + mt_rows + mt3_rows
    print_table(all_rows, total + mt_total + mt3_total)
    failed = [r for r in all_rows if not r["pass"]]
    if failed:
        print("\nFAIL 상세:")
        for r in failed:
            print(f"\n--- {r['id']} ({r['query']!r}) ---")
            print(f"  사유: {r['reason']}")
            print(f"  tools_used: {r['tools_used']}")
            print(f"  n_listings: {r['n_listings']}")
            print(f"  clarify: {r['clarify']}")
            print(f"  answer: {r['answer']}")
            if "turn1_listing_ids" in r:
                print(f"  turn1_listing_ids: {r['turn1_listing_ids']}")
            if "turn2_listing_ids" in r:
                print(f"  turn2_listing_ids: {r['turn2_listing_ids']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
