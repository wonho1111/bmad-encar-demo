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

DW-855 3차 재검증(2026-09-09)에서 재검색은 막혔는데도 순번("첫 번째")·극값("제일 싼")·
비교("더 저렴한 쪽") 지칭을 모델이 직전 목록에서 잘못 읽는 유형이 남아, `resolve_list_reference`
(아래 (5))를 추가했다 — 지칭을 코드가 직접 id로 확정해 agent.py가 프롬프트 힌트·도구
인자 교체·최종 선택 좁히기 세 지점에 쓴다.

이 모듈은 agent.py의 도구 디스패치 루프와 최종화 단계에서 호출된다(agent.py가 유일한
호출자) — 여기서는 순수 함수만 두고 LangChain 메시지 타입(ToolMessage 등)은 agent.py가
조립한다(이 모듈이 agent.py를 임포트하지 않게 해 순환 임포트를 피한다).
[Source: DW-855·DW-869·DW-870 트리거 절; CLAUDE.md B9]
"""

import re

from app.graph import agent_tools

# ── (1) 멀티턴 재검색 차단 ────────────────────────────────────────────────
#
# 직전 목록을 가리키는 지칭 표현 — 이 중 하나라도 이번 질의에 있고 직전 목록 id가 하나라도
# 있으면, search_listings 재호출은 "새 조건 검색"이 아니라 "직전 목록 참조를 재검색으로
# 도피"한 것으로 본다(DW-855 실측: "나머지 두 개랑 비교해줘"가 model_keyword 재검색으로 샘).
# \d+번째는 "5번째"처럼 숫자가 붙은 형태, 번째 단독은 "두 번째"·"세 번째"처럼 한글 수사가
# 붙는 형태까지 부분일치로 덮는다(둘 다 있어야 "두→다섯" 전부 잡힌다는 뜻은 아니고, 후자
# 하나만으로도 전자를 포함하지만 스펙 원문의 두 표현을 그대로 남겨 의도를 드러낸다).
# 아래 줄(여기서·여기 중·…·그 목록)은 DW-872 update(2026-09-09 18:08) (b) 실측 추가분 —
# "여기서 흰색만 있어?"(C59)가 이 목록 밖이라 재검색으로 샜다.
_REFERENCE_PATTERN = re.compile(
    r"그중|그 중|그거|이 중|이중에|\d+번째|번째|나머지|앞의|둘 다|전부 비교|"
    r"여기서|여기 중|이 매물들|이것들|그것들|위에서|위 목록|위에 있는|얘네|요 중|그 목록"
)

# 재검색을 거절할 때 도구 대신 돌려주는 ToolMessage 텍스트(그대로 고정 — agent.py가 참조).
# 뒷문장(DW-872 실측 C50: 재검색이 막히자 "목록의 매물은 모두 무사고"라고 지어냄) — 거절만
# 하고 대안을 안 주면 모델이 목록에 없는 속성을 스스로 지어내므로, compare_listings로
# 확인하는 경로를 함께 안내한다. 마지막 문장(DW-872 update 2026-09-09 18:08 (d) 실측 C53:
# 재검색이 막히자 "목록에 없다"고 답함 — 정답은 직전 매물 id로 market_price_stats)은
# 시세·적정가 질문 전용 경로를 추가로 안내한다.
FOLLOWUP_REFUSAL_TEXT = (
    "직전 목록의 매물 id로만 답해야 합니다 — 재검색 금지 — 목록에 없는 속성(사고·색상 등)이 "
    "필요하면 compare_listings에 그 매물 id들을 넘겨 확인하고, 확인 안 된 속성은 단정하지 마라. "
    "시세·적정가 질문이면 compare_listings가 아니라 그 매물 id로 market_price_stats를 호출해라"
)


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


# ── (4) 검색 인자 자동 주입(DW-872 update 2026-09-09 18:08 (f)) ──────────────
#
# 실측(C02·C03): 'SUV'·'하이브리드'가 질문에 명시돼 있는데도 search_listings 인자로는 안
# 넘기고 query_text에만 실린다 — agent.py [도구 인자 규칙]은 프롬프트 문장일 뿐이라 실측으로
# 계속 샜다(CLAUDE.md B9 "지켜야 하는 규칙이면 실행되는 검사로 바꾼다"). 모델이 이미 채운
# 인자는 절대 덮지 않고, **비어 있는** 인자만 원문 질의의 닫힌 어휘로 채운다 — 어휘는
# agent_tools의 기존 화이트리스트·별칭 표를 그대로 재사용한다(새 표를 여기서 중복 정의하지
# 않는다, 단일 출처 유지). agent_tools는 이 모듈을 임포트하지 않으므로 순환 임포트가 생기지
# 않는다(agent.py → answer_guards → agent_tools 한 방향).
_NEGATION_WORDS = ("말고", "빼고", "제외", "아닌", "아니고", "빼면")
_SEATS_MIN_RE = re.compile(r"(\d)인승\s*이상")

# 사고 이력 없음 표현(C68 실측) — "사고 이력 없는 차"·"무사고"·"사고 없는"이 질의에 있으면
# search_listings의 accident_free_only를 채운다. 부정어 보호 규칙(말고/빼고/제외)은 다른
# 필드와 동일하게 _is_negated로 적용한다.
_ACCIDENT_FREE_RE = re.compile(r"사고\s*이력\s*없는|무사고|사고\s*없는")


def _is_negated(query: str, match_end: int) -> bool:
    """매치가 끝난 바로 뒤 6자 안에 부정어가 있으면 그 매치는 버린다(예: "SUV 말고 세단"
    에서 SUV는 부정으로 걸러지고 세단만 남는다)."""
    return any(neg in query[match_end:match_end + 6] for neg in _NEGATION_WORDS)


def _find_best_match(query: str, vocab: dict[str, str]) -> str | None:
    """vocab(소문자 검색어 → 주입값) 중 query에 부분일치(대소문자 무시 — query만 lower()
    해서 비교, vocab 키는 호출부가 이미 소문자로 준비해 온다)하면서 부정어에 걸리지 않은
    항목 중 **가장 긴 검색어** 하나를 고른다(동률이면 먼저 나오는 쪽) — "세단"·"준중형"·
    "준중형 세단"이 동시에 일치할 수 있어 가장 구체적인(긴) 쪽을 쓴다."""
    low = query.lower()
    best: tuple[int, int, str] | None = None  # (검색어 길이, 시작 위치, 주입값)
    for keyword, value in vocab.items():
        idx = low.find(keyword)
        if idx == -1 or _is_negated(query, idx + len(keyword)):
            continue
        if best is None or len(keyword) > best[0] or (len(keyword) == best[0] and idx < best[1]):
            best = (len(keyword), idx, value)
    return best[2] if best else None


def _fuel_vocab() -> dict[str, str]:
    return {kw.lower(): kw for kw in agent_tools._FUEL_WHITELIST}


def _body_type_vocab() -> dict[str, str]:
    # 별칭(세단·준중형·소형 suv …) 먼저 채우고 화이트리스트로 덮어써, "suv"/"SUV"처럼 같은
    # 소문자 키가 겹치면 화이트리스트 표기(SUV)가 이긴다(주입값의 대소문자를 결정론으로 고정).
    vocab = {kw.lower(): kw for kw in agent_tools._BODY_TYPE_ALIAS_MAP}
    vocab.update({kw.lower(): kw for kw in agent_tools._BODY_TYPE_WHITELIST})
    return vocab


_INJECT_EXCLUDED_MANUFACTURER_KEYS = {"삼성"}


# 예산 상한 패턴(DW-876 계열 실측 C48) — "N천만원/N백만원/N만원" + "이하/이내/까지" 최소
# 조합만 인식한다(과설계 금지, 복잡한 예산 표현·하한은 범위 밖). 천만원 단위를 먼저 찾아야
# 한다 — "4천만원"에서 만원 패턴이 먼저 매치되면 "4"만 남아 자릿수가 100만 배 어긋난다.
_BUDGET_SUFFIX = r"(?:이하|이내|까지)"
_BUDGET_CHEONMAN_RE = re.compile(rf"(\d+)\s*천만원\s*{_BUDGET_SUFFIX}")
_BUDGET_BAEKMAN_RE = re.compile(rf"(\d+)\s*백만원\s*{_BUDGET_SUFFIX}")
_BUDGET_MAN_RE = re.compile(rf"(\d+)\s*만원\s*{_BUDGET_SUFFIX}")


def _parse_budget_max(query: str) -> int | None:
    """질의에서 예산 상한(원 단위)을 뽑는다. 세 패턴 중 먼저 매치되는 것 하나만 쓴다."""
    m = _BUDGET_CHEONMAN_RE.search(query)
    if m:
        return int(m.group(1)) * 10_000_000
    m = _BUDGET_BAEKMAN_RE.search(query)
    if m:
        return int(m.group(1)) * 1_000_000
    m = _BUDGET_MAN_RE.search(query)
    if m:
        return int(m.group(1)) * 10_000
    return None


# 매물 검색 의도를 나타내는 추천/조회 문구(C36·C32 실측) — infer_missing_args의 구조 조건
# 어휘·예산 패턴 둘 다 없어도 이 문구가 있으면 "매물 추천 의도"로 본다. C32(챗봇 답변 검증
# 2026-09-14): "아이 둘 키우는데 차 뭐가 좋을까요"가 False로 새 추천 의도를 놓쳤다 — 지식
# 질문("무사고 매물이랑 단순교환 매물이랑 뭐가 달라요?"·"침수차량인지 구별하는 팁")은
# 여전히 이 어휘들과 겹치지 않아 False로 남는다(테스트로 고정).
_LISTING_INTENT_WORDS = (
    "추천", "좋은 차", "뭐 있", "보여", "좋을까", "뭐가 좋", "어떤 차", "찾아줘", "골라줘", "괜찮은 차",
)


def has_listing_intent(query: str) -> bool:
    """질의에 매물 검색 의도 어휘가 있는지 판정한다(DW-876 계열 실측 C36·C71 — 가이드
    게이트의 조기 "범위 밖" 거절이 매물 추천 의도까지 삼키는 결함 수정).

    세 가지 중 하나라도 있으면 True: (1) infer_missing_args가 채우는 구조 조건 어휘
    (연료·차종·제조사·좌석수 — accident_free_only 제외, 아래 참조), (2) 예산 금액 패턴
    (_parse_budget_max), (3) 추천을 요청하는 문구(_LISTING_INTENT_WORDS).

    accident_free_only(C68, 챗봇 답변 검증 2026-09-14)는 이 구조 조건 판정에서 뺀다 —
    "무사고 매물이랑 단순교환 매물이랑 뭐가 달라요?" 같은 지식 질문에도 "무사고"라는 단어가
    있어 infer_missing_args가 그 필드만 채우는데, 이런 질문은 매물 추천 의도가 아니라 여전히
    False여야 한다(테스트로 고정). 다른 구조 조건 어휘(연료·차종 등)는 지식 질문 문맥에서
    쓰이는 경우가 드물어 그대로 True 판정에 남긴다."""
    inferred = infer_missing_args(query, {})
    structural = {k: v for k, v in inferred.items() if k != "accident_free_only"}
    if structural:
        return True
    if _parse_budget_max(query) is not None:
        return True
    return any(w in query for w in _LISTING_INTENT_WORDS)


def _manufacturer_vocab() -> dict[str, str]:
    # 별칭은 agent_tools._MANUFACTURER_ALIAS_MAP의 값(이미 해석된 화이트리스트 값)을 그대로
    # 주입값으로 쓴다(예: "르노"→"르노코리아") — body_type과 달리 manufacturer는 단일 문자열
    # 인자라 여러 값으로 펼칠 필요가 없다.
    # 자동 주입 전용 제외(DW-872 묶음 3 검토): '삼성'은 지명·전자제품 등 무관한 문맥에 흔해
    # 질문에서 자동으로 제조사를 채우면 오탐이 크다. LLM이 명시 인자로 넘기는 경로(agent_tools)의
    # 별칭표는 그대로 두고, 여기(질문 텍스트 스캔)에서만 뺀다.
    vocab = {kw.lower(): resolved for kw, resolved in agent_tools._MANUFACTURER_ALIAS_MAP.items()
             if kw not in _INJECT_EXCLUDED_MANUFACTURER_KEYS}
    vocab.update({kw.lower(): kw for kw in agent_tools._MANUFACTURER_WHITELIST})
    return vocab


# ── (5) 직전 목록 지칭 결정론 해석(DW-855) ────────────────────────────────
#
# 실측(DW-855 3차 재검증, 2026-09-09): 재검색은 코드로 막혔고 직전 목록 id도 프롬프트에
# 명시되는데도, 모델이 순번("첫 번째")·극값("제일 싼")·비교("더 저렴한 쪽") 지칭을 직전
# 목록에서 잘못 읽는 유형이 남았다(C48·C50·C59·C60). "프롬프트 규칙을 강화"하는 대신
# CLAUDE.md B9대로 **코드가 직접 지칭을 풀어 id로 확정**한다 — 순수 함수, LLM 호출 없음.
_ORDINAL_WORD_RE = re.compile(r"(첫|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*번째")
_ORDINAL_DIGIT_JJAE_RE = re.compile(r"(\d+)\s*번째")
_ORDINAL_DIGIT_BEON_RE = re.compile(r"(\d+)\s*번(?!째)")
_ORDINAL_WORD_MAP = {
    "첫": 1, "두": 2, "세": 3, "네": 4, "다섯": 5,
    "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10,
}


def _resolve_ordinal(query: str) -> int | None:
    """"첫 번째"·"두 번째"(한글 수사)·"2번째"(숫자+번째)·"1번"(숫자+번) 지칭에서 순번을
    뽑는다. 여럿 섞여 있으면 한글 수사 → 숫자+번째 → 숫자+번 순으로 먼저 찾은 것을 쓴다
    (문장에 먼저 등장하는 것을 따로 고르지 않는다 — "부정어·범위 밖 표현은 건드리지
    않는다"는 스펙대로, "말고"류 정정 표현까지 해석하려 들지 않는다)."""
    m = _ORDINAL_WORD_RE.search(query)
    if m:
        return _ORDINAL_WORD_MAP.get(m.group(1))
    m = _ORDINAL_DIGIT_JJAE_RE.search(query)
    if m:
        return int(m.group(1))
    m = _ORDINAL_DIGIT_BEON_RE.search(query)
    if m:
        return int(m.group(1))
    return None


# 극값·비교 지칭 → (카드 속성, 오름차순 여부). 비교("더 저렴한 쪽"/"둘 중 싼 거")는 카드가
# 정확히 몇 장이든 같은 결정 규칙(직전 목록 전체에서 최솟/최댓값)으로 처리한다 — "그중 더
# 저렴한 쪽"이 가리키는 부분집합을 따로 추적하지 않는다(스펙 범위 밖, 카드 목록 자체가 이미
# 그 턴에서 다룬 대상들이라는 전제).
_EXTREME_RULES: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"(가장|제일)\s*(싸|저렴|싼)"), "price", True),
    (re.compile(r"(가장|제일)\s*(비싸|비쌈|비싼)"), "price", False),
    (re.compile(r"더\s*(싸|저렴)\w*\s*쪽|둘\s*중\s*(싸|저렴)"), "price", True),
    (re.compile(r"더\s*비싼\s*쪽|둘\s*중\s*비싼"), "price", False),
    (re.compile(r"(가장|제일)\s*(최신|신형)"), "year", False),
    (re.compile(r"(가장|제일)\s*오래된"), "year", True),
    (re.compile(r"주행.{0,4}짧은"), "mileage", True),
    (re.compile(r"주행.{0,4}긴"), "mileage", False),
]


