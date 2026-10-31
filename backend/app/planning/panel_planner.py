"""Deterministic narrative-to-panel planning, separate from E2 page geometry.

The planner consumes authored, structured story beats. It does not claim to
understand arbitrary prose or to detect visual duplicates in generated images.
Its default camera and composition choices are rules keyed to each beat's
declared narrative function; explicit author choices always take precedence.
"""
from enum import Enum
from typing import Dict, List, Literal, Optional, Sequence, Tuple
import hashlib
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.canvas.descriptors import (
    CameraAngle,
    CameraPosition,
    CompositionType,
    FramingScale,
    LayoutRelation,
    MultiAxisPanelDescriptor,
    NarrativeFunction,
    NarrativePlanningTag,
    PanelBoundaryTreatment,
    PanelFramingDescriptor,
    PanelNarrativeDescriptor,
    PanelShapeType,
    PanelTransitionType,
    ShotType,
    VNGRole,
)
from app.canvas.models import CanvasLayoutResult, PanelSlot, ReadingDirection, LayoutTemplateId


class TextContentKind(str, Enum):
    SPOKEN_DIALOGUE = "spoken_dialogue"
    EMOTIONAL_SPEECH = "emotional_speech"
    INTERNAL_THOUGHT = "internal_thought"
    NARRATION = "narration"
    SFX = "sfx"
    DATE_OR_PLACE = "date_or_place"
    DIEGETIC = "diegetic"
    TRANSLATION = "translation"
    NONE = "none"


class TextCarrier(str, Enum):
    SPEECH_BUBBLE = "speech_bubble"
    THOUGHT_BUBBLE = "thought_bubble"
    NARRATION_BOX = "narration_box"
    CAPTION = "caption"
    SFX_LETTERING = "sfx_lettering"
    DIEGETIC_LAYER = "diegetic_layer"
    DIRECT_OVERLAY = "direct_overlay"
    NONE = "none"


class TextRegion(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    RESERVED_NEGATIVE_SPACE = "reserved_negative_space"
    AUTHOR_REVIEW = "author_review"


class PanelTextPlan(BaseModel):
    """Text semantics and visual carrier, recorded before lettering layout."""
    model_config = ConfigDict(extra="forbid")

    content_kind: TextContentKind = Field(
        description="Meaning of the text: audible spoken dialogue, internal thought, narration, SFX, or none. Scene/action descriptions are not dialogue."
    )
    carrier: TextCarrier = Field(
        description="Visual holder matched to meaning: spoken/emotional speech uses speech_bubble; internal_thought uses thought_bubble; narration uses caption or narration_box; omit with none."
    )
    text_content: Optional[str] = Field(
        default=None,
        max_length=4000,
        description=(
            "Exact creator-authored/approved wording, or the exact Agent-drafted line explicitly present in this typed plan. "
            "For newly drafted audible dialogue, aim for 8 words or fewer and never exceed 12; preserve creator wording "
            "even when longer. Omit text rather than filling every panel."
        ),
    )
    text_block_ids: List[str] = Field(default_factory=list, max_length=16)
    speaker_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Stable ID of the selected canonical character who speaks or thinks this text. For story-local characters, leave this empty and use speaker_name; the compiler assigns a job-local ID.",
    )
    speaker_name: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Exact name of a visible story-local character who speaks or thinks this text. Use only when the story has no creator-selected Canon cast; never invent a Canon ID.",
    )
    reading_order_index: int = Field(default=1, ge=1)
    reserve_space: bool = False
    preferred_region: Optional[TextRegion] = None
    override_reason: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_carrier_semantics(self) -> "PanelTextPlan":
        expected: Dict[TextContentKind, Tuple[TextCarrier, ...]] = {
            TextContentKind.SPOKEN_DIALOGUE: (TextCarrier.SPEECH_BUBBLE,),
            TextContentKind.EMOTIONAL_SPEECH: (TextCarrier.SPEECH_BUBBLE,),
            TextContentKind.INTERNAL_THOUGHT: (TextCarrier.THOUGHT_BUBBLE,),
            TextContentKind.NARRATION: (TextCarrier.NARRATION_BOX, TextCarrier.CAPTION),
            TextContentKind.SFX: (TextCarrier.SFX_LETTERING,),
            TextContentKind.DATE_OR_PLACE: (TextCarrier.CAPTION, TextCarrier.NARRATION_BOX),
            TextContentKind.DIEGETIC: (TextCarrier.DIEGETIC_LAYER,),
            TextContentKind.TRANSLATION: (TextCarrier.DIRECT_OVERLAY,),
            TextContentKind.NONE: (TextCarrier.NONE,),
        }
        allowed = expected[self.content_kind]
        if self.carrier == TextCarrier.SPEECH_BUBBLE and self.content_kind not in (
            TextContentKind.SPOKEN_DIALOGUE,
            TextContentKind.EMOTIONAL_SPEECH,
        ):
            raise ValueError("Speech bubbles are only for audible dialogue or emotional speech by a selected character.")
        if self.carrier not in allowed and not (self.override_reason and self.override_reason.strip()):
            raise ValueError(
                f"Carrier '{self.carrier.value}' is not the default for '{self.content_kind.value}'; "
                "provide an explicit override_reason to preserve the author decision."
            )
        strict_semantics = {
            TextContentKind.SPOKEN_DIALOGUE,
            TextContentKind.EMOTIONAL_SPEECH,
            TextContentKind.INTERNAL_THOUGHT,
            TextContentKind.NARRATION,
        }
        if self.content_kind in strict_semantics and self.carrier not in allowed:
            raise ValueError(
                f"Carrier '{self.carrier.value}' cannot represent '{self.content_kind.value}'; "
                "text meaning and carrier must stay aligned."
            )
        if self.content_kind == TextContentKind.NONE and (
            self.text_block_ids or self.reserve_space or self.text_content or self.speaker_id or self.speaker_name
        ):
            raise ValueError("A text-free panel cannot bind text blocks or reserve lettering space.")
        if self.content_kind == TextContentKind.NONE and self.preferred_region is not None:
            raise ValueError("A text-free panel cannot specify a preferred lettering region.")
        if self.carrier != TextCarrier.NONE and not self.reserve_space and self.preferred_region is None:
            if "reserve_space" not in self.model_fields_set:
                # Model/tool callers commonly name a text carrier but omit its
                # layout detail. Default the lettering reservation on so a
                # coherent plan can be compiled; an explicit false remains a
                # validation error unless the author supplies a region.
                self.reserve_space = True
            else:
                raise ValueError("Text-bearing panels must reserve lettering space or specify an explicit placement region.")
        return self


class PanelScriptLine(BaseModel):
    """A single line of lettering script within a panel (B6)."""
    model_config = ConfigDict(extra="ignore")

    line_id: Optional[str] = None
    type_id: str = "speech.normal"
    speaker_character_id: Optional[str] = None
    speaker_name: Optional[str] = None
    text: str
    reading_order: int = Field(default=1, ge=1)
    kind: Optional[TextContentKind] = None
    carrier: Optional[TextCarrier] = None
    delivery: Optional[str] = None


