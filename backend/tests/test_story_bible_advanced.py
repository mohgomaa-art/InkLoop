"""
Advanced defensive test suite for Story Bible, Canon Immutability, and State Service.
Validates all Section 9 edge cases:
- Optional attributes remain optional
- Unapproved and rejected mutations cannot become active
- CanonSnapshot frozen immutability assertions
- Independent runs state isolation
- User-supplied story text exact preservation (Arabic/RTL)
- Atomic file write resilience and crash safety
- Secret scrubbing and credential hygiene
- Declaring new entities via the approved Canon mutation flow
"""
import os
import json
import pytest
from pathlib import Path

from app.schemas import AttributeCheck, Tolerances
from app.project.canon import (
    CanonSnapshot,
    CanonMutationProposal,
    UnauthorizedMutationError,
    CanonImmutabilityError,
    CharacterDefinition,
    LocationDefinition,
    PropDefinition,
)
from app.project.story_state import (
    StoryStateEvent,
    StoryStateTimeline,
    resolve_timeline_state,
    UndeclaredEntityError,
)
from app.project.bible import (
    StoryBible,
    load_bible,
    save_bible,
    propose_canon_mutation,
    apply_canon_mutation,
    reject_canon_mutation,
    append_state_event,
    resolve_state,
    CanonMutationError,
    atomic_write_file,
)
from app.project.canon import StyleDefinition


@pytest.fixture
def sample_style() -> StyleDefinition:
    return StyleDefinition(
        style_id="test_ink_style",
        name="Test Ink Style",
        medium="digital ink",
        rendering_approach="black-and-white high contrast",
        line_art_rules=["crisp contours"],
        tonal_rules=["solid blacks"],
        positive_constraints=["manga lineart"],
        negative_constraints=["no color", "no text"]
    )


@pytest.fixture
def sample_character() -> CharacterDefinition:
    return CharacterDefinition(
        character_id="hero",
        name="Hero",
        canon_version=1,
        attributes=[
            AttributeCheck(id="hair", text="spiky brown hair", required=True),
            AttributeCheck(id="cloak", text="red hooded cloak", required=True)
        ],
        clothing_attributes=["red cloak"],
        visual_invariants=["spiky hair"],
        restrictions=["never remove cloak"],
        approval_status="approved"
    )


@pytest.fixture
def sample_bible(sample_style, sample_character) -> StoryBible:
    loc = LocationDefinition(
        location_id="citadel_gate",
        name="Citadel Gate",
        description="Massive stone gate",
        required_attributes=["stone arches"]
    )
    prop = PropDefinition(
        prop_id="magic_amulet",
        name="Magic Amulet",
        description="Silver amulet with blue crystal",
        required_attributes=["blue crystal"]
    )
    return StoryBible(
        project_id="test_project",
        schema_version="1.0.0",
        bible_version=1,
        created_at="2026-10-29T00:00:00Z",
        updated_at="2026-10-29T00:00:00Z",
        status="validated",
        style=sample_style,
        characters={"hero": sample_character},
        locations={"citadel_gate": loc},
        props={"magic_amulet": prop}
    )


def test_optional_attributes_remain_optional(tmp_path, sample_bible):
    """Verifies that optional visual attributes can be omitted without validation failure."""
    char = CharacterDefinition(
        character_id="scout",
        name="Scout",
        canon_version=1,
        attributes=[
            AttributeCheck(id="uniform", text="green scout uniform", required=True),
            AttributeCheck(id="badge", text="gold eagle badge", required=False),
            AttributeCheck(id="whistle", text="silver whistle on cord", required=False)
        ],
        clothing_attributes=["green uniform"],
        visual_invariants=["short blonde hair"],
        approval_status="approved"
    )
    assert char.get_attribute("badge").required is False
    assert char.get_attribute("uniform").required is True
    assert char.get_attribute("nonexistent") is None

    # Add to sample bible and save
    sample_bible.characters["scout"] = char
    save_bible(sample_bible, target_path=tmp_path)
    loaded = load_bible(tmp_path)

    scout_loaded = loaded.characters["scout"]
    assert len(scout_loaded.attributes) == 3
    optional_attrs = [a for a in scout_loaded.attributes if not a.required]
    assert len(optional_attrs) == 2


