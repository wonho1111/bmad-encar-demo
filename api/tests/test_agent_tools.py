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
    # 정규화(공백제거+양방향 부분일치) SQL 형태 — unnest 교차조인 + replace(...,' ','') ILIKE.
    assert "unnest(options)" in captured["sql"]
    assert "unnest(%s::text[])" in captured["sql"]
    assert "replace(o, ' ', '')" in captured["sql"]
    # 실제 값은 파라미터 배열로만 전달된다(바인딩) — 공백은 이미 제거된 채로 바인딩.
    assert ["스마트키", "통풍시트"] in captured["params"]


def test_search_listings_options_any_normalizes_spacing(monkeypatch):
    """LLM이 띄어쓰기 풀네임("어댑티브 크루즈 컨트롤")을 넣어도 파라미터는 공백이 제거된
    채로 바인딩된다 — DB 실존 문자열("어댑티브크루즈")과 정규화 비교되도록(실측 결함 #2)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc",
        options_any=["어댑티브 크루즈 컨트롤", "스마트 크루즈 컨트롤"],
    )
    assert ["어댑티브크루즈컨트롤", "스마트크루즈컨트롤"] in captured["params"]


def test_search_listings_options_any_strips_wildcard_chars(monkeypatch):
    """요청 옵션 문자열에 %·_가 섞여 있으면 ILIKE 와일드카드로 오염되지 않게 제거된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", options_any=["스마트%키_"],
    )
    assert ["스마트키"] in captured["params"]


def test_search_listings_options_any_blank_after_sanitize_skips_clause(monkeypatch):
    """정규화 후 남는 게 없으면(전부 공백·와일드카드였으면) 필터절 자체를 넣지 않는다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", options_any=["  ", "%%"])
    assert "unnest(options)" not in captured["sql"]


# ───────── (1b) search_listings — model_keyword 정규화(실측 결함 #1) ─────────

def test_search_listings_model_keyword_manufacturer_and_body_type_relocated(monkeypatch):
    """model_keyword="현대 SUV" → manufacturer='현대' AND body_type='SUV'로 옮겨지고,
    model 필터(ILIKE)는 아예 생략된다(예전엔 model ILIKE '%현대 SUV%' = 0건으로 샜음)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", model_keyword="현대 SUV", mileage_max=30000,
    )
    assert "manufacturer = %s" in captured["sql"]
    assert "body_type = %s" in captured["sql"]
    assert "model ILIKE %s" not in captured["sql"]
    assert "현대" in captured["params"]
    assert "SUV" in captured["params"]


def test_search_listings_model_keyword_keeps_remaining_token_as_model_filter(monkeypatch):
    """model_keyword="기아 쏘렌토" → manufacturer='기아'로 옮기고, 남은 토큰 "쏘렌토"는
    그대로 model ILIKE 필터로 남는다(제조사만 뽑아내고 진짜 모델명은 보존)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", model_keyword="기아 쏘렌토",
    )
    assert "manufacturer = %s" in captured["sql"]
    assert "model ILIKE %s" in captured["sql"]
    assert "기아" in captured["params"]
    assert "%쏘렌토%" in captured["params"]


def test_search_listings_model_keyword_does_not_overwrite_explicit_manufacturer(monkeypatch):
    """manufacturer 인자가 이미 채워져 있으면 model_keyword 안의 같은 토큰은 값을 덮지
    않고 그냥 제거만 된다(중복 입력 방어)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", manufacturer="기아", model_keyword="현대 쏘렌토",
    )
    # manufacturer는 명시값("기아")이 유지되고, "현대" 토큰은 버려진다(기아로 안 바뀜, 현대도 안 남음).
    assert captured["params"].count("기아") == 1
    assert "현대" not in captured["params"]


def test_search_listings_model_keyword_plain_model_unaffected(monkeypatch):
    """화이트리스트에 없는 순수 모델명은 그대로 model 필터로 간다(회귀 방지)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", model_keyword="아반떼")
    assert "model ILIKE %s" in captured["sql"]
    assert "%아반떼%" in captured["params"]


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


def test_search_listings_prioritizes_exact_model_match_when_similarity_sort(monkeypatch):
    # D(2026-08-31, 실측 P4 연장): model_keyword가 있으면 유사도 정렬보다 "정확 세대 일치"가
    # 먼저 온다 — "그랜저 IG"로 검색하면 부분일치("더 뉴 그랜저 IG")보다 정확히 "그랜저 IG"인
    # 매물이 먼저 나와야 세대 혼동이 없다.
    captured = {}
    monkeypatch.setattr(agent_tools, "embed_query", lambda q: [0.1, 0.2, 0.3])
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: (
        captured.update(sql=sql, params=params), [_fake_row()]
    )[1])
    agent_tools.search_listings.func(query_text="그랜저 IG 보여줘", model_keyword="그랜저 IG")
    assert "ORDER BY (model = %s) DESC, embedding <=> %s::vector" in captured["sql"]
    # 파라미터 순서: WHERE절 바인딩(model ILIKE 포함) → 정확일치 보조값 → 벡터 → limit.
    assert captured["params"][-3] == "그랜저 IG"  # 정확일치 보조 파라미터


def test_search_listings_explicit_sort_by_not_affected_by_exact_match_boost(monkeypatch):
    # sort_by가 명시되면(예: price_asc) 그 정렬을 그대로 존중한다 — 정확일치 보조는 유사도
    # 정렬(sort_by 생략/similarity)일 때만 끼어든다(판단 근거: 사용자가 가격·연식순을 명시
    # 요구했는데 세대 일치가 그 순서를 덮어쓰면 의도를 배신한다).
    captured = {}
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: (
        captured.update(sql=sql, params=params), [_fake_row()]
    )[1])
    agent_tools.search_listings.func(query_text="아무거나", model_keyword="그랜저 IG", sort_by="price_asc")
    assert "model = %s) DESC" not in captured["sql"]
    assert "ORDER BY price ASC" in captured["sql"]


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


def test_invalid_body_type_raises_with_allowed_values():
    """LLM이 지어낸 축값(회귀 실측 H26: body_type='세단')은 조용한 0건 대신 허용 목록을
    담은 에러로 되돌려 모델이 재시도하게 한다."""
    import pytest
    from app.graph import agent_tools

    with pytest.raises(ValueError) as exc:
        agent_tools.search_listings.invoke(
            {"body_type": "세단", "query_text": "중형 세단"}
        )
    msg = str(exc.value)
    assert "세단" in msg and "중형차" in msg  # 잘못된 값 + 허용 안내 동시 포함


def test_invalid_fuel_raises_with_allowed_values():
    import pytest
    from app.graph import agent_tools

    with pytest.raises(ValueError) as exc:
        agent_tools.search_listings.invoke(
            {"fuel": "가솔린+전기", "query_text": "하이브리드"}
        )
    assert "하이브리드" in str(exc.value)
