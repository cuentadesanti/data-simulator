import React, { useMemo } from 'react';
import { useDAGStore } from '../../stores/dagStore';
import { getEffectiveVarName } from '../../types/dag';

interface InputChipsProps {
  nodeId: string;
  onInsert: (text: string) => void;
}

export const InputChips: React.FC<InputChipsProps> = ({ nodeId, onInsert }) => {
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);

  const parentVars = useMemo(() => {
    const parentIds = new Set(edges.filter((e) => e.target === nodeId).map((e) => e.source));
    return nodes
      .filter((n) => parentIds.has(n.id))
      .map((n) => getEffectiveVarName(n.data.config));
  }, [nodeId, edges, nodes]);

  const contextKeys = useMemo(() => Object.keys(context), [context]);

  const hasChips = parentVars.length > 0 || contextKeys.length > 0;

  if (!hasChips) return null;

  return (
    <div className="flex flex-wrap items-center gap-1 text-xs">
      <span className="text-gray-400 mr-0.5">Inputs:</span>
      {parentVars.map((varName) => (
        <button
          key={varName}
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onInsert(varName)}
          className="px-1.5 py-0.5 font-mono bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
        >
          {varName}
        </button>
      ))}
      {contextKeys.map((key) => (
        <button
          key={key}
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onInsert(key)}
          className="px-1.5 py-0.5 font-mono bg-purple-50 text-purple-700 border border-purple-200 rounded hover:bg-purple-100 transition-colors"
        >
          {key}
        </button>
      ))}
      {['PI', 'E'].map((c) => (
        <button
          key={c}
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => onInsert(c)}
          className="px-1.5 py-0.5 font-mono bg-gray-100 text-gray-600 border border-gray-200 rounded hover:bg-gray-200 transition-colors"
        >
          {c}
        </button>
      ))}
    </div>
  );
};