def resolve_list_reference(query: str, cards: list, ordinal_cards: list | None = None) -> list[str] | None:
    """직전 목록 카드에서 순번·극값·비교 지칭을 결정적으로 풀어 매물 id 목록을 돌려준다.

    cards: 극값·비교 지칭(예: "제일 싼 거")이 기준으로 삼는 카드 목록 — 여러 턴을 병합한
    순서(agent._format_recent_listings_block과 동일)라도 된다.
    ordinal_cards: 순번 지칭("첫 번째" 등)의 기준 목록. 생략하면 cards를 그대로 쓴다. DW-855
    3차 재검증 후속(C59 실측): "가장 최근 listing_ids를 가진 어시스턴트 턴" 하나의 카드
    순서여야 한다 — 여러 턴을 병합한 목록으로 순번을 풀면 오래된 턴의 매물이 끼어든다
    (agent._recent_assistant_listing_ids는 멀티턴 참조 전반을 위해 병합하지만, 순번엔
    agent._latest_assistant_listing_ids로 뽑은 최신 턴 하나만 써야 한다).

    id·price·year·mileage 속성만 읽는다(ListingCard 계약, app/schemas/ai.py — 셋 다 non-null).

    지칭이 없거나(순번·극값·비교 패턴 미검출) 두 카드 목록이 모두 비어 있으면 None. 순번이
    ordinal_cards 범위를 벗어나면(예: 카드 2장인데 "5번째") 그 순번은 버리고 극값·비교
    패턴을 계속 찾는다 — "5번째"가 극값 표현이 아니면 최종적으로 None(부정어·범위 밖 표현은
    건드리지 않는다).
    """
    if ordinal_cards is None:
        ordinal_cards = cards
    if not cards and not ordinal_cards:
        return None

    ordinal = _resolve_ordinal(query)
    if ordinal is not None and ordinal_cards and 1 <= ordinal <= len(ordinal_cards):
        return [ordinal_cards[ordinal - 1].id]

    if not cards:
        return None

    for pattern, field, ascending in _EXTREME_RULES:
        if not pattern.search(query):
            continue
        values = [(getattr(card, field), card.id) for card in cards]
        if not values:
            continue
        chosen = min(values) if ascending else max(values)
        return [chosen[1]]

    return None


