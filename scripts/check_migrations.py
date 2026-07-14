#!/usr/bin/env python3
"""마이그레이션 순서 게이트 — supabase/migrations/의 정적·동적 self-containment 검사.

Story 8.6 Task 3. Python 표준 라이브러리만 사용(신규 의존성 0개).

정적 검사(도커 없이도 도는 층):
  ① 파일명 규약 `^\\d{4}[a-z]?_[a-z0-9_]+\\.sql$`
  ② 번호 밀집(정본 파일 0001~max, 공백 없음)
  ③ 바닥번호+접미사 조합 중복 없음
  ④ 접미사 파일은 같은 바닥번호의 정본 파일이 선행 존재

동적 검사(도커 필요): pgvector/pgvector:pg17 빈 컨테이너에 프렐류드 →
  파일명 정렬 순서(번호순, 접미사는 알파벳순)로 전량 적용 → self-containment 프로브 3건.

종료코드: 통과 0 / 위반 1. 도커 없으면 정적 층만 돌고 "동적 검사 건너뜀"을 출력하며 실패 처리
(조용한 통과 금지).
"""

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"
PRELUDE_FILE = REPO_ROOT / "scripts" / "migration-check-prelude.sql"

DOCKER_IMAGE = "pgvector/pgvector:pg17"
CONTAINER_NAME_PREFIX = "migration-gate-check"

FILENAME_RE = re.compile(r"^(\d{4})([a-z]?)_([a-z0-9_]+)\.sql$")

PG_ISREADY_TIMEOUT_SECONDS = 30
PG_ISREADY_POLL_INTERVAL_SECONDS = 1

# self-containment 프로브 3건 — 서로 다른 축(컬럼 GRANT·컬럼 차단·RLS 정책)을 증인한다.
# ⚠️ has_table_privilege는 쓰지 않는다 — 0011이 테이블 SELECT를 회수하고 컬럼 스코프로만
#    재부여했으므로 false가 정답이라 가짜 red가 난다.
# ⚠️ ③은 GRANT 프로브가 아니라 pg_policies 프로브다 — 0006의 스키마 전체 GRANT가 가려버려
#    항상 true가 뜨는 함정(GRANT만으론 행이 안 보인다 — 정책 필수)을 피하기 위함이다.
PROBES = [
    (
        "① 컬럼 GRANT 축: anon이 listings 일부 컬럼을 읽을 수 있다",
        "select has_any_column_privilege('anon', 'public.listings', 'select');",
        "t",
    ),
    (
        "② 컬럼 차단 축: anon이 listings.embedding은 못 읽는다",
        "select has_column_privilege('anon', 'public.listings', 'embedding', 'select');",
        "f",
    ),
    (
        "③ RLS 정책 축: guide_documents_ai_readonly_select 정책이 존재한다",
        "select exists (select 1 from pg_policies where policyname = 'guide_documents_ai_readonly_select');",
        "t",
    ),
]


class ParsedFile:
    def __init__(self, path):
        self.path = path
        self.name = path.name
        match = FILENAME_RE.match(self.name)
        self.valid = match is not None
        if match:
            self.base = int(match.group(1))
            self.suffix = match.group(2)
        else:
            self.base = None
            self.suffix = None

    @property
    def sort_key(self):
        # 번호순, 접미사는 알파벳순('' < 'b' < 'c' ...) — 파일명 정렬 순서와 동일하다.
        return (self.base, self.suffix)


def load_sql_files():
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [ParsedFile(p) for p in files]


def run_static_checks(files):
    """정적 검사 4종을 돌려 위반 메시지 리스트를 반환한다. 비어 있으면 통과."""
    violations = []

    invalid = [f for f in files if not f.valid]
    for f in invalid:
        violations.append(f"[파일명 규약 위반] {f.name} — `NNNN[a-z]?_이름.sql` 형식이 아니다")

    valid_files = [f for f in files if f.valid]

    # ② 번호 밀집 — 정본(접미사 없음) 파일만 대상
    primary_bases = sorted({f.base for f in valid_files if f.suffix == ""})
    if primary_bases:
        max_base = primary_bases[-1]
        expected = set(range(1, max_base + 1))
        missing = sorted(expected - set(primary_bases))
        for m in missing:
            violations.append(f"[번호 공백] {m:04d}_*.sql 이 없다 — 정본 마이그 번호는 0001~{max_base:04d}까지 빈틈없이 밀집해야 한다")

    # ③ 바닥번호+접미사 조합 중복 없음
    seen = {}
    for f in valid_files:
        key = (f.base, f.suffix)
        seen.setdefault(key, []).append(f.name)
    for key, names in seen.items():
        if len(names) > 1:
            base, suffix = key
            label = f"{base:04d}{suffix}"
            violations.append(f"[번호 중복] {label}_* 파일이 {len(names)}개다: {', '.join(names)}")

    # ④ 접미사 파일은 같은 바닥번호의 정본 파일이 선행 존재
    primary_base_set = set(primary_bases)
    for f in valid_files:
        if f.suffix != "" and f.base not in primary_base_set:
            violations.append(f"[선행 정본 없음] {f.name} — 바닥번호 {f.base:04d}의 정본(접미사 없는) 파일이 없다")

    return violations


