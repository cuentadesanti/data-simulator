import { useEffect, useState } from 'react';
import { AddNodeDropdown } from '../Toolbar/AddNodeDropdown';
import { OverflowMenu } from './OverflowMenu';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useDAGStore, selectLastValidationResult } from '../../stores/dagStore';
import { dagApi, downloadBlob } from '../../services/api';
import { usePipelineStore } from '../../stores/pipelineStore';
import { useProjectStore } from '../../stores/projectStore';
import { useSourceStore } from '../../stores/sourceStore';
import { useToast } from '../common';
import {
  trackClick,
  trackCompletionLatency,
  trackFeedbackLatencyOnNextPaint,
  trackFlowComplete,
  trackVisibleActions,
} from '../../services/telemetry';
import { useShareVersion } from '../../hooks/useShareVersion';
import type { DAGDefinition } from '../../types/dag';

// Counts: stage-bar primary buttons + GlobalHeader buttons (Save + Share = 2).
const HEADER_ACTIONS = 2;
const STAGE_BAR_COUNTS: Record<string, number> = {
  source: 4,    // AddNode, Generate Preview, Change Source, Variables
  transform: 3, // Generate Preview, Add Step, Materialize
  model: 1,     // Fit Model
  publish: 2,   // Download CSV, Share
};

