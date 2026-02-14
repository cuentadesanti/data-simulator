"""UX telemetry ingestion and KPI snapshot routes."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import quantiles
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import require_auth, require_user_id
from app.db import crud, get_db

router = APIRouter()


class UXEventIn(BaseModel):
    event_type: str = Field(max_length=100)
    path_id: str | None = None
    stage: str | None = None
    action: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UXEventsBatchIn(BaseModel):
    events: list[UXEventIn] = Field(max_length=500)


class UXEventsIngestResponse(BaseModel):
    ingested: int


class KPISnapshotResponse(BaseModel):
    window_hours: int
    generated_at: str
    kpis: dict[str, float]



@router.post("/events", response_model=UXEventsIngestResponse)
def ingest_ux_events(
    payload: UXEventsBatchIn,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> UXEventsIngestResponse:
    user_id = require_user_id(user)
    ingested = crud.create_ux_events(
        db,
        user_id=user_id,
        events=[event.model_dump() for event in payload.events],
    )
    return UXEventsIngestResponse(ingested=ingested)


@router.get("/kpi-snapshot", response_model=KPISnapshotResponse)
def get_kpi_snapshot(
    window: int = Query(default=168, ge=1, le=24 * 90),
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> KPISnapshotResponse:
    user_id = require_user_id(user)
    since_dt = datetime.now(UTC) - timedelta(hours=window)
    events = crud.list_ux_events(db, user_id=user_id, since_dt=since_dt)

    visible_action_snapshots: list[int] = []
    click_counts: defaultdict[str, int] = defaultdict(int)
    flow_started: defaultdict[str, int] = defaultdict(int)
    flow_completed: defaultdict[str, int] = defaultdict(int)
    feedback_latencies: list[int] = []
    orchestration_steps = 0
    progress_feedback = 0
    pointer_samples: list[float] = []
    familiar_pattern_samples: list[float] = []

    for event in events:
        metadata = event.event_metadata or {}

        if event.event_type == "visible_actions_snapshot":
            count = metadata.get("count")
            if isinstance(count, (int, float)):
                visible_action_snapshots.append(int(count))
        if event.event_type == "click":
            if event.path_id:
                click_counts[event.path_id] += 1
        if event.event_type == "flow_started" and event.path_id:
            flow_started[event.path_id] += 1
        if event.event_type == "flow_completed" and event.path_id:
            flow_completed[event.path_id] += 1
        if event.event_type == "feedback_latency" and event.latency_ms is not None:
            if metadata.get("user_initiated") is not False:
                feedback_latencies.append(event.latency_ms)
        if event.event_type == "manual_orchestration":
            orchestration_steps += 1
        if event.event_type == "progress_feedback":
            progress_feedback += 1

        pointer_px = metadata.get("pointer_travel_px")
        if isinstance(pointer_px, (int, float)):
            pointer_samples.append(float(pointer_px))

        familiar = metadata.get("familiar_pattern")
        if isinstance(familiar, bool):
            familiar_pattern_samples.append(1.0 if familiar else 0.0)
        elif isinstance(familiar, (int, float)):
            familiar_pattern_samples.append(1.0 if float(familiar) > 0 else 0.0)

    avg_clicks = (
        sum(click_counts.values()) / len(click_counts)
        if click_counts
        else 0.0
    )
    completion_total_started = sum(flow_started.values())
    completion_total_done = sum(flow_completed.values())
    completion_rate = (
        (completion_total_done / completion_total_started) * 100
        if completion_total_started > 0
        else 0.0
    )
    p95_latency = 0.0
    if len(feedback_latencies) == 1:
        p95_latency = float(feedback_latencies[0])
    elif len(feedback_latencies) >= 2:
        p95_latency = float(quantiles(feedback_latencies, n=100, method="inclusive")[94])

    avg_pointer_travel = (
        sum(pointer_samples) / len(pointer_samples) if pointer_samples else 0.0
    )
    familiar_coverage = (
        (sum(familiar_pattern_samples) / len(familiar_pattern_samples)) * 100.0
        if familiar_pattern_samples
        else 0.0
    )

    progress_feedback_coverage = 0.0
    if completion_total_started:
        progress_feedback_coverage = min(
            100.0, (progress_feedback / completion_total_started) * 100.0
        )

    kpis = {
        "visible_primary_actions": float(max(visible_action_snapshots)) if visible_action_snapshots else 0.0,
        "avg_pointer_travel_px": float(avg_pointer_travel),
        "familiar_pattern_coverage_pct": float(familiar_coverage),
        "avg_clicks_happy_path": float(avg_clicks),
        "manual_orchestration_steps": float(orchestration_steps),
        "progress_feedback_coverage_pct": float(progress_feedback_coverage),
        "p95_feedback_latency_ms": float(p95_latency),
        "completion_rate_pct": float(completion_rate),
    }

    return KPISnapshotResponse(
        window_hours=window,
        generated_at=datetime.now(UTC).isoformat(),
        kpis=kpis,
    )