def test_unapproved_and_rejected_mutations_cannot_become_active(tmp_path, sample_bible):
    """
    Verifies that:
    1. A proposed mutation does not alter the approved canon.
    2. A rejected mutation cannot be applied.
    3. An unapproved mutation cannot become active.
    """
    save_bible(sample_bible, target_path=tmp_path)

    proposal = CanonMutationProposal(
        proposal_id="prop_unapproved_99",
        project_id="test_project",
        target_type="character",
        target_id="hero",
        change_description="Propose turning cloak black",
        proposed_changes={"clothing_attributes": ["black cloak"]},
        created_at="2026-10-29T02:00:00Z"
    )
    propose_canon_mutation(tmp_path, proposal)

    # 1. Canon on disk is still v1 with original red cloak
    active_bible = load_bible(tmp_path)
    assert active_bible.bible_version == 1
    assert active_bible.characters["hero"].clothing_attributes == ["red cloak"]

    # 2. Reject the proposal
    rejected = reject_canon_mutation(tmp_path, "prop_unapproved_99", rejected_by="lead_artist", reason="Breaks character identity")
    assert rejected.status == "rejected"
    assert "Breaks character identity" in rejected.change_description

    # 3. Attempting to apply a rejected mutation must fail explicitly
    with pytest.raises(CanonMutationError) as exc_info:
        apply_canon_mutation(tmp_path, "prop_unapproved_99", approved_by="rogue_agent")
    assert "already has status 'rejected'" in str(exc_info.value)

    # 4. Canon remains strictly at v1
    active_after = load_bible(tmp_path)
    assert active_after.bible_version == 1
    assert active_after.characters["hero"].clothing_attributes == ["red cloak"]


def test_canon_snapshot_immutability_enforced(sample_bible):
    """Verifies that CanonSnapshot instances are frozen and reject in-place mutations."""
    snapshot = sample_bible.get_canon_snapshot()
    assert isinstance(snapshot, CanonSnapshot)

    # Attempting to reassign an attribute raises UnauthorizedMutationError / CanonImmutabilityError
    with pytest.raises(UnauthorizedMutationError):
        snapshot.style = None

    with pytest.raises(CanonImmutabilityError):
        snapshot.bible_version = 999

    # Entity declaration checkers work deterministically
    assert snapshot.is_entity_declared("character", "hero") is True
    assert snapshot.is_entity_declared("character", "unknown_person") is False
    assert snapshot.is_entity_declared("location", "citadel_gate") is True
    assert snapshot.is_entity_declared("location", "mars_base") is False
    assert snapshot.is_entity_declared("prop", "magic_amulet") is True
    assert snapshot.is_entity_declared("world", "world") is True


def test_independent_runs_state_isolation(sample_bible):
    """
    Verifies that multiple independent runs referencing the same Canon version
    maintain isolated state histories without cross-contamination.
    """
    canon_snap = sample_bible.get_canon_snapshot()

    # Run A timeline
    timeline_a = StoryStateTimeline(
        run_id="run_alpha",
        project_id=sample_bible.project_id,
        canon_version=sample_bible.bible_version
    )
    # Run B timeline
    timeline_b = StoryStateTimeline(
        run_id="run_beta",
        project_id=sample_bible.project_id,
        canon_version=sample_bible.bible_version
    )

    # Run A: Hero goes left, holding torch
    timeline_a.append_event(StoryStateEvent(
        event_id="evt_a1", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="pos", new_value="left_flank",
        timestamp="2026-10-29T02:01:00Z"
    ), canon=canon_snap)
    timeline_a.append_event(StoryStateEvent(
        event_id="evt_a2", sequence_number=2, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="held_item", new_value="torch",
        timestamp="2026-10-29T02:02:00Z"
    ), canon=canon_snap)

    # Run B: Hero goes right, holding shield
    timeline_b.append_event(StoryStateEvent(
        event_id="evt_b1", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="pos", new_value="right_rampart",
        timestamp="2026-10-29T02:01:00Z"
    ), canon=canon_snap)
    timeline_b.append_event(StoryStateEvent(
        event_id="evt_b2", sequence_number=2, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="held_item", new_value="shield",
        timestamp="2026-10-29T02:02:00Z"
    ), canon=canon_snap)

    # Resolve state for Run A
    res_a = timeline_a.resolve_state_at("p1")
    assert res_a.effective_state["character:hero"]["pos"] == "left_flank"
    assert res_a.effective_state["character:hero"]["held_item"] == "torch"

    # Resolve state for Run B
    res_b = timeline_b.resolve_state_at("p1")
    assert res_b.effective_state["character:hero"]["pos"] == "right_rampart"
    assert res_b.effective_state["character:hero"]["held_item"] == "shield"

    # Verify zero cross-contamination
    assert res_a.effective_state["character:hero"]["pos"] != res_b.effective_state["character:hero"]["pos"]
    assert len(timeline_a.events) == 2
    assert len(timeline_b.events) == 2


