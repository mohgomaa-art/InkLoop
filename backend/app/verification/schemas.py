"""
InkLoop Visual Verification Service - Data Models & Schemas.
Defines structured outcome types for multi-tier verification:
L0 (Deterministic Code), L1 (Structure / SAM), and L2 (Vision Judge).
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict

from app.schemas import (
    AttributeVerdict,
    VerificationResult,
    BoundingBox,
    SegmentationResult,
)


class VerificationMode(str, Enum):
    """Execution mode for the visual verification service."""
    AUTO = "auto"            # Use live credentials if present, else fallback safely to simulated
    LIVE = "live"            # Enforce live Meta API execution (fails if credentials missing)
    SIMULATED = "simulated"  # Strictly offline deterministic execution (never consumes budget)


class L0CheckResult(BaseModel):
    """Detailed outcomes from L0 deterministic code checks."""
    passed: bool = Field(..., description="True if all L0 checks passed")
    checks: Dict[str, bool] = Field(default_factory=dict, description="Status of individual L0 checks")
    reason: Optional[str] = Field(default=None, description="Actionable failure reason if any check failed")
    dimensions: Optional[Tuple[int, int]] = Field(default=None, description="Decoded width and height (px)")
    aspect_ratio: Optional[float] = Field(default=None, description="Decoded width / height ratio")
    pixel_std: Optional[float] = Field(default=None, description="Standard deviation of pixel intensities")
    border_uniformity: Optional[float] = Field(default=None, description="Uniformity ratio of perimeter border pixels")

    model_config = ConfigDict(extra="forbid")


class L1SubjectResult(BaseModel):
    """Detailed outcomes from L1 structure and subject framing checks."""
    passed: bool = Field(..., description="True if subject presence, count, and framing passed")
    subject_count: int = Field(default=0, description="Count of detected subjects/persons")
    boxes: List[BoundingBox] = Field(default_factory=list, description="Extracted bounding boxes")
    mask_available: bool = Field(default=False, description="Whether segmentation mask was produced")
    mask_sha256: Optional[str] = Field(default=None, description="SHA-256 of opaque returned SAM mask payloads, when available")
    framing_ok: bool = Field(default=True, description="Whether subject scale and framing meet minimum bounds")
    face_scale_ok: bool = Field(default=True, description="Whether face/head resolution meets minimum threshold")
    reason: Optional[str] = Field(default=None, description="Failure reason if subject check failed")
    is_simulated: bool = Field(default=False, description="True if structure check was simulated/mocked")

    model_config = ConfigDict(extra="forbid")


class L2JudgeResult(BaseModel):
    """Detailed outcomes from L2 multimodal vision judge."""
    passed: bool = Field(..., description="True if all required canonical attributes passed")
    verdicts: List[AttributeVerdict] = Field(default_factory=list, description="Per-attribute verdicts")
    rejection_reason: Optional[str] = Field(default=None, description="Explanation if rejected or unsure")
    raw_response: Optional[str] = Field(default=None, description="Raw model text or payload")
    is_simulated: bool = Field(default=False, description="True if judge verdict was simulated/mocked")
    latency: float = Field(default=0.0, description="Verification latency in seconds")
    model: str = Field(default="", description="Vision judge model name or simulator tag")

    model_config = ConfigDict(extra="forbid")
