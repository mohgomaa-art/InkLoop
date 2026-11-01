"""
InkLoop Image Knowledge Catalogue - Panel Types Research Ingestion Test Suite.
Verifies the ingestion of 12 bibliographic sources and research claims into
the 10 target taxonomy groups (tax_01, tax_03, tax_04, tax_05, tax_06, tax_11,
tax_53, tax_54, tax_56, tax_58) and their retrieval by KnowledgeRetriever.
"""
import pytest
from typing import Set

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
    ResearchClaim,
    SourceRecord,
)
from app.catalogue.register import TaxonomyRegister
from app.catalogue.retrieval_models import (
    KnowledgeBudget,
    KnowledgeRetrievalPolicy,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from app.catalogue.retrieval import KnowledgeRetriever


TARGET_RESEARCHED_GROUP_NUMBERS = [1, 3, 4, 5, 6, 11, 53, 54, 56, 58]

EXPECTED_12_SOURCE_IDS = [
    "src_cohn_2018",
    "src_cohn_2014",
    "src_cohn_2013",
    "src_cohn_2012",
    "src_natsume_2021",
    "src_molotiu_2013",
    "src_comix_2022",
    "src_stewart_2024",
    "src_embassy_japan_yonkoma",
    "src_cambridge_digital_comics",
    "src_chen_2023",
    "src_comics_terminology_2018",
]


@pytest.fixture
def register() -> TaxonomyRegister:
    return TaxonomyRegister()


@pytest.fixture
def retriever(register) -> KnowledgeRetriever:
    return KnowledgeRetriever(register=register)


# ==============================================================================
# 1. Taxonomy Integrity Invariants
# ==============================================================================

def test_60_groups_and_840_elements_invariant(register):
    """Proves all 60 taxonomy groups and exactly 840 canonical elements are preserved."""
    groups = register.list_groups()
    assert len(groups) == 60, f"Expected 60 groups, found {len(groups)}"
    total_elements = sum(len(g.canonical_elements) for g in groups)
    assert total_elements == 840, f"Expected 840 elements, found {total_elements}"

    # Group IDs and numbers must be unique and contiguous 1..60
    assert len(set(g.group_id for g in groups)) == 60
    assert sorted([g.group_number for g in groups]) == list(range(1, 61))


def test_10_target_groups_are_researched(register):
    """
    Verifies that the 10 target taxonomy groups are marked RESEARCHED,
    with rules, claims, sources, failure modes, and open research gaps.
    """
    groups_by_num = {g.group_number: g for g in register.list_groups()}

    for num in TARGET_RESEARCHED_GROUP_NUMBERS:
        group = groups_by_num[num]
        assert group.status == CoverageStatus.RESEARCHED, (
            f"Group {num} ({group.group_id}) status is {group.status}, expected RESEARCHED"
        )
        assert group.has_generation_rules is True, f"Group {num} missing has_generation_rules flag"
        assert group.has_failure_modes is True, f"Group {num} missing has_failure_modes flag"
        # Anti-gaming rule: without benchmark experiments, cannot be marked validated
        assert group.is_empirically_validated is False
        assert group.has_recipes is False

        assert len(group.claims) >= 2, f"Group {num} has {len(group.claims)} claims, expected >= 2"
        assert len(group.rules) >= 2, f"Group {num} has {len(group.rules)} rules, expected >= 2"
        assert len(group.sources) >= 2, f"Group {num} has {len(group.sources)} sources, expected >= 2"
        assert len(group.research_gaps) >= 1, f"Group {num} has no research gaps listed"


def test_bibliographic_sources_provenance(retriever):
    """
    Verifies that all 12 bibliographic sources are instantiated, indexed,
    and carry valid metadata (title, publisher, DOI/URL, what_it_establishes).
    """
    for src_id in EXPECTED_12_SOURCE_IDS:
        src = retriever.get_source(src_id)
        assert src is not None, f"Source '{src_id}' was not found in retriever index"
        assert src.title, f"Source '{src_id}' missing title"
        assert src.publisher, f"Source '{src_id}' missing publisher"
        assert src.url_or_doi, f"Source '{src_id}' missing URL or DOI"
        assert src.publication_date, f"Source '{src_id}' missing publication date"
        assert len(src.what_it_establishes) > 10, f"Source '{src_id}' what_it_establishes too brief"
        assert len(src.what_it_does_not_establish) > 10, f"Source '{src_id}' what_it_does_not_establish too brief"


# ==============================================================================
# 2. Knowledge Retrieval Tests Across the 10 Researched Groups
# ==============================================================================

def test_retrieval_group_01_4koma_and_webtoon(retriever):
    """Tests retrieval of 4-koma progression and webtoon vertical whitespace rules."""
    # 4-koma query
    req_4koma = KnowledgeRetrievalRequest(
        scene_id="scene_4koma_test",
        shot_type="medium shot",
        action="comedic character reaction",
        panel_instructions="Yonkoma format with ki-sho-ten-ketsu progression across 4 equal panels",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_4koma = retriever.retrieve(req_4koma)
    rule_ids = [r.rule_id for r in res_4koma.selected_rules]
    assert "rul_01_4koma_quad_beats" in rule_ids
    rule_4koma = next(r for r in res_4koma.selected_rules if r.rule_id == "rul_01_4koma_quad_beats")
    assert any(s in rule_4koma.source_ids for s in ["src_stewart_2024", "src_embassy_japan_yonkoma"])

    # Webtoon scroll query
    req_webtoon = KnowledgeRetrievalRequest(
        scene_id="scene_webtoon_test",
        shot_type="wide shot",
        action="descending a dark staircase",
        panel_instructions="Webtoon vertical scroll layout with extended blank whitespace",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_webtoon = retriever.retrieve(req_webtoon)
    rule_ids_w = [r.rule_id for r in res_webtoon.selected_rules]
    assert "rul_01_webtoon_whitespace_pacing" in rule_ids_w


def test_retrieval_group_03_page_structures(retriever):
    """Tests retrieval of blockage reading order and action diagonal cut rules."""
    # Blockage query
    req_blockage = KnowledgeRetrievalRequest(
        scene_id="scene_blockage_test",
        shot_type="tall panel",
        action="standing next to stacked smaller panels",
        panel_instructions="Blockage page layout with tall panel beside stacked tiers",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_b = retriever.retrieve(req_blockage)
    rule_ids_b = [r.rule_id for r in res_b.selected_rules]
    assert "rul_03_blockage_reading_order" in rule_ids_b

    # Diagonal cut query
    req_diagonal = KnowledgeRetrievalRequest(
        scene_id="scene_diagonal_test",
        shot_type="action shot",
        action="sword strike against enemy",
        panel_instructions="Dynamic action scene with diagonal grid and slanted cuts",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_d = retriever.retrieve(req_diagonal)
    rule_ids_d = [r.rule_id for r in res_d.selected_rules]
    assert "rul_03_action_diagonal_cuts" in rule_ids_d


def test_retrieval_group_04_narrative_function_and_silence(retriever):
    """Tests retrieval of peak focal emphasis and silent panel cleanliness rules."""
    # Peak beat query
    req_peak = KnowledgeRetrievalRequest(
        scene_id="scene_peak_test",
        shot_type="impact shot",
        action="shattering punch collision",
        panel_instructions="Peak beat impact panel at narrative climax with explosive contrast",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_peak = retriever.retrieve(req_peak)
    rule_ids_p = [r.rule_id for r in res_peak.selected_rules]
    assert "rul_04_peak_focal_emphasis" in rule_ids_p

    # Silent beat query
    req_silent = KnowledgeRetrievalRequest(
        scene_id="scene_silent_test",
        shot_type="close-up",
        action="staring into the distance",
        panel_instructions="Silent panel contemplative pause after the storm",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_silent = retriever.retrieve(req_silent)
    rule_ids_s = [r.rule_id for r in res_silent.selected_rules]
    assert "rul_04_silent_panel_cleanliness" in rule_ids_s
    silent_rule = next(r for r in res_silent.selected_rules if r.rule_id == "rul_04_silent_panel_cleanliness")
    assert silent_rule.rule_type == RuleType.NEGATIVE_CONSTRAINT


def test_retrieval_group_05_panel_shapes(retriever):
    """Tests retrieval of panoramic vista and tall vertical framing rules."""
    # Panoramic query
    req_pano = KnowledgeRetrievalRequest(
        scene_id="scene_pano_test",
        shot_type="wide landscape",
        action="gazing at distant mountains",
        panel_instructions="Panoramic vista wide rectangle panel spanning the full page width",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_p = retriever.retrieve(req_pano)
    rule_ids_p = [r.rule_id for r in res_p.selected_rules]
    assert "rul_05_panoramic_horizon_rule" in rule_ids_p

    # Tall vertical query
    req_tall = KnowledgeRetrievalRequest(
        scene_id="scene_tall_test",
        shot_type="full body shot",
        action="falling from a skyscraper",
        panel_instructions="Tall vertical rectangle towering vertical composition",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_t = retriever.retrieve(req_tall)
    rule_ids_t = [r.rule_id for r in res_t.selected_rules]
    assert "rul_05_tall_vertical_composition" in rule_ids_t


def test_retrieval_group_06_borders_and_relationships(retriever):
    """Tests retrieval of figure breaking frame and inset contrast rules."""
    # Figure breaking frame query
    req_break = KnowledgeRetrievalRequest(
        scene_id="scene_break_test",
        shot_type="impact shot",
        action="kicking forward with foot breaking out of the frame",
        panel_instructions="Dramatic punch with figure breaking frame into the gutter",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_b = retriever.retrieve(req_break)
    rule_ids_b = [r.rule_id for r in res_b.selected_rules]
    assert "rul_06_figure_breaking_frame" in rule_ids_b

    # Inset panel query
    req_inset = KnowledgeRetrievalRequest(
        scene_id="scene_inset_test",
        shot_type="detail insert",
        action="fingers tightening around the hilt",
        panel_instructions="Detail insert panel with high tonal contrast nested inside wide scene",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_i = retriever.retrieve(req_inset)
    rule_ids_i = [r.rule_id for r in res_i.selected_rules]
    assert "rul_06_inset_contrast_rule" in rule_ids_i


def test_retrieval_group_11_panel_transitions(retriever):
    """Tests retrieval of aspect-to-aspect and action-to-action transition rules."""
    # Aspect-to-aspect query
    req_aspect = KnowledgeRetrievalRequest(
        scene_id="scene_aspect_test",
        shot_type="medium close-up",
        action="listening to rain against the glass",
        panel_instructions="Aspect-to-aspect atmospheric mood transition showing streetlamps and rain puddles",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_a = retriever.retrieve(req_aspect)
    rule_ids_a = [r.rule_id for r in res_a.selected_rules]
    assert "rul_11_aspect_mood_transitions" in rule_ids_a

    # Action-to-action query
    req_action = KnowledgeRetrievalRequest(
        scene_id="scene_action_test",
        shot_type="medium shot",
        action="deflecting incoming blade",
        panel_instructions="Action-to-action sequence maintaining strict vector continuity",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_act = retriever.retrieve(req_action)
    rule_ids_act = [r.rule_id for r in res_act.selected_rules]
    assert "rul_11_action_to_action_continuity" in rule_ids_act


def test_retrieval_group_53_narrative_time(retriever):
    """Tests retrieval of asshuku/kaiho pacing and flashback styling rules."""
    # Asshuku / Kaiho query
    req_time = KnowledgeRetrievalRequest(
        scene_id="scene_time_test",
        shot_type="medium shot",
        action="rushing through crowded corridor",
        panel_instructions="Asshuku compression and kaiho release temporal rhythm",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_t = retriever.retrieve(req_time)
    rule_ids_t = [r.rule_id for r in res_t.selected_rules]
    assert "rul_53_compression_release_pacing" in rule_ids_t

    # Flashback query
    req_flashback = KnowledgeRetrievalRequest(
        scene_id="scene_fb_test",
        shot_type="medium close-up",
        action="childhood memory under cherry blossom tree",
        panel_instructions="Past memory flashback sequence with soft vignette borders and desaturated tones",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_fb = retriever.retrieve(req_flashback)
    rule_ids_fb = [r.rule_id for r in res_fb.selected_rules]
    assert "rul_53_flashback_styling" in rule_ids_fb


def test_retrieval_group_54_point_of_view(retriever):
    """Tests retrieval of first-person POV cues and dialogue shot-reverse-shot rules."""
    # First-person POV query
    req_pov = KnowledgeRetrievalRequest(
        scene_id="scene_pov_test",
        shot_type="pov shot",
        camera_angle="first-person POV with foreground hand reaching out",
        action="reaching for the glowing key",
        panel_instructions="Immersive first-person POV framing",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_p = retriever.retrieve(req_pov)
    rule_ids_p = [r.rule_id for r in res_p.selected_rules]
    assert "rul_54_pov_framing_cues" in rule_ids_p

    # Reverse shot query
    req_rev = KnowledgeRetrievalRequest(
        scene_id="scene_rev_test",
        shot_type="over-the-shoulder",
        camera_angle="over-the-shoulder reverse shot",
        action="intense verbal confrontation",
        panel_instructions="Conversational dialogue shot-reverse-shot adhering to the 180-degree rule",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_r = retriever.retrieve(req_rev)
    rule_ids_r = [r.rule_id for r in res_r.selected_rules]
    assert "rul_54_dialogue_reverse_shot" in rule_ids_r


def test_retrieval_group_56_narrative_pacing(retriever):
    """Tests retrieval of suspense silent beat and fast action panel density rules."""
    # Suspense silent beat query
    req_susp = KnowledgeRetrievalRequest(
        scene_id="scene_susp_test",
        shot_type="close-up",
        action="holding breath behind a wooden crate",
        panel_instructions="Silent beat suspense pause immediately before dramatic reveal",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_s = retriever.retrieve(req_susp)
    rule_ids_s = [r.rule_id for r in res_s.selected_rules]
    assert "rul_56_suspense_silent_beat" in rule_ids_s

    # High panel density query
    req_density = KnowledgeRetrievalRequest(
        scene_id="scene_density_test",
        shot_type="medium shot",
        action="rapid martial arts trade of blows",
        panel_instructions="Fast pacing rapid combat with high panel density and tight cropping",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_d = retriever.retrieve(req_density)
    rule_ids_d = [r.rule_id for r in res_d.selected_rules]
    assert "rul_56_action_panel_density" in rule_ids_d


def test_retrieval_group_58_geometry_and_binding(retriever):
    """Tests retrieval of mi-hiraki binding fold safety and trim/bleed separation rules."""
    # Double-page spread query
    req_spread = KnowledgeRetrievalRequest(
        scene_id="scene_spread_test",
        shot_type="epic double-page spread",
        action="army clashing across wide valley",
        panel_instructions="Double-page spread mi-hiraki layout accounting for center spine binding fold",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_sp = retriever.retrieve(req_spread)
    rule_ids_sp = [r.rule_id for r in res_sp.selected_rules]
    assert "rul_58_mihiraki_binding_safety" in rule_ids_sp

    # Bleed trim query
    req_bleed = KnowledgeRetrievalRequest(
        scene_id="scene_bleed_test",
        shot_type="wide shot",
        action="running through thunderstorm",
        panel_instructions="Full bleed canvas with 3mm trim safe zone separation",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3),
    )
    res_bl = retriever.retrieve(req_bleed)
    rule_ids_bl = [r.rule_id for r in res_bl.selected_rules]
    assert "rul_58_trim_bleed_separation" in rule_ids_bl


def test_retrieval_provenance_and_prompt_generation(retriever):
    """
    Verifies that retrieval results provide complete provenance records
    and that prompt clauses can be rendered deterministically.
    """
    req = KnowledgeRetrievalRequest(
        scene_id="scene_provenance_check",
        shot_type="wide shot",
        action="walking across the bridge",
        panel_instructions="Aspect-to-aspect atmospheric mood transition with panoramic horizon",
        target_model="muse-image-1.0",
        budget=KnowledgeBudget(max_rules=3, max_claims=2),
    )
    res = retriever.retrieve(req)

    assert len(res.selected_rules) > 0
    for rule in res.selected_rules:
        # Every selected rule must have at least one source ID
        assert len(rule.source_ids) > 0
        for s_id in rule.source_ids:
            # Source must exist in the index
            src = retriever.get_source(s_id)
            assert src is not None, f"Source '{s_id}' not found for rule '{rule.rule_id}'"

    # Clauses generation
    assert isinstance(res.positive_prompt_clauses, list)
    assert isinstance(res.negative_prompt_clauses, list)
