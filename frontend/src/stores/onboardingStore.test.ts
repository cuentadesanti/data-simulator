/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useOnboardingStore } from './onboardingStore';

const STORAGE_KEY = 'onboarding-state-v1';

describe('onboardingStore', () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset store to initial state
    useOnboardingStore.setState({
      mainTourStatus: 'new',
      sourceTourDone: false,
      transformTourDone: false,
      modelTourDone: false,
      publishTourDone: false,
      inspectorHintShown: false,
      skipReminderShown: false,
      tourVersions: {},
      activeTourId: null,
      activeTourStepIndex: 0,
      activeTourMode: 'guided',
    });
  });

  describe('startTour / nextStep / prevStep', () => {
    it('starts a tour and tracks step index', () => {
      const { startTour, nextStep, prevStep } = useOnboardingStore.getState();

      startTour('main', 'guided');
      expect(useOnboardingStore.getState().activeTourId).toBe('main');
      expect(useOnboardingStore.getState().activeTourStepIndex).toBe(0);
      expect(useOnboardingStore.getState().activeTourMode).toBe('guided');

      nextStep();
      expect(useOnboardingStore.getState().activeTourStepIndex).toBe(1);

      nextStep();
      expect(useOnboardingStore.getState().activeTourStepIndex).toBe(2);

      prevStep();
      expect(useOnboardingStore.getState().activeTourStepIndex).toBe(1);
    });

    it('prevStep does not go below 0', () => {
      const { startTour, prevStep } = useOnboardingStore.getState();
      startTour('source', 'guided');
      prevStep();
      expect(useOnboardingStore.getState().activeTourStepIndex).toBe(0);
    });
  });

  describe('skipTour', () => {
    it('marks main tour as skipped', () => {
      const { startTour, skipTour } = useOnboardingStore.getState();
      startTour('main', 'guided');
      skipTour();

      const state = useOnboardingStore.getState();
      expect(state.mainTourStatus).toBe('skipped');
      expect(state.activeTourId).toBeNull();
    });

    it('marks stage tour as done on skip', () => {
      const { startTour, skipTour } = useOnboardingStore.getState();
      startTour('source', 'guided');
      skipTour();

      expect(useOnboardingStore.getState().sourceTourDone).toBe(true);
    });
  });

  describe('completeTour', () => {
    it('marks main tour as completed', () => {
      const { startTour, completeTour } = useOnboardingStore.getState();
      startTour('main', 'guided');
      completeTour();

      const state = useOnboardingStore.getState();
      expect(state.mainTourStatus).toBe('completed');
      expect(state.activeTourId).toBeNull();
    });

    it('marks stage tour as done on complete', () => {
      const { startTour, completeTour } = useOnboardingStore.getState();
      startTour('transform', 'guided');
      completeTour();

      expect(useOnboardingStore.getState().transformTourDone).toBe(true);
    });
  });

  describe('dismissTour', () => {
    it('clears active tour without marking done', () => {
      const { startTour, dismissTour } = useOnboardingStore.getState();
      startTour('main', 'reference');
      dismissTour();

      const state = useOnboardingStore.getState();
      expect(state.activeTourId).toBeNull();
      expect(state.mainTourStatus).toBe('new'); // not changed
    });
  });

  describe('localStorage persistence', () => {
    it('round-trips persisted state', () => {
      const { startTour, completeTour, _hydrate } = useOnboardingStore.getState();
      startTour('main', 'guided');
      completeTour();

      // Verify saved to localStorage
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
      expect(saved.mainTourStatus).toBe('completed');

      // Reset store and hydrate
      useOnboardingStore.setState({
        mainTourStatus: 'new',
        sourceTourDone: false,
        activeTourId: null,
        activeTourStepIndex: 0,
      });

      _hydrate();
      expect(useOnboardingStore.getState().mainTourStatus).toBe('completed');
    });

    it('persists stage tour done flags', () => {
      const { startTour, completeTour, _hydrate } = useOnboardingStore.getState();
      startTour('model', 'guided');
      completeTour();

      useOnboardingStore.setState({ modelTourDone: false });
      _hydrate();
      expect(useOnboardingStore.getState().modelTourDone).toBe(true);
    });
  });

  describe('per-tour versioning', () => {
    it('bumpTourVersion increments version counter', () => {
      const { bumpTourVersion } = useOnboardingStore.getState();
      bumpTourVersion('source');
      expect(useOnboardingStore.getState().tourVersions.source).toBe(1);

      bumpTourVersion('source');
      expect(useOnboardingStore.getState().tourVersions.source).toBe(2);
    });
  });

  describe('resetAll', () => {
    it('resets all state to defaults', () => {
      const { startTour, completeTour, markInspectorHintShown, resetAll } =
        useOnboardingStore.getState();

      startTour('main', 'guided');
      completeTour();
      markInspectorHintShown();

      resetAll();

      const state = useOnboardingStore.getState();
      expect(state.mainTourStatus).toBe('new');
      expect(state.inspectorHintShown).toBe(false);
      expect(state.activeTourId).toBeNull();
    });
  });

  describe('markSkipReminderShown', () => {
    it('persists skip reminder state', () => {
      const { markSkipReminderShown, _hydrate } = useOnboardingStore.getState();
      markSkipReminderShown();
      expect(useOnboardingStore.getState().skipReminderShown).toBe(true);

      useOnboardingStore.setState({ skipReminderShown: false });
      _hydrate();
      expect(useOnboardingStore.getState().skipReminderShown).toBe(true);
    });
  });
});
