// DAG Types - matching backend Pydantic models

export type NodeKind = 'stochastic' | 'deterministic';
export type NodeScope = 'global' | 'group' | 'row';
export type NodeDtype = 'float' | 'int' | 'category' | 'bool' | 'string';

// Parameter value types
export interface LookupValue {
  lookup: string;
  key: string;
  default?: number;
}

export interface MappingValue {
  mapping: Record<string, number>;
  key: string;
  default?: number;
}

export type ParamValue = number | string | LookupValue | MappingValue;

// Distribution configuration
export interface DistributionConfig {
  type: string;
  params: Record<string, ParamValue>;
}

// Post-processing configuration
export interface PostProcessing {
  round_decimals?: number;
  clip_min?: number;
  clip_max?: number;
  missing_rate?: number;
}

// Node configuration (backend model)
export interface NodeConfig {
  id: string;
  name: string;
  kind: NodeKind;
  dtype?: NodeDtype;
  scope: NodeScope;
  group_by?: string;
  distribution?: DistributionConfig;
  formula?: string;
  post_processing?: PostProcessing;
}

// Helper to convert name to snake_case (mirrors backend logic)
export function toSnakeCase(name: string): string {
  // Replace common separators with spaces
  let result = name.replace(/[-\s]+/g, ' ');
  // Remove non-alphanumeric characters (except spaces)
  result = result.replace(/[^a-zA-Z0-9\s]/g, '');
  // Split into words and join with underscores
  const words = result.trim().toLowerCase().split(/\s+/);
  result = words.join('_');
  // Ensure it starts with a letter or underscore
  if (result && /^\d/.test(result)) {
    result = '_' + result;
  }
  return result || 'var';
}

// Get effective var_name (explicit or derived from name)
export function getEffectiveVarName(node: NodeConfig): string {
  return toSnakeCase(node.name);
}

// Edge configuration
export interface DAGEdge {
  source: string;
  target: string;
}

// Layout configuration
export interface NodePosition {
  x: number;
  y: number;
}

export interface Layout {
  positions: Record<string, NodePosition>;
}

// Generation metadata
export interface GenerationMetadata {
  sample_size: number;
  seed?: number;
  preview_rows?: number;
}

// Full DAG definition
export interface DAGDefinition {
  schema_version?: string;
  nodes: NodeConfig[];
  edges: DAGEdge[];
  context: Record<string, unknown>;
  metadata: GenerationMetadata;
  layout?: Layout;
}

// React Flow node data
export interface FlowNodeData {
  config: NodeConfig;
  isSelected?: boolean;
}

// React Flow node with position
export interface FlowNode {
  id: string;
  type: 'custom';
  position: { x: number; y: number };
  data: FlowNodeData;
}

// React Flow edge
export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}

// Edge validation types
export type EdgeStatus = 'used' | 'unused' | 'invalid';

export interface EdgeValidation {
  source: string;
  target: string;
  status: EdgeStatus;
  reason?: string;
}

export interface MissingEdge {
  source: string;
  target: string;
}

// Structured validation error types
export type ErrorCode =
  | 'CYCLE_DETECTED'
  | 'MISSING_EDGE'
  | 'INVALID_EDGE'
  | 'UNKNOWN_VARIABLE'
  | 'SYNTAX_ERROR'
  | 'RESERVED_KEYWORD'
  | 'INVALID_GROUP_BY'
  | 'LIMIT_EXCEEDED'
  | 'MISSING_DISTRIBUTION'
  | 'MISSING_FORMULA'
  | 'INVALID_DTYPE'
  | 'DUPLICATE_NODE_ID'
  | 'DUPLICATE_VAR_NAME'
  | 'ISOLATED_NODE'
  | 'GENERAL_ERROR';

export type ErrorSeverity = 'error' | 'warning';

export interface ValidationError {
  code: ErrorCode;
  message: string;
  severity: ErrorSeverity;
  node_id?: string;
  node_name?: string;
  suggestion?: string;
  context?: Record<string, unknown>;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  structured_errors: ValidationError[];
  topological_order?: string[];
  edge_statuses: EdgeValidation[];
  missing_edges: MissingEdge[];
}
