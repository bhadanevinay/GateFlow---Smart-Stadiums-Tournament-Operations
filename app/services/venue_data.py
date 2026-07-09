"""Service for loading and caching venue/stadium layout data from JSON files.

Fixture JSONs are parsed once at process start and cached via lru_cache;
no request re-reads disk.
"""

from __future__ import annotations

__all__ = [
    "load_concourse_graph",
    "load_gates",
    "load_stadium_info",
    "load_transport_nodes",
]

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.exceptions import GateFlowError
from app.models.domain import GateInfo

if TYPE_CHECKING:
    from collections.abc import Mapping


def _get_data_dir() -> Path:
    """Resolve the data directory path.

    Returns:
        Path object pointing to the fixtures data directory.

    """
    return Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def load_stadium_info() -> dict[str, Any]:
    """Loads and caches stadium metadata from stadium.json.

    Returns:
        A dictionary containing stadium name, capacity, zones, and sections.

    Raises:
        GateFlowError: If the stadium.json file is missing or contains invalid JSON.

    """
    file_path = _get_data_dir() / "stadium.json"
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise GateFlowError(f"Failed to load stadium info from {file_path}") from e


@lru_cache(maxsize=1)
def load_gates() -> list[GateInfo]:
    """Loads and caches list of gates from gates.json.

    Returns:
        A list of GateInfo domain objects.

    Raises:
        GateFlowError: If gates.json is missing or contains invalid JSON.

    """
    file_path = _get_data_dir() / "gates.json"
    try:
        with file_path.open("r", encoding="utf-8") as f:
            raw_gates: list[dict[str, Any]] = json.load(f)
            return [
                GateInfo(
                    id=gate["id"],
                    name=gate["name"],
                    step_free=gate["step_free"],
                    sensory_friendly=gate["sensory_friendly"],
                    audio_cues=gate["audio_cues"],
                    base_capacity_per_min=gate["base_capacity_per_min"],
                )
                for gate in raw_gates
            ]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        raise GateFlowError(f"Failed to load gates list from {file_path}") from e


@lru_cache(maxsize=1)
def load_concourse_graph() -> dict[str, Any]:
    """Loads and caches node/edge concourse walking network from concourse_graph.json.

    Returns:
        A dictionary containing 'nodes' list and 'edges' list.

    Raises:
        GateFlowError: If concourse_graph.json is missing or contains invalid JSON.

    """
    file_path = _get_data_dir() / "concourse_graph.json"
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise GateFlowError(f"Failed to load concourse graph from {file_path}") from e


@lru_cache(maxsize=1)
def load_transport_nodes() -> Mapping[str, Mapping[str, Any]]:
    """Loads and caches simulated transport nodes information.

    Returns:
        Mapping of transport mode keys to node configurations.

    Raises:
        GateFlowError: If transport_nodes.json is missing or contains invalid JSON.

    """
    file_path = _get_data_dir() / "transport_nodes.json"
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise GateFlowError(f"Failed to load transport nodes from {file_path}") from e
