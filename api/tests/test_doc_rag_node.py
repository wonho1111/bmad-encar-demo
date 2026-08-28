"""doc_rag_node(경로 B) 순수 로직 단위 테스트 — 네트워크(임베딩)·DB 무관 부분만 검증.

실제 임베딩 검색(라이브 Gemini+pgvector)은 dev-story 라이브 검증에서 눈으로 확인한다(Completion Notes).
여기서는 embed_query·run_select를 monkeypatch해 결정론적인 부분만 격리한다:
  · 질의가 embed_query(검색용)로 임베딩되는지
  · 벡터가 pgvector 리터럴 "[...]"로 바인딩되는지
  · 매물 검색 SQL에 FR11(status='on_sale')·코사인 정렬(<=>)이 들어가는지(AC2)
  · 튜플 → ListingCard 매핑
  · 0건 → FR17 안내·listings=[](AC3)
  · 근거 가이드 제목이 answer에 포함되는지 — 단, 컷오프(FR49, Story 13.6) 이내일 때만
"""

import app.graph.doc_rag_node as node
import app.graph.listing_cards as listing_cards
from app.graph.doc_rag_node import (
    _GUIDE_DISTANCE_CEILING,
    _GUIDE_MARGIN,
    _vec_literal,
    doc_rag_node,
    find_relevant_guide,
)

# run_select 모킹용 — listings/guide 행을 SQL 내용으로 분기해 돌려주는 가짜 구현.
_LISTING_ID = "44444444-4444-4444-8444-444444444444"
# Story 10.1·10.3: SELECT_COLUMNS가 12필드(기존 7 + fuel·신뢰속성 3 + options)라 튜플도 12개를 갖춘다.
_LISTING_ROW = (
    _LISTING_ID, "기아", "카니발", "2021", "38000000", "41000", "경기",
    "LPG", None, None, None, None,
)
# find_relevant_guide 계약(Story 13.6, top-k 상대 게이트로 전환) — (title, content, distance)
# 3-tuple. 0.1은 상한(0.45) 이내(기존 인용 동작 유지 확인용) — 단독 행이면 1등=자기 자신이라
# 마진 게이트도 항상 통과한다.
_GUIDE_ROW = ("패밀리카 적합 차종", "가이드 본문 텍스트", 0.1)
# 절대 상한(0.45) 초과 — 무관 가이드가 딸려 와도 인용·질의확장에 쓰이면 안 된다(FR49).
_GUIDE_ROW_BEYOND_CUTOFF = ("전기차 충전·보조금 가이드", "전기차 본문 텍스트", 0.5)


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
    # 근거 가이드 제목이 answer에 곁들여진다(AC1 "적합 차종/특성 근거"). 가이드가 1개면
    # 기존과 동일하게 "(참고: A)" 형식이다.
    assert result["answer"].endswith("(참고: 패밀리카 적합 차종)")


def test_answer_includes_up_to_two_guide_titles(monkeypatch):
    """신규 테스트(e) — top-k 게이트를 여러 건 통과하면 상위 최대 2개 제목만 인용한다.

    3건이 통과해도 3번째는 인용에서 빠진다("," 로 이어붙인 2개까지만).
    """
    captured = {}
    rows = [
        ("1등 가이드", "본문1", 0.20),
        ("2등 가이드", "본문2", 0.22),
        ("3등 가이드", "본문3", 0.24),
    ]
    _install_fakes(monkeypatch, [_LISTING_ROW], rows, captured)
    result = doc_rag_node("패밀리카")
    assert result["answer"].endswith("(참고: 1등 가이드, 2등 가이드)")
    assert "3등 가이드" not in result["answer"]


def test_find_relevant_guide_within_cutoff_returns_title_and_content(monkeypatch):
    """단독 행 + 상한(0.45) 이내면 [(title, content)]를 그대로 반환한다(Story 13.6 AC1)."""
    monkeypatch.setattr(node, "run_select", lambda query, params=None: [_GUIDE_ROW])
    assert find_relevant_guide("[0.1,0.2,0.3]") == [(_GUIDE_ROW[0], _GUIDE_ROW[1])]


def test_find_relevant_guide_beyond_cutoff_returns_none(monkeypatch):
    """거리가 절대 상한(0.45)을 초과하면 가이드가 있어도 빈 리스트를 반환한다(FR49)."""
    monkeypatch.setattr(node, "run_select", lambda query, params=None: [_GUIDE_ROW_BEYOND_CUTOFF])
    assert find_relevant_guide("[0.1,0.2,0.3]") == []


