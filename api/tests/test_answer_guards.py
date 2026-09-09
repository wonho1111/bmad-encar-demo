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


def test_followup_refusal_text_points_to_compare_listings_for_unlisted_attributes():
    """DW-872 실측(C50) — 재검색이 막히자 "목록의 매물은 모두 무사고"라고 지어냈다. 거절
    문구가 compare_listings로 확인하는 경로와 "단정 금지"를 함께 안내하는지 잠근다."""
    assert "재검색 금지" in answer_guards.FOLLOWUP_REFUSAL_TEXT  # 기존 문구 보존
    assert "compare_listings" in answer_guards.FOLLOWUP_REFUSAL_TEXT
    assert "단정하지 마라" in answer_guards.FOLLOWUP_REFUSAL_TEXT


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
