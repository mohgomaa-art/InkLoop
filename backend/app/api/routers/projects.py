"""
Project & Story Bible API Router.
Manages canonical character specs, style invariants, optimistic concurrency,
formal mutation proposals, and append-only narrative continuity timelines.
"""
import uuid
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.config import PROJECT_ROOT
from app.canvas.models import CanvasSpec, PageSpec, ReadingDirection
from app.canvas.engine import CanvasEngine
from app.editor.models import EditablePageDocument, EditorLayer, LayerKind
from app.project.bible import (
    load_bible,
    save_bible,
    create_canonical_nour_bible,
    get_canon_snapshot,
    propose_canon_mutation,
    apply_canon_mutation,
    reject_canon_mutation,
    append_state_event,
    resolve_timeline_state,
    CanonMutationProposal,
    StoryBible,
    StoryStateEvent,
    VersionConflictError,
    CanonValidationError,
    CanonMutationError,
    EntityNotFoundError,
)

router = APIRouter(prefix="/projects", tags=["Story Bible & Projects"])

def _get_project_dir(project_id: str) -> Path:
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("_", "-"))
    p = PROJECT_ROOT / "runs" / clean_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def _get_or_create_bible(project_id: str) -> StoryBible:
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    if not bible_path.exists():
        bible = create_canonical_nour_bible(PROJECT_ROOT)
        bible.project_id = project_id
        save_bible(bible, bible_path)
        return bible
    return load_bible(bible_path)

get_bible = _get_or_create_bible

class BibleUpdateRequest(BaseModel):
    bible: Dict[str, Any]
    expected_canon_hash: Optional[str] = None
    expected_version: Optional[int] = None

class ProposeMutationRequest(BaseModel):
    target_type: str = Field(default="character", description="'character', 'style', 'location', or 'prop'")
    target_id: str = Field(default="nour", description="Entity identifier (e.g. nour)")
    change_description: str = Field(..., description="Description of why this mutation is proposed")
    proposed_changes: Dict[str, Any] = Field(..., description="Target changes")

class ApplyMutationRequest(BaseModel):
    proposal: Optional[Dict[str, Any]] = None
    proposal_id: Optional[str] = None
    caller_authorized: bool = True

class RejectMutationRequest(BaseModel):
    proposal_id: str
    reason: Optional[str] = None
    caller_authorized: bool = True

class StateEventRequest(BaseModel):
    event_id: str
    panel_id: str
    target_entity: str
    state_delta: Dict[str, Any]
    description: str
    timestamp: Optional[str] = None

class SetCharacterAnchorRequest(BaseModel):
    asset_id: str = Field(..., description="Asset ID in AssetRegistry to set as canonical anchor")

class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)

class ProjectRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=1)

@router.get("")
def list_projects() -> List[Dict[str, Any]]:
    """List available projects with their current Bible version and canon hash."""
    runs_dir = PROJECT_ROOT / "runs"
    projects: List[Dict[str, Any]] = []
    
    if runs_dir.exists():
        for d in runs_dir.iterdir():
            if d.is_dir() and (d / "bible.json").exists() and not (d / "archived.json").exists():
                try:
                    bible = load_bible(d / "bible.json")
                    snap = get_canon_snapshot(d / "bible.json")
                    projects.append({
                        "project_id": bible.project_id,
                        "title": bible.title or bible.project_id,
                        "updated_at": bible.updated_at,
                        "bible_version": bible.bible_version,
                        "canon_hash": snap.canon_hash,
                        "characters": list(bible.characters.keys()),
                        "path": str(d.relative_to(PROJECT_ROOT)),
                    })
                except Exception:
                    continue

    if not projects:
        _get_or_create_bible("default_project")
        snap = get_canon_snapshot(_get_project_dir("default_project") / "bible.json")
        projects.append({
            "project_id": "default_project",
            "title": load_bible(_get_project_dir("default_project") / "bible.json").title,
            "bible_version": 1,
            "canon_hash": snap.canon_hash,
            "characters": ["nour"],
            "path": "runs/default_project",
        })

    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)

