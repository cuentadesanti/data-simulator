/**
 * Pipeline API client for managing versioned transform pipelines.
 */

import api from '../services/api';

// =============================================================================
// Types
// =============================================================================

export interface SchemaColumn {
    name: string;
    dtype: string;
}

export interface SimulationSource {
    type: 'simulation';
    dag_version_id: string;
    seed: number;
    sample_size: number;
}

export interface UploadSource {
    type: 'upload';
    source_id: string;
}

export interface CreatePipelineRequest {
    project_id: string;
    name: string;
    source: SimulationSource | UploadSource;
}

export interface CreatePipelineResponse {
    pipeline_id: string;
    current_version_id: string;
    schema: SchemaColumn[];
}

export interface StepSpec {
    type: string;
    output_column: string;
    params: Record<string, unknown>;
    allow_overwrite?: boolean;
}

export interface AddStepRequest {
    step: StepSpec;
    preview_limit?: number;
}

export interface AddStepResponse {
    new_version_id: string;
    schema: SchemaColumn[];
    added_columns: string[];
    preview_rows: Record<string, unknown>[];
    warnings: number;
}

export interface MaterializeResponse {
    schema: SchemaColumn[];
    rows: Record<string, unknown>[];
}

export interface ResimulateRequest {
    seed: number;
    sample_size: number;
}

export interface ResimulateResponse {
    new_pipeline_id: string;
    current_version_id: string;
}

export interface PipelineVersionSummary {
    id: string;
    version_number: number;
    steps_count: number;
    created_at: string;
}

export interface PipelineStep {
    step_id: string;
    type: string;
    output_column: string;
    params: Record<string, unknown>;
    order: number;
    created_at: string;
}

export interface LineageEntry {
    output_col: string;
    inputs: string[];
    step_id: string;
    transform_name: string;
}

export interface CurrentVersionDetail {
    id: string;
    version_number: number;
    steps: PipelineStep[];
    input_schema: SchemaColumn[];
    output_schema: SchemaColumn[];
    lineage: LineageEntry[];
}

export interface PipelineDetail {
    id: string;
    project_id: string;
    name: string;
    source_type: string;
    created_at: string;
}

export interface PipelineResponse {
    pipeline: PipelineDetail;
    current_version: CurrentVersionDetail | null;
    versions_summary: PipelineVersionSummary[];
}

export interface PipelineSummary {
    id: string;
    name: string;
    source_type: string;
    current_version_id: string | null;
    versions_count: number;
    created_at: string;
}

export interface TransformParameter {
    name: string;
    display_name: string;
    type: string;
    required: boolean;
    default: unknown;
    description: string;
}

export interface TransformInfo {
    name: string;
    display_name: string;
    description: string;
    parameters: TransformParameter[];
}

// =============================================================================
// API Functions
// =============================================================================

export const pipelineApi = {
    /**
     * Create a new pipeline from a simulation source
     */
    create: async (request: CreatePipelineRequest): Promise<CreatePipelineResponse> => {
        const response = await api.post<CreatePipelineResponse>('/api/pipelines', request);
        return response.data;
    },

    /**
     * Get pipeline details
     */
    get: async (pipelineId: string): Promise<PipelineResponse> => {
        const response = await api.get<PipelineResponse>(`/api/pipelines/${pipelineId}`);
        return response.data;
    },

    /**
     * List pipelines for a project
     */
    list: async (projectId: string): Promise<PipelineSummary[]> => {
        const response = await api.get<{ pipelines: PipelineSummary[] }>(
            `/api/pipelines?project_id=${projectId}`
        );
        return response.data.pipelines;
    },

    /**
     * Add a transform step to a pipeline
     */
    addStep: async (
        pipelineId: string,
        versionId: string,
        request: AddStepRequest
    ): Promise<AddStepResponse> => {
        const response = await api.post<AddStepResponse>(
            `/api/pipelines/${pipelineId}/versions/${versionId}/steps`,
            request
        );
        return response.data;
    },

    /**
     * Materialize pipeline data
     */
    materialize: async (
        pipelineId: string,
        versionId: string,
        limit?: number,
        columns?: string[]
    ): Promise<MaterializeResponse> => {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());
        if (columns && columns.length > 0) params.append('columns', columns.join(','));

        const response = await api.get<MaterializeResponse>(
            `/api/pipelines/${pipelineId}/versions/${versionId}/materialization?${params.toString()}`
        );
        return response.data;
    },

    /**
     * Resimulate with different seed/sample_size
     */
    resimulate: async (
        pipelineId: string,
        versionId: string,
        request: ResimulateRequest
    ): Promise<ResimulateResponse> => {
        const response = await api.post<ResimulateResponse>(
            `/api/pipelines/${pipelineId}/versions/${versionId}/resimulate`,
            request
        );
        return response.data;
    },
};

export const transformsApi = {
    /**
     * List all available transforms
     */
    list: async (): Promise<TransformInfo[]> => {
        const response = await api.get<{ transforms: TransformInfo[] }>('/api/transforms');
        return response.data.transforms;
    },
};
