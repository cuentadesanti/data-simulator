import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type {
  NodeConfig,
  FlowNode,
  FlowEdge,
  DAGDefinition,
  GenerationMetadata,
  EdgeValidation,
  MissingEdge,
  ValidationError,
  Viewport,
} from '../types/dag';

type MainTabId = 'dag' | 'data';

interface DAGState {
  // Flow state
  nodes: FlowNode[];
  edges: FlowEdge[];
  viewport: Viewport | null;

  // Selection
  selectedNodeId: string | null;

  // Context (lookup tables, constants)
  context: Record<string, unknown>;

  // Generation metadata
  metadata: GenerationMetadata;

  // UI state
  isValidating: boolean;
  isGenerating: boolean;
  validationErrors: string[];
  structuredErrors: ValidationError[];
  activeMainTab: MainTabId;

  // Preview data
  previewData: Record<string, unknown>[] | null;
  previewColumns: string[] | null;

  // Edge validation status
  edgeStatuses: EdgeValidation[];
  missingEdges: MissingEdge[];

  // Validation state
  lastValidationResult: 'valid' | 'invalid' | 'pending' | null;

  // Viewport restoration flag
  shouldRestoreViewport: boolean;
}

interface DAGActions {
  // Node operations
  addNode: (config: Partial<NodeConfig>, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, config: Partial<NodeConfig>) => void;
  deleteNode: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;

  // Edge operations
  addEdge: (source: string, target: string) => void;
  deleteEdge: (edgeId: string) => void;

  // Viewport operations
  setViewport: (viewport: Viewport) => void;

  // Context operations
  setContext: (context: Record<string, unknown>) => void;
  updateContextEntry: (key: string, value: unknown) => void;
  deleteContextEntry: (key: string) => void;

  // Metadata operations
  setMetadata: (metadata: Partial<GenerationMetadata>) => void;

  // Validation & generation state
  setValidating: (isValidating: boolean) => void;
  setGenerating: (isGenerating: boolean) => void;
  setValidationErrors: (errors: string[]) => void;
  setStructuredErrors: (errors: ValidationError[]) => void;
  setPreviewData: (data: Record<string, unknown>[] | null, columns?: string[] | null) => void;
  setEdgeStatuses: (statuses: EdgeValidation[], missing: MissingEdge[]) => void;
  setLastValidationResult: (result: 'valid' | 'invalid' | 'pending' | null) => void;
  setActiveMainTab: (tab: MainTabId) => void;
  setViewportRestored: () => void;

  // Import/Export
  exportDAG: () => DAGDefinition;
  importDAG: (
    dag: DAGDefinition & {
      layout?: { positions: Record<string, { x: number; y: number }>; viewport?: Viewport };
    }
  ) => void;
  clearDAG: () => void;

  // Utility
  getSelectedNode: () => NodeConfig | null;
  getNodeById: (nodeId: string) => NodeConfig | null;
}

