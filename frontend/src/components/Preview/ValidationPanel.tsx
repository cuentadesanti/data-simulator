import { useState } from 'react';
import { useDAGStore, selectStructuredErrors } from '../../stores/dagStore';
import type { ValidationError } from '../../types/dag';

export const ValidationPanel = () => {
  const structuredErrors = useDAGStore(selectStructuredErrors);
  const selectNode = useDAGStore((state) => state.selectNode);
  const [isExpanded, setIsExpanded] = useState(true);

  if (!structuredErrors || structuredErrors.length === 0) {
    return null;
  }

  const errors = structuredErrors.filter((e) => e.severity === 'error');
  const warnings = structuredErrors.filter((e) => e.severity === 'warning');

  const handleErrorClick = (error: ValidationError) => {
    if (error.node_id) {
      selectNode(error.node_id);
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {!isExpanded ? (
            <svg
              className="w-4 h-4 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          ) : (
            <svg
              className="w-4 h-4 text-gray-500 transform rotate-90"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          )}
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
                  className={`flex items-start gap-2 p-2 rounded text-sm ${error.node_id
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
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs font-bold text-red-700">{error.code}</span>
                      {error.node_name && (
                        <span className="text-xs text-red-600 border border-red-200 px-1 rounded bg-white">
                          {error.node_name}
                        </span>
                      )}
                    </div>
                    <div className="text-red-900">{error.message}</div>
                    {error.suggestion && (
                      <div className="text-xs text-red-700 mt-1 italic">
                        💡 {error.suggestion}
                      </div>
                    )}
                    {error.node_id && (
                      <div className="text-[10px] text-red-400 mt-1">
                        Node ID: {error.node_id}
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
                  className={`flex items-start gap-2 p-2 rounded text-sm ${warning.node_id
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
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs font-bold text-yellow-700">
                        {warning.code}
                      </span>
                      {warning.node_name && (
                        <span className="text-xs text-yellow-600 border border-yellow-200 px-1 rounded bg-white">
                          {warning.node_name}
                        </span>
                      )}
                    </div>
                    <div className="text-yellow-900">{warning.message}</div>
                    {warning.suggestion && (
                      <div className="text-xs text-yellow-700 mt-1 italic">
                        💡 {warning.suggestion}
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
