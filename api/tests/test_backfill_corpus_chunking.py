"""backfill_embeddings.load_corpus() 청킹 단위 테스트 — 네트워크(임베딩)·DB 무관.

문서 단위 1건 적재에서 '## ' 섹션 단위 청킹으로 바꾼 뒤(RAG 코퍼스 청킹), load_corpus()가
실제로 파일을 여러 건으로 쪼개는지만 검증한다. 임시 디렉터리에 md 파일을 직접 만들어
corpus_dir을 monkeypatch하는 방식 — 레포 corpus/*.md 내용에 의존하지 않는다.
"""

import importlib.util
from pathlib import Path

# scripts/backfill_embeddings.py를 모듈로 직접 로드(scripts는 패키지가 아니므로,
# tests/test_ab_scoring.py와 동일한 관행).
_SPEC = importlib.util.spec_from_file_location(
    "backfill_embeddings",
    Path(__file__).resolve().parent.parent / "scripts" / "backfill_embeddings.py",
)
backfill_embeddings = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(backfill_embeddings)


def _write(tmp_path: Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text, encoding="utf-8")


def test_intro_before_first_heading_kept_as_own_chunk(tmp_path, monkeypatch):
    """서두 문단(첫 '## ' 이전)이 비어 있지 않으면 문서제목으로 별도 1건이 된다."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write(
        corpus_dir,
        "01-test.md",
        "# 문서제목\n\n서두 문단 내용.\n\n## 섹션1\n\n섹션1 본문.\n",
    )
    # load_corpus()는 API_ROOT/corpus를 고정 참조하므로 API_ROOT 자체를 바꿔치기한다.
    monkeypatch.setattr(backfill_embeddings, "API_ROOT", tmp_path)
    docs = backfill_embeddings.load_corpus()

    assert docs[0] == ("문서제목", "서두 문단 내용.")
    assert docs[1] == ("문서제목 — 섹션1", "섹션1 본문.")
    assert len(docs) == 2


def test_no_intro_only_sections(tmp_path, monkeypatch):
    """서두 없이 바로 '## '로 시작하면 서두 청크 없이 섹션들만 생긴다."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write(
        corpus_dir,
        "01-test.md",
        "# 문서제목\n\n## 섹션1\n\n섹션1 본문.\n\n## 섹션2\n\n섹션2 본문.\n",
    )
    monkeypatch.setattr(backfill_embeddings, "API_ROOT", tmp_path)
    docs = backfill_embeddings.load_corpus()

    assert docs == [
        ("문서제목 — 섹션1", "섹션1 본문."),
        ("문서제목 — 섹션2", "섹션2 본문."),
    ]


def test_file_without_headings_stays_single_chunk(tmp_path, monkeypatch):
    """'## '가 하나도 없는 파일은 기존과 동일하게 문서 전체가 1건."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write(corpus_dir, "01-test.md", "# 문서제목\n\n헤딩 없는 본문 전체.\n")
    monkeypatch.setattr(backfill_embeddings, "API_ROOT", tmp_path)
    docs = backfill_embeddings.load_corpus()

    assert docs == [("문서제목", "헤딩 없는 본문 전체.")]


def test_blank_section_is_skipped(tmp_path, monkeypatch, capsys):
    """본문이 공백뿐인 섹션은 건너뛰고 그 사실을 print한다."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _write(
        corpus_dir,
        "01-test.md",
        "# 문서제목\n\n## 빈섹션\n\n   \n\n## 섹션2\n\n섹션2 본문.\n",
    )
    monkeypatch.setattr(backfill_embeddings, "API_ROOT", tmp_path)
    docs = backfill_embeddings.load_corpus()

    assert docs == [("문서제목 — 섹션2", "섹션2 본문.")]
    captured = capsys.readouterr()
    assert "빈섹션" in captured.out
