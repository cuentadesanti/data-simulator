import { useState, useMemo } from 'react';
import { Table2, BarChart3, ScatterChart } from 'lucide-react';
import { useDAGStore, selectPreviewData, selectPreviewColumns } from '../../stores/dagStore';
import { PreviewTable } from '../Preview/PreviewTable';
import { PreviewStats } from '../Preview/PreviewStats';
import { ValidationPanel } from '../Preview/ValidationPanel';
import { HistogramView } from './HistogramView';
import { ScatterPlotView } from './ScatterPlotView';

type SubTabId = 'table' | 'histograms' | 'scatter';

interface SubTab {
  id: SubTabId;
  label: string;
  icon: React.ReactNode;
}

const subTabs: SubTab[] = [
  { id: 'table', label: 'Table', icon: <Table2 size={14} /> },
  { id: 'histograms', label: 'Histograms', icon: <BarChart3 size={14} /> },
  { id: 'scatter', label: 'Scatter Plot', icon: <ScatterChart size={14} /> },
];

export const DataView = () => {
  const previewData = useDAGStore(selectPreviewData);
  const previewColumns = useDAGStore(selectPreviewColumns);
  const [activeSubTab, setActiveSubTab] = useState<SubTabId>('table');

  const hasData = previewData && previewData.length > 0;

  // Get numeric columns for charts
  const numericColumns = useMemo(() => {
    if (!previewData || previewData.length === 0 || !previewColumns) return [];

    return previewColumns.filter((col) => {
      const firstValue = previewData.find((row) => row[col] !== null && row[col] !== undefined)?.[
        col
      ];
      return typeof firstValue === 'number';
    });
  }, [previewData, previewColumns]);

  if (!hasData) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <svg
            className="w-20 h-20 mx-auto mb-4 text-gray-300"
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
          <p className="text-xl font-medium text-gray-600 mb-2">No preview data</p>
          <p className="text-sm text-gray-400 max-w-md">
            Add nodes to your DAG and click "Preview" in the toolbar to generate sample data. You'll
            see tables, histograms, and scatter plots here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-50">
      {/* Stats Bar */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200">
        <PreviewStats />
      </div>

      {/* Validation Panel */}
      <div className="flex-shrink-0">
        <ValidationPanel />
      </div>

      {/* Sub-tabs */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4">
        <div className="flex gap-1">
          {subTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              disabled={tab.id !== 'table' && numericColumns.length === 0}
              className={`
                flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors
                ${
                  activeSubTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
                ${tab.id !== 'table' && numericColumns.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
          {numericColumns.length === 0 && (
            <span className="self-center ml-2 text-xs text-gray-400">
              (Charts require numeric columns)
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeSubTab === 'table' && <PreviewTable data={previewData} columns={previewColumns} />}
        {activeSubTab === 'histograms' && (
          <HistogramView
            data={previewData}
            columns={numericColumns}
            allColumns={previewColumns ?? undefined}
          />
        )}
        {activeSubTab === 'scatter' && (
          <ScatterPlotView
            data={previewData}
            columns={numericColumns}
            allColumns={previewColumns ?? undefined}
          />
        )}
      </div>
    </div>
  );
};
