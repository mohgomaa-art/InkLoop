"""
Story Bible & Canon Studio Full-Stack CRUD & Concurrency Integration Tests.

Validates:
1. Character CRUD (create, update, delete, minimum-count guard).
2. Location CRUD (create, update, delete).
3. Prop CRUD (create, update, delete).
4. Referential integrity guards (cannot delete character referenced by active prop).
5. Style Bible update with all canonical fields & deletion prohibition.
6. Mutation proposal audit trail (propose, list, reject, apply).
7. Optimistic concurrency conflict detection (409 on stale hash or version).
"""

import shutil
import pytest
from fastapi.testclient import TestClient
from app.api.server import app
from app.config import PROJECT_ROOT

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_project(client):
    """Creates a fresh isolated project for each test to prevent mutation cross-contamination."""
    res = client.post("/api/v1/projects", json={"title": "Test Canon Studio Project"})
    assert res.status_code == 201
    data = res.json()
    project_id = data["project_id"]
    try:
        yield project_id
    finally:
        p_dir = PROJECT_ROOT / "runs" / project_id
        if p_dir.exists():
            shutil.rmtree(p_dir, ignore_errors=True)

def test_character_crud_and_invariants(client, test_project):
    project_id = test_project

    # 1. Fetch initial bible
    res = client.get(f"/api/v1/projects/{project_id}/bible")
    assert res.status_code == 200
    bible = res.json()
    assert "nour" in bible["characters"]
    v0 = bible["bible_version"]
    h0 = bible["canon_hash"]

    # 2. Add character 'tariq' via mutation proposal
    add_req = {
        "target_type": "character",
        "target_id": "tariq",
        "change_description": "Introduce detective Tariq into canon",
        "proposed_changes": {
            "action": "add",
            "data": {
                "canonical_name": "Tariq",
                "role": "Lead Investigator",
                "visual_invariants": ["sharp jawline", "overcoat", "fedora"],
                "clothing_traits": ["trench coat", "dark tie"],
                "restrictions": ["never smiles in public"],
                "tolerances": {"color_drift": "low", "geometry_drift": "strict"},
                "attributes": [
                    {
                        "trait_name": "facial_scar",
                        "expected_value": "left cheek scar",
                        "validation_strategy": "embedding",
                        "remediation_hint": "Ensure scar on left cheek is visible",
                    }
                ],
            },
        },
    }
    res_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=add_req)
    assert res_prop.status_code == 200
    prop_data = res_prop.json()
    prop_id = prop_data["proposal_id"]

    # Apply mutation
    res_apply = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop_id},
    )
    assert res_apply.status_code == 200
    updated_bible = res_apply.json()["bible"]
    assert "tariq" in updated_bible["characters"]
    assert updated_bible["bible_version"] == v0 + 1
    assert updated_bible["canon_hash"] != h0

    # 3. Update character 'tariq'
    update_req = {
        "target_type": "character",
        "target_id": "tariq",
        "change_description": "Update Tariq clothing for winter arc",
        "proposed_changes": {
            "action": "update",
            "data": {
                "clothing_traits": ["heavy wool trench coat", "dark scarf"],
            },
        },
    }
    res_up_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=update_req)
    assert res_up_prop.status_code == 200
    res_up_apply = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": res_up_prop.json()["proposal_id"]},
    )
    assert res_up_apply.status_code == 200
    tariq = res_up_apply.json()["bible"]["characters"]["tariq"]
    assert "heavy wool trench coat" in tariq["clothing_attributes"]
    # Unchanged fields remain preserved
    assert tariq["name"] == "Tariq"
    assert "Lead Investigator" in tariq["description"]

    # 4. Safe deletion of 'tariq' (Nour still remains)
    del_req = {
        "target_type": "character",
        "target_id": "tariq",
        "change_description": "Remove Tariq from canon",
        "proposed_changes": {
            "action": "delete",
        },
    }
    res_del_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_req)
    assert res_del_prop.status_code == 200
    res_del_apply = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": res_del_prop.json()["proposal_id"]},
    )
    assert res_del_apply.status_code == 200
    assert "tariq" not in res_del_apply.json()["bible"]["characters"]
    assert "nour" in res_del_apply.json()["bible"]["characters"]

    # 5. Guard: Attempting to delete the last character ('nour') must be rejected
    del_nour_req = {
        "target_type": "character",
        "target_id": "nour",
        "change_description": "Attempt to delete only remaining character",
        "proposed_changes": {"action": "delete"},
    }
    res_del_nour = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_nour_req)
    assert res_del_nour.status_code == 400
    assert "at least one character" in res_del_nour.json()["detail"]["message"].lower()


