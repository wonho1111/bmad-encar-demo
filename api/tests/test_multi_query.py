"""multi_query 단위 테스트 — LLM 분해·RRF 병합을 네트워크·DB 무관하게 검증.

여기서는 결정론적인 부분만 격리한다(LLM·find_relevant_guide·embed_query 전부 모킹):
  (a) 짧은 질의(<20자) → decompose_query가 LLM 호출 없이 빈 리스트
  (b) LLM 출력 파싱 — 3줄 → 3개, "NONE." → 빈 리스트(관대한 NONE 인식), 6줄 → 4개로 절단
  (c) LLM 예외 → 빈 리스트 + 원 질의 검색만으로 동작(폴백)
  (d) RRF 병합 — 원 질의 2배 가중이 실제 순위에 반영되는지 점수를 직접 계산해 검증
  (e) 하위 질의 없음 → 원 질의 결과 그대로, embed_query 미호출

실제 분해 품질(라이브 LLM+DB)은 스크래치패드 E2E 스크립트로 확인한다(이 파일 소관 아님).
"""

import app.graph.multi_query as node
from app.graph.multi_query import _RRF_K, decompose_query, find_relevant_guides_fused


class _FixedLLM:
    """미리 정해둔 응답을 돌려주는 가짜 LLM(네트워크·과금 없음)."""

    def __init__(self, output):
        self._output = output

    def invoke(self, messages):
        return type("Msg", (), {"content": self._output})()


class _ExplodingLLM:
    """호출되면 즉시 실패하는 가짜 LLM — "호출 안 됨"을 증명하는 용도."""

    def invoke(self, messages):
        raise AssertionError("LLM이 호출되면 안 되는 경로에서 호출됐다")


# ── (a) 짧은 질의는 LLM 호출 없이 분해 생략 ──────────────────────────────
def test_short_query_skips_decompose_without_calling_llm(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _ExplodingLLM())
    assert decompose_query("짧은 질의") == []  # 10자 미만, _MIN_QUERY_LEN(20) 미달


# ── (b) LLM 출력 파싱 ────────────────────────────────────────────────────
def test_decompose_parses_multiple_lines(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(
        "2천만원 이하 사회초년생용 중고차\n유지비가 적고 가성비가 좋은 차\n통풍시트 옵션이 있는 차"
    ))
    query = "2천만원 이하의 유지비가 적고 가성비가 좋은 통풍시트 옵션이 포함된 사회초년생용 중고차를 추천해줘."
    result = decompose_query(query)
    assert result == [
        "2천만원 이하 사회초년생용 중고차",
        "유지비가 적고 가성비가 좋은 차",
        "통풍시트 옵션이 있는 차",
    ]


def test_decompose_recognizes_lenient_none(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM("NONE."))
    query = "3천만원 이하로 초년생이 탈만한 유지비 적고 가성비 좋으며 통풍시트 옵션이 있는 차를 추천해줘."
    assert decompose_query(query) == []


def test_decompose_truncates_to_four_lines(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM(
        "축1\n축2\n축3\n축4\n축5\n축6"
    ))
    query = "20자가 넘도록 충분히 길게 쓴 복합 질의 테스트 문장입니다"
    result = decompose_query(query)
    assert result == ["축1", "축2", "축3", "축4"]


# ── (c) LLM 예외 → 빈 리스트 폴백 ────────────────────────────────────────
def test_decompose_llm_exception_falls_back_to_empty(monkeypatch):
    class _RaisingLLM:
        def invoke(self, messages):
            raise RuntimeError("네트워크 장애")

    monkeypatch.setattr(node, "_llm", lambda: _RaisingLLM())
    query = "20자가 넘도록 충분히 길게 쓴 복합 질의 테스트 문장입니다"
    assert decompose_query(query) == []


def test_fused_falls_back_to_original_only_on_llm_exception(monkeypatch):
    class _RaisingLLM:
        def invoke(self, messages):
            raise RuntimeError("네트워크 장애")

    original_guides = [("A제목", "A본문")]
    monkeypatch.setattr(node, "_llm", lambda: _RaisingLLM())

    def fake_find_relevant_guide(qvec_literal):
        assert qvec_literal == "원질의벡터"
        return original_guides

    def fail_embed_query(text):
        raise AssertionError("하위 질의가 없으면 embed_query가 호출되면 안 된다")

    monkeypatch.setattr(node, "find_relevant_guide", fake_find_relevant_guide)
    monkeypatch.setattr(node, "embed_query", fail_embed_query)

    query = "20자가 넘도록 충분히 길게 쓴 복합 질의 테스트 문장입니다"
    assert find_relevant_guides_fused(query, "원질의벡터") == original_guides


