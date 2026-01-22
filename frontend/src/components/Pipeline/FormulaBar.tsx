/**
 * FormulaBar component for adding transform steps to a pipeline.
 */

import { useState, useEffect } from 'react';
import { Plus, AlertCircle, ChevronDown, Loader2 } from 'lucide-react';
import {
    usePipelineStore,
    selectPipelineSchema,
    selectAvailableTransforms,
    selectIsApplyingStep,
    selectFormulaBarError,
    selectCurrentPipelineId,
} from '../../stores/pipelineStore';

export const FormulaBar = () => {
    const schema = usePipelineStore(selectPipelineSchema);
    const availableTransforms = usePipelineStore(selectAvailableTransforms);
    const isApplyingStep = usePipelineStore(selectIsApplyingStep);
    const formulaBarError = usePipelineStore(selectFormulaBarError);
    const currentPipelineId = usePipelineStore(selectCurrentPipelineId);

    const addStep = usePipelineStore((state) => state.addStep);
    const refreshTransformsCatalog = usePipelineStore((state) => state.refreshTransformsCatalog);
    const setFormulaBarError = usePipelineStore((state) => state.setFormulaBarError);

    const [selectedTransform, setSelectedTransform] = useState('formula');
    const [outputColumn, setOutputColumn] = useState('');
    const [expression, setExpression] = useState('');
    const [sourceColumn, setSourceColumn] = useState('');

    // Load transforms on mount
    useEffect(() => {
        if (availableTransforms.length === 0) {
            refreshTransformsCatalog();
        }
    }, [availableTransforms.length, refreshTransformsCatalog]);

    // Reset form when pipeline changes
    useEffect(() => {
        setOutputColumn('');
        setExpression('');
        setSourceColumn('');
        setFormulaBarError(null);
    }, [currentPipelineId, setFormulaBarError]);

    const currentTransform = availableTransforms.find((t) => t.name === selectedTransform);

    const handleApply = async () => {
        // Validate
        if (!outputColumn.trim()) {
            setFormulaBarError('Output column name is required');
            return;
        }

        // Build params based on transform type
        let params: Record<string, unknown> = {};

        if (selectedTransform === 'formula') {
            if (!expression.trim()) {
                setFormulaBarError('Expression is required');
                return;
            }
            params = { expression: expression.trim() };
        } else {
            // For column-based transforms (log, sqrt, exp, bin)
            if (!sourceColumn) {
                setFormulaBarError('Source column is required');
                return;
            }
            params = { column: sourceColumn };

            // Add bins for bin transform
            if (selectedTransform === 'bin') {
                params.bins = 5; // Default bins
            }
        }

        try {
            await addStep(selectedTransform, outputColumn.trim(), params);
            // Reset form on success
            setOutputColumn('');
            setExpression('');
            setSourceColumn('');
        } catch {
            // Error is handled in store
        }
    };

    if (!currentPipelineId) {
        return null;
    }

    return (
        <div className="bg-white border-b border-gray-200 px-4 py-3">
            <div className="flex items-center gap-3">
                {/* Transform type selector */}
                <div className="relative">
                    <select
                        value={selectedTransform}
                        onChange={(e) => {
                            setSelectedTransform(e.target.value);
                            setFormulaBarError(null);
                        }}
                        className="appearance-none bg-gray-50 border border-gray-300 rounded-md pl-3 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                        {availableTransforms.map((t) => (
                            <option key={t.name} value={t.name}>
                                {t.display_name}
                            </option>
                        ))}
                    </select>
                    <ChevronDown
                        size={14}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                    />
                </div>

                {/* Output column name */}
                <input
                    type="text"
                    value={outputColumn}
                    onChange={(e) => setOutputColumn(e.target.value)}
                    placeholder="Output column name"
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />

                <span className="text-gray-400">=</span>

                {/* Input field based on transform type */}
                {selectedTransform === 'formula' ? (
                    <input
                        type="text"
                        value={expression}
                        onChange={(e) => setExpression(e.target.value)}
                        placeholder="e.g., log(income) + age * 2"
                        className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !isApplyingStep) {
                                handleApply();
                            }
                        }}
                    />
                ) : (
                    <div className="relative">
                        <select
                            value={sourceColumn}
                            onChange={(e) => setSourceColumn(e.target.value)}
                            className="appearance-none bg-gray-50 border border-gray-300 rounded-md pl-3 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="">Select column...</option>
                            {schema
                                .filter((col) => col.dtype === 'float' || col.dtype === 'int')
                                .map((col) => (
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
                )}

                {/* Apply button */}
                <button
                    onClick={handleApply}
                    disabled={isApplyingStep}
                    className="flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isApplyingStep ? (
                        <>
                            <Loader2 size={14} className="animate-spin" />
                            Applying...
                        </>
                    ) : (
                        <>
                            <Plus size={14} />
                            Apply
                        </>
                    )}
                </button>
            </div>

            {/* Transform description */}
            {currentTransform?.description && (
                <p className="text-xs text-gray-500 mt-2">{currentTransform.description}</p>
            )}

            {/* Error message */}
            {formulaBarError && (
                <div className="flex items-center gap-2 mt-2 text-red-600 text-sm">
                    <AlertCircle size={14} />
                    {formulaBarError}
                </div>
            )}
        </div>
    );
};
