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

재실행하면 **사진이 이미 있는 매물은 건너뛰고 다음 매물로** 넘어간다(중복 삽입 없음, 실측 확인).

환경: web/.env.local(NEXT_PUBLIC_SUPABASE_URL·ANON_KEY) · supabase/.env.seed(SEED_PASSWORD)에서 읽는다.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import uuid
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
SEARCH_TERMS = {
    ("현대", "쏘나타 DN8"): "Hyundai Sonata DN8",
    ("현대", "팰리세이드"): "Hyundai Palisade",
    ("현대", "아반떼 CN7"): "Hyundai Avante CN7",
    ("현대", "그랜저 IG"): "Hyundai Grandeur IG",
    ("기아", "카니발 KA4"): "Kia Carnival KA4",
    ("기아", "쏘렌토 MQ4"): "Kia Sorento MQ4",
    ("기아", "K5 DL3"): "Kia K5 DL3",
    ("제네시스", "GV70"): "Genesis GV70",
    ("제네시스", "G80"): "Genesis G80",
    ("BMW", "X3"): "BMW X3",
    ("BMW", "520i"): "BMW 520i",
    ("벤츠", "E250"): "Mercedes-Benz E-Class W213",
    ("토요타", "캠리 하이브리드"): "Toyota Camry hybrid",
    ("쉐보레", "말리부"): "Chevrolet Malibu",
    ("르노코리아", "SM6"): "Renault Samsung SM6",
}

# 허용 라이선스(접두어 매칭). CC BY-SA 포함이라 크레딧 저장이 필수(㉠).
ALLOWED_LICENSE_PREFIXES = ("cc by", "cc0", "public domain", "cc-by", "pd")


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
        if not license_name.lower().startswith(ALLOWED_LICENSE_PREFIXES):
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
    have = requests.get(
        f"{supa_url}/rest/v1/listing_images",
        headers=rest, params={"select": "listing_id"}, timeout=30,
    )
    have.raise_for_status()
    already = {r["listing_id"] for r in have.json()}

    got = requests.get(
        f"{supa_url}/rest/v1/listings", headers=rest,
        params={"select": "id,manufacturer,model,year", "seller_id": f"eq.{uid}",
                "status": "eq.on_sale", "order": "created_at.desc,id.desc"},
        timeout=30,
    )
    got.raise_for_status()

    targets = []
    for row in got.json():
        if row["id"] in already:
            continue
        term = SEARCH_TERMS.get((row["manufacturer"], row["model"]))
        if not term:
            continue
        targets.append((row, term))
        if len(targets) >= args.limit:
            break

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

        for order, item in enumerate(found):
            try:
                raw = requests.get(item["url"], headers={"User-Agent": UA}, timeout=60).content
                blob = to_storage_webp(raw)
            except Exception as exc:                   # noqa: BLE001
                print(f"   {order}: 다운로드/변환 실패 — {exc}")
                continue

            path = f"{uid}/{row['id']}/{uuid.uuid4()}.webp"
            if args.dry_run:
                print(f"   {order}: (dry-run) {len(blob)//1024}KB · {item['license']} · {item['title']}")
                continue

            up = requests.post(
                f"{supa_url}/storage/v1/object/{BUCKET}/{path}",
                headers={**rest, "Content-Type": "image/webp"}, data=blob, timeout=120,
            )
            if up.status_code not in (200, 201):
                print(f"   {order}: 업로드 실패 {up.status_code} {up.text[:160]}")
                continue

            # 행은 순차로(#49). 대표 = sort_order 0번, is_cover는 그 파생(§10.1).
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
                print(f"   {order}: 행 INSERT 실패 {ins.status_code} {ins.text[:160]}")
                continue

            total_rows += 1
            print(f"   {order}{' (대표)' if order == 0 else ''}: {len(blob)//1024}KB · {item['license']}")

    print(f"\n완료 — listing_images {total_rows}행 생성")
    return 0


if __name__ == "__main__":
    sys.exit(main())
