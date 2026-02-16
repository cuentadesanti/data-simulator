import type { DistributionConfig, LookupValue, MappingValue } from '../types/dag';

/**
 * Get a param value with fallbacks, returning string representation
 */
function getParam(params: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = params[key];
    if (value !== undefined) {
      return paramToString(value);
    }
  }
  return '?';
}

/**
 * Convert a param value to a displayable string
 */
function paramToString(param: unknown): string {
  if (typeof param === 'number') {
    return param.toString();
  }
  if (typeof param === 'string') {
    // It's a formula expression
    return formulaToLatex(param);
  }
  if (typeof param === 'object' && param !== null) {
    if ('lookup' in param) {
      const lookup = param as LookupValue;
      return `${lookup.lookup}[${lookup.key}]`;
    }
    if ('mapping' in param) {
      const mapping = param as MappingValue;
      return `map(${mapping.key})`;
    }
  }
  return '?';
}

/**
 * Convert distribution config to LaTeX notation
 */
export function distributionToLatex(dist: DistributionConfig | undefined): string {
  if (!dist) return '';

  const { type, params } = dist;

  switch (type.toLowerCase()) {
    case 'normal':
    case 'gaussian': {
      const mu = getParam(params, 'mu', 'mean');
      const sigma = getParam(params, 'sigma', 'std');
      return `\\mathcal{N}(${mu}, ${sigma}^2)`;
    }

    case 'uniform': {
      const low = getParam(params, 'low', 'a');
      const high = getParam(params, 'high', 'b');
      return `\\mathcal{U}(${low}, ${high})`;
    }

    case 'categorical': {
      const categoriesParam = params.categories;
      if (Array.isArray(categoriesParam) && categoriesParam.length > 0) {
        const categories = categoriesParam as string[];
        if (categories.length <= 3) {
          return `\\text{Cat}(${categories.join(', ')})`;
        }
        return `\\text{Cat}(${categories.slice(0, 2).join(', ')}, \\ldots)`;
      }
      return '\\text{Categorical}';
    }

    case 'bernoulli': {
      const p = getParam(params, 'p');
      return `\\text{Bern}(${p})`;
    }

    case 'poisson': {
      const lambda = getParam(params, 'lambda', 'rate');
      return `\\text{Pois}(${lambda})`;
    }

    case 'exponential': {
      const rate = getParam(params, 'rate', 'lambda');
      return `\\text{Exp}(${rate})`;
    }

    case 'beta': {
      const alpha = getParam(params, 'alpha', 'a');
      const beta = getParam(params, 'beta', 'b');
      return `\\text{Beta}(${alpha}, ${beta})`;
    }

    case 'gamma': {
      const shape = getParam(params, 'shape', 'k');
      const scale = getParam(params, 'scale', 'theta');
      return `\\Gamma(${shape}, ${scale})`;
    }

    case 'binomial': {
      const n = getParam(params, 'n');
      const p = getParam(params, 'p');
      return `\\text{Bin}(${n}, ${p})`;
    }

    case 'lognormal': {
      const mu = getParam(params, 'mu', 'mean');
      const sigma = getParam(params, 'sigma', 'std');
      return `\\text{LogN}(${mu}, ${sigma}^2)`;
    }

    default: {
      // Generic distribution with type name
      const paramList = Object.entries(params)
        .slice(0, 2)
        .map(([, v]) => paramToString(v))
        .join(', ');
      return `\\text{${type}}(${paramList})`;
    }
  }
}

/**
 * Wrap variable names containing underscores in \text{} to prevent subscript interpretation
 * E.g., "income_net" becomes "\text{income\_net}" instead of "income" with subscript "net"
 */
function escapeVarNames(text: string): string {
  // Match variable names (identifiers): letter/underscore followed by letters/numbers/underscores
  // Only process those containing underscores
  return text.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g, (match) => {
    if (match.includes('_')) {
      // Escape underscores and wrap in \text{}
      const escaped = match.replace(/_/g, '\\_');
      return `\\text{${escaped}}`;
    }
    return match;
  });
}

/**
 * Convert a formula to simple LaTeX notation
 */
export function formulaToLatex(formula: string | undefined): string {
  if (!formula) return '';

  // First escape variable names with underscores
  let latex = escapeVarNames(formula);

  // Then apply other transformations
  latex = latex
    .replace(/\*/g, ' \\cdot ')
    .replace(/sqrt\(([^)]+)\)/g, '\\sqrt{$1}')
    .replace(/log\(([^)]+)\)/g, '\\log($1)')
    .replace(/exp\(([^)]+)\)/g, 'e^{$1}')
    .replace(/\^(\d+)/g, '^{$1}')
    .replace(/\^(\w+)/g, '^{$1}');

  return latex;
}
