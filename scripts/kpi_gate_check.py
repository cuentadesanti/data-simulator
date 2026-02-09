#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PHASE_TARGETS = {
    "phase1": {
        "visible_primary_actions": ("<=", 7.0),
        "avg_clicks_happy_path": ("<=", 10.0),
        "manual_orchestration_steps": ("<=", 2.0),
        "p95_feedback_latency_ms": ("<=", 700.0),
    },
    "phase2": {
        "avg_clicks_happy_path": ("<=", 10.0),
        "completion_rate_pct": (">=", 80.0),
        "progress_feedback_coverage_pct": (">=", 65.0),
    },
    "phase3": {
        "avg_pointer_travel_px": ("<=", 360.0),
        "familiar_pattern_coverage_pct": (">=", 75.0),
        "avg_clicks_happy_path": ("<=", 9.0),
    },
    "phase4": {
        "visible_primary_actions": ("<=", 5.0),
        "avg_pointer_travel_px": ("<=", 260.0),
        "familiar_pattern_coverage_pct": (">=", 85.0),
        "avg_clicks_happy_path": ("<=", 8.0),
        "manual_orchestration_steps": ("<=", 1.0),
        "progress_feedback_coverage_pct": (">=", 85.0),
        "p95_feedback_latency_ms": ("<=", 400.0),
        "completion_rate_pct": (">=", 90.0),
    },
}


def compare(actual: float, op: str, target: float) -> bool:
    if op == "<=":
        return actual <= target
    if op == ">=":
        return actual >= target
    raise ValueError(f"Unsupported operator: {op}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail if KPI scorecard misses threshold gate")
    parser.add_argument("--scorecard", required=True, help="Path to scorecard JSON")
    parser.add_argument("--phase", default="phase4", choices=sorted(PHASE_TARGETS.keys()))
    args = parser.parse_args()

    payload = json.loads(Path(args.scorecard).read_text())
    kpis = payload.get("kpis", {})
    checks = PHASE_TARGETS[args.phase]

    failures: list[str] = []
    for metric, (op, target) in checks.items():
        actual = float(kpis.get(metric, 0.0))
        if not compare(actual, op, target):
            failures.append(f"{metric}: {actual:.2f} {op} {target:.2f} FAILED")

    if failures:
        print(f"KPI gate failed for {args.phase}")
        for failure in failures:
            print(f" - {failure}")
        sys.exit(1)

    print(f"KPI gate passed for {args.phase}")


if __name__ == "__main__":
    main()
