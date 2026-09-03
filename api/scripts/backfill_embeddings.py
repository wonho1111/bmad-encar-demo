"""임베딩 일괄 적재(backfill) — Story 4.2.

하는 일:
  1) listings 중 embedding이 NULL인 행 → 설명·옵션·핵심사양 텍스트(코퍼스①)를 768 임베딩으로 채움
  2) api/corpus/*.md 가이드 문서(코퍼스②) → '## ' 섹션 단위로 청킹해 guide_documents에 제목·본문·임베딩 적재

⚠️ 쓰기 경로: 이 스크립트는 데이터를 '쓴다'. 4.1의 읽기전용 헬퍼(app/db/readonly.py, SET ROLE ai_readonly)를
   쓰면 insufficient_privilege로 실패하므로, 여기서는 SET ROLE 없이 연결 롤(postgres)로 직접 쓴다.
   런타임 AI 경로는 계속 읽기전용으로 둔다(ai_readonly에 쓰기 권한 GRANT 금지 — NFR2).

⚠️ DATABASE_URL 비밀번호에 '?', '$' 같은 URL 특수문자가 있으면 URL 파서가 깨지므로 비밀번호를
   퍼센트 인코딩해 안전한 conninfo로 만든다.

멱등: listings는 `embedding IS NULL`만 처리(재실행 시 채워진 행 스킵). guide_documents는 delete 후
   재삽입(코퍼스 단일출처 = 파일). 둘 다 재실행 안전.

실행: api/ 디렉터리에서  `.venv/Scripts/python.exe scripts/backfill_embeddings.py`
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

# api/ 를 import 경로에 추가(직접 실행 시 app 패키지 인식)
API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

import psycopg  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

from app.config import require, settings  # noqa: E402
from app.embeddings import embed_documents  # noqa: E402


def safe_conninfo(url: str) -> str:
    """URL 비밀번호의 특수문자(?, $, @ 등)를 퍼센트 인코딩해 libpq가 올바로 파싱하게 한다.

    예상 형태는 `scheme://user:password@host...` (Supabase Session pooler). 비밀번호 없는 URL,
    `://`가 없는 keyword/value conninfo, userinfo가 없는 URL 등 예상과 다른 형태면 손대지 않고
    원본을 그대로 돌려준다(잘못된 변형으로 크래시·오인코딩하는 것보다 안전).
    """
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    userinfo, hostpart = rest.rsplit("@", 1)  # 비밀번호에 @ 없다고 가정(Supabase 기본)
    if ":" not in userinfo:  # 비밀번호 없는 URL → 인코딩할 대상 없음
        return url
    user, password = userinfo.split(":", 1)
    return f"{scheme}://{user}:{quote(password, safe='')}@{hostpart}"


def compose_listing_text(row: dict) -> str:
    """매물 임베딩용 텍스트 합성 — description이 없어도 핵심 사양으로 의미가 생기게 엮는다."""
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


def backfill_listings(conn) -> int:
    """embedding이 NULL인 매물에 768 임베딩 적재(멱등: NULL만 처리)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            select id, manufacturer, model, body_type, year, fuel, options, description
            from public.listings
            where embedding is null
            """
        )
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    if not rows:
        print("[listings] 채울 행 없음(이미 모두 임베딩됨).")
        return 0

    print(f"[listings] {len(rows)}건 임베딩 생성 중...")
    vecs = embed_documents([compose_listing_text(r) for r in rows])
    # 반환 개수가 입력과 다르면 zip이 조용히 잘려 일부 매물이 누락된다 → fail-loud로 막는다.
    if len(vecs) != len(rows):
        raise RuntimeError(f"임베딩 개수 불일치: {len(vecs)} != listings {len(rows)}건.")

    with conn.cursor() as cur:
        for row, vec in zip(rows, vecs):
            cur.execute(
                "update public.listings set embedding = %s where id = %s",
                (vec, row["id"]),
            )
    conn.commit()
    print(f"[listings] {len(rows)}건 적재 완료.")
    return len(rows)


def _split_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """'## ' 헤딩 경계로 본문을 나눠 (서두, [(섹션제목, 섹션본문), ...])로 반환한다(헤딩 줄 제외).

    서두 = 첫 '## ' 헤딩 이전 텍스트. '## '가 하나도 없으면 서두="", 섹션 리스트=[].
    """
    intro_buf: list[str] = []
    sections: list[tuple[str, str]] = []
    heading: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("## "):
            if heading is not None:
                sections.append((heading, "\n".join(buf).strip()))
            else:
                intro_buf = buf
            heading = line.lstrip()[3:].strip()
            buf = []
        else:
            buf.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(buf).strip()))
    else:
        intro_buf = buf
    intro = "\n".join(intro_buf).strip() if sections else ""
    return intro, sections


def load_corpus() -> list[tuple[str, str]]:
    """api/corpus/*.md 를 (title, content) 여러 건으로 청킹해 읽는다.

    파일 제목(첫 줄 '# 제목') 직후~첫 '## ' 사이의 서두 문단이 있으면 그것도 1건
    (title=문서제목)으로 담고, 이후 '## ' 섹션마다 1건(title="{문서제목} — {섹션제목}")으로
    쪼갠다. '## '가 하나도 없는 파일은 기존과 동일하게 문서 전체를 1건으로 담는다(하위호환).
    """
    corpus_dir = API_ROOT / "corpus"
    docs: list[tuple[str, str]] = []
    for f in sorted(corpus_dir.glob("*.md")):
        # utf-8-sig: 편집기가 파일 앞에 넣는 BOM(﻿)을 자동 제거 → 첫 줄 '# 제목' 인식이 깨지지 않게.
        text = f.read_text(encoding="utf-8-sig").strip()
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("#"):
            doc_title = lines[0].lstrip("#").strip()
            body = "\n".join(lines[1:]).strip()
        else:
            doc_title = f.stem
            body = text

        intro, sections = _split_sections(body)
        if not sections:  # '## ' 없는 파일 — 기존과 동일하게 문서 전체를 1건으로.
            if not body:
                print(f"[guide_documents] 본문 없는 문서 건너뜀: {f.name}")
                continue
            docs.append((doc_title, body))
            continue

        # 서두(첫 '## ' 이전) — 01번 문서의 body_type 전체 목록처럼 버리면 안 되는 내용이 있다.
        if intro:
            docs.append((doc_title, intro))

        for section_title, section_body in sections:
            if not section_body:  # 헤딩만 있고 본문이 공백뿐인 섹션은 의미 없는 행이 되므로 건너뛴다.
                print(f"[guide_documents] 본문 없는 섹션 건너뜀: {f.name} — {section_title}")
                continue
            docs.append((f"{doc_title} — {section_title}", section_body))
    return docs


def backfill_guides(conn) -> int:
    """가이드 문서를 '## ' 섹션 단위 청크로 임베딩해 guide_documents에 적재(멱등: 전량 delete 후 재삽입)."""
    docs = load_corpus()
    if not docs:
        print("[guide_documents] corpus/*.md 없음 — 건너뜀.")
        return 0

    print(f"[guide_documents] {len(docs)}개 청크 임베딩 생성 중...")
    # 제목+본문을 함께 임베딩해 의미 맥락을 강화. 저장 content는 본문만.
    vecs = embed_documents([f"{title}\n{content}" for title, content in docs])
    # ⚠️ 개수 검증은 반드시 DELETE 전에 — 불일치 시 테이블을 비우기 전에 멈춰 데이터 유실을 막는다.
    if len(vecs) != len(docs):
        raise RuntimeError(f"임베딩 개수 불일치: {len(vecs)} != guide {len(docs)}개.")

    with conn.cursor() as cur:
        cur.execute("delete from public.guide_documents")
        for (title, content), vec in zip(docs, vecs):
            cur.execute(
                "insert into public.guide_documents (title, content, embedding) values (%s, %s, %s)",
                (title, content, vec),
            )
    conn.commit()
    print(f"[guide_documents] {len(docs)}개 적재 완료.")
    return len(docs)


def main() -> None:
    db_url = require("DATABASE_URL", settings.database_url)
    require("GEMINI_API_KEY", settings.gemini_api_key)

    with psycopg.connect(safe_conninfo(db_url)) as conn:
        register_vector(conn)  # 파이썬 list ↔ pgvector 타입 자동 변환
        n_listings = backfill_listings(conn)
        n_guides = backfill_guides(conn)

    print(f"\n[done] backfill 완료 - listings {n_listings}건, guide_documents {n_guides}개.")


if __name__ == "__main__":
    main()
