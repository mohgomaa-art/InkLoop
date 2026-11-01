"""
FastAPI Router for InkLoop Creative Director: Style Copier & Character Copier.
Provides typed REST endpoints for:
- Style reference intake, analysis, profile management, and user approval
- Character reference analysis, invariant extraction, character sheet planning, and Canon proposals
- Combined multi-reference generation and bounded QA refinement
- Declared provider capabilities
"""
import uuid
import threading
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT
from app.api.routers.assets import get_registry
from app.image_adapter import ProviderCapabilities
from app.creative.models import (
    StyleProfile,
    CharacterIdentityProfile,
    GenerationReferenceSet,
    StyleAnalysisRecord,
    ReferenceBinding,
    SemanticReferenceRole,
    ProfileStatus,
    StyleControlVariable,
)
from app.creative.storage import get_creative_profile_store
from app.creative.quick_styles import QUICK_STYLE_BY_ID, QUICK_STYLE_TEMPLATES
from app.creative.analyzer import (
    StyleAnalyzer,
    CharacterAnalyzer,
    ObjectAnalyzer,
    AnalysisUnavailableError,
    AnalysisProviderError,
)
from app.creative.orchestration import CreativeOrchestrator, CreativeGenerationResult, GenerationProviderUnavailableError
from app.creative.schemas import CharacterSheetPlan
from app.project.bible import StoryBible, load_bible, save_bible, create_canonical_nour_bible, CanonMutationProposal, propose_canon_mutation, VersionConflictError
from app.project.canon import PropAnalysisRecord, PropDefinition, StyleDefinition
from app.project.asset_refs import AssetRef


router = APIRouter(prefix="/projects/{project_id}/creative", tags=["Creative Director (Style & Character Copier)"])
_quick_style_apply_lock = threading.RLock()


# =============================================================================
# Request Schemas
# =============================================================================

class StyleAnalyzeRequest(BaseModel):
    asset_ids: List[str] = Field(..., min_length=1, max_length=3, description="AssetRegistry IDs for style references")
    user_instructions: Optional[str] = Field(default=None, description="Optional style prompt hints")


class CharacterAnalyzeRequest(BaseModel):
    character_id: str = Field(..., description="Stable character identifier in Story Bible")
    name: str = Field(..., description="Character display name")
    references: List[ReferenceBinding] = Field(..., min_length=1, max_length=4, description="Labeled character references")
    known_canon_facts: Optional[List[str]] = Field(default=None, description="Pre-existing canonical traits")


class ObjectAnalyzeRequest(BaseModel):
    prop_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    asset_ids: List[str] = Field(..., min_length=1, max_length=4)
    creator_notes: Optional[str] = Field(default=None, max_length=3000)


class ObjectDraftRequest(BaseModel):
    prop: PropDefinition
    expected_bible_version: int = Field(..., ge=1)
    reference_asset_ids: Optional[List[str]] = Field(default=None, max_length=4)


class ProposeCanonRequest(BaseModel):
    change_description: Optional[str] = Field(default=None, description="Reason for proposing to Canon")


class SheetGenerateRequest(BaseModel):
    style_profile_id: Optional[str] = Field(default=None, description="Optional style profile ID to style the turnaround views")
    max_attempts: int = Field(default=2, ge=1, le=4)


