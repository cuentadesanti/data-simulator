import { memo, useState, useRef, useEffect, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { MoreVertical, Trash2, Copy, Settings } from 'lucide-react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import type { FlowNodeData } from '../../types/dag';
import { getEffectiveVarName } from '../../types/dag';
import { useDAGStore } from '../../stores/dagStore';
import { distributionToLatex, formulaToLatex } from '../../utils/latex';

interface CustomNodeProps {
  data: FlowNodeData;
  selected?: boolean;
  id: string;
}

const CustomNode = memo(({ data, selected, id }: CustomNodeProps) => {
  const { config, isSelected } = data;
  const isHighlighted = selected || isSelected;
  const varName = useMemo(() => getEffectiveVarName(config), [config]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(config.name);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const deleteNode = useDAGStore((state) => state.deleteNode);
  const addNode = useDAGStore((state) => state.addNode);
  const selectNode = useDAGStore((state) => state.selectNode);
  const updateNode = useDAGStore((state) => state.updateNode);
  const nodes = useDAGStore((state) => state.nodes);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(false);
    deleteNode(id);
  };

  const handleDuplicate = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(false);

    // Find current node position
    const currentNode = nodes.find((n) => n.id === id);
    const position = currentNode?.position || { x: 100, y: 100 };

    // Create duplicate with offset position
    addNode(
      {
        ...config,
        id: undefined, // Generate new ID
        name: `${config.name} (copy)`,
      },
      { x: position.x + 50, y: position.y + 50 }
    );
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(false);
    selectNode(id);
  };

  const toggleMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpen(!menuOpen);
  };

  // Handle double-click to edit name
  const handleNameDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditedName(config.name);
    setIsEditingName(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditedName(e.target.value);
  };

  const handleNameBlur = () => {
    if (editedName.trim() && editedName !== config.name) {
      updateNode(id, { name: editedName.trim() });
    }
    setIsEditingName(false);
  };

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleNameBlur();
    } else if (e.key === 'Escape') {
      setEditedName(config.name);
      setIsEditingName(false);
    }
  };

  // Determine color scheme based on kind
  const colorScheme =
    config.kind === 'stochastic'
      ? {
          fill: 'fill-blue-100',
          stroke: 'stroke-blue-500',
          badge: 'bg-blue-200 text-blue-800',
          text: 'text-blue-900',
          textMuted: 'text-blue-700',
        }
      : {
          fill: 'fill-green-100',
          stroke: 'stroke-green-500',
          badge: 'bg-green-200 text-green-800',
          text: 'text-green-900',
          textMuted: 'text-green-700',
        };

  // Get display text for distribution/formula
  const getTypeDisplay = () => {
    if (config.kind === 'stochastic' && config.distribution) {
      return config.distribution.type;
    }
    if (config.kind === 'deterministic') {
      return 'formula';
    }
    return 'undefined';
  };

  // Render LaTeX formula
  const latexHtml = useMemo(() => {
    try {
      let latex = '';
      if (config.kind === 'stochastic' && config.distribution) {
        latex = distributionToLatex(config.distribution);
      } else if (config.kind === 'deterministic' && config.formula) {
        latex = formulaToLatex(config.formula);
      }

      if (!latex) return null;

      return katex.renderToString(latex, {
        throwOnError: false,
        displayMode: false,
        strict: false,
      });
    } catch {
      return null;
    }
  }, [config.kind, config.distribution, config.formula]);

  return (
    <div
      className={`
        relative min-w-[180px] transition-all bg-transparent
        ${isHighlighted ? 'drop-shadow-xl' : 'drop-shadow-lg'}
      `}
      style={{ background: 'transparent' }}
    >
      {/* Target Handle (top) */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-600 !border-2 !border-white !z-10"
      />

      {/* Ellipse shape using SVG background */}
      <div
        className="relative overflow-visible"
        style={{
          filter: isHighlighted ? 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.5))' : undefined,
        }}
      >
        {/* SVG Ellipse Background */}
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 180 120"
          preserveAspectRatio="none"
          style={{ overflow: 'visible' }}
        >
          <ellipse
            cx="90"
            cy="60"
            rx="89"
            ry="59"
            className={`${colorScheme.fill} ${colorScheme.stroke}`}
            strokeWidth="2"
          />
        </svg>

        {/* Content Container */}
        <div className="relative z-10 px-6 py-4 min-h-[120px] flex flex-col items-center justify-center text-center">
          {/* Header with name and menu */}
          <div className="flex items-center gap-1 mb-1 w-full justify-center">
            {isEditingName ? (
              <input
                ref={inputRef}
                type="text"
                value={editedName}
                onChange={handleNameChange}
                onBlur={handleNameBlur}
                onKeyDown={handleNameKeyDown}
                className={`font-semibold text-sm text-center bg-white/90 rounded px-1 py-0.5 outline-none ring-2 ring-blue-400 max-w-[120px] ${colorScheme.text}`}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span
                className={`font-semibold text-sm truncate max-w-[120px] cursor-text hover:bg-white/20 rounded px-1 ${colorScheme.text}`}
                onDoubleClick={handleNameDoubleClick}
                title="Double-click to edit"
              >
                {config.name}
              </span>
            )}

            {/* Three-dot menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={toggleMenu}
                className={`p-0.5 rounded hover:bg-black/10 transition-colors ${colorScheme.text}`}
                title="Options"
              >
                <MoreVertical size={14} />
              </button>

              {/* Dropdown menu */}
              {menuOpen && (
                <div className="absolute right-0 top-full mt-1 w-36 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                  <button
                    onClick={handleEdit}
                    className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                  >
                    <Settings size={14} />
                    Edit
                  </button>
                  <button
                    onClick={handleDuplicate}
                    className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                  >
                    <Copy size={14} />
                    Duplicate
                  </button>
                  <div className="border-t border-gray-100 my-1" />
                  <button
                    onClick={handleDelete}
                    className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-1 mb-1 flex-wrap justify-center">
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${colorScheme.badge}`}>
              {config.kind === 'stochastic' ? 'stoch' : 'det'}
            </span>
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-white/80 text-gray-700">
              {config.scope}
            </span>
            {config.dtype && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                {config.dtype}
              </span>
            )}
          </div>

          {/* Variable Name (for formulas) */}
          <div
            className="text-[9px] font-mono text-gray-500 bg-white/60 rounded px-1.5 py-0.5 mb-1 truncate max-w-[130px]"
            title={`Variable: ${varName}`}
          >
            {varName}
          </div>

          {/* LaTeX Formula Display */}
          {latexHtml ? (
            <div
              className="text-xs bg-white/80 rounded px-2 py-1 max-w-[150px] overflow-hidden"
              dangerouslySetInnerHTML={{ __html: latexHtml }}
            />
          ) : (
            <div className={`text-xs ${colorScheme.textMuted}`}>{getTypeDisplay()}</div>
          )}
        </div>
      </div>

      {/* Source Handle (bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-600 !border-2 !border-white !z-10"
      />
    </div>
  );
});

CustomNode.displayName = 'CustomNode';

export default CustomNode;
