// Distribution Types - matching backend distribution registry

export interface DistributionParam {
  name: string;
  display_name: string;
  description: string;
  type: 'float' | 'int' | 'string' | 'array' | 'bool';
  default?: number | string | boolean | number[] | string[];
  min?: number;
  max?: number;
  required: boolean;
}

export interface DistributionInfo {
  name: string;
  display_name: string;
  category: 'continuous' | 'discrete' | 'categorical';
  description: string;
  params: DistributionParam[];
  default_dtype: 'float' | 'int' | 'category' | 'bool';
}

// Common distribution configs for quick access
export const COMMON_DISTRIBUTIONS = {
  normal: {
    type: 'normal',
    params: { mu: 0, sigma: 1 },
  },
  uniform: {
    type: 'uniform',
    params: { low: 0, high: 1 },
  },
  categorical: {
    type: 'categorical',
    params: { categories: ['A', 'B', 'C'], probs: [0.33, 0.34, 0.33] },
  },
  bernoulli: {
    type: 'bernoulli',
    params: { p: 0.5 },
  },
} as const;

// Distribution categories for UI grouping
export const DISTRIBUTION_CATEGORIES = {
  continuous: {
    label: 'Continuous',
    description: 'Distributions for real-valued variables',
  },
  discrete: {
    label: 'Discrete',
    description: 'Distributions for integer-valued variables',
  },
  categorical: {
    label: 'Categorical',
    description: 'Distributions for category/string variables',
  },
} as const;
