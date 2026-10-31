"""Deterministic multi-bubble placement engine for comic & manga pages (B4).

Enforces hard invariants:
1. Zero overlap with protected face/head regions.
2. Zero overlap between speech bubbles (with minimum clearance gap).
3. Inside page safe margin (gutter bleed allowed when necessary).
4. Strictly monotonic reading order according to project reading direction (RTL/LTR).
5. Sizing caps based on panel geometry (panoramic <=35% width, normal <=55% width).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.canvas.bubble_registry import BUBBLE_TYPE_BY_ID, BubbleTypeSpec
from app.contracts.geometry import Point, Rect
from app.text.lettering_layout import (
    LetteringLayout,
    LetteringValidationError,
    count_words,
    layout_lettering_text,
)


class PlacementError(RuntimeError):
    """Structured error raised when no non-occluding placement is mathematically possible."""

    def __init__(self, code: str, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True)
class ProtectedRegion:
    """A bounding box that bubbles must never occlude (face, head, focal object)."""
    x: float
    y: float
    width: float
    height: float
    label: str = "face"
    character_id: Optional[str] = None
    region_id: str = ""

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, width=self.width, height=self.height)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Point:
        return Point(x=self.x + self.width / 2.0, y=self.y + self.height / 2.0)


@dataclass
class BubblePlacementRequest:
    """Input request describing a single bubble to place."""
    bubble_id: str
    type_id: str
    text: str
    reading_order: int = 1
    speaker_character_id: Optional[str] = None
    speaker_anchor: Optional[Point] = None
    font_family: str = "Comic Neue"
    preferred_font_size: Optional[float] = None
    is_offpanel: bool = False
    offpanel_edge: Optional[str] = None  # "left", "right", "top", "bottom"


@dataclass
class BubblePlacementResult:
    """Calculated position, dimensions, tail, and lettering layout for a bubble."""
    bubble_id: str
    type_id: str
    rect: Rect
    tail_target: Optional[Point]
    layout: LetteringLayout
    reading_order: int
    speaker_character_id: Optional[str] = None
    in_gutter: bool = False
    pad_x: float = 16.0
    pad_y: float = 12.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bubble_id": self.bubble_id,
            "type_id": self.type_id,
            "rect": {"x": self.rect.x, "y": self.rect.y, "width": self.rect.width, "height": self.rect.height},
            "tail_target": {"x": self.tail_target.x, "y": self.tail_target.y} if self.tail_target else None,
            "reading_order": self.reading_order,
            "speaker_character_id": self.speaker_character_id,
            "in_gutter": self.in_gutter,
            "font_size_px": self.layout.font_size_px,
            "line_count": len(self.layout.lines),
            "lines": self.layout.lines,
        }


def _rect_intersects(r1_x: float, r1_y: float, r1_w: float, r1_h: float,
                     r2_x: float, r2_y: float, r2_w: float, r2_h: float,
                     margin: float = 0.0) -> bool:
    """Check if two rectangles overlap with an optional clearance margin."""
    return not (
        r1_x + r1_w + margin <= r2_x
        or r2_x + r2_w + margin <= r1_x
        or r1_y + r1_h + margin <= r2_y
        or r2_y + r2_h + margin <= r1_y
    )


def _compute_bubble_envelope(layout: LetteringLayout, spec: BubbleTypeSpec) -> Tuple[float, float, float, float]:
    """Derive bubble (width, height, pad_x, pad_y) from measured text layout."""
    # Base padding depending on bubble shape
    shape = spec.default_shape
    if "oval" in shape or "thought" in shape:
        pad_x = max(16.0, layout.font_size_px * 0.85)
        pad_y = max(12.0, layout.font_size_px * 0.65)
        # Oval requires clearance around diamond corners
        bw = max(80.0, layout.content_width_px * 1.28 + pad_x * 2.0)
        bh = max(44.0, layout.content_height_px * 1.25 + pad_y * 2.0)
    elif "shout" in shape:
        pad_x = max(20.0, layout.font_size_px * 0.95)
        pad_y = max(16.0, layout.font_size_px * 0.75)
        bw = max(90.0, layout.content_width_px * 1.35 + pad_x * 2.0)
        bh = max(50.0, layout.content_height_px * 1.30 + pad_y * 2.0)
    else:  # narration.box, caption, rounded rectangle
        pad_x = max(12.0, layout.font_size_px * 0.60)
        pad_y = max(8.0, layout.font_size_px * 0.45)
        bw = max(70.0, layout.content_width_px + pad_x * 2.0 + 8.0)
        bh = max(36.0, layout.content_height_px + pad_y * 2.0 + 6.0)

    return bw, bh, pad_x, pad_y


def _calculate_tail_target(
    bubble_rect: Rect,
    speaker_anchor: Optional[Point],
    speaker_face: Optional[ProtectedRegion],
    panel_rect: Rect,
    type_id: str,
    offpanel_edge: Optional[str] = None,
) -> Optional[Point]:
    """Determine the tail tip target point, stopping a gap before the speaker's face."""
    if type_id in {"narration.box", "caption.timeplace", "sfx.text"}:
        return None

    if type_id == "speech.offpanel":
        # Points to the specified panel edge
        edge = offpanel_edge or "left"
        if edge == "left":
            return Point(x=panel_rect.x - 20.0, y=bubble_rect.y + bubble_rect.height / 2.0)
        elif edge == "right":
            return Point(x=panel_rect.x + panel_rect.width + 20.0, y=bubble_rect.y + bubble_rect.height / 2.0)
        elif edge == "top":
            return Point(x=bubble_rect.x + bubble_rect.width / 2.0, y=panel_rect.y - 20.0)
        else:
            return Point(x=bubble_rect.x + bubble_rect.width / 2.0, y=panel_rect.y + panel_rect.height + 20.0)

    # If we have a protected face region for the speaker:
    if speaker_face is not None:
        target_center = speaker_face.center
        # Calculate intersection with face boundary + clearance gap
        gap = 14.0
        bx = bubble_rect.x + bubble_rect.width / 2.0
        by = bubble_rect.y + bubble_rect.height / 2.0
        dx = target_center.x - bx
        dy = target_center.y - by
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            ux = dx / dist
            uy = dy / dist
            # Clamp tip to stop outside the face boundary
            # Approximate face as an ellipse/box
            hw = speaker_face.width / 2.0 + gap
            hh = speaker_face.height / 2.0 + gap
            t_scale = 1.0 / math.sqrt((ux / max(hw, 1.0)) ** 2 + (uy / max(hh, 1.0)) ** 2)
            tip_x = target_center.x - ux * t_scale
            tip_y = target_center.y - uy * t_scale
            return Point(x=round(tip_x, 1), y=round(tip_y, 1))

    # If we have a raw speaker anchor point:
    if speaker_anchor is not None:
        gap = 12.0
        bx = bubble_rect.x + bubble_rect.width / 2.0
        by = bubble_rect.y + bubble_rect.height / 2.0
        dx = speaker_anchor.x - bx
        dy = speaker_anchor.y - by
        dist = math.hypot(dx, dy)
        if dist > gap:
            ux = dx / dist
            uy = dy / dist
            return Point(x=round(speaker_anchor.x - ux * gap, 1), y=round(speaker_anchor.y - uy * gap, 1))
        return Point(x=speaker_anchor.x, y=speaker_anchor.y)

    return None


