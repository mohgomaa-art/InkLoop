"""
InkLoop Canvas Generation Engine (E2) - Deterministic SVG Structural Preview Generator.
Produces valid, self-contained, byte-stable SVG previews with clean layer groups,
optional debug guides, panel numbers, and strict XML entity escaping.
Zero script fragments, zero event handlers, zero random IDs, zero timestamps.
"""
import re
import xml.sax.saxutils as saxutils
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.canvas.models import CanvasLayoutResult, ReadingDirection

class SVGPreviewConfig(BaseModel):
    """Configuration options for structural SVG canvas previews."""
    show_bleed: bool = Field(default=True, description="Render outer bleed guide line (dotted crimson)")
    show_trim: bool = Field(default=True, description="Render page trim boundary (solid dark gray)")
    show_safe_area: bool = Field(default=True, description="Render safe area margin guide (dashed royal blue)")
    show_usable_area: bool = Field(default=False, description="Render usable margin boundary (light green)")
    show_gutters: bool = Field(default=True, description="Render panel gutter spacing guides")
    show_panels: bool = Field(default=True, description="Render panel frame borders and fills")
    show_panel_badges: bool = Field(default=True, description="Render reading order numbers and panel IDs")
    show_reading_flow: bool = Field(default=False, description="Render connecting directional arrows between panels")
    stroke_width_px: float = Field(default=2.0, description="Base stroke thickness for panel borders")
    background_fill: str = Field(default="#FFFFFF", description="Canvas background fill color")
    panel_fill: str = Field(default="#FAFAFA", description="Panel slot background fill color")
    panel_stroke: str = Field(default="#111111", description="Panel border stroke color")

def escape_xml(text: str) -> str:
    """Escapes user text safely for XML element and attribute inclusion."""
    # Sanitize dangerous script or event handler injection attempts
    cleaned = re.sub(r"(?i)<\s*script[^>]*>.*?</\s*script\s*>", "", text)
    cleaned = re.sub(r"(?i)on\w+\s*=", "", cleaned)
    cleaned = re.sub(r"(?i)javascript:", "", cleaned)
    return saxutils.escape(cleaned, entities={'"': "&quot;", "'": "&apos;"})

