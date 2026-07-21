"""sql_rag_node 순수 로직 단위 테스트 — 네트워크(LLM)·DB 무관 부분만 검증.

실제 생성·실행(라이브 LLM+DB)은 dev-story 라이브 검증에서 눈으로 확인한다(Completion Notes).
여기서는 LLM 응답 파싱·카드 매핑처럼 결정론적인 부분만 격리해 테스트한다.
특히 _content_to_text는 일부 Gemini 모델이 .content를 블록 리스트로 줄 때의 회귀 방지.
"""

from app.graph.sql_rag_node import _content_to_text, _strip_sql

# 카드 매핑은 경로 A·B 공유 헬퍼(listing_cards)로 이동했다. 같은 로직을 그대로 검증한다.
from app.graph.listing_cards import rows_to_cards as _to_cards


def test_content_to_text_plain_string():
    assert _content_to_text("SELECT 1") == "SELECT 1"


def test_content_to_text_block_list():
    # 일부 Gemini 모델 형식: [{"type":"text","text":"..."}] → text만 추출.
    content = [{"type": "text", "text": "SELECT id FROM listings", "extras": {"x": 1}}]
    assert _content_to_text(content) == "SELECT id FROM listings"


def test_content_to_text_mixed_blocks_concatenated():
    content = [
        {"type": "text", "text": "SELECT id "},
        {"type": "text", "text": "FROM listings"},
    ]
    assert _content_to_text(content) == "SELECT id FROM listings"


def test_strip_sql_removes_code_fence():
    fenced = "```sql\nSELECT id FROM listings\n```"
    assert _strip_sql(fenced) == "SELECT id FROM listings"


def test_strip_sql_plain_passthrough():
    assert _strip_sql("  SELECT 1  ") == "SELECT 1"


def test_to_cards_maps_tuple_positions_and_casts_int():
    # run_select 튜플 순서: id, manufacturer, model, year, price, mileage, region,
    #   fuel, accident_status, is_single_owner, is_non_smoker (Story 10.1 — 11필드)
    rows = [
        ("uuid-1", "현대", "싼타페", "2020", "26700000", "62000", "강원",
         "가솔린", "무사고", True, False)
    ]
    cards = _to_cards(rows)
    assert len(cards) == 1
    c = cards[0]
    assert c.id == "uuid-1" and c.manufacturer == "현대" and c.model == "싼타페"
    # 문자열로 와도 int로 캐스팅돼야 한다.
    assert c.year == 2020 and c.price == 26700000 and c.mileage == 62000
    assert c.region == "강원"
    assert c.fuel == "가솔린"
    assert c.accident_status == "무사고"
    assert c.is_single_owner is True
    assert c.is_non_smoker is False


def test_to_cards_empty():
    assert _to_cards([]) == []


# --- 경로 A 배선 검사 (코드리뷰 2026-07-20) -------------------------------------------
# 위 테스트들은 순수 헬퍼만 부르고 **노드 자체를 한 번도 호출하지 않는다.** 그래서
# `attach_cover_images(...)` 호출을 통째로 벗겨내도 전부 초록이었다(실측: 184 passed).
# 아래가 그 배선을 못박는다 — 경로 B(test_doc_rag_node)에도 짝이 되는 검사가 있다.

import app.graph.listing_cards as listing_cards  # noqa: E402
import app.graph.sql_rag_node as node  # noqa: E402

_LISTING_ID = "55555555-5555-4555-8555-555555555555"
_SAFE_SQL = (
    "SELECT id, manufacturer, model, year, price, mileage, region, "
    "fuel, accident_status, is_single_owner, is_non_smoker "
    "FROM listings WHERE status = 'on_sale' LIMIT 5"
)


class _FakeLLM:
    """항상 가드를 통과하는 SQL을 돌려주는 가짜 LLM(네트워크·과금 없음)."""

    def invoke(self, messages):
        return type("Msg", (), {"content": _SAFE_SQL})()


def test_cards_carry_cover_image_from_shared_helper(monkeypatch):
    """경로 A가 **실제로** attach_cover_images를 통과한다 — AC1 배선을 못박는 검사."""
    monkeypatch.setattr(node, "_llm", lambda: _FakeLLM())
    monkeypatch.setattr(
        node,
        "run_select",
        lambda sql, params=None: [
            (_LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원",
             "가솔린", None, None, None)
        ],
    )
    # 사진 조회는 listing_cards 모듈의 run_select를 탄다 — 노드 모듈만 패치하면
    # 진짜 DB에 붙으려다 실패하고 except가 삼켜, 기능이 없어도 초록이 된다.
    monkeypatch.setattr(
        listing_cards,
        "run_select",
        lambda sql, params=None: [(_LISTING_ID, "u/l/cover.webp", 4)],
    )

    result = node.sql_rag_node("3천만원 이하 SUV")

    card = result["listings"][0]
    assert card.image_path == "u/l/cover.webp", "사진 부착 헬퍼를 통과하지 않았다(AC1 배선 유실)"
    assert card.image_count == 4
    assert card.image_url is None  # api는 URL을 만들지 않는다(conventions.md §10)
    assert card.fuel == "가솔린"  # Story 10.1 — fuel이 실제로 채워진다(대장 #67)
    assert card.accident_status is None  # 신뢰속성 3필드는 NULL이면 None(미상)


