"""
InkLoop Image-Canvas Integration Engine (E3) - Raster Pixel Manipulation Utilities.
Handles high-fidelity Pillow image loading, resampling, cropping, polygon alpha masking,
and deterministic PNG encoding.
"""
import io
import hashlib
import math
from pathlib import Path
from typing import Tuple, Union, Optional, List
from PIL import Image, ImageDraw

from app.contracts.geometry import Point, Size, Rect, FitMode
from app.image_canvas.models import ResamplingFilter
from app.image_canvas.errors import (
    UnsupportedImageFormatError,
    AllocationLimitExceededError,
    InvalidPlacementGeometryError,
)
from app.image_canvas.fitter import compute_source_crop_rect

MAX_SOURCE_WIDTH = 20_000
MAX_SOURCE_HEIGHT = 20_000
MAX_SOURCE_PIXELS = 100_000_000

RESAMPLING_MAP = {
    ResamplingFilter.LANCZOS: Image.Resampling.LANCZOS,
    ResamplingFilter.BICUBIC: Image.Resampling.BICUBIC,
    ResamplingFilter.BILINEAR: Image.Resampling.BILINEAR,
    ResamplingFilter.NEAREST: Image.Resampling.NEAREST,
}

def load_source_image(
    source: Union[bytes, str, Path]
) -> Tuple[Image.Image, str, Size]:
    """
    Loads, validates, and hashes a source raster image.
    Enforces format safety and memory allocation limits.
    Returns:
        (image_rgba, sha256_hash, native_size)
    """
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.is_file():
            raise FileNotFoundError(f"Source image file does not exist: {p}")
        raw_bytes = p.read_bytes()
    elif isinstance(source, bytes):
        raw_bytes = source
    else:
        raise UnsupportedImageFormatError(f"Unsupported source image type: {type(source)}")

    if not raw_bytes or len(raw_bytes) < 8:
        raise UnsupportedImageFormatError("Source image bytes are empty or corrupted")

    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.verify()
        # Re-open after verify() as Pillow verify() invalidates file pointer
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception as e:
        raise UnsupportedImageFormatError(f"Failed to decode raster image format: {e}")

    w, h = img.size
    if w <= 0 or h <= 0:
        raise InvalidPlacementGeometryError(f"Decoded image has non-positive dimensions: {w}x{h}")

    if w > MAX_SOURCE_WIDTH or h > MAX_SOURCE_HEIGHT or (w * h) > MAX_SOURCE_PIXELS:
        raise AllocationLimitExceededError(
            f"Source image dimensions ({w}x{h} px) exceed maximum permitted allocation limits"
        )

    # Convert to RGBA for consistent alpha and compositing operations
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    return img, sha256, Size(width=float(w), height=float(h))

def apply_placement_raster(
    source_img: Image.Image,
    target_size: Size,
    mode: FitMode = FitMode.COVER,
    anchor: Point = Point(x=0.5, y=0.5),
    resampling: ResamplingFilter = ResamplingFilter.LANCZOS,
    background_color: Optional[str] = None
) -> Image.Image:
    """
    Resamples and crops/letterboxes source_img into target_size according to FitMode and anchor.
    Returns an RGBA Image of exact dimensions (target_size.width, target_size.height).
    """
    target_w = int(round(target_size.width))
    target_h = int(round(target_size.height))

    if target_w <= 0 or target_h <= 0:
        raise InvalidPlacementGeometryError(f"Target raster dimensions must be strictly positive: {target_w}x{target_h}")

    filter_type = RESAMPLING_MAP.get(resampling, Image.Resampling.LANCZOS)
    sw, sh = source_img.size

    if mode == FitMode.COVER:
        # 1. Calculate source crop rect in native image coordinates
        crop_rect = compute_source_crop_rect(
            Size(width=float(sw), height=float(sh)),
            Rect(x=0.0, y=0.0, width=float(target_w), height=float(target_h)),
            anchor=anchor
        )

        box = (
            int(round(crop_rect.left)),
            int(round(crop_rect.top)),
            int(round(crop_rect.right)),
            int(round(crop_rect.bottom))
        )
        # Crop native resolution region
        cropped = source_img.crop(box)
        # Resample cropped region to target dimensions
        placed = cropped.resize((target_w, target_h), resample=filter_type)
        return placed

    elif mode == FitMode.CONTAIN:
        # 2. Scale image uniformly so it fits entirely inside target_size
        scale_x = target_w / sw
        scale_y = target_h / sh
        scale = min(scale_x, scale_y)

        rw = max(1, int(round(sw * scale)))
        rh = max(1, int(round(sh * scale)))

        resized = source_img.resize((rw, rh), resample=filter_type)

        # Create target container canvas
        bg_col = background_color if background_color else (0, 0, 0, 0)
        canvas = Image.new("RGBA", (target_w, target_h), bg_col)

        # Paste aligned according to anchor
        paste_x = int(round((target_w - rw) * anchor.x))
        paste_y = int(round((target_h - rh) * anchor.y))

        canvas.alpha_composite(resized, (paste_x, paste_y))
        return canvas

    elif mode == FitMode.STRETCH:
        # 3. Direct non-uniform scaling
        return source_img.resize((target_w, target_h), resample=filter_type)

    else:
        # Default fallback
        return source_img.resize((target_w, target_h), resample=filter_type)

