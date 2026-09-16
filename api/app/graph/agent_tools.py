"""툴콜링 에이전트용 도구 4종 — 전부 결정론 코드다(도구 안에서 LLM 호출 금지, 4단계 부품 B).

search_listings·search_guides·market_price_stats·compare_listings 4종. 각 도구는
readonly_connection 관례(run_select/readonly_connection, db/readonly.py 4.1)로만 DB에 닿고,
파라미터는 항상 바인딩한다(사용자값을 f-string으로 SQL에 직접 박지 않는다 — sql_rag_node·
hybrid_rag_node와 동일 원칙, 함정 #1).

⚠️ search_listings의 SQL은 **코드가 조립**한다(LLM이 SQL 텍스트를 만들지 않는다) — 그래서
  sql_guard.validate_select_sql()을 거치지 않는다. 가드가 막는 대상은 "LLM이 생성한 SQL
  텍스트"이고, 이 도구는 파이썬이 고정된 절 목록에서 화이트리스트된 컬럼·연산자만 골라
  조립하므로 애초에 가드가 막으려는 위험(임의 테이블/컬럼/DDL 텍스트 생성)이 없다.
  ORDER BY 절도 마찬가지로 _SORT_WHITELIST에 없는 값은 거부한다(DW-848 해결 지점 —
  하이브리드 노드의 ORDER BY는 sql_guard의 벡터절 정규식이 고정한 모양만 허용하지만, 이
  도구는 LLM 생성 SQL이 아니므로 그 정규식과 무관하게 코드가 직접 화이트리스트를 검사한다).

search_guides는 multi_query.find_relevant_guides_fused(RRF 병합 + top-5 상대 게이트, FR49)를
  그대로 재사용하고, app.rerank_client.rerank가 있으면(사이드카 응답) 그 순서로 재정렬한다
  (병행 구현 중인 4단계 부품 A — 모듈이 없거나 임포트가 실패해도 None 취급하고 원래 순서를
  유지한다, 절대 실패시키지 않는다).

market_price_stats는 app.market_price.diagnose를 readonly_connection 트랜잭션 안에서 그대로
  호출한다(routers/market_price.py의 기존 관례와 동일 — 별도 진단 로직을 새로 만들지 않는다).

각 도구는 langchain @tool(response_format="content_and_artifact")로 감싸 (LLM에 보일 텍스트
요약, 에이전트 루프가 쓸 구조화 데이터) 쌍을 반환한다 — 에이전트 루프(agent.py)가 artifact로
selected_listing_ids 검증·market_diagnosis 노출에 쓸 매물 카드·진단 dict를 얻는다.
"""

import logging
import re
from typing import Literal

from langchain_core.tools import tool

from app.db.readonly import readonly_connection, run_select
from app.embeddings import embed_query
from app.graph.doc_rag_node import _vec_literal
from app.graph.listing_cards import SELECT_COLUMNS, attach_cover_images, rows_to_cards
from app.graph.multi_query import find_relevant_guides_fused
from app.market_price import diagnose
from app.schemas.ai import ListingCard

logger = logging.getLogger(__name__)

try:  # 4단계 부품 A(리랭커 사이드카)가 아직 없는 환경에서도 이 파일은 정상 동작해야 한다.
    from app.rerank_client import rerank
except ImportError:  # pragma: no cover — 방어적 폴백, 현재 레포엔 파일이 이미 존재한다.
    rerank = None

# search_listings 기본/상한 — 과다조회(20건) 후 에이전트가 가이드 지식으로 5건 내외 되추린다
# (DW-849). sql_rag_node의 DEFAULT_LIMIT(5)와는 다른 상수다 — 이 도구는 "최종 추천 개수"가
# 아니라 "에이전트가 되추릴 재료 개수"를 돌려준다.
_DEFAULT_SEARCH_LIMIT = 20
_MAX_SEARCH_LIMIT = 20

# 화이트리스트 ORDER BY — LLM 생성 SQL이 아니므로 sql_guard의 벡터절 정규식과 무관하게
# 이 도구 코드가 직접 검사한다(DW-848). similarity는 별도 분기(임베딩 벡터순)로 처리한다.
_SORT_WHITELIST: dict[str, str] = {
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "year_desc": "year DESC",
    "mileage_asc": "mileage ASC",
}

# listings.manufacturer/body_type CHECK 제약(supabase/migrations/0002_listings.sql)과 동일한
# 화이트리스트 — LLM이 model_keyword 칸에 제조사·차종을 섞어 넣는 실측 오류(예:
# model_keyword="현대 SUV" → model ILIKE '%현대 SUV%' = 0건, 정답은 manufacturer='현대' AND
# body_type='SUV')를 코드가 토큰 단위로 되돌리는 데 쓴다. '기타'는 진짜 필터 의도가 없는
# 캐치올 값이라 제외한다(사용자가 "기타"라고 말했다고 그걸 필터로 걸 이유가 없다).
_MANUFACTURER_WHITELIST = {
    "현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티",
    "BMW", "벤츠", "아우디", "폭스바겐", "토요타", "혼다", "렉서스", "테슬라",
}
_BODY_TYPE_WHITELIST = {
    "경차", "소형차", "준중형차", "중형차", "대형차", "스포츠카",
    "SUV", "RV", "경승합차", "승합차", "화물차",
}

