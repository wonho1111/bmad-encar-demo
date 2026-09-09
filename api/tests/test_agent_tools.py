"""agent_tools 단위 테스트 — 네트워크(LLM)·DB 무관, 조립·화이트리스트·바인딩만 검증(4단계 부품 B).

실제 실행(라이브 LLM+DB)은 4단계 부품 B 작업 보고의 실측 3질의(api/.venv, run_search_agent)로
확인한다. 여기서는 결정론적인 부분만 격리한다:
  (1) search_listings — sort_by 화이트리스트 밖 값 거부, limit 20 상한 강제,
      options_required가 SQL 문자열에 직접 삽입되지 않고 파라미터로만 바인딩되는지(AND 의미 —
      옵션마다 독립된 EXISTS 절+배열 파라미터)
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
    # 13번째 값(color)은 DW-872 — search_listings 전용 SELECT는 공용 SELECT_COLUMNS(12열)
    # 뒤에 color 1열을 덧붙인다(_SEARCH_SELECT_COLUMNS). compare_listings는 그대로 12열이라
    # 이 헬퍼를 쓰지 않는다(compare_listings 테스트는 자체 데이터로 검증).
    return (
        _LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원",
        "가솔린", None, None, None, ["선루프"], "흰색",
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


def test_search_listings_options_required_are_and_combined(monkeypatch):
    """수정(2026-09-01): 옵션 여러 개는 AND 의미다 — 옵션마다 독립된 EXISTS 절 + 독립된
    파라미터 배열이 SQL에 쌓인다(전체는 " AND "로 결합). 실측 결함: 예전 OR(options_any)
    의미로는 "통풍시트 그리고 스마트크루즈"를 나열해도 크루즈만 있는 매물이 통과했다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", options_required=["스마트키", "통풍시트"],
    )
    # SQL 문자열에는 값이 직접 삽입되지 않고 자리표시자(%s)만 남는다.
    assert "스마트키" not in captured["sql"]
    # 옵션 2개 → EXISTS 절 2개(리터럴 기대) — AND 결합.
    assert captured["sql"].count("EXISTS (SELECT 1 FROM unnest(options)") == 2
    assert "unnest(%s::text[])" in captured["sql"]
    assert "replace(o, ' ', '')" in captured["sql"]
    # 실제 값은 옵션마다 독립된 파라미터 배열로 전달된다(하나로 합쳐지지 않는다 — OR 시절과의 차이).
    option_arrays = [p for p in captured["params"] if isinstance(p, list)]
    assert len(option_arrays) == 2
    assert option_arrays[0] == ["스마트키"]
    assert option_arrays[1] == ["통풍시트"]


def test_search_listings_options_required_normalizes_spacing_and_expands_synonyms_per_option(monkeypatch):
    """LLM이 띄어쓰기 풀네임("어댑티브 크루즈 컨트롤")을 넣어도 파라미터는 공백이 제거된
    채로 바인딩되고(DB 실존 문자열과 정규화 비교, 실측 결함 #2), 동의어 계열도 함께
    확장된다(2026-09-01). 옵션이 여러 개일 땐 각자 자기 배열로만 확장된다 — "통풍시트"
    배열에 크루즈 동의어가 섞이지 않는다(옵션 단위 격리, AND 의미 유지에 필수)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc",
        options_required=["통풍시트", "어댑티브 크루즈 컨트롤"],
    )
    option_arrays = [p for p in captured["params"] if isinstance(p, list)]
    assert len(option_arrays) == 2
    ventilated_array, cruise_array = option_arrays[0], option_arrays[1]
    # 통풍시트는 동의어 그룹이 없어 자기 자신만 담긴다 — 크루즈 동의어가 섞이지 않는다.
    assert ventilated_array == ["통풍시트"]
    # 크루즈 쪽은 공백 정규화 + 동의어 계열 확장이 함께 일어난다.
    sent = set(cruise_array)
    assert "어댑티브크루즈컨트롤" in sent  # 정규화 유지
    assert {"어댑티브크루즈", "스마트크루즈", "크루즈컨트롤"} <= sent  # 동의어 확장
    assert "통풍시트" not in sent  # 격리 확인


def test_search_listings_options_required_strips_wildcard_chars(monkeypatch):
    """요청 옵션 문자열에 %·_가 섞여 있으면 ILIKE 와일드카드로 오염되지 않게 제거된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", options_required=["스마트%키_"],
    )
    assert ["스마트키"] in captured["params"]


def test_search_listings_options_required_blank_after_sanitize_skips_clause(monkeypatch):
    """정규화 후 남는 게 없는 옵션(전부 공백·와일드카드였으면)은 그 옵션의 EXISTS 절만
    빠지고, 나머지 옵션은 그대로 AND 조건에 남는다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", options_required=["  ", "%%"],
    )
    assert "unnest(options)" not in captured["sql"]


def test_search_listings_single_owner_only_filters_is_single_owner(monkeypatch):
    """single_owner_only=True면 is_single_owner IS TRUE 조건이 SQL에 걸린다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", single_owner_only=True,
    )
    assert "is_single_owner IS TRUE" in captured["sql"]


