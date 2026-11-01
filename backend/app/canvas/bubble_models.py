"""
InkLoop Speech Bubble Models & Enums.
Defines expressive bubble shapes, tail styles, accents, and geometry contracts.
"""
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

from app.contracts.geometry import Rect, Point


class BubbleShape(str, Enum):
    """Expressive speech, emotion, power, and reaction bubble shapes."""
    OVAL = "oval"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    THOUGHT_CLOUD = "thought_cloud"
    SHOUT_BURST = "shout_burst"
    EXPLOSIVE_BLAST = "explosive_blast"
    FEAR_TREMBLE = "fear_tremble"
    AFFECTION_HEART = "affection_heart"
    SPLAT_SURPRISE = "splat_surprise"
    ELECTRIC_ROBOTIC = "electric_robotic"
    TILTED_BANNER = "tilted_banner"
    SPEEDLINE_AURA = "speedline_aura"
    CONNECTED_LOBES = "connected_lobes"
    RADIO_BROADCAST_ZIGZAG = "radio_broadcast_zigzag"
    FOLDED_RIBBON_3D = "folded_ribbon_3d"
    DARK_AURA_GHOST = "dark_aura_ghost"
    ICICLE_FROST = "icicle_frost"
    WHISPER_CLOUD_SOFT = "whisper_cloud_soft"
    DOUBLE_BORDER_IMPACT = "double_border_impact"
    DROPLET_TEAR_SAD = "droplet_tear_sad"
    GLITCH_DIGITAL_CRT = "glitch_digital_crt"
    SCALLOPED_FLOWER = "scalloped_flower"
    SPIKY_RING_SCREAM = "spiky_ring_scream"
    HEAVY_WEIGHT_EMPHASIS = "heavy_weight_emphasis"
    NONE = "none"


class TailType(str, Enum):
    """Dynamic pointer and connection styles."""
    SMOOTH_POINTER = "smooth_pointer"
    LIGHTNING_BOLT = "lightning_bolt"
    BUBBLE_CHAIN = "bubble_chain"
    WHISPER_DASHED = "whisper_dashed"
    SMOKE_PUFF = "smoke_puff"
    DUAL_POINTER = "dual_pointer"
    OFF_SCREEN_POINTER = "off_screen_pointer"
    CURVED_HOOK_TAIL = "curved_hook_tail"
    ZIGZAG_ANTENNA = "zigzag_antenna"
    NONE = "none"


class BubbleAccent(str, Enum):
    """Comic and manga emotional and action accent decorators."""
    NONE = "none"
    SPEEDLINE_NEEDLES = "speedline_needles"
    SPARKLES = "sparkles"
    SWEAT_DROP = "sweat_drop"
    SHOCK_MARKS = "shock_marks"
    ANGER_VEIN_CROSS = "anger_vein_cross"
    HEART_FLUTTER = "heart_flutter"
    DIZZINESS_SWIRL = "dizziness_swirl"
    ELECTRIC_SPARKS = "electric_sparks"


class BubbleStyleRecommendation(BaseModel):
    """Recommended bubble styling deduced autonomously from narrative context."""
    shape: BubbleShape
    tail_type: TailType
    halftone_shadow: bool = False
    accent: BubbleAccent = BubbleAccent.NONE
    inverted_dark_mode: bool = False
    interior_screentone: bool = False
    stroke_width: float = 2.5
    stroke_dash: str = ""
    fill_color: str = "#FFFFFF"
    stroke_color: str = "#111111"
    padding_x: float = 24.0
    padding_y: float = 18.0
    reasoning: str = ""


class BubbleVectorGeometry(BaseModel):
    """Parametric vector paths ready for SVG rendering and headless export."""
    bubble_path: str
    tail_path: Optional[str] = None
    secondary_tail_path: Optional[str] = None
    double_stroke_path: Optional[str] = None
    shadow_path: Optional[str] = None
    accent_paths: List[str] = Field(default_factory=list)
    ribbon_fold_paths: List[str] = Field(default_factory=list)
    tail_chain_circles: List[Tuple[float, float, float]] = Field(default_factory=list)  # (cx, cy, r)
    bounds: Rect
    inner_text_rect: Rect
    tail_tip: Optional[Point] = None
