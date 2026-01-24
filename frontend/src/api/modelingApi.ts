/**
 * Modeling API client for ML model training and prediction.
 */

import api from '../services/api';
import type { AxiosError } from 'axios';

// =============================================================================
// Error Types
// =============================================================================

export type ModelingErrorCode =
    | 'PIPELINE_NOT_FOUND'
    | 'MODEL_NOT_FOUND'
    | 'UNKNOWN_MODEL_TYPE'
    | 'MISSING_TARGET'
    | 'INVALID_TARGET'
    | 'INVALID_FEATURES'
    | 'NO_VALID_ROWS'
    | 'INTEGRITY_ERROR'
    | 'VALIDATION_ERROR';

export interface ModelingError {
    code: ModelingErrorCode;
    message: string;
    field?: string;
    suggestion?: string;
    context?: Record<string, unknown>;
}

export interface ModelingErrorResponse {
    success: false;
    errors: ModelingError[];
}

export class ModelingAPIError extends Error {
    public readonly errors: ModelingError[];
    public readonly firstError: ModelingError;

    constructor(errors: ModelingError[]) {
        const firstError = errors[0];
        super(firstError?.message || 'Modeling operation failed');
        this.name = 'ModelingAPIError';
        this.errors = errors;
        this.firstError = firstError;
    }
}

function isModelingErrorResponse(data: unknown): data is ModelingErrorResponse {
    return (
        typeof data === 'object' &&
        data !== null &&
        'success' in data &&
        (data as ModelingErrorResponse).success === false &&
        'errors' in data &&
        Array.isArray((data as ModelingErrorResponse).errors)
    );
}

// =============================================================================
// Types
// =============================================================================

/** Valid types for model hyperparameter choice options */
export type ModelParamChoiceValue = string | number | boolean | null;

/** Valid types for model hyperparameter values */
export type ModelParamValue = string | number | boolean | null;

export interface SplitSpec {
    type: 'random' | 'none';
    test_size?: number;
    random_state?: number;
}

export interface FitRequest {
    pipeline_version_id: string;
    name: string;
    model_name: string;
    target?: string;
    features: string[];
    model_params?: Record<string, ModelParamValue>;
    split_spec?: SplitSpec;
}

export interface FitResponse {
    model_id: string;
    metrics: Record<string, number>;
    coefficients: Record<string, number> | null;
    diagnostics: Record<string, unknown> | null;
}

export interface PredictRequest {
    model_id: string;
    pipeline_version_id?: string;
    limit?: number;
}

export interface PredictResponse {
    predictions: (number | null)[];
    preview_rows_with_pred: Record<string, unknown>[];
}

export interface ModelParameter {
    name: string;
    display_name: string;
    type: string;
    required: boolean;
    default: ModelParamValue;
    description: string;
    choices?: ModelParamChoiceValue[];
    min_value?: number | null;
    max_value?: number | null;
    recommended_min?: number | null;
    recommended_max?: number | null;
    log_scale?: boolean;
    ui_group?: 'core' | 'advanced' | 'internal';
}

export interface ModelTypeInfo {
    name: string;
    display_name: string;
    description: string;
    task_type: 'regression';
    category?: string;
    parameters: ModelParameter[];
    // UI metadata
    icon?: string;
    complexity?: number;
    coming_soon?: boolean;
    tags?: string[];
    video_links?: { title: string; url: string }[];
}

export interface ModelFitSummary {
    id: string;
    name: string;
    model_type: string;
    task_type: string;
    target_column?: string;
    metrics: Record<string, number>;
    created_at: string;
}

export interface ModelFitDetail extends ModelFitSummary {
    pipeline_version_id: string;
    feature_spec: { columns: string[] };
    split_spec: SplitSpec;
    model_params: Record<string, ModelParamValue>;
    coefficients: Record<string, number> | null;
    diagnostics: Record<string, unknown> | null;
}

// =============================================================================
// API Functions
// =============================================================================

export const modelingApi = {
    /**
     * List available model types
     */
    listModels: async (): Promise<ModelTypeInfo[]> => {
        const response = await api.get<{ models: ModelTypeInfo[] }>('/api/modeling/models');
        return response.data.models;
    },

    /**
     * Fit a model on pipeline data.
     * Throws ModelingAPIError with structured errors on failure.
     */
    fit: async (request: FitRequest): Promise<FitResponse> => {
        try {
            const response = await api.post<FitResponse>('/api/modeling/fit', request);
            return response.data;
        } catch (error) {
            const axiosError = error as AxiosError;
            if (axiosError.response?.data && isModelingErrorResponse(axiosError.response.data)) {
                throw new ModelingAPIError(axiosError.response.data.errors);
            }
            throw error;
        }
    },

    /**
     * Generate predictions using a fitted model.
     * Throws ModelingAPIError with structured errors on failure.
     */
    predict: async (request: PredictRequest): Promise<PredictResponse> => {
        try {
            const response = await api.post<PredictResponse>('/api/modeling/predict', request);
            return response.data;
        } catch (error) {
            const axiosError = error as AxiosError;
            if (axiosError.response?.data && isModelingErrorResponse(axiosError.response.data)) {
                throw new ModelingAPIError(axiosError.response.data.errors);
            }
            throw error;
        }
    },

    /**
     * List model fits
     */
    listFits: async (pipelineVersionId?: string): Promise<ModelFitSummary[]> => {
        const params = pipelineVersionId
            ? `?pipeline_version_id=${pipelineVersionId}`
            : '';
        const response = await api.get<{ model_fits: ModelFitSummary[] }>(
            `/api/modeling/fits${params}`
        );
        return response.data.model_fits;
    },

    /**
     * Get model fit details
     */
    getFit: async (modelId: string): Promise<ModelFitDetail> => {
        const response = await api.get<ModelFitDetail>(`/api/modeling/fits/${modelId}`);
        return response.data;
    },
};
