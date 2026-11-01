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
    PropSpec,
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
    if isinstance(raw_char, dict):
        attributes = raw_char.get("attributes", [])
        tolerances = raw_char.get("tolerances") or Tolerances()
        char_id = raw_char.get("character_id", raw_char.get("id", cid))
        name = raw_char.get("name")
        entity_kind = raw_char.get("entity_kind", "unspecified being")
        morphology = raw_char.get("morphology", "")
        surface_description = raw_char.get("surface_description", "")
        physical_height_cm = raw_char.get("physical_height_cm")
        proportion_constraints = raw_char.get("proportion_constraints")
        visual_invariants = list(raw_char.get("visual_invariants", []))
        restrictions = list(raw_char.get("restrictions", []))
        clothing_attributes = list(raw_char.get("clothing_attributes", []))
    else:
        attributes = getattr(raw_char, "attributes", [])
        tolerances = getattr(raw_char, "tolerances", None) or Tolerances()
        char_id = getattr(raw_char, "character_id", getattr(raw_char, "id", cid))
        name = getattr(raw_char, "name", None)
        entity_kind = getattr(raw_char, "entity_kind", "unspecified being")
        morphology = getattr(raw_char, "morphology", "")
        surface_description = getattr(raw_char, "surface_description", "")
        physical_height_cm = getattr(raw_char, "physical_height_cm", None)
        proportion_constraints = getattr(raw_char, "proportion_constraints", None)
        visual_invariants = list(getattr(raw_char, "visual_invariants", []))
        restrictions = list(getattr(raw_char, "restrictions", []))
        clothing_attributes = list(getattr(raw_char, "clothing_attributes", []))

    parsed_height = None
    if physical_height_cm is not None:
        try:
            parsed_height = float(physical_height_cm)
        except (ValueError, TypeError):
            parsed_height = None

    return CharacterSpec(
        id=char_id,
        name=name,
        entity_kind=entity_kind,
        morphology=morphology,
        surface_description=surface_description,
        physical_height_cm=parsed_height,
        proportion_constraints=proportion_constraints if isinstance(proportion_constraints, dict) else None,
        attributes=attributes,
        tolerances=tolerances,
        visual_invariants=visual_invariants,
        restrictions=restrictions,
        clothing_attributes=clothing_attributes,
    )

def _normalize_reference_asset(raw_asset: Any, default_id: str) -> ReferenceAsset:
    """Extracts or normalizes a ReferenceAsset from either schema representation."""
    if isinstance(raw_asset, ReferenceAsset):
        return raw_asset
    asset_id = getattr(raw_asset, "asset_id", default_id)
    file_path = getattr(raw_asset, "path", getattr(raw_asset, "file_path", ""))
    # AssetRef uses ``expected_hash`` while ReferenceAsset uses ``content_hash``.
    # Preserve either contract so the generation boundary can verify the bytes
    # against the actual selected reference instead of silently losing lineage.
    sha256 = (
        getattr(raw_asset, "expected_hash", None)
        or getattr(raw_asset, "sha256", None)
        or getattr(raw_asset, "content_hash", "")
    )
    mime_type = getattr(raw_asset, "mime_type", "image/png") or "image/png"
    description = getattr(raw_asset, "description", None)
    return ReferenceAsset(
        asset_id=asset_id,
        file_path=file_path,
        content_hash=sha256,
        mime_type=mime_type,
        description=description,
    )


def _normalize_prop_spec(raw_prop: Any, prop_id: str) -> PropSpec:
    """Normalize Canon or external Story Bible prop records without dropping identity references."""
    if isinstance(raw_prop, PropSpec):
        return raw_prop
    references = [
        _normalize_reference_asset(item, f"{prop_id}_ref_{index}")
        for index, item in enumerate(getattr(raw_prop, "reference_assets", []) or [], start=1)
    ]
    return PropSpec(
        prop_id=getattr(raw_prop, "prop_id", prop_id),
        name=getattr(raw_prop, "name", prop_id),
        description=getattr(raw_prop, "description", ""),
        required_attributes=list(getattr(raw_prop, "required_attributes", []) or []),
        reference_assets=references,
        form_and_proportions=getattr(raw_prop, "form_and_proportions", ""),
        materials=list(getattr(raw_prop, "materials", []) or []),
        palette=list(getattr(raw_prop, "palette", []) or []),
        components=list(getattr(raw_prop, "components", []) or []),
        distinctive_marks=list(getattr(raw_prop, "distinctive_marks", []) or []),
        stable_invariants=list(getattr(raw_prop, "stable_invariants", []) or []),
        allowed_states=list(getattr(raw_prop, "allowed_states", []) or []),
        version=str(getattr(raw_prop, "version", "1.0.0")),
    )
