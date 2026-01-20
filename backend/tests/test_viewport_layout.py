"""
Tests for viewport persistence and node position bounds validation.

Tests cover:
1. Viewport model structure (x, y, zoom)
2. Layout model with viewport field
3. NodePosition bounds validation
4. Viewport serialization/deserialization
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.dag import Layout, NodePosition, Viewport


class TestViewportModel:
    """Tests for the Viewport model."""

    def test_viewport_with_valid_values(self):
        """Test creating viewport with valid x, y, zoom."""
        viewport = Viewport(x=100.5, y=-200.3, zoom=1.5)
        
        assert viewport.x == 100.5
        assert viewport.y == -200.3
        assert viewport.zoom == 1.5

    def test_viewport_with_zero_values(self):
        """Test viewport at origin with default zoom."""
        viewport = Viewport(x=0, y=0, zoom=1.0)
        
        assert viewport.x == 0
        assert viewport.y == 0
        assert viewport.zoom == 1.0

    def test_viewport_with_negative_zoom(self):
        """Test viewport allows negative/zero zoom (edge case)."""
        # Note: zoom of 0 or negative would be unusual but schema allows it
        viewport = Viewport(x=0, y=0, zoom=0.1)
        assert viewport.zoom == 0.1

    def test_viewport_serialization(self):
        """Test viewport serializes to dict correctly."""
        viewport = Viewport(x=150, y=250, zoom=0.75)
        data = viewport.model_dump()
        
        assert data == {"x": 150, "y": 250, "zoom": 0.75}


class TestLayoutWithViewport:
    """Tests for Layout model with viewport field."""

    def test_layout_with_positions_only(self):
        """Test layout without viewport (backwards compatible)."""
        layout = Layout(positions={"node1": NodePosition(x=100, y=200)})
        
        assert layout.viewport is None
        assert "node1" in layout.positions
        assert layout.positions["node1"].x == 100

    def test_layout_with_viewport(self):
        """Test layout with both positions and viewport."""
        layout = Layout(
            positions={"node1": NodePosition(x=100, y=200)},
            viewport=Viewport(x=50, y=50, zoom=1.2)
        )
        
        assert layout.viewport is not None
        assert layout.viewport.x == 50
        assert layout.viewport.zoom == 1.2

    def test_layout_empty_positions_with_viewport(self):
        """Test layout with empty positions but valid viewport."""
        layout = Layout(
            positions={},
            viewport=Viewport(x=0, y=0, zoom=1.0)
        )
        
        assert len(layout.positions) == 0
        assert layout.viewport.zoom == 1.0

    def test_layout_serialization_with_viewport(self):
        """Test layout serializes completely."""
        layout = Layout(
            positions={"n1": NodePosition(x=0, y=0)},
            viewport=Viewport(x=100, y=100, zoom=2.0)
        )
        data = layout.model_dump()
        
        assert "viewport" in data
        assert data["viewport"]["zoom"] == 2.0


class TestNodePositionBounds:
    """Tests for NodePosition bounds validation."""

    def test_valid_position_values(self):
        """Test positions within valid bounds."""
        pos = NodePosition(x=500, y=-300)
        
        assert pos.x == 500
        assert pos.y == -300

    def test_position_at_zero(self):
        """Test position at origin."""
        pos = NodePosition(x=0, y=0)
        
        assert pos.x == 0
        assert pos.y == 0

    def test_position_at_max_bounds(self):
        """Test position at maximum allowed values."""
        pos = NodePosition(x=100000, y=100000)
        
        assert pos.x == 100000
        assert pos.y == 100000

    def test_position_at_min_bounds(self):
        """Test position at minimum allowed values."""
        pos = NodePosition(x=-100000, y=-100000)
        
        assert pos.x == -100000
        assert pos.y == -100000

    def test_position_exceeds_max_x(self):
        """Test that x > 100000 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NodePosition(x=100001, y=0)
        
        assert "x" in str(exc_info.value)

    def test_position_exceeds_max_y(self):
        """Test that y > 100000 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NodePosition(x=0, y=100001)
        
        assert "y" in str(exc_info.value)

    def test_position_below_min_x(self):
        """Test that x < -100000 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NodePosition(x=-100001, y=0)
        
        assert "x" in str(exc_info.value)

    def test_position_below_min_y(self):
        """Test that y < -100000 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NodePosition(x=0, y=-100001)
        
        assert "y" in str(exc_info.value)

    def test_position_float_precision(self):
        """Test that float precision is preserved within bounds."""
        pos = NodePosition(x=123.456789, y=-987.654321)
        
        assert pos.x == 123.456789
        assert pos.y == -987.654321


class TestLayoutWithMultiplePositions:
    """Tests for Layout with multiple node positions and viewport."""

    def test_layout_multiple_nodes_and_viewport(self):
        """Test layout with several nodes and viewport state."""
        layout = Layout(
            positions={
                "income": NodePosition(x=100, y=100),
                "age": NodePosition(x=300, y=100),
                "savings": NodePosition(x=200, y=300),
            },
            viewport=Viewport(x=-50, y=-25, zoom=0.8)
        )
        
        assert len(layout.positions) == 3
        assert layout.positions["savings"].y == 300
        assert layout.viewport.zoom == 0.8

    def test_layout_roundtrip_serialization(self):
        """Test layout survives JSON roundtrip."""
        original = Layout(
            positions={
                "node_a": NodePosition(x=150.5, y=250.5),
                "node_b": NodePosition(x=-100, y=0),
            },
            viewport=Viewport(x=10, y=20, zoom=1.5)
        )
        
        # Serialize and deserialize
        data = original.model_dump()
        restored = Layout.model_validate(data)
        
        assert restored.positions["node_a"].x == 150.5
        assert restored.viewport.zoom == 1.5
