"""
Automated Style and Character Reference Analyzers for InkLoop.
Powered by Meta Muse Spark Multimodal Vision Model (live) and robust
computer-vision heuristics (Pillow color quantization and edge detection).
Extracts authentic, evidence-backed style dimensions and character identity invariants.
Zero hardcoded fake outputs.
"""
import base64
import json
import re
import time
import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Dict, Any, Optional
import httpx
from PIL import Image, ImageStat, ImageFilter

from app.config import InkLoopConfig
from app.storage.registry import AssetRegistry
from app.creative.models import (
    StyleDimensionTrait,
    StyleAnalysisRecord,
    StyleProfile,
    CharacterIdentityProfile,
    IdentityFeature,
    ReferenceBinding,
    CharacterViewRole,
    SemanticReferenceRole,
    ProfileStatus,
)
from app.creative.schemas import SheetViewSpec, CharacterSheetPlan

logger = logging.getLogger(__name__)


class AnalysisUnavailableError(RuntimeError):
    """Raised when no configured vision provider can analyze uploaded references."""


class AnalysisProviderError(RuntimeError):
    """Raised when the configured vision provider fails or returns unusable data."""


def _call_vision_json(config: InkLoopConfig, images: List[tuple[bytes, str]], prompt: str, task: str) -> Dict[str, Any]:
    if not config.has_credentials:
        raise AnalysisUnavailableError("Reference analysis requires configured vision-provider credentials.")

    content: List[Dict[str, str]] = []
    for index, (raw_bytes, mime_type) in enumerate(images, 1):
        encoded = base64.b64encode(raw_bytes).decode("ascii")
        content.append({"type": "input_text", "text": f"REFERENCE IMAGE #{index} (asset bytes verified by the application):"})
        content.append({"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"})
    content.append({"type": "input_text", "text": prompt})

    api_key = config.model_api_key.get_secret_value() if hasattr(config.model_api_key, "get_secret_value") else (config.model_api_key or "")
    payload = {
        "model": config.muse_spark_model,
        "reasoning": {"effort": "low"},
        "input": [{"role": "user", "content": content}],
        # The style contract has many independent dimensions. Leave enough
        # room for a complete JSON object so the provider is less likely to
        # truncate a valid analysis at the end of the response.
        "max_output_tokens": 2600,
    }

    last_error = "provider did not return a successful response"
    for attempt in range(2):
        try:
            with httpx.Client(timeout=httpx.Timeout(45.0)) as client:
                response = client.post(
                    f"{config.meta_base_url.rstrip('/')}/responses",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
            if response.status_code == 200:
                data = response.json()
                text_parts = [
                    part.get("text", "")
                    for item in data.get("output", [])
                    if item.get("type") == "message"
                    for part in item.get("content", [])
                    if part.get("type") == "output_text" and part.get("text")
                ]
                if not text_parts:
                    raise AnalysisProviderError(f"{task} provider returned no analysis text.")
                try:
                    decoded = _parse_json_object("\n".join(text_parts))
                except (json.JSONDecodeError, TypeError) as exc:
                    detail = (
                        f" (line {exc.lineno}, column {exc.colno})"
                        if isinstance(exc, json.JSONDecodeError)
                        else ""
                    )
                    raise AnalysisProviderError(
                        f"{task} provider returned invalid structured analysis{detail}; no analysis was saved."
                    ) from exc
                if not isinstance(decoded, dict):
                    raise AnalysisProviderError(f"{task} provider returned an invalid analysis object.")
                return decoded

            last_error = f"provider returned HTTP {response.status_code}"
            if response.status_code != 429 and response.status_code < 500:
                break
        except AnalysisProviderError:
            raise
        except httpx.TimeoutException:
            last_error = "provider request timed out"
        except httpx.RequestError as exc:
            last_error = f"provider network request failed ({type(exc).__name__})"
        except Exception as exc:
            last_error = f"provider response could not be processed ({type(exc).__name__})"
        if attempt == 0:
            time.sleep(0.25)

    logger.warning("%s reference analysis failed: %s", task, last_error)
    raise AnalysisProviderError(f"{task} reference analysis failed: {last_error}. No analysis was saved.")


def _extract_dominant_palette(img: Image.Image, num_colors: int = 5) -> List[str]:
    """
    Extracts true dominant color hex codes from an image using median-cut quantization.
    """
    try:
        small = img.copy().convert("RGB").resize((150, 150))
        quantized = small.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        palette = quantized.getpalette()[: num_colors * 3]
        hex_colors = []
        for i in range(0, len(palette), 3):
            r, g, b = palette[i], palette[i + 1], palette[i + 2]
            hex_colors.append(f"#{r:02x}{g:02x}{b:02x}".upper())
        return hex_colors
    except Exception as exc:
        raise ValueError("Palette measurement failed; no fallback palette was substituted.") from exc


def _measure_image_heuristics(image_bytes: bytes) -> Dict[str, Any]:
    """
    Measures objective image statistics using Pillow:
    dimensions, aspect ratio, monochrome status, contrast, brightness, and edge density.
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        stat = ImageStat.Stat(img)
        r_mean, g_mean, b_mean = stat.mean[:3]
        # Check if R, G, B channels are virtually identical (monochrome check)
        is_monochrome = abs(r_mean - g_mean) < 6.0 and abs(g_mean - b_mean) < 6.0

        # Contrast estimated via standard deviation
        avg_std = sum(stat.stddev[:3]) / 3.0

        # Edge density estimation via FIND_EDGES
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_density = edge_stat.mean[0]  # Higher value = heavier/denser lines

        dominant_palette = _extract_dominant_palette(img, 5)

        return {
            "width": img.width,
            "height": img.height,
            "is_monochrome": is_monochrome,
            "avg_std": round(avg_std, 2),
            "brightness": round(sum(stat.mean[:3]) / 3.0, 2),
            "edge_density": round(edge_density, 2),
            "dominant_palette": dominant_palette,
        }
    except Exception as exc:
        raise ValueError("Reference image could not be decoded for objective measurements.") from exc


def _clean_json_output(raw_text: str) -> str:
    """Strips an optional Markdown fence without altering the model output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_object(raw_text: str) -> Dict[str, Any]:
    """Parse a JSON object even when the model adds prose before or after it.

    Scan for the first complete object instead of using a greedy brace regex;
    braces inside quoted strings and multiple brace-delimited examples must
    not make us combine unrelated output into invalid JSON.
    """
    cleaned = _clean_json_output(raw_text)
    decoder = json.JSONDecoder()
    last_error: Optional[json.JSONDecodeError] = None
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(value, dict):
            return value
    if last_error:
        raise last_error
    raise json.JSONDecodeError("No JSON object found", cleaned, 0)


class StyleAnalyzer:
    """
    Analyzes visual style reference images using the Meta Muse Spark multimodal
    vision model to produce structured, reviewable style traits.
    Requires the configured vision provider; objective measurements are supplemental only.
    """

    def __init__(self, registry: AssetRegistry, config: Optional[InkLoopConfig] = None):
        self.registry = registry
        self.config = config or InkLoopConfig.load()

    def _call_multimodal_style_vision(
        self,
        images: List[tuple[bytes, str]],
        user_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ask the configured vision model for observations grounded in uploaded bytes."""
        prompt = """Analyze only the attached reference images as evidence for a reusable RENDERING STYLE. Do not assume a genre, medium, palette, or rendering convention. Separate visible observations from stylistic interpretation, and do not invent facts that are not visible.

Describe how marks and surfaces are rendered: whether outlines are present, their color, weight, consistency and separation from paint; brush or stroke size, direction, opacity and edge character (for example broad opaque gouache-like strokes versus fine hatching); shading transitions and highlights; palette roles including accent colors; and texture scale. Describe background-detail density separately from foreground detail, noting if it varies between images or regions. Describe lighting and shadow softness.

Do not label a reference watercolor merely because its colors are muted, shading is blended, edges are soft, or background shapes are loosely painted. Use watercolor only when there is visible evidence such as translucent pigment layering, pigment blooms/granulation, paint bleeding, or paper absorption/texture. Distinguish opaque gouache-like coverage and smooth digital blending from watercolor. If the medium is uncertain, describe only the visible rendering behavior and use a cautious medium label. Do not call a flat background wash "watercolor" without those material cues.

Keep style separate from depicted content. Do not turn a character, object, medical setting, text, panel border, framing, camera angle, number/order of panels, or composition into a style rule. You may briefly identify such content only as evidence context; never require it in style_prompt_core or rendering rules. Do not request a copied layout. If multiple references disagree, report the variation instead of averaging it away.

Return one JSON object with keys: medium, linework_summary, linework_rules, stroke_behavior_summary, stroke_behavior_rules, edge_quality_summary, edge_quality_rules, shading_summary, shading_rules, palette_summary, palette_rules, lighting_summary, lighting_rules, background_detail_summary, background_detail_rules, texture_summary, texture_rules, shape_language_summary, shape_language_rules, screentones_and_fx, negative_constraints, style_prompt_core. All summary fields and style_prompt_core must describe rendering only. Use empty arrays only when the property is genuinely not observable. Do not assign numeric confidence scores."""
        data = _call_vision_json(self.config, images, prompt, "Style")
        required_strings = (
            "medium", "linework_summary", "stroke_behavior_summary", "edge_quality_summary",
            "shading_summary", "palette_summary", "lighting_summary", "background_detail_summary",
            "texture_summary", "shape_language_summary", "style_prompt_core",
        )
        required_lists = (
            "linework_rules", "stroke_behavior_rules", "edge_quality_rules", "shading_rules",
            "palette_rules", "lighting_rules", "background_detail_rules", "texture_rules",
            "shape_language_rules", "screentones_and_fx", "negative_constraints",
        )
        if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required_strings):
            raise AnalysisProviderError("Style provider response omitted required observed fields.")
        if any(not isinstance(data.get(key), list) or any(not isinstance(item, str) for item in data[key]) for key in required_lists):
            raise AnalysisProviderError("Style provider response contained invalid trait lists.")
        return data

    def analyze_references(
        self,
        project_id: str,
        asset_ids: List[str],
        user_instructions: Optional[str] = None,
    ) -> StyleAnalysisRecord:
        if not asset_ids:
            raise ValueError("At least one reference asset ID is required to analyze style.")
        if len(asset_ids) > 3:
            raise ValueError("Style analysis accepts at most 3 references per request.")

        images: List[tuple[bytes, str]] = []
        measurements: List[Dict[str, Any]] = []
        from app.creative.quick_styles import QUICK_STYLE_TEMPLATES
        trusted_quick_style_preview_ids = {
            item.preview_asset_id
            for item in QUICK_STYLE_TEMPLATES
            if item.preview_asset_id
        }
        for asset_id in asset_ids:
            metadata = self.registry.get_asset(asset_id)
            if not metadata:
                raise ValueError(f"Reference asset '{asset_id}' is not registered.")
            is_trusted_selected_preview = (
                asset_id in trusted_quick_style_preview_ids
                and metadata.project_id == "quick_style_preview_lab"
            )
            is_canonical_anchor = bool(metadata.extra_metadata.get("is_canonical_anchor"))
            if metadata.project_id != project_id and not is_canonical_anchor and not is_trusted_selected_preview:
                raise ValueError(f"Reference asset '{asset_id}' does not belong to this project.")
            if metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"} or metadata.byte_size > 15 * 1024 * 1024:
                raise ValueError(f"Reference asset '{asset_id}' is not a supported image under 15 MB.")
            try:
                resolved = self.registry.resolve_asset(asset_id, verify_integrity=True)
                raw = resolved.absolute_path.read_bytes()
            except Exception as exc:
                raise ValueError(f"Reference asset '{asset_id}' could not be read and integrity-checked: {exc}") from exc
            if not raw:
                raise ValueError(f"Reference asset '{asset_id}' is empty.")
            images.append((raw, resolved.metadata.mime_type or "application/octet-stream"))
            measurements.append(_measure_image_heuristics(raw))

        vision_data = self._call_multimodal_style_vision(images, user_instructions)
        asset_ids_used = list(asset_ids)
        trait_specs = {
            "linework": ("linework_summary", "linework_rules"),
            "stroke_behavior": ("stroke_behavior_summary", "stroke_behavior_rules"),
            "edge_quality": ("edge_quality_summary", "edge_quality_rules"),
            "shading": ("shading_summary", "shading_rules"),
            "palette": ("palette_summary", "palette_rules"),
            "lighting": ("lighting_summary", "lighting_rules"),
            "background_detail": ("background_detail_summary", "background_detail_rules"),
            "texture": ("texture_summary", "texture_rules"),
            "shape_language": ("shape_language_summary", "shape_language_rules"),
        }
        traits = {
            key: StyleDimensionTrait(
                dimension=key,
                summary=vision_data[summary_key],
                rules=vision_data[rules_key],
                source="model_observation" if key in ("linework", "palette", "texture", "shape_language") else "model_inference",
                confidence=None,
                evidence_asset_ids=asset_ids_used,
                uncertainty_notes="Vision-model output is unverified; review against the original reference before approval.",
            )
            for key, (summary_key, rules_key) in trait_specs.items()
        }
        first_palette = measurements[0]["dominant_palette"]
        return StyleAnalysisRecord(
            medium=vision_data["medium"],
            analysis_status="completed",
            analysis_source="live_vision_model",
            model_id=self.config.muse_spark_model,
            traits=traits,
            measured_palette=first_palette,
            screentones_and_fx=vision_data["screentones_and_fx"],
            negative_constraints=vision_data["negative_constraints"],
            analysis_summary=vision_data["style_prompt_core"],
            user_directives=user_instructions.strip() if user_instructions and user_instructions.strip() else None,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

class CharacterAnalyzer:
    """
    Analyzes multi-view reference images using the Meta Muse Spark multimodal
    vision model to extract canonical character identity invariants.
    Requires the configured vision provider; no synthetic profile is created offline.
    """

    def __init__(self, registry: AssetRegistry, config: Optional[InkLoopConfig] = None):
        self.registry = registry
        self.config = config or InkLoopConfig.load()

    def _call_multimodal_character_vision(
        self,
        images: List[tuple[bytes, str]],
        name: str,
        character_id: str,
    ) -> Dict[str, Any]:
        """Extract reviewable character claims from the actual uploaded reference bytes."""
        prompt = f"""Analyze the attached images for the creator-named being {name!r} (stable ID: {character_id}). This may be any kind of entity: human, animal, monster, masked or headless figure, object-like or abstract being, hybrid, or an unusual shape such as a smiling circle. Never assume it has a human body, face, head, eyes, hair, skin, hands, limbs, clothing, or an age. Describe only what is actually visible; explicitly say absent, not visible, or unknown where appropriate. Keep stable identity separate from temporary state and clothing. Return JSON with keys: character_name, entity_kind, morphology, surface_description, appendages_or_parts (array of strings), sensory_features (array of strings), locomotion, visual_features (array of objects with label, description, stability, provenance), face_check_applicable (boolean), identity_invariants (array of strings), allowed_variations (array), forbidden_drift (array), unknown_or_occluded (array), prompt_identity_core. Use model_observation for visible facts and model_inference only for interpretations. Do not assign numeric confidence scores."""
        data = _call_vision_json(self.config, images, prompt, "Character")
        required_strings = ("prompt_identity_core",)
        required_lists = ("identity_invariants", "allowed_variations", "forbidden_drift")
        if any(not isinstance(data.get(key), str) or not data[key].strip() for key in required_strings):
            raise AnalysisProviderError("Character provider response omitted required observations.")
        if any(not isinstance(data.get(key), list) or any(not isinstance(item, str) for item in data[key]) for key in required_lists):
            raise AnalysisProviderError("Character provider response contained invalid trait lists.")
        if not data["identity_invariants"]:
            raise AnalysisProviderError("Character provider returned no identity claims; no profile was created.")
        legacy_features = []
        for key, label in (("hair", "Visible feature"), ("face_and_expression", "Face or front features"), ("outfit", "Clothing or covering")):
            value = data.get(key)
            if isinstance(value, str) and value.strip() and value.strip().lower() not in {"unknown", "not visible", "not applicable"}:
                legacy_features.append({"label": label, "description": value.strip(), "stability": "unknown", "provenance": "model_observation"})
        if not isinstance(data.get("visual_features"), list):
            data["visual_features"] = legacy_features
        return data

    def analyze_character(
        self,
        project_id: str,
        character_id: str,
        name: str,
        references: List[ReferenceBinding],
        known_canon_facts: Optional[List[str]] = None,
    ) -> CharacterIdentityProfile:
        if not references:
            raise ValueError("At least one character reference image is required.")
        if len(references) > 4:
            raise ValueError("Character analysis accepts at most 4 references per request.")
        if not character_id.strip() or not name.strip():
            raise ValueError("A stable character ID and display name are required.")

        images: List[tuple[bytes, str]] = []
        ref_asset_ids: List[str] = []
        views_present = {r.view_role for r in references if r.view_role}
        for reference in references:
            if reference.role != SemanticReferenceRole.CHARACTER_REFERENCE:
                raise ValueError(f"Asset '{reference.asset_id}' is not labeled as a character reference.")
            metadata = self.registry.get_asset(reference.asset_id)
            if not metadata:
                raise ValueError(f"Reference asset '{reference.asset_id}' is not registered.")
            if metadata.project_id != project_id and not metadata.extra_metadata.get("is_canonical_anchor"):
                raise ValueError(f"Reference asset '{reference.asset_id}' does not belong to this project.")
            if metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"} or metadata.byte_size > 15 * 1024 * 1024:
                raise ValueError(f"Reference asset '{reference.asset_id}' is not a supported image under 15 MB.")
            resolved = self.registry.resolve_asset(reference.asset_id, verify_integrity=True)
            raw = resolved.absolute_path.read_bytes()
            if not raw:
                raise ValueError(f"Reference asset '{reference.asset_id}' is empty.")
            images.append((raw, resolved.metadata.mime_type))
            ref_asset_ids.append(reference.asset_id)

        vision_data = self._call_multimodal_character_vision(images, name, character_id)
        uncertain_traits: List[str] = []
        if CharacterViewRole.FULL_BODY not in views_present and CharacterViewRole.FULL_FORM not in views_present:
            uncertain_traits.append("Parts outside the visible reference crop are not established.")
        if CharacterViewRole.SIDE not in views_present:
            uncertain_traits.append("The opposite-side/profile form is not established by a side-view reference.")

        visual_features = [
            IdentityFeature(
                feature_id=f"feature_{index + 1}",
                label=str(item.get("label", "Visible feature")),
                description=str(item.get("description", "")),
                stability=item.get("stability", "unknown") if item.get("stability") in {"stable", "state", "unknown"} else "unknown",
                provenance=item.get("provenance", "model_observation") if item.get("provenance") in {"user_authored", "model_observation", "model_inference", "unknown"} else "unknown",
                evidence_asset_ids=ref_asset_ids,
            )
            for index, item in enumerate(vision_data.get("visual_features", []))
            if isinstance(item, dict) and str(item.get("description", "")).strip()
        ]
        known_facts = [fact.strip() for fact in (known_canon_facts or []) if fact and fact.strip()]
        return CharacterIdentityProfile(
            profile_id=f"char_{character_id.strip().lower()}_v1",
            project_id=project_id,
            character_id=character_id.strip(),
            name=vision_data.get("character_name") if isinstance(vision_data.get("character_name"), str) and vision_data["character_name"].strip() else name.strip(),
            version=1,
            status=ProfileStatus.NEEDS_REVIEW,
            references=references,
            identity_invariants=vision_data["identity_invariants"],
            allowed_variations=vision_data["allowed_variations"],
            entity_kind=str(vision_data.get("entity_kind") or "unspecified being"),
            morphology=str(vision_data.get("morphology") or ""),
            surface_description=str(vision_data.get("surface_description") or ""),
            appendages_or_parts=[item for item in vision_data.get("appendages_or_parts", []) if isinstance(item, str)],
            sensory_features=[item for item in vision_data.get("sensory_features", []) if isinstance(item, str)],
            locomotion=str(vision_data.get("locomotion") or ""),
            face_check_applicable=vision_data.get("face_check_applicable") is True,
            identity_features=visual_features,
            contextual_traits=[part for part in [str(vision_data.get("surface_description") or ""), *[feature.description for feature in visual_features]] if part],
            uncertain_traits=uncertain_traits,
            analysis_status="completed",
            analysis_source="live_vision_model",
            trait_provenance={
                "identity_invariants": "model_observation",
                "allowed_variations": "model_inference",
                "forbidden_drift": "model_inference",
                "prompt_identity_core": "model_inference",
                "contextual_traits": "model_observation",
                "base_outfit": "model_observation",
                "known_canon_facts": "user_authored",
                "uncertain_traits": "unknown_due_to_missing_reference_view",
            },
            forbidden_drift=vision_data["forbidden_drift"],
            prompt_identity_core=vision_data["prompt_identity_core"],
            evidence_links={
                "identity_invariants": ref_asset_ids,
                **{feature.label: ref_asset_ids for feature in visual_features},
            },
            base_outfit=(
                {"name": "Reference clothing/covering (review required)", "description": vision_data["outfit"]}
                if isinstance(vision_data.get("outfit"), str) and vision_data["outfit"].strip()
                else None
            ),
            approved_by_user=False,
            metadata={
                "analysis_model": self.config.muse_spark_model,
                "analysis_reference_asset_ids": ref_asset_ids,
                "unknown_or_occluded": vision_data.get("unknown_or_occluded", []),
                "user_authored_known_facts": known_facts,
                "analysis_review_required": True,
            },
        )


    def generate_sheet_plan(self, profile: CharacterIdentityProfile) -> CharacterSheetPlan:
        """Constructs a reference plan from this being's declared form, not a human template."""
        plan_id = f"sheet_plan_{profile.character_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        form = "; ".join(part for part in [profile.entity_kind, profile.morphology, profile.surface_description, ", ".join(profile.appendages_or_parts), ", ".join(profile.sensory_features)] if part)
        anchors = ", ".join(profile.identity_invariants)
        form_guard = "Preserve the declared form; do not humanize or add absent parts, anatomy, materials, or coverings."

        views = [
            SheetViewSpec(
                view_type="identity_overview",
                prompt=f"Identity reference of {profile.name}. {form_guard} Form: {form}. Stable anchors: {anchors}. Clean neutral background.",
                negative_prompt="complex background, dynamic action, text, dialogue balloons",
                aspect_ratio="1:1",
                width=1024,
                height=1024,
            ),
            SheetViewSpec(
                view_type="form_turnaround",
                prompt=f"{form_guard} Show {profile.name} from a second useful view while preserving the exact declared form, parts, surface, and identity anchors. {form}. {anchors}.",
                negative_prompt="complex background, text, dialogue balloons",
                aspect_ratio="1:1",
                width=1024,
                height=1024,
            ),
            SheetViewSpec(
                view_type="identity_feature_detail",
                prompt=f"{form_guard} Detail study of {profile.name}'s declared distinctive features. Preserve their count, shape, placement, material, and color. {anchors}.",
                negative_prompt="complex background, text",
                aspect_ratio="1:1",
                width=1024,
                height=1024,
            ),
            SheetViewSpec(
                view_type="approved_variation",
                prompt=f"{form_guard} Show creator-approved allowed variations of {profile.name} without changing its stable identity. {profile.prompt_identity_core}.",
                negative_prompt="text, speech balloons",
                aspect_ratio="1:1",
                width=1024,
                height=1024,
            ),
        ]

        return CharacterSheetPlan(
            plan_id=plan_id,
            project_id=profile.project_id,
            character_id=profile.character_id,
            character_name=profile.name,
            views=views,
            estimated_cost_usd=None,
        )


class ObjectAnalyzer:
    """Analyze registered object-reference bytes into a reviewable prop draft."""

    def __init__(self, registry: AssetRegistry, config: Optional[InkLoopConfig] = None):
        self.registry = registry
        self.config = config or InkLoopConfig.load()

    def analyze_object(
        self,
        *,
        project_id: str,
        prop_id: str,
        name: str,
        asset_ids: List[str],
        creator_notes: Optional[str] = None,
    ):
        from app.project.asset_refs import AssetRef
        from app.project.canon import PropDefinition, PropIdentityFeature, PropAnalysisRecord

        clean_name = (name or "").strip()
        clean_id = (prop_id or "").strip().lower()
        if not clean_name or not clean_id:
            raise ValueError("A stable object ID and display name are required.")
        if not asset_ids or len(asset_ids) > 4:
            raise ValueError("Object analysis requires 1 to 4 registered reference images.")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("Object reference asset IDs must be unique.")

        images: List[tuple[bytes, str]] = []
        refs = []
        for asset_id in asset_ids:
            metadata = self.registry.get_asset(asset_id)
            if not metadata:
                raise ValueError(f"Reference asset '{asset_id}' is not registered.")
            if metadata.project_id != project_id:
                raise ValueError(f"Reference asset '{asset_id}' does not belong to this project.")
            if metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"} or metadata.byte_size > 15 * 1024 * 1024:
                raise ValueError(f"Reference asset '{asset_id}' is not a supported image under 15 MB.")
            resolved = self.registry.resolve_asset(asset_id, verify_integrity=True)
            raw = resolved.absolute_path.read_bytes()
            if not raw:
                raise ValueError(f"Reference asset '{asset_id}' is empty.")
            try:
                from app.config import PROJECT_ROOT
                rel_path = str(resolved.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
            except ValueError as exc:
                raise ValueError(f"Reference asset '{asset_id}' is outside project storage.") from exc
            images.append((raw, resolved.metadata.mime_type))
            refs.append(AssetRef(
                asset_id=asset_id,
                path=rel_path,
                asset_type="prop_ref",
                expected_hash=resolved.metadata.content_sha256,
                mime_type=resolved.metadata.mime_type,
                file_size_bytes=resolved.metadata.byte_size,
                provenance={"source": "object_studio_reference", "name": resolved.metadata.original_filename},
            ))

        prompt = f"""Analyze the supplied reference images for the recurring physical object named {clean_name!r} (stable ID: {clean_id}). Describe only what is visible in the attached image bytes. Do not invent hidden construction or material. Separate stable physical identity from scene state such as lit/unlit, held/hanging, clean/damaged, or open/closed. Use explicit unknowns for occluded or ambiguous details. The creator's notes are: {(creator_notes or '').strip()!r}. Return one JSON object with keys: observed_summary (string), inferred_purpose (string; empty if unknown), form_and_proportions (string), materials (array of strings), palette (array of strings), components (array of strings), distinctive_marks (array of strings), stable_invariants (array of strings), allowed_states (array of strings), uncertain_traits (array of strings), trait_provenance (object mapping description/form_and_proportions/materials/palette/components/distinctive_marks/stable_invariants/allowed_states to model_observation, model_inference, or unknown), visual_features (array of objects with label, description, stability [stable/state/unknown], provenance [model_observation/model_inference/unknown]). Never label an inference as observed fact and never turn creator notes into image observations."""
        data = _call_vision_json(self.config, images, prompt, "Object")
        required_strings = ("observed_summary", "form_and_proportions")
        required_lists = ("materials", "palette", "components", "distinctive_marks", "stable_invariants", "allowed_states", "uncertain_traits", "visual_features")
        if any(not isinstance(data.get(key), str) for key in required_strings):
            raise AnalysisProviderError("Object provider response omitted required observed fields.")
        if any(not isinstance(data.get(key), list) for key in required_lists):
            raise AnalysisProviderError("Object provider response omitted required trait lists.")
        if any(any(not isinstance(value, str) for value in data[key]) for key in required_lists[:-1]):
            raise AnalysisProviderError("Object provider response contained invalid trait lists.")
        features = []
        for index, item in enumerate(data["visual_features"], start=1):
            if not isinstance(item, dict) or not str(item.get("description", "")).strip():
                continue
            stability = item.get("stability") if item.get("stability") in {"stable", "state", "unknown"} else "unknown"
            provenance = item.get("provenance") if item.get("provenance") in {"model_observation", "model_inference", "unknown"} else "unknown"
            features.append(PropIdentityFeature(
                feature_id=f"object_feature_{index}",
                label=str(item.get("label") or "Visible object feature"),
                description=str(item["description"]).strip(),
                stability=stability,
                provenance=provenance,
                evidence_asset_ids=list(asset_ids),
            ))
        unknowns = [str(value) for value in data["uncertain_traits"] if isinstance(value, str)]
        if not features:
            raise AnalysisProviderError("Object provider returned no evidence-linked traits; no profile was created.")
        return PropDefinition(
            prop_id=clean_id,
            name=clean_name,
            description=str(data["observed_summary"]).strip(),
            reference_assets=refs,
            form_and_proportions=str(data["form_and_proportions"]).strip(),
            materials=[str(value) for value in data["materials"] if isinstance(value, str)],
            palette=[str(value) for value in data["palette"] if isinstance(value, str)],
            components=[str(value) for value in data["components"] if isinstance(value, str)],
            distinctive_marks=[str(value) for value in data["distinctive_marks"] if isinstance(value, str)],
            required_attributes=[str(value) for value in data["stable_invariants"] if isinstance(value, str)],
            stable_invariants=[str(value) for value in data["stable_invariants"] if isinstance(value, str)],
            trait_provenance={
                key: (data.get("trait_provenance", {}).get(key) if isinstance(data.get("trait_provenance"), dict) else None)
                if (data.get("trait_provenance", {}).get(key) if isinstance(data.get("trait_provenance"), dict) else None) in {"user_authored", "model_observation", "model_inference", "unknown"}
                else "unknown"
                for key in ("description", "form_and_proportions", "materials", "palette", "components", "distinctive_marks", "stable_invariants", "allowed_states")
            },
            allowed_states=[str(value) for value in data["allowed_states"] if isinstance(value, str)],
            permitted_variations=[str(value) for value in data["allowed_states"] if isinstance(value, str)],
            uncertain_traits=unknowns,
            identity_features=features,
            analysis=PropAnalysisRecord(
                analysis_status="completed",
                analysis_source="live_vision_model",
                model_id=self.config.muse_spark_model,
                observed_summary=str(data["observed_summary"]).strip(),
                inferred_purpose=str(data.get("inferred_purpose") or "").strip(),
                unknown_or_occluded=unknowns,
                creator_authored_facts=[line.strip() for line in (creator_notes or "").splitlines() if line.strip()],
                analyzed_at=datetime.now(timezone.utc).isoformat(),
            ),
            creator_notes=(creator_notes or "").strip(),
            approval_status="draft",
        )
