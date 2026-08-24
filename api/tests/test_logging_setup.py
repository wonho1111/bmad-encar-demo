"""로깅 설정(DW-659)이 실제로 INFO를 출력하는지 확인한다.

배경: `logging.basicConfig`가 어디에도 없어 루트 로거가 파이썬 기본값 WARNING(30)에
머물렀고, 그래프 노드들의 `logger.info`(라우팅 결정·생성 SQL 등, app/graph/*.py)가 전부
소리 없이 버려졌다(app/main.py 부재 확인, deferred-work DW-659). 이 파일은 "설정만 하고
끝내지 말 것"(B9) 요구에 맞춰 그 처방이 실제로 작동하는지 결정론으로 본다.

⚠️ 이 검사가 **안 보는 것**(추측 아니라 실측):
  · uvicorn으로 실제 기동했을 때 콘솔에 정말 찍히는 모습 자체는 보지 않는다 — 스토리 검증
    섹션에서 `bash scripts/dev-api.sh`로 직접 띄워 눈으로 확인한다(이 파일은 그 대체가 아니다).
  · "표준출력으로 나가는 핸들러가 있다"는 핸들러 **타입**(FileHandler가 아닌 순수
    StreamHandler)으로만 구조를 확인한다. `capsys`로 실제 문자열을 캡처해 검증하지 않는
    이유: 이 핸들러는 `app.main` 모듈이 처음 import될 때(대개 다른 테스트 파일이 먼저
    `from app.main import app`을 실행하는 시점) 그 순간의 `sys.stdout` 참조를 붙잡는데,
    pytest의 `capsys`는 **테스트마다** stdout을 새로 감싸므로 이미 붙잡힌 참조로는 나중
    캡처가 안 걸릴 수 있다(테스트 실행 순서에 따라 통과/실패가 갈리는 비결정 위험). 그래서
    "표준출력에 실제로 보이는지"는 핸들러 구조 확인 + 스토리 검증 섹션의 수동 확인으로
    나눠 본다.
  · 회전(rotation) 자체(파일이 maxBytes를 넘으면 실제로 잘리는지)는 보지 않는다 — 설정값
    (`RotatingFileHandler(maxBytes=..., backupCount=...)`)만 존재하고, 그 값을 실제로
    넘겨서 회전이 도는지는 이 스토리 범위 밖(상식적인 값을 넣었다는 선언 수준).
"""

import logging
import uuid

import app.main as main_module


def test_루트_로거_레벨이_INFO_이하다():
    """LOG_LEVEL 미설정 시 기본값이 INFO여야 logger.info가 버려지지 않는다."""
    assert logging.getLogger().getEffectiveLevel() <= logging.INFO


def test_표준출력용_스트림_핸들러가_루트에_달려있다():
    """파일 핸들러(RotatingFileHandler도 StreamHandler의 하위클래스)와 구분해서, 콘솔로
    나가는 순수 StreamHandler가 따로 존재하는지만 구조로 확인한다."""
    handlers = logging.getLogger().handlers
    assert any(type(h) is logging.StreamHandler for h in handlers), [
        type(h).__name__ for h in handlers
    ]


def test_INFO_로그_한줄이_실제로_로그파일에_남는다():
    """graph 노드들이 쓰는 것과 같은 패턴(logger.info)으로 찍은 한 줄이 .logs/api.log에
    실제로 기록되는지 본다 — '설정이 있다'가 아니라 '작동한다'를 확인(B4)."""
    marker = f"로그기록확인-{uuid.uuid4().hex}"
    probe = logging.getLogger("app.graph.test_probe")
    probe.info("검증용 마커: %s", marker)
    for h in logging.getLogger().handlers:
        h.flush()

    content = main_module.LOG_FILE.read_text(encoding="utf-8")
    assert marker in content


def test_WARNING_미만은_기본적으로_로그파일에_안_남긴다():
    """레벨 필터가 실제로 거른다는 대조군 — DEBUG 로그는 기본(INFO) 설정에서 안 보여야
    '아무거나 다 찍힌다'가 아니라 레벨이 실제로 작동함을 보인다."""
    marker = f"디버그마커-{uuid.uuid4().hex}"
    probe = logging.getLogger("app.graph.test_probe")
    probe.debug("이건 안 보여야 함: %s", marker)
    for h in logging.getLogger().handlers:
        h.flush()

    content = main_module.LOG_FILE.read_text(encoding="utf-8")
    assert marker not in content
