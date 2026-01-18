import { useState } from 'react';
import { useDAGStore, selectValidationErrors } from '../../stores/dagStore';

interface ValidationError {
  code: string;
  message: string;
  nodeId?: string;
  severity: 'error' | 'warning';
}

const parseValidationError = (error: string): ValidationError => {
  // Try to parse structured error format like: [ERROR:NODE_ID] message
  const errorMatch = error.match(/^\[(ERROR|WARNING):([^\]]+)\]\s*(.+)$/);
  if (errorMatch) {
    return {
      code: errorMatch[2],
      message: errorMatch[3],
      nodeId: errorMatch[2],
      severity: errorMatch[1].toLowerCase() as 'error' | 'warning',
    };
  }

  // Try to parse node reference
  const nodeMatch = error.match(/node[:\s]+['"]?([^'":\s]+)['"]?/i);
  const nodeId = nodeMatch ? nodeMatch[1] : undefined;

  // Determine severity
  const severity = error.toLowerCase().includes('warning') ? 'warning' : 'error';

  return {
    code: 'VALIDATION_ERROR',
    message: error,
    nodeId,
    severity,
  };
};

export const ValidationPanel = () => {
  const validationErrors = useDAGStore(selectValidationErrors);
  const selectNode = useDAGStore((state) => state.selectNode);
  const [isExpanded, setIsExpanded] = useState(true);

  if (!validationErrors || validationErrors.length === 0) {
    return null;
  }

  const parsedErrors = validationErrors.map(parseValidationError);
  const errors = parsedErrors.filter((e) => e.severity === 'error');
  const warnings = parsedErrors.filter((e) => e.severity === 'warning');

  const handleErrorClick = (error: ValidationError) => {
    if (error.nodeId) {
      selectNode(error.nodeId);
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="font-medium text-gray-900">Validation Issues</span>
          <span className="text-xs text-gray-500">
            ({errors.length} {errors.length === 1 ? 'error' : 'errors'}
            {warnings.length > 0 &&
              `, ${warnings.length} ${warnings.length === 1 ? 'warning' : 'warnings'}`}
            )
          </span>
        </div>
        <span className="text-xs text-gray-400">{isExpanded ? 'Collapse' : 'Expand'}</span>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2 max-h-40 overflow-y-auto">
          {errors.length > 0 && (
            <div className="space-y-1">
              {errors.map((error, index) => (
                <div
                  key={`error-${index}`}
                  className={`flex items-start gap-2 p-2 rounded text-sm ${
                    error.nodeId
                      ? 'bg-red-50 border border-red-200 cursor-pointer hover:bg-red-100 transition-colors'
                      : 'bg-red-50 border border-red-200'
                  }`}
                  onClick={() => handleErrorClick(error)}
                >
                  <svg
                    className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-xs text-red-700 mb-0.5">{error.code}</div>
                    <div className="text-red-900">{error.message}</div>
                    {error.nodeId && (
                      <div className="text-xs text-red-600 mt-1">
                        Click to highlight node: {error.nodeId}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="space-y-1">
              {warnings.map((warning, index) => (
                <div
                  key={`warning-${index}`}
                  className={`flex items-start gap-2 p-2 rounded text-sm ${
                    warning.nodeId
                      ? 'bg-yellow-50 border border-yellow-200 cursor-pointer hover:bg-yellow-100 transition-colors'
                      : 'bg-yellow-50 border border-yellow-200'
                  }`}
                  onClick={() => handleErrorClick(warning)}
                >
                  <svg
                    className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-xs text-yellow-700 mb-0.5">{warning.code}</div>
                    <div className="text-yellow-900">{warning.message}</div>
                    {warning.nodeId && (
                      <div className="text-xs text-yellow-600 mt-1">
                        Click to highlight node: {warning.nodeId}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
