"""Manual editor endpoints backed by immutable ArtifactStore page revisions."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from app.config import PROJECT_ROOT, InkLoopConfig
from app.api.routers.assets import get_registry
from app.editor.models import CreatePageRequest, EditablePageDocument, EditorLayer, LayerKind, SavePageRequest, RestorePageRequest, LayerPreviewRequest
from app.editor.store import PageDocumentStore, PageNotFound, PageRevisionConflict
from app.canvas.engine import CanvasEngine
from app.canvas.templates import get_template
from app.image_canvas.engine import ImageCanvasIntegrationEngine
from app.image_canvas.models import PlacementSpec
from app.contracts.geometry import FitMode, Transform2D, AssetFormat
from app.contracts.engine import ExportParams
from app.canvas.compositor import FinalCompositor
from app.export.delivery import ExportDeliveryEngine
from app.agent.registry import CapabilityRegistry
from app.agent.schemas import ToolCall

router = APIRouter(prefix="/editor/pages", tags=["Manual Page Editor"])
_store: PageDocumentStore | None = None

def get_page_store() -> PageDocumentStore:
    global _store
    if _store is None:
        root = PROJECT_ROOT / "runs"
        _store = PageDocumentStore(root / "page_documents.db", get_registry())
    return _store

def _not_found(exc: Exception):
    raise HTTPException(status_code=404, detail={"message": str(exc)})

@router.post("", status_code=201)
def create_page(request: CreatePageRequest):
    """Create an editable page from a real canonical E2 layout."""
    candidate = EditablePageDocument(page_id=request.layout.page_spec.page_id, project_id=request.project_id, layout=request.layout, source_artifact_ids=request.source_artifact_ids)
    validation = validate_page(candidate)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"message": "E2 layout is not valid for editing.", "diagnostics": validation["diagnostics"]})
    registry = get_registry()
    for asset_id in request.source_artifact_ids:
        asset = registry.get_asset(asset_id)
        if not asset or asset.project_id != request.project_id:
            raise HTTPException(status_code=422, detail={"message": f"Unknown or cross-project asset {asset_id}"})
        registry.resolve_asset(asset_id, verify_integrity=True)
    page_id = request.layout.page_spec.page_id
    layers = [EditorLayer(layer_id=f"layer_{slot.panel_id}", kind=LayerKind.PANEL, label=slot.panel_id, z_index=slot.z_index, panel_id=slot.panel_id) for slot in request.layout.panel_slots]
    doc = EditablePageDocument(page_id=page_id, project_id=request.project_id, layout=request.layout, layers=layers, source_artifact_ids=request.source_artifact_ids)
    try:
        return get_page_store().create(doc).model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)})

@router.get("")
def list_pages(project_id: str | None = None):
    return get_page_store().list_pages(project_id)

@router.get("/deleted", summary="List recoverable soft-deleted pages")
def list_deleted_pages(project_id: str | None = None):
    return get_page_store().list_deleted_pages(project_id)

@router.delete("/{page_id}", summary="Remove a page from the active editor list without deleting revisions")
def delete_page(page_id: str):
    try:
        get_page_store().delete(page_id)
        return {"page_id": page_id, "deleted": True, "revisions_retained": True}
    except PageNotFound as exc:
        _not_found(exc)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)})

@router.post("/{page_id}/restore-deleted", summary="Restore a soft-deleted page")
def restore_deleted_page(page_id: str):
    try:
        get_page_store().restore_deleted(page_id)
        return {"page_id": page_id, "deleted": False}
    except PageNotFound as exc:
        _not_found(exc)

@router.post("/{page_id}/layers/{layer_id}/preview", summary="Render an image layer through E3 without changing its source")
def preview_image_layer(page_id: str, layer_id: str, request: LayerPreviewRequest):
    try:
        doc = get_page_store().get(page_id)
    except PageNotFound as exc:
        _not_found(exc)
    layer = next((item for item in doc.layers if item.layer_id == layer_id and item.kind == LayerKind.IMAGE), None)
    if not layer or not layer.source_asset_id:
        raise HTTPException(status_code=404, detail={"message": "Image layer or registered source is missing."})
    registry = get_registry()
    try:
        source = registry.resolve_asset(layer.source_asset_id, verify_integrity=True)
        if layer.source_sha256 and source.metadata.content_sha256 != layer.source_sha256:
            raise HTTPException(status_code=409, detail={"message": "The registered source hash differs from this layer's recorded provenance."})
        layout = request.layout or doc.layout
        template = get_template(layout.template_id)
        template.validate_layout(layout, strict=True)
        slot = layout.get_panel(layer.panel_id or "")
        if slot is None:
            raise HTTPException(status_code=422, detail={"message": "Image layer references a panel that no longer exists."})
        fit = FitMode(layer.fit_mode)
        placed = ImageCanvasIntegrationEngine.place_artwork_in_slot(
            slot,
            PlacementSpec(target_panel_id=slot.panel_id, source_artifact_id=layer.source_asset_id,
                fit_mode=fit, manual_transform=request.transform, clip_to_polygon=True),
            canvas_spec=layout.canvas_spec,
            asset_registry=registry,
        )
        return Response(content=placed.output_image_bytes, media_type="image/png", headers={"X-Source-SHA256": placed.source_content_hash, "X-Rendered-SHA256": placed.output_content_hash})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": f"E3 preview failed: {exc}"})

@router.get("/{page_id}")
def get_page(page_id: str):
    try:
        return get_page_store().get(page_id).model_dump(mode="json")
    except PageNotFound as exc:
        _not_found(exc)

@router.get("/{page_id}/revisions")
def list_revisions(page_id: str):
    try:
        return get_page_store().revisions(page_id)
    except PageNotFound as exc:
        _not_found(exc)

@router.put("/{page_id}")
def save_page(page_id: str, request: SavePageRequest):
    try:
        validation = validate_page(request.document)
        if not validation["valid"]:
            raise HTTPException(status_code=422, detail={"message": "Invalid page geometry or asset references cannot be saved.", "diagnostics": validation["diagnostics"]})
        doc = get_page_store().save(page_id, request.expected_revision, request.document)
        return doc.model_dump(mode="json")
    except HTTPException:
        raise
    except PageRevisionConflict as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "current_revision": exc.current_revision})
    except PageNotFound as exc:
        _not_found(exc)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)})

@router.post("/{page_id}/restore")
def restore_page(page_id: str, request: RestorePageRequest):
    try:
        return get_page_store().restore(page_id, request.expected_revision, request.revision_to_restore).model_dump(mode="json")
    except PageRevisionConflict as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "current_revision": exc.current_revision})
    except PageNotFound as exc:
        _not_found(exc)

@router.post("/validate", summary="Validate edited E2 page geometry")
def validate_page(doc: EditablePageDocument) -> Dict[str, Any]:
    try:
        template = get_template(doc.layout.template_id)
        diagnostics = template.validate_layout(doc.layout, strict=False)
        # Reading order is explicit and must cover each panel exactly once.
        expected = {panel.panel_id for panel in doc.layout.panel_slots}
        actual = doc.layout.reading_order_panel_ids
        if len(actual) != len(set(actual)) or set(actual) != expected:
            diagnostics.append({"severity": "error", "code": "ERR_READING_ORDER", "message": "Reading order must contain each panel exactly once."})
        registry = get_registry()
        for layer in doc.layers:
            font_asset_id = layer.metadata.get("font_asset_id") if layer.kind == LayerKind.TEXT else None
            if font_asset_id:
                try:
                    font_asset = registry.resolve_asset(font_asset_id, verify_integrity=True)
                    if font_asset.metadata.project_id != doc.project_id or font_asset.metadata.asset_type.value != "font_file":
                        diagnostics.append({"severity": "error", "code": "ERR_FONT_ASSET_SCOPE", "message": f"Text layer {layer.layer_id} references a non-font or cross-project asset.", "layer_id": layer.layer_id})
                except Exception as exc:
                    diagnostics.append({"severity": "error", "code": "ERR_FONT_ASSET_UNAVAILABLE", "message": f"Text layer {layer.layer_id}: font asset could not be verified ({exc}).", "layer_id": layer.layer_id})
            if layer.kind != LayerKind.IMAGE or not layer.source_asset_id:
                continue
            try:
                asset = registry.resolve_asset(layer.source_asset_id, verify_integrity=True)
                if layer.source_sha256 and asset.metadata.content_sha256 != layer.source_sha256:
                    diagnostics.append({"severity": "error", "code": "ERR_ASSET_HASH_MISMATCH", "message": f"Layer {layer.layer_id} source hash no longer matches its registered asset.", "layer_id": layer.layer_id})
            except Exception as exc:
                diagnostics.append({"severity": "error", "code": "ERR_ASSET_UNAVAILABLE", "message": f"Layer {layer.layer_id}: registered source could not be verified ({exc}).", "layer_id": layer.layer_id})
        return {"valid": not any(getattr(item, "severity", item.get("severity") if isinstance(item, dict) else None) == "error" for item in diagnostics), "diagnostics": [item.model_dump() if hasattr(item, "model_dump") else item for item in diagnostics]}
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)})


class PanelGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Action, camera angle, and scene emotion for this panel")
    character_ids: List[str] = Field(default_factory=list, description="IDs of characters appearing in this panel")
    location_id: Optional[str] = Field(None, description="Location ID from Story Bible")
    style_profile_id: Optional[str] = Field(None, description="Style profile ID")
    style_profile_version: Optional[int] = Field(None, description="Expected style profile version")
    camera_angle: Optional[str] = Field("medium shot, eye level", description="Cinematic camera framing")
    fit_mode: Literal["cover", "contain"] = Field("cover", description="Image layer fitting mode")
    is_simulated: Optional[bool] = Field(None, description="Force simulation mode")


@router.post("/{page_id}/panels/{panel_id}/generate", summary="Direct in-panel image generation and layer placement")
def generate_panel_art(page_id: str, panel_id: str, req: PanelGenerateRequest):
    """
    Direct in-panel generation:
    1. Validates panel slot in page layout
    2. Compiles prompt with strict negative text invariants
    3. Runs image generation
    4. Registers image artifact in AssetRegistry
    5. Injects/updates image layer in EditablePageDocument and persists revision
    6. Returns truthful Critic report and updated page document
    """
    try:
        doc = get_page_store().get(page_id)
    except PageNotFound as exc:
        _not_found(exc)

    slot = doc.layout.get_panel(panel_id)
    if slot is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Panel '{panel_id}' does not exist in page '{page_id}' layout."}
        )

    registry = get_registry()
    if req.is_simulated is not True and not InkLoopConfig.load().has_credentials:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": "In-panel generation needs provider credentials. Choose explicit simulation only for a labeled test draft."},
        )
    generation_arguments = {
        "project_id": doc.project_id,
        "prompt": req.prompt.strip(),
        "panel_id": panel_id,
        "scene_id": doc.project_id,
    }
    if req.character_ids:
        # An explicit selection is authoritative. If the user selected no cast,
        # omit the field so the shared context builder can resolve exact canon
        # names from the prompt without guessing by appearance.
        generation_arguments["character_ids"] = req.character_ids
    for key, value in {
        "location_id": req.location_id,
        "style_profile_id": req.style_profile_id,
        "style_profile_version": req.style_profile_version,
        "camera_angle": req.camera_angle,
    }.items():
        if value is not None:
            generation_arguments[key] = value
    rect = getattr(slot, "rect", None)
    if rect is not None:
        generation_arguments["width"] = max(1, round(rect.width))
        generation_arguments["height"] = max(1, round(rect.height))

    generation = CapabilityRegistry().dispatch(
        ToolCall(
            call_id=f"editor_generate_{page_id}_{panel_id}_{doc.revision}",
            tool_id="generation.generate_image",
            arguments=generation_arguments,
        ),
        {"project_id": doc.project_id, "offline_mode": req.is_simulated is True},
    )
    if generation.status != "success" or not generation.output.get("asset_id"):
        if generation.error and "ERR_IMAGE_PROVIDER_UNAVAILABLE" in generation.error:
            raise HTTPException(status_code=503, detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": "In-panel generation needs provider credentials. Choose explicit simulation only for a labeled test draft."})
        raise HTTPException(status_code=502, detail={"message": generation.error or "Image generation did not return a registered artwork asset."})
    asset_meta = registry.get_asset(generation.output["asset_id"])
    if asset_meta is None:
        raise HTTPException(status_code=502, detail={"message": "Generated image asset was not found in the project registry."})

    # Create or update Image layer for this panel
    layer_id = f"img_layer_{panel_id}"
    existing_idx = next((i for i, l in enumerate(doc.layers) if l.panel_id == panel_id and l.kind == LayerKind.IMAGE), None)

    image_layer = EditorLayer(
        layer_id=layer_id,
        kind=LayerKind.IMAGE,
        label=f"Artwork: {panel_id}",
        panel_id=panel_id,
        source_asset_id=asset_meta.asset_id,
        source_sha256=asset_meta.content_sha256,
        fit_mode=req.fit_mode,
        z_index=0,
    )

    if existing_idx is not None:
        doc.layers[existing_idx] = image_layer
    else:
        # Insert image layer right after the panel layer or at start
        panel_idx = next((i for i, l in enumerate(doc.layers) if l.panel_id == panel_id and l.kind == LayerKind.PANEL), None)
        if panel_idx is not None:
            doc.layers.insert(panel_idx + 1, image_layer)
        else:
            doc.layers.append(image_layer)

    if asset_meta.asset_id not in doc.source_artifact_ids:
        doc.source_artifact_ids.append(asset_meta.asset_id)

    # Validate and save updated page document
    expected_rev = doc.revision
    try:
        saved_doc = get_page_store().save(page_id, expected_rev, doc)
    except PageRevisionConflict as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "current_revision": exc.current_revision})

    return {
        "success": True,
        "page_id": page_id,
        "panel_id": panel_id,
        "new_revision": saved_doc.revision,
        "asset_id": asset_meta.asset_id,
        "image_url": f"/api/v1/assets/{asset_meta.asset_id}/file",
        "generation_provenance": {
            "character_ids": generation.output.get("character_ids", []),
            "character_reference_asset_ids": generation.output.get("character_reference_asset_ids", []),
            "style_profile_id": req.style_profile_id,
            "style_profile_version": req.style_profile_version,
            "style_reference_asset_ids": generation.output.get("style_reference_asset_ids", []),
            "reference_image_roles": generation.output.get("reference_image_roles", []),
            "visual_verification_status": generation.output.get("visual_verification_status", "NOT_RUN"),
            "context_fingerprint": generation.output.get("context_fingerprint"),
        },
        "updated_page": saved_doc.model_dump(mode="json"),
    }


class ExportPageRequest(BaseModel):
    target_format: Literal["pdf", "png"] = "pdf"
    reading_direction: Literal["rtl", "ltr"] = "rtl"


@router.post("/{page_id}/composite", summary="Render high-DPI full-page composite")
def composite_page(page_id: str):
    try:
        doc = get_page_store().get(page_id)
    except PageNotFound as exc:
        _not_found(exc)

    registry = get_registry()
    compositor = FinalCompositor()
    output = compositor.composite_page_document(doc, registry)

    return {
        "success": True,
        "page_id": page_id,
        "revision": doc.revision,
        "composite_artifact_id": output.composite_page_artifact_id,
        "image_url": f"/api/v1/assets/{output.composite_page_artifact_id}/file",
        "output_file_path": output.output_file_path,
        "dimensions": {"width": output.dimensions.width, "height": output.dimensions.height},
        "dpi": output.dpi,
        "layer_count": output.layer_count,
        "sha256": output.sha256,
    }


@router.post("/{page_id}/export", summary="Compile print-ready PDF or high-res package")
def export_page(page_id: str, request: ExportPageRequest = ExportPageRequest()):
    try:
        doc = get_page_store().get(page_id)
    except PageNotFound as exc:
        _not_found(exc)

    registry = get_registry()
    compositor = FinalCompositor()
    comp_output = compositor.composite_page_document(doc, registry)

    target_fmt = AssetFormat.PDF if request.target_format == "pdf" else AssetFormat.PNG
    export_engine = ExportDeliveryEngine()
    params = ExportParams(
        project_id=doc.project_id,
        page_composite_artifact_ids=[comp_output.composite_page_artifact_id],
        target_format=target_fmt,
    )

    delivery = export_engine.export_delivery(
        params,
        asset_registry=registry,
        reading_direction=request.reading_direction,
    )

    return {
        "success": True,
        "page_id": page_id,
        "export_artifact_id": delivery.export_artifact_id,
        "file_path": delivery.file_path,
        "download_url": f"/api/v1/assets/{delivery.export_artifact_id}/file",
        "target_format": delivery.target_format.value,
        "page_count": delivery.page_count,
        "byte_size": delivery.byte_size,
        "sha256": delivery.sha256,
    }

