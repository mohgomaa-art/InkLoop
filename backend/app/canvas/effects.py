"""
E7: Effects & Motion Engine.
Generates deterministic visual effects: speed lines, action arcs,
impact bursts, focus blur, glow, and environmental manga effects.
"""
from io import BytesIO
import hashlib
import math
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter

from app.contracts.geometry import Rect, Point, BlendMode
from app.contracts.artifacts import AssetType
from app.contracts.engine import EffectsMotionParams, EffectsMotionOutput
from app.storage.registry import AssetRegistry


class EffectsMotionEngine:
    """Specialist Effects & Motion Engine (E7)."""

    def generate_effect(
        self,
        params: EffectsMotionParams,
        asset_registry: Optional[AssetRegistry] = None,
        project_id: str = "default_project",
    ) -> EffectsMotionOutput:
        """
        Renders a deterministic manga effect layer inside the panel boundary,
        applying intensity, direction, and focal point geometry.
        """
        rect = params.target_panel_rect
        w = max(10, int(rect.width))
        h = max(10, int(rect.height))

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        focal = params.focal_point or Point(x=rect.x + rect.width / 2, y=rect.y + rect.height / 2)
        fx = max(0, min(w, int(focal.x - rect.x)))
        fy = max(0, min(h, int(focal.y - rect.y)))

        category = params.effect_category.lower()

        if "speed_lines" in category or "action" in category:
            # Radial / directional speed lines emanating toward or from focal point
            num_lines = int(30 * max(0.2, min(params.intensity, 3.0)))
            for i in range(num_lines):
                angle = (i * (360.0 / num_lines) + params.direction_deg) * (math.pi / 180.0)
                # Outer perimeter point
                diag = math.hypot(w, h)
                x2 = int(fx + math.cos(angle) * diag)
                y2 = int(fy + math.sin(angle) * diag)
                # Inner clearance around focal point
                inner_r = 40.0
                x1 = int(fx + math.cos(angle) * inner_r)
                y1 = int(fy + math.sin(angle) * inner_r)
                draw.line([(x1, y1), (x2, y2)], fill=(20, 20, 20, int(180 * min(params.intensity, 1.0))), width=2)

        elif "impact" in category:
            # Impact star burst
            spikes = 16
            max_r = min(w, h) * 0.45 * min(params.intensity, 2.0)
            poly_pts = []
            for i in range(spikes * 2):
                r = max_r if i % 2 == 0 else max_r * 0.4
                ang = (i * (math.pi / spikes))
                poly_pts.append((int(fx + math.cos(ang) * r), int(fy + math.sin(ang) * r)))
            draw.polygon(poly_pts, outline=(15, 15, 15, 230), fill=(255, 255, 255, 120))

        elif "glow" in category or "bloom" in category:
            # Center radial glow
            glow_r = int(min(w, h) * 0.3 * params.intensity)
            draw.ellipse([fx - glow_r, fy - glow_r, fx + glow_r, fy + glow_r], fill=(255, 255, 255, 160))
            img = img.filter(ImageFilter.GaussianBlur(radius=8))

        elif "weather" in category or "rain" in category:
            # Slanted rain streaks
            rad = math.radians(params.direction_deg or 75)
            dx = math.cos(rad) * 25
            dy = math.sin(rad) * 25
            for y_step in range(0, h, 20):
                for x_step in range(0, w, 25):
                    draw.line([(x_step, y_step), (x_step + dx, y_step + dy)], fill=(180, 180, 200, 150), width=1)

        else:
            # Generic directional motion blur bars
            bar_height = max(2, int(4 * params.intensity))
            for y in range(0, h, int(15 / max(0.5, params.intensity))):
                draw.line([(0, y), (w, y)], fill=(30, 30, 30, 120), width=bar_height)

        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        artifact_id = f"effect_{hashlib.sha256(png_bytes).hexdigest()[:12]}"

        if asset_registry:
            asset = asset_registry.ingest_bytes(
                png_bytes,
                f"{artifact_id}.png",
                project_id=project_id,
                asset_type=AssetType.GENERIC_ARTIFACT,
                name=f"Effect layer {params.effect_category}",
                extra_metadata={
                    "effect_category": params.effect_category,
                    "intensity": params.intensity,
                    "direction_deg": params.direction_deg,
                    "blend_mode": params.blend_mode.value,
                },
            )
            artifact_id = asset.asset_id

        return EffectsMotionOutput(
            effect_layer_artifact_id=artifact_id,
            effect_bounds=rect,
            blend_mode=params.blend_mode,
        )