class NarrativeBeat(BaseModel):
    """One authored event and its intended reader takeaway."""
    model_config = ConfigDict(extra="forbid")

    beat_id: str = Field(..., min_length=1, max_length=128)
    panel_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    page_number: Optional[int] = Field(default=None, ge=1, description="Optional explicit page grouping in the approved story plan.")
    narrative_function: NarrativeFunction
    story_event: str = Field(..., min_length=1, max_length=2000)
    reader_takeaway: str = Field(..., min_length=1, max_length=1000)
    character_ids: List[str] = Field(
        default_factory=list,
        max_length=16,
        description="Characters explicitly used in this beat. Empty inherits the active creator-selected cast unless characterless is true.",
    )
    prop_ids: List[str] = Field(default_factory=list, max_length=24, description="Stable project object IDs visible in this beat")
    prop_states: Dict[str, str] = Field(default_factory=dict, description="Scene state for listed objects; does not change their stable identity")
    characterless: bool = Field(
        default=False,
        description="Set true only for an intentional environment/detail/cutaway panel with no selected character visible.",
    )
    environment: Optional[str] = Field(default=None, max_length=1000)
    visual_focus: str = Field(..., min_length=1, max_length=500)
    emotional_intent: str = Field(..., min_length=1, max_length=500)
    movement_direction: Optional[str] = Field(default=None, max_length=200)
    lighting_intent: Optional[str] = Field(default=None, max_length=500)
    protected_visual_elements: List[str] = Field(default_factory=list, max_length=32)
    prohibited_visual_elements: List[str] = Field(default_factory=list, max_length=32)
    text: PanelTextPlan
    script_lines: List[PanelScriptLine] = Field(default_factory=list)
    shot_type: Optional[ShotType] = None
    subject_scale: Optional[FramingScale] = None
    camera_angle: Optional[CameraAngle] = None
    camera_position: Optional[CameraPosition] = None
    composition_type: Optional[CompositionType] = None
    transition_role: Optional[PanelTransitionType] = Field(
        default=None,
        description="This panel's relationship to the panel immediately before it in reading order",
    )
    shape_preference: Optional[PanelShapeType] = Field(default=None, description="Story-aware panel geometry preference applied by the custom E2 page generator where supported")
    layout_relation: Optional[LayoutRelation] = Field(default=None, description="Suggestion for E2 layout; never changes geometry")
    intentional_repetition_reason: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_silent_beat_text(self) -> "NarrativeBeat":
        if self.characterless and self.character_ids:
            raise ValueError("A character-free beat cannot also declare character_ids.")
        if self.narrative_function == NarrativeFunction.SILENT:
            if self.text.content_kind != TextContentKind.NONE:
                raise ValueError("A declared silent beat must explicitly use text.content_kind='none'.")
            self.script_lines = []
        elif not self.script_lines and self.text.content_kind != TextContentKind.NONE and (self.text.text_content or "").strip():
            from app.text.lettering_layout import type_id_for_text
            carrier_str = self.text.carrier.value if hasattr(self.text.carrier, "value") else str(self.text.carrier)
            kind_str = self.text.content_kind.value if hasattr(self.text.content_kind, "value") else str(self.text.content_kind)
            derived_type = type_id_for_text(carrier=carrier_str, content_kind=kind_str)
            self.script_lines = [
                PanelScriptLine(
                    line_id=f"{self.beat_id}_line_1",
                    type_id=derived_type,
                    speaker_character_id=self.text.speaker_id,
                    speaker_name=self.text.speaker_name,
                    text=(self.text.text_content or "").strip(),
                    reading_order=1,
                    kind=self.text.content_kind,
                    carrier=self.text.carrier,
                )
            ]
        if self.text.content_kind in (TextContentKind.SPOKEN_DIALOGUE, TextContentKind.EMOTIONAL_SPEECH) and not self.text.speaker_id:
            # When a beat contains exactly one declared character, that stable
            # character ID is the only unambiguous speaker choice. Multi-cast
            # beats must name the speaker explicitly; guessing there could
            # attach dialogue to the wrong character.
            if len(self.character_ids) == 1:
                self.text.speaker_id = self.character_ids[0]
            elif not self.character_ids:
                # An empty beat cast inherits the active composer selection;
                # PanelPlanningRequest validates and may resolve that cast.
                pass
            else:
                raise ValueError(
                    "Spoken text needs speaker_id set to one of this beat's character_ids; "
                    "only a single-character beat can infer its speaker safely."
                )
        if self.text.speaker_id and self.character_ids and self.text.speaker_id not in self.character_ids:
            raise ValueError("speaker_id must match a character_id declared for this beat.")
        if self.intentional_repetition_reason is not None and not self.intentional_repetition_reason.strip():
            raise ValueError("intentional_repetition_reason must contain an explanation when supplied.")
        return self


class PanelPlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional project/story identifier scoping this panel plan.",
    )
    scene_id: str = Field(..., min_length=1, max_length=128)
    scene_summary: Optional[str] = Field(default=None, max_length=2000)
    reading_direction: ReadingDirection = ReadingDirection.RTL
    selected_character_ids: List[str] = Field(
        default_factory=list,
        max_length=16,
        description="Authoritative character IDs supplied by the active creator selection; the Agent must not invent or replace these IDs.",
    )
    available_prop_ids: List[str] = Field(default_factory=list, max_length=100, description="Project prop IDs available to this plan")
    beats: List[NarrativeBeat] = Field(..., min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PanelPlanningRequest":
        if len(self.selected_character_ids) != len(set(self.selected_character_ids)):
            raise ValueError("selected_character_ids must be unique.")
        selected = set(self.selected_character_ids)
        if selected:
            outside_selection = sorted({
                character_id
                for beat in self.beats
                for character_id in beat.character_ids
                if character_id not in selected
            })
            if outside_selection:
                raise ValueError(
                    "Beat character_ids must be part of the creator-selected cast: "
                    + ", ".join(outside_selection)
                )
        for beat in self.beats:
            unknown_props = sorted(set(beat.prop_ids) - set(self.available_prop_ids))
            if unknown_props:
                raise ValueError("Beat prop_ids must reference objects saved in the active project: " + ", ".join(unknown_props))
            if set(beat.prop_states) - set(beat.prop_ids):
                raise ValueError("prop_states may only specify objects listed in that beat's prop_ids.")
            if beat.text.content_kind not in (TextContentKind.SPOKEN_DIALOGUE, TextContentKind.EMOTIONAL_SPEECH):
                continue
            panel_cast = [] if beat.characterless else (beat.character_ids or self.selected_character_ids)
            if not beat.text.speaker_id and len(panel_cast) == 1:
                beat.text.speaker_id = panel_cast[0]
            if not beat.text.speaker_id or beat.text.speaker_id not in panel_cast:
                raise ValueError(
                    f"Beat '{beat.beat_id}' spoken text needs speaker_id set to a character in that panel's selected cast."
                )
        beat_ids = [beat.beat_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("beat_id values must be unique within a scene plan.")
        panel_ids = [beat.panel_id or f"panel_{index:02d}" for index, beat in enumerate(self.beats, start=1)]
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError("Resolved panel_id values must be unique within a scene plan.")
        return self


class StoryCastProfile(BaseModel):
    """Story-local character description; never written into Canon by planning."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=80)
    kind_and_form: Optional[str] = Field(default=None, max_length=160)
    visual_description: str = Field(..., min_length=1, max_length=800)
    personality: Optional[str] = Field(default=None, max_length=400)


class StoryObjectDraft(BaseModel):
    """Project-local draft identity for a new recurring story object."""
    model_config = ConfigDict(extra="forbid")

    prop_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    form_and_proportions: str = Field(default="", max_length=1000)
    materials: List[str] = Field(default_factory=list, max_length=24)
    palette: List[str] = Field(default_factory=list, max_length=24)
    components: List[str] = Field(default_factory=list, max_length=32)
    distinctive_marks: List[str] = Field(default_factory=list, max_length=32)
    stable_invariants: List[str] = Field(default_factory=list, max_length=32)
    allowed_states: List[str] = Field(default_factory=list, max_length=32)
    uncertain_traits: List[str] = Field(default_factory=list, max_length=32)


class StoryBeatDraft(BaseModel):
    """Compact page-planning beat compiled through the typed panel planner."""
    model_config = ConfigDict(extra="forbid")

    story_event: str = Field(..., min_length=1, max_length=2000)
    reader_takeaway: Optional[str] = Field(default=None, max_length=1000)
    visual_focus: Optional[str] = Field(default=None, max_length=500)
    emotional_intent: Optional[str] = Field(default=None, max_length=500)
    narrative_function: NarrativeFunction = NarrativeFunction.ACTION_CONTINUATION
    character_ids: List[str] = Field(..., max_length=16)
    prop_ids: List[str] = Field(default_factory=list, max_length=24, description="Use the same stable object ID on every panel where this recurring object appears.")
    prop_states: Dict[str, str] = Field(default_factory=dict, description="State only, such as lit, carried, or damaged; never redefine object identity here.")
    visible_character_names: List[str] = Field(..., max_length=16)
    characterless: bool = Field(...)
    environment: Optional[str] = Field(default=None, max_length=1000)
    text: PanelTextPlan = Field(
        description=(
            "Make an intentional lettering decision for this beat. Use short audible dialogue only when a visible character would plausibly speak; "
            "identify the actual speaker. Use captions for necessary narration, thought bubbles for internal thoughts, and none for visual-only beats. "
            "Do not put scene descriptions in speech bubbles or fill every panel with text. Aim for 8 words or fewer for newly drafted dialogue, with 12 as the maximum."
        )
    )
    script_lines: List[PanelScriptLine] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_planned_text(self) -> "StoryBeatDraft":
        text = self.text
        if text.content_kind != TextContentKind.NONE and not (text.text_content or "").strip():
            raise ValueError("A text-bearing story beat needs the exact wording; otherwise set content_kind and carrier to none.")
        if text.speaker_id and text.speaker_name:
            raise ValueError("Use speaker_id for a Canon character or speaker_name for a story-local character, not both.")
        return self


class StoryPageDraft(BaseModel):
    """A page summary and its story-driven, variable-density panel beats."""
    model_config = ConfigDict(extra="forbid")

    page_number: Optional[int] = Field(default=None, ge=1, le=50)
    summary: str = Field(..., min_length=1, max_length=1000)
    beats: List[StoryBeatDraft] = Field(..., min_length=1, max_length=24)


class StoryBlueprintDraft(BaseModel):
    """Reviewable, page-aware story plan. Compiled panels remain the production contract."""
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = Field(default=None, max_length=128)
    page_count: int = Field(..., ge=1, le=50)
    title: str = Field(..., min_length=1, max_length=180)
    premise: str = Field(..., min_length=1, max_length=2000)
    audience_tone: Optional[str] = Field(default=None, max_length=500)
    world_rules: List[str] = Field(default_factory=list, max_length=24)
    story_cast: List[StoryCastProfile] = Field(default_factory=list, max_length=16)
    recurring_objects: List[StoryObjectDraft] = Field(default_factory=list, max_length=32, description="New project-scoped object drafts needed across multiple panels. Use stable prop_ids in every relevant beat.")
    story_arc: str = Field(..., min_length=1, max_length=4000)
    assumptions: List[str] = Field(default_factory=list, max_length=32)
    reading_direction: ReadingDirection = ReadingDirection.RTL
    pages: List[StoryPageDraft] = Field(..., min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_page_count(self) -> "StoryBlueprintDraft":
        if len(self.pages) != self.page_count:
            raise ValueError(f"Expected exactly {self.page_count} pages, received {len(self.pages)}.")
        if self.page_count > 1 and any(not page.beats for page in self.pages):
            raise ValueError("Every planned page must contain at least one visual story beat.")
        object_ids = [item.prop_id.strip().lower() for item in self.recurring_objects]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("Recurring object prop_id values must be unique.")
        planned_object_uses = {
            object_id: sum(
                object_id in {prop_id.strip().lower() for prop_id in beat.prop_ids}
                for page in self.pages
                for beat in page.beats
            )
            for object_id in object_ids
        }
        unused_objects = sorted(object_id for object_id, uses in planned_object_uses.items() if uses == 0)
        if unused_objects:
            raise ValueError("Recurring object drafts must be selected in at least one planned panel: " + ", ".join(unused_objects))
        single_use_objects = sorted(object_id for object_id, uses in planned_object_uses.items() if uses == 1)
        if single_use_objects:
            raise ValueError("Recurring object drafts must recur in at least two planned panels; use a one-off scene prop without a recurring object draft: " + ", ".join(single_use_objects))
        for page in self.pages:
            for beat in page.beats:
                if set(beat.prop_states) - set(beat.prop_ids):
                    raise ValueError("prop_states may only specify objects listed in that beat's prop_ids.")
        all_beats = [beat for page in self.pages for beat in page.beats]
        has_lettering = any(beat.text.content_kind != TextContentKind.NONE for beat in all_beats)
        if not has_lettering and any(beat.narrative_function != NarrativeFunction.SILENT for beat in all_beats):
            raise ValueError(
                "This story plan contains no lettering. Add concise dialogue or necessary captions where the story calls for them; "
                "only mark every beat silent when the creator asked for a wordless story."
            )
        names = [profile.name.strip().casefold() for profile in self.story_cast]
        if len(names) != len(set(names)):
            raise ValueError("Story-local cast names must be unique.")
        known_names = set(names)
        unknown_names = sorted({
            name for page in self.pages for beat in page.beats
            for name in beat.visible_character_names
            if name.strip().casefold() not in known_names
        })
        if self.story_cast and unknown_names:
            raise ValueError("Panel references story-local characters missing from story_cast: " + ", ".join(unknown_names))
        return self


def compile_story_blueprint(
    blueprint: StoryBlueprintDraft,
    *,
    project_id: Optional[str] = None,
    selected_character_ids: Optional[Sequence[str]] = None,
    available_prop_ids: Optional[Sequence[str]] = None,
    allow_uniform_page_panels: bool = False,
) -> Dict[str, object]:
    """Compile each approved page independently, preserving its page number and cast scope."""
    selected = list(selected_character_ids or [])
    known_prop_ids = {str(item).strip().lower() for item in (available_prop_ids or [])}
    drafted_prop_ids = {item.prop_id.strip().lower() for item in blueprint.recurring_objects}
    conflict_ids = sorted(known_prop_ids & drafted_prop_ids)
    if conflict_ids:
        raise ValueError("Recurring object drafts cannot reuse existing prop IDs: " + ", ".join(conflict_ids))
    allowed_prop_ids = known_prop_ids | drafted_prop_ids
    if selected and blueprint.story_cast:
        raise ValueError("Use the creator-selected canonical cast; do not add a separate story-local cast.")
    if not selected and not blueprint.story_cast:
        raise ValueError("No cast is selected. Add a story-local cast to the blueprint; it will not be saved to Canon.")
    panel_densities = [len(page.beats) for page in blueprint.pages]
    if blueprint.page_count >= 4 and len(set(panel_densities)) == 1 and not allow_uniform_page_panels:
        raise ValueError("Every page has the same panel count. Vary panel density to match story pacing and action; only use a uniform count when the creator explicitly requested it.")

    local_speaker_ids = {
        profile.name.strip().casefold(): "story_local_" + hashlib.sha256(profile.name.strip().casefold().encode("utf-8")).hexdigest()[:16]
        for profile in blueprint.story_cast
    }
    all_plans: List[Dict[str, object]] = []
    page_rows: List[Dict[str, object]] = []
    for page_index, page in enumerate(blueprint.pages, start=1):
        page_number = page_index
        beats: List[NarrativeBeat] = []
        local_cast = {profile.name.casefold(): profile for profile in blueprint.story_cast}
        for beat_index, draft in enumerate(page.beats, start=1):
            outside_props = sorted({item.strip().lower() for item in draft.prop_ids} - allowed_prop_ids)
            if outside_props:
                raise ValueError("Panel prop_ids must reference an existing project object or a recurring_objects draft: " + ", ".join(outside_props))
            if selected:
                outside = sorted(set(draft.character_ids) - set(selected))
                if outside:
                    raise ValueError("Panel character_ids must be from the creator-selected cast: " + ", ".join(outside))
                character_ids = list(draft.character_ids) or ([] if draft.characterless else list(selected))
                characterless = draft.characterless
                visible_names: List[str] = []
            else:
                if draft.character_ids:
                    raise ValueError("Story-local cast panels cannot invent Canon character IDs.")
                character_ids = []
                characterless = draft.characterless
                visible_names = list(draft.visible_character_names)
                if not characterless and not visible_names:
                    raise ValueError("A story-local cast beat must name its visible_character_names or be marked characterless=true.")

            event = draft.story_event.strip()
            text_plan = draft.text.model_copy(deep=True)
            is_speaker_text = text_plan.content_kind in (
                TextContentKind.SPOKEN_DIALOGUE,
                TextContentKind.EMOTIONAL_SPEECH,
                TextContentKind.INTERNAL_THOUGHT,
            )
            if selected:
                if text_plan.speaker_name:
                    raise ValueError("Use selected Canon character IDs for dialogue; story-local speaker names are not allowed with a selected cast.")
                panel_cast = [] if characterless else (character_ids or selected)
                if is_speaker_text:
                    if not text_plan.speaker_id and len(panel_cast) == 1:
                        text_plan.speaker_id = panel_cast[0]
                    if not text_plan.speaker_id or text_plan.speaker_id not in panel_cast:
                        raise ValueError("Dialogue and thoughts must name a speaker from that panel's selected character cast.")
            elif is_speaker_text:
                if text_plan.speaker_id:
                    raise ValueError("Story-local dialogue must name its speaker with speaker_name, not a Canon character ID.")
                speaker_name = (text_plan.speaker_name or "").strip()
                speaker_key = speaker_name.casefold()
                if not speaker_name or speaker_key not in local_speaker_ids:
                    raise ValueError("Story-local dialogue speaker_name must match a character in the story-local cast.")
                if speaker_name.casefold() not in {name.casefold() for name in visible_names}:
                    raise ValueError("The story-local speaker must be visible in this panel.")
                text_plan.speaker_id = local_speaker_ids[speaker_key]

            # The deterministic panel planner validates canonical speakers.
            # Story-local speakers are carried by the typed page plan and
            # overlaid after geometry planning because they are not Canon IDs.
            planner_text = (
                PanelTextPlan(content_kind=TextContentKind.NONE, carrier=TextCarrier.NONE)
                if not selected and is_speaker_text
                else text_plan
            )
            beat = NarrativeBeat(
                beat_id=f"page_{page_number:02d}_beat_{beat_index:02d}",
                panel_id=f"page_{page_number:02d}_panel_{beat_index:02d}",
                page_number=page_number,
                narrative_function=draft.narrative_function,
                story_event=event,
                reader_takeaway=(draft.reader_takeaway or event).strip(),
                character_ids=character_ids,
                prop_ids=[item.strip().lower() for item in draft.prop_ids],
                prop_states={str(key).strip().lower(): str(value).strip() for key, value in draft.prop_states.items()},
                characterless=characterless,
                environment=draft.environment,
                visual_focus=(draft.visual_focus or event).strip(),
                emotional_intent=(draft.emotional_intent or "Advance the story naturally.").strip(),
                text=planner_text,
                script_lines=list(draft.script_lines),
            )
            beats.append(beat)

        request = PanelPlanningRequest(
            project_id=project_id or blueprint.project_id,
            scene_id=f"story_page_{page_number:02d}",
            scene_summary=f"{blueprint.title}: {page.summary}",
            reading_direction=blueprint.reading_direction,
            selected_character_ids=selected,
            available_prop_ids=sorted(allowed_prop_ids),
            beats=beats,
        )
        compiled = plan_panels(request)
        page_panel_ids: List[str] = []
        page_plan_rows: List[Dict[str, object]] = []
        for plan in compiled.plans:
            row = plan.model_dump(mode="json")
            source_beat = page.beats[int(row.get("reading_order_index", 1)) - 1]
            planned_text = source_beat.text.model_copy(deep=True)
            if not selected and planned_text.content_kind in (
                TextContentKind.SPOKEN_DIALOGUE,
                TextContentKind.EMOTIONAL_SPEECH,
                TextContentKind.INTERNAL_THOUGHT,
            ):
                planned_text.speaker_id = local_speaker_ids[planned_text.speaker_name.strip().casefold()]
            row["text"] = planned_text.model_dump(mode="json")
            row["page_number"] = page_number
            row["prop_ids"] = list(source_beat.prop_ids)
            row["prop_states"] = dict(source_beat.prop_states)
            row["image_brief"] = str(row.get("image_brief") or "") + f" Page story beat: {page.summary}."
            row["image_brief"] += f" Overall story arc: {blueprint.story_arc}."
            if blueprint.audience_tone:
                row["image_brief"] += f" Audience and tone: {blueprint.audience_tone}."
            if blueprint.world_rules:
                row["image_brief"] += " Story world rules to preserve: " + "; ".join(blueprint.world_rules) + "."
            object_profiles = {item.prop_id.strip().lower(): item for item in blueprint.recurring_objects}
            object_notes = []
            for object_id in source_beat.prop_ids:
                object_profile = object_profiles.get(object_id.strip().lower())
                if object_profile:
                    object_notes.append(
                        f"{object_profile.name} [{object_profile.prop_id}]: {object_profile.description}. "
                        f"Stable identity: {'; '.join(object_profile.stable_invariants)}. "
                        f"Panel state: {source_beat.prop_states.get(object_id, 'as described by the beat')}"
                    )
            if object_notes:
                row["image_brief"] += " Recurring object identities and this panel's states: " + " ".join(object_notes)
            if blueprint.story_cast and not bool(row.get("characterless")):
                visible = source_beat.visible_character_names
                profile_text = []
                for name in visible:
                    profile = local_cast[name.casefold()]
                    detail = f"{profile.name}: {profile.visual_description}"
                    if profile.kind_and_form:
                        detail += f" Kind/form: {profile.kind_and_form}."
                    if profile.personality:
                        detail += f" Personality: {profile.personality}."
                    profile_text.append(detail)
                row["story_local_character_names"] = visible
                row["image_brief"] = str(row["image_brief"]) + " Story-local character descriptions for this story: " + " ".join(profile_text)
            if planned_text.carrier != TextCarrier.NONE:
                row["image_brief"] = str(row["image_brief"]) + (
                    f" Reserve clear negative space for separately rendered {planned_text.carrier.value}; "
                    "do not draw bubbles, captions, or final lettering into the artwork."
                )
            all_plans.append(row)
            page_plan_rows.append(row)
            page_panel_ids.append(str(row["panel_id"]))
        page_rows.append({
            "page_number": page_number,
            "summary": page.summary,
            "panel_ids": page_panel_ids,
            "panel_count": len(page_panel_ids),
            "beats": [
                {
                    "panel_id": str(plan["panel_id"]),
                    "story_event": str(plan["story_event"]),
                    "visual_focus": str(plan["visual_focus"]),
                    "character_ids": list(plan.get("character_ids") or []),
                    "prop_ids": list(plan.get("prop_ids") or []),
                    "prop_states": dict(plan.get("prop_states") or {}),
                    "characterless": bool(plan.get("characterless")),
                    "text": dict(plan.get("text") or {}),
                }
                for plan in page_plan_rows
            ],
        })

    cast_rows = [
        {**profile.model_dump(mode="json"), "speaker_id": local_speaker_ids[profile.name.strip().casefold()]}
        for profile in blueprint.story_cast
    ]
    return {
        "schema_version": "story_blueprint.v1",
        "project_id": project_id or blueprint.project_id,
        "scene_summary": blueprint.premise,
        "page_count": blueprint.page_count,
        "total_panel_count": len(all_plans),
        "page_panel_counts": {str(row["page_number"]): row["panel_count"] for row in page_rows},
        "story_blueprint": {
            **blueprint.model_dump(mode="json"),
            "project_id": project_id or blueprint.project_id,
            "pages": page_rows,
            "selected_character_ids": selected,
            "story_cast_is_canon": False,
        },
        "story_local_cast": cast_rows,
        "recurring_objects": [item.model_dump(mode="json") for item in blueprint.recurring_objects],
        "plans": all_plans,
        "assumptions": list(blueprint.assumptions),
    }


class PanelPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel_id: str
    beat_id: str
    scene_id: str
    page_number: Optional[int] = Field(default=None, ge=1)
    reading_order_index: int = Field(default=1, ge=1)
    narrative_function: NarrativeFunction
    story_event: str
    reader_takeaway: str = Field(default="")
    character_ids: List[str] = Field(default_factory=list)
    prop_ids: List[str] = Field(default_factory=list)
    prop_states: Dict[str, str] = Field(default_factory=dict)
    characterless: bool = False
    character_selection_source: Literal[
        "explicit_beat", "creator_selected_default", "characterless", "none_selected"
    ] = "none_selected"
    environment: Optional[str] = None
    shot_type: ShotType
    subject_scale: FramingScale = FramingScale.MEDIUM_SHOT
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    camera_position: CameraPosition = CameraPosition.THREE_QUARTER
    composition_type: CompositionType = CompositionType.ENVIRONMENTAL_NEGATIVE_SPACE
    emotional_intent: str = Field(default="")
    visual_focus: str = Field(default="")
    movement_direction: Optional[str] = None
    lighting_intent: Optional[str] = None
    protected_visual_elements: List[str] = Field(default_factory=list)
    prohibited_visual_elements: List[str] = Field(default_factory=list)
    transition_role: PanelTransitionType = PanelTransitionType.ACTION_TO_ACTION
    transition_to_next: Optional[PanelTransitionType] = None
    text: PanelTextPlan
    script_lines: List[PanelScriptLine] = Field(default_factory=list)
    shape_preference: Optional[PanelShapeType] = None
    layout_relation: Optional[LayoutRelation] = None
    image_brief: str = Field(default="")
    planning_rationale: str = Field(default="")
    decision_sources: Dict[str, str] = Field(default_factory=dict)
    planning_signature: Dict[str, str] = Field(default_factory=dict)
    repetition_justification: Optional[str] = None

    @model_validator(mode="after")
    def populate_planning_signature_and_brief(self) -> "PanelPlan":
        if not self.planning_signature:
            self.planning_signature = {
                "shot_type": self.shot_type.value if hasattr(self.shot_type, "value") else str(self.shot_type),
                "subject_scale": self.subject_scale.value if hasattr(self.subject_scale, "value") else str(self.subject_scale),
                "camera_angle": self.camera_angle.value if hasattr(self.camera_angle, "value") else str(self.camera_angle),
                "camera_position": self.camera_position.value if hasattr(self.camera_position, "value") else str(self.camera_position),
                "composition_type": self.composition_type.value if hasattr(self.composition_type, "value") else str(self.composition_type),
            }
        if not self.image_brief:
            self.image_brief = (
                f"Story event: {self.story_event}. "
                f"Visual focus: {self.visual_focus}. "
                f"Narrative function: {self.narrative_function.value if hasattr(self.narrative_function, 'value') else self.narrative_function}."
            )
        return self


class PlanningDiagnostic(BaseModel):
    code: str
    severity: str
    panel_ids: List[str]
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    message: str


class PanelPlanningResult(BaseModel):
    planner_id: str = "S5.panel_planner"
    planner_version: str = "1.0.0"
    project_id: Optional[str] = None
    scene_id: str
    reading_direction: ReadingDirection
    plans: List[PanelPlan]
    diagnostics: List[PlanningDiagnostic] = Field(default_factory=list)
    planning_similarity_check: str = "complete"
    visual_similarity_check: str = "NOT_IMPLEMENTED"
    geometry_layout_status: str = "NOT_GENERATED_BY_PLANNER"
    recommended_template_id: Optional[str] = None
    recommended_layout_name: Optional[str] = None


_DEFAULTS: Dict[NarrativeFunction, Dict[str, object]] = {
    NarrativeFunction.ESTABLISHING: {
        "shot_type": ShotType.ESTABLISHING, "scale": FramingScale.EXTREME_LONG_SHOT,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.ENVIRONMENTAL,
        "composition": CompositionType.ENVIRONMENTAL_NEGATIVE_SPACE,
    },
    NarrativeFunction.ACTION_PREPARATION: {
        "shot_type": ShotType.MEDIUM, "scale": FramingScale.MEDIUM_LONG_SHOT,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.THREE_QUARTER,
        "composition": CompositionType.LEADING_LINES,
    },
    NarrativeFunction.ACTION_CONTINUATION: {
        "shot_type": ShotType.WIDE, "scale": FramingScale.FULL_SHOT,
        "angle": CameraAngle.LOW_ANGLE, "position": CameraPosition.THREE_QUARTER,
        "composition": CompositionType.DIAGONAL_ACTION,
    },
    NarrativeFunction.IMPACT: {
        "shot_type": ShotType.IMPACT, "scale": FramingScale.MEDIUM_CLOSE_UP,
        "angle": CameraAngle.DUTCH_CANTED, "position": CameraPosition.PROFILE,
        "composition": CompositionType.DIAGONAL_ACTION,
    },
    NarrativeFunction.REVEAL: {
        "shot_type": ShotType.CLOSE_UP, "scale": FramingScale.CLOSE_UP,
        "angle": CameraAngle.HIGH_ANGLE, "position": CameraPosition.THREE_QUARTER,
        "composition": CompositionType.OFF_CENTER_REVEAL,
    },
    NarrativeFunction.REACTION: {
        "shot_type": ShotType.REACTION, "scale": FramingScale.CLOSE_UP,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.FRONT,
        "composition": CompositionType.FACE_FOCUSED,
    },
    NarrativeFunction.AFTERMATH: {
        "shot_type": ShotType.DRAMATIC_WIDE, "scale": FramingScale.LONG_SHOT,
        "angle": CameraAngle.HIGH_ANGLE, "position": CameraPosition.ENVIRONMENTAL,
        "composition": CompositionType.AFTERMATH_NEGATIVE_SPACE,
    },
    NarrativeFunction.DETAIL: {
        "shot_type": ShotType.INSERT, "scale": FramingScale.EXTREME_CLOSE_UP,
        "angle": CameraAngle.OVERHEAD, "position": CameraPosition.ENVIRONMENTAL,
        "composition": CompositionType.DETAIL_FOCUSED,
    },
    NarrativeFunction.DIALOGUE: {
        "shot_type": ShotType.TWO_SHOT, "scale": FramingScale.MEDIUM_SHOT,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.OVER_THE_SHOULDER,
        "composition": CompositionType.TWO_SHOT_BALANCED,
    },
    NarrativeFunction.SILENT: {
        "shot_type": ShotType.SILENT, "scale": FramingScale.MEDIUM_LONG_SHOT,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.THREE_QUARTER,
        "composition": CompositionType.STILLNESS_NEGATIVE_SPACE,
    },
    NarrativeFunction.TRANSITION: {
        "shot_type": ShotType.TRANSITION, "scale": FramingScale.EXTREME_LONG_SHOT,
        "angle": CameraAngle.HIGH_ANGLE, "position": CameraPosition.ENVIRONMENTAL,
        "composition": CompositionType.ENVIRONMENTAL_NEGATIVE_SPACE,
    },
    NarrativeFunction.SYMBOLIC: {
        "shot_type": ShotType.WIDE, "scale": FramingScale.LONG_SHOT,
        "angle": CameraAngle.LOW_ANGLE, "position": CameraPosition.ENVIRONMENTAL,
        "composition": CompositionType.SYMBOLIC,
    },
    NarrativeFunction.CUTAWAY: {
        "shot_type": ShotType.INSERT, "scale": FramingScale.CLOSE_UP,
        "angle": CameraAngle.EYE_LEVEL, "position": CameraPosition.PROFILE,
        "composition": CompositionType.DETAIL_FOCUSED,
    },
}

_TAG_BY_FUNCTION = {
    NarrativeFunction.ESTABLISHING: NarrativePlanningTag.ESTABLISHING_SHOT,
    NarrativeFunction.ACTION_PREPARATION: NarrativePlanningTag.ACTION_PREPARATION,
    NarrativeFunction.ACTION_CONTINUATION: NarrativePlanningTag.ACTION_CONTINUATION,
    NarrativeFunction.IMPACT: NarrativePlanningTag.IMPACT_CONTACT,
    NarrativeFunction.REVEAL: NarrativePlanningTag.REVEAL,
    NarrativeFunction.REACTION: NarrativePlanningTag.REACTION,
    NarrativeFunction.AFTERMATH: NarrativePlanningTag.AFTERMATH_RESULT,
    NarrativeFunction.DETAIL: NarrativePlanningTag.DETAIL_INSERT,
    NarrativeFunction.DIALOGUE: NarrativePlanningTag.TWO_SHOT_DIALOGUE,
    NarrativeFunction.SILENT: NarrativePlanningTag.SILENT_BEAT,
    NarrativeFunction.TRANSITION: NarrativePlanningTag.TRANSITION_TIME_PLACE,
    NarrativeFunction.SYMBOLIC: NarrativePlanningTag.SYMBOLIC_METAPHOR,
    NarrativeFunction.CUTAWAY: NarrativePlanningTag.CUTAWAY,
}

_VNG_ROLE_BY_FUNCTION = {
    NarrativeFunction.ESTABLISHING: VNGRole.ESTABLISHER,
    NarrativeFunction.ACTION_PREPARATION: VNGRole.INITIAL,
    NarrativeFunction.ACTION_CONTINUATION: VNGRole.PROLONGATION,
    NarrativeFunction.IMPACT: VNGRole.PEAK,
    NarrativeFunction.REVEAL: VNGRole.PEAK,
    NarrativeFunction.REACTION: VNGRole.RELEASE,
    NarrativeFunction.AFTERMATH: VNGRole.RELEASE,
}


def _transition_for(beat: NarrativeBeat, index: int) -> PanelTransitionType:
    if beat.transition_role is not None:
        return beat.transition_role
    if index == 1:
        return PanelTransitionType.FIRST_PANEL_IN_SCENE
    if beat.narrative_function in (NarrativeFunction.ACTION_PREPARATION, NarrativeFunction.ACTION_CONTINUATION, NarrativeFunction.IMPACT):
        return PanelTransitionType.ACTION_TO_ACTION
    if beat.narrative_function in (NarrativeFunction.DIALOGUE, NarrativeFunction.REACTION):
        return PanelTransitionType.SUBJECT_TO_SUBJECT
    if beat.narrative_function == NarrativeFunction.TRANSITION:
        return PanelTransitionType.SCENE_TO_SCENE
    if beat.narrative_function in (NarrativeFunction.ESTABLISHING, NarrativeFunction.SILENT, NarrativeFunction.AFTERMATH):
        return PanelTransitionType.ASPECT_TO_ASPECT
    return PanelTransitionType.MOMENT_TO_MOMENT


def _compile_image_brief(
    beat: NarrativeBeat,
    scene_summary: Optional[str],
    shot: ShotType,
    scale: FramingScale,
    angle: CameraAngle,
    position: CameraPosition,
    composition: CompositionType,
    character_ids: Optional[Sequence[str]] = None,
) -> str:
    details = [
        f"Story event: {beat.story_event}",
        f"Reader should understand: {beat.reader_takeaway}",
        f"Narrative function: {beat.narrative_function.value}; shot: {shot.value}; subject scale: {scale.value}.",
        f"Camera: {position.value} position at {angle.value}; composition: {composition.value}.",
        f"Emotional intent: {beat.emotional_intent}; visual focus: {beat.visual_focus}.",
    ]
    if scene_summary:
        details.insert(0, f"Scene continuity context: {scene_summary}.")
    declared_character_ids = list(beat.character_ids if character_ids is None else character_ids)
    if declared_character_ids:
        details.append(f"Use only these selected character identities: {', '.join(declared_character_ids)}. Preserve their reference appearance and do not substitute a generic person or creature.")
    elif beat.characterless:
        details.append("This is intentionally character-free; show only the declared environment or detail, with no person or character.")
    if beat.environment:
        details.append(f"Environment: {beat.environment}.")
    if beat.movement_direction:
        details.append(f"Movement direction: {beat.movement_direction}.")
    if beat.lighting_intent:
        details.append(f"Lighting: {beat.lighting_intent}.")
    if beat.protected_visual_elements:
        details.append(f"Keep visible: {', '.join(beat.protected_visual_elements)}.")
    if beat.prohibited_visual_elements:
        details.append(f"Do not introduce: {', '.join(beat.prohibited_visual_elements)}.")
    if beat.text.reserve_space:
        region = beat.text.preferred_region.value if beat.text.preferred_region else "reserved negative space"
        details.append(f"Leave {region} available for a separately rendered {beat.text.carrier.value}; do not draw final lettering or bubbles.")
    else:
        details.append("Do not render dialogue, captions, bubbles, or final lettering into the artwork.")
    return " ".join(details)


def _word_jaccard(left: str, right: str) -> float:
    tokens_a = set(re.findall(r"[\w\u0600-\u06ff]+", left.casefold()))
    tokens_b = set(re.findall(r"[\w\u0600-\u06ff]+", right.casefold()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _planning_similarity(left: PanelPlan, right: PanelPlan) -> float:
    fields = ("shot_type", "subject_scale", "camera_angle", "camera_position", "composition_type")
    matches = sum(getattr(left, field) == getattr(right, field) for field in fields)
    focus = _word_jaccard(left.visual_focus, right.visual_focus)
    return round((matches / len(fields)) * 0.9 + focus * 0.1, 3)


def _deduce_shape_preference(
    narrative_function: NarrativeFunction,
    shot: ShotType,
    composition: CompositionType,
) -> PanelShapeType:
    if narrative_function == NarrativeFunction.ESTABLISHING or shot in (ShotType.ESTABLISHING, ShotType.WIDE, ShotType.DRAMATIC_WIDE):
        return PanelShapeType.PANORAMIC if shot == ShotType.DRAMATIC_WIDE else PanelShapeType.HORIZONTAL_RECTANGLE
    if narrative_function in (NarrativeFunction.ACTION_CONTINUATION, NarrativeFunction.IMPACT, NarrativeFunction.ACTION_PREPARATION):
        return PanelShapeType.TRAPEZOID
    if narrative_function in (NarrativeFunction.SILENT, NarrativeFunction.REACTION):
        return PanelShapeType.VERTICAL_RECTANGLE
    if narrative_function == NarrativeFunction.AFTERMATH:
        return PanelShapeType.HORIZONTAL_RECTANGLE
    return PanelShapeType.HORIZONTAL_RECTANGLE if "space" in composition.value else PanelShapeType.SQUARE


def recommend_layout_template(
    plans: Sequence[PanelPlan],
    reading_direction: ReadingDirection = ReadingDirection.RTL,
) -> LayoutTemplateId:
    count = len(plans)
    if count == 3:
        has_action = any(
            p.narrative_function in (
                NarrativeFunction.ACTION_CONTINUATION,
                NarrativeFunction.IMPACT,
                NarrativeFunction.ACTION_PREPARATION,
            ) for p in plans
        )
        return LayoutTemplateId.THREE_PANEL_HERO if has_action else LayoutTemplateId.THREE_PANEL_SLANTED
    elif count == 4:
        return LayoutTemplateId.DYNAMIC_SHONEN
    elif count == 5:
        return LayoutTemplateId.FIVE_PANEL_ACTION
    elif count == 6:
        return LayoutTemplateId.SIX_PANEL_CLASSIC
    elif count == 1:
        return LayoutTemplateId.MANGA_GRID
    return LayoutTemplateId.DYNAMIC_SHONEN if count <= 4 else LayoutTemplateId.MANGA_GRID


def plan_panels(request: PanelPlanningRequest) -> PanelPlanningResult:
    """Compile authored story beats into deterministic, reviewable per-panel plans."""
    plans: List[PanelPlan] = []
    diagnostics: List[PlanningDiagnostic] = []
    for index, beat in enumerate(request.beats, start=1):
        defaults = _DEFAULTS[beat.narrative_function]
        panel_id = beat.panel_id or f"panel_{index:02d}"
        shot = beat.shot_type or defaults["shot_type"]
        scale = beat.subject_scale or defaults["scale"]
        angle = beat.camera_angle or defaults["angle"]
        position = beat.camera_position or defaults["position"]
        composition = beat.composition_type or defaults["composition"]
        shape_pref = beat.shape_preference or _deduce_shape_preference(beat.narrative_function, shot, composition)
        beat_character_ids = list(beat.character_ids)
        if not beat_character_ids and not beat.characterless:
            beat_character_ids = list(request.selected_character_ids)
        plan = PanelPlan(
            panel_id=panel_id,
            beat_id=beat.beat_id,
            scene_id=request.scene_id,
            page_number=beat.page_number,
            reading_order_index=index,
            narrative_function=beat.narrative_function,
            story_event=beat.story_event,
            reader_takeaway=beat.reader_takeaway,
            character_ids=beat_character_ids,
            prop_ids=list(beat.prop_ids),
            prop_states=dict(beat.prop_states),
            characterless=beat.characterless,
            character_selection_source=(
                "characterless" if beat.characterless
                else "explicit_beat" if beat.character_ids
                else "creator_selected_default" if request.selected_character_ids
                else "none_selected"
            ),
            environment=beat.environment,
            shot_type=shot,
            subject_scale=scale,
            camera_angle=angle,
            camera_position=position,
            composition_type=composition,
            emotional_intent=beat.emotional_intent,
            visual_focus=beat.visual_focus,
            movement_direction=beat.movement_direction,
            lighting_intent=beat.lighting_intent,
            protected_visual_elements=beat.protected_visual_elements,
            prohibited_visual_elements=beat.prohibited_visual_elements,
            transition_role=_transition_for(beat, index),
            text=beat.text,
            script_lines=list(beat.script_lines),
            shape_preference=shape_pref,
            layout_relation=beat.layout_relation,
            image_brief=_compile_image_brief(
                beat, request.scene_summary, shot, scale, angle, position, composition,
                character_ids=beat_character_ids,
            ),
            planning_rationale=(
                f"The declared '{beat.narrative_function.value}' story event is framed as a {shot.value} "
                f"at {scale.value}, composed with {composition.value}, to direct attention to {beat.visual_focus} "
                f"and convey {beat.emotional_intent}."
            ),
            decision_sources={
                "shot_type": "author_override" if beat.shot_type else "narrative_function_rule",
                "subject_scale": "author_override" if beat.subject_scale else "narrative_function_rule",
                "camera_angle": "author_override" if beat.camera_angle else "narrative_function_rule",
                "camera_position": "author_override" if beat.camera_position else "narrative_function_rule",
                "composition_type": "author_override" if beat.composition_type else "narrative_function_rule",
                "transition_role": "author_override" if beat.transition_role else "deterministic_sequence_rule",
            },
            planning_signature={
                "shot_type": shot.value,
                "subject_scale": scale.value,
                "camera_angle": angle.value,
                "camera_position": position.value,
                "composition_type": composition.value,
            },
            repetition_justification=beat.intentional_repetition_reason,
        )
        if plans:
            previous = plans[-1]
            score = _planning_similarity(previous, plan)
            same_axes = sum(previous.planning_signature[k] == plan.planning_signature[k] for k in plan.planning_signature)
            same_focus = _word_jaccard(previous.visual_focus, plan.visual_focus)
            if (same_axes >= 4 and same_focus >= 0.35) or (same_axes == 5 and score >= 0.85):
                intentional = bool(beat.intentional_repetition_reason and beat.intentional_repetition_reason.strip())
                diagnostics.append(PlanningDiagnostic(
                    code="INTENTIONAL_PLANNING_REPETITION" if intentional else "UNJUSTIFIED_PLANNING_REPETITION",
                    severity="info" if intentional else "warning",
                    panel_ids=[previous.panel_id, panel_id],
                    similarity_score=score,
                    message=(
                        f"Adjacent plans are visually similar by their declared shot axes. Intent: {beat.intentional_repetition_reason}."
                        if intentional else
                        "Adjacent plans share at least four camera/composition axes and a similar focal point; vary a planned axis or record why the repeated framing is intentional."
                    ),
                ))
        plans.append(plan)
    for index, plan in enumerate(plans[:-1]):
        plan.transition_to_next = plans[index + 1].transition_role
    rec_tpl = recommend_layout_template(plans, request.reading_direction)
    return PanelPlanningResult(
        project_id=request.project_id,
        scene_id=request.scene_id,
        reading_direction=request.reading_direction,
        plans=plans,
        diagnostics=diagnostics,
        recommended_template_id=rec_tpl.value,
        recommended_layout_name=rec_tpl.name,
    )


def _shape_from_slot(slot: PanelSlot) -> PanelShapeType:
    if slot.has_polygon:
        return PanelShapeType.GENERAL_POLYGON
    ratio = slot.aspect_ratio
    if ratio >= 2.2:
        return PanelShapeType.PANORAMIC
    if ratio <= 1 / 2.2:
        return PanelShapeType.NARROW_STRIP
    if 0.9 <= ratio <= 1.1:
        return PanelShapeType.SQUARE
    return PanelShapeType.HORIZONTAL_RECTANGLE if ratio > 1 else PanelShapeType.VERTICAL_RECTANGLE


def _layout_relation(result: CanvasLayoutResult) -> LayoutRelation:
    """Annotate the relationship already chosen by E2's layout template."""
    return {
        "manga_grid": LayoutRelation.REGULAR_GRID,
        "six_panel_classic": LayoutRelation.TIERED,
        "four_koma": LayoutRelation.FOUR_KOMA,
        "dynamic_shonen": LayoutRelation.MIXED_DIAGONAL,
        "webtoon_vertical": LayoutRelation.VERTICAL_SCROLL,
    }.get(result.template_id.value, LayoutRelation.REGULAR_GRID)


def attach_panel_plans(layout: CanvasLayoutResult, planning: PanelPlanningResult) -> CanvasLayoutResult:
    """Attach narrative descriptors to matching E2 slots without changing geometry."""
    plan_by_id = {plan.panel_id: plan for plan in planning.plans}
    slot_ids = {slot.panel_id for slot in layout.panel_slots}
    if slot_ids != set(plan_by_id):
        missing_plans = sorted(slot_ids - set(plan_by_id))
        missing_slots = sorted(set(plan_by_id) - slot_ids)
        raise ValueError(
            "Panel plan IDs must match E2 slot IDs exactly; "
            f"missing_plans={missing_plans}, missing_slots={missing_slots}."
        )
    if layout.reading_direction != planning.reading_direction:
        raise ValueError("Planning and E2 layout reading directions must match.")
    planned_reading_order = [
        plan.panel_id for plan in sorted(planning.plans, key=lambda item: item.reading_order_index)
    ]
    if layout.reading_order_panel_ids != planned_reading_order:
        raise ValueError(
            "S5 and E2 reading_order_panel_ids must match exactly; "
            f"planning={planned_reading_order}, E2={layout.reading_order_panel_ids}."
        )
    slots = []
    for slot in layout.panel_slots:
        plan = plan_by_id[slot.panel_id]
        if slot.reading_order != plan.reading_order_index:
            raise ValueError(
                f"Reading-order mismatch for '{slot.panel_id}': S5 has {plan.reading_order_index}, "
                f"E2 has {slot.reading_order}."
            )
        function_tag = _TAG_BY_FUNCTION[plan.narrative_function]
        existing = slot.descriptor
        boundary = (
            existing.boundary.model_copy(update={
                "full_bleed": slot.is_full_bleed,
                "bleed_edges": slot.bleed_edges,
            })
            if existing else
            PanelBoundaryTreatment(full_bleed=slot.is_full_bleed, bleed_edges=slot.bleed_edges)
        )
        narrative = (
            existing.narrative.model_copy(update={
                "vng_role": _VNG_ROLE_BY_FUNCTION.get(plan.narrative_function, VNGRole.UNSPECIFIED),
                "narrative_function": plan.narrative_function,
                "function_tags": [function_tag],
                "scene_beat_description": plan.story_event,
                "is_silent": plan.text.content_kind == TextContentKind.NONE,
            })
            if existing else
            PanelNarrativeDescriptor(
                vng_role=_VNG_ROLE_BY_FUNCTION.get(plan.narrative_function, VNGRole.UNSPECIFIED),
                narrative_function=plan.narrative_function,
                function_tags=[function_tag],
                scene_beat_description=plan.story_event,
                is_silent=plan.text.content_kind == TextContentKind.NONE,
            )
        )
        framing = (
            existing.framing.model_copy(update={
                "scale": plan.subject_scale,
                "shot_type": plan.shot_type,
                "angle": plan.camera_angle,
                "camera_position": plan.camera_position,
                "composition_type": plan.composition_type,
                "emotional_intent": plan.emotional_intent,
                "visual_focus": plan.visual_focus,
            })
            if existing else
            PanelFramingDescriptor(
                scale=plan.subject_scale,
                shot_type=plan.shot_type,
                angle=plan.camera_angle,
                camera_position=plan.camera_position,
                composition_type=plan.composition_type,
                emotional_intent=plan.emotional_intent,
                visual_focus=plan.visual_focus,
            )
        )
        descriptor = MultiAxisPanelDescriptor(
            panel_id=plan.panel_id,
            reading_order_index=plan.reading_order_index,
            # E2 remains authoritative for page arrangement and actual frame shape.
            layout_relation=existing.layout_relation if existing else _layout_relation(layout),
            shape_type=_shape_from_slot(slot),
            boundary=boundary,
            narrative=narrative,
            framing=framing,
            transition_from_previous=plan.transition_role,
            group_id=existing.group_id if existing else None,
            parent_panel_id=existing.parent_panel_id if existing else None,
            z_index=slot.z_index,
            is_intentional_overlap=slot.is_intentional_overlap,
            source_reference_ids=existing.source_reference_ids if existing else [],
            notes=" ".join(filter(None, [
                existing.notes if existing else None,
                plan.reader_takeaway,
                f"Requested shape preference: {plan.shape_preference.value}." if plan.shape_preference else None,
                f"Requested layout relation: {plan.layout_relation.value}." if plan.layout_relation else None,
            ])),
        )
        slots.append(slot.model_copy(update={"descriptor": descriptor}))
    return layout.model_copy(deep=True, update={"panel_slots": slots})
