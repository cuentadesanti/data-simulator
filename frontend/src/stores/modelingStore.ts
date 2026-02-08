import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import {
    modelingApi,
    type ModelTypeInfo,
    type ModelParamValue,
} from '../api/modelingApi';

const SAVED_CONFIGS_KEY = 'data-simulator-model-configs';
const DEFAULT_MODEL_NAME = 'linear_regression';

export interface SavedModelConfig {
    id: string;
    name: string;
    createdAt: string;
    selectedModel: string;
    modelName: string;
    modelParams: Record<string, ModelParamValue>;
    testSize: number;
    targetColumn: string;
    selectedFeatures: string[];
    showAdvanced: boolean;
    showInternal: boolean;
}

interface ModelingState {
    modelTypes: ModelTypeInfo[];
    isLoadingModelTypes: boolean;
    modelTypesLoaded: boolean;

    selectedModel: string;
    modelName: string;
    modelParams: Record<string, ModelParamValue>;
    paramErrors: Record<string, string>;
    testSize: number;
    targetColumn: string;
    selectedFeatures: string[];
    showAdvanced: boolean;
    showInternal: boolean;

    savedConfigs: SavedModelConfig[];
}

interface ModelingActions {
    fetchModelTypes: () => Promise<void>;
    setSelectedModel: (name: string) => void;
    setModelName: (name: string) => void;
    setTargetColumn: (column: string) => void;
    toggleFeature: (column: string) => void;
    setTestSize: (size: number) => void;
    setShowAdvanced: (show: boolean) => void;
    setShowInternal: (show: boolean) => void;
    updateParam: (name: string, value: ModelParamValue, type: string) => void;

    saveCurrentConfig: (configName: string) => SavedModelConfig | null;
    loadConfig: (id: string) => void;
    deleteConfig: (id: string) => void;
}

function loadSavedConfigs(): SavedModelConfig[] {
    if (typeof window === 'undefined') {
        return [];
    }

    try {
        const raw = localStorage.getItem(SAVED_CONFIGS_KEY);
        if (!raw) {
            return [];
        }
        const parsed = JSON.parse(raw) as SavedModelConfig[];
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.warn('Failed to parse saved model configs:', error);
        return [];
    }
}

function persistSavedConfigs(configs: SavedModelConfig[]): void {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        localStorage.setItem(SAVED_CONFIGS_KEY, JSON.stringify(configs));
    } catch (error) {
        console.warn('Failed to persist model configs:', error);
    }
}

function getDefaultModelName(modelTypes: ModelTypeInfo[]): string {
    const linearRegression = modelTypes.find((model) => model.name === DEFAULT_MODEL_NAME);
    if (linearRegression) {
        return linearRegression.name;
    }
    return modelTypes[0]?.name ?? DEFAULT_MODEL_NAME;
}

function getDefaultParams(
    modelTypes: ModelTypeInfo[],
    modelName: string
): Record<string, ModelParamValue> {
    const model = modelTypes.find((item) => item.name === modelName);
    if (!model) {
        return {};
    }

    const defaults: Record<string, ModelParamValue> = {};
    model.parameters.forEach((param) => {
        defaults[param.name] = param.default;
    });
    return defaults;
}

const initialState: ModelingState = {
    modelTypes: [],
    isLoadingModelTypes: false,
    modelTypesLoaded: false,

    selectedModel: DEFAULT_MODEL_NAME,
    modelName: '',
    modelParams: {},
    paramErrors: {},
    testSize: 0.2,
    targetColumn: '',
    selectedFeatures: [],
    showAdvanced: false,
    showInternal: false,

    savedConfigs: loadSavedConfigs(),
};