def apply_fit_manual_transform(
    source_img: Image.Image,
    target_size: Size,
    mode: FitMode,
    anchor: Point,
    transform,
    resampling: ResamplingFilter = ResamplingFilter.LANCZOS,
    background_color: Optional[str] = None,
) -> Image.Image:
    """Fit and transform the complete source before clipping to the panel canvas.

    The result always has the target panel's dimensions, but the affine mapping is
    calculated against the uncropped fitted source. Translations and scale changes
    can therefore reveal source pixels that a cover crop previously discarded.
    """
    target_w = int(round(target_size.width))
    target_h = int(round(target_size.height))
    source_w, source_h = source_img.size
    if target_w <= 0 or target_h <= 0 or source_w <= 0 or source_h <= 0:
        raise InvalidPlacementGeometryError("Source image and target panel dimensions must be positive.")

    if mode == FitMode.COVER:
        fit_scale = max(target_w / source_w, target_h / source_h)
    elif mode == FitMode.CONTAIN:
        fit_scale = min(target_w / source_w, target_h / source_h)
    else:
        raise InvalidPlacementGeometryError(f"Unsupported editable image fit mode: {mode.value}")

    fit_w = source_w * fit_scale
    fit_h = source_h * fit_scale
    fit_x = (target_w - fit_w) * anchor.x
    fit_y = (target_h - fit_h) * anchor.y

    scale_x = float(transform.scale_x)
    scale_y = float(transform.scale_y)
    if scale_x <= 0 or scale_y <= 0:
        raise InvalidPlacementGeometryError("Manual image scale must be positive.")

    theta = math.radians(float(transform.rotation_deg))
    cosine = math.cos(theta)
    sine = math.sin(theta)
    anchor_x = float(transform.anchor_x) * target_w
    anchor_y = float(transform.anchor_y) * target_h
    translate_x = float(transform.translate_x)
    translate_y = float(transform.translate_y)

    # Pillow affine coefficients map destination panel pixels back to the full
    # original source. Fit offsets remain fractional until final resampling.
    a = cosine / (scale_x * fit_scale)
    b = sine / (scale_x * fit_scale)
    c = (anchor_x - cosine * (anchor_x + translate_x) - sine * (anchor_y + translate_y)) / (scale_x * fit_scale) - fit_x / fit_scale
    d = -sine / (scale_y * fit_scale)
    e = cosine / (scale_y * fit_scale)
    f = (anchor_y + sine * (anchor_x + translate_x) - cosine * (anchor_y + translate_y)) / (scale_y * fit_scale) - fit_y / fit_scale

    filter_type = RESAMPLING_MAP.get(resampling, Image.Resampling.LANCZOS)
    if filter_type not in (Image.Resampling.NEAREST, Image.Resampling.BILINEAR, Image.Resampling.BICUBIC):
        filter_type = Image.Resampling.BICUBIC
    transformed = source_img.transform(
        (target_w, target_h),
        Image.Transform.AFFINE,
        (a, b, c, d, e, f),
        resample=filter_type,
        fillcolor=(0, 0, 0, 0),
    )
    if background_color:
        background = Image.new("RGBA", (target_w, target_h), background_color)
        background.alpha_composite(transformed)
        return background
    return transformed


def apply_polygon_mask(
    img: Image.Image,
    polygon_points: List[Point],
    target_slot_rect: Rect
) -> Image.Image:
    """
    Applies an anti-aliased 8-bit alpha mask to img based on polygon vertices
    translated from PAGE coordinates to local PANEL_SLOT coordinates.
    """
    w, h = img.size
    # Map points from page space to local panel space
    local_pts = [
        (p.x - target_slot_rect.x, p.y - target_slot_rect.y)
        for p in polygon_points
    ]

    # Create 8-bit mask image initialized to black (transparent)
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(local_pts, fill=255)

    # Combine with image's existing alpha channel
    r, g, b, a = img.split()
    combined_alpha = Image.composite(a, Image.new("L", (w, h), 0), mask)
    img.putalpha(combined_alpha)
    return img

def apply_manual_transform(img: Image.Image, transform, resampling: ResamplingFilter = ResamplingFilter.LANCZOS) -> Image.Image:
    """Apply an affine user transform inside a fixed-size destination; the source is never mutated."""
    width, height = img.size
    sx, sy = float(transform.scale_x), float(transform.scale_y)
    if sx <= 0 or sy <= 0:
        raise InvalidPlacementGeometryError("Manual image scale must be positive.")
    if (abs(sx - 1.0) < 1e-12 and abs(sy - 1.0) < 1e-12
            and abs(float(transform.translate_x)) < 1e-12
            and abs(float(transform.translate_y)) < 1e-12
            and abs(float(transform.rotation_deg)) < 1e-12):
        return img.copy()
    import math
    theta = math.radians(float(transform.rotation_deg))
    cosine, sine = math.cos(theta), math.sin(theta)
    ax, ay = float(transform.anchor_x) * width, float(transform.anchor_y) * height
    tx, ty = float(transform.translate_x), float(transform.translate_y)
    # Pillow's affine coefficients map destination coordinates back to source coordinates.
    a = cosine / sx
    b = sine / sx
    d = -sine / sy
    e = cosine / sy
    c = ax - a * (ax + tx) - b * (ay + ty)
    f = ay - d * (ax + tx) - e * (ay + ty)
    filt = RESAMPLING_MAP.get(resampling, Image.Resampling.LANCZOS)
    if filt not in (Image.Resampling.NEAREST, Image.Resampling.BILINEAR, Image.Resampling.BICUBIC):
        filt = Image.Resampling.BICUBIC
    return img.transform((width, height), Image.Transform.AFFINE, (a, b, c, d, e, f), resample=filt)

def encode_png_bytes(img: Image.Image) -> Tuple[bytes, str]:
    """
    Encodes image to lossless PNG byte buffer deterministically and returns (bytes, sha256).
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    raw = buf.getvalue()
    sha256 = hashlib.sha256(raw).hexdigest()
    return raw, sha256
