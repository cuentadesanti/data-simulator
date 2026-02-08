export interface PipelineDiagnosticsPayload {
    modelId: string;
    modelName: string;
    modelType: string;
    targetColumn: string;
    selectedFeatures: string[];
    metrics: Record<string, number>;
    coefficients: Record<string, number> | null;
    diagnostics: Record<string, unknown> | null;
    predictionRows: Record<string, unknown>[];
    createdAt?: string;
}
