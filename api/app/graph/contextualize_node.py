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
_SYSTEM_PROMPT = """너는 중고차 검색 대화의 "질의 재작성기"다.
아래 [직전 대화]를 참고해, [현재 질의]를 그것만 읽어도 뜻이 통하는
독립적인 중고차 검색 질의 한 문장으로 다시 써라.

규칙:
- "그 중", "그거", "아까 그", "방금", "그럼" 같은 지시어를 직전 대화의 구체 내용으로 치환한다.
- 직전 대화에 없는 새 조건·차종·매물을 지어내지 않는다(있는 맥락만 흡수).
- 현재 질의가 이미 독립적이면 거의 그대로 둔다.
- 출력은 재작성된 질의 "한 줄"만. 설명·따옴표·접두어 없이."""

# 토큰 절약 — context가 길어도 최근 N턴만 맥락으로 쓴다(스키마가 이미 12턴으로 제한하지만 추가 안전).
_MAX_CONTEXT_TURNS = 6


def _llm() -> ChatGoogleGenerativeAI:
    """재작성용 LLM. temperature=0으로 같은 입력에 같은 재작성이 나오게 한다(재현성·보수성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,  # gemini-flash-latest
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


def contextualize_query(query: str, context: list | None = None) -> str:
    """직전 대화 맥락을 반영해 query를 독립 질의로 재작성한다(FR18).

    context가 비면(None·[]) LLM을 부르지 않고 query를 그대로 반환한다(단일턴, 함정 #2).
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
