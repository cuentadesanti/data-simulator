import React from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';

interface AvailableInputsProps {
  nodeId: string;
}

export const AvailableInputs: React.FC<AvailableInputsProps> = ({ nodeId }) => {
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);

  // Get direct parents (nodes with edges pointing TO this node)
  const parentIds = new Set(edges.filter((e) => e.target === nodeId).map((e) => e.source));

  // Get parent node configs with their effective var_names
  const parentNodes = nodes
    .filter((n) => parentIds.has(n.id))
    .map((n) => ({
      ...n.data.config,
      varName: getEffectiveVarName(n.data.config),
    }));

  // Get context keys
  const contextKeys = Object.keys(context);

  const hasInputs = parentNodes.length > 0 || contextKeys.length > 0;

  return (
    <div className="space-y-3">
      <div className="border-b border-gray-200 pb-2">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          Available Inputs
        </h3>
      </div>

      {!hasInputs ? (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 text-sm text-gray-600">
          <p className="font-medium text-gray-700">No inputs connected</p>
          <p className="mt-1 text-xs text-gray-500">
            Draw edges from other nodes to this node to use them as inputs in formulas or
            distribution parameters.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Parent Nodes */}
          {parentNodes.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Parent Nodes ({parentNodes.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {parentNodes.map((node) => (
                  <div
                    key={node.id}
                    className="inline-flex items-center gap-1.5 px-2 py-1 bg-blue-50 border border-blue-200 rounded-md"
                    title={`Display name: ${node.name}`}
                  >
                    <span className="font-mono text-sm text-blue-700">{node.varName}</span>
                    <span className="text-xs text-blue-500">({node.dtype || 'unknown'})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Context Keys */}
          {contextKeys.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Context Variables ({contextKeys.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {contextKeys.map((key) => {
                  const value = context[key];
                  const isLookup = typeof value === 'object' && value !== null;
                  return (
                    <div
                      key={key}
                      className="inline-flex items-center gap-1.5 px-2 py-1 bg-purple-50 border border-purple-200 rounded-md"
                    >
                      <span className="font-mono text-sm text-purple-700">{key}</span>
                      <span className="text-xs text-purple-500">
                        ({isLookup ? 'lookup' : typeof value})
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Built-in Constants */}
          <div>
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Built-in Constants
            </div>
            <div className="flex flex-wrap gap-2">
              {['PI', 'E', 'TRUE', 'FALSE'].map((name) => (
                <div
                  key={name}
                  className="inline-flex items-center px-2 py-1 bg-gray-100 border border-gray-200 rounded-md"
                >
                  <span className="font-mono text-xs text-gray-600">{name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tip */}
      <div className="text-xs text-gray-500 mt-2 flex items-start gap-1.5">
        <svg
          className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span>
          Only variables from connected parent nodes can be used in formulas. To add a variable,
          draw an edge from that node to this one.
        </span>
      </div>
    </div>
  );
};
