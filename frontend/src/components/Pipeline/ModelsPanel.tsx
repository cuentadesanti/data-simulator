import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    Brain,
    Play,
    Loader2,
    ChevronDown,
    ChevronRight,
    Target,
    AlertCircle,
    Settings,
    Youtube,
    Save,
    FolderOpen,
    Trash2,
    ExternalLink,
} from 'lucide-react';
import {
    modelingApi,
    ModelingAPIError,
    type FitResponse,
    type ModelFitSummary,
    type ModelParameter,
    type ModelParamChoiceValue,
    type ModelParamValue,
    type ModelingError,
} from '../../api/modelingApi';
import { Dropdown, type DropdownOption } from '../common';
import {
    usePipelineStore,
    selectCurrentVersionId,
    selectPipelineSchema,
} from '../../stores/pipelineStore';
import {
    useModelingStore,
    selectIsLoadingModelTypes,
    selectModelName,
    selectModelParams,
    selectModelTypes,
    selectParamErrors,
    selectSavedConfigs,
    selectSelectedFeatures,
    selectSelectedModel,
    selectShowAdvanced,
    selectShowInternal,
    selectTargetColumn,
    selectTestSize,
} from '../../stores/modelingStore';
import { getAlwaysVisibleModelParams } from '../../stores/modelCoreParams';
import type { PipelineDiagnosticsPayload } from './types';

interface ModelsPanelProps {
    className?: string;
    onDiagnosticsChange?: (payload: PipelineDiagnosticsPayload | null) => void;
}

const firstSentence = (text: string): string => {
    const trimmed = text.trim();
    if (!trimmed) {
        return '';
    }
    const match = trimmed.match(/^.*?[.!?](?:\s|$)/);
    return match?.[0]?.trim() ?? trimmed;
};

const getChoiceValue = (
    choice: string,
    choices: ModelParamChoiceValue[] | undefined
): ModelParamChoiceValue => {
    if (!choices || choices.length === 0) {
        return choice;
    }
    if (choice === 'null') {
        return null;
    }
    const matched = choices.find((candidate) => String(candidate) === choice);
    return matched ?? choice;
};

const parseNumericType = (type: string): 'int' | 'float' | null => {
    if (type === 'int' || type === 'integer') {
        return 'int';
    }
    if (type === 'float' || type === 'number') {
        return 'float';
    }
    return null;
};

const formatDate = (raw: string) => {
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) {
        return raw;
    }
    return date.toLocaleString();
};

