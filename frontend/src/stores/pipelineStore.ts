/**
 * Pipeline store for managing versioned transform pipelines.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import {
    pipelineApi,
    transformsApi,
    type CreatePipelineResponse,
    type PipelineResponse,
    type SchemaColumn,
    type PipelineStep,
    type TransformInfo,
    type AddStepResponse,
} from '../api/pipelineApi';
import { trackClick, trackCompletionLatency, trackProgressFeedback } from '../services/telemetry';

// =============================================================================
// Types
// =============================================================================

interface PipelineState {
    // Current pipeline
    currentPipelineId: string | null;
    currentVersionId: string | null;
    pipelineDetails: PipelineResponse | null;

    // Schema and data
    schema: SchemaColumn[];
    steps: PipelineStep[];
    previewRows: Record<string, unknown>[];
    materializedRows: Record<string, unknown>[];

    // Transforms catalog
    availableTransforms: TransformInfo[];

    // UI state
    isCreatingPipeline: boolean;
    isApplyingStep: boolean;
    isMaterializing: boolean;
    isLoadingTransforms: boolean;
    lastWarnings: number;
    formulaBarError: string | null;
}

interface PipelineActions {
    // Pipeline operations
    createPipelineFromSimulation: (
        projectId: string,
        name: string,
        dagVersionId: string,
        seed: number,
        sampleSize: number,
        options?: {
            trackClick?: boolean;
            userInitiated?: boolean;
            pathId?: 'HP-1' | 'HP-2' | 'HP-3';
        }
    ) => Promise<CreatePipelineResponse>;
    createPipelineFromUpload: (
        projectId: string,
        name: string,
        sourceId: string
    ) => Promise<CreatePipelineResponse>;

    loadPipeline: (pipelineId: string) => Promise<void>;

    // Step operations
    addStep: (
        stepType: string,
        outputColumn: string,
        params: Record<string, unknown>,
        allowOverwrite?: boolean
    ) => Promise<AddStepResponse>;

    // Materialization
    materialize: (limit?: number, columns?: string[]) => Promise<void>;

    // Transforms catalog
    refreshTransformsCatalog: () => Promise<void>;

    // State management
    clearPipeline: () => void;
    setFormulaBarError: (error: string | null) => void;
}

// =============================================================================
// Store
// =============================================================================

const initialState: PipelineState = {
    currentPipelineId: null,
    currentVersionId: null,
    pipelineDetails: null,
    schema: [],
    steps: [],
    previewRows: [],
    materializedRows: [],
    availableTransforms: [],
    isCreatingPipeline: false,
    isApplyingStep: false,
    isMaterializing: false,
    isLoadingTransforms: false,
    lastWarnings: 0,
    formulaBarError: null,
};

export const usePipelineStore = create<PipelineState & PipelineActions>()(
    immer((set, get) => ({
        ...initialState,

        createPipelineFromSimulation: async (
            projectId,
            name,
            dagVersionId,
            seed,
            sampleSize,
            options
        ) => {
            set((state) => {
                state.isCreatingPipeline = true;
                state.formulaBarError = null;
            });

            try {
                const started = performance.now();
                const result = await pipelineApi.create({
                    project_id: projectId,
                    name,
                    source: {
                        type: 'simulation',
                        dag_version_id: dagVersionId,
                        seed,
                        sample_size: sampleSize,
                    },
                });

                set((state) => {
                    state.currentPipelineId = result.pipeline_id;
                    state.currentVersionId = result.current_version_id;
                    state.schema = result.schema;
                    state.steps = [];
                    state.previewRows = [];
                    state.materializedRows = [];
                    state.isCreatingPipeline = false;
                });
                const pathId = options?.pathId ?? 'HP-1';
                const userInitiated = options?.userInitiated ?? true;
                if (options?.trackClick ?? true) {
                    trackClick(pathId, 'source', 'create_pipeline_simulation', { familiar_pattern: true });
                }
                trackCompletionLatency('pipeline.create.simulation', started, { user_initiated: userInitiated });
                trackProgressFeedback(pathId, 'source', 'pipeline_created');

                return result;
            } catch (error) {
                set((state) => {
                    state.isCreatingPipeline = false;
                    state.formulaBarError =
                        error instanceof Error ? error.message : 'Failed to create pipeline';
                });
                throw error;
            }
        },

        createPipelineFromUpload: async (projectId, name, sourceId) => {
            set((state) => {
                state.isCreatingPipeline = true;
                state.formulaBarError = null;
            });

            try {
                const started = performance.now();
                const result = await pipelineApi.create({
                    project_id: projectId,
                    name,
                    source: {
                        type: 'upload',
                        source_id: sourceId,
                    },
                });

                set((state) => {
                    state.currentPipelineId = result.pipeline_id;
                    state.currentVersionId = result.current_version_id;
                    state.schema = result.schema;
                    state.steps = [];
                    state.previewRows = [];
                    state.materializedRows = [];
                    state.isCreatingPipeline = false;
                });
                trackCompletionLatency('pipeline.create.upload', started, { user_initiated: true });
                trackProgressFeedback('HP-3', 'source', 'pipeline_created');

                return result;
            } catch (error) {
                set((state) => {
                    state.isCreatingPipeline = false;
                    state.formulaBarError =
                        error instanceof Error ? error.message : 'Failed to create pipeline';
                });
                throw error;
            }
        },

        loadPipeline: async (pipelineId) => {
            try {
                const details = await pipelineApi.get(pipelineId);

                set((state) => {
                    state.currentPipelineId = pipelineId;
                    state.pipelineDetails = details;
                    if (details.current_version) {
                        state.currentVersionId = details.current_version.id;
                        state.schema = details.current_version.output_schema;
                        state.steps = details.current_version.steps;
                    }
                });
            } catch (error) {
                console.error('Failed to load pipeline:', error);
                throw error;
            }
        },

        addStep: async (stepType, outputColumn, params, allowOverwrite = false) => {
            const { currentPipelineId, currentVersionId } = get();
            if (!currentPipelineId || !currentVersionId) {
                throw new Error('No active pipeline');
            }

            set((state) => {
                state.isApplyingStep = true;
                state.formulaBarError = null;
            });

            try {
                const started = performance.now();
                const result = await pipelineApi.addStep(currentPipelineId, currentVersionId, {
                    step: {
                        type: stepType,
                        output_column: outputColumn,
                        params,
                        allow_overwrite: allowOverwrite,
                    },
                    preview_limit: 200,
                });

                set((state) => {
                    state.currentVersionId = result.new_version_id;
                    state.schema = result.schema;
                    state.previewRows = result.preview_rows;
                    state.lastWarnings = result.warnings;
                    state.isApplyingStep = false;
                });

                // Reload pipeline to get authoritative step list from server
                await get().loadPipeline(currentPipelineId);
                trackClick('HP-3', 'transform', 'add_step', { familiar_pattern: true });
                trackCompletionLatency('pipeline.add_step', started, { stepType, user_initiated: true });
                trackProgressFeedback('HP-3', 'transform', 'step_applied');

                return result;
            } catch (error) {
                set((state) => {
                    state.isApplyingStep = false;
                    state.formulaBarError =
                        error instanceof Error ? error.message : 'Failed to apply step';
                });
                throw error;
            }
        },

        materialize: async (limit = 1000, columns) => {
            const { currentPipelineId, currentVersionId } = get();
            if (!currentPipelineId || !currentVersionId) {
                throw new Error('No active pipeline');
            }

            set((state) => {
                state.isMaterializing = true;
            });

            try {
                const started = performance.now();
                const result = await pipelineApi.materialize(
                    currentPipelineId,
                    currentVersionId,
                    limit,
                    columns
                );

                set((state) => {
                    state.materializedRows = result.rows;
                    state.isMaterializing = false;
                });
                trackCompletionLatency('pipeline.materialize', started, { limit, user_initiated: true });
                trackProgressFeedback('HP-3', 'transform', 'materialize_complete');
            } catch (error) {
                set((state) => {
                    state.isMaterializing = false;
                });
                throw error;
            }
        },

        refreshTransformsCatalog: async () => {
            set((state) => {
                state.isLoadingTransforms = true;
            });

            try {
                const transforms = await transformsApi.list();
                set((state) => {
                    state.availableTransforms = transforms;
                    state.isLoadingTransforms = false;
                });
            } catch (error) {
                set((state) => {
                    state.isLoadingTransforms = false;
                });
                console.error('Failed to load transforms:', error);
            }
        },

        clearPipeline: () => {
            set(initialState);
        },

        setFormulaBarError: (error) => {
            set((state) => {
                state.formulaBarError = error;
            });
        },
    }))
);

// =============================================================================
// Selectors
// =============================================================================

export const selectCurrentPipelineId = (state: PipelineState & PipelineActions) =>
    state.currentPipelineId;
export const selectCurrentVersionId = (state: PipelineState & PipelineActions) =>
    state.currentVersionId;
export const selectPipelineSchema = (state: PipelineState & PipelineActions) =>
    state.schema;
export const selectPipelineSteps = (state: PipelineState & PipelineActions) =>
    state.steps;
export const selectPreviewRows = (state: PipelineState & PipelineActions) =>
    state.previewRows;
export const selectMaterializedRows = (state: PipelineState & PipelineActions) =>
    state.materializedRows;
export const selectAvailableTransforms = (state: PipelineState & PipelineActions) =>
    state.availableTransforms;
export const selectIsApplyingStep = (state: PipelineState & PipelineActions) =>
    state.isApplyingStep;
export const selectIsMaterializing = (state: PipelineState & PipelineActions) =>
    state.isMaterializing;
export const selectFormulaBarError = (state: PipelineState & PipelineActions) =>
    state.formulaBarError;
export const selectLastWarnings = (state: PipelineState & PipelineActions) =>
    state.lastWarnings;
