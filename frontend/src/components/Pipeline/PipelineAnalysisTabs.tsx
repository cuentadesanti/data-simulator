import { useEffect, useMemo, useState } from 'react';
import {
    Table2,
    BarChart3,
    ScatterChart,
    Activity,
    GitBranch,
    ArrowRight,
} from 'lucide-react';
import type { LineageEntry, PipelineStep } from '../../api/pipelineApi';
import { PreviewTable } from '../Preview/PreviewTable';
import { HistogramView } from '../MainTabs/HistogramView';
import { ScatterPlotView } from '../MainTabs/ScatterPlotView';
import type { PipelineDiagnosticsPayload } from './types';

type AnalysisTabId = 'table' | 'histograms' | 'scatter' | 'diagnostics' | 'lineage';

interface AnalysisTab {
    id: AnalysisTabId;
    label: string;
    icon: React.ReactNode;
}

const analysisTabs: AnalysisTab[] = [
    { id: 'table', label: 'Table', icon: <Table2 size={14} /> },
    { id: 'histograms', label: 'Histograms', icon: <BarChart3 size={14} /> },
    { id: 'scatter', label: 'Scatter', icon: <ScatterChart size={14} /> },
    { id: 'diagnostics', label: 'Diagnostics', icon: <Activity size={14} /> },
    { id: 'lineage', label: 'Lineage', icon: <GitBranch size={14} /> },
];

interface PipelineAnalysisTabsProps {
    data: Record<string, unknown>[];
    columns: string[];
    derivedColumns: string[];
    steps: PipelineStep[];
    lineage: LineageEntry[];
    selectedStepId: string | null;
    onSelectStep: (stepId: string | null) => void;
    diagnostics: PipelineDiagnosticsPayload | null;
}

function getNumericColumns(data: Record<string, unknown>[], columns: string[]): string[] {
    if (data.length === 0) {
        return [];
    }
    return columns.filter((column) => {
        const firstValue = data.find((row) => row[column] !== null && row[column] !== undefined)?.[
            column
        ];
        return typeof firstValue === 'number';
    });
}

