import { useMemo } from 'react';
import {
  trackClick,
  trackCompletionLatency,
  trackFeedbackLatency,
  trackFlowComplete,
  trackFlowStart,
  type TelemetryStage,
} from '../services/telemetry';

export function useTelemetry(pathId: string) {
  return useMemo(
    () => ({
      trackClick: (stage: TelemetryStage | string | undefined, action: string, extra?: { familiar_pattern?: boolean }) =>
        trackClick(pathId, stage, action, extra),
      startFlow: () => trackFlowStart(pathId),
      completeFlow: () => trackFlowComplete(pathId),
      trackFeedbackLatency: (action: string, startMs: number, metadata?: Record<string, unknown>) =>
        trackFeedbackLatency(action, startMs, metadata),
      trackCompletionLatency: (action: string, startMs: number, metadata?: Record<string, unknown>) =>
        trackCompletionLatency(action, startMs, metadata),
    }),
    [pathId]
  );
}
