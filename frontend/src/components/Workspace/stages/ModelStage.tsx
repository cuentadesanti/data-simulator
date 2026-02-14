import { useMemo, useState } from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import {
  ModelsPanel,
  PipelineAnalysisTabs,
  type PipelineDiagnosticsPayload,
} from '../../Pipeline';
import {
  usePipelineStore,
  selectCurrentPipelineId,
  selectPipelineSchema,
  selectPreviewRows,
  selectMaterializedRows,
  selectPipelineSteps,
  selectPipelineLineage,
} from '../../../stores/pipelineStore';

export const ModelStage = () => {
  const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
  const schema = usePipelineStore(selectPipelineSchema);
  const previewRows = usePipelineStore(selectPreviewRows);
  const materializedRows = usePipelineStore(selectMaterializedRows);
  const steps = usePipelineStore(selectPipelineSteps);
  const lineage = usePipelineStore(selectPipelineLineage);

  const [diagnostics, setDiagnostics] = useState<PipelineDiagnosticsPayload | null>(null);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(true);

  const displayData = useMemo(
    () => (materializedRows.length > 0 ? materializedRows : previewRows),
    [materializedRows, previewRows],
  );
  const displayColumns = useMemo(() => schema.map((s) => s.name), [schema]);
  const derivedColumns = useMemo(() => steps.map((s) => s.output_column), [steps]);

  if (!currentPipelineId) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-gray-500">
        Create a pipeline before fitting models.
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {analysisOpen && (
        <div className="min-w-0 flex-1">
          <PipelineAnalysisTabs
            data={displayData as Record<string, unknown>[]}
            columns={displayColumns}
            derivedColumns={derivedColumns}
            steps={steps}
            lineage={lineage}
            selectedStepId={selectedStepId}
            onSelectStep={setSelectedStepId}
            diagnostics={diagnostics}
          />
        </div>
      )}

      <div className="border-l border-gray-200 bg-gray-50">
        <button
          type="button"
          onClick={() => setAnalysisOpen((v) => !v)}
          className="m-2 rounded border border-gray-200 bg-white p-1 text-gray-600"
        >
          {analysisOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
        </button>
      </div>

      <div className={analysisOpen ? 'w-[380px] shrink-0' : 'min-w-0 flex-1'}>
        <ModelsPanel
          className="!w-full !border-l-0"
          onDiagnosticsChange={setDiagnostics}
        />
      </div>
    </div>
  );
};