const generateId = () => `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

const initialState: DAGState = {
  nodes: [],
  edges: [],
  viewport: null,
  selectedNodeId: null,
  context: {},
  metadata: {
    sample_size: 1000,
    seed: undefined,
    preview_rows: 500,
  },
  isValidating: false,
  isGenerating: false,
  validationErrors: [],
  structuredErrors: [],
  activeMainTab: 'dag',
  previewData: null,
  previewColumns: null,
  edgeStatuses: [],
  missingEdges: [],
  lastValidationResult: null,
  shouldRestoreViewport: false,
};

export const useDAGStore = create<DAGState & DAGActions>()(
  immer((set, get) => ({
    ...initialState,

    addNode: (config, position) => {
      const id = config.id || generateId();
      const newNode: FlowNode = {
        id,
        type: 'custom',
        position,
        data: {
          config: {
            id,
            name: config.name || `Node ${get().nodes.length + 1}`,
            kind: config.kind || 'stochastic',
            dtype: config.dtype || 'float',
            scope: config.scope || 'row',
            distribution: config.distribution,
            formula: config.formula,
            group_by: config.group_by,
            post_processing: config.post_processing,
          },
        },
      };

      set((state) => {
        state.nodes.push(newNode);
        state.selectedNodeId = id;
        // Invalidate validation when DAG changes
        state.lastValidationResult = null;
        state.edgeStatuses = [];
        state.missingEdges = [];
      });
    },

    updateNode: (nodeId, config) => {
      set((state) => {
        const node = state.nodes.find((n) => n.id === nodeId);
        if (node) {
          // Apply config updates
          node.data.config = { ...node.data.config, ...config };

          // Invalidate validation when DAG changes
          state.lastValidationResult = null;
          state.edgeStatuses = [];
          state.missingEdges = [];
        }
      });
    },

    deleteNode: (nodeId) => {
      set((state) => {
        state.nodes = state.nodes.filter((n) => n.id !== nodeId);
        state.edges = state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
        if (state.selectedNodeId === nodeId) {
          state.selectedNodeId = null;
        }
        // Invalidate validation when DAG changes
        state.lastValidationResult = null;
        state.edgeStatuses = [];
        state.missingEdges = [];
      });
    },

    selectNode: (nodeId) => {
      set((state) => {
        state.selectedNodeId = nodeId;
      });
    },

    updateNodePosition: (nodeId, position) => {
      set((state) => {
        const node = state.nodes.find((n) => n.id === nodeId);
        if (node) {
          node.position = position;
        }
      });
    },

    addEdge: (source, target) => {
      const edgeId = `${source}->${target}`;
      set((state) => {
        // Prevent duplicate edges
        if (!state.edges.some((e) => e.id === edgeId)) {
          state.edges.push({
            id: edgeId,
            source,
            target,
            type: 'default', // bezier curve
          });
          // Invalidate validation when DAG changes
          state.lastValidationResult = null;
          state.edgeStatuses = [];
          state.missingEdges = [];
        }
      });
    },

    deleteEdge: (edgeId) => {
      set((state) => {
        state.edges = state.edges.filter((e) => e.id !== edgeId);
        // Invalidate validation when DAG changes
        state.lastValidationResult = null;
        state.edgeStatuses = [];
        state.missingEdges = [];
      });
    },

    setViewport: (viewport) => {
      set((state) => {
        state.viewport = viewport;
      });
    },

    setContext: (context) => {
      set((state) => {
        state.context = context;
      });
    },

    updateContextEntry: (key, value) => {
      set((state) => {
        state.context[key] = value;
      });
    },

    deleteContextEntry: (key) => {
      set((state) => {
        delete state.context[key];
      });
    },

    setMetadata: (metadata) => {
      set((state) => {
        state.metadata = { ...state.metadata, ...metadata };
      });
    },

    setValidating: (isValidating) => {
      set((state) => {
        state.isValidating = isValidating;
      });
    },

    setGenerating: (isGenerating) => {
      set((state) => {
        state.isGenerating = isGenerating;
      });
    },

    setValidationErrors: (errors) => {
      set((state) => {
        state.validationErrors = errors;
      });
    },

    setStructuredErrors: (errors) => {
      set((state) => {
        state.structuredErrors = errors;
      });
    },

    setPreviewData: (data, columns) => {
      set((state) => {
        state.previewData = data;
        state.previewColumns = columns ?? null;
      });
    },

    setEdgeStatuses: (statuses, missing) => {
      set((state) => {
        state.edgeStatuses = statuses;
        state.missingEdges = missing;
      });
    },

    setLastValidationResult: (result) => {
      set((state) => {
        state.lastValidationResult = result;
      });
    },

    setActiveMainTab: (tab) => {
      set((state) => {
        state.activeMainTab = tab;
      });
    },

    setViewportRestored: () => {
      set((state) => {
        state.shouldRestoreViewport = false;
      });
    },

    exportDAG: () => {
      const state = get();
      return {
        schema_version: '1.0',
        nodes: state.nodes.map((n) => n.data.config),
        edges: state.edges.map((e) => ({
          source: e.source,
          target: e.target,
        })),
        context: state.context,
        metadata: state.metadata,
        layout: {
          positions: Object.fromEntries(
            state.nodes.map((n) => [n.id, n.position])
          ),
          viewport: state.viewport || undefined,
        },
      };
    },

    importDAG: (dag) => {
      set((state) => {
        // Convert nodes to FlowNodes with positions
        state.nodes = dag.nodes.map((config, index) => {
          const position = dag.layout?.positions?.[config.id] || {
            x: 100 + (index % 4) * 250,
            y: 100 + Math.floor(index / 4) * 150,
          };
          return {
            id: config.id,
            type: 'custom' as const,
            position,
            data: { config },
          };
        });

        // Convert edges to FlowEdges
        state.edges = dag.edges.map((e) => ({
          id: `${e.source}->${e.target}`,
          source: e.source,
          target: e.target,
          type: 'default', // bezier curve
        }));

        state.context = dag.context || {};
        state.metadata = dag.metadata;
        state.selectedNodeId = null;
        state.validationErrors = [];
        state.structuredErrors = [];
        state.previewData = null;
        state.viewport = dag.layout?.viewport || null;
        state.shouldRestoreViewport = !!dag.layout?.viewport;
      });
    },

    clearDAG: () => {
      set(initialState);
    },

    getSelectedNode: () => {
      const state = get();
      if (!state.selectedNodeId) return null;
      const node = state.nodes.find((n) => n.id === state.selectedNodeId);
      return node?.data.config || null;
    },

    getNodeById: (nodeId) => {
      const node = get().nodes.find((n) => n.id === nodeId);
      return node?.data.config || null;
    },
  }))
);

// Selectors
export const selectNodes = (state: DAGState & DAGActions) => state.nodes;
export const selectEdges = (state: DAGState & DAGActions) => state.edges;
export const selectViewport = (state: DAGState & DAGActions) => state.viewport;
export const selectShouldRestoreViewport = (state: DAGState & DAGActions) =>
  state.shouldRestoreViewport;
export const selectSelectedNodeId = (state: DAGState & DAGActions) => state.selectedNodeId;
export const selectContext = (state: DAGState & DAGActions) => state.context;
export const selectMetadata = (state: DAGState & DAGActions) => state.metadata;
export const selectValidationErrors = (state: DAGState & DAGActions) => state.validationErrors;
export const selectStructuredErrors = (state: DAGState & DAGActions) => state.structuredErrors;
export const selectPreviewData = (state: DAGState & DAGActions) => state.previewData;
export const selectPreviewColumns = (state: DAGState & DAGActions) => state.previewColumns;
export const selectIsValidating = (state: DAGState & DAGActions) => state.isValidating;
export const selectIsGenerating = (state: DAGState & DAGActions) => state.isGenerating;
export const selectEdgeStatuses = (state: DAGState & DAGActions) => state.edgeStatuses;
export const selectMissingEdges = (state: DAGState & DAGActions) => state.missingEdges;
export const selectLastValidationResult = (state: DAGState & DAGActions) =>
  state.lastValidationResult;
export const selectActiveMainTab = (state: DAGState & DAGActions) => state.activeMainTab;
