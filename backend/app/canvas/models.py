"""
InkLoop Canvas Generation Engine (E2) - Core Domain Models and Contracts.
Establishes typed, validated Pydantic models for CanvasSpec, PageSpec, PanelSlot,
GutterSpec, MarginSpec, BleedSpec, SafeAreaSpec, and CanvasLayoutResult.
Authoritative coordinate reference: Top-Left (0, 0), +X right, +Y down.
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from app.contracts.geometry import (
    Rect,
    Point,
    Size,
    ColorSpace,
    mm_to_px,
)
from app.contracts.engine import CanvasGenerationOutput
from app.canvas.errors import (
    InvalidDimensionError,
    AllocationLimitExceededError,
    ImpossibleLayoutError,
)
from app.canvas.descriptors import MultiAxisPanelDescriptor

# Allocation safety limits to protect against memory exhaustion / DoS
MAX_CANVAS_WIDTH_PX: float = 20_000.0
MAX_CANVAS_HEIGHT_PX: float = 100_000.0
MAX_TOTAL_PIXELS: float = 100_000_000.0

class PageFormat(str, Enum):
    """Standard comic publication formats with canonical physical/pixel aspect ratios."""
    A4 = "A4"                           # 210 x 297 mm (~2480 x 3508 px at 300 DPI)
    B5 = "B5"                           # 182 x 257 mm (~2150 x 3035 px at 300 DPI - standard Japanese manga)
    US_COMIC = "us_comic"               # 6.625 x 10.187 in (~1988 x 3056 px at 300 DPI)
    WEBTOON_VERTICAL = "webtoon_vertical" # Continuous vertical scroll (800 px standard width, variable height)
    CUSTOM = "custom"                   # User-defined dimensions

class PageType(str, Enum):
    """Structural page classification in comic pagination."""
    SINGLE = "single"                   # Standard single-page layout
    SPREAD_LEFT = "spread_left"         # Left page of a two-page spread
    SPREAD_RIGHT = "spread_right"       # Right page of a two-page spread
    SPREAD_DOUBLE = "spread_double"     # Unified seamless double-page spread
    WEBTOON_SCROLL = "webtoon_scroll"   # Long-canvas vertical webtoon strip
    COVER = "cover"                     # Front/back cover page

class ReadingDirection(str, Enum):
    """Panel traversal direction determining the canonical reading order sequence."""
    RTL = "rtl"                         # Right-to-Left (Manga, Manhwa historical, Arabic comics)
    LTR = "ltr"                         # Left-to-Right (Western comics, European albums, Webtoons)

class LayoutTemplateId(str, Enum):
    """Enumeration of verified deterministic layout template algorithms."""
    MANGA_GRID = "manga_grid"
    SIX_PANEL_CLASSIC = "six_panel_classic"
    FOUR_KOMA = "four_koma"
    DYNAMIC_SHONEN = "dynamic_shonen"
    WEBTOON_VERTICAL = "webtoon_vertical"
    THREE_PANEL_HERO = "three_panel_hero"
    THREE_PANEL_SLANTED = "three_panel_slanted"
    FIVE_PANEL_ACTION = "five_panel_action"
    FOUR_PANEL_CINEMATIC = "four_panel_cinematic"
    DIAGONAL_SLASH_BATTLE = "diagonal_slash_battle"
    SHONEN_CLIMAX_SPREAD = "shonen_climax_spread"
    NINE_PANEL_GRID = "nine_panel_grid"
    TWO_PANEL_DRAMATIC_SPREAD = "two_panel_dramatic_spread"
    SEVEN_PANEL_ACTION_BURST = "seven_panel_action_burst"
    EIGHT_PANEL_MANHWA = "eight_panel_manhwa"
    THREE_TIER_ACTION_SLANT = "three_tier_action_slant"
    CUSTOM = "custom"

class MarginSpec(BaseModel):
    """Page margins defining the outer boundary of the usable panel area."""
    top: float = Field(default=120.0, ge=0.0, description="Top margin inset in pixels")
    bottom: float = Field(default=120.0, ge=0.0, description="Bottom margin inset in pixels")
    left: float = Field(default=100.0, ge=0.0, description="Left margin inset in pixels")
    right: float = Field(default=100.0, ge=0.0, description="Right margin inset in pixels")

    @classmethod
    def uniform(cls, amount_px: float) -> "MarginSpec":
        if amount_px < 0:
            raise InvalidDimensionError("Margin insets must be non-negative")
        return cls(top=amount_px, bottom=amount_px, left=amount_px, right=amount_px)

    @property
    def horizontal_total(self) -> float:
        return self.left + self.right

    @property
    def vertical_total(self) -> float:
        return self.top + self.bottom

class GutterSpec(BaseModel):
    """Spacing between adjacent panels."""
    horizontal: float = Field(default=40.0, ge=0.0, description="Horizontal gutter (between columns) in pixels")
    vertical: float = Field(default=40.0, ge=0.0, description="Vertical gutter (between rows) in pixels")

    @classmethod
    def uniform(cls, amount_px: float) -> "GutterSpec":
        if amount_px < 0:
            raise InvalidDimensionError("Gutter spacing must be non-negative")
        return cls(horizontal=amount_px, vertical=amount_px)

class BleedSpec(BaseModel):
    """Bleed margins extending outside the trim edge for borderless printing."""
    top: float = Field(default=35.0, ge=0.0, description="Top bleed extension in pixels")
    bottom: float = Field(default=35.0, ge=0.0, description="Bottom bleed extension in pixels")
    left: float = Field(default=35.0, ge=0.0, description="Left bleed extension in pixels")
    right: float = Field(default=35.0, ge=0.0, description="Right bleed extension in pixels")

    @classmethod
    def uniform(cls, amount_px: float) -> "BleedSpec":
        if amount_px < 0:
            raise InvalidDimensionError("Bleed extent must be non-negative")
        return cls(top=amount_px, bottom=amount_px, left=amount_px, right=amount_px)

    @property
    def is_zero(self) -> bool:
        return self.top == 0.0 and self.bottom == 0.0 and self.left == 0.0 and self.right == 0.0

class SafeAreaSpec(BaseModel):
    """Safe area inset inside trim edge to guarantee text and speech bubbles are not trimmed."""
    top: float = Field(default=60.0, ge=0.0, description="Top safe area inset from trim edge")
    bottom: float = Field(default=60.0, ge=0.0, description="Bottom safe area inset from trim edge")
    left: float = Field(default=50.0, ge=0.0, description="Left safe area inset from trim edge")
    right: float = Field(default=50.0, ge=0.0, description="Right safe area inset from trim edge")

    @classmethod
    def uniform(cls, amount_px: float) -> "SafeAreaSpec":
        if amount_px < 0:
            raise InvalidDimensionError("Safe area insets must be non-negative")
        return cls(top=amount_px, bottom=amount_px, left=amount_px, right=amount_px)

    @property
    def horizontal_total(self) -> float:
        return self.left + self.right

    @property
    def vertical_total(self) -> float:
        return self.top + self.bottom

class CanvasSpec(BaseModel):
    """
    Authoritative specification of canvas spatial extents, resolution, print margins, and bleeds.
    Dimensions are expressed in exact screen/render pixels at declared DPI.
    """
    page_format: PageFormat = Field(default=PageFormat.A4)
    width_px: float = Field(default=2480.0, gt=0.0, description="Page trim width in pixels")
    height_px: float = Field(default=3508.0, gt=0.0, description="Page trim height in pixels")
    dpi: float = Field(default=300.0, gt=0.0, description="Pixel density (dots per inch)")
    color_space: ColorSpace = Field(default=ColorSpace.SRGB)
    background_color: str = Field(default="#FFFFFF", description="Hex or CSS color representation")
    margins: MarginSpec = Field(default_factory=MarginSpec)
    gutters: GutterSpec = Field(default_factory=GutterSpec)
    bleed: BleedSpec = Field(default_factory=BleedSpec)
    safe_area: SafeAreaSpec = Field(default_factory=SafeAreaSpec)

    @model_validator(mode="after")
    def validate_canvas_bounds_and_safety(self) -> "CanvasSpec":
        w = self.width_px
        h = self.height_px

        # 1. Allocation safety checks
        if w > MAX_CANVAS_WIDTH_PX or h > MAX_CANVAS_HEIGHT_PX:
            raise AllocationLimitExceededError(
                f"Requested canvas dimensions ({w}x{h} px) exceed maximum permitted dimensions ({MAX_CANVAS_WIDTH_PX}x{MAX_CANVAS_HEIGHT_PX} px)",
                details={"width": w, "height": h, "max_w": MAX_CANVAS_WIDTH_PX, "max_h": MAX_CANVAS_HEIGHT_PX}
            )

        total_px = w * h
        if total_px > MAX_TOTAL_PIXELS:
            raise AllocationLimitExceededError(
                f"Requested total pixel count ({total_px:.0f} px) exceeds maximum safe allocation ({MAX_TOTAL_PIXELS:.0f} px)",
                details={"total_pixels": total_px, "max_pixels": MAX_TOTAL_PIXELS}
            )

        # 2. Margins containment check
        if self.margins.horizontal_total >= w:
            raise ImpossibleLayoutError(
                f"Horizontal margins ({self.margins.horizontal_total} px) must be strictly less than canvas width ({w} px)",
                details={"margins": self.margins.model_dump(), "canvas_width": w}
            )
        if self.margins.vertical_total >= h:
            raise ImpossibleLayoutError(
                f"Vertical margins ({self.margins.vertical_total} px) must be strictly less than canvas height ({h} px)",
                details={"margins": self.margins.model_dump(), "canvas_height": h}
            )

        # 3. Safe area containment check
        if self.safe_area.horizontal_total >= w:
            raise ImpossibleLayoutError(
                f"Horizontal safe area insets ({self.safe_area.horizontal_total} px) must be strictly less than canvas width ({w} px)",
                details={"safe_area": self.safe_area.model_dump(), "canvas_width": w}
            )
        if self.safe_area.vertical_total >= h:
            raise ImpossibleLayoutError(
                f"Vertical safe area insets ({self.safe_area.vertical_total} px) must be strictly less than canvas height ({h} px)",
                details={"safe_area": self.safe_area.model_dump(), "canvas_height": h}
            )

        return self

    @classmethod
    def create_a4(cls, dpi: float = 300.0, **kwargs) -> "CanvasSpec":
        """A4 format: 210 x 297 mm."""
        w = round(mm_to_px(210.0, dpi))
        h = round(mm_to_px(297.0, dpi))
        return cls(page_format=PageFormat.A4, width_px=float(w), height_px=float(h), dpi=dpi, **kwargs)

    @classmethod
    def create_b5(cls, dpi: float = 300.0, **kwargs) -> "CanvasSpec":
        """Japanese standard manga B5: 182 x 257 mm."""
        w = round(mm_to_px(182.0, dpi))
        h = round(mm_to_px(257.0, dpi))
        return cls(page_format=PageFormat.B5, width_px=float(w), height_px=float(h), dpi=dpi, **kwargs)

    @classmethod
    def create_us_comic(cls, dpi: float = 300.0, **kwargs) -> "CanvasSpec":
        """Standard US comic: 6.625 x 10.187 inches."""
        w = round(6.625 * dpi)
        h = round(10.187 * dpi)
        return cls(page_format=PageFormat.US_COMIC, width_px=float(w), height_px=float(h), dpi=dpi, **kwargs)

    @classmethod
    def create_webtoon(cls, width_px: float = 800.0, height_px: float = 4000.0, dpi: float = 72.0, **kwargs) -> "CanvasSpec":
        """Vertical webtoon format: fixed width, extended vertical height."""
        # Default webtoon gutters and margins
        margins = kwargs.pop("margins", MarginSpec(top=80.0, bottom=80.0, left=40.0, right=40.0))
        gutters = kwargs.pop("gutters", GutterSpec(horizontal=0.0, vertical=80.0))
        bleed = kwargs.pop("bleed", BleedSpec.uniform(0.0))
        safe_area = kwargs.pop("safe_area", SafeAreaSpec(top=40.0, bottom=40.0, left=20.0, right=20.0))
        return cls(
            page_format=PageFormat.WEBTOON_VERTICAL,
            width_px=width_px,
            height_px=height_px,
            dpi=dpi,
            margins=margins,
            gutters=gutters,
            bleed=bleed,
            safe_area=safe_area,
            **kwargs
        )

class PageSpec(BaseModel):
    """Specification of an individual page within a comic chapter or volume."""
    page_id: str = Field(..., description="Canonical page identifier, e.g., 'page_001'")
    page_number: int = Field(default=1, ge=1, description="1-indexed sequence number in chapter")
    page_type: PageType = Field(default=PageType.SINGLE)
    reading_direction: ReadingDirection = Field(default=ReadingDirection.LTR)

class PanelSlot(BaseModel):
    """
    A single bounded panel region within a page layout.
    Stores bounding Rect and optional polygon vertices for dynamic action cuts.
    """
    panel_id: str = Field(..., description="Canonical panel identifier, e.g., 'panel_01'")
    reading_order: int = Field(..., ge=1, description="1-based sequence indicating traversal order")
    rect: Rect = Field(..., description="Axis-aligned bounding box in PAGE coordinate space")
    polygon: Optional[List[Point]] = Field(default=None, description="Optional polygon vertices for non-rectangular cuts")
    is_full_bleed: bool = Field(default=False, description="Whether panel intentionally bleeds to page edge")
    bleed_edges: List[str] = Field(default_factory=list, description="Specific bleeding edges: ['top', 'bottom', 'left', 'right']")
    is_intentional_overlap: bool = Field(default=False, description="Legacy flag; does not by itself authorize overlap with every other panel")
    intentional_overlap_with: List[str] = Field(default_factory=list, description="Explicit panel IDs this slot is allowed to overlap")
    overlap_reason: Optional[str] = Field(default=None, description="Required rationale for each declared intentional overlap")
    z_index: int = Field(default=0, description="Rendering layer stacking order")
    descriptor: Optional[MultiAxisPanelDescriptor] = Field(
        default=None,
        description="Optional multi-axis narrative, framing, and layout descriptor"
    )

    @model_validator(mode="after")
    def validate_explicit_overlap_declaration(self) -> "PanelSlot":
        if self.panel_id in self.intentional_overlap_with:
            raise ValueError("A panel cannot declare an intentional overlap with itself.")
        if len(self.intentional_overlap_with) != len(set(self.intentional_overlap_with)):
            raise ValueError("intentional_overlap_with cannot contain duplicate panel IDs.")
        if self.intentional_overlap_with and not (self.overlap_reason and self.overlap_reason.strip()):
            raise ValueError("overlap_reason is required when intentional_overlap_with is non-empty.")
        valid_edges = {"top", "bottom", "left", "right"}
        if not set(self.bleed_edges).issubset(valid_edges):
            raise ValueError("bleed_edges may contain only top, bottom, left, and right.")
        return self

    @property
    def width(self) -> float:
        return self.rect.width

    @property
    def height(self) -> float:
        return self.rect.height

    @property
    def aspect_ratio(self) -> float:
        return self.rect.aspect_ratio

    @property
    def area(self) -> float:
        return self.rect.width * self.rect.height

    @property
    def has_polygon(self) -> bool:
        return bool(self.polygon and len(self.polygon) >= 3)

class ValidationDiagnostic(BaseModel):
    """Structured geometry validation warning or error."""
    severity: str = Field(default="error", description="'error', 'warning', or 'info'")
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    panel_id: Optional[str] = None
    observed_bounds: Optional[Dict[str, Any]] = None
    allowed_bounds: Optional[Dict[str, Any]] = None

class CanvasLayoutResult(BaseModel):
    """
    Authoritative canonical geometry result produced by the Canvas Generation Engine (E2).
    Acts as the single source of truth for both SVG and raster preview representations.
    """
    canvas_id: str = Field(..., description="Unique canvas layout result identifier")
    canvas_spec: CanvasSpec
    page_spec: PageSpec
    template_id: LayoutTemplateId
    template_version: str = Field(default="1.0.0")
    layout_preset_id: Optional[str] = Field(default=None, description="Stable catalogue recipe used to create this layout")
    reading_direction: ReadingDirection
    panel_slots: List[PanelSlot] = Field(default_factory=list)
    trim_box: Rect = Field(..., description="Page boundary without bleed: [0, 0, width, height)")
    bleed_box: Rect = Field(..., description="Page boundary expanded by bleed: [-b.l, -b.t, width + b.l + b.r, height + b.t + b.b)")
    safe_area_box: Rect = Field(..., description="Page boundary contracted by safe insets: [s.l, s.t, width - s.l - s.r, height - s.t - s.b)")
    usable_box: Rect = Field(..., description="Inner printable area within margins: [m.l, m.t, width - m.l - m.r, height - m.t - m.b)")
    reading_order_panel_ids: List[str] = Field(default_factory=list)
    diagnostics: List[ValidationDiagnostic] = Field(default_factory=list)

    @property
    def panel_count(self) -> int:
        return len(self.panel_slots)

    def get_panel(self, panel_id: str) -> Optional[PanelSlot]:
        for p in self.panel_slots:
            if p.panel_id == panel_id:
                return p
        return None

    def to_engine_output(self, artifact_id: str = "art_canvas_spec") -> CanvasGenerationOutput:
        """Adapts this canonical layout result to the shared engine contract CanvasGenerationOutput."""
        return CanvasGenerationOutput(
            canvas_spec_artifact_id=artifact_id,
            dimensions=Size(width=self.canvas_spec.width_px, height=self.canvas_spec.height_px),
            dpi=self.canvas_spec.dpi,
            panel_slots=[p.rect for p in self.panel_slots],
            safe_area=self.safe_area_box,
            bleed_box=self.bleed_box,
            reading_order_panel_ids=self.reading_order_panel_ids,
        )
