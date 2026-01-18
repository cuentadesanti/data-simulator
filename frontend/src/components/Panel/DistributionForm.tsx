import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { ParamValue, LookupValue } from '../../types/dag';
import type { DistributionInfo } from '../../services/api';
import { useDAGStore } from '../../stores/dagStore';
import { distributionsApi } from '../../services/api';
import { FormulaInput } from './FormulaInput';

interface DistributionFormProps {
  nodeId: string;
}

type InputType = 'literal' | 'formula' | 'lookup';

interface ParamInputProps {
  label: string;
  paramName: string;
  nodeId: string;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

// Helper to determine input type from value
const getInputTypeFromValue = (value: ParamValue | undefined): InputType => {
  if (typeof value === 'object' && value !== null && 'lookup' in value) {
    return 'lookup';
  }
  if (typeof value === 'string') {
    return 'formula';
  }
  return 'literal';
};

const ParamInput: React.FC<ParamInputProps> = ({
  label,
  paramName,
  nodeId,
  placeholder,
  min,
  max,
  step,
  description,
}) => {
  // Get value directly from store to avoid stale closures
  const value = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.distribution?.params[paramName];
  });
  const updateNode = useDAGStore((state) => state.updateNode);

  const [inputType, setInputType] = useState<InputType>(() => getInputTypeFromValue(value));

  // Sync inputType when value type changes externally
  useEffect(() => {
    const newType = getInputTypeFromValue(value);
    if (newType !== inputType) {
      setInputType(newType);
    }
  }, [value, inputType]);

  // Use callback to get fresh distribution from store
  const handleChange = useCallback(
    (newValue: ParamValue) => {
      const state = useDAGStore.getState();
      const node = state.nodes.find((n) => n.id === nodeId);
      const currentDist = node?.data.config.distribution || { type: 'normal', params: {} };

      updateNode(nodeId, {
        distribution: {
          ...currentDist,
          params: {
            ...currentDist.params,
            [paramName]: newValue,
          },
        },
      });
    },
    [nodeId, paramName, updateNode]
  );

  const handleTypeChange = (newType: InputType) => {
    setInputType(newType);
    // Reset to default value for the new type
    if (newType === 'literal') {
      handleChange(0);
    } else if (newType === 'formula') {
      handleChange('');
    } else if (newType === 'lookup') {
      handleChange({ lookup: '', key: '', default: 0 });
    }
  };

  const renderInput = () => {
    if (inputType === 'literal') {
      return (
        <input
          type="number"
          value={typeof value === 'number' ? value : 0}
          onChange={(e) => handleChange(parseFloat(e.target.value) || 0)}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step || 'any'}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
      );
    }

    if (inputType === 'formula') {
      return (
        <FormulaInput
          value={typeof value === 'string' ? value : ''}
          onChange={(newValue) => handleChange(newValue)}
          nodeId={nodeId}
          placeholder="e.g., parent_var * 2 + 5"
          compact
        />
      );
    }

    if (inputType === 'lookup') {
      const lookupValue =
        typeof value === 'object' && value !== null && 'lookup' in value
          ? (value as LookupValue)
          : { lookup: '', key: '', default: 0 };
      return (
        <div className="space-y-2">
          <input
            type="text"
            value={lookupValue.lookup}
            onChange={(e) => handleChange({ ...lookupValue, lookup: e.target.value })}
            placeholder="Lookup table name"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
          <input
            type="text"
            value={lookupValue.key}
            onChange={(e) => handleChange({ ...lookupValue, key: e.target.value })}
            placeholder="Key field"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
          <input
            type="number"
            value={lookupValue.default || 0}
            onChange={(e) =>
              handleChange({ ...lookupValue, default: parseFloat(e.target.value) || 0 })
            }
            placeholder="Default value"
            step="any"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
      );
    }

    return null;
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">{label}</label>
        {description && (
          <span className="text-xs text-gray-400" title={description}>
            ?
          </span>
        )}
      </div>

      {/* Input Type Toggle */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-md">
        <button
          type="button"
          onClick={() => handleTypeChange('literal')}
          className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
            inputType === 'literal'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Literal
        </button>
        <button
          type="button"
          onClick={() => handleTypeChange('formula')}
          className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
            inputType === 'formula'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Formula
        </button>
        <button
          type="button"
          onClick={() => handleTypeChange('lookup')}
          className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
            inputType === 'lookup'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Lookup
        </button>
      </div>

      {/* Actual Input */}
      {renderInput()}
    </div>
  );
};

