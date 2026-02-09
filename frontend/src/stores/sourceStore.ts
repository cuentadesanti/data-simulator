import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

type SourceType = 'dag' | 'upload' | null;

interface SourceState {
  sourceType: SourceType;
  uploadedSourceId: string | null;
  sourceSchema: Array<{ name: string; dtype: string }>;
}

interface SourceActions {
  setSourceType: (sourceType: SourceType) => void;
  setUploadedSource: (sourceId: string, schema: Array<{ name: string; dtype: string }>) => void;
  clearSource: () => void;
}

const initialState: SourceState = {
  sourceType: null,
  uploadedSourceId: null,
  sourceSchema: [],
};

export const useSourceStore = create<SourceState & SourceActions>()(
  immer((set) => ({
    ...initialState,
    setSourceType: (sourceType) => {
      set((state) => {
        state.sourceType = sourceType;
        if (sourceType !== 'upload') {
          state.uploadedSourceId = null;
          state.sourceSchema = [];
        }
      });
    },
    setUploadedSource: (sourceId, schema) => {
      set((state) => {
        state.sourceType = 'upload';
        state.uploadedSourceId = sourceId;
        state.sourceSchema = schema;
      });
    },
    clearSource: () => set(initialState),
  }))
);