export const ModelsPanel = ({ className = '', onDiagnosticsChange }: ModelsPanelProps) => {
    const schema = usePipelineStore(selectPipelineSchema);
    const currentVersionId = usePipelineStore(selectCurrentVersionId);

    const modelTypes = useModelingStore(selectModelTypes);
    const isLoadingModelTypes = useModelingStore(selectIsLoadingModelTypes);
    const selectedModel = useModelingStore(selectSelectedModel);
    const modelName = useModelingStore(selectModelName);
    const modelParams = useModelingStore(selectModelParams);
    const paramErrors = useModelingStore(selectParamErrors);
    const testSize = useModelingStore(selectTestSize);
    const targetColumn = useModelingStore(selectTargetColumn);
    const selectedFeatures = useModelingStore(selectSelectedFeatures);
    const showAdvanced = useModelingStore(selectShowAdvanced);
    const showInternal = useModelingStore(selectShowInternal);
    const savedConfigs = useModelingStore(selectSavedConfigs);

    const fetchModelTypes = useModelingStore((state) => state.fetchModelTypes);
    const setSelectedModel = useModelingStore((state) => state.setSelectedModel);
    const setModelName = useModelingStore((state) => state.setModelName);
    const setTestSize = useModelingStore((state) => state.setTestSize);
    const setTargetColumn = useModelingStore((state) => state.setTargetColumn);
    const toggleFeature = useModelingStore((state) => state.toggleFeature);
    const setShowAdvanced = useModelingStore((state) => state.setShowAdvanced);
    const setShowInternal = useModelingStore((state) => state.setShowInternal);
    const updateParam = useModelingStore((state) => state.updateParam);
    const saveCurrentConfig = useModelingStore((state) => state.saveCurrentConfig);
    const loadConfig = useModelingStore((state) => state.loadConfig);
    const deleteConfig = useModelingStore((state) => state.deleteConfig);

    const [isFitting, setIsFitting] = useState(false);
    const [fitErrors, setFitErrors] = useState<ModelingError[]>([]);
    const [fitResult, setFitResult] = useState<FitResponse | null>(null);
    const [fittedModels, setFittedModels] = useState<ModelFitSummary[]>([]);
    const [activeDiagnosticsModelId, setActiveDiagnosticsModelId] = useState<string | null>(null);
    const [isLoadingDiagnostics, setIsLoadingDiagnostics] = useState(false);
    const [diagnosticsCache, setDiagnosticsCache] = useState<Record<string, PipelineDiagnosticsPayload>>({});
    const [configName, setConfigName] = useState('');
    const [showSavedConfigs, setShowSavedConfigs] = useState(true);
    const [showLearning, setShowLearning] = useState(false);

    useEffect(() => {
        fetchModelTypes();
    }, [fetchModelTypes]);

    const currentModelType = modelTypes.find((model) => model.name === selectedModel);
    const alwaysVisibleParamNames = useMemo(
        () => (currentModelType ? getAlwaysVisibleModelParams(currentModelType) : new Set<string>()),
        [currentModelType]
    );

    const numericColumns = useMemo(
        () => schema.filter((col) => col.dtype === 'float' || col.dtype === 'int'),
        [schema]
    );

    const coreParams = useMemo(
        () =>
            currentModelType?.parameters.filter((param) =>
                alwaysVisibleParamNames.has(param.name)
            ) ?? [],
        [alwaysVisibleParamNames, currentModelType]
    );
    const advancedParams = useMemo(
        () =>
            currentModelType?.parameters.filter(
                (param) =>
                    !alwaysVisibleParamNames.has(param.name) &&
                    (param.ui_group === 'advanced' || !param.ui_group)
            ) ?? [],
        [alwaysVisibleParamNames, currentModelType]
    );
    const internalParams = useMemo(
        () =>
            currentModelType?.parameters.filter(
                (param) =>
                    !alwaysVisibleParamNames.has(param.name) && param.ui_group === 'internal'
            ) ?? [],
        [alwaysVisibleParamNames, currentModelType]
    );

    const refreshFits = useCallback(async () => {
        if (!currentVersionId) {
            setFittedModels([]);
            return;
        }
        try {
            const fits = await modelingApi.listFits(currentVersionId);
            setFittedModels(fits);
        } catch (error) {
            console.error('Failed to refresh fitted models:', error);
        }
    }, [currentVersionId]);

    useEffect(() => {
        refreshFits();
    }, [refreshFits]);

    useEffect(() => {
        setActiveDiagnosticsModelId(null);
        setDiagnosticsCache({});
    }, [currentVersionId]);

    const activeDiagnosticsPayload = activeDiagnosticsModelId
        ? diagnosticsCache[activeDiagnosticsModelId] ?? null
        : null;

    useEffect(() => {
        onDiagnosticsChange?.(activeDiagnosticsPayload);
    }, [activeDiagnosticsPayload, onDiagnosticsChange]);

    const loadDiagnosticsForModel = useCallback(
        async (modelId: string) => {
            if (!modelId) return;
            if (diagnosticsCache[modelId]) {
                setActiveDiagnosticsModelId(modelId);
                return;
            }

            setIsLoadingDiagnostics(true);
            try {
                const detail = await modelingApi.getFit(modelId);
                const prediction = await modelingApi.predict({
                    model_id: modelId,
                    pipeline_version_id: currentVersionId ?? undefined,
                    limit: 1000,
                });

                const payload: PipelineDiagnosticsPayload = {
                    modelId,
                    modelName: detail.name,
                    modelType: detail.model_type,
                    targetColumn: detail.target_column ?? '',
                    selectedFeatures: detail.feature_spec?.columns ?? [],
                    metrics: detail.metrics,
                    coefficients: detail.coefficients,
                    diagnostics: detail.diagnostics,
                    predictionRows: prediction.preview_rows_with_pred,
                    createdAt: detail.created_at,
                };

                setDiagnosticsCache((prev) => ({ ...prev, [modelId]: payload }));
                setActiveDiagnosticsModelId(modelId);
            } catch (error) {
                console.error('Failed to load model diagnostics:', error);
                setFitErrors([
                    {
                        code: 'VALIDATION_ERROR',
                        message:
                            error instanceof Error
                                ? error.message
                                : 'Failed to load model diagnostics',
                    },
                ]);
            } finally {
                setIsLoadingDiagnostics(false);
            }
        },
        [currentVersionId, diagnosticsCache]
    );

    const handleUpdateParam = (name: string, value: ModelParamValue, type: string) => {
        updateParam(name, value, type);
    };

    const handleSaveConfig = () => {
        const saved = saveCurrentConfig(configName);
        if (saved) {
            setConfigName('');
            setShowSavedConfigs(true);
        }
    };

    const handleFit = async () => {
        if (!currentVersionId) {
            setFitErrors([
                { code: 'VALIDATION_ERROR', message: 'Create a pipeline before fitting models' },
            ]);
            return;
        }
        if (!targetColumn) {
            setFitErrors([
                {
                    code: 'MISSING_TARGET',
                    message: 'Please select a target column',
                    field: 'target',
                    suggestion: 'Choose a numeric column to predict',
                },
            ]);
            return;
        }
        if (selectedFeatures.length === 0) {
            setFitErrors([
                {
                    code: 'INVALID_FEATURES',
                    message: 'Please select at least one feature',
                    field: 'features',
                    suggestion: 'Select one or more numeric columns as input features',
                },
            ]);
            return;
        }
        const hasErrors = Object.values(paramErrors).some((error) => !!error);
        if (hasErrors) {
            setFitErrors([
                {
                    code: 'VALIDATION_ERROR',
                    message: 'Please fix hyperparameter errors before fitting',
                    suggestion: 'Review highlighted parameters in the tuning panel',
                },
            ]);
            return;
        }

        setIsFitting(true);
        setFitErrors([]);
        setFitResult(null);

        try {
            const result = await modelingApi.fit({
                pipeline_version_id: currentVersionId,
                name: modelName || `${selectedModel}_${Date.now()}`,
                model_name: selectedModel,
                target: targetColumn,
                features: selectedFeatures,
                model_params: modelParams,
                split_spec: {
                    type: 'random',
                    test_size: testSize,
                    random_state: 42,
                },
            });
            setFitResult(result);
            await refreshFits();
            await loadDiagnosticsForModel(result.model_id);
        } catch (error) {
            if (error instanceof ModelingAPIError) {
                setFitErrors(error.errors);
            } else {
                setFitErrors([
                    {
                        code: 'VALIDATION_ERROR',
                        message: error instanceof Error ? error.message : 'Failed to fit model',
                    },
                ]);
            }
        } finally {
            setIsFitting(false);
        }
    };

    const modelOptions = modelTypes.map(
        (model): DropdownOption<string> => ({
            value: model.name,
            label: `${model.display_name}${model.coming_soon ? ' (Coming Soon)' : ''}`,
            disabled: model.coming_soon,
            description: firstSentence(model.description),
        })
    );

    const renderParam = (param: ModelParameter) => {
        const hasError = !!paramErrors[param.name];
        const value = modelParams[param.name];
        const numericType = parseNumericType(param.type);
        const isChoice = param.type === 'choice' && (param.choices ?? []).length > 0;
        const isBoolean = param.type === 'boolean' || param.type === 'bool';
        const choiceCount = (param.choices ?? []).length;
        const canUseSegmentedChoices = isChoice && choiceCount > 0 && choiceCount <= 4;
        const hasBounds = param.min_value !== null && param.min_value !== undefined && param.max_value !== null && param.max_value !== undefined;
        const useSlider = !!numericType && hasBounds;

        return (
            <div key={param.name} className="space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                    <label className="text-xs font-medium text-gray-700">{param.display_name}</label>
                    <span className="text-[10px] text-gray-400 font-mono">{param.type}</span>
                </div>

                {isBoolean ? (
                    <label className="inline-flex items-center gap-2 text-xs text-gray-600">
                        <input
                            type="checkbox"
                            checked={!!value}
                            onChange={(event) =>
                                handleUpdateParam(param.name, event.target.checked, param.type)
                            }
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        Enabled
                    </label>
                ) : canUseSegmentedChoices ? (
                    <div className="flex flex-wrap gap-1">
                        {(param.choices ?? []).map((choice) => {
                            const optionValue = choice === null ? 'null' : String(choice);
                            const selected =
                                (value === null ? 'null' : String(value ?? param.default)) === optionValue;
                            return (
                                <button
                                    key={optionValue}
                                    type="button"
                                    onClick={() =>
                                        handleUpdateParam(
                                            param.name,
                                            getChoiceValue(optionValue, param.choices),
                                            param.type
                                        )
                                    }
                                    className={`px-2 py-1 text-xs rounded border ${
                                        selected
                                            ? 'border-blue-400 bg-blue-50 text-blue-700'
                                            : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    {optionValue === 'null' ? 'None' : optionValue}
                                </button>
                            );
                        })}
                    </div>
                ) : isChoice ? (
                    <Dropdown
                        options={(param.choices ?? []).map((choice) => ({
                            value: choice === null ? 'null' : String(choice),
                            label: choice === null ? 'None' : String(choice),
                        }))}
                        value={value === null ? 'null' : String(value ?? param.default)}
                        onChange={(next) =>
                            handleUpdateParam(
                                param.name,
                                getChoiceValue(next, param.choices),
                                param.type
                            )
                        }
                        size="sm"
                        error={hasError}
                    />
                ) : useSlider ? (
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                            <input
                                type="range"
                                min={param.min_value ?? undefined}
                                max={param.max_value ?? undefined}
                                step={numericType === 'int' ? 1 : 0.01}
                                value={typeof value === 'number' ? value : Number(param.default ?? 0)}
                                onChange={(event) => {
                                    const raw = event.target.value;
                                    const parsed =
                                        numericType === 'int'
                                            ? parseInt(raw, 10)
                                            : parseFloat(raw);
                                    handleUpdateParam(param.name, parsed, param.type);
                                }}
                                className="flex-1 accent-blue-600"
                            />
                            <input
                                type="number"
                                min={param.min_value ?? undefined}
                                max={param.max_value ?? undefined}
                                step={numericType === 'int' ? 1 : 0.01}
                                value={typeof value === 'number' ? value : Number(param.default ?? 0)}
                                onChange={(event) => {
                                    const raw = event.target.value;
                                    const parsed =
                                        numericType === 'int'
                                            ? parseInt(raw, 10)
                                            : parseFloat(raw);
                                    handleUpdateParam(
                                        param.name,
                                        Number.isNaN(parsed) ? raw : parsed,
                                        param.type
                                    );
                                }}
                                className={`w-24 rounded border px-2 py-1 text-xs ${
                                    hasError
                                        ? 'border-red-300 bg-red-50'
                                        : 'border-gray-300 bg-white'
                                }`}
                            />
                        </div>
                        {(param.recommended_min !== null && param.recommended_min !== undefined) ||
                        (param.recommended_max !== null && param.recommended_max !== undefined) ? (
                            <div className="text-[10px] text-gray-500">
                                Recommended:{' '}
                                {param.recommended_min ?? param.min_value} -{' '}
                                {param.recommended_max ?? param.max_value}
                            </div>
                        ) : null}
                    </div>
                ) : (
                    <input
                        type={numericType ? 'number' : 'text'}
                        step={numericType === 'int' ? '1' : '0.01'}
                        value={
                            typeof value === 'string' || typeof value === 'number'
                                ? value
                                : ''
                        }
                        onChange={(event) => {
                            const raw = event.target.value;
                            if (!numericType) {
                                handleUpdateParam(param.name, raw, param.type);
                                return;
                            }
                            const parsed =
                                numericType === 'int'
                                    ? parseInt(raw, 10)
                                    : parseFloat(raw);
                            handleUpdateParam(
                                param.name,
                                Number.isNaN(parsed) ? raw : parsed,
                                param.type
                            );
                        }}
                        placeholder={String(param.default ?? '')}
                        className={`w-full rounded border px-2 py-1.5 text-xs ${
                            hasError
                                ? 'border-red-300 bg-red-50'
                                : 'border-gray-300 bg-white'
                        }`}
                    />
                )}

                <p className="text-[10px] text-gray-500 leading-tight">{param.description}</p>
                {hasError && (
                    <p className="text-[10px] text-red-500 flex items-center gap-1">
                        <AlertCircle size={10} />
                        {paramErrors[param.name]}
                    </p>
                )}
            </div>
        );
    };

    const isFitDisabled =
        !currentVersionId ||
        isFitting ||
        !targetColumn ||
        selectedFeatures.length === 0 ||
        !!currentModelType?.coming_soon ||
        modelOptions.length === 0;

    return (
        <div className={`h-full overflow-y-auto ${className}`}>
            <div className="space-y-4">
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Brain size={16} className="text-blue-600" />
                        <h3 className="text-sm font-semibold text-gray-800">Model Configuration</h3>
                    </div>
                    <div className="space-y-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Model Type
                            </label>
                            <Dropdown
                                options={modelOptions}
                                value={selectedModel}
                                onChange={setSelectedModel}
                                disabled={isLoadingModelTypes || isFitting || modelOptions.length === 0}
                                renderOption={(option, isSelected) => {
                                    const model = modelTypes.find((item) => item.name === option.value);
                                    return (
                                        <div
                                            className={`px-3 py-2 border-b border-gray-100 last:border-b-0 ${
                                                isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                                            } ${option.disabled ? 'opacity-50' : 'hover:bg-gray-50'}`}
                                        >
                                            <div className="text-sm font-medium truncate">{option.label}</div>
                                            {option.description && (
                                                <div className="text-[11px] text-gray-500 mt-0.5 leading-tight">
                                                    {option.description}
                                                </div>
                                            )}
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                {model?.category && (
                                                    <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded uppercase tracking-wide">
                                                        {model.category}
                                                    </span>
                                                )}
                                                {(model?.tags ?? []).slice(0, 2).map((tag) => (
                                                    <span
                                                        key={tag}
                                                        className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                }}
                            />
                            {isLoadingModelTypes && (
                                <p className="text-[11px] text-gray-400 mt-1">Loading model catalog...</p>
                            )}
                            {!isLoadingModelTypes && modelOptions.length === 0 && (
                                <p className="text-[11px] text-red-500 mt-1">Model catalog unavailable.</p>
                            )}
                        </div>

                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                Model Name
                            </label>
                            <input
                                type="text"
                                value={modelName}
                                onChange={(event) => setModelName(event.target.value)}
                                placeholder="my_model"
                                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                            />
                        </div>
                    </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
                    <div className="flex items-center gap-2">
                        <Target size={14} className="text-blue-600" />
                        <h4 className="text-sm font-semibold text-gray-800">Training Data Setup</h4>
                    </div>

                    {!currentVersionId ? (
                        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
                            Create a pipeline first to pick target/features and fit models.
                        </div>
                    ) : (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                    Target Column
                                </label>
                                <Dropdown
                                    options={[
                                        { value: '', label: 'Select target...' },
                                        ...numericColumns.map((column) => ({
                                            value: column.name,
                                            label: column.name,
                                        })),
                                    ]}
                                    value={targetColumn}
                                    onChange={setTargetColumn}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                    Feature Columns ({selectedFeatures.length})
                                </label>
                                <div className="max-h-40 overflow-y-auto rounded border border-gray-200">
                                    {numericColumns
                                        .filter((column) => column.name !== targetColumn)
                                        .map((column) => (
                                            <label
                                                key={column.name}
                                                className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50 cursor-pointer"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedFeatures.includes(column.name)}
                                                    onChange={() => toggleFeature(column.name)}
                                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                />
                                                <span>{column.name}</span>
                                                <span className="text-xs text-gray-400 ml-auto">
                                                    {column.dtype}
                                                </span>
                                            </label>
                                        ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                    Test Size: {(testSize * 100).toFixed(0)}%
                                </label>
                                <input
                                    type="range"
                                    min="0.1"
                                    max="0.4"
                                    step="0.05"
                                    value={testSize}
                                    onChange={(event) => setTestSize(parseFloat(event.target.value))}
                                    className="w-full accent-blue-600"
                                />
                            </div>
                        </>
                    )}
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
                    <div className="flex items-center gap-2">
                        <Settings size={14} className="text-blue-600" />
                        <h4 className="text-sm font-semibold text-gray-800">Core Hyperparameters</h4>
                    </div>
                    {coreParams.length === 0 ? (
                        <p className="text-xs text-gray-500">No core parameters for this model.</p>
                    ) : (
                        <div className="space-y-3">{coreParams.map(renderParam)}</div>
                    )}
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
                    <button
                        type="button"
                        onClick={handleFit}
                        disabled={isFitDisabled}
                        className="w-full flex items-center justify-center gap-2 rounded-md bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isFitting ? (
                            <>
                                <Loader2 size={14} className="animate-spin" />
                                Fitting...
                            </>
                        ) : currentModelType?.coming_soon ? (
                            <>Coming Soon</>
                        ) : (
                            <>
                                <Play size={14} />
                                Fit Model
                            </>
                        )}
                    </button>

                    {isLoadingDiagnostics && (
                        <div className="text-xs text-gray-500 flex items-center gap-1">
                            <Loader2 size={12} className="animate-spin" />
                            Loading diagnostics...
                        </div>
                    )}
                    {activeDiagnosticsPayload && (
                        <div className="rounded-md bg-blue-50 border border-blue-200 px-2.5 py-2 text-xs text-blue-700">
                            Diagnostics synced for <strong>{activeDiagnosticsPayload.modelName}</strong>
                            {activeDiagnosticsPayload.createdAt ? (
                                <> ({formatDate(activeDiagnosticsPayload.createdAt)})</>
                            ) : null}
                        </div>
                    )}

                    {fitErrors.length > 0 && (
                        <div className="rounded-md border border-red-200 bg-red-50 p-3 space-y-2">
                            {fitErrors.map((error, index) => (
                                <div key={`${error.code}-${index}`} className="text-xs text-red-700">
                                    <div className="flex items-start gap-1.5">
                                        <AlertCircle size={12} className="mt-0.5" />
                                        <div>
                                            <div>{error.message}</div>
                                            {error.suggestion && (
                                                <div className="text-red-600 mt-0.5">
                                                    Tip: {error.suggestion}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {fitResult && (
                        <div className="rounded-md border border-green-200 bg-green-50 px-2.5 py-2 text-xs text-green-700">
                            Model fitted successfully. Metrics and diagnostics are available in the
                            analysis pane.
                        </div>
                    )}
                </div>

                {advancedParams.length > 0 && (
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                        <button
                            type="button"
                            onClick={() => setShowAdvanced(!showAdvanced)}
                            className="flex items-center gap-1.5 text-sm font-semibold text-gray-700"
                        >
                            {showAdvanced ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            Advanced Parameters ({advancedParams.length})
                        </button>
                        {showAdvanced && <div className="space-y-3 mt-3">{advancedParams.map(renderParam)}</div>}
                    </div>
                )}

                {internalParams.length > 0 && (
                    <div className="rounded-xl border border-gray-200 bg-white p-4">
                        <button
                            type="button"
                            onClick={() => setShowInternal(!showInternal)}
                            className="flex items-center gap-1.5 text-sm font-semibold text-gray-700"
                        >
                            {showInternal ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            Internal Parameters ({internalParams.length})
                        </button>
                        {showInternal && <div className="space-y-3 mt-3">{internalParams.map(renderParam)}</div>}
                    </div>
                )}

                <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
                    <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                        <Save size={14} />
                        Save Configuration
                    </div>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={configName}
                            onChange={(event) => setConfigName(event.target.value)}
                            placeholder="e.g. baseline_linear"
                            className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-xs"
                        />
                        <button
                            type="button"
                            onClick={handleSaveConfig}
                            disabled={!configName.trim()}
                            className="px-2.5 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            Save
                        </button>
                    </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4">
                    <button
                        type="button"
                        onClick={() => setShowSavedConfigs(!showSavedConfigs)}
                        className="w-full flex items-center justify-between"
                    >
                        <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                            <FolderOpen size={14} />
                            Saved Configurations ({savedConfigs.length})
                        </div>
                        {showSavedConfigs ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    {showSavedConfigs && (
                        <div className="mt-3 space-y-2">
                            {savedConfigs.length === 0 ? (
                                <p className="text-xs text-gray-500">No saved configurations yet.</p>
                            ) : (
                                savedConfigs.map((config) => (
                                    <div key={config.id} className="rounded border border-gray-200 p-2">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="min-w-0">
                                                <div className="text-xs font-medium text-gray-700 truncate">
                                                    {config.name}
                                                </div>
                                                <div className="text-[10px] text-gray-500">
                                                    {formatDate(config.createdAt)}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <button
                                                    type="button"
                                                    onClick={() => loadConfig(config.id)}
                                                    className="px-2 py-1 text-[10px] rounded bg-blue-50 text-blue-700 hover:bg-blue-100"
                                                >
                                                    Load
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => deleteConfig(config.id)}
                                                    className="p-1 rounded text-red-500 hover:bg-red-50"
                                                    title="Delete configuration"
                                                >
                                                    <Trash2 size={11} />
                                                </button>
                                            </div>
                                        </div>
                                        <div className="mt-1 text-[10px] text-gray-500">
                                            {config.selectedModel} | {config.selectedFeatures.length} features
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>

                <div className="rounded-xl border border-gray-200 bg-white p-4">
                    <button
                        type="button"
                        onClick={() => setShowLearning(!showLearning)}
                        className="w-full flex items-center justify-between"
                    >
                        <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                            <Youtube size={14} className="text-red-500" />
                            Learning Materials
                        </div>
                        {showLearning ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    {showLearning && (
                        <div className="mt-3 space-y-2">
                            {currentModelType?.video_links && currentModelType.video_links.length > 0 ? (
                                currentModelType.video_links.map((link, index) => (
                                    <a
                                        key={`${link.url}-${index}`}
                                        href={link.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center justify-between gap-2 rounded border border-blue-200 bg-blue-50 px-2.5 py-2 hover:bg-blue-100"
                                    >
                                        <span className="text-xs text-blue-800 truncate">{link.title}</span>
                                        <ExternalLink size={11} className="text-blue-600" />
                                    </a>
                                ))
                            ) : (
                                <p className="text-xs text-gray-500">
                                    Select a model with learning resources to see curated material.
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {fittedModels.length > 0 && (
                    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-2">
                        <h4 className="text-sm font-semibold text-gray-800">
                            Existing Fits ({fittedModels.length})
                        </h4>
                        {fittedModels.map((fit) => {
                            const active = fit.id === activeDiagnosticsModelId;
                            return (
                                <button
                                    key={fit.id}
                                    type="button"
                                    onClick={() => void loadDiagnosticsForModel(fit.id)}
                                    className={`w-full text-left rounded border px-2.5 py-2 ${
                                        active
                                            ? 'border-blue-300 bg-blue-50'
                                            : 'border-gray-200 bg-white hover:border-blue-200'
                                    }`}
                                >
                                    <div className="text-xs font-medium text-gray-700 truncate">{fit.name}</div>
                                    <div className="text-[10px] text-gray-500 mt-0.5">
                                        {fit.model_type} | {formatDate(fit.created_at)}
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};