def test_guide_query_selects_three_columns_and_binds_vector_twice(monkeypatch):
    """가이드 조회 SQL의 컬럼·필터·정렬·**자리표시자 2개 바인딩**을 못박는다(후속 코드리뷰).

    이 SQL은 `%s`를 두 번 쓰면서 params도 두 개를 넘긴다 — 한쪽만 고치면 psycopg가 실행
    시점에 죽어 /ai/search 전체가 500이 된다. 그런데 두 단위테스트 파일 모두 run_select를
    가짜로 갈아끼우며 params를 통째로 무시하고 있어, 바인딩을 (qvec_literal,) 하나로 줄여도
    전 스위트가 초록이었다(실측). 그 구멍을 여기서 닫는다 — 이 SQL은 이 세션에서 실 DB로
    실행해 볼 수 없으므로(로컬 Supabase 부재, DW-604) 문자열·파라미터 단언이 유일한 가드다.
    """
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)
    doc_rag_node("패밀리카")

    # 기본값 없는 next()는 가이드 조회가 아예 사라진 회귀에서 StopIteration error로 끝나
    # "무엇이 없어졌는지"를 알려주지 못한다(3회차 코드리뷰) — 이 테스트가 실 DB 없이 이 SQL을
    # 지키는 유일한 가드이므로 실패 메시지가 원인을 말해야 한다.
    found = next(
        ((q, p) for (q, p) in captured["queries"] if "from guide_documents" in q.lower()),
        None,
    )
    assert found is not None, "가이드 조회 SQL이 발행되지 않았다(find_relevant_guide 미호출?)"
    guide_q, guide_params = found
    lowered = guide_q.lower()
    # content까지 함께 가져와야 hybrid의 질의확장(FR44)이 본문을 프롬프트에 넣을 수 있다.
    assert "select title, content," in lowered
    assert "embedding is not null" in lowered
    assert "order by embedding <=> %s::vector" in lowered
    # LIMIT도 %s 자리표시자로 바인딩된다(top-k, LIMIT 1이 아니다).
    assert "limit %s" in lowered
    # 자리표시자 개수와 바인딩 개수가 반드시 일치해야 한다(실행 시점 500 방지) — 벡터절 2개 +
    # top-k 정수 1개.
    assert lowered.count("%s") == len(guide_params) == 3
    assert guide_params == ("[0.1,0.2,0.3]", "[0.1,0.2,0.3]", node._GUIDE_TOP_K)


def test_find_relevant_guide_at_exact_cutoff_is_included(monkeypatch):
    """단독 행 + 거리 == 절대 상한은 **포함**이다(`<=`) — 경계 자체를 못박는다(후속 코드리뷰).

    기존 테스트는 0.1(한참 안쪽)과 0.5(한참 바깥)만 써서, 비교연산자를 `<`로 바꿔도
    전 스위트가 초록이었다. 상한이 이 게이트의 최후 안전판인데 그 판단의 정의가 테스트로
    고정돼 있지 않았다.
    """
    at_cutoff = ("경계 가이드", "본문", _GUIDE_DISTANCE_CEILING)
    monkeypatch.setattr(node, "run_select", lambda query, params=None: [at_cutoff])
    assert find_relevant_guide("[0.1,0.2,0.3]") == [("경계 가이드", "본문")]


def test_find_relevant_guide_just_beyond_cutoff_is_excluded(monkeypatch):
    """절대 상한을 아주 조금만 넘어도 제외된다 — 위 경계 테스트의 반대편 짝."""
    beyond = ("경계 밖 가이드", "본문", _GUIDE_DISTANCE_CEILING + 1e-9)
    monkeypatch.setattr(node, "run_select", lambda query, params=None: [beyond])
    assert find_relevant_guide("[0.1,0.2,0.3]") == []


def test_find_relevant_guide_rejects_nan_distance(monkeypatch):
    """1등 거리가 NaN이면 전부 제외된다 — 게이트를 "통과 조건"으로 써야 하는 이유(3회차 코드리뷰).

    실측(옛 절대 컷오프 시절): 게이트가 `if distance > _GUIDE_DISTANCE_CUTOFF`였을 때 NaN
    행을 넣으면 함수는 가이드를 **반환**하는데(NaN과의 모든 비교는 False라 `>` 검사를
    빠져나간다) 바로 위 로그는 `컷오프통과=False`라고 남겼다 — 스펙이 요구한 유일한 계측
    수단이 실제 동작과 반대를 말하는 상태였다. 도달 경로: 질의 임베딩이 영벡터면
    (embeddings.py의 _l2_normalize가 norm==0을 그대로 통과시킨다) pgvector `<=>`가 NaN을
    내고, 그때는 모든 행이 NaN이라 1등 거리(best_distance)도 NaN — `d <= NaN + margin`은
    항상 False라 top-k 게이트에서도 전부 탈락한다(빈 리스트).
    """
    nan_row = ("무관 가이드", "무관 본문", float("nan"))
    monkeypatch.setattr(node, "run_select", lambda query, params=None: [nan_row])
    assert find_relevant_guide("[0.0,0.0,0.0]") == []