# body_type 별칭·크기군 매핑(DW-872 — 실측: '세단'을 그대로 넘기면 ValueError로 되묻기에
# 도피하거나(C06·C48) 중형차 하나로만 좁혀 대형차 세단을 빠뜨림(C18)). DB CHECK 어휘엔
# "세단"이 없고 크기 축(준중형차/중형차/대형차)만 있어, 사용자가 흔히 쓰는 상위 개념 단어를
# 코드가 그 크기 값 목록으로 펼친다. SUV는 크기 축 자체가 어휘에 없어(소형/중형/대형 구분
# 없이 SUV 하나) 소형·중형·대형 SUV 요청이 전부 같은 값 하나로 묶인다 — applied_desc에 그
# 사실을 명시해 사용자 요청을 조용히 축소하지 않는다(_resolve_body_type 참조). 키는 공백
# 정규화(연속 공백→1칸) + 소문자 비교로 찾는다(예: "SUV"·"suv" 동일 취급).
_BODY_TYPE_ALIAS_MAP: dict[str, list[str]] = {
    "세단": ["준중형차", "중형차", "대형차"],
    "준중형": ["준중형차"],
    "준중형 세단": ["준중형차"],
    "중형": ["중형차"],
    "중형 세단": ["중형차"],
    "대형": ["대형차"],
    "대형 세단": ["대형차"],
    "소형": ["소형차"],
    "경형": ["경차"],
    "소형 suv": ["SUV"],
    "중형 suv": ["SUV"],
    "대형 suv": ["SUV"],
    "suv": ["SUV"],
    "승합": ["승합차"],
    "화물": ["화물차"],
}
# 크기+SUV 조합 키만 따로 모은다 — bare "suv"는 애초에 크기를 말하지 않았으므로 제외하고,
# 이 셋만 applied_desc에 "크기 구분 없음" 문구를 붙인다(_resolve_body_type 참조).
_SUV_SIZE_ALIAS_KEYS = {"소형 suv", "중형 suv", "대형 suv"}


def _resolve_body_type(value: str) -> tuple[list[str], str]:
    """body_type 인자 하나를 화이트리스트 값 목록 + applied_desc 문구로 바꾼다(DW-872).

    공백 정규화(연속 공백→1칸, 앞뒤 제거) + 영문 대소문자 정규화 후 별칭 맵을 찾는다.
    별칭이면 매핑된 값 목록을 돌려주고, 아니면 정규화한 원문 그대로 1개짜리 목록을
    돌려준다 — 모르는 값이어도 예외는 여기서 던지지 않는다(화이트리스트 검증은 호출부인
    search_listings가 한 곳에서 하고, 에러 문구도 거기 하나만 유지한다).
    """
    normalized = " ".join(value.split())
    key = normalized.lower()
    resolved = _BODY_TYPE_ALIAS_MAP.get(key)
    if resolved is None:
        return [normalized], f"차종={normalized}"
    if key in _SUV_SIZE_ALIAS_KEYS:
        return resolved, "차종=SUV(크기 구분 없음)"
    if resolved == [normalized]:
        return resolved, f"차종={normalized}"
    return resolved, f"차종={'·'.join(resolved)}({normalized})"

# listings.fuel CHECK 제약(0002)과 동일 — LLM이 '가솔린+전기' 같은 비실존 값을 지어내는 것 방지.
_FUEL_WHITELIST = {"가솔린", "디젤", "하이브리드", "전기", "LPG"}

# listings.region CHECK 제약(0002)과 동일한 17개 시·도 화이트리스트(DW-865/867) — 에이전트가
# 명시된 지역을 query_text에만 실어 다른 지역 매물을 "조건 충족"이라 안내하는 결함 방지.
# 별칭 맵은 사용자가 흔히 쓰는 행정구역 표기를 CHECK 허용값으로 되돌린다.
_REGION_WHITELIST = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
}
_REGION_ALIAS_MAP = {
    "경기도": "경기", "서울특별시": "서울", "서울시": "서울", "부산광역시": "부산",
    "강원도": "강원", "강원특별자치도": "강원", "전라북도": "전북", "전북특별자치도": "전북",
    "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "충청북도": "충북",
    "충청남도": "충남", "제주도": "제주", "제주특별자치도": "제주", "세종시": "세종",
}

# listings.color CHECK 제약(0002)과 동일한 9색 화이트리스트 — 지역과 같은 이유·같은 방식.
_COLOR_WHITELIST = {"흰색", "검정", "회색", "은색", "파랑", "빨강", "갈색", "녹색", "기타"}
_COLOR_ALIAS_MAP = {
    "검정색": "검정", "쥐색": "회색", "그레이": "회색", "파란색": "파랑",
    "빨간색": "빨강", "진주색": "흰색", "펄": "흰색",
}

# 제조사 별칭 — LLM이 구 상호·약칭·계열사명을 그대로 넣으면 DB 실제 값과 안 맞아 매물이
# 있어도 0건으로 샌다(DW-868 실측: "쌍용 렉스턴" → manufacturer='쌍용', DB는 'KG모빌리티'만 있음).
_MANUFACTURER_ALIAS_MAP = {
    "쌍용": "KG모빌리티", "쌍용자동차": "KG모빌리티",
    "르노": "르노코리아", "르노삼성": "르노코리아", "삼성": "르노코리아",
    "메르세데스": "벤츠", "메르세데스-벤츠": "벤츠",
    "현대자동차": "현대", "기아자동차": "기아",
    "지엠": "쉐보레", "쉐비": "쉐보레",
}

# 예산 인자 단위 방어(DW-868) — "1500이하"를 만원이 아니라 원으로 오독하면(price_max=1500)
# 실제 매물가(수백만~수천만 원)와 자릿수가 100만 배 어긋나 조용히 0건이 된다. 이 상한
# 미만이면 만원 단위로 보고 원으로 되돌린다(실매물 최저가가 이보다 훨씬 높아 오탐 위험 없음).
_PRICE_WON_GUARD_THRESHOLD = 1_000_000

