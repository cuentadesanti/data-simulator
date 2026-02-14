import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export type Stage = 'source' | 'transform' | 'model' | 'publish';
export type InspectorView = 'node' | 'variables';

export interface InspectorContext {
  type: 'node' | 'step' | 'model' | 'column';
  id: string;
}

interface WorkspaceState {
  activeStage: Stage;
  inspectorOpen: boolean;
  inspectorContext: InspectorContext | null;
  inspectorView: InspectorView;
  inspectorViewPinned: boolean;
  leftRailCollapsed: boolean;
}

interface WorkspaceActions {
  setActiveStage: (stage: Stage) => void;
  setInspectorOpen: (open: boolean) => void;
  setInspectorContext: (context: InspectorContext | null) => void;
  setInspectorView: (view: InspectorView) => void;
  pinInspectorView: (view: InspectorView) => void;
  setLeftRailCollapsed: (collapsed: boolean) => void;
}

const initialState: WorkspaceState = {
  activeStage: 'source',
  inspectorOpen: false,
  inspectorContext: null,
  inspectorView: 'node',
  inspectorViewPinned: false,
  leftRailCollapsed: false,
};

export const useWorkspaceStore = create<WorkspaceState & WorkspaceActions>()(
  immer((set) => ({
    ...initialState,
    setActiveStage: (stage) =>
      set((state) => {
        state.activeStage = stage;
      }),
    setInspectorOpen: (open) =>
      set((state) => {
        state.inspectorOpen = open;
      }),
    setInspectorContext: (context) =>
      set((state) => {
        state.inspectorContext = context;
      }),
    setInspectorView: (view) =>
      set((state) => {
        state.inspectorView = view;
      }),
    pinInspectorView: (view) =>
      set((state) => {
        state.inspectorView = view;
        state.inspectorViewPinned = view === 'variables';
      }),
    setLeftRailCollapsed: (collapsed) =>
      set((state) => {
        state.leftRailCollapsed = collapsed;
      }),
  }))
);
