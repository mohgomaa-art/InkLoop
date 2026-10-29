"""
InkLoop Image Generation Engine (E1) Contract Adapter.
Provides a backward-compatible bridge between the completed M0 Image Generation implementation
and the shared EngineRunRequest/EngineRunResponse contract system.
Supports dry-run validation, parameter checks, offline mock execution, and contract transformation.
"""
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.contracts.engine import (
    EngineId,
    EngineStatus,
    EngineRunRequest,
    EngineRunResponse,
    UsageMetrics,
    ProvenanceRecord,
    ImageGenerationParams,
    ImageGenerationOutput,
)
from app.contracts.artifacts import AssetType, LifecycleStatus, ArtifactManifest
from app.contracts.geometry import Size
from app.contracts.errors import ErrorCode, EngineFailure, ValidationErrorDetail
from app.config import PROJECT_ROOT, InkLoopConfig
from app.parsers import build_image_edit_payload

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

    def build_payload(self, params: ImageGenerationParams) -> Dict[str, Any]:
        """
        Builds the raw provider payload adhering to the tested M0 Meta API specification.
        Preserves original payload-building behavior.
        """
        if params.reference_image_path:
            ref_path = PROJECT_ROOT / params.reference_image_path
            with open(ref_path, "rb") as f:
                img_bytes = f.read()
            mime = "image/webp" if ref_path.suffix.lower() == ".webp" else "image/png"
            return build_image_edit_payload(
                prompt=params.prompt,
                image_bytes=img_bytes,
                mime_type=mime,
                model=params.model
            )
        else:
            return {
                "model": params.model,
                "prompt": params.prompt,
                "n": params.n
            }

    def execute_dry_run(self, request: EngineRunRequest[ImageGenerationParams]) -> EngineRunResponse[ImageGenerationOutput]:
        """
        Executes a dry-run contract check returning an explicit mock plan without API calls.
        Guaranteed to not be mistaken for real generation (tagged with dry_run provenance and mock hash).
        """
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
        art_id = f"art_dryrun_mock_{request.run_id}_{request.attempt_id}"

        mock_output = ImageGenerationOutput(
            primary_artifact_id=art_id,
            png_path=f"runs/dry_run_mock/{request.parameters.output_filename_base}.png",
            webp_path=f"runs/dry_run_mock/{request.parameters.output_filename_base}.webp",
            dimensions=Size(width=1280.0, height=1920.0),
            sha256="mock_dry_run_hash_do_not_use_in_production_00000000000000000000",
            is_reference_anchored=is_anchored,
            request_id="mock-dry-run-request-id"
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
                image_ops=0,  # Explicitly 0 to prevent accounting fraud
                compute_seconds=0.001,
                estimated_cost_usd=0.0
            ),
            provenance=ProvenanceRecord(
                engine_id=self.ENGINE_ID,
                engine_version=self.ENGINE_VERSION,
                config_hash=request.config_hash,
                input_artifact_ids=request.input_artifact_ids
            )
        )

    def handle_mock_response(
        self,
        request: EngineRunRequest[ImageGenerationParams],
        http_status: int,
        response_body: Dict[str, Any],
        latency: float = 0.5
    ) -> EngineRunResponse[ImageGenerationOutput]:
        """
        Parses an offline provider response mapping HTTP statuses and error categories
        into standardized InkLoop contract failures and retryability flags.
        """
        if http_status == 200:
            art_id = f"art_{request.run_id}_{request.attempt_id}"
            output = ImageGenerationOutput(
                primary_artifact_id=art_id,
                png_path=f"runs/generated/{request.parameters.output_filename_base}.png",
                webp_path=f"runs/generated/{request.parameters.output_filename_base}.webp",
                dimensions=Size(width=1280.0, height=1920.0),
                sha256="mock_verified_offline_sha256_hash_1234567890abcdef1234567890",
                is_reference_anchored=bool(request.parameters.reference_image_path),
                request_id=response_body.get("id", "req-offline-success")
            )
            usage_raw = response_body.get("usage", {})
            return EngineRunResponse[ImageGenerationOutput](
                run_id=request.run_id,
                attempt_id=request.attempt_id,
                engine_id=self.ENGINE_ID,
                engine_version=self.ENGINE_VERSION,
                status=EngineStatus.SUCCESS,
                latency_seconds=latency,
                output=output,
                output_artifact_ids=[art_id],
                usage=UsageMetrics(
                    input_tokens=usage_raw.get("input_tokens", 10000),
                    output_tokens=usage_raw.get("output_tokens", 1000),
                    total_tokens=usage_raw.get("total_tokens", 11000),
                    image_ops=1,
                    compute_seconds=latency,
                    estimated_cost_usd=0.01
                ),
                provenance=ProvenanceRecord(
                    engine_id=self.ENGINE_ID,
                    engine_version=self.ENGINE_VERSION,
                    config_hash=request.config_hash,
                    input_artifact_ids=request.input_artifact_ids
                )
            )

        # Failure mapping
        error_info = response_body.get("error", {})
        err_code_str = error_info.get("code", "")
        err_msg = error_info.get("message", "Unknown provider error")

        if http_status == 400 and err_code_str == "content_policy_violation":
            code = ErrorCode.CONTENT_POLICY_VIOLATION
            retryable = True  # Permitted 1 neutral rephrase iteration per M0 protocol
        elif http_status == 401:
            code = ErrorCode.PROVIDER_AUTH_FAILED
            retryable = False
        elif http_status == 429:
            code = ErrorCode.PROVIDER_RATE_LIMITED
            retryable = True
        elif http_status >= 500:
            code = ErrorCode.PROVIDER_SERVICE_UNAVAILABLE
            retryable = True
        else:
            code = ErrorCode.ENGINE_CRASH
            retryable = False

        failure = EngineFailure(
            code=code,
            message=err_msg,
            stage="provider_api_dispatch",
            retryable=retryable,
            http_status=http_status,
            raw_provider_error=str(response_body)[:200]
        )

        return EngineRunResponse[ImageGenerationOutput](
            run_id=request.run_id,
            attempt_id=request.attempt_id,
            engine_id=self.ENGINE_ID,
            engine_version=self.ENGINE_VERSION,
            status=EngineStatus.FAILED,
            latency_seconds=latency,
            output=None,
            error=failure,
            retryable=retryable,
            provenance=ProvenanceRecord(
                engine_id=self.ENGINE_ID,
                engine_version=self.ENGINE_VERSION,
                config_hash=request.config_hash,
                input_artifact_ids=request.input_artifact_ids
            )
        )
