"""
InkLoop Canvas Generation Engine (E2) - Standard Manga/Manhwa Grid Template.
Generates configurable regular or proportional grid layouts with strict non-cumulative
coordinate derivation, gutter spacing, and deterministic reading order (RTL/LTR).
"""
import uuid
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
from app.canvas.errors import ImpossibleLayoutError, InvalidDimensionError
from app.canvas.templates.base import BaseLayoutTemplate

class MangaGridLayoutTemplate(BaseLayoutTemplate):
    """
    Configurable regular or proportional grid template for Manga and Manhwa pages.
    Derives panel bounds directly from usable area, margins, and gutters.
    """
    template_id = LayoutTemplateId.MANGA_GRID
    version = "1.0.0"
    description = "Standard configurable manga/manhwa grid with rows, columns, and custom ratios."

    def generate(
        self,
        canvas_spec: CanvasSpec,
        page_spec: PageSpec,
        rows: int = 2,
        cols: int = 2,
        row_ratios: Optional[List[float]] = None,
        col_ratios: Optional[List[float]] = None,
        panel_ids: Optional[List[str]] = None,
        **params: Any
    ) -> CanvasLayoutResult:
        if rows < 1 or cols < 1:
            raise InvalidDimensionError(f"Grid rows and columns must be >= 1, received rows={rows}, cols={cols}")

        if rows > 20 or cols > 10:
            raise ImpossibleLayoutError(f"Grid panel density exceeds practical comic page limit (rows={rows}, cols={cols})")
        if panel_ids is not None and len(panel_ids) != rows * cols:
            raise InvalidDimensionError(f"panel_ids must contain exactly {rows * cols} IDs, got {len(panel_ids)}")
        if panel_ids is not None and len(set(panel_ids)) != len(panel_ids):
            raise InvalidDimensionError("panel_ids must be unique")

        trim_box, bleed_box, safe_area_box, usable_box = self.compute_canonical_boxes(canvas_spec)

        gutters = canvas_spec.gutters
        total_horizontal_gutters = (cols - 1) * gutters.horizontal
        total_vertical_gutters = (rows - 1) * gutters.vertical

        net_width = usable_box.width - total_horizontal_gutters
        net_height = usable_box.height - total_vertical_gutters

        if net_width <= 0:
            raise ImpossibleLayoutError(
                f"Horizontal gutters ({total_horizontal_gutters} px) exceed usable width ({usable_box.width} px)",
                details={"usable_width": usable_box.width, "gutters": total_horizontal_gutters, "cols": cols}
            )

        if net_height <= 0:
            raise ImpossibleLayoutError(
                f"Vertical gutters ({total_vertical_gutters} px) exceed usable height ({usable_box.height} px)",
                details={"usable_height": usable_box.height, "gutters": total_vertical_gutters, "rows": rows}
            )

        # Normalize column and row ratios
        if col_ratios is None:
            col_weights = [1.0 / cols] * cols
        else:
            if len(col_ratios) != cols:
                raise InvalidDimensionError(f"col_ratios length ({len(col_ratios)}) must match cols ({cols})")
            total_cw = sum(col_ratios)
            if total_cw <= 0:
                raise InvalidDimensionError("Sum of col_ratios must be strictly positive")
            col_weights = [r / total_cw for r in col_ratios]

        if row_ratios is None:
            row_weights = [1.0 / rows] * rows
        else:
            if len(row_ratios) != rows:
                raise InvalidDimensionError(f"row_ratios length ({len(row_ratios)}) must match rows ({rows})")
            total_rw = sum(row_ratios)
            if total_rw <= 0:
                raise InvalidDimensionError("Sum of row_ratios must be strictly positive")
            row_weights = [r / total_rw for r in row_ratios]

        # Calculate discrete widths and heights
        col_widths = [net_width * w for w in col_weights]
        row_heights = [net_height * h for h in row_weights]

        # Non-cumulative coordinate computation for exact stability
        # x_offsets[c] is the left coordinate of column c
        x_offsets: List[float] = []
        cur_x = usable_box.x
        for c in range(cols):
            x_offsets.append(cur_x)
            cur_x += col_widths[c] + gutters.horizontal

        y_offsets: List[float] = []
        cur_y = usable_box.y
        for r in range(rows):
            y_offsets.append(cur_y)
            cur_y += row_heights[r] + gutters.vertical

        # Generate panels and assign reading order
        panels: List[PanelSlot] = []
        is_rtl = (page_spec.reading_direction == ReadingDirection.RTL)
        reading_idx = 1

        for r in range(rows):
            # In RTL, column traversal order is from right (cols-1) to left (0)
            col_indices = list(reversed(range(cols))) if is_rtl else list(range(cols))
            for c in col_indices:
                raw_rect = Rect(
                    x=x_offsets[c],
                    y=y_offsets[r],
                    width=col_widths[c],
                    height=row_heights[r]
                )
                snapped = snap_to_pixel_grid(raw_rect)
                panel_id = panel_ids[reading_idx - 1] if panel_ids else f"panel_{r + 1:02d}_{c + 1:02d}"

                slot = PanelSlot(
                    panel_id=panel_id,
                    reading_order=reading_idx,
                    rect=snapped,
                    is_full_bleed=False,
                    is_intentional_overlap=False,
                    z_index=0,
                )
                panels.append(slot)
                reading_idx += 1

        # Sort panels by reading_order
        panels.sort(key=lambda p: p.reading_order)
        order_ids = [p.panel_id for p in panels]

        result = CanvasLayoutResult(
            canvas_id=f"canvas_grid_{uuid.uuid4().hex[:8]}",
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