# 옵션 동의어 그룹 — sql_rag_node._DOMAIN_RULES의 프롬프트 지시(2026-08-29 사용자 승인,
# DB 실측 옵션 문자열 기준)를 기계용 데이터로 옮긴 사본. 실측 결함(2026-09-01): "스마트크루즈"로
# 요청하면 부분일치로는 "어댑티브크루즈" 매물(더 뉴 쏘렌토 UM 무사고 2건, DB 정답)과 영원히 못
# 만난다 — 글자가 달라서. 프롬프트 원문과의 일치는 tests/test_agent_tools.py가 잠근다(표류 방지).
_OPTION_SYNONYM_GROUPS: list[frozenset[str]] = [
    frozenset({"크루즈컨트롤", "어댑티브크루즈", "스마트크루즈"}),
    frozenset({"주차센서", "후방센서", "후방감지센서"}),
    frozenset({"헤드업디스플레이", "HUD", "증강현실HUD"}),
    frozenset({"선루프", "파노라마선루프"}),
    frozenset({"어라운드뷰", "서라운드뷰"}),
    frozenset({"가죽시트", "나파가죽", "나파가죽시트"}),
    frozenset({"급속충전지원", "초고속충전"}),
    frozenset({"하만카돈", "렉시콘사운드", "뱅앤올룹슨"}),
]
_SUNROOF_GROUP = frozenset({"선루프", "파노라마선루프"})


def _expand_option_synonyms(opt: str) -> list[str]:
    """요청 옵션 하나를 동의어 계열로 확장한다(공백 제거 후 양방향 부분일치로 그룹 탐지).

    프롬프트 원문의 예외도 그대로 옮긴다: "파노라마"를 명시한 요청은 선루프 그룹으로
    확장하지 않는다(일반 선루프만 있는 매물이 파노라마 요청에 걸리면 오검색).
    """
    norm = opt.replace(" ", "")
    expanded = {opt}
    for group in _OPTION_SYNONYM_GROUPS:
        if group == _SUNROOF_GROUP and "파노라마" in norm:
            continue
        for member in group:
            m = member.replace(" ", "")
            if m in norm or norm in m:
                expanded |= group
                break
    return sorted(expanded)


# compare_listings에 한 번에 넣을 수 있는 최대 매물 수(설계 확정값) — 초과분은 앞에서부터 자른다.
_COMPARE_MAX = 4

# search_guides가 LLM에 넘기는 섹션당 본문 글자수 상한(doc_rag_node류와 동일 사상 — 프롬프트 비대화 방지).
_GUIDE_CONTENT_CHAR_CAP = 1200

# search_guides가 관련 문서를 하나도 못 찾았을 때 돌려주는 고정 문구 — 모듈 상수로 빼서
# agent.py의 강제 호출 게이트(DW-873)가 "가이드 0건"을 문자열 비교로 판별할 때 재사용한다
# (find_relevant_guides_fused의 top-5 상대 게이트를 다시 구현하지 않고 이 도구의 실제 반환값을
# 그대로 신뢰하는 방식).
NO_GUIDES_FOUND_TEXT = "관련 가이드 문서를 찾지 못했습니다."

# 어휘 근거 게이트(DW-876) — 리랭커 점수가 로컬에 없고 벡터 거리로는 주제 밖 가이드(예:
# "명의이전 절차가 복잡한가요?"에 전기차 보조금 가이드)를 못 가른다. 정교한 형태소 분석
# 대신 흔한 조사를 떼고 소수 기능어만 걸러내는 간단한 방식이다 — 오탐(정상 질의를 막음)을
# 피하려 보수적으로만 다듬는다(질의에서 뽑을 내용어가 없으면 아예 막지 않는다).
_GUIDE_GATE_STOPWORDS = {
    "뭐가", "달라요", "있을까요", "절차가", "복잡한가요", "있어", "알려줘", "궁금",
}
_GUIDE_GATE_TRAILING_JOSA = ("이랑", "이나", "은", "는", "이", "가", "을", "를", "의", "에", "로", "도", "만")
_GUIDE_GATE_HANGUL_WORD_RE = re.compile(r"[가-힣]{2,}")


def _extract_content_tokens(query_text: str) -> list[str]:
    """질의에서 한글 내용어 토큰을 뽑는다(2글자 이상 한글 연속 + 조사·소수 기능어 제거).

    형태소 분석기가 아니라 어절 끝의 흔한 조사를 떼고 고정된 소수 기능어 stopword만
    걸러내는 간단한 규칙이다(과설계 금지 — 어휘 근거 게이트 하나에만 쓴다).
    """
    tokens: list[str] = []
    for word in _GUIDE_GATE_HANGUL_WORD_RE.findall(query_text):
        if word in _GUIDE_GATE_STOPWORDS:
            continue
        for josa in _GUIDE_GATE_TRAILING_JOSA:
            if word.endswith(josa) and len(word) - len(josa) >= 2:
                word = word[: -len(josa)]
                break
        if word not in tokens:
            tokens.append(word)
    return tokens


def _guides_lexically_grounded(tokens: list[str], guides: list[tuple[str, str]]) -> bool:
    """토큰 중 하나라도 가이드 제목·본문에 부분 문자열로 있으면 통과(보수적 게이트).

    질의에서 내용어 토큰을 하나도 못 뽑았으면(전부 조사·기능어) 막지 않는다.
    """
    if not tokens:
        return True
    combined = "\n".join(f"{title}\n{content}" for title, content in guides)
    return any(tok in combined for tok in tokens)


def _normalize_model_keyword(
    model_keyword: str | None, manufacturer: str | None, body_type: str | None
) -> tuple[str | None, str | None, str | None]:
    """model_keyword를 공백 기준 토큰으로 쪼개, 제조사·차종 화이트리스트에 걸리는 토큰은
    각자 자리(manufacturer/body_type)로 옮기고 model 필터에서는 뺀다. 두 인자가 이미
    채워져 있으면 값을 덮지 않고 겹치는 토큰만 버린다(LLM이 같은 값을 두 군데에 중복
    입력한 경우도 안전). 남는 토큰이 없으면(전부 제조사·차종이었으면) model 필터는
    생략한다 — 그래야 "현대 SUV"가 model ILIKE '%현대 SUV%'(0건 오검색)로 새지 않는다.
    차종 자리는 화이트리스트뿐 아니라 body_type 별칭 단일 토큰(예: "세단")도 인식한다 —
    실제 값 목록으로 펼치는 건 search_listings의 _resolve_body_type이 한다(DW-872).
    """
    if not model_keyword:
        return manufacturer, body_type, None
    remaining: list[str] = []
    for tok in model_keyword.split():
        if tok in _MANUFACTURER_WHITELIST:
            manufacturer = manufacturer or tok
            continue
        if tok in _BODY_TYPE_WHITELIST or tok.lower() in _BODY_TYPE_ALIAS_MAP:
            body_type = body_type or tok
            continue
        remaining.append(tok)
    model_filter = " ".join(remaining) if remaining else None
    return manufacturer, body_type, model_filter


