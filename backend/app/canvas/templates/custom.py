"""Creator-specified custom panel geometry for scratch-built Canvas pages."""
from typing import Any, Dict, List, Optional

from app.contracts.geometry import Point, Rect
from app.contracts.identity import IdPrefix, generate_id
from app.canvas.models import (
    CanvasLayoutResult,
    CanvasSpec,
    LayoutTemplateId,
    PageSpec,
    PanelSlot,
    ReadingDirection,
)
from app.canvas.templates.base import BaseLayoutTemplate

_NORMALIZED_BOUNDARY_EPSILON = 1e-9


class CustomLayoutTemplate(BaseLayoutTemplate):
    template_id = LayoutTemplateId.CUSTOM
    version = "1.0.0"
    description = "Scratch-built editable page using creator-specified rectangle or polygon panels."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        panel_geometry: Optional[List[Dict[str, Any]]] = None,
        **params: Any,
    ) -> CanvasLayoutResult:
        del params
        trim, bleed, safe_area, usable = self.compute_canonical_boxes(canvas_spec)
        definitions = panel_geometry or [{"panel_id": "panel_01", "reading_order": 1, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}}]
        if not definitions:
            raise ValueError("A custom page needs at least one panel.")
        ids = [str(item.get("panel_id", "")).strip() for item in definitions]
        orders = [item.get("reading_order") for item in definitions]
        if any(not item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("Custom panel IDs must be non-empty and unique.")
        if any(not isinstance(order, int) or order < 1 for order in orders) or len(orders) != len(set(orders)):
            raise ValueError("Custom panel reading_order values must be unique positive integers.")

        panels: List[PanelSlot] = []
        for definition in definitions:
            rect_data = definition.get("rect")
            polygon_data = definition.get("polygon")
            if rect_data is None and not polygon_data:
                raise ValueError(f"Panel '{definition['panel_id']}' needs a normalized rect or polygon.")
            points = None
            if polygon_data:
                if any(not (0.0 <= float(point["x"]) <= 1.0 and 0.0 <= float(point["y"]) <= 1.0) for point in polygon_data):
                    raise ValueError(f"Panel '{definition['panel_id']}' polygon points must stay inside normalized usable-page coordinates [0, 1].")
                points = [
                    Point(x=usable.x + float(point["x"]) * usable.width, y=usable.y + float(point["y"]) * usable.height)
                    for point in polygon_data
                ]
            if rect_data is not None:
                rect_x = float(rect_data["x"])
                rect_y = float(rect_data["y"])
                rect_width = float(rect_data["width"])
                rect_height = float(rect_data["height"])
                if not all(0.0 <= value <= 1.0 for value in (rect_x, rect_y, rect_width, rect_height)):
                    raise ValueError(f"Panel '{definition['panel_id']}' rectangle values must stay inside normalized usable-page coordinates [0, 1].")
                if (
                    rect_width <= 0
                    or rect_height <= 0
                    or rect_x + rect_width > 1.0 + _NORMALIZED_BOUNDARY_EPSILON
                    or rect_y + rect_height > 1.0 + _NORMALIZED_BOUNDARY_EPSILON
                ):
                    raise ValueError(f"Panel '{definition['panel_id']}' rectangle must have positive size and fit inside the usable page area.")
                # Clamp only floating-point spill at the normalized edge; real
                # out-of-bounds geometry remains an error.
                rect_width = min(rect_width, 1.0 - rect_x)
                rect_height = min(rect_height, 1.0 - rect_y)
                if rect_width <= 0 or rect_height <= 0:
                    raise ValueError(f"Panel '{definition['panel_id']}' rectangle must have positive size and fit inside the usable page area.")
                x = usable.x + rect_x * usable.width
                y = usable.y + rect_y * usable.height
                width = rect_width * usable.width
                height = rect_height * usable.height
                rect = Rect(x=x, y=y, width=width, height=height)
            elif points:
                left = min(point.x for point in points)
                top = min(point.y for point in points)
                right = max(point.x for point in points)
                bottom = max(point.y for point in points)
                rect = Rect(x=left, y=top, width=right - left, height=bottom - top)
            else:
                raise ValueError(f"Panel '{definition['panel_id']}' geometry is empty.")
            if rect_data is not None and points:
                p_left = min(point.x for point in points)
                p_top = min(point.y for point in points)
                p_right = max(point.x for point in points)
                p_bottom = max(point.y for point in points)
                tolerance = 1.0
                if any(abs(a - b) > tolerance for a, b in ((rect.x, p_left), (rect.y, p_top), (rect.right, p_right), (rect.bottom, p_bottom))):
                    raise ValueError(f"Panel '{definition['panel_id']}' rect bounds must match its polygon bounds.")
            panels.append(PanelSlot(
                panel_id=definition["panel_id"],
                reading_order=definition["reading_order"],
                rect=rect,
                polygon=points,
                z_index=int(definition.get("z_index", definition["reading_order"])),
            ))

        layout = CanvasLayoutResult(
            canvas_id=generate_id(IdPrefix.CANVAS, page_spec.page_id),
            canvas_spec=canvas_spec,
            page_spec=page_spec,
            template_id=self.template_id,
            template_version=self.version,
            reading_direction=page_spec.reading_direction,
            panel_slots=panels,
            trim_box=trim,
            bleed_box=bleed,
            safe_area_box=safe_area,
            usable_box=usable,
            reading_order_panel_ids=[item.panel_id for item in sorted(panels, key=lambda panel: panel.reading_order)],
        )
        self.validate_layout(layout, strict=True)
        return layout
