"""질의 맥락화 노드 — FR18 멀티턴 맥락.

흐름: (직전 대화 context + 현재 query) → "혼자서도 뜻이 통하는 독립 질의" 한 줄로 재작성.
  그 재작성 질의를 기존 그래프(라우터→A/B/C→answer)에 그대로 흘리면, 다운스트림 노드는
  맥락을 몰라도 평소처럼 처리한다(이미 완결된 질의를 받으니까). 4.6의 맥락 처리는 전부
  여기 "그래프 앞단" 한 곳에 격리한다 — 다운스트림 노드 시그니처 불변(회귀 0, 함정 #4).

서버 무상태(FR18·NFR4):
  맥락은 오직 함수 인자(context)로만 들어온다. 모듈 전역/파일/DB에 대화를 저장하지 않는다.
  재작성 후 context는 버려지므로, 같은 서버라도 다음 요청은 직전을 기억하지 못한다(함정 #1).

안전장치:
  · context가 비면(None·[]) LLM을 아예 부르지 않고 query를 그대로 반환한다
    (단일턴 비용·지연 0, 키 없이도 동작 — 함정 #2).
  · 재작성 결과가 비거나 호출이 실패하면 원 query로 안전 폴백(조용한 빈 결과 금지 — 함정 #3).
  · GEMINI_API_KEY 부재는 (context 있을 때만) require()로 fail-loud.
[Source: story 4.6 contextualize 설계; 4-3·4-5 _llm() 호출시점 키·fallback 패턴]
"""

import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.schemas.ai import MAX_QUERY_LENGTH

logger = logging.getLogger(__name__)

# 폴백으로 "흡수해도 되는" 예상 실패만 좁혀 잡는다(D1).
#   · ConnectionError/TimeoutError = 네트워크·전송 계열 일시 오류
#   · ValueError/KeyError/AttributeError 등 코드 버그는 여기에 없음 → 폴백에 묻히지 않고 전파됨
# langchain/google 클라이언트가 던지는 예외 타입이 버전마다 달라, 표준 transport 예외를
# 기본으로 두고 (있으면) google 트랜스포트 예외도 합친다. import 실패해도 표준 예외로는 동작.
_EXPECTED_LLM_ERRORS: tuple[type[Exception], ...] = (ConnectionError, TimeoutError, OSError)
try:  # google API 클라이언트의 전송 예외(설치돼 있으면)도 폴백 대상에 포함
    from google.api_core import exceptions as _gax_exc  # type: ignore

    _EXPECTED_LLM_ERRORS = _EXPECTED_LLM_ERRORS + (_gax_exc.GoogleAPIError,)
except Exception:  # 패키지 부재·구조 변경 시엔 표준 예외만으로 동작(과한 의존 금지)
    pass

# 재작성 전용 시스템 프롬프트 — 지시어만 치환하고 새 조건을 지어내지 않게 못 박는다(함정 #3).
# party-mode 2026-06-23(안건2): "주제 전환 시 옛 조건 완전 폐기" 리셋 규칙을 명문화한다.
#   이 한 줄이 "병합기"로만 동작하던 버그(주제 바뀐 질의에도 옛 조건이 따라붙음)의 1차 방어선이다.
_SYSTEM_PROMPT = """너는 중고차 검색 대화의 "질의 재작성기"다.
아래 [직전 대화]를 참고해, [현재 질의]를 그것만 읽어도 뜻이 통하는
독립적인 중고차 검색 질의 한 문장으로 다시 써라.

규칙:
- "그 중", "그거", "아까 그", "방금", "그럼" 같은 지시어를 직전 대화의 구체 내용으로 치환한다.
- 직전 대화에 없는 새 조건·차종·매물을 지어내지 않는다(있는 맥락만 흡수).
- **현재 질의가 새 차종·새 주제·새 용도로 바뀌었으면(좁히기가 아니라 새 검색이면),
  직전 대화의 매물 조건(가격·차종·색상 등)을 완전히 버리고 현재 질의만으로 재작성한다.**
  예) "2천만원 이하 중형세단" 대화 뒤 "초보운전자 첫차 추천" → 옛 가격·차종 조건을 끌고 오지 말 것.
  예) "아반떼 보여줘" 뒤 "쏘렌토는?" → "아반떼"를 버리고 "쏘렌토"만 남길 것.
- 현재 질의가 이미 독립적이면 거의 그대로 둔다.
- 출력은 재작성된 질의 "한 줄"만. 설명·따옴표·접두어 없이."""

