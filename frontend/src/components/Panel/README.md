# Node Editor Panel Components

This directory contains the node editor panel components for the Data Simulator frontend.

## Components

### NodeEditor.tsx
Main panel container that orchestrates all sub-components.

- Shows "Select a node" message when nothing is selected
- Displays the currently selected node's ID in the header
- Contains a close button to deselect the node
- Renders all editing forms based on node configuration
- Fixed width panel (max-w-md) with scrollable content area

### BasicInfo.tsx
Basic node information editor.

**Fields:**
- Node name (text input)
- Kind selector (stochastic/deterministic radio buttons)
- Data type selector (float/int/category/bool/string dropdown)
- Scope selector (global/group/row dropdown)
- Group by field (conditional dropdown, only visible when scope=group)

**Features:**
- Automatically clears `group_by` when scope changes from 'group'
- Resets distribution/formula when switching between stochastic/deterministic
- Filters group_by options to only show categorical nodes
- Shows warning if no categorical nodes exist when scope=group

### DistributionForm.tsx
Distribution configuration for stochastic nodes.

**Distribution Types:**
- Normal (Gaussian): mu, sigma
- Uniform: low, high
- Categorical: categories (comma-separated), probs (comma-separated)
- Bernoulli: p (probability)

**Features:**
- Dynamic parameter inputs based on distribution type
- Three input modes per parameter:
  - Literal: Direct numeric value
  - Formula: String expression referencing other nodes
  - Lookup: Reference to context lookup table
- Input type toggle buttons for each parameter
- Helpful tip about parameter input modes

### FormulaEditor.tsx
Formula editor for deterministic nodes.

**Features:**
- Large textarea for formula expression
- List of available variables (other node IDs) with click-to-insert
- Collapsible help panel showing:
  - Available functions (abs, min, max, sqrt, pow, exp, log, etc.)
  - Syntax examples
  - Operators reference
- Click-to-insert functionality for both variables and functions
- Each variable shows node details (kind, dtype, scope)

**Supported Functions:**
abs, min, max, sqrt, pow, exp, log, sin, cos, tan, round, floor, ceil

**Operators:**
+, -, *, /, **, %, >, <, ==, !=, and, or, not

### PostProcessing.tsx
Optional post-processing transformations.

**Options:**
- round_decimals: Round to N decimal places (0-10)
- clip_min: Minimum value threshold
- clip_max: Maximum value threshold
- missing_rate: Rate of missing values (0-1)

**Features:**
- Checkbox to enable/disable each option
- Default values when enabling options
- Active summary panel showing all enabled post-processing steps
- Helpful descriptions for each option

## Usage

```tsx
import { NodeEditor } from './components/Panel';

function App() {
  return (
    <div className="flex">
      <div className="flex-1">
        {/* Main canvas area */}
      </div>
      <NodeEditor />
    </div>
  );
}
```

## Store Integration

All components use the Zustand store from `stores/dagStore.ts`:

- `selectedNodeId` - Currently selected node ID
- `getSelectedNode()` - Get the selected node config
- `updateNode(nodeId, partialConfig)` - Update node configuration
- `selectNode(null)` - Deselect the current node
- `nodes` - All flow nodes (used for references)

## Styling

All components use TailwindCSS for styling with a consistent design system:

- Color scheme: Blue for primary actions, gray for neutral elements
- Border radius: rounded-md (6px)
- Shadows: shadow-sm for subtle elevation
- Spacing: Consistent use of Tailwind spacing scale
- Focus states: Blue ring on interactive elements
