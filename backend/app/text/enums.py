"""
InkLoop Text Generation Engine - Enums & Classifications (Milestone M5 / Workstream E4).
Defines structured block kinds, delivery types, language/direction codes,
diagnostic severities, and source modes.
"""
from enum import Enum


class ScriptBlockKind(str, Enum):
    """Semantic category of a script text block in comic production."""
    DIALOGUE = "dialogue"
    NARRATION = "narration"
    CAPTION = "caption"
    MONOLOGUE = "monologue"
    OFF_PANEL = "off_panel"
    SFX = "sfx"


class DialogueDelivery(str, Enum):
    """Manner of speech delivery influencing typography and bubble styling in E5/E6."""
    NORMAL = "normal"
    WHISPER = "whisper"
    SHOUT = "shout"
    INTERRUPTED = "interrupted"
    FADING = "fading"
    REMOTE_DEVICE = "remote_device"  # Radio, phone, intercom, comms
    ROBOTIC = "robotic"
    OFF_PANEL = "off_panel"
    SINGING = "singing"


class CaptionKind(str, Enum):
    """Type of narrative caption."""
    SCENE_SETTING = "scene_setting"       # e.g., "The Old Cairo Alleyway - 1984"
    TIME_TRANSITION = "time_transition"   # e.g., "Three Hours Later..."
    LOCATION_STAMP = "location_stamp"     # e.g., "Al-Mu'izz Street"
    INTERNAL_CONTEXT = "internal_context" # Narrative commentary or omniscient note


class SFXCategory(str, Enum):
    """Semantic category of an onomatopoeia or sound-effect word."""
    IMPACT = "impact"         # THUD, BAM, CRASH, طاخ
    MOVEMENT = "movement"     # WHOOSH, SWISH, RUSH, فشش
    VOCAL = "vocal"           # GASP, SIGH, SCREAM, صرخة
    ENVIRONMENT = "environment" # RUMBLE, RAIN, WIND, حفيف
    ENERGY = "energy"         # ZAP, HUM, CRACKLE, طنين
    MECHANICAL = "mechanical" # CLICK, CLANK, TICK, تكتكة


class TextLanguage(str, Enum):
    """Primary language classification for typography selection and shaping."""
    AR = "ar"       # Arabic (RTL)
    EN = "en"       # English (LTR)
    MIXED = "mixed" # Bi-directional Arabic & English
    UNSPECIFIED = "und"


class TextDirection(str, Enum):
    """Semantic reading and layout direction."""
    RTL = "rtl"     # Right-to-Left (Arabic / Manga script)
    LTR = "ltr"     # Left-to-Right (Western comic script)
    AUTO = "auto"   # Derived from Unicode script properties


class SourceMode(str, Enum):
    """Provenance origin of the text content."""
    USER_EXACT = "user_exact"         # Immutable user-authored text preserved code-point by code-point
    USER_DERIVED = "user_derived"     # Summarized or adapted from user story text
    MODEL_GENERATED = "model_generated" # Proposed by text generation model
    SCRIPT_IMPORT = "script_import"   # Ingested from external structured screenplay / comic script


class DiagnosticSeverity(str, Enum):
    """Severity level of validation diagnostic."""
    ERROR = "error"     # Hard rejection; block cannot be accepted without repair
    WARNING = "warning" # Requires human review; does not block automated pipeline
    INFO = "info"       # Informational note (e.g. length observation)


class DiagnosticCode(str, Enum):
    """Machine-readable diagnostic error and warning codes."""
    EMPTY_TEXT_PAYLOAD = "ERR_TEXT_EMPTY_PAYLOAD"
    EXCESSIVE_LENGTH = "ERR_TEXT_EXCESSIVE_LENGTH"
    UNDECLARED_SPEAKER = "ERR_TEXT_UNDECLARED_SPEAKER"
    UNDECLARED_ENTITY = "ERR_TEXT_UNDECLARED_ENTITY"
    CANON_STATE_CONTRADICTION = "ERR_TEXT_CANON_STATE_CONTRADICTION"
    EXACT_TEXT_ALTERATION = "ERR_TEXT_EXACT_ALTERATION_DETECTED"
    INVALID_BLOCK_KIND = "ERR_TEXT_INVALID_BLOCK_KIND"
    READING_ORDER_DISCONTINUITY = "ERR_TEXT_READING_ORDER_DISCONTINUITY"
    LANGUAGE_SCRIPT_MISMATCH = "ERR_TEXT_LANGUAGE_SCRIPT_MISMATCH"
    MISSING_PANEL_LINKAGE = "ERR_TEXT_MISSING_PANEL_LINKAGE"
    UNVERIFIED_MODEL_OUTPUT = "WARN_TEXT_UNVERIFIED_MODEL_OUTPUT"
    CHARACTER_VOICE_DRIFT = "WARN_TEXT_CHARACTER_VOICE_DRIFT"
