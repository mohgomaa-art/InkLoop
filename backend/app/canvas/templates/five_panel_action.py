"""
InkLoop Canvas Generation Engine (E2) - Five-Panel Action Template.
Based on dynamic 5-panel comic layouts (Image 5: top diagonal split, middle wide, bottom 2 panels).
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


class FivePanelActionTemplate(BaseLayoutTemplate):
    """
    5-panel dynamic action layout:
    - Tier 1 (top): 2 panels split by a dynamic diagonal slash cut
    - Tier 2 (middle): 1 full-width widescreen panoramic panel
    - Tier 3 (bottom): 2 vertical panels with straight vertical gutter
    """
    template_id = LayoutTemplateId.FIVE_PANEL_ACTION
    version = "1.0.0"
    description = "5-panel dynamic action layout with diagonal split top, wide middle, and two bottom panels."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        seed: Optional[int] = None,
        top_slash_tilt: float = 0.12,
        tier_ratios: Optional[List[float]] = None,
        bottom_split_ratio: float = 0.45,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        rng = random.Random(seed) if seed is not None else None
        if rng is not None:
            top_slash_tilt = 0.08 + (rng.random() * 0.08)

        ratios = tier_ratios or [0.32, 0.36, 0.32]
        tot = sum(ratios)
        norm_r = [r / tot for r in ratios]

        total_v_gutters = 2 * gutters.vertical
        net_h = usable_box.height - total_v_gutters
        if net_h <= 0:
            raise ImpossibleLayoutError(f"Vertical gutters exceed usable height ({usable_box.height} px)")

        h1 = net_h * norm_r[0]
        h2 = net_h * norm_r[1]
        h3 = net_h * norm_r[2]

        y1 = usable_box.y
        y1_end = y1 + h1
        y2 = y1_end + gutters.vertical
        y2_end = y2 + h2
        y3 = y2_end + gutters.vertical

        # Tier 1: Diagonal slash between 2 panels
        h_gutter = gutters.horizontal
        net_w = usable_box.width - h_gutter
        if net_w <= 0:
            raise ImpossibleLayoutError(f"Horizontal gutter exceeds usable width ({usable_box.width} px)")

        mid_x = usable_box.x + (net_w * 0.55)
        dx = net_w * top_slash_tilt
        half_g = h_gutter / 2.0

        cut_top_x = max(usable_box.x + 40.0, min(usable_box.right - 40.0, mid_x + dx))
        cut_bot_x = max(usable_box.x + 40.0, min(usable_box.right - 40.0, mid_x - dx))

        poly_top_left_raw = [
            Point(x=usable_box.x, y=y1),
            Point(x=cut_top_x - half_g, y=y1),
            Point(x=cut_bot_x - half_g, y=y1_end),
            Point(x=usable_box.x, y=y1_end),
        ]
        poly_top_left = snap_polygon_to_grid(poly_top_left_raw)
        rect_top_left = polygon_bounding_box(poly_top_left)

        poly_top_right_raw = [
            Point(x=cut_top_x + half_g, y=y1),
            Point(x=usable_box.right, y=y1),
            Point(x=usable_box.right, y=y1_end),
            Point(x=cut_bot_x + half_g, y=y1_end),
        ]
        poly_top_right = snap_polygon_to_grid(poly_top_right_raw)
        rect_top_right = polygon_bounding_box(poly_top_right)

        # Tier 2: Widescreen horizontal panel
        rect_mid = snap_to_pixel_grid(Rect(
            x=usable_box.x,
            y=y2,
            width=usable_box.width,
            height=h2
        ))

        # Tier 3: 2 vertical panels with straight vertical gutter
        w_bot_left = net_w * bottom_split_ratio
        w_bot_right = net_w * (1.0 - bottom_split_ratio)

        rect_bot_left = snap_to_pixel_grid(Rect(
            x=usable_box.x,
            y=y3,
            width=w_bot_left,
            height=h3
        ))
        rect_bot_right = snap_to_pixel_grid(Rect(
            x=usable_box.x + w_bot_left + h_gutter,
            y=y3,
            width=w_bot_right,
            height=h3
        ))

        p_ids = panel_ids or [f"panel_{i:02d}" for i in range(1, 6)]
        while len(p_ids) < 5:
            p_ids.append(f"panel_{len(p_ids)+1:02d}")

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)

        # Reading order:
        # Tier 1: p1 and p2 (RTL: right then left)
        # Tier 2: p3
        # Tier 3: p4 and p5 (RTL: right then left)
        if is_rtl:
            slot1 = PanelSlot(panel_id=p_ids[0], reading_order=1, rect=rect_top_right, polygon=poly_top_right, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot2 = PanelSlot(panel_id=p_ids[1], reading_order=2, rect=rect_top_left, polygon=poly_top_left, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot3 = PanelSlot(panel_id=p_ids[2], reading_order=3, rect=rect_mid, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot4 = PanelSlot(panel_id=p_ids[3], reading_order=4, rect=rect_bot_right, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot5 = PanelSlot(panel_id=p_ids[4], reading_order=5, rect=rect_bot_left, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
        else:
            slot1 = PanelSlot(panel_id=p_ids[0], reading_order=1, rect=rect_top_left, polygon=poly_top_left, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot2 = PanelSlot(panel_id=p_ids[1], reading_order=2, rect=rect_top_right, polygon=poly_top_right, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot3 = PanelSlot(panel_id=p_ids[2], reading_order=3, rect=rect_mid, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot4 = PanelSlot(panel_id=p_ids[3], reading_order=4, rect=rect_bot_left, is_full_bleed=False, is_intentional_overlap=False, z_index=0)
            slot5 = PanelSlot(panel_id=p_ids[4], reading_order=5, rect=rect_bot_right, is_full_bleed=False, is_intentional_overlap=False, z_index=0)

        panels = [slot1, slot2, slot3, slot4, slot5]
        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_action5_{uuid.uuid4().hex[:8]}",
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
