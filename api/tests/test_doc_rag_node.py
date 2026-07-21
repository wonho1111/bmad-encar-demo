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
import app.graph.listing_cards as listing_cards
from app.graph.doc_rag_node import _vec_literal, doc_rag_node

# run_select 모킹용 — listings/guide 행을 SQL 내용으로 분기해 돌려주는 가짜 구현.
_LISTING_ID = "44444444-4444-4444-8444-444444444444"
# Story 10.1: SELECT_COLUMNS가 11필드(기존 7 + fuel·신뢰속성 3)라 튜플도 11개를 갖춘다.
_LISTING_ROW = (
    _LISTING_ID, "기아", "카니발", "2021", "38000000", "41000", "경기",
    "LPG", None, None, None,
)
_GUIDE_ROW = ("패밀리카 적합 차종",)


def _install_fakes(monkeypatch, listing_rows, guide_rows, captured, image_rows=()):
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
        if "from listing_images" in q:
            return image_rows
        raise AssertionError(f"예상치 못한 쿼리: {query}")

    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    monkeypatch.setattr(node, "run_select", fake_run_select)
    # ⚠️ listing_cards 모듈의 run_select도 **반드시 함께** 교체한다(코드리뷰 2026-07-20).
    #   attach_cover_images는 자기 모듈(listing_cards)의 run_select를 부르므로, 노드 모듈만
    #   패치하면 여기서 **진짜 DB 접속을 시도**한다. 그러면 ① 사진 부착이 매번 조용히
    #   예외로 죽어 기능이 없어도 초록이 되고(호출을 지워도 전 테스트 통과했다)
    #   ② api/.env가 있는 환경에서는 단위테스트가 실제 Supabase에 붙어 결정론을 잃는다
    #   (project-context §12 「테스트 규칙」 위반).
    monkeypatch.setattr(listing_cards, "run_select", fake_run_select)


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
    assert card.id == _LISTING_ID and card.manufacturer == "기아" and card.model == "카니발"
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


def test_cards_carry_cover_image_from_shared_helper(monkeypatch):
    """경로 B가 **실제로** attach_cover_images를 통과한다 — 배선을 못박는 검사.

    왜 필요한가(코드리뷰 2026-07-20): 이 배선은 그동안 **주석으로만** 지켜졌다. 두 노드에서
    `attach_cover_images(...)` 호출을 통째로 벗겨내도 api 테스트 184건이 전부 초록이었다
    (실측). 에픽 AC1이 "경로 A·B가 같은 헬퍼를 통과한다"를 요구한 이유가 두 경로의 drift
    방지인데, 한쪽이 헬퍼를 잃어도 우는 검사가 하나도 없었다. 이 테스트가 그 자리다.
    """
    captured = {}
    _install_fakes(
        monkeypatch,
        [_LISTING_ROW],
        [_GUIDE_ROW],
        captured,
        image_rows=[(_LISTING_ID, "u/l/cover.webp", 3)],
    )

    result = doc_rag_node("패밀리카")

    card = result["listings"][0]
    assert card.image_path == "u/l/cover.webp", "사진 부착 헬퍼를 통과하지 않았다(AC1 배선 유실)"
    assert card.image_count == 3
    # api는 URL을 만들지 않는다 — 원본 경로만 싣는다(conventions.md §10).
    assert card.image_url is None
