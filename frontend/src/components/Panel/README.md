# Node Editor Panel Components

Compact inspector panel for editing DAG node configuration.

## Components

### NodeEditor.tsx
Main panel container. Compact layout:

- **Header**: Node name `<input>` (editable, acts as title) + close button
- **Var preview**: One-line `var: snake_case_name` derived from node name
- **Meta row**: Kind toggle (`[Stoch | Det]`) + dtype `<select>` + scope `<select>` — all in one horizontal row
- **Group-by**: Conditional row, only when `scope === 'group'`
- **Kind-specific section**: Delegates to `DistributionForm` or `FormulaEditor`
- **Post-processing**: Collapsible `PostProcessing` at the bottom

Kind toggle clears distribution/formula on switch (clean swap, no state preservation).

### DistributionForm.tsx
Distribution configuration for stochastic nodes.

- Distribution dropdown with search (fetches from `/distributions` API)
- One text input per distribution parameter (label left, monospace input right)
- Values parsed on blur/Enter: if the full string is a finite number, stored as `number`; otherwise stored as `string` (expression)
- Categorical distributions use plain text inputs for `categories` and `probs` (comma-separated)
- `InputChips` below param fields for quick variable insertion
- Changing distribution type resets params to defaults (clean swap)

### InputChips.tsx
Shared clickable chip row for inserting variable names into formula inputs.

- Parent node var names (blue), context keys (purple), built-in constants PI/E (gray)
- `onMouseDown={e => e.preventDefault()}` prevents stealing focus from the active input
- `onInsert(text)` callback — parent component handles actual insertion
- Does not render if no chips are available

### FormulaEditor.tsx
Formula editor for deterministic nodes.

- Textarea with autocomplete suggestions (nodes, functions, constants)
- Live validation (syntax + reference checks)
- `InputChips` for quick variable insertion (replaces old Quick Insert section)
- Collapsible help panel (functions, operators, examples)

### PostProcessing.tsx
Collapsible post-processing options.

- Collapsed by default (auto-expands when any option is active)
- **Collapsed view**: Chevron + "Post-Processing" + inline summary (e.g., `Round 2 · Min 0 · Max 100 · 5% missing`)
- **Expanded view**: Checkboxes for round/clip_min/clip_max/missing_rate with compact number inputs
- `aria-expanded` for accessibility

## Store Integration

All components use the Zustand store from `stores/dagStore.ts`:

- `selectedNodeId` — Currently selected node ID
- `updateNode(nodeId, partialConfig)` — Update node configuration
- `selectNode(null)` — Deselect the current node
- `nodes` / `edges` / `context` — DAG data for parent/context resolution