// Separate component for categorical inputs to avoid stale closure issues
const CategoricalInputs: React.FC<{ nodeId: string }> = ({ nodeId }) => {
  const categories = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    const cats = node?.data.config.distribution?.params.categories;
    return typeof cats === 'string' ? cats : '';
  });

  const probs = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    const p = node?.data.config.distribution?.params.probs;
    return typeof p === 'string' ? p : '';
  });

  const updateNode = useDAGStore((state) => state.updateNode);

  const handleChange = useCallback(
    (paramName: string, value: string) => {
      const state = useDAGStore.getState();
      const node = state.nodes.find((n) => n.id === nodeId);
      const currentDist = node?.data.config.distribution || { type: 'categorical', params: {} };

      updateNode(nodeId, {
        distribution: {
          ...currentDist,
          params: {
            ...currentDist.params,
            [paramName]: value,
          },
        },
      });
    },
    [nodeId, updateNode]
  );

  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Categories (comma-separated)
        </label>
        <input
          type="text"
          value={categories}
          onChange={(e) => handleChange('categories', e.target.value)}
          placeholder="A,B,C"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Probabilities (comma-separated, must sum to 1)
        </label>
        <input
          type="text"
          value={probs}
          onChange={(e) => handleChange('probs', e.target.value)}
          placeholder="0.33,0.33,0.34"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
      </div>
    </>
  );
};

// Default parameters for common distributions
const DEFAULT_PARAMS: Record<string, Record<string, ParamValue>> = {
  normal: { mu: 0, sigma: 1 },
  uniform: { low: 0, high: 1 },
  categorical: { categories: 'A,B,C', probs: '0.33,0.33,0.34' },
  bernoulli: { p: 0.5 },
  poisson: { lam: 1 },
  exponential: { scale: 1 },
  beta: { a: 2, b: 2 },
  gamma: { shape: 2, scale: 1 },
  lognormal: { mean: 0, sigma: 1 },
  binomial: { n: 10, p: 0.5 },
  triangular: { left: 0, mode: 0.5, right: 1 },
  weibull: { a: 1, scale: 1 },
  chisquare: { df: 2 },
  student_t: { df: 10, loc: 0, scale: 1 },
};

