# Data Simulator – Core Spec (Condensed)

## What this is
Visual probabilistic DAG → JSON → backend forward-samples synthetic datasets  
Frontend defines structure, backend is the single source of truth for semantics

---

## Key Concepts (non-negotiable)

### Node
- Identified by `id` (stable, machine) and `name` (UI only)
- `kind` is MECE
  - `stochastic` → must have `distribution`
  - `deterministic` → must have `formula`
- `scope ∈ {global, row, group}`
- `dtype` is explicit, no inference

### Edge
- Pure dependency
- Defines evaluation order only

### Context
- Global constants and lookup tables
- Read-only during generation
- Used by formulas and lookup params

---

## ParamValue (this is the tricky part)

Explicit, no heuristics

- `number | int` → literal
- `string` → expression, evaluated with
  - parent node values
  - context constants
- `LookupValue`
  - `lookup`: context table name
  - `key`: categorical node id
- `MappingValue`
  - inline mapping, same semantics as lookup

Rules
- Node references are always by node id
- UI never invents variable names
- Snake_case aliases are cosmetic only

---

## Scopes Semantics

| Scope  | Samples | Meaning |
|--------|---------|---------|
| global | 1       | broadcast to all rows |
| row    | N       | one per row |
| group  | #groups | sampled per group, then mapped |

Rules for `group_by`
- Only valid if `scope=group`
- Must reference one categorical ancestor
- Backend enforces this, frontend only guides

Execution order
1. Validate DAG
2. Topological sort
3. For each node
   - global → sample once
   - group → group, sample, map
   - row → sample per row

---

## Backend Responsibilities

- DAG validation
  - acyclic
  - MECE kind rules
  - group_by ancestry and categorical
- Param resolution
  - literals
  - expressions (safe eval)
  - lookups
- Sampling
  - registry-based distributions
- Backend owns truth
  - frontend is advisory, not authoritative

---

## Frontend Responsibilities

- Never generate logic
- Never infer dependencies
- Always export canonical JSON

UI rules that avoid bugs
- Node id is immutable after creation
- Expressions autocomplete from node ids
- Disallow referencing node ids not in ancestors
- Store ParamValue as structured objects, not strings

---

## API (minimal)

- `GET /distributions`
- `POST /dag/validate`
- `POST /dag/preview` always sync, ~500 rows
- `POST /dag/generate` async-ready from day one

---

## Implementation Phases (collapsed)

1. Backend core
   - models
   - validation
   - topo sort
   - basic distributions
2. Param resolver
   - expressions
   - lookup
3. Frontend core