import { useEffect, useRef } from 'react';
import { useOnboardingStore } from '../../stores/onboardingStore';
import { useWorkspaceStore, type Stage } from '../../stores/workspaceStore';
import { useDAGStore, selectSelectedNodeId } from '../../stores/dagStore';
import { tourDefinitions } from './tourDefinitions';
import { dispatchTelemetryEvent } from '../../services/telemetry';
import type { TourId } from './types';

const STAGE_TOUR_DONE_KEY: Record<Stage, 'sourceTourDone' | 'transformTourDone' | 'modelTourDone' | 'publishTourDone'> = {
  source: 'sourceTourDone',
  transform: 'transformTourDone',
  model: 'modelTourDone',
  publish: 'publishTourDone',
};

/** Cooldown (ms) after a tour ends before another can auto-trigger. */
const POST_TOUR_COOLDOWN = 1500;

export function useTourTrigger() {
  const mainTourStatus = useOnboardingStore((s) => s.mainTourStatus);
  const activeTourId = useOnboardingStore((s) => s.activeTourId);
  const tourVersions = useOnboardingStore((s) => s.tourVersions);
  const inspectorHintShown = useOnboardingStore((s) => s.inspectorHintShown);
  const startTour = useOnboardingStore((s) => s.startTour);
  const markInspectorHintShown = useOnboardingStore((s) => s.markInspectorHintShown);

  const activeStage = useWorkspaceStore((s) => s.activeStage);
  const selectedNodeId = useDAGStore(selectSelectedNodeId);

  // Session-level guard: tours that already triggered this page load
  const triggeredThisSession = useRef(new Set<string>());
  // Cooldown: timestamp of last tour end
  const lastTourEndRef = useRef(0);

  // Track when a tour ends to set cooldown
  const prevActiveTourId = useRef(activeTourId);
  useEffect(() => {
    if (prevActiveTourId.current && !activeTourId) {
      // A tour just ended
      lastTourEndRef.current = Date.now();
    }
    prevActiveTourId.current = activeTourId;
  }, [activeTourId]);

  // Layer 1: Main tour auto-trigger
  useEffect(() => {
    if (mainTourStatus !== 'new' || activeTourId) return;
    if (triggeredThisSession.current.has('main')) return;

    const timer = setTimeout(() => {
      const state = useOnboardingStore.getState();
      if (state.mainTourStatus !== 'new' || state.activeTourId) return;
      if (triggeredThisSession.current.has('main')) return;

      // Check cooldown
      if (Date.now() - lastTourEndRef.current < POST_TOUR_COOLDOWN) return;

      triggeredThisSession.current.add('main');
      dispatchTelemetryEvent({
        event_type: 'tour_start',
        action: 'main',
        metadata: {
          tour_id: 'main',
          trigger: 'auto',
          tour_version: tourDefinitions.main.version,
        },
      });
      startTour('main', 'guided');
    }, 500);
    return () => clearTimeout(timer);
  }, [mainTourStatus, activeTourId, startTour]);

  // Layer 2: Stage micro-tour auto-trigger
  useEffect(() => {
    if (mainTourStatus === 'new' || activeTourId) return;

    const stageTourId = activeStage as TourId;
    const stageKey = STAGE_TOUR_DONE_KEY[activeStage];

    // Session guard: don't re-trigger a tour that already ran this session
    if (triggeredThisSession.current.has(stageTourId)) return;

    const stageTourDone = useOnboardingStore.getState()[stageKey];
    const definition = tourDefinitions[stageTourId];

    // Check version-based re-trigger
    const savedVersion = tourVersions[stageTourId] ?? 0;
    const needsRetrigger = savedVersion < definition.version;

    if (stageTourDone && !needsRetrigger) return;

    const timer = setTimeout(() => {
      const currentState = useOnboardingStore.getState();
      if (currentState.activeTourId) return;
      if (triggeredThisSession.current.has(stageTourId)) return;

      const currentDone = currentState[stageKey];
      if (currentDone && !needsRetrigger) return;

      // Check cooldown — don't chain immediately after another tour
      if (Date.now() - lastTourEndRef.current < POST_TOUR_COOLDOWN) return;

      triggeredThisSession.current.add(stageTourId);
      dispatchTelemetryEvent({
        event_type: 'tour_start',
        action: stageTourId,
        metadata: {
          tour_id: stageTourId,
          trigger: 'auto',
          tour_version: definition.version,
        },
      });
      startTour(stageTourId, 'guided');
    }, 800);
    return () => clearTimeout(timer);
  }, [activeStage, mainTourStatus, activeTourId, startTour, tourVersions]);

  // Inspector hint
  useEffect(() => {
    if (inspectorHintShown || activeTourId || !selectedNodeId) return;
    markInspectorHintShown();
  }, [inspectorHintShown, activeTourId, selectedNodeId, markInspectorHintShown]);
}
