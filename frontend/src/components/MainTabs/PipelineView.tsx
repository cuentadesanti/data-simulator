/**
 * PipelineView component - the main view for the Pipeline Workbench.
 *
 * This component combines:
 * - FormulaBar: for adding transform steps
 * - Data table: showing preview/materialized data
 * - RecipePanel: showing the pipeline steps
 * - ModelsPanel: for training ML models
 */

import { useState, useEffect, useMemo } from 'react';
import {
    Table2,
    Brain,
    Loader2,
    RefreshCw,
    Sparkles,
} from 'lucide-react';
import { Dropdown, type DropdownOption } from '../common';
import { FormulaBar, RecipePanel, ModelsPanel } from '../Pipeline';
import { PreviewTable } from '../Preview/PreviewTable';
import {
    usePipelineStore,
    selectCurrentPipelineId,
    selectCurrentVersionId,
    selectPipelineSchema,
    selectPreviewRows,
    selectMaterializedRows,
    selectIsMaterializing,
    selectIsApplyingStep,
    selectPipelineSteps,
    selectLastWarnings,
} from '../../stores/pipelineStore';
import { useDAGStore, selectPreviewData } from '../../stores/dagStore';
import { useProjectStore, selectCurrentProjectId, selectCurrentVersionId as selectCurrentDAGVersionId } from '../../stores/projectStore';

type SubTabId = 'table' | 'models';

interface SubTab {
    id: SubTabId;
    label: string;
    icon: React.ReactNode;
    description: string;
}

const subTabs: SubTab[] = [
    {
        id: 'table',
        label: 'Data',
        icon: <Table2 size={14} />,
        description: 'View and transform your data',
    },
    {
        id: 'models',
        label: 'Models',
        icon: <Brain size={14} />,
        description: 'Train ML models on your data',
    },
];

