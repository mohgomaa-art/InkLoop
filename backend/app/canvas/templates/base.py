"""
InkLoop Canvas Generation Engine (E2) - Base Layout Template Contract.
Defines the abstract interface and common spatial calculation helpers for all layout templates.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import uuid

from app.contracts.geometry import Rect, Point, rect_intersects, rect_contains
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
    ReadingDirection,
    ValidationDiagnostic,
)
from app.canvas.errors import (
    OutOfBoundsLayoutError,
    UnintendedOverlapError,
    ImpossibleLayoutError,
)
from app.canvas.geometry_utils import (
    shoelace_area,
    polygon_is_self_intersecting,
    polygons_intersect,
    polygon_is_within_rect,
)

class BaseLayoutTemplate(ABC):
    """Abstract base class for all deterministic canvas layout generation templates."""

    template_id: LayoutTemplateId
    version: str = "1.0.0"
    description: str

    @abstractmethod
    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        **params: Any
    ) -> CanvasLayoutResult:
        """
        Executes deterministic layout generation for the given canvas and page specifications.
        Returns a complete, validated CanvasLayoutResult.
        """
        pass

    def compute_canonical_boxes(self, canvas_spec: CanvasSpec) -> Tuple[Rect, Rect, Rect, Rect]:
        """
        Computes the 4 fundamental boundary envelopes in PAGE coordinate space:
        1. trim_box: [0.0, 0.0, width, height)
        2. bleed_box: [-bleed.left, -bleed.top, width + bleed.left + bleed.right, height + bleed.top + bleed.bottom)
        3. safe_area_box: [safe.left, safe.top, width - safe.left - safe.right, height - safe.top - safe.bottom)
        4. usable_box: [margin.left, margin.top, width - margin.left - margin.right, height - margin.top - margin.bottom)
        """
        w = canvas_spec.width_px
        h = canvas_spec.height_px

        trim_box = Rect(x=0.0, y=0.0, width=w, height=h)

        b = canvas_spec.bleed
        bleed_box = Rect(
            x=-b.left,
            y=-b.top,
            width=w + b.left + b.right,
            height=h + b.top + b.bottom
        )

        s = canvas_spec.safe_area
        safe_area_box = Rect(
            x=s.left,
            y=s.top,
            width=w - s.left - s.right,
            height=h - s.top - s.bottom
        )

        m = canvas_spec.margins
        usable_box = Rect(
            x=m.left,
            y=m.top,
            width=w - m.left - m.right,
            height=h - m.top - m.bottom
        )

        return trim_box, bleed_box, safe_area_box, usable_box

    def validate_layout(self, result: CanvasLayoutResult, strict: bool = True) -> List[ValidationDiagnostic]:
        """
        Runs comprehensive geometric validation on all panel slots in the layout:
        1. Non-zero, strictly positive panel area.
        2. Panel boundary containment (within trim box or bleed box if is_full_bleed).
        3. Unintended overlap detection between panels.
        4. Polygon boundary, non-self-intersection, and positive area validation.
        """
        diagnostics: List[ValidationDiagnostic] = []
        panels = result.panel_slots
        trim = result.trim_box
        bleed = result.bleed_box

        # 1. Individual panel checks
        for p in panels:
            if p.rect.width <= 0 or p.rect.height <= 0:
                diag = ValidationDiagnostic(
                    severity="error",
                    code="ERR_2001_ZERO_OR_NEGATIVE_DIMENSION",
                    message=f"Panel '{p.panel_id}' has non-positive dimensions ({p.rect.width}x{p.rect.height} px)",
                    panel_id=p.panel_id,
                )
                diagnostics.append(diag)
                if strict:
                    raise OutOfBoundsLayoutError(diag.message)

            # Containment check: full bleed panels checked against bleed_box; standard against trim_box
            allowed_box = bleed if p.is_full_bleed else trim
            if not rect_contains(allowed_box, p.rect):
                diag = ValidationDiagnostic(
                    severity="error",
                    code="ERR_2003_OUT_OF_BOUNDS",
                    message=f"Panel '{p.panel_id}' [{p.rect.x}, {p.rect.y}, {p.rect.width}x{p.rect.height}] extends outside {'bleed' if p.is_full_bleed else 'trim'} bounds [{allowed_box.width}x{allowed_box.height}]",
                    panel_id=p.panel_id,
                    observed_bounds={"x": p.rect.x, "y": p.rect.y, "w": p.rect.width, "h": p.rect.height},
                    allowed_bounds={"x": allowed_box.x, "y": allowed_box.y, "w": allowed_box.width, "h": allowed_box.height},
                )
                diagnostics.append(diag)
                if strict:
                    raise OutOfBoundsLayoutError(diag.message, details={"panel": p.panel_id, "observed": p.rect.model_dump()})

            # Full bleed is edge-specific: extending beyond trim on an undeclared
            # edge is not authorized just because the point lies inside bleed_box.
            if p.has_polygon:
                panel_left = min(point.x for point in p.polygon)
                panel_top = min(point.y for point in p.polygon)
                panel_right = max(point.x for point in p.polygon)
                panel_bottom = max(point.y for point in p.polygon)
            else:
                panel_left = p.rect.x
                panel_top = p.rect.y
                panel_right = p.rect.x + p.rect.width
                panel_bottom = p.rect.y + p.rect.height
            outside_trim_edges = set()
            if panel_left < trim.x:
                outside_trim_edges.add("left")
            if panel_top < trim.y:
                outside_trim_edges.add("top")
            if panel_right > trim.x + trim.width:
                outside_trim_edges.add("right")
            if panel_bottom > trim.y + trim.height:
                outside_trim_edges.add("bottom")
            undeclared_bleed = outside_trim_edges - set(p.bleed_edges)
            if undeclared_bleed:
                diag = ValidationDiagnostic(
                    severity="error",
                    code="ERR_2005_UNDECLARED_BLEED_EDGE",
                    message=f"Panel '{p.panel_id}' extends beyond trim on undeclared edge(s): {sorted(undeclared_bleed)}",
                    panel_id=p.panel_id,
                )
                diagnostics.append(diag)
                if strict:
                    raise OutOfBoundsLayoutError(diag.message, details={"panel": p.panel_id, "undeclared_edges": sorted(undeclared_bleed)})

            # Polygon checks
            if p.has_polygon:
                pts = p.polygon
                poly_area = shoelace_area(pts)
                if poly_area <= 1.0:
                    diag = ValidationDiagnostic(
                        severity="error",
                        code="ERR_2001_ZERO_OR_NEGATIVE_DIMENSION",
                        message=f"Polygon for panel '{p.panel_id}' has near-zero or negative area ({poly_area})",
                        panel_id=p.panel_id,
                    )
                    diagnostics.append(diag)
                    if strict:
                        raise OutOfBoundsLayoutError(diag.message)

                if polygon_is_self_intersecting(pts):
                    diag = ValidationDiagnostic(
                        severity="error",
                        code="ERR_1001_INVALID_SCHEMA",
                        message=f"Polygon for panel '{p.panel_id}' has self-intersecting boundary edges",
                        panel_id=p.panel_id,
                    )
                    diagnostics.append(diag)
                    if strict:
                        raise OutOfBoundsLayoutError(diag.message)

                if not polygon_is_within_rect(pts, allowed_box):
                    diag = ValidationDiagnostic(
                        severity="error",
                        code="ERR_2003_OUT_OF_BOUNDS",
                        message=f"Polygon for panel '{p.panel_id}' has vertices outside permitted boundary",
                        panel_id=p.panel_id,
                    )
                    diagnostics.append(diag)
                    if strict:
                        raise OutOfBoundsLayoutError(diag.message)

        # Validate each overlap declaration by target ID, rationale, and z-order.
        # A legacy boolean can no longer grant a blanket exemption for every pair.
        by_id = {panel.panel_id: panel for panel in panels}
        allowed_overlap_pairs = set()
        for panel in panels:
            for target_id in panel.intentional_overlap_with:
                target = by_id.get(target_id)
                declaration_error = None
                if target is None:
                    declaration_error = f"Panel '{panel.panel_id}' declares overlap with unknown panel '{target_id}'."
                elif panel.z_index == target.z_index:
                    declaration_error = f"Intentional overlap between '{panel.panel_id}' and '{target_id}' requires distinct z_index values."
                elif not (panel.overlap_reason and panel.overlap_reason.strip()):
                    declaration_error = f"Intentional overlap between '{panel.panel_id}' and '{target_id}' requires an overlap_reason."
                if declaration_error:
                    diag = ValidationDiagnostic(
                        severity="error",
                        code="ERR_2006_INVALID_INTENTIONAL_OVERLAP_DECLARATION",
                        message=declaration_error,
                        panel_id=panel.panel_id,
                    )
                    diagnostics.append(diag)
                    if strict:
                        raise UnintendedOverlapError(declaration_error, details={"panel_id": panel.panel_id, "target_id": target_id})
                    continue
                allowed_overlap_pairs.add(tuple(sorted((panel.panel_id, target_id))))

        # 2. Pairwise unintended overlap checks using actual polygons when available.
        n = len(panels)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = panels[i]
                p2 = panels[j]
                pair = tuple(sorted((p1.panel_id, p2.panel_id)))
                p1_points = p1.polygon if p1.has_polygon else [
                    Point(x=p1.rect.x, y=p1.rect.y),
                    Point(x=p1.rect.x + p1.rect.width, y=p1.rect.y),
                    Point(x=p1.rect.x + p1.rect.width, y=p1.rect.y + p1.rect.height),
                    Point(x=p1.rect.x, y=p1.rect.y + p1.rect.height),
                ]
                p2_points = p2.polygon if p2.has_polygon else [
                    Point(x=p2.rect.x, y=p2.rect.y),
                    Point(x=p2.rect.x + p2.rect.width, y=p2.rect.y),
                    Point(x=p2.rect.x + p2.rect.width, y=p2.rect.y + p2.rect.height),
                    Point(x=p2.rect.x, y=p2.rect.y + p2.rect.height),
                ]
                intersects = (
                    polygons_intersect(p1_points, p2_points)
                    if p1.has_polygon or p2.has_polygon
                    else rect_intersects(p1.rect, p2.rect)
                )
                if not intersects or pair in allowed_overlap_pairs:
                    continue
                diag = ValidationDiagnostic(
                    severity="error",
                    code="ERR_2004_PANEL_UNINTENDED_OVERLAP",
                    message=(
                        f"Panels '{p1.panel_id}' and '{p2.panel_id}' overlap without a pair-specific "
                        "declaration, rationale, and distinct z_index."
                    ),
                    panel_id=p1.panel_id,
                    observed_bounds={"p1": p1.rect.model_dump(), "p2": p2.rect.model_dump()},
                )
                diagnostics.append(diag)
                if strict:
                    raise UnintendedOverlapError(diag.message, details={"p1": p1.panel_id, "p2": p2.panel_id})

        return diagnostics