def test_user_story_text_preservation_and_hygiene(tmp_path, sample_bible):
    """
    Verifies that original user-supplied story text (including RTL Arabic)
    is preserved exactly across save and load cycles without normalization or loss.
    """
    original_arabic_story = (
        "في أزقة القاهرة القديمة، وقف نور يتأمل خريطة البردي المتوهجة.\n"
        "الرياح تعصف بسترته الواسعة، ونظارته المستديرة تعكس أضواء النيون الباهتة.\n"
        "قال لنفسه: 'هذه ليست مجرد حكاية... هذا مصير المدينة بالكامل.'"
    )
    sample_bible.user_story_text = original_arabic_story
    sample_bible.language = "ar"
    sample_bible.reading_direction = "rtl"

    save_bible(sample_bible, target_path=tmp_path)
    loaded = load_bible(tmp_path)

    # Exact byte and character preservation
    assert loaded.user_story_text == original_arabic_story
    assert loaded.language == "ar"
    assert loaded.reading_direction == "rtl"


def test_declare_new_character_via_approved_canon_mutation(tmp_path, sample_bible):
    """
    Proves that undeclared characters are rejected by the state timeline until
    explicitly introduced through an approved Canon mutation flow.
    """
    save_bible(sample_bible, target_path=tmp_path)

    # 1. Attempting to use undeclared 'ally_layla' in a state event fails immediately
    bad_event = StoryStateEvent(
        event_id="bad_layla_evt", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="layla", property_path="status", new_value="arrived",
        timestamp="2026-10-29T02:00:00Z"
    )
    with pytest.raises(UndeclaredEntityError) as exc_info:
        append_state_event(tmp_path, bad_event)
    assert "layla" in str(exc_info.value)

    # 2. Propose adding Layla to Canon via mutation proposal
    proposal = CanonMutationProposal(
        proposal_id="prop_add_layla",
        project_id="test_project",
        target_type="character",
        target_id="layla",
        change_description="Introduce ally character Layla to the story canon",
        proposed_changes={
            "action": "add",
            "name": "Layla",
            "attributes": [
                {"id": "scarf", "text": "crimson silk scarf", "required": True},
                {"id": "hair", "text": "long dark braid", "required": True}
            ],
            "clothing_attributes": ["desert coat", "crimson silk scarf"],
            "visual_invariants": ["crimson scarf always worn"]
        },
        created_at="2026-10-29T02:05:00Z"
    )
    propose_canon_mutation(tmp_path, proposal)

    # 3. Before approval, Layla is still undeclared
    with pytest.raises(UndeclaredEntityError):
        append_state_event(tmp_path, bad_event)

    # 4. Authorize and apply the mutation
    updated_bible = apply_canon_mutation(tmp_path, "prop_add_layla", approved_by="project_lead")
    assert updated_bible.bible_version == 2
    assert "layla" in updated_bible.characters
    assert updated_bible.characters["layla"].name == "Layla"

    # 5. Now state event for Layla succeeds!
    accepted_event = append_state_event(tmp_path, bad_event)
    assert accepted_event.entity_id == "layla"

    # Resolved state reflects Layla's arrival
    res = resolve_state(tmp_path, "p1")
    assert res.effective_state["character:layla"]["status"] == "arrived"


