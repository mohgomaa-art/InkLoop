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

class ReferenceImagePayload(BaseModel):
    """Structured reference image payload with semantic role, weight, and notes."""
    asset_id: Optional[str] = None
    image_bytes: bytes
    mime_type: str = "image/png"
    role: str = "style_reference"  # style_reference, character_reference, composition_reference, target_to_edit, pose_reference, background_reference
    character_id: Optional[str] = None
    prop_id: Optional[str] = None
    view_role: Optional[str] = None
    weight: float = 1.0  # Heuristic prompt weight
    notes: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ProviderCapabilities(BaseModel):
    """Declared, verified capabilities of an image generation provider."""
    text_to_image: bool = True
    single_image_edit: bool = True
    multi_image_reference: bool = True
    max_reference_images: int = 5
    conversational_refinement: bool = False
    deterministic_seed: bool = False
    identity_lock_guarantee: bool = False  # Honest: reference-conditioned best-effort generation, not guaranteed identity lock
    supported_mime_types: List[str] = Field(default_factory=lambda: ["image/png", "image/jpeg", "image/webp", "image/jpg"])
    max_image_dimension: int = 2048
    max_image_bytes: int = 10 * 1024 * 1024

class GenerationRequest(BaseModel):
    """Clean, sanitized request parameters for an image generation attempt."""
    prompt: str
    reference_bytes: Optional[bytes] = None
    reference_mime: str = "image/png"
    reference_images: List[ReferenceImagePayload] = Field(default_factory=list)
    model: str = "muse-image-1.0"
    panel_id: str = ""
    scene_id: str = ""
    n: int = 1
    dimensions: Optional[List[int]] = None
    aspect_ratio: Optional[str] = None
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
    is_simulated: bool = False
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    sanitized_metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ImageGenerationAdapter(ABC):
    """Abstract interface for image generation engines."""
    is_simulated: bool = False

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Execute image generation synchronously."""
        pass

    def get_capabilities(self) -> ProviderCapabilities:
        """Returns declared, verified capabilities of this generation engine."""
        return ProviderCapabilities()

def sanitize_error_text(text: str, sensitive_strings: Optional[List[str]] = None) -> str:
    """Removes sensitive authorization tokens, keys, or credentials from error strings."""
    if not text:
        return ""
    clean = text.strip()
    if sensitive_strings:
        for s in sensitive_strings:
            if s and len(s) > 3 and s in clean:
                clean = clean.replace(s, "[REDACTED_SECRET]")
    for sensitive_keyword in ["Bearer", "sk-", "key=", "api_key=", "authorization:"]:
        if sensitive_keyword.lower() in clean.lower():
            clean = "[REDACTED_ERROR_MESSAGE]"
    return clean[:400]

class MetaImageGenerationAdapter(ImageGenerationAdapter):
    """
    Live Meta Model API generation adapter.
    Uses POST /v1/images/edits for reference-anchored generation or
    POST /v1/images/generations for text-only baseline generation.
    """
    is_simulated: bool = False

    def __init__(self, config: InkLoopConfig, timeout_seconds: float = 60.0):
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.base_url = config.meta_base_url.rstrip("/")

    def _sanitize(self, text: str) -> str:
        sensitive = [self.config.model_api_key] if self.config.model_api_key else []
        return sanitize_error_text(text, sensitive_strings=sensitive)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.config.has_credentials:
            return GenerationResponse(
                success=False,
                http_status=401,
                endpoint="/images/edits" if request.reference_bytes else "/images/generations",
                error_category=ErrorCategory.AUTHENTICATION_ERROR,
                error_message="Meta Model API key is not configured.",
                is_simulated=False,
                sanitized_metadata={"model": request.model, "panel_id": request.panel_id}
            )

        headers = {
            "Authorization": f"Bearer {self.config.model_api_key}",
            "Content-Type": "application/json"
        }

        # Build payload with multi-reference support and legacy fallback
        images_list = []
        if request.reference_images:
            for ref in request.reference_images:
                b64_str = base64.b64encode(ref.image_bytes).decode("ascii")
                images_list.append({"image_url": f"data:{ref.mime_type};base64,{b64_str}"})
        elif request.reference_bytes:
            b64_str = base64.b64encode(request.reference_bytes).decode("ascii")
            images_list.append({"image_url": f"data:{request.reference_mime};base64,{b64_str}"})

        if images_list:
            endpoint = f"{self.base_url}/images/edits"
            payload = {
                "model": request.model or self.config.muse_image_model,
                "prompt": request.prompt,
                "images": images_list,
                "n": request.n
            }
        else:
            endpoint = f"{self.base_url}/images/generations"
            payload = {
                "model": request.model or self.config.muse_image_model,
                "prompt": request.prompt,
                "n": request.n
            }

        # Meta Muse Image accepts `size` as an aspect-ratio hint (not an exact
        # output resolution). Keep it in the provider request so page geometry
        # can guide the generated composition instead of being silently lost.
        if request.dimensions and len(request.dimensions) == 2:
            width, height = (int(request.dimensions[0]), int(request.dimensions[1]))
            if width > 0 and height > 0:
                payload["size"] = f"{width}x{height}"

        sanitized_meta = {
            "model": payload["model"],
            "prompt_length": len(request.prompt),
            "endpoint": endpoint,
            "has_reference": bool(images_list),
            "reference_count": len(images_list),
            "reference_roles": [r.role for r in request.reference_images] if request.reference_images else (["single_ref"] if request.reference_bytes else []),
            "panel_id": request.panel_id,
            "scene_id": request.scene_id,
            "requested_dimensions": request.dimensions,
            "requested_aspect_ratio": request.aspect_ratio,
        }

        start_time = time.time()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, headers=headers, json=payload)
            duration = round(time.time() - start_time, 3)
            status_code = resp.status_code
            req_id = resp.headers.get("x-request-id")

            if status_code != 200:
                raw_err = self._sanitize(resp.text)
                err_category = self._classify_error(status_code, raw_err)
                return GenerationResponse(
                    success=False,
                    http_status=status_code,
                    request_id=req_id,
                    endpoint=endpoint,
                    error_category=err_category,
                    error_message=raw_err,
                    duration_seconds=duration,
                    is_simulated=False,
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
                    is_simulated=False,
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
                is_simulated=False,
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
                is_simulated=False,
                sanitized_metadata=sanitized_meta
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 3)
            return GenerationResponse(
                success=False,
                endpoint=endpoint,
                error_category=ErrorCategory.UNKNOWN,
                error_message=self._sanitize(str(exc)),
                duration_seconds=duration,
                is_simulated=False,
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
    Clearly marked as simulated to prevent confusion with actual provider operations.
    """
    is_simulated: bool = True

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
        from PIL import ImageDraw
        buf = BytesIO()
        img = Image.new("RGB", (256, 256), color=(128, 140, 150))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 236, 236], fill=(50, 100, 180), outline=(20, 20, 20))
        draw.ellipse([60, 60, 196, 196], fill=(220, 80, 40))
        img.save(buf, format="PNG")
        return buf.getvalue()

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            text_to_image=True,
            single_image_edit=True,
            multi_image_reference=True,
            max_reference_images=5,
            conversational_refinement=False,
            deterministic_seed=False,
            identity_lock_guarantee=False,  # Simulation accurately models real probabilistic conditioning
        )

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.request_history.append(request)

        has_refs = bool(request.reference_images or request.reference_bytes)
        ref_count = len(request.reference_images) if request.reference_images else (1 if request.reference_bytes else 0)
        ref_roles = [r.role for r in request.reference_images] if request.reference_images else (["single_ref"] if request.reference_bytes else [])

        # Check if there is a scripted sequence for this panel
        if request.panel_id in self._scripted_responses and self._scripted_responses[request.panel_id]:
            resp = self._scripted_responses[request.panel_id].pop(0)
            resp.is_simulated = True
            return resp

        if not self.default_success:
            return GenerationResponse(
                success=False,
                http_status=500,
                endpoint="POST /v1/images/edits" if has_refs else "POST /v1/images/generations",
                error_category=ErrorCategory.SERVER_ERROR,
                error_message="Simulated internal server error",
                duration_seconds=self.duration_seconds,
                is_simulated=True,
                sanitized_metadata={
                    "panel_id": request.panel_id,
                    "model": request.model,
                    "has_reference": has_refs,
                    "reference_count": ref_count,
                    "reference_roles": ref_roles
                }
            )

        img_bytes = self._create_dummy_png(request.panel_id)
        return GenerationResponse(
            success=True,
            http_status=200,
            image_bytes=img_bytes,
            request_id=f"sim_req_{request.panel_id}_{len(self.request_history)}",
            endpoint="POST /v1/images/edits" if has_refs else "POST /v1/images/generations",
            duration_seconds=self.duration_seconds,
            is_simulated=True,
            usage=self.simulated_usage,
            cost_usd=self.simulated_cost,
            sanitized_metadata={
                "panel_id": request.panel_id,
                "model": request.model,
                "has_reference": has_refs,
                "reference_count": ref_count,
                "reference_roles": ref_roles
            }
        )
