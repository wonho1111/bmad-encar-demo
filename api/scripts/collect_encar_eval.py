"""평가용 엔카(encar.com) 실매물 수집 — 비상업·비배포, 시세 예측 검증용 오프라인 데이터.

배경: 서비스 시드 매물은 우리가 정한 규칙+노이즈로 만든 것이라(seed_depreciation.py) 시세
예측 모델을 검증하는 근거가 못 된다. 그래서 실제 매물을 평가 전용으로만 긁어 로컬
`.logs/encar_eval/`에만 저장한다(레포에도, 서비스 DB에도 넣지 않는다). 종전 "크롤링 배제"
결정(서비스 DB 적재 기준)은 그대로 두고, 이번 수집은 그 결정 밖의 평가용 오프라인 예외다.
상세 배경·설계 근거는 `/home/whlee/.claude/plans/sparkling-mixing-magpie.md` 참조.

지켜야 하는 규칙(전부 코드에 박혀 있다 — 주석이 아니라 실행되는 제약이라야 어기지 못한다.
CLAUDE.md B9: "규칙은 어길 수 없는 자리에 박는다"):
  - User-Agent는 아래 EncarHttpClient.USER_AGENT 고정값만 쓴다. 브라우저 위장·Referer/Origin
    추가·요청마다 헤더를 바꾸는 짓 금지 — 헤더는 이 클래스 한 곳에서만 만든다.
  - 단일 스레드, 요청 간격 최소 1.0초(--interval로 늘릴 수는 있어도 줄일 수는 없다 — 클래스
    생성자에서 하한을 clamp하므로 호출부가 실수로 값을 낮춰도 못 어긴다).
  - 429·5xx(또는 네트워크 자체 실패)는 5·15·45초 백오프 3회 후 포기(RequestFailed). 403은
    그 자리에서 즉시 중단(Forbidden) — 그 날은 다시 시도하지 않는다.
  - 저장하는 JSON은 화이트리스트 경로만 남긴다(pick_paths + assert_only_whitelisted_keys).
    연락처·차량번호·사진·판매자명 등은 디스크로 내려가기 전에 걸러진다 — "권한(=API 응답
    전체)은 있어도 저장 정책(화이트리스트)이 항상 앞선다"의 구현.

이 파일은 1단계 산출물이다 — 하위 명령 중 `discover`·`probe-accident`만 지금 구현돼 있고,
`collect`·`normalize`·`summary`는 2단계 이후에 채운다(지금은 스텁: 메시지 출력 후 exit 2).

사용 예:
  discover        (모델군 3개 최신 200건 세대분포 표 + limit/offset/세대필터 시험, ≈37요청)
    .venv/bin/python scripts/collect_encar_eval.py discover

  probe-accident  (discover가 찾은 그랜저 GN7 20건으로 사고이력 후보 엔드포인트 3종 시험,
                    20×4=80요청)
    .venv/bin/python scripts/collect_encar_eval.py probe-accident --n 20

  둘 다 기본으로 `<repo_root>/.logs/encar_eval/<YYYYMMDD>/`에 쓴다(--out-dir로 덮어쓰기 가능).
  진행 중단: 그 디렉터리에 빈 파일 `.stop`을 만들면 다음 요청 전에 StopRequested로 멈춘다.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# api/scripts/collect_encar_eval.py -> api/scripts -> api -> repo_root(= api/의 부모)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ── 화이트리스트(PII 규칙의 실체 — 아래 pick_paths가 이 목록 밖은 절대 못 담는다) ─────────

# 목록(SearchResults) 행에서 저장을 허용하는 키. 연락처·판매자명·사진 등은 여기 없으므로
# pick_paths를 거치면 애초에 안 담긴다.
LIST_WHITELIST = (
    "Id", "Manufacturer", "Model", "Badge", "BadgeDetail", "FuelType", "Transmission",
    "FormYear", "Year", "Mileage", "Price", "OfficeCityState", "SellType", "ModifiedDate",
    "ServiceCopyCar",
)

# 상세(vehicle/{Id}) 응답에서 저장을 허용하는 "상위키.하위키" 경로. 상세 원본엔 contact·
# contents·vehicleNo·vin·photos·partnership 등이 섞여 있는데(PII·비저장 대상) 이 dict에
# 없으므로 pick_paths를 거치면 통째로 빠진다.
DETAIL_WHITELIST = {
    "category": [
        "modelGroupName", "modelName", "gradeName", "gradeDetailName", "formYear",
        "yearMonth", "originPrice",
    ],
    "spec": [
        "mileage", "displacement", "transmissionName", "fuelName", "colorName",
        "seatCount", "bodyName",
    ],
    "advertisement": ["price", "status", "leaseRentInfo"],
    "options": ["standard", "choice"],
    "manage": ["modifyDateTime"],
    # probe-accident(2026-09-05) 결과 채택: 성능점검부(inspection) 엔드포인트가 사고이력의
    # 유일한 출처(레코드 엔드포인트 ep2/ep3는 안 씀). condition.inspection.formats·
    # condition.accident.recordView는 개인식별정보가 아닌 불리언/목록이라 상세 화이트리스트에
    # 더한다(둘 다 summary의 inspection_vs_formats 교차표용).
    "condition": {
        "inspection": ["formats"],
        "accident": ["recordView"],
    },
}

# 사고이력(성능점검부) `/v1/readside/inspection/vehicle/{Id}` 화이트리스트 — probe-accident에서
# 실제로 확인한 키만 담는다. `inspectionSource`(registrantId/updaterId 등 개인식별자 포함),
# `master.supplyNum`, `master.detail.recordNo`, `comments`, `images`, `inners`, `outers`,
# `etcs`는 **절대** 여기 없어야 한다 — 여기 없으면 pick_paths가 애초에 못 담는다.
INSPECTION_WHITELIST = {
    "vehicleId": True,
    "master": {
        "accdient": True,  # 원본 API 필드명 오타 그대로("accident" 아님) — 임의로 고치지 않는다
        "simpleRepair": True,
        "registrationDate": True,
        "detail": [
            "firstRegistrationDate", "mileage", "waterlog", "tuning", "recall",
            "usageChangeTypes", "seriousTypes", "issueDate", "modelYear",
        ],
    },
}

# probe-accident의 사고이력 후보 엔드포인트는 아직 화이트리스트를 정할 수 없다(무슨 키가
# 오는지 이 프로브로 처음 본다) — 대신 이름에 이 부분문자열(대소문자 무관)이 들어간 키를
# 어느 깊이에서든 넓게 제거한다. 실제 화이트리스트는 사람이 이 프로브 결과를 본 뒤 정한다.
FORBIDDEN_KEY_SUBSTRINGS = (
    "vehicleno", "vin", "contact", "phone", "owner", "name", "address", "userid",
)


# ── 예외 ────────────────────────────────────────────────────────────────────────────

class RequestFailed(Exception):
    """429/5xx(또는 네트워크 실패)가 백오프 3회(5·15·45초) 후에도 계속될 때."""

    def __init__(self, status: int | None, url: str):
        self.status = status
        self.url = url
        super().__init__(f"요청 반복 실패: status={status} url={url}")


class Forbidden(Exception):
    """403 — 엔카가 명시적으로 거부한 상태. 재시도 없이 즉시 올린다(당일 재수집 금지)."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(f"403 Forbidden: {url}")


class StopRequested(Exception):
    """`.stop` 파일 감지, 또는 --max-requests/--max-runtime 상한 도달."""


# ── 화이트리스트 헬퍼 ──────────────────────────────────────────────────────────────────

def pick_paths(obj: dict, whitelist) -> dict:
    """whitelist가 허용한 경로만 obj에서 뽑아 새 dict로 만든다(화이트리스트 방식 — 원본에
    금지 필드가 뭐가 더 있든, 여기 없으면 새어나가지 않는다).

    whitelist는 세 형태를 재귀적으로 조합한다(INSPECTION_WHITELIST처럼 3단 경로
    `master.detail.mileage`도 이 조합으로 표현한다):
      - 평평한 키 목록(list/tuple[str]): obj가 dict일 때 그 최상위 키만 그대로(raw) 고른다
        (LIST_WHITELIST, 그리고 DETAIL_WHITELIST의 각 상위키 아래 하위키 목록도 이 형태).
      - `True`: "잎(leaf)" 표시 — obj[key] 값을 타입(bool/str/list 무엇이든) 그대로 둔다
        (예: INSPECTION_WHITELIST의 master.accdient).
      - dict: 한 단 더 들어가 같은 규칙을 재귀 적용한다(예: master.detail 아래 목록).
    """
    if isinstance(whitelist, (list, tuple)):
        return {k: obj[k] for k in whitelist if isinstance(obj, dict) and k in obj}
    if isinstance(whitelist, dict):
        if not isinstance(obj, dict):
            return {}
        picked: dict = {}
        for key, sub in whitelist.items():
            if key not in obj:
                continue
            if sub is True:
                picked[key] = obj[key]
            elif isinstance(sub, (list, tuple)):
                sub_val = obj[key]
                if not isinstance(sub_val, dict):
                    continue
                sub_picked = {k: sub_val[k] for k in sub if k in sub_val}
                if sub_picked:
                    picked[key] = sub_picked
            elif isinstance(sub, dict):
                nested = pick_paths(obj[key], sub)
                if nested:
                    picked[key] = nested
        return picked
    raise TypeError(f"지원하지 않는 whitelist 타입: {type(whitelist)}")


