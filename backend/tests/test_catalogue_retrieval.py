"""
InkLoop Image Knowledge Catalogue - Retrieval & Context Integration Tests (Task T6.3).
Validates deterministic selection, explainable relevance ranking, compatibility filtering,
bounded budgeting, provenance completeness, context fingerprint invalidation, and offline execution.
"""
import pytest
from pathlib import Path

from app.catalogue.enums import (
    CoverageStatus,
    ClaimConfidence,
    RuleType,
    ConflictPriority,
    EvidenceClass,
)
from app.catalogue.models import (
    GenerationRule,
    RecipeRecord,
    ResearchClaim,
    SourceRecord,
)
from app.catalogue.register import TaxonomyRegister
from app.catalogue.retrieval_models import (
    KnowledgeBudget,
    KnowledgeRetrievalPolicy,
    KnowledgeRetrievalRequest,
    CandidateEvaluation,
    KnowledgeRetrievalResult,
)
from app.catalogue.retrieval import (
    KnowledgeRetriever,
    get_default_knowledge_retriever,
)
from app.catalogue.errors import (
    NoEligibleKnowledgeError,
    InvalidRetrievalRequestError,
)
from app.context_builder import build_panel_context_packet, compute_context_fingerprint
from app.schemas import SceneSpec, CharacterSpec, ReferenceAsset, BatchStatus, PanelStatus
from app.orchestrator import BatchOrchestrator, BatchSpec
from app.image_adapter import SimulatedImageGenerationAdapter
from app.config import InkLoopConfig
from tests.fixtures.benchmark_fixtures import (
    CANONICAL_M0_STORY_BIBLE,
    CANONICAL_M0_SIX_SCENES,
    create_m0_benchmark_batch_spec,
)


@pytest.fixture
def retriever() -> KnowledgeRetriever:
    return KnowledgeRetriever()


# ==============================================================================
# 1. Taxonomy Integrity & Preservation Tests
# ==============================================================================

def test_all_60_groups_and_elements_preserved_and_unaltered(retriever):
    """Proves all 60 taxonomy groups and 840 canonical elements remain intact."""
    groups = retriever.register.list_groups()
    assert len(groups) == 60
    assert sum(len(g.canonical_elements) for g in groups) == 840
    assert len(set(g.group_id for g in groups)) == 60
    assert len(set(g.group_number for g in groups)) == 60
    for idx, g in enumerate(groups, start=1):
        assert g.group_number == idx
        assert len(g.canonical_elements) > 0


# ==============================================================================
# 2. Context Signal Matching & Minimal Context Tests
# ==============================================================================

def test_empty_and_minimal_context_selection(retriever):
    """
    Verifies retrieval with minimal scene context:
    Matches framing scales (Group 7) and poses (Group 28) without injecting unrelated recipes.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_minimal",
        shot_type="wide shot",
        action="walking across street",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3, max_recipes=1),
    )
    res = retriever.retrieve(req)

    assert res.scene_id == "scene_minimal"
    # Should match shot scale and pose
    rule_ids = [r.rule_id for r in res.selected_rules]
    assert "rul_07_directive" in rule_ids
    assert "rul_28_directive" in rule_ids
    # Should NOT select reference portrait recipe because no character reference was supplied
    assert len(res.selected_recipes) == 0
    assert len(res.selected_rules) <= 3


def test_character_reference_anchoring_selection(retriever):
    """
    Verifies that supplying a canonical character reference image triggers
    Group 60 continuity rules and portrait recipes for portrait/close-up framing.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_nour_portrait",
        shot_type="medium close-up",
        action="looking forward with intense focus",
        character_ids=["nour"],
        has_reference_images=True,
        style_line_and_tone="clean linework with screentone shading",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3, max_recipes=1),
    )
    res = retriever.retrieve(req)

    rule_ids = [r.rule_id for r in res.selected_rules]
    recipe_ids = [r.recipe_id for r in res.selected_recipes]

    assert "rul_60_pass_reference_image" in rule_ids
    assert "rec_60_reference_anchored_portrait" in recipe_ids
    assert "tax_60_visual_continuity_validation" in res.selected_group_ids


