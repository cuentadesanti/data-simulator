import type { ContextVariableMeta } from '../types/dag';

export type SuggestionType = 'node' | 'context' | 'constant' | 'function';

export interface FormulaSuggestion {
  type: SuggestionType;
  id: string;
  name: string;
  description: string;
  insertText: string;
  matchScore: number;
}

const CONSTANTS: FormulaSuggestion[] = [
  { type: 'constant', id: 'PI', name: 'PI', description: '3.14159...', insertText: 'PI', matchScore: 0 },
  { type: 'constant', id: 'E', name: 'E', description: '2.71828...', insertText: 'E', matchScore: 0 },
  { type: 'constant', id: 'TRUE', name: 'TRUE', description: 'Boolean true', insertText: 'TRUE', matchScore: 0 },
  { type: 'constant', id: 'FALSE', name: 'FALSE', description: 'Boolean false', insertText: 'FALSE', matchScore: 0 },
];

const FUNCTIONS: FormulaSuggestion[] = [
  { type: 'function', id: 'abs', name: 'abs', description: 'Absolute value', insertText: 'abs(', matchScore: 0 },
  { type: 'function', id: 'min', name: 'min', description: 'Minimum of values', insertText: 'min(', matchScore: 0 },
  { type: 'function', id: 'max', name: 'max', description: 'Maximum of values', insertText: 'max(', matchScore: 0 },
  { type: 'function', id: 'sqrt', name: 'sqrt', description: 'Square root', insertText: 'sqrt(', matchScore: 0 },
  { type: 'function', id: 'pow', name: 'pow', description: 'Power', insertText: 'pow(', matchScore: 0 },
  { type: 'function', id: 'exp', name: 'exp', description: 'Exponential', insertText: 'exp(', matchScore: 0 },
  { type: 'function', id: 'log', name: 'log', description: 'Natural logarithm', insertText: 'log(', matchScore: 0 },
  { type: 'function', id: 'log10', name: 'log10', description: 'Log base 10', insertText: 'log10(', matchScore: 0 },
  { type: 'function', id: 'sin', name: 'sin', description: 'Sine', insertText: 'sin(', matchScore: 0 },
  { type: 'function', id: 'cos', name: 'cos', description: 'Cosine', insertText: 'cos(', matchScore: 0 },
  { type: 'function', id: 'tan', name: 'tan', description: 'Tangent', insertText: 'tan(', matchScore: 0 },
  { type: 'function', id: 'round', name: 'round', description: 'Round to nearest integer', insertText: 'round(', matchScore: 0 },
  { type: 'function', id: 'floor', name: 'floor', description: 'Round down', insertText: 'floor(', matchScore: 0 },
  { type: 'function', id: 'ceil', name: 'ceil', description: 'Round up', insertText: 'ceil(', matchScore: 0 },
  { type: 'function', id: 'clamp', name: 'clamp', description: 'Clamp between min and max', insertText: 'clamp(', matchScore: 0 },
  { type: 'function', id: 'if_else', name: 'if_else', description: 'Conditional', insertText: 'if_else(', matchScore: 0 },
];

function describeContextValue(value: unknown, meta?: ContextVariableMeta): string {
  const type = meta?.type;
  if (type === 'unsupported' || type === undefined) return 'unsupported type';
  if (type === 'number' && typeof value === 'number') return String(value);
  if (type === 'boolean' && typeof value === 'boolean') return String(value);
  if (type === 'dict' && typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return `dict (${Object.keys(value).length} keys)`;
  }
  if (type === 'array' && Array.isArray(value)) {
    return `array (${value.length} items)`;
  }
  return String(value);
}

export function buildSuggestions(
  parentVariables: { varName: string; name: string; kind?: string; dtype?: string; scope?: string }[],
  context: Record<string, unknown>,
  contextMeta: Record<string, ContextVariableMeta>,
): FormulaSuggestion[] {
  const nodes: FormulaSuggestion[] = parentVariables.map((v) => ({
    type: 'node' as const,
    id: v.varName,
    name: v.name,
    description: [v.kind, v.dtype || 'unknown', v.scope].filter(Boolean).join(' \u2022 '),
    insertText: v.varName,
    matchScore: 0,
  }));

  const contextSuggestions: FormulaSuggestion[] = Object.keys(context).map((key) => ({
    type: 'context' as const,
    id: key,
    name: key,
    description: describeContextValue(context[key], contextMeta[key]),
    insertText: key,
    matchScore: 0,
  }));

  return [...nodes, ...contextSuggestions, ...CONSTANTS, ...FUNCTIONS];
}

/** Shared set of names that are valid in formulas (used for validation).
 *  Includes all function names and parser keywords. */
export const FORMULA_RESERVED_NAMES = new Set([
  'abs', 'min', 'max', 'sqrt', 'pow', 'exp', 'log', 'log10',
  'sin', 'cos', 'tan', 'round', 'floor', 'ceil', 'clamp', 'if_else',
  'and', 'or', 'not', 'if', 'else', 'in', 'is',
]);