def test_find_relevant_guide_all_nan_distances_returns_empty(monkeypatch):
    """여러 행이 전부 NaN이어도(1등뿐 아니라 전체) 빈 리스트다 — top-k 게이트의 NaN 전멸 확인."""
    rows = [("가이드1", "본문1", float("nan")), ("가이드2", "본문2", float("nan"))]
    monkeypatch.setattr(node, "run_select", lambda query, params=None: rows)
    assert find_relevant_guide("[0.0,0.0,0.0]") == []


def test_find_relevant_guide_top_k_margin_gate(monkeypatch):
    """신규 테스트(a) — 1등 0.28·2등 0.31·3등 0.36(마진 0.05): a·b만 통과, c는 마진 밖.

    1등 대비 마진 0.05 이내(0.28~0.33)만 통과해야 한다 — b(0.31)는 포함, c(0.36)는 제외.
    """
    rows = [("a", "본문a", 0.28), ("b", "본문b", 0.31), ("c", "본문c", 0.36)]
    monkeypatch.setattr(node, "run_select", lambda query, params=None: rows)
    assert find_relevant_guide("[0.1,0.2,0.3]") == [("a", "본문a"), ("b", "본문b")]


def test_find_relevant_guide_ceiling_gate_even_within_margin(monkeypatch):
    """신규 테스트(b) — 1등 0.44·2등 0.47(마진 안이어도 2등은 절대 상한 0.45 초과라 제외).

    2등(0.47)은 1등(0.44) 대비 마진(0.05) 안이지만(0.44+0.05=0.49 ≥ 0.47), 절대 상한
    0.45를 넘어 제외돼야 한다 — 마진·상한 두 게이트가 AND로 둘 다 필요함을 확인한다.
    """
    rows = [("1등", "본문1", 0.44), ("2등", "본문2", 0.47)]
    monkeypatch.setattr(node, "run_select", lambda query, params=None: rows)
    assert find_relevant_guide("[0.1,0.2,0.3]") == [("1등", "본문1")]


def test_find_relevant_guide_ceiling_gate_excludes_first_place_too(monkeypatch):
    """신규 테스트(b) 이어서 — 1등 자체가 0.46(상한 초과)이면 빈 리스트."""
    rows = [("1등", "본문1", 0.46)]
    monkeypatch.setattr(node, "run_select", lambda query, params=None: rows)
    assert find_relevant_guide("[0.1,0.2,0.3]") == []


def test_doc_rag_node_reuses_caller_supplied_qvec(monkeypatch):
    """qvec을 넘기면 embed_query를 부르지 않고 그 벡터를 두 쿼리에 실제로 바인딩한다.

    3회차 코드리뷰 실측: doc_rag_node가 전달받은 qvec을 무시하고 embed_query(query)를 다시
    부르도록 되돌려도 전 스위트가 370 passed로 초록이었다. hybrid 쪽 테스트 3곳의
    `assert qvec == [0.1]`은 모두 doc_rag_node **자체를 대체한** fake_doc 안에 있어서
    "hybrid가 인자를 넘겼다"만 증명하고 "doc_rag_node가 그 인자를 썼다"는 증명하지 않는다
    (테스트 주석은 후자를 못박는다고 적혀 있었다 — 1·2회차가 잡은 것과 같은 부류의 착시).
    실제 대가는 과금되는 Gemini 임베딩 API의 중복 호출이며, 하필 이 스토리가 돕겠다고 한
    "느낌만 있는 질의"(NONE 폴백) 경로에서 매 요청 2회가 된다.
    """
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW], captured)

    result = doc_rag_node("느낌만 있는 질의", qvec=[0.9, 0.8, 0.7])

    assert "embed_query_arg" not in captured, "qvec을 넘겼는데 embed_query가 호출됐다"
    listing_params = next(
        p for (q, p) in captured["queries"] if "from listings" in q.lower()
    )
    assert listing_params[0] == "[0.9,0.8,0.7]"
    guide_params = next(
        p for (q, p) in captured["queries"] if "from guide_documents" in q.lower()
    )
    assert guide_params == ("[0.9,0.8,0.7]", "[0.9,0.8,0.7]", node._GUIDE_TOP_K)
    assert len(result["listings"]) == 1


