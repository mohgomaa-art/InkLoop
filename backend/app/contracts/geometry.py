"""
InkLoop Canonical Coordinate System and Shared Geometry Library.
Establishes the single source of truth for 2D spatial coordinates, units, transforms, and bounds.

Core Conventions:
- Origin: Top-Left (0.0, 0.0)
- Axes: +X points rightward, +Y points downward
- Primary Units: Screen/Render Pixels (px) at declared DPI (default 300 for print, 96/72 for preview)
- Boundary Interval: Half-open [x, x + width) and [y, y + height) for discrete rasterization
- Rotation: Degrees (deg), clockwise positive around an explicit anchor (default (0.5, 0.5) center)
"""
import math
from enum import Enum
from typing import Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from app.contracts.errors import InvalidGeometryError, OutOfBoundsError

class CoordinateSpace(str, Enum):
    """Explicit coordinate reference spaces used across InkLoop engines."""
    PAGE = "page"                 # Full canvas coordinate space (e.g. 2480x3508 px at 300 DPI)
    PANEL_SLOT = "panel_slot"     # Local coordinates within a panel frame (origin at panel top-left)
    SOURCE_IMAGE = "source_image" # Intrinsic raw pixel buffer of generated artwork (e.g. 1280x1920)
    VIEWPORT = "viewport"         # Presentation/screen viewing space
    NORMALIZED = "normalized"     # Dimensionless [0.0, 1.0] unit square

class FitMode(str, Enum):
    """Policies for mapping source image dimensions into a target panel slot."""
    CONTAIN = "contain"           # Scale uniformly so entire image fits; letterboxing may occur
    COVER = "cover"               # Scale uniformly so slot is completely filled; cropping may occur
    CROP_TO_FRAME = "crop_to_frame" # Specific sub-rectangle of source mapped to target
    STRETCH = "stretch"           # Non-uniform scale (disallowed unless explicit override)
    MANUAL = "manual"             # Custom arbitrary affine transform matrix

# --- Unit Conversion Functions ---

def mm_to_px(mm: float, dpi: float = 300.0) -> float:
    """Converts millimeters to pixels at specified DPI (1 inch = 25.4 mm)."""
    return (mm * dpi) / 25.4

def px_to_mm(px: float, dpi: float = 300.0) -> float:
    """Converts pixels to millimeters at specified DPI."""
    return (px * 25.4) / dpi

def pt_to_px(pt: float, dpi: float = 300.0) -> float:
    """Converts physical typographic points (1/72 inch) to pixels."""
    return (pt * dpi) / 72.0

def px_to_pt(px: float, dpi: float = 300.0) -> float:
    """Converts pixels to typographic points."""
    return (px * 72.0) / dpi

# --- Core Spatial Data Models ---

class Point(BaseModel):
    """A 2D coordinate in a declared coordinate space."""
    x: float = Field(..., description="Horizontal coordinate (+X points right)")
    y: float = Field(..., description="Vertical coordinate (+Y points down)")

    @field_validator("x", "y")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise InvalidGeometryError(f"Coordinate value must be finite, received {v}")
        return float(v)

class Size(BaseModel):
    """Strictly positive 2D dimensions."""
    width: float = Field(..., description="Horizontal extent (> 0)")
    height: float = Field(..., description="Vertical extent (> 0)")

    @field_validator("width", "height")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        if not math.isfinite(v) or v <= 0:
            raise InvalidGeometryError(f"Dimensions must be strictly positive (> 0), received {v}")
        return float(v)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

class Rect(BaseModel):
    """
    Axis-aligned 2D rectangle.
    Defined by top-left origin (x, y) and positive spatial extents (width, height).
    Discrete rasterization adheres to the half-open interval [x, x + width) x [y, y + height).
    """
    x: float = Field(..., description="Top-left X coordinate")
    y: float = Field(..., description="Top-left Y coordinate")
    width: float = Field(..., description="Strictly positive width")
    height: float = Field(..., description="Strictly positive height")

    @field_validator("x", "y")
    @classmethod
    def validate_finite_coords(cls, v: float) -> float:
        if not math.isfinite(v):
            raise InvalidGeometryError(f"Origin coordinate must be finite, received {v}")
        return float(v)

    @field_validator("width", "height")
    @classmethod
    def validate_positive_extents(cls, v: float) -> float:
        if not math.isfinite(v) or v <= 0:
            raise InvalidGeometryError(f"Rectangle dimensions must be strictly positive (> 0), received {v}")
        return float(v)

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Point:
        return Point(x=self.x + self.width / 2.0, y=self.y + self.height / 2.0)

    @property
    def size(self) -> Size:
        return Size(width=self.width, height=self.height)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