def _sanitize_ilike_fragment(text: str) -> str:
    """ILIKE 패턴 조립 재료에서 와일드카드 특수문자(%·_)를 제거한다. options_required 값은
    사용자/LLM이 자유 입력한 문자열이라, 그대로 패턴에 이어붙이면 %나 _가 의도치 않게
    와일드카드로 해석된다(SQL 인젝션은 아니다 — 파라미터 바인딩은 유지되지만, 패턴의
    '의미'가 사용자 입력에 흔들리는 문제).
    """
    return text.replace("%", "").replace("_", "")


def _format_listing_summary(listings: list[ListingCard], applied_desc: list[str] | None = None) -> str:
    """번호 매긴 간결한 매물 목록(id·모델·연식·주행·가격·연료·옵션 요약) — LLM에 보일 텍스트.

    applied_desc: 실제로 SQL에 걸린 필터를 사람이 읽을 문구로 나열한 목록(search_listings가
    조립). 0건일 때 이 목록을 그대로 보여줘 "조건에 맞는 매물이 없습니다"를 LLM이 다른 조건
    충족으로 오독하지 못하게 한다(DW-865 — 인자로 안 넘긴 조건은 검색이 보장하지 않는다)."""
    if not listings:
        if applied_desc:
            return f"조건에 맞는 매물이 없습니다 (적용 조건: {', '.join(applied_desc)})"
        return "조건에 맞는 매물이 없습니다."
    lines = []
    for i, c in enumerate(listings, start=1):
        # 옵션은 전체를 보여준다 — 앞 3개 절단 시절, 6번째 옵션(어댑티브크루즈)이 요약에서
        # 잘려 "속성은 도구 값과 일치해서만 서술" 규칙과 충돌 → LLM이 조건 충족 매물을
        # "옵션 확인 불가"로 스스로 걸러낸 실측 결함(2026-09-01, 트레이스 확정). 매물당
        # 옵션은 최대 십수 개 짧은 문자열이라 프롬프트 비대화 부담이 미미하다.
        opts = ", ".join(c.options or [])
        line = (
            f"{i}. id={c.id} {c.manufacturer} {c.model} {c.year}년식 "
            f"{c.mileage:,}km {c.price:,}원 연료={c.fuel or '미상'} "
            f"사고={c.accident_status or '미상'} 색상={c.color or '미상'} 지역={c.region or '미상'}"
        )
        if opts:
            line += f" 옵션={opts}"
        lines.append(line)
    return "\n".join(lines)


# search_listings 전용 SELECT — 공용 단일출처 SELECT_COLUMNS(listing_cards.py, 다른 세 RAG
# 경로와 공유)는 그대로 두고, 이 도구 결과 줄에만 필요한 color 1열을 맨 끝에 덧붙인다
# (DW-872). SELECT_COLUMNS를 직접 넓히면 sql_rag_node·hybrid_rag_node·doc_rag_node의
# rows_to_cards 12열 계약까지 함께 깨져 이 도구와 무관한 세 경로·테스트가 줄줄이 흔들린다.
_SEARCH_SELECT_COLUMNS = f"{SELECT_COLUMNS}, color"


def _rows_to_cards_with_color(rows: list[tuple]) -> list[ListingCard]:
    """_SEARCH_SELECT_COLUMNS(12열 + color 1열)로 뽑은 행을 카드로 바꾼다.

    앞 12열은 공용 rows_to_cards(단일출처, listing_cards.py)에 그대로 맡기고, 맨 끝의
    color만 이 함수가 덧붙인다 — rows_to_cards의 12열 고정 계약(_EXPECTED_COLUMN_COUNT)을
    건드리지 않는다. ListingCard는 frozen이 아니라 속성 대입이 그대로 된다(attach_cover_images와
    동일한 사후 부착 방식).
    """
    cards = rows_to_cards([r[:-1] for r in rows])
    for card, r in zip(cards, rows):
        color = r[-1]
        card.color = color if isinstance(color, str) else None
    return cards


def _run_similarity_select(sql: str, params: tuple) -> list[tuple]:
    """벡터 유사도(HNSW ANN) 정렬 SELECT 전용 실행 — run_select와 달리 쿼리 실행 전에
    hnsw.iterative_scan을 relaxed_order로 켠다(pgvector 0.8+, 로컬 실측 extversion 0.8.2).

    실측 결함(C60, 2026-09-14): search_listings(models=["쏘나타","K5"], accident_free_only=True)가
    로컬 DB(on_sale 7,239건)에서 0건을 냈다. 원인은 models 토큰 분리·ILIKE·status 조건이 아니라
    HNSW 인덱스 자체다 — 기본 설정(iterative_scan 꺼짐)에서는 벡터 정렬 인덱스 스캔이 유사도
    상위 후보만 ef_search개 훑고 나서 WHERE 필터를 사후 적용한다(사전 필터링이 아니다, 벡터
    검색은 doc_rag_node._vec_literal 근처 주석에도 같은 함정이 적혀 있다). 이 필터(모델 2종+
    무사고)는 매우 선택적이라(7,239건 중 6건, 0.08%) 그 6건이 기본 후보 범위 밖에 있어 LIMIT
    20을 못 채우는 정도가 아니라 0건이 된다 — 로컬 재현: 같은 WHERE에서 벡터 ORDER BY만
    떼면 6건, 얹으면 0건(SET 전), SET LOCAL hnsw.iterative_scan=relaxed_order를 얹으면 다시
    6건이 돌아온다. relaxed_order는 필터를 만족하는 행을 찾을 때까지(또는 인덱스를 다 훑을
    때까지) 후보를 반복 확장한다 — 근사 최근접이라는 성격은 그대로 유지된다(완전한 유사도순
    보장은 없음, relaxed라는 이름 그대로). 이 도구의 용도(과다조회 재료 최대 20건)엔 그걸로
    충분하다. SET LOCAL이라 트랜잭션 스코프 밖으로 새지 않는다(readonly.py의 SET LOCAL ROLE과
    동일 원칙) — run_select는 실행문 1개만 받으므로 이 함수는 readonly_connection을 직접 열어
    SET LOCAL과 본 쿼리를 같은 트랜잭션에서 순서대로 실행한다.
    """
    with readonly_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
            cur.execute(sql, params)
            return cur.fetchall()


