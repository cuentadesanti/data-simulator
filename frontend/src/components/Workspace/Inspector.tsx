import { NodeEditor, VariablesPanel } from '../Panel';
import { useWorkspaceStore } from '../../stores/workspaceStore';

export const Inspector = () => {
  const inspectorContext = useWorkspaceStore((state) => state.inspectorContext);
  const inspectorView = useWorkspaceStore((state) => state.inspectorView);
  const activeStage = useWorkspaceStore((state) => state.activeStage);

  return (
    <aside className="h-full w-96 border-l border-gray-200 bg-white overflow-y-auto">
      {inspectorView === 'variables' && activeStage === 'source' ? (
        <VariablesPanel />
      ) : inspectorContext?.type === 'node' ? (
        <NodeEditor />
      ) : (
        <div className="p-4 text-sm text-gray-500">
          {inspectorContext
            ? `Inspector: ${inspectorContext.type}`
            : activeStage === 'source'
              ? 'Select a node to edit its configuration, or click Variables to manage context variables.'
              : `No ${activeStage} item selected.`}
        </div>
      )}
    </aside>
  );
};