def test_character_copier_direct_add_appears_in_story_bible_roster(client, test_project):
    """The one-action Character Copier payload must create a visible Canon roster entry."""
    project_id = test_project
    proposed = {
        "target_type": "character",
        "target_id": "sunny",
        "change_description": "Add Sunny from Character Copier to Story Bible Characters.",
        "proposed_changes": {
            "action": "add",
            "name": "Sunny",
            "entity_kind": "smiling circle creature",
            "morphology": "flat yellow circle with one smile and no limbs",
            "surface_description": "matte yellow",
            "description": "smiling circle creature; flat yellow circle with one smile and no limbs",
            "visual_invariants": ["Keep the form circular", "Keep one smile"],
            "restrictions": ["Do not add a body or limbs"],
            "tolerances": {"face_check_applicable": False},
            "attributes": [
                {"id": "sunny_shape", "text": "Keep the form circular", "required": True},
                {"id": "sunny_smile", "text": "Keep one smile", "required": True},
            ],
            "reference_assets": [],
            "approval_status": "approved",
        },
    }
    proposal_response = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=proposed)
    assert proposal_response.status_code == 200
    applied_response = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": proposal_response.json()["proposal_id"], "caller_authorized": True},
    )
    assert applied_response.status_code == 200
    sunny = applied_response.json()["bible"]["characters"]["sunny"]
    assert sunny["name"] == "Sunny"
    assert sunny["entity_kind"] == "smiling circle creature"
    assert sunny["morphology"] == "flat yellow circle with one smile and no limbs"
    assert sunny["tolerances"]["face_check_applicable"] is False

def test_location_crud_via_api(client, test_project):
    project_id = test_project

    # 1. Add location
    add_loc = {
        "target_type": "location",
        "target_id": "loc_old_cairo",
        "change_description": "Register Old Cairo alleyway location",
        "proposed_changes": {
            "action": "add",
            "data": {
                "location_id": "loc_old_cairo",
                "name": "Old Cairo Alleyway",
                "description": "Narrow stone alley flanked by wooden mashrabiya balconies.",
                "required_attributes": ["stone pavement", "mashrabiya balconies"],
                "permitted_variations": ["sunset", "midnight rain"],
                "state_relevant_properties": {"lighting": "amber lanterns"},
            },
        },
    }
    prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=add_loc)
    assert prop.status_code == 200
    apply_res = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop.json()["proposal_id"]},
    )
    assert apply_res.status_code == 200
    locations = apply_res.json()["bible"]["locations"]
    assert "loc_old_cairo" in locations
    assert locations["loc_old_cairo"]["name"] == "Old Cairo Alleyway"

    # 2. Update location
    up_loc = {
        "target_type": "location",
        "target_id": "loc_old_cairo",
        "change_description": "Update Old Cairo lighting notes",
        "proposed_changes": {
            "action": "update",
            "data": {
                "description": "Updated alleyway with dense shadows and morning mist.",
            },
        },
    }
    prop_up = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=up_loc)
    assert prop_up.status_code == 200
    apply_up = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop_up.json()["proposal_id"]},
    )
    assert apply_up.status_code == 200
    loc_updated = apply_up.json()["bible"]["locations"]["loc_old_cairo"]
    assert "morning mist" in loc_updated["description"]
    assert loc_updated["name"] == "Old Cairo Alleyway"

    # 3. Delete location
    del_loc = {
        "target_type": "location",
        "target_id": "loc_old_cairo",
        "change_description": "Remove Old Cairo alleyway",
        "proposed_changes": {"action": "delete"},
    }
    prop_del = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_loc)
    assert prop_del.status_code == 200
    apply_del = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop_del.json()["proposal_id"]},
    )
    assert apply_del.status_code == 200
    assert "loc_old_cairo" not in apply_del.json()["bible"]["locations"]