export const PipelineView = () => {
    const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
    const currentVersionId = usePipelineStore(selectCurrentVersionId);
    const schema = usePipelineStore(selectPipelineSchema);
    const steps = usePipelineStore(selectPipelineSteps);
    const previewRows = usePipelineStore(selectPreviewRows);
    const materializedRows = usePipelineStore(selectMaterializedRows);
    const isMaterializing = usePipelineStore(selectIsMaterializing);
    const isApplyingStep = usePipelineStore(selectIsApplyingStep);
    const lastWarnings = usePipelineStore(selectLastWarnings);

    const createPipelineFromSimulation = usePipelineStore(
        (state) => state.createPipelineFromSimulation
    );
    const materialize = usePipelineStore((state) => state.materialize);
    const clearPipeline = usePipelineStore((state) => state.clearPipeline);
    const createProject = useProjectStore((state) => state.createProject);

    const dagPreviewData = useDAGStore(selectPreviewData);
    const dagVersionId = useProjectStore(selectCurrentDAGVersionId);
    const projectId = useProjectStore(selectCurrentProjectId);

    const [activeSubTab, setActiveSubTab] = useState<SubTabId>('table');
    const [showRecipePanel, setShowRecipePanel] = useState(true);
    const [isCreatingAnonymous, setIsCreatingAnonymous] = useState(false);
    const [anonymousCreateError, setAnonymousCreateError] = useState<string | null>(null);
    const [anonymousCreateAttempted, setAnonymousCreateAttempted] = useState(false);
    const [materializeLimit, setMaterializeLimit] = useState(1000);

    const [seed] = useState(42);
    const [sampleSize] = useState(1000);

    const hasDagPreview = dagPreviewData && dagPreviewData.length > 0;
    const hasPipeline = !!currentPipelineId;

    // Get display data - prefer materialized, fallback to preview
    const displayData = useMemo(() => {
        if (materializedRows.length > 0) return materializedRows;
        if (previewRows.length > 0) return previewRows;
        return [];
    }, [materializedRows, previewRows]);

    const displayColumns = useMemo(() => {
        return schema.map((s) => s.name);
    }, [schema]);

    // Columns added by transforms
    const derivedColumns = useMemo(() => {
        return steps.map((s) => s.output_column);
    }, [steps]);

    const handleCreateAnonymousPipeline = async () => {
        if (!hasDagPreview) return;

        setIsCreatingAnonymous(true);
        setAnonymousCreateError(null);
        try {
            let targetProjectId = projectId;
            let targetDagVersionId = dagVersionId;

            if (!targetProjectId || !targetDagVersionId) {
                const timestamp = new Date().toISOString().slice(0, 16).replace('T', ' ');
                const scratchProject = await createProject(`Untitled Project (${timestamp})`);
                targetProjectId = scratchProject.id;
                targetDagVersionId = scratchProject.current_version?.id || null;
            }

            if (!targetProjectId || !targetDagVersionId) {
                throw new Error('Unable to initialize anonymous project version');
            }

            await createPipelineFromSimulation(
                targetProjectId,
                'Untitled Pipeline',
                targetDagVersionId,
                seed,
                sampleSize
            );
        } catch (error) {
            console.error('Failed to create anonymous pipeline:', error);
            setAnonymousCreateError(
                error instanceof Error ? error.message : 'Failed to initialize anonymous pipeline'
            );
        } finally {
            setIsCreatingAnonymous(false);
        }
    };

    const handleMaterialize = async () => {
        if (!currentPipelineId || !currentVersionId) return;
        await materialize(materializeLimit);
    };

    // Start anonymous pipeline automatically when DAG preview exists.
    useEffect(() => {
        if (!hasDagPreview) {
            setAnonymousCreateAttempted(false);
            setAnonymousCreateError(null);
            return;
        }
        if (hasPipeline || isCreatingAnonymous || anonymousCreateAttempted) {
            return;
        }

        setAnonymousCreateAttempted(true);
        void handleCreateAnonymousPipeline();
    }, [
        hasDagPreview,
        hasPipeline,
        isCreatingAnonymous,
        anonymousCreateAttempted,
        handleCreateAnonymousPipeline,
    ]);

    // No DAG preview and no pipeline - show welcome screen
    if (!hasDagPreview && !hasPipeline) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50">
                <div className="text-center max-w-lg px-8">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                        <Sparkles className="w-10 h-10 text-white" />
                    </div>
                    <h2 className="text-2xl font-semibold text-gray-800 mb-3">
                        Pipeline Workbench
                    </h2>
                    <p className="text-gray-500 mb-6 leading-relaxed">
                        Create reproducible data transformations and train machine learning models.
                        Start by generating a DAG preview to use as your data source.
                    </p>
                    <div className="flex flex-col gap-3 text-sm text-gray-400">
                        <div className="flex items-center justify-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
                                1
                            </span>
                            <span>Create nodes in the DAG Canvas</span>
                        </div>
                        <div className="flex items-center justify-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
                                2
                            </span>
                            <span>Generate a preview in Data Preview tab</span>
                        </div>
                        <div className="flex items-center justify-center gap-2">
                            <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
                                3
                            </span>
                            <span>Create a pipeline here to transform & model</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Has DAG preview but no pipeline - bootstrap anonymous pipeline automatically.
    if (hasDagPreview && !hasPipeline) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-50 to-green-50">
                <div className="text-center max-w-md px-8">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
                        <Loader2 className="w-10 h-10 text-white animate-spin" />
                    </div>
                    <h2 className="text-2xl font-semibold text-gray-800 mb-3">
                        Preparing Anonymous Pipeline
                    </h2>
                    <p className="text-gray-500 leading-relaxed">
                        Creating a scratch pipeline so you can transform data and fit models immediately.
                    </p>
                    {anonymousCreateError && (
                        <p className="mt-4 text-sm text-red-600">
                            Failed to initialize pipeline: {anonymousCreateError}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    // Has pipeline - show full workbench
    return (
        <div className="w-full h-full flex flex-col bg-gray-50">
            {/* Formula Bar */}
            <div className="flex-shrink-0">
                <FormulaBar />
            </div>

            {/* Sub-tabs and controls */}
            <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4">
                <div className="flex items-center justify-between">
                    {/* Tabs */}
                    <div className="flex gap-1">
                        {subTabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveSubTab(tab.id)}
                                className={`
                                    flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                                    ${activeSubTab === tab.id
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }
                                `}
                            >
                                {tab.icon}
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Controls */}
                    {activeSubTab === 'table' && (
                        <div className="flex items-center gap-4 py-2">
                            {/* Warnings indicator */}
                            {lastWarnings > 0 && (
                                <div className="px-2 py-1 bg-yellow-50 text-yellow-700 text-xs rounded-md border border-yellow-200">
                                    {lastWarnings} warning{lastWarnings !== 1 ? 's' : ''}
                                </div>
                            )}

                            {/* Limit selector */}
                            <div className="flex items-center gap-2">
                                <label className="text-xs text-gray-500 font-medium">Rows:</label>
                                <Dropdown
                                    options={[
                                        { value: 100, label: '100' },
                                        { value: 500, label: '500' },
                                        { value: 1000, label: '1,000' },
                                        { value: 5000, label: '5,000' },
                                        { value: 10000, label: '10,000' },
                                    ] as DropdownOption<number>[]}
                                    value={materializeLimit}
                                    onChange={setMaterializeLimit}
                                    size="sm"
                                    className="w-24"
                                />
                            </div>

                            {/* Materialize button */}
                            <button
                                onClick={handleMaterialize}
                                disabled={isMaterializing || isApplyingStep}
                                className="flex items-center gap-1.5 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-4 py-1.5 rounded-lg text-xs font-medium hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow"
                            >
                                {isMaterializing ? (
                                    <>
                                        <Loader2 size={12} className="animate-spin" />
                                        Materializing...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw size={12} />
                                        Materialize
                                    </>
                                )}
                            </button>

                            {/* Recipe toggle */}
                            <button
                                onClick={() => setShowRecipePanel(!showRecipePanel)}
                                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${showRecipePanel
                                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                                    }`}
                            >
                                Recipe {steps.length > 0 && `(${steps.length})`}
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Content area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Main content */}
                <div className="flex-1 overflow-hidden">
                    {activeSubTab === 'table' && (
                        <div className="h-full">
                            {displayData.length > 0 ? (
                                <PreviewTable
                                    data={displayData as Record<string, unknown>[]}
                                    columns={displayColumns}
                                    highlightColumns={derivedColumns}
                                />
                            ) : (
                                <div className="h-full flex items-center justify-center">
                                    <div className="text-center px-8">
                                        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
                                            <Table2 className="w-8 h-8 text-gray-400" />
                                        </div>
                                        <h3 className="text-lg font-medium text-gray-700 mb-2">
                                            No Data Yet
                                        </h3>
                                        <p className="text-sm text-gray-400 max-w-sm">
                                            Click <strong>Materialize</strong> to generate your data,
                                            or add a transform step using the formula bar above.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    {activeSubTab === 'models' && (
                        <div className="h-full overflow-y-auto">
                            <ModelsPanel />
                        </div>
                    )}
                </div>

                {/* Recipe Panel (right sidebar) */}
                {showRecipePanel && activeSubTab === 'table' && <RecipePanel />}
            </div>

            {/* Pipeline info footer */}
            <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-2">
                <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-6 text-gray-500">
                        <span>
                            <span className="text-gray-400">Rows:</span>{' '}
                            <strong className="text-gray-700">{displayData.length.toLocaleString()}</strong>
                        </span>
                        <span>
                            <span className="text-gray-400">Columns:</span>{' '}
                            <strong className="text-gray-700">{displayColumns.length}</strong>
                        </span>
                        <span>
                            <span className="text-gray-400">Derived:</span>{' '}
                            <strong className="text-blue-600">{derivedColumns.length}</strong>
                        </span>
                        <span className="text-gray-300">|</span>
                        <span className="font-mono text-gray-400">
                            v{currentVersionId?.slice(0, 8)}
                        </span>
                    </div>
                    <button
                        onClick={clearPipeline}
                        className="text-gray-400 hover:text-red-500 transition-colors font-medium"
                    >
                        Close Pipeline
                    </button>
                </div>
            </div>
        </div>
    );
};
