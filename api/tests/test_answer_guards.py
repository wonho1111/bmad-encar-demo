"""answer_guards 단위 테스트 — 전부 순수 함수, LLM·DB 무관(DW-855·869·870 결정론 방어 3종).

agent.py의 도구 디스패치 루프·최종화 배선은 tests/test_agent_loop.py가 확인한다(가짜 LLM·
가짜 도구로 실제 루프 안에서 이 함수들이 호출되는지 검증). 여기서는 함수 자체의 입출력만
격리해 본다.
"""

from app.graph import answer_guards


# ───────── (1) block_research_on_followup ─────────

def test_block_research_on_followup_true_when_reference_and_context_ids_present():
    assert answer_guards.block_research_on_followup("나머지 두 개랑 비교해줘", ["aaa", "bbb"]) is True


def test_block_research_on_followup_false_without_context_ids():
    # 지칭 표현이 있어도 직전 목록 id가 없으면(첫 턴 등) 막을 이유가 없다 — 새 검색이 맞다.
    assert answer_guards.block_research_on_followup("나머지 두 개랑 비교해줘", []) is False
    assert answer_guards.block_research_on_followup("나머지 두 개랑 비교해줘", None) is False


def test_block_research_on_followup_false_without_reference_pattern():
    # 직전 목록 id가 있어도 지칭 표현이 없는 새 조건 검색이면 막지 않는다.
    assert answer_guards.block_research_on_followup("3천만원 이하 SUV 보여줘", ["aaa"]) is False


def test_block_research_on_followup_matches_various_reference_markers():
    phrases = (
        "그중 첫 번째는?", "그 중에 저렴한 거", "그거 시세 알려줘", "이 중 무사고만",
        "두 번째 매물 비교해줘", "5번째 매물은?", "앞의 두 개만", "둘 다 비교해줘", "전부 비교해줘",
    )
    for phrase in phrases:
        assert answer_guards.block_research_on_followup(phrase, ["aaa"]) is True, phrase


def test_block_research_on_followup_matches_newly_added_reference_markers():
    """DW-872 update(2026-09-09 18:08) (b) 실측(C59) — "여기서 흰색만 있어?"가 가드 지칭
    패턴 밖이라 재검색으로 샜다. 새로 추가한 지칭 표현이 전부 잡히는지 잠근다."""
    phrases = (
        "여기서 흰색만 있어?", "여기 중에 저렴한 거", "이 매물들 중에 골라줘",
        "이것들 다 비교해줘", "그것들 시세 알려줘", "위에서 첫 번째", "위 목록 중에",
        "위에 있는 거 비교해줘", "얘네 중에 뭐가 나아", "요 중에 무사고만", "그 목록에서 하나만",
    )
    for phrase in phrases:
        assert answer_guards.block_research_on_followup(phrase, ["aaa"]) is True, phrase


def test_followup_refusal_text_points_to_compare_listings_for_unlisted_attributes():
    """DW-872 실측(C50) — 재검색이 막히자 "목록의 매물은 모두 무사고"라고 지어냈다. 거절
    문구가 compare_listings로 확인하는 경로와 "단정 금지"를 함께 안내하는지 잠근다."""
    assert "재검색 금지" in answer_guards.FOLLOWUP_REFUSAL_TEXT  # 기존 문구 보존
    assert "compare_listings" in answer_guards.FOLLOWUP_REFUSAL_TEXT
    assert "단정하지 마라" in answer_guards.FOLLOWUP_REFUSAL_TEXT


def test_followup_refusal_text_points_to_market_price_stats_for_price_questions():
    """DW-872 update(2026-09-09 18:08) (d) 실측(C53) — 재검색이 막히자 "목록에 없다"고
    답했다. 정답은 직전 매물 id로 market_price_stats를 호출하는 것 — 거절 문구가 그
    경로도 안내하는지 잠근다(compare_listings 안내와는 별개 문장)."""
    assert "market_price_stats" in answer_guards.FOLLOWUP_REFUSAL_TEXT
    assert "compare_listings가 아니라" in answer_guards.FOLLOWUP_REFUSAL_TEXT


# ───────── (2) strip_listing_ids — 3가지 UUID 노출 형태 ─────────

def test_strip_listing_ids_removes_paren_id_form():
    answer = "쏘렌토 매물이에요 (id: 8f9ad147-1234-4abc-9def-0123456789ab) 확인해보세요."
    assert answer_guards.strip_listing_ids(answer) == "쏘렌토 매물이에요 확인해보세요."


