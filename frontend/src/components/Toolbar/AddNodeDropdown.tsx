import React, { useState, useRef, useEffect } from 'react';
import { Plus, ChevronDown } from 'lucide-react';
import { useDAGStore } from '../../stores/dagStore';
import { COMMON_DISTRIBUTIONS } from '../../types/distribution';

export const AddNodeDropdown: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { addNode, nodes } = useDAGStore();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Calculate staggered position for new nodes
  const getNewNodePosition = () => {
    const nodeCount = nodes.length;
    const baseX = 250;
    const baseY = 150;
    const offsetX = (nodeCount % 4) * 200;
    const offsetY = Math.floor(nodeCount / 4) * 150;

    return {
      x: baseX + offsetX,
      y: baseY + offsetY,
    };
  };

  const handleAddStochastic = () => {
    const position = getNewNodePosition();
    addNode(
      {
        name: `Stochastic ${nodes.length + 1}`,
        kind: 'stochastic',
        dtype: 'float',
        scope: 'row',
        distribution: COMMON_DISTRIBUTIONS.normal,
      },
      position
    );
    setIsOpen(false);
  };

  const handleAddDeterministic = () => {
    const position = getNewNodePosition();
    addNode(
      {
        name: `Deterministic ${nodes.length + 1}`,
        kind: 'deterministic',
        dtype: 'float',
        scope: 'row',
        formula: '',
      },
      position
    );
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
      >
        <Plus size={16} />
        <span className="text-sm font-medium">Add Node</span>
        <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="py-1">
            {/* Add Stochastic Node */}
            <button
              onClick={handleAddStochastic}
              className="w-full px-4 py-2 text-left hover:bg-gray-100 transition-colors"
            >
              <div className="text-sm font-medium text-gray-900">Add Stochastic Node</div>
              <div className="text-xs text-gray-500 mt-0.5">Random variable with distribution</div>
            </button>

            {/* Divider */}
            <div className="border-t border-gray-200 my-1" />

            {/* Add Deterministic Node */}
            <button
              onClick={handleAddDeterministic}
              className="w-full px-4 py-2 text-left hover:bg-gray-100 transition-colors"
            >
              <div className="text-sm font-medium text-gray-900">Add Deterministic Node</div>
              <div className="text-xs text-gray-500 mt-0.5">Computed from formula</div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