export const useModelingStore = create<ModelingState & ModelingActions>()(
    immer((set, get) => ({
        ...initialState,

        fetchModelTypes: async () => {
            const { modelTypesLoaded, isLoadingModelTypes } = get();
            if (modelTypesLoaded || isLoadingModelTypes) {
                return;
            }

            set((state) => {
                state.isLoadingModelTypes = true;
            });

            try {
                const modelTypes = await modelingApi.listModels();
                set((state) => {
                    state.modelTypes = modelTypes;
                    state.modelTypesLoaded = true;
                    state.isLoadingModelTypes = false;

                    const hasSelectedModel = modelTypes.some(
                        (model) => model.name === state.selectedModel
                    );
                    const selectedModel = hasSelectedModel
                        ? state.selectedModel
                        : getDefaultModelName(modelTypes);

                    const shouldResetParams =
                        selectedModel !== state.selectedModel ||
                        Object.keys(state.modelParams).length === 0;
                    state.selectedModel = selectedModel;
                    if (shouldResetParams) {
                        state.modelParams = getDefaultParams(modelTypes, selectedModel);
                        state.paramErrors = {};
                    }
                });
            } catch (error) {
                set((state) => {
                    state.isLoadingModelTypes = false;
                });
                console.error('Failed to load model types:', error);
            }
        },

        setSelectedModel: (name) => {
            const { modelTypes } = get();
            set((state) => {
                state.selectedModel = name;
                state.modelParams = getDefaultParams(modelTypes, name);
                state.paramErrors = {};
            });
        },

        setModelName: (name) => {
            set((state) => {
                state.modelName = name;
            });
        },

        setTargetColumn: (column) => {
            set((state) => {
                state.targetColumn = column;
                state.selectedFeatures = state.selectedFeatures.filter(
                    (feature) => feature !== column
                );
            });
        },

        toggleFeature: (column) => {
            set((state) => {
                if (state.selectedFeatures.includes(column)) {
                    state.selectedFeatures = state.selectedFeatures.filter(
                        (feature) => feature !== column
                    );
                    return;
                }
                state.selectedFeatures.push(column);
            });
        },

        setTestSize: (size) => {
            set((state) => {
                state.testSize = size;
            });
        },

        setShowAdvanced: (show) => {
            set((state) => {
                state.showAdvanced = show;
            });
        },

        setShowInternal: (show) => {
            set((state) => {
                state.showInternal = show;
            });
        },

        updateParam: (name, value, type) => {
            let error = '';
            if (value !== '' && value !== null && value !== undefined) {
                if (type === 'int' || type === 'integer') {
                    const n = Number(value);
                    if (!Number.isInteger(n)) {
                        error = 'Must be an integer';
                    }
                } else if (type === 'float' || type === 'number') {
                    const n = Number(value);
                    if (Number.isNaN(n)) {
                        error = 'Must be a number';
                    }
                }
            }

            set((state) => {
                state.modelParams[name] = value;
                state.paramErrors[name] = error;
            });
        },

        saveCurrentConfig: (configName) => {
            const name = configName.trim();
            if (!name) {
                return null;
            }

            const {
                selectedModel,
                modelName,
                modelParams,
                testSize,
                targetColumn,
                selectedFeatures,
                showAdvanced,
                showInternal,
            } = get();

            const config: SavedModelConfig = {
                id: `cfg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
                name,
                createdAt: new Date().toISOString(),
                selectedModel,
                modelName,
                modelParams: { ...modelParams },
                testSize,
                targetColumn,
                selectedFeatures: [...selectedFeatures],
                showAdvanced,
                showInternal,
            };

            set((state) => {
                state.savedConfigs.unshift(config);
                persistSavedConfigs(state.savedConfigs);
            });

            return config;
        },

        loadConfig: (id) => {
            const config = get().savedConfigs.find((item) => item.id === id);
            if (!config) {
                return;
            }

            set((state) => {
                state.selectedModel = config.selectedModel;
                state.modelName = config.modelName;
                state.modelParams = { ...config.modelParams };
                state.paramErrors = {};
                state.testSize = config.testSize;
                state.targetColumn = config.targetColumn;
                state.selectedFeatures = config.selectedFeatures.filter(
                    (feature) => feature !== config.targetColumn
                );
                state.showAdvanced = config.showAdvanced;
                state.showInternal = config.showInternal;
            });
        },

        deleteConfig: (id) => {
            set((state) => {
                state.savedConfigs = state.savedConfigs.filter((config) => config.id !== id);
                persistSavedConfigs(state.savedConfigs);
            });
        },
    }))
);

export const selectModelTypes = (state: ModelingState & ModelingActions) => state.modelTypes;
export const selectIsLoadingModelTypes = (state: ModelingState & ModelingActions) =>
    state.isLoadingModelTypes;
export const selectModelTypesLoaded = (state: ModelingState & ModelingActions) =>
    state.modelTypesLoaded;
export const selectSelectedModel = (state: ModelingState & ModelingActions) =>
    state.selectedModel;
export const selectModelName = (state: ModelingState & ModelingActions) => state.modelName;
export const selectModelParams = (state: ModelingState & ModelingActions) => state.modelParams;
export const selectParamErrors = (state: ModelingState & ModelingActions) => state.paramErrors;
export const selectTestSize = (state: ModelingState & ModelingActions) => state.testSize;
export const selectTargetColumn = (state: ModelingState & ModelingActions) =>
    state.targetColumn;
export const selectSelectedFeatures = (state: ModelingState & ModelingActions) =>
    state.selectedFeatures;
export const selectShowAdvanced = (state: ModelingState & ModelingActions) =>
    state.showAdvanced;
export const selectShowInternal = (state: ModelingState & ModelingActions) =>
    state.showInternal;
export const selectSavedConfigs = (state: ModelingState & ModelingActions) =>
    state.savedConfigs;
