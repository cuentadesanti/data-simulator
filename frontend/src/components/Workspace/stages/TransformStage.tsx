import { useEffect, useMemo, useRef, useState } from 'react';
import { PanelRightClose, PanelRightOpen } from 'lucide-react';
import { FormulaBar, RecipePanel } from '../../Pipeline';
import { PreviewTable } from '../../Preview/PreviewTable';
import {
  usePipelineStore,
  selectCurrentPipelineId,
  selectMaterializedRows,
  selectPipelineSchema,
  selectPreviewRows,
  selectPipelineSteps,
} from '../../../stores/pipelineStore';
import { useAutoMaterialize } from '../../../hooks/useAutoMaterialize';
import { useSourceStore } from '../../../stores/sourceStore';
import { useProjectStore } from '../../../stores/projectStore';
import { useWorkspaceStore } from '../../../stores/workspaceStore';

export const TransformStage = () => {
  const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
  const createPipelineFromSimulation = usePipelineStore((state) => state.createPipelineFromSimulation);
  const isCreatingPipeline = usePipelineStore((state) => state.isCreatingPipeline);
  const schema = usePipelineStore(selectPipelineSchema);
  const previewRows = usePipelineStore(selectPreviewRows);
  const materializedRows = usePipelineStore(selectMaterializedRows);
  const steps = usePipelineStore(selectPipelineSteps);
  const sourceType = useSourceStore((state) => state.sourceType);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const currentVersionId = useProjectStore((state) => state.currentVersionId);
  const saveCurrentVersion = useProjectStore((state) => state.saveCurrentVersion);
  const setActiveStage = useWorkspaceStore((state) => state.setActiveStage);
  const [recipeOpen, setRecipeOpen] = useState(true);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const bootstrapAttemptedRef = useRef(false);

  useAutoMaterialize(true);

  const data = useMemo(
    () => (materializedRows.length > 0 ? materializedRows : previewRows),
    [materializedRows, previewRows]
  );

  const bootstrapPipelineFromDag = async () => {
    if (!currentProjectId) {
      throw new Error('Create or select a project first.');
    }

    let dagVersionId = currentVersionId;
    if (!dagVersionId) {
      await saveCurrentVersion();
      dagVersionId = useProjectStore.getState().currentVersionId;
    }
    if (!dagVersionId) {
      throw new Error('Could not create a DAG version for pipeline source.');
    }

    await createPipelineFromSimulation(
      currentProjectId,
      `Pipeline ${new Date().toISOString().slice(0, 10)}`,
      dagVersionId,
      42,
      1000,
      { trackClick: false, userInitiated: false, pathId: 'HP-1' }
    );
  };

  useEffect(() => {
    if (currentPipelineId || sourceType !== 'dag' || !currentProjectId || bootstrapAttemptedRef.current) {
      return;
    }
    bootstrapAttemptedRef.current = true;
    void (async () => {
      try {
        setBootstrapError(null);
        await bootstrapPipelineFromDag();
      } catch (error) {
        bootstrapAttemptedRef.current = false;
        setBootstrapError(error instanceof Error ? error.message : 'Failed to initialize pipeline');
      }
    })();
  }, [currentPipelineId, sourceType, currentProjectId]);

  if (!currentPipelineId) {
    if (sourceType === 'upload') {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center text-gray-500">
          <p>Complete upload and pipeline creation in Source stage first.</p>
          <button
            type="button"
            onClick={() => setActiveStage('source')}
            className="rounded-md border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Go To Source
          </button>
        </div>
      );
    }

    if (!sourceType) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center text-gray-500">
          <p>Select a source first.</p>
          <button
            type="button"
            onClick={() => setActiveStage('source')}
            className="rounded-md border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Go To Source
          </button>
        </div>
      );
    }

    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center text-gray-500">
        <p>{isCreatingPipeline ? 'Preparing transform workspace...' : 'Preparing pipeline from DAG source...'}</p>
        {bootstrapError && <p className="max-w-lg text-sm text-red-600">{bootstrapError}</p>}
        {!isCreatingPipeline && (
          <button
            type="button"
            onClick={() => {
              bootstrapAttemptedRef.current = true;
              void (async () => {
                try {
                  setBootstrapError(null);
                  await bootstrapPipelineFromDag();
                } catch (error) {
                  bootstrapAttemptedRef.current = false;
                  setBootstrapError(error instanceof Error ? error.message : 'Failed to initialize pipeline');
                }
              })();
            }}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Retry Pipeline Setup
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <FormulaBar />
        <div className="min-h-0 flex-1 overflow-auto bg-white">
          {data.length > 0 ? (
            <PreviewTable
              data={data}
              columns={schema.map((column) => column.name)}
              highlightColumns={steps.map((step) => step.output_column)}
            />
          ) : (
            <div className="p-6 text-sm text-gray-500">Apply a step to preview transformed data.</div>
          )}
        </div>
      </div>
      <div className="border-l border-gray-200 bg-gray-50">
        <button
          type="button"
          onClick={() => setRecipeOpen((v) => !v)}
          className="m-2 rounded border border-gray-200 bg-white p-1 text-gray-600"
        >
          {recipeOpen ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
        </button>
      </div>
      {recipeOpen && <RecipePanel />}
    </div>
  );
};
