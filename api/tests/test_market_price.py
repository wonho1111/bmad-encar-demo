"""3단계 시세 진단 엔진(app/market_price.py) — DB 없이 도는 단위 테스트.

DB 통합 검증(실제 SELECT 결과·TabPFN 미설치 경로)은 이 파일이 아니라 실행 보고로 남긴다
(api/.venv로 실 DB에 diagnose() 3건을 직접 돌린 결과 — 작업 보고 참조). 여기서는 순수
파이썬 로직(사다리 선언·기본 모델명 추출·verdict 경계·WHERE 생성 분기·tabpfn 미설치 폴백)만
DB 없이 검증한다(다른 test_*.py들의 "DB 불필요 단위 테스트" 관례와 동일).
"""

import builtins
import threading
import time
import types

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


def test_train_rows_query_orders_by_similarity_with_expected_param_order():
    # DW-859: 학습표 SELECT는 최신순(연식 DESC)이 아니라 "대상과 가까운 순"(동일 세대→연료→
    # 연식차→주행거리차, id ASC 타이브레이커)으로 정렬해야 한다 — 실매물 기준 기본 모델명 하나에
    # 수천 건이 걸려, 정렬 없이 최신순으로 자르면 대상과 무관한 연식대만 남는 문제(실측)를 고친
    # 변경이다. SQL 문자열·파라미터 순서를 리터럴로 고정한다(DB 없는 순수 함수 — 실제 정렬
    # 동작은 tests/integration/test_market_price_train_rows_real_db.py가 실DB로 확인한다).
    target = {
        "id": "target-id",
        "model": "그랜저 GN7",
        "transmission": "자동",
        "year": 2024,
        "mileage": 20_000,
        "fuel": "가솔린",
    }
    sql, params = market_price._train_rows_query(target, "그랜저")

    assert (
        "ORDER BY (model = %s) DESC, (fuel = %s) DESC, abs(year - %s) ASC, "
        "abs(mileage - %s) ASC, id ASC"
    ) in sql
    assert "LIMIT 120" in sql
    assert params == [
        "target-id",
        "자동",
        "%그랜저%",
        "그랜저 GN7",
        "가솔린",
        2024,
        20_000,
    ]


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


def test_tabpfn_predict_adds_generation_categorical_feature(monkeypatch):
    # DW-854: 세대(model)를 11번째 칸에 범주로 인코딩해 TabPFNRegressor에 넘기는지 — 진짜
    # tabpfn 없이 가짜 TabPFNRegressor로 fit()/predict() 호출 인자를 그대로 기록해 검증한다
    # (위 test_tabpfn_import_failure_falls_back_to_none_with_note와 같은 __import__ 몽키패치
    # 패턴, 이번엔 ImportError 대신 가짜 모듈을 돌려준다).
    real_import = builtins.__import__

    class _FakeTabPFNRegressor:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs

        def fit(self, x, y):
            self.fit_x = x
            self.fit_y = y

        def predict(self, x, **kwargs):
            self.predict_x = x
            self.predict_kwargs = kwargs
            return {
                "mean": [20_000_000],
                "quantiles": [
                    [v] for v in (18_000_000, 19_000_000, 20_000_000, 21_000_000, 22_000_000)
                ],
            }

    fake_module = types.ModuleType("tabpfn")
    fake_module.TabPFNRegressor = _FakeTabPFNRegressor

    def _fake_import(name, *args, **kwargs):
        if name == "tabpfn":
            return fake_module
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    monkeypatch.setattr(market_price, "_TABPFN_MODEL", None)

    def _row(model, i):
        return {
            "id": f"{model}-{i}",
            "model": model,
            "year": 2020 + i,
            "mileage": 50_000 - i * 1_000,
            "price": 15_000_000,
            "displacement": 1_600,
            "fuel": "가솔린",
            "options": [],
            "accident_free": True,
        }

    train_rows = [_row("그랜저 GN7", i) for i in range(6)] + [
        _row("더 뉴 그랜저 IG", i) for i in range(6)
    ]
    target = {
        "model": "그랜저 GN7",
        "year": 2024,
        "mileage": 20_000,
        "displacement": 1_600,
        "fuel": "가솔린",
        "options": [],
        "accident_free": True,
    }

    price, quantiles, note = market_price._tabpfn_predict(target, train_rows)

    model_obj = market_price._TABPFN_MODEL
    assert model_obj.init_kwargs["categorical_features_indices"] == [10]

    fit_x = model_obj.fit_x
    assert all(len(row) == 11 for row in fit_x)
    predict_x = model_obj.predict_x
    assert len(predict_x) == 1
    assert len(predict_x[0]) == 11

    # 같은 모델은 같은 코드를 공유하고, 다른 모델은 다른 코드를 받는다.
    gn7_codes = {row[10] for row in fit_x[:6]}
    ig_codes = {row[10] for row in fit_x[6:]}
    assert len(gn7_codes) == 1
    assert len(ig_codes) == 1
    assert gn7_codes != ig_codes

    # 대상(그랜저 GN7)의 코드는 학습표의 같은 모델(그랜저 GN7) 코드와 같아야 한다.
    assert predict_x[0][10] == next(iter(gn7_codes))

    assert price is not None
    assert quantiles is not None


