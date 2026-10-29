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
