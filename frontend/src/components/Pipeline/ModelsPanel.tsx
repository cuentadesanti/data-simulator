/**
 * ModelsPanel component for training and viewing ML models.
 */

import { useState, useEffect } from 'react';
import {
    Brain,
    Play,
    Loader2,
    ChevronDown,
    ChevronRight,
    Target,
    BarChart3,
    ArrowRight,
    Settings,
    AlertCircle,
} from 'lucide-react';
import { modelingApi, type ModelTypeInfo, type FitResponse } from '../../api/modelingApi';
import {
    usePipelineStore,
    selectPipelineSchema,
    selectCurrentVersionId,
} from '../../stores/pipelineStore';

export const ModelsPanel = () => {
    const schema = usePipelineStore(selectPipelineSchema);
    const currentVersionId = usePipelineStore(selectCurrentVersionId);

    // Model types catalog
    const [modelTypes, setModelTypes] = useState<ModelTypeInfo[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);

    // Form state
    const [selectedModel, setSelectedModel] = useState('linear_regression');
    const [targetColumn, setTargetColumn] = useState('');
    const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
    const [modelName, setModelName] = useState('');
    const [testSize, setTestSize] = useState(0.2);
    const [modelParams, setModelParams] = useState<Record<string, any>>({});
    const [paramErrors, setParamErrors] = useState<Record<string, string>>({});
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [showInternal, setShowInternal] = useState(false);

    // Fit results
    const [isFitting, setIsFitting] = useState(false);
    const [fitResult, setFitResult] = useState<FitResponse | null>(null);
    const [fitError, setFitError] = useState<string | null>(null);


    // Load model types on mount
    useEffect(() => {
        const loadModelTypes = async () => {
            setIsLoadingModels(true);
            try {
                const models = await modelingApi.listModels();
                setModelTypes(models);
            } catch (error) {
                console.error('Failed to load model types:', error);
            } finally {
                setIsLoadingModels(false);
            }
        };
        loadModelTypes();
    }, []);

    // Refresh fitted models when needed
    const refreshFits = async () => {
        if (!currentVersionId) return;
        try {
            await modelingApi.listFits(currentVersionId);
        } catch (error) {
            console.error('Failed to refresh fitted models:', error);
        }
    };

    useEffect(() => {
        refreshFits();
    }, [currentVersionId]);

    // Reset parameters when model changes
    useEffect(() => {
        const model = modelTypes.find((m) => m.name === selectedModel);
        if (model) {
            const defaults: Record<string, any> = {};
            model.parameters.forEach((p) => {
                defaults[p.name] = p.default;
            });
            setModelParams(defaults);
            setParamErrors({});
        }
    }, [selectedModel, modelTypes]);

    // Get numeric columns for features/target
    const numericColumns = schema.filter(
        (col) => col.dtype === 'float' || col.dtype === 'int'
    );

    const currentModelType = modelTypes.find((m) => m.name === selectedModel);

    const handleToggleFeature = (colName: string) => {
        setSelectedFeatures((prev) =>
            prev.includes(colName)
                ? prev.filter((f) => f !== colName)
                : [...prev, colName]
        );
    };

    const handleUpdateParam = (name: string, value: any, type: string) => {
        setModelParams(prev => ({ ...prev, [name]: value }));

        // Basic validation
        let error = '';
        if (value !== '' && value !== null && value !== undefined) {
            if (type === 'int') {
                const n = Number(value);
                if (!Number.isInteger(n)) {
                    error = 'Must be an integer';
                }
            } else if (type === 'float') {
                const n = Number(value);
                if (isNaN(n)) {
                    error = 'Must be a number';
                }
            }
        }

        setParamErrors(prev => ({ ...prev, [name]: error }));
    };

    const handleFit = async () => {
        if (!currentVersionId) {
            setFitError('No active pipeline version');
            return;
        }

        if (!targetColumn) {
            setFitError('Please select a target column');
            return;
        }

        if (selectedFeatures.length === 0) {
            setFitError('Please select at least one feature');
            return;
        }

        // Check if there are any parameter errors
        const hasErrors = Object.values(paramErrors).some(err => !!err);
        if (hasErrors) {
            setFitError('Please fix hyperparameter errors before fitting');
            return;
        }

        setIsFitting(true);
        setFitError(null);
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
            refreshFits(); // Refresh the fitted models list
        } catch (error) {
            setFitError(error instanceof Error ? error.message : 'Failed to fit model');
        } finally {
            setIsFitting(false);
        }
    };


    if (!currentVersionId) {
        return (
            <div className="p-4 text-center text-gray-400 text-sm">
                Create a pipeline to train models.
            </div>
        );
    }

    return (
        <div className="bg-white border-l border-gray-200 w-80 flex flex-col h-full">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
                <Brain size={16} className="text-purple-500" />
                <h3 className="font-medium text-sm">Model Training</h3>
            </div>

            {/* Form */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Model name */}
                <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                        Model Name
                    </label>
                    <input
                        type="text"
                        value={modelName}
                        onChange={(e) => setModelName(e.target.value)}
                        placeholder="my_model"
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                </div>

                {/* Model type selector */}
                <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                        Model Type
                    </label>
                    <div className="relative">
                        <select
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            disabled={isLoadingModels}
                            className="w-full appearance-none bg-gray-50 border border-gray-300 rounded-md pl-3 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                            {modelTypes.map((m) => (
                                <option key={m.name} value={m.name}>
                                    {m.display_name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={14}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                        />
                    </div>
                    {currentModelType && (
                        <p className="text-xs text-gray-400 mt-1 capitalize">
                            {currentModelType.task_type}
                        </p>
                    )}
                </div>

                {/* Model Parameters */}
                {currentModelType && currentModelType.parameters.length > 0 && (() => {
                    const coreParams = currentModelType.parameters.filter(p => p.ui_group === 'core');
                    const advancedParams = currentModelType.parameters.filter(p => p.ui_group === 'advanced' || !p.ui_group);
                    const internalParams = currentModelType.parameters.filter(p => p.ui_group === 'internal');

                    const renderParam = (p: typeof currentModelType.parameters[0]) => {
                        const hasError = !!paramErrors[p.name];
                        const isChoice = p.type === 'choice' && p.choices && p.choices.length > 0;
                        const isBoolean = p.type === 'boolean' || p.type === 'bool';

                        return (
                            <div key={p.name}>
                                <div className="flex justify-between items-center mb-1">
                                    <label className="text-xs font-medium text-gray-700">
                                        {p.display_name}
                                    </label>
                                    <span className={`text-[10px] font-mono italic ${hasError ? 'text-red-500' : 'text-gray-400'}`}>
                                        {p.type}
                                    </span>
                                </div>

                                {isBoolean ? (
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={!!modelParams[p.name]}
                                            onChange={(e) => handleUpdateParam(p.name, e.target.checked, p.type)}
                                            className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                                        />
                                        <span className="text-xs text-gray-500">Enabled</span>
                                    </label>
                                ) : isChoice ? (
                                    <div className="relative">
                                        <select
                                            value={modelParams[p.name] === null ? 'null' : String(modelParams[p.name] ?? p.default)}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                handleUpdateParam(p.name, val === 'null' ? null : val, p.type);
                                            }}
                                            className={`w-full appearance-none bg-white border rounded-md pl-2 pr-8 py-1.5 text-xs focus:outline-none focus:ring-1 ${hasError
                                                ? 'border-red-300 focus:ring-red-500'
                                                : 'border-gray-300 focus:ring-purple-500'
                                                }`}
                                        >
                                            {p.choices?.map((choice) => (
                                                <option key={choice === null ? 'null' : String(choice)} value={choice === null ? 'null' : String(choice)}>
                                                    {choice === null ? 'None' : String(choice)}
                                                </option>
                                            ))}
                                        </select>
                                        <ChevronDown
                                            size={12}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                                        />
                                    </div>
                                ) : (
                                    <>
                                        <input
                                            type={p.type === 'int' || p.type === 'integer' || p.type === 'float' || p.type === 'number' ? 'number' : 'text'}
                                            step={p.type === 'float' || p.type === 'number' ? '0.01' : '1'}
                                            value={modelParams[p.name] ?? ''}
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                const parsed = (p.type === 'int' || p.type === 'integer') ? parseInt(val) : (p.type === 'float' || p.type === 'number') ? parseFloat(val) : val;
                                                handleUpdateParam(p.name, isNaN(parsed as any) ? val : parsed, p.type);
                                            }}
                                            placeholder={String(p.default)}
                                            className={`w-full border rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 ${hasError
                                                ? 'border-red-300 bg-red-50 focus:ring-red-500'
                                                : 'border-gray-300 focus:ring-purple-500'
                                                }`}
                                        />
                                        {hasError && (
                                            <p className="text-[10px] text-red-500 mt-1 flex items-center gap-1">
                                                <AlertCircle size={10} />
                                                {paramErrors[p.name]}
                                            </p>
                                        )}
                                    </>
                                )}
                                <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">
                                    {p.description}
                                </p>
                            </div>
                        );
                    };

                    return (
                        <div className="bg-gray-50 rounded-lg p-3 border border-gray-100 space-y-3">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                                <Settings size={12} />
                                Hyperparameters
                            </div>

                            {/* Core Parameters - Always visible */}
                            {coreParams.length > 0 && (
                                <div className="space-y-3">
                                    {coreParams.map(renderParam)}
                                </div>
                            )}

                            {/* Advanced Parameters - Collapsible */}
                            {advancedParams.length > 0 && (
                                <div className="border-t border-gray-200 pt-2 mt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowAdvanced(!showAdvanced)}
                                        className="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 w-full"
                                    >
                                        {showAdvanced ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                        Advanced ({advancedParams.length})
                                    </button>
                                    {showAdvanced && (
                                        <div className="space-y-3 mt-2">
                                            {advancedParams.map(renderParam)}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Internal Parameters - Collapsible */}
                            {internalParams.length > 0 && (
                                <div className="border-t border-gray-200 pt-2 mt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowInternal(!showInternal)}
                                        className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-gray-600 w-full"
                                    >
                                        {showInternal ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                        Internal ({internalParams.length})
                                    </button>
                                    {showInternal && (
                                        <div className="space-y-3 mt-2">
                                            {internalParams.map(renderParam)}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })()}

                {/* Target column */}
                <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                        <Target size={12} />
                        Target Column
                    </label>
                    <div className="relative">
                        <select
                            value={targetColumn}
                            onChange={(e) => setTargetColumn(e.target.value)}
                            className="w-full appearance-none bg-gray-50 border border-gray-300 rounded-md pl-3 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                            <option value="">Select target...</option>
                            {numericColumns.map((col) => (
                                <option key={col.name} value={col.name}>
                                    {col.name}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={14}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                        />
                    </div>
                </div>

                {/* Feature columns */}
                <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                        Feature Columns ({selectedFeatures.length} selected)
                    </label>
                    <div className="border border-gray-200 rounded-md max-h-40 overflow-y-auto">
                        {numericColumns
                            .filter((col) => col.name !== targetColumn)
                            .map((col) => (
                                <label
                                    key={col.name}
                                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer"
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedFeatures.includes(col.name)}
                                        onChange={() => handleToggleFeature(col.name)}
                                        className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                                    />
                                    <span className="text-sm">{col.name}</span>
                                    <span className="text-xs text-gray-400 ml-auto">{col.dtype}</span>
                                </label>
                            ))}
                    </div>
                </div>

                {/* Test size */}
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
                        onChange={(e) => setTestSize(parseFloat(e.target.value))}
                        className="w-full accent-purple-600"
                    />
                </div>

                {/* Fit button */}
                <button
                    onClick={handleFit}
                    disabled={isFitting || !targetColumn || selectedFeatures.length === 0}
                    className="w-full flex items-center justify-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isFitting ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Fitting...
                        </>
                    ) : (
                        <>
                            <Play size={14} />
                            Fit Model
                        </>
                    )}
                </button>


                {/* Error */}
                {fitError && (
                    <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-2">
                        {fitError}
                    </div>
                )}

                {/* Results */}
                {fitResult && (
                    <div className="bg-green-50 border border-green-200 rounded-md p-3 space-y-3">
                        <div className="flex items-center gap-2 text-green-700 font-medium text-sm">
                            <BarChart3 size={14} />
                            Model Fitted Successfully
                        </div>

                        {/* Metrics */}
                        <div>
                            <h4 className="text-xs font-medium text-gray-600 mb-1">Metrics</h4>
                            <div className="grid grid-cols-2 gap-1 text-xs">
                                {Object.entries(fitResult.metrics).map(([key, value]) => (
                                    <div key={key} className="flex justify-between bg-white rounded px-2 py-1">
                                        <span className="text-gray-500">{key}:</span>
                                        <span className="font-mono">
                                            {typeof value === 'number' ? value.toFixed(4) : value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Coefficients */}
                        {fitResult.coefficients && (
                            <div>
                                <h4 className="text-xs font-medium text-gray-600 mb-1">Coefficients</h4>
                                <div className="space-y-1 text-xs">
                                    {Object.entries(fitResult.coefficients).map(([key, value]) => (
                                        <div
                                            key={key}
                                            className="flex items-center gap-2 bg-white rounded px-2 py-1"
                                        >
                                            <span className="text-gray-500 truncate flex-1">{key}</span>
                                            <ArrowRight size={10} className="text-gray-300" />
                                            <span className="font-mono">
                                                {typeof value === 'number' ? value.toFixed(4) : value}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