def test_strip_listing_ids_removes_id_equals_form():
    answer = "id=8f9ad147-1234-4abc-9def-0123456789ab 매물을 추천합니다."
    assert answer_guards.strip_listing_ids(answer) == "매물을 추천합니다."


def test_strip_listing_ids_removes_bare_uuid():
    answer = "매물 8f9ad147-1234-4abc-9def-0123456789ab 을 확인하세요."
    assert answer_guards.strip_listing_ids(answer) == "매물 을 확인하세요."


def test_strip_listing_ids_no_id_is_unchanged():
    answer = "id 없는 평범한 답변입니다."
    assert answer_guards.strip_listing_ids(answer) == answer
    assert answer_guards.strip_listing_ids("") == ""


# ───────── (3) ensure_sample_caveat ─────────

def test_ensure_sample_caveat_appends_when_small_sample_and_no_existing_caveat():
    answer = "이 매물은 적정 수준의 가격입니다."
    result = answer_guards.ensure_sample_caveat(answer, [{"criteria": {"sample_count": 2}}])
    assert result == "이 매물은 적정 수준의 가격입니다. 비교 가능한 매물이 2건뿐이라 표본이 적어 참고만 하세요."


def test_ensure_sample_caveat_skips_when_caveat_word_already_present():
    # "표본" 또는 "참고만" 둘 중 하나만 있어도 이미 경고했다고 보고 중복으로 덧붙이지 않는다.
    with_sample = "표본이 적어 판단이 어렵지만 대략 3000만원대로 보여요."
    assert answer_guards.ensure_sample_caveat(with_sample, [{"criteria": {"sample_count": 1}}]) == with_sample

    with_reference_only = "이 가격대는 참고만 하시면 좋을 것 같아요."
    assert answer_guards.ensure_sample_caveat(
        with_reference_only, [{"criteria": {"sample_count": 1}}]
    ) == with_reference_only


def test_ensure_sample_caveat_no_change_when_samples_sufficient():
    answer = "이 매물은 적정 수준의 가격입니다."
    assert answer_guards.ensure_sample_caveat(answer, [{"criteria": {"sample_count": 6}}]) == answer


def test_ensure_sample_caveat_no_change_when_no_diagnoses():
    answer = "이 매물은 적정 수준의 가격입니다."
    assert answer_guards.ensure_sample_caveat(answer, None) == answer
    assert answer_guards.ensure_sample_caveat(answer, []) == answer


# ───────── (4) infer_missing_args — DW-872 update(2026-09-09 18:08) (f) 실측 C02·C03 ─────────
#
# "SUV"·"하이브리드"가 질문에 있어도 search_listings 인자 없이 query_text에만 실렸다.
# 모델이 비운 인자만 원문 질의의 닫힌 어휘(agent_tools 화이트리스트·별칭)로 채우는지,
# 이미 채운 인자는 절대 안 덮는지, 부정어 뒤 6자는 걸러지는지를 스펙 표 그대로 잠근다.

def test_infer_missing_args_fills_body_type_and_fuel_when_empty():
    assert answer_guards.infer_missing_args("SUV 중에 4천만원대 디젤", {}) == {
        "body_type": "SUV", "fuel": "디젤",
    }


def test_infer_missing_args_negation_guard_excludes_negated_body_type():
    # "SUV 말고 세단" — SUV는 부정어(말고) 6자 안이라 빠지고 세단만 채워진다.
    assert answer_guards.infer_missing_args("SUV 말고 세단 3천", {}) == {"body_type": "세단"}


def test_infer_missing_args_keeps_existing_arg_value():
    # 모델이 이미 채운 fuel="가솔린"은 질의에 "하이브리드"가 있어도 덮지 않는다.
    assert answer_guards.infer_missing_args("그랜저 하이브리드", {"fuel": "가솔린"}) == {"fuel": "가솔린"}


def test_infer_missing_args_fills_seats_min_and_body_type():
    assert answer_guards.infer_missing_args("7인승 이상 SUV", {}) == {"seats_min": 7, "body_type": "SUV"}


def test_infer_missing_args_fills_fuel_for_electric_car_phrase():
    # "전기차"는 별도 별칭 없이도 화이트리스트 "전기"가 부분일치로 잡힌다. "4천만원 이하"도
    # 예산 패턴(C48)에 걸려 price_max가 함께 채워진다.
    assert answer_guards.infer_missing_args("전기차 4천만원 이하", {}) == {
        "fuel": "전기", "price_max": 40_000_000,
    }


