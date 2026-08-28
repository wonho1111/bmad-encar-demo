"""multi-query 분해 + RRF 병합 — 복합 질의의 질의 희석을 완화한다.

흐름: 질의 → (Gemini) 주제 축별 하위 질의 2~4개로 분해 → 하위 질의마다 embed_query +
  find_relevant_guide(top-k 상대 게이트, FR49) → RRF(Reciprocal Rank Fusion, 순위 역수 합산)로
  병합 → 상위 5개 (title, content).

왜: 긴 복합 질의("초년생·유지비·가성비·통풍시트")를 벡터 1개로 만들면 여러 주제의 평균이 돼
  어느 섹션과도 부분적으로만 닮는다(질의 희석). 섹션 청킹(Story 13.6)만으로는 주제가 3개
  이상이면 top-k 상대 게이트 마진 밖의 관련 섹션을 놓친다. 질의를 주제 축별 하위 질의로
  쪼개 각각 검색하면 각 하위 질의는 벡터 1개=주제 1개가 돼 해당 섹션과 훨씬 가까워진다.

발동 조건: `_MIN_QUERY_LEN`(20자) 미만의 짧은 질의는 분해하지 않는다(주제가 하나일 확률이
  높고, 분해해봐야 LLM+임베딩 추가 호출만 낭비다). 분해 결과가 없으면(짧은 질의·LLM이
  NONE·LLM 예외) 원 질의 단독 검색으로 폴백한다 — hybrid_rag_node의 기존 find_relevant_guide
  단독 호출과 동일한 결과가 나온다(회귀 없음, 추가 임베딩 호출 0회).

find_relevant_guides_fused()는 doc_rag_node.find_relevant_guide/_vec_literal을 그대로
재사용한다(top-k 상대 게이트를 이 파일이 새로 만들지 않는다 — 드리프트 방지).
[Source: multi-query 분해 + RRF 병합 작업 지시; doc_rag_node.py find_relevant_guide(FR49);
 hybrid_rag_node.py _llm 패턴]
"""

import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.embeddings import embed_query
from app.graph.doc_rag_node import _vec_literal, find_relevant_guide
from app.graph.sql_rag_node import _content_to_text

logger = logging.getLogger(__name__)

# 이 길이 미만의 짧은 질의는 분해하지 않는다 — 주제가 하나일 확률이 높고, 분해해봐야
# LLM 호출·하위 질의별 재임베딩만 늘어난다(비용 대비 이득이 없다).
_MIN_QUERY_LEN = 20

# RRF(Reciprocal Rank Fusion) 상수 — 순위 r(0-base)의 점수를 1/(k+r)로 계산한다. 60은
# RRF 논문·업계 관행에서 흔히 쓰는 값으로, 상위 몇 등 사이의 점수 차를 완만하게 만들어
# 여러 리스트를 합칠 때 1등 쏠림을 줄인다.
_RRF_K = 60

# 병합 결과에서 최종적으로 남길 개수 — hybrid_rag_node._GUIDE_INJECT_MAX(3)보다 넉넉히 둬,
# 주입 단계(hybrid_rag_node._select_guides_to_inject)가 순위 내림차순으로 다시 추릴 수 있게 한다.
_FUSED_RESULT_LIMIT = 5

_SYSTEM_PROMPT = """너는 중고차 검색 질의를 검색하기 좋은 하위 질의로 분해하는 조수다.

질의를 서로 다른 주제 축(예산/용도·페르소나/연료·유지비/옵션/차종)별 독립 하위 질의
2~4개로 분해하라. 각 줄에 하나씩, 하위 질의만 출력한다. 주제가 사실상 하나면 NONE만 출력한다.

예시 1(복합 질의 → 3줄 분해):
질의: "2천만원 이하의 유지비가 적고 가성비가 좋은 통풍시트 옵션이 포함된 사회초년생용 중고차를 추천해줘."
출력:
2천만원 이하 사회초년생용 중고차
유지비가 적고 가성비가 좋은 차
통풍시트 옵션이 있는 차

예시 2(단일 주제 → NONE):
질의: "3천만원 이하 흰색 SUV"
출력:
NONE"""

# 폴백 신호(NONE) 인식 — hybrid_rag_node._NONE_SENTINEL_RE와 동일한 관대한 인식(따옴표·백틱·
# 마침표·공백만 두른 형태도 폴백으로 읽는다). 정확히 "NONE"만 보면 LLM이 "NONE."류로 살짝
# 어긋나게 낼 때 분해된 것으로 오인해 빈 줄이 하위 질의로 섞여 들어간다.
_NONE_SENTINEL_RE = re.compile(r"""^["'`.\s]*none["'`.\s]*$""", re.IGNORECASE)

