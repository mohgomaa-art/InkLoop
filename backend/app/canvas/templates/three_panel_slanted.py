"""
InkLoop Canvas Generation Engine (E2) - Three-Panel Slanted Template.
Generates 3 stacked panels separated by perspective slanted horizontal gutters (Image 3 layout).
"""
import uuid
import random
from typing import List, Optional, Any

from app.contracts.geometry import Rect, Point, snap_to_pixel_grid
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
    ReadingDirection,
)
from app.canvas.errors import ImpossibleLayoutError
from app.canvas.geometry_utils import (
    polygon_bounding_box,
    snap_polygon_to_grid,
)
from app.canvas.templates.base import BaseLayoutTemplate


class ThreePanelSlantedTemplate(BaseLayoutTemplate):
    """
    3-panel stacked cinematic layout with slanted horizontal gutters.
    Creates perspective momentum and cinematic tension.
    """
    template_id = LayoutTemplateId.THREE_PANEL_SLANTED
    version = "1.0.0"
    description = "3 stacked panels with slanted perspective gutters."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        seed: Optional[int] = None,
        slope_px: float = 40.0,
        ratios: Optional[List[float]] = None,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        rng = random.Random(seed) if seed is not None else None
        if rng is not None:
            slope_px = 30.0 + (rng.random() * 25.0)

        weights = ratios or [0.33, 0.34, 0.33]
        total_w = sum(weights)
        norm_w = [w / total_w for w in weights]

        total_v_gutters = 2 * gutters.vertical
        net_h = usable_box.height - total_v_gutters
        if net_h <= 0:
            raise ImpossibleLayoutError(f"Vertical gutters exceed usable height ({usable_box.height} px)")

        h1 = net_h * norm_w[0]
        h2 = net_h * norm_w[1]
        h3 = net_h * norm_w[2]

        # Nominal gutter divider central Y heights
        g1_nominal_y = usable_box.y + h1 + (gutters.vertical / 2.0)
        g2_nominal_y = g1_nominal_y + (gutters.vertical / 2.0) + h2 + (gutters.vertical / 2.0)

        half_g = gutters.vertical / 2.0

        # Slanted divider 1: left is (g1_nominal_y - slope_px/2), right is (g1_nominal_y + slope_px/2)
        # Slanted divider 2: left is (g2_nominal_y - slope_px/2), right is (g2_nominal_y + slope_px/2)
        # In RTL, slope can mirror
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        s = slope_px if not is_rtl else -slope_px

        # Panel 1: Top panel (usable.top to divider 1)
        poly1_raw = [
            Point(x=usable_box.x, y=usable_box.y),
            Point(x=usable_box.right, y=usable_box.y),
            Point(x=usable_box.right, y=g1_nominal_y + (s / 2.0) - half_g),
            Point(x=usable_box.x, y=g1_nominal_y - (s / 2.0) - half_g),
        ]
        poly1 = snap_polygon_to_grid(poly1_raw)
        rect1 = polygon_bounding_box(poly1)

        # Panel 2: Middle panel (divider 1 to divider 2)
        poly2_raw = [
            Point(x=usable_box.x, y=g1_nominal_y - (s / 2.0) + half_g),
            Point(x=usable_box.right, y=g1_nominal_y + (s / 2.0) + half_g),
            Point(x=usable_box.right, y=g2_nominal_y + (s / 2.0) - half_g),
            Point(x=usable_box.x, y=g2_nominal_y - (s / 2.0) - half_g),
        ]
        poly2 = snap_polygon_to_grid(poly2_raw)
        rect2 = polygon_bounding_box(poly2)

        # Panel 3: Bottom panel (divider 2 to usable.bottom)
        poly3_raw = [
            Point(x=usable_box.x, y=g2_nominal_y - (s / 2.0) + half_g),
            Point(x=usable_box.right, y=g2_nominal_y + (s / 2.0) + half_g),
            Point(x=usable_box.right, y=usable_box.bottom),
            Point(x=usable_box.x, y=usable_box.bottom),
        ]
        poly3 = snap_polygon_to_grid(poly3_raw)
        rect3 = polygon_bounding_box(poly3)

        p1_id = (panel_ids[0] if panel_ids and len(panel_ids) > 0 else "panel_01")
        p2_id = (panel_ids[1] if panel_ids and len(panel_ids) > 1 else "panel_02")
        p3_id = (panel_ids[2] if panel_ids and len(panel_ids) > 2 else "panel_03")

        slot1 = PanelSlot(
            panel_id=p1_id,
            reading_order=1,
            rect=rect1,
            polygon=poly1,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )
        slot2 = PanelSlot(
            panel_id=p2_id,
            reading_order=2,
            rect=rect2,
            polygon=poly2,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )
        slot3 = PanelSlot(
            panel_id=p3_id,
            reading_order=3,
            rect=rect3,
            polygon=poly3,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        panels = [slot1, slot2, slot3]
        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_slanted_{uuid.uuid4().hex[:8]}",
            canvas_spec=canvas_spec,
            page_spec=page_spec,
            template_id=self.template_id,
            template_version=self.version,
            reading_direction=page_spec.reading_direction,
            panel_slots=panels,
            trim_box=trim_box,
            bleed_box=bleed_box,
            safe_area_box=safe_area_box,
            usable_box=usable_box,
            reading_order_panel_ids=order_ids,
        )

        diags = self.validate_layout(result, strict=True)
        result.diagnostics = diags
        return result
