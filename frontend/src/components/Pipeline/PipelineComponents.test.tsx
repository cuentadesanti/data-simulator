/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FormulaBar } from './FormulaBar';
import { RecipePanel } from './RecipePanel';
import { ModelsPanel } from './ModelsPanel';
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
} from '../../stores/pipelineStore';
import { useProjectStore } from '../../stores/projectStore';
import type { TransformInfo, PipelineStep, SchemaColumn } from '../../api/pipelineApi';

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
}));

vi.mock('../../stores/projectStore', () => ({
    useProjectStore: vi.fn(),
}));

// Mock Lucide icons
vi.mock('lucide-react', () => ({
    Plus: () => <div data-testid="plus-icon" />,
    Trash2: () => <div data-testid="trash-icon" />,
    Play: () => <div data-testid="play-icon" />,
    Brain: () => <div data-testid="brain-icon" />,
    Info: () => <div data-testid="info-icon" />,
    AlertCircle: () => <div data-testid="alert-icon" />,
    Loader2: () => <div data-testid="loader-icon" />,
    ArrowRight: () => <div data-testid="arrow-right-icon" />,
    BarChart3: () => <div data-testid="bar-chart-icon" />,
    History: () => <div data-testid="history-icon" />,
    ChevronDown: () => <div data-testid="chevron-down-icon" />,
    ChevronUp: () => <div data-testid="chevron-up-icon" />,
    Search: () => <div data-testid="search-icon" />,
    Layers: () => <div data-testid="layers-icon" />,
    Target: () => <div data-testid="target-icon" />,
    Cpu: () => <div data-testid="cpu-icon" />,
    Settings: () => <div data-testid="settings-icon" />,
    Database: () => <div data-testid="database-icon" />,
    Table: () => <div data-testid="table-icon" />,
    FileText: () => <div data-testid="file-text-icon" />,
    Save: () => <div data-testid="save-icon" />,
    X: () => <div data-testid="x-icon" />,
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
                    currentVersionId: 'v1',
                    setFormulaBarError: vi.fn(),
                    addStep: vi.fn(),
                    materialize: vi.fn(),
                    refreshTransformsCatalog: vi.fn(),
                };
                return (selector as (state: typeof mockState) => unknown)(mockState);
            }
            return {
                setFormulaBarError: vi.fn(),
            };
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
        expect(screen.getByText('Model Training')).toBeDefined();
    });
});