@tool(response_format="content_and_artifact")
def search_listings(
    query_text: str,
    manufacturer: str | None = None,
    model_keyword: str | None = None,
    models: list[str] | None = None,
    body_type: str | None = None,
    fuel: str | None = None,
    region: str | None = None,
    color: str | None = None,
    price_max: int | None = None,
    price_min: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    mileage_max: int | None = None,
    seats_min: int | None = None,
    accident_free_only: bool | None = None,
    options_required: list[str] | None = None,
    single_owner_only: bool | None = None,
    non_smoker_only: bool | None = None,
    sort_by: Literal["price_asc", "price_desc", "year_desc", "mileage_asc", "similarity"] | None = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
) -> tuple[str, list[ListingCard]]:
    """조건에 맞는 매물을 검색한다. status='on_sale'만(FR11), 최대 20건까지 과다조회한다 —
    이 20건은 최종 추천 개수가 아니라 되추릴 재료다. 결과가 한 조건(예: 연료·차종)에 쏠려
    보이면 search_guides로 관련 가이드를 읽고 5건 내외로 다양성 있게 골라 최종 답하라.

    query_text는 매물 성격을 요약한 자연어(정렬 기준이 similarity일 때 벡터 검색에 쓰인다).
    sort_by 생략 시 similarity(벡터 유사도순)가 기본이다. limit은 20을 넘길 수 없다(자동 보정).

    model_keyword는 **모델명 전용**이다(예: "쏘렌토","아반떼") — 제조사·차종을 여기 넣지
    말고 반드시 전용 인자(manufacturer/body_type)를 써라. 섞여 들어와도 코드가 토큰 단위로
    걸러내긴 하지만, 전용 인자를 쓰는 편이 더 정확하다.
    여러 모델 중 하나를 찾는 요청("K3 아니면 아반떼")은 model_keyword 대신 models에
    ["K3","아반떼"]처럼 목록으로 넘겨라 — 목록 안 어느 모델과든 일치하면 걸린다(OR
    의미). model_keyword와 함께 써도 되고, 그러면 둘 다 합쳐 OR로 묶인다.
    body_type은 DB의 세부 차종값(예: "준중형차","중형차","대형차","SUV")뿐 아니라
    "세단"·"준중형"·"소형 SUV"처럼 사용자가 흔히 쓰는 말로 줘도 된다 — 코드가 알아서
    실제 차급 값(들)으로 바꾼다(예: "세단"→준중형차/중형차/대형차 전부). 크기+SUV
    조합("소형 SUV" 등)은 DB에 크기 구분이 없어 모두 "SUV" 하나로 처리된다.
    "7인승 이상"처럼 좌석 수 하한이 있으면 seats_min에 그 숫자를 넣어라(예: seats_min=7).
    options_required는 사용자가 요구한 옵션 문자열 목록(예: ["스마트키","통풍시트"]) —
    나열한 옵션을 **전부** 갖춘 매물만 걸러진다(하나라도 빠지면 제외, AND 의미). 옵션명은
    대략적으로 적어도 된다(공백·부분일치·동의어 계열을 허용해 정규화 비교한다 — 예:
    "어댑티브 크루즈 컨트롤"도 DB의 "어댑티브크루즈"와 매칭된다).
    single_owner_only=True면 1인소유(is_single_owner) 매물만, non_smoker_only=True면
    비흡연(is_non_smoker) 매물만 걸러진다 — 사용자가 "1인소유"·"비흡연"을 요구하면 이
    전용 인자를 써라(options_required에 문자열로 넣지 마라).
    region은 시·도 17개 중 하나만 인식한다(예: "서울","경기") — "경기도"·"서울특별시" 같은
    흔한 별칭은 코드가 자동으로 정규화하고, 그래도 모르는 값이면 필터를 걸지 않고 안내
    문구를 텍스트에 덧붙인다(지어낸 지역으로 조용히 0건이 되는 것 방지, DW-865/867).
    color는 9개 고정 색상 중 하나만 인식한다(예: "흰색","검정") — "검정색"·"그레이" 같은
    별칭도 같은 방식으로 정규화된다.
    """
    limit = min(max(int(limit or _DEFAULT_SEARCH_LIMIT), 1), _MAX_SEARCH_LIMIT)

    manufacturer, body_type, model_filter = _normalize_model_keyword(
        model_keyword, manufacturer, body_type
    )
    # models(여러 모델 중 하나, OR) — model_keyword와 같은 토큰 분리를 각 항목에 적용한다
    # (DW-872, "K3 아니면 아반떼"). manufacturer/body_type은 이미 채워져 있으면 안 덮이므로
    # (_normalize_model_keyword 자체 방어) 반복 호출로 누적해도 안전하다.
    model_ilike_fragments: list[str] = [model_filter] if model_filter else []
    if models:
        for m in models:
            if not (m and m.strip()):
                continue
            manufacturer, body_type, mf = _normalize_model_keyword(m.strip(), manufacturer, body_type)
            if mf:
                model_ilike_fragments.append(mf)
    if manufacturer:
        manufacturer = _MANUFACTURER_ALIAS_MAP.get(manufacturer, manufacturer)

    # 지역·색상 별칭 정규화 — 모르는 값이면 필터에서 제외하고 그 사실을 tool 텍스트에 남겨
    # LLM이 "조건에 맞다"고 착각하지 않게 한다(DW-865/867).
    notes: list[str] = []
    if region:
        region = _REGION_ALIAS_MAP.get(region, region)
        if region not in _REGION_WHITELIST:
            notes.append(f"지역 '{region}'는 인식되지 않아 필터에서 제외")
            region = None
    if color:
        color = _COLOR_ALIAS_MAP.get(color, color)
        if color not in _COLOR_WHITELIST:
            notes.append(f"색상 '{color}'는 인식되지 않아 필터에서 제외")
            color = None

    # body_type 별칭·복수값 해석(DW-872) — '세단'류는 DB CHECK 어휘에 없는 상위개념이라
    # 코드가 준중형차/중형차/대형차 등 실제 값 목록으로 펼친다(_resolve_body_type). 펼친
    # 각 값은 그대로 기존 화이트리스트로 검증한다 — 모르는 값이면 조용히 0건이 되는 대신
    # 허용 목록을 담은 에러를 던져 모델이 다음 스텝에서 스스로 고치게 한다(회귀 실측 H26,
    # 도구 실패 → ToolMessage → 재시도 회복은 실측 검증된 경로).
    body_type_list: list[str] | None = None
    body_type_desc: str | None = None
    if body_type:
        body_type_list, body_type_desc = _resolve_body_type(body_type)
        for bt in body_type_list:
            if bt not in _BODY_TYPE_WHITELIST:
                raise ValueError(
                    f"body_type '{bt}'은(는) 존재하지 않는 값이다. "
                    f"허용값: {sorted(_BODY_TYPE_WHITELIST)}. "
                    "'세단'류는 크기 축(준중형차/중형차/대형차)으로 바꿔 지정하라."
                )
    if fuel and fuel not in _FUEL_WHITELIST:
        raise ValueError(
            f"fuel '{fuel}'은(는) 존재하지 않는 값이다. 허용값: {sorted(_FUEL_WHITELIST)}."
        )

    # 예산 단위 방어(DW-868) — "1500이하"처럼 만원 단위 숫자가 원 단위 인자에 그대로 들어오면
    # 원 단위 매물가와 자릿수가 어긋나 조용히 0건이 된다. 경고 로그만 남기고 서버가 직접 고친다
    # (클라이언트/LLM이 보낸 값은 참고지 신뢰가 아니다 — CLAUDE.md B9).
    if price_max is not None and price_max < _PRICE_WON_GUARD_THRESHOLD:
        logger.warning("search_listings price_max=%s를 만원 단위로 보고 원 단위로 변환(×10,000)", price_max)
        price_max = price_max * 10_000
    if price_min is not None and price_min < _PRICE_WON_GUARD_THRESHOLD:
        logger.warning("search_listings price_min=%s를 만원 단위로 보고 원 단위로 변환(×10,000)", price_min)
        price_min = price_min * 10_000

    clauses = ["status = 'on_sale'"]
    params: list = []
    # 0건일 때 "조건에 맞는 매물이 없습니다"에 실제 적용된 필터를 나열하기 위한 설명 목록
    # (DW-865) — SQL 절을 추가할 때마다 나란히 채운다(정본은 위 clauses/params, 이건 표시용).
    applied_desc: list[str] = []
    if manufacturer:
        clauses.append("manufacturer = %s")
        params.append(manufacturer)
        applied_desc.append(f"제조사={manufacturer}")
    if model_ilike_fragments:
        # 1개면 기존과 동일한 단일 절, 여러 개면 OR로 묶는다(DW-872, "K3 아니면 아반떼").
        if len(model_ilike_fragments) == 1:
            clauses.append("model ILIKE %s")
            params.append(f"%{model_ilike_fragments[0]}%")
        else:
            clauses.append("(" + " OR ".join(["model ILIKE %s"] * len(model_ilike_fragments)) + ")")
            params.extend(f"%{f}%" for f in model_ilike_fragments)
        applied_desc.append(f"모델={'|'.join(model_ilike_fragments)}")
    if body_type_list:
        # 1개면 기존과 동일한 단일 절, 여러 개면 ANY로 묶는다(DW-872, '세단'→3개 차급).
        if len(body_type_list) == 1:
            clauses.append("body_type = %s")
            params.append(body_type_list[0])
        else:
            clauses.append("body_type = ANY(%s)")
            params.append(body_type_list)
        applied_desc.append(body_type_desc)
    if fuel:
        clauses.append("fuel = %s")
        params.append(fuel)
        applied_desc.append(f"연료={fuel}")
    if region:
        clauses.append("region = %s")
        params.append(region)
        applied_desc.append(f"지역={region}")
    if color:
        clauses.append("color = %s")
        params.append(color)
        applied_desc.append(f"색상={color}")
    if price_max is not None:
        clauses.append("price <= %s")
        params.append(price_max)
        applied_desc.append(f"가격≤{price_max:,}원")
    if price_min is not None:
        clauses.append("price >= %s")
        params.append(price_min)
        applied_desc.append(f"가격≥{price_min:,}원")
    if year_min is not None:
        clauses.append("year >= %s")
        params.append(year_min)
        applied_desc.append(f"연식≥{year_min}")
    if year_max is not None:
        clauses.append("year <= %s")
        params.append(year_max)
        applied_desc.append(f"연식≤{year_max}")
    if mileage_max is not None:
        clauses.append("mileage <= %s")
        params.append(mileage_max)
        applied_desc.append(f"주행≤{mileage_max:,}km")
    if seats_min is not None:
        clauses.append("seats >= %s")
        params.append(seats_min)
        applied_desc.append(f"좌석≥{seats_min}")
    if accident_free_only:
        clauses.append("accident_free = %s")
        params.append(True)
        applied_desc.append("무사고")
    if single_owner_only:
        clauses.append("is_single_owner IS TRUE")
        applied_desc.append("1인소유")
    if non_smoker_only:
        clauses.append("is_non_smoker IS TRUE")
        applied_desc.append("비흡연")
    if options_required:
        # 정확 일치(&&)는 LLM이 "어댑티브 크루즈 컨트롤"처럼 띄어쓰기 풀네임을 넣으면
        # DB 실존 문자열("어댑티브크루즈")과 어긋나 0건으로 샌다(실측 결함). 공백 제거 +
        # 양방향 부분일치로 바꿔 정규화 비교한다. 파라미터 바인딩은 그대로 유지(요청값은
        # %s 배열로만 전달, SQL 텍스트에 직접 삽입하지 않는다). 요청값의 %·_는 와일드카드
        # 오염 방지로 제거한다(_sanitize_ilike_fragment) — psycopg는 params가 있으면 SQL
        # 텍스트 전체에서 '%'를 자리표시자로 스캔하므로, 패턴 조립에 쓰는 리터럴 '%'도
        # '%%'로 이스케이프한다(hybrid_rag_node.py와 동일 이유).
        # 동의어 확장을 부분일치 앞에 건다 — "스마트크루즈" 요청이 "어댑티브크루즈" 매물과
        # 만나려면 글자 부분일치로는 불가능하고 계열 확장이 필요하다(실측 결함 2026-09-01).
        #
        # ⚠️ 옵션 간 의미는 AND다(실측 결함 2026-09-01): "통풍시트 그리고 스마트크루즈"를
        # 나열하면 둘 다 갖춘 매물만 나와야 한다. 요청 옵션마다 별도 EXISTS 절을 만들어
        # clauses에 각각 추가한다(전체가 " AND "로 결합되므로 옵션 개수만큼 EXISTS가
        # 쌓인다) — 그래서 동의어 확장도 옵션별로 독립된 %s::text[] 배열에 바인딩한다
        # (한 옵션의 동의어가 다른 옵션의 배열에 섞이면 안 된다, 옵션 단위 격리).
        applied_desc.append(f"옵션={','.join(o for o in options_required if o and o.strip())}")
        for opt in options_required:
            if not (opt and opt.strip()):
                continue
            expanded = _expand_option_synonyms(opt.strip())
            normalized_opt = [
                _sanitize_ilike_fragment(e).replace(" ", "") for e in expanded
            ]
            normalized_opt = [o for o in normalized_opt if o]
            if not normalized_opt:
                continue
            clauses.append(
                "EXISTS (SELECT 1 FROM unnest(options) o CROSS JOIN unnest(%s::text[]) req "
                "WHERE replace(o, ' ', '') ILIKE '%%' || req || '%%' "
                "OR req ILIKE '%%' || replace(o, ' ', '') || '%%')"
            )
            params.append(normalized_opt)
    where_sql = " AND ".join(clauses)

    if sort_by is None or sort_by == "similarity":
        qvec = _vec_literal(embed_query(query_text))
        # 정확 세대 우선(D, 2026-08-31 실측 P4 연장) — model_filter가 있으면 그 원문과 정확히
        # 같은 model인 매물을 유사도 정렬보다 먼저 세운다. "그랜저 IG"로 검색하면 model
        # ILIKE '%그랜저 IG%'가 "더 뉴 그랜저 IG"까지 부분일치로 끌어오는데, 그 안에서도
        # 정확히 "그랜저 IG"인 매물이 세대 혼동 없이 먼저 오는 게 사용자 기대와 맞는다.
        # sort_by가 명시된 값(price_asc 등)일 때는 그 정렬을 그대로 존중한다 — 사용자가 가격·
        # 연식순을 명시적으로 요구했는데 세대 일치가 끼어들면 그 의도를 덮어써 버리기
        # 때문이다(explicit sort가 우선한다는 기존 관례, 아래 else 분기는 그대로 둔다).
        order_prefix = ""
        order_params: list = []
        if model_filter:
            order_prefix = "(model = %s) DESC, "
            order_params = [model_filter]
        sql = (
            f"SELECT {_SEARCH_SELECT_COLUMNS} FROM listings WHERE {where_sql} "
            f"AND embedding IS NOT NULL ORDER BY {order_prefix}embedding <=> %s::vector LIMIT %s"
        )
        rows = _run_similarity_select(sql, (*params, *order_params, qvec, limit))
    else:
        if sort_by not in _SORT_WHITELIST:
            # 정상 경로에서는 Literal 타입이 LLM 호출 이전에 걸러주지만(langchain 스키마
            # 검증), 함수를 직접 부르는 호출자(테스트 포함)에도 같은 방어선을 둔다(코드 방어).
            raise ValueError(f"허용되지 않은 정렬 기준입니다: {sort_by!r}")
        sql = (
            f"SELECT {_SEARCH_SELECT_COLUMNS} FROM listings WHERE {where_sql} "
            f"ORDER BY {_SORT_WHITELIST[sort_by]} LIMIT %s"
        )
        rows = run_select(sql, (*params, limit))

    listings = attach_cover_images(_rows_to_cards_with_color(rows))
    summary = _format_listing_summary(listings, applied_desc)
    if notes:
        # 인식 못 한 지역·색상 안내를 요약 앞에 붙인다 — LLM이 "조건 충족"이라 오독하지 못하게.
        summary = "\n".join(notes) + "\n" + summary
    return summary, listings