export const PipelineAnalysisTabs = ({
    data,
    columns,
    derivedColumns,
    steps,
    lineage,
    selectedStepId,
    onSelectStep,
    diagnostics,
}: PipelineAnalysisTabsProps) => {
    const numericColumns = useMemo(() => getNumericColumns(data, columns), [data, columns]);
    const [activeTab, setActiveTab] = useState<AnalysisTabId>(
        numericColumns.length > 0 ? 'histograms' : 'table'
    );

    useEffect(() => {
        if (diagnostics) {
            // eslint-disable-next-line react-hooks/set-state-in-effect -- auto-switch to diagnostics tab when results arrive
            setActiveTab('diagnostics');
        }
    }, [diagnostics]);

    const lineageEntryByStep = useMemo(
        () => new Map(lineage.map((entry) => [entry.step_id, entry])),
        [lineage]
    );
    const selectedLineage = selectedStepId ? lineageEntryByStep.get(selectedStepId) : null;

    const highlightedColumns = useMemo(() => {
        const highlights = new Set<string>(derivedColumns);
        if (selectedLineage) {
            highlights.add(selectedLineage.output_col);
            selectedLineage.inputs.forEach((col) => highlights.add(col));
        }
        return Array.from(highlights);
    }, [derivedColumns, selectedLineage]);

    const diagnosticsResidualRows = useMemo(() => {
        if (!diagnostics || diagnostics.predictionRows.length === 0) {
            return [];
        }
        const target = diagnostics.targetColumn;
        return diagnostics.predictionRows
            .map((row): Record<string, unknown> | null => {
                const actual = row[target];
                const predicted = row._prediction;
                if (typeof actual !== 'number' || typeof predicted !== 'number') {
                    return null;
                }
                return {
                    ...row,
                    _residual: actual - predicted,
                    _abs_error: Math.abs(actual - predicted),
                };
            })
            .filter((row): row is Record<string, unknown> => row !== null);
    }, [diagnostics]);

    return (
        <div data-tour="analysis-tabs" className="h-full flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="border-b border-gray-200 px-4">
                <div className="flex items-center gap-1 overflow-x-auto">
                    {analysisTabs.map((tab) => {
                        const disabled =
                            (tab.id === 'histograms' || tab.id === 'scatter') &&
                            numericColumns.length === 0;
                        return (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => !disabled && setActiveTab(tab.id)}
                                disabled={disabled}
                                className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                                    activeTab === tab.id
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                            >
                                {tab.icon}
                                {tab.label}
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="flex-1 min-h-0">
                {activeTab === 'table' && (
                    <div className="h-full overflow-auto">
                        <PreviewTable data={data} columns={columns} highlightColumns={highlightedColumns} />
                    </div>
                )}

                {activeTab === 'histograms' && (
                    <div className="h-full">
                        {numericColumns.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-sm text-gray-500">
                                Numeric columns are required for histograms.
                            </div>
                        ) : (
                            <HistogramView data={data} columns={numericColumns} allColumns={columns} />
                        )}
                    </div>
                )}

                {activeTab === 'scatter' && (
                    <div className="h-full">
                        {numericColumns.length < 2 ? (
                            <div className="h-full flex items-center justify-center text-sm text-gray-500">
                                At least 2 numeric columns are required for scatter plots.
                            </div>
                        ) : (
                            <ScatterPlotView data={data} columns={numericColumns} allColumns={columns} />
                        )}
                    </div>
                )}

                {activeTab === 'diagnostics' && (
                    <div className="h-full overflow-auto p-4 space-y-4">
                        {!diagnostics ? (
                            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-sm text-gray-500">
                                Fit a model to unlock diagnostics. Metrics, prediction scatter, residuals,
                                and coefficients will appear here.
                            </div>
                        ) : (
                            <>
                                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                                    <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                                        Active Model
                                    </div>
                                    <div className="text-sm font-medium text-gray-800">
                                        {diagnostics.modelName}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                        {diagnostics.modelType} | target: {diagnostics.targetColumn}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
                                    {Object.entries(diagnostics.metrics).map(([metric, value]) => (
                                        <div
                                            key={metric}
                                            className="rounded-lg border border-gray-200 bg-white px-3 py-2"
                                        >
                                            <div className="text-[11px] text-gray-500 uppercase tracking-wide">
                                                {metric}
                                            </div>
                                            <div className="font-mono text-sm text-gray-800 mt-1">
                                                {value.toFixed(4)}
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {diagnostics.predictionRows.length > 0 && (
                                    <div className="space-y-3">
                                        <h4 className="text-sm font-semibold text-gray-700">
                                            Actual vs Predicted
                                        </h4>
                                        <ScatterPlotView
                                            data={diagnostics.predictionRows}
                                            columns={[diagnostics.targetColumn, '_prediction']}
                                            allColumns={Object.keys(diagnostics.predictionRows[0] ?? {})}
                                        />
                                    </div>
                                )}

                                {diagnosticsResidualRows.length > 0 && (
                                    <div className="space-y-3">
                                        <h4 className="text-sm font-semibold text-gray-700">
                                            Residual Distribution
                                        </h4>
                                        <HistogramView
                                            data={diagnosticsResidualRows}
                                            columns={['_residual']}
                                            allColumns={['_residual']}
                                        />
                                    </div>
                                )}

                                {diagnostics.coefficients && (
                                    <div className="rounded-lg border border-gray-200 bg-white p-3">
                                        <h4 className="text-sm font-semibold text-gray-700 mb-2">
                                            Coefficients
                                        </h4>
                                        <div className="space-y-1">
                                            {Object.entries(diagnostics.coefficients).map(
                                                ([feature, value]) => (
                                                    <div
                                                        key={feature}
                                                        className="text-xs flex items-center justify-between gap-2"
                                                    >
                                                        <span className="text-gray-600 truncate">
                                                            {feature}
                                                        </span>
                                                        <span className="font-mono text-gray-800">
                                                            {typeof value === 'number'
                                                                ? value.toFixed(4)
                                                                : String(value)}
                                                        </span>
                                                    </div>
                                                )
                                            )}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {activeTab === 'lineage' && (
                    <div className="h-full overflow-auto p-4 space-y-2">
                        {steps.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-sm text-gray-500">
                                Add transform steps to view lineage.
                            </div>
                        ) : (
                            steps.map((step) => {
                                const entry = lineageEntryByStep.get(step.step_id);
                                const selected = step.step_id === selectedStepId;
                                return (
                                    <button
                                        key={step.step_id}
                                        type="button"
                                        onClick={() => onSelectStep(selected ? null : step.step_id)}
                                        className={`w-full text-left rounded-lg border px-3 py-2 transition-colors ${
                                            selected
                                                ? 'border-blue-300 bg-blue-50'
                                                : 'border-gray-200 bg-white hover:border-blue-200'
                                        }`}
                                    >
                                        <div className="text-sm font-medium text-gray-800">
                                            {step.output_column}
                                        </div>
                                        <div className="text-[11px] text-gray-500 mt-1 flex items-center gap-1">
                                            {(entry?.inputs ?? []).length > 0 ? (
                                                <>
                                                    {(entry?.inputs ?? []).slice(0, 3).join(', ')}
                                                    {(entry?.inputs ?? []).length > 3 && '...'}
                                                    <ArrowRight size={10} className="text-gray-400" />
                                                </>
                                            ) : (
                                                <>No explicit input columns</>
                                            )}
                                            <span className="text-gray-700">{step.output_column}</span>
                                        </div>
                                    </button>
                                );
                            })
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
