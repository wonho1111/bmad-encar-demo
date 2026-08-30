"""
TabPFN 회귀(적정가 예측 스모크) CPU 실측 스크립트.
합성 중고차 데이터 200행 -> 160 fit / 40 predict.
결과는 bench/results_tabpfn.json 에 저장.
"""
import json
import os
import time
import traceback

import numpy as np
import psutil

OUT_PATH = os.path.join(os.path.dirname(__file__), "results_tabpfn.json")
SEED = 42


def rss_mb():
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def make_synthetic_data(n=200, seed=SEED):
    rng = np.random.RandomState(seed)
    year = rng.randint(2015, 2025, size=n)  # 연식
    mileage = rng.randint(10000, 150001, size=n)  # 주행거리(km)
    displacement = rng.randint(1000, 3501, size=n)  # 배기량(cc)
    fuel = rng.choice(["gasoline", "diesel", "hybrid"], size=n)  # 연료
    fuel_gasoline = (fuel == "gasoline").astype(int)
    fuel_diesel = (fuel == "diesel").astype(int)
    fuel_hybrid = (fuel == "hybrid").astype(int)
    n_options = rng.randint(0, 9, size=n)  # 옵션수
    no_accident = rng.randint(0, 2, size=n)  # 무사고 0/1

    base_price = 35_000_000  # 3500만원
    year_depreciation = (2024 - year) * 1_500_000  # 연식감가 (1년당 150만원 가정)
    mileage_depreciation = mileage * 40  # 주행감가 (1km당 40원 가정)
    option_premium = n_options * 300_000  # 옵션당 30만원 웃돈
    accident_premium = no_accident * 2_000_000  # 무사고 200만원 웃돈

    price = (
        base_price
        - year_depreciation
        - mileage_depreciation
        + option_premium
        + accident_premium
    )
    noise = rng.normal(0, 0.05, size=n) * price
    price = np.round(price + noise).astype(int)

    X = np.column_stack([
        year, mileage, displacement,
        fuel_gasoline, fuel_diesel, fuel_hybrid,
        n_options, no_accident,
    ]).astype(float)
    y = price.astype(float)
    return X, y


def main():
    result = {}
    rss_start = rss_mb()
    result["rss_start_mb"] = round(rss_start, 1)

    try:
        from tabpfn import TabPFNRegressor
    except Exception as e:
        result["error_stage"] = "import tabpfn"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    t0 = time.time()
    try:
        reg = TabPFNRegressor(device="cpu")
    except Exception as e:
        result["error_stage"] = "construct TabPFNRegressor"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return
    load_time = time.time() - t0
    result["load_time_sec"] = round(load_time, 3)
    result["rss_after_construct_mb"] = round(rss_mb(), 1)

    X, y = make_synthetic_data(200, SEED)
    X_train, y_train = X[:160], y[:160]
    X_test, y_test = X[160:], y[160:]

    try:
        t0 = time.time()
        reg.fit(X_train, y_train)
        fit_time = time.time() - t0
        result["fit_time_sec"] = round(fit_time, 3)
        result["rss_after_fit_mb"] = round(rss_mb(), 1)

        t0 = time.time()
        y_pred = reg.predict(X_test)
        predict_time = time.time() - t0
        result["predict_time_sec"] = round(predict_time, 3)
        result["rss_peak_mb"] = round(rss_mb(), 1)

        from sklearn.metrics import r2_score, mean_absolute_error
        r2 = r2_score(y_test, y_pred)
        mae_won = mean_absolute_error(y_test, y_pred)
        mae_man_won = mae_won / 10000.0

        result["r2"] = round(float(r2), 4)
        result["mae_man_won"] = round(float(mae_man_won), 2)
        result["y_test_sample_won"] = [int(v) for v in y_test[:5]]
        result["y_pred_sample_won"] = [round(float(v), 1) for v in y_pred[:5]]
    except Exception as e:
        result["error_stage"] = "fit/predict"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[info] done, results at {OUT_PATH}")


if __name__ == "__main__":
    main()
