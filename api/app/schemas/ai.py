"""AI 검색 요청·응답 Pydantic 모델.

공통 계약(architecture.md): 응답은 {answer, listings[]}, 에러는 {error:{code,message}}.
필드는 전부 snake_case (DB·JSON 통일, 변환 없음).
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# 질의 입력 상한(글자 수) — 한 곳에서만 정의해 스키마와 맥락화 노드가 공유한다.
# (4.6 재작성 질의 길이 재검증이 이 상한과 어긋나지 않도록 매직넘버를 단일 출처로 둔다.)
MAX_QUERY_LENGTH = 1000


class RouterDecision(BaseModel):
    """라우터(router_node)의 구조화 출력 — 질의 의도 3분류(FR13).

    route만 A/B/C로 강제(Literal)해 LLM이 형식을 벗어나지 못하게 한다. reason은 선택(디버깅용).
      · A = 구조형(가격·차종·연식 등 명시 조건) → 경로 A(Text-to-SQL)
      · B = 질적·의미형(용도·느낌·추천) → 경로 B(문서 RAG)
      · C = 매물 무관(잡담·상식 등) → 가드(정중한 거절)
    """

    route: Literal["A", "B", "C"]
    reason: str | None = None


class ConversationTurn(BaseModel):
    """멀티턴 맥락의 한 턴(FR18) — 클라이언트가 보관하다 후속 질의에 동봉한다.

    role/content만 둔 최소 스키마. content 길이를 막아 과대 입력(DoS)을 닫는다.
    role은 사용자/어시스턴트 둘로 한정(Literal) — 형식이탈을 422로 거른다.
    이 모델은 '서버 무상태' 입력 계약일 뿐, 서버·DB에 저장하지 않는다(요청 본문에서만 온다).
    """

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000, description="턴 내용")


class SearchRequest(BaseModel):
    # max_length로 과대 입력을 막고(4.3+ LLM 비용·DoS 방어), 공백만 있는 질의는 거른다.
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH, description="자연어 검색 질의")
    # 멀티턴 맥락(FR18) — 4.6에서 실제로 읽어 후속 질의를 맥락화한다(서버 무상태: 매 요청에 클라가 동봉).
    # 원소 타입(ConversationTurn)·최대 턴 수(12)를 강제해 4.5까지 무제한이던 DoS 여지를 닫는다.
    # 빈/누락(None·[])은 단일턴으로 정상 동작(회귀 0).
    context: list[ConversationTurn] | None = Field(
        default=None, max_length=12, description="직전 대화 맥락(클라이언트 보관, 최대 12턴)"
    )

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, v: str) -> str:
        # "   "(공백·개행만) 같은 질의는 min_length=1을 통과하므로 별도로 막는다.
        if not v.strip():
            raise ValueError("query는 공백만으로 구성될 수 없습니다.")
        return v


class ListingCard(BaseModel):
    """매물 카드 — architecture.md 확정 7필드(사진/썸네일 없음)."""

    id: str
    manufacturer: str
    model: str
    year: int
    price: int       # 원(KRW)
    mileage: int     # km
    region: str


class SearchResponse(BaseModel):
    answer: str
    listings: list[ListingCard] = []


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
