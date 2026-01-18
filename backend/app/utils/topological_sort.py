"""Topological sort utility for DAG ordering.

This module provides a stable topological sort implementation that orders nodes
such that all parent nodes appear before their children. The sort is deterministic
and will detect cycles in the graph.
"""

from __future__ import annotations

from typing import Dict, List, Set

from app.core.exceptions import CycleDetectedError
from app.models.dag import DAGEdge, NodeConfig


def topological_sort(nodes: List[NodeConfig], edges: List[DAGEdge]) -> List[str]:
    """Perform topological sort on DAG nodes.

    Returns nodes in topological order where all parent nodes appear before
    their children. The sort is deterministic - nodes at the same level are
    sorted lexicographically by node ID, ensuring identical output regardless
    of input node order.

    Args:
        nodes: List of node configurations
        edges: List of directed edges (source -> target dependencies)

    Returns:
        List of node IDs in topological order

    Raises:
        CycleDetectedError: If a cycle is detected in the graph

    Example:
        >>> nodes = [
        ...     NodeConfig(id="a", name="A", kind="stochastic", distribution=...),
        ...     NodeConfig(id="b", name="B", kind="deterministic", formula="a * 2"),
        ...     NodeConfig(id="c", name="C", kind="deterministic", formula="b + 1"),
        ... ]
        >>> edges = [
        ...     DAGEdge(source="a", target="b"),
        ...     DAGEdge(source="b", target="c"),
        ... ]
        >>> topological_sort(nodes, edges)
        ['a', 'b', 'c']
    """
    # Build adjacency list and in-degree map
    node_ids = [node.id for node in nodes]
    adjacency: Dict[str, List[str]] = {node_id: [] for node_id in node_ids}
    in_degree: Dict[str, int] = {node_id: 0 for node_id in node_ids}

    # Build the graph
    for edge in edges:
        adjacency[edge.source].append(edge.target)
        in_degree[edge.target] += 1

    # Sort adjacency lists for deterministic iteration order
    for node_id in adjacency:
        adjacency[node_id].sort()

    # Initialize queue with nodes that have no incoming edges
    # Sort by node_id (lexicographically) for deterministic order regardless of input
    queue: List[str] = sorted([node_id for node_id in node_ids if in_degree[node_id] == 0])

    result: List[str] = []

    # Process nodes in topological order
    while queue:
        # Pop from front of queue (smallest node_id due to sorted insertion)
        current = queue.pop(0)
        result.append(current)

        # Collect children whose in-degree becomes 0
        ready_children: List[str] = []
        for child in adjacency[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                ready_children.append(child)

        # Add ready children to queue in sorted order (by node_id)
        ready_children.sort()
        queue.extend(ready_children)
        # Re-sort queue to maintain deterministic order
        queue.sort()

    # If we haven't processed all nodes, there must be a cycle
    if len(result) != len(node_ids):
        # Find the nodes involved in the cycle
        unprocessed = [node_id for node_id in node_ids if node_id not in result]
        cycle_nodes = _find_cycle(unprocessed, adjacency)
        raise CycleDetectedError(cycle_nodes)

    return result


def _find_cycle(nodes: List[str], adjacency: Dict[str, List[str]]) -> List[str]:
    """Find a cycle in the remaining unprocessed nodes.

    Uses DFS to detect and return the nodes involved in a cycle.

    Args:
        nodes: List of unprocessed node IDs (known to contain a cycle)
        adjacency: Adjacency list representation of the graph

    Returns:
        List of node IDs involved in the cycle
    """
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    parent: Dict[str, str | None] = {}

    def dfs(node: str) -> str | None:
        """DFS helper that returns the node where cycle was detected."""
        visited.add(node)
        rec_stack.add(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                parent[neighbor] = node
                cycle_node = dfs(neighbor)
                if cycle_node:
                    return cycle_node
            elif neighbor in rec_stack:
                # Found a cycle - return the node that created it
                parent[neighbor] = node
                return neighbor

        rec_stack.remove(node)
        return None

    # Start DFS from unprocessed nodes
    for start_node in nodes:
        if start_node not in visited:
            cycle_node = dfs(start_node)
            if cycle_node:
                # Reconstruct the cycle path
                cycle = [cycle_node]
                current = parent.get(cycle_node)
                while current and current != cycle_node:
                    cycle.append(current)
                    current = parent.get(current)
                return list(reversed(cycle))

    # This shouldn't happen if called correctly, but return something
    return nodes[:5]  # Return first few nodes as fallback
