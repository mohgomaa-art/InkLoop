"""
Defensive unit and integration tests for InkLoop Story Bible, Canon, and State Timeline subsystem.
Validates all Section 10 mandatory test requirements:
- Schema and canon integrity
- State timeline determinism and conflict handling
- Asset integrity, hash validation, and path traversal protection
- Persistence, atomic writes, versioning, and non-pollution of JSON
- M0 Nour reference integration and Continuity Packet context assembly
"""
import os
import json
import time
from pathlib import Path
import pytest

from app.schemas import AttributeCheck, Tolerances, CharacterSpec
from app.project.asset_refs import (
    AssetRef,
    validate_asset_ref,
    compute_file_sha256,
    PathTraversalError,
    AssetNotFoundError,
    AssetHashMismatchError,
    InvalidAssetTypeError
)
from app.project.canon import (
    StyleDefinition,
    CharacterDefinition,
    LocationDefinition,
    PropDefinition,
    CanonMutationProposal,
    CanonSnapshot,
    UnauthorizedMutationError,
    CanonValidationError
)
from app.project.story_state import (
    StoryStateEvent,
    StateResolutionResult,
    resolve_timeline_state,
    validate_event_against_bible,
    UndeclaredEntityError,
    ContradictoryTransitionError,
    DuplicateEventConflictError,
    InvalidStateEventError
)
from app.project.bible import (
    StoryBible,
    ValidationReport,
    StoryBibleError,
    UnsupportedSchemaVersionError,
    VersionConflictError,
    EntityNotFoundError,
    MalformedBibleError,
    CanonMutationError,
    load_bible,
    validate_bible,
    save_bible,
    get_canon_snapshot,
    get_character_spec,
    get_location_spec,
    get_prop_spec,
    append_state_event,
    resolve_state,
    validate_state_transition,
    propose_canon_mutation,
    apply_canon_mutation,
    get_continuity_context,
    create_canonical_nour_bible
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# --- Fixtures ---

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
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
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
        created_at=now_iso,
        updated_at=now_iso,
        status="validated",
        style=sample_style,
        characters={"hero": sample_character},
        locations={"citadel_gate": loc},
        props={"magic_amulet": prop}
    )


# --- Test Suite 1: Schema and Canon Integrity ---

def test_valid_bible_loads_and_validates(tmp_path, sample_bible):
    """Proves that a valid Story Bible saves, loads, and passes validation."""
    bible_file = save_bible(sample_bible, target_path=tmp_path)
    assert bible_file.exists()

    loaded = load_bible(tmp_path)
    assert loaded.project_id == "test_project"
    assert loaded.bible_version == 1
    assert "hero" in loaded.characters

    report = validate_bible(loaded)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_invalid_or_missing_required_data_rejected():
    """Proves that missing required fields fail Pydantic validation."""
    with pytest.raises(Exception):
        # Missing required 'project_id' and 'style'
        StoryBible(schema_version="1.0.0")

    with pytest.raises(Exception):
        # Missing required attributes in character
        CharacterDefinition(character_id="bad_char", name="Bad")