# 토큰 절약 — context가 길어도 최근 N턴만 맥락으로 쓴다(스키마가 이미 12턴으로 제한하지만 추가 안전).
_MAX_CONTEXT_TURNS = 6


def _llm() -> ChatGoogleGenerativeAI:
    """재작성용 LLM. temperature=0으로 같은 입력에 같은 재작성이 나오게 한다(재현성·보수성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,  # gemini-3.1-flash-lite (env로 교체 가능)
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _extract_text(content) -> str:
    """LLM 응답 content에서 텍스트만 뽑는다.

    langchain-google-genai의 일부 모델은 content를 단순 str이 아니라
    [{'type':'text','text':...}, ...] 형태의 "콘텐츠 블록 리스트"로 돌려준다.
    두 형태를 모두 받아 평탄한 문자열로 만든다(라이브 검증에서 list 케이스 발견).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content or "")


def _serialize_context(context: list) -> str:
    """context(턴 목록)를 LLM 프롬프트용 텍스트로 직렬화. 최근 _MAX_CONTEXT_TURNS만 사용.

    턴은 Pydantic ConversationTurn(.role/.content) 또는 dict 둘 다 받아들인다(테스트 편의).
    """
    recent = context[-_MAX_CONTEXT_TURNS:]
    lines = []
    for turn in recent:
        role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else None)
        content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else None)
        if not content:
            continue
        # 프롬프트 주입 방어 — 턴 내용은 클라이언트가 보낸 '데이터'일 뿐 '지시'가 아니다.
        # 내용에 줄바꿈을 넣어 "[현재 질의]" 같은 가짜 섹션을 위조하지 못하도록 개행을 공백으로 눕힌다.
        flat = " ".join(str(content).split())
        label = "사용자" if role == "user" else "어시스턴트"
        lines.append(f"{label}: {flat}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# 결정적 주제전환 가드(party-mode 2026-06-23, 안건2 2차 안전망)
#
# 목적: 프롬프트(1차)가 비결정적이라 놓치는 "주제 전환" 케이스에서, LLM을 거치지 않고
#   코드로 먼저 판정해 맥락 오염(옛 SQL 조건이 새 질의에 따라붙어 WHERE를 망침)을 막는다.
#   (가) SQL 정확도 우선이라, 틀린 조건 계승은 결과를 0건/엉뚱하게 만드는 이진 실패라 결정성이 중요.
#
# ⚠️ 한계(투명): 카테고리형 차원(제조사·차종·연료·색상·지역 — DB CHECK 단일출처)의 "값 교체"와
#   "비-SQL 주제 점프"만 결정적으로 잡는다. 모델명(아반떼·쏘렌토 등)은 자유값이라 열거 불가 →
#   그 교체는 프롬프트(1차)에 맡긴다. 숫자 조건(가격·주행거리) 추가는 좁히기로 보고 리셋하지 않는다.
#
# 카테고리형 차원 어휘 — 0002_listings.sql CHECK 목록과 정렬(단일출처, 소문자 비교).
_CATEGORICAL_VOCAB: dict[str, tuple[str, ...]] = {
    "manufacturer": (
        "현대", "기아", "제네시스", "쉐보레", "르노코리아", "kg모빌리티", "bmw", "벤츠",
        "아우디", "폭스바겐", "토요타", "혼다", "렉서스", "테슬라",
    ),
    # body_type — "중형세단"은 '중형'으로, "SUV"는 'suv'로 잡힌다("세단"만 있으면 크기 불명이라 미검출).
    "body_type": (
        "경차", "소형차", "소형", "준중형차", "준중형", "중형차", "중형", "대형차", "대형",
        "스포츠카", "suv", "rv", "경승합차", "승합차", "승합", "화물차", "화물", "트럭",
    ),
    "fuel": ("가솔린", "디젤", "하이브리드", "전기차", "전기", "lpg"),
    "color": ("흰색", "검정", "회색", "은색", "파랑", "빨강", "갈색", "녹색"),
    "region": (
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
        "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    ),
}

# 후속·참조 표현 — 이게 보이면 "좁히기(refine)"로 보고 절대 리셋하지 않는다(보수적: 오인 리셋 방지).
_REFINE_MARKERS: tuple[str, ...] = (
    "그중", "그 중", "그거", "그것", "그 차", "그차", "아까", "방금", "그럼",
    "말고", "중에서", "다른", "비슷", "같은 거", "같은거", "이전", "위에", "더 싼", "더싼",
)

# 숫자형 조건 신호(가격·주행거리·연식) — 있으면 "조건 추가(좁히기)"로 보고 비-SQL 주제 점프로 안 친다.
_NUMERIC_CUE = re.compile(r"\d|천만원|만원|만\s*km|km|년식|연식|이하|이상|미만|초과")


def _categorical_dims(text: str) -> dict[str, set[str]]:
    """text에서 카테고리형 차원별로 등장한 값 토큰 집합을 뽑는다(소문자 부분문자열 매칭)."""
    low = text.lower()
    found: dict[str, set[str]] = {}
    for dim, vocab in _CATEGORICAL_VOCAB.items():
        hits = {v for v in vocab if v in low}
        if hits:
            found[dim] = hits
    return found


def _recent_user_text(context: list) -> str:
    """직전 대화의 최근 사용자 발화만 모아 한 문자열로(차원 추출용). 최근 _MAX_CONTEXT_TURNS만."""
    parts = []
    for turn in context[-_MAX_CONTEXT_TURNS:]:
        role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else None)
        content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else None)
        if role == "user" and content:
            parts.append(str(content))
    return " ".join(parts)