def _resolve_bible_style_rules(
    story_bible: Any,
    style_profile_override: Optional[Any] = None,
) -> tuple[str, List[str], Dict[str, Any]]:
    """Resolves (line_and_tone, negative_rules, style_meta) from style object across schemas."""
    if style_profile_override is not None:
        profile = style_profile_override
        analysis = getattr(profile, "analysis", None)
        traits = getattr(analysis, "traits", {}) if analysis else {}
        medium = (getattr(analysis, "medium", None) or "").strip()
        variables = getattr(profile, "style_variables", {}) or {}
        medium_control = variables.get("medium") if hasattr(variables, "get") else None
        if medium_control and getattr(medium_control, "pinned", False):
            medium = (getattr(medium_control, "value", None) or "").strip()
        if not medium or medium.casefold() in {"unclassified", "unknown", "unspecified"}:
            medium = profile.name
        line_and_tone = (getattr(profile, "style_prompt_core", None) or "").strip()
        if analysis and line_and_tone == (getattr(analysis, "analysis_summary", None) or "").strip():
            # Analysis summaries can accidentally include depicted content or
            # layout. Fall back to typed rendering traits in that case.
            line_and_tone = ""
        if not line_and_tone and analysis:
            safe_summaries = []
            for dimension in (
                "linework", "stroke_behavior", "edge_quality", "shading",
                "palette", "lighting", "background_detail", "texture",
            ):
                trait = traits.get(dimension) if hasattr(traits, "get") else None
                summary = str(getattr(trait, "summary", "") or "").strip()
                summary = summary.split(";", 1)[0]
                import re as regex
                summary = regex.sub(r"\bpanel\s+borders?\b", "outlines", summary, flags=regex.IGNORECASE)
                summary = summary.replace("visible in skin and fabric", "visible on surfaces")
                if summary:
                    safe_summaries.append(f"{dimension.replace('_', ' ')}: {summary}")
            line_and_tone = "; ".join(safe_summaries)
        if not line_and_tone:
            raise ValueError(f"Selected style profile '{profile.profile_id}' has no usable rendering description.")

        palette_trait = traits.get("palette") if hasattr(traits, "get") else None
        palette = (
            palette_trait.summary
            if palette_trait and getattr(palette_trait, "summary", None)
            else getattr(analysis, "measured_palette", None) if analysis else None
        ) or "unspecified"
        return line_and_tone, list(getattr(profile, "negative_constraints", []) or []), {
            "id": profile.profile_id,
            "medium": medium,
            "palette": palette,
            # The selected profile block is compiled by the Agent tool below.
            # Do not add inherited Bible or catalogue style directives around it.
            "positive_constraints": [],
            "lighting_constraints": [],
            "background_detail_rules": "",
        }

    style_obj = getattr(story_bible, "style", None)
    if style_obj is None:
        return (
            "clean panel artwork, illustrative style",
            ["no dialogue text", "no speech bubbles", "no watermarks"],
            {
                "medium": "comic book",
                "palette": "dynamic",
                "positive_constraints": [],
                "lighting_constraints": [],
                "background_detail_rules": "",
            }
        )

    medium = getattr(style_obj, "medium", None) or getattr(style_obj, "rendering_approach", None) or "comic illustration"
    line_and_tone = getattr(style_obj, "line_and_tone", None)
    if not line_and_tone and hasattr(style_obj, "line_art_rules"):
        rules = list(getattr(style_obj, "line_art_rules", [])) + list(getattr(style_obj, "tonal_rules", []))
        if rules:
            line_and_tone = ", ".join(rules)
    if not line_and_tone and hasattr(style_obj, "rendering_rules"):
        line_and_tone = ", ".join(style_obj.rendering_rules)
    if not line_and_tone and hasattr(style_obj, "rendering_approach"):
        line_and_tone = style_obj.rendering_approach
    if not line_and_tone:
        line_and_tone = f"clean panel artwork, {medium} style"

    negative_rules = getattr(style_obj, "negative_rules", None)
    if not negative_rules and hasattr(style_obj, "negative_constraints"):
        negative_rules = list(style_obj.negative_constraints)
    if not negative_rules:
        negative_rules = ["no dialogue text", "no speech bubbles", "no watermarks"]

    palette = getattr(style_obj, "palette", None) or getattr(style_obj, "palette_or_screentone", "dynamic")
    positive_constraints = list(getattr(style_obj, "positive_constraints", []))
    lighting_constraints = list(getattr(style_obj, "lighting_constraints", []))
    background_detail_rules = getattr(style_obj, "background_detail_rules", "")

    style_meta = {
        "medium": medium,
        "palette": palette if isinstance(palette, (str, dict, list)) else str(palette),
        "positive_constraints": positive_constraints,
        "lighting_constraints": lighting_constraints,
        "background_detail_rules": background_detail_rules,
    }
    return line_and_tone, list(negative_rules), style_meta


