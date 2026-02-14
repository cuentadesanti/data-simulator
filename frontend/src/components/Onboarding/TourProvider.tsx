import { useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useOnboardingStore } from '../../stores/onboardingStore';
import { tourDefinitions } from './tourDefinitions';
import { TourOverlay } from './TourOverlay';
import { TourTooltip } from './TourTooltip';
import { useTourPositioning } from './useTourPositioning';
import { dispatchTelemetryEvent } from '../../services/telemetry';
import type { TourId } from './types';

const STAGE_LABELS: Record<TourId, string> = {
  main: 'Main Tour',
  source: 'Source',
  transform: 'Transform',
  model: 'Model',
  publish: 'Publish',
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

  // Track whether we should show skip reminder on this skip
  const showSkipReminderRef = useRef(false);

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
    showSkipReminderRef.current = false;

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
      showSkipReminderRef.current = true;
      markSkipReminderShown();
      dispatchTelemetryEvent({
        event_type: 'tour_skip_reminder',
        metadata: {},
      });
    }

    skipTour();
  }, [definition, mode, stepIndex, skipReminderShown, skipTour, markSkipReminderShown]);

  const handleClose = useCallback(() => {
    if (mode === 'reference') {
      dismissTour();
    } else {
      handleSkip();
    }
  }, [mode, dismissTour, handleSkip]);

  // Clear skip reminder after a short time
  useEffect(() => {
    if (showSkipReminderRef.current) {
      const timer = setTimeout(() => {
        showSkipReminderRef.current = false;
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [activeTourId]); // reset when tour changes

  if (!activeTourId || !step || !definition) return null;

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
        showSkipReminder={showSkipReminderRef.current}
      />
    </>,
    document.body,
  );
};
