"""AI 검색 요청·응답 Pydantic 모델.

공통 계약(architecture.md): 응답은 {answer, listings[]}, 에러는 {error:{code,message}}.
필드는 전부 snake_case (DB·JSON 통일, 변환 없음).
"""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="자연어 검색 질의")
    # 멀티턴 맥락 — 4.6에서 사용. 4.1은 받아두되 무시(서버 무상태).
    context: list | None = Field(default=None, description="직전 대화 맥락(클라이언트 보관)")


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
