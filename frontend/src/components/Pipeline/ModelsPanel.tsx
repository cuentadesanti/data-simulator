/**
 * ModelsPanel component for training and viewing ML models.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
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
    TrendingUp,
    Shield,
    Scissors,
    GitMerge,
    GitBranch,
    Trees,
    Zap,
    Flame,
    Users,
    Box,
    Minus,
    Waves,
    Target as TargetIcon,
    Activity,
    Circle,
    Youtube,
    ExternalLink,
    HelpCircle,
    Save,
    FolderOpen,
    Trash2,
} from 'lucide-react';
import {
    modelingApi,
    ModelingAPIError,
    type FitResponse,
    type ModelParamValue,
    type ModelParameter,
    type ModelFitSummary,
    type ModelingError,
    type ModelParamChoiceValue,
} from '../../api/modelingApi';
import {
    usePipelineStore,
    selectPipelineSchema,
    selectCurrentVersionId,
} from '../../stores/pipelineStore';
import {
    useModelingStore,
    selectModelTypes,
    selectIsLoadingModelTypes,
    selectSelectedModel,
    selectModelName,
    selectModelParams,
    selectParamErrors,
    selectTestSize,
    selectTargetColumn,
    selectSelectedFeatures,
    selectShowAdvanced,
    selectShowInternal,
    selectSavedConfigs,
} from '../../stores/modelingStore';
import { Dropdown, type DropdownOption } from '../common';

// Helper to map icon names to Lucide components
const ModelIcon = ({
    name,
    size = 16,
    className = '',
}: {
    name?: string;
    size?: number;
    className?: string;
}) => {
    switch (name) {
        case 'trending-up':
            return <TrendingUp size={size} className={className} />;
        case 'shield':
            return <Shield size={size} className={className} />;
        case 'scissors':
            return <Scissors size={size} className={className} />;
        case 'git-merge':
            return <GitMerge size={size} className={className} />;
        case 'git-branch':
            return <GitBranch size={size} className={className} />;
        case 'trees':
            return <Trees size={size} className={className} />;
        case 'zap':
            return <Zap size={size} className={className} />;
        case 'flame':
            return <Flame size={size} className={className} />;
        case 'users':
            return <Users size={size} className={className} />;
        case 'box':
            return <Box size={size} className={className} />;
        case 'minus':
            return <Minus size={size} className={className} />;
        case 'wave':
            return <Waves size={size} className={className} />;
        case 'target':
            return <TargetIcon size={size} className={className} />;
        case 'activity':
            return <Activity size={size} className={className} />;
        case 'circle':
            return <Circle size={size} className={className} />;
        case 'brain':
            return <Brain size={size} className={className} />;
        default:
            return <Brain size={size} className={className} />;
    }
};

const firstSentence = (text: string): string => {
    const trimmed = text.trim();
    if (!trimmed) {
        return '';
    }
    const match = trimmed.match(/^.*?[.!?](?:\s|$)/);
    return match?.[0]?.trim() ?? trimmed;
};

const getComplexityDots = (complexity?: number): number => {
    if (!complexity || complexity <= 0) {
        return 0;
    }
    return Math.max(1, Math.min(5, Math.ceil(complexity / 20)));
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
    const matchedChoice = choices.find((candidate) => String(candidate) === choice);
    return matchedChoice ?? choice;
};

interface ModelsPanelProps {
    className?: string;
}

export const ModelsPanel = ({ className = '' }: ModelsPanelProps) => {
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

    // Fit results (transient state)
    const [isFitting, setIsFitting] = useState(false);
    const [fitResult, setFitResult] = useState<FitResponse | null>(null);
    const [fitErrors, setFitErrors] = useState<ModelingError[]>([]);
    const [fittedModels, setFittedModels] = useState<ModelFitSummary[]>([]);

    // Saved configuration controls (transient UI state)
    const [configName, setConfigName] = useState('');
    const [showSavedConfigs, setShowSavedConfigs] = useState(true);
    const fitHandlerRef = useRef<() => void>(() => {});

    useEffect(() => {
        fetchModelTypes();
    }, [fetchModelTypes]);

    // Refresh fitted models when needed
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

    // Get numeric columns for features/target
    const numericColumns = schema.filter(
        (col) => col.dtype === 'float' || col.dtype === 'int'
    );

    const currentModelType = modelTypes.find((model) => model.name === selectedModel);

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

        // Check if there are any parameter errors
        const hasErrors = Object.values(paramErrors).some((err) => !!err);
        if (hasErrors) {
            setFitErrors([
                {
                    code: 'VALIDATION_ERROR',
                    message: 'Please fix hyperparameter errors before fitting',
                    suggestion: 'Check the highlighted parameters above',
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
            refreshFits();
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
    fitHandlerRef.current = () => {
        void handleFit();
    };

    useEffect(() => {
        const handleWorkspaceFit = () => fitHandlerRef.current();
        window.addEventListener('workspace-fit-model', handleWorkspaceFit);
        return () => window.removeEventListener('workspace-fit-model', handleWorkspaceFit);
    }, []);

    const modelOptions = modelTypes.map(
        (model): DropdownOption<string> => ({
            value: model.name,
            label: `${model.display_name}${model.coming_soon ? ' (Coming Soon)' : ''}`,
            icon: <ModelIcon name={model.icon} size={14} />,
            disabled: model.coming_soon,
            description: firstSentence(model.description),
        })
    );

    const isFitDisabled =
        !currentVersionId ||
        isFitting ||
        !targetColumn ||
        selectedFeatures.length === 0 ||
        currentModelType?.coming_soon;

    return (
        <div className={`bg-white border-l border-gray-200 w-80 flex flex-col h-full ${className}`}>
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
                <Brain size={16} className="text-purple-500" />
                <h3 className="font-medium text-sm">Model Training</h3>
            </div>

            {/* Form */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Model name */}
                <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Model Name</label>
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
                    <label className="block text-xs font-medium text-gray-600 mb-1">Model Type</label>
                    <Dropdown
                        options={modelOptions}
                        value={selectedModel}
                        onChange={setSelectedModel}
                        disabled={isLoadingModelTypes || isFitting || modelOptions.length === 0}
                        icon={<ModelIcon name={currentModelType?.icon} size={14} />}
                        renderOption={(option, isSelected) => {
                            const model = modelTypes.find((item) => item.name === option.value);
                            const complexityDots = getComplexityDots(model?.complexity);
                            const topTags = model?.tags?.slice(0, 2) ?? [];
                            const videoCount = model?.video_links?.length ?? 0;

                            return (
                                <div
                                    className={`
                                        px-3 py-2 border-b border-gray-100 last:border-b-0
                                        ${isSelected ? 'bg-purple-50 text-purple-700' : 'text-gray-700'}
                                        ${option.disabled ? 'opacity-50' : 'hover:bg-gray-50'}
                                        transition-colors
                                    `}
                                >
                                    <div className="flex items-start gap-2">
                                        <span className="text-purple-600 mt-0.5">{option.icon}</span>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium truncate">{option.label}</div>
                                            {option.description && (
                                                <div className="text-[11px] text-gray-500 leading-tight mt-0.5">
                                                    {option.description}
                                                </div>
                                            )}
                                            <div className="flex flex-wrap gap-1 mt-1.5">
                                                {model?.category && (
                                                    <span className="text-[10px] uppercase tracking-wide bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                                        {model.category}
                                                    </span>
                                                )}
                                                {topTags.map((tag) => (
                                                    <span
                                                        key={tag}
                                                        className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end gap-1 pt-0.5">
                                            {complexityDots > 0 && (
                                                <div className="flex gap-0.5">
                                                    {[1, 2, 3, 4, 5].map((i) => (
                                                        <div
                                                            key={i}
                                                            className={`h-1.5 w-1.5 rounded-full ${i <= complexityDots ? 'bg-purple-400' : 'bg-gray-200'}`}
                                                        />
                                                    ))}
                                                </div>
                                            )}
                                            {videoCount > 0 && (
                                                <div className="flex items-center gap-1 text-[10px] text-red-500">
                                                    <Youtube size={10} />
                                                    {videoCount}
                                                </div>
                                            )}
                                        </div>
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
                    <div className="flex items-center gap-2 mt-1">
                        {currentModelType && (
                            <p className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium uppercase tracking-wider">
                                {currentModelType.task_type}
                            </p>
                        )}
                        {currentModelType?.complexity && (
                            <div className="flex items-center gap-1 text-[10px] text-gray-400">
                                <span>Complexity:</span>
                                <div className="flex gap-0.5">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <div
                                            key={i}
                                            className={`h-1 w-2 rounded-full ${
                                                i <= getComplexityDots(currentModelType?.complexity)
                                                    ? 'bg-purple-400'
                                                    : 'bg-gray-200'
                                            }`}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Video Links / Educational Resources */}
                {currentModelType?.video_links && currentModelType.video_links.length > 0 && (
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 space-y-2">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 uppercase tracking-wider">
                            <Youtube size={12} />
                            Learning Resources
                        </div>
                        <div className="space-y-1.5">
                            {currentModelType.video_links.map((link, idx) => (
                                <a
                                    key={idx}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center justify-between group p-1.5 bg-white border border-blue-200 rounded-md hover:border-blue-400 transition-colors"
                                >
                                    <span className="text-[11px] text-gray-700 truncate pr-2">
                                        {link.title}
                                    </span>
                                    <ExternalLink
                                        size={10}
                                        className="text-blue-400 group-hover:text-blue-600 flex-shrink-0"
                                    />
                                </a>
                            ))}
                        </div>
                        <p className="text-[10px] text-blue-500 italic flex items-center gap-1">
                            <HelpCircle size={10} />
                            Clearly explained by StatQuest
                        </p>
                    </div>
                )}

                {/* Model Parameters */}
                {currentModelType && currentModelType.parameters.length > 0 &&
                    (() => {
                        const coreParams = currentModelType.parameters.filter(
                            (param) => param.ui_group === 'core'
                        );
                        const advancedParams = currentModelType.parameters.filter(
                            (param) => param.ui_group === 'advanced' || !param.ui_group
                        );
                        const internalParams = currentModelType.parameters.filter(
                            (param) => param.ui_group === 'internal'
                        );

                        const renderParam = (param: ModelParameter) => {
                            const hasError = !!paramErrors[param.name];
                            const isChoice =
                                param.type === 'choice' &&
                                param.choices &&
                                param.choices.length > 0;
                            const isBoolean = param.type === 'boolean' || param.type === 'bool';
                            const textParamValue = modelParams[param.name];
                            const inputValue: string | number =
                                typeof textParamValue === 'string' ||
                                typeof textParamValue === 'number'
                                    ? textParamValue
                                    : '';

                            return (
                                <div key={param.name}>
                                    <div className="flex justify-between items-center mb-1">
                                        <label className="text-xs font-medium text-gray-700">
                                            {param.display_name}
                                        </label>
                                        <span
                                            className={`text-[10px] font-mono italic ${
                                                hasError ? 'text-red-500' : 'text-gray-400'
                                            }`}
                                        >
                                            {param.type}
                                        </span>
                                    </div>

                                    {isBoolean ? (
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={!!modelParams[param.name]}
                                                onChange={(e) =>
                                                    handleUpdateParam(
                                                        param.name,
                                                        e.target.checked,
                                                        param.type
                                                    )
                                                }
                                                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                                            />
                                            <span className="text-xs text-gray-500">Enabled</span>
                                        </label>
                                    ) : isChoice ? (
                                        <Dropdown
                                            options={(param.choices ?? []).map(
                                                (choice): DropdownOption<string> => ({
                                                    value:
                                                        choice === null
                                                            ? 'null'
                                                            : String(choice),
                                                    label:
                                                        choice === null
                                                            ? 'None'
                                                            : String(choice),
                                                })
                                            )}
                                            value={
                                                modelParams[param.name] === null
                                                    ? 'null'
                                                    : String(
                                                          modelParams[param.name] ?? param.default
                                                      )
                                            }
                                            onChange={(val) => {
                                                handleUpdateParam(
                                                    param.name,
                                                    getChoiceValue(val, param.choices),
                                                    param.type
                                                );
                                            }}
                                            size="sm"
                                            error={hasError}
                                        />
                                    ) : (
                                        <>
                                            <input
                                                type={
                                                    param.type === 'int' ||
                                                    param.type === 'integer' ||
                                                    param.type === 'float' ||
                                                    param.type === 'number'
                                                        ? 'number'
                                                        : 'text'
                                                }
                                                step={
                                                    param.type === 'float' ||
                                                    param.type === 'number'
                                                        ? '0.01'
                                                        : '1'
                                                }
                                                value={
                                                    inputValue
                                                }
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    const isNumeric =
                                                        param.type === 'int' ||
                                                        param.type === 'integer' ||
                                                        param.type === 'float' ||
                                                        param.type === 'number';
                                                    const parsed = isNumeric
                                                        ? param.type === 'int' ||
                                                          param.type === 'integer'
                                                            ? parseInt(val, 10)
                                                            : parseFloat(val)
                                                        : val;
                                                    const finalValue =
                                                        isNumeric && Number.isNaN(parsed)
                                                            ? val
                                                            : (parsed as ModelParamValue);
                                                    handleUpdateParam(
                                                        param.name,
                                                        finalValue,
                                                        param.type
                                                    );
                                                }}
                                                placeholder={String(param.default)}
                                                className={`w-full border rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 ${
                                                    hasError
                                                        ? 'border-red-300 bg-red-50 focus:ring-red-500'
                                                        : 'border-gray-300 focus:ring-purple-500'
                                                }`}
                                            />
                                            {hasError && (
                                                <p className="text-[10px] text-red-500 mt-1 flex items-center gap-1">
                                                    <AlertCircle size={10} />
                                                    {paramErrors[param.name]}
                                                </p>
                                            )}
                                        </>
                                    )}
                                    <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">
                                        {param.description}
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
                                    <div className="space-y-3">{coreParams.map(renderParam)}</div>
                                )}

                                {/* Advanced Parameters - Collapsible */}
                                {advancedParams.length > 0 && (
                                    <div className="border-t border-gray-200 pt-2 mt-2">
                                        <button
                                            type="button"
                                            onClick={() => setShowAdvanced(!showAdvanced)}
                                            className="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 w-full"
                                        >
                                            {showAdvanced ? (
                                                <ChevronDown size={12} />
                                            ) : (
                                                <ChevronRight size={12} />
                                            )}
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
                                            {showInternal ? (
                                                <ChevronDown size={12} />
                                            ) : (
                                                <ChevronRight size={12} />
                                            )}
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

                {/* Save configuration */}
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                        <Save size={12} />
                        Save Configuration
                    </div>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={configName}
                            onChange={(e) => setConfigName(e.target.value)}
                            placeholder="e.g. baseline_linear"
                            className="flex-1 border border-gray-300 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                        <button
                            type="button"
                            onClick={handleSaveConfig}
                            disabled={!configName.trim()}
                            className="px-2.5 py-1.5 text-xs font-medium rounded-md bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Save
                        </button>
                    </div>
                </div>

                {/* Saved configurations */}
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <button
                        type="button"
                        onClick={() => setShowSavedConfigs(!showSavedConfigs)}
                        className="flex items-center justify-between w-full text-left"
                    >
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            <FolderOpen size={12} />
                            Saved Configurations ({savedConfigs.length})
                        </div>
                        {showSavedConfigs ? (
                            <ChevronDown size={12} className="text-gray-400" />
                        ) : (
                            <ChevronRight size={12} className="text-gray-400" />
                        )}
                    </button>

                    {showSavedConfigs && (
                        <div className="mt-2 space-y-2">
                            {savedConfigs.length === 0 ? (
                                <p className="text-xs text-gray-400">No saved configurations yet.</p>
                            ) : (
                                savedConfigs.map((config) => (
                                    <div
                                        key={config.id}
                                        className="bg-white border border-gray-200 rounded-md p-2"
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="min-w-0">
                                                <div className="text-xs font-medium text-gray-700 truncate">
                                                    {config.name}
                                                </div>
                                                <div className="text-[10px] text-gray-400 mt-0.5">
                                                    {new Date(config.createdAt).toLocaleString()}
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
                                            {config.selectedModel} | {config.selectedFeatures.length}{' '}
                                            features
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>

                {/* Pipeline-dependent controls */}
                {currentVersionId && (
                    <>
                        {/* Target column */}
                        <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                                <Target size={12} />
                                Target Column
                            </label>
                            <Dropdown
                                options={[
                                    { value: '', label: 'Select target...' },
                                    ...numericColumns.map(
                                        (col): DropdownOption<string> => ({
                                            value: col.name,
                                            label: col.name,
                                        })
                                    ),
                                ]}
                                value={targetColumn}
                                onChange={setTargetColumn}
                                placeholder="Select target..."
                            />
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
                                                onChange={() => toggleFeature(col.name)}
                                                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                                            />
                                            <span className="text-sm">{col.name}</span>
                                            <span className="text-xs text-gray-400 ml-auto">
                                                {col.dtype}
                                            </span>
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
                    </>
                )}

                {!currentVersionId && (
                    <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700">
                        Create a pipeline first to select target/features and fit a model.
                    </div>
                )}

                {/* Fit button */}
                <button
                    onClick={handleFit}
                    disabled={isFitDisabled}
                    className="w-full flex items-center justify-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isFitting ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Fitting...
                        </>
                    ) : !currentVersionId ? (
                        <>Create a pipeline first</>
                    ) : currentModelType?.coming_soon ? (
                        <>Coming Soon</>
                    ) : (
                        <>
                            <Play size={14} />
                            Fit Model
                        </>
                    )}
                </button>

                {/* Errors */}
                {fitErrors.length > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3 space-y-2">
                        {fitErrors.map((error, idx) => (
                            <div key={idx} className="text-sm">
                                <div className="flex items-start gap-2">
                                    <AlertCircle
                                        size={14}
                                        className="text-red-500 mt-0.5 flex-shrink-0"
                                    />
                                    <div className="flex-1">
                                        <div className="text-red-700 font-medium">
                                            {error.message}
                                        </div>
                                        {error.suggestion && (
                                            <div className="text-red-600 text-xs mt-1">
                                                Tip: {error.suggestion}
                                            </div>
                                        )}
                                        {error.field && (
                                            <div className="text-red-500 text-xs mt-1 font-mono">
                                                Field: {error.field}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
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
                                    <div
                                        key={key}
                                        className="flex justify-between items-center bg-white rounded px-2 py-1"
                                    >
                                        <div className="flex items-center gap-1.5">
                                            <span className="text-gray-500">{key}:</span>
                                            {key.toLowerCase() === 'r2' && (
                                                <a
                                                    href="https://youtube.com/watch?v=2AQKmw14mHM"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    title="R-squared, Clearly Explained"
                                                    className="text-red-500 hover:text-red-600 transition-colors"
                                                >
                                                    <Youtube size={10} />
                                                </a>
                                            )}
                                        </div>
                                        <span className="font-mono text-gray-700">
                                            {typeof value === 'number'
                                                ? value.toFixed(4)
                                                : value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Coefficients */}
                        {fitResult.coefficients && (
                            <div>
                                <h4 className="text-xs font-medium text-gray-600 mb-1">
                                    Coefficients
                                </h4>
                                <div className="space-y-1 text-xs">
                                    {Object.entries(fitResult.coefficients).map(([key, value]) => (
                                        <div
                                            key={key}
                                            className="flex items-center gap-2 bg-white rounded px-2 py-1"
                                        >
                                            <span className="text-gray-500 truncate flex-1">
                                                {key}
                                            </span>
                                            <ArrowRight
                                                size={10}
                                                className="text-gray-300"
                                            />
                                            <span className="font-mono">
                                                {typeof value === 'number'
                                                    ? value.toFixed(4)
                                                    : value}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Fitted Models List */}
                {fittedModels.length > 0 && (
                    <div className="pt-4 border-t border-gray-100">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                            <BarChart3 size={12} />
                            Fitted Models ({fittedModels.length})
                        </div>
                        <div className="space-y-2">
                            {fittedModels.map((model) => (
                                <div
                                    key={model.id}
                                    className="p-2 border border-gray-200 rounded-md hover:border-purple-300 hover:bg-purple-50 transition-colors group"
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <div className="text-sm font-medium text-gray-800 truncate pr-2">
                                            {model.name}
                                        </div>
                                        <div className="text-[10px] text-gray-400 whitespace-nowrap">
                                            {new Date(model.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 text-[10px] text-gray-500">
                                        <span className="bg-gray-100 px-1 rounded">
                                            {model.model_type}
                                        </span>
                                        <span>•</span>
                                        <span>
                                            Target:{' '}
                                            <span className="text-gray-700">
                                                {model.target_column}
                                            </span>
                                        </span>
                                    </div>
                                    <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1">
                                        {Object.entries(model.metrics).map(([key, value]) => (
                                            <div
                                                key={key}
                                                className="flex justify-between items-center text-[10px]"
                                            >
                                                <div className="flex items-center gap-1">
                                                    <span className="text-gray-400 capitalize">
                                                        {key}:
                                                    </span>
                                                    {key.toLowerCase() === 'r2' && (
                                                        <a
                                                            href="https://youtube.com/watch?v=2AQKmw14mHM"
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            title="R-squared, Clearly Explained"
                                                            className="text-red-400 hover:text-red-600 transition-colors"
                                                        >
                                                            <Youtube size={8} />
                                                        </a>
                                                    )}
                                                </div>
                                                <span className="font-mono font-medium text-gray-600">
                                                    {value.toFixed(3)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
