import { useMemo, useState } from 'react';
import {
    Layers,
    ChevronLeft,
    ChevronRight,
    ArrowUp,
    ArrowDown,
    GripVertical,
    Trash2,
    AlertTriangle,
} from 'lucide-react';
import {
    usePipelineStore,
    selectCurrentVersionId,
    selectPipelineLineage,
    selectPipelineSteps,
    selectIsApplyingStep,
} from '../../stores/pipelineStore';

interface RecipePanelProps {
    collapsed?: boolean;
    onToggleCollapsed?: () => void;
    selectedStepId?: string | null;
    onSelectStep?: (stepId: string | null) => void;
    className?: string;
}

interface DependencyImpact {
    message: string;
    affectedStepIds: string[];
    affectedColumns: string[];
}

const getImpactFromError = (error: unknown): DependencyImpact | null => {
    const candidate = error as {
        response?: {
            status?: number;
            data?: {
                detail?: {
                    message?: string;
                    affected_step_ids?: string[];
                    affected_columns?: string[];
                } | string;
            };
        };
    };
    if (candidate?.response?.status !== 409) {
        return null;
    }
    const detail = candidate.response?.data?.detail;
    if (!detail || typeof detail === 'string') {
        return null;
    }
    return {
        message: detail.message ?? 'Operation would break dependent steps.',
        affectedStepIds: detail.affected_step_ids ?? [],
        affectedColumns: detail.affected_columns ?? [],
    };
};

const buildDependencyValidator = (
    orderedStepIds: string[],
    inputsByStepId: Map<string, string[]>,
    producersByColumn: Map<string, string[]>
): string | null => {
    const seen = new Set<string>();
    for (const stepId of orderedStepIds) {
        const inputs = inputsByStepId.get(stepId) ?? [];
        for (const input of inputs) {
            const producers = producersByColumn.get(input) ?? [];
            if (producers.length === 0) {
                continue;
            }
            const hasProducerBefore = producers.some((producerId) => seen.has(producerId));
            if (!hasProducerBefore) {
                return `Reorder blocked: step requires '${input}' before it can run.`;
            }
        }
        seen.add(stepId);
    }
    return null;
};