def test_tabpfn_predict_serializes_concurrent_requests_via_lock(monkeypatch):
    # DW-856: 전역 _TABPFN_MODEL은 요청마다 fit()한 뒤 그 상태로 predict()하는 공유 객체라,
    # 두 요청이 겹치면 A가 fit()한 학습표를 B의 fit()이 덮어쓴 뒤 A가 predict()할 수 있다
    # (운영에서 NotFittedError·가중치 FileNotFoundError로 실측). 진짜 tabpfn 없이, fit()이
    # 학습표(y)를 공유 객체에 저장하고 predict()가 "느린 추론"을 흉내 내려 잠깐 sleep한 뒤
    # 그 시점에 저장돼 있는 y로 값을 만드는 가짜 모델을 넣어, 두 스레드가 서로 다른 학습표로
    # 거의 동시에 _tabpfn_predict를 호출했을 때 각자 자기 학습표 기준 값을 받는지 확인한다.
    real_import = builtins.__import__

    class _FakeTabPFNModel:
        def __init__(self):
            self.trained_on = None

        def fit(self, x, y):
            self.trained_on = list(y)

        def predict(self, x, **kwargs):
            time.sleep(0.2)  # 그 사이 다른 스레드의 fit()이 끼어들 수 있는 창
            value = sum(self.trained_on) / len(self.trained_on)
            return {"mean": [value], "quantiles": [[value]] * 5}

    fake_module = types.ModuleType("tabpfn")
    fake_module.TabPFNRegressor = lambda **kwargs: _FakeTabPFNModel()

    def _fake_import(name, *args, **kwargs):
        if name == "tabpfn":
            return fake_module
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    monkeypatch.setattr(market_price, "_TABPFN_MODEL", None)

    def _row(model, i, price):
        return {
            "id": f"{model}-{i}",
            "model": model,
            "year": 2020 + i,
            "mileage": 50_000 - i * 1_000,
            "price": price,
            "displacement": 1_600,
            "fuel": "가솔린",
            "options": [],
            "accident_free": True,
        }

    train_rows_a = [_row("아반떼", i, 10_000_000) for i in range(10)]
    target_a = _row("아반떼", 0, 10_000_000)

    train_rows_b = [_row("쏘나타", i, 50_000_000) for i in range(10)]
    target_b = _row("쏘나타", 0, 50_000_000)

    results = {}

    def _call(key, target, train_rows, delay):
        time.sleep(delay)
        price, _quantiles, _note = market_price._tabpfn_predict(target, train_rows)
        results[key] = price

    thread_a = threading.Thread(target=_call, args=("a", target_a, train_rows_a, 0.0))
    thread_b = threading.Thread(target=_call, args=("b", target_b, train_rows_b, 0.05))

    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    # 락이 있으면 A는 자기 학습표(1천만) 기준, B는 자기 학습표(5천만) 기준 값을 각각 받는다.
    # 락이 없으면 B의 fit()이 A의 predict() sleep 중에 전역 상태를 덮어써 A도 5천만을 받는다.
    assert results["a"] == 10_000_000
    assert results["b"] == 50_000_000
