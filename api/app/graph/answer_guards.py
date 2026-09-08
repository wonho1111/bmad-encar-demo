"""에이전트 최종 답변에 대한 결정론 방어 3종 — 전부 LLM 호출 없는 순수 함수다.

프롬프트(agent.py _SYSTEM_PROMPT)만으로는 세 가지가 실측으로 계속 샜다(챗봇 답변 검증
2026-09-08~09, `_bmad-output/implementation-artifacts/deferred-work.md` DW-855·869·870):
  1. 멀티턴 지칭("나머지 두 개랑 비교해줘")인데도 모델이 직전 목록 id 대신 재검색을
     한다(DW-855, 회귀 MT5) — "규칙을 안 지키면"이 아니라 "지키지 않아도 실행되는" 구조가
     문제이므로, 프롬프트 규칙을 강화하는 대신 **도구 실행 자체를 코드로 막는다**(CLAUDE.md
     B9 "주석·문서는 계약이 아니다 — 실행되는 검사로 바꾼다").
  2. 시세 비교군이 3건 미만인데도 중앙값·범위를 단정적으로 전달한다(DW-869).
  3. 답변 본문에 매물 내부 UUID가 그대로 노출된다(DW-870).
2·3은 LLM이 프롬프트 규칙을 놓쳐도 최종 답변을 한 번 더 지나가며 결정론적으로 보정한다
(사람이 매번 확인하지 않아도 되는 안전망 — "재검색 금지"는 사전 차단, 이 둘은 사후 보정).

이 모듈은 agent.py의 도구 디스패치 루프와 최종화 단계에서 호출된다(agent.py가 유일한
호출자) — 여기서는 순수 함수만 두고 LangChain 메시지 타입(ToolMessage 등)은 agent.py가
조립한다(이 모듈이 agent.py를 임포트하지 않게 해 순환 임포트를 피한다).
[Source: DW-855·DW-869·DW-870 트리거 절; CLAUDE.md B9]
"""

import re

# ── (1) 멀티턴 재검색 차단 ────────────────────────────────────────────────
#
# 직전 목록을 가리키는 지칭 표현 — 이 중 하나라도 이번 질의에 있고 직전 목록 id가 하나라도
# 있으면, search_listings 재호출은 "새 조건 검색"이 아니라 "직전 목록 참조를 재검색으로
# 도피"한 것으로 본다(DW-855 실측: "나머지 두 개랑 비교해줘"가 model_keyword 재검색으로 샘).
# \d+번째는 "5번째"처럼 숫자가 붙은 형태, 번째 단독은 "두 번째"·"세 번째"처럼 한글 수사가
# 붙는 형태까지 부분일치로 덮는다(둘 다 있어야 "두→다섯" 전부 잡힌다는 뜻은 아니고, 후자
# 하나만으로도 전자를 포함하지만 스펙 원문의 두 표현을 그대로 남겨 의도를 드러낸다).
_REFERENCE_PATTERN = re.compile(
    r"그중|그 중|그거|이 중|이중에|\d+번째|번째|나머지|앞의|둘 다|전부 비교"
)

# 재검색을 거절할 때 도구 대신 돌려주는 ToolMessage 텍스트(그대로 고정 — agent.py가 참조).
FOLLOWUP_REFUSAL_TEXT = "직전 목록의 매물 id로만 답해야 합니다 — 재검색 금지"


def block_research_on_followup(query: str, context: list[str] | None) -> bool:
    """이번 질의가 직전 목록을 가리키는 후속 지칭이고, 그 직전 목록 id가 실제로 있으면
    True(→ search_listings 재호출을 막아야 한다).

    query: contextualize_query를 거친 이번 턴 질의(에이전트 루프에 실제로 전달되는 문자열).
    context: 직전 대화가 실제로 보여준 매물 id 목록(agent._recent_assistant_listing_ids의
    결과 — "직전 대화 원문"이 아니라 이미 뽑아낸 id 리스트다. 여기 함수는 그 리스트의
    유무만 보고, 대화 내용 자체를 다시 스캔하지 않는다(중복 로직·순환 임포트 방지).
    """
    if not context:
        return False
    return bool(_REFERENCE_PATTERN.search(query))


# ── (2) 답변 본문 매물 id 제거(DW-870) ───────────────────────────────────
#
# 도구 텍스트(예: "id=8f9ad147-...")는 후속 도구 호출을 위해 LLM에게 보이는 재료일 뿐,
# 최종 답변에 그대로 옮겨 적으면 사용자에게 의미 없는 문자열이 노출된다.
_UUID_PATTERN = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_ID_PAREN_RE = re.compile(rf"\(\s*id\s*[:=]\s*{_UUID_PATTERN}\s*\)")  # "(id: <uuid>)" 통째로
_ID_LABEL_RE = re.compile(rf"\bid\s*[:=]\s*{_UUID_PATTERN}")  # 괄호 없는 "id=<uuid>"/"id: <uuid>"
_BARE_UUID_RE = re.compile(_UUID_PATTERN)  # 위 두 패턴이 못 잡는 맨 UUID(라벨 없이 단독 등장)
_MULTI_SPACE_RE = re.compile(r" {2,}")


def strip_listing_ids(answer: str) -> str:
    """답변 문자열에서 매물 내부 UUID 흔적을 지운다 — "(id: ...)"·"id=..." 형태와 라벨 없는
    맨 UUID까지 제거한 뒤, 그 자리에 남는 중복 공백만 한 칸으로 정리한다(문장을 다시 짜
    맞추지는 않는다 — 그 정도로 충분히 자연스러워진다)."""
    if not answer:
        return answer
    cleaned = _ID_PAREN_RE.sub("", answer)
    cleaned = _ID_LABEL_RE.sub("", cleaned)
    cleaned = _BARE_UUID_RE.sub("", cleaned)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


# ── (3) 시세 표본 부족 주의 문구 보정(DW-869) ────────────────────────────
#
# market_price.diagnose()의 MIN_VERDICT_SAMPLE(3) 미만이면 판정 자체가 보류되는데도, LLM이
# 도구 텍스트의 중앙값·범위 숫자만 보고 단정적으로 전달하는 실측 결함이 있었다. agent_tools.
# _format_market_diagnosis가 도구 텍스트에 이미 주의 문구를 넣지만(1차 방어, LLM이 참고할
# 재료), 이 함수는 최종 답변 자체에 그 문구가 없을 때 한 번 더 덧붙이는 2차 방어다.
def ensure_sample_caveat(answer: str, market_diagnoses: list[dict] | None) -> str:
    """market_diagnoses 중 비교군(criteria.sample_count)이 3건 미만인 진단이 하나라도
    있는데 답변에 "표본"·"참고만"이 전혀 없으면, 그 사실을 알리는 문장을 덧붙인다."""
    if not market_diagnoses:
        return answer
    small = [
        d for d in market_diagnoses
        if isinstance(d, dict) and (d.get("criteria") or {}).get("sample_count", 999) < 3
    ]
    if not small:
        return answer
    if "표본" in answer or "참고만" in answer:
        return answer
    n = small[0]["criteria"]["sample_count"]
    return f"{answer} 비교 가능한 매물이 {n}건뿐이라 표본이 적어 참고만 하세요."
