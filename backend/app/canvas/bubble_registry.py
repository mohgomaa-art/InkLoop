"""Canonical semantic bubble types and their lettering constraints.

Visual preset IDs are appearances. They do not introduce new semantic types.
The registry is intentionally small so Agent, editor, and export callers can
use the same type descriptions and limits.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class BubbleTypeSpec:
    type_id: str
    label: str
    description: str
    carrier: str
    word_limit: int
    max_lines: int
    min_font_px: int
    max_font_px: int
    default_shape: str
    default_tail: str
    tail_required: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# This is the complete semantic type vocabulary. Keep appearance presets out
# of this tuple; legacy styles are mapped to these eight IDs below.
BUBBLE_TYPES: tuple[BubbleTypeSpec, ...] = (
    BubbleTypeSpec("speech.normal", "Normal speech", "Ordinary spoken dialogue from an on-panel speaker.", "speech_bubble", 12, 3, 16, 28, "oval", "smooth_pointer", True),
    BubbleTypeSpec("speech.shout", "Shout", "Loud, urgent, or strongly emphasized spoken dialogue.", "speech_bubble", 5, 2, 18, 36, "shout_burst", "lightning_bolt", True),
    BubbleTypeSpec("speech.whisper", "Whisper", "Quiet, secretive, or hesitant spoken dialogue.", "speech_bubble", 8, 3, 14, 24, "whisper_cloud_soft", "whisper_dashed", True),
    BubbleTypeSpec("thought.cloud", "Thought", "Internal thought or silent reflection.", "thought_bubble", 10, 4, 16, 28, "thought_cloud", "bubble_chain", False),
    BubbleTypeSpec("speech.offpanel", "Off-panel speech", "A voice whose speaker is outside the visible panel.", "speech_bubble", 12, 3, 16, 28, "oval", "off_screen_pointer", True),
    BubbleTypeSpec("narration.box", "Narration", "Narrator prose that is separate from spoken dialogue.", "narration_box", 16, 4, 14, 24, "rounded_rectangle", "none", False),
    BubbleTypeSpec("caption.timeplace", "Time or place caption", "A concise time, date, place, or scene-transition caption.", "caption", 5, 2, 12, 20, "rounded_rectangle", "none", False),
    BubbleTypeSpec("sfx.text", "Sound effect", "Standalone sound-effect lettering, not dialogue.", "sfx", 3, 1, 28, 72, "none", "none", False),
)

BUBBLE_TYPE_BY_ID: Dict[str, BubbleTypeSpec] = {item.type_id: item for item in BUBBLE_TYPES}

# Map the ten historical visual intents onto the semantic vocabulary without
# changing any of their stable bubble_<intent>_<treatment> preset IDs.
LEGACY_INTENT_TYPE_IDS: Dict[str, str] = {
    "spoken": "speech.normal",
    "thought": "thought.cloud",
    "whisper": "speech.whisper",
    "shout": "speech.shout",
    "fear": "speech.normal",
    "anger": "speech.shout",
    "joy": "speech.normal",
    "broadcast": "speech.offpanel",
    "narration": "narration.box",
    "mystery": "speech.offpanel",
}


def type_id_for_appearance(appearance_id: str) -> str:
    """Return the semantic type for a legacy appearance preset ID."""
    parts = appearance_id.split("_")
    if len(parts) < 3 or parts[0] != "bubble":
        raise ValueError(f"Unknown bubble appearance ID: {appearance_id}")
    intent = parts[1]
    type_id = LEGACY_INTENT_TYPE_IDS.get(intent)
    if type_id is None:
        raise ValueError(f"Unmapped bubble appearance intent: {intent}")
    return type_id


def describe_bubble_types() -> List[Dict[str, Any]]:
    """Return serializable type descriptions and constraints for API/tool schemas."""
    return [item.to_dict() for item in BUBBLE_TYPES]


def attach_type_ids(appearances: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Copy appearance records while adding the canonical semantic type ID."""
    result: List[Dict[str, Any]] = []
    for appearance in appearances:
        item = dict(appearance)
        item["type_id"] = type_id_for_appearance(str(item["id"]))
        result.append(item)
    return result


def validate_bubble_registry(appearances: Iterable[Dict[str, Any]]) -> None:
    """Raise on duplicate types, unmapped presets, or dangling type references."""
    if len(BUBBLE_TYPE_BY_ID) != 8:
        raise ValueError("Bubble semantic registry must contain exactly eight unique type IDs.")
    for appearance in appearances:
        type_id = appearance.get("type_id") or type_id_for_appearance(str(appearance.get("id", "")))
        if type_id not in BUBBLE_TYPE_BY_ID:
            raise ValueError(f"Bubble appearance {appearance.get('id')} references unknown type {type_id}.")
