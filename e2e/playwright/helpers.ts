import type { Page } from '@playwright/test';

export interface TelemetryEvent {
  event_type: string;
  path_id?: string;
  stage?: string;
  action?: string;
  latency_ms?: number;
  metadata?: Record<string, unknown>;
  ts: number;
}

/**
 * Extract the telemetry buffer from localStorage.
 */
export async function getTelemetryBuffer(page: Page): Promise<TelemetryEvent[]> {
  return page.evaluate(() => {
    const raw = window.localStorage.getItem('ux-telemetry-buffer-v1');
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
}

/**
 * Dump the telemetry buffer to a JSON file on disk.
 */
export async function dumpTelemetryToFile(page: Page, filePath: string): Promise<void> {
  const events = await getTelemetryBuffer(page);
  const fs = await import('fs');
  fs.writeFileSync(filePath, JSON.stringify({ events }, null, 2));
}

/**
 * Count events by type.
 */
export function countByType(events: TelemetryEvent[], eventType: string): number {
  return events.filter((e) => e.event_type === eventType).length;
}

/**
 * Count click events for a specific happy path.
 */
export function countClicks(events: TelemetryEvent[], pathId: string): number {
  return events.filter((e) => e.event_type === 'click' && e.path_id === pathId).length;
}

/**
 * Check if flow_started and flow_completed exist for a path.
 */
export function hasFlowLifecycle(events: TelemetryEvent[], pathId: string) {
  const started = events.some((e) => e.event_type === 'flow_started' && e.path_id === pathId);
  const completed = events.some((e) => e.event_type === 'flow_completed' && e.path_id === pathId);
  return { started, completed };
}

/**
 * Compute average pointer travel from click metadata.
 */
export function avgPointerTravel(events: TelemetryEvent[]): number {
  const samples = events
    .filter((e) => e.event_type === 'click' && e.metadata)
    .map((e) => e.metadata?.pointer_travel_px)
    .filter((v): v is number => typeof v === 'number');
  if (samples.length === 0) return 0;
  return samples.reduce((a, b) => a + b, 0) / samples.length;
}

/**
 * Compute familiar pattern coverage percentage.
 */
export function familiarPatternCoverage(events: TelemetryEvent[]): number {
  const samples = events
    .filter((e) => e.event_type === 'click' && e.metadata && 'familiar_pattern' in e.metadata)
    .map((e) => (e.metadata?.familiar_pattern ? 1 : 0));
  if (samples.length === 0) return 0;
  return (samples.reduce((a, b) => a + b, 0) / samples.length) * 100;
}

/**
 * Compute P95 latency from feedback-latency events.
 */
export function p95Latency(events: TelemetryEvent[]): number {
  const latencies = events
    .filter((e) => e.event_type === 'feedback_latency' && typeof e.latency_ms === 'number')
    .map((e) => e.latency_ms as number)
    .sort((a, b) => a - b);
  if (latencies.length === 0) return 0;
  const idx = Math.min(latencies.length - 1, Math.floor(0.95 * (latencies.length - 1)));
  return latencies[idx];
}