@router.post("", status_code=201)
def create_project(req: ProjectCreateRequest) -> Dict[str, Any]:
    """Create a durable project with a starter Story Bible and the canonical Nour entry."""
    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail={"message": "Project title cannot be empty."})
    stem = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:36] or "comic"
    project_id = f"{stem}_{uuid.uuid4().hex[:8]}"
    project_dir = _get_project_dir(project_id)
    bible = create_canonical_nour_bible(PROJECT_ROOT)
    bible.project_id = project_id
    bible.title = title
    bible_path = project_dir / "bible.json"
    save_bible(bible, bible_path)
    snapshot = get_canon_snapshot(bible_path)
    return {"project_id": project_id, "title": title, "bible_version": bible.bible_version, "canon_hash": snapshot.canon_hash, "characters": list(bible.characters)}


class QuickStartProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="Project title")
    genre: Literal["shonen", "seinen", "webtoon", "scifi", "comedy"] = Field("shonen", description="Genre preset")
    premise: str = Field(min_length=1, max_length=1000, description="Story premise or logline")
    reading_direction: Literal["rtl", "ltr"] = Field("ltr", description="Reading direction (ltr=Western, rtl=Manga/Arabic)")
    language: Literal["ar", "en"] = Field("en", description="Primary lettering language")


@router.post("/quick_start", status_code=201, summary="Instant 60-second project bootstrap with Story Bible and Page 1")
def quick_start_project(req: QuickStartProjectRequest) -> Dict[str, Any]:
    """
    1-Click Quick Start Project Wizard:
    - Creates durable project and canonical Story Bible
    - Seeds genre-tuned visual style constants and starter cast
    - Generates Page 1 document with dynamic layout template
    - Returns all IDs for immediate launch into Canvas Studio
    """
    from app.api.routers.editor import get_page_store

    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail={"message": "Project title cannot be empty."})
    stem = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:36] or "comic"
    project_id = f"{stem}_{uuid.uuid4().hex[:8]}"
    project_dir = _get_project_dir(project_id)

    # Initialize Story Bible
    bible = create_canonical_nour_bible(PROJECT_ROOT)
    bible.project_id = project_id
    bible.title = title
    bible.user_story_text = req.premise.strip()
    bible.language = req.language
    bible.reading_direction = req.reading_direction

    # Configure genre-tuned style and template
    if req.genre == "shonen":
        bible.style.name = "Dynamic Shonen Ink"
        bible.style.line_art_rules = ["Bold dynamic ink strokes", "Kinetic impact lines", "High contrast silhouettes"]
        bible.style.tonal_rules = ["Deep black shadows", "Action halftone screentones"]
        template_id = "dynamic_shonen"
    elif req.genre == "webtoon":
        bible.style.name = "Clean Digital Webtoon"
        bible.style.line_art_rules = ["Smooth vector-like contours", "Clean continuous lines"]
        bible.style.tonal_rules = ["Subtle digital screentones", "Clean white gutters"]
        template_id = "webtoon_vertical"
    elif req.genre == "seinen":
        bible.style.name = "Gritty Seinen Realism"
        bible.style.line_art_rules = ["Dense cross-hatching", "Fine architectural detail lines"]
        bible.style.tonal_rules = ["Heavy black ink pools", "Atmospheric screentone textures"]
        template_id = "four_panel_cinematic"
    elif req.genre == "comedy":
        bible.style.name = "Expressive 4-Koma Cartoon"
        bible.style.line_art_rules = ["Playful curved outlines", "Exaggerated emotion contours"]
        bible.style.tonal_rules = ["Minimal screentones", "Bright open spaces"]
        template_id = "four_koma"
    else:  # scifi
        bible.style.name = "Cyberpunk Hard Sci-Fi"
        bible.style.line_art_rules = ["Geometric mechanical lines", "Sharp precision edge contrast"]
        bible.style.tonal_rules = ["Duotone screentone", "Atmospheric ink occlusion"]
        template_id = "manga_grid"

    bible_path = project_dir / "bible.json"
    save_bible(bible, bible_path)
    snapshot = get_canon_snapshot(bible_path)

    # Generate Page 1 layout and persist in PageDocumentStore
    page_id = f"page_1_{uuid.uuid4().hex[:6]}"
    canvas_spec = CanvasSpec(width=1600, height=2400)
    page_spec = PageSpec(
        page_id=page_id,
        page_number=1,
        reading_direction=ReadingDirection.RTL if req.reading_direction == "rtl" else ReadingDirection.LTR,
    )
    layout = CanvasEngine.generate_layout(canvas_spec, page_spec, template_id)
    layers = [
        EditorLayer(
            layer_id=f"layer_{s.panel_id}",
            kind=LayerKind.PANEL,
            label=s.panel_id,
            z_index=s.z_index,
            panel_id=s.panel_id,
        )
        for s in layout.panel_slots
    ]
    doc = EditablePageDocument(
        page_id=page_id,
        project_id=project_id,
        layout=layout,
        layers=layers,
    )
    get_page_store().create(doc)

    return {
        "success": True,
        "project_id": project_id,
        "bible_id": project_id,
        "page_1_id": page_id,
        "title": bible.title,
        "genre": req.genre,
        "summary": bible.user_story_text,
        "reading_direction": req.reading_direction,
        "language": req.language,
        "canon_hash": snapshot.canon_hash,
        "layout_template": template_id,
        "starter_characters": [c.model_dump() for c in bible.characters.values()],
    }


