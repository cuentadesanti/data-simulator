import { useEffect, useRef } from 'react';
import { useDAGStore, selectSelectedNodeId } from '../../stores/dagStore';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useProjectStore } from '../../stores/projectStore';
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
  const setInspectorOpen = useWorkspaceStore((state) => state.setInspectorOpen);
  const setInspectorContext = useWorkspaceStore((state) => state.setInspectorContext);
  const selectedNodeId = useDAGStore(selectSelectedNodeId);
  const fetchProjects = useProjectStore((state) => state.fetchProjects);
  const restoreCurrentProject = useProjectStore((state) => state.restoreCurrentProject);
  const initRef = useRef(false);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    void (async () => {
      await fetchProjects();
      await restoreCurrentProject();
      const state = useProjectStore.getState();
      if (!state.currentProjectId && state.projects.length > 0) {
        await state.selectProject(state.projects[0].id);
      }
    })();
  }, [fetchProjects, restoreCurrentProject]);

  useEffect(() => {
    if (selectedNodeId) {
      setInspectorOpen(true);
      setInspectorContext({ type: 'node', id: selectedNodeId });
    } else {
      setInspectorOpen(false);
      setInspectorContext(null);
    }
  }, [selectedNodeId, setInspectorContext, setInspectorOpen]);

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
      </div>
    </div>
  );
};
