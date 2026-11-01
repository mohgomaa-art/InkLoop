"""
InkLoop Image-Canvas Integration Engine (E3) - Mathematical Fitting & Transform Calculator.
Computes exact 2D affine transforms, crop rectangles, scaling ratios, and aspect ratio checks.
Authoritative coordinate reference: Top-Left (0, 0), +X right, +Y down.
"""
import math
from typing import Tuple
from app.contracts.geometry import (
    Point,
    Size,
    Rect,
    FitMode,
    Transform2D,
    calculate_fit_transform,
)
from app.image_canvas.errors import (
    InvalidPlacementGeometryError,
    AspectRatioDistortionError,
)

def compute_placement_transform(
    source_size: Size,
    target_rect: Rect,
    mode: FitMode = FitMode.COVER,
    anchor: Point = Point(x=0.5, y=0.5)
) -> Tuple[Transform2D, Rect, bool]:
    """
    Computes exact affine transform, effective placed rect, and clipping flag.
    Returns:
        (transform, placed_rect, is_clipped)
    """
    if source_size.width <= 0 or source_size.height <= 0:
        raise InvalidPlacementGeometryError(
            f"Source image dimensions must be strictly positive, received {source_size.width}x{source_size.height}"
        )

    if target_rect.width <= 0 or target_rect.height <= 0:
        raise InvalidPlacementGeometryError(
            f"Target panel slot rect dimensions must be strictly positive, received {target_rect.width}x{target_rect.height}"
        )

    # Calculate authoritative transform using contracts/geometry.py
    transform = calculate_fit_transform(source_size, target_rect, mode=mode, anchor=anchor)

    # Check aspect ratio preservation for CONTAIN and COVER
    if mode in (FitMode.CONTAIN, FitMode.COVER):
        if abs(transform.scale_x - transform.scale_y) > 1e-6:
            raise AspectRatioDistortionError(
                f"Scale factors differ ({transform.scale_x:.6f} vs {transform.scale_y:.6f}) under {mode.value}"
            )

    sw, sh = source_size.width, source_size.height
    tw, th = target_rect.width, target_rect.height
    scale = transform.scale_x

    source_aspect = sw / sh
    target_aspect = tw / th
    aspect_diff = abs(source_aspect - target_aspect)

    if mode == FitMode.COVER:
        # Under COVER, if aspect ratios differ, content is cropped
        is_clipped = aspect_diff > 1e-4
        placed_rect = target_rect

    elif mode == FitMode.CONTAIN:
        # Under CONTAIN, entire image is preserved (letterboxed), no cropping
        is_clipped = False
        rw = sw * scale
        rh = sh * scale
        placed_rect = Rect(
            x=transform.translate_x,
            y=transform.translate_y,
            width=rw,
            height=rh
        )

    elif mode == FitMode.STRETCH:
        # Distorts aspect ratio to match slot exactly
        is_clipped = False
        placed_rect = target_rect

    else:
        is_clipped = False
        placed_rect = target_rect

    return transform, placed_rect, is_clipped

def compute_source_crop_rect(
    source_size: Size,
    target_rect: Rect,
    anchor: Point = Point(x=0.5, y=0.5)
) -> Rect:
    """
    For COVER mode, calculates the exact sub-rectangle of the source image in source pixels
    that corresponds to the target slot aspect ratio before resampling.
    """
    sw, sh = source_size.width, source_size.height
    tw, th = target_rect.width, target_rect.height

    scale = max(tw / sw, th / sh)
    crop_w = tw / scale
    crop_h = th / scale

    # Clamp to prevent precision overflow
    crop_w = min(sw, crop_w)
    crop_h = min(sh, crop_h)

    # Compute source offsets based on anchor
    excess_w = max(0.0, sw - crop_w)
    excess_h = max(0.0, sh - crop_h)

    crop_x = excess_w * anchor.x
    crop_y = excess_h * anchor.y

    return Rect(x=crop_x, y=crop_y, width=crop_w, height=crop_h)