class Transform2D(BaseModel):
    """
    2D Affine Transformation parameters.
    Composition order: Scale -> Rotate -> Translate relative to specified normalized anchor.
    """
    scale_x: float = Field(default=1.0, description="Horizontal scale factor")
    scale_y: float = Field(default=1.0, description="Vertical scale factor")
    translate_x: float = Field(default=0.0, description="Horizontal translation in target pixels")
    translate_y: float = Field(default=0.0, description="Vertical translation in target pixels")
    rotation_deg: float = Field(default=0.0, description="Clockwise rotation in degrees")
    anchor_x: float = Field(default=0.5, description="Normalized anchor X [0.0 = left, 0.5 = center, 1.0 = right]")
    anchor_y: float = Field(default=0.5, description="Normalized anchor Y [0.0 = top, 0.5 = center, 1.0 = bottom]")

    @field_validator("scale_x", "scale_y")
    @classmethod
    def validate_non_zero_scale(cls, v: float) -> float:
        if abs(v) < 1e-9:
            raise InvalidGeometryError("Scale factors must not be zero")
        return float(v)

# --- Geometry Arithmetic and Intersection Functions ---

def rect_contains(outer: Rect, inner: Rect, epsilon: float = 1e-6) -> bool:
    """Returns True if 'inner' rectangle is fully enclosed within 'outer'."""
    return (
        inner.left >= outer.left - epsilon and
        inner.right <= outer.right + epsilon and
        inner.top >= outer.top - epsilon and
        inner.bottom <= outer.bottom + epsilon
    )

def rect_intersects(a: Rect, b: Rect) -> bool:
    """
    Returns True if rectangles 'a' and 'b' overlap with non-zero area.
    Adheres to half-open interval: touching edges do NOT intersect.
    """
    return not (
        a.right <= b.left or
        a.left >= b.right or
        a.bottom <= b.top or
        a.top >= b.bottom
    )

