import { useState } from 'react';
import { useProjectStore } from '../../../stores/projectStore';
import { sourcesApi } from '../../../api/sourcesApi';
import { useSourceStore } from '../../../stores/sourceStore';
import { usePipelineStore } from '../../../stores/pipelineStore';
import { useToast } from '../../common';
import {
  trackClick,
  trackCompletionLatency,
  trackFeedbackLatencyOnNextPaint,
  trackFlowComplete,
  trackProgressFeedback,
} from '../../../services/telemetry';

type Step = 1 | 2 | 3;

export const UploadWizard = () => {
  const [step, setStep] = useState<Step>(1);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreatingPipeline, setIsCreatingPipeline] = useState(false);

  const projectId = useProjectStore((state) => state.currentProjectId);
  const setUploadedSource = useSourceStore((state) => state.setUploadedSource);
  const uploadedSourceId = useSourceStore((state) => state.uploadedSourceId);
  const sourceSchema = useSourceStore((state) => state.sourceSchema);
  const createPipelineFromUpload = usePipelineStore((state) => state.createPipelineFromUpload);
  const { addToast } = useToast();

  const handleUpload = async () => {
    if (!projectId) {
      addToast('info', 'Select a project in the top navigation first');
      return;
    }
    if (!file) {
      addToast('info', 'Choose a CSV or Parquet file first');
      return;
    }
    const started = performance.now();
    setIsUploading(true);
    trackFeedbackLatencyOnNextPaint('source.upload', started, {
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      const result = await sourcesApi.upload(projectId, file);
      setUploadedSource(result.source_id, result.schema);
      setStep(2);
      trackClick('HP-3', 'source', 'upload_dataset', { familiar_pattern: true });
      trackProgressFeedback('HP-3', 'source', 'upload_complete');
      trackCompletionLatency('source.upload', started, { user_initiated: true });
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreatePipeline = async () => {
    if (!projectId || !uploadedSourceId) return;
    const started = performance.now();
    setIsCreatingPipeline(true);
    trackFeedbackLatencyOnNextPaint('pipeline.create.upload', started, {
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      await createPipelineFromUpload(projectId, `Uploaded Pipeline (${new Date().toISOString().slice(0, 10)})`, uploadedSourceId);
      setStep(3);
      trackClick('HP-3', 'source', 'create_pipeline_from_upload', { familiar_pattern: true });
      trackFlowComplete('HP-3');
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Pipeline creation failed');
    } finally {
      setIsCreatingPipeline(false);
    }
  };

  return (
    <div className="space-y-4">
      {step === 1 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900">Step 1: Upload file</h3>
          <p className="mt-1 text-sm text-gray-500">CSV or Parquet up to 200MB.</p>
          {!projectId && (
            <p className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              No project selected. Pick a project from the top navigation before uploading.
            </p>
          )}
          <input
            type="file"
            accept=".csv,.parquet"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="mt-4 block w-full text-sm"
          />
          <button
            type="button"
            disabled={!file || !projectId || isUploading}
            onClick={handleUpload}
            className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      )}

      {step >= 2 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900">Step 2: Confirm schema</h3>
          <div className="mt-3 max-h-56 overflow-auto rounded border border-gray-100">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Column</th>
                  <th className="px-3 py-2 text-left">Type</th>
                </tr>
              </thead>
              <tbody>
                {sourceSchema.map((column) => (
                  <tr key={column.name} className="border-t border-gray-100">
                    <td className="px-3 py-2">{column.name}</td>
                    <td className="px-3 py-2 text-gray-600">{column.dtype}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {step === 2 && (
            <button
              type="button"
              onClick={handleCreatePipeline}
              disabled={isCreatingPipeline}
              className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {isCreatingPipeline ? 'Creating pipeline...' : 'Create Pipeline'}
            </button>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-green-700">
          Upload source linked and pipeline created. Continue to Transform stage.
        </div>
      )}
    </div>
  );
};