# --- 코드리뷰 P1: 컬럼 폭이 안 맞는 LLM 응답이 노드 전체를 500으로 죽이지 않는다 ------------
# 단위 테스트(test_listing_cards.py)는 rows_to_cards가 SqlGuardError를 던지는 것까지만 본다.
# 여기서는 그 예외가 sql_rag_node의 **기존 재생성(retry) 루프**에 실제로 잡혀, IndexError가
# 위로 새서 `/ai/search`를 500으로 만들지 않는다는 것까지 배선을 따라 확인한다.


def test_short_row_from_llm_retries_instead_of_crashing(monkeypatch):
    """LLM이 프롬프트 규칙 1을 어기고 옛 7컬럼 SQL을 내면, IndexError가 아니라 SqlGuardError로
    끝난다(2회 재시도 모두 같은 SQL을 내도록 가짜 LLM을 고정해 최종 실패 경로까지 확인)."""
    from app.db.sql_guard import SqlGuardError

    short_cols_sql = (
        "SELECT id, manufacturer, model, year, price, mileage, region "
        "FROM listings WHERE status = 'on_sale' LIMIT 5"
    )

    class _StaleLLM:
        def invoke(self, messages):
            return type("Msg", (), {"content": short_cols_sql})()

    monkeypatch.setattr(node, "_llm", lambda: _StaleLLM())
    monkeypatch.setattr(
        node,
        "run_select",
        lambda sql, params=None: [
            (_LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원")  # 7개뿐
        ],
    )

    try:
        node.sql_rag_node("아무 조건")
        assert False, "컬럼 폭이 안 맞는데 예외 없이 성공했다"
    except SqlGuardError:
        pass  # 기대한 경로 — 400으로 사용자에게 안내된다(routers/ai.py).
    except IndexError:
        assert False, "IndexError가 sql_rag_node 밖으로 샜다 — /ai/search가 500이 된다(P1 회귀)"


# --- Story 10.1: 시스템 프롬프트에 신뢰속성 스키마·프롬프트 회귀 지시문이 있는지 ------------
# 프롬프트만 늘리면 "무사고 차량 찾아줘"에 LLM이 accident_status='무사고'(대부분 NULL이라
# 0건)를 쓸 수 있다(Design Notes "프롬프트 회귀 주의"). 그 지시문이 실제로 프롬프트에
# 들어있는지를 여기서 못박아, 나중에 프롬프트를 고치다 조용히 빠지는 걸 막는다.


def test_system_prompt_includes_trust_attribute_columns():
    from app.graph.sql_rag_node import _SYSTEM_PROMPT

    assert "accident_status" in _SYSTEM_PROMPT
    assert "is_single_owner" in _SYSTEM_PROMPT
    assert "is_non_smoker" in _SYSTEM_PROMPT


def test_system_prompt_instructs_accident_free_for_no_accident_queries():
    from app.graph.sql_rag_node import _SYSTEM_PROMPT

    assert "accident_free" in _SYSTEM_PROMPT
    # accident_status는 대부분 NULL이라 그것으로 "무사고"를 거르면 0건이 난다는 지시가 있어야 한다.
    assert "NULL" in _SYSTEM_PROMPT
    assert "accident_free = true" in _SYSTEM_PROMPT


def test_system_prompt_instructs_accident_free_bidirectionally():
    """코드리뷰 P5: "무사고" 방향만 유도하면 "사고 있는 차" 요청이 accident_status(전 건 NULL)로
    새어 0건이 된다 — 반대 방향도 accident_free로 유도하는 지시가 프롬프트에 있어야 한다."""
    from app.graph.sql_rag_node import _SYSTEM_PROMPT

    assert "accident_free = false" in _SYSTEM_PROMPT


def test_system_prompt_instructs_not_filtering_by_all_null_bool_columns():
    """코드리뷰 P5: is_single_owner·is_non_smoker는 지금 전부 NULL이라, 스키마에 광고돼 있다는
    이유만으로 필터에 쓰면 "1인소유 차량 찾아줘" 같은 요청이 항상 0건이 된다. 그 두 컬럼으로
    지금 필터하지 말라는 지시가 프롬프트에 있어야 한다."""
    from app.graph.sql_rag_node import _SYSTEM_PROMPT

    assert "필터 조건으로 쓰지 마라" in _SYSTEM_PROMPT