def test_infer_missing_args_fills_manufacturer_alias():
    assert answer_guards.infer_missing_args("르노 차", {}) == {"manufacturer": "르노코리아"}


def test_infer_missing_args_does_not_mutate_input_dict():
    original = {}
    answer_guards.infer_missing_args("SUV 3천만원", original)
    assert original == {}  # 순수 함수 — 원본 args는 바뀌지 않는다.


def test_infer_missing_args_unknown_wording_stays_empty():
    # 화이트리스트 밖 축약어('하브' 등)는 채우지 않는다 — 오탐(잘못된 필터) 방지.
    assert answer_guards.infer_missing_args("하브 그랜저 좋아요", {}) == {}


def test_infer_missing_args_body_type_case_insensitive():
    # 소문자 'suv'로 써도 화이트리스트 표기(SUV)로 채운다 — 대소문자 표기 차이로 새지 않는다.
    assert answer_guards.infer_missing_args("suv 있나요", {}) == {"body_type": "SUV"}


def test_infer_missing_args_does_not_inject_manufacturer_from_bare_samsung():
    """'삼성'은 지명(삼성역)·가전 등 무관 문맥이 흔해 질문 스캔 자동 주입에서는 제외한다(르노코리아 오탐 방지)."""
    from app.graph.answer_guards import infer_missing_args
    assert "manufacturer" not in infer_missing_args("삼성역 근처 SUV 3천만원 이하", {})
    assert infer_missing_args("르노삼성 SUV", {}).get("manufacturer") == "르노코리아"


# ───────── (5) resolve_list_reference — DW-855 3차 재검증(순번·극값·비교) ─────────

from app.schemas.ai import ListingCard  # noqa: E402 — 기존 파일 상단 임포트 관례를 그대로 따른다.


def _card(id_, price, year, mileage):
    return ListingCard(
        id=id_, manufacturer="현대", model="아반떼", year=year, price=price,
        mileage=mileage, region="서울",
    )


_THREE_CARDS = [_card("id1", 9_260_000, 2017, 106_062), _card("id2", 25_000_000, 2020, 50_000),
                _card("id3", 15_000_000, 2019, 80_000)]


def test_resolve_list_reference_ordinal_word():
    assert answer_guards.resolve_list_reference("그중 두 번째 거 시세 봐줘", _THREE_CARDS) == ["id2"]


def test_resolve_list_reference_ordinal_digit_jjae():
    assert answer_guards.resolve_list_reference("2번째 매물 비교해줘", _THREE_CARDS) == ["id2"]


def test_resolve_list_reference_ordinal_digit_beon():
    assert answer_guards.resolve_list_reference("1번 매물 시세 알려줘", _THREE_CARDS) == ["id1"]


def test_resolve_list_reference_extreme_cheapest():
    assert answer_guards.resolve_list_reference("제일 싼 거 시세 봐줘", _THREE_CARDS) == ["id1"]


def test_resolve_list_reference_extreme_most_expensive():
    assert answer_guards.resolve_list_reference("가장 비싼 매물 알려줘", _THREE_CARDS) == ["id2"]


def test_resolve_list_reference_comparison_cheaper_side():
    assert answer_guards.resolve_list_reference("그중에 더 저렴한 쪽 시세 확인해줘", _THREE_CARDS) == ["id1"]


def test_resolve_list_reference_none_without_reference():
    assert answer_guards.resolve_list_reference("3천만원 이하 SUV 보여줘", _THREE_CARDS) is None


def test_resolve_list_reference_none_without_cards():
    assert answer_guards.resolve_list_reference("그중 두 번째 거 시세 봐줘", []) is None


def test_resolve_list_reference_ordinal_out_of_range_falls_through_to_none():
    # 카드 3장인데 "5번째"는 범위 밖이다 — 극값 패턴도 아니므로 최종 None(건드리지 않는다).
    assert answer_guards.resolve_list_reference("5번째 매물 보여줘", _THREE_CARDS) is None


# ───────── (7) _parse_budget_max·has_listing_intent (C36·C48·C71) ─────────

def test_parse_budget_max_cheonman_pattern():
    assert answer_guards._parse_budget_max("4천만원 이하 세단 보여줘") == 40_000_000


def test_parse_budget_max_baekman_pattern():
    assert answer_guards._parse_budget_max("8백만원 이내로요") == 8_000_000


