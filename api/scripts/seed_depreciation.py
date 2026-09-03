# -*- coding: utf-8 -*-
"""감가 규칙 v3(최종) 기반 시드 생성기 — 아반떼·쏘렌토·그랜저 150건(각 50건) + 기존 매물 이탈 진단.

v3로 교체한 이유(사용자 최종 승인, docs/ai-advanced/02-seed-price-calibration.md "v3 최종 확정" 절):
  v2는 그룹을 두긴 했지만 세대명에 F/L(페이스리프트) 표기를 안 쓰고 그룹 선택도 비중 랜덤이라
  세대 간 경계가 흐렸다. v3는 엔카 실측 표를 **그대로** 17개 그룹으로 옮기고(모델명은 엔카식
  자연 명칭 — "더 뉴 그랜저 IG"처럼), 그룹별 건수를 표에 박힌 값으로 고정한다(랜덤 비중 아님).
  아반떼 MD(연식범위가 시드 밖)·그랜저 LPG·쏘렌토 4세대 가솔린 전기형·GN7 3.5는 표본 부족/편향으로
  제외(문서에 명시).

하는 일 (--preview, 기본값):
  1) 그룹(모델·세대·파워트레인)마다 고정 건수만큼, 그룹 연식범위 내에서 균등 랜덤 연식으로
     생성한다(3개 모델 각 50건, 총 150건). 가격 공식은 v2와 동일:
     raw   = anchor_price − (anchor_year − year) × year_dep      (그룹 내 연감가)
     raw  -= (mileage − 13000×(2026−year)) × km_per              (차령 기준주행 대비 보정)
     raw  += len(options) × opt_prem
     raw  ×= accident_mult                                        (무사고1.0/단순교환0.95/사고0.88)
     price = round_만원(raw × noise), noise=U(0.95,1.05), 하한 250만원
  2) INSERT문을 _bmad-output/implementation-artifacts/seed-depreciation.sql로 쓴다(DB 미접속).
  3) DB에서 기존 아반떼·쏘렌토·그랜저 매물을 SELECT만 해서(쓰기 없음) 같은 v3 그룹 규칙으로
     "규칙가"를 계산하고, |실제가-규칙가|/규칙가 > 0.25인 행을 이탈 목록으로 뽑아
     seed-depreciation-adjustments.sql(UPDATE문)로 쓴다.
  4) 통계·검증 결과·그룹별 캘리브레이션 경고·샘플·이탈 목록을 콘솔에 출력한다.

--apply / --apply-adjustments: 구현만 하고 이번 세션에서는 실행하지 않는다(검수 후 상위 세션이
  실행). apply_listings_expansion.py와 동일한 접속 패턴(safe_conninfo, psycopg, 연결 롤=postgres).

v3에서 새로 판단해야 했던 지점(스펙에 없어 임의로 정한 것 — 보고에도 명시):
  · 더 뉴 아반떼 AD(18~20, 가솔린)와 아반떼 CN7(20~22, 가솔린)이 2020년에 겹친다(페이스리프트→
    풀체인지 전환 연도라 문서 표 자체가 겹치게 확정했다 — 실제 엔카에도 같은 해에 두 세대가
    같이 팔림). 기존 매물처럼 세대 표기가 없는 행(예: "아반떼" 2020년식 가솔린)은 이 두 그룹
    중 하나를 골라야 하는데, model 문자열이 어느 쪽과도 정확히 안 맞으면 **건수가 더 많은(더
    흔한) 그룹**을 기본값으로 쓴다(resolve_group 4단계, 이탈 리포트에 "모호 매핑"으로 표시).
    그랜저 IG/IG 3.0, 더 뉴 그랜저 IG/3.3처럼 같은 연식범위·같은 연료인 트림 쌍도 동일 로직.
  · 기존 매물의 accident_status가 NULL인 행은 accident_free로 대체 추정한다(true→'무사고',
    false→'사고') — 이번 데이터셋은 전부 채워져 있어 실제로는 해당 없음(v1·v2와 동일 가정).
  · 캘리브레이션 기준값은 v2처럼 별도 "실측 중앙값" 표를 또 코드에 옮기지 않고, GROUPS 테이블의
    앵커가·연감가로 그 그룹의 "중간연식" 기대가를 계산해 비교한다(정본은 GROUPS 하나 — 별도
    참고표를 두면 둘이 따로 놀 위험이 생긴다). 이 기대가는 주행·옵션·사고·노이즈 보정 전 값이라
    생성 중앙값과는 원래 어느 정도 차이가 날 수 있어 경고 임계값(±20%)은 참고용이다.
  · CURRENT_YEAR=2026(차령·기준주행 계산 기준 "올해")은 스펙 리터럴 그대로 고정(v2와 동일).
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import io
from pathlib import Path
from urllib.parse import quote

API_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = API_ROOT.parent
sys.path.insert(0, str(API_ROOT))
if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SQL_DIR = REPO_ROOT / "_bmad-output" / "implementation-artifacts"
SEED_SQL_PATH = SQL_DIR / "seed-depreciation.sql"
ADJUST_SQL_PATH = SQL_DIR / "seed-depreciation-adjustments.sql"

SEED = 20260830
CURRENT_YEAR = 2026  # 차령·기준주행(km_ref) 계산 기준 "올해" — 설계 확정값, 임의 변경 금지
FLOOR_PRICE = 2_500_000
N_PER_MODEL = 50
DEVIATION_THRESHOLD = 0.25
CALIBRATION_WARN_THRESHOLD = 0.20

SELLER_IDS = [
    "12dfba00-2544-45f4-8ffe-bdeb32229b97",
    "0f937a74-48ee-4e3a-9e78-4a3d85645727",
    "c19a85e7-6e23-432f-aa1c-efc57f1782af",
]

# ── DB CHECK 허용값 (supabase/migrations/0002_listings.sql, 0017_listings_trust_attributes.sql
#    단일 출처와 동일 — drift 감시용) ─────────────────────────────────────────────
ALLOWED_FUEL = {"가솔린", "디젤", "하이브리드", "전기", "LPG"}
ALLOWED_COLOR = {"흰색", "검정", "회색", "은색", "파랑", "빨강", "갈색", "녹색", "기타"}
ALLOWED_REGION = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
}
ALLOWED_BODY_TYPE = {
    "경차", "소형차", "준중형차", "중형차", "대형차", "스포츠카",
    "SUV", "RV", "경승합차", "승합차", "화물차", "기타",
}
ALLOWED_ACCIDENT_STATUS = {"무사고", "단순교환", "사고"}

# ── 모델별 고정값 ────────────────────────────────────────────────────────────
MANUFACTURER = {"아반떼": "현대", "쏘렌토": "기아", "그랜저": "현대"}
BODY_TYPE = {"아반떼": "준중형차", "쏘렌토": "SUV", "그랜저": "대형차"}
KM_PER = {"아반떼": 0.0008, "쏘렌토": 0.0010, "그랜저": 0.0010}  # 만원/km (v2 유지)
OPT_PREM = {"아반떼": 8, "쏘렌토": 12, "그랜저": 12}  # 만원/옵션 1개 (v2 유지)
ACCIDENT_MULT = {"무사고": 1.0, "단순교환": 0.95, "사고": 0.88}  # v2 유지

OPTIONS_POOL = {
    "아반떼": [
        "후방카메라", "내비게이션", "열선시트", "블루투스", "스마트키",
        "크루즈컨트롤", "애플카플레이", "하이패스", "주차센서", "에어백",
    ],
    "쏘렌토": [
        "후방카메라", "내비게이션", "통풍시트", "열선시트", "파노라마선루프",
        "어댑티브크루즈", "헤드업디스플레이", "스마트키", "7인승", "전동트렁크", "하이패스",
    ],
    "그랜저": [
        "후방카메라", "내비게이션", "통풍시트", "헤드업디스플레이", "어라운드뷰",
        "어댑티브크루즈", "메모리시트", "파노라마선루프", "스마트키", "무선충전",
    ],
}

# ── (모델·세대·파워트레인) 그룹 테이블 — docs/ai-advanced/02-seed-price-calibration.md
#    "v3 최종 확정" 표를 그대로 옮김(임의 변경 금지). 만원 단위. count=그룹별 고정 생성 건수
#    (모델당 count 합=50, 전체 17그룹). ─────────────────────────────────────────────
GROUPS = {
    "아반떼": [
        dict(model_name="아반떼 CN7", year_range=(2020, 2022), fuel="가솔린",
             displacement=1598, anchor_year=2022, anchor_price=1850, year_dep=180, count=15),
        dict(model_name="더 뉴 아반떼 CN7", year_range=(2023, 2025), fuel="가솔린",
             displacement=1598, anchor_year=2025, anchor_price=2250, year_dep=230, count=8),
        dict(model_name="아반떼 CN7 하이브리드", year_range=(2021, 2023), fuel="하이브리드",
             displacement=1580, anchor_year=2023, anchor_price=2150, year_dep=230, count=5),
        dict(model_name="아반떼 AD", year_range=(2015, 2017), fuel="가솔린",
             displacement=1591, anchor_year=2017, anchor_price=850, year_dep=70, count=12),
        dict(model_name="더 뉴 아반떼 AD", year_range=(2018, 2020), fuel="가솔린",
             displacement=1591, anchor_year=2020, anchor_price=1300, year_dep=140, count=10),
    ],
    "쏘렌토": [
        dict(model_name="쏘렌토 MQ4", year_range=(2020, 2023), fuel="디젤",
             displacement=2151, anchor_year=2023, anchor_price=2400, year_dep=70, count=13),
        dict(model_name="쏘렌토 MQ4 하이브리드", year_range=(2020, 2022), fuel="하이브리드",
             displacement=1598, anchor_year=2022, anchor_price=2950, year_dep=220, count=7),
        dict(model_name="더 뉴 쏘렌토 MQ4 하이브리드", year_range=(2023, 2025), fuel="하이브리드",
             displacement=1598, anchor_year=2025, anchor_price=4500, year_dep=420, count=10),
        dict(model_name="더 뉴 쏘렌토 MQ4", year_range=(2023, 2025), fuel="가솔린",
             displacement=2497, anchor_year=2025, anchor_price=3650, year_dep=150, count=5),
        dict(model_name="쏘렌토 UM", year_range=(2015, 2017), fuel="디젤",
             displacement=2199, anchor_year=2017, anchor_price=1250, year_dep=120, count=7),
        dict(model_name="더 뉴 쏘렌토 UM", year_range=(2018, 2019), fuel="디젤",
             displacement=2199, anchor_year=2019, anchor_price=1600, year_dep=50, count=8),
    ],
    "그랜저": [
        dict(model_name="그랜저 IG", year_range=(2017, 2019), fuel="가솔린",
             displacement=2359, anchor_year=2019, anchor_price=1350, year_dep=120, count=8),
        dict(model_name="그랜저 IG 3.0", year_range=(2017, 2019), fuel="가솔린",
             displacement=2999, anchor_year=2019, anchor_price=1400, year_dep=60, count=5),
        dict(model_name="더 뉴 그랜저 IG", year_range=(2020, 2022), fuel="가솔린",
             displacement=2497, anchor_year=2022, anchor_price=2300, year_dep=120, count=12),
        dict(model_name="더 뉴 그랜저 IG 3.3", year_range=(2020, 2022), fuel="가솔린",
             displacement=3342, anchor_year=2022, anchor_price=2200, year_dep=250, count=5),
        dict(model_name="그랜저 GN7", year_range=(2023, 2025), fuel="가솔린",
             displacement=2497, anchor_year=2025, anchor_price=3850, year_dep=430, count=10),
        dict(model_name="그랜저 GN7 하이브리드", year_range=(2023, 2025), fuel="하이브리드",
             displacement=1598, anchor_year=2025, anchor_price=4100, year_dep=220, count=10),
    ],
}

# (model_name, fuel) → 그룹. v3의 17개 model_name은 전부 서로 다른 문자열이라(v2엔 "쏘렌토
# MQ4"가 디젤/가솔린 두 그룹에 겹쳐 있었으나 v3는 가솔린 쪽 이름을 "더 뉴 쏘렌토 MQ4"로 분리)
# 이 키가 전 그룹에 걸쳐 유일하다 — 생성행의 그룹 역추적(연식범위 검증)에 쓴다.
GROUP_BY_KEY = {
    (g["model_name"], g["fuel"]): g for family in GROUPS for g in GROUPS[family]
}

COLOR_WEIGHTS = [
    ("흰색", 25), ("검정", 20), ("회색", 15), ("은색", 10),
    ("파랑", 10), ("빨강", 10), ("갈색", 10),
]
REGION_OTHERS = [
    "대구", "광주", "대전", "울산", "세종", "강원",
    "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]
REGION_WEIGHTS = (
    [("서울", 20), ("경기", 20), ("부산", 10), ("인천", 10)]
    + [(r, 40 / len(REGION_OTHERS)) for r in REGION_OTHERS]
)


# ── 순수 규칙 함수 (DB 접속 없이 단위 테스트 가능) ───────────────────────────────────
def compute_price(
    group: dict,
    year: int,
    mileage: int,
    n_options: int,
    accident_status: str,
    family: str,
    noise: float = 1.0,
    current_year: int = CURRENT_YEAR,
) -> int:
    """그룹 감가 공식(v2에서 그대로 유지, v3는 그룹 테이블만 바뀜).
    noise=1.0(기본)이면 노이즈 제외 상태로 결정론적 계산이 된다.

    accident_status가 규칙에 없는 값이면 KeyError를 그대로 던진다(조용히 대체하지 않음).
    """
    raw = group["anchor_price"] - (group["anchor_year"] - year) * group["year_dep"]
    km_ref = 13_000 * (current_year - year)
    raw -= (mileage - km_ref) * KM_PER[family]
    raw += n_options * OPT_PREM[family]
    raw *= ACCIDENT_MULT[accident_status]
    raw *= noise
    price_manwon = round(raw)
    price = price_manwon * 10_000
    return max(price, FLOOR_PRICE)


def sample_year(rng: random.Random, group: dict) -> int:
    lo, hi = group["year_range"]
    return rng.randint(lo, hi)


def sample_mileage(rng: random.Random, year: int, current_year: int = CURRENT_YEAR) -> int:
    age = current_year - year
    if age <= 1:
        val = rng.uniform(3_000, 20_000)
    else:
        val = age * rng.uniform(9_000, 16_000)
    val = max(2_000, min(180_000, val))
    return int(round(val))


def weighted_pick(rng: random.Random, weighted_items: list[tuple[str, float]]) -> str:
    items = [w[0] for w in weighted_items]
    weights = [w[1] for w in weighted_items]
    return rng.choices(items, weights=weights, k=1)[0]


def sample_accident(rng: random.Random) -> tuple[str, bool]:
    status = rng.choices(["무사고", "단순교환", "사고"], weights=[75, 18, 7], k=1)[0]
    return status, status == "무사고"


def format_mileage_kr(m: int) -> str:
    man, rem = divmod(m, 10_000)
    cheon = rem // 1_000
    parts = []
    if man:
        parts.append(f"{man}만")
    if cheon:
        parts.append(f"{cheon}천")
    if not parts:
        parts.append(str(m))
    return "".join(parts) + "km"


def disp_liter(cc: int) -> str:
    return f"{round(cc / 1000, 1):.1f}"


SENT1_TEMPLATES = [
    "{year}년식 {spec} {fuel} 차량으로 주행거리 {mileage_kr}의 {accident_lead} 상태입니다.",
    "{year}년식 {spec} {fuel}, 주행 {mileage_kr}의 {accident_lead} 매물입니다.",
]
ACCIDENT_LEAD = {
    "무사고": "무사고",
    "단순교환": "단순교환 이력이 있는",
    "사고": "사고 이력이 있는",
}
SENT2_TEMPLATES = [
    "정기적으로 관리되어 상태가 양호하며 실내외 컨디션이 좋습니다.",
    "옵션 구성이 알차 실용성과 편의성을 모두 갖췄습니다.",
    "관리 이력이 투명해 안심하고 타실 수 있습니다.",
]
SENT3_TEMPLATES = [
    "합리적인 가격에 {model}를 찾는 분께 추천합니다.",
    "가성비 좋은 매물을 찾는 분께 적합합니다.",
]


def build_description(
    rng: random.Random, model: str, year: int, mileage: int,
    accident_status: str, fuel: str, displacement: int,
) -> str:
    disp = disp_liter(displacement)
    # "그랜저 IG 3.0"처럼 모델명에 이미 배기량 트림이 박힌 경우 "3.0 3.0L" 같은 중복 표기를
    # 피한다 — spec은 문장 1에만 쓰고, 추천 문장(SENT3)엔 항상 plain model을 쓴다.
    spec = model if disp in model else f"{model} {disp}L"
    s1 = rng.choice(SENT1_TEMPLATES).format(
        year=year, spec=spec, fuel=fuel,
        mileage_kr=format_mileage_kr(mileage), accident_lead=ACCIDENT_LEAD[accident_status],
    )
    parts = [s1, rng.choice(SENT2_TEMPLATES)]
    if rng.random() < 0.5:
        parts.append(rng.choice(SENT3_TEMPLATES).format(model=model))
    return " ".join(parts)


def build_row(rng: random.Random, group: dict, family: str) -> dict:
    year = sample_year(rng, group)
    mileage = sample_mileage(rng, year)
    accident_status, accident_free = sample_accident(rng)
    status = weighted_pick(rng, [("on_sale", 90), ("sold", 10)])
    seller_id = rng.choice(SELLER_IDS)
    color = weighted_pick(rng, COLOR_WEIGHTS)
    region = weighted_pick(rng, REGION_WEIGHTS)
    is_single_owner = rng.random() < 0.6
    is_non_smoker = rng.random() < 0.7
    k = rng.randint(2, 6)
    options = rng.sample(OPTIONS_POOL[family], k)
    seats = 7 if (family == "쏘렌토" and "7인승" in options) else 5
    noise = rng.uniform(0.95, 1.05)
    price = compute_price(group, year, mileage, len(options), accident_status, family, noise=noise)
    description = build_description(
        rng, group["model_name"], year, mileage, accident_status, group["fuel"], group["displacement"],
    )
    return dict(
        seller_id=seller_id, status=status, manufacturer=MANUFACTURER[family],
        model=group["model_name"], body_type=BODY_TYPE[family], year=year, price=price,
        mileage=mileage, color=color, fuel=group["fuel"], transmission="자동",
        displacement=group["displacement"], seats=seats, region=region,
        accident_free=accident_free, options=options, description=description,
        accident_status=accident_status, is_single_owner=is_single_owner,
        is_non_smoker=is_non_smoker,
    )


def generate_all(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)  # 전역 random 금지 — 이 인스턴스로만 뽑는다.
    rows = []
    for family in ("아반떼", "쏘렌토", "그랜저"):
        for group in GROUPS[family]:
            for _ in range(group["count"]):
                rows.append(build_row(rng, group, family))
    return rows


# ── 검증 (실패 시 exit 1) ────────────────────────────────────────────────────
def classify_family(model: str) -> str | None:
    for family in ("아반떼", "쏘렌토", "그랜저"):
        if family in model:
            return family
    return None


def validate(rows: list[dict]) -> list[str]:
    issues = []
    for family in ("아반떼", "쏘렌토", "그랜저"):
        pool = set(OPTIONS_POOL[family])
        fam_rows = [r for r in rows if family in r["model"]]
        if len(fam_rows) != N_PER_MODEL:
            issues.append(f"{family}: 생성 건수 {len(fam_rows)} != {N_PER_MODEL}")
        prices = [r["price"] for r in fam_rows]
        mileages = [r["mileage"] for r in fam_rows]
        years = [r["year"] for r in fam_rows]
        if len(set(mileages)) > 1 and len(set(prices)) > 1:
            corr_mileage = statistics.correlation(mileages, prices)
            if not corr_mileage < 0:
                issues.append(f"{family}: price~mileage 상관 {corr_mileage:.4f} (음수여야 함)")
        if len(set(years)) > 1 and len(set(prices)) > 1:
            corr_year = statistics.correlation(years, prices)
            if not corr_year > 0:
                issues.append(f"{family}: price~year 상관 {corr_year:.4f} (양수여야 함)")
        for r in fam_rows:
            if not set(r["options"]).issubset(pool):
                issues.append(f"{family}: options {r['options']}가 풀 밖의 값을 포함")
    for family in ("아반떼", "쏘렌토", "그랜저"):
        for group in GROUPS[family]:
            key = (group["model_name"], group["fuel"])
            n = sum(1 for r in rows if r["model"] == key[0] and r["fuel"] == key[1])
            if n != group["count"]:
                issues.append(f"{key[0]}({key[1]}) 생성 건수 {n} != 그룹 표 count {group['count']}")
    for r in rows:
        if r["price"] < FLOOR_PRICE:
            issues.append(f"{r['model']} price {r['price']} < 하한 {FLOOR_PRICE}")
        if r["fuel"] not in ALLOWED_FUEL:
            issues.append(f"fuel '{r['fuel']}'이 CHECK 허용값 밖")
        if r["color"] not in ALLOWED_COLOR:
            issues.append(f"color '{r['color']}'이 CHECK 허용값 밖")
        if r["region"] not in ALLOWED_REGION:
            issues.append(f"region '{r['region']}'이 CHECK 허용값 밖")
        if r["body_type"] not in ALLOWED_BODY_TYPE:
            issues.append(f"body_type '{r['body_type']}'이 CHECK 허용값 밖")
        if r["accident_status"] not in ALLOWED_ACCIDENT_STATUS:
            issues.append(f"accident_status '{r['accident_status']}'이 CHECK 허용값 밖")
        # 그룹 연식범위 준수 — 생성 로직이 스스로 지키게 돼 있지만(sample_year가 group 범위
        # 안에서만 뽑음) 회귀 안전망으로 SQL 산출물 단계에서도 다시 확인한다.
        group = GROUP_BY_KEY.get((r["model"], r["fuel"]))
        if group is None:
            issues.append(f"model/fuel 조합 ({r['model']}, {r['fuel']})이 그룹 테이블에 없음")
        else:
            lo, hi = group["year_range"]
            if not (lo <= r["year"] <= hi):
                issues.append(f"{r['model']}({r['fuel']}) year={r['year']}가 그룹 연식범위 {group['year_range']} 밖")
    return issues


def check_calibration(rows: list[dict]) -> list[str]:
    """생성 중앙값이 "그룹 중간연식 기대값"(GROUPS 테이블의 앵커가·연감가로 직접 계산, 별도
    참고표 없음 — 정본은 GROUPS 하나) 대비 ±20% 밖이면 경고만 낸다(exit 1 아님 — 이 기대값은
    주행·옵션·사고·노이즈 보정 전 순수 연감가 값이라 생성 중앙값과 원래 어느 정도 차이가 날 수
    있어 사람이 판단할 몫으로 남긴다)."""
    warnings = []
    for family in ("아반떼", "쏘렌토", "그랜저"):
        for group in GROUPS[family]:
            group_rows = [
                r for r in rows if r["model"] == group["model_name"] and r["fuel"] == group["fuel"]
            ]
            if not group_rows:
                continue
            prices = sorted(r["price"] for r in group_rows)
            n = len(prices)
            median_won = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
            median_manwon = median_won / 10_000
            lo, hi = group["year_range"]
            mid_year = (lo + hi) / 2
            expected = group["anchor_price"] - (group["anchor_year"] - mid_year) * group["year_dep"]
            if expected <= 0:
                continue
            deviation = abs(median_manwon - expected) / expected
            if deviation > CALIBRATION_WARN_THRESHOLD:
                warnings.append(
                    f"{group['model_name']}({group['fuel']}) 생성 중앙값 {median_manwon:,.0f}만원 "
                    f"vs 중간연식({mid_year:g}) 기대값 {expected:,.0f}만원 — {deviation:.1%} 괴리"
                )
    return warnings


# ── SQL 생성 ─────────────────────────────────────────────────────────────
def escape_sql_string(s: str) -> str:
    return s.replace("'", "''")


def sql_array(items: list[str]) -> str:
    return "array[" + ",".join(f"'{escape_sql_string(i)}'" for i in items) + "]"


def row_to_sql_tuple(row: dict) -> str:
    return (
        f"('{row['seller_id']}', '{row['status']}', '{row['manufacturer']}', "
        f"'{escape_sql_string(row['model'])}', '{row['body_type']}', {row['year']}, "
        f"{row['price']}, {row['mileage']}, '{row['color']}', '{row['fuel']}', "
        f"'{row['transmission']}', {row['displacement']}, {row['seats']}, '{row['region']}', "
        f"{str(row['accident_free']).lower()}, {sql_array(row['options'])}, "
        f"'{escape_sql_string(row['description'])}', '{row['accident_status']}', "
        f"{str(row['is_single_owner']).lower()}, {str(row['is_non_smoker']).lower()})"
    )


def build_insert_sql(rows: list[dict]) -> str:
    header = (
        "-- seed-depreciation.sql — 감가 규칙 v3(엔카 실측 17그룹 고정건수) 기반 "
        "아반떼·쏘렌토·그랜저 시드 150건(각 50건, api/scripts/seed_depreciation.py 산출물)\n"
        "-- 근거: docs/ai-advanced/02-seed-price-calibration.md \"v3 최종 확정\" 표\n"
        "-- embedding·created_at·seller_name·id는 제외(기본값·트리거 위임)\n"
        "begin;\n"
        "insert into public.listings\n"
        "  (seller_id, status, manufacturer, model, body_type, year, price, mileage, color, "
        "fuel, transmission, displacement, seats, region, accident_free, options, description, "
        "accident_status, is_single_owner, is_non_smoker)\n"
        "values\n"
    )
    lines = ",\n".join("  " + row_to_sql_tuple(r) for r in rows)
    return header + lines + ";\ncommit;\n"


def build_adjustments_sql(deviations: list[dict]) -> str:
    header = (
        "-- seed-depreciation-adjustments.sql — 기존 아반떼·쏘렌토·그랜저 매물 중 v3 감가 규칙가와 "
        f"{int(DEVIATION_THRESHOLD * 100)}% 넘게 괴리된 행의 가격 조정 제안(별도 승인 대상)\n"
        "begin;\n"
    )
    lines = "\n".join(
        f"update public.listings set price = {d['rule_price']} where id = '{d['id']}';"
        for d in deviations
    )
    return header + lines + "\ncommit;\n"


# ── 기존 매물 이탈 진단 (SELECT만) ───────────────────────────────────────────
def resolve_group(family: str, model: str, year: int, fuel: str) -> tuple[dict | None, str | None]:
    """기존 DB 행(model 문자열만으로는 세대/트림이 모호할 수 있음)을 그룹 테이블에 매핑한다.

    1) 연료+연식범위로 후보를 좁힌다(3단계 시세 진단 매칭 기준 — v3 문서 확정: 모델 문자열
       완전 일치가 1순위지만, 완전 일치 후보가 없을 수 있으니 연료+연식범위로 먼저 후보를
       추린 뒤 아래에서 문자열 일치로 좁힌다).
    2) 후보가 하나면 그걸로 확정.
    3) 여럿이면(예: 더 뉴 아반떼 AD와 아반떼 CN7이 2020년에 겹치는 경우, 더 뉴 그랜저
       IG/3.3처럼 연료·연식범위가 같은 트림들) model 문자열과 정확히 같은 이름의 그룹이
       있으면 그걸로 확정(= "같은 종끼리 비교" 원칙).
    4) 그래도 모호하면(세대 표기가 아예 없는 model, 예: "그랜저" 2022) 건수가 더 많은(더
       흔한) 그룹을 기본값으로 쓴다 — 가정, 리포트에 표시.
    """
    candidates = [
        g for g in GROUPS[family]
        if g["fuel"] == fuel and g["year_range"][0] <= year <= g["year_range"][1]
    ]
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0], "unique"
    exact = [g for g in candidates if g["model_name"] == model]
    if len(exact) == 1:
        return exact[0], "exact_name"
    # 3.5) 세대 코드 일치: model에 세대 코드(AD·CN7 등)가 박혀 있으면 같은 코드를 가진
    #      그룹만 남긴다 — 예: 기존 "아반떼 AD" 2020년식은 CN7이 아니라 더 뉴 아반떼 AD로.
    #      (검수에서 발견: 건수 기본값이 세대가 다른 그룹을 고르는 오매핑을 막는다.)
    codes = [c for c in ("GN7", "CN7", "MQ4", "UM", "AD", "MD", "IG", "HG") if c in model]
    if codes:
        coded = [g for g in candidates if all(c in g["model_name"] for c in codes)]
        if len(coded) == 1:
            return coded[0], "generation_code"
        if coded:
            candidates = coded
    best = max(candidates, key=lambda g: g["count"])
    return best, "ambiguous_default"


def analyze_existing(rows: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    """반환: (이탈 목록, 제외 목록[연료/연식 조합 매핑 불가], 모호 매핑 안내 목록)."""
    deviations, excluded, ambiguous_notes = [], [], []
    for r in rows:
        family = classify_family(r["model"])
        if family is None:
            continue
        accident_status = r["accident_status"]
        if not accident_status:
            # 이번 데이터셋엔 해당 없음(전부 채워져 있음) — 없을 경우의 대체 추정치(가정 명시).
            accident_status = "무사고" if r["accident_free"] else "사고"
        group, method = resolve_group(family, r["model"], r["year"], r["fuel"])
        if group is None:
            excluded.append(
                {
                    "id": r["id"], "model": r["model"], "year": r["year"], "fuel": r["fuel"],
                    "reason": f"{family} 그룹 테이블에 연료='{r['fuel']}' 연식={r['year']} 조합 없음 — 매핑 불가",
                }
            )
            continue
        if method == "ambiguous_default":
            ambiguous_notes.append(
                f"id={r['id']} model={r['model']} year={r['year']} fuel={r['fuel']} → "
                f"'{group['model_name']}'({group['fuel']}) 기본값 매핑(건수 최대 그룹, 세대/트림 모호)"
            )
        rule_price = compute_price(
            group, r["year"], r["mileage"], len(r["options"] or []), accident_status, family, noise=1.0,
        )
        deviation = abs(r["price"] - rule_price) / rule_price
        if deviation > DEVIATION_THRESHOLD:
            deviations.append(
                {
                    "id": r["id"], "model": r["model"], "year": r["year"],
                    "mileage": r["mileage"], "actual_price": r["price"],
                    "rule_price": rule_price, "deviation": deviation,
                }
            )
    return deviations, excluded, ambiguous_notes


def fetch_existing_target_listings(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select id, model, year, price, mileage, fuel, options, accident_status, accident_free
            from public.listings
            where model like %s or model like %s or model like %s
            order by model
            """,
            ("%아반떼%", "%쏘렌토%", "%그랜저%"),
        )
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ── 리포트 출력 ──────────────────────────────────────────────────────────
def print_report(
    rows: list[dict], deviations: list[dict], excluded: list[dict],
    ambiguous_notes: list[str], calibration_warnings: list[str],
) -> None:
    print("=" * 70)
    print("모델별 생성 통계")
    print("=" * 70)
    for family in ("아반떼", "쏘렌토", "그랜저"):
        fam_rows = [r for r in rows if family in r["model"]]
        prices = sorted(r["price"] for r in fam_rows)
        fuels: dict[str, int] = {}
        accidents: dict[str, int] = {}
        for r in fam_rows:
            fuels[r["fuel"]] = fuels.get(r["fuel"], 0) + 1
            accidents[r["accident_status"]] = accidents.get(r["accident_status"], 0) + 1
        n = len(prices)
        median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        print(f"\n[{family}] {n}건 — price min={prices[0]:,} 중앙값={median:,.0f} max={prices[-1]:,}")
        print(f"  fuel {fuels} / accident_status {accidents}")

    print("\n" + "=" * 70)
    print("그룹별(17개) 생성 통계")
    print("=" * 70)
    for family in ("아반떼", "쏘렌토", "그랜저"):
        for group in GROUPS[family]:
            g_rows = [r for r in rows if r["model"] == group["model_name"] and r["fuel"] == group["fuel"]]
            prices = sorted(r["price"] for r in g_rows)
            n = len(prices)
            median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
            years = sorted(r["year"] for r in g_rows)
            print(
                f"  {group['model_name']:<16} ({group['fuel']:<5}) {n:>2}건  "
                f"연식 {years[0]}~{years[-1]}  가격 중앙값 {median:>12,.0f}원  "
                f"[{group['displacement']}cc, 표기대건수={group['count']}]"
            )

    print("\n" + "=" * 70)
    print("그룹 중간연식 기대값 대비 캘리브레이션 경고 (±20% 밖, exit 1 아님)")
    print("=" * 70)
    if calibration_warnings:
        for w in calibration_warnings:
            print(f"  ⚠️ {w}")
    else:
        print("경고 없음 — 전 그룹 생성 중앙값이 중간연식 기대값 ±20% 이내.")

    print("\n" + "=" * 70)
    print("샘플 5건")
    print("=" * 70)
    sample_rng = random.Random(SEED)  # 리포트 표시용 별도 인스턴스(생성 순서에 영향 없음)
    for r in sample_rng.sample(rows, 5):
        print(
            f"  {r['manufacturer']} {r['model']} {r['year']}년식 {r['price']:,}원 "
            f"{r['mileage']:,}km {r['fuel']} {r['accident_status']} 옵션{len(r['options'])}개"
        )

    print("\n" + "=" * 70)
    print(f"기존 매물 이탈 목록 (|실제가-규칙가|/규칙가 > {DEVIATION_THRESHOLD:.0%})")
    print("=" * 70)
    if excluded:
        print(f"제외 {len(excluded)}건(연료/연식 조합이 그룹 테이블 밖):")
        for e in excluded:
            print(f"  {e['id']} {e['model']} year={e['year']} fuel={e['fuel']} — {e['reason']}")
    else:
        print("제외 0건.")
    if ambiguous_notes:
        print(f"\n모호 매핑 {len(ambiguous_notes)}건(세대/트림 확정 불가 → 건수 최대 그룹 기본값):")
        for note in ambiguous_notes:
            print(f"  {note}")
    if deviations:
        print(f"\n이탈 {len(deviations)}건:")
        for d in deviations:
            print(
                f"  id={d['id']} model={d['model']} year={d['year']} mileage={d['mileage']:,} "
                f"실제가={d['actual_price']:,} 규칙가={d['rule_price']:,} "
                f"이탈률={d['deviation']:.1%}"
            )
    else:
        print("이탈 0건.")


