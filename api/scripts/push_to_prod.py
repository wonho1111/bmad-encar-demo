"""로컬에서 검증이 끝난 신규 매물 65건을 **운영 DB**에 반영한다.

왜 REST인가: 운영 DATABASE_URL(postgres 롤)이 없고, 이 프로젝트는 service_role 키 사용을 금지한다.
대신 마이그레이션 0020이 `authenticated`에게 embedding 포함 INSERT 권한을 주고, RLS
`listings_insert_own`이 `auth.uid() = seller_id`를 강제한다 → **판매자 본인 토큰으로 자기 매물만** 넣는다.

임베딩은 로컬에서 계산한 값을 그대로 가져다 쓴다(설명 텍스트가 동일하므로 결과도 동일).
Gemini를 다시 65번 부를 이유가 없다.

멱등: 운영에 같은 (seller_id, model, price, mileage) 조합이 이미 있으면 건너뛴다.
  → 중간에 끊겨도 다시 돌리면 남은 것만 넣는다. 새 id가 생기므로 로컬 id와는 다르다(정상).
"""

import json
import os
import sys
import urllib.error
import urllib.request

import psycopg

PROD = "https://psrnsasxpkpwqdukjdmt.supabase.co"
LOCAL_DB = "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
APPLY = "--apply" in sys.argv

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

COLS = ("seller_id status manufacturer model body_type year price mileage color fuel "
        "transmission displacement seats region accident_free options description "
        "embedding").split()


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
        return r.status, (json.loads(raw) if raw else None)


# ── 1) 로컬에서 신규 65건을 뽑는다(오늘 만든 것 = created_at 이 오늘) ──────────
with psycopg.connect(LOCAL_DB) as conn, conn.cursor() as cur:
    cur.execute(f"""
        select {', '.join(COLS)}
        from public.listings
        where created_at::date >= '2026-08-05'
        order by seller_id, model
    """)
    cols = [d.name for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

print(f"로컬 신규 매물 {len(rows)}건")
assert len(rows) == 65, f"65건이 아니라 {len(rows)}건 — 중단"

# ── 2) 운영에 이미 있는지 확인(멱등) ─────────────────────────────────────
tok0 = login(*ACCOUNTS["748caac4-5e45-403c-b8ee-1f5ccc16b813"])
_, existing = rest("GET", "listings?select=seller_id,model,price,mileage&limit=2000", tok0)
have = {(e["seller_id"], e["model"], e["price"], e["mileage"]) for e in existing}
todo = [r for r in rows
        if (str(r["seller_id"]), r["model"], r["price"], r["mileage"]) not in have]
print(f"운영에 이미 있는 것 제외 → 넣을 것 {len(todo)}건")

if not APPLY:
    print("(미적용 — 실제 반영은 --apply)")
    raise SystemExit(0)

# ── 3) 판매자별로 로그인해 자기 매물만 삽입 ──────────────────────────────
ok = 0
fails = []
for seller, (email, pw) in ACCOUNTS.items():
    mine = [r for r in todo if str(r["seller_id"]) == seller]
    if not mine:
        continue
    token = login(email, pw)
    for r in mine:
        payload = {k: (str(v) if k == "seller_id" else v) for k, v in r.items()}
        # pgvector 값은 psycopg가 문자열로 준다 — REST는 그대로 받는다.
        if payload.get("embedding") is not None:
            payload["embedding"] = str(payload["embedding"])
        try:
            st, _ = rest("POST", "listings", token, [payload],
                         {"Prefer": "return=minimal"})
            ok += 1
        except urllib.error.HTTPError as e:
            fails.append(f"{email} {r['model']}: {e.code} {e.read().decode()[:160]}")
        except Exception as e:  # noqa: BLE001
            fails.append(f"{email} {r['model']}: {e}")
    print(f"  {email}: 누적 성공 {ok}")

print(f"\n삽입 성공 {ok} · 실패 {len(fails)}")
for f in fails[:6]:
    print("  ✗", f)

_, after = rest("GET", "listings?status=eq.on_sale&select=id&limit=2000", tok0)
print(f"운영 판매중: {len(after)}건")