def _compile_scale_directives(
    character_specs: List[CharacterSpec],
    panel_plan: Optional[Any] = None,
    scene: Optional[SceneSpec] = None,
) -> List[str]:
    """
    Universally compiles relative character scale and solo miniature/massive grounding
    from canonical structured measurements without character-name hardcoding.
    """
    scale_directives: List[str] = []
    if not character_specs:
        return scale_directives

    # Case 1: Multi-character relative scale
    if len(character_specs) > 1:
        for i in range(len(character_specs)):
            for j in range(i + 1, len(character_specs)):
                c1 = character_specs[i]
                c2 = character_specs[j]
                h1 = getattr(c1, "physical_height_cm", None)
                h2 = getattr(c2, "physical_height_cm", None)

                # Both have explicit height measurements
                if h1 is not None and h2 is not None:
                    if abs(h1 - h2) >= 15.0 and min(h1, h2) > 0:
                        shorter = c1 if h1 < h2 else c2
                        taller = c2 if h1 < h2 else c1
                        min_h = min(h1, h2)
                        max_h = max(h1, h2)
                        ratio = max_h / min_h
                        ratio_int = round(ratio)
                        if ratio >= 4.5:
                            anchor = "lower shin or ankle height"
                        elif ratio >= 2.6:
                            anchor = "knee or mid-thigh height"
                        elif ratio >= 1.7:
                            anchor = "waist or hip height"
                        elif ratio >= 1.3:
                            anchor = "chest or shoulder height"
                        else:
                            anchor = "head level"
                        scale_directives.append(
                            f"Scale relationship: {shorter.name or shorter.id} (height: {min_h:g} cm) stands at approximately 1:{ratio_int} the height of {taller.name or taller.id} (height: {max_h:g} cm). "
                            f"{shorter.name or shorter.id} reaches only to {taller.name or taller.id}'s {anchor}. "
                            f"{taller.name or taller.id} visibly towers over {shorter.name or shorter.id}."
                        )
                        shorter_kind = getattr(shorter, "entity_kind", "").casefold()
                        taller_kind = getattr(taller, "entity_kind", "").casefold()
                        if "creature" in shorter_kind or "mascot" in shorter_kind or getattr(shorter, "proportion_constraints", None):
                            if "human" in taller_kind or taller_kind in {"unspecified being", "humanoid", "person"}:
                                scale_directives.append(
                                    f"Style separation: Creature character {shorter.name or shorter.id} and human character {taller.name or taller.id} must each strictly follow their respective canonical reference images without cross-contamination. "
                                    f"Human character {taller.name or taller.id} must strictly preserve natural adult human anatomy "
                                    f"(authentic realistic 7.5 to 8 head-to-body proportion, natural slender neck, natural adult torso length, and elongated legs), "
                                    f"realistic facial features, and natural eye proportions; do not apply chibi, anime, dwarf, or caricature distortion to {taller.name or taller.id}."
                                )
                # One has explicit height, other is an adult humanoid benchmark
                elif (h1 is not None and h2 is None) or (h2 is not None and h1 is None):
                    sized_char = c1 if h1 is not None else c2
                    unsized_char = c2 if h1 is not None else c1
                    s_height = h1 if h1 is not None else h2
                    unsized_kind = getattr(unsized_char, "entity_kind", "").casefold()
                    unsized_invs = " ".join(getattr(unsized_char, "visual_invariants", [])).casefold()
                    is_humanoid = (
                        unsized_kind in {"human", "person", "humanoid", "unspecified being"}
                        or any(tok in unsized_invs for tok in ("human", "man", "woman", "adult"))
                    )
                    if is_humanoid and s_height is not None and min(s_height, 175.0) > 0:
                        if s_height <= 120.0:
                            ratio = 175.0 / s_height
                            ratio_int = round(ratio)
                            if ratio >= 4.5:
                                anchor = "lower shin or ankle height"
                            elif ratio >= 2.6:
                                anchor = "knee or mid-thigh height"
                            elif ratio >= 1.7:
                                anchor = "waist or hip height"
                            else:
                                anchor = "chest or shoulder height"
                            scale_directives.append(
                                f"Scale relationship: {sized_char.name or sized_char.id} (height: {s_height:g} cm) stands at approximately 1:{ratio_int} scale against an adult human ({unsized_char.name or unsized_char.id}), "
                                f"reaching only to {unsized_char.name or unsized_char.id}'s {anchor}. "
                                f"{unsized_char.name or unsized_char.id} visibly towers over {sized_char.name or sized_char.id}."
                            )
                            scale_directives.append(
                                f"Style separation: Creature character {sized_char.name or sized_char.id} and human character {unsized_char.name or unsized_char.id} must each strictly follow their respective canonical reference images without cross-contamination. "
                                f"Human character {unsized_char.name or unsized_char.id} must strictly preserve natural adult human anatomy "
                                f"(authentic realistic 7.5 to 8 head-to-body proportion, natural slender neck, natural adult torso length, and elongated legs), "
                                f"realistic facial features, and natural eye proportions; do not apply chibi, anime, dwarf, or caricature distortion to {unsized_char.name or unsized_char.id}."
                            )
                        elif s_height >= 240.0:
                            scale_directives.append(
                                f"Scale relationship: {sized_char.name or sized_char.id} is a giant being ({s_height:g} cm), visibly towering over adult human {unsized_char.name or unsized_char.id}."
                            )

    # Case 2: Solo creature / character environmental scale grounding
    elif len(character_specs) == 1:
        char = character_specs[0]
        h = getattr(char, "physical_height_cm", None)
        if h is not None:
            scale_val = getattr(getattr(panel_plan, "subject_scale", None), "value", str(getattr(panel_plan, "subject_scale", ""))) if panel_plan else ""
            shot_val = getattr(getattr(panel_plan, "shot_type", None), "value", str(getattr(panel_plan, "shot_type", ""))) if panel_plan else (getattr(scene, "shot_type", "") if scene else "")
            scale_val_lower = scale_val.casefold()
            shot_val_lower = shot_val.casefold()

            is_framed_wide = any(term in scale_val_lower or term in shot_val_lower for term in ("full_shot", "wide", "medium", "establishing", "long"))
            is_close_up = any(term in scale_val_lower or term in shot_val_lower for term in ("close_up", "extreme_close_up", "macro"))

            if is_framed_wide and not is_close_up:
                shot_name = scale_val or shot_val or "wide"
                if h <= 60.0:
                    scale_directives.append(
                        f"Environmental scale grounding for solo miniature subject: "
                        f"Preserve the intended {shot_name} framing and camera composition while grounding {char.name or char.id}'s true physical scale: "
                        f"{char.name or char.id} is strictly {h:g} cm tall, visibly diminutive relative to surrounding environmental features (such as floor surfaces, furniture, walls, or architecture)."
                    )
                elif h >= 250.0:
                    scale_directives.append(
                        f"Environmental scale grounding for solo massive subject: "
                        f"Preserve the intended {shot_name} framing and camera composition while grounding {char.name or char.id}'s true physical scale: "
                        f"{char.name or char.id} is strictly {h:g} cm tall, visibly colossal relative to surrounding environmental features."
                    )

    return scale_directives