def rect_intersection(a: Rect, b: Rect) -> Optional[Rect]:
    """Computes the overlapping intersection of two rectangles, or None if disjoint."""
    x1 = max(a.left, b.left)
    y1 = max(a.top, b.top)
    x2 = min(a.right, b.right)
    y2 = min(a.bottom, b.bottom)
    if x2 > x1 and y2 > y1:
        return Rect(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
    return None

def rect_union(a: Rect, b: Rect) -> Rect:
    """Computes the minimal bounding rectangle enclosing both 'a' and 'b'."""
    x1 = min(a.left, b.left)
    y1 = min(a.top, b.top)
    x2 = max(a.right, b.right)
    y2 = max(a.bottom, b.bottom)
    return Rect(x=x1, y=y1, width=x2 - x1, height=y2 - y1)

def snap_to_pixel_grid(rect: Rect) -> Rect:
    """Snaps rectangle boundaries to exact integer pixel coordinates."""
    x = math.floor(rect.x + 0.5)
    y = math.floor(rect.y + 0.5)
    w = max(1.0, math.floor(rect.width + 0.5))
    h = max(1.0, math.floor(rect.height + 0.5))
    return Rect(x=x, y=y, width=w, height=h)

# --- Coordinate Space Transformations ---

def panel_to_page(point: Point, panel_rect: Rect) -> Point:
    """Converts a local point in PANEL_SLOT coordinates to PAGE coordinates."""
    return Point(x=panel_rect.x + point.x, y=panel_rect.y + point.y)

def page_to_panel(point: Point, panel_rect: Rect) -> Point:
    """Converts a point in PAGE coordinates to local PANEL_SLOT coordinates."""
    return Point(x=point.x - panel_rect.x, y=point.y - panel_rect.y)

def normalize_point(point: Point, container: Rect) -> Point:
    """Normalizes point coordinates to [0.0, 1.0] relative to container dimensions."""
    return Point(
        x=(point.x - container.x) / container.width,
        y=(point.y - container.y) / container.height
    )

def denormalize_point(norm_point: Point, container: Rect) -> Point:
    """Denormalizes a [0.0, 1.0] relative point back into absolute pixel coordinates."""
    return Point(
        x=container.x + (norm_point.x * container.width),
        y=container.y + (norm_point.y * container.height)
    )

def normalize_rect(rect: Rect, container: Rect) -> Rect:
    """Normalizes a rectangle relative to a container."""
    return Rect(
        x=(rect.x - container.x) / container.width,
        y=(rect.y - container.y) / container.height,
        width=rect.width / container.width,
        height=rect.height / container.height
    )

def denormalize_rect(norm_rect: Rect, container: Rect) -> Rect:
    """Denormalizes a relative rectangle back to absolute container pixels."""
    return Rect(
        x=container.x + (norm_rect.x * container.width),
        y=container.y + (norm_rect.y * container.height),
        width=norm_rect.width * container.width,
        height=norm_rect.height * container.height
    )

def calculate_fit_transform(
    source_size: Size,
    target_rect: Rect,
    mode: FitMode = FitMode.CONTAIN,
    anchor: Point = Point(x=0.5, y=0.5)
) -> Transform2D:
    """
    Computes exact scale and translation to place source_size into target_rect
    according to the specified FitMode while strictly preserving aspect ratio (except STRETCH).
    """
    sw, sh = source_size.width, source_size.height
    tw, th = target_rect.width, target_rect.height

    scale_x_ratio = tw / sw
    scale_y_ratio = th / sh

    if mode == FitMode.CONTAIN:
        # Fit entirely inside: choose smaller scale
        scale = min(scale_x_ratio, scale_y_ratio)
        rw = sw * scale
        rh = sh * scale
        tx = target_rect.x + (tw - rw) * anchor.x
        ty = target_rect.y + (th - rh) * anchor.y
        return Transform2D(scale_x=scale, scale_y=scale, translate_x=tx, translate_y=ty, anchor_x=anchor.x, anchor_y=anchor.y)

    elif mode == FitMode.COVER:
        # Cover target slot entirely: choose larger scale
        scale = max(scale_x_ratio, scale_y_ratio)
        rw = sw * scale
        rh = sh * scale
        tx = target_rect.x + (tw - rw) * anchor.x
        ty = target_rect.y + (th - rh) * anchor.y
        return Transform2D(scale_x=scale, scale_y=scale, translate_x=tx, translate_y=ty, anchor_x=anchor.x, anchor_y=anchor.y)

    elif mode == FitMode.STRETCH:
        # Non-uniform scale (distorts aspect ratio)
        return Transform2D(scale_x=scale_x_ratio, scale_y=scale_y_ratio, translate_x=target_rect.x, translate_y=target_rect.y)

    else:
        # Default fallback
        return Transform2D(scale_x=1.0, scale_y=1.0, translate_x=target_rect.x, translate_y=target_rect.y)

def validate_panel_in_canvas(
    panel: Rect,
    canvas: Rect,
    allow_bleed: bool = False,
    bleed_margin_px: float = 0.0
) -> None:
    """Validates that a panel is safely located within permissible canvas boundaries."""
    effective_canvas = canvas
    if allow_bleed and bleed_margin_px > 0:
        effective_canvas = Rect(
            x=canvas.x - bleed_margin_px,
            y=canvas.y - bleed_margin_px,
            width=canvas.width + (2 * bleed_margin_px),
            height=canvas.height + (2 * bleed_margin_px)
        )

    if not rect_contains(effective_canvas, panel):
        raise OutOfBoundsError(
            f"Panel [{panel.x}, {panel.y}, {panel.width}x{panel.height}] extends outside permissible canvas bounds [{canvas.width}x{canvas.height}]",
            details={"panel": panel.model_dump(), "canvas": canvas.model_dump(), "allow_bleed": allow_bleed}
        )