def _object_asset_ref(registry, project_id: str, asset_id: str) -> AssetRef:
    try:
        resolved = registry.resolve_asset(asset_id, verify_integrity=True)
    except Exception as exc:
        raise ValueError(f"Reference asset '{asset_id}' could not be verified: {exc}") from exc
    metadata = resolved.metadata
    if metadata.project_id != project_id:
        raise ValueError(f"Reference asset '{asset_id}' belongs to another project.")
    if metadata.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"Reference asset '{asset_id}' is not a supported image.")
    if metadata.byte_size > 15 * 1024 * 1024:
        raise ValueError(f"Reference asset '{asset_id}' exceeds the 15 MB object-reference limit.")
    try:
        path = str(resolved.absolute_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except ValueError as exc:
        raise ValueError(f"Reference asset '{asset_id}' is outside project storage.") from exc
    return AssetRef(
        asset_id=asset_id,
        path=path,
        asset_type="prop_ref",
        expected_hash=metadata.content_sha256,
        mime_type=metadata.mime_type,
        file_size_bytes=metadata.byte_size,
        provenance={"source": "object_studio", "original_filename": metadata.original_filename},
    )


def _object_bible_path(project_id: str):
    clean_project_id = "".join(char for char in project_id if char.isalnum() or char in ("_", "-"))
    if not clean_project_id or clean_project_id != project_id:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_PROJECT_ID", "message": "Invalid project ID."})
    project_dir = PROJECT_ROOT / "runs" / clean_project_id
    return project_dir / "bible.json"


def _load_object_bible(project_id: str, *, create_if_missing: bool = False):
    bible_path = _object_bible_path(project_id)
    if bible_path.exists():
        return load_bible(bible_path), bible_path
    if not create_if_missing:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_PROJECT_BIBLE_NOT_FOUND", "message": "This project does not have a saved Story Bible yet."})
    bible_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    bible = StoryBible(
        project_id=project_id,
        title="Untitled Comic",
        created_at=now,
        updated_at=now,
        status="draft",
        style=StyleDefinition(
            style_id="unspecified",
            name="Unspecified",
            medium="Not specified",
            rendering_approach="Not specified",
        ),
        characters={},
    )
    save_bible(bible, target_path=bible_path)
    return bible, bible_path


@router.get("/style-templates")
def list_quick_style_templates() -> List[Dict[str, Any]]:
    """List versioned built-in quick styles and their real preview provenance."""
    return [template.model_dump() for template in QUICK_STYLE_TEMPLATES]


@router.post("/style-templates/{template_id}/apply", response_model=StyleProfile)
def apply_quick_style_template(project_id: str, template_id: str) -> StyleProfile:
    """Import a built-in style as a project draft once; never overwrite user edits."""
    template = QUICK_STYLE_BY_ID.get(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quick style template was not found.")

    clean_project_id = "".join(char for char in project_id if char.isalnum() or char in ("_", "-"))
    if not clean_project_id or clean_project_id != project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project ID.")

    store = get_creative_profile_store()
    with _quick_style_apply_lock:
        preview_asset_ids = {
            item.preview_asset_id
            for item in QUICK_STYLE_TEMPLATES
            if item.preview_asset_id
        }
        existing_profiles = [
            profile for profile in store.list_style_profiles(project_id, include_archived=True)
            if profile.metadata.get("quick_style_template_id") == template_id
        ]
        # These images are picker examples only. Keep the profile prompt pure;
        # the preview itself must never become a generation reference.
        preview_status = "display_only_not_sent"
        initial_references = []

        for existing in existing_profiles:
            if existing.status == ProfileStatus.DRAFT:
                changed = False
                cleaned_references = [reference for reference in existing.references if reference.asset_id not in preview_asset_ids]
                if len(cleaned_references) != len(existing.references):
                    existing.references = cleaned_references
                    changed = True
                if existing.metadata.get("quick_style_preview_reference_status") != preview_status:
                    existing.metadata["quick_style_preview_reference_status"] = preview_status
                    changed = True
                if changed:
                    return store.save_style_profile(existing)
            return existing

        profile_id = f"quick_{template_id}"
        collision = store.get_style_profile(project_id, profile_id)
        if collision:
            profile_id = f"quick_{template_id}_{uuid.uuid4().hex[:8]}"

        profile = StyleProfile(
            profile_id=profile_id,
            project_id=project_id,
            name=template.name,
            status=ProfileStatus.DRAFT,
            style_prompt_core=template.style_prompt_core,
            negative_constraints=list(template.negative_constraints),
            references=initial_references,
            style_variables={
                key: StyleControlVariable(value=value, pinned=True, source="user_authored")
                for key, value in template.variables.items()
            },
            metadata={
                "quick_style_template_id": template.template_id,
                "quick_style_template_version": template.version,
                "preview_asset_id": template.preview_asset_id,
                "preview_url": template.preview_url,
                "preview_provider": template.preview_provider,
                "preview_prompt": template.preview_prompt,
                "quick_style_preview_reference_status": preview_status,
            },
        )
        return store.save_style_profile(profile)


class SheetViewResult(BaseModel):
    view_role: str
    label: str
    description: str
    camera_angle: str
    framing: str
    asset_id: str
    content_sha256: str
    qa_score: Optional[float] = None
    fidelity_notes: List[str]


class TurnaroundSheetResult(BaseModel):
    character_id: str
    profile_id: str
    views: List[SheetViewResult]
    total_views: int
    all_passed_qa: bool


class CreativeGenerateRequest(BaseModel):
    scene_action: str = Field(..., description="What happens in the panel/scene")
    shot_type: str = Field(default="Medium shot, eye-level angle")
    style_profile_id: Optional[str] = Field(default=None)
    character_profile_ids: Optional[List[str]] = Field(default=None)
    reference_set: Optional[GenerationReferenceSet] = Field(default=None)
    panel_id: str = Field(default="panel_01")
    scene_id: str = Field(default="scene_01")
    max_attempts: int = Field(default=2, ge=1, le=4)
    dimensions: Optional[List[int]] = Field(default=None)
    aspect_ratio: Optional[str] = Field(default=None)
    composition_notes: Optional[str] = Field(default=None)
    lighting_intent: Optional[str] = Field(default=None)


# =============================================================================
# Style Copier Endpoints
# =============================================================================

@router.post("/styles/analyze", response_model=StyleAnalysisRecord)
def analyze_style_references(project_id: str, req: StyleAnalyzeRequest) -> StyleAnalysisRecord:
    """Extracts structured, evidence-backed style traits from reference images."""
    registry = get_registry()
    analyzer = StyleAnalyzer(registry)
    try:
        return analyzer.analyze_references(
            project_id=project_id,
            asset_ids=req.asset_ids,
            user_instructions=req.user_instructions,
        )
    except AnalysisUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_VISION_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except AnalysisProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "ERR_VISION_ANALYSIS_FAILED", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "ERR_INVALID_STYLE_REFERENCES", "message": str(exc)}
        )


