"""
Generation Studio & Batch Orchestrator Router.
Connects the UI to pure-code context compilation, multi-panel generation orchestration,
bounded retry engines, and verifiable batch lifecycles.
"""
import json
import hashlib
import re
import threading
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import (
    SceneSpec,
    BatchSpec,
    BatchSummary,
    PanelContextPacket,
)
from app.context_builder import build_panel_context_packet
from app.orchestrator import BatchOrchestrator
from app.image_adapter import (
    MetaImageGenerationAdapter,
    SimulatedImageGenerationAdapter,
)
from app.verification.service import (
    VisualVerificationService,
    SimulatedVisualVerificationService,
)
from app.project.bible import load_bible

router = APIRouter(prefix="/generation", tags=["Generation & Orchestration"])
_batch_locks: Dict[str, threading.Lock] = {}
_batch_locks_guard = threading.Lock()

def _get_project_bible(project_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", project_id):
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_PROJECT_ID", "message": "Project IDs may contain letters, numbers, underscores, and hyphens only."})
    clean_id = project_id
    bible_path = PROJECT_ROOT / "runs" / clean_id / "bible.json"
    if not bible_path.exists():
        raise HTTPException(status_code=404, detail={"error_code": "ERR_PROJECT_CANON_UNAVAILABLE", "message": f"Project '{clean_id}' has no saved Story Bible."})
    return load_bible(bible_path)

class CompileContextRequest(BaseModel):
    project_id: str = "default_project"
    story_id: str = "story_01"
    panel_id: str = "panel_01"
    scene: SceneSpec

class CreateBatchRequest(BaseModel):
    batch_id: Optional[str] = None
    project_id: str = "default_project"
    story_id: str = "story_01"
    scenes: List[SceneSpec]
    model: str = "muse-image-1.0"
    max_retries_per_panel: int = 2
    spend_cap_usd: float = 25.0
    is_simulated: bool = False
    require_verification: bool = False

@router.post("/compile-context", response_model=PanelContextPacket)
def compile_context(req: CompileContextRequest) -> PanelContextPacket:
    """
    Pure-code compile continuity context for a panel.
    Returns effective prompt, visual invariants, negative rules, reference assets,
    and cryptographic context fingerprint without triggering external generation.
    """
    bible = _get_project_bible(req.project_id)
    try:
        packet = build_panel_context_packet(
            story_bible=bible,
            scene=req.scene,
            panel_id=req.panel_id,
            story_id=req.story_id,
            project_id=req.project_id,
            model="muse-image-1.0",
        )
        return packet
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_1001_INVALID_SCHEMA", "message": str(e)}
        )