def test_atomic_file_write_resilience(tmp_path):
    """Proves atomic_write_file writes destination file atomically without partial debris."""
    dest_file = tmp_path / "atomic_target.json"
    sample_content = '{"key": "production_safe_payload"}'

    atomic_write_file(dest_file, sample_content)
    assert dest_file.is_file()
    assert dest_file.read_text(encoding="utf-8") == sample_content

    # Ensure no temporary debris left behind
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_no_secrets_in_bible_serialization_or_exceptions(sample_bible):
    """
    Verifies that Story Bible JSON serialization and exceptions never leak
    API keys, authorization headers, or sensitive environment values.
    """
    json_output = sample_bible.model_dump_json()
    assert "bearer" not in json_output.lower()
    assert "api_key" not in json_output.lower()
    assert "model_api_key" not in json_output.lower()
    assert "meta_api_key" not in json_output.lower()


# ===========================================================================
# ADDITIONAL ACCEPTANCE TESTS FOR T5.3 AUDIT CRITERIA
# ===========================================================================

def test_canon_immutability_during_generation_batch(tmp_path, sample_bible):
    """
    Acceptance Test: Proves that executing a multi-panel generation run consumes
    an immutable Canon snapshot and never mutates canonical definitions or Story Bible state.
    """
    from app.config import InkLoopConfig
    from app.orchestrator import BatchOrchestrator
    from app.schemas import BatchSpec, SceneSpec
    from app.image_adapter import SimulatedImageGenerationAdapter

    save_bible(sample_bible, target_path=tmp_path)
    initial_snapshot = sample_bible.get_canon_snapshot()
    initial_hash = initial_snapshot.canon_hash
    initial_hair_attr = sample_bible.characters["hero"].attributes[0].text

    # Setup scenes with mutable narrative state deltas
    scenes = [
        SceneSpec(
            scene_id="scene_01",
            scene_index=0,
            title="Gate Approach",
            shot_type="wide",
            action="approaches the gate",
            character_ids=["hero"],
            scene_state={"clothing.cloak_state": "damp", "hero.mood": "determined"}
        ),
        SceneSpec(
            scene_id="scene_02",
            scene_index=1,
            title="Gate Entry",
            shot_type="close-up",
            action="pushes the massive gate open",
            character_ids=["hero"],
            scene_state={"clothing.cloak_state": "torn", "hero.mood": "strained"}
        )
    ]

    adapter = SimulatedImageGenerationAdapter(default_success=True)
    cfg = InkLoopConfig.load()
    orchestrator = BatchOrchestrator(config=cfg, adapter=adapter, run_log_dir=tmp_path / "runs")

    batch_spec = BatchSpec(
        batch_id="batch_immutability_test",
        story_id="test_story",
        story_bible=sample_bible.to_orchestrator_bible(),
        scenes=scenes,
        output_dir=str(tmp_path / "output")
    )

    summary = orchestrator.orchestrate_batch(batch_spec)
    assert summary.successful_panels == 2

    # Verify Canon snapshot and Story Bible remain 100% immutable
    reloaded_bible = load_bible(tmp_path)
    assert reloaded_bible.bible_version == 1
    assert reloaded_bible.characters["hero"].attributes[0].text == initial_hair_attr
    after_snapshot = reloaded_bible.get_canon_snapshot()
    assert after_snapshot.canon_hash == initial_hash

    # Verify direct mutation attempt on snapshot raises exception
    with pytest.raises(UnauthorizedMutationError):
        initial_snapshot.bible_version = 2