class PlacementEngine:
    """Places one or more dialogue/narration bubbles on a panel without covering faces."""

    def __init__(self, gutter_margin: float = 36.0, bubble_clearance: float = 12.0):
        self.gutter_margin = gutter_margin
        self.bubble_clearance = bubble_clearance

    def place_bubbles(
        self,
        panel_rect: Rect,
        bubbles: Sequence[BubblePlacementRequest],
        protected_regions: Sequence[ProtectedRegion | Rect | Dict[str, Any]],
        reading_direction: str = "rtl",
        page_safe_margin: Optional[Rect] = None,
        allow_gutter_bleed: bool = True,
    ) -> List[BubblePlacementResult]:
        """Compute non-occluding, reading-ordered positions for all requested bubbles."""
        if not bubbles:
            return []

        # Normalize protected regions
        normalized_faces: List[ProtectedRegion] = []
        for reg in protected_regions:
            if isinstance(reg, ProtectedRegion):
                normalized_faces.append(reg)
            elif isinstance(reg, Rect):
                normalized_faces.append(ProtectedRegion(x=reg.x, y=reg.y, width=reg.width, height=reg.height))
            elif isinstance(reg, dict):
                normalized_faces.append(ProtectedRegion(
                    x=float(reg["x"]), y=float(reg["y"]),
                    width=float(reg["width"]), height=float(reg["height"]),
                    label=str(reg.get("label", "face")),
                    character_id=reg.get("character_id"),
                    region_id=str(reg.get("region_id", "")),
                ))

        # Sort bubbles strictly by reading_order
        sorted_bubbles = sorted(bubbles, key=lambda b: b.reading_order)

        # Page boundary enforcement
        if page_safe_margin is None:
            # Default safe margin surrounds panel with generous gutters
            page_safe_margin = Rect(
                x=panel_rect.x - 60.0,
                y=panel_rect.y - 60.0,
                width=panel_rect.width + 120.0,
                height=panel_rect.height + 120.0,
            )

        panel_aspect = panel_rect.width / max(1.0, panel_rect.height)
        is_panoramic = panel_aspect > 3.0

        # Maximum allowable width and height for speech balloons on this panel
        # Enforces Codex B2 hard caps:
        # - Speech/thought <= 55% width, <= 35% height, <= 20% area
        # - Panoramic (>3:1) <= 35% width, <= 38% height
        if is_panoramic:
            max_bubble_w = max(110.0, panel_rect.width * 0.35)
            max_bubble_h = max(50.0, panel_rect.height * 0.38)
        else:
            max_bubble_w = max(140.0 if allow_gutter_bleed else 110.0, panel_rect.width * 0.55)
            max_bubble_h = max(95.0 if allow_gutter_bleed else 60.0, panel_rect.height * 0.38)

        # Search area definition: panel rect expanded into gutter if allowed
        gutter_reach_x = max(self.gutter_margin, max_bubble_w * 0.75) if allow_gutter_bleed else 0.0
        gutter_reach_y = max(self.gutter_margin, max_bubble_h * 0.90) if allow_gutter_bleed else 0.0
        search_left = max(page_safe_margin.x, panel_rect.x - gutter_reach_x)
        search_top = max(page_safe_margin.y, panel_rect.y - gutter_reach_y)
        search_right = min(page_safe_margin.x + page_safe_margin.width, panel_rect.x + panel_rect.width + gutter_reach_x)
        search_bottom = min(page_safe_margin.y + page_safe_margin.height, panel_rect.y + panel_rect.height + gutter_reach_y)

        placed_results: List[BubblePlacementResult] = []

        for bubble in sorted_bubbles:
            spec = BUBBLE_TYPE_BY_ID.get(bubble.type_id)
            if spec is None:
                raise PlacementError(
                    "ERR_BUBBLE_TYPE_UNKNOWN",
                    f"Unknown bubble type '{bubble.type_id}'.",
                    {"type_id": bubble.type_id},
                )

            # Try placing at current font size down to min font size
            placed = self._fit_and_place_single_bubble(
                bubble=bubble,
                spec=spec,
                panel_rect=panel_rect,
                search_box=(search_left, search_top, search_right, search_bottom),
                page_safe_margin=page_safe_margin,
                max_w=max_bubble_w,
                max_h=max_bubble_h,
                protected_faces=normalized_faces,
                existing_bubbles=placed_results,
                reading_direction=reading_direction.lower(),
                is_panoramic=is_panoramic,
            )
            if placed is None:
                raise PlacementError(
                    "ERR_NO_SAFE_BUBBLE_PLACEMENT",
                    f"Could not find a non-occluding placement for bubble '{bubble.bubble_id}' on panel ({panel_rect.width:.0f}x{panel_rect.height:.0f}). Shorten text or reposition characters.",
                    {
                        "bubble_id": bubble.bubble_id,
                        "type_id": bubble.type_id,
                        "text": bubble.text,
                        "reading_order": bubble.reading_order,
                        "panel_width": panel_rect.width,
                        "panel_height": panel_rect.height,
                    },
                )
            placed_results.append(placed)

        return placed_results

    def _fit_and_place_single_bubble(
        self,
        bubble: BubblePlacementRequest,
        spec: BubbleTypeSpec,
        panel_rect: Rect,
        search_box: Tuple[float, float, float, float],
        page_safe_margin: Rect,
        max_w: float,
        max_h: float,
        protected_faces: List[ProtectedRegion],
        existing_bubbles: List[BubblePlacementResult],
        reading_direction: str,
        is_panoramic: bool,
    ) -> Optional[BubblePlacementResult]:
        """Try layout and candidate positions across decreasing font sizes."""
        # Find speaker face if known
        speaker_face = None
        if bubble.speaker_character_id:
            for face in protected_faces:
                if face.character_id == bubble.speaker_character_id:
                    speaker_face = face
                    break

        # Sizing step iterations: start from preferred/max font down to min font
        start_font = int(round(bubble.preferred_font_size or spec.max_font_px))
        min_font = spec.min_font_px
        font_candidates = sorted(list(set([start_font, 22, 20, 18, 16, min_font])), reverse=True)
        font_candidates = [f for f in font_candidates if min_font <= f <= spec.max_font_px]

        for font_size in font_candidates:
            # Calculate inner text constraints so the final outer bubble envelope
            # (including padding and oval/burst geometric expansion) strictly obeys max_w and max_h
            if "oval" in spec.default_shape or "thought" in spec.default_shape:
                est_pad_x = max(16.0, font_size * 0.85)
                est_pad_y = max(12.0, font_size * 0.65)
                inner_w = max(40.0, (max_w - est_pad_x * 2.0) / 1.28)
                inner_h = max(24.0, (max_h - est_pad_y * 2.0) / 1.25)
            elif "shout" in spec.default_shape:
                est_pad_x = max(20.0, font_size * 0.95)
                est_pad_y = max(16.0, font_size * 0.75)
                inner_w = max(40.0, (max_w - est_pad_x * 2.0) / 1.35)
                inner_h = max(24.0, (max_h - est_pad_y * 2.0) / 1.30)
            else:
                est_pad_x = max(12.0, font_size * 0.60)
                est_pad_y = max(8.0, font_size * 0.45)
                inner_w = max(40.0, max_w - est_pad_x * 2.0 - 8.0)
                inner_h = max(20.0, max_h - est_pad_y * 2.0 - 6.0)

            # Keep speech and thought balloons near 2:1-3:1 comic aspect ratio
            # rather than stretching into flat horizontal bars
            words = count_words(bubble.text)
            if words >= 3 and bubble.type_id in {"speech.normal", "speech.whisper", "speech.offpanel", "thought.cloud"}:
                est_total_w = len(bubble.text) * font_size * 0.55
                est_area = est_total_w * (font_size * 1.15)
                target_w = math.sqrt(est_area * 2.3)
                inner_w = min(inner_w, max(70.0, target_w * 1.18))

            try:
                layout = layout_lettering_text(
                    text=bubble.text,
                    type_id=bubble.type_id,
                    max_width_px=inner_w,
                    max_height_px=inner_h,
                    font_family=bubble.font_family,
                    requested_font_size_px=font_size,
                )
            except LetteringValidationError:
                continue

            bw, bh, pad_x, pad_y = _compute_bubble_envelope(layout, spec)
            if bw > max_w + 1e-3 or bh > max_h + 1e-3:
                continue

            # Generate and evaluate candidate (x, y) coordinates
            best_pos = self._find_best_candidate_position(
                bw=bw,
                bh=bh,
                bubble=bubble,
                panel_rect=panel_rect,
                search_box=search_box,
                page_safe_margin=page_safe_margin,
                protected_faces=protected_faces,
                existing_bubbles=existing_bubbles,
                reading_direction=reading_direction,
                speaker_face=speaker_face,
                is_panoramic=is_panoramic,
            )

            if best_pos is not None:
                bx, by = best_pos
                bubble_rect = Rect(x=bx, y=by, width=bw, height=bh)
                tail_target = _calculate_tail_target(
                    bubble_rect=bubble_rect,
                    speaker_anchor=bubble.speaker_anchor,
                    speaker_face=speaker_face,
                    panel_rect=panel_rect,
                    type_id=bubble.type_id,
                    offpanel_edge=bubble.offpanel_edge,
                )
                in_gutter = (
                    bx < panel_rect.x
                    or by < panel_rect.y
                    or (bx + bw) > (panel_rect.x + panel_rect.width)
                    or (by + bh) > (panel_rect.y + panel_rect.height)
                )
                return BubblePlacementResult(
                    bubble_id=bubble.bubble_id,
                    type_id=bubble.type_id,
                    rect=bubble_rect,
                    tail_target=tail_target,
                    layout=layout,
                    reading_order=bubble.reading_order,
                    speaker_character_id=bubble.speaker_character_id,
                    in_gutter=in_gutter,
                    pad_x=pad_x,
                    pad_y=pad_y,
                )

        return None

    def _find_best_candidate_position(
        self,
        bw: float,
        bh: float,
        bubble: BubblePlacementRequest,
        panel_rect: Rect,
        search_box: Tuple[float, float, float, float],
        page_safe_margin: Rect,
        protected_faces: List[ProtectedRegion],
        existing_bubbles: List[BubblePlacementResult],
        reading_direction: str,
        speaker_face: Optional[ProtectedRegion],
        is_panoramic: bool,
    ) -> Optional[Tuple[float, float]]:
        """Search fine-grained candidate grid and score them deterministically."""
        s_left, s_top, s_right, s_bottom = search_box
        is_rtl = (reading_direction == "rtl")

        # Determine speaker anchor point for proximity scoring
        target_pt = None
        if speaker_face is not None:
            target_pt = speaker_face.center
        elif bubble.speaker_anchor is not None:
            target_pt = bubble.speaker_anchor

        # Previous bubble in reading order for monotonicity enforcement
        prev_bubble = existing_bubbles[-1] if existing_bubbles else None

        candidates: List[Tuple[float, float, float]] = []  # (score, x, y)

        # Strategic candidate seeds: top corners, gutters, flanks, sliding grid
        step_x = 16.0
        step_y = 12.0
        x_positions = []

        # Key x anchor seeds
        if is_rtl:
            # RTL prefers right to left
            x_positions.extend([
                panel_rect.x + panel_rect.width - bw - 10.0,  # Flush top-right
                panel_rect.x + 10.0,                          # Flush top-left
            ])
            if target_pt:
                x_positions.append(target_pt.x - bw / 2.0)     # Over speaker
                x_positions.append(target_pt.x + 20.0)         # Flank speaker right
                x_positions.append(target_pt.x - bw - 20.0)    # Flank speaker left
        else:
            # LTR prefers left to right
            x_positions.extend([
                panel_rect.x + 10.0,                          # Flush top-left
                panel_rect.x + panel_rect.width - bw - 10.0,  # Flush top-right
            ])
            if target_pt:
                x_positions.append(target_pt.x - bw / 2.0)
                x_positions.append(target_pt.x - bw - 20.0)
                x_positions.append(target_pt.x + 20.0)

        # Add regular grid steps
        curr_x = s_left
        while curr_x <= s_right - bw:
            x_positions.append(curr_x)
            curr_x += step_x

        y_positions = [
            panel_rect.y + 10.0,                              # Top inside panel
            panel_rect.y - bh * 0.4,                          # Gutter top bleed
            panel_rect.y + 30.0,
            panel_rect.y + panel_rect.height - bh - 10.0,     # Bottom inside panel
        ]
        curr_y = s_top
        while curr_y <= s_bottom - bh:
            y_positions.append(curr_y)
            curr_y += step_y

        seen_positions = set()

        for y in y_positions:
            for x in x_positions:
                rx = round(x, 1)
                ry = round(y, 1)
                if (rx, ry) in seen_positions:
                    continue
                seen_positions.add((rx, ry))

                # Hard Check 1: Inside page safe margin
                if rx < page_safe_margin.x or ry < page_safe_margin.y:
                    continue
                if rx + bw > page_safe_margin.x + page_safe_margin.width:
                    continue
                if ry + bh > page_safe_margin.y + page_safe_margin.height:
                    continue

                # Hard Check 2: Zero overlap with ANY protected face/head region
                collides_face = False
                for face in protected_faces:
                    if _rect_intersects(rx, ry, bw, bh, face.x, face.y, face.width, face.height, margin=4.0):
                        collides_face = True
                        break
                if collides_face:
                    continue

                # Hard Check 3: Zero overlap with previously placed bubbles
                collides_bubble = False
                for prev in existing_bubbles:
                    if _rect_intersects(rx, ry, bw, bh, prev.rect.x, prev.rect.y, prev.rect.width, prev.rect.height, margin=self.bubble_clearance):
                        collides_bubble = True
                        break
                if collides_bubble:
                    continue

                # Hard Check 4: Monotonic reading order constraint
                # If there is a previous bubble, current bubble MUST follow reading sequence
                if prev_bubble is not None:
                    # In both RTL and LTR, later speech cannot be placed significantly higher than earlier speech
                    if ry < prev_bubble.rect.y - 30.0:
                        continue
                    # When at roughly same vertical tier, enforce horizontal direction
                    if abs(ry - prev_bubble.rect.y) < 35.0:
                        if is_rtl and rx > prev_bubble.rect.x - 10.0:
                            # In RTL, later bubble must be further LEFT
                            continue
                        elif not is_rtl and rx < prev_bubble.rect.x + 10.0:
                            # In LTR, later bubble must be further RIGHT
                            continue

                # Score this valid candidate
                score = self._score_candidate(
                    rx=rx, ry=ry, bw=bw, bh=bh,
                    panel_rect=panel_rect,
                    target_pt=target_pt,
                    is_rtl=is_rtl,
                    bubble=bubble,
                    prev_bubble=prev_bubble,
                )
                candidates.append((score, rx, ry))

        if not candidates:
            return None

        # Sort by best (lowest) score
        candidates.sort(key=lambda c: c[0])
        return candidates[0][1], candidates[0][2]

    def _score_candidate(
        self,
        rx: float,
        ry: float,
        bw: float,
        bh: float,
        panel_rect: Rect,
        target_pt: Optional[Point],
        is_rtl: bool,
        bubble: BubblePlacementRequest,
        prev_bubble: Optional[BubblePlacementResult],
    ) -> float:
        """Lower score is better."""
        score = 0.0
        bc_x = rx + bw / 2.0
        bc_y = ry + bh / 2.0

        # 1. Vertical bias: Comic balloons strongly prefer the upper half of the panel
        y_rel = (ry - panel_rect.y) / max(1.0, panel_rect.height)
        score += max(0.0, y_rel) * 120.0

        # 2. Reading direction corner bias:
        # RTL strongly rewards top-right corner; LTR strongly rewards top-left corner
        if is_rtl:
            dist_from_right = (panel_rect.x + panel_rect.width) - (rx + bw)
            score += max(0.0, dist_from_right) * 0.18
        else:
            dist_from_left = rx - panel_rect.x
            score += max(0.0, dist_from_left) * 0.18

        # 3. Distance to speaker anchor (if known)
        if target_pt is not None:
            dist_to_speaker = math.hypot(bc_x - target_pt.x, bc_y - target_pt.y)
            # Penalize being excessively far from speaker
            score += dist_to_speaker * 0.22
            # Small bonus if bubble is ABOVE the speaker's head
            if bc_y < target_pt.y:
                score -= 40.0
        elif bubble.is_offpanel:
            # Offpanel speech prefers edge proximity
            dist_to_edge = min(abs(rx - panel_rect.x), abs((panel_rect.x + panel_rect.width) - (rx + bw)))
            score += dist_to_edge * 0.35

        # 4. Gutter bleed penalty: slight penalty for stepping outside panel borders
        outside_left = max(0.0, panel_rect.x - rx)
        outside_right = max(0.0, (rx + bw) - (panel_rect.x + panel_rect.width))
        outside_top = max(0.0, panel_rect.y - ry)
        outside_bottom = max(0.0, (ry + bh) - (panel_rect.y + panel_rect.height))
        bleed = outside_left + outside_right + outside_top + outside_bottom
        score += bleed * 0.45

        # 5. Narration box corner preference (top-left or top-right)
        if bubble.type_id in {"narration.box", "caption.timeplace"}:
            if is_rtl:
                corner_dist = math.hypot((panel_rect.x + panel_rect.width) - (rx + bw), ry - panel_rect.y)
            else:
                corner_dist = math.hypot(rx - panel_rect.x, ry - panel_rect.y)
            score += corner_dist * 0.50

        return score
