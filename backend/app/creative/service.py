"""
InkLoop AI Creative Director & Universe Builder Service.
Orchestrates the 16-stage creative workflow, turning natural language prompts
into comprehensive, versioned, coherent comic production bibles and machine-readable contracts.
"""
import os
import re
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.config import PROJECT_ROOT, InkLoopConfig
from app.creative.schemas import (
    CreativeBrief,
    CreativeMode,
    FactCategory,
    FactItem,
    CreativeStoryBible,
    CharacterIdentityProfile,
    OutfitVariant,
    CharacterArcCheckpoint,
    RelationshipGraph,
    RelationshipEdge,
    WorldBible,
    LocationSpec,
    PropArtifactSpec,
    MagicOrTechAbilityRule,
    NarrativeStructure,
    ChapterOutline,
    SceneCandidate,
    SetupPayoffItem,
    VisualStyleProfile,
    CharacterSheetPlan,
    SheetViewSpec,
    CreativeContractsPackage,
    ProjectCanonContract,
    CharacterIdentityContract,
    VisualStyleContract,
    WorldRuleContract,
    GenerationConstraintContract,
    CreativePackage,
    ValidationResult,
    FindingSeverity,
)
from app.creative.validator import CreativeCoherenceValidator
from app.creative.synthesizer import build_dynamic_universe, synthesize_with_live_ai
from app.project.bible import StoryBible
from app.project.canon import CharacterDefinition, StyleDefinition, CanonMutationProposal
from app.schemas import AttributeCheck, Tolerances


class CreativeProviderUnavailableError(RuntimeError):
    """Raised when a live creative synthesis was requested without provider credentials."""


class CreativeProviderError(RuntimeError):
    """Raised when the configured provider fails to synthesize a creative package."""