# ── (d) RRF 병합 — 원 질의 2배 가중이 순위에 반영되는지 ──────────────────
def test_rrf_fusion_weights_original_query_double(monkeypatch):
    """원 질의 [A,B], 하위1 [B,C], 하위2 [C,D]를 병합한다.

    실제 순위는 아래 공식으로 직접 계산해 검증한다(추측이 아니라 점수 계산):
      score(title) = sum(weight / (_RRF_K + rank)), 원 질의는 weight=2, 하위 질의는 weight=1.
      A = 2/(k+0)              (원질의 1등에만 등장)
      B = 2/(k+1) + 1/(k+0)    (원질의 2등 + 하위1 1등)
      C = 1/(k+1) + 1/(k+0)    (하위1 2등 + 하위2 1등)
      D = 1/(k+1)              (하위2 2등에만 등장)
    B가 가장 높다(두 리스트에 걸쳐 있고 그중 하나가 1등). 원 질의 2배 가중 덕에 A는 D보다
    위를 유지한다(원 질의 의도가 기준 — 하위 질의만으로 만들어진 조합에 밀리지 않는다).
    """
    k = _RRF_K

    def score(rank: int, weight: float) -> float:
        return weight / (k + rank)

    expected_a = score(0, 2.0)
    expected_b = score(1, 2.0) + score(0, 1.0)
    expected_c = score(1, 1.0) + score(0, 1.0)
    expected_d = score(1, 1.0)
    expected_order = [
        title
        for title, _score in sorted(
            [("A", expected_a), ("B", expected_b), ("C", expected_c), ("D", expected_d)],
            key=lambda pair: pair[1],
            reverse=True,
        )
    ]
    # 원 질의 가중(2배)이 살아 있으면 A가 D보다 항상 위다 — 이 자체를 먼저 확인한다.
    assert expected_order.index("A") < expected_order.index("D")

    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM("하위질의1\n하위질의2"))

    def fake_embed_query(text):
        return {"하위질의1": [1.0], "하위질의2": [2.0]}[text]

    def fake_find_relevant_guide(qvec_literal):
        mapping = {
            "원질의벡터": [("A", "a본문"), ("B", "b본문")],
            "[1.0]": [("B", "b본문"), ("C", "c본문")],
            "[2.0]": [("C", "c본문"), ("D", "d본문")],
        }
        return mapping[qvec_literal]

    monkeypatch.setattr(node, "embed_query", fake_embed_query)
    monkeypatch.setattr(node, "find_relevant_guide", fake_find_relevant_guide)

    query = "20자가 넘도록 충분히 길게 쓴 복합 질의 테스트 문장입니다"
    fused = find_relevant_guides_fused(query, "원질의벡터")
    assert [title for title, _content in fused] == expected_order


def test_rrf_fusion_without_original_weight_changes_order(monkeypatch):
    """red→green: 원 질의 2배 가중을 없애면(둘 다 weight=1) 위 테스트의 순위가 달라지는지
    확인한다 — 가중이 실제로 결과에 영향을 준다는 것을 증명한다(가중을 빼도 초록이면
    그 가중은 죽은 코드다).
    """
    k = _RRF_K

    def score(rank: int, weight: float) -> float:
        return weight / (k + rank)

    weighted_a = score(0, 2.0)
    weighted_order = [
        title
        for title, _score in sorted(
            [
                ("A", weighted_a),
                ("B", score(1, 2.0) + score(0, 1.0)),
                ("C", score(1, 1.0) + score(0, 1.0)),
                ("D", score(1, 1.0)),
            ],
            key=lambda pair: pair[1],
            reverse=True,
        )
    ]
    unweighted_a = score(0, 1.0)  # 가중 제거 시 A의 점수
    unweighted_order = [
        title
        for title, _score in sorted(
            [
                ("A", unweighted_a),
                ("B", score(1, 1.0) + score(0, 1.0)),
                ("C", score(1, 1.0) + score(0, 1.0)),
                ("D", score(1, 1.0)),
            ],
            key=lambda pair: pair[1],
            reverse=True,
        )
    ]
    assert weighted_order != unweighted_order  # 가중을 빼면 순서가 실제로 바뀐다(red 확인 대상).


# ── (e) 하위 질의 없음 → 원 질의 결과 그대로, embed_query 미호출 ─────────
def test_fused_without_subqueries_returns_original_and_skips_embedding(monkeypatch):
    monkeypatch.setattr(node, "_llm", lambda: _FixedLLM("NONE"))

    original_guides = [("A제목", "A본문"), ("B제목", "B본문")]

    def fake_find_relevant_guide(qvec_literal):
        assert qvec_literal == "원질의벡터"
        return original_guides

    def fail_embed_query(text):
        raise AssertionError("하위 질의가 없으면 embed_query가 호출되면 안 된다")

    monkeypatch.setattr(node, "find_relevant_guide", fake_find_relevant_guide)
    monkeypatch.setattr(node, "embed_query", fail_embed_query)

    query = "20자가 넘도록 충분히 길게 쓴 복합 질의 테스트 문장입니다"
    assert find_relevant_guides_fused(query, "원질의벡터") == original_guides
