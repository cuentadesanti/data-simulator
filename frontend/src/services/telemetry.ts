import api from './api';

export type TelemetryStage = 'source' | 'transform' | 'model' | 'publish';

export interface UXTelemetryEvent {
  event_type: string;
  path_id?: string;
  stage?: TelemetryStage | string;
  action?: string;
  latency_ms?: number;
  metadata?: Record<string, unknown>;
  ts: number;
}

const STORAGE_KEY = 'ux-telemetry-buffer-v1';
const FLUSH_INTERVAL_MS = 30_000;
const MAX_BATCH_SIZE = 200;
const MAX_BUFFER_SIZE = 5_000;
const MAX_CONSECUTIVE_FAILURES = 5;

let buffer: UXTelemetryEvent[] = [];
let initialized = false;
let flushTimer: number | null = null;
let flushing = false;
let consecutiveFailures = 0;

function loadBuffer() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as UXTelemetryEvent[];
    if (Array.isArray(parsed)) {
      buffer = parsed;
    }
  } catch {
    buffer = [];
  }
}

function persistBuffer() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(buffer));
  } catch {
    // Ignore storage quota or serialization issues.
  }
}

async function flushToBackend() {
  if (flushing || buffer.length === 0) return;
  if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) return;
  flushing = true;
  try {
    const batch = buffer.slice(0, MAX_BATCH_SIZE).map((event) => ({
      event_type: event.event_type,
      path_id: event.path_id,
      stage: event.stage,
      action: event.action,
      latency_ms: event.latency_ms,
      metadata: event.metadata || {},
    }));
    await api.post('/api/ux/events', { events: batch });
    buffer = buffer.slice(batch.length);
    persistBuffer();
    consecutiveFailures = 0;
  } catch {
    consecutiveFailures++;
  } finally {
    flushing = false;
  }
}

export function initTelemetry() {
  if (initialized) return;
  initialized = true;
  loadBuffer();
  initPointerTravel();

  flushTimer = window.setInterval(() => {
    void flushToBackend();
  }, FLUSH_INTERVAL_MS);

  window.addEventListener('beforeunload', () => {
    persistBuffer();
  });
}

export function dispatchTelemetryEvent(event: Omit<UXTelemetryEvent, 'ts'>) {
  const fullEvent: UXTelemetryEvent = {
    ...event,
    ts: Date.now(),
  };
  buffer.push(fullEvent);
  if (buffer.length > MAX_BUFFER_SIZE) {
    buffer = buffer.slice(buffer.length - MAX_BUFFER_SIZE);
  }
  persistBuffer();
}

export function trackClick(
  pathId: string | undefined,
  stage: string | undefined,
  action: string,
  extra?: { familiar_pattern?: boolean },
) {
  const meta: Record<string, unknown> = {};
  const travel = _popPointerTravel();
  if (travel !== null) meta.pointer_travel_px = travel;
  if (extra?.familiar_pattern !== undefined) meta.familiar_pattern = extra.familiar_pattern;
  dispatchTelemetryEvent({
    event_type: 'click',
    path_id: pathId,
    stage,
    action,
    metadata: meta,
  });
}

function emitLatencyEvent(
  eventType: 'feedback_latency' | 'completion_latency',
  action: string,
  startMs: number,
  metadata?: Record<string, unknown>,
) {
  const elapsed = Math.max(0, Math.round(performance.now() - startMs));
  dispatchTelemetryEvent({
    event_type: eventType,
    action,
    latency_ms: elapsed,
    metadata: metadata || {},
  });
}

export function trackFeedbackLatency(action: string, startMs: number, metadata?: Record<string, unknown>) {
  emitLatencyEvent('feedback_latency', action, startMs, metadata);
}

export function trackCompletionLatency(action: string, startMs: number, metadata?: Record<string, unknown>) {
  emitLatencyEvent('completion_latency', action, startMs, metadata);
}

export function trackFeedbackLatencyOnNextPaint(
  action: string,
  startMs: number,
  metadata?: Record<string, unknown>,
) {
  requestAnimationFrame(() => {
    trackFeedbackLatency(action, startMs, metadata);
  });
}

export function trackFlowStart(pathId: string) {
  dispatchTelemetryEvent({
    event_type: 'flow_started',
    path_id: pathId,
    metadata: {},
  });
}

export function trackFlowComplete(pathId: string) {
  dispatchTelemetryEvent({
    event_type: 'flow_completed',
    path_id: pathId,
    metadata: {},
  });
}

export function trackManualOrchestration(pathId?: string, stage?: string, action?: string) {
  dispatchTelemetryEvent({
    event_type: 'manual_orchestration',
    path_id: pathId,
    stage,
    action,
    metadata: {},
  });
}

export function trackProgressFeedback(pathId?: string, stage?: string, action?: string) {
  dispatchTelemetryEvent({
    event_type: 'progress_feedback',
    path_id: pathId,
    stage,
    action,
    metadata: {},
  });
}

export function trackVisibleActions(stage: string, count: number) {
  dispatchTelemetryEvent({
    event_type: 'visible_actions_snapshot',
    stage,
    metadata: { count },
  });
}

// ---------------------------------------------------------------------------
// Pointer travel tracker
// Tracks pixel distance between consecutive user clicks.
// ---------------------------------------------------------------------------
let _lastPointerX: number | null = null;
let _lastPointerY: number | null = null;
let _pendingTravel: number | null = null;

function _onPointerClick(e: MouseEvent) {
  if (_lastPointerX !== null && _lastPointerY !== null) {
    const dx = e.clientX - _lastPointerX;
    const dy = e.clientY - _lastPointerY;
    _pendingTravel = Math.round(Math.sqrt(dx * dx + dy * dy));
  }
  _lastPointerX = e.clientX;
  _lastPointerY = e.clientY;
}

function _popPointerTravel(): number | null {
  const v = _pendingTravel;
  _pendingTravel = null;
  return v;
}

export function initPointerTravel() {
  document.addEventListener('click', _onPointerClick, true);
}

export function getTelemetrySnapshot() {
  return {
    total: buffer.length,
    events: [...buffer],
  };
}

export function shutdownTelemetry() {
  if (flushTimer !== null) {
    window.clearInterval(flushTimer);
    flushTimer = null;
  }
  persistBuffer();
}