class CreativeDirectorService:
    """Core service for AI Creative Director / Universe Builder."""

    _instance: Optional["CreativeDirectorService"] = None

    def __init__(self, packages_dir: Optional[Path] = None):
        self.packages_dir = packages_dir or (PROJECT_ROOT / "runs" / "creative_packages")
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.validator = CreativeCoherenceValidator()

    @classmethod
    def get_instance(cls) -> "CreativeDirectorService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_package_path(self, project_id: str) -> Path:
        return self.packages_dir / f"{project_id}.json"

    def get_package(self, project_id: str) -> Optional[CreativePackage]:
        """Loads persisted CreativePackage from storage."""
        path = self._get_package_path(project_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CreativePackage(**data)
        except Exception:
            return None

    def save_package(self, package: CreativePackage) -> None:
        """Atomically saves CreativePackage to disk."""
        if not package.package_hash:
            seed = f"{package.project_id}:{package.version}:{package.story_bible.title}"
            package.package_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        path = self._get_package_path(package.project_id)
        package.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        tmp = path.with_suffix(".tmp")
        tmp.write_text(package.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)

    def develop_universe(
        self,
        project_id: str,
        user_prompt: str,
        mode: CreativeMode = CreativeMode.FULL_PRODUCTION_BIBLE,
        visual_references: Optional[List[Dict[str, Any]]] = None,
        offline_mode: Optional[bool] = None,
    ) -> CreativePackage:
        """
        Executes the 16-stage creative pipeline on a natural-language brief.
        Loads existing Story Bible, detects canon conflicts, synthesizes deliverables,
        and generates machine-readable contracts.
        """
        is_offline = (
            offline_mode
            if offline_mode is not None
            else os.getenv("INKLOOP_OFFLINE_MODE") == "1"
        )
        if not is_offline and not InkLoopConfig.load().has_credentials:
            raise CreativeProviderUnavailableError(
                "Creative synthesis requires configured provider credentials. Explicit offline mode is available for a labeled procedural draft."
            )

        completed_stages: List[str] = []

        # Stage 1: UNDERSTAND_BRIEF
        completed_stages.append("UNDERSTAND_BRIEF")

        # Stage 2: LOAD_EXISTING_CANON
        completed_stages.append("LOAD_EXISTING_CANON")
        existing_bible = self._load_existing_bible(project_id)

        # Dynamic, prompt-driven synthesis. Live provider failures remain visible;
        # procedural drafts are only used when the caller explicitly selects offline mode.
        synthesis_source = "dynamic_procedural"
        if not is_offline:
            try:
                (
                    brief,
                    story_bible,
                    characters,
                    world_bible,
                    relationships,
                    narrative_structure,
                    style_profile,
                ) = synthesize_with_live_ai(
                    project_id=project_id,
                    user_prompt=user_prompt,
                    mode=mode,
                    visual_references=visual_references,
                    existing_bible=existing_bible,
                )
                synthesis_source = "live_ai"
            except Exception as exc:
                logger.exception("Live model creative synthesis failed")
                raise CreativeProviderError(f"Creative provider synthesis failed: {exc}") from exc
        else:
            (
                brief,
                story_bible,
                characters,
                world_bible,
                relationships,
                narrative_structure,
                style_profile,
            ) = build_dynamic_universe(
                project_id=project_id,
                user_prompt=user_prompt,
                mode=mode,
                visual_references=visual_references,
                existing_bible=existing_bible,
            )

        # Stage 3: FIND_CONFLICTS_AND_GAPS
        completed_stages.append("FIND_CONFLICTS_AND_GAPS")
        conflicts = self._detect_initial_conflicts(brief, existing_bible)

        # Stage 4: PROPOSE_CREATIVE_DIRECTION
        completed_stages.append("PROPOSE_CREATIVE_DIRECTION")

        # Stage 5: BUILD_STORY_BIBLE
        completed_stages.append("BUILD_STORY_BIBLE")

        # Stage 6: BUILD_CHARACTER_BIBLE
        completed_stages.append("BUILD_CHARACTER_BIBLE")

        # Stage 7: BUILD_WORLD_AND_RELATIONSHIPS
        completed_stages.append("BUILD_WORLD_AND_RELATIONSHIPS")

        # Stage 8: BUILD_NARRATIVE_STRUCTURE
        completed_stages.append("BUILD_NARRATIVE_STRUCTURE")

        # Stage 9: BUILD_VISUAL_STYLE_PROFILE
        completed_stages.append("BUILD_VISUAL_STYLE_PROFILE")

        # Stage 10: BUILD_MACHINE_CONTRACTS
        completed_stages.append("BUILD_MACHINE_CONTRACTS")
        contracts = self._build_contracts(
            project_id=project_id,
            story_bible=story_bible,
            characters=characters,
            style_profile=style_profile,
            world_bible=world_bible,
        )

        # Stage 11: VALIDATE_COHERENCE
        completed_stages.append("VALIDATE_COHERENCE")
        hash_seed = f"{project_id}:{brief.brief_id}:{story_bible.title}:{len(characters)}"
        package_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:16]

        package_candidate = CreativePackage(
            project_id=project_id,
            version=1,
            package_hash=package_hash,
            brief=brief,
            story_bible=story_bible,
            characters=characters,
            relationship_graph=relationships,
            world_bible=world_bible,
            narrative_structure=narrative_structure,
            style_profile=style_profile,
            character_sheet_plans=self._build_sheet_plans(project_id, characters),
            contracts=contracts,
            validation=ValidationResult(project_id=project_id, is_coherent=True, findings=[]),
            completed_stages=completed_stages,
            current_stage="VALIDATE_COHERENCE",
            synthesis_source=synthesis_source,
        )

        validation_res = self.validator.validate_package(package_candidate, existing_bible)
        package_candidate.validation = validation_res

        # Stage 12: PRESENT_REVIEW_PACKAGE
        completed_stages.append("PRESENT_REVIEW_PACKAGE")

        # Stage 13: WAIT_FOR_APPROVAL_WHERE_REQUIRED
        has_canon_conflicts = any(f.category.value == "CANON_CONFLICT" for f in validation_res.findings)
        package_candidate.has_pending_approval = has_canon_conflicts
        if has_canon_conflicts:
            package_candidate.pending_proposal_diff = {
                "conflicts": [f.model_dump() for f in validation_res.findings if f.category.value == "CANON_CONFLICT"],
                "requires_human_approval": True,
            }
        completed_stages.append("WAIT_FOR_APPROVAL_WHERE_REQUIRED")

        # Stage 14: SAVE_APPROVED_VERSIONS (Persist draft/approved package)
        completed_stages.append("SAVE_APPROVED_VERSIONS")
        self.save_package(package_candidate)

        # Stage 15: OPTIONALLY_QUEUE_REFERENCE_SHEETS
        completed_stages.append("OPTIONALLY_QUEUE_REFERENCE_SHEETS")

        # Stage 16: COMPLETE_WITH_RECEIPT
        completed_stages.append("COMPLETE_WITH_RECEIPT")
        package_candidate.completed_stages = completed_stages
        package_candidate.current_stage = "COMPLETE_WITH_RECEIPT"

        self.save_package(package_candidate)
        return package_candidate

    def add_character_to_universe(
        self,
        project_id: str,
        character: CharacterIdentityProfile,
        commit_to_canon: bool = True,
    ) -> CreativePackage:
        """
        Adds or updates an individual character in the Creative Package and optionally commits
        it immediately to the authoritative Story Bible canon.
        """
        pkg = self.get_package(project_id)
        if not pkg:
            existing_bible = self._load_existing_bible(project_id)
            title = existing_bible.title if existing_bible else project_id
            pkg = self.develop_universe(
                project_id=project_id,
                user_prompt=f"Universe for {title}",
                mode=CreativeMode.QUICK_CONCEPT,
            )

        pkg.characters[character.character_id] = character
        self.save_package(pkg)

        if commit_to_canon:
            self.approve_canon_mutation(project_id, [character.character_id], commit_style=False)
            pkg = self.get_package(project_id) or pkg

        return pkg

    def approve_canon_mutation(
        self,
        project_id: str,
        character_ids_to_commit: Optional[List[str]] = None,
        commit_style: bool = True,
    ) -> StoryBible:
        """
        Commits approved creative package proposals into the authoritative StoryBible,
        creating an immutable new CanonSnapshot.
        """
        pkg = self.get_package(project_id)
        if not pkg:
            raise ValueError(f"No Creative Package found for '{project_id}'.")

        bible = self._load_existing_bible(project_id)
        if not bible:
            from app.project.bible import init_default_bible
            bible = init_default_bible(project_id)
        bible.project_id = project_id

        # 1. Update Characters
        target_ids = character_ids_to_commit or list(pkg.characters.keys())
        for cid in target_ids:
            if cid in pkg.characters:
                cp = pkg.characters[cid]
                # Map Creative Identity to StoryBible CharacterDefinition
                attrs = [
                    AttributeCheck(
                        id=f"{cid}_attr_{idx+1}",
                        text=inv,
                        required=True,
                    )
                    for idx, inv in enumerate(cp.visual_invariants)
                ]
                existing_char = bible.characters.get(cid)
                existing_ver = existing_char.canon_version if existing_char else 0
                existing_refs = list(getattr(existing_char, "reference_assets", [])) if existing_char else []
                bible.characters[cid] = CharacterDefinition(
                    character_id=cid,
                    name=cp.name,
                    entity_kind=cp.entity_kind,
                    morphology=cp.morphology,
                    surface_description=cp.surface_description,
                    description=" ".join(part for part in [cp.entity_kind, cp.morphology, cp.surface_description, cp.narrative_function, cp.backstory[:300]] if part),
                    canon_version=existing_ver + 1,
                    attributes=attrs,
                    tolerances=Tolerances(min_face_px_for_check=80, face_check_applicable=cp.face_check_applicable),
                    clothing_attributes=cp.base_outfit.garments if cp.base_outfit else [],
                    visual_invariants=cp.visual_invariants,
                    restrictions=cp.forbidden_visual_drift or [],
                    reference_assets=existing_refs,
                    approval_status="approved",
                )
                cp.approval_status = "approved"

        # 2. Update Style if requested
        if commit_style:
            sp = pkg.style_profile
            bible.style = StyleDefinition(
                style_id=sp.style_id,
                version=bible.style.version + 1,
                name=sp.name,
                medium=sp.medium,
                rendering_approach=sp.shape_language,
                line_art_rules=sp.line_art_rules,
                tonal_rules=sp.tonal_value_rules,
                palette_or_screentone={"accent_rules": sp.palette_and_accent_rules},
                lighting_constraints=sp.lighting_rules,
                negative_constraints=sp.negative_constraints,
                background_detail_rules=sp.background_detail_density,
            )
            sp.approval_status = "approved"

        # 3. Update Story Text / Title
        if pkg.brief.title:
            bible.title = pkg.brief.title
        if pkg.story_bible.synopsis_expanded:
            bible.user_story_text = pkg.story_bible.synopsis_expanded

        # 4. Save and take Canon snapshot
        bible.bible_version += 1
        snapshot = bible.get_canon_snapshot()
        bible.canon_hash = snapshot.canon_hash

        # Save bible to disk
        from app.project.bible import save_bible
        save_bible(bible, target_path=project_id)

        # Clear pending approval in package
        pkg.has_pending_approval = False
        pkg.pending_proposal_diff = None
        self.save_package(pkg)

        return bible

    # =========================================================================
    # Internal Stage Implementations & Generators
    # =========================================================================

    def _parse_brief(
        self,
        project_id: str,
        user_prompt: str,
        mode: CreativeMode,
        visual_references: Optional[List[Dict[str, Any]]] = None,
    ) -> CreativeBrief:
        existing_bible = self._load_existing_bible(project_id)
        return build_dynamic_universe(
            project_id=project_id,
            user_prompt=user_prompt,
            mode=mode,
            visual_references=visual_references,
            existing_bible=existing_bible,
        )[0]

    def _load_existing_bible(self, project_id: str) -> Optional[StoryBible]:
        try:
            from app.project.bible import load_bible
            return load_bible(project_id)
        except Exception:
            try:
                from app.project.bible import create_canonical_nour_bible
                return create_canonical_nour_bible(Path.cwd() / "runs" / project_id, project_id=project_id)
            except Exception:
                return None

    def _detect_initial_conflicts(
        self,
        brief: CreativeBrief,
        existing_bible: Optional[StoryBible]
    ) -> List[str]:
        conflicts = []
        if not existing_bible:
            return conflicts

        prompt_lower = brief.user_prompt.lower()
        for cid, char in existing_bible.characters.items():
            if cid in prompt_lower and "remove" in prompt_lower:
                for inv in char.visual_invariants:
                    if inv.lower() in prompt_lower:
                        conflicts.append(
                            f"Brief instructs removal of approved invariant '{inv}' on character '{char.name}'."
                        )
        return conflicts

    def _build_story_bible(
        self,
        brief: CreativeBrief,
        existing_bible: Optional[StoryBible] = None,
    ) -> CreativeStoryBible:
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[1]

    def _build_character_bible(
        self,
        brief: CreativeBrief,
        existing_bible: Optional[StoryBible] = None,
    ) -> Dict[str, CharacterIdentityProfile]:
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[2]

    def _build_world_bible(
        self,
        brief: CreativeBrief,
        existing_bible: Optional[StoryBible] = None,
    ) -> WorldBible:
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[3]

    def _build_relationship_graph(
        self,
        brief: CreativeBrief,
        characters: Dict[str, CharacterIdentityProfile],
    ) -> RelationshipGraph:
        existing_bible = self._load_existing_bible(brief.project_id)
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[4]

    def _build_narrative_structure(
        self,
        brief: CreativeBrief,
        characters: Dict[str, CharacterIdentityProfile],
        world: WorldBible,
    ) -> NarrativeStructure:
        existing_bible = self._load_existing_bible(brief.project_id)
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[5]

    def _build_style_profile(
        self,
        brief: CreativeBrief,
        existing_bible: Optional[StoryBible] = None,
    ) -> VisualStyleProfile:
        return build_dynamic_universe(
            project_id=brief.project_id,
            user_prompt=brief.user_prompt,
            mode=brief.mode,
            visual_references=None,
            existing_bible=existing_bible,
        )[6]

    def _build_sheet_plans(
        self,
        project_id: str,
        characters: Dict[str, CharacterIdentityProfile]
    ) -> Dict[str, CharacterSheetPlan]:
        plans: Dict[str, CharacterSheetPlan] = {}
        for cid, char in characters.items():
            form = "; ".join(part for part in [char.entity_kind, char.morphology, char.surface_description] if part)
            anchors = ", ".join(char.visual_invariants)
            form_guard = "Preserve the declared form; do not humanize or add absent parts, anatomy, materials, or coverings."
            views = [
                SheetViewSpec(
                    view_type="identity_overview",
                    prompt=f"Identity reference view of {char.name}. {form_guard} Form: {form}. Stable identity anchors: {anchors}. Clean neutral background.",
                    negative_prompt="blurry, missing or altered declared identity anchors",
                    width=1024,
                    height=1024,
                ),
                SheetViewSpec(
                    view_type="form_turnaround",
                    prompt=f"{form_guard} Show {char.name} from a different angle while preserving its exact morphology, visible parts, surface, and identity anchors. {form}. {anchors}.",
                    negative_prompt="blurry, altered declared identity anchors",
                    width=1024,
                    height=1024,
                ),
                SheetViewSpec(
                    view_type="identity_feature_detail",
                    prompt=f"{form_guard} Close reference study of {char.name}'s declared distinctive identity features. Form: {form}. Preserve feature count, shape, placement, material, and color. {anchors}.",
                    negative_prompt="blurry, text, altered declared identity anchors",
                    width=1024,
                    height=1024,
                )
            ]
            plans[cid] = CharacterSheetPlan(
                plan_id=f"sheet_{cid}_{int(time.time())}",
                project_id=project_id,
                character_id=cid,
                character_name=char.name,
                views=views,
                estimated_cost_usd=None,
            )
        return plans

    def _build_contracts(
        self,
        project_id: str,
        story_bible: CreativeStoryBible,
        characters: Dict[str, CharacterIdentityProfile],
        style_profile: VisualStyleProfile,
        world_bible: WorldBible,
    ) -> CreativeContractsPackage:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Canon Contract
        canon_contract = ProjectCanonContract(
            contract_id=f"canon_contract_{project_id}",
            project_id=project_id,
            version=1,
            canon_hash=hashlib.sha256(f"{project_id}:{story_bible.logline}".encode()).hexdigest(),
            status="draft",
            approved_facts=story_bible.approved_facts,
            proposed_facts=story_bible.proposed_facts,
            content_boundaries=story_bible.story_boundaries,
            provenance={"source": "AI Creative Director Pipeline v1.0"},
            updated_at=now,
        )

        # Character Contracts
        char_contracts: Dict[str, CharacterIdentityContract] = {}
        for cid, char in characters.items():
            char_contracts[cid] = CharacterIdentityContract(
                contract_id=f"char_contract_{cid}",
                character_id=cid,
                version=1,
                status="draft",
                mandatory_visual_invariants=char.visual_invariants,
                allowed_variations=char.allowed_variations,
                forbidden_drift=char.forbidden_visual_drift,
                reference_asset_roles={a: "canonical_reference" for a in char.reference_asset_ids},
                verifier_tolerances={"min_face_px_for_check": 80, "face_check_applicable": char.face_check_applicable},
                updated_at=now,
            )

        # Style Contract
        style_contract = VisualStyleContract(
            contract_id=f"style_contract_{style_profile.style_id}",
            style_id=style_profile.style_id,
            version=1,
            status="draft",
            style_dimensions={
                "medium": style_profile.medium,
                "shape_language": style_profile.shape_language,
                "facial_drawing_conventions": style_profile.facial_drawing_conventions,
                "line_art_rules": style_profile.line_art_rules,
                "palette_rules": style_profile.palette_and_accent_rules,
            },
            negative_constraints=style_profile.negative_constraints,
            reference_asset_roles={},
            updated_at=now,
        )

        # World Contract
        world_contract = WorldRuleContract(
            contract_id=f"world_contract_{project_id}",
            project_id=project_id,
            version=1,
            supernatural_limits={
                r.name: {"cost": r.cost_or_strain, "limit": r.absolute_limit}
                for r in world_bible.supernatural_or_tech_rules
            },
            continuity_consequences=world_bible.continuity_timeline_rules,
            updated_at=now,
        )

        # Generation Constraint Contract
        generation_constraints = GenerationConstraintContract(
            contract_id=f"gen_constraint_{project_id}",
            project_id=project_id,
            target_character_ids=list(characters.keys()),
            required_tokens=style_profile.palette_and_accent_rules + ["manga ink", "clean linework"],
            negative_tokens=style_profile.negative_constraints,
            reference_asset_ids=[],
            quality_gates=["L0_Structural_Sanity", "L1_Subject_Detection", "L2_Invariant_Check"],
            updated_at=now,
        )

        return CreativeContractsPackage(
            project_id=project_id,
            canon_contract=canon_contract,
            character_contracts=char_contracts,
            style_contract=style_contract,
            world_contract=world_contract,
            generation_constraints=generation_constraints,
            created_at=now,
        )
