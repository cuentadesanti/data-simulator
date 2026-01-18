import React from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { BasicInfo } from './BasicInfo';
import { DistributionForm } from './DistributionForm';
import { FormulaEditor } from './FormulaEditor';
import { PostProcessing } from './PostProcessing';
import { AvailableInputs } from './AvailableInputs';

export const NodeEditor: React.FC = () => {
  const selectedNodeId = useDAGStore((state) => state.selectedNodeId);
  const selectNode = useDAGStore((state) => state.selectNode);

  // Subscribe to the actual node data so we re-render when it changes
  const selectedNode = useDAGStore((state) => {
    if (!state.selectedNodeId) return null;
    const node = state.nodes.find((n) => n.id === state.selectedNodeId);
    return node?.data.config || null;
  });

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

  return (
    <div className="w-full max-w-md h-full bg-white border-l border-gray-200 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Node Editor</h2>
          <p className="text-sm text-gray-600 mt-0.5">{selectedNode.id}</p>
        </div>
        <button
          onClick={() => selectNode(null)}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          title="Close editor"
        >
          <svg
            className="w-5 h-5 text-gray-600"
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

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <BasicInfo nodeId={selectedNodeId!} config={selectedNode} />

          {/* Available Inputs - Shows parent nodes from edges */}
          <AvailableInputs nodeId={selectedNodeId!} />

          {/* Kind-specific editors */}
          {selectedNode.kind === 'stochastic' && <DistributionForm nodeId={selectedNodeId!} />}

          {selectedNode.kind === 'deterministic' && <FormulaEditor nodeId={selectedNodeId!} />}

          {/* Post-processing */}
          <PostProcessing nodeId={selectedNodeId!} config={selectedNode} />
        </div>
      </div>
    </div>
  );
};
