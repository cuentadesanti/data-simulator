/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { FormulaBar } from './FormulaBar';
import { RecipePanel } from './RecipePanel';
import { ModelsPanel } from './ModelsPanel';
import { PipelineAnalysisTabs } from './PipelineAnalysisTabs';
import {
    usePipelineStore,
    selectPipelineSchema,
    selectPipelineSteps,
    selectAvailableTransforms,
    selectIsMaterializing,
    selectIsApplyingStep,
    selectFormulaBarError,
    selectCurrentPipelineId,
    selectCurrentVersionId,
    selectPipelineLineage,
} from '../../stores/pipelineStore';
import { useProjectStore } from '../../stores/projectStore';
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
import type { TransformInfo, PipelineStep, SchemaColumn } from '../../api/pipelineApi';
import type { ModelTypeInfo } from '../../api/modelingApi';

// Mock the stores
vi.mock('../../stores/pipelineStore', () => ({
    usePipelineStore: vi.fn(),
    selectPipelineSchema: vi.fn(),
    selectPipelineSteps: vi.fn(),
    selectAvailableTransforms: vi.fn(),
    selectIsMaterializing: vi.fn(),
    selectIsApplyingStep: vi.fn(),
    selectFormulaBarError: vi.fn(),
    selectCurrentPipelineId: vi.fn(),
    selectCurrentVersionId: vi.fn(),
    selectPipelineLineage: vi.fn(),
}));

vi.mock('../../stores/projectStore', () => ({
    useProjectStore: vi.fn(),
}));

vi.mock('../../stores/modelingStore', () => ({
    useModelingStore: vi.fn(),
    selectModelTypes: vi.fn(),
    selectIsLoadingModelTypes: vi.fn(),
    selectSelectedModel: vi.fn(),
    selectModelName: vi.fn(),
    selectModelParams: vi.fn(),
    selectParamErrors: vi.fn(),
    selectTestSize: vi.fn(),
    selectTargetColumn: vi.fn(),
    selectSelectedFeatures: vi.fn(),
    selectShowAdvanced: vi.fn(),
    selectShowInternal: vi.fn(),
    selectSavedConfigs: vi.fn(),
}));

