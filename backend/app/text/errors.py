"""
InkLoop Text Generation Engine - Typed Domain Exceptions.
Provides actionable error classes with structured error codes and detail maps.
"""
from typing import Optional, Dict, Any, List


class TextEngineError(Exception):
    """Base exception for all Text Generation Engine failures."""
    def __init__(self, message: str, error_code: str = "ERR_TEXT_GENERIC", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class TextValidationError(TextEngineError):
    """Raised when structured text blocks fail schema or semantic validation."""
    def __init__(self, message: str, error_code: str = "ERR_TEXT_VALIDATION_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, error_code=error_code, details=details)


class UndeclaredSpeakerError(TextValidationError):
    """Raised when a dialogue or monologue block references a speaker not declared in the Story Bible."""
    def __init__(self, speaker_id: str, scene_id: str, panel_id: str):
        super().__init__(
            message=f"Speaker '{speaker_id}' in panel '{panel_id}' (scene '{scene_id}') is not declared in the Story Bible / Canon.",
            error_code="ERR_TEXT_UNDECLARED_SPEAKER",
            details={"speaker_id": speaker_id, "scene_id": scene_id, "panel_id": panel_id}
        )


class ExactTextAlterationError(TextValidationError):
    """Raised when exact user text was modified, normalized, or paraphrased in violation of the contract."""
    def __init__(self, original_text: str, modified_text: str, block_id: str):
        super().__init__(
            message=f"Exact user text preservation violated for block '{block_id}'. Content was altered.",
            error_code="ERR_TEXT_EXACT_ALTERATION_DETECTED",
            details={
                "block_id": block_id,
                "original_len": len(original_text),
                "modified_len": len(modified_text),
            }
        )


class NarrativeContinuityConflictError(TextValidationError):
    """Raised when text assertions contradict established narrative timeline state."""
    def __init__(self, message: str, conflicting_entity: str, state_property: str, observed_value: Any):
        super().__init__(
            message=message,
            error_code="ERR_TEXT_CANON_STATE_CONTRADICTION",
            details={
                "conflicting_entity": conflicting_entity,
                "state_property": state_property,
                "observed_value": observed_value,
            }
        )


class TextAdapterError(TextEngineError):
    """Raised when text generation adapter fails or encounters unexpected provider response."""
    def __init__(self, message: str, provider: str, error_code: str = "ERR_TEXT_ADAPTER_FAILURE", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, error_code=error_code, details={"provider": provider, **(details or {})})


class TextGenerationBlockedError(TextEngineError):
    """Raised when a requested live generation provider is not configured or unsupported."""
    def __init__(self, message: str, provider: str):
        super().__init__(
            message=message,
            error_code="ERR_TEXT_GENERATION_BLOCKED",
            details={"provider": provider, "status": "not_implemented"}
        )
