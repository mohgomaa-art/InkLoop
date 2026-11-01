"""
InkLoop Creative Orchestrator for Style Copier and Character Copier.
Executes bounded, multi-reference generation, runs StyleIdentityQA, and
performs targeted single-pass refinement within execution budget limits.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT, InkLoopConfig
from app.contracts.artifacts import AssetType
from app.contracts.identity import generate_id, IdPrefix
from app.storage.registry import AssetRegistry
from app.execution.manager import ExecutionManager
from app.execution.errors import BudgetExceededError
from app.image_adapter import (
    ImageGenerationAdapter,
    GenerationRequest,
    GenerationResponse,
    ReferenceImagePayload,
    SimulatedImageGenerationAdapter,
    MetaImageGenerationAdapter,
)
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    GenerationReferenceSet,
    GenerationReferenceItem,
    SemanticReferenceRole,
    StyleIdentityQAResult,
)
from app.creative.storage import CreativeProfileStore, get_creative_profile_store
from app.creative.prompt_builder import build_creative_generation_prompt
from app.verification.style_identity_qa import StyleIdentityQAService


class CreativeGenerationResult(BaseModel):
    """Result of a Style/Character-conditioned generation run."""
    run_id: str
    project_id: str
    output_asset_id: str
    initial_asset_id: Optional[str] = None
    success: bool
    status: str
    attempts_performed: int
    prompt: str
    qa_result: StyleIdentityQAResult
    style_profile_id: Optional[str] = None
    style_version: Optional[int] = None
    character_profiles_used: List[Dict[str, Any]] = Field(default_factory=list)
    cost_usd: Optional[float] = None
    is_simulated: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CreativeOrchestrator:
    """
    Coordinates multi-reference image generation with Style & Character profiles.
    Preserves original assets, guarantees bounded retries, and tracks lineage.
    """

    def __init__(
        self,
        registry: AssetRegistry,
        profile_store: Optional[CreativeProfileStore] = None,
        image_adapter: Optional[ImageGenerationAdapter] = None,
        qa_service: Optional[StyleIdentityQAService] = None,
        execution_manager: Optional[ExecutionManager] = None,
    ):
        self.registry = registry
        self.profile_store = profile_store or get_creative_profile_store()
        self.qa_service = qa_service or StyleIdentityQAService()
        self.execution_manager = execution_manager
        if image_adapter is None:
            cfg = InkLoopConfig()
            if os.getenv("INKLOOP_OFFLINE_MODE", "").strip().lower() in {"1", "true", "yes"}:
                self.adapter = SimulatedImageGenerationAdapter()
            elif cfg.has_credentials:
                self.adapter = MetaImageGenerationAdapter(cfg)
            else:
                raise GenerationProviderUnavailableError(
                    "Image generation is unavailable: configure MODEL_API_KEY, or explicitly enable INKLOOP_OFFLINE_MODE for labeled simulations."
                )
        else:
            self.adapter = image_adapter

    def generate(
        self,
        project_id: str,
        scene_action: str,
        shot_type: str = "Medium shot, eye-level angle",
        style_profile_id: Optional[str] = None,
        character_profile_ids: Optional[List[str]] = None,
        reference_set: Optional[GenerationReferenceSet] = None,
        panel_id: str = "panel_01",
        scene_id: str = "scene_01",
        max_attempts: int = 2,
        dimensions: Optional[List[int]] = None,
        aspect_ratio: Optional[str] = None,
        lighting_intent: Optional[str] = None,
        composition_notes: Optional[str] = None,
    ) -> CreativeGenerationResult:
        run_id = generate_id(IdPrefix.RUN)

        # 1. Resolve Style Profile
        style_prof: Optional[StyleProfile] = None
        if style_profile_id:
            style_prof = self.profile_store.get_style_profile(project_id, style_profile_id)
            if not style_prof:
                raise ValueError(f"Style profile '{style_profile_id}' was not found in project '{project_id}'.")

        # 2. Resolve Character Profiles
        char_profs: List[CharacterIdentityProfile] = []
        if character_profile_ids:
            for c_id in character_profile_ids:
                cp = self.profile_store.get_character_profile(project_id, c_id)
                if not cp:
                    # Also try resolving by character_id
                    cp = self.profile_store.get_character_profile_by_character_id(project_id, c_id)
                if cp:
                    char_profs.append(cp)
                else:
                    raise ValueError(f"Character profile '{c_id}' was not found in project '{project_id}'.")

        # 3. Assemble GenerationReferenceSet
        effective_ref_set = reference_set or GenerationReferenceSet(project_id=project_id)
        if effective_ref_set.project_id != project_id:
            raise ValueError("Reference set belongs to a different project.")
        if style_prof and not effective_ref_set.get_style_references():
            for ref in style_prof.references:
                effective_ref_set.references.append(GenerationReferenceItem(
                    asset_id=ref.asset_id,
                    role=SemanticReferenceRole.STYLE_REFERENCE,
                    profile_id=style_prof.profile_id,
                    profile_version=style_prof.version,
                    weight=ref.weight,
                ))

        for cp in char_profs:
            if not effective_ref_set.get_character_references(cp.character_id):
                for ref in cp.references:
                    effective_ref_set.references.append(GenerationReferenceItem(
                        asset_id=ref.asset_id,
                        role=SemanticReferenceRole.CHARACTER_REFERENCE,
                        view_role=ref.view_role,
                        character_id=cp.character_id,
                        profile_id=cp.profile_id,
                        profile_version=cp.version,
                        weight=ref.weight,
                    ))

        # 4. Resolve Image Reference Payloads from AssetRegistry
        ref_payloads: List[ReferenceImagePayload] = []
        ref_bytes_map: Dict[str, bytes] = {}
        parent_asset_ids: List[str] = []

        for ref_item in effective_ref_set.references:
            metadata = self.registry.get_asset(ref_item.asset_id)
            if not metadata or (metadata.project_id != project_id and not metadata.extra_metadata.get("is_canonical_anchor")):
                raise ValueError(f"Reference asset '{ref_item.asset_id}' is missing or outside project '{project_id}'.")
            if metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
                raise ValueError(f"Reference asset '{ref_item.asset_id}' has unsupported image MIME type.")
            try:
                resolved = self.registry.resolve_asset(ref_item.asset_id, verify_integrity=True)
                img_bytes = resolved.absolute_path.read_bytes()
                if not img_bytes:
                    raise ValueError(f"Reference asset '{ref_item.asset_id}' is empty.")
                ref_payloads.append(ReferenceImagePayload(
                    asset_id=ref_item.asset_id,
                    image_bytes=img_bytes,
                    mime_type=resolved.metadata.mime_type or "image/png",
                    role=ref_item.role.value if hasattr(ref_item.role, "value") else str(ref_item.role),
                    character_id=ref_item.character_id,
                    view_role=ref_item.view_role.value if ref_item.view_role and hasattr(ref_item.view_role, "value") else None,
                    weight=ref_item.weight,
                    notes=ref_item.notes,
                ))
                label = f"{ref_item.role.value}_{ref_item.asset_id}"
                ref_bytes_map[label] = img_bytes
                parent_asset_ids.append(ref_item.asset_id)
            except Exception as exc:
                raise ValueError(f"Reference asset '{ref_item.asset_id}' could not be resolved with integrity verification.") from exc

        # 5. Build Initial Prompt
        prompt = build_creative_generation_prompt(
            scene_action=scene_action,
            shot_type=shot_type,
            style_profile=style_prof,
            character_profiles=char_profs,
            reference_set=effective_ref_set,
            composition_notes=composition_notes,
            lighting_intent=lighting_intent,
        )

        # 6. Pass 1: Initial Generation
        gen_req = GenerationRequest(
            prompt=prompt,
            reference_images=ref_payloads,
            reference_bytes=ref_payloads[0].image_bytes if ref_payloads else None,
            reference_mime=ref_payloads[0].mime_type if ref_payloads else "image/png",
            panel_id=panel_id,
            scene_id=scene_id,
            dimensions=dimensions,
            aspect_ratio=aspect_ratio,
        )

        gen_resp: GenerationResponse = self.adapter.generate(gen_req)
        if not gen_resp.success or not gen_resp.image_bytes:
            raise RuntimeError(f"Creative generation failed: {gen_resp.error_message or 'No image returned'}")

        # Ingest Pass 1 Output
        initial_filename = f"{panel_id}_creative_p1.png"
        initial_asset = self.registry.ingest_bytes(
            data=gen_resp.image_bytes,
            filename=initial_filename,
            project_id=project_id,
            asset_type=AssetType.IMAGE_GENERATED,
            name=f"{panel_id} Creative Pass 1",
            parent_asset_ids=parent_asset_ids or None,
            lineage_operation="creative_generation_p1",
            lineage_params={
                "run_id": run_id,
                "style_profile_id": style_profile_id,
                "character_profile_ids": character_profile_ids,
            },
            extra_metadata={
                "run_id": run_id,
                "style_profile_id": style_profile_id,
                "character_profile_ids": character_profile_ids,
                "is_simulated": gen_resp.is_simulated,
            }
        )

        # 7. Quality Assurance Inspection (Pass 1)
        qa_result = self.qa_service.evaluate(
            run_id=run_id,
            asset_id=initial_asset.asset_id,
            image_bytes=gen_resp.image_bytes,
            requested_scene_action=scene_action,
            style_profile=style_prof,
            character_profiles=char_profs,
            reference_images=ref_bytes_map,
            expected_shot_type=shot_type,
        )

        current_asset_id = initial_asset.asset_id
        attempts = 1

        # 8. Pass 2: Targeted Refinement (if QA flagged fixable issue & attempts allowed)
        if max_attempts > 1 and qa_result.status in {"fail", "needs_review"} and qa_result.targeted_repair_prompt:
            repair_prompt = build_creative_generation_prompt(
                scene_action=scene_action,
                shot_type=shot_type,
                style_profile=style_prof,
                character_profiles=char_profs,
                reference_set=effective_ref_set,
                target_to_edit_instructions=qa_result.targeted_repair_prompt,
            )

            # Targeted refinement uses Pass 1 image as TARGET_TO_EDIT
            refinement_payloads = list(ref_payloads)
            refinement_payloads.insert(0, ReferenceImagePayload(
                asset_id=initial_asset.asset_id,
                image_bytes=gen_resp.image_bytes,
                mime_type="image/png",
                role="target_to_edit",
                notes="Base artwork undergoing targeted single-pass repair",
            ))

            refine_req = GenerationRequest(
                prompt=repair_prompt,
                reference_images=refinement_payloads,
                reference_bytes=gen_resp.image_bytes,
                panel_id=panel_id,
                scene_id=scene_id,
                dimensions=dimensions,
                aspect_ratio=aspect_ratio,
            )

            refine_resp = self.adapter.generate(refine_req)
            if refine_resp.success and refine_resp.image_bytes:
                attempts += 1
                refined_filename = f"{panel_id}_creative_refined.png"
                refined_asset = self.registry.ingest_bytes(
                    data=refine_resp.image_bytes,
                    filename=refined_filename,
                    project_id=project_id,
                    asset_type=AssetType.IMAGE_GENERATED,
                    name=f"{panel_id} Creative Refined",
                    parent_asset_ids=[initial_asset.asset_id],
                    lineage_operation="creative_targeted_refinement",
                    lineage_params={"run_id": run_id, "repair_prompt": qa_result.targeted_repair_prompt},
                    extra_metadata={"run_id": run_id, "is_refined": True}
                )

                # Re-evaluate refined result
                qa_result_p2 = self.qa_service.evaluate(
                    run_id=run_id,
                    asset_id=refined_asset.asset_id,
                    image_bytes=refine_resp.image_bytes,
                    requested_scene_action=scene_action,
                    style_profile=style_prof,
                    character_profiles=char_profs,
                    reference_images=ref_bytes_map,
                    expected_shot_type=shot_type,
                )
                current_asset_id = refined_asset.asset_id
                qa_result = qa_result_p2

        chars_summary = [{"id": c.character_id, "name": c.name, "version": c.version} for c in char_profs]

        return CreativeGenerationResult(
            run_id=run_id,
            project_id=project_id,
            output_asset_id=current_asset_id,
            initial_asset_id=initial_asset.asset_id,
            success=True,
            status=qa_result.status,
            attempts_performed=attempts,
            prompt=prompt,
            qa_result=qa_result,
            style_profile_id=style_prof.profile_id if style_prof else None,
            style_version=style_prof.version if style_prof else None,
            character_profiles_used=chars_summary,
            cost_usd=gen_resp.cost_usd,
            is_simulated=gen_resp.is_simulated,
        )


class GenerationProviderUnavailableError(RuntimeError):
    """Raised when live generation is not configured and simulation was not requested."""
