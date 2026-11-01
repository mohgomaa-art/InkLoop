"""
InkLoop Canvas Generation Engine (E2) - Shonen Climax Spread Template.
Features a dominant 62% width hero splash panel commanding the page with 3 stacked reaction cuts.
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


class ShonenClimaxSpreadTemplate(BaseLayoutTemplate):
    """
    4-panel climax layout:
    - Dominant hero splash panel (62% width, 100% usable height)
    - 3 stacked vertical reaction panels (38% width, 3 vertical tiers)
    """
    template_id = LayoutTemplateId.SHONEN_CLIMAX_SPREAD
    version = "1.0.0"
    description = "Dominant 62% hero splash panel with 3 stacked reaction cuts."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        hero_width_ratio: float = 0.62,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        v_gutter = gutters.vertical
        h_gutter = gutters.horizontal

        net_w = usable_box.width - h_gutter
        if net_w <= 0:
            raise ImpossibleLayoutError("Horizontal gutter exceeds usable width")

        w_hero = net_w * hero_width_ratio
        w_side = net_w * (1.0 - hero_width_ratio)

        total_v_side = usable_box.height - (2 * v_gutter)
        if total_v_side <= 0:
            raise ImpossibleLayoutError("Vertical gutters exceed usable height")

        h_cut = total_v_side / 3.0
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)

        p_ids = [
            (panel_ids[i] if panel_ids and len(panel_ids) > i else f"panel_{i+1:02d}")
            for i in range(4)
        ]

        # In RTL: Hero is on the right (reading order 1) or left based on climax emphasis
        # Standard manga climax: reading order 1 is the hero panel (right in RTL), cuts follow on left
        if is_rtl:
            x_hero = usable_box.x + w_side + h_gutter
            x_side = usable_box.x
        else:
            x_hero = usable_box.x
            x_side = usable_box.x + w_hero + h_gutter

        slot_hero = PanelSlot(
            panel_id=p_ids[0],
            reading_order=1,
            rect=snap_to_pixel_grid(Rect(
                x=x_hero,
                y=usable_box.y,
                width=w_hero,
                height=usable_box.height,
            )),
            is_full_bleed=False,
            is_intentional_overlap=False,
            z_index=0,
        )

        slots_cuts = []
        for i in range(3):
            y_cut = usable_box.y + (i * (h_cut + v_gutter))
            slots_cuts.append(PanelSlot(
                panel_id=p_ids[i + 1],
                reading_order=i + 2,
                rect=snap_to_pixel_grid(Rect(
                    x=x_side,
                    y=y_cut,
                    width=w_side,
                    height=h_cut,
                )),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            ))

        import uuid
        panels = [slot_hero] + slots_cuts
        order_ids = [p.panel_id for p in panels]
        result = CanvasLayoutResult(
            canvas_id=f"canvas_climax_{uuid.uuid4().hex[:8]}",
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
