"""embeddings.py 순수 로직 단위 테스트 — 외부 네트워크(Gemini) 불필요한 부분만 검증.

실제 임베딩 호출(차원 768·norm 1.0)은 라이브 backfill에서 검증한다(외부 키 의존).
여기서는 L2 정규화와 차원 검증 로직의 정확성만 격리해 테스트한다.
"""

import math

import pytest

from app.embeddings import _check_dim, _l2_normalize
from app.config import settings


def test_l2_normalize_makes_unit_vector():
    vec = [3.0, 4.0]  # 길이 5
    out = _l2_normalize(vec)
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0, rel_tol=1e-9)
    assert math.isclose(out[0], 0.6) and math.isclose(out[1], 0.8)


def test_l2_normalize_zero_vector_unchanged():
    # 0 벡터는 나눗셈 불가 → 그대로 반환(division by zero 방지)
    assert _l2_normalize([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


def test_check_dim_accepts_correct_dimension():
    vec = [0.1] * settings.gemini_embedding_dim  # 768
    assert _check_dim(vec) is vec


def test_check_dim_rejects_wrong_dimension():
    # 3072(기본 차원) 등 768이 아닌 경우 fail-loud
    with pytest.raises(RuntimeError, match="임베딩 차원 불일치"):
        _check_dim([0.1] * 3072)


def test_check_dim_rejects_non_finite_values():
    # NaN/Inf 성분이 섞이면 fail-loud — 무효 pgvector 리터럴로 번지기 전에 막는다.
    dim = settings.gemini_embedding_dim
    for bad in (float("nan"), float("inf"), float("-inf")):
        vec = [0.1] * (dim - 1) + [bad]
        with pytest.raises(RuntimeError, match="비유한 값"):
            _check_dim(vec)