def test_unsupported_schema_versions_fail_explicitly(tmp_path, sample_bible):
    """Proves that unsupported schema versions fail explicitly with actionable message."""
    bible_file = save_bible(sample_bible, target_path=tmp_path)

    # Corrupt schema version in saved file
    with open(bible_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["schema_version"] = "2.5.0-alpha"
    with open(bible_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(UnsupportedSchemaVersionError) as exc_info:
        load_bible(tmp_path)
    assert "Unsupported Story Bible schema version '2.5.0-alpha'" in str(exc_info.value)


def test_character_ids_stable_and_unambiguous():
    """Proves that character IDs must be normalized lowercase and reject invalid characters."""
    c = CharacterDefinition(
        character_id="Nour_01",
        name="Nour",
        attributes=[AttributeCheck(id="hair", text="black hair")]
    )
    assert c.character_id == "nour_01"

    with pytest.raises(ValueError):
        CharacterDefinition(
            character_id="invalid id with spaces!",
            name="Bad",
            attributes=[AttributeCheck(id="hair", text="black hair")]
        )


def test_required_character_attributes_preserved(sample_character):
    """Proves that CharacterDefinition cleanly converts to CharacterSpec preserving required flags."""
    spec = sample_character.to_character_spec()
    assert isinstance(spec, CharacterSpec)
    assert spec.id == "hero"
    assert len(spec.attributes) == 2
    assert spec.attributes[0].id == "hair"
    assert spec.attributes[0].required is True
    assert spec.tolerances.min_face_px_for_check == 80


def test_canonical_snapshot_hashes_are_reproducible(sample_bible):
    """Proves that canonical snapshot hashes are deterministic and tamper-evident."""
    snap1 = sample_bible.get_canon_snapshot()
    snap2 = sample_bible.get_canon_snapshot()
    assert snap1.canon_hash == snap2.canon_hash
    assert len(snap1.canon_hash) == 64  # SHA-256

    # Mutate a character attribute and verify hash changes
    mutated_char = sample_bible.characters["hero"].model_copy(deep=True)
    mutated_char.attributes.append(AttributeCheck(id="scar", text="scar on cheek", required=False))
    bible_mutated = sample_bible.model_copy(update={"characters": {"hero": mutated_char}})
    snap_mutated = bible_mutated.get_canon_snapshot()
    assert snap_mutated.canon_hash != snap1.canon_hash


def test_regular_state_event_cannot_mutate_canonical_identity(tmp_path, sample_bible):
    """Proves that appending a story state event never modifies canonical definition on disk."""
    save_bible(sample_bible, target_path=tmp_path)

    # Narrative event: Hero's cloak is torn
    event = StoryStateEvent(
        event_id="evt_001",
        sequence_number=1,
        scene_id="scene_01",
        panel_id="scene_01_p1",
        entity_type="character",
        entity_id="hero",
        property_path="clothing.cloak_state",
        previous_value=None,
        new_value="severely torn at edges",
        timestamp="2026-10-29T00:00:00Z"
    )
    append_state_event(tmp_path, event)

    # Reload canon: canonical hero clothing_attributes must be completely unchanged
    reloaded_bible = load_bible(tmp_path)
    assert reloaded_bible.characters["hero"].clothing_attributes == ["red cloak"]
    assert reloaded_bible.bible_version == 1

    # But state timeline resolved state reflects the torn cloak
    res = resolve_state(tmp_path, "scene_01_p1")
    assert res.effective_state["character:hero"]["clothing"]["cloak_state"] == "severely torn at edges"


def test_canon_mutation_requires_approved_operation(tmp_path, sample_bible):
    """Proves that canon mutation proposals do not take effect without explicit approval."""
    save_bible(sample_bible, target_path=tmp_path)

    proposal = CanonMutationProposal(
        proposal_id="prop_001",
        project_id="test_project",
        target_type="character",
        target_id="hero",
        change_description="Hero permanently loses red cloak after volcano escape",
        proposed_changes={"clothing_attributes": ["burned tunic"]},
        created_at="2026-10-29T00:00:00Z"
    )
    propose_canon_mutation(tmp_path, proposal)

    # Canon is NOT mutated yet
    bible_mid = load_bible(tmp_path)
    assert bible_mid.characters["hero"].clothing_attributes == ["red cloak"]
    assert bible_mid.bible_version == 1

    # Explicit approval operation
    updated_bible = apply_canon_mutation(tmp_path, "prop_001", approved_by="lead_director")
    assert updated_bible.bible_version == 2
    assert updated_bible.characters["hero"].canon_version == 2
    assert updated_bible.characters["hero"].clothing_attributes == ["burned tunic"]


# --- Test Suite 2: State Timeline and Resolution ---

def test_state_resolves_correctly_at_different_panels(tmp_path, sample_bible):
    """Proves that narrative state resolves deterministically across panels."""
    save_bible(sample_bible, target_path=tmp_path)

    events = [
        StoryStateEvent(
            event_id="e1", sequence_number=1, scene_id="s1", panel_id="p1",
            entity_type="character", entity_id="hero",
            property_path="held_item", new_value="torch",
            timestamp="2026-10-29T00:01:00Z"
        ),
        StoryStateEvent(
            event_id="e2", sequence_number=2, scene_id="s1", panel_id="p2",
            entity_type="character", entity_id="hero",
            property_path="held_item", previous_value="torch", new_value="sword",
            timestamp="2026-10-29T00:02:00Z"
        ),
        StoryStateEvent(
            event_id="e3", sequence_number=3, scene_id="s2", panel_id="p3",
            entity_type="world", entity_id="world",
            property_path="weather", new_value="heavy_rain",
            timestamp="2026-10-29T00:03:00Z"
        ),
    ]
    for ev in events:
        append_state_event(tmp_path, ev)

    # State at panel 1: torch held
    res_p1 = resolve_state(tmp_path, "p1")
    assert res_p1.effective_state["character:hero"]["held_item"] == "torch"
    assert "world:world" not in res_p1.effective_state
    assert len(res_p1.contributing_events) == 1

    # State at panel 2: torch replaced by sword
    res_p2 = resolve_state(tmp_path, "p2")
    assert res_p2.effective_state["character:hero"]["held_item"] == "sword"
    assert "world:world" not in res_p2.effective_state
    assert len(res_p2.contributing_events) == 2

    # State at scene 2 / panel 3: sword held AND heavy_rain
    res_p3 = resolve_state(tmp_path, "p3")
    assert res_p3.effective_state["character:hero"]["held_item"] == "sword"
    assert res_p3.effective_state["world:world"]["weather"] == "heavy_rain"
    assert len(res_p3.contributing_events) == 3


def test_event_order_is_deterministic():
    """Proves that out-of-order event inputs resolve identically based on monotonic sequence number."""
    e1 = StoryStateEvent(
        event_id="e1", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="pos", new_value="standing",
        timestamp="2026-10-29T00:01:00Z"
    )
    e2 = StoryStateEvent(
        event_id="e2", sequence_number=2, scene_id="s1", panel_id="p2",
        entity_type="character", entity_id="hero", property_path="pos", previous_value="standing", new_value="running",
        timestamp="2026-10-29T00:02:00Z"
    )

    # Feed shuffled [e2, e1]
    res = resolve_timeline_state([e2, e1], target_scene_or_panel=None)
    assert res.effective_state["character:hero"]["pos"] == "running"
    assert res.contributing_events[0]["event_id"] == "e1"
    assert res.contributing_events[1]["event_id"] == "e2"


def test_historical_events_are_preserved(tmp_path, sample_bible):
    """Proves that resolving state at an earlier panel never alters or truncates historical events."""
    save_bible(sample_bible, target_path=tmp_path)
    for i in range(1, 5):
        append_state_event(tmp_path, StoryStateEvent(
            event_id=f"evt_{i}", sequence_number=i, scene_id="s1", panel_id=f"p{i}",
            entity_type="character", entity_id="hero", property_path="step", new_value=i,
            timestamp=f"2026-10-29T00:0{i}:00Z"
        ))

    state_file = tmp_path / "state.jsonl"
    with open(state_file, "r", encoding="utf-8") as f:
        lines_before = f.readlines()
    assert len(lines_before) == 4

    # Resolve at p2
    res = resolve_state(tmp_path, "p2")
    assert res.effective_state["character:hero"]["step"] == 2

    # Check file again: all 4 lines still exist
    with open(state_file, "r", encoding="utf-8") as f:
        lines_after = f.readlines()
    assert len(lines_after) == 4
    assert lines_before == lines_after


def test_duplicate_and_invalid_events(tmp_path, sample_bible):
    """Proves idempotency for identical events and rejection for conflicting duplicate events."""
    save_bible(sample_bible, target_path=tmp_path)
    e1 = StoryStateEvent(
        event_id="dup_01", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="mood", new_value="alert",
        timestamp="2026-10-29T00:01:00Z"
    )
    append_state_event(tmp_path, e1)

    # Identical payload duplicate: skipped cleanly
    res_identical = resolve_timeline_state([e1, e1], strict_transitions=True)
    assert res_identical.effective_state["character:hero"]["mood"] == "alert"

    # Conflicting duplicate: same event_id, different value -> raises error
    e1_conflict = StoryStateEvent(
        event_id="dup_01", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="mood", new_value="confused",
        timestamp="2026-10-29T00:01:00Z"
    )
    with pytest.raises(DuplicateEventConflictError):
        resolve_timeline_state([e1, e1_conflict], strict_transitions=True)


def test_undeclared_entities_fail_validation(tmp_path, sample_bible):
    """Proves that state events for entities not declared in Bible fail validation."""
    save_bible(sample_bible, target_path=tmp_path)
    ghost_event = StoryStateEvent(
        event_id="ghost_01", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="phantom_stranger", property_path="pos", new_value="in_shadows",
        timestamp="2026-10-29T00:01:00Z"
    )
    with pytest.raises(UndeclaredEntityError):
        append_state_event(tmp_path, ghost_event)


def test_contradictory_states_handled(tmp_path, sample_bible):
    """Proves that state transitions asserting false previous_values fail with ContradictoryTransitionError."""
    save_bible(sample_bible, target_path=tmp_path)
    e1 = StoryStateEvent(
        event_id="e1", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="cloak", new_value="clean",
        timestamp="2026-10-29T00:01:00Z"
    )
    append_state_event(tmp_path, e1)

    e2_bad = StoryStateEvent(
        event_id="e2", sequence_number=2, scene_id="s1", panel_id="p2",
        entity_type="character", entity_id="hero", property_path="cloak",
        previous_value="torn",  # False! previous was "clean"
        new_value="mended",
        timestamp="2026-10-29T00:02:00Z"
    )
    with pytest.raises(ContradictoryTransitionError):
        append_state_event(tmp_path, e2_bad)


def test_state_resolution_does_not_modify_source_files(tmp_path, sample_bible):
    """Proves that read operations are strictly side-effect free."""
    save_bible(sample_bible, target_path=tmp_path)
    ev = StoryStateEvent(
        event_id="e1", sequence_number=1, scene_id="s1", panel_id="p1",
        entity_type="character", entity_id="hero", property_path="hp", new_value=100,
        timestamp="2026-10-29T00:01:00Z"
    )
    append_state_event(tmp_path, ev)

    bible_path = tmp_path / "bible.json"
    state_path = tmp_path / "state.jsonl"
    bible_hash_before = compute_file_sha256(bible_path)
    state_hash_before = compute_file_sha256(state_path)

    # Run resolution multiple times
    for _ in range(5):
        resolve_state(tmp_path, "p1")
        get_character_spec(tmp_path, "hero")
        get_canon_snapshot(tmp_path)

    assert compute_file_sha256(bible_path) == bible_hash_before
    assert compute_file_sha256(state_path) == state_hash_before


# --- Test Suite 3: Asset Integrity and Path Traversal ---

def test_existing_valid_reference_assets_accepted():
    """Proves that the real M0 Nour reference image is accepted and hash-verified."""
    nour_ref = Path("runs/m0_visual/reference/nour_reference.png")
    assert (PROJECT_ROOT / nour_ref).is_file()

    actual_hash = compute_file_sha256(PROJECT_ROOT / nour_ref)
    ref = AssetRef(
        asset_id="nour_anchor",
        path=str(nour_ref).replace("\\", "/"),
        asset_type="character_sheet",
        expected_hash=actual_hash,
        mime_type="image/png"
    )
    resolved = validate_asset_ref(ref, project_root=PROJECT_ROOT)
    assert resolved.is_file()


def test_missing_assets_fail_with_actionable_error():
    """Proves that non-existent assets fail with AssetNotFoundError."""
    ref = AssetRef(
        asset_id="ghost_asset",
        path="assets/does_not_exist.png",
        asset_type="generic_image",
        expected_hash="a" * 64,
        mime_type="image/png"
    )
    with pytest.raises(AssetNotFoundError) as exc_info:
        validate_asset_ref(ref, project_root=PROJECT_ROOT)
    assert "ghost_asset" in str(exc_info.value)


def test_hash_mismatch_detected(tmp_path):
    """Proves that a tampered or replaced asset triggers AssetHashMismatchError."""
    fake_img = tmp_path / "img.png"
    fake_img.write_bytes(b"PNG_CORRUPTED_BYTES")

    ref = AssetRef(
        asset_id="tampered_asset",
        path="img.png",
        asset_type="generic_image",
        expected_hash="0" * 64,  # Incorrect hash
        mime_type="image/png"
    )
    with pytest.raises(AssetHashMismatchError):
        validate_asset_ref(ref, project_root=tmp_path)


def test_path_traversal_outside_allowed_root_rejected(tmp_path):
    """Proves that directory traversal attempts (e.g. ../../etc/passwd) are blocked."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.png"
    secret_file.write_bytes(b"SECRET")

    project_dir = tmp_path / "project_root"
    project_dir.mkdir()

    ref = AssetRef(
        asset_id="traversal_attack",
        path="../outside/secret.png",
        asset_type="generic_image",
        expected_hash=compute_file_sha256(secret_file),
        mime_type="image/png"
    )
    with pytest.raises(PathTraversalError):
        validate_asset_ref(ref, project_root=project_dir)


def test_invalid_mime_and_extension_rejected(tmp_path):
    """Proves that executable or unsupported file types are rejected as assets."""
    script_file = tmp_path / "hack.sh"
    script_file.write_bytes(b"echo 'pwned'")

    ref = AssetRef(
        asset_id="malicious_script",
        path="hack.sh",
        asset_type="generic_image",
        expected_hash=compute_file_sha256(script_file),
        mime_type="text/x-shellscript"
    )
    with pytest.raises(InvalidAssetTypeError):
        validate_asset_ref(ref, project_root=tmp_path)


# --- Test Suite 4: Persistence, Versioning, and Hygiene ---

def test_load_save_roundtrip_preserves_semantics(tmp_path, sample_bible):
    """Proves that a Story Bible round-trips to disk and back with 100% semantic fidelity."""
    file_path = save_bible(sample_bible, target_path=tmp_path)
    loaded = load_bible(file_path)

    d_orig = sample_bible.model_dump(mode="json")
    d_loaded = loaded.model_dump(mode="json")

    # updated_at may be refreshed on save
    d_loaded["updated_at"] = d_orig["updated_at"]
    assert d_orig == d_loaded


def test_optimistic_concurrency_version_check(tmp_path, sample_bible):
    """Proves that save_bible with expected_version protects against race conditions."""
    save_bible(sample_bible, target_path=tmp_path)

    # First update succeeds with matching version
    sample_bible.bible_version = 2
    save_bible(sample_bible, target_path=tmp_path, expected_version=1)

    # Attempting to save expecting version 1 now fails
    with pytest.raises(VersionConflictError):
        save_bible(sample_bible, target_path=tmp_path, expected_version=1)


def test_asset_bytes_not_serialized_into_bible_json(tmp_path, sample_bible):
    """Proves that image bytes and base64 payloads never leak into Story Bible JSON."""
    file_path = save_bible(sample_bible, target_path=tmp_path)
    content = file_path.read_text(encoding="utf-8")

    assert "data:image" not in content
    assert ";base64," not in content
    # Bible JSON should remain compact metadata (< 20 KB)
    assert len(content.encode("utf-8")) < 20480


# --- Test Suite 5: Integration with M0 Nour Reference and Continuity Context ---

def test_canonical_nour_bible_integration(tmp_path):
    """
    Proves that the verified M0 Nour character reference and checklist are preserved,
    hash-verified, and successfully exported into CharacterSpec.
    """
    nour_bible = create_canonical_nour_bible(project_root=PROJECT_ROOT)
    assert nour_bible.project_id == "inkloop_m0_nour"
    assert "nour" in nour_bible.characters

    nour_char = nour_bible.get_character("nour")
    assert len(nour_char.attributes) == 4
    assert nour_char.attributes[0].id == "hair"
    assert nour_char.attributes[1].id == "glasses"
    assert nour_char.attributes[2].id == "jacket"

    # Verify that asset references resolve against PROJECT_ROOT
    rep = validate_bible(nour_bible, project_root=PROJECT_ROOT, verify_asset_hashes=True)
    assert rep.is_valid is True
    assert rep.validated_assets_count == 2  # Style ref and character ref

    # Save to disk and query spec
    save_bible(nour_bible, target_path=tmp_path)
    spec = get_character_spec(tmp_path, "nour")
    assert spec.id == "nour"
    assert len(spec.attributes) == 4


def test_continuity_context_assembly(tmp_path):
    """
    Proves that the Story Bible supplies canonical style, character references,
    and current state to the Continuity Packet builder.
    """
    nour_bible = create_canonical_nour_bible(project_root=PROJECT_ROOT)
    save_bible(nour_bible, target_path=tmp_path)

    # Narrative event: Nour in Scene 2 is holding an umbrella
    event = StoryStateEvent(
        event_id="nour_umbrella_evt",
        sequence_number=1,
        scene_id="scene_02",
        panel_id="scene_02_p1",
        entity_type="character",
        entity_id="nour",
        property_path="held_object",
        new_value="transparent rain umbrella",
        timestamp="2026-10-29T01:00:00Z"
    )
    append_state_event(tmp_path, event)

    context = get_continuity_context(
        project_id_or_path=tmp_path,
        scene_id_or_panel_id="scene_02_p1",
        active_character_ids=["nour"]
    )
    assert context["project_id"] == "inkloop_m0_nour"
    assert "manga_ink_screentone" in context["style"]["style_id"]
    assert "nour" in context["active_characters"]
    nour_ctx = context["active_characters"]["nour"]
    assert nour_ctx["current_state"]["held_object"] == "transparent rain umbrella"
    assert "no color" in context["negative_constraints"]
