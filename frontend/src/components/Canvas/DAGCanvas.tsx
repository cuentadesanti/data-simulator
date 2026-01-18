import { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  ConnectionLineType,
} from '@xyflow/react';
import type {
  Connection,
  EdgeChange,
  NodeChange,
  Node,
  Edge,
  MiniMapNodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  useDAGStore,
  selectNodes,
  selectEdges,
  selectSelectedNodeId,
  selectEdgeStatuses,
} from '../../stores/dagStore';
import CustomNode from './CustomNode';
import type { FlowNodeData } from '../../types/dag';
import { useToast } from '../common';

// Custom MiniMap node component to render ellipses instead of rectangles
const MiniMapNode = ({
  x,
  y,
  width,
  height,
  color,
  strokeColor,
  strokeWidth,
}: MiniMapNodeProps) => {
  return (
    <ellipse
      cx={x + width / 2}
      cy={y + height / 2}
      rx={width / 2}
      ry={height / 2}
      fill={color}
      stroke={strokeColor}
      strokeWidth={strokeWidth}
    />
  );
};

const nodeTypes = {
  custom: CustomNode,
};

const DAGCanvas = () => {
  // Get store state and actions
  const storeNodes = useDAGStore(selectNodes);
  const storeEdges = useDAGStore(selectEdges);
  const selectedNodeId = useDAGStore(selectSelectedNodeId);
  const edgeStatuses = useDAGStore(selectEdgeStatuses);
  const selectNode = useDAGStore((state) => state.selectNode);
  const updateNodePosition = useDAGStore((state) => state.updateNodePosition);
  const addEdge = useDAGStore((state) => state.addEdge);
  const deleteEdgeAction = useDAGStore((state) => state.deleteEdge);
  const deleteNode = useDAGStore((state) => state.deleteNode);
  const addNodeAction = useDAGStore((state) => state.addNode);
  const { addToast } = useToast();

  // Convert store nodes to React Flow nodes with selection state
  const flowNodes = useMemo(() => {
    return storeNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isSelected: node.id === selectedNodeId,
      },
    }));
  }, [storeNodes, selectedNodeId]);

  // Build a map of edge status for quick lookup
  const edgeStatusMap = useMemo(() => {
    const map = new Map<string, 'used' | 'unused' | 'invalid'>();
    for (const status of edgeStatuses) {
      const edgeId = `${status.source}->${status.target}`;
      map.set(edgeId, status.status);
    }
    return map;
  }, [edgeStatuses]);

  // Convert store edges to React Flow edges with styling based on validation status
  const flowEdges = useMemo(() => {
    return storeEdges.map((edge) => {
      const status = edgeStatusMap.get(edge.id);

      // Default styling (before validation runs)
      let style = {
        strokeWidth: 2,
        stroke: '#64748b', // slate-500
      };
      let animated = false;
      let labelStyle = {};
      let label = '';

      if (status === 'used') {
        // Used edges: solid green
        style = {
          strokeWidth: 2,
          stroke: '#22c55e', // green-500
        };
      } else if (status === 'unused') {
        // Unused edges: dashed yellow/orange
        style = {
          strokeWidth: 2,
          stroke: '#f59e0b', // amber-500
          strokeDasharray: '5 5',
        } as typeof style;
      } else if (status === 'invalid') {
        // Invalid edges: solid red
        style = {
          strokeWidth: 3,
          stroke: '#ef4444', // red-500
        };
        animated = true;
      }

      return {
        ...edge,
        style,
        animated,
        label,
        labelStyle,
      };
    });
  }, [storeEdges, edgeStatusMap]);

  // Use React Flow hooks for local state management
  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges as Edge[]);

  // Sync store changes to local state
  useEffect(() => {
    setNodes(flowNodes as Node[]);
  }, [flowNodes, setNodes]);

  useEffect(() => {
    setEdges(flowEdges as Edge[]);
  }, [flowEdges, setEdges]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // Delete selected node
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
        e.preventDefault();
        const nodeName = storeNodes.find((n) => n.id === selectedNodeId)?.data.config.name;
        deleteNode(selectedNodeId);
        addToast('info', `Deleted node: ${nodeName}`);
      }

      // Duplicate selected node (Ctrl+D or Cmd+D)
      if ((e.ctrlKey || e.metaKey) && e.key === 'd' && selectedNodeId) {
        e.preventDefault();
        const currentNode = storeNodes.find((n) => n.id === selectedNodeId);
        if (currentNode) {
          addNodeAction(
            {
              ...currentNode.data.config,
              id: undefined,
              name: `${currentNode.data.config.name} (copy)`,
            },
            { x: currentNode.position.x + 50, y: currentNode.position.y + 50 }
          );
          addToast('success', `Duplicated: ${currentNode.data.config.name}`);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, storeNodes, deleteNode, addNodeAction, addToast]);

  // Handle node drag end - update position in store
  const handleNodesChange = useCallback(
    (changes: NodeChange<Node>[]) => {
      onNodesChange(changes);

      // Update positions in store when drag ends
      changes.forEach((change) => {
        if (change.type === 'position' && change.dragging === false && change.position) {
          updateNodePosition(change.id, change.position);
        }
      });
    },
    [onNodesChange, updateNodePosition]
  );

  // Handle edge changes (including deletions)
  const handleEdgesChange = useCallback(
    (changes: EdgeChange<Edge>[]) => {
      onEdgesChange(changes);

      // Handle edge deletions
      changes.forEach((change) => {
        if (change.type === 'remove') {
          deleteEdgeAction(change.id);
        }
      });
    },
    [onEdgesChange, deleteEdgeAction]
  );

  // Handle new edge connections
  const onConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        addEdge(connection.source, connection.target);
      }
    },
    [addEdge]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'default', // bezier curve
          animated: false,
          style: {
            strokeWidth: 2,
            stroke: '#64748b',
          },
        }}
        connectionLineStyle={{
          strokeWidth: 2,
          stroke: '#94a3b8',
        }}
        connectionLineType={ConnectionLineType.Bezier}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls className="!bg-white !border !border-gray-200 !rounded-lg !shadow-md" />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as unknown as FlowNodeData;
            return data?.config?.kind === 'stochastic' ? '#3b82f6' : '#22c55e';
          }}
          nodeStrokeWidth={2}
          nodeStrokeColor={(node) => {
            const data = node.data as unknown as FlowNodeData;
            return data?.config?.kind === 'stochastic' ? '#1d4ed8' : '#15803d';
          }}
          nodeComponent={MiniMapNode}
          zoomable
          pannable
          className="!bg-gray-50 !border !border-gray-200 !rounded-lg !shadow-md"
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        {/* Info Panel */}
        <Panel
          position="top-left"
          className="bg-white p-3 rounded-lg shadow-md border border-gray-200"
        >
          <div className="font-semibold text-gray-800">DAG Canvas</div>
          <div className="text-gray-500 text-xs mt-1">
            {nodes.length} nodes · {edges.length} edges
          </div>
          {/* Edge legend - only show after validation */}
          {edgeStatuses.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              <div className="text-xs text-gray-600 font-medium mb-1">Edge Status</div>
              <div className="space-y-0.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-0.5 bg-green-500 rounded"></div>
                  <span className="text-gray-500">Used</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-0.5 bg-amber-500 rounded"
                    style={{
                      backgroundImage:
                        'repeating-linear-gradient(90deg, #f59e0b 0, #f59e0b 2px, transparent 2px, transparent 4px)',
                    }}
                  ></div>
                  <span className="text-gray-500">Unused</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-0.5 bg-red-500 rounded"></div>
                  <span className="text-gray-500">Invalid</span>
                </div>
              </div>
            </div>
          )}
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default DAGCanvas;
