"""
Unit tests for InkLoop Identity and Entity Reference Contracts.
Verifies identifier formats, prefixes, validation, and collision resistance.
"""
import pytest
from pydantic import ValidationError
from app.contracts.identity import (
    IdPrefix,
    is_valid_id,
    generate_id,
    EntityRef,
    ProjectRef,
    StoryRef,
    SceneRef,
    PanelRef,
    CharacterRef,
    AssetRef,
    ArtifactRef,
)

def test_is_valid_id_true():
    assert is_valid_id("proj_inkloop_01") is True
    assert is_valid_id("char_nour") is True
    assert is_valid_id("panel_scene01_02") is True
    assert is_valid_id("art_01h8x9a2b") is True
    assert is_valid_id("proj_inkloop_01", expected_prefix=IdPrefix.PROJECT) is True

def test_is_valid_id_false():
    assert is_valid_id("") is False
    assert is_valid_id("PROJ_CAPS") is False
    assert is_valid_id("no_prefix") is True  # Matches generic slug pattern
    assert is_valid_id("no_prefix", expected_prefix=IdPrefix.PROJECT) is False
    assert is_valid_id("proj-hyphen-01") is False  # Must use underscores
    assert is_valid_id("proj_") is False

def test_generate_id_format():
    pid = generate_id(IdPrefix.PROJECT, slug="demo_hackathon")
    assert pid.startswith("proj_demo_hackathon_")
    assert is_valid_id(pid, expected_prefix=IdPrefix.PROJECT) is True

    aid = generate_id(IdPrefix.ARTIFACT)
    assert aid.startswith("art_")
    assert is_valid_id(aid, expected_prefix=IdPrefix.ARTIFACT) is True

def test_generate_id_collision_resistance():
    ids = {generate_id(IdPrefix.PANEL, slug="scene01") for _ in range(100)}
    assert len(ids) == 100

def test_entity_ref_valid():
    ref = EntityRef(id="char_nour_01", prefix=IdPrefix.CHARACTER, version="1.0.0")
    assert ref.id == "char_nour_01"
    assert ref.prefix == IdPrefix.CHARACTER
    assert ref.version == "1.0.0"

def test_entity_ref_invalid_id_raises():
    with pytest.raises(ValidationError):
        EntityRef(id="INVALID-ID!!", prefix=IdPrefix.CHARACTER)

def test_specialized_refs():
    s_ref = StoryRef(project_id="proj_01", story_id="story_autumn", story_version=2)
    assert s_ref.story_id == "story_autumn"

    p_ref = PanelRef(page_id="page_01", panel_id="panel_01_01", order_in_page=1, scene_id="scene_01")
    assert p_ref.order_in_page == 1
    assert p_ref.scene_id == "scene_01"

    c_ref = CharacterRef(character_id="char_nour", canonical_version=1)
    assert c_ref.character_id == "char_nour"

    a_ref = AssetRef(asset_id="asset_nour_ref", version=1, content_sha256="abc123def456")
    assert a_ref.content_sha256 == "abc123def456"
