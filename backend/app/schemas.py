from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class AttributeCheck(BaseModel):
    id: str = Field(..., description="Unique attribute identifier (e.g. hair, glasses, jacket)")
    text: str = Field(..., description="Canonical description of the attribute")
    required: bool = Field(default=True, description="Whether this attribute is mandatory for panel acceptance")

class Tolerances(BaseModel):
    min_face_px_for_check: int = Field(default=80, description="Minimum face pixel size required to run identity check")

class CharacterSpec(BaseModel):
    id: str = Field(..., description="Character identifier in lowercase (e.g. nour)")
    attributes: List[AttributeCheck] = Field(..., description="List of declared attributes to verify")
    tolerances: Tolerances = Field(default_factory=Tolerances)

class AttributeVerdict(BaseModel):
    attr_id: str
    verdict: Literal["pass", "fail", "unsure"]
    evidence: str

class VerificationResult(BaseModel):
    passed: bool = Field(..., description="True only if all required attributes have verdict 'pass'")
    verdicts: List[AttributeVerdict]
    rejection_reason: Optional[str] = None

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    label: str
    confidence: float

class SegmentationResult(BaseModel):
    subject_count: int
    boxes: List[BoundingBox]
    mask_available: bool = False