# ── (6) 직전 목록 속성 좁힘(DW-872 계열 실측 C50·C59) ─────────────────────
#
# 실측: 재검색은 코드로 막혔고 직전 목록 id도 프롬프트에 명시되는데도, 모델이 목록에 실제로
# 있는 사고 상태·색상을 반대로 말했다(예: "목록은 모두 무사고"라고 지어냄, C50 — 도구 원문을
# 읽고도 반대로 답함). "그 중에 무사고인 것만"·"여기서 흰색만 있어?" 같은 후속 질의는 코드가
# 직접 카드 속성을 비교해 id를 걸러낸다 — LLM이 도구 텍스트를 다시 해석하지 않게 한다.
_ACCIDENT_STATUS_VALUES_ORDERED = ("무사고", "단순교환", "사고")


def _match_accident_status(query: str) -> str | None:
    """사고 상태 어휘를 찾는다. "무사고"·"단순교환"을 "사고"보다 먼저 검사해야 한다 —
    "무사고"에도 "사고"라는 부분 문자열이 들어 있어 순서를 바꾸면 항상 "사고"만 잡힌다."""
    for value in _ACCIDENT_STATUS_VALUES_ORDERED:
        if value in query:
            return value
    return None


def _color_vocab() -> dict[str, str]:
    vocab = {kw.lower(): resolved for kw, resolved in agent_tools._COLOR_ALIAS_MAP.items()}
    vocab.update({kw.lower(): kw for kw in agent_tools._COLOR_WHITELIST})
    return vocab


