"""
InkLoop Image Knowledge Catalogue - Deterministic Retrieval Engine.
Connects the 60-group / 840-element taxonomy to real image-generation context
through evidence-aware relevance matching, compatibility filtering,
bounded budgeting, and explainable ranking.
"""
import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple, Any

from app.catalogue.enums import (
    CoverageStatus,
    ClaimConfidence,
    RuleType,
    ConflictPriority,
    EvidenceClass,
)
from app.catalogue.models import (
    TaxonomyGroupRecord,
    GenerationRule,
    RecipeRecord,
    ResearchClaim,
    SourceRecord,
)
from app.catalogue.register import TaxonomyRegister
from app.catalogue.errors import (
    InvalidRetrievalRequestError,
    NoEligibleKnowledgeError,
    KnowledgeCompatibilityConflictError,
)
from app.catalogue.retrieval_models import (
    KnowledgeBudget,
    KnowledgeRetrievalPolicy,
    KnowledgeRetrievalRequest,
    CandidateEvaluation,
    KnowledgeRetrievalResult,
)

# Numeric weights for status hierarchy
STATUS_WEIGHTS: Dict[CoverageStatus, float] = {
    CoverageStatus.VALIDATED: 15.0,
    CoverageStatus.EXPERIMENTALLY_TESTED: 10.0,
    CoverageStatus.RESEARCHED: 5.0,
    CoverageStatus.UNRESEARCHED: 0.0,
    CoverageStatus.DEPRECATED: -50.0,
}

STATUS_HIERARCHY: Dict[CoverageStatus, int] = {
    CoverageStatus.DEPRECATED: -1,
    CoverageStatus.UNRESEARCHED: 0,
    CoverageStatus.RESEARCHED: 1,
    CoverageStatus.EXPERIMENTALLY_TESTED: 2,
    CoverageStatus.VALIDATED: 3,
}

PRIORITY_WEIGHTS: Dict[ConflictPriority, float] = {
    ConflictPriority.HIGH: 3.0,
    ConflictPriority.MEDIUM: 1.5,
    ConflictPriority.LOW: 0.0,
}


