"""
InkLoop Canvas Generation Engine (E2) - Standard Six-Panel Classic Page Template.
Implements the canonical 6-panel manga/comic page with 3 rows and 2 columns,
featuring proportional dramatic heights (establishing, action, reaction) and deterministic ordering.
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
    ReadingDirection,
)
from app.canvas.errors import ImpossibleLayoutError, InvalidDimensionError
from app.canvas.templates.base import BaseLayoutTemplate

class SixPanelClassicTemplate(BaseLayoutTemplate):
    """
    Deterministic 6-panel template with classic comic proportions:
    - Row 1 (Top): Establishing shot (~30% height)
    - Row 2 (Middle): Dynamic action / development (~38% height)
    - Row 3 (Bottom): Cliffhanger / reaction shot (~32% height)
    """
    template_id = LayoutTemplateId.SIX_PANEL_CLASSIC
    version = "1.0.0"
    description = "Classic six-panel comic page with 3 rows of 2 panels and dramatic row proportions."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        row_proportions: Tuple[float, float, float] = (0.30, 0.38, 0.32),
        asymmetric_col_split: bool = False,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        if panel_ids is not None and len(panel_ids) != 6:
            raise InvalidDimensionError(f"panel_ids must contain exactly 6 IDs, got {len(panel_ids)}")
        if panel_ids is not None and len(set(panel_ids)) != 6:
            raise InvalidDimensionError("panel_ids must be unique")
        if len(row_proportions) != 3:
            raise InvalidDimensionError(f"row_proportions must have exactly 3 values, got {len(row_proportions)}")

        total_rp = sum(row_proportions)
        if total_rp <= 0:
            raise InvalidDimensionError("Sum of row_proportions must be strictly positive")

        norm_row_ratios = [r / total_rp for r in row_proportions]

        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)
        gutters = canvas_spec.gutters

        total_h_gutters = gutters.horizontal  # 2 columns -> 1 horizontal gutter
        total_v_gutters = 2 * gutters.vertical  # 3 rows -> 2 vertical gutters

        net_w = usable_box.width - total_h_gutters
        net_h = usable_box.height - total_v_gutters

        if net_w <= 0:
            raise ImpossibleLayoutError(f"Horizontal gutter ({gutters.horizontal} px) exceeds usable width ({usable_box.width} px)")

        if net_h <= 0:
            raise ImpossibleLayoutError(f"Vertical gutters ({total_v_gutters} px) exceed usable height ({usable_box.height} px)")

        row_heights = [net_h * r for r in norm_row_ratios]

        # Calculate row Y coordinates non-cumulatively
        y_offsets = [
            usable_box.y,
            usable_box.y + row_heights[0] + gutters.vertical,
            usable_box.y + row_heights[0] + row_heights[1] + (2 * gutters.vertical),
        ]

        # Column width distributions: symmetrical (0.5, 0.5) or slight dynamic variation if asymmetric_col_split
        # Row 1: 50% / 50%
        # Row 2: 55% / 45% if asymmetric
        # Row 3: 45% / 55% if asymmetric
        col_splits = [
            (0.5, 0.5),
            (0.55, 0.45) if asymmetric_col_split else (0.5, 0.5),
            (0.45, 0.55) if asymmetric_col_split else (0.5, 0.5),
        ]

        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        panels: List[PanelSlot] = []
        reading_idx = 1

        for r in range(3):
            w_left_ratio, w_right_ratio = col_splits[r]
            w_left = net_w * w_left_ratio
            w_right = net_w * w_right_ratio

            x_left = usable_box.x
            x_right = usable_box.x + w_left + gutters.horizontal

            # In RTL: right panel is read first, left panel is read second
            if is_rtl:
                p_first_rect = Rect(x=x_right, y=y_offsets[r], width=w_right, height=row_heights[r])
                p_second_rect = Rect(x=x_left, y=y_offsets[r], width=w_left, height=row_heights[r])
                first_suffix = "a"
                second_suffix = "b"
            else:
                p_first_rect = Rect(x=x_left, y=y_offsets[r], width=w_left, height=row_heights[r])
                p_second_rect = Rect(x=x_right, y=y_offsets[r], width=w_right, height=row_heights[r])
                first_suffix = "a"
                second_suffix = "b"

            # Create first panel in row
            slot_first = PanelSlot(
                panel_id=panel_ids[reading_idx - 1] if panel_ids else f"panel_{reading_idx:02d}",
                reading_order=reading_idx,
                rect=snap_to_pixel_grid(p_first_rect),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            panels.append(slot_first)
            reading_idx += 1

            # Create second panel in row
            slot_second = PanelSlot(
                panel_id=panel_ids[reading_idx - 1] if panel_ids else f"panel_{reading_idx:02d}",
                reading_order=reading_idx,
                rect=snap_to_pixel_grid(p_second_rect),
                is_full_bleed=False,
                is_intentional_overlap=False,
                z_index=0,
            )
            panels.append(slot_second)
            reading_idx += 1

        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_six_{uuid.uuid4().hex[:8]}",
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