def _narrow_conditions(query: str) -> tuple[str | None, str | None, str | None]:
    """narrow_by_attribute·format_narrow_by_attribute_answer가 공유하는 조건 판정(사고 상태·
    색상·연료) — 두 함수가 같은 매칭 결과를 써야 "카드는 A인데 본문은 B"류 불일치가 안 생긴다."""
    accident = _match_accident_status(query)
    color = _find_best_match(query, _color_vocab())
    fuel = _find_best_match(query, _fuel_vocab())
    return accident, color, fuel


def narrow_by_attribute(query: str, cards: list) -> list[str] | None:
    """후속 지칭 질의가 사고 상태·색상·연료로 직전 목록을 좁히면, 그 조건에 맞는 카드 id만
    걸러 돌려준다(빈 리스트 포함 — 조건에 맞는 매물이 없다는 뜻). 셋 다 매치되지 않으면
    None(좁히지 않음 — 순번·극값 등 다른 지칭과 섞이지 않는다).

    cards: color까지 채워진 ListingCard 목록이어야 한다(agent._cards_for_ids가 color 포함
    SELECT로 조회해 넘긴다 — 이 함수는 card.color가 이미 채워져 있다고 가정한다)."""
    if not cards:
        return None
    accident, color, fuel = _narrow_conditions(query)
    if accident is None and color is None and fuel is None:
        return None
    matched = []
    for card in cards:
        if accident is not None and card.accident_status != accident:
            continue
        if color is not None and card.color != color:
            continue
        if fuel is not None and card.fuel != fuel:
            continue
        matched.append(card.id)
    return matched