def docker_available():
    return shutil.which("docker") is not None


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kwargs)


def psql_apply_file(container_name, sql_path):
    """파일 하나를 --single-transaction + ON_ERROR_STOP=1로 적용. (성공여부, stdout+stderr) 반환."""
    content = sql_path.read_text(encoding="utf-8")
    result = run(
        [
            "docker", "exec", "-i", container_name,
            "psql", "-U", "postgres", "-v", "ON_ERROR_STOP=1", "--single-transaction",
            "-f", "-",
        ],
        input=content,
    )
    ok = result.returncode == 0
    output = (result.stdout or "") + (result.stderr or "")
    return ok, output


def wait_pg_ready(container_name):
    deadline = time.time() + PG_ISREADY_TIMEOUT_SECONDS
    while time.time() < deadline:
        result = run(["docker", "exec", container_name, "pg_isready", "-U", "postgres"])
        if result.returncode == 0:
            return True
        time.sleep(PG_ISREADY_POLL_INTERVAL_SECONDS)
    return False


def run_dynamic_checks(files):
    """도커 컨테이너에 프렐류드+전체 마이그를 번호순 적용하고 프로브 3건을 확인한다.
    (통과여부, 상세 로그 라인 리스트) 반환."""
    log = []
    container_name = f"{CONTAINER_NAME_PREFIX}-{__import__('os').getpid()}"

    pull = run(["docker", "pull", DOCKER_IMAGE])
    if pull.returncode != 0:
        log.append(f"[FAIL] docker pull {DOCKER_IMAGE} 실패:\n{pull.stderr}")
        return False, log

    started = run([
        "docker", "run", "-d", "--name", container_name,
        "-e", "POSTGRES_PASSWORD=postgres",
        DOCKER_IMAGE,
    ])
    if started.returncode != 0:
        log.append(f"[FAIL] 컨테이너 기동 실패:\n{started.stderr}")
        return False, log

    try:
        if not wait_pg_ready(container_name):
            log.append(f"[FAIL] {PG_ISREADY_TIMEOUT_SECONDS}초 내 pg_isready 응답 없음")
            return False, log

        prelude_ok, prelude_out = psql_apply_file(container_name, PRELUDE_FILE)
        if not prelude_ok:
            log.append(f"[FAIL] 프렐류드 적용 실패:\n{prelude_out}")
            return False, log
        log.append(f"[OK] 프렐류드 적용 성공")

        valid_files = [f for f in files if f.valid]
        ordered = sorted(valid_files, key=lambda f: f.sort_key)

        for f in ordered:
            ok, out = psql_apply_file(container_name, f.path)
            if not ok:
                log.append(f"[FAIL] {f.name} : \n{out.strip()}")
                return False, log
            log.append(f"[OK] {f.name} 적용 성공")

        all_probes_ok = True
        for label, query, expected in PROBES:
            result = run([
                "docker", "exec", container_name,
                "psql", "-U", "postgres", "-tAc", query,
            ])
            actual = (result.stdout or "").strip()
            if result.returncode != 0 or actual != expected:
                all_probes_ok = False
                log.append(
                    f"[FAIL] 프로브 {label} — 기대값 '{expected}', 실제값 '{actual}'"
                    f"{': ' + result.stderr.strip() if result.stderr else ''}"
                )
            else:
                log.append(f"[OK] 프로브 {label} — '{actual}' 확인")

        return all_probes_ok, log
    finally:
        run(["docker", "rm", "-f", container_name])


def main():
    if not MIGRATIONS_DIR.exists():
        print(f"❌ 마이그레이션 디렉터리 없음: {MIGRATIONS_DIR}")
        return 1

    files = load_sql_files()
    print(f"── 정적 검사 ({len(files)}개 파일) ──")
    static_violations = run_static_checks(files)

    if static_violations:
        for v in static_violations:
            print(f"❌ {v}")
        print(f"\n정적 검사 실패: {len(static_violations)}건 위반")
        return 1

    print("✅ 정적 검사 통과")

    if not docker_available():
        print("\n⚠️ Docker를 찾을 수 없다 — 동적 검사를 건너뛴다.")
        print("❌ 정적 검사만으로는 게이트 통과로 인정하지 않는다 — 실패 처리")
        return 1

    print(f"\n── 동적 검사 ({DOCKER_IMAGE}) ──")
    dynamic_ok, log = run_dynamic_checks(files)
    for line in log:
        print(line)

    if not dynamic_ok:
        print("\n동적 검사 실패")
        return 1

    print("\n✅ 동적 검사 통과")
    print("\n=== 마이그레이션 게이트 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