def test_search_listings_non_smoker_only_filters_is_non_smoker(monkeypatch):
    """non_smoker_only=True면 is_non_smoker IS TRUE 조건이 SQL에 걸린다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", non_smoker_only=True,
    )
    assert "is_non_smoker IS TRUE" in captured["sql"]


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


# ───────── (1c) 지역·색상 인자, 제조사 별칭, 예산 단위 방어, 0건 안내(DW-865/867/868) ─────────

def test_search_listings_manufacturer_alias_ssangyong_maps_to_kg_mobility(monkeypatch):
    """DW-868 — LLM이 옛 상호 "쌍용"을 그대로 넣어도 DB 실제 값 "KG모빌리티"로 정규화된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", manufacturer="쌍용")
    assert "KG모빌리티" in captured["params"]
    assert "쌍용" not in captured["params"]


def test_search_listings_region_alias_reaches_sql(monkeypatch):
    """DW-865/867 — region 인자가 SQL의 region = %s 절로 걸리고, "경기도" 같은 흔한 별칭은
    CHECK 허용값 "경기"로 정규화된 채 파라미터에 바인딩된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", region="경기도")
    assert "region = %s" in captured["sql"]
    assert "경기" in captured["params"]
    assert "경기도" not in captured["params"]


def test_search_listings_color_alias_reaches_sql(monkeypatch):
    """color 인자가 SQL의 color = %s 절로 걸리고, "검정색" 같은 별칭은 "검정"으로 정규화된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", color="검정색")
    assert "color = %s" in captured["sql"]
    assert "검정" in captured["params"]
    assert "검정색" not in captured["params"]


# ───────── (1c-2) body_type 별칭·복수값, models, seats_min, 사고/색상/지역 표기, 르노 별칭(DW-872) ─────────

def test_search_listings_body_type_sedan_alias_expands_to_any_three_values(monkeypatch):
    """'세단'은 DB CHECK 어휘에 없는 상위개념이라 준중형차/중형차/대형차 3개로 펼쳐지고,
    값이 여러 개라 SQL은 '=' 대신 ANY로 바뀐다(DW-872 — 이전엔 ValueError였다, C06·C48)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="세단 보여줘", sort_by="price_asc", body_type="세단")
    assert "body_type = ANY(%s)" in captured["sql"]
    assert "body_type = %s" not in captured["sql"]
    body_type_param = next(p for p in captured["params"] if isinstance(p, list) and "중형차" in p)
    assert body_type_param == ["준중형차", "중형차", "대형차"]


def test_search_listings_body_type_sedan_alias_still_expands_with_different_spelling(monkeypatch):
    """red 증명을 표기 하나로만 우려내지 않기 위해, 브리프가 준 예시와 다른 표기(공백 포함)로
    한 번 더 확인한다 — 공백 정규화 후에도 같은 별칭으로 잡혀야 한다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="세단 보여줘", sort_by="price_asc", body_type=" 세단 ")
    assert "body_type = ANY(%s)" in captured["sql"]
    body_type_param = next(p for p in captured["params"] if isinstance(p, list) and "중형차" in p)
    assert body_type_param == ["준중형차", "중형차", "대형차"]


def test_search_listings_body_type_jun_jung_hyung_alias_maps_to_single_value(monkeypatch):
    """'준중형'은 화이트리스트 값 '준중형차' 1개로만 풀려 기존과 동일한 단일 절(=)을 쓴다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="준중형 보여줘", sort_by="price_asc", body_type="준중형")
    assert "body_type = %s" in captured["sql"]
    assert "body_type = ANY(%s)" not in captured["sql"]
    assert "준중형차" in captured["params"]
    assert "준중형" not in captured["params"]


def test_search_listings_body_type_medium_suv_alias_maps_to_suv(monkeypatch):
    """'중형 SUV'는 DB 어휘에 크기 구분이 없어 'SUV' 하나로 뭉개진다 — 조용히 축소하지
    않고 그 사실을 결과 텍스트(applied_desc)에 남긴다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    text, _ = agent_tools.search_listings.func(
        query_text="중형 SUV 보여줘", sort_by="price_asc", body_type="중형 SUV",
    )
    assert "body_type = %s" in captured["sql"]
    assert "SUV" in captured["params"]
    assert "크기 구분 없음" in text


