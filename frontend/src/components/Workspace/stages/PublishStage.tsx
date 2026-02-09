import { useState } from 'react';
import { dagApi, downloadBlob } from '../../../services/api';
import { useDAGStore } from '../../../stores/dagStore';
import { useProjectStore } from '../../../stores/projectStore';
import { useToast } from '../../common';
import { trackClick, trackCompletionLatency, trackFeedbackLatencyOnNextPaint } from '../../../services/telemetry';
import { useShareVersion } from '../../../hooks/useShareVersion';

type ExportFormat = 'csv' | 'parquet' | 'json';

export const PublishStage = () => {
  const exportDAG = useDAGStore((state) => state.exportDAG);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const currentVersionId = useProjectStore((state) => state.currentVersionId);
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [isExporting, setIsExporting] = useState(false);
  const { addToast } = useToast();
  const { isSharing, shareVersion } = useShareVersion();

  const handleDownload = async () => {
    setIsExporting(true);
    const started = performance.now();
    trackFeedbackLatencyOnNextPaint('publish.download', started, {
      format,
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      const blob = await dagApi.generate(exportDAG(), format);
      downloadBlob(blob, `dataset.${format}`);
      trackClick('HP-2', 'publish', 'download_dataset', { familiar_pattern: true });
      trackCompletionLatency('publish.download', started, { format, user_initiated: true });
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Download failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleShare = async () => {
    const result = await shareVersion(currentProjectId, currentVersionId);
    if (result) {
      trackClick('HP-2', 'publish', 'share_version', { familiar_pattern: true });
    }
  };

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-2xl rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900">Publish Dataset</h2>
        <p className="mt-1 text-sm text-gray-500">
          Export generated data and share the current version.
        </p>
        <div className="mt-4 flex items-center gap-3">
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="csv">CSV</option>
            <option value="parquet">Parquet</option>
            <option value="json">JSON</option>
          </select>
          <button
            type="button"
            onClick={handleDownload}
            disabled={isExporting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
          >
            {isExporting ? 'Preparing...' : 'Download'}
          </button>
          <button
            type="button"
            onClick={handleShare}
            disabled={isSharing}
            className="rounded-md border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {isSharing ? 'Sharing...' : 'Share'}
          </button>
        </div>
      </div>
    </div>
  );
};
