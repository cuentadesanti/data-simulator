import React, { useState, useMemo } from 'react';
import { HelpCircle, Edit2, Check, X } from 'lucide-react';
import type { NodeConfig, NodeKind, NodeDtype, NodeScope } from '../../types/dag';
import { toSnakeCase, getEffectiveVarName } from '../../types/dag';
import { useDAGStore } from '../../stores/dagStore';

const SCOPE_INFO: Record<NodeScope, { description: string; example: string }> = {
  row: {
    description: 'Generates one value per row. Each row gets its own independent sample.',
    example: 'age ~ Normal(35, 10) → [32, 41, 28, 39, ...]',
  },
  global: {
    description:
      'Generates a single value, broadcast to all rows. Useful for constants or shared parameters.',
    example: 'tax_rate ~ Uniform(0.1, 0.2) → [0.15, 0.15, 0.15, ...]',
  },
  group: {
    description:
      'Generates one value per unique category of the group_by node. Rows with the same category share the same value.',
    example: 'region_effect ~ Normal(0, 1) with group_by=region → {north: 0.5, south: -0.3, ...}',
  },
};

interface BasicInfoProps {
  nodeId: string;
  config: NodeConfig;
}

export const BasicInfo: React.FC<BasicInfoProps> = ({ nodeId, config }) => {
  const updateNode = useDAGStore((state) => state.updateNode);
  const nodes = useDAGStore((state) => state.nodes);
  const [showScopeHelp, setShowScopeHelp] = useState(false);
  const [isEditingVarName, setIsEditingVarName] = useState(false);
  const [tempVarName, setTempVarName] = useState('');

  // Compute effective var_name (custom or derived from name)
  const effectiveVarName = useMemo(() => getEffectiveVarName(config), [config]);
  const derivedVarName = useMemo(() => toSnakeCase(config.name), [config.name]);
  const isCustomVarName = config.var_name !== undefined && config.var_name !== '';

  // Validate var_name pattern (lowercase, underscores, starting with letter or underscore)
  const isValidVarName = (name: string) => /^[a-z_][a-z0-9_]*$/.test(name);

  // Check for duplicate var_names across all nodes
  const isDuplicateVarName = (varName: string) => {
    return nodes.some((n) => {
      if (n.id === nodeId) return false;
      return getEffectiveVarName(n.data.config) === varName;
    });
  };

  const startEditingVarName = () => {
    setTempVarName(config.var_name || derivedVarName);
    setIsEditingVarName(true);
  };

  const saveVarName = () => {
    const trimmed = tempVarName.trim();
    // If empty or same as derived, clear custom var_name
    if (!trimmed || trimmed === derivedVarName) {
      updateNode(nodeId, { var_name: undefined });
    } else if (isValidVarName(trimmed) && !isDuplicateVarName(trimmed)) {
      updateNode(nodeId, { var_name: trimmed });
    }
    setIsEditingVarName(false);
  };

  const cancelEditingVarName = () => {
    setIsEditingVarName(false);
  };

  const resetToDefault = () => {
    updateNode(nodeId, { var_name: undefined });
    setIsEditingVarName(false);
  };

  // Get available categorical nodes for group_by dropdown
  const categoricalNodes = nodes
    .filter((n) => n.data.config.dtype === 'category' && n.id !== nodeId)
    .map((n) => n.data.config);

  const handleChange = (field: keyof NodeConfig, value: unknown) => {
    const updates: Partial<NodeConfig> = { [field]: value };

    // Clear group_by if scope is not 'group'
    if (field === 'scope' && value !== 'group') {
      updates.group_by = undefined;
    }

    // Clear distribution if changing to deterministic
    if (field === 'kind' && value === 'deterministic') {
      updates.distribution = undefined;
      updates.formula = '';
    }

    // Clear formula if changing to stochastic
    if (field === 'kind' && value === 'stochastic') {
      updates.formula = undefined;
      updates.distribution = {
        type: 'normal',
        params: { mu: 0, sigma: 1 },
      };
    }

    updateNode(nodeId, updates);
  };

  return (
    <div className="space-y-4">
      <div className="border-b border-gray-200 pb-2">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
          Basic Information
        </h3>
      </div>

      {/* Node Name */}
      <div>
        <label htmlFor="node-name" className="block text-sm font-medium text-gray-700 mb-1">
          Node Name
        </label>
        <input
          id="node-name"
          type="text"
          value={config.name}
          onChange={(e) => handleChange('name', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          placeholder="Enter node name"
        />
      </div>

      {/* Variable Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Variable Name
          <span className="ml-1 text-xs text-gray-500 font-normal">
            (used in formulas & output)
          </span>
        </label>
        {isEditingVarName ? (
          <div className="space-y-2">
            <input
              type="text"
              value={tempVarName}
              onChange={(e) =>
                setTempVarName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveVarName();
                if (e.key === 'Escape') cancelEditingVarName();
              }}
              autoFocus
              className={`w-full px-3 py-2 font-mono text-sm border rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                !isValidVarName(tempVarName) || isDuplicateVarName(tempVarName)
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
              placeholder="variable_name"
            />
            {!isValidVarName(tempVarName) && (
              <p className="text-xs text-red-600">
                Must start with letter/underscore, contain only lowercase letters, numbers,
                underscores
              </p>
            )}
            {isValidVarName(tempVarName) && isDuplicateVarName(tempVarName) && (
              <p className="text-xs text-red-600">
                This variable name is already used by another node
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={saveVarName}
                disabled={!isValidVarName(tempVarName) || isDuplicateVarName(tempVarName)}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Check size={12} /> Save
              </button>
              <button
                type="button"
                onClick={cancelEditingVarName}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
              >
                <X size={12} /> Cancel
              </button>
              {isCustomVarName && (
                <button
                  type="button"
                  onClick={resetToDefault}
                  className="px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded hover:bg-blue-200"
                >
                  Reset to default
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 bg-gray-100 rounded-md text-sm font-mono text-gray-800">
              {effectiveVarName}
            </code>
            <button
              type="button"
              onClick={startEditingVarName}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
              title="Edit variable name"
            >
              <Edit2 size={14} />
            </button>
          </div>
        )}
        {!isEditingVarName && isCustomVarName && (
          <p className="mt-1 text-xs text-blue-600">
            Custom name (default: <code className="px-1 bg-gray-100 rounded">{derivedVarName}</code>
            )
          </p>
        )}
      </div>

      {/* Node Kind */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Node Kind</label>
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="radio"
              name="kind"
              value="stochastic"
              checked={config.kind === 'stochastic'}
              onChange={(e) => handleChange('kind', e.target.value as NodeKind)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
            />
            <span className="ml-2 text-sm text-gray-900">
              Stochastic <span className="text-gray-500">(random distribution)</span>
            </span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="kind"
              value="deterministic"
              checked={config.kind === 'deterministic'}
              onChange={(e) => handleChange('kind', e.target.value as NodeKind)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
            />
            <span className="ml-2 text-sm text-gray-900">
              Deterministic <span className="text-gray-500">(formula-based)</span>
            </span>
          </label>
        </div>
      </div>

      {/* Data Type */}
      <div>
        <label htmlFor="dtype" className="block text-sm font-medium text-gray-700 mb-1">
          Data Type
        </label>
        <select
          id="dtype"
          value={config.dtype || 'float'}
          onChange={(e) => handleChange('dtype', e.target.value as NodeDtype)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        >
          <option value="float">Float</option>
          <option value="int">Integer</option>
          <option value="category">Category</option>
          <option value="bool">Boolean</option>
          <option value="string">String</option>
        </select>
      </div>

      {/* Scope */}
      <div>
        <div className="flex items-center gap-1 mb-1">
          <label htmlFor="scope" className="block text-sm font-medium text-gray-700">
            Scope
          </label>
          <button
            type="button"
            onClick={() => setShowScopeHelp(!showScopeHelp)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="Learn about scopes"
          >
            <HelpCircle size={14} />
          </button>
        </div>

        {/* Scope Help Panel */}
        {showScopeHelp && (
          <div className="mb-2 p-3 bg-blue-50 border border-blue-200 rounded-md text-xs space-y-2">
            {Object.entries(SCOPE_INFO).map(([scope, info]) => (
              <div key={scope}>
                <span className="font-semibold text-blue-900 capitalize">{scope}:</span>{' '}
                <span className="text-blue-800">{info.description}</span>
                <div className="mt-0.5 text-blue-600 font-mono text-[10px]">{info.example}</div>
              </div>
            ))}
            <div className="pt-1 border-t border-blue-200 text-blue-700">
              <strong>Note:</strong> Group scope requires a categorical, row-scoped node as
              group_by.
            </div>
          </div>
        )}

        <select
          id="scope"
          value={config.scope}
          onChange={(e) => handleChange('scope', e.target.value as NodeScope)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        >
          <option value="row">Row (value per row)</option>
          <option value="global">Global (single value for all rows)</option>
          <option value="group">Group (value per group)</option>
        </select>
      </div>

      {/* Group By - Only show when scope is 'group' */}
      {config.scope === 'group' && (
        <div>
          <label htmlFor="group-by" className="block text-sm font-medium text-gray-700 mb-1">
            Group By
          </label>
          {categoricalNodes.length === 0 ? (
            <div className="px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
              No categorical nodes available. Create a categorical node first.
            </div>
          ) : (
            <select
              id="group-by"
              value={config.group_by || ''}
              onChange={(e) => handleChange('group_by', e.target.value || undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">Select a categorical node</option>
              {categoricalNodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.id})
                </option>
              ))}
            </select>
          )}
        </div>
      )}
    </div>
  );
};
