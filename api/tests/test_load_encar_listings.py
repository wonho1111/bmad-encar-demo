"""load_encar_listings.py 행 변환 단위 테스트 — 네트워크(임베딩)·DB 무관.

옵션 코드→이름 매핑(null 제거·중복 제거), generation 파생(하이브리드 접미 제거),
CHECK 어휘(0002_listings.sql) 안에 드는지만 검증한다. DB 연결이 필요한 --local/--embed/
--apply-prod/--dry-run-prod 경로는 여기서 다루지 않는다(로컬 리허설로 별도 실측).
"""

import importlib.util
from pathlib import Path

# scripts는 패키지가 아니므로 파일 경로로 직접 로드(test_backfill_corpus_chunking.py와 동일 관행).
_SPEC = importlib.util.spec_from_file_location(
    "load_encar_listings",
    Path(__file__).resolve().parent.parent / "scripts" / "load_encar_listings.py",
)
load_encar_listings = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(load_encar_listings)

# 0002_listings.sql CHECK 목록(단일출처, 이 테스트는 그 값을 그대로 옮겨 적어 드리프트를 잡는다).
VALID_MANUFACTURERS = {
    "현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티",
    "BMW", "벤츠", "아우디", "폭스바겐", "토요타", "혼다", "렉서스", "테슬라", "기타",
}
VALID_BODY_TYPES = {
    "경차", "소형차", "준중형차", "중형차", "대형차", "스포츠카",
    "SUV", "RV", "경승합차", "승합차", "화물차", "기타",
}
VALID_COLORS = {"흰색", "검정", "회색", "은색", "파랑", "빨강", "갈색", "녹색", "기타"}
VALID_FUELS = {"가솔린", "디젤", "하이브리드", "전기", "LPG"}
VALID_TRANSMISSIONS = {"자동", "수동"}
VALID_REGIONS = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
}


def _csv_row(**overrides) -> dict:
    """listings_eval.csv 한 행을 흉내낸 최소 dict(문자열 값, DictReader가 주는 그대로)."""
    base = {
        "manufacturer": "현대", "model": "그랜저 GN7 하이브리드", "body_type": "중형차",
        "year": "2023", "price": "35000000", "mileage": "20000", "color": "흰색",
        "fuel": "하이브리드", "transmission": "자동", "displacement": "1598", "seats": "5",
        "region": "서울", "accident_free": "True", "accident_status": "무사고",
        "options": '["005", "029", "001"]', "encar_id": "12345",
    }
    base.update(overrides)
    return base


# ── 옵션 매핑 ──────────────────────────────────────────────────────────────────
def test_map_options_translates_codes_to_product_names():
    option_map = {"005": "내비게이션", "029": None, "001": None}
    names = load_encar_listings.map_options(["005", "029", "001"], option_map)
    assert names == ["내비게이션"]


def test_map_options_drops_null_and_dedupes_preserving_order():
    option_map = {"022": "열선시트", "063": "열선시트", "057": "스마트키", "999": None}
    names = load_encar_listings.map_options(["022", "999", "063", "057"], option_map)
    # "022"·"063" 둘 다 "열선시트"로 매핑되므로 중복 제거, 처음 등장 순서(열선시트 → 스마트키) 보존.
    assert names == ["열선시트", "스마트키"]


def test_map_options_empty_list_returns_empty():
    assert load_encar_listings.map_options([], {"005": "내비게이션"}) == []


# ── generation 파생 ────────────────────────────────────────────────────────────
def test_derive_generation_strips_trailing_hybrid_suffix():
    assert load_encar_listings.derive_generation("그랜저 GN7 하이브리드") == "그랜저 GN7"


def test_derive_generation_no_suffix_returns_model_unchanged():
    assert load_encar_listings.derive_generation("쏘렌토 MQ4") == "쏘렌토 MQ4"


def test_derive_generation_hybrid_only_in_middle_not_stripped():
    # 접미사가 아니라 중간에 있으면 건드리지 않는다(끝만 본다).
    assert load_encar_listings.derive_generation("하이브리드 전용관") == "하이브리드 전용관"


# ── transform_row: CHECK 어휘 준수 ─────────────────────────────────────────────
def test_transform_row_values_are_within_check_vocab():
    option_map = {"005": "내비게이션", "029": None, "001": None}
    seller_ids = ["seller-a", "seller-b", "seller-c"]
    row = load_encar_listings.transform_row(_csv_row(), 0, option_map, seller_ids)

    assert row["manufacturer"] in VALID_MANUFACTURERS
    assert row["body_type"] in VALID_BODY_TYPES
    assert row["color"] in VALID_COLORS
    assert row["fuel"] in VALID_FUELS
    assert row["transmission"] in VALID_TRANSMISSIONS
    assert row["region"] in VALID_REGIONS


def test_transform_row_derives_expected_fields():
    option_map = {"005": "내비게이션", "029": None, "001": None}
    seller_ids = ["seller-a", "seller-b", "seller-c"]
    row = load_encar_listings.transform_row(_csv_row(), 0, option_map, seller_ids)

    assert row["seller_id"] == "seller-a"  # index 0 % 3
    assert row["status"] == "on_sale"
    assert row["source"] == load_encar_listings.SOURCE
    assert row["description"] is None
    assert row["generation"] == "그랜저 GN7"  # 하이브리드 접미 제거
    assert row["options"] == ["내비게이션"]
    assert row["year"] == 2023 and isinstance(row["year"], int)
    assert row["price"] == 35000000 and isinstance(row["price"], int)
    assert row["accident_free"] is True
    assert row["accident_status"] == "무사고"
    assert row["encar_id"] == "12345"


def test_transform_row_round_robins_seller_by_index():
    option_map = {}
    seller_ids = ["s0", "s1", "s2"]
    rows = [load_encar_listings.transform_row(_csv_row(options="[]"), i, option_map, seller_ids)
            for i in range(6)]
    assert [r["seller_id"] for r in rows] == ["s0", "s1", "s2", "s0", "s1", "s2"]


def test_transform_row_blank_accident_status_becomes_none():
    row = load_encar_listings.transform_row(_csv_row(accident_status="", options="[]"), 0, {}, ["s0"])
    assert row["accident_status"] is None


def test_prod_get_all_pages_past_supabase_row_cap(monkeypatch):
    """REST가 요청당 1,000행까지만 돌려줘도 offset으로 끝까지 모은다(E-6 실측: limit=10000이
    조용히 잘려 멱등성 검사가 4,341건을 '없음'으로 오판)."""
    total = 2_360
    calls: list[str] = []

    def fake_rest(method, path, token, anon, body=None, extra=None):
        calls.append(path)
        assert method == "GET"
        params = dict(kv.split("=") for kv in path.split("?", 1)[1].split("&"))
        limit, offset = int(params["limit"]), int(params["offset"])
        return 200, [{"id": i} for i in range(offset, min(offset + limit, total))]

    monkeypatch.setattr(load_encar_listings, "prod_rest", fake_rest)
    rows = load_encar_listings.prod_get_all("listings?select=id&seller_id=eq.x", "t", "a")
    assert [r["id"] for r in rows] == list(range(total))
    assert len(calls) == 3  # 1000 + 1000 + 360
    assert all("limit=1000" in c for c in calls)


def test_prod_get_all_single_short_page(monkeypatch):
    monkeypatch.setattr(load_encar_listings, "prod_rest",
                        lambda *a, **k: (200, [{"id": 1}, {"id": 2}]))
    assert len(load_encar_listings.prod_get_all("listings?select=id", "t", "a")) == 2
