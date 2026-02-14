import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { ParamValue } from '../../types/dag';
import type { DistributionInfo } from '../../services/api';
import { useDAGStore } from '../../stores/dagStore';
import { distributionsApi } from '../../services/api';
import { FormulaInput } from './FormulaInput';
import { InputChips } from './InputChips';

interface DistributionFormProps {
  nodeId: string;
}

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

const parseParamValue = (text: string): ParamValue => {
  const trimmed = text.trim();
  if (trimmed === '') return '';
  const num = Number(trimmed);
  return isFinite(num) ? num : trimmed;
};

/** Single param input — uses FormulaInput for autocomplete, parses on blur */
const ParamField: React.FC<{
  paramName: string;
  nodeId: string;
  distributionType: string;
  onFocus: (paramName: string) => void;
}> = ({ paramName, nodeId, distributionType, onFocus }) => {
  const storeValue = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.distribution?.params[paramName];
  });
  const updateNode = useDAGStore((state) => state.updateNode);

  // Local string state for editing — no store writes on keystroke
  const [localText, setLocalText] = useState(() =>
    storeValue !== undefined ? String(storeValue) : ''
  );
  const isEditingRef = useRef(false);

  // Sync from store when not actively editing (e.g. distribution type change, chip insert)
  useEffect(() => {
    if (!isEditingRef.current) {
      setLocalText(storeValue !== undefined ? String(storeValue) : '');
    }
  }, [storeValue]);

  const commitValue = useCallback(() => {
    isEditingRef.current = false;
    const parsed = parseParamValue(localText);
    const state = useDAGStore.getState();
    const node = state.nodes.find((n) => n.id === nodeId);
    const currentDist = node?.data.config.distribution || { type: distributionType, params: {} };

    updateNode(nodeId, {
      distribution: {
        ...currentDist,
        params: {
          ...currentDist.params,
          [paramName]: parsed,
        },
      },
    });
  }, [localText, nodeId, paramName, distributionType, updateNode]);

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs font-mono text-gray-500 w-14 text-right flex-shrink-0">
        {paramName}
      </label>
      <div className="flex-1">
        <FormulaInput
          value={localText}
          onChange={(val) => {
            isEditingRef.current = true;
            setLocalText(val);
          }}
          nodeId={nodeId}
          placeholder="0"
          compact
          onFocusCapture={() => onFocus(paramName)}
          onBlurCapture={commitValue}
        />
      </div>
    </div>
  );
};

/** Categorical-specific inputs (categories & probs as comma-separated text) */
const CategoricalFields: React.FC<{ nodeId: string }> = ({ nodeId }) => {
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
      <div className="flex items-center gap-2">
        <label className="text-xs font-mono text-gray-500 w-14 text-right flex-shrink-0">
          cats
        </label>
        <input
          type="text"
          value={categories}
          onChange={(e) => handleChange('categories', e.target.value)}
          placeholder="A,B,C"
          className="flex-1 px-2 py-1.5 border border-gray-200 rounded-md text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs font-mono text-gray-500 w-14 text-right flex-shrink-0">
          probs
        </label>
        <input
          type="text"
          value={probs}
          onChange={(e) => handleChange('probs', e.target.value)}
          placeholder="0.33,0.33,0.34"
          className="flex-1 px-2 py-1.5 border border-gray-200 rounded-md text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </>
  );
};