@router.post("/styles", response_model=StyleProfile)
def create_or_update_style_profile(project_id: str, profile: StyleProfile) -> StyleProfile:
    """Creates or updates a persistent StyleProfile in the project workspace."""
    profile.project_id = project_id
    store = get_creative_profile_store()
    return store.save_style_profile(profile)


@router.get("/styles", response_model=List[StyleProfile])
def list_style_profiles(project_id: str, include_archived: bool = Query(default=False)) -> List[StyleProfile]:
    """Lists all persistent style profiles for a project."""
    store = get_creative_profile_store()
    return store.list_style_profiles(project_id=project_id, include_archived=include_archived)


@router.get("/styles/{profile_id}", response_model=StyleProfile)
def get_style_profile(project_id: str, profile_id: str) -> StyleProfile:
    """Retrieves an existing StyleProfile by ID."""
    store = get_creative_profile_store()
    prof = store.get_style_profile(project_id, profile_id)
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Style profile '{profile_id}' not found.")
    return prof


@router.post("/styles/{profile_id}/approve", response_model=StyleProfile)
def approve_style_profile(project_id: str, profile_id: str) -> StyleProfile:
    """Formally approves a StyleProfile, locking its current version as verified."""
    store = get_creative_profile_store()
    try:
        return store.approve_style_profile(project_id, profile_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Style profile '{profile_id}' not found.")


@router.post("/styles/{profile_id}/archive", response_model=StyleProfile)
def archive_style_profile(project_id: str, profile_id: str) -> StyleProfile:
    """Archives a StyleProfile."""
    store = get_creative_profile_store()
    try:
        return store.archive_style_profile(project_id, profile_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Style profile '{profile_id}' not found.")


# =============================================================================
# Character Copier Endpoints
# =============================================================================

@router.post("/characters/analyze", response_model=CharacterIdentityProfile)
def analyze_character_references(project_id: str, req: CharacterAnalyzeRequest) -> CharacterIdentityProfile:
    """Extracts identity invariants, flexible variations, and proposed profile from references."""
    registry = get_registry()
    analyzer = CharacterAnalyzer(registry)
    try:
        return analyzer.analyze_character(
            project_id=project_id,
            character_id=req.character_id,
            name=req.name,
            references=req.references,
            known_canon_facts=req.known_canon_facts,
        )
    except AnalysisUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_VISION_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except AnalysisProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "ERR_VISION_ANALYSIS_FAILED", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "ERR_INVALID_CHARACTER_REFERENCES", "message": str(exc)}
        )


# =============================================================================
# Object Studio (project Story Bible prop records remain the single source)
# =============================================================================

@router.get("/objects", response_model=List[PropDefinition])
def list_object_profiles(project_id: str) -> List[PropDefinition]:
    bible, _ = _load_object_bible(project_id)
    return sorted(bible.props.values(), key=lambda item: (item.name.casefold(), item.prop_id))


