"""
Production Prompt and Context Assembly Engine for InkLoop.
Compiles versioned machine-readable creative contracts into deterministic prompts
for downstream Image Generation (E1) and Character Copier reference conditioning.
"""
from typing import Dict, Any, List, Optional
from app.creative.schemas import (
    CreativeContractsPackage,
    CharacterIdentityProfile,
    VisualStyleProfile,
)


class CreativePromptCompiler:
    """Compiles structured creative contracts into production panel prompts."""

    @classmethod
    def compile_panel_prompt(
        cls,
        contracts: CreativeContractsPackage,
        character_profiles: Optional[Dict[str, CharacterIdentityProfile]] = None,
        style: Optional[VisualStyleProfile] = None,
        scene_action: str = "",
        active_character_ids: Optional[List[str]] = None,
        camera_shot: Optional[str] = "medium shot",
        location_name: Optional[str] = None,
        # Convenience params
        character: Optional[CharacterIdentityProfile] = None,
        scene_description: Optional[str] = None,
        emotion: Optional[str] = None,
        outfit_id: Optional[str] = None,
        is_action_shot: bool = False,
    ) -> Any:
        """
        Assembles structured prompt sections enforcing instruction precedence:
        1. Action & scene intent
        2. Character visual invariants & outfit
        3. Visual style linework & rendering rules
        4. Environment anchors
        5. Negative constraints
        """
        # Resolve convenience aliases
        action_text = (scene_description or scene_action or "").strip()
        chars_dict = dict(character_profiles or {})
        if character:
            chars_dict[character.character_id] = character
            active_ids = [character.character_id]
        else:
            active_ids = list(active_character_ids or [])

        prompt_parts: List[str] = []

        # 1. Action & Camera
        if is_action_shot:
            camera_prefix = "Dynamic high-action dynamic shot"
        elif camera_shot:
            camera_prefix = f"{camera_shot.capitalize()}"
        else:
            camera_prefix = "Cinematic panel"
        prompt_parts.append(f"{camera_prefix} of {action_text}")

        # 2. Emotion
        if emotion and emotion != "neutral":
            prompt_parts.append(f"show the requested emotional signal through the being's established features and body language: {emotion}")

        # 3. Being Descriptions & Mandatory Invariants. Never infer human anatomy
        # from the generic word "character"; use only the selected profile.
        char_tokens = []
        for cid in active_ids:
            if cid in chars_dict:
                cp = chars_dict[cid]
                invariants_str = ", ".join(cp.visual_invariants)
                outfit_str = f"outfit: {', '.join(cp.base_outfit.garments)}" if cp.base_outfit and cp.base_outfit.garments else ""
                feature_str = "; ".join(feature.description for feature in cp.identity_features)
                form_str = "; ".join(part for part in [cp.entity_kind, cp.morphology, cp.surface_description, ", ".join(cp.appendages_or_parts), ", ".join(cp.sensory_features), feature_str, invariants_str, outfit_str] if part)
                char_tokens.append(f"{cp.name} [{form_str}]")
            elif cid in contracts.characters:
                c_contract = contracts.characters[cid]
                invariants_str = ", ".join(c_contract.mandatory_invariants)
                char_tokens.append(f"character {c_contract.character_name} ({invariants_str})")

        if char_tokens:
            prompt_parts.append("featuring " + " and ".join(char_tokens))

        # 4. Location
        if location_name:
            prompt_parts.append(f"in {location_name}")

        # 5. Visual Style & Medium
        if style:
            style_tokens = [
                style.medium,
                style.shape_language,
                f"lighting: {', '.join(style.lighting_rules[:2])}" if style.lighting_rules else "",
                f"palette: {', '.join(style.palette_and_accent_rules[:2])}" if style.palette_and_accent_rules else "",
            ]
            clean_style = [t for t in style_tokens if t]
            if clean_style:
                prompt_parts.append("art style: " + ", ".join(clean_style))
        elif contracts.style:
            st = contracts.style
            prompt_parts.append(f"art style: {st.target_medium}, {', '.join(st.rendering_invariants[:3])}")

        # Join positive prompt
        final_positive = ", ".join(prompt_parts)
        return final_positive

    @classmethod
    def compile_negative_prompt(
        cls,
        contracts: CreativeContractsPackage,
        character_profiles: Optional[Dict[str, CharacterIdentityProfile]] = None,
        style: Optional[VisualStyleProfile] = None,
        active_character_ids: Optional[List[str]] = None,
        character: Optional[CharacterIdentityProfile] = None,
    ) -> str:
        """Assembles unified negative prompt from style negative constraints and character drift rules."""
        chars_dict = dict(character_profiles or {})
        if character:
            chars_dict[character.character_id] = character
            active_ids = [character.character_id]
        else:
            active_ids = list(active_character_ids or [])

        negative_parts = []
        if style:
            negative_parts.extend(style.negative_constraints)
        if contracts.style:
            negative_parts.extend(contracts.style.negative_prompt_additions)

        for cid in active_ids:
            if cid in chars_dict:
                negative_parts.extend(chars_dict[cid].forbidden_visual_drift)
            elif cid in contracts.characters:
                negative_parts.extend(contracts.characters[cid].forbidden_visual_drift)

        # Extra parts, unusual proportions, or absent faces may be canonical.
        negative_parts.append("blurry")

        # Deduplicate
        seen = set()
        clean_negative = []
        for np in negative_parts:
            low = np.lower().strip()
            if low and low not in seen:
                seen.add(low)
                clean_negative.append(np)

        return ", ".join(clean_negative)
