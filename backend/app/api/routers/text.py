"""
InkLoop Text Generation Engine API Router (Milestone M5 / Workstream E4).
Exposes REST endpoints for script block validation, exact-user-text ingestion,
and structured text generation.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel, Field

from app.text.enums import (
    ScriptBlockKind,
    DialogueDelivery,
    TextLanguage,
    TextDirection,
)
from app.text.models import (
    ScriptBlock,
    TextScriptManifest,
    TextValidationRequest,
    TextValidationResult,
    TextGenerationRequest,
    TextGenerationResult,
)
from app.text.engine import TextGenerationEngine
from app.text.errors import (
    TextEngineError,
    TextValidationError,
    TextGenerationBlockedError,
)

router = APIRouter(prefix="/text", tags=["Text Generation Engine (E4)"])
_engine_instance: Optional[TextGenerationEngine] = None


def get_text_engine() -> TextGenerationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TextGenerationEngine()
    return _engine_instance


class IngestUserTextRequest(BaseModel):
    project_id: str
    story_id: str = "story_01"
    scene_id: str
    panel_id: str
    user_text: str = Field(..., max_length=5000, description="Exact user-authored text to preserve")
    speaker_id: Optional[str] = None
    language: TextLanguage = TextLanguage.AR
    direction: TextDirection = TextDirection.RTL
    block_kind: ScriptBlockKind = ScriptBlockKind.DIALOGUE
    passage_id: Optional[str] = None


@router.post("/validate", summary="Validate structured script blocks")
def validate_script_blocks(req: TextValidationRequest) -> Dict[str, Any]:
    """
    Validates a list of script blocks against Story Bible canon and timeline state.
    Returns machine-readable diagnostics with error/warning codes and explanation.
    """
    engine = get_text_engine()
    res = engine.validate_blocks(
        blocks=req.blocks,
        target_scene_id=req.target_scene_id,
        target_panel_id=req.target_panel_id,
        story_bible=req.story_bible,
        timeline_events=req.timeline_events,
        allow_undeclared_entities=req.allow_undeclared_entities,
    )
    return res.model_dump()


@router.post("/ingest", summary="Ingest exact user text")
def ingest_user_text(req: IngestUserTextRequest) -> Dict[str, Any]:
    """
    Ingests user-supplied text in exact-preservation mode.
    Guarantees code-point by code-point preservation without normalization or paraphrasing.
    """
    engine = get_text_engine()
    try:
        block = engine.ingest_exact_user_text(
            project_id=req.project_id,
            story_id=req.story_id,
            scene_id=req.scene_id,
            panel_id=req.panel_id,
            user_text=req.user_text,
            speaker_id=req.speaker_id,
            language=req.language,
            direction=req.direction,
            block_kind=req.block_kind,
            passage_id=req.passage_id,
        )
        return block.model_dump()
    except TextValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": e.error_code, "message": str(e), "details": e.details}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "ERR_TEXT_INGESTION_FAILED", "message": str(e)}
        )


@router.post("/generate", summary="Generate structured panel text")
def generate_text(req: TextGenerationRequest) -> Dict[str, Any]:
    """
    Generates structured script blocks for a comic scene/panel.
    Simulated output is allowed only when explicit offline mode is enabled.
    Returns structured failure diagnostics if generation or validation fails.
    """
    import os
    if req.adapter_name == "offline_simulated" and os.getenv("INKLOOP_OFFLINE_MODE", "0").lower() not in ("1", "true"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "ERR_OFFLINE_MODE_NOT_ENABLED",
                "message": "Deterministic simulated text generation is available only when explicit offline mode is enabled.",
            },
        )
    if req.adapter_name not in ("offline_simulated", "meta_llm"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "ERR_UNKNOWN_TEXT_ADAPTER", "message": "The requested text adapter is not registered."},
        )

    engine = get_text_engine()
    res = engine.generate_panel_text(req)
    if not res.success and res.error_message and "not configured" in res.error_message:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "ERR_TEXT_PROVIDER_UNAVAILABLE", "message": res.error_message}
        )
    return res.model_dump()
