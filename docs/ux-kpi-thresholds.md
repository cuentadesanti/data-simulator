# UX KPI Thresholds (Refactor Baseline)

This document is the source of truth for UX success thresholds. Refactor work should be planned and accepted against these KPIs.

## Scope
- Product surface: DAG editor, Data Preview, Pipeline workbench
- Measurement cadence: per milestone, then weekly after rollout
- Segments: new users, returning users, power users

## Laws of UX KPI Thresholds

| Law of UX | KPI | Baseline | Threshold (Phase Gate) | Target (End State) | Direction |
|---|---|---:|---:|---:|---|
| Hick's Law | Visible primary actions in active workspace | 9 | <= 7 | <= 5 | Lower is better |
| Fitts's Law | Avg pointer travel to primary CTA (px) | 520 | <= 360 | <= 260 | Lower is better |
| Jakob's Law | Familiar pattern coverage (%) | 62 | >= 75 | >= 85 | Higher is better |
| Cognitive Load | Avg clicks per happy path | 10.0 | <= 9.0 | <= 8.0 | Lower is better |
| Tesler's Law | Manual orchestration steps per flow | 3 | <= 2 | <= 1 | Lower is better |
| Goal-Gradient Effect | Flows with explicit progress feedback (%) | 40 | >= 65 | >= 85 | Higher is better |
| Doherty Threshold | P95 action-to-feedback latency (ms) | 1400 | <= 700 | <= 400 | Lower is better |
| Peak-End Rule | Successful flow completion rate (%) | 68 | >= 80 | >= 90 | Higher is better |

## Happy Path KPI Contracts

| Path ID | Description | Baseline Clicks | Phase Gate | End Target |
|---|---|---:|---:|---:|
| HP-1 | Build DAG -> preview data | 13 | <= 10 | <= 8 |
| HP-2 | Open existing project -> small edit -> share | 11 | <= 9 | <= 7 |
| HP-3 | Upload dataset -> transform -> model | N/A (missing path) | <= 10 | <= 8 |

## Measurement Definitions

1. Visible primary actions:
Count actions with first-order impact currently visible without opening overflow menus.

2. Avg pointer travel:
Mean pixel distance from last field interaction to next primary CTA for each happy path.

3. Familiar pattern coverage:
Percent of key flows matching expected conventions (explicit source selection, progressive disclosure, standard save/share patterns).

4. Avg clicks per happy path:
Mean clicks to complete HP-1/2/3 from clean state.

5. Manual orchestration steps:
User-triggered control steps required solely to move state machine forward (example: manual validate before generate).

6. Progress feedback coverage:
Percent of paths with step-level progress and completion cues.

7. P95 action-to-feedback latency:
95th percentile from user action to visible feedback (status, toast, inline state change, updated content).

8. Completion rate:
Completed runs / started runs for each happy path.

## Non-negotiable Rules

1. No phase closes unless all phase-gate thresholds are met.
2. KPI regressions block release unless explicitly waived.
3. Feature work that increases click counts must remove equivalent click cost elsewhere.
