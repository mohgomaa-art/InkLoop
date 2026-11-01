"""Read-only measurements of actual panel-to-panel spacing in a saved layout."""
from itertools import combinations
from math import hypot
from typing import Any, Dict, List

from app.canvas.geometry_utils import polygons_intersect
from app.canvas.models import PanelSlot
from app.contracts.geometry import Point, Rect


def panel_outline(slot: PanelSlot) -> List[Point]:
    if slot.has_polygon:
        return list(slot.polygon or [])
    rect = slot.rect
    return [
        Point(x=rect.x, y=rect.y),
        Point(x=rect.right, y=rect.y),
        Point(x=rect.right, y=rect.bottom),
        Point(x=rect.x, y=rect.bottom),
    ]


def _point_segment_distance(point: Point, start: Point, end: Point) -> float:
    dx, dy = end.x - start.x, end.y - start.y
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return hypot(point.x - start.x, point.y - start.y)
    t = max(0.0, min(1.0, ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_sq))
    closest_x, closest_y = start.x + t * dx, start.y + t * dy
    return hypot(point.x - closest_x, point.y - closest_y)


def edge_gap(first: List[Point], second: List[Point]) -> float:
    if polygons_intersect(first, second):
        return 0.0
    return min(
        _point_segment_distance(point, start, end)
        for source, target in ((first, second), (second, first))
        for index, point in enumerate(source)
        for edge_index, start in enumerate(target)
        for end in (target[(edge_index + 1) % len(target)],)
    )


def inspect_panel_spacing(
    slots: List[PanelSlot],
    limit: int = 3,
    trim_box: Rect | None = None,
    configured_margins_px: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    outlines = {slot.panel_id: panel_outline(slot) for slot in slots}
    rows = []
    for slot in slots:
        neighbors = []
        for other in slots:
            if other.panel_id == slot.panel_id:
                continue
            gap = edge_gap(outlines[slot.panel_id], outlines[other.panel_id])
            neighbors.append({
                "panel_id": other.panel_id,
                "reading_order": other.reading_order,
                "minimum_edge_gap_px": round(gap, 2),
                "overlapping": gap == 0.0,
            })
        neighbors.sort(key=lambda item: (item["minimum_edge_gap_px"], item["reading_order"]))
        row = {"panel_id": slot.panel_id, "reading_order": slot.reading_order, "nearest_panels": neighbors[:limit]}
        if trim_box is not None:
            points = outlines[slot.panel_id]
            min_x, max_x = min(p.x for p in points), max(p.x for p in points)
            min_y, max_y = min(p.y for p in points), max(p.y for p in points)
            measured = {
                "top": round(min_y - trim_box.y, 2),
                "right": round(trim_box.right - max_x, 2),
                "bottom": round(trim_box.bottom - max_y, 2),
                "left": round(min_x - trim_box.x, 2),
            }
            required = dict(configured_margins_px or {})
            if slot.is_full_bleed:
                for edge in slot.bleed_edges:
                    required[edge] = 0.0
            row["measured_margins_px"] = measured
            row["required_margins_px"] = {edge: round(float(required.get(edge, 0.0)), 2) for edge in measured}
            row["margin_clearance_valid"] = all(
                measured[edge] + 0.5 >= float(required.get(edge, 0.0))
                for edge in measured
            )
        rows.append(row)
    all_gaps = [neighbor["minimum_edge_gap_px"] for row in rows for neighbor in row["nearest_panels"]]
    unique_pairs = set(combinations(sorted(outlines), 2))
    pair_gaps = [
        edge_gap(outlines[first], outlines[second])
        for first, second in unique_pairs
        if first in outlines and second in outlines
    ]
    return {
        "measurement": "minimum Euclidean distance between actual panel boundary segments; polygons are measured from their stored vertices",
        "panels": rows,
        "minimum_edge_gap_px": round(min(pair_gaps), 2) if pair_gaps else None,
        "overlapping_panel_pairs": [
            list(pair) for pair in unique_pairs
            if pair_gaps and edge_gap(outlines[pair[0]], outlines[pair[1]]) == 0.0
        ],
        "margin_clearance_valid": all(row.get("margin_clearance_valid", True) for row in rows),
    }