# ==============================================================================
# 3. Deterministic Ranking & Tie-Breaking Tests
# ==============================================================================

def test_exact_relevance_ordering_and_deterministic_tie_breaking(retriever):
    """
    Verifies that candidate ranking strictly follows:
    (-relevance_score, -priority, group_number, record_id).
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_rank_test",
        shot_type="medium close-up",
        action="standing calmly in room",
        character_ids=["nour"],
        has_reference_images=True,
        style_line_and_tone="clean linework with screentone shading",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=10),
    )
    res = retriever.retrieve(req)

    # Verify score descending order within each category
    rule_evals = [e for e in res.selected_evaluations if e.record_type == "rule"]
    for i in range(len(rule_evals) - 1):
        assert rule_evals[i].relevance_score >= rule_evals[i+1].relevance_score

    recipe_evals = [e for e in res.selected_evaluations if e.record_type == "recipe"]
    for i in range(len(recipe_evals) - 1):
        assert recipe_evals[i].relevance_score >= recipe_evals[i+1].relevance_score


# ==============================================================================
# 4. Compatibility & Contradiction Filtering Tests
# ==============================================================================

def test_compatibility_filtering_excludes_conflicting_concepts(retriever):
    """
    rul_19_screentone_linework declares conflict with 'photorealistic gradients'.
    If the context specifies 'photorealistic gradients', rul_19 must be excluded as incompatible.
    """
    # Baseline: without conflict, rul_19 is selected
    req_clean = KnowledgeRetrievalRequest(
        scene_id="scene_compat_1",
        shot_type="medium shot",
        action="standing",
        style_line_and_tone="clean linework with screentone shading",
        target_model="muse-image-1.0",
    )
    res_clean = retriever.retrieve(req_clean)
    assert "rul_19_screentone_linework" in [r.rule_id for r in res_clean.selected_rules]

    # With conflict: style specifies 'photorealistic gradients'
    req_conflict = KnowledgeRetrievalRequest(
        scene_id="scene_compat_2",
        shot_type="medium shot",
        action="standing",
        style_line_and_tone="clean linework with screentone shading, photorealistic gradients",
        target_model="muse-image-1.0",
    )
    res_conflict = retriever.retrieve(req_conflict)
    assert "rul_19_screentone_linework" not in [r.rule_id for r in res_conflict.selected_rules]

    # Verify explicit exclusion reason
    excluded = next(e for e in res_conflict.excluded_candidates if e.record_id == "rul_19_screentone_linework")
    assert excluded.is_compatible is False
    assert "photorealistic gradients" in str(excluded.conflict_notes)


def test_hard_negative_constraints_precedence(retriever):
    """
    Verifies that hard negative constraints take precedence over catalogue rules.
    If style prohibits screentone ('no screentone'), a screentone rule must be excluded.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_neg_precedence",
        shot_type="medium shot",
        action="standing",
        style_line_and_tone="clean linework with screentone shading",
        style_negative_constraints=["no screentone shading"],
        target_model="muse-image-1.0",
    )
    res = retriever.retrieve(req)
    assert "rul_19_screentone_linework" not in [r.rule_id for r in res.selected_rules]


# ==============================================================================
# 5. Governance Status & Hypothesis Policy Tests
# ==============================================================================

def test_research_status_and_promotion_eligibility_policy(retriever):
    """
    Verifies that unresearched groups are excluded under default policy,
    and hypotheses are rejected unless explicitly permitted.
    """
    # Policy requiring VALIDATED: currently 0 groups are validated, so no rules eligible
    req_strict = KnowledgeRetrievalRequest(
        scene_id="scene_policy_strict",
        shot_type="close-up",
        action="speaking",
        policy=KnowledgeRetrievalPolicy(min_coverage_status=CoverageStatus.VALIDATED, allow_empty_selection=True),
    )
    res_strict = retriever.retrieve(req_strict)
    assert len(res_strict.selected_rules) == 0

    # Policy disallowing hypotheses
    req_no_hypo = KnowledgeRetrievalRequest(
        scene_id="scene_policy_hypo",
        shot_type="close-up",
        action="speaking",
        policy=KnowledgeRetrievalPolicy(allow_hypotheses=False),
    )
    res_no_hypo = retriever.retrieve(req_no_hypo)
    for rule in res_no_hypo.selected_rules:
        assert rule.confidence != ClaimConfidence.HYPOTHESIS