def test_search_listings_models_list_creates_or_clause(monkeypatch):
    """models=["K3","아반떼"] → model ILIKE 절 2개가 OR로 묶인다(DW-872, "K3 아니면 아반떼")."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="K3 아니면 아반떼", sort_by="price_asc", models=["K3", "아반떼"],
    )
    assert captured["sql"].count("model ILIKE %s") == 2
    assert "(model ILIKE %s OR model ILIKE %s)" in captured["sql"]
    assert "%K3%" in captured["params"]
    assert "%아반떼%" in captured["params"]


def test_search_listings_models_combines_with_model_keyword_as_or(monkeypatch):
    """model_keyword와 models가 함께 오면 합집합(OR)이다 — 셋 다 하나의 OR 절에 들어간다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(
        query_text="투싼이나 스포티지", sort_by="price_asc",
        model_keyword="투싼", models=["스포티지"],
    )
    assert captured["sql"].count("model ILIKE %s") == 2
    assert "%투싼%" in captured["params"]
    assert "%스포티지%" in captured["params"]


def test_search_listings_seats_min_filters_seats_gte(monkeypatch):
    """'7인승 이상' → seats_min=7 → SQL은 seats >= %s, 파라미터는 7."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="7인승 이상", sort_by="price_asc", seats_min=7)
    assert "seats >= %s" in captured["sql"]
    assert 7 in captured["params"]


def test_search_listings_manufacturer_alias_renault_maps_to_renault_korea(monkeypatch):
    """'르노' 단독 별칭 누락(DW-872 근거) — manufacturer='르노'가 '르노코리아'로 정규화된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="르노 매물", sort_by="price_asc", manufacturer="르노")
    assert "르노코리아" in captured["params"]
    assert "르노" not in captured["params"]


def test_search_listings_summary_line_includes_accident_color_region(monkeypatch):
    """검색 결과 줄에 사고·색상·지역이 보여야 후속 질문("그중 무사고만")을 재검색 없이
    목록만으로 거를 수 있다(DW-872 근거 C50 — 재검색 차단 후 지어내던 문제)."""
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: [_fake_row()])
    text, _ = agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc")
    assert "사고=미상" in text  # _fake_row()의 accident_status는 None
    assert "색상=흰색" in text
    assert "지역=강원" in text


def test_search_listings_unknown_region_is_dropped_and_noted_in_text(monkeypatch):
    """모르는 지역 값은 필터에서 빠지고(SQL에 region 절이 안 걸림), 그 사실이 tool 텍스트에
    남아 LLM이 "조건 충족"이라 오독하지 못하게 한다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    text, _ = agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", region="화성시")
    assert "region = %s" not in captured["sql"]
    assert "화성시" not in captured["params"]
    assert "지역 '화성시'는 인식되지 않아 필터에서 제외" in text


def test_search_listings_price_max_unit_guard_converts_man_won(monkeypatch):
    """DW-868 — price_max=1500(만원 단위로 보이는 값)은 15,000,000원으로 변환된다."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", price_max=1500)
    assert 15_000_000 in captured["params"]
    assert 1500 not in captured["params"]


def test_search_listings_price_min_unit_guard_converts_man_won(monkeypatch):
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", price_min=2000)
    assert 20_000_000 in captured["params"]
    assert 2000 not in captured["params"]


def test_search_listings_price_max_already_won_is_unchanged(monkeypatch):
    """이미 원 단위인 값(15,000,000)은 변환되지 않는다 — 자릿수를 오해해 15,000,000,000으로
    부풀리면 안 된다(회귀 방지)."""
    captured = {}

    def fake_run_select(sql, params=None):
        captured["params"] = params
        return [_fake_row()]

    monkeypatch.setattr(agent_tools, "run_select", fake_run_select)
    agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc", price_max=15_000_000)
    assert 15_000_000 in captured["params"]


def test_search_listings_zero_results_lists_applied_filters(monkeypatch):
    """DW-865 — 0건이면 "조건에 맞는 매물이 없습니다"에 실제 적용된 필터를 나열해, LLM이
    다른 지역·가격대 매물을 조건 충족이라고 우기지 못하게 한다."""
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: [])
    text, listings = agent_tools.search_listings.func(
        query_text="아무거나", sort_by="price_asc", region="서울", price_max=15_000_000,
    )
    assert listings == []
    assert text == "조건에 맞는 매물이 없습니다 (적용 조건: 지역=서울, 가격≤15,000,000원)"


def test_search_listings_zero_results_without_filters_uses_bare_message(monkeypatch):
    """필터가 하나도 없으면(회귀 방지) 기존과 동일한 짧은 문구를 그대로 쓴다."""
    monkeypatch.setattr(agent_tools, "run_select", lambda sql, params=None: [])
    text, listings = agent_tools.search_listings.func(query_text="아무거나", sort_by="price_asc")
    assert listings == []
    assert text == "조건에 맞는 매물이 없습니다."


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


