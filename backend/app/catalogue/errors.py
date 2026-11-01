"""
InkLoop Image Knowledge Catalogue - Typed Exceptions & Errors.
Provides actionable, structured error types for catalogue retrieval,
validation, and compatibility conflicts.
"""
from typing import Optional, List, Dict, Any


class CatalogueError(Exception):
    """Base exception for all catalogue and knowledge retrieval failures."""
    def __init__(self, message: str, error_code: str = "ERR_CATALOGUE_GENERIC", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class RetrievalError(CatalogueError):
    """Base exception for retrieval-specific failures."""
    def __init__(self, message: str, error_code: str = "ERR_RETRIEVAL_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code=error_code, details=details)


class InvalidRetrievalRequestError(RetrievalError):
    """Raised when a retrieval request is structurally malformed or missing required context."""
    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        super().__init__(
            message=message,
            error_code="ERR_RETRIEVAL_INVALID_REQUEST",
            details={"missing_fields": missing_fields or []}
        )


class NoEligibleKnowledgeError(RetrievalError):
    """Raised when strict retrieval policies find no eligible candidates and fallback is disallowed."""
    def __init__(self, message: str, scene_id: str, criteria: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ERR_RETRIEVAL_NO_ELIGIBLE_KNOWLEDGE",
            details={"scene_id": scene_id, "criteria": criteria or {}}
        )


class KnowledgeCompatibilityConflictError(RetrievalError):
    """Raised when mandatory constraints clash with hard canon invariants or conflicting rules."""
    def __init__(self, message: str, conflicting_rule_id: str, conflicting_concept: str):
        super().__init__(
            message=message,
            error_code="ERR_RETRIEVAL_COMPATIBILITY_CONFLICT",
            details={"conflicting_rule_id": conflicting_rule_id, "conflicting_concept": conflicting_concept}
        )
