"""
InkLoop Canvas Generation Engine (E2) - Raster Structural Preview Generator.
Renders empty structural panels, bleed/trim/safe guides, and reading badges using Pillow.
Enforces strict memory allocation limits before buffer creation.
"""
import io
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from app.canvas.models import CanvasLayoutResult
from app.canvas.errors import AllocationLimitExceededError

MAX_RASTER_WIDTH: int = 10_000
MAX_RASTER_HEIGHT: int = 50_000
MAX_RASTER_PIXELS: int = 50_000_000

class RasterPreviewConfig:
    """Settings for raster structural preview generation."""
    def __init__(
        self,
        scale: float = 1.0,
        show_bleed: bool = True,
        show_trim: bool = True,
        show_safe_area: bool = True,
        show_badges: bool = True,
        stroke_width: int = 3,
        background_color: str = "#FFFFFF",
        panel_color: str = "#FAFAFA",
        panel_border_color: str = "#111111",
    ):
        self.scale = max(0.05, min(2.0, scale))
        self.show_bleed = show_bleed
        self.show_trim = show_trim
        self.show_safe_area = show_safe_area
        self.show_badges = show_badges
        self.stroke_width = max(1, stroke_width)
        self.background_color = background_color
        self.panel_color = panel_color
        self.panel_border_color = panel_border_color

class RasterPreviewGenerator:
    """Generates structural raster PNG/image previews matching canonical layout geometry."""

    @classmethod
    def render_image(
        cls,
        result: CanvasLayoutResult,
        config: Optional[RasterPreviewConfig] = None
    ) -> Image.Image:
        cfg = config or RasterPreviewConfig()
        scale = cfg.scale

        b_box = result.bleed_box
        t_box = result.trim_box

        # Base dimensions
        if cfg.show_bleed:
            raw_w = b_box.width
            raw_h = b_box.height
            offset_x = -b_box.x
            offset_y = -b_box.y
        else:
            raw_w = t_box.width
            raw_h = t_box.height
            offset_x = 0.0
            offset_y = 0.0

        target_w = int(round(raw_w * scale))
        target_h = int(round(raw_h * scale))

        # Memory allocation guard
        if target_w > MAX_RASTER_WIDTH or target_h > MAX_RASTER_HEIGHT:
            raise AllocationLimitExceededError(
                f"Raster preview dimensions ({target_w}x{target_h} px) exceed safe raster limit ({MAX_RASTER_WIDTH}x{MAX_RASTER_HEIGHT} px)"
            )

        total_px = target_w * target_h
        if total_px > MAX_RASTER_PIXELS:
            raise AllocationLimitExceededError(
                f"Raster preview pixel count ({total_px} px) exceeds safe limit ({MAX_RASTER_PIXELS} px)"
            )

        # Create base image
        img = Image.new("RGBA", (target_w, target_h), cfg.background_color)
        draw = ImageDraw.Draw(img)

        # Coordinate mapper: maps PAGE coordinates (with offset) to scaled image pixels
        def map_x(x: float) -> float:
            return (x + offset_x) * scale

        def map_y(y: float) -> float:
            return (y + offset_y) * scale

        # 1. Bleed box guide
        if cfg.show_bleed and not result.canvas_spec.bleed.is_zero:
            draw.rectangle(
                [map_x(b_box.left), map_y(b_box.top), map_x(b_box.right) - 1, map_y(b_box.bottom) - 1],
                outline="#DC3545",
                width=max(1, int(1.5 * scale))
            )

        # 2. Trim boundary
        if cfg.show_trim:
            draw.rectangle(
                [map_x(0.0), map_y(0.0), map_x(t_box.width) - 1, map_y(t_box.height) - 1],
                outline="#212529",
                width=max(1, int(2.0 * scale))
            )

        # 3. Safe area guide
        if cfg.show_safe_area:
            s = result.safe_area_box
            draw.rectangle(
                [map_x(s.left), map_y(s.top), map_x(s.right) - 1, map_y(s.bottom) - 1],
                outline="#0D6EFD",
                width=max(1, int(1.0 * scale))
            )

        # 4. Panel slots
        sw = max(1, int(cfg.stroke_width * scale))
        for slot in result.panel_slots:
            if slot.has_polygon and slot.polygon:
                pts = [(map_x(p.x), map_y(p.y)) for p in slot.polygon]
                draw.polygon(pts, fill=cfg.panel_color, outline=cfg.panel_border_color, width=sw)
            else:
                r = slot.rect
                draw.rectangle(
                    [map_x(r.left), map_y(r.top), map_x(r.right) - 1, map_y(r.bottom) - 1],
                    fill=cfg.panel_color,
                    outline=cfg.panel_border_color,
                    width=sw
                )

            # Panel badges (reading order number)
            if cfg.show_badges:
                r = slot.rect
                radius = int(14.0 * scale)
                cx = int(map_x(r.right) - radius - int(8.0 * scale))
                cy = int(map_y(r.top) + radius + int(8.0 * scale))
                if radius > 4:
                    draw.ellipse(
                        [cx - radius, cy - radius, cx + radius, cy + radius],
                        fill="#0D6EFD",
                        outline="#FFFFFF",
                        width=1
                    )
                    # Simple reading number
                    draw.text(
                        (cx, cy),
                        str(slot.reading_order),
                        fill="#FFFFFF",
                        anchor="mm"
                    )

        return img

    @classmethod
    def render_png_bytes(
        cls,
        result: CanvasLayoutResult,
        config: Optional[RasterPreviewConfig] = None
    ) -> bytes:
        """Renders raster preview and encodes as PNG byte buffer."""
        img = cls.render_image(result, config)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