describe('Pipeline Workbench Components Smoke Tests', () => {
    const mockSchema: SchemaColumn[] = [{ name: 'age', dtype: 'float' }];
    const mockTransforms: TransformInfo[] = [{ name: 'formula', display_name: 'Formula', description: 'Apply a formula', parameters: [] }];
    const mockSteps: PipelineStep[] = [{
        step_id: 's1',
        type: 'formula',
        output_column: 'age_sq',
        params: { expression: 'age^2' },
        order: 0,
        created_at: new Date().toISOString()
    }];
    const mockModelTypes: ModelTypeInfo[] = [
        {
            name: 'linear_regression',
            display_name: 'Linear Regression',
            description: 'Simple model.',
            task_type: 'regression',
            category: 'linear',
            parameters: [],
            video_links: [{ title: 'Intro to Linear Regression', url: 'https://example.com/video' }],
            tags: [],
            coming_soon: false,
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();

        // Default mock setup for selectors
        vi.mocked(selectPipelineSchema).mockReturnValue(mockSchema);
        vi.mocked(selectPipelineSteps).mockReturnValue([]);
        vi.mocked(selectAvailableTransforms).mockReturnValue(mockTransforms);
        vi.mocked(selectIsMaterializing).mockReturnValue(false);
        vi.mocked(selectIsApplyingStep).mockReturnValue(false);
        vi.mocked(selectFormulaBarError).mockReturnValue(null);
        vi.mocked(selectCurrentPipelineId).mockReturnValue('p1');
        vi.mocked(selectCurrentVersionId).mockReturnValue('v1');
        vi.mocked(selectPipelineLineage).mockReturnValue([]);

        // Default mock for usePipelineStore
        vi.mocked(usePipelineStore).mockImplementation((selector: unknown) => {
            if (typeof selector === 'function') {
                const mockState = {
                    availableTransforms: mockTransforms,
                    steps: [],
                    schema: mockSchema,
                    isApplyingStep: false,
                    formulaBarError: null,
                    currentPipelineId: 'p1',
                    currentVersionId: null,
                    lineage: [],
                    setFormulaBarError: vi.fn(),
                    addStep: vi.fn(),
                    materialize: vi.fn(),
                    refreshTransformsCatalog: vi.fn(),
                    deleteStep: vi.fn(),
                    reorderSteps: vi.fn(),
                };
                return (selector as (state: typeof mockState) => unknown)(mockState);
            }
            return {
                setFormulaBarError: vi.fn(),
            };
        });

        vi.mocked(selectModelTypes).mockReturnValue([]);
        vi.mocked(selectIsLoadingModelTypes).mockReturnValue(false);
        vi.mocked(selectSelectedModel).mockReturnValue('linear_regression');
        vi.mocked(selectModelName).mockReturnValue('');
        vi.mocked(selectModelParams).mockReturnValue({});
        vi.mocked(selectParamErrors).mockReturnValue({});
        vi.mocked(selectTestSize).mockReturnValue(0.2);
        vi.mocked(selectTargetColumn).mockReturnValue('');
        vi.mocked(selectSelectedFeatures).mockReturnValue([]);
        vi.mocked(selectShowAdvanced).mockReturnValue(false);
        vi.mocked(selectShowInternal).mockReturnValue(false);
        vi.mocked(selectSavedConfigs).mockReturnValue([]);

        vi.mocked(useModelingStore).mockImplementation((selector: unknown) => {
            if (typeof selector === 'function') {
                const mockState = {
                    modelTypes: [],
                    isLoadingModelTypes: false,
                    selectedModel: 'linear_regression',
                    modelName: '',
                    modelParams: {},
                    paramErrors: {},
                    testSize: 0.2,
                    targetColumn: '',
                    selectedFeatures: [],
                    showAdvanced: false,
                    showInternal: false,
                    savedConfigs: [],
                    fetchModelTypes: vi.fn(),
                    setSelectedModel: vi.fn(),
                    setModelName: vi.fn(),
                    setTestSize: vi.fn(),
                    setTargetColumn: vi.fn(),
                    toggleFeature: vi.fn(),
                    setShowAdvanced: vi.fn(),
                    setShowInternal: vi.fn(),
                    updateParam: vi.fn(),
                    saveCurrentConfig: vi.fn(),
                    loadConfig: vi.fn(),
                    deleteConfig: vi.fn(),
                };
                return (selector as (state: typeof mockState) => unknown)(mockState);
            }
            return undefined;
        });
    });

    it('renders FormulaBar without crashing', () => {
        render(<FormulaBar />);
        expect(screen.getByText(/Formula/)).toBeDefined();
    });

    it('renders RecipePanel without crashing', () => {
        vi.mocked(selectPipelineSteps).mockReturnValue(mockSteps);
        render(<RecipePanel />);
        expect(screen.getByText('Recipe')).toBeDefined();
    });

    it('renders ModelsPanel without crashing', () => {
        vi.mocked(useProjectStore).mockReturnValue({ currentVersionId: 'dv1' } as never);
        render(<ModelsPanel />);
        expect(screen.getByText('Model Configuration')).toBeDefined();
    });

    it('keeps learning materials collapsed by default', () => {
        vi.mocked(selectModelTypes).mockReturnValue(mockModelTypes);
        render(<ModelsPanel />);
        expect(screen.queryByText('Intro to Linear Regression')).toBeNull();
        fireEvent.click(screen.getAllByText('Learning Materials')[0]);
        expect(screen.getByText('Intro to Linear Regression')).toBeDefined();
    });

    it('renders PipelineAnalysisTabs diagnostics empty state', () => {
        render(
            <PipelineAnalysisTabs
                data={[{ age: 30, income: 100 }]}
                columns={['age', 'income']}
                derivedColumns={[]}
                steps={[]}
                lineage={[]}
                selectedStepId={null}
                onSelectStep={vi.fn()}
                diagnostics={null}
            />
        );
        fireEvent.click(screen.getByText('Diagnostics'));
        expect(screen.getByText(/Fit a model to unlock diagnostics/)).toBeDefined();
    });
});
