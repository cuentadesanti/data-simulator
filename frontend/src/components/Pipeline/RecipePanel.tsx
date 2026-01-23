/**
 * RecipePanel component for displaying pipeline transform steps.
 */

import { Layers, ArrowRight, Trash2 } from 'lucide-react';
import {
    usePipelineStore,
    selectPipelineSteps,
    selectCurrentPipelineId,
} from '../../stores/pipelineStore';

export const RecipePanel = () => {
    const steps = usePipelineStore(selectPipelineSteps);
    const currentPipelineId = usePipelineStore(selectCurrentPipelineId);

    if (!currentPipelineId) {
        return null;
    }

    return (
        <div className="bg-white border-l border-gray-200 w-72 flex flex-col h-full">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
                <Layers size={16} className="text-gray-500" />
                <h3 className="font-medium text-sm">Recipe</h3>
                <span className="text-xs text-gray-400 ml-auto">
                    {steps.length} step{steps.length !== 1 ? 's' : ''}
                </span>
            </div>

            {/* Steps list */}
            <div className="flex-1 overflow-y-auto p-2">
                {steps.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 text-sm">
                        <p>No transform steps yet.</p>
                        <p className="mt-1 text-xs">
                            Use the formula bar above to add derived columns.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {steps.map((step, index) => (
                            <div
                                key={step.step_id}
                                className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm"
                            >
                                {/* Step header */}
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="flex items-center justify-center w-5 h-5 bg-blue-100 text-blue-600 text-xs font-medium rounded">
                                        {index + 1}
                                    </span>
                                    <span className="font-medium text-gray-700 capitalize">
                                        {step.type}
                                    </span>
                                    <button
                                        className="ml-auto text-gray-400 hover:text-red-500 transition-colors"
                                        title="Remove step (coming soon)"
                                        disabled
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                {/* Step content */}
                                <div className="flex items-center gap-2 text-xs font-mono">
                                    <span className="text-blue-600">{step.output_column}</span>
                                    <ArrowRight size={10} className="text-gray-400" />
                                    <span className="text-gray-500 truncate">
                                        {formatStepParams(step.type, step.params)}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer with source info */}
            <div className="px-4 py-2 border-t border-gray-200 text-xs text-gray-400">
                Pipeline ID: <span className="font-mono">{currentPipelineId.slice(0, 8)}...</span>
            </div>
        </div>
    );
};

/**
 * Format step parameters for display
 */
function formatStepParams(type: string, params: Record<string, unknown>): string {
    switch (type) {
        case 'formula':
            return String(params.expression || '');
        case 'log':
        case 'sqrt':
        case 'exp':
            return `${type}(${params.column})`;
        case 'bin':
            return `bin(${params.column}, ${params.bins || 5})`;
        default:
            return JSON.stringify(params);
    }
}