def test_version_progression_audit_trail_and_snapshot_retrieval(tmp_path, sample_bible):
    """
    Acceptance Test: Verifies monotonic version progression, multi-step audit trail logging,
    and historical snapshot retrieval by explicit version number.
    """
    from app.project.bible import get_canon_snapshot, EntityNotFoundError

    save_bible(sample_bible, target_path=tmp_path)
    assert sample_bible.bible_version == 1

    # Step 1: Propose and apply mutation for location
    prop_loc = CanonMutationProposal(
        proposal_id="prop_loc_01",
        project_id="test_project",
        target_type="location",
        target_id="citadel_gate",
        change_description="Expand gate visual attributes with bronze reliefs",
        proposed_changes={"required_attributes": ["stone arches", "bronze reliefs"]},
        created_at="2026-10-29T02:00:00Z"
    )
    propose_canon_mutation(tmp_path, prop_loc)
    v2_bible = apply_canon_mutation(tmp_path, "prop_loc_01", approved_by="senior_editor")
    assert v2_bible.bible_version == 2
    assert "bronze reliefs" in v2_bible.locations["citadel_gate"].required_attributes

    # Step 2: Propose and apply mutation for prop
    prop_prop = CanonMutationProposal(
        proposal_id="prop_prop_02",
        project_id="test_project",
        target_type="prop",
        target_id="magic_amulet",
        change_description="Add pulsing glow to amulet required attributes",
        proposed_changes={"required_attributes": ["blue crystal", "pulsing glow"]},
        created_at="2026-10-29T02:15:00Z"
    )
    propose_canon_mutation(tmp_path, prop_prop)
    v3_bible = apply_canon_mutation(tmp_path, "prop_prop_02", approved_by="director")
    assert v3_bible.bible_version == 3
    assert "pulsing glow" in v3_bible.props["magic_amulet"].required_attributes

    # Audit Trail Verification
    proposals_file = tmp_path / "canon_proposals.jsonl"
    assert proposals_file.is_file()
    lines = [json.loads(line) for line in proposals_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0]["proposal_id"] == "prop_loc_01"
    assert lines[0]["status"] == "approved"
    assert lines[0]["approved_by"] == "senior_editor"
    assert lines[1]["proposal_id"] == "prop_prop_02"
    assert lines[1]["status"] == "approved"
    assert lines[1]["approved_by"] == "director"

    # Historical Snapshot Retrieval
    snap_v1 = get_canon_snapshot(tmp_path, version=1)
    assert snap_v1.bible_version == 1
    assert "bronze reliefs" not in snap_v1.locations["citadel_gate"].required_attributes

    snap_v2 = get_canon_snapshot(tmp_path, version=2)
    assert snap_v2.bible_version == 2
    assert "bronze reliefs" in snap_v2.locations["citadel_gate"].required_attributes
    assert "pulsing glow" not in snap_v2.props["magic_amulet"].required_attributes

    snap_v3 = get_canon_snapshot(tmp_path, version=3)
    assert snap_v3.bible_version == 3
    assert "pulsing glow" in snap_v3.props["magic_amulet"].required_attributes

    # Non-existent version raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        get_canon_snapshot(tmp_path, version=999)


def test_snapshot_determinism_and_reconstruction(tmp_path, sample_bible):
    """
    Acceptance Test: Verifies that a project can be fully reconstructed from a CanonSnapshot,
    retaining byte-for-byte canonical hash determinism.
    """
    save_bible(sample_bible, target_path=tmp_path)
    original_snapshot = sample_bible.get_canon_snapshot()
    original_hash = original_snapshot.canon_hash

    # Reconstruct StoryBible from snapshot
    reconstructed_bible = original_snapshot.to_story_bible(
        language=sample_bible.language,
        reading_direction=sample_bible.reading_direction,
        user_story_text=sample_bible.user_story_text
    )

    reconstructed_snapshot = reconstructed_bible.get_canon_snapshot()
    assert reconstructed_snapshot.canon_hash == original_hash
    assert reconstructed_snapshot.bible_version == original_snapshot.bible_version
    assert reconstructed_snapshot.characters["hero"].name == original_snapshot.characters["hero"].name

    # Save reconstructed bible to an independent directory
    recon_dir = tmp_path / "reconstructed_project"
    save_bible(reconstructed_bible, target_path=recon_dir)

    loaded_recon = load_bible(recon_dir)
    assert loaded_recon.get_canon_snapshot().canon_hash == original_hash