@router.post("/batches", response_model=BatchSummary)
def start_batch_generation(req: CreateBatchRequest) -> BatchSummary:
    batch_id = req.batch_id or f"batch_{uuid.uuid4().hex[:10]}"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", batch_id):
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_BATCH_ID", "message": "Batch IDs may contain letters, numbers, underscores, and hyphens only."})
    request_payload = req.model_dump(mode="json", exclude={"batch_id"})
    request_fingerprint = hashlib.sha256(json.dumps(request_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    with _batch_locks_guard:
        lock = _batch_locks.setdefault(batch_id, threading.Lock())
    with lock:
        return _start_batch_generation(req, batch_id, request_fingerprint)


def _start_batch_generation(req: CreateBatchRequest, batch_id: str, request_fingerprint: str) -> BatchSummary:
    """
    Dispatch a multi-panel generation batch.
    Supports either LIVE Meta Model API dispatch or deterministic SIMULATED execution.
    Enforces bounded retries, spend caps, and full attempt audit logging.
    """
    config = InkLoopConfig.load()
    batch_path = PROJECT_ROOT / "runs" / "batches" / f"{batch_id}.json"
    if batch_path.is_file():
        try:
            prior = BatchSummary.model_validate_json(batch_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=409, detail={"error_code": "ERR_BATCH_ID_ALREADY_EXISTS", "message": f"A saved record exists for this batch ID but cannot be safely reused: {exc}"})
        if prior.request_fingerprint != request_fingerprint:
            raise HTTPException(status_code=409, detail={"error_code": "ERR_BATCH_IDEMPOTENCY_CONFLICT", "message": "This batch ID is already associated with a different or legacy request. Use the saved job or choose a new batch ID."})
        return prior
    bible = _get_project_bible(req.project_id)

    # Output directory for rendered panel assets
    output_dir = PROJECT_ROOT / "runs" / req.project_id / "panels"
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_spec = BatchSpec(
        batch_id=batch_id,
        project_id=req.project_id,
        story_id=req.story_id,
        story_bible=bible,
        scenes=req.scenes,
        model=req.model,
        max_retries_per_panel=req.max_retries_per_panel,
        spend_cap_usd=req.spend_cap_usd,
        output_dir=str(output_dir),
        require_verification=req.require_verification,
        request_fingerprint=request_fingerprint,
    )

    # Simulation is permitted only when explicitly requested. Missing credentials
    # must never be converted into a successful simulated batch.
    if req.is_simulated:
        adapter = SimulatedImageGenerationAdapter(default_success=True)
        verifier = SimulatedVisualVerificationService(config=config)
    else:
        if not config.has_credentials:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": "Live generation is unavailable because provider credentials are not configured. Select explicit simulation mode only for a labeled test run."},
            )
        adapter = MetaImageGenerationAdapter(config=config)
        verifier = VisualVerificationService(config=config)

    orchestrator = BatchOrchestrator(
        config=config,
        adapter=adapter,
        run_log_dir=PROJECT_ROOT / "runs" / "batches",
        verifier=verifier,
    )

    summary = orchestrator.orchestrate_batch(batch_spec)
    return summary

@router.get("/batches")
def list_batches() -> List[Dict[str, Any]]:
    """List all previous batch execution summaries."""
    batches_dir = PROJECT_ROOT / "runs" / "batches"
    batches = []
    if batches_dir.exists():
        for f in batches_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    batches.append({
                        "batch_id": data.get("batch_id", f.stem),
                        "status": data.get("status"),
                        "total_panels": data.get("total_panels", 0),
                        "successful_panels": data.get("successful_panels", 0),
                        "verified_panels": data.get("verified_panels", 0),
                        "failed_panels": data.get("failed_panels", 0),
                        "unresolved_panels": data.get("unresolved_panels", 0),
                        "is_simulated": data.get("is_simulated", False),
                        "started_at": data.get("started_at"),
                        "completed_at": data.get("completed_at"),
                        "total_duration_seconds": data.get("total_duration_seconds", 0),
                        "cost_mode": data.get("cost_mode"),
                        "known_cost_usd": data.get("known_cost_usd"),
                    })
            except Exception:
                continue

    # Sort newest first
    batches.sort(key=lambda b: b.get("started_at") or "", reverse=True)
    return batches

@router.get("/batches/{batch_id}")
def get_batch(batch_id: str) -> Dict[str, Any]:
    """Retrieve full batch execution summary with per-panel attempts and verifications."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", batch_id):
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_BATCH_ID", "message": "Invalid batch ID."})
    batches_dir = PROJECT_ROOT / "runs" / "batches"
    target = batches_dir / f"{batch_id}.json"
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": f"Batch {batch_id} not found"}
        )

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/batches/{batch_id}/resume", response_model=BatchSummary)
def resume_batch(batch_id: str) -> BatchSummary:
    """
    Resume an interrupted or partially failed batch.
    Re-uses already SUCCEEDED panels and only retries unresolved panels.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", batch_id):
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_BATCH_ID", "message": "Invalid batch ID."})
    batches_dir = PROJECT_ROOT / "runs" / "batches"
    target = batches_dir / f"{batch_id}.json"
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": f"Batch {batch_id} not found"}
        )

    with open(target, "r", encoding="utf-8") as f:
        prior_data = json.load(f)
    
    prior_summary = BatchSummary(**prior_data)
    project_id = prior_summary.project_id or "default_project"
    bible = _get_project_bible(project_id)
    current_bible_version = str(getattr(bible, "bible_version", getattr(bible, "version", "1.0.0")))
    if current_bible_version != prior_summary.bible_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "ERR_BATCH_CONTEXT_CHANGED", "message": "The project Story Bible changed since this batch started. Start a new batch or restore the original project revision before resuming."},
        )
    if not prior_summary.source_scenes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "ERR_BATCH_INPUTS_UNAVAILABLE", "message": "This older batch did not save its original scene inputs, so it cannot be resumed safely."},
        )
    scenes = prior_summary.source_scenes
    config = InkLoopConfig.load()

    batch_spec = BatchSpec(
        batch_id=batch_id,
        project_id=project_id,
        story_id=prior_summary.story_id,
        story_bible=bible,
        scenes=scenes,
        model=prior_summary.model,
        max_retries_per_panel=prior_summary.max_retries_per_panel,
        spend_cap_usd=prior_summary.spend_cap_usd or config.global_spend_cap_usd,
        require_verification=prior_summary.require_verification,
        output_dir=str(PROJECT_ROOT / "runs" / project_id / "panels"),
        request_fingerprint=prior_summary.request_fingerprint,
    )

    if prior_summary.is_simulated:
        adapter = SimulatedImageGenerationAdapter(default_success=True)
        verifier = SimulatedVisualVerificationService(config=config)
    else:
        if not config.has_credentials:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "ERR_IMAGE_PROVIDER_UNAVAILABLE", "message": "This batch used live generation, but provider credentials are currently unavailable. It was not resumed with simulation."},
            )
        adapter = MetaImageGenerationAdapter(config=config)
        verifier = VisualVerificationService(config=config)

    orchestrator = BatchOrchestrator(
        config=config,
        adapter=adapter,
        run_log_dir=batches_dir,
        verifier=verifier,
    )

    new_summary = orchestrator.resume_batch(batch_spec, prior_summary=prior_summary)
    return new_summary
