"""
InkLoop Canvas Generation Engine (E2) - Dynamic Shonen/Action Page Template.
Generates dynamic high-energy action page layouts with polygonal diagonal slash cuts,
asymmetric framing, and deterministic reproducible seeding.
"""
import uuid
import random
import math
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
from app.canvas.errors import ImpossibleLayoutError, InvalidDimensionError
from app.canvas.geometry_utils import (
    polygon_bounding_box,
    snap_polygon_to_grid,
    shoelace_area,
)
from app.canvas.templates.base import BaseLayoutTemplate

class DynamicShonenTemplate(BaseLayoutTemplate):
    """
    Deterministic dynamic action layout template for Shonen manga.
    Features:
    - Panel 1: Top cinematic establishing shot (horizontal rectangle)
    - Panels 2 & 3: High-energy diagonal slash cut producing two interlocking polygonal/trapezoidal panels
    - Panel 4: Bottom impact hero panel (horizontal rectangle)
    """
    template_id = LayoutTemplateId.DYNAMIC_SHONEN
    version = "1.0.0"
    description = "Dynamic action manga layout with diagonal polygon cuts and deterministic seeding."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        seed: Optional[int] = None,
        slash_tilt_ratio: float = 0.15,
        split_ratio: float = 0.50,
        top_row_height_ratio: float = 0.28,
        bottom_row_height_ratio: float = 0.32,
        panel_ids: Optional[List[str]] = None,
        bottom_gutter_peak_px: float = 0.0,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        if params.get("bottom_gutter_style") == "peak_v" and bottom_gutter_peak_px <= 0:
            bottom_gutter_peak_px = 35.0

        # Deterministic variation using explicit seed if provided
        rng = random.Random(seed) if seed is not None else None
        if rng is not None:
            # Constrained, safe parameter nudging based on seed
            slash_tilt_ratio = 0.10 + (rng.random() * 0.10)  # [0.10, 0.20]
            split_ratio = 0.45 + (rng.random() * 0.10)       # [0.45, 0.55]

        # Validate vertical distribution
        mid_row_height_ratio = 1.0 - (top_row_height_ratio + bottom_row_height_ratio)
        if mid_row_height_ratio <= 0.15:
            raise ImpossibleLayoutError(
                f"Middle dynamic row height ratio ({mid_row_height_ratio:.2f}) is too small (must be >= 0.15)"
            )

        total_v_gutters = 2 * gutters.vertical  # 3 rows -> 2 vertical gutters
        net_h = usable_box.height - total_v_gutters

        if net_h <= 0:
            raise ImpossibleLayoutError(f"Vertical gutters exceed usable height ({usable_box.height} px)")

        h_top = net_h * top_row_height_ratio
        h_mid = net_h * mid_row_height_ratio
        h_bot = net_h * bottom_row_height_ratio

        # Calculate Y positions
        y_top = usable_box.y
        y_mid_start = y_top + h_top + gutters.vertical
        y_mid_end = y_mid_start + h_mid
        y_bot_start = y_mid_end + gutters.vertical

        p1_id = panel_ids[0] if panel_ids and len(panel_ids) > 0 else "panel_01"
        p2_id = panel_ids[1] if panel_ids and len(panel_ids) > 1 else "panel_02"
        p3_id = panel_ids[2] if panel_ids and len(panel_ids) > 2 else "panel_03"
        p4_id = panel_ids[3] if panel_ids and len(panel_ids) > 3 else "panel_04"

        # 1. Panel 1: Top cinematic horizontal panel
        rect_top = snap_to_pixel_grid(Rect(
            x=usable_box.x,
            y=y_top,
            width=usable_box.width,
            height=h_top
        ))
        slot_top = PanelSlot(
            panel_id=p1_id,
            reading_order=1,
            rect=rect_top,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        # 2. Middle Row: Diagonal dynamic slash cut
        # Net width for the middle row accounting for horizontal gutter
        h_gutter = gutters.horizontal
        net_mid_w = usable_box.width - h_gutter
        if net_mid_w <= 0:
            raise ImpossibleLayoutError(f"Horizontal gutter ({h_gutter} px) exceeds usable width ({usable_box.width} px)")

        # Center split X
        mid_split_x = usable_box.x + (net_mid_w * split_ratio)
        # Shift X for top and bottom of the diagonal cut line
        dx = net_mid_w * slash_tilt_ratio

        # Ensure diagonal line stays well within margins
        cut_top_x = max(usable_box.x + 50.0, min(usable_box.right - 50.0, mid_split_x + dx))
        cut_bot_x = max(usable_box.x + 50.0, min(usable_box.right - 50.0, mid_split_x - dx))

        half_g = h_gutter / 2.0
        peak = min(bottom_gutter_peak_px, h_mid * 0.25, h_bot * 0.25)

        # Left polygon in middle row (P_left)
        poly_left_raw = [
            Point(x=usable_box.x, y=y_mid_start),
            Point(x=cut_top_x - half_g, y=y_mid_start),
            Point(x=cut_bot_x - half_g, y=y_mid_end - peak),
            Point(x=usable_box.x, y=y_mid_end),
        ]
        poly_left = snap_polygon_to_grid(poly_left_raw)
        rect_left = polygon_bounding_box(poly_left)

        # Right polygon in middle row (P_right)
        poly_right_raw = [
            Point(x=cut_top_x + half_g, y=y_mid_start),
            Point(x=usable_box.right, y=y_mid_start),
            Point(x=usable_box.right, y=y_mid_end),
            Point(x=cut_bot_x + half_g, y=y_mid_end - peak),
        ]
        poly_right = snap_polygon_to_grid(poly_right_raw)
        rect_right = polygon_bounding_box(poly_right)

        # Determine middle row reading order based on reading direction
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        if is_rtl:
            slot_mid_first = PanelSlot(
                panel_id=p2_id,
                reading_order=2,
                rect=rect_right,
                polygon=poly_right,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_mid_second = PanelSlot(
                panel_id=p3_id,
                reading_order=3,
                rect=rect_left,
                polygon=poly_left,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
        else:
            slot_mid_first = PanelSlot(
                panel_id=p2_id,
                reading_order=2,
                rect=rect_left,
                polygon=poly_left,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_mid_second = PanelSlot(
                panel_id=p3_id,
                reading_order=3,
                rect=rect_right,
                polygon=poly_right,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )

        # 3. Panel 4: Bottom climax impact panel (supports angled peak gutter matching Image 1)
        if peak > 0:
            poly_bot_raw = [
                Point(x=usable_box.x, y=y_bot_start),
                Point(x=cut_bot_x, y=y_bot_start - peak),
                Point(x=usable_box.right, y=y_bot_start),
                Point(x=usable_box.right, y=usable_box.bottom),
                Point(x=usable_box.x, y=usable_box.bottom),
            ]
            poly_bot = snap_polygon_to_grid(poly_bot_raw)
            rect_bot = polygon_bounding_box(poly_bot)
            slot_bot = PanelSlot(
                panel_id=p4_id,
                reading_order=4,
                rect=rect_bot,
                polygon=poly_bot,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
        else:
            rect_bot = snap_to_pixel_grid(Rect(
                x=usable_box.x,
                y=y_bot_start,
                width=usable_box.width,
                height=h_bot
            ))
            slot_bot = PanelSlot(
                panel_id=p4_id,
                reading_order=4,
                rect=rect_bot,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )

        panels = [slot_top, slot_mid_first, slot_mid_second, slot_bot]
        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_shonen_{uuid.uuid4().hex[:8]}",
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
