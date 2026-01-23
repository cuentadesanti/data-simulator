/**
 * Modeling API client for ML model training and prediction.
 */

import type { AxiosInstance } from 'axios';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// =============================================================================
// Types
// =============================================================================

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
    model_params?: Record<string, unknown>;
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
    default: unknown;
    description: string;
    choices?: any[];
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
    model_params: Record<string, unknown>;
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
     * Fit a model on pipeline data
     */
    fit: async (request: FitRequest): Promise<FitResponse> => {
        const response = await api.post<FitResponse>('/api/modeling/fit', request);
        return response.data;
    },

    /**
     * Generate predictions using a fitted model
     */
    predict: async (request: PredictRequest): Promise<PredictResponse> => {
        const response = await api.post<PredictResponse>('/api/modeling/predict', request);
        return response.data;
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
