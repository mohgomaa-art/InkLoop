"""
Image generation adapters for InkLoop.
Provides both live Meta Model API integration and deterministic test simulation.
Strictly sanitizes headers and metadata to eliminate credential leakage.
"""
import time
import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from io import BytesIO
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict

import httpx

from app.config import InkLoopConfig
from app.parsers import build_image_edit_payload
from app.schemas import ErrorCategory

class GenerationRequest(BaseModel):
    """Clean, sanitized request parameters for an image generation attempt."""
    prompt: str
    reference_bytes: Optional[bytes] = None
    reference_mime: str = "image/png"
    model: str = "muse-image-1.0"
    panel_id: str = ""
    scene_id: str = ""
    n: int = 1
    parameters: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

class GenerationResponse(BaseModel):
    """Normalized result returned from an image generation adapter."""
    success: bool
    http_status: Optional[int] = None
    image_bytes: Optional[bytes] = None
    request_id: Optional[str] = None
    endpoint: str = ""
    error_category: Optional[ErrorCategory] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    sanitized_metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ImageGenerationAdapter(ABC):
    """Abstract interface for image generation engines."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Execute image generation synchronously."""
        pass

def sanitize_error_text(text: str) -> str:
    """Removes sensitive authorization tokens or keys from error strings."""
    if not text:
        return ""
    # Truncate and strip
    clean = text.strip()
    for sensitive_keyword in ["Bearer", "sk-", "key=", "api_key="]:
        if sensitive_keyword.lower() in clean.lower():
            clean = "[REDACTED_ERROR_MESSAGE]"
    return clean[:400]

class MetaImageGenerationAdapter(ImageGenerationAdapter):
    """
    Live Meta Model API generation adapter.
    Uses POST /v1/images/edits for reference-anchored generation or
    POST /v1/images/generations for text-only baseline generation.
    """

    def __init__(self, config: InkLoopConfig, timeout_seconds: float = 60.0):
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.base_url = config.meta_base_url.rstrip("/")

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.config.has_credentials:
            return GenerationResponse(
                success=False,
                http_status=401,
                endpoint="/images/edits" if request.reference_bytes else "/images/generations",
                error_category=ErrorCategory.AUTHENTICATION_ERROR,
                error_message="Meta Model API key is not configured.",
                sanitized_metadata={"model": request.model, "panel_id": request.panel_id}
            )

        headers = {
            "Authorization": f"Bearer {self.config.model_api_key}",
            "Content-Type": "application/json"
        }

        # Build payload
        if request.reference_bytes:
            endpoint = f"{self.base_url}/images/edits"
            payload = build_image_edit_payload(
                prompt=request.prompt,
                image_bytes=request.reference_bytes,
                mime_type=request.reference_mime,
                model=request.model or self.config.muse_image_model
            )
        else:
            endpoint = f"{self.base_url}/images/generations"
            payload = {
                "model": request.model or self.config.muse_image_model,
                "prompt": request.prompt,
                "n": request.n
            }

        sanitized_meta = {
            "model": payload["model"],
            "prompt_length": len(request.prompt),
            "endpoint": endpoint,
            "has_reference": bool(request.reference_bytes),
            "panel_id": request.panel_id,
            "scene_id": request.scene_id
        }

        start_time = time.time()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, headers=headers, json=payload)
            duration = round(time.time() - start_time, 3)
            status_code = resp.status_code
            req_id = resp.headers.get("x-request-id")

            if status_code != 200:
                raw_err = sanitize_error_text(resp.text)
                err_category = self._classify_error(status_code, raw_err)
                return GenerationResponse(
                    success=False,
                    http_status=status_code,
                    request_id=req_id,
                    endpoint=endpoint,
                    error_category=err_category,
                    error_message=raw_err,
                    duration_seconds=duration,
                    sanitized_metadata=sanitized_meta
                )

            data = resp.json()
            items = data.get("data", [])
            if not items or "b64_json" not in items[0]:
                return GenerationResponse(
                    success=False,
                    http_status=status_code,
                    request_id=req_id,
                    endpoint=endpoint,
                    error_category=ErrorCategory.SERVER_ERROR,
                    error_message="Provider returned 200 OK but payload missing b64_json image data.",
                    duration_seconds=duration,
                    sanitized_metadata=sanitized_meta
                )

            img_bytes = base64.b64decode(items[0]["b64_json"])
            # Distinguish missing usage from zero usage
            reported_usage = data.get("usage")

            return GenerationResponse(
                success=True,
                http_status=status_code,
                image_bytes=img_bytes,
                request_id=req_id,
                endpoint=endpoint,
                duration_seconds=duration,
                usage=reported_usage,
                cost_usd=None, # Only set if genuinely returned/billed by provider
                sanitized_metadata=sanitized_meta
            )

        except httpx.TimeoutException as exc:
            duration = round(time.time() - start_time, 3)
            return GenerationResponse(
                success=False,
                endpoint=endpoint,
                error_category=ErrorCategory.NETWORK_TIMEOUT,
                error_message=f"Request timed out after {self.timeout_seconds}s.",
                duration_seconds=duration,
                sanitized_metadata=sanitized_meta
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 3)
            return GenerationResponse(
                success=False,
                endpoint=endpoint,
                error_category=ErrorCategory.UNKNOWN,
                error_message=sanitize_error_text(str(exc)),
                duration_seconds=duration,
                sanitized_metadata=sanitized_meta
            )

    def _classify_error(self, status: int, text: str) -> ErrorCategory:
        """Classifies HTTP error status and body into standard InkLoop error category."""
        if status in (401, 403):
            return ErrorCategory.AUTHENTICATION_ERROR
        if status == 429:
            return ErrorCategory.RATE_LIMIT_EXCEEDED
        if status == 400:
            if "content_policy" in text.lower():
                return ErrorCategory.CONTENT_POLICY_VIOLATION
            return ErrorCategory.BAD_REQUEST
        if 500 <= status <= 599:
            return ErrorCategory.SERVER_ERROR
        return ErrorCategory.UNKNOWN