@tool
def search_guides(query_text: str) -> str:
    """중고차 구매 가이드 문서를 의미 검색한다(용도·차급·연비 등 결정에 참고). 검색 결과가
    한 조건에 쏠릴 때(예: 하이브리드만 5건) 이 도구로 관련 섹션을 읽고 다양한 차급·용도를
    조합해 최종 추천을 5건 내외로 되추리는 데 쓴다(예: 하이브리드 소형 4 + 대형 3 + 준중형
    1 → 소형+준중형으로 5건). 근거 없는 시세·통계를 지어내지 말고, 이 도구가 준 문서
    내용만 인용하라.
    """
    qvec_literal = _vec_literal(embed_query(query_text))
    guides = find_relevant_guides_fused(query_text, qvec_literal)
    if not guides:
        return NO_GUIDES_FOUND_TEXT

    tokens = _extract_content_tokens(query_text)
    if not _guides_lexically_grounded(tokens, guides):
        logger.info("DW-876 어휘 근거 게이트 발동 — 질의=%r 내용어 토큰=%r", query_text, tokens)
        return NO_GUIDES_FOUND_TEXT

    if rerank is not None:
        try:
            order = rerank(query_text, [(title, content) for title, content in guides])
        except Exception as exc:  # 사이드카 실패는 원래 순서로 조용히 폴백(rerank_client와 동일 태도).
            logger.warning("search_guides 리랭크 호출 실패 — 원래 순서 유지: %r", exc)
            order = None
        if order:
            guides = [guides[i] for i in order if 0 <= i < len(guides)]

    blocks = [
        f"[{title}]\n{content[:_GUIDE_CONTENT_CHAR_CAP]}" for title, content in guides
    ]
    return "\n\n".join(blocks)


