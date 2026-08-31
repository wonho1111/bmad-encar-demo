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
    """라우터(router_node)의 구조화 출력 — 질의 의도 4분류(FR13·FR43, 13.2 4분기 라우팅).

    route만 REJECT/CLARIFY/SQL/HYBRID로 강제(Literal)해 LLM이 형식을 벗어나지 못하게 한다.
    reason은 선택(디버깅용).
      · SQL = 구조형(가격·차종·연식 등 명시 조건만) → 경로 SQL(Text-to-SQL)
      · HYBRID = 구조 조건 + 의미/느낌 조건이 함께 있는 조합형(신규) → 경로 HYBRID
        (13.3 전까지는 sql_rag_node로 임시 실행)
      · CLARIFY = 구조 조건 없이 순수 용도·느낌만 묻는 질의 → 경로 CLARIFY(되묻기)
        (13.4 전까지는 doc_rag_node로 임시 실행, 기존 B와 동일 경험)
      · REJECT = 매물 무관(잡담·상식·금융/세금/보험 일반지식 등) → 가드(정중한 거절)
    """

    route: Literal["REJECT", "CLARIFY", "SQL", "HYBRID"]
    reason: str | None = None


class ConversationTurn(BaseModel):
    """멀티턴 맥락의 한 턴(FR18) — 클라이언트가 보관하다 후속 질의에 동봉한다.

    role/content만 둔 최소 스키마. content 길이를 막아 과대 입력(DoS)을 닫는다.
    role은 사용자/어시스턴트 둘로 한정(Literal) — 형식이탈을 422로 거른다.
    이 모델은 '서버 무상태' 입력 계약일 뿐, 서버·DB에 저장하지 않는다(요청 본문에서만 온다).
    """

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000, description="턴 내용")
    # 멀티턴 매물 참조(FR18 확장) — 어시스턴트 턴이 실제로 보여준 매물 id들. role="assistant"
    # 턴에만 의미가 있고(사용자 턴엔 없음), 에이전트가 "그중 N번째"·"그 5개 비교" 같은 후속
    # 요청을 새 검색이 아니라 이 id들로 직접 처리하는 데 쓴다(agent.py). max_length로 과대
    # 입력(DoS)을 막는다 — 한 턴에 보여줄 수 있는 매물 카드는 실제로도 20건을 넘지 않는다
    # (search_listings 상한과 동일선상, agent_tools.py _MAX_SEARCH_LIMIT).
    listing_ids: list[str] | None = Field(default=None, max_length=20, description="이 턴이 보여준 매물 id들(어시스턴트 턴 전용)")


class SearchRequest(BaseModel):
    # max_length로 과대 입력을 막고(4.3+ LLM 비용·DoS 방어), 공백만 있는 질의는 거른다.
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH, description="자연어 검색 질의")
    # 멀티턴 맥락(FR18) — 4.6에서 실제로 읽어 후속 질의를 맥락화한다(서버 무상태: 매 요청에 클라가 동봉).
    # 원소 타입(ConversationTurn)·최대 턴 수(12)를 강제해 4.5까지 무제한이던 DoS 여지를 닫는다.
    # 빈/누락(None·[])은 단일턴으로 정상 동작(회귀 0).
    context: list[ConversationTurn] | None = Field(
        default=None, max_length=12, description="직전 대화 맥락(클라이언트 보관, 최대 12턴)"
    )
    # 상세 페이지 "AI 시세 진단" 버튼이 프리필 질의와 함께 동봉하는 대상 매물 id(5단계).
    # 버튼 클릭이 아닌 일반 채팅 질의는 이 필드를 보내지 않는다(None) — 에이전트가 질의만으로
    # 대상 매물을 못 찾는 경우에만 필요한 보조 힌트라 optional·additive(기존 클라이언트 회귀 없음).
    listing_id: str | None = Field(default=None, description="시세 진단 대상 매물 id(선택)")

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, v: str) -> str:
        # "   "(공백·개행만) 같은 질의는 min_length=1을 통과하므로 별도로 막는다.
        if not v.strip():
            raise ValueError("query는 공백만으로 구성될 수 없습니다.")
        return v