def assert_only_whitelisted_keys(obj: dict, whitelist) -> None:
    """obj에 whitelist 밖의 키가 있으면 즉시 AssertionError로 죽는다 — pick_paths 출력을
    디스크에 쓰기 직전에 다시 확인하는 안전망(CLAUDE.md B9: 저장 직전 지점에 박아야 어길 수
    없다). `assert` 문이 아니라 명시적 raise를 쓴다 — `python -O`로 실행되면 assert 문은
    통째로 사라지는데, 이건 "하드 요구사항"이라 최적화 플래그로도 빠지면 안 된다.

    pick_paths와 같은 whitelist 문법(list/True/dict)을 재귀적으로 검증한다.
    """
    if isinstance(whitelist, (list, tuple)):
        if not isinstance(obj, dict):
            raise AssertionError(f"dict가 아님: {type(obj)}")
        extra = set(obj) - set(whitelist)
        if extra:
            raise AssertionError(f"화이트리스트 밖 키: {sorted(extra)}")
        return
    if isinstance(whitelist, dict):
        if not isinstance(obj, dict):
            raise AssertionError(f"dict가 아님: {type(obj)}")
        extra_top = set(obj) - set(whitelist)
        if extra_top:
            raise AssertionError(f"화이트리스트 밖 최상위 키: {sorted(extra_top)}")
        for key, sub in whitelist.items():
            if key not in obj:
                continue
            if sub is True:
                continue  # 잎 — 어떤 값이든 허용(경로 자체가 이미 화이트리스트를 거쳤다)
            if isinstance(sub, (list, tuple)):
                extra_sub = set(obj[key]) - set(sub)
                if extra_sub:
                    raise AssertionError(f"화이트리스트 밖 하위 키({key}): {sorted(extra_sub)}")
            elif isinstance(sub, dict):
                assert_only_whitelisted_keys(obj[key], sub)
        return
    raise TypeError(f"지원하지 않는 whitelist 타입: {type(whitelist)}")


def strip_forbidden_keys(obj):
    """중첩 구조 전체(dict/list 어느 깊이든)에서 이름에 FORBIDDEN_KEY_SUBSTRINGS 중 하나가
    (대소문자 무관) 들어간 키를 제거한다. probe-accident 전용 — 아직 화이트리스트를 못 정한
    응답을 사람이 눈으로 볼 수 있게 최소 방어만 하는 블랙리스트다(정식 저장은 항상
    pick_paths 화이트리스트를 쓴다).
    """
    if isinstance(obj, dict):
        return {
            k: strip_forbidden_keys(v)
            for k, v in obj.items()
            if not any(bad in k.lower() for bad in FORBIDDEN_KEY_SUBSTRINGS)
        }
    if isinstance(obj, list):
        return [strip_forbidden_keys(v) for v in obj]
    return obj


# ── 원자적 쓰기(run_phase_b.py:218-229 패턴 — tmp 파일에 먼저 쓰고 replace로 교체) ────────

def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(str(path) + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


# ── HTTP 계층 ──────────────────────────────────────────────────────────────────────

class EncarHttpClient:
    """단일 스레드 HTTP 클라이언트 — 속도 제한·재시도·요청 로그를 전부 여기 한 곳에 모은다.

    discover/probe-accident/collect(2단계)가 전부 이 클래스 하나로만 요청한다 — 간격 계산·
    403 즉시중단·로그 형식이 흩어지면 나중에 하나만 고치고 나머지가 어긋난다(CLAUDE.md A2).
    """

    BASE = "https://api.encar.com"
    USER_AGENT = "chajangnim-eval-collector/0.1 (non-commercial academic evaluation; 1 req/s)"
    BACKOFF = (5, 15, 45)  # 429/5xx 재시도 대기(초), 총 3회

    def __init__(
        self,
        out_dir: Path,
        interval: float = 1.0,
        max_requests: int = 15000,
        max_runtime: float = 18000.0,
    ):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.interval = max(interval, 1.0)  # 하한 clamp — 호출부가 실수로 낮춰도 못 어긴다
        self.max_requests = max_requests
        self.max_runtime = max_runtime
        self.request_count = 0
        self._run_start = time.monotonic()
        self._prev_start: float | None = None
        self.log_path = out_dir / "collect.log"

    def _check_guards(self) -> None:
        """매 요청(재시도 포함) 전에 확인 — .stop 파일·요청수 상한·실행시간 상한."""
        stop_file = self.out_dir / ".stop"
        if stop_file.exists():
            raise StopRequested(f".stop 파일 감지: {stop_file}")
        if self.request_count >= self.max_requests:
            raise StopRequested(f"--max-requests 상한 도달: {self.request_count}")
        if time.monotonic() - self._run_start >= self.max_runtime:
            raise StopRequested(f"--max-runtime 상한 도달: {self.max_runtime}초")

    def _send_once(self, path_and_query: str, url: str) -> tuple[int | None, bytes]:
        """실제 HTTP 요청 1회 — 간격 대기(이전 요청 START 기준 interval 이상)·collect.log
        기록·request_count 증가까지 이 메서드 하나로 끝낸다. 재시도 루프(get_json)가 이
        메서드를 다시 부르면 그때도 여기서 간격을 다시 계산하므로, 백오프로 이미 충분히
        쉬었으면 추가로 안 쉬고, 백오프가 --interval보다 짧으면 모자란 만큼 더 쉰다.
        """
        if self._prev_start is not None:
            since = time.monotonic() - self._prev_start
            if since < self.interval:
                time.sleep(self.interval - since)
        start = time.monotonic()
        gap = None if self._prev_start is None else start - self._prev_start
        self._prev_start = start
        wall_ts = datetime.now().isoformat(timespec="milliseconds")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read()
        except urllib.error.URLError:
            status = None
            body = b""

        elapsed = time.monotonic() - start
        self.request_count += 1
        status_field = str(status) if status is not None else "ERR"
        gap_field = "NA" if gap is None else f"{gap:.3f}"
        # 로그엔 unescape된(사람이 읽을 수 있는) path+query만 남긴다 — 실제 요청은 위 url
        # (인코딩된 값)로 이미 보냈다.
        readable = urllib.parse.unquote(path_and_query)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"{wall_ts}\t{status_field}\t{elapsed:.3f}\t{gap_field}\t{readable}\n")

        return status, body

    def get_json(self, path_and_query: str) -> tuple[int | None, dict | None]:
        """GET 요청 1건. 계약:
          - 200 등 정상 응답: (status, JSON으로 파싱한 dict) — 파싱 실패 시 (status, None).
          - 404: (404, None) — 재시도 없음(엔드포인트에 따라 404가 정상 응답이라서).
          - 403: 즉시 Forbidden 예외.
          - 429 또는 5xx 또는 네트워크 실패: 5·15·45초 백오프 후 재시도, 3회 다 실패하면
            RequestFailed.
          - 그 외 상태코드(예: 세대필터 400): 그대로 (status, body_or_None) 반환 — 호출부가
            "이 시도는 실패"로 판단하게 한다(discover의 nested→flat 폴백이 이 경로를 쓴다).
        """
        url = self.BASE + path_and_query
        attempt = 0
        while True:
            self._check_guards()
            status, body = self._send_once(path_and_query, url)
            if status == 403:
                raise Forbidden(url)
            if status is None or status == 429 or (500 <= status < 600):
                if attempt < len(self.BACKOFF):
                    time.sleep(self.BACKOFF[attempt])
                    attempt += 1
                    continue
                raise RequestFailed(status, url)
            if status == 404:
                return 404, None
            try:
                obj = json.loads(body) if body else None
            except json.JSONDecodeError:
                obj = None
            return status, obj


# ── 목록 URL 빌더 ─────────────────────────────────────────────────────────────────────
# 아래 build_list_path의 인코딩 방식(q는 safe='()._', sr은 기본)은 프로브(2026-09-04)에서
# 실제로 200이 나온 형태를 그대로 옮긴 것 — 임의로 urlencode 등으로 바꾸지 않는다.

def build_list_q(manufacturer: str, model_group: str) -> str:
    return f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{manufacturer}._.ModelGroup.{model_group}.)))"


