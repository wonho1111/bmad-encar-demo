"""G2 커밋된 비교 근거(기준선 raw + 채점 리포트) 보호 — score_ab.py·run_phase_b.py 공용(DW-635).

run_phase_b.py는 이미 `_PROTECTED_BASELINES`로 자신이 만드는 raw 캡처 2개를 지켰지만,
쌍둥이 스크립트인 score_ab.py에는 같은 보호가 없었다 — `--out`을 커밋된 채점 리포트로
주면 47문항 기준 수치가 조용히 부분 캡처로 덮어써질 수 있었다(DW-635). 두 스크립트가
같은 목록을 참조하게 여기 한 곳으로 합친다(보호를 한쪽에만 넣는 공백 재발 방지).

DW-636이 지적한 `g2-exit-gate-2026-08-02.json`(13.8 AC2 증거, raw 캡처)도 이 목록에
포함한다 — 이전엔 `run_phase_b.py`의 보호 목록에 없어 재캡처 커맨드가 실수로 덮어쓸 수
있었다.

`g2-recapture-2026-08-03.json`·`g2-recapture-report.json`(13.9 AC 증거, 재기준선 판정
전 단계에서 만든 raw 캡처·리포트)도 같은 이유로 포함한다(코드리뷰 정정) — 13.8의
`g2-exit-gate-*` 선례와 동일하게, 스토리의 AC를 뒷받침하는 날짜형 커밋 증거 파일은
그 스토리가 끝난 뒤에도 실수로 덮어써지면 안 된다.

`g2-baseline-pre-13-9.json`(13.9 재기준선의 **before** 쪽 raw)도 같은 이유로 포함한다 —
이 파일이 없으면 `g2-recapture-report.json`이 기록한 "0.894 → 0.954" 방향을 리포지토리만
가지고는 다시 계산할 수 없다(원래는 세션 스크래치패드에만 있었다, 코드리뷰 P5).
"""

from __future__ import annotations

from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent

# 커밋된 G2 비교 근거 — raw 캡처(run_phase_b.py 산출) + 채점 리포트(score_ab.py 산출) 전부.
# 어느 스크립트든 `--out`으로 이 경로들을 가리키면 거부한다.
# ⚠️ 검사 지점은 스크립트마다 다르다(코드리뷰 정정 — 예전 주석은 "main()·capture() 양쪽"이라고
#   싸잡아 적어 실제보다 두터운 보호를 주장했다):
#     · run_phase_b.py — main()(argparse)과 capture()(실제로 파일을 쓰는 층) **양쪽**.
#     · score_ab.py    — main()(argparse) **한 곳뿐**. 리포트 쓰기 자체는 가드가 없으므로,
#                        main()을 거치지 않고 직접 호출하면 보호되지 않는다.
PROTECTED_BASELINES = frozenset(
    (_API_ROOT / "docs" / name).resolve()
    for name in (
        "g2-baseline.json",
        "g2-baseline-partial.json",
        "g2-baseline-report.json",
        "g2-baseline-pre-13-9.json",
        "g2-exit-gate-2026-08-02.json",
        "g2-exit-gate-report.json",
        "g2-recapture-2026-08-03.json",
        "g2-recapture-report.json",
    )
)


def is_protected(out_path) -> bool:
    """out_path가 보호 목록의 파일을 정확히 가리키면 True(resolve() 후 비교)."""
    return Path(out_path).resolve() in PROTECTED_BASELINES