def test_prop_crud_and_referential_integrity(client, test_project):
    project_id = test_project

    # 1. Add a second character first so character deletion is legally possible
    add_char = {
        "target_type": "character",
        "target_id": "char_secondary",
        "change_description": "Add secondary character",
        "proposed_changes": {
            "action": "add",
            "data": {"canonical_name": "Secondary", "role": "Sidekick"},
        },
    }
    p_char = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=add_char)
    client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": p_char.json()["proposal_id"]},
    )

    # 2. Add prop associated with 'nour'
    add_prop = {
        "target_type": "prop",
        "target_id": "prop_cyber_deck",
        "change_description": "Register Nour's custom cyber deck",
        "proposed_changes": {
            "action": "add",
            "data": {
                "prop_id": "prop_cyber_deck",
                "name": "Nour's Cyber Deck",
                "description": "Portable terminal with holographic projection module.",
                "associated_character_ids": ["nour"],
                "required_attributes": ["holographic emitter", "brass casing"],
                "permitted_variations": ["active glow", "powered off"],
            },
        },
    }
    p_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=add_prop)
    assert p_prop.status_code == 200
    a_prop = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": p_prop.json()["proposal_id"]},
    )
    assert a_prop.status_code == 200
    assert "prop_cyber_deck" in a_prop.json()["bible"]["props"]

    # 3. Referential integrity: Attempting to delete character 'nour' must fail
    # because 'prop_cyber_deck' explicitly references 'nour'
    del_nour = {
        "target_type": "character",
        "target_id": "nour",
        "change_description": "Attempt to delete Nour while prop references her",
        "proposed_changes": {"action": "delete"},
    }
    del_res = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_nour)
    assert del_res.status_code == 400
    detail = del_res.json()["detail"]["message"]
    assert "referenced by prop" in detail and "prop_cyber_deck" in detail

    # 4. Update prop
    up_prop = {
        "target_type": "prop",
        "target_id": "prop_cyber_deck",
        "change_description": "Disassociate prop from Nour",
        "proposed_changes": {
            "action": "update",
            "data": {"associated_character_ids": []},
        },
    }
    p_up_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=up_prop)
    a_up_prop = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": p_up_prop.json()["proposal_id"]},
    )
    assert a_up_prop.status_code == 200
    assert a_up_prop.json()["bible"]["props"]["prop_cyber_deck"]["associated_character_ids"] == []

    # 5. Delete prop
    del_prop = {
        "target_type": "prop",
        "target_id": "prop_cyber_deck",
        "change_description": "Delete cyber deck",
        "proposed_changes": {"action": "delete"},
    }
    p_del_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_prop)
    a_del_prop = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": p_del_prop.json()["proposal_id"]},
    )
    assert a_del_prop.status_code == 200
    assert "prop_cyber_deck" not in a_del_prop.json()["bible"]["props"]

def test_style_bible_update_and_deletion_guard(client, test_project):
    project_id = test_project

    # 1. Update style with full canonical fields
    update_style = {
        "target_type": "style",
        "target_id": "project_style",
        "change_description": "Update artistic style guidelines for noir arc",
        "proposed_changes": {
            "action": "update",
            "data": {
                "name": "Cyber-Noir Manga Ink",
                "medium": "traditional brush & screen-tone",
                "rendering_approach": "heavy chiaroscuro with dense cross-hatching",
                "line_art_rules": "thick dynamic contour lines, feathering at edges",
                "tonal_rules": "deep blacks, 60lpi 20% dot screentone, bright rim specular highlights",
                "background_detail_rules": "architectural perspective, high line density, atmospheric fog",
                "positive_constraints": ["high contrast", "manga ink masterwork", "dramatic low angles"],
                "negative_constraints": ["3D CGI render", "photorealistic skin", "color bleed", "fuzzy blur"],
            },
        },
    }
    prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=update_style)
    assert prop.status_code == 200
    applied = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop.json()["proposal_id"]},
    )
    assert applied.status_code == 200
    st = applied.json()["bible"]["style"]
    assert st["name"] == "Cyber-Noir Manga Ink"
    assert st["medium"] == "traditional brush & screen-tone"
    assert st["rendering_approach"] == "heavy chiaroscuro with dense cross-hatching"
    assert "high contrast" in st["positive_constraints"]
    assert "3D CGI render" in st["negative_constraints"]

    # 2. Deletion guard: deleting style must be rejected
    del_style = {
        "target_type": "style",
        "target_id": "project_style",
        "change_description": "Attempt to delete style",
        "proposed_changes": {"action": "delete"},
    }
    del_res = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=del_style)
    assert del_res.status_code == 400
    assert "style definition cannot be deleted" in del_res.json()["detail"]["message"].lower()