export const DistributionForm: React.FC<DistributionFormProps> = ({ nodeId }) => {
  const updateNode = useDAGStore((state) => state.updateNode);

  // Read distribution directly from store to avoid stale props
  const distribution = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.distribution || { type: 'normal', params: { mu: 0, sigma: 1 } };
  });

  // Distribution data
  const [commonDistributions, setCommonDistributions] = useState<DistributionInfo[]>([]);
  const [searchResults, setSearchResults] = useState<DistributionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<number | null>(null);

  // Fetch common distributions on mount
  useEffect(() => {
    distributionsApi
      .getAll()
      .then(setCommonDistributions)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    if (searchTimeoutRef.current !== null) {
      clearTimeout(searchTimeoutRef.current);
    }

    setIsSearching(true);
    searchTimeoutRef.current = window.setTimeout(async () => {
      try {
        const results = await distributionsApi.search(searchQuery.trim());
        setSearchResults(results);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current !== null) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery]);

  // Find current distribution info
  const currentDistInfo = useMemo(() => {
    const allDists = [...commonDistributions, ...searchResults];
    return allDists.find((d) => d.name === distribution.type);
  }, [commonDistributions, searchResults, distribution.type]);

  const handleDistributionSelect = (distInfo: DistributionInfo) => {
    // Get default params (either from our defaults or from the distribution info)
    let defaultParams: Record<string, ParamValue> = DEFAULT_PARAMS[distInfo.name] || {};

    // If no predefined defaults, use defaults from the distribution info
    if (Object.keys(defaultParams).length === 0 && distInfo.parameters) {
      defaultParams = {};
      for (const param of distInfo.parameters) {
        if (param.default !== undefined) {
          defaultParams[param.name] = param.default as ParamValue;
        } else if (param.required) {
          defaultParams[param.name] = param.type === 'float' || param.type === 'int' ? 1 : '';
        }
      }
    }

    updateNode(nodeId, {
      distribution: { type: distInfo.name, params: defaultParams },
    });
    setIsDropdownOpen(false);
    setSearchQuery('');
  };

  const renderDistributionParams = () => {
    // Special case for categorical
    if (distribution.type === 'categorical') {
      return <CategoricalInputs key={`${nodeId}-categorical`} nodeId={nodeId} />;
    }

    // If we have distribution info from API, render params dynamically
    if (currentDistInfo?.parameters) {
      return currentDistInfo.parameters.map((param) => (
        <ParamInput
          key={`${nodeId}-${distribution.type}-${param.name}`}
          label={param.name}
          paramName={param.name}
          nodeId={nodeId}
          placeholder={param.default?.toString()}
          min={param.min_value}
          max={param.max_value}
          description={param.description}
        />
      ));
    }

    // Fallback: render based on known distributions
    const keyPrefix = `${nodeId}-${distribution.type}`;
    switch (distribution.type) {
      case 'normal':
        return (
          <>
            <ParamInput
              key={`${keyPrefix}-mu`}
              label="mu"
              paramName="mu"
              nodeId={nodeId}
              placeholder="0"
            />
            <ParamInput
              key={`${keyPrefix}-sigma`}
              label="sigma"
              paramName="sigma"
              nodeId={nodeId}
              placeholder="1"
              min={0}
            />
          </>
        );
      case 'uniform':
        return (
          <>
            <ParamInput
              key={`${keyPrefix}-low`}
              label="low"
              paramName="low"
              nodeId={nodeId}
              placeholder="0"
            />
            <ParamInput
              key={`${keyPrefix}-high`}
              label="high"
              paramName="high"
              nodeId={nodeId}
              placeholder="1"
            />
          </>
        );
      case 'bernoulli':
        return (
          <ParamInput
            key={`${keyPrefix}-p`}
            label="p"
            paramName="p"
            nodeId={nodeId}
            placeholder="0.5"
            min={0}
            max={1}
            step={0.01}
          />
        );
      default:
        // For unknown distributions, try to render any existing params
        const paramKeys = Object.keys(distribution.params || {});
        if (paramKeys.length > 0) {
          return paramKeys.map((param) => (
            <ParamInput
              key={`${keyPrefix}-${param}`}
              label={param}
              paramName={param}
              nodeId={nodeId}
            />
          ));
        }
        return (
          <div className="text-sm text-gray-500 italic">No parameters for this distribution</div>
        );
    }
  };

  // Group distributions by category
  const groupedDistributions = useMemo(() => {
    const groups: Record<string, DistributionInfo[]> = {
      continuous: [],
      discrete: [],
      categorical: [],
    };
    for (const dist of commonDistributions) {
      if (groups[dist.category]) {
        groups[dist.category].push(dist);
      }
    }
    return groups;
  }, [commonDistributions]);

  // Display name for current distribution
  const currentDisplayName = currentDistInfo?.display_name || distribution.type;

  return (
    <div className="space-y-4">
      <div className="border-b border-gray-200 pb-2">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
          Distribution Configuration
        </h3>
      </div>

      {/* Distribution Selector */}
      <div ref={dropdownRef} className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-1">Distribution Type</label>

        {/* Selected distribution button */}
        <button
          type="button"
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="w-full px-3 py-2 text-left border border-gray-300 rounded-md shadow-sm bg-white hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm flex items-center justify-between"
        >
          <span>{currentDisplayName}</span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Dropdown */}
        {isDropdownOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-hidden">
            {/* Search input */}
            <div className="p-2 border-b border-gray-200">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search distributions..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                autoFocus
              />
            </div>

            {/* Distribution list */}
            <div className="max-h-60 overflow-y-auto">
              {isLoading ? (
                <div className="p-4 text-sm text-gray-500 text-center">Loading...</div>
              ) : searchQuery.trim() ? (
                // Search results
                <>
                  {isSearching && (
                    <div className="p-2 text-sm text-gray-500 text-center">Searching...</div>
                  )}
                  {!isSearching && searchResults.length === 0 && (
                    <div className="p-4 text-sm text-gray-500 text-center">No results found</div>
                  )}
                  {searchResults.map((dist) => (
                    <button
                      key={dist.name}
                      type="button"
                      onClick={() => handleDistributionSelect(dist)}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-blue-50 flex items-center justify-between ${
                        distribution.type === dist.name ? 'bg-blue-50 text-blue-700' : ''
                      }`}
                    >
                      <span>{dist.display_name}</span>
                      <span className="text-xs text-gray-400">{dist.category}</span>
                    </button>
                  ))}
                </>
              ) : (
                // Common distributions grouped by category
                <>
                  {Object.entries(groupedDistributions).map(
                    ([category, dists]) =>
                      dists.length > 0 && (
                        <div key={category}>
                          <div className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase bg-gray-50">
                            {category}
                          </div>
                          {dists.map((dist) => (
                            <button
                              key={dist.name}
                              type="button"
                              onClick={() => handleDistributionSelect(dist)}
                              className={`w-full px-3 py-2 text-left text-sm hover:bg-blue-50 ${
                                distribution.type === dist.name ? 'bg-blue-50 text-blue-700' : ''
                              }`}
                            >
                              {dist.display_name}
                            </button>
                          ))}
                        </div>
                      )
                  )}
                  <div className="px-3 py-2 text-xs text-gray-400 border-t border-gray-200 bg-gray-50">
                    Type to search more distributions from scipy...
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Distribution description */}
      {currentDistInfo?.description && (
        <p className="text-xs text-gray-500">{currentDistInfo.description}</p>
      )}

      {/* Distribution Parameters */}
      <div className="space-y-4">{renderDistributionParams()}</div>

      {/* Help Text */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
        <p className="text-xs text-blue-800">
          <strong>Tip:</strong> Parameters can be literal values, formulas referencing other nodes,
          or lookups from context tables. Use the toggle buttons to switch between input modes.
        </p>
      </div>
    </div>
  );
};
