"""운영에서 사진 없는 매물에 기존 사진을 복사해 붙인다(REST + Storage API, 판매자 본인 토큰).

로컬용 copy_photos.py와 같은 규칙. 다른 점은 경로(psql → REST)와 인증(secret → 판매자 JWT).
0013 트리거가 storage_path를 `{소유자}/{매물}/{파일}`로 강제하므로 참조가 아니라 복사다.

파일명은 (매물, 순번)에서 uuid5로 결정론 생성 — 실패 후 재실행해도 같은 경로를 덮어써서
스토리지에 고아가 쌓이지 않는다(로컬에서 실제로 138장 고아를 만들고 배운 것).
"""

import json
import random
import sys
import urllib.error
import urllib.request
import uuid

PROD = "https://psrnsasxpkpwqdukjdmt.supabase.co"
BUCKET = "listing-images"
APPLY = "--apply" in sys.argv
_NS = uuid.UUID("6f1c3a5e-9b2d-4c7a-8e15-2f0d7b4a9c31")

ANON = [l.split("=", 1)[1].strip() for l in open("web/.env.prod")
        if l.startswith("NEXT_PUBLIC_SUPABASE_ANON_KEY=")][0]
SEED_PW = [l.split("=", 1)[1].strip() for l in open("supabase/.env.seed")
           if l.startswith("SEED_PASSWORD=")][0]
ACCOUNTS = {
    "12dfba00-2544-45f4-8ffe-bdeb32229b97": ("seller-seed@test.com", SEED_PW),
    "0f937a74-48ee-4e3a-9e78-4a3d85645727": ("seller-seed2@test.com", SEED_PW),
    "c19a85e7-6e23-432f-aa1c-efc57f1782af": ("seller-seed3@test.com", SEED_PW),
    "748caac4-5e45-403c-b8ee-1f5ccc16b813": ("seller@test.com", "seller123"),
}
rng = random.Random(20260805)


def login(email, pw):
    req = urllib.request.Request(f"{PROD}/auth/v1/token?grant_type=password",
                                 data=json.dumps({"email": email, "password": pw}).encode(),
                                 method="POST")
    for k, v in (("apikey", ANON), ("Authorization", f"Bearer {ANON}"),
                 ("Content-Type", "application/json")):
        req.add_header(k, v)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]


def rest(method, path, token, body=None, extra=None):
    req = urllib.request.Request(f"{PROD}/rest/v1/{path}",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method)
    for k, v in (("apikey", ANON), ("Authorization", f"Bearer {token}"),
                 ("Content-Type", "application/json")):
        req.add_header(k, v)
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def fetch(path):
    with urllib.request.urlopen(
            f"{PROD}/storage/v1/object/public/{BUCKET}/{urllib.request.quote(path)}",
            timeout=60) as r:
        data = r.read()
    if not data:
        raise RuntimeError(f"0바이트: {path}")
    return data


def upload(path, blob, token):
    req = urllib.request.Request(
        f"{PROD}/storage/v1/object/{BUCKET}/{urllib.request.quote(path)}",
        data=blob, method="POST")
    req.add_header("apikey", ANON)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "image/webp")
    req.add_header("x-upsert", "true")
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"업로드 {r.status}")


tokens = {s: login(e, p) for s, (e, p) in ACCOUNTS.items()}
tok0 = next(iter(tokens.values()))

listings = rest("GET", "listings?status=eq.on_sale&select=id,seller_id,body_type"
                       "&order=id.asc&limit=2000", tok0)
images = rest("GET", "listing_images?select=listing_id,storage_path,sort_order,credit"
                     "&limit=5000", tok0)
have = {i["listing_id"] for i in images}
bt_of = {l["id"]: l["body_type"] for l in listings}

by_type, every = {}, []
for i in images:
    bt = bt_of.get(i["listing_id"])
    by_type.setdefault(bt, []).append((i["storage_path"], i.get("credit")))
    every.append((i["storage_path"], i.get("credit")))

targets = [l for l in listings if l["id"] not in have]
print(f"운영 판매중 {len(listings)}건 · 사진 없는 매물 {len(targets)}건 · 원본 풀 {len(every)}장")
if not targets:
    print("할 일 없음")
    raise SystemExit(0)

plan = []
for l in targets:
    pool = by_type.get(l["body_type"]) or every
    n = rng.choice([1, 2, 2, 3])
    for order, (src, credit) in enumerate(rng.sample(pool, min(n, len(pool)))):
        name = uuid.uuid5(_NS, "{}:{}".format(l["id"], order))
        dst = "{}/{}/{}.webp".format(l["seller_id"], l["id"], name)
        plan.append((l["id"], l["seller_id"], src, dst, order, order == 0, credit))

print(f"복사 계획 {len(plan)}장 (매물당 평균 {len(plan)/len(targets):.1f}장)")
if not APPLY:
    print("(미적용 — 실제 반영은 --apply)")
    raise SystemExit(0)

ok, fails = 0, []
for lid, seller, src, dst, order, cover, credit in plan:
    tok = tokens.get(seller)
    try:
        upload(dst, fetch(src), tok)
        rest("POST", "listing_images", tok,
             [{"listing_id": lid, "storage_path": dst, "sort_order": order,
               "is_cover": cover, "credit": credit}], {"Prefer": "return=minimal"})
        ok += 1
    except urllib.error.HTTPError as e:
        fails.append(f"{dst[-40:]}: {e.code} {e.read().decode()[:120]}")
    except Exception as e:  # noqa: BLE001
        fails.append(f"{dst[-40:]}: {e}")

print(f"\n완료 — 성공 {ok} · 실패 {len(fails)}")
for f in fails[:6]:
    print("  ✗", f)

after = rest("GET", "listing_images?select=listing_id&limit=5000", tok0)
still = len([l for l in listings if l["id"] not in {a["listing_id"] for a in after}])
print(f"남은 사진 없는 판매중 매물: {still}")
