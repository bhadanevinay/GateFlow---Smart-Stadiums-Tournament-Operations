"""Unit tests for the venue data loading service."""

from __future__ import annotations

import pathlib
from unittest.mock import patch

import pytest

from app.exceptions import GateFlowError
from app.services.venue_data import (
    load_concourse_graph,
    load_gates,
    load_stadium_info,
    load_transport_nodes,
)


def test_stadium_data_loads() -> None:
    """Verifies stadium metadata loads successfully."""
    stadium = load_stadium_info()
    assert "name" in stadium
    assert "total_capacity" in stadium
    assert "sections" in stadium


def test_gates_data_loads() -> None:
    """Verifies gates list loads and matches GateInfo objects."""
    gates = load_gates()
    assert len(gates) > 0
    assert gates[0].id is not None
    assert isinstance(gates[0].step_free, bool)


def test_concourse_graph_loads() -> None:
    """Verifies graph loads and contains nodes and edges."""
    graph = load_concourse_graph()
    assert "nodes" in graph
    assert "edges" in graph


def test_transport_nodes_loads() -> None:
    """Verifies transport nodes details load successfully."""
    nodes = load_transport_nodes()
    assert "metro" in nodes
    assert "shuttle" in nodes


def test_caching_behavior() -> None:
    """Verifies that subsequent loader calls return cached objects."""
    g1 = load_gates()
    g2 = load_gates()
    assert g1 is g2  # Cached singleton reference equality


def test_load_error_handling() -> None:
    """Tests loading failures wrap exceptions and throw GateFlowError."""
    # Temporarily override the data directory path to force FileNotFoundError
    with patch(
        "app.services.venue_data._get_data_dir",
        return_value=pathlib.Path("/nonexistent"),
    ):
        # Clear lru caches to force reload
        load_stadium_info.cache_clear()
        load_gates.cache_clear()
        load_concourse_graph.cache_clear()
        load_transport_nodes.cache_clear()

        with pytest.raises(GateFlowError):
            load_stadium_info()
        with pytest.raises(GateFlowError):
            load_gates()
        with pytest.raises(GateFlowError):
            load_concourse_graph()
        with pytest.raises(GateFlowError):
            load_transport_nodes()

    # Clear caches again after test to restore normal state for other tests
    load_stadium_info.cache_clear()
    load_gates.cache_clear()
    load_concourse_graph.cache_clear()
    load_transport_nodes.cache_clear()