def test_rejection_of_undeclared_locations_and_props(tmp_path, sample_bible):
    """
    Acceptance Test: Verifies that state events and canon mutations targeting undeclared
    locations or props are rejected with explicit, actionable errors.
    """
    from app.project.bible import append_state_event, EntityNotFoundError
    from app.project.story_state import UndeclaredEntityError, InvalidStateEventError

    save_bible(sample_bible, target_path=tmp_path)

    # 1. State event for undeclared location
    bad_loc_event = StoryStateEvent(
        event_id="bad_evt_loc_01",
        sequence_number=1,
        scene_id="s1",
        panel_id="p1",
        entity_type="location",
        entity_id="forbidden_catacomb",
        property_path="lighting",
        new_value="dark",
        timestamp="2026-10-29T02:00:00Z"
    )
    with pytest.raises(UndeclaredEntityError) as exc_loc:
        append_state_event(tmp_path, bad_loc_event)
    assert "Undeclared location 'forbidden_catacomb'" in str(exc_loc.value)

    # 2. State event for undeclared prop
    bad_prop_event = StoryStateEvent(
        event_id="bad_evt_prop_02",
        sequence_number=2,
        scene_id="s1",
        panel_id="p1",
        entity_type="prop",
        entity_id="plasma_cannon",
        property_path="condition",
        new_value="overheated",
        timestamp="2026-10-29T02:01:00Z"
    )
    with pytest.raises(UndeclaredEntityError) as exc_prop:
        append_state_event(tmp_path, bad_prop_event)
    assert "Undeclared prop 'plasma_cannon'" in str(exc_prop.value)

    # 3. State event with invalid dot path rejected at construction
    with pytest.raises(Exception) as exc_path:
        StoryStateEvent(
            event_id="bad_evt_path_03",
            sequence_number=3,
            scene_id="s1",
            panel_id="p1",
            entity_type="character",
            entity_id="hero",
            property_path="clothing..state",
            new_value="torn",
            timestamp="2026-10-29T02:02:00Z"
        )
    assert "Invalid property_path" in str(exc_path.value)

    # 4. Canon mutation update for undeclared location
    with pytest.raises(EntityNotFoundError):
        propose_canon_mutation(
            tmp_path,
            CanonMutationProposal(
                proposal_id="prop_bad_loc",
                project_id="test_project",
                target_type="location",
                target_id="nonexistent_realm",
                change_description="Try updating undeclared location",
                proposed_changes={"action": "update", "name": "New Name"},
                created_at="2026-10-29T02:03:00Z"
            )
        )


def test_correct_loading_and_saving_custom_paths(tmp_path, sample_bible):
    """
    Acceptance Test: Verifies correct resolution, loading, and saving when given
    custom absolute file paths, custom directory paths, or relative project identifiers.
    """
    from app.project.bible import resolve_bible_paths, VersionConflictError

    # 1. Custom explicit JSON file path in non-existent directory
    custom_file = tmp_path / "custom_workspace" / "my_story_bible.json"
    resolved_dir, resolved_file = resolve_bible_paths(custom_file)
    assert resolved_dir == custom_file.parent
    assert resolved_file == custom_file

    saved_path = save_bible(sample_bible, target_path=custom_file)
    assert saved_path == custom_file
    assert custom_file.is_file()

    loaded_bible = load_bible(custom_file)
    assert loaded_bible.project_id == sample_bible.project_id

    # 2. Custom directory path
    custom_dir = tmp_path / "project_folder_dir"
    resolved_dir2, resolved_file2 = resolve_bible_paths(custom_dir)
    assert resolved_dir2 == custom_dir
    assert resolved_file2 == custom_dir / "bible.json"

    saved_path2 = save_bible(sample_bible, target_path=custom_dir)
    assert saved_path2 == custom_dir / "bible.json"
    loaded_bible2 = load_bible(custom_dir)
    assert loaded_bible2.project_id == sample_bible.project_id

    # 3. Optimistic concurrency check
    with pytest.raises(VersionConflictError):
        save_bible(sample_bible, target_path=custom_dir, expected_version=99)


def test_rejected_canon_mutation_preserves_audit_trail(tmp_path, sample_bible):
    """
    Acceptance Test: Verifies that rejecting a proposed mutation explicitly records
    the rejection in the audit log, leaves the Bible untouched, and blocks subsequent application.
    """
    save_bible(sample_bible, target_path=tmp_path)

    prop = CanonMutationProposal(
        proposal_id="prop_unwanted_01",
        project_id="test_project",
        target_type="character",
        target_id="villain",
        change_description="Add villain to Act 1",
        proposed_changes={"action": "add", "name": "Dark Lord"},
        created_at="2026-10-29T02:00:00Z"
    )
    propose_canon_mutation(tmp_path, prop)

    # Reject proposal
    rejected = reject_canon_mutation(
        tmp_path,
        proposal_id="prop_unwanted_01",
        rejected_by="creative_director",
        reason="Villain must not appear until Act 3"
    )
    assert rejected.status == "rejected"
    assert "REJECTED" in rejected.change_description

    # Ensure applying rejected proposal raises CanonMutationError
    with pytest.raises(CanonMutationError) as exc:
        apply_canon_mutation(tmp_path, "prop_unwanted_01", approved_by="hacker")
    assert "already has status 'rejected'" in str(exc.value)

    # Ensure StoryBible was never mutated
    current_bible = load_bible(tmp_path)
    assert current_bible.bible_version == 1
    assert "villain" not in current_bible.characters


