import { useEffect } from 'react';
import { useDAGStore, selectSelectedNodeId } from '../../stores/dagStore';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useProjectStore, selectSidebarOpen } from '../../stores/projectStore';
import { ProjectSidebar } from '../ProjectSidebar';
import { GlobalHeader } from './GlobalHeader';
import { LeftRail } from './LeftRail';
import { Inspector } from './Inspector';
import { StageActionBar } from './StageActionBar';
import { SourceStage } from './stages/SourceStage';
import { TransformStage } from './stages/TransformStage';
import { ModelStage } from './stages/ModelStage';
import { PublishStage } from './stages/PublishStage';

export const WorkspaceShell = () => {
  const activeStage = useWorkspaceStore((state) => state.activeStage);
  const inspectorOpen = useWorkspaceStore((state) => state.inspectorOpen);
  const setInspectorContext = useWorkspaceStore((state) => state.setInspectorContext);
  const selectedNodeId = useDAGStore(selectSelectedNodeId);
  const sidebarOpen = useProjectStore(selectSidebarOpen);

  useEffect(() => {
    if (selectedNodeId) {
      setInspectorContext({ type: 'node', id: selectedNodeId });
    } else {
      setInspectorContext(null);
    }
  }, [selectedNodeId, setInspectorContext]);

  return (
    <div className="h-screen w-full bg-gray-50">
      <GlobalHeader />
      <div className="relative flex h-[calc(100vh-48px)] overflow-hidden">
        <LeftRail />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <StageActionBar />
          <div className="min-h-0 flex-1 overflow-hidden">
            {activeStage === 'source' && <SourceStage />}
            {activeStage === 'transform' && <TransformStage />}
            {activeStage === 'model' && <ModelStage />}
            {activeStage === 'publish' && <PublishStage />}
          </div>
        </main>
        {inspectorOpen && <div className="hidden xl:block">{<Inspector />}</div>}

        {sidebarOpen && (
          <div className="absolute left-0 top-0 z-30 h-full">
            <ProjectSidebar />
          </div>
        )}
      </div>
    </div>
  );
};
