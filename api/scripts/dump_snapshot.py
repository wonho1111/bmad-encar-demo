"""운영 DB → 로컬 시드 스냅샷(supabase/seed-local/data/*.json) 재생성.

지금까지 이 스냅샷은 손으로 떴다(생성 스크립트가 리포에 없다). 13-10이 운영 데이터를 바꿨으므로
스냅샷도 다시 떠야 `supabase db reset` 후에도 새 매물이 남는다.

⚠️ 신뢰속성 3컬럼을 이번에 처음 스냅샷에 포함한다.
   기존 listings.json엔 accident_status·is_single_owner·is_non_smoker가 **없었고**, 대신
   03_trust_demo.sql이 로컬에서 4건에만 심어줬다. 이제 운영에 91건이 있으므로 그대로 실어야
   로컬이 운영과 같아진다. 02_data.sql은 `jsonb_populate_recordset(null::public.listings, ...)`로
   **컬럼명 기준 매핑**이라 JSON에 키를 더해도 SQL은 안 고쳐도 된다(확인함).

embedding은 싣지 않는다(기존과 동일) — 로컬에선 backfill_embeddings.py가 채운다.
"""

import json
import pathlib
import urllib.request

PROD = "https://psrnsasxpkpwqdukjdmt.supabase.co"
OUT = pathlib.Path("supabase/seed-local/data")

ANON = [l.split("=", 1)[1].strip() for l in open("web/.env.prod")
        if l.startswith("NEXT_PUBLIC_SUPABASE_ANON_KEY=")][0]

SEED_PW = [l.split("=", 1)[1].strip() for l in open("supabase/.env.seed")
           if l.startswith("SEED_PASSWORD=")][0]
# ⚠️ 판매자 한 명의 토큰으로는 **sold 매물을 다 못 본다** — RLS가 on_sale과 "내 매물"만 보여준다.
# 처음 이 스크립트를 그렇게 짰다가 기존 스냅샷의 sold 8건이 통째로 사라졌다(실측으로 잡음).
# 그래서 판매자 4명 전원의 토큰으로 각자 것을 모아 합친다.
ACCOUNTS = [("seller-seed@test.com", SEED_PW), ("seller-seed2@test.com", SEED_PW),
            ("seller-seed3@test.com", SEED_PW), ("seller@test.com", "seller123")]


def login(email, pw):
    r = urllib.request.Request(f"{PROD}/auth/v1/token?grant_type=password",
                               data=json.dumps({"email": email, "password": pw}).encode(),
                               method="POST")
    for k, v in (("apikey", ANON), ("Authorization", f"Bearer {ANON}"),
                 ("Content-Type", "application/json")):
        r.add_header(k, v)
    return json.loads(urllib.request.urlopen(r, timeout=30).read())["access_token"]


TOKENS = [login(e, p) for e, p in ACCOUNTS]
TOK = TOKENS[0]


def get(path, token=None):
    r = urllib.request.Request(f"{PROD}/rest/v1/{path}")
    for k, v in (("apikey", ANON), ("Authorization", f"Bearer {token or TOK}")):
        r.add_header(k, v)
    return json.loads(urllib.request.urlopen(r, timeout=120).read())


def get_all(path_tmpl, key="id"):
    """판매자 4명의 시야를 합집합한다(sold 매물은 소유자만 보이므로)."""
    merged = {}
    for t in TOKENS:
        for row in get(path_tmpl, t):
            merged[row[key]] = row
    return list(merged.values())


LISTING_COLS = ("id,seller_id,seller_name,status,manufacturer,model,body_type,year,price,"
                "mileage,color,fuel,transmission,displacement,seats,region,accident_free,"
                "accident_status,is_single_owner,is_non_smoker,options,description,"
                "created_at,updated_at")

listings = get_all(f"listings?select={LISTING_COLS}&order=created_at.asc&limit=2000")
listings.sort(key=lambda r: (r["created_at"], r["id"]))
images = get_all("listing_images?select=id,listing_id,storage_path,sort_order,is_cover,credit"
                 "&order=storage_path.asc&limit=5000")
images.sort(key=lambda r: r["storage_path"])

# storage_objects.json은 파일 경로 목록(seed-local.sh가 이걸 보고 내려받아 올린다).
storage = [{"name": i["storage_path"]} for i in images]
# 기존 파일에 있던 빈폴더 표시 등 비-이미지 항목은 보존한다.
old_storage = json.loads((OUT / "storage_objects.json").read_text())
known = {s["name"] for s in storage}
for s in old_storage:
    if s["name"] not in known and s["name"].endswith(".emptyFolderPlaceholder"):
        storage.append(s)

before = {p.name: len(json.loads((OUT / p.name).read_text()))
          for p in OUT.glob("*.json")}

(OUT / "listings.json").write_text(
    json.dumps(listings, ensure_ascii=False, separators=(", ", ": ")))
(OUT / "listing_images.json").write_text(
    json.dumps(images, ensure_ascii=False, separators=(", ", ": ")))
(OUT / "storage_objects.json").write_text(
    json.dumps(storage, ensure_ascii=False, separators=(", ", ": ")))

print("스냅샷 갱신 (운영 기준)")
for name, n in (("listings.json", len(listings)), ("listing_images.json", len(images)),
                ("storage_objects.json", len(storage))):
    print(f"  {name:24} {before.get(name, 0):>4} → {n}")
trust = sum(1 for l in listings
            if l["accident_status"] or l["is_single_owner"] or l["is_non_smoker"])
print(f"  신뢰속성 보유 매물 {trust}건 (이번에 처음 스냅샷에 포함)")
