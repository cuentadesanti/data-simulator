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
    type LineageEntry,
    type TransformInfo,
    type AddStepResponse,
    type PipelineVersionMutationResponse,
    type DeleteStepResponse,
} from '../api/pipelineApi';

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
    lineage: LineageEntry[];
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
        sampleSize: number
    ) => Promise<CreatePipelineResponse>;

    loadPipeline: (pipelineId: string) => Promise<void>;

    // Step operations
    addStep: (
        stepType: string,
        outputColumn: string,
        params: Record<string, unknown>,
        allowOverwrite?: boolean
    ) => Promise<AddStepResponse>;
    deleteStep: (
        stepId: string,
        cascade?: boolean,
        previewLimit?: number
    ) => Promise<DeleteStepResponse>;
    reorderSteps: (
        stepIds: string[],
        previewLimit?: number
    ) => Promise<PipelineVersionMutationResponse>;

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
    lineage: [],
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
            sampleSize
        ) => {
            set((state) => {
                state.isCreatingPipeline = true;
                state.formulaBarError = null;
            });

            try {
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
                    state.lineage = [];
                    state.previewRows = [];
                    state.materializedRows = [];
                    state.isCreatingPipeline = false;
                });

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
                        state.lineage = details.current_version.lineage;
                    } else {
                        state.currentVersionId = null;
                        state.schema = [];
                        state.steps = [];
                        state.lineage = [];
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
                    state.materializedRows = [];
                    state.lastWarnings = result.warnings;
                    state.isApplyingStep = false;
                });

                // Reload pipeline to get authoritative step list from server
                await get().loadPipeline(currentPipelineId);

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

        deleteStep: async (stepId, cascade = false, previewLimit = 200) => {
            const { currentPipelineId, currentVersionId } = get();
            if (!currentPipelineId || !currentVersionId) {
                throw new Error('No active pipeline');
            }

            set((state) => {
                state.isApplyingStep = true;
                state.formulaBarError = null;
            });

            try {
                const result = await pipelineApi.deleteStep(
                    currentPipelineId,
                    currentVersionId,
                    stepId,
                    cascade,
                    previewLimit
                );
                set((state) => {
                    state.currentVersionId = result.new_version_id;
                    state.schema = result.schema;
                    state.steps = result.steps;
                    state.lineage = result.lineage;
                    state.previewRows = result.preview_rows;
                    state.materializedRows = [];
                    state.lastWarnings = result.warnings;
                    state.isApplyingStep = false;
                });
                return result;
            } catch (error) {
                set((state) => {
                    state.isApplyingStep = false;
                    state.formulaBarError =
                        error instanceof Error ? error.message : 'Failed to delete step';
                });
                throw error;
            }
        },

        reorderSteps: async (stepIds, previewLimit = 200) => {
            const { currentPipelineId, currentVersionId } = get();
            if (!currentPipelineId || !currentVersionId) {
                throw new Error('No active pipeline');
            }

            set((state) => {
                state.isApplyingStep = true;
                state.formulaBarError = null;
            });

            try {
                const result = await pipelineApi.reorderSteps(currentPipelineId, currentVersionId, {
                    step_ids: stepIds,
                    preview_limit: previewLimit,
                });
                set((state) => {
                    state.currentVersionId = result.new_version_id;
                    state.schema = result.schema;
                    state.steps = result.steps;
                    state.lineage = result.lineage;
                    state.previewRows = result.preview_rows;
                    state.materializedRows = [];
                    state.lastWarnings = result.warnings;
                    state.isApplyingStep = false;
                });
                return result;
            } catch (error) {
                set((state) => {
                    state.isApplyingStep = false;
                    state.formulaBarError =
                        error instanceof Error ? error.message : 'Failed to reorder steps';
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
export const selectPipelineLineage = (state: PipelineState & PipelineActions) =>
    state.lineage;
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