def _format_market_diagnosis(result: dict) -> str:
    listing = result["listing"]
    stats = result["stats"]
    header = (
        f"{listing['manufacturer']} {listing['model']} {listing['year']}년식 "
        f"{listing['price']:,}원"
    )
    if stats is None:
        return f"{header} — 비교 가능한 매물이 없어 시세 판정을 할 수 없습니다."
    percentile = result["percentile"]
    pct_txt = f"하위 {percentile * 100:.0f}%" if percentile is not None else "백분위 미상"
    lines = [
        f"{header} — 시세 판정: {result['verdict']}({pct_txt})",
        f"비교군 {result['criteria']['sample_count']}건({result['criteria']['desc']}) "
        f"가격범위 {stats['min']:,}~{stats['max']:,}원, 중앙값 {stats['median']:,.0f}원",
    ]
    tabpfn_price = result["tabpfn"]["price"]
    if tabpfn_price is not None:
        lines.append(f"모델 예측 적정가: {tabpfn_price:,}원")
    # 표본 부족 주의(DW-869) — market_price.diagnose()는 3건 미만이면 판정 자체를 보류하는데
    # (MIN_VERDICT_SAMPLE=3, market_price.py), LLM이 위 중앙값·범위 숫자만 보고 단정적으로
    # 전달하는 실측 결함이 있었다. 숫자는 그대로 두고(제거 아님) 주의 문구만 덧붙인다.
    sample_count = result["criteria"]["sample_count"]
    if sample_count < 3:
        lines.append(f"⚠ 비교군 {sample_count}건 — 표본이 적어 참고만 하세요(판정 보류)")
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def market_price_stats(listing_id: str) -> tuple[str, dict | None]:
    """매물 1건의 시세를 진단한다(비교군 통계 + 적정가 예측). 직전 검색 결과의 N번째
    매물 시세를 물으면, 그 결과 목록에서 N번째 매물의 id를 골라 이 도구를 호출하라.
    """
    with readonly_connection() as conn:
        result = diagnose(listing_id, conn)
    if result is None:
        return f"매물 id={listing_id}를 찾을 수 없습니다.", None
    return _format_market_diagnosis(result), result


