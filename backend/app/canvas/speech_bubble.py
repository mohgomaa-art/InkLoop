"""
E6: Expressive Speech Bubble Engine.
Generates parametric SVG vector geometry, dynamic tails, manga screentone halftone shadows,
radial speedline accents, and headless raster composites for all comic & manga narrative styles.
"""
from io import BytesIO
import hashlib
import math
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image, ImageDraw

from app.contracts.geometry import Rect, Point
from app.contracts.artifacts import AssetType
from app.contracts.engine import SpeechBubbleParams, SpeechBubbleOutput
from app.storage.registry import AssetRegistry
from app.canvas.bubble_models import (
    BubbleShape,
    TailType,
    BubbleAccent,
    BubbleVectorGeometry,
    BubbleStyleRecommendation,
)
from app.canvas.bubble_stylist import recommend_bubble_style


class SpeechBubbleEngine:
    """Specialist Expressive Speech Bubble Placement and Vector Rendering Engine (E6)."""

    def generate_vector_geometry(
        self,
        bounds: Rect,
        shape: BubbleShape = BubbleShape.OVAL,
        tail_type: TailType = TailType.SMOOTH_POINTER,
        tail_target: Optional[Point] = None,
        secondary_tail_target: Optional[Point] = None,
        accent: BubbleAccent = BubbleAccent.NONE,
        inverted_dark_mode: bool = False,
        padding_x: float = 24.0,
        padding_y: float = 18.0,
        organic_seed: Optional[str] = None,
    ) -> BubbleVectorGeometry:
        """
        Computes accurate SVG path strings for bubble outline, tail, shadow, and accents.
        Defensively handles degenerate dimensions and boundary invariants.
        """
        # Clamp dimensions against degenerate inputs
        w = max(40.0, float(bounds.width))
        h = max(30.0, float(bounds.height))
        x = float(bounds.x)
        y = float(bounds.y)
        cx = x + w / 2.0
        cy = y + h / 2.0
        rx = w / 2.0
        ry = h / 2.0

        inner_text_rect = Rect(
            x=x + padding_x,
            y=y + padding_y,
            width=max(10.0, w - (padding_x * 2)),
            height=max(10.0, h - (padding_y * 2)),
        )

        # 1. Generate Main Bubble Path
        bubble_path = self._build_bubble_path(shape, x, y, w, h, cx, cy, rx, ry, organic_seed)

        # 2. Determine Tail Target Tip
        if tail_target is None:
            # Default downwards pointer
            tail_tip = Point(x=cx - rx * 0.3, y=y + h + 45.0)
        else:
            tail_tip = Point(x=float(tail_target.x), y=float(tail_target.y))

        # 3. Generate Tail Path & Chain Circles
        tail_path: Optional[str] = None
        tail_chain_circles: List[Tuple[float, float, float]] = []

        if tail_type != TailType.NONE:
            tail_path, tail_chain_circles = self._build_tail_geometry(
                tail_type, cx, cy, rx, ry, x, y, w, h, tail_tip
            )

        # 4. Generate Halftone Shadow Path (Offset down-right)
        shadow_path = self._build_bubble_path(shape, x + 8.0, y + 10.0, w, h, cx + 8.0, cy + 10.0, rx, ry, organic_seed)

        # 4b. Secondary Tail for DUAL_POINTER
        secondary_tail_path: Optional[str] = None
        if tail_type == TailType.DUAL_POINTER:
            if secondary_tail_target is not None:
                sec_tip = Point(x=float(secondary_tail_target.x), y=float(secondary_tail_target.y))
            else:
                sec_tip = Point(x=cx + (cx - tail_tip.x) * 0.85, y=tail_tip.y)
            sec_path, _ = self._build_tail_geometry(TailType.SMOOTH_POINTER, cx, cy, rx, ry, x, y, w, h, sec_tip)
            secondary_tail_path = sec_path

        # 4c. Double Stroke Path for DOUBLE_BORDER_IMPACT
        double_stroke_path: Optional[str] = None
        if shape == BubbleShape.DOUBLE_BORDER_IMPACT:
            double_stroke_path = self._build_bubble_path(shape, x + 6.0, y + 6.0, max(20.0, w - 12.0), max(20.0, h - 12.0), cx, cy, rx - 6.0, ry - 6.0)

        # 4d. 3D Ribbon Fold Paths for FOLDED_RIBBON_3D
        ribbon_fold_paths: List[str] = []
        if shape == BubbleShape.FOLDED_RIBBON_3D:
            ribbon_fold_paths = self._build_ribbon_folds(x, y, w, h)

        # 5. Generate Accents (Speedline Needles, Sparkles, Sweat drops, Anger Cross, Shock Marks, Hearts, Electric)
        accent_paths = self._build_accent_paths(shape, accent, x, y, w, h, cx, cy, rx, ry)

        return BubbleVectorGeometry(
            bubble_path=bubble_path,
            tail_path=tail_path,
            secondary_tail_path=secondary_tail_path,
            double_stroke_path=double_stroke_path,
            shadow_path=shadow_path,
            accent_paths=accent_paths,
            ribbon_fold_paths=ribbon_fold_paths,
            tail_chain_circles=tail_chain_circles,
            bounds=Rect(x=x, y=y, width=w, height=h),
            inner_text_rect=inner_text_rect,
            tail_tip=tail_tip,
        )

    def _build_bubble_path(
        self,
        shape: BubbleShape,
        x: float,
        y: float,
        w: float,
        h: float,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        organic_seed: Optional[str] = None,
    ) -> str:
        """Constructs closed SVG path data for each expressive shape."""
        # A. Classic Oval
        if shape == BubbleShape.OVAL:
            if organic_seed:
                return self._build_organic_oval_path(cx, cy, rx, ry, organic_seed)
            kappa = 0.55228475
            dx = rx * kappa
            dy = ry * kappa
            return (f"M {cx:.1f} {y:.1f} C {cx + dx:.1f} {y:.1f} {x + w:.1f} {cy - dy:.1f} {x + w:.1f} {cy:.1f} "
                    f"C {x + w:.1f} {cy + dy:.1f} {cx + dx:.1f} {y + h:.1f} {cx:.1f} {y + h:.1f} "
                    f"C {cx - dx:.1f} {y + h:.1f} {x:.1f} {cy + dy:.1f} {x:.1f} {cy:.1f} "
                    f"C {x:.1f} {cy - dy:.1f} {cx - dx:.1f} {y:.1f} {cx:.1f} {y:.1f} Z")

        # B. Rounded Rectangle
        if shape == BubbleShape.ROUNDED_RECTANGLE:
            rad = min(22.0, w / 4.0, h / 4.0)
            return (
                f"M {x + rad:.1f} {y:.1f} "
                f"H {x + w - rad:.1f} "
                f"A {rad:.1f} {rad:.1f} 0 0 1 {x + w:.1f} {y + rad:.1f} "
                f"V {y + h - rad:.1f} "
                f"A {rad:.1f} {rad:.1f} 0 0 1 {x + w - rad:.1f} {y + h:.1f} "
                f"H {x + rad:.1f} "
                f"A {rad:.1f} {rad:.1f} 0 0 1 {x:.1f} {y + h - rad:.1f} "
                f"V {y + rad:.1f} "
                f"A {rad:.1f} {rad:.1f} 0 0 1 {x + rad:.1f} {y:.1f} Z"
            )

        # C. Thought Cloud (Multi-lobed cumulus arcs)
        if shape == BubbleShape.THOUGHT_CLOUD:
            num_lobes = 10
            pts: List[Tuple[float, float]] = []
            for i in range(num_lobes):
                angle = (2.0 * math.pi * i) / num_lobes
                px = cx + rx * math.cos(angle)
                py = cy + ry * math.sin(angle)
                pts.append((px, py))

            path_segs = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
            lobe_r = min(rx, ry) * 0.42
            for i in range(num_lobes):
                next_pt = pts[(i + 1) % num_lobes]
                path_segs.append(f"A {lobe_r:.1f} {lobe_r:.1f} 0 0 1 {next_pt[0]:.1f} {next_pt[1]:.1f}")
            path_segs.append("Z")
            return " ".join(path_segs)

        # D. Shout Starburst (Jagged multi-point action polygon)
        if shape == BubbleShape.SHOUT_BURST:
            num_peaks = 16
            poly_pts: List[str] = []
            for i in range(num_peaks * 2):
                angle = (math.pi * i) / num_peaks
                is_peak = (i % 2 == 1)
                scale = 1.18 if is_peak else 0.84
                px = cx + rx * math.cos(angle) * scale
                py = cy + ry * math.sin(angle) * scale
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # E. Explosive Blast (Exaggerated deep starburst)
        if shape == BubbleShape.EXPLOSIVE_BLAST:
            num_spikes = 14
            poly_pts = []
            for i in range(num_spikes * 2):
                angle = (math.pi * i) / num_spikes
                is_peak = (i % 2 == 1)
                # Vary spike lengths dynamically
                peak_factor = 1.28 + 0.15 * math.sin(i * 1.7)
                scale = peak_factor if is_peak else 0.72
                px = cx + rx * math.cos(angle) * scale
                py = cy + ry * math.sin(angle) * scale
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # F. Fear / Cold Tremble (Jittering, teeth-chattering perimeter)
        if shape == BubbleShape.FEAR_TREMBLE:
            num_steps = 36
            poly_pts = []
            for i in range(num_steps):
                angle = (2.0 * math.pi * i) / num_steps
                jitter = 1.0 + 0.06 * math.sin(angle * 12.0) + 0.04 * math.cos(angle * 7.0)
                px = cx + rx * math.cos(angle) * jitter
                py = cy + ry * math.sin(angle) * jitter
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # G. Affection Heart (Cardioid shape)
        if shape == BubbleShape.AFFECTION_HEART:
            top_y = y + h * 0.2
            bot_y = y + h
            return (
                f"M {cx:.1f} {bot_y:.1f} "
                f"C {x - rx * 0.1:.1f} {cy + ry * 0.4:.1f} {x:.1f} {y + ry * 0.2:.1f} {x + rx * 0.5:.1f} {y:.1f} "
                f"C {cx - rx * 0.1:.1f} {y:.1f} {cx:.1f} {top_y - 8:.1f} {cx:.1f} {top_y:.1f} "
                f"C {cx:.1f} {top_y - 8:.1f} {cx + rx * 0.1:.1f} {y:.1f} {x + w - rx * 0.5:.1f} {y:.1f} "
                f"C {x + w:.1f} {y + ry * 0.2:.1f} {x + w + rx * 0.1:.1f} {cy + ry * 0.4:.1f} {cx:.1f} {bot_y:.1f} Z"
            )

        # H. Slime / Surprise Splat (Viscous dripping blob)
        if shape == BubbleShape.SPLAT_SURPRISE:
            num_lobes = 12
            poly_pts = []
            for i in range(num_lobes):
                angle = (2.0 * math.pi * i) / num_lobes
                # Add bulging drip lobes
                drip = 1.0 + 0.22 * math.sin(angle * 4.0) + (0.18 if (i in (3, 6, 9)) else 0.0)
                px = cx + rx * math.cos(angle) * drip
                py = cy + ry * math.sin(angle) * drip
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # I. Electric Robotic Chamfer (45° beveled tech octagon)
        if shape == BubbleShape.ELECTRIC_ROBOTIC:
            cut = min(18.0, w / 5.0, h / 5.0)
            return (
                f"M {x + cut:.1f} {y:.1f} "
                f"L {x + w - cut:.1f} {y:.1f} "
                f"L {x + w:.1f} {y + cut:.1f} "
                f"L {x + w:.1f} {y + h - cut:.1f} "
                f"L {x + w - cut:.1f} {y + h:.1f} "
                f"L {x + cut:.1f} {y + h:.1f} "
                f"L {x:.1f} {y + h - cut:.1f} "
                f"L {x:.1f} {y + cut:.1f} Z"
            )

        # J. Tilted Banner (Folded parallelogram narration banner)
        if shape == BubbleShape.TILTED_BANNER:
            skew = min(20.0, w * 0.08)
            notch = 12.0
            return (
                f"M {x + skew:.1f} {y:.1f} "
                f"L {x + w:.1f} {y:.1f} "
                f"L {x + w - skew:.1f} {y + h:.1f} "
                f"L {x:.1f} {y + h:.1f} Z"
            )

        # K. Connected Lobes / Double Speaker
        if shape == BubbleShape.CONNECTED_LOBES:
            sub_w = w * 0.62
            return (
                f"M {x + sub_w / 2:.1f} {y:.1f} "
                f"H {x + sub_w:.1f} "
                f"A {sub_w / 2:.1f} {h / 2.5:.1f} 0 0 1 {x + w:.1f} {cy:.1f} "
                f"A {sub_w / 2:.1f} {h / 2.5:.1f} 0 0 1 {x + w - sub_w / 2:.1f} {y + h:.1f} "
                f"H {x + sub_w / 2:.1f} "
                f"A {sub_w / 2:.1f} {h / 2.5:.1f} 0 0 1 {x:.1f} {cy:.1f} "
                f"A {sub_w / 2:.1f} {h / 2.5:.1f} 0 0 1 {x + sub_w / 2:.1f} {y:.1f} Z"
            )

        # L. Radio Broadcast Zigzag (Walkie-talkie / Telecom electrical teeth)
        if shape == BubbleShape.RADIO_BROADCAST_ZIGZAG:
            pts = []
            tooth = 8.0
            steps_x = max(4, int(w / 18.0))
            for i in range(steps_x):
                x0 = x + (i * w / steps_x)
                x1 = x + ((i + 0.5) * w / steps_x)
                pts.append(f"{'M' if i == 0 else 'L'} {x0:.1f} {y:.1f}")
                pts.append(f"L {x1:.1f} {y - tooth:.1f}")
            steps_y = max(3, int(h / 18.0))
            for i in range(steps_y):
                y0 = y + (i * h / steps_y)
                y1 = y + ((i + 0.5) * h / steps_y)
                pts.append(f"L {x + w:.1f} {y0:.1f}")
                pts.append(f"L {x + w + tooth:.1f} {y1:.1f}")
            for i in range(steps_x):
                x0 = x + w - (i * w / steps_x)
                x1 = x + w - ((i + 0.5) * w / steps_x)
                pts.append(f"L {x0:.1f} {y + h:.1f}")
                pts.append(f"L {x1:.1f} {y + h + tooth:.1f}")
            for i in range(steps_y):
                y0 = y + h - (i * h / steps_y)
                y1 = y + h - ((i + 0.5) * h / steps_y)
                pts.append(f"L {x:.1f} {y0:.1f}")
                pts.append(f"L {x - tooth:.1f} {y1:.1f}")
            pts.append("Z")
            return " ".join(pts)

        # M. 3D Folded Parchment Ribbon
        if shape == BubbleShape.FOLDED_RIBBON_3D:
            wing_w = min(28.0, w * 0.15)
            drop_y = 6.0
            bx0 = x + wing_w
            bx1 = x + w - wing_w
            by0 = y
            by1 = y + h - drop_y
            return f"M {bx0:.1f} {by0:.1f} L {bx1:.1f} {by0:.1f} L {bx1:.1f} {by1:.1f} L {bx0:.1f} {by1:.1f} Z"

        # N. Dark Aura Ghost (Rising sinister tendrils)
        if shape == BubbleShape.DARK_AURA_GHOST:
            num_spikes = 20
            poly_pts = []
            for i in range(num_spikes):
                ang = (2.0 * math.pi * i) / num_spikes
                is_upper = math.sin(ang) < 0
                tendril = 1.0 + (0.28 * abs(math.sin(ang * 5.0)) if is_upper else 0.08 * math.sin(ang * 3.0))
                px = cx + rx * math.cos(ang) * tendril
                py = cy + ry * math.sin(ang) * tendril
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # O. Icicle Frost (Hanging sharp icicle spikes)
        if shape == BubbleShape.ICICLE_FROST:
            num_icicles = max(5, int(w / 28.0))
            pts = [f"M {x:.1f} {y:.1f}", f"L {x + w:.1f} {y:.1f}", f"L {x + w:.1f} {y + h * 0.65:.1f}"]
            for i in range(num_icicles):
                seg_w = w / num_icicles
                p_base_r = x + w - (i * seg_w)
                p_tip_x = p_base_r - (seg_w / 2.0)
                icicle_len = h * (0.80 + 0.35 * math.sin(i * 1.9))
                p_tip_y = y + icicle_len
                p_base_l = p_base_r - seg_w
                pts.append(f"L {p_tip_x:.1f} {p_tip_y:.1f}")
                pts.append(f"L {p_base_l:.1f} {y + h * 0.65:.1f}")
            pts.append(f"L {x:.1f} {y:.1f} Z")
            return " ".join(pts)

        # P. Soft Pillowy Whisper Cloud
        if shape == BubbleShape.WHISPER_CLOUD_SOFT:
            num_lobes = 18
            pts = []
            for i in range(num_lobes):
                ang = (2.0 * math.pi * i) / num_lobes
                pts.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang)))
            segs = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
            lobe_r = min(rx, ry) * 0.24
            for i in range(num_lobes):
                next_pt = pts[(i + 1) % num_lobes]
                segs.append(f"A {lobe_r:.1f} {lobe_r:.1f} 0 0 1 {next_pt[0]:.1f} {next_pt[1]:.1f}")
            segs.append("Z")
            return " ".join(segs)

        # Q. Double Border Impact (Outer rounded polygon)
        if shape in (BubbleShape.DOUBLE_BORDER_IMPACT, BubbleShape.HEAVY_WEIGHT_EMPHASIS):
            rad = min(22.0, w / 4.0, h / 4.0)
            return (
                f"M {x + rad:.1f} {y:.1f} H {x + w - rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + w:.1f} {y + rad:.1f} "
                f"V {y + h - rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + w - rad:.1f} {y + h:.1f} "
                f"H {x + rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x:.1f} {y + h - rad:.1f} "
                f"V {y + rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + rad:.1f} {y:.1f} Z"
            )

        # R. Sad Droplet Tear (Curving into bulbous rounded bottom)
        if shape == BubbleShape.DROPLET_TEAR_SAD:
            return (
                f"M {cx:.1f} {y:.1f} "
                f"C {x + w * 0.85:.1f} {cy:.1f} {x + w:.1f} {y + h * 0.75:.1f} {cx + rx * 0.6:.1f} {y + h:.1f} "
                f"C {cx:.1f} {y + h + 4:.1f} {cx - rx * 0.6:.1f} {y + h:.1f} {x:.1f} {y + h * 0.75:.1f} "
                f"C {x:.1f} {cy:.1f} {cx:.1f} {y:.1f} {cx:.1f} {y:.1f} Z"
            )

        # S. Digital CRT Glitch (Pixelated stepped block)
        if shape == BubbleShape.GLITCH_DIGITAL_CRT:
            step = 10.0
            return (
                f"M {x + step:.1f} {y:.1f} H {x + w - step:.1f} "
                f"V {y + step:.1f} H {x + w:.1f} "
                f"V {y + h - step:.1f} H {x + w - step:.1f} "
                f"V {y + h:.1f} H {x + step:.1f} "
                f"V {y + h - step:.1f} H {x:.1f} "
                f"V {y + step:.1f} H {x + step:.1f} Z"
            )

        # T. Scalloped Shojo Floral Flower
        if shape == BubbleShape.SCALLOPED_FLOWER:
            num_petals = 14
            pts = []
            for i in range(num_petals):
                ang = (2.0 * math.pi * i) / num_petals
                pts.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang)))
            segs = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
            pr = min(rx, ry) * 0.32
            for i in range(num_petals):
                next_pt = pts[(i + 1) % num_petals]
                segs.append(f"A {pr:.1f} {pr:.1f} 0 0 1 {next_pt[0]:.1f} {next_pt[1]:.1f}")
            segs.append("Z")
            return " ".join(segs)

        # U. Spiky Ring Scream (24 extreme needles)
        if shape == BubbleShape.SPIKY_RING_SCREAM:
            num_thorns = 24
            poly_pts = []
            for i in range(num_thorns * 2):
                ang = (math.pi * i) / num_thorns
                is_spike = (i % 2 == 1)
                factor = 1.35 + 0.20 * math.sin(i * 2.3) if is_spike else 0.78
                px = cx + rx * math.cos(ang) * factor
                py = cy + ry * math.sin(ang) * factor
                poly_pts.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            poly_pts.append("Z")
            return " ".join(poly_pts)

        # Fallback Rectangle
        return f"M {x:.1f} {y:.1f} H {x + w:.1f} V {y + h:.1f} H {x:.1f} Z"

    @staticmethod
    def _build_organic_oval_path(cx: float, cy: float, rx: float, ry: float, seed: str) -> str:
        """Stable, low-amplitude hand-ink variation without a provider call."""
        points = []
        for index in range(16):
            digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
            noise = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
            angle = (2.0 * math.pi * index) / 16.0
            radius = 1.0 + (noise - 0.5) * 0.035
            points.append((cx + rx * radius * math.cos(angle), cy + ry * radius * math.sin(angle)))
        parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
        for index, point in enumerate(points):
            previous = points[(index - 1) % len(points)]
            following = points[(index + 1) % len(points)]
            after = points[(index + 2) % len(points)]
            c1 = (point[0] + (following[0] - previous[0]) / 6.0, point[1] + (following[1] - previous[1]) / 6.0)
            c2 = (following[0] - (after[0] - point[0]) / 6.0, following[1] - (after[1] - point[1]) / 6.0)
            parts.append(f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {following[0]:.1f} {following[1]:.1f}")
        return " ".join(parts) + " Z"

    def _build_ribbon_folds(self, x: float, y: float, w: float, h: float) -> List[str]:
        """Builds 3D side swallowtail wings and under-fold shadow triangles for FOLDED_RIBBON_3D."""
        wing_w = min(28.0, w * 0.15)
        drop_y = 6.0
        fold_y = 10.0
        notch_d = min(14.0, wing_w * 0.6)

        # Left wing (behind front banner)
        lw_top = y + drop_y
        lw_bot = y + h
        lw_left = x
        lw_right = x + wing_w
        left_wing = f"M {lw_right:.1f} {lw_top:.1f} L {lw_left:.1f} {lw_top:.1f} L {lw_left + notch_d:.1f} {(lw_top + lw_bot) / 2:.1f} L {lw_left:.1f} {lw_bot:.1f} L {lw_right:.1f} {lw_bot:.1f} Z"

        # Left under-fold shadow triangle
        left_fold = f"M {lw_right:.1f} {y + h - drop_y:.1f} L {lw_right:.1f} {lw_bot:.1f} L {lw_right + 8:.1f} {y + h - drop_y:.1f} Z"

        # Right wing (behind front banner)
        rw_top = y + drop_y
        rw_bot = y + h
        rw_left = x + w - wing_w
        rw_right = x + w
        right_wing = f"M {rw_left:.1f} {rw_top:.1f} L {rw_right:.1f} {rw_top:.1f} L {rw_right - notch_d:.1f} {(rw_top + rw_bot) / 2:.1f} L {rw_right:.1f} {rw_bot:.1f} L {rw_left:.1f} {rw_bot:.1f} Z"

        # Right under-fold shadow triangle
        right_fold = f"M {rw_left:.1f} {y + h - drop_y:.1f} L {rw_left:.1f} {rw_bot:.1f} L {rw_left - 8:.1f} {y + h - drop_y:.1f} Z"

        return [left_wing, left_fold, right_wing, right_fold]

    def _build_tail_geometry(
        self,
        tail_type: TailType,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        x: float,
        y: float,
        w: float,
        h: float,
        tip: Point,
    ) -> Tuple[Optional[str], List[Tuple[float, float, float]]]:
        """Calculates tail path or bubble chain connecting bubble boundary to tip."""
        dx = tip.x - cx
        dy = tip.y - cy
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            dx, dy = 0.0, 1.0
            dist = 1.0

        ux = dx / dist
        uy = dy / dist

        # Exact ray/ellipse intersection, pulled inward so the body fill hides
        # the tail root and the final silhouette has no seam.
        boundary_scale = 1.0 / math.sqrt((ux / max(rx, 1e-6)) ** 2 + (uy / max(ry, 1e-6)) ** 2)
        bx = cx + ux * boundary_scale * 0.82
        by = cy + uy * boundary_scale * 0.82

        # Tangent perpendicular vector
        tx = -uy
        ty = ux
        base_w = 12.0

        p1_x = bx + tx * base_w
        p1_y = by + ty * base_w
        p2_x = bx - tx * base_w
        p2_y = by - ty * base_w

        # 1. Thought Bubble Chain
        if tail_type == TailType.BUBBLE_CHAIN:
            circles = []
            steps = [(0.25, 11.0), (0.55, 7.5), (0.85, 4.5)]
            for frac, rad in steps:
                px = bx + (tip.x - bx) * frac
                py = by + (tip.y - by) * frac
                circles.append((px, py, rad))
            return None, circles

        # 2. Lightning Bolt (Zigzag robotic/shout tail)
        if tail_type == TailType.LIGHTNING_BOLT:
            kink1_x = bx + (tip.x - bx) * 0.35 + tx * 16.0
            kink1_y = by + (tip.y - by) * 0.35 + ty * 16.0
            kink2_x = bx + (tip.x - bx) * 0.7 - tx * 12.0
            kink2_y = by + (tip.y - by) * 0.7 - ty * 12.0
            return (
                f"M {p1_x:.1f} {p1_y:.1f} "
                f"L {kink1_x:.1f} {kink1_y:.1f} "
                f"L {kink2_x:.1f} {kink2_y:.1f} "
                f"L {tip.x:.1f} {tip.y:.1f} "
                f"L {kink2_x + tx * 4:.1f} {kink2_y + ty * 4:.1f} "
                f"L {p2_x:.1f} {p2_y:.1f} Z",
                [],
            )

        # 3. Whisper Dashed (Delicate straight horn)
        if tail_type == TailType.WHISPER_DASHED:
            return (
                f"M {p1_x:.1f} {p1_y:.1f} "
                f"L {tip.x:.1f} {tip.y:.1f} "
                f"L {p2_x:.1f} {p2_y:.1f} Z",
                [],
            )

        # 4. Off-Screen Pointer (Extends straight with an arrowhead notch)
        if tail_type == TailType.OFF_SCREEN_POINTER:
            arrow_w = 12.0
            return (
                f"M {p1_x:.1f} {p1_y:.1f} L {tip.x + tx * arrow_w:.1f} {tip.y + ty * arrow_w:.1f} "
                f"L {tip.x:.1f} {tip.y:.1f} "
                f"L {tip.x - tx * arrow_w:.1f} {tip.y - ty * arrow_w:.1f} L {p2_x:.1f} {p2_y:.1f} Z",
                [],
            )

        # 5. Curved Hook Tail (Sweeping sickle-shaped dynamic hook)
        if tail_type == TailType.CURVED_HOOK_TAIL:
            hook_ctrl1_x = bx + (tip.x - bx) * 0.3 + tx * 28.0
            hook_ctrl1_y = by + (tip.y - by) * 0.3 + ty * 28.0
            hook_ctrl2_x = bx + (tip.x - bx) * 0.8 - tx * 14.0
            hook_ctrl2_y = by + (tip.y - by) * 0.8 - ty * 14.0
            return (
                f"M {p1_x:.1f} {p1_y:.1f} "
                f"C {hook_ctrl1_x:.1f} {hook_ctrl1_y:.1f} {hook_ctrl2_x:.1f} {hook_ctrl2_y:.1f} {tip.x:.1f} {tip.y:.1f} "
                f"Q {bx + (tip.x - bx) * 0.5:.1f} {by + (tip.y - by) * 0.5:.1f} {p2_x:.1f} {p2_y:.1f} Z",
                [],
            )

        # 6. Zigzag Antenna (Right-angled transmission pulse tail)
        if tail_type == TailType.ZIGZAG_ANTENNA:
            mid_x = (bx + tip.x) / 2.0
            mid_y = (by + tip.y) / 2.0
            return (
                f"M {bx:.1f} {by:.1f} L {mid_x:.1f} {by:.1f} L {mid_x:.1f} {tip.y:.1f} L {tip.x:.1f} {tip.y:.1f}",
                [(tip.x, tip.y, 5.0)],
            )

        # 7. Smooth Pointer Horn / Dual Pointer (Default comic horn)
        ctrl_x = bx + (tip.x - bx) * 0.45 + tx * 8.0
        ctrl_y = by + (tip.y - by) * 0.45 + ty * 8.0
        return (
            f"M {p1_x:.1f} {p1_y:.1f} "
            f"Q {ctrl_x:.1f} {ctrl_y:.1f} {tip.x:.1f} {tip.y:.1f} "
            f"Q {bx:.1f} {by:.1f} {p2_x:.1f} {p2_y:.1f} Z",
            [],
        )

    def _build_accent_paths(
        self,
        shape: BubbleShape,
        accent: BubbleAccent,
        x: float,
        y: float,
        w: float,
        h: float,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
    ) -> List[str]:
        """Builds action needle accents, sparkles, or sweat drops."""
        accents = []
        if shape in (BubbleShape.EXPLOSIVE_BLAST, BubbleShape.SPEEDLINE_AURA):
            # Radiating speedline needle bursts around perimeter
            num_needles = 8
            for i in range(num_needles):
                ang = (2.0 * math.pi * i) / num_needles
                n_start_x = cx + rx * math.cos(ang) * 1.35
                n_start_y = cy + ry * math.sin(ang) * 1.35
                n_end_x = cx + rx * math.cos(ang) * 1.75
                n_end_y = cy + ry * math.sin(ang) * 1.75
                accents.append(f"M {n_start_x:.1f} {n_start_y:.1f} L {n_end_x:.1f} {n_end_y:.1f}")

        if shape == BubbleShape.AFFECTION_HEART:
            # Sparkle 4-point stars near top-right
            sp_x = x + w + 12.0
            sp_y = y - 8.0
            accents.append(
                f"M {sp_x:.1f} {sp_y - 10:.1f} Q {sp_x:.1f} {sp_y:.1f} {sp_x + 10:.1f} {sp_y:.1f} "
                f"Q {sp_x:.1f} {sp_y:.1f} {sp_x:.1f} {sp_y + 10:.1f} "
                f"Q {sp_x:.1f} {sp_y:.1f} {sp_x - 10:.1f} {sp_y:.1f} "
                f"Q {sp_x:.1f} {sp_y:.1f} {sp_x:.1f} {sp_y - 10:.1f} Z"
            )

        if shape == BubbleShape.FEAR_TREMBLE or accent == BubbleAccent.SWEAT_DROP:
            # Sweat drop on upper right
            sw_x = x + w + 10.0
            sw_y = y + 10.0
            accents.append(
                f"M {sw_x:.1f} {sw_y - 12:.1f} "
                f"Q {sw_x + 7:.1f} {sw_y:.1f} {sw_x:.1f} {sw_y + 8:.1f} "
                f"Q {sw_x - 7:.1f} {sw_y:.1f} {sw_x:.1f} {sw_y - 12:.1f} Z"
            )

        # Anime Anger Vein Cross 💢
        if accent == BubbleAccent.ANGER_VEIN_CROSS:
            vx = x + w + 8.0
            vy = y - 4.0
            arm = 8.0
            accents.append(
                f"M {vx - arm:.1f} {vy - arm * 0.3:.1f} Q {vx:.1f} {vy:.1f} {vx - arm * 0.3:.1f} {vy - arm:.1f} "
                f"M {vx + arm * 0.3:.1f} {vy - arm:.1f} Q {vx:.1f} {vy:.1f} {vx + arm:.1f} {vy - arm * 0.3:.1f} "
                f"M {vx + arm:.1f} {vy + arm * 0.3:.1f} Q {vx:.1f} {vy:.1f} {vx + arm * 0.3:.1f} {vy + arm:.1f} "
                f"M {vx - arm * 0.3:.1f} {vy + arm:.1f} Q {vx:.1f} {vy:.1f} {vx - arm:.1f} {vy + arm * 0.3:.1f}"
            )

        # Impact Shock Marks //
        if accent == BubbleAccent.SHOCK_MARKS:
            sx = x + w + 6.0
            sy = y + 12.0
            accents.append(f"M {sx:.1f} {sy:.1f} L {sx + 14:.1f} {sy - 12:.1f}")
            accents.append(f"M {sx + 8:.1f} {sy + 4:.1f} L {sx + 22:.1f} {sy - 8:.1f}")

        # Romantic Heart Flutter
        if accent == BubbleAccent.HEART_FLUTTER:
            hx = x + w + 10.0
            hy = y + 6.0
            accents.append(
                f"M {hx:.1f} {hy + 8:.1f} C {hx - 8:.1f} {hy + 2:.1f} {hx - 6:.1f} {hy - 4:.1f} {hx:.1f} {hy - 2:.1f} "
                f"C {hx + 6:.1f} {hy - 4:.1f} {hx + 8:.1f} {hy + 2:.1f} {hx:.1f} {hy + 8:.1f} Z"
            )

        # Electric Sparks ⚡
        if accent == BubbleAccent.ELECTRIC_SPARKS:
            ex = x - 12.0
            ey = y + h * 0.3
            accents.append(f"M {ex:.1f} {ey:.1f} L {ex + 6:.1f} {ey + 8:.1f} L {ex + 2:.1f} {ey + 9:.1f} L {ex + 8:.1f} {ey + 18:.1f}")

        # Dizziness Swirl 🌀
        if accent == BubbleAccent.DIZZINESS_SWIRL:
            dz_x = x + w + 10.0
            dz_y = y + h * 0.5
            accents.append(
                f"M {dz_x:.1f} {dz_y:.1f} "
                f"A 4 4 0 0 1 {dz_x + 8:.1f} {dz_y:.1f} "
                f"A 8 8 0 0 1 {dz_x - 8:.1f} {dz_y:.1f} "
                f"A 12 12 0 0 1 {dz_x + 12:.1f} {dz_y:.1f}"
            )

        return accents

    def place_speech_bubble(
        self,
        params: SpeechBubbleParams,
        asset_registry: Optional[AssetRegistry] = None,
        project_id: str = "default_project",
    ) -> SpeechBubbleOutput:
        """
        E6 Engine Entrypoint:
        Calculates bubble dimensions enclosing measured text bounds + padding.
        Positions bubble within panel slot avoiding outer margins, calculates tail,
        generates vector geometry, and renders raster PNG artifact for headless export.
        """
        pad_x = params.padding_px.get("x", 24.0)
        pad_y = params.padding_px.get("y", 18.0)

        bubble_w = max(40.0, params.measured_text_bounds.width + (pad_x * 2))
        bubble_h = max(30.0, params.measured_text_bounds.height + (pad_y * 2))

        slot = params.panel_slot_rect
        margin = 12.0

        # Place at top-center of panel slot by default
        target_x = slot.x + max(margin, (slot.width - bubble_w) / 2)
        target_y = slot.y + margin

        # Check collision with panel bounds
        collision_detected = False
        if target_x + bubble_w > slot.x + slot.width or target_y + bubble_h > slot.y + slot.height:
            collision_detected = True
            target_x = max(slot.x + margin, min(target_x, slot.x + slot.width - bubble_w - margin))
            target_y = max(slot.y + margin, min(target_y, slot.y + slot.height - bubble_h - margin))

        bubble_bounds = Rect(x=target_x, y=target_y, width=bubble_w, height=bubble_h)

        # Parse shape enum safely
        raw_shape = str(params.bubble_shape or "rounded_rectangle").lower()
        matched_shape = BubbleShape.ROUNDED_RECTANGLE
        for s in BubbleShape:
            if s.value in raw_shape or raw_shape in s.value:
                matched_shape = s
                break

        # Generate procedural vector geometry
        geo = self.generate_vector_geometry(
            bounds=bubble_bounds,
            shape=matched_shape,
            tail_target=params.tail_target,
            padding_x=pad_x,
            padding_y=pad_y,
        )

        # Render high-resolution raster fallback via Pillow
        canvas_w = int(max(slot.width, bubble_w + 60))
        canvas_h = int(max(slot.height, bubble_h + 60))
        img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        bx = int(target_x - slot.x + 15)
        by = int(target_y - slot.y + 15)
        bw = int(bubble_w)
        bh = int(bubble_h)

        # Rasterize bubble outline
        if matched_shape == BubbleShape.OVAL:
            draw.ellipse([bx, by, bx + bw, by + bh], fill="#FFFFFF", outline="#111111", width=3)
        elif matched_shape == BubbleShape.SHOUT_BURST or matched_shape == BubbleShape.EXPLOSIVE_BLAST:
            pts = []
            num_pts = 24
            for i in range(num_pts):
                ang = (2.0 * math.pi * i) / num_pts
                sc = 1.15 if (i % 2 == 1) else 0.85
                pts.append((bx + bw / 2 + (bw / 2) * math.cos(ang) * sc, by + bh / 2 + (bh / 2) * math.sin(ang) * sc))
            draw.polygon(pts, fill="#FFFFFF", outline="#111111")
        else:
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=18, fill="#FFFFFF", outline="#111111", width=3)

        # Rasterize tail if present
        if geo.tail_tip:
            tx = int(geo.tail_tip.x - slot.x + 15)
            ty = int(geo.tail_tip.y - slot.y + 15)
            draw.polygon([(bx + bw // 2 - 10, by + bh - 2), (bx + bw // 2 + 10, by + bh - 2), (tx, ty)], fill="#FFFFFF", outline="#111111")

        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        artifact_id = f"bubble_{hashlib.sha256(png_bytes).hexdigest()[:12]}"

        if asset_registry:
            asset = asset_registry.ingest_bytes(
                png_bytes,
                f"{artifact_id}.png",
                project_id=project_id,
                asset_type=AssetType.GENERIC_ARTIFACT,
                name=f"Speech bubble for {params.text_block_artifact_id}",
                extra_metadata={
                    "shape": matched_shape.value,
                    "bubble_bounds": bubble_bounds.model_dump(),
                    "collision_detected": collision_detected,
                    "svg_path": geo.bubble_path,
                },
            )
            artifact_id = asset.asset_id

        return SpeechBubbleOutput(
            bubble_layer_artifact_id=artifact_id,
            bubble_bounds=bubble_bounds,
            tail_anchor=geo.tail_tip,
            collision_detected=collision_detected,
        )

    def place_speech_bubble_for_script_block(
        self,
        script_block: Any,
        panel_slot_rect: Rect,
        typography_engine: Any,
        asset_registry: Optional[AssetRegistry] = None,
        project_id: str = "default_project",
        tail_target: Optional[Point] = None,
        reading_direction: str = "rtl",
        font_family: Optional[str] = None,
        font_size_pt: float = 16.0,
    ) -> Dict[str, Any]:
        """
        Connects an E4 ScriptBlock to E5 typography shaping/measurement and E6 bubble placement.
        Returns a dictionary containing the SpeechBubbleOutput, TypographyOutput, and BubbleVectorGeometry.
        """
        delivery_obj = getattr(script_block, "delivery", None)
        delivery = getattr(delivery_obj, "value", str(delivery_obj or "")).lower()
        block_kind_obj = getattr(script_block, "block_kind", None)
        block_kind = getattr(block_kind_obj, "value", str(block_kind_obj or "dialogue")).lower()
        sfx_cat_obj = getattr(script_block, "sfx_category", None)
        sfx_category = getattr(sfx_cat_obj, "value", str(sfx_cat_obj or "")).lower()

        carrier = "speech_bubble"
        if "thought" in delivery or block_kind == "monologue":
            carrier = "thought_bubble"
        elif "caption" in block_kind:
            carrier = "caption_box"

        recommended_style = recommend_bubble_style(
            emotional_intent=delivery or block_kind,
            delivery=delivery,
            carrier=carrier,
            sfx_category=sfx_category if sfx_category else None,
        )

        max_text_width = max(60.0, panel_slot_rect.width * 0.70)
        typo_output = typography_engine.render_text_block_to_layer(
            script_block=script_block,
            max_width_px=max_text_width,
            font_family=font_family,
            font_size_pt=font_size_pt,
            asset_registry=asset_registry,
            project_id=project_id,
        )

        pad_x = 22.0
        pad_y = 16.0
        bubble_w = max(40.0, typo_output.measured_bounds.width + (pad_x * 2))
        bubble_h = max(30.0, typo_output.measured_bounds.height + (pad_y * 2))

        margin = 14.0
        if reading_direction.lower() == "rtl":
            target_x = panel_slot_rect.x + panel_slot_rect.width - bubble_w - margin
        else:
            target_x = panel_slot_rect.x + margin
        target_y = panel_slot_rect.y + margin

        if tail_target is None:
            tx = target_x + (bubble_w * 0.3 if reading_direction.lower() == "rtl" else bubble_w * 0.7)
            ty = panel_slot_rect.y + min(panel_slot_rect.height * 0.75, target_y + bubble_h + 50.0)
            tail_target = Point(x=tx, y=ty)

        bubble_params = SpeechBubbleParams(
            text_block_artifact_id=getattr(script_block, "block_id", "blk_direct"),
            lettering_layer_artifact_id=typo_output.lettering_layer_artifact_id,
            measured_text_bounds=typo_output.measured_bounds,
            panel_slot_rect=panel_slot_rect,
            bubble_shape=recommended_style.shape.value,
            tail_target=tail_target,
            padding_px={"x": pad_x, "y": pad_y},
        )

        bubble_output = self.place_speech_bubble(bubble_params, asset_registry=asset_registry, project_id=project_id)

        vector_geo = self.generate_vector_geometry(
            bounds=bubble_output.bubble_bounds,
            shape=recommended_style.shape,
            tail_type=recommended_style.tail_type,
            tail_target=tail_target,
            accent=recommended_style.accent,
            padding_x=pad_x,
            padding_y=pad_y,
        )

        return {
            "speech_bubble_output": bubble_output,
            "typography_output": typo_output,
            "bubble_vector_geometry": vector_geo,
            "recommended_style": recommended_style,
        }
