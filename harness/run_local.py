"""로컬 오케스트레이터 — dev 채점 + k-fold CV + baseline 진단.

현재 구현 범위(린 코어):
  기본 실행    : dev 120개 전체 채점 → overall, axes, focal 정확도
  --cv 5       : session 기준 5-fold 분할 → per-fold overall + 평균±표준편차 (fold 분산 = 노이즈 추정)
  --json PATH  : 상세 결과(overall·axes·per-task rows·CV) 저장
  --submission : screening 700개 → submission.csv (meta.seed=42)

포트폴리오 층(--ablate/--readiness/--segments/--ruleset)은 아직 미구현(DEFERRED).
규칙 풀이 생기고 baseline 숫자가 정당화할 때 붙인다. (OVERVIEW/스킬 설계 참조)
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from harness import FinalHarness
from scpc_core import (
    load_json,
    load_jsonl,
    run_harness,
    score_dev_submission,
    validate_payload,
    write_submission_csv,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRACK_DIR = ROOT / "improvement"
N_FOLDS = 5


def _session_of(tasks: list[dict]) -> dict[str, str]:
    return {str(t["id"]): str(t.get("session_id", "")) for t in tasks}


def _fold_assignment(tasks: list[dict], k: int) -> dict[str, int]:
    """session_id를 정렬 후 결정적으로 k개 fold에 배정 (재현 가능)."""
    sessions = sorted({str(t.get("session_id", "")) for t in tasks})
    session_fold = {sid: i % k for i, sid in enumerate(sessions)}
    sof = _session_of(tasks)
    return {tid: session_fold[sid] for tid, sid in sof.items()}


def evaluate(dev_tasks: list[dict], dev_answers: dict, k: int) -> dict:
    payload = run_harness(dev_tasks, FinalHarness, harness_name="baseline_extracted")
    report = score_dev_submission(payload, dev_answers)
    rows = report["rows"]

    # k-fold: 각 fold를 held-out으로 보고 그 fold task들의 평균 점수
    task_fold = _fold_assignment(dev_tasks, k)
    fold_scores: dict[int, list[float]] = {i: [] for i in range(k)}
    for r in rows:
        f = task_fold.get(r["task_id"])
        if f is not None:
            fold_scores[f].append(r["score"])
    per_fold = {i: (sum(v) / len(v) if v else 0.0) for i, v in fold_scores.items()}
    fold_vals = [per_fold[i] for i in range(k)]
    cv_mean = statistics.mean(fold_vals)
    cv_std = statistics.pstdev(fold_vals)

    return {
        "overall": report["overall"],
        "n": report["n"],
        "axes": report["axes"],
        "cv": {
            "k": k,
            "per_fold_overall": {str(i): round(per_fold[i], 4) for i in range(k)},
            "fold_sizes": {str(i): len(fold_scores[i]) for i in range(k)},
            "cv_mean": round(cv_mean, 4),
            "cv_std": round(cv_std, 4),
        },
        "rows": rows,
    }


def print_summary(result: dict) -> None:
    ax = result["axes"]
    cv = result["cv"]
    print("=" * 56)
    print(f"  BASELINE  (dev n={result['n']})")
    print("=" * 56)
    print(f"  overall (전체)      : {result['overall']:.4f}")
    print(f"  CV 일반화 평균±표준  : {cv['cv_mean']:.4f} ± {cv['cv_std']:.4f}  (k={cv['k']})")
    print(f"  per-fold overall    : " + ", ".join(f"{v:.3f}" for v in cv['per_fold_overall'].values()))
    print(f"  fold sizes          : " + ", ".join(str(v) for v in cv['fold_sizes'].values()))
    print("-" * 56)
    print("  축별 평균 (가중치):")
    w = {"focal": .18, "target": .12, "control": .18, "content_scope": .17, "policy": .13, "plan": .18}
    for name in ["focal", "target", "control", "content_scope", "policy", "plan"]:
        print(f"    {name:16s}: {ax[name]:.4f}   (w={w[name]})")
    print("-" * 56)
    print(f"  focal 정확도        : {ax['focal']*100:.1f}%  (focal_id 정답 일치 비율)")
    print("=" * 56)


def make_submission(k: int) -> None:
    screening = load_jsonl(DATA_DIR / "screening_tasks.jsonl")
    payload = run_harness(screening, FinalHarness, harness_name="baseline_extracted")
    validate_payload(payload, {str(t["id"]) for t in screening})
    out = ROOT / "submission.csv"
    write_submission_csv(payload, out)
    print(f"wrote: {out}  (answers={len(payload['answers'])}, seed={payload['meta']['seed']})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", type=int, default=N_FOLDS)
    ap.add_argument("--json", dest="json_path", default=None)
    ap.add_argument("--submission", action="store_true")
    # DEFERRED (미구현) — 존재만 표시
    for flag in ("--ablate", "--readiness", "--segments"):
        ap.add_argument(flag, action="store_true")
    ap.add_argument("--ruleset", default=None)
    args = ap.parse_args()

    if args.ablate or args.readiness or args.segments or args.ruleset:
        raise SystemExit("포트폴리오 층(--ablate/--readiness/--segments/--ruleset)은 아직 DEFERRED입니다. baseline 검증 후 활성화하세요.")

    if args.submission:
        make_submission(args.cv)
        return

    dev_tasks = load_jsonl(DATA_DIR / "dev_tasks.jsonl")
    dev_answers = load_json(DATA_DIR / "dev_answers.json")
    result = evaluate(dev_tasks, dev_answers, args.cv)
    print_summary(result)

    if args.json_path:
        Path(args.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved: {args.json_path}")


if __name__ == "__main__":
    main()
