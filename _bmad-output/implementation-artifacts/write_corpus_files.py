# -*- coding: utf-8 -*-
"""seed-expansion-guides.json → api/corpus/*.md 단일출처 파일로 기록.
- replace 2건: 기존 02/03 파일을 보강 내용으로 덮어씀(첫 줄 '# 제목'은 기존 title 유지).
- new 6건: 07~12 새 파일 생성.
backfill_guides()가 corpus/*.md 전체를 다시 읽어 임베딩하므로, 여기 쓰면 DB에 반영된다.
"""
import json, io, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).parent
CORPUS = HERE.parent.parent / "api" / "corpus"

guides = json.load(open(HERE/"seed-expansion-guides.json", encoding="utf-8"))

# 보강(replace) 제목 → 기존 파일명 매핑
REPLACE_FILE = {
    "패밀리카로 무난한 차종 고르기": "02-패밀리카-적합-차종.md",
    "초보 운전자에게 적합한 차종":   "03-초보운전자-적합-차종.md",
}
# 신규(new) 제목 → 새 파일명 (순서 07~12)
NEW_FILE = {
    "전기차 충전·보조금·주행거리 이해": "07-전기차-충전-보조금.md",
    "할부·리스·현금 구매 방식 비교":   "08-할부-리스-현금-비교.md",
    "자동차 보험과 세금 기초":         "09-보험-세금-기초.md",
    "사고이력·침수차·주행거리 조작 판별법": "10-사고이력-침수-판별.md",
    "적정 주행거리와 연식 판단 기준":  "11-주행거리-연식-판단.md",
    "옵션의 가치 판단":               "12-옵션-가치-판단.md",
}

written = []
for g in guides:
    title, content, mode = g["title"], g["content"], g["mode"]
    if mode == "replace":
        fname = REPLACE_FILE.get(title)
    else:
        fname = NEW_FILE.get(title)
    if not fname:
        print(f"⚠️  매핑 없음(건너뜀): {mode} / {title!r}")
        continue
    path = CORPUS / fname
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    written.append((mode, fname, len(content)))

print(f"✅ corpus 파일 {len(written)}개 기록 → {CORPUS}")
for mode, fname, n in written:
    print(f"   [{mode:7}] {fname}  ({n}자)")
print(f"\n총 corpus *.md: {len(list(CORPUS.glob('*.md')))}개")