def _is_topic_shift(query: str, context: list) -> bool:
    """현재 질의가 직전 맥락과 "다른 새 검색"이면 True(→ 맥락 버리고 원 질의 사용).

    판정 순서(보수적):
      1) 참조·후속 표현이 있으면 좁히기 → False(리셋 안 함).
      2) 같은 카테고리 차원에서 값이 통째로 교체되면(예: 중형→SUV, 현대→기아) → True.
      3) 새 질의에 카테고리·숫자 조건 신호가 전혀 없고(=용도·인물 등 새 주제),
         직전이 SQL성 검색(조건 보유)이었다면 → True(예: "…중형세단" 뒤 "초보 첫차 추천").
      그 외에는 조건 추가(좁히기)로 보고 False.
    """
    low = query.lower()
    if any(m in low for m in _REFINE_MARKERS):
        return False  # 참조 표현 → 좁히기로 확정, 리셋하지 않는다.

    prev_text = _recent_user_text(context)
    prev_dims = _categorical_dims(prev_text)
    new_dims = _categorical_dims(low)

    # (2) 같은 차원 값 교체 — 새 질의가 그 차원에 직전과 겹치지 않는 값을 들고 옴.
    for dim, new_vals in new_dims.items():
        prev_vals = prev_dims.get(dim)
        if prev_vals and not (prev_vals & new_vals):
            return True

    # (3) 새 질의에 SQL 조건 신호가 전혀 없음(카테고리·숫자 모두 없음) = 비-SQL 주제로 점프.
    if not new_dims and not _NUMERIC_CUE.search(low):
        if prev_dims or _NUMERIC_CUE.search(prev_text):  # 직전이 SQL성 검색일 때만 오염 대상
            return True

    return False


