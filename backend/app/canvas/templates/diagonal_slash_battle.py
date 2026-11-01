"""
InkLoop Canvas Generation Engine (E2) - Diagonal Slash Battle Template.
Directly implements User Reference Image 2: 6 panels with an aggressive diagonal slash cutting across the central tier.
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


class DiagonalSlashBattleTemplate(BaseLayoutTemplate):
    """
    6-panel action combat layout:
    - Tier 1 (top): 2 panels (establishing fighters / staredown)
    - Tier 2 & 3 (mid): A dramatic diagonal slash cutting across the page dividing 2 clash panels above and 2 response panels below
    - Tier 4 (bottom): 2 panels (impact aftermath / reaction)
    """
    template_id = LayoutTemplateId.DIAGONAL_SLASH_BATTLE
    version = "1.0.0"
    description = "6-panel action combat layout with a dynamic diagonal slash cutting across the page."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        slash_slope_px: float = 45.0,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal
        half_vg = v_gutter / 2.0
        half_hg = h_gutter / 2.0

        total_v_space = usable_box.height - (3 * v_gutter)
        if total_v_space <= 0:
            raise ImpossibleLayoutError("Vertical gutters exceed usable height")

        # 3 main vertical sections: top (24%), mid (50%), bot (26%)
        h_tier1 = total_v_space * 0.24
        h_tier_mid = total_v_space * 0.50
        h_tier_bot = total_v_space * 0.26

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        slope = -slash_slope_px if is_rtl else slash_slope_px

        net_w = usable_box.width - h_gutter
        if net_w <= 0:
            raise ImpossibleLayoutError("Horizontal gutter exceeds usable width")
        col_w = net_w / 2.0

        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(6)
        ]

        # Tier 1 (Top): 2 panels
        y_t1_top = usable_box.y
        y_t1_bot = y_t1_top + h_tier1

        x_col1_l = usable_box.x
        x_col1_r = x_col1_l + col_w
        x_col2_l = x_col1_r + h_gutter
        x_col2_r = usable_box.right

        # Reading order: RTL starts with right column
        first_col_x = x_col2_l if is_rtl else x_col1_l
        second_col_x = x_col1_l if is_rtl else x_col2_l

        slot_p1 = PanelSlot(
            panel_id=p_ids[0],
            reading_order=1,
            rect=snap_to_pixel_grid(Rect(x=first_col_x, y=y_t1_top, width=col_w, height=h_tier1)),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )
        slot_p2 = PanelSlot(
            panel_id=p_ids[1],
            reading_order=2,
            rect=snap_to_pixel_grid(Rect(x=second_col_x, y=y_t1_top, width=col_w, height=h_tier1)),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        # Mid Tier: Diagonal slash dividing top-mid and bot-mid
        y_mid_start = y_t1_bot + v_gutter
        y_mid_end = y_mid_start + h_tier_mid
        y_mid_center = y_mid_start + (h_tier_mid / 2.0)

        # Diagonal line: left is (y_mid_center - slope), right is (y_mid_center + slope)
        slash_left_y = y_mid_center - slope
        slash_right_y = y_mid_center + slope
        slash_mid_x = usable_box.x + (usable_box.width / 2.0)
        slash_mid_y = (slash_left_y + slash_right_y) / 2.0

        # Mid-tier Top-Left Polygon
        poly_tl_raw = [
            Point(x=x_col1_l, y=y_mid_start),
            Point(x=x_col1_r, y=y_mid_start),
            Point(x=x_col1_r, y=slash_mid_y - half_vg),
            Point(x=x_col1_l, y=slash_left_y - half_vg),
        ]
        poly_tl = snap_polygon_to_grid(poly_tl_raw)

        # Mid-tier Top-Right Polygon
        poly_tr_raw = [
            Point(x=x_col2_l, y=y_mid_start),
            Point(x=x_col2_r, y=y_mid_start),
            Point(x=x_col2_r, y=slash_right_y - half_vg),
            Point(x=x_col2_l, y=slash_mid_y - half_vg),
        ]
        poly_tr = snap_polygon_to_grid(poly_tr_raw)

        # Mid-tier Bot-Left Polygon
        poly_bl_raw = [
            Point(x=x_col1_l, y=slash_left_y + half_vg),
            Point(x=x_col1_r, y=slash_mid_y + half_vg),
            Point(x=x_col1_r, y=y_mid_end),
            Point(x=x_col1_l, y=y_mid_end),
        ]
        poly_bl = snap_polygon_to_grid(poly_bl_raw)

        # Mid-tier Bot-Right Polygon
        poly_br_raw = [
            Point(x=x_col2_l, y=slash_mid_y + half_vg),
            Point(x=x_col2_r, y=slash_right_y + half_vg),
            Point(x=x_col2_r, y=y_mid_end),
            Point(x=x_col2_l, y=y_mid_end),
        ]
        poly_br = snap_polygon_to_grid(poly_br_raw)

        if is_rtl:
            slot_p3 = PanelSlot(
                panel_id=p_ids[2],
                reading_order=3,
                rect=polygon_bounding_box(poly_tr),
                polygon=poly_tr,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p4 = PanelSlot(
                panel_id=p_ids[3],
                reading_order=4,
                rect=polygon_bounding_box(poly_tl),
                polygon=poly_tl,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p5 = PanelSlot(
                panel_id=p_ids[4],
                reading_order=5,
                rect=polygon_bounding_box(poly_br),
                polygon=poly_br,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p6 = PanelSlot(
                panel_id=p_ids[5],
                reading_order=6,
                rect=polygon_bounding_box(poly_bl),
                polygon=poly_bl,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
        else:
            slot_p3 = PanelSlot(
                panel_id=p_ids[2],
                reading_order=3,
                rect=polygon_bounding_box(poly_tl),
                polygon=poly_tl,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p4 = PanelSlot(
                panel_id=p_ids[3],
                reading_order=4,
                rect=polygon_bounding_box(poly_tr),
                polygon=poly_tr,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p5 = PanelSlot(
                panel_id=p_ids[4],
                reading_order=5,
                rect=polygon_bounding_box(poly_bl),
                polygon=poly_bl,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            slot_p6 = PanelSlot(
                panel_id=p_ids[5],
                reading_order=6,
                rect=polygon_bounding_box(poly_br),
                polygon=poly_br,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )

        import uuid
        panels = [slot_p1, slot_p2, slot_p3, slot_p4, slot_p5, slot_p6]
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_slash_{uuid.uuid4().hex[:8]}",
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
