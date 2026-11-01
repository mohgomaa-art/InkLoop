"""
InkLoop Canvas Generation Engine (E2) - Three-Tier Action Slant Template.
Directly implements User Reference Image 1:
- Tier 1: Wide rectangular establishing header
- Tier 2: 2 dynamic wedge panels separated by a slanted vertical gutter
- Tier 3: Bottom dynamic panel with an angled chevron apex meeting the mid-tier gutter
"""
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


class ThreeTierActionSlantTemplate(BaseLayoutTemplate):
    """
    4-panel dynamic action layout (Matches User Reference Image 1):
    - Tier 1 (top): Horizontal rectangular panel (establishing beat)
    - Tier 2 (mid): 2 dynamic polygon panels with a slanted vertical gutter
    - Tier 3 (bot): Wide polygon panel with an angled top apex meeting the mid-tier divider
    """
    template_id = LayoutTemplateId.THREE_TIER_ACTION_SLANT
    version = "1.0.0"
    description = "4 panels: Top wide rectangle + 2 mid diagonal wedges + bottom chevron apex panel."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        header_height_ratio: float = 0.30,
        apex_offset_px: float = 35.0,
        slant_offset_px: float = 30.0,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal
        half_vg = v_gutter / 2.0
        half_hg = h_gutter / 2.0

        total_v_space = usable_box.height - (2 * v_gutter)
        if total_v_space <= 0:
            raise ImpossibleLayoutError("Vertical gutters exceed usable height")

        h_t1 = total_v_space * header_height_ratio
        rem_h = total_v_space - h_t1
        h_t2 = rem_h * 0.58
        h_t3 = rem_h * 0.42

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(4)
        ]

        # Tier 1 (Top): Wide rectangular header
        slot_p1 = PanelSlot(
            panel_id=p_ids[0],
            reading_order=1,
            rect=snap_to_pixel_grid(Rect(
                x=usable_box.x,
                y=usable_box.y,
                width=usable_box.width,
                height=h_t1,
            )),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        # Tier 2 & Tier 3 Divider calculations
        y_t2_top = usable_box.y + h_t1 + v_gutter
        y_divider_base = y_t2_top + h_t2
        mid_x = usable_box.x + (usable_box.width * (0.52 if not is_rtl else 0.48))

        dx_top = slant_offset_px if not is_rtl else -slant_offset_px
        dx_bot = -slant_offset_px if not is_rtl else slant_offset_px

        # The slanted vertical gutter endpoints
        top_cut_x = mid_x + dx_top
        bot_cut_x = mid_x + dx_bot

        # Chevron apex at bot_cut_x: apex rises slightly or dips
        apex_y = y_divider_base - apex_offset_px
        left_corner_y = y_divider_base + apex_offset_px
        right_corner_y = y_divider_base + apex_offset_px

        # Mid-tier Left Polygon
        poly_mid_l_raw = [
            Point(x=usable_box.x, y=y_t2_top),
            Point(x=top_cut_x - half_hg, y=y_t2_top),
            Point(x=bot_cut_x - half_hg, y=apex_y - half_vg),
            Point(x=usable_box.x, y=left_corner_y - half_vg),
        ]
        poly_mid_l = snap_polygon_to_grid(poly_mid_l_raw)

        # Mid-tier Right Polygon
        poly_mid_r_raw = [
            Point(x=top_cut_x + half_hg, y=y_t2_top),
            Point(x=usable_box.right, y=y_t2_top),
            Point(x=usable_box.right, y=right_corner_y - half_vg),
            Point(x=bot_cut_x + half_hg, y=apex_y - half_vg),
        ]
        poly_mid_r = snap_polygon_to_grid(poly_mid_r_raw)

        # Tier 3 (Bottom): Wide chevron panel
        poly_bot_raw = [
            Point(x=usable_box.x, y=left_corner_y + half_vg),
            Point(x=bot_cut_x, y=apex_y + half_vg),
            Point(x=usable_box.right, y=right_corner_y + half_vg),
            Point(x=usable_box.right, y=usable_box.bottom),
            Point(x=usable_box.x, y=usable_box.bottom),
        ]
        poly_bot = snap_polygon_to_grid(poly_bot_raw)

        if is_rtl:
            slot_p2 = PanelSlot(
                panel_id=p_ids[1],
                reading_order=2,
                rect=polygon_bounding_box(poly_mid_r),
                polygon=poly_mid_r,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p3 = PanelSlot(
                panel_id=p_ids[2],
                reading_order=3,
                rect=polygon_bounding_box(poly_mid_l),
                polygon=poly_mid_l,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
        else:
            slot_p2 = PanelSlot(
                panel_id=p_ids[1],
                reading_order=2,
                rect=polygon_bounding_box(poly_mid_l),
                polygon=poly_mid_l,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p3 = PanelSlot(
                panel_id=p_ids[2],
                reading_order=3,
                rect=polygon_bounding_box(poly_mid_r),
                polygon=poly_mid_r,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )

        slot_p4 = PanelSlot(
            panel_id=p_ids[3],
            reading_order=4,
            rect=polygon_bounding_box(poly_bot),
            polygon=poly_bot,
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        import uuid
        panels = [slot_p1, slot_p2, slot_p3, slot_p4]
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_3tier_{uuid.uuid4().hex[:8]}",
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
