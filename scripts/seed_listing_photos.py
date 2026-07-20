# -*- coding: utf-8 -*-
"""Wikimedia Commons 실차 사진으로 시드 매물에 사진을 채운다 (Story 9.7 소싱 절차의 구현).

계획 근거: PRD OI-5 · addendum F7 · epics Story 9.7.
  - 시드의 (제조사 + 모델)로 Commons 검색 → CC-BY/CC-BY-SA/CC0/PD만 → 매물당 1~3장
  - 이미지별 저작자·라이선스·원본링크를 listing_images.credit(jsonb)에 저장(㉠ — CC BY-SA가 다수라 필수)

⚠️ 이 스크립트가 지키는 규칙 (어기면 이 프로젝트의 계약이 깨진다):
  1. **service_role 키를 쓰지 않는다** (docs/conventions.md §5). 시드 판매자 계정으로 실제 로그인해
     그 사용자의 JWT로 업로드한다 — 브라우저가 하는 것과 정확히 같은 경로다.
     따라서 Storage RLS(경로 첫 세그먼트 = 소유자)와 0013 경로 무결성 트리거가 그대로 적용된다.
  2. **저장본 규격을 업로더와 맞춘다** — 긴 변 ≤1600px · WebP · q0.82 (docs/conventions.md §10.1).
     Commons 원본은 수 MB라 그대로 올리면 목록에서 NFR7(저비용 서빙)이 깨진다.
  3. **대표 = sort_order 0번**, is_cover는 그 파생 결과로만 기록(§10.1).
  4. **행 INSERT는 순차(직렬)** — 10장 트리거가 count-후-insert라 병렬은 경합으로 샌다(tech-debt #49).

의존성: requests, Pillow. **api/ 가상환경에 넣지 않는다** — api는 Cloud Run 이미지라 시드 도구로 부풀리지 않는다.
  python3 -m venv .venv && .venv/bin/pip install requests Pillow     # 루트 .venv/ 는 .gitignore 처리됨
  .venv/bin/python scripts/seed_listing_photos.py --limit 5 [--dry-run]

재실행하면 **사진이 이미 있는 매물은 건너뛰고 다음 매물로** 넘어간다 — listing_images 사전조회가
페이지네이션으로 전체 행을 순회하므로(fetch_already_seeded_ids), 테이블 크기가 PostgREST의
페이지 상한을 넘어도 already 판단에 구멍이 생기지 않는다(불변식; 재실행 자체를 실측하지는 않음).

환경: web/.env.local(NEXT_PUBLIC_SUPABASE_URL·ANON_KEY) · supabase/.env.seed(SEED_PASSWORD)에서 읽는다.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import unicodedata
import uuid
from collections import Counter
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

BUCKET = "listing-images"
MAX_EDGE = 1600          # docs/conventions.md §10.1
WEBP_QUALITY = 82        # 0.82
UA = "bmad-encar-demo/1.0 (demo seed tooling; https://commons.wikimedia.org/wiki/Commons:API)"

# Commons는 한글 모델명을 못 찾는다 — 검색어만 영문으로 옮긴다(DB 값은 건드리지 않는다).
# 커버리지는 2026-07-12 API probe로 확인됨(DN8·MQ4·DL3·RG3 등 국산 세대코드까지 매칭).
#
# ⚠️ 키는 (제조사, 모델) **정확 일치**다. DB에 표기 흔들림이 실재하므로(`니로 EV`/`니로EV`,
#    `아반떼 MD`/`아반떼MD`) **DB 값을 고치지 말고 변형을 각각 키로 넣는다**(Story 9.7 결정).
# ⚠️ Commons 검색은 정확 일치가 아니라 관련도 순 전문검색이다 — 결과가 나온다고 그 차종인 건
#    아니다. 2026-07-21 실측으로 후보 59종의 반환 제목을 눈으로 확인했고, 아래 주석의
#    "≈" 표시가 붙은 것은 **같은 계열 다른 배지가 섞이는 것을 알고 수용한 자리**다.
#    (대조군: 존재하지 않는 검색어는 0건을 돌려준다 — 검색이 실제로 거르고 있음을 확인)
SEARCH_TERMS = {
    # ── 현대 ──
    ("현대", "쏘나타 DN8"): "Hyundai Sonata DN8",
    ("현대", "쏘나타"): "Hyundai Sonata",
    ("현대", "팰리세이드"): "Hyundai Palisade",
    ("현대", "아반떼 CN7"): "Hyundai Avante CN7",
    ("현대", "아반떼 MD"): "Hyundai Avante MD",
    ("현대", "아반떼MD"): "Hyundai Avante MD",
    ("현대", "아반떼"): "Hyundai Avante",
    ("현대", "아반떼 하이브리드"): "Hyundai Avante hybrid",
    ("현대", "그랜저 IG"): "Hyundai Grandeur IG",
    ("현대", "그랜저 GN7"): "Hyundai Grandeur GN7",
    ("현대", "그랜저 GN7 하이브리드"): "Hyundai Grandeur GN7",
    ("현대", "그랜저"): "Hyundai Grandeur",
    ("현대", "싼타페 TM"): "Hyundai Santa Fe TM",
    ("현대", "싼타페"): "Hyundai Santa Fe",
    ("현대", "투싼 NX4"): "Hyundai Tucson NX4",
    ("현대", "투싼"): "Hyundai Tucson",
    ("현대", "코나 일렉트릭"): "Hyundai Kona Electric",   # ≈ 제네바 전시 사진이 일부 섞임
    ("현대", "코나"): "Hyundai Kona",
    ("현대", "아이오닉5"): "Hyundai Ioniq 5",
    ("현대", "아이오닉6"): "Hyundai Ioniq 6",
    ("현대", "스타리아"): "Hyundai Staria",
    ("현대", "베뉴"): "Hyundai Venue",
    ("현대", "캐스퍼"): "Hyundai Casper",
    ("현대", "포터2"): "Hyundai Porter",
    # ── 기아 ──
    ("기아", "카니발 KA4"): "Kia Carnival KA4",
    ("기아", "카니발"): "Kia Carnival",
    ("기아", "쏘렌토 MQ4"): "Kia Sorento MQ4",
    ("기아", "쏘렌토"): "Kia Sorento",
    ("기아", "K5 DL3"): "Kia K5 DL3",
    ("기아", "K5"): "Kia K5",
    ("기아", "K8"): "Kia K8",
    ("기아", "K3"): "Kia K3",
    ("기아", "EV6"): "Kia EV6",
    ("기아", "니로 EV"): "Kia Niro EV",
    ("기아", "니로EV"): "Kia Niro EV",
    ("기아", "셀토스"): "Kia Seltos",
    ("기아", "스포티지 하이브리드"): "Kia Sportage hybrid",
    ("기아", "쏘울"): "Kia Soul",
    ("기아", "레이"): "Kia Ray",                          # ≈ Ray 컨셉카가 일부 섞임
    ("기아", "모닝"): "Kia Picanto",                       # 모닝의 수출명이 Picanto
    ("기아", "모닝 JA"): "Kia Picanto JA",
    ("기아", "봉고3"): "Kia Bongo",                        # ≈ 형제차 K2500/K2700이 섞임
    # ── 제네시스 ──
    ("제네시스", "GV70"): "Genesis GV70",
    ("제네시스", "G80"): "Genesis G80",
    ("제네시스", "G80 RG3"): "Genesis G80 RG3",
    ("제네시스", "G70"): "Genesis G70",
    # ── KG모빌리티 ──
    ("KG모빌리티", "토레스"): "KG Mobility Torres",
    ("KG모빌리티", "렉스턴"): "SsangYong Rexton",
    ("KG모빌리티", "티볼리"): "SsangYong Tivoli",
    # ── 르노코리아 · 쉐보레 ──
    ("르노코리아", "SM6"): "Renault Samsung SM6",
    ("르노코리아", "QM6"): "Renault Samsung QM6",
    ("르노코리아", "XM3"): "Renault Samsung XM3",
    ("쉐보레", "말리부"): "Chevrolet Malibu",
    ("쉐보레", "스파크"): "Chevrolet Spark",
    ("쉐보레", "트랙스"): "Chevrolet Trax",
    ("쉐보레", "트레일블레이저"): "Chevrolet Trailblazer 2020",  # 연식을 붙여야 국내형 세대가 잡힘
    ("쉐보레", "올란도"): "Chevrolet Orlando",
    # ── 수입 ──
    ("BMW", "X3"): "BMW X3",
    ("BMW", "520i"): "BMW 520i",
    ("BMW", "320i"): "BMW 320i",
    ("BMW", "M4"): "BMW M4",
    ("벤츠", "E250"): "Mercedes-Benz E-Class W213",
    ("벤츠", "GLE450"): "Mercedes-Benz GLE-Class",
    ("아우디", "Q5"): "Audi Q5",
    ("아우디", "A6 40 TDI"): "Audi A6 C8",
    ("폭스바겐", "티구안"): "Volkswagen Tiguan",
    ("토요타", "캠리 하이브리드"): "Toyota Camry hybrid",
    ("토요타", "캠리"): "Toyota Camry",
    ("혼다", "CR-V"): "Honda CR-V",
    ("렉서스", "ES300h"): "Lexus ES 300h",
    ("테슬라", "모델3"): "Tesla Model 3",
    ("테슬라", "모델S"): "Tesla Model S",
    ("테슬라", "모델Y"): "Tesla Model Y",
    ("기타", "볼보 XC60"): "Volvo XC60",
}

def is_license_allowed(license_name: str) -> bool:
    """CC-BY/CC-BY-SA/CC0/PD만 통과시킨다. CC BY-SA 포함이라 크레딧 저장이 필수(㉠).

    NC(비영리)·ND(변경금지) 성분은 반려한다 — 특히 ND가 중요한 이유: 이 스크립트가
    to_storage_webp()로 리사이즈·재인코딩을 하는데, 그 자체가 2차적 저작물이라 ND와
    정면으로 충돌한다(코드리뷰 지적).

    느슨한 문자열 접두어 매칭(예: "cc by".startswith 검사)은 "CC BY-NC-SA 4.0"도
    통과시켜 버린다 — 그래서 라이선스 성분을 공백/하이픈 기준 토큰으로 쪼개 "nc"/"nd"
    토큰이 있는지로 판정한다(부분 문자열이 아니라 토큰 경계 매칭).
    """
    name = (license_name or "").strip().lower()
    if not name:
        return False
    if name.startswith("cc0") or name.startswith("public domain"):
        return True
    if re.match(r"^pd\b", name):
        return True
    if not re.match(r"^cc[\s-]*by\b", name):
        return False
    tokens = re.split(r"[\s-]+", name)
    return "nc" not in tokens and "nd" not in tokens


# 위 함수의 애매한 사례를 import 시점에 확인한다(네트워크·DB 접근 없음, 순수 함수 자체 점검).
assert is_license_allowed("CC BY-SA 4.0") is True
assert is_license_allowed("CC0") is True
assert is_license_allowed("CC BY 2.0") is True
assert is_license_allowed("CC BY-NC-SA 4.0") is False
assert is_license_allowed("CC BY-ND 4.0") is False
assert is_license_allowed("CC BY-NC-ND 3.0") is False


def read_env(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return None


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def commons_search(term: str, limit: int) -> list[dict]:
    """Commons에서 파일을 찾아 라이선스가 허용된 것만 돌려준다."""
    r = requests.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "format": "json",
            "generator": "search", "gsrsearch": term,
            "gsrnamespace": 6, "gsrlimit": limit * 4,   # 필터로 걸러질 것을 감안해 넉넉히
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        },
        headers={"User-Agent": UA}, timeout=30,
    )
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})

    out = []
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        license_name = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        mime = info.get("mime", "")

        if not mime.startswith("image/") or mime == "image/svg+xml":
            continue
        if not is_license_allowed(license_name):
            continue

        out.append({
            "title": p.get("title"),
            "url": info.get("url"),
            "license": license_name,
            "author": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "source": info.get("descriptionurl") or info.get("url"),
        })
    return out[:limit]


def to_storage_webp(raw: bytes) -> bytes:
    """업로더와 같은 규격으로 다시 인코딩한다 — 긴 변 ≤1600px, WebP q82."""
    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":                      # WebP 알파는 카드에서 의미 없다 — 흰 배경으로 평탄화
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg

    w, h = img.size
    if max(w, h) > MAX_EDGE:
        scale = MAX_EDGE / max(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY)
    return buf.getvalue()


def fetch_already_seeded_ids(supa_url: str, rest: dict) -> set[str]:
    """listing_images에 이미 행이 있는 listing_id 전체를 모은다(재실행 시 건너뛸 대상).

    PostgREST는 한 번에 돌려주는 행 수에 상한이 있다(보통 1000행) — 넘으면 나머지를 잘라
    HTTP 206(Partial Content)으로 응답하는데, raise_for_status()는 206도 성공으로 본다.
    그걸 그대로 쓰면 already가 상한을 넘는 순간부터 조용히 일부만 채워지고, 그 매물들은
    재실행 때마다 다시 시드돼 sort_order 중복과 is_cover 중복(부분 유니크 인덱스 위반)을
    만든다. 그래서 Range 헤더로 페이지를 명시적으로 넘겨가며, 요청한 페이지 크기보다 적게
    돌아올 때까지(=마지막 페이지) 반복한다.
    """
    page_size = 1000
    ids: set[str] = set()
    start = 0
    while True:
        r = requests.get(
            f"{supa_url}/rest/v1/listing_images",
            headers={**rest, "Range-Unit": "items", "Range": f"{start}-{start + page_size - 1}"},
            params={"select": "listing_id"}, timeout=30,
        )
        if r.status_code not in (200, 206):
            r.raise_for_status()
        rows = r.json()
        ids.update(row["listing_id"] for row in rows)
        if len(rows) < page_size:
            break
        start += page_size
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="사진을 채울 매물 수")
    ap.add_argument("--email", default="seller-seed@test.com")
    ap.add_argument("--dry-run", action="store_true", help="업로드하지 않고 무엇을 할지만 출력")
    args = ap.parse_args()

    supa_url = read_env(ROOT / "web/.env.local", "NEXT_PUBLIC_SUPABASE_URL")
    anon = read_env(ROOT / "web/.env.local", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    password = read_env(ROOT / "supabase/.env.seed", "SEED_PASSWORD")
    if not (supa_url and anon and password):
        print("환경값이 없습니다: web/.env.local(URL·ANON_KEY) · supabase/.env.seed(SEED_PASSWORD)")
        return 1

    # ── 1) 시드 판매자로 로그인 (service_role 아님 — 브라우저와 같은 경로) ──
    auth = requests.post(
        f"{supa_url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon, "Content-Type": "application/json"},
        json={"email": args.email, "password": password}, timeout=30,
    )
    if auth.status_code != 200:
        print("로그인 실패:", auth.status_code, auth.text[:200])
        return 1
    session = auth.json()
    jwt, uid = session["access_token"], session["user"]["id"]
    rest = {"apikey": anon, "Authorization": f"Bearer {jwt}"}
    print(f"로그인 성공 — {args.email} ({uid})")

    # ── 2) 사진이 아직 없는 on_sale 매물 고르기 (재실행해도 중복으로 안 넣게) ──
    already = fetch_already_seeded_ids(supa_url, rest)

    got = requests.get(
        f"{supa_url}/rest/v1/listings", headers=rest,
        params={"select": "id,manufacturer,model,year", "seller_id": f"eq.{uid}",
                "status": "eq.on_sale", "order": "created_at.desc,id.desc"},
        timeout=30,
    )
    got.raise_for_status()

    # 대응표 조회 전에 표기를 다듬는다(코드리뷰 2026-07-21). `model`은 자유 입력 컬럼이라
    # 앞뒤 공백·유니코드 조합형(맥에서 복사한 한글은 NFD로 들어온다)이 실제로 섞일 수 있는데,
    # 정확 일치 딕셔너리는 그걸 **아무 로그 없이** 미스로 처리한다. 변형을 키로 늘리는 방식으로는
    # 이 축을 못 잡는다 — 표기 변형(`아반떼MD`)과 공백/조합형은 다른 문제다.
    def _norm(s: str) -> str:
        return unicodedata.normalize("NFC", (s or "").strip())

    targets = []
    unmatched: Counter[tuple[str, str]] = Counter()   # 대응표에 없는 (제조사, 모델) 집계
    for row in got.json():
        if row["id"] in already:
            continue
        key = (_norm(row["manufacturer"]), _norm(row["model"]))
        term = SEARCH_TERMS.get(key)
        if not term:
            # ⚠️ 세지 않으면 사유표를 만들 수 없다(스토리 9.7 AC1). 예전엔 그냥 continue라,
            #    몇 건이 대응표 미스로 빠졌는지 **실행 결과만 봐서는 알 수 없었다** —
            #    이번엔 별도 SQL로 외부 측정해 "0건"이라 적었지만 다음 실행자에겐 그 수단이 없다.
            unmatched[key] += 1
            continue
        # ⚠️ 상한 검사는 append **앞**에 둔다 — 뒤에 두면 `--limit 0`이 `len==1 >= 0`이 되어
        #    "아무것도 안 하고 확인만" 의도로 0을 줬는데 1건이 실제로 시딩된다(코드리뷰 2026-07-21).
        if len(targets) >= args.limit:
            break
        targets.append((row, term))

    if unmatched:
        print(f"\n대응표에 없어 건너뛴 매물 {sum(unmatched.values())}건 "
              f"({len(unmatched)}종) — SEARCH_TERMS에 추가하면 다음 실행에서 채워진다:")
        for (mfr, model), n in unmatched.most_common():
            print(f"   · ({mfr}, {model}) — {n}건")

    if not targets:
        print("대상 매물이 없습니다(이미 사진이 있거나 검색어 매핑이 없음).")
        return 0

    # 장수를 일부러 섞는다 — "N장" 배지와 플레이스홀더가 한 화면에 같이 보여야 9.4를 검증할 수 있다.
    counts = [3, 1, 2, 3, 1, 2, 3, 1]
    total_rows = 0

    for idx, (row, term) in enumerate(targets):
        want = counts[idx % len(counts)]
        label = f"[{row['manufacturer']}] {row['model']} {row['year']}"
        print(f"\n── {label} — Commons '{term}' 에서 {want}장")

        try:
            found = commons_search(term, want)
        except Exception as exc:                       # noqa: BLE001 — 한 매물 실패가 전체를 멈추지 않게
            print(f"   검색 실패: {exc}")
            continue
        if not found:
            print("   허용 라이선스 결과 없음 — 건너뜀")
            continue

        saved_count = 0   # 후보 인덱스(cand_idx)가 아니라 **실제로 저장에 성공한 개수** — 아래 참조.
        for cand_idx, item in enumerate(found):
            try:
                # raise_for_status()가 없으면 429(레이트리밋)·503의 에러 HTML이 그대로 PIL로
                # 넘어가 "cannot identify image file"이 된다 — **레이트리밋과 진짜 손상 파일이
                # 구분되지 않는다.** 90매물 × 최대 3장을 도는 실행에서 이건 원인 모를 대량 스킵이
                # 된다(코드리뷰 2026-07-21).
                resp = requests.get(item["url"], headers={"User-Agent": UA}, timeout=60)
                resp.raise_for_status()
                blob = to_storage_webp(resp.content)
            except Exception as exc:                   # noqa: BLE001
                print(f"   {cand_idx}: 다운로드/변환 실패 — {exc}")
                continue

            path = f"{uid}/{row['id']}/{uuid.uuid4()}.webp"
            if args.dry_run:
                print(f"   {cand_idx}: (dry-run) {len(blob)//1024}KB · {item['license']} · {item['title']}")
                continue

            up = requests.post(
                f"{supa_url}/storage/v1/object/{BUCKET}/{path}",
                headers={**rest, "Content-Type": "image/webp"}, data=blob, timeout=120,
            )
            if up.status_code not in (200, 201):
                print(f"   {cand_idx}: 업로드 실패 {up.status_code} {up.text[:160]}")
                continue

            # 행은 순차로(#49). sort_order/is_cover는 idx(후보 인덱스)가 아니라 saved_count로
            # 매긴다 — 다운로드·변환·업로드 실패로 건너뛴 후보가 있어도 구멍이 남지 않는다.
            # 대표 = sort_order 0번, is_cover는 그 파생(§10.1). web/.../photo-sync.ts:174와 같은 이유.
            order = saved_count
            ins = requests.post(
                f"{supa_url}/rest/v1/listing_images",
                headers={**rest, "Content-Type": "application/json", "Prefer": "return=representation"},
                json={
                    "listing_id": row["id"], "storage_path": path,
                    "sort_order": order, "is_cover": order == 0,
                    "credit": {"author": item["author"], "license": item["license"],
                               "source": item["source"], "title": item["title"]},
                },
                timeout=30,
            )
            if ins.status_code not in (200, 201):
                print(f"   {cand_idx}: 행 INSERT 실패 {ins.status_code} {ins.text[:160]}")
                # 오브젝트는 이미 올라갔는데 그걸 가리키는 행이 없다 — 아무도 못 읽는 고아가
                # 남는다. 그대로 두지 말고 방금 올린 오브젝트를 지워 정리한다(photo-sync.ts의
                # deleteListingImageObject와 같은 이유). 정리 자체의 성패도 삼키지 않고 남긴다.
                cleanup = requests.delete(
                    f"{supa_url}/storage/v1/object/{BUCKET}/{path}", headers=rest, timeout=30,
                )
                if cleanup.status_code in (200, 204):
                    print(f"   {cand_idx}: 고아 오브젝트 정리 성공")
                else:
                    print(f"   {cand_idx}: 고아 오브젝트 정리 실패 {cleanup.status_code} "
                          f"{cleanup.text[:160]} — 수동 확인 필요")
                continue

            saved_count += 1
            total_rows += 1
            print(f"   {cand_idx}{' (대표)' if order == 0 else ''}: {len(blob)//1024}KB · {item['license']}")

    print(f"\n완료 — listing_images {total_rows}행 생성")
    return 0


if __name__ == "__main__":
    sys.exit(main())