# ── (6b) 직전 목록 속성 좁힘 — 답변 본문도 코드가 만든다(챗봇 답변 검증 2026-09-14, C50·C59) ──
#
# 실측: narrow_by_attribute가 카드(listings)는 정확히 걸러내는데도, LLM이 본문에서 그 결과와
# 모순되는 말을 지어냈다(예: "스파크는 무사고 확인 안 돼 제외"(실제 무사고), "색상 정보
# 없음"(실제 흰색 2건)). 카드만 코드로 고정하고 본문은 LLM에 맡기는 절반짜리 방어로는 안
# 잡혀, 속성 좁힘 + 다른 요구가 안 섞인 질의는 LLM 루프 자체를 타지 않고 코드가 답을 통째로
# 만든다(CLAUDE.md B9 — 실행되는 검사로 바꾼다). 시세·비교 등 다른 요구가 섞이면(예: "그중
# 흰색 시세 봐줘") 템플릿이 그 요구까지 답할 수 없으므로 기존 경로(해석 id를 도구 인자로)를
# 그대로 쓴다.
_NARROW_MIXED_INTENT_WORDS = ("시세", "적정가", "가격대", "비교")


def has_mixed_intent_beyond_narrowing(query: str) -> bool:
    """속성 좁힘 질의에 시세·비교 등 다른 요구가 섞여 있는지 본다 — 섞여 있으면 템플릿 답변
    대신 기존 LLM 경로를 써야 한다(템플릿은 좁힌 목록 제시만 할 뿐 시세·비교에는 답 못 함)."""
    return any(w in query for w in _NARROW_MIXED_INTENT_WORDS)