def _fake_diagnosis(sample_count: int) -> dict:
    return {
        "listing": {"manufacturer": "기아", "model": "쏘렌토", "year": 2021, "price": 28000000},
        "criteria": {"step": 0, "desc": "동일 세대", "sample_count": sample_count},
        "stats": {"min": 25000000, "q1": 26000000, "median": 27000000, "q3": 29000000, "max": 31000000},
        "percentile": 0.4,
        "verdict": "적정",
        "tabpfn": {"price": 27500000, "note": "TabPFN 예측"},
        "comps": [],
    }


def test_format_market_diagnosis_adds_caveat_when_sample_count_below_three():
    """DW-869 — 비교군이 3건 미만이면 기존 숫자 서술은 그대로 두고 표본 부족 주의 문구가
    덧붙는다(엔진 자체는 3건 미만이면 판정을 보류하는데, LLM이 숫자만 보고 단정하는 걸 막는다)."""
    from app.graph.agent_tools import _format_market_diagnosis

    text = _format_market_diagnosis(_fake_diagnosis(sample_count=2))
    assert "비교군 2건" in text  # 기존 숫자 서술 유지
    assert "⚠ 비교군 2건 — 표본이 적어 참고만 하세요(판정 보류)" in text


def test_format_market_diagnosis_no_caveat_when_sample_count_sufficient():
    from app.graph.agent_tools import _format_market_diagnosis

    text = _format_market_diagnosis(_fake_diagnosis(sample_count=6))
    assert "표본이 적어 참고만" not in text


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
    """LLM이 지어낸 축값은 조용한 0건 대신 허용 목록을 담은 에러로 되돌려 모델이 재시도하게
    한다. DW-872 이전엔 이 값이 '세단'이었다(회귀 실측 H26) — DW-872로 '세단'은 별칭으로
    지원되므로(_resolve_body_type이 준중형차/중형차/대형차로 펼침, 아래 별도 테스트) 이
    테스트는 별칭·화이트리스트 어디에도 없는 값("쿠페")으로 여전히 막히는지만 확인한다."""
    import pytest
    from app.graph import agent_tools

    with pytest.raises(ValueError) as exc:
        agent_tools.search_listings.invoke(
            {"body_type": "쿠페", "query_text": "쿠페"}
        )
    msg = str(exc.value)
    assert "쿠페" in msg and "중형차" in msg  # 잘못된 값 + 허용 안내 동시 포함


def test_invalid_fuel_raises_with_allowed_values():
    import pytest
    from app.graph import agent_tools

    with pytest.raises(ValueError) as exc:
        agent_tools.search_listings.invoke(
            {"fuel": "가솔린+전기", "query_text": "하이브리드"}
        )
    assert "하이브리드" in str(exc.value)


def test_option_synonym_expansion_smart_cruise_reaches_adaptive():
    """실측 결함(2026-09-01): '스마트크루즈' 요청이 '어댑티브크루즈' 매물과 만나야 한다."""
    from app.graph.agent_tools import _expand_option_synonyms

    out = _expand_option_synonyms("스마트크루즈")
    assert "어댑티브크루즈" in out and "크루즈컨트롤" in out


def test_option_synonym_panorama_does_not_expand_to_plain_sunroof():
    """프롬프트 원문 예외: 파노라마 명시 시 일반 선루프로 확장 금지."""
    from app.graph.agent_tools import _expand_option_synonyms

    out = _expand_option_synonyms("파노라마선루프")
    assert "선루프" not in out and "파노라마선루프" in out


def test_option_synonym_groups_match_prompt_source():
    """동의어 그룹이 정본(sql_rag_node 프롬프트 원문)과 표류하지 않는지 잠근다."""
    from app.graph.agent_tools import _OPTION_SYNONYM_GROUPS
    from app.graph.sql_rag_node import _DOMAIN_RULES

    for group in _OPTION_SYNONYM_GROUPS:
        for member in group:
            assert member in _DOMAIN_RULES, f"{member}가 프롬프트 원문에 없음 — 두 정의가 갈라짐"


def test_listing_summary_includes_all_options():
    """실측 결함(2026-09-01): 요약이 옵션 앞 3개만 보여줘, 뒤쪽 옵션(어댑티브크루즈)을 근거로
    찾은 매물을 LLM이 '옵션 확인 불가'로 스스로 걸러냈다 — 전체 표기를 잠근다."""
    from app.graph.agent_tools import _format_listing_summary
    from app.schemas.ai import ListingCard

    card = ListingCard(
        id="x1", manufacturer="기아", model="더 뉴 쏘렌토 UM", year=2019,
        price=17_470_000, mileage=78_828, region="경기", fuel="디젤",
        options=["7인승", "열선시트", "헤드업디스플레이", "스마트키", "후방카메라", "어댑티브크루즈"],
    )
    summary = _format_listing_summary([card])
    assert "어댑티브크루즈" in summary  # 6번째 옵션도 요약에 보인다
