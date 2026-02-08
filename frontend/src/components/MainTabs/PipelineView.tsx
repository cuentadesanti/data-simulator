/**
 * PipelineView component - Split Studio for transforms, modeling, and analysis.
 */

import { useEffect, useMemo, useState } from 'react';
import { Loader2, RefreshCw, Sparkles, Rows3, PanelRightOpen } from 'lucide-react';
import { Dropdown, type DropdownOption } from '../common';
import {
    FormulaBar,
    ModelsPanel,
    PipelineAnalysisTabs,
    RecipePanel,
    type PipelineDiagnosticsPayload,
} from '../Pipeline';
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
    selectPipelineLineage,
} from '../../stores/pipelineStore';
import { useDAGStore, selectPreviewData } from '../../stores/dagStore';
import {
    useProjectStore,
    selectCurrentProjectId,
    selectCurrentVersionId as selectCurrentDAGVersionId,
} from '../../stores/projectStore';

export const PipelineView = () => {
    const currentPipelineId = usePipelineStore(selectCurrentPipelineId);
    const currentVersionId = usePipelineStore(selectCurrentVersionId);
    const schema = usePipelineStore(selectPipelineSchema);
    const steps = usePipelineStore(selectPipelineSteps);
    const lineage = usePipelineStore(selectPipelineLineage);
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

    const [isCreatingAnonymous, setIsCreatingAnonymous] = useState(false);
    const [anonymousCreateError, setAnonymousCreateError] = useState<string | null>(null);
    const [anonymousCreateAttempted, setAnonymousCreateAttempted] = useState(false);
    const [materializeLimit, setMaterializeLimit] = useState(1000);
    const [recipeCollapsed, setRecipeCollapsed] = useState(false);
    const [showRecipeOverlay, setShowRecipeOverlay] = useState(false);
    const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
    const [diagnostics, setDiagnostics] = useState<PipelineDiagnosticsPayload | null>(null);

    const [seed] = useState(42);
    const [sampleSize] = useState(1000);

    const hasDagPreview = dagPreviewData && dagPreviewData.length > 0;
    const hasPipeline = !!currentPipelineId;

    const displayData = useMemo(() => {
        if (materializedRows.length > 0) return materializedRows;
        if (previewRows.length > 0) return previewRows;
        return [];
    }, [materializedRows, previewRows]);

    const displayColumns = useMemo(() => schema.map((s) => s.name), [schema]);
    const derivedColumns = useMemo(() => steps.map((s) => s.output_column), [steps]);

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
                        Build reproducible transformations and train models with integrated analysis.
                        Start by generating a DAG preview.
                    </p>
                </div>
            </div>
        );
    }

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

    return (
        <div className="w-full h-full flex flex-col bg-gray-50 min-h-0">
            <div className="flex-shrink-0">
                <FormulaBar />
            </div>

            <div className="flex-shrink-0 bg-white border-b border-gray-200 px-3 md:px-4">
                <div className="flex items-center justify-between gap-3 py-2.5">
                    <div className="flex items-center gap-2 md:gap-3 flex-wrap">
                        <button
                            type="button"
                            onClick={() => setShowRecipeOverlay(true)}
                            className="xl:hidden inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-gray-200 text-xs text-gray-600 hover:bg-gray-50"
                        >
                            <PanelRightOpen size={12} />
                            Recipe
                        </button>
                        <button
                            type="button"
                            onClick={() => setRecipeCollapsed((prev) => !prev)}
                            className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-gray-200 text-xs text-gray-600 hover:bg-gray-50"
                        >
                            <Rows3 size={12} />
                            {recipeCollapsed ? 'Show Recipe' : 'Hide Recipe'}
                        </button>
                        {lastWarnings > 0 && (
                            <div className="px-2 py-1 bg-yellow-50 text-yellow-700 text-xs rounded-md border border-yellow-200">
                                {lastWarnings} warning{lastWarnings !== 1 ? 's' : ''}
                            </div>
                        )}
                    </div>

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
                        <button
                            onClick={handleMaterialize}
                            disabled={isMaterializing || isApplyingStep}
                            className="flex items-center gap-1.5 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-green-600 hover:to-emerald-700 disabled:opacity-50"
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
                    </div>
                </div>
            </div>

            <div className="flex-1 min-h-0 relative p-3 md:p-4">
                <div className="hidden xl:grid h-full min-h-0 gap-4 grid-cols-[minmax(56px,280px)_minmax(340px,420px)_minmax(0,1fr)]">
                    <RecipePanel
                        collapsed={recipeCollapsed}
                        onToggleCollapsed={() => setRecipeCollapsed((prev) => !prev)}
                        selectedStepId={selectedStepId}
                        onSelectStep={setSelectedStepId}
                    />
                    <ModelsPanel onDiagnosticsChange={setDiagnostics} />
                    <PipelineAnalysisTabs
                        data={displayData as Record<string, unknown>[]}
                        columns={displayColumns}
                        derivedColumns={derivedColumns}
                        steps={steps}
                        lineage={lineage}
                        selectedStepId={selectedStepId}
                        onSelectStep={setSelectedStepId}
                        diagnostics={diagnostics}
                    />
                </div>

                <div className="hidden md:grid xl:hidden h-full min-h-0 gap-4 grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
                    <ModelsPanel onDiagnosticsChange={setDiagnostics} />
                    <PipelineAnalysisTabs
                        data={displayData as Record<string, unknown>[]}
                        columns={displayColumns}
                        derivedColumns={derivedColumns}
                        steps={steps}
                        lineage={lineage}
                        selectedStepId={selectedStepId}
                        onSelectStep={setSelectedStepId}
                        diagnostics={diagnostics}
                    />
                </div>

                <div className="md:hidden h-full min-h-0 flex flex-col gap-3">
                    <div className="h-[45%] min-h-[240px]">
                        <ModelsPanel onDiagnosticsChange={setDiagnostics} />
                    </div>
                    <div className="flex-1 min-h-0">
                        <PipelineAnalysisTabs
                            data={displayData as Record<string, unknown>[]}
                            columns={displayColumns}
                            derivedColumns={derivedColumns}
                            steps={steps}
                            lineage={lineage}
                            selectedStepId={selectedStepId}
                            onSelectStep={setSelectedStepId}
                            diagnostics={diagnostics}
                        />
                    </div>
                </div>

                {showRecipeOverlay && (
                    <div className="xl:hidden absolute inset-0 z-40 bg-black/30">
                        <div className="absolute right-3 top-3 bottom-3 w-[320px] max-w-[85vw]">
                            <RecipePanel
                                collapsed={false}
                                onToggleCollapsed={() => setShowRecipeOverlay(false)}
                                selectedStepId={selectedStepId}
                                onSelectStep={setSelectedStepId}
                                className="h-full"
                            />
                        </div>
                        <button
                            type="button"
                            onClick={() => setShowRecipeOverlay(false)}
                            className="absolute inset-0 -z-10"
                            aria-label="Close recipe overlay"
                        />
                    </div>
                )}
            </div>

            <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-2">
                <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-5 text-gray-500 flex-wrap">
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
                        <span className="font-mono text-gray-400">v{currentVersionId?.slice(0, 8)}</span>
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