def test_proposals_audit_trail_and_rejection(client, test_project):
    project_id = test_project

    # 1. Propose mutation
    prop_req = {
        "target_type": "character",
        "target_id": "nour",
        "change_description": "Propose changing Nour's eye color",
        "proposed_changes": {
            "action": "update",
            "data": {"visual_invariants": ["amber eyes"]},
        },
    }
    res_prop = client.post(f"/api/v1/projects/{project_id}/bible/propose-mutation", json=prop_req)
    assert res_prop.status_code == 200
    prop_id = res_prop.json()["proposal_id"]

    # 2. List proposals
    res_list = client.get(f"/api/v1/projects/{project_id}/bible/proposals")
    assert res_list.status_code == 200
    proposals = res_list.json()
    assert any(p["proposal_id"] == prop_id for p in proposals)

    # 3. Reject proposal
    reject_req = {
        "proposal_id": prop_id,
        "reason": "Violates core character invariant of dark brown eyes.",
    }
    res_rej = client.post(f"/api/v1/projects/{project_id}/bible/reject-mutation", json=reject_req)
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"
    assert res_rej.json()["proposal"]["status"] == "rejected"

    # 4. Verify listed proposal status is updated
    res_list_after = client.get(f"/api/v1/projects/{project_id}/bible/proposals")
    updated_p = next(p for p in res_list_after.json() if p["proposal_id"] == prop_id)
    assert updated_p["status"] == "rejected"
    assert updated_p["rejection_reason"] == "Violates core character invariant of dark brown eyes."

    # 5. Guard: Attempting to apply a rejected proposal must fail
    res_apply_rejected = client.post(
        f"/api/v1/projects/{project_id}/bible/apply-mutation",
        json={"proposal_id": prop_id},
    )
    assert res_apply_rejected.status_code == 400
    assert "rejected" in res_apply_rejected.json()["detail"]["message"].lower()

def test_optimistic_concurrency_conflict_detection(client, test_project):
    project_id = test_project

    # 1. Fetch current bible
    res = client.get(f"/api/v1/projects/{project_id}/bible")
    assert res.status_code == 200
    bible_data = res.json()
    current_hash = bible_data["canon_hash"]
    current_version = bible_data["bible_version"]

    # 2. Stale hash conflict (409)
    res_conflict_hash = client.put(
        f"/api/v1/projects/{project_id}/bible",
        json={
            "bible": bible_data,
            "expected_canon_hash": "deadbeef" * 8,
        },
    )
    assert res_conflict_hash.status_code == 409
    assert res_conflict_hash.json()["detail"]["error_code"] == "ERR_1006_VERSION_MISMATCH"

    # 3. Stale version conflict (409)
    res_conflict_ver = client.put(
        f"/api/v1/projects/{project_id}/bible",
        json={
            "bible": bible_data,
            "expected_version": current_version + 99,
        },
    )
    assert res_conflict_ver.status_code == 409
    assert res_conflict_ver.json()["detail"]["error_code"] == "ERR_1006_VERSION_MISMATCH"

    # 4. Valid save with exact hash and version
    res_valid_save = client.put(
        f"/api/v1/projects/{project_id}/bible",
        json={
            "bible": bible_data,
            "expected_canon_hash": current_hash,
            "expected_version": current_version,
        },
    )
    assert res_valid_save.status_code == 200
    save_result = res_valid_save.json()
    assert save_result["status"] == "saved"
    assert save_result["bible_version"] == current_version + 1
