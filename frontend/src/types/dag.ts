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
  var_name?: string; // Custom variable name for formulas/output (defaults to snake_case of name)
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
  return node.var_name || toSnakeCase(node.name);
}

// Edge configuration
export interface DAGEdge {
  source: string;
  target: string;
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