def build_scene_generation_prompt(
    line_and_tone: str,
    scene: SceneSpec,
    character_specs: List[CharacterSpec],
    visual_invariants: List[str],
    prohibited_deviations: List[str],
    story_facts: Optional[List[str]] = None,
    style_positive_constraints: Optional[List[str]] = None,
    catalogue_guidance: Optional[List[str]] = None,
    medium: Optional[str] = None,
    prop_specs: Optional[Dict[str, PropSpec]] = None,
    prop_states: Optional[Dict[str, str]] = None,
) -> str:
    """
    Deterministically compiles visual prompt instructions for the image generation adapter.
    Preserves M0 reference-anchored generation grammar, negative rule constraints,
    and catalogue knowledge directives.
    """
    parts = []

    # 1. Medium and style header
    header_medium = (medium or "comic book").strip().title()
    line_clean = line_and_tone.strip().rstrip(".")
    if line_clean.lower().startswith(header_medium.lower()):
        parts.append(f"{line_clean}.")
    else:
        parts.append(f"{header_medium} panel illustration, {line_clean}.")

    # 2. Reference anchoring clause
    parts.append("Preserve the exact character likeness from the canonical reference image:")

    # 3. Primary subject action and shot framing
    char_names = ", ".join([c.name or c.id.capitalize() for c in character_specs]) or "the character"
    panel_plan = getattr(scene, "panel_plan", None)
    scene_action = panel_plan.story_event if panel_plan else scene.action
    shot_type = (
        f"{panel_plan.shot_type.value}, subject scale {panel_plan.subject_scale.value}"
        if panel_plan else scene.shot_type
    )
    camera_angle = (
        f"camera position {panel_plan.camera_position.value}; angle {panel_plan.camera_angle.value}; "
        f"composition {panel_plan.composition_type.value}"
        if panel_plan else scene.camera_angle
    )
    lighting = (panel_plan.lighting_intent or scene.lighting) if panel_plan else scene.lighting
    scene_core = f"{char_names} {scene_action} ({shot_type})"
    if camera_angle:
        scene_core += f", {camera_angle}"
    if lighting:
        scene_core += f", {lighting}"
    parts.append(f"{scene_core}.")

    if character_specs:
        selected_names = [c.name or c.id for c in character_specs]
        parts.append(
            "The visible cast is exactly the creator-selected characters: "
            f"{', '.join(selected_names)}. Do not add any unselected story character or extra person/creature."
        )
        parts.append("Character identity rules are scoped to the named character only:")
        for char in character_specs:
            label = char.name or char.id
            required = [attribute.text for attribute in char.attributes if attribute.required and attribute.text.strip()]
            required.extend(item for item in char.visual_invariants if item.strip())
            required.extend(item for item in char.clothing_attributes if item.strip())

            # Canonical body morphology
            morph = getattr(char, "morphology", "").strip()
            c_kind = getattr(char, "entity_kind", "").casefold()
            c_invs = " ".join(getattr(char, "visual_invariants", [])).casefold()
            is_human = (
                "human" in c_kind
                or c_kind in {"person", "humanoid"}
                or any(tok in c_invs for tok in ("human", "man", "woman", "adult"))
            )
            if morph:
                required.append(f"body morphology: {morph}")
            elif is_human:
                required.append("body morphology: authentic adult human anatomy with natural 7.5 to 8 head-to-body proportion, slender natural neck, natural torso length, and elongated legs")

            # Check full-body / wide framing for human characters
            scale_val = getattr(getattr(panel_plan, "subject_scale", None), "value", str(getattr(panel_plan, "subject_scale", ""))) if panel_plan else ""
            shot_val = getattr(getattr(panel_plan, "shot_type", None), "value", str(getattr(panel_plan, "shot_type", ""))) if panel_plan else (getattr(scene, "shot_type", "") if scene else "")
            is_full_or_wide = any(term in scale_val.casefold() or term in shot_val.casefold() for term in ("full_shot", "wide", "establishing", "long"))
            if is_human and is_full_or_wide:
                required.append(
                    "full-body human anatomy: authentic adult human proportions (strictly 7.5 to 8 heads tall, with head approximately 1/8th of total height), "
                    "slender natural neck, natural adult torso, and elongated legs; strictly zero oversized head, zero compressed torso, and zero squat or dwarf distortion"
                )

            # Canonical proportion constraints
            props = getattr(char, "proportion_constraints", None)
            if isinstance(props, dict):
                h_ratio = props.get("head_ratio")
                b_ratio = props.get("body_ratio")
                if props.get("description"):
                    required.append(str(props["description"]).strip())
                elif h_ratio is not None and b_ratio is not None:
                    h_pct = int(round(float(h_ratio) * 100))
                    b_pct = int(round(float(b_ratio) * 100))
                    required.append(f"proportional balance: {h_pct}% head to {b_pct}% body ratio matching canonical reference")

            # Canonical physical height
            h_val = getattr(char, "physical_height_cm", None)
            if h_val is not None:
                required.append(f"physical height: strictly {float(h_val):g} cm tall")

            avoid = [char.restrictions] if isinstance(char.restrictions, str) else list(char.restrictions or [])
            if is_human:
                avoid.extend([
                    "squat body, compressed torso, short stubby legs",
                    "giant head relative to body",
                    "caricature proportions, chibi or dwarf anatomy",
                    "distorted human proportions"
                ])
            avoid.extend(
                f"no {attribute.id}"
                for attribute in char.attributes
                if not attribute.required and attribute.id.strip()
            )
            required_text = "; ".join(dict.fromkeys(item.strip() for item in required if item.strip())) or "No extra visual traits are specified."
            avoid_text = "; ".join(dict.fromkeys(str(item).strip() for item in avoid if str(item).strip())) or "No character-specific exclusions are specified."
            parts.append(
                f"{label} [{char.id}] — preserve: {required_text}. "
                f"Reference fidelity: Anatomy, silhouette, body proportions, and visual features must strictly follow the canonical reference image without stylization, head enlargement, or body reduction. "
                f"Rules only for {label}: {avoid_text}. "
                "Never apply this character's exclusions to another selected character."
            )

        scale_directives = _compile_scale_directives(character_specs, panel_plan, scene)
        if scale_directives:
            parts.extend(scale_directives)

    object_rows = []
    for prop_id, prop in (prop_specs or {}).items():
        state = (prop_states or {}).get(prop_id)
        identity = [prop.name, prop.description, prop.form_and_proportions]
        identity.extend(prop.stable_invariants or prop.required_attributes)
        identity.extend(prop.materials)
        identity.extend(prop.components)
        identity.extend(prop.distinctive_marks)
        stable_text = "; ".join(dict.fromkeys(str(value).strip() for value in identity if str(value or "").strip()))
        state_text = f" Current state in this panel: {state}. Do not treat this state as a permanent identity change." if state else ""
        object_rows.append(f"{prop.name} [{prop_id}]@v{prop.version}: {stable_text}.{state_text}")
    if object_rows:
        referenced_objects = [prop_id for prop_id, prop in (prop_specs or {}).items() if prop.reference_assets]
        parts.append(
            "Preserve the selected recurring object designs from stable specifications. "
            "When a labeled object-reference image is attached, match that same physical design. "
            "For a text-only draft's first image, follow its saved identity specification; visual consistency is not verified yet. "
            + ("Object reference images are attached for: " + ", ".join(referenced_objects) + ". " if referenced_objects else "No object-reference images are attached for this panel. ")
            + "Do not replace, redesign, merge, or duplicate them. " + " ".join(object_rows)
        )

    parts.append(
        "Create one standalone artwork image for one comic panel. Do not create a comic page, "
        "multi-panel grid, split screen, diptych, storyboard, or extra framed scene."
    )

    if panel_plan:
        parts.append(
            f"Narrative function: {panel_plan.narrative_function.value}. "
            f"Reader takeaway: {panel_plan.reader_takeaway}. "
            f"Emotional intent: {panel_plan.emotional_intent}. "
            f"Composition focus: {panel_plan.visual_focus}."
        )
        if panel_plan.movement_direction:
            parts.append(f"Movement direction: {panel_plan.movement_direction}.")
        if panel_plan.environment:
            parts.append(f"Panel environment: {panel_plan.environment}.")
        if panel_plan.protected_visual_elements:
            parts.append(f"Keep these visual elements visible: {', '.join(panel_plan.protected_visual_elements)}.")
        if panel_plan.prohibited_visual_elements:
            parts.append(f"Do not introduce these elements: {', '.join(panel_plan.prohibited_visual_elements)}.")
        parts.append(f"Transition from the prior panel: {panel_plan.transition_role.value}.")
        if panel_plan.text.reserve_space:
            region = panel_plan.text.preferred_region.value if panel_plan.text.preferred_region else "reserved negative space"
            parts.append(
                f"Leave {region} open for a separately composited {panel_plan.text.carrier.value}; "
                "do not draw final text or speech bubbles into the artwork."
            )
        else:
            parts.append("Do not draw final dialogue, captions, lettering, or speech bubbles into the artwork.")

        # Natural Character Performance, Gaze Direction & Somatic Congruence
        if character_specs:
            acting_cues = []
            has_stylized_or_creature = any(any(token in getattr(c, "entity_kind", "").casefold() for token in ("creature", "animal", "stylized", "beast", "monster", "mascot")) for c in character_specs)
            has_mechanical = any(getattr(c, "entity_kind", "").casefold() in {"robot", "cyborg", "machine", "automaton"} for c in character_specs)
            has_human = not (has_stylized_or_creature or has_mechanical) or any(getattr(c, "entity_kind", "").casefold() in {"human", "humanoid", "person"} for c in character_specs)

            if panel_plan and panel_plan.emotional_intent:
                acting_cues.append(
                    f"Cinematic visual acting: convey '{panel_plan.emotional_intent}' with subtle, believable psychological tension, natural restraint, and somatic restraint. "
                    "Expressions must be anatomically natural, understated, and context-dependent (subtle brow asymmetry, tightened jaw, pressed lips, controlled gaze, natural neck and shoulder tension). "
                    "Strictly avoid generic permanently wide eyes, exaggerated gaping open mouths, frozen shocked expressions, melodramatic grimaces, or vacant stares."
                )

            # Camera Staging & Anti-Portrait Diversity
            if panel_plan:
                pos_val = getattr(getattr(panel_plan, "camera_position", None), "value", str(getattr(panel_plan, "camera_position", ""))).casefold()
                shot_val = getattr(getattr(panel_plan, "shot_type", None), "value", str(getattr(panel_plan, "shot_type", ""))).casefold()
                cinematic_framing = []
                if "profile" in pos_val:
                    cinematic_framing.append("Camera framing: true 90-degree side profile view; show character from the side with dramatic horizontal silhouette and directional lighting, not a three-quarter portrait.")
                elif "rear" in pos_val or "back" in pos_val:
                    cinematic_framing.append("Camera framing: rear view looking past the character's back/shoulder into the environment; face is partially turned away or obscured.")
                elif "over_the_shoulder" in pos_val:
                    cinematic_framing.append("Camera framing: over-the-shoulder (OTS) shot; foreground shoulder frames the composition looking directly at the narrative focal object.")
                elif "environmental" in pos_val or "wide" in shot_val:
                    cinematic_framing.append("Camera framing: cinematic environmental wide shot with meaningful negative space; the environment and architecture tell the story, character is organically integrated into the space rather than filling the frame as a portrait.")

                if cinematic_framing:
                    acting_cues.extend(cinematic_framing)
                else:
                    acting_cues.append("Cinematic direction: Tell the story through purposeful framing and environmental interaction; do not produce a generic character bust showcase or repetitive three-quarter headshot.")

            # Determine character interaction & gaze target vs composition focus
            scene_action_lower = scene.action.casefold() if scene.action else ""
            char_count = len(character_specs)

            if has_human:
                # Distinguish gaze target, gaze direction, and head orientation
                if char_count > 1 and any(token in scene_action_lower for token in ("talk", "look at", "faces", "confront", "argues", "speaks", "turns to")):
                    gaze_dir = "eyes directed toward conversational partner with natural eye-head coordination; conjugate gaze on partner's eye level"
                elif any(token in scene_action_lower for token in ("read", "inspect", "examin", "hold", "tinker", "repair", "reach", "work")):
                    gaze_dir = "head slightly inclined forward with eyes focused downward on the object of action; realistic optical vergence without crossed eyes"
                elif any(token in scene_action_lower for token in ("look up", "watches", "notices", "stares at", "glances")):
                    gaze_dir = "head and gaze oriented toward the observed action; sightlines track along a shared focal axis without divergent pupils"
                else:
                    gaze_dir = "natural sightline aligned with character action; conjugate optical tracking without strabismus or wandering eyes"

                acting_cues.append(
                    f"Ocular alignment: both eyes and sightlines converge accurately; {gaze_dir}; maintain subtle eyelid tension and natural asymmetrical expression."
                )

            if has_stylized_or_creature:
                acting_cues.append(
                    "Non-human/stylized performance: preserve canonical entity morphology without imposing human facial features; "
                    "express intent through head tilt, body turn, and creature silhouette."
                )

            if has_mechanical:
                acting_cues.append(
                    "Mechanical performance: convey state through optic sensor alignment, visor orientation, and mechanical posture."
                )

            acting_cues.append(
                "Posture-face congruence: physical body stance, spine line-of-action, and shoulder tension must reinforce the scene emotion."
            )
            parts.append(" ".join(acting_cues))

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

    # 8. Story-wide facts (if present)
    if story_facts:
        facts_str = "; ".join(story_facts)
        parts.append(f"Story context: {facts_str}.")

    # 9. Style positive directives (if present)
    if style_positive_constraints:
        pos_str = ", ".join(style_positive_constraints)
        parts.append(f"Style directives: {pos_str}.")

    # 10. Catalogue guidance (if present)
    if catalogue_guidance:
        cat_str = "; ".join(catalogue_guidance)
        parts.append(f"Catalogue guidance: {cat_str}.")

    # 11. Negative constraints / prohibited deviations
    combined_negatives = list(prohibited_deviations)
    if character_specs:
        has_stylized_or_creature = any(getattr(c, "entity_kind", "").casefold() in {"creature", "animal", "stylized", "beast", "monster"} for c in character_specs)
        has_mechanical = any(getattr(c, "entity_kind", "").casefold() in {"robot", "cyborg", "machine", "automaton"} for c in character_specs)
        has_human = not (has_stylized_or_creature or has_mechanical) or any(getattr(c, "entity_kind", "").casefold() in {"human", "humanoid", "person"} for c in character_specs)
        if has_human:
            for defect in (
                "crossed eyes", "divergent pupils", "wandering gaze", "blank stare",
                "distorted facial anatomy", "squat compressed body", "caricature dwarf proportions",
                "oversized head on adult body", "distorted human anatomy",
                "repetitive three-quarter portraits", "AI character showcase pose",
                "permanently wide eyes", "exaggerated gaping open mouth", "generic default shocked expression",
                "frozen melodramatic grimace", "excessive random scratches", "noisy scribble hatching",
                "plastic faces", "over-sharpened details",
            ):
                if defect not in combined_negatives:
                    combined_negatives.append(defect)
    if combined_negatives:
        parts.append(f"Avoid these prohibited visual traits: {', '.join(combined_negatives)}.")

    # Lettering is a separate downstream layer (E4-E6). Keep this invariant in
    # the base prompt even when the caller supplied no S5 plan.
    parts.append(
        "Artwork only: do not render words, labels, lettering, speech balloons, "
        "captions, logos, or watermarks inside the image."
    )

    return " ".join(parts)

