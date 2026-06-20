"""sql_rag_node 순수 로직 단위 테스트 — 네트워크(LLM)·DB 무관 부분만 검증.

실제 생성·실행(라이브 LLM+DB)은 dev-story 라이브 검증에서 눈으로 확인한다(Completion Notes).
여기서는 LLM 응답 파싱·카드 매핑처럼 결정론적인 부분만 격리해 테스트한다.
특히 _content_to_text는 gemini-flash-latest가 .content를 블록 리스트로 줄 때의 회귀 방지.
"""

from app.graph.sql_rag_node import _content_to_text, _strip_sql

# 카드 매핑은 경로 A·B 공유 헬퍼(listing_cards)로 이동했다. 같은 로직을 그대로 검증한다.
from app.graph.listing_cards import rows_to_cards as _to_cards


def test_content_to_text_plain_string():
    assert _content_to_text("SELECT 1") == "SELECT 1"


def test_content_to_text_block_list():
    # gemini-flash-latest 형식: [{"type":"text","text":"..."}] → text만 추출.
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
