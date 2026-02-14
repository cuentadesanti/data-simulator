import { useEffect, useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { useOnboardingStore } from '../../stores/onboardingStore';
import { tourDefinitions } from './tourDefinitions';
import { TourOverlay } from './TourOverlay';
import { TourTooltip } from './TourTooltip';
import { useTourPositioning } from './useTourPositioning';
import { dispatchTelemetryEvent } from '../../services/telemetry';
import type { TourId } from './types';
import { TOUR_Z } from './types';

const STAGE_LABELS: Record<TourId, string> = {
  main: 'Main Tour',
  source: 'Source',
  transform: 'Transform',
  model: 'Model',
  publish: 'Publish',
  inspector: 'Inspector',
};

export const TourProvider = () => {
  const activeTourId = useOnboardingStore((s) => s.activeTourId);
  const stepIndex = useOnboardingStore((s) => s.activeTourStepIndex);
  const mode = useOnboardingStore((s) => s.activeTourMode);
  const skipReminderShown = useOnboardingStore((s) => s.skipReminderShown);

  const nextStep = useOnboardingStore((s) => s.nextStep);
  const prevStep = useOnboardingStore((s) => s.prevStep);
  const skipTour = useOnboardingStore((s) => s.skipTour);
  const completeTour = useOnboardingStore((s) => s.completeTour);
  const dismissTour = useOnboardingStore((s) => s.dismissTour);
  const markSkipReminderShown = useOnboardingStore((s) => s.markSkipReminderShown);

  const definition = activeTourId ? tourDefinitions[activeTourId] : null;
  const step = definition?.steps[stepIndex] ?? null;

  const targetSelector = step?.target ?? null;
  const isFloating = step?.floating ?? !step?.target;
  const targetRect = useTourPositioning(isFloating ? null : targetSelector);

  // Skip reminder renders independently of the tour tooltip
  const [skipReminderVisible, setSkipReminderVisible] = useState(false);

  // Auto-hide skip reminder after 4s
  useEffect(() => {
    if (!skipReminderVisible) return;
    const timer = setTimeout(() => setSkipReminderVisible(false), 4000);
    return () => clearTimeout(timer);
  }, [skipReminderVisible]);

  // Telemetry: step viewed
  useEffect(() => {
    if (!activeTourId || !step || mode === 'reference') return;
    dispatchTelemetryEvent({
      event_type: 'tour_step_view',
      action: step.id,
      metadata: {
        tour_id: activeTourId,
        step_index: stepIndex,
        step_id: step.id,
        target_found: isFloating ? true : targetRect !== null,
      },
    });
  }, [activeTourId, stepIndex, step?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleNext = useCallback(() => {
    if (!definition) return;

    if (stepIndex >= definition.steps.length - 1) {
      // Last step — complete
      if (mode === 'guided') {
        dispatchTelemetryEvent({
          event_type: 'tour_complete',
          action: definition.id,
          metadata: {
            tour_id: definition.id,
            steps_viewed: stepIndex + 1,
            had_completion_action: !!definition.completionAction,
          },
        });
      }
      if (mode === 'reference') {
        dismissTour();
      } else {
        completeTour();
      }
    } else {
      nextStep();
    }
  }, [definition, stepIndex, mode, nextStep, completeTour, dismissTour]);

  const handlePrev = useCallback(() => {
    prevStep();
  }, [prevStep]);

  const handleSkip = useCallback(() => {
    if (!definition || mode === 'reference') return;

    dispatchTelemetryEvent({
      event_type: 'tour_skip',
      action: definition.id,
      metadata: {
        tour_id: definition.id,
        skipped_at_step: stepIndex,
        total_steps: definition.steps.length,
      },
    });

    if (!skipReminderShown) {
      markSkipReminderShown();
      dispatchTelemetryEvent({
        event_type: 'tour_skip_reminder',
        metadata: {},
      });
      // Show reminder *after* tour is dismissed (rendered independently)
      skipTour();
      setSkipReminderVisible(true);
    } else {
      skipTour();
    }
  }, [definition, mode, stepIndex, skipReminderShown, skipTour, markSkipReminderShown]);

  const handleClose = useCallback(() => {
    if (mode === 'reference') {
      dismissTour();
    } else {
      handleSkip();
    }
  }, [mode, dismissTour, handleSkip]);

  // Standalone skip reminder toast (rendered even when no tour is active)
  const skipReminderElement = skipReminderVisible
    ? createPortal(
        <div
          className="fixed bottom-28 right-4 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600 shadow-lg"
          style={{ zIndex: TOUR_Z.TOOLTIP }}
        >
          You can relaunch tours anytime from the{' '}
          <span className="font-medium text-blue-600">?</span> button.
        </div>,
        document.body,
      )
    : null;

  if (!activeTourId || !step || !definition) return skipReminderElement;

  const padding = step.spotlightPadding ?? 8;

  return createPortal(
    <>
      <TourOverlay
        targetRect={isFloating ? null : targetRect}
        padding={padding}
        visible
        onBackdropClick={handleClose}
      />
      <TourTooltip
        title={step.title}
        content={step.content}
        position={step.position}
        targetRect={isFloating ? null : targetRect}
        floating={isFloating || (!isFloating && targetRect === null)}
        stepIndex={stepIndex}
        totalSteps={definition.steps.length}
        mode={mode}
        tourLabel={STAGE_LABELS[activeTourId]}
        onNext={handleNext}
        onPrev={handlePrev}
        onSkip={handleSkip}
        onClose={handleClose}
      />
      {skipReminderElement}
    </>,
    document.body,
  );
};
