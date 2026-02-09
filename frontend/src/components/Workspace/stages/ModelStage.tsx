import { ModelsPanel } from '../../Pipeline';
import { usePipelineStore, selectCurrentPipelineId } from '../../../stores/pipelineStore';

export const ModelStage = () => {
  const currentPipelineId = usePipelineStore(selectCurrentPipelineId);

  if (!currentPipelineId) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-gray-500">
        Create a pipeline before fitting models.
      </div>
    );
  }

  return (
    <div className="h-full overflow-hidden bg-white">
      <ModelsPanel className="!w-full !border-l-0" />
    </div>
  );
};
