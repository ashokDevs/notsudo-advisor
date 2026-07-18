from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger

logger = get_logger(__name__)


async def run_eval() -> None:
    eval_file = Path(__file__).parent / "ground_truth.jsonl"
    if not eval_file.exists():
        print(f"Error: {eval_file} not found.")
        return

    from core.analysis.pipeline import analyze_advisory_against_repo

    results: list[dict[str, Any]] = []
    demo = Path(__file__).resolve().parents[1] / "demo_app"

    with open(eval_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            advisory_id = case["advisory_id"]
            expected = case["expected_verdict"]
            repo_path = case.get("repo_path") or str(demo)
            package = case.get("package_name")

            print(f"Running eval for {advisory_id}...")
            try:
                final = await analyze_advisory_against_repo(
                    advisory_id,
                    repo_path,
                    package_name=package,
                    run_preflight=False,
                )
                verdict = final.get("verdict")
                actual = True if verdict == "exposed" else False if verdict == "safe" else None
                # Map unsure: treat as incorrect vs boolean ground truth unless expected is null
                if actual is None:
                    correct = False
                else:
                    correct = expected == actual
                results.append(
                    {
                        "advisory_id": advisory_id,
                        "expected": expected,
                        "actual": actual,
                        "verdict": verdict,
                        "correct": correct,
                        "reasoning": (final.get("reasoning") or "")[:200],
                    }
                )
            except Exception as e:
                print(f"Error running case {advisory_id}: {e}")
                results.append(
                    {
                        "advisory_id": advisory_id,
                        "expected": expected,
                        "actual": None,
                        "verdict": None,
                        "correct": False,
                        "reasoning": str(e),
                    }
                )

    tp = sum(1 for r in results if r["expected"] is True and r["actual"] is True)
    fp = sum(1 for r in results if r["expected"] is False and r["actual"] is True)
    fn = sum(1 for r in results if r["expected"] is True and r["actual"] is False)
    tn = sum(1 for r in results if r["expected"] is False and r["actual"] is False)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    n = len(results)
    # Wilson-ish rough bootstrap stand-in: ±1.96 * sqrt(p(1-p)/n) on accuracy
    acc = sum(1 for r in results if r["correct"]) / n if n else 0.0
    se = math.sqrt(acc * (1 - acc) / n) if n else 0.0
    ci_low = max(0.0, acc - 1.96 * se)
    ci_high = min(1.0, acc + 1.96 * se)

    print("\n--- Eval Results ---")
    print(f"Total Cases:     {n}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Negatives:  {tn}")
    print(f"Precision:       {precision:.2f}")
    print(f"Recall:          {recall:.2f}")
    print(f"F1 Score:        {f1:.2f}")
    print(f"Accuracy:        {acc:.2f} [{ci_low:.2f}, {ci_high:.2f}]")
    for r in results:
        mark = "OK" if r["correct"] else "MISS"
        print(f"  [{mark}] {r['advisory_id']}: expected={r['expected']} got={r['verdict']}")


if __name__ == "__main__":
    asyncio.run(run_eval())
