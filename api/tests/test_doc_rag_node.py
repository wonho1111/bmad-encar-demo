"""doc_rag_node(경로 B) 순수 로직 단위 테스트 — 네트워크(임베딩)·DB 무관 부분만 검증.

실제 임베딩 검색(라이브 Gemini+pgvector)은 dev-story 라이브 검증에서 눈으로 확인한다(Completion Notes).
여기서는 embed_query·run_select를 monkeypatch해 결정론적인 부분만 격리한다:
  · 질의가 embed_query(검색용)로 임베딩되는지
  · 벡터가 pgvector 리터럴 "[...]"로 바인딩되는지
  · 매물 검색 SQL에 FR11(status='on_sale')·코사인 정렬(<=>)이 들어가는지(AC2)
  · 튜플 → ListingCard 매핑
  · 0건 → FR17 안내·listings=[](AC3)
  · 근거 가이드 제목이 answer에 포함되는지
"""

import app.graph.doc_rag_node as node
from app.graph.doc_rag_node import _vec_literal, doc_rag_node

# run_select 모킹용 — listings/guide 행을 SQL 내용으로 분기해 돌려주는 가짜 구현.
_LISTING_ROW = ("uuid-1", "기아", "카니발", "2021", "38000000", "41000", "경기")
_GUIDE_ROW = ("패밀리카 적합 차종",)


def _install_fakes(monkeypatch, listing_rows, guide_rows, captured):
    """embed_query·run_select를 가짜로 교체하고 호출 인자를 captured에 기록한다."""

    def fake_embed_query(text):
        captured["embed_query_arg"] = text
        return [0.1, 0.2, 0.3]  # 3차원이면 충분(차원 검증은 embeddings.py 단위테스트 소관)

    def fake_run_select(query, params=None):
        captured.setdefault("queries", []).append((query, params))
        q = query.lower()
        if "from listings" in q:
            return listing_rows
        if "from guide_documents" in q:
            return guide_rows
        raise AssertionError(f"예상치 못한 쿼리: {query}")

    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    monkeypatch.setattr(node, "run_select", fake_run_select)


def test_vec_literal_format():
    assert _vec_literal([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"
    assert _vec_literal([]) == "[]"


def test_uses_embed_query_with_raw_query(monkeypatch):
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)
    doc_rag_node("패밀리카로 무난한 거")
    # 검색용 embed_query에 원문 질의가 그대로 전달돼야 한다(함정 #3: embed_documents 아님).
    assert captured["embed_query_arg"] == "패밀리카로 무난한 거"


def test_listings_query_enforces_on_sale_and_cosine_order(monkeypatch):
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)
    doc_rag_node("초보 운전자에게 좋은 차")

    listing_q, listing_params = next(
        (q, p) for (q, p) in captured["queries"] if "from listings" in q.lower()
    )
    # AC2/FR11 — 코드가 직접 status='on_sale'을 강제해야 한다(가드가 없으므로).
    assert "status = 'on_sale'" in listing_q
    assert "embedding is not null" in listing_q.lower()
    # 코사인 유사도 정렬 + LIMIT 파라미터 바인딩.
    assert "order by embedding <=> %s::vector" in listing_q.lower()
    # 벡터는 리터럴 문자열로, LIMIT은 정수로 바인딩(f-string 직접 삽입 금지).
    assert listing_params[0] == "[0.1,0.2,0.3]"
    assert isinstance(listing_params[1], int)


def test_maps_rows_to_listing_cards(monkeypatch):
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)
    result = doc_rag_node("가족용 큰 차")

    assert len(result["listings"]) == 1
    card = result["listings"][0]
    assert card.id == "uuid-1" and card.manufacturer == "기아" and card.model == "카니발"
    # 문자열로 와도 int 캐스팅.
    assert card.year == 2021 and card.price == 38000000 and card.mileage == 41000
    assert card.region == "경기"


def test_answer_includes_guide_title(monkeypatch):
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)
    result = doc_rag_node("패밀리카")
    assert "1건을 찾았어요" in result["answer"]
    # 근거 가이드 제목이 answer에 곁들여진다(AC1 "적합 차종/특성 근거").
    assert "패밀리카 적합 차종" in result["answer"]


def test_empty_result_returns_fr17_guidance(monkeypatch):
    captured = {}
    # 매물 0건 — 가이드는 있어도 매물이 없으면 FR17 안내.
    _install_fakes(monkeypatch, [], [_GUIDE_ROW], captured)
    result = doc_rag_node("존재하지 않는 무언가")

    assert result["listings"] == []  # 빈 목록
    assert "없어요" in result["answer"]  # FR17 조건 완화/재질문 안내
    # 0건이면 근거 가이드 제목을 굳이 붙이지 않는다(혼선 방지).
    assert "참고:" not in result["answer"]


def test_no_guide_still_returns_listings(monkeypatch):
    captured = {}
    # 가이드 0건이어도 매물이 있으면 추천은 정상 반환(근거만 생략).
    _install_fakes(monkeypatch, [_LISTING_ROW], [], captured)
    result = doc_rag_node("무난한 차")
    assert len(result["listings"]) == 1
    assert "참고:" not in result["answer"]