def _format_compare_table(listings: list[ListingCard]) -> str:
    # 실측 결함(DW-891): 옵션을 앞 3개만 보여줘 4번째 이후(예: 어댑티브크루즈)의 차이가
    # 모델에게 안 보여, "동일한 기본 옵션"이라고 얕게 답했다. 2건 이상이면 공통 옵션을 한
    # 줄로 먼저 밝히고 각 매물 줄엔 그 매물만의 옵션(공통 외)만 적어 차이를 바로 드러낸다.
    if not listings:
        return "비교할 매물을 찾지 못했습니다."

    def base_line(c: ListingCard) -> str:
        return (
            f"- id={c.id} {c.manufacturer} {c.model} {c.year}년식 {c.mileage:,}km "
            f"{c.price:,}원 연료={c.fuel or '미상'} 사고={c.accident_status or '미상'}"
        )

    if len(listings) == 1:
        c = listings[0]
        line = base_line(c)
        opts = ", ".join(c.options or [])
        if opts:
            line += f" 옵션={opts}"
        return line

    common = [
        opt for opt in (listings[0].options or [])
        if all(opt in (c.options or []) for c in listings[1:])
    ]
    common_set = set(common)
    lines = [f"공통 옵션={', '.join(common) if common else '없음'}"]
    for c in listings:
        own_extra = [opt for opt in (c.options or []) if opt not in common_set]
        line = base_line(c) + f" 공통 외 옵션={', '.join(own_extra) if own_extra else '없음'}"
        lines.append(line)
    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def compare_listings(listing_ids: list[str]) -> tuple[str, list[ListingCard]]:
    """매물 여러 건(최대 4건)의 핵심 필드를 나란히 비교한다. 4건을 넘기면 앞의 4건만 쓴다."""
    ids = list(listing_ids)[:_COMPARE_MAX]
    if not ids:
        return "비교할 매물 id가 없습니다.", []
    rows = run_select(
        f"SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND id = ANY(%s::uuid[])",
        (ids,),
    )
    listings = attach_cover_images(rows_to_cards(rows))
    return _format_compare_table(listings), listings


# 에이전트 루프(agent.py)가 bind_tools/이름 조회에 쓰는 목록·딕셔너리.
AGENT_TOOLS = [search_listings, search_guides, market_price_stats, compare_listings]
TOOLS_BY_NAME = {t.name: t for t in AGENT_TOOLS}
