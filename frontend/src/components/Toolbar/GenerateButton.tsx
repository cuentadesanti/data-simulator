import React, { useState, useRef, useEffect } from 'react';
import { Play, ChevronDown, Loader2, Download, Table } from 'lucide-react';
import { useDAGStore } from '../../stores/dagStore';
import { dagApi, downloadBlob } from '../../services/api';
import { useToast } from '../common';

type Format = 'csv' | 'parquet' | 'json';

interface GenerateButtonProps {
  onGeneratePreview: () => Promise<void>;
  isPreviewing: boolean;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({
  onGeneratePreview,
  isPreviewing,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [sampleSize, setSampleSize] = useState(1000);
  const [previewRows, setPreviewRows] = useState(500);
  const [seed, setSeed] = useState<string>('');
  const [format, setFormat] = useState<Format>('csv');

  const dropdownRef = useRef<HTMLDivElement>(null);
  const { exportDAG, metadata, setMetadata } = useDAGStore();
  const lastValidationResult = useDAGStore((s) => s.lastValidationResult);
  const edgeStatuses = useDAGStore((s) => s.edgeStatuses);
  const hasUnusedEdges = edgeStatuses.some((e) => e.status === 'unused');
  const { addToast } = useToast();

  const isDisabled = isPreviewing || isExporting || lastValidationResult !== 'valid';

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

  // Sync with store metadata
  useEffect(() => {
    setSampleSize(metadata.sample_size);
    setPreviewRows(metadata.preview_rows || 500);
    setSeed(metadata.seed?.toString() || '');
  }, [metadata]);

  const updateStoreMetadata = () => {
    setMetadata({
      sample_size: sampleSize,
      preview_rows: previewRows,
      seed: seed ? parseInt(seed, 10) : undefined,
    });
  };

  const handleMainClick = async () => {
    updateStoreMetadata();
    await onGeneratePreview();
  };

  const handleExport = async () => {
    setIsExporting(true);
    setIsOpen(false);
    updateStoreMetadata(); // Sync metadata before export

    try {
      // Get current state
      const dag = exportDAG();

      // Generate dataset
      const blob = await dagApi.generate(dag, format);

      // Download the generated file
      const extension = format === 'parquet' ? 'parquet' : format === 'json' ? 'json' : 'csv';
      downloadBlob(blob, `dataset.${extension}`);
      addToast('success', `Dataset exported: ${sampleSize.toLocaleString()} rows`);
    } catch (error) {
      console.error('Export error:', error);
      addToast(
        'error',
        `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative flex items-center" ref={dropdownRef}>
      {/* Warning badge for unused edges */}
      {lastValidationResult === 'valid' && hasUnusedEdges && (
        <span
          className="absolute -top-1 -right-1 w-3 h-3 bg-amber-500 rounded-full z-10"
          title="Has unused edges"
        />
      )}

      <div className="flex bg-green-600 rounded overflow-hidden hover:bg-green-700 transition-colors">
        {/* Main Action: Generate (Preview) */}
        <button
          onClick={handleMainClick}
          disabled={isDisabled}
          className="flex items-center gap-2 px-3 py-1.5 text-white disabled:bg-gray-400 disabled:cursor-not-allowed border-r border-green-700"
          title={lastValidationResult !== 'valid' ? 'Run validation first' : 'Generate preview'}
        >
          {isPreviewing ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          <span className="text-sm font-medium">{isPreviewing ? 'Generating...' : 'Generate'}</span>
        </button>

        {/* Dropdown Toggle: Export Options */}
        <button
          onClick={() => !isDisabled && setIsOpen(!isOpen)}
          disabled={isDisabled}
          className="px-1.5 py-1.5 text-white disabled:bg-gray-400 disabled:cursor-not-allowed hover:bg-green-800 transition-colors"
          title="Generation settings"
        >
          <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="p-4 space-y-4">
            {/* Preview Section */}
            <section>
              <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Table size={12} />
                Preview Settings
              </h3>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Rows to display
                </label>
                <input
                  type="number"
                  value={previewRows}
                  onChange={(e) => setPreviewRows(parseInt(e.target.value, 10) || 500)}
                  min={1}
                  max={5000}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            </section>

            <div className="h-px bg-gray-100 mx-1" />

            {/* Export Section */}
            <section className="space-y-3">
              <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Download size={12} />
                Export Settings
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Total Samples
                  </label>
                  <input
                    type="number"
                    value={sampleSize}
                    onChange={(e) => setSampleSize(parseInt(e.target.value, 10) || 1000)}
                    min={1}
                    max={10000000}
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Seed (Opt)</label>
                  <input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    placeholder="Auto"
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Export Format
                </label>
                <div className="flex gap-1 p-0.5 bg-gray-100 rounded">
                  {(['csv', 'parquet', 'json'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFormat(f)}
                      className={`flex-1 py-1 px-2 text-[10px] font-bold uppercase rounded transition-all ${
                        format === f
                          ? 'bg-white text-green-600 shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleExport}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded hover:bg-gray-900 transition-colors disabled:bg-gray-400 mt-2"
              >
                {isExporting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Download size={16} />
                )}
                {isExporting ? 'Exporting...' : 'Export Dataset'}
              </button>
            </section>
          </div>
        </div>
      )}
    </div>
  );
};
