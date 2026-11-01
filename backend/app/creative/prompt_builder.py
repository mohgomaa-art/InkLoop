"""
Prompt and Context Builder for Style Copier and Character Copier.
Ensures strict semantic separation between:
1. Visual Rendering Style (linework, shading, screentone, palette)
2. Being Identity (creator-declared form, materials, features, and canonical invariants)
3. Scene & Composition Intent (action, camera angle, shot scale, dynamic poses)
4. Reference Image Roles (preventing cross-contamination or style-character leakage)
"""
from typing import List, Optional, Dict, Any
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    GenerationReferenceSet,
    SemanticReferenceRole,
)


def build_creative_generation_prompt(
    scene_action: str,
    shot_type: str = "Medium shot, eye-level angle",
    style_profile: Optional[StyleProfile] = None,
    character_profiles: Optional[List[CharacterIdentityProfile]] = None,
    reference_set: Optional[GenerationReferenceSet] = None,
    composition_notes: Optional[str] = None,
    lighting_intent: Optional[str] = None,
    additional_negatives: Optional[List[str]] = None,
    target_to_edit_instructions: Optional[str] = None,
) -> str:
    """
    Deterministically compiles a multi-reference generation prompt.
    Disambiguates style vs identity vs composition roles to prevent leakage.
    """
    chars = character_profiles or []
    sections: List[str] = []

    # =========================================================================
    # 1. Medium and Visual Style Core
    # =========================================================================
    if style_profile and style_profile.style_prompt_core:
        sections.append(f"Visual Style: {style_profile.style_prompt_core.strip()}")
    elif style_profile and style_profile.analysis:
        medium = style_profile.analysis.medium or "High quality comic and graphic novel illustration"
        traits_list = []
        for dim, trait in style_profile.analysis.traits.items():
            if trait.rules:
                traits_list.append("; ".join(trait.rules))
            elif trait.summary:
                traits_list.append(trait.summary)
        style_text = f"{medium}. " + " ".join(traits_list)
        sections.append(f"Visual Style: {style_text.strip()}")
    else:
        sections.append("Visual Style: High quality comic and graphic novel illustration, defined linework, balanced lighting and color harmony.")

    # =========================================================================
    # 2. Reference Image Semantic Roles Disambiguation
    # =========================================================================
    ref_clauses = []
    if reference_set and reference_set.references:
        for idx, ref in enumerate(reference_set.references, 1):
            if ref.role == SemanticReferenceRole.STYLE_REFERENCE:
                ref_clauses.append(
                    f"Reference #{idx} is a STYLE REFERENCE: match rendering medium, linework, color palette, and shading technique only. "
                    "DO NOT copy any characters, faces, clothing, or layout from Reference #"
                    f"{idx}."
                )
            elif ref.role == SemanticReferenceRole.CHARACTER_REFERENCE:
                char_label = f" for '{ref.character_id}'" if ref.character_id else ""
                view_label = f" ({ref.view_role.value if hasattr(ref.view_role, 'value') else ref.view_role} view)" if ref.view_role else ""
                ref_clauses.append(
                    f"Reference #{idx} is a BEING IDENTITY REFERENCE{char_label}{view_label}: "
                    "preserve the depicted being's actual form, feature count, materials, markings, and declared identity anchors. Do not humanize it or invent a face, hair, limbs, clothing, or other anatomy absent from the profile/reference. "
                    "Adapt pose, emotion, and angle to the requested scene action."
                )
            elif ref.role == SemanticReferenceRole.COMPOSITION_REFERENCE:
                ref_clauses.append(
                    f"Reference #{idx} is a COMPOSITION REFERENCE: adapt panel framing and camera perspective only."
                )
            elif ref.role == SemanticReferenceRole.TARGET_TO_EDIT:
                ref_clauses.append(
                    f"Reference #{idx} is the BASE IMAGE undergoing selective refinement: "
                    "preserve all established correct regions while applying requested adjustments."
                )
            elif ref.role == SemanticReferenceRole.POSE_REFERENCE:
                ref_clauses.append(
                    f"Reference #{idx} is a POSE REFERENCE: use body gesture and dynamic posture only."
                )

    if ref_clauses:
        sections.append("Reference Conditioning Directives: " + " ".join(ref_clauses))

    # =========================================================================
    # 3. Scene Action, Camera, and Dramatic Intent
    # =========================================================================
    char_names = ", ".join([c.name for c in chars]) if chars else "the subject"
    scene_core = f"Scene Action: {char_names} {scene_action.strip()} ({shot_type.strip()})"
    if lighting_intent:
        scene_core += f", lighting: {lighting_intent.strip()}"
    if composition_notes:
        scene_core += f". Composition directive: {composition_notes.strip()}"
    sections.append(scene_core + ".")

    # =========================================================================
    # 4. Character Identity Invariants & Intentional Variations
    # =========================================================================
    for c in chars:
        char_parts = []
        form = "; ".join(part for part in [c.entity_kind, c.morphology, c.surface_description, ", ".join(c.appendages_or_parts), ", ".join(c.sensory_features), c.locomotion] if part)
        if form:
            char_parts.append(
                f"Actual creator-defined form: {form}. Do not humanize or add absent parts, senses, materials, coverings, or anatomy"
            )
        if c.prompt_identity_core:
            char_parts.append(f"Likeness: {c.prompt_identity_core}")
        if c.identity_invariants:
            char_parts.append("Mandatory invariants: " + "; ".join(c.identity_invariants))
        if c.base_outfit:
            outfit_desc = c.base_outfit.get("description") or c.base_outfit.get("name")
            if outfit_desc:
                char_parts.append(f"Costume: {outfit_desc}")
        if c.allowed_variations:
            char_parts.append("Allowed dynamic variations: " + "; ".join(c.allowed_variations))
        if c.forbidden_drift:
            char_parts.append("Forbidden identity drift: " + "; ".join(c.forbidden_drift))
        if c.identity_features:
            char_parts.append("Typed identity features: " + "; ".join(f"{feature.label}: {feature.description} ({feature.stability})" for feature in c.identity_features))

        if char_parts:
            sections.append(f"Character '{c.name}' Constraints: " + ". ".join(char_parts) + ".")

    # Multi-character disambiguation
    if len(chars) > 1:
        sections.append(
            "Multi-character requirement: keep each being's declared form and identity features distinct. "
            "Do not merge traits or transfer parts, markings, materials, or declared coverings between beings."
        )

    # =========================================================================
    # 5. Targeted Edit Instructions (if applicable)
    # =========================================================================
    if target_to_edit_instructions:
        sections.append(f"Targeted Correction: {target_to_edit_instructions.strip()}")

    # =========================================================================
    # 6. Negative Constraints and Clean Artwork Boundary
    # =========================================================================
    negatives = []
    if style_profile and style_profile.negative_constraints:
        negatives.extend(style_profile.negative_constraints)
    if additional_negatives:
        negatives.extend(additional_negatives)

    # Mandatory lettering exclusion invariant (E4-E6 lettering handled downstream)
    negatives.append("dialogue text")
    negatives.append("speech balloons")
    negatives.append("captions")
    negatives.append("watermarks")

    # Remove duplicates preserving order
    deduped_negatives = list(dict.fromkeys(negatives))
    sections.append(f"Prohibited elements (Negative Constraints): {', '.join(deduped_negatives)}.")
    sections.append("Clean artwork only: do not draw lettering, speech bubbles, sound effects, or watermarks inside the image.")

    return "\n\n".join(sections)