export const RecipePanel = ({
    collapsed = false,
    onToggleCollapsed = () => {},
    selectedStepId = null,
    onSelectStep = () => {},
    className = '',
}: RecipePanelProps) => {
    const currentVersionId = usePipelineStore(selectCurrentVersionId);
    const steps = usePipelineStore(selectPipelineSteps);
    const lineage = usePipelineStore(selectPipelineLineage);
    const isApplyingStep = usePipelineStore(selectIsApplyingStep);

    const deleteStep = usePipelineStore((state) => state.deleteStep);
    const reorderSteps = usePipelineStore((state) => state.reorderSteps);

    const [draggingStepId, setDraggingStepId] = useState<string | null>(null);
    const [dropTargetStepId, setDropTargetStepId] = useState<string | null>(null);
    const [interactionError, setInteractionError] = useState<string | null>(null);
    const [deleteTargetStepId, setDeleteTargetStepId] = useState<string | null>(null);
    const [deleteImpact, setDeleteImpact] = useState<DependencyImpact | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const inputsByStepId = useMemo(() => {
        const byStep = new Map<string, string[]>();
        lineage.forEach((entry) => byStep.set(entry.step_id, entry.inputs));
        return byStep;
    }, [lineage]);

    const producersByColumn = useMemo(() => {
        const byColumn = new Map<string, string[]>();
        steps.forEach((step) => {
            const existing = byColumn.get(step.output_column) ?? [];
            byColumn.set(step.output_column, [...existing, step.step_id]);
        });
        return byColumn;
    }, [steps]);

    const orderedStepIds = useMemo(() => steps.map((step) => step.step_id), [steps]);

    const runReorder = async (nextStepIds: string[]) => {
        setInteractionError(null);
        const dependencyError = buildDependencyValidator(
            nextStepIds,
            inputsByStepId,
            producersByColumn
        );
        if (dependencyError) {
            setInteractionError(dependencyError);
            return;
        }
        try {
            await reorderSteps(nextStepIds);
        } catch (error) {
            setInteractionError(
                error instanceof Error ? error.message : 'Failed to reorder recipe steps.'
            );
        }
    };

    const moveStep = async (stepId: string, direction: 'up' | 'down') => {
        const currentIndex = orderedStepIds.indexOf(stepId);
        if (currentIndex < 0) return;
        const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
        if (targetIndex < 0 || targetIndex >= orderedStepIds.length) return;

        const next = [...orderedStepIds];
        const [item] = next.splice(currentIndex, 1);
        next.splice(targetIndex, 0, item);
        await runReorder(next);
    };

    const handleDrop = async (fromStepId: string, toStepId: string) => {
        if (fromStepId === toStepId) return;
        const fromIndex = orderedStepIds.indexOf(fromStepId);
        const toIndex = orderedStepIds.indexOf(toStepId);
        if (fromIndex < 0 || toIndex < 0) return;

        const next = [...orderedStepIds];
        const [item] = next.splice(fromIndex, 1);
        next.splice(toIndex, 0, item);
        await runReorder(next);
    };

    const handleDelete = async (cascade: boolean) => {
        if (!deleteTargetStepId) return;
        setIsDeleting(true);
        setInteractionError(null);
        try {
            await deleteStep(deleteTargetStepId, cascade);
            setDeleteTargetStepId(null);
            setDeleteImpact(null);
        } catch (error) {
            const impact = getImpactFromError(error);
            if (impact && !cascade) {
                setDeleteImpact(impact);
            } else {
                setInteractionError(error instanceof Error ? error.message : 'Failed to delete step.');
            }
        } finally {
            setIsDeleting(false);
        }
    };

    if (!currentVersionId) {
        return null;
    }

    if (collapsed) {
        return (
            <div className={`w-14 bg-white border border-gray-200 rounded-xl flex flex-col ${className}`}>
                <button
                    type="button"
                    onClick={onToggleCollapsed}
                    className="h-12 flex items-center justify-center border-b border-gray-200 text-gray-500 hover:text-gray-700"
                    title="Expand recipe rail"
                >
                    <ChevronRight size={16} />
                </button>
                <div className="flex-1 flex items-center justify-center text-xs text-gray-400 [writing-mode:vertical-lr] rotate-180">
                    Recipe ({steps.length})
                </div>
            </div>
        );
    }

    return (
        <>
            <div data-tour="recipe-panel" className={`bg-white border border-gray-200 rounded-xl flex flex-col min-h-0 ${className}`}>
                <div className="px-3 py-2 border-b border-gray-200 flex items-center gap-2">
                    <Layers size={15} className="text-gray-500" />
                    <h3 className="text-sm font-semibold text-gray-700">Recipe</h3>
                    <span className="text-xs text-gray-400 ml-auto">{steps.length} steps</span>
                    <button
                        type="button"
                        onClick={onToggleCollapsed}
                        className="p-1 rounded hover:bg-gray-100 text-gray-500"
                        title="Collapse recipe rail"
                    >
                        <ChevronLeft size={14} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {steps.length === 0 ? (
                        <div className="rounded-lg border border-dashed border-gray-300 p-4 text-xs text-gray-500">
                            No transform steps yet. Use the formula bar to build your pipeline.
                        </div>
                    ) : (
                        steps.map((step, index) => {
                            const selected = selectedStepId === step.step_id;
                            const isDropTarget = dropTargetStepId === step.step_id;
                            return (
                                <div
                                    key={step.step_id}
                                    draggable={!isApplyingStep}
                                    onDragStart={() => {
                                        setDraggingStepId(step.step_id);
                                        setDropTargetStepId(step.step_id);
                                    }}
                                    onDragOver={(event) => {
                                        event.preventDefault();
                                        setDropTargetStepId(step.step_id);
                                    }}
                                    onDrop={async (event) => {
                                        event.preventDefault();
                                        if (!draggingStepId) return;
                                        await handleDrop(draggingStepId, step.step_id);
                                        setDraggingStepId(null);
                                        setDropTargetStepId(null);
                                    }}
                                    onDragEnd={() => {
                                        setDraggingStepId(null);
                                        setDropTargetStepId(null);
                                    }}
                                    className={`rounded-lg border p-2.5 transition-colors ${
                                        selected
                                            ? 'border-blue-300 bg-blue-50'
                                            : isDropTarget
                                              ? 'border-blue-200 bg-blue-50/60'
                                              : 'border-gray-200 bg-white hover:border-gray-300'
                                    }`}
                                >
                                    <div className="flex items-start gap-2">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                onSelectStep(selected ? null : step.step_id)
                                            }
                                            className="flex-1 text-left"
                                        >
                                            <div className="flex items-center gap-2">
                                                <span className="text-[11px] text-gray-400 w-5">
                                                    {index + 1}
                                                </span>
                                                <span className="text-xs font-medium text-gray-700 capitalize">
                                                    {step.type}
                                                </span>
                                            </div>
                                            <div className="text-xs mt-1 flex items-center gap-1.5 text-gray-500">
                                                <span className="font-mono text-blue-600">
                                                    {step.output_column}
                                                </span>
                                            </div>
                                        </button>

                                        <div className="flex items-center gap-0.5">
                                            <button
                                                type="button"
                                                onClick={() => moveStep(step.step_id, 'up')}
                                                disabled={isApplyingStep || index === 0}
                                                title="Move step up"
                                                className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-40"
                                            >
                                                <ArrowUp size={12} />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => moveStep(step.step_id, 'down')}
                                                disabled={isApplyingStep || index === steps.length - 1}
                                                title="Move step down"
                                                className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-40"
                                            >
                                                <ArrowDown size={12} />
                                            </button>
                                            <button
                                                type="button"
                                                disabled={isApplyingStep}
                                                title="Drag to reorder"
                                                className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-40 cursor-grab"
                                            >
                                                <GripVertical size={12} />
                                            </button>
                                            <button
                                                type="button"
                                                disabled={isApplyingStep}
                                                onClick={() => {
                                                    setDeleteTargetStepId(step.step_id);
                                                    setDeleteImpact(null);
                                                }}
                                                title="Delete step"
                                                className="p-1 rounded text-red-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-40"
                                            >
                                                <Trash2 size={12} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {interactionError && (
                    <div className="px-3 py-2 border-t border-red-100 bg-red-50 text-xs text-red-600">
                        {interactionError}
                    </div>
                )}
            </div>

            {deleteTargetStepId && (
                <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
                    <div className="w-full max-w-lg bg-white rounded-xl border border-gray-200 shadow-xl p-4 space-y-3">
                        <div className="flex items-center gap-2 text-gray-800">
                            <AlertTriangle size={16} className="text-amber-500" />
                            <h4 className="font-semibold text-sm">Delete Pipeline Step</h4>
                        </div>
                        {!deleteImpact ? (
                            <p className="text-sm text-gray-600">
                                Delete this step? If downstream steps depend on it, you will see a
                                cascade option.
                            </p>
                        ) : (
                            <div className="space-y-2">
                                <p className="text-sm text-amber-700">{deleteImpact.message}</p>
                                {deleteImpact.affectedColumns.length > 0 && (
                                    <div className="text-xs text-gray-600">
                                        Affected columns: {deleteImpact.affectedColumns.join(', ')}
                                    </div>
                                )}
                                {deleteImpact.affectedStepIds.length > 0 && (
                                    <div className="text-xs text-gray-600">
                                        Downstream steps: {deleteImpact.affectedStepIds.length}
                                    </div>
                                )}
                            </div>
                        )}
                        <div className="flex items-center justify-end gap-2 pt-1">
                            <button
                                type="button"
                                onClick={() => {
                                    setDeleteTargetStepId(null);
                                    setDeleteImpact(null);
                                }}
                                disabled={isDeleting}
                                className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={() => void handleDelete(false)}
                                disabled={isDeleting}
                                className="px-3 py-1.5 text-xs rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                Delete
                            </button>
                            {deleteImpact && (
                                <button
                                    type="button"
                                    onClick={() => void handleDelete(true)}
                                    disabled={isDeleting}
                                    className="px-3 py-1.5 text-xs rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
                                >
                                    Delete With Cascade
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
