"""agent_tools 단위 테스트 — 네트워크(LLM)·DB 무관, 조립·화이트리스트·바인딩만 검증(4단계 부품 B).

실제 실행(라이브 LLM+DB)은 4단계 부품 B 작업 보고의 실측 3질의(api/.venv, run_search_agent)로
확인한다. 여기서는 결정론적인 부분만 격리한다:
  (1) search_listings — sort_by 화이트리스트 밖 값 거부, limit 20 상한 강제,
      options_any가 SQL 문자열에 직접 삽입되지 않고 파라미터로만 바인딩되는지
  (2) search_guides — app.rerank_client.rerank가 None이면 원래 순서를 유지하는 폴백,
      값을 주면 그 순서로 재정렬되는지
  (3) market_price_stats — app.market_price.diagnose를 readonly_connection 트랜잭션 안에서
      호출하고, 결과 dict를 artifact로 그대로 돌려주는지(없으면 None)
  (4) compare_listings — 4건 초과 입력을 앞의 4건으로 자르는지

.func는 langchain @tool 데코레이터가 감싸기 전의 원본 파이썬 함수를 가리킨다(StructuredTool의
공개 속성) — pydantic 스키마 검증(Literal 등)을 거치지 않고 우리 코드의 자체 방어(화이트리스트
재검사)를 직접 때려본다.
"""

import contextlib

import app.graph.agent_tools as agent_tools
from app.schemas.ai import ListingCard

_LISTING_ID = "55555555-5555-4555-8555-555555555555"


def _fake_row():
    return (
        _LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원",
        "가솔린", None, None, None, ["선루프"],
    )


# ───────── (1) search_listings ─────────

def test_search_listings_rejects_sort_by_outside_whitelist():
    try:
        agent_tools.search_listings.func(query_text="아무거나", sort_by="year_asc")
    except ValueError as exc:
        assert "year_asc" in str(exc)
    else:
        raise AssertionError("화이트리스트 밖 sort_by가 거부되지 않았다")


def test_search_listings_caps_limit_to_20(monkeypatch):
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    # sort_by="price_asc"로 정렬 분기를 타 embed_query(임베딩 API) 호출 없이 결정론적으로 돈다.
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", limit=999)
    assert captured["params"][-1] == 20  # _MAX_SEARCH_LIMIT(20)으로 강제 보정.


def test_search_listings_options_any_binds_as_param_not_interpolated(monkeypatch):
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", options_any=["스마트키", "통풍시트"],
    )
    # SQL 문자열에는 값이 직접 삽입되지 않고 자리표시자(%s)만 남는다.
    assert "스마트키" not in captured["sql"]
    assert "options && %s::text[]" in captured["sql"]
    # 실제 값은 파라미터 튜플로만 전달된다(바인딩).
    assert ["스마트키", "통풍시트"] in captured["params"]


def test_search_listings_returns_formatted_summary_and_cards(monkeypatch):
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: [_fake_row()])
    text, listings = agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc")
    assert isinstance(listings, list) and len(listings) == 1
    assert isinstance(listings[0], ListingCard)
    assert _LISTING_ID in text
    assert "싼타페" in text


def test_search_listings_similarity_sort_calls_embed_query(monkeypatch):
    # sort_by 생략(기본 similarity) → embed_query가 호출되고 벡터절이 SQL에 붙는다.
    captured = {}
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1, 0.2, 0.3])
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: (
        captured.update(sql=sql, params=params), [_fake_row()]
    )[1])
    agent_tools.search_listings.func(query_text="쏘렌토 같은 SUV")
    assert "ORDER BY embedding <=> %s::vector" in captured["sql"]


# ───────── (2) search_guides ─────────

_GUIDE_A = ("패밀리카 가이드", "본문 A")
_GUIDE_B = ("출퇴근용 가이드", "본문 B")


def test_search_guides_no_reranker_keeps_original_order(monkeypatch):
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(
        agent_tools, "find_relevant_guides_fused", lambda q, qvec: [_GUIDE_A, _GUIDE_B]
    )
    monkeypatch.setattr(agent_tools, "rerank", None)  # 사이드카 없음/미설정 취급.
    text = agent_tools.search_guides.func(query_text="가족용 SUV 추천")
    # 원래 순서(A가 먼저) 그대로 나온다.
    assert text.index("패밀리카 가이드") < text.index("출퇴근용 가이드")


def test_search_guides_reranker_reorders_when_available(monkeypatch):
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(
        agent_tools, "find_relevant_guides_fused", lambda q, qvec: [_GUIDE_A, _GUIDE_B]
    )
    # 리랭커가 [1, 0] 순서(B가 먼저)를 돌려주면 그 순서로 재정렬돼야 한다.
    monkeypatch.setattr(agent_tools, "rerank", lambda query, docs: [1, 0])
    text = agent_tools.search_guides.func(query_text="가족용 SUV 추천")
    assert text.index("출퇴근용 가이드") < text.index("패밀리카 가이드")


def test_search_guides_no_guides_found(monkeypatch):
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(agent_tools, "find_relevant_guides_fused", lambda q, qvec: [])
    text = agent_tools.search_guides.func(query_text="아무거나")
    assert "찾지 못했습니다" in text


# ───────── (3) market_price_stats ─────────

@contextlib.contextmanager
def _fake_readonly_connection():
    yield object()


def test_market_price_stats_returns_diagnosis_dict_as_artifact(monkeypatch):
    fake_result = {
        "listing": {"manufacturer": "기아", "model": "쏘렌토", "year": 2021, "price": 28000000},
        "criteria": {"step": 0, "desc": "동일 세대", "sample_count": 6},
        "stats": {"min": 25000000, "q1": 26000000, "median": 27000000, "q3": 29000000, "max": 31000000},
        "percentile": 0.4,
        "verdict": "적정",
        "tabpfn": {"price": 27500000, "note": "TabPFN 예측"},
        "comps": [],
    }
    monkeypatch.setattr(agent_tools, "readonly_connection", _fake_readonly_connection)
    monkeypatch.setattr(agent_tools, "diagnose", lambda listing_id, conn: fake_result)
    text, artifact = agent_tools.market_price_stats.func(listing_id=_LISTING_ID)
    assert artifact == fake_result
    assert "적정" in text
    assert "쏘렌토" in text


def test_market_price_stats_not_found_returns_none_artifact(monkeypatch):
    monkeypatch.setattr(agent_tools, "readonly_connection", _fake_readonly_connection)
    monkeypatch.setattr(agent_tools, "diagnose", lambda listing_id, conn: None)
    text, artifact = agent_tools.market_price_stats.func(listing_id="없는-id")
    assert artifact is None
    assert "찾을 수 없습니다" in text


# ───────── (4) compare_listings ─────────

def test_compare_listings_caps_to_four_ids(monkeypatch):
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return []

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    ids = [f"id-{i}" for i in range(6)]
    agent_tools.compare_listings.func(listing_ids=ids)
    assert captured["params"][0] == ids[:4]


def test_compare_listings_empty_ids_skips_query(monkeypatch):
    def fake_run_select(sql, params=None):
        raise AssertionError("빈 id 목록이면 DB를 조회하면 안 된다")

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    text, listings = agent_tools.compare_listings.func(listing_ids=[])
    assert listings == []
    assert "없습니다" in text
