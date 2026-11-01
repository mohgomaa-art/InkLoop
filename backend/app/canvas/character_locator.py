"""
InkLoop Character Locator & Non-Occluding Bubble Placement Engine.
Detects focal character/subject framing inside panel artwork and computes
optimal collision-free speech bubble positioning (above or under character,
avoiding facial occlusion) with accurate tail orientation.
"""
from typing import Optional, Tuple, Dict, Any, Union, List
from pathlib import Path
import io
import math
import numpy as np
from PIL import Image

from app.contracts.geometry import Rect, Point, Transform2D


def detect_panel_protected_regions(
    image_source: Optional[Union[bytes, Path, str]],
    panel_rect: Rect,
) -> Tuple[List[Any], List[Point]]:
    """
    Analyzes panel artwork for character faces/heads and returns:
    1. A list of ProtectedRegion objects to prevent bubble overlap with heads.
    2. A list of Point objects representing detected character speaker centers.
    """
    from app.canvas.placement_engine import ProtectedRegion

    if image_source is None:
        return [], []

    image_bytes: Optional[bytes] = None
    if isinstance(image_source, (str, Path)):
        p = Path(image_source)
        if p.is_file():
            image_bytes = p.read_bytes()
    elif isinstance(image_source, bytes):
        image_bytes = image_source

    if not image_bytes:
        return [], []

    try:
        import cv2

        bio = io.BytesIO(image_bytes)
        with Image.open(bio) as pil_img:
            img_w, img_h = pil_img.size
            rgb_arr = np.array(pil_img.convert("RGB"))

        gray = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2HSV)

        scale_x = panel_rect.width / max(1, img_w)
        scale_y = panel_rect.height / max(1, img_h)

        lower_skin = np.array([0, 25, 50], dtype=np.uint8)
        upper_skin = np.array([28, 220, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        clean_skin = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        clean_skin = cv2.morphologyEx(clean_skin, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(clean_skin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        protected_regions: List[ProtectedRegion] = []
        speaker_candidates: List[Point] = []

        min_area = 0.008 * img_w * img_h
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(c)

            # Skip small diagram cards / icons / background noise
            if bw < 0.04 * img_w or bh < 0.15 * img_h:
                continue

            # If wide torso/body contour, extract head from upper portion
            if bw > 0.25 * img_w:
                crop_skin = clean_skin[by:by + int(bh * 0.55), bx:bx + bw]
                pts = cv2.findNonZero(crop_skin)
                if pts is None:
                    continue
                sub_x, sub_y, sub_w, sub_h = cv2.boundingRect(pts)
                hx = bx + sub_x
                hy = by + sub_y
                hw = min(sub_w, int(img_w * 0.25))
                hh = min(sub_h, int(img_h * 0.40))
            else:
                hx, hy, hw, hh = bx, by, bw, bh

            # Reject featureless background clouds / computer screens:
            region_gray = gray[hy:hy + hh, hx:hx + hw]
            if region_gray.size > 0:
                dark_frac = np.mean(region_gray < 70)
                # If region is at top border (hy < 0.05*h) and has virtually no dark facial features, it's sky/monitor
                if hy < 0.05 * img_h and dark_frac < 0.12:
                    continue

            px = panel_rect.x + hx * scale_x
            py = panel_rect.y + hy * scale_y
            pw = hw * scale_x
            ph = hh * scale_y

            protected_regions.append(ProtectedRegion(x=px, y=py, width=pw, height=ph, label="face"))
            cx = panel_rect.x + (hx + hw / 2.0) * scale_x
            cy = panel_rect.y + (hy + hh / 2.0) * scale_y
            speaker_candidates.append(Point(x=cx, y=cy))

        if not protected_regions:
            focal = locate_character_in_panel(image_source, panel_rect, allow_fallback=False)
            if focal is not None:
                protected_regions.append(ProtectedRegion(x=focal.x, y=focal.y, width=focal.width, height=focal.height, label="subject"))
                speaker_candidates.append(focal.center)

        return protected_regions, speaker_candidates
    except Exception:
        return [], []


def locate_character_in_panel(
    image_source: Optional[Union[bytes, Path, str]],
    panel_rect: Rect,
    fit_mode: str = "cover",
    transform: Optional[Transform2D] = None,
    *,
    allow_fallback: bool = True,
) -> Optional[Rect]:
    """
    Locates the focal character / subject inside the panel image and maps
    its bounding box directly to PAGE COORDINATES within panel_rect.
    """
    if image_source is None:
        return _fallback_character_rect(panel_rect) if allow_fallback else None

    # 1. Load image data
    image_bytes: Optional[bytes] = None
    if isinstance(image_source, (str, Path)):
        p = Path(image_source)
        if p.is_file():
            image_bytes = p.read_bytes()
    elif isinstance(image_source, bytes):
        image_bytes = image_source

    if not image_bytes:
        return _fallback_character_rect(panel_rect) if allow_fallback else None

    try:
        # 2. Extract visual subject bounding box in pixel space
        bio = io.BytesIO(image_bytes)
        with Image.open(bio) as pil_img:
            img_w, img_h = pil_img.size
            rgb_arr = np.array(pil_img.convert("RGB"))

        # Fast saliency & edge contour detection using numpy / cv2
        norm_box = _detect_focal_subject_normalized(rgb_arr, img_w, img_h)
        if norm_box is None:
            return _fallback_character_rect(panel_rect) if allow_fallback else None

        # 3. Transform normalized image box into page coordinates based on placement
        tf = transform or Transform2D(scale_x=1.0, scale_y=1.0, translate_x=0.0, translate_y=0.0)
        user_sx = abs(float(tf.scale_x or 1.0))
        user_sy = abs(float(tf.scale_y or 1.0))
        tx = float(tf.translate_x or 0.0)
        ty = float(tf.translate_y or 0.0)

        # Match the editor's cover/contain placement and manual transform. The
        # transform origin is the image-layer anchor in panel-local pixels.
        fit = max if fit_mode == "cover" else min
        base_scale = fit(panel_rect.width / img_w, panel_rect.height / img_h)
        fitted_w, fitted_h = img_w * base_scale, img_h * base_scale
        fit_left = (panel_rect.width - fitted_w) / 2.0
        fit_top = (panel_rect.height - fitted_h) / 2.0
        angle = math.radians(float(tf.rotation_deg or 0.0))
        cosine, sine = math.cos(angle), math.sin(angle)
        anchor_x = float(tf.anchor_x) * panel_rect.width
        anchor_y = float(tf.anchor_y) * panel_rect.height

        source_box = (
            fit_left + norm_box["x"] * fitted_w,
            fit_top + norm_box["y"] * fitted_h,
            fit_left + (norm_box["x"] + norm_box["width"]) * fitted_w,
            fit_top + (norm_box["y"] + norm_box["height"]) * fitted_h,
        )
        transformed_points = []
        for local_x in (source_box[0], source_box[2]):
            for local_y in (source_box[1], source_box[3]):
                dx = (local_x - anchor_x) * user_sx
                dy = (local_y - anchor_y) * user_sy
                transformed_points.append((
                    panel_rect.x + anchor_x + cosine * dx - sine * dy + tx,
                    panel_rect.y + anchor_y + sine * dx + cosine * dy + ty,
                ))
        char_page_x = min(point[0] for point in transformed_points)
        char_page_y = min(point[1] for point in transformed_points)
        char_page_right = max(point[0] for point in transformed_points)
        char_page_bottom = max(point[1] for point in transformed_points)
        char_page_w = char_page_right - char_page_x
        char_page_h = char_page_bottom - char_page_y

        # Clip/clamp to visible panel bounds
        visible_left = max(panel_rect.x, char_page_x)
        visible_top = max(panel_rect.y, char_page_y)
        visible_right = min(panel_rect.right, char_page_x + char_page_w)
        visible_bottom = min(panel_rect.bottom, char_page_y + char_page_h)
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return None
        char_rect = Rect(
            x=visible_left,
            y=visible_top,
            width=visible_right - visible_left,
            height=visible_bottom - visible_top,
        )
        return char_rect
    except Exception:
        return _fallback_character_rect(panel_rect) if allow_fallback else None


def _detect_focal_subject_normalized(rgb_arr: np.ndarray, width: int, height: int) -> Optional[Dict[str, float]]:
    """
    Analyzes edge density, luminance gradients, and skin-tone clustering to locate
    the focal character inside the frame. Returns normalized {x, y, width, height} [0..1].
    """
    try:
        import cv2

        gray = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)
        lab = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
        hsv = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2HSV)
        # Combine ink edges with adaptive color and luminance saliency. The
        # border estimates the artwork's background; no human skin/color model
        # is used, so monochrome drawings and nonhuman subjects are supported.
        edges = cv2.Canny(gray, 32, 118)
        border = np.concatenate((lab[0, :, :], lab[-1, :, :], lab[:, 0, :], lab[:, -1, :]), axis=0)
        border_lab = np.median(border, axis=0).astype(np.int16)
        lab_delta = np.clip(np.linalg.norm(lab.astype(np.int16) - border_lab, axis=2), 0, 255).astype(np.uint8)
        gray_delta = np.abs(gray.astype(np.int16) - int(np.median(np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))))).astype(np.uint8)
        saturation = hsv[:, :, 1]
        saturation_delta = cv2.absdiff(saturation, np.full_like(saturation, int(np.median(np.concatenate((saturation[0], saturation[-1], saturation[:, 0], saturation[:, -1]))))))
        _, color_mask = cv2.threshold(lab_delta, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        _, gray_mask = cv2.threshold(gray_delta, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        _, saturation_mask = cv2.threshold(saturation_delta, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        combined = cv2.bitwise_or(edges, cv2.bitwise_or(color_mask, cv2.bitwise_or(gray_mask, saturation_mask)))

        # Morphological closing with adaptive structuring element that preserves separation
        k_w = max(5, min(25, width // 80))
        k_h = max(5, min(25, height // 80))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_w, k_h))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        min_area = 0.020 * width * height
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(contour)
            box_area = bw * bh
            if box_area > 0.92 * width * height:
                continue
            if bw < width * 0.08 or bh < height * 0.12:
                continue
            cx = (bx + bw / 2) / width
            cy = (by + bh / 2) / height
            center_score = max(0.15, 1.0 - abs(cx - 0.5) * 1.2 - abs(cy - 0.5) * 0.35)
            fill_score = min(1.0, area / max(1.0, box_area))
            # Prefer coherent, reasonably compact foreground figures over a
            # wide background strip or a large disconnected scene contour.
            aspect = bw / max(1.0, bh)
            shape_score = 1.0 if 0.16 <= aspect <= 2.8 else 0.55
            candidates.append((area * center_score * (0.6 + fill_score) * shape_score, bx, by, bw, bh))

        # Fallback to high-frequency edge density if full-bleed scene contours merged
        if not candidates:
            edge_density = cv2.GaussianBlur(edges.astype(np.float32), (31, 31), 0)
            edge_density = cv2.normalize(edge_density, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            _, thresh = cv2.threshold(edge_density, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            d_contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in d_contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                bx, by, bw, bh = cv2.boundingRect(contour)
                box_area = bw * bh
                if box_area > 0.92 * width * height:
                    continue
                if bw < width * 0.08 or bh < height * 0.12:
                    continue
                cx = (bx + bw / 2) / width
                cy = (by + bh / 2) / height
                center_score = max(0.15, 1.0 - abs(cx - 0.5) * 1.2 - abs(cy - 0.5) * 0.35)
                candidates.append((area * center_score, bx, by, bw, bh))

        if candidates:
            # Pick one plausible focal subject, not the union of detailed
            # background contours which can hide the actual character bounds.
            _, bx, by, bw, bh = max(candidates, key=lambda item: item[0])
            return {
                "x": max(0.0, min(1.0, bx / width)),
                "y": max(0.0, min(1.0, by / height)),
                "width": max(0.1, min(1.0, bw / width)),
                "height": max(0.1, min(1.0, bh / height)),
            }
    except Exception:
        pass

    # No visual evidence was found. Callers that require accuracy must report
    # unknown instead of pretending the central area contains a character.
    return None


def _fallback_character_rect(panel_rect: Rect) -> Rect:
    """Default character bounds when no image exists: central upper 60%."""
    return Rect(
        x=panel_rect.x + panel_rect.width * 0.25,
        y=panel_rect.y + panel_rect.height * 0.15,
        width=panel_rect.width * 0.50,
        height=panel_rect.height * 0.65,
    )


def compute_exterior_tail_tip(
    bubble_center: Point,
    head_anchor: Point,
    char_bounds: Rect,
    clearance: float = 12.0,
    bubble_rect: Optional[Rect] = None,
) -> Point:
    """Terminates speech bubble tail tip cleanly outside the character silhouette to avoid piercing faces."""
    dx = head_anchor.x - bubble_center.x
    dy = head_anchor.y - bubble_center.y
    dist = math.hypot(dx, dy)
    if dist < 1.0:
        return head_anchor
    ux = dx / dist
    uy = dy / dist

    # Ray starts at bubble_center and travels towards head_anchor.
    # Find t where ray enters char_bounds.
    if abs(ux) > 1e-6:
        tx1 = (char_bounds.x - bubble_center.x) / ux
        tx2 = (char_bounds.right - bubble_center.x) / ux
        t_enter_x = min(tx1, tx2)
    else:
        t_enter_x = 0.0 if (char_bounds.x <= bubble_center.x <= char_bounds.right) else float("inf")

    if abs(uy) > 1e-6:
        ty1 = (char_bounds.y - bubble_center.y) / uy
        ty2 = (char_bounds.bottom - bubble_center.y) / uy
        t_enter_y = min(ty1, ty2)
    else:
        t_enter_y = 0.0 if (char_bounds.y <= bubble_center.y <= char_bounds.bottom) else float("inf")

    t_enter = max(0.0, max(t_enter_x, t_enter_y))
    if t_enter < dist:
        if bubble_rect is not None:
            # Ray exits bubble_rect
            tx_exit = (bubble_rect.right - bubble_center.x) / ux if ux > 1e-6 else ((bubble_rect.x - bubble_center.x) / ux if ux < -1e-6 else float("inf"))
            ty_exit = (bubble_rect.bottom - bubble_center.y) / uy if uy > 1e-6 else ((bubble_rect.y - bubble_center.y) / uy if uy < -1e-6 else float("inf"))
            t_exit = max(0.0, min(tx_exit, ty_exit))
            gap = t_enter - t_exit
            if gap > 0:
                eff_clearance = min(clearance, gap * 0.5)
                t_tip = max(t_exit, t_enter - eff_clearance)
            else:
                t_tip = t_enter
        else:
            t_tip = max(0.0, t_enter - clearance)
        return Point(
            x=bubble_center.x + ux * t_tip,
            y=bubble_center.y + uy * t_tip,
        )
    return head_anchor


def calculate_safe_bubble_placement(
    panel_rect: Rect,
    bubble_w: float,
    bubble_h: float,
    character_bounds: Optional[Rect] = None,
    reading_direction: str = "ltr",
    page_trim: Optional[Rect] = None,
    obstacles: Optional[list[Rect]] = None,
    allow_overlap_fallback: bool = False,
    vertical_only: bool = False,
    speaker_anchor: Optional[Point] = None,
) -> Tuple[Point, Point]:
    """
    Calculates intelligent speech bubble coordinates that place the bubble
    ABOVE or UNDER the character, never directly covering the character's face.
    Returns (bubble_position: Point, tail_target: Point).
    """
    if character_bounds is None:
        raise ValueError("Character bounds are required for safe bubble placement; no guessed position is used.")
    char = character_bounds
    trim = page_trim or panel_rect
    margin = 10.0
    inset = 6.0
    char_cx = char.x + char.width / 2.0
    # This is a conservative head/mouth-region estimate from the visible
    # subject bounds, not a facial landmark claim. A creator-confirmed anchor
    # remains preferable and replaces this estimate at the registry boundary.
    head = speaker_anchor or Point(x=char_cx, y=char.y + min(char.height * 0.20, 45.0))
    # Strict panel bounding box (with optional small gutter bleed, max 4px, but clamped by page_trim)
    bleed = 4.0
    x_min = max(trim.x + bleed, panel_rect.x - bleed)
    y_min = max(trim.y + bleed, panel_rect.y - bleed)
    x_max = min(trim.right - bubble_w - bleed, panel_rect.right - bubble_w + bleed)
    y_max = min(trim.bottom - bubble_h - bleed, panel_rect.bottom - bubble_h + bleed)
    if x_max < x_min or y_max < y_min:
        x_min = panel_rect.x
        y_min = panel_rect.y
        x_max = max(x_min, panel_rect.right - bubble_w)
        y_max = max(y_min, panel_rect.bottom - bubble_h)
    if x_max < x_min or y_max < y_min:
        raise ValueError("The bubble is larger than the panel's available safe area.")

    def overlaps(a: Rect, b: Rect, gap: float = 0.0) -> bool:
        return not (a.right + gap <= b.x or b.right + gap <= a.x or a.bottom + gap <= b.y or b.bottom + gap <= a.y)

    clamp_x = lambda value: max(x_min, min(x_max, value))
    clamp_y = lambda value: max(y_min, min(y_max, value))
    side_y = clamp_y(head.y - bubble_h * 0.45)
    candidates = [
        (clamp_x(char.x - bubble_w + char.width * 0.22), char.y - bubble_h - margin, "top_left"),
        (clamp_x(char.right - char.width * 0.22), char.y - bubble_h - margin, "top_right"),
        (clamp_x(char.x - bubble_w + char.width * 0.22), char.bottom + margin, "bottom_left"),
        (clamp_x(char.right - char.width * 0.22), char.bottom + margin, "bottom_right"),
        (char.x - bubble_w - margin, side_y, "middle_left"),
        (char.right + margin, side_y, "middle_right"),
        (clamp_x(char_cx - bubble_w / 2.0), char.y - bubble_h - margin, "top_center"),
        (clamp_x(char_cx - bubble_w / 2.0), char.bottom + margin, "bottom_center"),
        (clamp_x(panel_rect.x + margin), clamp_y(panel_rect.y + margin), "panel_top_left"),
        (clamp_x(panel_rect.right - bubble_w - margin), clamp_y(panel_rect.y + margin), "panel_top_right"),
        (clamp_x(panel_rect.x + margin), clamp_y(panel_rect.bottom - bubble_h - margin), "panel_bottom_left"),
        (clamp_x(panel_rect.right - bubble_w - margin), clamp_y(panel_rect.bottom - bubble_h - margin), "panel_bottom_right"),
    ]
    if vertical_only:
        candidates = [item for item in candidates if item[2] in {"top_center", "bottom_center"}]

    head_box = Rect(
        x=max(panel_rect.x, char.x - 4.0),
        y=max(panel_rect.y, char.y - 4.0),
        width=char.width + 8.0,
        height=min(char.height * 0.35, 70.0),
    )

    viable = []
    face_safe_viable = []
    rtl = str(reading_direction).casefold() == "rtl"
    for x, y, region in candidates:
        if x < x_min or x > x_max or y < y_min or y > y_max:
            continue
        candidate = Rect(x=float(x), y=float(y), width=bubble_w, height=bubble_h)
        if any(overlaps(candidate, obstacle, gap=4.0) for obstacle in (obstacles or [])):
            continue
        if overlaps(candidate, head_box, gap=4.0):
            continue

        char_collides = overlaps(candidate, char, gap=margin)

        horizontal_distance = abs(candidate.center.x - head.x) / max(1.0, panel_rect.width)
        vertical_distance = abs(candidate.center.y - head.y) / max(1.0, panel_rect.height)
        reading_side = (candidate.center.x >= head.x) if rtl else (candidate.center.x <= head.x)
        # Prefer a compact balloon above the face and on the first-reading
        # side, while keeping proximity and page-edge clearance in the score.
        score = horizontal_distance * 1.1 + vertical_distance * 0.35
        score += 0.0 if region.startswith("top") or "top" in region else 0.45 if region.startswith("middle") else 0.72
        score += -0.18 if reading_side else 0.18
        score += 0.08 * (
            min(candidate.x - trim.x, trim.right - candidate.right, candidate.y - trim.y, trim.bottom - candidate.bottom)
            / max(1.0, min(trim.width, trim.height))
        )
        for obstacle in obstacles or []:
            gap_x = max(0.0, max(obstacle.x - candidate.right, candidate.x - obstacle.right))
            gap_y = max(0.0, max(obstacle.y - candidate.bottom, candidate.y - obstacle.bottom))
            distance = math.hypot(gap_x, gap_y)
            score += 0.1 / max(1.0, distance)
            # Enforce conversational reading order relative to previous obstacle
            if rtl:
                if candidate.center.x > obstacle.center.x - 10.0 and candidate.center.y >= obstacle.center.y - 20.0:
                    score += 1.5
            else:
                if candidate.center.x < obstacle.center.x + 10.0 and candidate.center.y >= obstacle.center.y - 20.0:
                    score += 1.5

        char_collides = overlaps(candidate, char, gap=margin)
        head_collides = overlaps(candidate, head_box, gap=4.0)

        if not char_collides:
            viable.append((score, x, y))
        elif not head_collides and (char.width < panel_rect.width * 0.90 or char.height < panel_rect.height * 0.90):
            face_safe_viable.append((score + 1.2, x, y))

    best_pool = viable if viable else face_safe_viable
    if best_pool:
        _, x, y = min(best_pool, key=lambda item: item[0])
        b_rect = Rect(x=float(x), y=float(y), width=bubble_w, height=bubble_h)
        b_center = Point(x=float(x) + bubble_w / 2.0, y=float(y) + bubble_h / 2.0)
        tail_tip = compute_exterior_tail_tip(b_center, head, char, clearance=12.0, bubble_rect=b_rect)
        clamped_tail = Point(
            x=max(panel_rect.x, min(panel_rect.right, tail_tip.x)),
            y=max(panel_rect.y, min(panel_rect.bottom, tail_tip.y)),
        )
        return Point(x=float(x), y=float(y)), clamped_tail

    if allow_overlap_fallback:
        # Legacy manual editing remains possible; Agent calls never enable this.
        x = max(x_min, min(x_max, char_cx - bubble_w / 2.0))
        y = max(y_min, min(y_max, char.y - bubble_h * 0.5))
        b_rect = Rect(x=float(x), y=float(y), width=bubble_w, height=bubble_h)
        b_center = Point(x=float(x) + bubble_w / 2.0, y=float(y) + bubble_h / 2.0)
        tail_tip = compute_exterior_tail_tip(b_center, head, char, clearance=12.0, bubble_rect=b_rect)
        return Point(x=float(x), y=float(y)), tail_tip

    raise ValueError("No clear space remains in this panel without covering the character.")
