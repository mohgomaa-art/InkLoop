"""
InkLoop Shared Error and Validation Contracts.
Defines machine-readable error codes, failure classifications, and validation models.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ErrorSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ErrorCode(str, Enum):
    # Schema & Contract Errors (1000s)
    INVALID_SCHEMA = "ERR_1001_INVALID_SCHEMA"
    MISSING_REQUIRED_FIELD = "ERR_1002_MISSING_REQUIRED_FIELD"
    INVALID_FIELD_TYPE = "ERR_1003_INVALID_FIELD_TYPE"
    INVALID_IDENTIFIER_FORMAT = "ERR_1004_INVALID_IDENTIFIER_FORMAT"
    UNKNOWN_ENTITY_REFERENCE = "ERR_1005_UNKNOWN_ENTITY_REFERENCE"
    VERSION_MISMATCH = "ERR_1006_VERSION_MISMATCH"

    # Geometry & Spatial Errors (2000s)
    ZERO_OR_NEGATIVE_DIMENSION = "ERR_2001_ZERO_OR_NEGATIVE_DIMENSION"
    NON_FINITE_COORDINATE = "ERR_2002_NON_FINITE_COORDINATE"
    OUT_OF_BOUNDS = "ERR_2003_OUT_OF_BOUNDS"
    PANEL_UNINTENDED_OVERLAP = "ERR_2004_PANEL_UNINTENDED_OVERLAP"
    INVALID_TRANSFORM_MATRIX = "ERR_2005_INVALID_TRANSFORM_MATRIX"
    ASPECT_RATIO_DISTORTION = "ERR_2006_ASPECT_RATIO_DISTORTION"
    IMPOSSIBLE_FIT = "ERR_2007_IMPOSSIBLE_FIT"

    # Story Bible & Canon Errors (3000s)
    UNDECLARED_CHARACTER = "ERR_3001_UNDECLARED_CHARACTER"
    UNDECLARED_PROP = "ERR_3002_UNDECLARED_PROP"
    UNDECLARED_LOCATION = "ERR_3003_UNDECLARED_LOCATION"
    CANON_MUTATION_REJECTED = "ERR_3004_CANON_MUTATION_REJECTED"
    CHRONOLOGY_VIOLATION = "ERR_3005_CHRONOLOGY_VIOLATION"
    SPEAKER_MISMATCH = "ERR_3006_SPEAKER_MISMATCH"

    # External Provider & Network Errors (4000s)
    PROVIDER_AUTH_FAILED = "ERR_4001_PROVIDER_AUTH_FAILED"
    PROVIDER_RATE_LIMITED = "ERR_4002_PROVIDER_RATE_LIMITED"
    PROVIDER_TIMEOUT = "ERR_4003_PROVIDER_TIMEOUT"
    CONTENT_POLICY_VIOLATION = "ERR_4004_CONTENT_POLICY_VIOLATION"
    PROVIDER_SERVICE_UNAVAILABLE = "ERR_4005_PROVIDER_SERVICE_UNAVAILABLE"
    BUDGET_EXCEEDED = "ERR_4006_BUDGET_EXCEEDED"

    # Verification & Quality Gate Errors (5000s)
    VERIFICATION_FAILED = "ERR_5001_VERIFICATION_FAILED"
    VERIFICATION_UNSURE = "ERR_5002_VERIFICATION_UNSURE"
    FACE_TOO_SMALL_FOR_VERIFICATION = "ERR_5003_FACE_TOO_SMALL_FOR_VERIFICATION"
    TEXT_INTEGRITY_MISMATCH = "ERR_5004_TEXT_INTEGRITY_MISMATCH"
    TEXT_OVERFLOW_COLLISION = "ERR_5005_TEXT_OVERFLOW_COLLISION"

    # Engine Execution & Lifecycle States (6000s)
    ENGINE_NOT_IMPLEMENTED_YET = "ERR_6001_ENGINE_NOT_IMPLEMENTED_YET"
    ENGINE_EXPERIMENTAL_FEATURE = "ERR_6002_ENGINE_EXPERIMENTAL_FEATURE"
    ENGINE_CRASH = "ERR_6003_ENGINE_CRASH"
    MAX_RETRIES_EXCEEDED = "ERR_6004_MAX_RETRIES_EXCEEDED"
    RUN_CANCELLED = "ERR_6005_RUN_CANCELLED"

class ValidationErrorDetail(BaseModel):
    """Fine-grained machine-readable diagnostic detail for a single validation fault."""
    code: ErrorCode = Field(..., description="Stable error code from ErrorCode enum")
    message: str = Field(..., description="Human-readable explanation of the validation failure")
    field: Optional[str] = Field(default=None, description="Path to the invalid attribute or field (e.g. 'panels[0].rect.width')")
    entity_id: Optional[str] = Field(default=None, description="Identifier of the entity that failed validation")
    severity: ErrorSeverity = Field(default=ErrorSeverity.ERROR, description="Error severity level")
    retryable: bool = Field(default=False, description="Whether the operation may be retried without modifying inputs")
    diagnostic_data: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary numeric or structured diagnostic evidence")

class EngineFailure(BaseModel):
    """Encapsulates a fatal or non-fatal engine execution failure with diagnostic trace."""
    code: ErrorCode = Field(..., description="Primary error code")
    message: str = Field(..., description="High-level summary of the engine failure")
    stage: str = Field(..., description="Pipeline execution stage where the failure occurred (e.g. 'compilation', 'provider_call', 'verification')")
    retryable: bool = Field(default=False, description="Whether targeted bounded retry is permissible")
    http_status: Optional[int] = Field(default=None, description="HTTP status code if an external API call failed")
    raw_provider_error: Optional[str] = Field(default=None, description="Sanitized provider error message without sensitive credentials")
    validation_details: List[ValidationErrorDetail] = Field(default_factory=list, description="Subordinate validation errors contributing to this failure")

# Custom Exceptions for clean defensive programming
class InkLoopContractError(Exception):
    """Base exception for all InkLoop contract violations."""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}

class InvalidGeometryError(InkLoopContractError):
    """Raised when geometric dimensions, coordinates, or transforms are invalid."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.ZERO_OR_NEGATIVE_DIMENSION, message, details)

class OutOfBoundsError(InkLoopContractError):
    """Raised when an element extends beyond permissible container or canvas bounds."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.OUT_OF_BOUNDS, message, details)

class CanonViolationError(InkLoopContractError):
    """Raised when undeclared entities or illegal mutations are introduced."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.UNDECLARED_CHARACTER, message, details)