def test_find_relevant_guide_rejects_blank_title_or_content(monkeypatch):
    """제목이나 본문이 공백뿐이면 상한 이내여도 그 행은 제외된다(후속 코드리뷰).

    이전 패스는 **인용 자리에만** `guide[0]` 검사를 넣었다 — 그래서 (1) 제목이 공백
    문자열이면 `"   "`가 참이라 "(참고:    )"라는 빈 인용이 그대로 붙었고(실측),
    (2) 빈 제목·빈 본문 가이드가 hybrid의 조건추출 프롬프트에는 여전히 주입돼 매핑도
    없이 "규칙 2보다 우선한다"는 지시만 LLM에 전달됐다. 게이트를 헬퍼로 모아 둘 다 막는다.
    단독 행이면 결과는 빈 리스트다.
    """
    for row in (("   ", "본문", 0.1), ("제목", "  \n ", 0.1), ("", "본문", 0.1)):
        monkeypatch.setattr(node, "run_select", lambda query, params=None, _r=row: [_r])
        assert find_relevant_guide("[0.1,0.2,0.3]") == [], f"거부돼야 한다: {row!r}"


def test_find_relevant_guide_skips_blank_row_but_keeps_others(monkeypatch):
    """신규 테스트(d) — 공백 제목 행은 건너뛰고, 통과 게이트를 만족하는 나머지는 반환한다.

    이전 버전(LIMIT 1)은 이 시나리오 자체가 없었다 — top-k라 여러 행 중 일부만 공백인
    경우가 생긴다. 공백 행 하나가 나머지 유효한 행까지 막으면 안 된다.
    """
    rows = [("   ", "공백 제목 본문", 0.1), ("유효한 가이드", "유효 본문", 0.12)]
    monkeypatch.setattr(node, "run_select", lambda query, params=None: rows)
    assert find_relevant_guide("[0.1,0.2,0.3]") == [("유효한 가이드", "유효 본문")]


def test_answer_omits_citation_when_guide_beyond_cutoff(monkeypatch):
    """doc_rag_node 순수 벡터 경로 — 컷오프 초과 가이드는 listings가 있어도 인용을 붙이지 않는다(FR49, 신규 게이트)."""
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [_GUIDE_ROW_BEYOND_CUTOFF], captured)
    result = doc_rag_node("가이드와 의미상 먼 질의")
    assert len(result["listings"]) == 1
    assert "참고:" not in result["answer"]  # 컷오프 초과 — 기존엔 무조건 부착됐었다(회귀 아님, 신규 게이트)


def test_empty_result_returns_fr17_guidance(monkeypatch):
    captured = {}
    # 매물 0건 — 가이드는 있어도 매물이 없으면 FR17 안내.
    _install_fakes(monkeypatch, [], [_GUIDE_ROW], captured)
    result = doc_rag_node("존재하지 않는 무언가")

    assert result["listings"] == []  # 빈 목록
    assert "없어요" in result["answer"]  # FR17 조건 완화/재질문 안내
    # 0건이면 근거 가이드 제목을 굳이 붙이지 않는다(혼선 방지).
    assert "참고:" not in result["answer"]


def test_answer_omits_citation_when_guide_title_is_empty_string(monkeypatch):
    """title이 빈 문자열인 가이드 행은 answer에 인용을 만들지 않는다(end-to-end 확인).

    guide_documents.title은 NOT NULL이지만 빈 문자열 자체는 스키마가 막지 않는다. 이 테스트가
    실제로 태우는 게이트는 **find_relevant_guide의 strip 검사**다(3회차 코드리뷰 정정) —
    호출부는 헬퍼가 이미 걸러 빈 리스트를 돌려주므로 이 행에 도달하지 않는다. 즉 이건
    "인용 자리 방어"가 아니라 "헬퍼 게이트가 사용자에게 보이는 문자열까지 막는다"는 확인이다.
    """
    captured = {}
    _install_fakes(monkeypatch, [_LISTING_ROW], [("", "본문", 0.1)], captured)
    result = doc_rag_node("아무 질의")
    assert len(result["listings"]) == 1
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
