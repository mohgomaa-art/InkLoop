"""
InkLoop Canvas Generation Engine (E2) - Four-Koma (Yonkoma) Page Template.
Implements the canonical 4-panel vertical comic strip layout with Ki-Shō-Ten-Ketsu structure.
"""
import uuid
from typing import Tuple, Optional, Any, List

from app.contracts.geometry import Rect, snap_to_pixel_grid
from app.canvas.models import (
    CanvasSpec,
    PageSpec,
    PanelSlot,
    CanvasLayoutResult,
    LayoutTemplateId,
)
from app.canvas.errors import ImpossibleLayoutError, InvalidDimensionError
from app.canvas.templates.base import BaseLayoutTemplate

class FourKomaTemplate(BaseLayoutTemplate):
    """
    Deterministic Four-Koma (4-panel) vertical strip layout.
    Traditional Japanese/Korean comic format consisting of 4 stacked panels:
    - Panel 1: Ki (Introduction)
    - Panel 2: Shō (Development)
    - Panel 3: Ten (Climax / Twist)
    - Panel 4: Ketsu (Conclusion / Punchline)
    """
    template_id = LayoutTemplateId.FOUR_KOMA
    version = "1.0.0"
    description = "Four-panel vertical comic strip layout with uniform or rhythmic vertical spacing."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        rhythmic_ratios: Optional[Tuple[float, float, float, float]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        total_v_gutters = 3 * gutters.vertical  # 4 panels -> 3 vertical gutters
        net_h = usable_box.height - total_v_gutters

        if net_h <= 0:
            raise ImpossibleLayoutError(
                f"Vertical gutters ({total_v_gutters} px) exceed usable page height ({usable_box.height} px)",
                details={"usable_height": usable_box.height, "vertical_gutters": total_v_gutters}
            )

        if rhythmic_ratios is None:
            weights = [0.25, 0.25, 0.25, 0.25]
        else:
            if len(rhythmic_ratios) != 4:
                raise InvalidDimensionError(f"rhythmic_ratios must contain exactly 4 values, received {len(rhythmic_ratios)}")
            total_w = sum(rhythmic_ratios)
            if total_w <= 0:
                raise InvalidDimensionError("Sum of rhythmic_ratios must be strictly positive")
            weights = [w / total_w for w in rhythmic_ratios]

        panel_heights = [net_h * w for w in weights]

        # Calculate Y coordinates non-cumulatively
        y_offsets: List[float] = []
        cur_y = usable_box.y
        for i in range(4):
            y_offsets.append(cur_y)
            cur_y += panel_heights[i] + gutters.vertical

        panel_names = ["ki", "sho", "ten", "ketsu"]
        panels: List[PanelSlot] = []

        for i in range(4):
            raw_rect = Rect(
                x=usable_box.x,
                y=y_offsets[i],
                width=usable_box.width,
                height=panel_heights[i]
            )
            snapped = snap_to_pixel_grid(raw_rect)
            slot = PanelSlot(
                panel_id=f"panel_{i + 1:02d}_{panel_names[i]}",
                reading_order=i + 1,
                rect=snapped,
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            panels.append(slot)

        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_4koma_{uuid.uuid4().hex[:8]}",
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