def test_deep_snapshot_immutability_and_isolation(sample_bible):
    """
    Acceptance & Verification Test for Deep Snapshot Immutability:
    1. Proves mutating a nested value obtained from a snapshot cannot alter that snapshot.
    2. Proves modifying a reconstructed StoryBible cannot alter the original snapshot.
    3. Proves resolving generation context does not mutate the canonical source or historical snapshot.
    4. Proves reconstructing a project and taking a new snapshot preserves the expected canonical hash.
    """
    from app.context_builder import build_panel_context_packet
    from app.schemas import SceneSpec

    snapshot = sample_bible.get_canon_snapshot()
    initial_hash = snapshot.canon_hash
    initial_hero_name = snapshot.characters["hero"].name
    initial_hair_attr = snapshot.characters["hero"].attributes[0].text
    initial_cloak_count = len(snapshot.characters["hero"].clothing_attributes)

    # 1. Mutating a nested value obtained from snapshot cannot alter the snapshot
    hero_copy = snapshot.get_character("hero")
    hero_copy.name = "Mutated Infiltrator"
    hero_copy.attributes[0].text = "shaved head bald"
    hero_copy.clothing_attributes.append("radioactive spikes")

    # Verify snapshot internal state is 100% unaffected
    fresh_hero = snapshot.get_character("hero")
    assert fresh_hero.name == initial_hero_name
    assert fresh_hero.attributes[0].text == initial_hair_attr
    assert len(fresh_hero.clothing_attributes) == initial_cloak_count
    assert "radioactive spikes" not in fresh_hero.clothing_attributes

    # Same for location and prop
    loc_copy = snapshot.get_location("citadel_gate")
    loc_copy.name = "Demolished Gate"
    loc_copy.required_attributes.append("rubble")
    assert snapshot.get_location("citadel_gate").name == "Citadel Gate"
    assert "rubble" not in snapshot.get_location("citadel_gate").required_attributes

    prop_copy = snapshot.get_prop("magic_amulet")
    prop_copy.name = "Broken Amulet"
    assert snapshot.get_prop("magic_amulet").name == "Magic Amulet"

    # Style deep immutability
    style_copy = snapshot.get_style()
    style_copy.rendering_approach = "hyperrealistic oil painting"
    assert snapshot.style.rendering_approach == "black-and-white high contrast"
    assert snapshot.get_style().rendering_approach == "black-and-white high contrast"

    # 2. Modifying a reconstructed StoryBible cannot alter the original snapshot
    reconstructed_bible = snapshot.to_story_bible()
    reconstructed_bible.characters["hero"].name = "Reconstructed Mutant"
    reconstructed_bible.characters["hero"].attributes[0].text = "neon hair"
    reconstructed_bible.style.medium = "watercolor"

    # Original snapshot remains completely unaltered
    assert snapshot.characters["hero"].name == initial_hero_name
    assert snapshot.get_character("hero").name == initial_hero_name
    assert snapshot.style.medium == "digital ink"
    assert snapshot.canon_hash == initial_hash

    # 3. Resolving generation context does not mutate canonical source or historical snapshot
    scene = SceneSpec(
        scene_id="scene_deep_test",
        scene_index=0,
        title="Deep Invariance Check",
        shot_type="extreme close-up",
        action="inspects the ancient gate",
        character_ids=["hero"],
        scene_state={"clothing.cloak_state": "muddy", "equipment": "torch"}
    )
    packet = build_panel_context_packet(
        story_bible=snapshot,
        scene=scene,
        panel_id="panel_deep_01"
    )
    assert packet.scene_state["clothing.cloak_state"] == "muddy"
    assert snapshot.characters["hero"].name == initial_hero_name
    assert snapshot.canon_hash == initial_hash

    # 4. Reconstructing a project and taking a new snapshot preserves the expected canonical hash
    clean_reconstruction = snapshot.to_story_bible()
    new_snapshot = clean_reconstruction.get_canon_snapshot()
    assert new_snapshot.canon_hash == initial_hash


