import asyncio
import json
from pathlib import Path
from typing import Any

from core.orchestration.graph import build_graph
from core.orchestration.state import AgentState
from core.observability.logging import get_logger

logger = get_logger(__name__)

async def run_eval() -> None:
    eval_file = Path(__file__).parent / "ground_truth.jsonl"
    if not eval_file.exists():
        print(f"Error: {eval_file} not found.")
        return

    graph = build_graph()
    results = []

    with open(eval_file, "r") as f:
        for line in f:
            case = json.loads(line)
            advisory_id = case["advisory_id"]
            repo_id = case["repo_id"]
            expected = case["expected_verdict"]

            print(f"Running eval for {advisory_id} on {repo_id}...")
            
            state: AgentState = {
                "advisory_id": advisory_id,
                "repo_id": repo_id,
                "commit_sha": "eval-run",
                "package_name": None,
                "vulnerable_ranges": [],
                "vulnerable_symbols": ["template"], # simplified
                "is_exposed": None,
                "reachability_reasoning": None,
                "retrieved_context": [],
                "retrieval_iterations": 0,
                "pr_draft": None
            }

            try:
                final_state = await graph.ainvoke(state)
                actual = final_state.get("is_exposed", False)
                
                results.append({
                    "advisory_id": advisory_id,
                    "expected": expected,
                    "actual": actual,
                    "correct": expected == actual
                })
            except Exception as e:
                print(f"Error running case {advisory_id}: {e}")
                results.append({
                    "advisory_id": advisory_id,
                    "expected": expected,
                    "actual": None,
                    "correct": False
                })

    # Calculate metrics
    tp = sum(1 for r in results if r["expected"] is True and r["actual"] is True)
    fp = sum(1 for r in results if r["expected"] is False and r["actual"] is True)
    fn = sum(1 for r in results if r["expected"] is True and r["actual"] is False)
    tn = sum(1 for r in results if r["expected"] is False and r["actual"] is False)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n--- Eval Results ---")
    print(f"Total Cases: {len(results)}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Negatives:  {tn}")
    print(f"Precision:       {precision:.2f}")
    print(f"Recall:          {recall:.2f}")
    print(f"F1 Score:        {f1:.2f}")

if __name__ == "__main__":
    asyncio.run(run_eval())