class SimulatedImageGenerationAdapter(ImageGenerationAdapter):
    """
    Deterministic fake adapter for unit and integration testing.
    Produces valid PNG outputs without external API calls or credit consumption.
    Supports scripted error sequences per panel.
    """

    def __init__(
        self,
        default_success: bool = True,
        simulated_usage: Optional[Dict[str, Any]] = None,
        simulated_cost: Optional[float] = None,
        duration_seconds: float = 0.01
    ):
        self.default_success = default_success
        self.simulated_usage = simulated_usage
        self.simulated_cost = simulated_cost
        self.duration_seconds = duration_seconds
        self.request_history: List[GenerationRequest] = []
        # Scripted responses: panel_id -> List of GenerationResponse
        self._scripted_responses: Dict[str, List[GenerationResponse]] = {}

    def script_panel_responses(self, panel_id: str, responses: List[GenerationResponse]):
        """Queue a specific sequence of responses for a panel identifier."""
        self._scripted_responses[panel_id] = list(responses)

    def _create_dummy_png(self, label: str) -> bytes:
        """Generates a small valid PNG byte stream with distinct content."""
        buf = BytesIO()
        img = Image.new("RGB", (64, 64), color="gray")
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.request_history.append(request)

        # Check if there is a scripted sequence for this panel
        if request.panel_id in self._scripted_responses and self._scripted_responses[request.panel_id]:
            resp = self._scripted_responses[request.panel_id].pop(0)
            return resp

        if not self.default_success:
            return GenerationResponse(
                success=False,
                http_status=500,
                endpoint="POST /v1/images/edits",
                error_category=ErrorCategory.SERVER_ERROR,
                error_message="Simulated internal server error",
                duration_seconds=self.duration_seconds,
                sanitized_metadata={"panel_id": request.panel_id, "model": request.model}
            )

        img_bytes = self._create_dummy_png(request.panel_id)
        return GenerationResponse(
            success=True,
            http_status=200,
            image_bytes=img_bytes,
            request_id=f"sim_req_{request.panel_id}_{len(self.request_history)}",
            endpoint="POST /v1/images/edits" if request.reference_bytes else "POST /v1/images/generations",
            duration_seconds=self.duration_seconds,
            usage=self.simulated_usage,
            cost_usd=self.simulated_cost,
            sanitized_metadata={"panel_id": request.panel_id, "model": request.model}
        )