def format_narrow_by_attribute_answer(query: str, cards: list, matched_ids: list[str]) -> str:
    """narrow_by_attribute가 걸러낸 id 목록으로 답변 본문 자체를 코드가 조립한다(LLM 호출
    없음) — 카드와 본문이 항상 같은 판정 결과(_narrow_conditions)를 쓰므로 모순이 날 수
    없다. 조건 설명은 매치된 항목을 "·"로 이어 붙인다(예: "무사고·흰색").

    cards: matched_ids가 가리키는 카드를 찾을 원본 목록(narrow_by_attribute에 넘긴 것과
    동일한 color 포함 카드)."""
    accident, color, fuel = _narrow_conditions(query)
    condition = "·".join(v for v in (accident, color, fuel) if v)
    if not matched_ids:
        return f"직전 목록에는 {condition}인 매물이 없습니다. 조건을 넓혀 다시 찾아드릴까요?"
    by_id = {c.id: c for c in cards}
    lines = [f"직전 목록 중 {condition}인 매물은 {len(matched_ids)}건입니다."]
    for lid in matched_ids:
        card = by_id.get(lid)
        if card is None:
            continue  # 강건성 — narrow_by_attribute는 cards 안의 id만 돌려주므로 정상 경로는 항상 찾는다.
        attr_value = "·".join(
            v for v in (
                card.accident_status if accident is not None else None,
                card.color if color is not None else None,
                card.fuel if fuel is not None else None,
            ) if v
        )
        lines.append(
            f"{card.manufacturer} {card.model} {card.year}년식 · {card.price:,}원 · "
            f"{card.mileage:,}km · {attr_value}"
        )
    return "\n".join(lines)


