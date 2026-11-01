"""
InkLoop Text Generation Engine - Domain Models & Data Contracts (Milestone M5 / Workstream E4).
Defines structured script blocks, speaker references, provenance tracking,
validation diagnostics, script manifests, and generation requests.
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.text.enums import (
    ScriptBlockKind,
    DialogueDelivery,
    CaptionKind,
    SFXCategory,
    TextLanguage,
    TextDirection,
    SourceMode,
    DiagnosticSeverity,
    DiagnosticCode,
)
from app.contracts.engine import EngineStatus, QualityVerdict, UsageMetrics


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SpeakerRef(BaseModel):
    """
    Stable reference to a speaker or narrative voice.
    Validated against Story Bible / Canon character definitions.
    """
    speaker_id: str = Field(..., description="Stable character ID in lowercase (e.g. 'nour') or 'narrator'")
    is_declared_character: bool = Field(default=True, description="True if character exists in Story Bible canon")
    display_name: Optional[str] = Field(default=None, description="Human-readable display name")
    voice_traits: List[str] = Field(default_factory=list, description="Canonical voice/vocabulary traits")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_speaker_id_clean(self) -> "SpeakerRef":
        clean = self.speaker_id.strip().lower()
        if not clean:
            raise ValueError("speaker_id cannot be empty or whitespace")
        return self


class TextProvenance(BaseModel):
    """
    Immutable provenance ledger for a structured text block.
    Links generated or user-authored text back to source passages, models, and timestamps.
    """
    provenance_id: str = Field(..., description="Unique provenance UUID or identifier")
    source_mode: SourceMode = Field(..., description="Origin of text (user_exact, user_derived, model_generated, etc.)")
    source_passage_id: Optional[str] = Field(default=None, description="ID of source script passage or user story beat")
    source_text_hash: Optional[str] = Field(default=None, description="SHA-256 of original source text if available")
    generated_text_hash: Optional[str] = Field(default=None, description="SHA-256 of final accepted text payload")
    model_name: Optional[str] = Field(default=None, description="Text generation model if AI-proposed")
    prompt_config_hash: Optional[str] = Field(default=None, description="Deterministic hash of generation prompt configuration")
    attempt_id: Optional[str] = Field(default=None, description="Execution attempt ID if part of an engine run")
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")


class TextValidationDiagnostic(BaseModel):
    """
    Actionable machine-readable diagnostic detailing a validation issue or review warning.
    """
    code: DiagnosticCode = Field(..., description="Stable diagnostic enum code")
    severity: DiagnosticSeverity = Field(..., description="ERROR, WARNING, or INFO")
    target_block_id: Optional[str] = Field(default=None, description="ID of offending ScriptBlock if block-specific")
    field_name: Optional[str] = Field(default=None, description="Model attribute involved (e.g. 'speaker', 'text_content')")
    message: str = Field(..., description="Human-readable explanation of diagnostic")
    observed_value: Optional[str] = Field(default=None, description="Value observed during validation")
    suggested_fix: Optional[str] = Field(default=None, description="Actionable recommendation for resolution")

    model_config = ConfigDict(extra="forbid")


class ScriptBlock(BaseModel):
    """
    Core structured text artifact representing a discrete unit of comic script.
    Serves as input to Typography & Font Engine (E5) and Speech Bubble Engine (E6).
    """
    block_id: str = Field(..., description="Stable unique block identifier (e.g. 'blk_p01_01')")
    project_id: str = Field(..., description="Parent project identifier")
    story_id: str = Field(default="story_01", description="Parent story identifier")
    scene_id: str = Field(..., description="Scene identifier (e.g. 'scene_01')")
    panel_id: str = Field(..., description="Target panel slot identifier (e.g. 'panel_01')")
    block_kind: ScriptBlockKind = Field(..., description="Semantic type: dialogue, narration, caption, monologue, sfx")
    reading_order_index: int = Field(default=0, ge=0, description="Sequential reading order within this panel (0-indexed)")
    text_content: str = Field(..., description="The exact text payload; Unicode-safe, preserves diacritics and exact punctuation")
    language: TextLanguage = Field(default=TextLanguage.AR, description="Primary language classification")
    direction: TextDirection = Field(default=TextDirection.RTL, description="Reading direction (RTL for Arabic/Manga, LTR for English)")
    is_exact_user_text: bool = Field(default=False, description="True if this block represents unadulterated user story text")
    provenance: TextProvenance = Field(..., description="Lineage and generation origin")
    
    # Kind-specific semantic metadata (no visual coordinates or geometry)
    speaker: Optional[SpeakerRef] = Field(default=None, description="Required for dialogue and monologue; disallowed for SFX")
    delivery: Optional[DialogueDelivery] = Field(default=None, description="Vocal delivery for dialogue (whisper, shout, radio, etc.)")
    addressee: Optional[SpeakerRef] = Field(default=None, description="Optional target character for dialogue")
    caption_kind: Optional[CaptionKind] = Field(default=None, description="Subtype if block_kind is CAPTION")
    sfx_category: Optional[SFXCategory] = Field(default=None, description="Semantic category if block_kind is SFX")
    length_guidance: Dict[str, Any] = Field(default_factory=dict, description="Calculated word count, character count, estimated reading duration")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_block_semantics(self) -> "ScriptBlock":
        # 1. Text payload cannot be purely whitespace
        if not self.text_content or not self.text_content.strip():
            raise ValueError(f"ScriptBlock '{self.block_id}' text_content cannot be empty or purely whitespace.")

        # 2. Dialogue and Monologue must specify a speaker
        if self.block_kind in (ScriptBlockKind.DIALOGUE, ScriptBlockKind.MONOLOGUE, ScriptBlockKind.OFF_PANEL):
            if self.speaker is None:
                raise ValueError(f"ScriptBlock '{self.block_id}' of kind '{self.block_kind.value}' requires a 'speaker'.")
            if self.delivery is None:
                self.delivery = DialogueDelivery.NORMAL

        # 3. SFX blocks must not specify a character speaker
        if self.block_kind == ScriptBlockKind.SFX and self.speaker is not None:
            raise ValueError(f"ScriptBlock '{self.block_id}' of kind 'sfx' cannot specify a character speaker.")

        # 4. Automatically populate length guidance if missing
        if not self.length_guidance:
            words = len(self.text_content.strip().split())
            chars = len(self.text_content)
            # Average reading speed ~ 200 words per minute -> 3.3 words per second
            est_reading_sec = max(0.5, round(words / 3.3, 2))
            self.length_guidance = {
                "word_count": words,
                "character_count": chars,
                "estimated_reading_seconds": est_reading_sec,
            }

        return self

    @property
    def word_count(self) -> int:
        return self.length_guidance.get("word_count", len(self.text_content.strip().split()))

    @property
    def character_count(self) -> int:
        return self.length_guidance.get("character_count", len(self.text_content))

    def content_hash(self) -> str:
        return compute_sha256(self.text_content)


class TextScriptManifest(BaseModel):
    """
    Authoritative collection of accepted structured text blocks for a scene or page.
    Provides verifiable cryptographic references and validation status.
    """
    manifest_id: str = Field(..., description="Unique script manifest identifier")
    project_id: str
    story_id: str
    scene_id: Optional[str] = None
    blocks: List[ScriptBlock] = Field(default_factory=list)
    total_word_count: int = 0
    total_character_count: int = 0
    languages_present: List[str] = Field(default_factory=list)
    canon_hash_referenced: Optional[str] = None
    bible_version: Optional[str] = None
    diagnostics: List[TextValidationDiagnostic] = Field(default_factory=list)
    is_valid: bool = True
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_blocks(
        cls,
        manifest_id: str,
        project_id: str,
        story_id: str,
        blocks: List[ScriptBlock],
        scene_id: Optional[str] = None,
        canon_hash: Optional[str] = None,
        bible_version: Optional[str] = None,
        diagnostics: Optional[List[TextValidationDiagnostic]] = None,
    ) -> "TextScriptManifest":
        total_w = sum(b.word_count for b in blocks)
        total_c = sum(b.character_count for b in blocks)
        langs = sorted(list({b.language.value for b in blocks}))
        diags = diagnostics or []
        has_errors = any(d.severity == DiagnosticSeverity.ERROR for d in diags)

        return cls(
            manifest_id=manifest_id,
            project_id=project_id,
            story_id=story_id,
            scene_id=scene_id,
            blocks=blocks,
            total_word_count=total_w,
            total_character_count=total_c,
            languages_present=langs,
            canon_hash_referenced=canon_hash,
            bible_version=bible_version,
            diagnostics=diags,
            is_valid=not has_errors,
        )


# ==============================================================================
# Request and Result Contracts
# ==============================================================================

class TextValidationRequest(BaseModel):
    """
    Request to validate a set of script blocks against Story Bible and timeline state.
    """
    project_id: str
    target_scene_id: str
    target_panel_id: str
    blocks: List[ScriptBlock]
    story_bible: Optional[Any] = Field(default=None, description="StoryBible or CanonSnapshot instance")
    timeline_events: Optional[List[Any]] = Field(default=None, description="List of StoryStateEvent records")
    allow_undeclared_entities: bool = Field(default=False, description="If True, emit warnings instead of errors for undeclared entities")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TextValidationResult(BaseModel):
    """
    Deterministic validation verdict for structured text blocks.
    """
    is_valid: bool
    needs_human_review: bool
    diagnostics: List[TextValidationDiagnostic] = Field(default_factory=list)
    accepted_blocks: List[ScriptBlock] = Field(default_factory=list)
    rejected_blocks: List[ScriptBlock] = Field(default_factory=list)
    effective_timeline_state: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class TextGenerationRequest(BaseModel):
    """
    Request to generate structured text blocks for a comic scene/panel.
    """
    project_id: str
    story_id: str = "story_01"
    scene_id: str
    panel_id: str
    scene_action: str = Field(..., description="Narrative action and dialogue intent")
    character_ids: List[str] = Field(default_factory=list, description="Characters present in panel")
    block_kinds_requested: List[ScriptBlockKind] = Field(
        default_factory=lambda: [ScriptBlockKind.DIALOGUE],
        description="Types of text blocks to produce"
    )
    exact_user_text: Optional[str] = Field(default=None, description="Immutable user text if exact preservation requested")
    target_language: TextLanguage = Field(default=TextLanguage.AR)
    target_direction: TextDirection = Field(default=TextDirection.RTL)
    tone_guidance: Optional[str] = None
    story_bible: Optional[Any] = Field(default=None, description="CanonSnapshot or StoryBible for character voice and invariants")
    timeline_events: Optional[List[Any]] = Field(default=None, description="Active narrative state timeline")
    adapter_name: str = Field(default="offline_simulated", description="Adapter to execute ('offline_simulated' or 'meta_llm')")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TextGenerationResult(BaseModel):
    """
    Complete result returned by the Text Generation Engine.
    """
    success: bool
    status: EngineStatus
    manifest: Optional[TextScriptManifest] = None
    blocks: List[ScriptBlock] = Field(default_factory=list)
    diagnostics: List[TextValidationDiagnostic] = Field(default_factory=list)
    is_exact_user_text: bool = False
    adapter_used: str = "offline_simulated"
    is_simulated: bool = True
    cost_usd: Optional[float] = None
    usage: Optional[UsageMetrics] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)

    model_config = ConfigDict(extra="forbid")
