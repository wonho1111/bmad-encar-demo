"""AI 검색 요청·응답 Pydantic 모델.

공통 계약(architecture.md): 응답은 {answer, listings[]}, 에러는 {error:{code,message}}.
필드는 전부 snake_case (DB·JSON 통일, 변환 없음).
"""

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    # max_length로 과대 입력을 막고(4.3+ LLM 비용·DoS 방어), 공백만 있는 질의는 거른다.
    query: str = Field(..., min_length=1, max_length=1000, description="자연어 검색 질의")
    # 멀티턴 맥락 — 4.6에서 사용. 4.1은 받아두되 무시(서버 무상태).
    context: list | None = Field(default=None, description="직전 대화 맥락(클라이언트 보관)")

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