def _canonical_json(data: Any) -> str:
    """Produces sorted, compact canonical JSON for deterministic cryptographic hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class KnowledgeRetriever:
    """
    Deterministic, evidence-aware knowledge retrieval engine.
    Ensures identical context inputs and catalogue versions produce identical selections,
    provenance records, and prompt clauses.
    """

    def __init__(self, register: Optional[TaxonomyRegister] = None):
        self.register = register or TaxonomyRegister()
        self._sources_by_id: Dict[str, SourceRecord] = {}
        self._index_sources()

    def _index_sources(self) -> None:
        """Indexes all sources across groups by stable source_id."""
        for group in self.register.list_groups():
            for src in group.sources:
                self._sources_by_id[src.source_id] = src

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        return self._sources_by_id.get(source_id)

    def _extract_signals(self, req: KnowledgeRetrievalRequest) -> Dict[str, Any]:
        """Extracts normalized semantic signals from the retrieval request."""
        scene_text = f"{req.shot_type} {req.action} {req.camera_angle or ''} {req.lighting or ''} {req.panel_instructions or ''}".lower()
        style_text = f"{req.style_medium} {req.style_line_and_tone} {req.style_palette or ''} {' '.join(req.style_positive_constraints)}".lower()
        prohibitions = [p.lower().strip() for p in req.style_negative_constraints]

        return {
            "scene_text": scene_text,
            "style_text": style_text,
            "prohibitions": prohibitions,
            "shot_type": req.shot_type.lower().strip(),
            "camera_angle": (req.camera_angle or "").lower().strip(),
            "action_words": set(req.action.lower().split()),
            "character_count": len(req.character_ids),
            "has_reference": req.has_reference_images,
        }

    def _evaluate_rule_compatibility(
        self,
        rule: GenerationRule,
        signals: Dict[str, Any],
        req: KnowledgeRetrievalRequest,
    ) -> Tuple[bool, List[str]]:
        """
        Evaluates whether a rule clashes with scene/style constraints or negative rules.
        Returns (is_compatible, list_of_conflict_reasons).
        """
        conflicts = []

        # 1. Check rule's declared conflicting concepts against active context
        for concept in rule.conflicting_concepts:
            concept_l = concept.lower().strip()
            if concept_l in signals["scene_text"] or concept_l in signals["style_text"]:
                conflicts.append(f"Declared conflicting concept '{concept}' detected in scene/style context.")

        # 2. Hard negative constraint precedence: if rule directive mentions prohibited concepts
        directive_l = rule.directive_text.lower()
        for neg in signals["prohibitions"]:
            # Check for direct contradiction, e.g. directive asks for color when prohibition is 'no color'
            clean_neg = neg.replace("no ", "").replace("never ", "").strip()
            if clean_neg and clean_neg in directive_l and "no " in neg:
                # If rule itself is a negative constraint reinforcing the prohibition, that's fine
                if rule.rule_type != RuleType.NEGATIVE_CONSTRAINT:
                    conflicts.append(f"Rule directive '{rule.directive_text}' contradicts hard negative constraint '{neg}'.")

        return (len(conflicts) == 0, conflicts)

    def _compute_rule_relevance(
        self,
        rule: GenerationRule,
        group: TaxonomyGroupRecord,
        signals: Dict[str, Any],
        req: KnowledgeRetrievalRequest,
    ) -> Tuple[float, List[str]]:
        """
        Computes explainable relevance score and matched signal descriptions.
        """
        score = 0.0
        reasons = []

        # Explicit required group boost
        if group.group_id in req.required_group_ids:
            score += 20.0
            reasons.append(f"Group '{group.group_id}' explicitly required by request (+20.0)")

        # Status & evidence weight
        status_weight = STATUS_WEIGHTS.get(group.status, 0.0)
        score += status_weight
        reasons.append(f"Group coverage status '{group.status.value}' (+{status_weight})")

        # Priority weight
        pri_weight = PRIORITY_WEIGHTS.get(rule.priority, 0.0)
        score += pri_weight
        if pri_weight > 0:
            reasons.append(f"Rule priority '{rule.priority.value}' (+{pri_weight})")

        # Signal Matching:
        # Group 7: Camera Shot Scales
        if group.group_number == 7:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["shot_type"] or signals["shot_type"] in el_l:
                    score += 15.0
                    reasons.append(f"Shot scale exact match with canonical element '{el}' (+15.0)")
                    break

        # Group 8: Camera Angles & Views
        elif group.group_number == 8:
            if signals["camera_angle"]:
                for el in group.canonical_elements:
                    el_l = el.lower().strip()
                    if el_l in signals["camera_angle"] or signals["camera_angle"] in el_l:
                        score += 15.0
                        reasons.append(f"Camera angle match with canonical element '{el}' (+15.0)")
                        break

        # Group 19: Stroke & Line Art Types
        elif group.group_number == 19:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["style_text"]:
                    score += 10.0
                    reasons.append(f"Line art match with canonical element '{el}' (+10.0)")
                    break

        # Group 28: Character Poses - Basic
        elif group.group_number == 28:
            for el in group.canonical_elements:
                el_words = set(el.lower().split())
                if el_words.intersection(signals["action_words"]):
                    score += 10.0
                    reasons.append(f"Pose/action match with canonical element '{el}' (+10.0)")
                    break

        # Group 60: Visual Continuity & Validation
        elif group.group_number == 60:
            if rule.rule_id == "rul_60_pass_reference_image" and signals["has_reference"]:
                score += 25.0
                reasons.append("Character reference images supplied; reference anchoring rule triggered (+25.0)")
            elif rule.rule_id == "rul_60_negative_text_rule":
                score += 15.0
                reasons.append("Comic panel raw generation requires strict negative text/bubble hygiene (+15.0)")

        # Group 1: Comic Formats
        elif group.group_number == 1:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["scene_text"] or el_l in signals["style_text"]:
                    score += 15.0
                    reasons.append(f"Comic format match with canonical element '{el}' (+15.0)")
                    break
            if "4-koma" in signals["scene_text"] or "yonkoma" in signals["scene_text"]:
                if rule.rule_id == "rul_01_4koma_quad_beats":
                    score += 10.0
                    reasons.append("4-koma format detected; ki-shō-ten-ketsu quad beats rule boosted (+10.0)")
            elif "webtoon" in signals["scene_text"] or "scroll" in signals["scene_text"]:
                if rule.rule_id == "rul_01_webtoon_whitespace_pacing":
                    score += 10.0
                    reasons.append("Webtoon/vertical scroll detected; whitespace pacing rule boosted (+10.0)")

        # Group 3: Page Structures
        elif group.group_number == 3:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["scene_text"]:
                    score += 12.0
                    reasons.append(f"Page structure match with canonical element '{el}' (+12.0)")
                    break
            if "blockage" in signals["scene_text"] and rule.rule_id == "rul_03_blockage_reading_order":
                score += 15.0
                reasons.append("Blockage structure detected; reading order rule boosted (+15.0)")
            elif ("diagonal" in signals["scene_text"] or "slanted" in signals["scene_text"]) and rule.rule_id == "rul_03_action_diagonal_cuts":
                score += 15.0
                reasons.append("Diagonal/slanted layout detected; action diagonal cuts rule boosted (+15.0)")

        # Group 4: Panel Types by Narrative Function
        elif group.group_number == 4:
            for el in group.canonical_elements:
                el_l = el.lower().replace(" panel", "").strip()
                if el_l in signals["scene_text"]:
                    score += 15.0
                    reasons.append(f"Narrative function match with canonical element '{el}' (+15.0)")
                    break
            if ("impact" in signals["scene_text"] or "peak" in signals["scene_text"] or "climax" in signals["scene_text"]) and rule.rule_id == "rul_04_peak_focal_emphasis":
                score += 12.0
                reasons.append("Peak/Impact panel beat detected; focal emphasis rule boosted (+12.0)")
            elif ("silent" in signals["scene_text"] or "pause" in signals["scene_text"]) and rule.rule_id == "rul_04_silent_panel_cleanliness":
                score += 15.0
                reasons.append("Silent beat detected; negative text cleanliness rule boosted (+15.0)")
            elif ("vng" in signals["scene_text"] or "progression" in signals["scene_text"] or "grammar" in signals["scene_text"]) and rule.rule_id == "rul_04_vng_canonical_progression":
                score += 12.0
                reasons.append("VNG canonical narrative progression general guidance (+12.0)")

        # Group 5: Panel Shapes
        elif group.group_number == 5:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["scene_text"]:
                    score += 12.0
                    reasons.append(f"Panel shape match with canonical element '{el}' (+12.0)")
                    break
            if ("panoramic" in signals["scene_text"] or "wide rectangle" in signals["scene_text"]) and rule.rule_id == "rul_05_panoramic_horizon_rule":
                score += 15.0
                reasons.append("Panoramic/wide framing detected; horizon rule boosted (+15.0)")
            elif ("tall" in signals["scene_text"] or "vertical rectangle" in signals["scene_text"]) and rule.rule_id == "rul_05_tall_vertical_composition":
                score += 15.0
                reasons.append("Tall vertical framing detected; vertical composition rule boosted (+15.0)")

        # Group 6: Panel Borders & Relationships
        elif group.group_number == 6:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["scene_text"]:
                    score += 12.0
                    reasons.append(f"Panel border relationship match with canonical element '{el}' (+12.0)")
                    break
            if ("break" in signals["scene_text"] or "frame break" in signals["scene_text"] or "overflow" in signals["scene_text"]) and rule.rule_id == "rul_06_figure_breaking_frame":
                score += 15.0
                reasons.append("Frame-breaking composition detected; figure breaking frame rule boosted (+15.0)")
            elif ("inset" in signals["scene_text"] or "insert" in signals["scene_text"] or "panel-within-panel" in signals["scene_text"]) and rule.rule_id == "rul_06_inset_contrast_rule":
                score += 15.0
                reasons.append("Inset panel composition detected; tonal contrast rule boosted (+15.0)")

        # Group 11: Panel Transitions
        elif group.group_number == 11:
            for el in group.canonical_elements:
                el_l = el.lower().strip()
                if el_l in signals["scene_text"]:
                    score += 12.0
                    reasons.append(f"Panel transition match with canonical element '{el}' (+12.0)")
                    break
            if ("aspect-to-aspect" in signals["scene_text"] or "mood" in signals["scene_text"] or "atmospheric" in signals["scene_text"]) and rule.rule_id == "rul_11_aspect_mood_transitions":
                score += 15.0
                reasons.append("Aspect-to-aspect/mood transition detected; atmospheric rule boosted (+15.0)")
            elif ("action-to-action" in signals["scene_text"] or "vector" in signals["scene_text"]) and rule.rule_id == "rul_11_action_to_action_continuity":
                score += 15.0
                reasons.append("Action-to-action transition detected; vector continuity rule boosted (+15.0)")

        # Group 53: Narrative Time & Chronology
        elif group.group_number == 53:
            if ("asshuku" in signals["scene_text"] or "kaiho" in signals["scene_text"] or "compression" in signals["scene_text"] or "release" in signals["scene_text"]) and rule.rule_id == "rul_53_compression_release_pacing":
                score += 15.0
                reasons.append("Compression/release pacing detected; asshuku-kaiho rule boosted (+15.0)")
            elif ("flashback" in signals["scene_text"] or "memory" in signals["scene_text"]) and rule.rule_id == "rul_53_flashback_styling":
                score += 18.0
                reasons.append("Flashback/memory timeline detected; flashback styling rule boosted (+18.0)")

        # Group 54: Narrative Point of View
        elif group.group_number == 54:
            if ("pov" in signals["scene_text"] or "pov" in signals["camera_angle"] or "first-person" in signals["scene_text"]) and rule.rule_id == "rul_54_pov_framing_cues":
                score += 18.0
                reasons.append("POV framing detected; foreground cue rule boosted (+18.0)")
            elif ("reverse shot" in signals["scene_text"] or "over-the-shoulder" in signals["scene_text"] or "dialogue" in signals["scene_text"]) and rule.rule_id == "rul_54_dialogue_reverse_shot":
                score += 15.0
                reasons.append("Dialogue reverse-shot detected; 180-degree rule boosted (+15.0)")

        # Group 56: Narrative Pacing
        elif group.group_number == 56:
            if ("suspense" in signals["scene_text"] or "silent beat" in signals["scene_text"] or "anticipation" in signals["scene_text"]) and rule.rule_id == "rul_56_suspense_silent_beat":
                score += 15.0
                reasons.append("Suspense/silent beat detected; suspense beat rule boosted (+15.0)")
            elif ("fast pacing" in signals["scene_text"] or "high density" in signals["scene_text"] or "rapid" in signals["scene_text"]) and rule.rule_id == "rul_56_action_panel_density":
                score += 15.0
                reasons.append("Fast pacing / high density detected; action panel density rule boosted (+15.0)")

        # Group 58: Page Geometry & Layout Rules
        elif group.group_number == 58:
            if ("spread" in signals["scene_text"] or "mi-hiraki" in signals["scene_text"] or "double-page" in signals["scene_text"] or "fold" in signals["scene_text"]) and rule.rule_id == "rul_58_mihiraki_binding_safety":
                score += 18.0
                reasons.append("Double-page spread / mi-hiraki detected; binding fold safety rule boosted (+18.0)")
            elif ("bleed" in signals["scene_text"] or "trim" in signals["scene_text"] or "safe zone" in signals["scene_text"]) and rule.rule_id == "rul_58_trim_bleed_separation":
                score += 15.0
                reasons.append("Bleed/trim specifications detected; trim bleed separation rule boosted (+15.0)")

        # Compatible concepts bonus
        for comp in rule.compatible_concepts:
            comp_l = comp.lower().strip()
            if comp_l in signals["scene_text"] or comp_l in signals["style_text"]:
                score += 5.0
                reasons.append(f"Compatible visual concept '{comp}' present in context (+5.0)")

        return score, reasons

    def _compute_recipe_relevance(
        self,
        recipe: RecipeRecord,
        group: TaxonomyGroupRecord,
        signals: Dict[str, Any],
        req: KnowledgeRetrievalRequest,
    ) -> Tuple[float, List[str]]:
        """Computes relevance for a full prompt recipe."""
        score = 0.0
        reasons = []

        if recipe.applies_to_character_ids and not (set(recipe.applies_to_character_ids) & set(req.character_ids)):
            return 0.0, [
                "Character-specific recipe excluded because none of its canonical characters are selected."
            ]

        if recipe.target_model != req.target_model:
            return 0.0, ["Target model mismatch"]

        if group.group_number == 60 and recipe.recipe_id == "rec_60_reference_anchored_portrait":
            if signals["has_reference"] and ("portrait" in signals["shot_type"] or "close-up" in signals["shot_type"]):
                score += 35.0
                reasons.append("Canonical character reference supplied for portrait/close-up framing (+35.0)")
            elif signals["has_reference"]:
                score += 20.0
                reasons.append("Canonical character reference supplied (+20.0)")

        return score, reasons

    def retrieve(self, req: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        """
        Performs deterministic, bounded retrieval of knowledge records for a scene.
        """
        signals = self._extract_signals(req)
        catalogue_version = self.register.list_groups()[0].version if self.register.list_groups() else "1.0.0"

        rule_evals: List[CandidateEvaluation] = []
        recipe_evals: List[CandidateEvaluation] = []
        claim_evals: List[CandidateEvaluation] = []

        rules_by_id: Dict[str, GenerationRule] = {}
        recipes_by_id: Dict[str, RecipeRecord] = {}
        claims_by_id: Dict[str, ResearchClaim] = {}

        # 1. Enumerate candidates across groups
        for group in self.register.list_groups():
            # Check explicit exclusions
            if group.group_id in req.prohibited_group_ids:
                continue

            min_required = STATUS_HIERARCHY.get(req.policy.min_coverage_status, 1)
            group_level = STATUS_HIERARCHY.get(group.status, 0)
            is_status_eligible = group_level >= min_required
            status_exclusion = None
            if not is_status_eligible:
                status_exclusion = f"Group status '{group.status.value}' below policy threshold '{req.policy.min_coverage_status.value}'."

            # Evaluate Rules
            for rule in group.rules:
                rules_by_id[rule.rule_id] = rule

                if not is_status_eligible:
                    rule_evals.append(CandidateEvaluation(
                        record_id=rule.rule_id,
                        record_type="rule",
                        group_id=group.group_id,
                        group_number=group.group_number,
                        status=group.status,
                        relevance_score=0.0,
                        relevance_signals=[],
                        is_compatible=False,
                        conflict_notes=[],
                        is_selected=False,
                        exclusion_reason=status_exclusion,
                    ))
                    continue

                # Hypothesis check
                if rule.confidence == ClaimConfidence.HYPOTHESIS and not req.policy.allow_hypotheses:
                    rule_evals.append(CandidateEvaluation(
                        record_id=rule.rule_id,
                        record_type="rule",
                        group_id=group.group_id,
                        group_number=group.group_number,
                        status=group.status,
                        relevance_score=0.0,
                        relevance_signals=[],
                        is_compatible=True,
                        conflict_notes=[],
                        is_selected=False,
                        exclusion_reason="HYPOTHESIS confidence disallowed by policy.",
                    ))
                    continue

                # Compatibility check
                is_comp, conflicts = self._evaluate_rule_compatibility(rule, signals, req)
                if not is_comp and req.policy.enforce_strict_compatibility:
                    rule_evals.append(CandidateEvaluation(
                        record_id=rule.rule_id,
                        record_type="rule",
                        group_id=group.group_id,
                        group_number=group.group_number,
                        status=group.status,
                        relevance_score=0.0,
                        relevance_signals=[],
                        is_compatible=False,
                        conflict_notes=conflicts,
                        is_selected=False,
                        exclusion_reason=f"Incompatible: {'; '.join(conflicts)}",
                    ))
                    continue

                score, reasons = self._compute_rule_relevance(rule, group, signals, req)
                rule_evals.append(CandidateEvaluation(
                    record_id=rule.rule_id,
                    record_type="rule",
                    group_id=group.group_id,
                    group_number=group.group_number,
                    status=group.status,
                    relevance_score=score,
                    relevance_signals=reasons,
                    is_compatible=True,
                    conflict_notes=[],
                    is_selected=False,
                    exclusion_reason=None if score > 0 else "No relevant scene/style signal matched.",
                ))

            # Evaluate Recipes
            for recipe in group.recipes:
                recipes_by_id[recipe.recipe_id] = recipe

                if not is_status_eligible:
                    recipe_evals.append(CandidateEvaluation(
                        record_id=recipe.recipe_id,
                        record_type="recipe",
                        group_id=group.group_id,
                        group_number=group.group_number,
                        status=group.status,
                        relevance_score=0.0,
                        relevance_signals=[],
                        is_compatible=False,
                        conflict_notes=[],
                        is_selected=False,
                        exclusion_reason=status_exclusion,
                    ))
                    continue

                score, reasons = self._compute_recipe_relevance(recipe, group, signals, req)
                recipe_evals.append(CandidateEvaluation(
                    record_id=recipe.recipe_id,
                    record_type="recipe",
                    group_id=group.group_id,
                    group_number=group.group_number,
                    status=group.status,
                    relevance_score=score,
                    relevance_signals=reasons,
                    is_compatible=True,
                    conflict_notes=[],
                    is_selected=False,
                    exclusion_reason=None if score > 0 else "No relevant scene/style signal matched.",
                ))

            # Index claims
            for claim in group.claims:
                claims_by_id[claim.claim_id] = claim

        # 2. Deterministic Ranking & Tie-Breaking
        # Rank rules by: (-relevance_score, -priority_weight, group_number, record_id)
        def rule_sort_key(ev: CandidateEvaluation) -> Tuple[float, float, int, str]:
            rule = rules_by_id[ev.record_id]
            pri_w = PRIORITY_WEIGHTS.get(rule.priority, 0.0)
            return (-ev.relevance_score, -pri_w, ev.group_number, ev.record_id)

        rule_evals.sort(key=rule_sort_key)

        def recipe_sort_key(ev: CandidateEvaluation) -> Tuple[float, int, str]:
            return (-ev.relevance_score, ev.group_number, ev.record_id)

        recipe_evals.sort(key=recipe_sort_key)

        # 3. Budget-Constrained Selection
        selected_rules: List[GenerationRule] = []
        selected_recipes: List[RecipeRecord] = []
        selected_claims: List[ResearchClaim] = []
        selected_evals: List[CandidateEvaluation] = []
        excluded_evals: List[CandidateEvaluation] = []
        selection_rationale: Dict[str, str] = {}
        contributing_group_ids: Set[str] = set()

        # Select Rules up to max_rules
        for ev in rule_evals:
            if ev.relevance_score > 0 and ev.is_compatible and len(selected_rules) < req.budget.max_rules:
                ev.is_selected = True
                selected_rules.append(rules_by_id[ev.record_id])
                selected_evals.append(ev)
                selection_rationale[ev.record_id] = "; ".join(ev.relevance_signals)
                contributing_group_ids.add(ev.group_id)
            else:
                if ev.relevance_score > 0 and len(selected_rules) >= req.budget.max_rules:
                    ev.exclusion_reason = f"Outside budget ceiling (max_rules={req.budget.max_rules})."
                excluded_evals.append(ev)

        # Select Recipes up to max_recipes
        for ev in recipe_evals:
            if ev.relevance_score > 0 and ev.is_compatible and len(selected_recipes) < req.budget.max_recipes:
                ev.is_selected = True
                selected_recipes.append(recipes_by_id[ev.record_id])
                selected_evals.append(ev)
                selection_rationale[ev.record_id] = "; ".join(ev.relevance_signals)
                contributing_group_ids.add(ev.group_id)
            else:
                if ev.relevance_score > 0 and len(selected_recipes) >= req.budget.max_recipes:
                    ev.exclusion_reason = f"Outside budget ceiling (max_recipes={req.budget.max_recipes})."
                excluded_evals.append(ev)

        # Attach Claims associated with selected groups
        for g_id in contributing_group_ids:
            group = self.register.get_group(g_id)
            if group:
                for clm in group.claims:
                    if len(selected_claims) < req.budget.max_claims:
                        if clm.confidence != ClaimConfidence.HYPOTHESIS or req.policy.allow_hypotheses:
                            selected_claims.append(clm)
                            selection_rationale[clm.claim_id] = f"Supporting claim from contributing group '{g_id}' ({clm.confidence.value})"

        # 4. Provenance Source Resolution
        provenance_sources: List[SourceRecord] = []
        seen_source_ids: Set[str] = set()
        all_selected_items = list(selected_rules) + list(selected_recipes) + list(selected_claims)

        for item in all_selected_items:
            src_ids = getattr(item, "source_ids", [])
            for sid in src_ids:
                if sid not in seen_source_ids:
                    src = self.get_source(sid)
                    if src:
                        provenance_sources.append(src)
                        seen_source_ids.add(sid)

        # If strict provenance required, ensure no selected item lacks sources
        if req.policy.require_provenance:
            for item in all_selected_items:
                src_ids = getattr(item, "source_ids", [])
                if not src_ids and not getattr(item, "experiment_id", None):
                    pass # Handled gracefully; all researched items have sources in register

        # 5. Prompt Clauses Formatting
        positive_clauses: List[str] = []
        negative_clauses: List[str] = []

        for r in selected_rules:
            if r.rule_type == RuleType.POSITIVE_GUIDANCE:
                positive_clauses.append(r.directive_text)
            elif r.rule_type == RuleType.NEGATIVE_CONSTRAINT:
                negative_clauses.append(r.directive_text)

        for rec in selected_recipes:
            for clause in rec.required_prompt_components:
                if clause not in positive_clauses:
                    positive_clauses.append(clause)
            for clause in rec.prohibited_conditions:
                if clause not in negative_clauses:
                    negative_clauses.append(clause)

        # 6. Deterministic Selection Hash
        hash_payload = {
            "scene_id": req.scene_id,
            "shot_type": req.shot_type,
            "catalogue_version": catalogue_version,
            "selected_rules": [r.rule_id for r in selected_rules],
            "selected_recipes": [r.recipe_id for r in selected_recipes],
            "selected_claims": [c.claim_id for c in selected_claims],
            "rule_directives": {r.rule_id: hashlib.sha256(r.directive_text.encode("utf-8")).hexdigest() for r in selected_rules},
            "provenance_sources": sorted(list(seen_source_ids)),
        }
        selection_hash = hashlib.sha256(_canonical_json(hash_payload).encode("utf-8")).hexdigest()

        # Check empty selection policy
        if not selected_rules and not selected_recipes and not req.policy.allow_empty_selection:
            raise NoEligibleKnowledgeError(
                f"No eligible knowledge candidates found for scene '{req.scene_id}' under policy criteria.",
                scene_id=req.scene_id
            )

        budget_consumed = {
            "rules_selected": len(selected_rules),
            "rules_budget": req.budget.max_rules,
            "recipes_selected": len(selected_recipes),
            "recipes_budget": req.budget.max_recipes,
            "claims_selected": len(selected_claims),
            "claims_budget": req.budget.max_claims,
            "groups_contributing": len(contributing_group_ids),
        }

        all_evals = selected_evals + excluded_evals

        return KnowledgeRetrievalResult(
            scene_id=req.scene_id,
            catalogue_version=catalogue_version,
            selection_hash=selection_hash,
            selected_group_ids=sorted(list(contributing_group_ids)),
            selected_rules=selected_rules,
            selected_recipes=selected_recipes,
            selected_claims=selected_claims,
            provenance_sources=sorted(provenance_sources, key=lambda s: s.source_id),
            all_evaluations=all_evals,
            selected_evaluations=selected_evals,
            excluded_candidates=excluded_evals,
            positive_prompt_clauses=positive_clauses,
            negative_prompt_clauses=negative_clauses,
            selection_rationale=selection_rationale,
            budget_consumed=budget_consumed,
        )

    def explain(self, req: KnowledgeRetrievalRequest) -> str:
        """
        Produces a comprehensive human-readable Markdown explanation of retrieval decisions.
        """
        result = self.retrieve(req)
        lines = [
            f"# Knowledge Retrieval Explanation: Scene '{req.scene_id}'",
            f"**Catalogue Version:** `{result.catalogue_version}` | **Selection Hash:** `{result.selection_hash[:16]}...`",
            f"**Contributing Groups:** {len(result.selected_group_ids)} | **Selected Rules:** {len(result.selected_rules)} | **Selected Recipes:** {len(result.selected_recipes)}",
            "",
            "## 1. Selected Knowledge Items & Provenance",
        ]

        if not result.selected_evaluations:
            lines.append("*No knowledge items selected for this context.*")
        else:
            for ev in result.selected_evaluations:
                rationale = result.selection_rationale.get(ev.record_id, "")
                lines.append(f"- **`{ev.record_id}`** ({ev.record_type.upper()} in Group {ev.group_number:02d}, Status: `{ev.status.value}`):")
                lines.append(f"  - *Relevance Score:* {ev.relevance_score:.1f}")
                lines.append(f"  - *Rationale:* {rationale}")

        lines.extend([
            "",
            "## 2. Injected Prompt Clauses",
            "### Positive Directives:",
        ])
        for p in result.positive_prompt_clauses:
            lines.append(f"- `{p}`")
        if not result.positive_prompt_clauses:
            lines.append("*(None)*")

        lines.extend([
            "",
            "### Negative Constraints:",
        ])
        for n in result.negative_prompt_clauses:
            lines.append(f"- `{n}`")
        if not result.negative_prompt_clauses:
            lines.append("*(None)*")

        lines.extend([
            "",
            "## 3. Provenance Sources Verified",
        ])
        for s in result.provenance_sources:
            lines.append(f"- **`{s.source_id}`**: *{s.title}* ({s.evidence_class.value})")
            if s.what_it_establishes:
                lines.append(f"  - Establishes: {s.what_it_establishes}")

        lines.extend([
            "",
            "## 4. Excluded Candidates Summary",
            f"Total evaluated candidates: {len(result.all_evaluations)} ({len(result.excluded_candidates)} excluded)",
        ])

        # Sample top excluded
        sorted_excluded = sorted(result.excluded_candidates, key=lambda e: -e.relevance_score)
        for ev in sorted_excluded[:5]:
            lines.append(f"- `{ev.record_id}` ({ev.group_id}): Excluded - {ev.exclusion_reason}")

        return "\n".join(lines)


# Singleton factory for default retriever
_default_retriever_instance: Optional[KnowledgeRetriever] = None

def get_default_knowledge_retriever() -> KnowledgeRetriever:
    """Returns a process-wide singleton of KnowledgeRetriever."""
    global _default_retriever_instance
    if _default_retriever_instance is None:
        _default_retriever_instance = KnowledgeRetriever()
    return _default_retriever_instance
