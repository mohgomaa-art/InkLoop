"""
InkLoop Canvas Generation Engine (E2) - Three-Panel Hero Template.
Based on classic action manga layouts (2 tilted panels on top, 1 wide hero panel on bottom).
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


class ThreePanelHeroTemplate(BaseLayoutTemplate):
    """
    3-panel dynamic action layout:
    - Tier 1 (top): 2 vertical tilted panels split by a diagonal line
    - Tier 2 (bottom): 1 large panoramic/hero panel across the full usable width
    """
    template_id = LayoutTemplateId.THREE_PANEL_HERO
    version = "1.0.0"
    description = "3-panel dynamic layout with 2 tilted top panels and a wide hero panel below."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        seed: Optional[int] = None,
        split_ratio: float = 0.50,
        tilt_ratio: float = 0.08,
        top_row_height_ratio: float = 0.45,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        rng = random.Random(seed) if seed is not None else None
        if rng is not None:
            split_ratio = 0.45 + (rng.random() * 0.10)
            tilt_ratio = 0.05 + (rng.random() * 0.06)

        total_v_gutter = gutters.vertical
        net_h = usable_box.height - total_v_gutter
        if net_h <= 0:
            raise ImpossibleLayoutError(f"Vertical gutter ({gutters.vertical} px) exceeds usable height ({usable_box.height} px)")

        h_top = net_h * top_row_height_ratio
        h_bot = net_h * (1.0 - top_row_height_ratio)

        y_top = usable_box.y
        y_top_end = y_top + h_top
        y_bot_start = y_top_end + gutters.vertical

        # Top row: diagonal cut between left and right panels
        h_gutter = gutters.horizontal
        net_w = usable_box.width - h_gutter
        if net_w <= 0:
            raise ImpossibleLayoutError(f"Horizontal gutter ({h_gutter} px) exceeds usable width ({usable_box.width} px)")

        mid_x = usable_box.x + (net_w * split_ratio)
        dx = net_w * tilt_ratio
        half_g = h_gutter / 2.0

        cut_top_x = max(usable_box.x + 40.0, min(usable_box.right - 40.0, mid_x + dx))
        cut_bot_x = max(usable_box.x + 40.0, min(usable_box.right - 40.0, mid_x - dx))

        poly_left_raw = [
            Point(x=usable_box.x, y=y_top),
            Point(x=cut_top_x - half_g, y=y_top),
            Point(x=cut_bot_x - half_g, y=y_top_end),
            Point(x=usable_box.x, y=y_top_end),
        ]
        poly_left = snap_polygon_to_grid(poly_left_raw)
        rect_left = polygon_bounding_box(poly_left)

        poly_right_raw = [
            Point(x=cut_top_x + half_g, y=y_top),
            Point(x=usable_box.right, y=y_top),
            Point(x=usable_box.right, y=y_top_end),
            Point(x=cut_bot_x + half_g, y=y_top_end),
        ]
        poly_right = snap_polygon_to_grid(poly_right_raw)
        rect_right = polygon_bounding_box(poly_right)

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        p1_id = (panel_ids[0] if panel_ids and len(panel_ids) > 0 else "panel_01")
        p2_id = (panel_ids[1] if panel_ids and len(panel_ids) > 1 else "panel_02")
        p3_id = (panel_ids[2] if panel_ids and len(panel_ids) > 2 else "panel_03")

        if is_rtl:
            slot_p1 = PanelSlot(
                panel_id=p1_id,
                reading_order=1,
                rect=rect_right,
                polygon=poly_right,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p2 = PanelSlot(
                panel_id=p2_id,
                reading_order=2,
                rect=rect_left,
                polygon=poly_left,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
        else:
            slot_p1 = PanelSlot(
                panel_id=p1_id,
                reading_order=1,
                rect=rect_left,
                polygon=poly_left,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p2 = PanelSlot(
                panel_id=p2_id,
                reading_order=2,
                rect=rect_right,
                polygon=poly_right,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )

        # Bottom row: full-width hero panel
        rect_bot = snap_to_pixel_grid(Rect(
            x=usable_box.x,
            y=y_bot_start,
            width=usable_box.width,
            height=h_bot
        ))
        slot_p3 = PanelSlot(
            panel_id=p3_id,
            reading_order=3,
            rect=rect_bot,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        panels = [slot_p1, slot_p2, slot_p3]
        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_hero_{uuid.uuid4().hex[:8]}",
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