class SVGPreviewGenerator:
    """Generates deterministic, byte-stable structural SVG representations from CanvasLayoutResult."""

    @classmethod
    def generate(cls, result: CanvasLayoutResult, config: Optional[SVGPreviewConfig] = None) -> str:
        cfg = config or SVGPreviewConfig()
        cs = result.canvas_spec

        # Determine SVG canvas viewBox covering bleed box with padding
        b_box = result.bleed_box
        t_box = result.trim_box

        # If bleed is present, viewBox spans bleed_box; otherwise trim_box
        view_min_x = b_box.x if cfg.show_bleed else 0.0
        view_min_y = b_box.y if cfg.show_bleed else 0.0
        view_w = b_box.width if cfg.show_bleed else cs.width_px
        view_h = b_box.height if cfg.show_bleed else cs.height_px

        lines: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{view_min_x:.1f} {view_min_y:.1f} {view_w:.1f} {view_h:.1f}" '
            f'width="{view_w:.1f}px" height="{view_h:.1f}px" '
            f'data-canvas-id="{escape_xml(result.canvas_id)}" '
            f'data-template-id="{escape_xml(result.template_id.value)}" '
            f'style="background-color: {escape_xml(cfg.background_fill)}; font-family: sans-serif;">'
        ]

        # 1. Definitions (markers for reading flow arrows)
        lines.append('  <defs>')
        lines.append('    <marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">')
        lines.append('      <path d="M 0 0 L 8 4 L 0 8 z" fill="#D9534F" />')
        lines.append('    </marker>')
        lines.append('  </defs>')

        # 2. Bleed guide layer
        if cfg.show_bleed and not cs.bleed.is_zero:
            lines.append('  <!-- Bleed Boundary Guide -->')
            lines.append('  <g id="guide-bleed">')
            lines.append(
                f'    <rect x="{b_box.x:.1f}" y="{b_box.y:.1f}" '
                f'width="{b_box.width:.1f}" height="{b_box.height:.1f}" '
                f'fill="none" stroke="#DC3545" stroke-width="1.5" stroke-dasharray="6,4" />'
            )
            lines.append(
                f'    <text x="{b_box.x + 8.0:.1f}" y="{b_box.y + 16.0:.1f}" '
                f'font-size="12px" fill="#DC3545" font-weight="bold">BLEED EDGE</text>'
            )
            lines.append('  </g>')

        # 3. Trim page boundary
        if cfg.show_trim:
            lines.append('  <!-- Page Trim Boundary -->')
            lines.append('  <g id="guide-trim">')
            lines.append(
                f'    <rect x="0.0" y="0.0" '
                f'width="{cs.width_px:.1f}" height="{cs.height_px:.1f}" '
                f'fill="none" stroke="#212529" stroke-width="2.0" />'
            )
            lines.append('  </g>')

        # 4. Safe area guide
        if cfg.show_safe_area:
            s_box = result.safe_area_box
            lines.append('  <!-- Safe Area Guide -->')
            lines.append('  <g id="guide-safe-area">')
            lines.append(
                f'    <rect x="{s_box.x:.1f}" y="{s_box.y:.1f}" '
                f'width="{s_box.width:.1f}" height="{s_box.height:.1f}" '
                f'fill="none" stroke="#0D6EFD" stroke-width="1.0" stroke-dasharray="4,4" />'
            )
            lines.append('  </g>')

        # 5. Usable margin box guide
        if cfg.show_usable_area:
            u_box = result.usable_box
            lines.append('  <!-- Usable Area Guide (Margins) -->')
            lines.append('  <g id="guide-usable">')
            lines.append(
                f'    <rect x="{u_box.x:.1f}" y="{u_box.y:.1f}" '
                f'width="{u_box.width:.1f}" height="{u_box.height:.1f}" '
                f'fill="none" stroke="#198754" stroke-width="1.0" stroke-dasharray="2,2" />'
            )
            lines.append('  </g>')

        # 6. Panel slots layer
        if cfg.show_panels:
            lines.append('  <!-- Panel Slots -->')
            lines.append('  <g id="panel-slots">')
            for slot in result.panel_slots:
                p_id = escape_xml(slot.panel_id)
                sw = cfg.stroke_width_px
                fill = escape_xml(cfg.panel_fill)
                stroke = escape_xml(cfg.panel_stroke)

                if slot.has_polygon and slot.polygon:
                    # Render as SVG polygon
                    pts_str = " ".join(f"{p.x:.1f},{p.y:.1f}" for p in slot.polygon)
                    lines.append(
                        f'    <polygon id="{p_id}" points="{pts_str}" '
                        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}" '
                        f'stroke-linejoin="round" />'
                    )
                else:
                    # Standard rectangle
                    r = slot.rect
                    lines.append(
                        f'    <rect id="{p_id}" '
                        f'x="{r.x:.1f}" y="{r.y:.1f}" width="{r.width:.1f}" height="{r.height:.1f}" '
                        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}" />'
                    )
            lines.append('  </g>')

        # 7. Panel Badges (Reading order and Panel ID)
        if cfg.show_panel_badges:
            lines.append('  <!-- Panel Reading Badges & Identification -->')
            lines.append('  <g id="panel-badges">')
            for slot in result.panel_slots:
                p_id = escape_xml(slot.panel_id)
                r = slot.rect

                # Top-right badge origin in panel space
                badge_radius = 16.0
                badge_cx = r.right - badge_radius - 8.0
                badge_cy = r.top + badge_radius + 8.0

                # Badge circle
                lines.append(
                    f'    <circle cx="{badge_cx:.1f}" cy="{badge_cy:.1f}" r="{badge_radius:.1f}" '
                    f'fill="#0D6EFD" />'
                )
                # Badge number
                lines.append(
                    f'    <text x="{badge_cx:.1f}" y="{badge_cy + 5.0:.1f}" '
                    f'font-size="14px" font-weight="bold" fill="#FFFFFF" text-anchor="middle">'
                    f'{slot.reading_order}</text>'
                )
                # Panel ID label
                lines.append(
                    f'    <text x="{r.x + 8.0:.1f}" y="{r.top + 20.0:.1f}" '
                    f'font-size="12px" fill="#495057" font-weight="bold">{p_id}</text>'
                )
                # Dimensions label
                lines.append(
                    f'    <text x="{r.x + 8.0:.1f}" y="{r.bottom - 8.0:.1f}" '
                    f'font-size="11px" fill="#6C757D">{r.width:.0f}x{r.height:.0f}px</text>'
                )
            lines.append('  </g>')

        # 8. Optional Reading Flow directional lines
        if cfg.show_reading_flow and len(result.panel_slots) > 1:
            lines.append('  <!-- Directional Reading Flow -->')
            lines.append('  <g id="reading-flow">')
            sorted_slots = sorted(result.panel_slots, key=lambda s: s.reading_order)
            for i in range(len(sorted_slots) - 1):
                p1 = sorted_slots[i].rect.center
                p2 = sorted_slots[i + 1].rect.center
                lines.append(
                    f'    <line x1="{p1.x:.1f}" y1="{p1.y:.1f}" x2="{p2.x:.1f}" y2="{p2.y:.1f}" '
                    f'stroke="#D9534F" stroke-width="2.5" stroke-dasharray="6,4" '
                    f'marker-end="url(#flow-arrow)" />'
                )
            lines.append('  </g>')

        lines.append('</svg>')
        return "\n".join(lines)