# ── --apply / --apply-adjustments (구현만, 이번 세션에서 실행 금지 — 검수 후 상위 세션이 실행) ──
def safe_conninfo(url: str) -> str:
    """apply_listings_expansion.py·backfill_embeddings.py와 동일 로직(중복 대신 재사용해도 되나,
    스크립트 단독 실행성을 위해 여기 인라인 — scripts.backfill_embeddings의 정의와 동일해야 한다)."""
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    userinfo, hostpart = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, password = userinfo.split(":", 1)
    return f"{scheme}://{user}:{quote(password, safe='')}@{hostpart}"


def apply_sql_file(sql_path: Path, label: str) -> None:
    import psycopg
    from app.config import require, settings

    if not sql_path.exists():
        print(f"❌ {sql_path} 없음 — 먼저 --preview로 생성하세요.", file=sys.stderr)
        raise SystemExit(2)
    sql = sql_path.read_text(encoding="utf-8")
    db_url = require("DATABASE_URL", settings.database_url)
    with psycopg.connect(safe_conninfo(db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)  # 파일에 begin;...commit; 포함
            cur.execute("select count(*) from public.listings")
            total = cur.fetchone()[0]
    print(f"✅ {label} 적용 완료. listings 총 {total}건")


def run_apply() -> None:
    apply_sql_file(SEED_SQL_PATH, "seed-depreciation.sql")


def run_apply_adjustments() -> None:
    apply_sql_file(ADJUST_SQL_PATH, "seed-depreciation-adjustments.sql")


# ── main ────────────────────────────────────────────────────────────────
def run_preview() -> None:
    rows = generate_all(SEED)

    issues = validate(rows)
    if issues:
        print("❌ 검증 실패:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        raise SystemExit(1)

    calibration_warnings = check_calibration(rows)

    SQL_DIR.mkdir(parents=True, exist_ok=True)
    SEED_SQL_PATH.write_text(build_insert_sql(rows), encoding="utf-8")

    import psycopg
    from app.config import require, settings

    db_url = require("DATABASE_URL", settings.database_url)
    with psycopg.connect(safe_conninfo(db_url)) as conn:
        existing = fetch_existing_target_listings(conn)
    deviations, excluded, ambiguous_notes = analyze_existing(existing)
    ADJUST_SQL_PATH.write_text(build_adjustments_sql(deviations), encoding="utf-8")

    print_report(rows, deviations, excluded, ambiguous_notes, calibration_warnings)

    print("\n" + "=" * 70)
    print("생성 파일")
    print("=" * 70)
    print(f"  {SEED_SQL_PATH}")
    print(f"  {ADJUST_SQL_PATH}")
    print("\n✅ 검증 통과. (실제 반영은 --apply / --apply-adjustments, 검수 후 상위 세션이 실행)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preview", action="store_true", help="생성+검증+SQL 산출(기본 동작)")
    ap.add_argument("--apply", action="store_true", help="seed-depreciation.sql을 DB에 적용")
    ap.add_argument(
        "--apply-adjustments", action="store_true",
        help="seed-depreciation-adjustments.sql을 DB에 적용",
    )
    args = ap.parse_args()

    if args.apply:
        run_apply()
    elif args.apply_adjustments:
        run_apply_adjustments()
    else:
        run_preview()


if __name__ == "__main__":
    main()
