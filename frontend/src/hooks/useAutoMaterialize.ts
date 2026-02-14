import { useEffect } from 'react';
import { usePipelineStore } from '../stores/pipelineStore';

const DEBOUNCE_MS = 800;

export function useAutoMaterialize(enabled = false) {
  const pipelineId = usePipelineStore((state) => state.currentPipelineId);
  const versionId = usePipelineStore((state) => state.currentVersionId);
  const steps = usePipelineStore((state) => state.steps);
  const materialize = usePipelineStore((state) => state.materialize);

  useEffect(() => {
    if (!enabled || !pipelineId || !versionId || steps.length === 0) return;
    const timer = window.setTimeout(() => {
      void materialize(500);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [enabled, pipelineId, versionId, steps, materialize]);
}
