import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { TourId, TourMode } from '../components/Onboarding/types';

const STORAGE_KEY = 'onboarding-state-v1';

interface PersistedState {
  mainTourStatus: 'new' | 'skipped' | 'completed';
  sourceTourDone: boolean;
  transformTourDone: boolean;
  modelTourDone: boolean;
  publishTourDone: boolean;
  inspectorHintShown: boolean;
  skipReminderShown: boolean;
  tourVersions: Record<string, number>;
}

interface OnboardingState extends PersistedState {
  activeTourId: TourId | null;
  activeTourStepIndex: number;
  activeTourMode: TourMode;
}

interface OnboardingActions {
  startTour: (tourId: TourId, mode: TourMode) => void;
  nextStep: () => void;
  prevStep: () => void;
  skipTour: () => void;
  completeTour: () => void;
  dismissTour: () => void;
  markStageTourDone: (stage: TourId) => void;
  markInspectorHintShown: () => void;
  markSkipReminderShown: () => void;
  resetTour: (tourId: TourId) => void;
  resetAll: () => void;
  bumpTourVersion: (tourId: TourId) => void;
  _hydrate: () => void;
}

const defaultPersisted: PersistedState = {
  mainTourStatus: 'new',
  sourceTourDone: false,
  transformTourDone: false,
  modelTourDone: false,
  publishTourDone: false,
  inspectorHintShown: false,
  skipReminderShown: false,
  tourVersions: {},
};

const initialState: OnboardingState = {
  ...defaultPersisted,
  activeTourId: null,
  activeTourStepIndex: 0,
  activeTourMode: 'guided',
};

function loadPersistedState(): Partial<PersistedState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<PersistedState>;
  } catch {
    return {};
  }
}

function persistState(state: OnboardingState): void {
  if (typeof window === 'undefined') return;
  try {
    const persisted: PersistedState = {
      mainTourStatus: state.mainTourStatus,
      sourceTourDone: state.sourceTourDone,
      transformTourDone: state.transformTourDone,
      modelTourDone: state.modelTourDone,
      publishTourDone: state.publishTourDone,
      inspectorHintShown: state.inspectorHintShown,
      skipReminderShown: state.skipReminderShown,
      tourVersions: state.tourVersions,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted));
  } catch {
    // Ignore storage errors
  }
}

const stageTourDoneKey = (stage: TourId): keyof PersistedState | null => {
  switch (stage) {
    case 'source': return 'sourceTourDone';
    case 'transform': return 'transformTourDone';
    case 'model': return 'modelTourDone';
    case 'publish': return 'publishTourDone';
    default: return null;
  }
};

export const useOnboardingStore = create<OnboardingState & OnboardingActions>()(
  immer((set) => ({
    ...initialState,

    startTour: (tourId, mode) =>
      set((state) => {
        state.activeTourId = tourId;
        state.activeTourStepIndex = 0;
        state.activeTourMode = mode;
      }),

    nextStep: () =>
      set((state) => {
        state.activeTourStepIndex += 1;
      }),

    prevStep: () =>
      set((state) => {
        if (state.activeTourStepIndex > 0) {
          state.activeTourStepIndex -= 1;
        }
      }),

    skipTour: () =>
      set((state) => {
        const tourId = state.activeTourId;
        if (!tourId) return;

        if (tourId === 'main') {
          state.mainTourStatus = 'skipped';
        } else {
          const key = stageTourDoneKey(tourId);
          if (key && key !== 'mainTourStatus' && key !== 'inspectorHintShown' && key !== 'skipReminderShown' && key !== 'tourVersions') {
            (state as Record<string, unknown>)[key] = true;
          }
        }

        state.activeTourId = null;
        state.activeTourStepIndex = 0;
        persistState(state);
      }),

    completeTour: () =>
      set((state) => {
        const tourId = state.activeTourId;
        if (!tourId) return;

        if (tourId === 'main') {
          state.mainTourStatus = 'completed';
        } else {
          const key = stageTourDoneKey(tourId);
          if (key && key !== 'mainTourStatus' && key !== 'inspectorHintShown' && key !== 'skipReminderShown' && key !== 'tourVersions') {
            (state as Record<string, unknown>)[key] = true;
          }
        }

        state.activeTourId = null;
        state.activeTourStepIndex = 0;
        persistState(state);
      }),

    dismissTour: () =>
      set((state) => {
        state.activeTourId = null;
        state.activeTourStepIndex = 0;
      }),

    markStageTourDone: (stage) =>
      set((state) => {
        const key = stageTourDoneKey(stage);
        if (key && key !== 'mainTourStatus' && key !== 'inspectorHintShown' && key !== 'skipReminderShown' && key !== 'tourVersions') {
          (state as Record<string, unknown>)[key] = true;
        }
        persistState(state);
      }),

    markInspectorHintShown: () =>
      set((state) => {
        state.inspectorHintShown = true;
        persistState(state);
      }),

    markSkipReminderShown: () =>
      set((state) => {
        state.skipReminderShown = true;
        persistState(state);
      }),

    resetTour: (tourId) =>
      set((state) => {
        if (tourId === 'main') {
          state.mainTourStatus = 'new';
        } else {
          const key = stageTourDoneKey(tourId);
          if (key && key !== 'mainTourStatus' && key !== 'inspectorHintShown' && key !== 'skipReminderShown' && key !== 'tourVersions') {
            (state as Record<string, unknown>)[key] = false;
          }
        }
        persistState(state);
      }),

    resetAll: () =>
      set((state) => {
        Object.assign(state, defaultPersisted);
        state.activeTourId = null;
        state.activeTourStepIndex = 0;
        persistState(state);
      }),

    bumpTourVersion: (tourId) =>
      set((state) => {
        state.tourVersions[tourId] = (state.tourVersions[tourId] ?? 0) + 1;
        persistState(state);
      }),

    _hydrate: () =>
      set((state) => {
        const saved = loadPersistedState();
        if (saved.mainTourStatus !== undefined) state.mainTourStatus = saved.mainTourStatus;
        if (saved.sourceTourDone !== undefined) state.sourceTourDone = saved.sourceTourDone;
        if (saved.transformTourDone !== undefined) state.transformTourDone = saved.transformTourDone;
        if (saved.modelTourDone !== undefined) state.modelTourDone = saved.modelTourDone;
        if (saved.publishTourDone !== undefined) state.publishTourDone = saved.publishTourDone;
        if (saved.inspectorHintShown !== undefined) state.inspectorHintShown = saved.inspectorHintShown;
        if (saved.skipReminderShown !== undefined) state.skipReminderShown = saved.skipReminderShown;
        if (saved.tourVersions !== undefined) state.tourVersions = saved.tourVersions;
      }),
  }))
);

export const selectActiveTourId = (state: OnboardingState & OnboardingActions) => state.activeTourId;
export const selectActiveTourStepIndex = (state: OnboardingState & OnboardingActions) => state.activeTourStepIndex;
export const selectActiveTourMode = (state: OnboardingState & OnboardingActions) => state.activeTourMode;
export const selectMainTourStatus = (state: OnboardingState & OnboardingActions) => state.mainTourStatus;