def contextualize_query(query: str, context: list | None = None) -> str:
    """직전 대화 맥락을 반영해 query를 독립 질의로 재작성한다(FR18).

    context가 비면(None·[]) LLM을 부르지 않고 query를 그대로 반환한다(단일턴, 함정 #2).
    주제 전환이 결정적으로 감지되면 LLM을 부르지 않고 원 query를 그대로 쓴다(맥락 오염 방지, 안건2).
    재작성이 실패/공백이면 원 query로 폴백한다(조용한 빈 결과 금지, 함정 #3).
    맥락은 인자로만 받고 반환 후 버린다 — 서버·DB에 저장하지 않는다(무상태, 함정 #1).
    """
    # 단일턴 — 맥락이 없으면 LLM 호출 없이 원 질의 그대로(회귀 0·비용 0·키 불필요).
    if not context:
        return query

    serialized = _serialize_context(context)
    if not serialized:
        # 직렬화 결과가 비면(빈 content뿐) 맥락이 없는 것과 같다 → 원 질의.
        return query

    # 결정적 주제전환 가드(2차 안전망) — 새 검색이면 맥락을 버리고 원 질의를 그대로 쓴다.
    #   LLM 호출 전이라 비용·지연 0, 키 불필요. 프롬프트(1차)가 놓치는 오염을 결정적으로 막는다.
    if _is_topic_shift(query, context):
        logger.info("contextualize 주제전환 감지 → 맥락 버리고 원 질의 사용: query=%r", query)
        return query

    llm = _llm()  # 키 부재 시 여기서 fail-loud(맥락 있을 때만 도달).
    human = f"[직전 대화]\n{serialized}\n\n[현재 질의]\n{query}"

    try:
        resp = llm.invoke([("system", _SYSTEM_PROMPT), ("human", human)])
        rewritten = _extract_text(resp.content).strip()
    # D1: 광범위 except를 좁힌다 — LLM 호출/전송 계열 "예상한 실패"만 흡수해 원 질의로 폴백한다.
    #   AttributeError·TypeError 같은 프로그래밍 오류는 여기서 잡지 않으므로, 코드 버그가
    #   조용한 폴백에 묻히지 않고 그대로 전파돼 드러난다(복원력은 유지하되 버그는 숨기지 않음).
    except _EXPECTED_LLM_ERRORS as exc:  # 네트워크·전송 일시 오류 → 원 질의 폴백(키 부재는 위 require가 처리)
        logger.warning("contextualize 재작성 실패 → 원 질의 폴백: %r", exc)
        return query

    if not rewritten:
        logger.warning("contextualize 재작성 결과 공백 → 원 질의 폴백 (query=%r)", query)
        return query

    # D2: 맥락을 합쳐 재작성하면 query 입력 상한(MAX_QUERY_LENGTH)을 넘을 수 있다.
    #   상한 초과분이 다운스트림(라우터·LLM)으로 새지 않도록 안전하게 절단한다.
    #   (원 query는 스키마가 이미 상한 안으로 보장하므로, 넘치는 건 재작성으로 늘어난 경우뿐.)
    if len(rewritten) > MAX_QUERY_LENGTH:
        logger.warning(
            "contextualize 재작성 결과가 상한(%d자) 초과(%d자) → %d자로 절단",
            MAX_QUERY_LENGTH, len(rewritten), MAX_QUERY_LENGTH,
        )
        rewritten = rewritten[:MAX_QUERY_LENGTH].strip()
        if not rewritten:  # 절단 결과가 공백뿐이면 원 질의로 폴백(조용한 빈 결과 금지)
            return query

    logger.info("contextualize 질의=%r (+맥락 %d턴) → 재작성=%r", query, len(context), rewritten)
    return rewritten