@router.put("/{project_id}/details")
def rename_project(project_id: str, req: ProjectRenameRequest) -> Dict[str, Any]:
    """Rename a project without changing its stable ID or canon identity."""
    bible_path = _get_project_dir(project_id) / "bible.json"
    bible = _get_or_create_bible(project_id)
    current = get_canon_snapshot(bible_path)
    if bible.bible_version != req.expected_version:
        raise HTTPException(status_code=409, detail={"message": "Project changed since it was loaded.", "current_version": bible.bible_version})
    bible.title = req.title.strip()
    save_bible(bible, bible_path, expected_version=req.expected_version)
    snapshot = get_canon_snapshot(bible_path)
    return {"project_id": project_id, "title": bible.title, "bible_version": bible.bible_version, "canon_hash": snapshot.canon_hash}

@router.delete("/{project_id}", status_code=200)
def archive_project(project_id: str) -> Dict[str, Any]:
    """Hide a project from the active list while retaining all its durable assets and history."""
    project_dir = _get_project_dir(project_id)
    if not (project_dir / "bible.json").exists():
        raise HTTPException(status_code=404, detail={"message": "Project not found."})
    marker = project_dir / "archived.json"
    marker.write_text(json.dumps({"project_id": project_id, "archived_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
    return {"project_id": project_id, "archived": True, "history_retained": True}

@router.get("/{project_id}/bible")
def get_project_bible(project_id: str) -> Dict[str, Any]:
    """Retrieve canonical Story Bible with real-time computed snapshot hash."""
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    bible = _get_or_create_bible(project_id)
    snap = get_canon_snapshot(bible_path)

    data = bible.model_dump()
    data["canon_hash"] = snap.canon_hash
    return data

@router.put("/{project_id}/bible")
def update_project_bible(project_id: str, req: BibleUpdateRequest) -> Dict[str, Any]:
    """
    Save Story Bible updates with optimistic concurrency check.
    Fails closed with HTTP 409 if expected canon hash or version does not match.
    """
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    
    if bible_path.exists():
        current_snap = get_canon_snapshot(bible_path)
        current_bible = load_bible(bible_path)
        
        # Concurrency verification
        if req.expected_canon_hash and req.expected_canon_hash != current_snap.canon_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "ERR_1006_VERSION_MISMATCH",
                    "message": "Optimistic concurrency conflict: Story Bible was modified concurrently.",
                    "current_canon_hash": current_snap.canon_hash,
                    "expected_canon_hash": req.expected_canon_hash,
                    "current_version": current_bible.bible_version,
                }
            )
        if req.expected_version and req.expected_version != current_bible.bible_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "ERR_1006_VERSION_MISMATCH",
                    "message": "Story Bible version mismatch.",
                    "current_version": current_bible.bible_version,
                    "expected_version": req.expected_version,
                }
            )

    try:
        new_bible = StoryBible(**req.bible)
        new_bible.project_id = project_id
        if current_bible:
            new_bible.bible_version = current_bible.bible_version + 1
        save_bible(new_bible, bible_path)
        new_snap = get_canon_snapshot(bible_path)
        
        result = new_bible.model_dump()
        result["canon_hash"] = new_snap.canon_hash
        return {
            "status": "saved",
            "bible_version": new_bible.bible_version,
            "canon_hash": new_snap.canon_hash,
            "bible": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "ERR_1001_INVALID_SCHEMA", "message": str(e)}
        )