@router.post("/objects/analyze", response_model=PropDefinition)
def analyze_object_references(project_id: str, req: ObjectAnalyzeRequest) -> PropDefinition:
    registry = get_registry()
    analyzer = ObjectAnalyzer(registry)
    try:
        return analyzer.analyze_object(
            project_id=project_id,
            prop_id=req.prop_id,
            name=req.name,
            asset_ids=req.asset_ids,
            creator_notes=req.creator_notes,
        )
    except AnalysisUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error_code": "ERR_VISION_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except AnalysisProviderError as exc:
        raise HTTPException(status_code=502, detail={"error_code": "ERR_VISION_ANALYSIS_FAILED", "message": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_OBJECT_REFERENCES", "message": str(exc)})


def _save_object_draft(project_id: str, req: ObjectDraftRequest, expected_prop_id: Optional[str] = None) -> Dict[str, Any]:
    bible, bible_path = _load_object_bible(project_id, create_if_missing=True)
    if req.expected_bible_version != bible.bible_version:
        raise HTTPException(status_code=409, detail={
            "error_code": "ERR_BIBLE_VERSION_CONFLICT",
            "message": "The Story Bible changed while this object draft was open. Reload it before saving.",
            "current_version": bible.bible_version,
        })
    prop = req.prop.model_copy(deep=True)
    prop.prop_id = prop.prop_id.strip().lower()
    if expected_prop_id and prop.prop_id != expected_prop_id:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_OBJECT_ID_IMMUTABLE", "message": "An existing object ID cannot be changed."})
    if prop.approval_status != "draft":
        raise HTTPException(status_code=422, detail={"error_code": "ERR_OBJECT_DRAFT_REQUIRED", "message": "Only draft objects can be saved directly. Canon objects must go through the proposal approval flow."})
    existing = bible.props.get(prop.prop_id)
    if existing and expected_prop_id is None:
        raise HTTPException(status_code=409, detail={"error_code": "ERR_OBJECT_ALREADY_EXISTS", "message": "This object ID already exists. Select it to edit the saved draft instead of creating a duplicate."})
    if existing and existing.approval_status != "draft":
        raise HTTPException(status_code=409, detail={"error_code": "ERR_OBJECT_ALREADY_CANON", "message": "This object is already in Canon; propose an update instead of overwriting it."})
    try:
        normalized_refs = []
        existing_hashes = {ref.asset_id: ref.expected_hash for ref in prop.reference_assets}
        submitted_asset_ids = req.reference_asset_ids if req.reference_asset_ids is not None else list(existing_hashes)
        if len(submitted_asset_ids) != len(set(submitted_asset_ids)):
            raise ValueError("Object reference asset IDs must be unique.")
        for asset_id in submitted_asset_ids:
            verified = _object_asset_ref(get_registry(), project_id, asset_id)
            if req.reference_asset_ids is None and verified.expected_hash != existing_hashes[asset_id]:
                raise ValueError(f"Reference asset '{asset_id}' changed since analysis. Analyze or attach the current asset again.")
            normalized_refs.append(verified)
        prop.reference_assets = normalized_refs
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_OBJECT_REFERENCES", "message": str(exc)}) from exc

    # Trait observations only describe the exact image set that was analyzed.
    # If a creator changes that set without rerunning analysis, retain authored
    # fields but clear stale model-derived claims and evidence.
    if prop.analysis.analysis_status == "completed":
        analyzed_asset_ids = {
            asset_id
            for feature in prop.identity_features
            for asset_id in feature.evidence_asset_ids
        }
        current_asset_ids = set(submitted_asset_ids)
        if analyzed_asset_ids != current_asset_ids:
            list_fields = {
                "materials", "palette", "components", "distinctive_marks",
                "stable_invariants", "allowed_states",
            }
            for field_name, provenance in list(prop.trait_provenance.items()):
                if provenance not in {"model_observation", "model_inference"}:
                    continue
                if field_name == "description":
                    prop.description = ""
                elif field_name == "form_and_proportions":
                    prop.form_and_proportions = ""
                elif field_name in list_fields:
                    setattr(prop, field_name, [])
                    if field_name == "stable_invariants":
                        prop.required_attributes = []
                prop.trait_provenance[field_name] = "unknown"
            prop.identity_features = [
                feature for feature in prop.identity_features
                if feature.provenance == "user_authored"
            ]
            stale_note = "Reference images changed; analyze the current reference set before relying on visual observations."
            prop.uncertain_traits = [stale_note]
            prop.analysis = PropAnalysisRecord(
                analysis_status="not_run",
                analysis_source="references_changed_requires_analysis",
                unknown_or_occluded=[stale_note],
                creator_authored_facts=list(prop.analysis.creator_authored_facts),
            )
    if existing:
        prop.version = max(prop.version, existing.version + 1)
    else:
        prop.version = max(1, prop.version)
    bible.props[prop.prop_id] = prop
    old_version = bible.bible_version
    bible.bible_version = old_version + 1
    try:
        save_bible(bible, target_path=bible_path, expected_version=old_version)
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail={"error_code": "ERR_BIBLE_VERSION_CONFLICT", "message": str(exc)}) from exc
    return {"prop": prop.model_dump(mode="json"), "bible_version": bible.bible_version}


@router.post("/objects/drafts")
def create_object_draft(project_id: str, req: ObjectDraftRequest) -> Dict[str, Any]:
    result = _save_object_draft(project_id, req)
    if result["prop"]["approval_status"] != "draft":
        raise HTTPException(status_code=500, detail="Object draft save returned an unexpected lifecycle state.")
    return result


@router.put("/objects/drafts/{prop_id}")
def update_object_draft(project_id: str, prop_id: str, req: ObjectDraftRequest) -> Dict[str, Any]:
    return _save_object_draft(project_id, req, expected_prop_id=prop_id)


@router.post("/objects/{prop_id}/propose-canon")
def propose_object_to_canon(project_id: str, prop_id: str, req: ProposeCanonRequest) -> Dict[str, Any]:
    bible, bible_path = _load_object_bible(project_id)
    prop = bible.props.get(prop_id)
    if not prop:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_OBJECT_NOT_FOUND", "message": f"Object '{prop_id}' was not found in this project."})
    if prop.approval_status != "draft":
        raise HTTPException(status_code=409, detail={"error_code": "ERR_OBJECT_NOT_DRAFT", "message": "Only a saved draft can be proposed to Canon."})
    proposal = CanonMutationProposal(
        proposal_id=f"prop_object_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        target_type="prop",
        target_id=prop_id,
        change_description=req.change_description or f"Approve the reviewed object identity '{prop.name}' for project Canon.",
        proposed_changes={"approval_status": "approved"},
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        result = propose_canon_mutation(bible_path, proposal)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_OBJECT_CANON_PROPOSAL_FAILED", "message": str(exc)}) from exc
    return {"status": "proposal_created", "proposal": result.model_dump(mode="json"), "message": "Object proposal saved. It becomes approved Canon only after the proposal is explicitly applied."}


@router.post("/characters/profiles", response_model=CharacterIdentityProfile)
def create_or_update_character_profile(project_id: str, profile: CharacterIdentityProfile) -> CharacterIdentityProfile:
    """Saves or updates a CharacterIdentityProfile."""
    profile.project_id = project_id
    store = get_creative_profile_store()
    return store.save_character_profile(profile)


@router.get("/characters/profiles", response_model=List[CharacterIdentityProfile])
def list_character_profiles(project_id: str, include_archived: bool = Query(default=False)) -> List[CharacterIdentityProfile]:
    """Lists all character identity profiles for a project."""
    store = get_creative_profile_store()
    return store.list_character_profiles(project_id=project_id, include_archived=include_archived)


@router.get("/characters/profiles/{profile_id}", response_model=CharacterIdentityProfile)
def get_character_profile(project_id: str, profile_id: str) -> CharacterIdentityProfile:
    """Retrieves an existing CharacterIdentityProfile."""
    store = get_creative_profile_store()
    prof = store.get_character_profile(project_id, profile_id)
    if not prof:
        prof = store.get_character_profile_by_character_id(project_id, profile_id)
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")
    return prof


@router.post("/characters/profiles/{profile_id}/approve", response_model=CharacterIdentityProfile)
def approve_character_profile(project_id: str, profile_id: str) -> CharacterIdentityProfile:
    """Approves a CharacterIdentityProfile."""
    store = get_creative_profile_store()
    try:
        return store.approve_character_profile(project_id, profile_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")


@router.post("/characters/profiles/{profile_id}/archive", response_model=CharacterIdentityProfile)
def archive_character_profile(project_id: str, profile_id: str) -> CharacterIdentityProfile:
    """Archives a CharacterIdentityProfile."""
    store = get_creative_profile_store()
    try:
        return store.archive_character_profile(project_id, profile_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")


@router.post("/characters/profiles/{profile_id}/sheet-plan", response_model=CharacterSheetPlan)
def generate_character_sheet_plan(project_id: str, profile_id: str) -> CharacterSheetPlan:
    """Constructs a turnaround character sheet plan with front, 3/4, full body, and expressions."""
    store = get_creative_profile_store()
    prof = store.get_character_profile(project_id, profile_id)
    if not prof:
        prof = store.get_character_profile_by_character_id(project_id, profile_id)
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")

    analyzer = CharacterAnalyzer(get_registry())
    return analyzer.generate_sheet_plan(prof)


@router.post("/characters/profiles/{profile_id}/generate-sheet", response_model=TurnaroundSheetResult)
def generate_character_turnaround_sheet(
    project_id: str,
    profile_id: str,
    req: Optional[SheetGenerateRequest] = None,
) -> TurnaroundSheetResult:
    """
    Executes turnaround sheet generation across all canonical view specs for the character.
    Renders each view through CreativeOrchestrator and verifies identity QA scores.
    """
    store = get_creative_profile_store()
    prof = store.get_character_profile(project_id, profile_id)
    if not prof:
        prof = store.get_character_profile_by_character_id(project_id, profile_id)
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")

    if req is None:
        req = SheetGenerateRequest()

    registry = get_registry()
    analyzer = CharacterAnalyzer(registry)
    plan = analyzer.generate_sheet_plan(prof)
    try:
        orchestrator = CreativeOrchestrator(registry=registry)
    except GenerationProviderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": str(exc)})

    view_results: List[SheetViewResult] = []
    all_passed = True

    for view in plan.views:
        action_text = view.prompt
        shot_text = "Turnaround model sheet reference, clean white background"
        panel_tag = f"turnaround_{view.view_type}"

        try:
            gen_res = orchestrator.generate(
                project_id=project_id,
                scene_action=action_text,
                shot_type=shot_text,
                style_profile_id=req.style_profile_id,
                character_profile_ids=[prof.profile_id],
                panel_id=panel_tag,
                scene_id="turnaround_sheet",
                max_attempts=req.max_attempts,
            )
            score = round(gen_res.qa_result.overall_score, 2) if gen_res.qa_result.overall_score is not None else None
            if not gen_res.qa_result.passed:
                all_passed = False

            meta = registry.get_asset(gen_res.output_asset_id) if gen_res.output_asset_id else None
            sha256_hash = meta.content_sha256 if meta else ""
            notes = [f.message for f in gen_res.qa_result.findings] if gen_res.qa_result.findings else [gen_res.qa_result.score_explanation]

            view_results.append(SheetViewResult(
                view_role=view.view_type,
                label=view.view_type.replace("_", " ").title(),
                description=view.prompt,
                camera_angle="Eye-level",
                framing="Turnaround reference",
                asset_id=gen_res.output_asset_id or "",
                content_sha256=sha256_hash,
                qa_score=score,
                fidelity_notes=notes,
            ))
        except Exception as e:
            all_passed = False
            view_results.append(SheetViewResult(
                view_role=view.view_type,
                label=view.view_type.replace("_", " ").title(),
                description=f"Generation failed: {str(e)}",
                camera_angle="Eye-level",
                framing="Turnaround reference",
                asset_id="",
                content_sha256="",
                qa_score=0.0,
                fidelity_notes=[f"Generation error: {str(e)}"],
            ))

    return TurnaroundSheetResult(
        character_id=prof.character_id,
        profile_id=prof.profile_id,
        views=view_results,
        total_views=len(view_results),
        all_passed_qa=all_passed,
    )


@router.post("/characters/profiles/{profile_id}/propose-canon")
def propose_character_invariants_to_canon(project_id: str, profile_id: str, req: ProposeCanonRequest) -> Dict[str, Any]:
    """
    Submits extracted character invariants to the Story Bible Canon proposal queue.
    Requires explicit user review/approval via the Canon workflow before altering canonical facts.
    """
    store = get_creative_profile_store()
    prof = store.get_character_profile(project_id, profile_id)
    if not prof:
        prof = store.get_character_profile_by_character_id(project_id, profile_id)
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character profile '{profile_id}' not found.")

    p_dir = PROJECT_ROOT / "runs" / project_id
    bible_path = p_dir / "bible.json"
    if not bible_path.exists():
        # Fallback to default_project if specific project directory has not yet saved bible
        fallback_path = PROJECT_ROOT / "runs" / "default_project" / "bible.json"
        if fallback_path.exists():
            bible_path = fallback_path
        else:
            p_dir.mkdir(parents=True, exist_ok=True)
            initial_bible = create_canonical_nour_bible(project_id)
            save_bible(initial_bible, target_path=bible_path)

    proposal = CanonMutationProposal(
        proposal_id=f"prop_char_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        target_type="character",
        target_id=prof.character_id,
        change_description=req.change_description or f"Update canonical visual invariants for '{prof.name}' from reference analysis.",
        proposed_changes={
            "visual_invariants": prof.identity_invariants,
            "forbidden_drift": prof.forbidden_drift,
            "prompt_identity_core": prof.prompt_identity_core,
            "approved_references": [r.asset_id for r in prof.references],
        },
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    result = propose_canon_mutation(bible_path, proposal)
    return {
        "status": "proposal_created",
        "proposal": result.model_dump(),
        "message": f"Proposed {len(prof.identity_invariants)} invariants for '{prof.name}' to Canon. Awaiting review."
    }


# =============================================================================
# Combined Generation & QA Refinement Endpoints
# =============================================================================

@router.post("/generate", response_model=CreativeGenerationResult)
def generate_with_creative_profiles(project_id: str, req: CreativeGenerateRequest) -> CreativeGenerationResult:
    """
    Runs multi-reference generation conditioned on Style Profile, Character Profile(s), and Scene.
    Performs StyleIdentityQA and triggers single-pass targeted refinement if needed.
    """
    registry = get_registry()
    try:
        orchestrator = CreativeOrchestrator(registry=registry)
        return orchestrator.generate(
            project_id=project_id,
            scene_action=req.scene_action,
            shot_type=req.shot_type,
            style_profile_id=req.style_profile_id,
            character_profile_ids=req.character_profile_ids,
            reference_set=req.reference_set,
            panel_id=req.panel_id,
            scene_id=req.scene_id,
            max_attempts=req.max_attempts,
            dimensions=req.dimensions,
            aspect_ratio=req.aspect_ratio,
            composition_notes=req.composition_notes,
            lighting_intent=req.lighting_intent,
        )
    except GenerationProviderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Creative generation failed: {str(exc)}"
        )


@router.get("/capabilities", response_model=ProviderCapabilities)
def get_generation_capabilities(project_id: str) -> ProviderCapabilities:
    """
    Returns declared and verified capabilities of the active image provider.
    Honest report: probabilistic reference conditioning, not guaranteed identity lock.
    """
    try:
        orchestrator = CreativeOrchestrator(registry=get_registry())
    except GenerationProviderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": str(exc)})
    return orchestrator.adapter.get_capabilities()


# =============================================================================
# Universe Builder / AI Creative Director Endpoints
# =============================================================================

from app.creative.schemas import (
    CreativeMode,
    CreativePackage,
    ValidationResult,
    CreativeContractsPackage,
    LocationSpec,
)
from app.creative.service import CreativeDirectorService, CreativeProviderUnavailableError, CreativeProviderError
from app.creative.prompt_compiler import CreativePromptCompiler

universe_router = APIRouter(prefix="/creative", tags=["AI Creative Director & Universe Builder"])


class DevelopCreativeRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to develop universe for")
    user_prompt: str = Field(..., min_length=1, description="Natural language creative brief or universe description")
    mode: CreativeMode = Field(default=CreativeMode.FULL_PRODUCTION_BIBLE, description="Operational mode for pipeline")
    visual_references: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional visual reference descriptors")
    offline_mode: Optional[bool] = Field(default=None, description="Force deterministic local synthesis without API spend")


class SaveLocationRequest(BaseModel):
    expected_package_version: int = Field(..., ge=1)
    expected_location_version: Optional[int] = Field(default=None, ge=1)
    location: LocationSpec


def _check_location_parent(pkg: CreativePackage, location_id: str, parent_id: Optional[str]) -> None:
    if not parent_id:
        return
    if parent_id == location_id or parent_id not in pkg.world_bible.locations:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Parent location must be a different existing location.")
    visited = {location_id}
    current_id: Optional[str] = parent_id
    while current_id:
        if current_id in visited:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Location parent links cannot contain a cycle.")
        visited.add(current_id)
        parent = pkg.world_bible.locations.get(current_id)
        current_id = parent.parent_location_id if parent else None


class ApproveCreativeCanonRequest(BaseModel):
    project_id: str = Field(..., description="Project ID to commit approved proposals for")
    character_ids_to_commit: Optional[List[str]] = Field(default=None, description="List of character IDs to commit (all if omitted)")
    commit_style: bool = Field(default=True, description="Whether to commit visual style profile to canon")


class CompilePromptRequest(BaseModel):
    project_id: str = Field(..., description="Project ID containing compiled contracts")
    character_id: Optional[str] = Field(default=None, description="Character ID to inject invariants for")
    scene_description: str = Field(..., min_length=1, description="Description of the panel scene or moment")
    emotion: str = Field(default="neutral", description="Emotional state of character in panel")
    outfit_id: Optional[str] = Field(default=None, description="Specific outfit variant ID")
    is_action_shot: bool = Field(default=False, description="Whether this panel is high dynamic action")


class AddCreativeCharacterRequest(BaseModel):
    project_id: str = Field(..., description="Project ID")
    name: str = Field(..., min_length=1, description="Character display name")
    role: str = Field(default="Supporting Character", description="Role in story")
    age_range: str = Field(default="18-25", description="Age range")
    narrative_function: str = Field(default="", description="Narrative purpose in story")
    visual_invariants: List[str] = Field(default_factory=list, description="Mandatory visual traits")
    garments: List[str] = Field(default_factory=list, description="Default wardrobe items")
    commit_to_canon: bool = Field(default=True, description="Directly commit to Story Bible canon")


@universe_router.post("/character/add", response_model=CreativePackage)
def add_character_to_universe(req: AddCreativeCharacterRequest):
    """
    Creates an individual character in the Creative Package and optionally commits
    it to authoritative Story Bible canon so Agent Studio can use it immediately.
    """
    from app.creative.schemas import CharacterIdentityProfile as UniverseCharacterProfile, OutfitVariant
    service = CreativeDirectorService.get_instance()
    char_id = req.name.lower().replace(" ", "_")
    invariants = req.visual_invariants or [f"Distinctive appearance for {req.name}"]
    garments = req.garments or ["Standard field attire"]

    char_profile = UniverseCharacterProfile(
        character_id=char_id,
        name=req.name,
        role=req.role,
        narrative_function=req.narrative_function or f"{req.role} in {req.project_id}.",
        age_range=req.age_range,
        external_goal="Pursue personal objectives aligned with canon.",
        internal_need="Maintain authentic character growth.",
        core_fear="Loss of agency and control.",
        wound_or_ghost="A defining moment in early history.",
        core_contradiction="Outward actions contrast with private convictions.",
        misbelief="Must rely solely on individual resilience.",
        stakes_personal="Personal reputation and survival.",
        strengths=["Steadfast resolve", "Quick reflexes"],
        flaws=["Cautious", "Guarded"],
        coping_mechanisms=["Maintains strict routines"],
        vulnerabilities=["Over-commitment to past promises"],
        voice_and_speech="Direct, purposeful, and clear.",
        values_and_morals=["Uphold established trust"],
        pressure_response="Assesses facts methodically under threat.",
        backstory=f"Established character in {req.project_id}.",
        secrets=[],
        arc_checkpoints=[],
        silhouette_and_proportions="Distinctive individual silhouette with grounded posture.",
        face_design=f"Expressive facial features for {req.name}.",
        hair_silhouette_and_color=invariants[0] if "hair" in invariants[0].lower() else "Natural linework styling.",
        distinctive_features=invariants[:3],
        visual_invariants=invariants,
        base_outfit=OutfitVariant(
            outfit_id=f"outfit_{char_id}_base",
            name=f"{req.name} Default Attire",
            description=f"Standard garments for {req.name}",
            garments=garments,
            colors=["Charcoal", "Slate", "White accent"],
            is_base=True,
        ),
        palette_and_values=["#1e293b", "#475569", "#f8fafc"],
        posture_and_movement="Grounded athletic posture with observant stance.",
        visual_motifs=invariants[:2],
        allowed_variations=["Standard clothing variations"],
        forbidden_visual_drift=[f"Never omit {invariants[0]}"],
        approval_status="approved" if req.commit_to_canon else "draft",
        version=1,
    )

    try:
        updated_pkg = service.add_character_to_universe(
            project_id=req.project_id,
            character=char_profile,
            commit_to_canon=req.commit_to_canon,
        )
        return updated_pkg
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add character: {str(exc)}",
        )


@universe_router.post("/develop", response_model=CreativePackage)
def develop_universe(req: DevelopCreativeRequest):
    """
    Execute the 16-stage AI Creative Director pipeline on a user brief.
    Synthesizes story bible, character profiles, relationship graph, world bible,
    narrative structure, style profile, sheet plans, and generation contracts.
    """
    service = CreativeDirectorService.get_instance()
    try:
        package = service.develop_universe(
            project_id=req.project_id,
            user_prompt=req.user_prompt,
            mode=req.mode,
            visual_references=req.visual_references,
            offline_mode=req.offline_mode,
        )
        return package
    except CreativeProviderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error_code": "ERR_CREATIVE_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except CreativeProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "ERR_CREATIVE_PROVIDER_FAILED", "message": str(exc)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Creative Director synthesis failed: {str(exc)}",
        )


@universe_router.get("/package/{project_id}", response_model=Optional[CreativePackage])
def get_universe_package(project_id: str) -> Optional[CreativePackage]:
    """Retrieve the current persisted Creative Package for a project."""
    service = CreativeDirectorService.get_instance()
    return service.get_package(project_id)


@universe_router.put("/package/{project_id}/locations/{location_id}", response_model=CreativePackage)
def save_universe_location(project_id: str, location_id: str, req: SaveLocationRequest) -> CreativePackage:
    """Create or update one reusable location with optimistic version checks."""
    service = CreativeDirectorService.get_instance()
    pkg = service.get_package(project_id)
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Creative package not found for project '{project_id}'.")
    if pkg.version != req.expected_package_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Creative package changed; current version is {pkg.version}.")
    if req.location.location_id != location_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The location ID in the path must match the location payload.")

    current = pkg.world_bible.locations.get(location_id)
    _check_location_parent(pkg, location_id, req.location.parent_location_id)
    location = req.location
    if current:
        if req.expected_location_version != current.version:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Location changed; current version is {current.version}.")
        prior_snapshot = current.model_dump(mode="json", exclude={"version_history"})
        location = location.model_copy(update={
            "version": current.version + 1,
            "version_history": (current.version_history + [prior_snapshot])[-20:],
        })
    else:
        if req.expected_location_version is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This location no longer exists. Reload the project before saving.")
        location = location.model_copy(update={"version": 1, "version_history": []})

    pkg.world_bible.locations[location_id] = location
    pkg.world_bible.version += 1
    pkg.version += 1
    pkg.package_hash = ""
    service.save_package(pkg)
    return pkg


@universe_router.delete("/package/{project_id}/locations/{location_id}", response_model=CreativePackage)
def delete_universe_location(project_id: str, location_id: str, expected_package_version: int = Query(..., ge=1)) -> CreativePackage:
    """Remove an unreferenced location without leaving dangling story links."""
    service = CreativeDirectorService.get_instance()
    pkg = service.get_package(project_id)
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Creative package not found for project '{project_id}'.")
    if pkg.version != expected_package_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Creative package changed; current version is {pkg.version}.")
    if location_id not in pkg.world_bible.locations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location '{location_id}' was not found.")
    if any(scene.location_id == location_id for chapter in pkg.narrative_structure.chapters for scene in chapter.scene_candidates):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This location is used by the story outline. Update those scenes before deleting it.")
    if any(location.parent_location_id == location_id for other_id, location in pkg.world_bible.locations.items() if other_id != location_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Other locations use this as their parent. Reassign them before deleting it.")

    del pkg.world_bible.locations[location_id]
    pkg.world_bible.version += 1
    pkg.version += 1
    pkg.package_hash = ""
    service.save_package(pkg)
    return pkg


@universe_router.post("/validate/{project_id}", response_model=ValidationResult)
def validate_universe_coherence(project_id: str):
    """
    Run deterministic cross-document coherence validator against
    the project's Creative Package and active Story Bible.
    """
    service = CreativeDirectorService.get_instance()
    pkg = service.get_package(project_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative package not found for project '{project_id}'",
        )
    active_bible = service._load_existing_bible(project_id)
    val_result = service.validator.validate(pkg, active_bible=active_bible)
    pkg.validation = val_result
    service.save_package(pkg)
    return val_result


@universe_router.post("/approve")
def approve_universe_canon_mutation(req: ApproveCreativeCanonRequest):
    """
    Approve agent proposals and commit them into the authoritative Story Bible,
    producing an immutable new CanonSnapshot with updated canon hash.
    """
    service = CreativeDirectorService.get_instance()
    try:
        updated_bible = service.approve_canon_mutation(
            project_id=req.project_id,
            character_ids_to_commit=req.character_ids_to_commit,
            commit_style=req.commit_style,
        )
        return {
            "success": True,
            "project_id": req.project_id,
            "bible_version": updated_bible.bible_version,
            "canon_hash": updated_bible.canon_hash,
            "characters_count": len(updated_bible.characters),
            "style_version": updated_bible.style.version,
            "message": "Creative proposals successfully committed to authoritative Story Bible canon.",
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit canon mutation: {str(exc)}",
        )


@universe_router.get("/contracts/{project_id}", response_model=CreativeContractsPackage)
def get_universe_contracts(project_id: str):
    """Retrieve downstream machine-readable generation contracts."""
    service = CreativeDirectorService.get_instance()
    pkg = service.get_package(project_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative package not found for project '{project_id}'",
        )
    return pkg.contracts


@universe_router.post("/compile-prompt")
def compile_universe_prompt(req: CompilePromptRequest):
    """Compile production panel prompt from downstream creative contracts and character profile."""
    service = CreativeDirectorService.get_instance()
    pkg = service.get_package(req.project_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Creative package not found for project '{req.project_id}'",
        )

    char_profile = None
    if req.character_id and req.character_id in pkg.characters:
        char_profile = pkg.characters[req.character_id]

    positive_prompt = CreativePromptCompiler.compile_panel_prompt(
        contracts=pkg.contracts,
        character=char_profile,
        scene_description=req.scene_description,
        emotion=req.emotion,
        outfit_id=req.outfit_id,
        is_action_shot=req.is_action_shot,
    )
    negative_prompt = CreativePromptCompiler.compile_negative_prompt(
        contracts=pkg.contracts,
        character=char_profile,
    )

    return {
        "project_id": req.project_id,
        "character_id": req.character_id,
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
    }

