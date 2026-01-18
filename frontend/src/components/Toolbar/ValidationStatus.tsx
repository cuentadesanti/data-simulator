import React, { useState, useRef, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Plus, Link } from 'lucide-react';
import { useDAGStore, selectMissingEdges, selectEdgeStatuses } from '../../stores/dagStore';

export const ValidationStatus: React.FC = () => {
  const [showDetails, setShowDetails] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { validationErrors, addEdge } = useDAGStore();
  const missingEdges = useDAGStore(selectMissingEdges);
  const edgeStatuses = useDAGStore(selectEdgeStatuses);

  // Parse validation errors to separate errors and warnings
  const errors = validationErrors.filter((msg) => !msg.toLowerCase().includes('warning'));
  const warnings = validationErrors.filter((msg) => msg.toLowerCase().includes('warning'));

  // Count unused edges
  const unusedEdges = edgeStatuses.filter((e) => e.status === 'unused');

  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0 || unusedEdges.length > 0;
  const isValid = !hasErrors && !hasWarnings;

  // Handler to add a missing edge
  const handleAddMissingEdge = (source: string, target: string) => {
    addEdge(source, target);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDetails(false);
      }
    };

    if (showDetails) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDetails]);

  // Track if validation has been run (edge statuses are populated after validation)
  const hasValidated = edgeStatuses.length > 0 || validationErrors.length > 0;

  // Don't show anything if no validation has been run yet
  if (!hasValidated) {
    return null;
  }

  // Determine if there's content to show in dropdown
  const hasDropdownContent =
    hasErrors || missingEdges.length > 0 || unusedEdges.length > 0 || warnings.length > 0;

  // Calculate total issues for display
  const errorCount = errors.length + missingEdges.length;
  const warningCount = warnings.length + unusedEdges.length;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Status Button */}
      <button
        onClick={() => hasDropdownContent && setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded transition-colors ${
          isValid && unusedEdges.length === 0
            ? 'bg-green-100 text-green-700 hover:bg-green-200'
            : hasErrors || missingEdges.length > 0
              ? 'bg-red-100 text-red-700 hover:bg-red-200 cursor-pointer'
              : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 cursor-pointer'
        }`}
      >
        {isValid && unusedEdges.length === 0 && (
          <>
            <CheckCircle size={16} />
            <span className="text-sm font-medium">Valid</span>
          </>
        )}
        {(hasErrors || missingEdges.length > 0) && (
          <>
            <XCircle size={16} />
            <span className="text-sm font-medium">
              {errorCount} Error{errorCount > 1 ? 's' : ''}
            </span>
          </>
        )}
        {!hasErrors &&
          missingEdges.length === 0 &&
          (unusedEdges.length > 0 || warnings.length > 0) && (
            <>
              <AlertTriangle size={16} />
              <span className="text-sm font-medium">
                {warningCount} Warning{warningCount > 1 ? 's' : ''}
              </span>
            </>
          )}
      </button>

      {/* Error/Warning Details Dropdown */}
      {showDetails && hasDropdownContent && (
        <div className="absolute top-full right-0 mt-1 w-96 max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="p-4">
            {/* Errors Section */}
            {hasErrors && (
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-2">
                  <XCircle size={16} />
                  Errors ({errors.length})
                </h3>
                <ul className="space-y-2">
                  {errors.map((error, index) => (
                    <li
                      key={`error-${index}`}
                      className="text-xs text-gray-800 bg-red-50 p-2 rounded border border-red-200"
                    >
                      {error}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Missing Edges Section */}
            {missingEdges.length > 0 && (
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-2">
                  <Link size={16} />
                  Missing Edges ({missingEdges.length})
                </h3>
                <ul className="space-y-2">
                  {missingEdges.map((edge, index) => (
                    <li
                      key={`missing-${index}`}
                      className="text-xs bg-red-50 p-2 rounded border border-red-200 flex items-center justify-between"
                    >
                      <span className="text-gray-800 font-mono">
                        {edge.source} → {edge.target}
                      </span>
                      <button
                        onClick={() => handleAddMissingEdge(edge.source, edge.target)}
                        className="flex items-center gap-1 px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-xs"
                      >
                        <Plus size={12} />
                        Add Edge
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Unused Edges Section */}
            {unusedEdges.length > 0 && (
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-amber-700 mb-2 flex items-center gap-2">
                  <AlertTriangle size={16} />
                  Unused Edges ({unusedEdges.length})
                </h3>
                <ul className="space-y-2">
                  {unusedEdges.map((edge, index) => (
                    <li
                      key={`unused-${index}`}
                      className="text-xs text-gray-800 bg-amber-50 p-2 rounded border border-amber-200"
                    >
                      <span className="font-mono">
                        {edge.source} → {edge.target}
                      </span>
                      <span className="text-gray-500 ml-2">— {edge.reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings Section */}
            {warnings.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-yellow-700 mb-2 flex items-center gap-2">
                  <AlertTriangle size={16} />
                  Warnings ({warnings.length})
                </h3>
                <ul className="space-y-2">
                  {warnings.map((warning, index) => (
                    <li
                      key={`warning-${index}`}
                      className="text-xs text-gray-800 bg-yellow-50 p-2 rounded border border-yellow-200"
                    >
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