export const DistributionForm: React.FC<DistributionFormProps> = ({ nodeId }) => {
  const updateNode = useDAGStore((state) => state.updateNode);

  const distribution = useDAGStore((state) => {
    const node = state.nodes.find((n) => n.id === nodeId);
    return node?.data.config.distribution || { type: 'normal', params: { mu: 0, sigma: 1 } };
  });

  // Distribution API data
  const [commonDistributions, setCommonDistributions] = useState<DistributionInfo[]>([]);
  const [searchResults, setSearchResults] = useState<DistributionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<number | null>(null);

  // Track last focused param for chip insertion
  const lastFocusedParamRef = useRef<string | null>(null);

  useEffect(() => {
    distributionsApi
      .getAll()
      .then(setCommonDistributions)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, []);

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

  const currentDistInfo = useMemo(() => {
    const allDists = [...commonDistributions, ...searchResults];
    return allDists.find((d) => d.name === distribution.type);
  }, [commonDistributions, searchResults, distribution.type]);

  const handleDistributionSelect = (distInfo: DistributionInfo) => {
    let defaultParams: Record<string, ParamValue> = DEFAULT_PARAMS[distInfo.name] || {};

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

  const currentDisplayName = currentDistInfo?.display_name || distribution.type;

  // Get param names to render
  const paramNames = useMemo(() => {
    if (distribution.type === 'categorical') return [];
    if (currentDistInfo?.parameters) {
      return currentDistInfo.parameters.map((p) => p.name);
    }
    return Object.keys(distribution.params || {});
  }, [distribution.type, distribution.params, currentDistInfo]);

  const handleParamFocus = useCallback((paramName: string) => {
    lastFocusedParamRef.current = paramName;
  }, []);

  const handleChipInsert = useCallback(
    (text: string) => {
      // Determine which param to insert into
      let targetParam = lastFocusedParamRef.current;
      if (!targetParam && paramNames.length > 0) {
        targetParam = paramNames[0];
      }
      if (!targetParam) return;

      // Get current value and append chip text
      const state = useDAGStore.getState();
      const node = state.nodes.find((n) => n.id === nodeId);
      const currentValue = node?.data.config.distribution?.params[targetParam];
      const currentText = currentValue !== undefined ? String(currentValue) : '';
      const newText = currentText + text;

      const currentDist = node?.data.config.distribution || {
        type: distribution.type,
        params: {},
      };

      updateNode(nodeId, {
        distribution: {
          ...currentDist,
          params: {
            ...currentDist.params,
            [targetParam]: newText,
          },
        },
      });
    },
    [nodeId, paramNames, distribution.type, updateNode]
  );

  const [showInfo, setShowInfo] = useState(false);

  return (
    <div className="space-y-3">
      {/* Distribution selector */}
      <div ref={dropdownRef} className="relative">
        <div className="flex items-center gap-1.5 mb-1">
          <label className="text-xs font-medium text-gray-500">Distribution</label>
          <button
            type="button"
            onClick={() => setShowInfo(!showInfo)}
            className="text-xs text-gray-400 hover:text-blue-600 leading-none"
          >
            ?
          </button>
        </div>

        {/* Info panel */}
        {showInfo && (
          <div className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-2.5 py-2 mb-2 space-y-1">
            <p>Each parameter accepts a <strong>number</strong> (e.g. <code className="text-blue-600">0.5</code>) or a <strong>formula</strong> referencing parent node variables (e.g. <code className="text-blue-600">age * 0.1</code>).</p>
            <p>Start typing to see autocomplete suggestions. Click a chip below to insert a variable name.</p>
          </div>
        )}
        <button
          type="button"
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="w-full px-2.5 py-1.5 text-left border border-gray-200 rounded-md bg-white hover:bg-gray-50 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm flex items-center justify-between"
        >
          <span>{currentDisplayName}</span>
          <svg
            className={`w-3.5 h-3.5 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isDropdownOpen && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-hidden">
            <div className="p-2 border-b border-gray-200">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search distributions..."
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                autoFocus
              />
            </div>
            <div className="max-h-60 overflow-y-auto">
              {isLoading ? (
                <div className="p-4 text-sm text-gray-500 text-center">Loading...</div>
              ) : searchQuery.trim() ? (
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

      {/* Parameters */}
      <div className="space-y-2">
        {distribution.type === 'categorical' ? (
          <CategoricalFields key={`${nodeId}-categorical`} nodeId={nodeId} />
        ) : (
          paramNames.map((pName) => (
            <ParamField
              key={`${nodeId}-${distribution.type}-${pName}`}
              paramName={pName}
              nodeId={nodeId}
              distributionType={distribution.type}
              onFocus={handleParamFocus}
            />
          ))
        )}
      </div>

      {/* InputChips */}
      {distribution.type !== 'categorical' && (
        <InputChips nodeId={nodeId} onInsert={handleChipInsert} />
      )}
    </div>
  );
};
