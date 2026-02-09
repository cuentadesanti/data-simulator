# UX Refactor Plan (KPI-Driven)

This plan is sequenced by KPI thresholds defined in `/Users/cuentadesanti/code/data-simulator/docs/ux-kpi-thresholds.md`.

## Goal
Ship a less clunky workspace by reducing click tax, removing forced orchestration, reclaiming space, and eliminating confusing states (especially anonymous pipeline bootstrap).

## Personas and Primary Jobs

1. Synthetic Data Analyst:
Build and iterate DAG quickly, preview results fast.

2. Dataset Practitioner:
Upload existing data and run transforms/models without DAG dependency.

3. Product Manager Reviewer:
Make quick edits and share outcomes with minimal context switching.

## Happy Paths to Optimize

1. HP-1: Build DAG -> Preview
2. HP-2: Open Project -> Edit -> Share
3. HP-3: Upload Dataset -> Transform -> Model

## Phase 0: Instrumentation and Baseline (No UX changes yet)

### Deliverables
1. Client telemetry for click counts by happy path.
2. Action-to-feedback timing metrics.
3. Completion funnel for HP-1/2/3.
4. Weekly KPI scorecard script (docs + generated JSON snapshot).

### Exit Criteria (must pass)
1. All KPI baselines measurable and reproducible.
2. KPI dashboards available to engineering/product.

## Phase 1: Remove Workflow Friction

### Changes
1. Replace manual validate gate with auto-validation on DAG mutations (debounced).
2. Keep generate/preview enabled; show inline blocking errors only when invalid.
3. Reduce top-toolbar primary actions through progressive disclosure (overflow/grouping).

### KPI Gates
1. Visible primary actions <= 7.
2. Avg clicks HP-1 <= 10.
3. Manual orchestration steps <= 2.
4. P95 feedback latency <= 700ms.

## Phase 2: Source-First Pipeline Entry

### Changes
1. Remove anonymous pipeline autostart and loading screen.
2. Add explicit source chooser in Pipeline tab:
`Use DAG Source` and `Upload Dataset`.
3. Implement upload source bootstrap (CSV/Parquet) with schema confirmation.

### KPI Gates
1. Completion rate >= 80%.
2. Progress feedback coverage >= 65%.
3. HP-3 click count <= 10.
4. Manual orchestration steps <= 2.

## Phase 3: Layout and Density Refactor

### Changes
1. Convert fixed side panels to responsive, resizable regions.
2. Maximize workspace usage for active task (canvas/data/model views).
3. Simplify visual divisions (fewer stacked bars, stronger hierarchy).

### KPI Gates
1. Avg pointer travel <= 360px.
2. Familiar pattern coverage >= 75%.
3. HP-2 click count <= 9.

## Phase 4: End-State Polish

### Changes
1. Final information architecture cleanup and language consistency.
2. Consolidate save/share behaviors into clear primary and secondary actions.
3. Tighten feedback and completion cues at end of each path.

### Final Target Gates
1. Visible primary actions <= 5.
2. Avg pointer travel <= 260px.
3. Familiar pattern coverage >= 85%.
4. Avg clicks per happy path <= 8.
5. Manual orchestration steps <= 1.
6. Progress feedback coverage >= 85%.
7. P95 feedback latency <= 400ms.
8. Completion rate >= 90%.

## Engineering Workstreams

1. Workflow state machine:
Auto-validation, non-blocking preview generation, error state unification.

2. Data source architecture:
Pipeline source abstraction for DAG + file upload.

3. UI shell/layout:
Responsive split panes, primary action prioritization, hierarchy cleanup.

4. Telemetry and quality:
Path instrumentation, KPI reporting, CI checks for click budgets.

## Suggested Build Order

1. Instrumentation (Phase 0)
2. Auto-validation and action consolidation (Phase 1)
3. Source chooser + upload source (Phase 2)
4. Space/layout rework (Phase 3)
5. Final pass with KPI hardening (Phase 4)

## Risks and Mitigations

1. Risk: Auto-validation performance impact on large DAGs.
Mitigation: Debounce, incremental validation, background workers if needed.

2. Risk: Upload source increases backend/storage complexity.
Mitigation: Start with size limits and one storage strategy.

3. Risk: Layout changes disrupt power users.
Mitigation: Beta toggle and focused user testing per persona.
