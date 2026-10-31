"""Unified closed-path vector geometry for comic speech balloons (B5).

Produces ONE continuous closed SVG path (union) combining the bubble body and tail,
rendered with a single stroke. Eliminates intersecting interior seams.
Includes deterministic seeded noise (seeded by bubble_id) without Math.random.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.contracts.geometry import Point, Rect


def seeded_noise(seed: str, index: int) -> float:
    """Deterministic pseudo-random float in [0.0, 1.0) seeded by string and index."""
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
    int_val = int.from_bytes(digest[:4], "big")
    return int_val / 0xFFFFFFFF


@dataclass(frozen=True)
class UnifiedVectorBubble:
    """Vector representation ready for SVG rendering and canvas export."""
    unified_path: str
    chain_circles: List[Tuple[float, float, float]] = field(default_factory=list)  # (cx, cy, r)
    stroke_dash: str = ""
    accent_paths: List[str] = field(default_factory=list)
    tail_tip: Optional[Point] = None
    inner_text_rect: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))


class BubbleVectorBuilder:
    """Builds unified closed-path vector geometry for all 8 canonical bubble types."""

    def build_bubble_vector(
        self,
        bounds: Rect,
        type_id: str = "speech.normal",
        shape: str = "oval",
        tail_type: str = "smooth_pointer",
        tail_target: Optional[Point] = None,
        bubble_id: str = "default_bubble",
        style_seed: str = "style_default",
        accent: str = "none",
        pad_x: float = 16.0,
        pad_y: float = 12.0,
    ) -> UnifiedVectorBubble:
        """Construct a single unified SVG path for body + tail."""
        w = max(40.0, float(bounds.width))
        h = max(30.0, float(bounds.height))
        x = float(bounds.x)
        y = float(bounds.y)
        cx = x + w / 2.0
        cy = y + h / 2.0
        rx = w / 2.0
        ry = h / 2.0

        seed = f"{bubble_id}:{style_seed}"

        inner_text_rect = Rect(
            x=x + pad_x,
            y=y + pad_y,
            width=max(10.0, w - pad_x * 2.0),
            height=max(10.0, h - pad_y * 2.0),
        )

        stroke_dash = "5 4" if (type_id == "speech.whisper" or tail_type == "whisper_dashed" or shape == "whisper_cloud_soft") else ""

        # Types with NO tail (narration, caption, sfx)
        if tail_type == "none" or type_id in {"narration.box", "caption.timeplace", "sfx.text"} or tail_target is None:
            body_path = self._build_body_only_path(shape, x, y, w, h, cx, cy, rx, ry, seed)
            return UnifiedVectorBubble(
                unified_path=body_path,
                chain_circles=[],
                stroke_dash=stroke_dash,
                tail_tip=None,
                inner_text_rect=inner_text_rect,
            )

        # Thought cloud: cloud body + dot chain circles
        if tail_type == "bubble_chain" or type_id == "thought.cloud" or shape == "thought_cloud":
            body_path = self._build_thought_cloud_path(cx, cy, rx, ry, seed)
            chain_circles = self._build_thought_chain_circles(cx, cy, rx, ry, tail_target)
            return UnifiedVectorBubble(
                unified_path=body_path,
                chain_circles=chain_circles,
                stroke_dash=stroke_dash,
                tail_tip=tail_target,
                inner_text_rect=inner_text_rect,
            )

        # Shout burst: spiky outline + lightning / spike tail
        if shape in {"shout_burst", "explosive_blast"} or type_id == "speech.shout":
            unified_path = self._build_unified_shout_burst(cx, cy, rx, ry, tail_target, seed)
            return UnifiedVectorBubble(
                unified_path=unified_path,
                chain_circles=[],
                stroke_dash=stroke_dash,
                tail_tip=tail_target,
                inner_text_rect=inner_text_rect,
            )

        # Standard oval or rounded rectangle with unified smooth pointer tail
        unified_path = self._build_unified_smooth_tail(
            shape=shape,
            x=x, y=y, w=w, h=h,
            cx=cx, cy=cy, rx=rx, ry=ry,
            tail_target=tail_target,
            seed=seed,
        )

        return UnifiedVectorBubble(
            unified_path=unified_path,
            chain_circles=[],
            stroke_dash=stroke_dash,
            tail_tip=tail_target,
            inner_text_rect=inner_text_rect,
        )

    def _build_unified_smooth_tail(
        self,
        shape: str,
        x: float, y: float, w: float, h: float,
        cx: float, cy: float, rx: float, ry: float,
        tail_target: Point,
        seed: str,
    ) -> str:
        """Create a single closed path tracing the tail out and in, and around the ellipse/rect."""
        tip_x = float(tail_target.x)
        tip_y = float(tail_target.y)

        dx = tip_x - cx
        dy = tip_y - cy
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            dx = 0.0
            dy = 1.0
            dist = 1.0

        ux = dx / dist
        uy = dy / dist

        # Angle on ellipse in radians
        theta_tip = math.atan2(uy * rx, ux * ry)

        # Base width along tangent: ~14px to 22px depending on bubble size
        base_w = min(22.0, max(12.0, min(w, h) * 0.16))
        # Angular half-width of the tail base
        delta_theta = math.asin(min(0.5, base_w / (2.0 * math.hypot(rx * math.cos(theta_tip), ry * math.sin(theta_tip)))))

        theta1 = theta_tip - delta_theta
        theta2 = theta_tip + delta_theta

        p1_x = cx + rx * math.cos(theta1)
        p1_y = cy + ry * math.sin(theta1)

        p2_x = cx + rx * math.cos(theta2)
        p2_y = cy + ry * math.sin(theta2)

        # Tangent vector for curved horn
        tx = -uy
        ty = ux
        ctrl1_x = p1_x + (tip_x - p1_x) * 0.45 + tx * 8.0
        ctrl1_y = p1_y + (tip_y - p1_y) * 0.45 + ty * 8.0
        ctrl2_x = p2_x + (tip_x - p2_x) * 0.45 - tx * 8.0
        ctrl2_y = p2_y + (tip_y - p2_y) * 0.45 - ty * 8.0

        # Construct single closed path:
        # Start at p1 -> curve to tip -> curve to p2 -> trace around ellipse to p1 -> Z
        d = [f"M {p1_x:.1f} {p1_y:.1f}"]
        # Curve 1: p1 to tip
        d.append(f"Q {ctrl1_x:.1f} {ctrl1_y:.1f} {tip_x:.1f} {tip_y:.1f}")
        # Curve 2: tip to p2
        d.append(f"Q {ctrl2_x:.1f} {ctrl2_y:.1f} {p2_x:.1f} {p2_y:.1f}")

        # Now trace the perimeter of the ellipse from theta2 all the way around to theta1
        num_arc_steps = 24
        # We need to sweep angle from theta2 to theta1 + 2*pi
        start_angle = theta2
        end_angle = theta1 + (2.0 * math.pi if theta1 < theta2 else 0.0)
        total_sweep = end_angle - start_angle

        for i in range(1, num_arc_steps + 1):
            ang = start_angle + (total_sweep * i) / num_arc_steps
            # Seeded subtle organic noise (0.015 variance)
            organic = 1.0 + (seeded_noise(seed, i) - 0.5) * 0.025
            pt_x = cx + rx * organic * math.cos(ang)
            pt_y = cy + ry * organic * math.sin(ang)
            d.append(f"L {pt_x:.1f} {pt_y:.1f}")

        d.append("Z")
        return " ".join(d)

    def _build_unified_shout_burst(
        self,
        cx: float, cy: float, rx: float, ry: float,
        tail_target: Point,
        seed: str,
    ) -> str:
        """Single closed path for a spiky burst bubble with one extended lightning pointer spike."""
        tip_x = float(tail_target.x)
        tip_y = float(tail_target.y)
        dx = tip_x - cx
        dy = tip_y - cy
        theta_tip = math.atan2(dy, dx)
        if theta_tip < 0:
            theta_tip += 2 * math.pi

        num_spikes = 16
        step_ang = (2 * math.pi) / num_spikes
        closest_spike_idx = int(round(theta_tip / step_ang)) % num_spikes

        pts: List[Tuple[float, float]] = []
        for i in range(num_spikes * 2):
            ang = (math.pi * i) / num_spikes
            is_peak = (i % 2 == 1)
            spike_idx = i // 2

            if is_peak and spike_idx == closest_spike_idx:
                # This spike extends all the way to the tail target!
                pts.append((tip_x, tip_y))
            else:
                scale = 1.22 if is_peak else 0.82
                jitter = 1.0 + (seeded_noise(seed, i) - 0.5) * 0.06
                px = cx + rx * math.cos(ang) * scale * jitter
                py = cy + ry * math.sin(ang) * scale * jitter
                pts.append((px, py))

        d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
        for p in pts[1:]:
            d.append(f"L {p[0]:.1f} {p[1]:.1f}")
        d.append("Z")
        return " ".join(d)

    def _build_thought_cloud_path(
        self,
        cx: float, cy: float, rx: float, ry: float,
        seed: str,
    ) -> str:
        """Closed cloud path with scalloped lobes and seeded organic variations."""
        num_lobes = 10
        pts: List[Tuple[float, float]] = []
        for i in range(num_lobes):
            ang = (2 * math.pi * i) / num_lobes
            organic = 1.0 + (seeded_noise(seed, i) - 0.5) * 0.08
            pts.append((cx + rx * organic * math.cos(ang), cy + ry * organic * math.sin(ang)))

        lobe_r = min(rx, ry) * 0.42
        d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
        for i in range(num_lobes):
            next_pt = pts[(i + 1) % num_lobes]
            d.append(f"A {lobe_r:.1f} {lobe_r:.1f} 0 0 1 {next_pt[0]:.1f} {next_pt[1]:.1f}")
        d.append("Z")
        return " ".join(d)

    def _build_thought_chain_circles(
        self,
        cx: float, cy: float, rx: float, ry: float,
        tail_target: Point,
    ) -> List[Tuple[float, float, float]]:
        """Circles decreasing in diameter toward the speaker."""
        tip_x = float(tail_target.x)
        tip_y = float(tail_target.y)
        dx = tip_x - cx
        dy = tip_y - cy
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return []

        ux = dx / dist
        uy = dy / dist
        bx = cx + ux * rx * 0.88
        by = cy + uy * ry * 0.88

        return [
            (bx + (tip_x - bx) * 0.28, by + (tip_y - by) * 0.28, 10.0),
            (bx + (tip_x - bx) * 0.58, by + (tip_y - by) * 0.58, 6.5),
            (bx + (tip_x - bx) * 0.86, by + (tip_y - by) * 0.86, 4.0),
        ]

    def _build_body_only_path(
        self,
        shape: str,
        x: float, y: float, w: float, h: float,
        cx: float, cy: float, rx: float, ry: float,
        seed: str,
    ) -> str:
        """Construct standard closed body path without tail."""
        if shape in {"rounded_rectangle", "narration_box", "caption"}:
            rad = min(16.0, min(w, h) * 0.25)
            return (
                f"M {x + rad:.1f} {y:.1f} "
                f"H {x + w - rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + w:.1f} {y + rad:.1f} "
                f"V {y + h - rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + w - rad:.1f} {y + h:.1f} "
                f"H {x + rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x:.1f} {y + h - rad:.1f} "
                f"V {y + rad:.1f} A {rad:.1f} {rad:.1f} 0 0 1 {x + rad:.1f} {y:.1f} Z"
            )

        if shape in {"thought_cloud", "whisper_cloud_soft"}:
            return self._build_thought_cloud_path(cx, cy, rx, ry, seed)

        if shape in {"shout_burst", "explosive_blast"}:
            num_spikes = 16
            d = []
            for i in range(num_spikes * 2):
                ang = (math.pi * i) / num_spikes
                sc = 1.18 if (i % 2 == 1) else 0.84
                jitter = 1.0 + (seeded_noise(seed, i) - 0.5) * 0.05
                px = cx + rx * math.cos(ang) * sc * jitter
                py = cy + ry * math.sin(ang) * sc * jitter
                d.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
            d.append("Z")
            return " ".join(d)

        # Standard oval with subtle seeded organic noise
        num_points = 24
        d = []
        for i in range(num_points):
            ang = (2 * math.pi * i) / num_points
            organic = 1.0 + (seeded_noise(seed, i) - 0.5) * 0.02
            px = cx + rx * organic * math.cos(ang)
            py = cy + ry * organic * math.sin(ang)
            d.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
        d.append("Z")
        return " ".join(d)