# 비정상 출력 방어 — 하위 질의 한 줄이 이 길이를 넘으면 분해가 아니라 LLM이 설명·원문을
# 통째로 반복한 것으로 보고 버린다.
_MAX_SUBQUERY_LEN = 80

# 5줄 이상 오면 앞 4개만 쓴다(주제 축 2~4개라는 지시를 못 지킨 이상 출력 방어).
_MAX_SUBQUERIES = 4


def _llm() -> ChatGoogleGenerativeAI:
    """질의 분해용 LLM. temperature=0으로 같은 질의에 같은 분해가 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def decompose_query(query: str) -> list[str]:
    """질의를 주제 축별 하위 질의로 분해한다. 분해 안 함/실패 시 빈 리스트.

    빈 리스트는 "원 질의 단독 검색으로 폴백"의 신호다 — 분해 실패는 기능 저하일 뿐
    에러가 아니므로 예외를 올리지 않는다(hybrid_rag_node의 NONE 폴백과 같은 태도).
    """
    if len(query) < _MIN_QUERY_LEN:
        return []

    try:
        llm = _llm()
        raw = llm.invoke([("system", _SYSTEM_PROMPT), ("human", query)]).content
    except Exception as exc:  # LLM 호출 실패(네트워크·형식오류 등) — 원 질의 단독 검색으로 폴백.
        logger.warning("decompose_query LLM 호출 실패 → 분해 생략: %r", exc)
        return []

    # 일부 Gemini 모델은 .content를 문자열이 아니라 콘텐츠 블록 리스트로 돌려준다(실측:
    # gemini-3.1-flash-lite) — sql_rag_node의 공유 헬퍼로 text 블록만 뽑는다(str(raw)로
    # 통째로 문자열화하면 파이썬 리스트 표현이 한 줄로 잡혀 80자 상한에 걸려 전부 버려진다).
    text = _content_to_text(raw)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    if not lines or (len(lines) == 1 and _NONE_SENTINEL_RE.match(lines[0])):
        return []

    subqueries = [line for line in lines[:_MAX_SUBQUERIES] if len(line) <= _MAX_SUBQUERY_LEN]
    logger.info("decompose_query 질의=%r → 하위질의=%r", query, subqueries)
    return subqueries


def find_relevant_guides_fused(query: str, qvec_literal: str) -> list[tuple[str, str]]:
    """원 질의 + 하위 질의들의 가이드 검색 결과를 RRF로 병합해 상위 5개를 반환한다.

    원 질의 벡터로 find_relevant_guide()를 항상 1회 호출한다(기존 경로 보존 — 하위 질의가
    없으면 이 결과가 그대로 최종 결과다, 추가 임베딩 호출 0회).

    decompose_query가 하위 질의를 주면 각각 embed_query → _vec_literal → find_relevant_guide로
    검색한 뒤, 각 결과 리스트의 순위 r(0-base)마다 1/(_RRF_K+r)점을 title 키로 합산한다.
    원 질의 결과는 2배 가중한다 — 하위 질의는 원 질의를 보조하는 것이지, 원 질의 의도를
    대체하지 않는다(원 질의가 여전히 기준).
    """
    guides = find_relevant_guide(qvec_literal)  # 항상 1회 — 기존 경로 보존.
    result_lists = [guides]
    weights = [2.0]

    subqueries = decompose_query(query)
    for subquery in subqueries:
        sub_vec = _vec_literal(embed_query(subquery))
        result_lists.append(find_relevant_guide(sub_vec))
        weights.append(1.0)

    if not subqueries:
        # 하위 질의 없음 — 원 질의 결과 그대로(추가 임베딩 0회, 기존과 동작 동일).
        return guides

    scores: dict[str, float] = {}
    contents: dict[str, str] = {}
    for result_list, weight in zip(result_lists, weights):
        for rank, (title, content) in enumerate(result_list):
            scores[title] = scores.get(title, 0.0) + weight / (_RRF_K + rank)
            contents.setdefault(title, content)

    fused_titles = sorted(scores, key=lambda title: scores[title], reverse=True)
    fused = [(title, contents[title]) for title in fused_titles[:_FUSED_RESULT_LIMIT]]
    logger.info(
        "find_relevant_guides_fused 질의=%r 하위질의=%r → 병합결과=%r",
        query, subqueries, [title for title, _content in fused],
    )
    return fused
