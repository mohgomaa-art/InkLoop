"""
InkLoop Canvas Generation Engine (E2) - Seven-Panel Action Burst Template.
High-density battle montage: 1 top banner + 3 mid rapid-action cuts + 3 explosive aftermath panels.
"""
from typing import List, Optional, Any
from app.contracts.geometry import Rect, snap_to_pixel_grid
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
    ReadingDirection,
)
from app.canvas.errors import ImpossibleLayoutError
from app.canvas.templates.base import BaseLayoutTemplate


class SevenPanelActionBurstTemplate(BaseLayoutTemplate):
    """
    7-panel action sequence layout:
    - Tier 1 (top): Establishing banner across full width (25% height)
    - Tier 2 (mid): 3 rapid-fire action cuts (37% height)
    - Tier 3 (bot): 3 impact aftermath / resolution cuts (38% height)
    """
    template_id = LayoutTemplateId.SEVEN_PANEL_ACTION_BURST
    version = "1.0.0"
    description = "7-panel battle montage: 1 banner + 3 rapid action cuts + 3 impact aftermath panels."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal

        total_v_space = usable_box.height - (2 * v_gutter)
        if total_v_space <= 0:
            raise ImpossibleLayoutError("Vertical gutters exceed usable height")

        h_t1 = total_v_space * 0.25
        h_t2 = total_v_space * 0.37
        h_t3 = total_v_space * 0.38

        net_w = usable_box.width - (2 * h_gutter)
        if net_w <= 0:
            raise ImpossibleLayoutError("Horizontal gutters exceed usable width")
        col_w = net_w / 3.0

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(7)
        ]

        # Tier 1: Banner
        slot_banner = PanelSlot(
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

        # Tier 2: 3 cuts
        y_t2 = usable_box.y + h_t1 + v_gutter
        slots_t2 = []
        cols = [2, 1, 0] if is_rtl else [0, 1, 2]
        for idx, col_idx in enumerate(cols):
            x_pos = usable_box.x + (col_idx * (col_w + h_gutter))
            slots_t2.append(PanelSlot(
                panel_id=p_ids[idx + 1],
                reading_order=idx + 2,
                rect=snap_to_pixel_grid(Rect(
                    x=x_pos,
                    y=y_t2,
                    width=col_w,
                    height=h_t2,
                )),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            ))

        # Tier 3: 3 cuts
        y_t3 = y_t2 + h_t2 + v_gutter
        slots_t3 = []
        for idx, col_idx in enumerate(cols):
            x_pos = usable_box.x + (col_idx * (col_w + h_gutter))
            slots_t3.append(PanelSlot(
                panel_id=p_ids[idx + 4],
                reading_order=idx + 5,
                rect=snap_to_pixel_grid(Rect(
                    x=x_pos,
                    y=y_t3,
                    width=col_w,
                    height=h_t3,
                )),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            ))

        import uuid
        panels = [slot_banner] + slots_t2 + slots_t3
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_burst_{uuid.uuid4().hex[:8]}",
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
