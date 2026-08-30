"""3단계 시세 진단 엔진(app/market_price.py) — DB 없이 도는 단위 테스트.

DB 통합 검증(실제 SELECT 결과·TabPFN 미설치 경로)은 이 파일이 아니라 실행 보고로 남긴다
(api/.venv로 실 DB에 diagnose() 3건을 직접 돌린 결과 — 작업 보고 참조). 여기서는 순수
파이썬 로직(사다리 선언·기본 모델명 추출·verdict 경계·WHERE 생성 분기·tabpfn 미설치 폴백)만
DB 없이 검증한다(다른 test_*.py들의 "DB 불필요 단위 테스트" 관례와 동일).
"""

import builtins

import pytest

from app import market_price


def test_ladder_steps_consecutive_and_first_step_is_exact_model():
    steps = [rung["step"] for rung in market_price.LADDER]
    assert steps == list(range(len(steps))), "사다리 step 번호는 0부터 연속이어야 한다"
    assert market_price.MIN_SAMPLE > 0
    assert market_price.LADDER[0]["model"] == "exact", "첫 단은 세대 동일(exact) 비교여야 한다(v3 확정 원칙)"


@pytest.mark.parametrize(
    "model, expected",
    [
        ("더 뉴 그랜저 IG", "그랜저"),
        ("올 뉴 쏘렌토", "쏘렌토"),
        ("아반떼 CN7 하이브리드", "아반떼"),
    ],
)
def test_base_model_extraction(model, expected):
    assert market_price._base_model(model) == expected


def test_verdict_boundaries():
    # q1=1000, q3=2000 리터럴 기대값으로 경계 3곳을 직접 확인.
    assert market_price._verdict(999, 1000, 2000) == "저렴"      # q1 미만
    assert market_price._verdict(1000, 1000, 2000) == "적정"     # 정확히 q1
    assert market_price._verdict(1500, 1000, 2000) == "적정"     # 중간
    assert market_price._verdict(2000, 1000, 2000) == "적정"     # 정확히 q3(초과 아님)
    assert market_price._verdict(2001, 1000, 2000) == "높음"     # q3 초과


def test_where_clause_differs_by_step_model_vs_ilike():
    target = {
        "id": "target-id",
        "model": "더 뉴 그랜저 IG",
        "transmission": "자동",
        "year": 2021,
        "mileage": 50_000,
        "fuel": "가솔린",
        "accident_free": True,
    }
    step0_sql, step0_params = market_price._build_where(market_price.LADDER[0], target)
    step3_sql, step3_params = market_price._build_where(market_price.LADDER[3], target)

    assert market_price.LADDER[0]["model"] == "exact"
    assert market_price.LADDER[3]["model"] == "base"
    assert "model = %s" in step0_sql
    assert "model ilike %s" not in step0_sql
    assert "model ilike %s" in step3_sql
    assert "model = %s" not in step3_sql
    # base 단은 기본 모델명 부분일치 패턴을 파라미터로 넘긴다(세대 코드 제거 확인).
    assert "%그랜저%" in step3_params


def test_tabpfn_import_failure_falls_back_to_none_with_note(monkeypatch):
    # tabpfn 미설치(또는 import 실패) 경로를 강제로 재현 — 통계 계산과 별개로 엔진이 죽지 않아야 한다.
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "tabpfn":
            raise ImportError("tabpfn not installed (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    comps = [
        {
            "id": f"comp-{i}",
            "model": "아반떼",
            "year": 2020,
            "mileage": 50_000,
            "price": 15_000_000,
            "displacement": 1_600,
            "fuel": "가솔린",
            "options": [],
            "accident_free": True,
        }
        for i in range(10)  # >= _TABPFN_MIN_COMPS
    ]
    target = {
        "year": 2020,
        "mileage": 50_000,
        "displacement": 1_600,
        "fuel": "가솔린",
        "options": [],
        "accident_free": True,
    }

    price, note = market_price._tabpfn_predict(target, comps)

    assert price is None
    assert note == "tabpfn 미설치"