def build_list_q_nested(manufacturer: str, model_group: str, model: str) -> str:
    """세대(Model) 필터 — 중첩(nested) 형태. discover가 먼저 이걸 시험한다."""
    return (
        f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{manufacturer}._."
        f"(C.ModelGroup.{model_group}._.Model.{model}.))))"
    )


def build_list_q_flat(manufacturer: str, model_group: str, model: str) -> str:
    """세대(Model) 필터 — 평평한(flat) 형태. nested가 실패(400 등)할 때만 시험한다."""
    return (
        f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{manufacturer}._."
        f"ModelGroup.{model_group}._.Model.{model}.)))"
    )


def build_list_path(q: str, offset: int, limit: int) -> str:
    sr = f"|ModifiedDate|{offset}|{limit}"
    return (
        "/search/car/list/premium?count=true&q="
        + urllib.parse.quote(q, safe="()._")
        + "&sr="
        + urllib.parse.quote(sr)
    )


# ── discover ───────────────────────────────────────────────────────────────────────

# (제조사, 모델군) — 모델군 이름을 그대로 파일명 slug로 쓴다(코드베이스 관례상 한글 이름을
# 그대로 키로 쓴다 — seed_depreciation.py의 MANUFACTURER/BODY_TYPE dict 참조).
TARGETS = (
    ("현대", "그랜저"),
    ("기아", "쏘렌토"),
    ("현대", "아반떼"),
)

GEN_FILTER_MANUFACTURER = "현대"
GEN_FILTER_MODEL_GROUP = "그랜저"
GEN_FILTER_TARGET_MODEL = "그랜저 (GN7)"


def _tabulate(rows: list[dict]) -> dict:
    """Model별 건수 + 그 안의 FuelType 분포 + FormYear min/max."""
    models: dict[str, dict] = {}
    for row in rows:
        model = row.get("Model") or "(없음)"
        entry = models.setdefault(
            model, {"count": 0, "fuel": {}, "form_year_min": None, "form_year_max": None}
        )
        entry["count"] += 1
        fuel = row.get("FuelType") or "(없음)"
        entry["fuel"][fuel] = entry["fuel"].get(fuel, 0) + 1
        try:
            fy = int(row.get("FormYear"))
        except (TypeError, ValueError):
            fy = None
        if fy is not None:
            if entry["form_year_min"] is None or fy < entry["form_year_min"]:
                entry["form_year_min"] = fy
            if entry["form_year_max"] is None or fy > entry["form_year_max"]:
                entry["form_year_max"] = fy
    return models


def _fetch_model_group(client: EncarHttpClient, manufacturer: str, model_group: str) -> tuple[list[dict], int | None]:
    """최신순 200건(20×10페이지)을 읽어 원본 행 목록과 첫 페이지 Count를 반환한다."""
    q = build_list_q(manufacturer, model_group)
    rows: list[dict] = []
    count_total = None
    for page in range(10):
        offset = page * 20
        status, obj = client.get_json(build_list_path(q, offset, 20))
        if status != 200 or obj is None:
            print(f"  경고: {manufacturer} {model_group} offset={offset} 조회 실패 status={status}")
            continue
        if page == 0:
            count_total = obj.get("Count")
        rows.extend(obj.get("SearchResults", []))
    return rows, count_total


def _save_list_rows(out_dir: Path, model_group: str, rows: list[dict]) -> None:
    """화이트리스트만 남긴 원본 행을 jsonl로 저장 — probe-accident가 여기서 Id를 읽는다."""
    picked_rows = []
    for row in rows:
        picked = pick_paths(row, LIST_WHITELIST)
        assert_only_whitelisted_keys(picked, LIST_WHITELIST)
        picked_rows.append(picked)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in picked_rows)
    atomic_write_text(out_dir / f"list_discover_{model_group}.jsonl", text)


def _test_generation_filter(
    client: EncarHttpClient, q: str, test_name: str, baseline_count: int | None
) -> dict:
    status, obj = client.get_json(build_list_path(q, 0, 20))
    if status != 200 or obj is None:
        return {"test": test_name, "status": status, "pass": False, "note": "200 아님 또는 본문 없음"}
    count = obj.get("Count")
    models_seen = sorted({r.get("Model") for r in obj.get("SearchResults", [])})
    ok = (
        baseline_count is not None
        and count is not None
        and count < baseline_count
        and models_seen == [GEN_FILTER_TARGET_MODEL]
    )
    note = f"Count={count}(기준={baseline_count}) models_seen={models_seen}"
    return {"test": test_name, "status": status, "pass": ok, "note": note}


def _run_discover_tests(client: EncarHttpClient, grandeur_count_total: int | None) -> list[dict]:
    """limit 50/100, offset 900/1500/3000, 세대필터 — 그랜저 대상, 각 정확히 1회 요청."""
    tests: list[dict] = []
    q = build_list_q(GEN_FILTER_MANUFACTURER, GEN_FILTER_MODEL_GROUP)

    for limit in (50, 100):
        status, obj = client.get_json(build_list_path(q, 0, limit))
        n = len(obj.get("SearchResults", [])) if obj else 0
        tests.append({
            "test": f"limit_{limit}", "status": status,
            "pass": status == 200 and n == limit, "note": f"len(SearchResults)={n}",
        })

    for offset in (900, 1500, 3000):
        status, obj = client.get_json(build_list_path(q, offset, 20))
        n = len(obj.get("SearchResults", [])) if obj else 0
        tests.append({
            "test": f"offset_{offset}", "status": status,
            "pass": status == 200 and n > 0, "note": f"len(SearchResults)={n}",
        })

    nested_q = build_list_q_nested(GEN_FILTER_MANUFACTURER, GEN_FILTER_MODEL_GROUP, GEN_FILTER_TARGET_MODEL)
    nested_test = _test_generation_filter(
        client, nested_q, "generation_filter_nested", grandeur_count_total
    )
    tests.append(nested_test)
    if not nested_test["pass"]:
        flat_q = build_list_q_flat(GEN_FILTER_MANUFACTURER, GEN_FILTER_MODEL_GROUP, GEN_FILTER_TARGET_MODEL)
        flat_test = _test_generation_filter(
            client, flat_q, "generation_filter_flat_fallback", grandeur_count_total
        )
        tests.append(flat_test)

    return tests


def _print_discover_report(result: dict) -> None:
    print("\n=== discover: 모델군별 세대 분포(최신 200건) ===")
    for grp in result["model_groups"]:
        print(
            f"\n[{grp['manufacturer']} {grp['model_group']}] "
            f"Count(전체)={grp['count_total']} 표본={grp['rows_sampled']}"
        )
        print(f"{'Model':28} {'건수':>5}  {'FormYear':10} FuelType(건수)")
        for model, info in sorted(grp["models"].items(), key=lambda kv: -kv[1]["count"]):
            fy_range = f"{info['form_year_min']}~{info['form_year_max']}"
            fuel_str = ", ".join(
                f"{k}:{v}" for k, v in sorted(info["fuel"].items(), key=lambda kv: -kv[1])
            )
            print(f"{model:28} {info['count']:>5}  {fy_range:10} {fuel_str}")

    print("\n=== discover: 시험 결과(limit/offset/세대필터) ===")
    print(f"{'test':28} {'status':>6} {'pass':>5}  note")
    for t in result["tests"]:
        print(f"{t['test']:28} {str(t['status']):>6} {str(t['pass']):>5}  {t['note']}")


def cmd_discover(client: EncarHttpClient, out_dir: Path) -> None:
    result: dict = {
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "model_groups": [],
        "tests": [],
    }
    first_counts: dict[str, int | None] = {}

    try:
        for manufacturer, model_group in TARGETS:
            rows, count_total = _fetch_model_group(client, manufacturer, model_group)
            first_counts[model_group] = count_total
            _save_list_rows(out_dir, model_group, rows)
            result["model_groups"].append({
                "manufacturer": manufacturer,
                "model_group": model_group,
                "count_total": count_total,
                "rows_sampled": len(rows),
                "models": _tabulate(rows),
            })

        result["tests"] = _run_discover_tests(client, first_counts.get(GEN_FILTER_MODEL_GROUP))
    except Forbidden as exc:
        atomic_write_json(out_dir / "discover.json", result)
        print(f"403 — 수집 중단, 당일 재시도 금지 ({exc})")
        sys.exit(3)

    atomic_write_json(out_dir / "discover.json", result)
    _print_discover_report(result)
    print(f"\n총 요청 수: {client.request_count}")


# ── probe-accident ────────────────────────────────────────────────────────────────

ACCIDENT_ENDPOINTS = (
    ("ep1", "/v1/readside/inspection/vehicle/{id}"),
    ("ep2", "/v1/readside/record/vehicle/{id}"),
    ("ep3", "/v1/readside/record/vehicle/{id}/open"),
)


