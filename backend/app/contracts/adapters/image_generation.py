"""
InkLoop Image Generation Engine (E1) Contract Adapter.
Provides a backward-compatible bridge between the completed M0 Image Generation implementation
and the shared EngineRunRequest/EngineRunResponse contract system.
"""
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field

from app.contracts.engine import (
    EngineId,
    EngineStatus,
    EngineRunRequest,
    EngineRunResponse,
    UsageMetrics,
    ProvenanceRecord,
)
from app.contracts.artifacts import AssetType, LifecycleStatus, ArtifactManifest
from app.contracts.geometry import Size
from app.contracts.errors import ErrorCode, EngineFailure, ValidationErrorDetail
from app.config import PROJECT_ROOT, InkLoopConfig
from app.parsers import build_image_edit_payload

class ImageGenerationParams(BaseModel):
    """Parameters passed to Engine E1 Image Generation."""
    prompt: str = Field(..., description="Compiled prompt including scene and character instructions")
    reference_image_path: Optional[str] = Field(default=None, description="Path to canonical character reference for anchored generation")
    model: str = Field(default="muse-image-1.0", description="Target model ID")
    output_filename_base: str = Field(default="generated_panel", description="Base filename without extension")
    n: int = Field(default=1, description="Number of candidates to generate")

class ImageGenerationOutput(BaseModel):
    """Structured output emitted by Engine E1 Image Generation."""
    primary_artifact_id: str
    png_path: str
    webp_path: str
    dimensions: Size
    sha256: str
    is_reference_anchored: bool
    request_id: Optional[str] = None

class ImageGenerationEngineAdapter:
    """
    Adapter encapsulating Engine E1 Image Generation.
    Supports dry-run validation, parameter checks, and contract transformation.
    """
    ENGINE_ID = EngineId.E1_IMAGE_GENERATION
    ENGINE_VERSION = "1.0.0"

    def __init__(self, config: Optional[InkLoopConfig] = None):
        self.config = config or InkLoopConfig.load()

    def validate_request(self, request: EngineRunRequest[ImageGenerationParams]) -> List[ValidationErrorDetail]:
        """Performs static pre-flight contract validation before any API dispatch."""
        errors: List[ValidationErrorDetail] = []
        if not request.parameters.prompt or not request.parameters.prompt.strip():
            errors.append(ValidationErrorDetail(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="Prompt must not be empty",
                field="parameters.prompt",
                entity_id=request.scope_id
            ))
        if request.parameters.reference_image_path:
            ref_path = PROJECT_ROOT / request.parameters.reference_image_path
            if not ref_path.exists():
                errors.append(ValidationErrorDetail(
                    code=ErrorCode.UNKNOWN_ENTITY_REFERENCE,
                    message=f"Referenced image file does not exist at {request.parameters.reference_image_path}",
                    field="parameters.reference_image_path",
                    entity_id=request.scope_id
                ))
        return errors

    def execute_dry_run(self, request: EngineRunRequest[ImageGenerationParams]) -> EngineRunResponse[ImageGenerationOutput]:
        """Executes a dry-run contract check returning a mock plan without API calls."""
        val_errors = self.validate_request(request)
        if val_errors:
            return EngineRunResponse[ImageGenerationOutput](
                run_id=request.run_id,
                attempt_id=request.attempt_id,
                engine_id=self.ENGINE_ID,
                engine_version=self.ENGINE_VERSION,
                status=EngineStatus.FAILED,
                output=None,
                validation_errors=val_errors,
                error=EngineFailure(
                    code=ErrorCode.INVALID_SCHEMA,
                    message="Dry-run validation failed on request parameters",
                    stage="pre_flight_validation",
                    validation_details=val_errors
                ),
                provenance=ProvenanceRecord(
                    engine_id=self.ENGINE_ID,
                    engine_version=self.ENGINE_VERSION,
                    config_hash=request.config_hash,
                    input_artifact_ids=request.input_artifact_ids
                )
            )

        is_anchored = bool(request.parameters.reference_image_path)
        art_id = f"art_mock_{request.run_id}_{request.attempt_id}"

        mock_output = ImageGenerationOutput(
            primary_artifact_id=art_id,
            png_path=f"runs/mock/{request.parameters.output_filename_base}.png",
            webp_path=f"runs/mock/{request.parameters.output_filename_base}.webp",
            dimensions=Size(width=1280.0, height=1920.0),
            sha256="mock_sha256_dry_run_digest_000000000000000000000000000000000000",
            is_reference_anchored=is_anchored,
            request_id="dry-run-req-id-0000"
        )

        return EngineRunResponse[ImageGenerationOutput](
            run_id=request.run_id,
            attempt_id=request.attempt_id,
            engine_id=self.ENGINE_ID,
            engine_version=self.ENGINE_VERSION,
            status=EngineStatus.SUCCESS,
            output=mock_output,
            output_artifact_ids=[art_id],
            usage=UsageMetrics(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                image_ops=1,
                compute_seconds=0.01,
                estimated_cost_usd=0.0
            ),
            provenance=ProvenanceRecord(
                engine_id=self.ENGINE_ID,
                engine_version=self.ENGINE_VERSION,
                config_hash=request.config_hash,
                input_artifact_ids=request.input_artifact_ids
            )
        )