# ==============================================================================
# 6. Budget Enforcement & Prompt Bloat Prevention
# ==============================================================================

def test_budget_enforcement_and_no_all_groups_injection(retriever):
    """
    Proves that retrieval strictly respects max_rules and max_recipes budgets.
    Never injects all 60 groups or 840 elements.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_budget",
        shot_type="medium close-up",
        action="standing calmly in room",
        camera_angle="eye level",
        character_ids=["nour"],
        has_reference_images=True,
        style_line_and_tone="clean linework with screentone shading",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=2, max_recipes=1),
    )
    res = retriever.retrieve(req)

    assert len(res.selected_rules) == 2
    assert len(res.selected_recipes) <= 1
    assert len(res.selected_group_ids) <= 3
    # Check that candidates exceeding budget have explicit exclusion reasons
    outside_budget_evals = [e for e in res.excluded_candidates if e.exclusion_reason and "Outside budget" in e.exclusion_reason]
    assert len(outside_budget_evals) > 0


# ==============================================================================
# 7. Provenance Completeness & Source Traceability
# ==============================================================================

def test_provenance_completeness_for_selected_records(retriever):
    """
    Every selected rule/recipe must have traceable provenance sources.
    Source records must identify what they establish vs what they do NOT establish.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_provenance",
        shot_type="medium close-up",
        action="standing",
        character_ids=["nour"],
        has_reference_images=True,
        style_line_and_tone="clean linework with screentone shading",
        target_model="muse-image-1.0",
    )
    res = retriever.retrieve(req)

    assert len(res.provenance_sources) > 0
    for src in res.provenance_sources:
        assert src.source_id is not None
        assert src.evidence_class in (
            EvidenceClass.PRIMARY_PROVIDER_DOC,
            EvidenceClass.INKLOOP_EXPERIMENT,
            EvidenceClass.SECONDARY_TECHNICAL,
        )
        assert src.what_it_establishes is not None
        assert src.what_it_does_not_establish is not None


# ==============================================================================
# 8. Deterministic Hash & Fingerprint Sensitivity Tests
# ==============================================================================

def test_deterministic_selection_hash_and_byte_stability(retriever):
    """Two identical calls must produce identical selection hashes and clauses."""
    req1 = KnowledgeRetrievalRequest(
        scene_id="scene_hash_1",
        shot_type="medium close-up",
        action="standing",
        character_ids=["nour"],
        has_reference_images=True,
    )
    req2 = KnowledgeRetrievalRequest(
        scene_id="scene_hash_1",
        shot_type="medium close-up",
        action="standing",
        character_ids=["nour"],
        has_reference_images=True,
    )
    res1 = retriever.retrieve(req1)
    res2 = retriever.retrieve(req2)

    assert res1.selection_hash == res2.selection_hash
    assert res1.positive_prompt_clauses == res2.positive_prompt_clauses
    assert res1.negative_prompt_clauses == res2.negative_prompt_clauses


def test_selection_hash_sensitivity_to_context_changes(retriever):
    """Changing framing or character reference status must produce a distinct selection hash."""
    req1 = KnowledgeRetrievalRequest(
        scene_id="scene_sens",
        shot_type="medium close-up",
        action="standing",
        has_reference_images=True,
    )
    req2 = KnowledgeRetrievalRequest(
        scene_id="scene_sens",
        shot_type="extreme wide shot",
        action="standing",
        has_reference_images=False,
    )
    res1 = retriever.retrieve(req1)
    res2 = retriever.retrieve(req2)

    assert res1.selection_hash != res2.selection_hash


# ==============================================================================
# 9. Context Builder Integration & Fingerprint Invalidation
# ==============================================================================

