"""
Pure-code builder for independent per-panel continuity context packets.
Ensures zero conversational drift and deterministic context fingerprinting.
Supports both app.schemas.StoryBible and app.project.StoryBible.
"""
import json
import hashlib
from typing import Optional, Dict, Any, List, Union
from app.schemas import (
    StoryBible,
    SceneSpec,
    PanelContextPacket,
    CharacterSpec,
    ReferenceAsset,
    Tolerances,
)

def compute_context_fingerprint(payload: Dict[str, Any]) -> str:
    """
    Computes a deterministic, reproducible SHA-256 fingerprint for a context packet.
    Uses canonical JSON formatting (sorted keys, compact separators).
    """
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

def _normalize_character_spec(raw_char: Any, cid: str) -> CharacterSpec:
    """Extracts or normalizes a CharacterSpec from either schema representation."""
    if isinstance(raw_char, CharacterSpec):
        return raw_char
    attributes = getattr(raw_char, "attributes", [])
    tolerances = getattr(raw_char, "tolerances", None) or Tolerances()
    char_id = getattr(raw_char, "character_id", getattr(raw_char, "id", cid))
    return CharacterSpec(
        id=char_id,
        attributes=attributes,
        tolerances=tolerances
    )

def _normalize_reference_asset(raw_asset: Any, default_id: str) -> ReferenceAsset:
    """Extracts or normalizes a ReferenceAsset from either schema representation."""
    if isinstance(raw_asset, ReferenceAsset):
        return raw_asset
    asset_id = getattr(raw_asset, "asset_id", default_id)
    file_path = getattr(raw_asset, "path", getattr(raw_asset, "file_path", ""))
    sha256 = getattr(raw_asset, "sha256", getattr(raw_asset, "content_hash", ""))
    mime_type = getattr(raw_asset, "mime_type", "image/png") or "image/png"
    description = getattr(raw_asset, "description", None)
    return ReferenceAsset(
        asset_id=asset_id,
        file_path=file_path,
        content_hash=sha256,
        mime_type=mime_type,
        description=description
    )

def _resolve_bible_style_rules(story_bible: Any) -> tuple[str, List[str]]:
    """Resolves (line_and_tone, negative_rules) from style object across schemas."""
    style_obj = getattr(story_bible, "style", None)
    if style_obj is None:
        return "black and white comic ink, clean linework with screentone shading", [
            "no dialogue text", "no speech bubbles", "no watermarks"
        ]

    line_and_tone = getattr(style_obj, "line_and_tone", None)
    if not line_and_tone and hasattr(style_obj, "rendering_rules"):
        line_and_tone = ", ".join(style_obj.rendering_rules)
    if not line_and_tone:
        line_and_tone = "black and white ink with screentone shading"

    negative_rules = getattr(style_obj, "negative_rules", None)
    if not negative_rules and hasattr(style_obj, "negative_constraints"):
        negative_rules = list(style_obj.negative_constraints)
    if not negative_rules:
        negative_rules = ["no dialogue text", "no speech bubbles", "no watermarks"]

    return line_and_tone, list(negative_rules)

def build_scene_generation_prompt(
    line_and_tone: str,
    scene: SceneSpec,
    character_specs: List[CharacterSpec],
    visual_invariants: List[str],
    prohibited_deviations: List[str],
) -> str:
    """
    Deterministically compiles visual prompt instructions for the image generation adapter.
    Preserves M0 reference-anchored generation grammar and negative rule constraints.
    """
    parts = []

    # 1. Medium and style header
    parts.append(f"Comic book panel illustration, {line_and_tone}.")

    # 2. Reference anchoring clause
    parts.append("Preserve the exact character likeness from the canonical reference image:")

    # 3. Primary subject action and shot framing
    char_names = ", ".join([c.id.capitalize() for c in character_specs]) or "the character"
    scene_core = f"{char_names} {scene.action} ({scene.shot_type})"
    if scene.camera_angle:
        scene_core += f", {scene.camera_angle}"
    if scene.lighting:
        scene_core += f", {scene.lighting}"
    parts.append(f"{scene_core}.")

    # 4. Explicit visual invariants
    if visual_invariants:
        invariants_str = "; ".join(visual_invariants)
        parts.append(f"Maintain canonical character identity: {invariants_str}.")

    # 5. Explicit current scene state (if present)
    if scene.scene_state:
        state_items = [f"{k}: {v}" for k, v in sorted(scene.scene_state.items())]
        parts.append(f"Current scene state: {', '.join(state_items)}.")

    # 6. Panel-specific composition instructions (isolated to this panel)
    if scene.panel_instructions:
        parts.append(f"Composition note: {scene.panel_instructions.strip()}.")

    # 7. Explicit previous panel continuity facts (if present)
    if scene.previous_panel_summary:
        parts.append(f"Narrative continuity from previous beat: {scene.previous_panel_summary.strip()}.")

    # 8. Negative constraints / prohibited deviations
    if prohibited_deviations:
        parts.append(f"Clean linework, high contrast, {', '.join(prohibited_deviations)}.")

    return " ".join(parts)

