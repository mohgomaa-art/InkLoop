"""
Comprehensive test suite for InkLoop AI Creative Director & Universe Builder.
Verifies the 16-stage creative pipeline, fact classification, Story Bible synthesis,
character profile invariants, cross-document coherence validation,
downstream contract compilation, prompt synthesis, and REST API endpoints.
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.api.server import app
from app.creative.schemas import (
    CreativeMode,
    FactCategory,
    FindingSeverity,
    CreativePackage,
    MagicOrTechAbilityRule,
)
from app.creative.service import CreativeDirectorService
from app.creative.validator import CreativeCoherenceValidator
from app.creative.prompt_compiler import CreativePromptCompiler
from app.project.bible import (
    load_bible,
    save_bible,
    create_canonical_nour_bible,
    StoryBible,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clean_creative_service(tmp_path, monkeypatch):
    test_packages_dir = tmp_path / "creative_packages"
    test_packages_dir.mkdir(parents=True, exist_ok=True)
    svc = CreativeDirectorService(packages_dir=test_packages_dir)
    monkeypatch.setattr(CreativeDirectorService, "_instance", svc)
    return svc


def test_brief_parsing_and_fact_classification(clean_creative_service):
    """Verifies that user brief statements are accurately classified into facts, proposals, and unknowns."""
    prompt = (
        "I want to create a dark fantasy manhwa titled 'Echo Tides' about a quiet courier named Nour "
        "who has short messy black hair with a white streak on the left. Nour can hear memories trapped inside broken objects. "
        "The story takes place in a flooded city."
    )
    brief = clean_creative_service._parse_brief(
        project_id="test_parse",
        user_prompt=prompt,
        mode=CreativeMode.FULL_PRODUCTION_BIBLE,
        visual_references=None,
    )

    assert brief.title == "Echo Tides"
    assert "dark fantasy" in brief.primary_genre.lower()
    assert brief.target_medium in ("manhwa", "webtoon")

    # Verify classification of explicit user facts
    user_facts = [f for f in brief.explicit_user_facts]
    assert len(user_facts) > 0
    fact_texts = [f.fact_statement.lower() for f in user_facts]
    assert any("white streak" in t or "black hair" in t for t in fact_texts)

    # Verify proposals were generated
    assert len(brief.agent_proposals) > 0

    # Verify unknowns were identified
    assert len(brief.open_questions_and_unknowns) > 0


def test_develop_universe_full_pipeline(clean_creative_service, tmp_path, monkeypatch):
    """Executes the full 16-stage creative pipeline in offline mode and verifies all deliverables."""
    project_id = "test_universe_proj"
    # Seed a project bible
    p_dir = tmp_path / "runs" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    bible = create_canonical_nour_bible(tmp_path)
    bible.project_id = project_id
    save_bible(bible, p_dir / "bible.json")

    # Mock the bible loader in service to point to our test directory
    monkeypatch.setattr(
        clean_creative_service,
        "_load_existing_bible",
        lambda pid: bible if pid == project_id else None,
    )

    prompt = (
        "Dark fantasy manhwa set in a flooded coastal metropolis. "
        "Nour is an 18-year-old courier with messy black hair and a white streak on the left, wearing round wireframe glasses. "
        "Nour can hear memories trapped in broken relics, but each memory causes acute migraine and temporary disorientation. "
        "Rival character Kaelen runs a salvage guild and distrusts Nour."
    )

    package = clean_creative_service.develop_universe(
        project_id=project_id,
        user_prompt=prompt,
        mode=CreativeMode.FULL_PRODUCTION_BIBLE,
        offline_mode=True,
    )

    assert isinstance(package, CreativePackage)
    assert package.project_id == project_id
    assert package.package_hash != ""

    # 1. Story Bible
    sb = package.story_bible
    assert sb.logline != ""
    assert sb.theme != ""
    assert "fantasy" in sb.genre.lower() or "dark" in sb.tone.lower()

    # 2. Characters
    assert len(package.characters) >= 1
    assert "nour" in package.characters
    nour = package.characters["nour"]
    assert nour.name == "Nour"
    assert len(nour.visual_invariants) >= 2
    assert any("streak" in inv.lower() and "white" in inv.lower() for inv in nour.visual_invariants)
    assert len(nour.flaws) >= 1
    assert len(nour.forbidden_visual_drift) >= 1
    assert nour.base_outfit is not None

    # 3. Relationships
    assert len(package.relationship_graph.characters) >= 1
    assert "nour" in package.relationship_graph.characters

    # 4. World Bible & Supernatural Rules (must have cost & limit)
    wb = package.world_bible
    assert len(wb.locations) >= 1
    assert len(wb.magic_or_tech_rules) >= 1
    for rule in wb.magic_or_tech_rules:
        assert rule.cost_or_strain != "", "Supernatural ability must have cost/strain"
        assert rule.absolute_limit != "", "Supernatural ability must have absolute limit"

    # 5. Narrative Structure (3 Acts + Scene Candidates)
    ns = package.narrative_structure
    assert len(ns.act_breakdown) == 3
    assert len(ns.chapter_outlines) >= 3
    for ch in ns.chapter_outlines:
        assert len(ch.scene_candidates) >= 1
        assert ch.emotional_turning_point != ""

    # 6. Visual Style Profile
    vp = package.style_profile
    assert vp.medium != ""
    assert len(vp.line_art_rules) > 0
    assert len(vp.negative_constraints) > 0

    # 7. Character Sheet Plan
    assert "nour" in package.character_sheet_plans
    sheet = package.character_sheet_plans["nour"]
    assert len(sheet.required_views) >= 3

    # 8. Downstream Contracts
    contracts = package.contracts
    assert contracts.canon.project_id == project_id
    assert "nour" in contracts.characters
    assert len(contracts.characters["nour"].mandatory_invariants) >= 2
    assert len(contracts.style.negative_prompt_additions) > 0

    # 9. Persistence check
    reloaded = clean_creative_service.get_package(project_id)
    assert reloaded is not None
    assert reloaded.package_hash == package.package_hash
    assert reloaded.story_bible.title == package.story_bible.title


def test_coherence_validator_catches_unbounded_power_and_orphaned_edges(clean_creative_service):
    """Ensures validator catches logic violations such as abilities without costs or invalid edges."""
    package = clean_creative_service.develop_universe(
        project_id="test_val_proj",
        user_prompt="Quick story about courier Nour with messy hair.",
        mode=CreativeMode.QUICK_CONCEPT,
        offline_mode=True,
    )

    validator = CreativeCoherenceValidator()
    # Initial validation should pass
    res1 = validator.validate(package)
    assert res1.is_coherent is True

    # Artificially inject an unbounded supernatural ability
    unbounded_rule = MagicOrTechAbilityRule(
        ability_id="god_mode",
        name="Omnipotent Telepathy",
        practitioners=["nour"],
        mechanism="Instant thought reading",
        cost_or_strain="",  # VIOLATION: Empty cost
        absolute_limit="",  # VIOLATION: Empty limit
        narrative_consequence="Wins every fight effortlessly",
    )
    package.world_bible.magic_or_tech_rules.append(unbounded_rule)

    res2 = validator.validate(package)
    rule_findings = [
        f for f in res2.findings
        if f.entity_id == "god_mode" and f.severity == FindingSeverity.ERROR
    ]
    assert len(rule_findings) > 0
    assert any("cost" in f.message.lower() for f in rule_findings)


def test_active_canon_conflict_detection(clean_creative_service, tmp_path, monkeypatch):
    """Verifies that proposed contradictions to an approved Story Bible are flagged as canon conflicts."""
    project_id = "test_canon_conflict"
    p_dir = tmp_path / "runs" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    bible = create_canonical_nour_bible(tmp_path)
    bible.project_id = project_id
    save_bible(bible, p_dir / "bible.json")

    monkeypatch.setattr(
        clean_creative_service,
        "_load_existing_bible",
        lambda pid: bible if pid == project_id else None,
    )

    package = clean_creative_service.develop_universe(
        project_id=project_id,
        user_prompt="Nour now has bright blonde hair and never wears glasses.",
        mode=CreativeMode.QUICK_CONCEPT,
        offline_mode=True,
    )

    validator = CreativeCoherenceValidator()
    res = validator.validate(package, active_bible=bible)

    conflict_findings = [f for f in res.findings if "Canon Conflict" in f.title]
    assert len(conflict_findings) > 0
    assert any("hair" in f.message.lower() for f in conflict_findings)


def test_approve_canon_mutation_updates_story_bible(clean_creative_service, tmp_path, monkeypatch):
    """Verifies that human approval commits proposals to StoryBible and updates canon hash."""
    from app.project import bible as bible_module

    project_id = "test_approve_proj"
    p_dir = tmp_path / "runs" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    bible = create_canonical_nour_bible(tmp_path)
    bible.project_id = project_id
    initial_version = bible.bible_version
    initial_hash = bible.canon_hash
    bible_file = p_dir / "bible.json"
    save_bible(bible, bible_file)

    # Monkeypatch load/save bible to use our test directory
    monkeypatch.setattr(clean_creative_service, "_load_existing_bible", lambda pid: load_bible(bible_file))
    monkeypatch.setattr(bible_module, "save_project_bible", lambda b: save_bible(b, bible_file))

    package = clean_creative_service.develop_universe(
        project_id=project_id,
        user_prompt="Create a sci-fi cyberpunk manhwa with courier Nour holding a pulse dagger.",
        mode=CreativeMode.QUICK_CONCEPT,
        offline_mode=True,
    )

    # Approve canon mutation
    updated_bible = clean_creative_service.approve_canon_mutation(
        project_id=project_id,
        character_ids_to_commit=["nour"],
        commit_style=True,
    )

    assert updated_bible.bible_version == initial_version + 1
    assert updated_bible.canon_hash != initial_hash
    assert "nour" in updated_bible.characters

    # Verify package pending status was cleared
    reloaded_pkg = clean_creative_service.get_package(project_id)
    assert reloaded_pkg.has_pending_approval is False


def test_prompt_compiler_with_contracts(clean_creative_service):
    """Verifies that CreativePromptCompiler generates deterministic, constraint-enforcing panel prompts."""
    package = clean_creative_service.develop_universe(
        project_id="test_compiler_proj",
        user_prompt="Courier Nour running across flooded rooftops in rain at midnight.",
        mode=CreativeMode.QUICK_CONCEPT,
        offline_mode=True,
    )

    nour = package.characters["nour"]
    pos_prompt = CreativePromptCompiler.compile_panel_prompt(
        contracts=package.contracts,
        character=nour,
        scene_description="Nour leaping over broken stone balustrade into neon reflection",
        emotion="determined",
        is_action_shot=True,
    )

    # Check key components
    assert "Nour" in pos_prompt
    assert "white" in pos_prompt.lower() and "streak" in pos_prompt.lower()
    assert "leaping over broken stone" in pos_prompt
    assert "determined" in pos_prompt
    assert "dynamic" in pos_prompt.lower() or "action" in pos_prompt.lower()

    neg_prompt = CreativePromptCompiler.compile_negative_prompt(
        contracts=package.contracts,
        character=nour,
    )
    assert len(neg_prompt) > 0
    # Negative prompt must contain visual drift prohibitions
    assert any(drift in neg_prompt for drift in nour.forbidden_visual_drift)


def test_creative_api_endpoints(client, clean_creative_service, tmp_path, monkeypatch):
    """Tests the full REST API lifecycle for the Creative Director."""
    from app.project import bible as bible_module

    project_id = "api_universe_test"
    p_dir = tmp_path / "runs" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    bible = create_canonical_nour_bible(tmp_path)
    bible.project_id = project_id
    bible_file = p_dir / "bible.json"
    save_bible(bible, bible_file)

    monkeypatch.setattr(clean_creative_service, "_load_existing_bible", lambda pid: load_bible(bible_file))
    monkeypatch.setattr(bible_module, "save_project_bible", lambda b: save_bible(b, bible_file))

    # 1. POST /api/v1/creative/develop
    dev_res = client.post(
        "/api/v1/creative/develop",
        json={
            "project_id": project_id,
            "user_prompt": "Dark fantasy manhwa about courier Nour in flooded city with relic powers.",
            "mode": "full_production_bible",
            "offline_mode": True,
        },
    )
    assert dev_res.status_code == 200
    pkg_data = dev_res.json()
    assert pkg_data["project_id"] == project_id
    assert "nour" in pkg_data["characters"]

    # 2. GET /api/v1/creative/package/{project_id}
    get_res = client.get(f"/api/v1/creative/package/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["project_id"] == project_id

    # 3. POST /api/v1/creative/validate/{project_id}
    val_res = client.post(f"/api/v1/creative/validate/{project_id}")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "is_coherent" in val_data
    assert "findings" in val_data

    # 4. GET /api/v1/creative/contracts/{project_id}
    contracts_res = client.get(f"/api/v1/creative/contracts/{project_id}")
    assert contracts_res.status_code == 200
    contracts_data = contracts_res.json()
    assert "canon_contract" in contracts_data or "canon" in contracts_data
    chars = contracts_data.get("character_contracts", contracts_data.get("characters", {}))
    assert "nour" in chars

    # 5. POST /api/v1/creative/compile-prompt
    compile_res = client.post(
        "/api/v1/creative/compile-prompt",
        json={
            "project_id": project_id,
            "character_id": "nour",
            "scene_description": "Nour inspecting an ancient cracked pocket watch underwater",
            "emotion": "focused",
            "is_action_shot": False,
        },
    )
    assert compile_res.status_code == 200
    compile_data = compile_res.json()
    assert "positive_prompt" in compile_data
    assert "negative_prompt" in compile_data
    assert "Nour" in compile_data["positive_prompt"]

    # 6. POST /api/v1/creative/approve
    appr_res = client.post(
        "/api/v1/creative/approve",
        json={
            "project_id": project_id,
            "character_ids_to_commit": ["nour"],
            "commit_style": True,
        },
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["success"] is True
    assert appr_data["bible_version"] >= 2
    assert "canon_hash" in appr_data


def test_creative_frontend_modes_and_graceful_package_retrieval(client):
    """Verifies that non-existent packages return 200 with null and all frontend modes succeed."""
    # 1. Non-existent package returns 200 null (avoiding console 404 noise)
    get_res = client.get("/api/v1/creative/package/uninitialized_project_xyz")
    assert get_res.status_code == 200
    assert get_res.json() is None

    # 2. All 5 frontend modes succeed without 422
    for mode in [
        "quick_concept",
        "full_production_bible",
        "character_deep_dive",
        "ensemble_builder",
        "visual_worldbuilding",
    ]:
        dev_res = client.post(
            "/api/v1/creative/develop",
            json={
                "project_id": f"proj_mode_{mode}",
                "user_prompt": f"Testing creative pipeline in {mode} mode",
                "mode": mode,
                "offline_mode": True,
            },
        )
        assert dev_res.status_code == 200, f"Mode {mode} failed with {dev_res.status_code}: {dev_res.text}"
        assert dev_res.json()["project_id"] == f"proj_mode_{mode}"


def test_add_character_to_universe_and_commit_canon(clean_creative_service, tmp_path, monkeypatch):
    """Verifies that an individual character can be added and committed directly to the Story Bible canon."""
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.project.bible import load_bible

    client = TestClient(create_app())
    project_id = "test_add_char_proj"

    # 1. First develop a universe
    client.post(
        "/api/v1/creative/develop",
        json={
            "project_id": project_id,
            "user_prompt": "Courier Nour delivers memories across flooded rooftops in Vespera.",
            "mode": "quick_concept",
            "offline_mode": True,
        },
    )

    # 2. Add a new character directly via endpoint
    add_res = client.post(
        "/api/v1/creative/character/add",
        json={
            "project_id": project_id,
            "name": "Kaelen",
            "role": "Relic Diver & Scavenger",
            "age_range": "21",
            "narrative_function": "Assists in retrieving submerged memory orbs from the lower canal ruins.",
            "visual_invariants": ["Brass diver goggles on forehead", "Coral scar along left arm", "Braided sea-green hair"],
            "garments": ["Diver harness", "Canvas trousers", "Grip boots"],
            "commit_to_canon": True,
        },
    )
    assert add_res.status_code == 200, f"Failed: {add_res.text}"
    pkg = add_res.json()
    assert "kaelen" in pkg["characters"]
    assert pkg["characters"]["kaelen"]["name"] == "Kaelen"

    # 3. Verify Story Bible has Kaelen committed to canon
    bible = load_bible(project_id)
    assert "kaelen" in bible.characters
    assert bible.characters["kaelen"].name == "Kaelen"
    assert len(bible.characters["kaelen"].visual_invariants) == 3

