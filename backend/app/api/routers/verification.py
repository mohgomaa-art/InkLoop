"""
Visual Verification API Router.
Exposes L0 code-level checks, L1 SAM subject/framing checks, and L2 Judge visual checklists
with tri-state pass/fail/unsure verdicts and fail-closed human review routing.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.config import InkLoopConfig, PROJECT_ROOT
from app.schemas import VerificationResult, CharacterSpec, AttributeCheck, Tolerances
from app.verification.service import VisualVerificationService, SimulatedVisualVerificationService
from app.project.bible import load_bible
from app.api.routers.assets import get_registry

router = APIRouter(prefix="/verification", tags=["Visual Verification"])

class VerifyRequest(BaseModel):
    file_path: Optional[str] = None
    asset_id: Optional[str] = None
    project_id: str = "default_project"
    character_id: str
    mode: str = Field(default="live", description="'live' or explicitly selected 'simulated'")

@router.get("/rules")
def get_verification_rules() -> Dict[str, Any]:
    """Retrieve active multi-tier verification rules and thresholds."""
    return {
        "l0_code": {
            "aspect_ratio_tolerance": 0.05,
            "min_dimension_px": 256,
            "min_byte_size": 1024,
            "forbidden_patterns": ["no dialogue text", "no speech bubbles", "watermark", "signature"],
            "sheet_bleed_check": True,
            "blank_frame_check": True,
        },
        "l1_sam_subject": {
            "model": "sam-3.1",
            "concept_prompt": "Derived from the selected being's declared kind and form",
            "face_landmark_check": "Only applies when explicitly enabled for the selected character",
            "framing_aspects": ["bounding_box_within_frame", "subject_count_match"],
        },
        "l2_vision_judge": {
            "model": "muse-spark-1.3",
            "evaluation_format": "tri_state_json",
            "verdict_states": ["pass", "fail", "unsure"],
            "acceptance_policy": "all_required_attributes_must_pass",
            "unsure_policy": "treated_as_fail_closed_routes_to_human_review",
            "identity_source": "Selected project character checklist and reference assets",
            "anatomy_policy": "Only evaluate features declared for the selected being; do not infer human anatomy",
        }
    }

@router.post("/verify", response_model=VerificationResult)
def verify_panel(req: VerifyRequest) -> VerificationResult:
    """
    Run multi-tier visual verification (L0 + L1 + L2).
    Never converts a simulated pass into live proof.
    """
    config = InkLoopConfig.load()
    
    # Resolve file path
    target_path: Optional[Path] = None
    if req.file_path:
        p = Path(req.file_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        target_path = p
    elif req.asset_id:
        try:
            asset = get_registry().get_asset(req.asset_id)
            if not asset or asset.project_id != req.project_id:
                raise HTTPException(status_code=404, detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": "Image asset was not found in this project."})
            resolved = get_registry().resolve_asset(req.asset_id, verify_integrity=True)
            target_path = Path(resolved.file_path)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail={"error_code": "ERR_ASSET_UNAVAILABLE", "message": str(exc)})

    if not target_path or not target_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "ERR_1005_UNKNOWN_ENTITY_REFERENCE", "message": "Target image not found"})
    if req.file_path:
        try:
            target_path.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail={"error_code": "ERR_ASSET_SCOPE_VIOLATION", "message": "Verification accepts files stored inside the project workspace only."})

    try:
        candidate_bytes = target_path.read_bytes()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "ERR_6003_ENGINE_CRASH", "message": f"Failed reading asset: {e}"}
        )

    # Verify against the project's actual selected character contract.
    try:
        bible = load_bible(PROJECT_ROOT / "runs" / req.project_id / "bible.json")
    except Exception as exc:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_PROJECT_CANON_UNAVAILABLE", "message": f"Project canon could not be loaded: {exc}"})
    char_spec = bible.characters.get(req.character_id)
    if char_spec is None:
        raise HTTPException(status_code=404, detail={"error_code": "ERR_CHARACTER_UNAVAILABLE", "message": f"Character '{req.character_id}' is not in this project's canon."})

    if req.mode == "live" and config.has_credentials:
        service = VisualVerificationService(config=config)
    elif req.mode == "simulated":
        service = SimulatedVisualVerificationService(config=config)
    elif req.mode == "live":
        raise HTTPException(status_code=503, detail={"error_code": "ERR_VERIFICATION_PROVIDER_UNAVAILABLE", "message": "Live verification requires configured provider credentials."})
    else:
        raise HTTPException(status_code=422, detail={"error_code": "ERR_INVALID_VERIFICATION_MODE", "message": "Mode must be 'live' or 'simulated'."})

    res = service.verify_panel(
        reference_asset=None,
        candidate_bytes=candidate_bytes,
        character_spec=char_spec,
    )
    return res
