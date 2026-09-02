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


def test_ladder_has_six_steps_with_trim_release_before_generation_release():
    # 2026-08-31 개정: "트림 해제(동일 세대 계열)" 단이 사고 해제(step2)와 세대 해제(step4)
    # 사이(step3)에 끼워졌다 — 사다리가 사고 해제 다음 곧장 세대를 넘어가 다른 세대(예: GN7)를
    # 섞어버리던 실측 오판(P4)을 막는 단이다.
    assert [rung["model"] for rung in market_price.LADDER] == [
        "exact", "exact", "exact", "family", "base", "base",
    ]
    assert market_price.LADDER[3]["desc"] == "트림 해제(동일 세대 계열)"
    assert market_price.LADDER[4]["desc"] == "세대 해제(기본 모델명 매칭)"
    assert market_price.LADDER[3]["accident"] is False  # 사고 해제(step2) 이후 단이므로 계승
    assert market_price.LADDER[3]["fuel"] is True  # 연료는 세대 해제(step4)까지 유지


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


@pytest.mark.parametrize(
    "model, expected",
    [
        ("더 뉴 그랜저 IG 3.3", "더 뉴 그랜저 IG"),  # 후미 배기량 토큰 제거
        ("그랜저 IG 3.0", "그랜저 IG"),
        ("아반떼 CN7 하이브리드", "아반떼 CN7 하이브리드"),  # 후미가 배기량 형태 아님 → 원본 그대로
    ],
)
def test_family_model_extraction(model, expected):
    assert market_price._family_model(model) == expected


def test_verdict_boundaries():
    # q1=1000, q3=2000 리터럴 기대값으로 경계 3곳을 직접 확인(사분위 폴백 기준).
    assert market_price._verdict(999, 1000, 2000) == "저렴"      # q1 미만
    assert market_price._verdict(1000, 1000, 2000) == "적정"     # 정확히 q1
    assert market_price._verdict(1500, 1000, 2000) == "적정"     # 중간
    assert market_price._verdict(2000, 1000, 2000) == "적정"     # 정확히 q3(초과 아님)
    assert market_price._verdict(2001, 1000, 2000) == "높음"     # q3 초과


def test_verdict_by_quantiles_boundaries():
    # 2026-09-03 판정 기준 전환(예측 분포 5단): 경계를 리터럴로 고정한다. 아래쪽 경계(q10·q25)는
    # 미만, 위쪽 경계(q75·q90)는 이하 — 가운데 절반 q25~q75가 닫힌 구간이어야 한다.
    q = {"q10": 1_000, "q25": 2_000, "q50": 2_500, "q75": 3_000, "q90": 4_000}
    assert market_price._verdict_by_quantiles(999, q) == "저렴"          # q10 미만
    assert market_price._verdict_by_quantiles(1_000, q) == "다소 저렴"   # 정확히 q10 → 저렴 아님
    assert market_price._verdict_by_quantiles(1_999, q) == "다소 저렴"
    assert market_price._verdict_by_quantiles(2_000, q) == "적정"        # 정확히 q25(포함)
    assert market_price._verdict_by_quantiles(3_000, q) == "적정"        # 정확히 q75(포함)
    assert market_price._verdict_by_quantiles(3_001, q) == "다소 높음"
    assert market_price._verdict_by_quantiles(4_000, q) == "다소 높음"   # 정확히 q90(포함)
    assert market_price._verdict_by_quantiles(4_001, q) == "높음"        # q90 초과


def test_verdict_and_basis_sample_size_boundary():
    # 2026-08-31 실측 결함(F4, 소표본 과신 판정) 수정 — 비교군 <3건이면 verdict를 보류한다.
    # 경계값을 리터럴로 고정: 0건/2건(보류) vs 3건(판정)을 직접 확인한다.
    stats = {"q1": 1_000, "q3": 2_000}

    assert market_price._verdict_and_basis(0, 1_500, None, None) == (None, None)  # 비교군 자체 없음
    assert market_price._verdict_and_basis(1, 1_500, stats, None) == (None, "표본 부족")
    assert market_price._verdict_and_basis(2, 1_500, stats, None) == (None, "표본 부족")  # 경계: 2건은 여전히 보류
    assert market_price._verdict_and_basis(3, 1_500, stats, None) == ("적정", "사분위")  # 경계: 3건부터 판정
    assert market_price._verdict_and_basis(3, 500, stats, None) == ("저렴", "사분위")


def test_verdict_and_basis_prefers_tabpfn_when_available_and_sample_sufficient():
    # 표본이 MIN_VERDICT_SAMPLE 이상이고 tabpfn 분위수가 있으면 사분위 대신 분위수 5단을 쓴다
    # (2026-09-03 전환). stats(q1/q3=1,000/2,000)만 보면 1,100,000은 '높음'이지만 분위수가 우선.
    stats = {"q1": 1_000, "q3": 2_000}
    q = {"q10": 900_000, "q25": 950_000, "q50": 1_000_000, "q75": 1_050_000, "q90": 1_100_000}
    assert market_price._verdict_and_basis(3, 1_100_000, stats, q) == ("다소 높음", "분위수")  # 정확히 q90
    assert market_price._verdict_and_basis(3, 1_100_001, stats, q) == ("높음", "분위수")
    assert market_price._verdict_and_basis(3, 1_000_000, stats, q) == ("적정", "분위수")
    # 표본 부족 보류(F4)는 분위수가 있어도 먼저 적용된다.
    assert market_price._verdict_and_basis(2, 1_100_001, stats, q) == (None, "표본 부족")


def test_where_clause_differs_by_step_model_vs_ilike():
    target = {
        "id": "target-id",
        "model": "더 뉴 그랜저 IG 3.3",
        "transmission": "자동",
        "year": 2021,
        "mileage": 50_000,
        "fuel": "가솔린",
        "accident_free": True,
    }
    step0_sql, step0_params = market_price._build_where(market_price.LADDER[0], target)
    step3_sql, step3_params = market_price._build_where(market_price.LADDER[3], target)
    step4_sql, step4_params = market_price._build_where(market_price.LADDER[4], target)

    assert market_price.LADDER[0]["model"] == "exact"
    assert market_price.LADDER[3]["model"] == "family"
    assert market_price.LADDER[4]["model"] == "base"
    assert "model = %s" in step0_sql
    assert "model ilike %s" not in step0_sql

    # step3(트림 해제) — 배기량 접두를 뗀 "더 뉴 그랜저 IG"로 시작하는 매물만(접두 매칭, 양쪽
    # % 아님) — GN7 등 다른 세대는 여전히 걸러진다.
    assert "model ilike %s" in step3_sql
    assert "model = %s" not in step3_sql
    assert "더 뉴 그랜저 IG%" in step3_params
    assert "%더 뉴 그랜저 IG%" not in step3_params

    # step4(세대 해제) — 기본 모델명(첫 토큰, 세대 코드 제거) 부분일치 패턴.
    assert "model ilike %s" in step4_sql
    assert "model = %s" not in step4_sql
    assert "%그랜저%" in step4_params


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

    price, quantiles, note = market_price._tabpfn_predict(target, comps)

    assert price is None
    assert quantiles is None
    assert note == "tabpfn 미설치"
