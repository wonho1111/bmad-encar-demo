"""FR11 실DB 검증 — `doc_rag_node`의 매물 의미검색이 **진짜 Postgres에서** sold 매물을
거른다(DW-627, `test_fr11_cover_images_real_db.py`와 같은 패턴).

왜 이 파일이 따로 있나 (13-8 3차 리뷰가 실증):
  `doc_rag_node`의 매물 의미검색은 `sql_guard`를 거치지 않고(코드 자체가 고정 SQL을 쓰므로
  인젝션 위험이 없어 애초에 안 거친다), `listings`의 `ai_readonly` RLS 정책도 `using(true)`라
  (sold까지 행 단위로는 안 막힌다) — 즉 `doc_rag_node.py`의 `WHERE status = 'on_sale'` 한 줄이
  **유일한 FR11 강제 지점**이다. 그런데 이걸 지키던 검사(`tests/test_doc_rag_node.py`)는
  생성된 SQL 문자열에 그 글자가 들어 있는지만 본다 — 조건을 `(status = 'on_sale' OR true)`로
  **무력화해도** 문자열엔 여전히 그 글자가 남아 있어 그 테스트는 계속 초록이다(3차 리뷰 실측:
  이 뮤테이션을 넣고 13.8 CM-B 커맨드 전량을 그대로 돌리니 스펙에 기록된 수치와 완전히
  동일했다). 대조군인 `hybrid_rag_node`는 조립 SQL 전문을 단언해 같은 뮤테이션에 실제로
  red가 된다 — `doc_rag_node`만 이 층이 비어 있었다.

무엇을 증명하나: api가 실제로 부르는 `doc_rag_node(query, qvec=...)`를 그대로 호출한다.
  `WHERE status = 'on_sale' AND embedding IS NOT NULL ORDER BY embedding <=> %s::vector`가
  실제 Postgres에서 sold 행을 거르는지 확인한다(문자열 검사가 아니라 실행 결과로).
무엇을 못 보나: 운영 DB의 데이터가 마이그레이션과 어긋난 경우(스키마 드리프트) —
  그건 migration-gate.yml 소관(test_fr11_cover_images_real_db.py와 동일한 경계).

⚠️ 이 파일은 `conftest.py`의 **`_create_user`만** 재사용하고 `_insert_listing`은 로컬로
  다시 정의한다(코드리뷰 정정) — 두 가지 이유가 있다.
  1) conftest의 `_insert_listing(cur, listing_id, seller_id)`는 status·embedding 인자를
     받지 않는다(`status='on_sale'` 고정). 이 테스트는 sold 1건 + on_sale 1건 + 임베딩이
     반드시 필요해 시그니처가 안 맞는다 — `test_seller_summary_real_db.py`가 이미 같은
     이유로 로컬 `_insert_listing(cur, listing_id, seller_id, status)`를 쓰는 선례를 따른다.
  2) conftest 표준 패턴(트랜잭션 하나에서 seed→yield→`conn.rollback()`)은 **같은 connection/
     session** 안에서만 유효하다(`test_seller_summary_real_db.py`의 `set local role anon`처럼).
     이 테스트는 `doc_rag_node()`가 내부적으로 `app/db/readonly.py`의 **별도 커넥션 풀**
     (`ai_readonly` 롤, 트랜잭션 풀러)로 조회한다 — Postgres 기본 격리수준(READ COMMITTED)에서
     다른 세션은 커밋 전 행을 볼 수 없으므로, 롤백 전제 패턴을 쓰면 시드 데이터가 애초에
     안 보여 테스트가 성립하지 않는다(`test_fr11_cover_images_real_db.py`가 롤백이 아니라
     커밋 후 명시적 DELETE를 쓰는 것과 같은 이유). 그래서 커밋 방식은 유지하되, `_create_user`로
     하드코딩 이메일 충돌을 없애고 teardown을 `try/finally`로 감싼다.
     ⚠️ (P10 코드리뷰 정정) `_create_user`는 `auth.users`에 INSERT한 뒤 가입 트리거 결과를
     `assert`로 확인한다 — 커넥션이 autocommit이라 그 INSERT는 assert 실패 여부와 무관하게
     이미 커밋돼 있는데, assert가 raise하면 `_create_user` 호출문 자체가 완료되지 않아
     `finally`의 `seller_id is not None` 가드는 그 행을 절대 못 본다(변수 대입이 일어나기
     전에 예외가 났으므로). 그래서 teardown은 `seller_id` 하나가 아니라 **먼저 생성해 둔
     이메일로 `auth.users`를 다시 조회**해 실제 id를 찾아 지운다 — `_create_user`가
     끝까지 성공했든 도중에 실패했든, 이메일로 찾은 행이 있으면 지운다.

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬에서 돌리려면 같은 변수를 직접 지정한다. 없으면 skip(거짓 통과 금지).
"""

import uuid

import psycopg
import pytest

from app.graph.doc_rag_node import doc_rag_node

from conftest import _DSN, _create_user, pytestmark  # noqa: F401

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region, embedding"
)

# 두 매물에 **동일한** 임베딩을 심는다 — 벡터 거리가 같으면(둘 다 질의 벡터와 거리 0) 정렬
# 우선순위로 sold가 우연히 빠진 게 아니라 `status` 필터가 실제로 걸렀음을 명확히 한다.
_EMBEDDING = "[" + ",".join(["0.01"] * 767 + ["1.0"]) + "]"


