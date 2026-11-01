"""Searchable, stable-ID panel-layout and speech-bubble preset catalogue.

Presets compose existing deterministic Canvas templates and implemented bubble
geometry. They do not claim a unique geometry algorithm for every catalogue row.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus
from typing import Any, Dict, List, Optional


_LAYOUT_PATTERNS = [
    {
        "id": "single_splash", "name": "Single Splash",
        "template_id": "manga_grid", "parameters": {"rows": 1, "cols": 1},
        "rhythm": "one large uninterrupted panel",
    },
    {
        "id": "balanced_diptych", "name": "Balanced Diptych",
        "template_id": "manga_grid", "parameters": {"rows": 1, "cols": 2},
        "rhythm": "two equal side-by-side panels",
    },
    {
        "id": "uneven_diptych", "name": "Uneven Diptych",
        "template_id": "manga_grid", "parameters": {"rows": 1, "cols": 2, "col_ratios": [1.55, 0.85]},
        "rhythm": "wide lead panel followed by a narrow reaction or detail",
    },
    {
        "id": "stacked_reveal", "name": "Stacked Reveal",
        "template_id": "manga_grid", "parameters": {"rows": 2, "cols": 1, "row_ratios": [0.72, 1.28]},
        "rhythm": "short setup above a larger reveal",
    },
    {
        "id": "hero_left", "name": "Left Hero with Cut-ins",
        "template_id": "manga_grid", "parameters": {"rows": 2, "cols": 2, "row_ratios": [1.35, 0.65], "col_ratios": [1.35, 0.65]},
        "rhythm": "large left hero region with compact right-side beats",
    },
    {
        "id": "hero_right", "name": "Right Hero with Cut-ins",
        "template_id": "manga_grid", "parameters": {"rows": 2, "cols": 2, "row_ratios": [1.35, 0.65], "col_ratios": [0.65, 1.35]},
        "rhythm": "large right hero region with compact left-side beats",
    },
    {
        "id": "three_beat_vertical", "name": "Three Beat Vertical",
        "template_id": "manga_grid", "parameters": {"rows": 3, "cols": 1, "row_ratios": [1.0, 0.75, 1.25]},
        "rhythm": "three vertically paced moments",
    },
    {
        "id": "four_koma", "name": "Four Koma",
        "template_id": "four_koma", "parameters": {},
        "rhythm": "four vertically stacked setup-to-payoff beats",
    },
    {
        "id": "five_panel_action", "name": "Five Panel Action",
        "template_id": "five_panel_action", "parameters": {},
        "rhythm": "angled action beats around a wide center panel",
    },
    {
        "id": "dynamic_shonen", "name": "Dynamic Shonen",
        "template_id": "dynamic_shonen", "parameters": {},
        "rhythm": "slanted action panels with a dominant impact beat",
    },
]

_NARRATIVE_CASES = [
    ("opening", "Scene opener", "Establish the scene quickly; reserve the largest region for the clearest visual hook."),
    ("reveal", "Reveal", "Delay the important visual information, then give the reveal the strongest panel area."),
    ("dialogue", "Conversation", "Keep character exchanges readable and leave comfortable space for dialogue."),
    ("reaction", "Reaction", "Give facial, creature, object, or environmental reactions room to land."),
    ("action", "Action beat", "Use varied panel sizes to make the movement and impact easy to follow."),
    ("chase", "Chase sequence", "Make direction and progression clear across successive panels."),
    ("quiet", "Quiet pause", "Use breathing room and fewer visual interruptions for a reflective beat."),
    ("comedy", "Comedic timing", "Create a clear setup, pause, reaction, and payoff rhythm."),
    ("suspense", "Suspense", "Control what the reader sees and when; reserve a strong final beat."),
    ("aftermath", "Aftermath", "Contrast the main consequence with smaller details or reactions."),
]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _build_panel_layouts() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for pattern in _LAYOUT_PATTERNS:
        for case_index, (case_id, case_name, guidance) in enumerate(_NARRATIVE_CASES):
            preset_id = f"panel_layout_{pattern['id']}_{case_id}"
            title = f"{pattern['name']} · {case_name}"
            query = quote_plus(f"comic manga panel layout {pattern['name']} {case_name}")
            parameters = dict(pattern["parameters"])
            # Narrative use changes relative panel emphasis where the underlying
            # template is a configurable grid, producing concrete geometry variants.
            rows = int(parameters.get("rows", 1))
            cols = int(parameters.get("cols", 1))
            for dimension, count, key in (("row", rows, "row_ratios"), ("column", cols, "col_ratios")):
                if count <= 1:
                    continue
                base = list(parameters.get(key, [1.0] * count))
                if len(base) != count:
                    continue
                rhythm = [1.0 + (((case_index + index * 2) % 5) - 2) * 0.12 for index in range(count)]
                parameters[key] = [round(value * scale, 3) for value, scale in zip(base, rhythm)]
            records.append({
                "id": preset_id,
                "name": title,
                "category": case_name,
                "use_case": guidance,
                "reading_rhythm": pattern["rhythm"],
                "template_id": pattern["template_id"],
                "template_parameters": parameters,
                "agent_guidance": f"{guidance} {pattern['rhythm']}",
                "pinterest_search_url": f"https://www.pinterest.com/search/pins/?q={query}",
                "version": 1,
            })
    return records


_BUBBLE_INTENTS = [
    ("spoken", "Natural Dialogue", "oval", "smooth_pointer", "none", False, False, "#FFFFFF", "#111111", "ordinary spoken dialogue"),
    ("thought", "Thought Cloud", "thought_cloud", "bubble_chain", "none", False, False, "#FFFFFF", "#111111", "inner thought or silent reflection"),
    ("whisper", "Whisper", "whisper_cloud_soft", "whisper_dashed", "none", False, False, "#FFFFFF", "#555555", "quiet, secretive, or hesitant speech"),
    ("shout", "Shout Burst", "shout_burst", "lightning_bolt", "speedline_needles", True, False, "#FFF8DC", "#111111", "loud speech or sudden emphasis"),
    ("fear", "Fear Tremble", "fear_tremble", "smoke_puff", "sweat_drop", False, False, "#F3FBFF", "#34505C", "fear, cold, or nervous speech"),
    ("anger", "Anger Impact", "explosive_blast", "lightning_bolt", "anger_vein_cross", True, False, "#FFE7E2", "#8B1E16", "anger, accusation, or confrontation"),
    ("joy", "Joy and Affection", "affection_heart", "smooth_pointer", "heart_flutter", False, False, "#FFF0F6", "#8B345E", "affection, delight, or playful excitement"),
    ("broadcast", "Radio Broadcast", "radio_broadcast_zigzag", "zigzag_antenna", "electric_sparks", True, False, "#EAFBFF", "#075B76", "radio, device, or public-address speech"),
    ("narration", "Narration Banner", "tilted_banner", "none", "none", False, False, "#FFF7DB", "#49391C", "narration, time jumps, or scene labels"),
    ("mystery", "Ghostly Voice", "dark_aura_ghost", "off_screen_pointer", "dizziness_swirl", False, True, "#111827", "#D9E6FF", "an eerie, disembodied, or supernatural voice"),
]

_BUBBLE_TREATMENTS = [
    ("classic", "Classic Ink", False, False, "", 2.5),
    ("halftone", "Manga Halftone", True, False, "", 3.0),
    ("soft_color", "Soft Color", False, False, "", 2.2),
    ("high_contrast", "High Contrast", True, True, "", 4.0),
    ("hand_inked", "Loose Hand Ink", False, False, "6 3", 3.2),
]


def _build_bubble_presets() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for intent_id, intent_name, shape, tail, accent, halftone, inverted, fill, stroke, use_case in _BUBBLE_INTENTS:
        for treatment_id, treatment_name, treatment_halftone, treatment_inverted, dash, width in _BUBBLE_TREATMENTS:
            is_inverted = inverted or treatment_inverted
            resolved_fill = ("#111827" if treatment_inverted else fill)
            resolved_stroke = ("#F8FAFC" if treatment_inverted else stroke)
            preset_id = f"bubble_{intent_id}_{treatment_id}"
            query = quote_plus(f"comic speech bubble {intent_name} {treatment_name}")
            records.append({
                "id": preset_id,
                "name": f"{intent_name} · {treatment_name}",
                "category": intent_name,
                "use_case": use_case,
                "shape": shape,
                "tail_type": tail,
                "accent": accent,
                "halftone_shadow": halftone or treatment_halftone,
                "inverted_dark_mode": is_inverted,
                "fill_color": resolved_fill,
                "stroke_color": resolved_stroke,
                "text_color": "#FFFFFF" if is_inverted else "#111111",
                "stroke_width": width,
                "stroke_dash": dash,
                "agent_guidance": f"Use for {use_case}; apply the {treatment_name.lower()} finish.",
                "pinterest_search_url": f"https://www.pinterest.com/search/pins/?q={query}",
                "version": 1,
            })
    return records


PANEL_LAYOUT_PRESETS = _build_panel_layouts()
BUBBLE_PRESETS = _build_bubble_presets()
_PANEL_LAYOUT_BY_ID = {item["id"]: item for item in PANEL_LAYOUT_PRESETS}
_BUBBLE_BY_ID = {item["id"]: item for item in BUBBLE_PRESETS}

assert len(PANEL_LAYOUT_PRESETS) == 100 and len(_PANEL_LAYOUT_BY_ID) == 100
assert len(BUBBLE_PRESETS) == 50 and len(_BUBBLE_BY_ID) == 50


def _search(records: List[Dict[str, Any]], query: str, limit: int) -> List[Dict[str, Any]]:
    if not query.strip():
        return records[:limit]
    terms = _words(query)
    ranked = []
    for item in records:
        searchable = _words(" ".join(str(item.get(key, "")) for key in ("id", "name", "category", "use_case", "agent_guidance")))
        score = len(terms & searchable)
        if score:
            ranked.append((score, item["id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:limit]]


def list_panel_layout_presets(query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    return _search(PANEL_LAYOUT_PRESETS, query, max(1, min(int(limit), 100)))


def get_panel_layout_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    return _PANEL_LAYOUT_BY_ID.get(preset_id)


def list_bubble_presets(query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    return _search(BUBBLE_PRESETS, query, max(1, min(int(limit), 50)))


def get_bubble_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    return _BUBBLE_BY_ID.get(preset_id)
