"""엔카 실매물 7,081건(listings_eval.csv) 로더 — E-4.

목적: 오프라인 평가용으로 수집·정규화된 엔카 매물(.logs/encar_eval/20260905/listings_eval.csv,
7,081행)을 제품 스키마(public.listings)에 실제로 얹는다. 시드 판매자 3명(seller-seed/2/3)에
라운드로빈으로 배분하고, 코퍼스① 임베딩(app.embeddings)까지 채운 뒤에야 검색·시세진단에서
"진짜 매물"로 보인다.

허용 의존성: 표준 라이브러리 + psycopg + app.embeddings 뿐이다(다른 스크립트를 import하지
않는다 — build_eval_db.py·push_to_prod.py·backfill_embeddings.py는 패턴 참고용으로만 읽었고,
같은 로직(compose_listing_text 등)은 이 파일 안에 그대로 다시 옮겨 적었다. 목적은 이 파일
하나만 봐도 무엇을 하는지 끝까지 알 수 있게 하는 것 — 다른 스크립트의 변경에 조용히 끌려
다니지 않는다).

컬럼 변환 규칙(고정, 임의로 늘리지 않는다):
  - manufacturer·model·body_type·year·price·mileage·color·fuel·transmission·displacement·
    seats·region·accident_free·accident_status: CSV 값을 타입만 맞춰 그대로 옮긴다.
  - options: CSV의 엔카 옵션 코드 배열([" 001", ...]) → encar_option_map.json으로 제품
    옵션명으로 바꾼다. null(매핑 없음)은 버리고, 중복은 제거하되 원래 순서는 보존한다.
  - description: 항상 NULL(엔카 원문 설명을 그대로 옮기지 않는다 — 사용 안 함, 명시적 결정).
  - generation: model 문자열 끝의 " 하이브리드"만 제거한 값(예: "그랜저 GN7 하이브리드" →
    "그랜저 GN7"). 0038 마이그레이션의 정규식 백필(레거시 시드용)과 달리 이 로더는 접미사
    제거만 한다 — 엔카 CSV의 model은 이미 정규화돼 있어 그 이상 걸러낼 잡음이 없다. 그 결과
    엔카 행은 generation이 항상 채워진다(NULL이 나오지 않는 게 정상 — 검증 SQL로 확인).
  - source: 'encar_eval_20260905' 고정(시드·사용자 매물은 계속 NULL, 0038 컬럼 코멘트 참조).
  - status: 'on_sale' 고정.
  - seller_id: 시드 판매자 3명(seller-seed/seed2/seed3, supabase/seed-local/01_accounts.sql
    id와 동일)에 CSV 행 순서로 라운드로빈. 로컬 DB에 이 3개 id가 profiles에 없으면 로컬
    판매자 중 아무 3명으로 대체하고 그 사실을 표준출력에 보고한다(조용히 다른 값을 쓰지 않는다).
  - encar_id: DB에 넣지 않는다(listings에 그런 열이 없다 — eval_meta는 build_eval_db.py의
    별도 encar_eval DB 전용이고 이 로더와는 무관하다). 임베딩 캐시 파일의 키로만 쓴다.

사용법(순서, 반드시 이 순서):
  1) python scripts/load_encar_listings.py --embed
       → Gemini 임베딩을 7,081건 계산해 .logs/encar_eval/20260905/embeddings/encar_embeddings.jsonl
         에 캐시(encar_id 키). 이미 캐시된 건 건너뛴다 — 몇 번을 다시 돌려도 안전.
  2) python scripts/load_encar_listings.py --local --demote-seed
       → 로컬 Supabase(127.0.0.1:55322, postgres DB)에 500건 배치로 INSERT.
         --demote-seed를 같이 주면 사진 없는 기존 무출처(source IS NULL) on_sale 시드 매물을
         'sold'로 내린다(백업 먼저 기록).
  3) python scripts/load_encar_listings.py --dry-run-prod
       → 운영에는 아무것도 쓰지 않고 GET만 해서 "실제로 --apply-prod를 돌리면 무슨 일이
         생길지"를 미리 보여준다.
  4) python scripts/load_encar_listings.py --apply-prod
       → 운영 반영. **이 스크립트를 작성한 세션은 이 플래그를 절대 실행하지 않는다** — 다음
         세션에서 사람이 명시 승인 후 직접 실행한다(CLAUDE.md B3 "운영 반영은 사용자 명시
         승인 시에만"). 코드는 --dry-run-prod와 대부분 재사용되므로 준비는 끝나 있다.

--demote-seed 원복: 저장된 `.logs/<env>_backup_<날짜>/demoted_ids.json`의 id 목록으로
  `UPDATE public.listings SET status = 'on_sale' WHERE id = ANY(%(ids)s::uuid[])`를 실행하면
  된다(로컬 psql/psycopg 어느 쪽이든 동일 SQL).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = API_ROOT.parent
sys.path.insert(0, str(API_ROOT))

import psycopg  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

from app.embeddings import embed_documents  # noqa: E402

# ── 경로·상수 ────────────────────────────────────────────────────────────────
EVAL_DIR = REPO_ROOT / ".logs" / "encar_eval" / "20260905"
DEFAULT_CSV = EVAL_DIR / "listings_eval.csv"
DEFAULT_OPTION_MAP = API_ROOT / "scripts" / "encar_option_map.json"
EMBED_CACHE = EVAL_DIR / "embeddings" / "encar_embeddings.jsonl"

SOURCE = "encar_eval_20260905"
LOCAL_DSN = "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
BATCH_SIZE = 100  # 임베딩
INSERT_BATCH = 500  # 로컬 INSERT
PROD_BATCH = 200  # 운영 REST POST

PROD_URL = "https://psrnsasxpkpwqdukjdmt.supabase.co"
# 라운드로빈 판매자(push_to_prod.py ACCOUNTS와 동일 id·계정, seller@test.com 제외 3명만).
SEED_ACCOUNTS = [
    ("12dfba00-2544-45f4-8ffe-bdeb32229b97", "seller-seed@test.com"),
    ("0f937a74-48ee-4e3a-9e78-4a3d85645727", "seller-seed2@test.com"),
    ("c19a85e7-6e23-432f-aa1c-efc57f1782af", "seller-seed3@test.com"),
]

# 판매완료 전환(demote)만 추가로 적용할 계정 — 엔카 행은 안 넣지만 사진 없는 시드 매물(19건 중 일부)을
# 갖고 있어 빠뜨리면 그 매물만 판매중으로 남는다. 비밀번호는 push_to_prod.py ACCOUNTS와 동일.
DEMOTE_EXTRA_ACCOUNTS = [
    ("748caac4-5e45-403c-b8ee-1f5ccc16b813", "seller@test.com", "seller123"),
]

IDEMPOTENCY_COLS = ("seller_id", "model", "year", "price", "mileage")

LISTING_INSERT_COLS = [
    "id", "seller_id", "status", "manufacturer", "model", "body_type", "year", "price",
    "mileage", "color", "fuel", "transmission", "displacement", "seats", "region",
    "accident_free", "accident_status", "options", "description", "generation", "source",
    "embedding",
]
LOCAL_INSERT_SQL = (
    f"INSERT INTO public.listings ({', '.join(LISTING_INSERT_COLS)}) "
    f"VALUES ({', '.join(['%s'] * len(LISTING_INSERT_COLS))})"
)


# ── 옵션·모델 변환 ────────────────────────────────────────────────────────────
def load_option_map(path: Path) -> dict[str, str | None]:
    return json.loads(path.read_text(encoding="utf-8"))


def map_options(codes: list[str], option_map: dict[str, str | None]) -> list[str]:
    """엔카 코드 배열 → 제품 옵션명. null 제거, 중복 제거(순서는 최초 등장 순 보존)."""
    seen: set[str] = set()
    out: list[str] = []
    for code in codes:
        name = option_map.get(code)
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def derive_generation(model: str) -> str:
    """model 끝의 ' 하이브리드'만 제거(그 외 잡음 제거는 하지 않는다 — CSV가 이미 정규화됨)."""
    suffix = " 하이브리드"
    return model[: -len(suffix)] if model.endswith(suffix) else model


def compose_listing_text(row: dict) -> str:
    """매물 임베딩용 텍스트 합성. backfill_embeddings.py의 동명 함수와 동일 로직(단일출처
    원칙은 지키고 싶지만 이 파일이 app.embeddings 외 스크립트 import를 금지하므로 옮겨 적었다
    — 텍스트 합성 방식이 서로 갈리면 엔카 매물 임베딩과 기존 매물 임베딩의 의미공간이
    미묘하게 달라지므로, 이 함수를 고칠 일이 생기면 backfill_embeddings.py 쪽도 함께 봐야 한다)."""
    opts = ", ".join(row.get("options") or [])
    parts = [
        f"{row['manufacturer']} {row['model']}",
        f"{row['body_type']} {row['year']}년식 {row['fuel']}",
    ]
    if opts:
        parts.append(f"옵션: {opts}")
    if row.get("description"):
        parts.append(row["description"])
    return ". ".join(parts).strip()


# ── CSV → 행 변환 ─────────────────────────────────────────────────────────────
def read_csv_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_seller_ids(conn) -> tuple[list[str], bool]:
    """시드 판매자 3명이 로컬 profiles에 있는지 확인. 없으면 로컬 판매자 아무 3명으로 대체.

    반환: (seller_id 3개, 대체했는지 여부).
    """
    wanted = [sid for sid, _ in SEED_ACCOUNTS]
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM public.profiles WHERE id = ANY(%s::uuid[])", (wanted,))
        found = {str(r[0]) for r in cur.fetchall()}
    if len(found) == 3:
        return wanted, False

    print(f"[경고] 시드 판매자 {wanted}가 로컬 profiles에 3명 다 없음(있는 것 {sorted(found)}) "
          "— 로컬 판매자 아무 3명으로 대체합니다.")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM public.profiles ORDER BY created_at LIMIT 3")
        fallback = [str(r[0]) for r in cur.fetchall()]
    if len(fallback) < 3:
        raise SystemExit(f"로컬 profiles에 판매자가 {len(fallback)}명뿐 — 3명 필요.")
    print(f"[대체] 사용할 판매자: {fallback}")
    return fallback, True


def transform_row(row: dict, index: int, option_map: dict, seller_ids: list[str]) -> dict:
    codes = json.loads(row["options"]) if row["options"] else []
    model = row["model"]
    return {
        "seller_id": seller_ids[index % len(seller_ids)],
        "status": "on_sale",
        "manufacturer": row["manufacturer"],
        "model": model,
        "body_type": row["body_type"],
        "year": int(row["year"]),
        "price": int(row["price"]),
        "mileage": int(row["mileage"]),
        "color": row["color"],
        "fuel": row["fuel"],
        "transmission": row["transmission"],
        "displacement": int(row["displacement"]),
        "seats": int(row["seats"]),
        "region": row["region"],
        "accident_free": row["accident_free"] == "True",
        "accident_status": row["accident_status"] or None,
        "options": map_options(codes, option_map),
        "description": None,
        "generation": derive_generation(model),
        "source": SOURCE,
        "encar_id": row["encar_id"],  # DB에는 안 넣음 — 캐시 키·멱등 확인용
    }


# ── 1) --embed: Gemini 임베딩 캐시 ───────────────────────────────────────────
def _read_cache(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    cache = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cache[rec["encar_id"]] = rec["vector"]
    return cache


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def embed_with_backoff(texts: list[str], backoffs=(20, 60, 180)) -> list[list[float]] | None:
    """embed_documents를 호출하되 429/RESOURCE_EXHAUSTED면 backoffs만큼 쉬고 재시도.

    3회(=len(backoffs)) 실패하면 None을 돌려줘 호출부가 중단·보고하게 한다.
    """
    attempt = 0
    while True:
        try:
            return embed_documents(texts)
        except Exception as exc:  # noqa: BLE001 — 원인 무관하게 재시도 판단은 메시지로만
            if not _is_rate_limit_error(exc) or attempt >= len(backoffs):
                if _is_rate_limit_error(exc):
                    print(f"[embed] 429/RESOURCE_EXHAUSTED {attempt + 1}회 실패 — 중단.")
                    return None
                raise
            wait = backoffs[attempt]
            print(f"[embed] 429/RESOURCE_EXHAUSTED — {wait}초 대기 후 재시도 "
                  f"({attempt + 1}/{len(backoffs)})")
            time.sleep(wait)
            attempt += 1


def run_embed(rows: list[dict]) -> None:
    EMBED_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = _read_cache(EMBED_CACHE)
    todo = [r for r in rows if r["encar_id"] not in cache]
    print(f"[embed] 전체 {len(rows)}건, 캐시된 것 {len(cache)}건, 남은 것 {len(todo)}건")
    if not todo:
        print("[embed] 더 계산할 것 없음.")
        return

    done = 0
    t0 = time.perf_counter()
    with EMBED_CACHE.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i : i + BATCH_SIZE]
            texts = [compose_listing_text(r) for r in batch]
            vecs = embed_with_backoff(texts)
            if vecs is None:
                print(f"[embed] 중단 — {done}/{len(todo)}건만 이번 실행에서 추가됨 "
                      f"(캐시에 누적, 재실행 시 이어서 계산).")
                return
            if len(vecs) != len(batch):
                raise RuntimeError(f"임베딩 개수 불일치: {len(vecs)} != {len(batch)}")
            for r, vec in zip(batch, vecs):
                f.write(json.dumps({"encar_id": r["encar_id"], "vector": vec}, ensure_ascii=False))
                f.write("\n")
            f.flush()
            done += len(batch)
            elapsed = time.perf_counter() - t0
            print(f"[embed] {done}/{len(todo)}건 완료 (누적 {elapsed:.0f}초, "
                  f"호출 {i // BATCH_SIZE + 1}회)")
    print(f"[embed] 전체 완료 — 이번 실행 {done}건, 총 소요 {time.perf_counter() - t0:.0f}초")


# ── 2) --local: 로컬 DB INSERT ───────────────────────────────────────────────
def existing_keys(conn, source: str) -> set[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT seller_id, model, year, price, mileage FROM public.listings "
            "WHERE source = %s",
            (source,),
        )
        return {(str(r[0]), r[1], r[2], r[3], r[4]) for r in cur.fetchall()}


def demote_seed_listings(conn, env: str) -> list[str]:
    """source IS NULL·on_sale·사진 없는 시드 매물을 sold로 내린다. 되돌릴 id를 먼저 백업."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT l.id FROM public.listings l
            WHERE l.source IS NULL AND l.status = 'on_sale'
              AND NOT EXISTS (SELECT 1 FROM public.listing_images li WHERE li.listing_id = l.id)
            """
        )
        ids = [str(r[0]) for r in cur.fetchall()]

    backup_dir = REPO_ROOT / f".logs/{env}_backup_{date.today():%Y%m%d}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / "demoted_ids.json"
    backup_path.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[demote-seed] 대상 {len(ids)}건 백업 → {backup_path}")

    if ids:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.listings SET status = 'sold' WHERE id = ANY(%s::uuid[])",
                (ids,),
            )
    print(f"[demote-seed] {len(ids)}건 sold 전환 완료. 원복: "
          f"UPDATE public.listings SET status = 'on_sale' WHERE id = ANY(%(ids)s::uuid[]) "
          f"-- ids는 {backup_path}")
    return ids


def run_local(csv_rows: list[dict], option_map: dict, demote_seed: bool) -> None:
    with psycopg.connect(LOCAL_DSN) as conn:
        register_vector(conn)
        seller_ids, _ = resolve_seller_ids(conn)
        rows = [transform_row(r, i, option_map, seller_ids) for i, r in enumerate(csv_rows)]

        cache = _read_cache(EMBED_CACHE)
        missing_embed = [r["encar_id"] for r in rows if r["encar_id"] not in cache]
        if missing_embed:
            raise SystemExit(
                f"[local] 임베딩 캐시에 없는 행 {len(missing_embed)}건 — 먼저 --embed를 "
                f"끝까지 돌리세요(예: {missing_embed[:3]})."
            )

        have = existing_keys(conn, SOURCE)
        todo = [
            r for r in rows
            if (r["seller_id"], r["model"], r["year"], r["price"], r["mileage"]) not in have
        ]
        skipped = len(rows) - len(todo)
        print(f"[local] 전체 {len(rows)}건, 이미 있어 건너뜀 {skipped}건, 넣을 것 {len(todo)}건")

        inserted = 0
        with conn.cursor() as cur:
            for i in range(0, len(todo), INSERT_BATCH):
                batch = todo[i : i + INSERT_BATCH]
                values = [
                    (
                        uuid.uuid4(), r["seller_id"], r["status"], r["manufacturer"], r["model"],
                        r["body_type"], r["year"], r["price"], r["mileage"], r["color"], r["fuel"],
                        r["transmission"], r["displacement"], r["seats"], r["region"],
                        r["accident_free"], r["accident_status"], r["options"], r["description"],
                        r["generation"], r["source"], cache[r["encar_id"]],
                    )
                    for r in batch
                ]
                cur.executemany(LOCAL_INSERT_SQL, values)
                inserted += len(batch)
                print(f"[local] {inserted}/{len(todo)}건 INSERT 완료")
        conn.commit()

        demoted_ids: list[str] = []
        if demote_seed:
            demoted_ids = demote_seed_listings(conn, "local")
            conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT status, count(*) FROM public.listings GROUP BY status")
            status_counts = dict(cur.fetchall())
            cur.execute(
                "SELECT source, count(*) FROM public.listings GROUP BY source ORDER BY source NULLS FIRST"
            )
            source_counts = cur.fetchall()
            cur.execute(
                "SELECT count(*) FROM public.listings WHERE source = %s AND generation IS NULL",
                (SOURCE,),
            )
            (gen_null,) = cur.fetchone()

        print(f"\n[검증] status별 건수: {status_counts}")
        print("[검증] source별 건수:")
        for src, cnt in source_counts:
            print(f"  {src!r}: {cnt}")
        print(f"[검증] source={SOURCE} 중 generation NULL 건수: {gen_null} (기대 0)")
        print(f"[검증] demote-seed로 sold 전환: {len(demoted_ids)}건")


# ── 3) 운영 REST 공통 헬퍼 ────────────────────────────────────────────────────
def _read_kv_line(path: Path, key: str) -> str:
    for line in path.open(encoding="utf-8"):
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{path}에서 {key}를 찾지 못함")


def prod_login(email: str, pw: str, anon: str) -> str:
    req = urllib.request.Request(
        f"{PROD_URL}/auth/v1/token?grant_type=password",
        data=json.dumps({"email": email, "password": pw}).encode(),
        method="POST",
    )
    for k, v in (("apikey", anon), ("Authorization", f"Bearer {anon}"),
                 ("Content-Type", "application/json")):
        req.add_header(k, v)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]


def prod_rest(method: str, path: str, token: str, anon: str, body=None, extra=None):
    req = urllib.request.Request(
        f"{PROD_URL}/rest/v1/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    for k, v in (("apikey", anon), ("Authorization", f"Bearer {token}"),
                 ("Content-Type", "application/json")):
        req.add_header(k, v)
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


def prod_get_all(path: str, token: str, anon: str, page: int = 1000) -> list[dict]:
    """GET을 offset 페이지로 끝까지 모아 돌려준다.

    Supabase REST는 요청당 최대 1,000행(max-rows)만 돌려주고 limit=10000 같은 큰 값은 조용히
    잘린다 — E-6 운영 적재 직후 멱등성 검사(dry-run)가 7,081건 중 4,341건을 "없음"으로 오판한
    실측 원인. 이 도우미 없이는 --apply-prod 재실행이 중복을 만든다.
    path에는 limit/offset을 넣지 않는다.
    """
    out: list[dict] = []
    offset = 0
    while True:
        sep = "&" if "?" in path else "?"
        _, rows = prod_rest("GET", f"{path}{sep}limit={page}&offset={offset}", token, anon)
        out.extend(rows)
        if len(rows) < page:
            return out
        offset += page


def load_prod_credentials() -> tuple[str, str]:
    """(anon key, 시드 비밀번호) — push_to_prod.py와 동일 출처 파일에서 읽는다."""
    anon = _read_kv_line(REPO_ROOT / "web" / ".env.prod", "NEXT_PUBLIC_SUPABASE_ANON_KEY")
    pw = _read_kv_line(REPO_ROOT / "supabase" / ".env.seed", "SEED_PASSWORD")
    return anon, pw


# ── 4) --dry-run-prod: GET만, 계획 수치 출력 ─────────────────────────────────
def run_dry_run_prod(csv_rows: list[dict], option_map: dict) -> None:
    anon, seed_pw = load_prod_credentials()
    seller_ids = [sid for sid, _ in SEED_ACCOUNTS]
    rows = [transform_row(r, i, option_map, seller_ids) for i, r in enumerate(csv_rows)]

    all_existing: set[tuple] = set()
    print("[dry-run-prod] 판매자별 운영 현황(GET만, 아무것도 쓰지 않음):")
    dry_accounts = [(sid, email, seed_pw) for sid, email in SEED_ACCOUNTS] + list(DEMOTE_EXTRA_ACCOUNTS)
    for seller_id, email, pw in dry_accounts:
        token = prod_login(email, pw, anon)
        mine = prod_get_all(
            "listings?select=id,model,year,price,mileage,status,source,listing_images(id)"
            f"&seller_id=eq.{seller_id}",
            token, anon,
        )
        on_sale = [m for m in mine if m["status"] == "on_sale"]
        # --demote-seed 대상과 같은 조건(무출처 시드만) — 엔카 행(source 있음)은 세지 않는다.
        no_photo = [m for m in on_sale if not m["listing_images"] and m.get("source") is None]
        print(f"  {email}: 전체 {len(mine)}건 · 판매중 {len(on_sale)}건 · "
              f"판매중+사진없음 {len(no_photo)}건")
        all_existing.update(
            (str(seller_id), m["model"], m["year"], m["price"], m["mileage"]) for m in mine
        )

    todo = [
        r for r in rows
        if (r["seller_id"], r["model"], r["year"], r["price"], r["mileage"]) not in all_existing
    ]
    print(f"\n[dry-run-prod] CSV {len(rows)}건 중 운영에 이미 있는 것 제외 → "
          f"예정 INSERT {len(todo)}건")


# ── 5) --apply-prod: 운영 반영(구현만, 이 세션은 절대 호출하지 않는다) ────────
def run_apply_prod(csv_rows: list[dict], option_map: dict, demote_seed: bool) -> None:
    """push_to_prod.py와 동일 패턴: 판매자 토큰으로 자기 매물만 REST POST, 200건 배치.

    ⚠️ CLAUDE.md B3(운영 반영은 사용자 명시 승인 시에만) + 이번 작업 지시("운영 DB에 쓰는
    실행 절대 금지")에 따라 이 함수는 코드 리뷰·다음 세션의 사람 실행을 위해서만 존재한다.
    이 로더를 만든 세션은 --apply-prod를 스스로 호출하지 않는다.
    """
    anon, seed_pw = load_prod_credentials()
    seller_ids = [sid for sid, _ in SEED_ACCOUNTS]
    rows = [transform_row(r, i, option_map, seller_ids) for i, r in enumerate(csv_rows)]

    cache = _read_cache(EMBED_CACHE)
    missing_embed = [r["encar_id"] for r in rows if r["encar_id"] not in cache]
    if missing_embed:
        raise SystemExit(f"[apply-prod] 임베딩 캐시 누락 {len(missing_embed)}건 — 먼저 --embed.")

    tokens = {sid: prod_login(email, seed_pw, anon) for sid, email in SEED_ACCOUNTS}

    existing: set[tuple] = set()
    for seller_id, email in SEED_ACCOUNTS:
        mine = prod_get_all(
            f"listings?select=model,year,price,mileage&seller_id=eq.{seller_id}",
            tokens[seller_id], anon,
        )
        existing.update((str(seller_id), m["model"], m["year"], m["price"], m["mileage"]) for m in mine)

    todo = [
        r for r in rows
        if (r["seller_id"], r["model"], r["year"], r["price"], r["mileage"]) not in existing
    ]
    print(f"[apply-prod] 운영에 없는 {len(todo)}건 POST 예정 (전체 {len(rows)}건 중)")

    ok, fails = 0, []
    by_seller: dict[str, list[dict]] = {}
    for r in todo:
        by_seller.setdefault(r["seller_id"], []).append(r)

    for seller_id, seller_rows in by_seller.items():
        token = tokens[seller_id]
        for i in range(0, len(seller_rows), PROD_BATCH):
            batch = seller_rows[i : i + PROD_BATCH]
            payload = [
                {
                    "seller_id": r["seller_id"], "status": r["status"],
                    "manufacturer": r["manufacturer"], "model": r["model"],
                    "body_type": r["body_type"], "year": r["year"], "price": r["price"],
                    "mileage": r["mileage"], "color": r["color"], "fuel": r["fuel"],
                    "transmission": r["transmission"], "displacement": r["displacement"],
                    "seats": r["seats"], "region": r["region"],
                    "accident_free": r["accident_free"], "accident_status": r["accident_status"],
                    "options": r["options"], "description": r["description"],
                    "generation": r["generation"], "source": r["source"],
                    "embedding": str(cache[r["encar_id"]]),
                }
                for r in batch
            ]
            try:
                prod_rest("POST", "listings", token, anon, payload, {"Prefer": "return=minimal"})
                ok += len(batch)
            except urllib.error.HTTPError as e:
                fails.append(f"{seller_id} batch@{i}: {e.code} {e.read().decode()[:200]}")
            print(f"[apply-prod] 누적 성공 {ok}/{len(todo)}")

    print(f"[apply-prod] 완료 — 성공 {ok} · 실패 {len(fails)}")
    for f in fails[:6]:
        print("  ✗", f)

    if demote_seed:
        # 운영 demote는 판매자 토큰 PATCH(REST는 UPDATE ... WHERE 조건이 없어 조건별 PATCH 호출).
        demote_targets = [(sid, email, tokens[sid]) for sid, email in SEED_ACCOUNTS] + [
            (sid, email, prod_login(email, pw, anon)) for sid, email, pw in DEMOTE_EXTRA_ACCOUNTS
        ]
        for seller_id, email, token in demote_targets:
            mine = prod_get_all(
                "listings?select=id,listing_images(id)&status=eq.on_sale"
                f"&seller_id=eq.{seller_id}&source=is.null",
                token, anon,
            )
            no_photo_ids = [m["id"] for m in mine if not m["listing_images"]]
            backup_dir = REPO_ROOT / f".logs/prod_backup_{date.today():%Y%m%d}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / f"demoted_ids_{seller_id}.json").write_text(
                json.dumps(no_photo_ids, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for lid in no_photo_ids:
                prod_rest("PATCH", f"listings?id=eq.{lid}", token, anon,
                          {"status": "sold"}, {"Prefer": "return=minimal"})
            print(f"[apply-prod demote-seed] {email}: {len(no_photo_ids)}건 sold 전환")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--option-map", default=str(DEFAULT_OPTION_MAP))
    ap.add_argument("--embed", action="store_true", help="Gemini 임베딩 계산·캐시(DB 접촉 없음)")
    ap.add_argument("--local", action="store_true", help="로컬 127.0.0.1:55322/postgres에 INSERT")
    ap.add_argument("--demote-seed", action="store_true",
                     help="--local 또는 --apply-prod와 함께: 사진 없는 무출처 on_sale 시드를 sold로")
    ap.add_argument("--apply-prod", action="store_true",
                     help="운영 REST POST — 구현만 되어 있음, 사람이 명시 승인 후에만 사용")
    ap.add_argument("--dry-run-prod", action="store_true", help="운영 GET만, 계획 수치 출력")
    args = ap.parse_args()

    if not any([args.embed, args.local, args.apply_prod, args.dry_run_prod]):
        ap.error("--embed/--local/--apply-prod/--dry-run-prod 중 하나 이상 지정하세요.")
    if args.demote_seed and not (args.local or args.apply_prod):
        ap.error("--demote-seed는 --local 또는 --apply-prod와 함께 써야 합니다.")

    option_map = load_option_map(Path(args.option_map))
    csv_rows = read_csv_rows(Path(args.csv))

    if args.embed:
        seller_ids = [sid for sid, _ in SEED_ACCOUNTS]
        rows = [transform_row(r, i, option_map, seller_ids) for i, r in enumerate(csv_rows)]
        run_embed(rows)

    if args.local:
        run_local(csv_rows, option_map, args.demote_seed)

    if args.dry_run_prod:
        run_dry_run_prod(csv_rows, option_map)

    if args.apply_prod:
        run_apply_prod(csv_rows, option_map, args.demote_seed)


if __name__ == "__main__":
    main()
