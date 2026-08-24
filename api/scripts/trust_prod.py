"""신뢰속성을 **운영** 매물에 배분한다(REST, 판매자 본인 토큰).

로컬용 trust_distribute.py와 같은 규칙·같은 비율이다. 다른 점은 접근 경로뿐(psql → REST).
마이그 0020이 `authenticated`에게 accident_status·is_single_owner·is_non_smoker UPDATE 권한을
주고, RLS가 본인 매물만 허용하므로 판매자별로 나눠 PATCH한다.

결정론: id 오름차순 위치로 배정 — 재실행하면 같은 결과.
멱등: 먼저 전체를 비우고 계획대로 다시 채운다.
"""

import json
import sys
import urllib.error
import urllib.request

PROD = "https://psrnsasxpkpwqdukjdmt.supabase.co"
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
N_ALL3, N_TWO, N_ONE = 15, 40, 25


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


tokens = {s: login(e, p) for s, (e, p) in ACCOUNTS.items()}
any_tok = next(iter(tokens.values()))

rows = rest("GET", "listings?status=eq.on_sale&select=id,seller_id,accident_free"
                   "&order=id.asc&limit=2000", any_tok)
print(f"운영 판매중 {len(rows)}건")
clean = [r for r in rows if r["accident_free"]]
dirty = [r for r in rows if not r["accident_free"]]
print(f"  accident_free true {len(clean)} / false {len(dirty)}")

plan = {}
i = 0
for r in clean[i:i + N_ALL3]:
    plan[r["id"]] = ("무사고", True, True)
i += N_ALL3
combos2 = [("무사고", True, None), ("무사고", None, True), (None, True, True)]
for n, r in enumerate(clean[i:i + N_TWO]):
    plan[r["id"]] = combos2[n % 3]
i += N_TWO
combos1 = [("무사고", None, None), (None, True, None), (None, None, True)]
for n, r in enumerate(clean[i:i + N_ONE]):
    plan[r["id"]] = combos1[n % 3]
i += N_ONE
for n, r in enumerate(dirty[: max(1, len(dirty) // 2)]):
    plan[r["id"]] = ("사고" if n % 2 else "단순교환", None, None)

owner = {r["id"]: r["seller_id"] for r in rows}
print(f"배정 {len(plan)}건 / {len(rows)} = {len(plan)*100//len(rows)}%")
if not APPLY:
    print("(미적용 — 실제 반영은 --apply)")
    raise SystemExit(0)

# 1) 전체 초기화(멱등) — 판매자별로 자기 것만
for seller, tok in tokens.items():
    rest("PATCH", f"listings?seller_id=eq.{seller}&status=eq.on_sale", tok,
         {"accident_status": None, "is_single_owner": None, "is_non_smoker": None},
         {"Prefer": "return=minimal"})

# 2) 계획대로 채움
ok = 0
fails = []
for lid, (st, so, ns) in plan.items():
    tok = tokens.get(owner[lid])
    if not tok:
        fails.append(f"{lid}: 소유자 토큰 없음")
        continue
    try:
        rest("PATCH", f"listings?id=eq.{lid}", tok,
             {"accident_status": st, "is_single_owner": so, "is_non_smoker": ns},
             {"Prefer": "return=minimal"})
        ok += 1
    except urllib.error.HTTPError as e:
        fails.append(f"{lid}: {e.code} {e.read().decode()[:120]}")

print(f"적용 성공 {ok} · 실패 {len(fails)}")
for f in fails[:5]:
    print("  ✗", f)

after = rest("GET", "listings?status=eq.on_sale&select=accident_status,is_single_owner,"
                    "is_non_smoker&limit=2000", any_tok)
a3 = sum(1 for r in after if r["accident_status"] == "무사고" and r["is_single_owner"] and r["is_non_smoker"])
anyv = sum(1 for r in after if r["accident_status"] or r["is_single_owner"] or r["is_non_smoker"])
chip = sum(1 for r in after if r["accident_status"] in ("사고", "단순교환"))
print(f"\n✅ 운영 판매중 {len(after)}건 — 3개전부 {a3} · 하나라도 {anyv} ({anyv*100//len(after)}%) · 상태칩 {chip}")