@router.post("/{project_id}/bible/propose-mutation")
def create_mutation_proposal(project_id: str, req: ProposeMutationRequest) -> Dict[str, Any]:
    """Create a structured CanonMutationProposal for formal review."""
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    current_bible = _get_or_create_bible(project_id)

    action = req.proposed_changes.get("action")
    if req.target_type == "character" and action == "delete" and len(current_bible.characters) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_1003_DELETION_GUARD", "message": "Cannot delete character: project must retain at least one character."}
        )

    proposal = CanonMutationProposal(
        proposal_id=f"prop_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        target_type=req.target_type,
        target_id=req.target_id,
        change_description=req.change_description,
        proposed_changes=req.proposed_changes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        result = propose_canon_mutation(bible_path, proposal)
        return result.model_dump()
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_1002_ENTITY_NOT_FOUND", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_3004_CANON_MUTATION_REJECTED", "message": str(e)}
        )

@router.post("/{project_id}/bible/apply-mutation")
def apply_mutation(project_id: str, req: ApplyMutationRequest) -> Dict[str, Any]:
    """Apply an approved CanonMutationProposal, creating a new monotonic version snapshot."""
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    _get_or_create_bible(project_id)
    prop_id = req.proposal_id or (req.proposal.get("proposal_id") if req.proposal else None)
    if not prop_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "ERR_1001_INVALID_SCHEMA", "message": "Missing proposal_id in request"}
        )

    try:
        updated_bible = apply_canon_mutation(
            bible_path,
            proposal_id=prop_id,
            approved_by="lead_operator",
        )
        snap = get_canon_snapshot(bible_path)
        return {
            "status": "applied",
            "bible_version": updated_bible.bible_version,
            "canon_hash": snap.canon_hash,
            "bible": updated_bible.model_dump(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_3004_CANON_MUTATION_REJECTED", "message": str(e)}
        )

@router.get("/{project_id}/bible/proposals")
def list_mutation_proposals(project_id: str) -> List[Dict[str, Any]]:
    """List all canon mutation proposals for a project."""
    p_dir = _get_project_dir(project_id)
    proposals_file = p_dir / "canon_proposals.jsonl"
    proposals = []
    if proposals_file.exists():
        with open(proposals_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        proposals.append(json.loads(line.strip()))
                    except Exception:
                        continue
    return proposals

@router.post("/{project_id}/bible/reject-mutation")
def reject_mutation(project_id: str, req: RejectMutationRequest) -> Dict[str, Any]:
    """Reject a pending CanonMutationProposal."""
    p_dir = _get_project_dir(project_id)
    bible_path = p_dir / "bible.json"
    _get_or_create_bible(project_id)
    try:
        rejected = reject_canon_mutation(
            bible_path,
            proposal_id=req.proposal_id,
            rejected_by="lead_operator",
            reason=req.reason,
        )
        return {
            "status": "rejected",
            "proposal": rejected.model_dump(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_3004_CANON_MUTATION_REJECTED", "message": str(e)}
        )

@router.get("/{project_id}/timeline")
def get_timeline(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve narrative state timeline events."""
    p_dir = _get_project_dir(project_id)
    timeline_file = p_dir / "state.jsonl"
    events = []
    if timeline_file.exists():
        with open(timeline_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        import json
                        events.append(json.loads(line))
                    except Exception:
                        continue
    return events

@router.post("/{project_id}/timeline/event")
def append_event(project_id: str, req: StateEventRequest) -> Dict[str, Any]:
    """Append a narrative event to the story state timeline."""
    p_dir = _get_project_dir(project_id)
    timeline_file = p_dir / "state.jsonl"
    
    event_dict = req.model_dump()
    if not event_dict.get("timestamp"):
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    import json
    with open(timeline_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_dict) + "\n")

    return {"status": "appended", "event": event_dict}

@router.get("/{project_id}/timeline/resolve/{panel_id}")
def resolve_panel_state(project_id: str, panel_id: str) -> Dict[str, Any]:
    """Deterministically resolve state for a specific panel."""
    p_dir = _get_project_dir(project_id)
    timeline_file = p_dir / "state.jsonl"
    resolved_state: Dict[str, Any] = {}
    
    if timeline_file.exists():
        with open(timeline_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        import json
                        ev = json.loads(line)
                        target = ev.get("target_entity", "global")
                        if target not in resolved_state:
                            resolved_state[target] = {}
                        resolved_state[target].update(ev.get("state_delta", {}))
                    except Exception:
                        continue

    return {
        "panel_id": panel_id,
        "resolved_state": resolved_state,
        "deterministic": True,
    }


@router.post("/{project_id}/characters/{character_id}/anchor")
def set_character_anchor(
    project_id: str,
    character_id: str,
    req: SetCharacterAnchorRequest,
) -> Dict[str, Any]:
    """Sets an existing registered asset as the canonical reference anchor for a Story Bible character."""
    from app.project.asset_refs import AssetRef
    from app.api.routers.assets import get_registry

    cid = character_id.lower().strip()
    bible = _get_or_create_bible(project_id)
    if cid not in bible.characters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{cid}' not found in project '{project_id}'."
        )

    reg = get_registry()
    try:
        resolved = reg.resolve_asset(req.asset_id, verify_integrity=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{req.asset_id}' not found in registry: {exc}"
        )

    try:
        rel_path = str(resolved.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except Exception:
        rel_path = str(resolved.absolute_path).replace("\\", "/")

    new_ref = AssetRef(
        asset_id=resolved.metadata.asset_id,
        path=rel_path,
        asset_type="character_sheet",
        expected_hash=resolved.metadata.content_sha256,
        mime_type=resolved.metadata.mime_type,
        file_size_bytes=resolved.metadata.byte_size,
    )

    char_def = bible.characters[cid]
    existing_refs = [r for r in getattr(char_def, "reference_assets", []) if getattr(r, "asset_id", None) != req.asset_id]
    char_def.reference_assets = [new_ref] + existing_refs
    bible.bible_version += 1
    p_dir = _get_project_dir(project_id)
    save_bible(bible, p_dir / "bible.json")

    return {
        "status": "success",
        "character_id": cid,
        "character_name": char_def.name,
        "asset_id": req.asset_id,
        "url": f"/api/v1/assets/{req.asset_id}/file",
        "content_sha256": resolved.metadata.content_sha256,
        "bible_version": bible.bible_version,
    }


@router.post("/{project_id}/characters/{character_id}/upload-anchor")
async def upload_character_anchor(
    project_id: str,
    character_id: str,
    file: Any = None,
) -> Dict[str, Any]:
    """Uploads an image file and immediately registers it as the canonical reference anchor for a character."""
    from fastapi import UploadFile, File
    from app.api.routers.assets import upload_image_asset
    from app.project.asset_refs import AssetRef
    from app.api.routers.assets import get_registry

    cid = character_id.lower().strip()
    bible = _get_or_create_bible(project_id)
    if cid not in bible.characters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{cid}' not found in project '{project_id}'."
        )

    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is required."
        )

    uploaded = await upload_image_asset(
        project_id=project_id,
        asset_type="character_sheet",
        name=f"{cid}_anchor_reference",
        file=file,
    )
    asset_id = uploaded["asset_id"]

    reg = get_registry()
    resolved = reg.resolve_asset(asset_id, verify_integrity=True)
    try:
        rel_path = str(resolved.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except Exception:
        rel_path = str(resolved.absolute_path).replace("\\", "/")

    new_ref = AssetRef(
        asset_id=asset_id,
        path=rel_path,
        asset_type="character_sheet",
        expected_hash=resolved.metadata.content_sha256,
        mime_type=resolved.metadata.mime_type,
        file_size_bytes=resolved.metadata.byte_size,
    )

    char_def = bible.characters[cid]
    existing_refs = [r for r in getattr(char_def, "reference_assets", []) if getattr(r, "asset_id", None) != asset_id]
    char_def.reference_assets = [new_ref] + existing_refs
    bible.bible_version += 1
    p_dir = _get_project_dir(project_id)
    save_bible(bible, p_dir / "bible.json")

    return {
        "status": "success",
        "character_id": cid,
        "character_name": char_def.name,
        "asset_id": asset_id,
        "url": f"/api/v1/assets/{asset_id}/file",
        "content_sha256": resolved.metadata.content_sha256,
        "bible_version": bible.bible_version,
    }


@router.post("/{project_id}/characters/{character_id}/generate-anchor")
def generate_character_anchor(
    project_id: str,
    character_id: str,
) -> Dict[str, Any]:
    """Generates an initial reference anchor portrait for a character based on visual invariants and registers it."""
    import os
    import hashlib
    from app.config import InkLoopConfig
    from app.image_adapter import SimulatedImageGenerationAdapter, MetaImageGenerationAdapter, GenerationRequest
    from app.api.routers.assets import get_registry
    from app.contracts.artifacts import AssetType
    from app.project.asset_refs import AssetRef

    cid = character_id.lower().strip()
    bible = _get_or_create_bible(project_id)
    if cid not in bible.characters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{cid}' not found in project '{project_id}'."
        )

    char_def = bible.characters[cid]
    invariants_text = ", ".join(char_def.visual_invariants) if char_def.visual_invariants else "Distinctive manga character appearance"
    wardrobe_text = ", ".join(char_def.clothing_attributes) if char_def.clothing_attributes else "Standard attire"
    
    prompt = (
        f"Initial canonical reference anchor bust portrait of {char_def.name}. "
        f"Character model sheet style, clear lighting, neutral expression, centered face. "
        f"Visual invariants: {invariants_text}. "
        f"Default wardrobe: {wardrobe_text}. "
        f"Masterpiece, crisp manga line art, high detail, no speech bubbles, no text."
    )

    offline = os.getenv("INKLOOP_OFFLINE_MODE", "0").lower() in ("1", "true")
    adapter = (
        SimulatedImageGenerationAdapter(default_success=True)
        if offline
        else MetaImageGenerationAdapter(config=InkLoopConfig.load())
    )

    req = GenerationRequest(
        prompt=prompt,
        panel_id=f"anchor_{cid}",
        dimensions=[768, 1024],
        scene_id="anchor_s0",
    )
    resp = adapter.generate(req)
    if not resp.success or not resp.image_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Anchor image generation failed: {resp.error_message or 'Unknown error'}"
        )

    reg = get_registry()
    asset = reg.ingest_bytes(
        data=resp.image_bytes,
        filename=f"{cid}_canonical_anchor.png",
        project_id=project_id,
        asset_type=AssetType.IMAGE_REFERENCE,
        name=f"{char_def.name} Canonical Reference Anchor",
        source_origin="E1 Anchor Portrait Synthesis",
        extra_metadata={
            "character_id": cid,
            "is_canonical_anchor": True,
            "width": 768,
            "height": 1024,
            "mime_type": "image/png",
            "is_simulated": resp.is_simulated,
        },
    )

    try:
        res_obj = reg.resolve_asset(asset.asset_id, verify_integrity=False)
        rel_path = str(res_obj.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except Exception:
        rel_path = str(asset.managed_path).replace("\\", "/")

    new_ref = AssetRef(
        asset_id=asset.asset_id,
        path=rel_path,
        asset_type="character_sheet",
        expected_hash=asset.content_sha256,
        mime_type="image/png",
        file_size_bytes=asset.byte_size,
    )

    existing_refs = [r for r in getattr(char_def, "reference_assets", []) if getattr(r, "asset_id", None) != asset.asset_id]
    char_def.reference_assets = [new_ref] + existing_refs
    bible.bible_version += 1
    p_dir = _get_project_dir(project_id)
    save_bible(bible, p_dir / "bible.json")

    return {
        "status": "success",
        "character_id": cid,
        "character_name": char_def.name,
        "asset_id": asset.asset_id,
        "url": f"/api/v1/assets/{asset.asset_id}/file",
        "content_sha256": asset.content_sha256,
        "bible_version": bible.bible_version,
        "is_simulated": resp.is_simulated,
    }
