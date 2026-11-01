"""
InkLoop Canvas Generation Engine (E2) - Multi-Axis Panel Descriptors.
Implementation-oriented multi-axis taxonomy based on comics scholarship
(Cohn 2013/2014/2018, Natsume Fusanosuke 2021, CO-MIX 2022, McCloud).

Separates:
- Axis A: Page and layout arrangement (ECS: External Compositional Structure)
- Axis B: Individual panel geometry and shape
- Axis C: Frame, page-edge, and boundary treatment
- Axis D: Narrative role (VNG: Visual Narrative Grammar)
- Axis E: Framing scale, camera angle, and point of view (ICS: Internal Compositional Structure)
- Axis F: Adjacent panel relationship (Transitions)
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# Axis A: Page and Layout Arrangement
# ==============================================================================
class LayoutRelation(str, Enum):
    """How the panel relates spatially to neighboring panels on the page/canvas."""
    REGULAR_GRID = "regular_grid"               # Uniform rows and columns
    UNEQUAL_GRID = "unequal_grid"               # Asymmetric rows/cols with varying ratios
    TIERED = "tiered"                           # Horizontal band containing one or more panels
    HORIZONTAL_STAGGER = "horizontal_stagger"   # Misaligned vertical edges along a continuous row
    VERTICAL_STAGGER = "vertical_stagger"       # Misaligned horizontal edges along columns
    BLOCKAGE = "blockage"                       # Tall panel beside a stack of smaller panels
    WIDESCREEN_STACK = "widescreen_stack"       # Full-width horizontal panels stacked vertically
    VERTICAL_COLUMN = "vertical_column"         # Tall vertical columns sequencing downward
    INSET = "inset"                             # Smaller panel enclosed inside a larger dominant panel
    OVERLAPPING = "overlapping"                 # Physical intersection/overlap with another panel
    FLOATING = "floating"                       # Detached panel surrounded by whitespace/art
    DIAGONAL = "diagonal"                       # Slanted tier or diagonal boundary cuts
    MIXED_DIAGONAL = "mixed_diagonal"           # Complex interlocking polygonal layout
    RADIAL = "radial"                           # Composition converging on a central focal point
    SPIRAL = "spiral"                           # Circular or spiral reading path
    SPLIT_VIEW = "split_view"                   # Concurrent simultaneous subviews or divided regions
    MONTAGE = "montage"                         # Compressed assembly of aspects/moments
    COMPOUND = "compound"                       # Grouped multi-panel sub-unit
    FULL_PAGE_SPLASH = "full_page_splash"       # Dominant full-page single composition
    DOUBLE_PAGE_SPREAD = "double_page_spread"   # Two-page opening (mi-hiraki)
    FOUR_KOMA = "four_koma"                     # 4-panel vertical sequence (ki-shō-ten-ketsu)
    VERTICAL_SCROLL = "vertical_scroll"         # Long-scroll continuous webtoon format


# ==============================================================================
# Axis B: Individual Panel Geometry and Shape
# ==============================================================================
class PanelShapeType(str, Enum):
    """The 2D geometric boundary category of an individual panel region."""
    SQUARE = "square"                           # Near 1:1 aspect ratio
    HORIZONTAL_RECTANGLE = "horizontal_rectangle" # Width > Height
    VERTICAL_RECTANGLE = "vertical_rectangle"   # Height > Width
    PANORAMIC = "panoramic"                     # Ultra-wide landscape (aspect ratio >= 2.2)
    NARROW_STRIP = "narrow_strip"               # Thin horizontal sliver or vertical strip
    TRIANGLE_WEDGE = "triangle_wedge"           # 3-vertex polygon
    TRAPEZOID = "trapezoid"                     # 4-vertex polygon with one parallel pair
    PARALLELOGRAM = "parallelogram"             # 4-vertex polygon with tilted parallel edges
    GENERAL_POLYGON = "general_polygon"         # Arbitrary N-sided convex or concave polygon
    CIRCULAR = "circular"                       # Circle boundary
    OVAL = "oval"                               # Elliptical boundary
    CURVED_ORGANIC = "curved_organic"           # Freeform bezier or curved edge
    HYBRID = "hybrid"                           # Multi-geometry composite
    BORDERLESS = "borderless"                   # Implicit boundary without a solid closed stroke
    CUSTOM_PATH = "custom_path"                 # Vector-defined custom path


# ==============================================================================
# Axis C: Frame, Page-Edge, and Boundary Treatment
# ==============================================================================
class FrameStyle(str, Enum):
    """Visible boundary line style separating the panel from surrounding content."""
    CLOSED = "closed"                           # Complete, unbroken border stroke
    BORDERLESS = "borderless"                   # No boundary stroke; defined by art/whitespace
    PARTIAL = "partial"                         # One or more sides left open
    BROKEN = "broken"                           # Stroke intentionally interrupted by art/text
    DASHED = "dashed"                           # Dashed or dotted border (e.g. flashback, radio)
    DECORATIVE = "decorative"                   # Textured, rough, or ornamental stroke


class GutterPolicy(str, Enum):
    """Spatial separation policy from adjacent panels."""
    STANDARD = "standard"                       # Standard uniform gutter spacing
    ZERO_GUTTER = "zero_gutter"                 # Tight abutting panels with no empty space
    SHARED_EDGE = "shared_edge"                 # Single common stroke dividing two panels
    NON_WHITE = "non_white"                     # Colored, patterned, or textured gutter
    VARIABLE_SCROLL = "variable_scroll"         # Pacing-controlled vertical webtoon gap


class PanelBoundaryTreatment(BaseModel):
    """Detailed boundary and edge specifications for a panel."""
    frame_style: FrameStyle = Field(default=FrameStyle.CLOSED)
    gutter_policy: GutterPolicy = Field(default=GutterPolicy.STANDARD)
    bleed_to_trim: bool = Field(default=False, description="Artwork extends to print trim edge")
    full_bleed: bool = Field(default=False, description="Artwork extends beyond trim into printer bleed")
    bleed_edges: List[str] = Field(default_factory=list, description="['top', 'bottom', 'left', 'right']")
    frame_break_art: bool = Field(default=False, description="Foreground character/object breaks out of frame")
    stroke_width_px: float = Field(default=2.0, ge=0.0, description="Border stroke thickness in pixels")
    stroke_color: str = Field(default="#000000", description="Hex stroke color")


# ==============================================================================
# Axis D: Narrative Role (Visual Narrative Grammar - Cohn 2013)
# ==============================================================================
class VNGRole(str, Enum):
    """Formal grammatical role in visual narrative structure (Neil Cohn 2013)."""
    ESTABLISHER = "establisher"                 # Sets up entities, state, or spatial environment (E)
    INITIAL = "initial"                         # Initiates action path, tension, or conflict (I)
    PROLONGATION = "prolongation"               # Extends developing action between start and climax (L)
    PEAK = "peak"                               # Decisive point, climax, or main event (P)
    RELEASE = "release"                         # Resolution, dissipation, aftermath, or response (R)
    UNSPECIFIED = "unspecified"                 # Role not formally declared


class NarrativePlanningTag(str, Enum):
    """Operational authoring tags for storytelling beats and panel intent."""
    ESTABLISHING_SHOT = "establishing_shot"     # Wide environment / location reveal
    ACTION_PREPARATION = "action_preparation"   # Wind-up, aim, stance before action
    ACTION_CONTINUATION = "action_continuation" # Mid-motion, traversal, trajectory
    IMPACT_CONTACT = "impact_contact"           # Strike, collision, decisive explosion
    REACTION = "reaction"                       # Character emotional or physical response
    AFTERMATH_RESULT = "aftermath_result"       # Smoke clearing, wound, settled state
    CLOSE_EMOTIONAL = "close_emotional"         # Micro-expression, eye, tear, grit
    DETAIL_INSERT = "detail_insert"             # Specific clue, weapon, hand, token, switch
    POV = "pov"                                 # Subjective point-of-view shot
    REVERSE_SHOT = "reverse_shot"               # Alternating viewpoint in dialogue
    TWO_SHOT_DIALOGUE = "two_shot_dialogue"     # Two characters interacting
    SILENT_BEAT = "silent_beat"                 # Deliberate pause / compression / contemplation
    REVEAL = "reveal"                           # Dramatic disclosure of hidden entity
    TRANSITION_TIME_PLACE = "transition_time_place" # Passage of time or change of setting
    CUTAWAY = "cutaway"                         # Simultaneous off-screen event or parallel beat
    FLASHBACK = "flashback"                     # Temporal regression / memory layer
    SYMBOLIC_METAPHOR = "symbolic_metaphor"     # Figurative / non-literal imagery
    COMEDIC_DEFORMED = "comedic_deformed"       # Chibi / exaggerated comedic expression


class NarrativeFunction(str, Enum):
    """Story beat intent, independent from shot scale and frame geometry."""
    ESTABLISHING = "establishing"
    ACTION_PREPARATION = "action_preparation"
    ACTION_CONTINUATION = "action_continuation"
    IMPACT = "impact"
    REVEAL = "reveal"
    REACTION = "reaction"
    AFTERMATH = "aftermath"
    DETAIL = "detail"
    DIALOGUE = "dialogue"
    SILENT = "silent"
    TRANSITION = "transition"
    SYMBOLIC = "symbolic"
    CUTAWAY = "cutaway"


class ShotType(str, Enum):
    """Narrative camera choice; intentionally distinct from subject scale."""
    ESTABLISHING = "establishing"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    REACTION = "reaction"
    IMPACT = "impact"
    INSERT = "insert"
    SILENT = "silent"
    TRANSITION = "transition"
    POV = "pov"
    TWO_SHOT = "two_shot"
    DRAMATIC_WIDE = "dramatic_wide"


class CompositionType(str, Enum):
    """Placement of subjects and visual weight inside the panel frame."""
    ENVIRONMENTAL_NEGATIVE_SPACE = "environmental_negative_space"
    LEADING_LINES = "leading_lines"
    DIAGONAL_ACTION = "diagonal_action"
    OFF_CENTER_REVEAL = "off_center_reveal"
    FACE_FOCUSED = "face_focused"
    DETAIL_FOCUSED = "detail_focused"
    TWO_SHOT_BALANCED = "two_shot_balanced"
    STILLNESS_NEGATIVE_SPACE = "stillness_negative_space"
    AFTERMATH_NEGATIVE_SPACE = "aftermath_negative_space"
    SYMBOLIC = "symbolic"
    RULE_OF_THIRDS = "rule_of_thirds"
    CENTERED = "centered"
    CUSTOM = "custom"


class CameraPosition(str, Enum):
    """Camera placement relative to the subject, separate from vertical angle."""
    ENVIRONMENTAL = "environmental"
    FRONT = "front"
    THREE_QUARTER = "three_quarter"
    PROFILE = "profile"
    REAR = "rear"
    OVER_THE_SHOULDER = "over_the_shoulder"
    SUBJECTIVE_POV = "subjective_pov"


class PanelNarrativeDescriptor(BaseModel):
    """Narrative function, story role, and temporal properties of a panel."""
    vng_role: VNGRole = Field(default=VNGRole.UNSPECIFIED)
    narrative_function: Optional[NarrativeFunction] = Field(default=None)
    function_tags: List[NarrativePlanningTag] = Field(default_factory=list)
    time_relation: str = Field(default="continuous", description="continuous, elapsed, flashback, simultaneous")
    scene_beat_description: Optional[str] = Field(default=None, description="Authoring summary of panel beat")
    is_silent: bool = Field(default=False, description="Panel contains no dialogue or narrative text")


# ==============================================================================
# Axis E: Framing Scale, Camera Angle, and Internal Composition
# ==============================================================================
class FramingScale(str, Enum):
    """Subject scale relative to frame boundaries."""
    EXTREME_LONG_SHOT = "extreme_long_shot"     # Subject tiny; vast landscape/cityscape
    LONG_SHOT = "long_shot"                     # Full subject with extensive surrounding environment
    FULL_SHOT = "full_shot"                     # Complete figure visible from head to toe
    MEDIUM_LONG_SHOT = "medium_long_shot"       # Figure from knees upward (cowboy shot)
    MEDIUM_SHOT = "medium_shot"                 # Figure from waist upward
    MEDIUM_CLOSE_UP = "medium_close_up"         # Figure from chest/shoulders upward
    CLOSE_UP = "close_up"                       # Face, head, or single isolated object
    EXTREME_CLOSE_UP = "extreme_close_up"       # Eyes, mouth, trigger, lock, micro-detail


class CameraAngle(str, Enum):
    """Vertical and horizontal angle of view on the represented subject."""
    EYE_LEVEL = "eye_level"                     # Neutral horizontal sightline
    HIGH_ANGLE = "high_angle"                   # Camera looking down on subject (vulnerability/scale)
    LOW_ANGLE = "low_angle"                     # Camera looking up at subject (dominance/power)
    OVERHEAD = "overhead"                       # True bird's-eye 90-degree downward perspective
    GROUND_LEVEL = "ground_level"               # Worm's-eye perspective from floor level
    DUTCH_CANTED = "dutch_canted"               # Tilted horizon creating psychological unease/motion
    POV = "pov"                                 # Character first-person viewpoint
    OVER_THE_SHOULDER = "over_the_shoulder"     # Third-person framing past foreground character


class SubjectOrientation(str, Enum):
    """Subject facing angle."""
    FRONTAL = "frontal"                         # Facing camera directly
    THREE_QUARTER = "three_quarter"             # Turned 45 degrees
    PROFILE = "profile"                         # Pure side view (90 degrees)
    REAR = "rear"                               # Facing away from camera (back view)


class PanelFramingDescriptor(BaseModel):
    """Cinematic camera framing and internal composition parameters."""
    scale: FramingScale = Field(default=FramingScale.MEDIUM_SHOT)
    shot_type: Optional[ShotType] = Field(default=None, description="Narrative shot choice, separate from subject scale")
    angle: CameraAngle = Field(default=CameraAngle.EYE_LEVEL)
    camera_position: Optional[CameraPosition] = Field(default=None)
    composition_type: Optional[CompositionType] = Field(default=None)
    emotional_intent: Optional[str] = Field(default=None, max_length=500)
    visual_focus: Optional[str] = Field(default=None, max_length=500)
    orientation: Optional[SubjectOrientation] = Field(default=SubjectOrientation.THREE_QUARTER)
    focal_point_norm: Optional[Dict[str, float]] = Field(
        default=None,
        description="Normalized focal point [0..1] x and y for E3 smart cropping"
    )
    camera_movement_hint: Optional[str] = Field(default=None, description="pan, tilt, zoom_in, zoom_out, static")


# ==============================================================================
# Axis F: Inter-Panel Transitions (Scott McCloud 1993)
# ==============================================================================
class PanelTransitionType(str, Enum):
    """Qualitative narrative relationship between this panel and the preceding panel."""
    MOMENT_TO_MOMENT = "moment_to_moment"       # Minimal time elapsed; subtle movement or blink
    ACTION_TO_ACTION = "action_to_action"       # Same subject progressing through action phases
    SUBJECT_TO_SUBJECT = "subject_to_subject"   # Shifts between different subjects in the same scene
    SCENE_TO_SCENE = "scene_to_scene"           # Significant jump across time and/or spatial location
    ASPECT_TO_ASPECT = "aspect_to_aspect"       # Wandering eye surveying different aspects of a mood/place
    NON_SEQUITUR = "non_sequitur"               # Associative / no direct logical relationship
    FIRST_PANEL_IN_SCENE = "first_panel_in_scene" # No preceding panel in current narrative sequence


# ==============================================================================
# Unified Multi-Axis Panel Descriptor
# ==============================================================================
class MultiAxisPanelDescriptor(BaseModel):
    """
    Authoritative InkLoop multi-axis panel descriptor.
    Binds spatial layout, geometry, boundary treatment, narrative role,
    camera framing, and inter-panel transitions into a single structured model.
    """
    panel_id: str = Field(..., description="Canonical panel identifier (e.g. 'panel_01')")
    reading_order_index: int = Field(..., ge=1, description="1-indexed sequence order")

    # The Six Orthogonal Axes
    layout_relation: LayoutRelation = Field(default=LayoutRelation.REGULAR_GRID)
    shape_type: PanelShapeType = Field(default=PanelShapeType.VERTICAL_RECTANGLE)
    boundary: PanelBoundaryTreatment = Field(default_factory=PanelBoundaryTreatment)
    narrative: PanelNarrativeDescriptor = Field(default_factory=PanelNarrativeDescriptor)
    framing: PanelFramingDescriptor = Field(default_factory=PanelFramingDescriptor)
    transition_from_previous: PanelTransitionType = Field(default=PanelTransitionType.ACTION_TO_ACTION)

    # Hierarchical Layout & Layer Grouping
    group_id: Optional[str] = Field(default=None, description="Tier or cluster grouping ID (e.g. 'tier_01')")
    parent_panel_id: Optional[str] = Field(default=None, description="Parent panel ID if this is an inset panel")
    z_index: int = Field(default=0, description="Stacking layer order")
    is_intentional_overlap: bool = Field(default=False, description="Explicit approval for overlapping another panel")

    # Authoring & Lineage Metadata
    source_reference_ids: List[str] = Field(default_factory=list, description="IDs of reference layouts or sketches")
    notes: Optional[str] = Field(default=None, description="Art director or authoring remarks")

    @model_validator(mode="after")
    def validate_multi_axis_integrity(self) -> "MultiAxisPanelDescriptor":
        # 1. Inset panels must have a declared parent_panel_id
        if self.layout_relation == LayoutRelation.INSET and not self.parent_panel_id:
            raise ValueError(f"Panel '{self.panel_id}' declares 'layout_relation=INSET' but lacks 'parent_panel_id'.")

        # 2. Bleed panels must declare bleed edges or boundary bleed flags
        if (self.boundary.bleed_to_trim or self.boundary.full_bleed) and not self.boundary.bleed_edges:
            # Default to full edges if unstated
            self.boundary.bleed_edges = ["top", "bottom", "left", "right"]

        return self
