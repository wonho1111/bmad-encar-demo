# -*- coding: utf-8 -*-
"""api/scripts/seed_depreciation.py(v3, 엔카 실측 17그룹 고정건수)의 순수 규칙 함수 단위 테스트
— DB 접속 없음.

기대값은 전부 리터럴로 직접 계산해 넣는다(피검사 코드에서 재계산 금지 — 자기일관 단언이면
규칙 상수를 바꿔도 항상 통과해 아무것도 못 잡는다).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_depreciation import (  # noqa: E402
    GROUPS,
    GROUP_BY_KEY,
    FLOOR_PRICE,
    N_PER_MODEL,
    compute_price,
    generate_all,
)

AVANTE_CN7 = GROUP_BY_KEY[("아반떼 CN7", "가솔린")]
GRANDEUR_NEW_IG = GROUP_BY_KEY[("더 뉴 그랜저 IG", "가솔린")]


def test_mileage_increase_decreases_price_same_conditions():
    kwargs = dict(year=2021, n_options=3, accident_status="무사고", family="아반떼", noise=1.0)
    p_low = compute_price(AVANTE_CN7, mileage=30_000, **kwargs)
    p_high = compute_price(AVANTE_CN7, mileage=90_000, **kwargs)
    assert p_high < p_low


def test_year_decrease_decreases_price_same_conditions():
    # 같은 그룹(더 뉴 그랜저 IG, 연식범위 2020~2022) 안에서 mileage를 고정하고 연식만 낮춘다.
    kwargs = dict(mileage=50_000, n_options=3, accident_status="무사고", family="그랜저", noise=1.0)
    p_newer = compute_price(GRANDEUR_NEW_IG, year=2022, **kwargs)
    p_older = compute_price(GRANDEUR_NEW_IG, year=2020, **kwargs)
    assert p_older < p_newer


def test_accident_status_reduces_price_relative_to_accident_free():
    # ACCIDENT_MULT(무사고1.0 > 단순교환0.95 > 사고0.88)의 순서를 직접 겨냥한 테스트 —
    # 나머지 테스트는 전부 accident_status="무사고"로 고정해서 뽑기 때문에 사고 배율 상수가
    # 깨져도(예: '사고' 배율이 1.0보다 커짐) 아무도 못 잡는다는 걸 실측으로 확인하고 추가함.
    kwargs = dict(year=2021, mileage=50_000, n_options=3, family="아반떼", noise=1.0)
    p_clean = compute_price(AVANTE_CN7, accident_status="무사고", **kwargs)
    p_minor = compute_price(AVANTE_CN7, accident_status="단순교환", **kwargs)
    p_accident = compute_price(AVANTE_CN7, accident_status="사고", **kwargs)
    assert p_accident < p_minor < p_clean


def test_price_floor_guaranteed_for_extreme_input():
    # 앵커(2022)에서 아주 먼 연식(1990)을 넣어 raw를 큰 폭으로 음수로 만든다 — 실제 생성 시
    # sample_year는 그룹 연식범위 밖을 뽑지 않지만, compute_price 자체는 순수 함수라 임의
    # 연식을 넣을 수 있다(하한 클램프가 "무슨 입력이 와도" 작동하는지 증명하는 목적).
    # 수기 계산: raw = 1850 - (2022-1990)*180 = 1850 - 5760 = -3910 → 만원 단위로도 충분히
    #   음수라 이후 주행·옵션·사고 보정을 더해도 하한(250만원)에 걸린다.
    price = compute_price(
        AVANTE_CN7, year=1990, mileage=100_000, n_options=3,
        accident_status="무사고", family="아반떼", noise=1.0,
    )
    assert price == FLOOR_PRICE


def test_generation_is_deterministic_for_fixed_seed():
    rows1 = generate_all(20260830)
    rows2 = generate_all(20260830)
    assert rows1 == rows2


def test_all_generated_options_are_within_pool():
    from scripts.seed_depreciation import OPTIONS_POOL

    rows = generate_all(20260830)
    assert len(rows) == 3 * N_PER_MODEL
    for row in rows:
        for family_name in ("아반떼", "쏘렌토", "그랜저"):
            if family_name in row["model"]:
                pool = set(OPTIONS_POOL[family_name])
                assert set(row["options"]).issubset(pool), (row["model"], row["options"])
                break
        else:
            raise AssertionError(f"알 수 없는 모델명: {row['model']}")


def test_all_generated_rows_stay_within_their_group_year_range():
    rows = generate_all(20260830)
    for row in rows:
        group = GROUP_BY_KEY.get((row["model"], row["fuel"]))
        assert group is not None, (row["model"], row["fuel"])
        lo, hi = group["year_range"]
        assert lo <= row["year"] <= hi, (row["model"], row["fuel"], row["year"], group["year_range"])


def test_group_table_matches_v3_spec_structure():
    """docs/ai-advanced/02-seed-price-calibration.md "v3 최종 확정" 표를 파싱해서 비교하는 게
    아니라(그러면 파서가 또 하나의 진실 소스가 되어버린다), 그 표가 지켜야 할 구조적 불변식만
    검사한다: 그룹 17개, 모델당 건수 합 50, (model_name, fuel) 키 유일(중복 시 GROUP_BY_KEY가
    조용히 그룹 하나를 덮어써 생성 건수가 틀어진다), 그룹 내부 연식범위가 뒤집히지 않음."""
    all_groups = [g for family in GROUPS.values() for g in family]
    assert len(all_groups) == 17

    for family in ("아반떼", "쏘렌토", "그랜저"):
        assert sum(g["count"] for g in GROUPS[family]) == N_PER_MODEL

    keys = [(g["model_name"], g["fuel"]) for g in all_groups]
    assert len(keys) == len(set(keys)), "중복된 (model_name, fuel) 키가 있음 — GROUP_BY_KEY가 깨짐"

    for g in all_groups:
        lo, hi = g["year_range"]
        assert lo <= hi, (g["model_name"], g["year_range"])