class ListingCard(BaseModel):
    """매물 카드 — conventions.md §4 확정 계약. 증분 신규 7필드는 전부 nullable
    (값 채움은 후속 에픽: image_url·image_count=Epic 9, fuel·accident_status·is_single_owner·
    is_non_smoker=Epic 10(10.1), view_count=Epic 11)."""

    id: str
    manufacturer: str
    model: str
    year: int
    price: int       # 원(KRW)
    mileage: int     # km
    region: str
    fuel: str | None = None  # 연료(가솔린/디젤/하이브리드/전기/LPG) — Story 10.1, 대장 #67
    # ⚠️ image_url은 api가 **채우지 않는다** — api는 사진 URL을 만들지 않기 때문이다
    #    (conventions.md §10, ai_readonly 최소권한 CR2). 대신 아래 image_path(원본 경로)를
    #    보내고, URL 조립은 web·app이 각자 getPublicUrl로 한다. 이 불변식은
    #    tests/test_storage_signed_url_contract.py가 지킨다.
    image_url: str | None = None
    # 대표 사진의 **버킷 상대 경로**(`{user_id}/{listing_id}/{filename}`, 버킷명 미포함).
    # AI 응답 wire 전용 필드 — web은 이걸 공개 URL로 바꿔 image_url에 넣고 버린다(Story 9.6).
    image_path: str | None = None
    view_count: int | None = None
    image_count: int | None = None
    accident_status: Literal["무사고", "단순교환", "사고"] | None = None
    is_single_owner: bool | None = None
    is_non_smoker: bool | None = None
    options: list[str] | None = None  # 장비 통제어휘 배열(text[]) — Story 10.3, docs/conventions.md §11


class ClarifyPayload(BaseModel):
    """CLARIFY 경로(FR46)의 되묻기 페이로드 — 고정 질문 1개 + 고정 칩 배열.

    route=CLARIFY이고 되묻기 상한 이내일 때만 채워진다(clarify_node.py). 상한 초과 시
    서버가 doc_rag_node로 강제 폴백하며 이 필드는 None이 된다(칩 없음 = 더 안 묻는다는 신호).
    """

    question: str
    chips: list[str]


class SearchResponse(BaseModel):
    answer: str
    listings: list[ListingCard] = []
    # CLARIFY 되묻기 페이로드(FR46, CR5) — additive 필드라 기존 소비처 회귀 없음.
    clarify: ClarifyPayload | None = None
    # REJECT 전용 고정 상수 사유 술어 배열(FR47, CR4, Story 13.5) — additive, 기존 소비처 회귀 없음.
    # REJECT가 아닌 경로(SQL/HYBRID/CLARIFY)는 None.
    narrowed_by: list[str] | None = None
    # 에이전트 경로(route=AGENT, 4단계 부품 B) 전용 — market_price_stats 도구의 마지막 호출
    # 결과(app/market_price.diagnose()가 만든 dict 그대로)를 옵션 필드로 노출한다. 기존
    # run_search 경로는 이 값을 채우지 않으므로 항상 None(additive, 기존 클라이언트 회귀 없음).
    market_diagnosis: dict | None = None
    # 다건 시세 진단(2026-08-31, 사용자 승인 설계 변경) — 한 대화에서 market_price_stats가
    # 2건 이상 호출됐을 때 그 결과 전부(app/market_price.diagnose() dict 그대로, 상한 5건)를
    # 담는다. 1건이거나 호출이 없으면 None — 그 경우 웹은 기존 market_diagnosis(단건 차트)
    # 렌더를 그대로 쓴다(additive, 기존 소비처 회귀 없음).
    market_diagnoses: list[dict] | None = None


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