def test_parse_budget_max_man_pattern():
    assert answer_guards._parse_budget_max("1500만원까지 생각중이에요") == 15_000_000


def test_parse_budget_max_none_without_suffix():
    # "이하/이내/까지"가 없으면(예: 단순 언급) 예산으로 보지 않는다 — 과설계 금지.
    assert answer_guards._parse_budget_max("4천만원짜리 차 있나요") is None


def test_has_listing_intent_true_for_structural_vocab():
    # infer_missing_args가 인식하는 구조 조건 어휘(body_type=SUV)만으로도 True.
    assert answer_guards.has_listing_intent("SUV 있나요") is True


def test_has_listing_intent_true_for_budget_pattern():
    assert answer_guards.has_listing_intent("4천만원 이하로 뭐 살 수 있어요") is True


def test_has_listing_intent_true_for_recommend_words():
    # C36 — 구조 조건도 예산도 없지만 "좋은 차"가 있으면 매물 추천 의도로 본다.
    assert answer_guards.has_listing_intent("여자친구랑 드라이브 다니기 좋은 차") is True


def test_has_listing_intent_false_for_pure_knowledge_question():
    assert answer_guards.has_listing_intent("침수차량인지 아닌지 구별하는 팁 있을까요") is False


# ───────── (8) narrow_by_attribute (C50·C59) ─────────

def _attr_card(id_, *, accident_status=None, color=None, fuel=None):
    card = ListingCard(
        id=id_, manufacturer="현대", model="아반떼", year=2020, price=10_000_000,
        mileage=50_000, region="서울",
    )
    card.accident_status = accident_status
    card.color = color
    card.fuel = fuel
    return card


_NARROW_CARDS = [
    _attr_card("id1", accident_status="무사고", color="흰색", fuel="가솔린"),
    _attr_card("id2", accident_status="단순교환", color="검정", fuel="하이브리드"),
    _attr_card("id3", accident_status="무사고", color="은색", fuel="가솔린"),
]


def test_narrow_by_attribute_accident_status():
    # C50 — "그 중에 무사고인 것만 골라줘" → 무사고 2건(id1·id3)만 남는다.
    assert answer_guards.narrow_by_attribute("그 중에 무사고인 것만 골라줘", _NARROW_CARDS) == ["id1", "id3"]


def test_narrow_by_attribute_color_with_no_match_returns_empty_list():
    # C59 — "여기서 흰색만 있어?"는 흰색 1건(id1)만 남긴다. 다른 케이스로 흰색이 전혀 없는
    # 목록을 주면 빈 리스트(조건에 맞는 매물 없음)를 돌려준다 — None이 아니다.
    assert answer_guards.narrow_by_attribute("여기서 흰색만 있어?", _NARROW_CARDS) == ["id1"]
    no_white = [_attr_card("id9", accident_status="무사고", color="검정", fuel="가솔린")]
    assert answer_guards.narrow_by_attribute("여기서 흰색만 있어?", no_white) == []


def test_narrow_by_attribute_none_without_matching_vocab():
    # 사고 상태·색상·연료 어휘가 전혀 없으면 좁히지 않는다(순번·극값 등 다른 지칭과 안 섞임).
    assert answer_guards.narrow_by_attribute("그중 두 번째 거 보여줘", _NARROW_CARDS) is None


def test_narrow_by_attribute_none_without_cards():
    assert answer_guards.narrow_by_attribute("그 중에 무사고인 것만", []) is None


# ───────── (9) infer_missing_args manufacturer 정규화(C19) ─────────

def test_infer_missing_args_normalizes_manufacturer_even_when_already_set():
    # 모델이 이미 manufacturer="르노"를 채워도(비어 있지 않음) 별칭 사전으로 정규화한다 —
    # 기존 "비어 있을 때만 채운다" 규칙의 예외(다른 필드는 그대로 유지).
    assert answer_guards.infer_missing_args(
        "르노 SUV 있나요 3천만원 이하로", {"manufacturer": "르노", "body_type": "SUV"}
    ) == {"manufacturer": "르노코리아", "body_type": "SUV", "price_max": 30_000_000}


def test_infer_missing_args_manufacturer_unaffected_when_no_alias():
    # 별칭 사전에 없는 값(이미 정확한 CHECK 표기)은 그대로 둔다.
    assert answer_guards.infer_missing_args("현대차 좋아요", {"manufacturer": "현대"}) == {
        "manufacturer": "현대",
    }
