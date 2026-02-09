import { useEffect, useMemo, useRef } from 'react';
import { dagApi } from '../services/api';
import { useDAGStore } from '../stores/dagStore';
import { trackCompletionLatency, trackProgressFeedback } from '../services/telemetry';

const DEBOUNCE_MS = 800;

export function useAutoValidation() {
  const exportDAG = useDAGStore((state) => state.exportDAG);
  const setValidating = useDAGStore((state) => state.setValidating);
  const setValidationErrors = useDAGStore((state) => state.setValidationErrors);
  const setStructuredErrors = useDAGStore((state) => state.setStructuredErrors);
  const setEdgeStatuses = useDAGStore((state) => state.setEdgeStatuses);
  const setLastValidationResult = useDAGStore((state) => state.setLastValidationResult);
  const nodes = useDAGStore((state) => state.nodes);
  const edges = useDAGStore((state) => state.edges);
  const context = useDAGStore((state) => state.context);
  const metadata = useDAGStore((state) => state.metadata);

  const dagSnapshot = useMemo(
    () =>
      JSON.stringify({
        nodes,
        edges,
        context,
        metadata,
      }),
    [nodes, edges, context, metadata]
  );
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (nodes.length === 0) {
      setValidationErrors([]);
      setStructuredErrors([]);
      setEdgeStatuses([], []);
      setLastValidationResult(null);
      return;
    }

    const currentRequest = ++requestIdRef.current;
    const timer = window.setTimeout(async () => {
      setValidating(true);
      setLastValidationResult('pending');
      const started = performance.now();
      try {
        const dag = exportDAG();
        const result = await dagApi.validate(dag);
        if (currentRequest !== requestIdRef.current) return;

        setEdgeStatuses(result.edge_statuses || [], result.missing_edges || []);
        setValidationErrors(result.errors || []);
        setStructuredErrors(result.structured_errors || []);
        setLastValidationResult(result.valid ? 'valid' : 'invalid');
        trackProgressFeedback(undefined, 'source', 'auto-validate');
      } catch {
        if (currentRequest !== requestIdRef.current) return;
        setLastValidationResult('invalid');
      } finally {
        if (currentRequest === requestIdRef.current) {
          setValidating(false);
        }
        trackCompletionLatency('dag.validate', started, { user_initiated: false });
      }
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [
    dagSnapshot,
    exportDAG,
    setValidating,
    setValidationErrors,
    setStructuredErrors,
    setEdgeStatuses,
    setLastValidationResult,
  ]);
}
