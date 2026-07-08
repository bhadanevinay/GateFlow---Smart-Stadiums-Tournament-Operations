"""Routing service using Dijkstra's algorithm.

Finds the shortest path on the concourse graph, optionally enforcing step-free constraints
for users with mobility accessibility needs.
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Any, Final, cast

from app.exceptions import RouteNotFoundError, UnknownZoneError
from app.models.domain import RoutePlan
from app.models.enums import AccessibilityNeed

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# Walking speed constants
WALKING_SPEED_METERS_PER_MIN: Final[float] = 80.0  # ~1.33 m/s
ACCESSIBLE_WALKING_SPEED_METERS_PER_MIN: Final[float] = 50.0  # ~0.83 m/s


def _build_adjacency_list(
    nodes: Sequence[str],
    edges: Sequence[Mapping[str, str | float | bool]],
) -> dict[str, list[tuple[str, float, bool, str]]]:
    """Helper to construct adjacency list for Dijkstra."""
    adj: dict[str, list[tuple[str, float, bool, str]]] = {node: [] for node in nodes}
    for edge in edges:
        src = str(edge["source"])
        tgt = str(edge["target"])
        dist = float(edge["distance"])
        sf = bool(edge["step_free"])
        landmark = str(edge.get("landmark_description", ""))

        adj[src].append((tgt, dist, sf, landmark))
        adj[tgt].append((src, dist, sf, landmark))
    return adj


def _reconstruct_route_details(
    start_node: str,
    end_node: str,
    predecessors: Mapping[str, tuple[str, float, bool, str] | None],
    distances: Mapping[str, float],
    *,
    require_step_free: bool,
) -> RoutePlan:
    """Helper to reconstruct the final path, distance, speed and landmarks."""
    steps: list[str] = []
    landmarks: list[str] = []
    is_step_free = True

    curr = end_node
    while curr != start_node:
        steps.append(curr)
        pred = predecessors[curr]
        if pred is None:  # pragma: no cover
            break
        parent, _, sf, landmark = pred
        if not sf:
            is_step_free = False
        if landmark:
            landmarks.append(landmark)
        curr = parent

    steps.append(start_node)
    steps.reverse()
    landmarks.reverse()

    distance = float(distances[end_node])

    # Determine speed based on mobility needs
    speed = (
        ACCESSIBLE_WALKING_SPEED_METERS_PER_MIN
        if require_step_free
        else WALKING_SPEED_METERS_PER_MIN
    )
    estimated_minutes = distance / speed

    return RoutePlan(
        steps=steps,
        distance_meters=distance,
        estimated_minutes=estimated_minutes,
        landmarks=landmarks,
        step_free=is_step_free,
    )


def _dijkstra_search(
    adj: Mapping[str, Sequence[tuple[str, float, bool, str]]],
    start_node: str,
    end_node: str,
    distances: dict[str, float],
    predecessors: dict[str, tuple[str, float, bool, str] | None],
    *,
    require_step_free: bool,
) -> None:
    """Helper implementing Dijkstra priority queue loop."""
    queue: list[tuple[float, str]] = [(0.0, start_node)]

    while queue:
        curr_dist, curr_node = heapq.heappop(queue)

        if curr_node == end_node:
            break

        if curr_dist > distances[curr_node]:  # pragma: no cover
            continue

        for neighbor, dist, sf, landmark in adj[curr_node]:
            # Apply mobility filter
            if require_step_free and not sf:
                continue

            new_dist = curr_dist + dist
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                predecessors[neighbor] = (curr_node, dist, sf, landmark)
                heapq.heappush(queue, (new_dist, neighbor))


def calculate_route(
    start_node: str,
    end_node: str,
    graph: Mapping[str, Sequence[str] | Sequence[Mapping[str, str | float | bool]]],
    accessibility_needs: Sequence[AccessibilityNeed],
) -> RoutePlan:
    """Calculates the shortest route between two nodes on the concourse graph.

    Uses Dijkstra's algorithm. If AccessibilityNeed.MOBILITY is present in
    accessibility_needs, edges that are not step-free are excluded from traversal.

    Time Complexity: O((V + E) log V) via heapq.
    Space Complexity: O(V + E) for adjacency representation.

    Args:
        start_node: The starting node ID.
        end_node: The destination node ID.
        graph: The concourse graph dictionary containing 'nodes' and 'edges'.
        accessibility_needs: The user's accessibility needs.

    Returns:
        A RoutePlan object containing path steps, distance, duration, and landmarks.

    Raises:
        UnknownZoneError: If either start_node or end_node is not in the graph.
        RouteNotFoundError: If no path can be found satisfying the constraints.

    """
    nodes = cast("list[str]", list(graph.get("nodes", [])))
    edges = cast("list[dict[str, Any]]", list(graph.get("edges", [])))

    if start_node not in nodes:
        raise UnknownZoneError(f"Start node '{start_node}' is not in the venue graph.")
    if end_node not in nodes:
        raise UnknownZoneError(
            f"Destination node '{end_node}' is not in the venue graph."
        )

    adj = _build_adjacency_list(nodes, edges)

    # Determine constraints
    require_step_free = AccessibilityNeed.MOBILITY in accessibility_needs

    # Dijkstra setup
    distances = {node: float("inf") for node in nodes}
    distances[start_node] = 0.0
    predecessors: dict[str, tuple[str, float, bool, str] | None] = dict.fromkeys(nodes)

    _dijkstra_search(
        adj=adj,
        start_node=start_node,
        end_node=end_node,
        distances=distances,
        predecessors=predecessors,
        require_step_free=require_step_free,
    )

    # Check if reachable
    if distances[end_node] == float("inf"):
        raise RouteNotFoundError(
            f"No path found between '{start_node}' and '{end_node}'"
            f"{' (step-free only)' if require_step_free else ''}."
        )

    return _reconstruct_route_details(
        start_node=start_node,
        end_node=end_node,
        predecessors=predecessors,
        distances=distances,
        require_step_free=require_step_free,
    )
