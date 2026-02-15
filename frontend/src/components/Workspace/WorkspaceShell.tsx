import { useEffect, useRef } from 'react';
import { useDAGStore, selectSelectedNodeId } from '../../stores/dagStore';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useProjectStore } from '../../stores/projectStore';
import { useOnboardingStore } from '../../stores/onboardingStore';
import { GlobalHeader } from './GlobalHeader';
import { LeftRail } from './LeftRail';
import { Inspector } from './Inspector';
import { StageActionBar } from './StageActionBar';
import { SourceStage } from './stages/SourceStage';
import { TransformStage } from './stages/TransformStage';
import { ModelStage } from './stages/ModelStage';
import { PublishStage } from './stages/PublishStage';
import { TourProvider, HelpButton, useTourTrigger } from '../Onboarding';

export const WorkspaceShell = () => {
  const activeStage = useWorkspaceStore((state) => state.activeStage);
  const inspectorOpen = useWorkspaceStore((state) => state.inspectorOpen);
  const setInspectorOpen = useWorkspaceStore((state) => state.setInspectorOpen);
  const setInspectorContext = useWorkspaceStore((state) => state.setInspectorContext);
  const selectedNodeId = useDAGStore(selectSelectedNodeId);
  const fetchProjects = useProjectStore((state) => state.fetchProjects);
  const restoreCurrentProject = useProjectStore((state) => state.restoreCurrentProject);
  const hydrateOnboarding = useOnboardingStore((state) => state._hydrate);
  const initRef = useRef(false);

  useTourTrigger();

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    hydrateOnboarding();
    void (async () => {
      await fetchProjects();
      await restoreCurrentProject();
      const state = useProjectStore.getState();
      if (!state.currentProjectId && state.projects.length > 0) {
        await state.selectProject(state.projects[0].id);
      }
    })();
  }, [fetchProjects, restoreCurrentProject, hydrateOnboarding]);

  const setInspectorView = useWorkspaceStore((state) => state.setInspectorView);
  const inspectorViewPinned = useWorkspaceStore((state) => state.inspectorViewPinned);

  useEffect(() => {
    if (selectedNodeId) {
      setInspectorOpen(true);
      setInspectorContext({ type: 'node', id: selectedNodeId });
      // Only auto-switch to node view if user hasn't pinned variables
      if (!inspectorViewPinned) {
        setInspectorView('node');
      }
    } else if (inspectorViewPinned) {
      // Variables pinned — keep inspector open even without a selected node
      setInspectorOpen(true);
      setInspectorContext(null);
    } else {
      setInspectorOpen(false);
      setInspectorContext(null);
    }
  }, [selectedNodeId, activeStage, inspectorViewPinned, setInspectorContext, setInspectorOpen, setInspectorView]);

  return (
    <div className="h-screen w-full bg-gray-50">
      <GlobalHeader />
      <div className="relative flex h-[calc(100vh-48px)] overflow-hidden">
        <LeftRail />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <StageActionBar />
          <div data-tour="main-content" className="min-h-0 flex-1 overflow-hidden">
            {activeStage === 'source' && <SourceStage />}
            {activeStage === 'transform' && <TransformStage />}
            {activeStage === 'model' && <ModelStage />}
            {activeStage === 'publish' && <PublishStage />}
          </div>
        </main>
        {inspectorOpen && <div className="hidden xl:block">{<Inspector />}</div>}
      </div>
      <TourProvider />
      <HelpButton />
    </div>
  );
};
