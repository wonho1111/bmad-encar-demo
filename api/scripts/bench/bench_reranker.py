"""
리랭커(크로스인코더) 2종 CPU 실측 스크립트.
- BAAI/bge-reranker-v2-m3
- dragonkue/bge-reranker-v2-m3-ko
측정: 로드시간/RSS, 지연(질의1 x 후보10, 5회), 품질(8질의 x 코퍼스 전체 섹션 1등 제목)
결과는 JSON으로 bench/results_reranker.json 에 저장. 실패해도 계속 진행(모델별 try/except).
"""
import glob
import json
import os
import re
import sys
import time
import traceback

import psutil

CORPUS_DIR = r"C:\Users\dnjsg\workspace\bmad-encar-demo\api\corpus"
OUT_PATH = os.path.join(os.path.dirname(__file__), "results_reranker.json")

MODELS = [
    "BAAI/bge-reranker-v2-m3",
    "dragonkue/bge-reranker-v2-m3-ko",
]

QUERIES = [
    ("초보운전자에게 좋은 차", "초보 운전자 첫차"),
    ("캠핑 다니기 좋은 차", "캠핑·차박"),
    ("겨울 눈길에 안전한 차", "겨울철·눈길"),
    ("가성비 좋은 중고차", "가성비 번역"),
    ("2천만원대에 살 만한 차", "예산대별"),
    ("연비 좋은 차", "연료별/주행패턴"),
    ("잔고장 적고 수리비 덜 나오는 차", "신뢰성 체크포인트"),
    ("세단이랑 SUV 중 뭐가 나아", "차종/차형 관련"),
]


def load_sections():
    sections = []  # list of (title, full_text)
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # split on '## ' headers (level-2). Keep title + body text.
        parts = re.split(r"(?m)^##\s+(.+)$", text)
        # parts[0] is preamble before first ##; then alternating title, body
        for i in range(1, len(parts), 2):
            title = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            sections.append({
                "file": os.path.basename(path),
                "title": title,
                "text": f"{title}\n{body}",
            })
    return sections


def rss_mb():
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def bench_one_model(model_name, sections):
    result = {"model": model_name}
    try:
        from sentence_transformers import CrossEncoder
    except Exception as e:
        result["error_stage"] = "import sentence_transformers"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()
        return result

    rss_before = rss_mb()
    t0 = time.time()
    try:
        model = CrossEncoder(model_name, device="cpu")
    except Exception as e:
        result["error_stage"] = "load model"
        result["error"] = repr(e)
        result["traceback"] = traceback.format_exc()
        return result
    load_time = time.time() - t0
    rss_after_load = rss_mb()

    result["load_time_sec"] = round(load_time, 3)
    result["rss_before_mb"] = round(rss_before, 1)
    result["rss_after_load_mb"] = round(rss_after_load, 1)

    # 지연 측정: 질의1개 x 후보 10개, 5회 반복
    try:
        query = QUERIES[0][0]
        candidates = [s["text"][:500] for s in sections[:10]]
        pairs = [[query, c] for c in candidates]
        latencies_ms = []
        for _ in range(5):
            t0 = time.time()
            model.predict(pairs)
            latencies_ms.append((time.time() - t0) * 1000)
        result["latency_ms"] = {
            "runs": [round(x, 2) for x in latencies_ms],
            "avg": round(sum(latencies_ms) / len(latencies_ms), 2),
            "max": round(max(latencies_ms), 2),
        }
    except Exception as e:
        result["latency_error"] = repr(e)
        result["latency_traceback"] = traceback.format_exc()

    # 품질: 8개 질의 x 전체 섹션(약 32개) 스코어링, 1등 섹션 제목
    try:
        quality = []
        all_texts = [s["text"] for s in sections]
        for q, expect in QUERIES:
            pairs = [[q, t] for t in all_texts]
            scores = model.predict(pairs)
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            quality.append({
                "query": q,
                "expected_hint": expect,
                "top1_title": sections[best_idx]["title"],
                "top1_file": sections[best_idx]["file"],
                "top1_score": float(scores[best_idx]),
            })
        result["quality"] = quality
        result["num_sections"] = len(sections)
    except Exception as e:
        result["quality_error"] = repr(e)
        result["quality_traceback"] = traceback.format_exc()

    result["rss_peak_mb"] = round(rss_mb(), 1)

    # 모델 언로드해서 다음 모델 측정에 영향 최소화
    del model
    import gc
    gc.collect()

    return result


def main():
    sections = load_sections()
    print(f"[info] loaded {len(sections)} sections from corpus", file=sys.stderr)

    all_results = {
        "num_sections": len(sections),
        "section_titles": [s["title"] for s in sections],
        "models": [],
    }

    for model_name in MODELS:
        print(f"[info] benchmarking {model_name} ...", file=sys.stderr)
        try:
            res = bench_one_model(model_name, sections)
        except Exception as e:
            res = {
                "model": model_name,
                "error_stage": "unexpected top-level failure",
                "error": repr(e),
                "traceback": traceback.format_exc(),
            }
        all_results["models"].append(res)
        # 중간 저장 (크래시 대비)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"[info] done {model_name}, saved interim results", file=sys.stderr)

    print(f"[info] all done, results at {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