def infer_missing_args(query: str, args: dict) -> dict:
    """search_listings 호출 인자 중 **모델이 비워 둔 것만** 원문 질의의 닫힌 어휘로 채운
    새 dict를 돌려준다(원본 args는 바꾸지 않는다 — 순수 함수, 부작용 없음).

    채우는 필드 — fuel·body_type·manufacturer(문자열 부분일치, 가장 긴 일치 하나만)·
    seats_min("N인승 이상" 패턴 하나뿐)·price_max(예산 패턴, _parse_budget_max). 부정어(말고·
    빼고·제외·아닌·아니고·빼면)가 매치 바로 뒤 6자 안에 있으면 그 매치는 채우지 않는다(예:
    "SUV 말고 세단" → body_type=세단만). body_type은 agent_tools.search_listings가 호출
    시점에 다시 해석하는 원시 표기(예: "세단") 그대로 넣는다 — "세단"→[준중형차·중형차·대형차]
    같은 다중값 펼치기는 이 함수의 일이 아니라 도구 쪽 _resolve_body_type이 이미 하는 일이다
    (중복 구현 금지).

    manufacturer는 다른 세 필드와 달리 **이미 값이 있어도** 별칭 사전으로 정규화한다(C19
    실측 — 모델이 manufacturer="르노"를 스스로 채우면 "비어 있을 때만 주입"하는 기존 규칙은
    건드리지 않아 CHECK 허용값 밖 표기가 그대로 남는다). 이 정규화는 defense-in-depth다 —
    agent_tools.search_listings도 SQL을 짜기 직전에 같은 별칭 사전으로 한 번 더 정규화하므로
    검색 결과 자체는 이미 정확했지만(로컬 실측 확인), 도구 호출 인자 로그·판정에 정규화 전
    표기가 그대로 남아 CHECK 목록과 어긋나 보인다.
    """
    result = dict(args)
    if not result.get("fuel"):
        matched = _find_best_match(query, _fuel_vocab())
        if matched:
            result["fuel"] = matched
    if not result.get("body_type"):
        matched = _find_best_match(query, _body_type_vocab())
        if matched:
            result["body_type"] = matched
    if result.get("manufacturer"):
        result["manufacturer"] = agent_tools._MANUFACTURER_ALIAS_MAP.get(
            result["manufacturer"], result["manufacturer"]
        )
    else:
        matched = _find_best_match(query, _manufacturer_vocab())
        if matched:
            result["manufacturer"] = matched
    if not result.get("seats_min"):
        m = _SEATS_MIN_RE.search(query)
        if m and not _is_negated(query, m.end()):
            result["seats_min"] = int(m.group(1))
    if not result.get("price_max"):
        budget = _parse_budget_max(query)
        if budget is not None:
            result["price_max"] = budget
    if result.get("accident_free_only") is None:
        # bool 필드라 다른 필드처럼 "not result.get(...)"을 쓰면 모델이 이미 명시적으로
        # False(무사고를 요구하지 않음)를 채운 값까지 True로 덮어쓴다 — 값이 아예 없을
        # 때(None)만 채운다.
        m = _ACCIDENT_FREE_RE.search(query)
        if m and not _is_negated(query, m.end()):
            result["accident_free_only"] = True
    return result