def build_panel_context_packet(
    story_bible: Any,
    scene: SceneSpec,
    panel_id: str,
    story_id: str = "story_01",
    project_id: str = "inkloop",
    model: str = "muse-image-1.0",
    generation_params: Optional[Dict[str, Any]] = None,
) -> PanelContextPacket:
    """
    Assembles an independent context packet for an individual panel.
    Every panel receives a freshly isolated context derived purely from the Story Bible
    and explicit scene specification. No hidden conversational state is used.
    """
    gen_params = generation_params or {"n": 1}

    # Extract version and identifiers
    bible_version = str(getattr(story_bible, "bible_version", getattr(story_bible, "version", "1.0.0")))
    bible_id = getattr(story_bible, "bible_id", getattr(story_bible, "project_id", "inkloop"))
    line_and_tone, style_negatives = _resolve_bible_style_rules(story_bible)

    # 1. Resolve relevant characters
    characters_dict = getattr(story_bible, "characters", {})
    character_specs: List[CharacterSpec] = []
    for cid in scene.character_ids:
        if cid in characters_dict:
            raw_char = characters_dict[cid]
            character_specs.append(_normalize_character_spec(raw_char, cid))

    # 2. Resolve canonical character reference assets
    character_assets_dict = getattr(story_bible, "character_assets", {})
    reference_assets: List[ReferenceAsset] = []
    for cid in scene.character_ids:
        if cid in character_assets_dict:
            raw_asset = character_assets_dict[cid]
            reference_assets.append(_normalize_reference_asset(raw_asset, f"{cid}_ref"))
        elif cid in characters_dict:
            # Check if CharacterDefinition has reference_assets attached directly
            raw_char = characters_dict[cid]
            char_refs = getattr(raw_char, "reference_assets", [])
            for r in char_refs:
                reference_assets.append(_normalize_reference_asset(r, f"{cid}_ref"))

    # 3. Assemble visual invariants
    visual_invariants: List[str] = []
    for char in character_specs:
        for attr in char.attributes:
            if attr.required:
                visual_invariants.append(f"{char.id} {attr.id}: {attr.text}")

    # 4. Assemble prohibited deviations / negative rules
    prohibited_deviations: List[str] = list(style_negatives)

    # 5. Build generation prompt
    prompt = build_scene_generation_prompt(
        line_and_tone=line_and_tone,
        scene=scene,
        character_specs=character_specs,
        visual_invariants=visual_invariants,
        prohibited_deviations=prohibited_deviations,
    )

    # 6. Deterministic continuity summary
    continuity_summary = scene.previous_panel_summary

    # 7. Construct semantic payload for reproducible fingerprint computation
    fingerprint_payload = {
        "story_id": story_id,
        "project_id": project_id,
        "bible_id": bible_id,
        "bible_version": bible_version,
        "panel_id": panel_id,
        "scene_id": scene.scene_id,
        "scene_index": scene.scene_index,
        "scene_description": f"{scene.title}: {scene.action} ({scene.shot_type})",
        "generation_prompt": prompt,
        "character_ids": sorted(scene.character_ids),
        "character_specs": [
            {
                "id": c.id,
                "attributes": [{"id": a.id, "text": a.text, "required": a.required} for a in c.attributes]
            }
            for c in character_specs
        ],
        "reference_assets": [
            {"asset_id": r.asset_id, "content_hash": r.content_hash}
            for r in reference_assets
        ],
        "previous_panel_continuity": continuity_summary,
        "scene_state": scene.scene_state,
        "visual_invariants": visual_invariants,
        "prohibited_deviations": prohibited_deviations,
        "model": model,
        "generation_params": gen_params,
    }

    fingerprint = compute_context_fingerprint(fingerprint_payload)

    return PanelContextPacket(
        story_id=story_id,
        project_id=project_id,
        bible_id=bible_id,
        bible_version=bible_version,
        panel_id=panel_id,
        scene_id=scene.scene_id,
        scene_index=scene.scene_index,
        scene_description=f"{scene.title}: {scene.action} ({scene.shot_type})",
        generation_prompt=prompt,
        character_ids=scene.character_ids,
        character_specs=character_specs,
        reference_assets=reference_assets,
        previous_panel_continuity=continuity_summary,
        scene_state=scene.scene_state,
        visual_invariants=visual_invariants,
        prohibited_deviations=prohibited_deviations,
        model=model,
        generation_params=gen_params,
        context_fingerprint=fingerprint,
    )
