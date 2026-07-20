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
    # run_select 튜플 순서: id, manufacturer, model, year, price, mileage, region
    rows = [("uuid-1", "현대", "싼타페", "2020", "26700000", "62000", "강원")]
    cards = _to_cards(rows)
    assert len(cards) == 1
    c = cards[0]
    assert c.id == "uuid-1" and c.manufacturer == "현대" and c.model == "싼타페"
    # 문자열로 와도 int로 캐스팅돼야 한다.
    assert c.year == 2020 and c.price == 26700000 and c.mileage == 62000
    assert c.region == "강원"


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
    "SELECT id, manufacturer, model, year, price, mileage, region "
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
            (_LISTING_ID, "현대", "싼타페", 2020, 26700000, 62000, "강원")
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