export const StageActionBar = () => {
  const stage = useWorkspaceStore((state) => state.activeStage);
  const inspectorView = useWorkspaceStore((state) => state.inspectorView);
  const pinInspectorView = useWorkspaceStore((state) => state.pinInspectorView);
  const setInspectorOpen = useWorkspaceStore((state) => state.setInspectorOpen);
  const exportDAG = useDAGStore((state) => state.exportDAG);
  const importDAG = useDAGStore((state) => state.importDAG);
  const clearDAG = useDAGStore((state) => state.clearDAG);
  const setPreviewData = useDAGStore((state) => state.setPreviewData);
  const materialize = usePipelineStore((state) => state.materialize);
  const isMaterializing = usePipelineStore((state) => state.isMaterializing);
  const currentPipelineId = usePipelineStore((state) => state.currentPipelineId);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const currentVersionId = useProjectStore((state) => state.currentVersionId);
  const clearSource = useSourceStore((state) => state.clearSource);
  const lastValidationResult = useDAGStore(selectLastValidationResult);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const { addToast } = useToast();
  const { isSharing, shareVersion } = useShareVersion();

  useEffect(() => {
    const count = (STAGE_BAR_COUNTS[stage] ?? 0) + HEADER_ACTIONS;
    trackVisibleActions(stage, count);
  }, [stage]);

  const handleGeneratePreview = async () => {
    const started = performance.now();
    setIsGeneratingPreview(true);
    trackFeedbackLatencyOnNextPaint('preview', started, {
      stage,
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      const result = await dagApi.preview(exportDAG());
      setPreviewData(result.data, result.columns);
      addToast('success', `Preview generated (${result.rows} rows)`);
      trackClick('HP-1', stage, 'generate_preview', { familiar_pattern: true });
      trackFlowComplete('HP-1');
      trackCompletionLatency('preview', started, { stage, user_initiated: true });
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Preview failed');
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  const handleMaterialize = async () => {
    if (!currentPipelineId) {
      addToast('info', 'Create a pipeline first');
      return;
    }
    const started = performance.now();
    try {
      const materializePromise = materialize(1000);
      trackFeedbackLatencyOnNextPaint('transform.materialize', started, {
        stage: 'transform',
        feedback_type: 'button_loading',
        user_initiated: true,
      });
      await materializePromise;
      trackClick('HP-3', 'transform', 'materialize', { familiar_pattern: true });
      trackCompletionLatency('transform.materialize', started, { user_initiated: true });
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Materialize failed');
    }
  };

  const handleFitModel = () => {
    window.dispatchEvent(new CustomEvent('workspace-fit-model'));
    trackClick('HP-3', 'model', 'fit_model', { familiar_pattern: true });
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    const started = performance.now();
    trackFeedbackLatencyOnNextPaint('publish.download', started, {
      format: 'csv',
      feedback_type: 'button_loading',
      user_initiated: true,
    });
    try {
      const blob = await dagApi.generate(exportDAG(), 'csv');
      downloadBlob(blob, 'dataset.csv');
      trackClick('HP-2', 'publish', 'download_dataset', { familiar_pattern: true });
      trackCompletionLatency('publish.download', started, { format: 'csv', user_initiated: true });
    } catch (error) {
      addToast('error', error instanceof Error ? error.message : 'Download failed');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(exportDAG(), null, 2)], { type: 'application/json' });
    downloadBlob(blob, 'dag-definition.json');
    trackClick(undefined, stage, 'export_json', { familiar_pattern: false });
  };

  const handleImportJSON = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        if (!isValidDagDefinition(parsed)) {
          throw new Error('Invalid DAG JSON format');
        }
        importDAG(parsed);
        trackClick(undefined, stage, 'import_json', { familiar_pattern: false });
      } catch (error) {
        addToast('error', error instanceof Error ? error.message : 'Invalid JSON file');
      }
    };
    input.click();
  };

  const handleClear = () => {
    clearDAG();
    trackClick(undefined, stage, 'clear_dag', { familiar_pattern: false });
  };

  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
      <div className="flex items-center gap-2">
        {stage === 'source' && <AddNodeDropdown />}
        {(stage === 'source' || stage === 'transform') && (
          <button
            type="button"
            onClick={handleGeneratePreview}
            disabled={lastValidationResult === 'invalid' || isGeneratingPreview}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            title={lastValidationResult === 'invalid' ? 'Fix validation errors first' : 'Generate preview'}
          >
            {isGeneratingPreview ? 'Generating...' : 'Generate Preview'}
          </button>
        )}
        {stage === 'source' && (
          <button
            type="button"
            onClick={clearSource}
            className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Change Source
          </button>
        )}
        {stage === 'source' && (
          <button
            type="button"
            onClick={() => {
              const next = inspectorView === 'variables' ? 'node' : 'variables';
              pinInspectorView(next);
              setInspectorOpen(true);
            }}
            className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
              inspectorView === 'variables'
                ? 'border-purple-300 bg-purple-50 text-purple-700'
                : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Variables
          </button>
        )}
        {stage === 'transform' && (
          <>
            <button
              type="button"
              onClick={() => window.dispatchEvent(new CustomEvent('workspace-focus-formula'))}
              className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Add Step
            </button>
            <button
              type="button"
              onClick={handleMaterialize}
              disabled={isMaterializing}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {isMaterializing ? 'Materializing...' : 'Materialize'}
            </button>
          </>
        )}
        {stage === 'model' && (
          <button
            type="button"
            onClick={handleFitModel}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Fit Model
          </button>
        )}
        {stage === 'publish' && (
          <>
            <button
              type="button"
              onClick={handleDownload}
              disabled={isDownloading}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
            >
              {isDownloading ? 'Preparing...' : 'Download CSV'}
            </button>
            <button
              type="button"
              onClick={() => void shareVersion(currentProjectId, currentVersionId)}
              disabled={isSharing}
              className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Share
            </button>
          </>
        )}
      </div>

      <OverflowMenu
        items={[
          { label: 'Import JSON', onClick: handleImportJSON },
          { label: 'Export JSON', onClick: handleExportJSON },
          { label: 'Clear DAG', onClick: handleClear },
        ]}
      />
    </div>
  );
};

function isValidDagDefinition(value: unknown): value is DAGDefinition {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Record<string, unknown>;
  return (
    Array.isArray(candidate.nodes) &&
    Array.isArray(candidate.edges) &&
    typeof candidate.context === 'object' &&
    candidate.context !== null &&
    typeof candidate.metadata === 'object' &&
    candidate.metadata !== null
  );
}