def _load_target_ids(out_dir: Path, n: int) -> list[str]:
    """discover가 저장한 그랜저 jsonl에서 Model == GEN_FILTER_TARGET_MODEL인 Id를 앞에서
    n개 뽑는다(파일 순서 = discover의 ModifiedDate desc 페이지 순서 = 최신순)."""
    jsonl_path = out_dir / f"list_discover_{GEN_FILTER_MODEL_GROUP}.jsonl"
    if not jsonl_path.exists():
        print(f"{jsonl_path}가 없습니다 — 먼저 discover를 실행하세요.")
        sys.exit(1)

    ids: list[str] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("Model") == GEN_FILTER_TARGET_MODEL and row.get("Id"):
                ids.append(row["Id"])
            if len(ids) >= n:
                break
    return ids


def _new_summary() -> dict:
    return {name: {"200": 0, "404": 0, "other": {}} for name, _ in ACCIDENT_ENDPOINTS}


def _finalize_summary(summary: dict, top_keys_seen: dict[str, set]) -> None:
    for name, keys in top_keys_seen.items():
        summary[name]["top_level_keys_seen"] = sorted(keys)


def cmd_probe_accident(client: EncarHttpClient, out_dir: Path, n: int) -> None:
    ids = _load_target_ids(out_dir, n)
    probe_dir = out_dir / "accident_probe"

    summary = _new_summary()
    top_keys_seen: dict[str, set] = {"ep1": set(), "ep2": set()}

    try:
        for vid in ids:
            status, detail_obj = client.get_json(f"/v1/readside/vehicle/{vid}")
            if status == 200 and detail_obj is not None:
                picked = pick_paths(detail_obj, DETAIL_WHITELIST)
                assert_only_whitelisted_keys(picked, DETAIL_WHITELIST)
                atomic_write_json(probe_dir / f"{vid}_detail.json", picked)
            else:
                print(f"경고: {vid} 상세 조회 실패 status={status}")

            for name, path_tmpl in ACCIDENT_ENDPOINTS:
                status, obj = client.get_json(path_tmpl.format(id=vid))
                if status == 200:
                    summary[name]["200"] += 1
                    if obj is not None:
                        if name in top_keys_seen and isinstance(obj, dict):
                            top_keys_seen[name].update(obj.keys())
                        cleaned = strip_forbidden_keys(obj)
                        atomic_write_json(probe_dir / f"{vid}_{name}.json", cleaned)
                elif status == 404:
                    summary[name]["404"] += 1
                else:
                    key = str(status)
                    summary[name]["other"][key] = summary[name]["other"].get(key, 0) + 1
    except Forbidden as exc:
        _finalize_summary(summary, top_keys_seen)
        atomic_write_json(out_dir / "accident_probe_summary.json", summary)
        print(f"403 — 수집 중단, 당일 재시도 금지 ({exc})")
        sys.exit(3)

    _finalize_summary(summary, top_keys_seen)
    atomic_write_json(out_dir / "accident_probe_summary.json", summary)

    print(f"\n대상 id {len(ids)}건 처리 완료")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n총 요청 수: {client.request_count}")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _append_jsonl(path: Path, obj: dict) -> None:
    """manifest.jsonl·failures.jsonl 전용 — 매 호출 append 1줄. 이 두 파일은 실행 중 계속
    자라야 하는 로그라 atomic_write_text(전체 재작성)가 아니라 open('a')로 이어붙인다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ── collect ────────────────────────────────────────────────────────────────────────

# 목록 단계 제외 사유 상수(그대로 progress.json의 excluded 키가 된다) — 문자열을 여기저기
# 흩어 쓰지 않도록 한곳에 모은다.
DETAIL_STAGE_EXCLUSION_REASONS = {"lease_rent", "not_advertise", "no_displacement"}


def _new_target_progress() -> dict:
    return {
        "listed": 0, "excluded": {}, "detail_ok": 0, "accepted": 0,
        "hybrid_accepted": 0, "hybrid_extra": 0, "no_inspection": 0,
        "offset": 0, "count_total": None, "done": False,
        "started": None, "updated": None,
    }


def _load_progress(path: Path) -> dict:
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"경고: {path} 파싱 실패 — 진행상황 새로 시작")
    data.setdefault("targets", {})
    data.setdefault("requests", 0)
    data.setdefault("started", now_iso())
    data.setdefault("updated", now_iso())
    return data


def _load_resume_state(out_dir: Path) -> tuple[set, set]:
    """manifest.jsonl(엔드포인트별 최종 상태)과 raw/*.json(손상 여부·제외사유)을 읽어
    "이미 끝난 id" 집합을 만든다 — 재개 시 이 id는 상세·사고이력 요청을 다시 보내지 않는다.

    DONE(id) = manifest상 detail==200 AND (
                 manifest상 inspection이 200 또는 404로 기록됨
                 OR raw 파일의 exclude_reason이 상세 단계 제외 사유(DETAIL_STAGE_EXCLUSION_REASONS)
               )
    raw JSON은 여기서 딱 1번 파싱한다(그 결과를 곧장 exclude_reason 판정에 쓴다) — 손상된
    파일은 파싱에 실패하므로 자동으로 "안 끝남" 취급(재수집 대상)이 된다.

    반환: (done_ids, all_seen_ids) — all_seen_ids는 manifest·raw에 한 번이라도 등장한 모든 id
    (목록 단계 "이미 본 id" 중복 배제에 쓴다. 이번 실행에서 새로 만나는 id는 호출부가 여기 더한다).
    """
    manifest_path = out_dir / "manifest.jsonl"
    id_status: dict[str, dict[str, int | None]] = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                id_status.setdefault(rec["id"], {})[rec["ep"]] = rec.get("status")

    raw_dir = out_dir / "raw"
    exclude_reason_by_id: dict[str, str | None] = {}
    all_seen_ids = set(id_status)
    if raw_dir.exists():
        for p in raw_dir.glob("*.json"):
            vid = p.stem
            all_seen_ids.add(vid)
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue  # 손상 파일 — done_ids에 못 들어가므로 재수집 대상으로 남는다
            exclude_reason_by_id[vid] = data.get("exclude_reason")

    done_ids = set()
    for vid, st in id_status.items():
        if st.get("detail") != 200:
            continue
        if st.get("inspection") in (200, 404):
            done_ids.add(vid)
        elif exclude_reason_by_id.get(vid) in DETAIL_STAGE_EXCLUSION_REASONS:
            done_ids.add(vid)
    return done_ids, all_seen_ids


def _bump_excluded(tprog: dict, reason: str) -> None:
    tprog.setdefault("excluded", {})
    tprog["excluded"][reason] = tprog["excluded"].get(reason, 0) + 1


def _save_raw(
    raw_dir: Path, vid: str, slug: str, list_picked: dict, detail_picked: dict,
    insp_picked: dict | None, accepted: bool, exclude_reason: str | None,
) -> None:
    record = {
        "encar_id": vid, "target_slug": slug, "collected_at": now_iso(),
        "list": list_picked, "detail": detail_picked, "inspection": insp_picked,
        "accepted": accepted, "exclude_reason": exclude_reason,
    }
    atomic_write_json(raw_dir / f"{vid}.json", record)


def _target_done(tprog: dict, cap: int, hybrid_min: int | None) -> bool:
    """이 세대의 수집을 멈출 때인지 — cap 도달 + (하이브리드 목표 없음 또는 채움 또는
    추가수집 300 도달). cap은 "채택" 행만 센다(제외분은 안 센다)."""
    if tprog.get("accepted", 0) < cap:
        return False
    if hybrid_min is None:
        return True
    if tprog.get("hybrid_accepted", 0) >= hybrid_min:
        return True
    if tprog.get("hybrid_extra", 0) >= 300:
        return True
    return False


def _aggregate_stats(progress: dict) -> tuple[int, int]:
    total_accepted = sum(t.get("accepted", 0) for t in progress.get("targets", {}).values())
    total_excluded = sum(
        sum((t.get("excluded") or {}).values()) for t in progress.get("targets", {}).values()
    )
    return total_accepted, total_excluded


def _maybe_heartbeat(client: EncarHttpClient, progress: dict, run_stats: dict, slug: str) -> None:
    """100요청마다 1줄 — 이미 이 request_count에서 찍었으면 중복 출력하지 않는다."""
    n = client.request_count
    if n <= 0 or n % 100 != 0 or run_stats.get("last_heartbeat") == n:
        return
    run_stats["last_heartbeat"] = n
    accepted, excluded = _aggregate_stats(progress)
    elapsed = time.monotonic() - run_stats["run_start_mono"]
    mm, ss = divmod(int(elapsed), 60)
    print(
        f"누계 요청 {n} · 채택 {accepted} · 제외 {excluded} · "
        f"실패 {run_stats.get('failures', 0)} · 경과 {mm:02d}:{ss:02d} · 현재 대상 {slug}"
    )


def _process_list_row(
    client: EncarHttpClient, raw_dir: Path, manifest_path: Path, failures_path: Path,
    progress_path: Path, target: dict, tprog: dict, row: dict, done_ids: set,
    all_seen_ids: set, fuel_map: dict, progress: dict, run_stats: dict,
) -> None:
    """목록 행 1건 → (제외 판정) → 상세 → (제외 판정) → 사고이력(성능점검부) → raw 저장.
    사유별 순서는 owner 결정 순서(목록: SellType→Price→Badge→ServiceCopyCar→중복→FuelType,
    상세: leaseRentInfo→status→displacement)를 그대로 따른다.
    """
    vid = row.get("Id")
    if not vid:
        return
    if vid in done_ids:
        return  # 이전 실행에서 이미 끝남 — 그때 이미 progress에 반영됐으므로 재집계도 안 함
    if vid in all_seen_ids:
        _bump_excluded(tprog, "duplicate_id")
        return
    if row.get("SellType") != "일반":
        _bump_excluded(tprog, "sell_type")
        return
    price_raw = row.get("Price")
    if price_raw is None or price_raw <= 0:
        _bump_excluded(tprog, "price_invalid")
        return
    badge_text = (row.get("Badge") or "") + (row.get("BadgeDetail") or "")
    if "택시" in badge_text:
        _bump_excluded(tprog, "taxi_badge")
        return
    if row.get("ServiceCopyCar") == "DUPLICATION":
        _bump_excluded(tprog, "duplication")
        return
    normalized_fuel = fuel_map.get(row.get("FuelType"))
    if normalized_fuel is None:
        _bump_excluded(tprog, "unmapped_fuel")
        return

    cap = target["cap"]
    hybrid_min = target.get("hybrid_min")
    hybrid_gate_active = (
        hybrid_min is not None
        and tprog.get("hybrid_accepted", 0) < hybrid_min
        and tprog.get("hybrid_extra", 0) < 300
    )
    is_extra = False
    if tprog.get("accepted", 0) >= cap:
        if not (hybrid_gate_active and normalized_fuel == "하이브리드"):
            _bump_excluded(tprog, "over_cap")
            return
        is_extra = True

    all_seen_ids.add(vid)
    slug = target["slug"]
    list_picked = pick_paths(row, LIST_WHITELIST)
    assert_only_whitelisted_keys(list_picked, LIST_WHITELIST)

    try:
        d_status, detail_obj = client.get_json(f"/v1/readside/vehicle/{vid}")
    except RequestFailed as exc:
        _append_jsonl(
            failures_path,
            {"id": vid, "ep": "detail", "status": exc.status, "error": str(exc), "ts": now_iso()},
        )
        run_stats["failures"] += 1
        _maybe_heartbeat(client, progress, run_stats, slug)
        return
    _append_jsonl(manifest_path, {"id": vid, "ep": "detail", "status": d_status, "ts": now_iso()})
    _maybe_heartbeat(client, progress, run_stats, slug)

    if d_status != 200 or detail_obj is None:
        _bump_excluded(tprog, "detail_unexpected_status")
        return

    detail_picked = pick_paths(detail_obj, DETAIL_WHITELIST)
    assert_only_whitelisted_keys(detail_picked, DETAIL_WHITELIST)
    tprog["detail_ok"] = tprog.get("detail_ok", 0) + 1

    lease = (detail_picked.get("advertisement") or {}).get("leaseRentInfo")
    adv_status = (detail_picked.get("advertisement") or {}).get("status")
    displacement = (detail_picked.get("spec") or {}).get("displacement")

    exclude_reason = None
    if lease is not None:
        exclude_reason = "lease_rent"
    elif adv_status != "ADVERTISE":
        exclude_reason = "not_advertise"
    elif displacement is None or (displacement == 0 and normalized_fuel != "전기"):
        exclude_reason = "no_displacement"

    if exclude_reason is not None:
        _bump_excluded(tprog, exclude_reason)
        _save_raw(raw_dir, vid, slug, list_picked, detail_picked, None, False, exclude_reason)
        return

    try:
        i_status, insp_obj = client.get_json(f"/v1/readside/inspection/vehicle/{vid}")
    except RequestFailed as exc:
        _append_jsonl(
            failures_path,
            {"id": vid, "ep": "inspection", "status": exc.status, "error": str(exc), "ts": now_iso()},
        )
        run_stats["failures"] += 1
        _maybe_heartbeat(client, progress, run_stats, slug)
        return
    _append_jsonl(manifest_path, {"id": vid, "ep": "inspection", "status": i_status, "ts": now_iso()})
    _maybe_heartbeat(client, progress, run_stats, slug)

    if i_status == 200 and insp_obj is not None:
        insp_picked = pick_paths(insp_obj, INSPECTION_WHITELIST)
        assert_only_whitelisted_keys(insp_picked, INSPECTION_WHITELIST)
        accepted = True
        exclude_reason = None
    elif i_status == 404:
        insp_picked = None
        accepted = False
        exclude_reason = "no_inspection"  # owner 결정: 404는 미채택(라더 상수화 방지)
        tprog["no_inspection"] = tprog.get("no_inspection", 0) + 1
    else:
        insp_picked = None
        accepted = False
        exclude_reason = "inspection_unexpected_status"
        _bump_excluded(tprog, "inspection_unexpected_status")

    _save_raw(raw_dir, vid, slug, list_picked, detail_picked, insp_picked, accepted, exclude_reason)

    if accepted:
        tprog["accepted"] = tprog.get("accepted", 0) + 1
        if normalized_fuel == "하이브리드":
            if is_extra:
                tprog["hybrid_extra"] = tprog.get("hybrid_extra", 0) + 1
            else:
                tprog["hybrid_accepted"] = tprog.get("hybrid_accepted", 0) + 1
        if tprog["accepted"] % 20 == 0:
            progress["requests"] = client.request_count
            atomic_write_json(progress_path, progress)


def _run_collect_target(
    client: EncarHttpClient, out_dir: Path, target: dict, targets_data: dict, progress: dict,
    done_ids: set, all_seen_ids: set, fuel_map: dict, run_stats: dict, force: bool = False,
) -> None:
    slug = target["slug"]
    tprog = progress["targets"].setdefault(slug, _new_target_progress())
    if force:
        tprog["done"] = False
    if tprog.get("done"):
        return
    tprog["started"] = tprog.get("started") or now_iso()

    cap = target["cap"]
    hybrid_min = target.get("hybrid_min")
    limit = targets_data["http"]["list_limit"]
    q = build_list_q_nested(target["manufacturer"], target["model_group"], target["encar_model"])
    offset = tprog.get("offset", 0)
    raw_dir = out_dir / "raw"
    manifest_path = out_dir / "manifest.jsonl"
    failures_path = out_dir / "failures.jsonl"
    progress_path = out_dir / "progress.json"

    print(f"\n[{slug}] 수집 시작 offset={offset} cap={cap} hybrid_min={hybrid_min}")

    interrupted = False
    while not _target_done(tprog, cap, hybrid_min):
        try:
            status, obj = client.get_json(build_list_path(q, offset, limit))
        except RequestFailed as exc:
            _append_jsonl(
                failures_path,
                {"id": None, "ep": "list", "status": exc.status, "error": str(exc), "ts": now_iso()},
            )
            run_stats["failures"] += 1
            print(f"  {slug} 목록 조회 반복 실패 — offset={offset}부터 다음 실행에서 재시도")
            interrupted = True
            break
        _maybe_heartbeat(client, progress, run_stats, slug)
        if status != 200 or obj is None:
            print(f"  경고: {slug} offset={offset} 목록 조회 실패 status={status} — 대상 종료")
            interrupted = True
            break

        if tprog.get("count_total") is None:
            tprog["count_total"] = obj.get("Count")
        rows = obj.get("SearchResults", [])
        tprog["listed"] = tprog.get("listed", 0) + len(rows)

        stopped_mid_page = False
        for row in rows:
            if _target_done(tprog, cap, hybrid_min):
                stopped_mid_page = True
                break
            _process_list_row(
                client, raw_dir, manifest_path, failures_path, progress_path,
                target, tprog, row, done_ids, all_seen_ids, fuel_map, progress, run_stats,
            )

        # 상한 도달로 페이지 중간에서 멈췄으면 offset을 넘기지 않는다 — 나중에 상한을 올려
        # 재개할 때 이 페이지의 나머지 행을 다시 읽어야 한다(이미 끝난 id는 done_ids로 건너뜀).
        if not stopped_mid_page:
            offset += limit
        tprog["offset"] = offset
        tprog["updated"] = now_iso()
        progress["requests"] = client.request_count
        atomic_write_json(progress_path, progress)

        count_total = tprog.get("count_total")
        if len(rows) < limit:
            break
        if count_total is not None and tprog["listed"] >= count_total:
            break

    if not interrupted:
        tprog["done"] = True
    tprog["updated"] = now_iso()
    progress["requests"] = client.request_count
    atomic_write_json(progress_path, progress)
    print(
        f"[{slug}] {'완료' if not interrupted else '중단(재개 가능)'} — "
        f"채택 {tprog['accepted']}(하이브리드 {tprog['hybrid_accepted']}+{tprog['hybrid_extra']}) "
        f"무기록 {tprog['no_inspection']} 제외 {sum(tprog['excluded'].values())}"
    )


def _retry_failures(client: EncarHttpClient, out_dir: Path, progress: dict, run_stats: dict) -> None:
    """failures.jsonl 각 항목을 1회만 재시도한다. 성공(200/404 등 예외 없이 반환)하면
    manifest.jsonl에 기록해 다음 collect 실행의 재개 판정(_load_resume_state)이 정상 처리하게
    하고, 그 항목은 failures.jsonl에서 뺀다. 다시 실패하면 남긴다."""
    failures_path = out_dir / "failures.jsonl"
    manifest_path = out_dir / "manifest.jsonl"
    if not failures_path.exists():
        return
    entries = []
    with open(failures_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    if not entries:
        return
    print(f"실패 재시도: {len(entries)}건")
    remaining = []
    for ent in entries:
        vid, ep = ent["id"], ent["ep"]
        if ep == "detail":
            path = f"/v1/readside/vehicle/{vid}"
        elif ep == "inspection":
            path = f"/v1/readside/inspection/vehicle/{vid}"
        else:
            remaining.append(ent)  # list 실패는 offset 재개로 자연 해소 — 재시도 대상 아님
            continue
        try:
            status, _obj = client.get_json(path)
        except RequestFailed as exc:
            remaining.append({"id": vid, "ep": ep, "status": exc.status, "error": str(exc), "ts": now_iso()})
            run_stats["failures"] += 1
            continue
        _append_jsonl(manifest_path, {"id": vid, "ep": ep, "status": status, "ts": now_iso()})
        print(f"  재시도 성공: {vid} {ep} status={status}")
    atomic_write_text(
        failures_path, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in remaining)
    )


def cmd_collect(
    client: EncarHttpClient, out_dir: Path, targets_path: Path, only: str | None,
    cap_override: int | None, retry_failures: bool,
) -> None:
    if not targets_path.exists():
        print(f"{targets_path}가 없습니다.")
        sys.exit(1)
    targets_data = json.loads(targets_path.read_text(encoding="utf-8"))
    fuel_map = targets_data["fuel_map"]

    progress_path = out_dir / "progress.json"
    progress = _load_progress(progress_path)

    done_ids, all_seen_ids = _load_resume_state(out_dir)

    only_slugs = {s.strip() for s in only.split(",")} if only else None
    run_stats = {"failures": 0, "run_start_mono": time.monotonic(), "last_heartbeat": 0}

    try:
        if retry_failures:
            _retry_failures(client, out_dir, progress, run_stats)

        for target in targets_data["targets"]:
            slug = target["slug"]
            forced = only_slugs is not None and slug in only_slugs
            if only_slugs is not None and not forced:
                continue
            if cap_override is not None:
                target = dict(target, cap=cap_override)
            if not forced and progress["targets"].get(slug, {}).get("done"):
                print(f"[{slug}] 이미 완료 — 스킵(--only로 이름을 지정하면 다시 처리)")
                continue
            _run_collect_target(
                client, out_dir, target, targets_data, progress,
                done_ids, all_seen_ids, fuel_map, run_stats, force=forced,
            )
            progress["requests"] = client.request_count
            progress["updated"] = now_iso()
            atomic_write_json(progress_path, progress)
    except Forbidden as exc:
        progress["requests"] = client.request_count
        progress["updated"] = now_iso()
        atomic_write_json(progress_path, progress)
        print(f"403 — 수집 중단, 당일 재시도 금지 ({exc})")
        sys.exit(3)
    except StopRequested as exc:
        progress["requests"] = client.request_count
        progress["updated"] = now_iso()
        atomic_write_json(progress_path, progress)
        print(f"중단 요청 처리됨: {exc}")
        sys.exit(4)

    progress["requests"] = client.request_count
    progress["updated"] = now_iso()
    atomic_write_json(progress_path, progress)
    print(f"\n수집 완료. 총 요청 수: {client.request_count}")


# ── normalize ──────────────────────────────────────────────────────────────────────

# dump_snapshot.py:64-67 LISTING_COLS와 순서·이름이 동일해야 한다(jsonb_populate_recordset
# 적재 호환 — 4단계에서 이 CSV를 그대로 옮겨 쓴다). id·seller_id·seller_name·is_single_owner·
# is_non_smoker·description·created_at·updated_at은 이 스크립트가 채울 수 없는 값이라 항상 빈 값,
# status는 항상 'on_sale'(평가용 매물은 "시장에 나와 있던 상태" 그대로 취급).
LISTING_SNAPSHOT_COLS = (
    "id", "seller_id", "seller_name", "status", "manufacturer", "model", "body_type", "year",
    "price", "mileage", "color", "fuel", "transmission", "displacement", "seats", "region",
    "accident_free", "accident_status", "is_single_owner", "is_non_smoker", "options",
    "description", "created_at", "updated_at",
)

EXTRA_EVAL_COLS = (
    "encar_id", "target_slug", "model_raw", "badge", "badge_detail", "seed_group",
    "resolve_method", "origin_price", "option_count_standard", "option_count_choice",
    "year_month", "list_price", "price_mismatch", "form_year_mismatch", "year_out_of_range",
    "body_type_raw", "color_raw", "region_raw", "seats_imputed", "accident_source",
    "waterlog", "usage_change", "modified_at", "collected_at",
)

CSV_COLUMNS = LISTING_SNAPSHOT_COLS + EXTRA_EVAL_COLS

# ── 정규화 허용 목록 — supabase/migrations/0002_listings.sql(제조사·차종·색상·지역)·
# 0017_listings_trust_attributes.sql(accident_status) CHECK 제약과 동일해야 한다(drift 감시용,
# scripts/seed_depreciation.py의 ALLOWED_* 상수와 같은 출처를 각자 옮겨 적은 것 — 이 스크립트는
# stdlib만 쓰므로 import로 공유하지 않는다). ────────────────────────────────────────────
ALLOWED_MANUFACTURER = {
    "현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티",
    "BMW", "벤츠", "아우디", "폭스바겐", "토요타", "혼다", "렉서스", "테슬라", "기타",
}
ALLOWED_BODY_TYPE = {
    "경차", "소형차", "준중형차", "중형차", "대형차", "스포츠카",
    "SUV", "RV", "경승합차", "승합차", "화물차", "기타",
}
ALLOWED_COLOR = {"흰색", "검정", "회색", "은색", "파랑", "빨강", "갈색", "녹색", "기타"}
ALLOWED_REGION = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
}

BODY_TYPE_MAP = {"경형": "경차", "소형": "소형차", "준중형": "준중형차", "중형": "중형차", "대형": "대형차"}

COLOR_MAP = {
    "흰색": "흰색", "진주색": "흰색", "펄": "흰색",
    "검정색": "검정", "검정": "검정",
    "쥐색": "회색", "회색": "회색", "그레이": "회색", "은회색": "회색",
    "은색": "은색", "실버": "은색",
    "파란색": "파랑", "청색": "파랑", "남색": "파랑", "파랑": "파랑",
    "빨간색": "빨강", "빨강": "빨강", "적색": "빨강",
    "갈색": "갈색", "베이지": "갈색", "브라운": "갈색",
    "녹색": "녹색", "초록": "녹색",
}

# 전체 명칭(행정구역 접미사 포함) 별칭 — 알고 있는 형태를 우선 정확히 맞추고, 그 밖은
# _map_region의 접두 스캔(예: '전남광주'→'전남')으로 넘어간다.
REGION_ALIAS = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
    "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
    "제주특별자치도": "제주", "제주도": "제주",
}

TRANSMISSION_MAP = {"오토": "자동", "CVT": "자동", "세미오토": "자동", "자동": "자동", "수동": "수동"}


def _map_body_type(raw: str | None) -> str:
    if raw in ALLOWED_BODY_TYPE:
        return raw
    return BODY_TYPE_MAP.get(raw, "기타")


def _map_color(raw: str | None) -> str:
    if raw is None:
        return "기타"
    if raw in ALLOWED_COLOR:
        return raw
    return COLOR_MAP.get(raw, "기타")


def _map_region(raw: str | None) -> str | None:
    if raw is None:
        return None
    if raw in ALLOWED_REGION:
        return raw
    if raw in REGION_ALIAS:
        return REGION_ALIAS[raw]
    for canonical in ALLOWED_REGION:
        if raw.startswith(canonical):
            return canonical
    return None


def _resolve_seed_group(target: dict, normalized_fuel: str, displacement: int) -> tuple[str, str]:
    """target.seed_group_rules를 위에서부터 첫 일치로 적용(targets.json naming_rules 그대로)."""
    for i, rule in enumerate(target.get("seed_group_rules") or []):
        if rule.get("fuel") != normalized_fuel:
            continue
        min_cc = rule.get("min_cc")
        if min_cc is not None and displacement < min_cc:
            continue
        return rule["seed_group"], f"rule:{i}"
    return "없음", "none"


def _normalize_row(
    record: dict, targets_by_slug: dict, fuel_map: dict, unmapped_raw: dict,
) -> tuple[dict | None, str | None]:
    """raw/<id>.json(accepted=true) 1건 → CSV 행 dict. 실패하면 (None, 제외사유)."""
    slug = record.get("target_slug")
    target = targets_by_slug.get(slug)
    if target is None:
        return None, "unknown_target_slug"

    list_row = record.get("list") or {}
    detail = record.get("detail") or {}
    inspection = record.get("inspection") or {}
    category = detail.get("category", {})
    spec = detail.get("spec", {})
    advertisement = detail.get("advertisement", {})
    options = detail.get("options", {})
    manage = detail.get("manage", {})
    master = inspection.get("master", {}) if inspection else {}
    master_detail = master.get("detail", {})

    manufacturer_raw = list_row.get("Manufacturer")
    if manufacturer_raw not in ALLOWED_MANUFACTURER:
        unmapped_raw["manufacturer"][manufacturer_raw] = unmapped_raw["manufacturer"].get(manufacturer_raw, 0) + 1
        return None, "unmapped_manufacturer"

    fuel_type_raw = spec.get("fuelName") or list_row.get("FuelType")
    normalized_fuel = fuel_map.get(fuel_type_raw)
    if normalized_fuel is None:
        unmapped_raw["fuel"][fuel_type_raw] = unmapped_raw["fuel"].get(fuel_type_raw, 0) + 1
        return None, "unmapped_fuel"

    transmission_raw = spec.get("transmissionName")
    transmission = TRANSMISSION_MAP.get(transmission_raw)
    if transmission is None:
        unmapped_raw["transmission"][transmission_raw] = unmapped_raw["transmission"].get(transmission_raw, 0) + 1
        return None, "unmapped_transmission"

    model = target["our_model"]
    our_model_by_fuel = target.get("our_model_by_fuel") or {}
    if normalized_fuel in our_model_by_fuel:
        model = our_model_by_fuel[normalized_fuel]

    body_type_raw = spec.get("bodyName")
    body_type = _map_body_type(body_type_raw)
    if body_type_raw not in ALLOWED_BODY_TYPE and body_type_raw not in BODY_TYPE_MAP:
        unmapped_raw["body_type"][body_type_raw] = unmapped_raw["body_type"].get(body_type_raw, 0) + 1

    color_raw = spec.get("colorName")
    color = _map_color(color_raw)
    if color_raw is not None and color_raw not in ALLOWED_COLOR and color_raw not in COLOR_MAP:
        unmapped_raw["color"][color_raw] = unmapped_raw["color"].get(color_raw, 0) + 1

    region_raw = list_row.get("OfficeCityState")
    region = _map_region(region_raw)
    if region is None:
        unmapped_raw["region"][region_raw] = unmapped_raw["region"].get(region_raw, 0) + 1
        return None, "unmapped_region"

    try:
        year = int(list_row.get("FormYear"))
    except (TypeError, ValueError):
        return None, "invalid_form_year"
    year_month = category.get("yearMonth")
    category_form_year = category.get("formYear")
    form_year_mismatch = (
        category_form_year is not None and str(category_form_year) != str(list_row.get("FormYear"))
    )
    lo, hi = target["year_range"]
    year_out_of_range = not (lo <= year <= hi)

    adv_price = advertisement.get("price")
    list_price_raw = list_row.get("Price")
    if adv_price is None or list_price_raw is None:
        return None, "missing_price"
    price = int(round(adv_price * 10_000))
    list_price = int(round(list_price_raw * 10_000))
    price_mismatch = price != list_price

    mileage = spec.get("mileage")
    if mileage is None:
        mileage = list_row.get("Mileage")
    if mileage is None:
        return None, "missing_mileage"
    mileage = int(round(mileage))

    displacement = spec.get("displacement")
    if displacement is None:
        return None, "missing_displacement"  # collect 단계에서 이미 걸러지나 방어적으로 재확인
    displacement = int(displacement)

    seats = spec.get("seatCount")
    seats_imputed = False
    if not seats:
        seats = 5
        seats_imputed = True
    seats = int(seats)

    if not master:
        # collect가 accepted=true인 raw만 여기 넘기므로 사실상 도달 안 함(방어적 재확인).
        return None, "no_inspection"
    accident_status = "사고" if master.get("accdient") else (
        "단순교환" if master.get("simpleRepair") else "무사고"
    )
    accident_free = accident_status == "무사고"

    standard = options.get("standard") or []
    choice = options.get("choice") or []
    options_json = json.dumps(list(standard) + list(choice), ensure_ascii=False)
    origin_price = category.get("originPrice")

    seed_group, resolve_method = _resolve_seed_group(target, normalized_fuel, displacement)

    row = {
        "id": "", "seller_id": "", "seller_name": "", "status": "on_sale",
        "manufacturer": manufacturer_raw, "model": model, "body_type": body_type, "year": year,
        "price": price, "mileage": mileage, "color": color, "fuel": normalized_fuel,
        "transmission": transmission, "displacement": displacement, "seats": seats,
        "region": region, "accident_free": accident_free, "accident_status": accident_status,
        "is_single_owner": "", "is_non_smoker": "", "options": options_json,
        "description": "", "created_at": "", "updated_at": "",
        "encar_id": record.get("encar_id"), "target_slug": slug,
        "model_raw": list_row.get("Model"), "badge": list_row.get("Badge"),
        "badge_detail": list_row.get("BadgeDetail"), "seed_group": seed_group,
        "resolve_method": resolve_method, "origin_price": origin_price,
        "option_count_standard": len(standard), "option_count_choice": len(choice),
        "year_month": year_month, "list_price": list_price, "price_mismatch": price_mismatch,
        "form_year_mismatch": form_year_mismatch, "year_out_of_range": year_out_of_range,
        "body_type_raw": body_type_raw, "color_raw": color_raw, "region_raw": region_raw,
        "seats_imputed": seats_imputed, "accident_source": "inspection",
        "waterlog": master_detail.get("waterlog"),
        "usage_change": ";".join(
            t.get("title", "") for t in (master_detail.get("usageChangeTypes") or [])
        ),
        "modified_at": manage.get("modifyDateTime"), "collected_at": record.get("collected_at"),
    }
    return row, None


def _write_csv(path: Path, rows: list[dict]) -> None:
    tmp_path = Path(str(path) + ".tmp")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp_path.replace(path)


def cmd_normalize(out_dir: Path, targets_path: Path) -> None:
    if not targets_path.exists():
        print(f"{targets_path}가 없습니다.")
        sys.exit(1)
    targets_data = json.loads(targets_path.read_text(encoding="utf-8"))
    targets_by_slug = {t["slug"]: t for t in targets_data["targets"]}
    fuel_map = targets_data["fuel_map"]

    raw_dir = out_dir / "raw"
    rows_read = 0
    excluded: dict[str, int] = {}
    unmapped_raw: dict[str, dict] = {
        "body_type": {}, "color": {}, "region": {}, "fuel": {}, "transmission": {}, "manufacturer": {},
    }
    csv_rows: list[dict] = []

    for path in sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            excluded["corrupt_raw"] = excluded.get("corrupt_raw", 0) + 1
            continue
        if not record.get("accepted"):
            continue
        rows_read += 1
        row, reason = _normalize_row(record, targets_by_slug, fuel_map, unmapped_raw)
        if row is None:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        csv_rows.append(row)

    _write_csv(out_dir / "listings_eval.csv", csv_rows)

    report = {
        "generated_at": now_iso(), "rows_read": rows_read, "rows_written": len(csv_rows),
        "excluded": excluded, "unmapped_raw_values": unmapped_raw,
    }
    atomic_write_json(out_dir / "normalize_report.json", report)
    print(f"normalize 완료 — 읽음(accepted) {rows_read} 씀 {len(csv_rows)}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


# ── summary ────────────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _quantile_summary(values: list[float]) -> dict | None:
    if not values:
        return None
    values = sorted(values)
    n = len(values)

    def pct(p: float) -> float:
        if n == 1:
            return values[0]
        idx = p * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return values[lo] + (values[hi] - values[lo]) * frac

    return {"min": values[0], "q1": pct(0.25), "median": pct(0.5), "q3": pct(0.75), "max": values[-1]}


def _count_true(rows: list[dict], col: str) -> int:
    return sum(1 for r in rows if str(r.get(col)).lower() == "true")


def cmd_summary(out_dir: Path) -> None:
    rows = _read_csv(out_dir / "listings_eval.csv")

    progress_path = out_dir / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}

    manifest_path = out_dir / "manifest.jsonl"
    manifest_requests = 0
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest_requests = sum(1 for _ in f)

    log_path = out_dir / "collect.log"
    gaps: list[float] = []
    log_lines = 0
    if log_path.exists():
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                log_lines += 1
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 4 and parts[3] != "NA":
                    try:
                        gaps.append(float(parts[3]))
                    except ValueError:
                        pass

    per_target = {}
    for slug, tprog in (progress.get("targets") or {}).items():
        per_target[slug] = {
            "listed": tprog.get("listed"), "excluded": tprog.get("excluded"),
            "detail_ok": tprog.get("detail_ok"), "accepted": tprog.get("accepted"),
            "no_inspection": tprog.get("no_inspection"),
        }

    cross: dict[str, dict] = {}
    for r in rows:
        key = f"{r['model']}|{r['fuel']}|{r['year']}"
        entry = cross.setdefault(key, {"n": 0, "mileage": [], "price": []})
        entry["n"] += 1
        try:
            entry["mileage"].append(float(r["mileage"]))
            entry["price"].append(float(r["price"]))
        except (TypeError, ValueError):
            pass
    cross_table = {}
    for key, entry in cross.items():
        mileage_stats = _quantile_summary(entry["mileage"])
        price_stats = _quantile_summary(entry["price"])
        cross_table[key] = {
            "n": entry["n"], "mileage": mileage_stats,
            "price_median": price_stats["median"] if price_stats else None,
        }

    total_rows = len(rows)
    null_rate = {}
    if total_rows:
        for col in CSV_COLUMNS:
            n_null = sum(1 for r in rows if r.get(col) in (None, ""))
            null_rate[col] = n_null / total_rows

    accident_dist: dict[str, int] = {}
    for r in rows:
        accident_dist[r["accident_status"]] = accident_dist.get(r["accident_status"], 0) + 1

    # formats(상세 vehicle 응답의 condition.inspection.formats)가 사고이력(성능점검부) 200/404를
    # 얼마나 잘 예측하는지 보는 교차표 — accepted 여부와 무관하게 raw 전체를 훑는다(제외된 행도
    # 이 질문엔 유효한 표본이다).
    inspection_vs_formats: dict[str, int] = {}
    raw_dir = out_dir / "raw"
    if raw_dir.exists():
        for p in raw_dir.glob("*.json"):
            try:
                record = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            detail = record.get("detail") or {}
            formats = ((detail.get("condition") or {}).get("inspection") or {}).get("formats")
            has_formats = bool(formats)
            had_inspection = record.get("inspection") is not None
            key = (
                f"formats_{'nonempty' if has_formats else 'empty'}_and_"
                f"{'200' if had_inspection else '404'}"
            )
            inspection_vs_formats[key] = inspection_vs_formats.get(key, 0) + 1

    summary = {
        "generated_at": now_iso(),
        "per_target": per_target,
        "cross_table_model_fuel_year": cross_table,
        "null_rate": null_rate,
        "price_mismatch_count": _count_true(rows, "price_mismatch"),
        "form_year_mismatch_count": _count_true(rows, "form_year_mismatch"),
        "year_out_of_range_count": _count_true(rows, "year_out_of_range"),
        "seats_imputed_count": _count_true(rows, "seats_imputed"),
        "accident_status_distribution": accident_dist,
        "inspection_vs_formats": inspection_vs_formats,
        "requests_total_manifest": manifest_requests,
        "requests_total_progress": progress.get("requests"),
        "collect_log_lines": log_lines,
        "request_gap_seconds": {
            "min": min(gaps) if gaps else None, "max": max(gaps) if gaps else None, "count": len(gaps),
        },
    }
    atomic_write_json(out_dir / "summary.json", summary)

    spotcheck_rows = random.sample(rows, min(5, len(rows))) if rows else []
    lines = [
        f"{r['encar_id']}\tmodel={r['model']}\tyear={r['year']}\tmileage={r['mileage']}\tprice={r['price']}"
        for r in spotcheck_rows
    ]
    atomic_write_text(out_dir / "spotcheck.txt", "\n".join(lines) + ("\n" if lines else ""))

    print("summary 완료 (요약, 전문은 summary.json 참조)")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:4000])


# ── CLI ────────────────────────────────────────────────────────────────────────────

def resolve_out_dir(out_dir_arg: str | None) -> Path:
    if out_dir_arg:
        out_dir = Path(out_dir_arg)
    else:
        out_dir = REPO_ROOT / ".logs" / "encar_eval" / datetime.now().strftime("%Y%m%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="평가용 엔카 실매물 수집(비상업·비배포) — discover/probe-accident/collect/normalize/summary",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--out-dir", default=None,
        help="출력 디렉터리(기본: <repo_root>/.logs/encar_eval/<YYYYMMDD>/)",
    )
    common.add_argument(
        "--interval", type=float, default=1.0,
        help="요청 간 최소 간격(초). 하한 1.0으로 clamp(기본 1.0)",
    )
    common.add_argument("--max-requests", type=int, default=15000, help="최대 요청 수(기본 15000)")
    common.add_argument(
        "--max-runtime", type=int, default=18000, help="최대 실행 시간(초, 기본 18000=5시간)"
    )

    sub.add_parser(
        "discover", parents=[common],
        help="모델군 3개 세대분포 표 + limit/offset/세대필터 시험(≈37요청)",
    )

    p_probe = sub.add_parser(
        "probe-accident", parents=[common],
        help="discover가 찾은 그랜저 GN7 id로 사고이력 후보 엔드포인트 3종 시험",
    )
    p_probe.add_argument(
        "--ids-from", default="discover", choices=["discover"],
        help="id 출처(현재는 discover가 저장한 jsonl만 지원)",
    )
    p_probe.add_argument("--n", type=int, default=20, help="시험할 매물 수(기본 20)")

    p_collect = sub.add_parser(
        "collect", parents=[common], help="targets.json 기준 목록→상세→사고이력(성능점검부) 순 수집",
    )
    p_collect.add_argument(
        "--targets", default=None, help="targets.json 경로(기본: <out-dir>/targets.json)",
    )
    p_collect.add_argument(
        "--only", default=None,
        help="쉼표구분 slug 목록만 처리(이미 done이어도 강제로 다시 처리)",
    )
    p_collect.add_argument(
        "--all", action="store_true",
        help="--only 없이 전체 대상 처리(기본 동작과 동일 — 의도 명시용 플래그)",
    )
    p_collect.add_argument(
        "--cap", type=int, default=None, help="처리하는 모든 대상의 cap을 이 값으로 덮어씀",
    )
    p_collect.add_argument(
        "--retry-failures", action="store_true",
        help="failures.jsonl의 각 항목을 1회 재시도 후 남은 실패만 다시 씀",
    )

    p_normalize = sub.add_parser(
        "normalize", parents=[common], help="raw/*.json(accepted=true) → listings_eval.csv",
    )
    p_normalize.add_argument(
        "--targets", default=None, help="targets.json 경로(기본: <out-dir>/targets.json)",
    )

    sub.add_parser(
        "summary", parents=[common],
        help="listings_eval.csv + progress.json + manifest.jsonl + collect.log → summary.json/spotcheck.txt",
    )

    return ap


def main() -> None:
    ap = build_arg_parser()
    args = ap.parse_args()

    out_dir = resolve_out_dir(args.out_dir)

    if args.command == "normalize":
        targets_path = Path(args.targets) if args.targets else out_dir / "targets.json"
        cmd_normalize(out_dir, targets_path)
        return
    if args.command == "summary":
        cmd_summary(out_dir)
        return

    client = EncarHttpClient(
        out_dir,
        interval=args.interval,
        max_requests=args.max_requests,
        max_runtime=args.max_runtime,
    )

    if args.command == "discover":
        cmd_discover(client, out_dir)
    elif args.command == "probe-accident":
        cmd_probe_accident(client, out_dir, args.n)
    elif args.command == "collect":
        targets_path = Path(args.targets) if args.targets else out_dir / "targets.json"
        cmd_collect(client, out_dir, targets_path, args.only, args.cap, args.retry_failures)


if __name__ == "__main__":
    main()
