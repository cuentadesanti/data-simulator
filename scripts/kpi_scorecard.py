#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import quantiles
from typing import Any


def load_events(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and "events" in payload:
        payload = payload["events"]
    if not isinstance(payload, list):
        raise ValueError("events payload must be a list or {'events': [...]}")
    return [event for event in payload if isinstance(event, dict)]


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    return float(quantiles(values, n=100, method="inclusive")[94])


def compute_kpis(events: list[dict[str, Any]]) -> dict[str, float]:
    clicks_by_path: dict[str, int] = defaultdict(int)
    started_by_path: dict[str, int] = defaultdict(int)
    completed_by_path: dict[str, int] = defaultdict(int)
    feedback_latencies: list[float] = []
    visible_action_snapshots: list[int] = []
    manual_orchestration_steps = 0
    progress_feedback_events = 0
    pointer_samples: list[float] = []
    familiar_pattern_samples: list[float] = []

    for event in events:
        event_type = event.get("event_type")
        path_id = str(event.get("path_id") or "")
        metadata = event.get("metadata") or {}

        if event_type == "visible_actions_snapshot":
            count = metadata.get("count")
            if isinstance(count, (int, float)):
                visible_action_snapshots.append(int(count))
        if event_type == "click":
            if path_id:
                clicks_by_path[path_id] += 1
        elif event_type == "flow_started" and path_id:
            started_by_path[path_id] += 1
        elif event_type == "flow_completed" and path_id:
            completed_by_path[path_id] += 1
        elif event_type == "feedback_latency":
            latency_ms = event.get("latency_ms")
            if isinstance(latency_ms, (int, float)) and metadata.get("user_initiated") is not False:
                feedback_latencies.append(float(latency_ms))
        elif event_type == "manual_orchestration":
            manual_orchestration_steps += 1
        elif event_type == "progress_feedback":
            progress_feedback_events += 1

        pointer_px = metadata.get("pointer_travel_px")
        if isinstance(pointer_px, (int, float)):
            pointer_samples.append(float(pointer_px))

        familiar = metadata.get("familiar_pattern")
        if isinstance(familiar, bool):
            familiar_pattern_samples.append(1.0 if familiar else 0.0)
        elif isinstance(familiar, (int, float)):
            familiar_pattern_samples.append(1.0 if float(familiar) > 0 else 0.0)

    paths_with_clicks = max(1, len(clicks_by_path))
    avg_clicks = sum(clicks_by_path.values()) / paths_with_clicks
    total_started = sum(started_by_path.values())
    total_completed = sum(completed_by_path.values())
    completion_rate = (total_completed / total_started * 100.0) if total_started else 0.0

    progress_feedback_coverage = 0.0
    if total_started:
        progress_feedback_coverage = min(100.0, (progress_feedback_events / total_started) * 100.0)

    familiar_pattern_coverage = 0.0
    if familiar_pattern_samples:
        familiar_pattern_coverage = (sum(familiar_pattern_samples) / len(familiar_pattern_samples)) * 100.0

    avg_pointer_travel = sum(pointer_samples) / len(pointer_samples) if pointer_samples else 0.0

    return {
        "visible_primary_actions": float(max(visible_action_snapshots)) if visible_action_snapshots else 0.0,
        "avg_pointer_travel_px": float(avg_pointer_travel),
        "familiar_pattern_coverage_pct": float(familiar_pattern_coverage),
        "avg_clicks_happy_path": float(avg_clicks),
        "manual_orchestration_steps": float(manual_orchestration_steps),
        "progress_feedback_coverage_pct": float(progress_feedback_coverage),
        "p95_feedback_latency_ms": float(percentile_95(feedback_latencies)),
        "completion_rate_pct": float(completion_rate),
    }


def to_markdown(kpis: dict[str, float]) -> str:
    rows = [
        ("visible_primary_actions", "<=5", kpis["visible_primary_actions"]),
        ("avg_pointer_travel_px", "<=260", kpis["avg_pointer_travel_px"]),
        ("familiar_pattern_coverage_pct", ">=85", kpis["familiar_pattern_coverage_pct"]),
        ("avg_clicks_happy_path", "<=8", kpis["avg_clicks_happy_path"]),
        ("manual_orchestration_steps", "<=1", kpis["manual_orchestration_steps"]),
        ("progress_feedback_coverage_pct", ">=85", kpis["progress_feedback_coverage_pct"]),
        ("p95_feedback_latency_ms", "<=400", kpis["p95_feedback_latency_ms"]),
        ("completion_rate_pct", ">=90", kpis["completion_rate_pct"]),
    ]
    lines = [
        "# UX KPI Scorecard",
        "",
        "| KPI | Target | Actual |",
        "|---|---:|---:|",
    ]
    lines.extend(f"| {name} | {target} | {value:.2f} |" for name, target, value in rows)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute UX KPI scorecard from telemetry events")
    parser.add_argument("--events", required=True, help="Path to telemetry events JSON")
    parser.add_argument("--out-json", required=True, help="Output JSON scorecard path")
    parser.add_argument("--out-md", required=True, help="Output markdown scorecard path")
    args = parser.parse_args()

    events = load_events(Path(args.events))
    kpis = compute_kpis(events)
    payload = {"kpis": kpis, "event_count": len(events)}

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(to_markdown(kpis))


if __name__ == "__main__":
    main()
