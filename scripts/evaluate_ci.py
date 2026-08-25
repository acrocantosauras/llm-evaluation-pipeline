#!/usr/bin/env python3
"""CI evaluation quality gate script.

Runs the evaluation pipeline on a safe synthetic dataset and compares results
against configured quality thresholds. Exits non-zero if the gate fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    """Run evaluation quality gate. Returns 0 on PASS, 1 on FAIL."""
    from evaluator.base import EvaluationSample
    from evaluator.registry import evaluate_with_profile

    # Load CI evaluation dataset
    dataset_path = Path(__file__).resolve().parent.parent / "examples" / "ci_evaluation_dataset.json"
    if not dataset_path.exists():
        print(f"ERROR: CI dataset not found: {dataset_path}")
        return 1

    with open(dataset_path) as f:
        dataset = json.load(f)

    items = dataset.get("items", [])
    profile = dataset.get("profile", "basic")
    thresholds = dataset.get("quality_thresholds", {})

    print(f"Running CI evaluation: profile={profile}, items={len(items)}")
    print(f"Thresholds: {json.dumps(thresholds, indent=2)}")
    print("-" * 60)

    all_passed = True
    results_summary = []

    for i, item in enumerate(items):
        raw_sample = item.get("sample", item)
        sample_name = item.get("name", f"Item {i + 1}")

        # Convert to EvaluationSample dataclass
        ctx = raw_sample.get("context", [])
        if ctx and isinstance(ctx[0], str):
            ctx = [{"text": t} for t in ctx]

        sample = EvaluationSample(
            question=raw_sample.get("question", ""),
            answer=raw_sample.get("answer", ""),
            context=ctx,
            reference_answer=raw_sample.get("reference_answer", ""),
            conversation={
                "model_response": raw_sample.get("answer", ""),
                "input_tokens": raw_sample.get("input_tokens", 100),
                "output_tokens": raw_sample.get("output_tokens", 200),
            },
        )

        try:
            metric_results = evaluate_with_profile(profile, sample)
        except Exception as e:
            print(f"  FAIL [{sample_name}]: Evaluation error: {e}")
            all_passed = False
            continue

        # Build a lookup dict from MetricResult dataclass list
        metrics_by_name = {}
        for mr in metric_results:
            if hasattr(mr, "metric"):
                metrics_by_name[mr.metric] = {
                    "score": mr.score,
                    "error": mr.error,
                }
            elif isinstance(mr, dict):
                metrics_by_name[mr.get("metric", "")] = mr

        # Check against thresholds
        for metric_name, threshold_config in thresholds.items():
            metric_result = metrics_by_name.get(metric_name)
            if metric_result is None:
                continue
            if metric_result.get("error"):
                continue

            score = metric_result.get("score", 0.0)
            threshold_value = threshold_config.get("value", 0)
            direction = threshold_config.get("direction", "higher_is_better")

            passed = score >= threshold_value if direction == "higher_is_better" else score <= threshold_value

            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            results_summary.append(
                {
                    "sample": sample_name,
                    "metric": metric_name,
                    "score": round(score, 4),
                    "threshold": threshold_value,
                    "direction": direction,
                    "passed": passed,
                }
            )

            symbol = "[PASS]" if passed else "[FAIL]"
            print(f"  {symbol} {sample_name} / {metric_name}: {score:.4f} ({status}, threshold={threshold_value})")

    print("-" * 60)

    # Print summary table
    if results_summary:
        print("\nMetric Summary:")
        print(f"{'Sample':<20} {'Metric':<25} {'Score':>8} {'Threshold':>10} {'Direction':<18} {'Status':<6}")
        print("-" * 95)
        for r in results_summary:
            direction_label = "higher" if r["direction"] == "higher_is_better" else "lower"
            print(
                f"{r['sample']:<20} {r['metric']:<25} {r['score']:>8.4f} {r['threshold']:>10.4f} {direction_label:<18} {'PASS' if r['passed'] else 'FAIL':<6}"
            )

    if all_passed:
        print(f"\n[PASS] Quality Gate: PASSED ({len(results_summary)} checks)")
        return 0
    else:
        failed_count = sum(1 for r in results_summary if not r["passed"])
        print(f"\n[FAIL] Quality Gate: FAILED ({failed_count}/{len(results_summary)} checks failed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