def build_panel_context_packet(
    story_bible: Any,
    scene: SceneSpec,
    panel_id: str,
    story_id: str = "story_01",
    project_id: str = "inkloop",
    model: str = "muse-image-1.0",
    generation_params: Optional[Dict[str, Any]] = None,
    knowledge_retriever: Optional[Any] = None,
    enable_catalogue_retrieval: bool = True,
    retrieval_budget: Optional[Any] = None,
    retrieval_policy: Optional[Any] = None,
    style_profile_override: Optional[Any] = None,
) -> PanelContextPacket:
    """
    Assembles an independent context packet for an individual panel.
    Every panel receives a freshly isolated context derived purely from the Story Bible,
    explicit scene specification, and evidence-backed knowledge catalogue retrieval (T6.3).
    No hidden conversational state is used.
    """
    gen_params = generation_params or {"n": 1}
    if scene.panel_plan:
        if scene.panel_plan.scene_id != scene.scene_id:
            raise ValueError("SceneSpec scene_id must match its attached S5 panel plan.")
        if scene.panel_plan.panel_id != panel_id:
            raise ValueError("Context panel_id must match the attached S5 panel plan's panel_id.")
        if set(scene.character_ids) != set(scene.panel_plan.character_ids):
            raise ValueError("SceneSpec character_ids must match its attached S5 panel plan.")
        if set(scene.prop_ids) != set(scene.panel_plan.prop_ids):
            raise ValueError("SceneSpec prop_ids must match its attached S5 panel plan.")
    if set(scene.prop_states) - set(scene.prop_ids):
        raise ValueError("SceneSpec prop_states may only describe selected prop_ids.")
    panel_plan_data = scene.panel_plan.model_dump(mode="json") if scene.panel_plan else None

    # Extract version and identifiers
    bible_version = str(getattr(story_bible, "bible_version", getattr(story_bible, "version", "1.0.0")))
    bible_id = getattr(story_bible, "bible_id", getattr(story_bible, "project_id", "inkloop"))
    canon_hash = getattr(story_bible, "canon_hash", None)
    story_facts = list(getattr(story_bible, "story_facts", []))
    line_and_tone, style_negatives, style_meta = _resolve_bible_style_rules(
        story_bible,
        style_profile_override=style_profile_override,
    )

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

    # 2b. Resolve only the explicit object IDs selected for this panel.
    all_props = getattr(story_bible, "props", {}) or {}
    prop_specs: Dict[str, PropSpec] = {}
    prop_reference_assets: List[ReferenceAsset] = []
    for prop_id in scene.prop_ids:
        raw_prop = all_props.get(prop_id)
        if raw_prop is None:
            raise ValueError(f"Selected prop '{prop_id}' is not present in the active Story Bible.")
        prop = _normalize_prop_spec(raw_prop, prop_id)
        prop_specs[prop_id] = prop
        prop_reference_assets.extend(prop.reference_assets)

    # 3. Assemble visual invariants
    visual_invariants: List[str] = []
    for char in character_specs:
        char_label = char.name or char.id.capitalize()
        for attr in char.attributes:
            if attr.required:
                visual_invariants.append(f"{char_label} ({char.id}) {attr.id}: {attr.text}")
        for inv in char.visual_invariants:
            inv_str = f"{char_label}: {inv}"
            if inv_str not in visual_invariants and inv not in visual_invariants:
                visual_invariants.append(inv_str)

    # Keep character exclusions scoped by name. The attached negative-clause
    # list is consumed by some adapters, so preserve optional-trait exclusions
    # there too without turning one character's rule into a global prohibition.
    prohibited_deviations: List[str] = list(style_negatives)
    for char in character_specs:
        char_label = char.name or char.id.capitalize()
        for attr in char.attributes:
            if not attr.required and attr.id.strip():
                prohibited_deviations.append(
                    f"For {char_label} only: do not depict {attr.text or attr.id}."
                )

    # 5. Retrieve deterministic knowledge from catalogue (T6.3)
    catalogue_version: Optional[str] = None
    knowledge_selection_hash: Optional[str] = None
    selected_knowledge_ids: List[str] = []
    knowledge_provenance_ids: List[str] = []
    knowledge_rationale: Dict[str, str] = {}
    catalogue_positive_clauses: List[str] = []

    style_obj = style_profile_override or getattr(story_bible, "style", None)
    style_id = (
        getattr(style_obj, "profile_id", None)
        or getattr(style_obj, "id", getattr(style_obj, "style_id", "default_style"))
        if style_obj else "default_style"
    )
    style_medium = (
        style_meta.get("medium", "") if style_profile_override
        else getattr(style_obj, "medium", "") if style_obj else ""
    )

    if enable_catalogue_retrieval:
        from app.catalogue.retrieval import get_default_knowledge_retriever
        from app.catalogue.retrieval_models import KnowledgeRetrievalRequest, KnowledgeBudget, KnowledgeRetrievalPolicy

        retriever = knowledge_retriever or get_default_knowledge_retriever()
        palette_val = style_meta.get("palette")
        panel_plan = getattr(scene, "panel_plan", None)
        ret_req = KnowledgeRetrievalRequest(
            scene_id=scene.scene_id,
            shot_type=(
                f"{panel_plan.shot_type.value} {panel_plan.subject_scale.value}"
                if panel_plan else scene.shot_type
            ),
            action=(
                f"{panel_plan.story_event}; focus: {panel_plan.visual_focus}; composition: {panel_plan.composition_type.value}"
                if panel_plan else scene.action
            ),
            camera_angle=(
                f"{panel_plan.camera_position.value} {panel_plan.camera_angle.value}"
                if panel_plan else scene.camera_angle
            ),
            lighting=(panel_plan.lighting_intent or scene.lighting) if panel_plan else scene.lighting,
            panel_instructions=(
                panel_plan.image_brief if panel_plan else scene.panel_instructions
            ),
            character_ids=scene.character_ids,
            has_reference_images=bool(reference_assets),
            visual_invariants=visual_invariants,
            style_medium=style_medium,
            style_line_and_tone=line_and_tone,
            style_palette=str(palette_val) if palette_val else None,
            style_positive_constraints=style_meta.get("positive_constraints", []),
            style_negative_constraints=prohibited_deviations,
            target_model=model,
            budget=retrieval_budget or KnowledgeBudget(),
            policy=retrieval_policy or KnowledgeRetrievalPolicy(),
        )
        ret_result = retriever.retrieve(ret_req)
        catalogue_version = ret_result.catalogue_version
        knowledge_selection_hash = ret_result.selection_hash
        selected_knowledge_ids = ret_result.selected_record_ids
        knowledge_provenance_ids = ret_result.provenance_source_ids
        knowledge_rationale = ret_result.selection_rationale
        catalogue_positive_clauses = ret_result.positive_prompt_clauses

        # Merge negative constraints from catalogue
        if style_profile_override is None:
            for n_clause in ret_result.negative_prompt_clauses:
                if n_clause not in prohibited_deviations:
                    prohibited_deviations.append(n_clause)

    # 6. Build generation prompt
    prompt = build_scene_generation_prompt(
        line_and_tone=line_and_tone,
        scene=scene,
        character_specs=character_specs,
        visual_invariants=visual_invariants,
        prohibited_deviations=prohibited_deviations,
        story_facts=story_facts,
        style_positive_constraints=style_meta.get("positive_constraints"),
        catalogue_guidance=(catalogue_positive_clauses if style_profile_override is None else []),
        medium=style_meta.get("medium"),
        prop_specs=prop_specs,
        prop_states=scene.prop_states,
    )

    # 7. Extract geometry and continuity
    continuity_summary = scene.previous_panel_summary
    dimensions = getattr(scene, "dimensions", None) or gen_params.get("dimensions")
    aspect_ratio = getattr(scene, "aspect_ratio", None) or gen_params.get("aspect_ratio")
    effective_action = scene.panel_plan.story_event if scene.panel_plan else scene.action
    effective_shot = (
        f"{scene.panel_plan.shot_type.value}, {scene.panel_plan.subject_scale.value}"
        if scene.panel_plan else scene.shot_type
    )
    effective_description = f"{scene.title}: {effective_action} ({effective_shot})"

    # 7. Construct semantic payload for reproducible fingerprint computation
    fingerprint_payload = {
        "story_id": story_id,
        "project_id": project_id,
        "bible_id": bible_id,
        "bible_version": bible_version,
        "canon_hash": canon_hash,
        "story_facts": sorted(story_facts) if isinstance(story_facts, list) else story_facts,
        "style_id": style_id,
        "style_profile_version": getattr(style_profile_override, "version", None),
        "style_medium": style_medium,
        "style_line_and_tone": line_and_tone,
        "style_palette": style_meta.get("palette"),
        "style_positive_constraints": sorted(style_meta.get("positive_constraints", [])),
        "style_lighting_constraints": sorted(style_meta.get("lighting_constraints", [])),
        "style_background_detail_rules": style_meta.get("background_detail_rules", ""),
        "panel_id": panel_id,
        "scene_id": scene.scene_id,
        "scene_index": scene.scene_index,
        "scene_title": scene.title,
        "scene_description": effective_description,
        "scene_action": effective_action,
        "scene_shot_type": effective_shot,
        "camera_angle": (
            f"{scene.panel_plan.camera_position.value}/{scene.panel_plan.camera_angle.value}"
            if scene.panel_plan else scene.camera_angle
        ),
        "lighting": (
            (scene.panel_plan.lighting_intent or scene.lighting)
            if scene.panel_plan else scene.lighting
        ),
        "panel_instructions": scene.panel_instructions,
        "panel_plan": panel_plan_data,
        "dimensions": dimensions,
        "aspect_ratio": aspect_ratio,
        "generation_prompt": prompt,
        "character_ids": sorted(scene.character_ids),
        "prop_ids": sorted(scene.prop_ids),
        "prop_states": dict(sorted(scene.prop_states.items())),
        "prop_specs": {
            prop_id: {
                "version": prop.version,
                "name": prop.name,
                "description": prop.description,
                "form_and_proportions": prop.form_and_proportions,
                "required_attributes": sorted(prop.required_attributes),
                "stable_invariants": sorted(prop.stable_invariants),
                "materials": sorted(prop.materials),
                "palette": sorted(prop.palette),
                "components": sorted(prop.components),
                "distinctive_marks": sorted(prop.distinctive_marks),
                "allowed_states": sorted(prop.allowed_states),
            }
            for prop_id, prop in sorted(prop_specs.items())
        },
        "prop_reference_assets": [
            {"asset_id": r.asset_id, "content_hash": r.content_hash, "mime_type": r.mime_type}
            for r in prop_reference_assets
        ],
        "character_specs": [
            {
                "id": c.id,
                "name": c.name or c.id.capitalize(),
                "attributes": [{"id": a.id, "text": a.text, "required": a.required} for a in c.attributes],
                "visual_invariants": sorted(c.visual_invariants),
                "restrictions": sorted(c.restrictions),
                "clothing_attributes": sorted(c.clothing_attributes),
            }
            for c in character_specs
        ],
        "reference_assets": [
            {
                "asset_id": r.asset_id,
                "content_hash": r.content_hash,
                "mime_type": r.mime_type
            }
            for r in reference_assets
        ],
        "previous_panel_id": scene.previous_panel_id,
        "previous_panel_continuity": continuity_summary,
        "scene_state": scene.scene_state,
        "visual_invariants": sorted(set(visual_invariants)),
        "prohibited_deviations": sorted(set(prohibited_deviations)),
        "model": model,
        "generation_params": gen_params,
        "catalogue_version": catalogue_version,
        "knowledge_selection_hash": knowledge_selection_hash,
        "selected_knowledge_ids": sorted(selected_knowledge_ids),
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
        panel_plan=panel_plan_data,
        scene_description=effective_description,
        generation_prompt=prompt,
        character_ids=scene.character_ids,
        character_specs=character_specs,
        reference_assets=reference_assets,
        prop_ids=list(scene.prop_ids),
        prop_specs=prop_specs,
        prop_reference_assets=prop_reference_assets,
        prop_states=dict(scene.prop_states),
        dimensions=dimensions,
        aspect_ratio=aspect_ratio,
        previous_panel_continuity=continuity_summary,
        scene_state=scene.scene_state,
        visual_invariants=visual_invariants,
        prohibited_deviations=prohibited_deviations,
        model=model,
        generation_params=gen_params,
        context_fingerprint=fingerprint,
        catalogue_version=catalogue_version,
        knowledge_selection_hash=knowledge_selection_hash,
        selected_knowledge_ids=selected_knowledge_ids,
        knowledge_provenance_ids=knowledge_provenance_ids,
        knowledge_rationale=knowledge_rationale,
    )
