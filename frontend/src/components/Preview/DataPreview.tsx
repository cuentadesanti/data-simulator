import { useState } from 'react';
import { useDAGStore, selectPreviewData, selectPreviewColumns } from '../../stores/dagStore';
import { PreviewStats } from './PreviewStats';
import { PreviewTable } from './PreviewTable';
import { ValidationPanel } from './ValidationPanel';

export const DataPreview = () => {
  const previewData = useDAGStore(selectPreviewData);
  const previewColumns = useDAGStore(selectPreviewColumns);
  const [isExpanded, setIsExpanded] = useState(false);

  const hasData = previewData && previewData.length > 0;
  const panelHeight = isExpanded ? 'h-[400px]' : 'h-[200px]';

  return (
    <div
      className={`${panelHeight} bg-white border-t border-gray-300 shadow-lg flex flex-col transition-all duration-300`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
          <h3 className="font-semibold text-gray-900">Data Preview</h3>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
        >
          {isExpanded ? (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
              Collapse
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 15l7-7 7 7"
                />
              </svg>
              Expand
            </>
          )}
        </button>
      </div>

      {/* Stats */}
      {hasData && <PreviewStats />}

      {/* Validation Panel */}
      <ValidationPanel />

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        {!hasData ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <svg
                className="w-16 h-16 mx-auto mb-3 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-lg font-medium mb-1">No preview data</p>
              <p className="text-sm text-gray-400">Generate data to see a preview here</p>
            </div>
          </div>
        ) : (
          <PreviewTable data={previewData} columns={previewColumns} />
        )}
      </div>
    </div>
  );
};
