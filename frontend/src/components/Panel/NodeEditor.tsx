import React, { useMemo, useRef } from 'react';
import type { NodeConfig, NodeKind, NodeDtype, NodeScope } from '../../types/dag';
import { getEffectiveVarName } from '../../types/dag';
import { useDAGStore } from '../../stores/dagStore';
import { Dropdown } from '../common/Dropdown';
import { DistributionForm } from './DistributionForm';
import { FormulaEditor } from './FormulaEditor';
import { PostProcessing } from './PostProcessing';

const DTYPE_OPTIONS = [
  { value: 'float' as NodeDtype, label: 'Float' },
  { value: 'int' as NodeDtype, label: 'Int' },
  { value: 'category' as NodeDtype, label: 'Category' },
  { value: 'bool' as NodeDtype, label: 'Bool' },
  { value: 'string' as NodeDtype, label: 'String' },
];

const SCOPE_OPTIONS = [
  { value: 'row' as NodeScope, label: 'Row' },
  { value: 'global' as NodeScope, label: 'Global' },
  { value: 'group' as NodeScope, label: 'Group' },
];

export const NodeEditor: React.FC = () => {
  const selectedNodeId = useDAGStore((state) => state.selectedNodeId);
  const selectNode = useDAGStore((state) => state.selectNode);
  const updateNode = useDAGStore((state) => state.updateNode);
  const nodes = useDAGStore((state) => state.nodes);

  const selectedNode = useDAGStore((state) => {
    if (!state.selectedNodeId) return null;
    const node = state.nodes.find((n) => n.id === state.selectedNodeId);
    return node?.data.config || null;
  });

  const effectiveVarName = useMemo(
    () => (selectedNode ? getEffectiveVarName(selectedNode) : ''),
    [selectedNode]
  );

  const categoricalNodes = useMemo(
    () =>
      nodes
        .filter((n) => n.data.config.dtype === 'category' && n.id !== selectedNodeId)
        .map((n) => n.data.config),
    [nodes, selectedNodeId]
  );

  const groupByOptions = useMemo(
    () => [
      { value: '', label: 'Group by...' },
      ...categoricalNodes.map((n) => ({ value: n.id, label: n.name })),
    ],
    [categoricalNodes]
  );

  // Cache formula/distribution during kind toggles (same node, same editing session)
  const cachedFormulaRef = useRef<{ nodeId: string; formula: string } | null>(null);
  const cachedDistributionRef = useRef<{ nodeId: string; distribution: NodeConfig['distribution'] } | null>(null);

  if (!selectedNode) {
    return (
      <div className="w-full max-w-md h-full bg-white border-l border-gray-200 flex items-center justify-center">
        <div className="text-center text-gray-500 p-8">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-lg font-medium">Select a node</p>
          <p className="text-sm mt-2">Click on a node to edit its properties</p>
        </div>
      </div>
    );
  }

  const handleChange = (field: keyof NodeConfig, value: unknown) => {
    const updates: Partial<NodeConfig> = { [field]: value };

    if (field === 'scope' && value !== 'group') {
      updates.group_by = undefined;
    }

    if (field === 'kind' && value === 'deterministic') {
      // Cache distribution before clearing
      if (selectedNode.distribution) {
        cachedDistributionRef.current = { nodeId: selectedNodeId!, distribution: selectedNode.distribution };
      }
      updates.distribution = undefined;
      // Restore formula if cached for this node, otherwise empty
      const cached = cachedFormulaRef.current;
      updates.formula = (cached && cached.nodeId === selectedNodeId) ? cached.formula : '';
    }

    if (field === 'kind' && value === 'stochastic') {
      // Cache formula before clearing
      if (selectedNode.formula) {
        cachedFormulaRef.current = { nodeId: selectedNodeId!, formula: selectedNode.formula };
      }
      updates.formula = undefined;
      // Restore distribution if cached for this node, otherwise defaults
      const cached = cachedDistributionRef.current;
      updates.distribution = (cached && cached.nodeId === selectedNodeId)
        ? cached.distribution
        : { type: 'normal', params: { mu: 0, sigma: 1 } };
    }

    updateNode(selectedNodeId!, updates);
  };

  const handleKindChange = (kind: NodeKind) => {
    if (kind !== selectedNode.kind) {
      handleChange('kind', kind);
    }
  };

  return (
    <div className="w-full max-w-md h-full bg-white border-l border-gray-200 flex flex-col">
      {/* Header: name input + close */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200">
        <input
          type="text"
          value={selectedNode.name}
          onChange={(e) => handleChange('name', e.target.value)}
          aria-label="Node name"
          className="flex-1 text-base font-semibold text-gray-900 bg-transparent border-none outline-none focus:ring-0 p-0 placeholder-gray-400"
          placeholder="Node name"
        />
        <button
          onClick={() => selectNode(null)}
          className="p-1.5 hover:bg-gray-100 rounded-md transition-colors flex-shrink-0"
          title="Close editor"
        >
          <svg
            className="w-4 h-4 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-4 py-3 space-y-4">
          {/* Var name preview */}
          <div className="text-xs font-mono text-gray-400">
            var: {effectiveVarName}
          </div>

          {/* Meta row: kind toggle + dtype + scope */}
          <div className="flex items-center gap-2">
            {/* Kind toggle */}
            <div className="flex rounded-md border border-gray-200 text-xs overflow-hidden">
              <button
                type="button"
                role="button"
                aria-pressed={selectedNode.kind === 'stochastic'}
                className={
                  selectedNode.kind === 'stochastic'
                    ? 'px-2.5 py-1 bg-blue-50 text-blue-700 font-medium border-r border-gray-200'
                    : 'px-2.5 py-1 text-gray-600 hover:bg-gray-50 border-r border-gray-200'
                }
                onClick={() => handleKindChange('stochastic')}
              >
                Stoch
              </button>
              <button
                type="button"
                role="button"
                aria-pressed={selectedNode.kind === 'deterministic'}
                className={
                  selectedNode.kind === 'deterministic'
                    ? 'px-2.5 py-1 bg-blue-50 text-blue-700 font-medium'
                    : 'px-2.5 py-1 text-gray-600 hover:bg-gray-50'
                }
                onClick={() => handleKindChange('deterministic')}
              >
                Det
              </button>
            </div>

            {/* Dtype dropdown */}
            <Dropdown<NodeDtype>
              options={DTYPE_OPTIONS}
              value={selectedNode.dtype || 'float'}
              onChange={(val) => handleChange('dtype', val)}
              size="sm"
              className="flex-1"
            />

            {/* Scope dropdown */}
            <Dropdown<NodeScope>
              options={SCOPE_OPTIONS}
              value={selectedNode.scope}
              onChange={(val) => handleChange('scope', val)}
              size="sm"
              className="flex-1"
            />
          </div>

          {/* Group-by row (conditional) */}
          {selectedNode.scope === 'group' && (
            <div>
              {categoricalNodes.length === 0 ? (
                <div className="px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-md text-xs text-yellow-800">
                  No categorical nodes available for group_by.
                </div>
              ) : (
                <Dropdown
                  options={groupByOptions}
                  value={selectedNode.group_by || ''}
                  onChange={(val) => handleChange('group_by', val || undefined)}
                  size="sm"
                  placeholder="Group by..."
                />
              )}
            </div>
          )}

          {/* Kind-specific section */}
          {selectedNode.kind === 'stochastic' && <DistributionForm nodeId={selectedNodeId!} />}
          {selectedNode.kind === 'deterministic' && <FormulaEditor nodeId={selectedNodeId!} />}

          {/* Post-processing */}
          <PostProcessing nodeId={selectedNodeId!} config={selectedNode} />
        </div>
      </div>
    </div>
  );
};