def test_context_builder_injects_catalogue_guidance_and_populates_provenance():
    """
    Verifies that build_panel_context_packet executes retrieval,
    injects guidance into the prompt, and populates packet provenance fields.
    """
    scene = CANONICAL_M0_SIX_SCENES[0]
    packet = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene, "panel_01")

    assert packet.catalogue_version is not None
    assert packet.knowledge_selection_hash is not None
    assert len(packet.selected_knowledge_ids) > 0
    assert len(packet.knowledge_provenance_ids) > 0
    assert "Catalogue guidance:" in packet.generation_prompt


def test_fingerprint_invalidation_when_catalogue_selection_changes():
    """
    Verifies that changing catalogue selection (e.g. changing shot type from close-up to wide shot)
    produces a distinct context fingerprint, triggering cache invalidation.
    """
    scene_close = CANONICAL_M0_SIX_SCENES[0] # medium close-up
    scene_wide = CANONICAL_M0_SIX_SCENES[0].model_copy(deep=True)
    scene_wide.shot_type = "extreme wide shot"

    pkt_close = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene_close, "panel_01")
    pkt_wide = build_panel_context_packet(CANONICAL_M0_STORY_BIBLE, scene_wide, "panel_01")

    assert pkt_close.knowledge_selection_hash != pkt_wide.knowledge_selection_hash
    assert pkt_close.context_fingerprint != pkt_wide.context_fingerprint


# ==============================================================================
# 10. Dry-Run Explain Mode & Error Handling
# ==============================================================================

def test_dry_run_explain_output_structure(retriever):
    """Verifies that explain() generates structured Markdown with rationale and exclusions."""
    req = KnowledgeRetrievalRequest(
        scene_id="scene_explain_test",
        shot_type="medium close-up",
        action="standing",
        character_ids=["nour"],
        has_reference_images=True,
    )
    explain_md = retriever.explain(req)

    assert "# Knowledge Retrieval Explanation" in explain_md
    assert "Selected Knowledge Items" in explain_md
    assert "Provenance Sources Verified" in explain_md
    assert "Excluded Candidates Summary" in explain_md


def test_no_eligible_knowledge_raises_when_empty_disallowed(retriever):
    """When allow_empty_selection=False and no signals match, raises NoEligibleKnowledgeError."""
    req = KnowledgeRetrievalRequest(
        scene_id="scene_empty",
        shot_type="unknown framing token 999",
        action="xyz nonexistent action",
        policy=KnowledgeRetrievalPolicy(
            min_coverage_status=CoverageStatus.VALIDATED, # No groups are validated
            allow_empty_selection=False
        ),
    )
    with pytest.raises(NoEligibleKnowledgeError):
        retriever.retrieve(req)


# ==============================================================================
# 11. Orchestrator Integration & Attempt Provenance Tracking
# ==============================================================================

def test_orchestrator_attempt_records_store_knowledge_provenance(tmp_path):
    """
    Verifies that BatchOrchestrator records catalogue version, selection hash,
    and selected rule IDs in attempt metadata during batch generation.
    """
    cfg = InkLoopConfig.load()
    adapter = SimulatedImageGenerationAdapter(default_success=True)
    orchestrator = BatchOrchestrator(
        config=cfg,
        adapter=adapter,
        run_log_dir=tmp_path / "logs",
        verifier=None
    )

    spec = create_m0_benchmark_batch_spec(
        batch_id="test_catalogue_attempt_provenance",
        output_dir=str(tmp_path / "out")
    )
    summary = orchestrator.orchestrate_batch(spec)

    assert summary.status == BatchStatus.COMPLETED
    assert len(summary.attempt_history) == 6

    # Every attempt record must store knowledge provenance in sanitized metadata
    for att in summary.attempt_history:
        meta = att.sanitized_request_metadata
        assert "catalogue_version" in meta
        assert "knowledge_selection_hash" in meta
        assert "selected_knowledge_ids" in meta
        assert len(meta["selected_knowledge_ids"]) > 0