def _insert_listing(cur, listing_id, seller_id, status):
    """conftest의 `_insert_listing`은 status·embedding을 안 받아 이 파일은 로컬로 정의한다
    (파일 상단 docstring 참조, `test_seller_summary_real_db.py`와 동일 선례)."""
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, %s, '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울', %s::vector)",
        (listing_id, seller_id, status, _EMBEDDING),
    )


@pytest.fixture
def seeded(monkeypatch):
    """on_sale 1건 + sold 1건, 둘 다 같은 임베딩. 테스트 후 명시적으로 정리해 DB를 원상복구한다.

    커밋 기반 유지 이유는 파일 상단 docstring 참조(별도 커넥션 풀 가시성). `_create_user`로
    유저마다 고유 이메일(uuid4)을 써 하드코딩 이메일 충돌을 없애고, `try/finally`로 teardown을
    보장한다.
    ⚠️ (P10 코드리뷰 정정) teardown은 `seller_id` 변수가 아니라 **이메일로 다시 조회한 실제
    id**를 지운다 — `_create_user`가 가입 트리거 assert에서 실패하면(그 INSERT 자체는
    autocommit이라 이미 커밋됨) `seller_id = _create_user(...)` 대입이 끝내 일어나지 않아
    `seller_id`는 계속 None으로 남는다. `seller_id is not None` 가드만 썼다면 바로 이 경로에서
    고아 행이 남는다(실측 가능한 함정) — 그래서 이메일로 다시 찾아 지운다.
    """
    monkeypatch.setenv("DATABASE_URL", _DSN)
    from app.db import readonly

    # ⚠️ (P9 코드리뷰 정정) `readonly._pool = None` 생짜 대입은 되돌려지지 않는다 —
    #   monkeypatch가 settings.database_url은 원복해도 모듈 전역 `_pool`은 이 픽스처가
    #   테스트용 DSN으로 만들어 놓은 풀에 계속 묶인 채 남고, 그 커넥션들도 열려 있다
    #   (같은 세션의 뒤 테스트가 그 풀을 그대로 물려받는다). monkeypatch로 바꿔 자동
    #   원복시키고, teardown에서 이 픽스처가 실제로 연 풀을 닫는다 — 내가 만든 것만 치운다.
    monkeypatch.setattr(readonly, "_pool", None)
    monkeypatch.setattr(readonly.settings, "database_url", _DSN, raising=False)

    seller_id = None
    seller_email = f"ci-doc-rag-seller-{uuid.uuid4()}@example.com"
    on_sale_id, sold_id = uuid.uuid4(), uuid.uuid4()

    try:
        with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
            seller_id = _create_user(cur, seller_email, role="seller")
            _insert_listing(cur, on_sale_id, seller_id, "on_sale")
            _insert_listing(cur, sold_id, seller_id, "sold")

        yield on_sale_id, sold_id, seller_id
    finally:
        # 이 픽스처가 테스트용 DSN으로 열게 만든 풀을 닫는다(커넥션 반납). 그 다음 monkeypatch가
        # `_pool`을 원래 값으로 되돌린다 — 순서가 반대면 닫을 대상을 잃는다.
        readonly.close_pool()
        with psycopg.connect(_DSN, autocommit=True) as conn, conn.cursor() as cur:
            # seller_id가 None이어도(위 docstring의 실패 경로) auth.users INSERT는 이미
            # 커밋돼 있을 수 있다 — 이메일로 실제 id를 다시 찾아 그 값으로 지운다. 정상
            # 경로에서는 이 조회 결과가 seller_id와 같은 값이라 동작이 달라지지 않는다.
            cur.execute("select id from auth.users where email = %s", (seller_email,))
            row = cur.fetchone()
            actual_seller_id = row[0] if row is not None else seller_id
            if actual_seller_id is not None:
                cur.execute("delete from public.listings where seller_id = %s", (actual_seller_id,))
                cur.execute("delete from public.profiles where id = %s", (actual_seller_id,))
                cur.execute("delete from auth.users where id = %s", (actual_seller_id,))


def test_sold_listing_never_reaches_doc_rag_semantic_search_on_real_postgres(seeded):
    """**진짜 Postgres**에서 sold 매물이 `doc_rag_node`의 의미검색 결과에 없다(FR11).

    이 테스트가 잡는 회귀(가짜 DB·문자열 검사 층이 못 잡던 것):
      · `AND status = 'on_sale'` → `AND (status = 'on_sale' OR true)`(조건 무력화, 3차 리뷰 실증)
      · `status = 'on_sale'` 조건 삭제
      · 조인·컬럼 오타 등 — 문자열은 멀쩡한데 의미가 뒤집히는 변형
    """
    on_sale_id, sold_id, _seller_id = seeded

    qvec = [0.01] * 767 + [1.0]  # 심은 임베딩과 동일 — 필터가 없으면 둘 다 거리 0으로 후보가 된다
    out = doc_rag_node("싼타페 같은 SUV", qvec=qvec)

    ids = [str(c.id) for c in out["listings"]]
    assert str(on_sale_id) in ids, "판매중 매물이 의미검색 결과에서 빠졌다(과잉 차단)"
    assert str(sold_id) not in ids, "sold 매물이 doc_rag_node 의미검색 결과에 실렸다 (FR11 위반)"
