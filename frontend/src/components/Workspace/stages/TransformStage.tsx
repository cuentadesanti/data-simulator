import { useMemo, useState } from 'react';
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

export const TransformStage = () => {
  const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
  const schema = usePipelineStore(selectPipelineSchema);
  const previewRows = usePipelineStore(selectPreviewRows);
  const materializedRows = usePipelineStore(selectMaterializedRows);
  const steps = usePipelineStore(selectPipelineSteps);
  const [recipeOpen, setRecipeOpen] = useState(true);

  useAutoMaterialize(true);

  const data = useMemo(
    () => (materializedRows.length > 0 ? materializedRows : previewRows),
    [materializedRows, previewRows]
  );

  if (!currentPipelineId) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-gray-500">
        Select source and create a pipeline first.
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
